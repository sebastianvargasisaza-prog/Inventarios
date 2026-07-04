"""Sebastián 4-jul: verificar-cadenas revisa todas las cadenas de una y marca estado por producto."""
import os
import sqlite3
from datetime import date, timedelta

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app):
    c = app.test_client()
    c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _ins(producto, fecha, origen):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute("INSERT INTO produccion_programada (producto,fecha_programada,lotes,estado,origen,cantidad_kg) "
                     "VALUES (?,?,1,'programado',?,50)", (producto, fecha, origen))
        conn.commit()
    finally:
        conn.close()


def test_verificar_cadenas(app, db_clean):
    hoy = date.today()
    # producto CON cadena completa (6 lotes cada 60d)
    for k in range(12):
        _ins('P COMPLETA', (hoy + timedelta(days=40 + k * 60)).isoformat(), 'eos_plan')
    # producto con 1 lote (incompleta)
    _ins('P INCOMPLETA', (hoy + timedelta(days=40)).isoformat(), 'eos_plan')
    # producto con cadena completa PERO azules encima
    for k in range(12):
        _ins('P AZULES', (hoy + timedelta(days=40 + k * 60)).isoformat(), 'eos_plan')
    _ins('P AZULES', (hoy + timedelta(days=90)).isoformat(), 'eos_proyeccion')
    c = _login(app)
    r = c.get('/api/plan/verificar-cadenas', headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    est = {p['producto']: p['estado'] for p in d['productos']}
    assert est.get('P COMPLETA') == 'ok', est
    assert est.get('P INCOMPLETA') == 'incompleta', est
    assert est.get('P AZULES') == 'azules_encima', est
