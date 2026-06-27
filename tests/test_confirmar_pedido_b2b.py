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
