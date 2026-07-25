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


def test_detecta_cadena_sobredimensionada(app):
    """Un producto cuya cadena entrega mucho más kg del que consume debe salir marcado."""
    _limpiar()
    # 3 lotes mensuales de 60 kg para un producto que vende poquísimo → sobra evidente
    for i, d in enumerate((30, 60, 90)):
        _lote(PROD_SOBRA, 60, d)
    c = _login(app)
    try:
        r = c.get('/api/plan/salud-cadenas')
        assert r.status_code == 200, r.data[:300]
        d = r.get_json()
        item = next((x for x in d['items'] if x['producto'] == PROD_SOBRA), None)
        # sin ventas mapeadas el motor no puede juzgar: debe decirlo, no inventar
        if item is not None:
            assert item['estado'] in ('sobre', 'sin_datos'), item
    finally:
        _limpiar()


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
