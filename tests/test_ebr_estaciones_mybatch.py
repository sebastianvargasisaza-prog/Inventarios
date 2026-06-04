"""EBR runner · estaciones MyBatch ①②⑦ (precauciones, despeje, registros físicos).

Completan el reemplazo de MyBatch en el legajo electrónico.
"""
import base64
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


def _ebr_en_proceso(producto="ZZ-EST"):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                           "VALUES (?, 1, 'aprobado', 1000, 'sebastian')", (producto,))
        mbr = cur.lastrowid
        cur = conn.execute("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, estado, "
                           "iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                           "VALUES (?, 1, ?, 'en_proceso', 'sebastian', datetime('now','utc'), 1000)",
                           (mbr, producto + "-L1"))
        eid = cur.lastrowid
        conn.commit(); return eid
    finally:
        conn.close()


def test_despeje_conforme_si_todo_cumple(app, db_clean):
    c = _login(app)
    eid = _ebr_en_proceso("ZZ-DESP")
    r = c.post(f"/api/brd/ebr/{eid}/despeje",
               json={"area_limpia": 1, "sin_producto_anterior": 1,
                     "equipos_limpios": 1, "documentacion_ok": 1}, headers=_h())
    assert r.status_code == 201, r.data
    assert r.get_json()["conforme"] == 1, r.data
    # falta un check → NO conforme
    r2 = c.post(f"/api/brd/ebr/{eid}/despeje",
                json={"area_limpia": 1, "sin_producto_anterior": 0,
                      "equipos_limpios": 1, "documentacion_ok": 1}, headers=_h())
    assert r2.get_json()["conforme"] == 0, r2.data
    items = c.get(f"/api/brd/ebr/{eid}/despeje").get_json()["items"]
    assert len(items) == 2


def test_precauciones_y_equipos(app, db_clean):
    c = _login(app)
    eid = _ebr_en_proceso("ZZ-PREC")
    assert c.post(f"/api/brd/ebr/{eid}/precauciones",
                  json={"tipo": "precaucion", "descripcion": "Usar guantes nitrilo"}, headers=_h()).status_code == 201
    assert c.post(f"/api/brd/ebr/{eid}/precauciones",
                  json={"tipo": "equipo", "descripcion": "Marmita 50L #3"}, headers=_h()).status_code == 201
    items = c.get(f"/api/brd/ebr/{eid}/precauciones").get_json()["items"]
    assert len(items) == 2
    assert {i["tipo"] for i in items} == {"precaucion", "equipo"}


def test_registro_fisico_con_pdf(app, db_clean):
    c = _login(app)
    eid = _ebr_en_proceso("ZZ-REG")
    pdf_b64 = base64.b64encode(b"%PDF-1.4 test").decode()
    r = c.post(f"/api/brd/ebr/{eid}/registros-fisicos",
               json={"descripcion": "Tirilla balanza", "archivo_nombre": "t.pdf",
                     "archivo_b64": pdf_b64}, headers=_h())
    assert r.status_code == 201, r.data
    rid = r.get_json()["id"]
    items = c.get(f"/api/brd/ebr/{eid}/registros-fisicos").get_json()["items"]
    assert len(items) == 1 and items[0]["tiene_pdf"] == 1
    # descarga del PDF
    rpdf = c.get(f"/api/brd/ebr/{eid}/registros-fisicos/{rid}/pdf")
    assert rpdf.status_code == 200 and rpdf.data[:4] == b"%PDF"
    # registro sin PDF también vale
    r2 = c.post(f"/api/brd/ebr/{eid}/registros-fisicos",
                json={"descripcion": "Bitácora pH pág 3"}, headers=_h())
    assert r2.status_code == 201, r2.data


def test_estaciones_bloquean_si_no_editable(app, db_clean):
    c = _login(app)
    eid = _ebr_en_proceso("ZZ-LIB")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("UPDATE ebr_ejecuciones SET estado='liberado' WHERE id=?", (eid,)); conn.commit(); conn.close()
    assert c.post(f"/api/brd/ebr/{eid}/precauciones", json={"descripcion": "x"}, headers=_h()).status_code == 409
    assert c.post(f"/api/brd/ebr/{eid}/despeje", json={"area_limpia": 1}, headers=_h()).status_code == 409
