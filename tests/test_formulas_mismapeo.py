"""Detector de nombre↔código cruzado en fórmulas (/api/admin/formulas-mismapeo).

El reparador de huérfanos NO ve el caso 'N-acetil glucosamina con código MP00175
(=Acetyl tetrapeptide-5)' porque el código es válido con stock. Este detector usa
el motor formula_match y además reporta COLISIONES (un mismo código usado por dos
materiales distintos)."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_mismapeo_requiere_admin(app, db_clean):
    r = app.test_client().get("/api/admin/formulas-mismapeo")
    assert r.status_code == 401


def test_mismapeo_detecta_colision_mismo_codigo(app, db_clean):
    """Dos líneas (materiales distintos) con el MISMO código → colisión."""
    db = sqlite3.connect(os.environ["DB_PATH"])
    try:
        db.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_comercial, activo) "
                   "VALUES ('MPMMCOL','Acetyl tetrapeptide-5',1)")
        db.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
                   "VALUES ('ZZ MM COL','MPMMCOL','Acetyl tetrapeptide-5',0.015,1)")
        db.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
                   "VALUES ('ZZ MM COL','MPMMCOL','N-acetil glucosamina',1,10)")
        db.commit()
    finally:
        db.close()
    c = _login(app)
    d = c.get("/api/admin/formulas-mismapeo").get_json()
    assert d.get("ok") is True
    cols = [x for x in (d.get("colisiones") or []) if x["material_id"] == "MPMMCOL"]
    assert cols, d.get("colisiones")
    nombres = {l["nombre"] for l in cols[0]["lineas"]}
    assert "N-acetil glucosamina" in nombres and "Acetyl tetrapeptide-5" in nombres

    db = sqlite3.connect(os.environ["DB_PATH"])
    try:
        db.execute("DELETE FROM formula_items WHERE producto_nombre='ZZ MM COL'")
        db.execute("DELETE FROM maestro_mps WHERE codigo_mp='MPMMCOL'")
        db.commit()
    finally:
        db.close()
