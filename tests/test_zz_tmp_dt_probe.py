"""TEMP probe (borrar) · verifica si hernando (Director Tecnico) puede dar el visto bueno DT."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login fallo {user}"
    return c


def _ebr_completado(lote):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        pn = "ZZ PROBE " + lote
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


def test_probe_hernando_dt(app, db_clean):
    eid = _ebr_completado("DEMO-PROBEDT1")
    c = _login(app, "hernando")
    # rol que el backend le asigna (lo que la UI usa para pintar el boton)
    rdet = c.get(f"/api/brd/ebr/{eid}")
    print("DETALLE hernando:", rdet.status_code, (rdet.get_json() or {}).get("mi_rol"))
    r = c.post(f"/api/brd/ebr/{eid}/aprobar-dt", json={}, headers=csrf_headers())
    print("HERNANDO aprobar-dt ->", r.status_code, r.get_data(as_text=True))

    eid2 = _ebr_completado("DEMO-PROBEDT2")
    c2 = _login(app, "laura")
    r2 = c2.post(f"/api/brd/ebr/{eid2}/aprobar-dt", json={}, headers=csrf_headers())
    print("LAURA(calidad) aprobar-dt ->", r2.status_code, r2.get_data(as_text=True))

    eid3 = _ebr_completado("DEMO-PROBEDT3")
    c3 = _login(app, "miguel")
    r3 = c3.post(f"/api/brd/ebr/{eid3}/aprobar-dt", json={}, headers=csrf_headers())
    print("MIGUEL(aseg) aprobar-dt ->", r3.status_code, r3.get_data(as_text=True))
    assert True
