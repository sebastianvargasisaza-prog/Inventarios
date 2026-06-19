"""Envase del checklist auto-poblado desde presentaciones · 18-jun (M55 alineación).

El DESCUENTO de envases (_descontar_mee_envasado) solo consume items del checklist con
mee_codigo_asignado. Antes el checklist se creaba con ese campo NULL → el operario debía
asignarlo a mano; si olvidaba, el envase NO se descontaba ≠ lo que la COMPRA planeó por
producto_presentaciones. Ahora el item de envase primario se pre-llena con el envase de
presentaciones (misma fuente que la compra) → compra == descuento.
"""
import os
import sqlite3
import importlib
import sys


def _api():
    api_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api")
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)


def test_checklist_envase_se_prellena_desde_presentaciones(app, db_clean):
    _api()
    prog = importlib.import_module("blueprints.programacion")
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    prod = "ZZ CHK ENV PROD"
    envase = "ENV-CHK-ZZ-30ML"
    try:
        conn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, volumen_unitario_ml) "
                     "VALUES (?,1,1,30)", (prod,))
        conn.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,stock_actual,stock_minimo) "
                     "VALUES (?, 'Frasco CHK 30ml','Envase',0,0)", (envase,))
        conn.execute("INSERT INTO producto_presentaciones "
                     "(producto_nombre,presentacion_codigo,etiqueta,volumen_ml,envase_codigo,es_default,activo) "
                     "VALUES (?, 'CHK-30','30 ml',30,?,1,1)", (prod, envase))
        cur = conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
                           "VALUES (?, date('now','-5 hours','+5 days'),1,'pendiente',3,'eos_plan')", (prod,))
        pid = cur.lastrowid
        conn.commit()
        # Generar el checklist (sin MPs · solo envases para el caso)
        prog._generar_checklist_produccion(conn.cursor(), pid, prod, '2026-06-25', 3.0,
                                           generar_mps=False, usuario='test')
        conn.commit()
        row = conn.execute(
            "SELECT mee_codigo_asignado FROM produccion_checklist "
            "WHERE produccion_id=? AND item_tipo='envase_primario'", (pid,)).fetchone()
        assert row is not None, "debe crearse el item de envase primario"
        assert (row[0] or '').upper() == envase, \
            f"el envase primario debe pre-llenarse desde presentaciones · got {row[0]}"
    finally:
        conn.close()
