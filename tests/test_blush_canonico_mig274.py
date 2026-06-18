"""Migración 274 · corrige el canónico de Blush Balm.

La mig 238 mapeó los SKUs de Shopify a 'Blush Balm' (minúscula · fórmula activo=0,
incompleta). La 274 los re-apunta a 'BLUSH BALM' (mayúscula · completa, activa, =Excel)
SOLO si esa fórmula existe y está activa. Idempotente y no destructivo.
"""
import os
import sys
import sqlite3

SKUS = ['BB101', 'BB201', 'BB301', 'BB401', 'BB501', 'BB601', 'BB701', 'BB801', 'BBM']


def _stmts(ver):
    api_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api")
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)
    from database import MIGRATIONS
    for v, _d, s in MIGRATIONS:
        if v == ver:
            return s
    raise AssertionError(f"migración {ver} no encontrada")


def _fresh(con_blush_mayus_activo=True):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE sku_producto_map (sku TEXT PRIMARY KEY, "
                 "producto_nombre TEXT NOT NULL, activo INTEGER DEFAULT 1)")
    conn.execute("CREATE TABLE formula_headers (producto_nombre TEXT, activo INTEGER DEFAULT 1)")
    if con_blush_mayus_activo:
        conn.execute("INSERT INTO formula_headers VALUES ('BLUSH BALM', 1)")
    conn.execute("INSERT INTO formula_headers VALUES ('Blush Balm', 0)")
    # BBM (bulk/regalo) ya existía mapeado a 'Blush Balm' antes de mig 238 (que solo crea BB101..BB801).
    conn.execute("INSERT INTO sku_producto_map (sku, producto_nombre, activo) VALUES ('BBM','Blush Balm',1)")
    conn.commit()
    return conn


def _apply(conn, ver):
    for s in _stmts(ver):
        try:
            conn.execute(s)
        except sqlite3.OperationalError:
            pass  # statements de otras tablas no presentes en este harness aislado
    conn.commit()


def test_mig274_remapea_a_blush_balm_mayuscula():
    conn = _fresh()
    _apply(conn, 238)   # mapea a 'Blush Balm' minúscula
    _apply(conn, 274)   # corrige a 'BLUSH BALM'
    rows = dict(conn.execute("SELECT sku, producto_nombre FROM sku_producto_map").fetchall())
    for sku in SKUS:
        assert rows.get(sku) == 'BLUSH BALM', f"{sku} debe quedar en 'BLUSH BALM', quedó {rows.get(sku)}"


def test_mig274_idempotente():
    conn = _fresh()
    _apply(conn, 238)
    _apply(conn, 274)
    _apply(conn, 274)  # segunda vez no cambia nada
    n = conn.execute("SELECT COUNT(*) FROM sku_producto_map WHERE producto_nombre='BLUSH BALM'").fetchone()[0]
    assert n == len(SKUS)


def test_mig274_no_remapea_si_no_existe_canonico_activo():
    # Defensa: si 'BLUSH BALM' no existe/activo, NO toca las ventas (evita huérfanos).
    conn = _fresh(con_blush_mayus_activo=False)
    _apply(conn, 238)
    _apply(conn, 274)
    val = conn.execute("SELECT producto_nombre FROM sku_producto_map WHERE sku='BB101'").fetchone()[0]
    assert val == 'Blush Balm', "sin canónico activo no debe remapear"
