# -*- coding: utf-8 -*-
"""La progresión de un cliente: cada paso exige el HECHO que lo justifica.

Sebastián (13-ago): *"revisar bien la progresión de cada cliente, qué pasos deben llegar hasta ser
cliente oficial y tener usuario"*.

Un pipeline donde se puede arrastrar la tarjeta a "contrato" sin que exista un contrato firmado no
es un seguimiento: es una lista de deseos que se lee como un compromiso, y quien decide mirando eso
decide mal. Las columnas de cada hito ya existían en la tabla desde el día uno y nadie las llenaba;
acá se vuelven la condición para avanzar.

Y el usuario del portal NO se crea antes del contrato, porque el portal sirve para PEDIR: darle
acceso a quien no firmó es dejar entrar pedidos sin respaldo.
"""
import pytest

TEST_PASSWORD = "TestPass123"
EMPRESA = "PROGTEST CLIENTE MAQUILA"


@pytest.fixture
def luz(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "luz", "password": TEST_PASSWORD},
               headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar(app):
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.cursor().execute("DELETE FROM maquila_pipeline WHERE empresa LIKE 'PROGTEST%'")
        conn.commit()


def _tarjeta(app, stage='consulta'):
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO maquila_pipeline (empresa, stage, owner) VALUES (?,?,'luz')",
                  (EMPRESA, stage))
        conn.commit()
        return c.lastrowid


def _stage(app, mid):
    with app.app_context():
        from database import get_db
        return get_db().cursor().execute(
            "SELECT stage, nda_firmado_at FROM maquila_pipeline WHERE id=?", (mid,)).fetchone()


def test_no_avanza_sin_el_hecho_que_lo_justifica(app, luz):
    """Pasar a NDA sin NDA firmado es escribir un compromiso que no existe."""
    _limpiar(app)
    mid = _tarjeta(app)
    r = luz.post('/api/comercial/maquila/%d/avanzar' % mid, json={},
                 headers={'Origin': 'http://localhost'})
    assert r.status_code == 422, 'avanzó sin el hito: %s' % r.get_data(as_text=True)[:200]
    d = r.get_json()
    assert d['codigo'] == 'FALTA_HITO' and d['campo'] == 'nda_firmado_at'
    assert d.get('que_hace_falta'), 'no dijo QUÉ falta: obliga a adivinar'
    assert _stage(app, mid)[0] == 'consulta', 'movió la tarjeta igual'


def test_avanza_registrando_el_hecho_en_el_mismo_acto(app, luz):
    _limpiar(app)
    mid = _tarjeta(app)
    r = luz.post('/api/comercial/maquila/%d/avanzar' % mid,
                 json={'registrar_hito': True, 'fecha': '2026-08-01'},
                 headers={'Origin': 'http://localhost'})
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    st = _stage(app, mid)
    assert st[0] == 'nda' and st[1] == '2026-08-01', \
        'avanzó pero no dejó registrado el hecho: %s' % (st,)


def test_el_usuario_del_portal_solo_desde_el_CONTRATO(app, luz):
    """El portal sirve para PEDIR. Antes del contrato, un cliente no puede tener usuario."""
    _limpiar(app)
    mid = _tarjeta(app, 'cotizacion')
    d = luz.get('/api/comercial/maquila/progresion').get_json()
    yo = [x for x in d['clientes'] if x['id'] == mid][0]
    assert yo['progresion']['puede_tener_usuario'] is False, \
        'le habilitó usuario a un cliente que todavía no firmó'

    luz.post('/api/comercial/maquila/%d/avanzar' % mid,
             json={'registrar_hito': True}, headers={'Origin': 'http://localhost'})
    d2 = luz.get('/api/comercial/maquila/progresion').get_json()
    yo2 = [x for x in d2['clientes'] if x['id'] == mid][0]
    assert yo2['progresion']['stage'] == 'contrato'
    assert yo2['progresion']['puede_tener_usuario'] is True, \
        'firmó el contrato y sigue sin poder tener usuario'


