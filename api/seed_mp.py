#!/usr/bin/env python3
"""
seed_mp.py -- Carga stock inicial de MPs en produccion.

Prerrequisito: stock_inicial_mp.sql debe estar en el repo (branch main).
Ejecutar en Render shell:
    python3 /opt/render/project/src/api/seed_mp.py

Uso local (para prueba):
    DB_PATH=/tmp/test.db python3 api/seed_mp.py
"""
import sqlite3
import urllib.request
import os
import sys

DB_PATH = os.environ.get('DB_PATH', '/var/data/inventario.db')
SQL_URL = ('https://raw.githubusercontent.com/'
           'sebastianvargasisaza-prog/Inventarios/main/stock_inicial_mp.sql')

print(f'DB    : {DB_PATH}')
print(f'SQL   : {SQL_URL}')

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
try:
    c.execute("SELECT COUNT(*) FROM movimientos WHERE observaciones LIKE 'Stock inicial%'")
    ya_cargados = c.fetchone()[0]
except Exception:
    ya_cargados = 0

if ya_cargados > 0:
    print(f'Ya existen {ya_cargados} movimientos de stock inicial -- abortando.')
    conn.close()
    sys.exit(0)

print('Descargando SQL...', end=' ', flush=True)
try:
    sql = urllib.request.urlopen(SQL_URL, timeout=30).read().decode('utf-8')
    print(f'OK ({len(sql):,} bytes)')
except Exception as e:
    print(f'Error al descargar: {e}')
    conn.close()
    sys.exit(1)

print('Ejecutando SQL...', end=' ', flush=True)
conn.executescript(sql)
conn.close()
print('OK')

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM maestro_mps')
total_mps = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM movimientos WHERE observaciones LIKE 'Stock inicial%'")
total_movs = c.fetchone()[0]
c.execute("SELECT SUM(cantidad) FROM movimientos WHERE observaciones LIKE 'Stock inicial%' AND tipo='Entrada'")
total_stock = c.fetchone()[0] or 0
conn.close()

print(f'Completado:')
print(f'   maestro_mps  : {total_mps} materiales')
print(f'   movimientos  : {total_movs} entradas de stock inicial')
print(f'   Stock total  : {total_stock:,.0f} g')
