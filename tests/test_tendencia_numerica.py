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


def test_sin_cadena_nombra_los_productos_y_no_cuenta_los_sin_ventas(app):
    """Un producto que SE VENDE y no tiene ni un lote programado va derecho al quiebre: es el
    hallazgo más caro y el diagnóstico solo devolvía el CONTEO, así que no se podía actuar.
    Y contaba también a los productos sin ventas, que no son un hallazgo (no hay qué programar).
    """
    c = _login(app)
    d = c.get('/api/plan/salud-cadenas').get_json()
    assert 'sin_cadena_productos' in d, d.get('resumen')
    assert 'sin_ventas' in d['resumen'], d['resumen']
    lista = d['sin_cadena_productos']
    assert isinstance(lista, list)
    assert len(lista) == d['resumen']['sin_cadena'], (len(lista), d['resumen'])
    for x in lista:
        assert x.get('producto'), x
        # si está en la lista es porque VENDE · si no vende, va a sin_ventas
        assert float(x.get('vende_uds_dia') or 0) > 0.001, x


def test_sobreproduccion_deliberada_es_un_DATO_no_una_inferencia(app):
    """Sebastián 25-jul: BLUSH BALM y LIP SERUM sobre-producen A PROPÓSITO.

    La primera versión los excusaba INFIRIENDO que venían en ascenso. Con los datos reales de
    producción los dos vienen en BAJA (-24% y -31%), así que la inferencia no los cubría y el
    diagnóstico seguía marcándolos como hallazgo. Una decisión del dueño se guarda como DATO
    explícito y reversible (mig 378), no se adivina con una heurística.
    """
    c = _login(app)
    r = c.get('/api/plan/salud-cadenas')
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert 'deliberado' in d['resumen'], d['resumen']
    for it in d['items']:
        if it['estado'] == 'deliberado':
            assert it.get('decision_motivo'), ('un deliberado debe decir POR QUÉ', it)
        if it['estado'] == 'sobre':
            assert not it.get('decision_motivo'), ('un deliberado no puede salir como sobre', it)


def test_la_marca_deliberada_gana_sobre_la_tendencia(app):
    """Marcar un producto lo saca de 'sobre' aunque su tendencia venga en BAJA (el caso real)."""
    import os
    import sqlite3
    c = _login(app)
    base = {i['producto']: i for i in c.get('/api/plan/salud-cadenas').get_json()['items']}
    objetivo = next((p for p, i in base.items() if i['estado'] == 'sobre'), None)
    if not objetivo:
        return   # el seed no produce ninguna cadena sobre-dimensionada · nada que afirmar

    def _marcar(valor, motivo):
        db = sqlite3.connect(os.environ['DB_PATH'], timeout=15)
        try:
            db.execute(
                "INSERT INTO sku_planeacion_config (producto_nombre, sobreproduccion_deliberada, "
                "sobreproduccion_motivo) VALUES (?,?,?) ON CONFLICT (producto_nombre) DO UPDATE SET "
                "sobreproduccion_deliberada=excluded.sobreproduccion_deliberada, "
                "sobreproduccion_motivo=excluded.sobreproduccion_motivo",
                (objetivo, valor, motivo))
            db.commit()
        finally:
            db.close()

    _marcar(1, 'test')
    try:
        it = next(x for x in c.get('/api/plan/salud-cadenas').get_json()['items']
                  if x['producto'] == objetivo)
        assert it['estado'] == 'deliberado', (objetivo, it['estado'])
        assert it['decision_motivo'] == 'test', it
        # y al desmarcarlo vuelve a ser un hallazgo (la marca no es de una sola vía)
        _marcar(0, '')
        it2 = next(x for x in c.get('/api/plan/salud-cadenas').get_json()['items']
                   if x['producto'] == objetivo)
        assert it2['estado'] == 'sobre', (objetivo, it2['estado'])
    finally:
        _marcar(0, '')
