"""Tests portal publico /reportar (empleados sin login).

Sebastian 3-may-2026: empleados reportan permisos / salud / incapacidad
desde el celular validando cedula. Auto-aparece en /rrhh.
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


def _seed_empleado(cedula="12345678", nombre="TestEmp", estado="Activo"):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM empleados WHERE cedula=?", (cedula,))
    cur = conn.execute(
        """INSERT INTO empleados (codigo, nombre, apellido, cedula, cargo, area, empresa, estado, salario_base)
           VALUES ('EMP-T01', ?, 'Apellido', ?, 'Operario', 'Planta', 'Espagiria', ?, 1500000)""",
        (nombre, cedula, estado))
    eid = cur.lastrowid
    conn.commit(); conn.close()
    return eid


def _cleanup_empleado(cedula):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM empleados WHERE cedula=?", (cedula,))
    conn.execute("DELETE FROM notificaciones_empleados WHERE empleado_username LIKE 'emp-t%' OR empleado_username LIKE 'EMP-%'")
    conn.commit(); conn.close()


def test_pagina_publica_carga_sin_login(client, db_clean):
    """GET /reportar debe servir HTML sin requerir auth."""
    r = client.get("/reportar")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Reportar a RH" in body
    assert "cedula" in body


def test_endpoint_publico_no_requiere_login(client, db_clean):
    """POST /api/publico/empleado-reporte sin sesion debe procesar (con cedula valida)."""
    eid = _seed_empleado("99999999", "TestNoLogin")
    try:
        r = client.post("/api/publico/empleado-reporte",
                        json={"cedula": "99999999", "tipo": "permiso",
                              "asunto": "Necesito permiso para cita", "fecha_inicio": "2026-05-10"},
                        headers={"Origin": "http://localhost"})
        assert r.status_code == 201, r.data
        d = r.get_json()
        assert d["ok"] is True
    finally:
        _cleanup_empleado("99999999")


def test_cedula_no_existe_404(client, db_clean):
    """Cedula con formato valido pero sin empleado → 404."""
    # Limpiar empleados de tests previos
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM empleados WHERE cedula='1234567890'")
    conn.commit(); conn.close()
    r = client.post("/api/publico/empleado-reporte",
                    json={"cedula": "1234567890", "tipo": "permiso",
                          "asunto": "Asunto largo de prueba"},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 404, r.data


def test_cedula_no_numerica_400(client, db_clean):
    r = client.post("/api/publico/empleado-reporte",
                    json={"cedula": "ABC123XYZ", "tipo": "permiso",
                          "asunto": "Test"},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 400


def test_tipo_invalido_400(client, db_clean):
    eid = _seed_empleado("88888888")
    try:
        r = client.post("/api/publico/empleado-reporte",
                        json={"cedula": "88888888", "tipo": "vacaciones",
                              "asunto": "Quiero vacas"},
                        headers={"Origin": "http://localhost"})
        assert r.status_code == 400
    finally:
        _cleanup_empleado("88888888")


def test_asunto_corto_400(client, db_clean):
    eid = _seed_empleado("77777777")
    try:
        r = client.post("/api/publico/empleado-reporte",
                        json={"cedula": "77777777", "tipo": "permiso",
                              "asunto": "x"},
                        headers={"Origin": "http://localhost"})
        assert r.status_code == 400
    finally:
        _cleanup_empleado("77777777")


def test_empleado_inactivo_403(client, db_clean):
    eid = _seed_empleado("66666666", estado="Inactivo")
    try:
        r = client.post("/api/publico/empleado-reporte",
                        json={"cedula": "66666666", "tipo": "permiso",
                              "asunto": "Test inactivo asunto largo"},
                        headers={"Origin": "http://localhost"})
        assert r.status_code == 403
    finally:
        _cleanup_empleado("66666666")


def test_reporte_aparece_en_rrhh(app, db_clean):
    """Reporte público creado debe aparecer en /api/bienestar/notificaciones."""
    eid = _seed_empleado("55555555", "TestVisible")
    client = app.test_client()
    try:
        # 1. Empleado reporta sin login
        r = client.post("/api/publico/empleado-reporte",
                        json={"cedula": "55555555", "tipo": "salud",
                              "asunto": "Tengo dolor de cabeza fuerte",
                              "descripcion": "Ya tomé pastilla pero sigue"},
                        headers={"Origin": "http://localhost"})
        assert r.status_code == 201
        # 2. Sebastian (admin) ve la lista en /rrhh
        cs = _login(app, "sebastian")
        r2 = cs.get("/api/bienestar/notificaciones?estado=pendiente")
        assert r2.status_code == 200
        notifs = r2.get_json().get("notificaciones", [])
        # Debe estar el reporte recien creado
        assuntos = [n.get("asunto", "") for n in notifs]
        assert any("dolor de cabeza" in s for s in assuntos)
    finally:
        _cleanup_empleado("55555555")


def test_audit_log_registra_reporte_publico(client, db_clean):
    eid = _seed_empleado("44444444")
    try:
        client.post("/api/publico/empleado-reporte",
                    json={"cedula": "44444444", "tipo": "cita_medica",
                          "asunto": "Cita ortopedista jueves"},
                    headers={"Origin": "http://localhost"})
        conn = sqlite3.connect(os.environ["DB_PATH"])
        row = conn.execute(
            "SELECT accion, detalle FROM audit_log WHERE accion='REPORTE_PUBLICO_EMPLEADO' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None
        # Cedula NO debe estar completa en detalle (PII)
        assert "44444444" not in (row[1] or "")
    finally:
        _cleanup_empleado("44444444")


def test_pagina_rrhh_tiene_tab_reportes(app, db_clean):
    cs = _login(app, "sebastian")
    r = cs.get("/rrhh")
    body = r.get_data(as_text=True)
    assert 'id="t-notif"' in body
    assert 'id="notif"' in body
    assert "cargarNotif" in body
    assert "/reportar" in body  # link al portal publico
