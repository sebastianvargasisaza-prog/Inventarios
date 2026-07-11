"""SIMULACIÓN EJECUTABLE END-TO-END · cero-error (Sebastián 10-jul).
Prueba el modelo REAL con datos sembrados, corriendo el código real:
  1) DESCUENTO + FEFO: producir un lote descuenta cada MP = %/100 · kg · 1000, por FEFO
     (lote de vencimiento más próximo primero), y baja el stock exacto.
  2) CADENCIA/CALENDARIO: la cadena cae en días hábiles (sin festivos), espaciada, por N años.
  3) ABASTECIMIENTO: la necesidad de cada MP = %/100 · kg_lote · n_lotes (lote COMPLETO).
Es la verificación más precisa: no lee el código, lo EJECUTA y asevera los números.
"""
import pytest
from datetime import date, timedelta

PROD = "ZZ SIM E2E"
MPA, MPB, MPC = "SIMMPA01", "SIMMPB01", "SIMMPC01"
PCT = {MPA: 2.0, MPB: 0.5, MPC: 1.0}   # %
LOTE_KG = 100.0


def _seed(app):
    from database import get_db
    conn = get_db()
    c = conn.cursor()
    # limpiar
    c.execute("DELETE FROM formula_items WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))", (PROD,))
    c.execute("DELETE FROM formula_headers WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))", (PROD,))
    c.execute("DELETE FROM produccion_programada WHERE UPPER(TRIM(producto))=UPPER(TRIM(?))", (PROD,))
    for cod in (MPA, MPB, MPC):
        c.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (cod,))
        c.execute("DELETE FROM movimientos WHERE material_id=?", (cod,))
    # maestro
    for cod in (MPA, MPB, MPC):
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, tipo_material, activo, controla_stock) "
                  "VALUES (?,?,?,'MP',1,1)", (cod, cod, cod))
    # fórmula
    c.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,?,1)", (PROD, LOTE_KG))
    for cod, pct in PCT.items():
        c.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) VALUES (?,?,?,?)",
                  (PROD, cod, cod, pct))
    # stock: MPA en 2 lotes (FEFO) · L1 vence antes (2026-09-01) 600g, L2 vence después (2027-09-01) 800g
    hoy = date.today()
    v1 = (hoy + timedelta(days=60)).isoformat()
    v2 = (hoy + timedelta(days=400)).isoformat()

    def _ent(cod, lote, g, venc):
        c.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, fecha_vencimiento, estado_lote) "
                  "VALUES (?,?,?,'Entrada',?,?,?,'VIGENTE')", (cod, cod, g, hoy.isoformat(), lote, venc))
    _ent(MPA, "SIM-L1", 600.0, v1)   # vence antes → FEFO primero
    _ent(MPA, "SIM-L2", 800.0, v2)
    _ent(MPB, "SIM-LB", 500.0, v2)
    _ent(MPC, "SIM-LC", 700.0, v2)
    try:
        conn.commit()
    except Exception:
        pass


def test_e2e_descuento_fefo_exacto(app, admin_client):
    """Producir 50 kg → descuenta MPA 1000g (600 de L1 + 400 de L2 por FEFO), MPB 250g, MPC 500g."""
    with app.app_context():
        _seed(app)
    kg = 50.0
    r = admin_client.post("/api/produccion", json={"producto": PROD, "cantidad_kg": kg, "operador": "sim"})
    assert r.status_code in (200, 201), r.get_data(as_text=True)[:400]
    with app.app_context():
        from database import get_db
        c = get_db().cursor()
        # gramos descontados por MP = %/100 · kg · 1000
        for cod, pct in PCT.items():
            esperado = pct / 100.0 * kg * 1000.0
            sal = c.execute("SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE material_id=? AND tipo='Salida'", (cod,)).fetchone()[0]
            assert abs(float(sal) - esperado) < 0.5, "%s: descontó %s, esperado %s" % (cod, sal, esperado)
        # FEFO: MPA saca 600 de SIM-L1 (vence antes) y 400 de SIM-L2
        l1 = c.execute("SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE material_id=? AND tipo='Salida' AND lote='SIM-L1'", (MPA,)).fetchone()[0]
        l2 = c.execute("SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE material_id=? AND tipo='Salida' AND lote='SIM-L2'", (MPA,)).fetchone()[0]
        assert abs(float(l1) - 600.0) < 0.5 and abs(float(l2) - 400.0) < 0.5, "FEFO mal: L1=%s L2=%s (esperado 600/400)" % (l1, l2)
        # stock final MPA = 1400 - 1000 = 400
        neto = c.execute("SELECT COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad WHEN tipo='Salida' THEN -cantidad ELSE 0 END),0) "
                         "FROM movimientos WHERE material_id=?", (MPA,)).fetchone()[0]
        assert abs(float(neto) - 400.0) < 0.5, "stock MPA final %s, esperado 400" % neto


