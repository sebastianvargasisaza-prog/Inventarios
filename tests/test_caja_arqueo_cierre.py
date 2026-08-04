# -*- coding: utf-8 -*-
"""Lo que vuelve CONFIABLE a la caja menor (3-ago).

Sebastián: *"piensa qué más falta en esta caja menor: trazabilidad, unión con tesorería,
trazabilidades y cosas que debería tener para que sea premium y confiable"*.

El hueco de fondo era éste: **el saldo era una SUMA de movimientos que nadie había contado
nunca contra la gaveta**. Si faltaba plata, el sistema seguía diciendo su número tan tranquilo.
Eso es un libro, no un control.

Las cuatro piezas y la regla que fija cada una:

1. ARQUEO · el efectivo FÍSICO es la verdad (igual que el conteo cíclico contra el kardex).
   Se cuenta, la diferencia exige motivo, y los libros se ajustan a la realidad.
2. TESORERÍA · la plata dejaba de verse al salir: consignar la sacaba de la caja sin meterla
   en ningún lado, y un gasto de caja no llegaba al flujo de egresos.
3. TRAZABILIDAD · dado un recibo, todo el recorrido en una vista. Lo que cuesta reconstruir
   no se audita nunca.
4. CIERRE · un período cerrado no se toca; corregir es registrar algo nuevo.
"""
from .conftest import TEST_PASSWORD, csrf_headers

MARCA = 'ZZARQ'


def _cli(app, quien='sebastian'):
    c = app.test_client()
    r = c.post("/login", data={"username": quien, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pude loguear a %s' % quien
    return c


def _limpiar(app):
    """Limpia ANTES de sembrar (M103): la BD de tests es compartida."""
    from database import get_db
    with app.app_context():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM animus_caja_menor WHERE concepto LIKE ?", ('%' + MARCA + '%',))
        cur.execute("DELETE FROM animus_caja_menor WHERE concepto LIKE ?",
                    ('%Ajuste por arqueo%',))
        cur.execute("DELETE FROM caja_arqueos")
        cur.execute("DELETE FROM caja_cierres")
        cur.execute("DELETE FROM flujo_egresos WHERE fuente='caja_menor'")
        cur.execute("DELETE FROM flujo_ingresos WHERE fuente='caja_menor'")
        conn.commit()


def _saldo(app):
    from database import get_db
    with app.app_context():
        conn = get_db()
        return float(conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN tipo='ingreso' THEN monto ELSE -monto END),0) "
            "FROM animus_caja_menor WHERE COALESCE(anulado,0)=0").fetchone()[0] or 0)


_SEMILLA = [0]


def _efectivo(app, monto, fecha=None):
    from database import get_db
    from tz_colombia import hoy_colombia
    _SEMILLA[0] += 1
    with app.app_context():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO animus_caja_menor (fecha, tipo, concepto, monto, "
                    "registrado_por, recibo_numero) VALUES (?,'ingreso',?,?,?,?)",
                    (fecha or hoy_colombia().isoformat(), MARCA + ' semilla', monto, 'test',
                     'RC-ZZ-%04d' % _SEMILLA[0]))
        conn.commit()


def _descerrar(app):
    """Saca el cierre. Un periodo cerrado bloquea a TODO el que venga despues."""
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.cursor().execute("DELETE FROM caja_cierres")
        conn.commit()


def _tope_alto(app):
    from database import get_db
    with app.app_context():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO app_settings (clave,valor) "
                    "VALUES ('caja_tope_sin_autorizar','9999999') "
                    "ON CONFLICT (clave) DO UPDATE SET valor=excluded.valor")
        conn.commit()


# ── ARQUEO ───────────────────────────────────────────────────────────────────

