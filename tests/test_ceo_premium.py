# -*- coding: utf-8 -*-
"""El tablero del CEO se puede LEER en los dos temas (5-ago).

Sebastián: *"no tiene premium"*. Antes de opinar sobre cómo se ve, se mide el contraste real de
cada par (fondo, texto) en los DOS temas (M114). Salieron tres por debajo de 3:1, y los peores
en tema **claro, que es el default**:

    botón "Panel Central"  1.03   `color:#fff` sobre `--cx-bg-alt` → literalmente invisible
    botón "Guardar inputs" 2.49   texto oscuro sobre relleno violeta
    chip "CEO"             1.00   violeta sobre violeta (2.61 en oscuro)

Los tres son el mismo error de fondo (M104): **un color de RELLENO y el mismo color como TEXTO no
pueden salir del mismo token.** Sobre un relleno de color el texto va blanco — eso no depende del
tema; sobre una superficie clara va el token de texto.

⚠ Este test EXTRAE los pares del HTML renderizado. La primera versión de la medición los tenía
**escritos a mano**, y eso documenta la intención pero no mide el archivo: después de aplicar los
arreglos seguía reportando los mismos tres fallos, porque estaba leyendo su propia lista y no la
página (M142). Un trinquete con una lista a mano se pudre el día que alguien agrega un par nuevo.
"""
import io
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _html():
    import sys
    api = os.path.join(RAIZ, 'api')
    if api not in sys.path:
        sys.path.insert(0, api)
    from templates_py.gerencia_html import GERENCIA_HTML
    return GERENCIA_HTML


def _sin_comentarios(h):
    """Saca los comentarios CSS y HTML antes de buscar.

    ⚠ Ya van CINCO veces que un test busca un valor y encuentra MI PROPIO COMENTARIO explicando
    por qué ese valor dejó de usarse (M154). Cuando se verifica por texto, los comentarios se
    quitan primero."""
    h = re.sub(r'/\*.*?\*/', ' ', h, flags=re.S)
    return re.sub(r'<!--.*?-->', ' ', h, flags=re.S)


# ── resolución de tokens y contraste ─────────────────────────────────────────

def _tokens(tema):
    css = io.open(os.path.join(RAIZ, 'api/static/cortex.css'), encoding='utf-8').read()
    vals = {}
    m = re.search(r':root\s*\{(.*?)\}', css, re.S)
    if m:
        for k, v in re.findall(r'(--cx-[\w-]+)\s*:\s*([^;]+);', m.group(1)):
            vals[k] = v.strip()
    if tema == 'dark':
        for blq in re.findall(r'\[data-theme="dark"\]\s*\{(.*?)\}', css, re.S):
            for k, v in re.findall(r'(--cx-[\w-]+)\s*:\s*([^;]+);', blq):
                vals[k] = v.strip()
    return vals


def _rgb(v, vals, prof=0):
    v = (v or '').strip()
    if prof > 6:
        return None
    m = re.match(r'var\(\s*(--cx-[\w-]+)\s*(?:,\s*(.+))?\)$', v)
    if m:
        t = vals.get(m.group(1))
        if t:
            return _rgb(t, vals, prof + 1)
        return _rgb(m.group(2), vals, prof + 1) if m.group(2) else None
    m = re.match(r'#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$', v)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return {'white': (255, 255, 255), 'black': (0, 0, 0)}.get(v.lower())


