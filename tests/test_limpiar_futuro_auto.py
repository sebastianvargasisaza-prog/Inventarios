"""Sebastián 3-jul: "limpiar auto futuro" · cancela los AZULES (auto/canónicos) futuros, preserva
Fijo (verde · cadenas) + B2B + ejecutado + todo lo pasado (base hasta hoy)."""
import os
import sqlite3
from datetime import date, timedelta

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    c.post('/login', data={'username': user, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _ins(producto, fecha, origen, estado='programado'):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,origen,cantidad_kg) "
                     "VALUES (?,?,1,?,?,50)", (producto, fecha, estado, origen))
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


def test_limpiar_futuro_auto(app, db_clean):
    fut = (date.today() + timedelta(days=30)).isoformat()
    pas = (date.today() - timedelta(days=5)).isoformat()
    auto_fut = _ins('P AUTO', fut, 'eos_canonico')       # AZUL futuro → cancela
    proy_fut = _ins('P PROY', fut, 'eos_proyeccion')     # AZUL futuro → cancela
    fijo_fut = _ins('P FIJO', fut, 'eos_plan')           # VERDE (cadena) → preserva
    b2b_fut  = _ins('P B2B', fut, 'eos_b2b')             # B2B → preserva
    auto_pas = _ins('P PAS', pas, 'eos_canonico')        # AZUL PASADO (base) → preserva
    c = _login(app)
    r = c.post('/api/plan/limpiar-futuro-auto', json={}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert _estado(auto_fut) == 'cancelado'
    assert _estado(proy_fut) == 'cancelado'
    assert _estado(fijo_fut) != 'cancelado', 'el Fijo (cadena) se preserva'
    assert _estado(b2b_fut) != 'cancelado', 'el B2B se preserva'
    assert _estado(auto_pas) != 'cancelado', 'lo pasado (base) NO se toca'
