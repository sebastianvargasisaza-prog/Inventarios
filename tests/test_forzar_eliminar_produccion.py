"""Forzar-eliminar producción (27-jun · Sebastián/Alejandro) · admin puede eliminar un lote que ya
descontó inventario: revierte el descuento + cancela en un paso."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD}, headers=csrf_headers(), follow_redirects=False)
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


def test_forzar_eliminar_produccion_descontada(app, db_clean):
    pid = _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, "
                "inventario_descontado_at) VALUES ('ZZ FORCE', date('now'), 1, 'programado', datetime('now'))")
    c = _login(app, "sebastian")
    # sin force → 409 (protegida)
    r = c.delete(f"/api/plan/proximas/{pid}", headers=_h())
    assert r.status_code == 409 and r.get_json().get("codigo") == "YA_EN_EJECUCION", r.data
    assert _q1("SELECT estado FROM produccion_programada WHERE id=?", (pid,))[0] == "programado"
    # con force (admin) → revierte + cancela
    r2 = c.delete(f"/api/plan/proximas/{pid}", json={"force": True}, headers=_h())
    assert r2.status_code == 200, r2.data
    row = _q1("SELECT estado, COALESCE(inventario_descontado_at,''), COALESCE(inicio_real_at,'') "
              "FROM produccion_programada WHERE id=?", (pid,))
    assert row[0] == "cancelado" and row[1] == "" and row[2] == "", row
