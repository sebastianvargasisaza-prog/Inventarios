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

# Techos EXACTOS (un trinquete con holgura no aprieta). BAJARLOS al migrar; NUNCA subirlos.
# 26-jul-2026, primera medición:            dashboard 8.077 · total 15.619
# tras migrar 9.685 declaraciones a tokens: dashboard 3.116 · total  5.934
# tras devolver a literal los 1.107 `color:#fff` (texto blanco sobre un relleno de color: NO
# depende del tema, mandarlo a --cx-card lo volvía oscuro sobre oscuro en el tema oscuro):
#                                           dashboard 3.578 · total  6.748
# y con la MEDICIÓN corregida (sin entidades HTML de iconos, sin el blanco de texto legítimo):
#                                           dashboard 2.509 · total  5.024
# tras migrar los chips de estado de Fabricación y unificar las 3 vistas del día en un solo
# renderizador (Envasado · Fabricación · Acondicionamiento):
TECHO_COLORES_DASHBOARD = 2499
TECHO_DISPLAY_NONE_DASHBOARD = 201
TECHO_COLORES_TOTAL = 5014   # los 42 templates juntos
TECHO_FONDO_OPACO = 0        # un fondo opaco sin token IGNORA el tema oscuro · debe quedar en 0
TECHO_TEXTO_PALABRA = 28     # `color:gray|black|red…` · el blanco no cuenta (ver abajo)

# `(?<!&)` deja fuera las ENTIDADES HTML: `&#9888;` (⚠) y `&#128203;` (📋) matcheaban como si
# fueran colores y le sumaban ruido al conteo. Un trinquete que cuenta iconos como deuda mide mal.
_HEX = re.compile(r'(?<!&)#[0-9a-fA-F]{3,8}\b')
# `color:#fff` NO es deuda: el texto blanco sobre un relleno de color es correcto y no depende del
# tema (por eso 1.107 volvieron a literal). Se descuenta para que el techo mida deuda de verdad.
_BLANCO_TEXTO = re.compile(r'(?<![-\w])color\s*:\s*#(?:fff|ffffff)\b', re.I)
_NONE = re.compile(r'display\s*:\s*none')

# El primer trinquete sólo contaba HEX y se le escapaban 617 colores escritos de otra forma:
# `background:white` sigue blanco en tema oscuro igual que `background:#fff`. Los rgba()
# TRANSLÚCIDOS (superposiciones de modal, sombras) no cuentan: funcionan en los dos temas.
_FONDO_OPACO = re.compile(
    r'background[a-z-]*\s*:\s*(?:white|black|whitesmoke|ghostwhite|ivory|snow'
    r'|rgb\([0-9., ]+\)|rgba\([0-9., ]+,\s*1(?:\.0+)?\s*\))(?![-\w])', re.I)
# `color:white` NO entra: el texto blanco sobre un relleno de color es correcto y NO depende del
# tema (por eso 1.107 de ellos se devolvieron a literal). Lo que sí es deuda es todo el resto.
_TEXTO_PALABRA = re.compile(
    r'(?<![-\w])color\s*:\s*(?:black|gray|grey|silver|darkgray|lightgray'
    r'|red|green|blue|orange|purple|brown|pink)(?![-\w])', re.I)


def _leer(nombre):
    with io.open(os.path.join(TEMPLATES, nombre), encoding='utf-8') as fh:
        return fh.read()


def _contar_colores(s):
    """Colores hardcodeados que SON deuda: sin entidades HTML y sin el blanco de texto legítimo."""
    return len(_HEX.findall(s)) - len(_BLANCO_TEXTO.findall(s))


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


def test_ningun_fondo_opaco_ignora_el_tema():
    """`background:white` es tan ciego al tema oscuro como `background:#fff`, y el primer
    trinquete no lo veía porque sólo contaba hex. Los 83 que había ya están migrados; este
    techo es CERO para que no vuelva a entrar ninguno."""
    total, donde = 0, []
    for f in sorted(os.listdir(TEMPLATES)):
        if f.endswith('.py'):
            n = len(_FONDO_OPACO.findall(_leer(f)))
            if n:
                total += n
                donde.append('%s (%d)' % (f, n))
    assert total <= TECHO_FONDO_OPACO, (
        'hay %d fondo(s) opaco(s) sin token: %s. Un `background:white`/`rgb(255,255,255)` se '
        'queda blanco en tema oscuro. Usá var(--cx-card) o var(--cx-bg-alt).'
        % (total, ', '.join(donde)))


def test_el_color_por_palabra_no_crece():
    """`color:gray` no respeta el tema. `color:white` NO cuenta: el texto blanco sobre un relleno
    de color es correcto y no depende del tema (por eso 1.107 volvieron a literal)."""
    total = sum(len(_TEXTO_PALABRA.findall(_leer(f)))
                for f in sorted(os.listdir(TEMPLATES)) if f.endswith('.py'))
    assert total <= TECHO_TEXTO_PALABRA, (
        'subió a %d `color:<palabra>` (techo %d). Usá var(--cx-text-mute) y familia.'
        % (total, TECHO_TEXTO_PALABRA))


