"""Sebastián 3-jul: programar la cadena de un producto DESDE NECESIDADES (sin lote ancla).
1ª auto (hoy + dias_hasta_primera) + cadena cada interval_dias · reemplaza futuras (salvo B2B/ejecutado)."""
import os
import sqlite3
import datetime as _dt

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _ins(producto, fecha, origen, estado='pendiente'):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,origen,cantidad_kg) "
                     "VALUES (?,?,1,?,?,20)", (producto, fecha, estado, origen))
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


def test_cadena_producto_crea_y_reemplaza(app, db_clean):
    hoy = (_dt.datetime.utcnow() - _dt.timedelta(hours=5)).date()
    futuro = (hoy + _dt.timedelta(days=200)).isoformat()
    fijo = _ins('PROD CADP', futuro, 'eos_plan')                # futuro Fijo → se cancela
    b2b = _ins('PROD CADP', (hoy + _dt.timedelta(days=210)).isoformat(), 'eos_b2b')  # B2B → se preserva
    c = _login(app)
    r = c.post('/api/plan/programar-cadencia-producto',
               json={'producto': 'PROD CADP', 'kg_por_lote': 20, 'interval_dias': 90,
                     'dias_hasta_primera': 10, 'kg_otro_cliente': 5, 'anios': 2},
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert d['creados'] == 9, d           # 10,100,...,730 = 9 lotes
    assert d['cancelados'] == 1, d        # solo el Fijo (el B2B se preserva)
    assert _estado(fijo) == 'cancelado'
    assert _estado(b2b) != 'cancelado'
    # la 1ª cae hoy+10 con la reserva de otro cliente (kg=25, kg_otro=5)
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        f1 = (hoy + _dt.timedelta(days=10)).isoformat()
        row = conn.execute("SELECT cantidad_kg, kg_otro_cliente FROM produccion_programada "
                           "WHERE producto='PROD CADP' AND fecha_programada=? AND origen='eos_plan'", (f1,)).fetchone()
    finally:
        conn.close()
    assert row is not None, 'la 1ª debe existir en hoy+10'
    assert abs(row[0] - 25.0) < 0.01, row   # 20 Animus + 5 otro cliente
    assert abs(row[1] - 5.0) < 0.01, row


def test_cadena_producto_sin_kg_error(app, db_clean):
    c = _login(app)
    r = c.post('/api/plan/programar-cadencia-producto', json={'producto': 'X', 'kg_por_lote': 0},
               headers=csrf_headers())
    assert r.status_code == 400


def test_cadena_producto_ancla_fecha(app, db_clean):
    """Con ancla_fecha (base = producción EJECUTADA sin id): la cadena se cuenta desde esa fecha,
    no desde hoy · y cancela lo posterior a la base."""
    import datetime as _dt2
    hoy = (_dt2.datetime.utcnow() - _dt2.timedelta(hours=5)).date()
    base = (hoy - _dt2.timedelta(days=3)).isoformat()   # producción base 3 días atrás
    # un lote futuro (posterior a la base) que debe cancelarse
    fut = _ins('PROD ANCLA', (hoy + _dt2.timedelta(days=100)).isoformat(), 'eos_plan')
    c = _login(app)
    r = c.post('/api/plan/programar-cadencia-producto',
               json={'producto': 'PROD ANCLA', 'kg_por_lote': 20, 'interval_dias': 90,
                     'dias_hasta_primera': 70, 'ancla_fecha': base, 'anios': 2},
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    # 1ª cae base + 70 días
    esperada = (_dt2.date.fromisoformat(base) + _dt2.timedelta(days=70)).isoformat()
    assert d['fechas'][0] == esperada, (d['fechas'][0], esperada)
    assert _estado(fut) == 'cancelado'
