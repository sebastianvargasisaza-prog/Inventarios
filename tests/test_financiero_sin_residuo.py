# -*- coding: utf-8 -*-
"""Financiero: nada llama a lo que no existe, y se retiró el residuo de las secciones podadas.

Dos botones muertos, uno de ellos **en el arranque de la página**:

- `cargarOCsPendientes()` se llamaba dentro de `loadConfig().then(...)` y no existe en ninguna
  parte. Adentro de un `.then()` sin `.catch`, un ReferenceError es una promesa rechazada en
  SILENCIO: ni error en pantalla ni nada que reportar. No hay ninguna sección de OCs pendientes
  en esta pantalla -- quedó viva la llamada de algo que se podó (M112).
- `loadKPIs()` se llamaba para refrescar tras "limpiar todo"; el refrescador real de esta
  pantalla es `loadDashboard`.

Y el residuo: 16 funciones que nadie llamaba y que tocaban **31 ids del DOM, ninguno existente**.
Se retiraron hasta punto fijo, porque borrar una muerta mata a las que sólo ella llamaba: las 8
primeras destaparon otras 8 (M145).

⚠ El criterio de poda importa tanto como la poda. Contar menciones da falsos positivos con los
`onclick` que el JS arma dentro de cadenas -- la primera medición decía 22 muertas y eran 8
(M155). Lo que decide es: cero llamadas en TODO el archivo **y** que los ids que toca no existan.
"""
import io
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))
sys.path.insert(0, os.path.join(RAIZ, 'scripts'))

RUIDO = {'Chart', 'URLSearchParams', 'atob', 'btoa', 'escape', 'unescape', 'gradient',
         'if', 'var', 'FormData', 'Intl'}


def _html():
    import templates_py.financiero_html as F
    return ''.join(v for k, v in vars(F).items()
                   if isinstance(v, str) and len(v) > 400 and '<script' in v)


def test_ninguna_funcion_llamada_falta(app):
    from check_js_animus import funciones_sin_definir
    faltan = [f for f in funciones_sin_definir(_html()) if f not in RUIDO]
    assert not faltan, (
        'Financiero llama funciones que no existen: %s · el botón que las use no hace nada, '
        'y si corre en el arranque el fallo es una promesa rechazada en silencio' % faltan)


def test_el_arranque_no_llama_a_una_seccion_podada(app):
    # ⚠ Sin quitar los comentarios, este test encuentra MI PROPIO comentario explicando por qué
    # se retiró la llamada, y falla con el código correcto. Es la tercera vez en el día (M154).
    from check_js_animus import _sin_ruido
    h = _sin_ruido(_html())
    assert 'cargarOCsPendientes' not in h, (
        'volvió la llamada a la sección de OCs pendientes, que no existe en esta pantalla')
    assert 'loadKPIs(' not in h, 'volvió `loadKPIs`, que no está definida acá'
    assert 'loadConfig().then' in h, 'se perdió el arranque de la pantalla'


def test_no_quedan_getElementById_apuntando_a_nada(app):
    """El par disparador↔destino: 31 ids apuntaban a elementos borrados. Eso además vuelve
    ruido permanente cualquier guard de "ningún botón apunta a algo que no existe" (M112)."""
    from check_js_animus import _sin_ruido
    h = _html()
    js = _sin_ruido('\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', h, re.S)))
    sin_js = re.sub(r'<script[^>]*>.*?</script>', '', h, flags=re.S)
    ids = set(re.findall(r'id="([^"]+)"', sin_js))
    creados = set(re.findall(r"\.id\s*=\s*'([^']+)'", js))
    usados = set(re.findall(r"getElementById\(\s*'([^']+)'", js))
    huerfanos = sorted(u for u in usados if u not in ids and u not in creados)
    assert not huerfanos, 'el JS busca ids que no existen: %s' % huerfanos


def test_el_residuo_NO_volvio(app):
    """Si alguien re-agrega una de estas, tiene que venir con su sección; sueltas son 25 KB que
    nadie puede ejecutar y que ensucian cualquier medición futura."""
    h = _html()
    for n in ('buscarTrazabilidadMP', 'guardarConteo', 'iniciarConteo', 'enviarRevisionCC',
              'cargarItemsConteo', 'abrirCCModal'):
        assert ('function %s(' % n) not in h, 'volvió el residuo: %s' % n


def test_la_pantalla_CARGA(app, admin_client):
    """Una poda se verifica MIRANDO la pantalla, no el diff: borrar un bloque no rompe la
    sintaxis, así que el node-check pasa con la página partida (M112)."""
    r = admin_client.get('/financiero')
    assert r.status_code == 200, r.data[:300]
    cuerpo = r.data.decode('utf-8', 'replace')
    assert 'loadDashboard' in cuerpo, 'la pantalla se sirvió sin su JS'
    assert cuerpo.count('<div') == cuerpo.count('</div>'), (
        'quedaron divs sin cerrar · la pantalla se parte sin dar ningún error')


def test_el_JS_PARSEA(app):
    import subprocess
    import tempfile
    try:
        subprocess.run(['node', '--version'], capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):  # pragma: no cover
        import pytest
        pytest.skip('node no disponible · el chequeo NO corrió (M100)')
    bloques = re.findall(r'<script[^>]*>(.*?)</script>', _html(), re.S)
    assert bloques
    for n, b in enumerate(bloques):
        f = os.path.join(tempfile.gettempdir(), '_fin_%d.js' % n)
        io.open(f, 'w', encoding='utf-8').write(b)
        r = subprocess.run(['node', '--check', f], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, 'bloque %d roto:\n%s' % (n, r.stderr[:500])
