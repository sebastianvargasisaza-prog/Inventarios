"""Sebastián 6-jul · desglose de Necesidades respeta la CANTIDAD FIJA (mig 204) + reparto por volumen (M72).

Niacinamida: lote 90kg → 1000 uds FIJAS de 10ml (=10kg) → el resto (80kg) va al 30ml (~2666 uds).
Antes el desglose repartía por % de mix → mostraba mal (no reservaba la fija ni pesaba por volumen).
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


def test_desglose_reserva_fija_10ml_y_reparte_resto_al_30ml(app, db_clean):
    PROD = "TESTNIA FORMULA"
    S30 = "TNIA30"   # 30ml
    S10 = "TNIA10"   # 10ml · FIJA 1000
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    for t in ("formula_headers", "sku_producto_map", "producto_presentaciones"):
        db.execute(f"DELETE FROM {t} WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM stock_pt WHERE sku IN (?,?)", (S30, S10))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'TNIA-%'")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, fecha_creacion) "
               "VALUES (?, 90, 1, '2025-01-01')", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (S30, PROD))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,10,1)", (S10, PROD))
    # presentaciones: 10ml con cantidad_fija_uds=1000 · 30ml sin fija
    db.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, volumen_ml, cantidad_fija_uds, activo) "
               "VALUES (?, 'TNIA-V10', '10ml', 10, 1000, 1)", (PROD,))
    db.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, volumen_ml, cantidad_fija_uds, activo) "
               "VALUES (?, 'TNIA-V30', '30ml', 30, 0, 1)", (PROD,))
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,50,'Disponible','ANIMUS')", (S30, PROD, "L30"))
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,20,'Disponible','ANIMUS')", (S10, PROD, "L10"))
    today = date.today()
    for i in range(30):
        f = (today - timedelta(days=i + 1)).isoformat()
        db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (f"TNIA-{i}", "c", 100.0, "COP", "", "paid", json.dumps([{"sku": S30, "qty": 12}, {"sku": S10, "qty": 4}]), 16, f))
    db.commit(); db.close()

    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    animus = next(x for x in r.get_json()["clientes"] if x["cliente_id"] == "ANIMUS_DTC")
    fila = next(p for p in animus["productos"] if p["producto_nombre"] == PROD)
    tonos = {t["sku"]: t for t in (fila.get("tonos") or [])}
    assert S10 in tonos and S30 in tonos, ("faltan referencias en el desglose", list(tonos))
    u10 = tonos[S10]["uds_estim_lote"]
    u30 = tonos[S30]["uds_estim_lote"]
    # 10ml = 1000 fijas exactas · 30ml = resto (80kg / 30ml ≈ 2666)
    assert u10 == 1000, ("el 10ml debe ser 1000 FIJAS, no proporcional al mix", u10, u30)
    assert 2550 <= u30 <= 2780, ("el 30ml debe llevarse el resto del bulk (~2666)", u30, u10)
    assert tonos[S10].get("es_fija") is True, "el 10ml debe marcarse es_fija"
