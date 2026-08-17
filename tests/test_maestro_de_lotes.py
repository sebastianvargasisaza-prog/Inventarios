# -*- coding: utf-8 -*-
"""Maestro de lotes · lote × presentación, teóricas contra liberadas.

Era lo último que MyBatch tenía y EOS no armaba: el dato vivía repartido en `acondicionamiento`,
`envasado` y `stock_pt`, y nadie los cruzaba, así que *"de este lote, ¿cuánto salió y cuánto está
liberado?"* sólo se podía contestar abriendo legajo por legajo.

Lo que estos tests protegen, además de que la vista exista:
  · **liberadas** sale de `unidades_inicial`, no de `unidades_disponible` -- la segunda baja con
    cada despacho, así que contestaría "cuánto queda", no "cuánto se liberó" (M5).
  · un lote SIN fila en producto terminado no es un lote con cero: puede estar en cuarentena, y
    la diferencia se DECLARA (M100/M154).
  · con varias presentaciones y sin SKU no se reparte a ojo: se dice que no se pudo (M19/M124).
  · el total se cuenta ANTES de recortar (M207).
"""
import pytest

_H = {"Origin": "http://localhost"}


def _login(client, usuario="sebastian"):
    r = client.post("/login", data={"username": usuario, "password": "TestPass123"},
                    headers=_H, follow_redirects=False)
    assert r.status_code == 302, "no entro %s" % usuario
    return client


def _sembrar(app):
    """Los tres casos que importan, con nombres FIJOS y limpieza ANTES (M103)."""
    import database
    with app.app_context():
        c = database.get_db()
        cur = c.cursor()
        for t, col in (("acondicionamiento", "lote"), ("envasado", "lote"),
                       ("stock_pt", "lote_produccion")):
            cur.execute("DELETE FROM %s WHERE %s LIKE 'ZZML-%%'" % (t, col))
        cur.execute("INSERT INTO app_settings (clave, valor) VALUES ('brd_visible','1') "
                    "ON CONFLICT (clave) DO UPDATE SET valor=excluded.valor")

        # 1 · un lote de UNA presentación, liberado parcialmente (400 salen, 390 se liberan)
        cur.execute("INSERT INTO acondicionamiento (lote,producto,presentacion,sku,"
                    "unidades_producidas,estado,fecha) VALUES ('ZZML-1','ZZ SUERO','30 mL',"
                    "'ZZSKU-30',400,'Completado',date('now'))")
        cur.execute("INSERT INTO stock_pt (sku,lote_produccion,unidades_inicial,"
                    "unidades_disponible,estado) VALUES ('ZZSKU-30','ZZML-1',390,120,'Disponible')")

        # 2 · un lote con DOS presentaciones: una con SKU y otra sin él
        for pres, sku, uds in (("30 mL", "ZZSKU-A", 300), ("10 mL", "", 200)):
            cur.execute("INSERT INTO acondicionamiento (lote,producto,presentacion,sku,"
                        "unidades_producidas,estado,fecha) VALUES ('ZZML-2','ZZ CREMA',?,?,?,"
                        "'Completado',date('now'))", (pres, sku, uds))
        cur.execute("INSERT INTO stock_pt (sku,lote_produccion,unidades_inicial,"
                    "unidades_disponible,estado) VALUES ('ZZSKU-A','ZZML-2',290,290,'Disponible')")
        cur.execute("INSERT INTO stock_pt (sku,lote_produccion,unidades_inicial,"
                    "unidades_disponible,estado) VALUES ('ZZSIN','ZZML-2',150,150,'Disponible')")

        # 3 · un lote envasado que todavía NO se acondicionó ni liberó
        cur.execute("INSERT INTO envasado (lote,producto,presentacion,unidades,estado,fecha) "
                    "VALUES ('ZZML-3','ZZ GEL','50 mL',120,'En proceso',date('now'))")
        c.commit()


def _mias(j):
    return {(f["lote"], f["presentacion"]): f
            for f in (j.get("items") or []) if f["lote"].startswith("ZZML-")}


def test_liberadas_es_lo_que_entro_al_stock_no_lo_que_queda(client, app):
    """390 liberadas aunque sólo queden 120 disponibles: son preguntas distintas (M5)."""
    _sembrar(app)
    j = _login(client).get("/api/brd/maestro-lotes?q=ZZML-").get_json() or {}
    f = _mias(j)[("ZZML-1", "30 mL")]

    assert f["unidades_teoricas"] == 400
    assert f["unidades_liberadas"] == 390, (
        "liberadas tiene que salir de unidades_inicial · con unidades_disponible daría 120, "
        "que es cuánto QUEDA, no cuánto se liberó")
    assert f["diferencia"] == 10
    assert f["liberado"] is True


