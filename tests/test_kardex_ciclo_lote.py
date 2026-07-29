"""El kardex sabe lo que pasa ADENTRO del lote (29-jul · mig 396).

Sebastián: *"cuando pesan las materias primas que tengan la posibilidad de pesar lo que
queda antes de devolverlo a inventario, así queda una forma de inventario cíclico sin ser
obligatorio"* y *"si quieren usar una materia prima que saben hay menos y completar, que
puedan adicionarla y él descuente todo"*.

Los dos son el mismo problema: la MP salía por FEFO al arrancar y ahí se acababa la
conversación. Lo que sobraba, lo que se agregaba y lo que volvía no movía un solo
movimiento, así que entre producción y producción el stock era una estimación.

⚠ Y lo más grave no era una función faltante: `ebr_ajustes_mp` YA existía y sólo dejaba
una NOTA. La trietanolamina que el operario agrega para corregir pH quedaba escrita en el
legajo y NUNCA salía del stock. Invisible, porque el legajo se ve completo.
"""
from .conftest import TEST_PASSWORD, csrf_headers

MP = 'ZZ-MP-CICLO'
LOTE_MP = 'ZZL-001'
LOTE_EBR = 'ZZ-EBR-CICLO'


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _sembrar(app, stock_g=1000.0):
    """MP con stock en UN lote + un legajo en proceso. Limpia ANTES (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM movimientos WHERE material_id=?", (MP,))
        f = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (LOTE_EBR,)).fetchone()
        if f:
            cu.execute("DELETE FROM ebr_devoluciones_mp WHERE ebr_id=?", (f[0],))
            cu.execute("DELETE FROM ebr_ajustes_mp WHERE ebr_id=?", (f[0],))
            cu.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (f[0],))
        cu.execute(
            "INSERT INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
            "VALUES (?,?,?,1) ON CONFLICT (codigo_mp) DO UPDATE SET activo=1",
            (MP, 'TEST INCI', 'MP de prueba ciclo'))
        cu.execute(
            "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, "
            "lote, fecha_vencimiento, estado_lote) "
            "VALUES (?,?,?, 'Entrada', '2026-07-01T08:00:00', ?, '2027-12-31', 'VIGENTE')",
            (MP, 'MP de prueba ciclo', stock_g, LOTE_MP))
        cu.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
            "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (1, 1, LOTE_EBR, LOTE_EBR, 'en_proceso', 'fabricacion', 'sebastian',
             '2026-07-29T10:00:00', 1000))
        eid = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (LOTE_EBR,)).fetchone()[0]
        conn.commit()
    return eid


def _stock(app):
    """Stock canónico por el CASE de la regla #4."""
    from database import get_db
    with app.app_context():
        r = get_db().cursor().execute(
            "SELECT COALESCE(SUM(CASE "
            "  WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad "
            "  WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -cantidad ELSE 0 END),0) "
            "FROM movimientos WHERE material_id=? "
            "AND UPPER(COALESCE(estado_lote,'')) NOT IN "
            "('CUARENTENA','CUARENTENA_EXTENDIDA','VENCIDO','RECHAZADO','AGOTADO','BLOQUEADO')",
            (MP,)).fetchone()
    return float(r[0] or 0)


# ══ el agujero de inventario que estaba abierto ═════════════════════════════════

def test_adicionar_MP_en_el_lote_DESCUENTA_del_stock(app, db_clean):
    """Era una NOTA: la MP agregada para corregir pH quedaba en el legajo y nunca salía
    del stock. El sistema creía que seguía ahí."""
    eid = _sembrar(app, 1000)
    assert _stock(app) == 1000
    r = _login(app).post('/api/brd/ebr/%d/ajustes-mp' % eid, headers=_h(), json={
        'material': 'MP de prueba ciclo', 'material_id': MP,
        'cantidad_g': 120, 'motivo': 'ajuste de pH'})
    assert r.status_code == 201, r.data[:300]
    j = r.get_json()
    assert j['descontado'] is True, 'el ajuste NO descontó: sigue siendo una nota'
    assert j['movimientos'], 'no quedó movimiento de kardex'
    assert _stock(app) == 880, 'el stock no bajó: %r' % _stock(app)


