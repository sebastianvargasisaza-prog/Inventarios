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


def test_recepcion_lote_info_endpoint(admin_client):
    """Lookup de lote existente en recepción (para avisar 'sumás al lote existente')."""
    r = admin_client.get("/api/recepcion/lote-info?codigo=MP00123&lote=NO-EXISTE-XYZ")
    assert r.status_code == 200, r.status_code
    assert r.get_json().get("existe") is False


def test_precios_sospechosos_page(admin_client):
    """La página de precios sospechosos renderiza (lista MP con precio fuera de rango)."""
    r = admin_client.get("/admin/precios-sospechosos")
    assert r.status_code == 200, r.status_code
    body = r.data.decode("utf-8", "replace")
    assert "Precios sospechosos" in body
    assert "fixPrecio" in body


def test_envases_recatalogo_preview(admin_client):
    """Preview read-only del re-catálogo de envases (mapeo nuevo→viejo)."""
    r = admin_client.get("/admin/envases-recatalogo")
    assert r.status_code == 200, r.status_code
    body = r.data.decode("utf-8", "replace")
    assert "Re-cat" in body
    assert "MEE-ENV-001" in body


def test_envases_10ml_sueros(admin_client):
    """Herramienta crear envase 10ml (Niacinamida/Hialurónico/TRX) + mapeo, idempotente (Sebastián 9-jul)."""
    r = admin_client.get("/admin/envases-10ml-sueros")
    assert r.status_code == 200 and b"Envases 10ml" in r.data
    r2 = admin_client.post("/api/admin/crear-envases-10ml-sueros", json={})
    assert r2.status_code == 200 and r2.get_json()["ok"]
    # 2a corrida: no re-crea (idempotente)
    r3 = admin_client.post("/api/admin/crear-envases-10ml-sueros", json={})
    assert r3.get_json()["creados"] == 0


def test_mee_codigo_auto_consecutivo(admin_client):
    """Código MEE automático: el sistema asigna MEE-{PREF}-### consecutivo (Sebastián 9-jul)."""
    r = admin_client.get("/api/mee/siguiente-codigo?tipo=ENV")
    assert r.status_code == 200, r.status_code
    j = r.get_json()
    assert j["ok"] and j["codigo"].startswith("MEE-ENV-") and j["categoria"] == "Envase"
    r2 = admin_client.post("/api/mee/crear-auto", json={"tipo": "ENV", "descripcion": "FRASCO PRUEBA", "volumen_ml": 30})
    assert r2.status_code == 200 and r2.get_json()["ok"]
    c1 = r2.get_json()["codigo"]
    r3 = admin_client.post("/api/mee/crear-auto", json={"tipo": "ENV", "descripcion": "FRASCO PRUEBA 2"})
    assert r3.get_json()["codigo"] != c1  # consecutivo, no repite
    # tipo inválido y sin descripción → 400
    assert admin_client.post("/api/mee/crear-auto", json={"tipo": "ZZ", "descripcion": "x"}).status_code == 400
    assert admin_client.post("/api/mee/crear-auto", json={"tipo": "ENV", "descripcion": ""}).status_code == 400


def test_envases_recatalogo_y_productos_envases(admin_client):
    r1 = admin_client.get("/admin/envases-recatalogo")
    assert r1.status_code == 200 and b"Re-cat" in r1.data
    assert b"MEE-ENV-001" in r1.data and b"Aplicar" in r1.data
    r2 = admin_client.get("/admin/productos-envases")
    assert r2.status_code == 200, r2.status_code
    assert b"producto" in r2.data.lower() and b"setEnv" in r2.data
    # vista basada en productos activos (fórmulas) → crea el mapeo aunque no haya presentación
    assert b"crearEnv" in r2.data and b"por asignar" in r2.data
