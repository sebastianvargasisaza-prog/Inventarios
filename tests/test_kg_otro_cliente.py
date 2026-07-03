"""Sebastián 2-jul: reserva MANUAL de kg para otro cliente (kg_otro_cliente · mig 334).
La cobertura/próxima de Animus usa la porción Animus = cantidad_kg − B2B − kg_otro_cliente
(caso Renova Body: 80% del lote iba para otra marca, sin pedido B2B formal)."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _lote(kg=30, fecha='2026-09-15'):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes) "
                     "VALUES ('PROD OTRO',?,'pendiente','eos_plan',?,1)", (fecha, kg))
        conn.commit()
        return conn.execute("SELECT id FROM produccion_programada WHERE producto='PROD OTRO'").fetchone()[0]
    finally:
        conn.close()


def _get_kg_otro(pid):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        return conn.execute("SELECT kg_otro_cliente FROM produccion_programada WHERE id=?", (pid,)).fetchone()[0]
    finally:
        conn.close()


def test_guarda_kg_otro_cliente(app, db_clean):
    pid = _lote(kg=30, fecha='2026-09-16')
    c = _login(app)
    r = c.post('/api/plan/proximas/%d/cantidad' % pid, json={'cantidad_kg': 30, 'kg_otro_cliente': 20},
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert _get_kg_otro(pid) == 20


def test_clamp_no_excede_el_lote(app, db_clean):
    pid = _lote(kg=30, fecha='2026-09-17')
    c = _login(app)
    # pedir 500 para otro cliente en un lote de 30 → clamp a 30
    r = c.post('/api/plan/proximas/%d/cantidad' % pid, json={'cantidad_kg': 30, 'kg_otro_cliente': 500},
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert _get_kg_otro(pid) == 30


def test_kg_otro_en_lote_en_curso(app, db_clean):
    """Sebastián 3-jul: la porción 'para otro cliente' es metadata · se puede guardar aunque el lote
    esté EN CURSO (inicio_real_at) · sin cantidad_kg no dispara el guard de inmutabilidad."""
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,inicio_real_at) "
                     "VALUES ('PROD ENCURSO','2026-06-30','programado','eos_plan',50,1,'2026-06-30 08:00:00')")
        conn.commit()
        pid = conn.execute("SELECT id FROM produccion_programada WHERE producto='PROD ENCURSO'").fetchone()[0]
    finally:
        conn.close()
    c = _login(app)
    # solo kg_otro_cliente (sin cantidad_kg) → debe pasar aunque esté en curso
    r = c.post('/api/plan/proximas/%d/cantidad' % pid, json={'kg_otro_cliente': 35}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert _get_kg_otro(pid) == 35
    # pero CAMBIAR el kg sí debe bloquearse en curso
    r2 = c.post('/api/plan/proximas/%d/cantidad' % pid, json={'cantidad_kg': 80}, headers=csrf_headers())
    assert r2.status_code == 409, r2.data[:200]
