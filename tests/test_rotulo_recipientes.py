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


def test_fecha_formato_largo_espanol(app, db_clean):
    """Las fechas del rótulo salen '08 JULIO 2026' (día + mes palabra en español · Sebastián 18-jul)."""
    _seed()
    from datetime import date
    meses = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO',
             'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']
    hoy_largo = '%02d %s %d' % (date.today().day, meses[date.today().month - 1], date.today().year)
    c = _login(app)
    r = c.get('/rotulo-recepcion/MP-RECTEST/LOTEX/2000')
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    # F. Impresion usa la fecha de hoy en formato largo español
    assert hoy_largo in html, f"fecha larga español no aparece · esperaba {hoy_largo}"
    # el formato viejo '-JUL-' (abreviado con guiones) ya no debe salir
    assert date.today().strftime('%d-%b-%Y').upper() not in html


def test_vencimiento_formato_largo(app, db_clean):
    """El vencimiento del lote también sale en formato largo español."""
    import os, sqlite3
    _seed()
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    conn.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
                 "fecha_vencimiento, estado_lote) VALUES ('MP-RECTEST','Glicerina Test',2000,'Entrada',"
                 "date('now'),'LOTEV','2027-01-15','VIGENTE')")
    conn.commit(); conn.close()
    c = _login(app)
    r = c.get('/rotulo-recepcion/MP-RECTEST/LOTEV/2000')
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert '15 ENERO 2027' in html, 'vencimiento en formato largo español'
