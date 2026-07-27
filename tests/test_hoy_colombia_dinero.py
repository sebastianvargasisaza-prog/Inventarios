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


def test_la_ventana_nocturna_no_corre_la_fecha_un_dia():
    """El caso exacto: 19:30 en Colombia el último día del mes."""
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
    s = io.open(os.path.join(raiz, 'api', 'blueprints', 'compras.py'), encoding='utf-8').read()
    i = s.find('INSERT INTO flujo_egresos')
    assert i > 0, 'no existe el INSERT a flujo_egresos'
    ctx = s[max(0, i - 700):i + 400]
    assert 'periodo_egr' in ctx and "(fecha_pago or '')[:7]" in ctx, (
        'el período del egreso volvió a salir del reloj en vez de la fecha del pago')


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
