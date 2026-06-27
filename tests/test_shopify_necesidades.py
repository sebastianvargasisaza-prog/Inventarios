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
