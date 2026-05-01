"""ULTRATHINK v2 — cadencia correcta usando BULK en gramos.

Insight clave: cuando hay hermanos (SAH+SAH10), el lote es el mismo bulk en gramos.
Lo que se consume del bulk depende de la presentación de cada venta:
  - 1 unidad SAH 30ml = 30 g del bulk
  - 1 unidad SAH10 10ml = 10 g del bulk
  Por lo tanto: bulk_consumido_día (g) = Σ ventas_sku × factor_g_sku

Lote_kg / bulk_consumido_día = días alcance del lote.
"""
import json
import csv
import sys
import io
import re
from datetime import date, datetime, timedelta
from collections import defaultdict, Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# DATOS
path_cal = r'C:\Users\sebas\.claude\projects\C--Users-sebas-Downloads-Claude\12b2fa66-3fd8-42c3-92e8-f207033a2c72\tool-results\mcp-7b88b900-684e-430a-957b-b1f73cf9c2ae-list_events-1777591629367.txt'
with open(path_cal, 'r', encoding='utf-8') as f:
    cal = json.load(f).get('events', [])

inv = defaultdict(lambda: {'animus_avail':0,'espagiria_avail':0,'espagiria_unavail':0})
with open(r'C:\Users\sebas\Downloads\inventory_export_1 (10).csv', 'r', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        sku = (r.get('SKU') or '').strip()
        if not sku: continue
        loc = (r.get('Location') or '').upper()
        try: a = int(r.get('Available (not editable)') or 0)
        except: a = 0
        try: u = int(r.get('Unavailable (not editable)') or 0)
        except: u = 0
        if 'NIMUS' in loc:
            inv[sku]['animus_avail'] += a
        elif 'ESPAGIRIA' in loc:
            inv[sku]['espagiria_avail'] += a
            inv[sku]['espagiria_unavail'] += u

ventas = {}
with open(r'C:\Users\sebas\Downloads\Ventas totales por variante de producto - 2026-01-01 - 2026-04-30.csv', 'r', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        sku = (r.get('SKU de variante de producto') or '').strip()
        if not sku: continue
        try: u = int(r.get('Articulos netos vendidos') or r.get('Artículos netos vendidos') or 0)
        except: u = 0
        ventas[sku] = u

DIAS = 120
HOY = date(2026, 4, 30)
MARGEN_MIN = 20
MARGEN_IDEAL = 25

# ════════════════════════════════════════════════════════════════════
# Factor g/u por presentación
# ════════════════════════════════════════════════════════════════════
FG = {
    'SAH':30, 'SAH10':10,
    'TRIAC':15, 'TRIAC30':30,
    'NIA':30, 'NIA10':10,
    'TRX':30, 'TRX10':10,
    'CCAFE':12, 'CMULP':15, 'CRETT':12,
    'SMULPP':30,
    'BHA33':30,
    'LBHA':150, 'LAH':150, 'LKJ':150, 'EMLIM':150,
    'GELH':40,
    'CRB3BHA':50, 'HKJ':50,
    'AZHC':15, 'AZHC30':30,
    'NPHA30':30, 'NPHA10':10,
    'SVITC33':30, 'SVITC3315':15,
    'RECN-2':30, 'RECN-1':15,
    'MAXLASH':4.5,
    'GLOSSN':10, 'GLOSSMERLOT':10, 'GLOSSMALVA':10, 'GLOSSPEACH':10, 'Glossmocca':10,
    'CRCUREA':100,
    'ECENT':30, 'EILU':30,
}

# ════════════════════════════════════════════════════════════════════
# GRUPOS de hermanos (mismo bulk)
# ════════════════════════════════════════════════════════════════════
GRUPOS = {
    'SAH':       {'lider':'SAH', 'skus':['SAH','SAH10'], 'producto':'Suero Hidratante AH 1.5%'},
    'NIA':       {'lider':'NIA', 'skus':['NIA','NIA10'], 'producto':'Suero Niacinamida'},
    'TRX':       {'lider':'TRX', 'skus':['TRX','TRX10'], 'producto':'Suero Iluminador TRX'},
    'TRIAC':     {'lider':'TRIAC', 'skus':['TRIAC','TRIAC30'], 'producto':'Suero Triactive Retinoid'},
    'NPHA':      {'lider':'NPHA30', 'skus':['NPHA30','NPHA10'], 'producto':'Suero Exfoliante Nova-PHA'},
    'AZHC':      {'lider':'AZHC30', 'skus':['AZHC','AZHC30'], 'producto':'Suero AZ Hybrid Clear'},
    'SVITC':     {'lider':'SVITC33', 'skus':['SVITC33','SVITC3315'], 'producto':'Suero Vitamina C+'},
    'RECN':      {'lider':'RECN-2', 'skus':['RECN-1','RECN-2'], 'producto':'Suero Antioxidante Renova C10'},
}

# Singletons (sin hermanos)
SINGLETONS = ['CCAFE','CMULP','CRETT','SMULPP','BHA33','LBHA','LAH','LKJ','EMLIM',
              'GELH','CRB3BHA','HKJ','MAXLASH','GLOSSN','GLOSSMERLOT','GLOSSMALVA',
              'GLOSSPEACH','Glossmocca','CRCUREA','ECENT','EILU']
for s in SINGLETONS:
    GRUPOS[s] = {'lider':s, 'skus':[s], 'producto':s}

# ════════════════════════════════════════════════════════════════════
# Matcheo SKU
# ════════════════════════════════════════════════════════════════════
SKU_KEYWORDS = {
    'SAH': ['SAH ', 'AH 1.5', 'HIDRATANTE'],
    'TRIAC': ['TRIAC ', 'TRIACTIVE', 'RETINOID', 'TRIAC_BATCH', 'TRIAC –', 'TRIAC -'],
    'NIA': [' NIA ', 'NIACINAMIDA'],
    'TRX': [' TRX ', 'ILUMINADOR TRX', ' TRX –', ' TRX -'],
    'CCAFE': ['CCAFE', 'CAFEINA', 'CAFEÍNA'],
    'CMULP': ['CMULP', 'CONTORNO MULTI'],
    'CRETT': ['CRETT', 'CONTORNO RETINAL', 'CONTORNO DE OJOS CON RETINAL'],
    'SMULPP': ['SMULPP', 'SUERO MULTIPEPTIDOS', 'SUERO MULTIPÉPTIDOS', 'MULTIPEPTIDOS'],
    'BHA33': ['BHA33', 'EXFOLIANTE BHA', 'SBHA'],
    'LBHA': ['LBHA', 'LIMPIADOR BHA', 'LIMPIADOR FACIAL BHA'],
    'LKJ': [' LKJ ', 'KOJICO', 'LKJ –', 'LKJ -'],
    'LAH': [' LAH ', 'LIMPIADOR HIDRATANTE'],
    'GELH': ['GELH', 'GEL HIDRATANTE'],
    'EMLIM': ['EMLIM', 'EMULSION LIMPIA'],
    'CRB3BHA': ['CRB3BHA', 'B3+BHA', 'EMULSION B3'],
    'HKJ': [' HKJ ', 'EMULSION ILUMI'],
    'AZHC30': ['AZHC30','AZHC ', 'AZ HYBRID', 'HYBRID CLEAR'],
    'NPHA30': ['NPHA30','NPHA ', 'NOVA-PHA', 'NPHA –', 'NPHA -'],
    'SVITC33': ['SVITC33', 'SVITC ', 'VITAMINA C', 'VIT C'],
    'RECN-2': ['RECN-2','RECN ', 'RENOVA C10', 'RENOVA30','RECN –','RECN -'],
    'MAXLASH': ['MAXLASH','CEJAS','PESTAÑAS'],
    'GLOSSN': ['GLOSSN ','TRANSLUCIDO','TRANSLÚCIDO'],
    'GLOSSMERLOT': ['GLOSSMERLOT','MERLOT'],
    'GLOSSMALVA': ['GLOSSMALVA','MALVA'],
    'GLOSSPEACH': ['GLOSSPEACH','PEACH'],
    'Glossmocca': ['GLOSSMOCCA','MOCCA'],
    'CRCUREA': ['CRCUREA','UREA','BODY'],
    'ECENT': ['ECENT','CENTELLA'],
    'EILU': ['EILU','ESENCIA ILUMINADORA'],
}

def match_grupo(text):
    t = ' ' + text.upper() + ' '
    matches = []
    for sku_lider, keys in SKU_KEYWORDS.items():
        for k in keys:
            if k.upper() in t:
                matches.append((len(k), sku_lider))
                break
    if matches:
        matches.sort(reverse=True)
        return matches[0][1]
    return None

# ════════════════════════════════════════════════════════════════════
# Procesar eventos — extraer SOLO fabricacion (no envasado/acondicionamiento)
# ════════════════════════════════════════════════════════════════════
def parse_kg(text):
    matches = re.findall(r'~?\s*(\d+(?:[.,]\d+)?)\s*kg', text, re.IGNORECASE)
    if matches:
        try: return float(matches[0].replace(',', '.'))
        except: pass
    return None

def parse_cad_ciclo(text):
    """Cadencia de ciclo: 'c/X días', '(X días)'.

    Excluye 'trigger X días' que NO es cadencia, es margen."""
    # Quitar texto trigger primero
    text = re.sub(r'trigger\s*\d+\s*d(?:í|i)?as', '', text, flags=re.IGNORECASE)
    patterns = [
        r'c/\s*(\d+)\s*d(?:í|i)?as',
        r'cada\s*(\d+)\s*d(?:í|i)?as',
        r'\(\s*(\d+)\s*d(?:í|i)?as\s*\)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try: return int(m.group(1))
            except: pass
    return None

eventos_fab = []
for e in cal:
    f = (e.get('start') or {}).get('date') or (e.get('start') or {}).get('dateTime', '')[:10]
    if not f: continue
    try: fd = datetime.strptime(f[:10], '%Y-%m-%d').date()
    except: continue
    s = e.get('summary','') or ''
    d = e.get('description','') or ''
    full = s + '\n' + d
    es_envasado = bool(re.search(r'envasad|micro\s*qc|acondicionamient', full, re.IGNORECASE))
    if es_envasado: continue
    grupo = match_grupo(full)
    if not grupo: continue
    eventos_fab.append({
        'fecha': fd,
        'summary': s,
        'description': d,
        'grupo': grupo,
        'kg': parse_kg(s) or parse_kg(d),
        'cadencia_decl': parse_cad_ciclo(s) or parse_cad_ciclo(d),
        'es_hecho': 'hecho' in full.lower() or '✅' in full,
    })

eventos_fab.sort(key=lambda x: x['fecha'])

# ════════════════════════════════════════════════════════════════════
# CALCULO BULK-BASED por grupo
# ════════════════════════════════════════════════════════════════════
print('=' * 115)
print('CADENCIAS POR GRUPO — bulk en gramos (correcto para hermanos)')
print('=' * 115)
print()
print('{:13} {:>7} {:>9} {:>9} {:>7} {:>7} {:>7} {:>5} {:>5} {:>5} {:>4} {:>13}'.format(
    'Grupo','Lote_kg','Stock_g','BulkVel','Alcance','Lote_d','CadOpt','CadIde','Cad-D','Cad-R','Ev','Verdict'))
print('-' * 115)

resumen = []

for grupo_id, info in GRUPOS.items():
    skus = info['skus']
    lider = info['lider']

    # Bulk velocidad: gramos consumidos por día = sum(ventas/120 × factor_g)
    bulk_vel_g = 0
    for s in skus:
        v = ventas.get(s, 0) / DIAS
        bulk_vel_g += v * FG.get(s, 30)

    # Stock bulk equivalente: gramos en stock = sum(stock_unidades × factor_g)
    stock_bulk_g = 0
    stock_total_u = 0
    for s in skus:
        d = inv.get(s, {})
        stock_u = d.get('animus_avail',0) + d.get('espagiria_avail',0) + d.get('espagiria_unavail',0)
        stock_bulk_g += stock_u * FG.get(s, 30)
        stock_total_u += stock_u

    # Alcance HOY (días) = stock_bulk_g / bulk_vel_g
    alcance_hoy = stock_bulk_g / bulk_vel_g if bulk_vel_g > 0.5 else None

    # Eventos de este grupo
    evs = [e for e in eventos_fab if e['grupo'] == lider]
    n_evs = len(evs)

    # Lote típico kg (mediana)
    kgs = sorted([e['kg'] for e in evs if e['kg']])
    if kgs:
        lote_kg = kgs[len(kgs)//2]
    else:
        lote_kg = None

    # Cadencia REAL (gap promedio entre fechas)
    fechas = sorted([e['fecha'] for e in evs])
    gaps = []
    if len(fechas) >= 2:
        for i in range(1, len(fechas)):
            gaps.append((fechas[i] - fechas[i-1]).days)
    cad_real = round(sum(gaps)/len(gaps)) if gaps else None

    # Cadencia DECLARADA (de eventos futuros, no del último pasado que tiene "trigger")
    cads_decl = [e['cadencia_decl'] for e in evs if e['cadencia_decl'] and e['fecha'] > HOY]
    if not cads_decl:
        cads_decl = [e['cadencia_decl'] for e in evs if e['cadencia_decl']]
    cad_decl = Counter(cads_decl).most_common(1)[0][0] if cads_decl else None

    # Cadencia OPTIMA (teórica con margen mínimo 20d)
    if lote_kg and bulk_vel_g > 0.5:
        lote_dura_d = (lote_kg * 1000) / bulk_vel_g
        cad_optima = lote_dura_d - MARGEN_MIN
        cad_ideal = lote_dura_d - MARGEN_IDEAL
    else:
        lote_dura_d = None
        cad_optima = None
        cad_ideal = None

    # Verdict
    verdict = '?'
    if cad_decl is None and cad_optima is None:
        verdict = 'sin datos'
    elif cad_decl is None:
        verdict = 'sin Cad-D'
    elif cad_optima is None:
        verdict = 'sin lote conocido'
    else:
        diff = cad_decl - cad_optima
        if abs(diff) < 10:
            verdict = 'OK'
        elif diff > 0:
            verdict = 'Acortar ' + str(int(round(diff))) + 'd'
        else:
            verdict = 'Alargar ' + str(int(round(-diff))) + 'd'

    resumen.append({
        'grupo': grupo_id,
        'producto': info['producto'],
        'lider': lider,
        'skus': skus,
        'lote_kg': lote_kg,
        'bulk_vel_g_dia': round(bulk_vel_g),
        'stock_unidades_total': stock_total_u,
        'stock_bulk_g': round(stock_bulk_g),
        'alcance_hoy_dias': round(alcance_hoy) if alcance_hoy else None,
        'lote_dura_dias': round(lote_dura_d) if lote_dura_d else None,
        'cadencia_optima_min': round(cad_optima) if cad_optima else None,
        'cadencia_ideal_25d': round(cad_ideal) if cad_ideal else None,
        'cadencia_declarada_calendar': cad_decl,
        'cadencia_real_observada': cad_real,
        'eventos_calendar': n_evs,
        'verdict': verdict,
    })

resumen.sort(key=lambda x: (x['alcance_hoy_dias'] is None, x['alcance_hoy_dias'] or 9999))

for r in resumen:
    print('{:13} {:>6}{:>1} {:>8}g {:>7}g/d {:>5}d {:>5}d {:>5} {:>5} {:>5} {:>5} {:>4} {:>13}'.format(
        r['grupo'][:13],
        ('%.0f' % r['lote_kg']) if r['lote_kg'] else '-',
        'k' if r['lote_kg'] else '',
        r['stock_bulk_g'],
        r['bulk_vel_g_dia'],
        ('%d' % r['alcance_hoy_dias']) if r['alcance_hoy_dias'] is not None else '—',
        ('%d' % r['lote_dura_dias']) if r['lote_dura_dias'] else '—',
        ('%dd' % r['cadencia_optima_min']) if r['cadencia_optima_min'] else '—',
        ('%dd' % r['cadencia_ideal_25d']) if r['cadencia_ideal_25d'] else '—',
        ('%dd' % r['cadencia_declarada_calendar']) if r['cadencia_declarada_calendar'] else '—',
        ('%dd' % r['cadencia_real_observada']) if r['cadencia_real_observada'] else '—',
        r['eventos_calendar'],
        r['verdict'],
    ))

# ════════════════════════════════════════════════════════════════════
# EJEMPLO DETALLADO: SAH (para validar la fórmula)
# ════════════════════════════════════════════════════════════════════
print('\n' + '=' * 100)
print('EJEMPLO DETALLADO — SAH (validar fórmula bulk)')
print('=' * 100)
sah = next(r for r in resumen if r['grupo'] == 'SAH')
print('\nProducto:    ' + sah['producto'])
print('SKUs grupo:  ' + ', '.join(sah['skus']))
print('Stock unidades:')
for s in sah['skus']:
    d = inv.get(s, {})
    a = d.get('animus_avail',0); ed = d.get('espagiria_avail',0); eu = d.get('espagiria_unavail',0)
    print('  - ' + s + ': Anim=' + str(a) + ' EspD=' + str(ed) + ' EspU=' + str(eu) + ' (' + str(FG[s]) + ' g/u) → ' + str((a+ed+eu)*FG[s]) + ' g bulk')
print()
print('Stock bulk total: ' + str(sah['stock_bulk_g']) + ' g (= ' + str(round(sah['stock_bulk_g']/1000,1)) + ' kg de producto)')
print('Velocidad:')
for s in sah['skus']:
    v = ventas.get(s,0); vd = v/DIAS
    print('  - ' + s + ': ' + str(v) + ' u en 120d → ' + ('%.2f' % vd) + ' u/d × ' + str(FG[s]) + ' g/u = ' + ('%.0f' % (vd*FG[s])) + ' g/d')
print('  Bulk consumido total: ' + str(sah['bulk_vel_g_dia']) + ' g/día')
print()
print('Lote típico Calendar: ' + str(sah['lote_kg']) + ' kg = ' + str(int(sah['lote_kg']*1000)) + ' g')
print('Días que dura lote: ' + str(int(sah['lote_kg']*1000)) + 'g ÷ ' + str(sah['bulk_vel_g_dia']) + ' g/d = ' + str(sah['lote_dura_dias']) + ' días')
print('Cadencia óptima (margen 20d): ' + str(sah['cadencia_optima_min']) + ' días')
print('Cadencia ideal (margen 25d):  ' + str(sah['cadencia_ideal_25d']) + ' días')
print('Cadencia declarada Calendar:  ' + str(sah['cadencia_declarada_calendar']) + ' días')
print('Verdict: ' + sah['verdict'])
print()
print('Alcance HOY: ' + str(sah['stock_bulk_g']) + 'g ÷ ' + str(sah['bulk_vel_g_dia']) + 'g/d = ' + str(sah['alcance_hoy_dias']) + ' días')
print('  → próximo lote toca dentro de: ' + str(sah['alcance_hoy_dias'] - MARGEN_MIN) + ' días')
print('  → fecha próxima sugerida (margen 20d): ' + str(HOY + timedelta(days=sah['alcance_hoy_dias']-MARGEN_MIN)))
print('  → fecha ideal (margen 25d):            ' + str(HOY + timedelta(days=sah['alcance_hoy_dias']-MARGEN_IDEAL)))
