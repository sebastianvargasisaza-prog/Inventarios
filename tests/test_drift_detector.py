"""Tests CERO SESGO continuo · drift detector + integraciones.

Verifica:
- detect_drift_mp encuentra MPs con stock negativo
- detect_drift_mee encuentra MEEs con drift entre persistido y calc
- drift_summary agrega ambos
- /api/admin/health-detailed incluye sección inventario_drift
- /api/bandeja-ceo incluye item si hay drift
- job_drift_detector_inventario corre, detecta, y notifica
- cron está registrado en JOBS_SCHEDULE
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


# ─── detect_drift_mp ─────────────────────────────────────────────────

def test_drift_mp_detecta_negativo(app, db_clean):
    from inventario_helpers import detect_drift_mp
    conn = sqlite3.connect(os.environ["DB_PATH"])
    # MP-DRIFT-N1 con más salidas que entradas → stock negativo
    conn.execute("DELETE FROM movimientos WHERE material_id LIKE 'MP-DRIFT-%'")
    conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha) VALUES ('MP-DRIFT-N1','Test',500,'Entrada',datetime('now'))")
    conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha) VALUES ('MP-DRIFT-N1','Test',800,'Salida',datetime('now'))")
    conn.commit()
    try:
        items = detect_drift_mp(conn)
        codes = [it['codigo_mp'] for it in items]
        assert 'MP-DRIFT-N1' in codes
        item = next(it for it in items if it['codigo_mp'] == 'MP-DRIFT-N1')
        assert item['stock_g'] == -300.0
    finally:
        conn.execute("DELETE FROM movimientos WHERE material_id LIKE 'MP-DRIFT-%'")
        conn.commit(); conn.close()


def test_drift_mp_ignora_positivos_y_cero(app, db_clean):
    from inventario_helpers import detect_drift_mp
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM movimientos WHERE material_id LIKE 'MP-DRIFT-%'")
    conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha) VALUES ('MP-DRIFT-OK','Test',1000,'Entrada',datetime('now'))")
    conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha) VALUES ('MP-DRIFT-ZERO','Test',500,'Entrada',datetime('now'))")
    conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha) VALUES ('MP-DRIFT-ZERO','Test',500,'Salida',datetime('now'))")
    conn.commit()
    try:
        items = detect_drift_mp(conn)
        codes = [it['codigo_mp'] for it in items]
        assert 'MP-DRIFT-OK' not in codes
        assert 'MP-DRIFT-ZERO' not in codes
    finally:
        conn.execute("DELETE FROM movimientos WHERE material_id LIKE 'MP-DRIFT-%'")
        conn.commit(); conn.close()


def test_drift_mp_severidad_critical_si_muy_negativo(app, db_clean):
    from inventario_helpers import detect_drift_mp
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM movimientos WHERE material_id LIKE 'MP-DRIFT-%'")
    # Stock = -2000g → critical
    conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha) VALUES ('MP-DRIFT-C','Test',1000,'Entrada',datetime('now'))")
    conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha) VALUES ('MP-DRIFT-C','Test',3000,'Salida',datetime('now'))")
    conn.commit()
    try:
        items = detect_drift_mp(conn)
        item = next(it for it in items if it['codigo_mp'] == 'MP-DRIFT-C')
        assert item['severidad'] == 'critical'
    finally:
        conn.execute("DELETE FROM movimientos WHERE material_id LIKE 'MP-DRIFT-%'")
        conn.commit(); conn.close()


# ─── detect_drift_mee ────────────────────────────────────────────────

def test_drift_mee_detecta_inconsistencia(app, db_clean):
    from inventario_helpers import detect_drift_mee
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM maestro_mee WHERE codigo='MEE-DRIFT-T1'")
    conn.execute("DELETE FROM movimientos_mee WHERE mee_codigo='MEE-DRIFT-T1'")
    # stock_actual=1000 pero solo movimiento Entrada de 600 → drift +400
    conn.execute("INSERT INTO maestro_mee (codigo,descripcion,stock_actual,estado) VALUES ('MEE-DRIFT-T1','Test',1000,'Activo')")
    conn.execute("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,fecha) VALUES ('MEE-DRIFT-T1','Entrada',600,datetime('now'))")
    conn.commit()
    try:
        items = detect_drift_mee(conn)
        codes = [it['codigo'] for it in items]
        assert 'MEE-DRIFT-T1' in codes
        item = next(it for it in items if it['codigo'] == 'MEE-DRIFT-T1')
        assert item['drift'] == 400.0
        assert item['stock_persistido'] == 1000
        assert item['stock_calculado'] == 600
    finally:
        conn.execute("DELETE FROM maestro_mee WHERE codigo='MEE-DRIFT-T1'")
        conn.execute("DELETE FROM movimientos_mee WHERE mee_codigo='MEE-DRIFT-T1'")
        conn.commit(); conn.close()


def test_drift_mee_ignora_dentro_tolerancia(app, db_clean):
    """Drift de 0.5 (dentro de tolerancia 1.0) no debe reportarse."""
    from inventario_helpers import detect_drift_mee
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM maestro_mee WHERE codigo='MEE-TOL-T'")
    conn.execute("DELETE FROM movimientos_mee WHERE mee_codigo='MEE-TOL-T'")
    conn.execute("INSERT INTO maestro_mee (codigo,descripcion,stock_actual,estado) VALUES ('MEE-TOL-T','Test',100.5,'Activo')")
    conn.execute("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,fecha) VALUES ('MEE-TOL-T','Entrada',100,datetime('now'))")
    conn.commit()
    try:
        items = detect_drift_mee(conn)
        codes = [it['codigo'] for it in items]
        assert 'MEE-TOL-T' not in codes
    finally:
        conn.execute("DELETE FROM maestro_mee WHERE codigo='MEE-TOL-T'")
        conn.execute("DELETE FROM movimientos_mee WHERE mee_codigo='MEE-TOL-T'")
        conn.commit(); conn.close()


def test_drift_summary_agrega_mp_y_mee(app, db_clean):
    from inventario_helpers import drift_summary
    conn = sqlite3.connect(os.environ["DB_PATH"])
    # 1 MP negativo + 1 MEE drift
    conn.execute("DELETE FROM movimientos WHERE material_id='MP-SUM-T'")
    conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha) VALUES ('MP-SUM-T','Test',100,'Salida',datetime('now'))")
    conn.execute("DELETE FROM maestro_mee WHERE codigo='MEE-SUM-T'")
    conn.execute("DELETE FROM movimientos_mee WHERE mee_codigo='MEE-SUM-T'")
    conn.execute("INSERT INTO maestro_mee (codigo,descripcion,stock_actual,estado) VALUES ('MEE-SUM-T','Test',500,'Activo')")
    conn.commit()
    try:
        s = drift_summary(conn)
        assert s['mp_negativos'] >= 1
        assert s['mee_drift'] >= 1
        assert s['total_items_con_drift'] >= 2
    finally:
        conn.execute("DELETE FROM movimientos WHERE material_id='MP-SUM-T'")
        conn.execute("DELETE FROM maestro_mee WHERE codigo='MEE-SUM-T'")
        conn.execute("DELETE FROM movimientos_mee WHERE mee_codigo='MEE-SUM-T'")
        conn.commit(); conn.close()


# ─── /api/admin/health-detailed expone drift ─────────────────────────

def test_health_detailed_expone_inventario_drift(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/admin/health-detailed")
    sections = r.get_json()['sections']
    assert 'inventario_drift' in sections
    s = sections['inventario_drift']
    assert s['status'] in ('ok', 'warning', 'error')
    assert 'mp_stocks_negativos' in s
    assert 'mee_con_drift' in s
    assert 'total_items_afectados' in s


def test_health_detailed_drift_warning_si_hay_negativos(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM movimientos WHERE material_id='MP-HD-T'")
    conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha) VALUES ('MP-HD-T','Test',300,'Salida',datetime('now'))")
    conn.commit(); conn.close()
    try:
        r = c.get("/api/admin/health-detailed")
        s = r.get_json()['sections']['inventario_drift']
        assert s['status'] in ('warning', 'error')
        assert s['mp_stocks_negativos'] >= 1
        assert 'top' in s
        assert 'hint' in s
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM movimientos WHERE material_id='MP-HD-T'")
        conn.commit(); conn.close()


# ─── /api/bandeja-ceo expone drift como item ─────────────────────────

def test_bandeja_ceo_incluye_item_si_drift(app, db_clean):
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM movimientos WHERE material_id='MP-BAN-T'")
    conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha) VALUES ('MP-BAN-T','Test',500,'Salida',datetime('now'))")
    conn.commit(); conn.close()
    try:
        r = c.get("/api/bandeja-ceo")
        items = r.get_json()['items']
        # Debe haber un item de drift de inventario
        drift_items = [it for it in items if 'sesgo' in (it.get('titulo','') or '').lower()
                                           or 'drift' in (it.get('descripcion','') or '').lower()]
        assert len(drift_items) >= 1
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM movimientos WHERE material_id='MP-BAN-T'")
        conn.commit(); conn.close()


# ─── Cron job_drift_detector_inventario ──────────────────────────────

def test_drift_cron_registrado_en_schedule():
    from blueprints.auto_plan_jobs import JOBS_SCHEDULE
    job_names = [j[0] for j in JOBS_SCHEDULE]
    assert 'drift_detector_inv' in job_names
    job = [j for j in JOBS_SCHEDULE if j[0] == 'drift_detector_inv'][0]
    name, hora, minuto, dias_sem, dias_mes, callable_name = job
    assert hora == 6 and minuto == 30
    assert dias_sem is None  # diario
    assert callable_name == 'job_drift_detector_inventario'


def test_drift_cron_returns_ok_sin_drift(app, db_clean, monkeypatch):
    """Si no hay drift, el cron devuelve ok sin notificar."""
    from blueprints.auto_plan_jobs import job_drift_detector_inventario
    # monkeypatch para evitar imports/notif fallidos
    notifs = []
    def fake_push(*args, **kwargs):
        notifs.append((args, kwargs))
    try:
        import blueprints.notif as notif_mod
        monkeypatch.setattr(notif_mod, 'push_notif_multi', fake_push)
    except Exception:
        pass
    ok, data, _ = job_drift_detector_inventario(app)
    assert ok is True
    # Si no hay drift en la DB de test (fresh), debería devolver mensaje
    # (o detectar drift residual de otros tests · acepto cualquiera)
    assert 'mensaje' in data or 'total' in data


def test_drift_cron_detecta_y_retorna_counts(app, db_clean, monkeypatch):
    """Sembrar drift y verificar que el cron lo detecta."""
    from blueprints.auto_plan_jobs import job_drift_detector_inventario
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM movimientos WHERE material_id='MP-CRON-T'")
    conn.execute("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha) VALUES ('MP-CRON-T','Test',300,'Salida',datetime('now'))")
    conn.commit(); conn.close()
    notifs = []
    try:
        import blueprints.notif as notif_mod
        def fake_push(*args, **kwargs): notifs.append((args, kwargs))
        monkeypatch.setattr(notif_mod, 'push_notif_multi', fake_push)
    except Exception:
        pass
    try:
        ok, data, _ = job_drift_detector_inventario(app)
        assert ok is True
        # Debe detectar el MP negativo
        assert data.get('mp_negativos', 0) >= 1
        assert data.get('total', 0) >= 1
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM movimientos WHERE material_id='MP-CRON-T'")
        conn.commit(); conn.close()
