"""A-3 (Sebastián 12-jun): el PT se crea UNA sola vez, al terminar la fase FINAL
del lote físico (regla CEO: acondicionamiento + liberar), keyado por lote físico
(lote_codigo). Antes cada fase (OP/OF/OA) creaba una Entrada PT con la llave
sufijada -> stock PT inflado x2/x3 en el kardex.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def _q1(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        r = conn.execute(sql, params).fetchone(); return r[0] if r else None
    finally:
        conn.close()


def test_pt_se_crea_una_vez_en_la_fase_final(app, db_clean):
    c = _login(app)
    mbr = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                "VALUES ('ZZ-PTFASE', 1, 'aprobado', 1000, 'sebastian')")
    # 3 EBR del MISMO lote fisico 'PTF1' · lote sufijado por fase, lote_codigo=fisico
    fases = [('PTF1', 'fabricacion'), ('PTF1-OF', 'envasado'), ('PTF1-OA', 'acondicionamiento')]
    ids = {}
    for lote, fase in fases:
        ids[fase] = _exec(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, estado, fase, "
            "iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
            "VALUES (?, 1, ?, 'PTF1', 'en_proceso', ?, 'sebastian', datetime('now','utc'), 1000)",
            (mbr, lote, fase))
    # Completar las 3 fases
    for fase in ('fabricacion', 'envasado', 'acondicionamiento'):
        r = c.post(f"/api/brd/ebr/{ids[fase]}/completar",
                   json={"cantidad_real_g": 980}, headers=csrf_headers())
        assert r.status_code == 200, (fase, r.data)

    # CLAVE: UNA sola Entrada PT, bajo el LOTE FISICO 'PTF1' (no 3, no sufijada)
    n_pt = _q1("SELECT COUNT(*) FROM movimientos WHERE tipo='Entrada' "
               "AND COALESCE(material_id,'') LIKE 'PT\\_%' ESCAPE '\\' "
               "AND lote IN ('PTF1','PTF1-OF','PTF1-OA')")
    assert n_pt == 1, f"debe haber 1 sola Entrada PT (no inflada por fase) · fueron {n_pt}"
    bajo_fisico = _q1("SELECT COUNT(*) FROM movimientos WHERE tipo='Entrada' "
                      "AND COALESCE(material_id,'') LIKE 'PT\\_%' ESCAPE '\\' AND lote='PTF1'")
    assert bajo_fisico == 1, "el PT debe quedar bajo el lote FISICO 'PTF1'"
    sufijada = _q1("SELECT COUNT(*) FROM movimientos WHERE tipo='Entrada' "
                   "AND COALESCE(material_id,'') LIKE 'PT\\_%' ESCAPE '\\' "
                   "AND lote IN ('PTF1-OF','PTF1-OA')")
    assert sufijada == 0, "el PT NO debe quedar bajo la llave sufijada -OF/-OA"
