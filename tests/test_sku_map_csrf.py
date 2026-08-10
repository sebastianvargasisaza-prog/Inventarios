# -*- coding: utf-8 -*-
"""Un boton de admin que no manda el token CSRF no hace NADA.

Sebastian (9-ago), intentando mapear los SKU del lip serum: *"Error: CSRF token requerido para
endpoint admin/sensible"*. La pantalla existia y no se podia usar, que desde la silla del usuario
es lo mismo que no tenerla (M15/M121).

Al buscar el patron aparecieron **catorce** botones con el mismo defecto. Se arreglo el que
bloqueaba el trabajo y el resto queda ENUMERADO acá: la lista no puede crecer, y cada vez que se
arregla uno se saca de la lista. Enumerar lo que falta es lo contrario de esconderlo -- una lista
que se puede mirar entera es la unica forma de que se termine (M122).
"""
import io
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

# Los que TODAVIA no mandan el token. Cada uno es un boton que hoy no hace nada.
# ⚠ Esta lista solo puede ACHICARSE. Si aparece uno nuevo, el test falla.
PENDIENTES = {
    '/api/admin/aplicar-correcciones-formulas-batch-2026-04-28',
    '/api/admin/aplicar-minimos',
    '/api/admin/aplicar-stock-minimos-sugeridos',
    '/api/admin/archivar-mps-sin-uso-bulk',
    '/api/admin/corregir-formulas',
    '/api/admin/corregir-unidad-base-bulk',
    '/api/admin/eliminar-formulas-obsoletas',
    '/api/admin/formula-remapear-material-id',
    '/api/admin/maestro-mps-unificar',
    '/api/admin/marcar-lotes-vencidos',
    '/api/admin/mps-asignar-proveedor',
    '/api/admin/revertir-formulas-desde-backup',
    '/api/admin/sku-producto-map',
    '/api/admin/test-email',
}


def _sin_token():
    src = io.open(os.path.join(RAIZ, 'api', 'blueprints', 'admin.py'), encoding='utf-8').read()
    falta = set()
    for m in re.finditer(
            r"fetch\(\s*'(/api/admin/[^']+)'[^)]{0,400}?method\s*:\s*'(POST|PUT|DELETE|PATCH)'",
            src, re.S):
        ventana = src[max(0, m.start() - 500):m.end() + 500]
        if 'X-CSRF-Token' not in ventana:
            falta.add(m.group(1))
    return falta


def test_el_guardar_de_sku_map_manda_el_token(app):
    """El que bloqueaba el trabajo."""
    src = io.open(os.path.join(RAIZ, 'api', 'blueprints', 'admin.py'), encoding='utf-8').read()
    i = src.find('async function guardar(i, sku, productoAnterior)')
    assert i > 0, 'no encuentro el guardar de sku-map'
    cuerpo = src[i:i + 1600]
    assert 'X-CSRF-Token' in cuerpo, \
        'el POST de sku-map no manda el token: el guard lo rechaza y la pantalla queda inutil'
    assert '/api/csrf-token' in cuerpo, 'no pide el token antes de mandarlo'


def test_la_lista_de_pendientes_NO_crece(app):
    """Un defecto conocido y contado se termina; uno suelto se repite."""
    nuevos = _sin_token() - PENDIENTES
    assert not nuevos, ('botones de admin NUEVOS sin token CSRF (no van a hacer nada): %s'
                        % sorted(nuevos))


def test_lo_que_se_arregla_se_SACA_de_la_lista(app):
    """Si un pendiente ya manda el token, tiene que salir de la lista: una lista que se queda con
    cosas resueltas deja de creerse y nadie vuelve a mirarla (M122)."""
    resueltos = PENDIENTES - _sin_token()
    assert not resueltos, ('ya mandan el token y siguen en PENDIENTES · sacalos de la lista: %s'
                           % sorted(resueltos))
