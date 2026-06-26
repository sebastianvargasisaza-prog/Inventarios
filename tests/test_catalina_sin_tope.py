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


def test_catalina_libera_aprueba_mp(app):
    # Sebastián 26-jun · Catalina libera/aprueba MP (QC_USERS) sin darle el módulo Calidad completo
    from config import MP_LIBERA_USERS, CALIDAD_USERS
    assert 'catalina' in MP_LIBERA_USERS
    assert 'catalina' not in CALIDAD_USERS, 'NO debe estar en el módulo Calidad completo'
    from blueprints.inventario import QC_USERS
    assert 'catalina' in QC_USERS, 'Catalina debe poder liberar/aprobar MP (gate QC)'


def test_catalina_aprueba_lote_pasa_gate_rol(app):
    # El gate de rol de /api/recepcion/aprobar-lote NO debe darle 403 a Catalina
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    c.post('/login', data={'username': 'catalina', 'password': TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    h = {'Content-Type': 'application/json'}
    h.update(csrf_headers())
    r = c.post('/api/recepcion/aprobar-lote', json={'lote': 'NOEXISTE-ZZ', 'accion': 'APROBAR'}, headers=h)
    assert r.status_code != 403, 'Catalina debe pasar el gate de rol (no 403) · ' + str(r.data[:120])
