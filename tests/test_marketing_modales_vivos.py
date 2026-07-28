"""Un botón vivo no puede abrir un modal que ya no existe (27-jul).

Lo que pasó: al reducir Marketing a pagos borré los 8 modales de la página y dejé vivos los
botones que los abren. "+ Nuevo Influencer", "Solicitar pago", "Dar de baja" y "Gestionar
pagos" quedaron haciendo `document.getElementById('modal-...')` sobre null: el click revienta
en la consola y desde afuera se ve como que **el botón no hace nada**. Solicitar pago es justo
el único flujo que este módulo tiene que tener.

Ningún test lo cazó porque los tests de pago ejercitan el ENDPOINT, y el endpoint estaba bien.
El hueco estaba entre el botón y el formulario.

Este test recorre los botones REALES de la página, sigue a la función que llaman, y exige que
todo modal que esa función abra exista de verdad -- salvo que la función lo construya al vuelo.
"""
import re

import pytest

from .conftest import TEST_PASSWORD, csrf_headers


@pytest.fixture
def pagina(app):
    """Depende de `app` A PROPÓSITO: importar el template arrastra `config`, y si eso pasa
    ANTES de que la fixture `app` siembre las PASS_<USER>, config queda cacheado sin claves
    y el login de los tests que vengan después empieza a fallar (M102: un test tiene que
    controlar su universo, y sobre todo no ensuciar el de los demás)."""
    from templates_py.marketing_html import MARKETING_HTML
    return MARKETING_HTML


def _partes(html):
    bloques = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S)
    solo_html = re.sub(r'<script(?![^>]*\bsrc=)[^>]*>.*?</script>', '', html, flags=re.S)
    return "\n".join(bloques), solo_html


def _cuerpo(js, nombre):
    """Cuerpo de una función JS, con las llaves balanceadas (ignorando strings)."""
    m = re.search(r'(?:async\s+)?function\s+' + re.escape(nombre) + r'\s*\(', js)
    if not m:
        return ''
    i = js.find('{', m.end() - 1)
    prof, j, en_str, q = 0, i, False, ''
    while j < len(js):
        ch = js[j]
        if en_str:
            if ch == '\\':
                j += 2
                continue
            if ch == q:
                en_str = False
        elif ch in '"\'`':
            en_str, q = True, ch
        elif ch == '{':
            prof += 1
        elif ch == '}':
            prof -= 1
            if prof == 0:
                break
        j += 1
    return js[i:j + 1]


def test_todo_modal_que_abre_un_boton_vivo_existe_en_la_pagina(pagina):
    js, solo_html = _partes(pagina)
    ids_html = set(re.findall(r'\bid="([^"]+)"', solo_html))

    # Botones reales: los del HTML estático y los que el JS pinta en las filas/tarjetas.
    invocadas = set()
    for m in re.finditer(r'\bon[a-z]+\s*=\s*"([^"]*)"', solo_html):
        invocadas |= set(re.findall(r'([A-Za-z_$][\w$]*)\s*\(', m.group(1)))
    for m in re.finditer(r'on[a-z]+=\\?["\']?\s*([A-Za-z_$][\w$]*)\s*\(', js):
        invocadas.add(m.group(1))

    # Algunos modales los arma el propio JS cuando hacen falta (`createElement` + `.id=`).
    # Esos valen igual: al momento de usarse existen. Se recogen de TODO el script, porque
    # el que lo crea y el que lo cierra suelen ser funciones distintas.
    dinamicos = set(re.findall(r"\.id\s*=\s*'(modal-[\w-]+)'", js))
    dinamicos |= set(re.findall(r"(?:const|let|var)\s+\w+\s*=\s*'(modal-[\w-]+)'", js))
    dinamicos |= set(re.findall(r"""id=\\?["'](modal-[\w-]+)""", js))

    rotos = []
    for fn in sorted(invocadas):
        cuerpo = _cuerpo(js, fn)
        if not cuerpo:
            continue
        abre = set(re.findall(r"getElementById\(\s*'(modal-[\w-]+)'\s*\)", cuerpo))
        abre |= set(re.findall(r"closeModal\(\s*'(modal-[\w-]+)'\s*\)", cuerpo))
        for mid in abre:
            if mid not in ids_html and mid not in dinamicos:
                rotos.append(f'{fn}() abre #{mid} y ese modal no está en la página')

    assert not rotos, (
        'hay botones que abren modales inexistentes (el click revienta y parece que el botón '
        'no hace nada):\n  - ' + '\n  - '.join(rotos))


