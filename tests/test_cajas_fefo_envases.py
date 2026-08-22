# -*- coding: utf-8 -*-
"""Manejo del inventario de envases POR CAJAS · 21-ago-2026.

Sebastián: *"si agrego 37 cajas, ¿cómo sé que hay 37 y cuántas hay en cada una? ¿allí aplica
FEFO? ¿va diciendo qué caja coger, cuáles usamos, en cuáles quedan alguna cantidad?"* y *"¿si se
daña? ¿si quiero reemplazar solo uno?"*.

La invariante que hace confiable todo esto, y la razón de que el desglose se DERIVE en vez de
declararse: **la suma de los saldos por tanda es exactamente el saldo del código**. Si el
desglose se guardara aparte, divergiría del kardex el día que alguno de los veinte escritores de
`movimientos_mee` se olvide de actualizarlo -- y ahí la pantalla diría una cosa y el descuento
otra (M5/M99).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers, pantalla_servida

_COD = 'MEE-CAJAS-FEFO'


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)


def _limpiar():
    """Limpieza ANTES de sembrar, con código FIJO (M103)."""
    cn = _cn()
    try:
        for (i,) in cn.execute("SELECT id FROM movimientos_mee WHERE mee_codigo=?",
                               (_COD,)).fetchall():
            cn.execute("DELETE FROM mee_cajas_disposicion WHERE mov_id=?", (i,))
        cn.execute("DELETE FROM movimientos_mee WHERE mee_codigo=?", (_COD,))
        cn.execute("DELETE FROM maestro_mee WHERE codigo=?", (_COD,))
        cn.execute("DELETE FROM oc_recepcion_dedup WHERE numero_oc='BAJA-MEE'")
        cn.commit()
    finally:
        cn.close()


def _sembrar_maestro():
    _limpiar()
    cn = _cn()
    try:
        cn.execute("INSERT INTO maestro_mee (codigo,descripcion,categoria,proveedor,estado,"
                   "stock_actual,stock_minimo,unidad) VALUES (?,?,?,?,'Activo',0,0,'und')",
                   (_COD, 'FRASCO VIDRIO CAJAS FEFO', 'Envase', 'HEBEI'))
        cn.commit()
    finally:
        cn.close()


def _tanda(n_cajas, upc, vence='', lote='', estado='VIGENTE', fecha='2026-01-01 08:00'):
    cn = _cn()
    try:
        cur = cn.execute(
            "INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, unidad, lote_ref, "
            "  responsable, fecha, estado, fecha_vencimiento, n_cajas, unidades_por_caja) "
            "VALUES (?,'Entrada',?,'und',?,'test',?,?,?,?,?)",
            (_COD, n_cajas * upc, lote, fecha, estado, vence, n_cajas, upc))
        cn.commit()
        return cur.lastrowid
    finally:
        cn.close()


def _consumir(n, obs='envasado'):
    cn = _cn()
    try:
        cn.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, unidad, "
                   "  responsable, fecha, estado, observaciones) "
                   "VALUES (?,'Salida',?,'und','test','2026-06-01 08:00','VIGENTE',?)",
                   (_COD, n, obs))
        cn.commit()
    finally:
        cn.close()


def _estado(cli):
    r = cli.get('/api/mee/%s/cajas' % _COD)
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert d.get('ok'), d
    return d


# ───────────────────────── la cuenta de las cajas ─────────────────────────

def test_37_cajas_de_200_se_ven_como_37_cajas(app, db_clean):
    """El caso exacto de la pregunta: cuántas hay y cuánto trae cada una."""
    _sembrar_maestro()
    try:
        _tanda(37, 200, vence='2028-01-31', lote='CH-37')
        d = _estado(_login(app))
        assert d['saldo_total'] == 7400, d['saldo_total']
        assert len(d['tandas']) == 1
        t = d['tandas'][0]
        assert t['n_cajas'] == 37 and t['unidades_por_caja'] == 200
        assert t['cajas_completas'] == 37, 'sin tocar nada deberían quedar las 37 enteras'
        assert t['suelto'] == 0 and t['caja_abierta'] == 0
        assert 'caja nueva' in d['instruccion'].lower(), d['instruccion']
    finally:
        _limpiar()


def test_consumir_media_caja_deja_UNA_abierta_y_el_resto_completas(app, db_clean):
    """*"¿en cuáles quedan alguna cantidad?"* -- una sola, la abierta, que es la regla de bodega."""
    _sembrar_maestro()
    try:
        _tanda(37, 200, vence='2028-01-31', lote='CH-37')
        _consumir(450)          # 2 cajas enteras + 50 de la tercera
        d = _estado(_login(app))
        t = d['tandas'][0]
        assert d['saldo_total'] == 6950
        assert t['cajas_completas'] == 34, t
        assert t['suelto'] == 150, 'la caja abierta tiene 200-50: %r' % (t['suelto'],)
        assert t['caja_abierta'] == 3, 'la abierta es la 3ra: %r' % (t['caja_abierta'],)
        assert 'CAJA 3' in d['instruccion'], d['instruccion']
        assert '150' in d['instruccion'], d['instruccion']
    finally:
        _limpiar()


def test_el_desglose_SUMA_exactamente_el_saldo_del_kardex(app, db_clean):
    """La invariante: si el desglose no cuadra con el total, la pantalla y el descuento mienten.

    Se prueba con tres tandas y un consumo que parte la segunda, que es donde una cuenta mal
    hecha se nota.
    """
    _sembrar_maestro()
    try:
        _tanda(10, 100, vence='2027-01-01', lote='A')
        _tanda(5, 100, vence='2027-06-01', lote='B')
        _tanda(3, 50, vence='2028-01-01', lote='C')
        _consumir(1250)         # se lleva A entera (1000) + 250 de B
        d = _estado(_login(app))
        suma = round(sum(t['saldo'] for t in d['tandas']), 2)
        assert suma == d['saldo_total'], \
            'el desglose suma %r y el kardex dice %r' % (suma, d['saldo_total'])
        assert d['saldo_total'] == 1000 + 500 + 150 - 1250
    finally:
        _limpiar()


# ───────────────────────── FEFO entre tandas ─────────────────────────

def test_se_consume_primero_la_que_vence_antes_no_la_que_llego_antes(app, db_clean):
    """FEFO de verdad: la tanda vieja que vence DESPUÉS no se toca primero."""
    _sembrar_maestro()
    try:
        vieja_larga = _tanda(5, 100, vence='2029-12-31', lote='VIEJA', fecha='2026-01-01 08:00')
        nueva_corta = _tanda(5, 100, vence='2026-09-30', lote='NUEVA', fecha='2026-08-01 08:00')
        _consumir(500)
        d = _estado(_login(app))
        por_id = {t['mov_id']: t for t in d['tandas']}
        assert por_id[nueva_corta]['saldo'] == 0, \
            'no consumió primero la que vence antes: %r' % (por_id[nueva_corta],)
        assert por_id[vieja_larga]['saldo'] == 500, por_id[vieja_larga]
        assert d['tomar_de']['lote'] == 'VIEJA'
    finally:
        _limpiar()


def test_la_tanda_SIN_fecha_no_se_consume_primero(app, db_clean):
    """`fecha_vencimiento` es TEXT DEFAULT '': un COALESCE pelado ordena la vacía PRIMERO, que es
    exactamente al revés del FEFO (M263)."""
    _sembrar_maestro()
    try:
        sin_fecha = _tanda(5, 100, vence='', lote='SINFECHA', fecha='2026-01-01 08:00')
        con_fecha = _tanda(5, 100, vence='2026-10-31', lote='CONFECHA', fecha='2026-02-01 08:00')
        _consumir(500)
        d = _estado(_login(app))
        por_id = {t['mov_id']: t for t in d['tandas']}
        assert por_id[con_fecha]['saldo'] == 0, \
            'gastó la que NO vence y dejó la que caduca: %r' % (por_id[con_fecha],)
        assert por_id[sin_fecha]['saldo'] == 500
    finally:
        _limpiar()


def test_la_tanda_en_CUARENTENA_no_se_ofrece_ni_cuenta(app, db_clean):
    """Un envase esperando a Calidad no es stock: ofrecerlo manda a bajar del estante algo que
    producción no puede usar."""
    _sembrar_maestro()
    try:
        _tanda(4, 100, vence='2027-01-01', lote='LIBRE')
        _tanda(9, 100, vence='2026-06-01', lote='CUARENTENA', estado='CUARENTENA')
        d = _estado(_login(app))
        assert d['saldo_total'] == 400, 'la cuarentena entró al stock: %r' % (d['saldo_total'],)
        assert len(d['tandas']) == 1 and d['tandas'][0]['lote'] == 'LIBRE'
        assert len(d['retenidas']) == 1
        assert 'Calidad' in d['retenidas'][0]['motivo']
        assert d['tomar_de']['lote'] == 'LIBRE', 'ofreció tomar de la cuarentena'
    finally:
        _limpiar()


# ───────────────────────── se dañó una caja ─────────────────────────

def test_dar_de_baja_una_caja_sale_de_SU_tanda_no_de_la_mas_vieja(app, db_clean):
    """*"¿si se daña? ¿si quiero reemplazar solo uno?"*

    Si sólo se registrara la Salida, el reparto FEFO se la cobraría a la tanda más vieja y la
    que de verdad se rompió quedaría con las cuentas infladas.
    """
    _sembrar_maestro()
    try:
        vieja = _tanda(5, 100, vence='2027-01-01', lote='VIEJA')
        nueva = _tanda(5, 100, vence='2028-01-01', lote='NUEVA')
        c = _login(app)
        r = c.post('/api/mee/%s/merma-caja' % _COD,
                   json={'mov_id': nueva, 'caja': 2, 'cantidad': 100,
                         'motivo': 'se rompió al bajarla del estante', 'token': 'baja-1'},
                   headers=csrf_headers())
        assert r.status_code == 200, r.data[:300]
        d = _estado(c)
        por_id = {t['mov_id']: t for t in d['tandas']}
        assert por_id[nueva]['saldo'] == 400, \
            'la baja no salió de SU tanda: %r' % (por_id[nueva],)
        assert por_id[vieja]['saldo'] == 500, \
            'la baja se la cobró a la tanda más vieja: %r' % (por_id[vieja],)
        assert d['saldo_total'] == 900, d['saldo_total']
        assert d['fuera_de_servicio_total'] == 100
        assert 'caja 2' in (por_id[nueva]['bajas'][0]['motivo'] or ''), por_id[nueva]['bajas']
        # y el desglose sigue cuadrando con el kardex
        assert round(sum(t['saldo'] for t in d['tandas']), 2) == d['saldo_total']
    finally:
        _limpiar()


def test_no_se_puede_dar_de_baja_mas_de_lo_que_la_tanda_tiene(app, db_clean):
    """Pasarse no es corregir: es inventar una merma que deja el kardex en negativo."""
    _sembrar_maestro()
    try:
        t = _tanda(2, 100, vence='2027-01-01', lote='A')
        c = _login(app)
        r = c.post('/api/mee/%s/merma-caja' % _COD,
                   json={'mov_id': t, 'cantidad': 500, 'motivo': 'se mojó la estiba',
                         'token': 'baja-x'}, headers=csrf_headers())
        assert r.status_code == 400, r.data[:200]
        assert r.get_json().get('codigo') == 'BAJA_MAYOR_QUE_SALDO'
        assert _estado(c)['saldo_total'] == 200, 'igual descontó'
    finally:
        _limpiar()


def test_un_rechazo_NO_quema_el_token(app, db_clean):
    """Si el token se quemara en un rechazo, corregir la cantidad y reenviar diría 'ya se
    registró' -- una mentira que deja a la persona sin poder hacerlo (M260 al revés)."""
    _sembrar_maestro()
    try:
        t = _tanda(2, 100, vence='2027-01-01', lote='A')
        c = _login(app)
        tok = 'baja-reuso-1'
        r1 = c.post('/api/mee/%s/merma-caja' % _COD,
                    json={'mov_id': t, 'cantidad': 500, 'motivo': 'me equivoqué', 'token': tok},
                    headers=csrf_headers())
        assert r1.status_code == 400
        r2 = c.post('/api/mee/%s/merma-caja' % _COD,
                    json={'mov_id': t, 'cantidad': 50, 'motivo': 'se rompieron 50', 'token': tok},
                    headers=csrf_headers())
        assert r2.status_code == 200, \
            'el rechazo quemó el token y ya no puede corregir: %s' % r2.data[:200]
        assert _estado(c)['saldo_total'] == 150
    finally:
        _limpiar()


