"""Tests audit_log + CSRF + paginacion en RRHH.

Sebastian 3-may-2026: RRHH maneja PII (cedula, telefono, banco) +
nomina (DINERO). Antes tenia tests=0. Ahora cubre:
- CREAR_EMPLEADO con audit_log
- MODIFICAR_EMPLEADO con audit_log + antes/despues
- Validacion salario_base no negativo
- CSRF helpers en frontend
- Paginacion en grid empleados
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


def _last_audit(accion):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    row = conn.execute(
        "SELECT usuario, accion, registro_id, detalle FROM audit_log WHERE accion=? ORDER BY id DESC LIMIT 1",
        (accion,)).fetchone()
    conn.close()
    return row


def _cleanup_emp(emp_id):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM empleados WHERE id=?", (emp_id,))
    conn.commit(); conn.close()


def test_pagina_rrhh_carga(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.get("/rrhh")
    assert r.status_code == 200


def test_pagina_rrhh_tiene_csrf(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.get("/rrhh")
    body = r.get_data(as_text=True)
    assert "_csrf" in body
    assert "_fetchOpts" in body
    assert "X-CSRF-Token" in body
    assert "method:'POST'" not in body
    assert "method:'PUT'" not in body
    assert "method:'PATCH'" not in body


def test_pagina_rrhh_tiene_paginacion(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.get("/rrhh")
    body = r.get_data(as_text=True)
    assert "TBL_STATE" in body
    assert "_paginar" in body
    assert "_renderPag" in body
    assert 'id="pg-emp"' in body


def test_crear_empleado_audita(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/rrhh/empleados",
                json={"nombre": "Test", "apellido": "Audit",
                      "cedula": "9999999001", "cargo": "Developer",
                      "area": "TI", "empresa": "Espagiria",
                      "salario_base": 3000000, "fecha_ingreso": "2026-05-03"},
                headers=csrf_headers())
    assert r.status_code == 201, r.data
    eid = r.get_json()["id"]
    try:
        audit = _last_audit("CREAR_EMPLEADO")
        assert audit is not None
        assert audit[0] == "sebastian"
        assert int(audit[2]) == eid
        # Cedula parcialmente oculta en detalle (PII)
        # No verificamos el detalle exacto, solo que no contenga la cedula completa
        assert "9999999001" not in (audit[3] or "")
    finally:
        _cleanup_emp(eid)


def test_crear_empleado_rechaza_sin_nombre(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/rrhh/empleados",
                json={"cedula": "1234567890", "salario_base": 1500000},
                headers=csrf_headers())
    assert r.status_code == 400


def test_crear_empleado_rechaza_sin_cedula(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/rrhh/empleados",
                json={"nombre": "Sin Cedula", "salario_base": 1500000},
                headers=csrf_headers())
    assert r.status_code == 400


def test_crear_empleado_rechaza_salario_negativo(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/rrhh/empleados",
                json={"nombre": "Negativo", "cedula": "1111111111",
                      "salario_base": -500000},
                headers=csrf_headers())
    assert r.status_code == 400


def test_modificar_empleado_audita(app, db_clean):
    cs = _login(app, "sebastian")
    # Crear primero
    r = cs.post("/api/rrhh/empleados",
                json={"nombre": "Test", "apellido": "Mod",
                      "cedula": "8888888001", "salario_base": 2000000,
                      "empresa": "Espagiria", "fecha_ingreso": "2026-01-01"},
                headers=csrf_headers())
    eid = r.get_json()["id"]
    try:
        # Modificar salario
        r2 = cs.put(f"/api/rrhh/empleados/{eid}",
                    json={"nombre": "Test", "apellido": "Mod",
                          "cargo": "Senior Dev", "area": "TI",
                          "empresa": "Espagiria", "tipo_contrato": "Indefinido",
                          "salario_base": 2500000, "estado": "Activo"},
                    headers=csrf_headers())
        assert r2.status_code == 200
        audit = _last_audit("MODIFICAR_EMPLEADO")
        assert audit is not None
        # Detalle muestra cambio de salario
        assert "2,000,000" in (audit[3] or "") or "2,500,000" in (audit[3] or "")
    finally:
        _cleanup_emp(eid)


def test_modificar_empleado_rechaza_salario_negativo(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.post("/api/rrhh/empleados",
                json={"nombre": "Test", "apellido": "Neg",
                      "cedula": "7777777001", "salario_base": 2000000,
                      "empresa": "Espagiria", "fecha_ingreso": "2026-01-01"},
                headers=csrf_headers())
    eid = r.get_json()["id"]
    try:
        r2 = cs.put(f"/api/rrhh/empleados/{eid}",
                    json={"salario_base": -1000},
                    headers=csrf_headers())
        assert r2.status_code == 400
    finally:
        _cleanup_emp(eid)


def test_modificar_empleado_inexistente_404(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.put("/api/rrhh/empleados/9999999",
               json={"nombre": "X", "salario_base": 100000},
               headers=csrf_headers())
    assert r.status_code == 404


def test_get_empleados_lista(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.get("/api/rrhh/empleados")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)
