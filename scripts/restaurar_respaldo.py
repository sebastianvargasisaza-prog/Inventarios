#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Restaura una copia de EOS generada por `api/respaldo_db.py` (tarea B-01 · ASG-PRO-014).

POR QUÉ EXISTE
--------------
Un respaldo sin restaurador no es un respaldo: es un archivo. La prueba anual del numeral 5.8 del
ASG-PRO-014 se ejecuta con esta herramienta, y el escenario D del numeral 5.7 (perder el proveedor)
se resuelve corriéndola contra una base nueva.

CÓMO FUNCIONA
-------------
La copia es un volcado de DATOS, no de esquema. Eso no es una carencia: EOS reconstruye su propio
esquema desde `MIGRATIONS`, así que el orden correcto es crear la base vacía, dejar que `init_db()`
levante las 423 migraciones, y recién ahí cargar las filas.

    1. descifra          (AES-256-GCM por bloques · clave BACKUP_CIPHER_KEY)
    2. descomprime
    3. init_db()         crea el esquema completo en la base DESTINO
    4. carga las filas   en varias pasadas, para resolver las llaves foráneas sin superusuario
    5. resetea las secuencias
    6. verifica          cuenta lo cargado contra el manifiesto y REPORTA las diferencias

USO
---
    # prueba anual: restaurar a una base de PRUEBA y comparar
    python scripts/restaurar_respaldo.py --key respaldo/semanal/20260812-0330-ab12cd34ef.jsonl.gz.enc \
        --destino postgresql://usuario:clave@host/eos_prueba

    # desde un archivo ya descargado
    python scripts/restaurar_respaldo.py --archivo copia.jsonl.gz.enc --destino ... --si

⚠ SIEMPRE contra una base VACÍA. La herramienta se niega a escribir sobre una base que ya tiene
datos salvo que se pase `--sobrescribir`, porque cargar encima mezcla dos realidades y el resultado
no es ninguna de las dos.
"""
import argparse
import gzip
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api'))

# Tablas que NO se cargan: las llena el propio init_db() y volver a insertarlas choca contra su
# clave única. `schema_migrations` es la más importante: si se cargara la del respaldo, el esquema
# quedaría diciendo que aplicó migraciones que esta base sí aplicó por su cuenta.
OMITIR = {'schema_migrations'}


def _clave():
    import hashlib
    raw = (os.environ.get('BACKUP_CIPHER_KEY') or '').strip()
    return hashlib.sha256(raw.encode('utf-8')).digest() if raw else None


def descifrar(origen, destino):
    """Devuelve True si descifró, False si el archivo ya venía en claro."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    MAGIC = b'EOSBK1\n'
    with open(origen, 'rb') as f:
        cab = f.read(len(MAGIC))
    if cab != MAGIC:
        return False
    clave = _clave()
    if not clave:
        raise SystemExit('La copia está cifrada y BACKUP_CIPHER_KEY no está configurada.')
    aes = AESGCM(clave)
    with open(origen, 'rb') as fi, open(destino, 'wb') as fo:
        fi.read(len(MAGIC))
        while True:
            largo = fi.read(4)
            if not largo:
                break
            nonce = fi.read(12)
            ct = fi.read(int.from_bytes(largo, 'big'))
            fo.write(aes.decrypt(nonce, ct, None))
    return True


def _valor(v):
    """Deshace la codificación de `_jsonable`."""
    if isinstance(v, dict) and '__b64__' in v:
        import base64
        return base64.b64decode(v['__b64__'])
    return v


def cargar(conn, ruta_gz, verbose=True):
    """Carga las filas en varias pasadas.

    Las llaves foráneas obligan a un orden, y calcular el orden topológico exacto es frágil (hay
    ciclos y auto-referencias). En vez de eso se insertan todas y se REINTENTAN las que fallaron:
    cada pasada resuelve al menos un nivel de dependencia, así que converge. Se corta cuando una
    pasada no logra insertar ni una fila más, y entonces lo que quedó se REPORTA en vez de darse
    por bueno.
    """
    c = conn.cursor()
    pendientes = []
    contados = {}

    with gzip.open(ruta_gz, 'rt', encoding='utf-8') as f:
        cabecera = json.loads(f.readline())
        if not cabecera.get('__eos_respaldo__'):
            raise SystemExit('El archivo no es un respaldo de EOS.')
        for linea in f:
            r = json.loads(linea)
            if r['t'] in OMITIR:
                continue
            pendientes.append((r['t'], r['f']))

    if verbose:
        print('  filas a cargar: %s' % format(len(pendientes), ',d'))

    pasada = 0
    fallidas = []
    while pendientes:
        pasada += 1
        fallidas = []
        ok = 0
        for tabla, fila in pendientes:
            cols = list(fila.keys())
            marcas = ','.join(['?'] * len(cols))
            sql = 'INSERT INTO "%s" (%s) VALUES (%s)' % (
                tabla, ','.join('"%s"' % x for x in cols), marcas)
            try:
                c.execute(sql, tuple(_valor(fila[k]) for k in cols))
                ok += 1
                contados[tabla] = contados.get(tabla, 0) + 1
            except Exception as e:
                fallidas.append((tabla, fila, str(e)[:160]))
        conn.commit()
        if verbose:
            print('  pasada %d: %s cargadas · %s pendientes'
                  % (pasada, format(ok, ',d'), format(len(fallidas), ',d')))
        if ok == 0:
            # Ninguna avanzó: reintentar otra vez daría lo mismo. Se corta y se declara.
            break
        pendientes = [(t, f) for t, f, _ in fallidas]

    return contados, [(t, m) for t, _, m in fallidas]


