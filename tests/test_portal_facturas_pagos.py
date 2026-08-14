"""Portal del cliente · facturas, pagos que él carga, documentos y consumo.

Sebastián 14-ago-2026: "piensa qué necesitan tener ellos en su módulo: facturas,
pagos que los carguen, análisis".

Lo que estos tests fijan, que es lo que puede salir caro:
  - un cliente NUNCA ve la factura de otro;
  - sin puente con la cuenta de facturación, el portal lo DICE (una lista vacía se
    lee como "no debo nada", que es lo contrario de "no se pudo cruzar");
  - un pago reportado NO es un asiento: la contabilidad se mueve sólo al conciliar,
    y conciliar dos veces no cobra dos veces;
  - el certificado de un lote ajeno no se sirve.
"""
import io
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


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


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _q(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _limpiar():
    """Limpiar ANTES de sembrar · un `finally` no corre si el proceso muere (M103)."""
    for sql in (
        "DELETE FROM portal_pagos_reportados WHERE cliente_id LIKE 'ZPF%'",
        "DELETE FROM portal_clientes_credenciales WHERE cliente_id LIKE 'ZPF%'",
        "DELETE FROM facturas_pagos WHERE numero_factura LIKE 'ZPF-%'",
        "DELETE FROM facturas WHERE numero LIKE 'ZPF-%'",
        "DELETE FROM clientes WHERE codigo LIKE 'ZPF%'",
        "DELETE FROM pedidos_b2b WHERE cliente_id LIKE 'ZPF%'",
    ):
        try:
            _exec(sql)
        except Exception:
            pass


def _cliente_portal(app, slug='ZPF1', nombre='Cliente Uno', email=None):
    """Crea la credencial por el endpoint real y devuelve un cliente logueado."""
    email = email or (slug.lower() + '@zpf.test')
    adm = _login(app)
    r = adm.post('/api/admin/portal/credenciales', json={
        'cliente_id': slug, 'cliente_nombre': nombre,
        'email': email, 'password': 'ClavePortal123',
    }, headers=_h())
    assert r.status_code in (200, 201), r.data
    cred_id = r.get_json().get('id')
    cli = app.test_client()
    r2 = cli.post('/api/portal/login', json={'email': email, 'password': 'ClavePortal123'})
    assert r2.status_code == 200, r2.data
    return cli, cred_id


def _factura(numero, cliente_ref, total, vence='2026-12-31', estado='Emitida'):
    return _exec(
        "INSERT INTO facturas (numero, tipo, cliente_id, cliente_nombre, empresa, fecha_emision, "
        "fecha_vencimiento, total, estado) VALUES (?,'Factura',?,?,'ANIMUS','2026-08-01',?,?,?)",
        (numero, cliente_ref, 'Cliente Uno', vence, total, estado))


# ══════════════════════════════════════════════════════════════════════
# Facturas
# ══════════════════════════════════════════════════════════════════════

def test_sin_enlace_el_portal_lo_dice_en_vez_de_mostrar_vacio(app, db_clean):
    """Una lista vacía significaría "no tenés facturas". El motivo se declara (M154)."""
    _limpiar()
    cli, _ = _cliente_portal(app, 'ZPFSOLO', 'Cliente Sin Cuenta')
    d = cli.get('/api/portal/facturas').get_json()
    assert d['enlazado'] is False
    assert d['motivo'] == 'sin_cuenta'
    assert d['mensaje'], 'tiene que explicar POR QUÉ no hay facturas'
    assert d['facturas'] == []


def test_el_cliente_ve_sus_facturas_con_el_saldo_real(app, db_clean):
    _limpiar()
    ref = _exec("INSERT INTO clientes (codigo, nombre, activo) VALUES ('ZPF1','Cliente Uno',1)")
    _factura('ZPF-001', ref, 1000000)
    _exec("INSERT INTO facturas_pagos (numero_factura, fecha, monto, medio) "
          "VALUES ('ZPF-001','2026-08-05',400000,'Transferencia')")
    cli, _ = _cliente_portal(app, 'ZPF1', 'Cliente Uno')

    d = cli.get('/api/portal/facturas').get_json()
    assert d['enlazado'] is True
    assert d['como'] == 'codigo', 'cruzó por el código del cliente'
    f = [x for x in d['facturas'] if x['numero'] == 'ZPF-001'][0]
    # El saldo sale de los pagos REGISTRADOS, no de un campo aparte (M5).
    assert f['total'] == 1000000 and f['pagado'] == 400000 and f['saldo'] == 600000
    assert d['saldo_total'] == 600000


def test_un_cliente_no_ve_la_factura_de_otro(app, db_clean):
    _limpiar()
    ref1 = _exec("INSERT INTO clientes (codigo, nombre, activo) VALUES ('ZPF1','Cliente Uno',1)")
    ref2 = _exec("INSERT INTO clientes (codigo, nombre, activo) VALUES ('ZPF2','Cliente Dos',1)")
    _factura('ZPF-001', ref1, 500000)
    _factura('ZPF-002', ref2, 900000)
    cli, _ = _cliente_portal(app, 'ZPF1', 'Cliente Uno')

    numeros = [f['numero'] for f in cli.get('/api/portal/facturas').get_json()['facturas']]
    assert 'ZPF-001' in numeros
    assert 'ZPF-002' not in numeros, 'AISLAMIENTO: vio la factura de otro cliente'


def test_la_factura_vencida_se_marca(app, db_clean):
    _limpiar()
    ref = _exec("INSERT INTO clientes (codigo, nombre, activo) VALUES ('ZPF1','Cliente Uno',1)")
    _factura('ZPF-VIEJA', ref, 300000, vence='2020-01-01')
    _factura('ZPF-NUEVA', ref, 300000, vence='2099-01-01')
    cli, _ = _cliente_portal(app, 'ZPF1', 'Cliente Uno')

    d = cli.get('/api/portal/facturas').get_json()
    porn = {f['numero']: f for f in d['facturas']}
    assert porn['ZPF-VIEJA']['vencida'] is True
    assert porn['ZPF-NUEVA']['vencida'] is False
    assert d['vencido_total'] == 300000


# ══════════════════════════════════════════════════════════════════════
# Pagos que reporta el cliente
# ══════════════════════════════════════════════════════════════════════

def test_reportar_un_pago_no_mueve_la_contabilidad(app, db_clean):
    """El aviso del cliente no es un hecho de dinero: la plata entra al conciliar (M168)."""
    _limpiar()
    ref = _exec("INSERT INTO clientes (codigo, nombre, activo) VALUES ('ZPF1','Cliente Uno',1)")
    _factura('ZPF-001', ref, 800000)
    cli, _ = _cliente_portal(app, 'ZPF1', 'Cliente Uno')

    r = cli.post('/api/portal/pagos', data={
        'factura_numero': 'ZPF-001', 'monto': '800000',
        'fecha_pago': '2026-08-10', 'metodo': 'Transferencia', 'referencia': 'ABC123',
    }, content_type='multipart/form-data')
    assert r.status_code == 201, r.data
    assert _q("SELECT estado FROM portal_pagos_reportados WHERE cliente_id='ZPF1'")[0][0] == 'reportado'
    # y la contabilidad NO se movió
    assert _q("SELECT COUNT(*) FROM facturas_pagos WHERE numero_factura='ZPF-001'")[0][0] == 0
    assert _q("SELECT estado FROM facturas WHERE numero='ZPF-001'")[0][0] == 'Emitida'


def test_el_mismo_pago_dos_veces_no_se_duplica(app, db_clean):
    _limpiar()
    ref = _exec("INSERT INTO clientes (codigo, nombre, activo) VALUES ('ZPF1','Cliente Uno',1)")
    _factura('ZPF-001', ref, 800000)
    cli, _ = _cliente_portal(app, 'ZPF1', 'Cliente Uno')
    cuerpo = {'factura_numero': 'ZPF-001', 'monto': '800000', 'fecha_pago': '2026-08-10'}

    r1 = cli.post('/api/portal/pagos', data=dict(cuerpo), content_type='multipart/form-data')
    r2 = cli.post('/api/portal/pagos', data=dict(cuerpo), content_type='multipart/form-data')
    assert r1.status_code == 201 and r2.status_code == 200
    assert r2.get_json().get('duplicado') is True
    assert _q("SELECT COUNT(*) FROM portal_pagos_reportados WHERE cliente_id='ZPF1'")[0][0] == 1


def test_no_se_puede_reportar_contra_la_factura_de_otro(app, db_clean):
    _limpiar()
    _exec("INSERT INTO clientes (codigo, nombre, activo) VALUES ('ZPF1','Cliente Uno',1)")
    ref2 = _exec("INSERT INTO clientes (codigo, nombre, activo) VALUES ('ZPF2','Cliente Dos',1)")
    _factura('ZPF-002', ref2, 900000)
    cli, _ = _cliente_portal(app, 'ZPF1', 'Cliente Uno')

    r = cli.post('/api/portal/pagos', data={'factura_numero': 'ZPF-002', 'monto': '100000'},
                 content_type='multipart/form-data')
    assert r.status_code == 403, r.data


def test_el_comprobante_que_no_se_pudo_guardar_se_declara(app, db_clean):
    """Sin R2 configurado el aviso queda igual, pero se DICE que el archivo no (M198)."""
    _limpiar()
    ref = _exec("INSERT INTO clientes (codigo, nombre, activo) VALUES ('ZPF1','Cliente Uno',1)")
    _factura('ZPF-001', ref, 500000)
    cli, _ = _cliente_portal(app, 'ZPF1', 'Cliente Uno')

    r = cli.post('/api/portal/pagos', data={
        'monto': '500000', 'factura_numero': 'ZPF-001',
        'archivo': (io.BytesIO(b'%PDF-1.4 comprobante'), 'comprobante.pdf'),
    }, content_type='multipart/form-data')
    assert r.status_code == 201, r.data
    d = r.get_json()
    assert d['archivo_estado'] in ('guardado', 'sin_almacenamiento', 'fallo_guardado')
    if d['archivo_estado'] != 'guardado':
        assert d['aviso'], 'si el comprobante no quedó, hay que decirlo'


def test_un_archivo_que_no_es_comprobante_se_rechaza(app, db_clean):
    _limpiar()
    _exec("INSERT INTO clientes (codigo, nombre, activo) VALUES ('ZPF1','Cliente Uno',1)")
    cli, _ = _cliente_portal(app, 'ZPF1', 'Cliente Uno')
    r = cli.post('/api/portal/pagos', data={
        'monto': '1000', 'archivo': (io.BytesIO(b'MZ ejecutable'), 'virus.exe'),
    }, content_type='multipart/form-data')
    assert r.status_code == 400, r.data


# ══════════════════════════════════════════════════════════════════════
# Conciliación (backoffice)
# ══════════════════════════════════════════════════════════════════════

def test_conciliar_cobra_por_el_camino_canonico_y_una_sola_vez(app, db_clean):
    _limpiar()
    ref = _exec("INSERT INTO clientes (codigo, nombre, activo) VALUES ('ZPF1','Cliente Uno',1)")
    _factura('ZPF-001', ref, 800000)
    cli, _ = _cliente_portal(app, 'ZPF1', 'Cliente Uno')
    cli.post('/api/portal/pagos', data={'factura_numero': 'ZPF-001', 'monto': '800000',
                                        'fecha_pago': '2026-08-10'},
             content_type='multipart/form-data')
    pago_id = _q("SELECT id FROM portal_pagos_reportados WHERE cliente_id='ZPF1'")[0][0]

    adm = _login(app)
    r = adm.post(f'/api/admin/portal/pagos/{pago_id}/conciliar', json={}, headers=_h())
    assert r.status_code == 200, r.data
    # el cobro entró por facturas_pagos (el único escritor) y la factura quedó Pagada
    assert _q("SELECT COUNT(*) FROM facturas_pagos WHERE numero_factura='ZPF-001'")[0][0] == 1
    assert _q("SELECT estado FROM facturas WHERE numero='ZPF-001'")[0][0] == 'Pagada'
    assert _q("SELECT estado FROM portal_pagos_reportados WHERE id=?", (pago_id,))[0][0] == 'conciliado'

    # segundo clic: no cobra de nuevo
    r2 = adm.post(f'/api/admin/portal/pagos/{pago_id}/conciliar', json={}, headers=_h())
    assert r2.status_code == 409, r2.data
    assert _q("SELECT COUNT(*) FROM facturas_pagos WHERE numero_factura='ZPF-001'")[0][0] == 1


def test_conciliar_de_mas_no_pasa_el_guard_de_over_payment(app, db_clean):
    _limpiar()
    ref = _exec("INSERT INTO clientes (codigo, nombre, activo) VALUES ('ZPF1','Cliente Uno',1)")
    _factura('ZPF-001', ref, 100000)
    cli, _ = _cliente_portal(app, 'ZPF1', 'Cliente Uno')
    cli.post('/api/portal/pagos', data={'factura_numero': 'ZPF-001', 'monto': '999999'},
             content_type='multipart/form-data')
    pago_id = _q("SELECT id FROM portal_pagos_reportados WHERE cliente_id='ZPF1'")[0][0]

    adm = _login(app)
    r = adm.post(f'/api/admin/portal/pagos/{pago_id}/conciliar', json={}, headers=_h())
    assert r.status_code == 422, r.data
    assert r.get_json().get('codigo') == 'OVER_PAYMENT'
    # y el reporte NO quedó marcado como conciliado
    assert _q("SELECT estado FROM portal_pagos_reportados WHERE id=?", (pago_id,))[0][0] == 'reportado'
    assert _q("SELECT COUNT(*) FROM facturas_pagos WHERE numero_factura='ZPF-001'")[0][0] == 0


def test_rechazar_exige_motivo_y_el_cliente_lo_lee(app, db_clean):
    _limpiar()
    _exec("INSERT INTO clientes (codigo, nombre, activo) VALUES ('ZPF1','Cliente Uno',1)")
    cli, _ = _cliente_portal(app, 'ZPF1', 'Cliente Uno')
    cli.post('/api/portal/pagos', data={'monto': '50000'}, content_type='multipart/form-data')
    pago_id = _q("SELECT id FROM portal_pagos_reportados WHERE cliente_id='ZPF1'")[0][0]

    adm = _login(app)
    assert adm.post(f'/api/admin/portal/pagos/{pago_id}/rechazar', json={},
                    headers=_h()).status_code == 400
    r = adm.post(f'/api/admin/portal/pagos/{pago_id}/rechazar',
                 json={'motivo': 'El comprobante es de otra factura'}, headers=_h())
    assert r.status_code == 200, r.data
    mio = [p for p in cli.get('/api/portal/pagos').get_json()['pagos'] if p['id'] == pago_id][0]
    assert mio['estado'] == 'rechazado'
    assert 'otra factura' in mio['motivo']


def test_el_enlace_de_facturacion_no_puede_apuntar_a_dos_portales(app, db_clean):
    """Enlazar mal deja a un cliente viendo las facturas de otro."""
    _limpiar()
    ref = _exec("INSERT INTO clientes (codigo, nombre, activo) VALUES ('ZPFX','Cuenta Compartida',1)")
    _cli1, cred1 = _cliente_portal(app, 'ZPFA', 'Cliente A')
    _cli2, cred2 = _cliente_portal(app, 'ZPFB', 'Cliente B')
    adm = _login(app)

    r1 = adm.post(f'/api/admin/portal/credenciales/{cred1}/enlazar',
                  json={'cliente_ref_id': ref}, headers=_h())
    assert r1.status_code == 200, r1.data
    r2 = adm.post(f'/api/admin/portal/credenciales/{cred2}/enlazar',
                  json={'cliente_ref_id': ref}, headers=_h())
    assert r2.status_code == 409, r2.data
    assert r2.get_json().get('codigo') == 'YA_ENLAZADA'


# ══════════════════════════════════════════════════════════════════════
# Documentos y consumo
# ══════════════════════════════════════════════════════════════════════

def test_el_certificado_de_un_lote_ajeno_no_se_sirve(app, db_clean):
    _limpiar()
    _exec("INSERT INTO clientes (codigo, nombre, activo) VALUES ('ZPF1','Cliente Uno',1)")
    cli, _ = _cliente_portal(app, 'ZPF1', 'Cliente Uno')
    r = cli.get('/portal/coa/LOTE-QUE-NO-ES-MIO')
    assert r.status_code == 403, r.data


def test_documentos_declara_el_lote_que_todavia_no_se_libero(app, db_clean):
    _limpiar()
    cli, _ = _cliente_portal(app, 'ZPF1', 'Cliente Uno')
    d = cli.get('/api/portal/documentos').get_json()
    assert 'documentos' in d
    for doc in d['documentos']:
        # o está disponible, o dice por qué no · nunca una fila muda
        assert doc['disponible'] or doc['motivo']


def test_el_consumo_no_cuenta_los_pedidos_cancelados(app, db_clean):
    _limpiar()
    _exec("INSERT INTO clientes (codigo, nombre, activo) VALUES ('ZPF1','Cliente Uno',1)")
    for estado, uds in (('despachado', 100), ('pendiente', 50), ('cancelado', 999)):
        _exec("INSERT INTO pedidos_b2b (cliente_id,cliente_nombre,producto_nombre,cantidad_uds,"
              "ml_unidad,estado,creado_at_utc,creado_por) "
              "VALUES ('ZPF1','Cliente Uno','ZZ PRODUCTO',?,30,?, '2026-08-01T10:00:00Z','portal')",
              (uds, estado))
    cli, _ = _cliente_portal(app, 'ZPF1', 'Cliente Uno')

    d = cli.get('/api/portal/consumo').get_json()
    assert d['hay_historia'] is True
    assert d['pedidos'] == 2, 'el cancelado no cuenta'
    assert d['unidades'] == 150
    assert d['productos'][0]['unidades'] == 150


def test_sin_historia_el_consumo_lo_dice(app, db_clean):
    _limpiar()
    cli, _ = _cliente_portal(app, 'ZPFNUEVO', 'Cliente Nuevo')
    d = cli.get('/api/portal/consumo').get_json()
    assert d['hay_historia'] is False, 'un cero sin historia se lee como "no compraste nada"'


# ══════════════════════════════════════════════════════════════════════
# Las pantallas existen (un endpoint sin pantalla no existe · M197)
# ══════════════════════════════════════════════════════════════════════

def test_las_pantallas_del_flujo_existen_y_traen_sus_botones(app, db_clean):
    _limpiar()
    adm = _login(app)
    pag = adm.get('/admin/portal-pagos')
    assert pag.status_code == 200
    html = pag.data.decode('utf-8')
    for pieza in ('conciliar', 'rechazar', 'enlazar', 'X-CSRF-Token'):
        assert pieza in html, 'la pantalla de pagos no trae %s' % pieza

    # y se llega a ella desde donde se gestionan los clientes (M121)
    b2b = adm.get('/admin/clientes-b2b').data.decode('utf-8')
    assert '/admin/portal-pagos' in b2b, 'nadie puede llegar a la pantalla de pagos'
    assert '/admin/portal-clientes' in b2b, 'nadie puede llegar a los accesos del portal'
    assert adm.get('/admin/portal-clientes').status_code == 200

    cli, _ = _cliente_portal(app, 'ZPF1', 'Cliente Uno')
    portal = cli.get('/portal').data.decode('utf-8')
    for pieza in ("irA('facturas')", "irA('pagos')", "irA('documentos')", "irA('consumo')",
                  'enviarPago', 'cargarFacturas'):
        assert pieza in portal, 'el portal no trae %s' % pieza


def test_ninguna_pantalla_del_portal_queda_tapada_por_otra_ruta(app, db_clean):
    """Dos rutas con la misma URL: gana la del blueprint que se registra primero.

    La segunda queda MUERTA sin un solo error, y desde el código se ve perfecta: fue
    exactamente lo que le pasó al panel de accesos del portal, que vivía en la misma
    URL que el dashboard de clientes y por eso no abría (M97).
    """
    from collections import Counter
    cuenta = Counter()
    for regla in app.url_map.iter_rules():
        if 'GET' in (regla.methods or set()):
            cuenta[str(regla.rule)] += 1
    repetidas = {u: n for u, n in cuenta.items() if n > 1
                 and ('portal' in u or 'clientes-b2b' in u)}
    assert not repetidas, 'URLs declaradas dos veces: %s' % repetidas
