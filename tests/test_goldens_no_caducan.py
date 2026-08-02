"""Un golden con una fecha de vencimiento FIJA caduca solo y rompe el gate (2-ago-2026).

`test_golden_distribuir_fefo_orden` sembraba el lote "cercano" con vencimiento hardcodeado en
`2026-08-01`. Venía verde durante meses y el 2 de agosto empezó a fallar: ese día el lote quedó
VENCIDO, el FEFO lo excluyó -- correctamente, por la guarda de vencimiento-por-fecha (M25) -- y
el golden pasó a exigir que se consumiera un lote vencido.

El código estaba bien. El test envejeció. Y el costo no es el test: es la media hora que se pierde
buscando una regresión que no existe, y la confianza que se le pierde al rojo del gate.

Este trinquete avisa con MESES de anticipación: si un golden siembra un vencimiento que cae
dentro de los próximos 120 días, hay que pasarlo a fecha relativa antes de que rompa.
"""
import os
import re
from datetime import date, timedelta

HORIZONTE_DIAS = 120


def _ruta(nombre):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), nombre)


def test_ningun_golden_siembra_un_vencimiento_que_esta_por_caducar():
    src = open(_ruta('test_golden_paths.py'), encoding='utf-8').read()
    limite = date.today() + timedelta(days=HORIZONTE_DIAS)
    riesgo = []
    # sólo las fechas que acompañan a un vencimiento · una fecha suelta puede ser otra cosa
    for m in re.finditer(r'fecha_vencimiento[^\n]{0,80}?[\'"](\d{4}-\d{2}-\d{2})[\'"]', src):
        try:
            f = date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if f <= limite:
            linea = src[:m.start()].count('\n') + 1
            riesgo.append('línea %d · %s' % (linea, m.group(1)))
    assert not riesgo, (
        'estos golden siembran un vencimiento que caduca dentro de %d días y van a romper el '
        'gate sin que nadie toque el código · pasalos a fecha relativa '
        "(date('now','+30 days')): %s" % (HORIZONTE_DIAS, '; '.join(riesgo)))
