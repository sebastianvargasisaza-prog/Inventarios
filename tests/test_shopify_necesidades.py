"""Auditoría Shopify→Necesidades (27-jun) · el SKU se cruza case-insensitive entre el motor del calendario
(auto_plan) y los datos de Shopify (igual que Necesidades) · antes case-sensitive daba velocidad 0."""
import os
import json
import sqlite3


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def test_ventas_diarias_sku_case_insensitive(app, db_clean):
    # orden Shopify (no cancelada, pagada) con el SKU en MINÚSCULA
    _exec("INSERT INTO animus_shopify_orders (shopify_id, estado, estado_pago, sku_items, unidades_total, "
          "tags, customer_tags, creado_en) VALUES ('TCASE1','','paid',?,5,'','',datetime('now','-5 hours'))",
          (json.dumps([{'sku': 'abc-30', 'qty': 5}]),))
    with app.app_context():
        from database import get_db
        from blueprints.auto_plan import _ventas_diarias_por_sku
        c = get_db()
        # el motor del calendario busca el SKU en MAYÚSCULA → debe encontrar la venta (case-insensitive)
        ventas = _ventas_diarias_por_sku(c, 'ABC-30', dias=30)
    total = sum(q for _, q in ventas)
    assert total == 5, ('SKU case-insensitive falló · velocidad quedaría en 0', ventas)


def _login(app, user="sebastian"):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def test_diag_detecta_mapeo_zombi(app, db_clean):
    # SKU mapeado a un producto que NO existe en formula_headers (zombi) + una venta
    _exec("INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES ('ZOMBI-30','XX NO EXISTE EN FORMULAS XX',1)")
    _exec("INSERT INTO animus_shopify_orders (shopify_id, estado, estado_pago, sku_items, unidades_total, "
          "tags, customer_tags, creado_en) VALUES ('TZ1','','paid',?,3,'','',datetime('now','-5 hours'))",
          (json.dumps([{'sku': 'ZOMBI-30', 'qty': 3}]),))
    c = _login(app)
    r = c.get("/api/plan/diagnostico-shopify")
    assert r.status_code == 200, r.data
    d = r.get_json()
    zombi = [x for x in d['por_sku'] if x['sku'] == 'ZOMBI-30']
    assert zombi and zombi[0]['estado'] == 'MAPEADO_SIN_FORMULA', (zombi, d['reconciliacion'])
    assert d['reconciliacion']['n_skus_mapeo_zombi'] >= 1, d['reconciliacion']


def _q1(sql, params=()):
    import os as _o, sqlite3 as _s
    conn = _s.connect(_o.environ["DB_PATH"], timeout=10.0)
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def test_job_alerta_skus_sin_mapear(app, db_clean):
    # orden con un SKU NUEVO sin mapear (huérfano) que vende
    _exec("INSERT INTO animus_shopify_orders (shopify_id, estado, estado_pago, sku_items, unidades_total, "
          "tags, customer_tags, creado_en) VALUES ('TALERT1','','paid',?,7,'','',datetime('now','-5 hours'))",
          (json.dumps([{'sku': 'NUEVO-SIN-MAPEAR-99', 'qty': 7}]),))
    from blueprints.auto_plan_jobs import job_alerta_skus_sin_mapear
    job_alerta_skus_sin_mapear(app)
    n = _q1("SELECT COUNT(*) FROM notificaciones_app WHERE destinatario='sebastian' "
            "AND tipo='shopify_sku_sin_mapear'")[0]
    assert n >= 1, 'no se creó el aviso de SKU sin mapear'


def test_mig294_limpiador_iluminador_remapea(app, db_clean):
    # SKU mapeado al nombre VIEJO (kójico) + la fórmula con el nombre NUEVO (iluminador)
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('Limpiador Iluminador',1,1)")
    _exec("INSERT INTO sku_producto_map (sku, producto_nombre, activo) "
          "VALUES ('LIMPILU-30','Limpiador Ácido Kójico',1)")
    _upd = ("UPDATE sku_producto_map SET producto_nombre = ("
            " SELECT producto_nombre FROM formula_headers WHERE COALESCE(activo,1)=1"
            " AND LOWER(producto_nombre) LIKE '%iluminador%' AND LOWER(producto_nombre) LIKE '%limpiador%'"
            " ORDER BY id LIMIT 1)"
            " WHERE (LOWER(producto_nombre) LIKE '%kojico%' OR LOWER(producto_nombre) LIKE '%kójico%')"
            " AND EXISTS (SELECT 1 FROM formula_headers WHERE COALESCE(activo,1)=1"
            " AND LOWER(producto_nombre) LIKE '%iluminador%' AND LOWER(producto_nombre) LIKE '%limpiador%')")
    _exec(_upd)
    n = _q1("SELECT producto_nombre FROM sku_producto_map WHERE sku='LIMPILU-30'")[0]
    assert 'luminador' in (n or '').lower(), ('el SKU no se re-apuntó a Iluminador', n)
