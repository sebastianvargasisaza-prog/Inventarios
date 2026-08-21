"""El rótulo F02 sale para FIRMAR, y sólo de los equipos que se van a usar (15-ago-2026).

Sebastián, abriendo los rótulos de limpieza desde Registrar Producción:
  1. *"siempre sale que fui yo sin importar el usuario"*
  2. *"no van a usar todos los equipos, deberían poder seleccionarlos... que primero
     pregunte cuáles usarán para que sean esos rótulos los que se impriman"*

**Lo primero no era la sesión**: el rótulo tomaba el ÚLTIMO ciclo de limpieza del área, y
en producción ése era una demo del 24-jun firmada por él. Así que TODAS las salas salían
de la impresora **ya firmadas por alguien que no ejecutó esa limpieza**, con "SIMULACRO
Demo" como producto a elaborar. Un registro regulado prefirmado por quien no hizo el acto
es un registro falso — y encima invita a pegarlo tal cual.

Lo que fija este guard:
  · que una firma vieja NO se preimprima (sale la línea en blanco para firmar);
  · que una limpieza RECIENTE sí salga firmada — si no, el arreglo rompería el caso bueno;
  · que se pueda elegir qué equipos se imprimen, y que se impriman SÓLO ésos;
  · que la URL vieja (`?todos=1`) siga funcionando: está enlazada desde el dashboard y una
    URL viva no se rompe (M120).
"""
import os
import re
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _area():
    """El id de un área limpiable cualquiera (las que la pantalla lista)."""
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        r = conn.execute(
            "SELECT id, codigo FROM areas_planta WHERE activo=1 "
            "AND (tipo='produccion' OR codigo IN ('DISP','ACOND')) "
            "ORDER BY orden, codigo LIMIT 1").fetchone()
    finally:
        conn.close()
    assert r, "no hay áreas limpiables sembradas"
    return r[0], r[1]


def _ciclo(area_id, area_codigo, realizado_at, quien="sebastian"):
    _exec("DELETE FROM rotulos_limpieza WHERE area_id=?", (area_id,))
    return _exec(
        "INSERT INTO rotulos_limpieza (area_id, area_codigo, producto_elaborar, "
        "sanitizante, detergente, realizado_por, realizado_at, estado) "
        "VALUES (?,?,'SIMULACRO Demo','Alcohol 70%','Detergente Neutro Industrial',?,?,'limpiando')",
        (area_id, area_codigo, quien, realizado_at))


def _hoy_menos(dias):
    from datetime import datetime, timedelta
    return (datetime.utcnow() - timedelta(hours=5) - timedelta(days=dias)).strftime(
        "%Y-%m-%d %H:%M:%S")


def test_una_firma_vieja_no_se_preimprime(app, db_clean):
    """El caso real: una demo de hace dos meses firmando todos los rótulos de la planta."""
    aid, acod = _area()
    _ciclo(aid, acod, "2026-06-24 23:16:56")
    c = _login(app)
    html = c.get("/planta/rotulo-limpieza/%d/pdf" % aid).data.decode("utf-8")
    assert "Firma electr" not in html, (
        "el rótulo sale prefirmado con un ciclo viejo: es un registro falso")
    assert "Firma y fecha" in html, "no dejó la línea en blanco para firmar"
    assert "SIMULACRO Demo" not in html, (
        "arrastra el producto del ciclo viejo: no es el que se va a elaborar ahora")


def test_una_limpieza_reciente_si_sale_firmada(app, db_clean):
    """El borde que hace que el arreglo no rompa el caso bueno (M96)."""
    aid, acod = _area()
    _ciclo(aid, acod, _hoy_menos(0), quien="mayerlin")
    c = _login(app)
    html = c.get("/planta/rotulo-limpieza/%d/pdf" % aid).data.decode("utf-8")
    assert "Firma electr" in html, "una limpieza de hoy tiene que salir firmada"
    # Desde el 16-ago el rótulo imprime el NOMBRE de la persona ("Maierlin Rivera Mejía")
    # en vez del username, que es lo que un registro regulado necesita: quién ejecutó, no
    # con qué usuario entró. El guard fija la GARANTÍA -- que se vea quién -- y acepta el
    # username sólo como respaldo, para el caso en que ese nombre no esté cargado (M97).
    assert ("maierlin" in html.lower() or "mayerlin" in html.lower()), (
        "no muestra a quien la ejecutó")


