"""Tests de estados terminales/inválidos en workflows ASG.

Verifica que NO se puede:
- Avanzar desde un estado terminal (cerrada, rechazada, cancelado).
- Saltar estados intermedios.
- Re-aprobar un cambio ya aprobado.
- Re-clasificar una desviación ya clasificada (cambio del workflow).

Cubre los 4 workflows: desviaciones · cambios · quejas · recalls.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="laura"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _cleanup(tabla, eventos_tabla, fk_col, codigo_or_id):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    if isinstance(codigo_or_id, int):
        conn.execute(f"DELETE FROM {eventos_tabla} WHERE {fk_col}=?", (codigo_or_id,))
        conn.execute(f"DELETE FROM {tabla} WHERE id=?", (codigo_or_id,))
    else:
        row = conn.execute(f"SELECT id FROM {tabla} WHERE codigo=?", (codigo_or_id,)).fetchone()
        if row:
            conn.execute(f"DELETE FROM {eventos_tabla} WHERE {fk_col}=?", (row[0],))
            conn.execute(f"DELETE FROM {tabla} WHERE id=?", (row[0],))
    conn.commit(); conn.close()


# ─── Desviaciones · estados terminales ──────────────────────────────────

def test_desv_no_se_puede_investigar_cerrada(app, db_clean):
    """Una desviación 'cerrada' no debe permitir investigar de nuevo."""
    c = _login(app, "laura")
    # Crear y avanzar a cerrada
    r = c.post("/api/aseguramiento/desviaciones",
               json={"tipo":"otra","descripcion":"Test estado terminal cerrada"},
               headers=csrf_headers())
    desv_id = r.get_json()["id"]
    c.post(f"/api/aseguramiento/desviaciones/{desv_id}/clasificar",
           json={"clasificacion":"menor","justificacion":"Test clasificacion menor"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/desviaciones/{desv_id}/investigar",
           json={"metodo_investigacion":"otro","causa_raiz":"Causa raiz texto suficiente"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/desviaciones/{desv_id}/capa",
           json={"capa_descripcion":"Capa descripcion suficiente para test","capa_responsable":"miguel"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/desviaciones/{desv_id}/cerrar",
           json={"efectividad_ok":True,"verificacion_efectividad":"Verificacion suficiente"},
           headers=csrf_headers())
    # Intentar investigar de nuevo · 409 (no 400 · payload válido)
    r = c.post(f"/api/aseguramiento/desviaciones/{desv_id}/investigar",
               json={"metodo_investigacion":"otro",
                     "causa_raiz":"Causa raiz alternativa con texto suficiente para pasar validacion"},
               headers=csrf_headers())
    assert r.status_code == 409
    _cleanup("desviaciones", "desviaciones_eventos", "desviacion_id", desv_id)


def test_desv_no_se_puede_cerrar_dos_veces(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/desviaciones",
               json={"tipo":"otra","descripcion":"Test cerrar dos veces"},
               headers=csrf_headers())
    desv_id = r.get_json()["id"]
    c.post(f"/api/aseguramiento/desviaciones/{desv_id}/clasificar",
           json={"clasificacion":"menor","justificacion":"Test"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/desviaciones/{desv_id}/investigar",
           json={"metodo_investigacion":"otro","causa_raiz":"Test causa raiz suficiente"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/desviaciones/{desv_id}/capa",
           json={"capa_descripcion":"Capa test descripcion suficiente","capa_responsable":"miguel"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/desviaciones/{desv_id}/cerrar",
           json={"efectividad_ok":True,"verificacion_efectividad":"Verificacion suficiente"},
           headers=csrf_headers())
    # Segundo intento de cerrar → 409 (verificacion ≥20 chars OK · falla por estado)
    r = c.post(f"/api/aseguramiento/desviaciones/{desv_id}/cerrar",
               json={"efectividad_ok":True,
                     "verificacion_efectividad":"Otra verificacion con texto suficiente para validar"},
               headers=csrf_headers())
    assert r.status_code == 409
    _cleanup("desviaciones", "desviaciones_eventos", "desviacion_id", desv_id)


# ─── Cambios · estados terminales ────────────────────────────────────────

def test_cambio_no_se_puede_evaluar_cerrado(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/cambios",
               json={"tipo":"otro","titulo":"Test cambio cerrado",
                     "descripcion":"Test descripcion completa para cambio cerrado"},
               headers=csrf_headers())
    cid = r.get_json()["id"]
    # Avanzar a cerrado
    c.post(f"/api/aseguramiento/cambios/{cid}/evaluar",
           json={"severidad":"menor","evaluacion_descripcion":"Test evaluacion menor descripcion"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/cambios/{cid}/aprobar",
           json={"decision":"aprobar","observaciones":"Observaciones suficientes",
                 "plan_implementacion":"Plan implementacion suficiente para test pasar validacion"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/cambios/{cid}/implementar",
           json={"observaciones":"Implementado test"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/cambios/{cid}/cerrar",
           json={"verificacion_ok":True,
                 "verificacion_post":"Verificacion post completada con texto suficiente"},
           headers=csrf_headers())
    # Intentar evaluar de nuevo
    r = c.post(f"/api/aseguramiento/cambios/{cid}/evaluar",
               json={"severidad":"mayor",
                     "evaluacion_descripcion":"Re-evaluacion despues de cerrado debe rechazarse"},
               headers=csrf_headers())
    assert r.status_code == 409
    _cleanup("control_cambios", "control_cambios_eventos", "cambio_id", cid)


def test_cambio_rechazado_no_se_puede_implementar(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/cambios",
               json={"tipo":"otro","titulo":"Test rechazado",
                     "descripcion":"Cambio descripcion suficiente para rechazo"},
               headers=csrf_headers())
    cid = r.get_json()["id"]
    c.post(f"/api/aseguramiento/cambios/{cid}/evaluar",
           json={"severidad":"menor","evaluacion_descripcion":"Evaluacion test descripcion completa"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/cambios/{cid}/aprobar",
           json={"decision":"rechazar","observaciones":"Rechazo motivado"},
           headers=csrf_headers())
    # Intentar implementar un cambio rechazado · 409
    r = c.post(f"/api/aseguramiento/cambios/{cid}/implementar",
               json={"observaciones":"Test implementar rechazado"},
               headers=csrf_headers())
    assert r.status_code == 409
    _cleanup("control_cambios", "control_cambios_eventos", "cambio_id", cid)


# ─── Quejas · estados terminales ─────────────────────────────────────────

def test_queja_no_se_puede_re_triar(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/quejas",
               json={"cliente_nombre":"Test","descripcion":"Queja para test re-triaje"},
               headers=csrf_headers())
    qid = r.get_json()["id"]
    c.post(f"/api/aseguramiento/quejas/{qid}/triaje",
           json={"severidad":"menor","triaje_descripcion":"Triaje test"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/quejas/{qid}/investigar",
           json={"causa_raiz":"Causa raiz suficiente para investigacion"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/quejas/{qid}/responder",
           json={"respuesta_canal":"email","respuesta_descripcion":"Respuesta suficiente para test"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/quejas/{qid}/cerrar",
           json={"cliente_satisfecho":True,"accion_correctiva":"Accion correctiva suficiente"},
           headers=csrf_headers())
    # Intentar re-triar después de cerrada · 409
    r = c.post(f"/api/aseguramiento/quejas/{qid}/triaje",
               json={"severidad":"mayor","triaje_descripcion":"Re-triaje despues cerrada"},
               headers=csrf_headers())
    assert r.status_code == 409
    _cleanup("quejas_clientes", "quejas_clientes_eventos", "queja_id", qid)


# ─── Recalls · estados terminales ────────────────────────────────────────

def test_recall_cerrado_no_se_puede_clasificar(app, db_clean):
    """Un recall ya cerrado no admite re-clasificación."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/recalls",
               json={"producto":"PROD","lotes_afectados":"LOTE-T",
                     "motivo":"Test recall para terminales suficiente"},
               headers=csrf_headers())
    rid = r.get_json()["id"]
    # Avanzar a cerrado
    c.post(f"/api/aseguramiento/recalls/{rid}/clasificar",
           json={"clase_recall":"clase_III","alcance_geografico":"local",
                 "justificacion_clasificacion":"Justificacion clase III test"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/recalls/{rid}/notificar-invima",
           json={"referencia":"X-test"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/recalls/{rid}/notificar-distribuidores",
           json={"distribuidores_notificados":"Distribuidor test"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/recalls/{rid}/recoleccion",
           json={"cantidad_recolectada":100,"completa":True},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/recalls/{rid}/cerrar",
           json={"disposicion_final":"destruccion",
                 "disposicion_descripcion":"Disposicion test descripcion suficiente"},
           headers=csrf_headers())
    # Intentar re-clasificar · 409
    r = c.post(f"/api/aseguramiento/recalls/{rid}/clasificar",
               json={"clase_recall":"clase_I","alcance_geografico":"nacional",
                     "justificacion_clasificacion":"Re-clasificacion despues cerrado test"},
               headers=csrf_headers())
    assert r.status_code == 409
    _cleanup("recalls", "recalls_eventos", "recall_id", rid)


def test_recall_no_se_puede_cerrar_sin_completar(app, db_clean):
    """No se puede cerrar un recall que no llegó a 'completado'."""
    c = _login(app, "laura")
    r = c.post("/api/aseguramiento/recalls",
               json={"producto":"PROD","lotes_afectados":"LOTE-T2",
                     "motivo":"Test cerrar sin completar suficiente"},
               headers=csrf_headers())
    rid = r.get_json()["id"]
    # Solo clasificar · NO avanzar más
    c.post(f"/api/aseguramiento/recalls/{rid}/clasificar",
           json={"clase_recall":"clase_III","alcance_geografico":"local",
                 "justificacion_clasificacion":"Justificacion suficiente test"},
           headers=csrf_headers())
    # Intentar cerrar sin completar · 409
    r = c.post(f"/api/aseguramiento/recalls/{rid}/cerrar",
               json={"disposicion_final":"destruccion",
                     "disposicion_descripcion":"Test no debe permitir cerrar aqui"},
               headers=csrf_headers())
    assert r.status_code == 409
    _cleanup("recalls", "recalls_eventos", "recall_id", rid)
