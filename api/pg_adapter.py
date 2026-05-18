"""Adaptador PostgreSQL para EOS · Fase 1 de la migración SQLite -> PostgreSQL.

Expone una conexión que se comporta como `sqlite3.Connection` pero habla con
PostgreSQL (psycopg3) por debajo. Así el código existente —que usa el
placeholder `?` y filas estilo `sqlite3.Row`— sigue funcionando sin tener
que reescribir las ~3.700 consultas a mano.

Qué resuelve el adaptador:
  - Traduce `?` -> `%s` en cada execute (vía pg_compat.translate_placeholders).
  - Filas con acceso por índice (`row[0]`) Y por nombre (`row['col']`),
    como sqlite3.Row.
  - `cursor.lastrowid` tras un INSERT (Postgres no lo tiene · se resuelve
    con `RETURNING id`, protegido por savepoint para no abortar la
    transacción si la tabla no tiene columna `id`).
  - `execute`, `executemany`, `cursor`, `commit`, `rollback`, `rowcount`,
    `description`, iteración.

NO se usa todavía en producción · `get_db()` sigue devolviendo SQLite. El
backend se conmutará por variable de entorno cuando el adaptador esté
validado contra los tests (Fase 4).
"""
import os

import psycopg

from pg_compat import translate_placeholders


def conninfo_desde_env() -> str:
    """Cadena de conexión: usa DATABASE_URL si está, si no el Postgres local."""
    url = os.environ.get('DATABASE_URL', '').strip()
    if url:
        return url
    return (
        f"host={os.environ.get('PGHOST', '127.0.0.1')} "
        f"port={os.environ.get('PGPORT', '5432')} "
        f"user={os.environ.get('PGUSER', 'postgres')} "
        f"dbname={os.environ.get('PGDATABASE', 'eos_dev')}"
    )


class _Row:
    """Fila que se comporta como sqlite3.Row: índice, nombre, len, iteración."""
    __slots__ = ('_v', '_idx')

    def __init__(self, values, idx):
        self._v = values          # tupla de valores
        self._idx = idx           # dict nombre_columna -> posición

    def __getitem__(self, key):
        if isinstance(key, (int, slice)):
            return self._v[key]
        return self._v[self._idx[key]]

    def __len__(self):
        return len(self._v)

    def __iter__(self):
        return iter(self._v)

    def keys(self):
        return list(self._idx)

    def get(self, key, default=None):
        try:
            return self[key]
        except (KeyError, IndexError):
            return default


def _row_factory(cursor):
    """Row factory de psycopg3 que produce _Row (índice + nombre)."""
    desc = cursor.description
    cols = [c.name for c in desc] if desc else []
    idx = {name: i for i, name in enumerate(cols)}

    def make(values):
        return _Row(tuple(values), idx)

    return make


def _es_insert_plano(sql: str) -> bool:
    """¿Es un INSERT simple sin RETURNING? (para resolver lastrowid)."""
    s = sql.lstrip()
    up = s[:12].upper()
    return up.startswith('INSERT INTO') and 'RETURNING' not in sql.upper()


class _Cursor:
    """Cursor que imita al de sqlite3 sobre un cursor psycopg3."""

    def __init__(self, pgcur, conn):
        self._cur = pgcur
        self.connection = conn      # algunos call sites usan cur.connection
        self.lastrowid = None

    def execute(self, sql, params=None):
        self.lastrowid = None
        translated = translate_placeholders(sql)
        p = params if params is not None else ()
        if _es_insert_plano(translated):
            # Postgres no tiene lastrowid · se obtiene con RETURNING id.
            # Protegido por savepoint: si la tabla no tiene columna `id`
            # (PK natural), un RETURNING id abortaría la transacción.
            base = translated.rstrip().rstrip(';')
            self._cur.execute('SAVEPOINT _eos_li')
            try:
                self._cur.execute(base + ' RETURNING id', p)
                row = self._cur.fetchone()
                self.lastrowid = row[0] if row else None
                self._cur.execute('RELEASE SAVEPOINT _eos_li')
            except psycopg.errors.UndefinedColumn:
                self._cur.execute('ROLLBACK TO SAVEPOINT _eos_li')
                self._cur.execute(translated, p)
                self._cur.execute('RELEASE SAVEPOINT _eos_li')
        else:
            self._cur.execute(translated, p)
        return self

    def executemany(self, sql, seq_params):
        self._cur.executemany(translate_placeholders(sql), list(seq_params))
        return self

    def executescript(self, script):
        # sqlite3.executescript · psycopg3 ejecuta varias sentencias si no
        # hay parámetros. Sin traducción de `?` (los scripts son DDL).
        self._cur.execute(script)
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def fetchmany(self, size=None):
        return self._cur.fetchmany(size) if size is not None else self._cur.fetchmany()

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def __iter__(self):
        return iter(self._cur)

    def close(self):
        try:
            self._cur.close()
        except Exception:
            pass


class PgConnection:
    """Conexión que imita a sqlite3.Connection sobre psycopg3."""

    def __init__(self, conninfo=None):
        self._conn = psycopg.connect(conninfo or conninfo_desde_env())
        self._conn.row_factory = _row_factory
        # row_factory de sqlite3 · se acepta y se ignora (siempre _Row).
        self.row_factory = None

    def cursor(self):
        return _Cursor(self._conn.cursor(), self)

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executescript(self, script):
        cur = self.cursor()
        cur.executescript(script)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


def connect(conninfo=None) -> PgConnection:
    """Abre una conexión PostgreSQL con interfaz estilo sqlite3."""
    return PgConnection(conninfo)
