"""
Genera el logo de Cortex Labs en multiples tamanos — VERSION FINAL.

Disenio: red neuronal estilizada (7 nodos del cerebro) — el que le gusto
a Sebastian — con FONDO MAS FINO:
  - Gradiente diagonal violeta profundo a violeta brillante
  - Brillo radial superior tipo glass (sutil)
  - Brillo inferior tenue para profundidad
  - Sombra interna sutil para volumen
  - Esquinas redondeadas estilo iOS (22% radius)
  - Sin bordes duros, todo pulido

Outputs:
  api/static/icons/icon-{192,512,1024,maskable-512}.png
  api/static/icons/apple-touch-icon-180.png
  api/static/icons/favicon-32.png + favicon.ico
  api/static/cortex_logo_horizontal.png
  api/static/cortex_logo.svg
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pathlib import Path
import math


# ===================== Paleta — fondo fino =====================

# Gradiente diagonal: indigo profundo (top-left) -> violeta vibrante (bottom-right)
BG_TOP_LEFT  = (30, 27, 75)    # #1e1b4b indigo-950
BG_BOT_RIGHT = (109, 40, 217)  # #6d28d9 violet-600 (la marca)

# Nodos cerebro
NODE_WHITE     = (255, 255, 255)        # blanco puro centro
NODE_GLOW_LAV  = (196, 181, 253)        # lavanda glow
LINE_NEURAL    = (167, 139, 250, 200)   # lavanda con alpha
LINE_RGB       = (167, 139, 250)        # solido para PIL

# Detalles
HIGHLIGHT_TOP  = (255, 255, 255)
RIM_LIGHT      = (255, 255, 255, 35)


# ===================== Fondo y efectos =====================

def _diagonal_gradient(size: int) -> Image.Image:
    """Fondo gradient diagonal con curva ease-in-out suave."""
    img = Image.new('RGB', (size, size), BG_TOP_LEFT)
    pixels = img.load()
    diag_max = size + size
    for y in range(size):
        for x in range(size):
            t = (x + y) / diag_max
            t = t * t * (3 - 2 * t)  # smoothstep
            R = int(BG_TOP_LEFT[0] * (1 - t) + BG_BOT_RIGHT[0] * t)
            G = int(BG_TOP_LEFT[1] * (1 - t) + BG_BOT_RIGHT[1] * t)
            B = int(BG_TOP_LEFT[2] * (1 - t) + BG_BOT_RIGHT[2] * t)
            pixels[x, y] = (R, G, B)
    return img


def _add_top_glow(img: Image.Image) -> Image.Image:
    """Brillo radial superior tipo glass."""
    w, h = img.size
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    cx, cy = w * 0.5, h * 0.10
    rx, ry = w * 0.85, h * 0.45
    # Multiples capas de elipse para gradient suave
    for i in range(5, 0, -1):
        opacity = 18 - i * 3
        scale = 1.0 - i * 0.10
        rxs, rys = rx * scale, ry * scale
        od.ellipse(
            [cx - rxs, cy - rys, cx + rxs, cy + rys],
            fill=(255, 255, 255, opacity)
        )
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=int(w * 0.05)))
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    return Image.alpha_composite(img, overlay)


def _add_bottom_glow(img: Image.Image) -> Image.Image:
    """Sutil glow violeta-claro inferior para profundidad."""
    w, h = img.size
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    cx, cy = w * 0.5, h * 1.05
    rx, ry = w * 0.7, h * 0.4
    od.ellipse(
        [cx - rx, cy - ry, cx + rx, cy + ry],
        fill=(167, 139, 250, 50)
    )
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=int(w * 0.06)))
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    return Image.alpha_composite(img, overlay)


def _round_corners(img: Image.Image, radius_pct: float = 0.22) -> Image.Image:
    """Esquinas redondeadas estilo iOS."""
    w, h = img.size
    radius = int(min(w, h) * radius_pct)
    mask = Image.new('L', (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([(0, 0), (w, h)], radius=radius, fill=255)
    out = img.convert('RGBA')
    out.putalpha(mask)
    return out


def _add_inner_rim(img: Image.Image, radius_pct: float = 0.22) -> Image.Image:
    """Borde interno sutil de luz para dar acabado pulido."""
    w, h = img.size
    radius = int(min(w, h) * radius_pct)
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle(
        [(1, 1), (w - 2, h - 2)],
        radius=radius,
        outline=(255, 255, 255, 28),
        width=2
    )
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    return Image.alpha_composite(img, overlay)


# ===================== Red neuronal (los 7 nodos) =====================

def _draw_brain_network(draw: ImageDraw.ImageDraw, size: int, scale: float = 1.0):
    """Dibuja la red neuronal de 7 nodos formando silueta de cerebro.

    Distribucion: 3 arriba (frontal), 1 centro (corteza), 3 abajo (occipital),
    formando una hexagonal con un nodo central. Lineas conectan nodos
    vecinos como sinapsis.
    """
    cx, cy = size / 2, size / 2
    s = size * 0.20 * scale  # radio del area

    # Posiciones de nodos — forma organica que evoca hemisferios cerebrales
    nodes = [
        (cx - s * 0.95, cy - s * 0.55),   # 0 sup-izq
        (cx,            cy - s * 1.05),   # 1 top
        (cx + s * 0.95, cy - s * 0.55),   # 2 sup-der
        (cx - s * 1.10, cy + s * 0.45),   # 3 mid-izq
        (cx,            cy),               # 4 centro
        (cx + s * 1.10, cy + s * 0.45),   # 5 mid-der
        (cx,            cy + s * 1.05),   # 6 bottom
    ]

    edges = [
        (0, 1), (1, 2), (0, 3), (3, 4), (4, 5), (5, 2),
        (3, 6), (4, 6), (5, 6), (1, 4), (0, 4), (2, 4),
    ]

    # 1) Lineas neurales (con alpha si fuera RGBA)
    line_w = max(2, int(size * 0.0125))
    for a, b in edges:
        x1, y1 = nodes[a]
        x2, y2 = nodes[b]
        draw.line([(x1, y1), (x2, y2)], fill=LINE_RGB, width=line_w)

    # 2) Nodos: glow lavanda + nucleo blanco + highlight
    node_r = max(7, int(size * 0.042))
    for x, y in nodes:
        # Glow lavanda externo (3 capas escalonadas)
        for i in range(3, 0, -1):
            r = node_r + int(size * 0.014 * i)
            # Mezclamos lavanda con fondo violeta para halo suave
            blend_t = 0.30 + (3 - i) * 0.18
            R = int(BG_BOT_RIGHT[0] * (1 - blend_t) + NODE_GLOW_LAV[0] * blend_t)
            G = int(BG_BOT_RIGHT[1] * (1 - blend_t) + NODE_GLOW_LAV[1] * blend_t)
            B = int(BG_BOT_RIGHT[2] * (1 - blend_t) + NODE_GLOW_LAV[2] * blend_t)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=(R, G, B))

        # Nucleo blanco
        draw.ellipse(
            [x - node_r, y - node_r, x + node_r, y + node_r],
            fill=NODE_WHITE
        )

        # Highlight tipo orbe (pequeno punto lavanda arriba-izq del centro)
        hr = node_r * 0.42
        offset = node_r * 0.30
        draw.ellipse(
            [x - hr - offset, y - hr - offset,
             x + hr - offset, y + hr - offset],
            fill=NODE_GLOW_LAV
        )


# ===================== Composicion final =====================

def _make_icon(size: int, padding_pct: float = 0.0,
               with_round: bool = True) -> Image.Image:
    """Compone el icono completo con todos los efectos."""
    # 1) Fondo gradient
    img = _diagonal_gradient(size)
    # 2) Glow inferior (debajo de la red)
    img = _add_bottom_glow(img)
    # 3) Red neuronal
    draw = ImageDraw.Draw(img)
    scale = 1.0 - padding_pct
    _draw_brain_network(draw, size, scale=scale)
    # 4) Smooth para suavizar bordes de PIL
    img = img.filter(ImageFilter.SMOOTH)
    # 5) Glow superior (glass effect)
    img = _add_top_glow(img)
    # 6) Esquinas redondeadas
    if with_round:
        img = _round_corners(img, radius_pct=0.22)
        # 7) Borde interno sutil
        img = _add_inner_rim(img, radius_pct=0.22)
    return img


def _make_horizontal_logo(width: int = 1400, height: int = 400) -> Image.Image:
    """Logo horizontal: icono + texto CORTEX LABS."""
    icon = _make_icon(height, with_round=True)

    # Fondo del canvas: indigo profundo
    canvas = Image.new('RGBA', (width, height), (15, 23, 42, 255))
    canvas.paste(icon, (30, 0), icon)

    draw = ImageDraw.Draw(canvas)
    text_x = height + 60
    try:
        font_big = ImageFont.truetype("arialbd.ttf", int(height * 0.34))
        font_small = ImageFont.truetype("ariali.ttf", int(height * 0.11))
        font_tiny = ImageFont.truetype("arial.ttf", int(height * 0.07))
    except OSError:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_tiny = ImageFont.load_default()

    draw.text((text_x, height * 0.22), "CORTEX LABS",
              font=font_big, fill=(196, 181, 253))
    draw.text((text_x, height * 0.62), "El cerebro operativo de tu laboratorio",
              font=font_small, fill=(167, 139, 250))
    draw.text((text_x, height * 0.79), "BY HHA GROUP",
              font=font_tiny, fill=(120, 113, 108))
    return canvas


# ===================== SVG vectorial =====================

def _save_svg(path: Path):
    """Guarda version SVG vectorial — mismo diseno de 7 nodos."""
    cx, cy = 256, 256
    s = 256 * 0.20
    nodes = [
        (cx - s * 0.95, cy - s * 0.55),
        (cx,            cy - s * 1.05),
        (cx + s * 0.95, cy - s * 0.55),
        (cx - s * 1.10, cy + s * 0.45),
        (cx,            cy),
        (cx + s * 1.10, cy + s * 0.45),
        (cx,            cy + s * 1.05),
    ]
    edges = [(0, 1), (1, 2), (0, 3), (3, 4), (4, 5), (5, 2),
             (3, 6), (4, 6), (5, 6), (1, 4), (0, 4), (2, 4)]
    node_r = 22

    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">']
    parts.append('<defs>')
    parts.append('<linearGradient id="cxBg" x1="0%" y1="0%" x2="100%" y2="100%">')
    parts.append('  <stop offset="0%" stop-color="#1e1b4b"/>')
    parts.append('  <stop offset="100%" stop-color="#6d28d9"/>')
    parts.append('</linearGradient>')
    parts.append('<radialGradient id="cxTopGlow" cx="50%" cy="10%" r="65%">')
    parts.append('  <stop offset="0%" stop-color="white" stop-opacity="0.20"/>')
    parts.append('  <stop offset="100%" stop-color="white" stop-opacity="0"/>')
    parts.append('</radialGradient>')
    parts.append('<radialGradient id="cxBotGlow" cx="50%" cy="100%" r="60%">')
    parts.append('  <stop offset="0%" stop-color="#a78bfa" stop-opacity="0.45"/>')
    parts.append('  <stop offset="100%" stop-color="#a78bfa" stop-opacity="0"/>')
    parts.append('</radialGradient>')
    parts.append('<filter id="cxNodeGlow" x="-50%" y="-50%" width="200%" height="200%">')
    parts.append('  <feGaussianBlur stdDeviation="6"/>')
    parts.append('</filter>')
    parts.append('</defs>')

    # Fondo + glow inferior + glow superior
    parts.append('<rect width="512" height="512" rx="112" fill="url(#cxBg)"/>')
    parts.append('<rect width="512" height="512" rx="112" fill="url(#cxBotGlow)"/>')
    parts.append('<rect width="512" height="512" rx="112" fill="url(#cxTopGlow)"/>')

    # Borde interno sutil
    parts.append('<rect x="2" y="2" width="508" height="508" rx="110" '
                 'fill="none" stroke="white" stroke-opacity="0.10" stroke-width="1.5"/>')

    # Lineas neurales
    for a, b in edges:
        x1, y1 = nodes[a]
        x2, y2 = nodes[b]
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#a78bfa" stroke-width="6" stroke-linecap="round"/>'
        )

    # Glow nodos (lavanda)
    for x, y in nodes:
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{node_r + 12}" '
            f'fill="#c4b5fd" opacity="0.45" filter="url(#cxNodeGlow)"/>'
        )
    # Nucleo blanco
    for x, y in nodes:
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{node_r}" fill="white"/>'
        )
    # Highlight pequeno
    for x, y in nodes:
        parts.append(
            f'<circle cx="{x - node_r * 0.30:.1f}" cy="{y - node_r * 0.30:.1f}" '
            f'r="{node_r * 0.42:.1f}" fill="#c4b5fd"/>'
        )

    parts.append('</svg>')
    path.write_text('\n'.join(parts), encoding='utf-8')


# ===================== Main =====================

if __name__ == '__main__':
    base = Path(__file__).parent
    icons_dir = base / 'api' / 'static' / 'icons'
    icons_dir.mkdir(parents=True, exist_ok=True)
    static_dir = base / 'api' / 'static'

    print('Generating Cortex Labs FINAL logo (7-node brain)...')

    img_1024 = _make_icon(1024)
    img_1024.save(icons_dir / 'icon-1024.png', 'PNG')
    print('  icon-1024.png')

    img_512 = _make_icon(512)
    img_512.save(icons_dir / 'icon-512.png', 'PNG')
    print('  icon-512.png')

    img_192 = _make_icon(192)
    img_192.save(icons_dir / 'icon-192.png', 'PNG')
    print('  icon-192.png')

    img_mask = _make_icon(512, padding_pct=0.18, with_round=False)
    img_mask.save(icons_dir / 'icon-maskable-512.png', 'PNG')
    print('  icon-maskable-512.png')

    img_180 = _make_icon(180)
    img_180.save(icons_dir / 'apple-touch-icon-180.png', 'PNG')
    print('  apple-touch-icon-180.png')

    img_32 = _make_icon(32, with_round=False)
    img_32.save(icons_dir / 'favicon-32.png', 'PNG')
    img_32.save(static_dir / 'favicon.ico', format='ICO')
    print('  favicon-32.png + favicon.ico')

    horiz = _make_horizontal_logo()
    horiz.save(static_dir / 'cortex_logo_horizontal.png', 'PNG')
    print('  cortex_logo_horizontal.png')

    _save_svg(static_dir / 'cortex_logo.svg')
    print('  cortex_logo.svg')

    print('\nDone. Icons in:', icons_dir)
