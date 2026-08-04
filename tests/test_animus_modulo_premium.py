# -*- coding: utf-8 -*-
"""Trinquete del modulo /animus (2-ago).

Lo que se rompio y que estos tests impiden que vuelva:

  1. Texto INVISIBLE por par (fondo, texto) mal armado. Medido: el titulo del
     modulo y los 7 titulos de modal daban contraste 1.00 en tema CLARO
     (`color:#fff` sobre `var(--cx-card)`, que en claro es blanco), y el boton
     Eliminar y el banner de error JS daban 1.00 en LOS DOS temas porque el
     fondo y el texto eran el MISMO token (M104/M114).

  2. Acciones que INSERTAN sin guard anti doble-click: un doble click en
     "Registrar movimiento" creaba DOS recibos de caja y descuadraba el saldo
     (M63). Ahora toda mutacion pasa por `_fetchUna`.

  3. Botones vivos apuntando a nada (M112) y funciones/ids pisados (M120).

El tema CLARO es el default de la pagina (el oscuro solo si esta en
localStorage), asi que un par roto en claro lo ve todo el mundo.
"""
import ast
import io
import os
import re

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(RAIZ, "api", "templates_py", "animus_html.py")
CSS = os.path.join(RAIZ, "api", "static", "cortex.css")


def _html():
    """El HTML RENDERIZADO (valor evaluado del string), no el fuente .py (M65)."""
    src = io.open(TPL, encoding="utf-8").read()
    for n in ast.walk(ast.parse(src)):
        if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str) and len(n.value.value) > 5000):
            return n.value.value
    raise AssertionError("no encontre ANIMUS_HTML")


# ---------------------------------------------------------------- contraste

def _tokens():
    css = io.open(CSS, encoding="utf-8").read()
    saca = lambda b: {m.group(1): m.group(2).strip()
                      for m in re.finditer(r"(--cx-[a-z0-9-]+)\s*:\s*([^;]+);", b)}
    claro = saca(re.search(r":root\s*\{(.*?)\}", css, re.S).group(1))
    md = re.search(r'\[data-theme="dark"\][^{]*\{(.*?)\}', css, re.S)
    oscuro = dict(claro)
    if md:
        oscuro.update(saca(md.group(1)))
    return claro, oscuro


def _rgb(valor, tema):
    vueltas = 0
    while valor.strip().startswith("var(") and vueltas < 6:
        clave = valor.strip()[4:].split(",")[0].split(")")[0].strip()
        valor = tema.get(clave, "#000")
        vueltas += 1
    m = re.match(r"#([0-9a-fA-F]{3,6})", valor.strip())
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(c):
    f = lambda x: (x / 255 / 12.92) if x / 255 <= 0.03928 else (((x / 255 + 0.055) / 1.055) ** 2.4)
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def _contraste(fg, bg, tema):
    a, b = _rgb(fg, tema), _rgb(bg, tema)
    if a is None or b is None:
        return None
    l1, l2 = sorted([_lum(a), _lum(b)], reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def _pares_declarados():
    """Extrae del ARCHIVO todo sitio que declara fondo y texto juntos.

    Se extrae, no se escribe a mano: una lista escrita a mano documenta la
    intencion pero no mide el archivo, asi que no caza una regresion nueva.
    """
    html = _html()
    pares = []

    # (a) reglas del <style> del modulo
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", "\n".join(
            re.findall(r"<style[^>]*>(.*?)</style>", html, re.S))):
        sel, cuerpo = m.group(1).strip().splitlines()[-1].strip(), m.group(2)
        bg = re.search(r"(?:^|;)\s*background(?:-color)?\s*:\s*([^;]+)", cuerpo)
        fg = re.search(r"(?:^|;)\s*color\s*:\s*([^;]+)", cuerpo)
        if bg and fg:
            pares.append((sel, fg.group(1).strip(), bg.group(1).split()[0].strip()))

    # (b) estilos en linea del HTML y de las plantillas del JS
    for m in re.finditer(r'style="([^"]*)"', html):
        cuerpo = m.group(1)
        bg = re.search(r"(?:^|;)\s*background(?:-color)?\s*:\s*([^;]+)", cuerpo)
        fg = re.search(r"(?:^|;)\s*color\s*:\s*([^;]+)", cuerpo)
        if bg and fg:
            pares.append(("inline: " + cuerpo[:44], fg.group(1).strip(),
                          bg.group(1).split()[0].strip()))
    return pares


