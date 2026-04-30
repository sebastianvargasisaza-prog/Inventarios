"""Smoke test por blueprint — Sebastian (30-abr-2026): "smoke tests por blueprint".

Cada blueprint debe responder 200 (o redirect razonable) en su URL principal
con sesión admin. Si alguien rompe un blueprint con un import error o
template missing, este test lo pilla en CI antes que un usuario.

Cobertura: 21 blueprints × URL principal cada uno = 21 smoke checks.

NOTA: estos NO son tests funcionales — solo verifican que la página
carga sin 500. Tests funcionales viven en test_<blueprint>.py específicos.
"""
import pytest

from .conftest import TEST_PASSWORD


# Mapeo blueprint → URL principal HTML (lista canónica de "carga la página").
# Si tu blueprint nuevo no está aquí, agrégalo.
# Blueprints con vista HTML directa
BLUEPRINT_HTML_URLS = [
    ("hub_modulos",       "/modulos"),
    ("hub_compromisos",   "/compromisos"),
    ("core_planta",       "/planta"),
    ("compras_solicitudes","/solicitudes"),
    ("clientes",          "/clientes"),
    ("gerencia",          "/gerencia"),
    ("financiero",        "/financiero"),
    ("contabilidad",      "/contabilidad"),
    ("maquila",           "/hub-salida"),
    ("despachos",         "/recepcion"),
    ("rrhh",              "/rrhh"),
    ("calidad",           "/calidad"),
    ("tecnica",           "/tecnica"),
    ("marketing",         "/marketing"),
    ("animus",            "/animus"),
    ("espagiria",         "/espagiria"),
    ("comunicacion",      "/comunicacion"),
    ("admin",             "/admin"),
    ("chat",              "/chat"),
    ("bienestar",         "/bienestar"),
]

# Blueprints API-only — testeamos con un endpoint GET que YA existe
# y devuelve JSON. Verifica que el blueprint registrado responde.
BLUEPRINT_API_URLS = [
    ("inventario",   "/api/inventario"),
    ("programacion", "/api/programacion/resumen"),
]


@pytest.mark.parametrize("blueprint,url", BLUEPRINT_HTML_URLS)
def test_blueprint_carga_con_admin(app, db_clean, blueprint, url):
    """Cada blueprint debe responder 200/302/304 con sesión admin sebastian."""
    client = app.test_client()
    # Login como admin
    r = client.post(
        "/login",
        data={"username": "sebastian", "password": TEST_PASSWORD},
        headers={"Origin": "http://localhost"},
        follow_redirects=False,
    )
    assert r.status_code == 302, f"Login falló (precondición): {r.status_code}"

    # Cargar la URL del blueprint
    r = client.get(url, follow_redirects=False)
    # Aceptamos:
    #   200 - página carga directo
    #   302/303 - redirect (ej: a sub-ruta default, o a /modulos por permisos)
    #   304 - not modified (cacheada)
    # NO aceptamos:
    #   500 - server error
    #   404 - ruta no registrada
    #   401 - auth roto (login no funcionó)
    assert r.status_code in (200, 302, 303, 304), (
        f"[{blueprint}] {url} retornó {r.status_code} con admin sebastian. "
        f"Response: {r.get_data(as_text=True)[:300]}"
    )


@pytest.mark.parametrize("blueprint,url", BLUEPRINT_API_URLS)
def test_blueprint_api_carga_con_admin(app, db_clean, blueprint, url):
    """Blueprints API-only deben responder con sesión admin."""
    client = app.test_client()
    client.post(
        "/login",
        data={"username": "sebastian", "password": TEST_PASSWORD},
        headers={"Origin": "http://localhost"},
    )
    r = client.get(url)
    assert r.status_code in (200, 304), (
        f"[{blueprint}] {url} retornó {r.status_code}. Body: {r.get_data(as_text=True)[:200]}"
    )


def test_modulos_lista_modulos_principales(app, db_clean):
    """/modulos es el hub central. Debe linkear a los módulos principales."""
    client = app.test_client()
    client.post(
        "/login",
        data={"username": "sebastian", "password": TEST_PASSWORD},
        headers={"Origin": "http://localhost"},
    )
    r = client.get("/modulos")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    # Módulos clave que un admin debe poder navegar desde /modulos.
    # Solo testeamos los que SON páginas HTML (no API blueprints).
    # Hub muestra al menos los módulos comerciales clave para admins
    expected_links = ["/clientes", "/calidad", "/gerencia", "/marketing"]
    missing = [link for link in expected_links if link not in body]
    assert not missing, f"/modulos no linkea a: {missing}"


def test_login_redirect_to_next_funciona(app, db_clean):
    """Login con ?next= debe redirigir a la URL pedida tras autenticarse."""
    client = app.test_client()
    r = client.post(
        "/login?next=/marketing",
        data={"username": "sebastian", "password": TEST_PASSWORD},
        headers={"Origin": "http://localhost"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "/marketing" in r.headers.get("Location", "")
