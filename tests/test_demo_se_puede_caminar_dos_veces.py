# -*- coding: utf-8 -*-
"""El demo de planta se puede caminar MÁS DE UNA VEZ.

Sebastián apretó el paso 2 en producción y le contestó *"No se puede registrar el envasado"*.
El lote existía, la presentación existía y el maestro decía que había 1.000 frascos.

La causa: **el demo sembraba su stock de envases sólo en el cache** (`maestro_mee.stock_actual`)
y el gate del envasado mide el CANÓNICO -- `SUM(movimientos_mee)`, con caída al cache SOLO si no
hay ningún movimiento (M26). Entonces:

    demo recién creado   -> 0 movimientos -> cae al cache -> funciona
    demo YA CAMINADO     -> tiene Salidas -> la suma da 0  -> "stock insuficiente"

O sea que se podía caminar UNA vez y nunca más, que es exactamente lo que él encontró. Y **los
tests pasaban**, porque su base arranca sin movimientos y siempre caía al cache: un fixture
tapando el comportamiento de producción (M153).

Por eso este test NO limpia `movimientos_mee` -- limpiarlo sería reproducir el fixture que
escondía el bug. Al revés: le DRENA el kardex a propósito, como lo dejaría una corrida anterior.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

CODIGOS = ("ENV-DEMO", "TAPA-DEMO", "CAJA-DEMO", "ETIQ-DEMO")
LOTE = "DEMO-PLANTA-1"


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, "no pudo entrar %s" % user
    return c


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)


def _suma_kardex(codigo):
    """Suma CRUDA del kardex, sin la caída al cache · misma semántica de tipos y de `anulado`
    que el resolver canónico `_mee_stock_real` (si el test contara distinto que el gate, estaría
    midiendo otra cosa · M1)."""
    cn = _cn()
    try:
        return float(cn.execute(
            "SELECT COALESCE(SUM(CASE "
            "   WHEN LOWER(tipo) IN ('entrada','ingreso','devolucion','devolución','ajuste') "
            "       THEN cantidad "
            "   WHEN LOWER(tipo) IN ('salida','consumo','rechazo') THEN -cantidad "
            "   ELSE 0 END),0) "
            "  FROM movimientos_mee "
            " WHERE UPPER(mee_codigo)=UPPER(?) AND COALESCE(anulado,0)=0",
            (codigo,)).fetchone()[0] or 0)
    finally:
        cn.close()


def _hay_movimientos(codigo):
    cn = _cn()
    try:
        return int(cn.execute(
            "SELECT COUNT(*) FROM movimientos_mee "
            " WHERE UPPER(mee_codigo)=UPPER(?) AND COALESCE(anulado,0)=0",
            (codigo,)).fetchone()[0] or 0)
    finally:
        cn.close()


def _stock_gate(codigo):
    """Lo que ve el gate del envasado: la suma del kardex, y SÓLO si no hay ni un movimiento,
    el cache `maestro_mee.stock_actual` (saldo de apertura)."""
    if _hay_movimientos(codigo):
        return max(_suma_kardex(codigo), 0.0)
    cn = _cn()
    try:
        r = cn.execute("SELECT COALESCE(stock_actual,0) FROM maestro_mee WHERE codigo=?",
                       (codigo,)).fetchone()
        return float(r[0] or 0) if r else 0.0
    finally:
        cn.close()


def _drenar():
    """Deja las cuatro piezas como las deja una corrida anterior del demo: CON movimientos y
    con saldo CERO.

    ⚠ Las dos mitades importan. Insertar sólo la Salida no alcanza en una base recién creada:
    ahí no hay nada que drenar, quedarían cero movimientos, el canónico caería al cache y el
    test estaría midiendo justo el caso que NO falla (M152). Por eso se fuerza que haya
    movimientos y que su suma dé cero, que es el estado real del demo en producción.
    """
    cn = _cn()
    try:
        for cod in CODIGOS:
            saldo = max(_suma_kardex(cod), 0.0)
            for tipo, cant in (("Entrada", 1), ("Salida", saldo + 1)):
                cn.execute(
                    "INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, lote_ref, "
                    "                             responsable, fecha, estado, observaciones) "
                    "VALUES (?, ?, ?, ?, 'test', datetime('now','utc'), 'VIGENTE', "
                    "        'drenado por el test de doble caminata')",
                    (cod, tipo, cant, LOTE))
        cn.commit()
    finally:
        cn.close()


def _camina(cli):
    """Los tres pasos que aprieta el usuario, por los endpoints REALES."""
    r = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h())
    assert r.status_code == 200, ("paso 1 falló: %s" % r.data[:400])
    d = r.get_json()
    cam = d.get("caminar") or {}

    r = cli.post("/api/envasado", headers=_h(), json={
        "lote": d["lote"], "producto": d["producto"], "presentacion": cam["presentacion"],
        "batch_g": cam["batch_g"], "unidades": cam["unidades"],
        "envase_codigo": cam["envase_codigo"], "tapa_codigo": cam["tapa_codigo"],
        "observaciones": "Envasado del demo de planta"})
    assert r.status_code in (200, 201), (
        "paso 2 falló · %s · %s" % (r.status_code, r.get_data(as_text=True)[:500]))

    r = cli.post("/api/acondicionamiento", headers=_h(), json={
        "lote": d["lote"], "producto": d["producto"], "presentacion": cam["presentacion"],
        "batch_g": cam["batch_g"], "unidades": cam["unidades"],
        "observaciones": "Acondicionamiento del demo de planta",
        "mee_consumido": [{"codigo": cam["etiqueta_codigo"], "cantidad": cam["unidades"]},
                          {"codigo": cam["caja_codigo"], "cantidad": cam["unidades"]}]})
    assert r.status_code in (200, 201), (
        "paso 3 falló · %s · %s" % (r.status_code, r.get_data(as_text=True)[:500]))
    return d


def test_el_demo_repone_el_stock_de_envases_como_MOVIMIENTO(app, db_clean):
    """Sembrar el cache no alcanza: el gate mide la suma del kardex."""
    cli = _login(app)
    _drenar()
    for cod in CODIGOS:
        assert _hay_movimientos(cod) > 0 and _stock_gate(cod) == 0, (
            "%s no quedó en el estado que tiene el demo ya caminado (movimientos, saldo 0)" % cod)

    assert cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).status_code == 200

    for cod in CODIGOS:
        assert _suma_kardex(cod) > 0, (
            "%s sigue en CERO en el KARDEX después de crear el demo · el demo repone el cache "
            "pero el envasado mide SUM(movimientos_mee)" % cod)
        assert _stock_gate(cod) >= 30, (
            "%s no alcanza para las 30 unidades que el demo va a envasar" % cod)


def test_el_demo_se_puede_caminar_DOS_veces_seguidas(app, db_clean):
    """La segunda vuelta es la que fallaba en producción."""
    cli = _login(app)
    _camina(cli)

    # como lo dejaría una corrida anterior: kardex drenado, cache lleno
    _drenar()

    _camina(cli)


def test_la_pagina_del_demo_DICE_por_que_fallo(app):
    """El 422 trae el motivo real y la página lo tiraba.

    Mostraba sólo el titular (*"No se puede registrar el envasado"*), así que el que camina el
    demo veía que algo falló y nunca por qué -- teniendo el endpoint el código, el stock que hay,
    el que pide y lo que falta en la misma respuesta (M124: lo que un cálculo excluye, se
    enumera).
    """
    import re
    cli = _login(app)
    html = cli.get("/admin/planta-demo").get_data(as_text=True)
    js = re.sub(r"//.*", "", html)          # sin comentarios: el guard no se encuentra a sí mismo (M154)

    assert "d.errores" in js, "la página no lee el detalle `errores` del 422"
    for campo in ("stock_disponible", "requerido", "falta"):
        assert campo in js, "la página no muestra `%s`, que es el número que explica el rechazo" % campo

    # y los tres pasos tienen que usarlo: si uno se queda con `d.error` pelado, ese vuelve a ser mudo
    mudos = re.findall(r"pinta\('ok\d',\s*r\.d\.error", js)
    assert not mudos, "hay pasos que siguen mostrando sólo el titular: %s" % mudos
