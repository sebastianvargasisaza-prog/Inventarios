# -*- coding: utf-8 -*-
"""El modal de control de calidad funciona en las DOS pantallas donde se inyecta.

`CC_REVIEW_JS` se inyecta en `/calidad` y en la pantalla de Planta, y usa `_fetchOpts`. Sólo
`/calidad` la definía, así que **el mismo modal funcionaba en una y en la otra el botón no hacía
absolutamente nada**: `_fetchOpts is not defined` revienta la función entera. Y ninguna de las
verificaciones habituales lo ve -- el `node --check` pasa (la sintaxis es válida) y el balance de
`<div>` da cero: una función que no existe es sintaxis perfectamente correcta hasta que corre
(M146). El síntoma es un botón muerto.

Lo que se rompía no era cosmético: ese modal registra el control de calidad de un lote recibido
y, en el mismo flujo, la FIRMA ELECTRÓNICA (Part 11).

La regla que queda fijada: **un bloque compartido trae su propia dependencia**, no confía en
quien lo hospeda -- si no, agregarlo a una pantalla nueva lo vuelve a romper en silencio (M158).
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))
sys.path.insert(0, os.path.join(RAIZ, 'scripts'))


def test_el_bloque_compartido_TRAE_su_propia_dependencia(app):
    from templates_py.cc_review_html import CC_REVIEW_JS
    assert '_fetchOpts' in CC_REVIEW_JS, 'el modal dejó de usarla · revisá este test'
    assert re.search(r'window\._fetchOpts\s*=\s*window\._fetchOpts\s*\|\|', CC_REVIEW_JS), (
        'el bloque volvió a depender de que el anfitrión defina `_fetchOpts` · en la pantalla '
        'que no la define, el botón no hace nada y no hay error visible')


def test_es_SINCRONA_como_la_del_anfitrion(app):
    """Las llamadas son `fetch(url, _fetchOpts('POST', body))` SIN `await`. Una versión async
    devolvería una PROMESA, `fetch` la ignoraría como opciones y mandaría un GET sin cuerpo ni
    token CSRF: arreglado en apariencia y roto de una forma mucho más difícil de ver."""
    from templates_py.cc_review_html import CC_REVIEW_JS
    i = CC_REVIEW_JS.find('window._fetchOpts')
    assert i > 0
    firma = CC_REVIEW_JS[i:i + 120]
    assert 'async' not in firma, (
        'se volvió asíncrona · las 4 llamadas no la esperan, así que fetch recibiría una promesa')
    # y las llamadas siguen sin await, que es el contrato que hay que respetar
    assert 'await _fetchOpts(' not in CC_REVIEW_JS


def test_manda_el_token_CSRF(app):
    """Sin el header, el backend responde "CSRF token requerido" y el botón parece roto por
    otra razón (M15)."""
    from templates_py.cc_review_html import CC_REVIEW_JS
    i = CC_REVIEW_JS.find('window._fetchOpts')
    bloque = CC_REVIEW_JS[i:i + 700]
    assert 'X-CSRF-Token' in bloque, 'no manda el token · los endpoints sensibles lo exigen'
    assert 'csrf-token' in CC_REVIEW_JS, 'no hay de dónde sacar el token'


def test_en_la_pantalla_de_PLANTA_no_queda_ninguna_funcion_sin_definir(app):
    """La verificación que de verdad mide: sobre el HTML RENDERIZADO de la pantalla, incluyendo
    el JS externo que carga. Es la única forma de ver una dependencia que falta (M65/M158)."""
    from check_js_animus import funciones_sin_definir
    import templates_py.dashboard_html as D
    extra = ''
    for nom in dir(D):
        v = getattr(D, nom)
        if nom.endswith('_JS') and isinstance(v, str):
            extra += '<script>' + v + '</script>'
    # Globales del navegador y artefactos que el escáner por texto no puede distinguir.
    RUIDO = {'Chart', 'URLSearchParams', 'atob', 'btoa', 'escape', 'unescape', 'gradient',
             'if', 'var', 'loadCuarentena', 'recDescontinuar', 'recReactivar'}
    faltan = [f for f in funciones_sin_definir(D.DASHBOARD_HTML + extra) if f not in RUIDO]
    assert not faltan, (
        'la pantalla de Planta llama funciones que no existen: %s · el botón que las use no '
        'va a hacer nada, sin error visible' % faltan)


def test_el_JS_del_modal_PARSEA(app):
    import io as _io
    import subprocess
    import tempfile
    from templates_py.cc_review_html import CC_REVIEW_JS
    try:
        subprocess.run(['node', '--version'], capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):  # pragma: no cover
        import pytest
        pytest.skip('node no disponible · el chequeo NO corrió (M100)')
    f = os.path.join(tempfile.gettempdir(), '_ccr_test.js')
    _io.open(f, 'w', encoding='utf-8').write(CC_REVIEW_JS)
    r = subprocess.run(['node', '--check', f], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr[:600]
