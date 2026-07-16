"""Persistencia del N° de recipientes al recibir (Laura 16-jul).

Cuando una MP llega en varios recipientes individuales, se guarda cuántos en el lote
(movimientos.n_recipientes) → figura en Cuarentena/Calidad. Migración 355.
"""
import os
import sqlite3

from .conftest import csrf_headers


def test_ingreso_mp_guarda_recipientes(admin_client):
    h = {'Content-Type': 'application/json'}; h.update(csrf_headers())
    r = admin_client.post('/api/recepcion', json={
        'codigo_mp': 'MPRECIP1', 'nombre_comercial': 'Activo Recip', 'nombre_inci': 'RECIPINCI',
        'cantidad': 4000, 'lote': 'LRECIP1', 'estanteria': 'CUARENTENA', 'cuarentena': True,
        'proveedor': 'ProvR', 'recipientes': 4}, headers=h)
    assert r.status_code in (200, 201), r.data
    conn = sqlite3.connect(os.environ['DB_PATH'])
    try:
        n = conn.execute("SELECT n_recipientes FROM movimientos WHERE material_id='MPRECIP1' AND lote='LRECIP1' AND tipo='Entrada'").fetchone()
    finally:
        conn.close()
    assert n and int(n[0]) == 4, 'debe guardar 4 recipientes en el lote'


def test_cuarentena_devuelve_recipientes(admin_client):
    h = {'Content-Type': 'application/json'}; h.update(csrf_headers())
    admin_client.post('/api/recepcion', json={
        'codigo_mp': 'MPRECIP2', 'nombre_comercial': 'Activo Recip2', 'nombre_inci': 'RECIP2',
        'cantidad': 3000, 'lote': 'LRECIP2', 'estanteria': 'CUARENTENA', 'cuarentena': True,
        'proveedor': 'ProvR', 'recipientes': 3}, headers=h)
    data = admin_client.get('/api/lotes/cuarentena').get_json()
    it = next((x for x in data if x.get('codigo_mp') == 'MPRECIP2'), None)
    assert it is not None, 'el lote debe salir en cuarentena'
    assert int(it.get('n_recipientes') or 1) == 3, 'la lista de cuarentena debe traer n_recipientes'


def test_default_un_recipiente(admin_client):
    h = {'Content-Type': 'application/json'}; h.update(csrf_headers())
    admin_client.post('/api/recepcion', json={
        'codigo_mp': 'MPRECIP3', 'nombre_comercial': 'Activo Recip3', 'nombre_inci': 'RECIP3',
        'cantidad': 1000, 'lote': 'LRECIP3', 'estanteria': 'CUARENTENA', 'cuarentena': True,
        'proveedor': 'ProvR'}, headers=h)
    conn = sqlite3.connect(os.environ['DB_PATH'])
    try:
        n = conn.execute("SELECT n_recipientes FROM movimientos WHERE material_id='MPRECIP3' AND lote='LRECIP3'").fetchone()
    finally:
        conn.close()
    assert n and int(n[0]) == 1, 'sin el dato, default 1 recipiente'
