"""Tests de los endpoints de reportes ad-hoc INVIMA.

Endpoints:
- /api/aseguramiento/reportes/audit-trail
- /api/aseguramiento/reportes/lote-trazabilidad/<lote>
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


# ─── Audit trail ──────────────────────────────────────────────────────

def test_audit_trail_requires_auth(client, db_clean):
    r = client.get("/api/aseguramiento/reportes/audit-trail")
    assert r.status_code == 401


def test_audit_trail_user_no_calidad_403(app, db_clean):
    c = _login(app, "luis")  # luis no es Calidad
    r = c.get("/api/aseguramiento/reportes/audit-trail")
    assert r.status_code == 403


def test_audit_trail_default_30d(app, db_clean):
    """Sin filtros, devuelve audit log de los últimos 30 días."""
    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/reportes/audit-trail")
    assert r.status_code == 200
    data = r.get_json()
    assert "desde" in data
    assert "hasta" in data
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_audit_trail_filtro_accion(app, db_clean):
    """Filtro por accion exacta."""
    c = _login(app, "laura")
    # Generar entrada audit log con CERRAR_DESVIACION
    r = c.post("/api/aseguramiento/desviaciones",
               json={"tipo":"otra","descripcion":"Audit trail test desviacion para cierre"},
               headers=csrf_headers())
    desv_id = r.get_json()["id"]
    c.post(f"/api/aseguramiento/desviaciones/{desv_id}/clasificar",
           json={"clasificacion":"menor","justificacion":"Test audit trail clasificacion"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/desviaciones/{desv_id}/investigar",
           json={"metodo_investigacion":"otro","causa_raiz":"Causa raiz suficiente para test audit trail"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/desviaciones/{desv_id}/capa",
           json={"capa_descripcion":"CAPA suficiente para test audit trail",
                 "capa_responsable":"miguel"},
           headers=csrf_headers())
    c.post(f"/api/aseguramiento/desviaciones/{desv_id}/cerrar",
           json={"efectividad_ok":True,
                 "verificacion_efectividad":"Verificacion suficiente para test audit trail"},
           headers=csrf_headers())
    # Filtrar
    r = c.get("/api/aseguramiento/reportes/audit-trail?accion=CERRAR_DESVIACION")
    items = r.get_json()["items"]
    assert any(it["accion"] == "CERRAR_DESVIACION" for it in items)
    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM desviaciones WHERE id=?", (desv_id,))
    conn.execute("DELETE FROM desviaciones_eventos WHERE desviacion_id=?", (desv_id,))
    conn.commit(); conn.close()


# ─── Lote trazabilidad ─────────────────────────────────────────────────

def test_lote_trazabilidad_requires_auth(client, db_clean):
    r = client.get("/api/aseguramiento/reportes/lote-trazabilidad/LOTE-X-001")
    assert r.status_code == 401


def test_lote_trazabilidad_user_no_calidad_403(app, db_clean):
    c = _login(app, "luis")
    r = c.get("/api/aseguramiento/reportes/lote-trazabilidad/LOTE-X-001")
    assert r.status_code == 403


def test_lote_trazabilidad_estructura(app, db_clean):
    """Devuelve estructura completa con 7 secciones."""
    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/reportes/lote-trazabilidad/LOTE-INEXISTENTE")
    assert r.status_code == 200
    data = r.get_json()
    assert data["lote"] == "LOTE-INEXISTENTE"
    assert "consulta_at" in data
    assert data["consultado_por"] == "laura"
    cadena = data["cadena"]
    for seccion in ("recepciones", "producciones_uso", "coas", "ncs", "oos",
                      "despachos_clientes", "desviaciones", "recalls"):
        assert seccion in cadena
        assert isinstance(cadena[seccion], list)
    # Resumen con counts por sección
    assert "resumen" in data
    for seccion in ("recepciones", "producciones", "coas", "ncs", "oos",
                      "despachos", "desviaciones", "recalls"):
        assert seccion in data["resumen"]
        assert isinstance(data["resumen"][seccion], int)


def test_lote_trazabilidad_lote_corto_400(app, db_clean):
    """Lote vacío o muy corto rechaza."""
    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/reportes/lote-trazabilidad/X")
    assert r.status_code == 400


def test_cliente_trazabilidad_requires_auth(client, db_clean):
    r = client.get("/api/aseguramiento/reportes/cliente-trazabilidad/1")
    assert r.status_code == 401


def test_cliente_trazabilidad_user_no_calidad_403(app, db_clean):
    c = _login(app, "luis")
    r = c.get("/api/aseguramiento/reportes/cliente-trazabilidad/1")
    assert r.status_code == 403


def test_cliente_trazabilidad_inexistente_404(app, db_clean):
    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/reportes/cliente-trazabilidad/99999")
    assert r.status_code == 404


def test_cliente_trazabilidad_estructura(app, db_clean):
    """Cliente existente devuelve estructura completa."""
    c = _login(app, "laura")
    # Crear cliente test
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.execute("""
        INSERT INTO clientes (codigo, nombre, empresa, activo)
        VALUES ('CLI-TRAZA-T', 'Cliente Traza Test', 'ANIMUS', 1)
    """)
    cid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.get(f"/api/aseguramiento/reportes/cliente-trazabilidad/{cid}")
        assert r.status_code == 200
        data = r.get_json()
        assert data["cliente"]["nombre"] == "Cliente Traza Test"
        assert "despachos" in data
        assert "pedidos" in data
        assert "lotes_unicos" in data
        assert "resumen" in data
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM clientes WHERE id=?", (cid,))
        conn.commit(); conn.close()


def test_audit_trail_csv_export(app, db_clean):
    """Export CSV devuelve text/csv con headers correctos."""
    c = _login(app, "laura")
    r = c.get("/api/aseguramiento/reportes/audit-trail/csv")
    assert r.status_code == 200
    assert 'text/csv' in r.headers.get('Content-Type', '')
    assert 'attachment' in r.headers.get('Content-Disposition', '')
    body = r.get_data(as_text=True)
    # Headers presentes
    assert 'usuario' in body and 'accion' in body and 'fecha' in body


def test_audit_trail_csv_user_no_calidad_403(app, db_clean):
    c = _login(app, "luis")
    r = c.get("/api/aseguramiento/reportes/audit-trail/csv")
    assert r.status_code == 403


def test_reportes_ui_pestana_y_handlers(app, db_clean):
    """La página /aseguramiento incluye la pestaña Reportes INVIMA + handlers JS."""
    c = _login(app, "laura")
    r = c.get("/aseguramiento")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    # Pestaña + pane
    assert "tab-reportes" in body
    assert "Reportes INVIMA" in body
    # Sub-pestañas
    assert "rep-audit" in body and "rep-lote" in body and "rep-cliente" in body
    # Handlers JS declarados (no solo referenciados en onclick)
    assert "function repInit(" in body
    assert "function repGoTab(" in body
    assert "async function repAuditCargar(" in body
    assert "function repAuditExport(" in body
    assert "async function repLoteCargar(" in body
    assert "async function repClienteCargar(" in body
    # _tabIds incluye tab-reportes
    assert "'tab-reportes'" in body
    # goTab dispatch para tab-reportes
    assert "id==='tab-reportes'" in body


def test_lote_trazabilidad_encuentra_desviacion(app, db_clean):
    """Si una desviación menciona el lote, aparece en la cadena."""
    c = _login(app, "laura")
    lote_test = "LOTE-TRAZA-T01"
    # Crear desviación con lote
    r = c.post("/api/aseguramiento/desviaciones",
               json={"tipo":"materia_prima",
                     "descripcion":"Desviación test trazabilidad por lote especifico",
                     "lotes_afectados": lote_test},
               headers=csrf_headers())
    desv_id = r.get_json()["id"]
    # Consultar trazabilidad
    r = c.get(f"/api/aseguramiento/reportes/lote-trazabilidad/{lote_test}")
    data = r.get_json()
    assert data["resumen"]["desviaciones"] >= 1
    desviaciones = data["cadena"]["desviaciones"]
    assert len(desviaciones) >= 1
    # Cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM desviaciones WHERE id=?", (desv_id,))
    conn.execute("DELETE FROM desviaciones_eventos WHERE desviacion_id=?", (desv_id,))
    conn.commit(); conn.close()
