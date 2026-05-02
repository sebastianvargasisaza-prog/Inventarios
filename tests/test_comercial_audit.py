"""Tests audit comercial · maquila pipeline + EOS leads."""
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
    sql = "SELECT usuario, accion, tabla, registro_id, detalle FROM audit_log"
    params = []
    if accion:
        sql += " WHERE accion=?"; params.append(accion)
    sql += " ORDER BY id DESC LIMIT 1"
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return row


def test_crear_maquila_pipeline_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/comercial/maquila",
               json={"empresa": "Pipeline Test", "stage": "nda",
                     "valor_estimado_cop": 10000000},
               headers=csrf_headers())
    assert r.status_code == 201
    pid = r.get_json()["id"]
    audit = _last_audit(accion="CREAR_MAQUILA_PIPELINE")
    assert audit is not None
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM maquila_pipeline WHERE id=?", (pid,))
    conn.commit(); conn.close()


def test_crear_pipeline_valor_invalido_400(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/comercial/maquila",
               json={"empresa": "X", "valor_estimado_cop": float('nan')},
               headers=csrf_headers())
    assert r.status_code == 400


def test_cambio_stage_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/comercial/maquila",
               json={"empresa": "Stage Test", "stage": "consulta"},
               headers=csrf_headers())
    pid = r.get_json()["id"]
    try:
        r = c.patch(f"/api/comercial/maquila/{pid}",
                    json={"stage": "nda"}, headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="CAMBIO_STAGE_MAQUILA")
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM maquila_pipeline WHERE id=?", (pid,))
        conn.commit(); conn.close()


def test_actualizar_eos_lead_audita(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute("""INSERT INTO eos_leads (nombre, email, estado, fuente)
                          VALUES ('Lead Test', 't@x.com', 'nuevo', 'web')""")
    lid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.patch(f"/api/eos/leads/{lid}",
                    json={"estado": "contactado", "owner": "sebastian"},
                    headers=csrf_headers())
        assert r.status_code == 200
        audit = _last_audit(accion="ACTUALIZAR_EOS_LEAD")
        assert audit is not None
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM eos_leads WHERE id=?", (lid,))
        conn.commit(); conn.close()
