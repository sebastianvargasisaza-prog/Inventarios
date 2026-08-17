# -*- coding: utf-8 -*-
"""UN lote atravesando las TRES fases, en orden, por los endpoints reales.

Sebastián, 17-ago: *"como no habíamos completado fabricación ni envasado, nunca se ha usado
completamente todo el flujo, por eso quiero ver que es perfecto"*.

Y es cierto: hay E2E de cada fase por separado (`test_ebr_e2e_demo`, `test_ebr_e2e_envasado_acond`)
y los tres están en el gate, pero **ninguno recorre el mismo lote de punta a punta**. Todo lo que
vive ENTRE las fases quedaba sin ejercer:

  · que liberar fabricación HABILITE el envasado del mismo lote,
  · que cerrar el envasado HABILITE el acondicionamiento,
  · y sobre todo que el inventario cuadre al final, con **cada material saliendo UNA vez**
    aunque tres cierres distintos toquen el mismo lote.

Ese último es el que importa: el doble descuento no da síntoma -- el kardex simplemente dice
menos de lo que hay (M162/M172) -- y sólo aparece mirando el lote entero.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

LOTE = "DEMO-PLANTA-1"
MEE = ("ENV-DEMO", "TAPA-DEMO", "CAJA-DEMO", "ETIQ-DEMO")


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


def _sql(q, p=()):
    cn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = cn.execute(q, p)
        cn.commit()
        return cur.fetchall()
    finally:
        cn.close()


def _salidas_por_codigo():
    filas = _sql("SELECT mee_codigo, COUNT(*), COALESCE(SUM(cantidad),0) "
                 "  FROM movimientos_mee WHERE tipo='Salida' AND mee_codigo IN (?,?,?,?) "
                 " GROUP BY mee_codigo", MEE)
    return {r[0]: (r[1], r[2]) for r in filas}


def _limpiar():
    """Registrar un envasado NO es idempotente: una corrida anterior dejaría el lote ya
    caminado y este test pasaría sin haber recorrido nada (M152/M103 · limpiar ANTES)."""
    _sql("DELETE FROM envasado WHERE lote=?", (LOTE,))
    _sql("DELETE FROM acondicionamiento WHERE lote=?", (LOTE,))
    _sql("DELETE FROM movimientos_mee WHERE mee_codigo IN (?,?,?,?)", MEE)
    # `crear_planta_demo` REUSA los legajos, así que uno cerrado por el caso anterior devuelve
    # 409 YA_CERRADO y el caso siguiente mediría el rechazo en vez del flujo (M102).
    _sql("UPDATE ebr_ejecuciones SET estado='iniciado', envases_descontados_at=NULL, "
         "       completado_at_utc=NULL "
         " WHERE COALESCE(NULLIF(lote_codigo,''), lote)=? AND estado<>'liberado'", (LOTE,))


def test_un_lote_recorre_las_tres_fases_y_el_inventario_cuadra(app, db_clean):
    _limpiar()
    cli = _login(app)

    # ── el lote y sus tres legajos ────────────────────────────────────────────────────────
    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    assert d.get("ok"), d
    cam = d["caminar"]
    op, of, oa = d["fabricacion_ebr"], d["envasado_ebr"], d["acondicionamiento_ebr"]

    fases = cli.get("/api/brd/lote/%s/fases" % LOTE).get_json() or {}
    assert fases.get("total") == 3, ("el lote tiene que tener sus tres legajos", fases)
    assert [f["fase"] for f in fases["fases"]] == \
        ["fabricacion", "envasado", "acondicionamiento"], fases

    # ── FASE 1 · fabricación ──────────────────────────────────────────────────────────────
    v = cli.get("/api/brd/ebr/%d/vista-completa" % op).get_json() or {}
    assert v.get("pasos"), "el legajo de fabricación abrió sin pasos que ejecutar"
    assert v.get("pesaje_sheet"), "el legajo de fabricación abrió sin hoja de pesaje"
    for p in v["pasos"]:
        cli.post("/api/brd/ebr/%d/pasos/%s/iniciar" % (op, p["orden"]), json={}, headers=_h())
        cli.post("/api/brd/ebr/%d/pasos/%s/completar" % (op, p["orden"]),
                 json={"observaciones": "flujo completo"}, headers=_h())
    v = cli.get("/api/brd/ebr/%d/vista-completa" % op).get_json() or {}
    assert v.get("progreso_pasos_pct") == 100.0, ("los pasos no quedaron completos",
                                                  v.get("progreso_pasos_pct"))

    # ── FASE 2 · envasado, por el endpoint que usa la planta ──────────────────────────────
    r = cli.post("/api/envasado", headers=_h(), json={
        "lote": LOTE, "producto": d["producto"], "presentacion": cam["presentacion"],
        "batch_g": cam["batch_g"], "unidades": cam["unidades"],
        "envase_codigo": cam["envase_codigo"], "tapa_codigo": cam["tapa_codigo"],
        "observaciones": "flujo completo"})
    assert r.status_code in (200, 201), r.data[:300]

    v = cli.get("/api/brd/ebr/%d/vista-completa" % of).get_json() or {}
    assert v.get("envasado_presentaciones"), "el legajo de envasado no ve lo que se envasó"
    assert v.get("envasado_materiales"), "el legajo de envasado no ve sus materiales"

    # ── FASE 3 · acondicionamiento ────────────────────────────────────────────────────────
    r = cli.post("/api/acondicionamiento", headers=_h(), json={
        "lote": LOTE, "producto": d["producto"], "presentacion": cam["presentacion"],
        "batch_g": cam["batch_g"], "unidades": cam["unidades"],
        "observaciones": "flujo completo",
        "mee_consumido": [{"codigo": cam["etiqueta_codigo"], "cantidad": cam["unidades"]},
                          {"codigo": cam["caja_codigo"], "cantidad": cam["unidades"]}]})
    assert r.status_code in (200, 201), r.data[:300]

    v = cli.get("/api/brd/ebr/%d/vista-completa" % oa).get_json() or {}
    assert v.get("acond_presentaciones"), "el legajo de acondicionamiento no ve sus unidades"
    assert v.get("acond_materiales"), "el legajo de acondicionamiento no ve su material de empaque"

    # ── LO QUE SÓLO SE VE MIRANDO EL LOTE ENTERO ─────────────────────────────────────────
    # Ningún material puede haber salido dos veces por haber pasado por dos fases.
    sal = _salidas_por_codigo()
    dobles = {c: v for c, v in sal.items() if v[1] > cam["unidades"]}
    assert not dobles, (
        "algún material salió del kardex MÁS de las unidades del lote: dos fases lo "
        "descontaron por separado (M162)", sal, cam["unidades"])


def test_cerrar_el_envasado_habilita_el_acondicionamiento(app, db_clean):
    """El eslabón entre fases: el operario tiene que VER el paso siguiente al terminar.

    Antes esta cadena era manual y silenciosa -- un callejón sin salida -- y por eso se
    construyó el hook. Si se rompe, el lote se queda sin su fase final sin que nada avise.
    """
    _limpiar()
    cli = _login(app)
    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    cam = d["caminar"]

    # Primero se REGISTRA lo envasado y después se cierra: cerrar sin unidades devuelve 400 con
    # el motivo, y eso es correcto -- no se cierra un envasado que nadie registró.
    r = cli.post("/api/envasado", headers=_h(), json={
        "lote": LOTE, "producto": d["producto"], "presentacion": cam["presentacion"],
        "batch_g": cam["batch_g"], "unidades": cam["unidades"],
        "envase_codigo": cam["envase_codigo"], "tapa_codigo": cam["tapa_codigo"]})
    assert r.status_code in (200, 201), r.data[:300]

    r = cli.post("/api/brd/ebr/%d/cerrar-envasado" % d["envasado_ebr"], headers=_h(), json={})
    assert r.status_code in (200, 409), r.data[:300]
    if r.status_code == 200:
        assert r.get_json().get("acond_ebr_id"), (
            "cerrar el envasado tiene que dejar habilitado el acondicionamiento", r.get_json())

    fases = cli.get("/api/brd/lote/%s/fases" % LOTE).get_json() or {}
    assert any(f["fase"] == "acondicionamiento" for f in fases.get("fases") or []), fases


def test_registrar_y_CERRAR_el_envasado_no_descuenta_dos_veces(app, db_clean):
    """El caso que sólo aparece caminando el lote entero.

    `POST /api/envasado` saca el frasco, la tapa y la caja del kardex al guardarse. El cierre del
    legajo los sacaba OTRA VEZ: medido antes del arreglo, **60 unidades de frasco y de tapa donde
    se envasaron 30**. En un lote con producción asociada lo evita el libro mayor
    (`produccion_checklist.consumido_at`), pero un lote sin ella -- como el demo, o una fabricación
    registrada a mano -- no tenía nada que coordinara (M162).

    La regla que lo cierra es precisa: **si las unidades vienen del REGISTRO, sus materiales ya
    salieron**, así que el cierre marca completado y encadena, pero no vuelve a descontar.
    """
    _limpiar()
    cli = _login(app)
    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    cam = d["caminar"]

    r = cli.post("/api/envasado", headers=_h(), json={
        "lote": LOTE, "producto": d["producto"], "presentacion": cam["presentacion"],
        "batch_g": cam["batch_g"], "unidades": cam["unidades"],
        "envase_codigo": cam["envase_codigo"], "tapa_codigo": cam["tapa_codigo"]})
    assert r.status_code in (200, 201), r.data[:300]
    tras_registro = _salidas_por_codigo()

    r = cli.post("/api/brd/ebr/%d/cerrar-envasado" % d["envasado_ebr"], headers=_h(), json={})
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    assert j.get("materiales_ya_descontados") is True, (
        "el cierre tiene que DECIR por qué no movió el kardex, no callarlo", j)
    assert j.get("acond_ebr_id"), ("aun sin descontar, el cierre habilita el acondicionamiento", j)

    tras_cierre = _salidas_por_codigo()
    assert tras_cierre == tras_registro, (
        "el cierre volvió a descontar lo que el registro ya había sacado del kardex",
        tras_registro, tras_cierre)
    for cod, (n, total) in tras_cierre.items():
        assert total <= cam["unidades"], (cod, n, total, "más unidades que las envasadas")


def test_el_cierre_que_SI_descuenta_tambien_habilita_el_acondicionamiento(app, db_clean):
    """El otro camino del cierre: las unidades se cargan en el LEGAJO, así que ahí sí descuenta.

    Los dos caminos tienen que dejar el enlace al paso siguiente. Sin este caso, el arreglo del
    hook quedaba cubierto en uno solo -- y el guard pasaba verde con el bug puesto en el otro
    (probado: mutar esa rama no ponía nada en rojo · M96).
    """
    _limpiar()
    cli = _login(app)
    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    cam = d["caminar"]
    of = d["envasado_ebr"]

    r = cli.post("/api/brd/ebr/%d/registrar-unidades" % of, headers=_h(),
                 json={"presentacion_codigo": cam["presentacion"], "unidades": cam["unidades"]})
    assert r.status_code in (200, 201), r.data[:300]

    r = cli.post("/api/brd/ebr/%d/cerrar-envasado" % of, headers=_h(), json={})
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    assert j.get("n_descuentos", 0) > 0, ("por este camino el cierre SÍ descuenta", j)
    assert j.get("acond_ebr_id"), (
        "el cierre que descuenta también tiene que habilitar el acondicionamiento", j)
