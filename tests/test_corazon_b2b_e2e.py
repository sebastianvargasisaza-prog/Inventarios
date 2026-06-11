"""Cierra el hueco que marcó el revisor escéptico (11-jun): el anti-doble-conteo B2B
del cálculo de Abastecimiento NO tenía test E2E que tocara la tabla pedidos_b2b.

Mecanismo (programacion.py ~10551-10561): los pedidos_b2b 'pendiente' cuentan en (8b)
SOLO si NO están integrados a un lote (LEFT JOIN pedidos_b2b_lote ... WHERE pbl.id IS NULL).
Si ya tienen lote → se cuentan vía produccion_programada (8a), una sola vez.
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


def _consumo(app, codigo, h="15"):
    c = _login(app)
    r = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp&horizontes=15,30,60,90")
    assert r.status_code == 200, r.data
    for m in r.get_json().get("mps", []):
        if (m.get("codigo") or "").upper() == codigo.upper():
            return float(m["consumo"].get(h, 0) or 0)
    return None


def _formula(prod, mp, pct=10):
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) "
          "VALUES (?,?,?,1)", (mp, mp, mp + " INCI"))
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES (?,10,1)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje,cantidad_g_por_lote) "
          "VALUES (?,?,?,?,0)", (prod, mp, mp, pct))


def test_b2b_pendiente_sin_lote_cuenta(app, db_clean):
    """Pedido B2B 'pendiente' sin lote vinculado → SÍ aporta consumo (path 8b)."""
    prod, mp = "QAB2B PROD UNO", "MP-QAB2B1"
    _formula(prod, mp, pct=10)
    # 100 uds × 30 ml = 3 kg → 10% × 3kg × 1000 = 300 g
    _exec("INSERT INTO pedidos_b2b (cliente_id, cliente_nombre, producto_nombre, cantidad_uds, ml_unidad, "
          "fecha_estimada, estado, creado_por) VALUES ('9001', 'Kelly QA', ?, 100, 30, date('now','-5 hours','+10 days'), 'pendiente', 'qa')",
          (prod,))
    cons = _consumo(app, mp, "15")
    assert cons is not None, "la MP del pedido B2B pendiente debe aparecer"
    assert abs(cons - 300) < 1, f"consumo B2B = 10% × 3kg × 1000 = 300g · obtuve {cons}"


def test_b2b_integrado_a_lote_no_doble_cuenta(app, db_clean):
    """Pedido B2B integrado a un lote → se cuenta SOLO vía la producción (8a), no dos veces."""
    prod, mp = "QAB2B PROD DOS", "MP-QAB2B2"
    _formula(prod, mp, pct=10)
    # Producción Fija eos_b2b de 5 kg → 10% × 5kg × 1000 = 500 g (path 8a)
    pp_id = _exec("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, estado, origen) "
                  "VALUES (?, date('now','-5 hours','+5 days'), 5, 1, 'pendiente', 'eos_b2b')", (prod,))
    # Pedido B2B del MISMO producto (si se contara aparte sumaría 300 g más = 800)
    pb_id = _exec("INSERT INTO pedidos_b2b (cliente_id, cliente_nombre, producto_nombre, cantidad_uds, ml_unidad, "
                  "fecha_estimada, estado, creado_por) VALUES ('9001', 'Kelly QA', ?, 100, 30, date('now','-5 hours','+5 days'), 'pendiente', 'qa')",
                  (prod,))
    # Integrado al lote → debe EXCLUIRse del path 8b (pbl.id IS NULL falla)
    _exec("INSERT INTO pedidos_b2b_lote (pedido_b2b_id, lote_produccion_id, kg_aporte, unidades_aporte, "
          "ml_unidad, envase_codigo, modo, cliente_nombre) VALUES (?, ?, 3, 100, 30, '', 'sumado_a_lote_canonico', 'Kelly QA')",
          (pb_id, pp_id))
    cons = _consumo(app, mp, "15")
    assert cons is not None, mp
    # Solo la producción (500 g) · NO 800 g (no doble conteo)
    assert abs(cons - 500) < 1, f"debe contar SOLO el lote (500g), no doble (800g) · obtuve {cons}"
