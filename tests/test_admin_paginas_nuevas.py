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


def test_mee_kit_partes(admin_client):
    """Kit de partes por envase: set/get + dedup + no auto-parte (Sebastián 9-jul)."""
    env = admin_client.post("/api/mee/crear-auto", json={"tipo": "ENV", "descripcion": "FRASCO KIT X"}).get_json()["codigo"]
    got = admin_client.post("/api/mee/crear-auto", json={"tipo": "GOT", "descripcion": "GOTERO KIT X"}).get_json()["codigo"]
    r = admin_client.post(f"/api/mee/{env}/partes", json={"partes": [{"codigo": got, "cantidad": 1}, {"codigo": got, "cantidad": 9}, {"codigo": env, "cantidad": 1}]})
    assert r.status_code == 200 and r.get_json()["n_partes"] == 1  # dedup + sin auto-parte
    g = admin_client.get(f"/api/mee/partes?codigo={env}").get_json()["partes"]
    assert len(g) == 1 and g[0]["codigo"] == got
    # el modal del kit se sirve en la pantalla de Planta (la función meeKit va en el JS extraído /planta-app.js)
    pg = admin_client.get("/inventarios").get_data(as_text=True)
    assert 'id="mee-kit-modal"' in pg


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


def test_renombrar_codigo_mp(admin_client):
    """Renombrar el código de una MP (normalizar EOS↔MyBatch · Sebastián 9-jul):
    preview + apply re-llavan maestro + fórmulas + stock, conservando todo."""
    # página
    assert admin_client.get("/admin/renombrar-codigo-mp").status_code == 200
    # preview de MP00199 (DIMETHICONE) → MP00293 (libre)
    pv = admin_client.get("/api/admin/renombrar-mp-preview?viejo=MP00199&nuevo=MP00293").get_json()
    assert pv["ok"] and pv["viejo"] == "MP00199" and pv["nuevo"] == "MP00293"
    assert "DIMETHICONE" in (pv["nombre_inci"] or "").upper()
    tablas = {r["tabla"] for r in pv["refs"]}
    assert "formula_items" in tablas  # 6 fórmulas la usan
    # target ocupado → 200 con fusion:true (ofrece fusionar); código inexistente → 404
    ocup = admin_client.get("/api/admin/renombrar-mp-preview?viejo=MP00199&nuevo=MP00072").get_json()
    assert ocup["ok"] and ocup["fusion"] is True
    assert admin_client.get("/api/admin/renombrar-mp-preview?viejo=MP99999&nuevo=MP00293").status_code == 404
    # aplicar
    r = admin_client.post("/api/admin/renombrar-mp-apply", json={"viejo": "MP00199", "nuevo": "MP00293"})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert d["ok"] and d["nucleo"]["maestro_mps.codigo_mp"] == 1
    assert d["nucleo"]["formula_items.material_id"] == 6
    # verificar en la BD: MP00199 ya no existe, MP00293 sí, fórmulas migradas
    pv2 = admin_client.get("/api/admin/renombrar-mp-preview?viejo=MP00293&nuevo=MP00199").get_json()
    assert pv2["ok"] and "DIMETHICONE" in (pv2["nombre_inci"] or "").upper()
    assert admin_client.get("/api/admin/renombrar-mp-preview?viejo=MP00199&nuevo=MP00293").status_code == 404


def test_mp_diag(admin_client):
    """Diagnóstico 'por qué no sale en Bodega': existe/tipo/activo/stock usable vs retenido."""
    d = admin_client.get("/api/admin/mp-diag?codigo=MPNOEXISTE").get_json()
    assert d["ok"] and d["existe"] is False and "NO existe" in d["razon"]
    d2 = admin_client.get("/api/admin/mp-diag?codigo=MP00062").get_json()
    assert d2["ok"] and d2["existe"] and d2["tipo_material"] == "MP"
    assert "stock_usable_g" in d2 and "aparece_en_bodega_default" in d2 and d2["razon"]
    assert "mov_total" in d2 and "historial" in d2
    # el historial registra el stock exacto al renombrar (dato duro para 'la anterior tenía stock?')
    from api.index import app
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, activo) VALUES ('MPHDIAG1','TEST H',1)")
        c.execute("INSERT INTO movimientos (material_id, tipo, cantidad, lote) VALUES ('MPHDIAG1','Entrada',777,'LHD1')")
        conn.commit()
    admin_client.post("/api/admin/renombrar-mp-apply", json={"viejo": "MPHDIAG1", "nuevo": "MPHDIAG2"})
    d3 = admin_client.get("/api/admin/mp-diag?codigo=MPHDIAG2").get_json()
    assert d3["mov_total"] == 1 and d3["stock_usable_g"] == 777
    assert any(h["accion"] == "RENOMBRAR_CODIGO_MP" and h["despues"].get("stock_g") == 777 for h in d3["historial"])


