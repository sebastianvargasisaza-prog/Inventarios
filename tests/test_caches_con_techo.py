# -*- coding: utf-8 -*-
"""Un cache llaveado por lo que teclea el usuario tiene TECHO, o se come la RAM del worker.

Sebastián 7-ago: *"con criterio, siempre pensando en escalabilidad"*.

Un cache de módulo vive por WORKER y no se limpia nunca. Mientras la llave sea fija (el año, el
mes) da igual. El problema es cuando la llave viene del request -- una fecha, un `limit`, una
combinación de umbrales -- o cambia a diario: ahí crece sin techo, y con 1 GB de RAM y 3 workers
eso termina en un worker muerto por memoria, que desde afuera se ve como una caída sin causa.

Es el P2 que M89 dejó anotado en el cerebro y que llevaba meses abierto. Cuatro caches estaban
así, y el peor guarda cuatro mapas de TODOS los SKUs por entrada, con la fecha en la llave: una
entrada nueva por día, para siempre.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))


def test_el_helper_NO_pasa_del_techo():
    from http_helpers import cache_poner
    d = {}
    for i in range(500):
        cache_poner(d, 'k%d' % i, i, tope=10)
    assert len(d) <= 10, 'el cache creció más allá del techo: %d' % len(d)
    # y conserva lo MÁS RECIENTE, que es lo que se va a volver a pedir
    assert 'k499' in d, 'tiró justo lo último que se guardó'


def test_re_guardar_la_MISMA_clave_no_hace_crecer_nada():
    """El caso normal (el mismo usuario recargando la misma pantalla) no debe rotar el cache."""
    from http_helpers import cache_poner
    d = {}
    for _ in range(100):
        cache_poner(d, 'una', 1, tope=5)
    assert len(d) == 1


def test_si_el_cache_falla_NO_rompe_el_request():
    """Un cache es una optimización: si algo sale mal se sigue sin cachear, nunca se cae la
    pantalla (el mismo criterio que M4 al revés: acá el silencio SÍ es correcto)."""
    from http_helpers import cache_poner

    class Roto(dict):
        def __setitem__(self, k, v):
            raise RuntimeError('cache roto')

    assert cache_poner(Roto(), 'x', 42, tope=3) == 42


def test_los_CUATRO_caches_de_llave_libre_pasan_por_el_helper():
    """El barrido que impide que el próximo nazca sin techo (M45).

    Se enumeran los que se revisaron uno por uno. Los que quedan fuera es porque su llave es
    ACOTADA por construcción (el año, el mes, un blob único) y no pueden crecer.
    """
    import ast
    import io as _io
    revisados = [
        ('api/blueprints/marketing.py', '_ATRIB_CACHE'),      # llave: `desde` del request
        ('api/blueprints/plan.py', '_HUERFANOS_CACHE'),       # llave: `limit` del request
        ('api/blueprints/plan.py', '_ALERTAS_IA_CACHE'),      # llave: 4 umbrales del request
        ('api/blueprints/plan.py', '_VMAPS_CACHE'),           # llave: fechas → 1 entrada por día
    ]
    sin_techo = []
    for rel, nombre in revisados:
        src = _io.open(os.path.join(RAIZ, rel), encoding='utf-8').read()
        # cada ESCRITURA de ese cache tiene que ir por el helper, no por asignación directa
        import re as _re
        limpio = _re.sub(r'#[^\n]*', '', src)
        directas = _re.findall(nombre + r'\[[^\]]+\]\s*=', limpio)
        if directas:
            sin_techo.append('%s::%s (%d escrituras directas)' % (rel, nombre, len(directas)))
    assert not sin_techo, ('caches con llave libre que siguen creciendo sin techo: %s' % sin_techo)
