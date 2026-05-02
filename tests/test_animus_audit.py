"""Tests audit Animus · caja menor."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
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


def test_animus_caja_registrar_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/animus/caja",
               json={"tipo": "ingreso", "concepto": "Test caja",
                     "monto": 50000, "metodo": "efectivo"},
               headers=csrf_headers())
    assert r.status_code == 200
    mov_id = r.get_json()["id"]
    audit = _last_audit(accion="ANIMUS_CAJA_MOV")
    assert audit is not None
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM animus_caja_menor WHERE id=?", (mov_id,))
    conn.commit(); conn.close()


def test_animus_caja_monto_invalido_400(app, db_clean):
    c = _login(app, "sebastian")
    # NaN
    r = c.post("/api/animus/caja",
               json={"tipo": "ingreso", "concepto": "x", "monto": float('nan')},
               headers=csrf_headers())
    assert r.status_code == 400
    # Negativo
    r = c.post("/api/animus/caja",
               json={"tipo": "ingreso", "concepto": "x", "monto": -100},
               headers=csrf_headers())
    assert r.status_code == 400


def test_animus_caja_eliminar_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/animus/caja",
               json={"tipo": "egreso", "concepto": "Test del", "monto": 1000},
               headers=csrf_headers())
    mov_id = r.get_json()["id"]
    r = c.delete(f"/api/animus/caja/{mov_id}", headers=csrf_headers())
    assert r.status_code == 200
    audit = _last_audit(accion="ANIMUS_CAJA_ELIMINAR")
    assert audit is not None


def test_animus_caja_eliminar_no_admin_403(app, db_clean):
    c = _login(app, "luis")
    r = c.delete("/api/animus/caja/1", headers=csrf_headers())
    assert r.status_code == 403


def test_animus_caja_eliminar_inexistente_404(app, db_clean):
    c = _login(app, "sebastian")
    r = c.delete("/api/animus/caja/9999999", headers=csrf_headers())
    assert r.status_code == 404