def test_dice_de_quien_esta_esperando_QUE(app, luz):
    """Lo que evita que se pierdan: la pregunta se contesta mirando, no acordándose."""
    _limpiar(app)
    mid = _tarjeta(app, 'nda')
    d = luz.get('/api/comercial/maquila/progresion').get_json()
    yo = [x for x in d['clientes'] if x['id'] == mid][0]
    assert yo['progresion']['siguiente'] == 'brief'
    assert yo['progresion']['falta']['campo'] == 'brief_recibido_at'
    assert d['resumen']['esperando_algo'] >= 1


def test_no_deja_saltarse_etapas(app, luz):
    """Un cliente que aparece en contrato sin haber pasado por el brief deja un hueco que nadie
    puede reconstruir después."""
    _limpiar(app)
    mid = _tarjeta(app)
    for _ in range(2):
        luz.post('/api/comercial/maquila/%d/avanzar' % mid, json={'registrar_hito': True},
                 headers={'Origin': 'http://localhost'})
    assert _stage(app, mid)[0] == 'brief', 'saltó etapas: %s' % (_stage(app, mid),)


def test_avanzar_queda_auditado(app, luz):
    _limpiar(app)
    mid = _tarjeta(app)
    luz.post('/api/comercial/maquila/%d/avanzar' % mid, json={'registrar_hito': True},
             headers={'Origin': 'http://localhost'})
    with app.app_context():
        from database import get_db
        n = get_db().cursor().execute(
            "SELECT COUNT(*) FROM audit_log WHERE accion='AVANZAR_PIPELINE_MAQUILA' "
            "  AND registro_id=?", (str(mid),)).fetchone()
    assert n[0] >= 1, 'mover un cliente de etapa no dejó rastro'


def test_compras_no_puede_avanzar_a_nadie(app):
    """El pipeline sigue siendo confidencial: los DOS bordes (M171)."""
    c = app.test_client()
    c.post("/login", data={"username": "catalina", "password": TEST_PASSWORD},
           headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert c.post('/api/comercial/maquila/1/avanzar', json={},
                  headers={'Origin': 'http://localhost'}).status_code == 403
    assert c.get('/api/comercial/maquila/progresion').status_code == 403


def test_dice_cuantos_DIAS_lleva_sin_movimiento(app, luz):
    """Sebastián lo dejó escrito en el calendario, sobre un cliente real: *"un lead del 25 de
    junio que estuvo 37 días sin respuesta de nuestra parte"*.

    Eso no lo ve nadie mirando una tarjeta: se ve mirando la columna. Y no aplica a lo cerrado --
    un cliente ganado no "espera respuesta".
    """
    _limpiar(app)
    mid = _tarjeta(app)
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.cursor().execute("UPDATE maquila_pipeline SET creado_en=?, actualizado_en=NULL "
                              " WHERE id=?", ('2026-06-25 09:00:00', mid))
        conn.commit()
    d = luz.get('/api/comercial/maquila/progresion').get_json()
    yo = [x for x in d['clientes'] if x['id'] == mid][0]
    assert (yo.get('dias_sin_movimiento') or 0) > 30, \
        'no cuenta los días sin respuesta: %s' % yo.get('dias_sin_movimiento')
    assert d['resumen']['sin_movimiento_7d'] >= 1


def test_un_cliente_GANADO_no_espera_respuesta(app, luz):
    _limpiar(app)
    mid = _tarjeta(app, 'ganado')
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.cursor().execute("UPDATE maquila_pipeline SET creado_en=? WHERE id=?",
                              ('2026-01-01 09:00:00', mid))
        conn.commit()
    d = luz.get('/api/comercial/maquila/progresion').get_json()
    yo = [x for x in d['clientes'] if x['id'] == mid][0]
    assert yo.get('dias_sin_movimiento') is None, 'cuenta días de espera en un cliente cerrado'
