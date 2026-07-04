"""Sebastián 2-jul: programar la CADENA desde un lote ancla (julio) cada X meses × 2 años.
Reemplaza las automáticas futuras del producto (proyeccion/sugerido) pero PRESERVA lo Fijo
(eos_plan) y los pedidos B2B. El ancla se produce; la cadena arranca en ancla + X meses."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _ins(producto, fecha, origen, estado='pendiente', kg=100):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,origen,cantidad_kg) "
                     "VALUES (?,?,1,?,?,?)", (producto, fecha, estado, origen, kg))
        conn.commit()
        return conn.execute("SELECT id FROM produccion_programada WHERE producto=? AND fecha_programada=? AND origen=?",
                            (producto, fecha, origen)).fetchone()[0]
    finally:
        conn.close()


def _estado(pid):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        return conn.execute("SELECT estado FROM produccion_programada WHERE id=?", (pid,)).fetchone()[0]
    finally:
        conn.close()


def test_cadena_reemplaza_auto_preserva_fijo(app, db_clean):
    ancla = _ins('PROD CAD', '2026-07-15', 'eos_plan', kg=100)
    auto = _ins('PROD CAD', '2026-09-01', 'eos_proyeccion')      # automática futura → cancela
    fijo = _ins('PROD CAD', '2026-10-01', 'eos_plan')            # Fijo futuro → AHORA también cancela
    b2b  = _ins('PROD CAD', '2026-11-01', 'eos_b2b')             # pedido B2B → SE PRESERVA
    c = _login(app)
    r = c.post('/api/plan/programar-cadencia-desde-lote/%d' % ancla,
               json={'interval_dias': 90, 'first_offset_dias': 70, 'kg_por_lote': 100, 'anios': 2}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert d['creados'] == 8, d           # cada 90d desde +70d en 730d = 8 producciones
    assert d['cancelados'] == 2, d        # la eos_proyeccion Y el eos_plan (Fijo)
    assert _estado(auto) == 'cancelado', 'la automática futura debe cancelarse'
    assert _estado(fijo) == 'cancelado', 'el Fijo posterior AHORA también se cancela (Sebastián 3-jul)'
    assert _estado(b2b) != 'cancelado', 'el pedido B2B de cliente se preserva'
    assert _estado(ancla) != 'cancelado', 'el ancla debe preservarse'
    # las 12 nuevas son eos_plan (Fijo) cada 2 meses desde el ancla
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        nuevas = conn.execute(
            "SELECT COUNT(*) FROM produccion_programada WHERE producto='PROD CAD' AND origen='eos_plan' "
            "AND estado='pendiente' AND fecha_programada > '2026-07-15'").fetchone()[0]
    finally:
        conn.close()
    assert nuevas >= 8, nuevas   # 8 de la cadena + el fijo de octubre


def test_sin_meses_error(app, db_clean):
    ancla = _ins('PROD CAD2', '2026-07-15', 'eos_plan', kg=100)
    c = _login(app)
    r = c.post('/api/plan/programar-cadencia-desde-lote/%d' % ancla, json={}, headers=csrf_headers())
    assert r.status_code == 400


def test_cadena_no_dobla_mismo_dia(app, db_clean):
    """Sebastián 4-jul: la cadena NO crea un lote el MISMO día que un B2B preservado (dedup mismo día).
    Puede caer CERCA (distinta demanda: B2B otro cliente vs Animus), pero NUNCA dos lotes el mismo día."""
    ancla = _ins('PROD DEDUP', '2026-07-15', 'eos_plan', kg=100)
    _ins('PROD DEDUP', '2026-09-23', 'eos_b2b')   # EXACTO donde caería el 1er slot (ancla+70=09-23)
    c = _login(app)
    r = c.post('/api/plan/programar-cadencia-desde-lote/%d' % ancla,
               json={'interval_dias': 90, 'first_offset_dias': 70, 'kg_por_lote': 100, 'anios': 2}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    fechas = [x[0][:10] for x in sqlite3.connect(os.environ['DB_PATH']).execute(
        "SELECT fecha_programada FROM produccion_programada WHERE producto='PROD DEDUP' "
        "AND estado NOT IN ('cancelado','completado') ORDER BY fecha_programada").fetchall()]
    assert len(fechas) == len(set(fechas)), ('no dos lotes el MISMO día', fechas)
    assert r.get_json()['creados'] >= 6, ('la cadena igual se crea completa', r.get_json())


def test_cadena_no_cae_finde(app, db_clean):
    """Sebastián 3-jul: ningún lote de la cadena cae en sábado/domingo."""
    ancla = _ins('PROD FINDE', '2026-07-15', 'eos_plan', kg=100)
    c = _login(app)
    r = c.post('/api/plan/programar-cadencia-desde-lote/%d' % ancla,
               json={'interval_dias': 30, 'first_offset_dias': 20, 'kg_por_lote': 100, 'anios': 2}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    from datetime import date
    for f in r.get_json()['fechas']:
        assert date.fromisoformat(f).weekday() < 5, ('cae en finde', f)


def test_cadena_desde_lote_propaga_kg_otro(app, db_clean):
    """Sebastián 3-jul: el path desde-lote propaga kg_otro_cliente a cada lote (antes se perdía)."""
    ancla = _ins('PROD OTRO CAD', '2026-07-15', 'eos_plan', kg=100)
    c = _login(app)
    r = c.post('/api/plan/programar-cadencia-desde-lote/%d' % ancla,
               json={'interval_dias': 60, 'first_offset_dias': 40, 'kg_por_lote': 20,
                     'kg_otro_cliente': 50, 'anios': 1}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    row = sqlite3.connect(os.environ['DB_PATH']).execute(
        "SELECT cantidad_kg, kg_otro_cliente FROM produccion_programada WHERE producto='PROD OTRO CAD' "
        "AND origen='eos_plan' AND estado='pendiente' AND fecha_programada > '2026-07-15' "
        "ORDER BY fecha_programada LIMIT 1").fetchone()
    assert abs(float(row[0]) - 70) < 0.01, ('total = Animus+otro', row[0])   # 20 + 50
    assert abs(float(row[1]) - 50) < 0.01, ('kg_otro guardado', row[1])


def test_cadena_lock_concurrente_409(app, db_clean):
    """Sebastián 3-jul: con un lock de cadena activo del producto, el 2º request da 409 (anti doble-cadena)."""
    ancla = _ins('PROD LOCK', '2026-07-15', 'eos_plan', kg=100)
    from datetime import datetime
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        try:
            conn.execute("INSERT INTO cron_locks (job_name, locked_at, locked_by) VALUES (?, ?, ?)",
                         ('cadena:PROD LOCK', datetime.utcnow().isoformat(), 'cad:otro'))
            conn.commit()
        except Exception:
            import pytest
            pytest.skip('cron_locks no existe en el schema de test')
    finally:
        conn.close()
    c = _login(app)
    r = c.post('/api/plan/programar-cadencia-desde-lote/%d' % ancla,
               json={'interval_dias': 60, 'first_offset_dias': 40, 'kg_por_lote': 20, 'anios': 1}, headers=csrf_headers())
    assert r.status_code == 409, r.data[:200]


def test_cadena_no_la_mata_proyeccion_densa(app, db_clean):
    """Sebastián 4-jul (workflow ultracode · BUG cadena de 1 lote): eos_proyeccion DENSA no debe matar
    la cadena · el cancel la borra y _preservados (simétrico) no la cuenta. Antes creaba 1."""
    from datetime import date, timedelta
    ancla = _ins('PROD DENSA', '2026-07-15', 'eos_plan', kg=100)
    d = date(2026, 8, 1)
    for _ in range(22):
        _ins('PROD DENSA', d.isoformat(), 'eos_proyeccion')
        d = d + timedelta(days=20)
    c = _login(app)
    r = c.post('/api/plan/programar-cadencia-desde-lote/%d' % ancla,
               json={'interval_dias': 61, 'first_offset_dias': 41, 'kg_por_lote': 100, 'anios': 2}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert r.get_json()['creados'] >= 8, ('la cadena NO debe quedar en 1', r.get_json())


def test_cadena_no_la_mata_b2b_denso(app, db_clean):
    """B2B denso preservado NO mata la cadena (dedup contra preservados = mismo día, no ±14)."""
    from datetime import date, timedelta
    ancla = _ins('PROD B2B DENSO', '2026-07-15', 'eos_plan', kg=100)
    d = date(2026, 8, 10)
    for _ in range(22):
        _ins('PROD B2B DENSO', d.isoformat(), 'eos_b2b')
        d = d + timedelta(days=20)
    c = _login(app)
    r = c.post('/api/plan/programar-cadencia-desde-lote/%d' % ancla,
               json={'interval_dias': 61, 'first_offset_dias': 41, 'kg_por_lote': 100, 'anios': 2}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert r.get_json()['creados'] >= 8, r.get_json()


def test_diag_lotes_producto(app, db_clean):
    from datetime import date, timedelta
    fut = (date.today() + timedelta(days=30)).isoformat()
    _ins('PROD DIAG', fut, 'eos_plan')
    c = _login(app)
    r = c.get('/api/plan/diag-lotes-producto?producto=PROD DIAG', headers=csrf_headers())
    assert r.status_code == 200, r.data[:200]
    d = r.get_json()
    assert d['cadena_futura_eos_plan'] >= 1
    assert 'eos_plan' in d['futuros_activos_por_origen']
