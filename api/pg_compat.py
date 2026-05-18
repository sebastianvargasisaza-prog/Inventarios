"""Compatibilidad SQLite -> PostgreSQL · Fase 1 de la migración.

EOS tiene ~3.700 consultas escritas con el placeholder `?` de SQLite.
PostgreSQL (driver psycopg) usa `%s`. Reescribir las 3.700 a mano sería
inviable y peligroso · en su lugar el SQL se traduce en el punto único
donde se ejecuta (el cursor adaptado de `get_db()`).

`translate_placeholders` convierte `?` -> `%s` y escapa los `%` literales
a `%%` (psycopg interpreta `%` como inicio de parámetro cuando hay args).
Respeta los `?` y `%` que están DENTRO de literales de string SQL (`'...'`),
incluyendo la comilla escapada estilo SQL (`''`).

Este módulo es PURO (sin dependencias, sin I/O) · se testea en
tests/test_pg_compat.py sin necesidad de una base de datos.
"""


def translate_placeholders(sql: str) -> str:
    """Traduce SQL estilo SQLite (`?`) a estilo psycopg (`%s`).

    Reglas:
      - `?` fuera de un string literal  -> `%s`
      - `?` dentro de un string literal -> se deja igual
      - `%` en cualquier posición       -> `%%` (psycopg lo exige cuando
        la consulta lleva parámetros)

    Maneja literales `'...'` con la comilla escapada de SQL (`''`).
    No interpreta comillas dobles: en SQL estándar (y PostgreSQL) `"..."`
    delimita identificadores, no strings, y no contienen `?`/`%` relevantes.
    """
    out = []
    in_str = False          # ¿estamos dentro de un literal '...'?
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if in_str:
            if ch == "'":
                # Comilla escapada '' -> sigue dentro del string.
                if i + 1 < n and sql[i + 1] == "'":
                    out.append("''")
                    i += 2
                    continue
                in_str = False
                out.append(ch)
            elif ch == '%':
                out.append('%%')
            else:
                out.append(ch)
        else:
            if ch == "'":
                in_str = True
                out.append(ch)
            elif ch == '?':
                out.append('%s')
            elif ch == '%':
                out.append('%%')
            else:
                out.append(ch)
        i += 1
    return ''.join(out)
