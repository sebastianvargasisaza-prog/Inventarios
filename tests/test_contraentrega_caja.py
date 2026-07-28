"""La plata de los envíos contraentrega, controlada pedido por pedido (27-jul).

Sebastián: *"caja menor es toda la plata que llega por envíos contraentrega · en Shopify les
ponen contraentrega · saber pedido tal, tanto valor, que marquen que sí ingresó esa plata, y
saber en tiempo real cuánto ingresa"*. Y después, precisando dónde está la marca: *"en Shopify
escriben en el pedido una nota cuando lo crean y escriben contraentrega, también se pueden crear
como etiquetas"*.

Dos cosas que definen el diseño y que estos tests fijan:

1. **La marca la escribe una persona a mano**, así que no viene en un campo estructurado. Se
   miran las tres señales (nota, etiqueta, medio de pago) y el patrón es configurable sin
   desplegar. Depender de una sola pierde pedidos en silencio.
2. **El estado del cobro NO puede vivir en `animus_shopify_orders`**: esa tabla la reescribe el
   sync en cada corrida, así que un "ya entró la plata" guardado ahí se borraría solo (M20). Va
   en su propia tabla, anclada por `shopify_id`.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PREFIJO = 'ZZCOD'


def _admin(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar(app):
    """Limpia ANTES de sembrar (M103): la BD de tests es compartida y en PG persiste entre
    corridas, así que el UNIQUE de `shopify_id` haría fallar la segunda."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM animus_cod_cobros WHERE shopify_id LIKE ?", (PREFIJO + '%',))
        cur.execute("DELETE FROM animus_caja_menor WHERE referencia LIKE ?", (PREFIJO + '%',))
        cur.execute("DELETE FROM animus_shopify_orders WHERE shopify_id LIKE ?", (PREFIJO + '%',))
        conn.commit()


def _sembrar(app, sufijo, *, total=100000, nota='', tags='', gateway='', fecha=None, estado=''):
    from database import get_db
    from tz_colombia import hoy_colombia
    fecha = fecha or hoy_colombia().isoformat()
    sid = PREFIJO + sufijo
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute(
            "INSERT INTO animus_shopify_orders (shopify_id, nombre, total, moneda, estado, "
            "estado_pago, creado_en, nota, tags, gateway) VALUES (?,?,?,'COP',?,?,?,?,?,?)",
            (sid, '#' + sufijo, total, estado, 'pending', fecha, nota, tags, gateway))
        conn.commit()
    return sid


# ── el detector ──────────────────────────────────────────────────────────────

def test_detecta_la_marca_en_la_nota_la_etiqueta_o_el_medio_de_pago(app):
    """Las tres señales, porque quien crea el pedido usa la que tiene a mano."""
    from blueprints.animus import es_contraentrega
    assert es_contraentrega('CONTRAENTREGA', '', '')[0]
    assert es_contraentrega('Entregar y cobrar contra entrega', '', '')[0]
    assert es_contraentrega('', 'vip, contraentrega', '')[0]
    assert es_contraentrega('', '', 'Cash on Delivery (COD)')[0]
    assert es_contraentrega('pago al recibir', '', '')[0]
    # y dice DÓNDE matcheó · sin eso nadie puede verificar por qué un pedido entró a la caja
    assert es_contraentrega('contraentrega', '', '')[1] == 'nota'
    assert es_contraentrega('', 'contraentrega', '')[1] == 'etiqueta'
    assert es_contraentrega('', '', 'COD')[1] == 'medio de pago'


def test_no_marca_un_pedido_normal(app):
    """Con dientes: si el patrón se afloja y matchea cualquier cosa, la caja se llena de pedidos
    que ya se pagaron por la pasarela y el saldo deja de significar algo."""
    from blueprints.animus import es_contraentrega
    for nota in ('', 'entregar en portería', 'cliente pidió factura',
                 'codigo de descuento aplicado', 'envio gratis'):
        assert not es_contraentrega(nota, '', 'shopify_payments')[0], nota


def test_la_marca_no_depende_de_tildes_ni_mayusculas(app):
    from blueprints.animus import es_contraentrega
    for txt in ('Contraentrega', 'CONTRA-ENTREGA', 'contra  entrega', 'Contra Entrega'):
        assert es_contraentrega(txt, '', '')[0], txt


# ── el flujo de cobro ────────────────────────────────────────────────────────

