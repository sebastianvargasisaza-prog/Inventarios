# -*- coding: utf-8 -*-
"""Luz da de alta un cliente de maquila, y el cliente NACE en el pipeline.

Sebastián (13-ago): *"que en el módulo de Espagiria Luz pueda crearlos, además de que tenemos que
montar el pipeline de clientes para no perdernos"*.

Las dos mitades son la misma cosa. Un cliente dado de alta que no queda en ninguna cola de
seguimiento **es exactamente el que se pierde**: desde afuera se ve igual que uno atendido. Por eso
el alta y la entrada al pipeline son UN acto, no dos botones que alguien tiene que recordar.
"""
import pytest

TEST_PASSWORD = "TestPass123"
NOMBRE = "MAQTEST BLURR PRUEBA"


@pytest.fixture
def luz(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "luz", "password": TEST_PASSWORD},
               headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert r.status_code == 302, 'luz no pudo entrar'
    return c


def _limpiar(app):
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM clientes_maquila WHERE nombre LIKE 'MAQTEST%'")
        c.execute("DELETE FROM maquila_pipeline WHERE empresa LIKE 'MAQTEST%'")
        conn.commit()


def _pipeline(app, nombre):
    with app.app_context():
        from database import get_db
        return get_db().cursor().execute(
            "SELECT id, stage, owner FROM maquila_pipeline WHERE empresa=?", (nombre,)).fetchall()


def test_el_alta_abre_la_tarjeta_del_pipeline_en_el_mismo_acto(app, luz):
    _limpiar(app)
    r = luz.post('/api/espagiria/clientes-maquila',
                 json={'nombre': NOMBRE, 'email': 'hola@blurr.co', 'telefono': '3001112222'},
                 headers={'Origin': 'http://localhost'})
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    d = r.get_json()
    assert d['cliente_id'] and d['pipeline_id'] and d['pipeline_nuevo'] is True
    filas = _pipeline(app, NOMBRE)
    assert len(filas) == 1, 'el cliente no quedo en el pipeline: se pierde'
    assert filas[0][1] == 'consulta'
    assert filas[0][2] == 'luz', 'la tarjeta quedo sin dueno: %s' % (filas[0],)


def test_dar_de_alta_dos_veces_NO_abre_dos_tarjetas(app, luz):
    """Dos tarjetas del mismo cliente son dos personas persiguiendolo sin saberlo."""
    _limpiar(app)
    luz.post('/api/espagiria/clientes-maquila', json={'nombre': NOMBRE},
             headers={'Origin': 'http://localhost'})
    r2 = luz.post('/api/espagiria/clientes-maquila',
                  json={'nombre': NOMBRE, 'permitir_existente': True},
                  headers={'Origin': 'http://localhost'})
    assert r2.status_code == 200, r2.get_data(as_text=True)[:300]
    assert r2.get_json()['pipeline_nuevo'] is False
    assert len(_pipeline(app, NOMBRE)) == 1, 'abrio una segunda tarjeta del mismo cliente'


def test_el_nombre_repetido_avisa_en_vez_de_reventar(app, luz):
    """`nombre` es UNIQUE: el chequeo va por la MISMA columna del indice y sin filtrar por
    `activo`, o el INSERT choca y en PostgreSQL deja la transaccion abortada."""
    _limpiar(app)
    luz.post('/api/espagiria/clientes-maquila', json={'nombre': NOMBRE},
             headers={'Origin': 'http://localhost'})
    r = luz.post('/api/espagiria/clientes-maquila', json={'nombre': NOMBRE.lower()},
                 headers={'Origin': 'http://localhost'})
    assert r.status_code == 409 and r.get_json().get('codigo') == 'YA_EXISTE', \
        'no aviso del duplicado: %s' % r.get_data(as_text=True)[:200]


