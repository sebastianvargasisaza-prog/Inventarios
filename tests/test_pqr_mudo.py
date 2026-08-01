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


# ══ la queja GRAVE que nadie abrió (31-jul) ════════════════════════════════════
#
# Sebastián abrió Aseguramiento y había 5 quejas por REACCIÓN ADVERSA en estado 'nueva',
# de hace 47 días. El vigía de plazos corría todos los días desde entonces... y las
# reportaba como "⏰ 5 nuevas sin triar (>1d)", igual que una queja por el empaque.
#
# El motivo: la rama 🚨 CRÍTICAS sólo miraba quejas que alguien YA había empezado a
# trabajar (en_triaje / en_investigacion). La peor de todas -- una reacción adversa que
# NADIE tocó nunca -- se quedaba fuera. La gravedad la da el TIPO de queja, no el avance
# de quien la atiende.

def _limpiar_quejas():
    _sql("DELETE FROM quejas_clientes WHERE codigo LIKE 'ZZQ-%'")


def _sembrar_queja(codigo, tipo, dias, estado='nueva', impacto=0):
    f = (date.today() - timedelta(days=dias)).isoformat()
    _sql("INSERT INTO quejas_clientes (codigo, cliente_nombre, tipo_queja, estado, "
         "impacto_salud, fecha_recepcion, descripcion, recibido_por, canal) "
         "VALUES (?,?,?,?,?,?,?,?,?)",
         (codigo, 'ZZ Cliente', tipo, estado, impacto, f, 'ZZ prueba', 'zztest', 'whatsapp'))


def _correr_plazos(app):
    from blueprints.auto_plan_jobs import job_quejas_plazos
    return job_quejas_plazos(app)


def test_una_REACCION_ADVERSA_sin_abrir_es_critica_desde_el_dia_1(app, db_clean):
    _limpiar_quejas()
    _sembrar_queja('ZZQ-RA', 'reaccion_adversa', dias=47)
    _sembrar_queja('ZZQ-EMP', 'envase_empaque', dias=47)
    try:
        ok, data, _ = _correr_plazos(app)
        assert ok, data
        assert data.get('sin_triar_criticas_1d') == 1, (
            'la reacción adversa sin abrir no se contó como crítica: %r' % data)
        assert data.get('sin_triar_1d') == 1, (
            'la queja de empaque debe seguir en la lista normal: %r' % data)
    finally:
        _limpiar_quejas()


def test_una_queja_comun_NO_escala_a_critica(app, db_clean):
    """Dientes del otro lado: si todo escala, nada escala."""
    _limpiar_quejas()
    _sembrar_queja('ZZQ-EMP2', 'envase_empaque', dias=10)
    try:
        ok, data, _ = _correr_plazos(app)
        assert ok, data
        assert data.get('sin_triar_criticas_1d') == 0, data
        assert data.get('sin_triar_1d') == 1, data
    finally:
        _limpiar_quejas()


# ══ que un mapeo equivocado NO vuelva a enmudecer el buzón (1-ago) ══════════════
#
# Sebastián: *"sigamos con PQR para que quede funcionando"*. El buzón estuvo mudo seis semanas
# porque el workflow mandaba el texto en un campo que GHL no resuelve, y EOS sólo miraba cuatro
# nombres de campo en el primer nivel del JSON. Un integrador externo cambia la forma del payload
# sin avisar; la tolerancia tiene que vivir de este lado.

def test_acepta_el_texto_venga_en_el_campo_que_venga(app, db_clean):
    from blueprints.aseguramiento import _texto_del_payload
    casos = [
        ({'message': 'hola'}, 'hola'),                              # lo de siempre
        ({'body': 'hola'}, 'hola'),
        ({'text': 'hola'}, 'hola'),                                 # nombre nuevo
        ({'message': {'body': 'hola'}}, 'hola'),                    # GHL manda el OBJETO
        ({'customData': {'mensaje': 'hola'}}, 'hola'),              # anidado en custom data
        ({'sms': {'text': 'hola'}}, 'hola'),
    ]
    for payload, esperado in casos:
        assert _texto_del_payload(payload) == esperado, payload


def test_NO_agarra_cualquier_texto_como_si_fuera_la_queja(app, db_clean):
    """Dientes: 'buscá el string más largo' metería un nombre o una URL como queja de cliente."""
    from blueprints.aseguramiento import _texto_del_payload
    assert _texto_del_payload({'full_name': 'Juan Perez', 'email': 'j@x.com'}) == ''
    assert _texto_del_payload({'contact': {'id': 'abc123', 'name': 'Juan'}}) == ''


