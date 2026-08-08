# -*- coding: utf-8 -*-
"""La matriz de permisos se GENERA del código, y declara lo que no pudo resolver.

Sebastián 7-ago: *"dejemos esta tarea pendiente revisar qué puede hacer cada usuario"*.

Una matriz escrita a mano queda vieja el día que alguien agrega un endpoint, y a partir de ahí
miente con cara de documento (M122). Ésta se calcula leyendo el código cuando se pide.

⚠ La lección de método que este archivo protege, y que costó cuatro pasadas: **un detector que
grita de más deja de mirarse**. La primera versión reportó 667 rutas "sin gate" y eran 0:
   · no sabía que todo lo que cuelga de /api/ pasa por el hook global de login;
   · no conocía `_require_admin`, `_require_login`, `_require_qa_or_admin`;
   · y su regex sólo aceptaba comillas SIMPLES, así que una página que gatea con
     `session.get("compras_user")` le parecía abierta.
Lo que entra al informe es la lista VERIFICADA, no la cruda.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))


_CACHE = {}


def _matriz(fresca=False):
    """Se construye UNA vez para todo el archivo: parsear los 36 blueprints cuesta ~45 s y
    hacerlo seis veces ponía el archivo en 5 minutos. Un test lento es un gate que se corre
    menos, y un gate que se corre menos no protege nada (M105)."""
    import permisos_matriz as pm
    if fresca or 'd' not in _CACHE:
        _CACHE['d'] = pm.construir()
    return _CACHE['d']


def test_analiza_TODO_el_mapa_de_rutas(app):
    d = _matriz()
    assert d['total_rutas'] > 1000, 'analizó muy poco: %s' % d['total_rutas']


def test_no_reporta_como_ABIERTO_lo_que_cubre_el_login_global(app):
    """El falso positivo que hacía inútil al detector: 667 rutas marcadas sin gate cuando el hook
    global de /api/ ya las cubre. Un detector así no se mira nunca (M122)."""
    d = _matriz()
    sg = d['sin_gate_reconocido']
    de_api = [x for x in sg if x['ruta'].startswith('/api/')]
    assert not de_api, 'reporta como sin gate rutas que el hook global de /api/ ya cubre: %s' % de_api[:3]
    assert len(sg) < 40, ('demasiadas rutas sin resolver (%d): el detector volvió a gritar de más '
                          'y así deja de mirarse' % len(sg))


def test_conoce_los_guards_que_de_verdad_se_usan(app):
    """Si no conoce un guard, marca su ruta como abierta y manda a revisar algo que está bien."""
    import io as _io
    import re as _re
    src = _io.open(os.path.join(RAIZ, 'api', 'permisos_matriz.py'), encoding='utf-8').read()
    for g in ('_require_admin', '_require_login', '_require_qa_or_admin',
              '_require_compras_write', '_require_brd_ejecutor', '_autorizados_escritura'):
        assert g in src, 'el detector no conoce %s · marcaría sus rutas como abiertas' % g
    # y acepta las DOS comillas
    assert _re.search(r'\["\']compras_user\["\']', src) or '["\']compras_user' in src, \
        'el detector depende del estilo de comillas de quien escribió la línea'


def test_el_OPERARIO_no_aparece_pudiendo_archivar(app):
    """El cruce entre la matriz y la regla que Sebastián dictó hoy: si la matriz dijera que un
    operario puede archivar, o la regla está mal aplicada o la matriz miente. Las dos importan."""
    d = _matriz()
    from config import PLANTA_USERS
    culpables = []
    for r in d['rutas']:
        if 'puede_archivar' not in (r['gate'] or ''):
            continue
        for op in PLANTA_USERS:
            if r['quienes'] and op in r['quienes']:
                culpables.append((op, r['ruta']))
    assert not culpables, 'la matriz dice que un operario puede archivar: %s' % culpables[:3]


def test_DECLARA_lo_que_no_pudo_resolver(app):
    """Una ruta desprotegida reportada como protegida es lo peor de los dos mundos (M100)."""
    d = _matriz()
    assert 'sin_gate_reconocido' in d and 'aviso' in d
    for r in d['rutas']:
        assert 'resuelto' in r
        if not r['resuelto']:
            assert r['quienes'] is None, 'dice quién entra a una ruta cuyo gate no resolvió'


def test_marca_a_QUIEN_tiene_la_cuenta_desactivada(app):
    """Un empleado retirado sigue en `config` a propósito (Part 11 no borra personas · su login lo
    bloquea `users_passwords.activo=0`). Si la matriz no lo marca, muestra a alguien que se fue
    con permisos de escritura en 30 módulos, que es justo la objeción que uno no quiere en una
    auditoría."""
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM users_passwords WHERE username='zz_baja_test'")
        c.execute("INSERT INTO users_passwords (username, password_hash, activo, changed_by) "
                  "VALUES ('zz_baja_test','!DESACTIVADO',0,'test')")
        c.commit()
    try:
        d = _matriz(fresca=True)
        assert 'zz_baja_test' in d['usuarios_desactivados'], \
            'no detecta las cuentas bloqueadas · mostraría a alguien retirado con permisos'
    finally:
        with app.app_context():
            c = get_db()
            c.execute("DELETE FROM users_passwords WHERE username='zz_baja_test'")
            c.commit()


def test_la_pantalla_EXISTE_y_es_solo_admin(app, admin_client, client):
    """Un diagnóstico al que no se llega no existe (M121) · y una matriz de permisos abierta a
    todos es ella misma un problema de permisos."""
    r = admin_client.get('/admin/permisos')
    assert r.status_code == 200
    assert b'matriz-permisos' in r.data, 'la pantalla no consulta la matriz'
    r2 = client.get('/admin/permisos')       # sin sesión
    assert r2.status_code in (401, 403, 302), 'la matriz de permisos está abierta'
