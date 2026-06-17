"""17-jun · Unificación de velocidad pantalla↔motor (auditoría cálculo calendario #2/#5/#8).

La pantalla de Necesidades (_calcular_animus_dtc) y el motor del calendario
(_demanda_stock_gramos) calculaban la velocidad con DOS algoritmos distintos
(blend 30/60/90 vs regresión 30d) → la cobertura mostrada contradecía la cadencia
programada. Ahora AMBOS usan la fuente única `velocidad_blended_uds_dia`.
"""
import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta

api = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api')
if api not in sys.path:
    sys.path.insert(0, api)


def test_helper_blended_formula_deterministica(app, db_clean):
    """Fija la fórmula compartida (la misma que ve Necesidades)."""
    from blueprints.auto_plan import velocidad_blended_uds_dia as vb
    # 15/12/11 · ratio 1.25 → aceleración moderada → 0.6*15+0.4*12 = 13.8
    v, t = vb(450, 720, 990)
    assert abs(v - 13.8) < 0.01 and t == 'aceleracion_moderada'
    # 20/12/10 · ratio 1.667 → 20*1.10=22, cap a vel90*2=20
    v, t = vb(600, 720, 900)
    assert abs(v - 20.0) < 0.01 and t == 'aceleracion_fuerte'
    # 12/12/12 · estable → 12
    v, t = vb(360, 720, 1080)
    assert abs(v - 12.0) < 0.01 and t == 'estable'
    # sin histórico (v60=0)
    v, t = vb(30, 0, 0)
    assert t == 'sin_historico'


def test_motor_usa_velocidad_blended(app, db_clean):
    """_demanda_stock_gramos calcula demand_g con la velocidad blended (no la
    regresión por SKU): demand_g == velocidad_blended(v30,v60,v90) × volumen."""
    from blueprints.auto_plan import _demanda_stock_gramos, velocidad_blended_uds_dia
    PROD = 'VELU TEST PROD'
    SKU = 'VELU30'
    VOL = 50.0
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PROD,))
        conn.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'VELU-TEST-%'")
        conn.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo, es_regalo) "
                     "VALUES (?,?,?,1,0)", (SKU, PROD, VOL))
        # 10 días de ventas (5 uds/día) dentro de las 3 ventanas → v30=v60=v90=50
        base = (datetime.utcnow() - timedelta(hours=5)).date()
        for i in range(1, 11):
            f = (base - timedelta(days=i)).isoformat()
            conn.execute(
                "INSERT INTO animus_shopify_orders (shopify_id, estado, estado_pago, sku_items, creado_en) "
                "VALUES (?,?,?,?,?)",
                (f'VELU-TEST-{i}', 'paid', 'paid', json.dumps([{'sku': SKU, 'qty': 5}]), f + 'T10:00:00'))
        conn.commit()
        d = _demanda_stock_gramos(conn.cursor(), PROD)
        # ventas reales que ve el motor (mismas 3 ventanas)
        from blueprints.auto_plan import _ventas_diarias_por_sku
        cur = conn.cursor()
        v30 = sum(q for _, q in _ventas_diarias_por_sku(cur, SKU, dias=30))
        v60 = sum(q for _, q in _ventas_diarias_por_sku(cur, SKU, dias=60))
        v90 = sum(q for _, q in _ventas_diarias_por_sku(cur, SKU, dias=90))
    finally:
        conn.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PROD,))
        conn.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'VELU-TEST-%'")
        conn.commit(); conn.close()
    assert v30 == 50 and v60 == 50 and v90 == 50, f"seed mal: {v30}/{v60}/{v90}"
    vel_esperada, _ = velocidad_blended_uds_dia(v30, v60, v90, None, 60)
    assert vel_esperada > 0
    # demand_g del motor == velocidad blended × volumen (1 solo SKU → vol_pond=VOL)
    assert abs(d['demand_g'] - vel_esperada * VOL) < 0.5, \
        f"el motor NO usa la velocidad blended: demand_g={d['demand_g']} esperado={vel_esperada*VOL}"
