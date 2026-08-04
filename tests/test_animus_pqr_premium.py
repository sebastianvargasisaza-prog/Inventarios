"""PQR: el pedido del cliente, gestionar de verdad, y el indicador para el tablero (3-ago).

Sebastián: *"finalmente organizar PQR. Ya pusimos a GHL a disparar; ahora hagamos que se vea
premium, que aparezca número de pedido -- GHL pide eso, o lo puede jalar, revisemos qué dicen --
y el gestionar más premium y que realmente traiga a algo. PQR debe dar finalmente un indicador
que se refleje en el dashboard de ÁNIMUS y sume a CEO para saber qué está pasando"*.

Sobre el número de pedido: la columna `pedido_numero` **existía desde una migración vieja y nada
la escribía** -- el PATCH ni siquiera la aceptaba. Y depender de que GHL lo mande es frágil: ya
pasó que un campo personalizado no se resolviera dentro de un webhook y el buzón quedara mudo
seis semanas (M127). Como los pedidos ya están en EOS, se **cruzan**: correo, teléfono y nombre,
en ese orden de confianza, y el resultado se muestra como CANDIDATO -- adjudicarle el pedido
equivocado a una queja es peor que no tener ninguno (M19).
"""
from .conftest import TEST_PASSWORD, csrf_headers

MARCA = 'ZZPQR'


