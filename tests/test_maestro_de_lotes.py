# -*- coding: utf-8 -*-
"""Maestro de lotes · UNO solo, y con enlace desde Dirección Técnica.

⚠ Este archivo nació protegiendo un maestro de lotes que yo construí el 17-ago en
`/aseguramiento/maestro-lotes`... sin ver que YA existía uno en `/calidad/maestro-lotes` desde
el 15-ago, y mucho más completo. Lo busqué preguntándole a EOS por `/api/brd/maestro-lotes` --
una URL que inventé yo --, vi el 404 y concluí que faltaba.

Dos pantallas con el mismo nombre no son dos vistas: son dos verdades que divergen, y quien las
mira no tiene forma de saber cuál creer (M99/M161). El duplicado se retiró y la ruta quedó
redirigiendo, porque llegó a estar enlazada (M120).

Lo que este guard protege ahora:
  · que el maestro de lotes exista y responda
  · que se pueda LLEGAR a él (una capacidad sin enlace no existe · M121)
  · que NO vuelva a haber dos rutas distintas ofreciendo un "maestro de lotes"
"""
import pytest

_H = {"Origin": "http://localhost"}


def _login(client, usuario="sebastian"):
    r = client.post("/login", data={"username": usuario, "password": "TestPass123"},
                    headers=_H, follow_redirects=False)
    assert r.status_code == 302, "no entro %s" % usuario
    return client


def test_el_maestro_de_lotes_responde(client):
    """La pantalla y su endpoint, ejercidos de verdad."""
    cli = _login(client, "laura")

    r = cli.get("/api/calidad/maestro-lotes")
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    j = r.get_json() or {}
    assert j.get("ok") is True
    for k in ("lotes", "total", "mostrados", "teorica_origen"):
        assert k in j, "falta %s en la respuesta · %s" % (k, sorted(j))
    # ⚠ el origen de la teórica se DECLARA: un número que no se puede auditar no sirve
    #   para firmar un lote (M124)
    assert (j.get("teorica_origen") or "").strip()

    p = cli.get("/calidad/maestro-lotes")
    assert p.status_code == 200
    assert len(p.get_data()) > 5000, "la pantalla salió casi vacía"


def test_se_llega_desde_direccion_tecnica(client):
    """Una capacidad a la que nadie puede llegar no existe (M121)."""
    tec = _login(client, "sebastian").get("/tecnica").get_data(as_text=True)
    assert "/calidad/maestro-lotes" in tec, (
        "Dirección Técnica no enlaza el maestro de lotes")
    assert "/aseguramiento/maestro-lotes" not in tec, (
        "el enlace sigue apuntando a la pantalla DUPLICADA que se retiró")


def test_la_ruta_del_duplicado_redirige_y_no_muestra_otra_cosa(client):
    """Una URL que estuvo enlazada no se borra: se redirige (M120)."""
    r = _login(client, "sebastian").get("/aseguramiento/maestro-lotes")
    assert r.status_code in (301, 302), (
        "la ruta del duplicado tiene que redirigir, no servir una segunda pantalla · dio %s"
        % r.status_code)
    assert "/calidad/maestro-lotes" in (r.headers.get("Location") or "")


def test_no_puede_haber_DOS_maestros_de_lotes(client, app):
    """El guard de fondo: que nadie vuelva a construir un segundo.

    ⚠ Se recorre el `url_map` REAL y se ABRE cada ruta, no se lee su fuente. La primera versión
    de este guard buscaba `redirect(` en el código y dio 0 pantallas: encontró el redirect del
    LOGIN dentro de la pantalla buena. Medir el comportamiento en vez del texto es la diferencia
    entre un guard y una impresión (M170).
    """
    cli = _login(client, "sebastian")
    sirven = []
    for regla in app.url_map.iter_rules():
        ruta = str(regla)
        if "maestro-lotes" not in ruta or ruta.startswith("/api/") or "<" in ruta:
            continue
        if "GET" not in (regla.methods or set()):
            continue
        r = cli.get(ruta)
        # sirve una pantalla = 200 con cuerpo de verdad · una redirección no cuenta
        if r.status_code == 200 and len(r.get_data()) > 5000:
            sirven.append(ruta)

    assert len(sirven) == 1, (
        "hay %d pantallas sirviendo un maestro de lotes: %s · dos verdades del mismo hecho "
        "divergen y el usuario no sabe cuál creer (M99/M161)" % (len(sirven), sirven))
    assert sirven[0] == "/calidad/maestro-lotes", sirven
