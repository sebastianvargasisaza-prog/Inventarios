"""La lista de códigos para el DIRECTOR TÉCNICO (1-ago).

Sebastián: *"desde que en EOS estén perfectos y la fórmula descuente la materia prima que es, se
deja así, y yo pido que cambien en batch ... el director técnico me dijo que le enviara la lista
de todas las materias primas con códigos, diciéndole cuáles debe cambiar"*.

La dirección de la corrección no es una preferencia: los códigos del batch que no cuadran o **no
existen** en el maestro de EOS, o apuntan a **otro material**. Para cada uno de esos materiales
EOS sí tiene el código con su nombre e INCI correctos.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _pedir(app):
    r = _login(app).get('/api/programacion/codigos-batch-vs-maestro')
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def test_cubre_TODAS_las_materias_primas_de_los_batch_records(app, db_clean):
    """Es una lista para mandar: si se deja una afuera, el DT corrige a medias y volvemos acá."""
    import json
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'api', 'data', 'formulas_batch_record.json')
    with open(ruta, encoding='utf-8') as f:
        ref = json.load(f)
    cods = {i['codigo'] for p in ref['productos'] for i in p['items']}
    j = _pedir(app)
    assert j['n_materias_primas'] == len(cods), (j['n_materias_primas'], len(cods))
    listados = {x['codigo_en_batch'] for x in j['cambiar_en_batch'] + j['ya_estan_bien']}
    assert listados == cods, 'faltan o sobran códigos: %r' % (cods ^ listados)
    assert j['n_cambiar'] + j['n_ok'] == len(cods)


def test_cada_uno_a_cambiar_dice_POR_QUE_y_DONDE(app, db_clean):
    """El DT tiene que poder abrir la orden concreta · una lista sin el dónde no es accionable."""
    j = _pedir(app)
    for x in j['cambiar_en_batch']:
        assert x.get('motivo'), x
        assert x.get('usado_en') and x['n_usos'] >= 1, x
        for u in x['usado_en']:
            assert u.get('producto'), u


def test_NO_inventa_un_codigo_cuando_no_lo_sabe(app, db_clean):
    """Si no hay código propuesto se DECLARA (sin_codigo_propuesto), no se rellena con el más
    parecido: proponerle al DT un código adivinado es peor que decirle que falta (M19)."""
    j = _pedir(app)
    sin = set(j['sin_codigo_propuesto'])
    for x in j['cambiar_en_batch']:
        if not x.get('codigo_correcto'):
            assert x['codigo_en_batch'] in sin, x
        else:
            assert x.get('material_correcto'), (
                'propone un código pero no dice qué material es: %r' % x)


def test_el_que_esta_bien_muestra_el_material_de_eos(app, db_clean):
    j = _pedir(app)
    for x in j['ya_estan_bien'][:20]:
        assert x.get('en_eos'), x


def test_NO_marca_por_parecido_de_NOMBRE(app, db_clean):
    """El error que casi le mando al Director Técnico (1-ago).

    La primera versión comparaba el nombre del batch contra el de EOS y daba **44** a cambiar
    cuando son ~12: "Alantoina" no matchea "Alantoína", "Glicerina" no matchea "Glycerin",
    "Niacinamida" no matchea "Niacinamide". Habrían sido 32 correcciones FALSAS -- y una lista
    con ese ruido se descarta entera, incluidas las que sí importan.

    La clasificación va por EVIDENCIA: el código está mal sólo si no existe en el maestro o si
    la reconciliación produjo un par (misma fórmula, mismo porcentaje, otro código).
    """
    j = _pedir(app)
    # estos existen en EOS y están bien; su nombre difiere sólo por tilde o idioma
    sanos = {'MP00047': 'Alantoína', 'MP00195': 'Glycerin', 'MP00148': 'Niacinamide',
             'MP00226': 'Ectoin', 'MP00163': 'hialurónico'}
    mal = {x['codigo_en_batch'] for x in j['cambiar_en_batch']}
    for cod, pista in sanos.items():
        assert cod not in mal, (
            '%s (%s) está bien en EOS y lo marcó para cambiar · vuelve el match por nombre'
            % (cod, pista))


def test_lo_marcado_tiene_evidencia_dura(app, db_clean):
    """Cada uno a cambiar: o no existe en el maestro, o hay un par de la reconciliación."""
    import json
    j = _pedir(app)
    r = _login(app).get('/api/programacion/unificar-codigos-batch')
    plan = r.get_json()
    con_par = {d['codigo_batch'] for d in plan['seguros'] + plan['bloqueados']}
    for x in j['cambiar_en_batch']:
        assert (x['codigo_en_batch'] in con_par) or not x.get('codigo_correcto'), (
            'marcado sin evidencia: %r' % x)
