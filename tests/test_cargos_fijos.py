"""Cargos fijos · Gerencia (Sebastián 14-jul).

Gastos recurrentes: Catalina los monta/vigila; SOLO admin (Sebastián) paga.
Cubre: crear plantilla → auto-instancia del mes → completar monto (variable) →
pagar (solo admin · CAS anti-doble + espejo a flujo_egresos).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='catalina'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _cleanup(concepto):
    conn = sqlite3.connect(os.environ['DB_PATH'])
    ids = [r[0] for r in conn.execute("SELECT id FROM cargos_fijos WHERE concepto=?", (concepto,)).fetchall()]
    for cid in ids:
        conn.execute("DELETE FROM cargos_fijos_pagos WHERE cargo_fijo_id=?", (cid,))
    conn.execute("DELETE FROM cargos_fijos WHERE concepto=?", (concepto,))
    conn.commit(); conn.close()


def test_cargo_fijo_fijo_autoinstancia_por_pagar(app, db_clean):
    cs = _login(app, 'catalina')
    try:
        r = cs.post('/api/compras/cargos-fijos',
                    json={'concepto': 'TEST-ARRIENDO', 'beneficiario': 'Inmobiliaria X',
                          'categoria': 'Arriendo', 'monto': 3000000, 'dia_corte': 5,
                          'medio_pago': 'cuenta', 'dato_pago': '123-456'},
                    headers=csrf_headers())
        assert r.status_code == 200, r.data
        r2 = cs.get('/api/compras/cargos-fijos')
        assert r2.status_code == 200, r2.data
        d = r2.get_json()
        p = next((x for x in d['pagos'] if x['concepto'] == 'TEST-ARRIENDO'), None)
        assert p is not None, 'no auto-creó la instancia del mes'
        # monto fijo → por_pagar directo con el monto de la plantilla
        assert p['estado'] == 'por_pagar', p['estado']
        assert abs(float(p['monto']) - 3000000) < 1
        assert d['alertas']['por_pagar'] >= 1
    finally:
        _cleanup('TEST-ARRIENDO')


def test_cargo_fijo_variable_pendiente_monto_luego_por_pagar(app, db_clean):
    cs = _login(app, 'catalina')
    try:
        cs.post('/api/compras/cargos-fijos',
                json={'concepto': 'TEST-LUZ', 'categoria': 'Servicios públicos',
                      'es_variable': True, 'dia_corte': 10, 'medio_pago': 'referencia',
                      'dato_pago': 'REF-999'},
                headers=csrf_headers())
        d = cs.get('/api/compras/cargos-fijos').get_json()
        p = next(x for x in d['pagos'] if x['concepto'] == 'TEST-LUZ')
        assert p['estado'] == 'pendiente_monto'
        # Catalina carga el monto del mes → por_pagar
        r = cs.post('/api/compras/cargos-fijos/pago/%d/monto' % p['id'],
                    json={'monto': 185000, 'medio_pago': 'referencia', 'dato_pago': 'REF-999'},
                    headers=csrf_headers())
        assert r.status_code == 200, r.data
        d2 = cs.get('/api/compras/cargos-fijos').get_json()
        p2 = next(x for x in d2['pagos'] if x['concepto'] == 'TEST-LUZ')
        assert p2['estado'] == 'por_pagar'
        assert abs(float(p2['monto']) - 185000) < 1
    finally:
        _cleanup('TEST-LUZ')


def test_cargo_fijo_solo_admin_paga(app, db_clean):
    cs = _login(app, 'catalina')
    admin = _login(app, 'sebastian')
    try:
        cs.post('/api/compras/cargos-fijos',
                json={'concepto': 'TEST-INTERNET', 'monto': 120000, 'dia_corte': 8},
                headers=csrf_headers())
        d = cs.get('/api/compras/cargos-fijos').get_json()
        pid = next(x['id'] for x in d['pagos'] if x['concepto'] == 'TEST-INTERNET')
        # Catalina NO puede pagar
        r_no = cs.post('/api/compras/cargos-fijos/pago/%d/pagar' % pid,
                       json={}, headers=csrf_headers())
        assert r_no.status_code == 403, r_no.data
        # Admin SÍ paga
        r_ok = admin.post('/api/compras/cargos-fijos/pago/%d/pagar' % pid,
                          json={'referencia_pago': 'CE-001'}, headers=csrf_headers())
        assert r_ok.status_code == 200, r_ok.data
        # Doble pago → 409 (CAS)
        r_dup = admin.post('/api/compras/cargos-fijos/pago/%d/pagar' % pid,
                           json={}, headers=csrf_headers())
        assert r_dup.status_code == 409, r_dup.data
        # Espejo en flujo_egresos
        conn = sqlite3.connect(os.environ['DB_PATH'])
        row = conn.execute(
            "SELECT monto FROM flujo_egresos WHERE referencia=? ", ('CF-%d' % pid,)).fetchone()
        conn.close()
        assert row is not None, 'no espejó a flujo_egresos'
        assert abs(float(row[0]) - 120000) < 1
    finally:
        _cleanup('TEST-INTERNET')
