# -*- coding: utf-8 -*-
"""Cada presentacion del reparto tiene que decir CUAL es y de donde salio su numero.

Sebastian, mirando el modal de un lote de blush: ocho tarjetas identicas, todas "60 uds de 6 ml ·
MEE-ENV-034". Los ocho tonos comparten volumen y frasco, asi que la tarjeta no mostraba nada que
los distinguiera -- y ademas todos con el mismo numero, sin forma de saber si eso estaba bien.

Un total sin su detalle no es informacion: es una afirmacion que el usuario no puede verificar
(M124). Y aca el dato ya viajaba desde el backend: lo unico que faltaba era pintarlo.
"""
import ast
import io
import os
import re

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api')


def _bloque_presentaciones():
    """El fragmento del modal que pinta las tarjetas del reparto."""
    src = io.open(os.path.join(RAIZ, 'templates_py', 'dashboard_html.py'),
                  encoding='utf-8').read()
    # Se lee el valor EVALUADO, no el fuente: los escapes de Python dan falsos negativos (M65).
    for n in ast.walk(ast.parse(src)):
        if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str) and 'De este lote salen' in n.value.value):
            v = n.value.value
            i = v.find('De este lote salen')
            return v[i:i + 4000]
    raise AssertionError('no encontré el bloque del reparto')


def test_la_tarjeta_dice_QUE_presentacion_es():
    """DIENTES · sin esto, ocho tonos del mismo volumen y frasco salen ocho tarjetas iguales."""
    b = _bloque_presentaciones()
    assert 'pp.etiqueta' in b and 'pp.presentacion_codigo' in b, (
        'la tarjeta no muestra la etiqueta ni el código de la presentación: los tonos que '
        'comparten volumen y frasco quedan indistinguibles')
    assert 'sin identificar' in b, (
        'una presentación sin nombre tiene que DECIRLO, no salir en blanco como las demás')


def test_la_tarjeta_dice_de_donde_salio_su_numero():
    """El reparto sale de las ventas de cada presentación · si son cero, el reparto es parejo y
    eso hay que poder VERLO en vez de deducirlo de que todos los números sean iguales."""
    b = _bloque_presentaciones()
    assert 'ventas_90d_uds' in b
    assert 'reparto parejo' in b, (
        'cuando no hay ventas propias el reparto es uniforme, y la tarjeta tiene que decirlo')


def test_el_backend_manda_lo_que_la_tarjeta_necesita():
    """Que la pantalla lo pinte no sirve si el dato no viaja · se verifican las dos puntas."""
    src = io.open(os.path.join(RAIZ, 'blueprints', 'programacion.py'), encoding='utf-8').read()
    i = src.find('variantes_out.append({')
    assert i > 0, 'no encontré el armado de las variantes'
    bloque = src[i:i + 1200]
    for campo in ("'presentacion_codigo'", "'etiqueta'", "'sku_shopify'", "'ventas_90d_uds'"):
        assert campo in bloque, 'el backend no manda %s' % campo


# ─────────────────────────────────────────────────────────────────────────────────────────────
# El CUARTO repartidor · usa las ventas de Shopify, no la columna que se llena a mano
# ─────────────────────────────────────────────────────────────────────────────────────────────

import pytest

TEST_PASSWORD = "TestPass123"


def _limpiar(app):
    with app.app_context():
        from database import get_db
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre='REPARTO TONOS'")
        c.execute("DELETE FROM sku_producto_map WHERE producto_nombre='REPARTO TONOS'")
        c.execute("DELETE FROM ventas_diarias WHERE sku LIKE 'RT%'")
        conn.commit()


