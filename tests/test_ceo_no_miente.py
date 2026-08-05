# -*- coding: utf-8 -*-
"""El tablero del CEO deja de mentir, y trae lo que le faltaba (5-ago).

Sebastián: *"el módulo CEO sigue estando pobre, no tiene premium, no tiene las cosas necesarias;
digamos no me sale caja menor, la parte de influencers la veo fea (...) no está jalando cosas de
los módulos necesarios"*.

Un tablero que miente es peor que uno pobre: el pobre se ignora, el que miente se cree — y sobre
él se decide. Por eso el orden fue **primero que no mienta**, después lo que falta, y al final lo
estético; maquillar un número falso lo único que hace es volverlo más creíble.

Lo que se encontró y estos tests protegen:

- `/api/gerencia/dashboard-extra` devolvía **500 en producción** por un `ORDER BY` con alias
  dentro de una expresión — PostgreSQL sólo lo acepta solo. Los **8 paneles** de "Metas
  estratégicas" quedaban en "Cargando…" para siempre, y en SQLite (los tests) pasaba: drift puro.
- `date` **nunca se importó** y se usa en dos sitios, los dos dentro de un `except`: los días de
  tránsito de TODAS las OCs daban 0 y los días de vencimiento del SGSST daban 999 (todo verde).
- Cinco campos se **pintaban sin calcularse**, uno de ellos dentro de una **alerta roja**
  ("Déficit total: 0.0 kg" — grita y se contradice sola).
- **Caja menor no existía en una sola línea** del módulo del CEO. Lo que veía como "Saldo de
  caja" es un número que él mismo teclea una vez al mes.
"""
import io
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(rel):
    return io.open(os.path.join(RAIZ, rel), encoding='utf-8').read()


def _sin_comentarios(txt):
    """Saca los comentarios (Python `#` y JS `//`) antes de buscar.

    ⚠ Van CUATRO veces que un test busca un nombre en el fuente y encuentra MI PROPIO COMENTARIO
    explicando por qué ese nombre dejó de usarse — o sea que pasa o falla por la razón
    equivocada (M154). Cuando se verifica por texto, los comentarios se quitan primero."""
    fuera = []
    for ln in txt.splitlines():
        _s = ln.strip()
        if _s.startswith('#') or _s.startswith('//') or _s.startswith('*'):
            continue
        ln = re.sub(r'\s+//\s.*$', '', ln)
        ln = re.sub(r'\s+#\s.*$', '', ln)
        fuera.append(ln)
    return chr(10).join(fuera)


def _html_gerencia():
    """El HTML FINAL, no el literal del fuente (M65)."""
    import sys
    api = os.path.join(RAIZ, 'api')
    if api not in sys.path:
        sys.path.insert(0, api)
    from templates_py.gerencia_html import GERENCIA_HTML
    return GERENCIA_HTML


# ── 1 · lo que rompía el endpoint en producción ──────────────────────────────

def test_el_stock_critico_usa_el_canonico_y_NO_revienta_en_PG(app, db_clean):
    """El `ORDER BY (alias / columna)` dejaba 8 paneles muertos en producción. Y el CASE que
    tenía era la TERCERA definición de "cuánta MP hay" en el mismo archivo."""
    g = _sin_comentarios(_src('api/blueprints/gerencia.py'))
    assert 'ORDER BY (stock_actual / m.stock_minimo)' not in g, \
        'volvió el ORDER BY con alias dentro de una expresión · eso es 500 en PostgreSQL'
    assert '_get_mp_stock' in g, 'no usa el stock canónico'
    # El ancla va sobre CÓDIGO, no sobre un comentario: `_sin_comentarios` justamente los quita,
    # así que anclar en `# Stock critico` daba -1 con el archivo correcto.
    i = g.find('_stk = _gmp(conn)')
    assert i > 0, 'no encontré la lectura del stock canónico'
    bloque = g[i:g.find('stock_critico = [', i) + 200]
    assert 'LEFT JOIN movimientos' not in bloque, 'sigue el JOIN sobre todo el kardex'


def test_el_endpoint_de_metas_estrategicas_RESPONDE(app, admin_client, db_clean):
    """El que vale: ejecutarlo. Leer el SQL no habría visto que estaba caído."""
    r = admin_client.get('/api/gerencia/dashboard-extra')
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert isinstance(d, dict) and 'stock_critico' in d


def test_date_esta_IMPORTADO(app, db_clean):
    """Dos NameError tapados por `except`: días de tránsito 0 siempre y SGSST 999 siempre."""
    g = _src('api/blueprints/gerencia.py')
    m = re.search(r'^from datetime import ([^\n]+)$', g, re.M)
    assert m, 'no encontré el import de datetime'
    assert 'date' in [x.strip() for x in m.group(1).split(',')], \
        '`date` sigue sin importarse, y el módulo lo usa en dos sitios'


