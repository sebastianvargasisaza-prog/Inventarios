# -*- coding: utf-8 -*-
"""Las tarjetas de la caja cuentan EFECTIVO, no la plata que entró al banco (4-ago).

Sebastián, mirando el modal de cobro del contraentrega: *"esto es por si llegan donde ese
cliente que pide contraentrega y dice 'ya decidí transferir, pagué de otra forma', entonces no
le entrega efectivo al mensajero · de aquí el único que registra ingreso de plata es si eligen
efectivo"*.

El modal ya estaba bien (avisa, pide el número de la transferencia y la foto del comprobante) y
los sitios que DECIDEN usan `caja_saldo()`, que excluye esos medios. Lo que estaba mal eran los
KPI de la pantalla: armaban su propio SUM sin mirar el medio, así que la gaveta mostraba un
saldo inflado con la plata del banco -- y ese hero alimenta `window._CAJA_SALDO`, el número
contra el que se valida un pago (M1 · un solo resolver · M5 · lo mostrado es lo que decide).
"""
from .conftest import TEST_PASSWORD, csrf_headers

MARCA = 'ZZKPIEF'


def _cli(app, quien='sebastian'):
    c = app.test_client()
    r = c.post("/login", data={"username": quien, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pude loguear a %s' % quien
    return c


def _limpiar(app):
    """Limpia ANTES de sembrar (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM animus_caja_menor")
        conn.commit()


def _mov(app, tipo, monto, metodo, fecha=None):
    from database import get_db
    from blueprints.animus import _hoy_col
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO animus_caja_menor (fecha, tipo, concepto, monto, metodo, "
                    "registrado_por) VALUES (?,?,?,?,?, 'test')",
                    (fecha or _hoy_col().isoformat(), tipo, MARCA + ' ' + metodo, monto, metodo))
        conn.commit()


def _kpis(app):
    return (_cli(app).get('/api/animus/caja').get_json() or {}).get('kpis') or {}


def test_una_transferencia_NO_suma_al_efectivo_de_la_gaveta(app, db_clean):
    """El cliente transfirió: al mensajero no le dieron un peso. Si eso suma al saldo, el
    arqueo no cuadra nunca y el sistema promete billetes que nadie va a encontrar."""
    _limpiar(app)
    _mov(app, 'ingreso', 100000, 'efectivo')
    _mov(app, 'ingreso', 250000, 'transferencia')
    _mov(app, 'ingreso',  40000, 'nequi')
    _mov(app, 'ingreso',  60000, 'tarjeta_credito')

    k = _kpis(app)
    assert k['saldo_total'] == 100000, 'el saldo cuenta plata que está en el banco'
    assert k['ingreso_hoy'] == 100000, '"entró hoy" cuenta lo que no entró a la gaveta'
    assert k['ingreso_mes'] == 100000


def test_lo_que_entro_al_BANCO_se_dice_no_se_esconde(app, db_clean):
    """Con dientes al revés: esa plata entró de verdad · un total que la deja afuera sin
    nombrarla se lee como un faltante (M124)."""
    _limpiar(app)
    _mov(app, 'ingreso', 100000, 'efectivo')
    _mov(app, 'ingreso', 250000, 'transferencia')
    _mov(app, 'ingreso',  40000, 'nequi')

    k = _kpis(app)
    assert k['ingreso_hoy_banco'] == 290000, 'no dice cuánto entró al banco'
    assert k['ingreso_mes_banco'] == 290000


def test_TODO_egreso_descuenta_aunque_sea_una_consignacion(app, db_clean):
    """El medio descarta un INGRESO que no pasó por la gaveta. En un egreso el medio dice CÓMO
    salió la plata, no si salió: consignar es exactamente sacar los billetes."""
    _limpiar(app)
    _mov(app, 'ingreso', 500000, 'efectivo')
    _mov(app, 'egreso',  200000, 'consignacion')

    k = _kpis(app)
    assert k['saldo_total'] == 300000, 'la consignación no descontó el efectivo'
    assert k['egreso_hoy'] == 200000


def test_el_saldo_del_hero_ES_el_que_usa_el_servidor_para_decidir(app, db_clean):
    """Dos SUM para el mismo hecho divergen en silencio (M1): el número que se muestra tiene
    que ser el mismo con el que se autoriza un pago."""
    from database import get_db
    from blueprints.animus import caja_saldo
    _limpiar(app)
    _mov(app, 'ingreso', 320000, 'efectivo')
    _mov(app, 'ingreso', 175000, 'daviplata')
    _mov(app, 'egreso',   90000, 'efectivo')

    k = _kpis(app)
    with app.app_context():
        canonico = caja_saldo(get_db())
    assert k['saldo_total'] == round(canonico, 2), \
        'la pantalla muestra un saldo y el servidor decide con otro'


def test_un_movimiento_ANULADO_no_cuenta_en_ninguno(app, db_clean):
    """Anular conserva la fila a la vista (ese es el punto de no borrar) pero no suma."""
    from database import get_db
    _limpiar(app)
    _mov(app, 'ingreso', 400000, 'efectivo')
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("UPDATE animus_caja_menor SET anulado=1 WHERE monto=400000")
        conn.commit()
    k = _kpis(app)
    assert k['saldo_total'] == 0 and k['ingreso_hoy'] == 0


def test_una_fila_VIEJA_sin_medio_sigue_contando_como_efectivo(app, db_clean):
    """Las filas anteriores al campo `metodo` eran efectivo: tratarlas como banco borraría
    plata real del saldo."""
    from database import get_db
    from blueprints.animus import _hoy_col
    _limpiar(app)
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO animus_caja_menor (fecha, tipo, concepto, monto, metodo, "
                    "registrado_por) VALUES (?, 'ingreso', ?, 77000, NULL, 'test')",
                    (_hoy_col().isoformat(), MARCA + ' legacy'))
        cur.execute("INSERT INTO animus_caja_menor (fecha, tipo, concepto, monto, metodo, "
                    "registrado_por) VALUES (?, 'ingreso', ?, 13000, '  ', 'test')",
                    (_hoy_col().isoformat(), MARCA + ' vacio'))
        conn.commit()
    k = _kpis(app)
    assert k['saldo_total'] == 90000, 'una fila sin medio dejó de contar como efectivo'


def test_el_modal_de_cobro_pide_comprobante_cuando_NO_es_efectivo():
    """Lo que Sebastián dio por bueno queda fijado: al elegir otro medio aparece el aviso, el
    número de la transferencia y la FOTO · con tarjeta el rótulo cambia y no la exige."""
    import io
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = io.open(os.path.join(raiz, 'api/templates_py/animus_html.py'),
                  encoding='utf-8').read()
    assert "id=\"cob-no-efectivo\"" in src
    assert 'entra al <b>banco</b>, no a la gaveta' in src
    assert 'id="cob-foto"' in src and 'capture="environment"' in src
    assert 'subirComprobanteCobro()' in src
    # el bloque se muestra SOLO cuando el medio no es efectivo
    assert "(m === 'efectivo') ? 'none' : ''" in src
