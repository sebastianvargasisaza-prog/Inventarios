"""EBR · conciliación de material de envase/empaque (MyBatch OF/OA).

Cubre:
  · registrar línea → 201 y utilizada = recibida - devuelta (auto)
  · utilizada explícita se respeta
  · listado devuelve las líneas
  · material_nombre faltante → 400
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


def _crear_ebr(c, lote='ZZ-CONC-001'):
    r1 = c.post('/api/brd/mbr', json={'producto_nombre': 'ZZ CONC PROD',
                                      'lote_size_g': 500.0}, headers=_h())
    mbr_id = r1.get_json()['id']
    c.post(f'/api/brd/mbr/{mbr_id}/pasos',
           json={'descripcion': 'Llenar', 'tipo_paso': 'otro',
                 'fase': 'envasado'}, headers=_h())
    c.post(f'/api/brd/mbr/{mbr_id}/submit', json={}, headers=_h())
    sig = _firmar(c, record_table='mbr_templates', record_id=mbr_id,
                  meaning='aprueba')
    c.post(f'/api/brd/mbr/{mbr_id}/aprobar',
           json={'signature_id': sig}, headers=_h())
    r2 = c.post('/api/brd/ebr', json={'mbr_template_id': mbr_id, 'lote': lote,
                                      'fase': 'envasado'}, headers=_h())
    assert r2.status_code == 201, r2.data
    return r2.get_json()['id']


def test_conciliacion_material(app, db_clean):
    c = _login(app, 'sebastian')
    c.patch('/api/identidad/sebastian', json={'cedula': '77777777'}, headers=_h())
    ebr_id = _crear_ebr(c)

    # utilizada auto = recibida - devuelta
    r = c.post(f'/api/brd/ebr/{ebr_id}/conciliacion-material', json={
        'tipo': 'envase', 'material_nombre': 'Airless 15ml',
        'lote_material': 'L-ENV-1', 'cant_requerida': 900,
        'cant_recibida': 900, 'cant_devuelta': 11,
    }, headers=_h())
    assert r.status_code == 201, r.data
    assert r.get_json()['cant_utilizada'] == 889  # 900 - 11

    # utilizada explícita se respeta
    r2 = c.post(f'/api/brd/ebr/{ebr_id}/conciliacion-material', json={
        'tipo': 'etiqueta', 'material_nombre': 'Etiqueta frontal',
        'cant_recibida': 900, 'cant_devuelta': 5, 'cant_utilizada': 880,
    }, headers=_h())
    assert r2.status_code == 201, r2.data
    assert r2.get_json()['cant_utilizada'] == 880

    # listado
    items = c.get(f'/api/brd/ebr/{ebr_id}/conciliacion-material').get_json()['items']
    assert len(items) == 2
    env = next(m for m in items if m['tipo'] == 'envase')
    assert env['material_nombre'] == 'Airless 15ml'
    assert env['cant_utilizada'] == 889

    # material_nombre faltante → 400
    rbad = c.post(f'/api/brd/ebr/{ebr_id}/conciliacion-material',
                  json={'tipo': 'caja'}, headers=_h())
    assert rbad.status_code == 400, rbad.data
