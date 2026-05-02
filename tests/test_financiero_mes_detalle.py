"""Tests del endpoint /api/financiero/mes-detalle (drill-down).

Verifica:
- RBAC: admin/contadora acceden, otros no
- Validaciones: periodo formato YYYY-MM · tipo válido
- Estructura: total + count + categorias (con count + pct + top_items)
- Cálculo correcto de pct y agrupación por categoría
- Top items ordenados por monto desc
- Sin categoria → 'Sin categoría' label
- UI page incluye modal + handler abrirMesDetalle
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


def test_mes_detalle_requires_auth(client, db_clean):
    r = client.get("/api/financiero/mes-detalle?periodo=2026-04&tipo=egresos")
    assert r.status_code == 401


def test_mes_detalle_user_no_finanzas_401(app, db_clean):
    c = _login(app, "luis")
    r = c.get("/api/financiero/mes-detalle?periodo=2026-04&tipo=egresos")
    assert r.status_code == 401


def test_mes_detalle_periodo_invalido_400(app, db_clean):
    c = _login(app, "sebastian")
    for periodo in ('', '2026', '2026/04', '202604', 'XX-YY'):
        r = c.get(f"/api/financiero/mes-detalle?periodo={periodo}&tipo=egresos")
        assert r.status_code == 400, f"periodo='{periodo}' debería ser 400"


def test_mes_detalle_tipo_invalido_400(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/financiero/mes-detalle?periodo=2026-04&tipo=foo")
    assert r.status_code == 400


def test_mes_detalle_estructura(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/financiero/mes-detalle?periodo=2026-04&tipo=egresos")
    assert r.status_code == 200
    d = r.get_json()
    assert d["periodo"] == "2026-04"
    assert d["tipo"] == "egresos"
    assert "total" in d
    assert "count" in d
    assert "categorias" in d
    assert isinstance(d["categorias"], list)


def test_mes_detalle_calcula_categorias_y_pct(app, db_clean):
    """Sembrar 3 egresos en 2 categorías y verificar pct/sort."""
    c = _login(app, "sebastian")
    p = '2026-95'  # período test exclusivo
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM flujo_egresos WHERE periodo=?", (p,))
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 6000000, 'MP1 grande', 'MPs')""", (p,))
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 2000000, 'MP2 mediano', 'MPs')""", (p,))
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 2000000, 'Salario abril', 'Nomina')""", (p,))
    conn.commit(); conn.close()
    try:
        r = c.get(f"/api/financiero/mes-detalle?periodo={p}&tipo=egresos")
        d = r.get_json()
        assert d["total"] == 10000000
        assert d["count"] == 3
        # Sorted by monto desc → MPs primero
        assert d["categorias"][0]["categoria"] == "MPs"
        assert d["categorias"][0]["monto"] == 8000000
        assert d["categorias"][0]["count"] == 2
        assert d["categorias"][0]["pct"] == 80.0
        assert d["categorias"][1]["categoria"] == "Nomina"
        assert d["categorias"][1]["pct"] == 20.0
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM flujo_egresos WHERE periodo=?", (p,))
        conn.commit(); conn.close()


def test_mes_detalle_top_items_ordenados(app, db_clean):
    """Top 5 items dentro de una categoría ordenados por monto desc."""
    c = _login(app, "sebastian")
    p = '2026-94'
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM flujo_egresos WHERE periodo=?", (p,))
    # Sembrar 6 items para verificar que solo trae top 5
    for i, monto in enumerate([1000000, 5000000, 3000000, 2000000, 4000000, 500000]):
        conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria, referencia)
                        VALUES (date('now'), ?, ?, ?, 'MPs', ?)""",
                     (p, monto, f'item-{i}', f'OC-2026-{i:04d}'))
    conn.commit(); conn.close()
    try:
        r = c.get(f"/api/financiero/mes-detalle?periodo={p}&tipo=egresos")
        d = r.get_json()
        cat = d["categorias"][0]
        assert cat["count"] == 6  # total real
        assert len(cat["top_items"]) == 5  # solo top 5
        # Ordenados desc
        montos = [it["monto"] for it in cat["top_items"]]
        assert montos == sorted(montos, reverse=True)
        assert montos[0] == 5000000
        # Referencia preservada
        assert cat["top_items"][0]["referencia"].startswith("OC-2026-")
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM flujo_egresos WHERE periodo=?", (p,))
        conn.commit(); conn.close()


def test_mes_detalle_sin_categoria_label(app, db_clean):
    """Items sin categoría caen bajo 'Sin categoría'."""
    c = _login(app, "sebastian")
    p = '2026-93'
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM flujo_egresos WHERE periodo=?", (p,))
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 1000000, 'sin cat', '')""", (p,))
    conn.execute("""INSERT INTO flujo_egresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 500000, 'sin cat 2', NULL)""", (p,))
    conn.commit(); conn.close()
    try:
        r = c.get(f"/api/financiero/mes-detalle?periodo={p}&tipo=egresos")
        d = r.get_json()
        cats = [c["categoria"] for c in d["categorias"]]
        assert "Sin categoría" in cats
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM flujo_egresos WHERE periodo=?", (p,))
        conn.commit(); conn.close()


def test_mes_detalle_ingresos_funciona(app, db_clean):
    c = _login(app, "sebastian")
    p = '2026-92'
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM flujo_ingresos WHERE periodo=?", (p,))
    conn.execute("""INSERT INTO flujo_ingresos (fecha, periodo, monto, concepto, categoria)
                    VALUES (date('now'), ?, 5000000, 'Cobro factura X', 'Cobranza B2B')""", (p,))
    conn.commit(); conn.close()
    try:
        r = c.get(f"/api/financiero/mes-detalle?periodo={p}&tipo=ingresos")
        d = r.get_json()
        assert d["tipo"] == "ingresos"
        assert d["total"] == 5000000
        assert len(d["categorias"]) == 1
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM flujo_ingresos WHERE periodo=?", (p,))
        conn.commit(); conn.close()


def test_mes_detalle_mes_vacio_devuelve_estructura_vacia(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/financiero/mes-detalle?periodo=1999-01&tipo=egresos")
    assert r.status_code == 200
    d = r.get_json()
    assert d["total"] == 0
    assert d["count"] == 0
    assert d["categorias"] == []


def test_financiero_page_incluye_modal_drill_down(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/financiero")
    body = r.get_data(as_text=True)
    assert 'id="mes-detalle-modal"' in body
    assert 'function abrirMesDetalle' in body
    assert 'function cerrarMesDetalle' in body
    # Las celdas del MoM table tienen onclick wired (vía clickIng/clickEgr)
    assert "clickIng" in body and "clickEgr" in body
    assert 'abrirMesDetalle("' in body  # función llamada con doble comillas
