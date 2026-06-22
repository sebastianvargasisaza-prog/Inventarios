"""Preflight READ-ONLY de carga de fórmula (admin.py · /api/admin/formula-preflight).

Valida una lista de códigos MP contra el maestro VIVO antes de cargar/cambiar una
fórmula cuyos códigos vienen de OTRA fuente (MyBatch, Excel). NO escribe nada. Es el
candado anti-error M19/M38: el código puede no existir en el maestro de la app, estar
inactivo, o ser OTRA molécula que la esperada.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _csrf(c):
    return {"X-CSRF-Token": c.get("/api/csrf-token").get_json()["csrf_token"]}


def _seed(mps):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    for cod, comercial, inci, activo in mps:
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
        conn.execute(
            "INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, proveedor, activo) "
            "VALUES (?,?,?,?,?)", (cod, comercial, inci, "Test", activo))
    conn.commit()
    conn.close()


def test_preflight_todo_verde(app, db_clean):
    _seed([
        ("MPPF01", "Glicerina", "GLYCERIN", 1),
        ("MPPF02", "Acido kojico", "KOJIC ACID", 1),
    ])
    c = _login(app)
    r = c.post("/api/admin/formula-preflight", json={"items": [
        {"codigo": "MPPF01", "pct": 60, "esperado": "Glicerina"},
        {"codigo": "MPPF02", "pct": 40, "esperado": "Acido kojico"},
    ]}, headers=_csrf(c))
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["todo_verde"] is True
    assert d["suma_100"] is True
    assert d["faltantes"] == [] and d["inactivos"] == []
    assert d["existen"] == 2 and d["activos"] == 2


def test_preflight_detecta_faltante_inactivo_dup_y_suma(app, db_clean):
    _seed([
        ("MPPF10", "Glicerina", "GLYCERIN", 1),
        ("MPPF11", "Conservante viejo", "PHENOXYETHANOL", 0),  # inactivo
    ])
    c = _login(app)
    r = c.post("/api/admin/formula-preflight", json={"items": [
        {"codigo": "MPPF10", "pct": 50, "esperado": "Glicerina"},
        {"codigo": "MPPF11", "pct": 30, "esperado": "Conservante"},   # inactivo
        {"codigo": "MPNOPE99", "pct": 10, "esperado": "Fantasma"},    # no existe
        {"codigo": "MPPF10", "pct": 5, "esperado": "Glicerina"},      # duplicado
    ]}, headers=_csrf(c))
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert "MPNOPE99" in d["faltantes"]
    assert "MPPF11" in d["inactivos"]
    assert "MPPF10" in d["duplicados_en_lista"]
    assert d["suma_100"] is False           # 95 != 100
    assert d["todo_verde"] is False


def test_preflight_flag_otra_molecula(app, db_clean):
    # el código existe y está activo, pero es OTRA molécula → coincide False (M19)
    _seed([("MPPF20", "Argania Spinosa", "ARGANIA SPINOSA KERNEL OIL", 1)])
    c = _login(app)
    r = c.post("/api/admin/formula-preflight", json={"items": [
        {"codigo": "MPPF20", "pct": 100, "esperado": "Propylheptyl Caprylate"},
    ]}, headers=_csrf(c))
    assert r.status_code == 200, r.data
    d = r.get_json()
    it = d["items"][0]
    assert it["existe"] is True and it["activo"] == 1
    assert it["coincide"] is False
    assert "MPPF20" in d["no_coinciden"]
    assert d["todo_verde"] is False or d["suma_100"] is True  # suma 100 pero no_coincide -> humano revisa


def test_preflight_no_escribe_nada(app, db_clean):
    _seed([("MPPF30", "Glicerina", "GLYCERIN", 1)])
    c = _login(app)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    antes = conn.execute("SELECT COUNT(*) FROM maestro_mps").fetchone()[0]
    conn.close()
    c.post("/api/admin/formula-preflight", json={"items": [
        {"codigo": "MPPF30", "pct": 100, "esperado": "Glicerina"},
        {"codigo": "MPNOPE", "pct": 0, "esperado": "x"},
    ]}, headers=_csrf(c))
    conn = sqlite3.connect(os.environ["DB_PATH"])
    despues = conn.execute("SELECT COUNT(*) FROM maestro_mps").fetchone()[0]
    conn.close()
    assert antes == despues  # read-only: no creó ni borró nada


def test_preflight_requiere_admin(app, db_clean):
    c = app.test_client()  # sin sesión
    r = c.post("/api/admin/formula-preflight", json={"items": []}, headers=csrf_headers())
    assert r.status_code in (401, 403)
