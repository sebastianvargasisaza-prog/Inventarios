"""Análisis BF 2025 + plan próxima semana con capacidad 2/día.

Comparativa noviembre 2025 vs ventas normales 4m 2026.
Calcula multiplicador BF real por SKU.
"""
import csv
import sys
import io
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Cargar tres CSVs
def cargar_ventas(path):
    d = {}
    with open(path, 'r', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            sku = (r.get('SKU de variante de producto') or '').strip()
            if not sku: continue
            try: u = int(r.get('Articulos netos vendidos') or r.get('Artículos netos vendidos') or 0)
            except: u = 0
            d[sku] = u
    return d

ventas_4m = cargar_ventas(r'C:\Users\sebas\Downloads\Ventas totales por variante de producto - 2026-01-01 - 2026-04-30.csv')
ventas_bf = cargar_ventas(r'C:\Users\sebas\Downloads\Ventas totales por variante de producto - 2025-11-01 - 2025-12-02.csv')
ventas_hist = cargar_ventas(r'C:\Users\sebas\Downloads\Ventas totales por variante de producto - 2020-01-01 - 2026-04-30.csv')

DIAS_4M = 120
DIAS_BF = 32  # 1-nov a 2-dic = 32 días
DIAS_HIST = 2311

print('═' * 100)
print('BLACK FRIDAY 2025 vs Ventas normales — Multiplicador real por SKU')
print('═' * 100)
print()
print('{:13} {:>9} {:>9} {:>9} {:>9} {:>10}'.format(
    'SKU', 'Vel hist', 'Vel 4m', 'Vel BF', 'Mult BF', 'Pico-est'))
print('-' * 75)

# Calcular multiplicador BF real
# BF month tiene 32 días, ~14 días pico (lift) y ~18 días normales
# vel_bf_total = (14×vel_pico + 18×vel_4m) / 32
# Resolviendo: vel_pico = (vel_bf_total × 32 - 18 × vel_4m) / 14
filas = []
for sku in ventas_bf:
    if not sku: continue
    v_4m = ventas_4m.get(sku, 0) / DIAS_4M
    v_bf = ventas_bf.get(sku, 0) / DIAS_BF
    v_hist = ventas_hist.get(sku, 0) / DIAS_HIST
    if v_4m < 0.05: continue  # ignorar productos sin ventas reciente
    mult_bf_total = v_bf / v_4m if v_4m > 0 else None
    # Pico estimado durante 14 días BF
    if v_4m > 0:
        v_pico = (v_bf * DIAS_BF - 18 * v_4m) / 14
        mult_pico = v_pico / v_4m if v_4m > 0 else None
    else:
        mult_pico = None
    filas.append((sku, v_hist, v_4m, v_bf, mult_bf_total, mult_pico))

filas.sort(key=lambda x: -x[4] if x[4] else 0)
for sku, vh, v4, vbf, mbf, mp in filas[:25]:
    print('{:13} {:>7.2f}/d {:>7.2f}/d {:>7.2f}/d {:>7.2f}× {:>8.2f}×'.format(
        sku, vh, v4, vbf, mbf or 0, mp or 0))

print()
print('Mult BF = velocidad mes BF (32d) / velocidad normal 2026')
print('Pico-est = multiplicador estimado durante 14 días pico de BF')
print()
print('Promedio Mult BF mes:', round(sum(f[4] for f in filas if f[4])/len([f for f in filas if f[4]]), 2), '×')

# Top productos para preparar BF 2026
print('\n' + '═' * 80)
print('TOP 12 productos para PRE-STOCK BF 2026')
print('═' * 80)
print()
print('{:13} {:>9} {:>9} {:>10}'.format('SKU', 'Vel 4m', 'Vel BF est', 'Stock extra para 2sem'))
print('-' * 60)
for sku, vh, v4, vbf, mbf, mp in filas[:12]:
    # Stock extra para 2 semanas BF si mult pico es 2.5× promedio
    extra_2sem = (vbf - v4) * 14
    print('{:13} {:>7.2f}/d {:>7.2f}/d {:>10.0f} u'.format(sku, v4, vbf, extra_2sem))
