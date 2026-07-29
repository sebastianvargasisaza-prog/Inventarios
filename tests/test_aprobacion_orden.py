"""La orden se APRUEBA antes de arrancar (28-jul).

Sebastián, describiendo el flujo de MyBatch: *"tanto fabricación, envasado como
acondicionamiento, todas inician con una ORDEN; esa orden se le entrega al operario, y
después empieza el proceso"*. El legajo de EOS ya guardaba quién lo INICIÓ, quién lo
LIBERÓ y el visto bueno final del Director Técnico (mig 286) -- pero no quién AUTORIZÓ
que empezara, que en MyBatch es una firma propia de la orden (`approved/<pk>`, y en
acondicionamiento dos: `approved` de producción y `approved_quality` de calidad).

El toggle arranca en OFF y ahí es un NO-OP TOTAL (M68: un modo beta que igual bloquea
en un caso es una traba fantasma esperando a aparecer). La firma se registra y se
muestra desde el día uno; frenar al piso es una decisión aparte, de Sebastián.
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


LOTE = 'ZZ-EBR-APROB'


def _ebr(app, *, estado='iniciado', aprobada_por=''):
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        fila = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (LOTE,)).fetchone()
        if fila:
            cu.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (fila[0],))
        cu.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, estado, "
            "fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, aprobada_orden_por) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (1, 1, LOTE, LOTE, estado, 'envasado', 'sebastian', '2026-07-28T10:00:00',
             1000, aprobada_por))
        eid = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (LOTE,)).fetchone()[0]
        conn.commit()
    return eid


def _toggle(app, valor):
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.cursor().execute(
            "INSERT INTO app_settings (clave, valor) VALUES ('exigir_aprobacion_orden', ?) "
            "ON CONFLICT (clave) DO UPDATE SET valor=excluded.valor", (valor,))
        conn.commit()


def _firma(app, eid, user='sebastian', meaning='aprueba_orden'):
    """Firma válida sembrada directo (el reto de /api/sign pide contraseña + TOTP)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        # Columnas verificadas contra el CREATE TABLE real: auth_factor y signature_hash
        # son NOT NULL (una firma sin factor de autenticación ni hash no es una firma).
        cu.execute(
            "INSERT INTO e_signatures (record_table, record_id, meaning, signer_username, "
            "signed_at_utc, auth_factor, signature_hash) "
            "VALUES ('ebr_ejecuciones', ?, ?, ?, datetime('now','utc'), 'password', ?)",
            (str(eid), meaning, user, 'hash-test-%s-%s' % (eid, meaning)))
        sid = cu.execute(
            "SELECT id FROM e_signatures WHERE record_table='ebr_ejecuciones' AND record_id=? "
            "AND meaning=? AND signer_username=? ORDER BY id DESC LIMIT 1",
            (str(eid), meaning, user)).fetchone()[0]
        conn.commit()
    return sid


# ══ la firma ════════════════════════════════════════════════════════════════════

def test_aprobar_la_orden_deja_quien_cuando_y_con_que_rol(app, db_clean):
    from database import get_db
    eid = _ebr(app)
    cli = _login(app)
    r = cli.post('/api/brd/ebr/%d/aprobar-orden' % eid, headers=_h(),
                 json={'signature_id': _firma(app, eid)})
    assert r.status_code == 200, r.data[:300]
    with app.app_context():
        row = get_db().cursor().execute(
            "SELECT aprobada_orden_por, aprobada_orden_at_utc, aprobada_orden_rol, "
            "aprobada_orden_signature_id FROM ebr_ejecuciones WHERE id=?", (eid,)).fetchone()
    assert row[0] == 'sebastian'
    assert row[1], 'no quedó cuándo se aprobó'
    assert row[2], 'no quedó el rol con el que firmó'
    assert row[3], 'no quedó la firma electrónica ligada'


def test_sin_firma_electronica_no_se_aprueba(app, db_clean):
    """Part 11: una aprobación de un lote regulado va firmada, no es un botón."""
    eid = _ebr(app)
    cli = _login(app)
    r = cli.post('/api/brd/ebr/%d/aprobar-orden' % eid, headers=_h(), json={})
    assert r.status_code == 400
    assert 'signature_id' in r.get_json().get('error', '')


