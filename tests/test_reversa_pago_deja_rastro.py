# -*- coding: utf-8 -*-
"""Revertir un pago deja RASTRO y cuadra en todas las vistas, sin tocar 52 consultas.

Sebastián 7-ago: *"resuelve el dos"*.

Hasta hoy la reversa BORRABA la fila del libro. Dos problemas, y el segundo es el que duele:

  (a) emparejaba por monto, así que con dos pagos parciales del MISMO monto a la misma OC,
      revertir el viejo se llevaba la fila del NUEVO: el total quedaba bien y el detalle mentía;
  (b) una reversa no dejaba nada. El libro perdía una fila en vez de mostrar que hubo un pago y
      su reversa, que es justo lo que alguien necesita para entender un período (M106).

⚠ Y la decisión de diseño que este test protege: **no se usó una columna `anulado`**. Hay 29
lugares que leen `flujo_egresos` y 23 más `flujo_ingresos`; un flag obliga a filtrarlo en los 52
y basta que uno se olvide para mostrar plata anulada (M116). El asiento compensatorio cuadra solo
en TODAS las vistas sin tocar una sola consulta, que es como el kardex anula un movimiento (M31).
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

OC = 'OC-REV-TEST-1'


def _seed(app, montos):
    """Una OC recibida con N pagos y su egreso espejo por cada uno."""
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM flujo_egresos WHERE referencia=?", (OC,))
        c.execute("DELETE FROM pagos_oc WHERE numero_oc=?", (OC,))
        c.execute("DELETE FROM ordenes_compra WHERE numero_oc=?", (OC,))
        c.execute("INSERT INTO ordenes_compra (numero_oc, proveedor, estado, valor_total) "
                  "VALUES (?, 'Prov Rev', 'Pagada', ?)", (OC, sum(montos)))
        for m in montos:
            c.execute("INSERT INTO pagos_oc (numero_oc, monto, fecha_pago, medio, registrado_por) "
                      "VALUES (?,?,date('now','-5 hours'),'Transferencia','sebastian')", (OC, m))
            c.execute("INSERT INTO flujo_egresos (fecha, empresa, concepto, categoria, monto, "
                      "periodo, fuente, referencia, creado_por) VALUES "
                      "(date('now','-5 hours'),'HHA',?, 'MPs', ?, "
                      " substr(date('now','-5 hours'),1,7), 'compras', ?, 'sebastian')",
                      ('Pago ' + OC, m, OC))
        c.commit()


def _libro(app):
    from database import get_db
    with app.app_context():
        filas = get_db().execute(
            "SELECT id, monto, concepto FROM flujo_egresos WHERE referencia=? ORDER BY id",
            (OC,)).fetchall()
    return [(r[0], float(r[1]), r[2]) for r in filas]


def _revertir(admin_client):
    return admin_client.post('/api/ordenes-compra/%s/revertir-pago' % OC,
                             json={'motivo': 'prueba de reversa con rastro completo'},
                             headers={'Origin': 'http://localhost'})


def test_la_reversa_NO_borra_la_fila_del_libro(app, admin_client):
    _seed(app, [500000])
    r = _revertir(admin_client)
    assert r.status_code == 200, r.data[:300]
    filas = _libro(app)
    assert len(filas) == 2, 'la reversa borró en vez de compensar · el libro perdió el rastro'
    assert any(m > 0 for _, m, _ in filas), 'desapareció el pago original'
    assert any(m < 0 for _, m, _ in filas), 'no quedó el asiento de reversa'


def test_NETEA_en_CERO_sin_tocar_ninguna_consulta(app, admin_client):
    """Es la razón de elegir el asiento compensatorio sobre una columna `anulado`: cualquier
    vista que SUME queda correcta sola, y son 52."""
    _seed(app, [500000])
    _revertir(admin_client)
    assert abs(sum(m for _, m, _ in _libro(app))) < 0.01, 'la reversa no netea a cero'


def test_NETEA_EN_EL_MISMO_PERIODO(app, admin_client):
    """Si el asiento cayera en el mes siguiente, el mes del pago quedaría inflado para siempre y
    el neteo sólo cuadraría en el acumulado."""
    from database import get_db
    _seed(app, [500000])
    _revertir(admin_client)
    with app.app_context():
        per = get_db().execute(
            "SELECT periodo, SUM(monto) FROM flujo_egresos WHERE referencia=? GROUP BY periodo",
            (OC,)).fetchall()
    assert len(per) == 1, 'el pago y su reversa quedaron en períodos distintos: %s' % (per,)
    assert abs(float(per[0][1] or 0)) < 0.01, 'el período no netea'


def test_con_DOS_pagos_del_mismo_monto_no_se_lleva_el_que_no_es(app, admin_client):
    """El bug (a): emparejaba por monto y podía compensar contra el pago equivocado. Con el
    asiento compensatorio el resultado es correcto igual, y además queda a la vista cuál se
    revirtió."""
    _seed(app, [300000, 300000])
    antes = _libro(app)
    assert len(antes) == 2
    r = _revertir(admin_client)
    assert r.status_code == 200, r.data[:300]
    despues = _libro(app)
    # las dos filas originales SIGUEN ahí · sólo se agregó la reversa
    ids_antes = {i for i, _, _ in antes}
    assert ids_antes.issubset({i for i, _, _ in despues}), \
        'se llevó por delante una fila legítima del mismo monto'
    assert abs(sum(m for _, m, _ in despues) - 300000) < 0.01, \
        'debía quedar un solo pago de 300.000 en el neto'


def test_la_reversa_dice_QUIEN_y_POR_QUE(app, admin_client):
    """Una reversa sin autor ni motivo es un hueco que nadie puede explicar tres meses después."""
    from database import get_db
    _seed(app, [500000])
    _revertir(admin_client)
    with app.app_context():
        r = get_db().execute(
            "SELECT creado_por, observaciones, concepto FROM flujo_egresos "
            " WHERE referencia=? AND monto < 0 ORDER BY id DESC LIMIT 1", (OC,)).fetchone()
    assert r, 'no hay asiento de reversa'
    assert (r[0] or '').strip(), 'la reversa no dice quién la hizo'
    assert 'prueba de reversa' in (r[1] or ''), 'la reversa no guarda el motivo'
    assert 'Reversa' in (r[2] or ''), 'el concepto no se distingue de un pago normal'


def test_NADIE_volvio_a_meter_un_DELETE_sobre_el_libro(app):
    """El trinquete: borrar del libro deja un hueco que ninguna vista puede explicar. Si alguien
    necesita anular, se compensa (M31/M106)."""
    import io as _io
    import re as _re
    for rel in ('api/blueprints/compras.py', 'api/blueprints/animus.py',
                'api/blueprints/financiero.py'):
        src = _io.open(os.path.join(RAIZ, rel), encoding='utf-8').read()
        # sin comentarios: si no, el test encuentra MI PROPIA explicación de por qué se retiró
        # el DELETE y falla por la razón equivocada (M154, me pasó cuatro veces hoy)
        limpio = _re.sub(r'#[^\n]*', '', src)
        limpio = _re.sub(r'"""(?:.|\n)*?"""', '', limpio)
        # Lo que se prohíbe es el borrado POR REGISTRO (una reversa, una corrección): ahí el
        # hueco es invisible y no hay forma de explicarlo después.
        #
        # La ÚNICA excepción, enumerada a propósito en vez de aflojar la regla (M122):
        # `financiero_limpiar_flujo`, el reset masivo para tirar datos de prueba o una
        # importación equivocada. Es otra cosa: admin, con confirmación explícita en el cuerpo
        # y auditado. No borra "un" movimiento: vacía la tabla a sabiendas.
        por_registro = [m.group(0) for m in
                        _re.finditer(r"DELETE\s+FROM\s+flujo_egresos\s+WHERE[^\"')]*", limpio, _re.I)]
        assert not por_registro, \
            '%s borra UNA fila del libro de egresos · se compensa, no se borra: %s' % (rel, por_registro)
