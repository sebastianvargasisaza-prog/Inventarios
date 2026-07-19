"""Laura 18-jul · Recepción de MP en 3 etapas: F01 (recepción técnica/documental) + F02 (certificado de
análisis). El F02 'aprobado' + firma del jefe LIBERA el lote (CUARENTENA→VIGENTE)."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="laura"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD}, headers=csrf_headers(),
               follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _lote_cuarentena(cod="MP-RCQ1", lote="LOTECQ1"):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        conn.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, tipo_material, activo) "
                     "VALUES (?, 'MP Recep Cal', 'MP', 1)", (cod,))
        conn.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, lote, estado_lote, fecha) "
                     "VALUES (?, 'MP Recep Cal', 4000, 'Entrada', ?, 'CUARENTENA', date('now'))", (cod, lote))
        conn.commit()
        return conn.execute("SELECT id FROM movimientos WHERE lote=?", (lote,)).fetchone()[0]
    finally:
        conn.close()


def _estado_lote(lote):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        return conn.execute("SELECT estado_lote FROM movimientos WHERE lote=?", (lote,)).fetchone()[0]
    finally:
        conn.close()


def test_pipeline_muestra_lote_en_cuarentena(app, db_clean):
    mid = _lote_cuarentena("MP-RCQ0", "LOTECQ0")
    c = _login(app)
    d = c.get("/api/calidad/recepcion-pipeline").get_json()
    movs = [l["mov_id"] for l in d.get("lotes", [])]
    assert mid in movs, "el lote en cuarentena debe aparecer en el pipeline"


def test_f01_guarda_y_prefill(app, db_clean):
    mid = _lote_cuarentena("MP-RCQ2", "LOTECQ2")
    c = _login(app)
    # prefill trae datos del movimiento
    g = c.get("/api/calidad/recepcion-tecnica?mov_id=%d" % mid).get_json()
    assert g["f01"] is None and g["prefill"]["lote"] == "LOTECQ2"
    r = c.post("/api/calidad/recepcion-tecnica", json={
        "mov_id": mid, "tipo_insumo": "materia_prima", "crit_rotulado": "cumple", "crit_coa": "cumple",
        "resultado": "conforme", "realiza_por": "Yuliel"}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    g2 = c.get("/api/calidad/recepcion-tecnica?mov_id=%d" % mid).get_json()
    assert g2["f01"]["resultado"] == "conforme"


def _firmar(client, mov_id, meaning="libera", record_table="movimientos"):
    """E-firma Part 11: challenge (password) → sign → signature_id."""
    rc = client.post("/api/sign/challenge", json={"password": TEST_PASSWORD, "totp_token": ""},
                     headers=csrf_headers())
    assert rc.status_code == 200, rc.data[:200]
    tok = rc.get_json()["token"]
    rs = client.post("/api/sign", json={"record_table": record_table, "record_id": str(mov_id),
                                        "meaning": meaning, "challenge_token": tok}, headers=csrf_headers())
    assert rs.status_code in (200, 201), rs.data[:200]
    return rs.get_json()["signature_id"]


def test_f02_aprobado_libera_lote(app, db_clean):
    mid = _lote_cuarentena("MP-RCQ3", "LOTECQ3")
    c = _login(app)
    # aprobar sin firma electrónica → 400 (Part 11)
    r0 = c.post("/api/calidad/certificado-analisis", json={
        "mov_id": mid, "resultado": "aprobado", "aprobo_por": "Laura Gonzalez"}, headers=csrf_headers())
    assert r0.status_code == 400, r0.data[:200]
    assert r0.get_json().get("requiere_firma") is True
    # aprobar CON e-firma → libera
    sig = _firmar(c, mid, "libera")
    r = c.post("/api/calidad/certificado-analisis", json={
        "mov_id": mid, "resultado": "aprobado", "aspecto_result": "polvo blanco", "aspecto_cumple": "si",
        "responsable_analisis": "Yuliel", "aprobo_por": "Laura Gonzalez", "signature_id": sig},
        headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert r.get_json().get("liberado") == 1
    assert _estado_lote("LOTECQ3") == "VIGENTE", "el lote aprobado debe quedar VIGENTE"


def test_f02_no_aprobado_rechaza(app, db_clean):
    mid = _lote_cuarentena("MP-RCQ4", "LOTECQ4")
    c = _login(app)
    sig = _firmar(c, mid, "rechaza")
    r = c.post("/api/calidad/certificado-analisis", json={
        "mov_id": mid, "resultado": "no_aprobado", "aprobo_por": "Laura", "signature_id": sig},
        headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert _estado_lote("LOTECQ4") == "RECHAZADO"


def test_f02_no_aprobado_crea_no_conformidad(app, db_clean):
    mid = _lote_cuarentena("MP-RCQ6", "LOTECQ6")
    c = _login(app)
    sig = _firmar(c, mid, "rechaza")
    r = c.post("/api/calidad/certificado-analisis", json={
        "mov_id": mid, "resultado": "no_aprobado", "aprobo_por": "Laura", "signature_id": sig,
        "observaciones_generales": "pH fuera de especificación"}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    nc_id = r.get_json().get("nc_id")
    assert nc_id, "el rechazo debe crear una No Conformidad"
    # la NC aparece en el listado, ligada al lote
    ncs = c.get("/api/calidad/no-conformidades").get_json()
    mine = [n for n in ncs if n["id"] == nc_id]
    assert mine and mine[0]["lote"] == "LOTECQ6" and mine[0]["estado"] == "Abierta"


# ── ENVASES (MEE) en el pipeline ──
def _lote_mee_cuarentena(cod="MEE-RCQ1", lote="MEELOTE1"):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        conn.execute("INSERT OR IGNORE INTO maestro_mee (codigo, descripcion, categoria, estado, unidad) "
                     "VALUES (?, 'Frasco Recep Cal', 'Frasco', 'Activo', 'und')", (cod,))
        conn.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, unidad, lote_ref, estado, fecha) "
                     "VALUES (?, 'Entrada', 500, 'und', ?, 'CUARENTENA', datetime('now'))", (cod, lote))
        conn.commit()
        return conn.execute("SELECT id FROM movimientos_mee WHERE lote_ref=?", (lote,)).fetchone()[0]
    finally:
        conn.close()


def _estado_mee(mid):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        return conn.execute("SELECT estado FROM movimientos_mee WHERE id=?", (mid,)).fetchone()[0]
    finally:
        conn.close()


def test_pipeline_muestra_envase_en_cuarentena(app, db_clean):
    mid = _lote_mee_cuarentena("MEE-RCQ0", "MEELOTE0")
    c = _login(app)
    d = c.get("/api/calidad/recepcion-pipeline").get_json()
    mee = [l for l in d.get("lotes", []) if l.get("tipo") == "MEE" and l["mov_id"] == mid]
    assert mee, "el envase en cuarentena debe aparecer en el pipeline con tipo=MEE"


def test_f01_envase_conforme_libera(app, db_clean):
    mid = _lote_mee_cuarentena("MEE-RCQ2", "MEELOTE2")
    c = _login(app)
    # prefill MEE trae datos del movimiento_mee
    g = c.get("/api/calidad/recepcion-tecnica?mov_id=%d&origen=MEE" % mid).get_json()
    assert g["origen"] == "MEE" and g["prefill"]["lote"] == "MEELOTE2"
    # conforme sin firma del jefe → 400
    r0 = c.post("/api/calidad/recepcion-tecnica", json={
        "mov_id": mid, "origen": "MEE", "tipo_insumo": "envase", "resultado": "conforme"}, headers=csrf_headers())
    assert r0.status_code == 400, r0.data[:200]
    # conforme sin e-firma Part 11 → 400 (requiere firma)
    r1 = c.post("/api/calidad/recepcion-tecnica", json={
        "mov_id": mid, "origen": "MEE", "tipo_insumo": "envase",
        "resultado": "conforme", "aprueba_por": "Laura"}, headers=csrf_headers())
    assert r1.status_code == 400 and r1.get_json().get("requiere_firma") is True
    # conforme CON firma electrónica → libera el envase
    sig = _firmar(c, mid, "libera", "movimientos_mee")
    r = c.post("/api/calidad/recepcion-tecnica", json={
        "mov_id": mid, "origen": "MEE", "tipo_insumo": "envase", "crit_empaque": "cumple",
        "resultado": "conforme", "realiza_por": "Yuliel", "aprueba_por": "Laura", "signature_id": sig}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert r.get_json().get("liberado") == 1
    assert _estado_mee(mid) == "VIGENTE", "el envase conforme debe quedar VIGENTE"


def test_f01_f02_imprimibles(app, db_clean):
    mid = _lote_cuarentena("MP-RCQ5", "LOTECQ5")
    c = _login(app)
    c.post("/api/calidad/recepcion-tecnica", json={
        "mov_id": mid, "tipo_insumo": "materia_prima", "crit_rotulado": "cumple",
        "resultado": "conforme", "realiza_por": "Yuliel"}, headers=csrf_headers())
    sig = _firmar(c, mid, "libera")
    c.post("/api/calidad/certificado-analisis", json={
        "mov_id": mid, "resultado": "aprobado", "aspecto_result": "polvo", "aspecto_cumple": "si",
        "responsable_analisis": "Yuliel", "aprobo_por": "Laura", "signature_id": sig}, headers=csrf_headers())
    f01 = c.get("/api/calidad/recepcion-tecnica/imprimible?mov_id=%d" % mid)
    assert f01.status_code == 200 and b"COC-PRO-002-F01" in f01.data
    f02 = c.get("/api/calidad/certificado-analisis/imprimible?mov_id=%d" % mid)
    assert f02.status_code == 200 and b"COC-PRO-002-F02" in f02.data


def test_f02_verificacion_final_aplica_correcciones_y_ubicacion(app, db_clean):
    """Verificación final (Laura · 19-jul): al aprobar el F02, INCI/tipo → maestro; cantidad/lote/
    vencimiento → kardex; y la ubicación (estantería/posición) queda en el movimiento al liberar."""
    mid = _lote_cuarentena("MP-RCQF", "LOTEQF1")
    c = _login(app)
    # el GET prefill trae los datos actuales de la MP (INCI/tipo/ubicación)
    g = c.get("/api/calidad/certificado-analisis?mov_id=%d" % mid).get_json()
    assert "nombre_inci" in g["prefill"] and g["prefill"]["tipo_material"] == "MP"
    sig = _firmar(c, mid, "libera")
    r = c.post("/api/calidad/certificado-analisis", json={
        "mov_id": mid, "resultado": "aprobado", "aprobo_por": "Laura", "signature_id": sig,
        "inci_corregido": "PROPYLENE GLYCOL", "tipo_material": "MP", "cantidad_final": "3950",
        "fecha_vencimiento_final": "2027-05-10", "lote_final": "LOTEQF1B",
        "estanteria_final": "E-12", "posicion_final": "B3"}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        inci = conn.execute("SELECT nombre_inci FROM maestro_mps WHERE codigo_mp='MP-RCQF'").fetchone()[0]
        assert inci == "PROPYLENE GLYCOL", "el INCI corregido debe quedar en el maestro"
        row = conn.execute("SELECT estado_lote, cantidad, lote, estanteria, posicion, fecha_vencimiento "
                           "FROM movimientos WHERE material_id='MP-RCQF' ORDER BY id DESC LIMIT 1").fetchone()
        assert row[0] == "VIGENTE"
        assert abs(float(row[1]) - 3950) < 0.01, "cantidad real corregida al kardex"
        assert row[2] == "LOTEQF1B", "lote interno renombrado"
        assert row[3] == "E-12" and row[4] == "B3", "ubicación final guardada"
        assert (row[5] or "")[:10] == "2027-05-10", "vencimiento corregido"
    finally:
        conn.close()


def test_rotulo_acepta_override_ubicacion(app, db_clean):
    """El rótulo imprime con la ubicación pasada por Calidad (?est=&pos=) aunque no esté en el kardex."""
    mid = _lote_cuarentena("MP-RCQU", "LOTEQU1")
    c = _login(app, "sebastian")
    r = c.get("/rotulo-recepcion/MP-RCQU/LOTEQU1/4000?est=E-9&pos=A1")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "E-9" in html and "A1" in html, "la ubicación override debe salir en el rótulo"


def test_indicadores_mp_cuentan_f02(app, db_clean):
    """Los indicadores de Calidad ahora reflejan el flujo F02: al aprobar una MP, sube MP liberadas
    y el RFT; y aparecen los KPIs nuevos (mp_liberadas_mes, mp_rechazadas_mes, rft_documental_f01)."""
    mid = _lote_cuarentena("MP-IND1", "LOTEIND1")
    c = _login(app)
    # F01 conforme (cuenta para cumplimiento documental)
    c.post("/api/calidad/recepcion-tecnica", json={
        "mov_id": mid, "tipo_insumo": "materia_prima", "crit_rotulado": "cumple",
        "resultado": "conforme", "realiza_por": "Yuliel"}, headers=csrf_headers())
    # F02 aprobado + firma → libera
    sig = _firmar(c, mid, "libera")
    r = c.post("/api/calidad/certificado-analisis", json={
        "mov_id": mid, "resultado": "aprobado", "aprobo_por": "Laura", "signature_id": sig,
        "aspecto_result": "ok", "aspecto_cumple": "si"}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    ind = c.get("/api/calidad/indicadores").get_json()
    codes = {i["codigo"]: i for i in ind.get("indicadores", [])}
    assert "mp_liberadas_mes" in codes, "debe existir el KPI MP liberadas"
    assert "mp_rechazadas_mes" in codes and "rft_documental_f01" in codes
    assert (codes["mp_liberadas_mes"]["valor"] or 0) >= 1, "la MP liberada por F02 debe contar"
    # RFT (right first time) debe reflejar el aprobado (100% si es el único)
    assert (codes["rft_mp"]["valor"] or 0) >= 1
    # cumplimiento documental F01: la F01 conforme debe dar 100%
    assert (codes["rft_documental_f01"]["valor"] or 0) >= 100


def test_ciclo_completo_ingreso_planta_a_disponible(app, db_clean):
    """Ciclo completo (Sebastián 19-jul): ingreso MANUAL de Planta → CUARENTENA → aparece en Calidad →
    F02 aprobado → VIGENTE → disponible para fabricación (sale de cuarentena, entra a /api/lotes)."""
    import os as _os
    conn = sqlite3.connect(_os.environ["DB_PATH"], timeout=10)
    conn.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, tipo_material, activo) "
                 "VALUES ('MP-CICLO', 'MP Ciclo', 'MP', 1)")
    conn.commit(); conn.close()
    c = _login(app, "sebastian")
    # 1) ingreso manual de Planta (modal Ingreso MP) · cuarentena por defecto
    r = c.post("/api/recepcion", json={"codigo_mp": "MP-CICLO", "cantidad": 5000, "lote": "LOTECICLO",
               "fecha_vencimiento": "2027-12-31"}, headers=csrf_headers())
    assert r.status_code in (200, 201), r.data[:300]
    # entra en CUARENTENA (no disponible aún)
    assert _estado_lote("LOTECICLO") == "CUARENTENA"
    lotes_disp = [l for l in c.get("/api/lotes").get_json().get("lotes", []) if l.get("lote") == "LOTECICLO"]
    assert not lotes_disp, "en cuarentena NO debe estar en stock disponible"
    cuar = c.get("/api/lotes/cuarentena").get_json()
    mid = next((x["id"] for x in cuar if x.get("lote") == "LOTECICLO"), None)
    assert mid is not None, "el ingreso manual debe aparecer en cuarentena"
    # 2) aparece en el pipeline de Calidad (conectado de una)
    pipe = c.get("/api/calidad/recepcion-pipeline").get_json()
    assert mid in [l["mov_id"] for l in pipe.get("lotes", [])], "debe aparecer en Calidad para F01/F02"
    # 3) Calidad aprueba el F02 (con firma) → libera
    sig = _firmar(c, mid, "libera")
    r2 = c.post("/api/calidad/certificado-analisis", json={
        "mov_id": mid, "resultado": "aprobado", "aprobo_por": "Laura", "signature_id": sig,
        "estanteria_final": "E-1", "posicion_final": "A1"}, headers=csrf_headers())
    assert r2.status_code == 200, r2.data[:300]
    # 4) queda VIGENTE, sale de cuarentena y entra a stock disponible para fabricación
    assert _estado_lote("LOTECICLO") == "VIGENTE"
    cuar2 = c.get("/api/lotes/cuarentena").get_json()
    assert "LOTECICLO" not in [x.get("lote") for x in cuar2], "liberado ya no debe estar en cuarentena"
    disp2 = [l for l in c.get("/api/lotes").get_json().get("lotes", []) if l.get("lote") == "LOTECICLO"]
    assert disp2, "liberado debe estar disponible en /api/lotes (usable en fabricación)"
