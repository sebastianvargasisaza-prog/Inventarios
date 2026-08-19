# -*- coding: utf-8 -*-
"""El badge de mensajes sin leer es la consulta que MÁS corre en EOS · 19-ago-2026.

Sebastián mandó tres capturas de pantallas lentas (Dashboard Ejecutivo 4,7 s, Necesidades
colgada en "Cargando…", Calendario a 365 días). La sonda local no encontró N+1 en ninguno
de los siete endpoints que alimentan esas pantallas: con 380 lotes y 160 MPs sembrados el
conteo de consultas no se movió (+0/+1) y ninguno pasó de 35 ms.

Lo que sí apareció, leyendo lo que el NAVEGADOR ya tenía medido de esa sesión:

    /api/chat/unread-summary   ·  90 llamadas ANTES de que yo tocara nada
                               ·  mediana 781 ms · picos de 6.275 ms · 0 KB de respuesta

El widget de chat se inyecta en TODAS las pantallas y pide eso **cada 12 segundos**, así
que su costo se multiplica por la cantidad de pestañas abiertas, contra tres workers. Un
componente inyectado en todas partes multiplica cualquier defecto suyo por la cantidad de
pantallas (M217), y una consulta lenta repetida cada 12 s no hace lenta UNA pantalla: hace
lenta la app entera (M43).

⚠ **La forma correcta de la consulta depende del MOTOR, y medirla en SQLite habría hecho
tomar la decisión al revés.** Con 180.000 mensajes:

    SQLite      · correlacionado  27 ms  · agrupado  60 ms   ← acá gana el viejo
    PostgreSQL  · correlacionado  92 ms  · agrupado  58 ms   ← y acá pierde
                  páginas leídas: 101.079  contra  1.684     (60 veces menos)

Producción es PostgreSQL. Este archivo fija el RESULTADO (que los no leídos sean los que
son), no la forma de escribirlo -- salvo el guard que impide volver al subquery por hilo,
que existe porque la razón para no volver no está en el código sino en esa medición.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=20.0)


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar():
    cn = _cn()
    try:
        cn.execute("DELETE FROM chat_messages WHERE thread_id IN "
                   "(SELECT id FROM chat_threads WHERE nombre LIKE 'ZBADGE%')")
        cn.execute("DELETE FROM chat_thread_members WHERE thread_id IN "
                   "(SELECT id FROM chat_threads WHERE nombre LIKE 'ZBADGE%')")
        cn.execute("DELETE FROM chat_threads WHERE nombre LIKE 'ZBADGE%'")
        cn.commit()
    finally:
        cn.close()


def _hilo(cn, nombre, usuario, mensajes, ultimo_leido_offset=None):
    """Crea un hilo con N mensajes de OTRO y devuelve (thread_id, ids)."""
    cn.execute("INSERT INTO chat_threads (tipo, nombre, creado_por) "
               "VALUES ('grupo', ?, 'sebastian')", (nombre,))
    tid = cn.execute("SELECT last_insert_rowid()").fetchone()[0]
    ids = []
    for i, (quien, borrado) in enumerate(mensajes):
        cn.execute("INSERT INTO chat_messages (thread_id, sender, contenido, eliminado) "
                   "VALUES (?,?,?,?)", (tid, quien, 'm%d' % i, borrado))
        ids.append(cn.execute("SELECT last_insert_rowid()").fetchone()[0])
    leido = ids[ultimo_leido_offset] if ultimo_leido_offset is not None else None
    cn.execute("INSERT INTO chat_thread_members (thread_id, username, ultimo_leido_id) "
               "VALUES (?,?,?)", (tid, usuario, leido))
    return tid, ids


def test_el_badge_cuenta_lo_que_de_verdad_falta_por_leer(app, db_clean):
    """Los cuatro casos que decide el badge · el resultado, no la forma de escribirlo."""
    _limpiar()
    cn = _cn()
    try:
        # A · 3 mensajes de otro, ninguno leído → 3
        _hilo(cn, 'ZBADGE A', 'sebastian',
              [('otro', 0), ('otro', 0), ('otro', 0)])
        # B · 4 de otro, leídos hasta el segundo → 2
        _hilo(cn, 'ZBADGE B', 'sebastian',
              [('otro', 0), ('otro', 0), ('otro', 0), ('otro', 0)],
              ultimo_leido_offset=1)
        # C · mis propios mensajes NO cuentan, y los borrados tampoco → 1
        _hilo(cn, 'ZBADGE C', 'sebastian',
              [('sebastian', 0), ('otro', 1), ('otro', 0)])
        # D · hilo de OTRA persona · no puede aparecer en mi badge
        _hilo(cn, 'ZBADGE D', 'otro_usuario', [('otro', 0), ('otro', 0)])
        cn.commit()
    finally:
        cn.close()

    try:
        j = _login(app).get('/api/chat/unread-summary').get_json() or {}
        por_nombre = {t.get('nombre'): t.get('unread') for t in (j.get('threads') or [])}
        assert por_nombre.get('ZBADGE A') == 3, por_nombre
        assert por_nombre.get('ZBADGE B') == 2, ('no respeta hasta dónde leí', por_nombre)
        assert por_nombre.get('ZBADGE C') == 1, (
            'cuenta mis propios mensajes o los borrados', por_nombre)
        assert 'ZBADGE D' not in por_nombre, (
            'muestra un hilo del que no soy miembro', por_nombre)
        # el total es la suma de lo que lista · si no, el número de arriba contradice
        # la lista de abajo (M161)
        assert j.get('total') == sum((t.get('unread') or 0) for t in j['threads']), j
    finally:
        _limpiar()


def test_un_hilo_SIN_nada_por_leer_no_ensucia_el_badge(app, db_clean):
    """El borde que hace que el agrupado no cambie lo que se ve (M96): con LEFT JOIN el
    hilo sigue viniendo, con cuenta 0, y no puede colarse en la lista."""
    _limpiar()
    cn = _cn()
    try:
        _hilo(cn, 'ZBADGE LEIDO', 'sebastian',
              [('otro', 0), ('otro', 0)], ultimo_leido_offset=1)
        cn.commit()
    finally:
        cn.close()
    try:
        j = _login(app).get('/api/chat/unread-summary').get_json() or {}
        nombres = [t.get('nombre') for t in (j.get('threads') or [])]
        assert 'ZBADGE LEIDO' not in nombres, (
            'un hilo totalmente leído aparece en el badge', nombres)
    finally:
        _limpiar()


def test_no_vuelve_al_COUNT_por_hilo(app, db_clean):
    """La razón para no volver no está en el código: está en la medición del docstring.

    En PostgreSQL el subquery por hilo lee 101.079 páginas contra 1.684 del agrupado, y
    esto corre cada 12 segundos desde cada pestaña abierta de cada persona.
    """
    import ast
    import io
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "api", "blueprints", "chat.py")
    src = io.open(ruta, encoding="utf-8").read()
    lin = src.splitlines()
    cuerpo = None
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.FunctionDef) and n.name == 'chat_unread_summary':
            cuerpo = "\n".join(lin[n.lineno - 1:n.end_lineno])
    assert cuerpo, "no encontré el endpoint del badge"
    # Sin comentarios · el que explica por qué NO se usa contiene la palabra (M154)
    sin_com = "\n".join(l for l in cuerpo.splitlines() if not l.strip().startswith("#"))
    assert "(SELECT COUNT(*) FROM chat_messages" not in sin_com, (
        "volvió el COUNT correlacionado por hilo · en PostgreSQL lee 60 veces más páginas "
        "y esta consulta corre cada 12 s desde todas las pantallas")
    assert "LEFT JOIN chat_messages" in sin_com, sin_com[:400]


def test_ningun_widget_GLOBAL_consulta_por_debajo_del_corte_de_visibilidad(app, db_clean):
    """Un poll por debajo de 15 s queda FUERA de la protección y corre con la pestaña oculta.

    `cortex.js` saltea el tick cuando nadie mira, pero sólo a partir de 15 s (por debajo
    viven relojes y animaciones, que no se tocan). El chat estaba en 12 s, o sea justo
    afuera: pedía desde cada pestaña abierta, la mirara alguien o no. Y estos widgets se
    inyectan en TODAS las pantallas, así que su costo se multiplica por la cantidad de
    pestañas contra tres workers (M43/M216/M217).
    """
    import io
    import re

    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cortex = io.open(os.path.join(raiz, "api", "static", "cortex.js"),
                     encoding="utf-8").read()
    m = re.search(r"UMBRAL_MS\s*=\s*(\d+)", cortex)
    assert m, "desapareció el umbral de visibilidad de cortex.js"
    umbral = int(m.group(1))

    malos = []
    for arch in ("chat.py", "notif.py"):
        ruta = os.path.join(raiz, "api", "blueprints", arch)
        if not os.path.exists(ruta):
            continue
        src = io.open(ruta, encoding="utf-8").read()
        src = re.sub(r"//.*", "", src)          # sin comentarios (M154)
        for mm in re.finditer(r"setInterval\(\s*[^,]+,\s*(\d+)", src):
            ms = int(mm.group(1))
            if ms < umbral:
                malos.append("%s · cada %d ms" % (arch, ms))
    assert not malos, (
        "widget global consultando por debajo del corte de %d ms: sigue pidiendo con la "
        "pestaña oculta, desde cada pestaña abierta · %s" % (umbral, malos))


def test_el_widget_servido_compila(app, db_clean):
    """Se node-checkea lo que el navegador RECIBE, no el fuente (M65/M173).

    Un error de sintaxis acá no rompe Python ni el gate: deja el chat muerto en TODAS las
    pantallas, sin un solo mensaje.
    """
    import os as _os
    import subprocess
    import tempfile

    r = _login(app).get('/api/chat/widget.js')
    assert r.status_code == 200, r.status_code
    js = r.get_data(as_text=True)
    assert len(js) > 2000, ("el widget salió vacío · el check no midió nada", len(js))
    assert 'cwCheckUnread' in js, "el widget servido no trae el poll del badge"

    f = _os.path.join(tempfile.gettempdir(), 'cw_widget_servido.js')
    with open(f, 'w', encoding='utf-8') as fh:
        fh.write(js)
    p = subprocess.run(['node', '--check', f], capture_output=True, text=True)
    assert p.returncode == 0, ("el widget de chat no compila: %s" % p.stderr[:400])
