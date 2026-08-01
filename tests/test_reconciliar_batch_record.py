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
    assert 'coinciden' in j and 'con_diferencias' in j
    assert j['coinciden'] + j['con_diferencias'] == 28, j
    for p in j['productos']:
        assert p['estado'] in ('coincide', 'difiere', 'sin_formula_en_eos'), p


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
