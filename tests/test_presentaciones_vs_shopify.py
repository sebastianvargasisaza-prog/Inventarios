# -*- coding: utf-8 -*-
"""El rastreo de las presentaciones CONTRA lo que Shopify vende.

Sebastián (7-ago): *"lo ideal es que sea el rastreo tal cual de Shopify, porque así sabemos qué
falta · Shopify tiene muchas cosas, regalos y variantes, pero yo había escogido cuáles quedaban y
cuáles no"*.

El punto de este diagnóstico es que los cuatro desencuentros se vean SEPARADOS: sus arreglos son
opuestos (un SKU sin mapeo se mapea; una presentación sin SKU se completa o se apaga), y mezclarlos
en un solo "hay 12 cosas mal" obliga a adivinar cuál es cuál -- que es como nació el duplicado.
"""
import json


def _seed(app, con_ventas=True):
    """Universo propio y limpio ANTES de sembrar · otros archivos escriben en estas mismas
    tablas y un agregado que no controla su universo pasa aislado y falla en el gate (M102/M103)."""
    # ⚠ Se siembra por la conexión de la APP, no por una segunda: la app arranca sus crons al
    # importarse y una conexión aparte choca contra el lock de escritura ("database is locked",
    # y con `timeout` sólo se convierte en 30 s de espera). Además así funciona igual en PG.
    with app.app_context():
        from database import get_db
        c = get_db()
        for sql in (
            "DELETE FROM producto_presentaciones WHERE producto_nombre LIKE 'PVS %'",
            "DELETE FROM sku_producto_map WHERE sku LIKE 'PVS-%'",
            "DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'PVS-%'",
        ):
            c.execute(sql)
        _seed_filas(c, con_ventas)
        c.commit()


def _seed_filas(c, con_ventas):

    # Curaduría: 4 SKUs · uno normal, uno regalo, uno apagado, uno sin mapear (no se inserta)
    for sku, prod, activo, regalo, vol in (
        ('PVS-A-30', 'PVS SUERO', 1, 0, 30),
        ('PVS-A-15', 'PVS SUERO', 1, 0, 15),     # vende y su tamaño NO tiene presentación
        ('PVS-REGALO', 'PVS SUERO', 1, 1, 30),
        ('PVS-VIEJO', 'PVS SUERO', 0, 0, 30),
    ):
        c.execute("INSERT INTO sku_producto_map (sku, producto_nombre, activo, es_regalo, volumen_ml) "
                  "VALUES (?,?,?,?,?)", (sku, prod, activo, regalo, vol))

    # Presentaciones: DOS de 30 ml con frascos distintos (el duplicado real) + una sin SKU
    for cod, etq, vol, env, sku in (
        ('V30', '30 ml', 30, 'MEE-001', 'PVS-A-30'),
        ('V30B', '30 ml bis', 30, 'MEE-002', ''),      # duplicada Y sin SKU
        ('V50', '50 ml', 50, 'MEE-003', ''),           # sólo sin SKU
    ):
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, envase_codigo, sku_shopify, activo) VALUES (?,?,?,?,?,?,1)",
                  ('PVS SUERO', cod, etq, vol, env, sku))

    if con_ventas:
        # Una orden real: el endpoint pide la lista COMPLETA de SKUs vendidos (forzar_ordenes),
        # así que tiene que salir de las ÓRDENES, no de la tabla precalculada (M128).
        items = [{'sku': s, 'cantidad': n} for s, n in
                 (('PVS-A-30', 5), ('PVS-A-15', 3), ('PVS-REGALO', 2),
                  ('PVS-VIEJO', 1), ('PVS-HUERFANO', 7))]
        c.execute("INSERT INTO animus_shopify_orders (shopify_id, creado_en, sku_items, estado, estado_pago) "
                  "VALUES (?, date('now','-5 hours'), ?, 'fulfilled', 'paid')",
                  ('PVS-1', json.dumps(items)))


def _pedir(admin_client):
    r = admin_client.get('/api/programacion/presentaciones-vs-shopify?dias=90')
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def test_el_SKU_que_vende_y_nadie_mapeo_SALE(app, admin_client):
    """Es el "¿qué falta?" literal: Shopify lo vende y EOS no sabe de qué producto es, así que esa
    venta no empuja ninguna producción ni la compra de su envase."""
    _seed(app)
    j = _pedir(admin_client)
    assert j['medido'] is True, j.get('avisos')
    skus = {x['sku'] for x in j['vende_sin_mapeo']}
    assert 'PVS-HUERFANO' in skus, 'no detecta el SKU que vende sin mapeo'
    assert 'PVS-A-30' not in skus, 'acusa a un SKU que SÍ está mapeado'


def test_el_tamano_sin_presentacion_SALE_y_el_que_si_tiene_NO(app, admin_client):
    """Sin presentación para ese volumen, su frasco/tapa/caja no entran a la compra."""
    _seed(app)
    j = _pedir(admin_client)
    faltan = {(x['sku'], x['volumen_ml']) for x in j['sin_presentacion']}
    assert ('PVS-A-15', 15) in faltan, 'no ve el tamaño que no tiene presentación'
    assert not any(s == 'PVS-A-30' for s, _ in faltan), \
        'marca como faltante un tamaño que SÍ tiene presentación'


