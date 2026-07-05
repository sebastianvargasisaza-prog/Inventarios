"""Sebastián 4-jul · CENTELLA/ANIMUSLASH · el ancla HECHA pero SIN REGISTRAR no está en góndola.

Cuando la última producción es PASADA pero NO ejecutada (sin inicio_real/fin_real/inventario_descontado),
su stock todavía NO está en la góndola (Shopify) → la cobertura NO debe basarse solo en la góndola (baja)
sino RESCATAR con el remanente del ancla (lo que le queda al lote de junio). Si el ancla SÍ está ejecutada
(NOVA PHA), su stock YA está en góndola → la góndola manda (no doble-contar).

Test A/B: dos productos idénticos (misma venta, misma góndola media ~20d, mismo lote de junio 27kg/~90d),
el único cambio es si el ancla está ejecutada. El NO ejecutado debe dar cobertura mucho mayor (rescate).
"""
import json
import os
import sqlite3
from datetime import date, timedelta


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login {user} fallo: {r.status_code}"
    return c


def _seed_prod(db, prod, sku, ejecutado, dias_ancla=11, estado_ancla="programado", kg_ancla=27):
    db.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (prod,))
    db.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (prod,))
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (prod,))
    db.execute("DELETE FROM stock_pt WHERE sku=?", (sku,))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE ?", (sku + "-%",))
    db.execute("INSERT INTO formula_headers (producto_nombre, codigo_pt, lote_size_kg, activo, fecha_creacion) "
               "VALUES (?,?,?,1,?)", (prod, sku[:6], 27, "2025-01-01"))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (sku, prod))
    # góndola media: 200 uds Disponibles (≈20 días a 10 uds/día · >7 para que NO salte el rescate H4)
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,200,'Disponible','ANIMUS')", (sku, prod, "L-" + sku))
    # venta ~10 uds/día repartida en la ventana
    today = date.today()
    for i, delta in enumerate([5, 12, 20, 28, 36, 44, 52]):
        fecha = (today - timedelta(days=delta)).isoformat()
        db.execute(
            """INSERT INTO animus_shopify_orders
               (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (f"{sku}-{i}", f"Cli {i}", 100000.0, "COP", "", "paid",
             json.dumps([{"sku": sku, "qty": 80}]), 80, fecha))
    # ancla = producción pasada de 27kg (~90d de cobertura) · past + no cancelada
    _exec_cols = ", inventario_descontado_at" if ejecutado else ""
    _exec_vals = ", datetime('now','-1 days')" if ejecutado else ""
    db.execute(
        f"""INSERT INTO produccion_programada
            (producto, fecha_programada, cantidad_kg, estado, origen, lotes{_exec_cols})
            VALUES (?, date('now',?,'-5 hours'), ?, ?, 'eos_plan', 1{_exec_vals})""",
        (prod, f"-{int(dias_ancla)} days", float(kg_ancla), estado_ancla))


def _cobertura(app, c, prod):
    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    d = r.get_json()
    animus = next((x for x in d["clientes"] if x["cliente_id"] == "ANIMUS_DTC"), None)
    fila = next((p for p in animus["productos"] if p["producto_nombre"] == prod), None)
    assert fila is not None, f"{prod} no apareció en necesidades"
    return fila.get("cobertura_efectiva_dias"), fila.get("proxima_sugerida_dias")


def test_ancla_sin_registrar_rescata_cobertura(app, db_clean):
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    _seed_prod(db, "PROD-ANCLA-SINREG", "ANCLASR30", ejecutado=False)   # hecha pero sin registrar
    _seed_prod(db, "PROD-ANCLA-EJEC", "ANCLAEJ30", ejecutado=True)      # ya descontada (en góndola)
    db.commit()
    db.close()

    cob_sinreg, prox_sinreg = _cobertura(app, c, "PROD-ANCLA-SINREG")
    cob_ejec, prox_ejec = _cobertura(app, c, "PROD-ANCLA-EJEC")

    # El ancla SIN registrar rescata con el remanente (~79d) → cobertura alta, próxima lejos.
    assert cob_sinreg is not None and cob_sinreg >= 50, (
        "ancla hecha-sin-registrar debe rescatar con el remanente del lote (no proponer producir ya)", cob_sinreg)
    # El ancla EJECUTADA ya está en góndola → manda la góndola (~20d) → cobertura baja.
    assert cob_ejec is not None and cob_ejec <= 35, (
        "ancla ejecutada ya está en góndola → NO debe inflar con el remanente", cob_ejec)
    # y la diferencia es clara (el rescate solo aplica al no-registrado)
    assert cob_sinreg > cob_ejec + 20, (cob_sinreg, cob_ejec)


def test_ancla_zombie_vieja_no_rescata(app, db_clean):
    """P1-A · un lote PASADO no-ejecutado pero VIEJO (>45d · sospechoso de zombie nunca producido) NO debe
    rescatar la cobertura con su remanente teórico (aunque sea enorme). Manda la góndola → produce antes."""
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    # ancla de hace 70 días, 60kg (remanente teórico enorme ~110d) pero NUNCA ejecutada = zombie
    _seed_prod(db, "PROD-ZOMBIE", "ZOMBIE30", ejecutado=False, dias_ancla=70, kg_ancla=60)
    db.commit()
    db.close()
    cob, _ = _cobertura(app, c, "PROD-ZOMBIE")
    # NO debe inflarse al remanente (~110d): manda la góndola (~18d)
    assert cob is not None and cob <= 30, (
        "un zombie viejo (>45d) NO debe inflar la cobertura con su remanente → riesgo de sub-compra", cob)


def test_ancla_esperando_recurso_no_es_ancla(app, db_clean):
    """P1-A · un lote pasado en 'esperando_recurso' (pausado por falta de MP = NO se produjo) NO debe
    contar como 'última producción' ancla ni rescatar la cobertura."""
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    _seed_prod(db, "PROD-ESPRECURSO", "ESPREC30", ejecutado=False, dias_ancla=11,
               estado_ancla="esperando_recurso", kg_ancla=60)
    db.commit()
    db.close()
    cob, _ = _cobertura(app, c, "PROD-ESPRECURSO")
    # pausado por MP no es producción → no rescata → manda la góndola (~18d)
    assert cob is not None and cob <= 30, (
        "un lote 'esperando_recurso' pasado NO debe anclar/rescatar la cobertura", cob)
