"""Abrir un legajo: el número de lote se PROPONE solo y se puede cambiar (16-ago-2026).

Sebastián: *"resuelve lo del lote juliano que aparezca espontáneo sin errores, pero que puedan
modificarlo, resuelve el tres"*.

El helper y el endpoint del lote juliano existían desde esta misma sesión y **ninguna pantalla
los llamaba**: una capacidad a la que nadie puede llegar no existe (M121). Y el "tres" era que
abrir un legajo eran **tres `prompt()` del navegador encadenados** (producto → fase → lote), con
el número de lote tecleado de memoria aunque el sistema ya sabe cuál toca.

Tres garantías, y la tercera es la que evita que esto se vuelva una traba:

  · el lote se propone con la numeración real de la planta (año + día juliano + consecutivo);
  · se puede editar -- quien decide el número de lote es quien fabrica;
  · y si no se puede calcular, el campo queda VACÍO con el motivo a la vista, nunca un número
    inventado ni un error que frene (Sebastián: *"sin errores"*).
"""
import re

import pytest

from .conftest import TEST_PASSWORD, csrf_headers, pantalla_servida


def _login(app, usuario="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": usuario, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, "no pudo entrar %s" % usuario
    return c


def _pantalla(app):
    """Todo lo que el navegador CARGA al abrir Planta: el HTML más sus bundles.

    El JS de esta pantalla no viaja inline (se sirve como `/planta-app.js` y `/planta-core.js`
    para que se pueda cachear), así que buscar el modal sólo en el HTML concluye que no existe
    -- y eso no habla del código sino de dónde quedó escrito (M166).
    """
    return pantalla_servida(_login(app), "/inventarios")


# ══ el número se propone ════════════════════════════════════════════════════════

def test_el_endpoint_propone_el_lote_de_hoy(app, db_clean):
    r = _login(app).get("/api/brd/lote-sugerido")
    assert r.status_code == 200, r.data[:200]
    j = r.get_json() or {}
    # o trae un número, o dice por qué no: las dos son respuestas válidas, un 500 no.
    assert ("sugerido" in j), j
    if j.get("sugerido"):
        assert re.fullmatch(r"\d{6}", str(j["sugerido"])), (
            "el formato no es el del rótulo (año + día juliano + consecutivo): %r" % j["sugerido"])
        assert j.get("explicacion"), "no explica de dónde sale el número"
    else:
        assert j.get("motivo"), "no dice por qué no pudo proponerlo"


def test_la_pantalla_pide_el_lote_propuesto(app, db_clean):
    """Lo que faltaba: que ALGUIEN lo llame. El endpoint estaba y no lo usaba nadie."""
    html = _pantalla(app)
    assert "/api/brd/lote-sugerido" in html, (
        "ninguna pantalla pide el lote sugerido · el endpoint sigue sin puerta")
    assert "_nlgLote" in html, "falta la función que lo trae al abrir el modal"


def test_el_lote_se_puede_cambiar(app, db_clean):
    """*"pero que puedan modificarlo"* · el número va en un input, no en un texto fijo."""
    html = _pantalla(app)
    assert 'id="nlg-lote"' in html, "no hay campo de lote"
    campo = html[html.index('id="nlg-lote"') - 200: html.index('id="nlg-lote"') + 200]
    assert "<input" in campo, "el lote no es editable · quedó como texto"
    assert "readonly" not in campo and "disabled" not in campo, "el campo está bloqueado"


def test_si_no_se_puede_calcular_no_frena(app, db_clean):
    """*"sin errores"* · sin número el campo queda vacío y el motivo se ve; nunca un número
    inventado ni un aviso que corte el paso."""
    html = _pantalla(app)
    i = html.index("async function _nlgLote(")
    cuerpo = html[i:i + 1400]
    assert "d.motivo" in cuerpo, "no muestra el motivo cuando no hay número"
    assert "catch" in cuerpo, "un fallo de red dejaría la pantalla colgada"
    assert "alert(" not in cuerpo, "un aviso modal para esto frena al operario"


# ══ los tres prompt() se fueron ═════════════════════════════════════════════════

def test_abrir_un_legajo_ya_no_son_tres_prompts(app, db_clean):
    """Los `prompt()` encadenados son del navegador, se ven prestados y obligan a contestar a
    ciegas: el error "ese producto no tiene instructivo" aparecía recién al final, después de
    haber escrito las tres respuestas."""
    html = _pantalla(app)
    i = html.index("async function ebrNuevoLegajo(")
    # sin comentarios: el de esta función EXPLICA que antes eran tres prompt(), así que un
    # guard que los cuente se encuentra a sí mismo y falla con el código correcto (M154)
    cuerpo = re.sub(r"//[^\n]*", "", html[i:i + 6000])
    assert "prompt(" not in cuerpo, "siguen los prompt() del navegador"
    for pieza, que in (('id="nlg-prod"', "el producto se elige de una lista"),
                       ('id="nlg-fase"', "la etapa también"),
                       ("_nlgCrear", "y hay un botón propio que abre el legajo")):
        assert pieza in html, "falta %s (%s)" % (pieza, que)


def test_solo_ofrece_productos_que_se_pueden_ejecutar(app, db_clean):
    """Sin instructivo aprobado no hay legajo posible, así que el producto se elige entre los
    que SÍ lo tienen -- en vez de descubrirlo al final (M188: el motivo tiene que llegar antes
    de que la persona haga el trabajo)."""
    html = _pantalla(app)
    i = html.index("async function _nlgProductos(")
    cuerpo = html[i:i + 1600]
    assert "estado=aprobado" in cuerpo, "ofrece productos sin instructivo aprobado"


def test_un_doble_clic_no_abre_dos_legajos(app, db_clean):
    """Toda acción que INSERTA necesita su guard: dos clics no pueden abrir dos registros de
    lote (M63)."""
    html = _pantalla(app)
    i = html.index("async function _nlgCrear(")
    cuerpo = html[i:i + 2000]
    assert "_nlgBusy" in cuerpo, "no hay guard anti doble-clic"
    assert "finally" in cuerpo, "el guard no se suelta si algo falla"


# ══ y no se pisa con la pantalla que lo hospeda ═════════════════════════════════

def test_los_ids_del_modal_no_chocan_con_la_pagina(app, db_clean):
    """Un modal que reusa ids ajenos deja botones que no hacen nada, y sin un solo error
    (M204): `getElementById` devuelve el primero del documento."""
    html = _pantalla(app)
    for ident in ("nlg-prod", "nlg-fase", "nlg-lote", "nlg-ok", "nlg-msg"):
        assert html.count('id="%s"' % ident) <= 1, "el id %s aparece repetido" % ident


def test_milton_tiene_nombre_en_los_registros_que_firma(app, db_clean):
    """Es operario y firma pasos del batch record: sin nombre, el registro dice el username.

    Se verifica sobre la MIGRACIÓN y no sobre la fila, porque `db_clean` puede vaciar la tabla
    entre tests y entonces el guard mediría el estado de la base y no la garantía (M103).
    """
    from database import MIGRATIONS
    sql = " ".join(str(s) for v, _d, stmts in MIGRATIONS if v == 439 for s in stmts)
    assert sql, "la migración del nombre de Milton desapareció"
    assert "milton" in sql.lower() and "Sierra" in sql
    assert "COALESCE(nombre_completo,'')=''" in sql, (
        "pisaría un nombre cargado a mano en vez de rellenar sólo lo vacío")
    # Milton entró a la planta DESPUÉS de que se sembró la tabla, así que no tenía fila: una
    # migración de sólo UPDATE habría sido un no-op silencioso -- se ve igual que aplicada y el
    # legajo seguiría imprimiendo el username. Lo cazó mirar la fila DESPUÉS de correrla.
    assert "INSERT" in sql.upper(), (
        "sin INSERT la migración no hace nada: Milton no tenía fila en usuarios_identidad")
    # y los que NO se cargan, por el motivo que está escrito en la migración
    for quien in ("alejandro", "mayra", "gloria"):
        assert ("'%s'" % quien) not in sql.lower(), (
            "%s no está en la nómina de Espagiria o su cargo desmiente la coincidencia" % quien)
