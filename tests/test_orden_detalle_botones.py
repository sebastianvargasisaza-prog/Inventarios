"""Botones del detalle de orden /planta/orden/<id> · paridad MyBatch.

Valida que los dos botones que el CEO pidió revisar (8-jun) apunten a destinos
vivos y no a rutas rotas:
  · 📖 Instrucción de Manufactura → togglePasos() sobre #pasos-sec (in-page),
    poblado por load() desde vista-completa.
  · 📜 Timeline Batch Record → /brd/timeline/<id> (página aparte, 3 nodos).

Ambos se alimentan de /api/brd/ebr/<id>/vista-completa, así que también se
verifica que ese endpoint traiga el header que las dos vistas consumen.
"""


def _crear_ebr(app, lote="LOTE-BTN-1"):
    from database import get_db
    with app.app_context():
        conn = get_db()
        cur = conn.execute(
            """INSERT INTO mbr_templates (producto_nombre, version, estado,
                 lote_size_g, creado_por) VALUES (?, 1, 'aprobado',
                 1000, 'sebastian')""", (f"PROD-BTN-{lote}",))
        mbr_id = cur.lastrowid
        cur = conn.execute(
            """INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote,
                 estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, fase)
               VALUES (?,1,?,'iniciado','sebastian','2026-06-06 10:00:00',1000,'fabricacion')""",
            (mbr_id, lote))
        ebr_id = cur.lastrowid
        conn.commit()
        return ebr_id


def test_detalle_orden_carga_y_cablea_botones(admin_client, app):
    ebr = _crear_ebr(app, "DET")
    r = admin_client.get(f"/planta/orden/{ebr}")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    # El botón Instrucción de Manufactura y su toggle deben existir.
    assert "Instrucción de Manufactura" in html
    assert "togglePasos()" in html
    assert 'id="pasos-sec"' in html
    # El botón Timeline debe apuntar a la ruta real.
    assert f"/brd/timeline/{ebr}" in html or "/brd/timeline/'+EBR_ID" in html


def test_timeline_batch_record_responde(admin_client, app):
    ebr = _crear_ebr(app, "TL")
    r = admin_client.get(f"/brd/timeline/{ebr}")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    # Los 3 nodos MyBatch del timeline deben estar maquetados.
    assert "Instrucciones de Fabricación" in html
    assert 'id="timeline"' in html


def test_vista_completa_trae_header_para_ambas_vistas(admin_client, app):
    ebr = _crear_ebr(app, "VC")
    d = admin_client.get(f"/api/brd/ebr/{ebr}/vista-completa").get_json()
    assert d and "header" in d, f"vista-completa sin header: {d}"
    h = d["header"]
    # Campos que Timeline e Instrucción de Manufactura leen del header.
    for campo in ("lote_codigo", "estado", "fase"):
        assert campo in h, f"header sin '{campo}': {list(h.keys())}"
