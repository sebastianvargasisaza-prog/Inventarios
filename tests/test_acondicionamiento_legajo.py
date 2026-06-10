"""Legajo de Acondicionamiento (OA) · reemplazo MyBatch · 10-jun-2026.

Cubre el nuevo módulo OA (espeja Envasado):
  · El MISMO lote físico tiene legajo de Fabricación (OP), Envasado (OF) y
    Acondicionamiento (OA) a la vez → 3 EBR distintos que CONVIVEN (la llave `lote`
    lleva sufijo de fase, el lote físico real va en lote_codigo).
  · vista-completa de un EBR de acondicionamiento expone fase + lote físico.
  · La página /planta/legajo-acondicionamiento/<id> carga.
  · Idempotencia: re-crear la OA del mismo lote físico no duplica el legajo.
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


def test_oa_legajo_convive_con_op_of(app, db_clean):
    c = _login(app, "sebastian")
    c.patch("/api/identidad/sebastian", json={"cedula": "77777777"}, headers=_h())
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) VALUES ('MP-OA','Agua',1)")
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('ZZ-OA-LEG', 1, 1)")
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES ('ZZ-OA-LEG','MP-OA','Agua',100,1000)")
    # Genera + APRUEBA el MBR en un paso (firma del usuario · Part 11).
    r = c.post("/api/brd/mbr/preparar-aprobado", json={"producto_nombre": "ZZ-OA-LEG"}, headers=_h())
    assert r.status_code == 200, r.data

    # Tres legajos del MISMO lote físico → deben coexistir (3 ids distintos).
    op = c.post("/api/brd/legajo-rapido", json={"producto": "ZZ-OA-LEG", "lote": "LOTEOA1", "fase": "fabricacion"}, headers=_h())
    of = c.post("/api/brd/legajo-rapido", json={"producto": "ZZ-OA-LEG", "lote": "LOTEOA1", "fase": "envasado"}, headers=_h())
    oa = c.post("/api/brd/legajo-rapido", json={"producto": "ZZ-OA-LEG", "lote": "LOTEOA1", "fase": "acondicionamiento"}, headers=_h())
    assert op.status_code == 200 and of.status_code == 200 and oa.status_code == 200, (op.data, of.data, oa.data)
    ids = {op.get_json()["id"], of.get_json()["id"], oa.get_json()["id"]}
    assert len(ids) == 3, (op.data, of.data, oa.data)
    oa_id = oa.get_json()["id"]

    # vista-completa de la OA: fase acondicionamiento + lote físico real (no la llave sufijada).
    v = c.get(f"/api/brd/ebr/{oa_id}/vista-completa")
    assert v.status_code == 200, v.data
    vj = v.get_json()
    assert vj["fase"] == "acondicionamiento", vj.get("fase")
    assert vj["header"]["lote_codigo"] == "LOTEOA1", vj["header"]
    # pasos clonados = solo los de acondicionamiento (no trae los de fab/envasado).
    assert all((p.get("fase") or "").lower() in ("acondicionamiento", "") for p in vj.get("pasos", [])), vj.get("pasos")

    # La página del legajo OA carga y muestra su título.
    p = c.get(f"/planta/legajo-acondicionamiento/{oa_id}")
    assert p.status_code == 200, p.status_code
    assert b"ORDEN DE ACONDICIONAMIENTO" in p.data

    # La lista unificada de OA incluye la orden con el lote físico (no la llave -OA).
    lu = c.get("/api/brd/ordenes-unificadas?fase=acondicionamiento")
    assert lu.status_code == 200, lu.data
    lotes = [o.get("lote_bulk") for o in lu.get_json().get("ordenes", [])]
    assert "LOTEOA1" in lotes, lotes

    # Idempotencia: re-crear la OA del mismo lote físico NO duplica (LOTE_DUPLICADO → 409).
    oa2 = c.post("/api/brd/legajo-rapido", json={"producto": "ZZ-OA-LEG", "lote": "LOTEOA1", "fase": "acondicionamiento"}, headers=_h())
    assert oa2.status_code == 409, oa2.data


def test_descartar_ebr_anula_y_desaparece(app, db_clean):
    """Descartar (anular) un legajo creado por error: estado='cancelado' + audit y
    desaparece de la lista de órdenes activas. Solo Admin · 10-jun-2026."""
    c = _login(app, "sebastian")
    mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                   "VALUES ('ZZ-DESC', 1, 'aprobado', 1000, 'sebastian')")
    ebr_id = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, estado, fase, "
                   "iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                   "VALUES (?, 1, 'DESC-OP1', 'iniciado', 'fabricacion', 'sebastian', "
                   "datetime('now','utc'), 1000)", (mbr_id,))
    lu = c.get("/api/brd/ordenes-unificadas?fase=fabricacion").get_json()
    assert any(o.get("ebr_id") == ebr_id for o in lu["ordenes"]), "el legajo debe aparecer antes de descartar"
    r = c.post(f"/api/brd/ebr/{ebr_id}/descartar", json={"motivo": "creado por error"}, headers=_h())
    assert r.status_code == 200 and r.get_json().get("estado") == "cancelado", r.data
    lu2 = c.get("/api/brd/ordenes-unificadas?fase=fabricacion").get_json()
    assert not any(o.get("ebr_id") == ebr_id for o in lu2["ordenes"]), "el legajo cancelado NO debe aparecer"
    import sqlite3 as _s, os as _o
    cc = _s.connect(_o.environ["DB_PATH"])
    est = cc.execute("SELECT estado FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()[0]
    cc.close()
    assert est == "cancelado", est


def test_descartar_ebr_liberado_rechaza(app, db_clean):
    """Un EBR liberado es inmutable · no se puede descartar (409)."""
    c = _login(app, "sebastian")
    mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                   "VALUES ('ZZ-DESC2', 1, 'aprobado', 1000, 'sebastian')")
    ebr_id = _exec("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, estado, fase, "
                   "iniciado_por, iniciado_at_utc, cantidad_objetivo_g, cantidad_real_g) "
                   "VALUES (?, 1, 'DESC-LIB', 'liberado', 'fabricacion', 'sebastian', "
                   "datetime('now','utc'), 1000, 980)", (mbr_id,))
    r = c.post(f"/api/brd/ebr/{ebr_id}/descartar", json={}, headers=_h())
    assert r.status_code == 409, r.data