def _cli(app, quien='sebastian'):
    c = app.test_client()
    r = c.post("/login", data={"username": quien, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM animus_pqr WHERE descripcion LIKE ?", ('%' + MARCA + '%',))
        cur.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE ?", (MARCA + '%',))
        conn.commit()


def _pedido(app, sufijo, *, email='', direccion='', total=90000):
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, email, total, "
                    "moneda, estado, estado_pago, creado_en, direccion) "
                    "VALUES (?,?,?,?,'COP','','paid',date('now','-5 hours'),?)",
                    (MARCA + sufijo, '#' + sufijo, email, total, direccion))
        conn.commit()


def _pqr(cli, **kw):
    body = {'descripcion': MARCA + ' no me llegó el pedido', 'tipo': 'envio',
            'contacto_nombre': 'Ana Perez', 'contacto_email': 'ana@x.com',
            'contacto_telefono': '3001234567'}
    body.update(kw)
    r = cli.post('/api/animus/pqr', json=body, headers=csrf_headers())
    assert r.status_code == 201, r.data[:250]
    return r.get_json()['id']


def _html_animus():
    import ast as _ast, io as _io, os as _os
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    src = _io.open(_os.path.join(raiz, 'api', 'templates_py', 'animus_html.py'),
                   encoding='utf-8').read()
    for n in _ast.walk(_ast.parse(src)):
        if (isinstance(n, _ast.Assign) and isinstance(n.value, _ast.Constant)
                and isinstance(n.value.value, str) and len(n.value.value) > 5000):
            return n.value.value
    raise AssertionError('no encontré el HTML de /animus')


# ── EL NÚMERO DE PEDIDO ──────────────────────────────────────────────────────

def test_el_numero_de_pedido_por_fin_SE_PUEDE_GUARDAR(app, db_clean):
    """La columna existía y el PATCH no la aceptaba: se podía leer el pedido de una queja que
    nunca se había podido guardar."""
    _limpiar(app)
    c = _cli(app)
    pid = _pqr(c)
    r = c.patch('/api/animus/pqr/%d' % pid, json={'pedido_numero': '#5001'},
                headers=csrf_headers())
    assert r.status_code == 200, r.data[:250]
    from database import get_db
    with app.app_context():
        n = get_db().execute("SELECT pedido_numero FROM animus_pqr WHERE id=?", (pid,)).fetchone()[0]
    assert n == '#5001'


def test_cruza_el_pedido_por_correo(app, db_clean):
    _limpiar(app)
    _pedido(app, '-A', email='ana@x.com')
    c = _cli(app)
    pid = _pqr(c)
    d = c.get('/api/animus/pqr/%d/pedidos-cliente' % pid).get_json()
    assert d['ok'] is True
    assert d['candidatos'], 'no cruzó el pedido del cliente'
    assert d['candidatos'][0]['cruzo_por'] == 'correo'


def test_cruza_por_telefono_cuando_no_hay_correo(app, db_clean):
    """El teléfono se escribe de mil formas (+57, espacios, guiones): se comparan los dígitos."""
    _limpiar(app)
    _pedido(app, '-B', direccion='Calle 1 Ana Perez 3001234567')
    c = _cli(app)
    pid = _pqr(c, contacto_email='')
    d = c.get('/api/animus/pqr/%d/pedidos-cliente' % pid).get_json()
    assert d['candidatos'] and d['candidatos'][0]['cruzo_por'] == 'teléfono'


def test_NO_inventa_un_pedido_cuando_nada_cruza(app, db_clean):
    """Con dientes: si propusiera cualquier pedido, se le respondería a un cliente sobre el
    pedido de otro."""
    _limpiar(app)
    _pedido(app, '-C', email='otro@x.com', direccion='Calle 9 Juan Gomez 3109999999')
    c = _cli(app)
    pid = _pqr(c)
    d = c.get('/api/animus/pqr/%d/pedidos-cliente' % pid).get_json()
    assert d['candidatos'] == [], 'adjudicó un pedido que no es del cliente'
    assert d['aviso'], 'no declara que no encontró nada · su lista vacía se leería como un error'


def test_cada_candidato_dice_POR_CUAL_cruzo(app, db_clean):
    """Sin eso nadie puede verificar por qué se le adjudicó ese pedido a esa queja."""
    _limpiar(app)
    _pedido(app, '-D', email='ana@x.com')
    c = _cli(app)
    pid = _pqr(c)
    for x in c.get('/api/animus/pqr/%d/pedidos-cliente' % pid).get_json()['candidatos']:
        assert x['cruzo_por'] in ('correo', 'teléfono', 'nombre')
        assert x['pedido'] and x['fecha']


# ── EL INDICADOR ─────────────────────────────────────────────────────────────

def test_el_indicador_da_la_tasa_por_100_pedidos(app, db_clean):
    """El número que importa no es cuántas quejas hay -- eso sube solo si se vende más -- sino
    cuántas por cada 100 pedidos."""
    _limpiar(app)
    for i in range(4):
        _pedido(app, '-P%d' % i, email='x%d@x.com' % i)
    c = _cli(app)
    _pqr(c)
    d = c.get('/api/animus/pqr/indicador?dias=30').get_json()
    assert d['ok'] is True
    assert d['pedidos'] >= 4 and d['pqr'] >= 1
    assert d['tasa_por_100'] is not None and d['tasa_por_100'] > 0


def test_sin_pedidos_la_tasa_es_SIN_DATO_y_no_cero(app, db_clean):
    """Un cero se leería como 'el servicio está perfecto', que es lo contrario de lo que
    significa no poder calcularlo (M124)."""
    _limpiar(app)
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.cursor().execute("DELETE FROM animus_shopify_orders WHERE date(creado_en) >= "
                              "date('now','-5 hours','-30 day')")
        conn.commit()
    d = _cli(app).get('/api/animus/pqr/indicador?dias=30').get_json()
    assert d['tasa_por_100'] is None
    assert d['aviso'], 'no declara que no se puede calcular'


def test_el_indicador_dice_DONDE_mirar_y_que_tan_viejo(app, db_clean):
    _limpiar(app)
    c = _cli(app)
    _pqr(c, tipo='faltante')
    d = c.get('/api/animus/pqr/indicador').get_json()
    assert d['por_tipo'], 'sin el motivo que más pesa, el indicador no dice dónde mirar'
    assert 'mas_viejo' in d
    if d['mas_viejo']:
        assert 'dias' in d['mas_viejo'], 'un aviso que no envejece a la vista se vuelve ruido'


def test_el_promedio_de_respuesta_solo_cuenta_lo_respondido(app, db_clean):
    """Meter las no respondidas como 0 días diría que respondemos al instante."""
    _limpiar(app)
    c = _cli(app)
    _pqr(c)
    d = c.get('/api/animus/pqr/indicador').get_json()
    if d['respondidos'] == 0:
        assert d['dias_respuesta_promedio'] is None


# ── LA PANTALLA ──────────────────────────────────────────────────────────────

def test_gestionar_dejo_de_pedir_que_TECLEEN_el_estado():
    """Pedía escribir 'nuevo' / 'en_proceso' a mano en un cuadro de texto: un desplegable no se
    escribe mal, y un estado mal tecleado el backend lo rechaza sin que quede claro por qué."""
    html = _html_animus()
    assert 'async function gestionarPqr(id, estadoActual)' not in html
    assert 'function gestionarPqr(id)' in html
    assert 'id="modal-pqrges"' in html
    for campo in ('pq-pedido', 'pq-estado', 'pq-prioridad', 'pq-asignado', 'pq-respuesta'):
        assert 'id="%s"' % campo in html, campo


def test_la_pantalla_muestra_el_indicador():
    html = _html_animus()
    assert 'id="pqr-indicador"' in html and 'function cargarPqrIndicador(' in html
    assert 'cargarPqrIndicador()' in html.split("name === 'pqr'")[1][:120], \
        'el indicador no se carga al abrir la pestaña'
    assert 'id="pq-pedidos"' in html, 'no muestra los pedidos del cliente'


# ── EL SERVICIO SUBE AL CEO ──────────────────────────────────────────────────

def test_una_queja_vieja_sube_a_la_cola_del_CEO(app, db_clean):
    """Sebastián: "PQR debe... sumar a CEO para saber qué está pasando". Lo que entra no es el
    conteo de quejas -- ese sube solo si se vende más -- sino la que lleva días sin que nadie la
    toque: la gravedad la da la EDAD, no la cantidad (M129)."""
    _limpiar(app)
    c = _cli(app)
    pid = _pqr(c)
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.cursor().execute(
            "UPDATE animus_pqr SET creado_en=date('now','-5 hours','-9 day') WHERE id=?", (pid,))
        conn.commit()
    d = c.get('/api/centro/decisiones').get_json()
    clientes = [x for x in d['decisiones'] if x.get('grupo') == 'clientes']
    assert clientes, 'una queja de 9 días no llegó a la cola del CEO'
    assert clientes[0]['nivel'] == 'critico'
    assert 'dias' in clientes[0]['detalle'] or 'días' in clientes[0]['detalle']
    assert clientes[0]['accion'] == '/animus'


def test_una_queja_de_HOY_no_molesta_al_CEO(app, db_clean):
    """Con dientes: si toda queja nueva subiera, la cola del CEO se volvería ruido y dejaría de
    mirarse justo el día que importa."""
    _limpiar(app)
    c = _cli(app)
    _pqr(c)
    d = c.get('/api/centro/decisiones').get_json()
    frescas = [x for x in d['decisiones']
               if x.get('grupo') == 'clientes' and 'esperando respuesta' in x.get('titulo', '')]
    assert not frescas, 'una queja de hoy no es una decisión del gerente'
