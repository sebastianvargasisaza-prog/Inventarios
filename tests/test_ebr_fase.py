"""EBR · discriminador de FASE (motor único OP/OF/OA · reemplazo MyBatch).

Cubre:
  · crear EBR con fase explícita (envasado) → se guarda y se lee
  · los pasos arrastran su fase desde mbr_pasos
  · filtro ?fase= en el listado
  · fase inválida → 400
  · sin fase → default 'fabricacion'
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


def _mbr_aprobado(c):
    r1 = c.post('/api/brd/mbr', json={'producto_nombre': 'ZZ FASE PROD',
                                      'lote_size_g': 1000.0}, headers=_h())
    assert r1.status_code == 201, r1.data
    mbr_id = r1.get_json()['id']
    c.post(f'/api/brd/mbr/{mbr_id}/pasos',
           json={'descripcion': 'Mezclar bulk', 'tipo_paso': 'mezclado',
                 'fase': 'fabricacion'}, headers=_h())
    c.post(f'/api/brd/mbr/{mbr_id}/pasos',
           json={'descripcion': 'Llenar envases', 'tipo_paso': 'otro',
                 'fase': 'envasado'}, headers=_h())
    rs = c.post(f'/api/brd/mbr/{mbr_id}/submit', json={}, headers=_h())
    assert rs.status_code == 200, rs.data
    sig = _firmar(c, record_table='mbr_templates', record_id=mbr_id,
                  meaning='aprueba')
    ra = c.post(f'/api/brd/mbr/{mbr_id}/aprobar',
                json={'signature_id': sig}, headers=_h())
    assert ra.status_code == 200, ra.data
    return mbr_id


def test_ebr_fase_envasado(app, db_clean):
    c = _login(app, 'sebastian')
    c.patch('/api/identidad/sebastian', json={'cedula': '77777777'}, headers=_h())
    mbr_id = _mbr_aprobado(c)

    # crear EBR fase=envasado
    r = c.post('/api/brd/ebr', json={'mbr_template_id': mbr_id,
                                     'lote': 'ZZ-FASE-ENV', 'fase': 'envasado'},
               headers=_h())
    assert r.status_code == 201, r.data
    ebr_id = r.get_json()['id']

    # detalle: fase del legajo. Batch B (3-jun): un EBR de envasado clona SOLO
    # los pasos de envasado (ya NO arrastra el paso de fabricación del MBR).
    d = c.get(f'/api/brd/ebr/{ebr_id}').get_json()
    assert d['fase'] == 'envasado', d
    fases_paso = sorted(p['fase'] for p in d['pasos'])
    assert fases_paso == ['envasado'], fases_paso

    # filtro ?fase=
    env = c.get('/api/brd/ebr?fase=envasado').get_json()['items']
    assert any(it['id'] == ebr_id for it in env)
    aco = c.get('/api/brd/ebr?fase=acondicionamiento').get_json()['items']
    assert all(it['id'] != ebr_id for it in aco)


def test_ebr_fase_invalida_y_default(app, db_clean):
    c = _login(app, 'sebastian')
    c.patch('/api/identidad/sebastian', json={'cedula': '77777777'}, headers=_h())
    mbr_id = _mbr_aprobado(c)

    # fase inválida → 400
    rbad = c.post('/api/brd/ebr', json={'mbr_template_id': mbr_id,
                                        'lote': 'ZZ-FASE-BAD', 'fase': 'xxx'},
                  headers=_h())
    assert rbad.status_code == 400, rbad.data

    # sin fase → default 'fabricacion'
    rdef = c.post('/api/brd/ebr', json={'mbr_template_id': mbr_id,
                                        'lote': 'ZZ-FASE-DEF'}, headers=_h())
    assert rdef.status_code == 201, rdef.data
    d = c.get(f"/api/brd/ebr/{rdef.get_json()['id']}").get_json()
    assert d['fase'] == 'fabricacion', d
