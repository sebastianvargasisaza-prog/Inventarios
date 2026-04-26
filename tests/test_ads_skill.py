"""Tests del motor ads_skill (Agencia de Ads multi-plataforma)."""

from .conftest import csrf_headers


def test_capabilities_lists_7_platforms(app):
    from ads_skill import list_capabilities
    caps = list_capabilities()
    assert len(caps["platforms"]) == 7
    expected = {"google", "meta", "linkedin", "tiktok", "youtube", "apple", "microsoft"}
    assert set(caps["platforms"]) == expected


def test_capabilities_lists_actions(app):
    from ads_skill import list_capabilities
    caps = list_capabilities()
    assert set(caps["actions_per_platform"]) == {"audit", "plan", "creative", "budget"}
    assert set(caps["actions_global"]) == {"competitor", "landing", "test", "dna"}


def test_default_model_is_sonnet(app):
    from ads_skill import list_capabilities
    assert list_capabilities()["default_model"] == "claude-sonnet-4-5"


def test_run_rejects_invalid_platform(app):
    from ads_skill import run_ads_skill
    r = run_ads_skill(
        platform="instagram-fake",
        action="audit",
        payload="some data",
        api_key="test-key",
    )
    assert "error" in r
    assert "plataforma" in r["error"].lower()


def test_run_rejects_invalid_action(app):
    from ads_skill import run_ads_skill
    r = run_ads_skill(
        platform="meta",
        action="hackear",
        payload="some data",
        api_key="test-key",
    )
    assert "error" in r
    assert "accion" in r["error"].lower()


def test_run_rejects_missing_api_key(app):
    from ads_skill import run_ads_skill
    r = run_ads_skill(
        platform="meta",
        action="audit",
        payload="some data",
        api_key="",
    )
    assert "error" in r
    assert "api_key" in r["error"].lower()


def test_system_prompt_has_orchestrator_and_platform(app):
    """Verifica que el system prompt combina los archivos correctamente."""
    from ads_skill import _build_system_prompt
    sp = _build_system_prompt("google", "audit")
    # Debe tener marker del orchestrator
    assert "Multi-Platform" in sp or "Quick Reference" in sp
    # Debe tener marker de la plataforma
    assert "GOOGLE" in sp.upper()
    # Debe tener marker de la acción
    assert "AUDIT" in sp.upper()
    # Debe ser sustancial (skills tienen mucho contenido)
    assert len(sp) > 10000


def test_system_prompt_for_global_actions_no_platform(app):
    """Acciones globales no requieren platform."""
    from ads_skill import _build_system_prompt
    sp = _build_system_prompt(None, "competitor")
    assert len(sp) > 5000
    assert "COMPETITOR" in sp.upper()


# ── Endpoints HTTP ────────────────────────────────────────────────────────────


def test_capabilities_endpoint_requires_auth(client, db_clean):
    r = client.get("/api/marketing/ads/capabilities")
    assert r.status_code == 401


def test_run_rejects_short_payload(app, db_clean):
    """Payload muy corto → 400 antes de llamar a Claude."""
    from .conftest import TEST_PASSWORD
    c = app.test_client()
    c.post("/login", data={"username": "felipe", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.post("/api/marketing/ads/run",
               json={"platform": "meta", "action": "audit", "payload": "x"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_run_rejects_invalid_combo(app, db_clean):
    """action de plataforma sin platform → 400."""
    from .conftest import TEST_PASSWORD
    c = app.test_client()
    c.post("/login", data={"username": "jefferson", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.post("/api/marketing/ads/run",
               json={"action": "audit", "payload": "x" * 50},
               headers=csrf_headers())
    assert r.status_code == 400
