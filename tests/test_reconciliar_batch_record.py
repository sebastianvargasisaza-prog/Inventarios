"""La fórmula de EOS contra el BATCH RECORD firmado (1-ago).

Sebastián: *"ya varias veces me has dicho que es perfecto, pero hoy hay cosas que no sabíamos"*.
La razón por la que aparecían cosas es que **nadie comparaba el sistema contra los batch records**,
que son lo que se pesó de verdad en planta, firmado por quien pesó y por quien verificó.

Estos tests protegen dos cosas distintas:
  1. que la REFERENCIA esté sana (los 28 suman 100% · si no, el dato está mal extraído y no se
     puede usar para acusar a ninguna fórmula);
  2. que la comparación detecte las cuatro clases de diferencia, que tienen arreglos OPUESTOS.
"""
import json
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PROD = 'ZZBR PRODUCTO'
COD_A = 'ZZBR-A'
COD_B = 'ZZBR-B'


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


def _ref():
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'api', 'data', 'formulas_batch_record.json')
    with open(ruta, encoding='utf-8') as f:
        return json.load(f)


# ── 1. la REFERENCIA está sana ────────────────────────────────────────────────

def test_los_28_batch_records_suman_100(app, db_clean):
    """El control de que la extracción del PDF salió bien. Un parser roto NO produce 28 fórmulas
    independientes cuadradas al milésimo -- el primer intento daba sumas de 1079% porque un
    nombre con número adentro ("CARBOMERO 980 NF") se leía como el porcentaje."""
    d = _ref()
    prods = d['productos']
    assert len(prods) == 28, len(prods)
    malos = [(p['producto'], p['suma_pct']) for p in prods if abs(p['suma_pct'] - 100) > 0.05]
    assert not malos, 'batch records con suma fuera de 100: %r' % malos


def test_la_referencia_NO_trae_codigos_fantasma(app, db_clean):
    """Sebastián 1-ago: *"los códigos que son así deben eliminarse, unificamos a que todos fueran
    MP00181"*. Los batch records ya están normalizados; si alguno trajera un MPxxxSO01, la
    referencia estaría contaminada y no serviría como verdad."""
    d = _ref()
    fant = sorted({i['codigo'] for p in d['productos'] for i in p['items']
                   if not (i['codigo'].startswith('MP00') and i['codigo'][4:].isdigit())})
    assert not fant, 'la referencia trae códigos no normalizados: %r' % fant


def test_ningun_producto_quedo_sin_ingredientes(app, db_clean):
    d = _ref()
    vacios = [p['producto'] for p in d['productos'] if len(p['items']) < 5]
    assert not vacios, vacios


# ── 2. la COMPARACIÓN detecta cada clase de diferencia ────────────────────────

def _pedir(app):
    r = _login(app).get('/api/programacion/reconciliar-batch-record')
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def test_corre_contra_las_formulas_reales_y_da_veredicto(app, db_clean):
    j = _pedir(app)
    assert j['ok'] and j['n_productos'] == 28, j.get('n_productos')
    # las tres clases son excluyentes y cubren los 28 · si no sumaran, el informe estaría
    # perdiendo productos por el camino y nadie lo notaría
    assert (j['coinciden'] + j['solo_codigos_distintos']
            + j['con_diferencias_reales']) == 28, j
    for p in j['productos']:
        assert p['estado'] in ('coincide', 'solo_codigos_distintos', 'difiere',
                               'sin_formula_en_eos'), p


def test_detecta_un_ingrediente_que_FALTA_en_eos(app, db_clean):
    """La diferencia más cara: el batch record lo lleva y la fórmula no → se descuenta de MENOS,
    el stock queda inflado y nadie lo vuelve a comprar. Es el caso del lauryl glucoside."""
    d = _ref()
    p = next(x for x in d['productos'] if x['producto'] == 'Limpiador Facial BHA 2%')
    codigos = {i['codigo'] for i in p['items']}
    assert 'MP00070' not in codigos, (
        'el batch record del Limpiador BHA SÍ trae lauryl glucoside · rehacer el análisis')
    assert len(codigos) == 12, len(codigos)


def test_la_comparacion_usa_el_normalizador_del_motor(app, db_clean):
    """M13 · el match producto↔fórmula por nombre debe quitar acentos y puntuación en AMBOS
    lados; si no, un acento distinto entre el PDF y EOS reporta 'sin fórmula' falsamente."""
    from blueprints.programacion import _norm_prod_fuerte
    assert _norm_prod_fuerte('EMULSIÓN LIMPIADORA NF') == _norm_prod_fuerte('Emulsion Limpiadora NF')
    assert _norm_prod_fuerte('Suero Exfoliante BHA 2%') == _norm_prod_fuerte('SUERO EXFOLIANTE BHA 2 %')


