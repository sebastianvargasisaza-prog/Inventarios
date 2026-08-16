"""Dos scripts de la misma página no pueden definir la misma función (16-ago-2026).

Encontrado revisando Planta paso por paso, antes de cerrar el módulo.

El widget del chat y el de la campana se cargan JUNTOS en las ocho pantallas principales, y
los dos definían `checkUnread`, `_tiempoRel` y `_esc`. Dos `function X` con el mismo nombre
no dan error: **gana la última**, en silencio (M120/M204). Y la última era la de la campana,
porque carga después. Consecuencias, las dos invisibles desde el servidor:

  · el chat pedía refrescar su globo cada 12 segundos y lo que corría era la función de la
    campana, así que `cw-badge` -- el contador de mensajes sin leer -- **no se pintaba
    nunca**: alguien con mensajes nuevos no los veía;
  · y la campana quedaba consultándose el doble (los 12 s del chat más sus propios 25 s),
    tráfico de más contra los tres workers (M43).

La regla es la de siempre: **un componente prefija SUS funciones con su propio prefijo**, el
mismo que ya usan sus ids (`cw-`, `nw-`). Así ninguno depende del orden de carga.

⚠ Esto estuvo a la vista mucho tiempo y ningún test lo veía, porque los guards miraban el
HTML de cada pantalla y estas funciones viven en scripts EXTERNOS (M166). Este recorre lo que
el navegador realmente carga.
"""
import re

import pytest

from .conftest import TEST_PASSWORD, csrf_headers

# Las pantallas que cargan los dos widgets a la vez.
PANTALLAS = ["/inventarios", "/compras", "/calidad", "/aseguramiento", "/hoy", "/marketing"]


def _cli(app, usuario="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _piezas(c, ruta):
    """Cada trozo de JS que la página carga, por separado, para saber QUIÉN define qué."""
    html = c.get(ruta).data.decode("utf-8", "replace")
    piezas = {"(inline)": "\n".join(
        re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S))}
    for src in re.findall(r'<script[^>]*\bsrc="([^"]+)"', html):
        if src.startswith("http") or src.startswith("//"):
            continue
        r = c.get(src)
        if r.status_code == 200:
            piezas[src.split("?")[0]] = r.data.decode("utf-8", "replace")
    return piezas


def _funciones(js):
    return set(re.findall(r'function\s+([A-Za-z_$][\w$]*)\s*\(', js))


def test_los_dos_widgets_no_definen_las_mismas_funciones(app):
    """El caso concreto: chat y campana conviven en toda la app."""
    c = _cli(app)
    chat = c.get("/api/chat/widget.js")
    notif = c.get("/api/notif/widget.js")
    assert chat.status_code == 200 and notif.status_code == 200
    f_chat = _funciones(chat.data.decode("utf-8", "replace"))
    f_notif = _funciones(notif.data.decode("utf-8", "replace"))
    chocan = sorted(f_chat & f_notif)
    assert not chocan, (
        "el chat y la campana definen las mismas funciones y una pisa a la otra: %s "
        "· cada widget prefija las suyas (cw / nw)" % chocan)


def test_cada_widget_conserva_lo_suyo(app):
    """El borde que evita que el arreglo rompa lo que venía a proteger (M96).

    Renombrar es barato de hacer mal: si una llamada se queda con el nombre viejo, el widget
    deja de funcionar sin dar error.
    """
    c = _cli(app)
    for src, fn, badge, endpoint in (
            ("/api/chat/widget.js", "cwCheckUnread", "cw-badge", "/api/chat/unread-summary"),
            ("/api/notif/widget.js", "nwCheckUnread", "nw-badge", "/api/notif/unread-count")):
        cod = c.get(src).data.decode("utf-8", "replace")
        assert len(re.findall(r"function\s+%s\s*\(" % fn, cod)) == 1, (
            "%s no define %s" % (src, fn))
        # la define Y la usa (el temporizador y el refresco tras leer)
        usos = len(re.findall(r"(?<![\w$.])%s\s*[\(,]" % fn, cod)) - 1
        assert usos >= 1, "%s define %s y no la llama: el globo no se refrescaría" % (src, fn)
        assert badge in cod, "%s dejó de pintar %s" % (src, badge)
        assert endpoint in cod, "%s dejó de consultar %s" % (src, endpoint)


def test_ninguna_funcion_se_define_dos_veces_en_una_pantalla(app):
    """El guard general: cualquier par de piezas de la misma página que choque.

    Se mira lo que el navegador CARGA (inline + cada script externo), no el template: estas
    colisiones viven justo entre archivos distintos, que es donde nadie miraba (M166).
    """
    c = _cli(app)
    problemas = []
    for ruta in PANTALLAS:
        piezas = _piezas(c, ruta)
        vistas = {}
        for nombre, js in piezas.items():
            for fn in _funciones(js):
                if fn in vistas and vistas[fn] != nombre:
                    problemas.append("%s: %s la definen %s y %s"
                                     % (ruta, fn, vistas[fn], nombre))
                vistas.setdefault(fn, nombre)
    assert not problemas, "funciones pisadas entre scripts de la misma pantalla:\n  %s" % (
        "\n  ".join(problemas[:12]))
