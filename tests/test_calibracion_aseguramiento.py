"""Bitácora de calibración de equipos · Aseguramiento (Miguel) · INVIMA.

Sebastián 21-jul-2026: "importante saber CUÁNDO se calibró cada equipo y cuándo vence la
próxima". La decisión fue que vive en ASEGURAMIENTO, no en Compras/Recepción.

Cubre: la lectura de la bitácora (estados y KPIs con UNA sola regla), el historial por
equipo, la trazabilidad con la OC de calibración (mig 376) y sobre todo la REGRESIÓN M32:
Miguel es el dueño del módulo pero el endpoint de registro estaba gateado solo a
CALIDAD_USERS, así que veía su bitácora y no podía escribir en ella (403).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

EQ_V = 'EQCALVIG'    # calibración vigente
EQ_X = 'EQCALVEN'    # calibración vencida
EQ_S = 'EQCALSIN'    # nunca calibrado
AREA = 'ACALTEST'


def _db():
    return sqlite3.connect(os.environ['DB_PATH'], timeout=15)


def _sql(*stmts):
    db = _db()
    try:
        for s in stmts:
            db.execute(s)
        db.commit()
    finally:
        db.close()


def _login(app, u):
    c = app.test_client()
    r = c.post('/login', data={'username': u, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pudo entrar %s' % u
    return c


def _limpiar():
    _sql("DELETE FROM equipos_eventos WHERE equipo_codigo IN ('%s','%s','%s')" % (EQ_V, EQ_X, EQ_S),
         "DELETE FROM equipos_planta WHERE codigo IN ('%s','%s','%s')" % (EQ_V, EQ_X, EQ_S),
         "DELETE FROM areas_planta WHERE codigo='%s'" % AREA)


def _sembrar():
    _limpiar()
    _sql("INSERT INTO areas_planta (codigo,nombre,tipo,activo) VALUES ('%s','Sala Calib Test','produccion',1)" % AREA,
         "INSERT INTO equipos_planta (codigo,nombre,area_codigo,tipo,activo) "
         "VALUES ('%s','Balanza vigente','%s','balanza',1)" % (EQ_V, AREA),
         "INSERT INTO equipos_planta (codigo,nombre,area_codigo,tipo,activo) "
         "VALUES ('%s','Balanza vencida','%s','balanza',1)" % (EQ_X, AREA),
         "INSERT INTO equipos_planta (codigo,nombre,area_codigo,tipo,activo) "
         "VALUES ('%s','Balanza sin calibrar','%s','balanza',1)" % (EQ_S, AREA),
         "INSERT INTO equipos_eventos (equipo_codigo,tipo_evento,fecha,fecha_proxima,estado,responsable,"
         "empresa_externa,certificado_url,numero_oc) VALUES "
         "('%s','calibracion','2026-01-10','2030-01-10','completado','Tecnico X',"
         "'CI Balanzas de Colombia','https://ej/cert.pdf','OC-2026-0268')" % EQ_V,
         "INSERT INTO equipos_eventos (equipo_codigo,tipo_evento,fecha,fecha_proxima,estado) VALUES "
         "('%s','calibracion','2024-01-10','2024-07-10','completado')" % EQ_X)


def test_mig376_columna_numero_oc(app):
    """mig 376: la calibración se ancla a la OC con que se compró el servicio."""
    with app.app_context():
        from database import get_db
        cols = {r[1] for r in get_db().execute("PRAGMA table_info(equipos_eventos)").fetchall()}
    assert 'numero_oc' in cols, 'falta equipos_eventos.numero_oc (mig 376)'


def test_bitacora_estados_y_kpis(app):
    """Vigente, vencido y sin calibrar salen bien clasificados y ordenados por urgencia."""
    _sembrar()
    c = _login(app, 'sebastian')
    try:
        r = c.get('/api/aseguramiento/calibracion')
        assert r.status_code == 200, r.data[:300]
        d = r.get_json()
        por_cod = {x['codigo']: x for x in d['items']}
        assert por_cod[EQ_V]['estado'] == 'vigente', por_cod[EQ_V]
        assert por_cod[EQ_V]['ultima'] == '2026-01-10'
        assert por_cod[EQ_V]['proxima'] == '2030-01-10'
        assert por_cod[EQ_V]['empresa'] == 'CI Balanzas de Colombia'
        assert por_cod[EQ_V]['numero_oc'] == 'OC-2026-0268'
        assert por_cod[EQ_X]['estado'] == 'vencido' and por_cod[EQ_X]['dias'] < 0
        assert por_cod[EQ_S]['estado'] == 'sin_calibrar'
        assert por_cod[EQ_S]['ultima'] == '' and por_cod[EQ_S]['dias'] is None
        # los KPIs cuentan lo mismo que la tabla (una sola regla · M5)
        k = d['kpis']
        assert k['total'] == len(d['items'])
        assert k['vigentes'] + k['proximos'] + k['vencidos'] + k['sin_calibrar'] == k['total']
        # lo vencido va primero (es lo que no se puede usar para fabricar)
        codigos = [x['codigo'] for x in d['items']]
        assert codigos.index(EQ_X) < codigos.index(EQ_V)
    finally:
        _limpiar()


def test_miguel_puede_registrar_calibracion(app):
    """REGRESIÓN M32: Miguel (Aseguramiento) es el dueño de la bitácora y DEBE poder escribirla.

    Antes el endpoint estaba gateado solo a CALIDAD_USERS y le devolvía 403: veía su módulo
    y no podía registrar nada.
    """
    _sembrar()
    c = _login(app, 'miguel')
    try:
        r = c.post('/api/calidad/equipos/%s/registrar-evento' % EQ_S, json={
            'tipo_evento': 'calibracion', 'fecha': '2026-07-24', 'fecha_proxima': '2027-07-24',
            'responsable': 'Miguel Valencia', 'empresa_externa': 'CI Balanzas de Colombia',
            'certificado_url': 'https://ej/cert-nuevo.pdf', 'numero_oc': 'OC-2026-0268',
            'resultado': 'conforme', 'observaciones': 'Calibración anual'}, headers=csrf_headers())
        assert r.status_code == 200, 'Miguel no pudo registrar la calibración: %s' % r.data[:300]
        assert r.get_json().get('ok') is True
        # la bitácora ya lo muestra vigente, con su OC y su certificado
        d = c.get('/api/aseguramiento/calibracion').get_json()
        it = next(x for x in d['items'] if x['codigo'] == EQ_S)
        assert it['estado'] == 'vigente', it
        assert it['numero_oc'] == 'OC-2026-0268'
        assert it['certificado_url'] == 'https://ej/cert-nuevo.pdf'
        # y queda en el historial del equipo (hoja de vida · INVIMA)
        h = c.get('/api/aseguramiento/calibracion/%s/historial' % EQ_S).get_json()
        assert h['equipo']['codigo'] == EQ_S
        assert len(h['eventos']) == 1
        assert h['eventos'][0]['responsable'] == 'Miguel Valencia'
        assert h['eventos'][0]['creado_por'] == 'miguel'
    finally:
        _limpiar()


def test_historial_equipo_inexistente(app):
    c = _login(app, 'sebastian')
    r = c.get('/api/aseguramiento/calibracion/NO-EXISTE-XYZ/historial')
    assert r.status_code == 404


def test_bitacora_exige_login(client):
    assert client.get('/api/aseguramiento/calibracion').status_code in (401, 302)
    assert client.get('/aseguramiento/calibracion').status_code in (302, 401)


def test_pagina_calibracion_abre(app):
    """La página premium responde para quien la usa (Aseguramiento/Calidad/Planta/Admin)."""
    c = _login(app, 'miguel')
    r = c.get('/aseguramiento/calibracion')
    assert r.status_code == 200, r.data[:200]
    html = r.data.decode('utf-8')
    assert 'Bit' in html and 'calibraci' in html.lower()
    assert 'cortex.css' in html, 'la página debe usar el sistema de diseño'
    assert chr(8212) not in html, 'sin em-dash en la UI'


def test_pagina_no_inyecta_widget_flotante(app):
    """La bitácora va EMBEBIDA como pestaña de /aseguramiento: si se le inyecta el widget
    flotante (campana + chat) sale duplicado sobre el del padre y, en la vista directa,
    tapa los botones de acción de las últimas filas."""
    c = _login(app, 'miguel')
    html = c.get('/aseguramiento/calibracion').data.decode('utf-8')
    assert '/api/notif/widget.js' not in html, 'no debe inyectar la campana (página embebida)'
    assert '/api/chat/widget.js' not in html, 'no debe inyectar el chat (página embebida)'
    # una página normal SÍ lo lleva (esto verifica que la exclusión es específica, no global)
    otra = c.get('/aseguramiento').data.decode('utf-8')
    assert '/api/notif/widget.js' in otra, 'la página contenedora sí debe llevar la campana'