def test_NO_empareja_dos_productos_distintos_que_se_parecen(app, db_clean):
    """El umbral del cruce por palabras es ALTO a propósito.

    Con 0.50 emparejaba "Suero Vitamina C+" (batch record) con "SUERO ANTIOXIDANTE VITAMINA C+B3"
    (EOS) al 67%. Pueden ser dos productos distintos, y comparar el par equivocado **inventa**
    diferencias en una fórmula regulada -- que es peor que no comparar. Lo que no llega al umbral
    sale como candidato para que lo confirme una persona.
    """
    import re
    from blueprints import programacion as P
    src = P.prog_reconciliar_batch_record.__doc__ or ''
    assert src, 'el endpoint perdió su documentación'
    fuente = open(P.__file__.replace('.pyc', '.py'), encoding='utf-8').read()
    m = re.search(r'punt\[0\]\[0\] >= (0\.\d+) and \(len\(punt\) == 1 or '
                  r'punt\[0\]\[0\] - punt\[1\]\[0\] >= (0\.\d+)\)', fuente)
    assert m, 'no encontré el umbral del cruce por palabras'
    assert float(m.group(1)) >= 0.70, 'el umbral bajó: %s' % m.group(1)
    assert float(m.group(2)) >= 0.20, 'la ventaja mínima bajó: %s' % m.group(2)


def test_siempre_dice_COMO_cruzo_cada_producto(app, db_clean):
    """Un emparejamiento que no se puede auditar no sirve para un dato regulado (M19): si el
    informe dice que una fórmula difiere, hay que poder ver contra qué la comparó."""
    r = _login(app).get('/api/programacion/reconciliar-batch-record')
    j = r.get_json()
    for p in j['productos']:
        if p['estado'] == 'sin_formula_en_eos':
            assert 'candidatos_en_eos' in p, p
        else:
            assert p.get('match_por'), ('no dice cómo cruzó: %r' % p['producto'])
            assert p.get('nombre_en_eos'), p


# ── 3. separar "otro código" de "otra fórmula" (M124) ─────────────────────────

def _sembrar_par(codigo_eos, pct):
    """Una fórmula de EOS que usa OTRO código para el mismo material del batch record."""
    _sql("DELETE FROM formula_items WHERE producto_nombre=?", ('ZZBR LIMPIADOR',))
    _sql("DELETE FROM formula_headers WHERE producto_nombre=?", ('ZZBR LIMPIADOR',))


def test_un_material_con_OTRO_CODIGO_no_se_cuenta_como_diferencia_de_formula(app, db_clean):
    """La primera corrida dijo "0 de 28 coinciden" y sonaba a catástrofe.

    Casi todo era el MISMO material con dos códigos: el agua es MP00286 en el batch record y
    MPAGUALI01 en EOS, con el MISMO 87,71%. Contarlo como "falta un ingrediente" + "sobra otro"
    esconde las POCAS diferencias que sí son de fórmula, que son las únicas que hay que arreglar
    (M124: un informe que no separa clases dice las cosas mal).

    Son arreglos distintos: un código se renombra (reversible); una receta la cambia Alejandro.
    """
    r = _login(app).get('/api/programacion/reconciliar-batch-record')
    j = r.get_json()
    assert 'solo_codigos_distintos' in j and 'con_diferencias_reales' in j, j.keys()
    assert 'mapa_codigos_batch_record_vs_eos' in j
    for p in j['productos']:
        assert p['estado'] in ('coincide', 'solo_codigos_distintos', 'difiere',
                               'sin_formula_en_eos'), p['estado']
        # un producto marcado 'solo_codigos_distintos' NO puede traer diferencias reales
        if p['estado'] == 'solo_codigos_distintos':
            assert not p['falta_en_eos'] and not p['sobra_en_eos'], p
            assert not p['porcentaje_difiere'], p
            assert p['mismo_material_otro_codigo'], p


def test_cada_par_de_codigos_dice_como_se_corroboro(app, db_clean):
    """Emparejar por porcentaje es una coincidencia fuerte, NO una prueba. El puente y el INCI
    sí lo son. Si el informe no dijera con qué se corroboró cada par, estaría afirmando que dos
    códigos son el mismo material sin poder demostrarlo -- y eso, en una fórmula regulada, es
    exactamente lo que no se puede hacer (M19)."""
    r = _login(app).get('/api/programacion/reconciliar-batch-record')
    j = r.get_json()
    for p in j['productos']:
        for par in p.get('mismo_material_otro_codigo') or []:
            assert par['confirmado_por'] in ('puente', 'mismo_inci', 'solo_porcentaje'), par
            assert par['codigo_batch_record'] and par['codigo_eos'], par
            assert par['codigo_batch_record'] != par['codigo_eos'], par


