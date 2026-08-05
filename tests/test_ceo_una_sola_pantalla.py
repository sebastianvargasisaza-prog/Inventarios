# -*- coding: utf-8 -*-
"""El CEO tiene UNA sola pantalla (5-ago).

Sebastián: *"si consolida"*. Había tres puertas al mismo trabajo — `/gerencia`, `/hoy` y
`/mi-bandeja` — y hasta el día anterior además se contradecían entre sí. Ya no se contradicen,
pero seguían siendo tres.

**La base es `/hoy`**, no `/gerencia`: tiene el conmutador de pestañas, los pagos con sus acciones
reales, y es la pantalla sobre la que Sebastián iteró (*"acá lo que hago es pagar o rechazar,
fin"*). Se le agregaron **Pendientes** (la bandeja cross-módulo, que era una pantalla huérfana a
la que ningún menú enlazaba) y **Estratégico** (metas, canal y los inputs del mes).

Lo que estos tests protegen, por orden de lo que más duele:

1. **Que ninguna pestaña deje la pantalla en blanco.** El conmutador apaga TODOS los paneles antes
   de encender el destino: una pestaña sin su panel no da error, deja la página vacía (M112/M155).
2. **Que las URLs viejas sigan llegando.** Un marcador que muere en la nada es peor que la
   pantalla vieja (M120).
3. **Que no se haya perdido nada** en la mudanza: los pagos con sus acciones, las decisiones, la
   bandeja y las metas.
"""
import io
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PANES = ('dec', 'pagos', 'pulso', 'fin', 'pend', 'estr')


def _html():
    import sys
    api = os.path.join(RAIZ, 'api')
    if api not in sys.path:
        sys.path.insert(0, api)
    from templates_py.centro_operaciones_html import HTML
    return HTML


def _src(rel):
    return io.open(os.path.join(RAIZ, rel), encoding='utf-8').read()


def _sin_comentarios(h):
    h = re.sub(r'/\*.*?\*/', ' ', h, flags=re.S)
    return re.sub(r'<!--.*?-->', ' ', h, flags=re.S)


# ── 1 · ninguna pestaña deja la pantalla en blanco ───────────────────────────

def test_CADA_pestaña_tiene_su_panel(app, db_clean):
    """El conmutador apaga todos los paneles antes de encender el destino: si el destino no
    existe, no da error — deja la pantalla VACÍA (M112/M155). Es el chequeo más barato que
    existe y el que más veces hizo falta."""
    h = _html()
    for p in PANES:
        assert 'id="pane-%s"' % p in h, 'la pestaña "%s" no tiene su panel' % p
    # y al revés: ningún botón apunta a un pane que el conmutador no conoce
    for destino in set(re.findall(r"showPane\('([a-z]+)'\)", h)):
        assert destino in PANES, 'un botón lleva a "%s", que el conmutador no conoce' % destino


def test_el_CONMUTADOR_conoce_todos_los_panes(app, db_clean):
    """La lista vive dentro de `showPane` · agregar un panel y olvidar la lista es exactamente
    como se deja una pestaña muerta."""
    h = _html()
    i = h.find('function showPane(p){')
    assert i > 0
    linea = h[i:h.find('\n', h.find('var panes=', i))]
    for p in PANES:
        assert "'%s'" % p in linea, 'el conmutador no conoce el pane "%s"' % p


def test_toda_funcion_que_los_botones_LLAMAN_existe(app, db_clean):
    """Un botón que llama a una función inexistente no da error visible: no hace nada (M146)."""
    h = _html()
    js = '\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', h, re.S))
    definidas = set(re.findall(r'function\s+([A-Za-z_$][\w$]*)', js))
    definidas |= set(re.findall(r'(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=', js))
    for nom in re.findall(r'on(?:click|change|input|submit)="([A-Za-z_$][\w$]*)\(', h):
        assert nom in definidas, 'el HTML llama a %s() y no está definida' % nom
    # Y los onclick que el JS ARMA como string · el 4-ago llamé a `hoyCol()` desde uno de estos
    # y esa función nunca existió: el botón no hacía nada, sin un solo error a la vista (M146).
    for nom in set(re.findall(r"onclick=\'([A-Za-z_$][\w$]*)\(", js)) |                set(re.findall(r'onclick="\s*\+?\s*([A-Za-z_$][\w$]*)\(', js)) |                set(re.findall(r"onclick=\\\"([A-Za-z_$][\w$]*)\(", js)):
        assert nom in definidas, 'un botón que arma el JS llama a %s() y no está definida' % nom


def test_el_JS_de_la_pantalla_es_VALIDO(app, db_clean):
    """node --check del valor EVALUADO · el AST de Python pasa igual con el `<script>` roto, y
    al inyectar CSS junto al JS ya cerré un `<style>` que no estaba abierto."""
    import ast
    import subprocess
    import tempfile
    import pytest
    try:
        subprocess.run(['node', '--version'], capture_output=True, check=True)
    except Exception:
        pytest.skip('sin node en este entorno')
    src = _src('api/templates_py/centro_operaciones_html.py')
    big = max((n.value.value for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
               and isinstance(n.value.value, str)), key=len)
    tmp = tempfile.mkdtemp()
    for i, blk in enumerate(re.findall(r'<script[^>]*>(.*?)</script>', big, re.S)):
        if not blk.strip():
            continue
        f = os.path.join(tmp, 'c%d.js' % i)
        io.open(f, 'w', encoding='utf-8').write(blk)
        r = subprocess.run(['node', '--check', f], capture_output=True, text=True)
        assert r.returncode == 0, 'JS roto en el bloque %d: %s' % (i, r.stderr[:400])
    # las etiquetas cierran · un <style> de más se come el JS que le sigue
    assert big.count('<style') == big.count('</style>'), 'los <style> no cierran'
    assert big.count('<script') == big.count('</script>'), 'los <script> no cierran'
    assert big.count('<div') == big.count('</div>'), 'los <div> quedaron desbalanceados'


