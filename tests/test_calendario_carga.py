# -*- coding: utf-8 -*-
"""El calendario CARGA · ningún acceso a un elemento que ya no existe (4-ago).

Lo rompí yo, y es exactamente el patrón que estuve arreglando todo el día. Al retirar el
autoplan borré los BOTONES y dejé vivo el código que los toca: `cargar()` hacía
`document.getElementById('btn-aplicar').disabled = true` en su primera línea útil, reventaba con
**"Cannot set properties of null (setting 'disabled')"**, y la pantalla entera quedaba en *"No se
pudo cargar el calendario"*.

**Podar es borrar el PAR completo** (M112). Y esto el node-check NO lo ve: `getElementById` sobre
un id inexistente es sintaxis perfectamente válida — el error sólo aparece al EJECUTAR, o sea en
la pantalla del usuario.

Este trinquete recorre el JS renderizado y verifica que todo `getElementById('x').algo` sin
guardar apunte a un `id="x"` que de verdad se crea. Es barato y caza la clase entera.
"""
import ast
import io
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _js(rel, minimo=100000):
    """El JS RENDERIZADO, no el fuente crudo (M65)."""
    src = io.open(os.path.join(RAIZ, rel), encoding='utf-8').read()
    grandes = [v.value for n in ast.walk(ast.parse(src)) for v in ast.walk(n)
               if isinstance(v, ast.Constant) and isinstance(v.value, str)
               and len(v.value) > minimo]
    assert grandes, 'no encontré el template de %s' % rel
    return max(grandes, key=len)


def _ids_creados(rel):
    """Los ids se buscan en el ARCHIVO ENTERO, no sólo en el string más grande.

    La primera versión miraba únicamente el template mayor y acusaba como inexistentes a decenas
    de ids que se crean en otros bloques del mismo archivo: un guard con falsos positivos deja
    de mirarse, que es peor que no tenerlo."""
    src = io.open(os.path.join(RAIZ, rel), encoding='utf-8').read()
    return (set(re.findall(r'id="([\w-]+)"', src))
            | set(re.findall(r"id='([\w-]+)'", src))
            | set(re.findall(r'id=\\"([\w-]+)\\"', src)))


def _accesos_sin_guardar(rel, minimo=100000):
    """`getElementById('x').algo` directo · sin `?.` y sin haber pasado por una variable."""
    js = _js(rel, minimo)
    ids = _ids_creados(rel)
    malos = []
    for m in re.finditer(r"document\.getElementById\('([\w-]+)'\)\s*(\??\.)", js):
        _id, op = m.group(1), m.group(2)
        if op == '?.':
            continue           # opcional · no revienta
        if _id in ids:
            continue           # el elemento existe
        # Hay más formas de guardar que `?.`, y este código usa las tres. Si no se reconocen,
        # el guard acusa a decenas de líneas sanas y se vuelve ruido:
        #   ·  X ? X.value : ''      (ternario)
        #   ·  (X || {}).value       (respaldo)
        #   ·  var v = X; if (v) …   (variable chequeada)
        antes = js[max(0, m.start() - 40):m.start()]
        ctx = js[max(0, m.start() - 260):m.end() + 260]
        if antes.rstrip().endswith('(') and '||' in js[m.end():m.end() + 12]:
            continue           # (X || {}).algo
        if ("getElementById('" + _id + "')?") in ctx:
            continue           # X ? X.algo : ...
        if re.search(r"(var|let|const)\s+(\w+)\s*=\s*document\.getElementById\('"
                     + re.escape(_id) + r"'\)", ctx) and 'if (' in ctx:
            continue           # variable chequeada
        malos.append(_id)
    return sorted(set(malos))


def test_el_calendario_no_toca_elementos_que_no_existen():
    """El fallo concreto: "Cannot set properties of null (setting 'disabled')" dejaba la
    pantalla entera en "No se pudo cargar el calendario"."""
    malos = _accesos_sin_guardar('api/blueprints/plan.py')
    assert not malos, ('el calendario toca ids que no existen y eso tumba la carga entera: %s'
                       % malos)


def test_el_dashboard_no_EMPEORA():
    """El dashboard arrastra accesos de este tipo desde antes de hoy · no son de esta tanda y
    arreglarlos a las corridas, con el calendario caído, era la prioridad equivocada.

    Se fija el número actual como techo para que no CREZCA, y queda anotado como deuda: el
    detector no distingue todavía los ids que se crean por `innerHTML` en otro template, así que
    parte de estos pueden ser falsos positivos. Un techo honesto vale más que un guard que
    grita y nadie mira (M104: probar que muerde antes de creerle)."""
    malos = _accesos_sin_guardar('api/templates_py/dashboard_html.py', 500000)
    assert len(malos) <= 20, ('el dashboard sumó accesos a ids inexistentes (%d): %s'
                              % (len(malos), malos))


def test_los_restos_del_autoplan_estan_GUARDADOS():
    """Con dientes sobre el caso exacto que rompió: si alguien vuelve a poner el acceso
    directo, esto falla."""
    js = _js('api/blueprints/plan.py')
    assert "document.getElementById('btn-aplicar').disabled" not in js, \
        'volvió el acceso directo que reventaba la carga'
    assert "document.getElementById('sugerencias-lista').innerHTML" not in js
    assert "document.getElementById('btn-ia-anual').style" not in js
    # y siguen guardados, no borrados: la función tiene que seguir funcionando si el botón vuelve
    assert '_btnAp0' in js and 'if (_btnAp0)' in js


def test_cargar_del_calendario_sigue_entera():
    """Con dientes al revés: guardar los accesos no puede haberse llevado la función."""
    js = _js('api/blueprints/plan.py')
    assert 'async function cargar()' in js or 'function cargar()' in js
    for fn in ('render', 'renderListaSugerencias'):
        assert 'function ' + fn + '(' in js, 'desapareció %s' % fn
