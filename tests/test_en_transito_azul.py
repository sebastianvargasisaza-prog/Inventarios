"""AZUL "POR ENTRAR" · qué lo dispara y qué NO.

REGLA VIGENTE (Sebastián 24-jul · reemplaza a la del 10-jul):
    **"El calendario NO es la verdad, debe ser el inventario de Espagiria."**
El azul lo dispara ÚNICAMENTE el inventario físico de Espagiria en Shopify
(`stock_por_entrar`, que alimenta `_por_entrar_uds`). El calendario ya NO lo dispara:
`_en_transito_uds` sigue calculándose pero queda SOLO como diagnóstico y no decide el color
(`plan.py`: `_transito_total_uds = int(_por_entrar_uds)`).

Por qué se cambió: un lote programado en el pasado que NUNCA se fabricó pintaba azul falso y
escondía el faltante real de góndola. Violaba M6 (físico vs plan, separados).

⚠ Este archivo llevaba tiempo EN ROJO porque seguía afirmando la regla vieja: 3 de sus 4
tests exigían que el calendario pintara azul, y uno afirmaba exactamente el bug que se quitó
(lote pasado no fabricado → azul). Se reescribieron para fijar la regla ACTUAL, así que ahora
protegen el cambio en vez de pelearse con él.
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
    try:
        db.execute("DELETE FROM stock_por_entrar WHERE sku=?", (SKU,))
    except Exception:
        pass
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


def _sembrar(prod, sku, extra_sql=None, params=()):
    db = sqlite3.connect(os.environ["DB_PATH"])
    try:
        _seed_critico(db, prod, sku)
        if extra_sql:
            db.execute(extra_sql, params)
        db.commit()
    finally:
        db.close()


# ── LO QUE SÍ pinta azul ────────────────────────────────────────────────────

def test_inventario_de_espagiria_saca_de_rojo_a_azul(app, db_clean):
    """La ÚNICA fuente del azul: producto físico en la bodega de Espagiria (Shopify)."""
    PROD, SKU = "ENTRANSITOLASH", "ETZ9"
    c = _login_as(app, "sebastian")
    _sembrar(PROD, SKU)
    assert _fila(c, PROD)["urgencia"] == "CRITICO", "sin nada físico debe estar en rojo"
    _sembrar(PROD, SKU,
             "INSERT INTO stock_por_entrar (sku, uds, actualizado_at) VALUES (?,?,date('now'))",
             (SKU, 500))
    f = _fila(c, PROD)
    assert f["urgencia"] == "POR_ENTRAR", (
        "el inventario físico de Espagiria debe pasar a azul", f.get("urgencia"))


# ── LO QUE **NO** pinta azul (el calendario dejó de ser la verdad) ──────────

def test_en_curso_ya_no_pinta_azul(app, db_clean):
    """Un lote en_curso es PLAN, no producto físico: no puede tapar el rojo (Sebastián 24-jul)."""
    PROD, SKU = "ENCURSOLASH", "ENC9"
    c = _login_as(app, "sebastian")
    _sembrar(PROD, SKU,
             "INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, origen, cantidad_kg) "
             "VALUES (?,?,1,'en_curso','eos_plan',10)", (PROD, date.today().isoformat()))
    f = _fila(c, PROD)
    assert f["urgencia"] == "CRITICO", (
        "un lote en curso NO debe esconder el faltante de góndola", f.get("urgencia"))


def test_lote_pasado_no_fabricado_ya_no_pinta_azul(app, db_clean):
    """EL BUG QUE SE QUITÓ · un lote con fecha pasada que nunca se fabricó pintaba azul falso.

    Es el caso que motivó el cambio: escondía el faltante real detrás de una producción que
    no existió. El calendario no prueba que algo se haya fabricado.
    """
    PROD, SKU = "BHAPASADOLASH", "BHA9"
    c = _login_as(app, "sebastian")
    _sembrar(PROD, SKU,
             "INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, origen, cantidad_kg) "
             "VALUES (?,?,1,'pendiente','eos_plan',10)", (PROD, (date.today() - timedelta(days=2)).isoformat()))
    f = _fila(c, PROD)
    assert f["urgencia"] == "CRITICO", (
        "un lote pasado NO fabricado no puede pintar azul", f.get("urgencia"))


def test_fuente_retroactiva_ya_no_pinta_azul(app, db_clean):
    """Tampoco una producción FUENTE colocada a mano: sigue siendo calendario, no inventario."""
    PROD, SKU = "FUENTELASH", "FTL9"
    c = _login_as(app, "sebastian")
    _sembrar(PROD, SKU,
             "INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, origen, cantidad_kg) "
             "VALUES (?,?,1,'pendiente','eos_retroactivo',10)", (PROD, (date.today() - timedelta(days=5)).isoformat()))
    f = _fila(c, PROD)
    assert f["urgencia"] == "CRITICO", (
        "la fuente retroactiva es plan, no producto en góndola", f.get("urgencia"))


def test_programado_futuro_sigue_rojo(app, db_clean):
    """Un lote solo PROGRAMADO a futuro NO pinta azul: sigue CRÍTICO (esto nunca cambió)."""
    PROD, SKU = "FUTUROLASH", "FUT9"
    c = _login_as(app, "sebastian")
    _sembrar(PROD, SKU,
             "INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, origen, cantidad_kg) "
             "VALUES (?,?,1,'pendiente','eos_plan',10)", (PROD, (date.today() + timedelta(days=20)).isoformat()))
    f = _fila(c, PROD)
    assert f["urgencia"] == "CRITICO", ("programado a futuro NO debe esconder el rojo", f.get("urgencia"))
