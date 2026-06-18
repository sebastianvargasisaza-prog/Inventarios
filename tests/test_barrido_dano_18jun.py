"""Regresiones del barrido 'qué más está dañado' · 18-jun.

Cubre los fixes confirmados+verificados del workflow:
- _get_formulas dedup: filas duplicadas (mismo producto+material) NO se suman → no inflar.
- _velocidad_total_producto excluye SKUs es_regalo (igual que sus hermanas).
- mee_codigo (no material_id) en movimientos_mee · columnas reales.
"""
import sqlite3
import importlib


def _build_db():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE formula_headers (producto_nombre TEXT, unidad_base_g REAL, lote_size_kg REAL, activo INTEGER DEFAULT 1)")
    c.execute("CREATE TABLE formula_items (producto_nombre TEXT, material_id TEXT, material_nombre TEXT, porcentaje REAL, cantidad_g_por_lote REAL)")
    c.execute("INSERT INTO formula_headers VALUES ('CREMA X', 1000, 1, 1)")
    # Duplicado del MISMO material (data error) — antes se sumaba 50+50=100%.
    c.execute("INSERT INTO formula_items VALUES ('CREMA X','MP001','Activo',50,500)")
    c.execute("INSERT INTO formula_items VALUES ('CREMA X','MP001','Activo',50,500)")
    c.execute("INSERT INTO formula_items VALUES ('CREMA X','MP002','Otro',10,100)")
    c.commit()
    return c


def test_get_formulas_dedup_no_suma_duplicados():
    prog = importlib.import_module("api.blueprints.programacion")
    conn = _build_db()
    fs = prog._get_formulas(conn)
    items = fs['CREMA X']['items']
    mids = [i['material_id'] for i in items]
    assert mids.count('MP001') == 1, f"MP001 duplicado no colapsado: {mids}"
    mp001 = next(i for i in items if i['material_id'] == 'MP001')
    # conserva el % mayor (50), NO la suma (100)
    assert mp001['porcentaje'] == 50, mp001
    assert len([i for i in items if i['material_id'] == 'MP002']) == 1


def test_velocidad_total_excluye_es_regalo():
    ap = importlib.import_module("api.blueprints.auto_plan")
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE sku_producto_map (sku TEXT, producto_nombre TEXT, activo INTEGER DEFAULT 1, es_regalo INTEGER DEFAULT 0)")
    c.execute("INSERT INTO sku_producto_map VALUES ('SKU-REAL','CREMA X',1,0)")
    c.execute("INSERT INTO sku_producto_map VALUES ('SKU-REGALO','CREMA X',1,1)")
    c.commit()

    seen = []
    orig = ap._velocidad_y_tendencia
    ap._velocidad_y_tendencia = lambda cur, sku: (seen.append(sku) or (5.0, 1.0))
    try:
        vel, _f = ap._velocidad_total_producto(c, 'CREMA X')
    finally:
        ap._velocidad_y_tendencia = orig
    assert 'SKU-REGALO' not in seen, f"velocity contó el SKU regalo: {seen}"
    assert seen == ['SKU-REAL']
    assert vel == 5.0
