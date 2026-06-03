"""EBR · puente OP→OF · densidad + mL envasable al cerrar el lote.

cantidad_real_g / densidad = mL envasables (lot_amount_filling de MyBatch).
"""
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


def test_ml_envasable_al_completar(app, db_clean):
    c = _login(app, 'sebastian')
    c.patch('/api/identidad/sebastian', json={'cedula': '77777777'}, headers=_h())

    # MBR con 1 paso simple (sin e-sign / sin QC / sin IPC obligatorio)
    r1 = c.post('/api/brd/mbr', json={'producto_nombre': 'ZZ MLENV PROD',
                                      'lote_size_g': 1000.0}, headers=_h())
    mbr_id = r1.get_json()['id']
    c.post(f'/api/brd/mbr/{mbr_id}/pasos',
           json={'descripcion': 'Mezclar', 'tipo_paso': 'mezclado'}, headers=_h())
    c.post(f'/api/brd/mbr/{mbr_id}/submit', json={}, headers=_h())
    sig = _firmar(c, record_table='mbr_templates', record_id=mbr_id,
                  meaning='aprueba')
    c.post(f'/api/brd/mbr/{mbr_id}/aprobar',
           json={'signature_id': sig}, headers=_h())

    # EBR fabricación
    r2 = c.post('/api/brd/ebr', json={'mbr_template_id': mbr_id,
                                      'lote': 'ZZ-MLENV-001'}, headers=_h())
    ebr_id = r2.get_json()['id']

    # ejecutar el único paso
    c.post(f'/api/brd/ebr/{ebr_id}/pasos/1/iniciar', json={}, headers=_h())
    rc = c.post(f'/api/brd/ebr/{ebr_id}/pasos/1/completar',
                json={'observaciones': 'ok'}, headers=_h())
    assert rc.status_code == 200, rc.data

    # completar con densidad 1.05 → 1050 mL para 1102.5 g
    r3 = c.post(f'/api/brd/ebr/{ebr_id}/completar',
                json={'cantidad_real_g': 1102.5, 'densidad_g_ml': 1.05},
                headers=_h())
    assert r3.status_code == 200, r3.data
    d = r3.get_json()
    assert d['ml_envasable'] == 1050.0, d   # 1102.5 / 1.05
    assert d['densidad_g_ml'] == 1.05

    # el detalle lo expone
    det = c.get(f'/api/brd/ebr/{ebr_id}').get_json()
    assert det['ml_envasable'] == 1050.0
    assert det['densidad_g_ml'] == 1.05
