"""Read-only · /api/admin/diag-familia-producto · radiografía familia de producto."""
import os, sqlite3


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_diag_familia_producto(app, db_clean):
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM formula_headers WHERE producto_nombre LIKE 'LIPDIAG%'")
    db.execute("DELETE FROM sku_producto_map WHERE producto_nombre LIKE 'LIPDIAG%'")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('LIPDIAG SERUM X', 12, 1)")
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES ('LIPDIAGSKU', 'LIPDIAG SERUM X', 1)")
    db.commit(); db.close()
    r = c.get("/api/admin/diag-familia-producto?q=LIPDIAG")
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["ok"] is True
    assert any(f["producto_nombre"] == "LIPDIAG SERUM X" for f in d["formulas"]), d["formulas"]
    assert any(s["sku"] == "LIPDIAGSKU" for s in d["skus"]), d["skus"]


def test_diag_familia_requiere_q(app, db_clean):
    c = _login_as(app, "sebastian")
    r = c.get("/api/admin/diag-familia-producto")
    assert r.status_code == 400
