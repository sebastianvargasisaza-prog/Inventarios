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


def test_presentaciones_producto_inexistente_404(app, db_clean):
    c = _login(app)
    r = c.post('/api/plan/producto/NO%20EXISTE%20XYZ/presentaciones',
               json={'presentaciones': [{'volumen_ml': 30, 'envase_codigo': 'FR-30'}]},
               headers=csrf_headers())
    assert r.status_code == 404
