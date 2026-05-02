"""Tests RBAC negative · gap del Día 5 ROADMAP.

Verifica que los endpoints sensibles RECHAZAN (403) cuando el user logueado
no tiene el rol requerido. Antes los audits encontraron varios endpoints
que solo verificaban session pero no rol.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login fallo {user}: {r.status_code}"
    return c


# ─── Calidad: POST endpoints requieren CALIDAD_USERS ───────────────────

def test_calidad_post_specs_user_no_calidad_403(app, db_clean):
    c = _login(app, "luis")  # luis no es calidad
    r = c.post("/api/calidad/especificaciones",
               json={"codigo_mp": "MP-001", "parametro": "pH"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_calidad_post_coa_user_no_calidad_403(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/calidad/coa",
               json={"lote": "L1", "codigo_mp": "MP-001",
                     "parametro": "pH", "valor_obtenido": "7.0"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_calidad_post_agua_user_no_calidad_403(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/calidad/agua/registros",
               json={"punto_muestreo": "tanque-1", "ph": 7.0},
               headers=csrf_headers())
    assert r.status_code == 403


def test_calidad_post_nc_user_no_calidad_403(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/calidad/no-conformidades",
               json={"descripcion": "Test sin permiso", "tipo": "Proceso"},
               headers=csrf_headers())
    assert r.status_code == 403


# ─── Compliance: POST endpoints requieren responsables BPM ─────────────

def test_compliance_post_capa_user_no_responsable_403(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/compliance/capa",
               json={"titulo": "Test sin permiso BPM",
                     "tipo": "desviacion", "severidad": "media"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_compliance_post_hallazgo_user_no_responsable_403(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/compliance/hallazgos",
               json={"titulo": "Test sin permiso BPM",
                     "origen": "BPM_interna"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_compliance_cumplir_cronograma_user_no_responsable_403(app, db_clean):
    c = _login(app, "luis")
    # ej_id arbitrario · solo nos importa el 403 antes del lookup
    r = c.post("/api/compliance/ejecuciones/999/cumplir",
               json={"observaciones": "test"},
               headers=csrf_headers())
    assert r.status_code == 403


# ─── Compras: SKIP · todos los usuarios del sistema están en COMPRAS_USERS ────
# Hoy COMPRAS_USERS = ALL_USERS · `user not in COMPRAS_USERS` es prácticamente
# equivalente a `not session`. El RBAC en compras es defensa-en-profundidad
# para futuros usuarios sin acceso compras (ej. clientes externos del módulo).
# Cuando se cree un rol "operario puro" se puede activar este test.

import pytest

@pytest.mark.skip(reason="Todos los users del sistema están en COMPRAS_USERS hoy")
def test_compras_recibir_oc_user_no_compras_403(app, db_clean):
    """Placeholder · activar cuando exista user fuera de COMPRAS_USERS."""
    pass


@pytest.mark.skip(reason="Todos los users del sistema están en COMPRAS_USERS hoy")
def test_compras_editar_oc_user_no_compras_403(app, db_clean):
    pass


@pytest.mark.skip(reason="Todos los users del sistema están en COMPRAS_USERS hoy")
def test_compras_revisar_oc_user_no_compras_403(app, db_clean):
    pass


# ─── Maquila: gate global ─────────────────────────────────────────────

def test_maquila_endpoint_sin_login_401(client, db_clean):
    """Sin login, endpoints maquila deben devolver 401."""
    r = client.get("/api/maquila/prospectos")
    assert r.status_code == 401


@pytest.mark.skip(reason="Todos los users del sistema están en COMPRAS_USERS hoy")
def test_maquila_endpoint_user_no_compras_403(app, db_clean):
    """Placeholder · activar cuando exista user fuera de COMPRAS_USERS."""
    pass


# ─── Clientes: PII protegida ──────────────────────────────────────────

def test_clientes_endpoint_sin_login_401(client, db_clean):
    """Sin login, endpoint cliente con PII devuelve 401."""
    r = client.get("/api/clientes")
    assert r.status_code == 401


# ─── Aseguramiento: triaje requiere Calidad ───────────────────────────

def test_aseguramiento_triaje_user_no_calidad_403(app, db_clean):
    """luis (no Calidad) no puede triar quejas."""
    luis = _login(app, "luis")
    # Crear queja primero (cualquier user puede)
    r = luis.post("/api/aseguramiento/quejas",
                   json={"cliente_nombre": "Test",
                         "descripcion": "Queja test para verificar RBAC en triaje"},
                   headers=csrf_headers())
    qid = r.get_json()["id"]
    # Intentar triar
    r = luis.post(f"/api/aseguramiento/quejas/{qid}/triaje",
                   json={"severidad": "menor",
                         "triaje_descripcion": "Test sin permiso"},
                   headers=csrf_headers())
    assert r.status_code == 403
    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM quejas_clientes_eventos WHERE queja_id=?", (qid,))
    conn.execute("DELETE FROM quejas_clientes WHERE id=?", (qid,))
    conn.commit(); conn.close()


def test_aseguramiento_recall_iniciar_user_no_calidad_403(app, db_clean):
    """luis no puede iniciar recall (decisión grave)."""
    c = _login(app, "luis")
    r = c.post("/api/aseguramiento/recalls",
               json={"producto": "PROD", "lotes_afectados": "L1",
                     "motivo": "Test sin permiso para iniciar recall"},
               headers=csrf_headers())
    assert r.status_code == 403
