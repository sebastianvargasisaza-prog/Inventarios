"""17-jun · Auditoría cálculo calendario · PENDIENTE #9 resuelto.

_demanda_stock_gramos y _stock_actual_pt sumaban stock_pt CRUDO (sin
estado='Disponible' ni la regla CC-manda-sobre-SHOPIFY) → doble-contaban
CC+Shopify e incluían snapshots 'Ajustado' viejos → stock inflado 5-10× →
el motor del calendario veía cobertura falsa y discrepaba de Necesidades.
Ahora ambos usan el resolver canónico _resolved_stock_por_sku (M1/M2).
"""
import os
import sys
import sqlite3

api = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api')
if api not in sys.path:
    sys.path.insert(0, api)


def _seed():
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("DELETE FROM sku_producto_map WHERE producto_nombre='CALC RESOLVER PROD'")
        conn.execute("DELETE FROM stock_pt WHERE sku='CALCRES30'")
        conn.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) "
                     "VALUES ('CALCRES30','CALC RESOLVER PROD',150,1)")
        # Liberación CC (lote real, Disponible) = autoridad
        conn.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
                     "VALUES ('CALCRES30','x','L-REAL-1',200,'Disponible','ANIMUS')")
        # Snapshot Shopify del MISMO sku (Disponible) → NO debe sumarse (CC manda)
        conn.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
                     "VALUES ('CALCRES30','x','SHOPIFY-2026-06-08',200,'Disponible','ANIMUS')")
        # Snapshot Shopify viejo 'Ajustado' → NUNCA debe contarse
        conn.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
                     "VALUES ('CALCRES30','x','SHOPIFY-2026-06-01',999,'Ajustado','ANIMUS')")
        conn.commit()
    finally:
        conn.close()


def _cleanup():
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("DELETE FROM sku_producto_map WHERE producto_nombre='CALC RESOLVER PROD'")
        conn.execute("DELETE FROM stock_pt WHERE sku='CALCRES30'")
        conn.commit()
    finally:
        conn.close()


def test_demanda_stock_gramos_usa_resolver_no_doble_cuenta(app, db_clean):
    from blueprints.auto_plan import _demanda_stock_gramos
    _seed()
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        d = _demanda_stock_gramos(conn.cursor(), 'CALC RESOLVER PROD')
    finally:
        conn.close()
        _cleanup()
    uds = d['skus'][0]['unidades']
    # CC manda (200) · NO 400 (CC+Shopify) ni 1199 (+ Ajustado viejo)
    assert uds == 200, f"stock debe ser 200 (CC manda), no doble-contar: {d}"
    # stock físico (sin pipeline) = 200 × 150 ml = 30.000 g
    assert abs(d['stock_shopify_g'] - 30000) < 1, d


def test_stock_actual_pt_usa_resolver(app, db_clean):
    from blueprints.auto_plan import _stock_actual_pt
    _seed()
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        total = _stock_actual_pt(conn.cursor(), 'CALC RESOLVER PROD')
    finally:
        conn.close()
        _cleanup()
    assert total == 200, f"_stock_actual_pt debe dar 200 (resolver), no 400/1199: {total}"
