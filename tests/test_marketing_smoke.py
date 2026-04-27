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
