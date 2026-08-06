# -*- coding: utf-8 -*-
"""Ningún botón llama a una función que no existe.

Barrido de las 30+ pantallas con el escáner del proyecto. De 35 candidatos, 33 eran ruido
(globales del navegador, prosa dentro de comentarios, funciones protegidas con `typeof` o
`if(window.X)`) y **2 eran reales**. Ese reparto es la lección de método: un detector que grita
de más deja de mirarse (M122), así que lo que entra al gate es la lista VERIFICADA, no la cruda.

1. **Compras · dar de baja un proveedor.** Llamaba a `renderProveedores()`, que no existe -- la
   real es `renderProv`. Y el `try/catch` lo hacía peor: la baja SÍ se aplicaba en el servidor,
   pero la pantalla decía *"Error: renderProveedores is not defined"*, no refrescaba la lista y
   se veía como que había fallado. El usuario reintenta sobre algo que ya pasó.

2. **Calidad · paginar y buscar en las tablas.** `_PAG_REFRESH` despacha `cambiarPag`,
   `cambiarPagSize` y `buscarTabla`, y apuntaba a `loadCalibraciones`, que no existe (la real es
   `loadCal`). Como cada entrada iba protegida con `if(window.X)`, no había error: **buscar o
   pasar de página en la bitácora de calibración simplemente no hacía nada**. Una guarda que
   convierte un error en silencio es peor que el error, porque nadie lo reporta nunca.
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))
sys.path.insert(0, os.path.join(RAIZ, 'scripts'))


def _fuente(mod):
    import io
    return io.open(os.path.join(RAIZ, 'api', 'templates_py', mod), encoding='utf-8').read()


def test_dar_de_baja_un_proveedor_refresca_la_lista(app):
    s = _fuente('compras_html.py')
    assert 'renderProveedores()' not in s, (
        'volvió `renderProveedores`, que no existe · la baja se aplica y la pantalla dice que '
        'falló')
    i = s.find('function confirmarBajaProv360')
    j = s.find('\nfunction ', i + 10)
    bloque = s[i:j]
    assert 'renderProv()' in bloque, 'ya no refresca la lista tras dar de baja'


def test_la_paginacion_de_calidad_apunta_a_funciones_que_EXISTEN(app):
    """Cada entrada del mapa contra las funciones realmente definidas en la pantalla."""
    s = _fuente('calidad_html.py')
    i = s.find('_PAG_REFRESH = {')
    j = s.find('};', i)
    assert i > 0 and j > i, 'no encuentro el mapa de paginación'
    mapa = s[i:j]
    definidas = set(re.findall(r'function\s+(\w+)\s*\(', s))
    definidas |= set(re.findall(r'window\.(\w+)\s*=', s))
    apuntadas = re.findall(r"_pagRefrescar\('(\w+)',\s*'(\w+)'\)", mapa)
    assert len(apuntadas) >= 10, 'el mapa se achicó · revisá este test (%d)' % len(apuntadas)
    # Las tablas que HOY tienen controles en la pantalla no pueden apuntar a algo inexistente:
    # ahí el silencio es una función que el usuario cree que anda.
    alcanzables = {k for k in re.findall(
        r"(?:cambiarPag|cambiarPagSize|buscarTabla)\(\s*'(\w+)'", s)}
    assert alcanzables, 'nadie pagina · revisá este test'
    rotas = [(k, fn) for k, fn in apuntadas if k in alcanzables and fn not in definidas]
    assert not rotas, (
        'estas tablas paginan/buscan contra una función que no existe, y como va protegida NO '
        'da error: la acción simplemente no hace nada · %s' % rotas)


def test_el_despacho_DECLARA_lo_que_no_puede_hacer(app):
    """Para las tablas sin loader, el no-op mudo se cambió por un aviso: el día que una reciba
    controles de paginación, el hueco se ve en vez de esconderse (M100/M124)."""
    s = _fuente('calidad_html.py')
    i = s.find('function _pagRefrescar')
    assert i > 0, 'desapareció el despacho central'
    bloque = s[i:i + 500]
    assert 'console.warn' in bloque, 'volvió el no-op silencioso'
    assert "typeof f === 'function'" in bloque, 'ya no verifica que el loader exista'


def test_el_JS_de_las_dos_pantallas_PARSEA(app):
    """Reordenar un bloque grande rompe la sintaxis con facilidad, y un `<script>` roto deja la
    pantalla ENTERA sin cargar -- no sólo la función tocada (M65)."""
    import io as _io
    import subprocess
    import tempfile
    try:
        subprocess.run(['node', '--version'], capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):  # pragma: no cover
        import pytest
        pytest.skip('node no disponible · el chequeo NO corrió (M100)')
    for mod in ('templates_py.calidad_html', 'templates_py.compras_html'):
        m = __import__(mod, fromlist=['*'])
        html = ''.join(v for k, v in vars(m).items()
                       if isinstance(v, str) and len(v) > 400 and '<script' in v)
        bloques = re.findall(r'<script[^>]*>(.*?)</script>', html, re.S)
        assert bloques, '%s no tiene JS' % mod
        for n, b in enumerate(bloques):
            f = os.path.join(tempfile.gettempdir(), '_bt_%d.js' % n)
            _io.open(f, 'w', encoding='utf-8').write(b)
            r = subprocess.run(['node', '--check', f], capture_output=True, text=True, timeout=60)
            assert r.returncode == 0, '%s bloque %d roto:\n%s' % (mod, n, r.stderr[:500])
