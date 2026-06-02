"""Sebastián 1-jun-2026 (P0 · frena producción): al producir decía 'N-acetil glucosamina ·
Hay 0g' aunque bodega tenía 600g bajo otro código (MP con ID distinto entre fórmula y
bodega). _resolver_material_bodega resuelve fórmula→bodega vía bridge / nombre; la
validación de stock encuentra el inventario real. MPs que ya funcionaban quedan idénticos."""
import os, sqlite3


def _seed_prod(conn, producto, form_mid, form_nombre, g_por_lote=140):
    conn.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (producto,))
    conn.execute("DELETE FROM formula_items WHERE producto_nombre=?", (producto,))
    conn.execute("DELETE FROM produccion_programada WHERE producto=?", (producto,))
    # formula_items.material_id tiene FK a maestro_mps activo → sembrar la entrada
    # de FÓRMULA (distinta de la de bodega · ese ES el caso real de los 116 MPs).
    conn.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) VALUES (?,?,?,1)",
                 (form_mid, form_nombre, form_nombre))
    conn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 10, 1)", (producto,))
    conn.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
                 "VALUES (?, ?, ?, 0, ?)", (producto, form_mid, form_nombre, g_por_lote))
    cur = conn.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, estado, origen) "
                       "VALUES (?, date('now','-5 hours','+3 days'), 10, 1, 'programado', 'eos_plan')", (producto,))
    return cur.lastrowid


def test_resuelve_via_bridge(app, db_clean):
    with app.app_context():
        from database import get_db
        from blueprints.programacion import _calcular_mp_consumo_produccion, _validar_stock_para_produccion
        conn = get_db()
        # bodega: 600g bajo BODGLU; fórmula usa FORMGLU (id distinto) · bridge los une
        conn.execute("DELETE FROM movimientos WHERE material_id IN ('BODGLU','FORMGLU')")
        conn.execute("DELETE FROM mp_formula_bridge WHERE formula_material_id='FORMGLU'")
        conn.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote) "
                     "VALUES ('BODGLU','N-Acetyl Glucosamina',600,'Entrada','2026-06-01','LBG-1','VIGENTE')")
        conn.execute("INSERT INTO mp_formula_bridge (formula_material_id, bodega_material_id, activo) VALUES ('FORMGLU','BODGLU',1)")
        pid = _seed_prod(conn, "ZZGLU BRIDGE", "FORMGLU", "N-acetil glucosamina")
        conn.commit()
        mps, meta = _calcular_mp_consumo_produccion(conn.cursor(), pid)
        assert mps and mps[0]['codigo_mp'] == 'BODGLU', mps   # resuelto a bodega
        faltantes = _validar_stock_para_produccion(conn.cursor(), mps)
        assert faltantes == [], faltantes                      # 600g >= 140g → no falta


def test_resuelve_via_nombre(app, db_clean):
    with app.app_context():
        from database import get_db
        from blueprints.programacion import _calcular_mp_consumo_produccion, _validar_stock_para_produccion
        conn = get_db()
        # sin bridge · maestro+movimientos bajo BODGLU2 con nombre que normaliza igual
        conn.execute("DELETE FROM movimientos WHERE material_id IN ('BODGLU2','FORMGLU2')")
        conn.execute("DELETE FROM maestro_mps WHERE codigo_mp='BODGLU2'")
        conn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
                     "VALUES ('BODGLU2','GLUCOSAMINA TEST','Glucosamina Test',1)")
        conn.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote) "
                     "VALUES ('BODGLU2','Glucosamina Test',600,'Entrada','2026-06-01','LBG-2','VIGENTE')")
        pid = _seed_prod(conn, "ZZGLU NOMBRE", "FORMGLU2", "Glucosamina Test")
        conn.commit()
        mps, meta = _calcular_mp_consumo_produccion(conn.cursor(), pid)
        assert mps and mps[0]['codigo_mp'] == 'BODGLU2', mps   # resuelto por nombre
        assert _validar_stock_para_produccion(conn.cursor(), mps) == []


def test_mp_que_ya_funciona_no_cambia(app, db_clean):
    """SEGURIDAD: si el id de fórmula YA tiene movimientos, el resolver lo deja igual."""
    with app.app_context():
        from database import get_db
        from blueprints.programacion import _calcular_mp_consumo_produccion
        conn = get_db()
        conn.execute("DELETE FROM movimientos WHERE material_id='BODOK1'")
        conn.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote) "
                     "VALUES ('BODOK1','MP OK',600,'Entrada','2026-06-01','LOK-1','VIGENTE')")
        pid = _seed_prod(conn, "ZZGLU OK", "BODOK1", "MP OK")
        conn.commit()
        mps, _ = _calcular_mp_consumo_produccion(conn.cursor(), pid)
        assert mps and mps[0]['codigo_mp'] == 'BODOK1', mps   # sin cambio
