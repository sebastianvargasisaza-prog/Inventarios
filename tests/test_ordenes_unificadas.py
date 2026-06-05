"""Órdenes de Producción unificadas (estilo MyBatch) · paso 1 · SOLO LECTURA.

Sebastián 4-jun-2026: la vista nueva /planta/ordenes-produccion une los
registros simples (tabla producciones) con los legajos EBR, en el formato de
MyBatch (N° orden · lote · teórica/producida/aprobada · estado). Aditivo.

Cubre:
  · endpoint devuelve ok + estructura esperada
  · un registro simple (producciones) aparece como origen='simple'
  · la página responde HTML 200
  · requiere login
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _conn():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)


def test_ordenes_unificadas_incluye_registro_simple(app, db_clean):
    c = _conn()
    c.execute("INSERT INTO producciones (producto, cantidad, fecha, estado, operador, lote) "
              "VALUES ('PROD ORDEN TEST', 20, '2026-06-04 10:00', 'Completado', 'sebastian', 'PROD-09999')")
    c.commit(); c.close()
    cl = _login(app)
    r = cl.get('/api/brd/ordenes-unificadas?fase=fabricacion')
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d['ok'] and d['fase'] == 'fabricacion'
    fila = next((o for o in d['ordenes'] if o['producto'] == 'PROD ORDEN TEST'), None)
    assert fila, f"el registro simple debe aparecer · {d['resumen']}"
    assert fila['origen'] == 'simple'
    assert fila['numero_op'] == 'PROD-09999'
    assert fila['teorica_g'] == 20000.0   # 20 kg → 20.000 g
    assert fila['producida_g'] == 20000.0
    assert fila['aprobada'] is None       # registro simple no tiene QC
    assert 'simple' in fila['estado'].lower()


def test_ordenes_unificadas_fase_invalida_cae_a_fabricacion(app, db_clean):
    cl = _login(app)
    r = cl.get('/api/brd/ordenes-unificadas?fase=xyz')
    assert r.status_code == 200, r.data
    assert r.get_json()['fase'] == 'fabricacion'


def test_ordenes_produccion_page_html(app, db_clean):
    cl = _login(app)
    r = cl.get('/planta/ordenes-produccion')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Órdenes de Producción' in body
    assert 'ordenes-unificadas' in body  # llama al endpoint


def test_ordenes_unificadas_requiere_login(app, db_clean):
    cl = app.test_client()
    r = cl.get('/api/brd/ordenes-unificadas')
    assert r.status_code == 401
