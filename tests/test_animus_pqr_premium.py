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


# ── LAS DOS PREGUNTAS DE SEBASTIÁN (4-ago) ───────────────────────────────────
# "cuando se resuelva van desapareciendo, ¿dónde quedan?" y "¿cómo generan datos esos PQR?"
# Las dos eran síntomas del mismo defecto: la pantalla no explicaba su propio comportamiento.

def test_los_contadores_sirven_para_ENCONTRAR_los_resueltos():
    """Se resuelven y salen de la vista por el filtro, pero eso no se veía en ningún lado.
    Ahora el contador es un botón: la pregunta se contesta sola en vez de exigir que alguien
    descubra el desplegable de arriba."""
    html = _html_animus()
    assert 'function filtrarPqr(' in html
    i = html.index('var tarjetas = [')
    tabla = html[i:i + 700]
    for estado in ('nuevo', 'en_proceso', 'resuelto', 'cerrado'):
        assert "'%s'" % estado in tabla, 'el contador de %s no está' % estado
    assert 'onclick="filtrarPqr(' in html, 'los contadores no son clicables'
    # y el segundo click vuelve a todos: no deja a nadie atrapado en un filtro
    i = html.index('function filtrarPqr(')
    assert "sel.value === estado" in html[i:i + 600], 'el filtro no se puede quitar'


def test_la_pantalla_dice_DE_DONDE_vienen():
    """Entran solos por el webhook de GoHighLevel cuando un cliente escribe. No estaba dicho en
    ninguna parte, y de ahí la pregunta."""
    html = _html_animus()
    assert 'GoHighLevel' in html, 'no dice de dónde salen los PQR'
    assert 'id="pqr-ultimo"' in html, 'no muestra cuándo entró el último'


def test_la_lista_muestra_la_ANTIGUEDAD():
    """Un reclamo de hace 40 días no puede leerse igual que uno de hoy · un aviso que no
    envejece a la vista se vuelve ruido (M129)."""
    html = _html_animus()
    i = html.index('async function loadAnimusPqr(')
    cuerpo = html[i:i + 6000]
    assert 'hace ' in cuerpo and '86400000' in cuerpo, 'la lista no muestra cuántos días lleva'
    assert 'var(--cx-danger-text)' in cuerpo, 'lo viejo no se distingue de lo de hoy'


def test_la_lista_muestra_el_pedido_cuando_lo_hay():
    html = _html_animus()
    i = html.index('async function loadAnimusPqr(')
    assert 'p.pedido_numero' in html[i:i + 6000], 'el pedido adjudicado no se ve en la lista'


# ── LO QUE NO ES UNA QUEJA SALE (pero se puede devolver) · 4-ago ─────────────
# Sebastián: *"elimina todos los que están, esto no es PQR: 'Más promos... me encantaría ser
# creadora para su marca' / 'Quiero saber método de pago y en cuánto tiempo llegan'"*.
# Son CONSULTAS DE VENTA. Una bandeja llena de eso entierra las quejas de verdad y le infla el
# indicador al servicio (M138: un registro lleno de ruido no queda incompleto, queda FALSO).

def _filtro():
    from blueprints.animus import _pqr_es_consulta
    return _pqr_es_consulta


def test_reconoce_las_consultas_que_Sebastian_marco(app):
    f = _filtro()
    for m in ("Mas promos, justo ayer no alcance. Me encantaria ser creadora para su marca",
              "Quiero saber metodo de pago y en cuanto tiempo llegan vivo en barranquilla",
              "Este producto que concentracion tiene de retinal",
              "Y me gustaria saber el modo de uso de los productos"):
        assert f(m), 'no reconoció como consulta: %s' % m[:50]


