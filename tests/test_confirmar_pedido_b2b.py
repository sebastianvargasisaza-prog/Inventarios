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
