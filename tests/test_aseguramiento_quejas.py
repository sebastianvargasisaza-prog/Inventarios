"""Tests del workflow de Quejas de Cliente (ASG-PRO-013)."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="laura"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _cleanup(qid_or_codigo):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    if isinstance(qid_or_codigo, int):
        conn.execute("DELETE FROM quejas_clientes_eventos WHERE queja_id=?", (qid_or_codigo,))
        conn.execute("DELETE FROM quejas_clientes WHERE id=?", (qid_or_codigo,))
    else:
        row = conn.execute("SELECT id FROM quejas_clientes WHERE codigo=?", (qid_or_codigo,)).fetchone()
        if row:
            conn.execute("DELETE FROM quejas_clientes_eventos WHERE queja_id=?", (row[0],))
            conn.execute("DELETE FROM quejas_clientes WHERE id=?", (row[0],))
    conn.commit(); conn.close()


def test_quejas_listar_estructura(app, db_clean):
    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/quejas")
    assert r.status_code == 200
    data = r.get_json()
    assert "items" in data
    assert "kpis" in data
    for k in ["total","nuevas","en_investigacion","pendientes_cierre","criticas_abiertas","cerradas_30d"]:
        assert k in data["kpis"]


def test_quejas_crear_codigo_auto(app, db_clean):
    c = _login(app, "luis")  # cualquier user puede registrar
    r = c.post("/api/aseguramiento/quejas",
               json={"canal": "email",
                     "tipo_queja": "calidad_producto",
                     "cliente_nombre": "María Pérez",
                     "cliente_contacto": "maria@example.com",
                     "producto": "SAH-30ml",
                     "lote": "LOTE-2026-001",
                     "descripcion": "El producto vino con grumos visibles desde el primer uso, no se distribuye bien."},
               headers=csrf_headers())
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    assert "QC-" in data["codigo"]
    _cleanup(data["id"])


def test_quejas_descripcion_corta_400(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/aseguramiento/quejas",
               json={"cliente_nombre": "Cliente X",
                     "descripcion": "corta"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_quejas_cliente_nombre_requerido_400(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/aseguramiento/quejas",
               json={"descripcion": "Descripción suficientemente larga aquí"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_quejas_workflow_completo(app, db_clean):
    """nueva → en_triaje → en_investigacion → respondida → cerrada."""
    c = _login(app, "laura")  # calidad puede hacer todo

    # 1. Registrar
    r = c.post("/api/aseguramiento/quejas",
               json={"canal": "whatsapp",
                     "tipo_queja": "envase_empaque",
                     "cliente_nombre": "Carlos Rodríguez",
                     "cliente_tipo": "consumidor_final",
                     "producto": "TRX-50ml",
                     "lote": "LOTE-2026-005",
                     "descripcion": "El envase llegó con la tapa rota, parece defecto de fabricación."},
               headers=csrf_headers())
    qid = r.get_json()["id"]
    codigo = r.get_json()["codigo"]

    # 2. Triaje
    r = c.post(f"/api/aseguramiento/quejas/{qid}/triaje",
               json={"severidad": "menor",
                     "triaje_descripcion": "Defecto cosmético del envase, no afecta producto interno",
                     "requiere_desviacion": False,
                     "requiere_recall": False},
               headers=csrf_headers())
    assert r.status_code == 200

    # 3. Investigar
    r = c.post(f"/api/aseguramiento/quejas/{qid}/investigar",
               json={"causa_raiz": "Lote LOTE-2026-005 tuvo problema en máquina de tapado, presión baja"},
               headers=csrf_headers())
    assert r.status_code == 200

    # 4. Responder cliente
    r = c.post(f"/api/aseguramiento/quejas/{qid}/responder",
               json={"respuesta_canal": "whatsapp",
                     "respuesta_descripcion": "Se enviará reposición sin costo adicional al cliente con disculpa formal",
                     "fecha_compromiso": "2026-05-10"},
               headers=csrf_headers())
    assert r.status_code == 200

    # 5. Cerrar
    r = c.post(f"/api/aseguramiento/quejas/{qid}/cerrar",
               json={"cliente_satisfecho": True,
                     "accion_correctiva": "Reposición enviada, máquina tapado recalibrada en planta",
                     "observaciones_cierre": "Cliente recibió producto reemplazo OK"},
               headers=csrf_headers())
    assert r.status_code == 200

    # Verificar estado final
    r = c.get(f"/api/aseguramiento/quejas/{qid}")
    data = r.get_json()
    assert data["estado"] == "cerrada"
    assert data["cliente_satisfecho"] == 1
    assert len(data["timeline"]) >= 5

    _cleanup(codigo)


def test_quejas_triaje_solo_calidad(app, db_clean):
    """Usuario sin rol Calidad/Admin → 403 al triar."""
    c_creator = _login(app, "luis")
    r = c_creator.post("/api/aseguramiento/quejas",
                       json={"cliente_nombre": "Test User",
                             "descripcion": "Test queja sin permiso para triaje aquí"},
                       headers=csrf_headers())
    qid = r.get_json()["id"]

    r = c_creator.post(f"/api/aseguramiento/quejas/{qid}/triaje",
                       json={"severidad": "menor",
                             "triaje_descripcion": "Triaje sin permiso"},
                       headers=csrf_headers())
    assert r.status_code == 403
    _cleanup(qid)


def test_quejas_no_puede_responder_sin_triar(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/quejas",
               json={"cliente_nombre": "Cliente Test",
                     "descripcion": "Descripción suficiente para crear la queja"},
               headers=csrf_headers())
    qid = r.get_json()["id"]
    # Intentar responder directo sin triar
    r = c.post(f"/api/aseguramiento/quejas/{qid}/responder",
               json={"respuesta_canal": "email",
                     "respuesta_descripcion": "Respuesta sin triaje previo aquí completa"},
               headers=csrf_headers())
    assert r.status_code == 409
    _cleanup(qid)


def test_quejas_no_puede_cerrar_sin_responder(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/quejas",
               json={"cliente_nombre": "Cliente Test",
                     "descripcion": "Descripción suficiente para crear la queja"},
               headers=csrf_headers())
    qid = r.get_json()["id"]
    # Triar
    r = c.post(f"/api/aseguramiento/quejas/{qid}/triaje",
               json={"severidad": "menor",
                     "triaje_descripcion": "Triaje OK aquí"},
               headers=csrf_headers())
    assert r.status_code == 200
    # Intentar cerrar sin responder
    r = c.post(f"/api/aseguramiento/quejas/{qid}/cerrar",
               json={"cliente_satisfecho": True,
                     "accion_correctiva": "Acción suficientemente larga aquí registrada"},
               headers=csrf_headers())
    assert r.status_code == 409
    _cleanup(qid)


def test_quejas_severidad_invalida_400(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/quejas",
               json={"cliente_nombre": "Cliente",
                     "descripcion": "Descripción larga suficiente para crear queja"},
               headers=csrf_headers())
    qid = r.get_json()["id"]
    r = c.post(f"/api/aseguramiento/quejas/{qid}/triaje",
               json={"severidad": "muy_grave",
                     "triaje_descripcion": "x"*15},
               headers=csrf_headers())
    assert r.status_code == 400
    _cleanup(qid)


def test_quejas_impacto_salud_kpi(app, db_clean):
    """Queja con impacto_salud y severidad crítica cuenta en KPI críticas_abiertas."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/quejas",
               json={"canal": "telefono",
                     "tipo_queja": "reaccion_adversa",
                     "cliente_nombre": "Paciente Anónimo",
                     "producto": "SAH-30ml",
                     "lote": "LOTE-2026-007",
                     "descripcion": "Cliente reporta enrojecimiento severo y picor tras aplicación primera vez",
                     "impacto_salud": True},
               headers=csrf_headers())
    assert r.status_code == 201
    qid = r.get_json()["id"]
    # KPI: impacta salud → ya cuenta como crítica abierta aunque sin severidad asignada
    r = c.get("/api/aseguramiento/quejas")
    kpis = r.get_json()["kpis"]
    assert kpis["criticas_abiertas"] >= 1
    _cleanup(qid)


def test_quejas_codigo_secuencial(app, db_clean):
    c = _login(app, "luis")
    codigos = []
    ids = []
    for i in range(3):
        r = c.post("/api/aseguramiento/quejas",
                   json={"cliente_nombre": f"Cliente {i+1}",
                         "descripcion": f"Queja secuencial número {i+1} suficientemente larga"},
                   headers=csrf_headers())
        codigos.append(r.get_json()["codigo"])
        ids.append(r.get_json()["id"])
    assert len(set(codigos)) == 3
    for cod in codigos:
        assert cod.startswith("QC-")
        parts = cod.split("-")
        assert len(parts) == 3
    for qid in ids:
        _cleanup(qid)


def test_quejas_endpoints_requieren_auth(client, db_clean):
    for path in ["/api/aseguramiento/quejas"]:
        r = client.get(path)
        assert r.status_code == 401
