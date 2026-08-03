# -*- coding: utf-8 -*-
"""Una OC AUTORIZADA no puede desaparecer de la pantalla donde se trabaja (3-ago).

Catalina: "se me estan perdiendo las ordenes autorizadas ... hoy ha realizado ordenes que no
aparecen". Verificado contra produccion: las dos OCs que hizo (OC-2026-0301 ADM y
OC-2026-0302 MEE, las dos `Autorizada`) SI estaban en /recepcion -- pero el desplegable de
"¿que OC estas recibiendo?" del formulario de ingreso filtraba

    estado IN ('Aprobada','Enviada','Parcial')

sin AUTORIZADA, que es justo el estado normal de una OC esperando la mercancia. Recepcion
listaba 51 OCs y el desplegable le ofrecia 3, ninguna suya: al ir a registrar el ingreso, sus
ordenes no existian.

'Enviada' ni siquiera es un estado de `ordenes_compra`: pertenece a la maquina de estados de
las COTIZACIONES (Borrador -> Enviada -> Recogida). Estaba de adorno.

Es M129 otra vez: un registro que sale de una lista tiene que seguir estando donde se lo
necesita. Y M45: el mismo filtro roto vivia tambien en el KPI de gerencia.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PREFIJO = 'ZZOCAUT'


def _admin(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM ordenes_compra_items WHERE numero_oc LIKE ?", (PREFIJO + '%',))
        cur.execute("DELETE FROM ordenes_compra WHERE numero_oc LIKE ?", (PREFIJO + '%',))
        conn.commit()


def _oc(app, sufijo, *, estado, categoria='MP', con_item=True):
    from database import get_db
    from datetime import datetime
    num = PREFIJO + sufijo
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO ordenes_compra (numero_oc, fecha, estado, proveedor, "
                    "categoria, valor_total) VALUES (?,?,?,?,?,?)",
                    (num, datetime.now().isoformat(), estado, 'PROV TEST', categoria, 100000))
        if con_item:
            cur.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, "
                        "cantidad_g, precio_unitario) VALUES (?,?,?,?,?)",
                        (num, 'MP00001', 'Materia test', 1000, 50))
        conn.commit()
    return num


def _nums(resp):
    d = resp.get_json()
    arr = d if isinstance(d, list) else (d.get('ocs') or [])
    return {x.get('numero_oc') for x in arr}


def test_una_oc_AUTORIZADA_se_puede_recibir(app, db_clean):
    """El caso de Catalina, exacto: OC autorizada esperando la mercancia."""
    _limpiar(app)
    num = _oc(app, 'A1', estado='Autorizada')
    r = _admin(app).get('/api/ordenes-compra/pendientes-recepcion')
    assert r.status_code == 200
    assert num in _nums(r), 'una OC Autorizada no aparece para recibir · es la queja literal'


def test_una_oc_PAGADA_sin_recibir_tambien(app, db_clean):
    """Pagar por anticipado y recibir despues es normal (M47). Si no aparece, esa mercancia
    no se puede registrar cuando llega."""
    _limpiar(app)
    num = _oc(app, 'A2', estado='Pagada')
    assert num in _nums(_admin(app).get('/api/ordenes-compra/pendientes-recepcion'))


def test_sigue_trayendo_las_que_ya_traia(app, db_clean):
    """El arreglo AMPLIA, no reemplaza: lo que ya funcionaba tiene que seguir igual."""
    _limpiar(app)
    a = _oc(app, 'A3', estado='Aprobada')
    p = _oc(app, 'A4', estado='Parcial')
    nums = _nums(_admin(app).get('/api/ordenes-compra/pendientes-recepcion'))
    assert a in nums and p in nums


def test_no_ofrece_para_recibir_lo_que_nadie_recibe(app, db_clean):
    """Con dientes: un servicio o una cuenta de cobro en el desplegable de ingreso invita a
    meter al kardex algo que no existe fisicamente."""
    _limpiar(app)
    svc = _oc(app, 'A5', estado='Autorizada', categoria='SVC')
    cc = _oc(app, 'A6', estado='Autorizada', categoria='CC')
    inf = _oc(app, 'A7', estado='Autorizada', categoria='Influencer/Marketing Digital')
    nums = _nums(_admin(app).get('/api/ordenes-compra/pendientes-recepcion'))
    assert svc not in nums and cc not in nums and inf not in nums


def test_no_ofrece_una_oc_ya_recibida(app, db_clean):
    _limpiar(app)
    num = _oc(app, 'A8', estado='Recibida')
    assert num not in _nums(_admin(app).get('/api/ordenes-compra/pendientes-recepcion'))


def test_ningun_filtro_de_OC_usa_el_estado_fantasma_Enviada():
    """'Enviada' es de las COTIZACIONES, no de las ordenes de compra. Donde aparezca en un
    filtro de `ordenes_compra` esta ocupando el lugar de un estado real -- que fue como
    'Autorizada' quedo afuera."""
    import io as _io, os as _os, re as _re
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    malos = []
    for sub in ('blueprints',):
        d = _os.path.join(raiz, 'api', sub)
        for f in _os.listdir(d):
            if not f.endswith('.py'):
                continue
            src = _io.open(_os.path.join(d, f), encoding='utf-8').read()
            for m in _re.finditer(r"FROM ordenes_compra[^;]{0,400}?estado IN \(([^)]*)\)", src, _re.S):
                if "'Enviada'" in m.group(1):
                    malos.append('%s: %s' % (f, m.group(1)[:80]))
    assert not malos, "filtros de ordenes_compra con el estado fantasma 'Enviada': %s" % malos


# ═══════════════════════════════════════════════════════════════════════════════
# "CUANDO DA AUTORIZAR DESAPARECEN Y NO SALEN EN POR PAGAR" (Catalina 3-ago)
# Desaparecian de verdad. La pantalla /compras pedia SOLO Borrador+Revisada, asi que al
# autorizar la OC salia del fetch -- y la seccion "Autorizadas" que ya existia abajo no se
# podia llenar nunca. El backend YA devolvia Autorizada por defecto: era la pantalla la que
# lo achicaba.
# Y el subtitulo prometia "las autorizadas listas para pagar estan en Por Pagar", que es
# FALSO para mercancia: esa espera en Recepcion hasta que llegue. La mandaba a buscarlas
# donde no estan (M129: un registro que sale de una lista tiene que decir a donde se fue,
# y el destino depende del TIPO).
# ═══════════════════════════════════════════════════════════════════════════════

def _compras_html():
    import ast as _ast, io as _io, os as _os
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    src = _io.open(_os.path.join(raiz, 'api', 'templates_py', 'compras_html.py'),
                   encoding='utf-8').read()
    for n in _ast.walk(_ast.parse(src)):
        if (isinstance(n, _ast.Assign) and isinstance(n.value, _ast.Constant)
                and isinstance(n.value.value, str) and len(n.value.value) > 100000):
            return n.value.value
    raise AssertionError('no encontre el HTML de compras')


def test_la_pantalla_pide_tambien_las_autorizadas():
    """Si la pantalla no las pide, la seccion 'Autorizadas' queda vacia para siempre y la OC
    desaparece en el momento en que se autoriza."""
    html = _compras_html()
    import re as _re
    m = _re.search(r"if\(!estados\.length\)\{\s*estados\s*=\s*(\[[^\]]*\])", html)
    assert m, 'no encontre el default de estados del consolidado'
    assert 'Autorizada' in m.group(1), (
        "la pantalla pide %s · al autorizar, la OC sale del fetch y desaparece" % m.group(1))


def test_existe_la_seccion_donde_caen_las_autorizadas():
    html = _compras_html()
    assert 'Autorizadas' in html and '_consolStage' in html, 'no hay seccion para las autorizadas'


def test_la_pantalla_no_promete_que_la_mercancia_va_a_por_pagar():
    """Por Pagar trae Recibida/Parcial y, de las Autorizadas, SOLO las de pago directo. Decir
    'las autorizadas van a Por Pagar' manda a buscar mercancia donde nunca va a estar."""
    html = _compras_html()
    assert 'las autorizadas listas para pagar están en <b>💰 Por Pagar</b>' not in html, \
        'el subtitulo sigue prometiendo el destino equivocado para la mercancia'
    assert 'Recepción' in html, 'no dice a donde SI va la mercancia autorizada'
