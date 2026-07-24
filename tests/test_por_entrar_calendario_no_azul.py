"""Sebastián 24-jul · el AZUL (POR_ENTRAR) sale SOLO del inventario Shopify de Espagiria (stock_por_entrar),
NO del calendario. "El calendario no es la verdad, debe ser el inventario de Espagiria."

Antes (10-jul) el azul lo disparaba también lo "en tránsito" derivado del calendario: un lote programado en el
pasado y NUNCA fabricado pintaba azul falso y escondía el faltante de góndola (violaba M6). Este test fija que
un lote programado-en-el-pasado-no-fabricado, SIN stock físico de Espagiria, deja el producto CRÍTICO (rojo).
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


def test_lote_calendario_pasado_no_fabricado_no_pinta_azul(app, db_clean):
    """Góndola 0 + lote programado en el pasado (no fabricado) + Espagiria 0 → CRÍTICO, NO POR_ENTRAR."""
    PROD = "TESTCAL-NOAZUL"
    SKU = "TCAL-30"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    for t in ("formula_headers", "sku_producto_map"):
        db.execute(f"DELETE FROM {t} WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM stock_pt WHERE sku=?", (SKU,))
    db.execute("DELETE FROM stock_por_entrar WHERE sku=?", (SKU,))
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'TCAL-%'")
    db.execute("DELETE FROM app_settings WHERE clave='por_entrar_manual'")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, fecha_creacion) "
               "VALUES (?, 20, 1, '2025-01-01')", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (SKU, PROD))
    # góndola 0 · sin nada por entrar = CRÍTICO (vende ~1/día)
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,0,'Disponible','ANIMUS')", (SKU, PROD, "L-0"))
    today = date.today()
    for i in range(30):
        f = (today - timedelta(days=i + 1)).isoformat()
        db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (f"TCAL-{i}", "c", 100.0, "COP", "", "paid", json.dumps([{"sku": SKU, "qty": 1}]), 1, f))
    db.commit(); db.close()

    # 1) baseline: sin lote programado → CRÍTICO
    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    animus = next(x for x in r.get_json()["clientes"] if x["cliente_id"] == "ANIMUS_DTC")
    fila = next(p for p in animus["productos"] if p["producto_nombre"] == PROD)
    assert fila["urgencia"] == "CRITICO", ("debería arrancar crítico", fila.get("urgencia"))

    # 2) agregar un lote PROGRAMADO en el pasado (≤14d), NO fabricado (sin fin_real_at ni descuento) →
    #    ESTO es "el calendario". Antes pintaba azul falso; ahora NO debe tocar el color.
    db = sqlite3.connect(os.environ["DB_PATH"])
    fpasado = (today - timedelta(days=3)).isoformat()
    db.execute(
        "INSERT INTO produccion_programada (producto, cantidad_kg, fecha_programada, estado, origen) "
        "VALUES (?, 20, ?, 'programado', 'eos_plan')", (PROD, fpasado))
    db.commit(); db.close()

    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    animus = next(x for x in r.get_json()["clientes"] if x["cliente_id"] == "ANIMUS_DTC")
    fila = next(p for p in animus["productos"] if p["producto_nombre"] == PROD)
    # el calendario YA NO decide el azul → sigue CRÍTICO (góndola 0, nada físico por entrar de Espagiria)
    assert fila["urgencia"] == "CRITICO", (
        "un lote programado-en-el-pasado-no-fabricado NO debe pintar azul (el calendario no es la verdad)",
        fila.get("urgencia"), fila.get("en_transito_uds"), fila.get("por_entrar_uds"))
    # y NO reporta 'por entrar' físico (Espagiria = 0)
    assert (fila.get("por_entrar_uds") or 0) == 0, ("Espagiria = 0 → sin por-entrar físico", fila.get("por_entrar_uds"))


def test_espagiria_fisico_si_pinta_azul(app, db_clean):
    """Contraste: con stock físico de Espagiria (stock_por_entrar) SÍ → POR_ENTRAR (lo válido)."""
    PROD = "TESTCAL-SIAZUL"
    SKU = "TCAL2-30"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    for t in ("formula_headers", "sku_producto_map"):
        db.execute(f"DELETE FROM {t} WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM stock_pt WHERE sku=?", (SKU,))
    db.execute("DELETE FROM stock_por_entrar WHERE sku=?", (SKU,))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'TCAL2-%'")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, fecha_creacion) "
               "VALUES (?, 20, 1, '2025-01-01')", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (SKU, PROD))
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,0,'Disponible','ANIMUS')", (SKU, PROD, "L-0"))
    # Espagiria tiene 500 uds FÍSICAS por entrar (inventario Shopify de su location)
    db.execute("INSERT INTO stock_por_entrar (sku, uds, actualizado_at) VALUES (?,500,?)", (SKU, date.today().isoformat()))
    today = date.today()
    for i in range(30):
        f = (today - timedelta(days=i + 1)).isoformat()
        db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (f"TCAL2-{i}", "c", 100.0, "COP", "", "paid", json.dumps([{"sku": SKU, "qty": 1}]), 1, f))
    db.commit(); db.close()

    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    animus = next(x for x in r.get_json()["clientes"] if x["cliente_id"] == "ANIMUS_DTC")
    fila = next(p for p in animus["productos"] if p["producto_nombre"] == PROD)
    assert fila["urgencia"] == "POR_ENTRAR", (
        "con stock físico de Espagiria SÍ es POR_ENTRAR", fila.get("urgencia"), fila.get("por_entrar_uds"))
    assert (fila.get("por_entrar_uds") or 0) == 500
