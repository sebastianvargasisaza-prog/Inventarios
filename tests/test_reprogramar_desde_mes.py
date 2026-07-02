"""Sebastián 2-jul · Botón "Fijar mes + recalcular 2 años" (/api/plan/reprogramar-desde-mes).

Fija todo lo ANTERIOR al ancla (1er día del próximo mes) y recalcula de ahí en adelante:
cancela el plan viejo >= ancla PERO preserva los pedidos B2B de clientes (eos_b2b), lo
histórico (eos_retroactivo) y lo ya ejecutado. Coloca proyección nueva solo >= ancla.
"""
import os
import sqlite3
import datetime as _dt

from .conftest import TEST_PASSWORD, csrf_headers
from .test_proyeccion_2anios import _seed_producto


def _login(app, user='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _ins(producto, fecha, origen, estado='pendiente', inicio=None):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute(
            "INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,origen,"
            "cantidad_kg,inicio_real_at) VALUES (?,?,1,?,?,30,?)",
            (producto, fecha, estado, origen, inicio))
        conn.commit()
    finally:
        conn.close()


def _rows(producto):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        return conn.execute(
            "SELECT substr(fecha_programada,1,10),origen,estado,inicio_real_at "
            "FROM produccion_programada WHERE producto=?", (producto,)).fetchall()
    finally:
        conn.close()


def test_reprogramar_fija_mes_preserva_b2b_y_ejecutado(app, db_clean):
    _seed_producto(producto='PROD REPROG', sku='SKU-REPROG', vel=10, stock=0, lote_kg=30)
    hoy = (_dt.datetime.utcnow() - _dt.timedelta(hours=5)).date()
    ancla = _dt.date(hoy.year + 1, 1, 1) if hoy.month == 12 else _dt.date(hoy.year, hoy.month + 1, 1)
    f_mes = hoy.isoformat()                                    # este mes (< ancla) → sobrevive
    f_ago_plan = (ancla + _dt.timedelta(days=14)).isoformat()  # >= ancla · eos_plan → cancela
    f_ago_b2b = (ancla + _dt.timedelta(days=15)).isoformat()   # >= ancla · eos_b2b → preserva
    f_ago_ejec = (ancla + _dt.timedelta(days=16)).isoformat()  # >= ancla · ejecutado → preserva
    _ins('PROD REPROG', f_mes, 'eos_plan')
    _ins('PROD REPROG', f_ago_plan, 'eos_plan')
    _ins('PROD REPROG', f_ago_b2b, 'eos_b2b')
    _ins('PROD REPROG', f_ago_ejec, 'eos_plan', inicio=f_ago_ejec)

    c = _login(app)
    r = c.post('/api/plan/reprogramar-desde-mes', json={'dry_run': False}, headers=csrf_headers())
    assert r.status_code == 200, f"{r.status_code} {r.data[:300]}"
    rows = _rows('PROD REPROG')

    assert any(x[0] == f_mes and x[2] != 'cancelado' for x in rows), "el mes actual debe sobrevivir"
    assert any(x[0] == f_ago_plan and x[1] == 'eos_plan' and x[2] == 'cancelado' for x in rows), \
        "el eos_plan de ago+ debe cancelarse"
    assert any(x[0] == f_ago_b2b and x[1] == 'eos_b2b' and x[2] != 'cancelado' for x in rows), \
        "el pedido B2B debe preservarse"
    assert any(x[3] and x[2] != 'cancelado' for x in rows), "lo ejecutado debe preservarse"
    proj = [x for x in rows if x[1] == 'eos_proyeccion' and x[2] != 'cancelado']
    assert all(x[0] >= ancla.isoformat() for x in proj), "no colocar proyección antes del ancla"
