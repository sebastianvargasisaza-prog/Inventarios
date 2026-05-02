"""Tests audit Bienestar · notificaciones empleados."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="luis"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _last_audit(accion=None):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    sql = "SELECT usuario, accion FROM audit_log"
    params = []
    if accion: sql += " WHERE accion=?"; params.append(accion)
    sql += " ORDER BY id DESC LIMIT 1"
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return row


def test_crear_notif_bienestar_audita(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/bienestar/notificaciones",
               json={"tipo": "cita_medica", "asunto": "Test cita médica",
                     "fecha_inicio": "2026-06-01"},
               headers=csrf_headers())
    assert r.status_code == 201
    nid = r.get_json()["id"]
    audit = _last_audit(accion="CREAR_NOTIF_BIENESTAR")
    assert audit is not None
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM notificaciones_empleados WHERE id=?", (nid,))
    conn.commit(); conn.close()


def test_notif_tipo_invalido_400(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/bienestar/notificaciones",
               json={"tipo": "invalido", "asunto": "x"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_notif_resolver_audita(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/bienestar/notificaciones",
               json={"tipo": "permiso", "asunto": "Test"},
               headers=csrf_headers())
    nid = r.get_json()["id"]
    try:
        # Login como sebastian (jefe)
        c2 = _login(app, "sebastian")
        r = c2.post(f"/api/bienestar/notificaciones/{nid}/resolver",
                    json={"estado": "aprobada", "comentario_jefe": "OK"},
                    headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="RESOLVER_NOTIF_BIENESTAR")
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM notificaciones_empleados WHERE id=?", (nid,))
        conn.commit(); conn.close()


def test_resolver_no_jefe_403(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/bienestar/notificaciones/1/resolver",
               json={"estado": "aprobada"}, headers=csrf_headers())
    assert r.status_code == 403
