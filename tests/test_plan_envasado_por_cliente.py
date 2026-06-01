"""Sebastián 1-jun-2026: el plan de envasado debe decir cuántas uds de cada envase
(10ml/30ml) para Animus y cuántas de 30ml para Kelly. DTC = composición − B2B por ml."""
import os, sqlite3


def test_plan_envasado_por_cliente_dtc_menos_b2b(app, db_clean):
    producto = "ZZENV TRX TEST"
    with app.app_context():
        from database import get_db
        from blueprints.programacion import _composicion_envases_lote, _plan_envasado_por_cliente
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (producto,))
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (producto,))
        c.execute("DELETE FROM produccion_programada WHERE producto=?", (producto,))
        c.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 90, 1)", (producto,))
        cur = c.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, estado, origen) "
                        "VALUES (?, '2026-06-15', 90, 1, 'programado', 'eos_plan')", (producto,))
        pid = cur.lastrowid
        # presentaciones: 30ml (no fija) + 10ml (fija 1200 uds = regalo)
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, volumen_ml, sku_shopify, cantidad_fija_uds, activo) "
                  "VALUES (?, 'ZZ-30', '30ml', 30, 'ZZ30SKU', 0, 1)", (producto,))
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, volumen_ml, sku_shopify, cantidad_fija_uds, activo) "
                  "VALUES (?, 'ZZ-10', '10ml', 10, 'ZZ10SKU', 1200, 1)", (producto,))
        # B2B: Kelly toma 100 uds de 30ml (3kg)
        c.execute("INSERT INTO pedidos_b2b_lote (pedido_b2b_id, lote_produccion_id, kg_aporte, unidades_aporte, ml_unidad, cliente_nombre, modo) "
                  "VALUES (999, ?, 3, 100, 30, 'Kelly Guerra', 'sumado_a_lote_canonico')", (pid,))
        conn.commit()

        comp = _composicion_envases_lote(c, pid)
        assert comp and comp.get("variantes"), comp
        v30 = next(v for v in comp["variantes"] if round(v["volumen_ml"]) == 30)
        v10 = next(v for v in comp["variantes"] if round(v["volumen_ml"]) == 10)
        # 10ml fija 1200 = 12kg · resto 78kg → 30ml = 2600 uds
        assert v10["unidades_estimadas"] == 1200, v10
        assert v30["unidades_estimadas"] == 2600, v30

        plan = _plan_envasado_por_cliente(c, pid, comp["variantes"])
        dtc = next(x for x in plan if x["es_dtc"])
        kelly = next(x for x in plan if not x["es_dtc"] and "Kelly" in x["cliente"])
        d30 = next(e for e in dtc["envases"] if round(e["ml"]) == 30)
        d10 = next(e for e in dtc["envases"] if round(e["ml"]) == 10)
        assert d30["uds"] == 2500, dtc        # 2600 − 100 Kelly
        assert d10["uds"] == 1200, dtc        # regalo fijo, todo DTC
        assert d10["es_fija"] is True, dtc
        assert kelly["envases"][0]["uds"] == 100, kelly
        assert round(kelly["envases"][0]["ml"]) == 30, kelly
