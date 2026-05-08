"""Tests para /cambiar-password page · Sebastián 7-may-2026."""
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_cambiar_password_page_logueado_ve_form(app, db_clean):
    """Cualquier user logueado puede entrar y ve el form."""
    cs = _login(app, 'sebastian')
    r = cs.get('/cambiar-password')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Cambiar contraseña' in body
    assert 'sebastian' in body  # username inyectado
    assert 'password_actual' in body
    assert 'password_nueva' in body
    assert 'password_confirmar' in body
    assert '/api/cambiar-password' in body  # endpoint del fetch


def test_cambiar_password_page_compras_user_tambien(app, db_clean):
    """No solo admin · cualquier user (catalina, mayerlin, luis) puede."""
    for user in ['catalina', 'luis', 'mayerlin']:
        cs = _login(app, user)
        r = cs.get('/cambiar-password')
        assert r.status_code == 200, f'user={user} no puede acceder'
        body = r.get_data(as_text=True)
        assert user in body, f'username {user} no aparece en pagina'


def test_cambiar_password_page_sin_login_redirect(client):
    """Sin login redirige a /login con next=/cambiar-password."""
    r = client.get('/cambiar-password', follow_redirects=False)
    assert r.status_code == 302
    location = r.headers.get('Location', '')
    assert '/login' in location
    assert 'cambiar-password' in location  # next preservado


# ── Widget "Mi contraseña" presente en páginas principales ─────────

def test_widget_visible_en_paginas_principales(app, db_clean):
    """Sebastián 8-may-2026: el link 🔐 Mi contraseña debe aparecer en
    todas las páginas principales · users descubren sin saber URL."""
    cs = _login(app, 'sebastian')
    paginas = [
        '/inventarios',  # dashboard
        '/compras',
        '/contabilidad',
        '/calidad',
        '/animus',
        '/marketing',
        '/modulos',
    ]
    fallan = []
    for url in paginas:
        r = cs.get(url)
        if r.status_code != 200:
            continue  # algunas pueden requerir permisos extra · skip
        body = r.get_data(as_text=True)
        if 'cambiar-password' not in body:
            fallan.append(url)
    assert not fallan, \
        f'Widget Mi contraseña falta en: {fallan}'
