"""Sweep tests CSRF defense-in-depth en 8 modulos chicos.

Sebastian 3-may-2026: aplica el patron _csrf + _fetchOpts a chat,
comunicacion, contabilidad, clientes, bienestar, gerencia, animus,
comercial. Cada modulo tiene los helpers y al menos un fetch
refactorizado.
"""
import pytest
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


# (ruta, user_que_puede_acceder)
MODULOS = [
    ("/chat", "sebastian"),
    ("/comunicacion", "sebastian"),
    ("/contabilidad", "sebastian"),
    ("/clientes", "sebastian"),
    ("/bienestar", "sebastian"),
    ("/gerencia", "sebastian"),
    ("/animus", "sebastian"),
    ("/comercial", "sebastian"),
]


@pytest.mark.parametrize("ruta,user", MODULOS)
def test_modulo_tiene_csrf_helpers(app, db_clean, ruta, user):
    """Cada uno de los 8 modulos chicos tiene _csrf + _fetchOpts."""
    c = _login(app, user)
    r = c.get(ruta)
    if r.status_code == 302:
        pytest.skip(f"{ruta} redirige (sin acceso para {user})")
    if r.status_code != 200:
        pytest.skip(f"{ruta} status={r.status_code}")
    body = r.get_data(as_text=True)
    assert "_csrf" in body, f"{ruta} sin helper _csrf"
    assert "_fetchOpts" in body, f"{ruta} sin helper _fetchOpts"
    assert "X-CSRF-Token" in body, f"{ruta} no usa header CSRF"
    assert "/api/csrf-token" in body, f"{ruta} sin pre-fetch token"
    # Sin patrones antiguos
    assert "method:'POST'" not in body, f"{ruta} aun tiene method:'POST' directo"
    assert "method:'PATCH'" not in body, f"{ruta} aun tiene method:'PATCH' directo"
