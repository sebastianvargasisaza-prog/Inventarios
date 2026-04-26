"""Tests del CSRF light (Origin/Referer check)."""
from .conftest import TEST_PASSWORD


def test_get_does_not_require_origin(admin_client):
    """GET no chequea Origin (es idempotente por contrato HTTP)."""
    r = admin_client.get("/api/admin/backups")
    assert r.status_code == 200


def test_post_with_malicious_origin_blocked(admin_client):
    """POST con Origin de otro host → 403."""
    r = admin_client.post(
        "/api/admin/backup-now",
        headers={"Origin": "https://evil-site.example.com"},
    )
    assert r.status_code == 403


def test_post_with_same_host_origin_passes(admin_client):
    """POST con Origin same-host pasa el check (puede fallar por otra razón)."""
    r = admin_client.post(
        "/api/admin/backup-now",
        headers={"Origin": "http://localhost"},
    )
    # Pasa CSRF; el endpoint puede devolver 200 o error de DB
    assert r.status_code != 403


def test_post_with_referer_same_host_passes(admin_client):
    """Si Origin no llega, Referer del mismo host es aceptado."""
    r = admin_client.post(
        "/api/admin/backup-now",
        headers={"Referer": "http://localhost/admin"},
    )
    assert r.status_code != 403


def test_post_session_no_origin_allowed_with_log(admin_client):
    """Sin Origin/Referer pero con sesión válida = scripts internos OK
    (se loguea como csrf_no_origin_allowed)."""
    r = admin_client.post("/api/admin/backup-now")
    assert r.status_code != 403   # permitido (log queda en security_events)


def test_post_no_origin_no_session_blocked(client):
    """Sin sesión, sin Origin/Referer en mutación → ya bloqueado por auth."""
    r = client.post("/api/cambiar-password", json={"x": 1})
    # Bloqueado por require_auth (401) antes de llegar al CSRF check
    assert r.status_code == 401


def test_post_with_empty_origin_treated_as_missing(admin_client):
    """Origin vacío → cae al bucket de 'sin headers' (sesión válida lo permite)."""
    r = admin_client.post(
        "/api/admin/backup-now",
        headers={"Origin": ""},
    )
    assert r.status_code != 403
