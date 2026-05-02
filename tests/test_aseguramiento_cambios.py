"""Tests del workflow de Control de Cambios (ASG-PRO-007)."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="laura"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _cleanup(cid_or_codigo):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    if isinstance(cid_or_codigo, int):
        conn.execute("DELETE FROM control_cambios_eventos WHERE cambio_id=?", (cid_or_codigo,))
        conn.execute("DELETE FROM control_cambios WHERE id=?", (cid_or_codigo,))
    else:
        row = conn.execute("SELECT id FROM control_cambios WHERE codigo=?", (cid_or_codigo,)).fetchone()
        if row:
            conn.execute("DELETE FROM control_cambios_eventos WHERE cambio_id=?", (row[0],))
            conn.execute("DELETE FROM control_cambios WHERE id=?", (row[0],))
    conn.commit(); conn.close()


def test_cambios_listar_estructura(app, db_clean):
    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/cambios")
    assert r.status_code == 200
    data = r.get_json()
    assert "items" in data
    assert "kpis" in data
    for k in ["total","sin_evaluar","en_evaluacion","aprobados_pendientes","requieren_invima","cerrados_30d"]:
        assert k in data["kpis"]


def test_cambios_crear_con_codigo_auto(app, db_clean):
    c = _login(app, "luis")  # cualquier user puede solicitar
    r = c.post("/api/aseguramiento/cambios",
               json={"tipo": "proveedor",
                     "titulo": "Cambio de proveedor de glicerina",
                     "descripcion": "Cambiar proveedor actual A por proveedor B con mejor calidad y precio competitivo",
                     "justificacion": "Reducción 15% costo MP",
                     "areas_afectadas": "Compras, Producción, Calidad",
                     "impacto_bpm": False,
                     "impacto_regulatorio": False},
               headers=csrf_headers())
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    assert "CHG-" in data["codigo"]
    _cleanup(data["id"])


def test_cambios_titulo_corto_400(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/aseguramiento/cambios",
               json={"titulo": "abc",
                     "descripcion": "Descripción suficientemente larga del cambio propuesto"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_cambios_descripcion_corta_400(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/aseguramiento/cambios",
               json={"titulo": "Cambio menor",
                     "descripcion": "corta"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_cambios_workflow_completo(app, db_clean):
    """solicitado → en_evaluacion → aprobado → implementado → cerrado."""
    c = _login(app, "laura")  # calidad puede hacer todo

    # 1. Solicitar
    r = c.post("/api/aseguramiento/cambios",
               json={"tipo": "documental",
                     "titulo": "Actualizar SOP COC-PRO-008 a versión 3",
                     "descripcion": "Incorporar verificación adicional de conductividad cada 4h en lugar de 8h",
                     "justificacion": "Hallazgo de auditoría INVIMA",
                     "areas_afectadas": "Calidad, Producción"},
               headers=csrf_headers())
    assert r.status_code == 201
    cid = r.get_json()["id"]
    codigo = r.get_json()["codigo"]

    # 2. Evaluar
    r = c.post(f"/api/aseguramiento/cambios/{cid}/evaluar",
               json={"severidad": "menor",
                     "evaluacion_descripcion": "Cambio documental sin impacto técnico mayor, formato existente solo cambia frecuencia",
                     "requiere_invima": False},
               headers=csrf_headers())
    assert r.status_code == 200

    # 3. Aprobar
    r = c.post(f"/api/aseguramiento/cambios/{cid}/aprobar",
               json={"decision": "aprobar",
                     "observaciones": "Aprobado, ejecutar antes de fin de mes",
                     "plan_implementacion": "Actualizar SOP, capacitar al personal de Calidad y poner en vigencia versión 3",
                     "fecha_implementacion_propuesta": "2026-06-15",
                     "responsable_implementacion": "yuliel"},
               headers=csrf_headers())
    assert r.status_code == 200

    # 4. Implementar
    r = c.post(f"/api/aseguramiento/cambios/{cid}/implementar",
               json={"observaciones": "SOP v3 publicado, personal capacitado"},
               headers=csrf_headers())
    assert r.status_code == 200

    # 5. Cerrar
    r = c.post(f"/api/aseguramiento/cambios/{cid}/cerrar",
               json={"verificacion_ok": True,
                     "verificacion_post": "Tres auditorías diarias OK, registros completos en bandeja del día",
                     "observaciones_cierre": "Sin novedad"},
               headers=csrf_headers())
    assert r.status_code == 200

    # Verificar estado final
    r = c.get(f"/api/aseguramiento/cambios/{cid}")
    data = r.get_json()
    assert data["estado"] == "cerrado"
    assert data["verificacion_ok"] == 1
    assert len(data["timeline"]) >= 5  # 5 eventos del workflow

    _cleanup(codigo)


def test_cambios_evaluar_solo_calidad(app, db_clean):
    """Usuario sin rol Calidad/Admin → 403 al evaluar."""
    c_creator = _login(app, "luis")
    r = c_creator.post("/api/aseguramiento/cambios",
                       json={"tipo": "otro",
                             "titulo": "Test sin permiso",
                             "descripcion": "Descripción suficientemente larga para superar validación mínima"},
                       headers=csrf_headers())
    cid = r.get_json()["id"]

    # luis NO puede evaluar
    r = c_creator.post(f"/api/aseguramiento/cambios/{cid}/evaluar",
                       json={"severidad": "menor",
                             "evaluacion_descripcion": "x"*25,
                             "requiere_invima": False},
                       headers=csrf_headers())
    assert r.status_code == 403
    _cleanup(cid)


def test_cambios_no_puede_cerrar_sin_implementar(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/cambios",
               json={"tipo": "otro",
                     "titulo": "Test no se puede cerrar",
                     "descripcion": "Descripción suficientemente larga para superar validación mínima"},
               headers=csrf_headers())
    cid = r.get_json()["id"]
    # Intentar cerrar directamente
    r = c.post(f"/api/aseguramiento/cambios/{cid}/cerrar",
               json={"verificacion_ok": True,
                     "verificacion_post": "Verificación texto suficientemente largo aquí"},
               headers=csrf_headers())
    assert r.status_code == 409  # estado inválido
    _cleanup(cid)


def test_cambios_aprobar_requiere_plan(app, db_clean):
    """Si decisión = aprobar, plan_implementacion es obligatorio."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/cambios",
               json={"tipo": "otro",
                     "titulo": "Test aprobar sin plan",
                     "descripcion": "Descripción suficientemente larga para superar validación"},
               headers=csrf_headers())
    cid = r.get_json()["id"]
    # Evaluar primero
    r = c.post(f"/api/aseguramiento/cambios/{cid}/evaluar",
               json={"severidad": "menor",
                     "evaluacion_descripcion": "Evaluación con texto suficientemente largo"},
               headers=csrf_headers())
    assert r.status_code == 200
    # Intentar aprobar SIN plan
    r = c.post(f"/api/aseguramiento/cambios/{cid}/aprobar",
               json={"decision": "aprobar",
                     "observaciones": "Aprobando rápido"},
               headers=csrf_headers())
    assert r.status_code == 400
    _cleanup(cid)


