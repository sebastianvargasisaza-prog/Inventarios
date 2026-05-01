"""Auditoria Calendar Producciones vs realidad Shopify."""
import json
import csv
import sys
import io
import re
from datetime import datetime, date
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 1) Calendar
path_cal = r'C:\Users\sebas\.claude\projects\C--Users-sebas-Downloads-Claude\12b2fa66-3fd8-42c3-92e8-f207033a2c72\tool-results\mcp-7b88b900-684e-430a-957b-b1f73cf9c2ae-list_events-1777591629367.txt'
with open(path_cal, 'r', encoding='utf-8') as f:
    cal = json.load(f).get('events', [])

# 2) Inventario
inv = defaultdict(lambda: {'title': '', 'available': 0})
with open(r'C:\Users\sebas\Downloads\inventory_export_1 (10).csv', 'r', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        sku = (r.get('SKU') or '').strip()
        if not sku:
            continue
        try:
            a = int(r.get('Available (not editable)') or 0)
        except Exception:
            a = 0
        title = r.get('Title', '')
        v = (r.get('Option1 Value') or '').strip()
        if v:
            title += ' (' + v + ')'
        inv[sku]['title'] = title
        inv[sku]['available'] += a

# 3) Ventas 120d
ventas = {}
with open(r'C:\Users\sebas\Downloads\Ventas totales por variante de producto - 2026-01-01 - 2026-04-30.csv', 'r', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        sku = (r.get('SKU de variante de producto') or '').strip()
        if not sku:
            continue
        try:
            u = int(r.get('Articulos netos vendidos') or r.get('Artículos netos vendidos') or 0)
        except Exception:
            u = 0
        ventas[sku] = u

DIAS_VENTAS = 120
HOY = date(2026, 4, 30)
NOMBRES_DIA = ['lun', 'mar', 'mie', 'jue', 'vie', 'sab', 'dom']

# Procesar Calendar
eventos = []
for e in cal:
    f = (e.get('start') or {}).get('date') or (e.get('start') or {}).get('dateTime', '')[:10]
    if not f:
        continue
    try:
        fd = datetime.strptime(f[:10], '%Y-%m-%d').date()
    except Exception:
        continue
    summary = e.get('summary', '') or ''
    desc = e.get('description', '') or ''
    kg = None
    for pat in [r'(\d+(?:[.,]\d+)?)\s*kg', r'~\s*(\d+(?:[.,]\d+)?)\s*kg']:
        m = re.search(pat, summary, re.IGNORECASE)
        if m:
            try:
                kg = float(m.group(1).replace(',', '.'))
                break
            except Exception:
                pass
    eventos.append({'fecha': fd, 'summary': summary, 'description': desc, 'kg': kg, 'dia': fd.weekday()})

eventos.sort(key=lambda x: x['fecha'])

print('=' * 78)
print('AUDITORIA CALENDAR vs REALIDAD (Stock + Ventas Shopify)')
print('Hoy: ' + str(HOY) + '  ·  Total eventos Calendar: ' + str(len(eventos)))
print('=' * 78)

# A) Resumen por mes
print('\n[A] EVENTOS POR MES')
print('-' * 40)
por_mes = defaultdict(int)
for e in eventos:
    por_mes[e['fecha'].strftime('%Y-%m')] += 1
for k, v in sorted(por_mes.items()):
    pasado = ' (pasado)' if k < HOY.strftime('%Y-%m') else ''
    print('  ' + k + ': ' + str(v) + ' eventos' + pasado)

# B) Días no laborales
print('\n[B] EVENTOS EN FIN DE SEMANA (regla: solo L-V)')
print('-' * 40)
fines = [e for e in eventos if e['dia'] >= 5]
if not fines:
    print('  OK Ninguno')
else:
    for e in fines[:10]:
        print('  ' + str(e['fecha']) + ' (' + NOMBRES_DIA[e['dia']] + ') ' + e['summary'][:60])

# C) Días con 2+ producciones
print('\n[C] DIAS CON 2+ PRODUCCIONES (regla 1/dia Mayerlin)')
print('-' * 40)
por_fecha = defaultdict(list)
for e in eventos:
    if e['fecha'] >= HOY:
        por_fecha[e['fecha']].append(e)
saturados = [(f, evs) for f, evs in por_fecha.items() if len(evs) >= 2]
saturados.sort()
if not saturados:
    print('  OK Ninguno')
else:
    for f, evs in saturados[:25]:
        print('  ' + str(f) + ' (' + NOMBRES_DIA[f.weekday()] + '): ' + str(len(evs)) + ' producciones')
        for e in evs:
            print('      └─ ' + e['summary'][:65])

# D) Mapeo SKU -> SKUs Calendar
SKU_KEYWORDS = {
    'SAH': ['SAH ', ' SAH', 'AH 1.5', 'HIDRATANTE'],
    'SAH10': ['SAH10'],
    'TRIAC': ['TRIAC ', ' TRIAC', 'TRIACTIVE 15', 'RETINOID 15'],
    'TRIAC30': ['TRIAC30', 'TRIACTIVE 30', 'RETINOID 30'],
    'NIA': ['NIA ', ' NIA', 'NIACINAMIDA 30', 'NIACINAMIDA'],
    'NIA10': ['NIA10', 'NIACINAMIDA 10'],
    'TRX': ['TRX ', ' TRX', 'ILUMINADOR TRX 30', 'ILUMINADOR TRX'],
    'TRX10': ['TRX10', 'TRX 10'],
    'CCAFE': ['CCAFE', 'CAFEINA', 'CAFEINA'],
    'CMULP': ['CMULP', 'CONTORNO MULTI'],
    'CRETT': ['CRETT', 'CONTORNO RETINAL', 'RETINAL'],
    'SMULPP': ['SMULPP', 'SUERO MULTIPEPTIDOS', 'SUERO MULTIP'],
    'BHA33': ['BHA33', 'EXFOLIANTE BHA'],
    'LBHA': ['LBHA', 'LIMPIADOR BHA', 'LIMPIADOR FACIAL BHA'],
    'LKJ': ['LKJ', 'KOJICO', 'LIMPIADOR ILUMI'],
    'LAH': ['LAH', 'LIMPIADOR HIDRATANTE'],
    'GELH': ['GELH', 'GEL HIDRATANTE'],
    'EMLIM': ['EMLIM', 'EMULSION LIMPIA'],
    'CRB3BHA': ['CRB3BHA', 'B3+BHA', 'B3 BHA', 'EMULSION B3'],
    'HKJ': ['HKJ', 'EMULSION ILUMI', 'EMULSION HIDRATANTE ILUMI'],
    'AZHC': ['AZHC ', 'AZ HYBRID 15', 'HYBRID 15'],
    'AZHC30': ['AZHC30', 'AZ HYBRID 30', 'HYBRID 30'],
    'NPHA30': ['NPHA30', 'NOVA-PHA 30', 'NOVA PHA'],
    'NPHA10': ['NPHA10', 'NOVA-PHA 10'],
    'SVITC33': ['SVITC33', 'VITAMINA C 30', 'SVITC 30', 'SVITC '],
    'SVITC3315': ['SVITC3315', 'VIT C 15'],
    'RECN-2': ['RECN-2', 'RENOVA C10 30', 'RENOVA30'],
    'MAXLASH': ['MAXLASH', 'CEJAS', 'PESTANAS'],
    'GLOSSN': ['GLOSSN ', 'GLOSS TRANSLU', 'TRANSLUCIDO'],
    'GLOSSMERLOT': ['GLOSSMERLOT', 'MERLOT'],
    'GLOSSMALVA': ['GLOSSMALVA', 'MALVA'],
    'GLOSSPEACH': ['GLOSSPEACH', 'PEACH'],
    'CRCUREA': ['CRCUREA', 'UREA', 'BODY'],
    'ECENT': ['ECENT', 'CENTELLA'],
    'EILU': ['EILU', 'ESENCIA ILUMI'],
}


def match_sku(summary, desc):
    text = (summary + ' ' + desc).upper()
    for sku, keys in SKU_KEYWORDS.items():
        for k in keys:
            if k.upper() in text:
                return sku
    return None


for e in eventos:
    e['sku_match'] = match_sku(e['summary'], e['description'])

# E) Huérfanos
print('\n[D] EVENTOS SIN SKU IDENTIFICABLE (huerfanos)')
print('-' * 40)
huerfanos = [e for e in eventos if not e['sku_match']]
print('  ' + str(len(huerfanos)) + ' de ' + str(len(eventos)) + ' eventos sin SKU detectable')
for e in huerfanos[:12]:
    print('    ' + str(e['fecha']) + ' ' + e['summary'][:70])

# F) Cobertura URGENTES
print('\n[E] COBERTURA DE SKU URGENTES (alcance < 25 dias)')
print('-' * 78)
URG = []
for sku in inv:
    a = inv[sku]['available']
    v = ventas.get(sku, 0)
    if v == 0:
        continue
    vel = v / DIAS_VENTAS
    if vel < 0.05:
        continue
    dias = a / vel if vel > 0 else 9999
    if dias < 25:
        URG.append((sku, inv[sku]['title'], a, vel, dias))
URG.sort(key=lambda x: x[4])

print('SKU         | Stock | Vel/d | Alcance | Prox Cal      | Gap | Estado')
print('-' * 78)
for sku, title, a, vel, dias in URG:
    futuros = [e for e in eventos if e.get('sku_match') == sku and e['fecha'] >= HOY]
    if futuros:
        prox = futuros[0]['fecha']
        gap = (prox - HOY).days
        stockout = HOY.toordinal() + int(dias)
        if prox.toordinal() <= stockout - 20:
            estado = 'OK'
        elif prox.toordinal() <= stockout:
            estado = 'TARDE'
        else:
            estado = 'STOCKOUT'
        print('{:12}| {:>5} | {:>5.2f} | {:>5.1f}d  | {:>13} | {:>3}d | {}'.format(sku, a, vel, dias, str(prox), gap, estado))
    else:
        print('{:12}| {:>5} | {:>5.2f} | {:>5.1f}d  | {:>13} | {:>3}  | {}'.format(sku, a, vel, dias, 'NO PLANEADO', '-', 'SIN PLAN'))

# G) Programados pero con stock cómodo
print('\n[F] PROGRAMADOS CON STOCK COMODO (alcance > 60d, no urge)')
print('-' * 78)
skus_cal = set(e['sku_match'] for e in eventos if e.get('sku_match'))
for sku in skus_cal:
    a = inv[sku]['available'] if sku in inv else 0
    v = ventas.get(sku, 0)
    vel = v / DIAS_VENTAS if v else 0
    if vel < 0.05 or a == 0:
        continue
    dias = a / vel
    if dias > 60:
        futuros = [e for e in eventos if e.get('sku_match') == sku and e['fecha'] >= HOY]
        if futuros:
            prox = futuros[0]['fecha']
            gap = (prox - HOY).days
            print('  ' + sku + ' stock ' + str(a) + 'u alcance ' + ('%.0f' % dias) + 'd prox-Cal ' + str(prox) + ' (en ' + str(gap) + 'd)  - innecesario tan pronto')

# H) Eventos pasados ya hechos
print('\n[G] PRODUCCIONES YA HECHAS (Calendar marcado "hecho")')
print('-' * 78)
hechos = [e for e in eventos if e['fecha'] < HOY and 'hecho' in (e['summary'] + e['description']).lower()]
print('  Total marcadas hechas: ' + str(len(hechos)) + ' (en abril)')
por_fecha_h = defaultdict(int)
for e in hechos:
    por_fecha_h[e['fecha']] += 1
for f, n in sorted(por_fecha_h.items()):
    if n > 1:
        print('  ' + str(f) + ' (' + NOMBRES_DIA[f.weekday()] + '): ' + str(n) + ' lotes en un dia (sobrecarga?)')

# I) Total eventos futuros vs urgentes
futuros_total = [e for e in eventos if e['fecha'] >= HOY]
print('\n[H] BALANCE GENERAL')
print('-' * 78)
print('  Eventos totales en Calendar:        ' + str(len(eventos)))
print('  Hechos (pasados):                   ' + str(len([e for e in eventos if e['fecha'] < HOY])))
print('  Futuros (pendientes):               ' + str(len(futuros_total)))
print('  SKUs urgentes (alcance <25d):       ' + str(len(URG)))
con_plan = sum(1 for s, _, _, _, _ in URG if any(e.get('sku_match') == s and e['fecha'] >= HOY for e in eventos))
print('  Urgentes con plan en Calendar:      ' + str(con_plan))
print('  Urgentes SIN plan en Calendar:      ' + str(len(URG) - con_plan))
