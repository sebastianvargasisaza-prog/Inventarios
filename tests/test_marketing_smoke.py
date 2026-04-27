"""Smoke tests for marketing endpoints."""
import re
import shutil
import subprocess

import pytest

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="jefferson"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_marketing_influencers_panel(app, db_clean):
    c = _login(app)
    r = c.get("/api/marketing/influencers-panel")
    assert r.status_code == 200
    j = r.get_json()
    assert "_error" not in j, f"endpoint error: {j.get('_error')} | {j.get('_trace','')}"


def test_marketing_pagos_influencers(app, db_clean):
    c = _login(app)
    r = c.get("/api/marketing/pagos-influencers")
    assert r.status_code == 200
    j = r.get_json()
    assert "_error" not in j, f"endpoint error: {j.get('_error')} | {j.get('_trace','')}"


def test_marketing_page(app, db_clean):
    c = _login(app)
    r = c.get("/marketing")
    assert r.status_code in (200, 302), f"unexpected status: {r.status_code}"


def test_debug_endpoints_admin_only(app, db_clean):
    """Endpoints debug (ig-debug, ghl-debug, debug-influencers, fix-pago-link)
    deben rechazar a usuarios marketing comunes — solo admin (sebastian).
    Antes estaban abiertos a Jefferson y exponían tokens/IDs."""
    c_jeff = _login(app, "jefferson")
    c_seb  = _login(app, "sebastian")

    debug_endpoints = [
        ("GET",  "/api/marketing/ig-debug"),
        ("GET",  "/api/marketing/ghl-debug"),
        ("GET",  "/api/marketing/debug-influencers"),
        ("POST", "/api/marketing/fix-pago-link"),
    ]
    for method, url in debug_endpoints:
        if method == "GET":
            r = c_jeff.get(url)
        else:
            r = c_jeff.post(url, headers=csrf_headers(), json={})
        assert r.status_code == 403, (
            f"{url} debió rechazar a jefferson — got {r.status_code}: "
            f"{r.get_data(as_text=True)[:200]}"
        )

    # Sebastian (admin) sí puede entrar — al menos no recibe 403
    for method, url in debug_endpoints:
        if method == "GET":
            r = c_seb.get(url)
        else:
            r = c_seb.post(url, headers=csrf_headers(), json={})
        assert r.status_code != 403, f"sebastian no debería ser rechazado en {url}"


def test_atribucion_influencers_endpoint(app, db_clean):
    """Endpoint de atribución por discount code retorna estructura correcta
    aunque no haya influencers con code asignado.

    Schema check: depende de migration 32 (discount_code, discount_codes,
    subtotal, total_descuentos). Si rompe, la migración no corrió.
    """
    import os
    import sqlite3
    db_path = os.environ.get("DB_PATH")
    assert db_path
    conn = sqlite3.connect(db_path)
    # Insertar 1 influencer con code y 2 órdenes que lo usan
    conn.execute("""INSERT INTO marketing_influencers
        (nombre, red_social, estado, discount_code) VALUES (?,?,?,?)""",
        ("Test Inf", "Instagram", "Activo", "ANIMUS_TEST10"))
    conn.execute("""INSERT INTO animus_shopify_orders
        (shopify_id, nombre, email, total, sku_items, unidades_total,
         creado_en, discount_codes, subtotal, total_descuentos)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        ("9001", "#9001", "a@b.com", 100000, "[]", 1,
         "2026-04-20", "ANIMUS_TEST10", 110000, 10000))
    conn.execute("""INSERT INTO animus_shopify_orders
        (shopify_id, nombre, email, total, sku_items, unidades_total,
         creado_en, discount_codes, subtotal, total_descuentos)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        ("9002", "#9002", "c@d.com", 200000, "[]", 2,
         "2026-04-21", "OTRO,ANIMUS_TEST10", 220000, 20000))
    conn.commit()
    conn.close()

    c = _login(app)
    r = c.get("/api/marketing/atribucion-influencers")
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("ok") is True
    assert "kpis" in j and "influencers" in j

    # Debe encontrar 1 influencer con 2 pedidos y revenue = 100k+200k
    infs = j["influencers"]
    matching = [x for x in infs if x["discount_code"] == "ANIMUS_TEST10"]
    assert len(matching) == 1, f"Expected 1 influencer, got {infs}"
    m = matching[0]
    assert m["n_pedidos"] == 2
    assert m["revenue_total"] == 300000
    assert m["unidades"] == 3


