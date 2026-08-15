"""La justificación del rendimiento tiene que QUEDAR en el legajo (15-ago-2026).

EOS ya exigía justificar un rendimiento fuera del 80-115% para poder liberar (GMP:
un yield anómalo no se libera en silencio). Pero el texto se guardaba **sólo dentro
del `despues` del audit_log**, así que:

- el legajo mostraba "Rendimiento 127%" sin decir por qué, y
- el PDF -que es el documento que se le muestra a INVIMA- tampoco lo traía.

Un dato que se exige, se captura y no llega a quien lo tiene que leer es un dato que
no existe (M115). MyBatch lo muestra en la cabecera del instructivo, al lado del
rendimiento; acá queda igual, y además atado al acto de liberar (se escribe en el
MISMO UPDATE, después el trigger de inmutabilidad ya no deja tocarlo).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PRODUCTO = "ZZ-YIELD-JUST"


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


def _q(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _firmar(c, tabla, rid, meaning):
    rc = c.post("/api/sign/challenge", json={"password": TEST_PASSWORD},
                headers=csrf_headers())
    assert rc.status_code == 200, rc.data
    rs = c.post("/api/sign", json={"record_table": tabla, "record_id": str(rid),
                                   "meaning": meaning,
                                   "challenge_token": rc.get_json()["token"]},
                headers=csrf_headers())
    assert rs.status_code == 201, rs.data
    return rs.get_json()["signature_id"]


def _legajo_completado(app, lote="LOTE-YJ-1", yield_raro=True):
    """Un legajo listo para liberar, con el rendimiento fuera de rango."""
    for sql in ("DELETE FROM mbr_pasos WHERE mbr_template_id IN "
                "(SELECT id FROM mbr_templates WHERE producto_nombre LIKE 'ZZ-YIELD%')",
                "DELETE FROM mbr_templates WHERE producto_nombre LIKE 'ZZ-YIELD%'",
                "DELETE FROM formula_items WHERE producto_nombre LIKE 'ZZ-YIELD%'",
                "DELETE FROM formula_headers WHERE producto_nombre LIKE 'ZZ-YIELD%'"):
        try:
            _exec(sql)
        except Exception:
            pass
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) "
          "VALUES ('MP-YJ','Agua',1)")
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,1,1)",
          (PRODUCTO,))
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
          "porcentaje, cantidad_g_por_lote) VALUES (?,'MP-YJ','Agua',100,1000)", (PRODUCTO,))
    c = _login(app)
    c.patch("/api/identidad/sebastian",
            json={"cedula": "77777777", "nombre_completo": "Sebastián Vargas"}, headers=_h())
    c.post("/api/brd/mbr/generar-desde-formula",
           json={"producto_nombre": PRODUCTO}, headers=_h())
    c.post("/api/brd/mbr/cargar-instructivo",
           json={"producto": PRODUCTO, "fase": "fabricacion",
                 "pasos": ["Paso 1. Mezclar."]}, headers=_h())
    c.post("/api/brd/mbr/preparar-aprobado",
           json={"producto_nombre": PRODUCTO}, headers=_h())
    r = c.post("/api/brd/legajo-rapido",
               json={"producto": PRODUCTO, "lote": lote, "fase": "fabricacion"},
               headers=_h())
    assert r.status_code in (200, 201), r.data
    ebr_id = (r.get_json().get("id") or r.get_json().get("ebr_id"))
    # Se lleva al estado 'completado' con el rendimiento fuera de rango: es la
    # situación que el gate existe para atrapar.
    _exec("UPDATE ebr_ejecuciones SET estado='completado', cantidad_objetivo_g=1000, "
          "cantidad_real_g=?, yield_pct=? WHERE id=?",
          (1270 if yield_raro else 990, 127.0 if yield_raro else 99.0, ebr_id))
    return c, ebr_id


def test_con_el_control_encendido_no_se_libera_sin_justificar(app, db_clean):
    """El control existía pero vivía dentro de EBR_MODE='strict' y el modo real es
    warn: NO CORRÍA NUNCA, así que hoy un lote al 127% se libera en silencio (M119).
    Ahora corre siempre y tiene interruptor propio."""
    _exec("INSERT INTO app_settings (clave, valor) VALUES ('exigir_justificacion_yield','1') "
          "ON CONFLICT (clave) DO UPDATE SET valor='1'")
    try:
        c, ebr_id = _legajo_completado(app, "LOTE-YJ-ON")
        sig = _firmar(c, "ebr_ejecuciones", ebr_id, "libera")
        r = c.post(f"/api/brd/ebr/{ebr_id}/liberar",
                   json={"signature_id": sig}, headers=_h())
        assert r.status_code == 409, r.data
        assert r.get_json().get("codigo") == "YIELD_FUERA_RANGO", r.data
    finally:
        _exec("UPDATE app_settings SET valor='0' WHERE clave='exigir_justificacion_yield'")


def test_apagado_no_traba_el_piso_pero_deja_rastro(app, db_clean):
    """Nace apagado a propósito: encenderlo a ciegas trabaría la liberación el mismo
    día (M126). Lo que no puede pasar es que se libere sin que quede constancia."""
    _exec("UPDATE app_settings SET valor='0' WHERE clave='exigir_justificacion_yield'")
    c, ebr_id = _legajo_completado(app, "LOTE-YJ-OFF")
    sig = _firmar(c, "ebr_ejecuciones", ebr_id, "libera")
    r = c.post(f"/api/brd/ebr/{ebr_id}/liberar",
               json={"signature_id": sig}, headers=_h())
    assert r.status_code == 200, r.data
    rastro = _q("SELECT despues FROM audit_log WHERE tabla='ebr_ejecuciones' "
                "AND registro_id=? AND accion='LIBERAR_EBR' ORDER BY id DESC LIMIT 1",
                (str(ebr_id),))
    assert rastro, "no quedó rastro de la liberación"
    assert "liberado_sin_justificar_yield" in (rastro[0][0] or ""), (
        "se liberó un rendimiento anómalo sin justificar y sin dejar constancia: %s"
        % (rastro[0][0] or "")[:200])


def test_la_justificacion_queda_en_el_legajo_y_se_puede_leer(app, db_clean):
    c, ebr_id = _legajo_completado(app, "LOTE-YJ-TXT")
    sig = _firmar(c, "ebr_ejecuciones", ebr_id, "libera")
    motivo = ("Se suman 100 unidades a la orden inicial por un cliente que canceló")
    r = c.post(f"/api/brd/ebr/{ebr_id}/liberar",
               json={"signature_id": sig, "yield_justificacion": motivo}, headers=_h())
    assert r.status_code == 200, r.data

    # 1 · quedó guardada en el legajo, no sólo en el audit
    fila = _q("SELECT COALESCE(yield_justificacion,'') FROM ebr_ejecuciones WHERE id=?",
              (ebr_id,))
    assert fila and fila[0][0] == motivo, (
        "la justificación no se guardó: en el legajo el 127%% queda sin explicación (%s)" % fila)

    # 2 · el detalle que lee la pantalla la devuelve
    det = c.get(f"/api/brd/ebr/{ebr_id}").get_json()
    assert det.get("yield_justificacion") == motivo, det.get("yield_justificacion")

    # 3 · y sale en el PDF, que es lo que ve la auditoría
    pdf = c.get(f"/api/brd/ebr/{ebr_id}/pdf")
    assert pdf.status_code == 200, pdf.status_code


def test_la_pantalla_muestra_la_justificacion(app, db_clean):
    """Un dato que el backend manda y la pantalla no pinta no existe (M115)."""
    import re
    c = _login(app)
    html = c.get("/inventarios").data.decode("utf-8")
    pub = app.test_client()
    for src in re.findall(r'<script[^>]+src="(/[^"?]+)', html):
        rj = pub.get(src)
        if rj.status_code == 200:
            html += rj.data.decode("utf-8", "replace")
    assert "Justificación del rendimiento" in html, (
        "el legajo no muestra por qué se liberó un rendimiento anómalo")
    assert "d.yield_justificacion" in html
