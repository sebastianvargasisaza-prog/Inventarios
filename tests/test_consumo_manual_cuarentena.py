"""B-1 (Sebastián 12-jun): el consumo manual NO debe descontar stock retenido por
Calidad (cuarentena/rechazado). Antes stock_antes sumaba TODO -> permitia consumir
stock en cuarentena y dejar el saldo producible negativo.
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


def test_consumo_manual_no_descuenta_cuarentena(app, db_clean):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MP-CUAR','Test Cuar',1)")
    # Único stock = 500g en CUARENTENA (retenido por Calidad)
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
          "VALUES ('MP-CUAR','Test Cuar',500,'Entrada',datetime('now'),'L-CUAR','CUARENTENA')")

    c = _login(app)
    r = c.post('/api/consumo-manual', json={'codigo_mp': 'MP-CUAR', 'cantidad': 100,
                                            'lote': 'L-CUAR', 'operador': 'sebastian'},
               headers=csrf_headers())
    # Debe bloquear (stock producible = 0 porque está en cuarentena) salvo forzar
    assert r.status_code != 200 or not (r.get_json() or {}).get('ok'), \
        f"no debe descontar stock en cuarentena sin forzar · {r.status_code} {r.data}"
    # No se creó Salida
    conn = sqlite3.connect(os.environ['DB_PATH'])
    salida = conn.execute("SELECT COALESCE(SUM(cantidad),0) FROM movimientos "
                          "WHERE material_id='MP-CUAR' AND tipo='Salida'").fetchone()[0]
    conn.close()
    assert salida == 0, f"no debe haber Salida (stock en cuarentena) · fue {salida}"