def test_kanban_contenido_endpoint(app, db_clean):
    """Endpoint kanban devuelve 5 columnas con la estructura correcta
    aunque no haya contenido cargado."""
    c = _login(app)
    r = c.get("/api/marketing/contenido/kanban")
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("ok") is True
    assert "columnas" in j
    estados = [col["estado"] for col in j["columnas"]]
    assert estados == ["Brief", "Produccion", "Pendiente", "Publicado", "Performance"]


def test_kanban_legacy_estado_se_mapea(app, db_clean):
    """Contenido viejo con estado='Borrador' debe aparecer en columna 'Brief'."""
    import os
    import sqlite3
    db_path = os.environ["DB_PATH"]
    conn = sqlite3.connect(db_path)
    conn.execute("""INSERT INTO marketing_contenido
        (tipo, estado, caption) VALUES ('Post', 'Borrador', 'Test legacy')""")
    conn.execute("""INSERT INTO marketing_contenido
        (tipo, estado, caption) VALUES ('Reel', 'Programado', 'Test programado')""")
    conn.commit()
    conn.close()

    c = _login(app)
    r = c.get("/api/marketing/contenido/kanban")
    j = r.get_json()
    cols = {col["estado"]: col for col in j["columnas"]}
    # 'Borrador' legacy → Brief
    assert any("Test legacy" in (it.get("caption") or "") for it in cols["Brief"]["items"])
    # 'Programado' legacy → Pendiente
    assert any("Test programado" in (it.get("caption") or "") for it in cols["Pendiente"]["items"])


def test_feedback_loop_agente(app, db_clean):
    """Feedback se guarda y stats reflejan tasa de acierto."""
    import os
    import sqlite3
    db_path = os.environ["DB_PATH"]
    conn = sqlite3.connect(db_path)
    # Crear 2 ejecuciones de log
    conn.execute("""INSERT INTO marketing_agentes_log
        (agente, accion, resultado, ejecutado_por)
        VALUES ('estrategia','Ejecutado','{}','test')""")
    log1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("""INSERT INTO marketing_agentes_log
        (agente, accion, resultado, ejecutado_por)
        VALUES ('estrategia','Ejecutado','{}','test')""")
    log2 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    c = _login(app)
    # Marcar log1 como útil, log2 como ejecutado
    r1 = c.post("/api/marketing/agentes/feedback", headers=csrf_headers(),
                json={"log_id": log1, "feedback": "util"})
    assert r1.status_code == 200, r1.get_data(as_text=True)
    r2 = c.post("/api/marketing/agentes/feedback", headers=csrf_headers(),
                json={"log_id": log2, "feedback": "ejecutado"})
    assert r2.status_code == 200

    # Stats: 2 feedbacks, ambos contan como acierto → 100%
    r = c.get("/api/marketing/agentes/feedback/stats")
    j = r.get_json()
    assert j["ok"] is True
    stats = j["agentes"].get("estrategia") or j["agentes"].get("Estrategia") or {}
    assert stats.get("total") == 2
    assert stats.get("tasa_acierto_pct") == 100

    # Feedback inválido → 400
    r_bad = c.post("/api/marketing/agentes/feedback", headers=csrf_headers(),
                    json={"log_id": log1, "feedback": "lol"})
    assert r_bad.status_code == 400


