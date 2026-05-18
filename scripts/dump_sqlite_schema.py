"""Fase 2 migracion PG · genera el esquema SQLite de ESTADO FINAL.

En vez de traducir las 134 migraciones una por una, corre init_db() sobre
una base SQLite fresca (que aplica todos los CREATE TABLE + las 134
migraciones + los ALTER legacy) y vuelca el esquema resultante. Ese volcado
es el punto de partida para traducir a PostgreSQL de una sola vez.

Uso:  python scripts/dump_sqlite_schema.py
Salida:  C:/Users/sebas/pgdev/sqlite_schema_actual.sql
"""
import os
import sys
import sqlite3
import tempfile

_TMP = os.path.join(tempfile.gettempdir(), 'eos_schema_dump.db')
for ext in ('', '-wal', '-shm', '-journal'):
    p = _TMP + ext
    if os.path.exists(p):
        os.remove(p)

os.environ['DB_PATH'] = _TMP
os.environ.setdefault('SECRET_KEY', 'dump-schema-only')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

import database  # noqa: E402

print('Corriendo init_db() sobre base SQLite fresca...')
database.init_db()

conn = sqlite3.connect(_TMP)
rows = conn.execute(
    "SELECT type, name, sql FROM sqlite_master "
    "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
    "ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 "
    "         WHEN 'trigger' THEN 2 ELSE 3 END, name"
).fetchall()
conn.close()

n_tabla = sum(1 for r in rows if r[0] == 'table')
n_index = sum(1 for r in rows if r[0] == 'index')
n_trig = sum(1 for r in rows if r[0] == 'trigger')

out = 'C:/Users/sebas/pgdev/sqlite_schema_actual.sql'
with open(out, 'w', encoding='utf-8') as f:
    f.write(f"-- Esquema SQLite estado-final de EOS\n")
    f.write(f"-- {n_tabla} tablas, {n_index} indices, {n_trig} triggers\n\n")
    for t, n, sql in rows:
        f.write(f"-- [{t}] {n}\n{sql};\n\n")

print(f"OK · {n_tabla} tablas, {n_index} indices, {n_trig} triggers")
print(f"Volcado -> {out}")