def test_el_descuento_sale_del_LOTE_correcto(app, db_clean):
    """Se descuenta por el FEFO canónico, no de un stock global sin lote: si no, se pierde
    la trazabilidad de qué lote de MP entró al producto."""
    from database import get_db
    eid = _sembrar(app, 1000)
    _login(app).post('/api/brd/ebr/%d/ajustes-mp' % eid, headers=_h(), json={
        'material': 'MP', 'material_id': MP, 'cantidad_g': 50, 'motivo': 'pH'})
    with app.app_context():
        r = get_db().cursor().execute(
            "SELECT lote, cantidad, tipo FROM movimientos WHERE material_id=? AND tipo='Salida'",
            (MP,)).fetchone()
    assert r, 'no hay Salida'
    assert r[0] == LOTE_MP, 'la Salida quedó sin lote (%r): se pierde la trazabilidad' % r[0]
    assert r[1] == 50


def test_sin_codigo_de_bodega_NO_adivina_a_que_material_imputar(app, db_clean):
    """El nombre es texto libre. Descontar por nombre sería descontar la molécula
    equivocada (M19: matching difuso = material equivocado). Se registra la nota y se
    declara que no descontó, en vez de imputarle a alguien."""
    eid = _sembrar(app, 1000)
    r = _login(app).post('/api/brd/ebr/%d/ajustes-mp' % eid, headers=_h(), json={
        'material': 'Trietanolamina', 'cantidad_g': 30, 'motivo': 'pH'})
    assert r.status_code == 201
    assert r.get_json()['descontado'] is False, 'descontó adivinando el material'
    assert _stock(app) == 1000, 'tocó el stock sin saber a qué código imputarlo'


def test_el_ajuste_queda_auditado_con_sus_movimientos(app, db_clean):
    from database import get_db
    eid = _sembrar(app, 1000)
    _login(app).post('/api/brd/ebr/%d/ajustes-mp' % eid, headers=_h(), json={
        'material': 'MP', 'material_id': MP, 'cantidad_g': 40, 'motivo': 'pH'})
    with app.app_context():
        r = get_db().cursor().execute(
            "SELECT despues FROM audit_log WHERE accion='AJUSTE_MP_EBR' AND registro_id=? "
            "ORDER BY id DESC LIMIT 1", (str(eid),)).fetchone()
    assert r and 'movimientos' in (r[0] or ''), 'el rastro no liga el ajuste a su movimiento'


# ══ la devolución del sobrante ══════════════════════════════════════════════════

def test_devolver_el_sobrante_SUMA_al_stock(app, db_clean):
    """Lo que vuelve al estante tiene que volver al kardex: si no, el stock queda
    subestimado y se compra de más."""
    eid = _sembrar(app, 1000)
    r = _login(app).post('/api/brd/ebr/%d/devolucion-mp' % eid, headers=_h(), json={
        'material_id': MP, 'lote': LOTE_MP, 'cantidad_g': 250})
    assert r.status_code == 201, r.data[:300]
    assert _stock(app) == 1250, 'la devolución no entró al kardex: %r' % _stock(app)
    j = r.get_json()
    assert j['stock_antes_g'] == 1000 and j['stock_despues_g'] == 1250


def test_la_devolucion_CONSERVA_el_vencimiento_del_lote(app, db_clean):
    """Si la Entrada de vuelta pierde la fecha, el lote devuelto queda sin vencimiento:
    el cron de vencidos y el FEFO dejan de verlo y vuelve a producción material vencido
    (M25). Es el error silencioso más caro de una devolución."""
    from database import get_db
    eid = _sembrar(app, 1000)
    _login(app).post('/api/brd/ebr/%d/devolucion-mp' % eid, headers=_h(), json={
        'material_id': MP, 'lote': LOTE_MP, 'cantidad_g': 100})
    with app.app_context():
        r = get_db().cursor().execute(
            "SELECT fecha_vencimiento FROM movimientos WHERE material_id=? AND tipo='Entrada' "
            "ORDER BY id DESC LIMIT 1", (MP,)).fetchone()
    assert (r[0] or '') == '2027-12-31', 'la devolución perdió el vencimiento: %r' % (r[0],)


def test_una_devolucion_de_cero_no_es_un_hecho(app, db_clean):
    """El trigger de PG rechaza cantidad <= 0 y con razón: un 0 es un formulario mal
    llenado, no un movimiento (M18)."""
    eid = _sembrar(app, 1000)
    r = _login(app).post('/api/brd/ebr/%d/devolucion-mp' % eid, headers=_h(), json={
        'material_id': MP, 'lote': LOTE_MP, 'cantidad_g': 0})
    assert r.status_code == 400
    assert r.get_json().get('codigo') == 'CANTIDAD_INVALIDA'
    assert _stock(app) == 1000