def test_el_reparto_usa_las_ventas_de_shopify_no_la_columna_manual(app):
    """DIENTES · tres tonos del MISMO volumen y frasco, con ventas muy distintas.

    Esta funcion pesaba con `ventas_mes_referencia`, una columna que se llena A MANO y que las
    filas nuevas tienen en CERO: caia a "estimado por volumen" y, como los tonos comparten los
    6 ml, repartia IGUAL para los tres. Sebastian lo vio en pantalla: ocho tarjetas de 60 uds.

    Los otros tres repartidores ya usaban `_unidades_por_presentacion`; este era el cuarto sin la
    regla (M45/M180).
    """
    _limpiar(app)
    with app.app_context():
        from database import get_db
        from blueprints.plan import _envases_para_kg
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM maestro_mee WHERE codigo='RT-ENV'")
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual) "
                  "VALUES ('RT-ENV','FRASCO REPARTO 6ml','Frasco',99999)")
        # tres tonos, mismo volumen y mismo frasco: lo unico que los distingue es su SKU
        for cod, sku in (('T-ALTO', 'RTALTO'), ('T-MEDIO', 'RTMEDIO'), ('T-BAJO', 'RTBAJO')):
            c.execute(
                "INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                "etiqueta, volumen_ml, envase_codigo, sku_shopify, ventas_mes_referencia, "
                "activo, es_default) VALUES ('REPARTO TONOS',?,?,6,'RT-ENV',?,0,1,0)",
                (cod, cod, sku))
            c.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) "
                      "VALUES (?, 'REPARTO TONOS', 6, 1)", (sku,))
        # y ventas MUY distintas entre ellos · el motor las lee de `ventas_diarias`, que es la
        # tabla que el cron precalcula (el fast-path que evita reparsear las ordenes · M43/M128)
        from datetime import datetime as _d, timedelta as _t
        f = (_d.utcnow() - _t(days=10)).strftime('%Y-%m-%d')
        for sku, n in (('RTALTO', 60), ('RTMEDIO', 20), ('RTBAJO', 4)):
            c.execute("INSERT INTO ventas_diarias (fecha, sku, cantidad) VALUES (?,?,?)",
                      (f, sku, n))
        conn.commit()

        res = _envases_para_kg(c, conn, 'REPARTO TONOS', 10.0)

    pres = {p.get('presentacion_codigo'): p for p in (res.get('presentaciones') or [])}
    assert len(pres) >= 2, 'no salieron las presentaciones: %s' % res.get('nota')
    # cada tarjeta se identifica
    assert all(k for k in pres), 'alguna presentación llegó sin identificar'
    # y el reparto NO es parejo: el que mas vende se lleva mas
    if 'T-ALTO' in pres and 'T-BAJO' in pres:
        assert pres['T-ALTO']['uds'] > pres['T-BAJO']['uds'], (
            'reparto parejo con ventas muy distintas: %s'
            % {k: v['uds'] for k, v in pres.items()})
        assert res.get('fuente_reparto') == 'ventas por presentación', res.get('fuente_reparto')


def test_sin_SKU_no_empeora_nada(app):
    """El borde que hace seguro el cambio: sin SKUs se comporta como antes (por volumen).

    Sin este test, el anterior pasaria con un repartidor que exigiera SKU y dejara sin reparto a
    todos los productos que no lo declaran, que son la mayoria.
    """
    _limpiar(app)
    with app.app_context():
        from database import get_db
        from blueprints.plan import _envases_para_kg
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM maestro_mee WHERE codigo='RT-ENV'")
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual) "
                  "VALUES ('RT-ENV','FRASCO REPARTO 6ml','Frasco',99999)")
        for cod, vol in (('V10', 10), ('V30', 30)):
            c.execute(
                "INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                "etiqueta, volumen_ml, envase_codigo, sku_shopify, ventas_mes_referencia, "
                "activo, es_default) VALUES ('REPARTO TONOS',?,?,?,'RT-ENV','',0,1,0)",
                (cod, cod, vol))
        conn.commit()
        res = _envases_para_kg(c, conn, 'REPARTO TONOS', 10.0)
    assert res.get('presentaciones'), 'sin SKU dejo de repartir: eso romperia la mayoria'
    assert res.get('fuente_reparto') == 'estimado por volumen'
