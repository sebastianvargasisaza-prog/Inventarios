# -*- coding: utf-8 -*-
"""El demo se puede CAMINAR hasta envasado y acondicionamiento, y las pantallas se llenan.

Sebastián: *"sería bueno un demo en envasado y otro en acondicionamiento para ver cómo se ven"*.

Y tenía razón en el diagnóstico: el demo creaba los tres legajos, pero **nadie caminaba las dos
últimas fases**, así que sus dos secciones centrales abrían VACÍAS -- medido antes de tocar nada:

    envasado          unidades por presentación 0 · materiales de envase 0
    acondicionamiento unidades 0 · materiales de empaque 0

Esas listas no salen de una tabla del legajo: salen de un envasado y un acondicionamiento
REGISTRADOS. Por eso el demo no las siembra a mano -- mostraría una pantalla que nadie llenó así
(M153) --, sino que se camina por los MISMOS endpoints que usa la planta, que es exactamente lo
que hace el botón de `/admin/planta-demo`.

Este test recorre lo mismo que aprieta el usuario, en el mismo orden.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


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


def _limpiar():
    """El demo es idempotente pero el ENVASADO no: si quedó uno de otra corrida, las listas ya
    vendrían llenas y el test pasaría sin haber caminado nada (M152)."""
    cn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        # ⚠ NO se borra `movimientos_mee`: borrarlo dejaba el kardex del demo sin un solo
        # movimiento, y ahí el stock CANÓNICO cae al cache `maestro_mee.stock_actual` (M26).
        # O sea que el fixture reproducía justo la condición que escondía el bug que Sebastián
        # encontró caminando el demo en producción -- ahí sí hay Salidas y la caída no aplica
        # (M153/M229). El demo repone su stock de envases como MOVIMIENTO, así que no hace falta.
        for q in ("DELETE FROM envasado WHERE lote='DEMO-PLANTA-1'",
                  "DELETE FROM acondicionamiento WHERE lote='DEMO-PLANTA-1'"):
            try:
                cn.execute(q)
            except Exception:
                pass
        cn.commit()
    finally:
        cn.close()


def _vista(cli, ebr_id):
    return cli.get("/api/brd/ebr/%d/vista-completa" % ebr_id).get_json() or {}


def test_el_demo_camina_hasta_acondicionamiento_y_las_pantallas_se_llenan(app, db_clean):
    _limpiar()
    cli = _login(app)

    # ── paso 1 · el lote ─────────────────────────────────────────────────────────────────
    r = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h())
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    cam = d.get("caminar") or {}
    assert cam.get("presentacion") and cam.get("etiqueta_codigo"), (
        "el demo no dice CON QUÉ caminarlo · la página no podría llamar a los endpoints", d)

    of, oa = d["envasado_ebr"], d["acondicionamiento_ebr"]

    # las dos pantallas arrancan vacías: es el punto de partida que este demo viene a resolver
    v = _vista(cli, of)
    assert v.get("envasado_presentaciones") == [], ("arranca vacío", v.get("envasado_presentaciones"))

    # ── paso 2 · envasado, por el endpoint REAL ──────────────────────────────────────────
    r = cli.post("/api/envasado", headers=_h(), json={
        "lote": d["lote"], "producto": d["producto"], "presentacion": cam["presentacion"],
        "batch_g": cam["batch_g"], "unidades": cam["unidades"],
        "envase_codigo": cam["envase_codigo"], "tapa_codigo": cam["tapa_codigo"],
        "observaciones": "Envasado del demo de planta"})
    assert r.status_code in (200, 201), r.data[:300]

    v = _vista(cli, of)
    pres = v.get("envasado_presentaciones") or []
    assert pres, "el legajo de envasado sigue SIN unidades por presentación después de envasar"
    assert int(pres[0].get("unidades") or 0) == cam["unidades"], pres[0]
    assert v.get("envasado_materiales"), "el legajo de envasado sigue SIN materiales de envase"

    # ── paso 3 · acondicionamiento, por el endpoint REAL ─────────────────────────────────
    r = cli.post("/api/acondicionamiento", headers=_h(), json={
        "lote": d["lote"], "producto": d["producto"], "presentacion": cam["presentacion"],
        "batch_g": cam["batch_g"], "unidades": cam["unidades"],
        "observaciones": "Acondicionamiento del demo de planta",
        "mee_consumido": [{"codigo": cam["etiqueta_codigo"], "cantidad": cam["unidades"]},
                          {"codigo": cam["caja_codigo"], "cantidad": cam["unidades"]}]})
    assert r.status_code in (200, 201), r.data[:300]
    ja = r.get_json()
    assert len(ja.get("descuentos") or []) == 2, ("la etiqueta y el estuche tienen que salir del "
                                                  "kardex", ja)

    v = _vista(cli, oa)
    assert v.get("acond_presentaciones"), "el legajo de acondicionamiento sigue SIN unidades"
    assert v.get("acond_materiales"), "el legajo de acondicionamiento sigue SIN material de empaque"


def test_el_demo_siembra_las_CUATRO_piezas_del_empaque(app, db_clean):
    """Sin tapa, caja y etiqueta en el maestro, las dos pantallas no tienen qué mostrar."""
    cli = _login(app)
    assert cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).status_code == 200
    cn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        hay = {r[0] for r in cn.execute(
            "SELECT codigo FROM maestro_mee WHERE codigo IN "
            "('ENV-DEMO','TAPA-DEMO','CAJA-DEMO','ETIQ-DEMO')").fetchall()}
        pres = cn.execute("SELECT COALESCE(tapa_codigo,''), COALESCE(caja_codigo,'') "
                          "  FROM producto_presentaciones WHERE producto_nombre=?",
                          ("DEMO PLANTA (BORRAR)",)).fetchone()
    finally:
        cn.close()
    assert hay == {"ENV-DEMO", "TAPA-DEMO", "CAJA-DEMO", "ETIQ-DEMO"}, hay
    assert pres and pres[0] and pres[1], ("la presentación del demo tiene que declarar su tapa y "
                                          "su caja, o el legajo no las lista", pres)


def test_la_pagina_del_demo_ofrece_las_tres_fases(app):
    """Una capacidad a la que nadie puede llegar no existe (M121): los botones tienen que estar
    en la pantalla, y cada uno llamar a una función que existe (M166)."""
    import re
    cli = _login(app)
    html = cli.get("/admin/planta-demo").get_data(as_text=True)
    assert "Caminar envasado" in html and "Caminar acondicionamiento" in html, (
        "la página del demo no ofrece caminar las dos fases")
    llamadas = sorted(set(re.findall(r'onclick="([A-Za-z_$][\w$]*)\(', html)))
    faltan = [f for f in llamadas if not re.search(r'(var|function)\s+' + f + r'\b', html)]
    assert not faltan, "botones que llaman a algo que no existe: %s" % faltan
    assert "/api/envasado" in html and "/api/acondicionamiento" in html, (
        "el demo tiene que caminar por los endpoints REALES, no por una ruta propia")
