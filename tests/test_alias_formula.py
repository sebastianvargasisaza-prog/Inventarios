"""Sebastián 17-jul · B3: alias producto→fórmula (mig 358). Cuando el nombre del producto en el PLAN
difiere del de la FÓRMULA (renombre/sinónimo), el match falla y la MP se cuenta en 0 (compra de menos).
Vincular el alias hace que su materia prima SÍ se cuente. Nunca fuzzy automático (lo confirma el humano)."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def _mps(client):
    r = client.get("/api/abastecimiento/consumo-horizontes?tipo=mp&horizontes=15,30,60,90")
    assert r.status_code == 200, r.data
    return r.get_json()


def test_alias_resuelve_match(app, db_clean):
    cod = "MP-ALIASZZ"
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES (?, 'Alias ZZ', 'ALIAS INCI', 1)", (cod,))
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('CREMA ALIAS', 1, 1)")
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES ('CREMA ALIAS', ?, 'Alias ZZ', 10, 0)", (cod,))
    # producción con nombre DISTINTO (renombrado · token '10' agregado) → NO cruza
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('CREMA ALIAS 10', date('now','-5 hours','+5 days'), 1, 'pendiente', 10, 'eos_plan')")
    c = _login(app)
    # ANTES de vincular: la MP no se cuenta y el producto está en sin_formula
    d = _mps(c)
    codigos = [(m.get("codigo") or "").upper() for m in d.get("mps", [])]
    assert cod.upper() not in codigos, "sin alias, la MP no debe contarse"
    assert any("CREMA ALIAS 10" in str(s) for s in d.get("productos_sin_match_formula", [])), \
        d.get("productos_sin_match_formula")
    # vincular
    r2 = c.post("/api/abastecimiento/vincular-formula",
                json={"producto_plan": "CREMA ALIAS 10", "producto_formula": "CREMA ALIAS"},
                headers=csrf_headers())
    assert r2.status_code == 200, r2.data[:300]
    # DESPUÉS: la MP aparece con demanda (10% × 10kg = 1000 g)
    d3 = _mps(c)
    mp = next((m for m in d3.get("mps", []) if (m.get("codigo") or "").upper() == cod.upper()), None)
    assert mp is not None, "tras vincular, la MP debe aparecer"
    assert mp["consumo"]["90"] > 0, mp["consumo"]


def test_vincular_valida_formula_existe(app, db_clean):
    c = _login(app)
    r = c.post("/api/abastecimiento/vincular-formula",
               json={"producto_plan": "X PLAN", "producto_formula": "NO EXISTE ZZZ"},
               headers=csrf_headers())
    assert r.status_code == 400, r.data[:200]


def test_vincular_y_desvincular(app, db_clean):
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('FORM REAL', 1, 1)")
    c = _login(app)
    r = c.post("/api/abastecimiento/vincular-formula",
               json={"producto_plan": "PLAN X", "producto_formula": "FORM REAL"}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    row = _exec("SELECT 1", ())  # noqa · just to reuse connection helper style
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        act = conn.execute("SELECT activo FROM producto_formula_alias WHERE producto_plan='PLAN X'").fetchone()
        assert act and act[0] == 1
    finally:
        conn.close()
    # desvincular (producto_formula vacío)
    r2 = c.post("/api/abastecimiento/vincular-formula",
                json={"producto_plan": "PLAN X", "producto_formula": ""}, headers=csrf_headers())
    assert r2.status_code == 200, r2.data[:300]
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        act = conn.execute("SELECT activo FROM producto_formula_alias WHERE producto_plan='PLAN X'").fetchone()
        assert act and act[0] == 0
    finally:
        conn.close()
