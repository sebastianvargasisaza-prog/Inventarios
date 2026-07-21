"""Override de VENTA ESPERADA/mes (Sebastián 20-jul · mig 365): cuando la venta reciente de Shopify
NO refleja la venta normal (bache/estacionalidad), el usuario fija la venta que conoce y el motor de
velocidad la usa en LUGAR del blend, IGUAL en el display y el motor (paridad M70)."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_override_helper_uds_dia(app, db_clean):
    prod = "ZZ VESP PROD"
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        conn.execute("INSERT INTO sku_planeacion_config (producto_nombre, venta_esperada_mes) VALUES (?, 900)", (prod,))
        conn.commit()
    finally:
        conn.close()
    # el helper devuelve uds/DÍA = 900/30.44
    from blueprints.auto_plan import venta_esperada_override
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        v = venta_esperada_override(conn.cursor(), prod)
    finally:
        conn.close()
    assert v is not None
    assert abs(v - (900 / 30.44)) < 0.01, f"esperaba ~{900/30.44}/día, got {v}"

    # nombre distinto → None (no aplica)
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        assert venta_esperada_override(conn.cursor(), "OTRO PRODUCTO XYZ") is None
    finally:
        conn.close()


def test_override_cero_es_none(app, db_clean):
    prod = "ZZ VESP CERO"
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        conn.execute("INSERT INTO sku_planeacion_config (producto_nombre, venta_esperada_mes) VALUES (?, 0)", (prod,))
        conn.commit()
    finally:
        conn.close()
    from blueprints.auto_plan import venta_esperada_override
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        assert venta_esperada_override(conn.cursor(), prod) is None, "venta 0 = usa Shopify (None)"
    finally:
        conn.close()


def test_endpoint_fija_y_borra(app, db_clean):
    prod = "ZZ VESP ENDPOINT"
    c = _login(app, "sebastian")
    # fijar 900
    r = c.post("/api/programacion/decision-produccion",
               json={"producto": prod, "venta_esperada_mes": 900}, headers=csrf_headers())
    assert r.status_code == 200, r.get_data(as_text=True)
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        v = conn.execute("SELECT venta_esperada_mes FROM sku_planeacion_config WHERE producto_nombre=?", (prod,)).fetchone()
    finally:
        conn.close()
    assert v and abs(float(v[0]) - 900) < 0.01

    # borrar (0 → NULL → vuelve a Shopify)
    r = c.post("/api/programacion/decision-produccion",
               json={"producto": prod, "venta_esperada_mes": 0}, headers=csrf_headers())
    assert r.status_code == 200, r.get_data(as_text=True)
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        v = conn.execute("SELECT venta_esperada_mes FROM sku_planeacion_config WHERE producto_nombre=?", (prod,)).fetchone()
    finally:
        conn.close()
    assert v is not None and v[0] is None, "venta 0 debe guardar NULL (volver a Shopify)"
