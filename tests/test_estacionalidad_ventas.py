"""Sebastián 11-jul · Fase 1a forecast · "ver las ventas por mes para prepararnos antes de Black Friday".
Motor de estacionalidad POR PRODUCTO: del histórico Shopify saca la curva de uds por mes calendario + índice
(mes/promedio) + marca los picos. Este test siembra 2 años con un pico REAL en noviembre y verifica que el
motor lo detecta (índice nov el mayor + nov en picos), y que un producto con poco histórico cae al global."""
import os
import sqlite3
import json
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


def _orden(sid, sku, qty, fecha_iso):
    _exec("INSERT INTO animus_shopify_orders (shopify_id,nombre,total,moneda,estado,estado_pago,sku_items,"
          "unidades_total,creado_en) VALUES (?,?,?,?,?,?,?,?,?)",
          (sid, "c", 1000.0, "COP", "", "paid", json.dumps([{"sku": sku, "qty": qty}]), qty, fecha_iso))


def test_estacionalidad_detecta_pico_noviembre(app, db_clean):
    prod, sku = "QA ESTAC PROD", "QAESTACSKU"
    _exec("INSERT INTO sku_producto_map (sku,producto_nombre,volumen_ml,activo) VALUES (?,?,30,1)", (sku, prod))
    # 2 años de historia: ~20 uds/mes normal, pico de ~80 en noviembre (Black Friday) los dos años
    for anio in (2024, 2025):
        for mes in range(1, 13):
            qty = 80 if mes == 11 else 20
            _orden(f"E-{anio}-{mes}", sku, qty, "%04d-%02d-15T10:00:00" % (anio, mes))

    c = _login(app)
    r = c.get("/api/plan/estacionalidad-ventas?meses=30&umbral=1.3")
    assert r.status_code == 200, r.data
    d = r.get_json()
    p = next((x for x in d["productos"] if x["producto"] == prod), None)
    assert p is not None, ("producto no apareció", [x["producto"] for x in d["productos"]])
    # noviembre (índice) debe ser el mes pico y estar en 'picos'
    ind = p["indice"]
    assert p["pico_max_mes"] == 11, ("el pico debe ser noviembre", p["pico_max_mes"], ind)
    assert 11 in p["picos"], ("noviembre en picos", p["picos"], ind)
    # el índice de nov ~ 80/promedio(~25) ≈ 3.2 · claramente > 1.3; enero (20) ~ 0.8
    assert ind[10] > 2.0, ("nov índice alto", ind)
    assert ind[0] < 1.2, ("enero índice normal/bajo", ind)
    assert p["meses_con_dato"] == 12 and not p["usa_global"], p


def test_producto_poco_historico_usa_global(app, db_clean):
    prod, sku = "QA ESTAC POCO", "QAESTACPOCO"
    _exec("INSERT INTO sku_producto_map (sku,producto_nombre,volumen_ml,activo) VALUES (?,?,30,1)", (sku, prod))
    # solo 3 meses de dato → < 6 → usa_global
    for mes in (9, 10, 11):
        _orden(f"P-{mes}", sku, 10, "2025-%02d-10T10:00:00" % mes)
    c = _login(app)
    r = c.get("/api/plan/estacionalidad-ventas?meses=30")
    assert r.status_code == 200, r.data
    p = next((x for x in r.get_json()["productos"] if x["producto"] == prod), None)
    assert p is not None
    assert p["usa_global"] is True and p["meses_con_dato"] < 6, p


def test_crecimiento_yoy_tienda(app, db_clean):
    """Crecimiento YoY: últimos 12m vs 12m previos. Producto que dobló sus ventas → ~+100%."""
    prod, sku = "QA CREC PROD", "QACRECSKU"
    _exec("INSERT INTO sku_producto_map (sku,producto_nombre,volumen_ml,activo) VALUES (?,?,30,1)", (sku, prod))
    # últimos 12 meses: 20 uds/mes · 12 meses previos: 10 uds/mes → +100%
    for i in range(12):
        _exec("INSERT INTO animus_shopify_orders (shopify_id,nombre,total,moneda,estado,estado_pago,sku_items,"
              "unidades_total,creado_en) VALUES (?,?,?,?,?,?,?,?, date('now','-5 hours','-' || ? || ' months'))",
              (f"CR-L{i}", "c", 100.0, "COP", "", "paid", json.dumps([{"sku": sku, "qty": 20}]), 20, i))
    for i in range(12, 24):
        _exec("INSERT INTO animus_shopify_orders (shopify_id,nombre,total,moneda,estado,estado_pago,sku_items,"
              "unidades_total,creado_en) VALUES (?,?,?,?,?,?,?,?, date('now','-5 hours','-' || ? || ' months'))",
              (f"CR-P{i}", "c", 100.0, "COP", "", "paid", json.dumps([{"sku": sku, "qty": 10}]), 10, i))
    c = _login(app)
    d = c.get("/api/plan/estacionalidad-ventas?meses=36").get_json()
    p = next((x for x in d["productos"] if x["producto"] == prod), None)
    assert p is not None, "producto no apareció"
    cr = p["crecimiento"]
    assert cr["disponible"] is True, cr
    assert 70 <= cr["yoy_pct"] <= 130, ("dobló ventas → ~+100% YoY", cr)  # tolerancia por bordes de mes
    assert d["global"]["crecimiento"]["yoy_pct"] is not None
