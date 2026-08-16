"""El JS de Compras se sirve aparte y la pantalla sigue completa (15-ago-2026).

Sebastián: *"revisá la velocidad de cada módulo, están lentos en cada cosa cargando y
mostrando"*. Medido: `/compras` servía **685 KB por carga y 551 KB eran JavaScript
incrustado**, que el navegador no puede guardar en caché ni reusar compilado -- se rebajaba
entero cada vez. Planta ya había movido el suyo a `/planta-app.js`; Compras, el módulo que
Catalina usa todo el día, no.

Lo que estos tests protegen es lo que un movimiento de 551 KB puede romper en silencio:

  1. **Que la página siga cargando el archivo.** Si la extracción falla, el fallback deja el
     JS inline y todo funciona -- pero si la página apunta a un archivo que no se sirve, la
     pantalla queda muerta sin un solo error de Python (M164/M197).
  2. **Que no falte ninguna función.** Un botón que llama a algo que ya no existe no da
     error visible: simplemente no hace nada (M112/M146/M166). Se recolectan las funciones
     que los `onclick` del HTML llaman y se exige que estén definidas.
  3. **Que los datos de cada usuario sigan siendo suyos.** Los cuatro valores por request
     salieron a un bloque inline: si se hubieran quedado dentro del archivo cacheado, el
     navegador le serviría a Catalina los permisos del último que cargó -- un error de
     permisos servido desde la caché, invisible desde el servidor.
"""
import re

import pytest

from .conftest import TEST_PASSWORD, csrf_headers


def _cli(app, usuario):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _js_total(c, html):
    """Todo el JS que la pantalla ejecuta: el inline más el archivo externo."""
    js = "\n".join(re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S))
    for src in re.findall(r'<script[^>]*\bsrc="([^"]+)"', html):
        if src.startswith("/compras-app.js"):
            r = c.get(src)
            assert r.status_code == 200, "%s -> %s" % (src, r.status_code)
            js += "\n" + r.data.decode("utf-8", "replace")
    return js


def test_la_pantalla_carga_el_archivo_y_se_sirve(app):
    c = _cli(app, "sebastian")
    html = c.get("/compras").data.decode("utf-8", "replace")
    if 'src="/compras-app.js' not in html:
        pytest.skip("extracción no activa (fallback inline) · la pantalla funciona igual")
    r = c.get("/compras-app.js")
    assert r.status_code == 200
    assert "javascript" in (r.headers.get("Content-Type") or "")
    # cacheable de verdad: sin esto el navegador lo vuelve a bajar y no se gana nada
    assert "immutable" in (r.headers.get("Cache-Control") or ""), r.headers.get("Cache-Control")


def test_ningun_boton_llama_a_una_funcion_que_ya_no_existe(app):
    """El guard que detecta si al mover el JS se perdió código."""
    c = _cli(app, "sebastian")
    html = c.get("/compras").data.decode("utf-8", "replace")
    js = _js_total(c, html)

    definidas = set(re.findall(r'function\s+([A-Za-z_$][\w$]*)\s*\(', js))
    definidas |= set(re.findall(r'(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?function', js))
    definidas |= set(re.findall(r'(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(', js))
    definidas |= set(re.findall(r'window\.([A-Za-z_$][\w$]*)\s*=', js))

    llamadas = set()
    for atrib in re.findall(r'on(?:click|change|input|submit|keyup)="([^"]*)"', html):
        # El lookbehind descarta los MÉTODOS (`el.click()`, `e.preventDefault()`): no son
        # funciones globales y sin esto el guard grita doce falsos positivos, que es como
        # un guard deja de mirarse (M170).
        llamadas |= set(re.findall(r'(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(', atrib))

    # Palabras del lenguaje y funciones del navegador: no las define la pantalla.
    nativas = {"if", "for", "while", "switch", "return", "alert", "confirm", "prompt",
               "parseInt", "parseFloat", "String", "Number", "Boolean", "Array", "Object",
               "JSON", "Math", "Date", "encodeURIComponent", "decodeURIComponent",
               "setTimeout", "setInterval", "fetch", "event", "this",
               "function", "typeof", "new", "catch", "delete", "void"}
    faltan = sorted(f for f in llamadas - definidas - nativas if not f.startswith("_"))
    assert not faltan, ("hay botones llamando a funciones que no están definidas: %s"
                        % ", ".join(faltan[:15]))


