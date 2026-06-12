"""El audit_log de operaciones EBR/MBR PERSISTE (Sebastián 12-jun · Part 11).
Antes, audit_log(cur,...) corría DESPUÉS de conn.commit() y el teardown cerraba
sin commit -> el rastro se perdía (COUNT=0). Ahora usa modo independiente
(autocommit) en los 9 sitios terminales -> el rastro queda guardado.
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


def _q1(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        r = conn.execute(sql, params).fetchone()
        return r[0] if r else None
    finally:
        conn.close()


def test_crear_mbr_deja_rastro_en_audit_log(app, db_clean):
    c = _login(app)
    r = c.post('/api/brd/mbr', json={'producto_nombre': 'PRODUCTO AUDIT WF',
                                     'titulo': 'Test audit persistencia',
                                     'lote_size_g': 1000})
    assert r.status_code in (200, 201), r.data
    mbr_id = r.get_json().get('id')
    assert mbr_id, r.data
    # El rastro de auditoría DEBE existir (antes se descartaba por commit-then-audit)
    n = _q1("SELECT COUNT(*) FROM audit_log WHERE accion='CREATE_MBR_DRAFT' "
            "AND registro_id=?", (str(mbr_id),))
    assert n and n >= 1, "el audit_log de CREATE_MBR_DRAFT debe persistir (Part 11)"
