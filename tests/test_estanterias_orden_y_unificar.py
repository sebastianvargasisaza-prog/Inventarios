# -*- coding: utf-8 -*-
"""Las estanterías en el orden del pasillo, y la misma ubicación escrita de una sola forma.

Sebastián, contando y mirando la pantalla (22-ago): *"hay varias neveras mayúscula y minúscula,
igual estanterías, necesito que unifiquemos eso"*.

Medido en su captura: `Estiba / ESTIBA / estibas / Estibas / ESTIBAS` eran CINCO botones del
mismo lugar (22 materiales repartidos) y `nevera / Nevera / NEVERA` otros tres (40). Como cada
variante es un botón distinto, **quien camina ese lugar sólo abre uno** y el resto del material
queda sin contar sin que nadie se entere.

Y el orden era el del diccionario (`10 11 12 13 14 2 3 4...`), no el de la bodega.

El JS se EJECUTA con node, no se lee: que compile no prueba que ordene ni que agrupe (M266).
"""
import json
import os
import re
import shutil
import subprocess

import pytest

EST_A = 'ESTIBA-TEST'
EST_B = 'estibas-test'
EST_C = 'Estiba-Test'
CODIGO = 'MPESTORDEN'


def _js_de_la_pantalla():
    from templates_py.cuadre_html import CUADRE_HTML
    bloques = re.findall(r'<script[^>]*>(.*?)</script>', CUADRE_HTML, re.S)
    grande = max(bloques, key=len)
    assert len(grande) > 5000, 'no se encontró el bloque de JS de la pantalla'
    return grande


def _correr_node(js, tmp_path):
    node = shutil.which('node')
    if not node:
        pytest.skip('node no está disponible en esta máquina · no se puede ejecutar el JS')
    f = tmp_path / 'probe.js'
    f.write_text(js, encoding='utf-8')
    r = subprocess.run([node, str(f)], capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode('utf-8', 'replace')[:600]
    return r.stdout.decode('utf-8', 'replace').strip()


def _extraer(js, *nombres):
    """Recorta las funciones pedidas por balance de llaves, no por un largo fijo (M229)."""
    fuera = []
    for n in nombres:
        i = js.find('function ' + n + '(')
        assert i != -1, 'no está la función %s en la pantalla' % n
        j = js.find('{', i)
        prof = 0
        for k in range(j, len(js)):
            if js[k] == '{':
                prof += 1
            elif js[k] == '}':
                prof -= 1
                if prof == 0:
                    fuera.append(js[i:k + 1])
                    break
        else:
            raise AssertionError('la función %s no cierra' % n)
    return '\n'.join(fuera)


# ─────────────────────────────────────────────────────────────────────────────
# 1 · el orden con el que se camina la bodega
# ─────────────────────────────────────────────────────────────────────────────

def test_las_estanterias_salen_en_orden_de_BODEGA_no_de_diccionario(app, tmp_path):
    js = _js_de_la_pantalla()
    probe = _extraer(js, '_ordenEstanteria', '_cmpEstanteria') + """
var d = [{estanteria:'10'},{estanteria:'11'},{estanteria:'12'},{estanteria:'13'},
         {estanteria:'14'},{estanteria:'2'},{estanteria:'3'},{estanteria:'9'},
         {estanteria:'CUARENTENA'},{estanteria:'nevera'},{estanteria:'Sin estanteria'}];
console.log(JSON.stringify(d.slice().sort(_cmpEstanteria).map(function(x){return x.estanteria;})));
"""
    orden = json.loads(_correr_node(probe, tmp_path))
    numeros = [x for x in orden if x.isdigit()]
    assert numeros == ['2', '3', '9', '10', '11', '12', '13', '14'], (
        'las estanterías no salen en orden de bodega: %s' % numeros)
    assert orden.index('2') < orden.index('CUARENTENA'), 'los números van primero'
    assert orden[-1].lower().startswith('sin estanter'), (
        'lo que no tiene ubicación va al final, no en el medio')


# ─────────────────────────────────────────────────────────────────────────────
# 2 · la misma ubicación escrita de varias formas se DETECTA sola
# ─────────────────────────────────────────────────────────────────────────────

def test_la_pantalla_detecta_las_ubicaciones_partidas(app, tmp_path):
    """El caso exacto de la captura: cinco estibas y tres neveras."""
    js = _js_de_la_pantalla()
    probe = _extraer(js, '_claveUbic') + """
var v = ['Estiba','ESTIBA','estibas','Estibas','ESTIBAS','nevera','Nevera','NEVERA','10','1'];
var g = {};
v.forEach(function(x){ var k=_claveUbic(x); (g[k]=g[k]||[]).push(x); });
console.log(JSON.stringify(g));
"""
    g = json.loads(_correr_node(probe, tmp_path))
    assert len(g.get('estiba') or []) == 5, 'no junta las cinco formas de estiba: %s' % g
    assert len(g.get('nevera') or []) == 3, 'no junta las tres neveras: %s' % g
    assert g.get('10') == ['10'] and g.get('1') == ['1'], (
        'juntó dos estanterías con NÚMERO distinto, que son lugares distintos: %s' % g)


def test_el_aviso_esta_PINTADO_en_la_pantalla(app):
    """Una capacidad sin puerta no existe: el problema tiene que anunciarse solo (M121)."""
    from templates_py.cuadre_html import CUADRE_HTML as H
    assert 'aviso-partidas' in H, 'no hay dónde pintar el aviso'
    assert '_avisoPartidas' in H, 'nadie calcula las ubicaciones partidas'
    i = H.find('function _avisoPartidas')
    cuerpo = H[i:i + 1800]
    assert 'abrirUbic()' in cuerpo, 'el aviso no ofrece resolverlo ahí mismo'
    assert 'cargarEstanterias' in H and '_avisoPartidas(d)' in H, (
        'el aviso no se dispara al cargar las estanterías')


# ─────────────────────────────────────────────────────────────────────────────
# 3 · unificar de verdad: el acto completo por los endpoints reales
# ─────────────────────────────────────────────────────────────────────────────

def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM movimientos WHERE material_id=?", (CODIGO,))
        c.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (CODIGO,))
        c.commit()


