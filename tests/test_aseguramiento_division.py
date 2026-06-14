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
    from config import ASEGURAMIENTO_USERS
    assert isinstance(ASEGURAMIENTO_USERS, set) and ASEGURAMIENTO_USERS, 'ASEGURAMIENTO_USERS debe existir'
