"""Alejandro 5-jul · MULTI-TONO · la cobertura la manda el tono que se AGOTA PRIMERO, no el promedio.

Un producto multi-tono (LIP SERUM · 6 tonos) donde un tono está casi vacío pero otro tiene mucho stock:
el AGREGADO (Σstock / Σvelocidad) da cobertura alta → el sistema decía "OK, próxima en agosto", pero el
tono bajo se agotaba antes → llegaban SIN ese tono. La cobertura/urgencia debe reflejar el cuello de botella.
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


def test_multitono_cobertura_por_cuello_de_botella(app, db_clean):
    PROD = "PROD-MULTITONO-T1"
    SKU_A = "TONOALTOA30"   # vende mucho, stock CASI VACÍO → cuello de botella
    SKU_B = "TONOBAJOB30"   # vende poco, MUCHO stock → infla el agregado
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    db.execute("DELETE FROM formula_headers WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM sku_producto_map WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM stock_pt WHERE sku IN (?,?)", (SKU_A, SKU_B))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'MTONO-%'")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, fecha_creacion) "
               "VALUES (?, 12, 1, '2025-01-01')", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (SKU_A, PROD))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (SKU_B, PROD))
    # góndola: SKU_A casi vacío (5 uds), SKU_B lleno (2000 uds) → agregado 2005 uds parece muchísimo
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,5,'Disponible','ANIMUS')", (SKU_A, PROD, "L-A"))
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,2000,'Disponible','ANIMUS')", (SKU_B, PROD, "L-B"))
    # ventas: SKU_A vende MUCHO (600 en la ventana), SKU_B poco (60) → SKU_A se agota en ~1 día
    today = date.today()
    for i in range(30):
        f = (today - timedelta(days=i + 1)).isoformat()
        db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (f"MTONO-A{i}", "c", 1000.0, "COP", "", "paid", json.dumps([{"sku": SKU_A, "qty": 20}]), 20, f))
        if i % 5 == 0:
            db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                       "VALUES (?,?,?,?,?,?,?,?,?)",
                       (f"MTONO-B{i}", "c", 1000.0, "COP", "", "paid", json.dumps([{"sku": SKU_B, "qty": 10}]), 10, f))
    db.commit()
    db.close()

    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    d = r.get_json()
    animus = next((x for x in d["clientes"] if x["cliente_id"] == "ANIMUS_DTC"), None)
    fila = next((p for p in animus["productos"] if p["producto_nombre"] == PROD), None)
    assert fila is not None, "producto no apareció"
    # Con el fix: la cobertura la manda el tono casi vacío → días bajos + urgencia CRÍTICA.
    # Sin el fix: el agregado (2005 uds) daría ~180 días → OK (test falla).
    assert fila["dias_gondola"] is not None and fila["dias_gondola"] < 15, (
        "la cobertura debe reflejar el tono que se agota primero, no el promedio", fila["dias_gondola"])
    assert fila["urgencia"] in ("CRITICO", "URGENTE"), (
        "un multi-tono con un tono casi vacío debe salir urgente, no OK", fila["urgencia"])


def test_tono_marginal_bajo_umbral_no_hace_critico(app, db_clean):
    """Umbral 5% (Sebastián 5-jul): un tono que vende <5% del mix y está en 0 NO debe pintar de rojo un
    producto que por lo demás está bien cubierto (evita inflar los críticos con tonos marginales)."""
    PROD = "PROD-MARGINAL-T1"
    SKU_MAIN = "TONOMAIN30"      # 96% del mix, buen stock → cubierto
    SKU_MARG = "TONOMARG30"      # ~4% del mix, stock 0 → marginal, NO debe mandar la alarma
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    for t in ("formula_headers", "sku_producto_map"):
        db.execute(f"DELETE FROM {t} WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM stock_pt WHERE sku IN (?,?)", (SKU_MAIN, SKU_MARG))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'MARG-%'")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, fecha_creacion) "
               "VALUES (?, 12, 1, '2025-01-01')", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (SKU_MAIN, PROD))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (SKU_MARG, PROD))
    # main: buen stock (500 uds) · marginal: 0
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,500,'Disponible','ANIMUS')", (SKU_MAIN, PROD, "L-M"))
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,0,'Disponible','ANIMUS')", (SKU_MARG, PROD, "L-G"))
    # ventas: main 500/ventana (~96%), marginal 20/ventana (~4% · bajo el umbral)
    today = date.today()
    for i in range(30):
        f = (today - timedelta(days=i + 1)).isoformat()
        db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (f"MARG-M{i}", "c", 1000.0, "COP", "", "paid", json.dumps([{"sku": SKU_MAIN, "qty": 17}]), 17, f))
        if i % 6 == 0:
            db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                       "VALUES (?,?,?,?,?,?,?,?,?)",
                       (f"MARG-G{i}", "c", 1000.0, "COP", "", "paid", json.dumps([{"sku": SKU_MARG, "qty": 4}]), 4, f))
    db.commit()
    db.close()

    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    d = r.get_json()
    animus = next((x for x in d["clientes"] if x["cliente_id"] == "ANIMUS_DTC"), None)
    fila = next((p for p in animus["productos"] if p["producto_nombre"] == PROD), None)
    assert fila is not None, "producto no apareció"
    # el tono marginal (0 stock, <5% mix) NO debe hacer crítico al producto (main lo cubre bien)
    assert fila["urgencia"] not in ("CRITICO", "URGENTE"), (
        "un tono marginal (<5% mix) en 0 NO debe disparar la alarma del producto", fila["urgencia"], fila["dias_gondola"])
    # el marginal se sigue viendo en el desglose, marcado mix_bajo
    marg = next((t for t in fila.get("tonos", []) if t["sku"] == SKU_MARG), None)
    assert marg is not None and marg.get("mix_bajo") is True, ("el tono marginal se muestra pero marcado mix_bajo", marg)


def test_az_hibrid_30ml_con_stock_15ml_cero_no_critico(app, db_clean):
    """Sebastián 6-jul (caso AZ HIBRID): 30ml dominante (99.9% mix) CON stock + 15ml marginal (0.1% mix) en 0.
    El producto NO debe ser crítico — lo manda el 30ml (el importante), el 15ml en 0 NO arrastra. Distinto
    tamaño (30 vs 15ml) para verificar que el ml no rompe el umbral 5%."""
    import json as _j
    from datetime import date as _d, timedelta as _td
    PROD = "PROD-AZTEST"
    D30 = "AZTEST30"    # 30ml · vende 99.9% · CON stock
    M15 = "AZTEST15"    # 15ml · vende 0.1% · stock 0
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    for t in ("formula_headers", "sku_producto_map"):
        db.execute(f"DELETE FROM {t} WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM stock_pt WHERE sku IN (?,?)", (D30, M15))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'AZT-%'")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, fecha_creacion) "
               "VALUES (?, 33, 1, '2025-01-01')", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (D30, PROD))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,15,1)", (M15, PROD))
    # 30ml: MUCHO stock (2000 uds ≈ 100d) · 15ml: 0
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,2000,'Disponible','ANIMUS')", (D30, PROD, "L-30"))
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,0,'Disponible','ANIMUS')", (M15, PROD, "L-15"))
    # ventas: 30ml 20/día (600/30d ≈ 99.9%) · 15ml 1 sola (0.1%)
    today = _d.today()
    for i in range(30):
        f = (today - _td(days=i + 1)).isoformat()
        db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (f"AZT-D{i}", "c", 1000.0, "COP", "", "paid", _j.dumps([{"sku": D30, "qty": 20}]), 20, f))
    db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
               "VALUES (?,?,?,?,?,?,?,?,?)",
               ("AZT-M0", "c", 100.0, "COP", "", "paid", _j.dumps([{"sku": M15, "qty": 1}]), 1, today.isoformat()))
    db.commit(); db.close()
    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    d = r.get_json()
    animus = next((x for x in d["clientes"] if x["cliente_id"] == "ANIMUS_DTC"), None)
    fila = next((p for p in animus["productos"] if p["producto_nombre"] == PROD), None)
    assert fila is not None, "producto no apareció"
    _tonos = [(t.get('sku'), t.get('stock_uds'), t.get('porcentaje_mix'), t.get('dias_cobertura_tono'), t.get('mix_bajo'))
              for t in (fila.get('tonos') or [])]
    assert fila["urgencia"] != "CRITICO", (
        "el 15ml marginal (0.1%) en 0 NO debe hacer crítico al producto · lo manda el 30ml (con stock)",
        fila.get("urgencia"), fila.get("dias_gondola"), _tonos)


def test_vitaminac_dominante_marca_secundario_significativo_en_cero(app, db_clean):
    """Sebastián 6-jul (VITAMINA C): el tono DOMINANTE marca la pauta · un tamaño SECUNDARIO ≥5% (15ml al 17%)
    en 0 NO tira el producto a crítico si el dominante (30ml, 83%) tiene stock. DISTINTO de los marginales <5%:
    acá el secundario SÍ pasa el umbral 5% pero igual NO manda (antes el 'min' lo hacía crítico falso)."""
    import json as _j
    from datetime import date as _d, timedelta as _td
    PROD = "PROD-VITCTEST"
    D30 = "VITCT30"     # 30ml · 83% · CON mucho stock
    S15 = "VITCT15"     # 15ml · 17% (≥5%) · stock 0
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    for t in ("formula_headers", "sku_producto_map"):
        db.execute(f"DELETE FROM {t} WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM stock_pt WHERE sku IN (?,?)", (D30, S15))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'VITCT-%'")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, fecha_creacion) "
               "VALUES (?, 20, 1, '2025-01-01')", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,30,1)", (D30, PROD))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,15,1)", (S15, PROD))
    # 30ml: MUCHO stock (2000 uds ≈ 80d) · 15ml: 0
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,2000,'Disponible','ANIMUS')", (D30, PROD, "L-30"))
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,0,'Disponible','ANIMUS')", (S15, PROD, "L-15"))
    # ventas: 30ml ~83% (25/día ≈ 750/30d) · 15ml ~17% (5/día ≈ 150/30d · ≥5% del mix)
    today = _d.today()
    for i in range(30):
        f = (today - _td(days=i + 1)).isoformat()
        db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (f"VITCT-D{i}", "c", 1000.0, "COP", "", "paid", _j.dumps([{"sku": D30, "qty": 25}, {"sku": S15, "qty": 5}]), 30, f))
    db.commit(); db.close()
    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    d = r.get_json()
    animus = next((x for x in d["clientes"] if x["cliente_id"] == "ANIMUS_DTC"), None)
    fila = next((p for p in animus["productos"] if p["producto_nombre"] == PROD), None)
    assert fila is not None, "producto no apareció"
    _tonos = [(t.get('sku'), t.get('stock_uds'), t.get('porcentaje_mix'), t.get('dias_cobertura_tono'))
              for t in (fila.get('tonos') or [])]
    # el 30ml (83%, 80d de stock) manda → NO crítico, aunque el 15ml (17% ≥5%) esté en 0d
    assert fila["urgencia"] != "CRITICO", (
        "el secundario 15ml (17%) en 0 NO debe hacer crítico si el dominante 30ml tiene stock",
        fila.get("urgencia"), fila.get("dias_gondola"), _tonos)
    # la cobertura debe reflejar el 30ml (alta), no el 15ml (0d)
    assert (fila.get("dias_gondola") or 0) > 30, (
        "la cobertura debe reflejar el dominante 30ml (~80d), no el 15ml (0d)", fila.get("dias_gondola"), _tonos)


def test_pauta_mono_producto_renombrado_no_cuello_fantasma(app, db_clean):
    """Sebastián 11-jul (ANIMUSLASH): producto RENOMBRADO (MAXLASH→ANIMUSLASH). El SKU viejo sigue con ventas
    en la ventana pero 0 stock (ya no se fabrica bajo ese código); el SKU nuevo tiene TODO el stock. La lógica
    multi-tono los trata como colores distintos → el 'tono' viejo (vende, 0 stock) crea un CUELLO fantasma →
    rojo permanente. Con la pauta 'mono' (no es multi-tono) el producto usa su cobertura agregada real."""
    import json as _j
    from datetime import date as _d, timedelta as _td
    PROD = "PROD-RENOMBRADO-T1"
    SKU_VIEJO = "MAXLASHVIEJO"   # nombre viejo · vende en la ventana · 0 stock
    SKU_NUEVO = "ANIMUSLASHNEW"  # nombre nuevo · TODO el stock · pocas ventas aún
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    for t in ("formula_headers", "sku_producto_map"):
        db.execute(f"DELETE FROM {t} WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM stock_pt WHERE sku IN (?,?)", (SKU_VIEJO, SKU_NUEVO))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'RENOM-%'")
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, fecha_creacion) "
               "VALUES (?, 5, 1, '2025-01-01')", (PROD,))
    # mismo volumen (4.5ml, máscara) → ruta multi-COLOR (cuello) sin la pauta mono
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,4.5,1)", (SKU_VIEJO, PROD))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,4.5,1)", (SKU_NUEVO, PROD))
    # stock: viejo 0 · nuevo MUCHO (410 uds ≈ el caso real)
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,0,'Disponible','ANIMUS')", (SKU_VIEJO, PROD, "L-V"))
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) "
               "VALUES (?,?,?,410,'Disponible','ANIMUS')", (SKU_NUEVO, PROD, "L-N"))
    # ventas: el SKU viejo aún tiene la mayoría de la ventana (10/día) · el nuevo poco (2/día)
    today = _d.today()
    for i in range(30):
        f = (today - _td(days=i + 1)).isoformat()
        db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (f"RENOM-V{i}", "c", 1000.0, "COP", "", "paid", _j.dumps([{"sku": SKU_VIEJO, "qty": 10}]), 10, f))
        db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (f"RENOM-N{i}", "c", 100.0, "COP", "", "paid", _j.dumps([{"sku": SKU_NUEVO, "qty": 2}]), 2, f))
    db.commit(); db.close()

    from .conftest import csrf_headers
    # SIN la pauta mono: el cuello fantasma (SKU viejo, 0 stock) lo pone crítico
    r0 = c.get("/api/plan/necesidades")
    assert r0.status_code == 200, r0.data
    fila0 = next((p for p in next(x for x in r0.get_json()["clientes"] if x["cliente_id"] == "ANIMUS_DTC")["productos"]
                  if p["producto_nombre"] == PROD), None)
    assert fila0 is not None, "producto no apareció (sin mono)"
    assert fila0["urgencia"] in ("CRITICO", "URGENTE"), (
        "sin la pauta mono el SKU viejo (0 stock) debería crear el cuello fantasma", fila0["urgencia"])

    # CON la pauta mono: usa la cobertura agregada real (410 uds / vel total) → NO crítico
    rp = c.post("/api/plan/pauta-multitono", json={"producto": PROD, "regla": "mono"}, headers=csrf_headers())
    assert rp.status_code == 200 and rp.get_json().get("regla") == "mono", rp.data
    r1 = c.get("/api/plan/necesidades")
    assert r1.status_code == 200, r1.data
    fila1 = next((p for p in next(x for x in r1.get_json()["clientes"] if x["cliente_id"] == "ANIMUS_DTC")["productos"]
                  if p["producto_nombre"] == PROD), None)
    assert fila1 is not None, "producto no apareció (con mono)"
    assert fila1["urgencia"] not in ("CRITICO", "URGENTE"), (
        "con la pauta mono el producto usa su cobertura agregada (410 uds) y NO es crítico",
        fila1["urgencia"], fila1.get("dias_gondola"))
    # el desglose de referencias se sigue viendo (informativo), pero sin marcar cuello
    assert (fila1.get("dias_gondola") or 0) > 25, (
        "la cobertura debe reflejar el stock agregado real, no 0", fila1.get("dias_gondola"))


def test_pauta_mono_default_animuslash_sin_setear(app, db_clean):
    """Sebastián 12-jul: ANIMUSLASH (renombrado de MAXLASH) debe usar cobertura agregada por DEFAULT,
    SIN que nadie setee la pauta 'mono' a mano (el SKU viejo con 0 stock creaba un cuello fantasma → 0d rojo
    permanente). El default automático de productos renombrados conocidos lo resuelve solo."""
    import json as _j
    from datetime import date as _d, timedelta as _td
    PROD = "ANIMUSLASH"
    SKU_VIEJO = "MAXLASHV2"
    SKU_NUEVO = "ANIMUSLASHN2"
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    for t in ("formula_headers", "sku_producto_map"):
        db.execute(f"DELETE FROM {t} WHERE producto_nombre=?", (PROD,))
    db.execute("DELETE FROM stock_pt WHERE sku IN (?,?)", (SKU_VIEJO, SKU_NUEVO))
    db.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE 'ANIMDEF-%'")
    # aseguremos que NO hay pauta explícita para ANIMUSLASH (probamos el DEFAULT)
    row = db.execute("SELECT valor FROM app_settings WHERE clave='pauta_multitono'").fetchone()
    if row and row[0]:
        try:
            _data = _j.loads(row[0]) or {}
        except Exception:
            _data = {}
        _data.pop("animuslash", None)
        db.execute("INSERT OR REPLACE INTO app_settings (clave, valor) VALUES ('pauta_multitono', ?)", (_j.dumps(_data),))
    db.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo, fecha_creacion) VALUES (?, 5, 1, '2025-01-01')", (PROD,))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,4.5,1)", (SKU_VIEJO, PROD))
    db.execute("INSERT INTO sku_producto_map (sku, producto_nombre, volumen_ml, activo) VALUES (?,?,4.5,1)", (SKU_NUEVO, PROD))
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) VALUES (?,?,?,0,'Disponible','ANIMUS')", (SKU_VIEJO, PROD, "L-V2"))
    db.execute("INSERT INTO stock_pt (sku, descripcion, lote_produccion, unidades_disponible, estado, empresa) VALUES (?,?,?,410,'Disponible','ANIMUS')", (SKU_NUEVO, PROD, "L-N2"))
    today = _d.today()
    for i in range(30):
        f = (today - _td(days=i + 1)).isoformat()
        db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) VALUES (?,?,?,?,?,?,?,?,?)",
                   (f"ANIMDEF-V{i}", "c", 1000.0, "COP", "", "paid", _j.dumps([{"sku": SKU_VIEJO, "qty": 10}]), 10, f))
        db.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, estado_pago, sku_items, unidades_total, creado_en) VALUES (?,?,?,?,?,?,?,?,?)",
                   (f"ANIMDEF-N{i}", "c", 100.0, "COP", "", "paid", _j.dumps([{"sku": SKU_NUEVO, "qty": 2}]), 2, f))
    db.commit(); db.close()

    r = c.get("/api/plan/necesidades")
    assert r.status_code == 200, r.data
    fila = next((p for p in next(x for x in r.get_json()["clientes"] if x["cliente_id"] == "ANIMUS_DTC")["productos"]
                 if p["producto_nombre"] == PROD), None)
    assert fila is not None, "ANIMUSLASH no apareció"
    # POR DEFAULT (sin setear mono): usa la cobertura agregada (410 uds) → NO crítico, dias_gondola alto
    assert fila["urgencia"] not in ("CRITICO", "URGENTE"), (
        "ANIMUSLASH debe usar cobertura agregada por default (renombrado), no el cuello fantasma",
        fila["urgencia"], fila.get("dias_gondola"))
    assert (fila.get("dias_gondola") or 0) > 25, ("cobertura agregada real, no 0", fila.get("dias_gondola"))
