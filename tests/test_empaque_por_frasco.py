# -*- coding: utf-8 -*-
"""La tapa y la caja se cargan por FRASCO, no producto por producto.

Sebastián (8-ago), al final de la revisión de Planta: *"¿entonces necesitas que llene los
productos?"*. Sí, pero la unidad correcta no es el producto: **la tapa pertenece al FRASCO**. Un
airless de 30 ml lleva la misma tapa lo tenga el suero que lo tenga.

Con eso, lo que se veía como "29 productos" se convierte en unos pocos frascos: se dice una vez y
todas las presentaciones que usan ese frasco lo heredan.

⚠ Deduce, NO adivina: sólo propone cuando otra presentación del mismo frasco ya tiene el dato, y
si dos tienen tapas distintas no elige por mayoría -- lo muestra y decide una persona (M19).
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

PREF = 'EMPQFR'


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre LIKE ?", (PREF + '%',))
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE ?", (PREF + '%',))
        c.commit()


def _mee(app, cod):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, stock_actual) VALUES (?,?,0)",
                  (cod, 'test ' + cod))
        c.commit()


def _pres(app, producto, frasco, tapa='', caja='', sin_tapa=0):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, envase_codigo, tapa_codigo, caja_codigo, sin_tapa, activo) "
                  "VALUES (?,'V30','30 ml',30,?,?,?,?,1)",
                  (producto, frasco, tapa, caja, sin_tapa))
        c.commit()


def _sug(admin_client):
    r = admin_client.get('/api/programacion/empaque-sugerencias')
    assert r.status_code == 200, r.data[:200]
    return r.get_json()


def _mios(j, clave, frasco):
    return [x for x in (j.get(clave) or []) if x.get('frasco') == frasco]


def test_DEDUCE_la_tapa_del_frasco_cuando_otra_ya_la_tiene(app, admin_client):
    _limpiar(app)
    _mee(app, PREF + '-FR'); _mee(app, PREF + '-TAPA')
    _pres(app, PREF + ' UNO', PREF + '-FR', tapa=PREF + '-TAPA')
    _pres(app, PREF + ' DOS', PREF + '-FR')            # mismo frasco, sin tapa
    s = _mios(_sug(admin_client), 'sugerencias', PREF + '-FR')
    tapa = [x for x in s if x['campo'] == 'tapa']
    assert tapa, 'no deduce la tapa del frasco'
    assert tapa[0]['codigo'] == PREF + '-TAPA'
    assert len(tapa[0]['aplica_a']) == 1
    _limpiar(app)


def test_NO_deduce_cuando_el_mismo_frasco_tiene_tapas_DISTINTAS(app, admin_client):
    """Puede ser correcto (dos versiones del envase) o ser el error. No se elige por mayoría: se
    muestra y decide una persona (M19)."""
    _limpiar(app)
    _mee(app, PREF + '-FR2'); _mee(app, PREF + '-T1'); _mee(app, PREF + '-T2')
    _pres(app, PREF + ' A', PREF + '-FR2', tapa=PREF + '-T1')
    _pres(app, PREF + ' B', PREF + '-FR2', tapa=PREF + '-T2')
    _pres(app, PREF + ' C', PREF + '-FR2')
    j = _sug(admin_client)
    assert not [x for x in _mios(j, 'sugerencias', PREF + '-FR2') if x['campo'] == 'tapa'], \
        'eligió una tapa cuando hay dos candidatas'
    assert _mios(j, 'ambiguos', PREF + '-FR2'), 'no avisa que es ambiguo · se resolvería solo'
    _limpiar(app)


def test_NO_LLEVA_es_una_respuesta_no_un_pendiente(app, admin_client):
    """Un frasco marcado 'no lleva tapa' no es un hueco: contarlo como faltante haría que la
    lista de pendientes nunca llegue a cero, y una lista que nunca cierra deja de mirarse."""
    _limpiar(app)
    _mee(app, PREF + '-FR3')
    _pres(app, PREF + ' SIN', PREF + '-FR3', sin_tapa=1)
    j = _sug(admin_client)
    assert not [x for x in _mios(j, 'sin_referencia', PREF + '-FR3') if x['campo'] == 'tapa'], \
        'cuenta como faltante una tapa que se declaró que no lleva'
    _limpiar(app)


def test_APLICA_a_todas_las_del_mismo_frasco(app, admin_client):
    from database import get_db
    _limpiar(app)
    _mee(app, PREF + '-FR4'); _mee(app, PREF + '-T4')
    for n in ('UNO', 'DOS', 'TRES'):
        _pres(app, PREF + ' ' + n, PREF + '-FR4')
    r = admin_client.post('/api/programacion/empaque-aplicar',
                          json={'frasco': PREF + '-FR4', 'campo': 'tapa', 'codigo': PREF + '-T4'},
                          headers={'Origin': 'http://localhost'})
    assert r.status_code == 200, r.data[:200]
    assert r.get_json()['aplicadas'] == 3
    with app.app_context():
        n = get_db().execute(
            "SELECT COUNT(*) FROM producto_presentaciones "
            " WHERE producto_nombre LIKE ? AND tapa_codigo=?",
            (PREF + '%', PREF + '-T4')).fetchone()[0]
    assert n == 3
    _limpiar(app)


def test_NO_pisa_lo_que_alguien_ya_cargo_a_mano(app, admin_client):
    """Lo cargado a mano vale más que lo deducido · es la misma regla del Fijo sobre lo Sugerido."""
    from database import get_db
    _limpiar(app)
    _mee(app, PREF + '-FR5'); _mee(app, PREF + '-TA'); _mee(app, PREF + '-TB')
    _pres(app, PREF + ' MANUAL', PREF + '-FR5', tapa=PREF + '-TA')
    _pres(app, PREF + ' VACIA', PREF + '-FR5')
    admin_client.post('/api/programacion/empaque-aplicar',
                      json={'frasco': PREF + '-FR5', 'campo': 'tapa', 'codigo': PREF + '-TB'},
                      headers={'Origin': 'http://localhost'})
    with app.app_context():
        r = get_db().execute(
            "SELECT tapa_codigo FROM producto_presentaciones WHERE producto_nombre=?",
            (PREF + ' MANUAL',)).fetchone()
    assert r[0] == PREF + '-TA', 'pisó una tapa que alguien había cargado a mano'
    _limpiar(app)


def test_NO_deja_poner_un_codigo_que_no_existe(app, admin_client):
    """Un empaque fantasma es un empaque que la compra no resuelve, así que no se compra nunca y
    nadie se entera (M5)."""
    _limpiar(app)
    _mee(app, PREF + '-FR6')
    _pres(app, PREF + ' X', PREF + '-FR6')
    r = admin_client.post('/api/programacion/empaque-aplicar',
                          json={'frasco': PREF + '-FR6', 'campo': 'tapa', 'codigo': 'NO-EXISTE-999'},
                          headers={'Origin': 'http://localhost'})
    assert r.status_code == 400, 'aceptó un código que no está en el maestro'
    _limpiar(app)


def test_el_resumen_cuenta_FRASCOS_no_productos(app, admin_client):
    """Es el número que dice cuánto trabajo queda de verdad. "29 productos" asusta y no es la
    unidad correcta: el mismo frasco se repite en varios."""
    j = _sug(admin_client)
    res = j.get('resumen') or {}
    for k in ('frascos', 'se_pueden_deducir', 'hay_que_teclear', 'ambiguos'):
        assert k in res, 'el resumen no dice %s' % k


def test_se_puede_ABRIR_desde_la_pantalla(app):
    """Un ayudante al que no se llega no existe (M121)."""
    import re
    import templates_py.dashboard_html as D
    html = D.DASHBOARD_HTML
    todo = html + getattr(D, 'DASHBOARD_APP_JS', '')
    assert 'empqCompletar()' in html, 'no hay botón'
    assert re.search(r'(?:async )?function\s+empqCompletar\s*\(', todo), \
        'el botón llama a una función que no existe'
    assert 'empqAplicarFrasco' in todo and 'empaque-aplicar' in todo