def test_todo_par_fondo_texto_declarado_junto_pasa_AA():
    """Un par donde el fondo y el texto se declaran juntos se puede medir sin
    suponer nada. Caza el bug original: fondo y texto con el MISMO token."""
    claro, oscuro = _tokens()
    malos = []
    for sel, fg, bg in _pares_declarados():
        rc, ro = _contraste(fg, bg, claro), _contraste(fg, bg, oscuro)
        if rc is None or ro is None:
            continue  # rgba()/transparent: translucido, funciona en los dos temas
        peor = min(rc, ro)
        if peor < 4.5:
            malos.append("%s -> %.2f  (texto %s sobre fondo %s)" % (sel[:52], peor, fg, bg))
    assert not malos, "pares por debajo de AA (4,5):\n  " + "\n  ".join(malos)


def test_los_pares_heredados_pasan_AA():
    """Los que heredan el fondo del contenedor (titulo del modulo sobre .hdr,
    titulos de modal sobre la tarjeta) no se pueden extraer solos: van medidos
    aparte, contra el fondo real de su contenedor."""
    claro, oscuro = _tokens()
    heredados = [
        ("titulo del modulo (h1 sobre .hdr)", "var(--cx-text)", "var(--cx-card)"),
        ("titulo de modal (h3 sobre la tarjeta)", "var(--cx-text)", "var(--cx-card)"),
        ("cifra ESPERADO (sobre la tarjeta)", "var(--cx-info-text)", "var(--cx-card)"),
        ("enlace volver (sobre .hdr)", "var(--cx-primary-text)", "var(--cx-card)"),
    ]
    for nombre, fg, bg in heredados:
        rc, ro = _contraste(fg, bg, claro), _contraste(fg, bg, oscuro)
        assert rc >= 4.5, "%s: %.2f en tema CLARO (AA exige 4,5)" % (nombre, rc)
        assert ro >= 4.5, "%s: %.2f en tema OSCURO (AA exige 4,5)" % (nombre, ro)


def test_medidor_de_contraste_tiene_dientes():
    """Si el medidor no caza el bug original, los tests de arriba no valen nada."""
    claro, _ = _tokens()
    # el bug real: texto blanco sobre la tarjeta, que en claro ES blanca
    assert _contraste("#fff", "var(--cx-card)", claro) < 1.6
    # el otro bug real: fondo y texto con el MISMO token
    assert _contraste("var(--cx-danger-pale)", "var(--cx-danger-pale)", claro) < 1.6


def test_ningun_color_a_mano_salvo_el_texto_del_boton_verde():
    """`#fff` como TEXTO sobre un relleno de COLOR es correcto y no depende del
    tema (M104); en cualquier otro lugar es un valor que ignora el tema."""
    src = io.open(TPL, encoding="utf-8").read()
    sueltos = re.findall(r"(?:background|color|border[a-z-]*)\s*:\s*#[0-9a-fA-F]{3,8}", src)
    # Los admitidos se ENUMERAN, no se cuentan con holgura: un techo con margen se afloja solo
    # y deja de apretar (M104). Los dos son el mismo caso -- texto blanco sobre un relleno de
    # color, que no depende del tema:
    #   1. el boton primario (blanco sobre el gradiente verde)
    #   2. la tarjeta del SALDO de caja (blanco sobre el gradiente violeta) · 4-ago
    ADMITIDOS = [
        ".btn-primary{background:linear-gradient(135deg,#10b981,#059669);color:#fff;}",
        "border-radius:16px;padding:22px 24px;color:#fff;",   # .caja-saldo
    ]
    assert len(sueltos) <= len(ADMITIDOS), "colores a mano que ignoran el tema: %s" % sueltos
    for esperado in ADMITIDOS[:len(sueltos)]:
        assert esperado in src, "el color a mano admitido cambio de lugar: %s" % esperado


# ------------------------------------------------- anti doble-click (dinero)

