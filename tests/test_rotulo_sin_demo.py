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
