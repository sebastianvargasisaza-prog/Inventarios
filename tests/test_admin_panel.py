"""Tests del panel admin extendido: users, reset password, eventos, config."""
from .conftest import TEST_PASSWORD, csrf_headers


# ── /api/admin/users ─────────────────────────────────────────────────────────


def test_users_list_requires_admin(client, db_clean):
    r = client.get("/api/admin/users")
    assert r.status_code == 401


def test_users_list_blocked_for_non_admin(app, db_clean):
    c = app.test_client()
    c.post("/login", data={"username": "valentina", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.get("/api/admin/users")
    assert r.status_code == 403


def test_users_list_admin_returns_19_users(admin_client, db_clean):
    r = admin_client.get("/api/admin/users")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 19
    assert len(data["users"]) == 19


def test_users_list_includes_groups_and_password_source(admin_client, db_clean):
    r = admin_client.get("/api/admin/users")
    data = r.get_json()
    sebastian = next(u for u in data["users"] if u["username"] == "sebastian")
    assert sebastian["is_admin"] is True
    assert "Admin" in sebastian["groups"]
    assert sebastian["password_source"] in ("env", "db")
    # No expone hashes ni passwords
    assert "password_hash" not in sebastian
    assert "password" not in sebastian


def test_users_list_no_hashes_exposed(admin_client, db_clean):
    """CRITICAL: el endpoint NO debe devolver hashes ni passwords plaintext."""
    r = admin_client.get("/api/admin/users")
    body = r.get_data(as_text=True)
    # Ningun PBKDF2 hash ni la TEST_PASSWORD plana en el response
    assert "pbkdf2:" not in body
    assert TEST_PASSWORD not in body


# ── /api/admin/reset-password ────────────────────────────────────────────────


def test_reset_password_requires_admin(client, db_clean):
    r = client.post("/api/admin/reset-password",
                    json={"username": "valentina"},
                    headers=csrf_headers())
    assert r.status_code == 401


def test_reset_password_blocked_for_non_admin(app, db_clean):
    c = app.test_client()
    c.post("/login", data={"username": "felipe", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.post("/api/admin/reset-password",
               json={"username": "felipe"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_reset_password_unknown_user(admin_client, db_clean):
    r = admin_client.post("/api/admin/reset-password",
                          json={"username": "fantasma"},
                          headers=csrf_headers())
    assert r.status_code == 404


def test_reset_password_missing_username(admin_client, db_clean):
    r = admin_client.post("/api/admin/reset-password",
                          json={},
                          headers=csrf_headers())
    assert r.status_code == 400


def test_reset_password_works_end_to_end(app, db_clean):
    """Admin resetea, user puede loguear con nueva password."""
    admin = app.test_client()
    admin.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    r = admin.post("/api/admin/reset-password",
                   json={"username": "valentina"},
                   headers=csrf_headers())
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    new_pwd = data["new_password"]
    assert len(new_pwd) >= 8

    # Valentina puede loguear con la nueva
    user_c = app.test_client()
    r = user_c.post("/login",
                    data={"username": "valentina", "password": new_pwd},
                    headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302  # redirect


def test_reset_password_disables_old_password(app, db_clean):
    """Después del reset, la password vieja (env var) ya no funciona."""
    admin = app.test_client()
    admin.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    admin.post("/api/admin/reset-password",
               json={"username": "yuliel"},
               headers=csrf_headers())
    # Ya no entra con la vieja TEST_PASSWORD
    user_c = app.test_client()
    r = user_c.post("/login",
                    data={"username": "yuliel", "password": TEST_PASSWORD},
                    headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 200  # fallo


# ── /api/admin/security-events ───────────────────────────────────────────────


def test_security_events_requires_admin(client, db_clean):
    r = client.get("/api/admin/security-events")
    assert r.status_code == 401


def test_security_events_returns_list(admin_client, db_clean):
    """Tras el login del admin (que generó login_success), debe haber al menos 1."""
    r = admin_client.get("/api/admin/security-events")
    assert r.status_code == 200
    data = r.get_json()
    assert "events" in data
    assert "stats_24h" in data
    assert isinstance(data["events"], list)


def test_security_events_filter_by_event_type(app, db_clean):
    """Filtro ?event=login_success funciona."""
    c = app.test_client()
    # Logear admin para generar 1 login_success
    c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.get("/api/admin/security-events?event=login_success&limit=5")
    assert r.status_code == 200
    events = r.get_json()["events"]
    for e in events:
        assert e["event"] == "login_success"


def test_security_events_limit_capped(admin_client, db_clean):
    """Limit > 500 se capea a 500 (anti-abuso)."""
    r = admin_client.get("/api/admin/security-events?limit=99999")
    assert r.status_code == 200
    # No debe crashear ni devolver más de 500
    assert len(r.get_json()["events"]) <= 500


# ── /api/admin/config-status ─────────────────────────────────────────────────


def test_config_status_requires_admin(client, db_clean):
    r = client.get("/api/admin/config-status")
    assert r.status_code == 401


def test_config_status_returns_structure(admin_client, db_clean):
    r = admin_client.get("/api/admin/config-status")
    assert r.status_code == 200
    data = r.get_json()
    for key in ("issues", "critical", "user_passwords", "optional"):
        assert key in data, f"Falta {key}"


def test_config_status_no_values_exposed(admin_client, db_clean):
    """CRITICAL: solo 'set' bool y 'length', NO el valor."""
    r = admin_client.get("/api/admin/config-status")
    body = r.get_data(as_text=True)
    # NO debe aparecer la SECRET_KEY de tests ni el TEST_PASSWORD
    assert "test-secret-key-only-for-pytest" not in body
    assert TEST_PASSWORD not in body
    # Cada item debe tener 'set' y 'length' pero NO 'value'
    data = r.get_json()
    for v in data["critical"] + data["user_passwords"] + data["optional"]:
        assert "set" in v
        assert "length" in v
        assert "value" not in v


def test_config_status_lists_all_user_passwords(admin_client, db_clean):
    """Las 19 PASS_<USER> aparecen."""
    r = admin_client.get("/api/admin/config-status")
    data = r.get_json()
    user_pass_names = {v["name"] for v in data["user_passwords"]}
    assert len(user_pass_names) == 19
    assert "PASS_SEBASTIAN" in user_pass_names
