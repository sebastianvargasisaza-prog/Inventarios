# -*- coding: utf-8 -*-
"""Tapa comentarios y literales de un JS CONSERVANDO las posiciones.

Vive aparte porque lo usan dos cosas: el chequeo de funciones sin definir y la poda de codigo
inalcanzable. Y conserva el largo a proposito: si la limpieza acortara el texto, los indices
dejarian de corresponder al original y cualquier recorte por posicion caeria en el lugar
equivocado.

⚠ No se puede hacer con un regex: una comilla dentro de un literal de expresion regular
(`.replace(/'/g, ...)`) lo desincroniza y se come el resto del archivo -- con eso el chequeo
reporta como "no definidas" decenas de funciones que si existen, se vuelve ruido, y deja de
mirarse.
"""

_ANTES_DE_REGEX = set('(,=:[!&|?{};\n+*%<>~^')


def enmascarar(js):
    out = list(js)
    i, n = 0, len(js)
    while i < n:
        c = js[i]
        dos = js[i:i + 2]
        if dos == '//':
            j = js.find('\n', i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = ' '
            i = j
        elif dos == '/*':
            j = js.find('*/', i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                out[k] = ' '
            i = j
        elif c == '/':
            prev = next((js[k] for k in range(i - 1, -1, -1) if not js[k].isspace()), '')
            if prev == '' or prev in _ANTES_DE_REGEX:
                j = i + 1
                while j < n and js[j] != '\n':
                    if js[j] == '\\':
                        j += 2
                        continue
                    if js[j] == '/':
                        break
                    j += 1
                if j < n and js[j] == '/':
                    for k in range(i, j + 1):
                        out[k] = ' '
                    i = j + 1
                    continue
            i += 1
        elif c in ('"', "'", '`'):
            j = i + 1
            while j < n:
                if js[j] == '\\':
                    j += 2
                    continue
                if js[j] == c:
                    break
                j += 1
            for k in range(i, min(j + 1, n)):
                out[k] = ' '
            i = j + 1
        else:
            i += 1
    return ''.join(out)


def cuerpos_de_funciones(limpio):
    """{nombre: (inicio, fin)} contando llaves sobre el texto ENMASCARADO."""
    import re
    out = {}
    for m in re.finditer(r'(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{', limpio):
        d, i, n = 0, m.end() - 1, len(limpio)
        while i < n:
            if limpio[i] == '{':
                d += 1
            elif limpio[i] == '}':
                d -= 1
                if d == 0:
                    break
            i += 1
        out[m.group(1)] = (m.start(), i + 1)
    return out
