"""Tests de audit_log + state transitions en compliance.py.

Cubre:
- AGENDAR_CRONOGRAMA (cronograma_ejecuciones POST · solo responsables BPM)
- ACTUALIZAR_CAPA_DESV / CERRAR_CAPA_DESV (capa_actualizar)
- ACTUALIZAR_HALLAZGO / CERRAR_HALLAZGO (hallazgo_actualizar)
- Validaciones: cerrar CAPA requiere causa_raiz, cerrar hallazgo INVIMA
  requiere evidencia_cierre_url
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login fallo {user}: {r.status_code}"
    return c


def _last_audit(accion=None, registro_id=None):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    sql = "SELECT usuario, accion, tabla, registro_id, detalle FROM audit_log"
    where = []; params = []
    if accion:
        where.append("accion=?"); params.append(accion)
    if registro_id is not None:
        where.append("registro_id=?"); params.append(str(registro_id))
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT 1"
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return row


# ─── Cronograma ejecuciones POST ─────────────────────────────────────

def test_cronograma_agendar_user_no_bpm_403(app, db_clean):
    c = _login(app, "luis")  # luis no es responsable BPM
    r = c.post("/api/compliance/cronogramas/1/ejecuciones",
               json={"fecha_planeada": "2026-06-01"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_cronograma_agendar_audita(app, db_clean):
    c = _login(app, "sebastian")
    # Sembrar cronograma BPM
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute("""INSERT INTO cronogramas_bpm
        (codigo, nombre, frecuencia, responsable, ejecuciones_year_objetivo, activo)
        VALUES ('CRON-T1', 'Cron test', 'mensual', 'sebastian', 12, 1)""")
    cron_id = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.post(f"/api/compliance/cronogramas/{cron_id}/ejecuciones",
                   json={"fecha_planeada": "2026-06-01",
                         "observaciones": "test agendar"},
                   headers=csrf_headers())
        assert r.status_code == 201
        ej_id = r.get_json()["id"]
        audit = _last_audit(accion="AGENDAR_CRONOGRAMA", registro_id=ej_id)
        assert audit is not None
        assert audit[0] == "sebastian"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM cronograma_ejecuciones WHERE cronograma_id=?", (cron_id,))
        conn.execute("DELETE FROM cronogramas_bpm WHERE id=?", (cron_id,))
        conn.commit(); conn.close()


# ─── CAPA · cerrar requiere causa_raiz ───────────────────────────────

def test_cerrar_capa_sin_causa_400(app, db_clean):
    c = _login(app, "sebastian")
    # Crear CAPA primero
    r = c.post("/api/compliance/capa",
               json={"titulo": "CAPA test cerrar"},
               headers=csrf_headers())
    assert r.status_code == 201
    cid = r.get_json()["id"]
    try:
        # Intentar cerrar SIN causa_raiz → 400
        r = c.patch(f"/api/compliance/capa/{cid}",
                    json={"estado": "cerrada"}, headers=csrf_headers())
        assert r.status_code == 400
        # Cerrar con causa_raiz válida → 200 + audit CERRAR_CAPA_DESV
        r = c.patch(f"/api/compliance/capa/{cid}",
                    json={"estado": "cerrada",
                          "causa_raiz": "Causa raíz válida e identificada"},
                    headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="CERRAR_CAPA_DESV", registro_id=cid)
        assert audit is not None
        assert audit[0] == "sebastian"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM capa_desviaciones WHERE id=?", (cid,))
        conn.commit(); conn.close()


def test_capa_actualizar_no_cierre_audita(app, db_clean):
    """Modificación que NO es cierre genera ACTUALIZAR_CAPA_DESV (no CERRAR)."""
    c = _login(app, "sebastian")
    r = c.post("/api/compliance/capa",
               json={"titulo": "CAPA actualizar test"},
               headers=csrf_headers())
    cid = r.get_json()["id"]
    try:
        r = c.patch(f"/api/compliance/capa/{cid}",
                    json={"severidad": "alta",
                          "accion_correctiva": "Acción correctiva descrita"},
                    headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="ACTUALIZAR_CAPA_DESV", registro_id=cid)
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM capa_desviaciones WHERE id=?", (cid,))
        conn.commit(); conn.close()


def test_capa_no_existe_404(app, db_clean):
    c = _login(app, "sebastian")
    r = c.patch("/api/compliance/capa/99999999",
                json={"severidad": "baja"}, headers=csrf_headers())
    assert r.status_code == 404


# ─── Hallazgo · cerrar INVIMA requiere evidencia ─────────────────────

def test_cerrar_hallazgo_invima_sin_evidencia_400(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/compliance/hallazgos",
               json={"titulo": "Hallazgo INVIMA test",
                     "origen": "INVIMA", "severidad": "mayor"},
               headers=csrf_headers())
    assert r.status_code == 201
    hid = r.get_json()["id"]
    try:
        # Sin evidencia → 400
        r = c.patch(f"/api/compliance/hallazgos/{hid}",
                    json={"estado": "cerrado"}, headers=csrf_headers())
        assert r.status_code == 400
        # Con evidencia → 200 + audit CERRAR_HALLAZGO
        r = c.patch(f"/api/compliance/hallazgos/{hid}",
                    json={"estado": "cerrado",
                          "evidencia_cierre_url": "https://drive.google.com/foo"},
                    headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="CERRAR_HALLAZGO", registro_id=hid)
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM hallazgos WHERE id=?", (hid,))
        conn.commit(); conn.close()


def test_cerrar_hallazgo_interno_baja_sin_evidencia_ok(app, db_clean):
    """Hallazgo BPM_interna severidad baja puede cerrarse sin evidencia."""
    c = _login(app, "sebastian")
    r = c.post("/api/compliance/hallazgos",
               json={"titulo": "Hallazgo interno menor",
                     "origen": "BPM_interna", "severidad": "menor"},
               headers=csrf_headers())
    hid = r.get_json()["id"]
    try:
        r = c.patch(f"/api/compliance/hallazgos/{hid}",
                    json={"estado": "cerrado"},
                    headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="CERRAR_HALLAZGO", registro_id=hid)
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM hallazgos WHERE id=?", (hid,))
        conn.commit(); conn.close()


def test_hallazgo_actualizar_no_cierre_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/compliance/hallazgos",
               json={"titulo": "Hallazgo actualizar",
                     "origen": "BPM_interna", "severidad": "menor"},
               headers=csrf_headers())
    hid = r.get_json()["id"]
    try:
        r = c.patch(f"/api/compliance/hallazgos/{hid}",
                    json={"accion_propuesta": "Plan de acción descrito"},
                    headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="ACTUALIZAR_HALLAZGO", registro_id=hid)
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM hallazgos WHERE id=?", (hid,))
        conn.commit(); conn.close()


def test_hallazgo_no_existe_404(app, db_clean):
    c = _login(app, "sebastian")
    r = c.patch("/api/compliance/hallazgos/99999999",
                json={"severidad": "baja"}, headers=csrf_headers())
    assert r.status_code == 404


def test_capa_user_no_bpm_403(app, db_clean):
    c = _login(app, "luis")
    r = c.patch("/api/compliance/capa/1",
                json={"severidad": "baja"}, headers=csrf_headers())
    assert r.status_code == 403


def test_hallazgo_user_no_bpm_403(app, db_clean):
    c = _login(app, "luis")
    r = c.patch("/api/compliance/hallazgos/1",
                json={"severidad": "baja"}, headers=csrf_headers())
    assert r.status_code == 403
