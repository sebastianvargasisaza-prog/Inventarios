"""ui_help · Sistema de tooltips premium global para EOS.

Sebastián 5-jun-2026: "que cada botón diga para qué sirve". Un solo CSS para
TODA la app. Convención:

    <button data-tip="Lo que hace este botón">…</button>

Cualquier elemento con atributo ``data-tip`` muestra una burbuja elegante al
pasar el mouse (hover) y al recibir foco (tab / tap en móvil). Variantes de
posición opcionales por si el botón está pegado a un borde:

    data-tip-pos="bottom"   → abre hacia abajo (botones del tope de la pantalla)
    class="tip-r"           → alinea a la derecha (botones de columna Acciones)
    class="tip-l"           → alinea a la izquierda

Uso en una plantilla server-side:

    from templates_py.ui_help import TOOLTIP_CSS
    html = f"<style>{TOOLTIP_CSS}</style>" + resto_de_la_pagina

o, si la página ya tiene un bloque <style>, pegar TOOLTIP_CSS dentro de él.
"""

# CSS puro · no depende de JS. ::after = burbuja, ::before = flechita.
TOOLTIP_CSS = """
/* ── Tooltips premium EOS (data-tip) ───────────────────────────────── */
[data-tip]{position:relative}
[data-tip]::after{
  content:attr(data-tip);
  position:absolute; left:50%; bottom:calc(100% + 9px);
  transform:translateX(-50%) translateY(4px);
  background:#1e293b; color:#fff; text-align:left;
  padding:8px 12px; border-radius:9px;
  font-size:12px; font-weight:600; line-height:1.4; letter-spacing:.1px;
  white-space:normal; width:max-content; max-width:260px;
  box-shadow:0 8px 24px rgba(15,23,42,.28);
  opacity:0; visibility:hidden; pointer-events:none;
  transition:opacity .14s ease, transform .14s ease, visibility .14s;
  z-index:99999;
}
[data-tip]::before{
  content:''; position:absolute; left:50%; bottom:calc(100% + 3px);
  transform:translateX(-50%);
  border:6px solid transparent; border-top-color:#1e293b;
  opacity:0; visibility:hidden;
  transition:opacity .14s ease, visibility .14s;
  z-index:99999;
}
[data-tip]:hover::after,[data-tip]:focus::after,[data-tip]:focus-within::after{
  opacity:1; visibility:visible; transform:translateX(-50%) translateY(0);
}
[data-tip]:hover::before,[data-tip]:focus::before,[data-tip]:focus-within::before{
  opacity:1; visibility:visible;
}
/* Alineaciones para bordes (evitan que la burbuja se salga de pantalla) */
[data-tip].tip-r::after{left:auto; right:0; transform:translateX(0) translateY(4px)}
[data-tip].tip-r:hover::after,[data-tip].tip-r:focus::after{transform:translateX(0) translateY(0)}
[data-tip].tip-l::after{left:0; right:auto; transform:translateX(0) translateY(4px)}
[data-tip].tip-l:hover::after,[data-tip].tip-l:focus::after{transform:translateX(0) translateY(0)}
/* Abrir hacia abajo (para botones del tope) */
[data-tip][data-tip-pos="bottom"]::after{
  bottom:auto; top:calc(100% + 9px); transform:translateX(-50%) translateY(-4px);
}
[data-tip][data-tip-pos="bottom"]::before{
  bottom:auto; top:calc(100% + 3px);
  border-top-color:transparent; border-bottom-color:#1e293b;
}
[data-tip][data-tip-pos="bottom"]:hover::after,[data-tip][data-tip-pos="bottom"]:focus::after{
  transform:translateX(-50%) translateY(0);
}
@media (max-width:640px){ [data-tip]::after{max-width:200px; font-size:11.5px} }
"""


def tooltip_css() -> str:
    """Devuelve el bloque <style> listo para inyectar en una página."""
    return f"<style>{TOOLTIP_CSS}</style>"
