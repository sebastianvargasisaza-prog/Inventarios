"""Tests de la integración con Sentry.

Sentry NO debe inicializarse en tests (se detecta via env var
PYTEST_CURRENT_TEST). Estos tests verifican el comportamiento opt-in.
"""
import importlib
import os


def test_sentry_not_initialized_in_tests(app):
    """En tests, sentry_sdk no debe estar configurado (PYTEST_CURRENT_TEST set)."""
    # En testing, no inicializamos Sentry. Verificar que no tiene client real.
    try:
        import sentry_sdk
        client = sentry_sdk.Hub.current.client
        # Si Sentry no se inicializó, el client puede ser None o no estar.
        # Si está inicializado, options['dsn'] sería el DSN real — no debe pasar.
        if client is not None:
            assert client.options.get("dsn") in (None, "", "test-dsn"), \
                "Sentry no debe estar inicializado con DSN real en tests"
    except ImportError:
        pass  # sentry_sdk no instalado — está OK para tests


def test_app_works_without_sentry(client, db_clean):
    """La app debe funcionar normalmente aunque SENTRY_DSN no esté configurado."""
    r = client.get("/api/health")
    assert r.status_code == 200


def test_sentry_listed_in_optional_config(admin_client, db_clean):
    """SENTRY_DSN aparece en optional vars del config-status."""
    r = admin_client.get("/api/admin/config-status")
    assert r.status_code == 200
    data = r.get_json()
    optional_names = {v["name"] for v in data["optional"]}
    assert "SENTRY_DSN" in optional_names


def test_sentry_missing_logged_as_info(monkeypatch):
    """Si SENTRY_DSN falta, validate_config emite INFO (no CRITICAL)."""
    import config
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    issues = config.validate_config()
    sentry_issue = next(
        (i for i in issues if "SENTRY_DSN" in i.get("msg", "")),
        None,
    )
    if sentry_issue:
        # Si aparece en issues, debe ser INFO (no bloqueante)
        assert sentry_issue["severity"] == "INFO"