# ── 2 · las URLs viejas siguen llegando ──────────────────────────────────────

def test_GERENCIA_redirige_a_la_pantalla_unica(app, admin_client, db_clean):
    """La ruta se retira, no se borra: un marcador viejo tiene que seguir llegando (M120)."""
    r = admin_client.get('/gerencia')
    assert r.status_code in (301, 302), 'se esperaba una redirección, llegó %s' % r.status_code
    assert '/hoy' in (r.headers.get('Location') or ''), r.headers.get('Location')


def test_MI_BANDEJA_redirige_a_su_pestaña(app, admin_client, db_clean):
    r = admin_client.get('/mi-bandeja')
    assert r.status_code in (301, 302), 'se esperaba una redirección, llegó %s' % r.status_code
    loc = r.headers.get('Location') or ''
    assert '/hoy' in loc and 'pend' in loc, loc


def test_los_ENDPOINTS_de_gerencia_siguen_VIVOS(app, admin_client, db_clean):
    """Se retiró la PANTALLA, no el cálculo: esos endpoints alimentan la pestaña Estratégico.
    Retirar los dos a la vez es como se queda una pestaña sin datos."""
    for url in ('/api/gerencia/kpis', '/api/gerencia/dashboard-extra',
                '/api/gerencia/decisiones-ceo'):
        r = admin_client.get(url)
        assert r.status_code == 200, '%s devolvió %s' % (url, r.status_code)


def test_la_pantalla_unica_CARGA(app, admin_client, db_clean):
    r = admin_client.get('/hoy')
    assert r.status_code == 200, r.data[:200]
    for marca in ('id="pane-pend"', 'id="pane-estr"', 'id="ceo-decisiones"'):
        assert marca.encode() in r.data, 'la pantalla no trae %s' % marca


# ── 3 · no se perdió nada en la mudanza ──────────────────────────────────────

def test_los_PAGOS_conservan_sus_acciones(app, db_clean):
    """Es la pestaña con las únicas dos acciones reales del tablero. Si la consolidación se las
    lleva, el CEO deja de poder pagar desde acá — que es para lo que existe."""
    h = _html()
    assert 'id="pane-pagos"' in h and 'cargarPagos' in h
    assert 'pg-lista' in h, 'se perdió la lista de pagos'


def test_la_BANDEJA_llegó_completa(app, db_clean):
    """Era una pantalla huérfana de 230 líneas: si la mudanza se come el filtro por severidad,
    queda una lista larga que no se puede atacar."""
    h = _html()
    assert 'cargarPendientes' in h and '/api/bandeja-ceo' in h
    for sev in ('critical', 'high', 'medium'):
        assert "'%s'" % sev in h, 'la bandeja perdió la severidad %s' % sev
    # ⚠ `'pendFiltro' in h` NO alcanza: el nombre aparece también dentro del `onclick` que el JS
    # construye, así que renombrar la DEFINICIÓN pasaba el test — y eso es justo el bug del botón
    # muerto (M146). Se exige la definición.
    assert re.search(r'function\s+pendFiltro\s*\(', h), 'se perdió el filtro por severidad'


def test_lo_ESTRATEGICO_llegó_con_sus_inputs(app, db_clean):
    """Los inputs del mes son lo único que sólo el CEO sabe · si se pierden, ese dato deja de
    entrar al sistema."""
    h = _html()
    assert 'cargarEstrategico' in h and '/api/gerencia/dashboard-extra' in h
    for campo in ('estr-caja', 'estr-animus', 'estr-maquila', 'estr-notas'):
        assert 'id="%s"' % campo in h, 'falta el input %s' % campo
    assert 'estrGuardar' in h, 'los inputs no se pueden guardar'
    # y la nómina NO se teclea: se deriva de RRHH (M99)
    assert 'id="estr-nomina"' in h and 'no se edita acá' in h


def test_las_TARJETAS_de_decision_estan_en_la_primera_pestaña(app, db_clean):
    """Un tablero de CEO se abre para decidir · lo primero tiene que ser lo que espera su firma."""
    h = _html()
    i_ceo = h.find('id="ceo-decisiones"')
    i_dec = h.find('id="pane-dec"')
    assert i_dec > 0 and i_ceo > i_dec, 'las tarjetas no están en la pestaña de Decisiones'
    assert i_ceo < h.find('id="decisiones"'), 'quedaron debajo de la cola de decisiones'
    assert 'cargarDecisionesCEO' in h


def test_el_estilo_nuevo_usa_TOKENS(app, db_clean):
    """Regla 0 · y un hex fijo con el texto en token da contraste 1.0 al invertir el tema (M114)."""
    h = _sin_comentarios(_html())
    i = h.find('.ceo-dec-grid{')
    assert i > 0, 'no encontré el CSS nuevo'
    css = h[i:h.find('</style>', i)]
    hexes = [x for x in re.findall(r'(?<!\w)#[0-9a-fA-F]{3,8}\b', css) if x.lower() != '#fff']
    assert not hexes, 'el CSS nuevo trae hex sueltos: %s' % hexes
