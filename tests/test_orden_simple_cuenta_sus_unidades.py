# -*- coding: utf-8 -*-
"""Una orden registrada por la vía SIMPLE también cuenta sus unidades.

Sebastián, mirando la pestaña de acondicionamiento: *"no me parece que deba ser así"* ·
*"le falta ser más EOS fusionado con MyBatch"*.

La vista de órdenes ya mezclaba las dos mitades -- el LEGAJO (la orden de MyBatch) y el registro
SIMPLE (la pantalla que usa la planta) --, pero el bucle que enriquece los items arrancaba con
`if not eid: continue`, así que sólo los legajos recibían `unidades_total`.

Consecuencia, con el trabajo hecho y registrado:
  · el KPI "Unidades acondicionadas" contaba **0**
  · y la tarjeta decía **"Sin unidades registradas todavía"**

El SQL ya sumaba `SUM(unidades_producidas)` y el diccionario la tiraba: un dato que se captura,
se calcula y se pierde en el camino lo termina inventando la pantalla (M115).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = "ZZ-ORD-SIMPLE"
LOTE = "ZZORDSIMPLE1"


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


def _orden_del_lote(cli, fase):
    d = cli.get("/api/brd/ordenes-unificadas?fase=%s" % fase).get_json() or {}
    fila = next((o for o in (d.get("ordenes") or []) if (o.get("lote_bulk") or "") == LOTE), None)
    return d, fila


def test_el_acondicionamiento_registrado_a_mano_muestra_sus_unidades(app, db_clean):
    _sql("DELETE FROM acondicionamiento WHERE lote=?", (LOTE,))
    cli = _login(app)

    r = cli.post("/api/acondicionamiento", headers=_h(), json={
        "lote": LOTE, "producto": PROD, "presentacion": "ZZ-30ML",
        "unidades": 120, "batch_g": 3600, "observaciones": "registro por la pantalla"})
    assert r.status_code in (200, 201), r.data[:300]

    d, fila = _orden_del_lote(cli, "acondicionamiento")
    assert fila, "el registro simple ni siquiera aparece en la lista de órdenes"
    assert fila.get("unidades_total") == 120, (
        "la orden aparece pero sin sus unidades: la tarjeta diría 'sin unidades registradas' "
        "con el trabajo hecho", fila)
    assert (d.get("resumen") or {}).get("unidades_total", 0) >= 120, (
        "el KPI de unidades acondicionadas no cuenta lo registrado a mano", d.get("resumen"))


def test_lo_mismo_para_envasado(app, db_clean):
    """El bucle era compartido, así que envasado tenía el mismo hueco (M45)."""
    _sql("DELETE FROM envasado WHERE lote=?", (LOTE,))
    cli = _login(app)

    r = cli.post("/api/envasado", headers=_h(), json={
        "lote": LOTE, "producto": PROD, "presentacion": "ZZ-30ML",
        "unidades": 75, "batch_g": 2250})
    assert r.status_code in (200, 201), r.data[:300]

    _d, fila = _orden_del_lote(cli, "envasado")
    assert fila, "el envasado registrado no aparece en la lista"
    assert fila.get("unidades_total") == 75, (
        "el envasado simple aparece sin sus unidades", fila)


def test_una_orden_SIN_unidades_sigue_avisando(app, db_clean):
    """El borde del otro lado: si de verdad no hay nada registrado, la tarjeta tiene que seguir
    diciéndolo. Convertir el aviso en un cero silencioso sería cambiar un bug por otro."""
    _sql("DELETE FROM acondicionamiento WHERE lote=?", (LOTE + "V",))
    cli = _login(app)
    r = cli.post("/api/acondicionamiento", headers=_h(), json={
        "lote": LOTE + "V", "producto": PROD, "presentacion": "ZZ-30ML",
        "unidades": 0, "batch_g": 0})
    assert r.status_code in (200, 201, 400), r.data[:300]
    d = cli.get("/api/brd/ordenes-unificadas?fase=acondicionamiento").get_json() or {}
    fila = next((o for o in (d.get("ordenes") or []) if (o.get("lote_bulk") or "") == LOTE + "V"),
                None)
    if fila:
        assert not fila.get("unidades_total"), (
            "una orden sin unidades no puede reportar un total", fila)


def test_la_excepcion_va_PLEGADA_y_la_cola_manda(app, db_clean):
    """La pestaña tiene que empujar al camino normal, no al excepcional.

    "Registrar a mano" son nueve campos vacíos y su propio subtítulo dice que es para reprocesos
    y entregas puntuales; abierto de fábrica era el bloque más grande de la pantalla, más que la
    cola -- cuyo botón YA pre-llena producto, lote, unidades y presentación. Eso invita a teclear
    a mano lo que el sistema ya sabe.

    Se pliega, **no se esconde**: sigue a un clic, con sus campos y su botón, y dice cuándo usarlo
    (una función que desaparece sin explicación se lee como un faltante · M124).
    """
    from .conftest import pantalla_servida
    cli = _login(app)
    html = pantalla_servida(cli, "/inventarios")

    i = html.find('id="ac-form-manual"')
    assert i > 0, "desapareció el formulario de registro a mano"
    apertura = html[max(0, i - 200):i + 40]
    assert "<details" in apertura, (
        "el formulario de excepción volvió a estar desplegado de fábrica: ocupa más pantalla "
        "que la cola, que es el camino normal")
    assert "open" not in apertura.split("<details")[1].split(">")[0], (
        "el <details> nace ABIERTO, que es lo mismo que no plegarlo")

    # sigue completo y alcanzable
    for x in ("ac-prod-sel", "ac-lote", "ac-form-msg"):
        assert x in html, "se perdió %s al plegar el formulario" % x
    # y la cola -- el camino normal -- sigue ahí con su botón
    assert "Lotes listos para acondicionar" in html
    assert "prefillAcond(" in html, "la cola perdió el botón que pre-llena el registro"


def test_la_tarjeta_de_acondicionamiento_no_habla_de_GRANEL(app, db_clean):
    """El renderizador es UNO para las tres fases -a propósito, para que el estilo no diverja-
    pero el CONTENIDO tiene que hablar de su fase.

    En una orden de acondicionamiento decía "1.000 g de granel": ahí el producto ya está
    envasado y no se maneja granel, se manejan unidades, etiquetas y plegadizas. Es pedirle la
    densidad a una caja (M205/M214).

    ⚠ Se mide sobre el JS que el navegador CARGA, no sobre el HTML: las funciones del dashboard
    viven en los bundles (M166).
    """
    from .conftest import pantalla_servida
    cli = _login(app)
    import re as _re
    js = pantalla_servida(cli, "/inventarios")
    # ⚠ SIN comentarios: el bloque lleva arriba una nota que explica por qué el granel no va en
    #   acondicionamiento, y la primera versión de este guard se encontró a sí misma (M154).
    js = _re.sub("//.*", "", js)   # sin DOTALL, el punto no cruza el salto de línea
    i = js.find("g de granel")
    assert i > 0, "desapareció la línea del granel (fabricación y envasado la necesitan)"
    ventana = js[max(0, i - 260):i]
    assert "fase!==" in ventana.replace(" ", "") or "fase !==" in ventana, (
        "la línea de 'g de granel' no está condicionada a la fase: vuelve a aparecer en una "
        "orden de acondicionamiento, donde ya no hay granel que medir")


def test_abrir_o_crear_el_legajo_de_un_lote_es_UNA_llamada(app, db_clean):
    """`legajo-rapido` contestaba 409 cuando el legajo YA existía -- el caso más común -- así que
    "abrir o crear" obligaba a cada botón a inventar su propio rescate.

    Es el mismo defecto que el enganche envasado→acondicionamiento ya había cobrado: "ya existe"
    no es un error, es la respuesta (M129). Ahora devuelve el que hay, marcado como reusado, y
    con el enlace de SU fase.
    """
    cli = _login(app)
    d = cli.post("/api/admin/planta-demo/crear", json={}, headers=_h()).get_json()
    assert d.get("ok"), d

    r = cli.post("/api/brd/legajo-rapido", headers=_h(),
                 json={"producto": d["producto"], "lote": d["lote"], "fase": "acondicionamiento"})
    assert r.status_code == 200, ("el legajo ya existe: eso no es un 409 · %s" % r.data[:250])
    j = r.get_json()
    assert j.get("ok") and j.get("id") == d["acondicionamiento_ebr"], (
        "devolvió otro legajo, no el del lote", j, d["acondicionamiento_ebr"])
    assert j.get("reusado") is True, ("tiene que DECIR que lo reusó, no fingir que lo creó", j)
    assert j.get("link") == "/planta/legajo-acondicionamiento/%d" % d["acondicionamiento_ebr"], (
        "el enlace no lleva a la pantalla de su fase", j)

    # y el de envasado, por su propio camino
    r2 = cli.post("/api/brd/legajo-rapido", headers=_h(),
                  json={"producto": d["producto"], "lote": d["lote"], "fase": "envasado"})
    assert r2.status_code == 200, r2.data[:250]
    assert r2.get_json().get("link") == "/planta/legajo-envasado/%d" % d["envasado_ebr"], r2.data[:250]


def test_el_boton_de_la_cola_abre_el_LEGAJO(app, db_clean):
    """La cola tiene que llevar al batch record, no a un registro paralelo.

    Se mide sobre el JS que el navegador CARGA (M166), y con los comentarios quitados: el bloque
    lleva arriba la explicación de por qué, y un guard que se encuentra a sí mismo no mide nada
    (M154).
    """
    import re as _re
    from .conftest import pantalla_servida
    cli = _login(app)
    js = _re.sub("//.*", "", pantalla_servida(cli, "/inventarios"))
    i = js.find("function prefillAcond")
    assert i > 0, "desapareció el handler del botón de la cola"
    # ⚠ acotado al CUERPO, no a N caracteres: con una ventana fija el guard se come la función
    #   siguiente y pasa verde con el bug puesto -- probado (M151/M176).
    _sig = min([x for x in (js.find("\nfunction ", i + 1), js.find("\nasync function ", i + 1))
                if x > 0] or [i + 2000])
    cuerpo = js[i:_sig]
    assert "legajo-rapido" in cuerpo, (
        "el botón de la cola volvió a abrir un registro suelto en vez del legajo del lote")
    assert "abrirAcond" in cuerpo, (
        "se perdió la caída al registro a mano: un lote sin MBR aprobado no puede quedar sin "
        "forma de registrarse")


def test_las_pantallas_del_batch_record_son_FULL_WIDTH():
    """Sebastián lo pide desde siempre: los módulos van a ~96vw.

    Las del batch record estaban clavadas en 1100-1200px, así que en un monitor de 1990 dejaban
    el 40% en blanco **y la tabla de Materiales de Empaque -- 7 columnas -- se desbordaba dentro
    de esa columna, cortando "Diferencia"**. La orden madre ya usaba 96vw: la asimetría entre
    hermanas es la firma del hueco (M45).

    Los dos INSTRUCTIVOS quedan angostos a propósito -- son formatos que se leen y se imprimen,
    donde una medida corta se lee mejor -- y por eso se enumeran acá con su motivo, en vez de
    aflojar la regla (M122).
    """
    import re
    from blueprints import brd
    ANGOSTAS = {"_INSTRUCCIONES_ACOND_HTML": "formato que se lee y se imprime",
                "_INSTRUCCIONES_ENVASADO_HTML": "formato que se lee y se imprime",
                "_BRD_OCULTO_HTML": "un aviso corto y centrado",
                "_ACTIVAR_LEGAJOS_HTML": "un formulario chico de admin"}
    angostas = []
    for nom in dir(brd):
        if not (nom.startswith("_") and nom.endswith("HTML")):
            continue
        h = getattr(brd, nom, "")
        if not isinstance(h, str) or ".wrap{max-width:" not in h:
            continue
        m = re.search(r"\.wrap\{max-width:([^;]+)", h)
        if not m:
            continue
        valor = m.group(1).strip()
        if valor.endswith("px") and nom not in ANGOSTAS:
            angostas.append("%s = %s" % (nom, valor))
    assert not angostas, (
        "estas pantallas del batch record volvieron a un ancho fijo en vez de 96vw: %s" % angostas)


def test_el_legajo_no_llama_ACONDICIONADAS_a_las_unidades_PLANEADAS():
    """El encabezado decía "Unidades acondicionadas: 333" mientras la fila de abajo decía
    "Programado": sin acondicionamiento registrado la lista cae a las presentaciones PLANEADAS,
    así que el rótulo prometía un hecho que no ocurrió (M19/M5)."""
    from blueprints import brd
    h = brd._ACOND_LEGAJO_HTML
    assert "Unidades a acondicionar (plan)" in h, (
        "el encabezado no distingue lo planeado de lo acondicionado")
    assert "fld(rotUds," in h, "el rótulo volvió a ser fijo en vez de derivarse de los datos"


def test_el_legajo_de_acond_no_lista_el_FRASCO_como_su_material(app, db_clean):
    """El frasco, la tapa y la caja los consume el ENVASADO (Sebastián 20-jul, escrito en
    `cerrar-envasado`); en acondicionamiento el material es la etiqueta y el estuche.

    Sin acondicionamiento registrado, la sección caía a `_materiales_envase_planeados` -- el
    helper de envasado -- que sin `sku_mee_config` devuelve **sólo el envase**. Resultado: el
    legajo de acondicionamiento listaba el FRASCO como su material de empaque, o sea justo lo que
    el envasado ya consumió. Quien llenara ahí la conciliación lo contaría dos veces.

    ⚠ Se prueba sobre el HELPER con el plan sembrado, no sobre el legajo del demo: el demo no
    tiene producción programada, así que las dos listas salen vacías y el test pasaría sin haber
    filtrado nada (M152 · la primera versión de este test hacía exactamente eso).
    """
    from database import get_db
    from blueprints.brd import _materiales_envase_planeados, _codigos_de_envasado
    prod = "ZZ-FILTRO-FASE"
    with app.app_context():
        cn = get_db()
        cn.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (prod,))
        cn.execute("DELETE FROM produccion_programada WHERE producto=?", (prod,))
        for cod, desc in (("ZZF-ENV", "Frasco"), ("ZZF-TAP", "Tapa"),
                          ("ZZF-CAJ", "Estuche"), ("ZZF-ETQ", "Etiqueta")):
            cn.execute("INSERT OR IGNORE INTO maestro_mee (codigo, descripcion, stock_actual, "
                       " estado) VALUES (?,?,500,'Activo')", (cod, desc))
        cn.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                   " etiqueta, volumen_ml, envase_codigo, tapa_codigo, caja_codigo, activo, "
                   " sku_shopify) VALUES (?, 'ZZF30', '30ml', 30, 'ZZF-ENV', 'ZZF-TAP', "
                   " 'ZZF-CAJ', 1, 'ZZF-SKU')", (prod,))
        cn.commit()

        # los tres codigos del envasado se resuelven
        cods = _codigos_de_envasado(cn.cursor(), prod)
        assert {"ZZF-ENV", "ZZF-TAP", "ZZF-CAJ"} <= cods, ("no resolvió los del envasado", cods)
        assert "ZZF-ETQ" not in cods, ("la etiqueta NO es material de envasado", cods)

        # y el filtro los saca sin tocar lo demas
        crudo = [{"material": "ZZF-ENV Frasco"}, {"material": "ZZF-ETQ Etiqueta"}]
        del crudo  # la salida real se compara abajo con el helper

    # el helper, con y sin filtro, sobre el MISMO plan
    with app.app_context():
        cn = get_db()
        cn.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, "
                   " estado, origen) VALUES (?, date('now'), 10, 'programado', 'eos_plan')",
                   (prod,))
        cn.commit()
        sin_filtro = _materiales_envase_planeados(cn, prod)
        con_filtro = _materiales_envase_planeados(cn, prod, excluir_envasado=True)

    _txt = lambda L: " ".join(str(m.get("material") or "") for m in (L or []))
    if not sin_filtro:
        import pytest
        pytest.skip("el plan no produjo materiales: sin eso este caso no mide el filtro")
    assert "ZZF-ENV" in _txt(sin_filtro), ("el envasado tiene que ver su frasco", sin_filtro)
    assert "ZZF-ENV" not in _txt(con_filtro), (
        "acondicionamiento sigue listando el frasco, que consume el envasado", con_filtro)


def test_el_legajo_de_acond_PIDE_el_filtro_de_fase():
    """El caso de arriba prueba el helper; éste prueba que el legajo lo USE.

    Sin esto, quitar `excluir_envasado=True` de la vista dejaba el guard verde con el frasco de
    vuelta en la pantalla: un guard que cubre el mecanismo y no el punto de llamada mide la mitad
    (M96 · probado reintroduciendo exactamente ese cambio).
    """
    import re
    import inspect
    from blueprints import brd
    src = inspect.getsource(brd.ebr_vista_completa)
    src = re.sub(r"#[^\n]*", "", src)          # sin comentarios (M154)
    i = src.find("acond_materiales")
    assert i > 0, "no encontré la carga del material de empaque del legajo de acondicionamiento"
    j = src.find("excluir_envasado", i)
    assert j > 0, (
        "el legajo de acondicionamiento volvió a pedir el material SIN filtrar por fase: "
        "listaría el frasco, la tapa y la caja, que consume el envasado")
