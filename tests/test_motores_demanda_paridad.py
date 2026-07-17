"""17-jun · PARIDAD entre los dos motores de demanda de compra.

Hay dos motores: el de la PANTALLA Abastecimiento (abastecimiento_consumo_horizontes,
verificado M16) y el de /generar-oc · /mps-deficit (_compute_mp_deficit_aggregated).
Hoy alineamos sus filtros (M47). Este test los AMARRA: si en el futuro alguien toca
uno y diverge del otro, el test falla. Es la red que evita volver a tener dos números
distintos para "qué comprar" (la deuda técnica de mantener dos motores).
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
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def test_mps_deficit_vs_consumo_horizontes_coinciden(app, db_clean):
    """Mismo escenario → el déficit de /mps-deficit (motor de compra) debe coincidir
    con el déficit del horizonte 90 de /consumo-horizontes (motor de pantalla)."""
    cod, prod = "MP-PARID1", "ZZ-PARID1"
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES (?, 'Material Paridad', 'INCI PARIDAD1', 1)", (cod,))
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 10, 1)", (prod,))
    # 10% de 10kg = 1000 g por lote
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES (?, ?, 'Material Paridad', 10, 1000)", (prod, cod))
    # producción Fija (origen reconocido por AMBOS motores) en el horizonte
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES (?, date('now','-5 hours','+10 days'), 1, 'pendiente', 10, 'eos_plan')", (prod,))
    # algo de stock parcial (200 g) para que el déficit no sea trivial
    _exec("INSERT INTO movimientos (material_id, cantidad, tipo, lote, fecha, estado_lote) "
          "VALUES (?, 200, 'Entrada', 'L-PARID1', date('now','-5 hours'), 'VIGENTE')", (cod,))

    c = _login(app)
    # motor de compra
    r1 = c.get("/api/programacion/mps-deficit")
    assert r1.status_code == 200, r1.data
    def1 = 0.0
    for it in (r1.get_json().get("mps") or []):
        if (it.get("codigo_mp") or "").upper() == cod.upper():
            def1 = float(it.get("deficit_g") or 0)
    # motor de pantalla
    r2 = c.get("/api/abastecimiento/consumo-horizontes")
    assert r2.status_code == 200, r2.data
    j2 = r2.get_json()
    hmax = str(max(j2["horizontes"]))
    def2 = 0.0
    for it in (j2.get("mps") or []):
        if (it.get("codigo") or "").upper() == cod.upper():
            def2 = float(it.get("deficit", {}).get(hmax) or 0)

    # ambos deben ver ~800 g de déficit (1000 necesidad − 200 stock) y COINCIDIR
    assert def1 > 0 and def2 > 0, f"ambos motores deben ver déficit · compra={def1} pantalla={def2}"
    assert abs(def1 - def2) <= 1.0, \
        f"los dos motores DEBEN dar el mismo déficit · compra={def1} pantalla={def2} (divergencia = deuda técnica reabierta)"


def test_paridad_acredita_pendiente_igual(app, db_clean):
    """Una OC 'Pagada' no recibida debe reducir el déficit IGUAL en ambos motores."""
    cod, prod = "MP-PARID2", "ZZ-PARID2"
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES (?, 'Material Paridad 2', 'INCI PARIDAD2', 1)", (cod,))
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 10, 1)", (prod,))
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES (?, ?, 'Material Paridad 2', 10, 1000)", (prod, cod))
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES (?, date('now','-5 hours','+10 days'), 1, 'pendiente', 10, 'eos_plan')", (prod,))
    # OC Pagada no recibida de 400 g
    _exec("INSERT INTO ordenes_compra (numero_oc, estado, fecha_recepcion) VALUES ('OC-PARID2','Pagada','')")
    _exec("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, cantidad_g, cantidad_recibida_g) "
          "VALUES ('OC-PARID2', ?, 400, 0)", (cod,))

    c = _login(app)
    d1 = next((float(it.get("deficit_g") or 0) for it in (c.get("/api/programacion/mps-deficit").get_json().get("mps") or [])
               if (it.get("codigo_mp") or "").upper() == cod.upper()), 0.0)
    j2 = c.get("/api/abastecimiento/consumo-horizontes").get_json()
    hmax = str(max(j2["horizontes"]))
    # Sebastián 17-jul (B2c · unificación): la COMPRA (mps-deficit, vía el núcleo único) usa el NETO
    # a pedir · se compara contra `neto_a_pedir` de la pantalla (NO el `deficit` bruto, que por diseño
    # NO resta lo pendiente · M39). Ambos = necesidad 1000 − pendiente 400 = 600.
    d2 = next((float(it.get("neto_a_pedir", {}).get(hmax) or 0) for it in (j2.get("mps") or [])
               if (it.get("codigo") or "").upper() == cod.upper()), 0.0)
    assert abs(d1 - d2) <= 1.0, f"la COMPRA debe = neto_a_pedir de la pantalla · compra={d1} pantalla={d2}"
