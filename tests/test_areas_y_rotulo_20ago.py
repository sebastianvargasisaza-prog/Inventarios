"""Lo que Sebastián reportó el 20-ago-2026, con la pantalla y la etiqueta impresa delante.

  1. *"aquí no están saliendo todas las áreas con las que contamos"* (Registrar Producción).
  2. *"los rótulos de limpieza se ven así al imprimirlos, el logo se pierde, salen esas
     rayas"* — la térmica no tiene grises: cada tono intermedio lo resuelve con una trama
     de puntos, y un logo con antialiasing sale rayado.
  3. *"en la firma la idea es que quede el espacio para que firmen con lapicero, no es
     necesario el nombre"*.

Y lo que salió de medir el punto 1 contra producción: la pantalla de áreas mostraba
ACTIVAS las cuatro áreas que están apagadas, por un `int(v or 1)` que convierte el 0 en 1.
"""
def test_el_cero_no_se_convierte_en_uno():
    from api.blueprints.admin import _flag_activo

    """`int(v or 1)` leía una fila apagada como encendida. Y en Postgres el valor llega
    como bool o como texto, que es la otra mitad de la trampa."""
    for apagado in (0, False, '0', 'f', 'false', 'FALSE', 'no'):
        assert _flag_activo(apagado) == 0, "leyó %r como encendido" % (apagado,)
    for encendido in (1, True, '1', 't', 'true', 'YES'):
        assert _flag_activo(encendido) == 1, "leyó %r como apagado" % (encendido,)
    # Sin dato, manda el default declarado en cada llamada (activo=1, puede_producir=0).
    assert _flag_activo(None) == 1
    assert _flag_activo(None, 0) == 0
    assert _flag_activo('') == 1
    assert _flag_activo('cualquier cosa', 0) == 0


def test_el_logo_del_rotulo_se_imprime_en_blanco_y_negro():
    """Binarizar acá -y no dejárselo al driver térmico- es lo que hace que salga el trazo."""
    import base64
    import io

    from api.blueprints.programacion import _logo_mono_datauri
    try:
        from PIL import Image
    except ImportError:                                    # pragma: no cover
        import pytest
        pytest.skip("sin Pillow")
    # Logo de prueba: fondo transparente + un trazo gris medio (el tono que la térmica
    # convierte en rayas).
    im = Image.new('RGBA', (40, 40), (0, 0, 0, 0))
    for x in range(8, 32):
        for y in range(18, 22):
            im.putpixel((x, y), (90, 100, 130, 255))
    buf = io.BytesIO(); im.save(buf, format='PNG')
    src = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')

    out = _logo_mono_datauri(src)
    assert out.startswith('data:image/png;base64,'), "no devolvió el logo binarizado"
    mono = Image.open(io.BytesIO(base64.b64decode(out.split(',', 1)[1])))
    assert mono.mode == '1', "quedó con grises: la térmica los imprime como trama"
    colores = {c for _n, c in (mono.convert('L').getcolors() or [])}
    assert colores <= {0, 255}, "quedaron tonos intermedios: %r" % (sorted(colores)[:5],)
    assert 0 in colores, "el trazo desapareció al binarizar"
    # Un src que no es data-uri (el SVG del repo) se devuelve tal cual: el rótulo cae al
    # logo normal en vez de quedarse sin logo.
    assert _logo_mono_datauri('/static/logos/espagiria.svg') == ''


def test_los_estados_salen_en_el_orden_del_formato():
    """El F02 lista Limpio · En uso · Sucio en ese orden; el parámetro no manda el orden."""
    from api.blueprints.programacion import _rotulo_estados_pedidos
    assert _rotulo_estados_pedidos('sucio,limpio') == ['limpio', 'sucio']
    assert _rotulo_estados_pedidos('limpio, en uso ,SUCIO') == ['limpio', 'en_uso', 'sucio']
    assert _rotulo_estados_pedidos('inventado') == [None], "aceptó un estado que no existe"
    # Sin el parámetro: una sola hoja con el estado real del área, como antes de tener
    # el juego de tres (una URL viva no cambia de comportamiento · M120).
    assert _rotulo_estados_pedidos('') == [None]
    assert _rotulo_estados_pedidos(None) == [None]


def test_el_desplegable_ofrece_envasado_y_apoyo():
    """*"aquí no están saliendo todas las áreas con las que contamos"*: el desplegable de
    Registrar Producción filtraba por `puede_producir`, así que sólo salían las salas de
    fabricación. Ahora ofrece también envasado y las de apoyo donde se trabaja el lote
    (dispensación y acondicionamiento), agrupadas para que no sea una lista plana.

    Se lee el template y no la página servida: este archivo importa la app en otros tests
    y hacerlo antes del fixture deja la sesión sin usuarios (login bloqueado)."""
    import io
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = io.open(os.path.join(raiz, 'api', 'templates_py', 'dashboard_html.py'),
                  encoding='utf-8').read()
    assert 'function cargarAreasFab' in src, "no está el cargador del desplegable"
    js = src.split('function cargarAreasFab', 1)[1][:2200]
    for grupo in ('<optgroup label="Fabricación">', '<optgroup label="Envasado">',
                  '<optgroup label="Apoyo">'):
        assert grupo in js, "falta el grupo %s" % grupo
    assert "'DISP':1" in js and "'ACOND':1" in js, "no incluye dispensación ni acondicionamiento"
    # Lo que NO entra: almacenes, lavado, esclusa, calidad y recepción no tocan el lote.
    assert "'ALMP'" not in js and "'RECEP'" not in js, "metió salas que no trabajan el lote"