def test_el_limite_de_vigencia_se_respeta(app, db_clean):
    """Justo adentro sale firmado; justo afuera, en blanco."""
    from api.blueprints.programacion import (_rotulo_firma_vigente,
                                             _ROTULO_FIRMA_VIGENTE_DIAS)
    assert _rotulo_firma_vigente(_hoy_menos(0)) is True
    assert _rotulo_firma_vigente(_hoy_menos(_ROTULO_FIRMA_VIGENTE_DIAS + 1)) is False
    # sin fecha o con basura se trata como vieja: el formato sale en blanco
    assert _rotulo_firma_vigente("") is False
    assert _rotulo_firma_vigente("no es una fecha") is False


def test_primero_pregunta_que_equipos(app, db_clean):
    """Sin elegir nada, la pantalla ofrece el selector en vez de imprimir todo."""
    c = _login(app)
    html = c.get("/planta/rotulos-limpieza").data.decode("utf-8")
    assert "Imprimir los seleccionados" in html, "no ofrece elegir"
    assert "function imprimir()" in html, "falta la función que arma la impresión"
    assert "ESTADO DE LIMPIEZA" not in html.upper(), (
        "imprimió los rótulos sin preguntar qué equipos se van a usar")


def test_imprime_solo_los_equipos_elegidos(app, db_clean):
    """El punto del pedido: un rótulo por equipo que SÍ se va a usar."""
    aid, acod = _area()
    from api.blueprints.programacion import _equipos_de_area
    from api.database import get_db
    with app.app_context():
        eqs = _equipos_de_area(get_db(), acod)
    if len(eqs) < 2:
        import pytest
        pytest.skip("el área sembrada no tiene dos equipos para distinguir")
    elegido, descartado = eqs[0], eqs[1]
    c = _login(app)
    html = c.get("/planta/rotulos-limpieza?equipos=%s" % elegido["codigo"]).data.decode("utf-8")
    assert elegido["codigo"] in html, "no salió el rótulo del equipo elegido"
    assert descartado["codigo"] not in html, (
        "salió el rótulo de un equipo que no se eligió: eso es papel descartado o un "
        "rótulo pegado donde no corresponde")


def test_la_url_vieja_sigue_funcionando(app, db_clean):
    """Está enlazada desde el dashboard: una URL viva no se rompe (M120)."""
    c = _login(app)
    r = c.get("/planta/rotulos-limpieza?todos=1")
    assert r.status_code == 200
    html = r.data.decode("utf-8")
    assert "ESTADO DE LIMPIEZA" in html.upper(), "el modo 'todos' dejó de imprimir"


def test_los_botones_dicen_lo_que_hacen(app, db_clean):
    """"Imprimir TODOS" tiene que seguir imprimiendo todos: si el botón promete una cosa
    y hace otra, se deja de creer en la pantalla (M161). Y el de Registrar Producción
    ahora pregunta qué equipos, así que su texto lo dice."""
    c = _login(app)
    html = c.get("/inventarios").data.decode("utf-8")
    assert "/planta/rotulos-limpieza?todos=1" in html, (
        "el botón 'Imprimir TODOS' perdió el modo todos: abriría el selector")
    assert "qu&eacute; equipos se van a usar" in html or "qué equipos se van a usar" in html, (
        "el botón de Registrar Producción no avisa que ahora se eligen los equipos")


def _nombre_area(aid):
    """El nombre de la sala, para verificar que se la puede buscar por él."""
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        r = conn.execute("SELECT nombre FROM areas_planta WHERE id=?", (aid,)).fetchone()
    finally:
        conn.close()
    return (r[0] if r else "") or ""


