"""15-jun · Sellar plan: limpieza global del horizonte futuro protegiendo lo
pasado, la semana en curso, lo iniciado y los B2B.

Regla (Sebastián): cancela solo los lotes FUTUROS pendientes (> domingo de la
semana en curso), no toca pasado / esta semana / iniciados / completados / B2B.
"""
import os
import sqlite3
import datetime as _dt
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, u='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': u, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _hoy_co():
    return (_dt.datetime.utcnow() - _dt.timedelta(hours=5)).date()


def _seed(prod, fecha, origen='eos_plan', estado='pendiente', inicio=None):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute(
            "INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,inicio_real_at) "
            "VALUES (?,?,?,?,?,1,?)", (prod, fecha, estado, origen, 30, inicio))
        conn.commit()
        return conn.execute("SELECT id FROM produccion_programada WHERE producto=? AND fecha_programada=? ORDER BY id DESC LIMIT 1",
                            (prod, fecha)).fetchone()[0]
    finally:
        conn.close()


def _estado(lote_id):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        r = conn.execute("SELECT estado FROM produccion_programada WHERE id=?", (lote_id,)).fetchone()
        return r[0] if r else None
    finally:
        conn.close()


def test_sellar_protege_pasado_semana_y_b2b(app, db_clean):
    hoy = _hoy_co()
    fin_sem = hoy + _dt.timedelta(days=(6 - hoy.weekday()))
    prod = 'PROD SELLAR TEST'
    id_pasado = _seed(prod, (hoy - _dt.timedelta(days=10)).isoformat())
    id_semana = _seed(prod, hoy.isoformat())                       # esta semana (Alejandro)
    id_futuro = _seed(prod, (fin_sem + _dt.timedelta(days=20)).isoformat())
    id_inic = _seed(prod, (fin_sem + _dt.timedelta(days=25)).isoformat(), inicio=(hoy.isoformat()))  # ya iniciado
    id_b2b = _seed(prod, (fin_sem + _dt.timedelta(days=30)).isoformat(), origen='eos_b2b')

    c = _login(app)
    # preview (dry_run) no cambia nada
    pv = c.post('/api/plan/sellar-horizonte', json={'dry_run': True}, headers=csrf_headers())
    assert pv.status_code == 200, pv.data[:300]
    assert pv.get_json()['n_a_cancelar'] >= 1
    assert _estado(id_futuro) == 'pendiente'  # dry_run no toca

    # ejecutar
    r = c.post('/api/plan/sellar-horizonte', json={'dry_run': False}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    # solo el futuro normal se cancela
    assert _estado(id_futuro) == 'cancelado'
    # protegidos
    assert _estado(id_pasado) == 'pendiente'
    assert _estado(id_semana) == 'pendiente'
    assert _estado(id_inic) == 'pendiente'
    assert _estado(id_b2b) == 'pendiente'


def test_reemplazar_no_hace_vanish(app, db_clean):
    """BUG 15-jun: 'Aplicar y recalcular' (reemplazar) cancelaba el lote y, si el
    planner no recreaba (sin velocidad/sin ancla), el producto desaparecía del
    calendario. Ahora si no se recrea nada, RESTAURA lo cancelado (anti-vanish)."""
    hoy = _hoy_co()
    prod = 'PROD VANISH TEST'
    fut = (hoy + _dt.timedelta(days=40)).isoformat()
    lote_id = _seed(prod, fut)  # único lote futuro, producto sin velocidad en test
    c = _login(app)
    r = c.post('/api/plan/auto-programar-sugeridas',
               json={'producto': prod, 'reemplazar': True, 'dias_horizonte': 365},
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    # sin velocidad → no recrea → restaura → el lote NO desaparece
    assert j.get('n_creados', 0) == 0
    assert j.get('restaurados', 0) >= 1
    assert _estado(lote_id) == 'pendiente'  # restaurado, no cancelado


def test_sellar_requiere_rol(app, db_clean):
    c = _login(app, 'valentina')  # sin admin/compras
    r = c.post('/api/plan/sellar-horizonte', json={'dry_run': True}, headers=csrf_headers())
    assert r.status_code == 403, r.data[:200]