@pytest.fixture()
def tres_formas(app):
    """El mismo lugar escrito de tres maneras, con material en cada una."""
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
                  "VALUES (?,?,?,1)", (CODIGO, 'MP ORDEN ESTANTERIA', 'TEST INCI'))
        for n, (est, lote, cant) in enumerate(
                ((EST_A, 'L-EST-1', 100.0), (EST_B, 'L-EST-2', 200.0),
                 (EST_C, 'L-EST-3', 300.0))):
            c.execute(
                "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
                " fecha, operador, estanteria, estado_lote) "
                "VALUES (?,?,'Entrada',?,?,?,?,?,'VIGENTE')",
                (CODIGO, 'MP ORDEN ESTANTERIA', cant, lote, '2026-08-0%d 08:00:00' % (n + 1),
                 'test', est))
        c.commit()
    yield
    _limpiar(app)


def _grupo_nuestro(client):
    r = client.get('/api/inventario/ubicaciones-agrupadas')
    assert r.status_code == 200, r.data[:200]
    for g in (r.get_json() or {}).get('grupos') or []:
        nombres = {v['nombre'] for v in g.get('variantes') or []}
        if EST_A in nombres:
            return g
    return None


def test_la_herramienta_VE_que_es_el_mismo_lugar(admin_client, tres_formas):
    g = _grupo_nuestro(admin_client)
    assert g is not None, 'no detecta que las tres formas son el mismo lugar'
    assert len({v['nombre'] for v in g['variantes']}) == 3, (
        'no juntó las tres variantes: %s' % g.get('variantes'))


def test_unificar_deja_UNA_sola_ubicacion(admin_client, tres_formas):
    """El acto que pidió Sebastián, medido donde se ve: en la lista de estanterías."""
    g = _grupo_nuestro(admin_client)
    variantes = [v['nombre'] for v in g['variantes'] if v['nombre'] != EST_A]
    r = admin_client.post('/api/inventario/unificar-ubicacion',
                          json={'canonica': EST_A, 'variantes': variantes})
    assert r.status_code == 200, r.data[:200]
    assert (r.get_json() or {}).get('movidos', 0) >= 2, 'dijo que ok y no movió nada'

    ests = admin_client.get('/api/conteo/estanterias')
    nombres = [e['estanteria'] for e in (ests.get_json() or [])]
    assert EST_A in nombres, 'se perdió la ubicación que queda'
    assert EST_B not in nombres and EST_C not in nombres, (
        'siguen apareciendo las otras formas: %s' % [n for n in nombres if 'EST' in n.upper()])


