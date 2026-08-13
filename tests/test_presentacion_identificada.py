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
