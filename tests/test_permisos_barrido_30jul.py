"""Tres endpoints que mutaban sin permiso de rol (barrido 30-jul).

El barrido encontró 36 endpoints que mutan tablas sensibles sin guard visible. Casi todos son
de planta, donde la política es deliberada ("lo hacen todos"). Los tres que NO son de planta se
gatearon con criterio de **proporcionalidad**: el permiso va donde está el peligro, sin trabar
la operación diaria (M68 · un gate que frena lo cotidiano es una traba fantasma).

  · `rechazar_oc` → guard estándar de mutaciones de COMPRAS. Rechazar cambia el estado de la OC
    y libera las SOL; el hermano `autorizar_oc` ya gateaba, y esa asimetría es la firma de M45.
  · `api_maquila_facturar` → **contadora o dirección**. Generar una factura alimenta `facturas`
    y después `flujo_ingresos`: es un acto financiero.
  · `mee_import_bulk` → planta sigue cargando envases (es su día a día), pero
    **`modo='replace'`, que ARCHIVA en masa lo que no venga en el archivo, es de dirección**.

Cada caso se prueba en los DOS sentidos: ampliar o poner un permiso sin probar el borde es
cambiar un control por una puerta (o por una traba).
"""
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pudo entrar %s' % user
    return c


def _h():
    h = {'Content-Type': 'application/json'}
    h.update(csrf_headers())
    return h


# ══ rechazar OC ═════════════════════════════════════════════════════════════════

def test_rechazar_oc_no_lo_hace_planta(app, db_clean):
    """Una operaria de dispensación no decide sobre una orden de compra."""
    r = _login(app, 'mayerlin').post('/api/compras/oc/OC-NO-EXISTE/rechazar', headers=_h(),
                                     json={'motivo': 'test'})
    assert r.status_code == 403, r.data[:250]


def test_rechazar_oc_si_lo_hace_compras(app, db_clean):
    """Dientes del otro lado: Catalina sí puede (pasa el guard y llega al 404 de la OC)."""
    r = _login(app, 'catalina').post('/api/compras/oc/OC-NO-EXISTE/rechazar', headers=_h(),
                                     json={'motivo': 'test'})
    assert r.status_code != 403, 'el guard dejó afuera a compras: %s' % r.data[:250]
    assert r.status_code == 404, r.data[:250]


# ══ facturar maquila ════════════════════════════════════════════════════════════

def test_facturar_maquila_no_lo_hace_planta(app, db_clean):
    r = _login(app, 'mayerlin').post('/api/maquila/ordenes/999999/facturar', headers=_h(), json={})
    assert r.status_code == 403, r.data[:250]
    assert (r.get_json() or {}).get('codigo') == 'SOLO_CONTABILIDAD'


def test_facturar_maquila_si_lo_hace_direccion(app, db_clean):
    """Pasa el guard y muere en el 404 de la orden inexistente, que es lo correcto."""
    r = _login(app, 'sebastian').post('/api/maquila/ordenes/999999/facturar', headers=_h(), json={})
    assert r.status_code != 403, 'el guard dejó afuera a dirección: %s' % r.data[:250]


# ══ import masivo de envases ════════════════════════════════════════════════════

def test_planta_sigue_pudiendo_cargar_envases(app, db_clean):
    """Lo cotidiano NO se traba: el upsert es como planta carga los envases."""
    r = _login(app, 'mayerlin').post('/api/mee/import-bulk', headers=_h(), json={
        'items': [{'codigo': 'ZZ-IMP-1', 'descripcion': 'Envase de prueba import',
                   'categoria': 'Envase', 'stock': 0}],
        'modo': 'upsert'})
    assert r.status_code in (200, 201), r.data[:300]
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.cursor().execute("DELETE FROM maestro_mee WHERE codigo='ZZ-IMP-1'")
        conn.commit()


def test_el_replace_que_archiva_en_masa_es_de_direccion(app, db_clean):
    """`replace` archiva TODO lo que no venga en el archivo: eso no es una carga, es una
    reescritura del maestro."""
    r = _login(app, 'mayerlin').post('/api/mee/import-bulk', headers=_h(), json={
        'items': [{'codigo': 'ZZ-IMP-2', 'descripcion': 'x', 'categoria': 'Envase', 'stock': 0}],
        'modo': 'replace'})
    assert r.status_code == 403, r.data[:300]
    assert (r.get_json() or {}).get('codigo') == 'REPLACE_SOLO_ADMIN'


def test_direccion_si_puede_hacer_el_replace(app, db_clean):
    """Dientes: el permiso existe para quien debe tenerlo."""
    r = _login(app, 'sebastian').post('/api/mee/import-bulk', headers=_h(), json={
        'items': [{'codigo': 'ZZ-IMP-3', 'descripcion': 'Envase replace admin',
                   'categoria': 'Envase', 'stock': 0}],
        'modo': 'upsert'})       # upsert, para no archivar el maestro de la BD de tests
    assert r.status_code in (200, 201), r.data[:300]
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.cursor().execute("DELETE FROM maestro_mee WHERE codigo='ZZ-IMP-3'")
        conn.commit()
