"""Tests del dashboard zero-error · Sebastián 7-may-2026."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_zero_error_status_estructura(app, db_clean):
    cs = _login(app, 'sebastian')
    r = cs.get('/api/admin/zero-error/status')
    assert r.status_code == 200, f'status fallo: {r.status_code} {r.data[:200]}'
    d = r.get_json()
    expected_keys = ['golden_paths', 'watcher', 'health', 'agent_memory',
                     'session_logs', 'git', 'pending_bugs',
                     'global_status', 'generated_at']
    for k in expected_keys:
        assert k in d, f'falta key {k} · keys: {list(d.keys())}'


def test_zero_error_golden_paths_count(app, db_clean):
    cs = _login(app, 'sebastian')
    r = cs.get('/api/admin/zero-error/status')
    d = r.get_json()
    gp = d['golden_paths']
    # Si el archivo existe, debe haber al menos 5 tests golden
    if 'count' in gp:
        assert gp['count'] >= 5, f'pocos golden paths · {gp["count"]}'
        # Debe listar nombres de tests
        assert all(t.startswith('test_golden_') for t in gp.get('tests', [])[:10])


def test_zero_error_health_incluido(app, db_clean):
    cs = _login(app, 'sebastian')
    r = cs.get('/api/admin/zero-error/status')
    d = r.get_json()
    health = d['health']
    # Si no hay error, debe traer checks
    if 'error' not in health:
        assert 'checks' in health or 'status' in health, \
            f'health sin estructura · {health}'


def test_zero_error_pending_bugs_listado(app, db_clean):
    cs = _login(app, 'sebastian')
    r = cs.get('/api/admin/zero-error/status')
    d = r.get_json()
    bugs = d['pending_bugs']
    assert isinstance(bugs, list)
    # Cada bug debe tener id + title + severity + next_action
    for b in bugs:
        assert all(k in b for k in ('id', 'title', 'severity', 'next_action')), \
            f'bug malformado · {b}'


def test_zero_error_status_sin_login_401(client):
    r = client.get('/api/admin/zero-error/status')
    assert r.status_code == 401


def test_zero_error_status_no_admin_403(app, db_clean):
    cs = _login(app, 'catalina')
    r = cs.get('/api/admin/zero-error/status')
    assert r.status_code == 403


def test_zero_error_html_page_admin(app, db_clean):
    cs = _login(app, 'sebastian')
    r = cs.get('/admin/zero-error')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Zero-Error Dashboard' in body
    assert '/api/admin/zero-error/status' in body  # JS fetch


def test_zero_error_html_no_admin_403(app, db_clean):
    cs = _login(app, 'catalina')
    r = cs.get('/admin/zero-error')
    assert r.status_code == 403
