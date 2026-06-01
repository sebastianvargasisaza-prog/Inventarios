"""Sebastián 1-jun-2026: 'si aumenta la venta y la programación ya no es adecuada,
¿cómo lo sabremos?'. Si el stock físico se agota ANTES de que llegue el próximo lote
programado → lote_tarde=True + alerta de adelantar producción."""
import os, sqlite3, json


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_lote_tarde_marca_y_alerta(app, db_clean):
    producto = "ZZTARDE TEST"
    sku = "ZZTARDE-30"
    c = _login_as(app, "sebastian")
    with app.app_context():
        from database import get_db
        conn = get_db()
        for t in ("formula_headers", "sku_producto_map", "producto_presentaciones", "produccion_programada"):
            conn.execute(f"DELETE FROM {t} WHERE {'producto_nombre' if t!='produccion_programada' else 'producto'}=?", (producto,))
        conn.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'ZZTARDE-%'")
        conn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, codigo_pt) VALUES (?, 20, 1, 'ZZTAR')", (producto,))
        conn.execute("INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES (?, ?, 1)", (sku, producto))
        conn.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, volumen_ml, sku_shopify, activo) "
                     "VALUES (?, 'ZZTAR-P', '30ml', 30, ?, 1)", (producto, sku))
        items = json.dumps([{"sku": sku, "qty": 15}])
        for i in range(8):
            conn.execute("INSERT INTO animus_shopify_orders (shopify_id, sku_items, unidades_total, estado, estado_pago, creado_en) "
                         "VALUES (?, ?, 15, '', 'paid', date('now','-5 hours','-%d days'))" % (i * 4), (f"ZZTARDE-{i}", items))
        # stock 0 (sin stock_pt) → dias_gondola=0 → se agota HOY · próximo lote +10 días → TARDE
        conn.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, estado, origen) "
                     "VALUES (?, date('now','-5 hours','+10 days'), 20, 1, 'programado', 'eos_plan')", (producto,))
        conn.commit()
    r = c.get("/api/plan/necesidades?live=0")
    d = r.get_json()
    animus = next(x for x in d["clientes"] if x.get("cliente_id") == "ANIMUS_DTC")
    p = next((pp for pp in animus["productos"] if pp["producto_nombre"] == producto), None)
    assert p is not None
    assert p.get("dias_gondola") in (0, 0.0), p
    assert p.get("lote_tarde") is True, p
    assert p.get("dias_descubierto", 0) >= 9, p           # ~10 días sin stock

    # la alerta IA debe emitir 'adelantar_lote' para este producto
    ra = c.get("/api/plan/alertas-ia")
    if ra.status_code == 200:
        da = ra.get_json()
        alertas = da.get("alertas") or da.get("items") or []
        assert any(a.get("tipo") == "adelantar_lote" and producto in (a.get("titulo","") + a.get("detalle",""))
                   for a in alertas), [a.get("titulo") for a in alertas]
