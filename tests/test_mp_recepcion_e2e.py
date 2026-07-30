"""¿La materia prima SE RECEPCIONA de verdad, de punta a punta? (30-jul)

Sebastián: *"quiero que revises materias primas, que sí se recepcionen, que sí pase todo, que
no tenga bugs"*.

Este archivo no lee código: **camina el flujo real por los endpoints**, que es lo único que
prueba que una cadena funciona (M94: una pieza no está validada hasta que un E2E la recorre).
El recorrido completo, como en la planta:

    OC autorizada → recepción administrativa (Catalina cuenta bultos, lote provisional)
        → el material entra en CUARENTENA y NO cuenta como stock
        → Calidad hace el F01 con el lote REAL, el peso de balanza y el vencimiento
        → el KARDEX queda con el lote real (el rótulo se imprime de ahí)
        → F02 aprobado → el lote pasa a VIGENTE y recién ahí SUMA al stock disponible

Y de paso verifica los guards que ya costaron caídas: código con espacios, factura obligatoria,
sobre-recepción, doble envío, y un ítem de OC sin código (el 500 de producción del 10-jul).
"""
from .conftest import TEST_PASSWORD, csrf_headers

OC = 'OC-ZZE2E-MP'
MP = 'MP-ZZE2E'
LOTE_REAL = 'LOTE-PROV-991'


def _login(app, usuario='sebastian'):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pudo entrar %s' % usuario
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _sembrar(app, cantidad_g=15000, codigo=MP):
    """OC autorizada con un ítem de MP + la MP en el maestro. Limpia ANTES (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (OC,))
        cur.execute("DELETE FROM solicitudes_compra WHERE numero_oc=?", (OC,))
        cur.execute("DELETE FROM ordenes_compra WHERE numero_oc=?", (OC,))
        cur.execute("DELETE FROM oc_recepcion_dedup WHERE numero_oc=?", (OC,))
        cur.execute("DELETE FROM movimientos WHERE material_id=?", (codigo,))
        cur.execute("DELETE FROM recepcion_tecnica_doc WHERE codigo_insumo=?", (codigo,))
        cur.execute(
            "INSERT INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
            "VALUES (?,?,?,1) ON CONFLICT (codigo_mp) DO UPDATE SET activo=1",
            (codigo, 'TEST INCI E2E', 'MP de prueba E2E'))
        cur.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, categoria, fecha, "
                    "valor_total, creado_por) VALUES (?,?,?,?,?,?,?)",
                    (OC, 'PROVEEDOR E2E', 'Autorizada', 'MP', '2026-07-30', 1000, 'catalina'))
        cur.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, "
                    "cantidad_g, precio_unitario) VALUES (?,?,?,?,?)",
                    (OC, codigo, 'MP de prueba E2E', cantidad_g, 1))
        cur.execute("INSERT INTO solicitudes_compra (numero, fecha, estado, solicitante, "
                    "numero_oc, categoria) VALUES (?,?,?,?,?,?)",
                    ('SOL-' + OC, '2026-07-30', 'Aprobada', 'catalina', OC, 'Materia Prima'))
        conn.commit()


def _recibir(cli, items, token, **extra):
    body = {'observaciones_recepcion': '', 'tiene_discrepancias': 0,
            'items_recepcion': items, 'receptor_nombre': 'Catalina',
            'recepcion_id': token}
    body.update(extra)
    return cli.post('/api/ordenes-compra/%s/recibir' % OC, headers=_h(), json=body)



def _firmar(cli, record_id, meaning='libera', tabla='movimientos'):
    """El F02 exige firma electronica Part 11 para disponer el lote. NO es una traba del
    test: es el control que hace que una liberacion tenga un responsable con nombre."""
    rc = cli.post('/api/sign/challenge', json={'password': TEST_PASSWORD}, headers=csrf_headers())
    assert rc.status_code in (200, 201), rc.data[:200]
    tok = rc.get_json()['token']
    rs = cli.post('/api/sign', json={'record_table': tabla, 'record_id': str(record_id),
                                     'meaning': meaning, 'challenge_token': tok},
                  headers=csrf_headers())
    assert rs.status_code == 201, rs.data[:300]
    return rs.get_json()['signature_id']


def _stock_disponible(app, codigo=MP):
    """El canónico de la regla #4: excluye cuarentena y compañía."""
    from database import get_db
    with app.app_context():
        r = get_db().cursor().execute(
            "SELECT COALESCE(SUM(CASE "
            "  WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad "
            "  WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -cantidad ELSE 0 END),0) "
            "FROM movimientos WHERE material_id=? "
            "AND UPPER(COALESCE(estado_lote,'')) NOT IN "
            "('CUARENTENA','CUARENTENA_EXTENDIDA','VENCIDO','RECHAZADO','AGOTADO','BLOQUEADO')",
            (codigo,)).fetchone()
    return float(r[0] or 0)


