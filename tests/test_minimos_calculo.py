"""Cálculo de MÍNIMOS (punto de reorden) desde el plan + lead time · Sebastián 12-jul.

MÍN = (consumo_plan_Nd / N) × lead_time × (1 + colchón%).  MÍN = 0 si el plan no consume la MP.
Incluye test de PARIDAD: el consumo que usa el recalculador == el del motor de abastecimiento
verificado (para MPs directas sin bridge), garantizando cero divergencia (M1/M16).
"""
import os
import sqlite3
from .conftest import csrf_headers, TEST_PASSWORD


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def _login(app, user='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _seed_plan():
    # idempotente (db_clean no resetea formula_headers/items/produccion_programada)
    _exec("DELETE FROM formula_items WHERE producto_nombre='PROD MIN QA'")
    _exec("DELETE FROM formula_headers WHERE producto_nombre='PROD MIN QA'")
    _exec("DELETE FROM produccion_programada WHERE producto='PROD MIN QA'")
    for cod, inci in [('MPMINQA', 'MINQA UNIQUE INCI'), ('MPMINQB', 'MINQB UNIQUE INCI'),
                      ('MPMINNOPLAN', 'NOPLAN UNIQUE INCI')]:
        _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, "
              "controla_stock, activo, stock_minimo, min_auto) VALUES (?,?,?,1,1,500,1)", (cod, cod, inci))
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('PROD MIN QA', 30, 1)")
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES ('PROD MIN QA','MPMINQA','MinQA', 10, 0)")
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES ('PROD MIN QA','MPMINQB','MinQB', 2, 0)")
    # Programada Fijo dentro del horizonte (Colombia-anclada, +10 días)
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen, inventario_descontado_at) "
          "VALUES ('PROD MIN QA', date('now','-5 hours','+10 days'), 1, 'pendiente', 30, 'eos_plan', '')")


def test_min_calculo_desde_plan(app, db_clean):
    _seed_plan()
    c = _login(app)
    r = c.get('/api/inventario/recalcular-minimos?dias=90&colchon_pct=30&lead_default=30')
    assert r.status_code == 200, r.data
    filas = {f['codigo']: f for f in r.get_json()['filas']}
    a = filas['MPMINQA']
    assert abs(a['consumo_plan_g'] - 3000) < 0.5, a         # 10% × 30kg × 1000
    assert a['min_sugerido'] == 1300, a                     # (3000/90)×30×1.3 = 1300
    b = filas['MPMINQB']
    assert abs(b['consumo_plan_g'] - 600) < 0.5, b          # 2% × 30kg × 1000
    assert b['min_sugerido'] == 260, b                      # (600/90)×30×1.3 = 260
    # MP que el plan NO consume → MÍN 0 (deja de alertar comprar lo que no se usa)
    n = filas['MPMINNOPLAN']
    assert n['consumo_plan_g'] == 0, n
    assert n['min_sugerido'] == 0, n


def test_min_paridad_con_motor(app, db_clean):
    _seed_plan()
    c = _login(app)
    rm = c.get('/api/abastecimiento/consumo-horizontes?horizontes=90&tipo=mp')
    assert rm.status_code == 200, rm.data
    motor = {}
    for it in (rm.get_json().get('mps') or []):
        motor[(it.get('codigo') or '').upper()] = float((it.get('consumo') or {}).get('90', 0))
    rr = c.get('/api/inventario/recalcular-minimos?dias=90')
    filas = {f['codigo']: f for f in rr.get_json()['filas']}
    # el consumo del recalculador == el del motor verificado (MPs directas · sin bridge)
    assert abs(filas['MPMINQA']['consumo_plan_g'] - motor.get('MPMINQA', 0)) < 0.5, (filas['MPMINQA'], motor)
    assert abs(filas['MPMINQB']['consumo_plan_g'] - motor.get('MPMINQB', 0)) < 0.5, (filas['MPMINQB'], motor)


def test_min_aplicar_escribe_y_gate(app, db_clean):
    _seed_plan()
    c = _login(app)
    r = c.post('/api/inventario/recalcular-minimos',
               json={'dias': 90, 'colchon_pct': 30, 'lead_default': 30}, headers=csrf_headers())
    assert r.status_code == 200, r.data
    assert r.get_json()['aplicados'] >= 2, r.data
    conn = sqlite3.connect(os.environ['DB_PATH'])
    try:
        m = dict(conn.execute("SELECT codigo_mp, stock_minimo FROM maestro_mps "
                              "WHERE codigo_mp IN ('MPMINQA','MPMINQB','MPMINNOPLAN')").fetchall())
    finally:
        conn.close()
    assert abs(m['MPMINQA'] - 1300) < 0.5, m
    assert abs(m['MPMINQB'] - 260) < 0.5, m
    assert abs(m['MPMINNOPLAN'] - 0) < 0.5, m               # sin demanda → 0
    # Gate: un operario de planta NO puede definir mínimos (afecta compras)
    rg = _login(app, 'luis').get('/api/inventario/recalcular-minimos')
    assert rg.status_code == 403, rg.data


def test_min_respeta_manual(app, db_clean):
    _seed_plan()
    # MPMINQB fijado a mano (min_auto=0) → el recalculador NO lo pisa
    _exec("UPDATE maestro_mps SET stock_minimo=999, min_auto=0 WHERE codigo_mp='MPMINQB'")
    c = _login(app)
    c.post('/api/inventario/recalcular-minimos', json={'dias': 90}, headers=csrf_headers())
    conn = sqlite3.connect(os.environ['DB_PATH'])
    try:
        v = conn.execute("SELECT stock_minimo FROM maestro_mps WHERE codigo_mp='MPMINQB'").fetchone()[0]
    finally:
        conn.close()
    assert abs(v - 999) < 0.5, f"el mínimo manual (min_auto=0) no debe pisarse · {v}"