def test_agente_estrategia_runs(app, db_clean):
    """El master agent estrategia no debe 500 con DB vacía.

    Sin ANTHROPIC_API_KEY el endpoint igual debe responder con el snapshot
    crudo (sin analisis_ia). El front renderiza un warning en ese caso.
    """
    c = _login(app)
    r = c.post("/api/marketing/agentes/estrategia",
               headers=csrf_headers(), json={})
    assert r.status_code == 200, f"unexpected: {r.status_code} | {r.get_data(as_text=True)[:300]}"
    j = r.get_json()
    assert "error" not in j, f"agente error: {j.get('error')}"
    assert j.get("agente") == "estrategia"
    # Debe traer el snapshot estructurado aunque la DB esté vacía
    assert "snapshot" in j
    assert "kpis" in j
    for key in ("top_shopify_30d", "skus_para_empujar", "skus_en_riesgo",
                "influencers_top", "produccion_proxima", "eventos_proximos",
                "campanas_activas"):
        assert key in j["snapshot"], f"falta {key} en snapshot"


def test_marketing_modals_outside_tab_panels(app, db_clean):
    """Cada div .modal-bg debe vivir FUERA de cualquier .tab-panel.

    Bug reportado: 'el modal Editar Influencer solo aparece cuando estoy
    en la sub-tab Histórico de inversión'. Causa: modal-historial,
    modal-influencer, etc. estaban dentro de tab-analytics. Cuando esa
    tab era display:none, todos los modales también — abrirlos no surtía
    efecto visible.
    """
    import html.parser
    c = _login(app)
    r = c.get("/marketing")
    html_doc = r.get_data(as_text=True)

    class Checker(html.parser.HTMLParser):
        def __init__(self):
            super().__init__()
            self.stack = []
            self.modals_in_tabs = []
        def handle_starttag(self, tag, attrs):
            if tag != "div":
                return
            d = dict(attrs)
            cls = d.get("class", "")
            mid = d.get("id", "")
            if "modal-bg" in cls:
                for (t, i, c) in self.stack:
                    if "tab-panel" in c:
                        self.modals_in_tabs.append((mid, i))
                        break
            self.stack.append((tag, mid, cls))
        def handle_endtag(self, tag):
            if tag == "div" and self.stack:
                self.stack.pop()

    ck = Checker()
    ck.feed(html_doc)
    assert not ck.modals_in_tabs, (
        f"Modales dentro de tab-panel (se ocultarán cuando la tab no esté "
        f"activa): {ck.modals_in_tabs}"
    )


def test_marketing_html_js_parses():
    """Compila el JS embebido en MARKETING_HTML con node.

    Si esto falla, TODO el <script> de la página se rompe y el panel queda
    inerte (sin clicks, sin tabs, sin loaders). Dispara este test antes de
    desplegar cambios al template.

    Skip si `node` no está disponible en el entorno de CI.
    """
    if not shutil.which("node"):
        pytest.skip("node no disponible — skip JS parse check")

    from api.templates_py.marketing_html import MARKETING_HTML

    # Extraer todos los <script>...</script> sin atributo src
    scripts = re.findall(
        r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
        MARKETING_HTML, re.DOTALL,
    )
    assert scripts, "no <script> blocks found in MARKETING_HTML"

    full_js = "\n;\n".join(scripts)
    # Wrap en función async para tolerar `await` top-level y declaraciones
    wrapped = f"(async function() {{\n{full_js}\n}})();"

    # Escribir a archivo temp — Windows limita longitud del cmdline
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False, encoding="utf-8"
    ) as f:
        f.write(wrapped)
        tmp = f.name

    try:
        proc = subprocess.run(
            ["node", "--check", tmp],
            capture_output=True, text=True, timeout=20,
        )
        assert proc.returncode == 0, (
            f"JS de marketing_html.py no parsea — esto rompe TODA la página:\n"
            f"{proc.stderr[-1500:]}"
        )
    finally:
        import os as _os
        try: _os.unlink(tmp)
        except OSError: pass
