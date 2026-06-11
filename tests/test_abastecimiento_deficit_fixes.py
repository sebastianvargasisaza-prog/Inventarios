"""Fixes auditoría Abastecimiento/Factibilidad · 10-jun-2026.

BUG 2: ítems de fórmula cargados SOLO con % (sin gramos) deben aportar demanda
       (antes daban 0 → déficit subestimado / sub-compra).
BUG 3: el déficit debe restar lo YA pedido (SOL/OC en vuelo) antes de proponer compra
       (antes /generar-oc re-pedía el total → sobre-compra / SOLs duplicadas).
Ambos sobre `_compute_mp_deficit_aggregated`, vía GET /api/programacion/mps-deficit.
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


def _deficit_de(c, codigo):
    r = c.get("/api/programacion/mps-deficit")
    assert r.status_code == 200, r.data
    for it in (r.get_json().get("mps") or []):
        if (it.get("codigo_mp") or "").upper() == codigo.upper():
            return float(it.get("deficit_g") or 0)
    return 0.0


def test_deficit_pct_only_y_resta_pendiente(app, db_clean):
    cod = "MP-DEFZTEST"
    prod = "ZZ-DEFTEST"
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES (?, 'Material Deficit ZZ', 'TEST INCI ZZ', 1)", (cod,))
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 1, 1)", (prod,))
    # ítem cargado SOLO con porcentaje (cantidad_g_por_lote = 0) → BUG 2
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES (?, ?, 'Material Deficit ZZ', 10, 0)", (prod, cod))
    # una producción programada futura del producto (genera demanda)
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg) "
          "VALUES (?, date('now','-5 hours'), 1, 'pendiente', 1)", (prod,))

    c = _login(app)
    # BUG 2: 10% de 1 kg = 100 g de demanda · sin stock → déficit ~100 g (antes daba 0).
    d0 = _deficit_de(c, cod)
    assert d0 >= 99, f"pct-only debe generar demanda/déficit · got {d0}"

    # BUG 3: una SOL pendiente de 100 g debe RESTARSE del déficit → baja a ~0.
    _exec("INSERT INTO solicitudes_compra (numero, estado, numero_oc) VALUES ('SOL-DEFZTEST', 'Pendiente', '')")
    _exec("INSERT INTO solicitudes_compra_items (numero, codigo_mp, cantidad_g) VALUES ('SOL-DEFZTEST', ?, 120)", (cod,))
    d1 = _deficit_de(c, cod)
    assert d1 < d0, f"el pendiente debe reducir el déficit · antes {d0}, después {d1}"
    assert d1 <= 0.5, f"pendiente (120g) cubre la demanda (100g) → déficit ~0 · got {d1}"
