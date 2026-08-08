# -*- coding: utf-8 -*-
"""El SKU de Shopify se deduce del TONO, y COMPLETA la presentación que ya existe.

Sebastián (8-ago), mirando LIP SERUM en la pantalla: *"vendemos varios tonos, pero veo que no los
está jalando en Shopify -- dice lip serum mocca, peach, merlot, y el envase para cada uno dice los
mismos nombres, pero veo que no los rastrea"*.

Tenía razón y la causa estaba a la vista: el tono está escrito en los DOS lados (el SKU
`GLOSSPEACH` y el frasco `LIPS GLOSS PEACH`), así que el vínculo se puede deducir. Lo que fallaba
es que el emparejador viejo **CREABA una presentación nueva por tono** (`TONO-<sku>`) en vez de
completar la que ya estaba: por eso el producto quedó con dos juegos de filas, unas mostrando su
venta y otras diciendo "SKU sin asignar", y encima disparando la alerta de duplicadas.

⚠ Deduce, NO adivina. Emparejar por parecido sin que nadie lo mire es como se le atribuye la venta
al tono equivocado (M19/M137).
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

PROD = 'TONO TEST PROD'


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'TTX-%'")
        c.commit()


def _sembrar(app, frascos, skus):
    from database import get_db
    with app.app_context():
        c = get_db()
        for cod, de in frascos:
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, stock_actual) VALUES (?,?,0)",
                      (cod, de))
        for sk in skus:
            c.execute("INSERT INTO sku_producto_map (sku, producto_nombre, activo, es_regalo) "
                      "VALUES (?,?,1,0)", (sk, PROD))
        for i, (cod, _de) in enumerate(frascos):
            c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                      "etiqueta, volumen_ml, envase_codigo, activo) VALUES (?,?,?,10,?,1)",
                      (PROD, 'V10-%d' % i, '10 ml', cod))
        c.commit()


def _ids(app):
    from database import get_db
    with app.app_context():
        return [r[0] for r in get_db().execute(
            "SELECT id FROM producto_presentaciones WHERE producto_nombre=? ORDER BY id",
            (PROD,)).fetchall()]


def _prop(admin_client):
    r = admin_client.get('/api/programacion/sku-por-tono')
    assert r.status_code == 200, r.data[:200]
    j = r.get_json()
    return [x for x in (j.get('propuestas') or []) if x['producto'] == PROD], j


def test_empareja_cada_TONO_con_su_SKU(app, admin_client):
    _limpiar(app)
    _sembrar(app,
             [('TTX-PEACH', 'LIPS GLOSS PEACH'), ('TTX-MERLOT', 'LIPS GLOSS MERLOT'),
              ('TTX-MALVA', 'LIPS GLOSS MALVA')],
             ['GLOSSPEACHX', 'GLOSSMERLOTX', 'GLOSSMALVAX'])
    props, _ = _prop(admin_client)
    por = {x['frasco']: x['sku'] for x in props}
    assert por.get('TTX-PEACH') == 'GLOSSPEACHX'
    assert por.get('TTX-MERLOT') == 'GLOSSMERLOTX'
    assert por.get('TTX-MALVA') == 'GLOSSMALVAX'
    _limpiar(app)


def test_COMPLETA_la_fila_que_existe_y_no_crea_otra(app, admin_client):
    """Es el punto: crear una presentación por tono fue lo que dejó el producto con dos juegos y
    disparó la alerta de duplicadas."""
    from database import get_db
    _limpiar(app)
    _sembrar(app, [('TTX-PEACH', 'LIPS GLOSS PEACH')], ['GLOSSPEACHX'])
    with app.app_context():
        antes = get_db().execute("SELECT COUNT(*) FROM producto_presentaciones "
                                 " WHERE producto_nombre=?", (PROD,)).fetchone()[0]
    props, _ = _prop(admin_client)
    r = admin_client.post('/api/programacion/sku-por-tono-aplicar',
                          json={'pares': [{'id': x['id'], 'sku': x['sku']} for x in props]},
                          headers={'Origin': 'http://localhost'})
    assert r.status_code == 200 and r.get_json()['aplicados'] == 1
    with app.app_context():
        c = get_db()
        despues = c.execute("SELECT COUNT(*) FROM producto_presentaciones "
                            " WHERE producto_nombre=?", (PROD,)).fetchone()[0]
        sku = c.execute("SELECT sku_shopify FROM producto_presentaciones "
                        " WHERE producto_nombre=?", (PROD,)).fetchone()[0]
    assert despues == antes, 'creó una presentación nueva en vez de completar la existente'
    assert sku == 'GLOSSPEACHX'
    _limpiar(app)


def test_si_DOS_SKU_empatan_NO_elige(app, admin_client):
    """Emparejar por parecido sin que nadie lo mire es como se le atribuye la venta al tono
    equivocado (M19/M137: el guard mide la ambigüedad de la COSA, no de quién tiene stock)."""
    _limpiar(app)
    _sembrar(app, [('TTX-ROSA', 'LIPS GLOSS ROSA')], ['GLOSSROSAX', 'GLOSSROSAY'])
    props, j = _prop(admin_client)
    assert not props, 'eligió uno de dos candidatos empatados'
    assert [x for x in (j.get('ambiguas') or []) if x['producto'] == PROD], \
        'no declara la ambigüedad · se resolvería sola'
    _limpiar(app)


def test_NO_cruza_el_SKU_de_OTRO_producto(app, admin_client):
    """El tono puede repetirse entre productos (dos líneas con un 'peach'). Cruzarlos le daría a
    un producto la venta del otro."""
    from database import get_db
    _limpiar(app)
    _sembrar(app, [('TTX-PEACH', 'LIPS GLOSS PEACH')], [])
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM sku_producto_map WHERE sku='GLOSSPEACHOTRO'")
        c.execute("INSERT INTO sku_producto_map (sku, producto_nombre, activo, es_regalo) "
                  "VALUES ('GLOSSPEACHOTRO','OTRO PRODUCTO DISTINTO',1,0)")
        c.commit()
    props, _ = _prop(admin_client)
    assert not props, 'le asignó el SKU de otro producto'
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM sku_producto_map WHERE sku='GLOSSPEACHOTRO'")
        c.commit()
    _limpiar(app)


def test_un_SKU_no_puede_quedar_en_DOS_presentaciones(app, admin_client):
    """Si dos filas dicen vender el mismo SKU, su venta se cuenta dos veces y el reparto de
    envases sale mal · que es el mismo daño de las presentaciones duplicadas."""
    from database import get_db
    _limpiar(app)
    _sembrar(app, [('TTX-PEACH', 'LIPS GLOSS PEACH'), ('TTX-PEACH2', 'LIPS GLOSS PEACH')],
             ['GLOSSPEACHX'])
    r = admin_client.post('/api/programacion/sku-por-tono-aplicar',
                          json={'pares': [{'id': i, 'sku': 'GLOSSPEACHX'} for i in _ids(app)]},
                          headers={'Origin': 'http://localhost'})
    assert r.status_code == 200
    with app.app_context():
        n = get_db().execute("SELECT COUNT(*) FROM producto_presentaciones "
                             " WHERE producto_nombre=? AND sku_shopify='GLOSSPEACHX'",
                             (PROD,)).fetchone()[0]
    assert n == 1, 'el mismo SKU quedó en %d presentaciones' % n
    _limpiar(app)


def test_NO_pisa_un_SKU_cargado_a_mano(app, admin_client):
    from database import get_db
    _limpiar(app)
    _sembrar(app, [('TTX-PEACH', 'LIPS GLOSS PEACH')], ['GLOSSPEACHX'])
    with app.app_context():
        c = get_db()
        c.execute("UPDATE producto_presentaciones SET sku_shopify='PUESTO-A-MANO' "
                  " WHERE producto_nombre=?", (PROD,))
        c.commit()
    for i in _ids(app):
        admin_client.post('/api/programacion/sku-por-tono-aplicar',
                          json={'pares': [{'id': i, 'sku': 'GLOSSPEACHX'}]},
                          headers={'Origin': 'http://localhost'})
    with app.app_context():
        v = get_db().execute("SELECT sku_shopify FROM producto_presentaciones "
                             " WHERE producto_nombre=?", (PROD,)).fetchone()[0]
    assert v == 'PUESTO-A-MANO', 'pisó un SKU que alguien había cargado a mano'
    _limpiar(app)


def test_se_puede_ABRIR_desde_la_pantalla(app):
    import re
    import templates_py.dashboard_html as D
    html = D.DASHBOARD_HTML
    todo = html + getattr(D, 'DASHBOARD_APP_JS', '')
    assert 'empqSkuTono()' in html, 'no hay botón'
    assert re.search(r'(?:async )?function\s+empqSkuTono\s*\(', todo), \
        'el botón llama a una función que no existe'
    assert 'sku-por-tono-aplicar' in todo, 'no puede aplicar lo que propone'
