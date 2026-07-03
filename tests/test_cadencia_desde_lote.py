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
