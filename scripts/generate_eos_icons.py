# -*- coding: utf-8 -*-
"""
Genera todos los iconos PNG de EOS (punto + eco) para PWA + favicon.

El logo es: círculo sólido (sol) sobre dos arcos descendentes (eco/ondas).
viewBox base 0 0 32 32 — escalable a cualquier tamaño.

Genera:
    icon-192.png        — Android home (regular)
    icon-512.png        — Android splash + iOS
    icon-maskable-512.png — Android adaptive (con padding 20% safe zone)
    icon-1024.png       — iOS hero / app store
    apple-touch-icon-180.png — iOS home
    favicon-32.png      — favicon navegador

Uso: python scripts/generate_eos_icons.py
"""
import os, sys
from PIL import Image, ImageDraw

# Carpeta destino: api/static/icons/
HERE = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(os.path.dirname(HERE), 'api', 'static', 'icons')
os.makedirs(ICONS_DIR, exist_ok=True)

# Paleta EOS
BG_DARK = (15, 23, 42)        # #0F172A — fondo navy oscuro (premium)
BG_VIOLET = (109, 40, 217)    # #6D28D9 — fondo violeta brand
FG_WHITE = (255, 255, 255)    # blanco logo
TRANSPARENT = (0, 0, 0, 0)


def _bezier_quad(p0, p1, p2, steps=200):
    """Devuelve lista de (x, y) muestreando una curva Bézier cuadrática."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x, y))
    return pts


def _draw_logo(draw, size, fg=FG_WHITE, scale=1.0, offset=(0, 0)):
    """Dibuja el logo EOS centrado en el canvas.

    El SVG original usa viewBox 0..32. Escalamos a `size` con factor `scale`
    (1.0 = ocupa todo, <1 = padding). offset desplaza el centro.
    """
    # Tamaño efectivo del logo dentro del canvas
    eff = size * scale
    pad = (size - eff) / 2
    cx_off = pad + offset[0]
    cy_off = pad + offset[1]

    def to_xy(vx, vy):
        # vx,vy en viewBox 0..32 → coords del canvas
        return (cx_off + vx * eff / 32, cy_off + vy * eff / 32)

    # 1. Círculo sólido (sol) — viewBox cx=16, cy=12, r=3
    cx, cy = to_xy(16, 12)
    r = 3 * eff / 32
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=fg
    )

    # Grosor de los arcos: viewBox usa stroke-width=1.5
    stroke_w = max(2, int(1.5 * eff / 32 * 2.4))  # un poco mas grueso para visibilidad

    # 2. Arco superior (opacity .55) — Q: M 5 19 Q 16 17, 27 19
    pts1 = _bezier_quad(to_xy(5, 19), to_xy(16, 17), to_xy(27, 19))
    arc1_color = tuple(int(c * 0.55 + 255 * 0.45) if i < 3 else c for i, c in enumerate(fg + (255,)))[:3]
    # Dibujar línea conectando puntos
    draw.line(pts1, fill=arc1_color, width=stroke_w, joint='curve')

    # 3. Arco inferior (opacity .25) — M 5 23 Q 16 21, 27 23
    pts2 = _bezier_quad(to_xy(5, 23), to_xy(16, 21), to_xy(27, 23))
    arc2_color = tuple(int(c * 0.25 + 255 * 0.75) if i < 3 else c for i, c in enumerate(fg + (255,)))[:3]
    draw.line(pts2, fill=arc2_color, width=stroke_w, joint='curve')


def _arc_color_alpha(fg, opacity, bg):
    """Mezcla fg con bg según opacity para simular alpha sobre fondo sólido."""
    return tuple(
        int(fg[i] * opacity + bg[i] * (1 - opacity))
        for i in range(3)
    )


def gen_icon_solid(path, size, bg, fg=FG_WHITE, rounded=False, mask_safe=False):
    """Genera PNG con fondo sólido + logo centrado.

    rounded: si True, aplica esquinas redondeadas (típico app icon iOS/Android).
    mask_safe: si True, deja 20% padding alrededor (Android maskable).
    """
    img = Image.new('RGBA', (size, size), TRANSPARENT)
    draw = ImageDraw.Draw(img)

    # Fondo sólido
    if rounded:
        radius = int(size * 0.22)  # iOS ~22% / Android ~24%
        draw.rounded_rectangle([0, 0, size, size], radius=radius, fill=bg)
    else:
        draw.rectangle([0, 0, size, size], fill=bg)

    # Logo centrado — escala según mask_safe
    scale = 0.60 if mask_safe else 0.78
    # Para el logo en este viewBox, el "centro óptico" no es 16,16 — el
    # círculo está arriba (y=12) y los arcos abajo. Compensamos un poco hacia arriba.
    img2 = Image.new('RGBA', (size, size), TRANSPARENT)
    draw2 = ImageDraw.Draw(img2)

    # Calcular colores de arcos pre-mezclados con bg (Pillow line no soporta alpha sobre RGBA con compositing decente para line)
    arc1 = _arc_color_alpha(fg, 0.55, bg)
    arc2 = _arc_color_alpha(fg, 0.25, bg)

    # Re-dibuja con colores pre-mezclados
    eff = size * scale
    pad = (size - eff) / 2
    def to_xy(vx, vy):
        return (pad + vx * eff / 32, pad + vy * eff / 32)

    # Círculo
    cx, cy = to_xy(16, 12)
    r = 3 * eff / 32
    draw2.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fg)

    stroke_w = max(2, int(1.6 * eff / 32 * 2.4))
    pts1 = _bezier_quad(to_xy(5, 19), to_xy(16, 17), to_xy(27, 19))
    draw2.line(pts1, fill=arc1, width=stroke_w, joint='curve')

    pts2 = _bezier_quad(to_xy(5, 23), to_xy(16, 21), to_xy(27, 23))
    draw2.line(pts2, fill=arc2, width=stroke_w, joint='curve')

    # Componer logo sobre fondo redondeado
    img.paste(img2, (0, 0), img2)
    img.save(path, 'PNG', optimize=True)
    print(f'  OK {os.path.basename(path)} ({size}x{size})')


def main():
    print(f'Generando iconos EOS en: {ICONS_DIR}')

    # Android Home / iOS / general PWA — fondo violeta brand, esquinas redondeadas
    gen_icon_solid(os.path.join(ICONS_DIR, 'icon-192.png'),
                   192, BG_VIOLET, rounded=True)
    gen_icon_solid(os.path.join(ICONS_DIR, 'icon-512.png'),
                   512, BG_VIOLET, rounded=True)
    gen_icon_solid(os.path.join(ICONS_DIR, 'icon-1024.png'),
                   1024, BG_VIOLET, rounded=True)

    # Maskable Android — debe llenar el cuadro completo + 20% safe zone
    gen_icon_solid(os.path.join(ICONS_DIR, 'icon-maskable-512.png'),
                   512, BG_VIOLET, rounded=False, mask_safe=True)

    # iOS apple-touch-icon (180x180, sin border-radius — iOS lo agrega)
    gen_icon_solid(os.path.join(ICONS_DIR, 'apple-touch-icon-180.png'),
                   180, BG_VIOLET, rounded=False)

    # Favicon 32x32
    gen_icon_solid(os.path.join(ICONS_DIR, 'favicon-32.png'),
                   32, BG_VIOLET, rounded=False)

    # Favicon ICO (multi-resolución 16+32+48)
    favicon_path = os.path.join(os.path.dirname(ICONS_DIR), 'favicon.ico')
    sizes = [(16, 16), (32, 32), (48, 48)]
    imgs = []
    for sz in sizes:
        img = Image.new('RGBA', sz, TRANSPARENT)
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, sz[0], sz[1]], fill=BG_VIOLET)
        eff = sz[0] * 0.78
        pad = (sz[0] - eff) / 2
        def to_xy(vx, vy, _eff=eff, _pad=pad):
            return (_pad + vx * _eff / 32, _pad + vy * _eff / 32)
        cx, cy = to_xy(16, 12)
        r = max(1, 3 * eff / 32)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=FG_WHITE)
        if sz[0] >= 32:
            arc1 = _arc_color_alpha(FG_WHITE, 0.55, BG_VIOLET)
            arc2 = _arc_color_alpha(FG_WHITE, 0.25, BG_VIOLET)
            stroke_w = max(1, int(1.5 * eff / 32 * 2))
            pts1 = _bezier_quad(to_xy(5, 19), to_xy(16, 17), to_xy(27, 19), steps=80)
            draw.line(pts1, fill=arc1, width=stroke_w, joint='curve')
            pts2 = _bezier_quad(to_xy(5, 23), to_xy(16, 21), to_xy(27, 23), steps=80)
            draw.line(pts2, fill=arc2, width=stroke_w, joint='curve')
        imgs.append(img)
    imgs[0].save(favicon_path, format='ICO', sizes=sizes, append_images=imgs[1:])
    print('  OK favicon.ico (multi-res)')

    print('Listo.')


if __name__ == '__main__':
    main()