def test_los_KPIs_del_CEO_RESPONDEN(app, admin_client, db_clean):
    r = admin_client.get('/api/gerencia/kpis')
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert 'mps_total' in d['espagiria'], 'falta el denominador del "N bajo mínimo"'
    # los kg del mes salen de una columna que EXISTE
    assert 'kg_mes' in d['espagiria']


# ── 2 · lo que se pintaba sin calcularse ─────────────────────────────────────

def test_NO_quedan_campos_pintados_que_nadie_calcula(app, db_clean):
    """Un cero que nadie calculó se lee como "no hay nada que hacer" y significa lo contrario:
    "no se midió" (M154)."""
    h = _sin_comentarios(_html_gerencia())
    for inventado in ('deficit_total_kg', 'valor_ocs_pendientes', 'valor_pedidos_activos',
                      'ultimo_pedido_fm'):
        assert inventado not in h, \
            'el tablero vuelve a pintar "%s", que el endpoint nunca devuelve' % inventado


def test_la_ALERTA_ROJA_no_afirma_un_numero_inventado(app, db_clean):
    """Era el peor de todos: una alerta roja que decía "Déficit total: 0.0 kg"."""
    h = _html_gerencia()
    h = _sin_comentarios(h)
    i = h.find('materias primas bajo el mínimo')
    assert i > 0, 'se perdió la alerta de MPs bajo mínimo'
    assert 'Déficit total' not in h[i - 200:i + 300], 'la alerta volvió a afirmar un déficit'


def test_los_SEMAFOROS_leen_lo_que_el_endpoint_manda(app, db_clean):
    """Leían `sem.inventario` y `sem.fm`, que no existen → estaban SIEMPRE en verde, o sea que
    eran decoración."""
    h = _sin_comentarios(_html_gerencia())
    assert 'sem.inventario' not in h and 'sem.fm' not in h, \
        'los semáforos vuelven a leer claves que el endpoint no manda'
    assert 'sem.mps' in h and 'sem.vencimientos' in h, 'no leen las claves reales'
    # y toman lo PEOR de sus componentes · un semáforo que promedia esconde el problema
    assert "indexOf('rojo')" in h


def test_la_NOMINA_no_se_teclea_dos_veces(app, db_clean):
    """El KPI ya la deriva de lo que RRHH aprobó. Un campo manual al lado sería un SEGUNDO
    origen del mismo hecho, y dos orígenes divergen siempre (M99). Encima lo que se escribía se
    descartaba: la tabla no tiene esa columna."""
    h = _sin_comentarios(_html_gerencia())
    assert 'id="inp-nomina"' not in h, 'volvió el campo manual de nómina'
    assert 'nomina_total:' not in h, 'sigue enviando un campo que nadie guarda'
    assert 'inp-nomina-vista' in h, 'no muestra la nómina derivada'


def test_el_periodo_contable_va_anclado_a_COLOMBIA(app, db_clean):
    """El server corre en UTC: la noche del último día del mes, la nómina y la producción se
    buscaban en el mes SIGUIENTE y salían en cero (M24)."""
    g = _sin_comentarios(_src('api/blueprints/gerencia.py'))
    for viejo in ("periodo_nom = _date2.today()", "mes_str_prod = _date2.today()"):
        assert viejo not in g, 'vuelve a anclar un período contable al UTC del server: %s' % viejo


# ── 3 · lo que faltaba: caja menor e influencers ─────────────────────────────

def test_el_CEO_ve_la_CAJA_MENOR(app, admin_client, db_clean):
    """No estaba en una sola línea del módulo. Lo que veía era `gerencia_inputs.saldo_caja`,
    que él mismo teclea una vez al mes."""
    r = admin_client.get('/api/gerencia/decisiones-ceo')
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert d.get('caja') is not None, 'la caja no llegó al tablero'
    for k in ('saldo', 'comprometido', 'disponible', 'esperan_n', 'pendientes'):
        assert k in d['caja'], 'falta %s' % k
    # lo AUTORIZADO y sin pagar ya está comprometido aunque siga en la gaveta
    assert d['caja']['disponible'] == round(d['caja']['saldo'] - d['caja']['comprometido'], 2)


def test_el_saldo_del_CEO_es_el_MISMO_que_el_de_la_caja(app, admin_client, db_clean):
    """Si el tablero recalculara la caja, en un mes habría dos números para el mismo hecho —
    que es exactamente lo que ya pasaba con el stock de MP, contado de tres formas."""
    a = admin_client.get('/api/gerencia/decisiones-ceo').get_json()['caja']['saldo']
    b = admin_client.get('/api/caja/solicitudes').get_json()['saldo']
    assert abs(float(a) - float(b)) < 0.01, \
        'el CEO ve un saldo de caja distinto al del módulo dueño: %s vs %s' % (a, b)


