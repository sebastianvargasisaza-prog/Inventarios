"""Batch Record oculto hasta Part 11 (Sebastián 18-jun).

Las PÁGINAS del batch record (EBR/MBR/legajos) están detrás del flag
app_settings.brd_visible (default OCULTO). Cuando está oculto, las páginas devuelven
un aviso "en validación"; las APIs /api/brd/* siguen vivas (el historial de producción
del dashboard las usa). Reversible: poner brd_visible='1' cuando Part 11 esté lista.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _set_brd_visible(val):
    cc = sqlite3.connect(os.environ['DB_PATH'])
    cc.execute("INSERT INTO app_settings (clave, valor) SELECT 'brd_visible',? "
               "WHERE NOT EXISTS (SELECT 1 FROM app_settings WHERE clave='brd_visible')", (val,))
    cc.execute("UPDATE app_settings SET valor=? WHERE clave='brd_visible'", (val,))
    cc.commit(); cc.close()


def test_brd_oculto_pagina_da_aviso(app, db_clean):
    """Con brd_visible='0', la página /brd devuelve el aviso 'en validación' (no el módulo)."""
    cs = _login(app)
    _set_brd_visible('0')
    try:
        r = cs.get('/brd')
        assert r.status_code == 200
        assert b'validaci' in r.data, f"debe mostrar aviso de validación · {r.data[:200]}"
        assert b'Part 11' in r.data
    finally:
        _set_brd_visible('1')  # restaurar para el resto de la suite


def test_brd_oculto_api_sigue_viva(app, db_clean):
    """Aunque las páginas estén ocultas, las APIs /api/brd/* NO se gatean (el dashboard
    las usa para el historial de producción)."""
    cs = _login(app)
    _set_brd_visible('0')
    try:
        r = cs.get('/api/brd/ordenes-unificadas?fase=fabricacion')
        # no debe ser el aviso HTML · debe responder la API (200 JSON o su error propio, NO el gate)
        assert b'validaci' not in r.data or r.content_type.startswith('application/json'), \
            f"la API no debe ser gateada · {r.status_code} {r.content_type}"
    finally:
        _set_brd_visible('1')


def test_brd_visible_pagina_carga(app, db_clean):
    """Con brd_visible='1' (default de tests), /brd carga el módulo normal."""
    cs = _login(app)
    _set_brd_visible('1')
    r = cs.get('/brd')
    assert r.status_code == 200
    assert b'validaci' not in r.data or b'Part 11' not in r.data
