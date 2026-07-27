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


def test_animus_caja_anular_audita(app, db_clean):
    """El recibo se ANULA, no se borra (27-jul).

    Antes esto esperaba `ANIMUS_CAJA_ELIMINAR` y un DELETE real. Se cambió a propósito: la caja
    existe para reemplazar los recibos sueltos SIN numeración, y un talonario del que se pueden
    arrancar hojas no prueba nada. El movimiento se conserva, deja de sumar al saldo, y guarda
    quién lo anuló y por qué.
    """
    c = _login(app, "sebastian")
    r = c.post("/api/animus/caja",
               json={"tipo": "egreso", "concepto": "Test del", "monto": 1000},
               headers=csrf_headers())
    mov_id = r.get_json()["id"]
    r = c.delete(f"/api/animus/caja/{mov_id}",
                 json={"motivo": "cargado dos veces"}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    audit = _last_audit(accion="ANIMUS_CAJA_ANULAR")
    assert audit is not None
    # y el movimiento SIGUE existiendo, marcado
    conn = sqlite3.connect(os.environ["DB_PATH"])
    row = conn.execute("SELECT anulado, anulado_por, anulado_motivo, recibo_numero "
                       "FROM animus_caja_menor WHERE id=?", (mov_id,)).fetchone()
    conn.close()
    assert row is not None, 'el movimiento se borró: la anulación tiene que conservarlo'
    assert int(row[0]) == 1 and row[1] == 'sebastian' and row[2] == 'cargado dos veces'
    assert (row[3] or '').startswith('RC-'), 'quedó sin número de recibo: %s' % (row[3],)


def test_animus_caja_anular_sin_motivo_400(app, db_clean):
    """Sin motivo no se anula: el motivo es lo que hace auditable el hueco del correlativo."""
    c = _login(app, "sebastian")
    r = c.post("/api/animus/caja",
               json={"tipo": "egreso", "concepto": "Test motivo", "monto": 1000},
               headers=csrf_headers())
    mov_id = r.get_json()["id"]
    r = c.delete(f"/api/animus/caja/{mov_id}", headers=csrf_headers())
    assert r.status_code == 400


def test_animus_caja_anular_dos_veces_409(app, db_clean):
    """Segunda anulación no pisa el motivo de la primera (CAS)."""
    c = _login(app, "sebastian")
    r = c.post("/api/animus/caja",
               json={"tipo": "ingreso", "concepto": "Test doble", "monto": 2000},
               headers=csrf_headers())
    mov_id = r.get_json()["id"]
    assert c.delete(f"/api/animus/caja/{mov_id}", json={"motivo": "primera"},
                    headers=csrf_headers()).status_code == 200
    assert c.delete(f"/api/animus/caja/{mov_id}", json={"motivo": "segunda"},
                    headers=csrf_headers()).status_code == 409
    conn = sqlite3.connect(os.environ["DB_PATH"])
    motivo = conn.execute("SELECT anulado_motivo FROM animus_caja_menor WHERE id=?",
                          (mov_id,)).fetchone()[0]
    conn.close()
    assert motivo == 'primera', 'la segunda anulación pisó el motivo de la primera'


def test_animus_caja_anular_no_admin_403(app, db_clean):
    """Un usuario sin rol admin no anula. NO se hardcodea una persona (M102): 'luis' fue dado de
    baja en la mig 375 y este test se caía por eso, no por el permiso."""
    from config import ADMIN_USERS, ANIMUS_ACCESS
    comun = sorted(ANIMUS_ACCESS - ADMIN_USERS)
    if not comun:
        import pytest
        pytest.skip('todos los usuarios con acceso a ÁNIMUS son admin')
    c = _login(app, comun[0])
    r = c.delete("/api/animus/caja/1", json={"motivo": "x"}, headers=csrf_headers())
    assert r.status_code == 403


def test_animus_caja_anular_inexistente_404(app, db_clean):
    c = _login(app, "sebastian")
    r = c.delete("/api/animus/caja/9999999", json={"motivo": "x"}, headers=csrf_headers())
    assert r.status_code == 404
