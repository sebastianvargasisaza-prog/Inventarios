"""Vista por TONO de Blush Balm (Sebastián 12-jun · paso A).
/api/planta/blush-tonos desglosa venta + stock + unidades sugeridas por tono.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def test_blush_tonos_desglosa_venta_y_sugerencia(app, db_clean):
    # Venta reciente de Hot Pink (BB101): 180 uds en 180d -> vdia=1
    _exec("INSERT INTO animus_shopify_orders (shopify_id, creado_en, sku_items, unidades_total) "
          "VALUES ('ORD-BB-1', date('now','-5 hours'), ?, 180)",
          ('[{"sku":"BB101","qty":180}]',))

    c = _login(app)
    r = c.get('/api/planta/blush-tonos?dias=60')
    assert r.status_code == 200, r.data
    data = r.get_json()
    assert len(data['tonos']) == 8, "deben salir los 8 tonos"

    hp = next(t for t in data['tonos'] if t['sku'] == 'BB101')
    assert hp['tono'] == 'Hot Pink'
    assert hp['ventas_180d'] >= 180
    # sugerencia = max(0, round(vdia*60) - stock) · vdia=1 (180/180) -> ~60 a cubrir
    assert isinstance(hp['sugerencia_uds'], int) and hp['sugerencia_uds'] >= 55
    # el total del bulk = suma de sugerencias por tono
    assert data['total_bulk_sugerido_uds'] == sum(t['sugerencia_uds'] for t in data['tonos'])


def test_blush_tonos_pagina_renderiza(app, db_clean):
    c = _login(app)
    r = c.get('/planta/blush-tonos')
    assert r.status_code == 200
    body = r.data.decode('utf-8', 'replace')
    assert 'Blush Balm' in body
    for tono in ('Hot Pink', 'Malva', 'Borgoña', 'Moca'):
        assert tono in body, f"falta el tono {tono} en la página"
    assert 'bulk a fabricar' in body
