# -*- coding: utf-8 -*-
"""Al cerrar una recepción, decir QUÉ FILAS van sin lote y pedir confirmación.

Sebastián eligió "avisar y confirmar" (7-ago), sobre las otras dos opciones (dejarlo como estaba
o volverlo obligatorio).

El lote sigue **opcional a propósito**: se quitó de obligatorio el 27-jul porque trababa la
recepción administrativa -- quien cuenta bultos no siempre puede leer el lote del envase, eso lo
hace Calidad en el F01. Pero dejarlo vacío **por descuido** es exactamente lo que hizo que
después Calidad viera `OC-OC-2026-0314-1` y pareciera un bug del sistema.

Tres decisiones que hacen que el aviso sirva en vez de estorbar:

1. **Dice CUÁLES son**, no cuántas. "Faltan 3" obliga a buscarlas a mano, y entonces se le da
   Aceptar sin mirar.
2. **Deja seguir.** Un guard que traba un caso legítimo (el remito no trae el lote) se termina
   esquivando, y ahí se pierde también para los casos que sí importan (M39).
3. **Sólo cuenta las filas que de verdad se reciben** (`cant > 0`): una línea en cero no entra
   al kardex, así que avisar por ella sería ruido -- y una alerta que suena de más deja de
   mirarse justo el día que importa (M129).
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))
sys.path.insert(0, os.path.join(RAIZ, 'scripts'))


def _html():
    from templates_py.recepcion_html import RECEPCION_HTML
    return RECEPCION_HTML


def _js_limpio():
    from check_js_animus import _sin_ruido
    h = _html()
    return _sin_ruido('\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', h, re.S)))


def test_avisa_ANTES_de_mandar_la_recepcion(app):
    """Después de cerrar ya no se puede corregir: el aviso va donde todavía sirve."""
    js = _js_limpio()
    i = js.find('_sinLote.length')
    j = js.find('var payload = {')
    assert i > 0, 'no hay aviso de filas sin lote'
    assert j > i, 'el aviso quedó DESPUÉS de armar el envío · no llegaría a tiempo'


def test_dice_CUALES_son_no_cuantas(app):
    """"Faltan 3" obliga a buscarlas a mano, y entonces se le da Aceptar sin mirar."""
    js = _js_limpio()
    i = js.find('_sinLote.push')
    bloque = js[max(0, i - 200):i + 200]
    assert 'descripcion_full' in bloque or 'nombre_mp' in bloque, (
        'guarda un contador en vez del nombre del material')
    assert '_lista' in js, 'no arma la lista de nombres para mostrar'


def test_DEJA_seguir(app):
    """El lote es opcional a propósito · un guard que traba un caso legítimo se esquiva, y se
    pierde también para los casos que sí importan (M39)."""
    js = _js_limpio()
    i = js.find('_sinLote.length')
    bloque = js[i:i + 900]
    assert 'confirm(' in bloque, 'no pregunta · o bloquea o pasa de largo'
    assert 'return' in bloque, 'no respeta el Cancelar'
    # y NO puede haber vuelto a ser obligatorio en el backend
    import io
    src = io.open(os.path.join(RAIZ, 'api', 'blueprints', 'compras.py'), encoding='utf-8').read()
    assert 'sin_lote_proveedor' in src, 'desapareció el aviso del backend'
    i2 = src.find('sin_lote_proveedor` SALIÓ de las bloqueantes')
    assert i2 > 0, (
        'el lote volvió a ser bloqueante · eso traba la recepción administrativa, que es el '
        'motivo por el que se quitó el 27-jul')


def test_NO_avisa_por_lineas_que_no_se_reciben(app):
    """Una línea en cero no entra al kardex. Avisar por ella es ruido, y una alerta que suena de
    más deja de mirarse justo el día que importa (M129)."""
    js = _js_limpio()
    i = js.find('_sinLote.push')
    bloque = js[max(0, i - 260):i]
    assert 'cant > 0' in bloque, 'avisaría por filas que ni siquiera se están recibiendo'


def test_explica_QUE_pasa_si_sigue(app):
    """Un aviso que sólo dice "falta" sin decir la consecuencia se lee como un error del
    sistema · acá la consecuencia es concreta y no es grave (M124)."""
    h = _html()
    assert 'provisional' in h, 'no dice qué le pasa al material sin lote'
    assert 'F01' in h, 'no dice quién carga el lote real después'


def test_el_JS_de_recepcion_PARSEA(app):
    import io as _io
    import subprocess
    import tempfile
    try:
        subprocess.run(['node', '--version'], capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):  # pragma: no cover
        import pytest
        pytest.skip('node no disponible · el chequeo NO corrió (M100)')
    for n, b in enumerate(re.findall(r'<script[^>]*>(.*?)</script>', _html(), re.S)):
        f = os.path.join(tempfile.gettempdir(), '_rec_%d.js' % n)
        _io.open(f, 'w', encoding='utf-8').write(b)
        r = subprocess.run(['node', '--check', f], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, 'bloque %d roto:\n%s' % (n, r.stderr[:400])