def test_el_pedido_aparece_pendiente_y_al_cobrarlo_entra_a_caja_con_recibo(app, db_clean):
    """De punta a punta: se ve lo que falta cobrar, se marca, y la plata queda en caja con su
    recibo numerado (el mismo correlativo del ingreso manual, no una serie aparte)."""
    _limpiar(app)
    sid = _sembrar(app, 'A1', total=150000, nota='CONTRAENTREGA - llamar antes')
    c = _admin(app)

    d = c.get('/api/animus/contraentrega').get_json()
    mio = [p for p in d['pedidos'] if p['shopify_id'] == sid]
    assert mio, 'el pedido contraentrega no salió en la lista'
    assert mio[0]['cobrado'] is False and mio[0]['valor_esperado'] == 150000
    assert mio[0]['detectado_por'] == 'nota'

    r = c.post('/api/animus/contraentrega/%s/cobrar' % sid, json={}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    body = r.get_json()
    assert body['recibo_numero'].startswith('RC-') and body['estado'] == 'cobrado'

    # quedó en caja, como ingreso, con ese recibo
    caja = c.get('/api/animus/caja').get_json()
    mov = [m for m in caja['movimientos'] if m['referencia'] == sid]
    assert mov, 'el cobro no llegó a caja'
    assert mov[0]['tipo'] == 'ingreso' and float(mov[0]['monto']) == 150000
    assert mov[0]['recibo_numero'] == body['recibo_numero']


def test_no_se_puede_cobrar_dos_veces_el_mismo_pedido(app, db_clean):
    """Es plata: el UNIQUE de shopify_id es lo que lo impide de verdad (el chequeo previo no
    sirve con 3 workers)."""
    _limpiar(app)
    sid = _sembrar(app, 'A2', total=50000, tags='contraentrega')
    c = _admin(app)
    assert c.post('/api/animus/contraentrega/%s/cobrar' % sid, json={},
                  headers=csrf_headers()).status_code == 200
    assert c.post('/api/animus/contraentrega/%s/cobrar' % sid, json={},
                  headers=csrf_headers()).status_code == 409
    conn = sqlite3.connect(os.environ["DB_PATH"])
    n = conn.execute("SELECT COUNT(*) FROM animus_caja_menor WHERE referencia=?", (sid,)).fetchone()[0]
    conn.close()
    assert n == 1, 'el pedido entró dos veces a caja'


def test_un_pedido_que_no_es_contraentrega_no_entra_a_esta_caja(app, db_clean):
    """Si entrara, sumaría plata que ya cobró la pasarela y el saldo dejaría de reflejar la
    realidad."""
    _limpiar(app)
    sid = _sembrar(app, 'A3', total=90000, nota='entregar en la portería')
    c = _admin(app)
    r = c.post('/api/animus/contraentrega/%s/cobrar' % sid, json={}, headers=csrf_headers())
    assert r.status_code == 409, r.data[:200]


def test_recibir_menos_de_lo_esperado_exige_explicacion_y_queda_como_descuadre(app, db_clean):
    """El descuadre es el dato que Sebastián quiere ver ('saber que sí estamos teniendo ese
    dinero'). Sin motivo obligatorio, después nadie puede reconstruir qué pasó."""
    _limpiar(app)
    sid = _sembrar(app, 'A4', total=100000, nota='contraentrega')
    c = _admin(app)
    r = c.post('/api/animus/contraentrega/%s/cobrar' % sid,
               json={'valor_recibido': 80000}, headers=csrf_headers())
    assert r.status_code == 400, 'dejó registrar un faltante sin explicarlo'

    r = c.post('/api/animus/contraentrega/%s/cobrar' % sid,
               json={'valor_recibido': 80000, 'observaciones': 'el mensajero entregó de menos'},
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert r.get_json()['estado'] == 'descuadre' and r.get_json()['diferencia'] == -20000

    k = c.get('/api/animus/contraentrega').get_json()['kpis']
    assert k['n_descuadres'] >= 1 and k['descuadre'] <= -20000
    # y en caja entró lo que REALMENTE se recibió, no lo que decía el pedido
    caja = c.get('/api/animus/caja').get_json()
    mov = [m for m in caja['movimientos'] if m['referencia'] == sid]
    assert float(mov[0]['monto']) == 80000


def test_los_kpis_separan_lo_que_falta_cobrar_de_lo_que_ya_entro(app, db_clean):
    """'Cuánto ingresa en tiempo real' y 'cuánto está todavía en la calle' son dos números
    distintos y no se pueden mezclar (M6: físico y en-camino, separados)."""
    _limpiar(app)
    _sembrar(app, 'B1', total=10000, nota='contraentrega')
    _sembrar(app, 'B2', total=20000, nota='contraentrega')
    sid3 = _sembrar(app, 'B3', total=30000, nota='contraentrega')
    c = _admin(app)
    k0 = c.get('/api/animus/contraentrega').get_json()['kpis']
    assert k0['esperado_pendiente'] >= 60000 and k0['n_pendientes'] >= 3

    c.post('/api/animus/contraentrega/%s/cobrar' % sid3, json={}, headers=csrf_headers())
    k1 = c.get('/api/animus/contraentrega').get_json()['kpis']
    assert round(k0['esperado_pendiente'] - k1['esperado_pendiente'], 2) == 30000, (
        'cobrar no bajó lo que falta cobrar')
    assert k1['cobrado_hoy'] >= 30000


def test_anular_un_cobro_lo_saca_del_saldo_pero_conserva_el_rastro(app, db_clean):
    _limpiar(app)
    sid = _sembrar(app, 'C1', total=70000, nota='contraentrega')
    c = _admin(app)
    c.post('/api/animus/contraentrega/%s/cobrar' % sid, json={}, headers=csrf_headers())
    saldo_con = c.get('/api/animus/caja').get_json()['kpis']['saldo_total']

    r = c.post('/api/animus/contraentrega/%s/anular' % sid,
               json={'motivo': 'lo marqué en el pedido equivocado'}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    saldo_sin = c.get('/api/animus/caja').get_json()['kpis']['saldo_total']
    assert round(saldo_con - saldo_sin, 2) == 70000, 'anular no sacó la plata del saldo'

    conn = sqlite3.connect(os.environ["DB_PATH"])
    fila = conn.execute("SELECT estado FROM animus_cod_cobros WHERE shopify_id=?", (sid,)).fetchone()
    mov = conn.execute("SELECT anulado FROM animus_caja_menor WHERE referencia=?", (sid,)).fetchone()
    conn.close()
    assert fila and fila[0] == 'anulado', 'el cobro se borró en vez de anularse'
    assert mov and int(mov[0]) == 1, 'el recibo de caja quedó vivo'
    # y el pedido vuelve a estar cobrable
    d = c.get('/api/animus/contraentrega').get_json()
    assert any(p['shopify_id'] == sid and not p['cobrado'] for p in d['pedidos'])


# ── la trampa que había debajo ───────────────────────────────────────────────

def test_ningun_sync_de_shopify_borra_lo_que_escribe_otro(app):
    """LA razón por la que esto casi no funciona.

    Los tres sincronizadores de `animus_shopify_orders` usaban `INSERT OR REPLACE` listando
    columnas DISTINTAS, y esa sentencia devuelve al default toda columna que no listes. El sync
    de marketing borraba `tags` (donde puede vivir la marca de contraentrega) y los otros dos
    borraban los descuentos y `flujo_synced`. Ganaba el que corriera último, así que la marca se
    perdía sola y sin síntoma.

    Con `ON CONFLICT ... DO UPDATE` cada sync toca sólo lo suyo. Este test lo fija leyendo el
    código, porque reproducir los tres crons en un test costaría más de lo que protege.
    """
    import io
    import re
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    culpables = []
    for rel in ('api/shopify_client.py', 'api/blueprints/marketing.py',
                'api/blueprints/auto_plan_jobs.py'):
        s = io.open(os.path.join(raiz, rel), encoding='utf-8').read()
        for m in re.finditer(r'INSERT\s+OR\s+REPLACE\s+INTO\s+animus_shopify_orders', s, re.I):
            culpables.append('%s:%d' % (rel, s[:m.start()].count('\n') + 1))
    assert not culpables, (
        'estos sync volvieron a INSERT OR REPLACE sobre animus_shopify_orders: %s. Esa sentencia '
        'resetea toda columna que no listes, y como los tres listan columnas distintas se borran '
        'la marca de contraentrega y los descuentos entre ellos. Usá '
        'ON CONFLICT(shopify_id) DO UPDATE SET <solo tus columnas>.' % ', '.join(culpables))


def test_el_estado_del_cobro_no_vive_en_la_tabla_que_reescribe_el_sync(app):
    """Si `cobrado` viviera en `animus_shopify_orders`, el próximo sync lo borraría y la plata
    ya cobrada volvería a aparecer como pendiente."""
    from database import get_db
    with app.app_context():
        cols = [r[1] for r in get_db().execute("PRAGMA table_info(animus_shopify_orders)")] \
            if os.environ.get('DB_PATH') else []
    prohibidas = {'cobrado', 'cobrado_por', 'cobrado_at', 'valor_recibido'}
    assert not (set(cols) & prohibidas), (
        'el estado del cobro se metió en la tabla que el sync reescribe: %s'
        % (set(cols) & prohibidas))


def test_la_pantalla_de_animus_tiene_la_pestana_y_carga(app, db_clean):
    """Un endpoint sin pantalla es un campo que en la práctica nadie llena (fue exactamente lo que
    pasó con la densidad del granel). Si alguien quita la pestaña, esto lo caza."""
    c = _admin(app)
    r = c.get('/animus')
    assert r.status_code == 200, r.status_code
    html = r.data.decode('utf-8', 'replace')
    assert 'data-tab="cod"' in html, 'desapareció la pestaña de Contraentrega'
    assert 'loadCod' in html and 'codCobrar' in html, 'la pestaña quedó sin su carga o sin el botón'
    assert "if (name === 'cod') loadCod();" in html, 'la pestaña no está enrutada · abriría vacía'


# ═══════════════════════════════════════════════════════════════════════════════
# PLATA VIEJA EN LA CALLE (28-jul)
# Un contraentrega normal se cobra en dias. A las tres semanas, o la transportadora ya
# consigno y nadie lo registro, o esa plata no vuelve -- en los dos casos hay que ir a
# buscarla, y mezclada en el total "pendiente" no se ve.
# ═══════════════════════════════════════════════════════════════════════════════

def test_un_contraentrega_viejo_se_separa_del_pendiente_normal(app, db_clean):
    from database import get_db
    from datetime import date, timedelta
    viejo = (date.today() - timedelta(days=40)).isoformat()
    nuevo = date.today().isoformat()
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        for sid in ('ZZ-COD-VIEJO', 'ZZ-COD-NUEVO'):
            cu.execute("DELETE FROM animus_cod_cobros WHERE shopify_id=?", (sid,))
            cu.execute("DELETE FROM animus_shopify_orders WHERE shopify_id=?", (sid,))
        cu.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, creado_en, nota) "
                   "VALUES (?,?,?,?,?)", ('ZZ-COD-VIEJO', '#9001', 150000, viejo + ' 10:00', 'CONTRAENTREGA'))
        cu.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, creado_en, nota) "
                   "VALUES (?,?,?,?,?)", ('ZZ-COD-NUEVO', '#9002', 90000, nuevo + ' 10:00', 'CONTRAENTREGA'))
        conn.commit()

    c = _admin(app)
    js = c.get('/api/animus/contraentrega').get_json()
    k = js['kpis']
    assert k['anejo_21d'] >= 150000, 'el viejo no entró en la plata añeja: %s' % k
    assert k['n_anejos_21d'] >= 1
    # El de hoy NO puede contar como añejo.
    mios = {p['pedido']: p for p in js['pedidos']}
    assert mios['#9001']['dias_en_calle'] >= 21
    assert mios['#9002']['dias_en_calle'] < 21


