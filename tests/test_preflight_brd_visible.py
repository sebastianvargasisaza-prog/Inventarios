# -*- coding: utf-8 -*-
"""PRE-VUELO de `brd_visible` · lo que el piso va a ver cuando se encienda el interruptor.

Hoy el registro de lote nace OCULTO (`app_settings.brd_visible` ausente = '0'): las páginas del
batch record devuelven el candado "en validación" y el dashboard de Planta esconde sus dos
secciones. Encenderlo NO bloquea nada -- sólo REVELA --, y por eso el riesgo no es que trabe la
planta: es que el piso llegue a una pantalla rota, a un "sin acceso", o a dos pantallas distintas
peleando por la misma URL (M200), y aprenda en el primer día que el módulo no sirve.

Este barrido ABRE cada página del batch record con cada persona que trabaja en el piso y exige
que sirva algo utilizable. No lee gates: los ejerce (M210/M217).
"""
import re

import pytest

# ⚠ `database` se importa DENTRO de cada función, nunca a nivel de módulo: a nivel de módulo
#   corre en la COLECCIÓN -- antes de que ninguna fixture prepare el entorno -- y deja `config`
#   cacheado sin las claves de prueba, rompiendo el login de los archivos siguientes (M165/M184).

# Quiénes van a ver el módulo cuando se encienda. Las páginas del batch record sólo piden
# sesión, así que el universo es "todo el que entra a planta": los operarios, el jefe de
# producción, Control de Calidad, Aseguramiento, el Director Técnico y dirección.
PISO = ["jose", "milton", "mayerlin", "camilo", "smurillo",
        "laura", "yuliel", "miguel", "hernando", "alejandro", "sebastian"]

# Páginas con puerta propia declarada a propósito, con su motivo. Se enumeran (nunca se afloja
# el barrido): una excepción sin motivo escrito es una ruta que dejó de vigilarse (M122).
RESTRINGIDAS = {
    "/planta/activar-legajos": ("activación masiva de legajos: Admin o Calidad",
                                {"sebastian", "alejandro", "laura", "yuliel"}),
    "/admin/planta-demo": ("sembrar un lote de demostración: sólo dirección",
                           {"sebastian", "alejandro"}),
    "/admin/cargar-instructivo": ("cargar el instructivo maestro: sólo dirección",
                                  {"sebastian", "alejandro"}),
    # Retirada el 17-ago: era un duplicado del maestro de lotes de Calidad. Queda redirigiendo
    # (M120) y la pantalla destino pertenece a Calidad, así que el piso NO la ve: eso es la
    # matriz de módulos funcionando, no una traba.
    "/aseguramiento/maestro-lotes": ("redirige al maestro de lotes de Calidad",
                                     {"sebastian", "alejandro", "miguel", "hernando"}),
}

CANDADO = "en validación"


def _login(app, usuario):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": "TestPass123"},
               headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert r.status_code == 302, "no pudo entrar %s" % usuario
    return c


def _visible(app, valor="1"):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO app_settings (clave, valor) VALUES ('brd_visible',?) "
                  "ON CONFLICT (clave) DO UPDATE SET valor=excluded.valor", (valor,))
        c.commit()


@pytest.fixture(scope="module")
def demo(app):
    """Los tres legajos del lote DEMO, creados por el camino REAL (no filas a mano · M153)."""
    from flask import session
    with app.test_request_context("/", method="GET"):
        session["compras_user"] = "sebastian"
        from blueprints.brd import crear_planta_demo
        j = crear_planta_demo().get_json()
    assert j.get("ok"), "el demo no se pudo sembrar: %s" % j
    return j


