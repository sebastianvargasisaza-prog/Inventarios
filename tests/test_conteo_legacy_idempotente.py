"""B1 (Sebastián 12-jun): la ruta legacy PATCH /api/conteos/<id> (aplicar_ajustes)
no debe doble-insertar al aplicarse dos veces. Antes marcaba ajuste_aplicado por
codigo sin atomic-claim; ahora claima por fila (id) antes de insertar (M20/M3).
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
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def _q1(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        r = conn.execute(sql, params).fetchone(); return r[0] if r else None
    finally:
        conn.close()


def test_aplicar_ajustes_legacy_idempotente(app, db_clean):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MP-LEG','Test Leg',1)")
    cid = _exec("INSERT INTO conteos_fisicos (numero,estado,responsable) VALUES ('CNT-LEG','Abierto','sebastian')")
    # 1 item con diferencia -50 (no requiere gerencia)
    _exec("INSERT INTO conteo_items (conteo_id,codigo_mp,nombre_mp,stock_sistema,stock_fisico,diferencia,lote,requiere_gerencia,ajuste_aplicado) "
          "VALUES (?,'MP-LEG','Test Leg',100,50,-50,'L-LEG',0,0)", (cid,))

    c = _login(app)
    body = {'accion': 'aplicar_ajustes', 'responsable': 'sebastian'}
    r1 = c.patch(f'/api/conteos/{cid}', json=body, headers=csrf_headers())
    assert r1.status_code in (200, 201), r1.data
    # Aplicar OTRA vez (reintento / doble click) -> NO debe duplicar
    r2 = c.patch(f'/api/conteos/{cid}', json=body, headers=csrf_headers())
    assert r2.status_code in (200, 201), r2.data

    n = _q1("SELECT COUNT(*) FROM movimientos WHERE material_id='MP-LEG' AND tipo='Salida'")
    assert n == 1, f"el ajuste legacy debe aplicarse 1 sola vez (idempotente) · fueron {n}"
    aplicado = _q1("SELECT COALESCE(ajuste_aplicado,0) FROM conteo_items WHERE conteo_id=? AND codigo_mp='MP-LEG'", (cid,))
    assert aplicado == 1
