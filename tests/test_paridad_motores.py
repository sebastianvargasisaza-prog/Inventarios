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


def test_paridad_motores_pendiente_segun_toggle(admin_client):
    """Semántica del interruptor `abast_contar_pendiente` (Sebastián 12-jul).

    Divergencia documentada #9: solo la PANTALLA respeta este toggle; el motor de
    Generar OC SIEMPRE resta lo pendiente (FIX 10-jun · no duplicar SOLs).
      - toggle ON  → la pantalla también resta → los 2 motores COINCIDEN (neto).
      - toggle OFF → la pantalla NO resta (bruto) → difieren A PROPÓSITO.
    Este test bloquea que, CON el toggle ON, ambos resten idéntico. Si alguien
    cambia cómo un motor resta pendientes, se pone rojo.
    """
    codigo, producto = "MPPARIDAD9B", "PROD_PARIDAD_TEST9B"
    sol = "SOL-TEST-PARIDAD9"
    # Demanda 2000 g, stock 500 g, SOL pendiente 1000 g.
    _seed(codigo, producto, stock_g=500, lotes=4, cant_kg=20, pct=10)
    _seed_sol_pendiente(sol, codigo, 1000)
    cu = codigo.upper()
    try:
        # ── Toggle ON: ambos netos (2000 - 500 - 1000 = 500) y coinciden ──
        _set_toggle("1")
        oc = {str(m["codigo_mp"]).upper(): float(m["deficit_g"])
              for m in (admin_client.get("/api/programacion/mps-deficit").get_json().get("mps") or [])}
        sc = _deficit_pantalla(admin_client.get("/api/abastecimiento/consumo-horizontes?horizontes=90").get_json(), cu)
        oc_on, sc_on = oc.get(cu, 0.0), sc
        assert abs(oc_on - sc_on) <= max(1.0, max(oc_on, sc_on) * 0.005), (
            f"Con toggle ON los motores deben coincidir restando la SOL: OC={oc_on} vs Pantalla={sc_on} (#9)")
        assert oc_on < 1400, f"Con SOL de 1000g el déficit debe bajar de 1500 a ~500, got {oc_on}"

        # ── Toggle OFF (default): la pantalla NO resta (bruto=1500) · divergencia intencional ──
        _set_toggle(None)
        payload_off = admin_client.get("/api/abastecimiento/consumo-horizontes?horizontes=90").get_json()
        sc_off = _deficit_pantalla(payload_off, cu)
        assert sc_off > sc_on, (
            f"Con toggle OFF la pantalla debe mostrar déficit BRUTO (mayor). "
            f"OFF={sc_off} vs ON={sc_on}. Si esto cambia, revisar el interruptor abast_contar_pendiente.")

        # ── #9 FIX: el 'neto_a_pedir' (lo que usa la sugerencia "Pedir") SIEMPRE es neto,
        #    independiente del toggle → coincide con lo que Generar OC pediría (evita
        #    re-comprar lo en camino desde la pantalla).
        oc_d = oc.get(cu, 0.0)  # OC engine (neto) del bloque toggle-ON de arriba
        neto = _campo_pantalla(payload_off, cu, "neto_a_pedir")
        assert abs(neto - oc_d) <= max(1.0, oc_d * 0.005), (
            f"'neto_a_pedir' de la pantalla ({neto}) debe igualar a Generar OC ({oc_d}) "
            f"aun con toggle OFF (#9 · la sugerencia Pedir no debe re-comprar lo en camino).")
    finally:
        _set_toggle(None)
        _cleanup_sol(sol)
        _cleanup(codigo, producto)
