"""A-2 (Sebastián 12-jun): /api/conteo/materiales devuelve un ARRAY plano. La
página móvil de conteo hacía ITEMS=d.items||[] -> siempre [] -> no listaba MPs.
Este test fija el contrato (array) y que la página carga.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app):
    c = app.test_client()
    c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def test_conteo_materiales_devuelve_array(app, db_clean):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,activo) VALUES ('MP-CM','Test CM',1)")
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estanteria,estado_lote) "
          "VALUES ('MP-CM','Test CM',100,'Entrada',datetime('now'),'L-CM','E-CM','VIGENTE')")
    c = _login(app)
    r = c.get('/api/conteo/materiales?estanteria=E-CM')
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert isinstance(d, list), "el contrato es un ARRAY plano (no {items})"
    assert any(x.get('codigo_mp') == 'MP-CM' for x in d), f"debe listar MP-CM · {d}"


def test_pagina_conteo_movil_maneja_array(app, db_clean):
    c = _login(app)
    r = c.get('/planta/conteo-ciclico')
    assert r.status_code == 200
    body = r.data.decode('utf-8', 'replace')
    # el fix: la pagina soporta array plano
    assert 'Array.isArray(d)' in body, "la pagina debe manejar el array plano de /materiales"
