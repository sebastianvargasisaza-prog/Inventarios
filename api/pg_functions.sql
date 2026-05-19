-- Funciones de compatibilidad SQLite -> PostgreSQL · migracion Fase 3-4.
--
-- EOS usa date()/datetime() de SQLite con modificadores ('now', '-5 hours',
-- '+30 days', 'start of month', 'utc', 'localtime') en ~700 consultas. En
-- vez de traducir cada call site, se DEFINEN esas funciones en Postgres con
-- el mismo comportamiento. Asi las consultas corren tal cual.
--
-- Convencion EOS: 'now' = UTC · '-5 hours' = hora Colombia (UTC-5).
-- El servidor (Render) corre en UTC, por eso 'utc'/'localtime' son no-op.
--
-- Se cargan en cada base ANTES del esquema. En Render se cargan una vez.

-- Helper interno: aplica timestring + modificadores y devuelve un timestamp.
CREATE OR REPLACE FUNCTION _eos_sqlite_ts(p_args text[])
RETURNS timestamp AS $$
DECLARE
  ts timestamp;
  m  text;
  i  int;
BEGIN
  IF p_args IS NULL OR array_length(p_args, 1) IS NULL THEN
    RETURN NULL;
  END IF;
  IF p_args[1] IS NULL THEN
    RETURN NULL;
  END IF;
  IF lower(trim(p_args[1])) = 'now' THEN
    ts := (now() AT TIME ZONE 'UTC');
  ELSE
    BEGIN
      ts := p_args[1]::timestamp;
    EXCEPTION WHEN others THEN
      RETURN NULL;
    END;
  END IF;
  FOR i IN 2 .. coalesce(array_length(p_args, 1), 1) LOOP
    IF p_args[i] IS NULL THEN
      CONTINUE;
    END IF;
    m := lower(trim(p_args[i]));
    IF m = 'utc' OR m = 'localtime' THEN
      CONTINUE;                          -- servidor en UTC · no-op
    ELSIF m = 'start of month' THEN
      ts := date_trunc('month', ts);
    ELSIF m = 'start of day' THEN
      ts := date_trunc('day', ts);
    ELSIF m = 'start of year' THEN
      ts := date_trunc('year', ts);
    ELSE
      BEGIN
        ts := ts + m::interval;          -- '-5 hours', '+30 days', etc.
      EXCEPTION WHEN others THEN
        CONTINUE;                        -- modificador no reconocido
      END;
    END IF;
  END LOOP;
  RETURN ts;
END;
$$ LANGUAGE plpgsql STABLE;

-- datetime(timestring, modificadores...) -> 'YYYY-MM-DD HH24:MI:SS'
CREATE OR REPLACE FUNCTION datetime(variadic p_args text[])
RETURNS text AS $$
  SELECT to_char(_eos_sqlite_ts(p_args), 'YYYY-MM-DD HH24:MI:SS');
$$ LANGUAGE sql STABLE;

-- date(timestring, modificadores...) -> 'YYYY-MM-DD'
-- Sustituye el cast date(x) de Postgres · 1 arg sigue funcionando igual.
CREATE OR REPLACE FUNCTION date(variadic p_args text[])
RETURNS text AS $$
  SELECT to_char(_eos_sqlite_ts(p_args), 'YYYY-MM-DD');
$$ LANGUAGE sql STABLE;

-- Overload explícito de 1 argumento · sin él, `date('x')` lo resuelve
-- Postgres como el cast a tipo date (devolvería un date, no text) y
-- rompería las comparaciones contra columnas TEXT de EOS.
CREATE OR REPLACE FUNCTION date(p_arg text)
RETURNS text AS $$
  SELECT to_char(_eos_sqlite_ts(ARRAY[p_arg]), 'YYYY-MM-DD');
$$ LANGUAGE sql STABLE;

-- NOTA: `date('x')` de 1 argumento Postgres lo resuelve como cast al tipo
-- date (no a la función de arriba). Para que devuelva texto, el adaptador
-- reescribe `date(X)` -> `date(X, '')` (ver pg_compat.forzar_date_texto) ·
-- así siempre se usa la función date(variadic text[]) que devuelve texto.
-- No se usa CREATE CAST porque requiere superusuario (no disponible en
-- el PostgreSQL gestionado de Render).

-- strftime(formato, timestring, modificadores...) -> texto formateado.
-- Traduce los códigos de formato SQLite a los de to_char de Postgres.
CREATE OR REPLACE FUNCTION _eos_strftime_fmt(f text)
RETURNS text AS $$
  SELECT replace(replace(replace(replace(replace(replace(replace(
         replace(replace(f, '%Y', 'YYYY'), '%m', 'MM'), '%d', 'DD'),
         '%H', 'HH24'), '%M', 'MI'), '%S', 'SS'), '%j', 'DDD'),
         '%y', 'YY'), '%%', '%');
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION strftime(variadic p_args text[])
RETURNS text AS $$
  SELECT to_char(
    _eos_sqlite_ts(p_args[2:coalesce(array_length(p_args, 1), 1)]),
    _eos_strftime_fmt(p_args[1]));