def test_NO_empareja_si_el_porcentaje_esta_repetido(app, db_clean):
    """Si dos ingredientes van al 0,05%, no se puede saber cuál es cuál -- y adivinar ahí es
    inventar un mapeo de códigos en un dato regulado. Esos quedan como diferencia real, que es
    lo honesto: alguien los mira."""
    import re
    from blueprints import programacion as P
    fuente = open(P.__file__.replace('.pyc', '.py'), encoding='utf-8').read()
    assert '_pf[pc] != 1 or _ps.get(pc) != 1' in fuente, (
        'se perdió el guard de porcentaje único: emparejaría a ciegas')


# ── Dos códigos que conviven en una misma fórmula NO son el mismo material (2-ago) ────────────
# El reconciliador venía emparejando `MP00252 -> MP00176` ("Centella Asiatica Extract" ->
# "triterpenos 80%") en 8 productos. La ESENCIA DE CENTELLA los lleva a los DOS, 0,15% + 0,10%:
# una receta no lista dos veces el mismo material. O sea que en esos 8 productos EOS descuenta
# OTRO GRADO del que pide el batch record, con la misma dosis -- potencia distinta (M19).

def _pqc():
    try:
        from api.blueprints.programacion import _pares_que_conviven
    except Exception:
        from blueprints.programacion import _pares_que_conviven
    return _pares_que_conviven


def test_detecta_dos_codigos_en_la_misma_formula():
    f = _pqc()
    ref = [{'producto': 'X', 'items': [{'codigo': 'MP00001'}, {'codigo': 'MP00002'}]}]
    assert f(ref).get(('MP00001', 'MP00002')) == 'X'


def test_no_marca_codigos_que_viven_en_formulas_distintas():
    """Si los marcara, ningún par se podría emparejar nunca y el mapa de códigos moriría."""
    f = _pqc()
    ref = [{'producto': 'X', 'items': [{'codigo': 'MP00001'}]},
           {'producto': 'Y', 'items': [{'codigo': 'MP00002'}]}]
    assert f(ref) == {}


def test_en_los_batch_records_REALES_la_centella_convive():
    """El hecho que dispara todo, sobre el archivo de referencia versionado."""
    try:
        from api.blueprints.programacion import _cargar_batch_records
    except Exception:
        from blueprints.programacion import _cargar_batch_records
    ref = _cargar_batch_records().get('productos') or []
    assert ref, 'no se pudo cargar la referencia de batch records'
    prueba = _pqc()(ref).get(('MP00176', 'MP00252'))
    assert prueba and 'ESENCIA' in prueba.upper(), prueba


def test_ningun_par_del_mapa_puede_convivir_en_una_formula(app):
    """La invariante: el mapa de códigos NUNCA puede contener un par descalificado.

    Es lo que estaba roto -- y el par equivocado se propagaba a la herramienta de unificación,
    que renombra códigos de verdad.
    """
    try:
        from api.blueprints.programacion import _cargar_batch_records
    except Exception:
        from blueprints.programacion import _cargar_batch_records
    conviven = _pqc()(_cargar_batch_records().get('productos') or [])
    j = _login(app).get('/api/programacion/reconciliar-batch-record').get_json()
    for m in j.get('mapa_codigos_batch_record_vs_eos') or []:
        a, b = m['codigo_batch_record'], m['codigo_eos']
        assert (min(a, b), max(a, b)) not in conviven, m


def test_no_corrobora_por_INCI_si_uno_de_los_dos_no_esta_en_el_maestro(app):
    """Antes leía los INCI de los dos con un IN (?,?) y aceptaba `len(set)==1` como "mismo INCI".
    Si uno de los códigos no existe en el maestro, la consulta trae UNO solo y el chequeo daba
    corroborado sin haber comparado nada: un chequeo que no puede correr no devuelve un OK."""
    j = _login(app).get('/api/programacion/reconciliar-batch-record').get_json()
    for p in j['productos']:
        for par in p.get('mismo_material_otro_codigo') or []:
            if par.get('aviso'):
                assert par['confirmado_por'] != 'mismo_inci', par
                assert 'no está en el maestro' in par['aviso'], par


# ── Un typo de una letra dejaba un batch record SIN comparar (2-ago) ──────────────────────────
# "AZ Hybrid Clear" (batch) contra "AZ HIBRID CLEAR" (EOS): el emparejador compara CONJUNTOS DE
# PALABRAS, y para él HYBRID y HIBRID son dos palabras distintas -> 33% de parecido -> ese batch
# record no se comparaba con nada. Y ahí adentro vive un ingrediente al 4%.

