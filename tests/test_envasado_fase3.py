"""Envasado Fase 3 (26-jun) · descuento de envases al cerrar el legajo.
Modelo: presentaciones de producto_presentaciones (envase/tapa/caja) × unidades → movimientos_mee.
Cubre: envases-plan lee presentaciones · registrar-unidades guarda · cerrar-envasado descuenta UNA vez
(CAS idempotente) · tras cerrar no se edita."""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _h():
    h = {'Content-Type': 'application/json'}
    h.update(csrf_headers())
    return h


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def _q(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _firmar(c, *, record_table, record_id, meaning):
    rc = c.post('/api/sign/challenge', json={'password': TEST_PASSWORD}, headers=csrf_headers())
    token = rc.get_json()['token']
    rs = c.post('/api/sign', json={'record_table': record_table, 'record_id': str(record_id),
                'meaning': meaning, 'challenge_token': token}, headers=csrf_headers())
    return rs.get_json()['signature_id']


def test_fase3_descuento_envases(app, db_clean):
    prod = 'ZZ ENV PROD'
    env, tap, caj = 'ENV-ZZ-30', 'TAP-ZZ', 'CAJ-ZZ'
    c = _login(app)
    c.post('/api/admin/brd-visibilidad', json={'modo': 'todos'}, headers=_h())
    for cod, desc in ((env, 'Frasco 30'), (tap, 'Tapa'), (caj, 'Caja')):
        _exec("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,stock_actual,stock_minimo) "
              "VALUES (?,?,?,0,0)", (cod, desc, 'Envase'))
    _exec("INSERT INTO producto_presentaciones (producto_nombre,presentacion_codigo,etiqueta,volumen_ml,"
          "envase_codigo,tapa_codigo,caja_codigo,es_default,activo) VALUES (?,'ZZ-30','30 ml',30,?,?,?,1,1)",
          (prod, env, tap, caj))
    # MBR aprobado con paso de envasado
    mbr_id = c.post('/api/brd/mbr', json={'producto_nombre': prod, 'lote_size_g': 1000.0},
                    headers=_h()).get_json()['id']
    c.post(f'/api/brd/mbr/{mbr_id}/pasos', json={'descripcion': 'Llenar envases',
           'tipo_paso': 'envasado', 'fase': 'envasado'}, headers=_h())
    c.post(f'/api/brd/mbr/{mbr_id}/submit', json={}, headers=_h())
    sig = _firmar(c, record_table='mbr_templates', record_id=mbr_id, meaning='aprueba')
    c.post(f'/api/brd/mbr/{mbr_id}/aprobar', json={'signature_id': sig}, headers=_h())
    ebr_id = c.post('/api/brd/ebr', json={'mbr_template_id': mbr_id, 'lote': 'ZZ-ENV-001',
                    'fase': 'envasado'}, headers=_h()).get_json()['id']

    # plan: lee la presentación con su envase/tapa/caja
    pl = c.get(f'/api/brd/ebr/{ebr_id}/envases-plan').get_json()
    assert pl['ok'] and len(pl['items']) == 1, pl
    it = pl['items'][0]
    assert it['envase_codigo'] == env and it['tapa_codigo'] == tap and it['caja_codigo'] == caj, it
    assert pl['descontado'] is False

    # registrar 50 unidades
    rr = c.post(f'/api/brd/ebr/{ebr_id}/registrar-unidades',
                json={'presentacion_codigo': 'ZZ-30', 'unidades': 50, 'volumen_ml': 30}, headers=_h())
    assert rr.status_code == 200, rr.data

    # cerrar → descuenta envase+tapa+caja × 50
    rc = c.post(f'/api/brd/ebr/{ebr_id}/cerrar-envasado', json={}, headers=_h())
    assert rc.status_code == 200, rc.data
    assert rc.get_json()['n_descuentos'] == 3, rc.get_json()
    for cod in (env, tap, caj):
        rows = _q("SELECT cantidad FROM movimientos_mee WHERE mee_codigo=? AND tipo='Salida'", (cod,))
        assert rows and abs(float(rows[0][0]) - 50) < 0.01, (cod, rows)

    # idempotente: cerrar de nuevo → 409 (no doble descuento)
    rc2 = c.post(f'/api/brd/ebr/{ebr_id}/cerrar-envasado', json={}, headers=_h())
    assert rc2.status_code == 409, rc2.data
    # sigue habiendo UNA sola Salida por código (no se duplicó)
    assert len(_q("SELECT id FROM movimientos_mee WHERE mee_codigo=? AND tipo='Salida'", (env,))) == 1

    # tras cerrar no se editan unidades
    rr2 = c.post(f'/api/brd/ebr/{ebr_id}/registrar-unidades',
                 json={'presentacion_codigo': 'ZZ-30', 'unidades': 99}, headers=_h())
    assert rr2.status_code == 409, rr2.data
