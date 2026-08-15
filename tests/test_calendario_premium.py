"""El calendario tiene que DECIR lo que muestra (Sebastián 14-ago-2026).

Mirando la pantalla: "¿calendario es premium?". No lo era, y el defecto de fondo
estaba a la vista en su propia captura: un chip que decía **"BLUSH BALM 0kg"**
dibujado igual que uno de 90 kg.

Lo que estos tests fijan es lo que puede salir caro:

1. **Un lote de 0 kg no se puede ver igual que uno normal.** Ocupa un día del
   calendario, NO produce nada y NO le pide materia prima al abastecimiento, así
   que promete una producción que no va a existir (M5: lo que se muestra es lo que
   decide). El guard mira que la regla de color del lote sin kg quede DESPUÉS de
   las de origen: con la misma especificidad manda la última, y puesta antes el
   verde del origen la tapaba. Ese fue el bug real que apareció al mirar la previa,
   no al leer el código.
2. **Ya no se puede CREAR uno de 0 kg** por el ➕ del calendario, que lo aceptaba y
   lo guardaba en silencio.
3. **El nombre del producto no se corta**: "SUERO TRIACTIVE RE" y
   "SUERO DE NIACINAMI" no distinguen un producto de otro, justo en la pantalla
   donde se decide qué se fabrica.
4. **La barra de Programación no puede mentir sobre dónde estás**: dos pestañas
   ('Alistar envases' y 'Estacionalidad') no estaban en el mapa del resaltado, así
   que al abrirlas seguía marcada la anterior (M161).
"""
import ast
import io
import os
import re
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _h():
    h = {'Content-Type': 'application/json'}
    h.update(csrf_headers())
    return h