def test_NUNCA_toca_un_reclamo_real(app):
    """Lo que manda: botar una queja de verdad es mucho peor que dejar pasar una consulta. Por
    eso las pistas de reclamo se evalúan PRIMERO y ganan siempre."""
    f = _filtro()
    for m in ("Hola, revisando el numero de guia aparece como entregado, pero a mi no llego el pedido.",
              "Me llego el blush pero no me llego el lip serum",
              "ya me llego el pedido pero la crema viene en una presentacion distinta",
              "Mira que me rechaza el pago",
              "Disculpa, hice un pedido el 15 de julio y aun no llega",
              # el caso que MÁS importa: pregunta algo Y además reclama
              "Quiero saber el metodo de pago pero ademas mi pedido no ha llegado"):
        assert not f(m), '¡SE IRÍA UN RECLAMO REAL!: %s' % m[:60]


def test_descartar_saca_de_la_bandeja_pero_NO_borra(app, db_clean):
    _limpiar(app)
    c = _cli(app)
    pid = _pqr(c, descripcion=MARCA + ' quiero saber metodo de pago')
    r = c.post('/api/animus/pqr/%d/descartar' % pid,
               json={'motivo': 'Es una consulta de venta'}, headers=csrf_headers())
    assert r.status_code == 200
    # sale de la bandeja
    assert pid not in [x['id'] for x in c.get('/api/animus/pqr').get_json()['pqr']]
    # pero SIGUE existiendo y se puede ver
    d = c.get('/api/animus/pqr?estado=descartado').get_json()
    fila = [x for x in d['pqr'] if x['id'] == pid]
    assert fila, 'el descartado desapareció · no se puede revisar si estuvo bien sacarlo'
    assert fila[0]['descartado_motivo'] == 'Es una consulta de venta'
    # y se devuelve
    assert c.post('/api/animus/pqr/%d/descartar' % pid, json={'recuperar': True},
                  headers=csrf_headers()).status_code == 200
    assert pid in [x['id'] for x in c.get('/api/animus/pqr').get_json()['pqr']]


def test_descartar_SIN_motivo_no_pasa(app, db_clean):
    """Sin motivo nadie puede revisar después si estuvo bien sacarlo."""
    _limpiar(app)
    c = _cli(app)
    pid = _pqr(c)
    assert c.post('/api/animus/pqr/%d/descartar' % pid, json={},
                  headers=csrf_headers()).status_code == 400


def test_la_limpieza_masiva_MUESTRA_antes_de_aplicar(app, db_clean):
    """Un botón que saca 191 filas sin decir cuáles es un botón que nadie debería apretar."""
    _limpiar(app)
    c = _cli(app)
    _pqr(c, descripcion=MARCA + ' quiero saber cuanto cuesta el serum')
    _pqr(c, descripcion=MARCA + ' mi pedido no ha llegado hace 20 dias')
    d = c.get('/api/animus/pqr/consultas').get_json()
    assert d['ok'] is True and d['n'] >= 1
    textos = ' '.join(x['descripcion'] for x in d['candidatos'])
    assert 'cuanto cuesta' in textos
    assert 'no ha llegado' not in textos, 'propuso descartar un reclamo real'
    for x in d['candidatos']:
        assert x['motivo'] and x['fecha'], 'un candidato sin motivo no se puede revisar'


def test_el_indicador_NO_cuenta_lo_descartado(app, db_clean):
    """Si contara, la tasa por 100 pedidos mediría ruido y diría que el servicio empeoró."""
    _limpiar(app)
    c = _cli(app)
    pid = _pqr(c, descripcion=MARCA + ' quiero saber el precio')
    antes = c.get('/api/animus/pqr/indicador').get_json()['pqr']
    c.post('/api/animus/pqr/%d/descartar' % pid, json={'motivo': 'consulta de venta'},
           headers=csrf_headers())
    assert c.get('/api/animus/pqr/indicador').get_json()['pqr'] == antes - 1


def test_la_lista_trae_la_FECHA_y_lo_de_hoy_primero(app, db_clean):
    """Sebastián: *"falta la fecha del PQR y filtra mejor, que empiecen desde hoy"*."""
    html = _html_animus()
    i = html.index('async function loadAnimusPqr(')
    cuerpo = html[i:i + 7000]
    assert "<th>Fecha</th>" in cuerpo, 'la lista no muestra la fecha'
    assert "p.creado_en||'').slice(0,10)" in cuerpo
    assert 'descartarPqr(' in html and 'limpiarConsultasPqr(' in html
