"""Tests del flujo de autenticación: login, password change, rate limiting."""
import pytest

from .conftest import TEST_PASSWORD, csrf_headers


# ── Login ─────────────────────────────────────────────────────────────────────


def test_login_with_correct_password(client, db_clean):
    r = client.post(
        "/login",
        data={"username": "sebastian", "password": TEST_PASSWORD},
        headers=csrf_headers(),
        follow_redirects=False,
    )
    assert r.status_code == 302   # redirect


def test_login_with_wrong_password(client, db_clean):
    r = client.post(
        "/login",
        data={"username": "sebastian", "password": "incorrect"},
        headers=csrf_headers(),
        follow_redirects=False,
    )
    assert r.status_code == 200   # vuelve a login con error
    assert b"incorrect" in r.data.lower() or b"error" in r.data.lower()


def test_login_with_nonexistent_user(client, db_clean):
    r = client.post(
        "/login",
        data={"username": "fantasma", "password": "anything"},
        headers=csrf_headers(),
        follow_redirects=False,
    )
    # Mismo mensaje genérico — no revelar si el user existe
    assert r.status_code == 200


def test_logout_clears_session(client, db_clean):
    client.post(
        "/login",
        data={"username": "sebastian", "password": TEST_PASSWORD},
        headers=csrf_headers(),
        follow_redirects=False,
    )
    r = client.get("/logout")
    assert r.status_code == 302
    # Después del logout, ruta privada redirige a login
    r = client.get("/api/marketing/ads/capabilities")
    assert r.status_code == 401


# ── Rate limiting ─────────────────────────────────────────────────────────────


def test_rate_limit_locks_after_max_attempts(app, db_clean):
    """5 intentos fallidos consecutivos bloquean al user (15 min)."""
    c = app.test_client()
    # 5 intentos fallidos
    for _ in range(5):
        c.post(
            "/login",
            data={"username": "alejandro", "password": "wrong"},
            headers=csrf_headers(),
            follow_redirects=False,
        )
    # 6to intento: bloqueado
    r = c.post(
        "/login",
        data={"username": "alejandro", "password": TEST_PASSWORD},  # CORRECTA
        headers=csrf_headers(),
        follow_redirects=False,
    )
    # Debería seguir en página de login con mensaje de "demasiados intentos"
    assert r.status_code == 200
    assert b"intentos" in r.data.lower() or b"15" in r.data.lower()


def test_rate_limit_per_user_blocks_brute_force(app, db_clean):
    """Brute-force dirigido a UN user es bloqueado por el lock (IP, user)."""
    c = app.test_client()
    target = "mayra"
    for _ in range(5):
        c.post(
            "/login",
            data={"username": target, "password": f"wrong-{_}"},
            headers=csrf_headers(),
            follow_redirects=False,
        )
    # El user "mayra" queda bloqueado incluso con la password correcta
    r = c.post(
        "/login",
        data={"username": target, "password": TEST_PASSWORD},
        headers=csrf_headers(),
        follow_redirects=False,
    )
    assert r.status_code == 200   # bloqueado, no redirect


# ── Cambio de password ───────────────────────────────────────────────────────


def test_password_change_success(app, db_clean):
    """Cambio OK con password actual correcta."""
    c = app.test_client()
    c.post(
        "/login",
        data={"username": "valentina", "password": TEST_PASSWORD},
        headers=csrf_headers(),
        follow_redirects=False,
    )
    r = c.post(
        "/api/cambiar-password",
        json={
            "password_actual": TEST_PASSWORD,
            "password_nueva": "NuevaPass123",
            "password_confirmar": "NuevaPass123",
        },
        headers=csrf_headers(),
    )
    assert r.status_code == 200
    assert r.get_json().get("ok") is True


def test_password_change_then_login_with_new_password(app, db_clean):
    """Después del cambio, la NUEVA password permite login (lee de DB)."""
    c = app.test_client()
    # Login inicial con password de env var
    c.post("/login", data={"username": "felipe", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    # Cambio
    c.post("/api/cambiar-password",
           json={"password_actual": TEST_PASSWORD,
                 "password_nueva": "OtroPass456",
                 "password_confirmar": "OtroPass456"},
           headers=csrf_headers())
    c.get("/logout")
    # Re-login con la NUEVA
    r = c.post("/login", data={"username": "felipe", "password": "OtroPass456"},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302   # OK
    # Re-login con la VIEJA env var → ya no funciona
    c.get("/logout")
    r = c.post("/login", data={"username": "felipe", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 200   # fallo


def test_password_change_wrong_current(app, db_clean):
    c = app.test_client()
    c.post("/login", data={"username": "laura", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.post("/api/cambiar-password",
               json={"password_actual": "WRONG",
                     "password_nueva": "NuevaPass123",
                     "password_confirmar": "NuevaPass123"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_password_change_too_short(app, db_clean):
    c = app.test_client()
    c.post("/login", data={"username": "yuliel", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.post("/api/cambiar-password",
               json={"password_actual": TEST_PASSWORD,
                     "password_nueva": "abc",
                     "password_confirmar": "abc"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_password_change_no_letters(app, db_clean):
    c = app.test_client()
    c.post("/login", data={"username": "miguel", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.post("/api/cambiar-password",
               json={"password_actual": TEST_PASSWORD,
                     "password_nueva": "12345678",
                     "password_confirmar": "12345678"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_password_change_confirmation_mismatch(app, db_clean):
    c = app.test_client()
    c.post("/login", data={"username": "hernando", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.post("/api/cambiar-password",
               json={"password_actual": TEST_PASSWORD,
                     "password_nueva": "Pass1234",
                     "password_confirmar": "DiferentE5"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_password_change_without_session(client, db_clean):
    r = client.post("/api/cambiar-password",
                    json={"password_actual": "x", "password_nueva": "Pass1234",
                          "password_confirmar": "Pass1234"},
                    headers=csrf_headers())
    assert r.status_code == 401
