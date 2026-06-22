"""Ajustar % de fórmula (admin.py · /api/admin/ajustar-formula-pct).

Corrección fina de % de ingredientes puntuales (ej. alinear EOS con MyBatch · caso real
Trietanolamina 0.2→0.1 en Limpiador Hidratante). dry-run + apply + recalcula g/lote. Admin.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = "ZZ AJUSTE TEST"


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _csrf(c):
    return {"X-CSRF-Token": c.get("/api/csrf-token").get_json()["csrf_token"]}


def _seed():
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
    conn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
    for cod in ("MPAJAGUA", "MPAJTEA", "MPAJFILL"):
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
        conn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, proveedor, activo) "
                     "VALUES (?,?,?,1)", (cod, cod, "Test"))
    conn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,80,1)", (PROD,))
    # agua 82.14 + TEA 0.20 + filler 17.66 = 100
    for cod, nom, pct, g in (("MPAJAGUA", "Agua", 82.14, 65712), ("MPAJTEA", "TEA", 0.20, 160),
                             ("MPAJFILL", "Filler", 17.66, 14128)):
        conn.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
                     "VALUES (?,?,?,?,?)", (PROD, cod, nom, pct, g))
    conn.commit(); conn.close()


def test_dry_run_reporta_y_no_escribe(app, db_clean):
    _seed()
    c = _login(app)
    r = c.post("/api/admin/ajustar-formula-pct", json={
        "producto": "zz ajuste test", "dry_run": 1,
        "items": [{"material_id": "MPAJTEA", "pct": 0.1}, {"material_id": "MPAJAGUA", "pct": 82.24}]},
        headers=_csrf(c))
    assert r.status_code == 200, r.data
    j = r.get_json()
    assert j["nombre_real"] == PROD
    tea = next(x for x in j["cambios"] if x["material_id"] == "MPAJTEA")
    assert tea["pct_actual"] == 0.2 and tea["pct_nuevo"] == 0.1
    assert tea["g_por_lote_nuevo"] == 80.0           # 0.1% de 80kg
    assert abs(j["suma_resultante"] - 100.0) < 0.01 and j["suma_100"] is True
    # no escribió
    conn = sqlite3.connect(os.environ["DB_PATH"])
    p = conn.execute("SELECT porcentaje FROM formula_items WHERE producto_nombre=? AND material_id='MPAJTEA'", (PROD,)).fetchone()[0]
    conn.close()
    assert p == 0.2


def test_aplica_y_recalcula_gramos(app, db_clean):
    _seed()
    c = _login(app)
    r = c.post("/api/admin/ajustar-formula-pct", json={
        "producto": PROD, "dry_run": 0,
        "items": [{"material_id": "MPAJTEA", "pct": 0.1}, {"material_id": "MPAJAGUA", "pct": 82.24}]},
        headers=_csrf(c))
    assert r.status_code == 200, r.data
    assert r.get_json()["aplicado"] is True
    conn = sqlite3.connect(os.environ["DB_PATH"])
    tea = conn.execute("SELECT porcentaje, cantidad_g_por_lote FROM formula_items WHERE producto_nombre=? AND material_id='MPAJTEA'", (PROD,)).fetchone()
    agua = conn.execute("SELECT porcentaje, cantidad_g_por_lote FROM formula_items WHERE producto_nombre=? AND material_id='MPAJAGUA'", (PROD,)).fetchone()
    conn.close()
    assert tea[0] == 0.1 and tea[1] == 80.0
    assert agua[0] == 82.24 and agua[1] == 65792.0   # 82.24% de 80kg


def test_material_inexistente_reporta_error(app, db_clean):
    _seed()
    c = _login(app)
    r = c.post("/api/admin/ajustar-formula-pct", json={
        "producto": PROD, "dry_run": 1, "items": [{"material_id": "MPNOPE", "pct": 1.0}]}, headers=_csrf(c))
    assert r.status_code == 200, r.data
    ch = r.get_json()["cambios"][0]
    assert ch["material_id"] == "MPNOPE" and "error" in ch


def test_requiere_admin(app, db_clean):
    c = _login(app, user="catalina")
    r = c.post("/api/admin/ajustar-formula-pct", json={"producto": "x", "items": [{"material_id": "y", "pct": 1}]},
               headers=_csrf(c))
    assert r.status_code in (401, 403)
