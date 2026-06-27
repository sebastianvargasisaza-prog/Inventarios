"""Confirmación de pedido B2B (Sebastián 26-jun) · el pedido del portal queda 'pendiente' (NO entra solo al
plan); el equipo lo CONFIRMA en el backoffice → recién ahí se integra al plan + queda 'confirmado'.
Idempotente: confirmar 2× = 409."""
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
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def _q(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def test_confirmar_pedido_b2b(app, db_clean):
    prod = 'ZZ B2B PROD'
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,10,1)", (prod,))
    # pedido 'pendiente' (como lo deja el portal · NO integrado)
    pid = _exec("INSERT INTO pedidos_b2b (cliente_id,cliente_nombre,producto_nombre,cantidad_uds,"
                "ml_unidad,fecha_estimada,estado,creado_por) VALUES ('C1','Cliente Uno',?,100,30,?,'pendiente','portal:c1@x.com')",
                (prod, '2026-08-01'))
    # antes de confirmar: NO está en el plan
    assert not _q("SELECT id FROM pedidos_b2b_lote WHERE pedido_b2b_id=?", (pid,)), 'no debe integrarse aún'

    c = _login(app)
    r = c.post(f'/api/pedidos-b2b/{pid}/confirmar', json={}, headers=_h())
    assert r.status_code == 200, r.data
    # ahora SÍ: confirmado + integrado al plan (trazado en pedidos_b2b_lote)
    assert _q("SELECT estado FROM pedidos_b2b WHERE id=?", (pid,))[0][0] == 'confirmado'
    assert _q("SELECT id FROM pedidos_b2b_lote WHERE pedido_b2b_id=?", (pid,)), 'debe trazar el lote del plan'

    # idempotente: confirmar de nuevo → 409 (ya no está pendiente)
    r2 = c.post(f'/api/pedidos-b2b/{pid}/confirmar', json={}, headers=_h())
    assert r2.status_code == 409, r2.data


def test_confirmar_con_ajuste_cantidad(app, db_clean):
    prod = 'ZZ B2B AJ'
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,10,1)", (prod,))
    pid = _exec("INSERT INTO pedidos_b2b (cliente_id,cliente_nombre,producto_nombre,cantidad_uds,"
                "ml_unidad,estado,creado_por) VALUES ('C2','Dos',?,50,30,'pendiente','portal:c2@x.com')", (prod,))
    c = _login(app)
    # Catalina ajusta la cantidad al confirmar
    r = c.post(f'/api/pedidos-b2b/{pid}/confirmar', json={'cantidad_uds': 200}, headers=_h())
    assert r.status_code == 200, r.data
    assert _q("SELECT cantidad_uds FROM pedidos_b2b WHERE id=?", (pid,))[0][0] == 200


def test_despachar_pedido_b2b(app, db_clean):
    prod = 'ZZ B2B DESP'
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,10,1)", (prod,))
    pid = _exec("INSERT INTO pedidos_b2b (cliente_id,cliente_nombre,producto_nombre,cantidad_uds,"
                "ml_unidad,estado,creado_por) VALUES ('C3','Tres',?,50,30,'confirmado','portal:c3@x.com')", (prod,))
    c = _login(app)
    r = c.post(f'/api/pedidos-b2b/{pid}/despachar',
               json={'transportadora': 'Servientrega', 'guia': 'ABC123'}, headers=_h())
    assert r.status_code == 200, r.data
    row = _q("SELECT estado, despachado_at, despacho_guia, despacho_transportadora FROM pedidos_b2b WHERE id=?", (pid,))[0]
    assert row[0] == 'despachado' and row[1] and row[2] == 'ABC123' and row[3] == 'Servientrega'
    # re-despachar → 409 (ya no está confirmado/en_produccion)
    r2 = c.post(f'/api/pedidos-b2b/{pid}/despachar', json={}, headers=_h())
    assert r2.status_code == 409, r2.data


def test_job_b2b_recurrentes(app, db_clean):
    import datetime
    rid = _exec("INSERT INTO pedidos_b2b_recurrentes (cliente_id,cliente_nombre,producto_nombre,"
                "cantidad_uds,ml_unidad,frecuencia_dias,proximo_at,activo,creado_por) "
                "VALUES ('CR1','Recur Uno','ZZ RECUR PROD',100,30,30,'2026-01-01',1,'portal:cr1@x.com')")
    from blueprints.auto_plan_jobs import job_b2b_recurrentes
    job_b2b_recurrentes(app)
    peds = _q("SELECT estado, producto_nombre, cantidad_uds FROM pedidos_b2b WHERE cliente_id='CR1'")
    assert peds and peds[0][0] == 'pendiente' and peds[0][1] == 'ZZ RECUR PROD' and peds[0][2] == 100, peds
    prox = _q("SELECT proximo_at FROM pedidos_b2b_recurrentes WHERE id=?", (rid,))[0][0]
    hoy = (datetime.datetime.utcnow() - datetime.timedelta(hours=5)).strftime('%Y-%m-%d')
    assert prox > hoy, ('proximo no avanzó al futuro', prox, hoy)


