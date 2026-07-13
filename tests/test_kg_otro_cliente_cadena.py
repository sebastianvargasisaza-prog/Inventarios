"""Aplicar la porción 'para otro cliente' (kg fijo) a TODA la cadena · Sebastián 13-jul.

Al poner 'para otro cliente' en un lote, un botón lo aplica a TODOS los lotes futuros del producto
(kg fijo por lote, clampeado a la cantidad del lote). Solo lotes NO ejecutados y fecha >= hoy.
Reversible (0 lo quita de todos). La cadencia recalcula con la porción Ánimus (lo hace el modal).
"""
import os
import sqlite3
from .conftest import csrf_headers, TEST_PASSWORD


def _login(app, user='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def test_kg_otro_cliente_cadena_aplica_a_futuros(app, db_clean):
    PROD = "PROD OTRO CLIENTE QA"
    _exec("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
    _ins = ("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, "
            "inventario_descontado_at) VALUES (?, %s, ?, ?, 'eos_plan', '')")
    _exec(_ins % "date('now','-5 hours','+10 days')", (PROD, 20, 'pendiente'))   # futuro
    _exec(_ins % "date('now','-5 hours','+40 days')", (PROD, 20, 'pendiente'))   # futuro
    _exec(_ins % "date('now','-5 hours','+70 days')", (PROD, 3, 'pendiente'))    # futuro · chico → clamp a 3
    _exec(_ins % "date('now','-5 hours','-10 days')", (PROD, 20, 'pendiente'))   # PASADO · no se toca
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, "
          "fin_real_at, inventario_descontado_at) VALUES (?, date('now','-5 hours','+15 days'), 20, "
          "'completado', 'eos_plan', '2026-01-01', '')", (PROD,))               # EJECUTADO · no se toca

    c = _login(app)
    r = c.post('/api/plan/kg-otro-cliente-cadena', json={'producto': PROD, 'kg_otro_cliente': 5}, headers=csrf_headers())
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d['ok'] and d['aplicados'] == 3, d   # SOLO los 3 futuros pendientes

    conn = sqlite3.connect(os.environ['DB_PATH'])
    try:
        rows = conn.execute("SELECT cantidad_kg, COALESCE(kg_otro_cliente,0), estado FROM produccion_programada "
                            "WHERE producto=? ORDER BY fecha_programada", (PROD,)).fetchall()
    finally:
        conn.close()
    con_reserva = [x for x in rows if x[1] > 0]
    assert len(con_reserva) == 3, ("solo 3 lotes futuros tocados", rows)
    # el completado y el pasado quedan en 0
    for cant, kotro, estado in rows:
        if estado == 'completado':
            assert kotro == 0, ("el completado no se toca", rows)
    # clamp: el lote de 3kg no puede reservar 5 al otro cliente
    chico = [x for x in rows if abs(x[0] - 3) < 0.01]
    assert chico and abs(chico[0][1] - 3) < 0.01, ("clamp a la cantidad del lote", chico)

    # reversible: 0 lo quita de todos los futuros
    r2 = c.post('/api/plan/kg-otro-cliente-cadena', json={'producto': PROD, 'kg_otro_cliente': 0}, headers=csrf_headers())
    assert r2.status_code == 200 and r2.get_json()['aplicados'] == 3, r2.data
    conn = sqlite3.connect(os.environ['DB_PATH'])
    try:
        vals = [x[0] for x in conn.execute(
            "SELECT COALESCE(kg_otro_cliente,0) FROM produccion_programada WHERE producto=? AND estado='pendiente' "
            "AND fecha_programada >= date('now','-5 hours')", (PROD,)).fetchall()]
    finally:
        conn.close()
    assert all(abs(v) < 0.01 for v in vals), ("reversible a 0", vals)


def test_kg_otro_cliente_cadena_requiere_login(app, db_clean):
    r = app.test_client().post('/api/plan/kg-otro-cliente-cadena',
                               json={'producto': 'X', 'kg_otro_cliente': 5}, headers=csrf_headers())
    assert r.status_code in (401, 403, 302), r.data
