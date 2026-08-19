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
