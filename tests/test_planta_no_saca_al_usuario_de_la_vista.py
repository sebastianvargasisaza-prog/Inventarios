# -*- coding: utf-8 -*-
"""Tres cosas que sacaban al usuario de la vista o lo dejaban atrapado · 19-ago-2026.

Sebastian, mirando Planta:

  1. *"cuando le doy legajo en envasado me abre otra pagina, organizalo que sea en el
     mismo vista"* -- la tabla de ordenes de envasado usaba un `<a href>` que NAVEGABA
     fuera del dashboard: se perdia la pestana, los filtros y el scroll. La lista premium
     de ESA MISMA pestana ya lo abria inline con `abrirEBR` sobre #envasado-runner; la
     tabla se habia quedado con el enlace viejo (M150: dos hermanos y uno se quedo atras).

  2. *"hay pop up que se abren y no tienen opcion de x para salirse y toca darle
     actualizar"* -- de los 26 modales de Planta, 25 tienen su cierre. El unico sin
     salida era el de operador, y era peor de lo que parece: `cambiarOperador()` hacia
     `localStorage.removeItem` ANTES de abrir el dialogo, asi que quien apretaba
     "[cambiar]" por accidente YA habia perdido el operador y no podia volver.

  3. *"el plano sigue el antiguo no el arreglo nuevo"* -- el boton "Plano de planta"
     hacia `window.open('/planta/plano')`, la pantalla vieja, teniendo el dashboard su
     propia pestana de plano en vivo. Medido: la vieja no tiene pantalla completa, ni
     modal de sala, ni equipos, ni el rotulo F02 desde el plano.

Las tres se miden sobre lo SERVIDO (HTML + bundles), no sobre el fuente: el JS se arma
dentro de constantes de Python y un regex sobre el fuente termina midiendo otra cosa.
"""
import re

from .conftest import TEST_PASSWORD, csrf_headers


def _cli(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, user
    return c


def _servido(cli, ruta='/inventarios'):
    r = cli.get(ruta, follow_redirects=True)
    assert r.status_code == 200, (ruta, r.status_code)
    html = r.get_data(as_text=True)
    total = html
    for src in set(re.findall(r'<script[^>]+src="([^"]+\.js[^"]*)"', html)):
        if not src.startswith('http'):
            rb = cli.get(src)
            if rb.status_code == 200:
                total += rb.get_data(as_text=True)
    return html, total


def test_el_legajo_de_envasado_se_abre_EN_LA_MISMA_VISTA(app, db_clean):
    html, total = _servido(_cli(app))
    assert 'ordenes-env-tbody' in html, (
        "desaparecio la tabla de ordenes de envasado · el guard dejo de medir (M210)")
    # la fila del legajo NO puede ser un enlace que navega
    m = re.search(r"var leg=o\.(\w+)\?\('<(\w+)", total)
    assert m, "no encontre como se arma el boton del legajo en la tabla de envasado"
    assert m.group(2) != 'a', (
        "el legajo de envasado se abre con un <a href> que saca al usuario del "
        "dashboard · tiene que abrirse inline como en la lista premium", m.group(0))
    assert "abrirEBR('+o.ebr_id+',&#39;envasado-runner&#39;)" in total, (
        "la tabla de envasado no abre el legajo en el runner de su propia pestana")
    assert 'id="envasado-runner"' in html, (
        "falta el contenedor donde se pinta el legajo inline · el boton no tendria "
        "donde abrirlo (M239: el destino existe pero es el de otra fase)")


def test_el_dialogo_de_operador_tiene_salida(app, db_clean):
    html, total = _servido(_cli(app))
    assert 'id="oper-cancelar"' in html, (
        "el dialogo de operador no ofrece salida · quien entra a cambiar de operador "
        "queda atrapado y tiene que recargar la pagina")
    assert 'function cancelarCambioOperador' in total, (
        "falta la funcion que cierra el dialogo de operador")


def test_cambiar_operador_NO_borra_al_actual_antes_de_confirmar(app, db_clean):
    """El estado se destruye al CONFIRMAR, no al abrir el dialogo (M112).

    Con el removeItem adelantado, apretar "[cambiar]" por error ya costaba el operador
    -- y sin salida en el modal, la unica forma de recuperarlo era recargar.
    """
    _, total = _servido(_cli(app))
    m = re.search(r"function cambiarOperador\(\)\{(.*?)\n\}", total, re.S)
    assert m, "no encontre cambiarOperador en lo servido"
    cuerpo = "\n".join(l for l in m.group(1).splitlines()
                       if not l.strip().startswith('//'))
    assert 'removeItem' not in cuerpo, (
        "cambiarOperador borra el operador ANTES de que la persona confirme · si se "
        "arrepiente, ya lo perdio")


def test_el_boton_del_plano_lleva_a_la_pestana_NUEVA(app, db_clean):
    html, total = _servido(_cli(app))
    assert 'id="plano"' in html and 'plano-mapa' in html, (
        "no esta la pestana de plano en vivo del dashboard")
    # el boton de la barra de rotulos ya no puede abrir la pantalla vieja
    m = re.search(r'<button onclick="([^"]+)"[^>]*>\s*&#127981;\s*Plano de planta', html)
    assert m, "no encontre el boton 'Plano de planta'"
    assert 'window.open' not in m.group(1), (
        "el boton del plano sigue abriendo la pantalla vieja en otra pestana · el plano "
        "que se rehizo es la pestana del dashboard", m.group(1))
    assert 'id="btn-tab-plano"' in html, (
        "falta el id de la pestana de plano · irAlPlano no tendria a que hacerle click")


def test_los_modales_de_planta_se_pueden_cerrar(app, db_clean):
    """Ningun overlay puede quedar sin forma de salir (M112 en su forma de UI).

    Se mide sobre lo SERVIDO y contando: un modal cuyo contenido se inyecta por JS
    lleva su cierre en el JS, no en el HTML estatico -- por eso se busca en los dos.
    """
    html, total = _servido(_cli(app))
    CIERRES = ('closeModal', 'cerrarModal', '&#10005;', '&#215;', '&times;', '×',
               '✕', 'Cancelar', 'Cerrar', 'cerrar(')
    overlays = []
    for m in re.finditer(r'<div\b([^>]*)>', html):
        at = m.group(1)
        mid = re.search(r'id="([^"]+)"', at)
        if not mid or 'position:fixed' not in at:
            continue
        ident = mid.group(1)
        cls = re.search(r'class="([^"]*)"', at)
        if not (ident.startswith('modal') or 'modal' in (cls.group(1) if cls else '')):
            continue
        overlays.append((ident, m.start()))
    assert len(overlays) >= 10, (
        "se midieron muy pocos modales (%d) · el guard dejo de encontrarlos y pasaria "
        "verde por omision (M210)" % len(overlays))
    sin_salida = []
    for k, (ident, pos) in enumerate(overlays):
        fin = overlays[k + 1][1] if k + 1 < len(overlays) else min(pos + 9000, len(html))
        blk = html[pos:fin]
        if any(x in blk for x in CIERRES):
            continue
        # el contenido puede inyectarse: su cierre vive en el JS servido
        if re.search(r"getElementById\(['\"]" + re.escape(ident) +
                     r"['\"]\)\.style\.display\s*=\s*['\"]none", total):
            continue
        sin_salida.append(ident)
    assert not sin_salida, (
        "hay modales sin forma de cerrarse · el usuario queda atrapado y tiene que "
        "recargar la pagina: %s" % sin_salida)
