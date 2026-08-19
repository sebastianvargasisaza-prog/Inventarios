# -*- coding: utf-8 -*-
"""La tarjeta de Acondicionamiento no puede decir "sin unidades" con el trabajo hecho.

Sebastián lo vio en su pantalla: la tarjeta del legajo decía **"⚠ Sin unidades registradas
todavía"** y tres renglones más abajo, en la MISMA pantalla, el historial mostraba
**DEMO-PLANTA-1 · 30 uds**. Dos partes de la misma vista contradiciéndose sobre el mismo hecho
(M161).

La causa es la de siempre: `ordenes-unificadas` leía las unidades de `ebr_envasado_unidades` --
que es del ENVASADO -- para las DOS fases, y lo que registra `POST /api/acondicionamiento` vive
en la tabla `acondicionamiento`. Un hecho que entra por dos puertas y un lector que conoce una
sola (M37 · tercera vez el mismo día).

Y el otro que arregló la misma captura: **"Abrir legajo" no abría**. El renderizador de tarjetas
se comparte entre las dos fases y el botón pasaba SIEMPRE `envasado-runner`. Ese contenedor
existe (vive en la pestaña de al lado), así que el legajo se pintaba dentro de un panel OCULTO:
peor que un no-op, porque el trabajo se hace y no se ve, y no hay error que mirar (M112/M166).
"""
import re

from .conftest import TEST_PASSWORD, csrf_headers


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_la_tarjeta_cuenta_las_unidades_que_registro_la_planta(app, db_clean):
    cli = _login(app)
    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    cam = d.get("caminar") or {}
    oa = d["acondicionamiento_ebr"]

    # Registrar el acondicionamiento NO es idempotente: una corrida anterior sobre el
    # mismo lote dejaria sus unidades puestas y la tarjeta contaria el DOBLE, o sea que
    # el test pasaria (o fallaria) por algo que no es lo que mide (M103 · limpiar ANTES).
    import os as _o
    import sqlite3 as _s
    _c = _s.connect(_o.environ["DB_PATH"], timeout=10.0)
    try:
        _c.execute("DELETE FROM acondicionamiento WHERE lote=?", (d["lote"],))
        _c.commit()
    finally:
        _c.close()

    r = cli.post("/api/acondicionamiento", headers=_h(), json={
        "lote": d["lote"], "producto": d["producto"], "presentacion": cam["presentacion"],
        "batch_g": cam["batch_g"], "unidades": cam["unidades"],
        "mee_consumido": [{"codigo": cam["etiqueta_codigo"], "cantidad": cam["unidades"]}]})
    assert r.status_code in (200, 201), r.get_data(as_text=True)[:300]

    j = cli.get("/api/brd/ordenes-unificadas?fase=acondicionamiento").get_json() or {}
    fila = [o for o in (j.get("ordenes") or []) if o.get("ebr_id") == oa]
    assert fila, ("el legajo no aparece en la lista", j)
    assert int(fila[0].get("unidades_total") or 0) == cam["unidades"], (
        "la tarjeta dice que no hay unidades con el acondicionamiento registrado: eso es lo que "
        "hace que la pantalla se contradiga con su propio historial", fila[0])


def test_abrir_legajo_lleva_a_la_pantalla_de_ESTA_fase(app, db_clean):
    """El botón no puede abrir el runner de la fase de al lado, que está oculto."""
    cli = _login(app)
    html = cli.get("/inventarios").get_data(as_text=True)
    for src in set(re.findall(r'<script[^>]+src="(/[^"]+\.js[^"]*)"', html)):
        rb = cli.get(src)
        if rb.status_code == 200:
            html += rb.get_data(as_text=True)

    i = html.find("function ordenesRenderLista")
    assert i > 0, "no encontré el renderizador compartido de tarjetas"
    m = re.search(r"\n(?:async )?function ", html[i + 30:])
    cuerpo = html[i:i + 30 + (m.start() if m else 4000)]
    cuerpo = re.sub(r"//.*", "", cuerpo)      # sin comentarios (M154)

    i2 = cuerpo.find("legajo-acondicionamiento/")
    assert i2 > 0, "el botón de la tarjeta no lleva a la pantalla de acondicionamiento"

    # ⚠ No alcanza con que el enlace EXISTA: con la condición neutralizada seguiría en el
    # texto, dentro de una rama muerta, y el guard pasaría verde con el bug puesto (M96).
    # Lo que importa es que el enlace esté BAJO la condición de fase.
    previo = cuerpo[max(0, i2 - 700):i2].replace(" ", "").replace('"', "'")
    assert "fase==='acondicionamiento'" in previo, (
        "el enlace al legajo de acondicionamiento no está guardado por la fase: desde "
        "acondicionamiento volvería a abrir el runner de envasado, que está oculto")


# ── El CIERRE del acondicionamiento se mide en UNIDADES ──────────────────────────
#
# El botón decía "(g, opcional · Enter para usar el objetivo)" y `completar_ebr` cortaba
# con `400 · cantidad_real_g debe ser > 0` sin excepción: darle Enter daba error SIEMPRE
# (M233 · el campo anuncia lo contrario de lo que el guard exige). Y de fondo le pedía
# GRAMOS a la fase que produce UNIDADES etiquetadas (M205/M214), que es por lo que
# acondicionamiento llevaba 0 lotes caminados de verdad: el último paso no se podía
# cerrar sin inventar un número.