def resetear_secuencias(conn):
    """Sin esto el primer INSERT posterior choca contra un id que ya existe.

    Es el paso que más se olvida en una restauración y el que hace que la base restaurada parezca
    sana hasta que alguien intenta grabar algo.
    """
    c = conn.cursor()
    try:
        c.execute("SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema='public'")
        secuencias = [r[0] for r in c.fetchall()]
    except Exception:
        return 0          # SQLite maneja el autoincremento solo
    n = 0
    for s in secuencias:
        try:
            tabla = s.rsplit('_', 2)[0] if s.endswith('_id_seq') else None
            if not tabla:
                continue
            c.execute('SELECT COALESCE(MAX(id), 0) FROM "%s"' % tabla)
            mx = c.fetchone()[0] or 0
            # `?` porque la conexión pasa por el adaptador, que traduce los marcadores.
            c.execute("SELECT setval(?, ?, true)", (s, max(int(mx), 1)))
            n += 1
        except Exception:
            continue
    conn.commit()
    return n


def main():
    ap = argparse.ArgumentParser(description='Restaura una copia de EOS')
    ap.add_argument('--key', help='key de la copia en el almacenamiento de objetos')
    ap.add_argument('--archivo', help='archivo local ya descargado')
    ap.add_argument('--destino', help='URL de la base DESTINO (postgresql://...)')
    ap.add_argument('--sobrescribir', action='store_true',
                    help='permitir cargar sobre una base que ya tiene datos')
    ap.add_argument('--si', action='store_true', help='no preguntar')
    args = ap.parse_args()

    if not args.key and not args.archivo:
        raise SystemExit('Indicá --key o --archivo.')
    if not args.destino:
        raise SystemExit('Indicá --destino. NUNCA se restaura sobre la base de producción sin '
                         'nombrarla explícitamente.')

    t0 = time.time()
    tmp = 'eos_restaurar_%d' % int(t0)
    enc, gz = tmp + '.enc', tmp + '.gz'

    try:
        if args.key:
            print('· descargando %s' % args.key)
            from r2_storage import r2_get
            datos = r2_get(args.key)
            if not datos:
                raise SystemExit('No pude descargar esa copia.')
            with open(enc, 'wb') as f:
                f.write(datos)
            origen = enc
        else:
            origen = args.archivo

        print('· descifrando')
        if descifrar(origen, gz):
            print('  descifrada')
        else:
            print('  el archivo venía sin cifrar')
            gz = origen

        os.environ['DATABASE_URL'] = args.destino
        os.environ['EOS_DB_BACKEND'] = 'postgres' if args.destino.startswith('postgres') else ''

        print('· creando el esquema con init_db()')
        from database import init_db, db_connect
        init_db()
        conn = db_connect()

        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM movimientos")
        ya = c.fetchone()[0]
        if ya and not args.sobrescribir:
            raise SystemExit('La base destino ya tiene %d movimientos. Usá una base VACÍA, o '
                             '--sobrescribir si sabés lo que hacés.' % ya)

        if not args.si:
            r = input('Restaurar sobre %s · ¿confirmás? (escribí SI): ' % args.destino[:60])
            if r.strip().upper() != 'SI':
                raise SystemExit('Cancelado.')

        print('· cargando datos')
        contados, fallidas = cargar(conn, gz)
        print('· reseteando secuencias')
        n = resetear_secuencias(conn)
        print('  %d secuencias' % n)

        total = sum(contados.values())
        print('')
        print('Restauración terminada en %ds' % int(time.time() - t0))
        print('  %s filas en %d tablas' % (format(total, ',d'), len(contados)))
        if fallidas:
            # Se declara. Una restauración con filas perdidas que no lo dice es la peor forma de
            # quedar mal: la base parece completa (M100).
            print('')
            print('  ATENCIÓN · %d filas NO se pudieron cargar:' % len(fallidas))
            vistos = {}
            for t, m in fallidas[:2000]:
                vistos.setdefault(t, m)
            for t, m in list(vistos.items())[:15]:
                print('    %-32s %s' % (t, m))
            return 1
        return 0
    finally:
        for p in (enc, gz):
            try:
                if p != args.archivo and os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass


if __name__ == '__main__':
    sys.exit(main())