def test_toda_mutacion_pasa_por_el_guard_anti_doble_click():
    """Un doble click en una accion que INSERTA no puede crear dos registros.

    En Caja Menor y en Contraentrega eso es PLATA: dos recibos con numero
    propio, o un cobro contado dos veces.
    """
    html = _html()
    crudas = re.findall(r"await fetch\([^;]*?_fetchOpts\('(?:POST|DELETE|PATCH|PUT)'", html, re.S)
    assert not crudas, (
        "%d mutacion(es) llaman a fetch() directo en vez de _fetchUna(): %s"
        % (len(crudas), crudas[:3]))

    guardadas = re.findall(r"_fetchUna\([^;]*?_fetchOpts\('(?:POST|DELETE|PATCH|PUT)'", html, re.S)
    assert len(guardadas) >= 14, "esperaba al menos 14 mutaciones protegidas, hay %d" % len(guardadas)
    # y cada una descarta la respuesta nula (el segundo disparo en vuelo)
    # El guard puede llamarse `r`, `r2`, ... segun cuantas mutaciones tenga la funcion: se
    # cuenta la FORMA, no el nombre. Contar el literal marcaba en rojo un guard que si estaba.
    guards = len(re.findall(r"if \(!r\d*\) return;", html))
    assert guards >= len(guardadas), (
        "%d mutaciones protegidas pero solo %d descartan la respuesta nula" %
        (len(guardadas), guards))


def test_el_guard_existe_y_se_suelta_siempre():
    html = _html()
    assert "var _enVuelo = {}" in html
    assert "async function _fetchUna(url, opts)" in html
    # se suelta en un finally: si se soltara solo en el camino feliz, un error de
    # red dejaria la accion muerta hasta recargar la pagina
    assert re.search(r"finally\s*\{\s*delete _enVuelo\[k\];\s*\}", html)


# ------------------------------------------------------------- estructura

def test_ningun_boton_apunta_a_algo_que_no_existe():
    """M112: podar una pantalla deja botones vivos llamando a lo que borraste."""
    html = _html()
    ids = re.findall(r'id="([^"]+)"', html)
    pedidos = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", html))
    assert not (pedidos - set(ids)), "getElementById sin id en el HTML: %s" % sorted(pedidos - set(ids))

    destinos = set(re.findall(r"switchTab\(['\"]([^'\"]+)['\"]\)", html))
    paneles = set(re.findall(r'id="tab-([^"]+)"', html))
    assert not (destinos - paneles), "switchTab a panel inexistente: %s" % sorted(destinos - paneles)

    funciones = set(re.findall(r"function\s+([A-Za-z0-9_]+)\s*\(", html))
    llamadas = set(re.findall(r'onclick="([A-Za-z0-9_]+)\(', html))
    assert not (llamadas - funciones), "onclick a funcion inexistente: %s" % sorted(llamadas - funciones)


def test_nada_pisado_en_el_html_renderizado():
    """M120: un id repetido o una segunda `function esc` rompen la pagina sin error."""
    html = _html()
    ids = re.findall(r'id="([^"]+)"', html)
    dup_id = sorted({x for x in ids if ids.count(x) > 1})
    assert not dup_id, "ids duplicados: %s" % dup_id

    fns = re.findall(r"function\s+([A-Za-z0-9_]+)\s*\(", html)
    dup_fn = sorted({x for x in fns if fns.count(x) > 1})
    assert not dup_fn, "funciones declaradas dos veces: %s" % dup_fn


def test_cada_pestana_tiene_su_cargador():
    """Una pestana sin cargador se abre vacia y parece rota."""
    html = _html()
    pestanas = set(re.findall(r"switchTab\('([a-z]+)'\)", html))
    m = re.search(r"function loadTab\(name\)\s*\{(.*?)\n\}", html, re.S)
    assert m, "no encontre loadTab"
    despacho = m.group(1)
    for tab in sorted(pestanas):
        assert "'%s'" % tab in despacho, "la pestana '%s' no carga nada" % tab


def test_sin_rastro_de_IA_ni_tildes_faltantes():
    """Regla 0: el em-dash delata IA; y una tilde faltante en un titulo se ve."""
    html = _html()
    assert html.count("—") == 0, "quedan em-dash en la UI"
    for palabra in ("Fisico", "Ciclico", "Metodo", "Descripcion", "Codigo"):
        # solo en texto VISIBLE (entre > y <), no en identificadores de codigo
        visibles = re.findall(r">[^<>]*\b%s\b[^<>]*<" % palabra, html)
        assert not visibles, "'%s' sin tilde en texto visible: %s" % (palabra, visibles[:2])


