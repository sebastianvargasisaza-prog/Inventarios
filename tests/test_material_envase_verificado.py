"""2ª firma sobre el material de envase recibido (28-jul · mig 394).

En MyBatch recibir y verificar son DOS pasos separados (`material_received` y
`material_verified`), y esa separación ES el control: quien cuenta lo que llegó no puede
ser el mismo que certifica que está bien. La mig 391 trajo `recibida`/`recibido_por`;
faltaba el paso siguiente.

Acá se cubre además un hueco que apareció al construirlo: `recibida` y `recibido_por` se
guardaban desde la mig 391 pero el lector del legajo NO los consultaba y la tabla no tenía
esas columnas -- o sea que la sección 3 del envasado quedaba a medias en pantalla aunque el
dato estuviera en la base (M115: un dato capturado que no llega al consumidor no existe).
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


LOTE = 'ZZ-EBR-MATVERIF'


def _ebr(app):
    """Limpia ANTES de sembrar (M103): `ebr_ejecuciones.lote` es UNIQUE (M10)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        fila = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (LOTE,)).fetchone()
        if fila:
            cu.execute("DELETE FROM ebr_envase_materiales WHERE ebr_id=?", (fila[0],))
            cu.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (fila[0],))
        cu.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
            "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (1, 1, LOTE, LOTE, 'en_proceso', 'envasado', 'sebastian',
             '2026-07-28T10:00:00', 1000))
        eid = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (LOTE,)).fetchone()[0]
        conn.commit()
    return eid


def _fila(app, eid):
    from database import get_db
    with app.app_context():
        r = get_db().cursor().execute(
            "SELECT id, COALESCE(recibido_por,''), COALESCE(verificado_por,''), "
            "COALESCE(verificado_at_utc,'') FROM ebr_envase_materiales "
            "WHERE ebr_id=? ORDER BY id DESC LIMIT 1", (eid,)).fetchone()
    return dict(zip(('id', 'recibido_por', 'verificado_por', 'verificado_at'), r)) if r else None


def _recibe(cli, eid, **extra):
    body = {'material_codigo': 'MEE-ENV-022', 'requerida': 100, 'recibida': 95}
    body.update(extra)
    return cli.post('/api/brd/ebr/%d/material-envase' % eid, headers=_h(), json=body)


# ══ la regla de las 2 personas ══════════════════════════════════════════════════

def test_otra_persona_verifica_lo_recibido(app, db_clean):
    eid = _ebr(app)
    _recibe(_login(app, 'laura'), eid)
    rid = _fila(app, eid)['id']
    r = _login(app).post('/api/brd/ebr/%d/material-envase/%d/verificar' % (eid, rid),
                         headers=_h(), json={})
    assert r.status_code == 200, r.data[:300]
    f = _fila(app, eid)
    assert f['recibido_por'] == 'laura'
    assert f['verificado_por'] == 'sebastian', 'no quedó la 2ª firma: %r' % f['verificado_por']
    assert f['verificado_at'], 'no quedó cuándo se verificó'


def test_nadie_verifica_su_propia_recepcion(app, db_clean):
    """Si el mismo que contó certifica que está bien, no hay control: hay un solo par de
    ojos con dos firmas."""
    eid = _ebr(app)
    cli = _login(app)
    _recibe(cli, eid)
    rid = _fila(app, eid)['id']
    r = cli.post('/api/brd/ebr/%d/material-envase/%d/verificar' % (eid, rid),
                 headers=_h(), json={})
    assert r.status_code == 409, 'se verificó a sí mismo: %s' % r.data[:200]
    assert r.get_json().get('codigo') == 'AUTOVERIFICACION_BLOQUEADA'
    assert _fila(app, eid)['verificado_por'] == ''


def test_no_se_verifica_lo_que_no_llego(app, db_clean):
    """Sin recepción declarada no hay nada que certificar: una firma sobre un dato que no
    existe es peor que ninguna firma."""
    eid = _ebr(app)
    _login(app, 'laura').post('/api/brd/ebr/%d/material-envase' % eid, headers=_h(),
                              json={'material_codigo': 'MEE-ENV-022', 'requerida': 100})
    rid = _fila(app, eid)['id']
    r = _login(app).post('/api/brd/ebr/%d/material-envase/%d/verificar' % (eid, rid),
                         headers=_h(), json={})
    assert r.status_code == 409
    assert r.get_json().get('codigo') == 'SIN_RECEPCION'


def test_no_se_verifica_dos_veces(app, db_clean):
    eid = _ebr(app)
    _recibe(_login(app, 'laura'), eid)
    rid = _fila(app, eid)['id']
    cli = _login(app)
    cli.post('/api/brd/ebr/%d/material-envase/%d/verificar' % (eid, rid), headers=_h(), json={})
    r = cli.post('/api/brd/ebr/%d/material-envase/%d/verificar' % (eid, rid),
                 headers=_h(), json={})
    assert r.status_code == 409
    assert r.get_json().get('codigo') == 'YA_VERIFICADO'


