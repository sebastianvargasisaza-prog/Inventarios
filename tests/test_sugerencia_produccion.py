"""Programación v4 · Fase B paso 1 · panel de sugerencia (SOLO LECTURA).

Verifica /api/programacion/sugerencia-produccion:
  - horizontes 1/2/3 meses en kg (blend × días × ml ÷ 1000; mes_2≈2×mes_1)
  - guardrails ½×–2× del promedio 90d ("ni menos ni exagerar")
  - recordá: kg producidos el mes pasado (historial que ya existe)
  - NO escribe nada (idempotente entre llamadas)
"""
import os
import sqlite3
from datetime import date, timedelta

from .conftest import TEST_PASSWORD, csrf_headers

PROD = "QA SUERO SUGERENCIA"
SKU = "QA-SUG-30"


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


def _seed():
    # idempotente: la suite comparte DB (PG) y cada test re-siembra
    for sql, p in (
        ("DELETE FROM ventas_diarias WHERE sku=?", (SKU,)),
        ("DELETE FROM produccion_programada WHERE producto=?", (PROD,)),
    ):
        _exec(sql, p)
    # fórmula establecida (fecha vieja → divisor 30/60/90, sin ajuste de edad)
    _exec("INSERT OR IGNORE INTO formula_headers (producto_nombre, lote_size_kg, activo, fecha_creacion) "
          "VALUES (?, 30, 1, '2024-01-01')", (PROD,))
    _exec("INSERT OR IGNORE INTO sku_producto_map (sku, producto_nombre, activo, es_regalo) "
          "VALUES (?, ?, 1, 0)", (SKU, PROD))
    # 10 uds/día los últimos 90 días → v30=300, v60=600, v90=900 → estable → 10 uds/día
    hoy = date.today()
    for d in range(1, 90):
        _exec("INSERT INTO ventas_diarias (sku, fecha, cantidad) VALUES (?, ?, 10)",
              (SKU, (hoy - timedelta(days=d)).isoformat()))
    # historial: lote de 30 kg en el calendario el mes pasado · NO marcado 'completado'
    # (como el caso real del 25-jun: está en el calendario y ES la verdad de lo producido)
    fin_mes_pasado = (hoy.replace(day=1) - timedelta(days=1)).isoformat()
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, "
          "lotes, estado, cantidad_kg, origen) "
          "VALUES (?, ?, 1, 'programado', 30, 'eos_plan')",
          (PROD, fin_mes_pasado))


def test_sugerencia_estructura_y_horizontes(app):
    _seed()
    c = _login(app)
    r = c.get(f"/api/programacion/sugerencia-produccion?producto={PROD}")
    assert r.status_code == 200, r.data
    j = r.get_json()

    # venta blended ~10 uds/día
    assert abs(j["venta"]["vel_uds_dia"] - 10) < 1.5, j["venta"]
    assert j["venta"]["tendencia"] in ("estable", "sin_historico",
                                       "caida_moderada", "aceleracion_moderada")

    # horizontes: kg = 10 uds/día × días × 30ml ÷ 1000 · mes_2 ≈ 2× mes_1
    h = j["horizontes"]
    assert h["mes_1"]["kg"] > 0
    assert abs(h["mes_2"]["kg"] - 2 * h["mes_1"]["kg"]) < 0.5, h
    assert abs(h["mes_3"]["kg"] - 3 * h["mes_1"]["kg"]) < 0.5, h
    # ~9 kg/mes (10×30×30/1000)
    assert 7 <= h["mes_1"]["kg"] <= 11, h["mes_1"]

    # guardrails: piso ½ y techo 2× del 90d, con la velocidad adentro
    g = j["guardrails"]
    assert g["piso_uds_dia"] <= g["vel_uds_dia"] <= g["techo_uds_dia"], g

    # recordá: 30 kg el mes pasado
    assert j["recorda"]["kg_mes_pasado"] == 30, j["recorda"]
    assert j["recorda"]["lotes_mes_pasado"] == 1, j["recorda"]
    # historial revisable: el lote aparece con fecha + kg + fuente
    hist = j["recorda"]["historial"]
    assert len(hist) >= 1 and hist[0]["kg"] == 30, hist
    assert hist[0]["fuente"] in ("calendario", "fabricacion", "ambos"), hist[0]


def test_solo_lectura_no_muta(app):
    _seed()
    c = _login(app)

    def _snap():
        conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
        try:
            return conn.execute(
                "SELECT COUNT(*) FROM produccion_programada WHERE producto=?", (PROD,)
            ).fetchone()[0]
        finally:
            conn.close()

    antes = _snap()
    for _ in range(3):
        assert c.get(f"/api/programacion/sugerencia-produccion?producto={PROD}").status_code == 200
    assert _snap() == antes  # nada creado/cancelado


def test_recorda_cuenta_fabricacion_directa(app):
    # producto SOLO con lote en la tabla producciones (Fabricación), sin fila en el
    # calendario → recordá igual lo recuerda (empezaron a usar Fabricación hace poco)
    prod = "QA FAB DIRECTA"
    _exec("DELETE FROM producciones WHERE producto=?", (prod,))
    _exec("INSERT OR IGNORE INTO formula_headers (producto_nombre, lote_size_kg, activo) "
          "VALUES (?, 20, 1)", (prod,))
    fin_mes_pasado = (date.today().replace(day=1) - timedelta(days=1)).isoformat()
    _exec("INSERT INTO producciones (producto, cantidad, fecha, operador) "
          "VALUES (?, 20, ?, 'op')", (prod, fin_mes_pasado + " 10:00:00"))
    c = _login(app)
    j = c.get(f"/api/programacion/sugerencia-produccion?producto={prod}").get_json()
    assert j["recorda"]["kg_mes_pasado"] == 20, j["recorda"]


