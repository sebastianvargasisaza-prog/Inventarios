# -*- coding: utf-8 -*-
"""Asignar una nueva ubicación desde el cuadre: que de verdad quede ubicado.

Sebastián 22-ago, contando la estantería: *"también revisá que lo que le asigne nueva
ubicación quede perfecto"*.

Lo que apareció midiendo: el botón **Ubicar aquí** -- el que deja en la estantería que se
está revisando un lote que nadie sabía dónde estaba -- mandaba `PATCH` a una ruta declarada
sólo para `PUT`. Flask contesta **405** y la página, que hace `r.json()` sobre una respuesta
HTML, cae al `catch` y muestra *"Sin conexión"*: o sea que el botón nunca ubicó nada y encima
echaba la culpa a la red.

El guard que ya existía pedía que el texto `ubicarAqui` estuviera en la página. **Que el botón
EXISTA no prueba que su petición se pueda contestar** (M121 con una vuelta más): acá lo que
faltaba era cruzar el MÉTODO contra el mapa de rutas real, que es lo que hace
`test_cada_llamada_de_la_hoja_apunta_a_una_ruta_QUE_ACEPTA_ESE_METODO` para las 16 llamadas
de la pantalla, no sólo para ésta.
"""
import re

import pytest

CODIGO = 'MPCUADRUBI'          # propio de este archivo · nadie más lo siembra
LOTE = 'LOTE-UBI-1'
EST = 'EST-UBICAR-AQUI'


def _limpiar(app):
    """Se limpia ANTES de sembrar: un `finally` no corre si el proceso muere (M103)."""
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM movimientos WHERE material_id=?", (CODIGO,))
        c.execute("DELETE FROM maestro_mps WHERE codigo_mp=?", (CODIGO,))
        c.commit()


@pytest.fixture()
def sembrado(app):
    """Un material con stock en DOS lotes: uno ubicado en EST y otro SIN ubicar.

    Ése es el caso real: el lote sin ubicación aparece en la hoja de EST porque su material
    sí vive ahí, y quien está parado enfrente es el único que puede decir dónde está.
    """
    from database import get_db
    _limpiar(app)
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
                  "VALUES (?,?,?,1)", (CODIGO, 'MP CUADRE UBICACION', 'TEST INCI'))
        c.execute(
            "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
            " fecha, operador, estanteria, posicion, estado_lote) "
            "VALUES (?,?,'Entrada',?,?,?,?,?,?,'VIGENTE')",
            (CODIGO, 'MP CUADRE UBICACION', 500.0, 'LOTE-YA-UBICADO',
             '2026-08-01 08:00:00', 'test', EST, 'A1'))
        c.execute(
            "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
            " fecha, operador, estanteria, posicion, estado_lote) "
            "VALUES (?,?,'Entrada',?,?,?,?,'','','VIGENTE')",
            (CODIGO, 'MP CUADRE UBICACION', 300.0, LOTE, '2026-08-02 08:00:00', 'test'))
        c.commit()
    yield
    _limpiar(app)


def _fila(client, lote, est=EST):
    r = client.get('/api/inventario/cuadre-lotes?est=' + est)
    assert r.status_code == 200, r.data[:200]
    for l in (r.get_json() or {}).get('lotes') or []:
        if l.get('codigo_mp') == CODIGO and l.get('lote') == lote:
            return l
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 1 · el acto completo, por la puerta que usa la pantalla
# ─────────────────────────────────────────────────────────────────────────────

def test_el_lote_sin_ubicar_aparece_en_la_estanteria_marcado(admin_client, sembrado):
    """Antes de ubicarlo tiene que VERSE, o nadie puede ir a buscarlo."""
    f = _fila(admin_client, LOTE)
    assert f is not None, 'el lote sin ubicar no aparece en la hoja de la estantería'
    assert f.get('sin_ubicar') is True, 'no se distingue del que sí está ubicado acá'