def _mov(app, codigo=MP):
    from database import get_db
    with app.app_context():
        return get_db().cursor().execute(
            "SELECT id, cantidad, COALESCE(lote,''), COALESCE(estado_lote,''), "
            "       COALESCE(fecha_vencimiento,''), COALESCE(estanteria,'') "
            "FROM movimientos WHERE material_id=? AND tipo='Entrada' ORDER BY id DESC LIMIT 1",
            (codigo,)).fetchone()


# ══ EL RECORRIDO COMPLETO ═══════════════════════════════════════════════════════

def test_e2e_de_la_OC_al_stock_disponible(app, db_clean):
    """El camino entero. Si algo de la cadena está roto, este test lo dice."""
    _sembrar(app, 15000)
    cat = _login(app, 'catalina')

    # 1 · recepción administrativa: cuenta bultos, sin el lote (eso es de Calidad)
    r = _recibir(cat, [{'codigo_mp': MP, 'cantidad_recibida': 15000}], 'ZZE2E-1')
    assert r.status_code == 200, 'la recepción administrativa falló: %s' % r.data[:400]

    m = _mov(app)
    assert m is not None, 'no quedó Entrada en el kardex: la MP no se recepcionó'
    assert float(m[1]) == 15000
    assert m[3].upper() == 'CUARENTENA', 'entró sin cuarentena (estado %r)' % m[3]
    assert _stock_disponible(app) == 0, 'la cuarentena está contando como stock disponible'
    mov_id = m[0]

    # 2 · le llega a Calidad
    r = _login(app, 'laura').get('/api/calidad/recepcion-pipeline')
    assert r.status_code == 200, r.data[:300]
    mios = [x for x in (r.get_json().get('lotes') or [])
            if x.get('codigo_mp') == MP and x.get('tipo') != 'MEE']
    assert mios, 'la recepción no le llegó a Calidad'

    # 3 · F01: lote REAL, peso de balanza, vencimiento y ubicación
    lau = _login(app, 'laura')
    r = lau.post('/api/calidad/recepcion-tecnica', headers=_h(), json={
        'mov_id': mov_id, 'origen': 'MP', 'numero_oc': OC,
        'codigo_insumo': MP, 'nombre_insumo': 'MP de prueba E2E',
        'lote_proveedor': LOTE_REAL, 'cantidad_recibida': 14800,
        'proveedor': 'PROVEEDOR E2E', 'fecha_recepcion': '2026-07-30',
        'fecha_vencimiento': '2028-01-31',
        'ubic_tipo': 'estanteria', 'ubic_estanteria': 'A3', 'ubic_posicion': '2',
        'crit_rotulado': 1, 'crit_empaque': 1, 'crit_hoja_seguridad': 1,
        'crit_ficha_tecnica': 1, 'crit_coa': 1, 'crit_doc_coincide': 1,
        'resultado': 'conforme', 'realiza_por': 'laura', 'aprueba_por': 'laura'})
    assert r.status_code in (200, 201), 'el F01 falló: %s' % r.data[:400]

    # 4 · el KARDEX quedó con el lote REAL (el rótulo se imprime de acá · M109)
    m2 = _mov(app)
    assert m2[2] == LOTE_REAL, 'el kardex se quedó con el lote provisional: %r' % m2[2]
    assert float(m2[1]) == 14800, 'el kardex no tomó el peso de balanza: %r' % m2[1]
    assert m2[4][:10] == '2028-01-31', 'sin vencimiento el cron de vencidos nunca lo marca'

    # 5 · el rótulo imprime el lote real, no el provisional
    r = lau.get('/rotulo-recepcion/%s/%s/14800' % (MP, LOTE_REAL))
    assert r.status_code == 200, r.data[:200]
    assert LOTE_REAL in r.data.decode('utf-8', 'replace')

    # 6 · F02 aprobado → recién ahí es stock usable
    r = lau.post('/api/calidad/certificado-analisis', headers=_h(), json={
        'mov_id': mov_id, 'codigo_insumo': MP, 'nombre_insumo': 'MP de prueba E2E',
        'lote': LOTE_REAL, 'lote_proveedor': LOTE_REAL, 'resultado': 'aprobado',
        'responsable_analisis': 'laura', 'aprobo_por': 'laura',
        'fecha_analisis': '2026-07-30',
        'signature_id': _firmar(lau, mov_id)})
    assert r.status_code in (200, 201), 'el F02 falló: %s' % r.data[:400]
    assert _stock_disponible(app) == 14800, (
        'liberado y NO cuenta como stock disponible: %r' % _stock_disponible(app))


def test_la_recepcion_queda_auditada(app, db_clean):
    """Part 11: una recepción sin rastro es una recepción que no se puede defender."""
    _sembrar(app)
    _recibir(_login(app, 'catalina'), [{'codigo_mp': MP, 'cantidad_recibida': 15000}], 'ZZE2E-2')
    from database import get_db
    with app.app_context():
        n = get_db().cursor().execute(
            "SELECT COUNT(*) FROM audit_log WHERE tabla IN ('movimientos','ordenes_compra') "
            "AND (COALESCE(detalle,'') LIKE ? OR COALESCE(despues,'') LIKE ?)",
            ('%' + OC + '%', '%' + OC + '%')).fetchone()[0]
    assert n > 0, 'la recepción no dejó rastro en audit_log'


