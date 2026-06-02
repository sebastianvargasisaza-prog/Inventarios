"""Guard nombre↔código al guardar fórmula (1-jun-2026).

Caso real: "N-acetil glucosamina" guardada con el código MP00175 que en el
catálogo es "Acetyl tetrapeptide-5" → stock cruzado → "Hay 0g" al producir.
El form tiene código y nombre como inputs independientes; el backend solo
validaba que el código existiera. Ahora rechaza el mapeo cruzado (409) salvo
override explícito, usando blueprints.formula_match (mismo motor que el detector).
"""
import os
import sqlite3
import json

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _seed(cod, nombre_comercial, inci=""):
    db = sqlite3.connect(os.environ["DB_PATH"])
    try:
        db.execute(
            "INSERT OR REPLACE INTO maestro_mps "
            "(codigo_mp, nombre_comercial, nombre_inci, activo) VALUES (?,?,?,1)",
            (cod, nombre_comercial, inci))
        db.commit()
    finally:
        db.close()


def test_guard_rechaza_nombre_codigo_cruzado(app, db_clean):
    """Guardar 'N-acetil glucosamina' con el código del tetrapéptido → 409."""
    c = _login(app)
    _seed("MPGUARDTETRA", "Acetyl tetrapeptide-5", "Acetyl Tetrapeptide-5")
    _seed("MPGUARDGLUCO", "N-acetil glucosamina", "Acetyl Glucosamine")
    body = {"producto_nombre": "ZZ GUARD CRUZADO", "unidad_base_g": 1000, "items": [
        {"material_id": "MPGUARDTETRA", "material_nombre": "N-acetil glucosamina", "porcentaje": 1},
        {"material_id": "MPGUARDGLUCO", "material_nombre": "N-acetil glucosamina", "porcentaje": 99},
    ]}
    r = c.post("/api/formulas", data=json.dumps(body), headers=_h())
    assert r.status_code == 409, r.data
    d = r.get_json()
    assert d.get("forzar_mismatch_requerido") is True
    ms = d.get("mismatches") or []
    assert any(m["material_id"] == "MPGUARDTETRA" for m in ms), ms
    # debe sugerir una glucosamina (la sembrada o la real del catálogo)
    cruzado = next(m for m in ms if m["material_id"] == "MPGUARDTETRA")
    assert cruzado["codigo_sugerido"], cruzado
    assert "GLUCOSAMIN" in (cruzado.get("nombre_sugerido") or "").upper(), cruzado
    # NO se guardó nada
    db = sqlite3.connect(os.environ["DB_PATH"])
    try:
        n = db.execute("SELECT COUNT(*) FROM formula_items WHERE producto_nombre='ZZ GUARD CRUZADO'").fetchone()[0]
    finally:
        db.close()
    assert n == 0


def test_guard_permite_con_forzar_mismatch(app, db_clean):
    """Con forzar_mismatch=true se guarda igual (override consciente)."""
    c = _login(app)
    _seed("MPGUARDTETRA2", "Acetyl tetrapeptide-5", "Acetyl Tetrapeptide-5")
    body = {"producto_nombre": "ZZ GUARD FORZADO", "unidad_base_g": 1000,
            "forzar_mismatch": True, "items": [
                {"material_id": "MPGUARDTETRA2", "material_nombre": "N-acetil glucosamina", "porcentaje": 100},
            ]}
    r = c.post("/api/formulas", data=json.dumps(body), headers=_h())
    assert r.status_code == 201, r.data


def test_guard_acepta_sinonimo_cross_idioma(app, db_clean):
    """No debe bloquear sinónimos legítimos ES/EN (Glicerina↔Glycerin)."""
    c = _login(app)
    _seed("MPGUARDGLY", "Glycerin", "Glycerin")
    body = {"producto_nombre": "ZZ GUARD SINONIMO", "unidad_base_g": 1000, "items": [
        {"material_id": "MPGUARDGLY", "material_nombre": "Glicerina", "porcentaje": 100},
    ]}
    r = c.post("/api/formulas", data=json.dumps(body), headers=_h())
    assert r.status_code == 201, r.data