def test_un_arqueo_que_CUADRA_no_mueve_nada(app, db_clean):
    _limpiar(app)
    _efectivo(app, 2000000)
    c = _cli(app)
    saldo = _saldo(app)
    r = c.post('/api/caja/arqueos', json={'conteo_fisico': saldo, 'observaciones': MARCA},
               headers=csrf_headers())
    assert r.status_code == 201, r.data[:300]
    d = r.get_json()
    assert d['diferencia'] == 0 and d['ajuste_mov_id'] is None
    assert _saldo(app) == saldo, 'un arqueo que cuadra no puede mover el saldo'


def test_si_FALTA_plata_se_registra_y_los_libros_se_ajustan_a_la_realidad(app, db_clean):
    """El efectivo físico es la verdad. Si el sistema dice más de lo que hay, el que está mal
    es el sistema -- y dejarlo así sería seguir mostrando plata que no existe."""
    _limpiar(app)
    _efectivo(app, 2000000)
    c = _cli(app)
    saldo = _saldo(app)
    faltan = 25000
    r = c.post('/api/caja/arqueos',
               json={'conteo_fisico': saldo - faltan, 'motivo': MARCA + ' falto plata',
                     'observaciones': MARCA}, headers=csrf_headers())
    assert r.status_code == 201, r.data[:300]
    d = r.get_json()
    assert d['diferencia'] == -faltan
    assert d['ajuste_mov_id'], 'no se registró el faltante'
    assert _saldo(app) == saldo - faltan, 'el saldo no quedó igual al efectivo contado'


def test_si_SOBRA_plata_tambien(app, db_clean):
    _limpiar(app)
    _efectivo(app, 2000000)
    c = _cli(app)
    saldo = _saldo(app)
    r = c.post('/api/caja/arqueos',
               json={'conteo_fisico': saldo + 9000, 'motivo': MARCA + ' sobro',
                     'observaciones': MARCA}, headers=csrf_headers())
    assert r.status_code == 201, r.data[:300]
    assert _saldo(app) == saldo + 9000


def test_una_diferencia_SIN_motivo_no_pasa(app, db_clean):
    """Es el momento en que se sabe qué pasó · un mes después ya nadie lo reconstruye."""
    _limpiar(app)
    _efectivo(app, 2000000)
    c = _cli(app)
    r = c.post('/api/caja/arqueos', json={'conteo_fisico': _saldo(app) - 50000},
               headers=csrf_headers())
    assert r.status_code == 400, r.data[:200]


def test_el_ajuste_del_arqueo_NO_se_cuenta_como_gasto(app, db_clean):
    """Un faltante de caja no es un gasto del mes: si se mezclara, el reporte diría que se
    gastó una plata que en realidad se perdió o se contó mal."""
    _limpiar(app)
    _efectivo(app, 2000000)
    c = _cli(app)
    c.post('/api/caja/arqueos', json={'conteo_fisico': _saldo(app) - 12000,
                                      'motivo': MARCA + ' x', 'observaciones': MARCA},
           headers=csrf_headers())
    from database import get_db
    with app.app_context():
        conn = get_db()
        sub = conn.execute("SELECT subtipo FROM animus_caja_menor WHERE concepto LIKE ? "
                           "ORDER BY id DESC LIMIT 1", ('%Ajuste por arqueo%',)).fetchone()[0]
    assert sub == 'ajuste_arqueo'


def test_el_arqueo_dice_hace_cuanto_no_se_cuenta(app, db_clean):
    """Una caja que lleva semanas sin arquear tiene un saldo que nadie verificó, y eso hay que
    poder verlo sin abrir el historial."""
    _limpiar(app)
    d = _cli(app).get('/api/caja/arqueos').get_json()
    assert 'dias_sin_arqueo' in d and 'saldo_actual' in d


# ── CIERRE ───────────────────────────────────────────────────────────────────

def test_cerrar_sin_haber_contado_la_plata_avisa(app, db_clean):
    """Cerrar sin arqueo es sellar un número que nadie verificó."""
    _limpiar(app)
    from tz_colombia import hoy_colombia
    r = _cli(app).post('/api/caja/cierres', json={'hasta_fecha': hoy_colombia().isoformat()},
                       headers=csrf_headers())
    assert r.status_code == 409, r.data[:250]
    assert r.get_json().get('puede_forzar') is True