# ══ LOS GUARDS QUE YA COSTARON CAÍDAS ═══════════════════════════════════════════

def test_un_item_de_OC_SIN_codigo_no_tumba_la_recepcion(app, db_clean):
    """El 500 de producción del 10-jul (M81): un ítem con `codigo_mp` vacío disparaba el
    trigger de PG, el `except` lo confundía con un drift de esquema y reintentaba un INSERT
    que reventaba igual. Catalina veía 'error interno del servidor'."""
    _sembrar(app)
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.cursor().execute(
            "INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g, "
            "precio_unitario) VALUES (?,'','Flete',1,0)", (OC,))
        conn.commit()
    r = _recibir(_login(app, 'catalina'),
                 [{'codigo_mp': MP, 'cantidad_recibida': 15000},
                  {'codigo_mp': '', 'cantidad_recibida': 1}], 'ZZE2E-3')
    assert r.status_code == 200, 'un ítem sin código volvió a tumbar la recepción: %s' % r.data[:400]
    assert _mov(app) is not None, 'la MP buena no entró'


def test_doble_envio_no_duplica_la_recepcion(app, db_clean):
    """Sin el token, un doble click mete la mercancía dos veces al kardex."""
    _sembrar(app)
    cat = _login(app, 'catalina')
    r1 = _recibir(cat, [{'codigo_mp': MP, 'cantidad_recibida': 15000}], 'ZZE2E-4')
    assert r1.status_code == 200, r1.data[:300]
    r2 = _recibir(cat, [{'codigo_mp': MP, 'cantidad_recibida': 15000}], 'ZZE2E-4')
    assert r2.status_code == 409, 'aceptó la misma recepción dos veces: %s' % r2.data[:300]
    from database import get_db
    with app.app_context():
        n = get_db().cursor().execute(
            "SELECT COUNT(*) FROM movimientos WHERE material_id=? AND tipo='Entrada'",
            (MP,)).fetchone()[0]
    assert n == 1, 'quedaron %d entradas de la misma recepción' % n


def test_recepcion_parcial_y_despues_el_resto(app, db_clean):
    """Lo normal en la planta: llega parte hoy y parte la semana que viene. Con token
    distinto cada envío, las dos entran."""
    _sembrar(app, 15000)
    cat = _login(app, 'catalina')
    assert _recibir(cat, [{'codigo_mp': MP, 'cantidad_recibida': 9000}],
                    'ZZE2E-5a').status_code == 200
    assert _recibir(cat, [{'codigo_mp': MP, 'cantidad_recibida': 6000}],
                    'ZZE2E-5b').status_code == 200
    from database import get_db
    with app.app_context():
        tot = get_db().cursor().execute(
            "SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE material_id=? AND tipo='Entrada'",
            (MP,)).fetchone()[0]
    assert float(tot) == 15000, 'las parciales no suman lo pedido: %r' % tot


def test_manual_sin_OC_entra_en_cuarentena(app, db_clean):
    """La otra puerta: ingreso manual (ajustes, material sin OC). También en cuarentena."""
    _sembrar(app)
    r = _login(app, 'catalina').post('/api/recepcion', headers=_h(), json={
        'codigo_mp': MP, 'cantidad': 500, 'lote': 'MAN-1',
        'nombre_mp': 'MP de prueba E2E'})
    assert r.status_code in (200, 201), r.data[:400]
    m = _mov(app)
    assert m is not None and m[3].upper() == 'CUARENTENA', 'el ingreso manual no quedó retenido'
    assert _stock_disponible(app) == 0


def test_un_codigo_con_espacios_se_rechaza(app, db_clean):
    """Una factura de servicios tecleada como MP no puede entrar a la bodega (9-jul)."""
    r = _login(app, 'catalina').post('/api/recepcion', headers=_h(), json={
        'codigo_mp': 'Factura junio', 'cantidad': 1, 'lote': 'X'})
    assert r.status_code == 400, r.data[:300]
    assert (r.get_json() or {}).get('codigo_invalido') is True


def test_con_OC_la_factura_es_obligatoria(app, db_clean):
    """Control contable: si se vinculó una OC, tiene que venir el número de factura."""
    _sembrar(app)
    r = _login(app, 'catalina').post('/api/recepcion', headers=_h(), json={
        'codigo_mp': MP, 'cantidad': 100, 'lote': 'L1', 'numero_oc': OC})
    assert r.status_code == 400, r.data[:300]
    assert (r.get_json() or {}).get('factura_obligatoria') is True


def test_no_se_recibe_mas_de_lo_pedido_sin_forzar(app, db_clean):
    """Recibir 3× lo comprado suele ser un cero de más tecleado."""
    _sembrar(app, 1000)
    r = _login(app, 'catalina').post('/api/recepcion', headers=_h(), json={
        'codigo_mp': MP, 'cantidad': 5000, 'lote': 'L1', 'numero_oc': OC,
        'numero_factura': 'F-1'})
    assert r.status_code in (400, 409, 422), r.data[:300]
    assert (r.get_json() or {}).get('cantidad_excede_oc') is True