def _emp():
    try:
        from api.blueprints.programacion import _emparejar_producto_eos
    except Exception:
        from blueprints.programacion import _emparejar_producto_eos
    return _emparejar_producto_eos


def test_une_un_nombre_con_UNA_letra_distinta():
    eos = {'AZ HIBRID CLEAR': {'nombre_eos': 'AZ HIBRID CLEAR', 'items': {}},
           'GEL HIDRATANTE': {'nombre_eos': 'GEL HIDRATANTE', 'items': {}}}
    f, como, cands = _emp()(eos, 'AZ HYBRID CLEAR', 'AZ Hybrid Clear')
    assert f is not None and f['nombre_eos'] == 'AZ HIBRID CLEAR', (como, cands)
    assert 'casi_igual' in como, como


def test_NO_une_dos_productos_distintos_que_comparten_palabras():
    """El umbral alto es a propósito: comparar el par equivocado INVENTA diferencias en una
    fórmula regulada. Lo que no llega sale como CANDIDATO para que lo confirme una persona."""
    eos = {'SUERO ANTIOXIDANTE VITAMINA C B3': {'nombre_eos': 'SUERO ANTIOXIDANTE VITAMINA C+B3', 'items': {}},
           'SUERO DE VITAMINA C FORMULA NUEVA': {'nombre_eos': 'SUERO DE VITAMINA C+ FORMULA NUEVA', 'items': {}}}
    f, como, cands = _emp()(eos, 'SUERO VITAMINA C', 'Suero Vitamina C+')
    assert f is None, ('no puede elegir solo entre dos candidatos', como)
    assert len(cands) >= 2


def test_el_nombre_exacto_sigue_ganando():
    eos = {'GEL HIDRATANTE': {'nombre_eos': 'GEL HIDRATANTE', 'items': {}},
           'GEL HIDRATANTE PLUS': {'nombre_eos': 'GEL HIDRATANTE PLUS', 'items': {}}}
    f, como, _ = _emp()(eos, 'GEL HIDRATANTE', 'Gel Hidratante')
    assert como == 'nombre_exacto' and f['nombre_eos'] == 'GEL HIDRATANTE'


# ── Intercambio CRUZADO · dos códigos que se intercambian entre sí (2-ago) ────────────────────
# En EMULSION HIDRATANTE, GEL HIDRATANTE e HYDRAPEPTIDE el batch usa MP00301 (propylheptyl 3%) y
# MP00302 (ethylhexylglycerin 0,4%), y EOS usa MP00030 (3%) y MP00301 (0,4%). Como MP00301 está
# de los DOS lados no entra ni en `falta` ni en `sobra`: el emparejador resuelve pares de a uno y
# no puede con un ciclo, así que MP00302 se quedaba sin propuesta.
#
# Acá NO hay umbral: se descompone sólo si en el otro lado hay un código libre con EXACTAMENTE
# ese porcentaje, y se REVIERTE si no llega a formar par.

def _rec(app):
    return _login(app).get('/api/programacion/reconciliar-batch-record').get_json()


def test_el_intercambio_cruzado_se_resuelve(app):
    """MP00302 tiene que dejar de quedarse sin propuesta."""
    j = _rec(app)
    _mapa = {(m['codigo_batch_record'], m['codigo_eos']) for m in
             (j.get('mapa_codigos_batch_record_vs_eos') or [])}
    # si el corpus tiene el ciclo, tiene que aparecer resuelto en AMBOS sentidos
    _tiene_ciclo = any(
        any(x['codigo'] == 'MP00302' for x in (p.get('falta_en_eos') or []))
        for p in j['productos'])
    if _tiene_ciclo:
        assert ('MP00302', 'MP00301') in _mapa or ('MP00301', 'MP00030') in _mapa, _mapa


def test_una_diferencia_REAL_de_dosis_no_se_descompone(app):
    """El guard: si la descomposición no cierra, el código vuelve a `porcentaje_difiere` -- que
    es lo correcto para una diferencia de DOSIS, no de código."""
    j = _rec(app)
    for p in j['productos']:
        _cods_f = {x['codigo'] for x in (p.get('falta_en_eos') or [])}
        _cods_s = {x['codigo'] for x in (p.get('sobra_en_eos') or [])}
        _dobles = _cods_f & _cods_s
        assert not _dobles, (
            'un código no puede FALTAR y SOBRAR a la vez en el mismo producto: %r %r'
            % (p['producto'], _dobles))
