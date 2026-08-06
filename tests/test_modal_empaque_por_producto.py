# -*- coding: utf-8 -*-
"""El empaque se revisa POR PRODUCTO, en un modal, dentro de Planta.

Sebastián: *"no encuentro eso, preferiría que revisemos por productos no crees? que quede un modal
para eso"*. Tenía razón en las dos cosas: la tabla vivía en `/planta` › Configuración › Reparto
envases -- tres niveles, donde no la iba a mirar nadie -- y estaba ordenada por PRESENTACIÓN, que
no es como piensa el negocio. Él piensa *"este producto, ¿tiene todo su empaque?"*.

Un tablero que hay que leer entero para encontrar el problema no se lee: el modal agrupa por
producto, filtra por defecto a los que les falta algo, y ordena lo incompleto primero.
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))


def _pagina():
    """El valor FINAL, no el literal del fuente: el JS se extrae a los bundles al importar el
    módulo, así que buscarlo en `DASHBOARD_HTML` da CERO con el código correcto (M158)."""
    import templates_py.dashboard_html as D
    return (D.DASHBOARD_HTML,
            ((getattr(D, 'DASHBOARD_APP_JS', '') or '')
             + (getattr(D, 'DASHBOARD_CORE_JS', '') or '') + D.DASHBOARD_HTML))


def _sin_comentarios_js(txt):
    return re.sub(r'//[^\n]*', '', txt)


def test_el_modal_EXISTE_una_sola_vez(app, db_clean):
    html, _ = _pagina()
    assert html.count('id="modal-empaque"') == 1, 'el modal falta o está duplicado'


def test_se_ENTRA_desde_Necesidades(app, db_clean):
    """Un modal al que no se llega desde ninguna parte no existe (M121). Y el botón tiene que
    estar en Necesidades, que es donde se miran los productos, no enterrado en Configuración."""
    html, _ = _pagina()
    assert 'empqAbrir()' in html, 'no hay botón que abra el modal'
    i = html.find('id="ptab-necesidades"')
    assert i > 0
    j = html.find('empqAbrir()')
    assert i < j < i + 6000, 'el botón no está en la barra de Necesidades'


def test_toda_funcion_del_modal_esta_DEFINIDA(app, db_clean):
    """Un botón que llama a una función inexistente no falla: simplemente no hace nada (M146)."""
    html, todo = _pagina()
    js = _sin_comentarios_js(todo)
    definidas = set(re.findall(r'function\s+(empq[\w$]*)\s*\(', js))
    llamadas = (set(re.findall(r'(?<![\w$.])(empq[\w$]*)\s*\(', js))
                | set(re.findall(r'on\w+="(empq[\w$]*)\(', html)))
    assert not (llamadas - definidas), sorted(llamadas - definidas)


def test_ningun_id_del_modal_apunta_al_vacio(app, db_clean):
    """El chequeo barato que caza el par disparador↔destino roto (M112)."""
    html, todo = _pagina()
    js = _sin_comentarios_js(todo)
    ids = set(re.findall(r'id="([^"]+)"', html))
    usados = set(re.findall(r"getElementById\('(empq[^']*)'\)", js))
    assert not (usados - ids), sorted(usados - ids)


def test_agrupa_por_PRODUCTO_no_por_presentacion(app, db_clean):
    """Es el punto del cambio: la vista anterior era una fila por presentación."""
    _, todo = _pagina()
    js = _sin_comentarios_js(todo)
    i = js.find('function empqAgrupar')
    assert i > 0, 'no agrupa'
    bloque = js[i:i + 1200]
    assert 'por[x.producto]' in bloque, 'no agrupa por producto'


def test_un_producto_SIN_presentacion_no_desaparece(app, db_clean):
    """El peor hueco de todos -- su envase no se compra en absoluto -- y si sólo se listara
    `union` no aparecería en ninguna fila (M124: lo excluido se enumera)."""
    _, todo = _pagina()
    js = _sin_comentarios_js(todo)
    i = js.find('function empqAgrupar')
    bloque = js[i:i + 1400]
    assert 'sin_envase' in bloque, 'los productos sin presentación quedan invisibles'
    assert 'sin_presentacion' in bloque


def test_lo_INCOMPLETO_va_primero(app, db_clean):
    """Un tablero que hay que leer entero para encontrar el problema no se lee."""
    _, todo = _pagina()
    js = _sin_comentarios_js(todo)
    i = js.find('function empqPintar')
    bloque = js[i:i + 2600]
    assert 'lista.sort' in bloque, 'no ordena'
    assert 'b.falta-a.falta' in bloque, 'no pone primero lo que falta'


def test_los_KPI_no_cambian_al_BUSCAR(app, db_clean):
    """Si el contador se calculara sobre lo filtrado, cambiaría al escribir en el buscador y
    dejaría de significar algo (M5)."""
    _, todo = _pagina()
    js = _sin_comentarios_js(todo)
    i = js.find('function empqPintar')
    bloque = js[i:i + 2600]
    # ⚠ Se mide SOBRE QUÉ se calcula, no dónde aparece el nombre: la primera versión de este
    # test comparaba posiciones y pasaba en verde con el cálculo roto, porque `nFalta` seguía
    # nombrándose más abajo al pintarlo. Un test que mide un proxy en vez del hecho no protege
    # nada (M142/M152).
    assert 'nFalta=todos.filter' in bloque.replace(' ', ''), \
        'el contador de "les falta algo" no se calcula sobre TODOS los productos'
    assert 'nSerig=todos.reduce' in bloque.replace(' ', ''), \
        'el contador de serigrafía no se calcula sobre TODOS los productos'
    assert 'nFalta=lista' not in bloque.replace(' ', ''), \
        'los KPI se calculan sobre lo FILTRADO · cambiarían al escribir en el buscador'


def test_si_la_union_no_se_pudo_calcular_lo_DICE(app, db_clean):
    """Una lista vacía se leería como "está todo bien" (M100)."""
    _, todo = _pagina()
    js = _sin_comentarios_js(todo)
    i = js.find('function empqPintar')
    bloque = js[i:i + 1200]
    assert 'EMPQ.union===null' in bloque, 'no distingue "no hay huecos" de "no pude medir"'
    assert 'EMPQ.aviso' in bloque
