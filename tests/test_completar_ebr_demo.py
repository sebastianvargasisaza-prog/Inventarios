"""Terminar producción (completar EBR): un lote DEMO (lote 'DEMO-...') se puede terminar SIN todos
los pasos completos (sandbox para caminar el flujo); un lote REAL exige todo (GMP). Sebastián 20-jul."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _ebr_con_paso_pendiente(lote):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        pn = "ZZ COMPL " + lote
        conn.execute("INSERT INTO mbr_templates (producto_nombre,version,lote_size_g,creado_por,estado) "
                     "VALUES (?,1,1000,'test','aprobado')", (pn,))
        mbr = conn.execute("SELECT id FROM mbr_templates WHERE producto_nombre=? ORDER BY id DESC LIMIT 1", (pn,)).fetchone()[0]
        conn.execute("INSERT INTO ebr_ejecuciones (mbr_template_id,mbr_version,lote,lote_codigo,estado,iniciado_por,"
                     "iniciado_at_utc,cantidad_objetivo_g,fase) VALUES (?,1,?,?, 'en_proceso','test',"
                     "'2026-07-20T00:00:00',1000,'fabricacion')", (mbr, lote, lote))
        eid = conn.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (lote,)).fetchone()[0]
        # un paso PENDIENTE (sin completar) → bloquea en lote real
        conn.execute("INSERT INTO ebr_pasos_ejecutados (ebr_id,mbr_paso_id,orden,descripcion,estado) "
                     "VALUES (?,1,1,'Mezclar','pendiente')", (eid,))
        conn.commit()
        return eid
    finally:
        conn.close()


def test_demo_termina_con_pasos_pendientes(app, db_clean):
    eid = _ebr_con_paso_pendiente("DEMO-260720COMP")
    c = _login(app, "sebastian")
    r = c.post(f"/api/brd/ebr/{eid}/completar", json={"cantidad_real_g": 950}, headers=csrf_headers())
    assert r.status_code == 200, "el DEMO debe poder terminar con pasos pendientes · " + r.get_data(as_text=True)


def test_lote_real_bloquea_si_faltan_pasos(app, db_clean):
    eid = _ebr_con_paso_pendiente("REAL-260720COMP")
    c = _login(app, "sebastian")
    r = c.post(f"/api/brd/ebr/{eid}/completar", json={"cantidad_real_g": 950}, headers=csrf_headers())
    assert r.status_code == 409, "un lote real NO puede terminar con pasos sin completar"
