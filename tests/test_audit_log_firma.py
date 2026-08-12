# -*- coding: utf-8 -*-
"""Trinquete · `audit_log` sólo admite el cursor como argumento posicional.

La firma es:

    audit_log(c=None, *, usuario, accion, registro_id, tabla=None, antes=None,
              despues=None, detalle=None)

Todo lo demás es keyword-only, así que una llamada posicional revienta con `TypeError`. El
problema es DÓNDE revienta: el rastro de auditoría se escribe al final de la mutación, después de
la lógica que importa, así que el endpoint hace todo su trabajo y **devuelve 500 en la última
línea**. Desde afuera se lee como "el botón falla", no como "falta el rastro".

Cuando esto se escribió había SIETE llamadas así en `admin.py`, ninguna funcionando: dar de alta
un envase, fijar su volumen, mapear tonos de gloss, anclar impresos, anclar componentes, anclar
tapa/gotero y mapear envase. Ninguna dejaba rastro y todas fallaban, desde el día que se
escribieron -- y no las cazó ningún test porque el golden no abre páginas de admin (M78).

El chequeo es de AST y no de texto: buscar `audit_log(` con una expresión regular encuentra la
propia definición y los comentarios que la explican (M154).
"""
import ast
import io
import os

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api')


def _llamadas_posicionales():
    malas = []
    for base, _dirs, archivos in os.walk(RAIZ):
        for a in archivos:
            if not a.endswith('.py'):
                continue
            ruta = os.path.join(base, a)
            try:
                arbol = ast.parse(io.open(ruta, encoding='utf-8').read())
            except Exception:
                continue
            for n in ast.walk(arbol):
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                        and n.func.id == 'audit_log' and len(n.args) > 1):
                    rel = os.path.relpath(ruta, RAIZ).replace(os.sep, '/')
                    malas.append('%s:%d (%d posicionales)' % (rel, n.lineno, len(n.args)))
    return malas


def test_ninguna_llamada_pasa_argumentos_posicionales():
    malas = _llamadas_posicionales()
    assert not malas, (
        'Estas llamadas a audit_log revientan con TypeError al ejecutarse, y como el rastro se '
        'escribe al final de la mutación el endpoint devuelve 500 después de haber hecho todo su '
        'trabajo:\n  ' + '\n  '.join(malas))


def test_el_trinquete_MUERDE():
    """Un guard que no se prueba contra el defecto real es decorativo (M104).

    Se compila una llamada con la forma exacta del bug y se comprueba que el detector la ve.
    """
    fuente = 'audit_log(None, u, "ACCION", "tabla", "id", "detalle")\n'
    arbol = ast.parse(fuente)
    vistas = [n for n in ast.walk(arbol)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
              and n.func.id == 'audit_log' and len(n.args) > 1]
    assert vistas, 'el detector no reconoce la forma del bug que existe para cazar'


def test_la_forma_correcta_NO_se_marca():
    """Y el caso sano: la llamada bien escrita no puede dar falso positivo.

    Sin esto el trinquete pasaría igual estando roto al revés (marcando todo), y un guard que
    grita de más deja de mirarse.
    """
    fuente = ('audit_log(c, usuario=u, accion="ACCION", tabla="tabla",\n'
              '          registro_id="id", detalle="detalle")\n')
    arbol = ast.parse(fuente)
    vistas = [n for n in ast.walk(arbol)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
              and n.func.id == 'audit_log' and len(n.args) > 1]
    assert not vistas, 'el detector marca como rota una llamada correcta'
