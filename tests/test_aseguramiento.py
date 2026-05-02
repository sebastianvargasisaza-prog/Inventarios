"""Tests del módulo Aseguramiento (ASG · /aseguramiento).

SGD electrónico + capacitaciones + conflictos. Complementario a /calidad.
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


# ─── Página y dashboard ─────────────────────────────────────────────────

def test_aseguramiento_pagina_redirect_sin_login(client, db_clean):
    """GET /aseguramiento sin login redirige a /login."""
    r = client.get("/aseguramiento", follow_redirects=False)
    assert r.status_code == 302


def test_aseguramiento_pagina_con_login(app, db_clean):
    """GET /aseguramiento con login retorna HTML."""
    c = _login(app, "laura")
    r = c.get("/aseguramiento")
    assert r.status_code == 200
    assert b"ASEGURAMIENTO" in r.data


def test_dashboard_estructura(app, db_clean):
    """GET /api/aseguramiento/dashboard retorna estructura completa con 4 workflows."""
    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/dashboard")
    assert r.status_code == 200
    data = r.get_json()
    assert "fecha_hoy" in data
    assert "sgd" in data
    assert "capacitaciones" in data
    assert "ncs_abiertas" in data
    assert "auditorias_60d" in data
    # Workflows ASG
    assert "desviaciones" in data
    assert "cambios" in data
    assert "quejas" in data
    assert "recalls" in data
    # Cada workflow tiene KPIs mínimos
    for k in ("total","sin_clasificar","criticas_abiertas","investigando","cerradas_30d"):
        assert k in data["desviaciones"], f"falta {k} en desviaciones"
    for k in ("total","sin_evaluar","aprobados_pendientes","invima_pendiente","cerrados_30d"):
        assert k in data["cambios"], f"falta {k} en cambios"
    for k in ("total","nuevas","pendientes_cierre","criticas_abiertas","cerradas_30d"):
        assert k in data["quejas"], f"falta {k} en quejas"
    for k in ("total","sin_clasificar","clase_I_abiertos","invima_pendiente","en_recoleccion","cerrados_30d"):
        assert k in data["recalls"], f"falta {k} en recalls"
    # Alertas consolidadas (lista, vacía si no hay urgentes)
    assert "alertas_criticas" in data
    assert isinstance(data["alertas_criticas"], list)


def test_dashboard_requiere_auth(client, db_clean):
    r = client.get("/api/aseguramiento/dashboard")
    assert r.status_code == 401


def test_sgd_pdf_actualizar_solo_calidad(app, db_clean):
    """POST /sgd/<codigo>/pdf actualiza el PDF · solo Calidad/Admin."""
    # Crear doc primero
    cal = _login(app, "laura")
    r = cal.post("/api/aseguramiento/sgd",
                 json={"codigo": "COC-PRO-099", "titulo": "Test PDF doc"},
                 headers=csrf_headers())
    assert r.status_code == 200

    # luis (no Calidad) → 403
    luis = _login(app, "luis")
    r = luis.post("/api/aseguramiento/sgd/COC-PRO-099/pdf",
                  json={"archivo_pdf_url": "https://drive.example/test.pdf"},
                  headers=csrf_headers())
    assert r.status_code == 403

    # laura (Calidad) → OK
    r = cal.post("/api/aseguramiento/sgd/COC-PRO-099/pdf",
                 json={"archivo_pdf_url": "https://drive.example/test.pdf"},
                 headers=csrf_headers())
    assert r.status_code == 200
    assert r.get_json()["ok"] is True
    assert r.get_json()["archivo_pdf_url"] == "https://drive.example/test.pdf"

    # Verificar persistencia
    r = cal.get("/api/aseguramiento/sgd/COC-PRO-099")
    assert r.get_json()["archivo_pdf_url"] == "https://drive.example/test.pdf"

    # Limpiar PDF (URL vacía)
    r = cal.post("/api/aseguramiento/sgd/COC-PRO-099/pdf",
                 json={"archivo_pdf_url": ""},
                 headers=csrf_headers())
    assert r.status_code == 200
    assert r.get_json()["archivo_pdf_url"] is None

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sgd_documentos WHERE codigo='COC-PRO-099'")
    conn.commit(); conn.close()


def test_sgd_pdf_url_invalida_400(app, db_clean):
    """URL no http(s) → 400."""
    cal = _login(app, "laura")
    cal.post("/api/aseguramiento/sgd",
             json={"codigo": "COC-PRO-098", "titulo": "Test"},
             headers=csrf_headers())
    r = cal.post("/api/aseguramiento/sgd/COC-PRO-098/pdf",
                 json={"archivo_pdf_url": "javascript:alert(1)"},
                 headers=csrf_headers())
    assert r.status_code == 400
    r = cal.post("/api/aseguramiento/sgd/COC-PRO-098/pdf",
                 json={"archivo_pdf_url": "ftp://server/file.pdf"},
                 headers=csrf_headers())
    assert r.status_code == 400
    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sgd_documentos WHERE codigo='COC-PRO-098'")
    conn.commit(); conn.close()


def test_sgd_pdf_doc_inexistente_404(app, db_clean):
    cal = _login(app, "laura")
    r = cal.post("/api/aseguramiento/sgd/COC-PRO-777/pdf",
                 json={"archivo_pdf_url": "https://x.com/y.pdf"},
                 headers=csrf_headers())
    assert r.status_code == 404


def test_mis_tareas_estructura(app, db_clean):
    """GET /api/aseguramiento/mis-tareas devuelve estructura correcta."""
    c = _login(app, "luis")
    r = c.get("/api/aseguramiento/mis-tareas")
    assert r.status_code == 200
    data = r.get_json()
    assert data["usuario"] == "luis"
    assert data["es_calidad"] is False  # luis no es Calidad
    for k in ("capacitaciones","mis_creados","calidad_queue","urgentes","resumen"):
        assert k in data
    assert isinstance(data["capacitaciones"], list)
    assert isinstance(data["mis_creados"], list)


def test_mis_tareas_user_calidad_ve_queue(app, db_clean):
    """Usuario en CALIDAD_USERS ve la cola consolidada."""
    cal = _login(app, "laura")
    r = cal.get("/api/aseguramiento/mis-tareas")
    assert r.status_code == 200
    data = r.get_json()
    assert data["usuario"] == "laura"
    assert data["es_calidad"] is True


def test_mis_tareas_no_ve_de_otros(app, db_clean):
    """Items que creó luis NO aparecen en mis_creados de laura."""
    luis = _login(app, "luis")
    r = luis.post("/api/aseguramiento/desviaciones",
                  json={"tipo": "otra", "descripcion": "Desviación reportada por luis para test mis tareas"},
                  headers=csrf_headers())
    desv_id = r.get_json()["id"]

    laura = _login(app, "laura")
    r = laura.get("/api/aseguramiento/mis-tareas")
    creados = r.get_json()["mis_creados"]
    # laura no creó nada → su lista de mis_creados no tiene la desviación de luis
    for it in creados:
        assert it.get("modulo") != "desviaciones" or "luis" not in str(it)

    # Pero luis SÍ ve su desviación
    r = luis.get("/api/aseguramiento/mis-tareas")
    creados_luis = r.get_json()["mis_creados"]
    assert any(it["modulo"]=="desviaciones" for it in creados_luis)

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM desviaciones WHERE id=?", (desv_id,))
    conn.execute("DELETE FROM desviaciones_eventos WHERE desviacion_id=?", (desv_id,))
    conn.commit(); conn.close()


def test_mis_tareas_queue_calidad_aparece_queja_nueva(app, db_clean):
    """Una queja nueva aparece en calidad_queue para Calidad."""
    luis = _login(app, "luis")
    r = luis.post("/api/aseguramiento/quejas",
                  json={"cliente_nombre": "Cliente test queue",
                        "descripcion": "Queja para verificar que aparece en cola Calidad"},
                  headers=csrf_headers())
    qid = r.get_json()["id"]

    laura = _login(app, "laura")
    r = laura.get("/api/aseguramiento/mis-tareas")
    queue = r.get_json()["calidad_queue"]
    quejas_en_queue = [it for it in queue if it["modulo"]=="quejas"]
    assert len(quejas_en_queue) >= 1

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM quejas_clientes_eventos WHERE queja_id=?", (qid,))
    conn.execute("DELETE FROM quejas_clientes WHERE id=?", (qid,))
    conn.commit(); conn.close()


def test_mis_tareas_requiere_auth(client, db_clean):
    r = client.get("/api/aseguramiento/mis-tareas")
    assert r.status_code == 401


# ─── Audit log regulatorio (Resolución 2214/2021) ─────────────────────

def test_audit_log_columnas_antes_despues(app, db_clean):
    """Migración 91 garantiza que audit_log tenga columnas antes/despues."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cols = [r[1] for r in conn.execute("PRAGMA table_info(audit_log)").fetchall()]
    conn.close()
    assert 'antes' in cols, f"falta columna antes en audit_log. Tiene: {cols}"
    assert 'despues' in cols, f"falta columna despues en audit_log. Tiene: {cols}"


