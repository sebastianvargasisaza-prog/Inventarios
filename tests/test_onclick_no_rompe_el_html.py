# -*- coding: utf-8 -*-
"""Un valor con comillas dentro de un `onclick="..."` parte el HTML y mata la pantalla.

Sebastián, mandando la captura del modal de empaque: *"pero mirá lo que sale"* -- abajo, una barra
roja: **`Uncaught SyntaxError: Unexpected end of input`**.

Era mío. `JSON.stringify` devuelve el valor CON comillas dobles, y esas comillas, adentro de un
atributo delimitado por comillas dobles, lo CIERRAN antes de tiempo: el HTML queda partido, el
navegador intenta parsear la basura que sigue y la pantalla deja de responder.

⚠ Lo que hace a este bug peligroso es que **la verificación de siempre no lo ve**: `node --check`
de los bloques `<script>` pasa en verde, porque el JavaScript es sintácticamente válido. Lo que
está roto es el HTML que ese JavaScript ARMA al ejecutarse (M112/M146: verifiqué la sintaxis en
vez de la estructura).

Y el archivo ya tenía el patrón correcto en seis sitios (`.replace(/"/g,'&quot;')`). Mis tres
botones nuevos lo copiaron a medias, que es exactamente M45: un idiom copiado incompleto.
"""
import io
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

# Los archivos que ARMAN HTML dentro de JavaScript. Si mañana aparece otro, se agrega acá.
FUENTES = (
    'api/templates_py/dashboard_html.py',
    'api/templates_py/calidad_html.py',
    'api/templates_py/recepcion_html.py',
    'api/templates_py/centro_operaciones_html.py',
)


def _lineas_sospechosas(txt):
    """Una línea que mete `JSON.stringify` en un atributo y no escapa las comillas.

    Se busca por LÍNEA y no por el span del atributo: el contenido se arma concatenando, así que
    una expresión regular que corte en la primera comilla no ve nada -- me pasó al escribir este
    mismo guard y daba 0 con el bug puesto.
    """
    malas = []
    for n, ln in enumerate(txt.split('\n'), 1):
        if 'JSON.stringify' not in ln:
            continue
        if not re.search(r'on\w+\s*=\s*\\?"', ln):
            continue
        if 'replace(/"/g' in ln or '_q(' in ln:
            continue
        malas.append((n, ln.strip()[:130]))
    return malas


def test_ningun_onclick_mete_comillas_sin_escapar():
    malas = []
    for rel in FUENTES:
        p = os.path.join(RAIZ, rel)
        if not os.path.exists(p):
            continue
        for n, ln in _lineas_sospechosas(io.open(p, encoding='utf-8').read()):
            malas.append('%s:%d · %s' % (rel, n, ln))
    assert not malas, (
        'estas líneas parten el HTML que generan (el atributo se cierra en la comilla que mete '
        'JSON.stringify) · usá `_q(...)` o `.replace(/"/g,"&quot;")`:\n  ' + '\n  '.join(malas))


def test_el_helper_EXISTE_y_escapa():
    """`_q` es el punto único: si cada botón lo resuelve a su manera, el próximo se olvida."""
    src = io.open(os.path.join(RAIZ, 'api', 'templates_py', 'dashboard_html.py'),
                  encoding='utf-8').read()
    assert re.search(r'function\s+_q\s*\(', src), 'no existe el helper'
    i = src.find('function _q(')
    assert 'replace(/"/g' in src[i:i + 700], 'el helper no escapa las comillas'


def test_el_HTML_que_se_GENERA_queda_entero(app):
    """El guard que mide el hecho, no el texto: se ejecuta el generador con un valor que lleva una
    comilla y se comprueba que el atributo sigue completo.

    Es lo único que distingue este bug de un falso positivo, porque el JS es válido en los dos
    casos y `node --check` pasa igual.
    """
    import subprocess
    import tempfile
    import templates_py.dashboard_html as D

    js = D.DASHBOARD_APP_JS
    sig = re.compile('\n(?:async )?function ')

    def bloque(nombre):
        i = js.find('function ' + nombre)
        assert i > 0, nombre
        m = sig.search(js, i + 10)
        return js[i:m.start() if m else i + 9000]

    prog = bloque('empqEsc') + '\n' + bloque('_q') + """
var v = 'MEE"ENV-009';
var h = '<button onclick="empqAplicarFrasco('+_q(v)+',&quot;tapa&quot;)">x</button>';
var m = h.match(/onclick="([^"]*)"/);
console.log(m && m[1].indexOf('empqAplicarFrasco') === 0 && m[1].slice(-1) === ')' ? 'OK' : 'ROTO');
"""
    f = os.path.join(tempfile.gettempdir(), 'guard_onclick.js')
    io.open(f, 'w', encoding='utf-8').write(prog)
    r = subprocess.run(['node', f], capture_output=True, text=True)
    assert 'OK' in (r.stdout or ''), (
        'el atributo generado se parte con un valor que lleva comillas: %s %s'
        % (r.stdout.strip(), r.stderr.strip()[:200]))
