"""Bodega MP · auditoría 12-jun (paso inicial):
M1: duplicados-deteccion usaba 'tipo=Entrada ELSE -cantidad' -> restaba los Ajuste.
Toggle 0-stock: la Bodega muestra solo con-stock por defecto + checkbox para ver en 0.
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


def test_duplicados_stock_cuenta_ajuste_canonico(app, db_clean):
    # 2 MPs con el MISMO nombre -> forman grupo de duplicados
    for cod in ('MP-DUPA', 'MP-DUPB'):
        _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,activo) "
              "VALUES (?,'Purisil Duplicado','PURISIL TEST',1)", (cod,))
    # MP-DUPA: Entrada 1000 + Ajuste +50 -> canonico 1050 (la formula vieja daba 950)
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote) "
          "VALUES ('MP-DUPA','Purisil Duplicado',1000,'Entrada',datetime('now'),'L1')")
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote) "
          "VALUES ('MP-DUPA','Purisil Duplicado',50,'Ajuste',datetime('now'),'L1')")

    c = _login(app)
    r = c.get('/api/maestro-mps/duplicados-deteccion')
    assert r.status_code == 200, r.data
    d = r.get_json()
    grupos = d.get('grupos') or d.get('duplicados') or d.get('items') or []
    va = None
    for g in grupos:
        for v in (g.get('variantes') or g.get('codigos') or []):
            if v.get('codigo_mp') == 'MP-DUPA':
                va = v
    assert va is not None, f"MP-DUPA debe salir en duplicados · {d}"
    assert abs(va['stock_actual_g'] - 1050) < 0.5, \
        f"el Ajuste +50 debe SUMAR (1050), no restar (950) · fue {va['stock_actual_g']}"


def test_api_lotes_excluye_cuarentena_y_no_infla_total(app, db_clean):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,nombre_inci,tipo_material,activo) "
          "VALUES ('MP-A1','Test A1','TEST A1','MP',1)")
    # 500g VIGENTE (usable) + 800g CUARENTENA (retenido por Calidad)
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
          "VALUES ('MP-A1','Test A1',500,'Entrada',datetime('now'),'L-OK','VIGENTE')")
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
          "VALUES ('MP-A1','Test A1',800,'Entrada',datetime('now'),'L-CUAR','CUARENTENA')")

    c = _login(app)
    r = c.get('/api/lotes')
    assert r.status_code == 200, r.data
    lotes = [x for x in r.get_json()['lotes'] if x['material_id'] == 'MP-A1']
    nombres = {x['lote'] for x in lotes}
    assert 'L-OK' in nombres, "el lote VIGENTE debe aparecer"
    assert 'L-CUAR' not in nombres, "el lote en CUARENTENA NO debe aparecer en Bodega usable"
    # El total por MP refleja solo lo usable (500), no infla con la cuarentena (1300)
    assert abs((lotes[0].get('stock_total_mp_g') or 0) - 500) < 0.5, \
        f"el total debe ser 500 (usable), no 1300 · {lotes}"


def test_bodega_pagina_tiene_toggle_0stock(app, db_clean):
    c = _login(app)
    r = c.get('/inventarios')
    assert r.status_code == 200
    # El JS del dashboard va en archivos servidos aparte (cacheables): combinar.
    body = (r.data.decode('utf-8', 'replace')
            + c.get('/planta-core.js').get_data(as_text=True)
            + c.get('/planta-app.js').get_data(as_text=True))
    assert 'stock-ver-sin' in body, "la Bodega debe tener el checkbox 'Ver MPs en 0'"
    assert "fetch('/api/lotes'+(_verSin" in body, "loadStock debe pedir con-stock por defecto"
