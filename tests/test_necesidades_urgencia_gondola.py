"""Sebastián 1-jun-2026: 'unos dicen alcanza 0 días pero no salen en rojo'.
La urgencia/alerta debe basarse en el stock FÍSICO de góndola (dias_gondola), no en
la cobertura-con-pipeline. Un producto agotado (stock 0) con ventas debe salir CRÍTICO
aunque tenga un lote programado (pipeline)."""
import os, sqlite3, json


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_stock_cero_con_pipeline_es_critico(app, db_clean):
    producto = "ZZGONDOLA CRITICO TEST"
    sku = "ZZGON-30"
    c = _login_as(app, "sebastian")
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (producto,))
        conn.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (producto,))
        conn.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'ZZGON-%'")
        conn.execute("DELETE FROM produccion_programada WHERE producto=?", (producto,))
        conn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, codigo_pt) "
                     "VALUES (?, 10, 1, 'ZZGON')", (producto,))
        conn.execute("INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES (?, ?, 1)", (sku, producto))
        # ventas recientes → velocidad > 0 (sin stock_pt → stock 0 = góndola 0)
        items = json.dumps([{"sku": sku, "qty": 10}])
        for i in range(6):
            conn.execute(
                "INSERT INTO animus_shopify_orders (shopify_id, sku_items, unidades_total, estado, estado_pago, creado_en) "
                "VALUES (?, ?, 10, '', 'paid', date('now','-5 hours','-%d days'))" % (i * 3),
                (f"ZZGON-{i}", items))
        # lote Fijo programado a futuro (pipeline) → cobertura-con-pipeline alta
        conn.execute(
            "INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, estado, origen) "
            "VALUES (?, date('now','-5 hours','+5 days'), 10, 1, 'programado', 'eos_plan')", (producto,))
        conn.commit()
    r = c.get("/api/plan/necesidades?live=0")
    assert r.status_code == 200, r.data
    d = r.get_json()
    animus = next((x for x in (d.get("clientes") or []) if x.get("cliente_id") == "ANIMUS_DTC"), None)
    assert animus is not None
    p = next((pp for pp in animus["productos"] if pp["producto_nombre"] == producto), None)
    assert p is not None, "producto no apareció"
    assert p["stock_uds_total"] == 0, p
    assert p["dias_gondola"] in (0, 0.0), p              # góndola vacía → 0 días reales
    assert p["urgencia"] == "CRITICO", p                  # CRÍTICO pese al pipeline
    # la cobertura-con-pipeline SÍ puede ser alta (anotación +prod), pero no manda la alerta
    assert p.get("ya_programado") is True, p
