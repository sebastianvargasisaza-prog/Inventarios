"""Trail de explosión de fórmula (Alejandro · read-only): desglose auditable de la demanda de MP."""
import sys
import os
import urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))


def test_trail_page(logged_client):
    r = logged_client.get('/planta/trail-explosion')
    assert r.status_code == 200 and b'cortex.css' in r.data and b'cx-mod-header' in r.data


def test_trail_endpoint_sin_producto(logged_client):
    r = logged_client.get('/api/programacion/trail-explosion')
    assert r.status_code == 200
    d = r.get_json()
    assert d['ok'] is True and d['items'] == []


def test_trail_endpoint_producto_inexistente(logged_client):
    r = logged_client.get('/api/programacion/trail-explosion?producto=NO-EXISTE-XYZ')
    assert r.status_code == 200
    d = r.get_json()
    assert d['ok'] is False and 'error' in d


def test_trail_endpoint_producto_real(app, logged_client):
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
    d = logged_client.get('/api/programacion/trail-explosion?producto=' + urllib.parse.quote(prod)).get_json()
    assert d['ok'] is True and d['producto'] == prod and d['n'] >= 1
    it = d['items'][0]
    for k in ('material_id', 'pct', 'gramos', 'codigo_bodega', 'stock', 'pendiente', 'deficit', 'puenteado', 'fantasma'):
        assert k in it
    # gramos = %/100 × kg × 1000 (%-first · M71) cuando hay %
    if it['pct'] > 0:
        esperado = round(it['pct'] / 100.0 * d['kg'] * 1000.0, 1)
        assert abs(it['gramos'] - esperado) < 1.0