def test_lo_CERRADO_no_se_puede_tocar(app, db_clean):
    """Un cierre que se edita hacia atrás no es un cierre: el saldo con el que se cerró dejaría
    de reconstruirse."""
    _limpiar(app)
    _efectivo(app, 900000)
    from tz_colombia import hoy_colombia
    c = _cli(app)
    hoy = hoy_colombia().isoformat()
    c.post('/api/caja/arqueos', json={'conteo_fisico': _saldo(app), 'observaciones': MARCA},
           headers=csrf_headers())
    assert c.post('/api/caja/cierres', json={'hasta_fecha': hoy},
                  headers=csrf_headers()).status_code == 201
    r = c.post('/api/caja/traslado', json={'monto': 1000, 'fecha': hoy},
               headers=csrf_headers())
    _descerrar(app)          # el cierre bloquea a todo el que venga despues
    assert r.status_code == 409, r.data[:250]
    assert r.get_json().get('cerrada_hasta') == hoy


def test_no_se_cierra_dos_veces_el_mismo_periodo(app, db_clean):
    _limpiar(app)
    _efectivo(app, 500000)
    from tz_colombia import hoy_colombia
    c = _cli(app)
    hoy = hoy_colombia().isoformat()
    c.post('/api/caja/arqueos', json={'conteo_fisico': _saldo(app), 'observaciones': MARCA},
           headers=csrf_headers())
    assert c.post('/api/caja/cierres', json={'hasta_fecha': hoy},
                  headers=csrf_headers()).status_code == 201
    r2 = c.post('/api/caja/cierres', json={'hasta_fecha': hoy}, headers=csrf_headers())
    _descerrar(app)          # el cierre bloquea a todo el que venga despues
    assert r2.status_code == 409


# ── TESORERÍA ────────────────────────────────────────────────────────────────

def test_consignar_ENTRA_al_banco_en_tesoreria(app, db_clean):
    """La plata no desaparece: sale de la gaveta y entra al banco. Sin el espejo, Tesorería ve
    una consignación sin origen y la caja una salida sin destino."""
    _limpiar(app)
    _efectivo(app, 3000000)
    r = _cli(app).post('/api/caja/traslado',
                       json={'monto': 800000, 'cuenta': 'Bancolombia 1'},
                       headers=csrf_headers())
    assert r.status_code == 200, r.data[:250]
    recibo = r.get_json()['recibo_numero']
    from database import get_db
    with app.app_context():
        conn = get_db()
        fila = conn.execute("SELECT monto, categoria FROM flujo_ingresos "
                            "WHERE fuente='caja_menor' AND referencia=?", (recibo,)).fetchone()
    assert fila, 'la consignación no llegó a Tesorería'
    assert float(fila[0]) == 800000


def test_el_espejo_a_tesoreria_no_se_duplica(app, db_clean):
    """Es plata: dos filas por el mismo recibo contarían el ingreso dos veces."""
    _limpiar(app)
    _efectivo(app, 3000000)
    c = _cli(app)
    recibo = c.post('/api/caja/traslado', json={'monto': 100000},
                    headers=csrf_headers()).get_json()['recibo_numero']
    from database import get_db
    with app.app_context():
        conn = get_db()
        cur = conn.cursor()
        from blueprints.animus import _tesoreria_espejo
        _tesoreria_espejo(cur, tipo='ingreso', fecha='2026-08-03', concepto='x',
                          monto=100000, empresa='ANIMUS', referencia=recibo,
                          usuario='test', categoria='Traslado de caja')
        conn.commit()
        n = conn.execute("SELECT COUNT(*) FROM flujo_ingresos WHERE referencia=?",
                         (recibo,)).fetchone()[0]
    assert n == 1, 'el espejo se duplicó'