$$ LANGUAGE sql STABLE;

-- julianday(timestring, modificadores...) -> número de día juliano (float).
-- EOS lo usa para diferencias de fechas · julianday(a)-julianday(b) = días.
CREATE OR REPLACE FUNCTION julianday(variadic p_args text[])
RETURNS double precision AS $$
  SELECT extract(epoch FROM _eos_sqlite_ts(p_args)) / 86400.0 + 2440587.5;
$$ LANGUAGE sql STABLE;

-- instr(haystack, needle) -> posición 1-based (0 si no está). = strpos.
CREATE OR REPLACE FUNCTION instr(p_haystack text, p_needle text)
RETURNS integer AS $$
  SELECT strpos(p_haystack, p_needle);
$$ LANGUAGE sql IMMUTABLE;

-- printf('%0Nd', valor) -> entero con padding de ceros (único patrón en EOS).
CREATE OR REPLACE FUNCTION printf(p_fmt text, p_val bigint)
RETURNS text AS $$
  SELECT lpad(p_val::text,
              coalesce((substring(p_fmt FROM '%0(\d+)d'))::int, 0), '0');
$$ LANGUAGE sql IMMUTABLE;

-- group_concat: agregado de concatenación de SQLite (separador ',' default).
CREATE OR REPLACE FUNCTION _eos_gc_step(acc text, val text)
RETURNS text AS $$
  SELECT CASE WHEN val IS NULL THEN acc
              WHEN acc IS NULL THEN val
              ELSE acc || ',' || val END;
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE AGGREGATE group_concat(text) (
  sfunc = _eos_gc_step, stype = text);

CREATE OR REPLACE FUNCTION _eos_gc_step2(acc text, val text, sep text)
RETURNS text AS $$
  SELECT CASE WHEN val IS NULL THEN acc
              WHEN acc IS NULL THEN val
              ELSE acc || sep || val END;
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE AGGREGATE group_concat(text, text) (
  sfunc = _eos_gc_step2, stype = text);

-- total(x): como sum() pero devuelve 0.0 en vez de NULL (agregado SQLite).
CREATE OR REPLACE AGGREGATE total(double precision) (
  sfunc = float8pl, stype = double precision, initcond = '0');

-- round(x, n) sobre float: SQLite redondea floats con N decimales · Postgres
-- solo tiene round(numeric, int) de 2 args · se agrega el overload float.
CREATE OR REPLACE FUNCTION round(p_val double precision, p_dec integer)
RETURNS double precision AS $$
  SELECT round(p_val::numeric, p_dec)::double precision;
$$ LANGUAGE sql IMMUTABLE;

-- COLLATE NOCASE: colación case-insensitive de SQLite · se recrea en
-- Postgres con ICU (nivel 2 = ignora mayúsculas/acentos secundarios).
CREATE COLLATION IF NOT EXISTS nocase (
  provider = icu, locale = 'und-u-ks-level2', deterministic = false);

-- max(a,b) / min(a,b) escalares: en SQLite max()/min() con 2+ argumentos
-- son funciones escalares (= greatest/least) · en Postgres max/min solo
-- existen como agregados. Se agregan los overloads escalares · el de 1
-- argumento sigue resolviendo al agregado.
CREATE OR REPLACE FUNCTION max(anycompatible, anycompatible)
RETURNS anycompatible AS $$ SELECT greatest($1, $2); $$ LANGUAGE sql IMMUTABLE;
CREATE OR REPLACE FUNCTION max(anycompatible, anycompatible, anycompatible)
RETURNS anycompatible AS $$ SELECT greatest($1, $2, $3); $$ LANGUAGE sql IMMUTABLE;
CREATE OR REPLACE FUNCTION min(anycompatible, anycompatible)
RETURNS anycompatible AS $$ SELECT least($1, $2); $$ LANGUAGE sql IMMUTABLE;
CREATE OR REPLACE FUNCTION min(anycompatible, anycompatible, anycompatible)
RETURNS anycompatible AS $$ SELECT least($1, $2, $3); $$ LANGUAGE sql IMMUTABLE;

-- sqlite_master: catálogo de SQLite · EOS lo consulta en chequeos de salud
-- y diagnóstico (index.py, admin.py). Se expone como vista sobre pg_catalog.
CREATE OR REPLACE VIEW sqlite_master AS
  SELECT 'table'::text AS type, tablename AS name, tablename AS tbl_name,
         ''::text AS sql
  FROM pg_tables WHERE schemaname = 'public'
  UNION ALL
  SELECT 'index'::text, indexname, tablename, ''::text
  FROM pg_indexes WHERE schemaname = 'public'
  UNION ALL
  SELECT 'trigger'::text, t.tgname, c.relname, ''::text
  FROM pg_trigger t
  JOIN pg_class c ON c.oid = t.tgrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' AND NOT t.tgisinternal;
