"""Tests de audit_log en operaciones financieras críticas (DIAN/laboral).

Cubre:
- contabilidad: CREAR_FACTURA (DIAN trail)
- rrhh: APROBAR_NOMINA / PAGAR_NOMINA (laboral trail)

Validaciones:
- iva_pct fuera de rango → 400
- nómina sin registros para período → 404
- nómina pagar sin estar aprobada → 400
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login fallo {user}: {r.status_code}"
    # Dual login para contabilidad
    c.post('/api/contabilidad/login', json={'usuario': user, 'password': TEST_PASSWORD})
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


# ─── Contabilidad · CREAR_FACTURA ────────────────────────────────────

def test_crear_factura_audita(app, db_clean):
    c = _login(app, "sebastian")
    # Bump counter sufficient para evitar colisión con otros tests que
    # insertan facturas hardcoded (ej. test_gap5_pago_factura uses 9000)
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT OR REPLACE INTO config_facturacion
                    (empresa, anio, tipo, siguiente)
                    VALUES ('ANIMUS', strftime('%Y', 'now'), 'FV', 50000)""")
    conn.commit(); conn.close()
    r = c.post("/api/contabilidad/facturas/generar",
               json={"empresa": "ANIMUS", "iva_pct": 19,
                     "items": [{"sku": "TST-1", "descripcion": "Test item",
                                "cantidad": 2, "precio_unitario": 50000,
                                "subtotal": 100000}]},
               headers=csrf_headers())
    assert r.status_code == 200, r.data
    body = r.get_json()
    numero = body["numero"]
    audit = _last_audit(accion="CREAR_FACTURA", registro_id=numero)
    assert audit is not None, "audit_log CREAR_FACTURA no registrado"
    assert audit[0] == "sebastian"
    assert audit[2] == "facturas"
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM facturas WHERE numero=?", (numero,))
    conn.execute("DELETE FROM facturas_items WHERE numero_factura=?", (numero,))
    conn.commit(); conn.close()


def test_crear_factura_iva_fuera_rango_400(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/contabilidad/facturas/generar",
               json={"iva_pct": 99, "items": [{"cantidad": 1, "precio_unitario": 1000}]},
               headers=csrf_headers())
    assert r.status_code == 400


def test_crear_factura_iva_invalido_400(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/contabilidad/facturas/generar",
               json={"iva_pct": "abc", "items": [{"cantidad": 1, "precio_unitario": 1000}]},
               headers=csrf_headers())
    assert r.status_code == 400


def test_crear_factura_total_cero_400(app, db_clean):
    """Factura sin items o monto cero → validate_money rechaza."""
    c = _login(app, "sebastian")
    r = c.post("/api/contabilidad/facturas/generar",
               json={"items": []}, headers=csrf_headers())
    assert r.status_code == 400


# ─── RRHH · APROBAR_NOMINA ────────────────────────────────────────────

def test_nomina_aprobar_audita(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT OR IGNORE INTO empleados (id, codigo, nombre, cargo, estado)
                    VALUES (9101, 'EMP-AUDIT-1', 'Test empleado', 'Op', 'Activo')""")
    conn.execute("""INSERT INTO nomina_registros (empleado_id, periodo, salario_neto, estado)
                    VALUES (9101, '2026-05', 2000000, 'Borrador')""")
    conn.commit(); conn.close()
    try:
        r = c.patch("/api/rrhh/nomina/2026-05/aprobar", headers=csrf_headers())
        assert r.status_code == 200, r.data
        audit = _last_audit(accion="APROBAR_NOMINA", registro_id="2026-05")
        assert audit is not None
        assert audit[0] == "sebastian"
        assert "2026-05" in (audit[4] or "")
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM nomina_registros WHERE empleado_id=9101")
        conn.execute("DELETE FROM empleados WHERE id=9101")
        conn.commit(); conn.close()


def test_nomina_aprobar_no_admin_403(app, db_clean):
    c = _login(app, "luis")  # luis no es admin
    r = c.patch("/api/rrhh/nomina/2026-05/aprobar", headers=csrf_headers())
    # luis no está en RRHH_USERS, así que el gate primero le da 403 en _rrhh_gate
    assert r.status_code == 403


def test_nomina_aprobar_sin_registros_404(app, db_clean):
    c = _login(app, "sebastian")
    r = c.patch("/api/rrhh/nomina/9999-99/aprobar", headers=csrf_headers())
    assert r.status_code == 404


def test_nomina_pagar_audita(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT OR IGNORE INTO empleados (id, codigo, nombre, cargo, estado)
                    VALUES (9102, 'EMP-AUDIT-2', 'Test 2', 'Op', 'Activo')""")
    conn.execute("""INSERT INTO nomina_registros (empleado_id, periodo, salario_neto, estado)
                    VALUES (9102, '2026-06', 1800000, 'Aprobada')""")
    conn.commit(); conn.close()
    try:
        r = c.patch("/api/rrhh/nomina/2026-06/pagar", headers=csrf_headers())
        assert r.status_code == 200, r.data
        audit = _last_audit(accion="PAGAR_NOMINA", registro_id="2026-06")
        assert audit is not None
        assert audit[0] == "sebastian"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM nomina_registros WHERE empleado_id=9102")
        conn.execute("DELETE FROM empleados WHERE id=9102")
        conn.execute("DELETE FROM flujo_egresos WHERE referencia='NOM-2026-06'")
        conn.commit(); conn.close()


def test_nomina_pagar_sin_aprobar_400(app, db_clean):
    """No se puede pagar nómina si registros no están Aprobados."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT OR IGNORE INTO empleados (id, codigo, nombre, cargo, estado)
                    VALUES (9103, 'EMP-AUDIT-3', 'Test 3', 'Op', 'Activo')""")
    conn.execute("""INSERT INTO nomina_registros (empleado_id, periodo, salario_neto, estado)
                    VALUES (9103, '2026-07', 1500000, 'Borrador')""")
    conn.commit(); conn.close()
    try:
        r = c.patch("/api/rrhh/nomina/2026-07/pagar", headers=csrf_headers())
        assert r.status_code == 400
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM nomina_registros WHERE empleado_id=9103")
        conn.execute("DELETE FROM empleados WHERE id=9103")
        conn.commit(); conn.close()