def test_audit_log_sgd_pdf_se_inserta(app, db_clean):
    """Actualizar PDF debe quedar en audit_log."""
    cal = _login(app, "laura")
    cal.post("/api/aseguramiento/sgd",
             json={"codigo": "COC-PRO-080", "titulo": "Test audit"},
             headers=csrf_headers())
    cal.post("/api/aseguramiento/sgd/COC-PRO-080/pdf",
             json={"archivo_pdf_url": "https://x.com/y.pdf"},
             headers=csrf_headers())
    conn = sqlite3.connect(os.environ["DB_PATH"])
    rows = conn.execute("""
        SELECT usuario, accion, tabla, registro_id, despues
        FROM audit_log WHERE accion='SGD_PDF' AND registro_id='COC-PRO-080'
        ORDER BY id DESC LIMIT 1
    """).fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0][0] == 'laura'
    assert rows[0][2] == 'sgd_documentos'
    assert 'archivo_pdf_url' in (rows[0][4] or '')


def test_audit_log_capacitacion_firma(app, db_clean):
    """Firma de SOP es evidencia INVIMA primaria · debe ir a audit_log."""
    cal = _login(app, "laura")
    cal.post("/api/aseguramiento/sgd",
             json={"codigo": "COC-PRO-070", "titulo": "Test firma"},
             headers=csrf_headers())
    cal.post("/api/aseguramiento/capacitaciones/asignar",
             json={"sgd_codigo": "COC-PRO-070", "sgd_version": "1",
                   "personas": ["miguel"]},
             headers=csrf_headers())
    miguel = _login(app, "miguel")
    miguel.post("/api/aseguramiento/capacitaciones/firmar",
                json={"sgd_codigo": "COC-PRO-070", "sgd_version": "1"},
                headers=csrf_headers())
    conn = sqlite3.connect(os.environ["DB_PATH"])
    rows = conn.execute("""
        SELECT usuario, accion, tabla
        FROM audit_log WHERE accion='SGD_FIRMAR_CAP'
        AND registro_id LIKE 'COC-PRO-070%'
    """).fetchall()
    conn.close()
    assert len(rows) >= 1, "firma no llegó a audit_log"
    assert rows[0][0] == 'miguel'


