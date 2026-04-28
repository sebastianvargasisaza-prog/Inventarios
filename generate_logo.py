"""
Genera el logo de Cortex Labs en multiples tamanos — version PROFESIONAL.

Disenio v2:
  - Glifo monograma "C" estilizado con corte interno
  - Acento de neurona (3 puntos conectados) como elemento sutil
  - Gradiente diagonal violeta → indigo profundo
  - Esquinas redondeadas estilo iOS / macOS
  - Sombra interna sutil para profundidad
  - Brillo superior tipo glass

Outputs:
  api/static/icons/icon-192.png
  api/static/icons/icon-512.png
  api/static/icons/icon-maskable-512.png
  api/static/icons/icon-1024.png
  api/static/icons/apple-touch-icon-180.png
  api/static/icons/favicon-32.png
  api/static/favicon.ico
  api/static/cortex_logo_horizontal.png
  api/static/cortex_logo.svg
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pathlib import Path
import math


# ===================== Paleta =====================

# Background diagonal gradient
BG_TOP_LEFT  = (124, 58, 237)   # #7c3aed violet-600
BG_BOT_RIGHT = (44, 19, 102)    # #2c1366 violet-950 muy oscuro

# Glifo principal
GLYPH_COLOR  = (255, 255, 255)  # blanco puro
GLYPH_GLOW   = (196, 181, 253)  # lavanda

# Acentos neuronales
ACCENT_DOT   = (251, 191, 36)   # amber-400 — toque calido
ACCENT_LINE  = (255, 255, 255, 100)  # blanco semitransparente

# Brillo superior (glass effect)
HIGHLIGHT    = (255, 255, 255, 60)


# ===================== Helpers =====================

def _diagonal_gradient(size: int) -> Image.Image:
    """Genera fondo gradient diagonal (top-left → bottom-right)."""
    img = Image.new('RGB', (size, size), BG_TOP_LEFT)
    pixels = img.load()
    diag_max = size + size  # max diagonal coord
    for y in range(size):
        for x in range(size):
            t = (x + y) / diag_max
            # Suavizar con ease-in-out
            t = t * t * (3 - 2 * t)
            R = int(BG_TOP_LEFT[0] * (1 - t) + BG_BOT_RIGHT[0] * t)
            G = int(BG_TOP_LEFT[1] * (1 - t) + BG_BOT_RIGHT[1] * t)
            B = int(BG_TOP_LEFT[2] * (1 - t) + BG_BOT_RIGHT[2] * t)
            pixels[x, y] = (R, G, B)
    return img


def _round_corners(img: Image.Image, radius_pct: float = 0.22) -> Image.Image:
    """Esquinas redondeadas estilo iOS (~22% del lado)."""
    w, h = img.size
    radius = int(min(w, h) * radius_pct)
    mask = Image.new('L', (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([(0, 0), (w, h)], radius=radius, fill=255)
    out = img.convert('RGBA')
    out.putalpha(mask)
    return out


def _draw_c_monogram(draw: ImageDraw.ImageDraw, size: int, scale: float = 1.0):
    """Dibuja una 'C' estilizada al estilo Cortex Labs.

    La 'C' es un anillo grueso con un corte en el lado derecho que evoca
    procesamiento / abertura / activacion neural. El corte tiene un acento
    de 3 puntos (neurona) que reemplazan parte del trazo.
    """
    cx, cy = size / 2, size / 2
    R_outer = size * 0.34 * scale     # radio externo del anillo
    stroke  = size * 0.085 * scale    # grosor del trazo

    # 1) Anillo blanco principal — la 'C' con corte amplio a la DERECHA
    # PIL: 0°=Este, 90°=Sur(abajo), 180°=Oeste, 270°=Norte(arriba) [horario]
    # Para que el corte de 130° quede centrado en el Este (0°):
    #   corte = (-65°, +65°)
    #   arc dibujado = de 65° a 295° (recorre 230° en sentido horario,
    #   pasando por Sur → Oeste → Norte)
    bbox = [cx - R_outer, cy - R_outer, cx + R_outer, cy + R_outer]
    draw.arc(bbox, start=65, end=295, fill=GLYPH_COLOR, width=int(stroke))

    # Tapas redondeadas en los extremos del arc — caps round-linecap
    r_cap = stroke / 2
    # Extremo inferior del arc (angulo 65° = SE, abajo-derecha)
    a_bot = math.radians(65)
    cap_bot = (cx + R_outer * math.cos(a_bot), cy + R_outer * math.sin(a_bot))
    draw.ellipse(
        [cap_bot[0] - r_cap, cap_bot[1] - r_cap,
         cap_bot[0] + r_cap, cap_bot[1] + r_cap],
        fill=GLYPH_COLOR
    )
    # Extremo superior del arc (angulo 295° = NE, arriba-derecha)
    a_top = math.radians(295)
    cap_top = (cx + R_outer * math.cos(a_top), cy + R_outer * math.sin(a_top))
    draw.ellipse(
        [cap_top[0] - r_cap, cap_top[1] - r_cap,
         cap_top[0] + r_cap, cap_top[1] + r_cap],
        fill=GLYPH_COLOR
    )

    # 2) Tres puntos neurona AFUERA del anillo (eje derecho, dentro del corte)
    # Posicion: a la derecha del centro, separados verticalmente
    dot_radius = stroke * 0.30
    spacing = stroke * 1.40
    # Centro de los dots: en el centro vertical, a R_outer * 1.05 a la derecha
    cx_dots = cx + R_outer * 0.55  # ligeramente al interior del corte
    for i, dy in enumerate([-spacing, 0, spacing]):
        # Halo amber sutil (mezcla con fondo)
        for g in range(3, 0, -1):
            r = dot_radius + g * 2.5
            blend_t = 0.20 + (3 - g) * 0.08
            r_blend = int(BG_BOT_RIGHT[0] * (1 - blend_t) + ACCENT_DOT[0] * blend_t)
            g_blend = int(BG_BOT_RIGHT[1] * (1 - blend_t) + ACCENT_DOT[1] * blend_t)
            b_blend = int(BG_BOT_RIGHT[2] * (1 - blend_t) + ACCENT_DOT[2] * blend_t)
            draw.ellipse(
                [cx_dots - r, cy + dy - r, cx_dots + r, cy + dy + r],
                fill=(r_blend, g_blend, b_blend),
            )
        # Punto amber solido
        draw.ellipse(
            [cx_dots - dot_radius, cy + dy - dot_radius,
             cx_dots + dot_radius, cy + dy + dot_radius],
            fill=ACCENT_DOT,
        )
        # Centro blanco brillante (highlight)
        hr = dot_radius * 0.40
        offset = dot_radius * 0.18
        draw.ellipse(
            [cx_dots - hr - offset, cy + dy - hr - offset,
             cx_dots + hr - offset, cy + dy + hr - offset],
            fill=GLYPH_COLOR,
        )

    # 3) Linea fina conectora vertical entre los dots (eje neuronal)
    line_w = max(1, int(stroke * 0.08))
    draw.line(
        [(cx_dots, cy - spacing + dot_radius),
         (cx_dots, cy + spacing - dot_radius)],
        fill=ACCENT_DOT, width=line_w
    )


def _add_top_highlight(img: Image.Image) -> Image.Image:
    """Agrega un brillo radial sutil en la parte superior (efecto glass)."""
    w, h = img.size
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    # Elipse blanca semi-transparente en parte superior
    cx, cy = w / 2, h * 0.18
    rx = w * 0.72
    ry = h * 0.32
    od.ellipse(
        [cx - rx, cy - ry, cx + rx, cy + ry],
        fill=(255, 255, 255, 28)
    )
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=int(w * 0.06)))
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    return Image.alpha_composite(img, overlay)


def _make_icon(size: int, padding_pct: float = 0.0,
               with_round: bool = True) -> Image.Image:
    """Genera el icono cuadrado con todos los efectos."""
    img = _diagonal_gradient(size)
    draw = ImageDraw.Draw(img, 'RGB')
    scale = 1.0 - padding_pct
    _draw_c_monogram(draw, size, scale=scale)
    img = img.filter(ImageFilter.SMOOTH)
    img = _add_top_highlight(img)
    if with_round:
        img = _round_corners(img, radius_pct=0.22)
    return img


def _make_horizontal_logo(width: int = 1400, height: int = 400) -> Image.Image:
    """Logo horizontal con icono + texto CORTEX LABS."""
    icon = _make_icon(height, with_round=True)

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


def _save_svg(path: Path):
    """Guarda version SVG vectorial del logo (Cortex Labs v2 — C estilizada)."""
    # cx=256, cy=256, R=174, stroke=44
    # Arc de 65° a 295° (corte de 130° a la derecha, centrado en este)
    # En SVG: 0°=Este, 90°=Sur (positivo Y va hacia abajo).
    # Punto inicio (65°): cx + R*cos(65°), cy + R*sin(65°)
    # Punto fin (295°)  : cx + R*cos(295°), cy + R*sin(295°)
    import math as _m
    cx, cy, R = 256, 256, 174
    a1 = _m.radians(65)
    a2 = _m.radians(295)
    x1, y1 = cx + R * _m.cos(a1), cy + R * _m.sin(a1)
    x2, y2 = cx + R * _m.cos(a2), cy + R * _m.sin(a2)
    # large-arc-flag = 1 (>180°), sweep-flag = 0 (sentido antihorario en SVG
    # porque queremos ir desde abajo-derecha por la izquierda hasta arriba-derecha)
    arc_d = (
        f"M {x1:.1f} {y1:.1f} "
        f"A {R} {R} 0 1 0 {x2:.1f} {y2:.1f}"
    )
    # Posiciones de los 3 dots (justo a la derecha, en el corte)
    dot_x = cx + R * 0.55
    dot_spacing = 56
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="cxBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#7c3aed"/>
      <stop offset="100%" stop-color="#2c1366"/>
    </linearGradient>
    <radialGradient id="cxHl" cx="50%" cy="20%" r="55%">
      <stop offset="0%" stop-color="white" stop-opacity="0.20"/>
      <stop offset="100%" stop-color="white" stop-opacity="0"/>
    </radialGradient>
    <filter id="cxGlow" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="5"/>
    </filter>
  </defs>
  <rect width="512" height="512" rx="112" fill="url(#cxBg)"/>
  <rect width="512" height="512" rx="112" fill="url(#cxHl)"/>
  <path d="{arc_d}" stroke="white" stroke-width="44" fill="none" stroke-linecap="round"/>
  <g>
    <circle cx="{dot_x}" cy="{cy - dot_spacing}" r="22" fill="#fbbf24" opacity="0.45" filter="url(#cxGlow)"/>
    <circle cx="{dot_x}" cy="{cy}" r="22" fill="#fbbf24" opacity="0.45" filter="url(#cxGlow)"/>
    <circle cx="{dot_x}" cy="{cy + dot_spacing}" r="22" fill="#fbbf24" opacity="0.45" filter="url(#cxGlow)"/>
    <line x1="{dot_x}" y1="{cy - dot_spacing + 13}" x2="{dot_x}" y2="{cy + dot_spacing - 13}" stroke="#fbbf24" stroke-width="3" stroke-linecap="round" opacity="0.7"/>
    <circle cx="{dot_x}" cy="{cy - dot_spacing}" r="13" fill="#fbbf24"/>
    <circle cx="{dot_x}" cy="{cy}" r="13" fill="#fbbf24"/>
    <circle cx="{dot_x}" cy="{cy + dot_spacing}" r="13" fill="#fbbf24"/>
    <circle cx="{dot_x - 2.5}" cy="{cy - dot_spacing - 2.5}" r="5" fill="white"/>
    <circle cx="{dot_x - 2.5}" cy="{cy - 2.5}" r="5" fill="white"/>
    <circle cx="{dot_x - 2.5}" cy="{cy + dot_spacing - 2.5}" r="5" fill="white"/>
  </g>
</svg>'''
    path.write_text(svg, encoding='utf-8')


# ===================== Main =====================

if __name__ == '__main__':
    base = Path(__file__).parent
    icons_dir = base / 'api' / 'static' / 'icons'
    icons_dir.mkdir(parents=True, exist_ok=True)
    static_dir = base / 'api' / 'static'

    print('Generating Cortex Labs v2 logos...')

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

    # Maskable 512 (con padding 18% para safe zone Android)
    img_mask = _make_icon(512, padding_pct=0.18, with_round=False)
    img_mask.save(icons_dir / 'icon-maskable-512.png', 'PNG')
    print('  icon-maskable-512.png')

    # Apple touch icon (180)
    img_180 = _make_icon(180)
    img_180.save(icons_dir / 'apple-touch-icon-180.png', 'PNG')
    print('  apple-touch-icon-180.png')

    # Favicon 32 (browser tab) — sin esquinas redondas para max nitidez
    img_32 = _make_icon(32, with_round=False)
    img_32.save(icons_dir / 'favicon-32.png', 'PNG')
    img_32.save(static_dir / 'favicon.ico', format='ICO')
    print('  favicon-32.png + favicon.ico')

    # Logo horizontal (para login + headers especiales)
    horiz = _make_horizontal_logo()
    horiz.save(static_dir / 'cortex_logo_horizontal.png', 'PNG')
    print('  cortex_logo_horizontal.png')

    # SVG vectorial
    _save_svg(static_dir / 'cortex_logo.svg')
    print('  cortex_logo.svg')

    print('\nDone. Icons in:', icons_dir)
