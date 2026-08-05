# -*- coding: utf-8 -*-
"""El modal del CALENDARIO tiene la MISMA cara que el de Necesidades (5-ago).

Sebastián: *"revisa que necesidades programar y calendario quedan como me los mostraste cuando
aprobamos, no los veo así"*.

Los dos modales ya compartían el CÁLCULO (mismo endpoint, misma respuesta). Lo que seguía
distinto era la CARA: el del calendario conservaba su estructura vieja y, encima, en un orden que
contestaba antes de preguntar — el selector de envase abría el modal (un detalle de
configuración) y el chequeo de materiales salía ANTES de que el usuario eligiera los kilos, o sea
respondiendo "alcanza" sobre un kilaje que todavía no había decidido.

La cara aprobada es: **veredicto en una línea → ① Cómo va → ② Qué decido (dominante) → ③ Con qué
cuento → ④ Qué queda agendado**.

⚠ Lo que este archivo vigila NO es la estética, es que el reordenamiento no se haya comido HTML:
borrar un `<div>` no rompe la sintaxis, así que el node-check pasa verde con la pantalla partida
(M112/M156). Por eso se cuentan las marcas conocidas y el balance de `<div>`.
"""
import io
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ① ② ③ ④ como entidades HTML · en el fuente van así para no meter un carácter que el
# navegador tenga que adivinar (y para que el diff sea legible en cualquier consola).
BLOQUES = ('&#9312;', '&#9313;', '&#9314;', '&#9315;')


def _cuerpo_del_modal():
    """El cuerpo de `abrirLoteModal`, que es la función que arma el modal del calendario."""
    s = io.open(os.path.join(RAIZ, 'api/blueprints/plan.py'), encoding='utf-8').read()
    i = s.find('async function abrirLoteModal(id, producto, fecha, kg){')
    assert i > 0, 'no encontré abrirLoteModal'
    j = s.find('function _saludCadenaCal(', i)
    assert j > i, 'no encontré el final de abrirLoteModal'
    return s[i:j]


def test_el_modal_del_calendario_tiene_los_CUATRO_bloques(app, db_clean):
    b = _cuerpo_del_modal()
    for n in BLOQUES:
        assert b.count(n) == 1, 'el bloque %s falta o está duplicado' % n
    # y en ORDEN · un modal que decide antes de mostrar cómo va no es el que se aprobó
    pos = [b.find(n) for n in BLOQUES]
    assert pos == sorted(pos), 'los cuatro bloques están, pero fuera de orden'


def test_el_veredicto_va_ANTES_del_primer_bloque(app, db_clean):
    """Lo primero que se lee: en cuántos días se agota y cuándo toca producir."""
    b = _cuerpo_del_modal()
    i_ver = b.find('20 antes de agotarse')
    assert i_ver > 0, 'el modal no abre con el veredicto en una línea'
    assert i_ver < b.find(BLOQUES[0]), 'el veredicto quedó después de ① Cómo va'
    assert 'hay que producir YA' in b, 'el veredicto no distingue el caso urgente'


def test_la_DECISION_es_el_bloque_dominante(app, db_clean):
    """Es el bloque por el que se abre el modal · antes tenía el mismo peso visual que los tres
    de información que lo rodeaban, así que la acción quedaba escondida entre datos."""
    b = _cuerpo_del_modal()
    i, fin = b.find(BLOQUES[1]), b.find(BLOQUES[2])   # ② … hasta ③
    assert 0 < i < fin
    ventana = b[i:fin]
    assert 'border-left:5px solid var(--cx-primary' in ventana, \
        'el contenedor de la decisión no está marcado como dominante'
    assert 'edit-kg-lote' in ventana, 'los kilos no están dentro del bloque de la decisión'
    assert 'cal-cm-preview' in ventana, 'la cadencia no está dentro del bloque de la decisión'


def _emisiones(b):
    """El ORDEN EN QUE SE PINTA, que no es el orden en que está escrito.

    ⚠ La primera versión de estos tests comparaba posiciones en el FUENTE y daba rojo con el
    código correcto: los bloques capturados en una variable se CONSTRUYEN arriba y se EMITEN
    abajo, que es justo la técnica que hace seguro el reordenamiento (M156). Lo que hay que
    medir es dónde entran a `html`."""
    return [(m.start(), m.group(0)) for m in re.finditer(r'\bhtml (?:\+=|=) [^\n]*', b)]