# ------------------------------------------- la marca de contraentrega (3-ago)

def test_el_patron_que_arma_el_selector_de_marca_se_comporta(tmp_path):
    """El selector de marca construye la expresion que decide que pedido entra a la caja.

    Se ejecuta el JS REAL de la pantalla, no una replica: una replica en Python probaria mi
    copia, no lo que corre en el navegador. Dos bugs que este test cazo antes de desplegar:

      1. El patron salia con MAYUSCULAS y el detector compara contra el texto ya normalizado
         a minusculas (`_norm_txt`), asi que elegir "CM: ENTREGADA" no hacia absolutamente
         nada, sin un solo error a la vista (M2: la normalizacion va identica en los dos lados).
      2. Sin anclar a la etiqueta COMPLETA, elegir "vmc" tambien matchea "vmcx" y mete a la
         caja plata que no es contraentrega -- justo lo que esta caja existe para evitar.
    """
    import shutil
    import subprocess
    if not shutil.which("node"):
        pytest.skip("node no disponible")

    html = _html()
    lit = re.search(r"var lit = String\(f\.valor\)[^\n]+;", html)
    nuevo = re.search(r"var nuevo = campo === 'tag' \? [^\n]+;", html)
    assert lit and nuevo, "no encontre la construccion del patron en usarMarca()"

    guion = """
function construir(valor, campo){ var f = {valor: valor}; %s %s return nuevo; }
var casos = [
  ['vmc','tag','az, CM: ENTREGADA, vmc', true],
  ['vmc','tag','vmcx, Facturado',        false],
  ['vmc','tag','vmc',                    true],
  ['CM: ENTREGADA','tag','az, CM: ENTREGADA, Facturado', true],
  ['CM: ENTREGADA','tag','CM: EN REPARTO, Facturado',    false],
  ['manual','gw','manual',                true],
  ['manual','gw','Checkout Mercado Pago', false],
  ['Mercado Pago (COD)','tag','x, Mercado Pago (COD)', true],
  ['Mercado Pago (COD)','tag','Mercado Pago  COD',     false]
];
var malos = [];
casos.forEach(function(c){
  var pat = construir(c[0], c[1]);
  // el detector del backend compara contra el texto normalizado a minusculas
  if (new RegExp(pat).test(c[2].toLowerCase()) !== c[3]) malos.push(JSON.stringify(c) + ' patron=' + pat);
});
console.log(malos.length ? 'MALOS: ' + malos.join(' | ') : 'OK');
""" % (lit.group(0), nuevo.group(0))

    p = tmp_path / "patron.js"
    p.write_text(guion, encoding="utf-8")
    r = subprocess.run(["node", str(p)], capture_output=True, text=True)
    assert r.returncode == 0, "el JS del selector no corre: %s" % r.stderr[:400]
    assert r.stdout.strip() == "OK", r.stdout.strip()


def test_el_selector_SUMA_al_patron_y_no_lo_reemplaza():
    """En Shopify usan la nota 'contraentrega' Y una etiqueta. Si elegir la etiqueta
    REEMPLAZARA el patron, los pedidos marcados por nota dejarian de entrar a la caja."""
    html = _html()
    m = re.search(r"patron = patron \? patron \+ '\|' \+ nuevo : nuevo;", html)
    assert m, "el selector de marca deberia AGREGAR al patron con '|', no pisarlo"