def test_reactiva_al_que_estaba_dado_de_baja_en_vez_de_duplicarlo(app, luz):
    _limpiar(app)
    luz.post('/api/espagiria/clientes-maquila', json={'nombre': NOMBRE},
             headers={'Origin': 'http://localhost'})
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.cursor().execute("UPDATE clientes_maquila SET activo=0 WHERE nombre=?", (NOMBRE,))
        conn.commit()
    r = luz.post('/api/espagiria/clientes-maquila', json={'nombre': NOMBRE},
                 headers={'Origin': 'http://localhost'})
    assert r.status_code == 200 and r.get_json()['reactivado'] is True
    with app.app_context():
        from database import get_db
        n = get_db().cursor().execute(
            "SELECT COUNT(*) FROM clientes_maquila WHERE nombre=?", (NOMBRE,)).fetchone()
    assert n[0] == 1, 'lo duplico en vez de reactivarlo'


def test_DICE_si_el_cliente_puede_entrar_al_portal(app, luz):
    """Un cliente sin credencial no ve el portal, y eso no da ningun error: simplemente nunca
    entra a pedir. Un hueco DICHO es accionable; uno silencioso se descubre cuando el cliente
    llama preguntando por que no puede."""
    _limpiar(app)
    d = luz.post('/api/espagiria/clientes-maquila', json={'nombre': NOMBRE},
                 headers={'Origin': 'http://localhost'}).get_json()
    assert d.get('tiene_portal') is False
    assert 'portal' in (d.get('aviso') or '').lower(), 'no dijo nada del acceso: %s' % d.get('aviso')


def test_el_alta_queda_auditada(app, luz):
    """Un maestro que se toca sin dejar quien fue no se puede revisar despues (M175)."""
    _limpiar(app)
    luz.post('/api/espagiria/clientes-maquila', json={'nombre': NOMBRE},
             headers={'Origin': 'http://localhost'})
    with app.app_context():
        from database import get_db
        n = get_db().cursor().execute(
            "SELECT COUNT(*) FROM audit_log WHERE accion IN "
            "('CREAR_CLIENTE_MAQUILA','ABRIR_PIPELINE_MAQUILA') AND usuario='luz'").fetchone()
    assert n[0] >= 2, 'el alta o la apertura del pipeline no dejaron rastro'


# ------------------------------------------------ quien ve y quien MUEVE el pipeline

def _entrar(app, quien):
    c = app.test_client()
    r = c.post("/login", data={"username": quien, "password": TEST_PASSWORD},
               headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert r.status_code == 302, '%s no pudo entrar' % quien
    return c


def test_luz_VE_el_pipeline(app):
    """El pipeline existía y la única persona que lo iba a usar no lo veía (M121)."""
    assert _entrar(app, 'luz').get('/api/comercial/maquila').status_code == 200


def test_compras_sigue_AFUERA_del_pipeline(app):
    """Abrirle a Luz no puede abrirle a todo el mundo: el pipeline B2B es confidencial a
    propósito. Un test que sólo prueba que el nuevo entra pasa verde aunque el gate se haya caído
    entero (M171: probar los DOS bordes)."""
    r = _entrar(app, 'catalina').get('/api/comercial/maquila')
    assert r.status_code == 403, 'el pipeline quedó abierto para compras'


def test_el_que_no_puede_VER_tampoco_puede_MOVER(app):
    """El GET era sólo admin y el PATCH no gateaba nada: cualquiera con login podía cambiarle la
    etapa a un cliente, su valor estimado, o marcarlo perdido. La asimetría entre leer y escribir
    es la firma del hueco (M45)."""
    r = _entrar(app, 'catalina').patch('/api/comercial/maquila/1',
                                       json={'stage': 'perdido'},
                                       headers={'Origin': 'http://localhost'})
    assert r.status_code == 403, 'compras puede mover el pipeline: %s' % r.status_code


def test_la_pagina_no_abre_en_blanco_para_quien_no_puede(app):
    """Una pantalla que abre vacía se lee como rota, no como prohibida."""
    assert _entrar(app, 'catalina').get('/comercial').status_code == 403
    assert _entrar(app, 'luz').get('/comercial').status_code == 200
