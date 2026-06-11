"""PROPIEDAD 2 (Sebastián 10-jun-2026 · verificación empírica):
/api/abastecimiento/consumo-horizontes usa las cantidades REALES de la fórmula
(prioriza 'porcentaje'; si 0, usa 'cantidad_g_por_lote') y resuelve el material_id
de fórmula al código de BODEGA antes de reportar consumo.

  consumo[h] = (porcentaje/100) × cant_kg × 1000 × lotes   (EXACTO, sin redondeo)
  fallback:  cantidad_g_por_lote × (cant_kg / lote_size_kg)

Datos CONTROLADOS, prefijo 'QAFORMULA-', aislados con db_clean.
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


def _consumo_mp(app, codigo):
    c = _login(app)
    r = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp&horizontes=15,30,60,90")
    assert r.status_code == 200, r.data
    for m in r.get_json().get("mps", []):
        if (m.get("codigo") or "").upper() == codigo.upper():
            return m
    return None


def test_formula_usa_porcentaje_x_kg_exacto(app, db_clean):
    """% × kg × 1000 × lotes EXACTO. 10% de 7 kg = 700 g por lote; 3 lotes = 2100 g."""
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES ('QAFORMULA-PCT','Pct QA','PCT INCI QA',1)")
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('QAFORMULA-PRODPCT', 7, 1)")
    # Item por PORCENTAJE 10% · cantidad_g_por_lote=0 (debe IGNORARSE porque hay %)
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES ('QAFORMULA-PRODPCT', 'QAFORMULA-PCT', 'Pct QA', 10, 0)")
    # Programado Fijo: 3 lotes × 7 kg = 21 kg · en +3 días (entra en todos los horizontes)
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('QAFORMULA-PRODPCT', date('now','-5 hours','+3 days'), 3, 'pendiente', 21, 'eos_plan')")

    mp = _consumo_mp(app, "QAFORMULA-PCT")
    assert mp is not None, "la MP por % debe aparecer (match producción↔fórmula OK)"
    cons = mp["consumo"]
    # 10% de 21 kg = 0.10 × 21000 g = 2100 g EXACTO. Entra en 15/30/60/90.
    for h in ("15", "30", "60", "90"):
        assert abs(cons[h] - 2100.0) < 0.05, f"horizonte {h}: esperado 2100g, vi {cons[h]} · {cons}"


def test_formula_fallback_cantidad_g_por_lote(app, db_clean):
    """Item con cantidad_g_por_lote y SIN % usa g_por_lote × (cant_kg/lote_size).
    lote_size=5kg, g_por_lote=250g · cant_kg=15 (3 lotes) → 250 × (15/5) = 750 g."""
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES ('QAFORMULA-GPL','GporLote QA','GPL INCI QA',1)")
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('QAFORMULA-PRODGPL', 5, 1)")
    # porcentaje=0 fuerza el fallback a cantidad_g_por_lote
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES ('QAFORMULA-PRODGPL', 'QAFORMULA-GPL', 'GporLote QA', 0, 250)")
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('QAFORMULA-PRODGPL', date('now','-5 hours','+4 days'), 3, 'pendiente', 15, 'eos_plan')")

    mp = _consumo_mp(app, "QAFORMULA-GPL")
    assert mp is not None, "la MP por g_por_lote debe aparecer"
    cons = mp["consumo"]
    # 250 g/lote × (15 kg / 5 kg) = 250 × 3 = 750 g EXACTO
    for h in ("15", "30", "60", "90"):
        assert abs(cons[h] - 750.0) < 0.05, f"horizonte {h}: esperado 750g, vi {cons[h]} · {cons}"


def test_formula_resuelve_a_codigo_de_bodega(app, db_clean):
    """El código de FÓRMULA (fantasma, sin movimientos) se resuelve al código de
    BODEGA vía mp_formula_bridge antes de reportar. El consumo debe aparecer bajo
    el código de BODEGA (no el de fórmula), confirmando _resolver_material_bodega."""
    # Código de BODEGA (tiene stock real en movimientos) y código de FÓRMULA (fantasma)
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES ('QAFORMULA-BODEGA','Bodega QA','BODEGA INCI QA',1)")
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES ('QAFORMULA-FANTASMA','Fantasma QA','FANTASMA INCI QA',1)")
    # Stock neto producible bajo el código de BODEGA
    _exec("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, fecha, estado_lote) "
          "VALUES ('QAFORMULA-BODEGA','Bodega QA','Entrada', 50000, 'QAFORMULA-LOTE1', date('now','-5 hours'), 'APROBADO')")
    # Bridge: el código de fórmula (fantasma) apunta al de bodega
    _exec("INSERT INTO mp_formula_bridge (formula_material_id, bodega_material_id, activo) "
          "VALUES ('QAFORMULA-FANTASMA','QAFORMULA-BODEGA',1)")
    # Fórmula usa el código FANTASMA · 20% de 10 kg = 2000 g
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('QAFORMULA-PRODBRIDGE', 10, 1)")
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES ('QAFORMULA-PRODBRIDGE', 'QAFORMULA-FANTASMA', 'Fantasma QA', 20, 0)")
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('QAFORMULA-PRODBRIDGE', date('now','-5 hours','+2 days'), 1, 'pendiente', 10, 'eos_plan')")

    # El consumo debe reportarse bajo el código de BODEGA (resuelto), no el fantasma
    mp_bod = _consumo_mp(app, "QAFORMULA-BODEGA")
    mp_fant = _consumo_mp(app, "QAFORMULA-FANTASMA")
    assert mp_bod is not None, "el consumo debe colapsarse al código de BODEGA resuelto"
    assert abs(mp_bod["consumo"]["15"] - 2000.0) < 0.05, mp_bod["consumo"]
    # Y el stock leído debe ser el de bodega (50000 g) → sin déficit en 15d
    assert abs(mp_bod["stock_actual_g"] - 50000.0) < 0.5, mp_bod
    assert mp_fant is None, "NO debe quedar consumo bajo el código de fórmula fantasma (debe colapsar)"
