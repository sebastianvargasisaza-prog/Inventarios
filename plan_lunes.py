"""Stock REAL = Available + Unavailable Espagiria + Pipeline 7d reciente."""
import csv
import sys
import io
from datetime import date, timedelta
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Stock por SKU separado por ubicacion + tipo
inv = defaultdict(lambda: {
    'title': '',
    'animus_available': 0,
    'animus_committed': 0,
    'espagiria_available': 0,
    'espagiria_unavailable': 0,  # producido pero NO trasladado/etiquetado
})

with open(r'C:\Users\sebas\Downloads\inventory_export_1 (10).csv', 'r', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        sku = (r.get('SKU') or '').strip()
        if not sku: continue
        loc = (r.get('Location') or '').strip()
        try: a = int(r.get('Available (not editable)') or 0)
        except: a = 0
        try: c = int(r.get('Committed (not editable)') or 0)
        except: c = 0
        try: u = int(r.get('Unavailable (not editable)') or 0)
        except: u = 0
        title = r.get('Title', '')
        v = (r.get('Option1 Value') or '').strip()
        if v: title += ' (' + v + ')'
        inv[sku]['title'] = title
        if 'NIMUS' in loc.upper():
            inv[sku]['animus_available'] += a
            inv[sku]['animus_committed'] += c
        elif 'ESPAGIRIA' in loc.upper():
            inv[sku]['espagiria_available'] += a
            inv[sku]['espagiria_unavailable'] += u

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

# Pipeline 7d (correcciones reales)
# Sebastian confirmo:
#   LBHA 28-abr: 150 kg
#   GELH 29-abr: 20 kg
#   HKJ 30-abr: NO se hizo
#   SAH 30-abr: 90 kg (entre SAH y SAH10)
#   GLOSSN 28-abr: 5 kg
#   NPHA 23-abr: 12 kg
#   CRETT 23-abr: 9 kg
#   EMLIM 22-abr: 20 kg salieron 125 u (no 133)
#   CMULP 22-abr: 600 u (faltan 338 por subir a inventario)
#   TRIAC 17-abr: 866 u, serigrafia mal -> devolucion, NO entregado
PIPELINE = [
    (date(2026, 4, 30), 'SAH',   90, 1800),    # 60% del lote 90kg = 1800u (presentacion 30ml)
    (date(2026, 4, 30), 'SAH10', 0,  1200),    # 40% del lote 90kg = 1200u (presentacion 10ml)
    (date(2026, 4, 29), 'GELH',  20, 500),
    (date(2026, 4, 28), 'LBHA',  150, 1000),
    (date(2026, 4, 28), 'GLOSSN', 5, 500),
    (date(2026, 4, 23), 'NPHA30', 12, 181),
    (date(2026, 4, 23), 'CRETT',  9, 750),
]

pipeline_por_sku = defaultdict(int)
for fecha, sku, kg, u in PIPELINE:
    edad = (HOY - fecha).days
    if edad <= 7:
        pipeline_por_sku[sku] += u

print('=' * 90)
print('STOCK REAL ANIMUS — Available + Espagiria(disponible+pendiente) + Pipeline 7d')
print('Hoy: ' + str(HOY) + '  ·  Pipeline = lotes hechos < 7d esperando entrega')
print('=' * 90)

def estado(d):
    if d is None: return '—'
    if d < 0: return 'STOCKOUT'
    if d < 20: return 'URGENTE'
    if d < 40: return 'PRONTO'
    if d < 80: return 'OK'
    return 'SOBRA'

print('\n{:13} {:>5} {:>5} {:>5} {:>5} {:>6} {:>6} {:>5}  {}'.format(
    'SKU', 'Anim', 'EspD', 'EspU', 'Pipe', 'TOTAL', 'Vel/d', 'Días', 'Estado'))
print('-' * 90)

# Procesar todos los SKUs con ventas
items = []
for sku in inv:
    v = ventas.get(sku, 0)
    if v == 0: continue
    a = inv[sku]['animus_available']
    espD = inv[sku]['espagiria_available']
    espU = inv[sku]['espagiria_unavailable']
    pipe = pipeline_por_sku.get(sku, 0)
    total = a + espD + espU + pipe
    vel = v / DIAS_VENTAS
    if vel < 0.05:
        items.append((sku, a, espD, espU, pipe, total, vel, None))
    else:
        items.append((sku, a, espD, espU, pipe, total, vel, total / vel))

items.sort(key=lambda x: (x[7] is None, x[7] if x[7] is not None else 9999))

for sku, a, espD, espU, pipe, total, vel, dias in items:
    dias_str = '—' if dias is None else ('%.0f' % dias) + 'd'
    pipe_s = ('+' + str(pipe)) if pipe else '0'
    espU_s = ('+' + str(espU)) if espU else '0'
    espD_s = str(espD) if espD else '0'
    print('{:13} {:>5} {:>5} {:>5} {:>5} {:>6} {:>6.2f} {:>5}  {}'.format(
        sku, a, espD_s, espU_s, pipe_s, total, vel, dias_str, estado(dias)))

# Casos especiales
print('\n[CASOS ESPECIALES]')
print('-' * 80)
print('TRIAC 15ml: stock real -215 + lote 866u en Espagiria pero CON SERIGRAFIA MAL')
print('   -> esperando devolucion + reserigrafia. ETA desconocida.')
print('   -> de momento NO contar como pipeline. Stock real: -215')
print('AZHC 15ml: -3 stock. No se hizo por falta MP. Pendiente cuando llegue MP.')
print('HKJ: -9 stock. NO se produjo hoy 30-abr (Calendar mintio).')
print('   -> URGENTE: programar lote esta semana.')
print('CMULP: 4 Animus + 338 unavailable Espagiria = 342u real')
print('   -> faltan 258u del lote 600u del 22-abr. Pueden estar en otra parte.')
print('EMLIM: 25 Animus + 125 unavailable Espagiria = 150u real')
print('   -> lote 22-abr fue 125u (no 133 como decia Calendar)')

# El lunes
print('\n' + '=' * 80)
print('PROXIMA SEMANA (4-may a 8-may): que toca producir')
print('=' * 80)
print()
# Top urgentes
urgentes = [(s,a,d,e,p,t,v,da) for s,a,d,e,p,t,v,da in items if da is not None and da < 25]
print('TOP URGENTES (alcance < 25 dias):')
print('{:13} {:>6} {:>6} {:>5}  {}'.format('SKU','Stock','Vel/d','Dias','Comentario'))
print('-' * 80)
COMENTARIOS = {
    'TRIAC': 'EN DEVOLUCION serigrafia, ETA?',
    'HKJ': 'NO se hizo hoy, falta agendar',
    'AZHC': 'Falta MP, pendiente',
    'CMULP': 'OK con Espagiria pendiente trasladar',
    'EMLIM': 'OK con Espagiria pendiente trasladar',
    'NPHA10': 'Sin lote programado',
    'LKJ': 'Lote 4-may en Calendar (160 kg) ✓',
    'SAH': 'Lote hoy en pipeline ✓',
    'GLOSSN': 'Lote 28-abr en pipeline ✓',
    'CRETT': 'Lote 23-abr en pipeline ✓',
    'NPHA30': 'Lote 23-abr en pipeline ✓',
    'LBHA': 'Lote 28-abr en pipeline ✓',
    'GELH': 'Lote 29-abr en pipeline ✓',
    'MAXLASH': 'Lote 14-may en Calendar',
}
for sku, a, d, e, p, t, v, da in urgentes:
    com = COMENTARIOS.get(sku, '')
    print('{:13} {:>6} {:>6.2f} {:>4.0f}d  {}'.format(sku, t, v, da, com))
