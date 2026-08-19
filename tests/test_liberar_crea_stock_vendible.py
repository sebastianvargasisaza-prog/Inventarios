# -*- coding: utf-8 -*-
"""La firma que libera el lote lo vuelve VENDIBLE · y no lo vuelve vendible dos veces.

MyBatch termina en *"lote liberado"*: es un batch record y no vende. EOS si vende, y
hasta el 18-ago la cadena quedaba partida en dos puertas que no se tocaban -- el batch
record dejaba el producto terminado en el KARDEX (en cuarentena, y VIGENTE al liberar)
mientras `stock_pt`, el stock por SKU que alimenta despachos y el cruce con Shopify, lo
tenia que volver a teclear alguien por la pantalla de Liberaciones.

Medido caminando el lote entero antes de tocar nada:

    liberar -> {"pt_lotes_promovidos": 1}      <- el kardex si
    stock_pt: (nada)                           <- lo vendible no

**La firma del Director Tecnico es el acto que dice "este producto puede salir"**
(PRD-PRO-001-F01 y el acta del 27-jul con Hernando), asi que crear el stock ahi no es un
permiso nuevo: es su consecuencia.

Y el otro defecto, reproducido en la puerta que YA existia: `liberacion_update` hacia
`UPDATE liberaciones SET estado='Liberado' WHERE id=?` **sin condicion de estado**, asi
que tres clics creaban TRES filas de stock vendible del mismo lote (90 unidades donde
hay 30) y **un lote RECHAZADO por Calidad se volvia a liberar con un clic**. Un stock que
no existe no da ningun sintoma: se vende, y despues falta (M27/M160).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _demo(cli, con_sku=True):
    """Camina el demo hasta dejar el acondicionamiento REGISTRADO."""
    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    cam = d.get("caminar") or {}
    lote = d["lote"]
    cn = _cn()
    try:
        # El demo REUSA sus legajos, asi que una corrida anterior dejaria unidades y
        # stock ya cargados y el test mediria eso en vez del flujo (M102).
        cn.execute("DELETE FROM stock_pt WHERE lote_produccion=?", (lote,))
        cn.execute("DELETE FROM acondicionamiento WHERE lote=?", (lote,))
        cn.commit()
    finally:
        cn.close()
    body = {"lote": lote, "producto": d["producto"], "presentacion": cam["presentacion"],
            "batch_g": cam["batch_g"], "unidades": cam["unidades"],
            "mee_consumido": [{"codigo": cam["etiqueta_codigo"],
                               "cantidad": cam["unidades"]}]}
    if con_sku:
        body["sku"] = "DEMO-SKU-30"
        body["precio_base"] = 45000
    r = cli.post("/api/acondicionamiento", headers=_h(), json=body)
    assert r.status_code in (200, 201), r.get_data(as_text=True)[:300]
    return d, cam, lote


def test_liberar_el_lote_lo_deja_vendible(app, db_clean):
    cli = _login(app)
    d, cam, lote = _demo(cli, con_sku=True)
    oa = d["acondicionamiento_ebr"]

    cli.post("/api/brd/ebr/%d/completar" % oa, json={"cantidad_real_g": 900}, headers=_h())
    r = cli.post("/api/brd/ebr/%d/liberar" % oa, json={}, headers=_h())
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    j = r.get_json() or {}

    creado = (j.get("stock_pt") or {}).get("creado") or []
    assert creado, ("el lote quedo liberado y NO entro al stock vendible: desde afuera "
                    "se ve igual que un lote sin liberar", j.get("stock_pt"))
    assert creado[0]["sku"] == "DEMO-SKU-30"
    assert int(creado[0]["unidades"]) == int(cam["unidades"])

    cn = _cn()
    try:
        filas = cn.execute(
            "SELECT sku, unidades_inicial, unidades_disponible, estado FROM stock_pt "
            "WHERE lote_produccion=?", (lote,)).fetchall()
    finally:
        cn.close()
    assert len(filas) == 1, ("el lote entro al stock mas de una vez", filas)
    assert filas[0][0] == "DEMO-SKU-30"
    assert filas[0][1] == filas[0][2] == int(cam["unidades"])
    assert filas[0][3] == "Disponible"


def test_las_unidades_salen_de_lo_REGISTRADO_no_de_lo_planeado(app, db_clean):
    """Crear stock contra un plan seria vender unidades que nadie envaso (M230)."""
    cli = _login(app)
    d, cam, lote = _demo(cli, con_sku=True)
    cn = _cn()
    try:
        # La planta registro MENOS de lo planeado: el stock dice lo REGISTRADO.
        cn.execute("UPDATE acondicionamiento SET unidades_producidas=? WHERE lote=?",
                   (int(cam["unidades"]) - 7, lote))
        cn.commit()
    finally:
        cn.close()
    oa = d["acondicionamiento_ebr"]
    cli.post("/api/brd/ebr/%d/completar" % oa, json={"cantidad_real_g": 900}, headers=_h())
    r = cli.post("/api/brd/ebr/%d/liberar" % oa, json={}, headers=_h())
    creado = ((r.get_json() or {}).get("stock_pt") or {}).get("creado") or []
    assert creado and int(creado[0]["unidades"]) == int(cam["unidades"]) - 7, creado


def test_sin_SKU_lo_DECLARA_y_no_lo_adivina(app, db_clean):
    """Un lote entrando al stock del producto equivocado no da error: se vende."""
    cli = _login(app)
    d, cam, lote = _demo(cli, con_sku=False)
    oa = d["acondicionamiento_ebr"]
    cli.post("/api/brd/ebr/%d/completar" % oa, json={"cantidad_real_g": 900}, headers=_h())
    r = cli.post("/api/brd/ebr/%d/liberar" % oa, json={}, headers=_h())
    pt = (r.get_json() or {}).get("stock_pt") or {}
    assert not pt.get("creado"), ("invento un SKU para un registro que no lo trae", pt)
    assert pt.get("sin_resolver"), (
        "se callo que el lote no pudo entrar al stock: eso deja un liberado que nadie "
        "puede despachar y sin una sola senal de por que", pt)
    assert pt["sin_resolver"][0].get("motivo") == "sin_sku", pt["sin_resolver"]

    cn = _cn()
    try:
        n = cn.execute("SELECT COUNT(*) FROM stock_pt WHERE lote_produccion=?",
                       (lote,)).fetchone()[0]
    finally:
        cn.close()
    assert n == 0, "creo stock con un SKU inventado"


def test_una_fase_INTERMEDIA_no_crea_producto_terminado(app, db_clean):
    """El borde que hace que el arreglo no rompa lo que ya andaba (M96).

    Si al lote le queda envasado o acondicionamiento, lo vendible lo crea ESA fase.
    Crearlo al liberar la fabricacion seria poner un GRANEL en el stock de venta.
    """
    cli = _login(app)
    d, cam, lote = _demo(cli, con_sku=True)
    op = d.get("ebr_id") or d.get("fabricacion_ebr")
    assert op, ("el demo no expuso el legajo de fabricacion", sorted(d.keys()))

    cn = _cn()
    try:
        cn.execute("UPDATE ebr_ejecuciones SET estado='completado' WHERE id=? "
                   "AND estado NOT IN ('liberado','rechazado')", (op,))
        cn.commit()
    finally:
        cn.close()
    r = cli.post("/api/brd/ebr/%d/liberar" % op, json={}, headers=_h())
    if r.status_code == 200:
        pt = (r.get_json() or {}).get("stock_pt") or {}
        assert not pt.get("creado"), (
            "la FABRICACION metio producto terminado al stock vendible teniendo fases "
            "posteriores: eso es vender un granel", pt)


def test_el_helper_es_idempotente_por_ACTO_y_no_colapsa_dos_actos(app, db_clean):
    """La llave de dedup identifica el ACTO, no el par (sku, lote).

    Anclarla a (sku, lote) haria que una segunda liberacion PARCIAL legitima del mismo
    lote y el mismo SKU se saltee en silencio, y perder unidades no se ve (M134/M80).
    """
    try:
        from blueprints.inventario import crear_stock_pt
    except ImportError:
        from api.blueprints.inventario import crear_stock_pt

    cn = _cn()
    try:
        cn.execute("DELETE FROM stock_pt WHERE lote_produccion='ZPT-ACTO'")
        cn.commit()
        c = cn.cursor()
        a1 = crear_stock_pt(c, sku="ZSKU", descripcion="p", lote="ZPT-ACTO",
                            unidades=10, marca="[lib#1]")
        a2 = crear_stock_pt(c, sku="ZSKU", descripcion="p", lote="ZPT-ACTO",
                            unidades=10, marca="[lib#1]")
        b1 = crear_stock_pt(c, sku="ZSKU", descripcion="p", lote="ZPT-ACTO",
                            unidades=5, marca="[lib#2]")
        cn.commit()
        assert a1["creado"] and a1["motivo"] == "creado"
        assert not a2["creado"] and a2["motivo"] == "ya_existe", (
            "el mismo acto creo el stock dos veces", a2)
        assert b1["creado"], ("una segunda liberacion parcial legitima se perdio en "
                              "silencio: eso es peor que duplicarla, porque no se ve", b1)
        assert crear_stock_pt(c, sku="", descripcion="p", lote="ZPT-ACTO",
                              unidades=10, marca="[lib#3]")["motivo"] == "sin_sku"
        assert crear_stock_pt(c, sku="ZSKU", descripcion="p", lote="ZPT-ACTO",
                              unidades=0, marca="[lib#4]")["motivo"] == "sin_unidades"
        n = cn.execute("SELECT COUNT(*) FROM stock_pt "
                       "WHERE lote_produccion='ZPT-ACTO'").fetchone()[0]
        assert n == 2, ("filas inesperadas en stock_pt", n)
    finally:
        cn.execute("DELETE FROM stock_pt WHERE lote_produccion='ZPT-ACTO'")
        cn.commit()
        cn.close()


def test_liberar_dos_veces_por_la_pantalla_no_duplica_el_stock(app, db_clean):
    """Reproducido el 18-ago: tres clics = 90 unidades vendibles donde hay 30."""
    cli = _login(app)
    cn = _cn()
    try:
        cn.execute("DELETE FROM stock_pt WHERE lote_produccion='ZLIB-CAS'")
        cn.execute("DELETE FROM liberaciones WHERE lote='ZLIB-CAS'")
        cn.commit()
    finally:
        cn.close()
    r = cli.post("/api/liberacion", headers=_h(), json={
        "lote": "ZLIB-CAS", "producto": "ZZ PRODUCTO", "unidades": 30,
        "presentacion": "30 ml", "sku": "ZLIB-SKU", "precio_base": 1000})
    assert r.status_code in (200, 201), r.get_data(as_text=True)[:200]
    cn = _cn()
    try:
        lid = cn.execute("SELECT id FROM liberaciones "
                         "WHERE lote='ZLIB-CAS'").fetchone()[0]
    finally:
        cn.close()

    assert cli.patch("/api/liberacion/%d" % lid, json={"estado": "Liberado"},
                     headers=_h()).status_code == 200
    for _ in range(2):
        rr = cli.patch("/api/liberacion/%d" % lid, json={"estado": "Liberado"},
                       headers=_h())
        assert rr.status_code == 409, ("volvio a liberar un lote ya liberado: cada clic "
                                       "suma stock vendible que no existe", rr.status_code)

    cn = _cn()
    try:
        n, uds = cn.execute("SELECT COUNT(*), COALESCE(SUM(unidades_disponible),0) "
                            "FROM stock_pt "
                            "WHERE lote_produccion='ZLIB-CAS'").fetchone()
    finally:
        cn.close()
    assert (n, uds) == (1, 30), ("el stock vendible se multiplico por los clics", n, uds)


def test_un_lote_RECHAZADO_no_se_re_libera_con_un_clic(app, db_clean):
    cli = _login(app)
    cn = _cn()
    try:
        cn.execute("DELETE FROM stock_pt WHERE lote_produccion='ZLIB-RECH'")
        cn.execute("DELETE FROM liberaciones WHERE lote='ZLIB-RECH'")
        cn.commit()
    finally:
        cn.close()
    cli.post("/api/liberacion", headers=_h(), json={
        "lote": "ZLIB-RECH", "producto": "ZZ PRODUCTO", "unidades": 30,
        "presentacion": "30 ml", "sku": "ZRECH-SKU", "precio_base": 1000})
    cn = _cn()
    try:
        lid = cn.execute("SELECT id FROM liberaciones "
                         "WHERE lote='ZLIB-RECH'").fetchone()[0]
    finally:
        cn.close()
    assert cli.patch("/api/liberacion/%d" % lid, headers=_h(), json={
        "estado": "Rechazado",
        "observaciones": "contaminacion microbiologica confirmada"}).status_code == 200

    rr = cli.patch("/api/liberacion/%d" % lid, json={"estado": "Liberado"}, headers=_h())
    assert rr.status_code == 409, ("un lote que Calidad RECHAZO se volvio a liberar con "
                                   "un clic y entro al stock vendible", rr.status_code)
    cn = _cn()
    try:
        n = cn.execute("SELECT COUNT(*) FROM stock_pt "
                       "WHERE lote_produccion='ZLIB-RECH'").fetchone()[0]
    finally:
        cn.close()
    assert n == 0, "un lote rechazado quedo vendible"
