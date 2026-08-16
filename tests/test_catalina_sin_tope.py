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


def test_quien_recibe_la_mp_no_es_quien_la_libera(app):
    """Catalina RECIBE la materia prima, y por eso NO puede liberarla de cuarentena.

    Estos dos tests nacieron el 26-jun afirmando lo contrario (`'catalina' in MP_LIBERA_USERS`)
    y una decisión posterior los invalidó: `config.py` vació el set con el motivo escrito --
    Resolución 2214/2021 art. 10 asigna la disposición del lote a Calidad, así que quien recibe
    no puede ser quien libera. El comportamiento de hoy es el correcto y el que estaba viejo era
    el test (M97), así que se re-apunta a la GARANTÍA -- la segregación de funciones -- en vez de
    a la implementación de entonces.

    Lo que Catalina conserva (y es lo que el archivo vino a proteger) son sus topes de compra,
    que siguen probados arriba.
    """
    from config import MP_LIBERA_USERS, CALIDAD_USERS
    assert 'catalina' not in MP_LIBERA_USERS, (
        'quien recibe la MP no puede liberarla · si esto se amplía tiene que ser una decisión '
        'explícita de Dirección Técnica (ver el comentario en config.py)')
    assert 'catalina' not in CALIDAD_USERS, 'NO debe estar en el módulo Calidad completo'
    from blueprints.inventario import QC_USERS
    assert 'catalina' not in QC_USERS, 'el gate de liberación de MP tampoco la incluye'


def test_el_gate_de_liberar_lote_deja_afuera_a_quien_recibe(app):
    """El gate de `/api/recepcion/aprobar-lote` responde 403 a Catalina: el mismo principio,
    ejercido por la ruta real y no leyendo el set (M170)."""
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    c.post('/login', data={'username': 'catalina', 'password': TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    h = {'Content-Type': 'application/json'}
    h.update(csrf_headers())
    r = c.post('/api/recepcion/aprobar-lote', json={'lote': 'NOEXISTE-ZZ', 'accion': 'APROBAR'}, headers=h)
    assert r.status_code == 403, (
        'la disposición del lote es de Calidad · ' + str(r.data[:120]))


def test_calidad_si_pasa_el_gate_de_liberar_lote(app):
    """Y el borde que hace que el test anterior signifique algo: con el rol correcto NO hay 403.

    Sin esto, un gate que trabara a TODO el mundo pasaría verde igual (M171).
    """
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    c.post('/login', data={'username': 'laura', 'password': TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    h = {'Content-Type': 'application/json'}
    h.update(csrf_headers())
    r = c.post('/api/recepcion/aprobar-lote', json={'lote': 'NOEXISTE-ZZ', 'accion': 'APROBAR'}, headers=h)
    assert r.status_code != 403, (
        'Control de Calidad tiene que poder disponer el lote · ' + str(r.data[:120]))
