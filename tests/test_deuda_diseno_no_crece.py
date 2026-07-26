"""La deuda de diseño no puede CRECER (26-jul · Sebastián: "¿es premium?").

Medido ese día en `dashboard_html.py`: **8.072 colores hardcodeados contra 40 tokens** del sistema
(99,5% del color a mano), **415 valores de color distintos** — o sea que no hay paleta, cada vista
se inventó sus grises y sus violetas — 385 emojis usados como iconografía, 7.032 estilos inline y
201 bloques ocultos con `display:none`.

Por eso el tema oscuro no funciona en Planta: los fondos claros están fijos en el HTML y ganan
sobre cualquier hoja de estilos.

Arreglar los 8.000 de golpe es un proyecto de semanas en el archivo más frágil del sistema, y
compite con construir fabricación y acondicionamiento. La decisión (26-jul) fue: **no arreglar
todo ahora, pero impedir que crezca.**

Este test es un TRINQUETE: fija el máximo actual y falla si sube. No obliga a mejorar; obliga a no
empeorar. La regla 0 del cerebro ("toda UI que toco sale premium con tokens `--cx-*`") ya estaba
escrita y no se cumplió — una regla que nadie verifica es una intención, no un blindaje.

**Si este test falla porque agregaste una vista nueva:** no subas el número. Usá los tokens
(`var(--cx-primary)`, `var(--cx-text-mute)`, `var(--cx-card)`, `var(--cx-border)`…). Si de verdad
hace falta un color que no existe, agregalo a `cortex.css` como token y usalo desde ahí.
**Si el test falla y vos MEJORASTE** (migraste colores a tokens), bajá el techo a lo que quedó:
así el trinquete aprieta y nunca se afloja.
"""
import io
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(RAIZ, 'api', 'templates_py')

# Techos medidos el 26-jul-2026, EXACTOS (un trinquete con holgura no aprieta).
# BAJARLOS cuando se migre a tokens; NUNCA subirlos.
TECHO_COLORES_DASHBOARD = 8077
TECHO_DISPLAY_NONE_DASHBOARD = 201
TECHO_COLORES_TOTAL = 15619   # los 42 templates juntos

_HEX = re.compile(r'#[0-9a-fA-F]{3,8}\b')
_NONE = re.compile(r'display\s*:\s*none')


def _leer(nombre):
    with io.open(os.path.join(TEMPLATES, nombre), encoding='utf-8') as fh:
        return fh.read()


def _contar_colores(s):
    return len(_HEX.findall(s))


def test_el_dashboard_no_agrega_colores_hardcodeados():
    """El archivo más grande y más frágil: 1,9 MB con el JS embebido."""
    n = _contar_colores(_leer('dashboard_html.py'))
    assert n <= TECHO_COLORES_DASHBOARD, (
        'dashboard_html.py subió a %d colores hardcodeados (techo %d). Usá los tokens del sistema '
        '(var(--cx-primary), var(--cx-text-mute), var(--cx-card)…) en vez de un #hex: si no, esa '
        'pantalla no respeta el tema oscuro. Si en cambio MIGRASTE colores a tokens, bajá el techo '
        'en este test a %d.' % (n, TECHO_COLORES_DASHBOARD, n))


def test_el_dashboard_no_agrega_bloques_ocultos():
    """Cada `display:none` permanente es una pantalla vieja escondida. Ya hay 201: son la causa de
    que alguien edite la parte equivocada del archivo."""
    n = len(_NONE.findall(_leer('dashboard_html.py')))
    assert n <= TECHO_DISPLAY_NONE_DASHBOARD, (
        'dashboard_html.py subió a %d `display:none` (techo %d). Si retiraste una vista, BORRALA; '
        'esconderla deja código muerto que confunde. Si bajaste el número, ajustá el techo a %d.'
        % (n, TECHO_DISPLAY_NONE_DASHBOARD, n))


def test_los_templates_en_conjunto_no_agregan_color_a_mano():
    total = 0
    for f in sorted(os.listdir(TEMPLATES)):
        if f.endswith('.py'):
            total += _contar_colores(_leer(f))
    assert total <= TECHO_COLORES_TOTAL, (
        'los templates subieron a %d colores hardcodeados (techo %d). Toda vista nueva va con '
        'tokens var(--cx-*) · ver la regla 0 en .claude/CERO_ERROR.md' % (total, TECHO_COLORES_TOTAL))


def test_el_techo_esta_apretado():
    """Un trinquete flojo no sirve: si el número real bajó mucho, hay que bajar el techo.

    Falla a propósito cuando sobra más del 4% de holgura, para forzar que la mejora quede fijada y
    no se pueda volver atrás en silencio.
    """
    n = _contar_colores(_leer('dashboard_html.py'))
    holgura = TECHO_COLORES_DASHBOARD - n
    assert holgura <= max(40, int(TECHO_COLORES_DASHBOARD * 0.04)), (
        'el dashboard bajó a %d colores y el techo sigue en %d (sobran %d). Bajá '
        'TECHO_COLORES_DASHBOARD a %d para fijar la mejora.'
        % (n, TECHO_COLORES_DASHBOARD, holgura, n))


def test_cortex_tiene_los_tokens_que_el_mensaje_de_error_recomienda():
    """Si el test recomienda un token, ese token tiene que existir."""
    css = io.open(os.path.join(RAIZ, 'api', 'static', 'cortex.css'), encoding='utf-8').read()
    for tok in ('--cx-primary', '--cx-text', '--cx-text-mute', '--cx-card', '--cx-border',
                '--cx-success', '--cx-warn', '--cx-danger', '--cx-bg'):
        assert tok in css, 'falta el token %s en cortex.css' % tok
