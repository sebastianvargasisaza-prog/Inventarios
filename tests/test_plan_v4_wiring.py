"""Programación v4 · Fase 1 · wiring de la DECISIÓN al motor (Sebastián 15-jul).

La decisión que el usuario guarda en el panel `/planta/programar`
(`sku_planeacion_config`: kg_objetivo_lote, horizonte_dias, cadencia_dias, mix_mode)
debe cambiar lo que el generador `_generar_plan_desde_hoy` programa. Cada pieza va con
default = comportamiento actual (nada cambia hasta que el usuario fije la decisión).

Pieza 1: kg_objetivo_lote manda sobre formula_headers.lote_size_kg.
"""
import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta

api = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api')
if api not in sys.path:
    sys.path.insert(0, api)

PROD = 'V4WIRE KG PROD'
SKU = 'V4WKG30'


def _seed(kg_objetivo=None, lote_size=10, horizonte=None, cadencia=None):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        _cleanup_conn(conn)
        conn.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo, es_regalo) "
                     "VALUES (?,?,?,1,0)", (SKU, PROD, 50.0))
        # 10 días de ventas (5 uds/día) → demanda > 0 (necesaria para que el generador cree la cadena)
        base = (datetime.utcnow() - timedelta(hours=5)).date()
        for i in range(1, 11):
            f = (base - timedelta(days=i)).isoformat()
            conn.execute("INSERT INTO animus_shopify_orders (shopify_id, estado, estado_pago, sku_items, creado_en) "
                         "VALUES (?,?,?,?,?)",
                         (f'V4WKG-{i}', 'paid', 'paid', json.dumps([{'sku': SKU, 'qty': 5}]), f + 'T10:00:00'))
        conn.execute("INSERT INTO formula_headers (producto_nombre, unidad_base_g, lote_size_kg, activo) "
                     "VALUES (?,1000,?,1)", (PROD, lote_size))
        cols = ['producto_nombre', 'activo']
        vals = [PROD, 1]
        for col, v in (('kg_objetivo_lote', kg_objetivo), ('horizonte_dias', horizonte),
                       ('cadencia_dias', cadencia)):
            if v is not None:
                cols.append(col); vals.append(v)
        conn.execute("INSERT INTO sku_planeacion_config (" + ','.join(cols) + ") VALUES (" +
                     ','.join(['?'] * len(cols)) + ")", vals)
        conn.commit()
    finally:
        conn.close()


def _cleanup_conn(conn):
    for t, col in [('sku_producto_map', 'producto_nombre'), ('formula_headers', 'producto_nombre'),
                   ('sku_planeacion_config', 'producto_nombre'), ('produccion_programada', 'producto')]:
        conn.execute(f"DELETE FROM {t} WHERE {col}=?", (PROD,))
    conn.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'V4WKG-%'")


def _cleanup():
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        _cleanup_conn(conn); conn.commit()
    finally:
        conn.close()


def _lotes_kg():
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        return [r[0] for r in conn.execute(
            "SELECT cantidad_kg FROM produccion_programada WHERE producto=? AND estado='pendiente'",
            (PROD,)).fetchall()]
    finally:
        conn.close()


def _run():
    from blueprints.plan import _generar_plan_desde_hoy
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        _generar_plan_desde_hoy(conn)
    finally:
        conn.close()


def test_kg_objetivo_manda(app, db_clean):
    _seed(kg_objetivo=25, lote_size=10)
    try:
        _run()
        kgs = _lotes_kg()
        assert kgs, "el generador debe crear lotes del producto con venta"
        assert all(abs(k - 25) < 0.01 for k in kgs), \
            f"debe usar kg_objetivo=25 (decisión), no lote_size=10: {kgs}"
    finally:
        _cleanup()


def test_sin_kg_objetivo_usa_lote_size(app, db_clean):
    _seed(kg_objetivo=None, lote_size=10)
    try:
        _run()
        kgs = _lotes_kg()
        assert kgs, "el generador debe crear lotes del producto con venta"
        assert all(abs(k - 10) < 0.01 for k in kgs), \
            f"sin decisión debe caer a lote_size=10 (comportamiento actual): {kgs}"
    finally:
        _cleanup()


def _n_lotes():
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM produccion_programada WHERE producto=? AND estado='pendiente'",
            (PROD,)).fetchone()[0]
    finally:
        conn.close()


def test_horizonte_corto_acorta_la_cadena(app, db_clean):
    # lote 10kg, venta 250 g/día → cadencia ~40d. Con horizonte 30d, 1 solo lote cubre el
    # horizonte (emite_uno). Sin decisión (default 730) → cadena larga (muchos lotes).
    _seed(lote_size=10, horizonte=30)
    try:
        _run()
        assert _n_lotes() == 1, "con horizonte 30d y cadencia ~40d debe emitir 1 solo lote"
    finally:
        _cleanup()
    _seed(lote_size=10, horizonte=None)
    try:
        _run()
        assert _n_lotes() > 3, "sin decisión (horizonte 730) debe encadenar muchos lotes"
    finally:
        _cleanup()


def test_cadencia_forzada_cambia_el_ritmo(app, db_clean):
    # natural: lote 10kg, venta 250 g/día → ~40d. En un horizonte de 60d:
    #   - ritmo forzado 20d → off 0,20,40,60 = más lotes
    #   - sin decisión → off 0,40 = 2 lotes
    _seed(lote_size=10, horizonte=60, cadencia=20)
    try:
        _run(); n_forzada = _n_lotes()
    finally:
        _cleanup()
    _seed(lote_size=10, horizonte=60)
    try:
        _run(); n_natural = _n_lotes()
    finally:
        _cleanup()
    assert n_forzada > n_natural, \
        f"la cadencia forzada (20d) debe dar más lotes que la natural (~40d): {n_forzada} vs {n_natural}"
    assert n_natural == 2, f"natural en 60d ~40d = 2 lotes: {n_natural}"
