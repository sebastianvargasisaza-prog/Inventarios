"""Verificar despeje: regla de 2 personas en lotes reales, PERO en lotes DEMO (lote 'DEMO-...')
se permite AUTO-verificar para poder caminar el demo con una sola persona (Sebastián 20-jul)."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _ebr_con_despeje(lote, marcado_por):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        pn = "ZZ DESP " + lote
        conn.execute("INSERT INTO mbr_templates (producto_nombre,version,lote_size_g,creado_por,estado) "
                     "VALUES (?,1,1000,'test','aprobado')", (pn,))
        mbr = conn.execute("SELECT id FROM mbr_templates WHERE producto_nombre=? ORDER BY id DESC LIMIT 1", (pn,)).fetchone()[0]
        conn.execute("INSERT INTO ebr_ejecuciones (mbr_template_id,mbr_version,lote,lote_codigo,estado,iniciado_por,"
                     "iniciado_at_utc,cantidad_objetivo_g,fase) VALUES (?,1,?,?, 'en_proceso','test',"
                     "'2026-07-20T00:00:00',1000,'fabricacion')", (mbr, lote, lote))
        eid = conn.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (lote,)).fetchone()[0]
        conn.execute("INSERT INTO ebr_despeje_items (ebr_id,item_idx,etapa,item_texto,cumple,registrado_por,registrado_at_utc) "
                     "VALUES (?,0,'dispensacion','Temp <30',1,?, '2026-07-20T00:00:00')", (eid, marcado_por))
        conn.commit()
        return eid
    finally:
        conn.close()


def test_demo_permite_autoverificar(app, db_clean):
    eid = _ebr_con_despeje("DEMO-260720999", "sebastian")
    c = _login(app, "sebastian")  # el MISMO que marcó
    r = c.post(f"/api/brd/ebr/{eid}/despeje-verificar",
               json={"item_idx": 0, "etapa": "dispensacion"}, headers=csrf_headers())
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json().get("verificados") == 1, "en DEMO el mismo usuario puede verificar"


def test_lote_real_bloquea_autoverificacion(app, db_clean):
    eid = _ebr_con_despeje("REAL-260720999", "sebastian")
    c = _login(app, "sebastian")  # el mismo que marcó → 409 (regla 2 personas)
    r = c.post(f"/api/brd/ebr/{eid}/despeje-verificar",
               json={"item_idx": 0, "etapa": "dispensacion"}, headers=csrf_headers())
    assert r.status_code == 409, "en lote real no podés verificar tu propio despeje"
    assert r.get_json().get("codigo") == "AUTOVERIFICACION_BLOQUEADA"
