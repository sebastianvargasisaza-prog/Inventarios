"""Abastecimiento de ENVASES (MEE) unificado en producto_presentaciones · 18-jun.

Antes el motor de abastecimiento sacaba los envases de sku_mee_config (vacía) → consumo
de envases = 0 para todo, en silencio. Ahora los saca de producto_presentaciones (la MISMA
fuente que usa el descuento _composicion_envases_lote): por producto, su envase + volumen,
repartido por share de ventas. Volumen también cae a presentaciones si no hay
volumen_unitario_producto. Clave _norm_prod (M13).
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def test_envase_abastecimiento_desde_presentaciones(app, db_clean):
    prod = "ZZ ENV PROD"
    envase = "ENV-ZZ-001"
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) "
          "VALUES ('MP-ENVZZ','Mat ENVZZ','INCI ENVZZ',1)")
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,1,1)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES (?, 'MP-ENVZZ','Mat ENVZZ',10,0)", (prod,))
    _exec("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,stock_actual,stock_minimo) "
          "VALUES (?, 'Frasco ZZ 50ml','Envase',0,0)", (envase,))
    # presentación: 50 ml → envase (ventas ref 100). Es la fuente única (= descuento).
    _exec("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,etiqueta,volumen_ml,envase_codigo,ventas_mes_referencia,activo) "
          "VALUES (?, 'ZZ-50','50 ml',50,?,100,1)", (prod, envase))
    # producción FIJA en horizonte: 5 kg → 5000 g / 50 ml = 100 unidades → 100 envases.
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES (?, date('now','-5 hours','+5 days'),1,'pendiente',5,'eos_plan')", (prod,))
    c = _login(app)
    r = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp,mee")
    assert r.status_code == 200, r.data
    j = r.get_json()
    mees = j.get("mees") or []
    it = next((m for m in mees if (m.get("codigo") or "").upper() == envase.upper()), None)
    assert it is not None, \
        f"el envase debe aparecer en abastecimiento (consumo desde presentaciones) · mees={[m.get('codigo') for m in mees]}"
    hmax = str(max(j["horizontes"]))
    assert float(it["consumo"][hmax]) >= 99, f"consumo envase ~100 unidades · got {it['consumo']}"
    # sin stock → déficit ~100
    assert float(it["deficit"][hmax]) >= 99, f"déficit envase ~100 · got {it['deficit']}"


def test_tapa_caja_aparecen_en_abastecimiento(app, db_clean):
    """A+ (mig 278): tapa y caja SECUNDARIAS también se planean (compra), desde la
    MISMA presentación que el envase primario → no dejar nada por fuera."""
    prod = "ZZ TC PROD"
    envase, tapa, caja = "ENV-TC-A-50ML", "TAPA-TC-A", "CAJA-TC-A"
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) "
          "VALUES ('MP-TCA','Mat TCA','INCI TCA',1)")
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,1,1)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES (?, 'MP-TCA','Mat TCA',10,0)", (prod,))
    for cod in (envase, tapa, caja):
        _exec("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,stock_actual,stock_minimo) "
              "VALUES (?, 'MEE TC','Envase',0,0)", (cod,))
    _exec("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,etiqueta,volumen_ml,envase_codigo,tapa_codigo,caja_codigo,ventas_mes_referencia,activo) "
          "VALUES (?, 'TC-50','50 ml',50,?,?,?,100,1)", (prod, envase, tapa, caja))
    # 5 kg → 5000 g / 50 ml = 100 unidades → 100 de envase, tapa y caja c/u.
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES (?, date('now','-5 hours','+5 days'),1,'pendiente',5,'eos_plan')", (prod,))
    c = _login(app)
    j = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp,mee").get_json()
    mees = {(m.get("codigo") or "").upper(): m for m in (j.get("mees") or [])}
    hmax = str(max(j["horizontes"]))
    for cod in (envase, tapa, caja):
        it = mees.get(cod.upper())
        assert it is not None, f"{cod} debe aparecer en abastecimiento · mees={list(mees)}"
        assert float(it["consumo"][hmax]) >= 99, f"{cod} consumo ~100 · got {it['consumo']}"


def test_envase_no_aparece_sin_presentacion(app, db_clean):
    """Control: un producto SIN presentación+envase no genera consumo MEE fantasma."""
    prod = "ZZ ENV SINPRES"
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) "
          "VALUES ('MP-SINPRES','Mat SP','INCI SP',1)")
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,1,1)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES (?, 'MP-SINPRES','Mat SP',10,0)", (prod,))
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES (?, date('now','-5 hours','+5 days'),1,'pendiente',5,'eos_plan')", (prod,))
    c = _login(app)
    r = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp,mee")
    assert r.status_code == 200, r.data
    mees = r.get_json().get("mees") or []
    # no debe inventar un envase para este producto (no tiene presentación)
    assert all('SINPRES' not in (m.get('codigo') or '').upper() for m in mees)



def test_envase_multipresentacion_reparte_por_ventas(app, db_clean):
    # M58: producto con 2 presentaciones (15/30ml) con ventas_mes_referencia=0 → el envase NO se reparte
    # uniforme (50/50) sino por VENTAS Shopify por volumen (= desglose por referencia). 30ml vende 100, 15ml 1.
    import json as _j
    prod = "ZZ MULTIPRES"
    envA, envB = "ENV-ZZ-15", "ENV-ZZ-30"
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) VALUES ('MP-ZZMP','Mat','INCI',1)")
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,1,1)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES (?, 'MP-ZZMP','Mat',10,0)", (prod,))
    for cod, d in ((envA, 'Frasco 15ml'), (envB, 'Frasco 30ml')):
        _exec("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,stock_actual,stock_minimo) "
              "VALUES (?,?,'Envase',0,0)", (cod, d))
    _exec("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,etiqueta,volumen_ml,envase_codigo,ventas_mes_referencia,activo) "
          "VALUES (?, 'V15','15 ml',15,?,0,1)", (prod, envA))
    _exec("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,etiqueta,volumen_ml,envase_codigo,ventas_mes_referencia,activo) "
          "VALUES (?, 'V30','30 ml',30,?,0,1)", (prod, envB))
    _exec("INSERT INTO sku_producto_map (sku,producto_nombre,volumen_ml,activo) VALUES ('ZZSKU15',?,15,1)", (prod,))
    _exec("INSERT INTO sku_producto_map (sku,producto_nombre,volumen_ml,activo) VALUES ('ZZSKU30',?,30,1)", (prod,))
    _exec("INSERT INTO animus_shopify_orders (shopify_id,estado,estado_pago,sku_items,unidades_total,tags,customer_tags,creado_en) "
          "VALUES ('ZZO1','','paid',?,101,'','',datetime('now','-5 hours'))",
          (_j.dumps([{'sku': 'ZZSKU30', 'qty': 100}, {'sku': 'ZZSKU15', 'qty': 1}]),))
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES (?, date('now','-5 hours','+5 days'),1,'pendiente',5,'eos_plan')", (prod,))
    c = _login(app)
    j = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp,mee").get_json()
    mees = j.get("mees") or []
    hmax = str(max(j["horizontes"]))
    a_it = next((m for m in mees if (m.get("codigo") or "").upper() == envA.upper()), None)
    b_it = next((m for m in mees if (m.get("codigo") or "").upper() == envB.upper()), None)
    assert b_it is not None, ('falta el frasco 30ml en abastecimiento', [m.get('codigo') for m in mees])
    cb = float(b_it["consumo"][hmax])
    ca = float(a_it["consumo"][hmax]) if a_it else 0.0
    # 30ml vende 100x más → demanda mucho mayor (uniforme daría cb≈ca)
    assert cb > ca * 5, f"el frasco 30ml debe demandar mucho mas que el 15ml (no uniforme) · 30={cb} 15={ca}"



def test_envase_abastecimiento_acumula_por_horizonte(app, db_clean):
    # M16/M58: la demanda de envases ACUMULA por horizonte (15⊂30⊂60⊂90) igual que MP · 2 producciones del
    # mismo producto a distinta fecha → el horizonte mayor incluye más envases.
    prod = "ZZ HORIZ ENV"
    env = "ENV-HZ-50"
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) VALUES ('MP-HZ','Mat','INCI',1)")
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,1,1)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES (?, 'MP-HZ','Mat',10,0)", (prod,))
    _exec("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,stock_actual,stock_minimo) "
          "VALUES (?, 'Frasco 50','Envase',0,0)", (env,))
    _exec("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,etiqueta,volumen_ml,envase_codigo,ventas_mes_referencia,activo) "
          "VALUES (?, 'V50','50 ml',50,?,100,1)", (prod, env))
    # +5 días (entra a todos los horizontes) · +45 días (solo el grande)
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES (?, date('now','-5 hours','+5 days'),1,'pendiente',5,'eos_plan')", (prod,))
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES (?, date('now','-5 hours','+45 days'),1,'pendiente',5,'eos_plan')", (prod,))
    c = _login(app)
    j = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp,mee").get_json()
    it = next((m for m in (j.get("mees") or []) if (m.get("codigo") or "").upper() == env.upper()), None)
    assert it is not None, ('falta envase', [m.get('codigo') for m in (j.get('mees') or [])])
    hs = sorted(int(h) for h in it["consumo"].keys())
    h_chico = next((h for h in hs if 5 <= h < 45), None)
    h_grande = next((h for h in hs if h >= 45), None)
    assert h_chico and h_grande, ('horizontes inesperados', hs)
    c1 = float(it["consumo"][str(h_chico)]); c2 = float(it["consumo"][str(h_grande)])
    assert c1 >= 99, f"horizonte chico ~100 uds (1 producción) · {h_chico}d={c1}"
    assert c2 > c1 + 50, f"acumula por horizonte ({h_grande}d > {h_chico}d) · {h_chico}={c1} {h_grande}={c2}"



def test_serigrafia_cola(app, db_clean):
    # Cola de envases por producción: un producto con presentación mapeada aparece con su envase + unidades teóricas.
    prod = "ZZ SERIG PROD"
    env = "ENV-SG-50"
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,1,1)", (prod,))
    _exec("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,stock_actual,stock_minimo) "
          "VALUES (?, 'Frasco SG 50','Envase',0,0)", (env,))
    _exec("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,etiqueta,volumen_ml,envase_codigo,ventas_mes_referencia,activo) "
          "VALUES (?, 'V50','50 ml',50,?,100,1)", (prod, env))
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES (?, date('now','-5 hours','+10 days'),1,'pendiente',5,'eos_plan')", (prod,))
    c = _login(app)
    r = c.get('/api/programacion/serigrafia-cola')
    assert r.status_code == 200, r.data
    d = r.get_json()
    it = next((x for x in (d.get('items') or []) if x.get('producto') == prod), None)
    assert it is not None, ('falta la producción en la cola', [x.get('producto') for x in (d.get('items') or [])])
    assert (it['envase_codigo'] or '').upper() == env, it
    assert it['unidades'] >= 99, ('~100 uds (5000g / 50ml)', it)



def test_marcacion_envase_set_y_cola(app, db_clean):
    # Compras define el método+proveedor del envase y aparece en la cola con fecha_envio (producción-15d).
    from .conftest import csrf_headers
    prod = "ZZ MARC PROD"
    base = "FR-MARC-30"
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,1,1)", (prod,))
    _exec("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,stock_actual,stock_minimo) "
          "VALUES (?, 'Frasco marc 30','Frasco',0,0)", (base,))
    _exec("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,etiqueta,volumen_ml,envase_codigo,ventas_mes_referencia,activo) "
          "VALUES (?,'V30','30ml',30,?,100,1)", (prod, base))
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES (?, date('now','-5 hours','+20 days'),1,'pendiente',5,'eos_plan')", (prod,))
    c = _login(app)
    r = c.post('/api/admin/marcacion-envase',
               json={'codigo': base, 'marcacion_tipo': 'serigrafia', 'marcacion_proveedor': 'ProvX'},
               headers=csrf_headers())
    assert r.status_code == 200, r.data
    d = c.get('/api/programacion/serigrafia-cola').get_json()
    it = next((x for x in (d.get('items') or []) if x.get('envase_codigo') == base), None)
    assert it is not None, ('base no en la cola', [x.get('envase_codigo') for x in (d.get('items') or [])])
    assert it['marcacion_tipo'] == 'serigrafia' and it['marcacion_proveedor'] == 'ProvX', it
    assert it.get('fecha_envio'), ('falta fecha_envio (producción-15d)', it)


def test_cola_excluye_pre_impreso(app, db_clean):
    # un envase marcado pre_impreso (viene de China serigrafiado) NO entra a la cola de alistar/marcar.
    prod = "ZZ PREIMP PROD"
    pre = "FR-PREIMP-X-30"
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,1,1)", (prod,))
    _exec("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,stock_actual,stock_minimo,marcacion_tipo) "
          "VALUES (?, 'Frasco preimp','Frasco',0,0,'pre_impreso')", (pre,))
    _exec("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,etiqueta,volumen_ml,envase_codigo,ventas_mes_referencia,activo) "
          "VALUES (?,'V30','30ml',30,?,100,1)", (prod, pre))
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES (?, date('now','-5 hours','+20 days'),1,'pendiente',5,'eos_plan')", (prod,))
    c = _login(app)
    d = c.get('/api/programacion/serigrafia-cola').get_json()
    it = next((x for x in (d.get('items') or []) if x.get('envase_codigo') == pre), None)
    assert it is None, ('el pre_impreso NO debe aparecer en la cola', [x.get('envase_codigo') for x in (d.get('items') or [])])


def test_envase_reparto_pesado_por_volumen(app, db_clean):
    # 5-jul (Sebastián · lote 90kg niacinamida): el KG se reparte PESADO POR VOLUMEN, no por unidades. Con VENTAS
    # IGUALES de 10 y 30ml, las UNIDADES producidas deben ser IGUALES (el 30ml se lleva 3x el bulk por unidad).
    # El bug viejo (aplicar share-de-unidades al kg) daba ~3x más unidades de 10ml que de 30ml.
    prod = "ZZ VOLPESO"
    envA, envB = "ENV-VP-10", "ENV-VP-30"
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) VALUES ('MP-VP','Mat','INCI',1)")
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,1,1)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES (?, 'MP-VP','Mat',10,0)", (prod,))
    for cod, d in ((envA, 'Frasco 10ml'), (envB, 'Frasco 30ml')):
        _exec("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,stock_actual,stock_minimo) "
              "VALUES (?,?,'Envase',0,0)", (cod, d))
    # ventas IGUALES por presentación (override manual · prioridad 1 · determinista sin Shopify)
    _exec("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,etiqueta,volumen_ml,envase_codigo,ventas_mes_referencia,activo) "
          "VALUES (?, 'A10','10 ml',10,?,100,1)", (prod, envA))
    _exec("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,etiqueta,volumen_ml,envase_codigo,ventas_mes_referencia,activo) "
          "VALUES (?, 'B30','30 ml',30,?,100,1)", (prod, envB))
    _exec("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,cantidad_kg,origen) "
          "VALUES (?, date('now','-5 hours','+5 days'),1,'pendiente',10,'eos_plan')", (prod,))
    c = _login(app)
    j = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp,mee").get_json()
    mees = j.get("mees") or []
    hmax = str(max(j["horizontes"]))
    a_it = next((m for m in mees if (m.get("codigo") or "").upper() == envA.upper()), None)
    b_it = next((m for m in mees if (m.get("codigo") or "").upper() == envB.upper()), None)
    assert a_it and b_it, ('faltan los frascos', [m.get('codigo') for m in mees])
    un10 = float(a_it["consumo"][hmax]); un30 = float(b_it["consumo"][hmax])
    # ventas iguales → unidades IGUALES (pesado por volumen · ~250 c/u para 10kg)
    assert abs(un10 - un30) <= max(un10, un30, 1) * 0.15, \
        f"con ventas iguales las unidades deben ser ~iguales (pesado por volumen) · 10ml={un10} 30ml={un30}"
    # DIENTES: el bug viejo (share-por-unidades sobre kg) daba 10ml ~3x el 30ml
    assert un10 < un30 * 2, \
        f"si 10ml >> 30ml es el bug de share-por-unidades (no pesado por volumen) · 10ml={un10} 30ml={un30}"
    # el bulk repartido no se pasa de 10kg (10000 ml)
    assert abs(un10 * 10 + un30 * 30 - 10000) <= 600, \
        f"el bulk repartido debe sumar ~10kg (10000 ml) · dio {un10*10+un30*30}"
