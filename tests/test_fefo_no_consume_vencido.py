"""INVIMA · defensa de vencimiento en el USO de producción (12-jun).

El cron job_marcar_vencidos corre 1x/día (7:50). Entre que un lote vence y
corre el cron, su estado_lote sigue 'VIGENTE'. El FEFO/verificar-stock NO deben
consumir ni prometer ese material vencido-por-fecha aunque el cron no lo haya
marcado todavía (mismo límite que el cron: fecha_venc < hoy Colombia). Sin
bloquear lotes con fecha hoy/futura ni sin fecha (NULL).
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


def _formula(prod, cod, nombre):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES (?,?,1)", (cod, nombre))
    _exec("INSERT OR REPLACE INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg) VALUES (?,1000,1)", (prod,))
    _exec("DELETE FROM formula_items WHERE producto_nombre=?", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES (?,?,?,10,100)", (prod, cod, nombre))


def test_fefo_no_consume_lote_vencido_aunque_vigente(app, db_clean):
    """Lote estado_lote='VIGENTE' pero fecha_venc pasada → FEFO no lo consume."""
    _formula('ZZ VENC', 'MP-VENC', 'Test Venc')
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote,fecha_vencimiento) "
          "VALUES ('MP-VENC','Test Venc',500,'Entrada','2024-01-01','L-VENC','VIGENTE','2024-06-01')")

    c = _login(app)
    r = c.post('/api/produccion', json={'producto': 'ZZ VENC', 'cantidad_kg': 1,
                                        'operador': 'sebastian', 'presentacion': 'x'},
               headers=csrf_headers())
    assert r.status_code in (200, 201, 422), r.data
    salidas = _q1("SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE material_id='MP-VENC' AND tipo='Salida'")
    assert salidas == 0, f"FEFO NO debe consumir un lote vencido por fecha · consumió {salidas}g"
    f = next((x for x in (r.get_json() or {}).get('faltantes', []) if x['material_id'] == 'MP-VENC'), None)
    assert f, "MP-VENC debe faltar (su único lote está vencido por fecha)"


def test_verificar_stock_reporta_vencido_como_faltante(app, db_clean):
    _formula('ZZ VENC2', 'MP-VENC2', 'Test Venc2')
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote,fecha_vencimiento) "
          "VALUES ('MP-VENC2','Test Venc2',500,'Entrada','2024-01-01','L-VENC2','VIGENTE','2024-06-01')")

    c = _login(app)
    r = c.post('/api/produccion/simular', json={'producto': 'ZZ VENC2', 'cantidad_kg': 1},
               headers=csrf_headers())
    assert r.status_code == 200, r.data
    d = r.get_json()
    items = d.get('ingredientes') or d.get('materiales') or d.get('resultado') or []
    it = next((x for x in items if x.get('material_id') == 'MP-VENC2'), None)
    assert it is not None, f"MP-VENC2 debe estar en el simulador · {d}"
    assert it.get('suficiente') is False, \
        f"Verificar Stock debe reportar INSUFICIENTE (lote vencido) · {it}"
    assert (it.get('g_disponible') or 0) == 0, f"g_disponible debe ser 0 · {it}"


def test_fefo_si_consume_lote_vigente_no_vencido(app, db_clean):
    """No bloquear de más: un lote con fecha FUTURA sí se consume."""
    _formula('ZZ OK', 'MP-OKV', 'Test OKV')
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote,fecha_vencimiento) "
          "VALUES ('MP-OKV','Test OKV',500,'Entrada','2026-01-01','L-OKV','VIGENTE','2099-12-31')")

    c = _login(app)
    r = c.post('/api/produccion', json={'producto': 'ZZ OK', 'cantidad_kg': 1,
                                        'operador': 'sebastian', 'presentacion': 'x'},
               headers=csrf_headers())
    assert r.status_code in (200, 201), r.data
    salidas = _q1("SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE material_id='MP-OKV' AND tipo='Salida'")
    assert abs(salidas - 100) < 0.5, f"debe consumir 100g del lote vigente no vencido · consumió {salidas}g"


def test_fefo_si_consume_lote_sin_fecha_vencimiento(app, db_clean):
    """Un lote sin fecha_venc (NULL) no se bloquea por la defensa de vencimiento."""
    _formula('ZZ NULLFV', 'MP-NFV', 'Test NFV')
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote,fecha_vencimiento) "
          "VALUES ('MP-NFV','Test NFV',500,'Entrada','2026-01-01','L-NFV','VIGENTE',NULL)")

    c = _login(app)
    r = c.post('/api/produccion', json={'producto': 'ZZ NULLFV', 'cantidad_kg': 1,
                                        'operador': 'sebastian', 'presentacion': 'x'},
               headers=csrf_headers())
    assert r.status_code in (200, 201), r.data
    salidas = _q1("SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE material_id='MP-NFV' AND tipo='Salida'")
    assert abs(salidas - 100) < 0.5, f"debe consumir 100g del lote sin fecha de venc · consumió {salidas}g"
