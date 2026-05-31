"""Pieza 2 · feed unificado de necesidades (MP + envases bajo mínimo)."""
def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_feed_necesidades(app, db_clean):
    c = _login_as(app, "sebastian")
    with app.app_context():
        from database import get_db
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM maestro_mee WHERE codigo='ENV-FEED-T'")
        # envase con stock por debajo del mínimo
        cu.execute("INSERT INTO maestro_mee (codigo, descripcion, estado, stock_actual, stock_minimo) VALUES ('ENV-FEED-T','Envase feed test','Activo',100,500)")
        conn.commit()
    r = c.get("/api/compras/feed-necesidades")
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["ok"] is True
    fila = next((x for x in d["items"] if x["codigo"] == "ENV-FEED-T"), None)
    assert fila is not None, d["items"]
    assert fila["tipo"] == "MEE"
    assert fila["faltante"] == 400  # 500-100
    assert fila["pct"] == 20  # 100/500