def test_e2e_cadencia_calendario(app, admin_client):
    """Cadena cada ~2 meses por 2 años: días hábiles, sin festivos, espaciada, sin duplicados."""
    with app.app_context():
        _seed(app)
    r = admin_client.post("/api/plan/programar-cadencia-producto",
                          json={"producto": PROD, "kg_por_lote": LOTE_KG, "interval_dias": 61,
                                "dias_hasta_primera": 61, "anios": 2})
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    fechas = sorted((r.get_json().get("fechas") or []))
    assert len(fechas) >= 8, "esperaba una cadena de ~11 lotes en 2 años, dio %d" % len(fechas)
    with app.app_context():
        from blueprints.plan import es_festivo_colombia
        prev = None
        for f in fechas:
            d = date.fromisoformat(f[:10])
            assert d.weekday() < 5, "lote en fin de semana: %s" % f
            assert not es_festivo_colombia(d), "lote en festivo: %s" % f
            if prev:
                gap = (d - prev).days
                assert gap >= 2, "dos lotes demasiado juntos: %s" % f   # dedup
            prev = d
        # span ~2 años
        span = (date.fromisoformat(fechas[-1][:10]) - date.fromisoformat(fechas[0][:10])).days
        assert span >= 600, "la cadena no llega a ~2 años (span %d)" % span


def test_e2e_abastecimiento_mp(app):
    """Abastecimiento: necesidad de cada MP = %/100 · kg_lote · n_lotes (lote COMPLETO)."""
    from datetime import date as _d
    with app.app_context():
        from database import get_db
        from blueprints.programacion import _compute_mp_deficit_aggregated
        conn = get_db(); c = conn.cursor()
        _seed(app)
        # sembrar 3 lotes de la cadena dentro de los próximos 80 días (horizonte 90)
        hoy = _d.today()
        for k in (1, 2, 3):
            f = (hoy + timedelta(days=20 * k)).isoformat()
            c.execute("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, origen, cantidad_kg) "
                      "VALUES (?,?,1,'pendiente','eos_plan',?)", (PROD, f, LOTE_KG))
        try:
            conn.commit()
        except Exception:
            pass
        agg = _compute_mp_deficit_aggregated(conn, days_ahead=90)
        # dict {material_id: {total_g, stock_g, deficit_g, ...}} · solo MPs con deficit>0
        assert isinstance(agg, dict), "esperaba dict, dio %s" % type(agg)
        need = {str(k).upper(): (v.get('total_g') if isinstance(v, dict) else v) for k, v in agg.items()}
        n_lotes = 3
        for cod, pct in PCT.items():
            esperado = pct / 100.0 * LOTE_KG * 1000.0 * n_lotes   # necesidad total = %/100 · kg · 1000 · n_lotes (lote COMPLETO)
            got = need.get(cod.upper())
            assert got is not None, "abastecimiento no reporta %s · claves=%s" % (cod, list(need.keys())[:10])
            assert abs(float(got) - esperado) < 1.0, "%s: abastecimiento pide %s g, esperado %s (%%×kg×1000×n)" % (cod, got, esperado)
        # el déficit = necesidad − stock (una sola vez): MPA 6000−1400=4600
        assert abs(float(agg[MPA]['deficit_g']) - (6000.0 - 1400.0)) < 1.0, "déficit MPA %s, esperado 4600" % agg[MPA]['deficit_g']
