# -*- coding: utf-8 -*-
"""Las dos mitades del legajo de envasado no se pueden contradecir.

Caminando el lote completo en producción, el MISMO legajo decía:

    Lotes de Producto por Presentación   DEMO30 · DEMO-PLANTA-1 · 30 unidades · Completado
    Conciliación del Granel              − Envasado · "Sin unidades registradas todavía" · 0 mL

Tres centímetros de distancia, el mismo hecho, dos respuestas opuestas. El que mira no tiene
forma de saber cuál creer, y termina no creyéndole a ninguna de las dos (M161).

La causa es la de siempre: **las unidades se registran por DOS caminos** -- `POST /api/envasado`
(la pantalla que usa la planta) escribe en `envasado`, y el formulario del propio legajo escribe
en `ebr_envasado_unidades` -- y `_conciliacion_granel` leía sólo el segundo. El CIERRE del
envasado ya tenía este arreglo desde el 17-ago; este hermano quedó vivo (M45).

⚠ Lo que este test también fija, y es la parte delicada: la conciliación se cae a lo REGISTRADO,
nunca a las presentaciones PLANEADAS. Conciliar el granel contra un plan daría un rendimiento
inventado sobre unidades que nadie llenó.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

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


def _sin_envasado_previo():
    """El demo es idempotente, registrar el envasado NO: sin esto una corrida anterior dejaría
    las unidades puestas y el test pasaría sin haber caminado nada (M152)."""
    cn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        # El demo rota de lote cuando el anterior quedo LIBERADO (inmutable · Part 11),
        # asi que limpiar por el nombre fijo dejaria las filas de la corrida anterior
        # y el test mediria eso en vez del flujo. Se limpia por PREFIJO.
        cn.execute("DELETE FROM envasado WHERE lote LIKE 'DEMO-PLANTA%'")
        cn.commit()
    finally:
        cn.close()


def test_la_conciliacion_ve_las_unidades_que_registro_la_planta(app, db_clean):
    cli = _login(app)
    _sin_envasado_previo()

    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    cam = d.get("caminar") or {}
    of = d["envasado_ebr"]

    # antes de envasar, la conciliación DEBE decir que no hay unidades · si dijera un número
    # acá, estaría contando un plan (M226)
    v = cli.get("/api/brd/ebr/%d/vista-completa" % of).get_json() or {}
    cg = v.get("conciliacion_granel") or {}
    assert not (cg.get("presentaciones") or []), (
        "la conciliación cuenta unidades ANTES de que se envase · está contando lo PLANEADO", cg)

    r = cli.post("/api/envasado", headers=_h(), json={
        "lote": d["lote"], "producto": d["producto"], "presentacion": cam["presentacion"],
        "batch_g": cam["batch_g"], "unidades": cam["unidades"],
        "envase_codigo": cam["envase_codigo"], "tapa_codigo": cam["tapa_codigo"],
        "observaciones": "Envasado del demo de planta"})
    assert r.status_code in (200, 201), r.get_data(as_text=True)[:400]

    v = cli.get("/api/brd/ebr/%d/vista-completa" % of).get_json() or {}
    arriba = v.get("envasado_presentaciones") or []
    cg = v.get("conciliacion_granel") or {}
    abajo = cg.get("presentaciones") or []

    uds_arriba = sum(int(p.get("unidades") or 0) for p in arriba)
    uds_abajo = sum(float(p.get("unidades") or 0) for p in abajo)

    assert uds_arriba == cam["unidades"], ("la tabla de arriba perdió las unidades", arriba)
    assert abajo, (
        "la Conciliación del Granel dice 'Sin unidades registradas todavía' mientras la tabla "
        "de arriba del MISMO legajo lista %d unidades" % uds_arriba)
    assert uds_abajo == uds_arriba, (
        "las dos mitades del legajo cuentan distinto: arriba %s, en la conciliación %s"
        % (uds_arriba, uds_abajo))
    assert float(cg.get("envasado_ml") or 0) > 0, (
        "la conciliación sigue en 0 mL con %d unidades de %s registradas"
        % (uds_arriba, cam["presentacion"]))


def test_la_conciliacion_declara_lo_que_no_puede_pesar(app, db_clean):
    """Sin volumen no se inventa: se cuenta como presentación sin volumen y se DECLARA.

    Un cero mudo se lee como 'no se envasó nada', que es lo contrario de 'no se pudo convertir'
    (M100/M124).
    """
    cli = _login(app)
    _sin_envasado_previo()

    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    cam = d.get("caminar") or {}
    of = d["envasado_ebr"]

    cn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cn.execute("UPDATE producto_presentaciones SET volumen_ml=0 "
                   " WHERE producto_nombre=? AND presentacion_codigo=?",
                   (d["producto"], cam["presentacion"]))
        cn.commit()
        cli.post("/api/envasado", headers=_h(), json={
            "lote": d["lote"], "producto": d["producto"], "presentacion": cam["presentacion"],
            "batch_g": cam["batch_g"], "unidades": cam["unidades"],
            "envase_codigo": cam["envase_codigo"], "tapa_codigo": cam["tapa_codigo"]})
        cg = (cli.get("/api/brd/ebr/%d/vista-completa" % of).get_json()
              or {}).get("conciliacion_granel") or {}
        assert int(cg.get("presentaciones_sin_volumen") or 0) > 0, (
            "sin volumen la conciliación tiene que DECLARARLO, no devolver un cero mudo", cg)
    finally:
        cn.execute("UPDATE producto_presentaciones SET volumen_ml=30 "
                   " WHERE producto_nombre=? AND presentacion_codigo=?",
                   (d["producto"], cam["presentacion"]))
        cn.commit()
        cn.close()
