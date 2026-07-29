"""La ORDEN como objeto propio (29-jul · mig 395).

Sebastián describiendo MyBatch: *"tanto fabricación, envasado como acondicionamiento, todas
inician con una ORDEN; esa orden se le entrega al operario, y después empieza el proceso"*.
Hasta hoy EOS modelaba el legajo POR LOTE y la orden era una etiqueta.

Lo que la orden agrega y el legajo por lote no tenía:
  1. un encabezado que se aprueba UNA vez para TODOS sus lotes,
  2. el botón "Adicionar lote",
  3. un número de orden, que es lo que se imprime y se le entrega al operario.

**Es ADITIVA y eso es el punto** (decisión de Sebastián: *"sí, desde los nuevos"*): los
legajos que ya existen se quedan sin orden madre y siguen funcionando exactamente igual.
Colgar retroactivamente un legajo ya ejecutado de una orden inventada sería fabricar
historia en un registro regulado.
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


def _limpiar(app):
    """Limpia ANTES (M103): `ordenes_produccion.numero` es UNIQUE y la BD de tests es
    compartida entre corridas en PG."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        for r in cu.execute(
            "SELECT id FROM ordenes_produccion WHERE producto_nombre LIKE 'ZZ-ORD%'").fetchall():
            cu.execute("UPDATE ebr_ejecuciones SET orden_id=NULL WHERE orden_id=?", (r[0],))
            cu.execute("DELETE FROM ordenes_produccion WHERE id=?", (r[0],))
        conn.commit()


def _crear(cli, **extra):
    body = {'fase': 'envasado', 'producto_nombre': 'ZZ-ORD PRODUCTO',
            'lote_bulk': '262021', 'cantidad_g': 17000, 'densidad_g_ml': 0.916}
    body.update(extra)
    return cli.post('/api/brd/ordenes', headers=_h(), json=body)


