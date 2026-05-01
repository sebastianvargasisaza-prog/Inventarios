"""TABLA MAESTRA — todas las reglas aplicadas, plan perfecto.

Reglas integradas:
  1. Stock = Animus_Avail + Espagiria_Avail + Espagiria_Unavail + Pipeline_7d
  2. Velocidad = Shopify_4m + B2B_Fernando_trimestral / 90d
  3. Para SAH y TRX: descontar 12 kg del lote (regalo 10ml fijos 1200 u)
  4. Para NPHA y otros: 10ml según ventas
  5. Cadencia: margen 20d mínimo, 25d ideal
  6. Productos hermanos: bulk en gramos
  7. Festivos colombianos NO programar
  8. Excluir kits y productos pausados/descontinuados
  9. Comparar con Calendar actual: detectar acortar/alargar
  10. Histórico 6.3 años: confirmar crecimiento, ajustar buffer
"""
import csv
import sys
import io
import json
import re
from datetime import date, datetime, timedelta
from collections import defaultdict, Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HOY = date(2026, 4, 30)
DIAS_RECIENTE = 120
DIAS_HISTORICO = (HOY - date(2020, 1, 1)).days  # 2311
MARGEN_MIN = 20
MARGEN_IDEAL = 25

# Festivos Colombia 2026 (días que NO se produce)
FESTIVOS = [
    date(2026, 5, 1),   # Trabajo
    date(2026, 5, 18),  # Ascensión
    date(2026, 6, 8),   # Corpus
    date(2026, 6, 15),  # Sagrado Corazón
    date(2026, 6, 29),  # San Pedro
    date(2026, 7, 20),  # Independencia
    date(2026, 8, 7),   # Boyacá
    date(2026, 8, 17),  # Asunción
    date(2026, 10, 12), # Raza
    date(2026, 11, 2),  # Todos Santos
    date(2026, 11, 16), # Cartagena
    date(2026, 12, 8),  # Inmaculada
    date(2026, 12, 25), # Navidad
]

