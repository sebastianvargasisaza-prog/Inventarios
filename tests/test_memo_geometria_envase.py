# -*- coding: utf-8 -*-
"""El memo de la geometría del envase acelera SIN cambiar la respuesta, y muere con el request.

Resolver "cuántos ml trae una unidad de este producto" cuesta hasta 3 consultas y se llama una vez
por SKU. Medido con la sonda local: `/api/plan/necesidades` lo pedía 47 veces para 22 productos
(BLUSH BALM 9 veces, una por tono) y `/api/plan/dashboard` 94 veces para los mismos 22, porque
recorre la lista dos veces con ventanas de venta distintas. Sobre PostgreSQL cada consulta es un
viaje de red: eso es latencia pura en la pantalla que más se abre.

Los dos guards que importan son de correctitud, no de velocidad:

  1. **la respuesta no cambia** · un atajo que puede contestar distinto al camino lento no es un
     atajo, es otra respuesta (M128, que costó SKUs reales con velocidad cero);
  2. **el memo muere con el request** · si alguien lo pasa a cache de módulo, una presentación
     recién editada dejaría de verse hasta que el worker se recicle (M9), y eso no da error: da un
     número viejo con cara de número bueno.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))


def test_el_memo_NO_cambia_la_respuesta(app, admin_client):
    """Mismo endpoint con el memo puesto y con el memo esquivado: idéntico."""
    from blueprints import auto_plan as ap

    r1 = admin_client.get('/api/plan/necesidades')
    assert r1.status_code == 200

    # se esquiva el memo llamando al camino lento directo
    orig = ap._factor_g_por_unidad_detalle
    ap._factor_g_por_unidad_detalle = ap._factor_g_por_unidad_detalle_impl
    orig_v = ap._volumen_sku
    ap._volumen_sku = ap._volumen_sku_impl
    try:
        r2 = admin_client.get('/api/plan/necesidades')
    finally:
        ap._factor_g_por_unidad_detalle = orig
        ap._volumen_sku = orig_v
    assert r2.status_code == 200
    assert r1.data == r2.data, 'el memo devuelve algo distinto del camino lento'


def test_el_memo_MUERE_con_el_request(app, admin_client):
    """Editar el volumen de una presentación tiene que verse en la carga SIGUIENTE.

    Es la razón por la que el memo va en `flask.g` y no en una variable de módulo: un cache de
    módulo sobrevive al request y dejaría al usuario mirando el número viejo, sin ningún error a
    la vista (M9).
    """
    from database import get_db
    from blueprints.auto_plan import _factor_g_por_unidad_detalle as fgpu

    PROD = 'MEMOGEO PRODUCTO'
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM sku_planeacion_config WHERE producto_nombre=?", (PROD,))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, activo, es_default) VALUES (?,?,?,?,1,1)",
                  (PROD, 'V30', '30 ml', 30))
        c.commit()

    with app.app_context():
        v1 = fgpu(get_db(), PROD)[0]
        # dentro del MISMO contexto el memo contesta lo mismo (ese es su trabajo)
        assert fgpu(get_db(), PROD)[0] == v1
    assert v1 == 30, 'no leyó el volumen cargado'

    with app.app_context():
        c = get_db()
        c.execute("UPDATE producto_presentaciones SET volumen_ml=50 WHERE producto_nombre=?", (PROD,))
        c.commit()

    with app.app_context():
        v2 = fgpu(get_db(), PROD)[0]
    assert v2 == 50, ('el memo sobrevivió al request · una presentación editada seguiría '
                      'mostrando el volumen viejo')

    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        c.commit()


def test_el_pres_devuelto_es_una_COPIA(app):
    """`pres` es un dict y aguas abajo hay quien lo muta. Si se devolviera la referencia guardada,
    el primer caller que le toque una clave se la cambiaría a todos los siguientes del mismo
    request -- un bug que aparece lejos de su causa."""
    from database import get_db
    from blueprints.auto_plan import _factor_g_por_unidad_detalle as fgpu

    PROD = 'MEMOGEO COPIA'
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, activo, es_default) VALUES (?,?,?,?,1,1)",
                  (PROD, 'V30', '30 ml', 30))
        c.commit()
        # ⚠ Se muta el resultado de CADA llamada, no sólo el de la primera: la primera es un
        # fallo de memo (ya devolvía copia por otro camino) y mutarla sólo a ella deja el guard
        # probando el caso sano · probado, pasaba VERDE con el bug puesto (M152).
        for _ in range(2):
            r = fgpu(get_db(), PROD)[3]
            assert isinstance(r, dict)
            r['volumen_ml'] = 999      # el caller lo muta
        b = fgpu(get_db(), PROD)[3]
        assert b['volumen_ml'] == 30, 'el memo entregó la MISMA referencia · un caller se la pisa a otro'
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        c.commit()


def test_fuera_de_un_request_sigue_funcionando(app):
    """Los crons llaman a estos helpers sin contexto de Flask · ahí no hay memo y el
    comportamiento tiene que ser el de siempre, no una excepción."""
    from database import db_connect
    from blueprints.auto_plan import _factor_g_por_unidad_detalle as fgpu, _volumen_sku as vsku
    con = db_connect(timeout=30)
    try:
        assert fgpu(con, 'PRODUCTO QUE NO EXISTE')[0] > 0     # cae al default, no revienta
        assert vsku(con, 'SKU-QUE-NO-EXISTE', 'PRODUCTO QUE NO EXISTE')[0] > 0
    finally:
        con.close()


def test_los_CATALOGOS_de_volumen_se_leen_una_vez(app, admin_client):
    """`_volumen_sku` disparaba DOS consultas por SKU, y en Necesidades son 47 SKUs distintos: 94
    consultas para leer dos tablas que caben enteras en memoria. Sobre PostgreSQL son 94 viajes de
    red para resolver algo que se resuelve con dos.

    Medido: /plan/necesidades 221 -> 129 consultas, /plan/dashboard 276 -> 184, salud-cadenas
    222 -> 130, con el payload byte a byte idéntico.
    """
    from blueprints import auto_plan as ap

    r1 = admin_client.get('/api/plan/necesidades')
    assert r1.status_code == 200

    # el camino lento (sin mapas) tiene que dar EXACTAMENTE lo mismo
    orig = ap._mapas_volumen
    ap._mapas_volumen = lambda c: None
    try:
        r2 = admin_client.get('/api/plan/necesidades')
    finally:
        ap._mapas_volumen = orig
    assert r2.status_code == 200
    assert r1.data == r2.data, 'leer los catálogos de una cambia el resultado'


def test_el_mapa_de_presentaciones_elige_la_MISMA_fila_que_el_LIMIT_1(app):
    """Es el punto donde un atajo así se rompe en silencio: la consulta que reemplaza ordenaba por
    `es_default DESC, id ASC` y se quedaba con la primera. Si el mapa eligiera otra fila, el
    volumen cambiaría y con él los kg del plan, sin un solo error a la vista (M128).
    """
    from database import get_db
    from blueprints.auto_plan import _volumen_sku_impl
    SKU = 'MAPAVOL-30'
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE sku_shopify=?", (SKU,))
        c.execute("DELETE FROM sku_producto_map WHERE sku=?", (SKU,))
        # ⚠ La DEFAULT va PRIMERO (id menor) a propósito: si fuera al revés, ordenar por
        # `es_default DESC` y ordenar por `id ASC` darían el MISMO resultado y el guard estaría
        # midiendo el caso donde da igual · probado, así pasaba verde con el ORDER BY roto (M152).
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, sku_shopify, activo, es_default) "
                  "VALUES ('MAPAVOL PROD','VB','b',50,?,1,1)", (SKU,))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, sku_shopify, activo, es_default) "
                  "VALUES ('MAPAVOL PROD','VA','a',10,?,1,0)", (SKU,))
        c.commit()
        vol, fuente = _volumen_sku_impl(get_db(), SKU, 'MAPAVOL PROD')
    assert (vol, fuente) == (50.0, 'presentacion'), \
        'el mapa eligió una fila distinta de la que elegía el LIMIT 1: %s %s' % (vol, fuente)
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE sku_shopify=?", (SKU,))
        c.commit()


def test_sin_contexto_de_flask_sigue_resolviendo(app):
    """Los crons llaman a esto sin request · ahí no hay mapas y cada caller consulta como siempre."""
    from database import db_connect
    from blueprints.auto_plan import _mapas_volumen, _volumen_sku_impl
    con = db_connect(timeout=30)
    try:
        assert _mapas_volumen(con) is None, 'fuera de un request no debería armar mapas'
        assert _volumen_sku_impl(con, 'SKU-INEXISTENTE', 'PRODUCTO QUE NO EXISTE')[0] > 0
    finally:
        con.close()
