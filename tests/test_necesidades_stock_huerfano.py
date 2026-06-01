"""Caso 'Limpiador BHA: vende pero stock 0'.

Cuando el SKU de la VARIANTE en Shopify (con el que el sync escribe stock_pt)
difiere del SKU de la ORDEN (mapeado en sku_producto_map · con el que funciona la
velocidad), el stock quedaba huérfano → Stock=0. El fix lo atribuye al producto vía
producto_presentaciones.sku_shopify. Aditivo, sin doble conteo.
"""
import os, sqlite3


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _stock_de(client, producto):
    r = client.get("/api/plan/necesidades?cobertura_dias_minimo=20&cobertura_dias_alerta=25&cobertura_dias_vigilar=45")
    assert r.status_code == 200, r.data
    d = r.get_json()
    animus = next((c for c in (d.get("clientes") or []) if c.get("cliente_id") == "ANIMUS_DTC"), None)
    assert animus is not None, d
    p = next((pp for pp in animus["productos"] if pp["producto_nombre"] == producto), None)
    return p


def _seed_base(db, producto):
    db.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (producto,))
    db.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (producto,))
    db.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (producto,))
    db.execute("DELETE FROM stock_pt WHERE sku IN ('ZZBHA-ORD','ZZBHA-VAR')")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, codigo_pt) "
               "VALUES (?, 10, 1, 'ZZBHA')", (producto,))
    # SKU de la ORDEN (mapeado) → da velocidad pero NO tiene stock_pt
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES ('ZZBHA-ORD', ?, 1)", (producto,))
    # SKU de la VARIANTE (NO está en sku_producto_map) registrado en presentaciones
    db.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, "
               "volumen_ml, sku_shopify, activo) VALUES (?, 'ZZBHA-150', '150ml', 150, 'ZZBHA-VAR', 1)", (producto,))


def test_stock_huerfano_por_variante_se_atribuye(app, db_clean):
    producto = "ZZBHA LIMPIADOR TEST"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    _seed_base(db, producto)
    # stock SOLO bajo el SKU de la variante (huérfano para sku_producto_map)
    db.execute("INSERT INTO stock_pt (sku, lote_produccion, unidades_disponible, empresa, estado, observaciones) "
               "VALUES ('ZZBHA-VAR', 'SHOPIFY-2026-06-01', 40, 'ANIMUS', 'Disponible', 'Sync Shopify (Available)')")
    db.commit(); db.close()
    p = _stock_de(c, producto)
    assert p is not None, "el producto debe aparecer en ANIMUS_DTC"
    assert p["stock_uds_total"] >= 40, p   # el stock huérfano AHORA se atribuye


def test_no_doble_conteo_si_sku_en_ambos(app, db_clean):
    """Si el mismo SKU está en sku_producto_map Y en presentaciones, se cuenta UNA vez."""
    producto = "ZZBHA LIMPIADOR TEST"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    _seed_base(db, producto)
    # ahora el SKU de la variante TAMBIÉN está mapeado → no debe duplicar
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES ('ZZBHA-VAR', ?, 1)", (producto,))
    db.execute("INSERT INTO stock_pt (sku, lote_produccion, unidades_disponible, empresa, estado, observaciones) "
               "VALUES ('ZZBHA-VAR', 'SHOPIFY-2026-06-01', 40, 'ANIMUS', 'Disponible', 'Sync Shopify (Available)')")
    db.commit(); db.close()
    p = _stock_de(c, producto)
    assert p is not None
    assert p["stock_uds_total"] == 40, p   # exactamente 40, no 80
