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
