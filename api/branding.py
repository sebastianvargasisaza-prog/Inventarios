# -*- coding: utf-8 -*-
"""
Branding centralizado de la aplicacion.

Para cambiar el nombre del producto, modificar SOLO este archivo.

Producto:  EOS  (diosa griega de la aurora — primer rayo)
Compania:  HHA Group  (Hermes · Hefesto · Asclepio)
Tagline:   Todo el holding, al frente

Renombrado 28-abr-2026: era "Cortex Labs", Alejandro pidio nombre mitologico
griego (en linea con HHA, Espagiria, ANIMUS, ANIMA, Persefone).
"""

# ===================== Identidad de producto =====================

PRODUCT_NAME       = "EOS"
PRODUCT_NAME_SHORT = "EOS"
PRODUCT_TAGLINE    = "Todo el holding, al frente"

# ===================== Compania =====================

COMPANY_NAME       = "HHA Group"
COMPANY_LEGAL      = "HHA Group S.A.S."
COMPANY_TAGLINE    = "Espagiria & ANIMUS Lab"
COMPANY_URL        = "https://hhagroup.co"

# ===================== Atribucion =====================

POWERED_BY         = "Desarrollado por HHA Group"
POWERED_BY_SHORT   = "by HHA Group"
COPYRIGHT_LINE     = f"© 2026 {COMPANY_LEGAL} — Todos los derechos reservados"

# ===================== Version =====================

VERSION            = "1.0.0"
VERSION_LABEL      = "EOS v1.0 · Edicion Espagiria"

# ===================== Color brand =====================
# Mantenemos #6d28d9 como acento primario para no repintar toda la UI.
# La paleta EOS completa esta documentada en /static/cortex.css.

BRAND_PRIMARY      = "#6d28d9"   # violeta — acentos, links, botones primarios
BRAND_AURORA       = "#FF8E72"   # coral — alertas suaves, highlights
BRAND_GOLD         = "#FFCB77"   # dorado — acentos celebracion / KPI
BRAND_NIGHT        = "#0A0A0B"   # noche — fondo oscuro

# ===================== Logo SVG inline (concepto: punto + eco) =====================
# Punto solido (sol/dato) sobre dos arcos descendentes (ondas / eco / propagacion).
# Aurora literal: el sol asomando, irradiando. Usa currentColor para heredar
# el color del contenedor — un solo SVG sirve para dark y light.
#
# viewBox 0 0 32 32 — escalable de 16px (favicon) a 200px (hero) sin perdida.

LOGO_SVG = (
    '<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" '
    'fill="none" stroke="currentColor">'
    '<circle cx="16" cy="12" r="3" fill="currentColor" stroke="none"/>'
    '<path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" '
    'stroke-linecap="round" opacity=".55"/>'
    '<path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" '
    'stroke-linecap="round" opacity=".25"/>'
    '</svg>'
)


def logo_svg(size: int = 32, color: str = "currentColor") -> str:
    """Logo EOS inline como SVG. Escala libre, color heredable."""
    return (
        f'<svg viewBox="0 0 32 32" width="{size}" height="{size}" '
        f'xmlns="http://www.w3.org/2000/svg" fill="none" stroke="{color}" '
        f'class="eos-logo">'
        f'<circle cx="16" cy="12" r="3" fill="{color}" stroke="none"/>'
        f'<path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" '
        f'stroke-linecap="round" opacity=".55"/>'
        f'<path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" '
        f'stroke-linecap="round" opacity=".25"/>'
        f'</svg>'
    )


# ===================== Helpers de presentacion =====================

def page_title(modulo: str = "") -> str:
    """Devuelve un <title> consistente para cada pagina."""
    if modulo:
        return f"{PRODUCT_NAME} — {modulo}"
    return f"{PRODUCT_NAME} · {COMPANY_NAME}"


