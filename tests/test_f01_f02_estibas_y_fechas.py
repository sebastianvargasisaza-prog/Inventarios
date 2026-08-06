# -*- coding: utf-8 -*-
"""Tres pedidos de Alejandro sobre los formatos F01/F02 (6-ago).

1. **Falta ESTIBAS** en la ubicación de bodega: hay material que no va ni a estantería ni a
   nevera, y sin la opción quedaba forzado a mentir (o a dejar la ubicación en blanco, que es el
   dato que después el rótulo imprime y el conteo cíclico agrupa · M115).
2. **El F02 decía "Lote (interno)"** -- se le quita el "interno". El código interno es otra cosa
   y está en su propio campo; llamar así al lote invita a confundirlos justo en el formato que
   libera el material.
3. **Toda fecha de F01/F02 con CALENDARIO y leída "28 diciembre 2028".** El F02 pedía sus tres
   fechas como texto libre.

⚠ La fecha larga se arma con los COMPONENTES de la cadena ISO, nunca con `new Date(iso)`: eso lo
interpreta como UTC y en Colombia muestra el día ANTERIOR (M106/M24). En un registro regulado un
día corrido no es un detalle de formato, es un dato falso.
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))


def _html():
    from templates_py.calidad_html import CALIDAD_HTML
    return CALIDAD_HTML


def test_ESTIBAS_es_una_opcion_de_ubicacion(app):
    h = _html()
    assert '>Estibas<' in h, 'no está la opción'
    assert "if(t === 'estibas') return 'Estibas'" in h, (
        'la opción existe pero no produce texto · se guardaría vacía y el rótulo saldría sin '
        'ubicación')


def test_estibas_esconde_estanteria_y_posicion(app):
    """Pedir estantería y posición para algo que va en estibas es pedir un dato que no existe."""
    h = _html()
    i = h.find('function _rcUbicTipo')
    bloque = h[i:i + 400]
    assert "t==='estibas'" in bloque, 'al elegir estibas sigue pidiendo estantería'


def test_un_registro_VIEJO_guardado_como_estiba_se_reconoce(app):
    """La ubicación se guardaba como texto libre. Si al reabrir el F01 no se reconoce, el
    registro viejo se lee como una estantería vacía y se pierde el dato (M115)."""
    h = _html()
    assert "indexOf('ESTIBA')===0" in h, 'no reconoce lo ya guardado como estiba'


def test_el_F02_ya_no_dice_lote_INTERNO(app):
    h = _html()
    assert 'Lote (interno)' not in h, 'volvió el rótulo viejo'
    assert "_rcFld('Lote'," in h, 'se perdió el campo de lote del F02'


def test_las_TRES_fechas_del_F02_tienen_calendario(app):
    """Eran texto libre: cada quien escribía en un formato distinto y no había forma de
    ordenarlas ni de compararlas."""
    h = _html()
    for campo in ('f02_fecha_recepcion', 'f02_fecha_analisis', 'f02_fecha_vencimiento'):
        assert ("_rcDate('%s'" % campo) in h, '%s sigue siendo texto libre' % campo
        assert ("_rcInput('%s'" % campo) not in h, '%s quedó duplicado' % campo


def test_la_fecha_se_LEE_como_28_diciembre_2028(app):
    h = _html()
    i = h.find('function _rcFechaLarga')
    assert i > 0, 'no existe el formateador'
    bloque = h[i:i + 700]
    assert 'diciembre' in bloque, 'no tiene los meses en español'
    assert '_rcDateSync' in h, 'la fecha larga no se actualiza al elegir en el calendario'


def test_la_fecha_larga_NO_se_arma_con_new_Date(app):
    """`new Date('2028-12-28')` es UTC: en Colombia imprime el 27. En un registro regulado eso
    es un dato falso, no un detalle de formato (M106/M24)."""
    from check_js_animus import _sin_ruido
    h = _html()
    i = h.find('function _rcFechaLarga')
    j = h.find('function _rcDateSync')
    assert 0 < i < j
    # ⚠ sin quitar los comentarios este test encuentra MI PROPIO comentario explicando por qué
    # no se usa `new Date` y falla con el código correcto (M154 · me pasó todo el día).
    bloque = _sin_ruido(h[i:j])
    assert 'new Date' not in bloque, 'volvió a construir la fecha con new Date · corre un día'
    assert re.search(r'\\d\{4\}|\\d\{2\}', bloque) or 'exec(' in bloque, (
        'ya no parsea la cadena por componentes')


def test_el_F01_conserva_sus_fechas_con_calendario(app):
    """El F01 ya las tenía · el cambio no puede habérselas llevado."""
    h = _html()
    for campo in ('f01_fecha_recepcion', 'f01_fecha_vencimiento'):
        assert ("_rcDate('%s'" % campo) in h, '%s perdió su calendario' % campo