def test_cambios_rechazar_no_requiere_plan(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/cambios",
               json={"tipo": "otro",
                     "titulo": "Test rechazo",
                     "descripcion": "Descripción suficientemente larga para superar validación"},
               headers=csrf_headers())
    cid = r.get_json()["id"]
    r = c.post(f"/api/aseguramiento/cambios/{cid}/evaluar",
               json={"severidad": "mayor",
                     "evaluacion_descripcion": "Evaluación con texto suficientemente largo"},
               headers=csrf_headers())
    assert r.status_code == 200
    r = c.post(f"/api/aseguramiento/cambios/{cid}/aprobar",
               json={"decision": "rechazar",
                     "observaciones": "No procede por riesgo regulatorio"},
               headers=csrf_headers())
    assert r.status_code == 200
    # Verificar estado final
    r = c.get(f"/api/aseguramiento/cambios/{cid}")
    assert r.get_json()["estado"] == "rechazado"
    _cleanup(cid)


def test_cambios_invima_workflow(app, db_clean):
    """Cambio que requiere INVIMA: aprobar → notificar → implementar → cerrar."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/cambios",
               json={"tipo": "formulacion",
                     "titulo": "Cambio fórmula SAH (sérum)",
                     "descripcion": "Modificar concentración de niacinamida del 4% al 5% en SAH-30ml",
                     "impacto_bpm": True,
                     "impacto_regulatorio": True},
               headers=csrf_headers())
    cid = r.get_json()["id"]
    codigo = r.get_json()["codigo"]
    # Evaluar marcando requiere_invima
    r = c.post(f"/api/aseguramiento/cambios/{cid}/evaluar",
               json={"severidad": "mayor",
                     "evaluacion_descripcion": "Cambio de fórmula activa, requiere notificación INVIMA por modificación post-registro",
                     "requiere_invima": True},
               headers=csrf_headers())
    assert r.status_code == 200
    # Aprobar
    r = c.post(f"/api/aseguramiento/cambios/{cid}/aprobar",
               json={"decision": "aprobar",
                     "observaciones": "Aprobado, requiere INVIMA antes de implementar",
                     "plan_implementacion": "Notificar INVIMA, esperar respuesta, ajustar fichas técnicas y arrancar fabricación con nueva fórmula",
                     "responsable_implementacion": "alejandro"},
               headers=csrf_headers())
    assert r.status_code == 200
    # Notificar INVIMA
    r = c.post(f"/api/aseguramiento/cambios/{cid}/notificar-invima",
               json={"referencia": "INVIMA-2026-987654"},
               headers=csrf_headers())
    assert r.status_code == 200
    # Verificar
    r = c.get(f"/api/aseguramiento/cambios/{cid}")
    data = r.get_json()
    assert data["notificacion_invima_ref"] == "INVIMA-2026-987654"
    assert data["notificacion_invima_at"] is not None
    _cleanup(codigo)


def test_cambios_notificar_invima_sin_requerir(app, db_clean):
    """No se debe poder notificar INVIMA si no requiere."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/cambios",
               json={"tipo": "documental",
                     "titulo": "Cambio menor sin INVIMA",
                     "descripcion": "Solo documental sin impacto regulatorio significativo alguno"},
               headers=csrf_headers())
    cid = r.get_json()["id"]
    r = c.post(f"/api/aseguramiento/cambios/{cid}/evaluar",
               json={"severidad": "menor",
                     "evaluacion_descripcion": "Cambio sin impacto regulatorio en absoluto",
                     "requiere_invima": False},
               headers=csrf_headers())
    assert r.status_code == 200
    # Intentar notificar INVIMA
    r = c.post(f"/api/aseguramiento/cambios/{cid}/notificar-invima",
               json={"referencia": "INVIMA-XXX"},
               headers=csrf_headers())
    assert r.status_code == 400
    _cleanup(cid)


def test_cambios_codigo_secuencial(app, db_clean):
    """Cada cambio nuevo tiene código único secuencial CHG-AAAA-NNNN."""
    c = _login(app, "luis")
    codigos = []
    ids = []
    for i in range(3):
        r = c.post("/api/aseguramiento/cambios",
                   json={"tipo": "otro",
                         "titulo": f"Cambio secuencial {i+1}",
                         "descripcion": f"Descripción de prueba secuencial número {i+1} suficientemente larga"},
                   headers=csrf_headers())
        codigos.append(r.get_json()["codigo"])
        ids.append(r.get_json()["id"])
    assert len(set(codigos)) == 3
    for cod in codigos:
        assert cod.startswith("CHG-")
        parts = cod.split("-")
        assert len(parts) == 3
    for cid in ids:
        _cleanup(cid)


def test_cambios_endpoints_requieren_auth(client, db_clean):
    for path in ["/api/aseguramiento/cambios"]:
        r = client.get(path)
        assert r.status_code == 401
