"""El granel que entró al envasado tiene que terminar EXPLICADO (28-jul).

El caso que lo motivó es de la OF-2026-77 real: entraron 12.658,95 mL de granel y se
envasaron 100 unidades de 10 mL = 1.000 mL. Los otros 11.658,95 mL no los explicaba
ningún registro del legajo. Puede ser perfectamente legítimo -queda granel en bodega
para otra orden- pero eso es justo lo que una auditoría INVIMA pregunta y el legajo no
contestaba: el granel que entró, ¿en qué terminó?

La cuenta es    entró = envasado + remanente + diferencia sin explicar
y todo se DERIVA salvo el remanente, que es lo único que hay que ir a pesar (M71).
"""
from .conftest import TEST_PASSWORD, csrf_headers


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


LOTE = 'ZZ-EBR-GRANEL'


def _ebr(app, *, ml_envasable=12658.95, densidad=0.916, estado='en_proceso', fase='envasado'):
    """Legajo de envasado con la magnitud REAL de la OF-2026-77.

    Limpia ANTES de sembrar (M103): `ebr_ejecuciones.lote` es UNIQUE (M10), así que un
    lote fijo revienta a la segunda corrida si se limpia sólo al final.
    """
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        fila = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (LOTE,)).fetchone()
        if fila:
            cu.execute("DELETE FROM ebr_envasado_unidades WHERE ebr_id=?", (fila[0],))
            cu.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (fila[0],))
        cu.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, estado, "
            "fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, cantidad_real_g, "
            "densidad_g_ml, ml_envasable) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (1, 1, LOTE, LOTE, estado, fase, 'sebastian', '2026-07-28T10:00:00',
             17000, 17000, densidad, ml_envasable))
        eid = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (LOTE,)).fetchone()[0]
        conn.commit()
    return eid


def _unidades(app, eid, codigo, volumen_ml, unidades):
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute(
            "INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, etiqueta, volumen_ml, "
            "unidades, registrado_por, registrado_at_utc) VALUES (?,?,?,?,?,?,datetime('now','utc')) "
            "ON CONFLICT(ebr_id, presentacion_codigo) DO UPDATE SET unidades=excluded.unidades, "
            "volumen_ml=excluded.volumen_ml",
            (eid, codigo, 'x%s mL' % volumen_ml, volumen_ml, unidades, 'sebastian'))
        conn.commit()


def _conc(app, cli, eid):
    r = cli.get('/api/brd/ebr/%d/vista-completa' % eid)
    assert r.status_code == 200, r.data[:300]
    return r.get_json().get('conciliacion_granel')


# ══ la cuenta ═══════════════════════════════════════════════════════════════════

def test_el_granel_sin_explicar_queda_a_la_vista(app, db_clean):
    """El caso OF-2026-77 tal cual: 12.658,95 entran, 1.000 salen envasados.

    Sin declarar remanente, la conciliación NO puede decir que cuadra: los 11.658,95
    restantes son exactamente el número que la auditoría pregunta.
    """
    eid = _ebr(app)
    _unidades(app, eid, 'ENV-COLGLOSS-15-01', 10.0, 100)
    cli = _login(app)
    c = _conc(app, cli, eid)
    assert c and c['aplica']
    assert c['disponible_ml'] == 12658.95
    assert c['envasado_ml'] == 1000.0, 'Σ(uds × mL) mal: %r' % c['envasado_ml']
    assert c['diferencia_ml'] == 11658.95, 'no expone el granel sin explicar: %r' % c['diferencia_ml']
    assert c['falta_remanente'] is True
    assert c['completa'] is False
    assert c['cuadra'] is False, 'no puede cuadrar sin remanente declarado'


def test_al_declarar_el_remanente_la_cuenta_cierra(app, db_clean):
    """El remanente se PESA (gramos) y los mL se derivan con la densidad."""
    eid = _ebr(app)
    _unidades(app, eid, 'ENV-COLGLOSS-15-01', 10.0, 100)
    cli = _login(app)
    # 11.658,95 mL de remanente × 0,916 g/mL = 10.679,6 g pesados en balanza
    r = cli.post('/api/brd/ebr/%d/remanente-granel' % eid, headers=_h(), json={
        'remanente_g': 10679.6, 'destino': 'otra_orden',
        'observaciones': 'Queda en bodega para la siguiente orden del mismo lote'})
    assert r.status_code == 200, r.data[:300]
    c = r.get_json()['conciliacion']
    assert c['remanente_g'] == 10679.6
    assert abs(c['remanente_ml'] - 11658.95) < 0.5, 'mal derivado a mL: %r' % c['remanente_ml']
    assert abs(c['diferencia_ml']) < 1.0, 'la cuenta no cerró: %r' % c['diferencia_ml']
    assert c['completa'] is True
    assert c['cuadra'] is True
    assert c['remanente_por'] == 'sebastian' and c['remanente_at_utc']


