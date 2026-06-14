"""14-jun · División Control de Calidad (CC) vs Aseguramiento de la Calidad (AC).

Aseguramiento ahora es un módulo visible (tile en el menú) con rol propio
(ASEGURAMIENTO_USERS) y tooltips 'para qué sirve'. CC=/calidad, AC=/aseguramiento.
"""


def test_aseguramiento_en_menu_modulos(admin_client):
    body = admin_client.get('/modulos').get_data(as_text=True)
    assert 'href="/aseguramiento"' in body, 'Aseguramiento debe estar en el menú'
    assert '>Aseguramiento<' in body
    # Calidad relabelado a Control de Calidad
    assert '>Control de Calidad<' in body


def test_aseguramiento_page_accesible_calidad(admin_client):
    r = admin_client.get('/aseguramiento')
    assert r.status_code == 200, r.data[:200]
    body = r.get_data(as_text=True)
    assert 'data-tip' in body or '[data-tip]' in body, 'tooltips para-qué-sirve inyectados'


def test_aseguramiento_page_bloquea_no_calidad(logged_client):
    # valentina no es calidad/aseguramiento/admin → sin acceso
    r = logged_client.get('/aseguramiento')
    body = r.get_data(as_text=True)
    assert ('cceso' in body or r.status_code in (302, 403)), 'no-AC no debe entrar al módulo'


def test_rol_aseguramiento_existe():
    from config import ASEGURAMIENTO_USERS, CALIDAD_USERS
    assert 'miguel' in ASEGURAMIENTO_USERS, 'Miguel debe ser Aseguramiento'
    assert 'miguel' not in CALIDAD_USERS, 'Miguel ya no es Control de Calidad'
    assert 'laura' in CALIDAD_USERS, 'Laura sigue en Control de Calidad'


def test_division_acceso_miguel_si_laura_no(app):
    from .conftest import TEST_PASSWORD, csrf_headers
    # Miguel (Aseguramiento) entra
    cm = app.test_client()
    cm.post('/login', data={'username': 'miguel', 'password': TEST_PASSWORD}, headers=csrf_headers())
    assert cm.get('/aseguramiento').status_code == 200
    # Laura (Control de Calidad) NO entra a Aseguramiento (cargos divididos)
    cl = app.test_client()
    cl.post('/login', data={'username': 'laura', 'password': TEST_PASSWORD}, headers=csrf_headers())
    body = cl.get('/aseguramiento').get_data(as_text=True)
    assert 'cceso' in body, 'CC no debe entrar a Aseguramiento (división de cargos)'
    # ...pero Laura SÍ entra a Control de Calidad
    assert cl.get('/calidad').status_code == 200
