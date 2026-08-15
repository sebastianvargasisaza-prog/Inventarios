"""¿Qué falta para reemplazar MyBatch? · medido, no supuesto (15-ago-2026).

El clon del batch record puede estar completo y aun así no reemplazar nada: el registro
de lote nace OCULTO (`brd_visible` default '0') y el modo de control nace en 'off'. Un
sistema construido y apagado se ve, desde afuera, exactamente igual que uno que no existe
(M181: un respaldo que no corre se ve igual que uno que corre, hasta el día que hace
falta).

Lo que fija este guard:
  · que el estado se MIDA contra la base y cambie cuando el interruptor cambia (si el
    tablero no se mueve al mover el interruptor, está mostrando una foto, no el estado);
  · que cada punto diga DÓNDE se cambia, o el tablero informa y no sirve para actuar;
  · que lo que no se pudo medir NO se reporte como cero (M154: un cero que nadie calculó
    se lee como "no hay nada que hacer" y significa lo contrario);
  · que se declare lo que este tablero NO mide -la validación Part 11 por un tercero-,
    porque un tablero que promete más de lo que mide enseña a desconfiar de los demás.
"""
import os
import sqlite3

import pytest

from .conftest import TEST_PASSWORD, csrf_headers

# Los interruptores que este archivo mueve viven en `app_settings`, que es COMPARTIDA por
# toda la suite. Dejar `ebr_mode` en 'strict' enciende los gates de liberación para todos
# los archivos que corran después y produce rojos que no hablan de ellos (M103). Se
# guardan sus valores y se restauran, pase lo que pase con los asserts.
_CLAVES_TOCADAS = ("brd_visible", "ebr_mode", "exigir_area_limpia", "exigir_ipc_estandar",
                   "exigir_justificacion_yield", "exigir_aprobacion_orden")


@pytest.fixture(autouse=True)
def _restaurar_interruptores():
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        previos = {}
        for k in _CLAVES_TOCADAS:
            r = conn.execute("SELECT valor FROM app_settings WHERE clave=?", (k,)).fetchone()
            previos[k] = (r[0] if r else None)
    finally:
        conn.close()
    yield
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        for k, v in previos.items():
            if v is None:
                conn.execute("DELETE FROM app_settings WHERE clave=?", (k,))
            else:
                conn.execute("INSERT INTO app_settings (clave, valor) VALUES (?,?) "
                             "ON CONFLICT (clave) DO UPDATE SET valor=excluded.valor", (k, v))
        conn.commit()
    finally:
        conn.close()


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _set(clave, valor):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        conn.execute("INSERT INTO app_settings (clave, valor) VALUES (?,?) "
                     "ON CONFLICT (clave) DO UPDATE SET valor=excluded.valor",
                     (clave, valor))
        conn.commit()
    finally:
        conn.close()


def _estado(app):
    c = _login(app)
    r = c.get("/api/aseguramiento/estado-reemplazo-mybatch")
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def _punto(j, clave):
    p = [x for x in j["puntos"] if x["clave"] == clave]
    assert p, "falta el punto %s: %s" % (clave, [x["clave"] for x in j["puntos"]])
    return p[0]


def test_dice_quien_ve_el_registro_de_lote(app, db_clean):
    """Oculto es el default y es correcto; lo que no puede pasar es que no se sepa."""
    _set("brd_visible", "0")
    p = _punto(_estado(app), "visibilidad")
    assert p["estado"] == "falta", p
    assert "nadie" in p["valor"], p["valor"]

    _set("brd_visible", "sebastian")
    p = _punto(_estado(app), "visibilidad")
    assert p["estado"] == "parcial", p
    assert "sebastian" in p["valor"], p["valor"]

    _set("brd_visible", "1")
    p = _punto(_estado(app), "visibilidad")
    assert p["estado"] == "ok", p
    assert "todo el equipo" in p["valor"], p["valor"]


def test_el_tablero_se_mueve_cuando_el_interruptor_se_mueve(app, db_clean):
    """Si no se mueve, está mostrando una foto y no el estado (M9)."""
    _set("ebr_mode", "off")
    assert _punto(_estado(app), "modo")["estado"] == "falta"
    _set("ebr_mode", "warn")
    p = _punto(_estado(app), "modo")
    assert p["estado"] == "parcial", p
    assert "no bloquea" in p["valor"], p["valor"]
    _set("ebr_mode", "strict")
    p = _punto(_estado(app), "modo")
    assert p["estado"] == "ok", p
    assert "bloquea" in p["valor"], p["valor"]


def test_los_controles_apagados_se_reportan_apagados(app, db_clean):
    """Los cuatro controles que MyBatch aplica y EOS trae apagados de fábrica."""
    for clave in ("exigir_area_limpia", "exigir_ipc_estandar",
                  "exigir_justificacion_yield", "exigir_aprobacion_orden"):
        _set(clave, "0")
        assert _punto(_estado(app), clave)["estado"] == "falta", clave
        _set(clave, "1")
        p = _punto(_estado(app), clave)
        assert p["estado"] == "ok", (clave, p)
        assert p["valor"] == "encendido", (clave, p)
        _set(clave, "0")


def test_cada_punto_dice_donde_se_cambia(app, db_clean):
    """Un tablero que informa y no dice dónde actuar obliga a buscar la pantalla."""
    j = _estado(app)
    sin_donde = [p["clave"] for p in j["puntos"] if not p.get("donde")]
    assert not sin_donde, "estos puntos no dicen dónde se cambian: %s" % sin_donde
    assert all(p.get("porque") for p in j["puntos"]), (
        "un punto sin el porqué es una orden sin motivo")


def test_declara_lo_que_no_mide(app, db_clean):
    """La validación por un tercero (GAMP 5) no se puede leer de la base, y prometerla
    haría que el tablero mienta justo en lo que más pesa para INVIMA."""
    j = _estado(app)
    assert j.get("aviso"), j.keys()
    assert "tercero" in j["aviso"], j["aviso"]
    assert j["listos"] + j["parciales"] + j["pendientes"] == j["total"], j


def test_la_pantalla_existe_y_se_alcanza(app, db_clean):
    """Una capacidad a la que nadie puede llegar no existe (M121), y la pestaña tiene que
    estar en el mapa o abre EN BLANCO (M155)."""
    c = _login(app, "miguel")
    pg = c.get("/aseguramiento/reemplazo-mybatch")
    assert pg.status_code == 200, pg.status_code
    html = pg.data.decode("utf-8")
    assert "/api/aseguramiento/estado-reemplazo-mybatch" in html, "la pantalla no carga nada"
    assert "function rmCargar(" in html, "falta la función que la pinta"
    aseg = c.get("/aseguramiento").data.decode("utf-8")
    assert "/aseguramiento/reemplazo-mybatch" in aseg, "no se llega desde Aseguramiento"
    assert "goTab('tab-reemplazo')" in aseg, "falta la pestaña"
    assert "'tab-reemplazo'" in aseg.split("_tabIds")[1][:400], (
        "la pestaña no está en el mapa: abrirla dejaría la pantalla en blanco")
    assert 'id="tab-reemplazo"' in aseg, "falta el panel"
