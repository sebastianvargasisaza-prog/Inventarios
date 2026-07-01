"""Verifica /api/plan/diagnostico-shopify · reconciliación ventas por SKU.

Prueba que la atribución por SKU/sub-SKU sale bien y que la fuga
(SKU vacío + huérfano) se cuantifica, filtrando cancelled/refunded.
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


def _ins(db, shopify_id, sku_items, creado_en, estado="", estado_pago="paid"):
    db.execute(
        """INSERT INTO animus_shopify_orders
           (shopify_id, nombre, total, moneda, estado, estado_pago,
            sku_items, unidades_total, creado_en)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (shopify_id, "Cliente " + shopify_id, 100000.0, "COP",
         estado, estado_pago, json.dumps(sku_items),
         sum(i.get("qty", 0) for i in sku_items), creado_en),
    )


def test_diagnostico_shopify_reconciliacion(app, db_clean):
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM animus_shopify_orders")
    db.execute("DELETE FROM sku_producto_map")
    # SKU mapeado a un producto REAL (existe en formula_headers) · si no existiera, el detector
    # mapeo-zombi (27-jun) lo contaría como zombi en vez de mapeado. Sembramos la fórmula.
    db.execute("INSERT OR IGNORE INTO formula_headers (producto_nombre) VALUES ('SUERO VIT C B3')")
    db.execute(
        "INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES (?,?,1)",
        ("SVITC33", "SUERO VIT C B3"),
    )
    # Órdenes válidas (fechas claramente dentro de 30/60/90d de 2026-05-30)
    _ins(db, "OK-MAP", [{"sku": "SVITC33", "qty": 5}], "2026-05-28")
    _ins(db, "OK-HUER", [{"sku": "ZZZNOPE", "qty": 3}], "2026-05-20")
    _ins(db, "OK-VACIO", [{"sku": "", "qty": 7}], "2026-05-25")
    # Excluidas: cancelada y reembolsada (no deben contar)
    _ins(db, "X-CANCEL", [{"sku": "SVITC33", "qty": 100}], "2026-05-26",
         estado="cancelled")
    _ins(db, "X-REFUND", [{"sku": "SVITC33", "qty": 50}], "2026-05-27",
         estado_pago="refunded")
    db.commit()
    db.close()

    r = c.get("/api/plan/diagnostico-shopify")
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["ok"] is True

    rec = d["reconciliacion"]
    # 5 mapeada + 3 huérfana + 7 vacío = 15 (cancel/refund excluidas)
    assert rec["uds_total_90d"] == 15, rec
    assert rec["uds_mapeadas_90d"] == 5, rec
    assert rec["uds_huerfanas_90d"] == 3, rec
    assert rec["uds_sku_vacio_90d"] == 7, rec
    assert rec["n_skus_mapeados"] == 1, rec
    assert rec["n_skus_huerfanos"] == 1, rec
    # cobertura real = 5/15 = 33.3%
    assert 33.0 <= rec["pct_cobertura_real"] <= 33.4, rec

    # por_sku trae ambos SKUs con su estado
    by = {x["sku"]: x for x in d["por_sku"]}
    assert by["SVITC33"]["estado"] == "MAPEADO"
    assert by["SVITC33"]["producto"] == "SUERO VIT C B3"
    assert by["SVITC33"]["uds_90d"] == 5
    assert by["ZZZNOPE"]["estado"] == "HUERFANO"
    assert by["ZZZNOPE"]["producto"] is None

    # fuga SKU vacío reportada con muestra de orden
    assert d["sku_vacio"]["uds_90d"] == 7
    assert len(d["sku_vacio"]["ordenes_muestra"]) >= 1


def test_diagnostico_shopify_requiere_login(app, db_clean):
    c = app.test_client()
    r = c.get("/api/plan/diagnostico-shopify")
    assert r.status_code == 401
