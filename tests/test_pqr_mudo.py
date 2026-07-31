"""El buzón de PQR que se queda MUDO tiene que avisar solo (30-jul).

Los PQR entran por un workflow de GoHighLevel que dispara un webhook a EOS. El 30-jul se
descubrió que el último PQR había entrado el **15 de junio**: seis semanas sin una sola queja de
cliente. Con el volumen de Ánimus eso no es que los clientes dejaran de escribir — es que el
envío se cortó. Nadie se enteró porque **una bandeja vacía se ve igual que una bandeja al día**.

Una integración que enmudece es peor que una que nunca funcionó: la que nunca funcionó se nota el
primer día. Esta acumuló seis semanas de quejas fuera del sistema de calidad, y para INVIMA la
queja es un registro regulado cuyo plazo de respuesta corre igual.

El aviso sólo tiene sentido si ANTES entraban PQR: en un buzón que nunca recibió nada, el
silencio no prueba que algo se rompió.
"""
import os
import sqlite3
from datetime import date, timedelta


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        filas = conn.execute(sql, params).fetchall()
        conn.commit()
        return filas
    finally:
        conn.close()


def _tok_headers():
    """Si otro archivo de tests dejó `PQR_WEBHOOK_SECRET` en el entorno, el webhook exige el
    header. Sin esto el test pasa solo y falla acompañado, que es la peor forma de fallar."""
    tok = os.environ.get('PQR_WEBHOOK_SECRET', '')
    return {'X-PQR-Token': tok} if tok else {}


def _limpiar():
    _sql("DELETE FROM pqr_inbox WHERE COALESCE(mensaje,'') LIKE 'ZZTEST%'")


def _sembrar(dias_atras):
    # El vigía mira MAX(recibido_en) de TODA la tabla: si otro archivo dejó una fila reciente,
    # este test mediría la fila ajena (M102 · un test controla el universo que su código observa).
    _sql("DELETE FROM pqr_inbox")
    f = (date.today() - timedelta(days=dias_atras)).isoformat()
    _sql("INSERT INTO pqr_inbox (ghl_message_id, canal, mensaje, recibido_en, estado) "
         "VALUES (?,?,?,?,'pendiente')",
         ('ZZTEST-%d' % dias_atras, 'whatsapp', 'ZZTEST queja de prueba', f))


def _correr(app):
    from blueprints.auto_plan_jobs import job_pqr_mudo
    return job_pqr_mudo(app)


def test_avisa_cuando_lleva_semanas_sin_recibir(app, db_clean):
    """El caso real: último PQR hace 45 días."""
    _sembrar(45)
    ok, info, _ = _correr(app)
    assert ok, info
    assert info.get('dias_sin_recibir', 0) >= 45, info
    assert info.get('ultimo_recibido'), info


def test_no_molesta_si_los_PQR_estan_entrando(app, db_clean):
    """Dientes del otro lado: una alerta que salta con todo en orden se ignora, y el día que
    importa también se ignora."""
    _sembrar(1)
    ok, info, _ = _correr(app)
    assert ok, info
    assert 'dias_sin_recibir' not in info, info
    assert info.get('mensaje') == 'PQR al día', info


def test_un_buzon_que_NUNCA_recibio_nada_no_dispara(app, db_clean):
    """El silencio de un buzón vacío no prueba que algo se rompió: puede que nunca se conectó.
    Avisar ahí sería ruido diario desde el primer día."""
    _limpiar()
    _sql("DELETE FROM pqr_inbox")
    ok, info, _ = _correr(app)
    assert ok, info
    assert 'nunca' in str(info.get('mensaje', '')).lower(), info


def test_el_umbral_se_cambia_sin_deploy(app, db_clean):
    """Si 7 días resulta mucho o poco, se ajusta desde app_settings y no esperando un release."""
    _sembrar(4)
    ok, info, _ = _correr(app)
    assert 'dias_sin_recibir' not in info, 'con 4 días y umbral 7 no debía avisar'
    _sql("INSERT INTO app_settings (clave, valor) VALUES ('pqr_dias_mudo','3') "
         "ON CONFLICT (clave) DO UPDATE SET valor='3'")
    try:
        ok, info, _ = _correr(app)
        assert info.get('dias_sin_recibir') == 4, info
        assert info.get('umbral') == 3, info
    finally:
        _sql("DELETE FROM app_settings WHERE clave='pqr_dias_mudo'")


