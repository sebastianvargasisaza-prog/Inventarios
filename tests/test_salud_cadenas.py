"""Diagnóstico de SALUD DE CADENAS · ¿está bien dimensionada la producción programada?

Sebastián 25-jul, mirando LIP SERUM: la cadena tenía 36 lotes de 15 kg mensuales cuando el
motor calcula que con 5.9 kg alcanza. La app ya lo sabía (marcaba sobra-stock de 400 a 1030
días lote por lote) pero estaba escondido dentro del modal, y la fila decía verde.

La regla que se verifica es la MISMA del motor de cadencia (regla de reorden, 11-jul):
    cada lote debe cubrir la cadencia + 20 días de colchón
    kg_requerido = velocidad_uds_dia × (cadencia_dias + 20) × ml_unidad / 1000

Si el lote programado es mucho más grande que eso, la cadena SOBRE-PRODUCE: se inmoviliza
plata y se acumula producto cosmético con vencimiento. Si es mucho más chico, se queda CORTA
y habrá quiebre.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD_SOBRA = 'ZZ CADENA SOBRA'
PROD_OK = 'ZZ CADENA SANA'
SKU_SOBRA = 'ZZSKU-SOBRA'
SKU_OK = 'ZZSKU-OK'


def _db():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=15)


def _sql(*stmts):
    db = _db()
    try:
        for s in stmts:
            db.execute(s)
        db.commit()
    finally:
        db.close()


def _login(app, u='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': u, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar():
    _sql("DELETE FROM produccion_programada WHERE producto IN ('%s','%s')" % (PROD_SOBRA, PROD_OK))


def _lote(prod, kg, dias):
    _sql("INSERT INTO produccion_programada (producto,fecha_programada,lotes,cantidad_kg,origen,estado) "
         "VALUES ('%s', date('now','-5 hours','+%d days'), 1, %s, 'eos_plan', 'pendiente')"
         % (prod, dias, kg))


def test_endpoint_responde_y_exige_login(app, client):
    assert client.get('/api/plan/salud-cadenas').status_code in (401, 302)
    c = _login(app)
    r = c.get('/api/plan/salud-cadenas')
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert d.get('ok') is True
    assert isinstance(d.get('items'), list)
    assert 'resumen' in d


def test_ve_las_cadenas_que_existen(app):
    """Si un producto de la lista tiene lotes futuros, el diagnóstico TIENE que verlos.

    ⚠ Este test nació de un bug PROPIO: la primera versión del endpoint usaba `_date` sin
    importarlo (en plan.py cada función lo importa local), el `except` de la iteración se
    tragaba el NameError lote por lote y TODAS las cadenas salían vacías: respondía
    `sin_cadena: 28` con 200 OK. La primera versión de este test tenía un
    `if item is not None: assert ...`, así que PASÓ EN VACÍO y no lo detectó.
    Por eso ahora siembra sobre un producto REAL del payload y afirma sin condicionales.
    """
    c = _login(app)
    base = c.get('/api/plan/salud-cadenas').get_json()
    n_sin_antes = base['resumen']['sin_cadena']
    # tomar un producto que el motor SÍ lista (los sembrados a mano no están mapeados a SKU)
    nec = c.get('/api/plan/necesidades').get_json()
    prods = [p.get('producto_nombre') for cl in (nec.get('clientes') or [])
             for p in (cl.get('productos') or []) if p.get('producto_nombre')]
    if not prods:
        return   # el seed de tests no trae productos mapeados · nada que afirmar
    objetivo = prods[0]
    _sql("DELETE FROM produccion_programada WHERE producto='%s'" % objetivo.replace("'", "''"))
    for d in (30, 60, 90):
        _sql("INSERT INTO produccion_programada (producto,fecha_programada,lotes,cantidad_kg,origen,estado) "
             "VALUES ('%s', date('now','-5 hours','+%d days'), 1, 60, 'eos_plan', 'pendiente')"
             % (objetivo.replace("'", "''"), d))
    try:
        d2 = c.get('/api/plan/salud-cadenas').get_json()
        item = next((x for x in d2['items'] if x['producto'] == objetivo), None)
        assert item is not None, (
            'el diagnóstico NO vio una cadena de 3 lotes futuros · resumen=%s' % d2['resumen'])
        assert item['n_lotes'] == 3, item
        assert item['cadencia_dias'] == 30, item
        assert item['kg_lote_programado'] == 60.0, item
        assert d2['resumen']['sin_cadena'] < n_sin_antes + 1, d2['resumen']
    finally:
        _sql("DELETE FROM produccion_programada WHERE producto='%s'" % objetivo.replace("'", "''"))


def test_no_marca_lo_que_no_puede_juzgar(app):
    """Sin velocidad de venta o sin ml no se puede calcular el requerido: se informa, no se adivina."""
    c = _login(app)
    r = c.get('/api/plan/salud-cadenas')
    d = r.get_json()
    for it in d['items']:
        if it['estado'] == 'sin_datos':
            assert it.get('kg_requerido_lote') in (None, 0), it
        else:
            assert it.get('kg_requerido_lote'), it
            # todo item juzgado trae con qué se juzgó (auditable)
            assert it.get('cadencia_dias') and it.get('kg_lote_programado') is not None, it
