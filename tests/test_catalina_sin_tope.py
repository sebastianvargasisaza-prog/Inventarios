"""Sebastián 26-jun · Catalina autoriza/paga OCs SIN tope de monto (OC_SIN_LIMITE_MONTO).
Mayra mantiene su tope de 5M (no está en el set). Verifica el gate _check_monto_limit."""


def test_catalina_autoriza_cualquier_monto(app):
    with app.app_context():
        from blueprints.compras import _check_monto_limit
        # Catalina: cualquier monto, incluso muy por encima de 5M → OK (sin tope)
        err, _ = _check_monto_limit('catalina', 50_000_000)
        assert err is None, 'Catalina debe poder autorizar cualquier monto'
        err2, _ = _check_monto_limit('catalina', 999_000_000)
        assert err2 is None


def test_mayra_mantiene_tope_5m(app):
    with app.app_context():
        from blueprints.compras import _check_monto_limit
        # Mayra <= 5M → OK
        ok, _ = _check_monto_limit('mayra', 4_000_000)
        assert ok is None
        # Mayra > 5M → bloqueada (mantiene su tope · solo Catalina quedó sin tope)
        err, code = _check_monto_limit('mayra', 6_000_000)
        assert err is not None and code == 403, 'Mayra mantiene su tope de 5M'
