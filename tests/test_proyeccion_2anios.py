"""16-jun · Plan rodante a 2 años (_proyectar_horizonte_2y).

Cada producto se proyecta anclado a su venta en Shopify (velocidad + tendencia) y a
su stock EFECTIVO = Shopify disponible + pipeline (lo producido ≤7d que aún no entra
a Shopify). Automático (cron 5:10), idempotente, NO toca lo ejecutado ni lo Fijo.
"""
import os
import sqlite3
import sys
import datetime as _dt


def _api():
    api_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api")
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)


def _seed_producto(producto='PROD PROY 2A', sku='SKU-PROY', vel=10, stock=50,
                   lote_kg=30, factor_g=30, dias_venta=30):
    """Siembra un producto vendible: ventas_diarias (velocidad), mapa SKU, stock
    Shopify, presentación (factor g/u), config de planeación y fórmula (lote_size)."""
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        # Auto-limpieza (db_clean no resetea estas tablas de config) → tests aislados
        conn.execute("CREATE TABLE IF NOT EXISTS ventas_diarias (sku TEXT, fecha TEXT, cantidad REAL)")
        for q, p in [("DELETE FROM ventas_diarias WHERE sku=?", (sku,)),
                     ("DELETE FROM sku_producto_map WHERE sku=?", (sku,)),
                     ("DELETE FROM stock_pt WHERE sku=?", (sku,)),
                     ("DELETE FROM sku_planeacion_config WHERE producto_nombre=?", (producto,)),
                     ("DELETE FROM formula_headers WHERE producto_nombre=?", (producto,)),
                     ("DELETE FROM produccion_programada WHERE producto=?", (producto,))]:
            try:
                conn.execute(q, p)
            except Exception:
                pass
        hoy = (_dt.datetime.utcnow() - _dt.timedelta(hours=5)).date()
        for i in range(dias_venta):
            f = (hoy - _dt.timedelta(days=i)).isoformat()
            conn.execute("INSERT INTO ventas_diarias (sku,fecha,cantidad) VALUES (?,?,?)", (sku, f, vel))
        conn.execute("INSERT OR REPLACE INTO sku_producto_map (sku,producto_nombre,activo) VALUES (?,?,1)",
                     (sku, producto))
        conn.execute("INSERT INTO stock_pt (sku,descripcion,unidades_disponible,empresa,estado) "
                     "VALUES (?,?,?,?,?)", (sku, producto, stock, 'ANIMUS', 'activo'))
        # factor g/u sale del fallback por categoría ('suero' → 30 g/u),
        # consistente con lote_kg=30 → 1000 u/lote (evita NOT NULLs de presentaciones).
        conn.execute("INSERT INTO sku_planeacion_config (producto_nombre,categoria,cadencia_dias,"
                     "cobertura_target_dias,cobertura_min_dias,cobertura_max_dias,merma_pct,prioridad,activo) "
                     "VALUES (?,?,?,?,?,?,?,?,1)", (producto, 'suero', 30, 60, 20, 90, 5, 1))
        conn.execute("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,?,1)",
                     (producto, lote_kg))
        conn.commit()
    finally:
        conn.close()


def _eos_proyeccion(producto='PROD PROY 2A'):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        return conn.execute(
            "SELECT id, fecha_programada, observaciones FROM produccion_programada "
            "WHERE producto=? AND origen='eos_proyeccion' AND COALESCE(estado,'')<>'cancelado' "
            "ORDER BY fecha_programada", (producto,)).fetchall()
    finally:
        conn.close()


def test_proyeccion_genera_lotes_futuros(app, db_clean):
    _api()
    from blueprints.plan import _proyectar_horizonte_2y
    from database import get_db
    _seed_producto()
    with app.app_context():
        res = _proyectar_horizonte_2y(get_db(), dias=200, usuario='test')
    assert res['creados'] >= 1, res
    lotes = _eos_proyeccion()
    assert len(lotes) == res['creados']
    hoy = (_dt.datetime.utcnow() - _dt.timedelta(hours=5)).date().isoformat()
    assert all(l[1][:10] >= hoy for l in lotes)   # todos futuros