def test_fusionar_codigo_mp(admin_client):
    """Fusión: cuando el destino YA existe (ej. PARFUM MPFRCN01 → MP00062 pistacho),
    mueve stock/refs al destino y desactiva el origen (Sebastián 9-jul)."""
    from api.index import app
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, activo) VALUES ('MPZZDST','PARFUM PISTACHO',1)")
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, activo) VALUES ('MPZZSRC','PARFUM PISTACHO',1)")
        c.execute("INSERT INTO movimientos (material_id, tipo, cantidad, lote) VALUES ('MPZZSRC','Entrada',500,'LOTE-FUS-99')")
        # ref AUXILIAR real → debe moverse limpio (sin el bug de savepoint que rompía todas)
        c.execute("INSERT INTO especificaciones_mp (codigo_mp, parametro) VALUES ('MPZZSRC','pH')")
        conn.commit()
    # preview detecta fusión (destino existe) y muestra AMBOS nombres
    pv = admin_client.get("/api/admin/renombrar-mp-preview?viejo=MPZZSRC&nuevo=MPZZDST").get_json()
    assert pv["ok"] and pv["fusion"] is True
    assert "PARFUM" in (pv["destino_nombre_inci"] or "").upper()
    assert pv["stock_g"] == 500
    # aplicar SIN modo=fusion sobre destino existente → 409 (obliga a confirmar fusión)
    assert admin_client.post("/api/admin/renombrar-mp-apply",
                             json={"viejo": "MPZZSRC", "nuevo": "MPZZDST"}).status_code == 409
    # fusión real
    r = admin_client.post("/api/admin/renombrar-mp-apply",
                          json={"viejo": "MPZZSRC", "nuevo": "MPZZDST", "modo": "fusion"})
    d = r.get_json()
    assert r.status_code == 200 and d["ok"] and d["fusion"]
    assert d["nucleo"]["movimientos"] == 1
    assert d["stock_destino_final_g"] == 500  # el stock se movió al destino
    # la ref auxiliar se movió LIMPIO (bug savepoint) · sin falsos errores
    assert d["auxiliares"].get("especificaciones_mp.codigo_mp") == 1
    assert not any(e["tabla"] == "especificaciones_mp" for e in (d.get("errores") or []))
    # el origen quedó desactivado (ya no es preview-able como activo · sigue existiendo por GMP)
    with app.app_context():
        from database import get_db
        c = get_db().cursor()
        act = c.execute("SELECT COALESCE(activo,1) FROM maestro_mps WHERE codigo_mp='MPZZSRC'").fetchone()[0]
        assert int(act) == 0
        mov = c.execute("SELECT material_id FROM movimientos WHERE lote='LOTE-FUS-99'").fetchone()[0]
        assert mov == "MPZZDST"


def test_envases_recatalogo_y_productos_envases(admin_client):
    r1 = admin_client.get("/admin/envases-recatalogo")
    assert r1.status_code == 200 and b"Re-cat" in r1.data
    assert b"MEE-ENV-001" in r1.data and b"Aplicar" in r1.data
    r2 = admin_client.get("/admin/productos-envases")
    assert r2.status_code == 200, r2.status_code
    assert b"producto" in r2.data.lower() and b"setEnv" in r2.data
    # vista basada en productos activos (fórmulas) → crea el mapeo aunque no haya presentación
    assert b"crearEnv" in r2.data and b"por asignar" in r2.data


