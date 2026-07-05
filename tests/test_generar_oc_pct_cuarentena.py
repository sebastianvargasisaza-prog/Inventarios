"""Sebastián 5-jul (auditoría ultracode abastecimiento) · el motor de COMPRA (_compute_mp_deficit_aggregated,
alimenta /generar-oc) debe: (1) usar %-first × kg real (no cantidad_g_por_lote crudo · M71), y (2) acreditar
la CUARENTENA (igual que la pantalla) para no re-comprar MP que ya llegó y espera liberación de Calidad.
"""
import os
import sqlite3


def test_generar_oc_pct_first_y_acredita_cuarentena(app, db_clean):
    PROD = "PROD-DEFAGG-X"
    M = "MPDEFAGG01"
    db = sqlite3.connect(os.environ["DB_PATH"])
    for t in ("formula_headers", "formula_items"):
        db.execute(f"DELETE FROM {t} WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    db.execute("DELETE FROM movimientos WHERE material_id=?", (M,))
    db.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, activo) VALUES (?, 'MP DefAgg', 1)", (M,))
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 1, 1)", (PROD,))
    # % = 10, cantidad_g_por_lote CORRUPTO (5 · base 100g) → %-first debe usar el % (100g), no el 5
    db.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
               "VALUES (?,?,?,10,5)", (PROD, M, "MP DefAgg"))
    db.execute("INSERT INTO produccion_programada (producto, fecha_programada, lotes, cantidad_kg, estado, origen) "
               "VALUES (?, date('now','+10 days'), 1, 1, 'programado', 'eos_plan')", (PROD,))
    # 50g del MP en CUARENTENA (recibido, esperando Calidad) → debe restarse del déficit
    db.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, estado_lote, fecha) "
               "VALUES (?,?,?,50,?,?,date('now'))", (M, "MP DefAgg", "Entrada", "LOTE-CUAR", "CUARENTENA"))
    db.commit()
    db.close()

    from database import get_db
    with app.app_context():
        conn = get_db()
        from blueprints.programacion import _compute_mp_deficit_aggregated
        out = _compute_mp_deficit_aggregated(conn, days_ahead=90)

    row = out.get(M) or next((v for k, v in out.items() if str(k).strip().upper() == M), None)
    assert row is not None, ("el MP debe aparecer en el déficit", list(out.keys())[:25])
    # (1) %-first: total_g = 10% × 1kg × 1000 = 100 g (NO 5 del g_por_lote corrupto)
    assert abs(row['total_g'] - 100) < 1.0, ("%-first: total_g debe ser 100g, no 5", row['total_g'])
    # (2) déficit resta cuarentena: 100 − 0 stock − 0 pend − 50 cuar = 50
    assert abs(row['deficit_g'] - 50) < 1.0, ("el déficit debe acreditar la cuarentena (50g)", row.get('deficit_g'), row)
