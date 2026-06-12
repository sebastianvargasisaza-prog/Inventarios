"""Dashboard de planta · fixes paso 1 y 2 (Sebastián 12-jun · auditoría ultracode).
A-1: KPIs de operarios no rompe (GROUP BY con MIN, PG-safe).
C-1: FEFO de producción NO consume lotes BLOQUEADO por Calidad.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _db():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)


# ── C-1 · FEFO excluye BLOQUEADO ──────────────────────────────────────────
def test_fefo_no_consume_lote_bloqueado(app, db_clean):
    db = _db()
    db.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MPBLOQ1','Test Bloq',1)")
    db.execute("INSERT OR REPLACE INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg) VALUES ('ZZ BLOQ',1000,1)")
    db.execute("DELETE FROM formula_items WHERE producto_nombre='ZZ BLOQ'")
    db.execute("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
               "VALUES ('ZZ BLOQ','MPBLOQ1','Test Bloq',10,100)")
    # Único stock = 500g BLOQUEADO por Calidad. NO debe entrar a producción.
    db.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
               "VALUES ('MPBLOQ1','Test Bloq',500,'Entrada','2026-06-01','L-BLOQ','BLOQUEADO')")
    db.commit(); db.close()

    c = _login(app)
    r = c.post('/api/produccion', json={'producto': 'ZZ BLOQ', 'cantidad_kg': 1,
                                        'operador': 'sebastian', 'presentacion': 'x'},
               headers=csrf_headers())
    assert r.status_code in (200, 201, 422), r.data
    d = r.get_json()
    # El lote BLOQUEADO NO se consumió (no hay Salida de MPBLOQ1)
    db = _db()
    salidas = db.execute("SELECT COALESCE(SUM(cantidad),0) FROM movimientos "
                         "WHERE material_id='MPBLOQ1' AND tipo='Salida'").fetchone()[0]
    db.execute("DELETE FROM movimientos WHERE material_id='MPBLOQ1'")
    db.execute("DELETE FROM formula_items WHERE producto_nombre='ZZ BLOQ'")
    db.execute("DELETE FROM formula_headers WHERE producto_nombre='ZZ BLOQ'")
    db.commit(); db.close()
    assert salidas == 0, f"FEFO consumió {salidas}g de un lote BLOQUEADO (no debe)"
    # Debe reportarlo como faltante + retenido en BLOQUEADO
    f = next((x for x in d.get('faltantes', []) if x['material_id'] == 'MPBLOQ1'), None)
    assert f, f"debe faltar MPBLOQ1 (su único stock está BLOQUEADO) · {d}"
    assert 'BLOQUEADO' in (f.get('retenido_por_estado') or {}), f


# ── A-1 · KPIs de operarios (PG-safe) ─────────────────────────────────────
def test_kpis_operarios_no_rompe(app, db_clean):
    db = _db()
    try:
        cur = db.execute("INSERT INTO operarios_planta (nombre,apellido,rol_predeterminado) "
                         "VALUES ('TestOp','Apellido','envasado')")
        op_id = cur.lastrowid
        # actividades_sala exige area_id NOT NULL + tipo (CHECK enum)
        db.execute("INSERT INTO actividades_sala (area_id,operario_id,tipo,inicio_at,fin_at,duracion_min) "
                   "VALUES (1,?,'produccion',datetime('now','-5 hours'),datetime('now','-5 hours'),60)", (op_id,))
        db.commit()
    finally:
        db.close()

    c = _login(app)
    r = c.get('/api/planta/actividades/kpis')
    assert r.status_code == 200, r.data  # antes: 500 en PG por GROUP BY incompleto
    d = r.get_json()
    ops = d.get('por_operario', [])
    assert any('TestOp' in (o.get('operario') or '') for o in ops), f"el operario debe agregarse · {ops}"
