"""Tests del CSRF token explícito (defense in depth sobre Origin check)."""
from .conftest import TEST_PASSWORD, csrf_headers


def test_csrf_token_endpoint_requires_auth(client, db_clean):
    r = client.get("/api/csrf-token")
    assert r.status_code == 401


def test_csrf_token_endpoint_returns_token(admin_client, db_clean):
    r = admin_client.get("/api/csrf-token")
    assert r.status_code == 200
    data = r.get_json()
    assert "csrf_token" in data
    assert isinstance(data["csrf_token"], str)
    assert len(data["csrf_token"]) > 20  # ≥32 chars urlsafe


def test_csrf_token_stable_within_session(admin_client, db_clean):
    """Múltiples calls a /api/csrf-token devuelven el mismo token."""
    t1 = admin_client.get("/api/csrf-token").get_json()["csrf_token"]
    t2 = admin_client.get("/api/csrf-token").get_json()["csrf_token"]
    assert t1 == t2


def test_csrf_token_rotates_on_login(app, db_clean):
    """Tras login fresh, el token cambia (rotación)."""
    c = app.test_client()
    c.post("/login", data={"username": "valentina", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    t1 = c.get("/api/csrf-token").get_json()["csrf_token"]

    c.get("/logout")
    c.post("/login", data={"username": "valentina", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    t2 = c.get("/api/csrf-token").get_json()["csrf_token"]
    assert t1 != t2


def test_post_without_token_still_works(admin_client, db_clean):
    """Compatibilidad: POST sin X-CSRF-Token sigue funcionando (Origin check pasa)."""
    r = admin_client.post("/api/admin/backup-now", headers=csrf_headers())
    assert r.status_code == 200


def test_post_with_valid_token_works(admin_client, db_clean):
    """POST con X-CSRF-Token válido pasa los 2 checks."""
    token = admin_client.get("/api/csrf-token").get_json()["csrf_token"]
    r = admin_client.post(
        "/api/admin/backup-now",
        headers={**csrf_headers(), "X-CSRF-Token": token},
    )
    assert r.status_code == 200


def test_post_with_invalid_token_blocked(admin_client, db_clean):
    """POST con X-CSRF-Token inválido es 403 — defense in depth."""
    r = admin_client.post(
        "/api/admin/backup-now",
        headers={**csrf_headers(), "X-CSRF-Token": "fake-token-not-in-session"},
    )
    assert r.status_code == 403
    assert "csrf" in (r.get_json().get("error") or "").lower()


def test_post_with_empty_token_treated_as_missing(admin_client, db_clean):
    """X-CSRF-Token vacío = como si no se enviara → no se valida."""
    r = admin_client.post(
        "/api/admin/backup-now",
        headers={**csrf_headers(), "X-CSRF-Token": ""},
    )
    assert r.status_code == 200


def test_get_does_not_validate_csrf_token(admin_client, db_clean):
    """GET no se chequea aunque envíe token inválido (idempotente)."""
    r = admin_client.get(
        "/api/admin/backups",
        headers={"X-CSRF-Token": "garbage"},
    )
    assert r.status_code == 200
