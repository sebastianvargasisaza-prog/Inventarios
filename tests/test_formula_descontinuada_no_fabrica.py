"""GMP/INVIMA · audit fórmulas 13-jun (hallazgo revisor adversarial): el descuento
al fabricar NO debe usar una fórmula DESCONTINUADA (formula_headers.activo=0). Antes
el SELECT de formula_items no filtraba por header activo → producir con el nombre exacto
de una fórmula descontinuada (caso 'Blush Balm' minúscula 67% vs 'BLUSH BALM' completa,
o las 6 que descontinuó mig 231) descontaba la fórmula vieja/incompleta.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app):
    c = app.test_client()
    c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def _q1(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        r = conn.execute(sql, params).fetchone(); return r[0] if r else None
    finally:
        conn.close()


def _formula(prod, cod, activo):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES (?,?,1)", (cod, 'Test ' + cod))
    _exec("INSERT OR REPLACE INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo) VALUES (?,1000,1,?)", (prod, activo))
    _exec("DELETE FROM formula_items WHERE producto_nombre=?", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES (?,?,?,10,100)", (prod, cod, 'Test ' + cod))
    # stock con lote vigente
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
          "VALUES (?,?,?,'Entrada','2026-01-01',?, 'VIGENTE')", (cod, 'Test ' + cod, 5000, 'L-' + cod))


def test_descontinuada_no_descuenta(app, db_clean):
    _formula('ZZ DESCONTINUADA', 'MP-DISC', activo=0)
    c = _login(app)
    r = c.post('/api/produccion', json={'producto': 'ZZ DESCONTINUADA', 'cantidad_kg': 1,
                                        'operador': 'sebastian', 'presentacion': 'x'},
               headers=csrf_headers())
    salidas = _q1("SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE material_id='MP-DISC' AND tipo='Salida'")
    assert salidas == 0, f"una fórmula DESCONTINUADA (activo=0) no debe descontar · descontó {salidas}g · resp {r.status_code}"


def test_activa_si_descuenta(app, db_clean):
    """No bloquear de más: la fórmula ACTIVA sí fabrica normal."""
    _formula('ZZ ACTIVA', 'MP-ACT', activo=1)
    c = _login(app)
    r = c.post('/api/produccion', json={'producto': 'ZZ ACTIVA', 'cantidad_kg': 1,
                                        'operador': 'sebastian', 'presentacion': 'x'},
               headers=csrf_headers())
    assert r.status_code in (200, 201), r.data[:200]
    salidas = _q1("SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE material_id='MP-ACT' AND tipo='Salida'")
    assert abs(salidas - 100) < 0.5, f"la fórmula activa debe descontar 100g · descontó {salidas}g"


def test_simular_descontinuada_rechaza(app, db_clean):
    _formula('ZZ DISC SIM', 'MP-DISCS', activo=0)
    c = _login(app)
    r = c.post('/api/produccion/simular', json={'producto': 'ZZ DISC SIM', 'cantidad_kg': 1},
               headers=csrf_headers())
    assert r.status_code == 404, f"simular una descontinuada debe dar 404 · fue {r.status_code} {r.data[:150]}"


def test_caso_blush_balm_case_dup(app, db_clean):
    """El caso real: nombre activo (uppercase completo) vs inactivo (titlecase incompleto)
    son strings distintos → el activo fabrica, el inactivo se rechaza, sin cruzarse."""
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MP-BBOK','BB ok',1)")
    # header inactivo (incompleto)
    _exec("INSERT OR REPLACE INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo) VALUES ('ZZ Bb',1000,1,0)")
    _exec("DELETE FROM formula_items WHERE producto_nombre='ZZ Bb'")
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) VALUES ('ZZ Bb','MP-BBOK','BB ok',5,50)")
    # header activo (completo) · MISMO material para simplificar, distinto %
    _exec("INSERT OR REPLACE INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo) VALUES ('ZZ BB',1000,1,1)")
    _exec("DELETE FROM formula_items WHERE producto_nombre='ZZ BB'")
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) VALUES ('ZZ BB','MP-BBOK','BB ok',10,100)")
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MP-BBOK','BB ok',5000,'Entrada','2026-01-01','L-BBOK','VIGENTE')")

    c = _login(app)
    # el inactivo NO descuenta
    c.post('/api/produccion', json={'producto': 'ZZ Bb', 'cantidad_kg': 1, 'operador': 'sebastian', 'presentacion': 'x'}, headers=csrf_headers())
    s_inact = _q1("SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE material_id='MP-BBOK' AND tipo='Salida'")
    assert s_inact == 0, f"el header inactivo 'ZZ Bb' no debe descontar · {s_inact}g"
    # el activo SÍ (100g, su %)
    r = c.post('/api/produccion', json={'producto': 'ZZ BB', 'cantidad_kg': 1, 'operador': 'sebastian', 'presentacion': 'x'}, headers=csrf_headers())
    assert r.status_code in (200, 201), r.data[:150]
    s_act = _q1("SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE material_id='MP-BBOK' AND tipo='Salida'")
    assert abs(s_act - 100) < 0.5, f"el header activo 'ZZ BB' debe descontar 100g · {s_act}g"
