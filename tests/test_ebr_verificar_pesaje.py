"""EBR · 2ª firma de verificación de pesaje (verified_weight estilo MyBatch).

Reemplazo MyBatch · Batch 1. Cubre:
  · verificar sin e-firma → 400
  · verificar con e-firma (verificador ≠ pesador) → 200 + listado refleja verificado_por
  · re-verificar un pesaje ya verificado → 409
  · segregación de funciones: el verificador no puede ser quien pesó → 409
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


def _h():
    h = {'Content-Type': 'application/json'}
    h.update(csrf_headers())
    return h


def _firmar(c, *, record_table, record_id, meaning):
    rc = c.post('/api/sign/challenge', json={'password': TEST_PASSWORD},
                headers=csrf_headers())
    assert rc.status_code == 200, rc.data
    token = rc.get_json()['token']
    rs = c.post('/api/sign', json={
        'record_table': record_table, 'record_id': str(record_id),
        'meaning': meaning, 'challenge_token': token,
    }, headers=csrf_headers())
    assert rs.status_code == 201, rs.data
    return rs.get_json()['signature_id']


def _crear_ebr(c, lote='ZZ-VERIF-001'):
    """MBR aprobado (con 1 paso) → EBR iniciado. Devuelve ebr_id."""
    r1 = c.post('/api/brd/mbr', json={'producto_nombre': 'ZZ VERIF PESAJE',
                                      'lote_size_g': 500.0}, headers=_h())
    assert r1.status_code == 201, r1.data
    mbr_id = r1.get_json()['id']
    c.post(f'/api/brd/mbr/{mbr_id}/pasos',
           json={'descripcion': 'Pesar MPs', 'tipo_paso': 'pesaje'}, headers=_h())
    rs = c.post(f'/api/brd/mbr/{mbr_id}/submit', json={}, headers=_h())
    assert rs.status_code == 200, rs.data
    sig = _firmar(c, record_table='mbr_templates', record_id=mbr_id,
                  meaning='aprueba')
    ra = c.post(f'/api/brd/mbr/{mbr_id}/aprobar',
                json={'signature_id': sig}, headers=_h())
    assert ra.status_code == 200, ra.data
    r2 = c.post('/api/brd/ebr', json={'mbr_template_id': mbr_id, 'lote': lote},
                headers=_h())
    assert r2.status_code == 201, r2.data
    return r2.get_json()['id']


def _insert_pesaje(ebr_id, pesado_por):
    """Inserta un pesaje directo (evita depender de formula_items en el test)."""
    db = sqlite3.connect(os.environ['DB_PATH'])
    try:
        db.execute(
            """INSERT INTO ebr_pesajes
                 (ebr_id, material_id, material_nombre, cantidad_teorica_g,
                  cantidad_real_g, delta_g, delta_pct, lote_mp, pesado_por,
                  pesado_at_utc)
               VALUES (?, 'MP001', 'Agua', 100, 100, 0, 0, 'L1', ?,
                       datetime('now','utc'))""",
            (ebr_id, pesado_por),
        )
        pid = db.execute(
            "SELECT id FROM ebr_pesajes WHERE ebr_id=? ORDER BY id DESC LIMIT 1",
            (ebr_id,),
        ).fetchone()[0]
        db.commit()
    finally:
        db.close()
    return pid


def test_verificar_pesaje_flujo(app, db_clean):
    c = _login(app, 'sebastian')
    c.patch('/api/identidad/sebastian',
            json={'cedula': '77777777', 'nombre_completo': 'Test Verif'},
            headers=_h())
    ebr_id = _crear_ebr(c)
    pid = _insert_pesaje(ebr_id, 'mayerlin')  # pesado por OTRA persona

    # 1) verificar SIN firma → 400
    r = c.post(f'/api/brd/ebr/{ebr_id}/pesajes/{pid}/verificar',
               json={}, headers=_h())
    assert r.status_code == 400, r.data

    # 2) verificar CON firma (sebastian admin ≠ mayerlin) → 200
    sig = _firmar(c, record_table='ebr_pesajes', record_id=pid,
                  meaning='supervisa')
    r2 = c.post(f'/api/brd/ebr/{ebr_id}/pesajes/{pid}/verificar',
                json={'signature_id': sig}, headers=_h())
    assert r2.status_code == 200, r2.data
    assert r2.get_json()['verificado_por'] == 'sebastian'

    # 3) el listado refleja la verificación
    rl = c.get(f'/api/brd/ebr/{ebr_id}/pesajes')
    pes = next(p for p in rl.get_json()['items'] if p['id'] == pid)
    assert pes['verificado_por'] == 'sebastian'
    assert pes['verificado_at_utc']

    # 4) re-verificar un pesaje ya verificado → 409
    sig2 = _firmar(c, record_table='ebr_pesajes', record_id=pid,
                   meaning='supervisa')
    r4 = c.post(f'/api/brd/ebr/{ebr_id}/pesajes/{pid}/verificar',
                json={'signature_id': sig2}, headers=_h())
    assert r4.status_code == 409, r4.data


def test_verificar_pesaje_segregacion(app, db_clean):
    """El verificador NO puede ser quien pesó (segregación de funciones GMP)."""
    c = _login(app, 'sebastian')
    c.patch('/api/identidad/sebastian',
            json={'cedula': '77777777'}, headers=_h())
    ebr_id = _crear_ebr(c, lote='ZZ-VERIF-SEG')
    pid = _insert_pesaje(ebr_id, 'sebastian')  # pesado por sebastian mismo

    # sebastian intenta verificar su propio pesaje → 409 (segregación, antes de firma)
    r = c.post(f'/api/brd/ebr/{ebr_id}/pesajes/{pid}/verificar',
               json={}, headers=_h())
    assert r.status_code == 409, r.data
    assert 'segregaci' in r.get_json()['error'].lower()
