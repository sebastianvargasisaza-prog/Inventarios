"""18-jun · Causa raíz del pedido ~130x inflado: el MISMO producto planificado por
VARIOS generadores (eos_plan manual + auto_plan del cron + eos_proyeccion) en fechas
distintas, todo SUMADO por el cálculo de compra. Fix prefer-Fijo: si un producto tiene
plan FIJO, se ignoran sus capas auto → no se suman planes solapados.
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
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def _lote(prod, dias, origen, kg=10):
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES (?, date('now','-5 hours','+' || ? || ' days'), 1, 'pendiente', ?, ?)",
          (prod, str(dias), kg, origen))


def test_planes_solapados_no_suman_sobre_el_fijo(app, db_clean):
    cod, prod = "MP-INFL1", "ZZ-INFL1"
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES (?, 'Mat Infl', 'INCI INFL1', 1)", (cod,))
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 10, 1)", (prod,))
    # 10% de 10kg = 1000 g por lote
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES (?, ?, 'Mat Infl', 10, 1000)", (prod, cod))
    # 1 lote FIJO (lo que el usuario deliberadamente planificó)
    _lote(prod, 10, 'eos_plan')
    # capas AUTO que se apilan en fechas distintas (cron + proyección) → NO deben sumar
    for d in (20, 30, 40):
        _lote(prod, d, 'auto_plan')
    for d in (25, 35, 45):
        _lote(prod, d, 'eos_proyeccion')

    c = _login(app)
    # PANTALLA (consumo-horizontes): debe contar SOLO el lote Fijo → consumo90 ≈ 1000g
    j = c.get("/api/abastecimiento/consumo-horizontes").get_json()
    hmax = str(max(j["horizontes"]))
    it = next((x for x in (j.get("mps") or []) if (x.get("codigo") or "").upper() == cod.upper()), None)
    assert it is not None, "la MP debe aparecer"
    cons90 = it["consumo"][hmax]
    assert 950 <= cons90 <= 1050, \
        f"debe contar SOLO el plan Fijo (~1000g), no los 7 lotes solapados (~7000g) · got {cons90}"

    # MOTOR DE COMPRA (mps-deficit): mismo criterio · déficit ~1000g (sin stock)
    r2 = c.get("/api/programacion/mps-deficit").get_json()
    d2 = next((float(x.get("deficit_g") or 0) for x in (r2.get("mps") or [])
               if (x.get("codigo_mp") or "").upper() == cod.upper()), 0.0)
    assert 950 <= d2 <= 1050, f"generar-OC también debe contar solo el Fijo (~1000g) · got {d2}"


def test_sin_fijo_conserva_sugeridas(app, db_clean):
    """Un producto SIN plan Fijo (solo sugeridas) NO se sub-cuenta: se cuentan sus
    sugeridas (deduplicadas por fecha)."""
    cod, prod = "MP-INFL2", "ZZ-INFL2"
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES (?, 'Mat Infl2', 'INCI INFL2', 1)", (cod,))
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 10, 1)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES (?, ?, 'Mat Infl2', 10, 1000)", (prod, cod))
    # solo sugeridas, fechas distintas → se cuentan (2 lotes = 2000g)
    _lote(prod, 15, 'auto_plan')
    _lote(prod, 45, 'sugerido')
    c = _login(app)
    j = c.get("/api/abastecimiento/consumo-horizontes").get_json()
    hmax = str(max(j["horizontes"]))
    it = next((x for x in (j.get("mps") or []) if (x.get("codigo") or "").upper() == cod.upper()), None)
    assert it is not None
    assert it["consumo"][hmax] >= 1900, f"sin Fijo, las sugeridas SÍ cuentan · got {it['consumo'][hmax]}"
