"""Tests CRUD /api/admin/sku-producto-map · Sebastián 8-may-2026."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _cleanup(skus):
    if not skus:
        return
    conn = sqlite3.connect(os.environ['DB_PATH'])
    ph = ','.join(['?'] * len(skus))
    conn.execute(f"DELETE FROM sku_producto_map WHERE UPPER(sku) IN ({ph})",
                 [s.upper() for s in skus])
    conn.commit(); conn.close()


def test_sku_map_post_get_basico(app, db_clean):
    cs = _login(app, 'sebastian')
    try:
        r = cs.post('/api/admin/sku-producto-map',
                    json={'sku': 'TEST_SKU_X', 'producto_nombre': 'TEST PROD X',
                          'activo': True},
                    headers=csrf_headers())
        assert r.status_code == 200, f'POST fallo: {r.data}'
        d = r.get_json()
        assert d['ok'] is True
        assert d['sku'] == 'TEST_SKU_X'
        # GET by sku
        r = cs.get('/api/admin/sku-producto-map?sku=TEST_SKU_X')
        d = r.get_json()
        assert d['mappings'][0]['sku'] == 'TEST_SKU_X'
        assert d['mappings'][0]['producto_nombre'] == 'TEST PROD X'
    finally:
        _cleanup(['TEST_SKU_X'])


def test_sku_map_upsert(app, db_clean):
    """POST con mismo SKU actualiza el producto."""
    cs = _login(app, 'sebastian')
    try:
        cs.post('/api/admin/sku-producto-map',
                json={'sku': 'TEST_UPS', 'producto_nombre': 'PROD V1'},
                headers=csrf_headers())
        cs.post('/api/admin/sku-producto-map',
                json={'sku': 'TEST_UPS', 'producto_nombre': 'PROD V2'},
                headers=csrf_headers())
        r = cs.get('/api/admin/sku-producto-map?sku=TEST_UPS')
        d = r.get_json()
        assert d['mappings'][0]['producto_nombre'] == 'PROD V2'
    finally:
        _cleanup(['TEST_UPS'])


def test_sku_map_delete_soft(app, db_clean):
    """_delete=true marca activo=0."""
    cs = _login(app, 'sebastian')
    try:
        cs.post('/api/admin/sku-producto-map',
                json={'sku': 'TEST_DEL', 'producto_nombre': 'X'},
                headers=csrf_headers())
        r = cs.post('/api/admin/sku-producto-map',
                    json={'sku': 'TEST_DEL', '_delete': True},
                    headers=csrf_headers())
        assert r.status_code == 200
        # Verificar activo=0
        r = cs.get('/api/admin/sku-producto-map?sku=TEST_DEL')
        d = r.get_json()
        if d['mappings']:
            assert d['mappings'][0]['activo'] is False
    finally:
        _cleanup(['TEST_DEL'])


def test_sku_map_warning_sin_formula(app, db_clean):
    """Si el producto no tiene fórmula, el response trae warning."""
    cs = _login(app, 'sebastian')
    try:
        r = cs.post('/api/admin/sku-producto-map',
                    json={'sku': 'TEST_NF',
                          'producto_nombre': 'PRODUCTO_QUE_NO_EXISTE_CON_FORMULA'},
                    headers=csrf_headers())
        d = r.get_json()
        assert d['warning'] is not None
        assert 'fórmula' in d['warning'] or 'formula' in d['warning']
    finally:
        _cleanup(['TEST_NF'])


def test_sku_map_validacion(app, db_clean):
    cs = _login(app, 'sebastian')
    # SKU vacío
    r = cs.post('/api/admin/sku-producto-map', json={'sku': ''},
                headers=csrf_headers())
    assert r.status_code == 400
    # Producto vacío
    r = cs.post('/api/admin/sku-producto-map',
                json={'sku': 'TEST_X', 'producto_nombre': ''},
                headers=csrf_headers())
    assert r.status_code == 400


def test_sku_map_sin_login_401(client):
    r = client.get('/api/admin/sku-producto-map')
    assert r.status_code == 401


def test_sku_map_no_admin_403(app, db_clean):
    cs = _login(app, 'catalina')
    r = cs.get('/api/admin/sku-producto-map')
    assert r.status_code == 403


def test_skus_pendientes_page_admin(app, db_clean):
    cs = _login(app, 'sebastian')
    r = cs.get('/admin/skus-pendientes')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'SKUs pendientes' in body
    assert '/api/admin/sku-producto-map' in body


def test_skus_pendientes_page_no_admin_403(app, db_clean):
    cs = _login(app, 'catalina')
    r = cs.get('/admin/skus-pendientes')
    assert r.status_code == 403
