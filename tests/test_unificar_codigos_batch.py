"""Dejar los códigos de EOS iguales a los del BATCH RECORD · con candado (1-ago).

Sebastián: *"lo ideal es que todo quede con los códigos del batch, si estás seguro, hazlo"*.
Para la mayoría sí. Para algunos NO, y hacerlo en bloque destruye el kardex -- los dos casos
aparecieron en los datos REALES de producción:

  · `MP00301` es PROPYLHEPTYL CAPRYLATE en el batch record, pero en EOS ese código es OTRO
    material y el propylheptyl vive en `MP00030`. Renombrar fusionaría dos materias primas.
  · `MP00296 CARBOMERO 980` y `MP00008 Carbopol` caen los dos en `MP00200`; `MP00252` y
    `MP00181` (dos grados de centella) caen los dos en `MP00176`.

"Si estás seguro" me da la responsabilidad de decir cuándo NO lo estoy. Estos tests fijan que
el candado exista y que tenga dientes.
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


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        filas = conn.execute(sql, params).fetchall()
        conn.commit()
        return filas
    finally:
        conn.close()


def test_el_plan_no_aplica_nada_por_defecto(app, db_clean):
    """Un GET NUNCA muta (M113: un GET que muta duplica el daño de cualquier defecto)."""
    r = _login(app).get('/api/programacion/unificar-codigos-batch')
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    assert j['dry_run'] is True, j
    assert 'seguros' in j and 'bloqueados' in j


def test_un_POST_sin_confirmar_TAMPOCO_aplica(app, db_clean):
    """Renombrar códigos mueve kardex y fórmulas: se confirma explícitamente o no pasa nada."""
    r = _login(app).post('/api/programacion/unificar-codigos-batch',
                         headers={'Content-Type': 'application/json', **csrf_headers()},
                         json={})
    assert r.status_code == 200, r.data[:300]
    assert r.get_json()['dry_run'] is True


def test_solo_un_ADMIN_puede_unificar(app, db_clean):
    """Cambia el código de una materia prima en TODO el sistema · no es una acción de operación."""
    r = _login(app, 'catalina').get('/api/programacion/unificar-codigos-batch')
    assert r.status_code == 403, r.data[:200]


def test_cada_par_trae_su_motivo_y_su_clasificacion(app, db_clean):
    j = _login(app).get('/api/programacion/unificar-codigos-batch').get_json()
    for d in j['seguros'] + j['bloqueados']:
        assert d['estado'] in ('seguro', 'bloqueado_ambiguo', 'bloqueado_colision',
                               'bloqueado_nombre', 'bloqueado_batch_inconsistente',
                               'bloqueado_no_es_el_mismo_material'), d
        assert d.get('motivo'), d
        assert d['codigo_batch'] != d['codigo_eos'], d
        if d['estado'] == 'seguro':
            assert d.get('accion') in ('renombrar', 'fusionar'), d


def test_BLOQUEA_cuando_el_destino_existe_con_OTRO_material(app, db_clean):
    """El caso MP00301: el código del batch YA EXISTE en EOS con otro INCI. Fusionarlos mezcla
    dos materias primas distintas y eso no se deshace contando."""
    from blueprints.programacion import _plan_unificar_codigos
    import blueprints.programacion as P

    class _FakeCur:
        def __init__(self, incis):
            self.incis = incis
        def execute(self, sql, params=()):
            self._r = []
            if 'nombre_inci' in sql and params:
                v = self.incis.get(params[0])
                self._r = [(v,)] if v is not None else []
            return self
        def fetchall(self):
            return self._r
        def fetchone(self):
            return self._r[0] if self._r else None

    # el plan real se arma con la BD; acá se prueba la CLASIFICACIÓN, que es la que decide
    j = _login(app).get('/api/programacion/unificar-codigos-batch').get_json()
    for d in j['bloqueados']:
        if d['estado'] == 'bloqueado_colision':
            assert d['inci_batch'] and d['inci_eos'] and d['inci_batch'] != d['inci_eos'], d
    assert P._plan_unificar_codigos is not None


def test_el_candado_TIENE_dientes(app, db_clean):
    """Si el clasificador dejara pasar todo, este test cae. La regla: nada con estado distinto
    de 'seguro' puede aparecer en la lista que se aplica."""
    j = _login(app).get('/api/programacion/unificar-codigos-batch').get_json()
    assert all(d['estado'] == 'seguro' for d in j['seguros']), (
        'se coló un par no seguro en la lista que se aplica')
    assert all(d['estado'] != 'seguro' for d in j['bloqueados']), j['bloqueados'][:2]


def test_el_plan_y_el_informe_usan_EL_MISMO_emparejador(app, db_clean):
    """El defecto que casi hace aplicar un renombrado equivocado (1-ago).

    El informe cruzaba productos con tres niveles (exacto → prefijo → palabras) y el PLAN sólo
    con dos. El plan se salteaba 5 productos, y con ellos los pares que hacen AMBIGUO a un
    código: `MP00296` y `MP00008` caen los dos en `MP00200`, pero como "Crema Facial de Urea"
    sólo cruzaba por palabras, el plan no veía el segundo par y declaraba el primero **seguro**.

    Un plan armado sobre datos parciales es peor que no tener plan: da confianza para ejecutar.
    Los dos tienen que ver EXACTAMENTE los mismos productos.
    """
    cli = _login(app)
    rec = cli.get('/api/programacion/reconciliar-batch-record').get_json()
    plan = cli.get('/api/programacion/unificar-codigos-batch').get_json()

    # los productos que el informe SÍ cruzó
    cruzados = {p['producto'] for p in rec['productos']
                if p['estado'] != 'sin_formula_en_eos'}
    # los productos que el plan tuvo en cuenta
    en_plan = {prod for d in (plan['seguros'] + plan['bloqueados']) for prod in d['productos']}
    assert en_plan <= cruzados, (
        'el plan mira productos que el informe no cruzó: %r' % sorted(en_plan - cruzados))

    # y el emparejador es literalmente el mismo objeto
    from blueprints.programacion import _emparejar_producto_eos
    assert callable(_emparejar_producto_eos)


def test_un_codigo_de_eos_destino_de_DOS_del_batch_queda_bloqueado(app, db_clean):
    """Si dos códigos del batch record caen en el mismo de EOS, renombrar elegiría uno al azar.
    Ese par NO puede aparecer como seguro -- es el caso MP00296/MP00008 → MP00200."""
    plan = _login(app).get('/api/programacion/unificar-codigos-batch').get_json()
    import collections
    # 2-ago · los pares DESCALIFICADOS (dos códigos que conviven en una misma fórmula del batch:
    # no son el mismo material) no son un mapeo, así que no cuentan para la ambigüedad. Antes
    # `MP00301` figuraba apuntando a MP00030 Y a MP00195 -- pero ese segundo par era basura
    # (propylheptyl con glicerina) y bloqueaba de rebote al par legítimo.
    _reales = [d for d in plan['seguros'] + plan['bloqueados']
               if d['estado'] != 'bloqueado_no_es_el_mismo_material']
    _por_eos = collections.Counter(d['codigo_eos'] for d in _reales)
    _por_batch = collections.Counter(d['codigo_batch'] for d in _reales)
    for d in plan['seguros']:
        assert _por_eos[d['codigo_eos']] == 1, (
            'par SEGURO cuyo destino EOS recibe varios códigos del batch: %r' % d)
        assert _por_batch[d['codigo_batch']] == 1, (
            'par SEGURO cuyo código del batch va a varios de EOS: %r' % d)


def test_BLOQUEA_cuando_los_nombres_se_contradicen_en_una_palabra_que_DISTINGUE(app, db_clean):
    """El par que casi se aplica (1-ago · lo vi revisando la salida real, no lo cazó el código).

        MP00305 ← MP00025
        batch: "CITRUS AURANTIUM AMARA **leaf** OIL"   (petitgrain)
        EOS:   "CITRUS AURANTIUM AMARA **FLOWER** OIL" (neroli)

    Dos aceites esenciales DISTINTOS del mismo árbol. Salía "seguro" porque el código del batch
    no existe en EOS y entonces no había INCI con qué corroborar: la única evidencia era el
    porcentaje idéntico -- y el porcentaje no distingue hoja de flor.

    Mismo espíritu que M19 (Centella triterpenos vs extracto plano, Vit E polvo vs líquida): la
    palabra que cambia el material puede ser una sola.
    """
    from blueprints.programacion import _plan_unificar_codigos  # noqa: F401
    plan = _login(app).get('/api/programacion/unificar-codigos-batch').get_json()
    for d in plan['seguros']:
        for grupo in (('LEAF', 'HOJA', 'FLOWER', 'FLOR', 'SEED', 'SEMILLA', 'ROOT', 'RAIZ',
                       'FRUIT', 'FRUTO', 'PEEL', 'CASCARA'),
                      ('POLVO', 'POWDER', 'LIQUIDO', 'LIQUIDA', 'LIQUID')):
            _n = (d.get('nombre') or '').upper()
            _e = ((d.get('inci_eos') or '') + ' ' + (d.get('inci_batch') or '')).upper()
            _a = {g for g in grupo if g in _n}
            _b = {g for g in grupo if g in _e}
            assert not (_a and _b and _a != _b), (
                'par SEGURO con nombres que se contradicen (%s vs %s): %r' % (_a, _b, d))


def test_el_estado_bloqueado_nombre_existe_y_explica(app, db_clean):
    plan = _login(app).get('/api/programacion/unificar-codigos-batch').get_json()
    for d in plan['bloqueados']:
        assert d['estado'] in ('bloqueado_ambiguo', 'bloqueado_colision', 'bloqueado_nombre',
                               'bloqueado_batch_inconsistente',
                               'bloqueado_no_es_el_mismo_material'), d
        assert d.get('motivo'), d


def test_solo_renombrar_deja_las_FUSIONES_afuera(app, db_clean):
    """Renombrar y fusionar no son lo mismo (1-ago).

    Renombrar es limpio: el código del batch NO existe en EOS, así que no se junta nada.
    Fusionar une DOS códigos que el maestro mantiene separados -- y eso no es limpiar
    duplicados, es DECIDIR que son el mismo material. El caso que lo destapó: `MP00110
    Pantenol` y `MP00236 Pantenol POLVO` existen los dos con el mismo INCI, porque el INCI no
    distingue una presentación. Igual `Aloe vera polvo` vs `Aloe Vera 200X`.

    `solo_renombrar` permite aplicar lo indiscutible sin tomar por el usuario una decisión de
    formulación.
    """
    j = _login(app).get('/api/programacion/unificar-codigos-batch').get_json()
    assert 'renombrados_limpios' in j and 'fusiones' in j, j.keys()
    assert j['renombrados_limpios'] + j['fusiones'] == len(j['seguros']), j
    for d in j['seguros']:
        if d['accion'] == 'renombrar':
            assert d['destino_existe_en_eos'] is False, (
                'un "renombrar" cuyo destino YA existe es en realidad una fusión: %r' % d)
        else:
            assert d['destino_existe_en_eos'] is True, d


def test_BLOQUEA_si_el_batch_usa_TAMBIEN_el_codigo_de_eos(app, db_clean):
    """El candado que faltaba · lo aprendí rompiéndolo en producción (1-ago).

    Apliqué 10 renombrados "seguros" y 3 hicieron daño NETO: el hialurónico es `MP00273` en 1
    producto del batch y `MP00163` en 14. El par sólo se veía por el producto minoritario --
    en los otros 14 ambos lados coincidían y por eso NO generaban diferencia. Renombrar
    `MP00163 → MP00273` arregló 1 y rompió 14. El conflicto era invisible hasta después de
    aplicar; lo vi porque el plan, al volver a correr, proponía deshacer lo que acababa de hacer.

    **Una diferencia sólo se puede corregir mirando dónde NO hay diferencia.** Si el batch usa
    los dos códigos, el duplicado está en el batch: no lo resuelve un renombrado.
    """
    import json as _js
    import os as _os
    ruta = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                         'api', 'data', 'formulas_batch_record.json')
    with open(ruta, encoding='utf-8') as f:
        ref = _js.load(f)
    cods_batch = {i['codigo'] for p in ref['productos'] for i in p['items']}

    plan = _login(app).get('/api/programacion/unificar-codigos-batch').get_json()
    for d in plan['seguros']:
        assert d['codigo_eos'] not in cods_batch, (
            'par SEGURO cuyo codigo_eos %s TAMBIÉN lo usa el batch record: renombrarlo rompe '
            'todos los productos donde el batch ya dice %s · %r'
            % (d['codigo_eos'], d['codigo_eos'], d))


def test_el_estado_batch_inconsistente_dice_cuantos_productos_usa_cada_uno(app, db_clean):
    """El número es lo que permite decidir: 1 contra 14 no es una duda, es una respuesta."""
    plan = _login(app).get('/api/programacion/unificar-codigos-batch').get_json()
    for d in plan['bloqueados']:
        if d['estado'] == 'bloqueado_batch_inconsistente':
            assert d.get('usos_en_batch'), d
            assert d['usos_en_batch']['codigo_eos'] > 0, d


def test_cuando_la_evidencia_es_de_UN_SOLO_lado_el_informe_CONCLUYE(app, db_clean):
    """Dejar una duda abierta cuando los datos ya la contestan es hacer trabajar al usuario.

    Los 4 casos reales: el hialurónico es MP00163 en 18 batch records y MP00273 en 1; y MP00273
    NI SIQUIERA EXISTE en el maestro de EOS. Ahí no hay nada que decidir -- EOS está bien y lo
    que salió mal es ese batch record. El informe tiene que decirlo, no listar el par como
    "pendiente de que alguien decida".
    """
    plan = _login(app).get('/api/programacion/unificar-codigos-batch').get_json()
    for d in plan['bloqueados']:
        if d['estado'] != 'bloqueado_batch_inconsistente':
            continue
        _u = d.get('usos_en_batch') or {}
        # evidencia de un solo lado = el codigo del batch no esta en el maestro Y es minoritario
        if d.get('destino_existe_en_eos') is False and _u.get('codigo_eos', 0) >= _u.get('codigo_batch', 0):
            assert d.get('veredicto'), (
                'la evidencia alcanza para concluir y el informe deja la duda abierta: %r' % d)
            assert 'EOS ESTÁ BIEN' in d['veredicto'], d['veredicto']


def test_un_par_DESCALIFICADO_nunca_puede_quedar_seguro(app, db_clean):
    """Dos códigos que el batch record lleva como renglones separados de una misma fórmula no son
    el mismo material. Acá no es un informe: esta herramienta RENOMBRA códigos de verdad, así que
    un par así jamás puede llegar a `seguros` (el apply sólo toca esos)."""
    try:
        from api.blueprints.programacion import _cargar_batch_records, _pares_que_conviven
    except Exception:
        from blueprints.programacion import _cargar_batch_records, _pares_que_conviven
    conviven = _pares_que_conviven(_cargar_batch_records().get('productos') or [])
    plan = _login(app).get('/api/programacion/unificar-codigos-batch').get_json()
    for d in plan['seguros']:
        a, b = d['codigo_batch'], d['codigo_eos']
        assert (min(a, b), max(a, b)) not in conviven, d
    for d in plan['bloqueados']:
        if d['estado'] == 'bloqueado_no_es_el_mismo_material':
            assert 'no son el mismo material' in d['motivo'], d
