"""Batch A · gates de seguridad EBR antes de prod (audit 3-jun).

Cubre:
  · candado multi-lote al aceptar (lotes>1 con EBR activo → 409)
  · asignar lote físico real reemplaza el provisional + propaga a movimientos
  · gate directo de IPC OOS al liberar (fail-closed, independiente del texto)
  · pesaje exige rol ejecutor
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


def _firmar(c, *, record_table, record_id, meaning):
    rc = c.post("/api/sign/challenge", json={"password": TEST_PASSWORD}, headers=csrf_headers())
    token = rc.get_json()["token"]
    rs = c.post("/api/sign", json={"record_table": record_table, "record_id": str(record_id),
                                   "meaning": meaning, "challenge_token": token}, headers=csrf_headers())
    assert rs.status_code == 201, rs.data
    return rs.get_json()["signature_id"]


def test_candado_multilote_bloquea_aceptar(app, db_clean, monkeypatch):
    """Con EBR encendido (warn/strict) y lotes>1 → 409 EBR_MULTILOTE_NO_SOPORTADO."""
    import blueprints.programacion as _prog
    c = _login(app)
    monkeypatch.setattr(_prog, "EBR_MODE", "warn")
    pp = _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado) "
               "VALUES ('MULTI-LOTE-T1', date('now'), 3, 'pendiente')")
    r = c.post(f"/api/planta/aceptar-produccion/{pp}", json={}, headers=_h())
    assert r.status_code == 409, r.data
    assert r.get_json().get("codigo") == "EBR_MULTILOTE_NO_SOPORTADO", r.data
    # con EBR_MODE=off, el candado no aplica (no se crea EBR)
    monkeypatch.setattr(_prog, "EBR_MODE", "off")
    r2 = c.post(f"/api/planta/aceptar-produccion/{pp}", json={}, headers=_h())
    assert r2.status_code == 200, r2.data


def test_asignar_lote_fisico_propaga(app, db_clean):
    """Reasigna el lote provisional al lote físico real y arrastra el movimiento."""
    c = _login(app)
    mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                   "VALUES ('LF-T1', 1, 'aprobado', 1000, 'sebastian')")
    ebr_id = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, estado, "
                   "iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                   "VALUES (?, 1, 'PP999', 'en_proceso', 'sebastian', datetime('now','utc'), 1000)", (mbr_id,))
    # un movimiento de Entrada con el lote provisional (simula PT en cuarentena)
    _exec("INSERT INTO movimientos (material_id, tipo, cantidad, lote, fecha) "
          "VALUES ('PT-LF-T1', 'Entrada', 10, 'PP999', date('now'))")
    r = c.post(f"/api/brd/ebr/{ebr_id}/asignar-lote-fisico",
               json={"lote_fisico": "PROD-2026-0007"}, headers=_h())
    assert r.status_code == 200, r.data
    assert r.get_json()["movimientos_actualizados"] == 1, r.data
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        lote = conn.execute("SELECT lote FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()[0]
        mov = conn.execute("SELECT COUNT(*) FROM movimientos WHERE lote='PROD-2026-0007' AND tipo='Entrada'").fetchone()[0]
    finally:
        conn.close()
    assert lote == "PROD-2026-0007"
    assert mov == 1


def test_no_reasignar_lote_si_liberado(app, db_clean):
    c = _login(app)
    mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                   "VALUES ('LF-T2', 1, 'aprobado', 1000, 'sebastian')")
    ebr_id = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, estado, "
                   "iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                   "VALUES (?, 1, 'PP998', 'liberado', 'sebastian', datetime('now','utc'), 1000)", (mbr_id,))
    r = c.post(f"/api/brd/ebr/{ebr_id}/asignar-lote-fisico",
               json={"lote_fisico": "X"}, headers=_h())
    assert r.status_code == 409, r.data


def test_liberar_bloquea_ipc_oos_sin_desviacion(app, db_clean):
    """Gate directo: IPC conforme=0 sin desviación resuelta → 409 IPC_OOS_SIN_RESOLVER,
    aunque no haya desviación que el matching textual pudiera encontrar."""
    c = _login(app)
    c.patch("/api/identidad/sebastian", json={"cedula": "77777777"}, headers=_h())
    mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                   "VALUES ('OOS-T1', 1, 'draft', 1000, 'sebastian')")
    spec_id = _exec("INSERT INTO ipc_specs (mbr_template_id, parametro, unidad, valor_min, valor_max, obligatorio) "
                    "VALUES (?, 'pH', '', 5.0, 7.0, 0)", (mbr_id,))  # NO obligatorio
    _exec("UPDATE mbr_templates SET estado='aprobado' WHERE id=?", (mbr_id,))
    ebr_id = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, estado, "
                   "iniciado_por, iniciado_at_utc, cantidad_objetivo_g, cantidad_real_g) "
                   "VALUES (?, 1, 'OOS-LOTE-1', 'completado', 'sebastian', datetime('now','utc'), 1000, 970)", (mbr_id,))
    # IPC OOS conforme=0 SIN desviación enlazada (simula el fallo de auto-desviación)
    _exec("INSERT INTO ipc_resultados (ebr_id, ipc_spec_id, valor_medido, conforme, medido_por, medido_at_utc) "
          "VALUES (?, ?, 9.0, 0, 'sebastian', datetime('now','utc'))", (ebr_id, spec_id))
    sig = _firmar(c, record_table="ebr_ejecuciones", record_id=ebr_id, meaning="libera")
    r = c.post(f"/api/brd/ebr/{ebr_id}/liberar", json={"signature_id": sig}, headers=_h())
    assert r.status_code == 409, r.data
    assert r.get_json().get("codigo") == "IPC_OOS_SIN_RESOLVER", r.data


def test_pesaje_exige_rol_ejecutor(app, db_clean):
    """Un usuario sin rol de planta/calidad/admin no puede reportar pesaje."""
    # jefferson es marketing, no ejecutor de lote
    c = _login(app, "jefferson")
    mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                   "VALUES ('ROL-T1', 1, 'aprobado', 1000, 'sebastian')")
    ebr_id = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, estado, "
                   "iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                   "VALUES (?, 1, 'ROL-LOTE-1', 'en_proceso', 'sebastian', datetime('now','utc'), 1000)", (mbr_id,))
    r = c.post(f"/api/brd/ebr/{ebr_id}/pesajes",
               json={"material_id": "MP-X", "cantidad_real_g": 100}, headers=_h())
    assert r.status_code == 403, r.data
