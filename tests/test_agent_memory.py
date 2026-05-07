"""Tests para /api/admin/agent-memory · memoria persistente IA.

Sebastián 7-may-2026 (zero-error sprint día 3).
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


def _cleanup_keys(keys):
    if not keys:
        return
    conn = sqlite3.connect(os.environ['DB_PATH'])
    ph = ','.join(['?'] * len(keys))
    conn.execute(f"DELETE FROM agent_memory WHERE key IN ({ph})", keys)
    conn.commit()
    conn.close()


def test_agent_memory_post_get_basic(app, db_clean):
    cs = _login(app, 'sebastian')
    try:
        # POST upsert
        r = cs.post('/api/admin/agent-memory',
                    json={'key': 'test_key_1', 'value': 'hello',
                          'category': 'test'},
                    headers=csrf_headers())
        assert r.status_code == 200
        assert r.get_json()['ok'] is True

        # GET by key
        r = cs.get('/api/admin/agent-memory?key=test_key_1')
        assert r.status_code == 200
        d = r.get_json()
        assert d['key'] == 'test_key_1'
        assert d['value'] == 'hello'
        assert d['category'] == 'test'
        assert d['created_by'] == 'sebastian'
    finally:
        _cleanup_keys(['test_key_1'])


def test_agent_memory_upsert_actualiza(app, db_clean):
    cs = _login(app, 'sebastian')
    try:
        cs.post('/api/admin/agent-memory',
                json={'key': 'test_upsert', 'value': 'v1', 'category': 'cat1'},
                headers=csrf_headers())
        cs.post('/api/admin/agent-memory',
                json={'key': 'test_upsert', 'value': 'v2', 'category': 'cat2'},
                headers=csrf_headers())
        r = cs.get('/api/admin/agent-memory?key=test_upsert')
        d = r.get_json()
        assert d['value'] == 'v2'
        assert d['category'] == 'cat2'
    finally:
        _cleanup_keys(['test_upsert'])


def test_agent_memory_filter_category(app, db_clean):
    cs = _login(app, 'sebastian')
    try:
        cs.post('/api/admin/agent-memory',
                json={'key': 'gp_a', 'value': '1', 'category': 'release'},
                headers=csrf_headers())
        cs.post('/api/admin/agent-memory',
                json={'key': 'gp_b', 'value': '2', 'category': 'release'},
                headers=csrf_headers())
        cs.post('/api/admin/agent-memory',
                json={'key': 'gp_c', 'value': '3', 'category': 'bug'},
                headers=csrf_headers())
        r = cs.get('/api/admin/agent-memory?category=release')
        keys = {e['key'] for e in r.get_json()['entries']}
        assert 'gp_a' in keys and 'gp_b' in keys
        assert 'gp_c' not in keys
    finally:
        _cleanup_keys(['gp_a', 'gp_b', 'gp_c'])


def test_agent_memory_delete(app, db_clean):
    cs = _login(app, 'sebastian')
    cs.post('/api/admin/agent-memory',
            json={'key': 'gp_del', 'value': 'x', 'category': 'tmp'},
            headers=csrf_headers())
    r = cs.post('/api/admin/agent-memory',
                json={'key': 'gp_del', '_delete': True},
                headers=csrf_headers())
    assert r.status_code == 200
    assert r.get_json()['deleted'] == 'gp_del'
    # Verificar borrado
    r = cs.get('/api/admin/agent-memory?key=gp_del')
    assert r.status_code == 404


def test_agent_memory_value_dict_serializa(app, db_clean):
    """Si el agente envía un dict como value, se serializa a JSON."""
    cs = _login(app, 'sebastian')
    try:
        cs.post('/api/admin/agent-memory',
                json={'key': 'gp_dict', 'value': {'a': 1, 'b': 'x'},
                      'category': 'test'},
                headers=csrf_headers())
        r = cs.get('/api/admin/agent-memory?key=gp_dict')
        d = r.get_json()
        assert '"a": 1' in d['value']
        assert '"b": "x"' in d['value']
    finally:
        _cleanup_keys(['gp_dict'])


def test_agent_memory_sin_login_401(client):
    r = client.get('/api/admin/agent-memory')
    assert r.status_code == 401


def test_agent_memory_no_admin_403(app, db_clean):
    cs = _login(app, 'catalina')   # compras, no admin
    r = cs.get('/api/admin/agent-memory')
    assert r.status_code == 403
