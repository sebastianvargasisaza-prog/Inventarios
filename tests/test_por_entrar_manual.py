"""Sebastián 6-jul · carga MANUAL del "por entrar" (Espagiria) por NOMBRE de producto / código, no solo SKU.

Cuando Shopify no expone el inventario de Espagiria a la API, Sebastián carga a mano cuántas unidades hay.
La escribe pensando en el PRODUCTO (ej. 'ANIMUSLASH'), pero el SKU Shopify real puede ser otra cadena → el
lookup por SKU daba 0 y el producto NO salía de rojo. El fallback debe resolver por nombre/código normalizado.
"""
import json
import os
import sqlite3
from datetime import date, timedelta


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login {user} fallo: {r.status_code}"
    return c


def test_por_entrar_manual_por_nombre_producto_saca_de_rojo(app, db_clean):
    """El manual keyed por NOMBRE de producto (no por el SKU exacto) igual saca el producto de crítico a POR_ENTRAR."""
    PROD = "TESTLASH"
    SKU = "TL-VARIANTE-9"      # el SKU real ≠ el nombre del producto (a propósito)
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    for t in ("formula_headers", "sku_producto_map"):
        db.execute(f"DELETE FROM {t} WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM stock_pt WHERE sku=?", (SKU,))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'TLASH-%'")
    db.execute("DELETE FROM app_settings WHERE clave='por_entrar_manual'")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, fecha_creacion) "
               "VALUES (?, 20, 1, '2025-01-01')", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES (?,?,1)", (SKU, PROD))
    # stock 0 en góndola → sin el "por entrar" es CRÍTICO
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,0,'Disponible','ANIMUS')", (SKU, PROD, "L-0"))
    today = date.today()
    for i in range(30):
        f = (today - timedelta(days=i + 1)).isoformat()
        db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (f"TLASH-{i}", "c", 100.0, "COP", "", "paid", json.dumps([{"sku": SKU, "qty": 1}]), 1, f))
    db.commit(); db.close()

    # 1) sin "por entrar" → CRÍTICO (vende ~1/día, stock 0)
    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    animus = next(x for x in r.get_json()["clientes"] if x["cliente_id"] == "ANIMUS_DTC")
    fila = next(p for p in animus["productos"] if p["producto_nombre"] == PROD)
    assert fila["urgencia"] == "CRITICO", ("debería arrancar crítico", fila.get("urgencia"))

    # 2) cargar el "por entrar" MANUAL por NOMBRE del producto (no por el SKU) → POR_ENTRAR
    r = c.post(f"/api/programacion/por-entrar-manual?sku={PROD}&uds=500",
               headers=__import__("tests.conftest", fromlist=["csrf_headers"]).csrf_headers())
    assert r.status_code == 200, r.data
    r = c.get("/api/plan/necesidades")
    animus = next(x for x in r.get_json()["clientes"] if x["cliente_id"] == "ANIMUS_DTC")
    fila = next(p for p in animus["productos"] if p["producto_nombre"] == PROD)
    assert fila["urgencia"] == "POR_ENTRAR", (
        "el manual por nombre de producto debe sacarlo de rojo a POR_ENTRAR", fila.get("urgencia"),
        fila.get("por_entrar_uds"))
