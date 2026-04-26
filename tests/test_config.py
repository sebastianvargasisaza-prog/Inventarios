"""Tests de validate_config()."""
import os


def test_validate_config_runs_without_error(app):
    """validate_config no debe crashear bajo ninguna condición."""
    from config import validate_config
    issues = validate_config()
    assert isinstance(issues, list)


def test_validate_config_detects_missing_secret_key(monkeypatch):
    """Si SECRET_KEY no está, validate_config emite CRITICAL."""
    import config
    monkeypatch.delenv("SECRET_KEY", raising=False)
    issues = config.validate_config()
    codes = [i["code"] for i in issues]
    assert "MISSING_SECRET_KEY" in codes


def test_validate_config_detects_plaintext_password(app):
    """Setear PASS_<USER> con texto plano (no hash) debe detectarse."""
    import importlib
    import config

    saved = os.environ.get("PASS_LUIS")
    os.environ["PASS_LUIS"] = "esto-es-plaintext-no-hash"
    try:
        importlib.reload(config)
        issues = config.validate_config()
        codes = [i["code"] for i in issues]
        assert "PLAINTEXT_PASSWORDS" in codes
        # Y debe mencionar al user afectado
        msg = next(i["msg"] for i in issues if i["code"] == "PLAINTEXT_PASSWORDS")
        assert "luis" in msg.lower()
    finally:
        if saved is not None:
            os.environ["PASS_LUIS"] = saved
        else:
            os.environ.pop("PASS_LUIS", None)
        importlib.reload(config)


def test_validate_config_returns_severity_levels(app):
    """Todos los issues tienen severity en {CRITICAL,HIGH,MEDIUM,INFO}."""
    from config import validate_config
    valid = {"CRITICAL", "HIGH", "MEDIUM", "INFO"}
    for issue in validate_config():
        assert issue["severity"] in valid
        assert "code" in issue
        assert "msg" in issue
        assert isinstance(issue["msg"], str)


def test_formula_pin_random_when_missing(app):
    """Si FORMULA_PIN no está en env, se genera uno aleatorio (no '7531')."""
    from config import FORMULA_PIN
    assert FORMULA_PIN != "7531"
    # En tests el PIN es random porque no setteamos FORMULA_PIN
    if not os.environ.get("FORMULA_PIN"):
        assert len(FORMULA_PIN) >= 8


def test_no_hardcoded_secret_key_fallback(app):
    """index.py no debe usar el fallback público 'hha-group-2026-secretkey-x9kq'."""
    # En conftest.py seteamos SECRET_KEY=test-secret-key-only-for-pytest
    assert app.secret_key != "hha-group-2026-secretkey-x9kq"