def test_un_doble_click_no_da_de_baja_dos_veces(app, db_clean):
    """Un doble descuento de material no da NINGÚN síntoma: se ve como un número más (M260)."""
    _sembrar_maestro()
    try:
        t = _tanda(3, 100, vence='2027-01-01', lote='A')
        c = _login(app)
        cuerpo = {'mov_id': t, 'caja': 1, 'cantidad': 100, 'motivo': 'caja aplastada',
                  'token': 'baja-doble-1'}
        assert c.post('/api/mee/%s/merma-caja' % _COD, json=cuerpo,
                      headers=csrf_headers()).status_code == 200
        r2 = c.post('/api/mee/%s/merma-caja' % _COD, json=cuerpo, headers=csrf_headers())
        assert r2.status_code == 409, r2.data[:200]
        assert _estado(c)['saldo_total'] == 200, 'el segundo clic descontó otra vez'
    finally:
        _limpiar()


def test_dos_bajas_seguidas_de_la_MISMA_caja_no_chocan(app, db_clean):
    """`mee_cajas_disposicion` tiene UNIQUE(mov_id, caja) y Calidad ya ocupa 1..N con sus filas:
    una baja con el número real chocaría con la de Calidad, y dos bajas de la misma caja entre
    sí. Son dos hechos legítimos (se rompieron 10 el lunes y 5 el martes)."""
    _sembrar_maestro()
    try:
        t = _tanda(3, 100, vence='2027-01-01', lote='A')
        c = _login(app)
        assert c.post('/api/mee/%s/merma-caja' % _COD,
                      json={'mov_id': t, 'caja': 2, 'cantidad': 10, 'motivo': 'se rompieron 10',
                            'token': 'b1'}, headers=csrf_headers()).status_code == 200
        r2 = c.post('/api/mee/%s/merma-caja' % _COD,
                    json={'mov_id': t, 'caja': 2, 'cantidad': 5, 'motivo': 'otras 5 el martes',
                          'token': 'b2'}, headers=csrf_headers())
        assert r2.status_code == 200, 'la segunda baja de la misma caja chocó: %s' % r2.data[:200]
        d = _estado(c)
        assert d['saldo_total'] == 285, d['saldo_total']
        assert d['fuera_de_servicio_total'] == 15
    finally:
        _limpiar()


