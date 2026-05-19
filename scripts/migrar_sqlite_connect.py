"""Migración Fase 3 · reemplaza los `sqlite3.connect(DB_PATH)` directos
por `db_connect()` (helper conmutable SQLite/Postgres de database.py).

Solo toca conexiones a la BD principal (DB_PATH) · deja intactas las
conexiones a archivos temporales de backup (tmp_db, tmp_path).

Uso:  python scripts/migrar_sqlite_connect.py
"""
import re

ARCHIVOS = [
    'api/auth.py',
    'api/blueprints/mfa.py',
    'api/blueprints/core.py',
    'api/blueprints/admin.py',
    'api/blueprints/auto_plan_jobs.py',
    'api/blueprints/inventario.py',
    'api/blueprints/programacion.py',
]

# sqlite3.connect(DB_PATH)  /  sqlite3.connect(DB_PATH, timeout=30)  -> db_connect(...)
RE_CONNECT = re.compile(r'sqlite3\.connect\(DB_PATH,?\s*')
RE_IMPORT_ANCHOR = re.compile(r'^from [\w.]+ import ', re.M)


def migrar(path):
    with open(path, encoding='utf-8') as f:
        src = f.read()
    nuevo, n = RE_CONNECT.subn('db_connect(', src)
    if n == 0:
        return path, 0, False
    importado = False
    if 'db_connect' not in re.sub(r'db_connect\(', '', nuevo):
        # No hay ningún uso de db_connect como import · lo agregamos.
        pass
    if not re.search(r'^from database import .*\bdb_connect\b', nuevo, re.M) \
            and not re.search(r'^\s*from database import db_connect$', nuevo, re.M):
        m = RE_IMPORT_ANCHOR.search(nuevo)
        if not m:
            raise SystemExit(f'{path}: no encontré ancla de import')
        fin_linea = nuevo.index('\n', m.start()) + 1
        nuevo = (nuevo[:fin_linea]
                 + 'from database import db_connect\n'
                 + nuevo[fin_linea:])
        importado = True
    with open(path, 'w', encoding='utf-8') as f:
        f.write(nuevo)
    return path, n, importado


def main():
    total = 0
    for path in ARCHIVOS:
        p, n, imp = migrar(path)
        total += n
        print(f'  {p}: {n} reemplazos{"  (+import)" if imp else ""}')
    print(f'OK · {total} sqlite3.connect(DB_PATH) -> db_connect()')


if __name__ == '__main__':
    main()