def header_html(scale: str = "default") -> str:
    """
    HTML del header con branding completo.

    scale='compact'  -> solo nombre de producto + by HHA
    scale='default'  -> producto + tagline pequeno + by HHA
    scale='hero'     -> banner grande para login/home
    """
    if scale == "compact":
        return (
            f'<div class="brand-header" style="display:flex;align-items:center;gap:10px">'
            f'<span style="color:{BRAND_PRIMARY};display:inline-flex;">{logo_svg(20, BRAND_PRIMARY)}</span>'
            f'<span class="brand-name" style="font-weight:700;font-size:18px;color:{BRAND_PRIMARY};letter-spacing:3px">{PRODUCT_NAME}</span>'
            f'<span class="brand-by" style="font-size:11px;color:#78716c;font-weight:500">{POWERED_BY_SHORT}</span>'
            f'</div>'
        )
    if scale == "hero":
        return (
            f'<div class="brand-hero" style="text-align:center;padding:24px 0">'
            f'<div style="color:{BRAND_PRIMARY};display:flex;justify-content:center;margin-bottom:12px;">{logo_svg(72, BRAND_PRIMARY)}</div>'
            f'<div style="font-size:34px;font-weight:300;color:{BRAND_PRIMARY};letter-spacing:8px">{PRODUCT_NAME}</div>'
            f'<div style="font-size:13px;color:#57534e;margin-top:6px;font-style:italic">{PRODUCT_TAGLINE}</div>'
            f'<div style="font-size:11px;color:#a8a29e;margin-top:14px;letter-spacing:1px;text-transform:uppercase">{POWERED_BY}</div>'
            f'</div>'
        )
    # default
    return (
        f'<div class="brand-header" style="display:flex;align-items:center;gap:10px">'
        f'<span style="color:{BRAND_PRIMARY};display:inline-flex;">{logo_svg(22, BRAND_PRIMARY)}</span>'
        f'<span class="brand-name" style="font-weight:700;font-size:20px;color:{BRAND_PRIMARY};letter-spacing:4px">{PRODUCT_NAME}</span>'
        f'<span class="brand-tagline" style="font-size:11px;color:#a8a29e;font-style:italic">{PRODUCT_TAGLINE}</span>'
        f'<span class="brand-by" style="margin-left:auto;font-size:11px;color:#78716c;font-weight:500">{POWERED_BY_SHORT}</span>'
        f'</div>'
    )


def footer_html() -> str:
    """Footer minimalista para usar en todas las paginas."""
    return (
        f'<footer class="brand-footer" style="padding:16px 20px;border-top:1px solid #e7e5e4;'
        f'margin-top:32px;text-align:center;font-size:11px;color:#a8a29e">'
        f'<div><strong style="color:{BRAND_PRIMARY};letter-spacing:3px">{PRODUCT_NAME}</strong> {VERSION_LABEL.split("·")[1].strip() if "·" in VERSION_LABEL else "v" + VERSION}</div>'
        f'<div style="margin-top:4px">{COPYRIGHT_LINE}</div>'
        f'<div style="margin-top:2px">{POWERED_BY}</div>'
        f'</footer>'
    )


def meta_tags_html() -> str:
    """Meta tags para <head> consistentes en toda la app."""
    return (
        f'<meta name="application-name" content="{PRODUCT_NAME}">'
        f'<meta name="apple-mobile-web-app-title" content="{PRODUCT_NAME}">'
        f'<meta name="apple-mobile-web-app-capable" content="yes">'
        f'<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
        f'<meta name="mobile-web-app-capable" content="yes">'
        f'<meta name="theme-color" content="{BRAND_PRIMARY}">'
        f'<meta name="description" content="{PRODUCT_NAME} · {PRODUCT_TAGLINE}">'
        f'<meta name="author" content="{COMPANY_NAME}">'
    )


# ===================== Iconos SVG (Heroicons line-style) =====================
# Reutilizables en cualquier template para tener consistencia visual.
# Uso: branding.icon('planta', size=32, color='#6d28d9')

