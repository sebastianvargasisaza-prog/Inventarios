"""Guardián anti-drift de los 2 motores de demanda de MP (#9 · Sebastián 16-jul-2026).

Contexto: existen DOS implementaciones separadas del cálculo de demanda de MP:
  - Motor "Generar OC"      → _compute_mp_deficit_aggregated  (endpoint /api/programacion/mps-deficit)
  - Motor pantalla Abastec. → abastecimiento_consumo_horizontes (endpoint /api/abastecimiento/consumo-horizontes)

Ambos leen la MISMA fuente (produccion_programada Fijas + B2B, - stock, - lo en camino)
y se mantuvieron en paridad a mano a lo largo de muchos fixes (M16/M47/M49, prefer-Fijo,
%-first, restar SOL/OC pendientes). El riesgo real es DRIFT FUTURO: que alguien toque un
motor y desalinee del otro (sobre/sub-compra silenciosa).

Este test siembra un escenario controlado, corre AMBOS motores y exige el MISMO déficit
por MP. Si algún cambio futuro los desalinea, este test se pone rojo antes de llegar a prod.
"""
import os
import sqlite3
from datetime import date, timedelta


def _db():
    return sqlite3.connect(os.environ["DB_PATH"])


def _seed(codigo, producto, stock_g, lotes, cant_kg, pct):
    con = _db()
    _cleanup(codigo, producto, _con=con)
    con.execute(
        "INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_comercial, activo, tipo_material, controla_stock) "
        "VALUES (?, 'MP Paridad', 1, 'MP', 1)", (codigo,))
    con.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote, operador) "
        "VALUES (?, 'MP Paridad', ?, 'Entrada', date('now'), 'LOTE-PAR', 'VIGENTE', 'seed')", (codigo, stock_g))
    con.execute(
        "INSERT OR REPLACE INTO formula_headers (producto_nombre, unidad_base_g, lote_size_kg, fecha_creacion, activo) "
        "VALUES (?, 5000, 5, datetime('now'), 1)", (producto,))
    con.execute(
        "INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
        "VALUES (?, ?, 'MP Paridad', ?, 500)", (producto, codigo, pct))
    fecha = (date.today() + timedelta(days=10)).isoformat()
    con.execute(
        "INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
        "VALUES (?, ?, ?, 'pendiente', ?, 'eos_plan')", (producto, fecha, lotes, cant_kg))
    con.commit()
    con.close()


def _cleanup(codigo, producto, _con=None):
    con = _con or _db()
    for q, p in [
        ("DELETE FROM formula_items WHERE producto_nombre=?", (producto,)),
        ("DELETE FROM formula_headers WHERE producto_nombre=?", (producto,)),
        ("DELETE FROM produccion_programada WHERE producto=?", (producto,)),
        ("DELETE FROM movimientos WHERE material_id=?", (codigo,)),
        ("DELETE FROM maestro_mps WHERE codigo_mp=?", (codigo,)),
    ]:
        con.execute(q, p)
    con.commit()
    if _con is None:
        con.close()


def _campo_pantalla(payload, cod_up, campo="deficit"):
    """Extrae <campo>@90 del MP cod_up del payload de consumo-horizontes (robusto a la forma)."""
    found = {}

    def _walk(o):
        if isinstance(o, dict):
            # la pantalla usa 'codigo'; el motor OC 'codigo_mp' · aceptar ambos
            c = o.get("codigo") or o.get("codigo_mp")
            d = o.get(campo)
            if c and isinstance(d, dict) and "90" in d:
                found[str(c).upper()] = float(d["90"])
            for v in o.values():
                _walk(v)
        elif isinstance(o, list):
            for v in o:
                _walk(v)

    _walk(payload)
    return found.get(cod_up, 0.0)


def _deficit_pantalla(payload, cod_up):
    return _campo_pantalla(payload, cod_up, "deficit")


