# -*- coding: utf-8 -*-
"""Bodega, verificación y consumo tienen que decidir LO MISMO sobre cada lote · 21-ago-2026.

Sebastián, después del AZ HYBRID CLEAR: *"revisemos cómo está descontando y que sí esté enlazado
bodega con fabricación, verificación y consumos"*.

La cadena tiene tres caminos que miran los mismos lotes y deciden cosas distintas si divergen:

  1. `_lotes_de_material`          -> lo que la PANTALLA muestra como "lotes a usar"
  2. `_validar_stock_para_produccion` -> el gate que decide si se puede arrancar ("FALTA 4000g")
  3. `_distribuir_fefo`            -> lo que REALMENTE se descuenta del kardex

Cuando dos de los tres no coinciden pasa lo que Sebastián vio: la misma fila diciendo
"disponible 0g" y "lotes a usar: 29.137,5g" a la vez. Y la forma peligrosa es la contraria: que
el gate diga "alcanza" y la distribución no encuentre de dónde sacarlo, o que se consuma un lote
que la pantalla mostraba como retenido.

Este archivo NO prueba una función: prueba que las tres coinciden, sembrando de una vez todos
los casos que hacen dudar a un lote (vencido por fecha aunque el cron no lo marcó, cuarentena,
fecha ilegible, sin fecha). Es el guard de la INVARIANTE, no de la implementación (M232).
"""
import os
import sqlite3

_COD = 'MP-CADENA-TEST'
_NOM = 'MP CADENA COHERENTE'

# (lote, cantidad, estado, fecha_vencimiento, se_puede_usar)
_CASOS = [
    ('CAD-OK-FUTURO', 1000.0, 'VIGENTE', '2030-01-15', True),
    ('CAD-OK-SINFECHA', 500.0, 'VIGENTE', '', True),
    # El cron de vencidos corre una vez al día: entre que un lote vence y el cron pasa, el
    # estado sigue diciendo VIGENTE. El consumo se defiende por la FECHA cruda (M25).
    ('CAD-VENCIDO', 800.0, 'VIGENTE', '2020-03-01', False),
    ('CAD-CUARENTENA', 900.0, 'CUARENTENA', '2030-01-15', False),
    # Lo que destapó el caso del 21-ago: con la fecha en texto, date() da NULL y el motor lo
    # excluye. La pantalla tiene que decir lo mismo, o promete material que no se va a usar.
    ('CAD-ILEGIBLE', 700.0, 'VIGENTE', 'proximamente', False),
]

_USABLES_G = sum(c for (_l, c, _e, _f, ok) in _CASOS if ok)


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.fetchall()
    finally:
        conn.close()


def _limpiar():
    """Limpieza ANTES de sembrar, con códigos FIJOS: idempotente por construcción (M103)."""
    _sql("DELETE FROM movimientos WHERE material_id=?", (_COD,))
    _sql("DELETE FROM maestro_mps WHERE codigo_mp=?", (_COD,))


def _sembrar():
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_inci, activo) VALUES (?,?,1)", (_COD, _NOM))
    for lote, cant, estado, fv, _ok in _CASOS:
        _sql("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, "
             "lote, fecha_vencimiento, estado_lote) VALUES (?,?,?,'Entrada',?,?,?,?)",
             (_COD, _NOM, cant, '2026-01-10', lote, fv, estado))


def test_pantalla_gate_y_descuento_ven_los_MISMOS_lotes(app, db_clean):
    """La invariante que faltaba el 21-ago: los tres caminos coinciden lote por lote."""
    _sembrar()
    try:
        with app.app_context():
            from api.database import get_db
            from api.blueprints.programacion import (_lotes_de_material,
                                                     _validar_stock_para_produccion,
                                                     _distribuir_fefo)
            cur = get_db().cursor()
            vista = _lotes_de_material(cur, _COD)
            # Se pide MÁS de lo que hay usable para que la distribución tenga que tocar todos
            # los lotes que considera consumibles.
            reparto = _distribuir_fefo(cur, _COD, _USABLES_G)
            faltan_justo = _validar_stock_para_produccion(
                cur, [{'codigo_mp': _COD, 'nombre': _NOM, 'cantidad_g': _USABLES_G}])
            faltan_de_mas = _validar_stock_para_produccion(
                cur, [{'codigo_mp': _COD, 'nombre': _NOM, 'cantidad_g': _USABLES_G + 1000}])

        esperados = set(l for (l, _c, _e, _f, ok) in _CASOS if ok)
        prohibidos = set(l for (l, _c, _e, _f, ok) in _CASOS if not ok)

        # 1 · la PANTALLA
        en_vista = set(x['lote'] for x in vista['usables'])
        assert en_vista == esperados, (
            "la pantalla muestra como usables %s y los usables son %s"
            % (sorted(en_vista), sorted(esperados)))
        # y lo que no se puede usar se DECLARA con su motivo, no desaparece (M124)
        retenidos = dict((x['lote'], x.get('motivo', '')) for x in vista['retenidos'])
        for lote in prohibidos:
            assert lote in retenidos, "el lote %s desapareció en vez de declararse" % lote
            assert retenidos[lote].strip(), "el lote %s no dice POR QUÉ no se puede usar" % lote

        # 2 · el DESCUENTO real
        en_reparto = set(d.get('lote') for d in reparto if d.get('lote') and not d.get('sin_lote'))
        assert not (en_reparto & prohibidos), (
            "el descuento iba a consumir lotes que la pantalla da por retenidos: %s"
            % sorted(en_reparto & prohibidos))
        assert en_reparto == esperados, (
            "el descuento toma %s y la pantalla promete %s" % (sorted(en_reparto), sorted(esperados)))

        # 3 · el GATE de arranque
        assert not faltan_justo, (
            "el gate dice que falta pidiendo exactamente lo usable (%s g): %r"
            % (_USABLES_G, faltan_justo))
        assert faltan_de_mas, "el gate dejó arrancar pidiendo más de lo que hay usable"
    finally:
        _limpiar()


