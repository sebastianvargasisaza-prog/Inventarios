"""Tesorería · vigilancia de precios (18-jul): detecta MPs cuyo último precio subió vs el
promedio histórico (precios_historico_mp · $/g). Gate gerencia/contadora."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def _seed_precio(cod, precio_g, fecha, prov="Prov X", oc=""):
    _exec("INSERT INTO precio_historico_mp (codigo_mp,nombre_mp,proveedor,precio_unit_g,fecha,fuente,oc_numero) "
          "VALUES (?, ?, ?, ?, ?, 'oc_creada', ?)", (cod, "MP Vigila ZZ", prov, precio_g, fecha, oc))


def test_vigilancia_detecta_salto(app, db_clean):
    cod = "MP-VIG1"
    # historial: 3 precios bajos (~100 $/g) y el último alto (150 = +50%)
    _seed_precio(cod, 100, "2026-05-01")
    _seed_precio(cod, 100, "2026-06-01")
    _seed_precio(cod, 100, "2026-06-15")
    _seed_precio(cod, 150, "2026-07-10", prov="Prov Caro", oc="OC-2026-9999")
    c = _login(app)
    d = c.get("/api/compras/vigilancia-precios?umbral=20&dias=3650").get_json()
    assert d.get("ok")
    mine = [a for a in d.get("anomalias", []) if a["codigo"] == cod]
    assert mine, f"el salto de precio debe detectarse · {[a['codigo'] for a in d.get('anomalias', [])][:8]}"
    a = mine[0]
    assert a["variacion_pct"] >= 45, f"variación ~50% · got {a['variacion_pct']}"
    assert a["precio_ultimo_kg"] == 150000  # 150 $/g × 1000
    assert a["proveedor"] == "Prov Caro"


def test_vigilancia_no_marca_estable(app, db_clean):
    cod = "MP-VIG2"
    _seed_precio(cod, 200, "2026-06-01")
    _seed_precio(cod, 205, "2026-07-01")  # +2.5% solo
    c = _login(app)
    d = c.get("/api/compras/vigilancia-precios?umbral=20&dias=3650").get_json()
    assert not [a for a in d.get("anomalias", []) if a["codigo"] == cod], "una subida chica no es anomalía"


def test_vigilancia_gate(app, db_clean):
    c = app.test_client()
    r = c.post("/login", data={"username": "laura", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    resp = c.get("/api/compras/vigilancia-precios")
    assert resp.status_code == 403, "solo gerencia/contadora"
