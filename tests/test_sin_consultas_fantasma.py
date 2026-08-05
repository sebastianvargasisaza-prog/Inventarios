"""Ninguna consulta puede nombrar una tabla o columna que no existe (4-ago).

Es el patrón que más veces apareció en el cerebro (M12a · M26 · M87 · M94 · M96): una consulta
que nombra algo inexistente, envuelta en un `except`, **no da error** -- devuelve vacío. La
feature queda muerta y su pantalla se ve exactamente igual que "no hay datos todavía".

La revisión del 4-ago encontró cinco así, todas invisibles a la vista:

  · el bloque **Dirección Técnica del tablero del CEO** nombraba TRES tablas que no existen
    (`formulas_maestras`, `registros_invima`, `documentos_sgd`) -- el bloque salía vacío;
  · el **último precio** y el **top de proveedores** de una materia prima pedían
    `precios_mp_historico.precio_unitario`, y esa tabla tiene `precio_kg`;
  · la lista de **pagos** de la trazabilidad de una OC pedía `pagos_oc.fecha`, que es
    `fecha_pago`;
  · el resumen de **cotizaciones** pedía `cotizaciones.fecha_creacion`, que es
    `fecha_solicitud`.

Leerlas no alcanza: hay que EJECUTARLAS contra el esquema real. Eso es lo que hace este test.
"""
import ast
import io
import os
import re

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODULOS = [
    'api/blueprints/animus.py',
    'api/blueprints/bienestar.py',
    'api/blueprints/hub.py',
    'api/blueprints/compras.py',
    'api/blueprints/rrhh.py',
]

# Endpoints que quedaron de features retiradas (los agentes de IA de marketing): nadie los
# llama desde ninguna pantalla y nombran tablas que nunca existieron. Se enumeran para que el
# trinquete no los reporte cada corrida -- pero quedan ANOTADOS, no escondidos.
MUERTOS_CONOCIDOS = ('liberaciones', 'formulas_maestras')

# Dos casos que NO son bugs y que el trinquete tiene que dejar pasar, o se vuelve ruido (M122):
#   · la SONDA de esquema de compras: prueba `precio_unitario` A PROPÓSITO para elegir qué
#     columna usar, y cae a `precio_kg`, que ya es el default correcto. Ese try/except SÍ es un
#     detector, no un tapón.
#   · los fragmentos donde el nombre de la tabla se concatena (`"FROM animus_" + tabla`).
EXCEPCIONES = (
    'SELECT precio_unitario FROM precios_mp_historico LIMIT 1',
    'FROM animus_ ',
)


def _consultas(src):
    """Las consultas COMPLETAS del archivo: con FROM propio y sin señales de concatenación.

    Un fragmento sin FROM no se puede ejecutar solo, y reportarlo sería ruido -- que es
    exactamente lo que hace que un guard deje de mirarse (M122).
    """
    qs = re.findall(r'"""(SELECT[^"]{20,900}?)"""', src, re.S)
    qs += re.findall(r'"(SELECT [^"]{20,700}?)"', src)
    out = []
    for q in qs:
        q = ' '.join(q.split())
        if ' FROM ' not in q.upper():
            continue
        if '{' in q or '%s' in q:
            continue                       # se arma con formato: no es literal
        if q.rstrip().upper().endswith(('WHERE', 'AND', 'OR', 'FROM', 'JOIN', 'ON', 'BY')):
            continue
        out.append(q)
    return out


@pytest.mark.parametrize('modulo', MODULOS)
def test_las_consultas_corren_contra_el_esquema_real(app, modulo):
    from database import get_db
    rotas = []
    src = io.open(os.path.join(RAIZ, modulo), encoding='utf-8').read()
    with app.app_context():
        c = get_db().cursor()
        for q in _consultas(src):
            if any(m in q for m in MUERTOS_CONOCIDOS):
                continue
            if any(e in (q + ' ') for e in EXCEPCIONES):
                continue
            try:
                c.execute(q, tuple([''] * q.count('?')))
                c.fetchall()
            except Exception as e:
                m = str(e)
                if 'no such column' in m or 'no such table' in m:
                    rotas.append('%s  ->  %s' % (m, q[:120]))
    assert not rotas, ('%s nombra cosas que no existen:\n  ' % modulo) + '\n  '.join(rotas)


def test_el_tablero_del_CEO_lee_tablas_que_existen(app):
    """El bloque de Dirección Técnica salía vacío porque nombraba tablas inexistentes, y el
    `except` lo tapaba: se leía como "no hay nada que mirar".

    ⚠ Corregido el 5-ago. Este guard tenía una **lista negra de nombres escrita a mano**, y
    `registros_invima` estaba en ella por error: la tabla SÍ existe — la crea
    `tecnica._init_tecnica()`, que corre al importar el blueprint (y `get_db()` cae a una
    conexión directa fuera de contexto, así que también se crea en producción). El guard daba
    rojo con el código correcto e impedía leer un dato real.

    Una lista de nombres a mano se pudre (M122). La invariante que de verdad importa no es
    "no nombres esta tabla" sino **"no muestres un número que no pudiste medir"**: por eso lo
    que se verifica ahora es que la lectura esté guardada y que degrade a `None` — que la
    pantalla distingue de un cero — en vez de a 0. Las dos tablas que sí eran fantasma en el
    hub siguen prohibidas. Y el chequeo duro lo hace el test de arriba, que EJECUTA cada
    consulta contra el esquema real."""
    src = io.open(os.path.join(RAIZ, 'api/blueprints/hub.py'), encoding='utf-8').read()
    for fantasma in ('FROM formulas_maestras', 'FROM documentos_sgd'):
        assert fantasma not in src, 'el tablero del CEO todavía nombra %s' % fantasma

    # `registros_invima` se puede leer, pero SIEMPRE guardada y degradando a None.
    i = src.find('FROM registros_invima')
    if i > 0:
        ventana = src[max(0, i - 700):i + 1400]
        assert 'except' in ventana, 'la lectura de registros INVIMA quedó sin guard'
        assert '_invima_vigentes, _invima_vencen = None, None' in ventana, \
            'si no se puede leer cae a 0 · un cero se lee como "ninguno vigente", que es lo ' \
            'contrario de "no pude mirar"'


def test_el_precio_historico_se_pide_por_su_nombre_real(app):
    """`precios_mp_historico` tiene `precio_kg` · y la unidad importa: meter un $/kg en un campo
    de $/g infla la orden 1000 veces (M83)."""
    src = io.open(os.path.join(RAIZ, 'api/blueprints/compras.py'), encoding='utf-8').read()
    for m in re.finditer(r'FROM\s+precios_mp_historico', src):
        contexto = src[max(0, m.start() - 700):m.start()]
        # La sonda deliberada se saltea: prueba la columna a propósito para elegir cuál usar.
        if 'descubrimiento' in contexto:
            continue
        tramo = contexto[-420:].split('c.execute')[-1]
        assert 'precio_unitario' not in tramo, \
            'una consulta a precios_mp_historico sigue pidiendo precio_unitario'
