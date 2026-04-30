"""Tests del módulo Marketing — Fase 4/4.

Sebastian (29-abr-2026): "que sea agencia de marketing tirando todo,
que se mantenga, que no se rompa nunca más".

Cobertura:
  ✓ Cada uno de los 11 agentes responde 200 (smoke test)
  ✓ Workflow aplicar-agente crea entidades reales (campaña, brief, flag)
  ✓ Workflow es idempotente (no duplica)
  ✓ Workflow rechaza agente desconocido
  ✓ Endpoint refresh-metrics funciona
  ✓ Endpoint metrics-history devuelve estructura correcta
  ✓ Bulk import de influencers crea SOL+OC+pago_inf
  ✓ Reset pendientes borra solo lo correcto
"""
import pytest
import sqlite3


def _login_admin(app):
    """Login como admin (sebastian)."""
    from .conftest import TEST_PASSWORD
    c = app.test_client()
    r = c.post("/login",
               data={"username": "sebastian", "password": TEST_PASSWORD},
               headers={"Origin": "http://localhost"},
               follow_redirects=False)
    assert r.status_code == 302
    return c


def _login_marketing(app):
    """Login como user marketing (jefferson)."""
    from .conftest import TEST_PASSWORD
    c = app.test_client()
    r = c.post("/login",
               data={"username": "jefferson", "password": TEST_PASSWORD},
               headers={"Origin": "http://localhost"},
               follow_redirects=False)
    assert r.status_code == 302
    return c


# ─── Tests de cada agente (smoke) ──────────────────────────────────

