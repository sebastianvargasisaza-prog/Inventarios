"""DEMO (lote 'DEMO-...'): liberar el lote + visto bueno del Director Técnico se hacen de UN CLICK
sin e-firma (Part 11), para caminar el flujo hasta envasado. Un lote REAL sigue exigiendo signature_id.
(Sebastián 20-jul: "un click, liberar y verificar, para pasar a envasado sin contraseña ya que es demo".)"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _ebr_completado(lote):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        pn = "ZZ LIB " + lote
        conn.execute("INSERT INTO mbr_templates (producto_nombre,version,lote_size_g,creado_por,estado) "
                     "VALUES (?,1,1000,'test','aprobado')", (pn,))
        mbr = conn.execute("SELECT id FROM mbr_templates WHERE producto_nombre=? ORDER BY id DESC LIMIT 1", (pn,)).fetchone()[0]
        conn.execute("INSERT INTO ebr_ejecuciones (mbr_template_id,mbr_version,lote,lote_codigo,estado,iniciado_por,"
                     "iniciado_at_utc,cantidad_objetivo_g,fase) VALUES (?,1,?,?, 'completado','test',"
                     "'2026-07-20T00:00:00',1000,'fabricacion')", (mbr, lote, lote))
        eid = conn.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (lote,)).fetchone()[0]
        conn.commit()
        return eid
    finally:
        conn.close()


def test_demo_libera_sin_firma_un_click(app, db_clean):
    eid = _ebr_completado("DEMO-260720LIB")
    c = _login(app, "sebastian")
    r = c.post(f"/api/brd/ebr/{eid}/liberar", json={}, headers=csrf_headers())
    assert r.status_code == 200, "el DEMO debe liberar sin signature_id · " + r.get_data(as_text=True)
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        row = conn.execute("SELECT estado, liberado_por FROM ebr_ejecuciones WHERE id=?", (eid,)).fetchone()
    finally:
        conn.close()
    assert row[0] == "liberado"
    assert (row[1] or "").strip() == "sebastian", "debe registrar QUIÉN liberó (el nombre)"


def test_demo_visto_bueno_dt_sin_firma(app, db_clean):
    eid = _ebr_completado("DEMO-260720DT")
    c = _login(app, "sebastian")  # admin → aprueba_dt
    r = c.post(f"/api/brd/ebr/{eid}/aprobar-dt", json={}, headers=csrf_headers())
    assert r.status_code == 200, "el DEMO debe dar visto bueno DT sin firma · " + r.get_data(as_text=True)
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        row = conn.execute("SELECT aprobado_dt_por FROM ebr_ejecuciones WHERE id=?", (eid,)).fetchone()
    finally:
        conn.close()
    assert (row[0] or "").strip() == "sebastian", "debe registrar el nombre del DT que aprobó"


def test_lote_real_liberar_exige_firma(app, db_clean):
    eid = _ebr_completado("REAL-260720LIB")
    c = _login(app, "sebastian")
    r = c.post(f"/api/brd/ebr/{eid}/liberar", json={}, headers=csrf_headers())
    assert r.status_code == 400, "un lote real NO puede liberarse sin signature_id"