def test_la_plata_vieja_en_la_calle_llega_al_centro_de_mando(app, db_clean):
    """Igual que el resto: un dato que hay que ir a buscar no avisa."""
    from database import get_db
    from datetime import date, timedelta
    viejo = (date.today() - timedelta(days=50)).isoformat()
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM animus_cod_cobros WHERE shopify_id=?", ('ZZ-COD-CENTRO',))
        cu.execute("DELETE FROM animus_shopify_orders WHERE shopify_id=?", ('ZZ-COD-CENTRO',))
        cu.execute("INSERT INTO animus_shopify_orders (shopify_id, nombre, total, creado_en, nota) "
                   "VALUES (?,?,?,?,?)", ('ZZ-COD-CENTRO', '#9003', 400000, viejo + ' 10:00', 'contraentrega'))
        conn.commit()
    c = _admin(app)
    dec = c.get('/api/centro/decisiones').get_json().get('decisiones') or []
    cod = [d for d in dec if 'Contraentrega' in (d.get('titulo') or '')]
    assert cod, 'la plata vieja en la calle no llega a la cola del CEO'
    assert 'días en la calle' in (cod[0].get('detalle') or '')
    # Grupo PROPIO: esto es plata que ENTRA. Si cayera en 'pagos' se mezclaría con lo que
    # hay que pagar, que es lo opuesto -- y ademas volveria a inundar esa seccion.
    assert cod[0].get('grupo') == 'cobros', cod[0].get('grupo')
