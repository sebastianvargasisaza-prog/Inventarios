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
import sqlite3
import pytest
import pyotp

from .conftest import TEST_PASSWORD


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
    # Generar token válido
    token = pyotp.TOTP(secret).now()
    r = client.post("/api/mfa/verify-setup", json={"token": token},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.get_data(as_text=True)
    backup_code = r.get_json()["backup_code"]
    return secret, backup_code


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
    secret, backup_code = _setup_mfa(client)
    # Status ahora dice enabled
    r = client.get("/api/mfa/status")
    assert r.status_code == 200
    assert r.get_json()["mfa_enabled"] is True
    # Backup code formato XXXX-XXXX-XXXX
    assert len(backup_code) == 14
    assert backup_code.count("-") == 2


def test_mfa_disable_requiere_password_y_token(app, db_clean):
    client = app.test_client()
    secret, _ = _setup_mfa(client)
    # Sin password → 400
    r = client.post("/api/mfa/disable", json={"token": pyotp.TOTP(secret).now()},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 400
    # Password incorrecto → 403
    r = client.post("/api/mfa/disable",
                    json={"password": "wrong", "token": pyotp.TOTP(secret).now()},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 403


def test_mfa_disable_con_credenciales_correctas_funciona(app, db_clean):
    client = app.test_client()
    secret, _ = _setup_mfa(client)
    r = client.post("/api/mfa/disable",
                    json={"password": TEST_PASSWORD, "token": pyotp.TOTP(secret).now()},
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
    secret, _ = _setup_mfa(client)
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
    secret, _ = _setup_mfa(client)
    client.get("/logout")
    # Step 1
    client.post("/login",
                data={"username": "sebastian", "password": TEST_PASSWORD},
                headers={"Origin": "http://localhost"})
    # Step 2 con token correcto
    token = pyotp.TOTP(secret).now()
    r = client.post("/login/mfa", data={"token": token, "csrf_token": "x"},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 302
    assert "/modulos" in r.headers["Location"]


def test_login_backup_code_desactiva_mfa(app, db_clean):
    client = app.test_client()
    secret, backup_code = _setup_mfa(client)
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