def test_no_doble_cuenta_calendario_y_fabricacion(app):
    # mismo lote reflejado en AMBAS tablas el mismo día → cuenta UNA vez (dedup por día)
    prod = "QA DEDUP DIA"
    dia = (date.today().replace(day=1) - timedelta(days=1)).isoformat()
    _exec("DELETE FROM producciones WHERE producto=?", (prod,))
    _exec("DELETE FROM produccion_programada WHERE producto=?", (prod,))
    _exec("INSERT OR IGNORE INTO formula_headers (producto_nombre, lote_size_kg, activo) "
          "VALUES (?, 25, 1)", (prod,))
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, fin_real_at, "
          "lotes, estado, cantidad_kg, kg_real, origen) "
          "VALUES (?, ?, ?, 1, 'completado', 25, 25, 'eos_retroactivo')", (prod, dia, dia))
    _exec("INSERT INTO producciones (producto, cantidad, fecha, operador) "
          "VALUES (?, 25, ?, 'op')", (prod, dia + " 10:00:00"))
    c = _login(app)
    j = c.get(f"/api/programacion/sugerencia-produccion?producto={prod}").get_json()
    assert j["recorda"]["kg_mes_pasado"] == 25, j["recorda"]  # NO 50


def test_confrontar_calendario_vs_productos(app):
    _seed()  # PROD tiene fórmula + lote en el calendario (mes pasado)
    # producto con fórmula pero SIN producción
    sin_prod = "QA SIN PRODUCCION"
    _exec("INSERT OR IGNORE INTO formula_headers (producto_nombre, lote_size_kg, activo) "
          "VALUES (?, 10, 1)", (sin_prod,))
    # HUÉRFANO: lote en el calendario cuyo nombre NO cruza con ninguna fórmula
    huerfano = "QA HUERFANO SIN FORMULA XYZ"
    dia = (date.today().replace(day=1) - timedelta(days=1)).isoformat()
    _exec("DELETE FROM produccion_programada WHERE producto=?", (huerfano,))
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, "
          "cantidad_kg, origen) VALUES (?, ?, 1, 'programado', 12, 'eos_plan')", (huerfano, dia))

    c = _login(app)
    j = c.get("/api/programacion/confrontar-calendario-productos").get_json()

    prods = {p["producto"]: p for p in j["productos"]}
    assert prods[PROD]["tiene_produccion"] is True, prods[PROD]
    assert prods[sin_prod]["tiene_produccion"] is False, prods.get(sin_prod)

    huerf = {h["producto"]: h for h in j["huerfanos"]}
    assert huerfano in huerf, j["huerfanos"]
    assert huerf[huerfano]["kg"] == 12, huerf[huerfano]

    assert j["resumen"]["huerfanos"] >= 1
    assert j["resumen"]["con_produccion"] >= 1
    assert j["resumen"]["sin_produccion"] >= 1


def test_decision_produccion_guarda_y_lee(app):
    _seed()
    c = _login(app)
    # guardar decisión: cada 2 meses (60d), 30 kg, horizonte 3 años, mix crece
    r = c.post("/api/programacion/decision-produccion",
               json={"producto": PROD, "cadencia_dias": 60, "kg_objetivo_lote": 30,
                     "horizonte_dias": 1095, "mix_mode": "crece"})
    assert r.status_code == 200, r.data
    cfg = r.get_json()["config"]
    assert cfg["cadencia_dias"] == 60 and cfg["kg_objetivo_lote"] == 30
    assert cfg["horizonte_dias"] == 1095 and cfg["mix_mode"] == "crece"
    # la sugerencia ahora la refleja
    j = c.get(f"/api/programacion/sugerencia-produccion?producto={PROD}").get_json()
    assert j["config"]["cadencia_dias"] == 60, j["config"]
    assert j["config"]["kg_objetivo_lote"] == 30
    assert j["config"]["mix_mode"] == "crece"


def test_decision_patch_parcial_no_pisa(app):
    _seed()
    c = _login(app)
    c.post("/api/programacion/decision-produccion",
           json={"producto": PROD, "cadencia_dias": 60, "kg_objetivo_lote": 30})
    # patch solo mix_mode → no borra cadencia ni kg
    c.post("/api/programacion/decision-produccion", json={"producto": PROD, "mix_mode": "fijo"})
    j = c.get(f"/api/programacion/sugerencia-produccion?producto={PROD}").get_json()["config"]
    assert j["mix_mode"] == "fijo" and j["cadencia_dias"] == 60 and j["kg_objetivo_lote"] == 30, j


def test_decision_valida_mix_mode(app):
    _seed()
    c = _login(app)
    r = c.post("/api/programacion/decision-produccion",
               json={"producto": PROD, "mix_mode": "invalido"})
    assert r.status_code == 400


def test_panel_programar_page_200(app):
    _seed()
    c = _login(app)
    r = c.get("/planta/programar")
    assert r.status_code == 200, r.status_code
    html = r.data.decode("utf-8", "replace")
    assert "Panel de programaci" in html
    assert "sugerencia-produccion" in html  # el panel llama al endpoint
    assert PROD in html                       # el producto está en el dropdown embebido


def test_falta_producto_400(app):
    c = _login(app)
    assert c.get("/api/programacion/sugerencia-produccion").status_code == 400
