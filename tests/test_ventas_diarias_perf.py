"""PERF 6-jul (Sebastián) · _ventas_sku_map_orders lee la tabla ventas_diarias (precalculada por cron) en vez
de parsear el JSON de miles de órdenes. Test: con ventas_diarias poblada, la usa (fast path)."""
import os
import sqlite3
from datetime import datetime, timedelta


def test_ventas_sku_map_lee_ventas_diarias(app, db_clean):
    fecha = (datetime.utcnow() - timedelta(hours=5) - timedelta(days=5)).strftime('%Y-%m-%d')
    db = sqlite3.connect(os.environ['DB_PATH'])
    db.execute("DELETE FROM ventas_diarias")
    db.execute("INSERT INTO ventas_diarias (sku,fecha,cantidad) VALUES ('ZZFASTSKU',?,42)", (fecha,))
    db.commit(); db.close()
    from database import get_db
    with app.app_context():
        conn = get_db()
        from blueprints.auto_plan import _ventas_sku_map_orders
        m = _ventas_sku_map_orders(conn, dias_max=200)
    assert 'ZZFASTSKU' in m, ("debe leer ventas_diarias (fast path)", list(m.keys())[:10])
    assert abs(m['ZZFASTSKU'].get(fecha, 0) - 42) < 0.01, ("cantidad del fast path", m.get('ZZFASTSKU'))


def test_shopify_velocity_lee_ventas_diarias(app, db_clean):
    from datetime import datetime, timedelta
    fecha = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
    db = sqlite3.connect(os.environ['DB_PATH'])
    db.execute("DELETE FROM ventas_diarias")
    db.execute("INSERT INTO ventas_diarias (sku,fecha,cantidad) VALUES ('ZZVELSKU',?,60)", (fecha,))
    db.execute("INSERT OR IGNORE INTO sku_producto_map (sku,producto_nombre,activo) VALUES ('ZZVELSKU','ZZ VEL PROD',1)")
    db.commit(); db.close()
    from database import get_db
    with app.app_context():
        conn = get_db()
        from blueprints.programacion import _shopify_velocity
        r = _shopify_velocity(conn, days=60)
    assert r['sku_velocity'].get('ZZVELSKU', 0) > 0, ("_shopify_velocity debe leer ventas_diarias", r.get('sku_velocity'))
    assert r['total_orders'] > 0, ("total_orders debe reflejar filas de ventas_diarias", r.get('total_orders'))
