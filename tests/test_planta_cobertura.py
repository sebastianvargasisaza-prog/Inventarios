"""17-jun · Cobertura de endpoints de Planta que se arreglaron en la auditoría y
NO tenían test propio (blindaje · "algo que se escape rompe todo").

- recepcion_aprobar_lote: NO puede revivir un lote RECHAZADO a VIGENTE (INVIMA).
- prog_cancelar_evento: NO cancela una producción ya completada/descontada (M27 guard).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, u='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': u, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def test_aprobar_lote_no_revive_rechazado(app, db_clean):
    """recepcion_aprobar_lote SOLO dispone lotes en cuarentena · un lote RECHAZADO
    no se puede 'Aprobar' (revivir a VIGENTE = material rechazado usable · INVIMA)."""
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote, operador) "
                     "VALUES ('MPREV','X',500,'Entrada','2026-06-10','LREV','RECHAZADO','qc')")
        mid = conn.execute("SELECT id FROM movimientos WHERE lote='LREV'").fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    c = _login(app)  # sebastian = admin
    r = c.post('/api/recepcion/aprobar-lote', json={'mov_id': mid, 'estado': 'Aprobado'},
               headers=csrf_headers())
    try:
        assert r.status_code == 409, r.data[:300]
        conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
        est = conn.execute("SELECT estado_lote FROM movimientos WHERE id=?", (mid,)).fetchone()[0]
        conn.close()
        assert est == 'RECHAZADO', f'el lote rechazado NO debe revivir · quedó {est}'
    finally:
        conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
        conn.execute("DELETE FROM movimientos WHERE material_id='MPREV'")
        conn.commit(); conn.close()


def test_cancelar_produccion_completada_da_409(app, db_clean):
    """prog_cancelar_evento NO cancela una producción ya completada/descontada
    (si lo hiciera dejaría stock fantasma · M27). Debe devolver 409 YA_COMPLETADA."""
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("DELETE FROM produccion_programada WHERE producto='CANCEL GUARD PROD'")
        conn.execute("INSERT INTO produccion_programada (producto, fecha_programada, estado, origen, cantidad_kg, inventario_descontado_at) "
                     "VALUES ('CANCEL GUARD PROD', '2026-06-20', 'completado', 'manual', 10, '2026-06-16T08:00:00')")
        pid = conn.execute("SELECT id FROM produccion_programada WHERE producto='CANCEL GUARD PROD'").fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    c = _login(app)
    r = c.delete(f'/api/programacion/programar/{pid}', headers=csrf_headers())
    try:
        assert r.status_code == 409, r.data[:300]
        assert (r.get_json() or {}).get('codigo') == 'YA_COMPLETADA'
        conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
        est = conn.execute("SELECT estado FROM produccion_programada WHERE id=?", (pid,)).fetchone()[0]
        conn.close()
        assert est == 'completado', f'no debe cancelarse · quedó {est}'
    finally:
        conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
        conn.execute("DELETE FROM produccion_programada WHERE producto='CANCEL GUARD PROD'")
        conn.commit(); conn.close()
