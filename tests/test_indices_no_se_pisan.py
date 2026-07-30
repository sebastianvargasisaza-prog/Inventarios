"""Un nombre de índice repetido es un índice que NO existe (30-jul · M96).

Los nombres de índice son GLOBALES en SQLite y en PostgreSQL. Un
`CREATE INDEX IF NOT EXISTS idx_x ON otra_tabla(...)` con un nombre que ya usó otra
migración es un **no-op silencioso**: no falla, no avisa, y la tabla se queda en scan
completo. El barrido del 30-jul encontró tres pares así -- el peor,
`producto_presentaciones`, es la tabla que el motor de envases consulta por producto.

Este test es un TRINQUETE: si alguien vuelve a reusar un nombre, falla acá y no en
producción seis meses después.
"""
import re
from collections import defaultdict


def _indices_declarados():
    from database import MIGRATIONS
    decl = defaultdict(set)
    pat = re.compile(
        r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-z_0-9]+)\s+ON\s+([a-z_0-9]+)',
        re.I)
    for _v, _d, stmts in MIGRATIONS:
        for st in stmts:
            if not isinstance(st, str):
                continue
            for m in pat.finditer(st):
                decl[m.group(1).lower()].add(m.group(2).lower())
    return decl


def test_ningun_nombre_de_indice_apunta_a_dos_tablas(app):
    """Si un nombre aparece sobre dos tablas, el segundo NUNCA se creó.

    Pide `app` porque `database` sólo es importable con el harness montado."""
    decl = _indices_declarados()
    pisados = {n: sorted(ts) for n, ts in decl.items() if len(ts) > 1}
    assert not pisados, (
        'estos nombres de índice se usan en más de una tabla, así que el segundo de cada par '
        'no existe en la base: %r' % pisados)


def test_las_tablas_que_quedaron_sin_indice_ya_lo_tienen(app):
    """Las tres del barrido: cada una con su nombre propio (mig 401)."""
    decl = _indices_declarados()
    esperados = {
        'idx_mee_lt_origen': 'mee_lead_time_config',
        'idx_prodpres_producto': 'producto_presentaciones',
        'idx_tareas_oper_estado': 'tareas_operativas',
    }
    for nombre, tabla in esperados.items():
        assert nombre in decl, 'falta el índice %s' % nombre
        assert decl[nombre] == {tabla}, '%s debería ser sólo de %s: %r' % (nombre, tabla, decl[nombre])


def test_el_indice_existe_de_verdad_en_la_base(app):
    """Declararlo no alcanza: se comprueba que la migración lo CREA de verdad.

    ⚠ Sólo en SQLite, y la razón importa: el harness de PG **no corre las migraciones** — carga
    la foto `pg_schema.sql` y auto-sana tablas y columnas, pero NO índices. Así que en PG la
    ausencia de un índice nuevo no dice nada del producto (en producción `init_db()` sí corre
    las migraciones al arrancar). Este test falló primero en el gate PG por eso: estaba
    midiendo el harness, no el sistema. En SQLite las migraciones SÍ corren, así que acá el
    chequeo tiene dientes de verdad.
    """
    import os
    from database import get_db
    with app.app_context():
        c = get_db().cursor()
        try:
            filas = c.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'").fetchall()
        except Exception:
            import pytest
            pytest.skip('backend PostgreSQL: el harness carga pg_schema.sql y no corre las '
                        'migraciones, así que no crea índices nuevos (en prod sí se crean)')
            return
        nombres = {str(r[0]).lower() for r in filas}
    if not nombres:
        import pytest
        pytest.skip('sin índices legibles en este backend')
    for n in ('idx_mee_lt_origen', 'idx_prodpres_producto', 'idx_tareas_oper_estado'):
        assert n in nombres, 'el índice %s se declaró pero la migración NO lo creó: %s' % (
            n, sorted(x for x in nombres if 'pres' in x or 'tareas' in x or 'lt_' in x))
