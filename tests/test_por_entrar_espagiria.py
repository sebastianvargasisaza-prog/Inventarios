"""Sebastián 5-jul · Paso 2 · stock 'POR ENTRAR' de Espagiria (producido en el lab, no entregado a Ánimus).

Debe sumar a la PRÓXIMA (dias_con_pipeline), NO a la góndola (dias_gondola/urgencia). Así:
- no se sobre-produce lo que el lab ya hizo (concern #1),
- no se sobre-cuenta la góndola vendible (la urgencia sigue siendo lo físico en Ánimus),
- al trasladar a Ánimus, Shopify mueve las uds → cero doble-conteo.
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


def test_por_entrar_suma_a_proxima_no_a_gondola(app, db_clean):
    PROD = "PROD-PORENTRAR-T1"
    SKU = "PORENTRAR30"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM stock_pt WHERE sku=?", (SKU,))
    db.execute("DELETE FROM stock_por_entrar WHERE sku=?", (SKU,))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'PENT-%'")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, fecha_creacion) "
               "VALUES (?, 12, 1, '2025-01-01')", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (SKU, PROD))
    # góndola Ánimus: 100 uds
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,100,'Disponible','ANIMUS')", (SKU, PROD, "L-P"))
    # POR ENTRAR (Espagiria): 300 uds producidas, sin entregar
    db.execute("INSERT INTO stock_por_entrar (sku, uds, actualizado_at) VALUES (?,300,?)", (SKU, date.today().isoformat()))
    # venta ~10 uds/día
    today = date.today()
    for i in range(30):
        db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (f"PENT-{i}", "c", 1000.0, "COP", "", "paid", json.dumps([{"sku": SKU, "qty": 10}]), 10,
                    (today - timedelta(days=i + 1)).isoformat()))
    db.commit()
    db.close()

    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    d = r.get_json()
    animus = next((x for x in d["clientes"] if x["cliente_id"] == "ANIMUS_DTC"), None)
    fila = next((p for p in animus["productos"] if p["producto_nombre"] == PROD), None)
    assert fila is not None, "producto no apareció"
    # por_entrar reportado
    assert fila.get("por_entrar_uds") == 300, ("debe traer las 300 uds por entrar de Espagiria", fila.get("por_entrar_uds"))
    # la PRÓXIMA (dias_con_pipeline) SÍ cuenta el por-entrar → mucho mayor que la góndola sola
    assert fila["dias_con_pipeline"] is not None and fila["dias_gondola"] is not None
    assert fila["dias_con_pipeline"] >= fila["dias_gondola"] + 20, (
        "el por-entrar de Espagiria debe sumar a la próxima (dias_con_pipeline)",
        fila["dias_con_pipeline"], fila["dias_gondola"])
    # la GÓNDOLA (urgencia) NO cuenta el por-entrar → sigue siendo lo físico en Ánimus (~10 días)
    assert fila["dias_gondola"] < 20, (
        "la góndola/urgencia NO debe inflarse con el por-entrar de Espagiria", fila["dias_gondola"])
