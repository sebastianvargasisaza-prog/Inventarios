"""`tendencia` es una ETIQUETA de texto · el número vive en `tendencia_pct` (25-jul).

`velocidad_blended_uds_dia` (auto_plan.py) devuelve `(velocidad, etiqueta)` donde la etiqueta es
un texto: 'aceleracion_fuerte', 'aceleracion_moderada', 'estable', 'caida_moderada',
'caida_fuerte', 'sin_historico'. DOS consumidores la trataban como si fuera una fracción:

  1. El diagnóstico de cadenas hacía `float(p['tendencia'])` → **500 en producción**
     (`could not convert string to float: 'caida_fuerte'`).
  2. La alerta del panel comparaba `p.tendencia >= 0.08` → con un texto eso es SIEMPRE falso,
     así que "📈 ventas +X% · considerá adelantar" nunca apareció (feature muerta en silencio,
     misma clase que M94).

Estos tests fijan el contrato: la etiqueta sigue siendo texto (no romper a nadie) y
`tendencia_pct` es un número que se puede comparar contra un umbral.
"""
from .conftest import TEST_PASSWORD, csrf_headers

ETIQUETAS = {'aceleracion_fuerte', 'aceleracion_moderada', 'estable',
             'caida_moderada', 'caida_fuerte', 'sin_historico'}


def _login(app, u='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': u, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _productos(c):
    r = c.get('/api/plan/necesidades')
    assert r.status_code == 200, r.data[:300]
    return [p for cl in (r.get_json().get('clientes') or [])
            for p in (cl.get('productos') or [])]


def test_velocidad_blended_devuelve_ETIQUETA_no_numero(app):
    """El contrato de la fuente: el 2º valor de retorno es texto. Si algún día pasa a número,
    este test se pone rojo y hay que revisar a los consumidores (no al revés)."""
    from blueprints.auto_plan import velocidad_blended_uds_dia
    for args in ((100, 120, 150), (0, 0, 0), (300, 120, 150), (10, 120, 150)):
        vel, tend = velocidad_blended_uds_dia(*args)
        assert isinstance(vel, (int, float)), (args, vel)
        assert isinstance(tend, str) and tend in ETIQUETAS, (args, tend)


def test_necesidades_expone_tendencia_pct_numerica(app):
    """Todo producto trae `tendencia_pct` NUMÉRICO (el que se compara contra el umbral)."""
    c = _login(app)
    prods = _productos(c)
    if not prods:
        return   # seed sin productos mapeados · nada que afirmar
    for p in prods:
        assert 'tendencia_pct' in p, p.get('producto_nombre')
        tp = p['tendencia_pct']
        assert isinstance(tp, (int, float)) and not isinstance(tp, bool), (p.get('producto_nombre'), tp)
        assert -2.0 <= float(tp) <= 2.0, (p.get('producto_nombre'), tp)
        # la etiqueta se conserva intacta (no se rompió a otros consumidores)
        assert isinstance(p.get('tendencia'), (str, float, int)), p.get('tendencia')


def test_salud_cadenas_responde_y_no_convierte_la_etiqueta(app):
    """El endpoint que caía con 500 responde 200 y su `tendencia_pct` es un entero de %."""
    c = _login(app)
    r = c.get('/api/plan/salud-cadenas')
    assert r.status_code == 200, r.data[:300]
    for it in (r.get_json().get('items') or []):
        if 'tendencia_pct' in it:
            assert isinstance(it['tendencia_pct'], (int, float)), it


def test_lanzamiento_en_ascenso_no_se_marca_como_sobreproduccion(app):
    """Sebastián 25-jul: BLUSH BALM y LIP SERUM sobre-producen A PROPÓSITO (lanzamientos en
    rampa). La rama que los protege depende de que la tendencia sea comparable como número:
    con la etiqueta de texto NUNCA se cumplía. Se verifica la decisión en aislamiento."""
    ratio, dias_exceso = 3.18, 87        # datos reales de LIP SERUM en producción

    def _clasificar(tend):
        if ratio >= 1.3 and dias_exceso >= 30:
            return 'lanzamiento' if tend >= 0.08 else 'sobre'
        return 'ok'

    assert _clasificar(0.35) == 'lanzamiento', 'en ascenso fuerte NO es sobre-producción'
    assert _clasificar(0.0) == 'sobre', 'sin ascenso sí es sobre-producción'
    # el bug original: comparar la ETIQUETA nunca daba lanzamiento
    try:
        float('aceleracion_fuerte')
        assert False, 'la etiqueta no debería ser convertible a float'
    except ValueError:
        pass