def test_el_CEO_ve_los_pagos_a_creadores_CON_NOMBRE(app, admin_client, db_clean):
    """Eran dos agregados, uno en cero permanente por una columna que no existe. El detalle ya
    estaba resuelto en el hub · se reusa, no se recalcula."""
    d = admin_client.get('/api/gerencia/decisiones-ceo').get_json()
    assert d.get('influencers') is not None
    for k in ('pendientes', 'n', 'monto', 'vencidos_n'):
        assert k in d['influencers'], 'falta %s' % k
    g = _src('api/blueprints/gerencia.py')
    assert '_pagos_influencer_pendientes' in g, 'no reusa el helper del hub'


def test_los_influencers_ya_NO_se_buscan_por_una_columna_INEXISTENTE(app, db_clean):
    """`ordenes_compra.area_solicitante` no existe en ningún CREATE ni ALTER del repo · el
    `except` dejaba el conteo en 0 permanente."""
    g = _sin_comentarios(_src('api/blueprints/gerencia.py'))
    assert 'area_solicitante' not in g, 'sigue consultando una columna que no existe'
    assert 'oc.categoria' in g, 'no usa la columna que Marketing sí escribe'


def test_el_bloque_de_decisiones_se_pinta_ARRIBA(app, db_clean):
    """Un tablero de CEO se abre para decidir, no para mirar: lo primero tiene que ser lo que
    espera su firma."""
    h = _html_gerencia()
    i = h.find('id="ceo-decisiones"')
    assert i > 0, 'no está el bloque de decisiones'
    assert i < h.find('id="alertas-panel"'), 'el bloque quedó debajo de las alertas'
    assert i < h.find('💰 Financiero del mes'), 'el bloque quedó debajo del financiero'


def test_un_bloque_que_falla_NO_se_lleva_la_pantalla(app, admin_client, db_clean):
    """Cada bloque va aislado y lo que no se pudo medir se DECLARA: si un `None` se pintara como
    0, el tablero diría "nada que hacer" cuando en realidad no pudo mirar."""
    g = _src('api/blueprints/gerencia.py')
    i = g.find('def gerencia_decisiones_ceo')
    bloque = g[i:i + 7000]
    assert bloque.count('except Exception as e:') >= 4, 'los bloques no están aislados'
    assert bloque.count("out['avisos'].append") >= 4, 'un bloque caído no deja aviso'
    # y el front pinta ese aviso
    assert 'ceo-aviso' in _html_gerencia()


# ── 4 · premium y sin deuda nueva ────────────────────────────────────────────

def test_el_bloque_nuevo_usa_TOKENS(app, db_clean):
    """Regla 0 del proyecto · y un hex fijo con el texto en token da contraste 1.0 al invertir
    el tema (M114)."""
    h = _html_gerencia()
    i = h.find('.ceo-dec-grid')
    j = h.find('.sem.verde', i)
    assert 0 < i < j
    css = h[i:j]
    hexes = re.findall(r'(?<!\w)#[0-9a-fA-F]{3,8}\b', css)
    assert not hexes, 'el CSS nuevo del CEO trae hex sueltos: %s' % hexes


def test_el_JS_del_tablero_sigue_siendo_VALIDO(app, db_clean):
    """node --check del valor EVALUADO · el AST de Python pasa igual con el `<script>` roto."""
    import ast
    import subprocess
    import tempfile
    import pytest
    try:
        subprocess.run(['node', '--version'], capture_output=True, check=True)
    except Exception:
        pytest.skip('sin node en este entorno')
    src = _src('api/templates_py/gerencia_html.py')
    big = max((n.value.value for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
               and isinstance(n.value.value, str)), key=len)
    tmp = tempfile.mkdtemp()
    for i, blk in enumerate(re.findall(r'<script[^>]*>(.*?)</script>', big, re.S)):
        if not blk.strip():
            continue
        f = os.path.join(tmp, 'g%d.js' % i)
        io.open(f, 'w', encoding='utf-8').write(blk)
        r = subprocess.run(['node', '--check', f], capture_output=True, text=True)
        assert r.returncode == 0, 'JS roto en el bloque %d: %s' % (i, r.stderr[:400])


def test_toda_funcion_que_el_tablero_LLAMA_existe(app, db_clean):
    """Un botón que llama a una función inexistente no da error visible: no hace nada (M146)."""
    h = _html_gerencia()
    js = '\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', h, re.S))
    definidas = set(re.findall(r'function\s+([A-Za-z_$][\w$]*)', js))
    definidas |= set(re.findall(r'(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=', js))
    for nom in re.findall(r'on(?:click|change|input|submit)="([A-Za-z_$][\w$]*)\(', h):
        assert nom in definidas, 'el HTML llama a %s() y no está definida' % nom
