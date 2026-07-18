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


def test_f02_aprobado_libera_lote(app, db_clean):
    mid = _lote_cuarentena("MP-RCQ3", "LOTECQ3")
    c = _login(app)
    # aprobar sin firma del jefe → 400
    r0 = c.post("/api/calidad/certificado-analisis", json={"mov_id": mid, "resultado": "aprobado"},
                headers=csrf_headers())
    assert r0.status_code == 400, r0.data[:200]
    # aprobar CON firma → libera
    r = c.post("/api/calidad/certificado-analisis", json={
        "mov_id": mid, "resultado": "aprobado", "aspecto_result": "polvo blanco", "aspecto_cumple": "si",
        "responsable_analisis": "Yuliel", "aprobo_por": "Laura Gonzalez"}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert r.get_json().get("liberado") == 1
    assert _estado_lote("LOTECQ3") == "VIGENTE", "el lote aprobado debe quedar VIGENTE"


def test_f02_no_aprobado_rechaza(app, db_clean):
    mid = _lote_cuarentena("MP-RCQ4", "LOTECQ4")
    c = _login(app)
    r = c.post("/api/calidad/certificado-analisis", json={
        "mov_id": mid, "resultado": "no_aprobado", "aprobo_por": "Laura"}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert _estado_lote("LOTECQ4") == "RECHAZADO"


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
    # conforme CON firma → libera el envase
    r = c.post("/api/calidad/recepcion-tecnica", json={
        "mov_id": mid, "origen": "MEE", "tipo_insumo": "envase", "crit_empaque": "cumple",
        "resultado": "conforme", "realiza_por": "Yuliel", "aprueba_por": "Laura"}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert r.get_json().get("liberado") == 1
    assert _estado_mee(mid) == "VIGENTE", "el envase conforme debe quedar VIGENTE"


def test_f01_f02_imprimibles(app, db_clean):
    mid = _lote_cuarentena("MP-RCQ5", "LOTECQ5")
    c = _login(app)
    c.post("/api/calidad/recepcion-tecnica", json={
        "mov_id": mid, "tipo_insumo": "materia_prima", "crit_rotulado": "cumple",
        "resultado": "conforme", "realiza_por": "Yuliel"}, headers=csrf_headers())
    c.post("/api/calidad/certificado-analisis", json={
        "mov_id": mid, "resultado": "aprobado", "aspecto_result": "polvo", "aspecto_cumple": "si",
        "responsable_analisis": "Yuliel", "aprobo_por": "Laura"}, headers=csrf_headers())
    f01 = c.get("/api/calidad/recepcion-tecnica/imprimible?mov_id=%d" % mid)
    assert f01.status_code == 200 and b"COC-PRO-002-F01" in f01.data
    f02 = c.get("/api/calidad/certificado-analisis/imprimible?mov_id=%d" % mid)
    assert f02.status_code == 200 and b"COC-PRO-002-F02" in f02.data
