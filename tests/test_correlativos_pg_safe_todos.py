"""Los 15 numeradores ya no usan CAST(SUBSTR) · PG-safe (30-jul · M45/M96).

`MAX(CAST(SUBSTR(numero,N) AS INTEGER))` revienta en PostgreSQL en cuanto un número trae un
sufijo no numérico: *"invalid input syntax for type integer"* → **500 en TODA la creación del
año**. Ya pasó con las OCs (`OC-2026-0215-1`) y se arregló ahí; quedaban 15 sitios con el mismo
patrón en `solicitudes_compra`, `maquila_pedidos`, `pedidos` y `despachos`.

Este archivo fija dos cosas:
  1. **que no quede ni uno** (barrido sobre el código · trinquete);
  2. **que el helper esté en el scope y funcione**, ejercitándolo con datos que tienen sufijo.
     Un `siguiente_correlativo` usado sin importar es un `NameError` → 500 silencioso, y el
     golden no abre esos endpoints (es exactamente el bug de `get_db()` de M78).
"""
import os
import re

BPS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api', 'blueprints')


def _es_doc(texto, linea_idx):
    """Distingue una mención en docstring/comentario de código ejecutable."""
    lineas = texto.splitlines()
    linea = lineas[linea_idx].strip()
    if linea.startswith('#'):
        return True
    ctx = ' '.join(lineas[max(0, linea_idx - 4):linea_idx + 1])
    return any(p in ctx for p in ('revienta', 'viejo `MAX', 'jam', 'nunca CAST'))


def test_no_queda_ningun_CAST_SUBSTR_ejecutable():
    """Trinquete: el patrón no puede volver a entrar."""
    sospechosos = []
    for f in sorted(os.listdir(BPS)):
        if not f.endswith('.py'):
            continue
        s = open(os.path.join(BPS, f), encoding='utf-8').read()
        for m in re.finditer(r'CAST\s*\(\s*SUBSTR', s, re.I):
            ln = s[:m.start()].count('\n')
            if not _es_doc(s, ln):
                sospechosos.append('%s:%d' % (f, ln + 1))
    assert not sospechosos, (
        'volvió el CAST(SUBSTR) en un numerador (revienta en PG con cualquier sufijo). '
        'Usá `siguiente_correlativo(c, tabla, columna, prefijo)`: %s' % sospechosos)


def test_todo_archivo_que_lo_usa_lo_tiene_en_el_SCOPE():
    """Un helper usado sin importar es un NameError → 500 silencioso (M78)."""
    faltan = []
    for f in sorted(os.listdir(BPS)):
        if not f.endswith('.py'):
            continue
        s = open(os.path.join(BPS, f), encoding='utf-8').read()
        # llamadas reales, no la palabra en un comentario
        usa = re.search(r'(?<!def )siguiente_correlativo\s*\(', s)
        if not usa:
            continue
        importa = re.search(r'import[^\n]*\bsiguiente_correlativo\b', s)
        if not importa:
            faltan.append(f)
    assert not faltan, 'usan siguiente_correlativo SIN importarlo: %s' % faltan


def test_el_helper_ignora_sufijos_que_reventaban_el_CAST(app):
    """El caso real: `SOL-2026-0215-1` hacía explotar `CAST('0215-1' AS INTEGER)`."""
    from database import get_db
    from audit_helpers import siguiente_correlativo
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM solicitudes_compra WHERE numero LIKE 'SOL-2099-%'")
        for num in ('SOL-2099-0001', 'SOL-2099-0007-1', 'SOL-2099-0003'):
            c.execute("INSERT INTO solicitudes_compra (numero, fecha, estado, solicitante) "
                      "VALUES (?,?,?,?)", (num, '2099-01-01', 'Pendiente', 'test'))
        conn.commit()
        n = siguiente_correlativo(c, 'solicitudes_compra', 'numero', 'SOL-2099-')
        c.execute("DELETE FROM solicitudes_compra WHERE numero LIKE 'SOL-2099-%'")
        conn.commit()
    assert n == 8, 'debería tomar el 7 del número con sufijo y devolver 8, devolvió %r' % n


def test_los_cuatro_numeradores_corren_sin_NameError(app):
    """Se EJERCITA el helper contra las cuatro tablas que quedaban con el patrón viejo:
    si el import faltara o el nombre de tabla/columna estuviera mal, revienta acá."""
    from database import get_db
    from audit_helpers import siguiente_correlativo
    with app.app_context():
        c = get_db().cursor()
        for tabla, col, pref in (('solicitudes_compra', 'numero', 'SOL-2099-'),
                                 ('maquila_pedidos', 'numero', 'MQ-'),
                                 ('pedidos', 'numero', 'PED-2099-'),
                                 ('despachos', 'numero', 'DSP-2099-')):
            n = siguiente_correlativo(c, tabla, col, pref)
            assert isinstance(n, int) and n >= 1, '%s.%s devolvió %r' % (tabla, col, n)
