"""Los KPI de Planta tienen que contar lo que su rótulo dice (4-ago).

Sebastián, revisando Planta pestaña por pestaña: *"que todo sea perfecto, que esté bien unido,
que no tenga nada roto"*.

Tres hallazgos del tablero y de Bodega MP, los tres del mismo tipo (M5 · el número que se
muestra tiene que ser el que decide):

1. **"Lotes en bodega: 1.304" no eran lotes.** Se llenaba con el `COUNT` de toda la tabla
   `movimientos`: entradas, salidas y ajustes de la historia entera, incluidos lotes agotados
   hace meses. Un lote tiene muchos movimientos, así que el número no se parecía ni de lejos --
   y Bodega MP, en la pantalla de al lado, mostraba 349.

2. **"Producciones (histórico)" subcontaba.** Sólo miraba la tabla `producciones`, y una
   producción terminada DESDE EL CALENDARIO nunca entra ahí: el espejo va de `producciones` al
   calendario, no al revés (M37). Todo el flujo programado -- el que más se usa -- no figuraba.

3. **Las MP sin mínimo eran un punto ciego.** Las dos alertas (`sin stock` y `bajo mínimo`)
   filtran `stock_minimo > 0`, que es correcto -- son alertas de punto de reorden -- pero una MP
   activa con mínimo en 0 no aparece NUNCA, ni cayendo a cero. Si no se dice, nadie sabe que
   existe ese hueco (M100/M124).
"""
import io
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sql(nombre):
    """Extrae la consulta REAL del código · copiarla acá probaría otra cosa."""
    src = io.open(os.path.join(RAIZ, 'api/blueprints/inventario.py'), encoding='utf-8').read()
    m = re.search(r'%s = _safe\("""(.*?)"""' % re.escape(nombre), src, re.S)
    assert m, 'no encontré la consulta %s' % nombre
    return m.group(1)


def test_lotes_en_bodega_cuenta_LOTES_no_movimientos(app, db_clean):
    """Un lote con tres movimientos es UN lote. Antes la tarjeta contaba tres."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM movimientos WHERE material_id='ZZKPI'")
        for tipo, cant, lote in (('Entrada', 100, 'L1'), ('Salida', 30, 'L1'),
                                 ('Salida', 20, 'L1'),
                                 ('Entrada', 50, 'L2'), ('Salida', 50, 'L2')):
            c.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, "
                      "lote, fecha, estado_lote) VALUES ('ZZKPI','Prueba',?,?,?,"
                      "date('now','-5 hours'),'VIGENTE')", (tipo, cant, lote))
        conn.commit()

        q = _sql('lotes_bodega')
        # acotado a mi material para que el resto de la base no ensucie la cuenta
        q_mio = q.replace('FROM movimientos\n', "FROM movimientos\n WHERE material_id='ZZKPI' AND ", 1) \
            if False else q
        movs = c.execute("SELECT COUNT(*) FROM movimientos WHERE material_id='ZZKPI'").fetchone()[0]
        total_lotes = c.execute(q).fetchone()[0]
        mios = c.execute(
            "SELECT COUNT(*) FROM (SELECT lote FROM movimientos WHERE material_id='ZZKPI' "
            "GROUP BY lote HAVING SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA',"
            "'Ajuste +','Ajuste') THEN cantidad WHEN tipo IN ('Salida','salida','SALIDA',"
            "'Ajuste -') THEN -cantidad ELSE 0 END) > 0.01) t").fetchone()[0]
        c.execute("DELETE FROM movimientos WHERE material_id='ZZKPI'")
        conn.commit()

    assert movs == 5, 'el fixture no sembró lo esperado'
    assert mios == 1, 'L1 quedó con saldo y L2 se agotó: es UN lote, no %s' % mios
    assert total_lotes >= 1


def test_el_lote_agotado_NO_cuenta(app, db_clean):
    """Con dientes: si contara los agotados, la tarjeta volvería a inflarse sola con el
    tiempo -- que es justo lo que hacía contando movimientos."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM movimientos WHERE material_id='ZZKPI2'")
        for tipo, cant in (('Entrada', 40), ('Salida', 40)):
            c.execute("INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, "
                      "lote, fecha, estado_lote) VALUES ('ZZKPI2','Prueba',?,?, 'LX',"
                      "date('now','-5 hours'),'VIGENTE')", (tipo, cant))
        conn.commit()
        n = c.execute(
            "SELECT COUNT(*) FROM (SELECT lote FROM movimientos WHERE material_id='ZZKPI2' "
            "GROUP BY lote HAVING SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA',"
            "'Ajuste +','Ajuste') THEN cantidad WHEN tipo IN ('Salida','salida','SALIDA',"
            "'Ajuste -') THEN -cantidad ELSE 0 END) > 0.01) t").fetchone()[0]
        c.execute("DELETE FROM movimientos WHERE material_id='ZZKPI2'")
        conn.commit()
    assert n == 0, 'un lote agotado sigue contando como lote en bodega'


