"""Rótulo de recepción · N rótulos por recipiente (Laura 16-jul).

Cuando una MP llega en varios recipientes individuales, el rótulo genera UNO por
recipiente con su cantidad (no uno solo por el total). Vía ?recs=1000,1000,500.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app):
    c = app.test_client()
    r = c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    assert r.status_code == 302, r.data
    return c


def _seed():
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
                     "VALUES ('MP-RECTEST','Glicerina Test','GLYCERIN',1)")
        conn.commit()
    finally:
        conn.close()


def test_un_solo_rotulo_sin_recs(app, db_clean):
    _seed()
    c = _login(app)
    r = c.get('/rotulo-recepcion/MP-RECTEST/LOTEX/4000')
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)
    assert html.count('class="sheet"') == 1, 'sin recs = 1 solo rótulo'
    assert 'Recipiente' not in html


def test_cuatro_rotulos_por_recipiente(app, db_clean):
    _seed()
    c = _login(app)
    r = c.get('/rotulo-recepcion/MP-RECTEST/LOTEX/4000?recs=1000,1000,1000,1000')
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert html.count('class="sheet"') == 4, '4 recipientes = 4 rótulos'
    assert 'Recipiente 1 de 4' in html and 'Recipiente 4 de 4' in html
    # cada hoja lleva su código de barras con id único
    assert 'id="bc0"' in html and 'id="bc3"' in html
    # cada uno muestra su cantidad (1.000 g) y referencia al total
    assert '1,000 g' in html
    assert '4,000' in html  # total en el subtítulo


def test_recipientes_desiguales(app, db_clean):
    _seed()
    c = _login(app)
    r = c.get('/rotulo-recepcion/MP-RECTEST/LOTEX/2500?recs=1000,1000,500')
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert html.count('class="sheet"') == 3
    assert '500 g' in html and '1,000 g' in html