def test_el_arranque_pasa_por_el_despachador_de_pestanas():
    """La pantalla tiene que abrir CARGADA, y eso depende del punto de entrada.

    3-ago: al fusionar Contraentrega dentro de Caja Menor actualice `loadTab` y deje el init
    llamando a `loadCaja()` DIRECTO. Resultado: la pantalla abria con el saldo cargado y la
    seccion de contraentrega en "Cargando..." para siempre -- `loadCod()` solo corria si te
    ibas a otra pestana y volvias. Los dos endpoints respondian 200 con datos.

    Es la misma familia que M112: verifique el despachador y no el punto de ENTRADA. Cuando
    hay un despachador, el arranque lo usa; un cargador suelto en el init queda viejo la
    proxima vez que una pestana cargue algo mas.
    """
    html = _html()
    m = re.search(r"//\s*Init\s*\n(.*?)</script>", html, re.S)
    assert m, "no encontre el bloque Init"
    # sin los comentarios: este mismo comentario NOMBRA `loadCaja()` al explicar el bug, y
    # escanear el texto crudo lo contaba como una llamada (el test se cazo a si mismo)
    init = "\n".join(l for l in m.group(1).splitlines() if not l.strip().startswith("//"))
    assert "loadTab(" in init, "el init no pasa por loadTab · la pestana abriria a medias"
    sueltos = [f for f in re.findall(r"\b(load[A-Z]\w+|cargar[A-Z]\w+)\(\)", init)]
    assert not sueltos, (
        "el init llama cargadores sueltos %s en vez de loadTab: lo que loadTab agregue "
        "para esa pestana no correria al abrir" % sueltos)


def test_cada_pestana_carga_todo_lo_que_muestra():
    """Si un panel tiene una tabla que empieza en 'Cargando...', alguien tiene que llenarla.

    Caza el sintoma exacto que reporto Sebastian: una seccion que se queda en 'Cargando...'
    porque su cargador no esta enganchado a la pestana donde vive.
    """
    html = _html()
    m = re.search(r"function loadTab\(name\)\s*\{(.*?)\n\}", html, re.S)
    assert m, "no encontre loadTab"
    despacho = m.group(1)

    # Los contenedores que viven dentro de un MODAL no entran: un modal se llena cuando se
    # abre, no al cargar la pestana, y contarlos como "de la pestana" es medir mal (el
    # trinquete marcaba 'marca-cuerpo', que es el cuerpo del selector de marca).
    en_modal = set()
    for m_ in re.finditer(r'<div id="(modal-[^"]+)"', html):
        fin_ = html.find('<div id="modal-', m_.end())
        trozo = html[m_.start():fin_ if fin_ > 0 else m_.start() + 4000]
        en_modal |= set(re.findall(r'id="([a-z-]+)"', trozo))

    # cada panel -> los tbody con 'Cargando...' que contiene -> quien los llena
    for tab in sorted(set(re.findall(r"switchTab\('([a-z]+)'\)", html))):
        ini = html.find('id="tab-%s"' % tab)
        assert ini > 0, tab
        sig = [html.find('id="tab-%s"' % t) for t in
               set(re.findall(r'id="tab-([a-z]+)"', html)) if html.find('id="tab-%s"' % t) > ini]
        panel = html[ini:min(sig) if sig else len(html)]
        pendientes = re.findall(r'id="([a-z-]+)"[^>]*>\s*(?:<tr>)?\s*<td[^>]*>Cargando', panel)
        pendientes += re.findall(r'id="([a-z-]+)"[^>]*>Cargando', panel)
        for cont in set(pendientes) - en_modal:
            # el contenedor tiene que ser escrito por alguna funcion que la pestana dispara
            escritores = re.findall(
                r"function\s+([A-Za-z0-9_]+)[^\n]*\n(?:.(?!\nfunction ))*?getElementById\('%s'\)"
                % re.escape(cont), html, re.S)
            assert escritores, "nadie llena '%s' (panel de la pestana '%s')" % (cont, tab)
            enganchado = any(e in despacho for e in escritores) or any(
                re.search(r"\b%s\(\)" % re.escape(e), despacho) for e in escritores)
            if not enganchado:
                # puede llenarlo un cargador que SI esta en el despacho
                llamados = re.findall(r"\b(load[A-Z]\w+|cargar[A-Z]\w+)\(\)", despacho)
                cuerpos = "".join(
                    html[html.find("function %s" % f):html.find("function %s" % f) + 2500]
                    for f in llamados if html.find("function %s" % f) > 0)
                enganchado = ("'%s'" % cont) in cuerpos or any(
                    e in cuerpos for e in escritores)
            assert enganchado, (
                "la pestana '%s' muestra '%s' pero loadTab no dispara quien lo llena · "
                "quedaria en 'Cargando...'" % (tab, cont))
