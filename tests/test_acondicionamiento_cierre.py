"""Cierre de Acondicionamiento (OA) · huecos #1 (cadena OF→OA) y #2 (cierre canónico) · 27-jun-2026.

  · #1 · al CERRAR el envasado se HABILITA automático el legajo de acondicionamiento (espeja OP→OF).
  · #2 · cerrar-acondicionamiento descuenta los materiales listados vía movimientos_mee (canónico) UNA
        sola vez (CAS · 2º cierre → 409).
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


def _h():
    h = {"Content-Type": "application/json"}; h.update(csrf_headers()); return h


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def _q1(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def test_cerrar_acondicionamiento_descuenta_y_cas(app, db_clean):
    c = _login(app, "sebastian")
    mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                   "VALUES ('ZZ-OAC', 1, 'aprobado', 1000, 'sebastian')")
    ebr_id = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, estado, fase, "
                   "iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                   "VALUES (?, 1, 'OAC-OA', 'OAC1', 'iniciado', 'acondicionamiento', 'sebastian', "
                   "datetime('now','utc'), 1000)", (mbr_id,))
    _exec("INSERT OR IGNORE INTO maestro_mee (codigo, descripcion, stock_actual, estado) "
          "VALUES ('ETQ-OAC','Etiqueta',5000,'Activo')")
    r = c.post(f"/api/brd/ebr/{ebr_id}/cerrar-acondicionamiento",
               json={"materiales": [{"codigo": "ETQ-OAC", "cantidad": 100}]}, headers=_h())
    assert r.status_code == 200, r.data
    assert r.get_json().get("n_descuentos") == 1, r.data
    # movimientos_mee Salida (canónico) + estado completado
    assert _q1("SELECT COUNT(*) FROM movimientos_mee WHERE mee_codigo='ETQ-OAC' AND tipo='Salida'")[0] == 1
    assert _q1("SELECT estado FROM ebr_ejecuciones WHERE id=?", (ebr_id,))[0] == "completado"
    # CAS: el 2º cierre NO vuelve a descontar (409)
    r2 = c.post(f"/api/brd/ebr/{ebr_id}/cerrar-acondicionamiento",
                json={"materiales": [{"codigo": "ETQ-OAC", "cantidad": 50}]}, headers=_h())
    assert r2.status_code == 409, r2.data
    assert _q1("SELECT COUNT(*) FROM movimientos_mee WHERE mee_codigo='ETQ-OAC' AND tipo='Salida'")[0] == 1


def test_cerrar_acondicionamiento_sin_materiales_rechaza(app, db_clean):
    c = _login(app, "sebastian")
    mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                   "VALUES ('ZZ-OAC2', 1, 'aprobado', 1000, 'sebastian')")
    ebr_id = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, estado, fase, "
                   "iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                   "VALUES (?, 1, 'OAC2-OA', 'OAC2', 'iniciado', 'acondicionamiento', 'sebastian', "
                   "datetime('now','utc'), 1000)", (mbr_id,))
    r = c.post(f"/api/brd/ebr/{ebr_id}/cerrar-acondicionamiento", json={"materiales": []}, headers=_h())
    assert r.status_code == 400, r.data
    # no se marcó completado
    assert _q1("SELECT estado FROM ebr_ejecuciones WHERE id=?", (ebr_id,))[0] == "iniciado"


def test_cerrar_envasado_encadena_acondicionamiento(app, db_clean):
    c = _login(app, "sebastian")
    c.patch("/api/identidad/sebastian", json={"cedula": "77777777"}, headers=_h())
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) VALUES ('MP-CAD','Agua',1)")
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('ZZ-CAD', 1, 1)")
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES ('ZZ-CAD','MP-CAD','Agua',100,1000)")
    r = c.post("/api/brd/mbr/preparar-aprobado", json={"producto_nombre": "ZZ-CAD"}, headers=_h())
    assert r.status_code == 200, r.data
    _exec("INSERT OR IGNORE INTO maestro_mee (codigo, descripcion, stock_actual, estado) "
          "VALUES ('ENV-CAD','Frasco',1000,'Activo')")
    _exec("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, volumen_ml, "
          "envase_codigo, activo) VALUES ('ZZ-CAD','P30','30ml',30,'ENV-CAD',1)")
    of = c.post("/api/brd/legajo-rapido", json={"producto": "ZZ-CAD", "lote": "LOTECAD", "fase": "envasado"}, headers=_h())
    assert of.status_code == 200, of.data
    of_id = of.get_json()["id"]
    c.post(f"/api/brd/ebr/{of_id}/registrar-unidades",
           json={"presentacion_codigo": "P30", "unidades": 100, "volumen_ml": 30}, headers=_h())
    rc = c.post(f"/api/brd/ebr/{of_id}/cerrar-envasado", json={}, headers=_h())
    assert rc.status_code == 200, rc.data
    # el cierre del envasado encadenó la OA
    assert rc.get_json().get("acond_ebr_id"), rc.data
    assert _q1("SELECT COUNT(*) FROM ebr_ejecuciones WHERE COALESCE(lote_codigo,lote)='LOTECAD' "
               "AND fase='acondicionamiento'")[0] == 1


def _firmar(c, ebr_id, meaning="libera"):
    rc = c.post("/api/sign/challenge", json={"password": TEST_PASSWORD}, headers=csrf_headers())
    token = rc.get_json()["token"]
    rs = c.post("/api/sign", json={"record_table": "ebr_ejecuciones", "record_id": str(ebr_id),
                                   "meaning": meaning, "challenge_token": token}, headers=csrf_headers())
    assert rs.status_code == 201, rs.data
    return rs.get_json()["signature_id"]


def test_liberar_strict_gates_pesaje_y_yield(app, db_clean):
    """Huecos #5/#6 · en strict, un EBR de fabricación NO se libera sin pesajes (#5) ni con yield fuera de
    rango sin justificar (#6). Gateado a EBR_MODE='strict' (app_settings) · no afecta off/warn."""
    c = _login(app, "sebastian")
    c.patch("/api/identidad/sebastian", json={"cedula": "77777777"}, headers=_h())
    _exec("INSERT OR REPLACE INTO app_settings (clave, valor) VALUES ('ebr_mode','strict')")
    try:
        mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                       "VALUES ('ZZ-G56', 1, 'aprobado', 1000, 'sebastian')")
        ebr = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, estado, fase, "
                    "iniciado_por, iniciado_at_utc, cantidad_objetivo_g, cantidad_real_g, yield_pct, "
                    "completado_at_utc) VALUES (?, 1, 'G56-OP', 'G56', 'completado', 'fabricacion', 'sebastian', "
                    "datetime('now','utc'), 1000, 1000, 100.0, datetime('now','utc'))", (mbr_id,))
        # #5 · cero pesajes → 409 SIN_PESAJES
        r = c.post(f"/api/brd/ebr/{ebr}/liberar", json={"signature_id": _firmar(c, ebr)}, headers=_h())
        assert r.status_code == 409 and r.get_json().get("codigo") == "SIN_PESAJES", r.data
        # 1 pesaje (pasa #5) + yield anómalo 50% → 409 YIELD_FUERA_RANGO
        _exec("INSERT INTO ebr_pesajes (ebr_id, material_id, cantidad_teorica_g, cantidad_real_g, pesado_por, "
              "pesado_at_utc) VALUES (?, 'MP1', 1000, 500, 'sebastian', datetime('now','utc'))", (ebr,))
        _exec("UPDATE ebr_ejecuciones SET yield_pct=50.0 WHERE id=?", (ebr,))
        r2 = c.post(f"/api/brd/ebr/{ebr}/liberar", json={"signature_id": _firmar(c, ebr)}, headers=_h())
        assert r2.status_code == 409 and r2.get_json().get("codigo") == "YIELD_FUERA_RANGO", r2.data
        # con justificación → pasa #6 (cae al gate siguiente: pesaje sin 2ª firma)
        r3 = c.post(f"/api/brd/ebr/{ebr}/liberar",
                    json={"signature_id": _firmar(c, ebr), "yield_justificacion": "merma por tara"}, headers=_h())
        assert r3.status_code == 409 and r3.get_json().get("codigo") == "PESAJES_SIN_VERIFICAR", r3.data
    finally:
        _exec("DELETE FROM app_settings WHERE clave='ebr_mode'")
