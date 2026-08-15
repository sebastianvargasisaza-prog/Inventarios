"""Programación no puede abrir en blanco (Sebastián 14-ago-2026).

"aquí no está cargando, toca darle a Necesidades para que cargue · eso debería
cargar solo".

`switchProgTab` hacía, en este orden: cargar los datos del tab → apagar todos los
paneles → encender el destino. Y toda la función vive dentro de un `try` que sólo
hace `console.warn`, así que si una carga tiraba una excepción el conmutador ya
había apagado todo y nunca encendía nada: **pantalla en blanco, sin un error a la
vista**. Al hacer click después sí funcionaba, y por eso se leía como "hay que
darle a Necesidades".

La invariante que fija este test es la del conmutador (M112): lo que se VE no puede
depender de que la carga de datos salga bien.
"""
import ast
import io
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _js_del_dashboard():
    """El VALOR EVALUADO, no el fuente: los escapes de Python engañan (M65)."""
    ruta = os.path.join(RAIZ, 'api', 'templates_py', 'dashboard_html.py')
    with io.open(ruta, encoding='utf-8') as fh:
        arbol = ast.parse(fh.read())
    trozos = []
    for nodo in ast.walk(arbol):
        if (isinstance(nodo, ast.Assign) and len(nodo.targets) == 1
                and isinstance(nodo.targets[0], ast.Name)
                and isinstance(nodo.value, ast.Constant)
                and isinstance(nodo.value.value, str)
                and 'function switchProgTab' in nodo.value.value):
            trozos.append(nodo.value.value)
    assert trozos, 'no se encontró switchProgTab en ninguna constante'
    return trozos[0]


def _cuerpo_switchprogtab(js):
    i = js.find('function switchProgTab')
    assert i > 0
    # hasta la siguiente declaración de función de nivel superior
    j = js.find('\n  function ', i + 10)
    return js[i:j if j > 0 else i + 12000]


def test_el_panel_se_enciende_antes_de_cargar_los_datos():
    cuerpo = _cuerpo_switchprogtab(_js_del_dashboard())
    i_mostrar = cuerpo.find('Ocultar TODOS los ptab-')
    i_carga = cuerpo.find("Lazy-load Abastecimiento")
    assert i_mostrar > 0, 'no está el bloque que enciende el panel'
    assert i_carga > 0, 'no están las cargas diferidas'
    assert i_mostrar < i_carga, (
        'las cargas de datos volvieron a correr ANTES de encender el panel: si una '
        'falla, Programación abre en blanco')


def test_cada_carga_diferida_esta_aislada():
    """Una que falle no puede llevarse puestas a las demás ni al resto de la función."""
    cuerpo = _cuerpo_switchprogtab(_js_del_dashboard())
    for llamada in ('cargarNecesidades()', 'cargarPlanEnCurso()'):
        i = cuerpo.find(llamada)
        assert i > 0, 'no se llama %s' % llamada
        ventana = cuerpo[max(0, i - 260):i]
        assert 'try' in ventana, '%s no está dentro de un try propio' % llamada


def test_entrar_a_programacion_selecciona_un_sub_tab():
    """El conmutador apaga todos los paneles: si nadie enciende uno, queda en blanco."""
    js = _js_del_dashboard()
    i = js.find("if(n==='programacion')")
    assert i > 0, 'no está el handler de la pestaña Programación'
    # La ventana cubre el bloque entero: los comentarios que explican el porqué son
    # largos, y una ventana corta mediría los comentarios en vez del código.
    ventana = js[i:i + 1800]
    assert ('switchProgTab' in ventana or 'switchProgGroup' in ventana), (
        'entrar a Programación ya no selecciona ningún sub-tab')


def test_todo_destino_del_conmutador_tiene_su_panel():
    """Un destino sin panel deja la pantalla vacía y no da ningún error (M112)."""
    js = _js_del_dashboard()
    cuerpo = _cuerpo_switchprogtab(js)
    i = cuerpo.find('var TAB_TO_DIV')
    j = cuerpo.find('};', i)
    mapa = dict(re.findall(r"'([a-z0-9_]+)'\s*:\s*'([a-z0-9-]+)'", cuerpo[i:j]))
    assert mapa, 'no se pudo leer el mapa de tab -> panel'
    faltan = [f'{t} -> {d}' for t, d in mapa.items() if ('id="%s"' % d) not in js]
    assert not faltan, 'destinos del conmutador sin panel en el HTML: %s' % faltan


def test_entrar_a_programacion_tiene_red_de_seguridad():
    """Si por lo que sea ningún panel quedó visible, se enciende el default.

    No alcanza con arreglar el orden: la pantalla en blanco no puede depender de que
    ninguna de las cargas falle nunca. El chequeo mira los paneles REALES del DOM.
    """
    js = _js_del_dashboard()
    i = js.find("if(n==='programacion')")
    assert i > 0
    ventana = js[i:i + 1800]
    assert 'switchProgGroup' in ventana, 'entrar ya no sincroniza el grupo con la sub-barra'
    assert 'ptab-' in ventana, 'la red ya no mira los paneles reales del DOM'
    assert 'if(!visible' in ventana, 'la red ya no comprueba si quedó alguno visible'
    assert "switchProgTab('necesidades')" in ventana, (
        'la red de seguridad no enciende ningún panel')
