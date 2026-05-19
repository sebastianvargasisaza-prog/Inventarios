"""Migra EOS de SQLite a PostgreSQL · Fase 5 de la migración (cutover).

Carga el esquema PostgreSQL y copia TODOS los datos de una base SQLite
(la de producción) a PostgreSQL. Es el mismo mecanismo que usa conftest
para los tests, pero como herramienta de línea de comandos.

Uso:
    # Cutover completo (carga esquema + copia datos):
    python scripts/migrar_datos_a_postgres.py --sqlite /var/data/inventario.db --esquema

    # Solo copiar datos (el esquema PG ya existe):
    python scripts/migrar_datos_a_postgres.py --sqlite /var/data/inventario.db

La conexión PostgreSQL se toma de DATABASE_URL, o de PGHOST/PGPORT/
PGUSER/PGDATABASE si DATABASE_URL no está definida.

ADVERTENCIA: `--esquema` hace `DROP SCHEMA public CASCADE` · borra todo
lo que haya en la base PostgreSQL destino. Úsalo solo en una base nueva.

No requiere superusuario: el orden de dependencias FK se resuelve con un
bucle de reintentos (una tabla que falla por FK se reintenta cuando su
tabla padre ya fue copiada).
"""
import argparse
import os
import sqlite3
import sys

import psycopg

API_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api")
ARCHIVOS_ESQUEMA = ("pg_functions.sql", "pg_schema.sql", "pg_triggers.sql")


