"""Material de envase MANUAL del legajo (Sebastián 11-jun): elegir/agregar/editar/borrar
un material desde el desplegable de TODOS los envases (maestro_mee), además del auto-cargado.
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


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def _ebr_envasado(prod="ZZ-MANUAL", lote="ZZMAN-OF", estado="iniciado"):
    pp_id = _exec("INSERT INTO produccion_programada (producto,fecha_programada,cantidad_kg,estado,lotes) "
                  "VALUES (?, date('now','-5 hours'),10,'pendiente',1)", (prod,))
    mbr_id = _exec("INSERT INTO mbr_templates (producto_nombre,version,estado,lote_size_g,creado_por) "
                   "VALUES (?,1,'aprobado',10000,'sebastian')", (prod,))
    return _exec("INSERT INTO ebr_ejecuciones (mbr_template_id,mbr_version,produccion_id,lote,estado,fase,"
                 "iniciado_por,iniciado_at_utc,cantidad_objetivo_g) "
                 "VALUES (?,1,?,?,?,'envasado','sebastian',datetime('now','utc'),10000)",
                 (mbr_id, pp_id, lote, estado))


def test_envase_opciones_lista_catalogo(app, db_clean):
    _exec("INSERT OR IGNORE INTO maestro_mee (codigo, descripcion) VALUES ('ENV-XTEST','Envase X test 50ml')")
    c = _login(app)
    r = c.get("/api/brd/envase-opciones")
    assert r.status_code == 200, r.data
    cods = [o["codigo"] for o in r.get_json()["opciones"]]
    assert "ENV-XTEST" in cods


def test_material_envase_manual_crud(app, db_clean):
    _exec("INSERT OR IGNORE INTO maestro_mee (codigo, descripcion) VALUES ('ENV-XTEST','Envase X test 50ml')")
    ebr_id = _ebr_envasado()
    c = _login(app)

    # AGREGAR
    ra = c.post(f"/api/brd/ebr/{ebr_id}/material-envase",
                json={"material_codigo": "ENV-XTEST", "requerida": 500, "lote_material": "LM-1"})
    assert ra.status_code == 200, ra.data
    rid = ra.get_json()["id"]
    v = c.get(f"/api/brd/ebr/{ebr_id}/vista-completa").get_json()
    manual = [m for m in v["envasado_materiales"] if m.get("id") == rid]
    assert manual, v["envasado_materiales"]
    assert manual[0]["fuente"] == "manual" and "ENV-XTEST" in manual[0]["material"]
    assert abs((manual[0]["requerida"] or 0) - 500) < 1

    # EDITAR (requerida 600, utilizada 550 → diferencia 50)
    re = c.post(f"/api/brd/ebr/{ebr_id}/material-envase",
                json={"id": rid, "material_codigo": "ENV-XTEST", "requerida": 600, "utilizada": 550})
    assert re.status_code == 200, re.data
    m2 = [m for m in c.get(f"/api/brd/ebr/{ebr_id}/vista-completa").get_json()["envasado_materiales"]
          if m.get("id") == rid][0]
    assert abs(m2["requerida"] - 600) < 1 and abs(m2["diferencia"] - 50) < 1, m2

    # BORRAR
    rd = c.delete(f"/api/brd/ebr/{ebr_id}/material-envase/{rid}")
    assert rd.status_code == 200, rd.data
    v3 = c.get(f"/api/brd/ebr/{ebr_id}/vista-completa").get_json()
    assert not [m for m in v3["envasado_materiales"] if m.get("id") == rid]


def test_material_envase_bloqueado_si_liberado(app, db_clean):
    _exec("INSERT OR IGNORE INTO maestro_mee (codigo, descripcion) VALUES ('ENV-XTEST','Envase X test')")
    ebr_id = _ebr_envasado(prod="ZZ-LIBRE", lote="ZZLIB-OF", estado="liberado")
    c = _login(app)
    r = c.post(f"/api/brd/ebr/{ebr_id}/material-envase",
               json={"material_codigo": "ENV-XTEST", "requerida": 100})
    assert r.status_code == 409, r.data