def test_el_area_elegida_viaja_y_queda_en_foco(app, db_clean):
    """Sebastián: *"se supone que yo aquí elijo el área, entonces debería mostrarme"*.

    El contexto que ya llenó en Registrar Producción no se vuelve a preguntar: la sala
    elegida abre primero y con sus equipos marcados. Las demás quedan abajo -esconderlas
    dejaría sin salida a una tanda que toca dos salas (M179).
    """
    aid, acod = _area()
    c = _login(app)
    html = c.get("/planta/rotulos-limpieza?area=%s" % acod).data.decode("utf-8")
    # Desde el 21-ago la pantalla es UNA lista con buscador, no tarjetas por sala
    # (Sebastán: *"que no aparecieran por áreas sino el listado completo ... y con un
    # buscador así buscan los equipos que necesitan"*). La garantía es la misma: quien
    # viene de Registrar Producción encuentra ESA sala servida, sin buscarla a mano.
    assert 'class="eq foco"' in html, "no distingue los equipos de la sala elegida"
    assert 'id="q"' in html and 'value="' in html, "el buscador no viene con la sala"
    # El chip con el nombre de la sala salió de la fila del equipo el 21-ago, y no es una
    # pérdida: Sebastián lo pidió con todas las letras (*"aquí en el equipo no es necesario el
    # área, se puede quitar todo esto que dice área"*) porque el rótulo del equipo tampoco la
    # lleva -- mostrarla en la lista prometía algo que el papel no dice. Lo que NO se puede
    # perder es poder ubicar el equipo por su sala, así que la garantía se mide donde ahora
    # vive: el nombre de la sala sigue en el índice de búsqueda de cada fila.
    _nom_sala = _nombre_area(aid).lower()
    # Se mide sobre las filas de EQUIPO, no sobre el HTML entero: el nombre de la sala también
    # aparece en su propia fila de área, así que un `in html` pasaría verde con el índice de los
    # equipos vacío -- o sea dejaría de medir (M96).
    _filas_eq = [m for m in re.findall(r'<label class="eq([^"]*)" data-buscar="([^"]*)"', html)
                 if 'area' not in m[0]]
    assert _filas_eq, "no hay filas de equipo"
    # Anclado al FINAL, que es donde el generador pone la sala: sin anclar, "Fabricación 1"
    # matchea dentro de "tanque de fabricación 100L" y el guard mide su propio ruido (M80).
    assert any(b.lower().rstrip().endswith(_nom_sala) for _cls, b in _filas_eq),         "no se puede encontrar el equipo buscando por su sala"
    assert "checked" in html, "los equipos de esa sala no vienen marcados"
    # y la sala se puede pedir como ítem propio: su rótulo es el que no trae equipo
    assert 'value="AREA:%s"' % acod in html, "el área no se puede elegir en la lista"


def test_la_linea_de_firma_sale_vacia(app, db_clean):
    """La línea va EN BLANCO para firmar con lapicero (Sebastián 20-ago, con la etiqueta
    impresa en la mano). El 15-ago se imprimía el nombre del operario asignado para no
    escribirlo a mano; el problema es que el asignado y el que termina limpiando no
    siempre son el mismo, y un nombre ya impreso empuja a que firme quien no hizo el acto.
    La marca de firma electrónica tampoco va: certificaría por él."""
    aid, acod = _area()
    _exec("DELETE FROM rotulos_limpieza WHERE area_id=?", (aid,))
    c = _login(app)
    from api.blueprints.programacion import _equipos_de_area
    from api.database import get_db
    with app.app_context():
        eqs = _equipos_de_area(get_db(), acod)
    if not eqs:
        import pytest
        pytest.skip("el área sembrada no tiene equipos")
    html = c.get("/planta/rotulos-limpieza?equipos=%s&operario=mayerlin"
                 % eqs[0]["codigo"]).data.decode("utf-8")
    assert "mayerlin" not in html.lower(), "imprimió el nombre en la línea de la firma"
    assert "Firma electr" not in html, (
        "certificó la firma de alguien que no registró la limpieza")
    assert "Firma y fecha" in html, "no dejó la línea para firmar"


def test_el_rotulo_por_equipo_no_lleva_la_sala(app, db_clean):
    """El rótulo se pega EN la máquina y la máquina se mueve entre salas: el papel decía
    una sala y el equipo estaba en otra (Sebastián 20-ago). La sala del ciclo queda en el
    registro, que es lo que va al expediente."""
    aid, acod = _area()
    c = _login(app)
    from api.blueprints.programacion import _equipos_de_area
    from api.database import get_db
    with app.app_context():
        eqs = _equipos_de_area(get_db(), acod)
    if not eqs:
        import pytest
        pytest.skip("el área sembrada no tiene equipos")
    html = c.get("/planta/rotulos-limpieza?equipos=%s" % eqs[0]["codigo"]).data.decode("utf-8")
    assert "Sala / " not in html, "el rótulo por equipo sigue imprimiendo la sala"
    assert eqs[0]["codigo"] in html, "perdió el código del equipo, que es el sujeto del rótulo"