def test_una_firma_de_otro_significado_no_sirve(app, db_clean):
    """Un `signature_id` cualquiera no aprueba: la firma tiene que ser de ESTE legajo,
    con ESTE significado y de ESTE usuario."""
    eid = _ebr(app)
    cli = _login(app)
    r = cli.post('/api/brd/ebr/%d/aprobar-orden' % eid, headers=_h(),
                 json={'signature_id': _firma(app, eid, meaning='ejecuta')})
    assert r.status_code == 400


def test_no_se_aprueba_dos_veces(app, db_clean):
    eid = _ebr(app)
    cli = _login(app)
    cli.post('/api/brd/ebr/%d/aprobar-orden' % eid, headers=_h(),
             json={'signature_id': _firma(app, eid)})
    r = cli.post('/api/brd/ebr/%d/aprobar-orden' % eid, headers=_h(),
                 json={'signature_id': _firma(app, eid)})
    assert r.status_code == 409
    assert r.get_json().get('codigo') == 'YA_APROBADA'


def test_queda_rastro_en_audit_log(app, db_clean):
    from database import get_db
    eid = _ebr(app)
    cli = _login(app)
    cli.post('/api/brd/ebr/%d/aprobar-orden' % eid, headers=_h(),
             json={'signature_id': _firma(app, eid)})
    with app.app_context():
        r = get_db().cursor().execute(
            "SELECT usuario FROM audit_log WHERE accion='APROBAR_ORDEN' AND registro_id=?",
            (str(eid),)).fetchone()
    assert r and r[0] == 'sebastian', 'la aprobación de la orden no dejó rastro'


# ══ el gate (default OFF = NO-OP total) ═════════════════════════════════════════

def test_con_el_toggle_apagado_no_frena_a_nadie(app, db_clean):
    """M68: en beta el gate es NO-OP COMPLETO. Un legajo sin aprobar ejecuta igual."""
    _toggle(app, '0')
    eid = _ebr(app)
    cli = _login(app)
    r = cli.post('/api/brd/ebr/%d/observaciones' % eid, headers=_h(),
                 json={'descripcion': 'se pausa el envasado'})
    assert r.status_code in (200, 201), r.data[:300]
    r2 = cli.post('/api/brd/ebr/%d/registrar-unidades' % eid, headers=_h(),
                  json={'presentacion_codigo': 'ENV-10', 'volumen_ml': 10, 'unidades': 5})
    assert r2.status_code == 200, r2.data[:300]


def test_con_el_toggle_encendido_un_legajo_sin_aprobar_no_arranca(app, db_clean):
    _toggle(app, '1')
    eid = _ebr(app)
    cli = _login(app)
    try:
        r = cli.post('/api/brd/ebr/%d/registrar-unidades' % eid, headers=_h(),
                     json={'presentacion_codigo': 'ENV-10', 'volumen_ml': 10, 'unidades': 5})
        assert r.status_code == 409, 'ejecutó sin la orden aprobada: %s' % r.data[:200]
        assert r.get_json().get('codigo') == 'ORDEN_SIN_APROBAR'
    finally:
        _toggle(app, '0')


def test_con_el_toggle_encendido_una_orden_aprobada_si_arranca(app, db_clean):
    _toggle(app, '1')
    eid = _ebr(app, aprobada_por='alejandro')
    cli = _login(app)
    try:
        r = cli.post('/api/brd/ebr/%d/registrar-unidades' % eid, headers=_h(),
                     json={'presentacion_codigo': 'ENV-10', 'volumen_ml': 10, 'unidades': 5})
        assert r.status_code == 200, 'la orden aprobada igual quedó trabada: %s' % r.data[:200]
    finally:
        _toggle(app, '0')


def test_el_gate_nunca_bloquea_documentar_ni_aprobar(app, db_clean):
    """Un registro regulado no se puede quedar SIN ANOTAR por un permiso administrativo:
    la bitácora, las correcciones y la aprobación misma quedan siempre abiertas."""
    _toggle(app, '1')
    eid = _ebr(app)
    cli = _login(app)
    try:
        r = cli.post('/api/brd/ebr/%d/observaciones' % eid, headers=_h(),
                     json={'descripcion': 'la orden llegó sin aprobar, se avisa a produccion'})
        assert r.status_code in (200, 201), 'el gate tapó la bitácora: %s' % r.data[:200]
        r2 = cli.post('/api/brd/ebr/%d/aprobar-orden' % eid, headers=_h(),
                      json={'signature_id': _firma(app, eid)})
        assert r2.status_code == 200, 'el gate se muerde la cola: %s' % r2.data[:200]
    finally:
        _toggle(app, '0')


