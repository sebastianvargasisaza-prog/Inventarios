"""Catalina acepta el pedido del cliente y le asigna los materiales.

Sebastián 14-ago-2026, señalando Compras › Envases a marcar: "aquí viven los envases
que ella envía a serigrafía · que le aparezca: el cliente tal pidió tantas unidades ·
le sale aceptar · y escoge envase, si lleva serigrafía, si lleva etiqueta, si lleva
caja · y de una vez el cliente pidió 700 unidades, automáticamente sube la cantidad
de kilos".

Lo que fijan estos tests es lo que puede salir caro: que el frasco que ella elige
llegue al LOTE (si no, la compra pide el genérico y el piso recibe otro), y que
cuando el pedido se suma a un lote compartido el sistema lo DIGA en vez de aceptar
la elección y no aplicarla.
"""
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
    for sql in ("DELETE FROM pedidos_b2b WHERE cliente_id LIKE 'ZCAT%'",
                "DELETE FROM produccion_programada WHERE producto LIKE 'ZCAT %'",
                "DELETE FROM formula_headers WHERE producto_nombre LIKE 'ZCAT %'",
                "DELETE FROM maestro_mee WHERE codigo LIKE 'ZCAT-%'"):
        try:
            _exec(sql)
        except Exception:
            pass


def _sembrar(uds=700, ml=30, producto='ZCAT PRODUCTO'):
    _limpiar()
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,50,1)",
          (producto,))
    for cod, desc in (('ZCAT-ENV-A', 'Frasco de siempre'), ('ZCAT-ENV-B', 'Frasco del cliente')):
        _exec("INSERT INTO maestro_mee (codigo, descripcion, stock_actual, estado) "
              "VALUES (?,?,0,'Activo')", (cod, desc))
    pid = _exec(
        "INSERT INTO pedidos_b2b (cliente_id, cliente_nombre, producto_nombre, cantidad_uds, "
        "ml_unidad, fecha_estimada, estado, urgencia, envase_codigo, creado_at_utc, creado_por) "
        "VALUES ('ZCAT1','Cliente De Catalina',?,?,?,'2026-12-01','pendiente','media','', "
        "'2026-08-12T09:00:00Z','portal:cliente@zcat.test')", (producto, uds, ml))
    return pid, producto


def test_la_cola_le_muestra_quien_pidio_y_cuantos_kilos(app, db_clean):
    pid, _ = _sembrar(uds=700, ml=30)
    d = _login(app).get('/api/pedidos-b2b/por-asignar').get_json()
    mio = [x for x in d['items'] if x['id'] == pid]
    assert mio, 'el pedido no aparece en la cola de Catalina'
    it = mio[0]
    assert it['cliente_nombre'] == 'Cliente De Catalina'
    assert it['unidades'] == 700
    # 700 uds x 30 ml = 21 kg · los kilos NO se teclean
    assert it['kg'] == 21.0, it['kg']
    assert d['envases'], 'no hay envases para elegir'


def test_el_frasco_que_elige_llega_al_lote(app, db_clean):
    """Si no llega, la compra pide el genérico y el piso recibe otro frasco."""
    pid, producto = _sembrar()
    adm = _login(app)
    r = adm.post(f'/api/pedidos-b2b/{pid}/confirmar',
                 json={'envase_codigo': 'ZCAT-ENV-B', 'lleva_etiqueta': True,
                       'lleva_caja': False}, headers=_h())
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d['kg_b2b'] == 21.0
    assert d['envase'] == 'ZCAT-ENV-B'
    lote = (d.get('integracion_plan') or {}).get('lote_id')
    assert lote, 'no quedó lote'
    if (d.get('integracion_plan') or {}).get('modo') == 'lote_dedicado':
        ov = _q("SELECT COALESCE(envase_codigo_override,'') FROM produccion_programada WHERE id=?",
                (lote,))[0][0]
        assert ov == 'ZCAT-ENV-B', 'el frasco elegido no llegó al lote (la compra pediría otro)'
    else:
        assert d['requiere_reparto'] is True, (
            'se sumó a un lote compartido y no avisó que hay que repartir')
    # y lo que ella definió queda guardado
    assert _q("SELECT lleva_etiqueta, lleva_caja FROM pedidos_b2b WHERE id=?", (pid,))[0] == (1, 0)


def test_un_envase_que_no_existe_se_rechaza(app, db_clean):
    """Un código inventado apunta al vacío y nadie lo ve hasta que falta el frasco."""
    pid, _ = _sembrar()
    r = _login(app).post(f'/api/pedidos-b2b/{pid}/confirmar',
                         json={'envase_codigo': 'NO-EXISTE-999'}, headers=_h())
    assert r.status_code == 400, r.data
    assert r.get_json().get('codigo') == 'ENVASE_DESCONOCIDO'
    assert _q("SELECT estado FROM pedidos_b2b WHERE id=?", (pid,))[0][0] == 'pendiente', \
        'lo rechazó pero igual movió el pedido'


def test_sumarse_a_un_lote_compartido_con_otro_frasco_se_declara(app, db_clean):
    """No se le puede cambiar el frasco a todo el lote: también es de ÁNIMUS."""
    pid, producto = _sembrar()
    # un lote del mismo producto, cercano a la fecha pedida, para que se sume
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, "
          "estado, origen) VALUES (?, '2026-11-25', 50, 1, 'pendiente', 'eos_plan')", (producto,))
    r = _login(app).post(f'/api/pedidos-b2b/{pid}/confirmar',
                         json={'envase_codigo': 'ZCAT-ENV-B'}, headers=_h())
    assert r.status_code == 200, r.data
    d = r.get_json()
    if (d.get('integracion_plan') or {}).get('modo') == 'sumado_a_lote_canonico':
        assert d['requiere_reparto'] is True
        assert (d['integracion_plan'].get('aviso') or ''), 'no explica qué hacer'


def test_la_pantalla_de_catalina_trae_la_cola_y_el_boton(app, db_clean):
    """Un endpoint sin pantalla no existe para nadie (M197)."""
    html = _login(app).get('/admin/marcacion-envases').data.decode('utf-8')
    for pieza in ('smt-pedidos', 'id="sub-pedidos"', 'cargarPedidosClientes',
                  'aceptarPedidoCliente', '/api/pedidos-b2b/por-asignar'):
        assert pieza in html, 'la pantalla de Catalina no trae %s' % pieza