def test_unificar_NO_MUEVE_material(admin_client, tres_formas):
    """Cambia cómo se llama el lugar, no qué hay adentro: los tres lotes siguen enteros."""
    from database import get_db
    with admin_client.application.app_context():
        antes = get_db().execute(
            "SELECT COALESCE(SUM(cantidad),0), COUNT(*) FROM movimientos WHERE material_id=?",
            (CODIGO,)).fetchone()
    g = _grupo_nuestro(admin_client)
    admin_client.post('/api/inventario/unificar-ubicacion', json={
        'canonica': EST_A,
        'variantes': [v['nombre'] for v in g['variantes'] if v['nombre'] != EST_A]})
    with admin_client.application.app_context():
        desp = get_db().execute(
            "SELECT COALESCE(SUM(cantidad),0), COUNT(*) FROM movimientos WHERE material_id=?",
            (CODIGO,)).fetchone()
    assert float(desp[0]) == float(antes[0]), 'unificar cambió las cantidades'
    assert desp[1] == antes[1], 'unificar creó o borró movimientos'


def test_unificar_NO_junta_dos_lugares_DISTINTOS(admin_client, tres_formas):
    """El borde que hace segura la herramienta: juntar dos lugares de verdad movería material
    de un estante a otro sin que nadie lo haya movido."""
    r = admin_client.post('/api/inventario/unificar-ubicacion',
                          json={'canonica': EST_A, 'variantes': ['NEVERA-QUE-NO-ES']})
    assert r.status_code == 400, 'dejó juntar dos lugares distintos'
    assert (r.get_json() or {}).get('codigo') == 'UBICACIONES_DISTINTAS'


def test_unificar_deja_rastro_de_lo_que_se_movio(admin_client, tres_formas):
    """Sin saber qué variantes se movieron no se puede deshacer."""
    from database import get_db
    g = _grupo_nuestro(admin_client)
    admin_client.post('/api/inventario/unificar-ubicacion', json={
        'canonica': EST_A,
        'variantes': [v['nombre'] for v in g['variantes'] if v['nombre'] != EST_A]})
    with admin_client.application.app_context():
        filas = get_db().execute(
            "SELECT COALESCE(antes,'') || COALESCE(despues,'') || COALESCE(detalle,'') "
            "  FROM audit_log WHERE accion='UNIFICAR_UBICACION' AND registro_id=?",
            (EST_A,)).fetchall()
    assert filas, 'unificar no dejó rastro'
    texto = ' '.join(f[0] for f in filas)
    assert EST_B in texto or EST_C in texto, 'el rastro no dice qué variantes se movieron'


def test_la_PANTALLA_y_el_SERVIDOR_agrupan_IGUAL(app, tmp_path):
    """Un solo criterio canónico, verificado ejecutando los dos (M1).

    Si la pantalla agrupara distinto que el endpoint, avisaría de un grupo que después se
    rechaza con *"no son la misma ubicación"*: manda a apretar un botón que va a fallar, que
    es peor que no avisar.
    """
    from blueprints.inventario import _ubic_norm
    casos = ['Estiba', 'ESTIBA', 'estibas', 'Estibas', 'ESTIBAS',
             'nevera', 'Nevera', 'NEVERA', 'NEVERA 2', 'neveras 2',
             'ESTIBA 3', 'ESTIBAS 3', 'Cuarto de almacenamiento',
             'CUARTO DE ALMACENAMIENTO', '10', '1', 'A-3', 'a 3']
    js = _js_de_la_pantalla()
    probe = (_extraer(js, '_claveUbic')
             + "\nconsole.log(JSON.stringify(" + json.dumps(casos) + ".map(_claveUbic)));\n")
    del_js = json.loads(_correr_node(probe, tmp_path))
    del_py = [_ubic_norm(x) for x in casos]
    difieren = [(c, a, b) for c, a, b in zip(casos, del_js, del_py) if a != b]
    assert not difieren, 'la pantalla y el servidor agrupan distinto: %s' % difieren
    # Y que de verdad esté midiendo: si todo diera la misma clave, no probaría nada (M158).
    assert len(set(del_py)) >= 6, 'el normalizador colapsó todo en %d claves' % len(set(del_py))


def test_el_plural_se_quita_PALABRA_POR_PALABRA(app):
    """En la bodega los nombres llevan número, así que el plural casi nunca queda al final."""
    from blueprints.inventario import _ubic_norm
    assert _ubic_norm('ESTIBA 3') == _ubic_norm('ESTIBAS 3')
    assert _ubic_norm('NEVERA 2') == _ubic_norm('neveras 2')
    # Y el borde que lo hace seguro: los números NO se tocan.
    assert _ubic_norm('10') != _ubic_norm('1'), 'la 1 y la 10 son estanterías distintas'
    assert _ubic_norm('ESTIBA 3') != _ubic_norm('ESTIBA 4'), 'dos estibas distintas se juntaron'
