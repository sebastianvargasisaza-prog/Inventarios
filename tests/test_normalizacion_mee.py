# -*- coding: utf-8 -*-
"""Cuánto falta para que el envase de CADA producto esté normalizado.

Sebastián (8-ago): *"lo más importante es que necesito normalizar MEE para cada producto, para que
podamos avanzar"*.

"Normalizado" no es una opinión: es una lista de condiciones que se cumplen o no, y cada una tiene
una consecuencia concreta si falta. Por eso cada hueco se reporta con **lo que rompe**, no con un
rótulo -- un pendiente que no dice qué se pierde no se prioriza.

⚠ Y el avance se mide en **productos listos**, no en campos llenos: un porcentaje de campos
subiría aunque ningún producto quede utilizable, que es justo el número que no sirve para decidir
si se puede avanzar (M5).
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

PROD = 'NORMTEST PRODUCTO'


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'NT-%'")
        c.commit()


def _sembrar(app, **kw):
    """Un producto activo con UNA presentación, y sus piezas como las pidan."""
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO formula_headers (producto_nombre, unidad_base_g, lote_size_kg, activo) "
                  "VALUES (?, 30000, 30, 1)", (PROD,))
        for cod in ('NT-FR', 'NT-TAPA', 'NT-CAJA'):
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, stock_actual) VALUES (?,?,0)",
                      (cod, 'test'))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, envase_codigo, tapa_codigo, caja_codigo, sin_tapa, "
                  "sin_caja, sku_shopify, activo) VALUES (?,?,?,?,?,?,?,?,?,?,1)",
                  (PROD, 'V30', '30 ml', 30,
                   kw.get('frasco', 'NT-FR'), kw.get('tapa', 'NT-TAPA'),
                   kw.get('caja', 'NT-CAJA'), kw.get('sin_tapa', 0), kw.get('sin_caja', 0),
                   kw.get('sku', 'SKU-NORM')))
        c.commit()


def _mio(admin_client):
    r = admin_client.get('/api/mee/normalizacion')
    assert r.status_code == 200, r.data[:200]
    j = r.get_json()
    fila = [p for p in j['productos'] if p['producto'] == PROD]
    return (fila[0] if fila else None), j


def _ques(p):
    return {f['que'] for f in (p or {}).get('faltas', [])}


def test_un_producto_COMPLETO_queda_listo(app, admin_client):
    _limpiar(app)
    _sembrar(app)
    p, _ = _mio(admin_client)
    assert p and p['listo'], 'un producto con todo cargado no queda listo: %s' % _ques(p)
    _limpiar(app)


def test_cada_hueco_dice_QUE_ROMPE(app, admin_client):
    """Un pendiente que no dice qué se pierde no se prioriza · y el peor de todos (sin
    presentación) es justo el más fácil de no ver: el producto no aparece en la demanda."""
    _limpiar(app)
    _sembrar(app, tapa='', caja='', sku='')
    p, _ = _mio(admin_client)
    assert _ques(p) == {'sin tapa', 'sin caja', 'sin SKU'}, _ques(p)
    for f in p['faltas']:
        assert f.get('rompe'), 'el hueco "%s" no dice qué rompe' % f['que']
    _limpiar(app)


def test_NO_LLEVA_cierra_el_pendiente(app, admin_client):
    """*"algunos no tienen tapa, no tienen caja y cosas así"*. Es una RESPUESTA: si contara como
    faltante, la lista no llegaría a cero nunca y dejaría de mirarse (M129)."""
    _limpiar(app)
    _sembrar(app, tapa='', caja='', sin_tapa=1, sin_caja=1)
    p, _ = _mio(admin_client)
    assert 'sin tapa' not in _ques(p) and 'sin caja' not in _ques(p), \
        'cuenta como faltante algo que se declaró que no lleva'
    assert p['listo'], 'no queda listo pese a estar todo resuelto: %s' % _ques(p)
    _limpiar(app)


def test_caza_el_codigo_FANTASMA(app, admin_client):
    """Apunta a algo que no está en el maestro: la compra no lo resuelve y no se compra nunca."""
    _limpiar(app)
    _sembrar(app, tapa='NO-EXISTE-999')
    p, _ = _mio(admin_client)
    assert 'tapa fantasma' in _ques(p), _ques(p)
    _limpiar(app)


def test_caza_la_DUPLICADA_solo_cuando_hace_dano(app, admin_client):
    """Dos filas del mismo tamaño con frascos DISTINTOS reparten la compra mitad y mitad. Con el
    MISMO frasco el reparto suma bien y no hay nada que corregir: avisar ahí sería ruido (M129)."""
    from database import get_db
    _limpiar(app)
    _sembrar(app)
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, stock_actual) VALUES ('NT-FR2','x',0)")
        # misma medida, MISMO frasco -> no es un problema
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, envase_codigo, tapa_codigo, caja_codigo, sku_shopify, activo) "
                  "VALUES (?,'V30B','30 ml',30,'NT-FR','NT-TAPA','NT-CAJA','SKU-NORM-B',1)", (PROD,))
        c.commit()
    p, _ = _mio(admin_client)
    assert 'duplicada' not in _ques(p), 'avisa con dos filas que usan el MISMO frasco'
    with app.app_context():
        c = get_db()
        c.execute("UPDATE producto_presentaciones SET envase_codigo='NT-FR2' "
                  " WHERE producto_nombre=? AND presentacion_codigo='V30B'", (PROD,))
        c.commit()
    p, _ = _mio(admin_client)
    assert 'duplicada' in _ques(p), 'no ve las dos del mismo tamaño con frascos distintos'
    _limpiar(app)


def test_el_producto_SIN_presentacion_no_desaparece(app, admin_client):
    """El peor hueco de todos y el más fácil de no ver: no aparece en ninguna fila de la demanda,
    así que su envase no se compra en absoluto (M124)."""
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO formula_headers (producto_nombre, unidad_base_g, lote_size_kg, activo) "
                  "VALUES (?, 30000, 30, 1)", (PROD,))
        c.commit()
    p, _ = _mio(admin_client)
    assert p and 'sin presentacion' in _ques(p), 'un producto sin presentación no aparece'
    _limpiar(app)


def test_el_avance_se_mide_en_PRODUCTOS_listos(app, admin_client):
    """Un porcentaje de campos llenos subiría aunque ningún producto quede utilizable."""
    _limpiar(app)
    _sembrar(app)
    _, j = _mio(admin_client)
    r = j['resumen']
    for k in ('productos', 'listos', 'faltan', 'pct'):
        assert k in r, 'el resumen no dice %s' % k
    assert r['listos'] + r['faltan'] == r['productos'], 'la cuenta no cierra'
    _limpiar(app)


def test_lo_INCOMPLETO_va_primero(app, admin_client):
    """Un tablero que hay que leer entero para encontrar el problema no se lee."""
    _, j = _mio(admin_client)
    ps = j['productos']
    listos = [i for i, p in enumerate(ps) if p['listo']]
    faltan = [i for i, p in enumerate(ps) if not p['listo']]
    if listos and faltan:
        assert max(faltan) < min(listos), 'los listos salen antes que lo que falta'


def test_se_VE_desde_la_pantalla(app):
    """Un indicador que no se muestra no cambia ninguna decisión (M121)."""
    import templates_py.dashboard_html as D
    todo = D.DASHBOARD_HTML + getattr(D, 'DASHBOARD_APP_JS', '')
    assert '/api/mee/normalizacion' in todo, 'la pantalla no consulta el estado'
    assert 'Normalizados' in todo, 'no se pinta el indicador'
