"""El modal "Solicitar lote a Compras" tiene que leer SUS campos (14-ago-2026).

Encontrado barriendo Producción: dos modales distintos de la misma página
compartían `id="sol-obs"` e `id="sol-msg"`. `getElementById` devuelve el PRIMERO
del documento -el del modal "Solicitar Compra", que está oculto-, así que:

- la justificación que el operario escribía acá NO se leía nunca -> la validación
  "mínimo 5 caracteres" cortaba SIEMPRE, y
- el mensaje que lo explica se pintaba dentro del modal oculto -> **no se veía
  nada**: el botón "Enviar a Compras" no funcionaba y no daba ninguna señal.

Entrando desde Alertas era peor: el pre-llenado escribía en el input del otro
modal, así que se mandaba una justificación autogenerada y se DESCARTABA lo que
la persona había escrito.

Es M199: un id repetido no da error, deja un botón que no hace nada. El guard
mira el HTML REAL servido, que es donde se ve.
"""
import re

from .conftest import TEST_PASSWORD, csrf_headers


def _pantalla(app):
    c = app.test_client()
    r = c.post('/login', data={'username': 'sebastian', 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    r = c.get('/inventarios')
    assert r.status_code == 200, r.status_code
    return r.data.decode('utf-8')


def _pantalla_con_js(app):
    """La página MÁS los bundles externos que carga: el JS del dashboard vive en
    /planta-core.js y /planta-app.js, así que un escáner que sólo mire el HTML
    concluye que no existe ninguna función (M166)."""
    html = _pantalla(app)
    c = app.test_client()   # sin sesión: los dos bundles son públicos por diseño
    todo = html
    for src in re.findall(r'<script[^>]+src="(/[^"?]+)', html):
        rj = c.get(src)
        if rj.status_code == 200:
            todo += '\n' + rj.data.decode('utf-8', 'replace')
    return todo


def _sin_comentarios(html):
    # Un id NOMBRADO dentro de un comentario no es un elemento: contarlo hace que
    # el guard se encuentre a sí mismo (M154).
    return re.sub(r'<!--.*?-->', '', html, flags=re.S)


def test_ningun_id_repetido_en_la_pantalla_de_planta(app):
    html = _sin_comentarios(_pantalla(app))
    ids = re.findall(r'\sid="([^"]+)"', html)
    # los ids que el JS arma en tiempo de ejecución llevan una expresión adentro
    reales = [x for x in ids if "'" not in x and '+' not in x]
    dup = sorted({x for x in reales if reales.count(x) > 1})
    assert not dup, 'ids repetidos (getElementById devuelve el primero): %s' % dup


def test_el_modal_de_solicitar_lote_usa_sus_propios_campos(app):
    html = _pantalla_con_js(app)
    # El modal declara sus campos...
    i = html.find('id="modal-solicitar-lote"')
    assert i > 0, 'no está el modal de solicitar lote'
    bloque = html[i:i + 6000]
    assert 'id="sollote-obs"' in bloque, 'la justificación no tiene id propio'
    assert 'id="sollote-msg"' in bloque, 'la caja de mensajes no tiene id propio'
    # ...y la función que lo envía lee ESOS, no los del otro modal.
    j = html.find('async function enviarSolicitarLote')
    assert j > 0, 'no está la función que envía la solicitud'
    cuerpo = html[j:j + 2500]
    assert "getElementById('sollote-obs')" in cuerpo, (
        'lee la justificación del OTRO modal: siempre vacía -> botón muerto')
    assert "getElementById('sollote-msg')" in cuerpo, (
        'escribe los mensajes en el otro modal: el usuario no ve el error')
    assert "getElementById('sol-obs')" not in cuerpo
    assert "getElementById('sol-msg')" not in cuerpo
    # Y la que ABRE el modal también: si limpia los campos del otro, deja la
    # justificación vieja a la vista y borra la del modal ajeno.
    k = html.find('function abrirSolicitarLote')
    assert k > 0, 'no está la función que abre el modal'
    apertura = html[k:k + 2000]
    assert "getElementById('sollote-obs')" in apertura
    assert "getElementById('sollote-msg')" in apertura
    assert "getElementById('sol-obs')" not in apertura
    assert "getElementById('sol-msg')" not in apertura


def test_desde_alertas_tambien_apunta_al_modal_correcto(app):
    """Este camino pre-llenaba el campo del otro modal, así que mandaba una
    justificación que el usuario no escribió."""
    html = _pantalla_con_js(app)
    j = html.find('function solicitarMPAlerta')
    assert j > 0
    cuerpo = html[j:j + 1500]
    assert "getElementById('sollote-obs')" in cuerpo
    assert "getElementById('sol-obs')" not in cuerpo