def test_la_baja_NO_le_cambia_la_fecha_de_analisis_al_rotulo_F06(app, db_clean):
    """`dispuesto_at_utc` alimenta la FECHA DE ANÁLISIS del rótulo F06, que es un formato
    regulado: una baja de bodega no es un análisis de Calidad y no puede firmarle la fecha
    (M258)."""
    _sembrar_maestro()
    try:
        t = _tanda(3, 100, vence='2027-01-01', lote='A')
        c = _login(app)
        assert c.post('/api/mee/%s/merma-caja' % _COD,
                      json={'mov_id': t, 'caja': 1, 'cantidad': 20, 'motivo': 'caja aplastada',
                            'token': 'b-f06'}, headers=csrf_headers()).status_code == 200
        cn = _cn()
        try:
            filas = cn.execute("SELECT estado, COALESCE(dispuesto_at_utc,'') "
                               "  FROM mee_cajas_disposicion WHERE mov_id=?", (t,)).fetchall()
        finally:
            cn.close()
        assert filas, 'no quedó el rastro de la baja'
        for est, fecha in filas:
            if str(est or '').upper() == 'AVERIADA':
                assert fecha == '', \
                    'la baja escribió la fecha de análisis del rótulo regulado: %r' % (fecha,)
    finally:
        _limpiar()


