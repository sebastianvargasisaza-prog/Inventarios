"""Alejandro 5-jul · MULTI-TONO · la cobertura la manda el tono que se AGOTA PRIMERO, no el promedio.

Un producto multi-tono (LIP SERUM · 6 tonos) donde un tono está casi vacío pero otro tiene mucho stock:
el AGREGADO (Σstock / Σvelocidad) da cobertura alta → el sistema decía "OK, próxima en agosto", pero el
tono bajo se agotaba antes → llegaban SIN ese tono. La cobertura/urgencia debe reflejar el cuello de botella.
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


def test_multitono_cobertura_por_cuello_de_botella(app, db_clean):
    PROD = "PROD-MULTITONO-T1"
    SKU_A = "TONOALTOA30"   # vende mucho, stock CASI VACÍO → cuello de botella
    SKU_B = "TONOBAJOB30"   # vende poco, MUCHO stock → infla el agregado
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM stock_pt WHERE sku IN (?,?)", (SKU_A, SKU_B))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'MTONO-%'")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, fecha_creacion) "
               "VALUES (?, 12, 1, '2025-01-01')", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (SKU_A, PROD))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (SKU_B, PROD))
    # góndola: SKU_A casi vacío (5 uds), SKU_B lleno (2000 uds) → agregado 2005 uds parece muchísimo
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,5,'Disponible','ANIMUS')", (SKU_A, PROD, "L-A"))
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,2000,'Disponible','ANIMUS')", (SKU_B, PROD, "L-B"))
    # ventas: SKU_A vende MUCHO (600 en la ventana), SKU_B poco (60) → SKU_A se agota en ~1 día
    today = date.today()
    for i in range(30):
        f = (today - timedelta(days=i + 1)).isoformat()
        db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (f"MTONO-A{i}", "c", 1000.0, "COP", "", "paid", json.dumps([{"sku": SKU_A, "qty": 20}]), 20, f))
        if i % 5 == 0:
            db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                       "VALUES (?,?,?,?,?,?,?,?,?)",
                       (f"MTONO-B{i}", "c", 1000.0, "COP", "", "paid", json.dumps([{"sku": SKU_B, "qty": 10}]), 10, f))
    db.commit()
    db.close()

    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    d = r.get_json()
    animus = next((x for x in d["clientes"] if x["cliente_id"] == "ANIMUS_DTC"), None)
    fila = next((p for p in animus["productos"] if p["producto_nombre"] == PROD), None)
    assert fila is not None, "producto no apareció"
    # Con el fix: la cobertura la manda el tono casi vacío → días bajos + urgencia CRÍTICA.
    # Sin el fix: el agregado (2005 uds) daría ~180 días → OK (test falla).
    assert fila["dias_gondola"] is not None and fila["dias_gondola"] < 15, (
        "la cobertura debe reflejar el tono que se agota primero, no el promedio", fila["dias_gondola"])
    assert fila["urgencia"] in ("CRITICO", "URGENTE"), (
        "un multi-tono con un tono casi vacío debe salir urgente, no OK", fila["urgencia"])


def test_tono_marginal_bajo_umbral_no_hace_critico(app, db_clean):
    """Umbral 5% (Sebastián 5-jul): un tono que vende <5% del mix y está en 0 NO debe pintar de rojo un
    producto que por lo demás está bien cubierto (evita inflar los críticos con tonos marginales)."""
    PROD = "PROD-MARGINAL-T1"
    SKU_MAIN = "TONOMAIN30"      # 96% del mix, buen stock → cubierto
    SKU_MARG = "TONOMARG30"      # ~4% del mix, stock 0 → marginal, NO debe mandar la alarma
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    for t in ("formula_headers", "sku_producto_map"):
        db.execute(f"DELETE FROM {t} WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM stock_pt WHERE sku IN (?,?)", (SKU_MAIN, SKU_MARG))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'MARG-%'")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, fecha_creacion) "
               "VALUES (?, 12, 1, '2025-01-01')", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (SKU_MAIN, PROD))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (SKU_MARG, PROD))
    # main: buen stock (500 uds) · marginal: 0
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,500,'Disponible','ANIMUS')", (SKU_MAIN, PROD, "L-M"))
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,0,'Disponible','ANIMUS')", (SKU_MARG, PROD, "L-G"))
    # ventas: main 500/ventana (~96%), marginal 20/ventana (~4% · bajo el umbral)
    today = date.today()
    for i in range(30):
        f = (today - timedelta(days=i + 1)).isoformat()
        db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (f"MARG-M{i}", "c", 1000.0, "COP", "", "paid", json.dumps([{"sku": SKU_MAIN, "qty": 17}]), 17, f))
        if i % 6 == 0:
            db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                       "VALUES (?,?,?,?,?,?,?,?,?)",
                       (f"MARG-G{i}", "c", 1000.0, "COP", "", "paid", json.dumps([{"sku": SKU_MARG, "qty": 4}]), 4, f))
    db.commit()
    db.close()

    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    d = r.get_json()
    animus = next((x for x in d["clientes"] if x["cliente_id"] == "ANIMUS_DTC"), None)
    fila = next((p for p in animus["productos"] if p["producto_nombre"] == PROD), None)
    assert fila is not None, "producto no apareció"
    # el tono marginal (0 stock, <5% mix) NO debe hacer crítico al producto (main lo cubre bien)
    assert fila["urgencia"] not in ("CRITICO", "URGENTE"), (
        "un tono marginal (<5% mix) en 0 NO debe disparar la alarma del producto", fila["urgencia"], fila["dias_gondola"])
    # el marginal se sigue viendo en el desglose, marcado mix_bajo
    marg = next((t for t in fila.get("tonos", []) if t["sku"] == SKU_MARG), None)
    assert marg is not None and marg.get("mix_bajo") is True, ("el tono marginal se muestra pero marcado mix_bajo", marg)
