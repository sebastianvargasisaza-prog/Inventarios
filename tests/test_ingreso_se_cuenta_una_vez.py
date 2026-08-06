# -*- coding: utf-8 -*-
"""Un peso que entra se cuenta UNA vez, cuando se cobra. Y consignar no es vender.

Esto salió de un error MÍO, cazado antes de desplegarlo. Al hacer que el movimiento manual de
caja llegue al libro central quedó, sin querer, la plata contada dos veces:

    se cobra $250K en efectivo   -> ingreso $250K   (el espejo nuevo)
    se consigna esa misma plata  -> ingreso $250K   (el espejo que ya existía)
    ------------------------------------------------------------------
    ingresos del mes: $500K por $250K reales

El espejo del traslado existía por una razón razonable ("que la consignación no aparezca sin
origen"), y mientras el cobro en efectivo NO llegaba al libro, era la única forma de que esa
plata se contara. Pero es una respuesta al problema equivocado: **una consignación no es un
ingreso, es mover plata de un bolsillo propio a otro**, y el libro central registra ingresos y
gastos, no saldos de cuentas.

El modelo que queda, coherente y con una sola regla: **el ingreso se registra cuando se COBRA,
sea efectivo o no**; el método dice dónde quedó la plata, no si hubo venta. El origen de una
consignación se ve en el libro de caja, que existe justamente para eso.

Corolario que este archivo protege: la suma de `flujo_ingresos` tiene que ser igual a lo
cobrado, sin importar cuántas veces esa plata se mueva de bolsillo después.
"""
from .conftest import TEST_PASSWORD, csrf_headers

MARCA = 'ZZUNAVEZ'


def _admin(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM animus_caja_menor WHERE concepto LIKE ?", (MARCA + '%',))
        conn.execute("DELETE FROM animus_caja_menor WHERE concepto LIKE ?", ('%Consigna%',))
        for t in ('flujo_ingresos', 'flujo_egresos'):
            conn.execute("DELETE FROM " + t + " WHERE fuente='caja_menor'")
        conn.commit()


def _ingresos_caja(app):
    from database import get_db
    with app.app_context():
        return float(get_db().execute(
            "SELECT COALESCE(SUM(monto),0) FROM flujo_ingresos WHERE fuente='caja_menor'"
        ).fetchone()[0] or 0)


def test_cobrar_y_luego_CONSIGNAR_no_cuenta_la_plata_dos_veces(app, db_clean):
    """El caso exacto que casi se despliega."""
    _limpiar(app)
    c = _admin(app)
    r = c.post("/api/animus/caja", headers=csrf_headers(), json={
        "tipo": "ingreso", "concepto": MARCA + " cobro del dia",
        "monto": 250000, "fecha": "2026-08-04"})
    assert r.status_code == 200, r.data[:300]
    assert _ingresos_caja(app) == 250000, 'el cobro no llegó al libro'

    # ⚠ Se consigna MENOS de lo sembrado a propósito: la gaveta es global y los archivos
    # vecinos la dejan con el saldo que sea, así que consignar el total daba "no hay efectivo
    # suficiente" según quién corriera antes. La invariante que se mide no depende del monto:
    # mover plata de bolsillo no puede sumar ingresos, sea cual sea la cantidad.
    rc = c.post("/api/caja/traslado", headers=csrf_headers(), json={
        "monto": 50000, "fecha": "2026-08-04", "cuenta": "Bancolombia ***1234"})
    assert rc.status_code == 200, rc.data[:300]

    assert _ingresos_caja(app) == 250000, (
        'la consignación volvió a contar la plata · los ingresos del mes quedan inflados por '
        'mover el dinero de bolsillo')
    _limpiar(app)


def test_la_consignacion_SIGUE_teniendo_origen_en_el_libro_de_caja(app, db_clean):
    """Quitar el espejo no puede dejar la consignación huérfana: se ve en el libro de caja, con
    su recibo y su subtipo. Si no, se habría cambiado un número inflado por un rastro perdido."""
    _limpiar(app)
    c = _admin(app)
    c.post("/api/animus/caja", headers=csrf_headers(), json={
        "tipo": "ingreso", "concepto": MARCA + " fondeo", "monto": 90000,
        "fecha": "2026-08-04"})
    r = c.post("/api/caja/traslado", headers=csrf_headers(), json={
        "monto": 50000, "fecha": "2026-08-04", "cuenta": "Bancolombia ***1234"})
    assert r.status_code == 200, r.data[:300]
    recibo = r.get_json()['recibo_numero']

    lib = c.get('/api/caja/libro?desde=2026-08-04&hasta=2026-08-04').get_json()
    fila = [m for m in lib['movimientos'] if m['recibo'] == recibo]
    assert fila, 'la consignación desapareció del libro de caja'
    assert fila[0]['subtipo'] == 'traslado', 'no se distingue de un gasto'
    assert fila[0]['tipo'] == 'egreso', 'sale de la gaveta'
    _limpiar(app)


def test_el_cobro_EN_EFECTIVO_llega_al_libro(app, db_clean):
    """Antes el espejo estaba condicionado a `not es_efectivo`: la venta en efectivo sólo se
    contaba el día que alguien la consignara, y la que nunca se consignaba no se contaba nunca.
    Se mide sobre el fuente porque el cobro real exige un pedido de Shopify sembrado."""
    import io
    import os
    import re
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    s = io.open(os.path.join(raiz, 'api', 'blueprints', 'animus.py'), encoding='utf-8').read()
    i = s.find("categoria='Contraentrega'")
    assert i > 0, 'desapareció el espejo del cobro contraentrega'
    # ventana hacia atrás hasta el inicio del espejo · sin comentarios (M154)
    j = s.rfind('_tesoreria_espejo', 0, i)
    ventana = re.sub(r'^\s*#[^\n]*$', '', s[max(0, j - 400):i], flags=re.M)
    assert 'if not es_efectivo' not in ventana, (
        'el cobro en efectivo volvió a quedar fuera del libro · esa venta sólo se contaría al '
        'consignarla, y la que nunca se consigna no se cuenta nunca')


def test_el_traslado_NO_escribe_en_flujo_ingresos(app, db_clean):
    """Guard estructural del modelo: si alguien vuelve a espejar el traslado como ingreso, el
    doble conteo regresa y no da ningún síntoma -- nadie sospecha de un ingreso de más."""
    import io
    import os
    import re
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    s = io.open(os.path.join(raiz, 'api', 'blueprints', 'animus.py'), encoding='utf-8').read()
    i = s.find("subtipo='traslado'")
    assert i > 0, 'no encuentro el traslado'
    j = s.find('audit_log', i)
    bloque = re.sub(r'^\s*#[^\n]*$', '', s[i:j], flags=re.M)
    assert '_tesoreria_espejo' not in bloque, (
        'la consignación volvió a espejarse al libro · mover plata entre dos bolsillos propios '
        'no es un ingreso, y sumado al espejo del cobro cuenta lo mismo dos veces')
