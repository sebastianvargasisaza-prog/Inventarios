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
import re
import sqlite3

import psycopg

from pg_compat import (translate_placeholders, translate_ddl,
                       es_ddl_a_saltar, es_ddl_a_traducir,
                       es_insert_or, reescribir_insert_or_ignore,
                       rewrite_having_alias, traducir_pragma,
                       forzar_date_texto)


# Cache de columnas PK por tabla (para reescribir INSERT OR REPLACE).
_PK_CACHE = {}


def _pk_columns(pgcur, tabla):
    """Columnas de la PK de `tabla` (lista vacía si no tiene). Cacheado."""
    clave = tabla.lower()
    if clave in _PK_CACHE:
        return _PK_CACHE[clave]
    pgcur.execute(
        "SELECT a.attname FROM pg_index i "
        "JOIN pg_attribute a ON a.attrelid = i.indrelid "
        "                   AND a.attnum = ANY(i.indkey) "
        "WHERE i.indrelid = %s::regclass AND i.indisprimary",
        (clave,))
    pk = [r[0] for r in pgcur.fetchall()]
    _PK_CACHE[clave] = pk
    return pk


# Cache de "¿la tabla tiene columna id?" (para decidir el RETURNING id).
_IDCOL_CACHE = {}


def _tiene_columna_id(pgcur, tabla):
    """True si `tabla` tiene una columna llamada `id`. Cacheado."""
    clave = tabla.lower()
    if clave in _IDCOL_CACHE:
        return _IDCOL_CACHE[clave]
    pgcur.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s "
        "AND column_name = 'id'",
        (clave,))
    res = pgcur.fetchone() is not None
    _IDCOL_CACHE[clave] = res
    return res


_RE_TABLA_INSERT = re.compile(r'INSERT\s+INTO\s+"?(\w+)"?', re.I)


def _tabla_de_insert(sql):
    """Nombre de la tabla de un `INSERT INTO tabla ...` (o None)."""
    m = _RE_TABLA_INSERT.match(sql.lstrip())
    return m.group(1) if m else None


# SQLSTATEs de "el objeto ya existe" · al correr init_db sobre un esquema
# ya cargado, ese DDL redundante se ignora (igual que CREATE ... IF NOT
# EXISTS / safe_alter en SQLite).
_DUP_SQLSTATES = {
    '42P07',  # duplicate_table (incluye índices)
    '42701',  # duplicate_column
    '42710',  # duplicate_object (trigger, constraint)
    '42723',  # duplicate_function
    '42P06',  # duplicate_schema
    '42P16',  # invalid_table_definition (PK ya definida)
}


