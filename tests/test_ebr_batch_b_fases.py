"""Batch B · motor EBR por fase (Envasado/Acondicionamiento · reemplazo MyBatch).

Cubre:
  · MBR desde fórmula es multi-fase (fabricación + envasado + acondicionamiento)
  · un EBR clona SOLO los pasos de su fase
  · el MISMO lote físico puede tener EBR de fabricación, envasado y acond
  · gate: no liberar acondicionamiento con arte/etiqueta sin aprobar
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _h():
    h = {"Content-Type": "application/json"}; h.update(csrf_headers()); return h


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def _firmar(c, *, record_table, record_id, meaning):
    rc = c.post("/api/sign/challenge", json={"password": TEST_PASSWORD}, headers=csrf_headers())
    token = rc.get_json()["token"]
    rs = c.post("/api/sign", json={"record_table": record_table, "record_id": str(record_id),
                                   "meaning": meaning, "challenge_token": token}, headers=csrf_headers())
    assert rs.status_code == 201, rs.data
    return rs.get_json()["signature_id"]


def test_ebr_por_fase_clona_solo_su_fase(app, db_clean):
    c = _login(app, "sebastian")
    c.patch("/api/identidad/sebastian", json={"cedula": "77777777"}, headers=_h())
    # MBR multi-fase: 1 dispensación + 1 mezcla (fab) + 3 envasado + 3 acond = 8 pasos
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) VALUES ('MP-Z','Agua',1)")
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('ZZ-BFASE', 1, 1)")
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES ('ZZ-BFASE','MP-Z','Agua',100,1000)")
    r = c.post("/api/brd/mbr/generar-desde-formula", json={"producto_nombre": "ZZ-BFASE"}, headers=_h())
    assert r.status_code == 201, r.data
    assert r.get_json()["pasos"] == 8, r.data
    mbr_id = r.get_json()["id"]
    c.post(f"/api/brd/mbr/{mbr_id}/submit", json={}, headers=_h())
    sig = _firmar(c, record_table="mbr_templates", record_id=mbr_id, meaning="aprueba")
    assert c.post(f"/api/brd/mbr/{mbr_id}/aprobar", json={"signature_id": sig}, headers=_h()).status_code == 200

    # EBR por fase: cada uno clona SOLO sus pasos. El lote del EBR lleva sufijo
    # de fase (lote UNIQUE a nivel BD); el lote físico real va en lote_codigo.
    op = c.post("/api/brd/ebr", json={"mbr_template_id": mbr_id, "lote": "BFASE-L1", "fase": "fabricacion"}, headers=_h())
    of = c.post("/api/brd/ebr", json={"mbr_template_id": mbr_id, "lote": "BFASE-L1-OF", "fase": "envasado"}, headers=_h())
    oa = c.post("/api/brd/ebr", json={"mbr_template_id": mbr_id, "lote": "BFASE-L1-OA", "fase": "acondicionamiento"}, headers=_h())
    assert op.status_code == 201 and of.status_code == 201 and oa.status_code == 201, (op.data, of.data, oa.data)
    assert op.get_json()["pasos"] == 2, op.data   # dispensación + mezcla
    assert of.get_json()["pasos"] == 3, of.data   # 3 envasado
    assert oa.get_json()["pasos"] == 3, oa.data   # 3 acondicionamiento


def test_mismo_lote_misma_fase_rechaza(app, db_clean):
    c = _login(app, "sebastian")
    c.patch("/api/identidad/sebastian", json={"cedula": "77777777"}, headers=_h())
    mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                   "VALUES ('ZZ-DUP', 1, 'aprobado', 1000, 'sebastian')")
    r1 = c.post("/api/brd/ebr", json={"mbr_template_id": mbr_id, "lote": "DUP-L1", "fase": "envasado"}, headers=_h())
    assert r1.status_code == 201, r1.data
    r2 = c.post("/api/brd/ebr", json={"mbr_template_id": mbr_id, "lote": "DUP-L1", "fase": "envasado"}, headers=_h())
    assert r2.status_code == 409, r2.data


def test_acond_no_libera_con_arte_sin_aprobar(app, db_clean):
    c = _login(app, "sebastian")
    c.patch("/api/identidad/sebastian", json={"cedula": "77777777"}, headers=_h())
    mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                   "VALUES ('ZZ-OA', 1, 'aprobado', 1000, 'sebastian')")
    ebr_id = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, estado, fase, "
                   "iniciado_por, iniciado_at_utc, cantidad_objetivo_g, cantidad_real_g) "
                   "VALUES (?, 1, 'OA-L1', 'completado', 'acondicionamiento', 'sebastian', "
                   "datetime('now','utc'), 1000, 980)", (mbr_id,))
    # arte registrada SIN aprobar
    _exec("INSERT INTO ebr_artes_codificacion (ebr_id, descripcion, creado_por, creado_at_utc) "
          "VALUES (?, 'Etiqueta frontal', 'sebastian', datetime('now','utc'))", (ebr_id,))
    sig = _firmar(c, record_table="ebr_ejecuciones", record_id=ebr_id, meaning="libera")
    r = c.post(f"/api/brd/ebr/{ebr_id}/liberar", json={"signature_id": sig}, headers=_h())
    assert r.status_code == 409, r.data
    assert r.get_json().get("codigo") == "ARTES_SIN_APROBAR", r.data
