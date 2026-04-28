# -*- coding: utf-8 -*-
"""
Branding centralizado de la aplicacion.

Para cambiar el nombre del producto, modificar SOLO este archivo.

Producto:  Cortex Labs
Compania:  HHA Group
Tagline:   El cerebro operativo de tu laboratorio
"""

# ===================== Identidad de producto =====================

PRODUCT_NAME       = "Cortex Labs"
PRODUCT_NAME_SHORT = "Cortex"
PRODUCT_TAGLINE    = "El cerebro operativo de tu laboratorio"

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
VERSION_LABEL      = "Cortex Labs v1.0 · Edicion Espagiria"

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
            f'<span class="brand-name" style="font-weight:700;font-size:18px;color:#6d28d9">{PRODUCT_NAME}</span>'
            f'<span class="brand-by" style="font-size:11px;color:#78716c;font-weight:500">{POWERED_BY_SHORT}</span>'
            f'</div>'
        )
    if scale == "hero":
        return (
            f'<div class="brand-hero" style="text-align:center;padding:24px 0">'
            f'<div style="font-size:34px;font-weight:800;color:#6d28d9;letter-spacing:-1px">{PRODUCT_NAME}</div>'
            f'<div style="font-size:13px;color:#57534e;margin-top:6px;font-style:italic">{PRODUCT_TAGLINE}</div>'
            f'<div style="font-size:11px;color:#a8a29e;margin-top:14px;letter-spacing:1px;text-transform:uppercase">{POWERED_BY}</div>'
            f'</div>'
        )
    # default
    return (
        f'<div class="brand-header" style="display:flex;align-items:baseline;gap:8px">'
        f'<span class="brand-name" style="font-weight:700;font-size:20px;color:#6d28d9;letter-spacing:-0.3px">{PRODUCT_NAME}</span>'
        f'<span class="brand-tagline" style="font-size:11px;color:#a8a29e;font-style:italic">{PRODUCT_TAGLINE}</span>'
        f'<span class="brand-by" style="margin-left:auto;font-size:11px;color:#78716c;font-weight:500">{POWERED_BY_SHORT}</span>'
        f'</div>'
    )


def footer_html() -> str:
    """Footer minimalista para usar en todas las paginas."""
    return (
        f'<footer class="brand-footer" style="padding:16px 20px;border-top:1px solid #e7e5e4;'
        f'margin-top:32px;text-align:center;font-size:11px;color:#a8a29e">'
        f'<div><strong style="color:#6d28d9">{PRODUCT_NAME}</strong> {VERSION_LABEL.split("·")[1].strip() if "·" in VERSION_LABEL else "v" + VERSION}</div>'
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
        f'<meta name="theme-color" content="#6d28d9">'
        f'<meta name="description" content="{PRODUCT_NAME} · {PRODUCT_TAGLINE}">'
        f'<meta name="author" content="{COMPANY_NAME}">'
    )


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
    }
