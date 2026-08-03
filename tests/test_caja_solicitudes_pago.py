# -*- coding: utf-8 -*-
"""La caja menor PAGA: solicitar -> autorizar -> pagar (3-ago).

Sebastián: *"luz asistente de espagiria solicita un pago se autoriza pago con caja menor ·
catalina dice hay que pagar tal cosa decimos paguen con caja menor · daniela es quien maneja
caja menor entonces ella paga registra solicita ok de gerencia paga sube el comprobante de ese
pago y ese dinero sale de la caja · a veces es mucha le digo consigna a la cuenta"*.

Decisiones suyas que estos tests fijan:

1. **UNA sola caja** (una gaveta física, Daniela paga todo) con `empresa` en cada movimiento:
   el saldo sigue siendo verificable contra el efectivo real y el reporte separa las dos.
2. **Tope**: bajo cierto monto se paga sin esperar a gerencia. Configurable sin desplegar.
3. **El comprobante puede subirse después**, pero lo que no tiene respaldo se cuenta y se
   muestra -- un egreso sin comprobante es una salida que nadie puede verificar.

Y dos reglas que definen el modelo:

- **El saldo baja al PAGAR, no al autorizar.** Una autorización no es plata que salió; si el
  saldo bajara antes, dejaría de cuadrar contra el efectivo de la gaveta.
- **Consignar NO es gastar.** El traslado a la cuenta va con `subtipo='traslado'`: contarlo
  como egreso inflaría los gastos del mes y reportaría como gastado algo que está en el banco.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

CONCEPTO = 'ZZTEST caja solicitud'


def _cli(app, quien):
    c = app.test_client()
    r = c.post("/login", data={"username": quien, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pude loguear a %s' % quien
    return c


def _limpiar(app):
    """Limpia ANTES de sembrar (M103): la BD de tests es compartida."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM animus_caja_menor WHERE concepto LIKE ?", ('%ZZTEST%',))
        cur.execute("DELETE FROM caja_solicitudes_pago WHERE concepto LIKE ?", ('%ZZTEST%',))
        conn.commit()


def _saldo(app):
    from database import get_db
    with app.app_context():
        conn = get_db()
        return float(conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN tipo='ingreso' THEN monto ELSE -monto END),0) "
            "FROM animus_caja_menor WHERE COALESCE(anulado,0)=0").fetchone()[0] or 0)


def _sembrar_efectivo(app, monto):
    """Mete efectivo a la caja para que haya con qué pagar."""
    from database import get_db
    from tz_colombia import hoy_colombia
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO animus_caja_menor (fecha, tipo, concepto, monto, "
                    "registrado_por, recibo_numero) VALUES (?,'ingreso',?,?,?,?)",
                    (hoy_colombia().isoformat(), 'ZZTEST saldo inicial', monto, 'test',
                     'RC-TEST-%d' % int(monto)))
        conn.commit()


def _tope(app, monto):
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO app_settings (clave, valor) "
                    "VALUES ('caja_tope_sin_autorizar', ?) "
                    "ON CONFLICT (clave) DO UPDATE SET valor=excluded.valor", (str(monto),))
        conn.commit()


def _crear(cli, **kw):
    body = {'concepto': CONCEPTO, 'monto': 500000, 'empresa': 'ANIMUS'}
    body.update(kw)
    return cli.post('/api/caja/solicitudes', json=body, headers=csrf_headers())


# ── el flujo completo ────────────────────────────────────────────────────────

