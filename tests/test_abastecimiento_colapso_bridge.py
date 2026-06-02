"""Audit abastecimiento 2-jun-2026: la DEMANDA debe colapsarse al código de BODEGA
resuelto (bridge/alias), no quedar partida entre códigos de fórmula del mismo
material. Antes: dos códigos de fórmula bridgeados al mismo bodega salían como 2
filas con déficit parcial · ahora: 1 fila con la demanda sumada."""
import os
import sqlite3


def _login_as(app, user="sebastian"):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_demanda_colapsa_por_bridge(app, db_clean):
    bod = "MPBODCOL01"          # código de bodega (tiene movimientos)
    fa, fb = "MPFCOLA01", "MPFCOLB01"   # dos códigos de fórmula → mismo bodega
    p1, p2 = "ZZ COL P1", "ZZ COL P2"
    c = _login_as(app)
    with app.app_context():
        from database import get_db
        conn = get_db()
        for t, q in [
            ("DELETE FROM formula_items WHERE producto_nombre IN (?,?)", (p1, p2)),
            ("DELETE FROM formula_headers WHERE producto_nombre IN (?,?)", (p1, p2)),
            ("DELETE FROM produccion_programada WHERE producto IN (?,?)", (p1, p2)),
            ("DELETE FROM maestro_mps WHERE codigo_mp IN (?,?,?)", (bod, fa, fb)),
            ("DELETE FROM movimientos WHERE material_id=?", (bod,)),
            ("DELETE FROM mp_formula_bridge WHERE formula_material_id IN (?,?)", (fa, fb)),
        ]:
            conn.execute(t, q)
        conn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) VALUES (?,?,?,1)",
                     (bod, "Material Bodega Colapso", "BODCOL"))
        # los códigos de fórmula deben existir en maestro (trigger FK), SIN movimientos
        # → el resolver Tier-1 falla y cae al bridge → bodega.
        for fc in (fa, fb):
            conn.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, activo) VALUES (?,?,1)",
                         (fc, "Material Bodega Colapso"))
        # movimiento bajo el código de bodega → _resolver_material_bodega resuelve el bridge
        conn.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote) "
                     "VALUES (?,?,?,?,date('now','-5 hours'),?,'VIGENTE')", (bod, "Material Bodega Colapso", 1000, "Entrada", "LC1"))
        conn.execute("INSERT INTO mp_formula_bridge (formula_material_id, bodega_material_id, activo) VALUES (?,?,1)", (fa, bod))
        conn.execute("INSERT INTO mp_formula_bridge (formula_material_id, bodega_material_id, activo) VALUES (?,?,1)", (fb, bod))
        for prod, fcode in [(p1, fa), (p2, fb)]:
            conn.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,10,1)", (prod,))
            conn.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
                         "VALUES (?,?,?,50,0)", (prod, fcode, "Material Bodega Colapso"))
            conn.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, estado, origen) "
                         "VALUES (?, date('now','-5 hours','+5 days'), 10, 1, 'programado', 'eos_plan')", (prod,))
        conn.commit()

    r = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp&horizontes=15,30,60,90")
    assert r.status_code == 200, r.data
    mps = r.get_json().get("mps") or []
    # NO debe haber filas por los códigos de fórmula
    assert not any(str(x.get("codigo")).upper() in (fa, fb) for x in mps), \
        "la demanda NO debe salir por los códigos de fórmula crudos"
    # SÍ una fila por el código de bodega, con la demanda SUMADA (5000+5000=10000)
    fila = next((x for x in mps if str(x.get("codigo")).upper() == bod), None)
    assert fila is not None, "debe existir una fila por el código de bodega resuelto"
    assert abs(fila["consumo"].get("30") - 10000.0) < 1.0, f"demanda sumada ~10000g, got {fila['consumo'].get('30')}"

    with app.app_context():
        from database import get_db
        conn = get_db()
        for t, q in [
            ("DELETE FROM formula_items WHERE producto_nombre IN (?,?)", (p1, p2)),
            ("DELETE FROM formula_headers WHERE producto_nombre IN (?,?)", (p1, p2)),
            ("DELETE FROM produccion_programada WHERE producto IN (?,?)", (p1, p2)),
            ("DELETE FROM maestro_mps WHERE codigo_mp IN (?,?,?)", (bod, fa, fb)),
            ("DELETE FROM movimientos WHERE material_id=?", (bod,)),
            ("DELETE FROM mp_formula_bridge WHERE formula_material_id IN (?,?)", (fa, fb)),
        ]:
            conn.execute(t, q)
        conn.commit()
