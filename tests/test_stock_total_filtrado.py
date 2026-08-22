# -*- coding: utf-8 -*-
"""Con un filtro puesto, el total y el detalle tienen que hablar de lo MISMO.

Sebastián 22-ago, buscando el lote `20250902`: *"dice cantidad total 600, pero sólo existe un
lote de 300, ¿de dónde saca los 600?"*.

De ningún lado inventado: PANTHENOL tiene 600 g en 2 lotes y la búsqueda escondió uno. Lo que
estaba mal es que la fila mostraba el total **sin filtrar** (`stock_total_mp_g`, que el backend
calcula sobre TODOS los lotes) al lado de una columna LOTES y un detalle que **sí** están
filtrados -- y el tooltip encima prometía *"suma de sus lotes"*, que con filtro es falso.

Un total que incluye lo que no se ve, junto a un conteo que no lo cuenta, se lee como un
descuadre (M148/M5): quien lo mira no sabe a cuál de los dos creerle.

La aritmética se EJECUTA con node: que el JS compile no prueba que sume bien (M266).
"""
import json
import re
import shutil
import subprocess

import pytest


def _js():
    from templates_py.dashboard_html import DASHBOARD_CORE_JS
    return DASHBOARD_CORE_JS


def _bloque(js, desde, hasta):
    i = js.find(desde)
    assert i != -1, 'no se encontro %r en la pantalla' % desde[:40]
    j = js.find(hasta, i)
    assert j > i, 'no se encontro %r' % hasta[:40]
    return js[i:j + len(hasta)]


def _correr(codigo, tmp_path):
    node = shutil.which('node')
    if not node:
        pytest.skip('node no disponible · no se puede ejecutar el JS')
    f = tmp_path / 'p.js'
    f.write_text(codigo, encoding='utf-8')
    r = subprocess.run([node, str(f)], capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode('utf-8', 'replace')[:600]
    return json.loads(r.stdout.decode('utf-8', 'replace').strip())


def _probe(lotes_visibles, total_mp, lotes_mp, tmp_path):
    js = _js()
    calc = _bloque(js, '    var totalVisible=lotes.reduce', 'var hayFiltro=')
    calc = calc[:calc.rfind('var hayFiltro=')]
    hay = _bloque(js, '    var hayFiltro=', ';\n')
    qshow = _bloque(js, '    var qShow=hayFiltro', ';\n')
    codigo = (
        'var grp={k:%s}, k="k";\n' % json.dumps(lotes_visibles)
        + 'var lotes=grp[k], first=Object.assign({}, lotes[0], '
          '{stock_total_mp_g:%s, lotes_mp_n:%s});\n' % (json.dumps(total_mp), json.dumps(lotes_mp))
        + 'function _mpSafe(x){return String(x);} var safe=_mpSafe(k);\n'
        + calc + hay + qshow
        + '\nconsole.log(JSON.stringify({hayFiltro:hayFiltro, qShow:qShow, '
          'totalVisible:totalVisible, totalMP:totalMP, lotesMP:lotesMP}));\n')
    return _correr(codigo, tmp_path)


def test_con_FILTRO_el_numero_que_se_muestra_es_el_que_se_ve(app, tmp_path):
    """El caso exacto de la captura: 2 lotes de 300, la busqueda deja ver uno."""
    d = _probe([{'cantidad_g': 300}], 600, 2, tmp_path)
    assert d['hayFiltro'] is True, 'no se dio cuenta de que hay un filtro puesto'
    assert d['qShow'] == 300, (
        'sigue mostrando %s al lado de un detalle de 300' % d['qShow'])
    assert d['totalMP'] == 600 and d['lotesMP'] == 2, (
        'perdio el total real del material: sin eso no puede declarar lo que esconde')


def test_SIN_filtro_muestra_el_total_del_material(app, tmp_path):
    """El guard tiene que distinguir: sin filtro nada cambia respecto de antes."""
    d = _probe([{'cantidad_g': 300}, {'cantidad_g': 300}], 600, 2, tmp_path)
    assert d['hayFiltro'] is False, 'creyo que habia filtro sin haberlo'
    assert d['qShow'] == 600, 'sin filtro debe mostrar el total del material'


def test_tambien_lo_detecta_por_el_CONTEO(app, tmp_path):
    """Dos lotes distintos pueden sumar lo mismo: si sólo se comparara el total, un filtro que
    esconde un lote de 0 g pasaría desapercibido."""
    d = _probe([{'cantidad_g': 600}], 600, 2, tmp_path)
    assert d['hayFiltro'] is True, (
        'no detecto el filtro porque los gramos coincidian: hay que mirar tambien el conteo')


def test_la_pantalla_DECLARA_lo_que_esconde(app):
    """No basta con mostrar el numero bueno: hay que decir que hay mas (M148)."""
    js = _js()
    i = js.find('var hayFiltro=')
    assert i != -1
    cuerpo = js[i:i + 3000]
    assert 'de \'+totalMP' in cuerpo or 'de ' in cuerpo, (
        'no dice cuanto tiene el material en total')
    assert 'lotesMP' in cuerpo, 'no dice cuantos lotes tiene en total'
    assert 'Suma de los lotes que se estan viendo' in cuerpo, (
        'el tooltip sigue prometiendo "suma de sus lotes" con un filtro puesto')


def test_el_backend_manda_CUANTOS_lotes_tiene_el_material(admin_client, app):
    """La pantalla filtra del lado del cliente, asi que sin este dato no puede decir '1 de 2'.

    Siembra su propio material con DOS lotes: un test que se saltea cuando no hay datos no
    mide nada, y con el tiempo se lee como si estuviera pasando (M152/M210).
    """
    from database import get_db
    COD = 'MPTOTFILTRO'
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM movimientos WHERE material_id=?", (COD,))
        c.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (COD,))
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
                  "VALUES (?,?,?,1)", (COD, 'MP TOTAL FILTRADO', 'TEST INCI'))
        for lote in ('L-TF-1', 'L-TF-2'):
            c.execute(
                "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
                " fecha, operador, estanteria, estado_lote) "
                "VALUES (?,?,'Entrada',300.0,?,?,?,?,'VIGENTE')",
                (COD, 'MP TOTAL FILTRADO', lote, '2026-08-01 08:00:00', 'test', 'EST-TF'))
        c.commit()
    try:
        r = admin_client.get('/api/lotes')
        assert r.status_code == 200, r.data[:200]
        d = r.get_json()
        filas = d if isinstance(d, list) else (d.get('lotes') or d.get('items') or [])
        mios = [x for x in filas if (x.get('material_id') or '').upper() == COD]
        assert len(mios) == 2, 'el endpoint no devolvio los dos lotes sembrados'
        for f in mios:
            assert f.get('lotes_mp_n') == 2, (
                'no dice cuantos lotes tiene el material: %r' % f.get('lotes_mp_n'))
            assert round(float(f.get('stock_total_mp_g') or 0), 2) == 600.0, (
                'el total del material no es la suma de sus lotes: %r'
                % f.get('stock_total_mp_g'))
    finally:
        with app.app_context():
            c = get_db()
            c.execute("DELETE FROM movimientos WHERE material_id=?", (COD,))
            c.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (COD,))
            c.commit()
