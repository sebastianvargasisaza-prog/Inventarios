"""M6 · 17-jun · Factibilidad debe separar FÍSICO de EN-CAMINO.

Caso real (Suero Multipéptidos): factibilidad decía "factible" porque sumaba
las compras en camino (SOL/OC pendientes) al stock físico, mientras en bodega
solo había 2.4 g y Alejandro decía "no alcanza". Ahora el veredicto distingue:
- factible_fisico: ¿alcanza con lo que hay en bodega HOY?
- solo_con_compras: factible SOLO cuando llegue lo pedido (hoy NO alcanza)
- mps_en_camino: qué MP fuerza esa espera
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


def _prod_factib(c, producto):
    r = c.get("/api/plan/factibilidad?dias=120&incluir_atrasadas=1")
    assert r.status_code == 200, r.data
    j = r.get_json()
    for p in j["producciones"]:
        if (p["producto"] or "").upper() == producto.upper():
            return p, j["resumen"]
    return None, j["resumen"]


def _seed(cod, prod, inci):
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES (?, ?, ?, 1)", (cod, "Pep " + cod, inci))
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 10, 1)", (prod,))
    # 10% de 10kg = 1000 g por lote (necesidad clara)
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES (?, ?, ?, 10, 1000)", (prod, cod, "Pep " + cod))


def test_factible_solo_con_compras_no_es_factible_fisico(app, db_clean):
    """Físico 200 g < necesidad 1000 g, pero hay SOL de 1000 g en camino →
    factible (con compras) pero NO factible_fisico → solo_con_compras=True."""
    cod, prod = "MP-M6CAM", "ZZ-M6CAM"
    _seed(cod, prod, "INCI M6CAM")
    # stock físico insuficiente: 200 g
    _exec("INSERT INTO movimientos (material_id, cantidad, tipo, lote, fecha, estado_lote) "
          "VALUES (?, 200, 'Entrada', 'L-M6CAM', date('now','-5 hours'), 'VIGENTE')", (cod,))
    # producción programada de 10 kg (necesita 1000 g)
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES (?, date('now','-5 hours','+5 days'), 1, 'pendiente', 10, 'eos_plan')", (prod,))
    # SOL pendiente de 1000 g (en camino)
    _exec("INSERT INTO solicitudes_compra (numero, estado, numero_oc) VALUES ('SOL-M6CAM', 'Pendiente', '')")
    _exec("INSERT INTO solicitudes_compra_items (numero, codigo_mp, cantidad_g) VALUES ('SOL-M6CAM', ?, 1000)", (cod,))

    c = _login(app)
    p, resumen = _prod_factib(c, prod)
    assert p is not None, "la producción debe aparecer en factibilidad"
    assert p["factible"] is True, "con la SOL en camino, sí es factible (cuando llegue)"
    assert p["factible_fisico"] is False, "con 200g físico NO alcanza para 1000g"
    assert p["solo_con_compras"] is True, "debe marcarse que solo es factible con compras"
    ids = [m["material_id"] for m in p["mps_en_camino"]]
    assert cod in ids, f"debe listar el péptido en camino · got {ids}"
    assert resumen.get("solo_con_compras", 0) >= 1


def test_factible_fisico_cuando_hay_stock_real(app, db_clean):
    """Con stock físico suficiente → factible_fisico=True, solo_con_compras=False."""
    cod, prod = "MP-M6FIS", "ZZ-M6FIS"
    _seed(cod, prod, "INCI M6FIS")
    _exec("INSERT INTO movimientos (material_id, cantidad, tipo, lote, fecha, estado_lote) "
          "VALUES (?, 5000, 'Entrada', 'L-M6FIS', date('now','-5 hours'), 'VIGENTE')", (cod,))
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES (?, date('now','-5 hours','+5 days'), 1, 'pendiente', 10, 'eos_plan')", (prod,))
    c = _login(app)
    p, _ = _prod_factib(c, prod)
    assert p is not None
    assert p["factible"] is True and p["factible_fisico"] is True
    assert p["solo_con_compras"] is False
    assert p["mps_en_camino"] == []


def test_bloqueada_ni_con_compras(app, db_clean):
    """Sin stock ni pendiente → bloqueada (factible False en ambos)."""
    cod, prod = "MP-M6BLO", "ZZ-M6BLO"
    _seed(cod, prod, "INCI M6BLO")
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES (?, date('now','-5 hours','+5 days'), 1, 'pendiente', 10, 'eos_plan')", (prod,))
    c = _login(app)
    p, _ = _prod_factib(c, prod)
    assert p is not None
    assert p["factible"] is False and p["factible_fisico"] is False
    assert p["solo_con_compras"] is False
