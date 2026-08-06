# -*- coding: utf-8 -*-
"""Tres cosas de la bandeja de pagos de caja, todas reportadas mirando la pantalla real.

1. **El "ver" del respaldo daba 404.** Alguien escribió *"soporte de pago, fisico"* en el campo
   del comprobante -- que es un hecho REAL: el respaldo está en papel, en una carpeta -- y el
   sistema lo guardaba como URL y lo pintaba como enlace: click → `/soporte%20de%20pago,%20fisico`
   → 404. Un dato que se captura bien y se muestra como otra cosa termina rompiéndose (M115).

2. **Una solicitud mal hecha que ya estaba AUTORIZADA no se podía frenar.** Sebastián, sobre
   SP-2026-0003: *"esta la hicieron mal, pero debe eliminarse, quizás algo que diga rechazar o
   eliminar y que escriban porqué"*. El endpoint ya aceptaba rechazar en `solicitada` Y en
   `autorizada`; la pantalla sólo ofrecía el botón en la primera (M121: construido e
   inalcanzable justo donde hacía falta).

3. **El número de cuenta se veía en 11px.** Es el único dato que hay que transcribir EXACTO y
   donde un error manda la plata a otro lado: *"se ven super pequeños... que después no tengamos
   errores"*. Va grande y con botón de copiar -- leerlo bien ayuda, no tener que teclearlo lo
   elimina.
"""
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))


def _html():
    from templates_py.animus_html import ANIMUS_HTML
    return ANIMUS_HTML


def _js():
    return re.sub(r'//[^\n]*', '', _html())


# ── 1 · el respaldo que no es un enlace ──────────────────────────────────────

def test_un_respaldo_EN_PAPEL_no_se_pinta_como_enlace(app, db_clean):
    js = _js()
    assert 'function _cajaRespaldo' in js, 'no hay nada que distinga papel de archivo'
    i = js.find('function _cajaRespaldo')
    bloque = js[i:i + 700]
    assert '_cajaEsUrl(v)' in bloque, 'pinta el enlace sin mirar si es un enlace'
    # y el camino de la NOTA no arma un <a>
    nota = bloque[bloque.find('return', bloque.find('_cajaEsUrl')) + 40:]
    assert '<a href' not in nota, 'el respaldo en papel sigue saliendo como enlace'
    # ⚠ Y la FILA tiene que usarlo: el ayudante puede existir y la fila seguir armando el <a>
    # a mano. Verificar sólo la función es medir el proxy en vez del hecho (M154).
    assert '_cajaRespaldo(s.comprobante_url' in js, 'la fila no usa el ayudante · sigue enlazando todo'


def test_el_respaldo_en_papel_NO_se_pierde(app, db_clean):
    """No alcanza con no enlazarlo: el texto tiene que seguir viéndose, porque dice DÓNDE está
    el comprobante. Ocultarlo sería perder el dato para no mostrar un enlace roto."""
    js = _js()
    i = js.find('function _cajaRespaldo')
    bloque = js[i:i + 700]
    assert "+e(v)+" in bloque.replace(' ', ''), 'el texto del respaldo no se muestra'


def test_reconoce_las_dos_formas_de_URL(app, db_clean):
    """Un comprobante puede ser `https://...` (subido a R2) o `/uploads/...` (ruta interna).
    Si sólo reconociera una, la otra se vería como nota y dejaría de abrirse."""
    js = _js()
    i = js.find('function _cajaEsUrl')
    bloque = js[i:i + 320]
    assert 'https?' in bloque, 'no reconoce una URL absoluta'
    assert bloque.count('test(t)') == 2, 'no reconoce las dos formas'


# ── 2 · rechazar una solicitud mal hecha ─────────────────────────────────────

def test_se_puede_RECHAZAR_una_ya_autorizada(app, db_clean):
    """El caso de SP-2026-0003: pasó el tope, quedó "lista para pagar", y estaba mal."""
    js = _js()
    i = js.find("s.estado === 'autorizada'")
    assert i > 0
    bloque = js[i:i + 900]
    assert 'spRechazar(' in bloque, 'una solicitud autorizada no se puede frenar desde la pantalla'
    assert 'spPagar(' in bloque, 'se perdió el botón de pagar'