def test_mp_reactivar(admin_client):
    """Reactivar MP inactiva (MP00293 quedó activo=0): página + endpoint, auditado."""
    assert admin_client.get("/admin/mp-diag").status_code == 200
    from api.index import app
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, activo) VALUES ('MPZZINACT','DIMETHICONE X',0)")
        conn.commit()
    dg = admin_client.get("/api/admin/mp-diag?codigo=MPZZINACT").get_json()
    assert dg["existe"] and dg["activo"] == 0 and "INACTIVA" in dg["razon"]
    r = admin_client.post("/api/admin/mp-reactivar", json={"codigo": "MPZZINACT"})
    assert r.status_code == 200 and r.get_json()["activo"] == 1
    dg2 = admin_client.get("/api/admin/mp-diag?codigo=MPZZINACT").get_json()
    assert dg2["activo"] == 1
    assert admin_client.post("/api/admin/mp-reactivar", json={"codigo": "MPNOEXISTE"}).status_code == 404


def test_descuento_retroactivo(admin_client):
    """Descuento retroactivo (producción no registrada): revisión clasifica bien +
    aplica por FEFO solo los OK, reduce stock, idempotente (Sebastián 9-jul)."""
    assert admin_client.get("/admin/descuento-retroactivo").status_code == 200
    from api.index import app
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo,tipo_material) VALUES ('MPDRETO1','UREA DR',1,'MP')")
        c.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPDRETO1','UREA DR',10000,'Entrada','2026-01-01','LDR1','VIGENTE')")
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo,tipo_material) VALUES ('MPDRETO2','CUAR DR',1,'MP')")
        c.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPDRETO2','CUAR DR',5000,'Entrada','2026-01-01','LDRC','CUARENTENA')")
        conn.commit()
    filas = [
        {"cod": "MPDRETO1", "desc": "UREA", "lote": "_00LDR1", "cant": 7000, "prod": "PT-A", "bulk": "B1"},
        {"cod": "MPDRETO2", "desc": "CUAR", "lote": "LDRC", "cant": 3000, "prod": "PT-A", "bulk": "B1"},
        {"cod": "MPNOEXISTEZ", "desc": "?", "lote": "z", "cant": 5, "prod": "PT-A", "bulk": "B1"},
        {"cod": "MPDRETO1", "desc": "UREA", "lote": "x", "cant": 999999, "prod": "PT-A", "bulk": "B2"},
    ]
    d = admin_client.post("/api/admin/descuento-retro/preview", json={"filas": filas}).get_json()
    assert d["ok"]
    st = {r["cod"] + "/" + str(int(r["cant"])): r["status"] for r in d["rows"]}
    assert st["MPDRETO1/7000"] == "OK"
    assert st["MPDRETO2/3000"] == "CUARENTENA"
    assert st["MPNOEXISTEZ/5"] == "MP_NO_EXISTE"
    assert st["MPDRETO1/999999"] == "INSUF"
    oks = [r for r in d["rows"] if r["status"] == "OK"]
    da = admin_client.post("/api/admin/descuento-retro/apply", json={"filas": oks}).get_json()
    assert da["ok"] and da["n_aplicadas"] == 1 and abs(da["total_descontado_g"] - 7000) < 1
    dg = admin_client.get("/api/admin/mp-diag?codigo=MPDRETO1").get_json()
    assert abs(dg["stock_usable_g"] - 3000) < 1
    # idempotente: re-aplicar no vuelve a descontar
    assert admin_client.post("/api/admin/descuento-retro/apply", json={"filas": oks}).get_json()["n_aplicadas"] == 0


def test_descuento_retro_page_js_node_check(admin_client):
    """La página de descuento retroactivo: cada <script> del valor RENDERIZADO pasa node --check
    (M65: validar el valor evaluado, no el fuente · el bug \t/\n rompía todo el script)."""
    import re, subprocess, os, shutil
    if not shutil.which("node"):
        return
    html = admin_client.get("/admin/descuento-retroactivo").get_data(as_text=True)
    for fn in ("function revisar", "function copiarRev", "function aplicar", "function pinta"):
        assert fn in html, fn
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    assert scripts
    for i, s in enumerate(scripts):
        p = "_nctest_%d.js" % i
        open(p, "w", encoding="utf-8").write(s)
        try:
            r = subprocess.run(["node", "--check", p], capture_output=True, text=True)
            assert r.returncode == 0, "script %d: %s" % (i, r.stderr[:300])
        finally:
            os.remove(p)


