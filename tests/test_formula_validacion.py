"""audit MP/fórmulas 1-jun: al guardar fórmula, consolidar material_id duplicado (no
doble-contar en producción) y rechazar suma de % >100 (imposible)."""
import os, sqlite3, json

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _h():
    h = {"Content-Type": "application/json"}; h.update(csrf_headers()); return h


def _seed_mp(cod):
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) VALUES (?,?,?,1)",
               (cod, cod, cod))
    db.commit(); db.close()


def test_formula_consolida_material_duplicado(app, db_clean):
    c = _login(app)
    _seed_mp("MPFV1")
    body = {"producto_nombre": "ZZ FORMVAL DUP", "unidad_base_g": 1000, "items": [
        {"material_id": "MPFV1", "material_nombre": "MPFV1", "porcentaje": 30},
        {"material_id": "MPFV1", "material_nombre": "MPFV1", "porcentaje": 20},  # duplicado
        {"material_id": "MPFV1", "material_nombre": "MPFV1", "porcentaje": 50},  # qs (suma 100)
    ]}
    r = c.post("/api/formulas", data=json.dumps(body), headers=_h())
    assert r.status_code == 201, r.data
    assert r.get_json()["items_count"] == 1, r.get_json()   # consolidado a 1
    db = sqlite3.connect(os.environ["DB_PATH"])
    rows = db.execute("SELECT porcentaje FROM formula_items WHERE producto_nombre='ZZ FORMVAL DUP'").fetchall()
    db.close()
    assert len(rows) == 1, rows
    assert abs(rows[0][0] - 100.0) < 0.01, rows   # 30+20+50 sumados, una línea


def test_formula_rechaza_suma_mayor_100(app, db_clean):
    c = _login(app)
    _seed_mp("MPFV2"); _seed_mp("MPFV3")
    body = {"producto_nombre": "ZZ FORMVAL SOBRE", "unidad_base_g": 1000, "items": [
        {"material_id": "MPFV2", "material_nombre": "MPFV2", "porcentaje": 80},
        {"material_id": "MPFV3", "material_nombre": "MPFV3", "porcentaje": 60},  # suma 140%
    ]}
    r = c.post("/api/formulas", data=json.dumps(body), headers=_h())
    assert r.status_code == 400, r.data
    assert "suma" in (r.get_json().get("error", "").lower())