def _paginas(app, demo):
    """Cada página no-API del batch record, con sus parámetros resueltos a datos REALES.

    Se enumeran desde el `url_map` de verdad, así que una página nueva entra sola al barrido.
    """
    fab = demo["fabricacion_ebr"]
    env = demo["envasado_ebr"]
    aco = demo["acondicionamiento_ebr"]
    from database import get_db
    with app.app_context():
        orden = get_db().execute(
            "SELECT orden_id FROM ebr_ejecuciones WHERE id=? AND orden_id IS NOT NULL",
            (fab,)).fetchone()
    orden_id = (orden[0] if orden else None)

    urls = []
    vistas = set()
    for rule in app.url_map.iter_rules():
        if not str(rule.endpoint).startswith("brd."):
            continue
        if "GET" not in (rule.methods or set()):
            continue
        regla = str(rule.rule)
        if regla.startswith("/api/"):
            continue
        # una sola URL por PÁGINA: /brd y /brd/ son la misma
        url = regla.replace("<int:ebr_id>", str(fab)).replace("<int:orden_id>",
                                                              str(orden_id or fab))
        if "legajo-envasado" in url or "instrucciones-envasado" in url:
            url = re.sub(r"/\d+$", "/%d" % env, url)
        if "acondicionamiento" in url:
            url = re.sub(r"/\d+$", "/%d" % aco, url)
        if "<" in url:            # quedó un parámetro sin resolver: no se puede medir
            continue
        if url.rstrip("/") in vistas:
            continue
        vistas.add(url.rstrip("/"))
        urls.append(url)
    return sorted(urls)


def test_ninguna_pagina_del_batch_record_comparte_URL_con_otra(app):
    """Dos pantallas en la misma URL no dan error: una queda MUERTA y desde el código se ve
    perfecta (M200). Acá pasó con `/planta/orden/<id>`, que estaba declarada dos veces -- el
    legajo del LOTE y el detalle de la ORDEN madre -- así que una de las dos era inalcanzable."""
    vistas = {}
    for rule in app.url_map.iter_rules():
        if not str(rule.endpoint).startswith("brd."):
            continue
        regla = str(rule.rule)
        if regla.startswith("/api/"):
            continue
        # la forma de la URL, sin el NOMBRE del parámetro: /x/<int:a> y /x/<int:b> son la misma
        forma = re.sub(r"<[^:>]+:[^>]+>", "<n>", regla).rstrip("/")
        # dos reglas del MISMO endpoint son un alias legítimo (`/brd` y `/brd/`), no un choque:
        # el choque es que dos PANTALLAS distintas contesten la misma URL
        vistas.setdefault(forma, set()).add(str(rule.endpoint))
    choques = {k: sorted(v) for k, v in vistas.items() if len(v) > 1}
    assert not choques, (
        "dos pantallas del batch record responden a la misma URL · una queda muerta: %s" % choques)


def test_el_piso_llega_a_cada_pantalla_del_batch_record(app, demo):
    """El barrido que decide si el interruptor se puede encender: abrir TODO, con TODOS."""
    _visible(app, "1")
    paginas = _paginas(app, demo)
    assert len(paginas) >= 12, "el barrido se quedó sin páginas que medir: %s" % paginas

    fallas, medidas = [], 0
    for usuario in PISO:
        cli = _login(app, usuario)
        for url in paginas:
            base = url.split("?")[0]
            clave = re.sub(r"/\d+$", "", base)
            motivo_permitidos = RESTRINGIDAS.get(clave)
            r = cli.get(url)
            medidas += 1
            if r.status_code in (301, 302, 303, 307, 308):
                # una ruta retirada que redirige es correcta (M120): se mide el DESTINO
                r = cli.get(r.headers.get("Location") or url)
            cuerpo = r.get_data(as_text=True)
            if r.status_code >= 500:
                fallas.append("%s %s → %s" % (usuario, url, r.status_code))
                continue
            if CANDADO in cuerpo:
                fallas.append("%s %s → el candado tapó la pantalla con brd_visible=1" % (usuario, url))
                continue
            if motivo_permitidos:
                _motivo, permitidos = motivo_permitidos
                if usuario in permitidos and ("Solo admin" in cuerpo or "Solo Admin" in cuerpo):
                    fallas.append("%s %s → la puerta rebotó a quien SÍ debe entrar (%s)"
                                  % (usuario, url, _motivo))
                continue
            # una página sin puerta propia no puede contestar "sin acceso" (M210: contesta 200)
            if re.search(r"[Ss]in acceso|Solo Admin o Calidad|No autorizado", cuerpo[:4000]):
                fallas.append("%s %s → 200 con 'sin acceso' en el cuerpo" % (usuario, url))
                continue
            if len(cuerpo) < 500:
                fallas.append("%s %s → respuesta de %d caracteres (pantalla vacía)"
                              % (usuario, url, len(cuerpo)))

    assert medidas >= len(PISO) * 12, "se midieron sólo %d combinaciones" % medidas
    assert not fallas, "el piso no llega a estas pantallas:\n  " + "\n  ".join(fallas)


