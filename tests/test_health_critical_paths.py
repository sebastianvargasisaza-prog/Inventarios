"""Tests para /api/admin/health/critical-paths · invariantes prod.

Sebastián 7-may-2026 (zero-error sprint día 4).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_health_critical_paths_estructura(app, db_clean):
    cs = _login(app, 'sebastian')
    r = cs.get('/api/admin/health/critical-paths')
    assert r.status_code in (200, 503), f'unexpected status: {r.status_code}'
    d = r.get_json()
    # Estructura esperada
    assert 'status' in d
    assert d['status'] in ('ok', 'warn', 'critical')
    assert 'checks' in d
    assert isinstance(d['checks'], list)
    assert d['total_checks'] == len(d['checks'])
    # Aritmética: crit + warn + ok = total
    assert (d['critical_count'] + d['warn_count'] + d['ok_count']
            == d['total_checks'])


def test_health_critical_paths_check_names(app, db_clean):
    """Verifica que los 8 checks core estén presentes."""
    cs = _login(app, 'sebastian')
    r = cs.get('/api/admin/health/critical-paths')
    d = r.get_json()
    check_names = {c['name'] for c in d['checks']}
    expected = {
        'tablas_criticas', 'indexes_criticos', 'producciones_zombie',
        'sols_planta_huerfanas', 'last_calendar_sync', 'last_backup',
        'agent_memory_smoke', 'movimientos_consistency',
    }
    missing = expected - check_names
    assert not missing, f'Faltan checks: {missing}'


def test_health_critical_paths_tablas_criticas_ok(app, db_clean):
    """En entorno test las tablas críticas deben existir."""
    cs = _login(app, 'sebastian')
    r = cs.get('/api/admin/health/critical-paths')
    d = r.get_json()
    tablas_check = next(c for c in d['checks'] if c['name'] == 'tablas_criticas')
    assert tablas_check['status'] == 'ok', \
        f'BUG migration: tablas críticas faltantes: {tablas_check}'


def test_health_critical_paths_agent_memory_smoke(app, db_clean):
    """La tabla agent_memory (mig 96) debe estar presente y respondiendo."""
    cs = _login(app, 'sebastian')
    r = cs.get('/api/admin/health/critical-paths')
    d = r.get_json()
    am_check = next(c for c in d['checks'] if c['name'] == 'agent_memory_smoke')
    assert am_check['status'] == 'ok', \
        f'agent_memory health falló: {am_check}'


def test_health_critical_paths_sin_login_401(client):
    r = client.get('/api/admin/health/critical-paths')
    assert r.status_code == 401


def test_health_critical_paths_no_admin_403(app, db_clean):
    cs = _login(app, 'catalina')
    r = cs.get('/api/admin/health/critical-paths')
    assert r.status_code == 403


def test_health_critical_paths_503_si_critical(app, db_clean):
    """Si hay un check critical, response es 503 (para uptime monitors)."""
    # El trigger trg_mov_tipo_valido (database.py:2752) ahora bloquea cualquier
    # tipo fuera de Entrada/Salida/Ajuste, así que ya no se puede insertar
    # 'TIPO_INVALIDO'. Pero el check movimientos_consistency (admin.py:2338)
    # NO incluye 'Ajuste' en su whitelist · un movimiento 'Ajuste' es aceptado
    # por el trigger y a la vez marcado critical por el health check.
    conn = sqlite3.connect(os.environ['DB_PATH'])
    conn.execute("""
        INSERT INTO movimientos
          (material_id, material_nombre, cantidad, tipo, fecha, lote, operador)
        VALUES ('TEST-INVALID', 'X', 100, 'Ajuste', date('now'), 'L1', 'test')
    """)
    conn.commit()
    conn.close()
    try:
        cs = _login(app, 'sebastian')
        r = cs.get('/api/admin/health/critical-paths')
        assert r.status_code == 503, \
            f'esperaba 503 con critical, got {r.status_code}: {r.data[:200]}'
        d = r.get_json()
        assert d['status'] == 'critical'
        cons_check = next(c for c in d['checks']
                          if c['name'] == 'movimientos_consistency')
        assert cons_check['status'] == 'critical'
    finally:
        conn = sqlite3.connect(os.environ['DB_PATH'])
        conn.execute("DELETE FROM movimientos WHERE material_id='TEST-INVALID'")
        conn.commit()
        conn.close()