def test_sale_un_rotulo_por_estado(app, db_clean):
    """El área pasa de limpia a en uso y a sucia en la misma jornada: se imprimen las tres
    etiquetas y se cambia la pegada, en vez de tachar la anterior (Sebastián 20-ago)."""
    aid, acod = _area()
    c = _login(app)
    from api.blueprints.programacion import _equipos_de_area
    from api.database import get_db
    with app.app_context():
        eqs = _equipos_de_area(get_db(), acod)
    if not eqs:
        import pytest
        pytest.skip("el área sembrada no tiene equipos")
    cod = eqs[0]["codigo"]
    una = c.get("/planta/rotulos-limpieza?equipos=%s" % cod).data.decode("utf-8")
    tres = c.get("/planta/rotulos-limpieza?equipos=%s&estados=limpio,en_uso,sucio"
                 % cod).data.decode("utf-8")
    assert una.count('class="sheet"') == 1, "sin el parámetro debería salir un solo rótulo"
    assert tres.count('class="sheet"') == 3, "no salieron las tres etiquetas"
    # Cada copia marca SU estado: son tres etiquetas distintas, no la misma tres veces.
    assert tres.count('class="chip on"') == 3, "las tres copias no marcan un estado cada una"
    dos = c.get("/planta/rotulos-limpieza?equipos=%s&estados=limpio,sucio"
                % cod).data.decode("utf-8")
    assert dos.count('class="sheet"') == 2, "no respetó los estados elegidos"


def test_el_selector_deja_elegir_los_estados(app, db_clean):
    """La pantalla previa elige qué estados se imprimen. Y ya NO pregunta quién limpia: ese
    desplegable existía sólo para imprimir el nombre, que dejó de imprimirse."""
    aid, acod = _area()
    c = _login(app)
    html = c.get("/planta/rotulos-limpieza?area=%s" % acod).data.decode("utf-8")
    assert 'class="ckest"' in html, "no deja elegir los estados"
    for v in ('value="limpio"', 'value="en_uso"', 'value="sucio"'):
        assert v in html, "falta el estado %s" % v
    assert 'id="quien"' not in html, "quedó el desplegable de quién limpia, que ya no hace nada"


def test_el_rol_limpieza_no_se_convierte_en_todero(app, db_clean):
    """Hay DOS whitelists de rol (crear y editar): si el rol se agrega en una sola, la
    otra lo pisa en silencio y la operaria queda como 'todero' (M116/M45)."""
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "api", "blueprints", "programacion.py")
    fuente = open(ruta, encoding="utf-8").read()
    listas = [l for l in fuente.splitlines() if "if rol not in (" in l]
    assert len(listas) >= 2, "cambió la forma de validar el rol: revisar este guard"
    # cada whitelist tiene que estar completa: se mira la línea y su continuación
    for i, linea in enumerate(fuente.splitlines()):
        if "if rol not in (" in linea:
            ventana = " ".join(fuente.splitlines()[i:i + 3])
            assert "'limpieza'" in ventana, (
                "una de las whitelists de rol no acepta 'limpieza': ahí se convierte en "
                "todero sin avisar")


def test_el_boton_lleva_el_area_y_el_operario(app, db_clean):
    """Si el contexto no viaja, la persona vuelve a elegir lo que ya eligió.

    ⚠ El JS del dashboard NO está inline: vive en los bundles `/planta-app.js` y
    `/planta-core.js`, así que un test que sólo mire el HTML concluye que la función no
    existe (M166 · me pasó al escribir este mismo guard). Se mira el HTML para el BOTÓN y
    los bundles para la FUNCIÓN.
    """
    c = _login(app)
    html = c.get("/inventarios").data.decode("utf-8")
    assert "abrirRotulosLimpieza()" in html, "el botón no llama a la función"
    js = ""
    for ruta in ("/planta-app.js", "/planta-core.js"):
        r = c.get(ruta)
        assert r.status_code == 200, (ruta, r.status_code)
        js += r.data.decode("utf-8")
    assert "function abrirRotulosLimpieza()" in js, "falta la función del botón"
    assert "'area=' + encodeURIComponent(cod)" in js, "no manda el área elegida"
    # El operario que FABRICA no viaja: el que limpia puede ser otro (hay operaria de
    # limpieza) y poner su nombre induciría a que firme quien no limpió. Ese dato lo
    # pregunta el selector.
    assert "'operario=' + encodeURIComponent(nom)" not in js, (
        "manda el operario de fabricación al rótulo de limpieza")
