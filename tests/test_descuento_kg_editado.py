"""Sebastián 5-jul (auditoría ultracode fórmula→descuento) · el descuento PROGRAMADO debe usar
PORCENTAJE × kg REAL (respeta el kg editado · M44), no `cantidad_g_por_lote × lotes` crudo (M16/M50).
"""
import os
import sqlite3


def test_descuento_programado_usa_kg_editado(app, db_clean):
    PROD = "PROD-KGEDIT-X"
    MAT = "MPKGEDIT01"
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM formula_items WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    # el trigger FK de formula_items (M38) exige el material en maestro_mps activo=1
    db.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, activo) VALUES (?, 'Material KG Editado', 1)", (MAT,))
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 1, 1)", (PROD,))
    # porcentaje 10% · cantidad_g_por_lote coherente (10% de 1kg = 100g)
    db.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
               "VALUES (?,?,?,10,100)", (PROD, MAT, "Material KG Editado"))
    # producción con kg EDITADO a 2 (≠ lotes×lote_size = 1×1 = 1)
    db.execute("INSERT INTO produccion_programada (producto, fecha_programada, lotes, cantidad_kg, estado, origen) "
               "VALUES (?, date('now'), 1, 2, 'programado', 'eos_plan')", (PROD,))
    pid = db.execute("SELECT id FROM produccion_programada WHERE producto=? ORDER BY id DESC LIMIT 1", (PROD,)).fetchone()[0]
    db.commit()
    c = db.cursor()

    from blueprints.programacion import _calcular_mp_consumo_produccion
    mps, meta = _calcular_mp_consumo_produccion(c, pid)
    db.close()

    m = next((x for x in mps if str(x.get('codigo_mp', '')).upper() == MAT
              or 'MATERIAL KG' in str(x.get('nombre', '')).upper()), None)
    assert m is not None, ("el material debe estar en el consumo", mps)
    # % × kg_real(2) × 1000 = 10/100 × 2 × 1000 = 200 g · NO g_lote(100)×lotes(1) = 100 g
    assert abs(m['cantidad_g'] - 200) < 1, (
        "el descuento debe usar % × kg editado (200g), no cantidad_g_por_lote×lotes (100g)", m['cantidad_g'])