def test_un_message_id_anidado_NO_se_usa_como_llave(app, db_clean):
    """La llave de dedup no puede salir de un `id` cualquiera del JSON: dos mensajes DISTINTOS
    colisionarían y el segundo se descartaría como duplicado (así se pierde una queja)."""
    from blueprints.aseguramiento import _campo_del_payload
    d = {'contact': {'id': 'ID-DE-OTRA-COSA'}, 'message': 'hola'}
    assert _campo_del_payload(d, ('message_id', 'messageId', 'id'), profundo=False) == ''


def test_un_intento_fallido_GUARDA_lo_que_ghl_mando(app, db_clean):
    """Antes se descartaba el payload: se perdía la queja Y la única pista de qué manda GHL."""
    _sql("DELETE FROM pqr_intentos_fallidos")
    _sql("DELETE FROM app_settings WHERE clave='pqr_aviso_fallo'")
    cli = app.test_client()
    r = cli.post('/api/pqr/inbound',
                 json={'contact_id': 'ZZTEST-EVIDENCIA', 'pqr_mensaje_raro': 'me salio brote'},
                 headers=_tok_headers())
    assert r.status_code == 400, r.data[:200]
    j = r.get_json()
    assert 'pqr_mensaje_raro' in (j.get('esto_fue_lo_que_mandaste') or ''), j
    filas = _sql("SELECT claves, payload FROM pqr_intentos_fallidos ORDER BY id DESC LIMIT 1")
    assert filas, 'no guardó el intento: la evidencia se perdió otra vez'
    assert 'pqr_mensaje_raro' in filas[0][0], filas[0]
    assert 'me salio brote' in filas[0][1], 'el texto del cliente no quedó guardado'


def test_el_endpoint_muestra_que_campos_manda_ghl(app, db_clean):
    _sql("DELETE FROM pqr_intentos_fallidos")
    _sql("DELETE FROM app_settings WHERE clave='pqr_aviso_fallo'")
    cli = app.test_client()
    cli.post('/api/pqr/inbound', json={'contact_id': 'ZZT-2', 'campo_inventado': 'hola'},
             headers=_tok_headers())
    from .conftest import TEST_PASSWORD, csrf_headers
    c2 = app.test_client()
    c2.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD},
            headers=csrf_headers(), follow_redirects=False)
    r = c2.get('/api/aseguramiento/pqr-intentos-fallidos')
    assert r.status_code == 200, r.data[:200]
    j = r.get_json()
    assert j['n'] >= 1, j
    assert 'campo_inventado' in j['campos_que_manda_ghl'], j['campos_que_manda_ghl']
    assert 'message' in j['campos_que_EOS_acepta_como_texto']


def test_E2E_una_queja_de_whatsapp_entra_y_aparece_en_la_bandeja(app, db_clean):
    """"Que quede funcionando": el recorrido completo con la forma de payload que manda un
    disparador de mensaje entrante de GHL -- el objeto `message` con el cuerpo adentro, que es
    exactamente lo que antes se caía con 400.

    Un test de unidad del extractor no alcanza: lo que hay que probar es que la queja LLEGA a
    la bandeja donde Miguel la va a ver (M94 · construido no es lo mismo que validado).
    """
    _sql("DELETE FROM pqr_inbox WHERE COALESCE(ghl_contact_id,'')='ZZE2E-CONTACT'")
    cli = app.test_client()
    r = cli.post('/api/pqr/inbound', headers=_tok_headers(), json={
        'contact_id': 'ZZE2E-CONTACT',
        'full_name': 'ZZ Cliente E2E',
        'phone': '+573001112233',
        'type': 'whatsapp',
        'message': {'id': 'ZZE2E-MSG-1', 'body': 'ZZTEST me salio brote con la crema, lote 123'},
    })
    assert r.status_code in (200, 201), r.data[:300]
    assert not (r.get_json() or {}).get('error'), r.get_json()

    fila = _sql("SELECT mensaje, canal, contacto_nombre, estado FROM pqr_inbox "
                "WHERE ghl_contact_id='ZZE2E-CONTACT' ORDER BY id DESC LIMIT 1")
    assert fila, 'la queja no quedó en el buzón'
    assert 'brote' in fila[0][0], fila[0]
    assert fila[0][3] == 'pendiente', fila[0]

    from .conftest import TEST_PASSWORD, csrf_headers
    c2 = app.test_client()
    c2.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD},
            headers=csrf_headers(), follow_redirects=False)
    rb = c2.get('/api/aseguramiento/pqr-inbox?estado=pendiente')
    assert rb.status_code == 200, rb.data[:200]
    _ids = [x.get('contacto_nombre') for x in (rb.get_json() or {}).get('inbox', [])]
    assert 'ZZ Cliente E2E' in _ids, 'entró al buzón pero NO aparece en la bandeja de triaje'
    _sql("DELETE FROM pqr_inbox WHERE COALESCE(ghl_contact_id,'')='ZZE2E-CONTACT'")
