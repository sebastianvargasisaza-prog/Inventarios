# -*- coding: utf-8 -*-
"""Quién entra a cada módulo · la matriz que dictó Sebastián el 7-ago-2026.

Se transcribe acá tal como la dictó, porque un permiso que sólo vive en el código se cambia sin
que nadie note que cambió. Si mañana alguien mueve a una persona de módulo, este archivo se pone
rojo y obliga a decir por qué.

⚠ Cada persona se prueba en los DOS sentidos: lo que SÍ puede abrir y lo que NO. Un test que sólo
verifica el 403 pasa verde aunque el gate haya trabado a todo el mundo, y ése es el error que
duele -- abrir de más no se nota, abrir de menos se descubre con alguien parado en pleno turno
(M32/M121).
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

TEST_PASSWORD = 'TestPass123'

# Lo que dictó, persona por persona: (usuario, módulos que SÍ, módulos que NO)
# 'solicitudes', 'recepcion' y 'chat' son para todos, así que no se repiten en cada fila.
MATRIZ = [
    ('sebastian', ['gerencia', 'tesoreria', 'planta', 'calidad', 'aseguramiento', 'tecnica',
                   'compras', 'rrhh', 'marketing', 'clientes', 'animus', 'espagiria'], []),
    ('alejandro', ['gerencia', 'tesoreria', 'planta', 'calidad', 'aseguramiento'], []),

    # Jefes
    ('miguel',    ['aseguramiento', 'calidad', 'planta'],
                  ['compras', 'tesoreria', 'rrhh', 'marketing', 'gerencia']),
    ('hernando',  ['tecnica', 'aseguramiento', 'calidad', 'planta'],
                  ['compras', 'tesoreria', 'rrhh', 'marketing']),
    ('laura',     ['calidad', 'planta'],
                  ['aseguramiento', 'compras', 'tesoreria', 'rrhh', 'gerencia']),
    ('yuliel',    ['calidad', 'planta'],
                  ['aseguramiento', 'compras', 'tesoreria', 'rrhh']),
    ('jose',      ['planta'],
                  ['compras', 'tesoreria', 'rrhh', 'calidad', 'aseguramiento', 'gerencia']),

    # Administración
    ('catalina',  ['compras', 'planta', 'calidad'],
                  ['tesoreria', 'aseguramiento', 'tecnica', 'rrhh', 'gerencia']),
    ('luz',       ['compras', 'planta', 'calidad', 'tecnica', 'aseguramiento', 'rrhh',
                   'espagiria', 'clientes', 'bienestar'],
                  ['tesoreria', 'gerencia', 'marketing', 'animus']),
    ('mayra',     ['tesoreria', 'compras', 'rrhh'],
                  ['planta', 'calidad', 'aseguramiento', 'tecnica', 'gerencia', 'marketing']),
    ('gloria',    ['rrhh', 'bienestar'],
                  ['planta', 'compras', 'tesoreria', 'calidad', 'marketing', 'gerencia']),

    # Comercial y marcas
    ('jefferson', ['marketing'],
                  ['planta', 'compras', 'tesoreria', 'calidad', 'rrhh', 'gerencia']),
    ('daniela',   ['animus'],
                  ['planta', 'compras', 'tesoreria', 'calidad', 'rrhh', 'marketing', 'gerencia']),
    ('valentina', ['clientes'],
                  ['planta', 'compras', 'tesoreria', 'calidad', 'rrhh', 'gerencia']),

    # Operarios · lo general y planta, nada más
    ('camilo',    ['planta'],
                  ['compras', 'tesoreria', 'rrhh', 'calidad', 'aseguramiento', 'tecnica',
                   'marketing', 'clientes', 'gerencia', 'animus', 'espagiria']),
    ('mayerlin',  ['planta'], ['compras', 'tesoreria', 'calidad', 'gerencia']),
    ('smurillo',  ['planta'], ['compras', 'tesoreria', 'calidad', 'gerencia']),
    ('milton',    ['planta'], ['compras', 'tesoreria', 'calidad', 'gerencia']),
]

GENERAL = ('solicitudes', 'recepcion', 'chat')

# ⚠ TODOS los tests de este archivo piden la fixture `app`, incluso los que sólo leen
# `config`. Sin ella, `config` se importa ANTES de que se siembren las claves de prueba y
# queda cacheado sin ellas: el login del test SIGUIENTE empieza a fallar con
# 'env var no hasheada', y el rojo aparece lejísimos de su causa. Ya estaba escrito en el
# cerebro (M165) y lo pisé igual.


def test_cada_persona_entra_a_LO_SUYO(app):
    """El borde que se rompe si el gate se pone de más."""
    from config import puede_ver_modulo
    faltan = []
    for usuario, si, _no in MATRIZ:
        for m in list(si) + list(GENERAL):
            if not puede_ver_modulo(usuario, m):
                faltan.append('%s NO entra a %s' % (usuario, m))
    assert not faltan, faltan


def test_y_NO_entra_a_lo_que_no_es_suyo(app):
    from config import puede_ver_modulo
    sobran = []
    for usuario, _si, no in MATRIZ:
        for m in no:
            if puede_ver_modulo(usuario, m):
                sobran.append('%s SÍ entra a %s' % (usuario, m))
    assert not sobran, sobran


def test_lo_GENERAL_es_para_todos(app):
    """*"hay cosas que son para todos como solicitudes y recepciones, chat"*.

    "Todos" son los que TRABAJAN acá. `COMPRAS_USERS` no es ese universo: conserva a quien ya se
    fue para que sus registros firmados sigan siendo atribuibles -- borrarlo los dejaría sin
    dueño (GMP conserva el rastro). Quien está desvinculado no ve nada, y el login además lo
    bloquea en la base.
    """
    from config import puede_ver_modulo, COMPRAS_USERS, USUARIOS_DESVINCULADOS
    activos = set(COMPRAS_USERS) - USUARIOS_DESVINCULADOS
    faltan = [(u, m) for u in activos for m in GENERAL if not puede_ver_modulo(u, m)]
    assert not faltan, faltan


def test_y_el_DESVINCULADO_es_exactamente_la_excepcion(app):
    """Con más dientes que sólo sacarlo del universo: si mañana el barrido saca de más, o si
    alguien vuelve a meter a un desvinculado, este test lo dice."""
    from config import puede_ver_modulo, COMPRAS_USERS, USUARIOS_DESVINCULADOS
    assert USUARIOS_DESVINCULADOS, 'la lista está vacía: nadie la mantiene'
    for quien in USUARIOS_DESVINCULADOS:
        for m in GENERAL:
            assert not puede_ver_modulo(quien, m), \
                '%s está desvinculado y sigue viendo %s' % (quien, m)
    # y el borde: nadie más perdió los módulos generales
    ciegos = sorted(u for u in set(COMPRAS_USERS) - USUARIOS_DESVINCULADOS
                    if not all(puede_ver_modulo(u, m) for m in GENERAL))
    assert not ciegos, 'el barrido dejó sin lo general a gente que trabaja acá: %r' % (ciegos,)


def test_los_operarios_RECIBEN(app):
    """Sebastián: *"pueden recepcionar"*. Es lo que ya hacen en el piso: registran lo que llega.
    Liberar el material y archivar una ficha siguen siendo de Calidad y de los jefes (eso se
    cerró aparte, con `puede_archivar`)."""
    from config import puede_ver_modulo, puede_archivar
    for op in ('camilo', 'mayerlin', 'smurillo', 'milton'):
        assert puede_ver_modulo(op, 'recepcion'), '%s no puede recepcionar' % op
        assert not puede_archivar(op), '%s podría archivar una ficha maestra' % op


def test_los_que_SALIERON_no_entran_a_nada(app):
    """Sergio y Felipe salieron de la empresa · Luis ya estaba dado de baja desde julio.

    No se borran del sistema: GMP y Part 11 conservan quién hizo qué, y sus firmas tienen que
    seguir siendo legibles. Lo que se bloquea es el login (mig 421) y salen de las listas de rol
    para no figurar con permisos en la matriz.
    """
    from config import puede_ver_modulo, PLANTA_USERS, MARKETING_USERS
    assert 'sergio' not in PLANTA_USERS
    assert 'felipe' not in MARKETING_USERS
    for quien in ('sergio', 'felipe'):
        for m in ('planta', 'compras', 'calidad', 'marketing', 'tesoreria', 'gerencia'):
            assert not puede_ver_modulo(quien, m), '%s todavía entra a %s' % (quien, m)


def test_el_login_de_los_que_salieron_esta_BLOQUEADO(app):
    """Sacarlos de las listas no alcanza: si sólo existieran en `config` seguirían entrando por el
    fallback de la variable de entorno. La fila en `users_passwords` con activo=0 es lo que de
    verdad cierra la puerta."""
    # ⚠ El test SIEMBRA su propio universo: `db_clean` vacía `users_passwords` entre tests, así
    # que mirar las filas que dejó la migración pasa aislado y falla en el gate (M102/M103). Lo
    # que se prueba acá es el MECANISMO -- que una fila con activo=0 de verdad cierra la puerta --
    # y que la migración las escribe (eso se verifica aparte, leyendo el SQL).
    from database import get_db
    from blueprints.core import _resolve_password_hash
    with app.app_context():
        c = get_db()
        for quien in ('sergio', 'felipe', 'luis'):
            c.execute("DELETE FROM users_passwords WHERE username=?", (quien,))
            c.execute("INSERT INTO users_passwords (username, password_hash, activo, changed_by) "
                      "VALUES (?, '!DESACTIVADO', 0, 'test')", (quien,))
        c.commit()
        for quien in ('sergio', 'felipe', 'luis'):
            assert not (_resolve_password_hash(quien) or ''), (
                '%s todavía resuelve una clave · seguiría entrando por el fallback de la env var'
                % quien)

    # y la migración es la que las escribe en producción
    import io as _io
    import os as _os
    sql = _io.open(_os.path.join(RAIZ, 'api', 'database.py'), encoding='utf-8').read()
    for quien in ('sergio', 'felipe'):
        assert ("UPDATE users_passwords SET activo=0 WHERE username='%s'" % quien) in sql,             'la migración no bloquea a %s' % quien
        assert ("VALUES ('%s', '!DESACTIVADO'" % quien) in sql, (
            'la migración no INSERTA la fila de %s · si sólo existe en config, el activo=0 no '
            'tiene qué actualizar y seguiría entrando' % quien)


def test_el_MENU_muestra_exactamente_lo_que_se_puede_abrir(app):
    """El menú y el gate salen del MISMO mapa. Si tuvieran listas separadas, un día el menú
    ofrecería una tarjeta que al abrirse da 403 -- o al revés, escondería algo a lo que la persona
    sí tiene acceso, y ella concluiría que la feature no existe (M1)."""
    import re
    from config import modulo_de_ruta, puede_ver_modulo
    for usuario in ('camilo', 'gloria', 'daniela', 'mayra', 'luz', 'catalina'):
        c = app.test_client()
        r = c.post('/login', data={'username': usuario, 'password': TEST_PASSWORD},
                   headers={'Origin': 'http://localhost'}, follow_redirects=False)
        assert r.status_code == 302, 'no pude loguear a %s' % usuario
        html = c.get('/modulos').data.decode('utf-8', 'ignore')
        for href in set(re.findall(r'<a class="mod-card" href="([^"]+)"', html)):
            m = modulo_de_ruta(href)
            assert (m is None) or puede_ver_modulo(usuario, m), \
                'el menú le ofrece %s a %s y no puede abrirlo' % (href, usuario)


def test_al_bloquear_se_DICE_por_que(app):
    """Un 403 mudo se vive como si la app estuviera rota y la persona reintenta (M109)."""
    c = app.test_client()
    c.post('/login', data={'username': 'camilo', 'password': TEST_PASSWORD},
           headers={'Origin': 'http://localhost'}, follow_redirects=False)
    r = c.get('/tesoreria')
    assert r.status_code == 403
    cuerpo = r.data.decode('utf-8', 'ignore')
    assert 'camilo' in cuerpo, 'no dice de quién es el usuario'
    assert 'Sebastian' in cuerpo or 'Alejandro' in cuerpo, 'no dice a quién pedírselo'
    assert '/modulos' in cuerpo, 'no ofrece volver'


def test_los_ENDPOINTS_no_se_gatearon_por_modulo(app):
    """Es deliberado y hay que dejarlo escrito: el gate nuevo cubre PÁGINAS, no las APIs.

    Una pantalla de un módulo llama endpoints de otro todo el tiempo (Planta pide stock, Calidad
    pide la OC). Cerrar las APIs por módulo rompería pantallas que hoy funcionan, y el síntoma
    sería alguien trabado en pleno turno sin que nadie sepa por qué (M121). Los endpoints
    conservan el gate que ya tenían.
    """
    c = app.test_client()
    c.post('/login', data={'username': 'camilo', 'password': TEST_PASSWORD},
           headers={'Origin': 'http://localhost'}, follow_redirects=False)
    r = c.get('/api/inventario')
    assert r.status_code != 403, 'el gate de módulo se comió una API · romperá pantallas'


def test_el_LOGOUT_nunca_queda_detras_de_un_permiso(app):
    """Si salir estuviera detrás de un módulo, alguien sin acceso no podría ni cerrar sesión."""
    from config import modulo_de_ruta
    for r in ('/logout', '/login', '/modulos', '/cambiar-password', '/'):
        assert modulo_de_ruta(r) is None, '%s quedó detrás de un permiso' % r
