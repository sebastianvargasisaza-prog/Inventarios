"""La conciliación del granel tiene que VERSE en el legajo (15-ago-2026).

Clonando MyBatch buscaba dos cosas que faltaban: el "saldo del granel" (su campo
*Cantidad por Envasar*) y el rendimiento. Al medir aparecieron **ya calculadas** y
mejor que en MyBatch — `_conciliacion_granel` da granel disponible, envasado,
remanente, diferencia en mL y %, tolerancia, rendimiento y unidades teóricas —
pero se exponían **sólo en `/vista-completa`**, que la pantalla del legajo no
llama. El número existía y no lo veía nadie (M115).

Este guard fija las dos mitades: que el detalle lo entregue y que la pantalla lo
pinte, incluidos los avisos de lo que NO se pudo calcular (un cero sin aviso se
lee como "la cuenta cierra" · M100/M124).
"""
import os
import re
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PRODUCTO = "ZZ-GRANEL-VIS"


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


def _legajo_envasado(app, lote="LOTE-GV-1"):
    for sql in ("DELETE FROM mbr_pasos WHERE mbr_template_id IN "
                "(SELECT id FROM mbr_templates WHERE producto_nombre LIKE 'ZZ-GRANEL%')",
                "DELETE FROM mbr_templates WHERE producto_nombre LIKE 'ZZ-GRANEL%'",
                "DELETE FROM formula_items WHERE producto_nombre LIKE 'ZZ-GRANEL%'",
                "DELETE FROM formula_headers WHERE producto_nombre LIKE 'ZZ-GRANEL%'"):
        try:
            _exec(sql)
        except Exception:
            pass
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) "
          "VALUES ('MP-GV','Agua',1)")
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,1,1)",
          (PRODUCTO,))
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
          "porcentaje, cantidad_g_por_lote) VALUES (?,'MP-GV','Agua',100,1000)", (PRODUCTO,))
    c = _login(app)
    c.post("/api/brd/mbr/generar-desde-formula",
           json={"producto_nombre": PRODUCTO}, headers=_h())
    c.post("/api/brd/mbr/cargar-instructivo",
           json={"producto": PRODUCTO, "fase": "envasado",
                 "pasos": ["Paso 1. Llenar."]}, headers=_h())
    c.post("/api/brd/mbr/preparar-aprobado",
           json={"producto_nombre": PRODUCTO}, headers=_h())
    r = c.post("/api/brd/legajo-rapido",
               json={"producto": PRODUCTO, "lote": lote, "fase": "envasado"}, headers=_h())
    assert r.status_code in (200, 201), r.data
    return c, (r.get_json().get("id") or r.get_json().get("ebr_id"))


def test_el_detalle_del_legajo_trae_la_conciliacion_del_granel(app, db_clean):
    c, ebr_id = _legajo_envasado(app)
    # 20 L de granel disponibles y 500 unidades de 30 mL envasadas = 15 L
    _exec("UPDATE ebr_ejecuciones SET ml_envasable=20000, densidad_g_ml=1.0 WHERE id=?", (ebr_id,))
    _exec("INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, etiqueta, "
          "volumen_ml, unidades, registrado_por, registrado_at_utc) "
          "VALUES (?,'P30','30 ml',30,500,'test',datetime('now','utc'))", (ebr_id,))

    d = c.get(f"/api/brd/ebr/{ebr_id}").get_json()
    cg = d.get("conciliacion_granel")
    assert cg and cg.get("aplica"), (
        "el legajo no trae la conciliación del granel: el saldo se calcula y no se ve")
    assert cg["disponible_ml"] == 20000, cg
    assert cg["envasado_ml"] == 15000, cg
    # el saldo del granel · lo que MyBatch llama "Cantidad por Envasar"
    assert cg["diferencia_ml"] == 5000, cg
    assert cg["rendimiento_ml_pct"] == 75.0, cg
    # con UNA sola presentación se puede decir cuántas unidades debían salir
    assert cg["unidades_teoricas"] == 666, cg


def test_declara_lo_que_no_pudo_calcular(app, db_clean):
    """Sin remanente declarado la cuenta NO cierra, y eso se dice: un cero sin
    aviso se lee como 'cuadra' y es lo contrario (M100/M124)."""
    c, ebr_id = _legajo_envasado(app, "LOTE-GV-2")
    _exec("UPDATE ebr_ejecuciones SET ml_envasable=10000 WHERE id=?", (ebr_id,))
    cg = c.get(f"/api/brd/ebr/{ebr_id}").get_json().get("conciliacion_granel")
    assert cg["falta_remanente"] is True, cg
    assert cg["cuadra"] is False, "sin remanente declarado no puede darse por cuadrada"


def test_la_pantalla_pinta_la_conciliacion_del_granel(app, db_clean):
    c = _login(app)
    html = c.get("/inventarios").data.decode("utf-8")
    pub = app.test_client()
    for src in re.findall(r'<script[^>]+src="(/[^"?]+)', html):
        rj = pub.get(src)
        if rj.status_code == 200:
            html += rj.data.decode("utf-8", "replace")
    for que, pieza in (("la sección", "Conciliación del granel"),
                       ("el granel disponible", "Granel disponible"),
                       ("el saldo", "Diferencia"),
                       ("el rendimiento", "Rendimiento"),
                       ("el aviso de remanente faltante", "falta declarar el remanente"),
                       ("la lectura del dato", "d.conciliacion_granel")):
        assert pieza in html, "la pantalla no muestra %s (%s)" % (que, pieza)
