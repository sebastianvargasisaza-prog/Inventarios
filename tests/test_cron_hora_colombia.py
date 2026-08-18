# -*- coding: utf-8 -*-
"""Los crons disparan a la hora que dice su NOMBRE, no 5 horas antes.

Render corre en **UTC** y el planificador comparaba contra `datetime.now()` pelado, así que cada
job se ejecutaba 5 horas antes de lo que promete su nombre. Medido en producción el 18-ago:

    resumen_ejecutivo_noche · programado 19:00 · ejecutado a las **14:05 Colombia**

Con eso, *"lunes 7am"* corría a las **2 de la mañana**, el resumen *"de la noche"* llegaba a las
**2 de la tarde**, y `marcar_vencidos` "7:50" a las 2:50. Los nombres, los comentarios y la
memoria del proyecto asumen hora Colombia: esto ALINEA la realidad con la intención (M24, ahora
en el planificador y no en un dato).

⚠ La transición no duplica nada: `_ya_ejecutado_hoy` compara por DÍA COLOMBIA contra un
`ejecutado_at` que ya se guarda en Colombia. Un job que hoy corrió a las 02:00 queda salteado y
arranca mañana en su hora.
"""
import ast
import io
import os
import re


def _fuente(nombre):
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "api", "blueprints", nombre)
    return io.open(ruta, encoding="utf-8").read()


def _cuerpo(src, firma):
    """El cuerpo REAL de la función · nunca una ventana de N caracteres, que la secuestra
    cualquier función escrita más abajo (M151)."""
    tree = ast.parse(src)
    lineas = src.splitlines()
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == firma:
            return "\n".join(lineas[n.lineno - 1:n.end_lineno])
    raise AssertionError("no encontré la función %s" % firma)


def _sin_comentarios(txt):
    return "\n".join(l for l in txt.splitlines() if not l.strip().startswith("#"))


def test_el_planificador_usa_la_hora_de_colombia():
    codigo = _sin_comentarios(_cuerpo(_fuente("auto_plan_jobs.py"), "_loop_multi_cron"))
    m = re.search(r"ahora\s*=\s*([^\n]+)", codigo)
    assert m, "desapareció el reloj del planificador"
    expr = m.group(1)
    assert "hours=5" in expr, (
        "el planificador volvió al reloj del servidor (UTC en Render): cada job dispararía 5 "
        "horas antes de lo que dice su nombre · valor actual: %r" % expr)


def test_el_transcurrido_del_health_check_no_mezcla_husos():
    """Un diff `now - inicio` exige que los dos estén en la MISMA base.

    `ejecutado_at` se guarda en Colombia; restarle el reloj del servidor inflaba el
    transcurrido en 5 h -- y ese número es el que decide si un cron se da por caído.
    """
    codigo = _sin_comentarios(_cuerpo(_fuente("auto_plan.py"), "planta_health_check"))
    i = codigo.find("ago = ")
    assert i > 0, "desapareció el cálculo del transcurrido de los crons"
    expr = codigo[i:i + 160]
    assert "datetime.now()" not in expr or "hours=5" in codigo[max(0, i - 300):i + 160], (
        "el transcurrido vuelve a restar el reloj del servidor contra una hora Colombia: %r"
        % expr)


def test_el_guard_de_ya_ejecutado_usa_el_mismo_dia_que_el_reloj():
    """Si el reloj es Colombia y el "ya corrió hoy" fuera del servidor, el día del cambio un
    job podría ejecutarse dos veces. Los dos tienen que hablar del MISMO día."""
    codigo = _sin_comentarios(_cuerpo(_fuente("auto_plan_jobs.py"), "_ya_ejecutado_hoy"))
    assert "date('now', '-5 hours')" in codigo or "date('now','-5 hours')" in codigo, (
        "el guard de 'ya se ejecutó hoy' dejó de anclar el día en Colombia: con el reloj del "
        "planificador en Colombia, esto abre la puerta a una doble ejecución")