# ───────────────────── lo que no se puede calcular, se dice ─────────────────────

def test_una_entrada_SIN_cajas_se_declara_en_vez_de_mostrar_cero(app, db_clean):
    """Todo el histórico entró sin desglose: mostrar 0 cajas se leería como "no queda nada",
    que es lo contrario de la verdad (M236/M100)."""
    _sembrar_maestro()
    try:
        cn = _cn()
        try:
            cn.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, unidad, "
                       "  lote_ref, responsable, fecha, estado) "
                       "VALUES (?,'Entrada',900,'und','VIEJO','test','2025-01-01 08:00','VIGENTE')",
                       (_COD,))
            cn.commit()
        finally:
            cn.close()
        d = _estado(_login(app))
        assert d['saldo_total'] == 900
        t = d['tandas'][0]
        assert t['sin_desglose'] is True, t
        assert d['sin_desglose_n'] == 1, 'no declara cuántas entradas no tienen desglose'
        assert 'no se contó por cajas' in d['instruccion'], d['instruccion']
    finally:
        _limpiar()


def test_el_stock_que_no_sale_de_ninguna_tanda_se_DECLARA(app, db_clean):
    """Un ajuste en más (saldo de apertura) deja stock sin tanda de origen. Repartirlo entre las
    tandas cuadraría el número inventando de dónde salió el material (M124/M148)."""
    _sembrar_maestro()
    try:
        _tanda(2, 100, vence='2027-01-01', lote='A')
        cn = _cn()
        try:
            cn.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, unidad, "
                       "  responsable, fecha, estado, observaciones) "
                       "VALUES (?,'Ajuste',300,'und','test','2026-05-01 08:00','VIGENTE','apertura')",
                       (_COD,))
            cn.commit()
        finally:
            cn.close()
        d = _estado(_login(app))
        assert d['saldo_total'] == 500
        assert d['sin_atribuir'] == 300, \
            'no declaró el stock que ninguna tanda explica: %r' % (d['sin_atribuir'],)
        assert d['tandas'][0]['saldo'] == 200, 'infló una tanda para cuadrar'
    finally:
        _limpiar()