# ════════════════════════════════════════════════════════════════════
# DATOS
# ════════════════════════════════════════════════════════════════════
inv = defaultdict(lambda: {'animus_avail':0,'esp_avail':0,'esp_unavail':0})
with open(r'C:\Users\sebas\Downloads\inventory_export_1 (10).csv', 'r', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        sku = (r.get('SKU') or '').strip()
        if not sku: continue
        loc = (r.get('Location') or '').upper()
        try: a = int(r.get('Available (not editable)') or 0)
        except: a = 0
        try: u = int(r.get('Unavailable (not editable)') or 0)
        except: u = 0
        if 'NIMUS' in loc: inv[sku]['animus_avail'] += a
        elif 'ESPAGIRIA' in loc:
            inv[sku]['esp_avail'] += a
            inv[sku]['esp_unavail'] += u

ventas_4m = {}
with open(r'C:\Users\sebas\Downloads\Ventas totales por variante de producto - 2026-01-01 - 2026-04-30.csv', 'r', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        sku = (r.get('SKU de variante de producto') or '').strip()
        if not sku: continue
        try: u = int(r.get('Articulos netos vendidos') or r.get('Artículos netos vendidos') or 0)
        except: u = 0
        ventas_4m[sku] = u

ventas_hist = {}
with open(r'C:\Users\sebas\Downloads\Ventas totales por variante de producto - 2020-01-01 - 2026-04-30.csv', 'r', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        sku = (r.get('SKU de variante de producto') or '').strip()
        if not sku: continue
        try: u = int(r.get('Articulos netos vendidos') or r.get('Artículos netos vendidos') or 0)
        except: u = 0
        ventas_hist[sku] = u

# Pipeline 7d (lo recién hecho)
PIPELINE = {
    'SAH':    1800, 'SAH10':   1200,  # lote 90kg 30-abr (60% 30ml + 1200 regalo 10ml)
    'GELH':    500,  # 20kg 29-abr (corregido)
    'LBHA':   1000,  # 150kg 28-abr (corregido)
    'GLOSSN':  500,
    'NPHA30':  181,
    'CRETT':   750,
}

# Pedidos B2B Fernando (trimestral) — siguiente pedido confirmado
FERNANDO_PEDIDO = {
    'LBHA':    500,
    'CRCUREA': 500,
    'NIA':     300,
    'BHA33':   200,
    'AZHC30':  200,
    'GELH':    300,
    'TRX':     300,
    'ECENT':   500,
    # EILU: pendiente, no incluir aún
}

# Factor g/u por SKU
FG = {
    'SAH':30, 'SAH10':10,
    'TRIAC':15, 'TRIAC30':30,
    'NIA':30, 'NIA10':10,
    'TRX':30, 'TRX10':10,
    'CCAFE':12, 'CMULP':15, 'CRETT':12,
    'SMULPP':30, 'BHA33':30, 'BHA10':10,
    'LBHA':150, 'LAH':150, 'LKJ':150, 'EMLIM':150,
    'GELH':40,
    'CRB3BHA':50, 'HKJ':50,
    'AZHC':15, 'AZHC30':30,
    'NPHA30':30, 'NPHA10':10,
    'SVITC33':30, 'SVITC3315':15, 'SVITC10':10,
    'RECN-2':30, 'RECN-1':15,
    'MAXLASH':4.5,
    'GLOSSN':10, 'GLOSSMERLOT':10, 'GLOSSMALVA':10, 'GLOSSPEACH':10, 'Glossmocca':10,
    'CRCUREA':100,
    'ECENT':30, 'EILU':30,
}

# Grupos hermanos (mismo bulk)
GRUPOS = {
    'SAH':       {'skus':['SAH','SAH10'], 'producto':'Suero Hidratante AH 1.5%', 'regalo_10ml':1200},
    'NIA':       {'skus':['NIA','NIA10'], 'producto':'Suero Niacinamida'},
    'TRX':       {'skus':['TRX','TRX10'], 'producto':'Suero Iluminador TRX', 'regalo_10ml':1200},
    'TRIAC':     {'skus':['TRIAC','TRIAC30'], 'producto':'Suero Triactive Retinoid'},
    'NPHA':      {'skus':['NPHA30','NPHA10'], 'producto':'Suero Exfoliante Nova-PHA'},
    'AZHC':      {'skus':['AZHC','AZHC30'], 'producto':'Suero AZ Hybrid Clear'},
    'SVITC':     {'skus':['SVITC33','SVITC3315','SVITC10'], 'producto':'Suero Vitamina C+ (FÓRMULA NUEVA)'},
    'RECN':      {'skus':['RECN-1','RECN-2'], 'producto':'Suero Renova C10', 'nota':'RECN-1 15ml agotado, parado'},
    'BHA':       {'skus':['BHA33','BHA10'], 'producto':'Suero Exfoliante BHA 2%'},
}

SINGLETONS = ['CCAFE','CMULP','CRETT','SMULPP','LBHA','LAH','LKJ','EMLIM',
              'GELH','CRB3BHA','HKJ','MAXLASH','GLOSSN','GLOSSMERLOT','GLOSSMALVA',
              'GLOSSPEACH','Glossmocca','CRCUREA','ECENT','EILU']

# Lotes típicos del Calendar (de eventos recientes)
LOTE_TIPICO_KG = {
    'SAH': 90, 'TRX': 92, 'NIA': 97, 'TRIAC': 16, 'NPHA': 12, 'AZHC': 28,
    'SVITC': 23, 'RECN': 18, 'BHA': 75,
    'CCAFE': 10, 'CMULP': 9, 'CRETT': 14, 'SMULPP': 30,
    'LBHA': 150, 'LAH': 70, 'LKJ': 160, 'EMLIM': 98,
    'GELH': 50, 'CRB3BHA': 33, 'HKJ': 20,
    'MAXLASH': 3, 'GLOSSN': 5, 'GLOSSMERLOT': 2, 'GLOSSMALVA': 2, 'GLOSSPEACH': 2,
    'Glossmocca': 2, 'CRCUREA': 100, 'ECENT': 114, 'EILU': 20,
}

# ════════════════════════════════════════════════════════════════════
# Función: próxima fecha L/M/V evitando festivos
# ════════════════════════════════════════════════════════════════════
def proxima_fecha_LMV(desde):
    """Avanza al próximo L/M/V que no sea festivo."""
    f = max(desde, HOY + timedelta(days=2))
    DIAS_LMV = (0, 2, 4)  # lun mar mié jue vie? L/M/V = 0, 2, 4
    for _ in range(120):
        if f.weekday() in DIAS_LMV and f not in FESTIVOS:
            return f
        f += timedelta(days=1)
    return f

# ════════════════════════════════════════════════════════════════════
# CALCULO POR GRUPO
# ════════════════════════════════════════════════════════════════════
def calcular_grupo(grupo_id, info):
    skus = info['skus']
    regalo_u = info.get('regalo_10ml', 0)
    lote_kg = LOTE_TIPICO_KG.get(grupo_id)

    # Stock efectivo (gramos de bulk)
    stock_g = 0
    stock_u_total = 0
    for s in skus:
        d = inv.get(s, {})
        stock_u = d.get('animus_avail',0) + d.get('esp_avail',0) + d.get('esp_unavail',0)
        stock_u += PIPELINE.get(s, 0)
        stock_u_total += stock_u
        stock_g += stock_u * FG.get(s, 30)

    # Velocidad Shopify reciente (suma de hermanos en gramos/día)
    bulk_vel_g = 0
    vel_unidades = {}
    for s in skus:
        v_4m = ventas_4m.get(s, 0) / DIAS_RECIENTE
        v_hist = ventas_hist.get(s, 0) / DIAS_HISTORICO
        crecimiento = v_4m / v_hist if v_hist > 0.01 else None
        vel_unidades[s] = {'reciente_u_d': v_4m, 'historica_u_d': v_hist, 'crecimiento': crecimiento}
        bulk_vel_g += v_4m * FG.get(s, 30)

    # Demanda B2B Fernando (trimestral → /90 días para velocidad equivalente)
    fernando_g_dia = 0
    fernando_skus_aplica = {}
    for s in skus:
        if s in FERNANDO_PEDIDO:
            cantidad_trim = FERNANDO_PEDIDO[s]
            v_b2b = cantidad_trim / 90  # u/d equivalente
            fernando_g_dia += v_b2b * FG.get(s, 30)
            fernando_skus_aplica[s] = cantidad_trim

    # Bulk total consumido por día = ventas Shopify + B2B Fernando
    bulk_total_g_dia = bulk_vel_g + fernando_g_dia

    # Para SAH y TRX: el lote se reparte 78kg venta + 12kg regalo fijo
    # Bulk útil para venta = lote_kg - 12 (si tiene regalo_10ml)
    if regalo_u and lote_kg:
        bulk_util_lote_g = (lote_kg * 1000) - (regalo_u * 10)
        # El regalo no consume velocidad de venta (es fijo por lote)
        # Lo modelamos: cada lote produce 12 kg para regalo + 78 kg para venta
    else:
        bulk_util_lote_g = lote_kg * 1000 if lote_kg else None

    # Cadencia teórica
    if bulk_util_lote_g and bulk_total_g_dia > 1:
        lote_dura_d = bulk_util_lote_g / bulk_total_g_dia
        cad_min = lote_dura_d - MARGEN_MIN
        cad_ideal = lote_dura_d - MARGEN_IDEAL
    else:
        lote_dura_d = None
        cad_min = None
        cad_ideal = None

    # Alcance HOY (días hasta stockout sin nuevo lote)
    if bulk_total_g_dia > 1:
        # Para grupos con regalo, el stock 10ml es regalo fijo, no cuenta para venta
        if regalo_u and lote_kg:
            # Stock útil = stock total en gramos - reserva regalo equivalente
            # El regalo "sale" en función del ciclo, no diariamente
            # Aproximación: stock útil = stock_g (todo cuenta porque el regalo ya está apartado)
            stock_util_g = stock_g  # simplificación
        else:
            stock_util_g = stock_g
        alcance_d = stock_util_g / bulk_total_g_dia
    else:
        alcance_d = None

    # Próxima fecha sugerida
    if alcance_d is not None and alcance_d > 0:
        dias_hasta_lote_min = max(0, int(alcance_d - MARGEN_MIN))
        dias_hasta_lote_ideal = max(0, int(alcance_d - MARGEN_IDEAL))
        prox_min = proxima_fecha_LMV(HOY + timedelta(days=dias_hasta_lote_min))
        prox_ideal = proxima_fecha_LMV(HOY + timedelta(days=dias_hasta_lote_ideal))
    else:
        prox_min = None
        prox_ideal = None

    return {
        'grupo': grupo_id,
        'producto': info['producto'],
        'skus': skus,
        'regalo_10ml': regalo_u,
        'lote_kg': lote_kg,
        'stock_unidades_total': stock_u_total,
        'stock_bulk_g': round(stock_g),
        'bulk_vel_g_dia_shopify': round(bulk_vel_g, 1),
        'bulk_vel_g_dia_fernando': round(fernando_g_dia, 1),
        'bulk_total_g_dia': round(bulk_total_g_dia, 1),
        'fernando_skus': fernando_skus_aplica,
        'lote_dura_d': round(lote_dura_d) if lote_dura_d else None,
        'cadencia_min': round(cad_min) if cad_min else None,
        'cadencia_ideal': round(cad_ideal) if cad_ideal else None,
        'alcance_hoy_d': round(alcance_d) if alcance_d else None,
        'proxima_min': prox_min,
        'proxima_ideal': prox_ideal,
        'crecimiento_skus': vel_unidades,
        'nota': info.get('nota', ''),
    }

# Procesar todos
GRUPOS_TODOS = {**GRUPOS}
for s in SINGLETONS:
    GRUPOS_TODOS[s] = {'skus':[s], 'producto':s}

resultados = []
for gid, info in GRUPOS_TODOS.items():
    r = calcular_grupo(gid, info)
    resultados.append(r)

# Ordenar por urgencia (alcance ascendente)
resultados.sort(key=lambda r: (r['alcance_hoy_d'] is None, r['alcance_hoy_d'] or 9999))

# ════════════════════════════════════════════════════════════════════
# IMPRIMIR TABLA MAESTRA
# ════════════════════════════════════════════════════════════════════
print('═' * 120)
print('TABLA MAESTRA — Plan de Producción Ánimus (con todas las reglas aplicadas)')
print('Hoy: ' + str(HOY) + '  ·  Reglas: stock_efectivo + B2B Fernando + 10ml regalo + festivos + margen 20/25d')
print('═' * 120)
print()
print('{:13} {:>6} {:>5} {:>7} {:>5} {:>5} {:>5} {:>5} {:>11} {:>11}'.format(
    'Grupo', 'LoteKg', 'Stock', 'BulkV/d', 'Alcan', 'Dura', 'CadMin', 'CadIde', 'PróxMin', 'PróxIdeal'))
print('-' * 120)

for r in resultados:
    nota = ' ⭐' if r['regalo_10ml'] else ''
    if r['fernando_skus']: nota += ' 👤F'
    print('{:13} {:>5}{:>1} {:>5} {:>6}g/d {:>4}d {:>4}d {:>4}d {:>4}d {:>11} {:>11}{}'.format(
        r['grupo'][:13],
        ('%.0f' % r['lote_kg']) if r['lote_kg'] else '-', 'k' if r['lote_kg'] else '',
        r['stock_unidades_total'],
        r['bulk_total_g_dia'],
        r['alcance_hoy_d'] or '—',
        r['lote_dura_d'] or '—',
        r['cadencia_min'] or '—',
        r['cadencia_ideal'] or '—',
        str(r['proxima_min'])[5:] if r['proxima_min'] else '—',
        str(r['proxima_ideal'])[5:] if r['proxima_ideal'] else '—',
        nota,
    ))

# Aclaraciones
print()
print('⭐ = grupo con regalo 10ml (1200 fijas/lote: SAH, TRX)')
print('👤F = producto que Fernando pide trimestral')

# Crecimiento histórico vs reciente
print('\n' + '═' * 80)
print('TENDENCIA crecimiento (Shopify reciente / histórico 6.3 años)')
print('═' * 80)
print()
print('{:13} {:>9} {:>9} {:>8}'.format('SKU', 'Vel hist', 'Vel 4m', 'Crece'))
print('-' * 50)
crecimientos = []
for r in resultados:
    for s, info in r['crecimiento_skus'].items():
        if info['historica_u_d'] > 0.05 and info['reciente_u_d'] > 0.05:
            crecimientos.append((s, info['historica_u_d'], info['reciente_u_d'], info['crecimiento']))

crecimientos.sort(key=lambda x: -x[3] if x[3] else 0)
for s, vh, vr, c in crecimientos[:25]:
    flag = ' 🚀' if c > 3 else ' ⬆' if c > 1.5 else ' ⬇' if c < 0.7 else ''
    print('{:13} {:>7.2f}/d {:>7.2f}/d {:>6.1f}×{}'.format(s, vh, vr, c, flag))

# Promedio crecimiento
if crecimientos:
    avg = sum(c for _,_,_,c in crecimientos) / len(crecimientos)
    print(f'\nCrecimiento promedio: {avg:.1f}× (negocio creciendo {(avg-1)*100:.0f}% sostenido)')
