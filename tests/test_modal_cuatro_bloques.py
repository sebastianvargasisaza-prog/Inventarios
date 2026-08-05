# -*- coding: utf-8 -*-
"""El modal Programar, con la cara que Sebastián aprobó (4-ago).

Él vio la propuesta y dijo *"me encanta"*; después, mirando lo desplegado: *"revisá que
Necesidades Programar y Calendario queden como me los mostraste cuando aprobamos, no los veo
así"*. Tenía razón: el contenido nuevo se había metido DENTRO del modal viejo, con su estructura
de siempre.

Los cuatro bloques del mockup, y por qué cada uno:

  · **veredicto en una línea** arriba de todo — antes había que leer ocho recuadros para saber
    cómo venía el producto;
  · **① Cómo va** — el diagnóstico comprimido a una fila de números, no un párrafo en grilla;
  · **② Qué decido** — el bloque DOMINANTE: es la razón por la que se abre el modal, y tenía el
    mismo peso visual que los tres bloques de información que lo rodeaban;
  · **③ Con qué cuento** — DESPUÉS de decidir, porque contesta por los kilos que el usuario
    acaba de elegir. Puesto antes contestaba por un kilaje que todavía no existía;
  · **④ Qué queda agendado**.

El reordenamiento se hizo CAPTURANDO el bloque en una variable, sin reescribir una línea de su
contenido: así el cambio es mecánico y no puede perderse HTML por el camino.
"""
import ast
import io
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cuerpo_modal():
    """El JS RENDERIZADO de `abrirSolicitar` · no el fuente crudo (M65)."""
    src = io.open(os.path.join(RAIZ, 'api/templates_py/dashboard_html.py'),
                  encoding='utf-8').read()
    grandes = [v.value for n in ast.walk(ast.parse(src)) for v in ast.walk(n)
               if isinstance(v, ast.Constant) and isinstance(v.value, str)
               and len(v.value) > 500000]
    assert grandes, 'no encontré el template del dashboard'
    g = max(grandes, key=len)
    i = g.find('function abrirSolicitar(')
    assert i > 0, 'no encontré abrirSolicitar'
    m = re.search(r"document\.getElementById\('sol-body'\)\.innerHTML = html;", g[i:])
    assert m, 'no encontré el final del modal'
    return g[i:i + m.start()]


def test_los_cuatro_bloques_estan_y_EN_ESE_ORDEN():
    """El orden es el que Sebastián describió al contar cómo programa · si se invierte, el
    chequeo de materiales vuelve a contestar por un lote que él no eligió."""
    c = _cuerpo_modal()
    bloques = ['① Cómo va', 'Qué decido', '③ Con qué cuento',
               '④ Qué queda agendado']
    pos = []
    for b in bloques:
        i = c.find(b)
        assert i > 0, 'falta el bloque %s' % b.encode('ascii', 'replace').decode()
        pos.append(i)
    assert pos == sorted(pos), 'los bloques están en otro orden: %s' % pos


def test_el_veredicto_va_en_UNA_linea_arriba():
    """Antes había que leer ocho recuadros para saber cómo venía el producto."""
    c = _cuerpo_modal()
    assert 'VEREDICTO EN UNA LINEA' in c
    assert 'Sin stock en góndola' in c
    assert 'sin SKU mapeado' in c, \
        'lo que hace que el plan NO vea al producto tiene que estar en la primera línea'
    # y usa el MISMO estado que la fila de la tabla, o los dos colores discrepan (M5)
    i = c.find('VEREDICTO EN UNA LINEA')
    assert 'cfg.' in c[i:i + 2200], 'el veredicto no usa el estado ya calculado'


def test_el_diagnostico_es_una_FILA_DE_NUMEROS():
    c = _cuerpo_modal()
    assert '_kpiTarjeta' in c, 'el diagnóstico sigue siendo un párrafo en grilla'
    for rot in ('Vende / día', 'Vende / mes', 'Stock góndola', 'Alcanza'):
        assert "_kpiTarjeta('" + rot + "'" in c, 'falta la tarjeta %s' % rot.encode('ascii', 'replace').decode()


def test_ALCANZA_no_aparece_dos_veces():
    """Al pasar a tarjetas quedó duplicado (tarjeta + línea de texto) · dos veces el mismo
    número invita a buscarle una diferencia que no existe."""
    c = _cuerpo_modal()
    assert c.count("_kpiTarjeta('Alcanza'") == 1
    assert 'Alcanza góndola:' not in c, 'quedó la línea vieja además de la tarjeta'


def test_el_recuadro_de_POR_ENTRAR_solo_sale_si_hay():
    """Se dibujaba siempre, con su padding, aunque no hubiera nada adentro."""
    c = _cuerpo_modal()
    i = c.find('Por entrar (Espagiria)')
    assert i > 0, 'se perdió el aviso de lo que viene de Espagiria'
    assert 'if ((p.por_entrar_uds || 0) > 0) {' in c[max(0, i - 900):i], \
        'el recuadro se sigue dibujando sin contenido'


def test_la_DECISION_es_el_bloque_dominante():
    """Es la razón por la que se abre el modal · tenía el mismo peso visual que los bloques de
    información que lo rodeaban."""
    c = _cuerpo_modal()
    i = c.find('Qué decido')
    assert i > 0
    # El contenedor se emite JUSTO ANTES del rótulo, así que la ventana mira para atrás también:
    # buscar sólo hacia adelante hacía fallar el test con el estilo puesto correctamente.
    bloque = c[max(0, i - 900):i + 900]
    assert 'border-left:5px solid var(--cx-primary)' in bloque, 'no destaca sobre el resto'
    assert 'box-shadow' in bloque


def test_el_bloque_de_materiales_se_EMITE_una_sola_vez():
    """Se movió capturándolo en una variable: si se declarara o emitiera dos veces, el modal
    mostraría el chequeo duplicado."""
    c = _cuerpo_modal()
    assert c.count("var _htmlConQue = ''") == 1
    assert c.count('html += _htmlConQue;') == 1
    # y se emite DESPUÉS de la decisión, no antes
    assert c.find('html += _htmlConQue;') > c.find('Qué decido')


def test_no_se_perdio_nada_al_reordenar():
    """Con dientes: mover un bloque de 40 líneas es donde se cae contenido sin que nadie lo
    note (el node-check pasa igual · borrar un div no rompe la sintaxis · M112)."""
    c = _cuerpo_modal()
    for marca in ('nec-disp-viejo', 'id="nec-disp"', 'FALTAN MATERIAS PRIMAS',
                  'Ver todas las materias primas', 'Sin fórmula registrada',
                  'programarCadenaManual', 'renderLotesInline', 'Back-fill'):
        assert marca in c, 'se perdió: %s' % marca.encode('ascii', 'replace').decode()


def test_el_modal_sigue_cerrando_todos_sus_div():
    """Un `<div>` sin cerrar rompe el layout de todo lo que viene abajo, y el node-check no lo
    ve porque la sintaxis del JS sigue siendo válida."""
    c = _cuerpo_modal()
    ab = len(re.findall(r'<div', c))
    ce = len(re.findall(r'</div>', c))
    assert ab == ce, 'quedaron %d <div> sin cerrar' % (ab - ce)
