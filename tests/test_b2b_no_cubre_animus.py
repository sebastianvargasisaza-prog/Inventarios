"""La porción B2B de un lote Fijo NO debe contar como cobertura de Animus.

Caso SUERO BHA (30-may-2026): lote 65kg con 4.5kg para Fernando Meza (B2B).
La cobertura/duración debe reflejar solo los 60.5kg que consume Animus.
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


def test_b2b_resta_del_pipeline_fijo(app, db_clean):
    PROD = "PROD-B2B-T1"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'B2BT-%'")
    db.execute(
        "INSERT INTO formula_headers (producto_nombre, codigo_pt, lote_size_kg, "
        "activo, fecha_creacion) VALUES (?,?,?,1,?)",
        (PROD, "PB2B", 65, "2025-01-01"),
    )
    db.execute(
        "INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES (?,?,1)",
        ("SKUB2B1", PROD),
    )
    for i, fecha in enumerate(["2026-05-15", "2026-05-01", "2026-04-20"]):
        db.execute(
            """INSERT INTO animus_shopify_orders
               (shopify_id, nombre, total, moneda, estado, estado_pago,
                sku_items, unidades_total, creado_en)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (f"B2BT-{i}", f"Cli {i}", 100000.0, "COP", "", "paid",
             json.dumps([{"sku": "SKUB2B1", "qty": 10}]), 10, fecha),
        )
    # Lote Fijo de 65kg dentro del horizonte (60d)
    cur = db.execute(
        """INSERT INTO produccion_programada
           (producto, fecha_programada, cantidad_kg, estado, origen, lotes)
           VALUES (?, date('now','+20 days'), 65, 'programado', 'eos_plan', 1)""",
        (PROD,),
    )
    lote_id = cur.lastrowid
    # Pedido B2B + aporte de 4.5kg vinculado a ese lote
    cur2 = db.execute(
        """INSERT INTO pedidos_b2b
           (cliente_id, cliente_nombre, producto_nombre, cantidad_uds,
            estado, creado_por)
           VALUES ('CLI-TEST', 'Fernando Meza', ?, 150, 'confirmado', 'sebastian')""",
        (PROD,),
    )
    pedido_id = cur2.lastrowid
    db.execute(
        """INSERT INTO pedidos_b2b_lote
           (pedido_b2b_id, lote_produccion_id, kg_aporte, unidades_aporte,
            ml_unidad, envase_codigo, modo, cliente_nombre)
           VALUES (?, ?, 4.5, 150, 30, '', 'sumado_a_lote_canonico', 'Fernando Meza')""",
        (pedido_id, lote_id),
    )
    db.commit()
    db.close()

    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    d = r.get_json()
    animus = next((x for x in d["clientes"] if x["cliente_id"] == "ANIMUS_DTC"), None)
    assert animus is not None
    fila = next((p for p in animus["productos"]
                 if p["producto_nombre"] == PROD), None)
    assert fila is not None, "producto no apareció en necesidades"

    # El B2B comprometido se reporta y se resta del pipeline Fijo
    assert abs(fila["b2b_comprometido_kg"] - 4.5) < 0.01, fila
    # pipeline Fijo efectivo para Animus = 65 - 4.5 = 60.5
    assert abs(fila["pipeline_fijo_kg"] - 60.5) < 0.01, fila
