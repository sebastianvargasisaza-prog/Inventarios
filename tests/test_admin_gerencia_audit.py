"""Tests de audit_log en mutaciones admin/gerencia.

Cubre las nuevas acciones agregadas (audit zero-error · 2-may-2026):
- admin.py: RESET_PASSWORD, BACKUP_MANUAL, ASIGNAR_PROVEEDOR_MP,
            CREAR_SKU_MAP / ACTUALIZAR_SKU_MAP
- gerencia.py: CLEANUP_TEST_DATA, GERENCIA_INPUT_MANUAL, MEE_SET_STOCK_BULK
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


# ─── admin.py: RESET_PASSWORD ────────────────────────────────────────

def test_reset_password_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/admin/reset-password",
               json={"username": "luis"}, headers=csrf_headers())
    assert r.status_code == 200, r.data
    audit = _last_audit(accion="RESET_PASSWORD", registro_id="luis")
    assert audit is not None
    assert audit[0] == "sebastian"


def test_reset_password_user_no_admin_403(app, db_clean):
    c = _login(app, "luis")  # luis no es admin
    r = c.post("/api/admin/reset-password",
               json={"username": "smurillo"}, headers=csrf_headers())
    assert r.status_code == 403


# ─── admin.py: ASIGNAR_PROVEEDOR_MP ──────────────────────────────────

def test_asignar_proveedor_mp_audita(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT OR IGNORE INTO maestro_mps
        (codigo_mp, nombre_inci, nombre_comercial, activo, proveedor)
        VALUES ('MP-AP-T1', 'INCI', 'Test MP asignar', 1, 'Prov Original')""")
    conn.commit(); conn.close()
    try:
        r = c.post("/api/admin/mps-asignar-proveedor",
                   json={"codigo_mp": "MP-AP-T1", "proveedor": "Prov Nuevo"},
                   headers=csrf_headers())
        assert r.status_code == 200, r.data
        audit = _last_audit(accion="ASIGNAR_PROVEEDOR_MP", registro_id="MP-AP-T1")
        assert audit is not None
        assert "Prov Original" in (audit[4] or "") and "Prov Nuevo" in (audit[4] or "")
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp='MP-AP-T1'")
        conn.commit(); conn.close()


def test_asignar_proveedor_mp_404(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/admin/mps-asignar-proveedor",
               json={"codigo_mp": "MP-NO-EXISTE-XYZ", "proveedor": "X"},
               headers=csrf_headers())
    assert r.status_code == 404


# ─── admin.py: SKU_MAP_UPSERT ────────────────────────────────────────

def test_sku_map_upsert_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/admin/sku-map",
               json={"sku": "SKU-AUDIT-T1", "producto_nombre": "Producto Test"},
               headers=csrf_headers())
    assert r.status_code == 200, r.data
    audit = _last_audit(registro_id="SKU-AUDIT-T1")
    assert audit is not None
    assert audit[1] in ("CREAR_SKU_MAP", "ACTUALIZAR_SKU_MAP")
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sku_producto_map WHERE sku='SKU-AUDIT-T1'")
    conn.commit(); conn.close()


# ─── gerencia.py: CLEANUP_TEST_DATA ──────────────────────────────────

def test_cleanup_test_data_requiere_confirm(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/admin/cleanup-test-data",
               json={}, headers=csrf_headers())
    assert r.status_code == 400


def test_cleanup_test_data_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/admin/cleanup-test-data",
               json={"confirm": True}, headers=csrf_headers())
    assert r.status_code == 200
    audit = _last_audit(accion="CLEANUP_TEST_DATA")
    assert audit is not None
    assert audit[0] == "sebastian"


def test_cleanup_test_data_no_admin_401(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/admin/cleanup-test-data",
               json={"confirm": True}, headers=csrf_headers())
    assert r.status_code == 401


# ─── gerencia.py: GERENCIA_INPUT_MANUAL ──────────────────────────────

def test_gerencia_input_manual_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/gerencia/input-manual",
               json={"periodo": "2026-12", "saldo_caja": 5000000,
                     "ingresos_animus": 2000000, "ingresos_maquila": 1500000,
                     "notas": "Test audit gerencia"},
               headers=csrf_headers())
    assert r.status_code == 200
    audit = _last_audit(accion="GERENCIA_INPUT_MANUAL", registro_id="2026-12")
    assert audit is not None
    assert "5000000" in (audit[4] or "")
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM gerencia_inputs WHERE periodo='2026-12'")
    conn.commit(); conn.close()


# ─── gerencia.py: MEE_SET_STOCK_BULK ─────────────────────────────────

def test_mee_set_stock_bulk_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/admin/mee-set-stock",
               json={"stock_actual": 3000, "stock_minimo": 500},
               headers=csrf_headers())
    assert r.status_code == 200
    audit = _last_audit(accion="MEE_SET_STOCK_BULK")
    assert audit is not None
    assert audit[0] == "sebastian"


def test_mee_set_stock_no_admin_401(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/admin/mee-set-stock",
               json={"stock_actual": 1000, "stock_minimo": 100},
               headers=csrf_headers())
    assert r.status_code == 401
