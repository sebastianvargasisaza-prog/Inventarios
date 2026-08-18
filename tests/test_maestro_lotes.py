"""Maestro de lotes · el cuadro de unidades que MyBatch tiene y EOS no armaba (15-ago-2026).

MyBatch lo tiene en Aseguramiento: por lote, cuántas unidades debían salir y cuántas
se liberaron, cruzado con la presentación. En EOS el dato estaba ENTERO pero repartido
en tres tablas -unidades por presentación en `ebr_envasado_unidades`, granel envasable
en el propio legajo, liberación en el kardex de PT- y sólo se veía abriendo legajo por
legajo. La pregunta que hace un auditor no tenía pantalla (M121).

Lo que fija este guard:
  · que un lote FÍSICO sea UN renglón aunque tenga tres legajos (M10: la columna `lote`
    lleva sufijo de fase porque es UNIQUE, y agrupar por ella parte el lote en tres);
  · que las unidades que "debían" salir se calculen repartiendo el granel por VOLUMEN
    (M72) y que, sin granel medido, se declare en vez de estimarse (M124);
  · que el TOTAL se cuente aparte de la ventana (M207 · el error que casi despliego ayer);
  · que la pantalla PINTE el cuadro, porque un dato que el backend manda y la vista no
    dibuja no existe (M115);
  · que se arme con consultas agregadas y NUNCA una por lote (M43/M63: llamar al
    repartidor de envases por fila es exactamente lo que satura los tres workers).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _limpiar():
    for sql in ("DELETE FROM ebr_envasado_unidades WHERE ebr_id IN "
                "(SELECT id FROM ebr_ejecuciones WHERE lote LIKE 'ZMAE%')",
                "DELETE FROM movimientos WHERE lote LIKE 'ZMAE%'",
                "DELETE FROM ebr_ejecuciones WHERE lote LIKE 'ZMAE%'",
                "DELETE FROM mbr_templates WHERE producto_nombre LIKE 'ZMAE%'"):
        try:
            _exec(sql)
        except Exception:
            pass


def _sembrar_lote(lote_fisico, producto, *, granel_g=90000.0, densidad=0.9,
                  ml_envasable=100000.0):
    """Un lote físico con sus tres legajos, como los crea la app: la llave `lote` lleva
    sufijo de fase (-OF/-OA) y el lote real vive en `lote_codigo` (M10)."""
    mbr = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                "creado_por) VALUES (?,1,'aprobado',100000,'sebastian')", (producto,))
    ids = {}
    for fase, sufijo, estado in (("fabricacion", "", "liberado"),
                                 ("envasado", "-OF", "completado"),
                                 ("acondicionamiento", "-OA", "iniciado")):
        ids[fase] = _exec(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
            "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, "
            "cantidad_real_g, yield_pct, densidad_g_ml, ml_envasable) "
            "VALUES (?,1,?,?,?,?,'sebastian','2026-08-01 10:00:00',100000,?,?,?,?)",
            (mbr, lote_fisico + sufijo, lote_fisico, estado, fase,
             granel_g, round(100.0 * granel_g / 100000.0, 2), densidad, ml_envasable))
    return ids


def _maestro(app, **qs):
    c = _login(app)
    url = "/api/calidad/maestro-lotes"
    if qs:
        url += "?" + "&".join("%s=%s" % (k, v) for k, v in qs.items())
    r = c.get(url)
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def test_un_lote_fisico_es_un_solo_renglon(app, db_clean):
    """Tres legajos (OP/OF/OA) del mismo lote son UN lote, no tres."""
    _limpiar()
    _sembrar_lote("ZMAE-L1", "ZMAE PRODUCTO A")
    j = _maestro(app, q="ZMAE-L1")
    mios = [x for x in j["lotes"] if x["lote"] == "ZMAE-L1"]
    assert len(mios) == 1, "el lote quedó partido por fase: %s" % [x["lote"] for x in j["lotes"]]
    L = mios[0]
    assert set(L["fases"]) == {"fabricacion", "envasado", "acondicionamiento"}, L["fases"]
    # El estado del lote es el de su fase MÁS AVANZADA, no el de la primera que se lea.
    assert L["fase_final"] == "acondicionamiento", L["fase_final"]
    assert L["estado_liberacion"] == "en_proceso", L["estado_liberacion"]


def test_las_unidades_que_debian_salir_se_reparten_por_volumen(app, db_clean):
    """100.000 mL envasables, mitad del volumen en 30 mL y mitad en 10 mL.

    Con el reparto por VOLUMEN (M72) a cada mitad le tocan 50.000 mL: 1.666 unidades de
    30 y 5.000 de 10. Repartir por unidades daría el mismo número de las dos, que es el
    error dimensional que M72 dejó escrito.
    """
    _limpiar()
    ids = _sembrar_lote("ZMAE-L2", "ZMAE PRODUCTO B", ml_envasable=100000.0)
    ebr_of = ids["envasado"]
    # 1500 x 30 mL = 45.000 mL · 4500 x 10 mL = 45.000 mL → mitad y mitad del volumen
    _exec("INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, etiqueta, "
          "volumen_ml, unidades) VALUES (?,'P30','30 ml',30,1500)", (ebr_of,))
    _exec("INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, etiqueta, "
          "volumen_ml, unidades) VALUES (?,'P10','10 ml',10,4500)", (ebr_of,))
    L = [x for x in _maestro(app, q="ZMAE-L2")["lotes"] if x["lote"] == "ZMAE-L2"][0]
    pres = {p["codigo"]: p for p in L["presentaciones"]}
    assert set(pres) == {"P30", "P10"}, pres
    assert pres["P30"]["registradas"] == 1500
    assert pres["P10"]["registradas"] == 4500
    # 50.000 mL / 30 = 1666,67 → 1667 · 50.000 mL / 10 = 5000
    assert pres["P30"]["teoricas"] == 1667, pres["P30"]
    assert pres["P10"]["teoricas"] == 5000, pres["P10"]
    assert pres["P30"]["diferencia"] == 1500 - 1667
    assert pres["P10"]["diferencia"] == 4500 - 5000
    assert L["unidades"]["registradas"] == 6000
    assert L["unidades"]["diferencia"] == 6000 - 6667


def test_sin_granel_medido_se_declara_en_vez_de_estimar(app, db_clean):
    """Una teórica inventada se lee igual que una medida, y sobre ésta se firma (M124)."""
    _limpiar()
    ids = _sembrar_lote("ZMAE-L3", "ZMAE PRODUCTO C", ml_envasable=0.0)
    _exec("INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, etiqueta, "
          "volumen_ml, unidades) VALUES (?,'P30','30 ml',30,900)", (ids["envasado"],))
    L = [x for x in _maestro(app, q="ZMAE-L3")["lotes"] if x["lote"] == "ZMAE-L3"][0]
    assert L["unidades"]["registradas"] == 900
    assert L["unidades"]["teoricas"] is None, "estimó una teórica sin granel medido"
    assert L["unidades"]["diferencia"] is None
    assert L["presentaciones"][0]["teoricas"] is None


def test_el_total_no_sale_de_la_ventana(app, db_clean):
    """Un total calculado sobre un recorte es un total falso (M207 · lo pagué ayer)."""
    _limpiar()
    for i in range(4):
        _sembrar_lote("ZMAE-T%d" % i, "ZMAE TOTAL %d" % i)
    j = _maestro(app)
    assert j["total"] >= j["mostrados"], j
    assert j["recortado"] == max(0, j["total"] - j["mostrados"]), j
    # Y el filtro tiene que mover el total, no sólo la lista: si el total ignorara el
    # filtro, la pantalla diría "4 de 900" y nadie sabría cuál de los dos creer.
    jf = _maestro(app, q="ZMAE-T")
    assert jf["total"] == 4, jf["total"]


def test_liberado_reporta_unidades_liberadas(app, db_clean):
    """Lo que Calidad liberó es lo que se puede vender: si la fase final está liberada,
    las unidades envasadas cuentan como liberadas."""
    _limpiar()
    ids = _sembrar_lote("ZMAE-L4", "ZMAE PRODUCTO D")
    _exec("INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, etiqueta, "
          "volumen_ml, unidades) VALUES (?,'P30','30 ml',30,800)", (ids["envasado"],))
    _exec("UPDATE ebr_ejecuciones SET estado='liberado' WHERE id=?", (ids["acondicionamiento"],))
    L = [x for x in _maestro(app, q="ZMAE-L4")["lotes"] if x["lote"] == "ZMAE-L4"][0]
    assert L["estado_liberacion"] == "liberado", L["estado_liberacion"]
    assert L["unidades"]["liberadas"] == 800, L["unidades"]
    # Y un lote RECHAZADO no libera nada, aunque se haya envasado. Va en otro lote a
    # propósito: un legajo liberado es INMUTABLE por trigger (Part 11 §11.10(e)), así
    # que moverlo a rechazado no es un caso que la app pueda producir (M93).
    ids2 = _sembrar_lote("ZMAE-L5", "ZMAE PRODUCTO E")
    _exec("INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, etiqueta, "
          "volumen_ml, unidades) VALUES (?,'P30','30 ml',30,700)", (ids2["envasado"],))
    _exec("UPDATE ebr_ejecuciones SET estado='rechazado' WHERE id=?", (ids2["acondicionamiento"],))
    L2 = [x for x in _maestro(app, q="ZMAE-L5")["lotes"] if x["lote"] == "ZMAE-L5"][0]
    assert L2["estado_liberacion"] == "rechazado"
    assert L2["unidades"]["liberadas"] == 0, L2["unidades"]


def test_la_pantalla_pinta_el_cuadro(app, db_clean):
    """Un dato que el backend manda y la pantalla no dibuja no existe (M115).

    Se exige la FUNCIÓN que arma la tabla y los encabezados, no sólo que la palabra
    aparezca: con la tabla borrada los textos podrían seguir en un comentario y el
    guard pasaría verde midiendo otra cosa (M152/M154).
    """
    c = _login(app)
    html = c.get("/calidad/maestro-lotes").data.decode("utf-8")
    for que, pieza in (("la función que arma el detalle", "function mlDetalle("),
                       ("la carga de la cola", "/api/calidad/maestro-lotes?q="),
                       ("la columna de teóricas", ">Debían</th>"),
                       ("la columna de envasadas", ">Envasadas</th>"),
                       ("la columna de diferencia", ">Diferencia</th>"),
                       ("el bloque de clientes", "Para quién es")):
        assert pieza in html, "la pantalla no muestra %s (%s)" % (que, pieza)


def test_no_hace_una_consulta_por_lote(app, db_clean):
    """El repartidor de envases por fila es lo que tumba la pantalla (M43/M63): el
    maestro se arma con agregados, así que ni lo importa."""
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "api", "blueprints", "calidad.py")
    fuente = open(ruta, encoding="utf-8").read()
    i = fuente.find("def calidad_maestro_lotes(")
    assert i > 0, "no se encontró el endpoint"
    bloque = fuente[i:i + 14000]
    assert "_composicion_envases_lote" not in bloque, (
        "llama al repartidor de envases dentro del maestro: eso es una consulta por lote")
    # El bloque de presentaciones va FUERA del recorrido de lotes.
    k = bloque.find("FROM ebr_envasado_unidades")
    m = bloque.find("for L in vista.values():")
    assert k > 0 and m > 0, bloque[:200]
    assert k < m, "la consulta de presentaciones quedó dentro del loop por lote"


def test_se_puede_llegar_desde_las_tres_pantallas(app, db_clean):
    """Una pantalla sin enlace no existe: Sebastián tuvo que escribir la URL a mano más
    de una vez por esto (M121/M174). El maestro se alcanza desde donde la gente ya está.
    """
    c = _login(app)
    for pagina, quien in (("/calidad", "Calidad (Laura)"),
                          ("/calidad/expediente", "el expediente por lote"),
                          ("/calidad/genealogia", "la genealogía de PT"),
                          ("/inventarios", "Producción (jefe de planta)")):
        html = c.get(pagina).data.decode("utf-8")
        assert "/calidad/maestro-lotes" in html, (
            "no se puede llegar al maestro de lotes desde %s (%s)" % (quien, pagina))


def test_el_material_de_envase_conecta_con_compras(app, db_clean):
    """El tercer enganche que pidió Sebastián: calendario, clientes y COMPRAS.

    Por lote: lo que se pidió, lo que Compras entregó, lo que la línea usó, lo que volvió
    y lo que se rompió. Lo que se pidió y no llegó se señala aparte, porque eso es lo que
    hay que reclamar. La DIFERENCIA se deriva con el helper canónico de `brd`: dos copias
    de la misma resta divergen el día que alguien corrige una (M3/M99).
    """
    _limpiar()
    ids = _sembrar_lote("ZMAE-M1", "ZMAE MATERIAL")
    ebr = ids["envasado"]
    # se pidieron 1000 frascos, Compras entregó 900, la línea usó 850, devolvió 30, rompió 10
    _exec("INSERT INTO ebr_conciliacion_material (ebr_id, tipo, material_codigo, "
          "material_nombre, cant_requerida, cant_recibida, cant_utilizada, cant_devuelta, "
          "cant_averiada, registrado_por, registrado_at_utc) "
          "VALUES (?,'envase','MEE-ENV-001','Frasco 30 ml',1000,900,850,30,10,'mayerlin',"
          "'2026-08-01 12:00:00')", (ebr,))
    L = [x for x in _maestro(app, q="ZMAE-M1")["lotes"] if x["lote"] == "ZMAE-M1"][0]
    assert len(L["materiales"]) == 1, L["materiales"]
    m = L["materiales"][0]
    assert m["requerida"] == 1000 and m["recibida"] == 900
    # lo que Compras no entregó
    assert m["sin_entregar"] == 100, m
    assert L["material_sin_entregar"] == 100, L["material_sin_entregar"]
    # la diferencia se mide contra lo que ENTRÓ a la línea: 900 - 850 - 30 - 10 = 10
    assert m["diferencia"] == 10, m
    assert L["material_sin_explicar"] == 10, L["material_sin_explicar"]

    # y la pantalla lo pinta, con la salida hacia Compras
    c = _login(app)
    html = c.get("/calidad/maestro-lotes").data.decode("utf-8")
    for que, pieza in (("el bloque de material", "Material de envase"),
                       ("la columna de lo pedido", ">Pedido</th>"),
                       ("la columna sin explicar", ">Sin explicar</th>"),
                       ("la salida a Compras", 'href="/compras"')):
        assert pieza in html, "la pantalla no muestra %s (%s)" % (que, pieza)


def test_la_diferencia_no_se_recalcula_a_mano(app, db_clean):
    """Dos copias de la misma resta divergen el día que alguien corrige una (M99).

    ⚠ 18-ago · antes esto exigía el NOMBRE `_conc_diferencia` dentro de una ventana FIJA de
    16.000 caracteres. Las dos mitades estaban mal:

      · fijaba la IMPLEMENTACIÓN (qué helper se llama) en vez de la GARANTÍA (que Calidad no
        haga su propia resta) -- y dio rojo con el código correcto el día que el maestro pasó a
        pedirle el número al resolvedor unificado de `brd`, que internamente usa ese mismo
        helper (M97/M216);
      · y una ventana por CONTEO DE CARACTERES la secuestra cualquier función que se escriba
        más abajo, así que deja de proteger sin avisar (M151/M157 · el mismo defecto apareció
        hoy en el guard de los cierres).

    Ahora se acota al cuerpo real de la función y se mide lo que importa: que el número venga de
    `brd` y que acá no haya una resta escrita a mano.
    """
    import re
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "api", "blueprints", "calidad.py")
    fuente = open(ruta, encoding="utf-8").read()
    i = fuente.find("def calidad_maestro_lotes(")
    assert i > 0, "no encontré el maestro de lotes en calidad.py"
    m = re.search(chr(10) + r"(?:@|def )", fuente[i + 30:])
    bloque = fuente[i:i + 30 + (m.start() if m else len(fuente))]

    # sin comentarios: el guard no se puede satisfacer con la nota que lo explica (M154)
    codigo = chr(10).join(ln for ln in bloque.splitlines()
                          if not ln.strip().startswith("#"))

    assert ("_conc_diferencia" in codigo) or ("conciliacion_material_lote" in codigo), (
        "el maestro no le pide la diferencia a `brd`: o llama al helper canónico o al "
        "resolvedor unificado, nunca calcula por su cuenta")

    # Y la garantía dura, medida donde vive: el valor que se publica como `diferencia` no
    # puede salir de una cuenta escrita acá.
    #
    # ⚠ La primera versión de este assert buscaba el texto `requerida - utilizada` y NO mordía:
    # basta con que la resta use otro nombre de variable (`_req - utilizada`) para esquivarla.
    # Un guard que sólo caza la forma literal del bug de ayer no caza el de mañana -- se mide la
    # expresión ASIGNADA, no la redacción (M96).
    asignaciones = re.findall(r"['\"]diferencia['\"]\s*:\s*([^,]+),", codigo)
    assert asignaciones, "el maestro ya no publica una `diferencia` · ¿se renombró el campo?"
    for expr in asignaciones:
        assert not re.search(r"[-+*/]", expr.replace("->", "")), (
            "la diferencia se está calculando en calidad.py en vez de pedírsela a `brd`: %r"
            % expr.strip())
