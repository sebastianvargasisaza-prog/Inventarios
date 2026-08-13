# -*- coding: utf-8 -*-
"""El bulto se reparte por las ventas de CADA TONO, no en partes iguales.

Sebastián (9-ago): *"resuelve eso de las filas por tono"*. Antes de crear una fila por tono hay
que arreglar el reparto, porque los ocho tonos del blush son todos de 6 ml y las tres funciones
que reparten pesaban por `(producto, VOLUMEN)` **antes** que por SKU: la suma por volumen devuelve
lo mismo para los ocho, así que el nivel por SKU no llegaba a correr nunca y **se pediría la misma
cantidad de cada etiqueta**, sin importar que el borgoña venda cinco veces más que el malva
(M58/M72 aplicados al caso tono).

La regla vive ahora en UNA función que usan las tres (M45: tres copias divergen).
"""


def _f():
    # ⚠ El import va ADENTRO y NO se toca `sys.path` a nivel de módulo: eso corre en la
    # COLECCIÓN, antes de que la fixture `app` prepare el entorno, y deja `config` cargado sin
    # las claves de prueba -- lo que rompe el LOGIN del archivo siguiente, con un rojo que no
    # habla de este archivo (M165). La fixture `app` ya pone `api/` en la ruta.
    from blueprints.programacion import _unidades_por_presentacion
    return _unidades_por_presentacion


def test_dos_tonos_del_mismo_volumen_pesan_por_SU_venta(app):
    f = _f()
    pres = [{'cod': 'A', 'sku': 'BB101', 'vol': 6, 'override': 0},
            {'cod': 'B', 'sku': 'BB201', 'vol': 6, 'override': 0}]
    uds = f(pres, {'BB101': 300, 'BB201': 30}, {6: 330})
    assert uds['A'] == 300 and uds['B'] == 30, \
        'los tonos se repartieron en partes iguales: %s' % uds


def test_si_FALTA_el_sku_de_uno_se_usa_el_agregado_como_antes(app):
    """Mezclar una venta por SKU con una suma por volumen es sumar peras y manzanas: la que no
    tiene SKU se llevaría el total del grupo y aplastaría a las demás. Con el grupo incompleto se
    usa el agregado, que es exactamente lo que se hacía antes -- sin SKUs cargados, nada cambia."""
    f = _f()
    pres = [{'cod': 'A', 'sku': 'BB101', 'vol': 6, 'override': 0},
            {'cod': 'B', 'sku': '', 'vol': 6, 'override': 0}]
    uds = f(pres, {'BB101': 300}, {6: 330})
    assert uds['A'] == uds['B'] == 330, 'mezcló venta por SKU con suma por volumen: %s' % uds


def test_el_override_manual_le_gana_a_todo(app):
    """Lo que una persona fijó a mano es una decisión, no una medición."""
    f = _f()
    pres = [{'cod': 'A', 'sku': 'BB101', 'vol': 6, 'override': 5},
            {'cod': 'B', 'sku': 'BB201', 'vol': 6, 'override': 1}]
    uds = f(pres, {'BB101': 300, 'BB201': 30}, {6: 330})
    assert uds == {'A': 5.0, 'B': 1.0}


def test_sin_ninguna_venta_reparte_uniforme(app):
    f = _f()
    pres = [{'cod': 'A', 'sku': 'BB101', 'vol': 6, 'override': 0},
            {'cod': 'B', 'sku': 'BB201', 'vol': 6, 'override': 0}]
    assert f(pres, {}, {}) == {'A': 1.0, 'B': 1.0}


def test_dos_TAMANOS_distintos_siguen_pesando_por_volumen(app):
    """El caso que ya funcionaba y no se puede romper (M72): con ventas iguales, el de 30 ml se
    lleva 3× el bulto del de 10 ml. Acá se comprueba que las unidades salen bien; el peso por
    volumen lo aplica el caller."""
    f = _f()
    pres = [{'cod': 'A', 'sku': 'S10', 'vol': 10, 'override': 0},
            {'cod': 'B', 'sku': 'S30', 'vol': 30, 'override': 0}]
    uds = f(pres, {'S10': 100, 'S30': 100}, {10: 100, 30: 100})
    assert uds['A'] == uds['B'] == 100


def test_el_reparto_del_LOTE_usa_la_misma_regla(app):
    """Las tres funciones que reparten tenían la prioridad copiada. Si una se queda atrás, dos
    pantallas dicen números distintos del mismo hecho (M45/M73)."""
    import io as _io
    import os
    import re
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'api', 'blueprints', 'programacion.py')
    src = _io.open(ruta, encoding='utf-8').read()
    codigo = '\n'.join(l.split('#')[0] for l in src.splitlines())
    # ⚠ Se cuenta la DEFINICION aparte: con `>= 3` el test pasaba con la definicion y solo DOS
    # llamadas, y la tercera funcion se habia quedado atras. Un guard que cuenta tiene que saber
    # que esta contando (M152).
    llamadas = len(re.findall(r'(?<!def )_unidades_por_presentacion\(', codigo))
    assert llamadas >= 3, ('las tres que reparten tienen que usar la MISMA regla '
                           '(llamadas=%d)' % llamadas)