def test_retro_ya_aplicada_y_fusion_reactiva(admin_client):
    """Revisión marca YA_APLICADA lo ya descontado (no cuenta como a-revisar) + la fusión
    reactiva un destino inactivo (Sebastián 9-jul · consumo retroactivo)."""
    from api.index import app
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo,tipo_material) VALUES ('MPYAR1','UREA YA',1,'MP')")
        c.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPYAR1','UREA YA',10000,'Entrada','2026-01-01','LYAR','VIGENTE')")
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo,tipo_material) VALUES ('MPLEGR1','MEL LEG',1,'MP')")
        c.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPLEGR1','MEL',400,'Entrada','2026-01-01','LLEGR','VIGENTE')")
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo,tipo_material) VALUES ('MPDSTR9','MEL MB',0,'MP')")
        conn.commit()
    filas = [{"cod": "MPYAR1", "desc": "UREA", "lote": "LYAR", "cant": 7000, "prod": "PT-Z", "bulk": "BZR"}]
    d = admin_client.post("/api/admin/descuento-retro/preview", json={"filas": filas}).get_json()
    assert d["rows"][0]["status"] == "OK"
    admin_client.post("/api/admin/descuento-retro/apply", json={"filas": [r for r in d["rows"] if r["status"] == "OK"]})
    d2 = admin_client.post("/api/admin/descuento-retro/preview", json={"filas": filas}).get_json()
    assert d2["rows"][0]["status"] == "YA_APLICADA" and d2["resumen"]["revisar_g"] == 0
    ap = admin_client.post("/api/admin/normalizar-lote/apply", json={"texto": "MPLEGR1 -> MPDSTR9"}).get_json()
    assert ap["ok"] and ap["hechos"][0]["modo"] == "fusion"
    dg = admin_client.get("/api/admin/mp-diag?codigo=MPDSTR9").get_json()
    assert dg["activo"] == 1 and abs(dg["stock_usable_g"] - 400) < 1


def test_retro_marcador_incluye_lote(admin_client):
    """[audit 9-jul] 2 consumos del MISMO bulk/cod/cant pero DISTINTO lote NO se saltan entre sí
    (el marcador incluye el lote) → se descuentan AMBOS (antes: sub-descuento silencioso)."""
    from api.index import app
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo,tipo_material) VALUES ('MPMK1','MK',1,'MP')")
        c.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPMK1','MK',5000,'Entrada','2026-01-01','LMKA','VIGENTE')")
        c.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPMK1','MK',5000,'Entrada','2026-01-01','LMKB','VIGENTE')")
        conn.commit()
    filas = [
        {"cod": "MPMK1", "lote": "LMKA", "cant": 500, "prod": "PT-X", "bulk": "BMK"},
        {"cod": "MPMK1", "lote": "LMKB", "cant": 500, "prod": "PT-X", "bulk": "BMK"},
    ]
    d = admin_client.post("/api/admin/descuento-retro/preview", json={"filas": filas}).get_json()
    oks = [r for r in d["rows"] if r["status"] == "OK"]
    assert len(oks) == 2
    da = admin_client.post("/api/admin/descuento-retro/apply", json={"filas": oks}).get_json()
    assert da["n_aplicadas"] == 2 and abs(da["total_descontado_g"] - 1000) < 1  # AMBOS, no 1


def test_liberar_cuarentena_seleccion_vacia_no_libera(admin_client):
    """[audit 9-jul] seleccion=[] (lista vacía) libera NADA, no TODA la cuarentena."""
    from api.index import app
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo,tipo_material) VALUES ('MPSV1','SV',1,'MP')")
        c.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) VALUES ('MPSV1','SV',900,'Entrada','2026-01-01','LSV','CUARENTENA')")
        conn.commit()
    r = admin_client.post("/api/admin/liberar-cuarentena-bloque", json={"seleccion": []})
    assert r.status_code == 200 and r.get_json()["liberados"] == 0
    with app.app_context():
        from database import get_db
        c = get_db().cursor()
        assert c.execute("SELECT estado_lote FROM movimientos WHERE lote='LSV'").fetchone()[0] == "CUARENTENA"
