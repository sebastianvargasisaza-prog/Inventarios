"""Sebastián 4-jul · P1-B (audit) · el pipeline del MOTOR de proyección debe restar la porción NO-Animus.

_demanda_stock_gramos (auto_plan · alimenta _proyectar_horizonte_2y y la generación de lotes) sumaba el
bulk COMPLETO de un lote reciente al stock de Animus, sin restar kg_otro_cliente/B2B → cobertura inflada →
menos lotes → sub-compra de MP, justo para productos con reserva a otro cliente (RENOVA 80% otro).
"""
import os
import sqlite3


def test_pipeline_demanda_resta_kg_otro(app, db_clean):
    from blueprints.auto_plan import _demanda_stock_gramos
    PROD = "PROD-PIPE-ANIMUS"
    SKU = "PIPEANIMUS30"
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)",
               (SKU, PROD))
    # lote reciente (fin_real hace 2 días · dentro de la ventana 7d de pipeline) · 50kg total, 30 para otro
    db.execute(
        """INSERT INTO produccion_programada
           (producto, fecha_programada, cantidad_kg, kg_otro_cliente, estado, origen, lotes, fin_real_at)
           VALUES (?, date('now','-2 days','-5 hours'), 50, 30, 'completado', 'eos_plan', 1,
                   datetime('now','-2 days'))""",
        (PROD,))
    db.commit()

    d = _demanda_stock_gramos(db.cursor(), PROD)
    db.close()
    # pipe_g debe reflejar SOLO la porción Animus: (50 - 30) kg × 1000 = 20.000 g · NO 50.000
    assert abs(d["pipe_g"] - 20000.0) < 500, (
        "el pipeline del motor debe restar kg_otro_cliente (solo la porción Animus cubre demanda Animus)",
        d["pipe_g"])


def test_pipeline_motor_por_fecha_fisica_no_registro(app, db_clean):
    """P1 (Fable 5) · un lote FÍSICO de junio (fecha_programada vieja >7d) pero REGISTRADO esta semana
    (fin_real_at reciente) NO debe contar como pipe del motor (ya está en góndola/stock_g) → evita el
    doble-conteo clase NOVA PHA en el motor de proyección (→ sub-compra)."""
    from blueprints.auto_plan import _demanda_stock_gramos
    PROD = "PROD-PIPE-MOTOR-FIS"
    SKU = "PIPEMOTORFIS30"
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)",
               (SKU, PROD))
    # físico hace 20 días (>7 → ya en góndola) pero fin_real_at (registro) hace 1 día
    db.execute(
        """INSERT INTO produccion_programada
           (producto, fecha_programada, cantidad_kg, estado, origen, lotes, fin_real_at)
           VALUES (?, date('now','-20 days','-5 hours'), 50, 'completado', 'eos_plan', 1,
                   datetime('now','-1 days'))""",
        (PROD,))
    db.commit()
    d = _demanda_stock_gramos(db.cursor(), PROD)
    db.close()
    # NO debe contarse como pipe (físico >7d): pipe_g ≈ 0, NO 50.000
    assert d["pipe_g"] < 1000, (
        "un lote físico de junio registrado tarde NO debe contar como pipe del motor (ya está en góndola)",
        d["pipe_g"])
