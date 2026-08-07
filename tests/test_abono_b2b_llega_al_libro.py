# -*- coding: utf-8 -*-
"""Un abono de cliente B2B llega al libro central de Tesorería.

Actualizar `pedidos.monto_pagado` es registrar plata que ENTRÓ, y no llegaba a `flujo_ingresos`
en una sola línea: Tesorería no veía un solo abono de B2B.

⚠ `monto_pagado` es un **ACUMULADO**, no un evento: cada PATCH fija el total nuevo. Por eso se
espeja la **diferencia** contra lo que había, y la referencia lleva ese acumulado. Insertar el
total en cada PATCH habría hecho crecer los ingresos con cada corrección -- y un ingreso inflado
no da síntoma: nadie sospecha de un número de más (M148).
"""
from .conftest import TEST_PASSWORD, csrf_headers

PED = 'ZZ-PED-ABONO-1'


def _cli(app):
    c = app.test_client()
    r = c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _sembrar(app):
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM flujo_ingresos WHERE referencia LIKE ?", ('PED-' + PED + '%',))
        c.execute("DELETE FROM pedidos WHERE numero=?", (PED,))
        c.execute("INSERT INTO pedidos (numero, fecha, estado, valor_total, empresa, "
                  " monto_pagado) VALUES (?,?,?,?,?,?)",
                  (PED, '2026-08-06', 'Confirmado', 1000000, 'ANIMUS', 0))
        conn.commit()


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM flujo_ingresos WHERE referencia LIKE ?", ('PED-' + PED + '%',))
        conn.execute("DELETE FROM pedidos WHERE numero=?", (PED,))
        conn.commit()


def _ingresos(app):
    from database import get_db
    with app.app_context():
        r = get_db().execute(
            "SELECT COALESCE(SUM(monto),0), COUNT(*) FROM flujo_ingresos "
            " WHERE fuente='pedido_abono' AND referencia LIKE ?", ('PED-' + PED + '%',)).fetchone()
        return float(r[0] or 0), int(r[1] or 0)


def _abonar(cli, total):
    return cli.patch('/api/pedidos/' + PED, json={'monto_pagado': total},
                     headers=csrf_headers())


def test_el_abono_llega_al_libro(app, db_clean):
    _sembrar(app)
    r = _abonar(_cli(app), 400000)
    assert r.status_code in (200, 201), r.data[:300]
    total, n = _ingresos(app)
    assert n == 1 and total == 400000, 'el abono no llegó a Tesorería (%s filas, %s)' % (n, total)
    _limpiar(app)


def test_el_SEGUNDO_abono_suma_solo_la_diferencia(app, db_clean):
    """`monto_pagado` es acumulado: si se espejara el total, el segundo abono contaría también
    el primero y los ingresos del mes quedarían inflados."""
    _sembrar(app)
    c = _cli(app)
    _abonar(c, 400000)
    _abonar(c, 700000)          # el cliente abona 300.000 más
    total, n = _ingresos(app)
    assert n == 2, 'esperaba dos movimientos, hay %d' % n
    assert total == 700000, 'sumó %s · debería ser el acumulado real, no la suma de totales' % total
    _limpiar(app)


def test_fijar_DOS_VECES_el_mismo_total_no_duplica(app, db_clean):
    """Guardar el mismo pedido otra vez (o un doble click) no puede inventar un ingreso."""
    _sembrar(app)
    c = _cli(app)
    _abonar(c, 500000)
    _abonar(c, 500000)
    total, n = _ingresos(app)
    assert n == 1 and total == 500000, 'se duplicó el abono (%s filas, %s)' % (n, total)
    _limpiar(app)


def test_CORREGIR_hacia_abajo_no_inventa_un_ingreso(app, db_clean):
    """Bajar el monto es una corrección, no plata que entra. Un ingreso negativo acá sería peor
    que el hueco original."""
    _sembrar(app)
    c = _cli(app)
    _abonar(c, 600000)
    _abonar(c, 200000)
    total, n = _ingresos(app)
    assert n == 1 and total == 600000, (
        'la corrección hacia abajo generó movimiento (%s filas, %s)' % (n, total))
    _limpiar(app)


def test_el_periodo_sale_de_la_fecha_del_HECHO(app, db_clean):
    """Si saliera del reloj del server (UTC), de noche el abono caería en el mes siguiente
    (M24/M106)."""
    from database import get_db
    from tz_colombia import hoy_colombia
    _sembrar(app)
    _abonar(_cli(app), 100000)
    with app.app_context():
        per = get_db().execute(
            "SELECT periodo FROM flujo_ingresos WHERE fuente='pedido_abono' "
            " AND referencia LIKE ? LIMIT 1", ('PED-' + PED + '%',)).fetchone()
    assert per and per[0] == hoy_colombia().strftime('%Y-%m'), per
    _limpiar(app)
