"""El legajo registra CUÁNTO material de envase se recibió en línea, y quién (28-jul).

Contrastando el batch record contra MyBatch apareció que la conciliación de empaque ya estaba
completa (`requerida` / `devuelta` / `utilizada` / `averiada`), pero faltaba el momento
ANTERIOR: la sección 3 del envasado -- `MATERIAL | N° LOTE | CANT. REQUERIDA | CANT. RECIBIDA |
RECIBIDO POR`.

Por qué importa y no es un campo de adorno: si se piden 100 tapas y entregan 95, sin `recibida`
la conciliación cierra igual y el faltante se lo termina comiendo `utilizada`. El reclamo al
proveedor y la merma real quedan indistinguibles.
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


LOTE = 'ZZ-EBR-ENVMAT'


def _ebr(app):
    """Un EBR mínimo. Limpia ANTES (M103) · `ebr_ejecuciones.lote` es UNIQUE (M10)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        fila = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (LOTE,)).fetchone()
        if fila:
            cu.execute("DELETE FROM ebr_envase_materiales WHERE ebr_id=?", (fila[0],))
            cu.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (fila[0],))
        # Columnas reales verificadas contra el CREATE TABLE: no hay `producto_nombre`, y
        # mbr_template_id / mbr_version / iniciado_por / iniciado_at_utc / cantidad_objetivo_g
        # son NOT NULL.
        cu.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, estado, "
            "iniciado_por, iniciado_at_utc, cantidad_objetivo_g) VALUES (?,?,?,?,?,?,?)",
            (1, 1, LOTE, 'en_proceso', 'sebastian', '2026-07-28T10:00:00', 1000))
        eid = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (LOTE,)).fetchone()[0]
        conn.commit()
    return eid


def _fila(app, eid):
    from database import get_db
    with app.app_context():
        r = get_db().cursor().execute(
            "SELECT requerida, recibida, COALESCE(recibido_por,''), COALESCE(recibido_at_utc,''), "
            "       utilizada FROM ebr_envase_materiales WHERE ebr_id=?", (eid,)).fetchone()
    return dict(zip(('requerida', 'recibida', 'recibido_por', 'recibido_at', 'utilizada'), r)) if r else None


# ═══════════════════════════════════════════════════════════════════════════════

def test_se_registra_cuanto_se_recibio_y_quien_lo_recibio(app, db_clean):
    eid = _ebr(app)
    cli = _login(app)
    r = cli.post(f'/api/brd/ebr/{eid}/material-envase', headers=_h(), json={
        'material_codigo': 'MEE-ENV-022', 'material_nombre': 'Envase 30ml',
        'lote_material': 'LM-1', 'requerida': 100, 'recibida': 95})
    assert r.status_code in (200, 201), r.data[:300]

    f = _fila(app, eid)
    assert f, 'no se guardó la fila'
    assert f['requerida'] == 100
    assert f['recibida'] == 95, 'no guardó la cantidad recibida: %r' % f['recibida']
    assert f['recibido_por'] == 'sebastian', 'no quedó quién recibió: %r' % f['recibido_por']
    assert f['recibido_at'], 'no quedó cuándo se recibió'


def test_sin_declarar_recibida_no_se_inventa_un_receptor(app, db_clean):
    """Un nombre puesto por defecto en un registro regulado es peor que el campo vacío: parece
    que alguien firmó algo que nadie firmó."""
    eid = _ebr(app)
    cli = _login(app)
    r = cli.post(f'/api/brd/ebr/{eid}/material-envase', headers=_h(), json={
        'material_codigo': 'MEE-ENV-022', 'material_nombre': 'Envase 30ml',
        'requerida': 100})
    assert r.status_code in (200, 201), r.data[:300]
    f = _fila(app, eid)
    assert f['recibida'] is None, 'inventó una cantidad recibida: %r' % f['recibida']
    assert f['recibido_por'] == '', 'inventó un receptor: %r' % f['recibido_por']
    assert f['recibido_at'] == ''


def test_el_faltante_de_la_entrega_queda_a_la_vista(app, db_clean):
    """El caso real: se piden 100, entregan 95, se usan 95. Sin `recibida` la conciliación
    cerraba perfecta y esas 5 quedaban como si se hubieran consumido."""
    eid = _ebr(app)
    cli = _login(app)
    cli.post(f'/api/brd/ebr/{eid}/material-envase', headers=_h(), json={
        'material_codigo': 'MEE-ENV-022', 'material_nombre': 'Envase 30ml',
        'requerida': 100, 'recibida': 95, 'utilizada': 95, 'devuelta': 0, 'averiada': 0})
    f = _fila(app, eid)
    faltante_entrega = (f['requerida'] or 0) - (f['recibida'] or 0)
    assert faltante_entrega == 5, (
        'no se puede distinguir lo que no entregaron de lo que se consumió')
    # Y contra lo recibido, la conciliación cierra: no hay merma inventada.
    assert (f['recibida'] or 0) - (f['utilizada'] or 0) == 0


def test_editar_la_fila_conserva_lo_recibido(app, db_clean):
    """Al corregir la conciliación no se puede borrar el dato de la entrega."""
    from database import get_db
    eid = _ebr(app)
    cli = _login(app)
    cli.post(f'/api/brd/ebr/{eid}/material-envase', headers=_h(), json={
        'material_codigo': 'MEE-ENV-022', 'requerida': 100, 'recibida': 95})
    with app.app_context():
        rid = get_db().cursor().execute(
            "SELECT id FROM ebr_envase_materiales WHERE ebr_id=?", (eid,)).fetchone()[0]
    r = cli.post(f'/api/brd/ebr/{eid}/material-envase', headers=_h(), json={
        'id': rid, 'material_codigo': 'MEE-ENV-022',
        'requerida': 100, 'recibida': 95, 'utilizada': 90, 'averiada': 5})
    assert r.status_code in (200, 201), r.data[:300]
    f = _fila(app, eid)
    assert f['recibida'] == 95 and f['recibido_por'] == 'sebastian'
    assert f['utilizada'] == 90


def test_la_migracion_agrega_las_tres_columnas(app, db_clean):
    from database import MIGRATIONS
    stmts = ' '.join(next(s for v, _, s in MIGRATIONS if v == 391))
    for col in ('recibida', 'recibido_por', 'recibido_at_utc'):
        assert col in stmts, 'la mig 391 no agrega %s' % col
    assert 'DELETE' not in stmts and 'DROP' not in stmts, (
        'una migración que sólo agrega columnas no puede borrar nada')
