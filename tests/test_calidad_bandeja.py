"""Tests del endpoint /api/calidad/bandeja (Bandeja QC del día).

Sebastián 1-may-2026: el equipo Calidad necesita ver TODO lo pendiente en
una sola pantalla — lotes a liberar, equipos a calibrar, NCs/OOS abiertas,
muestreo micro de la semana, registro agua de hoy, auditorías próximas.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="laura"):
    """Login con un usuario de Calidad por default (laura)."""
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login fallo {user}: {r.status_code}"
    return c


def test_bandeja_requiere_auth(client, db_clean):
    """GET sin login → 401."""
    r = client.get("/api/calidad/bandeja")
    assert r.status_code == 401


def test_bandeja_estructura_response(app, db_clean):
    """Response debe incluir todas las secciones y kpis esperados."""
    c = _login(app, "laura")
    r = c.get("/api/calidad/bandeja")
    assert r.status_code == 200
    data = r.get_json()

    # Estructura top-level
    assert "fecha_hoy" in data
    assert "secciones" in data
    assert "kpis" in data

    # Las 9 secciones requeridas
    secciones_esperadas = [
        "lotes_cuarentena", "ncs_abiertas", "oos_abiertas",
        "calibraciones", "muestreo_micro_semana", "registro_agua_hoy",
        "cola_liberacion", "auditorias_proximas", "estabilidades_pendientes",
    ]
    for sec in secciones_esperadas:
        assert sec in data["secciones"], f"falta sección {sec}"

    # KPIs requeridos
    kpis_esperados = [
        "lotes_cuarentena", "ncs_abiertas", "oos_abiertas",
        "calibraciones_vencidas", "calibraciones_proximas",
        "muestreo_pendiente_semana", "cola_liberacion_listos",
        "auditorias_proximas", "estabilidades_pendientes",
        "agua_registrada_hoy", "total_pendientes",
    ]
    for kpi in kpis_esperados:
        assert kpi in data["kpis"], f"falta KPI {kpi}"


def test_bandeja_detecta_lote_cuarentena(app, db_clean):
    """Insertar un movimiento Cuarentena debe aparecer en bandeja."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT OR IGNORE INTO maestro_mps
                    (codigo_mp, nombre_inci, nombre_comercial, activo, tipo_material)
                    VALUES ('MP_BAN_TEST', 'test', 'Test Bandeja', 1, 'MP')""")
    conn.execute("""INSERT INTO movimientos
                    (material_id, material_nombre, lote, cantidad, tipo,
                     fecha, estado_lote, proveedor)
                    VALUES ('MP_BAN_TEST', 'Test Bandeja', 'LOTE-BAN-001',
                            1000, 'Entrada',
                            datetime('now', '-3 days'),
                            'Cuarentena', 'Prov X')""")
    conn.commit(); conn.close()

    c = _login(app, "laura")
    r = c.get("/api/calidad/bandeja")
    data = r.get_json()
    sec = data["secciones"]["lotes_cuarentena"]
    assert sec["total"] >= 1
    lotes = [it["lote"] for it in sec["items"]]
    assert "LOTE-BAN-001" in lotes
    # 3 días en cuarentena → no crítico (> 5d)
    item = next(it for it in sec["items"] if it["lote"] == "LOTE-BAN-001")
    assert item["dias_cuarentena"] >= 2  # tolerancia floor
    assert item["critico"] is False

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM movimientos WHERE material_id='MP_BAN_TEST'")
    conn.execute("DELETE FROM maestro_mps WHERE codigo_mp='MP_BAN_TEST'")
    conn.commit(); conn.close()


def test_bandeja_marca_critico_cuarentena_vieja(app, db_clean):
    """Lote >5 días en cuarentena debe marcarse como crítico."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT OR IGNORE INTO maestro_mps
                    (codigo_mp, nombre_comercial, activo)
                    VALUES ('MP_OLD_QUAR', 'Test Old Quarantine', 1)""")
    conn.execute("""INSERT INTO movimientos
                    (material_id, material_nombre, lote, cantidad, tipo,
                     fecha, estado_lote)
                    VALUES ('MP_OLD_QUAR', 'Test Old Quarantine', 'LOTE-OLD',
                            500, 'Entrada',
                            datetime('now', '-10 days'),
                            'Cuarentena')""")
    conn.commit(); conn.close()

    c = _login(app, "laura")
    r = c.get("/api/calidad/bandeja")
    data = r.get_json()
    sec = data["secciones"]["lotes_cuarentena"]
    assert sec["criticos"] >= 1

    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM movimientos WHERE material_id='MP_OLD_QUAR'")
    conn.execute("DELETE FROM maestro_mps WHERE codigo_mp='MP_OLD_QUAR'")
    conn.commit(); conn.close()


def test_bandeja_detecta_nc_abierta(app, db_clean):
    """NC en estado Abierta debe aparecer en bandeja."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO no_conformidades
                    (fecha, tipo, descripcion, area, impacto, estado)
                    VALUES (date('now'), 'Proceso',
                            'Test NC para bandeja',
                            'Calidad', 'Critico', 'Abierta')""")
    conn.commit(); conn.close()

    c = _login(app, "laura")
    r = c.get("/api/calidad/bandeja")
    data = r.get_json()
    sec = data["secciones"]["ncs_abiertas"]
    assert sec["total"] >= 1
    assert sec["criticas"] >= 1
    descs = [it["descripcion"] for it in sec["items"]]
    assert any("Test NC para bandeja" in d for d in descs)

    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM no_conformidades WHERE descripcion='Test NC para bandeja'")
    conn.commit(); conn.close()


def test_bandeja_kpi_total_pendientes(app, db_clean):
    """KPI total_pendientes suma las categorías que requieren acción."""
    c = _login(app, "laura")
    r = c.get("/api/calidad/bandeja")
    data = r.get_json()
    k = data["kpis"]
    expected = (
        k["lotes_cuarentena"] + k["ncs_abiertas"] + k["oos_abiertas"]
        + k["calibraciones_vencidas"] + k["cola_liberacion_listos"]
    )
    assert k["total_pendientes"] == expected


def test_bandeja_agua_registrada_hoy_alert(app, db_clean):
    """Si no hay registro de agua hoy, debe aparecer alerta."""
    # Borrar cualquier registro de hoy para garantizar el caso
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        conn.execute("DELETE FROM agua_registros WHERE date(fecha) = date('now')")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # tabla puede no existir
    conn.close()

    c = _login(app, "laura")
    r = c.get("/api/calidad/bandeja")
    data = r.get_json()
    sec = data["secciones"]["registro_agua_hoy"]
    assert sec["registrado"] is False
    assert "alerta" in sec