def _mbr_aprobado(app, producto='ZZ-ORD PRODUCTO'):
    """Sin un MBR aprobado, "Adicionar lote" no puede crear el legajo y el test se corta
    sin probar nada. Se siembra en el ORDEN REAL del flujo -- draft primero y recién
    después aprobado -- porque un MBR aprobado es INMUTABLE por trigger (mig 109) y
    escribirlo aprobado de una da IntegrityError (M93)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        r = cu.execute("SELECT id FROM mbr_templates WHERE producto_nombre=? AND version=1",
                       (producto,)).fetchone()
        if not r:
            cu.execute(
                "INSERT INTO mbr_templates (producto_nombre, version, estado, titulo, "
                "lote_size_g, creado_por) VALUES (?,1,'draft','MBR de prueba',1000,'sebastian')",
                (producto,))
        cu.execute(
            "UPDATE mbr_templates SET estado='aprobado', aprobado_por='sebastian', "
            "aprobado_at_utc=datetime('now','utc') WHERE producto_nombre=? AND version=1",
            (producto,))
        conn.commit()


def _firma(app, oid, user='sebastian', meaning='aprueba_orden'):
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute(
            "INSERT INTO e_signatures (record_table, record_id, meaning, signer_username, "
            "signed_at_utc, auth_factor, signature_hash) "
            "VALUES ('ordenes_produccion', ?, ?, ?, datetime('now','utc'), 'password', ?)",
            (str(oid), meaning, user, 'h-%s-%s' % (oid, meaning)))
        sid = cu.execute(
            "SELECT id FROM e_signatures WHERE record_table='ordenes_produccion' AND record_id=? "
            "AND meaning=? AND signer_username=? ORDER BY id DESC LIMIT 1",
            (str(oid), meaning, user)).fetchone()[0]
        conn.commit()
    return sid


# ══ el encabezado ═══════════════════════════════════════════════════════════════

def test_la_orden_nace_con_numero_propio(app, db_clean):
    """El número es lo que se imprime y se le entrega al operario."""
    _limpiar(app)
    r = _crear(_login(app))
    assert r.status_code == 201, r.data[:300]
    j = r.get_json()
    assert j['numero'].startswith('OF-'), 'una orden de envasado se numera OF-: %r' % j['numero']
    d = _login(app).get('/api/brd/ordenes/%d' % j['id']).get_json()['orden']
    assert d['estado'] == 'borrador'
    assert d['lotes'] == []


def test_cada_fase_tiene_su_prefijo(app, db_clean):
    _limpiar(app)
    cli = _login(app)
    for fase, pref in (('fabricacion', 'OP-'), ('envasado', 'OF-'), ('acondicionamiento', 'OA-')):
        j = _crear(cli, fase=fase).get_json()
        assert j['numero'].startswith(pref), '%s se numeró %r' % (fase, j['numero'])


def test_la_cantidad_en_ml_se_DERIVA_de_la_densidad(app, db_clean):
    """M71: lo derivado no se guarda. 17.000 g / 0,916 g/mL = 18.558,95 mL."""
    _limpiar(app)
    j = _crear(_login(app)).get_json()
    d = _login(app).get('/api/brd/ordenes/%d' % j['id']).get_json()['orden']
    assert abs(d['cantidad_ml'] - 18558.95) < 0.5, 'mal derivado: %r' % d['cantidad_ml']


def test_sin_densidad_no_se_inventa_la_conversion(app, db_clean):
    _limpiar(app)
    j = _crear(_login(app), densidad_g_ml=None).get_json()
    d = _login(app).get('/api/brd/ordenes/%d' % j['id']).get_json()['orden']
    assert d['cantidad_ml'] is None, 'inventó mL sin densidad'


def test_fase_invalida_se_rechaza(app, db_clean):
    _limpiar(app)
    r = _crear(_login(app), fase='loquesea')
    assert r.status_code == 400


# ══ una orden, N lotes ══════════════════════════════════════════════════════════

def test_una_orden_agrupa_varios_lotes(app, db_clean):
    """"Adicionar lote" de MyBatch: es la razón de ser de la orden."""
    from database import get_db
    _limpiar(app)
    _mbr_aprobado(app)
    cli = _login(app)
    oid = _crear(cli).get_json()['id']
    r = cli.post('/api/brd/ordenes/%d/adicionar-lote' % oid, headers=_h(), json={'lote': 'ZZ-L1'})
    assert r.status_code == 201, r.data[:300]
    with app.app_context():
        n = get_db().cursor().execute(
            "SELECT COUNT(*) FROM ebr_ejecuciones WHERE orden_id=?", (oid,)).fetchone()[0]
    assert n == 1
    d = cli.get('/api/brd/ordenes/%d' % oid).get_json()['orden']
    assert len(d['lotes']) == 1 and d['lotes'][0]['lote']


def test_no_se_agregan_lotes_a_una_orden_anulada(app, db_clean):
    from database import get_db
    _limpiar(app)
    cli = _login(app)
    oid = _crear(cli).get_json()['id']
    with app.app_context():
        conn = get_db()
        conn.cursor().execute("UPDATE ordenes_produccion SET estado='anulada' WHERE id=?", (oid,))
        conn.commit()
    r = cli.post('/api/brd/ordenes/%d/adicionar-lote' % oid, headers=_h(), json={'lote': 'ZZ-L9'})
    assert r.status_code == 409
    assert r.get_json().get('codigo') == 'ORDEN_CERRADA'


# ══ se aprueba UNA vez para todos ═══════════════════════════════════════════════

def test_aprobar_la_orden_la_deja_aprobada(app, db_clean):
    _limpiar(app)
    cli = _login(app)
    oid = _crear(cli).get_json()['id']
    r = cli.post('/api/brd/ordenes/%d/aprobar' % oid, headers=_h(),
                 json={'signature_id': _firma(app, oid)})
    assert r.status_code == 200, r.data[:300]
    assert r.get_json()['orden_aprobada'] is True
    d = cli.get('/api/brd/ordenes/%d' % oid).get_json()['orden']
    assert d['estado'] == 'aprobada' and d['aprobada_por'] == 'sebastian'


def test_sin_firma_no_se_aprueba(app, db_clean):
    _limpiar(app)
    cli = _login(app)
    oid = _crear(cli).get_json()['id']
    r = cli.post('/api/brd/ordenes/%d/aprobar' % oid, headers=_h(), json={})
    assert r.status_code == 400


def test_no_se_aprueba_dos_veces(app, db_clean):
    _limpiar(app)
    cli = _login(app)
    oid = _crear(cli).get_json()['id']
    cli.post('/api/brd/ordenes/%d/aprobar' % oid, headers=_h(),
             json={'signature_id': _firma(app, oid)})
    r = cli.post('/api/brd/ordenes/%d/aprobar' % oid, headers=_h(),
                 json={'signature_id': _firma(app, oid)})
    assert r.status_code == 409
    assert r.get_json().get('codigo') == 'YA_APROBADA'


def test_acondicionamiento_necesita_LAS_DOS_firmas(app, db_clean):
    """Como la OA-2026-102 real: 'Supervisado por: Jefe de producción' Y 'Aprobado por:
    Laura González, Jefe de calidad'. Con una sola, la orden todavía NO autoriza arrancar."""
    _limpiar(app)
    cli = _login(app)
    oid = _crear(cli, fase='acondicionamiento').get_json()['id']
    r = cli.post('/api/brd/ordenes/%d/aprobar' % oid, headers=_h(),
                 json={'signature_id': _firma(app, oid)})
    assert r.status_code == 200
    assert r.get_json()['orden_aprobada'] is False, 'se dio por aprobada con una sola firma'
    d = cli.get('/api/brd/ordenes/%d' % oid).get_json()['orden']
    assert d['estado'] == 'borrador' and d['aprobada'] is False
    r2 = cli.post('/api/brd/ordenes/%d/aprobar-calidad' % oid, headers=_h(),
                  json={'signature_id': _firma(app, oid, meaning='aprueba_orden_calidad')})
    assert r2.status_code == 200, r2.data[:300]
    d2 = cli.get('/api/brd/ordenes/%d' % oid).get_json()['orden']
    assert d2['estado'] == 'aprobada' and d2['aprobada'] is True


