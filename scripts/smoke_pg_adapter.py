"""Smoke test del adaptador PostgreSQL (Fase 1 de la migración).

Prueba api/pg_adapter.py contra un PostgreSQL real. Requiere el Postgres
local corriendo en 127.0.0.1:5432 con la base `eos_test`.

Se corre a mano:  python scripts/smoke_pg_adapter.py
NO es parte de los golden paths (esos siguen sobre SQLite hasta el cutover).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from pg_adapter import connect

CONNINFO = "host=127.0.0.1 port=5432 user=postgres dbname=eos_test"


def main():
    conn = connect(CONNINFO)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS _smoke_id")
    c.execute("DROP TABLE IF EXISTS _smoke_nat")
    conn.commit()
    fallos = []

    # 1. Tabla con id SERIAL · INSERT con `?` · lastrowid
    c.execute("CREATE TABLE _smoke_id (id SERIAL PRIMARY KEY, nombre TEXT, cant INTEGER)")
    conn.commit()
    c.execute("INSERT INTO _smoke_id (nombre, cant) VALUES (?, ?)", ("Suero 100%", 5))
    if c.lastrowid != 1:
        fallos.append(f"lastrowid 1ra fila: esperado 1, got {c.lastrowid}")
    c.execute("INSERT INTO _smoke_id (nombre, cant) VALUES (?, ?)", ("Crema", 9))
    if c.lastrowid != 2:
        fallos.append(f"lastrowid 2da fila: esperado 2, got {c.lastrowid}")
    conn.commit()

    # 2. SELECT · acceso por índice Y por nombre · dict(row)
    c.execute("SELECT id, nombre, cant FROM _smoke_id WHERE id=?", (1,))
    row = c.fetchone()
    if row[0] != 1 or row['nombre'] != "Suero 100%" or row[2] != 5:
        fallos.append(f"acceso fila mal: idx0={row[0]} nombre={row['nombre']} idx2={row[2]}")
    if dict(row) != {"id": 1, "nombre": "Suero 100%", "cant": 5}:
        fallos.append(f"dict(row) mal: {dict(row)}")

    # 3. LIKE con `%` literal (como lo escribe el código de EOS)
    c.execute("SELECT nombre FROM _smoke_id WHERE nombre LIKE '%100%'")
    encontrados = [r[0] for r in c.fetchall()]
    if encontrados != ["Suero 100%"]:
        fallos.append(f"LIKE con % mal: {encontrados}")

    # 4. Tabla con PK natural (sin id) · INSERT NO debe romper · lastrowid None
    c.execute("CREATE TABLE _smoke_nat (codigo TEXT PRIMARY KEY, val INTEGER)")
    conn.commit()
    c.execute("INSERT INTO _smoke_nat (codigo, val) VALUES (?, ?)", ("MP-1", 7))
    if c.lastrowid is not None:
        fallos.append(f"lastrowid en tabla sin id deberia ser None, got {c.lastrowid}")
    conn.commit()
    c.execute("SELECT val FROM _smoke_nat WHERE codigo=?", ("MP-1",))
    got = c.fetchone()
    if not got or got[0] != 7:
        fallos.append("INSERT en tabla con PK natural no persistio")

    # 5. rowcount tras UPDATE
    c.execute("UPDATE _smoke_id SET cant=? WHERE id=?", (99, 1))
    if c.rowcount != 1:
        fallos.append(f"rowcount esperado 1, got {c.rowcount}")
    conn.commit()

    # 6. executemany
    c.executemany("INSERT INTO _smoke_nat (codigo, val) VALUES (?, ?)",
                  [("MP-2", 1), ("MP-3", 2)])
    conn.commit()
    c.execute("SELECT COUNT(*) FROM _smoke_nat")
    if c.fetchone()[0] != 3:
        fallos.append("executemany no inserto las 2 filas")

    # 7. rollback
    c.execute("INSERT INTO _smoke_nat (codigo, val) VALUES (?, ?)", ("MP-X", 0))
    conn.rollback()
    c.execute("SELECT COUNT(*) FROM _smoke_nat WHERE codigo=?", ("MP-X",))
    if c.fetchone()[0] != 0:
        fallos.append("rollback no revirtio el INSERT")

    # limpieza
    c.execute("DROP TABLE _smoke_id")
    c.execute("DROP TABLE _smoke_nat")
    conn.commit()
    conn.close()

    if fallos:
        print("SMOKE PG ADAPTER · FALLOS:")
        for f in fallos:
            print("  -", f)
        sys.exit(1)
    print("SMOKE PG ADAPTER · OK · 7/7 chequeos pasaron")


if __name__ == "__main__":
    main()
