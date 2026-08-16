"""La bandeja donde se RESPONDE lo que el cliente escribe (14-ago-2026).

Hasta hoy no existía: los endpoints para responder un PQR estaban desde mayo, la
campana avisaba con un enlace a `/admin?tab=portal_pqr` y el cron de plazos con otro
a `/admin/portal/pqr`. Ninguna de las dos rutas existe, así que un reclamo formal
(registro regulado, con plazo) sólo se podía responder por API.

Lo que fijan estos tests:
  - la pantalla existe y se llega a ella;
  - CALIDAD, que es la dueña del registro regulado, puede leer y responder (antes la
    campana le llegaba y al entrar le daba 403);
  - la respuesta del backoffice llega al portal del cliente;
  - ningún aviso apunta a una pantalla que no existe.
"""
import os
import re
import sqlite3

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


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _limpiar():
    for sql in ("DELETE FROM portal_pqr WHERE cliente_id LIKE 'ZMSG%'",
                "DELETE FROM portal_clientes_credenciales WHERE cliente_id LIKE 'ZMSG%'"):
        try:
            _exec(sql)
        except Exception:
            pass


def _cliente(app, slug='ZMSG1'):
    email = slug.lower() + '@zmsg.test'
    adm = _login(app)
    r = adm.post('/api/admin/portal/credenciales', json={
        'cliente_id': slug, 'cliente_nombre': 'Cliente Mensajes',
        'email': email, 'password': 'ClavePortal123'}, headers=_h())
    assert r.status_code in (200, 201), r.data
    cli = app.test_client()
    assert cli.post('/api/portal/login',
                    json={'email': email, 'password': 'ClavePortal123'}).status_code == 200
    return cli


def test_la_bandeja_existe_y_se_llega_desde_los_clientes(app, db_clean):
    adm = _login(app)
    r = adm.get('/admin/portal-mensajes')
    assert r.status_code == 200, r.data
    html = r.data.decode('utf-8')
    for pieza in ('/api/admin/portal/pqr', '/api/admin/portal/solicitudes', 'X-CSRF-Token'):
        assert pieza in html, 'la bandeja no trae %s' % pieza
    b2b = adm.get('/admin/clientes-b2b').data.decode('utf-8')
    assert '/admin/portal-mensajes' in b2b, 'nadie puede llegar a la bandeja'


def test_la_bandeja_vieja_redirige_en_vez_de_dar_404(app, db_clean):
    """Estaba enlazada en avisos y marcadores: un 404 no explica nada (M120)."""
    adm = _login(app)
    r = adm.get('/admin/portal-rfq', follow_redirects=False)
    assert r.status_code in (301, 302), r.data
    assert '/admin/portal-mensajes' in r.headers.get('Location', '')


def test_ningun_aviso_apunta_a_una_pantalla_que_no_existe(app, db_clean):
    """El de PQR iba a `/admin?tab=portal_pqr` y el del cron a `/admin/portal/pqr`.

    ⚠ Ampliado el 15-ago. La versión anterior miraba DOS archivos y sólo los enlaces que
    empiezan con `/admin`: ese filtro decidía lo que no iba a encontrar (M174), y dejó pasar
    CUATRO avisos de Planta que llevaban a `/dashboard#...` -- una ruta que no existe, porque
    el dashboard de Planta es `/inventarios`. El operario recibía el aviso de lotes en
    cuarentena, hacía clic y no llegaba a ninguna parte; así se aprende que la campana no
    sirve, y ahí se pierden los avisos que sí importan (M202).

    También se verifica el ANCLA: el dashboard sólo abre pestaña con los nombres que su
    propio JS acepta, así que `/inventarios#inventario` llega a la página y no abre nada --
    desde la silla del usuario, lo mismo que un enlace roto.
    """
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rutas, patrones = set(), []
    for regla in app.url_map.iter_rules():
        r = str(regla.rule)
        if '<' in r:
            patrones.append(re.compile('^' + re.sub(r'<[^>]+>', '[^/]+', r) + '$'))
        else:
            rutas.add(r)

    # la lista blanca de pestañas la declara el propio dashboard: se lee de ahí, no se copia
    tabs = set()
    try:
        from templates_py.dashboard_html import DASHBOARD_HTML as _DH
        m = re.search(r"var valid = \[([^\]]+)\]", _DH)
        if m:
            tabs = set(re.findall(r"'([\w-]+)'", m.group(1)))
    except Exception:
        tabs = set()

    bp = os.path.join(raiz, 'api', 'blueprints')
    malos = []
    for arch in sorted(os.listdir(bp)):
        if not arch.endswith('.py'):
            continue
        with open(os.path.join(bp, arch), encoding='utf-8') as fh:
            texto = fh.read()
        for enlace in sorted(set(re.findall(r"""link\s*=\s*["'](/[^"']*)["']""", texto))):
            base = enlace.split('?')[0].split('#')[0].rstrip('/') or '/'
            ancla = enlace.split('#')[1] if '#' in enlace else ''
            if base not in rutas and not any(p.match(base) for p in patrones):
                malos.append('%s -> %s (la ruta no existe)' % (arch, enlace))
            elif ancla and base == '/inventarios' and tabs and ancla not in tabs:
                malos.append('%s -> %s (la pestaña "%s" no existe)' % (arch, enlace, ancla))
    assert not malos, 'avisos que llevan a una pantalla inexistente: %s' % malos


def test_calidad_puede_leer_y_responder_un_pqr(app, db_clean):
    """El PQR es un registro regulado y su dueño es Calidad, no sólo el admin (M32)."""
    _limpiar()
    cli = _cliente(app, 'ZMSG1')
    r = cli.post('/api/portal/pqr', json={
        'tipo': 'reclamo', 'titulo': 'Dos frascos con la tapa floja',
        'descripcion': 'De la última entrega, dos unidades traían la tapa mal ajustada.'})
    assert r.status_code in (200, 201), r.data
    pqr_id = r.get_json()['id']

    from config import CALIDAD_USERS
    usuario = sorted(CALIDAD_USERS)[0]
    qc = _login(app, usuario)

    lista = qc.get('/api/admin/portal/pqr')
    assert lista.status_code == 200, 'Calidad no pudo LEER su propio registro: %s' % lista.data
    assert any(i['id'] == pqr_id for i in lista.get_json()['items'])

    resp = qc.patch(f'/api/admin/portal/pqr/{pqr_id}',
                    json={'respuesta': 'Revisamos el lote y ajustamos el torque de la tapadora.',
                          'estado': 'respondido'}, headers=_h())
    assert resp.status_code == 200, 'Calidad no pudo RESPONDER: %s' % resp.data

    # y la respuesta llega al portal del cliente
    mio = [p for p in cli.get('/api/portal/mis-pqr').get_json()['pqrs'] if p['id'] == pqr_id][0]
    assert mio['estado'] == 'respondido'
    assert 'torque' in (mio['respuesta_admin'] or '')

    # la pantalla también abre para Calidad
    assert qc.get('/admin/portal-mensajes').status_code == 200


def test_quien_no_es_de_calidad_ni_admin_no_lee_los_pqr(app, db_clean):
    """Abrir el gate no puede volverlo una puerta: el borde se prueba (M121)."""
    from config import CALIDAD_USERS, ADMIN_USERS, PLANTA_USERS
    afuera = sorted(set(PLANTA_USERS) - set(CALIDAD_USERS) - set(ADMIN_USERS))
    if not afuera:
        return
    otro = _login(app, afuera[0])
    assert otro.get('/api/admin/portal/pqr').status_code == 403
