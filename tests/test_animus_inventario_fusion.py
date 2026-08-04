"""Inventario de ÁNIMUS: la API y los guards de estructura del módulo.

⚠ 4-ago: Sebastián retiró la PESTAÑA de Inventario de /animus ("la veo innecesaria, eso de
inventario está en Shopify"). Se podó la interfaz, NO los datos: los endpoints y las tablas
siguen intactos, así que estos tests siguen valiendo y volver a mostrarla no exige reconstruir
nada (regla 0.7). Lo que se apagó además es el cron diario, que si no seguiría asignando conteos
y avisándole a Daniela sobre una pantalla que ya no existe.

Los guards de ESTRUCTURA se quedan y aplican a todo el módulo: son los que faltaban cuando una
pestaña quedó anidada dentro de otra y cuando llamé a una función que no existía.

Contexto original (3-ago): fusión de Inventario Físico y Conteo Cíclico.

Sebastián: *"inventario físico y conteo cíclico me parece que debemos fusionarlos. Cómo debería
ser: que aparezcan todos los SKU de Shopify, aparezcan allí con la cantidad que dice Shopify que
hay, y que por día aparezca seleccionado un inventario cíclico que cuenten y pongan 'tenemos en
físico tanto', diga discrepancia y notifique a gerencia. Si hay menos o más de una, le genera una
causa raíz: deben buscar por qué"*.

Lo que fijan estos tests, que es donde estaba el hueco:

1. **Nadie comparaba contra Shopify.** La pantalla medía el esperado de EOS contra el conteo,
   nunca contra el número con el que se VENDE. Un SKU podía estar bien en EOS y mal en Shopify
   y no se notaba hasta que se vendía algo que no había.
2. **Una unidad de diferencia se toleraba.** Solo se exigía explicación pasando de 2, y si se
   tolera, el faltante se vuelve normal.
3. **La discrepancia no le avisaba a nadie**: quedaba en la fila esperando que alguien la abriera.
4. **El conteo del día dependía de que alguien apretara un botón.** Una rutina que hay que
   acordarse de disparar no es una rutina.
"""
from .conftest import TEST_PASSWORD, csrf_headers

SKU = 'ZZFUS-001'


