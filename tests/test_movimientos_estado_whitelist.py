"""P2 (Sebastián 12-jun · hallazgo Fable): POST /api/movimientos valida + normaliza
estado_lote. Antes entraba crudo -> un 'cuarentena' minúscula o un estado inventado
evadía los filtros NOT IN (mayúsculas) del FEFO/descuento.
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


def _estado_de(lote):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        r = conn.execute("SELECT estado_lote FROM movimientos WHERE lote=? ORDER BY id DESC LIMIT 1", (lote,)).fetchone()
        return r[0] if r else None
    finally:
        conn.close()


def test_movimiento_normaliza_estado_minuscula(app, db_clean):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MP-WL','Test WL',1)")
    c = _login(app)
    # 'cuarentena' minúscula -> debe guardarse 'CUARENTENA' (normalizado)
    r = c.post('/api/movimientos', json={'material_id': 'MP-WL', 'material_nombre': 'Test WL',
                                         'cantidad': 100, 'tipo': 'Entrada', 'lote': 'L-WL1',
                                         'estado_lote': 'cuarentena'}, headers=csrf_headers())
    assert r.status_code in (200, 201), r.data
    assert _estado_de('L-WL1') == 'CUARENTENA', "debe normalizar a mayúsculas canónicas"


def test_movimiento_rechaza_estado_inventado(app, db_clean):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MP-WL2','Test WL2',1)")
    c = _login(app)
    r = c.post('/api/movimientos', json={'material_id': 'MP-WL2', 'material_nombre': 'Test WL2',
                                         'cantidad': 100, 'tipo': 'Entrada', 'lote': 'L-WL2',
                                         'estado_lote': 'retenido'}, headers=csrf_headers())
    assert r.status_code == 400, f"un estado inventado debe rechazarse · {r.status_code} {r.data}"
    assert _estado_de('L-WL2') is None, "no debe persistir el movimiento con estado inválido"