def test_la_aprobacion_de_calidad_es_solo_de_acondicionamiento(app, db_clean):
    _limpiar(app)
    cli = _login(app)
    oid = _crear(cli, fase='envasado').get_json()['id']
    r = cli.post('/api/brd/ordenes/%d/aprobar-calidad' % oid, headers=_h(),
                 json={'signature_id': _firma(app, oid, meaning='aprueba_orden_calidad')})
    assert r.status_code == 400
    assert r.get_json().get('codigo') == 'FASE_SIN_APROBACION_CALIDAD'


# ══ lo ADITIVO: no se toca nada de lo que ya existe ═════════════════════════════

def test_un_legajo_SIN_orden_sigue_funcionando_igual(app, db_clean):
    """La decisión de Sebastián fue 'sí, desde los nuevos'. Los legajos anteriores se
    quedan con `orden_id` NULL y no cambia nada para ellos: ni el legajo se rompe, ni la
    vista deja de responder, ni el gate los frena."""
    from database import get_db
    _limpiar(app)
    LOTE = 'ZZ-EBR-SINORDEN'
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        f = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (LOTE,)).fetchone()
        if f:
            cu.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (f[0],))
        cu.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
            "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (1, 1, LOTE, LOTE, 'en_proceso', 'envasado', 'sebastian', '2026-07-29T10:00:00', 1000))
        eid = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (LOTE,)).fetchone()[0]
        conn.commit()
    cli = _login(app)
    r = cli.get('/api/brd/ebr/%d/vista-completa' % eid)
    assert r.status_code == 200, 'un legajo sin orden dejó de abrir: %s' % r.data[:200]
    assert r.get_json().get('orden') is None, 'le inventó una orden madre'
    # Y sigue ejecutando: el gate no lo frena por no tener orden (está en beta, y aunque
    # se encendiera, el legajo conserva su propia firma como camino).
    r2 = cli.post('/api/brd/ebr/%d/observaciones' % eid, headers=_h(),
                  json={'descripcion': 'sigue andando sin orden madre'})
    assert r2.status_code in (200, 201), r2.data[:300]