def test_no_se_devuelve_a_un_lote_liberado(app, db_clean):
    from database import get_db
    eid = _sembrar(app, 1000)
    with app.app_context():
        conn = get_db()
        conn.cursor().execute("UPDATE ebr_ejecuciones SET estado='liberado' WHERE id=?", (eid,))
        conn.commit()
    r = _login(app).post('/api/brd/ebr/%d/devolucion-mp' % eid, headers=_h(), json={
        'material_id': MP, 'lote': LOTE_MP, 'cantidad_g': 100})
    assert r.status_code == 409
    assert r.get_json().get('codigo') == 'LEGAJO_INMUTABLE'


# ══ el conteo cíclico, que es de regalo y NO obligatorio ════════════════════════

def test_sin_declarar_el_fisico_NO_se_inventa_una_discrepancia(app, db_clean):
    """Sebastián lo pidió *"sin ser obligatorio"*. Si el operario no cuenta, no hay conteo:
    un conteo inventado es peor que no contar (M109: sin dato no se inventa un default)."""
    eid = _sembrar(app, 1000)
    r = _login(app).post('/api/brd/ebr/%d/devolucion-mp' % eid, headers=_h(), json={
        'material_id': MP, 'lote': LOTE_MP, 'cantidad_g': 200})
    assert r.get_json()['discrepancia_g'] is None, 'inventó una discrepancia sin conteo'


def test_declarar_el_fisico_da_un_conteo_ciclico_gratis(app, db_clean):
    """El kardex dirá 1.200 tras devolver 200. Si el operario cuenta 1.150 físicos,
    aparecen 50 g de faltante SIN que nadie haga una jornada de conteo."""
    eid = _sembrar(app, 1000)
    r = _login(app).post('/api/brd/ebr/%d/devolucion-mp' % eid, headers=_h(), json={
        'material_id': MP, 'lote': LOTE_MP, 'cantidad_g': 200,
        'fisico_declarado_g': 1150})
    assert r.status_code == 201, r.data[:300]
    assert r.get_json()['discrepancia_g'] == -50, (
        'no detectó el faltante: %r' % r.get_json()['discrepancia_g'])


def test_el_conteo_que_cuadra_da_cero(app, db_clean):
    eid = _sembrar(app, 1000)
    r = _login(app).post('/api/brd/ebr/%d/devolucion-mp' % eid, headers=_h(), json={
        'material_id': MP, 'lote': LOTE_MP, 'cantidad_g': 200,
        'fisico_declarado_g': 1200})
    assert r.get_json()['discrepancia_g'] == 0


def test_la_devolucion_queda_auditada(app, db_clean):
    from database import get_db
    eid = _sembrar(app, 1000)
    _login(app).post('/api/brd/ebr/%d/devolucion-mp' % eid, headers=_h(), json={
        'material_id': MP, 'lote': LOTE_MP, 'cantidad_g': 200, 'fisico_declarado_g': 1150})
    with app.app_context():
        r = get_db().cursor().execute(
            "SELECT usuario, despues FROM audit_log WHERE accion='DEVOLVER_MP_SOBRANTE' "
            "ORDER BY id DESC LIMIT 1").fetchone()
    assert r and r[0] == 'sebastian'
    assert 'discrepancia_g' in (r[1] or ''), 'el rastro no guarda el resultado del conteo'


def test_la_migracion_396_no_borra_nada(app, db_clean):
    from database import MIGRATIONS
    stmts = ' '.join(next(s for v, _, s in MIGRATIONS if v == 396))
    assert 'ebr_devoluciones_mp' in stmts
    for col in ('material_id', 'lote', 'mov_id', 'descontado_at_utc'):
        assert col in stmts, 'la mig 396 no agrega %s a ebr_ajustes_mp' % col
    assert 'DELETE' not in stmts.upper() and 'DROP' not in stmts.upper()


# ══ el granel real viaja SOLO de fabricacion a envasado ═════════════════════════

LOTE_FIS = 'ZZ-LOTE-FISICO'