import os as _os
import sqlite3 as _sq


def _cnx():
    return _sq.connect(_os.environ["DB_PATH"], timeout=10.0)


def _demo_acondicionado(cli):
    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    cam = d.get("caminar") or {}
    cn = _cnx()
    try:
        cn.execute("DELETE FROM acondicionamiento WHERE lote=?", (d["lote"],))
        cn.commit()
    finally:
        cn.close()
    r = cli.post("/api/acondicionamiento", headers=_h(), json={
        "lote": d["lote"], "producto": d["producto"], "presentacion": cam["presentacion"],
        "batch_g": cam["batch_g"], "unidades": cam["unidades"],
        "mee_consumido": [{"codigo": cam["etiqueta_codigo"], "cantidad": cam["unidades"]}]})
    assert r.status_code in (200, 201), r.get_data(as_text=True)[:300]
    return d, cam


def test_cerrar_sin_teclear_nada_usa_lo_REGISTRADO(app, db_clean):
    cli = _login(app)
    d, cam = _demo_acondicionado(cli)
    r = cli.post("/api/brd/ebr/%d/completar" % d["acondicionamiento_ebr"],
                 json={}, headers=_h())
    assert r.status_code == 200, (
        "el botón promete cerrar con Enter y el endpoint lo rechaza: el operario no "
        "tiene forma de terminar el lote", r.get_data(as_text=True)[:200])
    cn = _cnx()
    try:
        real = cn.execute("SELECT cantidad_real_g FROM ebr_ejecuciones WHERE id=?",
                          (d["acondicionamiento_ebr"],)).fetchone()[0]
    finally:
        cn.close()
    assert abs(float(real) - float(cam["batch_g"])) < 1.0, (
        "cerró con una cantidad que no es la registrada por la planta", real,
        cam["batch_g"])


def test_cerrar_por_UNIDADES_reescala_con_el_factor_real_del_lote(app, db_clean):
    cli = _login(app)
    d, cam = _demo_acondicionado(cli)
    uds = max(1, int(cam["unidades"]) // 3)
    r = cli.post("/api/brd/ebr/%d/completar" % d["acondicionamiento_ebr"],
                 json={"unidades": uds}, headers=_h())
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    esperado = float(cam["batch_g"]) / float(cam["unidades"]) * uds
    cn = _cnx()
    try:
        real = cn.execute("SELECT cantidad_real_g FROM ebr_ejecuciones WHERE id=?",
                          (d["acondicionamiento_ebr"],)).fetchone()[0]
    finally:
        cn.close()
    assert abs(float(real) - esperado) < 1.0, (
        "las unidades no se convirtieron con el factor real del lote", real, esperado)


def test_sin_nada_registrado_NO_cierra_a_ciegas(app, db_clean):
    """Cerrar con un número inventado falsea el rendimiento, que es lo que se audita."""
    cli = _login(app)
    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    cn = _cnx()
    try:
        cn.execute("DELETE FROM acondicionamiento WHERE lote=?", (d["lote"],))
        cn.execute("UPDATE ebr_ejecuciones SET cantidad_objetivo_g=0 WHERE id=?",
                   (d["acondicionamiento_ebr"],))
        cn.commit()
    finally:
        cn.close()
    r = cli.post("/api/brd/ebr/%d/completar" % d["acondicionamiento_ebr"],
                 json={"unidades": 10}, headers=_h())
    assert r.status_code == 400, r.status_code
    j = r.get_json() or {}
    assert j.get("codigo") == "SIN_CANTIDAD", j
    assert "unidades" in (j.get("error") or "").lower(), (
        "el rechazo no dice qué hacer", j)


def test_la_pantalla_pide_UNIDADES_no_gramos(app, db_clean):
    """El texto del botón y el guard tienen que decir lo mismo (M233)."""
    import ast as _ast
    import io as _io
    import re as _re
    ruta = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                         "api", "blueprints", "brd.py")
    src = _io.open(ruta, encoding="utf-8").read()
    val = None
    for n in _ast.walk(_ast.parse(src)):
        if (isinstance(n, _ast.Assign) and isinstance(n.value, _ast.Constant)
                and isinstance(n.value.value, str)
                and isinstance(n.targets[0], _ast.Name)
                and n.targets[0].id == "_ACOND_LEGAJO_HTML"):
            val = n.value.value
            break
    assert val, "no encontré el legajo de acondicionamiento"

    i = val.find("function terminarLote")
    assert i > 0, "el legajo ya no tiene el botón de terminar"
    m = _re.search(r"\n(?:async )?function ", val[i + 25:])
    cuerpo = val[i:i + 25 + (m.start() if m else 2000)]
    # Sin comentarios: el que explica POR QUÉ ya no van gramos contiene la palabra
    # 'gramos' y el guard se encontraría a sí mismo (M154).
    cuerpo = _re.sub(r"//.*", "", cuerpo)

    j = cuerpo.find("prompt(")
    assert j > 0, "el cierre dejó de preguntar"
    pregunta = cuerpo[j:j + 200].lower()
    assert "unidades" in pregunta, ("el cierre del acondicionamiento sigue pidiendo la "
                                    "magnitud de otra fase", pregunta[:120])
    assert "body.unidades" in cuerpo, "pregunta por unidades y manda otra cosa"
