"""Corrección de colisiones de código del Consumo retroactivo (Sebastián 15-jul).

El Excel de MyBatch usó códigos que en EOS son OTRA molécula (MP00300=Ceramide en MyBatch
pero Sodium Cocoyl Glycinate en EOS). La herramienta /api/admin/descuento-retro/corregir
revierte el descuento al material equivocado (Entrada net-zero) y lo re-aplica al correcto
(MP00103) por FEFO. Idempotente + reversible.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        conn.execute(sql, params); conn.commit()
    finally:
        conn.close()


def _q(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _admin(app):
    c = app.test_client()
    r = c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD}, headers=csrf_headers())
    assert r.status_code == 302, r.data
    return c


def _stock(cod):
    rows = _q("SELECT tipo, cantidad FROM movimientos WHERE material_id=?", (cod,))
    s = 0.0
    for t, q in rows:
        s += (q or 0) if str(t).upper().startswith(('ENTRADA', 'AJUSTE')) else -(q or 0)
    return round(s, 2)


def _seed():
    for cod in ('MP00300', 'MP00103'):
        _exec("DELETE FROM movimientos WHERE material_id=?", (cod,))
        _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, activo) VALUES (?,?,1)", (cod, cod))
        _exec("UPDATE maestro_mps SET activo=1 WHERE codigo_mp=?", (cod,))
    # MP00300 (Eversoft en EOS): tenía 3000g · el retro le descontó 1400 por error (con marcador)
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
          "VALUES ('MP00300','Eversoft',3000,'Entrada','2026-01-01','LEV1','VIGENTE')")
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,observaciones) "
          "VALUES ('MP00300','Eversoft',1400,'Salida','2026-07-10','LEV1',?)",
          ('Consumo retroactivo · EMULSION LIMPIADORA · lote real 73526 [retro 261871|MP00300|73526|1400]',))
    # MP00103 (Ceramide NP): tiene 2000g para re-aplicar
    _exec("INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,lote,estado_lote) "
          "VALUES ('MP00103','Ceramide NP',2000,'Entrada','2026-01-01','73526','VIGENTE')")


FILA = {'cod': 'MP00300', 'cant': 1400, 'lote': '73526', 'bulk': '261871',
        'prod': 'EMULSION LIMPIADORA', 'desc': 'Ceramide NP'}


def test_preview_no_muta(app, db_clean):
    _seed()
    c = _admin(app)
    r = c.post('/api/admin/descuento-retro/corregir', json={'filas': [FILA]}, headers=csrf_headers())
    d = r.get_json()
    assert r.status_code == 200 and d['dry_run'] is True, d
    assert d['plan'] and d['plan'][0]['de'] == 'MP00300' and d['plan'][0]['a'] == 'MP00103'
    assert d['plan'][0]['wrong_movs'] == 1
    # nada cambió (sigue el estado original)
    assert _stock('MP00300') == 1600.0   # 3000 - 1400
    assert _stock('MP00103') == 2000.0


def test_corrige_revierte_y_reaplica(app, db_clean):
    _seed()
    c = _admin(app)
    r = c.post('/api/admin/descuento-retro/corregir', json={'filas': [FILA], 'aplicar': True}, headers=csrf_headers())
    d = r.get_json()
    assert r.status_code == 200 and d['dry_run'] is False, d
    assert d['revertidos'] and d['reaplicados'], d
    # MP00300 (equivocado) vuelve a 3000 (net-zero: Salida 1400 + reversión Entrada 1400)
    assert _stock('MP00300') == 3000.0, _stock('MP00300')
    # MP00103 (correcto) baja a 600 (2000 - 1400)
    assert _stock('MP00103') == 600.0, _stock('MP00103')
    # el re-aplicado lleva el marcador de corrección
    corr = _q("SELECT 1 FROM movimientos WHERE material_id='MP00103' AND observaciones LIKE '%[retro-corr %'")
    assert corr, "el descuento correcto debe llevar marcador [retro-corr ...]"


def test_idempotente(app, db_clean):
    _seed()
    c = _admin(app)
    c.post('/api/admin/descuento-retro/corregir', json={'filas': [FILA], 'aplicar': True}, headers=csrf_headers())
    # 2a corrida: no debe volver a corregir
    r2 = c.post('/api/admin/descuento-retro/corregir', json={'filas': [FILA], 'aplicar': True}, headers=csrf_headers())
    d2 = r2.get_json()
    assert d2['plan'][0]['ya_corregido'] is True, d2
    assert not d2['revertidos'] and not d2['reaplicados'], d2
    # stock intacto (no doble corrección)
    assert _stock('MP00300') == 3000.0 and _stock('MP00103') == 600.0
