# -*- coding: utf-8 -*-
"""Una fila de la cola de marcación es una ORDEN DE TRABAJO: una por envase, no por presentación.

Sebastián (12-ago), mirando `Compras › Envases a marcar`: cinco filas seguidas de LIP SERUM, todas
de 214 unidades, todas apuntando al MISMO frasco `MEE-ENV-016`. Son los cinco tonos, que comparten
frasco -- pero cada fila trae su propio botón "Generar OC" y su "Solicitar alistamiento". Si actúa
sobre las cinco, pide cinco veces el mismo frasco, y la pantalla no tiene cómo darse cuenta.

Esto es lo que hay que cerrar ANTES de convertir la pantalla en el lugar donde Catalina decide
cómo se envasa cada producción: una pantalla de decisión construida sobre filas que mienten
produce decisiones equivocadas más rápido.
"""
import pytest

TEST_PASSWORD = "TestPass123"
PROD = "COLAGRUP TEST SERUM"


@pytest.fixture
def compras_client(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "catalina", "password": TEST_PASSWORD},
               headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar(app):
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre LIKE 'COLAGRUP TEST%'")
        c.execute("DELETE FROM produccion_programada WHERE producto LIKE 'COLAGRUP TEST%'")
        c.execute("DELETE FROM sku_producto_map WHERE producto_nombre LIKE 'COLAGRUP TEST%'")
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE 'CG-%'")
        conn.commit()


def _sembrar(app):
    """Tres tonos que COMPARTEN frasco + uno con frasco propio."""
    from datetime import datetime, timedelta
    _f = (datetime.utcnow() + timedelta(days=30)).date().isoformat()
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        for cod, desc in (('CG-COMUN', 'Frasco 10 ml comun'), ('CG-PROPIO', 'Frasco 10 ml propio')):
            c.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual, estado) "
                      "VALUES (?,?,'Envase',0,'Activo')", (cod, desc))
        for pc, etq, env in (('T-A', 'Tono A', 'CG-COMUN'), ('T-B', 'Tono B', 'CG-COMUN'),
                             ('T-C', 'Tono C', 'CG-COMUN'), ('T-D', 'Tono D', 'CG-PROPIO')):
            c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                      " etiqueta, volumen_ml, envase_codigo, activo) VALUES (?,?,?,10,?,1)",
                      (PROD, pc, etq, env))
        c.execute("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, "
                  " estado, origen) VALUES (?,?,?,'pendiente','eos_plan')", (PROD, _f, 4.0))
        conn.commit()
        return c.lastrowid


def test_un_frasco_compartido_por_tres_tonos_sale_UNA_vez_con_la_suma(app, compras_client):
    """El defecto exacto de la captura: tres filas del mismo frasco con tres botones de compra."""
    _limpiar(app); _sembrar(app)
    r = compras_client.get('/api/programacion/serigrafia-cola')
    assert r.status_code == 200, r.get_data(as_text=True)[:250]
    filas = [x for x in (r.get_json().get('items') or []) if x.get('producto') == PROD]
    comunes = [x for x in filas if (x.get('envase_codigo') or '').upper() == 'CG-COMUN']
    assert len(comunes) == 1, \
        'el mismo frasco salio %d veces: actuar sobre cada fila lo pide %d veces' % (
            len(comunes), len(comunes))
    # y el número de la fila única es la SUMA, no el de una sola presentación
    propios = [x for x in filas if (x.get('envase_codigo') or '').upper() == 'CG-PROPIO']
    if propios and comunes[0]['unidades'] and propios[0]['unidades']:
        assert comunes[0]['unidades'] > propios[0]['unidades'], \
            ('la fila agrupada trae las unidades de UNA presentacion, no la suma de las tres: '
             '%s vs %s' % (comunes[0]['unidades'], propios[0]['unidades']))


def test_la_fila_agrupada_DICE_que_presentaciones_cubre(app, compras_client):
    """Un total que agrupa sin enumerar lo que agrupa obliga a desconfiar del número (M124).

    Catalina tiene que poder ver que esas 3× unidades son Tono A + B + C antes de mandar la orden.
    """
    _limpiar(app); _sembrar(app)
    filas = [x for x in (compras_client.get('/api/programacion/serigrafia-cola')
                         .get_json().get('items') or []) if x.get('producto') == PROD]
    comunes = [x for x in filas if (x.get('envase_codigo') or '').upper() == 'CG-COMUN']
    assert comunes, 'no salio la fila del frasco compartido'
    cubre = comunes[0].get('cubre') or []
    assert len(cubre) >= 2, 'no dice que presentaciones cubre: %s' % (comunes[0],)
    assert 'Tono A' in cubre and 'Tono B' in cubre, 'la lista de lo que cubre esta incompleta: %s' % cubre


def test_un_frasco_usado_por_UNA_sola_presentacion_no_cambia(app, compras_client):
    """Agrupar no puede alterar el caso normal: una presentacion, una fila, su etiqueta propia."""
    _limpiar(app); _sembrar(app)
    filas = [x for x in (compras_client.get('/api/programacion/serigrafia-cola')
                         .get_json().get('items') or []) if x.get('producto') == PROD]
    propios = [x for x in filas if (x.get('envase_codigo') or '').upper() == 'CG-PROPIO']
    assert len(propios) == 1, 'el frasco de un solo tono salio %d veces' % len(propios)
    assert propios[0].get('etiqueta') == 'Tono D', \
        'le cambio la etiqueta a una fila que no agrupa nada: %r' % propios[0].get('etiqueta')