_SVG_ICONS = {
    'hoy':         '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/>',
    'gerencia':    '<path d="M3 9l9-6 9 6"/><path d="M5 21V11M19 21V11M9 21v-8M15 21v-8M2 21h20"/>',
    'planta':      '<path d="M21 7.5l-9-5-9 5 9 5z"/><path d="M3 7.5v9l9 5 9-5v-9M12 12.5v9"/>',
    'calidad':     '<path d="M9 3h6M10 3v6.5L4 19a2 2 0 001.7 3h12.6a2 2 0 001.7-3l-6-9.5V3"/><path d="M6 14h12"/>',
    'tecnica':     '<path d="M14.7 6.3a4 4 0 005.7-5.7L18 3l-2-1-1-2-2.6 2.6a4 4 0 005.3 5.4z"/><path d="M14 9 4 19l3 3 10-10"/>',
    'compras':     '<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M2 3h2l3 13h12l3-9H6"/>',
    'solicitudes': '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M9 13h6M9 17h6M9 9h2"/>',
    'clientes':    '<path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 00-3-3.9M16 3.1a4 4 0 010 7.8"/>',
    'marketing':   '<path d="M3 11v3a1 1 0 001 1h2.5l8 5V5l-8 5H4a1 1 0 00-1 1z"/><path d="M19 12a4 4 0 000-5.7"/>',
    'animus':      '<path d="M12 3l1.9 5.4L19 10l-5.1 1.6L12 17l-1.9-5.4L5 10l5.1-1.6L12 3z"/><path d="M19 17l.6 1.7L21 19l-1.4.3L19 21l-.6-1.7L17 19l1.4-.3z"/>',
    'espagiria':   '<path d="M12 21V8M12 8c-3 0-6-2-6-5 3 0 6 2 6 5z"/><path d="M12 8c3 0 6-2 6-5-3 0-6 2-6 5zM8 14c-2 0-4-1-4-3 2 0 4 1 4 3zM16 14c2 0 4-1 4-3-2 0-4 1-4 3z"/>',
    'tesoreria':   '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M6 12h.01M18 12h.01"/>',
    'rrhh':        '<path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.9M16 3.1a4 4 0 010 7.8"/>',
    'compromisos': '<path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="9"/>',
    'recepcion':   '<path d="M14 18V6a2 2 0 00-2-2H4a2 2 0 00-2 2v11a1 1 0 001 1h2"/><path d="M15 18h-3M22 18h-2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/><path d="M14 9h3l3 4v5h-2"/>',
    'maquila':     '<path d="M9 3v6L4 18a2 2 0 001.7 3h12.6a2 2 0 001.7-3l-5-9V3"/><path d="M9 3h6"/>',
    'dashboard':   '<rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/>',
    'bodega':      '<path d="M3 7l9-4 9 4-9 4-9-4z"/><path d="M3 7v10l9 4 9-4V7"/>',
    'produccion':  '<path d="M2 22h20M4 22V8l5 3V8l5 3V8l6 4v10"/>',
    'programacion':'<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    'modulos':     '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>',
    'volver':      '<path d="M19 12H5M12 19l-7-7 7-7"/>',
    'logout':      '<path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/>',
    'config':      '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09A1.65 1.65 0 008 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H2a2 2 0 110-4h.09A1.65 1.65 0 004.6 8a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V2a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H22a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1z"/>',
    'campana':     '<path d="M18 8a6 6 0 00-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 01-3.4 0"/>',
    'lupa':        '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    # Logo EOS como icono usable (concepto C: punto + eco)
    'eos':         '<circle cx="16" cy="12" r="3" fill="currentColor"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/>',
}


def icon(name: str, size: int = 24, color: str = "currentColor",
         stroke_width: float = 1.6, css_class: str = "cx-ico") -> str:
    """Devuelve un <svg>...</svg> inline con el icono pedido.

    Si name no existe, retorna un placeholder de cuadrado.

    Args:
        name: clave del icono (ver _SVG_ICONS)
        size: tamanio en px (width=height)
        color: color del trazo (ej '#6d28d9' o 'currentColor')
        stroke_width: grosor del trazo
        css_class: clase CSS para el SVG
    """
    paths = _SVG_ICONS.get(name)
    if not paths:
        paths = '<rect x="4" y="4" width="16" height="16" rx="2"/>'
    # El icono 'eos' usa viewBox 0 0 32 32, los demas 0 0 24 24
    viewbox = "0 0 32 32" if name == 'eos' else "0 0 24 24"
    return (
        f'<svg viewBox="{viewbox}" width="{size}" height="{size}" '
        f'fill="none" stroke="{color}" stroke-width="{stroke_width}" '
        f'stroke-linecap="round" stroke-linejoin="round" class="{css_class}">'
        f'{paths}</svg>'
    )


