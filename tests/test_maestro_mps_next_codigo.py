"""Tests para /api/maestro-mps/next-codigo · Sebastián 8-may-2026.

Endpoint que devuelve el siguiente código MP disponible para evitar
que los usuarios adivinen el consecutivo y dupliquen códigos.
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


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'])
    conn.execute(sql, params)
    conn.commit()
    conn.close()


def test_next_codigo_arranca_en_mp00001_si_vacio(app, db_clean):
    """Si no hay MPs en el catálogo, el siguiente es MP00001."""
    _exec("DELETE FROM maestro_mps WHERE codigo_mp LIKE 'TEST_NEXT%'")
    cs = _login(app, 'sebastian')
    r = cs.get('/api/maestro-mps/next-codigo?prefix=TEST_NEXT')
    assert r.status_code == 200
    d = r.get_json()
    assert d['siguiente'] == 'TEST_NEXT00001'
    assert d['ultimo'] is None
    assert d['siguiente_n'] == 1
    assert d['total_con_prefix'] == 0


def test_next_codigo_max_plus_one(app, db_clean):
    """Si existen MP00100 y MP00150, el siguiente es MP00151."""
    cs = _login(app, 'sebastian')
    # Seed
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_comercial, activo, tipo_material) VALUES ('TEST_NXT00100', 'X', 1, 'MP')")
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_comercial, activo, tipo_material) VALUES ('TEST_NXT00150', 'Y', 1, 'MP')")
    try:
        r = cs.get('/api/maestro-mps/next-codigo?prefix=TEST_NXT')
        d = r.get_json()
        assert d['siguiente_n'] == 151
        assert d['siguiente'] == 'TEST_NXT00151'
        assert d['ultimo'] == 'TEST_NXT00150'
        assert d['total_con_prefix'] == 2
    finally:
        _exec("DELETE FROM maestro_mps WHERE codigo_mp LIKE 'TEST_NXT%'")


def test_next_codigo_ignora_archivadas(app, db_clean):
    """Códigos archivados (activo=0) cuentan también para el max."""
    cs = _login(app, 'sebastian')
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_comercial, activo, tipo_material) VALUES ('TEST_ARCH00050', 'A', 1, 'MP')")
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_comercial, activo, tipo_material) VALUES ('TEST_ARCH00200', 'B', 0, 'MP')")
    try:
        r = cs.get('/api/maestro-mps/next-codigo?prefix=TEST_ARCH')
        d = r.get_json()
        assert d['siguiente_n'] == 201, \
            'archivados también deben contar para evitar reusar códigos'
    finally:
        _exec("DELETE FROM maestro_mps WHERE codigo_mp LIKE 'TEST_ARCH%'")


def test_next_codigo_ignora_codigos_no_numericos(app, db_clean):
    """Códigos sin patrón MP\\d+ (ej. 'CUSTOM-XYZ') no afectan el max."""
    cs = _login(app, 'sebastian')
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_comercial, activo, tipo_material) VALUES ('TEST_CUST00010', 'X', 1, 'MP')")
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_comercial, activo, tipo_material) VALUES ('TEST_CUSTOM-AB', 'Y', 1, 'MP')")
    try:
        r = cs.get('/api/maestro-mps/next-codigo?prefix=TEST_CUST')
        d = r.get_json()
        assert d['siguiente_n'] == 11, \
            f'el no-numérico no debe afectar · got {d["siguiente_n"]}'
    finally:
        _exec("DELETE FROM maestro_mps WHERE codigo_mp LIKE 'TEST_CUST%'")


def test_next_codigo_width_param(app, db_clean):
    """El parámetro width controla el padding."""
    cs = _login(app, 'sebastian')
    r = cs.get('/api/maestro-mps/next-codigo?prefix=ZZZ&width=3')
    d = r.get_json()
    assert d['siguiente'] == 'ZZZ001'  # 3 dígitos


def test_next_codigo_sin_login_401(client):
    r = client.get('/api/maestro-mps/next-codigo')
    assert r.status_code == 401
