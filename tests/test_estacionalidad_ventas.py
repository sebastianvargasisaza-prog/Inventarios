"""Sebastián 11-jul · Fase 1a forecast · "ver las ventas por mes para prepararnos antes de Black Friday".
Motor de estacionalidad POR PRODUCTO: del histórico Shopify saca la curva de uds por mes calendario + índice
(mes/promedio) + marca los picos. Este test siembra 2 años con un pico REAL en noviembre y verifica que el
motor lo detecta (índice nov el mayor + nov en picos), y que un producto con poco histórico cae al global."""
import os
import sqlite3
import json
import pytest
from .conftest import TEST_PASSWORD, csrf_headers


@pytest.fixture(autouse=True)
def _clear_estac_cache():
    # el cache de estacionalidad es module-level (TTL 10min per-worker en prod) · en tests hay que limpiarlo
    # entre casos para no servir datos de otro test (aislamiento).
    from blueprints import plan as _p
    _p._ESTAC_CACHE.clear()
    yield
    _p._ESTAC_CACHE.clear()


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


def test_preparacion_pico_sugiere_agrandar_lote(app, db_clean):
    """Fase 1b: un producto con pico estacional ~2 meses adelante y un lote CHICO antes del pico → la sugerencia
    'Preparar pico' propone agrandar ese lote. Prueba la función de enriquecimiento directo (sin el endpoint pesado)."""
    import datetime as _dt
    from blueprints import plan as _plan
    _plan._ESTAC_CACHE.clear()   # el cache es module-level · limpiarlo para ver los datos recién sembrados
    prod, sku = "QA PICO PREP", "QAPICOPREP"
    hoy = (_dt.datetime.utcnow() - _dt.timedelta(hours=5)).date()
    # mes pico = 2 meses adelante (robusto a la fecha de corrida)
    pk = ((hoy.month - 1 + 2) % 12) + 1
    _exec("INSERT INTO sku_producto_map (sku,producto_nombre,volumen_ml,activo) VALUES (?,?,30,1)", (sku, prod))
    # 2 años de historia con el mes pico a 3× (60 uds) vs 20 el resto
    for anio in (hoy.year - 2, hoy.year - 1):
        for mes in range(1, 13):
            q = 60 if mes == pk else 20
            _exec("INSERT INTO animus_shopify_orders (shopify_id,nombre,total,moneda,estado,estado_pago,sku_items,"
                  "unidades_total,creado_en) VALUES (?,?,?,?,?,?,?,?,?)",
                  (f"PP-{anio}-{mes}", "c", 100.0, "COP", "", "paid",
                   json.dumps([{"sku": sku, "qty": q}]), q, "%04d-%02d-15T10:00:00" % (anio, mes)))
    # un lote CHICO (20 kg) ~25 días adelante (antes del pico a ~2 meses)
    lote_fecha = (hoy + _dt.timedelta(days=25)).isoformat()
    import sqlite3
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    productos = [{"producto_nombre": prod, "planificacion": [
        {"id": 4242, "fecha": lote_fecha, "kg": 20.0, "estado": "pendiente"}]}]
    _plan._enriquecer_preparacion_picos(conn, productos)
    conn.close()
    pp = productos[0].get("preparacion_pico")
    assert pp is not None, ("debería sugerir preparación pre-pico", productos[0])
    assert pp["tipo"] == "agrandar", pp
    assert pp["lote_id"] == 4242, pp
    assert pp["kg_sugerido"] > pp["kg_actual"] >= 20.0, ("debe sugerir MÁS kg que el actual", pp)
    assert pp["pico_mes"] == pk, pp


def test_acelerador_config_y_en_abastecimiento(app, db_clean):
    """El acelerador se guarda (activo + colchones) y viaja en la respuesta de Abastecimiento para que el
    frontend calcule el buffer visible sobre 'Pedir'."""
    c = _login(app)
    # guardar config
    r = c.post("/api/plan/acelerador-config",
               json={"activo": True, "crecimiento_tope": 40, "colchon_local": 8, "colchon_import": 22, "lead_umbral": 25},
               headers=csrf_headers())
    assert r.status_code == 200, r.data
    cfg = r.get_json()["config"]
    assert cfg["activo"] is True and cfg["colchon_import"] == 22 and cfg["lead_umbral"] == 25, cfg
    # GET refleja lo guardado
    g = c.get("/api/plan/acelerador-config").get_json()["config"]
    assert g["activo"] is True and g["colchon_local"] == 8, g
    # viaja en Abastecimiento
    r2 = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp")
    assert r2.status_code == 200, r2.data
    ac = r2.get_json().get("acelerador")
    assert ac is not None and ac["activo"] is True and ac["colchon_import"] == 22, ac
    # clamp de seguridad: valores absurdos se acotan
    r3 = c.post("/api/plan/acelerador-config", json={"crecimiento_tope": 999, "colchon_import": -5},
                headers=csrf_headers())
    cfg3 = r3.get_json()["config"]
    assert cfg3["crecimiento_tope"] <= 200 and cfg3["colchon_import"] >= 0, cfg3
