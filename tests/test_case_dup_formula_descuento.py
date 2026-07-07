"""Audit ultracode 7-jul (P0) · un header de fórmula CASE-DUPLICADO (activo + inactivo case-variant) NO debe
impedir el descuento de MP en producción programada. Antes la exclusión `UPPER(TRIM) NOT IN (...activo=0)`
botaba TAMBIÉN los ítems de la fórmula ACTIVA → mps=[] → la producción no descontaba MP (stock inflado)."""
import os
import sqlite3


def test_case_dup_header_no_vacia_el_descuento(app, db_clean):
    from api.blueprints.programacion import _calcular_mp_consumo_produccion
    PROD = "CASEDUP SERUM"      # header ACTIVO (mayúsculas)
    DUP = "Casedup Serum"       # header INACTIVO case-variant (normaliza al mismo)
    db = sqlite3.connect(os.environ["DB_PATH"])
    mats = [r[0] for r in db.execute(
        "SELECT codigo_mp FROM maestro_mps WHERE COALESCE(activo,1)=1 ORDER BY codigo_mp LIMIT 2").fetchall()]
    assert len(mats) >= 2, "el seed de maestro_mps debe tener >=2 materiales activos"
    for t in ("formula_headers", "formula_items"):
        db.execute(f"DELETE FROM {t} WHERE UPPER(TRIM(producto_nombre))=UPPER(?)", (PROD,))
    db.execute("DELETE FROM produccion_programada WHERE UPPER(TRIM(producto))=UPPER(?)", (PROD,))
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 10, 1)", (PROD,))
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 10, 0)", (DUP,))
    db.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
               "VALUES (?, ?, 'Ingrediente A', 5.0, 500)", (PROD, mats[0]))
    db.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
               "VALUES (?, ?, 'Ingrediente B', 2.0, 200)", (PROD, mats[1]))
    db.execute("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
               "VALUES (?, '2026-08-01', 1, 'programado', 10, 'eos_plan')", (PROD,))
    pid = db.execute("SELECT id FROM produccion_programada WHERE producto=? ORDER BY id DESC LIMIT 1", (PROD,)).fetchone()[0]
    db.commit()
    c = db.cursor()
    mps, cant_kg = _calcular_mp_consumo_produccion(c, pid)
    db.close()
    assert mps, ("el descuento NO debe quedar vacío por un header inactivo case-variant (bug P0 · antes [])", mps)