# Pantallas a las que se llega tecleando la URL, con su motivo. Se enumeran: una excepción sin
# motivo escrito es una pantalla que dejó de vigilarse (M122).
SIN_ENLACE_A_PROPOSITO = {
    "/admin/planta-demo": "herramienta de dirección para sembrar el lote de demostración",
    "/admin/cargar-instructivo": "carga puntual del instructivo maestro, sólo dirección",
    "/aseguramiento/maestro-lotes": "ruta RETIRADA que sólo redirige (M120)",
    "/planta/ordenes-batch": "se llega desde el detalle de una orden madre",
}

# Los menús y tableros de los que cuelga el batch record. Se suman a las páginas del propio
# módulo, porque muchos enlaces viven DENTRO de un legajo (el imprimible del despeje, el
# timeline, las instrucciones). Se piden SERVIDAS y con sus bundles: las funciones y los
# enlaces del dashboard viven en archivos externos, así que mirar sólo el HTML concluye que
# nada existe (M166/M217).
# ⚠ el tablero de gerencia se sirve en `/gerencia-financiero`: `/gerencia` redirige a otra
#   pantalla. Puse `/gerencia` de memoria y el guard marcó la analítica como huérfana teniendo
#   su enlace ahí desde siempre -- una ruta se verifica contra el url_map, no contra el recuerdo
#   de quien la escribe (M202).
MENUS = ["/planta", "/tecnica", "/gerencia-financiero", "/calidad",
         "/planta-core.js", "/planta-app.js"]


def test_toda_pantalla_del_batch_record_tiene_por_donde_llegar(app, demo):
    """Una capacidad a la que nadie puede llegar no existe (M121).

    Encender `brd_visible` sin esto revela pantallas que el piso no puede abrir: pasó con la
    lista de Órdenes de Producción y con la bandeja del Director Técnico, las dos vivas desde
    junio y con CERO enlaces -- sólo se llegaba tecleando la URL.

    Se compara contra lo que el navegador CARGA, y **nunca contra la propia pantalla**: una
    página que sólo se enlaza a sí misma sigue siendo inalcanzable.
    """
    _visible(app, "1")
    cli = _login(app, "sebastian")
    paginas = _paginas(app, demo)

    corpus = {}
    for url in MENUS + paginas:
        r = cli.get(url)
        if r.status_code in (301, 302):
            continue
        if r.status_code == 200:
            corpus[url] = r.get_data(as_text=True)
    assert len(corpus) >= len(paginas), "no se pudieron leer las pantallas: %d" % len(corpus)

    huerfanas = []
    for url in paginas:
        prefijo = re.sub(r"/\d+$", "/", url)
        if prefijo.rstrip("/") in SIN_ENLACE_A_PROPOSITO or url in SIN_ENLACE_A_PROPOSITO:
            continue
        llega = any(
            (prefijo in cuerpo or url in cuerpo)
            for otra, cuerpo in corpus.items() if otra != url)
        if not llega:
            huerfanas.append(url)
    assert not huerfanas, (
        "estas pantallas del batch record no se pueden abrir desde ninguna otra (M121): %s"
        % huerfanas)


def test_apagado_sigue_tapando_las_paginas(app, demo):
    """Dientes del otro lado: el candado tiene que seguir funcionando (el interruptor es
    reversible, y si vuelve a apagarse debe tapar de verdad)."""
    _visible(app, "0")
    try:
        html = _login(app, "jose").get("/planta/ordenes-produccion").get_data(as_text=True)
        assert CANDADO in html, "con brd_visible=0 la página se sirvió igual"
    finally:
        _visible(app, "1")   # el resto de la suite corre con el módulo visible