def test_el_lote_hereda_la_aprobacion_de_su_orden(app, db_clean):
    """El sentido de aprobar el encabezado UNA vez es que valga para TODOS sus lotes: si
    cada lote tuviera que firmarse igual, la orden no serviría de nada."""
    from database import get_db
    _limpiar(app)
    _mbr_aprobado(app)
    cli = _login(app)
    oid = _crear(cli).get_json()['id']
    cli.post('/api/brd/ordenes/%d/aprobar' % oid, headers=_h(),
             json={'signature_id': _firma(app, oid)})
    r = cli.post('/api/brd/ordenes/%d/adicionar-lote' % oid, headers=_h(), json={'lote': 'ZZ-L2'})
    assert r.status_code == 201, r.data[:300]
    eid = r.get_json()['ebr_id']
    with app.app_context():
        ap = get_db().cursor().execute(
            "SELECT COALESCE(aprobada_orden_por,'') FROM ebr_ejecuciones WHERE id=?",
            (eid,)).fetchone()[0]
    assert ap == 'sebastian', 'el lote no heredó la aprobación de su orden: %r' % ap


def test_queda_rastro_en_audit_log(app, db_clean):
    from database import get_db
    _limpiar(app)
    cli = _login(app)
    oid = _crear(cli).get_json()['id']
    cli.post('/api/brd/ordenes/%d/aprobar' % oid, headers=_h(),
             json={'signature_id': _firma(app, oid)})
    with app.app_context():
        acc = {r[0] for r in get_db().cursor().execute(
            "SELECT accion FROM audit_log WHERE tabla='ordenes_produccion' AND registro_id=?",
            (str(oid),)).fetchall()}
    assert 'CREAR_ORDEN_PRODUCCION' in acc
    assert 'APROBAR_ORDEN_PRODUCCION' in acc


def test_la_migracion_395_es_aditiva(app, db_clean):
    """No puede tocar un solo registro existente: sin UPDATE, sin DELETE, sin DROP, y el
    vínculo NULEABLE (que es lo que deja a los legajos viejos intactos)."""
    from database import MIGRATIONS
    stmts = ' '.join(next(s for v, _, s in MIGRATIONS if v == 395))
    assert 'orden_id' in stmts and 'ordenes_produccion' in stmts
    for prohibido in ('DELETE', 'DROP', 'UPDATE '):
        assert prohibido not in stmts.upper(), (
            'la mig 395 %s: tiene que ser puramente aditiva' % prohibido)


# ══ las pantallas ═══════════════════════════════════════════════════════════════

def test_las_paginas_de_orden_cargan(app, db_clean):
    """El golden no abre pantallas: una página nueva que revienta al render se despliega
    sin que nada la cace (así se fue a producción un `get_db()` sin importar · M78)."""
    _limpiar(app)
    cli = _login(app)
    oid = _crear(cli).get_json()['id']
    r = cli.get('/planta/ordenes-batch')
    assert r.status_code == 200, r.data[:300]
    assert b'Ordenes de Produccion' in r.data
    r2 = cli.get('/planta/orden/%d' % oid)
    assert r2.status_code == 200, r2.data[:300]
    assert str(oid).encode() in r2.data, 'el id de la orden no llegó a la página'


def test_cada_boton_de_la_pagina_tiene_su_funcion(app, db_clean):
    """M112: podar o agregar deja botones vivos apuntando a lo que no existe. El chequeo
    barato es cruzar cada onclick contra las funciones declaradas en el mismo bloque."""
    import re
    from api.blueprints import brd
    for nom in ('_ORDENES_BATCH_HTML', '_ORDEN_DETALLE_BATCH_HTML'):
        t = getattr(brd, nom)
        for fn in set(re.findall(r'onclick="(\w+)\(', t)):
            assert ('function %s' % fn) in t or ('async function %s' % fn) in t, (
                '%s: el botón %s no tiene función' % (nom, fn))
        for ruta in re.findall(r"fetch\('(/api/brd/[^']+)'", t):
            assert '/api/brd/' in ruta
