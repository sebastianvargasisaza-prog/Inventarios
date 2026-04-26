"""Smoke tests: verifica que la app arranca y la estructura básica está OK."""


def test_app_boots(app):
    """La app Flask se importa y tiene secret_key."""
    assert app is not None
    assert app.secret_key is not None
    assert len(app.secret_key) >= 16


def test_health_endpoint_public(client):
    """/api/health no requiere auth — usado por Render para health checks."""
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data is not None
    # health del core devuelve 'ok' o info de DB
    assert "status" in data or "tables" in data


def test_login_page_accessible(client):
    """/login responde sin auth."""
    r = client.get("/login")
    assert r.status_code in (200, 302)


def test_request_id_header_present(client):
    """Cada response tiene X-Request-Id (para correlación de logs)."""
    r = client.get("/api/health")
    assert "X-Request-Id" in r.headers
    assert len(r.headers["X-Request-Id"]) > 0


def test_request_id_echoed_from_header(client):
    """Si el cliente envía X-Request-Id, se reusa (load balancer use case)."""
    r = client.get("/api/health", headers={"X-Request-Id": "lb-test-12345"})
    assert r.headers.get("X-Request-Id") == "lb-test-12345"


def test_security_headers_present(client):
    """Headers de seguridad básicos en cada response."""
    r = client.get("/login")
    assert r.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert "Strict-Transport-Security" in r.headers
    assert "Content-Security-Policy" in r.headers


def test_critical_blueprints_registered(app):
    """Verifica que los blueprints críticos están registrados."""
    blueprint_names = list(app.blueprints.keys())
    expected = {"core", "hub", "inventario", "compras", "marketing", "admin"}
    missing = expected - set(blueprint_names)
    assert not missing, f"Blueprints faltantes: {missing}"


def test_critical_routes_registered(app):
    """Verifica que las rutas críticas existen."""
    rules = {r.rule for r in app.url_map.iter_rules()}
    critical = {
        "/login",
        "/logout",
        "/api/health",
        "/api/cambiar-password",
        "/admin",
        "/api/admin/backups",
        "/api/admin/backup-now",
        "/api/marketing/ads/run",
        "/api/marketing/ads/capabilities",
    }
    missing = critical - rules
    assert not missing, f"Rutas faltantes: {missing}"


def test_404_returns_html(client):
    """404 personalizado devuelve HTML (no stack trace)."""
    r = client.get("/no-existe-xyz")
    assert r.status_code == 404
    # No expone info sensible
    assert b"Traceback" not in r.data