def test_el_periodo_de_tesoreria_sale_de_la_fecha_del_HECHO(app, db_clean):
    """M106: si saliera del reloj, un pago con fecha de la semana pasada caería en el mes en
    curso y el período contable quedaría mal."""
    _limpiar(app)
    _efectivo(app, 2000000)
    r = _cli(app).post('/api/caja/traslado',
                       json={'monto': 50000, 'fecha': '2026-06-15'}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:250]
    from database import get_db
    with app.app_context():
        conn = get_db()
        per = conn.execute("SELECT periodo FROM flujo_ingresos WHERE fuente='caja_menor' "
                           "AND referencia=?", (r.get_json()['recibo_numero'],)).fetchone()[0]
    assert per == '2026-06', per


# ── TRAZABILIDAD ─────────────────────────────────────────────────────────────

def test_un_recibo_cuenta_TODO_su_recorrido(app, db_clean):
    """Los datos estaban, pero repartidos en cinco tablas. Lo que cuesta reconstruir en la
    práctica no se audita nunca."""
    _limpiar(app)
    _efectivo(app, 2000000)
    c = _cli(app)
    recibo = c.post('/api/caja/traslado', json={'monto': 70000, 'cuenta': 'BC'},
                    headers=csrf_headers()).get_json()['recibo_numero']
    r = c.get('/api/caja/trazabilidad/' + recibo)
    assert r.status_code == 200, r.data[:250]
    d = r.get_json()
    assert d['movimiento']['recibo_numero'] == recibo
    assert d['tesoreria'] and d['tesoreria']['monto'] == 70000
    assert isinstance(d['auditoria'], list)


def test_un_recibo_que_no_existe_da_404(app, db_clean):
    r = _cli(app).get('/api/caja/trazabilidad/RC-NO-EXISTE')
    assert r.status_code == 404


# ── SOBRANTE ─────────────────────────────────────────────────────────────────

def test_devolver_el_sobrante_de_un_pago(app, db_clean):
    """Se autorizaron 200.000 y el pago costó 180.000: esos 20.000 vuelven a la gaveta. Sin
    esto el saldo queda por debajo de la realidad y el próximo arqueo reporta un sobrante
    inexplicable."""
    _limpiar(app)
    _efectivo(app, 2000000)
    _tope_alto(app)
    c = _cli(app)
    sid = c.post('/api/caja/solicitudes',
                 json={'concepto': MARCA + ' compra', 'monto': 200000},
                 headers=csrf_headers()).get_json()['id']
    c.post('/api/caja/solicitudes/%d/pagar' % sid, json={}, headers=csrf_headers())
    saldo = _saldo(app)
    r = c.post('/api/caja/solicitudes/%d/sobrante' % sid, json={'monto': 20000},
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:250]
    assert _saldo(app) == saldo + 20000


def test_el_sobrante_no_puede_superar_lo_pagado(app, db_clean):
    """Devolver más de lo que salió no es un sobrante: es meter plata de otro lado."""
    _limpiar(app)
    _efectivo(app, 2000000)
    _tope_alto(app)
    c = _cli(app)
    sid = c.post('/api/caja/solicitudes', json={'concepto': MARCA + ' y', 'monto': 60000},
                 headers=csrf_headers()).get_json()['id']
    c.post('/api/caja/solicitudes/%d/pagar' % sid, json={}, headers=csrf_headers())
    r = c.post('/api/caja/solicitudes/%d/sobrante' % sid, json={'monto': 90000},
               headers=csrf_headers())
    assert r.status_code == 400


# ── REPORTE POR EMPRESA ──────────────────────────────────────────────────────

def test_el_reporte_separa_las_dos_empresas_y_saca_el_traslado_del_gasto(app, db_clean):
    """Una gaveta con plata de dos empresas tiene que poder separarse. Y consignar no es
    gastar: mezclarlos infla los gastos del mes con plata que está en el banco."""
    _limpiar(app)
    _efectivo(app, 4000000)
    c = _cli(app)
    c.post('/api/caja/traslado', json={'monto': 300000, 'empresa': 'ESPAGIRIA'},
           headers=csrf_headers())
    d = c.get('/api/caja/reporte').get_json()
    assert d['ok'] and 'por_empresa' in d
    esp = d['por_empresa'].get('ESPAGIRIA')
    assert esp, 'no separa por empresa'
    assert esp['traslados'] >= 300000
    assert esp['gastos'] == 0, 'el traslado se está contando como gasto'


