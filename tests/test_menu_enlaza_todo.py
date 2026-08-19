# -*- coding: utf-8 -*-
"""El menú ofrece lo que se puede abrir, y todo lo que se puede abrir está en el menú.

Sebastián 19-ago: *"ir enlazando todo... que vaya cogiendo más forma de app perfecta"*.

Dos formas de que una capacidad no exista aunque esté construida:
  · la pantalla existe y **no hay cómo llegar** -- desde adentro se ve terminada, y por eso
    es la más cara (M121: pasó con el listado de órdenes, con la bandeja del DT y con el
    panel de acceso al portal);
  · el menú ofrece una tarjeta y al abrirla **rebota** -- ahí la persona aprende que el
    módulo no sirve, y deja de intentar (M210).

Se mide sobre la página SERVIDA, no sobre el texto del template: los enlaces se arman con
HTML escapado dentro de constantes de Python y cualquier regex sobre el fuente termina
midiendo otra cosa (M170).
"""
import re

from .conftest import TEST_PASSWORD, csrf_headers


def _cli(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, ("no pudo entrar %s" % user)
    return c


def _tarjetas(cli):
    """Los destinos que el menú ofrece de verdad."""
    html = cli.get("/modulos").get_data(as_text=True)
    assert len(html) > 3000, "el menú salió vacío · el guard no midió nada"
    hrefs = set()
    for m in re.finditer(r'<a\b[^>]*>', html):
        tag = m.group(0)
        if "mod-card" not in tag:
            continue
        h = re.search(r'href=["\']([^"\']+)', tag)
        if h:
            hrefs.add(h.group(1).split("?")[0].rstrip("/") or "/")
    return hrefs


def test_el_menu_tiene_tarjetas(app, db_clean):
    """Si esto falla, los otros dos guards pasarían por omisión (M158/M210)."""
    t = _tarjetas(_cli(app))
    assert len(t) >= 8, ("el menú no ofrece casi nada · o cambió cómo se arman las "
                         "tarjetas y este archivo dejó de medir", sorted(t))


def test_cada_tarjeta_del_menu_lleva_a_una_ruta_QUE_EXISTE(app, db_clean):
    """Una tarjeta que da 404 enseña que el módulo no sirve (M202)."""
    cli = _cli(app)
    reglas = []
    for r in app.url_map.iter_rules():
        rx = re.sub(r"<path:[^>]+>", "@@P@@", str(r.rule))
        rx = re.sub(r"<[^>]+>", "[^/]+", rx)
        reglas.append(re.compile("^" + rx.replace("@@P@@", ".+") + "$"))
    rotas = [h for h in _tarjetas(cli)
             if not any(rg.match(h) for rg in reglas)]
    assert not rotas, ("el menú ofrece tarjetas que no llevan a ninguna ruta: %s" % rotas)


def test_todo_MODULO_de_la_matriz_tiene_su_tarjeta(app, db_clean):
    """Un módulo con permisos y sin puerta es una capacidad que no existe (M121).

    La matriz `config.MODULOS_ACCESO` es la única fuente de quién ve qué; si un módulo
    está ahí y el menú no lo ofrece, alguien tiene permiso para algo a lo que no puede
    llegar salvo tecleando la URL.
    """
    import config
    cli = _cli(app)
    tarjetas = _tarjetas(cli)

    con_puerta = set()
    for h in tarjetas:
        try:
            m = config.modulo_de_ruta(h)
        except Exception:
            m = None
        if m:
            con_puerta.add(m)

    # 'chat' y 'seguridad' se abren desde el widget flotante y desde el perfil, no desde
    # una tarjeta · se declaran acá para que la excepción sea visible y revisable (M122).
    SIN_TARJETA_A_PROPOSITO = {"chat", "seguridad"}

    # Un módulo sin NINGUNA ruta mapeada no necesita tarjeta: no es una pantalla
    # inalcanzable, es una llave de la matriz sin páginas detrás (al 19-ago:
    # `inteligencia` e `invima`). La excepción se calcula, no se escribe: el día que
    # alguien le cuelgue una página, este guard vuelve a exigir su puerta -- una
    # excepción escrita a mano se pudre y deja de vigilar en silencio (M122/M174).
    con_rutas = {mod for _pref, mod in config.MODULO_POR_RUTA}

    falta = sorted((set(config.MODULOS_ACCESO.keys()) & con_rutas)
                   - con_puerta - SIN_TARJETA_A_PROPOSITO)
    assert not falta, (
        "módulos con acceso definido, con páginas, y sin tarjeta en el menú · quien tiene "
        "el permiso no tiene cómo llegar: %s" % falta)


def test_ningun_modulo_de_la_matriz_quedo_SIN_paginas(app, db_clean):
    """Lo que el guard de arriba deja pasar, éste lo NOMBRA en vez de callarlo.

    Un módulo en la matriz de permisos sin una sola ruta detrás no rompe nada, pero hace
    que la matriz -que es la única fuente de quién ve qué- describa algo que no existe.
    Se listan para que sea una decisión y no un olvido (M124: lo que se excluye se dice).
    """
    import config
    con_rutas = {mod for _pref, mod in config.MODULO_POR_RUTA}
    fantasma = sorted(set(config.MODULOS_ACCESO.keys()) - con_rutas)
    # 19-ago · `inteligencia` e `invima` se RETIRARON de la matriz (eran llaves sin
    # ninguna ruta detras y sin un solo consumidor). La excepcion se vacia: si vuelve a
    # aparecer un modulo sin paginas, este guard lo nombra en vez de callarlo.
    CONOCIDOS = set()
    nuevos = sorted(set(fantasma) - CONOCIDOS)
    assert not nuevos, (
        "aparecieron módulos en la matriz de permisos sin ninguna página detrás: %s · o se "
        "les cuelga su pantalla o se sacan de la matriz" % nuevos)