def test_nadie_cambia_a_una_pestana_que_no_existe(pagina):
    """Sebastián: *"le tengo que dar click en la pestaña para que aparezca"*.

    La causa era un bloque heredado que 100 ms después de cargar llamaba a
    `switchTab('dashboard')`. Al quitar la pestaña Dashboard ese tab dejó de existir, así que
    switchTab le sacaba `active` a TODOS los paneles, no encontraba a cuál ponérselo, y la
    pantalla quedaba en blanco hasta que uno hacía click. Mismo patrón que los modales
    borrados: un disparador vivo apuntando a algo que ya no está.
    """
    js, solo_html = _partes(pagina)
    paneles = set(re.findall(r'id="tab-([\w-]+)"', solo_html))
    destinos = set(re.findall(r"switchTab\(\s*'([\w-]+)'\s*\)", js))
    faltan = sorted(d for d in destinos if d not in paneles)
    assert not faltan, (
        'switchTab apunta a pestañas que no existen %s · eso deja la pantalla en blanco '
        '(quita `active` de todos los paneles y no se lo pone a ninguno). Paneles reales: %s'
        % (faltan, sorted(paneles)))


def test_los_modales_que_el_JS_CREA_usan_el_contrato_de_la_pagina(pagina):
    """Sebastián, al ir a fusionar los duplicados: *"no se abre nada"*.

    El botón funcionaba: creaba la ventana y hacía el fetch. Pero la creaba con las clases de
    OTRO sistema de modales (`.modal` como capa + `.modal-content` adentro), y el de esta
    página es `.modal-bg` (la capa, que es la que tiene `display:none` y se muestra con
    `.open`) conteniendo un `.modal`. Como `.modal` no está oculto, la ventana se dibujaba
    pegada al final del body en vez de encima -- invisible en la práctica.

    Mismo patrón que el botón sin modal y el switchTab sin panel: código escrito contra un
    contrato que la página ya no usa.
    """
    js, _ = _partes(pagina)
    # Toda capa de modal creada al vuelo tiene que ser `.modal-bg`.
    malos = re.findall(r"\.className\s*=\s*'modal'\s*;", js)
    assert not malos, (
        'un modal dinámico se crea con class "modal" (la CAJA) en vez de "modal-bg" (la CAPA): '
        'no tiene display:none, así que aparece al final del body en vez de encima')
    # Y `.modal-content` no existe en el CSS de esta página: si alguien lo usa, no estiliza nada.
    if '.modal-content{' not in pagina:
        assert 'class="modal-content"' not in pagina, (
            'se usa .modal-content pero esa clase no existe en el CSS de la página')


def test_no_manda_al_usuario_a_una_pantalla_que_ya_no_existe(pagina):
    """La sub-vista de Influencers salió de Compras el 27-jul, pero tres textos seguían
    diciendo "va a /compras → tab Influencers para autorizar y pagar".

    Una instrucción que manda a un lugar que ya no está es peor que no tener instrucción:
    Jefferson iba, no encontraba nada, y quedaba sin saber dónde se decide su pago. Es el
    mismo patrón que el botón sin modal y el switchTab sin panel, pero en el texto.
    """
    import re as _re
    # Se mira sólo lo que el usuario LEE: los comentarios del código pueden mencionarlo
    # justamente para explicar por qué ya no va.
    visible = _re.sub(r'<!--.*?-->', '', pagina, flags=_re.S)
    visible = _re.sub(r'^\s*//.*$', '', visible, flags=_re.M)
    for muerto in ('/compras → tab Influencers', 'compras -> tab Influencers'):
        assert muerto not in visible, (
            'un texto sigue mandando a "%s", que se retiró · el pago se decide en '
            'Centro de Mando → Pagos' % muerto)


def test_la_pantalla_se_abre_sola_sin_tener_que_hacer_click(pagina):
    """Con una sola pestaña, entrar al módulo tiene que mostrarla ya cargada."""
    js, _ = _partes(pagina)
    assert 'DOMContentLoaded' in js and "switchTab('influencers')" in js, (
        'no hay arranque: el panel queda oculto y loadTab nunca corre, así que además de '
        'verse vacío tampoco carga los datos')


@pytest.mark.parametrize('modal', [
    'modal-influencer',        # + Nuevo Influencer / editar
    'modal-inf-pago',          # Solicitar pago  <- el flujo que el módulo existe para tener
    'modal-dar-baja',          # Dar de baja
    'modal-gestionar-pagos',   # Gestionar pagos de un creador
    'modal-historial',         # Historial
])
def test_los_modales_del_flujo_de_pagos_estan_presentes(pagina, modal):
    assert f'id="{modal}"' in pagina, (
        f'falta {modal}: se borró al recortar la pantalla y su botón quedó vivo')


def test_los_campos_que_el_formulario_de_pago_escribe_existen(pagina):
    """No alcanza con que el modal esté: si le falta un campo, `solicitarPagoInf` revienta
    a mitad de camino y el pago no se pide."""
    for campo in ('pago-inf-id', 'pago-inf-nombre', 'pago-valor', 'pago-concepto',
                  'pago-fecha-contenido', 'pago-entregable', 'pago-link-post',
                  'pago-inf-alert', 'pago-banco-preview'):
        assert f'id="{campo}"' in pagina, f'al modal de solicitar pago le falta #{campo}'


def test_la_pantalla_carga_y_trae_los_modales(app):
    """Contra la ruta real, no sólo contra la constante."""
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    html = c.get('/marketing').data.decode('utf-8', 'replace')
    assert 'id="modal-inf-pago"' in html and 'id="modal-influencer"' in html
