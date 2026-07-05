"""Sebastián 4-jul · P2-A (doble-conteo borde 'hoy') + alerta higiene (probable_zombie)."""
import json
import os
import sqlite3


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login {user} fallo: {r.status_code}"
    return c


def test_pipeline_fijo_no_doble_cuenta_lote_de_hoy(app, db_clean):
    """P2-A · un lote Fijo con fecha == HOY (no ejecutado) lo cuenta pipeline_kg (ventana ≤hoy) · NO debe
    contarse TAMBIÉN en pipeline_fijo_kg (ventana >hoy) → sin esto stock_kg_total lo sumaba 2×."""
    PROD = "PROD-BORDE-HOY"
    SKU = "BORDEHOY30"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'BORDEHOY-%'")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 10, 1)", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (SKU, PROD))
    for i, delta in enumerate([10, 25, 40]):
        db.execute(
            """INSERT INTO animus_shopify_orders
               (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en)
               VALUES (?,?,?,?,?,?,?,?,date('now',?))""",
            (f"BORDEHOY-{i}", f"Cli {i}", 100000.0, "COP", "", "paid",
             json.dumps([{"sku": SKU, "qty": 50}]), 50, f"-{delta} days"))
    # lote Fijo con fecha == HOY, no ejecutado
    db.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes) "
               "VALUES (?, date('now','-5 hours'), 10, 'programado', 'eos_plan', 1)", (PROD,))
    db.commit()
    db.close()

    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    d = r.get_json()
    animus = next((x for x in d["clientes"] if x["cliente_id"] == "ANIMUS_DTC"), None)
    fila = next((p for p in animus["productos"] if p["producto_nombre"] == PROD), None)
    assert fila is not None, "producto no apareció"
    # el lote de hoy NO debe estar en pipeline_fijo (solo en pipeline_kg) → no doble-conteo
    assert fila["pipeline_fijo_kg"] < 0.5, ("lote de hoy NO debe contarse en pipeline_fijo", fila["pipeline_fijo_kg"])
    # stock_kg_total ≈ 10 (una vez), NO ~20 (doble)
    assert fila["stock_kg_total"] < 15, ("stock_kg_total no debe doble-contar el lote de hoy", fila["stock_kg_total"])


def test_sin_descontar_marca_probable_zombie(app, db_clean):
    """Higiene · la alerta marca probable_zombie los lotes pasados >45d (casi seguro nunca producidos)
    para cancelar, y NO marca los recientes (junio real ≤34d)."""
    PROD = "PROD-ZOMBIE-ALERTA"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    # zombie: 60 días atrás, pendiente, sin descuento
    db.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen) "
               "VALUES (?, date('now','-60 days','-5 hours'), 10, 'pendiente', 'eos_plan')", (PROD,))
    # reciente: 20 días atrás → NO zombie
    db.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen) "
               "VALUES (?, date('now','-20 days','-5 hours'), 10, 'pendiente', 'eos_plan')", (PROD,))
    db.commit()
    db.close()

    r = c.get("/api/plan/producciones-sin-descontar")
    assert r.status_code == 200, r.data
    d = r.get_json()
    mios = [p for p in d["producciones"] if p["producto"] == PROD]
    assert len(mios) == 2, mios
    viejo = next(p for p in mios if p["dias_atraso"] >= 55)
    reciente = next(p for p in mios if p["dias_atraso"] <= 25)
    assert viejo["probable_zombie"] is True, ("lote >45d debe marcarse zombie", viejo)
    assert reciente["probable_zombie"] is False, ("lote reciente NO debe marcarse zombie", reciente)
    assert d["zombie"] >= 1