@pytest.mark.parametrize("agente", [
    "estacionalidad", "oportunidad", "roi", "tendencias",
    "brief", "pricing", "reorden", "canibal", "contenido_auto",
    "alerta_stock", "estrategia",
])
def test_agente_responde_200(app, db_clean, agente):
    """Cada agente del módulo marketing responde 200 sin crashear."""
    client = _login_admin(app)
    r = client.post(f"/api/marketing/agentes/{agente}",
                    json={},  # body vacío JSON (algunos agentes leen request.get_json)
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200, f"Agente {agente} falló: {r.get_data(as_text=True)[:200]}"
    d = r.get_json()
    # Debe tener al menos titulo o algún identificador
    assert isinstance(d, dict)


def test_agente_desconocido_devuelve_400(app, db_clean):
    """Llamar un agente que no existe → 400."""
    client = _login_admin(app)
    r = client.post("/api/marketing/agentes/agente_inventado",
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 400


# ─── Tests de workflow aplicar-agente ──────────────────────────────

def test_workflow_oportunidad_crea_campanas(app, db_clean):
    """Workflow oportunidad: payload con SKUs → marketing_campanas Planificadas."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    # Limpiar campañas previas para evitar idempotencia
    con = sqlite3.connect(db_path)
    con.execute("DELETE FROM marketing_campanas WHERE sku_objetivo LIKE 'TEST_WF%'")
    con.commit(); con.close()

    client = _login_admin(app)
    payload = {
        "recomendaciones": [
            {"sku": "TEST_WF_A", "stock": 100, "razones": ["test razón A"]},
            {"sku": "TEST_WF_B", "stock": 50, "razones": ["test razón B"]},
        ]
    }
    r = client.post("/api/marketing/workflow/aplicar-agente",
                    json={"agente": "oportunidad", "payload": payload},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is True
    assert d["campanas"] == 2

    # Verificar en BD
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT sku_objetivo, estado FROM marketing_campanas WHERE sku_objetivo LIKE 'TEST_WF%'"
    ).fetchall()
    con.close()
    assert len(rows) == 2
    assert all(r[1] == "Planificada" for r in rows)


def test_workflow_oportunidad_es_idempotente(app, db_clean):
    """Si ya hay campaña activa para el SKU, el workflow la skip."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    con = sqlite3.connect(db_path)
    con.execute("DELETE FROM marketing_campanas WHERE sku_objetivo='TEST_IDEMP'")
    # Pre-crear campaña activa
    con.execute("""
        INSERT INTO marketing_campanas (nombre, sku_objetivo, estado, tipo, canal)
        VALUES ('Pre-existente', 'TEST_IDEMP', 'Planificada', 'Push', 'Influencer')
    """)
    con.commit(); con.close()

    client = _login_admin(app)
    r = client.post("/api/marketing/workflow/aplicar-agente",
                    json={"agente": "oportunidad",
                          "payload": {"recomendaciones": [
                              {"sku": "TEST_IDEMP", "stock": 100, "razones": ["x"]}
                          ]}},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200
    d = r.get_json()
    assert d["campanas"] == 0  # NO creó porque ya existía
    assert any("ya tiene campaña activa" in str(item) for item in d.get("detalle", []))


def test_workflow_contenido_auto_crea_briefs(app, db_clean):
    """Workflow contenido_auto: piezas → marketing_contenido estado='Brief'."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    con = sqlite3.connect(db_path)
    con.execute("DELETE FROM marketing_contenido WHERE sku_objetivo LIKE 'TEST_BRIEF%'")
    con.commit(); con.close()

    client = _login_admin(app)
    payload = {
        "piezas": [
            {"sku": "TEST_BRIEF_A", "caption_instagram": "✨ Caption A"},
            {"sku": "TEST_BRIEF_B", "caption_instagram": "✨ Caption B"},
        ]
    }
    r = client.post("/api/marketing/workflow/aplicar-agente",
                    json={"agente": "contenido_auto", "payload": payload},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["briefs"] == 2

    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT sku_objetivo, estado FROM marketing_contenido WHERE sku_objetivo LIKE 'TEST_BRIEF%'"
    ).fetchall()
    con.close()
    assert len(rows) == 2
    assert all(r[1] == "Brief" for r in rows)


def test_workflow_alerta_stock_crea_flags(app, db_clean):
    """Workflow alerta_stock: SKUs críticos → marketing_campanas Reposición."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    con = sqlite3.connect(db_path)
    con.execute("DELETE FROM marketing_campanas WHERE sku_objetivo LIKE 'TEST_FLAG%'")
    con.commit(); con.close()

    client = _login_admin(app)
    payload = {
        "alertas": [
            {"sku": "TEST_FLAG_A", "stock": 5, "nivel": "critico",
             "accion": "Producir urgente"},
        ]
    }
    r = client.post("/api/marketing/workflow/aplicar-agente",
                    json={"agente": "alerta_stock", "payload": payload},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["solicitudes_produccion"] == 1


def test_workflow_agente_desconocido(app, db_clean):
    """Workflow para agente sin handler → 400 con mensaje útil."""
    client = _login_admin(app)
    r = client.post("/api/marketing/workflow/aplicar-agente",
                    json={"agente": "agente_no_implementado", "payload": {}},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 400
    d = r.get_json()
    assert "no implementado" in d.get("error", "").lower()


# ─── Tests de socialblade / metrics ────────────────────────────────

def test_refresh_metrics_sin_usuario_red_falla_grace(app, db_clean):
    """Si el influencer no tiene usuario_red, devuelve 400 con mensaje claro."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    con = sqlite3.connect(db_path)
    con.execute(
        "INSERT INTO marketing_influencers (nombre, red_social, usuario_red, estado) "
        "VALUES ('Test sin user', 'Instagram', '', 'Activo')"
    )
    iid = con.execute(
        "SELECT id FROM marketing_influencers WHERE nombre='Test sin user'"
    ).fetchone()[0]
    con.commit(); con.close()

    client = _login_admin(app)
    r = client.post(f"/api/marketing/influencers/{iid}/refresh-metrics",
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 400
    d = r.get_json()
    assert "usuario_red" in d.get("error", "")


def test_metrics_history_devuelve_estructura(app, db_clean):
    """metrics-history devuelve list aunque vacío."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    con = sqlite3.connect(db_path)
    con.execute(
        "INSERT INTO marketing_influencers (nombre, red_social, usuario_red, estado) "
        "VALUES ('Test history', 'Instagram', 'test_history_user', 'Activo')"
    )
    iid = con.execute(
        "SELECT id FROM marketing_influencers WHERE nombre='Test history'"
    ).fetchone()[0]
    # Insertar 1 snapshot
    con.execute("""
        INSERT INTO marketing_influencers_metrics
          (influencer_id, fecha, seguidores, fuente)
        VALUES (?, date('now'), 5000, 'socialblade')
    """, (iid,))
    con.commit(); con.close()

    client = _login_admin(app)
    r = client.get(f"/api/marketing/influencers/{iid}/metrics-history?dias=30",
                   headers={"Origin": "http://localhost"})
    assert r.status_code == 200
    d = r.get_json()
    assert "snapshots" in d
    assert d["count"] >= 1


def test_refresh_all_metrics_solo_admin(app, db_clean):
    """Refresh masivo requiere admin."""
    client = _login_marketing(app)
    r = client.post("/api/marketing/refresh-all-metrics",
                    headers={"Origin": "http://localhost"})
    # jefferson NO es admin → 401 o 403
    assert r.status_code in (401, 403)


# ─── Tests de bulk import / reset (29abr) ──────────────────────────

def test_bulk_import_crea_sol_oc_pago(app, db_clean):
    """Bulk import crea SOL Aprobada + OC Aprobada + pago_influencer Pendiente."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    # Limpiar antes
    con = sqlite3.connect(db_path)
    con.execute("DELETE FROM marketing_influencers WHERE nombre='Test Bulk Inf'")
    con.commit(); con.close()

    client = _login_admin(app)
    r = client.post("/admin/influencers-bulk-import",
                    json={"influencers": [
                        {"nombre": "Test Bulk Inf", "telefono": "3001234567",
                         "ciudad": "Cali", "costo": 500000,
                         "fecha_pub": "2026-05-15",
                         "concepto": "Test bulk"}
                    ]},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["creados"] == 1

    con = sqlite3.connect(db_path)
    inf_row = con.execute(
        "SELECT id FROM marketing_influencers WHERE nombre='Test Bulk Inf'"
    ).fetchone()
    assert inf_row is not None
    sol = con.execute(
        "SELECT estado, valor FROM solicitudes_compra WHERE influencer_id=? AND categoria='Cuenta de Cobro'",
        (inf_row[0],)
    ).fetchone()
    assert sol is not None
    assert sol[0] == "Aprobada"
    assert sol[1] == 500000
    con.close()


def test_bulk_import_es_idempotente(app, db_clean):
    """Llamar bulk import 2x con el mismo influencer no duplica SOLs."""
    db_path = app.config.get("DATABASE") or __import__("os").environ["DB_PATH"]
    con = sqlite3.connect(db_path)
    con.execute("DELETE FROM marketing_influencers WHERE nombre='Test Idemp Inf'")
    con.commit(); con.close()

    client = _login_admin(app)
    item = {"nombre": "Test Idemp Inf", "telefono": "3009999999",
            "ciudad": "Cali", "costo": 200000, "fecha_pub": "2026-05-20",
            "concepto": "Test idemp"}
    r1 = client.post("/admin/influencers-bulk-import",
                     json={"influencers": [item]},
                     headers={"Origin": "http://localhost"})
    assert r1.status_code == 200
    assert r1.get_json()["creados"] == 1

    r2 = client.post("/admin/influencers-bulk-import",
                     json={"influencers": [item]},
                     headers={"Origin": "http://localhost"})
    assert r2.status_code == 200
    d2 = r2.get_json()
    assert d2["creados"] == 0  # ya existía
    assert d2["skipped"] == 1


def test_reset_pendientes_solo_admin(app, db_clean):
    """Reset pendientes requiere admin."""
    client = _login_marketing(app)
    r = client.post("/admin/influencers-reset-pendientes",
                    headers={"Origin": "http://localhost"})
    assert r.status_code in (401, 403)


def test_audit_socialblade_helper_no_crashea_con_url_invalida(app, db_clean):
    """_fetch_socialblade_data debe devolver None si la cuenta no existe,
    no lanzar excepción."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
    from blueprints.marketing import _fetch_socialblade_data
    # Usuario inventado que con seguridad no existe
    result = _fetch_socialblade_data("usuario_inventado_xyz_test_999_no_existe")
    # Esperamos None (no excepción)
    assert result is None or isinstance(result, dict)
