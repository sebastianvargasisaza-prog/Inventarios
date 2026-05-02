"""Tests del workflow de Desviaciones (ASG-PRO-001)."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="laura"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_desv_listar_estructura(app, db_clean):
    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/desviaciones")
    assert r.status_code == 200
    data = r.get_json()
    assert "items" in data
    assert "kpis" in data
    for k in ["total","criticas_abiertas","sin_clasificar","investigando","cerradas_30d"]:
        assert k in data["kpis"]


def test_desv_crear_con_codigo_auto(app, db_clean):
    c = _login(app, "luis")  # cualquier user puede reportar
    r = c.post("/api/aseguramiento/desviaciones",
               json={"tipo": "sistema_agua",
                     "area_origen": "Lab CC",
                     "descripcion": "Conductividad fuera de spec en tanque RO 1.8 µS/cm",
                     "contencion_inmediata": "Tanque cuarentena",
                     "impacto_producto": True,
                     "lotes_afectados": "LOTE-X-001"},
               headers=csrf_headers())
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    assert "DESV-" in data["codigo"]

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM desviaciones WHERE id=?", (data["id"],))
    conn.execute("DELETE FROM desviaciones_eventos WHERE desviacion_id=?", (data["id"],))
    conn.commit(); conn.close()


def test_desv_descripcion_corta_400(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/aseguramiento/desviaciones",
               json={"descripcion": "corta"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_desv_workflow_completo(app, db_clean):
    """Detectada → clasificada → investigada → CAPA → cerrada."""
    c = _login(app, "laura")  # calidad puede hacer todo

    # 1. Crear
    r = c.post("/api/aseguramiento/desviaciones",
               json={"tipo": "equipo",
                     "area_origen": "Fab1",
                     "descripcion": "Balanza BL-PRD-001 muestra deriva en verificación diaria"},
               headers=csrf_headers())
    desv_id = r.get_json()["id"]
    codigo = r.get_json()["codigo"]

    # 2. Clasificar
    r = c.post(f"/api/aseguramiento/desviaciones/{desv_id}/clasificar",
               json={"clasificacion": "mayor",
                     "justificacion": "Equipo crítico afecta dispensación de MP"},
               headers=csrf_headers())
    assert r.status_code == 200

    # 3. Investigar
    r = c.post(f"/api/aseguramiento/desviaciones/{desv_id}/investigar",
               json={"metodo_investigacion": "5_porques",
                     "causa_raiz": "Pesa patrón no se verificó la semana anterior por descanso del operario"},
               headers=csrf_headers())
    assert r.status_code == 200

    # 4. CAPA
    r = c.post(f"/api/aseguramiento/desviaciones/{desv_id}/capa",
               json={"capa_descripcion": "Recalibrar balanza, capacitar al backup en verificación diaria",
                     "capa_responsable": "miguel",
                     "capa_fecha_limite": "2026-06-15"},
               headers=csrf_headers())
    assert r.status_code == 200

    # 5. Cerrar
    r = c.post(f"/api/aseguramiento/desviaciones/{desv_id}/cerrar",
               json={"efectividad_ok": True,
                     "verificacion_efectividad": "Balanza recalibrada, dos verificaciones diarias OK",
                     "observaciones_cierre": "Backup capacitado"},
               headers=csrf_headers())
    assert r.status_code == 200

    # Verificar estado final
    r = c.get(f"/api/aseguramiento/desviaciones/{desv_id}")
    data = r.get_json()
    assert data["estado"] == "cerrada"
    assert data["efectividad_ok"] == 1
    assert len(data["timeline"]) >= 5  # 5 eventos del workflow

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM desviaciones WHERE codigo=?", (codigo,))
    conn.execute("DELETE FROM desviaciones_eventos WHERE desviacion_id=?", (desv_id,))
    conn.commit(); conn.close()


def test_desv_clasificar_solo_calidad(app, db_clean):
    """Usuario sin rol Calidad/Admin → 403."""
    c_creator = _login(app, "luis")
    r = c_creator.post("/api/aseguramiento/desviaciones",
                       json={"tipo": "documental",
                             "descripcion": "Test desviación sin permiso"},
                       headers=csrf_headers())
    desv_id = r.get_json()["id"]

    # luis NO puede clasificar
    r = c_creator.post(f"/api/aseguramiento/desviaciones/{desv_id}/clasificar",
                       json={"clasificacion": "menor", "justificacion": "test"},
                       headers=csrf_headers())
    assert r.status_code == 403

    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM desviaciones WHERE id=?", (desv_id,))
    conn.execute("DELETE FROM desviaciones_eventos WHERE desviacion_id=?", (desv_id,))
    conn.commit(); conn.close()


def test_desv_no_puede_cerrar_sin_capa(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/desviaciones",
               json={"tipo": "otra", "descripcion": "Test no se puede cerrar sin pasos"},
               headers=csrf_headers())
    desv_id = r.get_json()["id"]
    # Intentar cerrar directamente
    r = c.post(f"/api/aseguramiento/desviaciones/{desv_id}/cerrar",
               json={"efectividad_ok": True,
                     "verificacion_efectividad": "Verificación texto suficiente"},
               headers=csrf_headers())
    assert r.status_code == 409  # estado inválido

    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM desviaciones WHERE id=?", (desv_id,))
    conn.execute("DELETE FROM desviaciones_eventos WHERE desviacion_id=?", (desv_id,))
    conn.commit(); conn.close()


def test_desv_clasificacion_invalida(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/desviaciones",
               json={"tipo": "otra", "descripcion": "Test clasif invalid"},
               headers=csrf_headers())
    desv_id = r.get_json()["id"]

    r = c.post(f"/api/aseguramiento/desviaciones/{desv_id}/clasificar",
               json={"clasificacion": "muy_grave", "justificacion": "x"*15},
               headers=csrf_headers())
    assert r.status_code == 400

    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM desviaciones WHERE id=?", (desv_id,))
    conn.execute("DELETE FROM desviaciones_eventos WHERE desviacion_id=?", (desv_id,))
    conn.commit(); conn.close()


def test_desv_codigo_secuencial(app, db_clean):
    """Cada desviación nueva tiene código único secuencial DESV-AAAA-NNNN."""
    c = _login(app, "luis")
    codigos = []
    ids = []
    for i in range(3):
        r = c.post("/api/aseguramiento/desviaciones",
                   json={"tipo": "otra",
                         "descripcion": f"Desviación de prueba secuencial {i+1}"},
                   headers=csrf_headers())
        codigos.append(r.get_json()["codigo"])
        ids.append(r.get_json()["id"])
    # Todos diferentes
    assert len(set(codigos)) == 3
    # Formato correcto
    for cod in codigos:
        assert cod.startswith("DESV-")
        parts = cod.split("-")
        assert len(parts) == 3

    conn = sqlite3.connect(os.environ["DB_PATH"])
    for i in ids:
        conn.execute("DELETE FROM desviaciones WHERE id=?", (i,))
        conn.execute("DELETE FROM desviaciones_eventos WHERE desviacion_id=?", (i,))
    conn.commit(); conn.close()


def test_desv_endpoints_requieren_auth(client, db_clean):
    for path in ["/api/aseguramiento/desviaciones"]:
        r = client.get(path)
        assert r.status_code == 401
