"""Migración 238 · los 8 tonos de Blush Balm (SKU Shopify) mapean a 'Blush Balm'
(Sebastián 12-jun). Así sus ventas SUMAN al bulk -> aparece en necesidades y se
solicita la producción. El desglose por tono se maneja en la capa de tonos.
"""
import os
import sys
import sqlite3

SKUS = ['BB101', 'BB201', 'BB301', 'BB401', 'BB501', 'BB601', 'BB701', 'BB801']


def _load_migrations():
    api_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api")
    added = api_dir not in sys.path
    if added:
        sys.path.insert(0, api_dir)
    try:
        from database import MIGRATIONS
        return MIGRATIONS
    finally:
        if added:
            try:
                sys.path.remove(api_dir)
            except ValueError:
                pass


def _mig238_stmts():
    for ver, _d, stmts in _load_migrations():
        if ver == 238:
            return stmts
    raise AssertionError("migración 238 no encontrada")


def _fresh():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE sku_producto_map (sku TEXT PRIMARY KEY, "
                 "producto_nombre TEXT NOT NULL, activo INTEGER DEFAULT 1)")
    return conn


def _apply(conn):
    for s in _mig238_stmts():
        conn.execute(s)
    conn.commit()


def test_mig238_mapea_8_tonos_a_blush_balm():
    conn = _fresh(); _apply(conn)
    rows = dict(conn.execute(
        "SELECT sku, producto_nombre FROM sku_producto_map WHERE activo=1").fetchall())
    for sku in SKUS:
        assert rows.get(sku) == 'Blush Balm', f"{sku} debe mapear a Blush Balm"
    assert len(SKUS) == 8


def test_mig238_corrige_mapeo_previo_equivocado_y_es_idempotente():
    conn = _fresh()
    # BB201 ya estaba mapeado MAL a otro producto -> debe quedar en Blush Balm
    conn.execute("INSERT INTO sku_producto_map (sku, producto_nombre, activo) "
                 "VALUES ('BB201','Otro Producto',1)")
    conn.commit()
    _apply(conn)
    _apply(conn)  # idempotente
    val = conn.execute("SELECT producto_nombre FROM sku_producto_map WHERE sku='BB201'").fetchone()[0]
    assert val == 'Blush Balm'
    # no se duplica (sku es PK)
    n = conn.execute("SELECT COUNT(*) FROM sku_producto_map WHERE sku='BB201'").fetchone()[0]
    assert n == 1
