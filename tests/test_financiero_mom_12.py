"""Tests del endpoint /api/financiero/mom-12-meses + UI render del card.

Verifica:
- RBAC: solo admin/contadora pueden acceder
- Estructura: 12 meses contiguos hacia atrás siempre
- Cálculo correcto de margen + MoM% con datos sembrados
- Stats: mejor_mes / peor_mes / margen_promedio / top_categoria_egreso
- UI page /financiero incluye el card y JS handlers
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


def test_mom_12_requires_auth(client, db_clean):
    r = client.get("/api/financiero/mom-12-meses")
    assert r.status_code == 401


def test_mom_12_user_no_admin_no_contadora_401(app, db_clean):
    """Usuario sin acceso financiero recibe 401 (mismo gate que kpis)."""
    c = _login(app, "luis")  # luis no es admin ni contadora
    r = c.get("/api/financiero/mom-12-meses")
    assert r.status_code == 401


def test_mom_12_devuelve_12_meses_contiguos(app, db_clean):
    """Aunque no haya datos, devuelve 12 períodos contiguos hacia atrás."""
    c = _login(app, "sebastian")
    r = c.get("/api/financiero/mom-12-meses")
    assert r.status_code == 200
    d = r.get_json()
    assert "meses" in d
    assert len(d["meses"]) == 12
    # Períodos deben ser YYYY-MM strings
    for m in d["meses"]:
        assert "periodo" in m
        assert len(m["periodo"]) == 7  # YYYY-MM
        assert "ingresos" in m and "egresos" in m
        assert "margen" in m and "margen_pct" in m
    # rango debe coincidir con primero/último de meses
    assert d["rango"]["desde"] == d["meses"][0]["periodo"]
    assert d["rango"]["hasta"] == d["meses"][-1]["periodo"]


def test_mom_12_calcula_margen_correcto(app, db_clean):
    """Sembrar dos meses contiguos y verificar cálculos + MoM."""
    c = _login(app, "sebastian")
    # Determinar los 2 meses más recientes que devuelve el endpoint
    r = c.get("/api/financiero/mom-12-meses")
    meses_endpoint = r.get_json()["meses"]
    p_ult = meses_endpoint[-1]["periodo"]
    p_pen = meses_endpoint[-2]["periodo"]

    conn = sqlite3.connect(os.environ["DB_PATH"])
    # Cleanup
    conn.execute("DELETE FROM flujo_ingresos WHERE periodo IN (?,?)", (p_ult, p_pen))
    conn.execute("DELETE FROM flujo_egresos WHERE periodo IN (?,?)", (p_ult, p_pen))
    # Mes anterior: 5M ingresos
    conn.execute("""INSERT INTO flujo_ingresos (fecha, periodo, monto, concepto)
                    VALUES (date('now'), ?, 5000000, 'Test pen')""", (p_pen,))
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 3000000, 'Test pen', 'MPs')""", (p_pen,))
    # Mes último: 8M ingresos (60% MoM)
    conn.execute("""INSERT INTO flujo_ingresos (fecha, periodo, monto, concepto)
                    VALUES (date('now'), ?, 8000000, 'Test ult')""", (p_ult,))
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 5000000, 'Test ult', 'Nomina')""", (p_ult,))
    conn.commit(); conn.close()
    try:
        r = c.get("/api/financiero/mom-12-meses")
        d = r.get_json()
        meses = d["meses"]
        # Buscar los 2 meses sembrados
        m_pen = next(m for m in meses if m["periodo"] == p_pen)
        m_ult = next(m for m in meses if m["periodo"] == p_ult)
        assert m_pen["ingresos"] == 5000000
        assert m_pen["margen"] == 2000000
        assert m_pen["margen_pct"] == 40.0
        assert m_ult["ingresos"] == 8000000
        assert m_ult["margen"] == 3000000
        # MoM ingreso último: (8M - 5M) / 5M * 100 = 60.0
        assert m_ult["mom_pct"] == 60.0
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM flujo_ingresos WHERE periodo IN (?,?)", (p_ult, p_pen))
        conn.execute("DELETE FROM flujo_egresos WHERE periodo IN (?,?)", (p_ult, p_pen))
        conn.commit(); conn.close()


def test_mom_12_stats_mejor_peor_promedio(app, db_clean):
    """Stats deben identificar mejor mes y peor mes."""
    c = _login(app, "sebastian")
    r = c.get("/api/financiero/mom-12-meses")
    meses_endpoint = r.get_json()["meses"]
    p_a = meses_endpoint[-3]["periodo"]
    p_b = meses_endpoint[-2]["periodo"]

    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM flujo_ingresos WHERE periodo IN (?,?)", (p_a, p_b))
    conn.execute("DELETE FROM flujo_egresos WHERE periodo IN (?,?)", (p_a, p_b))
    # p_a: margen alto (10M ingreso, 1M egreso = 9M margen)
    conn.execute("""INSERT INTO flujo_ingresos (fecha, periodo, monto, concepto)
                    VALUES (date('now'), ?, 10000000, 'Mejor mes')""", (p_a,))
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 1000000, 'Mejor egr', 'MPs')""", (p_a,))
    # p_b: margen bajo/negativo (3M ingreso, 5M egreso = -2M margen)
    conn.execute("""INSERT INTO flujo_ingresos (fecha, periodo, monto, concepto)
                    VALUES (date('now'), ?, 3000000, 'Peor mes')""", (p_b,))
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 5000000, 'Peor egr', 'Nomina')""", (p_b,))
    conn.commit(); conn.close()
    try:
        r = c.get("/api/financiero/mom-12-meses")
        d = r.get_json()
        stats = d.get("stats", {})
        assert stats.get("mejor_mes") == p_a
        assert stats.get("peor_mes") == p_b
        assert stats.get("mejor_mes_margen") == 9000000
        assert stats.get("peor_mes_margen") == -2000000
        assert "margen_promedio" in stats
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM flujo_ingresos WHERE periodo IN (?,?)", (p_a, p_b))
        conn.execute("DELETE FROM flujo_egresos WHERE periodo IN (?,?)", (p_a, p_b))
        conn.commit(); conn.close()


def test_mom_12_top_categoria_ultimo_mes(app, db_clean):
    """Stats incluye top_categoria_egreso del último período."""
    c = _login(app, "sebastian")
    r = c.get("/api/financiero/mom-12-meses")
    p_ult = r.get_json()["meses"][-1]["periodo"]

    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM flujo_egresos WHERE periodo=?", (p_ult,))
    # MPs es mayor que Nomina
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 7000000, 'MPs1', 'MPs')""", (p_ult,))
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 2000000, 'Nom1', 'Nomina')""", (p_ult,))
    conn.commit(); conn.close()
    try:
        r = c.get("/api/financiero/mom-12-meses")
        stats = r.get_json().get("stats", {})
        assert stats.get("top_categoria_egreso") == "MPs"
        assert stats.get("top_categoria_egreso_monto") == 7000000
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM flujo_egresos WHERE periodo=?", (p_ult,))
        conn.commit(); conn.close()


def test_mom_12_admin_y_contadora_acceden(app, db_clean):
    """Tanto admin como contadora pueden ver el endpoint."""
    for u in ("sebastian", "mayra"):
        c = _login(app, u)
        r = c.get("/api/financiero/mom-12-meses")
        assert r.status_code == 200, f"{u} no debería recibir {r.status_code}"


def test_financiero_page_incluye_mom_card(app, db_clean):
    """La página /financiero contiene el card de MoM 12 meses + handlers JS."""
    c = _login(app, "sebastian")
    r = c.get("/financiero")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    # Card visible
    assert "Tendencia 12 meses" in body
    assert 'id="chart-mom-12"' in body
    assert 'id="mom-12-stats"' in body
    assert 'id="mom-12-tbody"' in body
    # Handler JS
    assert "function loadMoM12" in body
    assert "/api/financiero/mom-12-meses" in body
    # Llamada desde loadDashboard
    assert "loadMoM12()" in body