# ══ el id que identifica a la PERSONA, no al mensaje (30-jul) ═══════════════════

def test_dos_quejas_del_mismo_cliente_NO_se_pisan(app, db_clean):
    """El workflow de GHL manda `message_id = {{contact.id}}` — o sea el id del CONTACTO, no del
    mensaje. Con eso, la segunda queja de la misma persona entraba con el mismo id que la primera
    y EOS la descartaba como duplicada: una queja perdida en silencio, que es lo peor que le puede
    pasar a un registro regulado.

    No se puede confiar en que la configuración externa esté bien; el sistema detecta el caso y
    calcula su propio id (contacto + hash del texto), que es lo que distingue un reintento de un
    reclamo nuevo.
    """
    import os as _os
    _os.environ.setdefault('PYTEST_CURRENT_TEST', 'pqr')
    _sql("DELETE FROM pqr_inbox WHERE COALESCE(ghl_contact_id,'')='ZZTEST-CONTACT'")
    cli = app.test_client()
    _hd = _tok_headers()
    base = {'contact_id': 'ZZTEST-CONTACT', 'message_id': 'ZZTEST-CONTACT',
            'full_name': 'ZZ Cliente', 'channel': 'whatsapp'}
    r1 = cli.post('/api/pqr/inbound', json=dict(base, message='ZZTEST primera queja: llegó roto'), headers=_hd)
    assert r1.status_code in (200, 201), r1.data[:300]
    assert not (r1.get_json() or {}).get('duplicado'), r1.get_json()
    r2 = cli.post('/api/pqr/inbound', json=dict(base, message='ZZTEST segunda queja: otra cosa'), headers=_hd)
    assert r2.status_code in (200, 201), r2.data[:300]
    assert not (r2.get_json() or {}).get('duplicado'), (
        'la segunda queja del mismo cliente se descartó como duplicada: %r' % r2.get_json())
    n = _sql("SELECT COUNT(*) FROM pqr_inbox WHERE COALESCE(ghl_contact_id,'')='ZZTEST-CONTACT'")
    assert int(n[0][0]) == 2, 'quedó una sola queja de dos distintas'


def test_el_MISMO_mensaje_repetido_sigue_siendo_duplicado(app, db_clean):
    """Dientes del otro lado: los webhooks reintentan, y un reintento NO puede abrir dos PQR."""
    _sql("DELETE FROM pqr_inbox WHERE COALESCE(ghl_contact_id,'')='ZZTEST-CONTACT2'")
    cli = app.test_client()
    payload = {'contact_id': 'ZZTEST-CONTACT2', 'message_id': 'ZZTEST-CONTACT2',
               'message': 'ZZTEST queja idéntica', 'channel': 'whatsapp'}
    _hd = _tok_headers()
    cli.post('/api/pqr/inbound', json=payload, headers=_hd)
    r2 = cli.post('/api/pqr/inbound', json=payload, headers=_hd)
    assert (r2.get_json() or {}).get('duplicado') is True, (
        'un reintento del MISMO mensaje abrió un segundo PQR: %r' % r2.get_json())


def test_un_PQR_que_no_se_pudo_registrar_avisa_YA(app, db_clean):
    """El workflow de GHL de Sebastián NO permite ramificar sobre la respuesta del webhook (su
    versión no expone ese campo), así que del lado de GHL un fallo es indistinguible de un éxito.
    La alarma vive en EOS, que es donde además queda auditable: un intento que no se pudo
    registrar es una queja de cliente que se perdió, y su plazo de respuesta corre igual.

    Una vez al día: la campana que suena por cada mensaje deja de mirarse.
    """
    _sql("DELETE FROM app_settings WHERE clave='pqr_aviso_fallo'")
    cli = app.test_client()
    r = cli.post('/api/pqr/inbound',
                 json={'contact_id': 'ZZTEST-SINTEXTO', 'full_name': 'ZZ Cliente'},
                 headers=_tok_headers())
    assert r.status_code == 400, r.data[:300]
    j = r.get_json()
    assert j.get('por_que') and j.get('como_arreglarlo'), (
        'el error no dice qué arreglar · así se perdieron seis semanas: %r' % j)
    fila = _sql("SELECT valor FROM app_settings WHERE clave='pqr_aviso_fallo'")
    assert fila, 'no dejó registro de que avisó'
