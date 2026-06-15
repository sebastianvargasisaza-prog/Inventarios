"""14-jun · PQR omnicanal: webhook GHL → clasificación → triaje → enrutado.

- Webhook /api/pqr/inbound exige secreto (token) y no usa sesión.
- Clasifica (reglas como fallback sin API key) y deja en triaje si confianza baja.
- Idempotencia por ghl_message_id.
- Triaje: enrutar a Espagiria (quejas_clientes) o Ánimus (animus_pqr), o descartar.
- Gating: solo Aseguramiento/Calidad/Admin enrutan; el webhook no necesita sesión.
"""
import os
from .conftest import TEST_PASSWORD, csrf_headers

SECRET = 'test-pqr-secret'


def _login(app, u):
    c = app.test_client()
    c.post('/login', data={'username': u, 'password': TEST_PASSWORD}, headers=csrf_headers())
    return c


def _webhook(app, payload, token=SECRET):
    os.environ['PQR_WEBHOOK_SECRET'] = SECRET
    c = app.test_client()
    h = {'X-PQR-Token': token} if token else {}
    return c.post('/api/pqr/inbound', json=payload, headers=h)


def test_webhook_exige_token(app, db_clean):
    r = _webhook(app, {'message': 'hola'}, token='malo')
    assert r.status_code == 401, r.data[:200]


def test_webhook_clasifica_y_deja_en_triaje(app, db_clean):
    r = _webhook(app, {'message': 'mi pedido no ha llegado, la transportadora demora mucho',
                       'full_name': 'Ana', 'channel': 'whatsapp', 'message_id': 'wh-1'})
    assert r.status_code == 201, r.data[:300]
    d = r.get_json()
    assert d['clasificacion']['empresa'] == 'animus'  # reglas: envío → animus
    assert d['auto_enrutado'] is False  # confianza de reglas < umbral → triaje

    # idempotencia
    r2 = _webhook(app, {'message': 'otro', 'message_id': 'wh-1'})
    assert r2.get_json().get('duplicado') is True


def test_triaje_enruta_a_espagiria_y_animus(app, db_clean):
    _webhook(app, {'message': 'se me brotó la cara con ardor tras la crema', 'full_name': 'Luis',
                   'channel': 'instagram', 'message_id': 'wh-esp'})
    _webhook(app, {'message': 'me llegó un producto que no era el que pedí', 'full_name': 'Sara',
                   'channel': 'instagram', 'message_id': 'wh-ani'})
    c = _login(app, 'miguel')
    inb = c.get('/api/aseguramiento/pqr-inbox').get_json()
    assert inb['pendientes'] >= 2
    by_msg = {x['id']: x for x in inb['inbox']}

    # enrutar cada uno · el de Espagiria genera código QC-..., el de Ánimus PQR-A-...
    codigos = {}
    for iid, x in by_msg.items():
        emp = 'espagiria' if 'brot' in x['mensaje'] else 'animus'
        tipo = 'reaccion_adversa' if emp == 'espagiria' else 'producto_equivocado'
        r = c.post('/api/aseguramiento/pqr-inbox/%d/enrutar' % iid,
                   json={'empresa': emp, 'tipo': tipo}, headers=csrf_headers())
        assert r.status_code == 200, r.data[:300]
        codigos[emp] = r.get_json()['codigo']

    assert codigos['espagiria'].startswith('QC'), codigos
    assert codigos['animus'].startswith('PQR-A'), codigos
    # ya no quedan pendientes
    assert c.get('/api/aseguramiento/pqr-inbox').get_json()['pendientes'] == 0
    # re-enrutar el mismo inbox ya procesado → 409
    any_id = next(iter(by_msg))
    r409 = c.post('/api/aseguramiento/pqr-inbox/%d/enrutar' % any_id,
                  json={'empresa': 'animus'}, headers=csrf_headers())
    assert r409.status_code == 409, r409.data[:200]


def test_enrutar_requiere_rol(app, db_clean):
    _webhook(app, {'message': 'consulta', 'message_id': 'wh-x'})
    c = _login(app, 'valentina')  # sin rol calidad/aseguramiento
    inb_id = None
    # valentina sí puede leer el inbox (solo login), pero no enrutar
    r = c.post('/api/aseguramiento/pqr-inbox/1/enrutar',
               json={'empresa': 'animus'}, headers=csrf_headers())
    assert r.status_code in (403, 404), r.data[:200]  # 403 por rol (o 404 si id no existe)


def test_webhook_jala_mensaje_de_ghl_si_viene_vacio(app, db_clean, monkeypatch):
    """GHL no resuelve custom fields en el webhook → si message viene vacío pero
    hay contact_id, EOS lo jala de la API de GHL (pqr_mensaje)."""
    import sys
    A = sys.modules.get('blueprints.aseguramiento') or sys.modules.get('api.blueprints.aseguramiento')
    monkeypatch.setattr(A, '_ghl_fetch_contact', lambda c, cid: {
        'message': 'No me ha llegado mi pedido y ya pasaron 10 dias',
        'channel': 'whatsapp', 'fullName': 'Cliente GHL', 'email': '', 'phone': '3001234567'})
    os.environ['PQR_WEBHOOK_SECRET'] = SECRET
    c = app.test_client()
    r = c.post('/api/pqr/inbound', json={'contact_id': 'AbC123'}, headers={'X-PQR-Token': SECRET})
    assert r.status_code == 201, r.data[:300]
    assert r.get_json()['clasificacion']['empresa'] == 'animus'
    # idempotencia por sha1(mensaje): mismo contacto + mismo texto → duplicado
    r2 = c.post('/api/pqr/inbound', json={'contact_id': 'AbC123'}, headers={'X-PQR-Token': SECRET})
    assert r2.get_json().get('duplicado') is True


def test_webhook_vacio_sin_contact_id_da_400(app, db_clean):
    os.environ['PQR_WEBHOOK_SECRET'] = SECRET
    c = app.test_client()
    r = c.post('/api/pqr/inbound', json={}, headers={'X-PQR-Token': SECRET})
    assert r.status_code == 400


def test_diagnostico_solo_admin(app, db_clean):
    _webhook(app, {'message': 'se me brotó la piel', 'message_id': 'diag-1'})
    # admin ve el diagnóstico con message_id
    a = _login(app, 'sebastian')
    r = a.get('/api/aseguramiento/pqr-inbox/diagnostico')
    assert r.status_code == 200, r.data[:200]
    d = r.get_json()
    assert d['total'] >= 1
    assert any(x['ghl_message_id'] == 'diag-1' for x in d['ultimas'])
    # no-admin → 403
    m = _login(app, 'miguel')
    assert m.get('/api/aseguramiento/pqr-inbox/diagnostico').status_code == 403


def test_animus_pqr_crud(app, db_clean):
    # sebastian tiene ANIMUS_ACCESS (admin)
    c = _login(app, 'sebastian')
    r = c.post('/api/animus/pqr', json={'tipo': 'envio', 'contacto_nombre': 'Cli',
               'descripcion': 'el envío llegó tarde y dañado'}, headers=csrf_headers())
    assert r.status_code == 201, r.data[:300]
    pid = r.get_json()['id']
    g = c.get('/api/animus/pqr').get_json()
    assert g['resumen']['nuevo'] >= 1
    upd = c.patch('/api/animus/pqr/%d' % pid, json={'estado': 'resuelto', 'respuesta': 'reenviado'},
                  headers=csrf_headers())
    assert upd.status_code == 200, upd.data[:300]