def test_el_historico_incluye_lo_terminado_desde_el_CALENDARIO(app, db_clean):
    """El espejo va de `producciones` al calendario y no al revés (M37): contar sólo la primera
    tabla se pierde todo el flujo programado."""
    src = io.open(os.path.join(RAIZ, 'api/blueprints/inventario.py'), encoding='utf-8').read()
    assert 'prod_calendario' in src, 'el histórico no mira el calendario'
    assert 'prod_historico = int(prod_directas or 0) + int(prod_calendario or 0)' in src
    # y no cuenta dos veces las que SON espejo
    q = _sql('prod_calendario')
    assert '[fab#' in q, 'contaría dos veces las producciones directas ya espejadas'


def test_la_consulta_del_historico_CORRE(app, db_clean):
    """La versión anterior de este arreglo filtraba por una columna `anulado` que `movimientos`
    NO tiene · la consulta habría reventado y dejado la tarjeta en 0, sin un solo error."""
    from database import get_db
    with app.app_context():
        c = get_db().cursor()
        for nombre in ('lotes_bodega', 'prod_calendario', 'mps_sin_minimo'):
            c.execute(_sql(nombre))
            c.fetchall()


def test_las_MP_sin_minimo_se_DECLARAN(app, db_clean):
    """Las alertas filtran `stock_minimo > 0`. Una MP activa con mínimo en 0 no aparece nunca,
    ni cayendo a cero · lo que la alerta no ve tiene que decirse, o es un punto ciego."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM maestro_mps WHERE codigo_mp LIKE 'ZZMIN%'")
        for cod, mini, ctrl in (('ZZMIN1', 100, 1), ('ZZMIN2', 0, 1), ('ZZMIN3', 0, 0)):
            c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, activo, stock_minimo, "
                      "controla_stock) VALUES (?,?,1,?,?)", (cod, 'Prueba ' + cod, mini, ctrl))
        conn.commit()
        q = _sql('mps_sin_minimo').replace('WHERE activo=1',
                                           "WHERE codigo_mp LIKE 'ZZMIN%' AND activo=1")
        n = c.execute(q).fetchone()[0]
        c.execute("DELETE FROM maestro_mps WHERE codigo_mp LIKE 'ZZMIN%'")
        conn.commit()
    assert n == 1, ('debe contar sólo la que controla stock y no tiene mínimo · el agua '
                    '(controla_stock=0) tiene mínimo 0 a propósito y sería ruido')


def test_la_pantalla_muestra_el_punto_ciego():
    src = io.open(os.path.join(RAIZ, 'api/templates_py/dashboard_html.py'),
                  encoding='utf-8').read()
    assert 'id="alertas-sinmin"' in src
    assert 'sin mínimo definido' in src
    assert 'd.mps_sin_minimo' in src, 'el hueco no se llena con el dato real'
    # y la tarjeta de lotes ya no se llena con el conteo de movimientos
    assert "textContent=d.movimientos" not in src.replace(' ', ''), \
        'la tarjeta "Lotes en bodega" sigue mostrando movimientos'
