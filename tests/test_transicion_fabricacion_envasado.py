"""Transición Fabricación → Envasado (Sebastián 20-jul · el demo/lote real: al FINALIZAR y liberar
la fabricación, el MISMO lote pasa a Envasado). Al liberar el granel (QC aprueba) el hook de
liberar_ebr auto-crea el legajo de Envasado del mismo lote (brd.py). Verifica esa transición."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _firma(record_id, meaning, signer):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        cur = conn.execute(
            "INSERT INTO e_signatures (record_table, record_id, meaning, signer_username, "
            "signed_at_utc, auth_factor, signature_hash) VALUES ('ebr_ejecuciones',?,?,?, "
            "'2026-07-20T00:00:00','password','h')", (str(record_id), meaning, signer))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def test_liberar_fabricacion_crea_envasado(app, db_clean):
    prod = "ZZ TRANS FAB ENV"
    lote = "TRANS-2026-001"
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        # MBR aprobado (para que crear_ebr_desde_mbr fase envasado resuelva el producto)
        conn.execute("INSERT INTO mbr_templates (producto_nombre,version,lote_size_g,creado_por,estado) "
                     "VALUES (?,1,10000,'test','aprobado')", (prod,))
        mbr_id = conn.execute("SELECT id FROM mbr_templates WHERE producto_nombre=?", (prod,)).fetchone()[0]
        # EBR de FABRICACIÓN ya COMPLETADO (listo para que Calidad libere)
        conn.execute("INSERT INTO ebr_ejecuciones (mbr_template_id,mbr_version,lote,lote_codigo,estado,iniciado_por,"
                     "iniciado_at_utc,cantidad_objetivo_g,fase) VALUES (?,1,?,?, 'completado','test',"
                     "'2026-07-20T00:00:00',10000,'fabricacion')", (mbr_id, lote, lote))
        fab_id = conn.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (lote,)).fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    # Antes: NO hay legajo de envasado para el lote
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        n0 = conn.execute("SELECT COUNT(*) FROM ebr_ejecuciones WHERE COALESCE(fase,'')='envasado' "
                          "AND COALESCE(lote_codigo,lote)=?", (lote,)).fetchone()[0]
    finally:
        conn.close()
    assert n0 == 0

    # Calidad libera la fabricación (con e-firma) → debe crear el legajo de envasado
    sid = _firma(fab_id, "libera", "sebastian")
    c = _login(app, "sebastian")
    r = c.post(f"/api/brd/ebr/{fab_id}/liberar", json={"signature_id": sid}, headers=csrf_headers())
    assert r.status_code == 200, r.get_data(as_text=True)

    # Después: EXISTE un legajo de envasado para el MISMO lote
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        env = conn.execute("SELECT COUNT(*) FROM ebr_ejecuciones WHERE COALESCE(fase,'')='envasado' "
                           "AND COALESCE(lote_codigo,lote)=?", (lote,)).fetchone()[0]
    finally:
        conn.close()
    assert env >= 1, "al liberar la fabricación, el lote debe pasar a Envasado (legajo OF auto-creado)"
