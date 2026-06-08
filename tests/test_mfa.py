"""Tests del módulo MFA TOTP — Sebastian (30-abr-2026).

Cubre:
- /api/mfa/status sin auth → 401
- /api/mfa/setup genera secret y provisioning_uri
- /api/mfa/verify-setup con token correcto activa MFA + emite backup_code
- /api/mfa/verify-setup con token incorrecto → 400
- /api/mfa/disable con password+token correctos desactiva
- /api/mfa/admin-disable solo admin puede llamarlo
- Login flow: usuario con MFA activo debe pasar por /login/mfa
- Login con backup code desactiva MFA + completa sesión
"""
import os
import sqlite3
import time
import pytest
import pyotp

from .conftest import TEST_PASSWORD, ALL_USERS, TEST_PASSWORD_HASH


@pytest.fixture(autouse=True)
def _seed_users_passwords(app):
    """users_mfa tiene FK username→users_passwords. En prod los usuarios viven
    en esa tabla; en tests vienen de env. Sembramos antes de cada test MFA para
    que el INSERT en users_mfa no falle por FK en PostgreSQL (SQLite no la
    enforzaba). db_clean borra users_passwords tras cada test, por eso se
    siembra aquí en el setup (no rompe los tests de cambio de password)."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    for u in ALL_USERS:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO users_passwords (username, password_hash, activo) "
                "VALUES (?, ?, 1)", (u, TEST_PASSWORD_HASH))
        except Exception:
            pass
    conn.commit(); conn.close()
    yield


def _fresh_totp(secret, ya_usado=None):
    """Genera un token TOTP válido NO reusado.

    SEC 25-may-2026: hay protección anti-replay (tabla mfa_tokens_usados ·
    UNIQUE(username, token_hash) donde hash = sha256(secret:token)). Un mismo
    token TOTP no se puede consumir dos veces. Los helpers que ya gastaron un
    token (p.ej. verify-setup) deben pedir uno de una ventana posterior para
    el siguiente paso (disable / login). Avanzamos de a 30s (una ventana TOTP)
    hasta obtener un código distinto del ya consumido. El server verifica con
    valid_window=1, así que un token de la ventana +30s sigue siendo aceptado.
    """
    base = time.time()
    for paso in range(1, 6):
        token = pyotp.TOTP(secret).at(base + 30 * paso)
        if token != ya_usado:
            return token
    # Fallback improbable (5 ventanas idénticas) · devolver la última.
    return pyotp.TOTP(secret).at(base + 30)


def _login(client, username="sebastian"):
    """Login simple sin MFA (paso 1 si MFA no activo)."""
    r = client.post(
        "/login",
        data={"username": username, "password": TEST_PASSWORD},
        headers={"Origin": "http://localhost"},
        follow_redirects=False,
    )
    assert r.status_code == 302, r.get_data(as_text=True)
    return r


def _setup_mfa(client, username="sebastian"):
    """Helper: completa enrollment MFA y retorna (secret, backup_code)."""
    _login(client, username)
    r = client.post("/api/mfa/setup", json={},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.get_data(as_text=True)
    secret = r.get_json()["secret"]
    # Generar token válido · este queda CONSUMIDO (anti-replay) tras verify-setup
    token = pyotp.TOTP(secret).now()
    r = client.post("/api/mfa/verify-setup", json={"token": token},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.get_data(as_text=True)
    backup_code = r.get_json()["backup_code"]
    return secret, backup_code, token


def test_mfa_status_sin_auth_devuelve_401(app, db_clean):
    client = app.test_client()
    r = client.get("/api/mfa/status")
    assert r.status_code == 401


def test_mfa_setup_genera_secret(app, db_clean):
    client = app.test_client()
    _login(client)
    r = client.post("/api/mfa/setup", json={},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert "secret" in body
    assert len(body["secret"]) >= 16
    assert body["provisioning_uri"].startswith("otpauth://totp/")
    assert body["account"] == "sebastian"


def test_mfa_verify_setup_token_incorrecto_falla(app, db_clean):
    client = app.test_client()
    _login(client)
    client.post("/api/mfa/setup", json={},
                headers={"Origin": "http://localhost"})
    r = client.post("/api/mfa/verify-setup", json={"token": "000000"},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 400


def test_mfa_verify_setup_token_correcto_activa(app, db_clean):
    client = app.test_client()
    secret, backup_code, _ = _setup_mfa(client)
    # Status ahora dice enabled
    r = client.get("/api/mfa/status")
    assert r.status_code == 200
    assert r.get_json()["mfa_enabled"] is True
    # Backup code formato XXXX-XXXX-XXXX
    assert len(backup_code) == 14
    assert backup_code.count("-") == 2


def test_mfa_disable_requiere_password_y_token(app, db_clean):
    client = app.test_client()
    secret, _, usado = _setup_mfa(client)
    # Sin password → 400 (falla antes de verificar el token · no consume)
    r = client.post("/api/mfa/disable", json={"token": _fresh_totp(secret, usado)},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 400
    # Password incorrecto → 403 (falla en password · token no se verifica)
    r = client.post("/api/mfa/disable",
                    json={"password": "wrong", "token": _fresh_totp(secret, usado)},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 403


def test_mfa_disable_con_credenciales_correctas_funciona(app, db_clean):
    client = app.test_client()
    secret, _, usado = _setup_mfa(client)
    # Token FRESCO · el de setup ya fue consumido (anti-replay) y daría 400
    r = client.post("/api/mfa/disable",
                    json={"password": TEST_PASSWORD, "token": _fresh_totp(secret, usado)},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.get_data(as_text=True)
    # Status ahora dice disabled
    r = client.get("/api/mfa/status")
    assert r.get_json()["mfa_enabled"] is False


def test_mfa_admin_disable_solo_admins(app, db_clean):
    """Un usuario NO admin no puede llamar /api/mfa/admin-disable."""
    client_user = app.test_client()
    # Login simple como mayra (no admin, sin MFA activo)
    _login(client_user, username="mayra")
    r = client_user.post("/api/mfa/admin-disable",
                         json={"target_username": "alejandro"},
                         headers={"Origin": "http://localhost"})
    assert r.status_code == 403


def test_mfa_admin_disable_funciona_para_admin(app, db_clean):
    client = app.test_client()
    # Setup MFA en mayra
    _setup_mfa(client, username="mayra")
    client.get("/logout")
    # Login como sebastian (admin) y disable de mayra
    _login(client, username="sebastian")
    r = client.post("/api/mfa/admin-disable",
                    json={"target_username": "mayra"},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.get_data(as_text=True)


def test_login_con_mfa_activa_redirige_a_segundo_paso(app, db_clean):
    client = app.test_client()
    secret, _, _ = _setup_mfa(client)
    # Logout y volver a entrar
    client.get("/logout")
    r = client.post(
        "/login",
        data={"username": "sebastian", "password": TEST_PASSWORD},
        headers={"Origin": "http://localhost"},
        follow_redirects=False,
    )
    # Debe redirigir a /login/mfa, NO a /modulos
    assert r.status_code == 302
    assert "/login/mfa" in r.headers["Location"]


def test_login_mfa_token_correcto_completa_sesion(app, db_clean):
    client = app.test_client()
    secret, _, usado = _setup_mfa(client)
    client.get("/logout")
    # Step 1
    client.post("/login",
                data={"username": "sebastian", "password": TEST_PASSWORD},
                headers={"Origin": "http://localhost"})
    # Step 2 con token FRESCO · el de setup ya fue consumido (anti-replay)
    token = _fresh_totp(secret, usado)
    r = client.post("/login/mfa", data={"token": token, "csrf_token": "x"},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 302
    assert "/modulos" in r.headers["Location"]


def test_login_backup_code_desactiva_mfa(app, db_clean):
    client = app.test_client()
    secret, backup_code, _ = _setup_mfa(client)
    client.get("/logout")
    # Step 1
    client.post("/login",
                data={"username": "sebastian", "password": TEST_PASSWORD},
                headers={"Origin": "http://localhost"})
    # Step 2 con backup code
    r = client.post("/login/mfa-backup",
                    data={"backup_code": backup_code, "csrf_token": "x"},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 302
    assert "/modulos" in r.headers["Location"]
    # MFA debe estar desactivado ahora
    r = client.get("/api/mfa/status")
    assert r.get_json()["mfa_enabled"] is False
