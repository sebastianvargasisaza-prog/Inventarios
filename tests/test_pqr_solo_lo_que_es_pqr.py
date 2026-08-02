"""Al buzón de PQR sólo entra lo que ES un PQR (2-ago).

Sebastián, mirando la bandeja apenas quedó funcionando el webhook: *"si serán reales... debería
ser eso solo lo que realmente es PQR"*. De los 5 primeros que entraron, **ninguno era una queja**:
"Perfecto", "Buena tarde", "En un momento pago", "Te aviso cualquier cosa".

La causa es el disparador de GHL ("Customer Replied · sin filtros"): entra con CADA respuesta del
cliente. Y el clasificador contestaba "¿de qué empresa?" y "¿qué tipo?" pero nunca "¿esto es un
PQR?".

Un registro REGULADO lleno de saludos no queda incompleto: queda FALSO. Entierra las quejas de
verdad y le infla los indicadores a Calidad.

Lo que estos tests fijan:
  · un saludo o un acuse de recibo NO entra al buzón
  · una queja real SÍ entra, aunque empiece con "gracias" o "buenas tardes"
  · lo descartado NO se pierde: queda con su motivo y se puede RECUPERAR
  · el filtro corre sin IA (determinista), así que no depende de que haya API key
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

URL = '/api/pqr/inbound'


def _db():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=15)


def _limpiar():
    """M103: limpiar ANTES · la BD de tests es compartida."""
    db = _db()
    try:
        db.execute("DELETE FROM pqr_inbox WHERE ghl_message_id LIKE 'QAPQR-%'")
        db.execute("DELETE FROM pqr_descartados WHERE ghl_message_id LIKE 'QAPQR-%'")
        db.commit()
    finally:
        db.close()


def _enviar(app, texto, mid):
    return app.test_client().post(URL, json={
        'message': texto, 'message_id': mid, 'contact_id': 'QAC-' + mid,
        'full_name': 'QA Cliente', 'phone': '+573000000000', 'channel': 'whatsapp'})


def _en_buzon(mid):
    db = _db()
    try:
        return db.execute("SELECT COUNT(*) FROM pqr_inbox WHERE ghl_message_id=?", (mid,)).fetchone()[0]
    finally:
        db.close()


def _descartado(mid):
    db = _db()
    try:
        r = db.execute("SELECT id, motivo FROM pqr_descartados WHERE ghl_message_id=?",
                       (mid,)).fetchone()
        return (r[0], r[1]) if r else None
    finally:
        db.close()


def test_un_saludo_NO_entra_al_buzon(app):
    _limpiar()
    for i, txt in enumerate(('Buena tarde', 'Perfecto', 'ok', 'Muchas gracias', 'Listo')):
        mid = 'QAPQR-s%d' % i
        r = _enviar(app, txt, mid)
        js = r.get_json()
        assert r.status_code == 200 and js['registrado'] is False, (txt, js)
        assert _en_buzon(mid) == 0, '"%s" no puede entrar a un registro regulado' % txt
        assert _descartado(mid), '"%s" tiene que quedar guardado con su motivo' % txt


def test_una_queja_REAL_si_entra(app):
    """Y el filtro mira el mensaje ENTERO: si mirara si CONTIENE "gracias", botaría esta."""
    _limpiar()
    casos = [
        ('QAPQR-q1', 'El producto me llegó abierto y derramado, quiero que me lo repongan'),
        ('QAPQR-q2', 'Gracias, pero me salió un brote en la cara con la crema'),
        ('QAPQR-q3', 'Buenas tardes, el pedido no ha llegado y ya van 15 días'),
    ]
    for mid, txt in casos:
        r = _enviar(app, txt, mid)
        js = r.get_json()
        assert r.status_code in (200, 201), (txt, js)
        assert js.get('registrado') is not False, ('una queja real NO se descarta', txt, js)
        assert _en_buzon(mid) == 1, txt


def test_lo_descartado_se_puede_RECUPERAR(app):
    """Un filtro que descarta en silencio es un filtro en el que no se puede confiar."""
    _limpiar()
    mid = 'QAPQR-rec1'
    _enviar(app, 'Perfecto', mid)
    d = _descartado(mid)
    assert d, 'tiene que estar en descartados'

    c = app.test_client()
    c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    h = dict(csrf_headers())
    h["X-CSRF-Token"] = c.get("/api/csrf-token").get_json()["csrf_token"]

    lista = c.get('/api/aseguramiento/pqr-descartados').get_json()
    assert any(x['id'] == d[0] for x in lista['items'])

    r = c.post('/api/aseguramiento/pqr-descartados/%d/recuperar' % d[0], headers=h)
    js = r.get_json()
    assert r.status_code == 200 and js['ok'] is True, js
    assert _en_buzon(mid) == 1, 'tras recuperarlo tiene que estar en el buzón'

    r2 = c.post('/api/aseguramiento/pqr-descartados/%d/recuperar' % d[0], headers=h)
    assert r2.status_code == 409, 'no se puede recuperar dos veces'


def test_el_filtro_es_DETERMINISTA_sin_IA(app):
    """Corre antes de llamar al clasificador: si la IA no está disponible, sigue funcionando."""
    try:
        from api.blueprints.aseguramiento import _no_es_pqr_por_reglas as f
    except Exception:
        from blueprints.aseguramiento import _no_es_pqr_por_reglas as f
    assert f('Buenas tardes')
    assert f('  PERFECTO!  ')
    assert f('ok')
    assert f('')
    assert not f('El producto me llegó vencido')
    assert not f('Gracias, pero me salió un brote')
    assert not f('buenas tardes, el frasco vino roto de fábrica')


def test_motivo_explica_por_que(app):
    """Un descarte sin motivo no se puede auditar ni corregir."""
    _limpiar()
    _enviar(app, 'Buena tarde', 'QAPQR-m1')
    d = _descartado('QAPQR-m1')
    assert d and d[1], 'sin motivo no sirve'
    assert 'saludo' in d[1].lower() or 'acuse' in d[1].lower(), d[1]
