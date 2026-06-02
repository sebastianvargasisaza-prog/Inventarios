"""Factibilidad 2-jun: si el stock está bajo un código distinto al de la fórmula
pero resoluble por NOMBRE (no bridge), factibilidad debe encontrarlo (no déficit
falso). Antes solo miraba id+bridge → perdía el tier de nombre."""
import os, sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_factibilidad_resuelve_por_nombre(app, db_clean):
    bod = "MPFACBOD01"    # bodega · tiene stock · nombre "Glicerina FacTest"
    fcode = "MPFACFRM01"  # código de fórmula · sin movimientos · sin bridge · mismo nombre
    prod = "ZZ FAC NOMBRE"
    nombre = "Glicerina FacTest"
    db = sqlite3.connect(os.environ["DB_PATH"])
    try:
        for t, q in [
            ("DELETE FROM formula_items WHERE producto_nombre=?", (prod,)),
            ("DELETE FROM formula_headers WHERE producto_nombre=?", (prod,)),
            ("DELETE FROM produccion_programada WHERE producto=?", (prod,)),
            ("DELETE FROM maestro_mps WHERE codigo_mp IN (?,?)", (bod, fcode)),
            ("DELETE FROM movimientos WHERE material_id=?", (bod,)),
            ("DELETE FROM mp_formula_bridge WHERE formula_material_id=?", (fcode,)),
        ]:
            db.execute(t, q)
        db.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, activo) VALUES (?,?,1)", (bod, nombre))
        db.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, activo) VALUES (?,?,1)", (fcode, nombre))
        # stock SOLO bajo el código de bodega · resoluble por nombre exacto
        db.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote) "
                   "VALUES (?,?,?,?,date('now','-5 hours'),?,'VIGENTE')", (bod, nombre, 50000, "Entrada", "LF1"))
        db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,10,1)", (prod,))
        db.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
                   "VALUES (?,?,?,10,1000)", (prod, fcode, nombre))
        db.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, estado, origen) "
                   "VALUES (?, date('now','-5 hours','+3 days'), 10, 1, 'programado', 'eos_plan')", (prod,))
        db.commit()
    finally:
        db.close()
    c = _login(app)
    r = c.get("/api/plan/factibilidad?dias=30&solo_fijo=1")
    assert r.status_code == 200, r.data
    d = r.get_json()
    fila = next((p for p in d.get("producciones", []) if p.get("producto") == prod), None)
    assert fila is not None, "la producción debe aparecer"
    # 10kg × 10% × 1000 = 1000g · stock 50000 bajo otro código resoluble por nombre
    # → debe ser FACTIBLE (antes: déficit falso por no ver el stock por nombre)
    assert fila.get("factible") is True, f"debió ser factible (stock resoluble por nombre) · {fila.get('mps_faltantes')}"

    db = sqlite3.connect(os.environ["DB_PATH"])
    try:
        for t, q in [
            ("DELETE FROM formula_items WHERE producto_nombre=?", (prod,)),
            ("DELETE FROM formula_headers WHERE producto_nombre=?", (prod,)),
            ("DELETE FROM produccion_programada WHERE producto=?", (prod,)),
            ("DELETE FROM maestro_mps WHERE codigo_mp IN (?,?)", (bod, fcode)),
            ("DELETE FROM movimientos WHERE material_id=?", (bod,)),
        ]:
            db.execute(t, q)
        db.commit()
    finally:
        db.close()
