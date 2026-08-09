# -*- coding: utf-8 -*-
"""Cuando el envase impreso no alcanza, la cola lo DICE.

Sebastián (9-ago): *"todo lo impreso va primero; cuando no alcanza, entonces debe decir se debe
enviar tal envase a serigrafía o solicitar etiqueta, y eso ya lo hace Catalina: ella revisa en
compras y solicita"*.

El circuito estaba montado (mandar a marcar, el envase limpio sale y vuelve con otro código, entra
en cuarentena y Calidad lo libera). Lo que faltaba era el DISPARADOR: la cola saltaba el envase
pre-impreso con un `continue` -- *"viene ya serigrafiado de China, no se alista ni envía a
marcar"* -- así que mientras alcanzara todo iba bien, y **el día que no alcanzara nadie se
enteraba**. No mandarlo a marcar no es lo mismo que no mirarlo.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

PROD = 'IMPRESO TEST SUERO'


def _sembrar(app, stock_impreso, uds_por_lote_kg=10.0, con_limpio=True):
    """Un producto cuyo envase viene impreso, con el stock que se le diga."""
    from database import get_db
    import datetime as _d
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'IMP-%'")
        c.execute("DELETE FROM movimientos_mee WHERE mee_codigo LIKE 'IMP-%'")
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual, "
                  "marcacion_tipo, material_referencia) VALUES "
                  "('IMP-IMPRESO','FRASCO 30ML IMPRESO CHINA','Frasco',0,'pre_impreso',?)",
                  ('IMP-LIMPIO' if con_limpio else '',))
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual) "
                  "VALUES ('IMP-LIMPIO','FRASCO 30ML LIMPIO','Frasco',0)")
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, envase_codigo, activo, es_default) "
                  "VALUES (?,'V30','30 ml',30,'IMP-IMPRESO',1,1)", (PROD,))
        if stock_impreso > 0:
            c.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, fecha, lote_ref) "
                      "VALUES ('IMP-IMPRESO','Entrada',?,?,'SEED')",
                      (stock_impreso, _d.date.today().isoformat()))
        f = (_d.date.today() + _d.timedelta(days=40)).isoformat()
        c.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, "
                  "estado, origen) VALUES (?,?,?, 'pendiente','eos_plan')",
                  (PROD, f, uds_por_lote_kg))
        c.commit()


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre=?", (PROD,))
        c.execute("DELETE FROM produccion_programada WHERE producto=?", (PROD,))
        c.execute("DELETE FROM movimientos_mee WHERE mee_codigo LIKE 'IMP-%'")
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'IMP-%'")
        c.commit()


def _cola(admin_client):
    r = admin_client.get('/api/programacion/serigrafia-cola')
    assert r.status_code == 200, r.data[:200]
    return [x for x in (r.get_json().get('items') or [])
            if str(x.get('producto', '')) == PROD]


def test_si_el_impreso_ALCANZA_no_molesta(app, admin_client):
    """Una alerta que suena también cuando no pasa nada deja de mirarse justo el día que importa
    (M129/M122). 10 kg de 30 ml son ~333 unidades: con 5.000 en bodega, sobra."""
    _sembrar(app, stock_impreso=5000)
    assert not _cola(admin_client), 'avisó teniendo impreso de sobra'
    _limpiar(app)


def test_si_el_impreso_NO_alcanza_lo_DICE_y_dice_QUE_mandar(app, admin_client):
    """Lo que Catalina necesita para actuar: cuántos faltan y qué envase mandar a marcar."""
    _sembrar(app, stock_impreso=100)          # hacen falta ~333
    filas = _cola(admin_client)
    assert filas, 'el impreso no alcanzaba y la cola no dijo nada'
    f = filas[0]
    assert f.get('impreso_no_alcanza') is True
    assert f.get('faltan', 0) > 0, 'no dice cuántos faltan'
    assert f.get('envase_limpio') == 'IMP-LIMPIO', \
        'no dice qué envase mandar a marcar: %s' % f
    assert f.get('accion') == 'enviar_a_serigrafiar'
    assert f.get('fecha_envio'), 'no dice para cuándo (producción menos 15 días)'
    # La fila es una ORDEN DE TRABAJO: la pantalla de Compras la usa para mandar a marcar. Si
    # trajera el envase IMPRESO (que ya viene marcado) o las unidades de la producción entera,
    # Catalina mandaría el frasco equivocado por la cantidad equivocada, y la pantalla no tendría
    # cómo darse cuenta.
    assert f.get('envase_codigo') == 'IMP-LIMPIO', \
        'la orden apunta al envase impreso, que ya viene marcado: %s' % f.get('envase_codigo')
    assert f.get('unidades') == f.get('faltan'), \
        'la orden pide las unidades de toda la producción, no las que faltan: %s vs %s' % (
            f.get('unidades'), f.get('faltan'))
    assert f.get('envase_impreso') == 'IMP-IMPRESO', 'no dice de qué impreso viene el faltante'
    assert f.get('unidades_produccion', 0) > f.get('faltan'), \
        'no conserva cuántas necesita la producción completa'
    _limpiar(app)


def test_si_no_hay_envase_limpio_anclado_lo_DECLARA(app, admin_client):
    """Sin el puente no se puede decir QUÉ mandar a marcar. Eso se dice; no se adivina un código
    parecido, que sería mandar a serigrafiar el frasco de otro producto (M19/M100)."""
    _sembrar(app, stock_impreso=100, con_limpio=False)
    filas = _cola(admin_client)
    assert filas, 'no avisó del faltante'
    f = filas[0]
    assert not f.get('envase_limpio')
    assert f.get('accion') in ('solicitar_etiqueta', 'sin_salida_definida')
    assert 'no' in (f.get('aviso') or '').lower(), 'no explica que le falta el puente'
    _limpiar(app)
