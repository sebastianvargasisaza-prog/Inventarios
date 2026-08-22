# -*- coding: utf-8 -*-
"""La lista para cerrar se RESUELVE ahí mismo: cada pendiente trae sus tres botones.

Sebastián: *"que me diga estantería uno, posición tal, tal producto, nadie lo tocó -- pero con
las opciones de una vez de cambiar cantidad o decir no existe, está en cero, para que salga de
inventario"*.

Una lista que sólo se puede leer manda a abrir otra pantalla, buscar el material y empezar de
nuevo -- y ahí es donde se abandona (M121/M129).

El HTML se genera EJECUTANDO el renderizador con datos sembrados: el `node --check` verifica
que el JavaScript sea válido, **no que el HTML que ese JavaScript arma lo sea** (M266). El dato
sembrado lleva comillas a propósito, que es lo que destapa un atributo partido (M173).
"""
import json
import re
import shutil
import subprocess

import pytest


def _js():
    from blueprints.inventario import _INFORME_CUADRE_HTML as H
    return '\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', H, re.S))


def _recortar(js, desde, hasta):
    i = js.find(desde)
    assert i != -1, 'no se encontro %r' % desde
    j = js.find(hasta, i)
    assert j > i, 'no se encontro el cierre de %r' % desde
    return js[i:j + len(hasta)]


def _fn(js, nombre):
    """La funcion entera, cortada por BALANCE de llaves (M229)."""
    i = js.find('function ' + nombre + '(')
    assert i != -1, 'no esta la funcion %s' % nombre
    j = js.find('{', i)
    prof = 0
    for k in range(j, len(js)):
        if js[k] == '{':
            prof += 1
        elif js[k] == '}':
            prof -= 1
            if prof == 0:
                return js[i:k + 1]
    raise AssertionError('la funcion %s no cierra' % nombre)