def _op_y_of(app, *, real_g=17000.0, densidad=0.916):
    """Un lote fisico con su legajo de FABRICACION cerrado (peso real del granel) y su
    legajo de ENVASADO. La llave del OF va sufijada y el lote fisico vive en
    `lote_codigo` (M10)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        for k in (LOTE_FIS, LOTE_FIS + '-OF'):
            f = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (k,)).fetchone()
            if f:
                cu.execute("DELETE FROM ebr_envasado_unidades WHERE ebr_id=?", (f[0],))
                cu.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (f[0],))
        cu.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
            "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, cantidad_real_g, "
            "densidad_g_ml) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (1, 1, LOTE_FIS, LOTE_FIS, 'completado', 'fabricacion', 'sebastian',
             '2026-07-29T08:00:00', 17000, real_g, densidad))
        cu.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
            "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (1, 1, LOTE_FIS + '-OF', LOTE_FIS, 'en_proceso', 'envasado', 'sebastian',
             '2026-07-29T10:00:00', 17000))
        eof = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?",
                         (LOTE_FIS + '-OF',)).fetchone()[0]
        conn.commit()
    return eof


def _conc(cli, eid):
    return cli.get('/api/brd/ebr/%d/vista-completa' % eid).get_json().get('conciliacion_granel')


def test_el_envasado_hereda_el_granel_real_de_fabricacion(app, db_clean):
    """Sebastián: *"al final de la producción que aparezca peso total del granel, así en
    envasado ya va con un teórico"*. Sin el puente, el envasado esperaba que alguien
    tecleara el granel -- y lo tecleado es lo primero que queda viejo."""
    eof = _op_y_of(app)
    c = _conc(_login(app), eof)
    assert c and c['aplica']
    assert c['origen_granel'] == 'fabricacion', 'no vino del lote de fabricación'
    assert abs(c['disponible_ml'] - 18558.95) < 0.5, (
        '17.000 g / 0,916 g/mL = 18.558,95 mL · dio %r' % c['disponible_ml'])


def test_el_teorico_de_unidades_sale_del_granel_heredado(app, db_clean):
    """Es para lo que sirve el teórico: cuántas unidades DEBERÍAN salir de ese granel."""
    from database import get_db
    eof = _op_y_of(app)
    with app.app_context():
        conn = get_db()
        conn.cursor().execute(
            "INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, volumen_ml, "
            "unidades, registrado_por, registrado_at_utc) VALUES (?,?,?,?,?,datetime('now','utc'))",
            (eof, 'ENV-30', 30.0, 600, 'sebastian'))
        conn.commit()
    c = _conc(_login(app), eof)
    assert c['unidades_teoricas'] == 618, (
        '18.558,95 mL / 30 mL = 618 unidades teóricas · dio %r' % c['unidades_teoricas'])
    assert c['rendimiento_uds_pct'] == 97.09, (
        '600 de 618 = 97,09%% · dio %r' % c['rendimiento_uds_pct'])


def test_con_varias_presentaciones_NO_se_inventa_un_teorico_por_presentacion(app, db_clean):
    """Repartir el granel entre presentaciones exige un criterio que nadie definió.
    Se declara el rendimiento en VOLUMEN, que sí vale siempre, y no se parte (M8)."""
    from database import get_db
    eof = _op_y_of(app)
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        for cod, vol, uds in (('ENV-10', 10.0, 500), ('ENV-30', 30.0, 400)):
            cu.execute(
                "INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, volumen_ml, "
                "unidades, registrado_por, registrado_at_utc) "
                "VALUES (?,?,?,?,?,datetime('now','utc'))", (eof, cod, vol, uds, 'sebastian'))
        conn.commit()
    c = _conc(_login(app), eof)
    assert c['unidades_teoricas'] is None, 'inventó un teórico repartiendo el granel'
    assert c['rendimiento_ml_pct'] is not None, 'el rendimiento en volumen sí tiene que estar'
    assert abs(c['rendimiento_ml_pct'] - 91.6) < 0.5, (
        '17.000 mL envasados de 18.558,95 = 91,6%% · dio %r' % c['rendimiento_ml_pct'])


def test_el_legajo_con_su_PROPIO_granel_no_lo_pisa_el_puente(app, db_clean):
    """Si el envasado ya tiene su granel cargado, manda ese: el puente es un fallback,
    no una sobreescritura."""
    from database import get_db
    eof = _op_y_of(app)
    with app.app_context():
        conn = get_db()
        conn.cursor().execute(
            "UPDATE ebr_ejecuciones SET ml_envasable=5000, densidad_g_ml=0.916 WHERE id=?", (eof,))
        conn.commit()
    c = _conc(_login(app), eof)
    assert c['disponible_ml'] == 5000, 'el puente pisó el dato propio del legajo'
    assert c['origen_granel'] == 'legajo'
