# -*- coding: utf-8 -*-
"""Acondicionamiento no puede descontar el mismo envase DOS veces por dos caminos distintos.

Hay dos rutas que sacan material de acondicionamiento del kardex:

  · `POST /api/brd/ebr/<id>/cerrar-acondicionamiento`  (canónica) — reclama el libro mayor
    `produccion_checklist.consumido_at` con CAS antes de descontar.
  · `POST /api/acondicionamiento`                      (legacy)   — descontaba directo: escribía
    la Salida y bajaba `maestro_mee.stock_actual` sin mirar el libro mayor, sin CAS y sin audit.

La legacy NO es código muerto: el dashboard le hace POST desde tres lugares. Así que registrar
el acondicionamiento en esa pantalla y además cerrar el legajo OA sacaba el envase **dos veces**,
y el segundo descuento era invisible para el libro mayor que existe justamente para impedirlo.

Es M162 en su tercer camino: *dos candados distintos para el MISMO hecho no son dos protecciones,
son un doble descuento esperando*. Y un doble descuento no da síntoma -- el kardex simplemente
dice menos de lo que hay --, así que sólo lo caza un test que recorra los DOS endpoints (M172).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

COD = "ZZ-OA-DOBLE"


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _q1(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def _salidas():
    return _q1("SELECT COUNT(*), COALESCE(SUM(cantidad),0) FROM movimientos_mee "
               " WHERE mee_codigo=? AND tipo='Salida'", (COD,))


def _sembrar(lote="OADOB1"):
    """Un lote de acondicionamiento con su libro mayor, armado como lo arma la app.

    Limpia ANTES (no después): un `finally` no corre si el proceso muere, y limpiar antes es
    idempotente por construcción (M103). El producto lleva el lote en el nombre porque
    `mbr_templates` es UNIQUE por (producto, versión) y los tres casos sembrarían el mismo.
    """
    prod = "ZZ-OA-DOBLE-%s" % lote
    # ⚠ produccion_id PROPIO por caso: con uno compartido, el checklist que el caso anterior
    #   dejó marcado como consumido hace que el cierre salte SIN haber medido nada -- el test
    #   pasaba por la razón equivocada (M152).
    #   `hash()` NO sirve para esto: varía entre corridas (PYTHONHASHSEED) y un id que cambia
    #   solo es la firma de un test no determinista (M133).
    pid = 4242 + sum(ord(ch) for ch in lote)
    for sql, p in (
            ("DELETE FROM movimientos_mee WHERE mee_codigo=?", (COD,)),
            ("DELETE FROM produccion_checklist WHERE producto_nombre=? OR produccion_id=?", (prod, pid)),
            ("DELETE FROM acondicionamiento WHERE lote=?", (lote,)),
            ("DELETE FROM maestro_mee WHERE codigo=?", (COD,))):
        _exec(sql, p)
    _exec("INSERT INTO maestro_mee (codigo, descripcion, stock_actual, estado) "
          "VALUES (?, 'Caja de acondicionamiento', 5000, 'Activo')", (COD,))
    prod_id = _exec(
        "INSERT INTO produccion_checklist (produccion_id, producto_nombre, fecha_planeada, "
        " item_tipo, descripcion, cantidad_requerida, mee_codigo_asignado) "
        "VALUES (?, ?, date('now'), 'caja_exterior', 'Caja', 100, ?)",
        (pid, prod, COD))
    assert prod_id
    mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                   "VALUES (?, 1, 'aprobado', 1000, 'sebastian')", (prod,))
    ebr_id = _exec(
        "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, estado, fase, "
        " produccion_id, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
        "VALUES (?, 1, ?, ?, 'iniciado', 'acondicionamiento', ?, 'sebastian', "
        " datetime('now','utc'), 1000)", (mbr_id, lote + "-OA", lote, pid))
    return ebr_id, lote, prod, pid


def test_el_legajo_y_la_pantalla_vieja_no_descuentan_dos_veces(app, db_clean):
    """El caso real: el operario cierra el legajo OA y además registra el acondicionamiento."""
    ebr_id, lote, prod, pid = _sembrar()
    c = _login(app)

    r = c.post("/api/brd/ebr/%d/cerrar-acondicionamiento" % ebr_id,
               json={"materiales": [{"codigo": COD, "cantidad": 100}]}, headers=_h())
    assert r.status_code == 200, r.data
    assert r.get_json().get("n_descuentos") == 1, r.data
    n, total = _salidas()
    assert (n, total) == (1, 100), ("el cierre canónico descontó una vez", n, total)

    # el mismo material, por la pantalla vieja, para la MISMA producción
    r2 = c.post("/api/acondicionamiento",
                json={"produccion_id": pid, "lote": lote, "producto": prod,
                      "unidades": 100, "batch_g": 1000,
                      "mee_consumido": [{"codigo": COD, "cantidad": 100}]}, headers=_h())
    assert r2.status_code in (200, 201), r2.data

    n2, total2 = _salidas()
    assert (n2, total2) == (1, 100), (
        "el envase salió del kardex DOS veces: el registro de acondicionamiento no miró el "
        "libro mayor que el cierre del legajo ya había reclamado (M162)", n2, total2)
    # y el registro queda igual: lo que no descuenta es el material ya consumido, no el acto
    assert _q1("SELECT COUNT(*) FROM acondicionamiento WHERE lote=?", (lote,))[0] == 1


def test_la_pantalla_vieja_descuenta_cuando_es_ELLA_la_primera(app, db_clean):
    """Dientes del otro lado: coordinar no puede volverse 'no descontar nunca'.

    Si el operario registra el acondicionamiento ANTES de cerrar el legajo, ese material SÍ tiene
    que salir del kardex -- y el cierre posterior no debe volver a sacarlo.
    """
    ebr_id, lote, prod, pid = _sembrar("OADOB2")
    c = _login(app)

    r = c.post("/api/acondicionamiento",
               json={"produccion_id": pid, "lote": lote, "producto": prod,
                     "unidades": 100, "batch_g": 1000,
                     "mee_consumido": [{"codigo": COD, "cantidad": 100}]}, headers=_h())
    assert r.status_code in (200, 201), r.data
    n, total = _salidas()
    assert (n, total) == (1, 100), ("la pantalla vieja tiene que descontar si llega primero", n, total)

    r2 = c.post("/api/brd/ebr/%d/cerrar-acondicionamiento" % ebr_id,
                json={"materiales": [{"codigo": COD, "cantidad": 100}]}, headers=_h())
    assert r2.status_code == 200, r2.data
    j = r2.get_json()
    assert j.get("n_descuentos") == 0, ("ya estaba consumido: no se descuenta de nuevo", j)
    assert j.get("saltados"), ("lo que no se descuenta se DECLARA, no desaparece del informe", j)

    n2, total2 = _salidas()
    assert (n2, total2) == (1, 100), ("doble descuento por el orden inverso", n2, total2)


def test_sin_libro_mayor_descuenta_igual_y_lo_DECLARA(app, db_clean):
    """Un lote sin checklist (no hay libro mayor que reclamar) tiene que seguir descontando.

    Que un envase NO salga del kardex es peor que arriesgar el doble: se descuenta y se declara,
    para que un descuadre futuro no aparezca sin explicación (M100/M124).
    """
    _ebr, _lt, prod, pid = _sembrar("OADOB3")
    _exec("DELETE FROM produccion_checklist WHERE producto_nombre=?", (prod,))
    c = _login(app)
    r = c.post("/api/acondicionamiento",
               json={"produccion_id": pid, "lote": "OADOB3", "producto": prod,
                     "unidades": 50, "batch_g": 500,
                     "mee_consumido": [{"codigo": COD, "cantidad": 50}]}, headers=_h())
    assert r.status_code in (200, 201), r.data
    j = r.get_json()
    n, total = _salidas()
    assert (n, total) == (1, 50), ("sin libro mayor igual tiene que descontar", n, total)
    assert j.get("sin_libro_mayor") is True, ("tiene que DECIR que no pudo coordinar", j)