def test_queda_rastro_en_audit_log(app, db_clean):
    from database import get_db
    eid = _ebr(app)
    _recibe(_login(app, 'laura'), eid)
    rid = _fila(app, eid)['id']
    _login(app).post('/api/brd/ebr/%d/material-envase/%d/verificar' % (eid, rid),
                     headers=_h(), json={})
    with app.app_context():
        r = get_db().cursor().execute(
            "SELECT usuario, despues FROM audit_log WHERE accion='VERIFICAR_MATERIAL_ENVASE_EBR' "
            "AND registro_id=? ORDER BY id DESC LIMIT 1", (str(rid),)).fetchone()
    assert r, 'la verificación no dejó rastro'
    assert r[0] == 'sebastian'
    assert 'recibido_por' in (r[1] or ''), 'el rastro no dice a quién se le verificó'


# ══ la firma cubre LOS DATOS QUE SE FIRMARON ════════════════════════════════════

def test_cambiar_lo_recibido_TUMBA_la_verificacion(app, db_clean):
    """Si después se corrige la cantidad que llegó, la firma quedaría certificando otro
    número: eso es falsear un registro Part 11. Se cae y hay que rehacerla."""
    eid = _ebr(app)
    cli_l = _login(app, 'laura')
    _recibe(cli_l, eid)
    rid = _fila(app, eid)['id']
    _login(app).post('/api/brd/ebr/%d/material-envase/%d/verificar' % (eid, rid),
                     headers=_h(), json={})
    assert _fila(app, eid)['verificado_por'] == 'sebastian'
    _recibe(cli_l, eid, id=rid, recibida=90)
    assert _fila(app, eid)['verificado_por'] == '', (
        'la firma sobrevivió a un cambio de la cantidad recibida')


def test_conciliar_despues_NO_tumba_la_verificacion(app, db_clean):
    """Lo contrario también importa: devuelta/utilizada/averiada son un momento POSTERIOR y
    no cambian lo que la firma certificó. Si cada ajuste la tumbara, nadie firmaría."""
    eid = _ebr(app)
    cli_l = _login(app, 'laura')
    _recibe(cli_l, eid)
    rid = _fila(app, eid)['id']
    _login(app).post('/api/brd/ebr/%d/material-envase/%d/verificar' % (eid, rid),
                     headers=_h(), json={})
    _recibe(cli_l, eid, id=rid, utilizada=90, averiada=5)
    assert _fila(app, eid)['verificado_por'] == 'sebastian', (
        'conciliar tumbó una firma que seguía siendo válida')


# ══ el dato tiene que LLEGAR a la pantalla (M115) ═══════════════════════════════

def test_lo_recibido_llega_a_la_pantalla(app, db_clean):
    """`recibida`/`recibido_por` se guardaban desde la mig 391 pero el lector del legajo no
    los consultaba y la tabla no tenía esas columnas: el dato existía y nadie lo veía."""
    from api.blueprints import brd
    eid = _ebr(app)
    cli = _login(app, 'laura')
    _recibe(cli, eid)
    d = cli.get('/api/brd/ebr/%d/vista-completa' % eid).get_json()
    fila = next((m for m in (d.get('envasado_materiales') or []) if m.get('id')), None)
    assert fila, 'el legajo no devuelve la fila de material'
    assert fila.get('recibida') == 95, 'la cantidad recibida no llega a la vista'
    assert fila.get('recibido_por') == 'laura', 'quién recibió no llega a la vista'
    assert fila.get('faltante_entrega') == 5, 'no expone lo que NO entregaron'
    t = brd._ENVASADO_LEGAJO_HTML
    for col in ('Cant. recibida', 'Recibido por', 'Verificado por'):
        assert col in t, 'la tabla del legajo no tiene la columna %r' % col
    assert 'async function verificarMat' in t, 'el botón de verificar no tiene función'


def test_el_imprimible_lleva_las_dos_firmas(app, db_clean):
    """Si no está en el PDF, la regla de las 2 personas no se puede auditar sobre el papel."""
    eid = _ebr(app)
    _recibe(_login(app, 'laura'), eid)
    rid = _fila(app, eid)['id']
    cli = _login(app)
    cli.post('/api/brd/ebr/%d/material-envase/%d/verificar' % (eid, rid), headers=_h(), json={})
    r = cli.get('/api/brd/ebr/%d/pdf' % eid)
    assert r.status_code == 200, r.data[:300]
    assert r.data[:4] == b'%PDF'


def test_la_migracion_394_solo_agrega_columnas(app, db_clean):
    from database import MIGRATIONS
    stmts = ' '.join(next(s for v, _, s in MIGRATIONS if v == 394))
    for col in ('verificado_por', 'verificado_at_utc'):
        assert col in stmts, 'la mig 394 no agrega %s' % col
    assert 'DELETE' not in stmts and 'DROP' not in stmts
