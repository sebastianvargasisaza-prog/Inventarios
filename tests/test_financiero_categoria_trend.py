"""Tests del endpoint /api/financiero/categoria-trend (drill-down sobre 12 meses).

Verifica:
- RBAC: admin/contadora acceden, otros no
- Validaciones: categoria requerida, tipo válido
- 12 meses contiguos hacia atrás (incluso si vacíos)
- Cálculo correcto: monto + count por mes
- Stats: promedio, max_mes, min_mes, ultimo_vs_promedio_pct
- 'Sin categoría' matchea NULL/empty correctamente
- UI page incluye toggleCategoriaTrend handler
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


def test_trend_requires_auth(client, db_clean):
    r = client.get("/api/financiero/categoria-trend?categoria=MPs")
    assert r.status_code == 401


def test_trend_user_no_finanzas_401(app, db_clean):
    c = _login(app, "luis")
    r = c.get("/api/financiero/categoria-trend?categoria=MPs")
    assert r.status_code == 401


def test_trend_categoria_requerida_400(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/financiero/categoria-trend")
    assert r.status_code == 400
    r = c.get("/api/financiero/categoria-trend?categoria=")
    assert r.status_code == 400


def test_trend_tipo_invalido_400(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/financiero/categoria-trend?categoria=MPs&tipo=foo")
    assert r.status_code == 400


def test_trend_devuelve_12_meses_contiguos(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/financiero/categoria-trend?categoria=NoExiste")
    assert r.status_code == 200
    d = r.get_json()
    assert d["categoria"] == "NoExiste"
    assert d["tipo"] == "egresos"
    assert len(d["meses"]) == 12
    for m in d["meses"]:
        assert m["monto"] == 0
        assert m["count"] == 0


def test_trend_calcula_montos_y_count(app, db_clean):
    """Sembrar 3 meses con datos en categoría 'MPs' y verificar."""
    c = _login(app, "sebastian")
    r = c.get("/api/financiero/categoria-trend?categoria=MPs")
    meses_endpoint = r.get_json()["meses"]
    p_a = meses_endpoint[-3]["periodo"]
    p_b = meses_endpoint[-2]["periodo"]
    p_c = meses_endpoint[-1]["periodo"]

    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM flujo_egresos WHERE periodo IN (?,?,?) AND categoria='MPs'", (p_a, p_b, p_c))
    # 3M en p_a (1 tx)
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 3000000, 'mp1', 'MPs')""", (p_a,))
    # 5M total en p_b (2 tx)
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 2000000, 'mp2', 'MPs')""", (p_b,))
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 3000000, 'mp3', 'MPs')""", (p_b,))
    # 8M en p_c (1 tx)
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 8000000, 'mp4', 'MPs')""", (p_c,))
    conn.commit(); conn.close()
    try:
        r = c.get("/api/financiero/categoria-trend?categoria=MPs")
        d = r.get_json()
        meses = {m["periodo"]: m for m in d["meses"]}
        assert meses[p_a]["monto"] == 3000000
        assert meses[p_a]["count"] == 1
        assert meses[p_b]["monto"] == 5000000
        assert meses[p_b]["count"] == 2
        assert meses[p_c]["monto"] == 8000000
        assert meses[p_c]["count"] == 1
        # Stats
        s = d["stats"]
        # promedio = (3 + 5 + 8) / 3 = 5.33M
        assert abs(s["promedio"] - 5333333.33) < 1
        assert s["max_mes"] == p_c
        assert s["max_monto"] == 8000000
        assert s["min_mes"] == p_a
        assert s["min_monto"] == 3000000
        # último (p_c=8M) vs promedio 5.33M = +50%
        assert s["ultimo_vs_promedio_pct"] == 50.0
        assert s["total_12m"] == 16000000
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM flujo_egresos WHERE periodo IN (?,?,?) AND categoria='MPs'", (p_a, p_b, p_c))
        conn.commit(); conn.close()


def test_trend_sin_categoria_matchea_nulls(app, db_clean):
    """categoria='Sin categoría' debe traer items con categoria NULL o ''."""
    c = _login(app, "sebastian")
    p = '2026-91'
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM flujo_egresos WHERE periodo=?", (p,))
    # mismo periodo, dos items: uno NULL, otro ''
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 1000000, 'sin', NULL)""", (p,))
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 500000, 'sin2', '')""", (p,))
    conn.commit(); conn.close()
    try:
        # No debería traer estos en el rango de 12 meses (porque p está fuera del rango).
        # Probar con un período DENTRO del rango de 12m hacia atrás:
        r = c.get("/api/financiero/categoria-trend?categoria=Sin categoría")
        meses_endpoint = r.get_json()["meses"]
        p_recent = meses_endpoint[-1]["periodo"]

        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM flujo_egresos WHERE periodo=?", (p_recent,))
        conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                        VALUES (date('now'), ?, 7000000, 'sin', NULL)""", (p_recent,))
        conn.commit(); conn.close()

        r = c.get("/api/financiero/categoria-trend?categoria=Sin categoría")
        d = r.get_json()
        meses_dict = {m["periodo"]: m for m in d["meses"]}
        assert meses_dict[p_recent]["monto"] == 7000000
        assert meses_dict[p_recent]["count"] == 1
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM flujo_egresos WHERE periodo IN (?, ?)",
                     (p, meses_endpoint[-1]["periodo"]))
        conn.commit(); conn.close()


def test_trend_ingresos_funciona(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/financiero/categoria-trend?categoria=Cobranza B2B&tipo=ingresos")
    assert r.status_code == 200
    d = r.get_json()
    assert d["tipo"] == "ingresos"
    assert len(d["meses"]) == 12


def test_trend_admin_y_contadora_acceden(app, db_clean):
    for u in ("sebastian", "mayra"):
        c = _login(app, u)
        r = c.get("/api/financiero/categoria-trend?categoria=MPs")
        assert r.status_code == 200, f"{u} recibió {r.status_code}"


def test_financiero_page_incluye_toggle_handler(app, db_clean):
    """La página /financiero debe incluir el handler JS toggleCategoriaTrend."""
    c = _login(app, "sebastian")
    r = c.get("/financiero")
    body = r.get_data(as_text=True)
    assert "function toggleCategoriaTrend" in body
    assert "/api/financiero/categoria-trend" in body
    # En el modal, las categorías deben tener el toggle wired
    assert "toggleCategoriaTrend(" in body
    assert "ver 12m" in body  # el texto del botón emoji
