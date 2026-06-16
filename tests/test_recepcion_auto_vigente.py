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


def test_recepcion_default_cuarentena(app, db_clean, monkeypatch):
    monkeypatch.delenv('RECEPCION_AUTO_VIGENTE', raising=False)
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
