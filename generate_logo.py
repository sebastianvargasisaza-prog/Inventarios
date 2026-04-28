"""
Genera el logo de Cortex Labs en multiples tamanos.

Disenio: red neuronal estilizada (nodos conectados) sobre gradient violeta.
Evoca: cerebro + neuronas + tech + sistema operativo.

Outputs:
  api/static/icons/icon-192.png
  api/static/icons/icon-512.png
  api/static/icons/icon-maskable-512.png  (con safe zone 80%)
  api/static/icons/icon-1024.png  (Apple App Store)
  api/static/icons/icon-favicon.png  (32x32)
  api/static/cortex_logo_horizontal.png  (con texto)
  api/static/cortex_logo.svg  (vector)
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pathlib import Path
import math


# ===================== Paleta =====================

BG_OUTER  = (15, 23, 42)      # azul oscuro casi negro
BG_INNER  = (76, 29, 149)     # violeta profundo
ACCENT_1  = (167, 139, 250)   # lavanda claro (nodos)
ACCENT_2  = (196, 181, 253)   # lavanda mas claro (highlight)
LINE_COL  = (139, 92, 246)    # violeta medio (lineas neurales)
WHITE     = (255, 255, 255)


def _radial_gradient(size: int, color_inner, color_outer):
    """Genera fondo gradient radial."""
    img = Image.new('RGB', (size, size), color_outer)
    cx, cy = size / 2, size / 2
    max_r = math.sqrt(cx**2 + cy**2)
    pixels = img.load()
    for y in range(size):
        for x in range(size):
            r = math.sqrt((x - cx)**2 + (y - cy)**2) / max_r
            r = min(1.0, r)
            ease = r * r  # ease-in
            R = int(color_inner[0] * (1 - ease) + color_outer[0] * ease)
            G = int(color_inner[1] * (1 - ease) + color_outer[1] * ease)
            B = int(color_inner[2] * (1 - ease) + color_outer[2] * ease)
            pixels[x, y] = (R, G, B)
    return img


def _draw_brain_network(draw: ImageDraw.ImageDraw, size: int, scale: float = 1.0):
    """Dibuja la red neuronal estilizada que evoca un cerebro.

    7 nodos en formacion organica (siluetas de cerebro).
    Lineas curvas conectan nodos vecinos.
    """
    cx, cy = size / 2, size / 2
    s = size * 0.18 * scale  # radio del area

    # Posiciones de nodos (relativas al centro)
    # Forma organica que evoca hemisferios cerebrales
    nodes = [
        (cx - s * 0.9, cy - s * 0.5),   # 0 superior izq
        (cx,           cy - s * 1.0),   # 1 top center
        (cx + s * 0.9, cy - s * 0.5),   # 2 superior der
        (cx - s * 1.1, cy + s * 0.4),   # 3 medio izq
        (cx,           cy),              # 4 center
        (cx + s * 1.1, cy + s * 0.4),   # 5 medio der
        (cx,           cy + s * 1.0),   # 6 bottom
    ]

    # Lineas entre nodos (red neuronal)
    edges = [
        (0, 1), (1, 2), (0, 3), (3, 4), (4, 5), (5, 2),
        (3, 6), (4, 6), (5, 6), (1, 4), (0, 4), (2, 4),
    ]
    line_w = max(2, int(size * 0.012))
    for a, b in edges:
        x1, y1 = nodes[a]
        x2, y2 = nodes[b]
        # Linea con grosor pequenio
        draw.line([(x1, y1), (x2, y2)], fill=LINE_COL + (180,) if False else LINE_COL, width=line_w)

    # Nodos (circulos)
    node_r = max(6, int(size * 0.038))
    glow_r = node_r * 2
    for x, y in nodes:
        # Glow exterior
        for i in range(3, 0, -1):
            r = node_r + i * (size * 0.012)
            alpha = 80 // i
            draw.ellipse(
                [x - r, y - r, x + r, y + r],
                fill=ACCENT_1,
                outline=None
            )
        # Nodo central blanco
        draw.ellipse(
            [x - node_r, y - node_r, x + node_r, y + node_r],
            fill=WHITE,
            outline=None
        )
        # Highlight pequenio
        hr = node_r * 0.45
        draw.ellipse(
            [x - hr - node_r * 0.25, y - hr - node_r * 0.25,
             x + hr - node_r * 0.25, y + hr - node_r * 0.25],
            fill=ACCENT_2,
            outline=None
        )


def _make_icon(size: int, padding_pct: float = 0.0) -> Image.Image:
    """Genera un icono cuadrado con fondo gradient + red neural.

    padding_pct: cuanto espacio dejar entre la red y el borde
                 (0.0 = full, 0.2 = 20% padding por lado para maskable).
    """
    img = _radial_gradient(size, BG_INNER, BG_OUTER)
    draw = ImageDraw.Draw(img, 'RGB')
    scale = 1.0 - padding_pct
    _draw_brain_network(draw, size, scale=scale)
    # Suavizar
    img = img.filter(ImageFilter.SMOOTH)
    return img


def _add_rounded_corners(img: Image.Image, radius: int) -> Image.Image:
    """Agrega esquinas redondeadas para iOS-style icon."""
    mask = Image.new('L', img.size, 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)
    out = img.convert('RGBA')
    out.putalpha(mask)
    return out


def _make_horizontal_logo(width: int = 1200, height: int = 360) -> Image.Image:
    """Logo horizontal con texto CORTEX LABS al lado del icono."""
    icon = _make_icon(height)
    icon = _add_rounded_corners(icon, radius=int(height * 0.22))

    canvas = Image.new('RGBA', (width, height), (15, 23, 42, 255))
    canvas.paste(icon, (20, 0), icon)

    draw = ImageDraw.Draw(canvas)
    # Texto - usa default font si no hay otra
    text_x = height + 50
    try:
        font_big = ImageFont.truetype("arialbd.ttf", int(height * 0.36))
        font_small = ImageFont.truetype("ariali.ttf", int(height * 0.12))
        font_tiny = ImageFont.truetype("arial.ttf", int(height * 0.075))
    except OSError:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_tiny = ImageFont.load_default()

    draw.text((text_x, height * 0.20), "CORTEX LABS",
              font=font_big, fill=(196, 181, 253))
    draw.text((text_x, height * 0.62), "El cerebro operativo de tu laboratorio",
              font=font_small, fill=(167, 139, 250))
    draw.text((text_x, height * 0.80), "BY HHA GROUP",
              font=font_tiny, fill=(120, 113, 108))
    return canvas


def _save_svg(path: Path):
    """Guarda una version SVG vectorial del logo (red neural)."""
    cx, cy = 256, 256
    s = 256 * 0.18
    nodes = [
        (cx - s * 0.9, cy - s * 0.5),
        (cx,           cy - s * 1.0),
        (cx + s * 0.9, cy - s * 0.5),
        (cx - s * 1.1, cy + s * 0.4),
        (cx,           cy),
        (cx + s * 1.1, cy + s * 0.4),
        (cx,           cy + s * 1.0),
    ]
    edges = [(0, 1), (1, 2), (0, 3), (3, 4), (4, 5), (5, 2),
             (3, 6), (4, 6), (5, 6), (1, 4), (0, 4), (2, 4)]
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">']
    svg.append('<defs>')
    svg.append('<radialGradient id="bg" cx="50%" cy="50%" r="70%">')
    svg.append('<stop offset="0%" stop-color="#4c1d95"/>')
    svg.append('<stop offset="100%" stop-color="#0f172a"/>')
    svg.append('</radialGradient>')
    svg.append('</defs>')
    svg.append('<rect width="512" height="512" rx="100" fill="url(#bg)"/>')
    # Lineas
    for a, b in edges:
        x1, y1 = nodes[a]; x2, y2 = nodes[b]
        svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                   f'stroke="#8b5cf6" stroke-width="6" stroke-linecap="round"/>')
    # Glow nodos
    for x, y in nodes:
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="22" fill="#a78bfa" opacity="0.5"/>')
    for x, y in nodes:
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="14" fill="#ffffff"/>')
        svg.append(f'<circle cx="{x-3:.1f}" cy="{y-3:.1f}" r="5" fill="#c4b5fd"/>')
    svg.append('</svg>')
    path.write_text('\n'.join(svg), encoding='utf-8')


# ===================== Main =====================

if __name__ == '__main__':
    base = Path(__file__).parent
    icons_dir = base / 'api' / 'static' / 'icons'
    icons_dir.mkdir(parents=True, exist_ok=True)
    static_dir = base / 'api' / 'static'

    print('Generating Cortex Labs logos...')

    # 1024 (App Store + retina)
    img_1024 = _make_icon(1024)
    img_1024.save(icons_dir / 'icon-1024.png', 'PNG')
    print('  icon-1024.png')

    # 512
    img_512 = _make_icon(512)
    img_512.save(icons_dir / 'icon-512.png', 'PNG')
    print('  icon-512.png')

    # 192
    img_192 = _make_icon(192)
    img_192.save(icons_dir / 'icon-192.png', 'PNG')
    print('  icon-192.png')

    # Maskable 512 (con padding 20% para safe zone)
    img_mask = _make_icon(512, padding_pct=0.20)
    img_mask.save(icons_dir / 'icon-maskable-512.png', 'PNG')
    print('  icon-maskable-512.png')

    # Favicon 32 (browser tab)
    img_32 = _make_icon(32)
    img_32.save(icons_dir / 'favicon-32.png', 'PNG')
    img_32.save(static_dir / 'favicon.ico', format='ICO')
    print('  favicon-32.png + favicon.ico')

    # Apple touch icon (180)
    img_180 = _make_icon(180)
    img_180.save(icons_dir / 'apple-touch-icon-180.png', 'PNG')
    print('  apple-touch-icon-180.png')

    # Logo horizontal (para login + headers)
    horiz = _make_horizontal_logo()
    horiz.save(static_dir / 'cortex_logo_horizontal.png', 'PNG')
    print('  cortex_logo_horizontal.png')

    # SVG vectorial
    _save_svg(static_dir / 'cortex_logo.svg')
    print('  cortex_logo.svg')

    print('\nDone. Icons in:', icons_dir)
