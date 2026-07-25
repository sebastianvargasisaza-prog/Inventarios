"""Los endpoints /diag/* son SOLO de admin (auditoría de seguridad 25-jul).

Estaban ABIERTOS A INTERNET: el hook de login solo cubre `/api/`, así que
`GET /diag/formulas-dump` sin ninguna sesión devolvía TODAS las fórmulas maestras con
código de MP, INCI y porcentaje. Verificado contra producción con un curl anónimo antes
del fix. También quedaban expuestos el maestro de MP, los MBR con sus pasos, ventas por
SKU y el plan de producción: la propiedad intelectual completa de ÁNIMUS + Espagiria.
"""
from .conftest import TEST_PASSWORD, csrf_headers

RUTAS = ['/diag/formulas-dump', '/diag/maestro-dump', '/diag/matriz-batch']


def _login(app, u):
    c = app.test_client()
    r = c.post('/login', data={'username': u, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pudo entrar %s' % u
    return c


def test_anonimo_no_ve_las_formulas(client):
    """Sin sesión: nada. 404 para no confirmarle siquiera que la ruta existe."""
    for ruta in RUTAS:
        r = client.get(ruta)
        assert r.status_code == 404, '%s quedó expuesta a anónimos (%s)' % (ruta, r.status_code)
        assert b'formulas' not in r.data.lower() or b'"error"' in r.data.lower(), \
            '%s filtró contenido' % ruta


def test_usuario_normal_tampoco(app):
    """Una operaria de planta autenticada tampoco tiene por qué bajarse el maestro."""
    c = _login(app, 'mayerlin')
    for ruta in RUTAS:
        assert c.get(ruta).status_code == 404, '%s visible para planta' % ruta


def test_admin_si_puede(app):
    """El admin conserva sus herramientas de diagnóstico."""
    c = _login(app, 'sebastian')
    r = c.get('/diag/formulas-dump')
    assert r.status_code == 200, r.data[:200]
    assert b'formulas' in r.data.lower()


def test_el_gate_no_toca_el_resto_de_la_app(client, app):
    """El filtro es solo para /diag/ · no puede romper login ni health."""
    assert client.get('/api/health').status_code == 200
    assert client.get('/login').status_code == 200