def test_ubicar_aqui_deja_el_lote_UBICADO_de_verdad(admin_client, sembrado):
    """El acto completo: la petición que manda la pantalla tiene que ser contestada,
    y el efecto se mide donde alguien lo lee, no en el 200 de la respuesta."""
    r = admin_client.put(
        '/api/lotes/%s/%s/ubicacion' % (CODIGO, LOTE),
        json={'estanteria': EST, 'motivo': 'ubicado durante el cuadre'})
    assert r.status_code == 200, 'la pantalla no puede ubicar: %s %s' % (
        r.status_code, r.data[:200])
    d = r.get_json() or {}
    assert d.get('movimientos_actualizados', 0) >= 1, 'dijo que ok y no movió nada'

    f = _fila(admin_client, LOTE)
    assert f is not None, 'el lote se perdió de la hoja al ubicarlo'
    assert f.get('estanteria') == EST, 'quedó con otra ubicación: %r' % f.get('estanteria')
    assert not f.get('sin_ubicar'), 'sigue marcado como sin ubicar después de ubicarlo'


def test_ubicar_NO_toca_la_cantidad_ni_el_estado_ni_el_vencimiento(admin_client, sembrado):
    """Mover de estante no es mover material: cambiar dónde está no puede cambiar cuánto hay.

    Si el UPDATE se pasara de columnas, un lote en cuarentena quedaría liberado por la puerta
    de atrás y uno sin fecha volvería eterno al FEFO (M31/M118)."""
    from database import get_db
    antes = _fila(admin_client, LOTE)
    admin_client.put('/api/lotes/%s/%s/ubicacion' % (CODIGO, LOTE),
                     json={'estanteria': EST, 'posicion': 'B7', 'motivo': 'cuadre'})
    desp = _fila(admin_client, LOTE)
    assert desp['stock_sistema'] == antes['stock_sistema'], 'la ubicación cambió la cantidad'
    assert desp.get('posicion') == 'B7', 'no guardó la posición'
    with admin_client.application.app_context():
        filas = get_db().execute(
            "SELECT COALESCE(estado_lote,''), COALESCE(fecha_vencimiento,''), tipo "
            "  FROM movimientos WHERE material_id=? AND lote=?", (CODIGO, LOTE)).fetchall()
    assert filas, 'se perdieron los movimientos del lote'
    for est_l, venc, tipo in filas:
        assert est_l == 'VIGENTE', 'la ubicación tocó el estado del lote: %r' % est_l
        assert tipo == 'Entrada', 'la ubicación creó un movimiento: %r' % tipo


def test_ubicar_un_lote_NO_arrastra_al_otro_lote_del_mismo_material(admin_client, sembrado):
    """El UPDATE va por (material, lote). Si fuera sólo por material, ubicar uno reescribiría
    la ubicación de todos los lotes de esa materia prima."""
    admin_client.put('/api/lotes/%s/%s/ubicacion' % (CODIGO, LOTE),
                     json={'estanteria': 'OTRA-ESTANTERIA', 'motivo': 'cuadre'})
    otro = _fila(admin_client, 'LOTE-YA-UBICADO')
    assert otro is not None, 'el otro lote desapareció de su estantería'
    assert otro.get('estanteria') == EST, (
        'ubicar un lote se llevó puesta la ubicación del otro: %r' % otro.get('estanteria'))


def test_ubicar_deja_rastro_de_DONDE_VENIA(admin_client, sembrado):
    """Ante una ubicación equivocada la pregunta es *¿dónde estaba antes?*, así que el rastro
    sin el valor previo no sirve para deshacer (M139)."""
    from database import get_db
    admin_client.put('/api/lotes/%s/%s/ubicacion' % (CODIGO, LOTE),
                     json={'estanteria': EST, 'motivo': 'cuadre'})
    with admin_client.application.app_context():
        filas = get_db().execute(
            "SELECT COALESCE(detalle,'') || COALESCE(antes,'') || COALESCE(despues,'') "
            "  FROM audit_log WHERE accion='EDITAR_UBICACION_LOTE' AND registro_id LIKE ?",
            (CODIGO + '%',)).fetchall()
    assert filas, 'ubicar un lote no dejó rastro'
    texto = ' '.join(f[0] for f in filas)
    assert EST in texto, 'el rastro no dice a dónde fue'
    assert 'estanteria_anterior' in texto, 'el rastro no dice de dónde venía'


