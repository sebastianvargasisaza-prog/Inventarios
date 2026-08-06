# -*- coding: utf-8 -*-
"""Las pestañas AP, AR y Capital de Trabajo ABREN CON ALGO.

Sebastián, revisando Tesorería: *"mira que no está conectado, organiza que no quede muerto"*.

Medido: `loadAPaging` / `loadARaging` / `loadWorkingCapital` -- que las llama `goTab` -- escribían
en `ap-content` / `ar-content` / `wc-content`, y el HTML tiene `ap-table`, `ar-table`, `wc-kpis`.
Los dos lados se renombraron por separado.

Y lo peor no fue el rename: cada función hacía `if(!el) return;`, así que **fallaba en silencio
por diseño**. La pestaña abría vacía sin un rastro en consola, y una pantalla vacía se lee como
"no hay datos" -- que es lo contrario de lo que pasaba (M100/M112).

⚠ Acá corresponde CONECTAR, no borrar: los tres endpoints existen y devuelven estructura real
(buckets por antigüedad, DSO/DPO/CCC, burn rate, runway). No confundir con las consultas AR/AP que
sí se borraron del tablero del CEO (M161): allá los conceptos eran inventados.
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))


def _html():
    from templates_py.financiero_html import FINANCIERO_HTML
    return FINANCIERO_HTML


def _js():
    return re.sub(r'//[^\n]*', '', _html())


def test_ninguna_pestana_escribe_en_un_contenedor_INEXISTENTE(app, db_clean):
    """El chequeo barato que caza el par disparador↔destino roto (M112)."""
    H, js = _html(), _js()
    ids = set(re.findall(r'id="([^"]+)"', H))
    creados = set(re.findall(r"id\s*=\s*['\"]([^'\"]+)['\"]", js))
    for base in ('ap', 'ar', 'wc'):
        i = js.find("_finCont('%s'" % base)
        assert i > 0, 'la pestaña %s no resuelve su contenedor' % base
    # los que el resolvedor prueba tienen que existir de verdad al menos uno por pestaña
    for base in ('ap', 'ar', 'wc'):
        cands = [base + s for s in ('-content', '-table', '-kpis', '-ccc')]
        assert any(c in ids or c in creados for c in cands), \
            'la pestaña %s no tiene NINGÚN contenedor donde pintar' % base


def test_las_tres_siguen_siendo_ASYNC(app, db_clean):
    """Usan `await` · perder el `async` rompe el bloque entero de JS, no sólo la función."""
    js = _js()
    for f in ('loadAPaging', 'loadARaging', 'loadWorkingCapital'):
        i = js.find('function ' + f)
        assert i > 0, f
        assert js[max(0, i - 6):i].strip() == 'async', '%s perdió el async' % f


def test_si_no_hay_donde_pintar_lo_DICE(app, db_clean):
    """El `if(!el) return` silencioso es lo que dejó tres pestañas en blanco durante meses sin
    que nadie pudiera notarlo. Ahora la pantalla declara el problema (M100)."""
    js = _js()
    # ⚠ Con el parentesis: `function _finSinDondeVIEJO` CONTIENE `function _finSinDonde` y el
    # test pasaba en verde con la funcion renombrada (M154).
    assert 'function _finSinDonde(' in js, 'no hay aviso cuando falta el contenedor'
    for base in ('ap', 'ar', 'wc'):
        i = js.find("_finCont('%s'" % base)
        bloque = js[i:i + 220]
        assert '_finSinDonde' in bloque, 'la pestaña %s vuelve a fallar en silencio' % base


def test_el_resolvedor_avisa_en_consola(app, db_clean):
    """Un helper que devuelve null sin decir nada reintroduce el silencio que se vino a quitar."""
    js = _js()
    i = js.find('function _finCont')
    bloque = js[i:i + 600]
    assert 'console.warn' in bloque, 'el resolvedor se queda mudo cuando no encuentra nada'


def test_los_TRES_endpoints_responden(app, admin_client, db_clean):
    """La razón por la que esto se CONECTA en vez de borrarse: los números existen."""
    for u in ('/api/financiero/ar-aging', '/api/financiero/ap-aging',
              '/api/financiero/working-capital'):
        r = admin_client.get(u)
        assert r.status_code == 200, '%s -> %s' % (u, r.status_code)
        d = r.get_json()
        assert isinstance(d, dict) and d, u


def test_la_estructura_que_devuelven_es_la_que_la_pantalla_pinta(app, admin_client, db_clean):
    """Si el endpoint cambiara de forma, la pestaña volvería a verse vacía sin error (M5)."""
    d = admin_client.get('/api/financiero/ar-aging').get_json()
    assert 'buckets' in d, d.keys()
    for b in ('corriente', 'dias_30', 'dias_60', 'dias_90'):
        assert b in d['buckets'], 'falta el bucket %s que la pantalla pinta' % b
    w = admin_client.get('/api/financiero/working-capital').get_json()
    for k in ('working_capital', 'ar_total', 'ap_total', 'cash', 'burn_rate', 'runway_meses'):
        assert k in w, 'falta %s que la tarjeta muestra' % k
