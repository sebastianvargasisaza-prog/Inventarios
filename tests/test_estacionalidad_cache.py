"""PERF · estacionalidad con cache COMPARTIDA en BD (Sebastián 15-jul).

El scan de 24 meses de órdenes (_estacionalidad_ventas) es el ÚNICO del path de Necesidades sin
fast-path a ventas_diarias → cada worker frío lo re-escanea (lentitud intermitente). La cache
compartida (plan_vmaps_cache · clave estac:24:1.30) + el cron job_refrescar_estacionalidad hacen
que NINGUNA carga vuelva a escanear. Este test verifica el round-trip real de esa cache.
"""
import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta

api = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api')
if api not in sys.path:
    sys.path.insert(0, api)

SKU = 'ESTACSKU1'
PROD = 'ESTAC PROD CACHE'


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def _limpiar():
    _exec("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PROD,))
    _exec("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'ESTAC-%'")
    _exec("DELETE FROM plan_vmaps_cache WHERE cache_key='estac:24:1.30'")


def _seed():
    _limpiar()
    _exec("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo, es_regalo) "
          "VALUES (?,?,?,1,0)", (SKU, PROD, 50.0))
    base = (datetime.utcnow() - timedelta(hours=5)).date()
    # ventas repartidas en varios meses del último año (para que el producto tenga curva)
    for i in range(0, 6):
        f = (base - timedelta(days=30 * i + 3)).isoformat()
        _exec("INSERT INTO animus_shopify_orders (shopify_id, estado, estado_pago, sku_items, creado_en) "
              "VALUES (?,?,?,?,?)",
              (f'ESTAC-{i}', 'paid', 'paid', json.dumps([{'sku': SKU, 'qty': 10}]), f + 'T10:00:00'))


def test_estacionalidad_cache_round_trip(app, db_clean):
    from blueprints import plan as P
    _seed()
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    # bajo pytest la cache está desactivada (como vmaps) → la levantamos para ejercitar el round-trip real
    _saved = os.environ.pop('PYTEST_CURRENT_TEST', None)
    try:
        P._ESTAC_CACHE.clear()
        # 1) force=True (lo que hace el cron) computa y ESCRIBE la cache compartida
        d1 = P._estacionalidad_cached(conn, 24, 1.3, force=True)
        prods1 = {p['producto'] for p in d1.get('productos', [])}
        assert PROD in prods1, "el producto sembrado debe aparecer en la estacionalidad"
        row = conn.execute("SELECT payload FROM plan_vmaps_cache WHERE cache_key='estac:24:1.30'").fetchone()
        assert row and row[0], "force=True debe dejar el blob en plan_vmaps_cache"
        assert PROD in (json.loads(row[0]).get('productos') and
                        {p['producto'] for p in json.loads(row[0])['productos']})

        # 2) borro las órdenes: un scan FRESCO daría vacío. Con la cache compartida, la próxima
        #    carga (sin force) debe LEER el blob → sigue devolviendo el producto (no re-escanea).
        _exec("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'ESTAC-%'")
        P._ESTAC_CACHE.clear()   # vaciar el nivel-1 → obliga a pegarle al nivel-2 (BD)
        d2 = P._estacionalidad_cached(conn, 24, 1.3)
        prods2 = {p['producto'] for p in d2.get('productos', [])}
        assert PROD in prods2, "la 2a carga debe venir de la cache compartida (BD), no de un scan vacío"
        assert d2.get('total_productos') == d1.get('total_productos')
    finally:
        if _saved is not None:
            os.environ['PYTEST_CURRENT_TEST'] = _saved
        P._ESTAC_CACHE.clear()
        conn.close()
        _limpiar()


def test_cron_estacionalidad_corre(app, db_clean):
    """El cron devuelve (ok, info, n) como espera el multi-cron dispatcher."""
    from blueprints.auto_plan_jobs import job_refrescar_estacionalidad
    _seed()
    try:
        ok, info, n = job_refrescar_estacionalidad(app)
        assert ok is True, info
        assert isinstance(n, int) and n >= 0
    finally:
        _limpiar()
