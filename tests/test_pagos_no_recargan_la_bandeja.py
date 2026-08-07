# -*- coding: utf-8 -*-
"""Pagar o rechazar un creador no recarga toda la bandeja (Sebastián, 6-ago).

*"cuando le doy pagar o rechazar se vuelve a cargar, eso no me gusta"*.

Los dos handlers hacían `_PG_DATA=null` + `cargarPagos()`: otra ida a la red, el spinner
"Cargando pagos...", y la lista re-armada entera -- se pierde el scroll y las tarjetas que tenía
abiertas. Con 25 creadores eso es una espera por cada pago.

Lo que se paga o se rechaza **desaparece** de la bandeja: no hace falta preguntarle al servidor
cómo quedó, ya se sabe. Sale del arreglo en memoria y se vuelve a pintar sin red.

⚠ Los KPI se **recalculan desde lo que queda**. Dejarlos como estaban sería peor que la espera:
el "Total por pagar" seguiría contando plata ya pagada, y ese es el número con el que se decide
(M5). Y si el pago no estaba en la lista cargada, se recarga -- nunca dejar la pantalla mostrando
algo que ya no existe.
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))
sys.path.insert(0, os.path.join(RAIZ, 'scripts'))


def _html():
    import templates_py.centro_operaciones_html as C
    return ''.join(v for k, v in vars(C).items()
                   if isinstance(v, str) and len(v) > 400 and '<script' in v)


def _bloque(h, nombre):
    i = h.find('async function %s(' % nombre)
    assert i > 0, 'no encuentro %s' % nombre
    j = h.find('\nasync function ', i + 10)
    k = h.find('\nfunction ', i + 10)
    fin = min(x for x in (j, k, len(h)) if x > 0)
    return h[i:fin]


def test_pagar_NO_vuelve_a_pedir_la_lista(app):
    from check_js_animus import _sin_ruido
    b = _sin_ruido(_bloque(_html(), 'pagarDesdeBandeja'))
    assert '_pgSacarDeLaBandeja' in b, 'sigue recargando en vez de sacar la tarjeta'
    # La recarga sólo puede quedar como RESPALDO, detrás del `if(!...)`. Se mide por posición
    # y no con una regex de llaves: hay un `={}` en el medio que la rompía (y el rojo era del
    # test, no del código).
    i_guard = b.find('if(!_pgSacarDeLaBandeja')
    i_carga = b.find('cargarPagos(')
    assert i_guard > 0, 'la recarga dejó de estar condicionada'
    assert i_carga > i_guard, 'recarga ANTES de intentar sacar la tarjeta · recarga siempre'


def test_rechazar_NO_vuelve_a_pedir_la_lista(app):
    from check_js_animus import _sin_ruido
    b = _sin_ruido(_bloque(_html(), 'rechazarDesdeBandeja'))
    assert '_pgSacarDeLaBandeja' in b, 'sigue recargando en vez de sacar la tarjeta'
    i_guard = b.find('if(!_pgSacarDeLaBandeja')
    i_carga = b.find('cargarPagos(')
    assert i_guard > 0 and i_carga > i_guard, 'la recarga dejó de ser el respaldo'


def test_los_KPI_se_RECALCULAN_con_lo_que_queda(app):
    """Si el total siguiera contando lo ya pagado, la pantalla mentiría en el número con el que
    se autorizan los pagos -- peor que la espera que esto viene a quitar (M5)."""
    h = _html()
    i = h.find('function _pgSacarDeLaBandeja')
    assert i > 0, 'no existe el helper'
    b = h[i:i + 1400]
    assert 'res.total' in b and 'reduce(' in b, 'no recalcula el total'
    assert 'res.n' in b, 'no recalcula la cantidad de creadores'
    assert 'con_alerta' in b, 'no recalcula los que hay que revisar'
    assert 'pintarPagos()' in b, 'no vuelve a pintar'


def test_si_NO_estaba_en_la_lista_recarga(app):
    """El borde: sin ese respaldo, un pago hecho desde otra pestaña dejaría la bandeja mostrando
    una tarjeta que ya no existe."""
    h = _html()
    i = h.find('function _pgSacarDeLaBandeja')
    b = h[i:i + 1400]
    assert 'return false' in b, 'no avisa cuando no encontró el pago'
    assert 'return true' in b, 'no distingue el caso resuelto'


def test_el_JS_de_la_pantalla_PARSEA(app):
    import io as _io
    import subprocess
    import tempfile
    try:
        subprocess.run(['node', '--version'], capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):  # pragma: no cover
        import pytest
        pytest.skip('node no disponible · el chequeo NO corrió (M100)')
    for n, b in enumerate(re.findall(r'<script[^>]*>(.*?)</script>', _html(), re.S)):
        f = os.path.join(tempfile.gettempdir(), '_pg_%d.js' % n)
        _io.open(f, 'w', encoding='utf-8').write(b)
        r = subprocess.run(['node', '--check', f], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, 'bloque %d roto:\n%s' % (n, r.stderr[:400])


# ── Creadores SIN correo: el comprobante no les llega ────────────────────────────────────

def test_se_ve_CUANTOS_creadores_no_tienen_correo(app):
    """Sebastián (6-ago): *"los correos tienen que llegar a los creadores"*. Hoy no llegan: el
    comprobante se genera y no tiene a dónde ir porque el creador no tiene `email` guardado.

    Eso no lo arregla código -- alguien tiene que cargarlos -- pero hasta ahora se descubría
    PAGO POR PAGO: el aviso saltaba recién al apretar Pagar. El número al frente convierte
    "hay un problema" en "estos cuatro, cargales el correo" (M121: lo que no se puede ver, no
    se puede actuar)."""
    h = _html()
    assert 'Sin correo' in h, 'no se ve cuántos no tienen correo'
    assert '_sinMail' in h, 'no se cuenta'
    assert 'pgFiltrarSinCorreo' in h and 'function pgFiltrarSinCorreo' in h, (
        'el contador no lleva a la lista · obligaría a buscarlos a mano')


def test_el_filtro_se_puede_APAGAR(app):
    """Si sólo prendiera, quedarías viendo cuatro de veinticinco sin entender por qué (M112)."""
    h = _html()
    i = h.find('function pgFiltrarSinCorreo')
    b = h[i:i + 400]
    assert '!window._PG_SOLO_SIN_CORREO' in b, 'el filtro no alterna'


def test_cuando_NO_falta_ninguno_lo_dice(app):
    """Un cero pelado se lee como "no se calculó". Decir "a todos les llega" es la diferencia
    entre un dato y un hueco (M154)."""
    h = _html()
    assert 'a todos les llega el comprobante' in h, 'el caso sano no dice nada'