def _pinta_en(b, aguja):
    """Posición de la emisión que mete `aguja` en el html final."""
    for pos, linea in _emisiones(b):
        if aguja in linea:
            return pos
    return -1


def test_el_chequeo_de_materiales_se_PINTA_despues_de_decidir(app, db_clean):
    """Antes contestaba "alcanza" sobre un kilaje que el usuario todavía no había elegido.

    El chequeo se CONSTRUYE arriba (para no mover su código) pero se PINTA dentro del bloque ③,
    que va después de la decisión."""
    b = _cuerpo_del_modal()
    # se acumula en el bloque 3, no se pinta suelto
    assert 'lote-readiness' not in ''.join(l for _, l in _emisiones(b)), \
        'el chequeo de materiales vuelve a pintarse suelto, fuera del bloque ③'
    assert '_htmlConQue' in b[b.find('lote-readiness') - 400:b.find('lote-readiness') + 400], \
        'el chequeo de materiales no entra al acumulador del bloque ③'
    p3 = _pinta_en(b, '_htmlConQue')
    assert p3 > 0, 'el bloque ③ nunca se pinta'
    assert p3 > b.find(BLOQUES[1]), 'el bloque "con qué cuento" se pinta antes de decidir'


def test_el_envase_y_las_presentaciones_dejaron_de_ABRIR_el_modal(app, db_clean):
    """Un detalle de configuración no puede ser lo primero que se ve."""
    b = _cuerpo_del_modal()
    assert 'env-ovr-' not in ''.join(l for _, l in _emisiones(b)), \
        'el selector de envase se sigue pintando suelto arriba, no dentro del bloque ③'
    assert 'pres-box-' not in ''.join(l for _, l in _emisiones(b)), \
        'las presentaciones se siguen pintando sueltas arriba'
    # y el acumulador se declara y se emite EXACTAMENTE una vez (M156)
    assert b.count("var _htmlConQue = ''") == 1, 'el acumulador del bloque ③ no se declara una vez'
    assert b.count('html += _htmlConQue') == 1, 'el bloque ③ no se emite exactamente una vez'


def test_el_reordenamiento_no_se_comio_NADA(app, db_clean):
    """El trinquete que de verdad importa.

    Un `<div>` de menos NO rompe la sintaxis: el node-check pasa verde con la pantalla partida.
    Estas dos cuentas son las que lo cazan (M156)."""
    b = _cuerpo_del_modal()
    # las piezas que el modal tiene que seguir teniendo, con su multiplicidad
    for marca, veces in (('lote-readiness', 1), ('_planEnvHtml', 4), ('_renderLotesAgendadosCal', 1),
                         ('_renderAccionesLote', 3), ('env-ovr-', 2), ('pres-box-', 1),
                         ('edit-kg-lote', 1), ('cal-cm-preview', 1), ('lote-desglose-edit', 1),
                         ('_calDisponibilidad', 1)):
        assert b.count(marca) == veces, \
            'el modal perdió (o duplicó) "%s": %d, esperaba %d' % (marca, b.count(marca), veces)
    assert b.count('<div') == b.count('</div>'), \
        'los <div> del modal quedaron desbalanceados: %d abren, %d cierran' % (
            b.count('<div'), b.count('</div>'))


def test_el_JS_del_calendario_SIGUE_siendo_valido(app, db_clean):
    """node --check del valor EVALUADO, no del fuente (M65: los escapes de Python dan falsos)."""
    import ast
    import subprocess
    import tempfile
    src = io.open(os.path.join(RAIZ, 'api/blueprints/plan.py'), encoding='utf-8').read()
    grande = None
    for n in ast.walk(ast.parse(src)):
        if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str) and len(n.value.value) > 50000):
            grande = n.value.value
    assert grande and 'abrirLoteModal(id, producto' in grande, \
        'no encontré la constante que contiene el modal del calendario'
    try:
        subprocess.run(['node', '--version'], capture_output=True, check=True)
    except Exception:
        import pytest
        pytest.skip('sin node en este entorno')
    tmp = tempfile.mkdtemp()
    for idx, blk in enumerate(re.findall(r'<script[^>]*>(.*?)</script>', grande, re.S)):
        if not blk.strip():
            continue
        f = os.path.join(tmp, 'cal%d.js' % idx)
        io.open(f, 'w', encoding='utf-8').write(blk)
        r = subprocess.run(['node', '--check', f], capture_output=True, text=True)
        assert r.returncode == 0, 'el JS del calendario quedó roto: ' + r.stderr[:600]
