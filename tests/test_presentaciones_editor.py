"""Sebastián 2-jul · Editor de presentaciones (multi-envase) del producto desde el modal.
GET/POST /api/plan/producto/<prod>/presentaciones → upsert en producto_presentaciones
(cada presentación = frasco envase_codigo + volumen_ml + cantidad_fija_uds opcional).
Persiste para TODOS los lotes del producto.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _seed_prod(nombre='PROD PRES'):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("INSERT OR REPLACE INTO formula_headers (producto_nombre,lote_size_kg,activo) "
                     "VALUES (?,30,1)", (nombre,))
        conn.execute("DELETE FROM producto_presentaciones WHERE LOWER(TRIM(producto_nombre))=LOWER(TRIM(?))",
                     (nombre,))
        conn.commit()
    finally:
        conn.close()


def test_presentaciones_crear_listar_editar_quitar(app, db_clean):
    _seed_prod('PROD PRES')
    c = _login(app)
    # crear 2 presentaciones (150ml + 50ml con cantidad fija)
    r = c.post('/api/plan/producto/PROD%20PRES/presentaciones', json={'presentaciones': [
        {'volumen_ml': 150, 'envase_codigo': 'FR-150'},
        {'volumen_ml': 50, 'envase_codigo': 'FR-50', 'cantidad_fija_uds': 100},
    ]}, headers=csrf_headers())
    assert r.status_code == 200, f"{r.status_code} {r.data[:300]}"

    g = c.get('/api/plan/producto/PROD%20PRES/presentaciones').get_json()
    pres = g['presentaciones']
    assert len(pres) == 2, pres
    assert sorted(p['volumen_ml'] for p in pres) == [50, 150]
    p150 = [p for p in pres if p['volumen_ml'] == 150][0]
    p50 = [p for p in pres if p['volumen_ml'] == 50][0]
    assert p150['envase_codigo'] == 'FR-150'
    assert p50['cantidad_fija_uds'] == 100

    # editar el 150 (cambiar frasco) + quitar el 50
    r2 = c.post('/api/plan/producto/PROD%20PRES/presentaciones', json={'presentaciones': [
        {'id': p150['id'], 'volumen_ml': 150, 'envase_codigo': 'FR-OTRO'},
        {'id': p50['id'], 'remove': True},
    ]}, headers=csrf_headers())
    assert r2.status_code == 200, r2.data[:300]

    pres2 = c.get('/api/plan/producto/PROD%20PRES/presentaciones').get_json()['presentaciones']
    assert len(pres2) == 1, pres2
    assert pres2[0]['volumen_ml'] == 150 and pres2[0]['envase_codigo'] == 'FR-OTRO'


def test_presentaciones_no_duplica_identica(app, db_clean):
    _seed_prod('PROD DUP')
    c = _login(app)
    # dos filas IDÉNTICAS (mismo ml + mismo frasco) → debe quedar UNA sola
    r = c.post('/api/plan/producto/PROD%20DUP/presentaciones', json={'presentaciones': [
        {'volumen_ml': 150, 'envase_codigo': 'FR-150'},
        {'volumen_ml': 150, 'envase_codigo': 'FR-150'},
    ]}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    pres = c.get('/api/plan/producto/PROD%20DUP/presentaciones').get_json()['presentaciones']
    assert len(pres) == 1, f"idénticas deben colapsar a 1 · {pres}"


def test_presentaciones_get_devuelve_skus_del_producto(app, db_clean):
    _seed_prod('PROD SKU')
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("INSERT OR REPLACE INTO sku_producto_map (sku,producto_nombre,activo) VALUES ('SKU-30','PROD SKU',1)")
        conn.execute("INSERT OR REPLACE INTO sku_producto_map (sku,producto_nombre,activo) VALUES ('SKU-10','PROD SKU',1)")
        conn.commit()
    finally:
        conn.close()
    c = _login(app)
    d = c.get('/api/plan/producto/PROD%20SKU/presentaciones').get_json()
    skus = {s['sku'] for s in d.get('skus', [])}
    assert 'SKU-30' in skus and 'SKU-10' in skus, d.get('skus')


def test_presentaciones_skus_match_sin_acentos(app, db_clean):
    # formula con acento, SKU mapeado SIN acento → igual debe encontrarlo (M13)
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("INSERT OR REPLACE INTO formula_headers (producto_nombre,lote_size_kg,activo) "
                     "VALUES (?,30,1)", ('CRÉMA ÚREA',))
        conn.execute("INSERT OR REPLACE INTO sku_producto_map (sku,producto_nombre,activo) "
                     "VALUES ('SKU-UREA','CREMA UREA',1)")
        conn.commit()
    finally:
        conn.close()
    c = _login(app)
    d = c.get('/api/plan/producto/CR%C3%89MA%20%C3%9AREA/presentaciones').get_json()
    skus = {s['sku'] for s in d.get('skus', [])}
    assert 'SKU-UREA' in skus, f"debe matchear sin acentos · {d.get('skus')}"


def test_presentaciones_enlaza_sku_al_editar(app, db_clean):
    _seed_prod('PROD LINK')
    c = _login(app)
    # crear presentación sin SKU real
    c.post('/api/plan/producto/PROD%20LINK/presentaciones', json={'presentaciones': [
        {'volumen_ml': 30, 'envase_codigo': 'FR-30'}]}, headers=csrf_headers())
    pid = c.get('/api/plan/producto/PROD%20LINK/presentaciones').get_json()['presentaciones'][0]['id']
    # editar enlazando su SKU real
    r = c.post('/api/plan/producto/PROD%20LINK/presentaciones', json={'presentaciones': [
        {'id': pid, 'volumen_ml': 30, 'envase_codigo': 'FR-30', 'sku_shopify': 'SKU-REAL-30'}]},
        headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    pres = c.get('/api/plan/producto/PROD%20LINK/presentaciones').get_json()['presentaciones'][0]
    assert pres['sku_shopify'] == 'SKU-REAL-30', pres


def test_presentaciones_producto_inexistente_404(app, db_clean):
    c = _login(app)
    r = c.post('/api/plan/producto/NO%20EXISTE%20XYZ/presentaciones',
               json={'presentaciones': [{'volumen_ml': 30, 'envase_codigo': 'FR-30'}]},
               headers=csrf_headers())
    assert r.status_code == 404
