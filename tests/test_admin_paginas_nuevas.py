"""Sebastián 7-jul: las páginas admin nuevas (logo Espagiria, purgar GCal, producciones sin fórmula)
renderizan 200 (regresión del NameError get_db que no estaba en scope de módulo en admin.py)."""


def test_pagina_logo_espagiria_200(admin_client):
    r = admin_client.get("/admin/logo-espagiria")
    assert r.status_code == 200, r.status_code
    assert b"Logo de Espagiria" in r.data


def test_pagina_purgar_gcal_200(admin_client):
    r = admin_client.get("/admin/purgar-gcal")
    assert r.status_code == 200, r.status_code
    assert b"Google Calendar" in r.data


def test_pagina_producciones_sin_formula_200(admin_client):
    r = admin_client.get("/admin/producciones-sin-formula")
    assert r.status_code == 200, r.status_code
    assert b"sin f" in r.data  # "sin fórmula"


def test_purgar_gcal_post_ok(admin_client):
    r = admin_client.post("/api/admin/purgar-gcal", json={})
    assert r.status_code == 200, r.status_code
    assert r.get_json().get("ok") is True


def test_equipos_sync_preview(admin_client):
    """La vista previa de sync de equipos carga el maestro 2026 y renderiza el delta."""
    r = admin_client.get("/admin/equipos-sync")
    assert r.status_code == 200, r.status_code
    body = r.data.decode("utf-8", "replace")
    assert "Maestro 2026" in body
    assert "Aplicar sync" in body


def test_rotulo_recepcion_mp_premium(admin_client):
    """Rótulo de recepción de MP: renderiza premium (logo + tarjeta .sheet + 100×100), sin 500."""
    r = admin_client.get("/rotulo-recepcion/MP00107/LOTE-TEST/3000")
    assert r.status_code == 200, r.status_code
    body = r.data.decode("utf-8", "replace")
    assert "ESPAGIRIA Laboratorio SAS" in body
    assert "espagiria" in body.lower()  # logo src
    assert 'class="sheet"' in body
    assert "100mm 100mm" in body


def test_rotulo_recepcion_mee_premium(admin_client):
    """Rótulo de recepción de material de envase (MEE): premium, sin 500."""
    r = admin_client.get("/rotulo-recepcion-mee/MEE0001/100")
    assert r.status_code == 200, r.status_code
    body = r.data.decode("utf-8", "replace")
    assert "ESPAGIRIA Laboratorio SAS" in body
    assert 'class="sheet"' in body
    assert "100mm 100mm" in body


def test_rotulo_limpieza_render_logo_sin_animus(admin_client):
    """El rótulo de limpieza F02 renderiza, trae el logo Espagiria y NO dice ÁNIMUS Lab (Planta = Espagiria)."""
    r = admin_client.get("/planta/rotulos-limpieza")
    assert r.status_code == 200, r.status_code
    body = r.data.decode("utf-8", "replace")
    assert "espagiria" in body.lower()  # logo src o marca
    assert "ÁNIMUS Lab" not in body
    assert "100mm 100mm" in body or "size:100mm 100mm" in body  # @page 100×100 default


def test_calidad_modulo_tiene_modal_ccreview_premium(admin_client):
    """El módulo Calidad (Laura) ahora trae el modal premium de Revisión CC (COC-PRO-001) para liberar MP."""
    r = admin_client.get("/calidad")
    assert r.status_code == 200, r.status_code
    body = r.data.decode("utf-8", "replace")
    assert "ccr-modal" in body
    assert "abrirCCReview" in body
    assert "Revisar CC" in body
    assert "Firmar y registrar" in body


def test_planta_dashboard_tiene_modal_ccreview_premium(admin_client):
    """La pantalla de Planta (CEO/Hernando/Miguel) también trae el modal premium de Revisión CC."""
    r = admin_client.get("/inventarios")
    assert r.status_code == 200, r.status_code
    body = r.data.decode("utf-8", "replace")
    assert "ccr-modal" in body
    assert "function abrirCCReview" in body