def test_el_gate_es_default_deny_no_una_lista_a_mano(app, db_clean):
    """M45: un guard que se aplica endpoint por endpoint deja hermanos sin blindar.

    El gate vive DENTRO de `_require_brd_ejecutor`, así que todo endpoint de ejecución
    -- incluidos los que se escriban mañana -- lo hereda. Lo que se enumera es sólo lo
    EXENTO. Si alguien lo saca de ahí y lo empieza a pegar a mano, este test cae.
    """
    import inspect
    from api.blueprints import brd
    src = inspect.getsource(brd._require_brd_ejecutor)
    assert '_gate_aprobacion_orden' in src, (
        'el gate ya no se hereda desde _require_brd_ejecutor · volvió a ser una lista a mano')
    # Y lo exento es corto y explícito: si crece sin control, deja de ser una excepción.
    assert len(brd._APROBACION_ORDEN_EXENTOS) <= 10


def test_el_gate_nunca_bloquea_una_LECTURA(app, db_clean):
    """Un control de ARRANQUE frena la ejecución, nunca la consulta.

    Se ejercita el guard DIRECTO en un contexto GET, no vía un endpoint: hoy ningún
    endpoint gateado lee (la rama GET de `ipc-estandar` retorna antes de llamar al
    guard), así que un test por HTTP pasaría verde con y sin el filtro -- o sea que
    no probaría nada (M104: un trinquete sin dientes da falsa tranquilidad).
    """
    from api.blueprints import brd
    _toggle(app, '1')
    eid = _ebr(app)                                   # legajo SIN aprobar
    try:
        with app.test_request_context('/api/brd/ebr/%d/ipc-estandar' % eid, method='GET'):
            from flask import request as _rq
            _rq.view_args = {'ebr_id': eid}
            assert brd._gate_aprobacion_orden() is None, 'el gate bloqueó una LECTURA'
        with app.test_request_context('/api/brd/ebr/%d/ipc-estandar' % eid, method='POST'):
            from flask import request as _rq2
            _rq2.view_args = {'ebr_id': eid}
            assert brd._gate_aprobacion_orden() is not None, (
                'el gate dejó ESCRIBIR con la orden sin aprobar')
    finally:
        _toggle(app, '0')


def test_los_exentos_existen_de_verdad(app, db_clean):
    """Son ENDPOINTS de Flask, no rutas. Uno mal escrito no falla: queda de peso muerto
    y el endpoint que creías eximido se frena igual. (Así se cazó uno inventado.)"""
    from api.blueprints import brd
    reales = {r.endpoint for r in app.url_map.iter_rules()}
    malos = sorted(e for e in brd._APROBACION_ORDEN_EXENTOS if e not in reales)
    assert not malos, 'exentos que no existen en el url_map: %s' % malos


# ══ la firma que nunca se pudo dar ══════════════════════════════════════════════

def test_los_meanings_de_aprobacion_existen_en_el_firmador(app, db_clean):
    """`aprueba_dt` faltaba en la whitelist de /api/sign desde que se creó (mig 286):
    la pantalla firmaba con ese meaning y el firmador devolvía 400, así que el visto
    bueno del Director Técnico NUNCA se pudo dar. El backend que lo valida estaba
    bien; el hueco vivía en la lista del firmador."""
    from api.blueprints.firmas import VALID_MEANINGS, _now_utc_iso  # noqa: F401
    for m in ('aprueba_dt', 'aprueba_orden'):
        assert m in VALID_MEANINGS, (
            '%s no está en VALID_MEANINGS · esa firma da 400 y la feature queda muerta' % m)


def test_la_migracion_es_no_op_por_defecto(app, db_clean):
    """El toggle nace apagado · encenderlo a ciegas trabaría el piso el mismo día."""
    from database import MIGRATIONS
    stmts = ' '.join(next(s for v, _, s in MIGRATIONS if v == 393))
    assert "'exigir_aprobacion_orden','0'" in stmts.replace(' ', '').replace('\n', '') or \
           "'exigir_aprobacion_orden', '0'" in stmts, 'el toggle no nace en 0'
    for col in ('aprobada_orden_por', 'aprobada_orden_at_utc', 'aprobada_orden_signature_id'):
        assert col in stmts, 'la mig 393 no agrega %s' % col
