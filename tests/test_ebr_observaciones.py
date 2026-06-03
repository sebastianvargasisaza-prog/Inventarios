"""EBR · observaciones generales del proceso (bitácora · MyBatch)."""
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


def _crear_ebr(c):
    r1 = c.post('/api/brd/mbr', json={'producto_nombre': 'ZZ OBS PROD',
                                      'lote_size_g': 500.0}, headers=_h())
    mbr_id = r1.get_json()['id']
    c.post(f'/api/brd/mbr/{mbr_id}/pasos',
           json={'descripcion': 'Mezclar', 'tipo_paso': 'mezclado'}, headers=_h())
    c.post(f'/api/brd/mbr/{mbr_id}/submit', json={}, headers=_h())
    sig = _firmar(c, record_table='mbr_templates', record_id=mbr_id,
                  meaning='aprueba')
    c.post(f'/api/brd/mbr/{mbr_id}/aprobar',
           json={'signature_id': sig}, headers=_h())
    r2 = c.post('/api/brd/ebr', json={'mbr_template_id': mbr_id,
                                      'lote': 'ZZ-OBS-001'}, headers=_h())
    return r2.get_json()['id']


def test_observaciones(app, db_clean):
    c = _login(app, 'sebastian')
    c.patch('/api/identidad/sebastian', json={'cedula': '77777777'}, headers=_h())
    ebr_id = _crear_ebr(c)

    # vacía → 400
    rbad = c.post(f'/api/brd/ebr/{ebr_id}/observaciones', json={'descripcion': ''},
                  headers=_h())
    assert rbad.status_code == 400, rbad.data

    # registrar 2 observaciones
    for txt in ['Se ajustó pH con trietanolamina', 'Granel homogéneo a 3:20pm']:
        r = c.post(f'/api/brd/ebr/{ebr_id}/observaciones',
                   json={'descripcion': txt}, headers=_h())
        assert r.status_code == 201, r.data

    items = c.get(f'/api/brd/ebr/{ebr_id}/observaciones').get_json()['items']
    assert len(items) == 2
    assert items[0]['descripcion'].startswith('Se ajustó pH')
    assert items[0]['registrado_por'] == 'sebastian'
