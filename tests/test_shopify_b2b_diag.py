"""Verificación config · test-shopify expone el filtro SHOPIFY_B2B_TAGS."""
def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_test_shopify_b2b_configurado(app, db_clean, monkeypatch):
    monkeypatch.setenv("SHOPIFY_B2B_TAGS", "mayorista,b2b")
    c = _login_as(app, "sebastian")
    r = c.get("/api/programacion/sync-salud")
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert "b2b" in d, d
    assert d["b2b"]["configurado"] is True
    assert "mayorista" in d["b2b"]["tags_configurados"]
    assert d["b2b"]["columnas_tags_existen"] is True


def test_test_shopify_b2b_vacio(app, db_clean, monkeypatch):
    monkeypatch.delenv("SHOPIFY_B2B_TAGS", raising=False)
    c = _login_as(app, "sebastian")
    r = c.get("/api/programacion/sync-salud")
    assert r.status_code == 200
    d = r.get_json()
    assert d["b2b"]["configurado"] is False
    assert d["b2b"]["tags_configurados"] == []
