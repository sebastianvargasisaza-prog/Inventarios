"""Sebastián 17-jul: 'Agregar otro cliente' a un lote del Calendario SUMA kg a la producción
(base = Ánimus; el cliente se agrega encima). Crea pedidos_b2b + pedidos_b2b_lote y sube
cantidad_kg atómicamente. No debe tocar un lote ya iniciado/cerrado."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _lote(producto, kg=10, fecha='2026-10-15', inicio=None):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute(
            "INSERT INTO produccion_programada (producto,fecha_programada,estado,origen,cantidad_kg,lotes,inicio_real_at) "
            "VALUES (?,?,?,?,?,1,?)",
            (producto, fecha, 'programado' if inicio else 'pendiente', 'eos_proyeccion', kg, inicio))
        conn.commit()
        return conn.execute("SELECT id FROM produccion_programada WHERE producto=?", (producto,)).fetchone()[0]
    finally:
        conn.close()


def _row(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def test_agregar_cliente_suma_kg(app, db_clean):
    pid = _lote('PROD SUMA CLI', kg=10, fecha='2026-10-16')
    c = _login(app)
    r = c.post('/api/plan/lote/%d/agregar-cliente' % pid,
               json={'cliente': 'Cliente X', 'kg': 5, 'ml': 30}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:400]
    d = r.get_json()
    assert d.get('ok') is True
    assert abs(d.get('kg_total', 0) - 15) < 0.01, d           # 10 + 5
    assert abs(d.get('kg_sumados', 0) - 5) < 0.01
    # cantidad_kg del lote subió y quedó Fijo (eos_plan)
    row = _row("SELECT cantidad_kg, origen FROM produccion_programada WHERE id=?", (pid,))
    assert abs(float(row[0]) - 15) < 0.01
    assert row[1] == 'eos_plan'
    # se creó el pedido + el aporte
    apo = _row("SELECT kg_aporte, cliente_nombre, modo FROM pedidos_b2b_lote WHERE lote_produccion_id=?", (pid,))
    assert apo is not None
    assert abs(float(apo[0]) - 5) < 0.01
    assert apo[1] == 'Cliente X'
    assert apo[2] == 'sumado_a_lote_canonico'


def test_agregar_cliente_lote_en_curso_409(app, db_clean):
    pid = _lote('PROD ENCURSO CLI', kg=20, fecha='2026-06-30', inicio='2026-06-30 08:00:00')
    c = _login(app)
    r = c.post('/api/plan/lote/%d/agregar-cliente' % pid,
               json={'cliente': 'Tarde', 'kg': 5}, headers=csrf_headers())
    assert r.status_code == 409, r.data[:300]
    # el kg NO cambió
    row = _row("SELECT cantidad_kg FROM produccion_programada WHERE id=?", (pid,))
    assert abs(float(row[0]) - 20) < 0.01


def test_agregar_cliente_sin_kg_400(app, db_clean):
    pid = _lote('PROD SIN KG', kg=10, fecha='2026-10-18')
    c = _login(app)
    r = c.post('/api/plan/lote/%d/agregar-cliente' % pid,
               json={'cliente': 'Y', 'kg': 0}, headers=csrf_headers())
    assert r.status_code == 400, r.data[:300]
    r2 = c.post('/api/plan/lote/%d/agregar-cliente' % pid,
                json={'cliente': '', 'kg': 5}, headers=csrf_headers())
    assert r2.status_code == 400, r2.data[:300]
