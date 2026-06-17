"""17-jun · Auditoría ultracode de Planta (corazón de EOS) · regresiones de los P1.

Cubre los fixes de mayor valor:
- [10] anular_movimiento no da 500 (columna fantasma mp.nombre eliminada).
- [2]  _distribuir_fefo NO consume lote vencido-por-fecha aunque el cron no corrió (M25).
- [9]  "Generar plan" preserva compromisos B2B (eos_b2b) y producción ejecutada.
"""
import os
import sys
import sqlite3
from datetime import datetime, timedelta

from .conftest import TEST_PASSWORD, csrf_headers

api = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api')
if api not in sys.path:
    sys.path.insert(0, api)


def _login(app, u='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': u, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def test_anular_movimiento_no_da_500(app, db_clean):
    """[10] El SELECT usaba mp.nombre (columna inexistente en maestro_mps) → 500 en
    TODA anulación. Ahora debe procesar (200) o un error de negocio, NUNCA 500."""
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote, operador) "
                     "VALUES ('MPANUL','X',100,'Entrada','2026-06-10','LANUL','VIGENTE','sebastian')")
        mov_id = conn.execute("SELECT id FROM movimientos WHERE lote='LANUL'").fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    c = _login(app)
    r = c.post(f'/api/movimientos/{mov_id}/anular', json={'motivo': 'error de digitación test'},
               headers=csrf_headers())
    assert r.status_code != 500, r.data[:300]
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    conn.execute("DELETE FROM movimientos WHERE material_id='MPANUL'")
    conn.commit(); conn.close()


def test_distribuir_fefo_excluye_vencido_por_fecha(app, db_clean):
    """[2/M25] _distribuir_fefo NO debe entregar un lote vencido-por-fecha aunque su
    estado_lote siga 'VIGENTE' (el cron job_marcar_vencidos no corrió)."""
    from blueprints.programacion import _distribuir_fefo
    ayer = ((datetime.utcnow() - timedelta(hours=5)).date() - timedelta(days=1)).isoformat()
    futuro = ((datetime.utcnow() - timedelta(hours=5)).date() + timedelta(days=200)).isoformat()
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("DELETE FROM movimientos WHERE material_id='MPFEFO25'")
        # lote VENCIDO por fecha pero estado aún VIGENTE (cron no corrió)
        conn.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote, fecha_vencimiento) "
                     "VALUES ('MPFEFO25','X',1000,'Entrada','2026-01-01','LVENC','VIGENTE',?)", (ayer,))
        # lote sano (vence en el futuro)
        conn.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote, fecha_vencimiento) "
                     "VALUES ('MPFEFO25','X',1000,'Entrada','2026-06-10','LSANO','VIGENTE',?)", (futuro,))
        conn.commit()
        dist = _distribuir_fefo(conn.cursor(), 'MPFEFO25', 500)
        lotes = {d.get('lote') for d in dist} if dist else set()
    finally:
        conn.execute("DELETE FROM movimientos WHERE material_id='MPFEFO25'")
        conn.commit(); conn.close()
    assert 'LVENC' not in lotes, f"NO debe consumir el lote vencido-por-fecha: {dist}"
    assert 'LSANO' in lotes, f"debe consumir el lote sano: {dist}"


def test_generar_plan_preserva_b2b(app, db_clean):
    """[9] "Generar plan" (LIMPIAR) NO debe cancelar producción origen='eos_b2b'
    (compromisos de clientes) ni la ya ejecutada."""
    from blueprints.plan import _generar_plan_desde_hoy
    fut = ((datetime.utcnow() - timedelta(hours=5)).date() + timedelta(days=10)).isoformat()
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("DELETE FROM produccion_programada WHERE producto IN ('B2B GUARD PROD','EJEC GUARD PROD')")
        conn.execute("INSERT INTO produccion_programada (producto, fecha_programada, estado, origen, cantidad_kg) "
                     "VALUES ('B2B GUARD PROD', ?, 'pendiente', 'eos_b2b', 10)", (fut,))
        # ejecutada (inicio_real_at) con origen sugerido → tampoco debe cancelarse
        conn.execute("INSERT INTO produccion_programada (producto, fecha_programada, estado, origen, cantidad_kg, inicio_real_at) "
                     "VALUES ('EJEC GUARD PROD', ?, 'programado', 'auto_plan', 10, '2026-06-16T08:00:00')", (fut,))
        conn.commit()
        _generar_plan_desde_hoy(conn, dias=60, usuario='test', dry_run=False)
        b2b = conn.execute("SELECT estado FROM produccion_programada WHERE producto='B2B GUARD PROD'").fetchone()
        ejec = conn.execute("SELECT estado FROM produccion_programada WHERE producto='EJEC GUARD PROD'").fetchone()
    finally:
        conn.execute("DELETE FROM produccion_programada WHERE producto IN ('B2B GUARD PROD','EJEC GUARD PROD')")
        conn.commit(); conn.close()
    assert b2b and b2b[0] != 'cancelado', f"el compromiso B2B NO debe cancelarse: {b2b}"
    assert ejec and ejec[0] != 'cancelado', f"la producción ejecutada NO debe cancelarse: {ejec}"
