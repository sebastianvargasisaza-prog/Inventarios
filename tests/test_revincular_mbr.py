"""Re-vincular un legajo abierto a la versión APROBADA de su MBR (26-jul).

Al aprobar una versión nueva del MBR (cargar el instructivo real), la anterior pasa a `obsoleto`
pero los legajos YA ABIERTOS siguen apuntando a la vieja: el operario ve los pasos de relleno
aunque el procedimiento aprobado exista. Los legajos nuevos sí toman la aprobada.

Las tres líneas que esta herramienta NO puede cruzar:
  · un legajo liberado/rechazado/completado es INMUTABLE (mig 111)
  · un legajo que YA ejecutó un paso no se re-vincula solo: cambiar el procedimiento con el lote
    en marcha es una desviación que decide Calidad
  · una firma jamás se borra (sólo se reemplazan pasos en estado `pendiente`)
"""
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, usuario='sebastian'):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _csrf(c):
    h = dict(csrf_headers())
    h["X-CSRF-Token"] = c.get("/api/csrf-token").get_json()["csrf_token"]
    h["Content-Type"] = "application/json"
    return h


def _mbr(conn, producto, pasos, version, estado='aprobado'):
    cur = conn.cursor()
    cur.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                "VALUES (?,?,'draft',10000,'test')", (producto, version))
    mid = cur.lastrowid
    for i, d in enumerate(pasos, 1):
        cur.execute("INSERT INTO mbr_pasos (mbr_template_id, orden, fase, descripcion, tipo_paso) "
                    "VALUES (?,?,'fabricacion',?,'mezclado')", (mid, i, d))
    cur.execute("UPDATE mbr_templates SET estado=? WHERE id=?", (estado, mid))
    conn.commit()
    return mid


def _escenario(app, producto, lote, estado_ebr='iniciado'):
    """MBR v1 obsoleto con 1 paso de relleno + v2 aprobada con el instructivo · EBR en la v1."""
    from database import get_db
    with app.app_context():
        conn = get_db()
        viejo = _mbr(conn, producto, ['Fabricar el producto siguiendo procedimiento aprobado'],
                     1, estado='obsoleto')
        nuevo = _mbr(conn, producto, ['Paso 1. Calentar fase A a 75°C',
                                      'Paso 2. Agregar fase B con agitación',
                                      'Paso 3. Enfriar a 40°C y ajustar pH'], 2)
        cur = conn.cursor()
        # El producto NO vive en ebr_ejecuciones: sale del MBR al que apunta.
        cur.execute("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, numero_op, "
                    "estado, iniciado_por, iniciado_at_utc, fase, cantidad_objetivo_g) "
                    "VALUES (?,1,?,?,?,'sebastian','2026-07-26 10:00:00','fabricacion',10000)",
                    (viejo, lote, 'OP-TEST-' + lote, estado_ebr))
        ebr = cur.lastrowid
        cur.execute("INSERT INTO ebr_pasos_ejecutados (ebr_id, mbr_paso_id, orden, descripcion, "
                    "tipo_paso, estado, fase) VALUES (?,?,1,'Fabricar el producto siguiendo "
                    "procedimiento aprobado','mezclado','pendiente','fabricacion')",
                    (ebr, viejo))
        conn.commit()
        return ebr, viejo, nuevo


def _pasos(app, ebr):
    from database import get_db
    with app.app_context():
        return [r[0] for r in get_db().execute(
            "SELECT descripcion FROM ebr_pasos_ejecutados WHERE ebr_id=? ORDER BY orden",
            (ebr,)).fetchall()]