def test_su_CURADURIA_no_se_cuenta_como_hueco_pero_se_VE(app, admin_client):
    """*"yo había escogido cuáles quedaban y cuáles no"*. Un regalo o un SKU que él apagó no es un
    hueco -- pero tampoco desaparece: un descarte que no se ve se lee como que nunca existió (M124).
    """
    _seed(app)
    j = _pedir(admin_client)
    falt = {x['sku'] for x in j['vende_sin_mapeo']} | {x['sku'] for x in j['sin_presentacion']}
    assert 'PVS-REGALO' not in falt, 'cuenta un regalo como hueco'
    assert 'PVS-VIEJO' not in falt, 'cuenta como hueco un SKU que él apagó'
    exc = j['excluidos_por_curaduria']
    assert 'PVS-REGALO' in {x['sku'] for x in exc['regalos']}, 'el regalo desapareció sin decirlo'
    assert 'PVS-VIEJO' in {x['sku'] for x in exc['apagados']}, 'el apagado desapareció sin decirlo'


def test_la_presentacion_SIN_SKU_sale_aparte(app, admin_client):
    """Sin SKU no se puede cruzar contra lo que se vende: no se sabe si sobra o si le falta el dato.
    Va en su propia lista porque su arreglo es el OPUESTO al del SKU sin mapeo."""
    _seed(app)
    j = _pedir(admin_client)
    cods = {(x['producto'], x['volumen_ml']) for x in j['sin_sku']}
    assert ('PVS SUERO', 50) in cods, 'no lista la presentación sin SKU'
    assert ('PVS SUERO', 30) in cods, 'la duplicada sin SKU tampoco se rastrea y no sale'


def test_las_DOS_del_mismo_tamano_salen_con_sus_dos_frascos(app, admin_client):
    """El motor reparte la compra por las ventas de ese volumen: con dos filas encendidas del mismo
    tamaño el reparto queda mitad y mitad y se compra la MEZCLA equivocada, con los totales
    cuadrando -- por eso es invisible y por eso hay que nombrarlo (M5/M124)."""
    _seed(app)
    j = _pedir(admin_client)
    dup = [d for d in j['duplicadas'] if d['producto'] == 'PVS SUERO' and d['volumen_ml'] == 30]
    assert dup, 'no detecta las dos presentaciones de 30 ml'
    d = dup[0]
    assert d['frascos_distintos'] is True, 'no distingue el caso que HACE daño (frascos distintos)'
    assert len(d['filas']) == 2
    # y se dice qué vendió cada una: es el dato con el que él decide cuál conservar
    ventas = {f['codigo']: f['uds_shopify'] for f in d['filas']}
    assert ventas.get('V30') == 5, 'no trae las ventas del SKU de la fila'
    assert ventas.get('V30B') is None, 'inventa ventas para una fila que no tiene SKU'


def test_si_no_se_pudo_MEDIR_lo_dice_en_vez_de_devolver_CERO(app, admin_client, monkeypatch):
    """Un cero que nadie calculó se lee como "no hay nada que hacer" y significa lo contrario:
    "no se miró" (M100/M154)."""
    _seed(app, con_ventas=False)
    from blueprints import auto_plan as _ap

    def _boom(*a, **k):
        raise RuntimeError('shopify caído')
    monkeypatch.setattr(_ap, '_ventas_sku_map_orders', _boom)
    j = _pedir(admin_client)
    assert j['medido'] is False, 'dice que midió cuando no pudo'
    assert j['avisos'], 'no avisa por qué la lista está vacía'
    assert j['resumen']['skus_vendidos'] is None, 'un cero inventado se lee como "todo bien"'
    # lo que NO depende de Shopify se sigue midiendo igual
    assert j['resumen']['duplicadas'] >= 1, 'perdió los chequeos que sí podía hacer'


def test_el_rastreo_se_puede_ABRIR_desde_la_pantalla(app):
    """Un diagnóstico al que no se llega desde ninguna parte no existe (M121). Y va detrás de un
    BOTÓN, no en la carga del modal: el cruce recorre las órdenes de Shopify (necesita la lista
    completa de SKUs vendidos, no la tabla precalculada) y eso en un path de carga satura los
    workers · es la causa raíz de las caídas de M43/M59."""
    import os as _os
    import re as _re
    import sys as _sys
    _sys.path.insert(0, _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'api'))
    import templates_py.dashboard_html as D
    html = D.DASHBOARD_HTML
    todo = html + getattr(D, 'DASHBOARD_APP_JS', '') + getattr(D, 'DASHBOARD_CORE_JS', '')
    assert 'empqRastreo()' in html, 'no hay botón que dispare el rastreo'
    assert _re.search(r'function\s+empqRastreo\s*\(', todo), 'el botón llama a una función que no existe'
    assert 'id="empq-rastreo"' in html, 'el destino donde se pinta no existe'
    # y NO se dispara solo al abrir el modal
    # ⚠ La ventana se corta en la PRÓXIMA función sea `function` o `async function`: buscando sólo
    # la primera forma, la ventana se pasaba de largo y medía la función de al lado · un guard
    # anclado flojo mide código ajeno y da rojo con el código correcto (M151/M165).
    i = todo.find('async function empqAbrir')
    assert i > 0, 'no encuentro empqAbrir'
    _sig = _re.compile(r'\n(?:async )?function ')
    _m = _sig.search(todo, i + 10)
    j = _m.start() if _m else -1
    assert 'empqRastreo' not in todo[i:j if j > i else i + 4000], \
        'el rastreo corre en la CARGA del modal · recorrer las órdenes ahí satura los workers (M43)'
