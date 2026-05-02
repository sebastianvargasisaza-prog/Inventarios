"""Tests del módulo Equipos & Calibraciones (COC-PRO-006/012 + PRD-PRO-004).

Sebastián 1-may-2026: 104 equipos del listado maestro con tracking de
hoja de vida, cronograma 2026 y alertas vencimientos.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="laura"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login fallo {user}: {r.status_code}"
    return c


def test_equipos_dashboard_estructura(app, db_clean):
    """GET /api/calidad/equipos/dashboard retorna estructura completa."""
    c = _login(app, "laura")
    r = c.get("/api/calidad/equipos/dashboard")
    assert r.status_code == 200
    data = r.get_json()
    assert "kpis" in data
    for k in ["total_activos","vigentes","proximos_30d","vencidos","sin_tracking"]:
        assert k in data["kpis"]
    for sec in ["vencidos","proximos_30d","sin_tracking"]:
        assert sec in data
        assert isinstance(data[sec], list)


def test_equipos_dashboard_total_activos_no_cero(app, db_clean):
    """El seed de migración 63 carga 104 equipos · total_activos > 0."""
    c = _login(app, "laura")
    r = c.get("/api/calidad/equipos/dashboard")
    data = r.get_json()
    # En BD test, debe haber al menos algunos equipos del seed
    assert data["kpis"]["total_activos"] > 0, "El seed de equipos_planta debería cargar 104 equipos"


def test_equipos_registrar_evento_rbac(app, db_clean):
    """Solo CALIDAD_USERS o ADMIN_USERS pueden registrar eventos."""
    # Luis (planta) NO debe poder
    c = _login(app, "luis")
    # Buscar un código de equipo del seed
    conn = sqlite3.connect(os.environ["DB_PATH"])
    eq_codigo = conn.execute(
        "SELECT codigo FROM equipos_planta WHERE COALESCE(activo,1)=1 LIMIT 1"
    ).fetchone()
    conn.close()
    if not eq_codigo:
        # No hay equipos en seed test
        return
    codigo = eq_codigo[0]
    r = c.post(f"/api/calidad/equipos/{codigo}/registrar-evento",
               json={"tipo_evento": "calibracion", "fecha_proxima": "2027-05-01"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_equipos_registrar_evento_ok(app, db_clean):
    """Calidad puede registrar evento + actualiza estado."""
    c = _login(app, "laura")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    eq_codigo = conn.execute(
        "SELECT codigo FROM equipos_planta WHERE COALESCE(activo,1)=1 LIMIT 1"
    ).fetchone()
    conn.close()
    if not eq_codigo:
        return
    codigo = eq_codigo[0]
    r = c.post(f"/api/calidad/equipos/{codigo}/registrar-evento",
               json={"tipo_evento": "calibracion",
                     "fecha": "2026-05-01",
                     "fecha_proxima": "2027-05-01",
                     "responsable": "Laura",
                     "empresa_externa": "ONAC Lab",
                     "resultado": "aprobado",
                     "observaciones": "Test"},
               headers=csrf_headers())
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert "evento_id" in data

    # Verificar que se insertó
    conn = sqlite3.connect(os.environ["DB_PATH"])
    row = conn.execute(
        "SELECT tipo_evento, fecha_proxima FROM equipos_eventos WHERE id=?",
        (data["evento_id"],)
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "calibracion"
    assert row[1] == "2027-05-01"


def test_equipos_registrar_evento_tipo_invalido(app, db_clean):
    """tipo_evento fuera del CHECK constraint → 400."""
    c = _login(app, "laura")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    eq_codigo = conn.execute("SELECT codigo FROM equipos_planta LIMIT 1").fetchone()
    conn.close()
    if not eq_codigo:
        return
    r = c.post(f"/api/calidad/equipos/{eq_codigo[0]}/registrar-evento",
               json={"tipo_evento": "tipo_invalido_xyz"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_equipos_registrar_evento_codigo_inexistente(app, db_clean):
    """Equipo no encontrado → 404."""
    c = _login(app, "laura")
    r = c.post("/api/calidad/equipos/EQ-NO-EXISTE-99/registrar-evento",
               json={"tipo_evento": "calibracion"},
               headers=csrf_headers())
    assert r.status_code == 404


def test_equipos_hoja_vida(app, db_clean):
    """GET /api/calidad/equipos/<codigo>/hoja-vida retorna equipo + eventos + cronograma."""
    c = _login(app, "laura")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    eq_codigo = conn.execute("SELECT codigo FROM equipos_planta LIMIT 1").fetchone()
    conn.close()
    if not eq_codigo:
        return
    r = c.get(f"/api/calidad/equipos/{eq_codigo[0]}/hoja-vida")
    assert r.status_code == 200
    data = r.get_json()
    assert "equipo" in data
    assert "eventos" in data
    assert "cronograma" in data
    assert data["equipo"]["codigo"] == eq_codigo[0]


def test_equipos_cronograma_estructura(app, db_clean):
    """GET cronograma retorna items + kpis."""
    c = _login(app, "laura")
    r = c.get("/api/calidad/equipos/cronograma?mes=5&anio=2026")
    assert r.status_code == 200
    data = r.get_json()
    assert data["mes"] == 5
    assert data["anio"] == 2026
    assert "items" in data
    assert "kpis" in data
    for k in ["total","completados","pendientes"]:
        assert k in data["kpis"]


def test_equipos_cronograma_mes_invalido(app, db_clean):
    """mes fuera de 1-12 → 400."""
    c = _login(app, "laura")
    r = c.get("/api/calidad/equipos/cronograma?mes=13")
    assert r.status_code == 400


def test_equipos_importar_cronograma_admin(app, db_clean):
    """Solo admin puede importar."""
    c_user = _login(app, "laura")  # calidad pero no admin
    r = c_user.post("/api/calidad/equipos/importar-cronograma",
                    json={"items": []},
                    headers=csrf_headers())
    assert r.status_code == 403

    c_admin = _login(app, "sebastian")
    # Items vacíos → 400
    r = c_admin.post("/api/calidad/equipos/importar-cronograma",
                     json={"items": []},
                     headers=csrf_headers())
    assert r.status_code == 400


def test_equipos_importar_cronograma_ok(app, db_clean):
    """Admin importa items · idempotente."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    eq_codigo = conn.execute("SELECT codigo FROM equipos_planta LIMIT 1").fetchone()
    conn.close()
    if not eq_codigo:
        return
    items = [
        {"equipo_codigo": eq_codigo[0], "mes": 5, "tipo_actividad": "preventivo"},
        {"equipo_codigo": eq_codigo[0], "mes": 6, "tipo_actividad": "preventivo"},
    ]
    r = c.post("/api/calidad/equipos/importar-cronograma",
               json={"anio": 2026, "items": items},
               headers=csrf_headers())
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["insertados"] == 2

    # Re-importar → idempotente
    r2 = c.post("/api/calidad/equipos/importar-cronograma",
                json={"anio": 2026, "items": items},
                headers=csrf_headers())
    data2 = r2.get_json()
    assert data2["insertados"] == 0
    assert data2["saltados_ya_existian"] == 2

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM equipos_cronograma WHERE equipo_codigo=?", (eq_codigo[0],))
    conn.commit(); conn.close()


