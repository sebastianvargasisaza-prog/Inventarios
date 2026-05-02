"""Tests del endpoint /api/admin/health-detailed · diagnóstico zero-error.

Cubre: auth · estructura del JSON · secciones esperadas con status válido.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_health_detailed_requires_auth(client, db_clean):
    r = client.get("/api/admin/health-detailed")
    assert r.status_code == 401


def test_health_detailed_user_no_admin_403(app, db_clean):
    """User no-admin recibe 403."""
    c = _login(app, "luis")  # luis no es admin
    r = c.get("/api/admin/health-detailed")
    assert r.status_code == 403


def test_health_detailed_admin_estructura(app, db_clean):
    """Admin recibe estructura esperada con todas las secciones."""
    c = _login(app, "sebastian")
    r = c.get("/api/admin/health-detailed")
    assert r.status_code == 200
    data = r.get_json()
    assert "timestamp" in data
    assert "commit" in data
    assert "overall" in data
    assert data["overall"] in ("ok", "warning", "error")
    assert "sections" in data
    # Las 8 secciones esperadas
    sections = data["sections"]
    for k in ("migrations", "indexes", "helpers", "crons",
                "audit_log", "asg_workflows", "backups", "sentry"):
        assert k in sections, f"falta sección {k}"
        assert "status" in sections[k]
        assert sections[k]["status"] in ("ok", "warning", "error")


def test_health_detailed_migrations_aplicadas(app, db_clean):
    """En entorno de test, todas las migrations deben estar aplicadas."""
    c = _login(app, "sebastian")
    r = c.get("/api/admin/health-detailed")
    sections = r.get_json()["sections"]
    mig = sections["migrations"]
    assert mig["status"] == "ok"
    assert mig["applied_count"] >= 90  # 90+ migraciones definidas
    assert mig.get("missing", []) == []


def test_health_detailed_helpers_disponibles(app, db_clean):
    """audit_helpers + http_helpers deben importarse OK."""
    c = _login(app, "sebastian")
    r = c.get("/api/admin/health-detailed")
    helpers = r.get_json()["sections"]["helpers"]
    assert helpers["status"] == "ok"
    assert helpers["audit_helpers"] == "ok"
    assert helpers["http_helpers"] == "ok"


def test_health_detailed_crons_registrados(app, db_clean):
    """JOBS_SCHEDULE debe tener al menos los 13 cron jobs definidos."""
    c = _login(app, "sebastian")
    r = c.get("/api/admin/health-detailed")
    crons = r.get_json()["sections"]["crons"]
    assert crons["status"] == "ok"
    assert crons["jobs_count"] >= 13
    # Los 4 jobs ASG nuevos deben estar
    for j in ("desv_plazos", "cambios_plazos", "quejas_plazos", "recalls_plazos"):
        assert j in crons["jobs"]


def test_health_detailed_indexes_criticos(app, db_clean):
    """Los 8 indexes críticos deben estar presentes."""
    c = _login(app, "sebastian")
    r = c.get("/api/admin/health-detailed")
    idx = r.get_json()["sections"]["indexes"]
    # Status ok significa que todos los críticos existen
    assert idx["status"] == "ok", f"Faltan indexes: {idx.get('missing', [])}"
    assert idx["critical_present"] == idx["critical_total"]
    assert idx["missing"] == []


def test_health_detailed_asg_workflows_existen(app, db_clean):
    """Las 4 tablas de workflows ASG deben existir (count >= 0, no -1)."""
    c = _login(app, "sebastian")
    r = c.get("/api/admin/health-detailed")
    asg = r.get_json()["sections"]["asg_workflows"]
    assert asg["status"] == "ok"
    for tabla in ("desviaciones", "control_cambios", "quejas_clientes", "recalls"):
        assert asg[tabla] >= 0, f"Tabla {tabla} no existe"


# ─── Secciones operacionales nuevas ──────────────────────────────────

def test_health_detailed_secciones_operacionales(app, db_clean):
    """Las 7 secciones operacionales nuevas deben estar presentes."""
    c = _login(app, "sebastian")
    r = c.get("/api/admin/health-detailed")
    sections = r.get_json()["sections"]
    for k in ("invima", "recalls", "cuarentena", "liberacion_pt",
              "hallazgos_vencidos", "caja", "salas", "mfa_admins"):
        assert k in sections, f"falta sección {k}"
        assert "status" in sections[k]


def test_health_detailed_invima_estructura(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/admin/health-detailed")
    invima = r.get_json()["sections"]["invima"]
    assert "vencidos" in invima
    assert "por_vencer_30d" in invima
    assert "por_vencer_90d" in invima


def test_health_detailed_recalls_estructura(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/admin/health-detailed")
    rcl = r.get_json()["sections"]["recalls"]
    assert "total_abiertos" in rcl
    assert "sin_clasificar" in rcl
    assert "clase_I_abiertos" in rcl


def test_health_detailed_caja_calcula_committed(app, db_clean):
    """Sección caja debe traer saldo + committed + ratio."""
    c = _login(app, "sebastian")
    r = c.get("/api/admin/health-detailed")
    caja = r.get_json()["sections"]["caja"]
    assert "saldo_ultimo_input" in caja
    assert "committed_ocs_autorizadas" in caja
    assert "cobertura_ratio" in caja


def test_health_detailed_mfa_admins(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/admin/health-detailed")
    mfa = r.get_json()["sections"]["mfa_admins"]
    assert "admins_total" in mfa
    assert "admins_con_mfa" in mfa
    assert "admins_sin_mfa" in mfa


# ─── UI page /admin/system-health ────────────────────────────────────

def test_system_health_page_requires_auth(client, db_clean):
    r = client.get("/admin/system-health", follow_redirects=False)
    assert r.status_code == 302  # redirect to /login


def test_system_health_page_no_admin_403(app, db_clean):
    c = _login(app, "luis")
    r = c.get("/admin/system-health")
    assert r.status_code == 403


def test_system_health_page_admin_renderiza(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/admin/system-health")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    # Verificar elementos clave del template
    assert "System Health" in body
    assert "/api/admin/health-detailed" in body
    # Section labels esperados
    for label in ("Recalls activos", "Hallazgos vencidos",
                   "Caja vs commitments", "Salas planta"):
        assert label in body
