"""Sebastián 5-jul · Paso 2 (A) · el MOTOR del calendario cuenta el "por entrar" de Espagiria.

`_demanda_stock_gramos` (auto_plan.py) es la fuente de stock del simulador de agotamiento
`_proyectar_horizonte_2y` (el que decide CUÁNDO programar). Debe contar el stock producido en Espagiria
(stock_por_entrar) como bulk EN CAMINO → el motor NO re-programa producción de lo que el lab YA hizo.
"""
import os
import sqlite3
from datetime import date


def test_demanda_stock_gramos_cuenta_por_entrar(app, db_clean):
    PROD = "PROD-MOTOR-PENT"
    SKU = "MOTORPENT30"
    db = sqlite3.connect(os.environ["DB_PATH"])
    for t in ("formula_headers", "sku_producto_map"):
        db.execute(f"DELETE FROM {t} WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM stock_pt WHERE sku=?", (SKU,))
    db.execute("DELETE FROM stock_por_entrar WHERE sku=?", (SKU,))
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, fecha_creacion) "
               "VALUES (?, 12, 1, '2025-01-01')", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (SKU, PROD))
    # góndola Ánimus: 100 uds · POR ENTRAR (Espagiria): 300 uds producidas sin entregar
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,100,'Disponible','ANIMUS')", (SKU, PROD, "L-M"))
    db.execute("INSERT INTO stock_por_entrar (sku, uds, actualizado_at) VALUES (?,300,?)", (SKU, date.today().isoformat()))
    db.commit()
    c = db.cursor()

    from blueprints.auto_plan import _demanda_stock_gramos
    dsg = _demanda_stock_gramos(c, PROD)
    db.close()

    # el motor reporta el por-entrar: 300 uds × 30 ml = 9000 g
    assert dsg.get('por_entrar_g') == 300 * 30, ("el motor debe contar el por-entrar de Espagiria", dsg.get('por_entrar_g'))
    # góndola física = 100 × 30 = 3000 g
    assert abs(dsg['stock_shopify_g'] - 3000) < 1, dsg['stock_shopify_g']
    # stock TOTAL del motor = góndola + max(pipe=0, por_entrar=9000) = 12000 g → cuenta lo que viene de Espagiria
    assert dsg['stock_g'] >= 3000 + 9000 - 1, (
        "el stock efectivo del motor debe incluir el por-entrar (no re-produce lo del lab)",
        dsg['stock_g'], dsg['stock_shopify_g'], dsg.get('por_entrar_g'))