def list_icons() -> list:
    """Lista los iconos disponibles."""
    return sorted(_SVG_ICONS.keys())


# ===================== Header de modulo unificado =====================

def module_header(modulo: str, subtitulo: str = "",
                  icon_name: str = None,
                  back_url: str = "/modulos",
                  with_dark_toggle: bool = True) -> str:
    """Devuelve el HTML completo de un header de modulo EOS.

    Args:
        modulo: nombre del modulo (ej "Planta", "Compras", "Calidad")
        subtitulo: descripcion (ej "stock · lotes · trazabilidad")
        icon_name: clave de icono (ver list_icons()). Si None, usa el logo EOS.
        back_url: a donde lleva el boton "Modulos"
        with_dark_toggle: incluye boton de toggle dark mode

    Genera estructura:
        <header class="cx-mod-header">
          <SVG logo EOS />
          <div>
            <div title>Modulo</div>
            <div sub>by HHA Group · subtitulo</div>
          </div>
          <nav>
            [icono volver] Módulos
            [icono dark mode]
          </nav>
        </header>
    """
    # Logo EOS inline (SVG, escala desde 32px). Reemplaza la imagen PNG anterior.
    logo_html = (
        f'<span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;'
        f'color:{BRAND_PRIMARY};">'
        f'{logo_svg(38, BRAND_PRIMARY)}'
        f'</span>'
    )

    # Icono opcional al lado del nombre del modulo (en violeta)
    icon_inline = ""
    if icon_name:
        icon_inline = (
            f'<span style="display:inline-flex;vertical-align:middle;color:{BRAND_PRIMARY};'
            f'margin-right:8px;">{icon(icon_name, size=22)}</span>'
        )

    nav_buttons = (
        f'<a href="{back_url}" class="cx-btn cx-btn-ghost cx-btn-sm" '
        f'title="Volver a Modulos">{icon("modulos", size=14)} Modulos</a>'
    )
    if with_dark_toggle:
        nav_buttons += (
            f'<button class="cx-theme-toggle" onclick="cxToggleTheme()" '
            f'title="Modo claro/oscuro" id="cx-theme-btn">'
            f'<span id="cx-theme-icon">{icon("config", size=18)}</span>'
            f'</button>'
        )

    return (
        f'<header class="cx-mod-header">'
        f'{logo_html}'
        f'<div>'
        f'<div class="cx-mod-header__title">{icon_inline}{modulo}</div>'
        f'<div class="cx-mod-header__sub">'
        f'<strong style="letter-spacing:3px">{PRODUCT_NAME}</strong> &middot; by HHA Group'
        + (f' &middot; {subtitulo}' if subtitulo else '')
        + f'</div>'
        f'</div>'
        f'<div class="cx-mod-header__nav">{nav_buttons}</div>'
        f'</header>'
    )


def dark_mode_script() -> str:
    """Script JS minimo para toggle de dark mode (persistente en localStorage)."""
    return '''<script>
function cxToggleTheme(){
  var html = document.documentElement;
  var current = html.getAttribute("data-theme");
  var next = current === "dark" ? "light" : "dark";
  if (next === "dark") html.setAttribute("data-theme","dark");
  else html.removeAttribute("data-theme");
  try { localStorage.setItem("cx-theme", next); } catch(e){}
}
</script>'''


def context_dict() -> dict:
    """Diccionario para inyectar en templates Jinja-like si se necesitara."""
    return {
        "product_name":      PRODUCT_NAME,
        "product_short":     PRODUCT_NAME_SHORT,
        "tagline":           PRODUCT_TAGLINE,
        "company":           COMPANY_NAME,
        "company_legal":     COMPANY_LEGAL,
        "powered_by":        POWERED_BY,
        "powered_by_short":  POWERED_BY_SHORT,
        "version":           VERSION,
        "version_label":     VERSION_LABEL,
        "copyright":         COPYRIGHT_LINE,
        "logo_svg":          LOGO_SVG,
        "brand_primary":     BRAND_PRIMARY,
    }