def test_el_saldo_lo_calcula_UN_solo_helper():
    """Cinco sitios preguntan cuánta plata hay (pagar, consignar, listar, arquear, cerrar). Si
    cada uno arma su propio SUM, divergen en silencio (M1)."""
    import inspect
    from blueprints import animus
    src = inspect.getsource(animus)
    assert 'def caja_saldo(' in src
    assert src.count("WHEN tipo='ingreso' THEN monto ELSE -monto END") <= 4, \
        'hay demasiadas copias del calculo del saldo · usar caja_saldo()'


# ── la PANTALLA (M94: un endpoint sin pantalla no lo usa nadie) ───────────────

def _html_caja():
    import ast as _ast, io as _io, os as _os
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    src = _io.open(_os.path.join(raiz, 'api', 'templates_py', 'animus_html.py'),
                   encoding='utf-8').read()
    for n in _ast.walk(_ast.parse(src)):
        if (isinstance(n, _ast.Assign) and isinstance(n.value, _ast.Constant)
                and isinstance(n.value.value, str) and len(n.value.value) > 5000):
            return n.value.value
    raise AssertionError('no encontre ANIMUS_HTML')


def test_la_pantalla_deja_arquear_y_ver_el_recorrido():
    html = _html_caja()
    assert 'abrirArqueo' in html and 'id="modal-arqueo"' in html, 'no se puede arquear'
    assert 'function guardarArqueo' in html, 'el arqueo no guarda'
    assert 'verTraza' in html and 'id="modal-traza"' in html, 'no se puede ver el recorrido'
    # el recibo es la puerta: es el dato que la persona tiene en la mano al preguntar
    assert 'verTraza(&quot;' in html, 'el recibo de la tabla no abre su recorrido'


def test_la_pantalla_avisa_cuando_hace_mucho_que_no_se_cuenta():
    """Una caja que lleva semanas sin arquear tiene un saldo que nadie verifico. Si eso no se
    ve solo, no se mira nunca."""
    html = _html_caja()
    assert 'cargarAvisoArqueo' in html and 'id="caja-aviso-arqueo"' in html
    assert 'nunca se ha arqueado' in html, 'no distingue "nunca contada" de "hace N dias"'


def test_la_diferencia_se_ve_MIENTRAS_se_escribe():
    """Si hay que explicarla, que se sepa antes de darle a guardar y no despues de un error."""
    html = _html_caja()
    assert 'function arqAvisarDif' in html
    assert 'Faltan' in html and 'Sobran' in html


# ── anular deshace TODO lo que el movimiento provoco (M134) ───────────────────

def test_anular_un_pago_devuelve_la_solicitud_a_autorizada(app, db_clean):
    """Anular sin deshacer lo que provoco deja el sistema contandose historias distintas: la
    solicitud diciendo "pagada" con la plata de vuelta en la caja."""
    _limpiar(app)
    _efectivo(app, 2000000)
    _tope_alto(app)
    c = _cli(app)
    sid = c.post('/api/caja/solicitudes', json={'concepto': MARCA + ' rev', 'monto': 90000},
                 headers=csrf_headers()).get_json()['id']
    mov = c.post('/api/caja/solicitudes/%d/pagar' % sid, json={},
                 headers=csrf_headers()).get_json()['caja_mov_id']
    saldo = _saldo(app)
    r = c.delete('/api/animus/caja/%d' % mov, json={'motivo': MARCA + ' me equivoque'},
                 headers=csrf_headers())
    assert r.status_code == 200, r.data[:250]
    assert _saldo(app) == saldo + 90000, 'la plata no volvio a la caja'
    from database import get_db
    with app.app_context():
        conn = get_db()
        est = conn.execute("SELECT estado, caja_mov_id FROM caja_solicitudes_pago WHERE id=?",
                           (sid,)).fetchone()
    assert est[0] == 'autorizada', 'la solicitud quedo "pagada" con la plata devuelta'
    assert est[1] is None