def test_el_legajo_abierto_recibe_el_instructivo_aprobado(app):
    ebr, viejo, nuevo = _escenario(app, 'REVINC PRODUCTO A', 'LOTE-RV-1')
    c = _login(app)

    prev = c.get("/api/brd/mbr-desactualizados").get_json()
    mio = [x for x in prev['plan'] if x['ebr_id'] == ebr]
    assert mio and mio[0]['movible'] is True, prev
    assert mio[0]['mbr_aprobado'] == nuevo and mio[0]['pasos_nuevos'] == 3

    # dry_run no toca nada
    r = c.post("/api/brd/revincular-mbr", headers=_csrf(c), json={'ebr_ids': [ebr]})
    assert r.get_json()['dry_run'] is True
    assert len(_pasos(app, ebr)) == 1

    d = c.post("/api/brd/revincular-mbr", headers=_csrf(c),
               json={'ebr_ids': [ebr], 'aplicar': True}).get_json()
    assert len(d['revinculados']) == 1, d
    pasos = _pasos(app, ebr)
    assert len(pasos) == 3, pasos
    assert 'Calentar fase A a 75°C' in pasos[0], 'el instructivo real tiene que llegar al piso'


def test_un_lote_que_YA_ejecuto_un_paso_no_se_toca(app):
    """Cambiar el procedimiento con el lote en marcha es una desviación, no un ajuste."""
    ebr, _v, _n = _escenario(app, 'REVINC PRODUCTO B', 'LOTE-RV-2')
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.execute("UPDATE ebr_pasos_ejecutados SET estado='completado', "
                     "operario_username='mayerlin' WHERE ebr_id=?", (ebr,))
        conn.commit()
    c = _login(app)
    prev = [x for x in c.get("/api/brd/mbr-desactualizados").get_json()['plan'] if x['ebr_id'] == ebr]
    assert prev and prev[0]['movible'] is False
    assert 'desviación' in prev[0]['motivo']
    d = c.post("/api/brd/revincular-mbr", headers=_csrf(c),
               json={'ebr_ids': [ebr], 'aplicar': True}).get_json()
    assert d['revinculados'] == [], d
    assert len(d['saltados']) == 1
    pasos = _pasos(app, ebr)
    assert len(pasos) == 1 and 'procedimiento aprobado' in pasos[0], 'la firma no se puede perder'


def test_un_legajo_liberado_es_inmutable(app):
    ebr, _v, _n = _escenario(app, 'REVINC PRODUCTO C', 'LOTE-RV-3', estado_ebr='liberado')
    c = _login(app)
    prev = [x for x in c.get("/api/brd/mbr-desactualizados").get_json()['plan'] if x['ebr_id'] == ebr]
    assert prev == [], 'un lote liberado no puede ni aparecer en la lista'


def test_correrlo_dos_veces_no_duplica_pasos(app):
    ebr, _v, _n = _escenario(app, 'REVINC PRODUCTO D', 'LOTE-RV-4')
    c = _login(app)
    c.post("/api/brd/revincular-mbr", headers=_csrf(c), json={'ebr_ids': [ebr], 'aplicar': True})
    d2 = c.post("/api/brd/revincular-mbr", headers=_csrf(c),
                json={'ebr_ids': [ebr], 'aplicar': True}).get_json()
    assert d2['revinculados'] == [], d2
    assert len(_pasos(app, ebr)) == 3


def test_queda_auditado(app):
    ebr, viejo, nuevo = _escenario(app, 'REVINC PRODUCTO E', 'LOTE-RV-5')
    c = _login(app)
    c.post("/api/brd/revincular-mbr", headers=_csrf(c), json={'ebr_ids': [ebr], 'aplicar': True})
    from database import get_db
    with app.app_context():
        r = get_db().execute(
            "SELECT usuario, antes, despues FROM audit_log WHERE accion='REVINCULAR_MBR_EBR' "
            "AND registro_id=?", (str(ebr),)).fetchone()
    assert r is not None, 'una corrección sobre un registro de lote tiene que dejar rastro'
    assert r[0] == 'sebastian'
    assert str(viejo) in str(r[1]) and str(nuevo) in str(r[2])


def test_solo_calidad_o_admin_pueden_revincular(app):
    from .conftest import TEST_PASSWORD as _P
    c = app.test_client()
    c.post("/login", data={"username": "valentina", "password": _P}, headers=csrf_headers())
    r = c.post("/api/brd/revincular-mbr", headers=_csrf(c), json={'aplicar': True})
    assert r.status_code == 403, r.status_code
