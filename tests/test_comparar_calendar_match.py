"""Verifica el fix del cruce necesidades↔calendario (plan.py).

Antes contaba solo origen IN ('calendar','manual') → una producción Fijo
(origen='eos_plan') quedaba invisible y el cruce la marcaba 'URGENTE_SIN_AGENDAR'
(falso). Ahora cuenta los orígenes nativos EOS, así que la VE.
"""
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


def test_cruce_ve_produccion_fijo_eos_plan(app, db_clean):
    PROD = "PROD-MATCH-T1"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    db.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'MATCH-%'")
    db.execute(
        "INSERT INTO formula_headers (producto_nombre, codigo_pt, lote_size_kg, "
        "activo, fecha_creacion) VALUES (?,?,?,1,?)",
        (PROD, "PMT1", 10, "2025-01-01"),
    )
    db.execute(
        "INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES (?,?,1)",
        ("SKUMATCH1", PROD),
    )
    # Ventas recientes → velocidad > 0 (si no, urgencia=SIN_VENTAS)
    for i, fecha in enumerate(["2026-05-15", "2026-05-01", "2026-04-20", "2026-04-05"]):
        db.execute(
            """INSERT INTO animus_shopify_orders
               (shopify_id, nombre, total, moneda, estado, estado_pago,
                sku_items, unidades_total, creado_en)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (f"MATCH-{i}", f"Cli {i}", 100000.0, "COP", "", "paid",
             json.dumps([{"sku": "SKUMATCH1", "qty": 15}]), 15, fecha),
        )
    # Producción FIJA (origen='eos_plan') en el horizonte → el cruce DEBE verla
    db.execute(
        """INSERT INTO produccion_programada
           (producto, fecha_programada, cantidad_kg, estado, origen, lotes)
           VALUES (?, date('now','+15 days'), 10, 'programado', 'eos_plan', 1)""",
        (PROD,),
    )
    db.commit()
    db.close()

    r = c.get("/api/plan/comparar-calendar-necesidades?horizonte_dias=90")
    assert r.status_code == 200, r.data
    d = r.get_json()
    fila = next((x for x in d["productos"] if x["producto_nombre"] == PROD), None)
    assert fila is not None, "producto no apareció en el cruce"

    # El núcleo del fix: VE la producción Fijo eos_plan
    assert fila["n_lotes_calendar"] == 1, fila
    assert fila["kg_calendar_horizonte"] > 0, fila
    # Y por lo tanto NO la marca como falsa "sin agendar"
    assert fila["categoria"] != "URGENTE_SIN_AGENDAR", fila
