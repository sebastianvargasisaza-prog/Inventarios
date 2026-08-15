"""La conciliación de material tiene que CERRAR (15-ago-2026 · clon de MyBatch).

MyBatch concilia el material de envase y de empaque con seis columnas:
requerida · recibida · devuelta · utilizada · **averiada** · **diferencia**.
EOS tenía cuatro.

Por qué la averiada no es un detalle: lo devuelto vuelve a bodega y lo averiado no
vuelve de ninguna forma. Sin separarlas, la conciliación cuadra contra material que
ya no existe, y el faltante sin explicar -el número que mira una auditoría- queda
escondido dentro de "devuelta".

La diferencia NO se guarda: se deriva. Un total guardado al lado de sus sumandos
diverge el día que alguien corrige uno solo (M99).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PRODUCTO = "ZZ-CONC-AVER"


def _login(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _legajo(app, lote="LOTE-CONC-1"):
    """Un legajo de envasado listo para conciliar, por los endpoints reales."""
    for sql in ("DELETE FROM mbr_pasos WHERE mbr_template_id IN "
                "(SELECT id FROM mbr_templates WHERE producto_nombre LIKE 'ZZ-CONC%')",
                "DELETE FROM mbr_templates WHERE producto_nombre LIKE 'ZZ-CONC%'",
                "DELETE FROM formula_items WHERE producto_nombre LIKE 'ZZ-CONC%'",
                "DELETE FROM formula_headers WHERE producto_nombre LIKE 'ZZ-CONC%'"):
        try:
            _exec(sql)
        except Exception:
            pass
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) "
          "VALUES ('MP-CONC-A','Agua',1)")
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,1,1)",
          (PRODUCTO,))
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
          "porcentaje, cantidad_g_por_lote) VALUES (?,'MP-CONC-A','Agua',100,1000)",
          (PRODUCTO,))
    c = _login(app)
    c.post("/api/brd/mbr/generar-desde-formula",
           json={"producto_nombre": PRODUCTO}, headers=_h())
    c.post("/api/brd/mbr/cargar-instructivo",
           json={"producto": PRODUCTO, "fase": "envasado",
                 "pasos": ["Paso 1. Llenar.", "Paso 2. Sellar."]}, headers=_h())
    c.post("/api/brd/mbr/preparar-aprobado",
           json={"producto_nombre": PRODUCTO}, headers=_h())
    r = c.post("/api/brd/legajo-rapido",
               json={"producto": PRODUCTO, "lote": lote, "fase": "envasado"},
               headers=_h())
    assert r.status_code in (200, 201), r.data
    d = r.get_json()
    return c, (d.get("id") or d.get("ebr_id"))


def test_lo_averiado_se_registra_aparte_de_lo_devuelto(app, db_clean):
    c, ebr_id = _legajo(app)
    r = c.post(f"/api/brd/ebr/{ebr_id}/conciliacion-material",
               json={"tipo": "envase", "material_nombre": "Frasco 30 ml",
                     "cant_requerida": 500, "cant_recibida": 500,
                     "cant_devuelta": 20, "cant_averiada": 5,
                     "cant_utilizada": 475}, headers=_h())
    assert r.status_code == 201, r.data
    fila = (c.get(f"/api/brd/ebr/{ebr_id}/conciliacion-material")
            .get_json()["items"])[0]
    assert fila["cant_averiada"] == 5, "lo averiado no quedó registrado: %s" % fila
    assert fila["cant_devuelta"] == 20, fila
    # 500 recibidas = 475 usadas + 20 devueltas + 5 averiadas -> cierra en cero
    assert fila["diferencia"] == 0, ("la conciliación no cierra: %s" % fila)


def test_la_diferencia_delata_el_material_que_falta_explicar(app, db_clean):
    c, ebr_id = _legajo(app, "LOTE-CONC-2")
    r = c.post(f"/api/brd/ebr/{ebr_id}/conciliacion-material",
               json={"tipo": "etiqueta", "material_nombre": "Etiqueta 30 ml",
                     "cant_requerida": 300, "cant_recibida": 300,
                     "cant_devuelta": 0, "cant_averiada": 0,
                     "cant_utilizada": 280}, headers=_h())
    assert r.status_code == 201, r.data
    fila = (c.get(f"/api/brd/ebr/{ebr_id}/conciliacion-material")
            .get_json()["items"])[0]
    assert fila["diferencia"] == 20, (
        "20 etiquetas no se pueden explicar y la pantalla debería decirlo: %s" % fila)


def test_sin_utilizada_se_deriva_descontando_tambien_lo_averiado(app, db_clean):
    """Si no se teclea la utilizada, sale de lo que entró menos lo que salió por
    los otros dos caminos. Antes se olvidaba de lo averiado y la inflaba."""
    c, ebr_id = _legajo(app, "LOTE-CONC-3")
    r = c.post(f"/api/brd/ebr/{ebr_id}/conciliacion-material",
               json={"tipo": "envase", "material_nombre": "Frasco sin utilizada",
                     "cant_requerida": 100, "cant_recibida": 100,
                     "cant_devuelta": 10, "cant_averiada": 4}, headers=_h())
    assert r.status_code == 201, r.data
    assert r.get_json()["cant_utilizada"] == 86, r.data
    fila = (c.get(f"/api/brd/ebr/{ebr_id}/conciliacion-material")
            .get_json()["items"])[0]
    assert fila["diferencia"] == 0, fila


def test_la_pantalla_muestra_averiada_y_diferencia(app, db_clean):
    """Un dato que el backend manda y la pantalla no pinta no existe (M115)."""
    import re
    c = _login(app)
    html = c.get("/inventarios").data.decode("utf-8")
    # El JS del legajo se sirve en /planta-core.js y /planta-app.js: mirar sólo el
    # HTML concluiría que la pantalla no existe (M166).
    pub = app.test_client()
    for src in re.findall(r'<script[^>]+src="(/[^"?]+)', html):
        rj = pub.get(src)
        if rj.status_code == 200:
            html += rj.data.decode("utf-8", "replace")
    # Se exige el CAMPO y la COLUMNA, no la mención: el id aparece también en la
    # función que lo lee, así que buscarlo suelto pasaría verde con el formulario
    # sin el campo (el guard mediría otra cosa · M152).
    piezas = {
        'el campo para cargar lo averiado': 'placeholder="Averiada"',
        'la columna Averiada de la tabla': '>Averiada</th>',
        'la columna Diferencia de la tabla': '>Diferencia</th>',
        'el envío de cant_averiada al backend': 'cant_averiada:',
    }
    for que, pieza in piezas.items():
        assert pieza in html, "falta %s (%s)" % (que, pieza)