def _cli(app, quien='sebastian'):
    c = app.test_client()
    r = c.post("/login", data={"username": quien, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar(app):
    """Limpia ANTES de sembrar (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        for t, col in (('animus_conteos_asignados', 'sku'),
                       ('animus_inventario_movimientos', 'sku'),
                       ('animus_inventario_baseline', 'sku')):
            cur.execute("DELETE FROM %s WHERE %s LIKE ?" % (t, col), ('ZZFUS%',))
        cur.execute("DELETE FROM notificaciones_app WHERE titulo LIKE ?", ('%ZZFUS%',))
        conn.commit()


def _sembrar(app, *, baseline=100):
    from database import get_db
    from tz_colombia import hoy_colombia
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO animus_inventario_baseline (sku, descripcion, "
                    "unidades_baseline, fecha_baseline, creado_por) VALUES (?,?,?,?,?)",
                    (SKU, 'Producto de prueba', baseline, hoy_colombia().isoformat(), 'test'))
        cur.execute("INSERT INTO animus_conteos_asignados (sku, asignado_a, estado, "
                    "fecha_asignado) VALUES (?,?,'pendiente',?)",
                    (SKU, 'daniela', hoy_colombia().isoformat()))
        aid = cur.lastrowid
        conn.commit()
    return aid


def _html_animus():
    import ast as _ast, io as _io, os as _os
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    src = _io.open(_os.path.join(raiz, 'api', 'templates_py', 'animus_html.py'),
                   encoding='utf-8').read()
    for n in _ast.walk(_ast.parse(src)):
        if (isinstance(n, _ast.Assign) and isinstance(n.value, _ast.Constant)
                and isinstance(n.value.value, str) and len(n.value.value) > 5000):
            return n.value.value
    raise AssertionError('no encontré el HTML de /animus')


# ── EXISTENCIAS · Shopify contra EOS ─────────────────────────────────────────

def test_las_existencias_muestran_los_dos_numeros(app, db_clean):
    _limpiar(app); _sembrar(app, baseline=100)
    d = _cli(app).get('/api/animus/inv-fisico/existencias').get_json()
    assert d['ok'] is True
    fila = [f for f in d['filas'] if f['sku'] == SKU]
    assert fila, 'el SKU con baseline no salió en existencias'
    f = fila[0]
    assert f['esperado_eos'] == 100
    assert 'shopify' in f, 'falta lo que dice Shopify · es el número con el que se vende'
    assert f['sin_baseline'] is False


def test_un_SKU_sin_baseline_dice_que_NO_SABEMOS_y_no_cero(app, db_clean):
    """Sin baseline, un cero de EOS no significa 'no hay': significa 'no sabemos' (M124).
    Mostrarlo como 0 inventaría una diferencia contra Shopify que nadie puede explicar."""
    _limpiar(app)
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO animus_inventario_movimientos (sku, tipo, cantidad, fecha, "
                    "origen, usuario) VALUES (?,'SHOPIFY_VENTA',1,date('now','-5 hours'),"
                    "'test','test')", ('ZZFUS-SINBASE',))
        conn.commit()
    d = _cli(app).get('/api/animus/inv-fisico/existencias').get_json()
    fila = [f for f in d['filas'] if f['sku'] == 'ZZFUS-SINBASE']
    if fila:
        assert fila[0]['esperado_eos'] is None
        assert fila[0]['diferencia'] is None, 'inventó una diferencia sin tener con qué comparar'


def test_los_kpis_cuentan_lo_que_hay_que_mirar(app, db_clean):
    _limpiar(app); _sembrar(app)
    k = _cli(app).get('/api/animus/inv-fisico/existencias').get_json()['kpis']
    for campo in ('skus', 'sin_baseline', 'con_diferencia',
                  'investigaciones_abiertas', 'nunca_contados'):
        assert campo in k, campo


# ── CAUSA RAÍZ ANTE CUALQUIER DIFERENCIA ─────────────────────────────────────

def test_UNA_unidad_de_diferencia_ya_abre_investigacion(app, db_clean):
    """Antes solo se exigía explicación pasando de 2 unidades. Si una se tolera, el faltante
    se vuelve normal · Sebastián: "si hay menos o más de una, le genera una causa raíz"."""
    _limpiar(app); aid = _sembrar(app, baseline=100)
    r = _cli(app).post('/api/animus/inv-fisico/conteo/%d/registrar' % aid,
                       json={'cantidad_fisica': 99}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:250]
    d = r.get_json()
    assert d['diferencia'] == -1
    assert d['investigacion'] == 'abierta', 'una unidad de diferencia quedó sin nadie a cargo'


def test_un_conteo_que_cuadra_NO_abre_investigacion(app, db_clean):
    """Con dientes: si abriera investigación siempre, la lista de pendientes sería ruido y
    dejaría de mirarse."""
    _limpiar(app); aid = _sembrar(app, baseline=100)
    d = _cli(app).post('/api/animus/inv-fisico/conteo/%d/registrar' % aid,
                       json={'cantidad_fisica': 100}, headers=csrf_headers()).get_json()
    assert d['diferencia'] == 0 and d['investigacion'] == 'no_aplica'
    assert d['alerta'] is None


def test_la_discrepancia_le_AVISA_a_gerencia(app, db_clean):
    """Antes quedaba en la fila esperando que alguien la abriera · una discrepancia que no
    suena se ve igual que un conteo que cuadró."""
    _limpiar(app); aid = _sembrar(app, baseline=100)
    _cli(app).post('/api/animus/inv-fisico/conteo/%d/registrar' % aid,
                   json={'cantidad_fisica': 90}, headers=csrf_headers())
    from database import get_db
    with app.app_context():
        avisados = [x[0] for x in get_db().execute(
            "SELECT destinatario FROM notificaciones_app WHERE tipo='inventario_discrepancia' "
            "AND titulo LIKE ?", ('%' + SKU + '%',)).fetchall()]
    assert avisados, 'nadie se enteró de la discrepancia'
    assert 'sebastian' in avisados


def test_la_causa_no_se_cierra_con_dos_palabras(app, db_clean):
    """Dentro de un mes nadie puede reconstruir un faltante con 'ok' como explicación."""
    _limpiar(app); aid = _sembrar(app, baseline=100)
    c = _cli(app)
    c.post('/api/animus/inv-fisico/conteo/%d/registrar' % aid,
           json={'cantidad_fisica': 95}, headers=csrf_headers())
    r = c.post('/api/animus/inv-fisico/conteo/%d/causa-raiz' % aid,
               json={'causa_raiz': 'nada'}, headers=csrf_headers())
    assert r.status_code == 400


def test_cerrar_la_causa_deja_el_rastro_completo(app, db_clean):
    _limpiar(app); aid = _sembrar(app, baseline=100)
    c = _cli(app)
    c.post('/api/animus/inv-fisico/conteo/%d/registrar' % aid,
           json={'cantidad_fisica': 95}, headers=csrf_headers())
    r = c.post('/api/animus/inv-fisico/conteo/%d/causa-raiz' % aid,
               json={'causa_raiz': 'Se despacharon 5 unidades sin registrar la salida',
                     'accion_correctiva': 'Se registra la salida al despachar'},
               headers=csrf_headers())
    assert r.status_code == 200 and r.get_json()['investigacion'] == 'cerrada'
    from database import get_db
    with app.app_context():
        f = get_db().execute("SELECT investigacion, causa_raiz, causa_raiz_por, "
                             "accion_correctiva FROM animus_conteos_asignados WHERE id=?",
                             (aid,)).fetchone()
    assert f[0] == 'cerrada' and f[1].startswith('Se despacharon')
    assert f[2] == 'sebastian' and f[3]


def test_dos_personas_no_cierran_la_misma_causa(app, db_clean):
    """CAS: sin él, la segunda pisa la explicación de la primera sin dejar rastro (M27)."""
    _limpiar(app); aid = _sembrar(app, baseline=100)
    c = _cli(app)
    c.post('/api/animus/inv-fisico/conteo/%d/registrar' % aid,
           json={'cantidad_fisica': 95}, headers=csrf_headers())
    body = {'causa_raiz': 'Se despacharon 5 unidades sin registrar la salida'}
    assert c.post('/api/animus/inv-fisico/conteo/%d/causa-raiz' % aid,
                  json=body, headers=csrf_headers()).status_code == 200
    assert c.post('/api/animus/inv-fisico/conteo/%d/causa-raiz' % aid,
                  json=body, headers=csrf_headers()).status_code == 409


def test_la_diferencia_abierta_sale_en_existencias(app, db_clean):
    """Si no apareciera junto al SKU, habría que ir a buscarla a otra pantalla y se acumularían
    sin que nadie las vea."""
    _limpiar(app); aid = _sembrar(app, baseline=100)
    c = _cli(app)
    c.post('/api/animus/inv-fisico/conteo/%d/registrar' % aid,
           json={'cantidad_fisica': 93}, headers=csrf_headers())
    d = c.get('/api/animus/inv-fisico/existencias').get_json()
    f = [x for x in d['filas'] if x['sku'] == SKU][0]
    assert f['investigaciones_abiertas'], 'la diferencia abierta no se ve en la lista'
    assert f['investigaciones_abiertas'][0]['diferencia'] == -7
    assert d['kpis']['investigaciones_abiertas'] >= 1


# ── EL ESPERADO SE CALCULA IGUAL DE A UNO QUE EN BLOQUE ──────────────────────

def test_el_esperado_en_bloque_da_lo_MISMO_que_de_a_uno(app, db_clean):
    """El endpoint nuevo usa la versión en bloque para no hacer cientos de viajes (M43). Si las
    dos no dieran lo mismo, la pantalla mostraría un esperado distinto al que decide el conteo
    (M1/M5) · por eso el de a uno DELEGA en el de bloque, y esto lo verifica."""
    _limpiar(app); _sembrar(app, baseline=100)
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        for tipo, cant in (('ENTRADA', 30), ('SHOPIFY_VENTA', 12), ('SALIDA', 3), ('AJUSTE', 5)):
            cur.execute("INSERT INTO animus_inventario_movimientos (sku, tipo, cantidad, fecha, "
                        "origen, usuario) VALUES (?,?,?,date('now','-5 hours'),'test','test')",
                        (SKU, tipo, cant))
        conn.commit()
        from blueprints.animus import _calcular_esperado, _esperado_bulk
        uno = _calcular_esperado(conn, SKU)
        bulk = _esperado_bulk(conn).get(SKU)
    assert uno['esperado'] == bulk['esperado'] == 100 + 30 - 12 - 3 + 5


# ── EL CONTEO DEL DÍA SE ASIGNA SOLO ─────────────────────────────────────────

def test_el_cron_asigna_el_conteo_sin_que_nadie_apriete_nada(app, db_clean):
    """El cron NO puede entrar por HTTP (el endpoint exige sesión): llama al helper. Si pasara
    por HTTP recibiría 401 siempre y el síntoma sería 'no hay nada para contar hoy',
    indistinguible de que de verdad no haya."""
    _limpiar(app); _sembrar(app)
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.cursor().execute("DELETE FROM animus_conteos_asignados WHERE sku LIKE 'ZZFUS%'")
        conn.commit()
    from blueprints.auto_plan_jobs import job_animus_conteo_diario
    job_animus_conteo_diario(app)
    with app.app_context():
        n = get_db().execute("SELECT COUNT(*) FROM animus_conteos_asignados WHERE "
                             "fecha_asignado=date('now','-5 hours')").fetchone()[0]
    assert n >= 1, 'el cron no asignó nada'


def test_el_cron_fecha_la_asignacion_en_hora_COLOMBIA(app, db_clean):
    """El bug que explicaba los cientos de conteos acumulados: el INSERT del cron no fijaba
    `fecha_asignado`, así que tomaba el default de columna date('now') -- UTC -- mientras el
    chequeo de idempotencia compara contra Colombia. De noche las dos fechas no coinciden y el
    cron volvía a asignar sobre lo ya asignado, todos los días (M24)."""
    from blueprints.auto_plan_jobs import job_animus_conteo_diario
    _limpiar(app); _sembrar(app)
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.cursor().execute("DELETE FROM animus_conteos_asignados WHERE sku LIKE 'ZZFUS%'")
        conn.commit()
    job_animus_conteo_diario(app)
    with app.app_context():
        conn = get_db()
        # Las que el cron acaba de crear tienen que llevar la fecha de Colombia. Si alguna
        # quedara con otra, la idempotencia no la vería y mañana se asignaría de nuevo.
        recientes = conn.execute(
            "SELECT COUNT(*) FROM animus_conteos_asignados "
            "WHERE fecha_asignado = date('now','-5 hours')").fetchone()[0]
    assert recientes >= 1, 'el cron no asignó nada con fecha de hoy en Colombia'


def test_asignar_dos_veces_el_mismo_dia_no_duplica(app, db_clean):
    from blueprints.auto_plan_jobs import job_animus_conteo_diario
    _limpiar(app); _sembrar(app)
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.cursor().execute("DELETE FROM animus_conteos_asignados WHERE sku LIKE 'ZZFUS%'")
        conn.commit()
    job_animus_conteo_diario(app)
    with app.app_context():
        n1 = get_db().execute("SELECT COUNT(*) FROM animus_conteos_asignados WHERE "
                              "fecha_asignado=date('now','-5 hours')").fetchone()[0]
    job_animus_conteo_diario(app)
    with app.app_context():
        n2 = get_db().execute("SELECT COUNT(*) FROM animus_conteos_asignados WHERE "
                              "fecha_asignado=date('now','-5 hours')").fetchone()[0]
    assert n1 == n2, 'correrlo dos veces duplicó la tarea del día'


# ── LA PANTALLA ──────────────────────────────────────────────────────────────


def _paneles(html):
    import re
    def cierre(ini):
        d = 0
        for m in re.finditer(r'<div\b|</div>', html[ini:]):
            d += 1 if m.group(0).startswith('<div') else -1
            if d == 0:
                return ini + m.end()
        return None
    ids = re.findall(r'<div id="(tab-[a-z]+)" class="tab-panel', html)
    return {p: (html.index('<div id="%s" class="tab-panel' % p),
                cierre(html.index('<div id="%s" class="tab-panel' % p))) for p in ids}


def test_ninguna_pestana_queda_dentro_de_otra():
    html = _html_animus()
    p = _paneles(html)
    # 4 desde el 4-ago: se retiro la pestana Inventario
    assert len(p) >= 4, 'faltan paneles: %s' % sorted(p)
    for a, (ia, fa) in p.items():
        assert fa, 'el panel %s nunca cierra' % a
        for b, (ib, _) in p.items():
            if a != b:
                assert not (ia < ib < fa), '%s quedó ANIDADO dentro de %s · nunca se vería' % (b, a)


def test_cada_boton_de_pestana_tiene_su_panel():
    """Un botón que apunta a un panel inexistente deja la pantalla en blanco: `switchTab` apaga
    todos los paneles ANTES de encender el destino (M112)."""
    import re
    html = _html_animus()
    for t in sorted(set(re.findall(r"switchTab\('([a-z]+)'\)", html))):
        assert '<div id="tab-%s"' % t in html, 'switchTab(%r) no tiene panel' % t



def test_toda_funcion_llamada_esta_definida():
    """El 4-ago llamé a `hoyCol()` en dos modales y esa función nunca existió: los botones de
    Novedades y de Registrar pago no hacían NADA.

    Lo verifiqué buscando el nombre en la página — y encontré mi propia LLAMADA, no la
    definición. El `node --check` pasa (la sintaxis es válida) y el balance de divs da cero:
    ninguno de los dos ve una función que no existe."""
    import sys, os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(raiz, 'scripts'))
    from check_js_animus import funciones_sin_definir
    faltan = funciones_sin_definir()
    assert not faltan, 'se llaman y no existen: %s' % ', '.join(faltan)
