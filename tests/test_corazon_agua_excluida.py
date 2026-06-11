"""Fix 11-jun: MP con controla_stock=0 (agua del lab / consumibles infinitos · mig 218)
NO debe aparecer en la tabla de Abastecimiento (no se compran nunca). Sebastián lo cazó:
el Agua Desionizada salía con déficit y Pedir gigante.
"""
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


def test_mp_controla_stock_cero_se_excluye(app, db_clean):
    prod = "QAAGUA PROD"
    # MP infinita (agua) · controla_stock=0 · + MP normal en la misma fórmula
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo,controla_stock) "
          "VALUES ('MP-QAAGUA','Agua QA','AQUA',1,0)")
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo,controla_stock) "
          "VALUES ('MP-QANORMAL','Normal QA','NORMAL QA',1,1)")
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,10,1)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES (?,'MP-QAAGUA','Agua QA',80,0)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES (?,'MP-QANORMAL','Normal QA',10,0)", (prod,))
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, estado, origen) "
          "VALUES (?, date('now','-5 hours','+3 days'), 10, 1, 'pendiente', 'eos_plan')", (prod,))

    c = _login(app)
    mps = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp&horizontes=15,30,60,90").get_json().get("mps", [])
    cods = {(m.get("codigo") or "").upper() for m in mps}
    assert "MP-QAAGUA" not in cods, "el agua (controla_stock=0) NO debe aparecer en Abastecimiento"
    assert "MP-QANORMAL" in cods, "la MP normal de la misma fórmula SÍ debe aparecer (no rompimos lo bueno)"