def test_el_gate_no_deja_arrancar_con_lo_que_el_descuento_no_puede_sacar(app, db_clean):
    """La forma PELIGROSA de la divergencia: "validó pero no alcanzó".

    Si el gate contara el lote vencido o el de cuarentena, dejaría arrancar una producción que
    después no puede descontar -- y ahí el lote queda a medias, con parte de la MP consumida.
    """
    _sembrar()
    try:
        with app.app_context():
            from api.database import get_db
            from api.blueprints.programacion import (_validar_stock_para_produccion,
                                                     _distribuir_fefo)
            cur = get_db().cursor()
            # Justo por encima de lo usable: el gate DEBE frenar.
            pedido = _USABLES_G + 0.5
            faltan = _validar_stock_para_produccion(
                cur, [{'codigo_mp': _COD, 'nombre': _NOM, 'cantidad_g': pedido}])
            # La distribución NO devuelve un faltante silencioso: LANZA. Está bien que sea así
            # (no inventa stock), y es lo que hay que verificar -- el contrato se lee del
            # código antes de usarlo (M220).
            from api.blueprints.programacion import _DescuentoError
            reventó = False
            try:
                _distribuir_fefo(cur, _COD, pedido)
            except _DescuentoError:
                reventó = True
        assert faltan, "el gate dejó pasar %s g cuando sólo hay %s usables" % (pedido, _USABLES_G)
        assert reventó, (
            "la distribución aceptó sacar %s g con %s usables: estaría tomando de lotes "
            "retenidos o inventando stock" % (pedido, _USABLES_G))
    finally:
        _limpiar()


def test_el_FEFO_saca_primero_el_que_vence_antes(app, db_clean):
    """FEFO de verdad: el orden lo decide el vencimiento, y el lote sin fecha va al final.

    Importa para esta cadena porque el ORDEN es lo único que evita que se venza material que
    estaba disponible: si el sin-fecha saliera primero, el que caduca en marzo se queda.
    """
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_inci, activo) VALUES (?,?,1)", (_COD, _NOM))
    for lote, fv in (('CAD-F3', '2031-12-01'), ('CAD-F1', '2029-03-01'),
                     ('CAD-F2', '2030-06-01'), ('CAD-F0', '')):
        _sql("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, "
             "lote, fecha_vencimiento, estado_lote) VALUES (?,?,?,'Entrada',?,?,?,'VIGENTE')",
             (_COD, _NOM, 100.0, '2026-01-10', lote, fv))
    try:
        with app.app_context():
            from api.database import get_db
            from api.blueprints.programacion import _distribuir_fefo, _lotes_de_material
            cur = get_db().cursor()
            reparto = _distribuir_fefo(cur, _COD, 350.0)
            vista = _lotes_de_material(cur, _COD)
        orden = [d['lote'] for d in reparto if d.get('lote') and not d.get('sin_lote')]
        assert orden[:3] == ['CAD-F1', 'CAD-F2', 'CAD-F3'], \
            "el FEFO no salió por vencimiento: %r" % (orden,)
        assert orden[-1] == 'CAD-F0', "el lote sin fecha no quedó al final: %r" % (orden,)
        # Y la pantalla los ofrece en el MISMO orden en que se van a consumir: si mostrara otro,
        # el operario bajaría del estante un lote distinto del que el kardex va a descontar.
        orden_vista = [x['lote'] for x in vista['usables']]
        assert orden_vista[:3] == ['CAD-F1', 'CAD-F2', 'CAD-F3'], \
            "la pantalla ofrece otro orden que el descuento: %r" % (orden_vista,)
    finally:
        _limpiar()
