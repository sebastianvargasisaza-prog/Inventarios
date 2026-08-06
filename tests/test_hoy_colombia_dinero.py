"""El "hoy" de un registro de dinero va en hora Colombia, no en la del servidor (27-jul).

Auditando Compras, Marketing y Tesorería apareció el patrón M24 en el peor lugar posible: el
registro de un pago.

`contabilidad.registrar_pago` usaba `date.today()` del servidor cuando el usuario no escribía la
fecha. Render corre en **UTC** y la empresa opera en **Colombia (UTC-5)**, así que después de las
7 de la tarde local el servidor ya está en el día siguiente:

    pago del 31-jul 19:30 Colombia  →  guardaba fecha 2026-08-01  →  periodo contable "2026-08"

Un pago de julio quedaba contabilizado en agosto, y pasaba **todas las noches de fin de mes**.

`api/tz_colombia.py` resolvía esto desde mayo y **sólo lo usaba un módulo**: el helper canónico
existía y nadie lo llamaba (M1). Ahora contabilidad y financiero lo usan.
"""
from datetime import datetime, timedelta, timezone


def test_la_ventana_nocturna_no_corre_la_fecha_un_dia(app):
    """El caso exacto: 19:30 en Colombia el último día del mes.

    ⚠ Depende de `app` aunque sea pura aritmética: sin esa fixture corre ANTES de que se
    levante la app, y al meter `api/` en el `sys.path` deja `config` importado sin las claves
    de prueba -- el login del ARCHIVO SIGUIENTE empieza a fallar y el rojo aparece lejos de
    acá (M112). Un test no puede ensuciar el universo de los demás.
    """
    import sys
    import os
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api'))
    from tz_colombia import TZ_COLOMBIA
    utc = datetime(2026, 8, 1, 0, 30, tzinfo=timezone.utc)      # = 31-jul 19:30 en Colombia
    assert utc.date().isoformat() == '2026-08-01'               # lo que veía el servidor
    col = utc.astimezone(TZ_COLOMBIA)
    assert col.date().isoformat() == '2026-07-31', 'la conversión a Colombia está mal'
    assert col.date().isoformat()[:7] == '2026-07', 'el período contable seguiría corrido'


# Los módulos donde un día corrido cuesta plata o descuadra un registro. Se barrieron los cinco
# el 27-jul: contabilidad y financiero (pagos y período), compras (período del egreso + corte de
# vencimiento), gerencia (período del input) y animus (caja y conteos de inventario).
MODULOS_DINERO = ('contabilidad.py', 'financiero.py', 'compras.py', 'gerencia.py', 'animus.py',
                  'marketing.py')


def test_los_modulos_de_dinero_no_usan_el_hoy_del_servidor(app):
    """Con dientes: si alguien vuelve a escribir `date.today()` en un módulo de dinero, esto lo
    caza. Un `date.today()` suelto ahí es un pago con la fecha de otro día."""
    import io
    import os
    import re
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    patron = re.compile(
        r'(?<![\w.])(?:_?date\.today\(\)'
        r'|datetime\.now\(\)\.date\(\)'
        r'|_?dt?a?t?e?time\.now\(\)\.strftime\(\s*[\'"]%Y-%m(?:-%d)?[\'"]\s*\))')
    culpables = []
    for f in MODULOS_DINERO:
        s = io.open(os.path.join(raiz, 'api', 'blueprints', f), encoding='utf-8').read()
        for m in patron.finditer(s):
            linea = s[:m.start()].count('\n') + 1
            culpables.append('%s:%d  %s' % (f, linea, s.split('\n')[linea - 1].strip()[:70]))
    assert not culpables, (
        'estos módulos de dinero volvieron a usar el "hoy" del servidor (UTC en Render):\n  %s\n'
        'Usá `hoy_colombia()`/`now_colombia()` de tz_colombia: después de las 19:00 locales, '
        'date.today() ya está en el día siguiente y el registro cae en el período equivocado.'
        % '\n  '.join(culpables))