def test_los_permisos_de_cada_usuario_no_viajan_en_el_archivo_cacheado(app):
    """Catalina y Sebastián tienen permisos distintos: eso NO puede vivir en un archivo que
    el navegador cachea para todos."""
    cs = _cli(app, "sebastian")
    html_s = cs.get("/compras").data.decode("utf-8", "replace")
    if 'src="/compras-app.js' not in html_s:
        pytest.skip("extracción no activa (fallback inline)")

    bundle = cs.get("/compras-app.js").data.decode("utf-8", "replace")
    for marca in ("{usuario}", "{es_admin}", "{es_contadora}", "{es_autorizador}"):
        assert marca not in bundle, "%s quedó dentro del archivo cacheado" % marca

    cc = _cli(app, "catalina")
    html_c = cc.get("/compras").data.decode("utf-8", "replace")
    # el bloque inline de cada uno declara SUS valores
    def _val(h, var):
        m = re.search(r'window\.%s\s*=\s*([^;]+);' % var, h)
        return (m.group(1).strip() if m else None)
    # La ruta inyecta `username.capitalize()`, que es exactamente el valor que este JS
    # recibía ANTES del cambio (lo usa como `creado_por`): se compara contra eso, no contra
    # el username, o el test estaría exigiendo un comportamiento que nunca existió.
    assert _val(html_s, "_CP_USER") == '"Sebastian"', _val(html_s, "_CP_USER")
    assert _val(html_c, "_CP_USER") == '"Catalina"', _val(html_c, "_CP_USER")
    # y el permiso de autorizar no puede ser el mismo texto sin resolver
    for h in (html_s, html_c):
        assert "{es_autorizador}" not in h, "quedó un permiso sin resolver en el HTML"


def test_las_cuatro_pantallas_sirven_su_bundle(app):
    """Las otras tres que se movieron el mismo día (Calidad, Aseguramiento, Marketing).

    El error que este guard existe para cazar ya ocurrió: el script generó la constante con
    otro nombre (`CALIDAD_HTML_APP_JS` en vez de `CALIDAD_APP_JS`), así que la página
    enlazaba un archivo que la ruta no sabía servir -- 404, y la pantalla se quedaba SIN su
    JavaScript. Del lado del servidor no se ve nada: la página responde 200.
    """
    c = _cli(app, "sebastian")
    for ruta, bundle in (("/calidad", "/calidad-app.js"),
                         ("/aseguramiento", "/aseguramiento-app.js"),
                         ("/marketing", "/marketing-app.js")):
        html = c.get(ruta).data.decode("utf-8", "replace")
        if ('src="%s' % bundle) not in html:
            continue          # fallback inline: la pantalla funciona igual
        r = c.get(bundle)
        assert r.status_code == 200, (
            "%s enlaza %s y esa ruta responde %s: la pantalla se queda sin JS"
            % (ruta, bundle, r.status_code))
        assert len(r.data) > 50000, "%s vino casi vacío (%d bytes)" % (bundle, len(r.data))
        assert "immutable" in (r.headers.get("Cache-Control") or ""), (
            "%s no se cachea, que es la razón de haberlo movido" % bundle)


def test_la_pagina_pesa_mucho_menos(app):
    """La razón por la que se hizo: lo que baja el navegador en cada carga."""
    c = _cli(app, "sebastian")
    html = c.get("/compras").data.decode("utf-8", "replace")
    if 'src="/compras-app.js' not in html:
        pytest.skip("extracción no activa (fallback inline)")
    kb = len(html.encode("utf-8")) / 1024.0
    # antes eran ~685 KB; el techo deja margen sin dejar de morder si el JS vuelve al HTML
    assert kb < 250, "la página de Compras sigue pesando %.0f KB" % kb
