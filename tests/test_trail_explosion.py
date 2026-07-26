"""Trail de explosión de fórmula (Alejandro · read-only): desglose auditable de la demanda de MP.

⚠ 26-jul: esta herramienta muestra la RECETA desglosada (código de MP + porcentaje + gramos), así
que pasó a exigir permiso INVIMA como el resto de los volcados de catálogo. Los tests usaban un
usuario común; ahora usan a Alejandro, que es de quien es la herramienta. Se agregó el caso
negativo, que es el invariante nuevo.
"""
import sys
import os
import urllib.parse

from .conftest import TEST_PASSWORD, csrf_headers

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))


def _cliente_con_permiso(app):
    """Alejandro: dueño de la herramienta y con permiso INVIMA sobre fórmulas."""
    c = app.test_client()
    r = c.post('/login', data={'username': 'alejandro', 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_sin_permiso_invima_no_ve_el_trail(app, logged_client):
    """El invariante nuevo: el desglose de la fórmula no es para cualquier usuario."""
    assert logged_client.get('/api/programacion/trail-explosion?producto=X').status_code == 403
    assert logged_client.get('/planta/trail-explosion').status_code == 403


def test_trail_page(app):
    r = _cliente_con_permiso(app).get('/planta/trail-explosion')
    assert r.status_code == 200 and b'cortex.css' in r.data and b'cx-mod-header' in r.data


def test_trail_endpoint_sin_producto(app):
    r = _cliente_con_permiso(app).get('/api/programacion/trail-explosion')
    assert r.status_code == 200
    d = r.get_json()
    assert d['ok'] is True and d['items'] == []


def test_trail_endpoint_producto_inexistente(app):
    r = _cliente_con_permiso(app).get('/api/programacion/trail-explosion?producto=NO-EXISTE-XYZ')
    assert r.status_code == 200
    d = r.get_json()
    assert d['ok'] is False and 'error' in d


def test_trail_endpoint_producto_real(app):
    """Con un producto con fórmula activa: cada ítem trae %, gramos (%×kg×1000), bodega, stock, déficit."""
    with app.app_context():
        from database import get_db
        row = get_db().execute(
            "SELECT producto_nombre FROM formula_headers WHERE COALESCE(activo,1)=1 "
            "AND (SELECT COUNT(*) FROM formula_items fi WHERE fi.producto_nombre=formula_headers.producto_nombre)>0 "
            "LIMIT 1").fetchone()
    if not row:
        return  # sin fórmulas seedeadas · nada que probar
    prod = row[0]
    d = _cliente_con_permiso(app).get('/api/programacion/trail-explosion?producto=' + urllib.parse.quote(prod)).get_json()
    assert d['ok'] is True and d['producto'] == prod and d['n'] >= 1
    it = d['items'][0]
    for k in ('material_id', 'pct', 'gramos', 'codigo_bodega', 'stock', 'pendiente', 'deficit', 'puenteado',
              'fantasma', 'infinita'):
        assert k in it
    # gramos = %/100 × kg × 1000 (%-first · M71) cuando hay %
    if it['pct'] > 0:
        esperado = round(it['pct'] / 100.0 * d['kg'] * 1000.0, 1)
        assert abs(it['gramos'] - esperado) < 1.0
    # las MP infinitas (agua · controla_stock=0 · M16) NO cuentan como déficit
    for x in d['items']:
        if x['infinita']:
            assert x['deficit'] == 0