def test_kpis_no_limitados_a_500_pagina(app, db_clean):
    """KPIs deben reflejar TOTAL en BD, no la página de 500."""
    cal = _login(app, "laura")
    # Estructura del response: total + sin_evaluar + ...
    r = cal.get("/api/aseguramiento/cambios")
    assert r.status_code == 200
    kpis = r.get_json()['kpis']
    assert isinstance(kpis['total'], int)
    # Crear 1 cambio y verificar que el total sube en 1
    total_antes = kpis['total']
    cal.post("/api/aseguramiento/cambios",
             json={"tipo": "otro", "titulo": "Test KPI",
                   "descripcion": "Test que KPIs reflejan COUNT real, no len(items) de la página"},
             headers=csrf_headers())
    r = cal.get("/api/aseguramiento/cambios")
    assert r.get_json()['kpis']['total'] == total_antes + 1
    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM control_cambios WHERE titulo='Test KPI'")
    conn.commit(); conn.close()


def test_cambio_implementar_bloquea_sin_invima_notif(app, db_clean):
    """cambio_implementar debe bloquear si requiere_invima=1 y no se notificó."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/cambios",
               json={"tipo": "formulacion", "titulo": "Cambio crítico INVIMA",
                     "descripcion": "Cambio fórmula con impacto regulatorio que requiere INVIMA",
                     "impacto_regulatorio": True},
               headers=csrf_headers())
    cid = r.get_json()["id"]
    # Evaluar marcando requiere_invima
    c.post(f"/api/aseguramiento/cambios/{cid}/evaluar",
           json={"severidad": "mayor",
                 "evaluacion_descripcion": "Mayor · requiere notificación INVIMA",
                 "requiere_invima": True},
           headers=csrf_headers())
    # Aprobar
    c.post(f"/api/aseguramiento/cambios/{cid}/aprobar",
           json={"decision": "aprobar",
                 "observaciones": "Aprobado pero pendiente INVIMA",
                 "plan_implementacion": "Implementar tras notificación INVIMA + esperar respuesta"},
           headers=csrf_headers())
    # Intentar implementar SIN notificar INVIMA → 409
    r = c.post(f"/api/aseguramiento/cambios/{cid}/implementar",
               json={"observaciones": "Test sin notif"},
               headers=csrf_headers())
    assert r.status_code == 409
    assert 'INVIMA' in r.get_json()['error']
    # Notificar INVIMA y reintentar → 200
    c.post(f"/api/aseguramiento/cambios/{cid}/notificar-invima",
           json={"referencia": "INVIMA-2026-X"},
           headers=csrf_headers())
    r = c.post(f"/api/aseguramiento/cambios/{cid}/implementar",
               json={"observaciones": "Implementado tras INVIMA"},
               headers=csrf_headers())
    assert r.status_code == 200
    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM control_cambios WHERE id=?", (cid,))
    conn.execute("DELETE FROM control_cambios_eventos WHERE cambio_id=?", (cid,))
    conn.commit(); conn.close()


def test_audit_log_recall_iniciar(app, db_clean):
    """INICIAR_RECALL debe llegar a audit_log (regulatorio crítico INVIMA)."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/recalls",
               json={"producto": "PROD-X-test", "lotes_afectados": "LOTE-T01",
                     "motivo": "Test audit_log debe registrar inicio de recall siempre"},
               headers=csrf_headers())
    rid = r.get_json()["id"]
    codigo = r.get_json()["codigo"]
    conn = sqlite3.connect(os.environ["DB_PATH"])
    rows = conn.execute("""
        SELECT accion, tabla, registro_id, despues FROM audit_log
        WHERE accion='INICIAR_RECALL' AND registro_id=?
    """, (codigo,)).fetchall()
    assert len(rows) == 1
    assert 'PROD-X-test' in (rows[0][3] or '')
    conn.execute("DELETE FROM recalls WHERE id=?", (rid,))
    conn.execute("DELETE FROM recalls_eventos WHERE recall_id=?", (rid,))
    conn.commit(); conn.close()