def _map_error(e):
    """Convierte una excepción psycopg en su equivalente sqlite3.

    EOS está escrito contra sqlite3 · captura `sqlite3.IntegrityError`
    (race conditions, UNIQUE) y `sqlite3.OperationalError` en cientos de
    sitios. El adaptador re-lanza con el tipo sqlite3 para que ese manejo
    de errores siga funcionando sin tocar el código.
    """
    if isinstance(e, (psycopg.errors.IntegrityError,
                      psycopg.errors.RaiseException)):
        # RaiseException = un trigger hizo RAISE · en SQLite los triggers
        # RAISE(ABORT,...) de EOS levantan sqlite3.IntegrityError.
        return sqlite3.IntegrityError(str(e))
    return sqlite3.OperationalError(str(e))


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

    def __eq__(self, other):
        # sqlite3.Row sin row_factory devuelve tuplas · varios tests y
        # call sites comparan `row == (a, b, c)` · se replica esa igualdad.
        if isinstance(other, _Row):
            return self._v == other._v
        if isinstance(other, (tuple, list)):
            return self._v == tuple(other)
        return NotImplemented

    def __ne__(self, other):
        r = self.__eq__(other)
        return r if r is NotImplemented else not r

    def __hash__(self):
        return hash(self._v)

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
        # Cursor aparte para SAVEPOINT/RELEASE/ROLLBACK · si se corrieran
        # en self._cur pisarían el resultado de la query recién ejecutada.
        self._spcur = pgcur.connection.cursor()
        self.connection = conn      # algunos call sites usan cur.connection
        self.lastrowid = None

    def _ejecutar_guardado(self, accion, tolerar_dup=False):
        """Corre `accion()` emulando la semántica de error de SQLite.

        En SQLite un statement que falla NO aborta la conexión · el caller
        captura la excepción y sigue (p.ej. `intentar_insert_con_retry`).
        En Postgres un error aborta toda la transacción. Para replicar el
        comportamiento de SQLite, cada statement transaccional se envuelve
        en un SAVEPOINT: si falla se hace ROLLBACK TO y la transacción
        sigue viva. Las excepciones psycopg se mapean a sqlite3.

        `tolerar_dup`: si el error es "el objeto ya existe" se traga
        silenciosamente (DDL idempotente al re-correr init_db sobre PG).
        """
        if self._cur.connection.autocommit:
            try:
                accion()
            except psycopg.Error as e:
                if tolerar_dup and getattr(e, 'sqlstate', '') in _DUP_SQLSTATES:
                    return self
                raise _map_error(e) from e
            return self
        self._spcur.execute('SAVEPOINT _eos_sp')
        try:
            accion()
        except BaseException as e:
            try:
                self._spcur.execute('ROLLBACK TO SAVEPOINT _eos_sp')
                self._spcur.execute('RELEASE SAVEPOINT _eos_sp')
            except psycopg.Error:
                pass
            if (tolerar_dup and isinstance(e, psycopg.Error)
                    and getattr(e, 'sqlstate', '') in _DUP_SQLSTATES):
                return self
            if isinstance(e, psycopg.Error):
                raise _map_error(e) from e
            raise
        self._spcur.execute('RELEASE SAVEPOINT _eos_sp')
        return self

    def execute(self, sql, params=None):
        self.lastrowid = None
        # PRAGMA: los de lectura (table_info, journal_mode...) se traducen
        # a una consulta Postgres equivalente · los de escritura se ignoran.
        if sql.lstrip()[:6].upper() == 'PRAGMA':
            pg = traducir_pragma(sql)
            if pg is None:
                return self
            return self._ejecutar_guardado(lambda: self._cur.execute(pg))
        # DDL SQLite-only: CREATE/DROP TRIGGER se ignoran (los triggers
        # PostgreSQL se cargan aparte).
        if es_ddl_a_saltar(sql):
            return self
        # CREATE TABLE/INDEX, ALTER TABLE: varios blueprints los corren bajo
        # demanda · se traducen y ejecutan (en tabla existente, el IF NOT
        # EXISTS los vuelve no-op).
        if es_ddl_a_traducir(sql):
            ddl = translate_ddl(sql)
            return self._ejecutar_guardado(
                lambda: self._cur.execute(ddl), tolerar_dup=True)
        # Upsert SQLite (`INSERT OR IGNORE/REPLACE`) -> `ON CONFLICT`.
        tipo = es_insert_or(sql)
        if tipo == 'ignore':
            sql = reescribir_insert_or_ignore(sql)
        elif tipo == 'replace':
            sql = self._reescribir_insert_or_replace(sql)
        # `HAVING <alias>` no es válido en Postgres · se sustituye el alias.
        sql = rewrite_having_alias(sql)
        # `date(X)` de 1 arg -> `date(X,'')` para que devuelva texto.
        sql = forzar_date_texto(sql)
        translated = translate_placeholders(sql)
        p = params if params is not None else ()
        # INSERT plano: Postgres no tiene lastrowid · se resuelve con
        # RETURNING id si la tabla tiene esa columna.
        if _es_insert_plano(translated):
            tabla = _tabla_de_insert(translated)
            if tabla and _tiene_columna_id(self._cur, tabla):
                base = translated.rstrip().rstrip(';')

                def _acc():
                    self._cur.execute(base + ' RETURNING id', p)
                    row = self._cur.fetchone()
                    self.lastrowid = row[0] if row else None
                return self._ejecutar_guardado(_acc)
        return self._ejecutar_guardado(
            lambda: self._cur.execute(translated, p))

    def _reescribir_insert_or_replace(self, sql):
        """`INSERT OR REPLACE INTO t (cols) VALUES ...` -> upsert Postgres.

        Se reescribe a `INSERT INTO ... ON CONFLICT (pk) DO UPDATE SET ...`
        usando la PK de la tabla como objetivo del conflicto (igual que el
        REPLACE de SQLite, que sustituye la fila en colisión de clave).
        """
        base = re.sub(r'^(\s*)INSERT\s+OR\s+REPLACE\s+INTO\b',
                      r'\1INSERT INTO', sql, count=1, flags=re.I)
        base = base.rstrip().rstrip(';')
        m = re.match(r'\s*INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s*\(([^)]*)\)',
                     sql, re.I)
        if not m:
            return base                       # sin lista de columnas
        tabla, cols_raw = m.group(1), m.group(2)
        cols = [c.strip().strip('"') for c in cols_raw.split(',') if c.strip()]
        pk = _pk_columns(self._cur, tabla)
        if not pk:
            return base                       # sin PK no hay conflicto
        set_cols = [c for c in cols if c.lower() not in
                    {p.lower() for p in pk}]
        if set_cols:
            sets = ', '.join('{0}=EXCLUDED.{0}'.format(c) for c in set_cols)
            accion = 'DO UPDATE SET ' + sets
        else:
            accion = 'DO NOTHING'
        return '{0} ON CONFLICT ({1}) {2}'.format(
            base, ', '.join(pk), accion)

    def executemany(self, sql, seq_params):
        self.lastrowid = None
        tipo = es_insert_or(sql)
        if tipo == 'ignore':
            sql = reescribir_insert_or_ignore(sql)
        elif tipo == 'replace':
            sql = self._reescribir_insert_or_replace(sql)
        translated = translate_placeholders(sql)
        filas = list(seq_params)
        return self._ejecutar_guardado(
            lambda: self._cur.executemany(translated, filas))

    def executescript(self, script):
        # sqlite3.executescript · psycopg3 ejecuta varias sentencias si no
        # hay parámetros. Sin traducción de `?` (los scripts son DDL).
        self._cur.execute(script)
        return self

    def fetchone(self):
        # Tras un INSERT/UPDATE sin RETURNING psycopg lanza ProgrammingError
        # al hacer fetch · sqlite3 devuelve None · se replica ese contrato.
        try:
            return self._cur.fetchone()
        except psycopg.ProgrammingError:
            return None

    def fetchall(self):
        try:
            return self._cur.fetchall()
        except psycopg.ProgrammingError:
            return []

    def fetchmany(self, size=None):
        try:
            return (self._cur.fetchmany(size) if size is not None
                    else self._cur.fetchmany())
        except psycopg.ProgrammingError:
            return []

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def __iter__(self):
        try:
            return iter(self._cur)
        except psycopg.ProgrammingError:
            return iter(())

    def close(self):
        for cur in (self._cur, self._spcur):
            try:
                cur.close()
            except Exception:
                pass


class PgConnection:
    """Conexión que imita a sqlite3.Connection sobre psycopg3."""

    def __init__(self, conninfo=None, autocommit=False):
        # EOS asume hora UTC (igual que el 'now' de SQLite) · se fija la
        # zona horaria de la sesión para que CURRENT_DATE / 'now'::date sean
        # consistentes con las funciones date()/datetime() de pg_functions.
        self._conn = psycopg.connect(conninfo or conninfo_desde_env(),
                                     options='-c timezone=UTC')
        self._conn.row_factory = _row_factory
        if autocommit:
            self._conn.autocommit = True
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


def connect(conninfo=None, autocommit=False) -> PgConnection:
    """Abre una conexión PostgreSQL con interfaz estilo sqlite3.

    autocommit=True replica el `isolation_level=None` de SQLite (cada
    statement se confirma solo) · lo usa el audit_log independiente.
    """
    return PgConnection(conninfo, autocommit=autocommit)
