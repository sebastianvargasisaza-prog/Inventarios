"""P0 INVIMA (Sebastián 12-jun · hallazgo Fable 5): un lote RECHAZADO por Calidad
NO debe consumirse al fabricar ni por consumo manual, aunque su estado_lote esté
en otro case ('Rechazado' Title-case, que es lo que escribía aprobar-lote).
Antes el filtro NOT IN ('...','RECHAZADO') era case-sensitive -> se colaba.
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


def test_fefo_no_consume_rechazado_titlecase(app, db_clean):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MP-REJ','Test Rej',1)")
    _exec("INSERT OR REPLACE INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg) VALUES ('ZZ REJ',1000,1)")
    _exec("DELETE FROM formula_items WHERE producto_nombre='ZZ REJ'")
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES ('ZZ REJ','MP-REJ','Test Rej',10,100)")
    # Único stock = 500g RECHAZADO en Title-case (exactamente lo que escribía Calidad)
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
          "VALUES ('MP-REJ','Test Rej',500,'Entrada','2026-06-01','L-REJ','Rechazado')")

    c = _login(app)
    r = c.post('/api/produccion', json={'producto': 'ZZ REJ', 'cantidad_kg': 1,
                                        'operador': 'sebastian', 'presentacion': 'x'},
               headers=csrf_headers())
    assert r.status_code in (200, 201, 422), r.data
    salidas = _q1("SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE material_id='MP-REJ' AND tipo='Salida'")
    assert salidas == 0, f"FEFO NO debe consumir un lote Rechazado (case-insensitive) · consumió {salidas}g"
    d = r.get_json()
    f = next((x for x in d.get('faltantes', []) if x['material_id'] == 'MP-REJ'), None)
    assert f, f"MP-REJ debe faltar (su stock está rechazado) · {d}"


def test_consumo_manual_no_consume_rechazado_titlecase(app, db_clean):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MP-REJ2','Test Rej2',1)")
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
          "VALUES ('MP-REJ2','Test Rej2',500,'Entrada','2026-06-01','L-REJ2','Rechazado')")
    c = _login(app)
    r = c.post('/api/consumo-manual', json={'codigo_mp': 'MP-REJ2', 'cantidad': 100,
                                            'lote': 'L-REJ2', 'operador': 'sebastian'},
               headers=csrf_headers())
    assert r.status_code != 200 or not (r.get_json() or {}).get('ok'), \
        f"no debe descontar un lote Rechazado sin forzar · {r.status_code} {r.data}"
    salidas = _q1("SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE material_id='MP-REJ2' AND tipo='Salida'")
    assert salidas == 0, f"consumo manual NO debe consumir lote Rechazado · consumió {salidas}g"