def _q(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _pantalla(app):
    """El HTML REAL que se sirve, no el fuente (M65/M173)."""
    r = _login(app).get('/admin/plan-calendario')
    assert r.status_code == 200, r.status_code
    return r.data.decode('utf-8')


# ── 1 · el lote sin kg se ve distinto ────────────────────────────────────────
def test_el_lote_sin_kg_se_pinta_distinto_del_resto(app):
    html = _pantalla(app)
    i_sinkg = html.rfind('.lote.sinkg{')
    assert i_sinkg > 0, 'no existe la regla del lote sin kg'
    # Con igual especificidad manda la ÚLTIMA aparición, así que se compara con
    # rfind: si una variante por origen queda después -aunque sea una copia suelta
    # más abajo-, el chip sin kg vuelve a salir verde con el texto de alerta
    # adentro, que es exactamente lo que mostró la previa.
    for origen in ('.lote.eos_plan{', '.lote.eos_canonico{', '.lote.eos_b2b{',
                   '.lote.calendar{', '.lote.sugerido{', '.lote.esperando_recurso{'):
        i_o = html.rfind(origen)
        if i_o > 0:
            assert i_o < i_sinkg, (
                '%s queda DESPUÉS de .lote.sinkg y le tapa el rojo' % origen)


def test_el_chip_dice_sin_kg_en_vez_de_0kg(app):
    html = _pantalla(app)
    assert 'const sinKg = !((lt.kg || 0) > 0);' in html, 'no se detecta el lote sin kg'
    assert '⚠ sin kg definidos' in html, 'el chip seguiría mostrando "0kg" a secas'
    assert "(sinKg ? ' sinkg' : '')" in html, 'la clase no llega al chip'


def test_el_kpi_cuenta_los_lotes_sin_kg(app):
    """Un hallazgo que no se puede contar no se puede cerrar."""
    html = _pantalla(app)
    assert '⚖ Sin kg' in html
    assert "filter(a => !((a.kg || 0) > 0))" in html, 'el KPI no cuenta lo que dice'


# ── 2 · no se puede crear ────────────────────────────────────────────────────
def test_no_se_puede_programar_un_lote_de_cero_kg(app, db_clean):
    r = _login(app).post('/api/plan/programar-manual',
                         json={'producto': 'ZCAL SIN KG', 'fecha': _prox_habil(),
                               'kg': 0, 'lotes': 1},
                         headers=_h())
    assert r.status_code == 400, r.data
    assert r.get_json().get('codigo') == 'SIN_KG'
    assert not _q("SELECT 1 FROM produccion_programada WHERE producto='ZCAL SIN KG'"), \
        'lo rechazó pero igual lo guardó'


def test_programar_con_kg_sigue_funcionando(app, db_clean):
    """El guard tiene que frenar lo malo SIN trabar lo legítimo (M171)."""
    f = _prox_habil()
    r = _login(app).post('/api/plan/programar-manual',
                         json={'producto': 'ZCAL CON KG', 'fecha': f,
                               'kg': 30, 'lotes': 1},
                         headers=_h())
    assert r.status_code == 200, r.data
    fila = _q("SELECT cantidad_kg FROM produccion_programada WHERE producto='ZCAL CON KG'")
    assert fila and float(fila[0][0]) == 30.0
    _q("SELECT 1")  # noop · la limpieza la hace db_clean


def test_un_pedido_sin_kilos_no_cae_al_calendario(app, db_clean):
    """El otro camino que crea lotes: el pedido del cliente. Los kilos salen de
    unidades × ml, así que un pedido sin unidades daría un lote de 0 kg.

    (El volumen tiene respaldo aguas arriba -sin ml asume 30-, así que el caso
    que de verdad llega a cero es el de las unidades.)"""
    import sqlite3 as _sq
    conn = _sq.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute("DELETE FROM pedidos_b2b WHERE cliente_id='ZKG1'")
        cur = conn.execute(
            "INSERT INTO pedidos_b2b (cliente_id, cliente_nombre, producto_nombre, "
            "cantidad_uds, ml_unidad, fecha_estimada, estado, urgencia, envase_codigo, "
            "creado_at_utc, creado_por) VALUES ('ZKG1','Cliente Sin Kg','ZKG PRODUCTO', "
            "0, 30, '2026-12-01', 'pendiente', 'media', '', '2026-08-12T09:00:00Z', 'test')")
        pid = cur.lastrowid
        conn.commit()
    finally:
        conn.close()
    r = _login(app).post('/api/pedidos-b2b/%d/confirmar' % pid, json={}, headers=_h())
    assert r.status_code == 400, r.data
    assert r.get_json().get('codigo') == 'SIN_KG'
    assert _q("SELECT estado FROM pedidos_b2b WHERE id=?", (pid,))[0][0] == 'pendiente', \
        'lo rechazó pero igual movió el pedido'
    assert not _q("SELECT 1 FROM produccion_programada WHERE producto='ZKG PRODUCTO'"), \
        'creó un lote de 0 kg en el calendario'


def _prox_habil():
    """La planta produce lun-vie no festivo · un offset fijo cae siempre en el
    mismo día de semana y el test reventaría los fines de semana (M99)."""
    from datetime import date, timedelta
    import sys
    sys.path.insert(0, os.path.join(RAIZ, 'api'))
    from blueprints.plan import es_festivo_colombia
    d = date.today() + timedelta(days=10)
    for _ in range(12):
        if d.weekday() < 5 and not es_festivo_colombia(d):
            return d.isoformat()
        d += timedelta(days=1)
    raise AssertionError('sin día hábil en la ventana')


# ── 3 · el nombre completo ───────────────────────────────────────────────────
def test_el_nombre_del_producto_no_se_corta(app):
    html = _pantalla(app)
    assert 'slice(0, 18)' not in html, 'el nombre del lote vuelve a salir cortado'
    assert '.lote .lote-nom{' in html, 'falta el CSS que lo acota a dos líneas'
    assert '-webkit-line-clamp:2' in html


def _sin_comentarios(html):
    """Lo que se juzga es el texto que la persona LEE, no los comentarios del
    código: buscar en el fuente crudo hace que el test pase o falle por la razón
    equivocada (M154)."""
    html = re.sub(r'<!--.*?-->', '', html, flags=re.S)
    html = re.sub(r'^\s*//.*$', '', html, flags=re.M)
    return html


def test_la_pantalla_no_habla_de_fallback(app):
    """"fallback" es jerga interna: el que la lee no sabe si algo está roto."""
    html = _sin_comentarios(_pantalla(app))
    assert 'fallback' not in html.lower(), 'jerga interna a la vista del usuario'
    assert 'Todos los lotes agendados' in html


def test_sin_rastros_de_ia_en_el_calendario(app):
    """El em-dash delata IA (regla 0) · Sebastián lo pidió explícitamente."""
    assert '—' not in _pantalla(app)


# ── 4 · la barra de Programación no miente ───────────────────────────────────
def _dashboard_html():
    ruta = os.path.join(RAIZ, 'api', 'templates_py', 'dashboard_html.py')
    with io.open(ruta, encoding='utf-8') as fh:
        arbol = ast.parse(fh.read())
    for nodo in ast.walk(arbol):
        if (isinstance(nodo, ast.Assign) and len(nodo.targets) == 1
                and isinstance(nodo.targets[0], ast.Name)
                and isinstance(nodo.value, ast.Constant)
                and isinstance(nodo.value.value, str)
                and 'data-prog-sub' in nodo.value.value
                and '_highlightProgSubTab' in nodo.value.value):
            return nodo.value.value
    raise AssertionError('no se encontró la pantalla de Programación')


def test_toda_subpestania_de_programacion_se_puede_marcar_activa():
    html = _dashboard_html()
    # Los tabs que la barra ofrece...
    ofrecidos = set(re.findall(r"data-prog-sub=\"[^\"]+\"[^>]*onclick=\"switchProgTab\('([a-z_]+)'\)",
                               html))
    assert len(ofrecidos) >= 6, 'no se encontraron los botones de la barra: %s' % ofrecidos
    # ...tienen que estar TODOS en la lista que usa el resaltado.
    m = re.search(r"var TABS = \[([^\]]+)\]", html)
    assert m, 'no está la lista de tabs del resaltado'
    conocidos = set(re.findall(r"'([a-z_]+)'", m.group(1)))
    faltan = sorted(ofrecidos - conocidos)
    assert not faltan, 'pestañas que se abren y no se marcan activas: %s' % faltan


def test_el_mapa_de_grupos_cubre_toda_pestania_de_la_barra():
    html = _dashboard_html()
    m = re.search(r"var _PROG_TAB_TO_GROUP = \{(.*?)\n  \};", html, re.S)
    assert m, 'no está el mapa tab→grupo'
    mapeados = set(re.findall(r"'([a-z_]+)':\s*'", m.group(1)))
    for tab in ('estacionalidad', 'config', 'serigrafia', 'calendario',
                'abastecimiento', 'factibilidad', 'necesidades'):
        assert tab in mapeados, (
            "'%s' no está en el mapa: al abrirla, la barra sigue marcando otra" % tab)


def test_la_barra_usa_un_solo_sistema_de_color():
    """Cinco colores distintos se leen como cinco cosas sueltas y no dejan ver
    cuál está abierta. Encendido = violeta del sistema, apagado = tarjeta."""
    html = _dashboard_html()
    i = html.find('id="prog-sub-calendario_grp"')
    assert i > 0
    barra = html[i:i + 3000]
    botones = re.findall(r'<button[^>]*data-prog-sub="calendario_grp"[^>]*>', barra)
    assert len(botones) >= 5, 'faltan botones en la barra: %d' % len(botones)
    activos = [b for b in botones if 'cx-primary-grad' in b]
    assert len(activos) == 1, 'tiene que haber UNA sola pestaña marcada, hay %d' % len(activos)
    for b in botones:
        if b in activos:
            continue
        assert 'background:var(--cx-card)' in b, 'una pestaña apagada con color propio: %s' % b[:120]