def test_portal_editar_pedido_pendiente(app, db_clean):
    pid = _exec("INSERT INTO pedidos_b2b (cliente_id,cliente_nombre,producto_nombre,cantidad_uds,"
                "ml_unidad,estado,creado_por) VALUES ('PC1','Portal Cli','ZZ PROD',50,30,'pendiente','portal:pc1@x.com')")
    c = app.test_client()
    with c.session_transaction() as sess:
        sess['portal_cliente_id'] = 'PC1'
        sess['portal_cliente_nombre'] = 'Portal Cli'
        sess['portal_email'] = 'pc1@x.com'
        sess['portal_activo_check_ts'] = 9999999999
    r = c.patch('/api/portal/pedidos/' + str(pid), json={'cantidad_uds': 80}, headers=csrf_headers())
    assert r.status_code == 200, r.data
    assert _q("SELECT cantidad_uds FROM pedidos_b2b WHERE id=?", (pid,))[0][0] == 80
    # confirmado → ya no editable por el cliente
    _exec("UPDATE pedidos_b2b SET estado='confirmado' WHERE id=?", (pid,))
    r2 = c.patch('/api/portal/pedidos/' + str(pid), json={'cantidad_uds': 99}, headers=csrf_headers())
    assert r2.status_code == 409, r2.data


def test_catalogo_nombre_generico(app, db_clean):
    prod = 'ZZ COMERCIAL ANIMUS'
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,10,1)", (prod,))
    c = _login(app)  # admin
    r = c.post('/api/admin/portal/catalogo', json={'producto': prod, 'nombre_generico': 'Niacinamida'}, headers=_h())
    assert r.status_code == 200, r.data
    pc = app.test_client()
    with pc.session_transaction() as sess:
        sess['portal_cliente_id'] = 'PC9'
        sess['portal_cliente_nombre'] = 'X'
        sess['portal_email'] = 'x@x.com'
        sess['portal_activo_check_ts'] = 9999999999
    d = pc.get('/api/portal/productos').get_json()
    item = next((p for p in d['productos'] if p['nombre'] == prod), None)
    assert item and item['mostrar'] == 'Niacinamida', item


def test_portal_pedido_sin_ml_deriva(app, db_clean):
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('ZZ SIN ML',10,1)")
    c = app.test_client()
    with c.session_transaction() as sess:
        sess['portal_cliente_id'] = 'PM1'
        sess['portal_cliente_nombre'] = 'X'
        sess['portal_email'] = 'pm1@x.com'
        sess['portal_activo_check_ts'] = 9999999999
    # el cliente NO manda ml (ahora oculto · pide 500 frascos y ya)
    r = c.post('/api/portal/pedidos', json={'producto_nombre': 'ZZ SIN ML', 'cantidad_uds': 500, 'ml_unidad': 0}, headers=csrf_headers())
    assert r.status_code == 201, r.data
    ml = _q("SELECT ml_unidad FROM pedidos_b2b WHERE cliente_id='PM1'")[0][0]
    assert ml == 30, ('sin presentación → fallback 30', ml)  # con producto_presentaciones derivaría el volumen real


def test_comunicacion_nuevo_producto_y_reunion(app, db_clean):
    c = app.test_client()
    with c.session_transaction() as sess:
        sess['portal_cliente_id'] = 'CC1'
        sess['portal_cliente_nombre'] = 'Comm Cli'
        sess['portal_email'] = 'cc1@x.com'
        sess['portal_activo_check_ts'] = 9999999999
    # nuevo producto (requiere producto)
    r = c.post('/api/portal/solicitudes', json={'tipo': 'nuevo_producto', 'producto_nombre': 'Serum X',
               'mensaje': 'quiero que lo desarrollen'}, headers=csrf_headers())
    assert r.status_code == 201, r.data
    # reunión SIN producto (debe pasar · producto opcional)
    r2 = c.post('/api/portal/solicitudes', json={'tipo': 'reunion',
                'mensaje': 'reunirnos por volúmenes', 'fecha_requerida': '2026-08-01'}, headers=csrf_headers())
    assert r2.status_code == 201, r2.data
    rows = _q("SELECT tipo, producto_nombre FROM portal_solicitudes WHERE cliente_id='CC1' ORDER BY id")
    pares = [(x[0], x[1]) for x in rows]
    assert ('nuevo_producto', 'Serum X') in pares, pares
    assert any(x[0] == 'reunion' for x in rows), pares


def test_cliente_id_unico(app, db_clean):
    c = _login(app)  # admin
    r1 = c.post('/api/admin/portal/credenciales', json={'cliente_id': 'dup-x', 'cliente_nombre': 'A',
                'email': 'a@x.com', 'password': '12345678'}, headers=_h())
    assert r1.status_code == 201, r1.data
    # mismo cliente_id, otro email → 409 (aislamiento multi-cliente)
    r2 = c.post('/api/admin/portal/credenciales', json={'cliente_id': 'dup-x', 'cliente_nombre': 'B',
                'email': 'b@x.com', 'password': '12345678'}, headers=_h())
    assert r2.status_code == 409, r2.data
