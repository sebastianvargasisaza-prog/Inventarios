"""Sebastián 1-jun-2026: la sugerencia de próxima producción debe basarse SOLO en
los kg que van para Animus, no en el total del lote (la parte B2B va a otro cliente
y no cubre la venta de Animus). Lote 45kg con 4.5kg B2B → dura según 40.5kg."""
import os, sqlite3, json


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_proxima_sugerida_solo_animus(app, db_clean):
    producto = "ZZSUG ANIMUS TEST"
    sku = "ZZSUG-30"
    c = _login_as(app, "sebastian")
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (producto,))
        conn.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (producto,))
        conn.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (producto,))
        conn.execute("DELETE FROM produccion_programada WHERE producto=?", (producto,))
        conn.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'ZZSUG-%'")
        conn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, codigo_pt) VALUES (?, 45, 1, 'ZZSUG')", (producto,))
        conn.execute("INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES (?, ?, 1)", (sku, producto))
        conn.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, volumen_ml, sku_shopify, activo) "
                     "VALUES (?, 'ZZSUG-P', '30ml', 30, ?, 1)", (producto, sku))
        # ventas → velocidad > 0
        items = json.dumps([{"sku": sku, "qty": 12}])
        for i in range(8):
            conn.execute("INSERT INTO animus_shopify_orders (shopify_id, sku_items, unidades_total, estado, estado_pago, creado_en) "
                         "VALUES (?, ?, 12, '', 'paid', date('now','-5 hours','-%d days'))" % (i * 4), (f"ZZSUG-{i}", items))
        # ancla = lote Fijo futuro de 45kg, con 4.5kg para B2B (Kelly)
        cur = conn.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, estado, origen) "
                           "VALUES (?, date('now','-5 hours','+5 days'), 45, 1, 'programado', 'eos_plan')", (producto,))
        pid = cur.lastrowid
        conn.execute("INSERT INTO pedidos_b2b_lote (pedido_b2b_id, lote_produccion_id, kg_aporte, unidades_aporte, ml_unidad, cliente_nombre, modo) "
                     "VALUES (888, ?, 4.5, 150, 30, 'Kelly', 'sumado_a_lote_canonico')", (pid,))
        conn.commit()
    r = c.get("/api/plan/necesidades?live=0")
    assert r.status_code == 200, r.data
    d = r.get_json()
    animus = next(x for x in d["clientes"] if x.get("cliente_id") == "ANIMUS_DTC")
    p = next((pp for pp in animus["productos"] if pp["producto_nombre"] == producto), None)
    assert p is not None
    vel = p.get("velocidad_kg_dia") or 0
    assert vel > 0, p
    assert p.get("ancla_kg_b2b") == 4.5, p
    assert p.get("ancla_kg_animus") == 40.5, p          # 45 − 4.5 B2B
    # duración basada en 40.5 (Animus), NO en 45 (total)
    assert p.get("duracion_lote_dias") == int(40.5 / vel), p
    assert p.get("duracion_lote_dias") != int(45.0 / vel) or 40.5 == 45.0, p