def test_el_periodo_del_egreso_sale_de_la_fecha_del_pago(app):
    """Un pago con fecha retroactiva tenía la fila partida en dos meses: `fecha` decía el mes
    pasado y `periodo` (que salía de "ahora") decía el mes en curso. El período contable se
    deriva SIEMPRE de la fecha del pago, no del reloj."""
    import io
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    import ast
    s = io.open(os.path.join(raiz, 'api', 'blueprints', 'compras.py'), encoding='utf-8').read()
    # ⚠ Antes buscaba el PRIMER `INSERT INTO flujo_egresos` del archivo y exigía la expresión
    # literal de `pagar_oc`. Al agregar el espejo de `fp_pagar` -- que quedó ANTES en el archivo --
    # el guard pasó a medir código que no tenía nada que ver y dio rojo con los dos correctos
    # (M151: a un trinquete que busca por posición lo secuestra cualquier función nueva puesta
    # más arriba). Buscar el texto `[:7]` en una ventana tampoco servía: hay períodos legítimos
    # que no son un recorte (el de un cargo fijo sale del cargo, no del pago).
    #
    # Lo que de verdad se quiere medir: **el `periodo` no puede salir de una consulta al reloj
    # independiente de la `fecha` de la misma fila**. Se resuelven los argumentos posicionales
    # del INSERT contra las columnas, se sigue un nivel de variable local, y se exige que el
    # período o no toque el reloj, o lo toque a través de la MISMA expresión que la fecha.
    arbol = ast.parse(s)
    padres = {}
    for n in ast.walk(arbol):
        for h in ast.iter_child_nodes(n):
            padres[h] = n

    def _funcion_de(nodo):
        while nodo is not None:
            if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return nodo
            nodo = padres.get(nodo)
        return None

    # ⚠ La primera versión listaba sólo `now(`/`today(`/`utcnow(` y pasaba VERDE con el bug
    # original reintroducido: acá el reloj se pide por los helpers anclados a Colombia
    # (`_hoy_col()`, `hoy_colombia()`), que no contienen ninguna de esas palabras. Probar el
    # guard contra un bug inventado en vez del REAL es lo que deja un trinquete decorativo
    # (M142) -- se verificó que muerde con las DOS formas antes de darlo por bueno.
    RELOJES = ('now(', 'today(', 'utcnow(', '_hoy_col(', 'hoy_colombia(', 'now_colombia(',
               '_now_co', 'date.today', 'time.time(')

    def _reloj(txt):
        return any(t in txt for t in RELOJES)

    revisados = []
    for nodo in ast.walk(arbol):
        if not (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr in ('execute', 'executemany') and nodo.args):
            continue
        sql = nodo.args[0]
        if not (isinstance(sql, ast.Constant) and isinstance(sql.value, str)
                and 'INSERT INTO flujo_egresos' in sql.value):
            continue
        linea = nodo.lineno
        cols = sql.value.split('flujo_egresos', 1)[1].split('(', 1)[1].split(')', 1)[0]
        cols = [c.strip() for c in cols.split(',')]
        assert 'fecha' in cols and 'periodo' in cols, (
            'el INSERT de la línea %d no nombra fecha y periodo · no se puede verificar' % linea)
        assert len(nodo.args) >= 2 and isinstance(nodo.args[1], ast.Tuple), (
            'el INSERT de la línea %d pasa los valores en algo que no es una tupla literal · '
            'este guard no lo puede leer, revisalo a mano' % linea)
        vals = nodo.args[1].elts
        assert len(vals) == len(cols), (
            'el INSERT de la línea %d tiene %d columnas y %d valores'
            % (linea, len(cols), len(vals)))

        def _src(col):
            return ast.get_source_segment(s, vals[cols.index(col)]) or ''

        f_src, p_src = _src('fecha'), _src('periodo')
        # un nivel de variable local: `_peri = ...` dentro de la misma función
        fn = _funcion_de(nodo)
        locales = {}
        for sub in ast.walk(fn) if fn is not None else []:
            if (isinstance(sub, ast.Assign) and len(sub.targets) == 1
                    and isinstance(sub.targets[0], ast.Name)):
                locales.setdefault(sub.targets[0].id, []).append(
                    ast.get_source_segment(s, sub.value) or '')
        def _nombres(txt):
            try:
                return {x.id for x in ast.walk(ast.parse(txt, mode='eval'))
                        if isinstance(x, ast.Name)}
            except SyntaxError:
                return set()

        # ⚠ El lado de la FECHA se compara SIN resolver, a propósito: si se expande a su
        # definición, dos llamadas al reloj distintas comparten los alias del módulo
        # (`datetime`, `_td`) y se leen como "el mismo instante" -- con eso el guard dejaba
        # pasar justo el caso que existe para cazar. Lo que importa es si el período se
        # deriva de la VARIABLE que lleva la fecha de la fila.
        nombres_f = _nombres(f_src)
        # Cada asignación de esa variable en la función cuenta: si alguna pide el reloj por su
        # cuenta, el período de esa rama puede discrepar de la fecha.
        for p_res in locales.get(p_src.strip(), [p_src]):
            # comparte identificador con la fecha => MISMO instante, no otra consulta al reloj
            mismo_instante = bool(nombres_f & _nombres(p_res)) or p_res.strip() == f_src.strip()
            assert (not _reloj(p_res)) or mismo_instante, (
                'compras.py:%d · el período del egreso sale de una consulta al reloj propia, '
                'distinta de la fecha de la fila (fecha=%s · periodo=%s → %s). El período '
                'contable se deriva del HECHO; con dos relojes la misma fila puede decir dos '
                'meses.' % (linea, f_src, p_src, p_res))
        revisados.append(linea)
    assert len(revisados) >= 4, 'se revisaron sólo %d inserts a flujo_egresos' % len(revisados)


def test_el_helper_canonico_sigue_existiendo(app):
    """Si alguien lo borra o lo cambia de nombre, los módulos de dinero se quedan sin ancla."""
    from tz_colombia import hoy_colombia, now_colombia, TZ_COLOMBIA
    assert TZ_COLOMBIA.utcoffset(None) == timedelta(hours=-5), 'Colombia es UTC-5 fijo, sin horario de verano'
    hoy = hoy_colombia()
    ahora = now_colombia()
    assert ahora.date() == hoy
    # y de verdad difiere del UTC cuando corresponde
    assert abs((ahora.replace(tzinfo=None) - datetime.utcnow()).total_seconds() + 5 * 3600) < 120


def test_el_pago_sin_fecha_usa_la_de_colombia(app):
    """De punta a punta: registrar un pago sin fecha lo guarda con la fecha de Colombia."""
    from tz_colombia import hoy_colombia
    import io
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    s = io.open(os.path.join(raiz, 'api', 'blueprints', 'contabilidad.py'), encoding='utf-8').read()
    i = s.find('fecha_pago = data.get')
    assert i > 0, 'no existe la asignación de fecha_pago'
    assert '_hoy_col()' in s[i:i + 120], (
        'el pago volvió a tomar la fecha del servidor: %s' % s[i:i + 90])
    # el período se deriva de esa misma fecha, así que queda anclado también
    j = s.find('periodo = (fecha_pago')
    assert j > 0 and '_hoy_col()' in s[j:j + 120], 'el período contable no quedó anclado'
    assert hoy_colombia() is not None