def _render(tmp_path, datos):
    """Corre el renderizador de la seccion con un informe sembrado y devuelve el HTML."""
    node = shutil.which('node')
    if not node:
        pytest.skip('node no disponible · no se puede ejecutar el generador')
    js = _js()
    # Se recorta desde el arranque del bloque hasta el cierre de la seccion.
    i = js.find('if((d.por_ubicacion||[]).length){')
    assert i != -1, 'no se encontro la seccion para cerrar'
    j = js.find("h+='</div>';\n    }", i)
    assert j > i, 'no se encontro el cierre de la seccion'
    bloque = js[i:j + len("h+='</div>';\n    }")]

    # El bloque LLAMA a `_btnsDato`, que vive fuera: sin ella el render revienta y la sonda
    # mediria otra cosa. Se recorta por balance de llaves, no por un largo fijo (M229).
    aux = _recortar(js, '_DATO_BTN = {', '};') + '\n' + _fn(js, '_btnsDato')
    prelude = (
        'var ' + aux.lstrip('var ') + '\n'
        'function esc(s){return String(s==null?"":s)'
        '.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")'
        '.replace(/"/g,"&quot;");}\n'
        'function n(v){return Number(v||0).toLocaleString("es-CO");}\n'
        'function _sec(t,c){return "<h2 class=\\"" + (c||"") + "\\">" + t + "</h2>";}\n'
        'var _PEND=[];\n'
        'var d=' + json.dumps(datos) + ';\n'
        'var s=d.resumen||{};\n'
        'var h="";\n')
    codigo = prelude + bloque + '\nconsole.log(h);\n'
    f = tmp_path / 'r.js'
    f.write_text(codigo, encoding='utf-8')
    r = subprocess.run([node, str(f)], capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode('utf-8', 'replace')[:700]
    return r.stdout.decode('utf-8', 'replace')


DATOS = {
    'resumen': {'ubicaciones_pendientes': 1},
    'por_ubicacion': [{
        'estanteria': 'Est. 1',
        'total': 3,
        'no_esta': [{'codigo_mp': 'MP1', 'nombre': 'ACIDO "raro"', 'lote': "L'1",
                     'sistema': 500, 'estanteria': 'Est. 1', 'posicion': 'A2'}],
        'sin_revisar': [{'codigo_mp': 'MP2', 'nombre': 'GLICERINA', 'lote': 'L2',
                         'stock_sistema': 800, 'estanteria': 'Est. 1', 'posicion': 'B3'}],
        'sin_dato': [{'codigo_mp': 'MP3', 'nombre': 'UREA', 'lote': 'L3',
                      'stock_sistema': 200, 'estanteria': 'Est. 1', 'posicion': 'C4',
                      'falta': ['vencimiento']}],
    }],
}


def test_cada_pendiente_trae_LOS_TRES_botones(app, tmp_path):
    html = _render(tmp_path, DATOS)
    for t in ('pOk(', 'pCant(', 'pNo('):
        assert t in html, 'falta el boton %s en la lista para cerrar' % t


def test_dice_DONDE_esta_cada_uno(app, tmp_path):
    """*"que me diga estanteria uno, posicion tal, tal producto"*."""
    html = _render(tmp_path, DATOS)
    assert 'Est. 1' in html, 'no dice la estanteria'
    assert 'pos. B3' in html, 'no dice la posicion del pendiente'
    assert 'GLICERINA' in html, 'no dice que producto es'


def test_lo_que_le_falta_un_DATO_no_ofrece_declarar_cantidad(app, tmp_path):
    """Se corrige el dato, no se declara cantidad: ofrecer "no existe" ahi seria invitar a
    borrar un lote que SI esta, solo porque le falta el vencimiento."""
    html = _render(tmp_path, DATOS)
    i = html.find('UREA')
    assert i != -1
    fila = html[i:html.find('</li>', i)]
    assert 'pNo(' not in fila and 'pOk(' not in fila, (
        'la fila de "le falta un dato" ofrece declararlo en cero')
    assert 'falta vencimiento' in fila, 'no dice cual dato falta'


def test_lo_que_le_falta_un_DATO_ofrece_COMPLETARLO(app, tmp_path):
    """Sebastian: *"las que les falte un dato puedo hacerlo de una vez"*. Sin el boton hay que
    abrir otra pantalla y buscar el material: ahi es donde se abandona (M121)."""
    html = _render(tmp_path, DATOS)
    i = html.find('UREA')
    fila = html[i:html.find('</li>', i)]
    assert 'dVenc(' in fila, 'no ofrece poner el vencimiento que le falta'


def test_solo_ofrece_el_boton_del_dato_que_FALTA(app, tmp_path):
    """Si ofreciera los cuatro siempre, tres de ellos cambiarian un dato que ya esta bien."""
    datos = json.loads(json.dumps(DATOS))
    datos['por_ubicacion'][0]['sin_dato'][0]['falta'] = ['INCI']
    html = _render(tmp_path, datos)
    i = html.find('UREA')
    fila = html[i:html.find('</li>', i)]
    assert 'dInci(' in fila, 'no ofrece poner el INCI'
    assert 'dVenc(' not in fila, 'ofrece cambiar el vencimiento, que no falta'
    assert 'dUbic(' not in fila, 'ofrece cambiar la ubicacion, que no falta'


def test_cada_dato_va_por_SU_endpoint(app):
    """Cada boton usa el endpoint que ya existe para ese dato, no una puerta nueva (M3)."""
    js = _js()
    for fn, url in (('function dVenc(', 'fecha-vencimiento'),
                    ('function dUbic(', 'ubicacion'),
                    ('function dInci(', '/inci'),
                    ('function dLote(', 'codigo-lote')):
        i = js.find(fn)
        assert i != -1, 'falta la funcion %s' % fn
        cuerpo = js[i:i + 900]
        assert url in cuerpo, '%s no llama a su endpoint (%s)' % (fn, url)


def test_ningun_dato_se_deja_VACIO(app):
    """Un INCI vacio hace que el resolver caiga a otros criterios y elija la molecula de al
    lado (M137); un vencimiento vacio vuelve el lote eterno al FEFO (M118)."""
    js = _js()
    for fn in ('function dVenc(', 'function dInci(', 'function dUbic(', 'function dLote('):
        i = js.find(fn)
        cuerpo = js[i:i + 900]
        assert 'if(!' in cuerpo and 'alert(' in cuerpo, (
            '%s deja guardar el dato vacio' % fn)


def test_el_HTML_que_arma_no_queda_PARTIDO(app, tmp_path):
    """El dato sembrado lleva comillas dobles y simples a proposito: es lo que parte un
    atributo `onclick="..."` y deja el boton roto sin que el node-check lo vea (M173)."""
    html = _render(tmp_path, DATOS)
    assert '<li' in html
    assert html.count('<li') == html.count('</li>'), 'las filas no cierran'
    assert html.count('<ul') == html.count('</ul>'), 'las listas no cierran'
    # Cada onclick tiene que quedar entero: nombre(argumentos) y el atributo cerrado.
    ocs = re.findall(r'onclick="([^"]*)"', html)
    assert len(ocs) >= 3, 'no se encontraron los botones: la sonda no midio nada'
    for o in ocs:
        assert o.count('(') == o.count(')') and o.endswith(')'), 'onclick partido: %r' % o
        assert '"' not in o and "'" not in o, (
            'el onclick lleva comillas: un dato con comillas lo parte · %r' % o)


def test_cada_fila_tiene_su_PROPIO_id(app, tmp_path):
    """El mismo lote puede estar pendiente por dos motivos: con una llave por lote los dos
    botones escribirian en el mismo sitio y uno no haria nada (M204)."""
    html = _render(tmp_path, DATOS)
    ids = re.findall(r'id="(p-\d+|pm-\d+)"', html)
    assert ids, 'las filas no tienen id'
    assert len(ids) == len(set(ids)), 'hay ids repetidos: %s' % sorted(ids)


def test_escribe_por_el_MISMO_endpoint_del_cuadre(app):
    """No es una segunda puerta al inventario: por ahi ya pasan el estado del lote, su
    vencimiento, el rastro y el token anti doble-clic (M3)."""
    js = _js()
    i = js.find('async function _declararPend')
    assert i != -1, 'no existe la funcion que declara desde el cierre'
    cuerpo = js[i:i + 1800]
    assert "'/api/inventario/cuadre'" in cuerpo, 'no usa el endpoint canonico del cuadre'
    assert 'X-CSRF-Token' in cuerpo, 'no manda el token CSRF'
    assert 'token:' in cuerpo, 'no manda el token anti doble-clic'


def test_al_declarar_la_fila_SALE_de_la_lista(app):
    """Si se quedara, nadie sabe cual ya cerro y vuelve a buscarlo (M129)."""
    js = _js()
    i = js.find('async function _declararPend')
    cuerpo = js[i:i + 1800]
    assert "li.className = 'hecho'" in cuerpo, 'la fila declarada no se marca como resuelta'
    assert 'ubin-' in cuerpo, 'el contador del estante no baja'


def test_dar_por_NO_ENCONTRADO_exige_motivo(app):
    """Dar un lote por perdido sin decir por que deja el ajuste sin poder explicarse (M19)."""
    js = _js()
    i = js.find('function pNo(')
    assert i != -1
    cuerpo = js[i:i + 700]
    assert 'prompt(' in cuerpo, 'no pregunta el motivo'
    assert 'Hace falta el motivo' in cuerpo, 'deja declarar sin motivo'
    assert '_declararPend(ix, 0,' in cuerpo, 'no lo deja en cero'