def test_una_diferencia_fuera_de_tolerancia_no_se_da_por_buena(app, db_clean):
    """Declarar un remanente NO hace que la cuenta cuadre sola: si sigue faltando
    granel por encima de la tolerancia, tiene que verse."""
    eid = _ebr(app)
    _unidades(app, eid, 'ENV-COLGLOSS-15-01', 10.0, 100)
    cli = _login(app)
    r = cli.post('/api/brd/ebr/%d/remanente-granel' % eid, headers=_h(), json={
        'remanente_g': 5000, 'destino': 'otra_orden'})
    c = r.get_json()['conciliacion']
    assert c['diferencia_ml'] > 1000, 'debería quedar granel sin explicar'
    assert c['diferencia_pct'] > c['tolerancia_pct']
    assert c['cuadra'] is False, 'dio por buena una diferencia fuera de tolerancia'


def test_suma_todas_las_presentaciones_del_mismo_lote(app, db_clean):
    """Un lote se envasa en varios formatos y sigue siendo UN lote (Sebastián 28-jul:
    *"se pone el mismo lote, sólo cambia el envase"*)."""
    eid = _ebr(app)
    _unidades(app, eid, 'ENV-10', 10.0, 100)     # 1.000 mL
    _unidades(app, eid, 'ENV-30', 30.0, 200)     # 6.000 mL
    cli = _login(app)
    c = _conc(app, cli, eid)
    assert c['envasado_ml'] == 7000.0, 'no sumó las dos presentaciones: %r' % c['envasado_ml']
    assert len(c['presentaciones']) == 2


def test_presentacion_no_envasada_no_suma(app, db_clean):
    """Una presentación marcada como NO envasada no puede aportar granel."""
    from database import get_db
    eid = _ebr(app)
    _unidades(app, eid, 'ENV-10', 10.0, 100)
    _unidades(app, eid, 'ENV-30', 30.0, 200)
    with app.app_context():
        conn = get_db()
        conn.cursor().execute(
            "UPDATE ebr_envasado_unidades SET no_envasada=1 WHERE ebr_id=? AND presentacion_codigo=?",
            (eid, 'ENV-30'))
        conn.commit()
    cli = _login(app)
    c = _conc(app, cli, eid)
    assert c['envasado_ml'] == 1000.0, 'contó una presentación no envasada: %r' % c['envasado_ml']


def test_sin_densidad_no_se_inventa_la_conversion(app, db_clean):
    """Sin densidad no hay forma de pasar los gramos pesados a mL. Se declara que
    falta, no se inventa un número (M109: sin dato no se inventa un default)."""
    eid = _ebr(app, densidad=None)
    _unidades(app, eid, 'ENV-10', 10.0, 100)
    cli = _login(app)
    cli.post('/api/brd/ebr/%d/remanente-granel' % eid, headers=_h(), json={
        'remanente_g': 5000, 'destino': 'otra_orden'})
    c = _conc(app, cli, eid)
    assert c['remanente_ml'] is None, 'inventó una conversión sin densidad'
    assert c['falta_densidad'] is True
    assert c['completa'] is False


def test_una_presentacion_sin_volumen_deja_la_cuenta_abierta(app, db_clean):
    """Si una presentación no tiene mL, Σ(uds × mL) subcuenta y la diferencia sería
    falsamente grande. Se declara en vez de cerrar una cuenta que no se puede hacer."""
    eid = _ebr(app)
    _unidades(app, eid, 'ENV-10', 10.0, 100)
    _unidades(app, eid, 'ENV-SIN-VOL', 0, 50)
    cli = _login(app)
    cli.post('/api/brd/ebr/%d/remanente-granel' % eid, headers=_h(), json={
        'remanente_g': 10679.6, 'destino': 'otra_orden'})
    c = _conc(app, cli, eid)
    assert c['presentaciones_sin_volumen'] == 1
    assert c['completa'] is False and c['cuadra'] is False


# ══ integridad del registro ═════════════════════════════════════════════════════

def test_destino_fuera_de_la_lista_se_rechaza(app, db_clean):
    eid = _ebr(app)
    cli = _login(app)
    r = cli.post('/api/brd/ebr/%d/remanente-granel' % eid, headers=_h(), json={
        'remanente_g': 100, 'destino': 'lo que sea'})
    assert r.status_code == 400
    assert r.get_json().get('codigo') == 'DESTINO_INVALIDO'


def test_declarar_sin_remanente_con_peso_es_contradiccion(app, db_clean):
    """Dos campos que se contradicen en un registro regulado no se guardan: uno de
    los dos es un error de tipeo y no se puede adivinar cuál."""
    eid = _ebr(app)
    cli = _login(app)
    r = cli.post('/api/brd/ebr/%d/remanente-granel' % eid, headers=_h(), json={
        'remanente_g': 500, 'destino': 'sin_remanente'})
    assert r.status_code == 400
    assert r.get_json().get('codigo') == 'DESTINO_CONTRADICE_PESO'


def test_remanente_negativo_se_rechaza(app, db_clean):
    eid = _ebr(app)
    cli = _login(app)
    r = cli.post('/api/brd/ebr/%d/remanente-granel' % eid, headers=_h(), json={
        'remanente_g': -5, 'destino': 'otra_orden'})
    assert r.status_code == 400


