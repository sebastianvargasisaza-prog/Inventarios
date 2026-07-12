"""Fixes auditoría Abastecimiento (motor de COMPRA) · 17-jun-2026.

El motor que alimenta /generar-oc · /mps-deficit (`_compute_mp_deficit_aggregated`)
y el motor de la PANTALLA Abastecimiento (`abastecimiento_consumo_horizontes`)
divergían y sobre/sub-compraban. Alineados al motor verificado:

[1] No contar como demanda los lotes YA INICIADOS (inventario_descontado_at set):
    su MP ya bajó del stock → contarlos = DOBLE conteo → sobre-compra.
[2] Respetar cantidad_kg editada del lote (antes usaba lote_size×lotes a secas).
[3] Acreditar OC 'Pagada' aún NO recibida como pendiente (igual que el helper
    canónico _pendiente_en_compras_bulk) → no re-comprar MP ya pagada en tránsito.
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


def _seed_formula(cod, prod):
    # Nombre/INCI ÚNICO por código (maestro_mps persiste en la sesión de tests · si
    # comparten INCI, el resolver por-INCI los colapsa al de más stock y el consumo
    # se atribuye al MP equivocado).
    nombre = "Material " + cod
    inci = "INCI " + cod.replace("-", "")
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES (?, ?, ?, 1)", (cod, nombre, inci))
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 1, 1)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES (?, ?, ?, 10, 0)", (prod, cod, nombre))


def _deficit_mps(c, codigo):
    """déficit del motor de COMPRA (/mps-deficit · _compute_mp_deficit_aggregated)."""
    r = c.get("/api/programacion/mps-deficit")
    assert r.status_code == 200, r.data
    for it in (r.get_json().get("mps") or []):
        if (it.get("codigo_mp") or "").upper() == codigo.upper():
            return float(it.get("deficit_g") or 0)
    return 0.0


def _item_horizontes(c, codigo):
    """item de la PANTALLA Abastecimiento (consumo-horizontes)."""
    r = c.get("/api/abastecimiento/consumo-horizontes")
    assert r.status_code == 200, r.data
    for it in (r.get_json().get("mps") or []):
        if (it.get("codigo") or "").upper() == codigo.upper():
            return it
    return None


def test_deficit_no_cuenta_lote_iniciado(app, db_clean):
    """[1] Un lote con inventario_descontado_at puesto NO debe sumar demanda."""
    cod, prod = "MP-INI17", "ZZ-INI17"
    _seed_formula(cod, prod)
    # Lote YA INICIADO (MP ya descontada) → su demanda NO debe contar.
    _exec("INSERT INTO produccion_programada "
          "(producto, fecha_programada, lotes, estado, cantidad_kg, inventario_descontado_at) "
          "VALUES (?, date('now','-5 hours','+2 days'), 1, 'en_proceso', 1, "
          "date('now','-5 hours'))", (prod,))
    c = _login(app)
    d_iniciado = _deficit_mps(c, cod)
    assert d_iniciado <= 0.5, f"lote iniciado NO debe generar déficit (doble conteo) · got {d_iniciado}"

    # Control: un lote PENDIENTE (no descontado) del mismo producto SÍ cuenta.
    _exec("INSERT INTO produccion_programada "
          "(producto, fecha_programada, lotes, estado, cantidad_kg) "
          "VALUES (?, date('now','-5 hours','+3 days'), 1, 'pendiente', 1)", (prod,))
    d_pendiente = _deficit_mps(c, cod)
    assert d_pendiente >= 99, f"lote pendiente (10% de 1kg) debe dar ~100g de déficit · got {d_pendiente}"


def test_deficit_respeta_cantidad_kg(app, db_clean):
    """[2] La demanda usa cantidad_kg editada, no lote_size×lotes."""
    cod, prod = "MP-KG17", "ZZ-KG17"
    _seed_formula(cod, prod)
    # lote_size_kg=1 pero el usuario editó el lote a 5 kg → demanda = 10% × 5kg = 500g.
    _exec("INSERT INTO produccion_programada "
          "(producto, fecha_programada, lotes, estado, cantidad_kg) "
          "VALUES (?, date('now','-5 hours','+2 days'), 1, 'pendiente', 5)", (prod,))
    c = _login(app)
    d = _deficit_mps(c, cod)
    assert 480 <= d <= 520, f"cantidad_kg=5 → demanda ~500g (no 100g del lote_size) · got {d}"


def test_consumo_horizontes_acredita_oc_pagada_no_recibida(app, db_clean):
    """[3] La pantalla Abastecimiento cuenta una OC 'Pagada' sin recibir como
    pendiente → no re-sugiere comprar MP ya pagada en tránsito (MODO 'contar pendiente')."""
    # Sebastián 12-jul · el default cambió a NO contar pendiente (M39/M66) · este test valida que la OC Pagada
    # se acredita como pendiente en el modo viejo → fijarlo.
    _exec("INSERT OR REPLACE INTO app_settings (clave, valor) VALUES ('abast_contar_pendiente','1')")
    cod, prod = "MP-PAG17", "ZZ-PAG17"
    _seed_formula(cod, prod)
    # producción FIJA en horizonte (origen requerido por consumo-horizontes).
    _exec("INSERT INTO produccion_programada "
          "(producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES (?, date('now','-5 hours','+3 days'), 1, 'pendiente', 1, 'eos_plan')", (prod,))
    c = _login(app)
    it0 = _item_horizontes(c, cod)
    assert it0 is not None, "la MP debe aparecer (tiene consumo)"
    # sin stock ni pendiente → déficit ~100g en el horizonte mayor
    h_max = str(max(c.get('/api/abastecimiento/consumo-horizontes').get_json()['horizontes']))
    assert it0['deficit'][h_max] >= 99, f"sin suministro → déficit ~100g · got {it0['deficit']}"

    # OC 'Pagada' SIN recibir (fecha_recepcion vacía) de 120g → debe acreditarse.
    _exec("INSERT INTO ordenes_compra (numero_oc, estado, fecha_recepcion) "
          "VALUES ('OC-PAG17', 'Pagada', '')")
    _exec("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, cantidad_g, cantidad_recibida_g) "
          "VALUES ('OC-PAG17', ?, 120, 0)", (cod,))
    it1 = _item_horizontes(c, cod)
    assert it1['pendiente_compras_g'] >= 119, \
        f"OC Pagada-no-recibida debe contar como pendiente · got {it1['pendiente_compras_g']}"
    assert it1['deficit'][h_max] <= 0.5, \
        f"pendiente (120g) cubre el consumo (100g) → déficit ~0 · got {it1['deficit']}"


def test_consumo_horizontes_oc_pagada_recibida_no_acredita(app, db_clean):
    """[3-neg] Una OC 'Pagada' YA recibida (fecha_recepcion puesta) NO se cuenta
    como pendiente (ya entró al stock por su recepción)."""
    cod, prod = "MP-PAGR17", "ZZ-PAGR17"
    _seed_formula(cod, prod)
    _exec("INSERT INTO produccion_programada "
          "(producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES (?, date('now','-5 hours','+3 days'), 1, 'pendiente', 1, 'eos_plan')", (prod,))
    # Pagada YA recibida → NO pendiente.
    _exec("INSERT INTO ordenes_compra (numero_oc, estado, fecha_recepcion) "
          "VALUES ('OC-PAGR17', 'Pagada', '2026-06-10')")
    _exec("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, cantidad_g, cantidad_recibida_g) "
          "VALUES ('OC-PAGR17', ?, 120, 120)", (cod,))
    c = _login(app)
    it = _item_horizontes(c, cod)
    assert it is not None
    assert it['pendiente_compras_g'] <= 0.5, \
        f"OC Pagada YA recibida NO es pendiente · got {it['pendiente_compras_g']}"