def test_proyeccion_idempotente(app, db_clean):
    _api()
    from blueprints.plan import _proyectar_horizonte_2y
    from database import get_db
    _seed_producto()
    with app.app_context():
        r1 = _proyectar_horizonte_2y(get_db(), dias=200, usuario='test')
        r2 = _proyectar_horizonte_2y(get_db(), dias=200, usuario='test')
    # segunda corrida borra la previa y rehace → NO se acumula
    assert r2['creados'] == r1['creados']
    assert len(_eos_proyeccion()) == r1['creados']


def test_proyeccion_incluye_pipeline(app, db_clean):
    """Lo ya producido ≤7d (aún no en Shopify) cuenta como stock efectivo ANTES de
    proponer. Debe reflejarse en el cálculo (obs muestra el pipeline en unidades)."""
    _api()
    from blueprints.plan import _proyectar_horizonte_2y
    from database import get_db
    _seed_producto(stock=50)
    # producción real reciente: 30kg ejecutada hace 2 días → 30000/30 = 1000 u en pipeline
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    f2 = (_dt.datetime.utcnow() - _dt.timedelta(hours=5) - _dt.timedelta(days=2)).date().isoformat()
    conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,"
                 "fin_real_at,inicio_real_at) VALUES (?,?,?,?,?,1,?,?)",
                 ('PROD PROY 2A', f2, 'completado', 'eos_retroactivo', 30, f2, f2))
    conn.commit(); conn.close()
    with app.app_context():
        res = _proyectar_horizonte_2y(get_db(), dias=300, usuario='test')
    assert res['creados'] >= 1
    lotes = _eos_proyeccion()
    # el pipeline (1000 u) quedó contado en el stock efectivo (visible en la obs)
    assert any('pipeline 1000' in (l[2] or '') for l in lotes), [l[2] for l in lotes][:3]


def test_proyeccion_sin_ventas_no_planea(app, db_clean):
    _api()
    from blueprints.plan import _proyectar_horizonte_2y
    from database import get_db
    _seed_producto(producto='PROD SIN VENTA', sku='SKU-SV', vel=0, dias_venta=0, stock=10)
    with app.app_context():
        _proyectar_horizonte_2y(get_db(), dias=200, usuario='test')
    assert len(_eos_proyeccion('PROD SIN VENTA')) == 0   # sin venta → no inventa demanda


def test_proyeccion_no_toca_fijo_ni_ejecutado(app, db_clean):
    _api()
    from blueprints.plan import _proyectar_horizonte_2y
    from database import get_db
    _seed_producto()
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    fut = ((_dt.datetime.utcnow() - _dt.timedelta(hours=5)).date() + _dt.timedelta(days=15)).isoformat()
    conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes) "
                 "VALUES (?,?,?,?,?,1)", ('PROD PROY 2A', fut, 'pendiente', 'eos_plan', 30))
    fijo = conn.execute("SELECT id FROM produccion_programada WHERE origen='eos_plan' AND producto='PROD PROY 2A'").fetchone()[0]
    ej = ((_dt.datetime.utcnow() - _dt.timedelta(hours=5)).date() - _dt.timedelta(days=3)).isoformat()
    conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,inicio_real_at) "
                 "VALUES (?,?,?,?,?,1,?)", ('PROD PROY 2A', ej, 'en_proceso', 'eos_proyeccion', 30, ej))
    ejec = conn.execute("SELECT id FROM produccion_programada WHERE origen='eos_proyeccion' AND inicio_real_at IS NOT NULL").fetchone()[0]
    conn.commit(); conn.close()
    with app.app_context():
        _proyectar_horizonte_2y(get_db(), dias=200, usuario='test')
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        # Fijo intacto
        assert conn.execute("SELECT estado FROM produccion_programada WHERE id=?", (fijo,)).fetchone()[0] == 'pendiente'
        # eos_proyeccion ejecutado NO se borra (idempotencia solo borra NO ejecutado)
        assert conn.execute("SELECT estado FROM produccion_programada WHERE id=?", (ejec,)).fetchone()[0] == 'en_proceso'
    finally:
        conn.close()
