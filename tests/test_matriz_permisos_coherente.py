"""La matriz de permisos y la puerta de cada módulo tienen que decir LO MISMO (15-ago-2026).

`config.MODULOS_ACCESO` es la matriz que Sebastián dictó persona por persona (7-ago) y es
la ÚNICA fuente: la usan el menú de /modulos y el gate global de rutas de `auth.py`. Pero
cada página puede además tener su propio gate, y si ese es más estricto que la matriz el
resultado es el peor posible: **el menú le ofrece el módulo a la persona, el gate global
la deja pasar, y la página le contesta "sin acceso"**.

Así estaba `/aseguramiento`: gateaba con `ASEGURAMIENTO_USERS` (miguel, alejandro,
sebastian) mientras la matriz incluye también al director técnico y a Luz. Hernando veía
la tarjeta en el menú, entraba, y le rebotaba (M32/M97 · y se vive como que el sistema
miente · M161).

Este guard recorre la matriz REAL y ENTRA por la ruta de cada módulo con cada persona que
la matriz autoriza. No lee gates: los ejerce, que es la única forma de no equivocarse
sobre cuál corre (M170: distinguir "no tiene gate" de "tiene uno que no supe resolver").
"""
import pytest

from .conftest import TEST_PASSWORD, csrf_headers


def _entra(app, usuario, ruta):
    """Abre la ruta con ese usuario. Devuelve None si no se pudo loguear.

    Se devuelve None en vez de saltar el test: un `pytest.skip` dentro del recorrido
    aborta el barrido ENTERO al primer usuario sin clave, y el guard pasaría verde sin
    haber medido nada (M152).
    """
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    if r.status_code != 302:
        return None
    return c.get(ruta, follow_redirects=False)


def _matriz():
    from api.config import MODULOS_ACCESO, MODULO_POR_RUTA
    ruta_de = {}
    for pref, mod in MODULO_POR_RUTA:
        # la ruta más corta del módulo es su portada
        if mod not in ruta_de or len(pref) < len(ruta_de[mod]):
            ruta_de[mod] = pref
    return MODULOS_ACCESO, ruta_de


def test_quien_esta_en_la_matriz_entra_de_verdad(app, db_clean):
    """Si la matriz te da el módulo, la página no te puede rebotar."""
    matriz, ruta_de = _matriz()
    trabados, medidos, sin_clave = [], 0, set()
    for modulo, gente in sorted(matriz.items()):
        ruta = ruta_de.get(modulo)
        if not ruta:
            continue
        for usuario in sorted(gente):
            r = _entra(app, usuario, ruta)
            if r is None:
                sin_clave.add(usuario)
                continue
            medidos += 1
            cuerpo = r.data.decode("utf-8", "ignore") if r.data else ""
            # `sin_acceso_html` responde 200 con la pantalla de "sin acceso": un 200 NO
            # prueba que entró, así que se mira el contenido (M170).
            rebotado = ("Sin acceso" in cuerpo or "sin acceso" in cuerpo
                        or "No tienes acceso" in cuerpo)
            if r.status_code == 403 or rebotado:
                trabados.append("%s no entra a %s (%s · %s)"
                                % (usuario, modulo, ruta, r.status_code))
    # Un barrido que no midió nada no es un barrido verde: es un barrido que no corrió.
    assert medidos >= 20, (
        "sólo se pudieron medir %d combinaciones (sin clave en este entorno: %s)"
        % (medidos, sorted(sin_clave)))
    assert not trabados, (
        "la matriz les da el módulo y la página los rechaza:\n  " + "\n  ".join(trabados))


def test_el_director_tecnico_llega_a_sus_verificaciones(app, db_clean):
    """El caso concreto que destapó esto: la pantalla donde el DT configura el
    procedimiento vivía detrás de una puerta que el DT no podía abrir (M121)."""
    r = _entra(app, "hernando", "/aseguramiento")
    cuerpo = r.data.decode("utf-8", "ignore")
    assert "Sin acceso" not in cuerpo and "sin acceso" not in cuerpo, (
        "el director técnico no entra a Aseguramiento, que es donde configura el "
        "despeje y los controles en proceso")
    assert "/aseguramiento/checklists" in cuerpo, "y no encuentra su pantalla"