def test_anular_tambien_borra_el_espejo_de_tesoreria(app, db_clean):
    """Si no, Tesoreria queda con un gasto que ya no existe."""
    _limpiar(app)
    _efectivo(app, 2000000)
    c = _cli(app)
    d = c.post('/api/caja/traslado', json={'monto': 60000}, headers=csrf_headers()).get_json()
    from database import get_db
    with app.app_context():
        conn = get_db()
        assert conn.execute("SELECT COUNT(*) FROM flujo_ingresos WHERE referencia=?",
                            (d['recibo_numero'],)).fetchone()[0] == 1
    c.delete('/api/animus/caja/%d' % d['caja_mov_id'], json={'motivo': MARCA + ' x'},
             headers=csrf_headers())
    with app.app_context():
        conn = get_db()
        n = conn.execute("SELECT COUNT(*) FROM flujo_ingresos WHERE referencia=?",
                         (d['recibo_numero'],)).fetchone()[0]
    assert n == 0, 'Tesoreria quedo con un movimiento que ya no existe'


def test_no_se_anula_dentro_de_un_periodo_cerrado(app, db_clean):
    _limpiar(app)
    _efectivo(app, 2000000)
    from tz_colombia import hoy_colombia
    c = _cli(app)
    hoy = hoy_colombia().isoformat()
    mov = c.post('/api/caja/traslado', json={'monto': 5000, 'fecha': hoy},
                 headers=csrf_headers()).get_json()['caja_mov_id']
    c.post('/api/caja/arqueos', json={'conteo_fisico': _saldo(app), 'observaciones': MARCA},
           headers=csrf_headers())
    c.post('/api/caja/cierres', json={'hasta_fecha': hoy}, headers=csrf_headers())
    r = c.delete('/api/animus/caja/%d' % mov, json={'motivo': MARCA + ' tarde'},
                 headers=csrf_headers())
    _descerrar(app)          # el cierre bloquea a todo el que venga despues
    assert r.status_code == 409, r.data[:250]


# ── las sub-pestanas y el boton de cierre ────────────────────────────────────

def test_caja_menor_tiene_DOS_subpestanas():
    """Sebastian: "deberia ir caja menor en dos subpestanas". Dos trabajos distintos -cobrar lo
    que esta en la calle y manejar la plata que hay- obligaban a scrollear 46 filas."""
    html = _html_caja()
    for req in ('data-sub="cod"', 'data-sub="mov"', 'id="sub-cod"', 'id="sub-mov"',
                'function subTab'):
        assert req in html, 'falta %s' % req
    # conmutador PROPIO: reusar switchTab apagaria todos los .tab-panel
    import re as _re
    m = _re.search(r'function subTab\(name\)\s*\{(.*?)\n\}', html, _re.S)
    assert m and 'sub-panel' in m.group(1), 'el conmutador no maneja los sub-paneles'
    assert 'tab-panel' not in m.group(1), 'reusa el conmutador de las pestanas · pantalla en blanco'


def test_el_saldo_esta_ARRIBA_de_las_dos_subpestanas():
    """Cobrar una contraentrega ALIMENTA la caja: si el saldo vive dentro de una sola pestana,
    se pierde de vista que una cosa lleva a la otra."""
    html = _html_caja()
    assert html.index('id="caja-kpis"') < html.index('class="subtabs"')


def test_el_cierre_tiene_boton():
    """Estaba en el backend y sin pantalla: una feature que en la practica no existe (M94)."""
    html = _html_caja()
    assert 'cerrarPeriodo' in html and '/api/caja/cierres' in html
