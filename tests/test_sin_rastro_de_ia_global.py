# -*- coding: utf-8 -*-
"""Regla 0, medida en TODAS las pantallas grandes y no en tres sueltas.

Sebastián lo pide desde hace meses: *cero rastro de IA*, y el em-dash `—` es el delator. Había
guards para ÁNIMUS, el calendario y calibración... y **ninguno para Planta, Calidad, Compras ni
el CEO**, que son los módulos que se usan todos los días. Una regla global con medición parcial
es una intención (M104: lo mismo pasó con los tokens de color, 8.077 veces).

Se mide sobre lo que el navegador RECIBE, no sobre el fuente:

  · los `—` de comentarios y docstrings son invisibles y no son rastro de nada (M86);
  · y lo que importa es lo que la persona lee, que puede venir de un bundle o de una inyección
    (M158/M166: leer el literal del fuente no ve nada de lo que se inyecta después).

⚠ Es un TRINQUETE con techo EXACTO por pantalla. Si alguna vez sube, falla; si baja, también
avisa para que se ajuste. Con holgura se afloja solo y deja de apretar (M104).
"""
import re

from .conftest import TEST_PASSWORD, csrf_headers

EM = chr(8212)

# Techo por pantalla. Hoy TODAS están en cero y así se quedan.
PANTALLAS = {
    "/inventarios": 0,      # Planta
    "/calidad": 0,
    "/compras": 0,
    "/aseguramiento": 0,
    "/hoy": 0,              # CEO · vista del día
    "/tesoreria": 0,
    # 19-ago · faltaban justo las que Sebastián pidió revisar: el panel del CEO, el
    # Centro de Mando y Dirección Técnica. Una regla global medida en 6 de 12 pantallas
    # es una intención, no un blindaje -- y el em-dash apareció en la primera que se
    # sumó (M235, otra vez).
    "/gerencia-financiero": 0,   # CEO · financiero
    "/centro": 0,                # Centro de Mando
    "/tecnica": 0,               # Dirección Técnica
    "/rrhh": 0,
}


def _pantallas_del_menu(cli):
    """Los destinos que el MENÚ ofrece · para que una pantalla nueva no nazca sin vigilar.

    La lista de arriba es el piso (esas se exigen sí o sí); ésta la amplía sola con lo que
    el menú agregue mañana. Una lista escrita a mano se pudre y deja de cubrir justo lo
    que se acaba de construir (M122).
    """
    try:
        html = cli.get("/modulos").get_data(as_text=True)
    except Exception:
        return set()
    out = set()
    for m in re.finditer(r"<a\b[^>]*>", html):
        tag = m.group(0)
        if "mod-card" not in tag:
            continue
        h = re.search(r'href=["\']([^"\']+)', tag)
        if h and h.group(1).startswith("/"):
            out.add(h.group(1).split("?")[0])
    return out


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, "no pudo entrar %s" % user
    return c


def _servido(cli, ruta):
    """El HTML + los bundles que esa página carga · es lo que el navegador recibe."""
    r = cli.get(ruta, follow_redirects=True)
    if r.status_code != 200:
        return None, r.status_code
    html = r.get_data(as_text=True)
    total = html
    for src in set(re.findall(r'<script[^>]+src="([^"]+\.js[^"]*)"', html)):
        if src.startswith("http"):
            continue
        rb = cli.get(src)
        if rb.status_code == 200:
            total += rb.get_data(as_text=True)
    return total, 200


def test_ninguna_pantalla_grande_tiene_em_dash(app, db_clean):
    cli = _login(app)
    encontrados = {}
    medidas = 0
    objetivo = dict(PANTALLAS)
    for r in _pantallas_del_menu(cli):
        objetivo.setdefault(r, 0)      # lo que el menú ofrezca mañana, también se mide
    for ruta, techo in objetivo.items():
        servido, code = _servido(cli, ruta)
        if servido is None:
            # No se puede medir: se DECLARA, no se da por buena (M100). Si la ruta cambió de
            # nombre, este test tiene que gritar, no callarse.
            encontrados[ruta] = "no se pudo abrir (status %s)" % code
            continue
        medidas += 1
        n = servido.count(EM)
        if n > techo:
            muestras = [m.strip()[:70] for m in
                        re.findall(r"[^\n<>]{0,45}" + EM + r"[^\n<>]{0,25}", servido)[:3]]
            encontrados[ruta] = {"em_dash": n, "techo": techo, "ejemplos": muestras}

    assert medidas >= 10, (
        "se midieron muy pocas pantallas (%d): un barrido que no puede abrir lo que revisa no "
        "mide nada y pasa verde por omisión (M210)" % medidas)
    assert not encontrados, (
        "queda rastro de IA (em-dash) en la UI · regla 0: %s" % encontrados)
