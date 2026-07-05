"""Sebastián 4-jul · BUG doble-conteo NOVA PHA.

Una producción FÍSICA de hace >7 días (que ya está en góndola, contada en el stock) pero
DESCONTADA/registrada hace poco (el jefe normaliza junio esta semana) NO debe volver a contarse como
"pipeline" (lo producido ≤7d aún en camino). Si se cuenta, la cobertura y la próxima se inflan
(NOVA PHA: 207 días → próxima enero, cuando lo real era ~86d → septiembre).

El pipeline debe usar la fecha FÍSICA (fin_real_at real, o fecha_programada), NO inventario_descontado_at.
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


def test_pipeline_usa_fecha_fisica_no_descuento(app, db_clean):
    PROD = "PROD-PIPE-T1"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'PIPET-%'")
    db.execute(
        "INSERT INTO formula_headers (producto_nombre, codigo_pt, lote_size_kg, activo, fecha_creacion) "
        "VALUES (?,?,?,1,?)", (PROD, "PPIP", 12, "2025-01-01"))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES (?,?,1)", ("SKUPIP1", PROD))
    # ventas para que tenga velocidad y aparezca en Necesidades
    today = date.today()
    for i, delta in enumerate([20, 35, 50]):
        fecha = (today - timedelta(days=delta)).isoformat()
        db.execute(
            """INSERT INTO animus_shopify_orders
               (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (f"PIPET-{i}", f"Cli {i}", 100000.0, "COP", "", "paid",
             json.dumps([{"sku": "SKUPIP1", "qty": 10}]), 10, fecha))
    # Producción A: física hace 12 días (>7 → ya en góndola) pero REGISTRADA hace poco → tanto
    # inventario_descontado_at COMO fin_real_at quedan recientes (fecha de registro, no física). Con el bug
    # (cualquiera de esos dos) se contaría de nuevo como pipeline; con el fix (fecha_programada) NO.
    db.execute(
        """INSERT INTO produccion_programada
           (producto, fecha_programada, cantidad_kg, estado, origen, lotes, inventario_descontado_at, fin_real_at)
           VALUES (?, date('now','-12 days','-5 hours'), 12, 'programado', 'eos_plan', 1,
                   datetime('now','-1 days'), datetime('now','-1 days'))""",
        (PROD,))
    # Producción B: física hace 3 días (≤7 → recién hecha, en camino) → SÍ pipeline
    db.execute(
        """INSERT INTO produccion_programada
           (producto, fecha_programada, cantidad_kg, estado, origen, lotes, inventario_descontado_at)
           VALUES (?, date('now','-3 days','-5 hours'), 5, 'programado', 'eos_plan', 1, datetime('now','-3 days'))""",
        (PROD,))
    db.commit()
    db.close()

    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    d = r.get_json()
    animus = next((x for x in d["clientes"] if x["cliente_id"] == "ANIMUS_DTC"), None)
    assert animus is not None
    fila = next((p for p in animus["productos"] if p["producto_nombre"] == PROD), None)
    assert fila is not None, "producto no apareció en necesidades"
    # pipeline_kg debe ser ~5 (solo la de hace 3 días). Con el bug (fecha de descuento) sería ~17
    # (la de hace 12 días descontada hoy se contaría de nuevo, doble con la góndola).
    assert abs(fila["pipeline_kg"] - 5.0) < 0.5, (
        "la producción física de hace 12 días descontada HOY NO debe contar como pipeline", fila["pipeline_kg"])