def test_equipos_completar_cronograma(app, db_clean):
    """Completar item de cronograma crea evento asociado."""
    c = _login(app, "laura")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    eq_codigo = conn.execute("SELECT codigo FROM equipos_planta LIMIT 1").fetchone()
    if not eq_codigo:
        conn.close()
        return
    # Insertar item de cronograma manualmente
    conn.execute("""INSERT OR IGNORE INTO equipos_cronograma
        (equipo_codigo, anio, mes, tipo_actividad)
        VALUES (?, 2026, 7, 'preventivo')""", (eq_codigo[0],))
    cron_id = conn.execute("""SELECT id FROM equipos_cronograma
        WHERE equipo_codigo=? AND anio=2026 AND mes=7""", (eq_codigo[0],)).fetchone()[0]
    conn.commit(); conn.close()

    r = c.post(f"/api/calidad/equipos/cronograma/{cron_id}/completar",
               json={"observaciones": "test"},
               headers=csrf_headers())
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert "evento_id" in data

    # Re-completar → 409 (ya está completado)
    r2 = c.post(f"/api/calidad/equipos/cronograma/{cron_id}/completar",
                json={}, headers=csrf_headers())
    assert r2.status_code == 409

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM equipos_cronograma WHERE id=?", (cron_id,))
    conn.execute("DELETE FROM equipos_eventos WHERE id=?", (data["evento_id"],))
    conn.commit(); conn.close()


def test_equipos_endpoints_requieren_auth(client, db_clean):
    """Sin login, endpoints retornan 401."""
    for path in ["/api/calidad/equipos/dashboard",
                 "/api/calidad/equipos/cronograma"]:
        r = client.get(path)
        assert r.status_code == 401, f"{path} debería 401"
