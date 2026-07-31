"""Un fast-path puede acelerar la respuesta; NO puede cambiarla (30-jul).

El motor de ventas lee `ventas_diarias`, una tabla que un cron llena 3 veces al día para no
reparsear 16.000 órdenes en cada carga. El atajo estaba escrito como **todo o nada**:

    rows = [] if _usada_cache else c.execute(...órdenes...)

O sea: si esa tabla tenía **una sola fila** en la ventana, las órdenes ya no se consultaban nunca.
Un SKU que el cron todavía no procesó -- el caso normal de un producto **nuevo que empezó a vender
hoy** -- devolvía CERO ventas teniendo órdenes reales. Y cero ventas es velocidad cero: el motor
no lo programa. Si además el cron lo excluye por cualquier razón, es invisible para siempre.

El mismo idiom estaba copiado en TRES lugares (M45): el mapa de ventas de `auto_plan`, el cálculo
de Necesidades en `plan.py`, y -- lo más irónico -- el job que existe justamente para detectar
SKUs nuevos sin mapear, que leyendo el precalculado nunca podía ver uno nuevo.

Estos tests fijan la regla en los tres: **con la tabla precalculada llena, un SKU que no está en
ella tiene que encontrarse igual en las órdenes.**
"""
import json
import os
import sqlite3


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


SKU = 'ZZFAST-30'


def _sembrar_precalculado_lleno_sin_este_sku():
    """El escenario real: `ventas_diarias` con datos (el cron corrió) pero SIN este SKU."""
    _exec("DELETE FROM ventas_diarias WHERE sku LIKE 'ZZFAST%' OR sku='ZZOTRO-30'")
    _exec("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'ZZFAST%'")
    _exec("INSERT INTO ventas_diarias (sku, fecha, cantidad) "
          "VALUES ('ZZOTRO-30', date('now','-5 hours','-2 days'), 9)")
    # el SKU nuevo SÓLO existe en las órdenes
    _exec("INSERT INTO animus_shopify_orders (shopify_id, estado, estado_pago, sku_items, "
          "unidades_total, tags, customer_tags, creado_en) "
          "VALUES ('ZZFAST1','','paid',?,6,'','',datetime('now','-5 hours'))",
          (json.dumps([{'sku': SKU.lower(), 'qty': 6}]),))


def test_un_sku_fuera_del_precalculado_igual_se_encuentra(app, db_clean):
    """El corazón del asunto: con `ventas_diarias` llena, el SKU nuevo NO puede dar 0."""
    _sembrar_precalculado_lleno_sin_este_sku()
    with app.app_context():
        from database import get_db
        from blueprints.auto_plan import _ventas_diarias_por_sku
        ventas = _ventas_diarias_por_sku(get_db(), SKU, dias=30)
    total = sum(q for _, q in ventas)
    assert total == 6, (
        'el fast-path se comió las ventas de un SKU que el cron todavía no procesó · '
        'velocidad 0 = el motor no lo programa · %r' % ventas)


def test_el_precalculado_SIGUE_mandando_para_los_que_si_estan(app, db_clean):
    """Dientes del otro lado: el atajo tiene que seguir sirviendo, o se pierde lo que se ganó."""
    _sembrar_precalculado_lleno_sin_este_sku()
    with app.app_context():
        from database import get_db
        from blueprints.auto_plan import _ventas_diarias_por_sku
        ventas = _ventas_diarias_por_sku(get_db(), 'ZZOTRO-30', dias=30)
    assert sum(q for _, q in ventas) == 9, ventas


def test_el_detector_de_SKUs_sin_mapear_ve_los_nuevos(app, db_clean):
    """Ese job existe para encontrar SKUs que nadie mapeó. Si leyera el precalculado, un SKU
    nuevo -- justo el que busca -- sería invisible hasta que el cron lo procese."""
    _sembrar_precalculado_lleno_sin_este_sku()
    with app.app_context():
        from database import get_db
        from blueprints.auto_plan import _ventas_sku_map_orders
        m = _ventas_sku_map_orders(get_db(), dias_max=90, forzar_ordenes=True)
    assert SKU in m, ('el detector de SKUs sin mapear no ve un SKU nuevo: %r' % sorted(m)[:8])
