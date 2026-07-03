"""Sebastián 3-jul: "forzar (normalizar)" · mover/editar-kg producciones YA ejecutadas para cuadrar el
calendario con MyBatch · cambia SOLO el registro (fecha/cantidad_kg), NO toca el inventario (la
producción ya se hizo · la MP no se revierte). Sin forzar → 409 con puede_forzar=True."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _lote_ejecutado(fecha='2026-06-30', kg=50):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute(
            "INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,"
            "inicio_real_at,inventario_descontado_at) VALUES ('PROD NORM',?,'programado','eos_plan',?,1,"
            "'2026-06-30 08:00:00','2026-06-30 08:05:00')", (fecha, kg))
        conn.commit()
        return conn.execute("SELECT id FROM produccion_programada WHERE producto='PROD NORM'").fetchone()[0]
    finally:
        conn.close()


def _row(pid):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        return conn.execute(
            "SELECT fecha_programada, cantidad_kg, inventario_descontado_at FROM produccion_programada WHERE id=?",
            (pid,)).fetchone()
    finally:
        conn.close()


def test_mover_ejecutado_sin_forzar_409(app, db_clean):
    pid = _lote_ejecutado()
    c = _login(app)
    r = c.post('/api/plan/proximas/%d/reprogramar' % pid,
               json={'nueva_fecha': '2026-07-01'}, headers=csrf_headers())
    assert r.status_code == 409, r.data[:300]
    assert (r.get_json() or {}).get('puede_forzar') is True


def test_mover_ejecutado_forzar_cambia_fecha_no_inventario(app, db_clean):
    pid = _lote_ejecutado()
    inv_antes = _row(pid)[2]
    c = _login(app)
    r = c.post('/api/plan/proximas/%d/reprogramar' % pid,
               json={'nueva_fecha': '2026-07-01', 'forzar_normalizar': True}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    fecha, _kg, inv_despues = _row(pid)
    assert str(fecha)[:10] == '2026-07-01'
    assert inv_despues == inv_antes  # el inventario NO se toca (sigue descontado)


def test_editar_kg_ejecutado_sin_forzar_409(app, db_clean):
    pid = _lote_ejecutado(kg=50)
    c = _login(app)
    r = c.post('/api/plan/proximas/%d/cantidad' % pid,
               json={'cantidad_kg': 42}, headers=csrf_headers())
    assert r.status_code == 409, r.data[:300]
    assert (r.get_json() or {}).get('puede_forzar') is True


def test_editar_kg_ejecutado_forzar_cambia_registro(app, db_clean):
    pid = _lote_ejecutado(kg=50)
    inv_antes = _row(pid)[2]
    c = _login(app)
    r = c.post('/api/plan/proximas/%d/cantidad' % pid,
               json={'cantidad_kg': 42, 'forzar_normalizar': True}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    _fecha, kg, inv_despues = _row(pid)
    assert abs(float(kg) - 42) < 0.01
    assert inv_despues == inv_antes  # NO re-descuenta MP


def _otro_lote_mismo_dia(fecha='2026-06-30'):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes) "
                     "VALUES ('OTRO MISMO DIA',?,'programado','eos_plan',5,1)", (fecha,))
        conn.commit()
    finally:
        conn.close()


def test_editar_a_lote_grande_sin_forzar_409_puede_forzar(app, db_clean):
    """Renova 30-jun = 70kg (>50 grande) pero el día tiene otros lotes → sin forzar 409 con puede_forzar."""
    pid = _lote_ejecutado(kg=16, fecha='2026-06-30')
    _otro_lote_mismo_dia('2026-06-30')
    c = _login(app)
    r = c.post('/api/plan/proximas/%d/cantidad' % pid, json={'cantidad_kg': 70}, headers=csrf_headers())
    assert r.status_code == 409, r.data[:300]
    assert (r.get_json() or {}).get('puede_forzar') is True


def test_editar_a_lote_grande_forzar_ok(app, db_clean):
    pid = _lote_ejecutado(kg=16, fecha='2026-06-30')
    _otro_lote_mismo_dia('2026-06-30')
    c = _login(app)
    r = c.post('/api/plan/proximas/%d/cantidad' % pid,
               json={'cantidad_kg': 70, 'forzar_normalizar': True}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert abs(float(_row(pid)[1]) - 70) < 0.01