def test_audit_log_recall_clasificar_y_notif_invima(app, db_clean):
    """Clasificar recall + notificar INVIMA debe quedar en audit_log."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/recalls",
               json={"producto": "PROD-Y-test", "lotes_afectados": "LOTE-T02",
                     "motivo": "Test audit clasificación + notificación INVIMA"},
               headers=csrf_headers())
    rid = r.get_json()["id"]
    codigo = r.get_json()["codigo"]
    c.post(f"/api/aseguramiento/recalls/{rid}/clasificar",
           json={"clase_recall": "clase_I", "alcance_geografico": "nacional",
                 "justificacion_clasificacion": "Riesgo grave salud · Clase I por norma"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/recalls/{rid}/notificar-invima",
           json={"referencia": "INVIMA-2026-RCL-T02"},
           headers=csrf_headers())
    conn = sqlite3.connect(os.environ["DB_PATH"])
    acciones = [r[0] for r in conn.execute("""
        SELECT accion FROM audit_log WHERE registro_id=? ORDER BY id
    """, (codigo,)).fetchall()]
    assert 'INICIAR_RECALL' in acciones
    assert 'RECALL_CLASIFICAR' in acciones
    assert 'RECALL_NOTIFICAR_INVIMA' in acciones
    conn.execute("DELETE FROM recalls WHERE id=?", (rid,))
    conn.execute("DELETE FROM recalls_eventos WHERE recall_id=?", (rid,))
    conn.commit(); conn.close()


def test_dashboard_kpis_workflows_se_actualizan(app, db_clean):
    """Crear desviación + queja crítica → KPIs del dashboard reflejan cambios."""
    c = _login(app, "laura")
    # Crear desviación crítica abierta
    r = c.post("/api/aseguramiento/desviaciones",
               json={"tipo": "equipo", "area_origen": "Lab",
                     "descripcion": "Test desviación dashboard KPI funcional"},
               headers=csrf_headers())
    desv_id = r.get_json()["id"]
    c.post(f"/api/aseguramiento/desviaciones/{desv_id}/clasificar",
           json={"clasificacion": "critica",
                 "justificacion": "Test crítica para KPI dashboard"},
           headers=csrf_headers())
    # Crear queja con impacto salud
    r = c.post("/api/aseguramiento/quejas",
               json={"canal":"email","tipo_queja":"reaccion_adversa",
                     "cliente_nombre":"Test Cliente",
                     "descripcion":"Test queja salud para KPI dashboard",
                     "impacto_salud": True},
               headers=csrf_headers())
    queja_id = r.get_json()["id"]

    r = c.get("/api/aseguramiento/dashboard")
    data = r.get_json()
    assert data["desviaciones"]["total"] >= 1
    assert data["desviaciones"]["criticas_abiertas"] >= 1
    assert data["quejas"]["total"] >= 1
    assert data["quejas"]["criticas_abiertas"] >= 1  # impacto_salud cuenta

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM desviaciones_eventos WHERE desviacion_id=?", (desv_id,))
    conn.execute("DELETE FROM desviaciones WHERE id=?", (desv_id,))
    conn.execute("DELETE FROM quejas_clientes_eventos WHERE queja_id=?", (queja_id,))
    conn.execute("DELETE FROM quejas_clientes WHERE id=?", (queja_id,))
    conn.commit(); conn.close()


# ─── SGD electrónico ─────────────────────────────────────────────────────

def test_sgd_listado_vacio(app, db_clean):
    """Sin documentos importados, retorna lista vacía pero estructura OK."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sgd_documentos")
    conn.commit(); conn.close()

    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/sgd/listado")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 0
    assert data["items"] == []
    assert "areas" in data
    assert "tipos_doc" in data


