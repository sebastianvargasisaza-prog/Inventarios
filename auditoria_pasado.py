"""Auditoria producciones ULTIMAS 2 SEMANAS (16-abr a 30-abr-2026)."""
import json
import csv
import sys
import io
import re
from datetime import datetime, date, timedelta
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

path_cal = r'C:\Users\sebas\.claude\projects\C--Users-sebas-Downloads-Claude\12b2fa66-3fd8-42c3-92e8-f207033a2c72\tool-results\mcp-7b88b900-684e-430a-957b-b1f73cf9c2ae-list_events-1777591629367.txt'
with open(path_cal, 'r', encoding='utf-8') as f:
    cal = json.load(f).get('events', [])

# Inventario
inv = defaultdict(lambda: {'title': '', 'available': 0, 'on_hand': 0})
with open(r'C:\Users\sebas\Downloads\inventory_export_1 (10).csv', 'r', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        sku = (r.get('SKU') or '').strip()
        if not sku: continue
        try: a = int(r.get('Available (not editable)') or 0)
        except: a = 0
        try: oh = int(r.get('On hand (current)') or 0)
        except: oh = 0
        title = r.get('Title', '')
        v = (r.get('Option1 Value') or '').strip()
        if v: title += ' (' + v + ')'
        inv[sku]['title'] = title
        inv[sku]['available'] += a
        inv[sku]['on_hand'] += oh

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
INICIO_2SEM = date(2026, 4, 16)
NOMBRES_DIA = ['lun', 'mar', 'mie', 'jue', 'vie', 'sab', 'dom']

# Procesar eventos
eventos = []
for e in cal:
    f = (e.get('start') or {}).get('date') or (e.get('start') or {}).get('dateTime', '')[:10]
    if not f: continue
    try: fd = datetime.strptime(f[:10], '%Y-%m-%d').date()
    except: continue
    summary = e.get('summary', '') or ''
    desc = e.get('description', '') or ''
    # Parsear kg
    kg = None
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*kg', summary, re.IGNORECASE)
    if m:
        try: kg = float(m.group(1).replace(',', '.'))
        except: pass
    if kg is None:
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*kg', desc, re.IGNORECASE)
        if m:
            try: kg = float(m.group(1).replace(',', '.'))
            except: pass
    # Unidades
    u = None
    m2 = re.search(r'(\d+(?:[.,]\d+)?)\s*u\b', summary)
    if m2:
        try: u = int(float(m2.group(1).replace(',', '.')))
        except: pass
    if u is None:
        m2 = re.search(r'(\d[\d,]*)\s*u\b', desc)
        if m2:
            try: u = int(m2.group(1).replace(',', ''))
            except: pass
    es_hecho = 'hecho' in summary.lower() or 'hecho' in desc.lower() or '✅' in summary or '✅' in desc
    eventos.append({
        'fecha': fd,
        'summary': summary,
        'description': desc,
        'kg': kg,
        'unidades': u,
        'dia': fd.weekday(),
        'hecho': es_hecho,
    })

eventos.sort(key=lambda x: x['fecha'])

# Filtrar 2 semanas (16-abr a 30-abr inclusive)
ult2sem = [e for e in eventos if INICIO_2SEM <= e['fecha'] <= HOY]

print('=' * 78)
print('AUDITORIA PRODUCCIONES ULTIMAS 2 SEMANAS')
print('Periodo: ' + str(INICIO_2SEM) + ' a ' + str(HOY) + ' (15 dias)')
print('=' * 78)
print('\nTotal eventos en el periodo: ' + str(len(ult2sem)))

# Lista cronologica
print('\n[A] LISTADO CRONOLOGICO DETALLADO')
print('-' * 78)
print('{:12} {:5} {:8} {:8} {}'.format('Fecha', 'Dia', 'kg', 'unidad', 'Descripcion'))
print('-' * 78)
for e in ult2sem:
    kg_s = (str(e['kg']) + 'kg') if e['kg'] else '-'
    u_s = (str(e['unidades']) + 'u') if e['unidades'] else '-'
    marca = ' [HECHO]' if e['hecho'] else ' [PROG]'
    print('{:12} {:5} {:8} {:8} {}'.format(
        str(e['fecha']),
        NOMBRES_DIA[e['dia']],
        kg_s, u_s,
        e['summary'][:50] + marca,
    ))

# Por dia con count
print('\n[B] CARGA POR DIA (regla 1/dia Mayerlin)')
print('-' * 50)
por_fecha = defaultdict(list)
for e in ult2sem:
    por_fecha[e['fecha']].append(e)

f = INICIO_2SEM
while f <= HOY:
    dia_n = NOMBRES_DIA[f.weekday()]
    evs = por_fecha.get(f, [])
    sep = '⚠ SOBRECARGA' if len(evs) > 1 else 'OK' if evs else '(libre)'
    print(str(f) + ' ' + dia_n + ': ' + str(len(evs)) + ' producciones  ' + sep)
    for ev in evs:
        kg_s = (str(ev['kg']) + 'kg') if ev['kg'] else '-'
        print('    - ' + ev['summary'][:65] + ' (' + kg_s + ')')
    f += timedelta(days=1)

# Resumen kg producidos
print('\n[C] RESUMEN KG PRODUCIDOS (lo que efectivamente se fabrico)')
print('-' * 50)
total_kg = sum(e['kg'] for e in ult2sem if e['kg'])
total_u = sum(e['unidades'] for e in ult2sem if e['unidades'])
hechos = [e for e in ult2sem if e['hecho']]
print('  Total kg sumados (todas las producciones):  ' + ('%.1f' % total_kg) + ' kg')
print('  Total unidades teoricas:                    ' + str(total_u) + ' u')
print('  Marcadas explicitamente como HECHO:         ' + str(len(hechos)) + ' eventos')
print('  Total eventos en el periodo:                ' + str(len(ult2sem)))

# Cruce CRITICO: si TRIAC se hizo el 17-abr con 866u, por que stock hoy es -215?
print('\n[D] CRUCE LOTES vs STOCK ACTUAL (los puzzles)')
print('-' * 78)
SKU_KEYWORDS = {
    'SAH': ['SAH', 'AH 1.5', 'HIDRATANTE'],
    'TRIAC': ['TRIAC', 'TRIACTIVE', 'RETINOID 15'],
    'TRIAC30': ['TRIAC30', 'TRIACTIVE 30'],
    'NIA': ['NIA', 'NIACINAMIDA'],
    'TRX': ['TRX', 'ILUMINADOR TRX'],
    'CCAFE': ['CCAFE', 'CAFEINA'],
    'CMULP': ['CMULP', 'CONTORNO MULTI'],
    'CRETT': ['CRETT', 'CONTORNO RETINAL', 'RETINAL'],
    'SMULPP': ['SMULPP', 'MULTIPEPTIDOS'],
    'BHA33': ['BHA33', 'EXFOLIANTE BHA'],
    'LBHA': ['LBHA', 'LIMPIADOR BHA'],
    'LKJ': ['LKJ', 'KOJICO'],
    'LAH': ['LAH', 'LIMPIADOR HIDRATANTE'],
    'GELH': ['GELH', 'GEL HIDRATANTE'],
    'EMLIM': ['EMLIM', 'EMULSION LIMPIA'],
    'HKJ': ['HKJ', 'EMULSION ILUMI'],
    'AZHC': ['AZHC', 'AZ HYBRID'],
    'NPHA30': ['NPHA30', 'NOVA-PHA'],
    'GLOSSN': ['GLOSSN', 'TRANSLUCIDO'],
    'GLOSSMERLOT': ['GLOSSMERLOT', 'MERLOT'],
    'GLOSSMALVA': ['GLOSSMALVA', 'MALVA'],
    'GLOSSPEACH': ['GLOSSPEACH', 'PEACH'],
}

def match_sku(s, d):
    text = (s + ' ' + d).upper()
    for sku, keys in SKU_KEYWORDS.items():
        for k in keys:
            if k.upper() in text:
                return sku
    return None

print('{:14} {:>10} {:>9} {:>10} {:>9} {:>9} {:>10}'.format(
    'SKU', 'kg lote', 'u teor', 'Stock hoy', 'Vendido', 'Esperado', 'Diff'))
print('-' * 78)
for e in ult2sem:
    sku = match_sku(e['summary'], e['description'])
    if not sku: continue
    if not e['unidades']: continue
    stock_hoy = inv[sku]['available']
    vel = ventas.get(sku, 0) / DIAS_VENTAS if ventas.get(sku) else 0
    dias_desde = (HOY - e['fecha']).days
    vendido_periodo = round(vel * dias_desde)
    esperado = e['unidades'] - vendido_periodo
    diff = stock_hoy - esperado
    flag = ''
    if abs(diff) > 50:
        flag = ' [discrepancia]'
    print('{:14} {:>9.1f}kg {:>9}u {:>9}u {:>9}u {:>9}u {:>10}{}'.format(
        sku, e['kg'] or 0, e['unidades'], stock_hoy, vendido_periodo, esperado, diff, flag))

# E) Que toco hacerse pero NO se hizo
print('\n[E] LO QUE DEBIA PRODUCIRSE EN ESTAS 2 SEMANAS (segun stock+ventas)')
print('-' * 78)
print('Para cada SKU con alcance < 25d HOY: sumando 2sem atras + alcance hoy,')
print('inferimos si quedo descubierto en abril.')
print('-' * 78)

# Mas simple: que SKUs aparecen en URGENTE pero no aparecen producidos en estas 2sem
SKUS_EN_2SEM = set(match_sku(e['summary'], e['description']) for e in ult2sem)
SKUS_EN_2SEM.discard(None)
print('\nSKUs CON LOTE en estas 2 semanas: ' + str(sorted(SKUS_EN_2SEM)))

print('\nSKUs URGENTES HOY que NO se produjeron en estas 2 semanas:')
print('{:14} {:>9} {:>9} {:>9}'.format('SKU', 'Stock', 'Vel/d', 'Alcance'))
for sku in inv:
    a = inv[sku]['available']
    v = ventas.get(sku, 0)
    if v == 0 or a < -50: continue
    vel = v / DIAS_VENTAS
    if vel < 0.05: continue
    dias = a / vel
    if dias < 25 and sku not in SKUS_EN_2SEM:
        print('{:14} {:>9} {:>9.2f} {:>8.1f}d'.format(sku, a, vel, dias))
