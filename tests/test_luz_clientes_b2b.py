"""Sebastián 2-jul: Luz (asistente Espagiria que maneja clientes) debe poder crear/gestionar
clientes B2B y sus pedidos (se cargan solos al plan). Antes los endpoints exigían admin/compras
(COMPRAS_ACCESS) y Luz quedaba con 403. Ahora _require_clientes_access permite CLIENTES_ACCESS.
"""
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def test_luz_lista_y_crea_clientes_b2b(app, db_clean):
    c = _login(app, 'luz')
    # listar clientes: ya no 403
    r = c.get('/api/clientes-b2b')
    assert r.status_code == 200, f"GET clientes · {r.status_code} {r.data[:200]}"
    # crear cliente: acceso concedido (no 403 · puede ser 200/201/400 por body)
    r2 = c.post('/api/clientes-b2b', json={'cliente_nombre': 'CLIENTE TEST LUZ', 'empresa': 'Espagiria'},
                headers=csrf_headers())
    assert r2.status_code != 403, f"crear cliente NO debe ser 403 · {r2.status_code} {r2.data[:300]}"
    # página de clientes: ya no 403
    r3 = c.get('/admin/clientes-b2b')
    assert r3.status_code == 200, f"página clientes · {r3.status_code}"


def test_luz_puede_crear_pedido_b2b(app, db_clean):
    c = _login(app, 'luz')
    r = c.post('/api/pedidos-b2b', json={'cliente_nombre': 'X', 'producto_nombre': 'Y', 'cantidad_uds': 10},
               headers=csrf_headers())
    assert r.status_code != 403, f"crear pedido NO debe ser 403 · {r.status_code} {r.data[:300]}"
