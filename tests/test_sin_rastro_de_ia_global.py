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
}


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, "no pudo entrar %s" % user
    return c


def _servido(cli, ruta):
    """El HTML + los bundles que esa página carga · es lo que el navegador recibe."""
    r = cli.get(ruta)
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
    for ruta, techo in PANTALLAS.items():
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

    assert medidas >= 4, (
        "se midieron muy pocas pantallas (%d): un barrido que no puede abrir lo que revisa no "
        "mide nada y pasa verde por omisión (M210)" % medidas)
    assert not encontrados, (
        "queda rastro de IA (em-dash) en la UI · regla 0: %s" % encontrados)
