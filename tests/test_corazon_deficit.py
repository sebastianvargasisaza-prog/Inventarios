"""PROPIEDAD 3 · deficit[h] = max(0, consumo[h] - stock - pendiente_compras).

Verifica EMPÍRICAMENTE que /api/abastecimiento/consumo-horizontes:
  · resta BIEN el stock físico (vía movimientos Entrada) del consumo,
  · resta TAMBIÉN el pendiente de compras (SOL Pendiente sin OC),
  · nunca devuelve déficit negativo,
  · si stock+pendiente cubren el consumo → déficit = 0.

Datos CONTROLADOS con prefijo único 'QADEF-' / 'DEFICIT-' para aislar.
Cada MP resuelve a sí misma en _resolver_material_bodega (tier 1: tiene
movimientos propios) → los códigos no se colapsan entre sí.
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


def _seed_mp(codigo, nombre):
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES (?,?,?,1)", (codigo, nombre, "INCI " + codigo))


def _seed_formula(prod, codigo_mp, nombre_mp, pct):
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,1,1)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES (?, ?, ?, ?, 0)", (prod, codigo_mp, nombre_mp, pct))


def _programar(prod, kg, dias):
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES (?, date('now','-5 hours','+' || ? || ' days'), 1, 'pendiente', ?, 'eos_plan')",
          (prod, str(dias), kg))


def _entrada_stock(codigo, nombre, gramos):
    """Seed stock físico DISPONIBLE vía movimientos (tipo Entrada · sin cuarentena)."""
    _exec("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote) "
          "VALUES (?, ?, ?, 'Entrada', date('now'), ?, '')",
          (codigo, nombre, gramos, "LOTE-" + codigo))


def _sol_pendiente(numero, codigo, nombre, gramos):
    """Seed pendiente de compras: SOL en estado Pendiente, SIN numero_oc."""
    _exec("INSERT INTO solicitudes_compra (numero, fecha, estado, categoria, numero_oc) "
          "VALUES (?, date('now'), 'Pendiente', 'Materia Prima', '')", (numero,))
    _exec("INSERT INTO solicitudes_compra_items (numero, codigo_mp, nombre_mp, cantidad_g) "
          "VALUES (?, ?, ?, ?)", (numero, codigo, nombre, gramos))


def test_deficit_resta_stock(app, db_clean):
    """A: consumo 5000g · stock 1000g · pendiente 0 → deficit = 4000g."""
    _seed_mp("DEFICIT-A", "Deficit A")
    _seed_formula("QADEF-PRODA", "DEFICIT-A", "Deficit A", 50)  # 50% de 10kg = 5000g
    _programar("QADEF-PRODA", 10, 3)                            # entra en todos los horizontes
    _entrada_stock("DEFICIT-A", "Deficit A", 1000)             # stock físico 1000g
    mp = _consumo_mp(app, "DEFICIT-A")
    assert mp is not None, "MP con consumo debe aparecer"
    assert abs(mp["consumo"]["15"] - 5000) < 1, mp["consumo"]
    assert abs(mp["stock_actual_g"] - 1000) < 1, mp["stock_actual_g"]
    assert abs(mp["pendiente_compras_g"] - 0) < 1, mp["pendiente_compras_g"]
    # deficit = max(0, 5000 - 1000 - 0) = 4000
    assert abs(mp["deficit"]["15"] - 4000) < 1, f"deficit debe restar stock · {mp['deficit']}"
    assert abs(mp["deficit"]["90"] - 4000) < 1, f"acumulativo igual (1 sola prod) · {mp['deficit']}"


def test_deficit_resta_stock_mas_pendiente(app, db_clean):
    """B: consumo 5000g · stock 1000g · pendiente 2000g → deficit = 2000g.
    Confirma que SE RESTAN AMBOS (stock + pendiente_compras)."""
    _seed_mp("DEFICIT-B", "Deficit B")
    _seed_formula("QADEF-PRODB", "DEFICIT-B", "Deficit B", 50)  # 50% de 10kg = 5000g
    _programar("QADEF-PRODB", 10, 3)
    _entrada_stock("DEFICIT-B", "Deficit B", 1000)            # stock físico 1000g
    _sol_pendiente("QADEF-SOL-B", "DEFICIT-B", "Deficit B", 2000)  # pendiente 2000g
    mp = _consumo_mp(app, "DEFICIT-B")
    assert mp is not None
    assert abs(mp["consumo"]["15"] - 5000) < 1, mp["consumo"]
    assert abs(mp["stock_actual_g"] - 1000) < 1, mp["stock_actual_g"]
    assert abs(mp["pendiente_compras_g"] - 2000) < 1, mp["pendiente_compras_g"]
    # deficit = max(0, 5000 - 1000 - 2000) = 2000
    assert abs(mp["deficit"]["15"] - 2000) < 1, f"deficit debe restar stock+pendiente · {mp['deficit']}"


def test_deficit_nunca_negativo_si_stock_cubre(app, db_clean):
    """C: consumo 5000g · stock 8000g → deficit = 0 (nunca negativo)."""
    _seed_mp("DEFICIT-C", "Deficit C")
    _seed_formula("QADEF-PRODC", "DEFICIT-C", "Deficit C", 50)  # 50% de 10kg = 5000g
    _programar("QADEF-PRODC", 10, 3)
    _entrada_stock("DEFICIT-C", "Deficit C", 8000)            # stock cubre de sobra
    mp = _consumo_mp(app, "DEFICIT-C")
    assert mp is not None
    assert abs(mp["consumo"]["15"] - 5000) < 1, mp["consumo"]
    assert abs(mp["stock_actual_g"] - 8000) < 1, mp["stock_actual_g"]
    # deficit = max(0, 5000 - 8000 - 0) = 0  (NO -3000)
    for h in ("15", "30", "60", "90"):
        assert mp["deficit"][h] == 0, f"deficit nunca negativo · h={h} · {mp['deficit']}"
    # urgencia debe ser OK (sin déficit en ningún horizonte)
    assert mp["urgencia"] == "OK", f"sin déficit → urgencia OK · {mp['urgencia']}"
