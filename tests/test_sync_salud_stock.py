"""sync-salud ahora reporta salud del STOCK Shopify (stock_pt) + scopes del token.

Caso Sebastián 1-jun-2026: 'el stock no jala de Shopify'. La salud debe exponer
si el sync de stock corrió, cuántos SKUs quedaron disponibles vs agotados, y si
faltó el scope read_inventory (causa típica de stock=0 masivo)."""
import os, sqlite3


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_sync_salud_reporta_stock(app, db_clean):
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM stock_pt WHERE sku LIKE 'SALUDTEST%'")
    # 1 SKU disponible (Available) + 1 agotado → la salud debe contarlos
    db.execute("INSERT INTO stock_pt (sku, lote_produccion, unidades_disponible, empresa, estado, observaciones) "
               "VALUES ('SALUDTEST-A', 'SHOPIFY-2026-06-01', 50, 'ANIMUS', 'Disponible', 'Sync Shopify (Available)')")
    db.execute("INSERT INTO stock_pt (sku, lote_produccion, unidades_disponible, empresa, estado, observaciones) "
               "VALUES ('SALUDTEST-B', 'SHOPIFY-2026-06-01', 0, 'ANIMUS', 'Agotado', 'Sync Shopify · agotado (Available=0)')")
    db.commit(); db.close()
    r = c.get("/api/programacion/sync-salud")
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert "stock" in d, d
    st = d["stock"]
    assert st.get("skus_disponibles", 0) >= 1, st
    assert st.get("skus_agotados", 0) >= 1, st
    assert st.get("uds_disponibles_total", 0) >= 50, st
    assert st.get("uso_available") is True, st
    # scopes: sin token configurado en test → reporta error/no configurado (no crashea)
    assert "shopify_scopes" in d, d


def test_reconciliar_shopify_sin_config(app, db_clean):
    """Smoke · el endpoint de reconciliación responde limpio sin Shopify configurado
    (no 500). Con token devolvería filas SKU x SKU."""
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM animus_config WHERE clave IN ('shopify_token','shopify_shop')")
    db.commit(); db.close()
    r = c.get("/api/programacion/reconciliar-shopify")
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d.get("ok") is False
    assert "configurado" in (d.get("error") or "").lower(), d


def test_reconciliar_shopify_requiere_auth(app, db_clean):
    r = app.test_client().get("/api/programacion/reconciliar-shopify")
    assert r.status_code == 401


def test_shopify_location_id_usa_config(app, db_clean):
    """SOLO tienda ÁNIMUS LAB · animus_config('shopify_location_id') manda y NO
    requiere red. Sin config (y sin red en test) devuelve None (suma todas =
    comportamiento previo, no rompe)."""
    with app.app_context():
        from database import get_db
        from blueprints.programacion import _shopify_location_id
        conn = get_db()
        conn.execute("DELETE FROM animus_config WHERE clave='shopify_location_id'")
        conn.commit()
        # sin config + sin red → None (no rompe)
        assert _shopify_location_id(conn, "tok", "x.myshopify.com") is None
        # con config → la usa sin tocar red
        conn.execute("INSERT INTO animus_config (clave, valor) VALUES ('shopify_location_id','72866627864')")
        conn.commit()
        assert _shopify_location_id(conn, "tok", "x.myshopify.com") == "72866627864"