def test_legajo_liberado_es_inmutable(app, db_clean):
    """Part 11: un lote liberado no se toca más."""
    eid = _ebr(app, estado='liberado')
    cli = _login(app)
    r = cli.post('/api/brd/ebr/%d/remanente-granel' % eid, headers=_h(), json={
        'remanente_g': 100, 'destino': 'otra_orden'})
    assert r.status_code == 409
    assert r.get_json().get('codigo') == 'LEGAJO_INMUTABLE'


def test_no_aplica_a_fabricacion(app, db_clean):
    """La conciliación de granel es del envasado · en fabricación no significa nada."""
    eid = _ebr(app, fase='fabricacion')
    cli = _login(app)
    r = cli.post('/api/brd/ebr/%d/remanente-granel' % eid, headers=_h(), json={
        'remanente_g': 100, 'destino': 'otra_orden'})
    assert r.status_code == 400
    assert _conc(app, cli, eid) is None


def test_queda_rastro_en_audit_log(app, db_clean):
    """INVIMA / Part 11 §11.10(e): quién declaró el remanente y cuánto quedó sin explicar."""
    from database import get_db
    eid = _ebr(app)
    _unidades(app, eid, 'ENV-10', 10.0, 100)
    cli = _login(app)
    cli.post('/api/brd/ebr/%d/remanente-granel' % eid, headers=_h(), json={
        'remanente_g': 10679.6, 'destino': 'otra_orden'})
    with app.app_context():
        r = get_db().cursor().execute(
            "SELECT usuario, despues FROM audit_log WHERE accion='CONCILIAR_GRANEL_ENVASADO' "
            "AND registro_id=? ORDER BY id DESC LIMIT 1", (str(eid),)).fetchone()
    assert r, 'la conciliación no dejó rastro en audit_log'
    assert r[0] == 'sebastian'
    assert 'diferencia_ml' in (r[1] or ''), 'el rastro no guarda la diferencia declarada'


def test_la_migracion_solo_agrega_columnas(app, db_clean):
    from database import MIGRATIONS
    stmts = ' '.join(next(s for v, _, s in MIGRATIONS if v == 392))
    for col in ('remanente_g', 'remanente_destino', 'remanente_por', 'remanente_at_utc'):
        assert col in stmts, 'la mig 392 no agrega %s' % col
    assert 'DELETE' not in stmts and 'DROP' not in stmts


def test_el_imprimible_lleva_la_conciliacion(app, db_clean):
    """Si no está en el PDF, no está en el legajo que se archiva · que es el que ve
    la auditoría. Un bloque que sólo vive en la pantalla no es un registro."""
    eid = _ebr(app)
    _unidades(app, eid, 'ENV-10', 10.0, 100)
    cli = _login(app)
    cli.post('/api/brd/ebr/%d/remanente-granel' % eid, headers=_h(), json={
        'remanente_g': 10679.6, 'destino': 'otra_orden'})
    r = cli.get('/api/brd/ebr/%d/pdf' % eid)
    assert r.status_code == 200, r.data[:300]
    assert r.data[:4] == b'%PDF', 'no devolvió un PDF'
    assert len(r.data) > 1000


def test_la_pantalla_del_legajo_pinta_el_bloque(app, db_clean):
    """M112: podar/agregar deja botones vivos apuntando a lo que no existe. Cada
    función que la tarjeta llama tiene que estar definida en el mismo bloque."""
    from api.blueprints import brd
    t = brd._ENVASADO_LEGAJO_HTML
    assert 'conciliacion_granel' in t, 'la pantalla no lee la conciliación'
    assert 'Conciliación del Granel' in t, 'no pinta la tarjeta'
    for fn in ('concModal', 'guardarConc', 'cerrarConc'):
        assert ('function %s' % fn) in t or ('async function %s' % fn) in t, (
            'el botón llama a %s y esa función no existe' % fn)
    assert 'remanente-granel' in t, 'la pantalla no llama al endpoint'


def test_el_pdf_no_revienta_sin_rendimiento(app, db_clean):
    """Regresión: el PDF del batch record daba 500 con cantidad real pero sin yield.

    `yield_pct` queda en NULL cuando el objetivo es 0 (brd.py:4304) y formatear None
    con `:.2f` revienta -- o sea que el documento regulado se caía por un dato que
    falta, en vez de imprimirlo como faltante. Nadie lo cubría porque no había test
    del PDF con esa combinación.
    """
    from database import get_db
    eid = _ebr(app)
    with app.app_context():
        conn = get_db()
        conn.cursor().execute(
            "UPDATE ebr_ejecuciones SET yield_pct=NULL, cantidad_objetivo_g=0 WHERE id=?", (eid,))
        conn.commit()
    cli = _login(app)
    r = cli.get('/api/brd/ebr/%d/pdf' % eid)
    assert r.status_code == 200, 'el PDF del legajo se cae sin yield: %s' % r.data[:200]
    assert r.data[:4] == b'%PDF'
