#!/usr/bin/env python3
"""
seed_mee.py — Carga stock inicial de MEE en producción.

Prerrequisito: stock_inicial_mee.sql debe estar en el repo (branch main).
Ejecutar en Render shell:
    wget -q -O /tmp/seed_mee.py https://raw.githubusercontent.com/sebastianvargasisaza-prog/Inventarios/main/api/seed_mee.py
    python3 /tmp/seed_mee.py

Uso local (para prueba):
    DB_PATH=/tmp/test.db python3 api/seed_mee.py
"""
import sqlite3
import urllib.request
import os
import sys

DB_PATH = os.environ.get('DB_PATH', '/var/data/inventario.db')
SQL_URL = ('https://raw.githubusercontent.com/'
           'sebastianvargasisaza-prog/Inventarios/main/stock_inicial_mee.sql')

print(f"DB    : {DB_PATH}")
print(f"SQL   : {SQL_URL}")

# Verificar estado actual de maestro_mee
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
try:
    c.execute("SELECT COUNT(*) FROM maestro_mee")
    ya_existentes = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM maestro_mee WHERE stock_actual = 2000 OR fecha_creacion IS NULL OR fecha_creacion = ''")
    placeholders = c.fetchone()[0]
except Exception as e:
    print(f"Error al consultar maestro_mee: {e}")
    ya_existentes = 0
    placeholders  = 0

print(f"\nEstado actual de maestro_mee:")
print(f"  Registros totales      : {ya_existentes}")
print(f"  Registros placeholder  : {placeholders}")

if ya_existentes > 0 and placeholders == 0:
    print(f"\nYa existen {ya_existentes} registros con datos reales.")
    print("   Si quieres re-ejecutar, borra primero:")
    print("   DELETE FROM maestro_mee;")
    conn.close()
    sys.exit(0)

if ya_existentes > 0:
    print(f"   Detectados {placeholders} placeholders, se procede con INSERT OR REPLACE")

# Descargar y ejecutar SQL
print("\nDescargando SQL...", end=' ', flush=True)
try:
    sql = urllib.request.urlopen(SQL_URL, timeout=30).read().decode('utf-8')
    print(f"OK ({len(sql):,} bytes)")
except Exception as e:
    print(f"\nError al descargar: {e}")
    print("El archivo stock_inicial_mee.sql debe estar en el repo (branch main)")
    conn.close()
    sys.exit(1)

print("Ejecutando SQL...", end=' ', flush=True)
conn.executescript(sql)
conn.close()
print("OK")

# Verificacion
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM maestro_mee")
total_mee = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM maestro_mee WHERE stock_actual < stock_minimo AND stock_minimo > 0")
bajo_minimo = c.fetchone()[0]

c.execute("SELECT categoria, COUNT(*) c FROM maestro_mee GROUP BY categoria ORDER BY c DESC")
por_categoria = c.fetchall()

c.execute("SELECT SUM(stock_actual) FROM maestro_mee")
stock_total = c.fetchone()[0] or 0

conn.close()

print(f"\nCompletado exitosamente:")
print(f"   maestro_mee total    : {total_mee} materiales")
print(f"   Bajo minimo          : {bajo_minimo} materiales")
print(f"   Stock total          : {stock_total:,.0f} unidades")
print(f"\n   Por categoria:")
for cat, cnt in por_categoria:
    print(f"     {cat:<20} : {cnt}")