def test_el_camino_completo_solicitar_autorizar_pagar(app, db_clean):
    _limpiar(app); _tope(app, 100000); _sembrar_efectivo(app, 2000000)
    saldo0 = _saldo(app)

    # Catalina pide
    r = _crear(_cli(app, 'catalina'), monto=500000, beneficiario='Ferretería',
               modulo_origen='compras')
    assert r.status_code == 201, r.data[:300]
    d = r.get_json()
    sid, numero = d['id'], d['numero']
    assert d['estado'] == 'solicitada' and numero.startswith('SP-')

    # autorizar NO mueve el saldo · una autorización no es plata que salió
    r = _cli(app, 'sebastian').post('/api/caja/solicitudes/%d/autorizar' % sid,
                                    json={}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert _saldo(app) == saldo0, 'el saldo bajó al AUTORIZAR · debe bajar al pagar'

    # Daniela paga · acá sí baja, con recibo
    r = _cli(app, 'sebastian').post('/api/caja/solicitudes/%d/pagar' % sid,
                                    json={}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    p = r.get_json()
    assert p['recibo_numero'].startswith('RC-') and p['estado'] == 'pagada'
    assert _saldo(app) == saldo0 - 500000, 'el pago no bajó el saldo'


def test_el_saldo_NO_baja_al_autorizar(app, db_clean):
    """Con dientes, aislado: si bajara al autorizar, el saldo dejaría de cuadrar contra el
    efectivo de la gaveta -- que es lo único que se puede contar contra la realidad."""
    _limpiar(app); _tope(app, 1000); _sembrar_efectivo(app, 900000)
    sid = _crear(_cli(app, 'catalina'), monto=300000).get_json()['id']
    antes = _saldo(app)
    _cli(app, 'sebastian').post('/api/caja/solicitudes/%d/autorizar' % sid,
                                json={}, headers=csrf_headers())
    assert _saldo(app) == antes


# ── el tope ──────────────────────────────────────────────────────────────────

def test_bajo_el_tope_no_espera_a_gerencia(app, db_clean):
    _limpiar(app); _tope(app, 200000)
    d = _crear(_cli(app, 'catalina'), monto=50000).get_json()
    assert d['estado'] == 'autorizada' and d['bajo_tope'] is True


def test_sobre_el_tope_SI_espera(app, db_clean):
    _limpiar(app); _tope(app, 200000)
    d = _crear(_cli(app, 'catalina'), monto=200001).get_json()
    assert d['estado'] == 'solicitada' and d['bajo_tope'] is False


def test_el_atajo_del_tope_queda_DECLARADO(app, db_clean):
    """Un atajo sin rastro es indistinguible de alguien saltándose el control."""
    _limpiar(app); _tope(app, 200000)
    sid = _crear(_cli(app, 'catalina'), monto=50000).get_json()['id']
    from database import get_db
    with app.app_context():
        conn = get_db()
        via = conn.execute("SELECT autorizacion_via FROM caja_solicitudes_pago WHERE id=?",
                           (sid,)).fetchone()[0]
    assert 'tope' in (via or '').lower(), 'no dice por qué quedó autorizada sin gerencia'


def test_el_tope_se_cambia_sin_desplegar(app, db_clean):
    c = _cli(app, 'sebastian')
    r = c.put('/api/caja/tope', json={'tope': 350000}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:200]
    assert c.get('/api/caja/tope').get_json()['tope'] == 350000


# ── los controles ────────────────────────────────────────────────────────────

def test_nadie_autoriza_su_propia_solicitud(app, db_clean):
    """Es el control que hace que la autorización signifique algo."""
    _limpiar(app); _tope(app, 1000)
    sid = _crear(_cli(app, 'sebastian'), monto=800000).get_json()['id']
    r = _cli(app, 'sebastian').post('/api/caja/solicitudes/%d/autorizar' % sid,
                                    json={}, headers=csrf_headers())
    assert r.status_code == 403, r.data[:200]


def test_solo_gerencia_autoriza(app, db_clean):
    _limpiar(app); _tope(app, 1000)
    sid = _crear(_cli(app, 'catalina'), monto=800000).get_json()['id']
    r = _cli(app, 'catalina').post('/api/caja/solicitudes/%d/autorizar' % sid,
                                   json={}, headers=csrf_headers())
    assert r.status_code == 403


def test_no_se_paga_lo_que_no_esta_autorizado(app, db_clean):
    """Con dientes: pagar sin autorización es saltarse el control entero."""
    _limpiar(app); _tope(app, 1000); _sembrar_efectivo(app, 900000)
    sid = _crear(_cli(app, 'catalina'), monto=700000).get_json()['id']
    r = _cli(app, 'sebastian').post('/api/caja/solicitudes/%d/pagar' % sid,
                                    json={}, headers=csrf_headers())
    assert r.status_code == 409, r.data[:200]


def test_no_se_paga_dos_veces(app, db_clean):
    """Es plata: dos clics no pueden sacar el doble de la gaveta."""
    _limpiar(app); _tope(app, 1000000); _sembrar_efectivo(app, 3000000)
    sid = _crear(_cli(app, 'catalina'), monto=400000).get_json()['id']
    c = _cli(app, 'sebastian')
    assert c.post('/api/caja/solicitudes/%d/pagar' % sid, json={},
                  headers=csrf_headers()).status_code == 200
    saldo = _saldo(app)
    assert c.post('/api/caja/solicitudes/%d/pagar' % sid, json={},
                  headers=csrf_headers()).status_code == 409
    assert _saldo(app) == saldo, 'el segundo pago igual movió el saldo'


def test_no_se_paga_mas_de_lo_que_hay_en_la_gaveta(app, db_clean):
    """Un pago que deja la caja en negativo es un pago que no ocurrió: el efectivo físico no
    puede ser menor que cero."""
    _limpiar(app); _tope(app, 9999999)
    _sembrar_efectivo(app, 100000)
    sid = _crear(_cli(app, 'catalina'), monto=5000000).get_json()['id']
    r = _cli(app, 'sebastian').post('/api/caja/solicitudes/%d/pagar' % sid,
                                    json={}, headers=csrf_headers())
    assert r.status_code == 409
    assert r.get_json().get('puede_forzar') is True, 'no ofrece salida si el efectivo sí está'


def test_el_rechazo_exige_motivo(app, db_clean):
    """Sin motivo, quien pidió no sabe qué corregir y quien audita no sabe por qué no se pagó."""
    _limpiar(app); _tope(app, 1000)
    sid = _crear(_cli(app, 'catalina'), monto=900000).get_json()['id']
    c = _cli(app, 'sebastian')
    assert c.post('/api/caja/solicitudes/%d/rechazar' % sid, json={},
                  headers=csrf_headers()).status_code == 400
    assert c.post('/api/caja/solicitudes/%d/rechazar' % sid, json={'motivo': 'no aplica'},
                  headers=csrf_headers()).status_code == 200


def test_una_rechazada_no_se_puede_pagar(app, db_clean):
    _limpiar(app); _tope(app, 1000); _sembrar_efectivo(app, 2000000)
    sid = _crear(_cli(app, 'catalina'), monto=600000).get_json()['id']
    c = _cli(app, 'sebastian')
    c.post('/api/caja/solicitudes/%d/rechazar' % sid, json={'motivo': 'no'},
           headers=csrf_headers())
    assert c.post('/api/caja/solicitudes/%d/pagar' % sid, json={},
                  headers=csrf_headers()).status_code == 409


# ── el comprobante ───────────────────────────────────────────────────────────

def test_lo_pagado_sin_comprobante_se_CUENTA_y_se_ve(app, db_clean):
    """Se puede pagar y subirlo después (decisión de Sebastián), pero no en silencio: lo que
    no tiene respaldo tiene que incomodar hasta que se cierre."""
    _limpiar(app); _tope(app, 1000000); _sembrar_efectivo(app, 2000000)
    sid = _crear(_cli(app, 'catalina'), monto=250000).get_json()['id']
    c = _cli(app, 'sebastian')
    c.post('/api/caja/solicitudes/%d/pagar' % sid, json={}, headers=csrf_headers())
    sc = c.get('/api/caja/solicitudes').get_json()['sin_comprobante']
    assert sc['n'] >= 1 and sc['monto'] >= 250000, sc

    r = c.post('/api/caja/solicitudes/%d/comprobante' % sid,
               json={'url': 'https://x/comprobante.jpg'}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:200]
    sc2 = c.get('/api/caja/solicitudes').get_json()['sin_comprobante']
    assert sc2['n'] == sc['n'] - 1


def test_el_comprobante_queda_tambien_en_el_MOVIMIENTO(app, db_clean):
    """Quien audita la caja mira el movimiento, no la solicitud: un egreso sin su respaldo a
    la vista es un egreso sin respaldo."""
    _limpiar(app); _tope(app, 1000000); _sembrar_efectivo(app, 2000000)
    sid = _crear(_cli(app, 'catalina'), monto=120000).get_json()['id']
    c = _cli(app, 'sebastian')
    mov_id = c.post('/api/caja/solicitudes/%d/pagar' % sid, json={},
                    headers=csrf_headers()).get_json()['caja_mov_id']
    c.post('/api/caja/solicitudes/%d/comprobante' % sid,
           json={'url': 'https://x/c.pdf'}, headers=csrf_headers())
    from database import get_db
    with app.app_context():
        conn = get_db()
        url = conn.execute("SELECT comprobante_url FROM animus_caja_menor WHERE id=?",
                           (mov_id,)).fetchone()[0]
    assert url == 'https://x/c.pdf'


# ── las dos empresas ─────────────────────────────────────────────────────────

def test_cada_movimiento_lleva_su_EMPRESA(app, db_clean):
    """Una sola gaveta, pero la plata es de dos empresas: sin la marca el reporte no las
    puede separar."""
    _limpiar(app); _tope(app, 1000000); _sembrar_efectivo(app, 3000000)
    sid = _crear(_cli(app, 'catalina'), monto=90000, empresa='ESPAGIRIA').get_json()['id']
    c = _cli(app, 'sebastian')
    mov = c.post('/api/caja/solicitudes/%d/pagar' % sid, json={},
                 headers=csrf_headers()).get_json()['caja_mov_id']
    from database import get_db
    with app.app_context():
        conn = get_db()
        emp = conn.execute("SELECT empresa FROM animus_caja_menor WHERE id=?", (mov,)).fetchone()[0]
    assert emp == 'ESPAGIRIA'


def test_una_empresa_inventada_se_rechaza(app, db_clean):
    _limpiar(app)
    r = _crear(_cli(app, 'catalina'), empresa='OTRA COSA')
    assert r.status_code == 400


# ── el traslado a la cuenta ──────────────────────────────────────────────────

def test_consignar_NO_es_un_gasto(app, db_clean):
    """La plata cambia de bolsillo. Contarlo como gasto inflaría los gastos del mes y
    reportaría como gastado algo que está en el banco."""
    _limpiar(app); _sembrar_efectivo(app, 5000000)
    saldo0 = _saldo(app)
    r = _cli(app, 'sebastian').post('/api/caja/traslado',
                                    json={'monto': 1500000, 'cuenta': 'Bancolombia 123'},
                                    headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    assert _saldo(app) == saldo0 - 1500000, 'el traslado no bajó el efectivo'
    from database import get_db
    with app.app_context():
        conn = get_db()
        st = conn.execute("SELECT subtipo FROM animus_caja_menor WHERE id=?",
                          (r.get_json()['caja_mov_id'],)).fetchone()[0]
    assert st == 'traslado', 'un traslado marcado como gasto infla los gastos del mes'


def test_no_se_consigna_mas_de_lo_que_hay(app, db_clean):
    _limpiar(app); _sembrar_efectivo(app, 50000)
    r = _cli(app, 'sebastian').post('/api/caja/traslado', json={'monto': 9000000},
                                    headers=csrf_headers())
    assert r.status_code == 409


# ── higiene ──────────────────────────────────────────────────────────────────

def test_una_solicitud_sin_concepto_o_sin_monto_no_entra(app, db_clean):
    _limpiar(app)
    c = _cli(app, 'catalina')
    assert _crear(c, concepto='').status_code == 400
    assert _crear(c, monto=0).status_code == 400
    assert _crear(c, monto=-5000).status_code == 400


def test_la_migracion_409_es_ADITIVA():
    """Lo que ya estaba registrado en la caja no puede cambiar: la migración sólo AGREGA."""
    import io as _io, os as _os, re as _re
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    src = _io.open(_os.path.join(raiz, 'api', 'database.py'), encoding='utf-8').read()
    m = _re.search(r"\(409,.*?\n\s*\]\),", src, _re.S)
    assert m, 'no encontré la migración 409'
    cuerpo = m.group(0)
    for prohibido in ('DELETE ', 'DROP ', 'UPDATE animus_caja_menor SET'):
        assert prohibido not in cuerpo, 'la migración 409 toca datos existentes: %s' % prohibido


# ── la PUERTA (M121) ─────────────────────────────────────────────────────────
# Casi mata la feature: los endpoints nacieron con `_auth()` de ANIMUS_ACCESS
# ({daniela, alejandro, sebastian}), y quienes SOLICITAN son Catalina desde Compras y Luz
# desde Espagiria. Ninguna de las dos estaba en ese set: la feature nacia inalcanzable para
# justo la gente que la pidio. El permiso se amplia en la PUERTA, no solo al final.

def test_catalina_y_luz_pueden_SOLICITAR(app, db_clean):
    _limpiar(app); _tope(app, 1000)
    for quien, empresa in (('catalina', 'ANIMUS'), ('luz', 'ESPAGIRIA')):
        r = _crear(_cli(app, quien), monto=700000, empresa=empresa)
        assert r.status_code == 201, '%s no puede solicitar: %s' % (quien, r.data[:200])


def test_daniela_puede_PAGAR(app, db_clean):
    """Es quien maneja la caja: si no puede pagar, el flujo no se cierra."""
    _limpiar(app); _tope(app, 1000000); _sembrar_efectivo(app, 2000000)
    sid = _crear(_cli(app, 'catalina'), monto=300000).get_json()['id']
    r = _cli(app, 'daniela').post('/api/caja/solicitudes/%d/pagar' % sid,
                                  json={}, headers=csrf_headers())
    assert r.status_code == 200, r.data[:250]


def test_la_puerta_sigue_teniendo_dientes(app, db_clean):
    """Ampliar el acceso no puede volverlo una puerta abierta: quien no tiene nada que ver
    con la caja sigue afuera."""
    _limpiar(app)
    c = app.test_client()
    r = c.post("/login", data={"username": "mayerlin", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    if r.status_code != 302:
        import pytest as _pt
        _pt.skip('mayerlin no existe en este entorno')
    r2 = _crear(c)
    assert r2.status_code in (401, 403), 'entro alguien que no deberia: %s' % r2.status_code


def test_daniela_NO_autoriza_lo_que_supera_el_tope(app, db_clean):
    """Quien maneja la caja no puede autorizarse el gasto grande a si misma: ese es todo el
    punto del tope."""
    _limpiar(app); _tope(app, 100000)
    sid = _crear(_cli(app, 'catalina'), monto=900000).get_json()['id']
    r = _cli(app, 'daniela').post('/api/caja/solicitudes/%d/autorizar' % sid,
                                  json={}, headers=csrf_headers())
    assert r.status_code == 403, r.data[:200]


# ── el punto de ENTRADA en cada modulo (M120: lo pide quien lo necesita, donde trabaja) ──
# Sebastian: "quiero que catalina en modulo compras tenga una sub pestana solicitar pago desde
# caja menor, me llega a mi a mi modulo ceo autorizo le sale a daniela autorizado paga queda
# trazabilidad, lo mismo a luz en su modulo de espagiria".
# Un endpoint sin pantalla es una feature que en la practica nadie usa (M94).

def _html_compras():
    import ast as _ast, io as _io, os as _os
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    src = _io.open(_os.path.join(raiz, 'api', 'templates_py', 'compras_html.py'),
                   encoding='utf-8').read()
    for n in _ast.walk(_ast.parse(src)):
        if (isinstance(n, _ast.Assign) and isinstance(n.value, _ast.Constant)
                and isinstance(n.value.value, str) and len(n.value.value) > 100000):
            return n.value.value
    raise AssertionError('no encontre el HTML de compras')


def test_compras_tiene_la_subpestana_completa():
    """Boton + panel + despacho. Si falta el despacho la pestana abre vacia; si falta el
    `data-tab` el handler delegado de `.tn` apaga TODOS los panes y deja la pantalla en
    blanco (M61 · ya paso al reusar esa clase sin el atributo)."""
    html = _html_compras()
    assert 'data-tab="cajapagos"' in html, 'el boton no lleva data-tab · apagaria toda la pantalla'
    assert 'id="pane-cajapagos"' in html, 'no existe el panel'
    assert "tab==='cajapagos'" in html, 'la pestana no esta enrutada · abriria vacia'
    assert 'function loadCajaPagos' in html, 'nadie llena el panel'


def test_compras_NO_ofrece_autorizar_ni_pagar():
    """Autorizar es de gerencia y pagar es de quien maneja la caja. Un boton que responde 403
    es peor que no tenerlo: quien lo aprieta cree que hizo algo."""
    html = _html_compras()
    i = html.index('id="pane-cajapagos"')
    j = html.index('id="pane-por-pagar"', i)
    panel = html[i:j]
    for prohibido in ('/autorizar', '/pagar'):
        assert prohibido not in panel, 'la pantalla de Compras ofrece %s' % prohibido


def test_la_solicitud_desde_compras_queda_marcada_con_su_ORIGEN(app, db_clean):
    """Sin el origen no se puede saber de que modulo salio cada pedido."""
    _limpiar(app); _tope(app, 1000)
    sid = _crear(_cli(app, 'catalina'), monto=600000,
                 modulo_origen='compras').get_json()['id']
    from database import get_db
    with app.app_context():
        conn = get_db()
        org = conn.execute("SELECT modulo_origen FROM caja_solicitudes_pago WHERE id=?",
                           (sid,)).fetchone()[0]
    assert org == 'compras'


def _html_espagiria():
    import ast as _ast, io as _io, os as _os
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    src = _io.open(_os.path.join(raiz, 'api', 'templates_py', 'espagiria_html.py'),
                   encoding='utf-8').read()
    cands = [n.value.value for n in _ast.walk(_ast.parse(src))
             if isinstance(n, _ast.Assign) and isinstance(n.value, _ast.Constant)
             and isinstance(n.value.value, str) and len(n.value.value) > 5000]
    assert cands, 'no encontre el HTML de espagiria'
    return max(cands, key=len)


def test_espagiria_tiene_la_entrada_de_luz_completa():
    """Boton + panel + despacho + quien lo llena. Si falta el despacho la pestana abre vacia."""
    html = _html_espagiria()
    assert 'data-tab="cajapagos"' in html, 'no hay boton'
    assert 'id="esp-tab-cajapagos"' in html, 'no existe el panel'
    assert "name === 'cajapagos'" in html, 'la pestana no esta enrutada · abriria vacia'
    assert 'function cargarPagosCaja' in html, 'nadie llena el panel'


def test_luz_ve_solo_lo_de_ESPAGIRIA():
    """No tiene por que ver los gastos de ANIMUS: la lista se pide filtrada."""
    html = _html_espagiria()
    assert "'/api/caja/solicitudes?empresa=ESPAGIRIA'" in html, \
        'la pantalla de Luz pide TODAS las solicitudes'


def test_espagiria_NO_ofrece_autorizar_ni_pagar():
    html = _html_espagiria()
    for prohibido in ('/autorizar', '/pagar'):
        assert prohibido not in html, 'la pantalla de Luz ofrece %s' % prohibido


def test_el_filtro_por_empresa_funciona_de_verdad(app, db_clean):
    """El filtro de la pantalla tiene que existir en el BACKEND: si el parametro se ignora,
    Luz veria todo igual y el test de arriba pasaria mirando una promesa vacia."""
    _limpiar(app); _tope(app, 1000)
    _crear(_cli(app, 'catalina'), monto=700000, empresa='ANIMUS')
    _crear(_cli(app, 'luz'), monto=700000, empresa='ESPAGIRIA')
    d = _cli(app, 'luz').get('/api/caja/solicitudes?empresa=ESPAGIRIA').get_json()
    empresas = {s['empresa'] for s in d['solicitudes']}
    assert empresas <= {'ESPAGIRIA'}, 'el filtro por empresa no se aplica: %s' % empresas
