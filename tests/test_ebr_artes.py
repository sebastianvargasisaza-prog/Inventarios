"""EBR · Aprobación de Artes / Codificación (gate de etiquetado · MyBatch OA).

Cubre:
  · registrar arte → 201
  · aprobar sin firma → 400
  · aprobar con e-firma (Calidad/Admin) → 200
  · re-aprobar → 409
  · descripcion faltante → 400
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


def _crear_ebr_acond(c, lote='ZZ-ART-001'):
    r1 = c.post('/api/brd/mbr', json={'producto_nombre': 'ZZ ART PROD',
                                      'lote_size_g': 500.0}, headers=_h())
    mbr_id = r1.get_json()['id']
    c.post(f'/api/brd/mbr/{mbr_id}/pasos',
           json={'descripcion': 'Estuchar', 'tipo_paso': 'otro',
                 'fase': 'acondicionamiento'}, headers=_h())
    c.post(f'/api/brd/mbr/{mbr_id}/submit', json={}, headers=_h())
    sig = _firmar(c, record_table='mbr_templates', record_id=mbr_id,
                  meaning='aprueba')
    c.post(f'/api/brd/mbr/{mbr_id}/aprobar',
           json={'signature_id': sig}, headers=_h())
    r2 = c.post('/api/brd/ebr', json={'mbr_template_id': mbr_id, 'lote': lote,
                                      'fase': 'acondicionamiento'}, headers=_h())
    assert r2.status_code == 201, r2.data
    return r2.get_json()['id']


def test_artes_codificacion(app, db_clean):
    c = _login(app, 'sebastian')
    c.patch('/api/identidad/sebastian', json={'cedula': '77777777'}, headers=_h())
    ebr_id = _crear_ebr_acond(c)

    # registrar arte
    r = c.post(f'/api/brd/ebr/{ebr_id}/artes', json={
        'descripcion': 'Etiqueta frontal AZ Hybrid 15ml',
        'codigo_lote': '261481', 'codigo_vencimiento': '2028-06',
    }, headers=_h())
    assert r.status_code == 201, r.data
    arte_id = r.get_json()['id']

    # descripcion faltante → 400
    rbad = c.post(f'/api/brd/ebr/{ebr_id}/artes', json={'codigo_lote': 'X'},
                  headers=_h())
    assert rbad.status_code == 400, rbad.data

    # aprobar sin firma → 400
    r1 = c.post(f'/api/brd/ebr/{ebr_id}/artes/{arte_id}/aprobar', json={},
                headers=_h())
    assert r1.status_code == 400, r1.data

    # aprobar con e-firma → 200
    sig = _firmar(c, record_table='ebr_artes_codificacion', record_id=arte_id,
                  meaning='aprueba')
    r2 = c.post(f'/api/brd/ebr/{ebr_id}/artes/{arte_id}/aprobar',
                json={'signature_id': sig}, headers=_h())
    assert r2.status_code == 200, r2.data
    assert r2.get_json()['aprobado_por'] == 'sebastian'

    # el listado refleja la aprobación
    items = c.get(f'/api/brd/ebr/{ebr_id}/artes').get_json()['items']
    ar = next(a for a in items if a['id'] == arte_id)
    assert ar['aprobado_por'] == 'sebastian'
    assert ar['codigo_lote'] == '261481'

    # re-aprobar → 409
    sig2 = _firmar(c, record_table='ebr_artes_codificacion', record_id=arte_id,
                   meaning='aprueba')
    r3 = c.post(f'/api/brd/ebr/{ebr_id}/artes/{arte_id}/aprobar',
                json={'signature_id': sig2}, headers=_h())
    assert r3.status_code == 409, r3.data