def test_paridad_motores_demanda_mp(admin_client):
    """Generar OC (mps-deficit) y Pantalla (consumo-horizontes@90) → MISMO déficit por MP."""
    codigo, producto = "MPPARIDAD9", "PROD_PARIDAD_TEST9"
    # Demanda = 20 kg * 10% = 2000 g. Stock = 500 g → déficit REAL = 1500 g en AMBOS motores.
    _seed(codigo, producto, stock_g=500, lotes=4, cant_kg=20, pct=10)
    cu = codigo.upper()
    try:
        r_oc = admin_client.get("/api/programacion/mps-deficit")
        assert r_oc.status_code == 200, r_oc.data
        oc = {str(m["codigo_mp"]).upper(): float(m["deficit_g"])
              for m in (r_oc.get_json().get("mps") or [])}

        r_sc = admin_client.get("/api/abastecimiento/consumo-horizontes?horizontes=90")
        assert r_sc.status_code == 200, r_sc.data

        oc_d = oc.get(cu, 0.0)
        sc_d = _deficit_pantalla(r_sc.get_json(), cu)

        # El escenario DEBE producir déficit real (evita el falso-pass 0==0).
        assert oc_d > 100, (
            f"El seed no produjo déficit en el motor OC (oc={oc_d}). "
            f"Revisar filtros de produccion_programada del motor de compra.")
        # Paridad: los 2 motores deben coincidir (tolerancia de redondeo).
        assert abs(oc_d - sc_d) <= max(1.0, oc_d * 0.005), (
            f"DRIFT entre motores de demanda para {codigo}: "
            f"Generar OC={oc_d} g  vs  Pantalla Abastecimiento={sc_d} g. "
            f"Alguien cambió un motor sin alinear el otro (#9).")
    finally:
        _cleanup(codigo, producto)


def _seed_sol_pendiente(numero, codigo, cantidad_g):
    con = _db()
    con.execute("DELETE FROM solicitudes_compra_items WHERE numero=?", (numero,))
    con.execute("DELETE FROM solicitudes_compra WHERE numero=?", (numero,))
    con.execute(
        "INSERT INTO solicitudes_compra (numero, fecha, estado, solicitante, categoria) "
        "VALUES (?, date('now'), 'Pendiente', 'seed', 'Materia Prima')", (numero,))
    con.execute(
        "INSERT INTO solicitudes_compra_items (numero, codigo_mp, nombre_mp, cantidad_g) "
        "VALUES (?, ?, 'MP Paridad', ?)", (numero, codigo, cantidad_g))
    con.commit()
    con.close()


def _cleanup_sol(numero):
    con = _db()
    con.execute("DELETE FROM solicitudes_compra_items WHERE numero=?", (numero,))
    con.execute("DELETE FROM solicitudes_compra WHERE numero=?", (numero,))
    con.commit()
    con.close()


def _set_toggle(valor):
    con = _db()
    if valor is None:
        con.execute("DELETE FROM app_settings WHERE clave='abast_contar_pendiente'")
    else:
        con.execute("INSERT OR REPLACE INTO app_settings (clave, valor) VALUES ('abast_contar_pendiente', ?)", (valor,))
    con.commit()
    con.close()


def _seed_cuarentena(codigo, cantidad_g):
    con = _db()
    con.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, estado_lote, operador) "
        "VALUES (?, 'MP Paridad', ?, 'Entrada', date('now'), 'LOTE-CUAR', 'CUARENTENA', 'seed')", (codigo, cantidad_g))
    con.commit()
    con.close()


