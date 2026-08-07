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


def test_avisa_cuando_hay_DOS_presentaciones_del_mismo_tamano(app):
    """Sebastián, viendo el modal: *"¿por qué me salen repetidos?"* -- CONTORNO DE OJOS tenía dos
    filas de 15 ml encendidas, cada una con un frasco distinto.

    El motor reparte la compra de envases por las **ventas de ese volumen**. Con dos filas del
    mismo tamaño las dos reciben las MISMAS ventas, así que el reparto queda 50/50: se compraría
    la mitad de cada frasco cuando en la realidad sólo se usa uno. No compra de más, compra la
    **mezcla equivocada** -- y como los totales cuadran, el error es invisible (M5/M124).

    ⚠ El aviso sólo salta cuando los frascos son DISTINTOS. Dos tonos que comparten el mismo
    envase reparten bien y no hay nada que corregir: una alerta que suena también en el caso sano
    deja de mirarse justo el día que importa (M129).
    """
    import sys as _sys
    import os as _os
    _sys.path.insert(0, _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'api'))
    import templates_py.dashboard_html as D
    js = D.DASHBOARD_APP_JS
    i = js.find('function empqTarjeta')
    assert i > 0, 'no encuentro la tarjeta del modal'
    bloque = js[i:i + 3000]
    assert '_volAct' in bloque, 'no agrupa las presentaciones por volumen'
    assert 'presentaciones encendidas de' in bloque, 'no avisa nada'
    # sólo las ENCENDIDAS: una apagada ya está fuera del calendario y de la compra
    assert 'if(!x.activo) return;' in bloque, 'contaría presentaciones apagadas'
    # y sólo cuando los frascos DIFIEREN
    assert 'Object.keys(fr).length > 1' in bloque, (
        'avisaría también cuando las dos usan el mismo frasco, que es el caso sano')
    assert 'Apag' in bloque, 'no dice qué hacer'


def test_se_puede_dejar_SOLO_UNA_presentacion_del_mismo_tamano(app):
    """Sebastián: *"es el mismo producto, mismos ml, mismas ventas, y sólo tengo UNO de ese"*.
    La segunda fila no es una variante que haya que elegir: **sobra**.

    Apagarla a mano funciona, pero es tratar el síntoma producto por producto. Con un clic en la
    fila que sí es la real, las otras del mismo tamaño quedan apagadas.

    ⚠ Se APAGA, no se borra: `producto_presentaciones` la leen la compra, el plan, el
    alistamiento y el descuento -- borrar una fila que una producción vieja referencia deja
    huérfano lo que ya pasó (M31/M126).
    """
    import sys as _sys
    import os as _os
    import re as _re
    _sys.path.insert(0, _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'api'))
    import templates_py.dashboard_html as D
    js = D.DASHBOARD_APP_JS
    assert len(_re.findall(r'async function empqDejarUna', js)) == 1, (
        'hay más de una definición · una pisa a la otra sin dar error')
    i = js.find('async function empqDejarUna')
    b = js[i:i + 1600]
    assert 'activo: false' in b, 'no apaga · o borra, o no hace nada'
    assert 'DELETE' not in b.upper(), 'está borrando la presentación en vez de apagarla'
    assert 'confirm(' in b, 'apaga sin preguntar'
    assert 'break' in b, (
        'si una falla sigue apagando a ciegas · dejaría el producto a medio arreglar (M134)')
    # el botón sólo aparece en filas que de verdad están duplicadas
    # ⚠ Ventana amplia y anclada al FIN de la función: una fija se queda corta en cuanto el
    # bloque crece, y el rojo es del test, no del código (me pasó al agregar el SKU · M154).
    _i = js.find('function empqTarjeta')
    _j = js.find(chr(10) + 'function ', _i + 10)
    t = js[_i:_j if _j > _i else _i + 12000]
    assert '_esDup' in t, 'no detecta las filas duplicadas'
    assert 'dejar s' in t, 'no ofrece el botón'
    # ⚠ Y sobre todo: que el botón se PINTE. La 1ª versión lo calculaba en una variable y no lo
    # insertaba nunca en la fila -- construir la pieza y no conectarla es cómo queda un botón
    # que no existe, sin un solo error a la vista (M112).
    assert "_dupBtn + '</td>'" in t, 'el botón se calcula y no se pinta'


def test_apagar_varias_no_recarga_el_modal_por_cada_una(app):
    """`empqSet` recarga el modal a propósito (uso de a uno). Llamarlo en un loop dispararía una
    recarga por fila y las respuestas se pisarían entre sí."""
    import sys as _sys
    import os as _os
    _sys.path.insert(0, _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'api'))
    import templates_py.dashboard_html as D
    js = D.DASHBOARD_APP_JS
    assert 'async function empqGuardar(' in js, 'no existe el guardado sin recarga'
    i = js.find('async function empqDejarUna')
    b = js[i:i + 1600]
    assert 'empqGuardar(' in b, 'usa el que recarga'
    assert b.count('empqAbrir()') == 1, 'recarga más de una vez'


def test_cada_fila_muestra_SU_sku_de_shopify(app):
    """Sebastián (7-ago): *"lo ideal es que sea el rastreo tal cual de Shopify, porque así
    sabemos qué falta"*.

    Los SKU que ya se mostraban salen de (producto, volumen), así que **dos presentaciones del
    mismo tamaño mostraban el mismo** -- imposible distinguir una duplicada de dos variantes
    elegidas a mano. El dato propio de cada fila existía en la tabla (`sku_shopify`) y no llegaba
    a la pantalla (M115).

    Con él, los tres casos se distinguen de un vistazo: dos SKU distintos = dos variantes;
    el mismo o ninguno = duplicada; **sin SKU = no se puede rastrear contra lo que se vende**.
    """
    import io as _io
    import os as _os
    import re as _re
    import sys as _sys
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    _sys.path.insert(0, _os.path.join(raiz, 'api'))

    # el endpoint lo manda
    s = _io.open(_os.path.join(raiz, 'api', 'blueprints', 'programacion.py'),
                 encoding='utf-8').read()
    i = s.find("@bp.route('/api/abastecimiento/envases-cobertura'")
    j = s.find('\n@bp.route', i + 10)
    b = s[i:j]
    assert "'sku_propio'" in b, 'el endpoint no manda el SKU propio de la presentación'
    assert 'COALESCE(sku_shopify' in b, 'no lo lee de la tabla'

    # y la pantalla lo pinta · declararlo sin pintarlo es un dato que sigue sin existir (M112)
    import templates_py.dashboard_html as D
    js = D.DASHBOARD_APP_JS
    _i = js.find('function empqTarjeta')
    _j = js.find(chr(10) + 'function ', _i + 10)
    t = js[_i:_j if _j > _i else _i + 12000]
    assert 'x.sku_propio' in t, 'la pantalla no usa el SKU propio'
    assert '_skuCell' in t and "vcell+_skuCell" in t, 'lo calcula y no lo pinta'
    assert 'sin SKU' in t, (
        'no distingue la presentación que NO existe en Shopify · ésa es justo la que no se '
        'puede rastrear')