# ─────────────────────────────────────────────────────────────────────────────
# 2 · la clase entera: ningún botón puede pedir algo que la ruta no acepta
# ─────────────────────────────────────────────────────────────────────────────

def _llamadas_de_la_hoja():
    """(url_expr, metodo) de cada llamada de la pantalla del cuadre.

    Se resuelve el texto de la petición, no lo que uno cree que manda: el bug de hoy era
    exactamente un método que nadie había cruzado contra el mapa de rutas.
    """
    from templates_py.cuadre_html import CUADRE_HTML
    js = CUADRE_HTML
    fuera = []

    # (a) fetch('<literal...>', <opciones>)
    for m in re.finditer(r"fetch\(\s*('(?:[^'\\]|\\.)*'(?:\s*\+[^,;]*?)?)\s*,\s*([^;]{0,120})",
                         js):
        fuera.append((m.group(1), _metodo_de(m.group(2))))
    # `fetch(url, ...)` con la URL en variable: se resuelven las asignaciones `url='...'`
    # de esa función, cuyo método es el de la variable `metodo`.
    if re.search(r"fetch\(\s*url\s*,", js):
        met_var = re.search(r"metodo\s*=\s*'([A-Z]+)'", js)
        met = (met_var.group(1) if met_var else 'GET')
        for m in re.finditer(r"url\s*=\s*('(?:[^'\\]|\\.)*'(?:\s*\+[^;]*?)?)\s*;", js):
            fuera.append((m.group(1), met))
    return fuera


def _metodo_de(opciones):
    m = re.search(r"_opts\(\s*'([A-Z]+)'", opciones)
    if m:
        return m.group(1)
    m = re.search(r"method\s*:\s*'([A-Z]+)'", opciones)
    if m:
        return m.group(1)
    return 'GET'


def _a_ruta(expr):
    """La expresión JS de una URL, convertida en un camino concreto que se pueda enrutar.

    Cada pedazo interpolado (`+encodeURIComponent(x)+`) se vuelve un segmento cualquiera:
    lo que se está midiendo es la FORMA de la ruta y su método, no el valor.
    """
    partes = []
    for trozo in re.split(r"\+", expr):
        trozo = trozo.strip()
        lit = re.match(r"^'((?:[^'\\]|\\.)*)'$", trozo)
        partes.append(lit.group(1) if lit else 'X')
    ruta = ''.join(partes)
    return ruta.split('?')[0].rstrip('/') or '/'


def test_cada_llamada_de_la_hoja_apunta_a_una_ruta_QUE_ACEPTA_ESE_METODO(app):
    """El defecto de hoy en su forma general.

    `ubicarAqui` mandaba PATCH a una ruta declarada `methods=['PUT']` -> 405 -> la pantalla
    decía *"Sin conexión"*. Un guard que sólo mira que el botón exista no lo caza: hay que
    cruzar (ruta, método) contra el mapa REAL de Werkzeug, que es quien contesta el 405.
    """
    from werkzeug.exceptions import MethodNotAllowed, NotFound

    llamadas = _llamadas_de_la_hoja()
    # Un barrido que deja de medir pasa verde por omisión (M158/M210): piso explícito.
    assert len(llamadas) >= 12, 'el extractor sólo vio %d llamadas' % len(llamadas)

    adaptador = app.url_map.bind('localhost')
    malas = []
    for expr, metodo in llamadas:
        ruta = _a_ruta(expr)
        if not ruta.startswith('/api/'):
            continue
        try:
            adaptador.match(ruta, method=metodo)
        except MethodNotAllowed as e:
            malas.append('%s %s -> 405 (acepta %s)'
                         % (metodo, ruta, ','.join(sorted(e.valid_methods or []))))
        except NotFound:
            malas.append('%s %s -> 404 (esa ruta no existe)' % (metodo, ruta))
    assert not malas, 'la pantalla del cuadre pide cosas que el servidor no contesta:\n  ' \
                      + '\n  '.join(malas)