def test_sgd_crear_documento(app, db_clean):
    """POST /api/aseguramiento/sgd con código válido crea documento."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/sgd",
               json={"codigo": "COC-PRO-099",
                     "titulo": "Test Procedure",
                     "version": "1",
                     "estado": "vigente",
                     "elaborado_por": "Laura"},
               headers=csrf_headers())
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["accion"] == "creado"

    # Verificar que aparece en listado
    r2 = c.get("/api/aseguramiento/sgd/listado?area=COC")
    items = r2.get_json()["items"]
    codigos = [it["codigo"] for it in items]
    assert "COC-PRO-099" in codigos

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sgd_documentos WHERE codigo='COC-PRO-099'")
    conn.commit(); conn.close()


def test_sgd_codigo_invalido(app, db_clean):
    """Código fuera del formato AAA-BBB-NNN → 400."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/sgd",
               json={"codigo": "FOO-BAR-X", "titulo": "Test"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_sgd_area_no_reconocida(app, db_clean):
    """Área fuera de las 8 oficiales → 400."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/sgd",
               json={"codigo": "XYZ-PRO-001", "titulo": "Test"},
               headers=csrf_headers())
    assert r.status_code == 400


def test_sgd_actualizar_archiva_version_anterior(app, db_clean):
    """Cambiar versión actual archiva la anterior en sgd_versiones."""
    c = _login(app, "laura")
    # Crear v1
    c.post("/api/aseguramiento/sgd",
           json={"codigo": "ASG-PRO-099", "titulo": "Test ASG",
                 "version": "1", "fecha_aprobacion": "2026-01-01"},
           headers=csrf_headers())
    # Cambiar a v2
    r = c.post("/api/aseguramiento/sgd",
               json={"codigo": "ASG-PRO-099", "titulo": "Test ASG",
                     "version": "2", "fecha_aprobacion": "2026-05-01",
                     "motivo_cambio": "Actualización por hallazgo"},
               headers=csrf_headers())
    assert r.status_code == 200

    # Verificar que la v1 quedó en histórico
    conn = sqlite3.connect(os.environ["DB_PATH"])
    rows = conn.execute(
        "SELECT version, motivo_cambio FROM sgd_versiones WHERE codigo='ASG-PRO-099'"
    ).fetchall()
    conn.execute("DELETE FROM sgd_documentos WHERE codigo='ASG-PRO-099'")
    conn.execute("DELETE FROM sgd_versiones WHERE codigo='ASG-PRO-099'")
    conn.commit(); conn.close()

    versiones = [r[0] for r in rows]
    assert "1" in versiones, f"versión 1 debería estar archivada · histórico: {versiones}"


def test_sgd_detalle_no_existe(app, db_clean):
    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/sgd/COC-PRO-999999")
    assert r.status_code == 404


def test_sgd_solo_calidad_admin_pueden_escribir(app, db_clean):
    """Usuario sin rol de Calidad/Admin → 403."""
    c = _login(app, "luis")  # planta operativa
    r = c.post("/api/aseguramiento/sgd",
               json={"codigo": "COC-PRO-088", "titulo": "X"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_sgd_importar_admin_only(app, db_clean):
    """Solo admin puede importar masivamente."""
    c = _login(app, "laura")  # calidad pero no admin
    r = c.post("/api/aseguramiento/sgd/importar",
               json={"items": [{"codigo": "COC-PRO-077", "titulo": "X"}]},
               headers=csrf_headers())
    assert r.status_code == 403

    c_admin = _login(app, "sebastian")
    r2 = c_admin.post("/api/aseguramiento/sgd/importar",
                      json={"items": [
                          {"codigo": "COC-PRO-077", "titulo": "Test importado"},
                          {"codigo": "ASG-PRO-077", "titulo": "Test ASG importado"},
                      ]},
                      headers=csrf_headers())
    assert r2.status_code == 200
    data = r2.get_json()
    assert data["insertados"] == 2

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sgd_documentos WHERE codigo IN ('COC-PRO-077','ASG-PRO-077')")
    conn.commit(); conn.close()


# ─── Capacitaciones ──────────────────────────────────────────────────────

def test_capacitaciones_asignar_y_firmar(app, db_clean):
    """Asignar a una persona y luego firmar como esa persona."""
    c_admin = _login(app, "laura")
    # Crear documento
    c_admin.post("/api/aseguramiento/sgd",
                 json={"codigo": "RRH-PRO-099", "titulo": "Test RRHH",
                       "version": "1"},
                 headers=csrf_headers())
    # Asignar a smurillo
    r = c_admin.post("/api/aseguramiento/capacitaciones/asignar",
                     json={"sgd_codigo": "RRH-PRO-099",
                           "sgd_version": "1",
                           "personas": ["smurillo"]},
                     headers=csrf_headers())
    assert r.status_code == 200
    assert r.get_json()["asignados"] == 1

    # Login como smurillo y firmar
    c_user = _login(app, "smurillo")
    r2 = c_user.get("/api/aseguramiento/capacitaciones/mias")
    items = r2.get_json()["items"]
    assert any(it["sgd_codigo"] == "RRH-PRO-099" for it in items)

    r3 = c_user.post("/api/aseguramiento/capacitaciones/firmar",
                     json={"sgd_codigo": "RRH-PRO-099", "sgd_version": "1"},
                     headers=csrf_headers())
    assert r3.status_code == 200
    assert "firma_hash" in r3.get_json()

    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sgd_capacitaciones WHERE sgd_codigo='RRH-PRO-099'")
    conn.execute("DELETE FROM sgd_documentos WHERE codigo='RRH-PRO-099'")
    conn.commit(); conn.close()


def test_capacitaciones_firmar_sin_asignacion(app, db_clean):
    """Si no tiene la capacitación asignada → 404."""
    c = _login(app, "smurillo")
    r = c.post("/api/aseguramiento/capacitaciones/firmar",
               json={"sgd_codigo": "FAKE-PRO-001", "sgd_version": "1"},
               headers=csrf_headers())
    assert r.status_code == 404


def test_capacitaciones_doc_no_existe(app, db_clean):
    """Asignar capacitación de doc inexistente → 404."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/capacitaciones/asignar",
               json={"sgd_codigo": "FAKE-DOC-001", "sgd_version": "1",
                     "personas": ["luis"]},
               headers=csrf_headers())
    assert r.status_code == 404


# ─── Conflictos ──────────────────────────────────────────────────────────

def test_conflictos_listar(app, db_clean):
    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/sgd/conflictos")
    assert r.status_code == 200
    assert "items" in r.get_json()


def test_conflictos_resolver_requiere_resolucion_larga(app, db_clean):
    """Resolución <10 chars → 400."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("""INSERT INTO sgd_conflictos (codigo, archivos_detectados, temas_detectados)
                    VALUES ('TEST-CONF-001', 'a;b', 'tema1;tema2')""")
    cid = conn.execute("SELECT id FROM sgd_conflictos WHERE codigo='TEST-CONF-001'").fetchone()[0]
    conn.commit(); conn.close()

    c = _login(app, "laura")
    r = c.post(f"/api/aseguramiento/sgd/conflictos/{cid}/resolver",
               json={"resolucion": "corta"},
               headers=csrf_headers())
    assert r.status_code == 400

    r2 = c.post(f"/api/aseguramiento/sgd/conflictos/{cid}/resolver",
                json={"resolucion": "Resolución detallada con más de 10 caracteres"},
                headers=csrf_headers())
    assert r2.status_code == 200

    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM sgd_conflictos WHERE codigo='TEST-CONF-001'")
    conn.commit(); conn.close()