def conninfo():
    """Cadena de conexión PostgreSQL · DATABASE_URL o variables PG*."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    return (
        f"host={os.environ.get('PGHOST', '127.0.0.1')} "
        f"port={os.environ.get('PGPORT', '5432')} "
        f"user={os.environ.get('PGUSER', 'postgres')} "
        f"dbname={os.environ.get('PGDATABASE', 'eos_dev')}"
    )


def cargar_esquema(pg):
    """Carga pg_functions + pg_schema + pg_triggers (DROP SCHEMA previo)."""
    with pg.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        for archivo in ARCHIVOS_ESQUEMA:
            with open(os.path.join(API_DIR, archivo), encoding="utf-8") as f:
                cur.execute(f.read())
            print(f"  · esquema cargado: {archivo}")


def copiar_datos(sqlite_path, pg):
    """Copia todas las filas SQLite -> PostgreSQL. Devuelve (resumen, omitidas).

    Cada tabla se copia en su propia transacción · si falla (típicamente
    por una FK cuya tabla padre aún no se copió) se reintenta en la
    siguiente vuelta. El bucle termina cuando ya no hay progreso.
    """
    sq = sqlite3.connect(sqlite_path)
    sq.row_factory = sqlite3.Row
    tablas = [r[0] for r in sq.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()]
    pendientes = {}
    for t in tablas:
        filas = sq.execute('SELECT * FROM "%s"' % t).fetchall()
        if not filas:
            continue
        cols = list(filas[0].keys())
        collist = ", ".join('"%s"' % c for c in cols)
        ph = ", ".join(["%s"] * len(cols))
        sql = 'INSERT INTO "%s" (%s) VALUES (%s)' % (t, collist, ph)
        pendientes[t] = (sql, [tuple(f) for f in filas])
    sq.close()

    # Desactivar los triggers de USUARIO de EOS durante la copia · un
    # trigger creado por una migración tardía (p.ej. trg_fi_material_id_fk)
    # no debe rechazar filas sembradas por una migración temprana. No toca
    # las FK (triggers de sistema) · el bucle de reintentos las resuelve.
    # `DISABLE TRIGGER USER` lo puede hacer el dueño de la tabla, sin
    # superusuario.
    for t in tablas:
        try:
            with pg.cursor() as cur:
                cur.execute('ALTER TABLE "%s" DISABLE TRIGGER USER' % t)
        except psycopg.Error:
            pass

    resumen = []
    ultimo_error = {}
    while pendientes:
        progreso = False
        for t in list(pendientes):
            sql, datos = pendientes[t]
            try:
                with pg.transaction():
                    with pg.cursor() as cur:
                        cur.executemany(sql, datos)
            except psycopg.Error as e:
                ultimo_error[t] = str(e).splitlines()[0][:90]
                continue
            resumen.append((t, len(datos)))
            del pendientes[t]
            progreso = True
        if not progreso:
            break
    omitidas = [(t, ultimo_error.get(t, "no se pudo copiar"))
                for t in pendientes]

    # Reactivar los triggers de usuario.
    for t in tablas:
        try:
            with pg.cursor() as cur:
                cur.execute('ALTER TABLE "%s" ENABLE TRIGGER USER' % t)
        except psycopg.Error:
            pass

    # Reajustar las secuencias IDENTITY al MAX(id)+1.
    for t, _ in resumen:
        try:
            with pg.cursor() as cur:
                cur.execute("SELECT pg_get_serial_sequence(%s, 'id')", (t,))
                fila = cur.fetchone()
                if fila and fila[0]:
                    cur.execute(
                        'SELECT setval(%%s, COALESCE((SELECT MAX(id) '
                        'FROM "%s"), 0) + 1, false)' % t, (fila[0],))
        except psycopg.Error:
            pass
    return resumen, omitidas


def verificar(sqlite_path, pg, resumen):
    """Compara conteos de filas SQLite vs PostgreSQL · devuelve discrepancias."""
    sq = sqlite3.connect(sqlite_path)
    fallos = []
    for tabla, n_sqlite in resumen:
        with pg.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM "%s"' % tabla)
            n_pg = cur.fetchone()[0]
        if n_pg != n_sqlite:
            fallos.append((tabla, n_sqlite, n_pg))
    sq.close()
    return fallos


def main():
    ap = argparse.ArgumentParser(description="Migra EOS SQLite -> PostgreSQL")
    ap.add_argument("--sqlite", required=True,
                    help="ruta de la base SQLite origen")
    ap.add_argument("--esquema", action="store_true",
                    help="cargar el esquema PG primero (DROP SCHEMA · base nueva)")
    args = ap.parse_args()

    if not os.path.exists(args.sqlite):
        sys.exit(f"ERROR: no existe la base SQLite: {args.sqlite}")

    info = conninfo()
    print(f"Origen SQLite : {args.sqlite}")
    print(f"Destino PG    : {info.split('@')[-1] if '@' in info else info}")
    print()

    with psycopg.connect(info, autocommit=True) as pg:
        if args.esquema:
            print("Cargando esquema PostgreSQL...")
            cargar_esquema(pg)
            print()
        print("Copiando datos...")
        resumen, omitidas = copiar_datos(args.sqlite, pg)
        total = sum(n for _, n in resumen)
        print(f"  · {len(resumen)} tablas copiadas, {total} filas en total")
        # "relation does not exist" = tabla del SQLite que no es parte del
        # esquema EOS (backups manuales ad-hoc, tablas lazy) · es benigno.
        benignas = [(t, m) for t, m in omitidas if 'does not exist' in m]
        reales = [(t, m) for t, m in omitidas if 'does not exist' not in m]
        for tabla, _ in benignas:
            print(f"  · saltada {tabla} (no es del esquema EOS · backup/lazy)")
        for tabla, motivo in reales:
            print(f"  ! OMITIDA {tabla}: {motivo}")
        print()
        print("Verificando conteos...")
        fallos = verificar(args.sqlite, pg, resumen)
        if fallos or reales:
            for tabla, n_sq, n_pg in fallos:
                print(f"  ! {tabla}: SQLite={n_sq} PostgreSQL={n_pg}")
            sys.exit("MIGRACION CON ERRORES · revisar lo de arriba")
        print(f"  · OK · {len(resumen)} tablas verificadas")

    print()
    print("Migracion completa. Para el cutover, setear EOS_DB_BACKEND=postgres")
    print("(y DATABASE_URL) en el entorno de la app.")


if __name__ == "__main__":
    main()