# ───────────────────────── la pantalla puede llegar ─────────────────────────

def _cuerpo_de(js, decl):
    """Recorta UNA funcion por balance de llaves: una ventana de N caracteres la secuestra
    cualquier funcion que se escriba mas abajo y el guard deja de medir sin avisar (M229)."""
    i = js.find(decl)
    assert i != -1, 'no encontre %s' % decl
    j = js.index('{', i)
    prof = 0
    for k in range(j, len(js)):
        if js[k] == '{':
            prof += 1
        elif js[k] == '}':
            prof -= 1
            if prof == 0:
                return js[i:k + 1]
    raise AssertionError('no cerro %s' % decl)


def test_la_lista_de_envases_tiene_el_boton_de_CAJAS(app, db_clean):
    """Sin botón, el cálculo existe y nadie llega (M121, la forma más cara del hueco)."""
    js = pantalla_servida(_login(app), '/inventarios')
    assert 'meeCajas(' in js, 'ninguna fila ofrece ver las cajas'
    assert 'async function meeCajas' in js, 'el botón llama a una función que no existe'
    assert 'function _cjPintar' in js, 'la hoja no tiene quién la dibuje'


def test_la_hoja_pide_el_estado_al_BACKEND_y_no_lo_calcula_en_la_pantalla(app, db_clean):
    """El desglose lo deriva el backend del kardex. Si la pantalla lo recalculara, tendríamos dos
    cuentas del mismo hecho y divergirían el día que alguien toque una (M5/M99)."""
    js = pantalla_servida(_login(app), '/inventarios')
    cuerpo = _cuerpo_de(js, 'async function _cjPintar')
    assert "'/cajas'" in cuerpo or '/cajas' in cuerpo,         'la hoja no consulta el estado por cajas'
    for cuenta in ('Math.floor', '% upc', 'caja_abierta =', 'cajas_completas ='):
        assert cuenta not in cuerpo,             'la pantalla recalcula el desglose (%s) en vez de pedirlo: dos cuentas divergen' % cuenta


def test_dar_de_baja_va_por_el_endpoint_que_AUDITA(app, db_clean):
    """Una baja de material sin rastro no se puede reconstruir después (Part 11)."""
    js = pantalla_servida(_login(app), '/inventarios')
    cuerpo = _cuerpo_de(js, 'async function cjBaja')
    assert '/merma-caja' in cuerpo, 'la baja no llega al endpoint que la registra'
    assert 'X-CSRF-Token' in cuerpo, 'POST sin token CSRF'
    assert 'motivo' in cuerpo, 'no pide el motivo: la baja quedaría sin explicación'
    assert 'token:' in cuerpo, 'sin token de idempotencia: un doble clic descuenta dos veces'


def test_el_modal_se_puede_cerrar(app, db_clean):
    """Un pop-up sin salida obliga a recargar la página (M254)."""
    js = pantalla_servida(_login(app), '/inventarios')
    assert 'function _cjCerrar' in js, 'el modal no tiene salida'
    assert '_cjCerrar()' in js, 'la X no llama a nada'


def test_la_hoja_no_usa_colores_fijos_que_ignoran_el_tema_oscuro(app, db_clean):
    """Un fondo fijo con texto en token deja la pantalla ilegible al invertir el tema (M114)."""
    js = pantalla_servida(_login(app), '/inventarios')
    i = js.find("st.id='cj-css'")
    assert i != -1, 'la hoja de cajas no trae su estilo propio'
    css = js[i:i + 3000]
    import re as _re
    hexes = _re.findall(r'(?:background|color)\s*:\s*(#[0-9a-fA-F]{3,8})', css)
    assert not hexes, 'la hoja de cajas usa colores fijos: %r' % (hexes[:5],)