def test_un_lote_en_cuarentena_no_se_ve_igual_que_uno_sin_liberar_nada(client, app):
    """Un cero mudo se lee como 'no salió nada' y significa otra cosa."""
    _sembrar(app)
    j = _login(client).get("/api/brd/maestro-lotes?q=ZZML-").get_json() or {}
    f = _mias(j)[("ZZML-3", "50 mL")]

    assert f["unidades_liberadas"] == 0
    assert f["liberado"] is False
    assert (f["motivo_no_liberado"] or "").strip(), "un cero sin motivo miente"


def test_con_varias_presentaciones_y_sin_sku_no_se_reparte_a_ojo(client, app):
    """Repartir a ojo le pondría a una presentación las unidades de otra (M19)."""
    _sembrar(app)
    j = _login(client).get("/api/brd/maestro-lotes?q=ZZML-").get_json() or {}
    m = _mias(j)

    con_sku = m[("ZZML-2", "30 mL")]
    assert con_sku["unidades_liberadas"] == 290, "la que TIENE SKU sí se puede cruzar"

    sin_sku = m[("ZZML-2", "10 mL")]
    assert sin_sku["unidades_liberadas"] == 0
    # ⚠ el resto sin dueño son 150 (440 del lote menos las 290 ya atribuidas), NO 440:
    #   decir 440 manda a buscar un descuadre que no existe
    assert sin_sku.get("unidades_sin_repartir") == 150, sin_sku
    assert "150" in (sin_sku["motivo_no_liberado"] or ""), sin_sku["motivo_no_liberado"]
    assert "290" not in (sin_sku["motivo_no_liberado"] or "")

    assert j.get("unidades_sin_repartir", 0) >= 150
    assert "no se pudieron asignar" in (j.get("aviso") or ""), (
        "unidades liberadas que ninguna fila reclama tienen que declararse (M148)")


def test_una_fila_por_lote_y_presentacion(client, app):
    """El mismo lote aparece una vez por cada tamaño · es la forma de MyBatch."""
    _sembrar(app)
    j = _login(client).get("/api/brd/maestro-lotes?q=ZZML-").get_json() or {}
    m = _mias(j)
    assert len(m) == 4, sorted(m)
    assert len({k[0] for k in m}) == 3, "3 lotes en 4 filas"


def test_el_total_se_cuenta_antes_de_recortar(client, app):
    """Un total calculado sobre la ventana recortada es un total falso (M207)."""
    _sembrar(app)
    cli = _login(client)
    completo = cli.get("/api/brd/maestro-lotes").get_json() or {}
    recortado = cli.get("/api/brd/maestro-lotes?limite=1").get_json() or {}

    assert recortado["total"] == completo["total"], (
        "el total cambió al recortar · se está contando sobre la ventana")
    assert recortado["mostradas"] == 1
    assert recortado["recortadas"] == completo["total"] - 1
    assert "se muestran" in (recortado.get("aviso") or ""), "el recorte no se declara"


def test_la_pantalla_existe_y_se_puede_llegar(client, app):
    """Una capacidad a la que nadie puede llegar no existe (M121)."""
    _sembrar(app)
    cli = _login(client)
    r = cli.get("/aseguramiento/maestro-lotes")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "en validación" not in html, "el candado de Part 11 tapó la pantalla"
    assert "/api/brd/maestro-lotes" in html, "la pantalla no llama a su endpoint"
    assert "cortex.css" in html, "sin la hoja de estilos los tokens caen al respaldo"
    for txt in ("Maestro de lotes", "te&oacute;ricas", "liberadas"):
        assert txt in html, txt

    import re
    llamadas = set(re.findall(r'onclick="\s*([A-Za-z_$][\w$]*)\s*\(', html))
    definidas = set(re.findall(r"function\s+([A-Za-z_$][\w$]*)\s*\(", html))
    assert not (llamadas - definidas), (
        "botón que llama a una función inexistente: %s" % sorted(llamadas - definidas))

    # y se llega desde Dirección Técnica, no escribiendo la URL a mano
    tec = cli.get("/tecnica").get_data(as_text=True)
    assert "/aseguramiento/maestro-lotes" in tec, "nadie enlaza el maestro de lotes"
