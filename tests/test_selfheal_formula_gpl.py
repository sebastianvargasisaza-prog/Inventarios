"""Sebastián 5-jul (M71) · el self-heal cron re-deriva formula_items.cantidad_g_por_lote = % × lote_size × 10,
dejando la columna consistente aunque una reconciliación parcial la haya dejado con bases mezcladas.
"""
import os
import sqlite3


def test_selfheal_rederiva_cantidad_g_por_lote(app, db_clean):
    PROD = "PROD-SELFHEAL-GPL"
    M_OK = "MPSH00001"      # ya bien (60 = 0.3% × 20kg × 10)
    M_MAL = "MPSH00002"     # corrupto (6 = base 100g, debería ser 1200 para 20kg)
    db = sqlite3.connect(os.environ["DB_PATH"])
    for t in ("formula_headers", "formula_items"):
        db.execute(f"DELETE FROM {t} WHERE producto_nombre=?", (PROD,))
    for mid, nom in ((M_OK, "Activo OK"), (M_MAL, "Cetiol corrupto")):
        db.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, activo) VALUES (?,?,1)", (mid, nom))
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, unidad_base_g, activo) VALUES (?, 20, 100, 1)", (PROD,))
    # M_OK: 0.3% con g_por_lote ya correcto (60) · M_MAL: 6% con g_por_lote corrupto (6, base 100g)
    db.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) VALUES (?,?,?,0.3,60)", (PROD, M_OK, "Activo OK"))
    db.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) VALUES (?,?,?,6,6)", (PROD, M_MAL, "Cetiol corrupto"))
    db.commit()
    db.close()

    from blueprints.auto_plan_jobs import job_reconciliar_formula_gpl
    ok, meta, n = job_reconciliar_formula_gpl(app)
    assert ok, meta

    db = sqlite3.connect(os.environ["DB_PATH"])
    vals = dict(db.execute("SELECT material_id, cantidad_g_por_lote FROM formula_items WHERE producto_nombre=?", (PROD,)).fetchall())
    ub = db.execute("SELECT unidad_base_g FROM formula_headers WHERE producto_nombre=?", (PROD,)).fetchone()[0]
    db.close()
    # ambos re-derivados a % × lote_size(20) × 10
    assert abs(vals[M_OK] - 60) < 0.01, ("0.3% × 20kg × 10 = 60g", vals[M_OK])
    assert abs(vals[M_MAL] - 1200) < 0.01, ("6% × 20kg × 10 = 1200g (corrupto 6 → 1200)", vals[M_MAL])
    # unidad_base_g alineado a lote_size × 1000 = 20000
    assert abs(float(ub) - 20000) < 0.01, ("unidad_base_g debe alinearse a lote_size×1000", ub)
