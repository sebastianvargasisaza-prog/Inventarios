"""Bodega MP · vista 'No disponible / retenido' (12-jun).

A1 excluyó RECHAZADO/VENCIDO/BLOQUEADO de /api/lotes para no enmascarar
quiebres, pero ese material físico debe seguir TRAZABLE (INVIMA Res. 2214) y
cuadrar con el conteo físico. /api/lotes/retenido cierra ese hueco: lista a
nivel de lote lo retenido con saldo, sin que reaparezca como disponible.
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


def _seed(cod, lote, cant, estado, tipo='Entrada'):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,tipo_material,activo) "
          "VALUES (?,?,?, 'MP',1)", (cod, 'Test ' + cod, 'INCI ' + cod))
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
          "VALUES (?,?,?,?,datetime('now'),?,?)", (cod, 'Test ' + cod, cant, tipo, lote, estado))


def test_retenido_lista_rechazado_vencido_bloqueado(app, db_clean):
    _seed('MP-RET-R', 'L-R', 700, 'RECHAZADO')
    _seed('MP-RET-V', 'L-V', 300, 'VENCIDO')
    _seed('MP-RET-B', 'L-B', 120, 'BLOQUEADO')

    c = _login(app)
    r = c.get('/api/lotes/retenido')
    assert r.status_code == 200, r.data
    data = r.get_json()
    by_lote = {x['lote']: x for x in data}
    assert 'L-R' in by_lote and by_lote['L-R']['estado_lote'] == 'RECHAZADO'
    assert 'L-V' in by_lote and by_lote['L-V']['estado_lote'] == 'VENCIDO'
    assert 'L-B' in by_lote and by_lote['L-B']['estado_lote'] == 'BLOQUEADO'
    assert abs(by_lote['L-R']['cantidad'] - 700) < 0.5


def test_retenido_no_incluye_vigente_ni_cuarentena(app, db_clean):
    _seed('MP-RET-OK', 'L-OK', 500, 'VIGENTE')
    _seed('MP-RET-Q', 'L-Q', 400, 'CUARENTENA')

    c = _login(app)
    data = c.get('/api/lotes/retenido').get_json()
    lotes = {x['lote'] for x in data}
    assert 'L-OK' not in lotes, "VIGENTE no es retenido"
    assert 'L-Q' not in lotes, "CUARENTENA tiene su propia vista, no la de retenido"


def test_retenido_no_aparece_en_api_lotes(app, db_clean):
    """El lote retenido NO debe reaparecer como disponible (preserva A1)."""
    _seed('MP-RET-X', 'L-X', 900, 'RECHAZADO')
    c = _login(app)
    lotes = c.get('/api/lotes').get_json()['lotes']
    assert not any(x['material_id'] == 'MP-RET-X' for x in lotes), \
        "un lote RECHAZADO no debe salir en /api/lotes (stock disponible)"


def test_retenido_excluye_saldo_cero_y_polvo(app, db_clean):
    """Umbral >0.01 (M21): un lote consumido a 0 o con polvo no aparece."""
    # Entrada 500 RECHAZADO + Salida 500 (mismo estado) -> neto 0
    _seed('MP-RET-Z', 'L-Z', 500, 'RECHAZADO')
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
          "VALUES ('MP-RET-Z','Test MP-RET-Z',500,'Salida',datetime('now'),'L-Z','RECHAZADO')")
    # polvo 0.004
    _seed('MP-RET-P', 'L-P', 0.004, 'VENCIDO')

    c = _login(app)
    lotes = {x['lote'] for x in c.get('/api/lotes/retenido').get_json()}
    assert 'L-Z' not in lotes, "saldo neto 0 no debe aparecer"
    assert 'L-P' not in lotes, "polvo <0.01 no debe aparecer"


def test_retenido_case_insensitive(app, db_clean):
    """Defensa M23: un estado en Title-case ('Rechazado') igual se detecta."""
    _seed('MP-RET-CI', 'L-CI', 250, 'Rechazado')
    c = _login(app)
    lotes = {x['lote'] for x in c.get('/api/lotes/retenido').get_json()}
    assert 'L-CI' in lotes, "el filtro debe ser UPPER-insensible al case"


def test_retenido_seccion_en_tab_cuarentena(app, db_clean):
    c = _login(app)
    body = c.get('/inventarios').data.decode('utf-8', 'replace')
    assert 'ret-tbody' in body, "el tab debe tener la tabla de retenido"
    assert "fetch('/api/lotes/retenido')" in body, "debe cargar el endpoint de retenido"
