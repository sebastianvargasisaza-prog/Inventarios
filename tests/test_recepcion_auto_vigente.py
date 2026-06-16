"""16-jun · Interruptor RECEPCION_AUTO_VIGENTE.

Sebastián (día de inventario): "las recepciones no necesiten de calidad para
ingresar, que no pasen por cuarentena sino que carguen automático."

Interruptor reversible (config.recepcion_auto_vigente · env RECEPCION_AUTO_VIGENTE):
  - OFF (default INVIMA): la mercancía recibida entra en CUARENTENA (espera QC).
  - ON: entra como VIGENTE directo (disponible, sin pasar por Calidad).

Cubre el ingreso manual (/api/recepcion). La recepción de OC comparte el mismo
helper de config.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, u='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': u, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _estado_lote(lote):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        r = conn.execute(
            "SELECT estado_lote FROM movimientos WHERE lote=? ORDER BY id DESC LIMIT 1",
            (lote,)).fetchone()
        return r[0] if r else None
    finally:
        conn.close()


def _clear_modo_inv():
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("DELETE FROM app_settings WHERE clave='recepcion_auto_vigente'")
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def test_modo_inventario_toggle_db_controla_recepcion(app, db_clean, monkeypatch):
    """El toggle en BD (botón UI · sin Render) manda sobre el env. Encenderlo hace
    que la recepción entre VIGENTE aunque el env esté apagado."""
    monkeypatch.setenv('RECEPCION_AUTO_VIGENTE', '0')  # env apagado
    _clear_modo_inv()
    c = _login(app, 'sebastian')  # admin
    try:
        # Estado inicial: apagado (env 0, sin fila BD)
        g0 = c.get('/api/inventario/modo-inventario')
        assert g0.status_code == 200 and g0.get_json()['activo'] is False
        # Encender por BD
        p = c.post('/api/inventario/modo-inventario', json={'activo': True}, headers=csrf_headers())
        assert p.status_code == 200 and p.get_json()['activo'] is True
        assert c.get('/api/inventario/modo-inventario').get_json()['activo'] is True
        # Ahora la recepción entra VIGENTE pese al env apagado
        r = c.post('/api/recepcion', json={
            'codigo_mp': 'MPTESTDBTG', 'cantidad': 300, 'lote': 'LOTE-DBTG-1',
            'nombre_inci': 'Test DB Toggle', 'nombre_comercial': 'Test DBTG'},
            headers=csrf_headers())
        assert r.status_code in (200, 201), r.data[:300]
        assert _estado_lote('LOTE-DBTG-1') == 'VIGENTE'
        # Apagar de nuevo
        p2 = c.post('/api/inventario/modo-inventario', json={'activo': False}, headers=csrf_headers())
        assert p2.status_code == 200 and p2.get_json()['activo'] is False
    finally:
        _clear_modo_inv()


def test_modo_inventario_post_requiere_admin(app, db_clean, monkeypatch):
    _clear_modo_inv()
    c = _login(app, 'valentina')  # no admin
    r = c.post('/api/inventario/modo-inventario', json={'activo': True}, headers=csrf_headers())
    assert r.status_code == 403, r.data[:200]
    _clear_modo_inv()


def test_recepcion_off_cuarentena(app, db_clean, monkeypatch):
    # Con el interruptor APAGADO se restaura la posición INVIMA (cuarentena-first).
    # NOTA 16-jun: el default del código está TEMPORALMENTE en ON (día de
    # inventario), por eso este test fuerza '0' para verificar la ruta cuarentena.
    monkeypatch.setenv('RECEPCION_AUTO_VIGENTE', '0')
    c = _login(app)
    r = c.post('/api/recepcion', json={
        'codigo_mp': 'MPTESTCUAR', 'cantidad': 1000, 'lote': 'LOTE-CUAR-1',
        'nombre_inci': 'Test Cuarentena INCI', 'nombre_comercial': 'Test Cuar'},
        headers=csrf_headers())
    assert r.status_code in (200, 201), r.data[:300]
    assert _estado_lote('LOTE-CUAR-1') == 'CUARENTENA'


def test_recepcion_auto_vigente_on(app, db_clean, monkeypatch):
    monkeypatch.setenv('RECEPCION_AUTO_VIGENTE', '1')
    c = _login(app)
    r = c.post('/api/recepcion', json={
        'codigo_mp': 'MPTESTVIG', 'cantidad': 1000, 'lote': 'LOTE-VIG-1',
        'nombre_inci': 'Test Vigente INCI', 'nombre_comercial': 'Test Vig'},
        headers=csrf_headers())
    assert r.status_code in (200, 201), r.data[:300]
    # Con el interruptor encendido, carga disponible directo (sin cuarentena).
    assert _estado_lote('LOTE-VIG-1') == 'VIGENTE'


def _seed_cuarentena(lote):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute(
            "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote, operador) "
            "VALUES (?,?,?,?,?,?, 'CUARENTENA', ?)",
            ('MPSEED1', 'Seed Cuar', 500, 'Entrada', '2026-06-16', lote, 'sebastian'))
        conn.commit()
        return conn.execute("SELECT id FROM movimientos WHERE lote=? ORDER BY id DESC LIMIT 1", (lote,)).fetchone()[0]
    finally:
        conn.close()


def test_liberar_inventario_admin_switch_on(app, db_clean, monkeypatch):
    monkeypatch.setenv('RECEPCION_AUTO_VIGENTE', '1')
    mid = _seed_cuarentena('LOTE-LIB-1')
    c = _login(app, 'sebastian')  # admin
    r = c.post('/api/lotes/cuarentena/liberar-inventario', json={}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert r.get_json()['liberados'] >= 1
    assert _estado_lote('LOTE-LIB-1') == 'VIGENTE'


def test_liberar_inventario_switch_off_409(app, db_clean, monkeypatch):
    monkeypatch.setenv('RECEPCION_AUTO_VIGENTE', '0')
    _seed_cuarentena('LOTE-LIB-2')
    c = _login(app, 'sebastian')
    r = c.post('/api/lotes/cuarentena/liberar-inventario', json={}, headers=csrf_headers())
    assert r.status_code == 409, r.data[:200]
    assert _estado_lote('LOTE-LIB-2') == 'CUARENTENA'  # no tocado


def test_liberar_inventario_requiere_admin(app, db_clean, monkeypatch):
    monkeypatch.setenv('RECEPCION_AUTO_VIGENTE', '1')
    c = _login(app, 'valentina')  # no admin
    r = c.post('/api/lotes/cuarentena/liberar-inventario', json={}, headers=csrf_headers())
    assert r.status_code == 403, r.data[:200]


def test_recepcion_explicito_gana_sobre_default(app, db_clean, monkeypatch):
    """Si el operario marca cuarentena explícitamente, se respeta aun con el
    interruptor encendido (el explícito manda)."""
    monkeypatch.setenv('RECEPCION_AUTO_VIGENTE', '1')
    c = _login(app)
    r = c.post('/api/recepcion', json={
        'codigo_mp': 'MPTESTEXP', 'cantidad': 500, 'lote': 'LOTE-EXP-1',
        'cuarentena': True,
        'nombre_inci': 'Test Exp INCI', 'nombre_comercial': 'Test Exp'},
        headers=csrf_headers())
    assert r.status_code in (200, 201), r.data[:300]
    assert _estado_lote('LOTE-EXP-1') == 'CUARENTENA'
