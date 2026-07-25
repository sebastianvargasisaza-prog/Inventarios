"""Generar OC / Regenerar OC desde el Centro de Programación no pueden reventar con 500.

Auditoría 25-jul (workflow ultracode): `siguiente_correlativo` espera un CURSOR (hace
`c.execute(...)` y después `c.fetchall()`), y estos dos endpoints le pasan la CONEXIÓN.
Ni `sqlite3.Connection` ni `PgConnection` tienen `fetchall` → AttributeError → 500.

Los otros 14 llamadores del repo pasan cursor; solo estos dos quedaron mal, y ningún test
los tocaba: la suite probaba el MOTOR de déficit (`_mp_deficit_para_oc`) pero nunca el
endpoint que ESCRIBE las solicitudes.

El de regenerar es además DESTRUCTIVO: borra las SOL/OC viejas y hace `conn.commit()`
ANTES de llegar a la línea que revienta, así que borra y no vuelve a crear.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = 'ZZ GENOC PROD'
MP = 'MPGENOC1'


def _db():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=15)


def _sql(*stmts):
    db = _db()
    try:
        for s in stmts:
            db.execute(s)
        db.commit()
    finally:
        db.close()


def _login(app, u='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': u, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar():
    _sql("DELETE FROM produccion_programada WHERE producto='%s'" % PROD,
         "DELETE FROM formula_items WHERE producto_nombre='%s'" % PROD,
         "DELETE FROM formula_headers WHERE producto_nombre='%s'" % PROD,
         "DELETE FROM solicitudes_compra_items WHERE codigo_mp='%s'" % MP,
         "DELETE FROM movimientos WHERE material_id='%s'" % MP,
         "DELETE FROM maestro_mps WHERE codigo_mp='%s'" % MP)


def _sembrar_deficit():
    """Un producto programado sin stock de su MP → déficit garantizado."""
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo,controla_stock) "
         "VALUES ('%s','GLYCERIN GENOC','Glicerina GenOC','MP',1,1)" % MP,
         "INSERT INTO formula_headers (producto_nombre,unidad_base_g,lote_size_kg,activo,fecha_creacion) "
         "VALUES ('%s',20000,20,1,datetime('now'))" % PROD,
         "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
         "VALUES ('%s','%s','GLYCERIN GENOC',10.0,0)" % (PROD, MP),
         "INSERT INTO produccion_programada (producto,fecha_programada,lotes,cantidad_kg,origen,estado) "
         "VALUES ('%s', date('now','-5 hours','+5 days'), 1, 20, 'eos_plan', 'pendiente')" % PROD)


def test_generar_oc_no_revienta(app):
    """El botón 'Generar OC' del Centro de Programación tiene que responder, no dar 500."""
    _sembrar_deficit()
    c = _login(app)
    try:
        r = c.post('/api/programacion/generar-oc', json={}, headers=csrf_headers())
        assert r.status_code != 500, \
            'Generar OC devolvió 500 · %s' % r.data[:400]
        assert r.status_code in (200, 201), r.data[:400]
    finally:
        _limpiar()


def test_regenerar_oc_no_borra_y_falla(app):
    """Regenerar OC borra las viejas y commitea ANTES de crear: si revienta, deja el hueco."""
    _sembrar_deficit()
    c = _login(app)
    try:
        r = c.post('/api/programacion/regenerar-oc', json={}, headers=csrf_headers())
        assert r.status_code != 500, \
            'Regenerar OC devolvió 500 DESPUÉS de borrar las viejas · %s' % r.data[:400]
        assert r.status_code in (200, 201), r.data[:400]
    finally:
        _limpiar()


def test_correlativo_acepta_cursor_no_conexion(app):
    """El helper exige cursor: dejarlo documentado con una prueba directa."""
    with app.app_context():
        from database import get_db
        from audit_helpers import siguiente_correlativo
        conn = get_db()
        n = siguiente_correlativo(conn.cursor(), 'solicitudes_compra', 'numero', 'SOL-2026-')
        assert isinstance(n, int) and n >= 1
