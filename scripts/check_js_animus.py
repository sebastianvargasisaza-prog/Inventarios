# -*- coding: utf-8 -*-
"""Verifica que toda funcion LLAMADA en /animus este DEFINIDA.

Esto es lo que faltaba el 4-ago: llame a `hoyCol()` en dos modales y esa funcion nunca existio.
Yo "verifique" buscando el nombre en la pagina -- y encontre MI PROPIA LLAMADA, no la
definicion. El `node --check` pasa (la sintaxis es valida) y el balance de divs da cero: ninguno
de los dos ve una funcion que no existe. El sintoma fue un boton que no hace nada.

⚠ La limpieza de comentarios y strings se hace con un escaner CARACTER POR CARACTER, no con
regex: una comilla dentro de un literal de expresion regular (`/[^']/`) desincroniza al regex y
se come el resto del archivo -- con lo cual el chequeo reporta como "no definidas" decenas de
funciones que si existen, se vuelve ruido, y deja de mirarse. Que es exactamente lo que le pasa
a un guard que no se puede creer.

Corre solo (`python scripts/check_js_animus.py`) o desde el test del gate.
"""
import ast
import io
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Lo que provee el navegador o el resto de la pagina, y no se define en este archivo.
GLOBALES = set("""
if for while switch catch function return typeof await new delete void in of else do try finally
throw class extends super this yield instanceof case default break continue
fetch parseFloat parseInt isNaN isFinite encodeURIComponent decodeURIComponent
Number String Boolean Array Object JSON Math Date Promise RegExp Error Map Set Symbol
setTimeout setInterval clearTimeout clearInterval requestAnimationFrame
alert confirm prompt console document window localStorage sessionStorage navigator location
FormData Blob File FileReader URL Image Audio Notification AbortController Headers Request
Response WebSocket IntersectionObserver MutationObserver ResizeObserver CustomEvent Event
""".split())


def html_animus():
    """El HTML **final** de /animus, no el literal del fuente.

    ⚠ Antes leía la constante cruda del AST, y eso vuelve al guard incapaz de ver cualquier
    bloque que se INYECTE después de declarar el string (`ANIMUS_HTML.replace(...)` al final del
    módulo). El 5-ago dio un rojo falso por eso: la página llama a `cajaComoPagar` y su
    definición entra por inyección, así que el guard veía la llamada y no la función.

    Leer el valor final es además lo correcto por principio (M65): lo que hay que verificar es
    lo que el navegador recibe, no lo que está escrito. El AST queda de respaldo por si el
    módulo no se puede importar — con aviso, porque en ese modo el guard mira menos.
    """
    try:
        import sys
        api = os.path.join(RAIZ, 'api')
        if api not in sys.path:
            sys.path.insert(0, api)
        from templates_py.animus_html import ANIMUS_HTML
        return ANIMUS_HTML
    except Exception as e:
        print('[check_js_animus] AVISO: no pude importar animus_html (%s) · caigo al fuente '
              'crudo, asi que NO veo lo que se inyecta despues.' % e)
    src = io.open(os.path.join(RAIZ, 'api', 'templates_py', 'animus_html.py'),
                  encoding='utf-8').read()
    for n in ast.walk(ast.parse(src)):
        if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str) and len(n.value.value) > 5000):
            return n.value.value
    raise AssertionError('no encontre el HTML de /animus')


def _sin_ruido(js):
    """Reemplaza comentarios y literales por espacios, recorriendo el texto.

    Un regex no sirve: se desincroniza con la primera comilla que viva dentro de otro literal.
    """
    out = []
    i, n = 0, len(js)
    # Un `/` puede abrir una expresion regular. Y una regex puede llevar una COMILLA adentro
    # (`.replace(/'/g, ...)`): si no se saltea como unidad, el escaner la toma como inicio de
    # string y se come todo el archivo desde ahi -- fue lo que dejo el chequeo en 24k de 125k.
    ANTES_DE_REGEX = set('(,=:[!&|?{};\n+*%<>~^')
    while i < n:
        c = js[i]
        dos = js[i:i + 2]
        if c == '/' and dos not in ('//', '/*'):
            prev = ''.join(out).rstrip()[-1:] if out else ''
            if prev == '' or prev in ANTES_DE_REGEX:
                j = i + 1
                while j < n and js[j] != '\n':
                    if js[j] == '\\':
                        j += 2
                        continue
                    if js[j] == '/':
                        break
                    j += 1
                if j < n and js[j] == '/':
                    out.append(' ')
                    i = j + 1
                    continue
        if dos == '//':
            j = js.find('\n', i)
            i = n if j < 0 else j
        elif dos == '/*':
            j = js.find('*/', i + 2)
            i = n if j < 0 else j + 2
        elif c in ('"', "'", '`'):
            j = i + 1
            while j < n:
                if js[j] == '\\':
                    j += 2
                    continue
                if js[j] == c:
                    break
                j += 1
            out.append('""')
            i = j + 1
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def funciones_sin_definir(html=None):
    html = html or html_animus()
    js = _sin_ruido('\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', html, re.S)))
    definidas = set(re.findall(r'function\s+([A-Za-z_$][\w$]*)', js))
    definidas |= set(re.findall(r'(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=', js))
    definidas |= set(re.findall(r'([A-Za-z_$][\w$]*)\s*:\s*(?:async\s*)?function', js))
    definidas |= set(re.findall(r'window\.([A-Za-z_$][\w$]*)\s*=', js))

    faltan = set()
    # Lookbehind, NO un grupo opcional: `([\w$.]?)(nombre)` se come la primera letra y entonces
    # `hoyCol(` se lee como `h` + `oyCol(` -> se descarta como "parte de otro identificador" y
    # la llamada rota pasa desapercibida. Fue lo que hizo que este guard no mordiera.
    for m in re.finditer(r'(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(', js):
        nom = m.group(1)
        if nom not in definidas and nom not in GLOBALES:
            faltan.add(nom)
    # los handlers escritos en el HTML tambien tienen que existir
    for nom in re.findall(r'on(?:click|change|input|submit)="([A-Za-z_$][\w$]*)\(', html):
        if nom not in definidas:
            faltan.add(nom)
    return sorted(faltan)


if __name__ == '__main__':
    f = funciones_sin_definir()
    if f:
        print('FUNCIONES LLAMADAS Y NO DEFINIDAS:', ', '.join(f))
        raise SystemExit(1)
    print('OK · toda funcion llamada esta definida')
