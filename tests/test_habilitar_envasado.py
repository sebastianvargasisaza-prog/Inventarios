"""Re-disparo manual del legajo de ENVASADO (Sebastián 20-jul: "ya liberé pero no me sale en envasado").
El hook automático del liberar es best-effort; este endpoint lo re-crea (o reusa) y devuelve el error real."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _fab_liberado(prod, lote):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        conn.execute("INSERT INTO mbr_templates (producto_nombre,version,lote_size_g,creado_por,estado) "
                     "VALUES (?,1,10000,'test','aprobado')", (prod,))
        mbr = conn.execute("SELECT id FROM mbr_templates WHERE producto_nombre=?", (prod,)).fetchone()[0]
        conn.execute("INSERT INTO ebr_ejecuciones (mbr_template_id,mbr_version,lote,lote_codigo,estado,iniciado_por,"
                     "iniciado_at_utc,liberado_por,liberado_at_utc,cantidad_objetivo_g,fase) VALUES "
                     "(?,1,?,?, 'liberado','test','2026-07-20T00:00:00','test','2026-07-21T00:00:00',10000,'fabricacion')",
                     (mbr, lote, lote))
        eid = conn.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (lote,)).fetchone()[0]
        conn.commit()
        return eid
    finally:
        conn.close()


def test_habilitar_envasado_crea_legajo(app, db_clean):
    prod = "ZZ HAB ENV"
    lote = "HABENV-2026-001"
    fab = _fab_liberado(prod, lote)
    c = _login(app, "sebastian")
    r = c.post(f"/api/brd/ebr/{fab}/habilitar-envasado", json={}, headers=csrf_headers())
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    assert j.get("envasado_ebr_id"), "debe devolver el id del legajo de envasado creado"
    # existe un legajo de envasado para el MISMO lote físico
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        n = conn.execute("SELECT COUNT(*) FROM ebr_ejecuciones WHERE COALESCE(fase,'')='envasado' "
                         "AND COALESCE(lote_codigo,lote)=?", (lote,)).fetchone()[0]
    finally:
        conn.close()
    assert n >= 1

    # idempotente · segunda llamada reusa (no duplica)
    r2 = c.post(f"/api/brd/ebr/{fab}/habilitar-envasado", json={}, headers=csrf_headers())
    assert r2.status_code == 200
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        n2 = conn.execute("SELECT COUNT(*) FROM ebr_ejecuciones WHERE COALESCE(fase,'')='envasado' "
                         "AND COALESCE(lote_codigo,lote)=?", (lote,)).fetchone()[0]
    finally:
        conn.close()
    assert n2 == n, "no debe duplicar el legajo de envasado"
