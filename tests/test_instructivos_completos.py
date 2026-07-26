"""Todo producto del batch record tiene que tener su instructivo de fabricación (26-jul).

Los 27 primeros entraron el 24-jul de una sola carga. `SUERO HIDRATANTE AH 1.5%` quedó afuera y
nadie lo notó por meses: su PDF exportado (formato viejo de abril) traía SOLO las 2 páginas de
pesajes — la sección "5. Fabricación/Mezcla" no bajó en la exportación. Se descubrió revisando la
cadena de Producción a mano, no por una alarma. Este test es la alarma.

⚠ Compara las dos CONSTANTES (`BATCH_FORMULAS` vs `BATCH_INSTRUCTIVOS`), NO la BD. La BD de tests
es compartida y otros archivos siembran fórmulas de prueba (`PROD PCT TEST`, `REVINC PRODUCTO A`…)
que aparecerían como "producto activo sin instructivo" según el orden en que corran. Un test que
depende del orden de los demás no es una alarma, es ruido — y así fue como puse el gate en rojo.
"""


import os
import sys

# Estos tests NO usan el fixture `app` (a propósito: leen constantes, no la BD compartida), así que
# hay que poner `api/` en el path a mano — el fixture es quien normalmente lo hace.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api'))


def _norm(s):
    return ' '.join(str(s or '').upper().split())


def test_todo_producto_del_batch_tiene_instructivo():
    """Si entra un producto nuevo al batch sin su procedimiento, esto lo dice."""
    from batch_formulas_data import BATCH_FORMULAS, BATCH_INSTRUCTIVOS
    con_instructivo = {_norm(k) for k in BATCH_INSTRUCTIVOS}
    faltan = sorted(k for k in BATCH_FORMULAS if _norm(k) not in con_instructivo)
    assert not faltan, (
        'productos con fórmula del batch pero SIN instructivo de fabricación: %s · un lote no se '
        'puede fabricar sin procedimiento aprobado (BPM/INVIMA)' % faltan)


def test_no_hay_instructivo_huerfano():
    """Un instructivo cuyo producto no existe sería un nombre mal escrito: no llegaría a ningún MBR."""
    from batch_formulas_data import BATCH_FORMULAS, BATCH_INSTRUCTIVOS
    con_formula = {_norm(k) for k in BATCH_FORMULAS}
    huerfanos = sorted(k for k in BATCH_INSTRUCTIVOS if _norm(k) not in con_formula)
    assert not huerfanos, (
        'instructivos cuyo producto no está en BATCH_FORMULAS (¿nombre mal escrito?): %s' % huerfanos)


def test_el_instructivo_de_AH_tiene_sus_6_pasos():
    """El que faltaba. Se transcribió de MyBatch porque el PDF no lo traía."""
    from batch_formulas_data import BATCH_INSTRUCTIVOS
    pasos = BATCH_INSTRUCTIVOS.get('SUERO HIDRATANTE AH 1.5%')
    assert pasos and len(pasos) == 6, pasos
    todo = ' '.join(pasos)
    # las tres cosas que definen ESTE procedimiento y no otro
    assert '70%' in todo and '30%' in todo, 'el agua se divide en dos partes'
    assert 'batidora de mano' in todo
    assert 'fenoxietanol' in todo.lower(), 'el conservante va al final'
    assert 'Resultado:' not in todo, (
        'los tiempos registrados de un lote concreto no son parte del procedimiento')


def test_ningun_instructivo_quedo_vacio():
    from batch_formulas_data import BATCH_INSTRUCTIVOS
    flojos = {k: len(v or []) for k, v in BATCH_INSTRUCTIVOS.items() if not v or len(v) < 2}
    assert not flojos, 'instructivos con menos de 2 pasos (¿carga incompleta?): %s' % flojos


def test_ningun_paso_quedo_truncado():
    """Un paso cortado a la mitad es peor que no tenerlo: el operario no sabe qué le falta."""
    from batch_formulas_data import BATCH_INSTRUCTIVOS
    malos = []
    for prod, pasos in BATCH_INSTRUCTIVOS.items():
        for i, p in enumerate(pasos, 1):
            t = str(p).strip()
            if len(t) < 20 or t[-1] not in '.:)':
                malos.append('%s · paso %d termina en %r' % (prod, i, t[-40:]))
    assert not malos, 'pasos sospechosos de estar truncados: %s' % malos[:5]
