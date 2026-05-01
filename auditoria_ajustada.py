"""Auditoria ajustada: con pipeline 7d + correcciones LBHA/GELH/HKJ."""
import csv
import sys
import io
from datetime import date, timedelta
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Inventario Shopify (Available)
inv = defaultdict(lambda: {'title': '', 'available': 0})
with open(r'C:\Users\sebas\Downloads\inventory_export_1 (10).csv', 'r', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        sku = (r.get('SKU') or '').strip()
        if not sku: continue
        try: a = int(r.get('Available (not editable)') or 0)
        except: a = 0
        title = r.get('Title', '')
        v = (r.get('Option1 Value') or '').strip()
        if v: title += ' (' + v + ')'
        inv[sku]['title'] = title
        inv[sku]['available'] += a

# Ventas
ventas = {}
with open(r'C:\Users\sebas\Downloads\Ventas totales por variante de producto - 2026-01-01 - 2026-04-30.csv', 'r', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        sku = (r.get('SKU de variante de producto') or '').strip()
        if not sku: continue
        try: u = int(r.get('Articulos netos vendidos') or r.get('Artículos netos vendidos') or 0)
        except: u = 0
        ventas[sku] = u

DIAS_VENTAS = 120
HOY = date(2026, 4, 30)
PIPELINE_DIAS = 7

# Pipeline: producciones de los ultimos 7 dias que aun NO entraron a Shopify
# Usuario confirmo:
#   - LBHA 28-abr: 150 kg (Calendar decia 200) -> -50 kg
#   - GELH 29-abr: 20 kg (Calendar decia 50)   -> -30 kg
#   - HKJ 30-abr: 0 kg (NO se hizo)
#   - SAH 30-abr: 90 kg (Calendar OK)
#   - GLOSSN 28-abr: 5 kg (Calendar OK)
#   - NPHA 23-abr: 12 kg (Calendar OK) -- 7 dias justo, podria estar entrando hoy
#   - CRETT 23-abr: 9 kg (Calendar OK)
# Producciones HECHO (dentro de 7d) que ya estan en pipeline:
#   - TRIAC 17-abr ya pasaron 13d, deberia estar en Shopify (no esta -> problema)
#   - GLOSSMERLOT 20-abr, 10d, deberia estar
#   - GLOSSMALVA 20-abr, 10d, deberia estar
#   - EMLIM 22-abr, 8d, justo entrando
#   - CMULP 22-abr, 8d, justo entrando

# Factores g/u por SKU (estimados)
FACTOR_G = {
    'SAH': 30, 'SAH10': 10,
    'TRIAC': 15, 'TRIAC30': 30,
    'NIA': 30, 'NIA10': 10,
    'TRX': 30, 'TRX10': 10,
    'CCAFE': 12, 'CMULP': 15, 'CRETT': 12,
    'SMULPP': 30,
    'BHA33': 30,
    'LBHA': 150, 'LAH': 150, 'LKJ': 150, 'EMLIM': 150,
    'GELH': 40,
    'CRB3BHA': 50, 'HKJ': 50,
    'AZHC': 15, 'AZHC30': 30,
    'NPHA30': 30, 'NPHA10': 10,
    'SVITC33': 30, 'SVITC3315': 15,
    'RECN-2': 30,
    'MAXLASH': 4.5,
    'GLOSSN': 10, 'GLOSSMERLOT': 10, 'GLOSSMALVA': 10, 'GLOSSPEACH': 10,
    'CRCUREA': 100,
    'ECENT': 30, 'EILU': 30,
}

# Producciones efectivas en pipeline (ultimos 7 dias)
# Lista (fecha, sku, kg, unidades)
PIPELINE = [
    # Confirmado por Sebastian
    (date(2026, 4, 30), 'SAH',  90,  None),  # 90 kg total para SAH+SAH10 (suma de ambas presentaciones)
    (date(2026, 4, 29), 'GELH', 20,  None),  # corregido: 20 kg (no 50)
    (date(2026, 4, 28), 'LBHA', 150, None),  # corregido: 150 kg (no 200)
    (date(2026, 4, 28), 'GLOSSN', 5, 500),
    (date(2026, 4, 23), 'NPHA30', 12, 181),
    (date(2026, 4, 23), 'CRETT', 9, None),
    # Producciones de >7d pero que parecen no haber entrado a Shopify (dudoso)
    # Las dejamos fuera del pipeline porque deberian estar reflejadas ya
]

def kg_a_unidades(sku, kg):
    fg = FACTOR_G.get(sku, 30)
    return int(kg * 1000 / fg)

# Calcular pipeline por SKU
pipeline_por_sku = defaultdict(int)
for fecha, sku, kg, u in PIPELINE:
    if (HOY - fecha).days > PIPELINE_DIAS:
        continue  # ya deberia estar en stock
    if u:
        pipeline_por_sku[sku] += u
    elif kg:
        pipeline_por_sku[sku] += kg_a_unidades(sku, kg)

# SAH especial: el lote 90kg de hoy se reparte SAH (30ml) + SAH10 (10ml). Dividir 50/50 segun Sebastian
sah_pipe = pipeline_por_sku.pop('SAH', 0)
if sah_pipe:
    pipeline_por_sku['SAH'] += int(sah_pipe * 0.6)  # asumimos 60% va a SAH 30ml (mas vendido)
    pipeline_por_sku['SAH10'] += int(sah_pipe * 0.4)

print('=' * 78)
print('AUDITORIA AJUSTADA — con pipeline 7d + correcciones reales')
print('Hoy: ' + str(HOY))
print('=' * 78)

print('\n[A] PIPELINE EFECTIVO (lotes hechos no entregados, < 7 dias)')
print('-' * 78)
print('{:14} {:>10} {:>5}'.format('SKU', 'Pipeline u', 'Edad'))
print('-' * 78)
for fecha, sku, kg, u in PIPELINE:
    edad = (HOY - fecha).days
    if edad > PIPELINE_DIAS:
        marca = ' (>7d, deberia estar en Shopify)'
    else:
        marca = ''
    u_calc = u if u else kg_a_unidades(sku, kg)
    print('{:14} {:>10} {:>4}d  {} {}kg{}'.format(sku, u_calc, edad, str(fecha), kg, marca))

print('\n[B] STOCK EFECTIVO = Shopify Available + Pipeline')
print('-' * 78)
print('{:14} {:>9} {:>9} {:>9} {:>9} {:>9} {:>10}'.format(
    'SKU', 'Shopify', 'Pipeline', 'Efectivo', 'Vel/d', 'Alcance', 'Estado'))
print('-' * 78)

def estado(d):
    if d is None: return '—'
    if d < 0: return 'STOCKOUT'
    if d < 20: return 'URGENTE'
    if d < 40: return 'PRONTO'
    if d < 80: return 'OK'
    return 'SOBRA'

skus_relevantes = [sku for sku in inv if ventas.get(sku, 0) > 0]
items = []
for sku in skus_relevantes:
    a = inv[sku]['available']
    p = pipeline_por_sku.get(sku, 0)
    efectivo = a + p
    v = ventas.get(sku, 0)
    vel = v / DIAS_VENTAS
    if vel < 0.05:
        items.append((sku, a, p, efectivo, vel, None))
    else:
        items.append((sku, a, p, efectivo, vel, efectivo / vel))

items.sort(key=lambda x: (x[5] is None, x[5] if x[5] is not None else 9999))

for sku, a, p, ef, vel, dias in items[:35]:
    dias_str = '—' if dias is None else ('%.1f' % dias) + 'd'
    pipe_str = ('+' + str(p)) if p > 0 else '0'
    print('{:14} {:>9} {:>9} {:>9} {:>9.2f} {:>8} {:>10}'.format(sku, a, pipe_str, ef, vel, dias_str, estado(dias)))

# Producciones >7d que SÍ deberian estar en Shopify pero no estan
print('\n[C] PRODUCCIONES VIEJAS (>7d) QUE NO APARECEN EN SHOPIFY (problema sync?)')
print('-' * 78)
PROD_VIEJAS = [
    (date(2026, 4, 17), 'TRIAC', 13, 866),
    (date(2026, 4, 20), 'GLOSSMERLOT', 1.2, 120),
    (date(2026, 4, 20), 'GLOSSMALVA', 1.2, 120),
    (date(2026, 4, 22), 'EMLIM', 20, 133),
    (date(2026, 4, 22), 'CMULP', 9, 600),
]
for fecha, sku, kg, u in PROD_VIEJAS:
    edad = (HOY - fecha).days
    a_hoy = inv[sku]['available']
    v = ventas.get(sku, 0) / DIAS_VENTAS
    vendido_post = round(v * edad)
    esperado_hoy = u - vendido_post
    print('{:14} hecho {} ({}d) lote {}u  esperado_hoy ~{}u  real {}u  diff {}'.format(
        sku, str(fecha), edad, u, esperado_hoy, a_hoy, a_hoy - esperado_hoy))
