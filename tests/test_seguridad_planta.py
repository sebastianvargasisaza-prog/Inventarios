"""Centro de Seguridad de Planta (admin.py · /api/admin/seguridad-planta).

READ-ONLY: estado vivo de los controles de planta + exposición. Refleja si el modo
inventario (recepción sin cuarentena) quedó encendido. Gerencia (admin).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _set_modo(valor):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""CREATE TABLE IF NOT EXISTS app_settings (
        clave TEXT PRIMARY KEY, valor TEXT NOT NULL, descripcion TEXT,
        actualizado_at_utc TEXT, actualizado_por TEXT, tenant_id INTEGER DEFAULT 1)""")
    conn.execute("DELETE FROM app_settings WHERE clave='recepcion_auto_vigente'")
    conn.execute("INSERT INTO app_settings (clave, valor, actualizado_at_utc, actualizado_por) "
                 "VALUES ('recepcion_auto_vigente', ?, '2026-06-16T10:00:00', 'sebastian')", (valor,))
    conn.commit(); conn.close()


def _modo_ctrl(j):
    return next(x for x in j["controles"] if x["clave"] == "recepcion_auto_vigente")


def test_modo_inventario_encendido_da_alerta(app, db_clean):
    _set_modo("1")
    c = _login(app)
    r = c.get("/api/admin/seguridad-planta")
    assert r.status_code == 200, r.data
    j = r.get_json()
    m = _modo_ctrl(j)
    assert m["estado"] == "ENCENDIDO"
    assert m["ok"] is False and m["toggle_off"] is True
    assert m["por"] == "sebastian"        # quién lo cambió
    assert j["alertas"] >= 1
    # controles esperados presentes
    claves = {x["clave"] for x in j["controles"]}
    # el endpoint emite la clave 'ebr_mode' (minúscula, como el resto de settings de dominio)
    assert {"recepcion_auto_vigente", "micro_gate_mode", "ebr_mode", "FORMULA_PIN", "sesion"} <= claves


def test_modo_inventario_apagado_ok(app, db_clean):
    _set_modo("0")
    c = _login(app)
    r = c.get("/api/admin/seguridad-planta")
    assert r.status_code == 200, r.data
    m = _modo_ctrl(r.get_json())
    assert m["estado"] == "APAGADO"
    assert m["ok"] is True and m["toggle_off"] is False


def test_requiere_admin(app, db_clean):
    c = _login(app, user="catalina")
    r = c.get("/api/admin/seguridad-planta")
    assert r.status_code in (401, 403)