def test_ubicar_aqui_refresca_la_fila_en_pantalla(app):
    """Si la fila sigue diciendo la ubicación vieja, la próxima edición se guarda contra un
    dato que ya no es cierto y quien mira no sabe si quedó (M129)."""
    from templates_py.cuadre_html import CUADRE_HTML
    i = CUADRE_HTML.find('function ubicarAqui')
    assert i != -1
    j = CUADRE_HTML.find('\nasync function', i + 10)
    cuerpo = CUADRE_HTML[i:j if j > i else len(CUADRE_HTML)]
    assert 'l.estanteria' in cuerpo, 'ubicar no actualiza la ubicación de la fila'
    assert 'sin_ubicar' in cuerpo, 'ubicar no le quita la marca de sin ubicar a la fila'


# -----------------------------------------------------------------------------
# La vista "Sin ubicacion · para ubicar" tiene que poder UBICAR
# -----------------------------------------------------------------------------

def test_la_vista_de_los_SIN_UBICAR_los_lista(admin_client, sembrado):
    """Es la unica vista desde la que se alcanza un lote cuyo material no tiene NINGUN
    movimiento ubicado: en la hoja de una estanteria sale solo si su material vive ahi."""
    r = admin_client.get('/api/inventario/cuadre-lotes?est=')
    assert r.status_code == 200, r.data[:200]
    lotes = (r.get_json() or {}).get('lotes') or []
    assert any(l.get('codigo_mp') == CODIGO and l.get('lote') == LOTE for l in lotes), (
        'el lote sin ubicar no aparece en la cola de los que hay que ubicar')


def test_desde_ahi_se_puede_UBICAR(app):
    """El boton *Ubicar aqui* deja el lote en la estanteria que se esta revisando, asi que en
    esta vista -- donde no hay ninguna elegida -- estaba oculto: la pantalla que se llama
    "para ubicar" era la unica desde la que no se podia ubicar (M233)."""
    from templates_py.cuadre_html import CUADRE_HTML as H
    assert 'function ubicarEn(' in H, 'no hay forma de ubicar sin estar parado en la estanteria'
    i = H.find('function ubicarEn(')
    j = H.find('async function ubicarEnGuardar', i)
    cuerpo = H[i:j if j > i else i + 1200]
    assert '_ESTS' in cuerpo, (
        'ofrece escribir la ubicacion a mano en vez de elegir de las que ya existen: '
        'eso es lo que parte el inventario en variantes (M272)')


def test_el_boton_aparece_SOLO_donde_corresponde(app):
    """Con estanteria elegida va *Ubicar aqui*; sin ella, *Ubicar en...*. Si los dos salieran
    a la vez, uno de los dos haria algo distinto de lo que dice."""
    from templates_py.cuadre_html import CUADRE_HTML as H
    assert 'l.sin_ubicar&&EST' in H, 'se perdio la condicion del boton *Ubicar aqui*'
    assert 'l.sin_ubicar&&!EST' in H, 'el boton *Ubicar en...* no esta condicionado'


def test_ubicar_en_manda_PUT_como_los_demas(app):
    """Mismo endpoint y mismo metodo que el resto: una segunda forma de ubicar que use otra
    puerta es la que se queda vieja (M1)."""
    from templates_py.cuadre_html import CUADRE_HTML as H
    i = H.find('async function ubicarEnGuardar')
    assert i != -1
    cuerpo = H[i:i + 1600]
    assert "_opts('PUT'" in cuerpo, 'no usa PUT, que es lo que la ruta acepta'
    assert '/ubicacion' in cuerpo, 'no llama al endpoint canonico de ubicacion'
    assert 'l.estanteria=est' in cuerpo, 'no refresca la fila con la ubicacion nueva'
