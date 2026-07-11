"""Sebastián 10-jul · AZUL "EN TRÁNSITO". Un producto que estás produciendo (lote en_curso) o que
produjiste hace poco (≤14d · o la producción FUENTE que colocás) NO debe seguir en ROJO: pasa a
POR_ENTRAR (azul · va en camino a la góndola) hasta que Shopify lo refleje (→ verde). Lo solo
PROGRAMADO a futuro NO pinta azul (no escondemos reds reales).
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
    assert r.status_code == 302, "login %s fallo: %s" % (user, r.status_code)
    return c


def _seed_critico(db, PROD, SKU):
    db.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    db.execute("DELETE FROM stock_pt WHERE sku=?", (SKU,))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE '" + SKU + "-%'")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, fecha_creacion) "
               "VALUES (?, 20, 1, '2025-01-01')", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, activo, volumen_ml) VALUES (?,?,1,50)", (SKU, PROD))
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,0,'Disponible','ANIMUS')", (SKU, PROD, "L-0"))
    today = date.today()
    for i in range(30):
        f = (today - timedelta(days=i + 1)).isoformat()
        db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (SKU + "-" + str(i), "c", 100.0, "COP", "", "paid", json.dumps([{"sku": SKU, "qty": 1}]), 1, f))


def _fila(client, prod):
    r = client.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    animus = next(x for x in r.get_json()["clientes"] if x["cliente_id"] == "ANIMUS_DTC")
    return next(p for p in animus["productos"] if p["producto_nombre"] == prod)


def test_en_curso_saca_de_rojo_a_azul(app, db_clean):
    PROD, SKU = "ENTRANSITOLASH", "ETZ9"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"]); _seed_critico(db, PROD, SKU); db.commit(); db.close()
    # 1) sin producción → CRÍTICO (stock 0, vende ~1/día)
    assert _fila(c, PROD)["urgencia"] == "CRITICO"
    # 2) un lote EN_CURSO (le diste fabricar) → POR_ENTRAR (azul · va en camino)
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, origen, cantidad_kg) "
               "VALUES (?,?,1,'en_curso','eos_plan',10)", (PROD, date.today().isoformat()))
    db.commit(); db.close()
    f = _fila(c, PROD)
    assert f["urgencia"] == "POR_ENTRAR", ("en_curso debe pasar a azul", f.get("urgencia"), f.get("en_transito_uds"))
    assert f.get("en_transito_uds", 0) > 0


def test_fuente_colocada_reciente_saca_de_rojo(app, db_clean):
    """La producción FUENTE colocada (eos_retroactivo, fecha pasada ≤14d) también saca de rojo a azul."""
    PROD, SKU = "FUENTELASH", "FTL9"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"]); _seed_critico(db, PROD, SKU)
    db.execute("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, origen, cantidad_kg) "
               "VALUES (?,?,1,'pendiente','eos_retroactivo',10)", (PROD, (date.today() - timedelta(days=5)).isoformat()))
    db.commit(); db.close()
    f = _fila(c, PROD)
    assert f["urgencia"] == "POR_ENTRAR", ("la fuente reciente debe pasar a azul", f.get("urgencia"), f.get("en_transito_uds"))


def test_lote_pasado_eos_plan_saca_de_rojo(app, db_clean):
    """[Sebastián 11-jul · caso LIMPIADOR BHA] Un lote con FECHA PASADA (≤14d) no-cancelado, aunque sea
    eos_plan 'pendiente' (el jefe lo produjo pero no lo marcó), cuenta como en tránsito → azul.
    'El calendario es el ojo de la verdad': lote pasado no-cancelado = producido."""
    PROD, SKU = "BHAPASADOLASH", "BHA9"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"]); _seed_critico(db, PROD, SKU)
    db.execute("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, origen, cantidad_kg) "
               "VALUES (?,?,1,'pendiente','eos_plan',10)", (PROD, (date.today() - timedelta(days=2)).isoformat()))
    db.commit(); db.close()
    f = _fila(c, PROD)
    assert f["urgencia"] == "POR_ENTRAR", ("lote pasado eos_plan (producido) debe pasar a azul", f.get("urgencia"), f.get("en_transito_uds"))


def test_programado_futuro_sigue_rojo(app, db_clean):
    """Un lote solo PROGRAMADO a futuro (no en_curso, no producido) NO pinta azul: sigue CRÍTICO."""
    PROD, SKU = "FUTUROLASH", "FUT9"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"]); _seed_critico(db, PROD, SKU)
    db.execute("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, origen, cantidad_kg) "
               "VALUES (?,?,1,'pendiente','eos_plan',10)", (PROD, (date.today() + timedelta(days=20)).isoformat()))
    db.commit(); db.close()
    f = _fila(c, PROD)
    assert f["urgencia"] == "CRITICO", ("programado a futuro NO debe esconder el rojo", f.get("urgencia"))
