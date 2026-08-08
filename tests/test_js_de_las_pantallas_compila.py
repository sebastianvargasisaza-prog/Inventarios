# -*- coding: utf-8 -*-
"""Todo el JavaScript que sirve la app COMPILA · y la verificación no puede saltarse nada.

Sebastián, dos veces el mismo día: *"pero mirá lo que sale"* -- una barra roja al pie de la
pantalla. La segunda fue `Uncaught ReferenceError: switchProgTab is not defined`, con la pestaña
Programación en blanco: un error de sintaxis rompe el bundle ENTERO, así que las funciones que se
definen después nunca existen y la pantalla deja de responder.

La causa de las dos fue mía y la misma: **un escape dentro de un string REGULAR de Python lo
interpreta Python, no el JavaScript**. `\\u000a` escrito con una sola barra se convierte en un
salto de línea real y parte el `confirm` a la mitad.

⚠ Pero lo que hace falta escribir acá es el fallo de VERIFICACIÓN, que es peor que el bug:

  · yo node-checkeaba buscando bloques `<script>...</script>` dentro de cada constante grande;
  · `DASHBOARD_APP_JS` es JavaScript CRUDO, sin etiquetas: mi búsqueda encontraba **cero bloques**
    y lo daba por bueno. Un millón de caracteres de JS, el archivo que estaba editando, nunca se
    revisó;
  · `DASHBOARD_CORE_JS` es peor todavía: contiene el texto `<script` en alguna cadena pero no
    pares completos, así que también daba cero.

Es exactamente M65 otra vez ("el node-check era hueco: devolvía '' y un string vacío siempre
pasa"). Por eso este guard **enumera lo que TIENE que revisar y falla si alguno no se revisó**:
una verificación que puede saltarse su objeto en silencio no es una verificación.
"""
import io
import os
import re
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

# Lo que SÍ o SÍ tiene que quedar revisado. Si mañana se agrega otro bundle, se suma acá y el
# guard lo exige.
OBLIGATORIOS = (
    ('templates_py.dashboard_html', 'DASHBOARD_APP_JS'),
    ('templates_py.dashboard_html', 'DASHBOARD_CORE_JS'),
    ('templates_py.dashboard_html', 'DASHBOARD_HTML'),
    ('templates_py.calidad_html', 'CALIDAD_HTML'),
    ('templates_py.recepcion_html', 'RECEPCION_HTML'),
)


def _node_check(codigo, etiqueta):
    """Devuelve el error o None. Se escribe a archivo porque `node --check` no lee de stdin."""
    f = os.path.join(tempfile.gettempdir(), 'jscheck.js')
    io.open(f, 'w', encoding='utf-8').write(codigo)
    r = subprocess.run(['node', '--check', f], capture_output=True, text=True)
    return None if r.returncode == 0 else ('%s · %s' % (etiqueta, (r.stderr or '').strip()[:400]))


def _pedazos(nombre, valor):
    """Qué hay que compilar de esta constante.

    Si el nombre termina en `_JS` es JavaScript crudo y se compila ENTERO -- buscarle etiquetas
    `<script>` es justo el error que dejó pasar un bundle de un millón de caracteres.
    """
    if nombre.endswith('_JS'):
        return [(nombre, valor)]
    bloques = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', valor, re.S)
    return [('%s[script %d]' % (nombre, i), b) for i, b in enumerate(bloques)]


def test_todo_el_JS_de_las_pantallas_compila():
    errores, revisados = [], []
    for modulo, const in OBLIGATORIOS:
        try:
            m = __import__(modulo, fromlist=['x'])
        except Exception as e:
            errores.append('%s no importa: %s' % (modulo, e))
            continue
        v = getattr(m, const, None)
        if not isinstance(v, str) or len(v) < 100:
            errores.append('%s.%s no existe o está vacío · la verificación estaría mirando la nada'
                           % (modulo, const))
            continue
        pedazos = _pedazos(const, v)
        if not pedazos:
            errores.append('%s.%s no produjo NADA que compilar · el check se lo saltaría en '
                           'silencio, que es como se coló el bundle roto' % (modulo, const))
            continue
        for etiqueta, codigo in pedazos:
            revisados.append(etiqueta)
            err = _node_check(codigo, etiqueta)
            if err:
                errores.append(err)
    assert not errores, '\n'.join(errores)
    # Un error de sintaxis rompe el bundle ENTERO, así que si el bundle grande no se revisó, el
    # verde de este test no significa nada.
    assert any(x == 'DASHBOARD_APP_JS' for x in revisados), \
        'el bundle principal no se revisó · el verde de este test no prueba nada'
    assert len(revisados) >= 8, 'se revisaron muy pocos pedazos: %s' % revisados


def test_ningun_salto_de_linea_REAL_dentro_de_un_string_de_JS():
    """El error concreto que me pasó cuatro veces: un `\\n` o `\\uXXXX` escrito con UNA barra
    dentro de un string REGULAR de Python lo interpreta Python, y al JavaScript le llega un salto
    de línea de verdad que parte la cadena a la mitad.

    El node-check ya lo caza, pero este chequeo dice DÓNDE está y por qué, que es lo que hace la
    diferencia entre arreglarlo en un minuto o buscarlo en un millón de caracteres.
    """
    import templates_py.dashboard_html as D
    malas = []
    for const in ('DASHBOARD_APP_JS', 'DASHBOARD_CORE_JS'):
        v = getattr(D, const, '') or ''
        for n, linea in enumerate(v.split('\n'), 1):
            # una línea que abre comilla simple y no la cierra, dentro de alert/confirm/prompt
            if not re.search(r"\b(alert|confirm|prompt)\s*\(", linea):
                continue
            if linea.count("'") % 2 == 1:
                malas.append('%s:%d · %s' % (const, n, linea.strip()[:110]))
    assert not malas, (
        'estas cadenas quedaron abiertas (un escape se volvió salto de línea real · M65):\n  '
        + '\n  '.join(malas))
