# -*- coding: utf-8 -*-
"""La contadora VE la caja menor en Tesorería: cuánto hay y con qué entró cada peso.

Sebastián (6-ago): *"la caja menor le debe aparecer todo, cuánto hay, con qué ingresó todo, para
ella revisar"*. El endpoint `/api/caja/libro` ya existía y estaba probado
([[test_caja_libro_contadora]]) -- pero **la pantalla no lo pintaba en ninguna parte**, así que
desde la silla de Mayra el dato seguía sin existir (M121: una capacidad que nadie puede alcanzar
no existe · M115: un dato que se captura y no llega al consumidor tampoco).

Lo que se verifica acá es la costura completa, que es donde vive este tipo de hueco: botón →
panel → lista de pestañas → despacho → función que hace el fetch. Si falta UNA de las cinco
puntas la pestaña queda muerta y no hay error en ningún lado (M112: el conmutador apaga todos
los paneles antes de encender el destino, así que un destino ausente deja la pantalla EN BLANCO).
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))
sys.path.insert(0, os.path.join(RAIZ, 'scripts'))


def _html():
    from templates_py.tesoreria_html import HTML
    return HTML


def test_las_CINCO_puntas_de_la_pestana_estan_conectadas(app):
    """Botón, panel, TABS, despacho y la función. Falta una y la pantalla queda en blanco."""
    h = _html()
    assert "switchTab('cajamenor')" in h, 'no hay botón que lleve a la pestaña'
    assert 'id="tab-cajamenor"' in h, 'no existe el panel destino'
    m = re.search(r'const TABS = \[([^\]]+)\]', h)
    assert m and "'cajamenor'" in m.group(1), (
        'la pestaña no está en TABS · el conmutador no la apagaría ni encendería')
    assert re.search(r"else if \(t === 'cajamenor'\) cargarCajaMenor\(\)", h), (
        'nadie carga los datos al abrir la pestaña')
    assert 'async function cargarCajaMenor(' in h, 'la función no está definida'


def test_PINTA_lo_que_el_endpoint_manda_y_no_otra_cosa(app):
    """Los contratos rotos de esta misma pantalla (leer `ingresos_mes` cuando el endpoint manda
    `ing_mes`) son la razón por la que el P&L decía "Error cargando" siempre. Acá se fija que
    cada llave que la vista lee EXISTE en la respuesta de `/api/caja/libro`."""
    import io as _io
    h = _html()
    i = h.find('async function cargarCajaMenor(')
    j = h.find('function cmExportar(')
    assert 0 < i < j, 'no encuentro el bloque de caja menor'
    bloque = h[i:j]

    src = _io.open(os.path.join(RAIZ, 'api', 'blueprints', 'animus.py'), encoding='utf-8').read()
    k = src.find('def caja_libro')
    fin = src.find('\n@bp.route', k)
    endpoint = src[k:fin]

    for llave in ('saldo_actual', 'ingresos_a_gaveta', 'ingresos_al_banco', 'egresos',
                  'egresos_sin_respaldo', 'por_origen', 'movimientos', 'cerrada_hasta'):
        assert llave in bloque, 'la vista no usa %s' % llave
        assert ("'%s'" % llave) in endpoint, (
            'la vista lee `%s` y el endpoint NO la manda · es el contrato roto de siempre' % llave)


def test_DICE_lo_que_no_cuenta_al_saldo(app):
    """Un ingreso por Nequi entró al banco, no a la gaveta, y el saldo lo excluye a propósito.
    Si la fila no lo dijera, ella tendría que descubrirlo restando -- y ahí es donde el arqueo
    deja de cuadrar sin que nadie entienda por qué (M124/M148)."""
    h = _html()
    i, j = h.find('function cmPintarTabla('), h.find('function cmExportar(')
    bloque = h[i:j]
    assert 'cuenta_en_saldo' in bloque, 'la fila no distingue gaveta de banco'
    assert 'gaveta' in bloque and 'al banco' in bloque, 'no se nombran los dos destinos'
    assert 'anulado' in bloque, 'un movimiento anulado tiene que verse, tachado'
    # y el egreso sin soporte, que es lo primero que una contadora busca
    assert 'falta' in bloque, 'no marca el egreso sin comprobante'


def test_el_rango_por_defecto_NO_sale_del_reloj_UTC(app):
    """`toISOString()` es UTC: después de las 19:00 en Colombia ya devuelve el día siguiente y
    el rango arrancaría corrido (M106). Se arma con los componentes locales."""
    from check_js_animus import _sin_ruido
    h = _html()
    i, j = h.find('function cmFechaLocal('), h.find('async function cargarCajaMenor(')
    assert 0 < i < j
    # ⚠ Sin quitar los comentarios, este test encuentra MI PROPIO comentario explicando por qué
    # no se usa `toISOString` y falla con el código correcto (M154 · me pasó a la primera).
    bloque = _sin_ruido(h[i:j])
    assert 'toISOString' not in bloque, 'volvió a armar la fecha en UTC'
    assert 'getFullYear' in bloque and 'getMonth' in bloque, 'no usa los componentes locales'


def test_el_JS_de_la_pantalla_PARSEA(app):
    """El `ast.parse` del .py no ve un error de sintaxis dentro del `<script>`: se node-checkea
    el valor EVALUADO, y un solo bloque roto deja TODA la pantalla sin cargar (M65)."""
    import subprocess
    import io as _io
    import tempfile
    h = _html()
    bloques = re.findall(r'<script[^>]*>(.*?)</script>', h, re.S)
    assert bloques, 'la pantalla no tiene JS'
    try:
        subprocess.run(['node', '--version'], capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):  # pragma: no cover
        import pytest
        pytest.skip('node no disponible · el chequeo NO corrió (M100)')
    for n, b in enumerate(bloques):
        f = os.path.join(tempfile.gettempdir(), '_tes_%d.js' % n)
        _io.open(f, 'w', encoding='utf-8').write(b)
        r = subprocess.run(['node', '--check', f], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, 'bloque %d roto:\n%s' % (n, r.stderr[:600])


def test_toda_funcion_LLAMADA_esta_DEFINIDA(app):
    """Reusa el escáner del proyecto (`scripts/check_js_animus.py`), que enmascara comentarios y
    literales carácter por carácter. Con regex se desincroniza en el primer literal de expresión
    regular y reporta decenas de funciones sanas como faltantes -- o sea ruido, o sea un guard
    que deja de mirarse (M146). Escribí el mío con regex y dio 17 falsos positivos."""
    from check_js_animus import funciones_sin_definir
    faltan = funciones_sin_definir(_html())
    assert not faltan, 'funciones llamadas y no definidas en /tesoreria: %s' % faltan


def test_ningun_boton_apunta_a_un_id_que_no_existe(app):
    """El par disparador↔destino: si el JS busca un id que el HTML no tiene, el botón no hace
    nada y no hay error visible (M112)."""
    from check_js_animus import _sin_ruido
    h = _html()
    js = _sin_ruido('\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', h, re.S)))
    ids = set(re.findall(r'id="([^"]+)"', h))
    usados = set(re.findall(r"getElementById\(\s*'([^']+)'\s*\)", js))
    # los que el propio JS crea al vuelo no viven en el HTML
    creados = set(re.findall(r"\.id\s*=\s*'([^']+)'", js))
    huerfanos = sorted(u for u in usados if u not in ids and u not in creados)
    assert not huerfanos, 'el JS busca ids que no existen: %s' % huerfanos