def _lum(rgb):
    def f(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(rgb[0]) + 0.7152 * f(rgb[1]) + 0.0722 * f(rgb[2])


def _ratio(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _pares(html):
    """Los pares (fondo, texto) que la PÁGINA declara · extraídos, no listados a mano (M142).

    Sólo cuentan los pares en los que fondo y texto están en la MISMA declaración: si el fondo lo
    pone otra regla no se puede saber cuál gana sin un navegador, y adivinar produce ruido.
    """
    out = []
    # reglas CSS  ·  .clase{...background:X...color:Y...}
    for sel, cuerpo in re.findall(r'([.#][\w.#\s>-]+)\s*\{([^}]*)\}', html):
        bg = re.search(r'(?:^|[;{\s])background(?:-color)?\s*:\s*([^;}]+)', cuerpo)
        fg = re.search(r'(?:^|[;{\s])color\s*:\s*([^;}]+)', cuerpo)
        if bg and fg:
            out.append((sel.strip()[:44], bg.group(1).strip(), fg.group(1).strip()))
    # estilos en línea  ·  style="background:X;color:Y"
    for est in re.findall(r'style="([^"]*)"', html):
        bg = re.search(r'(?:^|;)\s*background(?:-color)?\s*:\s*([^;]+)', est)
        fg = re.search(r'(?:^|;)\s*color\s*:\s*([^;]+)', est)
        if bg and fg:
            out.append(('inline: ' + est[:40], bg.group(1).strip(), fg.group(1).strip()))
    return out


def _ilegibles(umbral=3.0):
    html = _html()
    malos = []
    for tema in ('light', 'dark'):
        vals = _tokens(tema)
        for nom, bg, fg in _pares(html):
            # los fondos translúcidos funcionan en los dos temas · no se pueden medir sin
            # componer contra su padre, y adivinar el padre es ruido
            if 'rgba' in bg or 'gradient' in bg or 'rgba' in fg:
                continue
            a, b = _rgb(bg, vals), _rgb(fg, vals)
            if not a or not b:
                continue
            r = _ratio(a, b)
            if r < umbral:
                malos.append((tema, nom, round(r, 2), bg, fg))
    return malos


# ── los tests ────────────────────────────────────────────────────────────────

def test_NINGUN_par_del_tablero_es_ILEGIBLE(app, db_clean):
    """Extrae los pares de la página y los mide en los dos temas. El peor que había daba 1.03:
    el botón "Panel Central" era invisible en tema claro."""
    malos = _ilegibles()
    assert not malos, 'pares por debajo de 3:1:\n  ' + '\n  '.join(
        '%s · %s · %.2f  (%s sobre %s)' % (t, n, r, fg, bg) for t, n, r, bg, fg in malos)


def test_el_boton_PANEL_CENTRAL_es_legible(app, db_clean):
    """El caso concreto: `color:#fff` sobre `--cx-bg-alt`, que en tema claro es casi blanco."""
    h = _sin_comentarios(_html())
    i = h.find('href="/hub"')
    assert i > 0, 'se perdió el botón al Panel Central'
    tramo = h[max(0, i - 300):i + 300]
    assert 'color:#fff' not in tramo, 'volvió el texto blanco sobre una superficie clara'


def test_sobre_un_RELLENO_de_color_el_texto_va_BLANCO(app, db_clean):
    """El error de fondo (M104): un color de relleno y el mismo color como texto no pueden salir
    del mismo token · al invertir el tema tiran en direcciones opuestas."""
    h = _html()
    for clase in ('.btn-save', '.badge-ceo'):
        i = h.find(clase + '{')
        assert i > 0, 'no encontré %s' % clase
        regla = h[i:h.find('}', i)]
        assert 'color:#fff' in regla, '%s no usa texto blanco sobre su relleno de color' % clase
        assert 'color:var(--cx-text)' not in regla and 'color:var(--cx-primary-text)' not in regla


def test_el_hover_del_boton_no_es_de_OTRA_paleta(app, db_clean):
    """`#1d5c5a` es un verde azulado: resto de una paleta anterior, sobre un botón violeta."""
    h = _sin_comentarios(_html())
    assert '#1d5c5a' not in h, 'volvió el hover de la paleta vieja'


def test_las_secciones_SEPARAN(app, db_clean):
    """Los encabezados eran texto gris suelto y no separaban nada: la página se leía como una
    lista larga en vez de como bloques."""
    h = _html()
    i = h.find('.section-title{')
    assert i > 0
    regla = h[i:h.find('}', i)]
    assert 'border-bottom' in regla, 'los encabezados de sección siguen sin separar'


def test_los_numeros_de_dinero_se_ALINEAN(app, db_clean):
    """Cifras en columna sin `tabular-nums` bailan de ancho y se leen mal."""
    h = _html()
    for clase in ('.fin-val{', '.kpi-val{'):
        i = h.find(clase)
        assert i > 0, 'no encontré %s' % clase
        assert 'tabular-nums' in h[i:h.find('}', i)], '%s no alinea los dígitos' % clase


def test_el_medidor_SIRVE_para_este_archivo(app, db_clean):
    """⚠ El guard del guard. La primera versión de la medición tenía los pares escritos a mano y
    seguía reportando fallos ya corregidos, porque leía su propia lista y no la página (M142).
    Acá se verifica que la extracción de verdad encuentra pares del archivo."""
    pares = _pares(_html())
    assert len(pares) >= 15, 'la extracción sólo encontró %d pares · no está leyendo la página' % len(pares)
    nombres = ' '.join(p[0] for p in pares)
    assert '.btn-save' in nombres or 'btn-save' in nombres, 'no ve las reglas del archivo'