def test_los_semanticos_tienen_par_de_texto_para_el_tema_oscuro():
    """Un color de RELLENO y el mismo color como TEXTO no pueden ser el mismo token: al invertir
    el tema tiran en direcciones opuestas. Con un solo token, el violeta como texto daba 2,06:1
    sobre la tarjeta oscura. Este test fija esa separación: los 5 pares existen y el bloque
    oscuro los redefine (si alguien borra el override, el texto vuelve a ser ilegible)."""
    css = io.open(os.path.join(RAIZ, 'api', 'static', 'cortex.css'), encoding='utf-8').read()
    i = css.find('[data-theme="dark"]')
    assert i > 0, 'cortex.css perdió el bloque de tema oscuro'
    oscuro = css[i:]
    for tok in ('--cx-primary-text', '--cx-success-text', '--cx-danger-text',
                '--cx-info-text', '--cx-warn-text'):
        assert tok in css, 'falta el token de texto %s en cortex.css' % tok
        assert tok in oscuro, (
            '%s existe pero el tema OSCURO no lo redefine → ese texto queda ilegible sobre el '
            'fondo oscuro (era 2,06:1 antes de separarlos)' % tok)


def _luminancia(hexv):
    h = hexv.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    canales = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contraste(a, b):
    la, lb = _luminancia(a), _luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _tokens(bloque):
    return dict(re.findall(r'(--cx-[a-z-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;', bloque))


def test_los_tokens_de_texto_pasan_AA_en_los_dos_temas():
    """El contraste se degrada sin que nadie lo note: alguien "ajusta un gris" y meses después la
    letra no se lee al sol del piso de planta. Acá se calcula, no se confía.

    Se verifica contra el fondo MÁS EXIGENTE de cada tema (el que menos contrasta). AA = 4,5:1.
    """
    css = io.open(os.path.join(RAIZ, 'api', 'static', 'cortex.css'), encoding='utf-8').read()
    i = css.find('[data-theme="dark"]')
    claro, oscuro = _tokens(css[:i]), _tokens(css[i:])

    def val(tok, tema):
        return (oscuro if tema == 'oscuro' else claro).get(tok) or claro.get(tok)

    fondos = {'claro': ('#ffffff', '#f4f4f7'), 'oscuro': ('#0f172a', '#1e293b')}
    # --cx-text-faint queda fuera a propósito: es decorativo (separadores, marcas de agua),
    # nunca texto de lectura. Si alguna vez se usa para leer, el problema es el uso, no el token.
    de_lectura = ('--cx-text', '--cx-text-soft', '--cx-text-mute', '--cx-primary-text',
                  '--cx-success-text', '--cx-danger-text', '--cx-info-text', '--cx-warn-text')
    fallos = []
    for tok in de_lectura:
        for tema, fs in fondos.items():
            v = val(tok, tema)
            assert v, 'el token %s no existe' % tok
            for f in fs:
                r = _contraste(v, f)
                if r < 4.5:
                    fallos.append('%s (%s) = %s sobre %s -> %.2f:1' % (tok, tema, v, f, r))
    assert not fallos, ('estos tokens de texto no llegan a AA (4,5:1):\n  ' +
                        '\n  '.join(fallos) +
                        '\nOscurecé el valor del tema claro o aclará el del oscuro.')


def test_los_chips_se_leen_sobre_su_propio_fondo_palido():
    """El hueco que dejé en la primera versión de este test: sólo medí el texto contra el FONDO y
    la TARJETA, y los chips de estado ponen texto semántico sobre el pálido del MISMO color
    (`--cx-info-text` sobre `--cx-info-pale`). Al mirar la lista de Envasado en oscuro, el chip
    'ENVASANDO' daba 4,07:1 porque `--cx-info-pale` era el único pálido que no se había oscurecido
    como sus hermanos. Un par que nadie mide es un par que se degrada."""
    css = io.open(os.path.join(RAIZ, 'api', 'static', 'cortex.css'), encoding='utf-8').read()
    i = css.find('[data-theme="dark"]')
    claro, oscuro = _tokens(css[:i]), _tokens(css[i:])
    fallos = []
    for base in ('primary', 'success', 'danger', 'info', 'warn'):
        for tema, tabla in (('claro', claro), ('oscuro', oscuro)):
            txt = tabla.get('--cx-%s-text' % base) or claro.get('--cx-%s-text' % base)
            pale = tabla.get('--cx-%s-pale' % base) or claro.get('--cx-%s-pale' % base)
            assert txt and pale, 'faltan tokens de %s' % base
            r = _contraste(txt, pale)
            if r < 4.5:
                fallos.append('--cx-%s-text sobre --cx-%s-pale (%s): %s sobre %s -> %.2f:1'
                              % (base, base, tema, txt, pale, r))
    assert not fallos, ('estos chips no se leen:\n  ' + '\n  '.join(fallos) +
                        '\nEn tema oscuro el pale tiene que ser OSCURO de verdad (mirá que '
                        '--cx-primary-pale es #1e1b4b, no un tono medio).')


def test_el_texto_blanco_sobre_los_rellenos_se_sigue_leyendo():
    """La contracara: si alguien ACLARA un token de relleno para "mejorar el texto", rompe el
    texto blanco de los botones. Los dos lados tienen que sostenerse a la vez."""
    css = io.open(os.path.join(RAIZ, 'api', 'static', 'cortex.css'), encoding='utf-8').read()
    i = css.find('[data-theme="dark"]')
    claro, oscuro = _tokens(css[:i]), _tokens(css[i:])
    fallos = []
    for tok in ('--cx-primary', '--cx-success', '--cx-danger', '--cx-info'):
        for tema, tabla in (('claro', claro), ('oscuro', oscuro)):
            v = tabla.get(tok) or claro.get(tok)
            r = _contraste('#ffffff', v)
            if r < 4.5:
                fallos.append('blanco sobre %s (%s) = %s -> %.2f:1' % (tok, tema, v, r))
    assert not fallos, ('el texto blanco no se lee sobre estos rellenos:\n  ' +
                        '\n  '.join(fallos) +
                        '\nEl relleno tiene que quedarse OSCURO; para el texto está --cx-*-text.')


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