def test_neteo_regla_alejandro(admin_client):
    """Regla de neteo de Alejandro (22-jul · revisión ultracode):
      - lo EN CAMINO (SOL/OC pendiente) NO reduce el déficit → Alejandro ve la necesidad BRUTA
        (el pendiente se muestra aparte); el toggle abast_contar_pendiente ya no lo cambia.
      - la CUARENTENA (material que YA llegó por recepción, esperando QC de Calidad) SÍ se acredita
        en el déficit Y en 'Pedir' → no se re-compra lo que está físicamente en planta.
      - 'neto_a_pedir' (columna 'Pedir') == Generar OC: ambos netos de stock + cuarentena + en-camino.
    """
    codigo, producto = "MPPARIDAD9B", "PROD_PARIDAD_TEST9B"
    sol = "SOL-TEST-PARIDAD9"
    # Demanda 2000 g · stock 500 g · SOL pendiente 1000 g (en camino) · cuarentena 300 g (ya llegó).
    _seed(codigo, producto, stock_g=500, lotes=4, cant_kg=20, pct=10)
    _seed_sol_pendiente(sol, codigo, 1000)
    _seed_cuarentena(codigo, 300)
    cu = codigo.upper()
    try:
        payload = admin_client.get("/api/abastecimiento/consumo-horizontes?horizontes=90").get_json()
        deficit = _deficit_pantalla(payload, cu)
        neto = _campo_pantalla(payload, cu, "neto_a_pedir")
        oc = {str(m["codigo_mp"]).upper(): float(m["deficit_g"])
              for m in (admin_client.get("/api/programacion/mps-deficit").get_json().get("mps") or [])}
        oc_d = oc.get(cu, 0.0)

        # Déficit BRUTO de en-camino, pero ACREDITA cuarentena: 2000 - 500(stock) - 300(cuar) = 1200.
        assert abs(deficit - 1200) <= 5, (
            f"Déficit debe ser bruto de en-camino y acreditar cuarentena: esperado ~1200, got {deficit}")
        # 'Pedir' (neto_a_pedir) descuenta stock + cuarentena + en-camino: 2000 - 500 - 300 - 1000 = 200.
        assert abs(neto - 200) <= 5, (
            f"'Pedir' debe descontar stock+cuarentena+en-camino: esperado ~200, got {neto}")
        # Paridad EXACTA pantalla 'Pedir' == Generar OC (mismo neto).
        assert abs(neto - oc_d) <= max(1.0, oc_d * 0.005), (
            f"neto_a_pedir pantalla ({neto}) debe igualar Generar OC ({oc_d}) · paridad de motores.")
    finally:
        _set_toggle(None)
        _cleanup_sol(sol)
        _cleanup(codigo, producto)


def test_fanout_oc_agrupando_sols_no_infla_pendiente(admin_client):
    """Fan-out OC↔SOL (revisión ultracode 22-jul): una OC creada desde N solicitudes NO debe
    inflar el pendiente ×N (el LEFT JOIN a solicitudes_compra multiplicaba las filas → 'Pedir 0'
    falso → sub-compra). El pendiente debe ser la cantidad REAL de la OC, no × nº de SOLs."""
    codigo, producto = "MPFANOUT1", "PROD_FANOUT_TEST1"
    oc_num = "OC-FANOUT-TEST-1"
    _seed(codigo, producto, stock_g=100, lotes=5, cant_kg=20, pct=10)  # demanda 2000 g · stock 100
    con = _db()
    con.execute("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (oc_num,))
    con.execute("DELETE FROM ordenes_compra WHERE numero_oc=?", (oc_num,))
    con.execute("DELETE FROM solicitudes_compra WHERE numero_oc=?", (oc_num,))
    # 1 OC con item de 500 g agrupando 3 SOLs (mismo numero_oc). Fan-out daría 1500; correcto = 500.
    con.execute("INSERT INTO ordenes_compra (numero_oc, fecha, estado, proveedor, categoria) "
                "VALUES (?, date('now'), 'Autorizada', 'ProvFanout', 'MP')", (oc_num,))
    con.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g, cantidad_recibida_g) "
                "VALUES (?, ?, 'MP Paridad', 500, 0)", (oc_num, codigo))
    for i in range(3):
        con.execute("INSERT INTO solicitudes_compra (numero, fecha, estado, solicitante, categoria, numero_oc) "
                    "VALUES (?, date('now'), 'Aprobada', 'seed', 'Materia Prima', ?)", (f"SOL-FANOUT-{i}", oc_num))
    con.commit()
    con.close()
    cu = codigo.upper()
    try:
        payload = admin_client.get("/api/abastecimiento/consumo-horizontes?horizontes=90").get_json()
        neto = _campo_pantalla(payload, cu, "neto_a_pedir")
        # Con pendiente correcto (500): neto = 2000 - 100(stock) - 500 = 1400.
        # Con fan-out (1500 = 500×3):   neto = 2000 - 100 - 1500 = 400 (SUB-compra).
        assert abs(neto - 1400) <= 5, (
            f"El pendiente NO debe inflarse ×N por las 3 SOLs: neto esperado ~1400 (pend real 500), "
            f"got {neto} (si es ~400, el fan-out sigue vivo).")
    finally:
        con = _db()
        con.execute("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (oc_num,))
        con.execute("DELETE FROM ordenes_compra WHERE numero_oc=?", (oc_num,))
        con.execute("DELETE FROM solicitudes_compra WHERE numero_oc=?", (oc_num,))
        con.commit()
        con.close()
        _cleanup(codigo, producto)