def test_el_rechazo_EXIGE_motivo(app, admin_client, db_clean):
    """Un rechazo sin motivo deja al que pidió sin saber qué corregir, y a quien audite sin
    saber por qué no se pagó."""
    from .conftest import csrf_headers
    r = admin_client.post('/api/caja/solicitudes/999999/rechazar',
                          data=json.dumps({'motivo': ''}), headers=csrf_headers(),
                          content_type='application/json')
    assert r.status_code == 400, r.data[:200]
    assert 'motivo' in r.get_data(as_text=True).lower()


def test_rechazar_NO_borra_la_solicitud(app, admin_client, db_clean):
    """*"debe eliminarse"* -- pero la plata que NO se pagó también hay que poder explicarla, así
    que se rechaza con motivo y queda el rastro (nunca un DELETE)."""
    import io as _io
    src = _io.open(os.path.join(RAIZ, 'api/blueprints/animus.py'), encoding='utf-8').read()
    i = src.find('def caja_solicitud_rechazar')
    bloque = src[i:i + 1400]
    assert "estado='rechazada'" in bloque
    assert 'DELETE FROM caja_solicitudes_pago' not in bloque, 'borra en vez de rechazar'
    assert 'motivo_rechazo' in bloque, 'no guarda el motivo'
    assert 'rowcount == 0' in bloque, 'sin CAS · dos rechazos concurrentes pasan los dos'


# ── 3 · el número de cuenta legible ──────────────────────────────────────────

def test_el_numero_de_cuenta_va_GRANDE(app, db_clean):
    from templates_py.caja_modal import CAJA_MODAL_CSS
    assert '.cajam-cuenta b' in CAJA_MODAL_CSS, 'el número de cuenta no tiene estilo propio'
    i = CAJA_MODAL_CSS.find('.cajam-cuenta b')
    bloque = CAJA_MODAL_CSS[i:i + 260]
    m = re.search(r'font-size:(\d+(?:\.\d+)?)px', bloque)
    assert m and float(m.group(1)) >= 15, 'el dato que hay que transcribir exacto sigue chico'
    assert 'letter-spacing' in bloque, 'sin aire entre dígitos se leen mal los números largos'
    assert 'monospace' in bloque, 'sin monoespaciado los dígitos no se alinean'


def test_hay_boton_de_COPIAR(app, db_clean):
    """Leerlo bien ayuda; no tener que teclearlo elimina el error."""
    js = _js()
    assert 'function cajaCopiar' in js, 'no se puede copiar el número'
    i = js.find('function cajaComoPagar')
    bloque = js[i:i + 2000]
    assert 'cajaCopiar(this' in bloque, 'el botón de copiar no está en la fila'


def test_el_copiar_tiene_RESPALDO_sin_portapapeles(app, db_clean):
    """Sin HTTPS o en un navegador viejo el portapapeles moderno no existe · sin respaldo el
    botón queda mudo, que es peor que no tenerlo."""
    js = _js()
    assert 'function cajaCopiarFallback' in js
    # ⚠ Se cuentan las LLAMADAS (llevan argumentos), no el nombre: la DEFINICIÓN está a pocas
    # líneas y una ventana de texto la encuentra igual con el respaldo desconectado (M154).
    assert js.count('cajaCopiarFallback(txt') >= 2,         'el respaldo está definido pero no se usa en los dos caminos que pueden fallar'


def test_si_FALTA_el_numero_se_dice(app, db_clean):
    """Una transferencia sin número de cuenta no se puede pagar · un espacio en blanco se lee
    como "no hace falta" (M100)."""
    js = _js()
    i = js.find('function cajaComoPagar')
    bloque = js[i:i + 2000]
    assert 'falta el numero' in bloque, 'una transferencia sin cuenta no avisa'


def test_toda_funcion_llamada_esta_DEFINIDA(app, db_clean):
    """El corte que extrae el JS compartido empieza en el ayudante de copiar · si empezara más
    abajo, el botón llamaría a una función inexistente y no haría nada (M146)."""
    H = _html()
    js = _js()
    definidas = set(re.findall(r'function\s+(\w+)\s*\(', js))
    llamadas = set(re.findall(r'on\w+="(\w+)\(', H))
    assert not (llamadas - definidas), sorted(llamadas - definidas)
    assert 'cajaCopiar' in definidas, 'el ayudante de copiar quedó fuera del corte'
