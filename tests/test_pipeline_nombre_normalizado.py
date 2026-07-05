"""Sebastián 4-jul · P1-D (audit) · el pipeline reciente debe verse aunque el lote tenga nombre VARIANTE.

produccion_programada.producto puede diferir de la fórmula por acento/'+'/espacios (operario de Fabricación ·
TRIACTIVE 'NAD' vs 'NAD+'). Los 4 dicts del pipeline se keyean por nombre CRUDO; sin fallback normalizado
(M13), un lote reciente con nombre variante caía a pipeline_kg=0 en silencio → cobertura subcontada →
próxima adelantada → producir/comprar de más (y se perdía el anti-doble-conteo NOVA PHA).
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


def test_pipeline_matchea_nombre_variante(app, db_clean):
    PROD = "PROD PIPE NORM"          # nombre de la fórmula
    PROD_LOTE = "PROD-PIPE-NORM+"    # nombre VARIANTE del lote (normaliza igual)
    SKU = "PIPENORM30"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    for p in (PROD, PROD_LOTE):
        db.execute("DELETE FROM produccion_programada WHERE producto=?", (p,))
    db.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'PIPENORM-%'")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 10, 1)", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (SKU, PROD))
    today = date.today()
    for i, delta in enumerate([15, 30, 45]):
        db.execute(
            """INSERT INTO animus_shopify_orders
               (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (f"PIPENORM-{i}", f"Cli {i}", 100000.0, "COP", "", "paid",
             json.dumps([{"sku": SKU, "qty": 60}]), 60, (today - timedelta(days=delta)).isoformat()))
    # lote reciente (≤7d) bajo el nombre VARIANTE → debe verse como pipeline vía normalizado
    db.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes) "
               "VALUES (?, date('now','-2 days','-5 hours'), 10, 'programado', 'eos_plan', 1)", (PROD_LOTE,))
    db.commit()
    db.close()

    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    d = r.get_json()
    animus = next((x for x in d["clientes"] if x["cliente_id"] == "ANIMUS_DTC"), None)
    fila = next((p for p in animus["productos"] if p["producto_nombre"] == PROD), None)
    assert fila is not None, "producto no apareció en necesidades"
    # el lote variante (10kg) debe contarse como pipeline (match normalizado M13), NO 0
    assert fila["pipeline_kg"] >= 9.5, (
        "un lote reciente con nombre variante debe verse en el pipeline (fallback normalizado)", fila["pipeline_kg"])
