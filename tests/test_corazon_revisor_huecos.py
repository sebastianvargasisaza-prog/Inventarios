"""REVISOR ESCEPTICO · huecos no cubiertos por los 5 agentes.

Tres casos que pueden esconder errores en las SOLICITUDES de compra:
  H1 · MULTI-LOTE del MISMO producto (2 filas produccion_programada, mismo prod,
       distintas fechas) → consumo debe SUMAR ambos por horizonte (no quedarse uno).
  H2 · BRIDGE + PENDIENTE: la formula usa un codigo FANTASMA (bridge→bodega),
       el stock y el PENDIENTE de compra estan bajo el codigo de BODEGA.
       Tras colapsar la demanda a bodega, el deficit debe restar ESE pendiente.
       (Si el pendiente no cruza → SOL duplicada / sobre-compra.)
  H3 · CUARENTENA: stock en estado_lote='CUARENTENA' NO debe contar como
       disponible → debe seguir habiendo deficit (no falso "tengo stock").
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


def _mp(app, codigo):
    c = _login(app)
    r = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp&horizontes=15,30,60,90")
    assert r.status_code == 200, r.data
    for m in r.get_json().get("mps", []):
        if (m.get("codigo") or "").upper() == codigo.upper():
            return m
    return None


def test_H1_multilote_mismo_producto_suma(app, db_clean):
    """2 lotes del MISMO producto a +3d y +50d → consumo acumula AMBOS."""
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES ('QAHUECO-H1','HuecoH1','HUECO H1 INCI',1)")
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('QAHUECO-PRODH1', 1, 1)")
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES ('QAHUECO-PRODH1', 'QAHUECO-H1', 'HuecoH1', 10, 0)")
    # Lote 1: +3d, 10kg → 1000g (entra en todos). Lote 2: +50d, 10kg → 1000g (entra desde 60).
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('QAHUECO-PRODH1', date('now','-5 hours','+3 days'), 1, 'pendiente', 10, 'eos_plan')")
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('QAHUECO-PRODH1', date('now','-5 hours','+50 days'), 1, 'pendiente', 10, 'eos_plan')")
    mp = _mp(app, "QAHUECO-H1")
    assert mp is not None
    cons = mp["consumo"]
    assert abs(cons["15"] - 1000) < 1, f"15d = solo lote1 (1000) · {cons}"
    assert abs(cons["30"] - 1000) < 1, f"30d = solo lote1 (1000) · {cons}"
    assert abs(cons["60"] - 2000) < 1, f"60d = lote1+lote2 (2000) · MULTI-LOTE debe sumar · {cons}"
    assert abs(cons["90"] - 2000) < 1, f"90d = 2000 · {cons}"


def test_H2_pendiente_cruza_por_bridge_a_bodega(app, db_clean):
    """Formula usa FANTASMA→bridge→BODEGA. Stock y PENDIENTE bajo BODEGA.
    Tras colapsar demanda a bodega, deficit resta el pendiente (MODO 'contar pendiente')."""
    # Sebastián 12-jul · el default cambió a NO contar pendiente (M39/M66) · este test valida el bridge del
    # PENDIENTE + su resta → fijar el modo viejo.
    _exec("INSERT OR REPLACE INTO app_settings (clave, valor) VALUES ('abast_contar_pendiente','1')")
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES ('QAHUECO-BOD','HuecoBod','HUECO BOD INCI',1)")
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES ('QAHUECO-FANT','HuecoFant','HUECO FANT INCI',1)")
    # Stock fisico bajo el codigo de BODEGA: 1000g
    _exec("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, fecha, estado_lote) "
          "VALUES ('QAHUECO-BOD','HuecoBod','Entrada', 1000, 'QAHUECO-BOD-L1', date('now','-5 hours'), 'APROBADO')")
    # Pendiente de compra registrado bajo el codigo de BODEGA: 2000g
    _exec("INSERT INTO solicitudes_compra (numero, fecha, estado, categoria, numero_oc) "
          "VALUES ('SOL-QAHUECO-H2', date('now'), 'Pendiente', 'Materia Prima', '')")
    _exec("INSERT INTO solicitudes_compra_items (numero, codigo_mp, nombre_mp, cantidad_g) "
          "VALUES ('SOL-QAHUECO-H2', 'QAHUECO-BOD', 'HuecoBod', 2000)")
    # Bridge fantasma→bodega
    _exec("INSERT INTO mp_formula_bridge (formula_material_id, bodega_material_id, activo) "
          "VALUES ('QAHUECO-FANT','QAHUECO-BOD',1)")
    # Formula usa FANTASMA · 80% de 10kg = 8000g
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('QAHUECO-PRODH2', 10, 1)")
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES ('QAHUECO-PRODH2', 'QAHUECO-FANT', 'HuecoFant', 80, 0)")
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('QAHUECO-PRODH2', date('now','-5 hours','+3 days'), 1, 'pendiente', 10, 'eos_plan')")

    mp = _mp(app, "QAHUECO-BOD")
    assert mp is not None, "el consumo debe colapsar a BODEGA"
    cons = mp["consumo"]; defc = mp["deficit"]
    assert abs(cons["15"] - 8000) < 1, f"consumo 8000g bajo bodega · {cons}"
    assert abs(mp["stock_actual_g"] - 1000) < 1, mp["stock_actual_g"]
    # CLAVE: el pendiente bajo el codigo de bodega DEBE acreditarse
    assert abs(mp["pendiente_compras_g"] - 2000) < 1, (
        f"el pendiente bajo codigo BODEGA debe cruzar (sino → SOL duplicada) · got {mp['pendiente_compras_g']}")
    # deficit = max(0, 8000 - 1000 - 2000) = 5000
    assert abs(defc["15"] - 5000) < 1, f"deficit debe restar stock+pendiente cruzado · {defc}"


def test_H3_cuarentena_no_cuenta_como_disponible(app, db_clean):
    """Stock en CUARENTENA NO es disponible → sigue habiendo deficit completo."""
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES ('QAHUECO-H3','HuecoH3','HUECO H3 INCI',1)")
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES ('QAHUECO-PRODH3', 1, 1)")
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES ('QAHUECO-PRODH3', 'QAHUECO-H3', 'HuecoH3', 50, 0)")
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('QAHUECO-PRODH3', date('now','-5 hours','+3 days'), 1, 'pendiente', 10, 'eos_plan')")
    # 5000g de consumo. Todo el stock (9999g) esta en CUARENTENA → NO disponible.
    _exec("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, fecha, estado_lote) "
          "VALUES ('QAHUECO-H3','HuecoH3','Entrada', 9999, 'QAHUECO-H3-CUAR', date('now','-5 hours'), 'CUARENTENA')")
    mp = _mp(app, "QAHUECO-H3")
    assert mp is not None
    assert abs(mp["consumo"]["15"] - 5000) < 1, mp["consumo"]
    assert abs(mp["stock_actual_g"] - 0) < 1, (
        f"stock en CUARENTENA NO debe contar como disponible · got {mp['stock_actual_g']}")
    assert abs(mp["deficit"]["15"] - 5000) < 1, (
        f"deficit completo (cuarentena no cubre) · got {mp['deficit']}")
