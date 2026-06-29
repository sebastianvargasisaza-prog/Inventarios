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
