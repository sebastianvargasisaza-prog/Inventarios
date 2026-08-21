"""Un rótulo regulado no puede hablar de un lote de DEMOSTRACIÓN · 21-ago-2026.

Sebastián, urgente, con los rótulos abiertos: *"el rótulo de limpieza no está jalando"* · *"el
producto aparece el demo en todos"*. Medido en producción: **37 de 70 rótulos** salían con
"DEMO PLANTA (BORRAR)" como producto a elaborar.

Dos causas, y las dos de la misma familia:
  · el derivador tomaba la primera producción del área sin mirar si era un demo, y el demo del
    17-ago dejó 62 lotes abiertos ocupando las salas;
  · el botón "Limpiar demos" buscaba "SIMULACRO" o "PRUEBA" y el demo de Planta se llama
    "DEMO PLANTA (BORRAR)", así que nunca los borró (M248: el vocabulario lo define quien
    ESCRIBE el dato, no quien lo lee).

Y lo que se agregó en el mismo movimiento (Sebastián): *"pon todos los datos del rótulo que se
puedan escribir y que se impriman, así deciden qué escribir"*.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur
    finally:
        conn.close()


def _area_fab():
    """Un área que produce, con su id."""
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        r = conn.execute(
            "SELECT id, codigo FROM areas_planta WHERE activo=1 AND puede_producir=1 "
            "ORDER BY orden, id LIMIT 1").fetchone()
    finally:
        conn.close()
    assert r, "no hay área de fabricación sembrada"
    return r[0], r[1]


def _limpiar(aid):
    """Limpiar ANTES de sembrar (M103)."""
    _sql("DELETE FROM produccion_programada WHERE area_id=? AND producto LIKE 'ZROT%'", (aid,))
    _sql("DELETE FROM rotulos_limpieza WHERE area_id=?", (aid,))


def test_reconoce_las_dos_formas_de_nombrar_un_demo(app, db_clean):
    """El batch record marca el LOTE (`DEMO-`), el demo de Planta marca el NOMBRE. Un
    vocabulario solo deja pasar al otro."""
    with app.app_context():
        from blueprints.programacion import _es_produccion_demo
        for p, l in (("DEMO PLANTA (BORRAR)", "DEMPLA(BO-6350"),
                     ("SIMULACRO Demo", ""),
                     ("Lote de PRUEBA", ""),
                     ("AZ HIBRID CLEAR", "DEMO-PLANTA-1")):
            assert _es_produccion_demo(p, l) is True, "no reconoció %r / %r" % (p, l)
        assert _es_produccion_demo("AZ HIBRID CLEAR", "AZHIB-4210-20260821") is False, \
            "marcó como demo una producción real"
        assert _es_produccion_demo("", "") is False


def test_el_rotulo_no_nombra_el_lote_demo_y_si_el_real(app, db_clean):
    """Con un demo abierto en la sala, el rótulo tiene que seguir hablando del lote de verdad."""
    aid, acod = _area_fab()
    _limpiar(aid)
    from datetime import date, timedelta
    hoy = date.today().isoformat()
    ayer = (date.today() - timedelta(days=1)).isoformat()
    # El demo entra PRIMERO y ya iniciado: sin el filtro, es el que gana el orden.
    _sql("INSERT INTO produccion_programada (producto, fecha_programada, lotes, area_id, "
         "estado, inicio_real_at) VALUES (?,?,1,?,'en_proceso',?)",
         ("ZROT DEMO PLANTA (BORRAR)", ayer, aid, ayer + " 08:00:00"))
    _sql("INSERT INTO produccion_programada (producto, fecha_programada, lotes, area_id, "
         "estado) VALUES (?,?,1,?,'programado')", ("ZROT PRODUCTO REAL", hoy, aid))
    c = _login(app)
    html = c.get("/planta/rotulos-limpieza?area=%s&todos=1" % acod).get_data(as_text=True)
    assert "ZROT DEMO PLANTA" not in html, "el rótulo imprimió el lote de demostración"
    assert "ZROT PRODUCTO REAL" in html, "no jaló la producción real del área"
    _limpiar(aid)


def test_los_campos_escritos_mandan_y_el_vacio_deja_la_linea(app, db_clean):
    """*"pon todos los datos del rótulo que se puedan escribir y que se impriman"*. Vacío es
    una decisión: dejar la línea para llenarla a mano (mismo criterio que sanitizante)."""
    aid, acod = _area_fab()
    _limpiar(aid)
    from datetime import date
    _sql("INSERT INTO produccion_programada (producto, fecha_programada, lotes, area_id, "
         "estado) VALUES (?,?,1,?,'programado')",
         ("ZROT DERIVADO", date.today().isoformat(), aid))
    c = _login(app)
    url = ("/planta/rotulos-limpieza?area=%s&todos=1"
           "&prod=ZROT%%20ESCRITO&lote=ZL-9&prod_prev=&lote_prev=ZPREV-1" % acod)
    html = c.get(url).get_data(as_text=True)
    assert "ZROT ESCRITO" in html, "no imprimió el producto que se escribió"
    assert "ZL-9" in html and "ZPREV-1" in html, "no imprimió el lote escrito"
    assert "ZROT DERIVADO" not in html, "lo escrito no le ganó a lo derivado"
    # Y la pantalla previa ofrece los cuatro campos.
    sel = c.get("/planta/rotulos-limpieza?area=%s" % acod).get_data(as_text=True)
    for cid in ("prod", "lote", "prod_prev", "lote_prev"):
        assert ('id="%s"' % cid) in sel, "falta el campo %s en la pantalla previa" % cid
    _limpiar(aid)


def test_limpiar_demos_reconoce_al_demo_de_planta(app, db_clean):
    """Buscaba SIMULACRO o PRUEBA, así que los 62 lotes del demo de Planta -- que se llama
    "DEMO PLANTA (BORRAR)" -- quedaron abiertos ocupando las salas."""
    aid, _acod = _area_fab()
    _limpiar(aid)
    from datetime import date
    _sql("INSERT INTO produccion_programada (producto, fecha_programada, lotes, area_id, "
         "estado) VALUES (?,?,1,?,'programado')",
         ("ZROT DEMO PLANTA (BORRAR)", date.today().isoformat(), aid))
    c = _login(app)
    r = c.post("/api/planta/simulacro/limpiar", json={}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        n = conn.execute("SELECT COUNT(*) FROM produccion_programada "
                         "WHERE producto='ZROT DEMO PLANTA (BORRAR)'").fetchone()[0]
    finally:
        conn.close()
    assert n == 0, "el limpiador dejó vivo el lote del demo de Planta"
    _limpiar(aid)


def test_los_campos_se_autocargan_con_lo_que_ya_hay(app, db_clean):
    """*"debería auto cargar lo que ya está: el nombre del producto, cantidad, todo lo que
    esté"* (Sebastián 21-ago). Con sala elegida sale de esa sala; sin sala, del lote que está
    corriendo en la planta. Lo que el sistema NO sabe queda vacío: no se inventa un producto."""
    aid, acod = _area_fab()
    _limpiar(aid)
    from datetime import date
    _sql("INSERT INTO produccion_programada (producto, fecha_programada, lotes, area_id, "
         "estado, inicio_real_at) VALUES (?,?,1,?,'en_proceso',?)",
         ("ZROT EN CURSO", date.today().isoformat(), aid, date.today().isoformat() + " 07:00:00"))
    c = _login(app)
    # (a) viniendo de la sala
    sel = c.get("/planta/rotulos-limpieza?area=%s" % acod).get_data(as_text=True)
    assert "ZROT EN CURSO" in sel, "no autocargó el producto de la sala elegida"
    # (b) sin sala: igual trae el lote que está corriendo
    sel2 = c.get("/planta/rotulos-limpieza").get_data(as_text=True)
    assert "ZROT EN CURSO" in sel2, "sin sala elegida no autocargó lo que está corriendo"
    _limpiar(aid)


def test_un_demo_no_se_autocarga(app, db_clean):
    """La autocarga no puede meter por la ventana lo que el rótulo acaba de dejar de imprimir."""
    aid, acod = _area_fab()
    _limpiar(aid)
    from datetime import date
    _sql("INSERT INTO produccion_programada (producto, fecha_programada, lotes, area_id, "
         "estado, inicio_real_at) VALUES (?,?,1,?,'en_proceso',?)",
         ("ZROT DEMO PLANTA (BORRAR)", date.today().isoformat(), aid,
          date.today().isoformat() + " 07:00:00"))
    c = _login(app)
    sel = c.get("/planta/rotulos-limpieza").get_data(as_text=True)
    assert "ZROT DEMO PLANTA" not in sel, "autocargó un lote de demostración"
    _limpiar(aid)


def test_el_rotulo_no_lleva_raya_ni_el_nombre_de_la_empresa(app, db_clean):
    """*"cuando algo no está escrito sale una raya, quitala para que puedan escribir a mano"* y
    *"el encabezado deja solo el logo, quita ESPAGIRIA Laboratorio SAS, el logo ya lo dice"*."""
    aid, acod = _area_fab()
    _limpiar(aid)
    c = _login(app)
    html = c.get("/planta/rotulos-limpieza?area=%s&todos=1&prod=&lote=" % acod).get_data(as_text=True)
    assert ">—<" not in html, "sigue imprimiendo la raya en los campos vacíos"
    assert 'class="co"' not in html, "el nombre de la empresa sigue ocupando el encabezado"
    assert 'class="vacio"' in html or 'class="num vacio"' in html, "las celdas vacías no dejan renglón"
    # Y desde la hoja se puede volver a elegir equipos sin cerrar la pestaña.
    assert "Elegir equipos" in html or "Elegir otros equipos" in html, \
        "no hay forma de volver al selector desde la impresión"
    _limpiar(aid)


def test_el_area_tiene_su_propio_rotulo_y_el_del_equipo_no_la_menciona(app, db_clean):
    """*"Aquí es UNO SOLO que diga área, no repetido; pero los rótulos de equipo no llevan área,
    entonces debe decir sólo equipo sin área. Y además necesito rótulos PARA EL ÁREA"* (Sebastián
    21-ago, con los rótulos impresos delante).

    Reemplaza al guard de la mañana, que fijaba la implementación anterior (un desplegable de área
    dentro del formulario, cuyo valor se imprimía como un renglón más en TODOS los rótulos). Esa
    forma repetía el área en el rótulo de la sala y la afirmaba en el de la máquina -- y una
    máquina se mueve entre salas, así que el papel pegado en ella prometía algo que puede dejar de
    ser cierto (es la misma razón por la que el 20-ago se quitó "Sala / área").

    La garantía que sí importa: el ÁREA es un ítem que se puede pedir y trae su propio rótulo; el
    del EQUIPO habla del equipo y de nada más."""
    aid, acod = _area_fab()
    _limpiar(aid)
    c = _login(app)
    # (a) la sala se puede pedir como un ítem más de la lista
    sel = c.get("/planta/rotulos-limpieza?area=%s" % acod).get_data(as_text=True)
    assert 'value="AREA:%s"' % acod in sel, "el área no se puede elegir en el selector"
    # (b) pedirla produce un rótulo de ÁREA -- encabezado propio y sin renglón de equipo
    hoja_area = c.get("/planta/rotulos-limpieza?equipos=AREA:%s&estados=limpio" % acod
                      ).get_data(as_text=True)
    assert hoja_area.count('class="sheet"') == 1, "no salió el rótulo del área"
    assert "rea &middot; c" in hoja_area or "rea · c" in hoja_area,         "el rótulo del área no se nombra como área"
    assert "Equipo &middot; c" not in hoja_area and "Equipo · c" not in hoja_area,         "el rótulo del área no debería encabezarse como equipo"
    # (c) el rótulo de un EQUIPO no menciona el área por ningún lado
    # El equipo se SIEMBRA: condicionarlo a que el área ya tenga uno dejaba el guard sin medir
    # -- y pasó verde con el bug puesto (M96). Limpieza ANTES, con código fijo (M103).
    _sql("DELETE FROM equipos_planta WHERE codigo=?", ("EQ-ROT-TEST",))
    _sql("INSERT INTO equipos_planta (codigo, nombre, area_codigo, tipo, activo) "
         "VALUES (?,?,?,?,1)", ("EQ-ROT-TEST", "Marmita de prueba", acod, "otro"))
    try:
        hoja_eq = c.get("/planta/rotulos-limpieza?equipos=EQ-ROT-TEST&estados=limpio"
                        ).get_data(as_text=True)
        assert hoja_eq.count('class="sheet"') == 1, "no salió el rótulo del equipo"
        assert "Equipo &middot; c" in hoja_eq or "Equipo · c" in hoja_eq,             "el rótulo del equipo no se nombra como equipo"
        assert ">&Aacute;rea<" not in hoja_eq and ">Área<" not in hoja_eq,             "el rótulo del equipo no lleva área (la máquina se mueve de sala)"
    finally:
        _sql("DELETE FROM equipos_planta WHERE codigo=?", ("EQ-ROT-TEST",))
    _limpiar(aid)
