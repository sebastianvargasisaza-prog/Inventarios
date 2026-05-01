"""ULTRATHINK: extraer cadencias declaradas + reales + teóricas por SKU.

Input:
  - Calendar Producciones (74 eventos, abr-ago 2026)
  - Shopify inventario (Available + Espagiria pending + pipeline)
  - Shopify ventas 120d
  - Reglas: margen 20d/25d, productos hermanos, factor g/u

Output:
  Para cada SKU activo:
    - Lote típico (kg) — mediana histórica + Calendar
    - Factor g/u — por categoría
    - Unidades por lote
    - Velocidad — ventas/120
    - Cadencia DECLARADA — texto Calendar "c/X días"
    - Cadencia REAL — gap entre eventos consecutivos
    - Cadencia TEÓRICA — alcance lote - margen 20d
    - Verdict: ¿declarada coincide con teórica?
"""
import json
import csv
import sys
import io
import re
from datetime import date, datetime, timedelta
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─────────────────────────────────────────────────────────────────────
# 1) CARGAR DATOS COMPLETOS
# ─────────────────────────────────────────────────────────────────────
path_cal = r'C:\Users\sebas\.claude\projects\C--Users-sebas-Downloads-Claude\12b2fa66-3fd8-42c3-92e8-f207033a2c72\tool-results\mcp-7b88b900-684e-430a-957b-b1f73cf9c2ae-list_events-1777591629367.txt'
with open(path_cal, 'r', encoding='utf-8') as f:
    cal = json.load(f).get('events', [])

# Inventario por ubicación
inv = defaultdict(lambda: {
    'title': '',
    'animus_avail': 0,
    'animus_committed': 0,
    'espagiria_avail': 0,
    'espagiria_unavail': 0,
})
with open(r'C:\Users\sebas\Downloads\inventory_export_1 (10).csv', 'r', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        sku = (r.get('SKU') or '').strip()
        if not sku: continue
        loc = (r.get('Location') or '').upper()
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
        if 'NIMUS' in loc:
            inv[sku]['animus_avail'] += a
            inv[sku]['animus_committed'] += c
        elif 'ESPAGIRIA' in loc:
            inv[sku]['espagiria_avail'] += a
            inv[sku]['espagiria_unavail'] += u

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
MARGEN_IDEAL = 25
MARGEN_MIN = 20

# Factor g/u por SKU (basado en presentación)
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
    'RECN-2': 30, 'RECN-1': 15,
    'MAXLASH': 4.5,
    'GLOSSN': 10, 'GLOSSMERLOT': 10, 'GLOSSMALVA': 10, 'GLOSSPEACH': 10, 'Glossmocca': 10,
    'CRCUREA': 100,
    'ECENT': 30, 'EILU': 30,
}

# ─────────────────────────────────────────────────────────────────────
# 2) MATCHEO ROBUSTO PRODUCTO → SKU
# ─────────────────────────────────────────────────────────────────────
SKU_KEYWORDS = {
    'SAH':         ['SAH ', 'AH 1.5', 'HIDRATANTE DE ACIDO', 'HIDRATANTE DE ÁCIDO'],
    'TRIAC':       ['TRIAC ', 'TRIACTIVE 15', 'RETINOID 15', 'TRIAC –', 'TRIAC -', 'TRIAC_BATCH'],
    'TRIAC30':     ['TRIAC30', 'TRIACTIVE 30', 'RETINOID 30'],
    'NIA':         [' NIA ', 'NIACINAMIDA 30', 'NIACINAMIDA'],
    'NIA10':       ['NIA10', 'NIACINAMIDA 10'],
    'TRX':         [' TRX ', 'ILUMINADOR TRX 30', 'ILUMINADOR TRX', ' TRX –', 'TRX -'],
    'TRX10':       ['TRX10', 'TRX 10'],
    'CCAFE':       ['CCAFE', 'CAFEINA', 'CAFEÍNA'],
    'CMULP':       ['CMULP', 'CONTORNO MULTI', 'CONTORNO DE OJOS MULTI'],
    'CRETT':       ['CRETT', 'CONTORNO RETINAL', 'CONTORNO DE OJOS CON RETINAL'],
    'SMULPP':      ['SMULPP', 'SUERO MULTIPEPTIDOS', 'SUERO MULTIPÉPTIDOS', 'MULTIPEPTIDOS', 'MULTIPÉPTIDOS'],
    'BHA33':       ['BHA33', 'EXFOLIANTE BHA', 'SBHA'],
    'LBHA':        ['LBHA', 'LIMPIADOR BHA', 'LIMPIADOR FACIAL BHA'],
    'LKJ':         [' LKJ ', 'KOJICO', 'KÓJICO', 'LKJ –', 'LKJ -'],
    'LAH':         [' LAH ', 'LIMPIADOR HIDRATANTE', 'LAH –', 'LAH -'],
    'GELH':        ['GELH', 'GEL HIDRATANTE'],
    'EMLIM':       ['EMLIM', 'EMULSION LIMPIA', 'EMULSIÓN LIMPIA'],
    'CRB3BHA':     ['CRB3BHA', 'B3+BHA', 'B3 BHA', 'EMULSION B3', 'EMULSIÓN B3'],
    'HKJ':         [' HKJ ', 'EMULSION ILUMI', 'EMULSIÓN ILUMI', 'HKJ –', 'HKJ -'],
    'AZHC':        ['AZHC ', ' AZHC ', 'AZ HYBRID 15', 'HYBRID 15', 'HYBRID CLEAR 15'],
    'AZHC30':      ['AZHC30', 'AZ HYBRID 30', 'HYBRID 30', 'HYBRID CLEAR 30'],
    'NPHA30':      ['NPHA30', 'NOVA-PHA 30', 'NOVA PHA 30', 'NPHA 30', ' NPHA ', 'NPHA –', 'NPHA -'],
    'NPHA10':      ['NPHA10', 'NOVA-PHA 10', 'NPHA 10'],
    'SVITC33':     ['SVITC33', 'VITAMINA C 30', 'VIT C 30', 'SVITC30', 'SVITC '],
    'SVITC3315':   ['SVITC3315', 'VIT C 15', 'SVITC15'],
    'RECN-2':      ['RECN-2', 'RENOVA C10 30', 'RENOVA30', 'RECN ', 'RECN –', 'RECN -'],
    'MAXLASH':     ['MAXLASH', 'CEJAS', 'PESTAÑAS', 'PESTANAS'],
    'GLOSSN':      ['GLOSSN ', 'TRANSLUCIDO', 'TRANSLÚCIDO', 'GLOSSN –', 'GLOSSN -'],
    'GLOSSMERLOT': ['GLOSSMERLOT', 'MERLOT'],
    'GLOSSMALVA':  ['GLOSSMALVA', 'MALVA'],
    'GLOSSPEACH':  ['GLOSSPEACH', 'PEACH'],
    'Glossmocca':  ['GLOSSMOCCA', 'GLOSS MOCCA', ' MOCA'],
    'CRCUREA':     ['CRCUREA', 'UREA', 'BODY'],
    'ECENT':       ['ECENT', 'CENTELLA'],
    'EILU':        ['EILU', 'ESENCIA ILUMINADORA'],
}

def match_sku(text):
    t = ' ' + text.upper() + ' '
    # Mejor match: longest keyword wins
    matches = []
    for sku, keys in SKU_KEYWORDS.items():
        for k in keys:
            if k.upper() in t:
                matches.append((len(k), sku))
                break
    if matches:
        matches.sort(reverse=True)  # longest first
        return matches[0][1]
    return None

# ─────────────────────────────────────────────────────────────────────
# 3) PROCESAR EVENTOS — parsear cadencia, kg, unidades
# ─────────────────────────────────────────────────────────────────────
def parse_kg(text):
    # Busca patterns: "90 kg", "13kg", "~92 kg", "1.2 kg"
    matches = re.findall(r'~?\s*(\d+(?:[.,]\d+)?)\s*kg', text, re.IGNORECASE)
    if matches:
        try:
            return float(matches[0].replace(',', '.'))
        except: pass
    return None

def parse_unidades(text):
    # Patterns: "866 u", "1,000 u", "1200u"
    m = re.search(r'(\d[\d,\.]*)\s*u\b', text)
    if m:
        try:
            v = m.group(1).replace(',', '').replace('.', '')
            n = int(v)
            if 5 <= n <= 50000:
                return n
        except: pass
    return None

def parse_cadencia(text):
    # "c/90 días", "(90 días)", "cada 60 días", "(c/60 días)"
    patterns = [
        r'c/\s*(\d+)\s*d(?:í|i)?as',
        r'cada\s*(\d+)\s*d(?:í|i)?as',
        r'\(\s*(\d+)\s*d(?:í|i)?as\s*\)',
        r'trigger\s*(\d+)\s*d(?:í|i)?as',
        r'(\d+)\s*d(?:í|i)?as\s*\)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try: return int(m.group(1))
            except: pass
    return None

eventos = []
for e in cal:
    f = (e.get('start') or {}).get('date') or (e.get('start') or {}).get('dateTime', '')[:10]
    if not f: continue
    try: fd = datetime.strptime(f[:10], '%Y-%m-%d').date()
    except: continue
    summary = e.get('summary', '') or ''
    desc = e.get('description', '') or ''
    full = summary + '\n' + desc

    # Filtrar eventos de envasado/acondicionamiento (no son fabricacion del bulk)
    es_envasado = bool(re.search(r'envasad|micro\s*qc|acondicionamient', full, re.IGNORECASE))
    es_fabricacion = bool(re.search(r'fabricaci|fab\s*[—–-]|batch|lanzamient', full, re.IGNORECASE)) or not es_envasado

    sku = match_sku(full)
    kg = parse_kg(summary) or parse_kg(desc)
    u = parse_unidades(summary) or parse_unidades(desc)
    cadencia = parse_cadencia(summary) or parse_cadencia(desc)
    es_hecho = 'hecho' in full.lower() or '✅' in full
    eventos.append({
        'fecha': fd,
        'summary': summary,
        'description': desc,
        'sku': sku,
        'kg': kg,
        'unidades': u,
        'cadencia_declarada': cadencia,
        'es_envasado': es_envasado,
        'es_fabricacion': es_fabricacion and not es_envasado,
        'es_hecho': es_hecho,
    })

eventos.sort(key=lambda x: x['fecha'])

# ─────────────────────────────────────────────────────────────────────
# 4) AGRUPAR POR SKU — solo eventos de FABRICACION (no envasado)
# ─────────────────────────────────────────────────────────────────────
por_sku = defaultdict(list)
for e in eventos:
    if e['es_fabricacion'] and e['sku']:
        por_sku[e['sku']].append(e)

# ─────────────────────────────────────────────────────────────────────
# 5) PRODUCTOS HERMANOS (suman velocidad para cadencia bulk)
# ─────────────────────────────────────────────────────────────────────
HERMANOS = {
    'SAH':       ['SAH', 'SAH10'],
    'NIA':       ['NIA', 'NIA10'],
    'TRX':       ['TRX', 'TRX10'],
    'TRIAC':     ['TRIAC', 'TRIAC30'],
    'NPHA30':    ['NPHA30', 'NPHA10'],
    'AZHC':      ['AZHC', 'AZHC30'],
    'SVITC33':   ['SVITC33', 'SVITC3315'],
    'RECN-2':    ['RECN-1', 'RECN-2'],
}

def velocidad_total(sku_principal):
    """Velocidad combinada de hermanos."""
    if sku_principal in HERMANOS:
        skus = HERMANOS[sku_principal]
    else:
        skus = [sku_principal]
    total_v = sum(ventas.get(s, 0) for s in skus) / DIAS_VENTAS
    return total_v, skus

def stock_efectivo(sku_list):
    total = 0
    for s in sku_list:
        d = inv.get(s, {})
        total += d.get('animus_avail', 0) + d.get('espagiria_avail', 0) + d.get('espagiria_unavail', 0)
    return total

# ─────────────────────────────────────────────────────────────────────
# 6) ANÁLISIS POR SKU
# ─────────────────────────────────────────────────────────────────────
print('=' * 110)
print('ANALISIS DE CADENCIAS POR SKU - Calendar declarado vs Real vs Teorico')
print('=' * 110)

# SKUs líder de cada grupo (no incluir hermanos ml-pequeño en cadencia)
SKUS_LIDER = []
ya_visto = set()
for principal, skus in HERMANOS.items():
    SKUS_LIDER.append(principal)
    ya_visto.update(skus)
for sku in por_sku:
    if sku not in ya_visto:
        SKUS_LIDER.append(sku)

# Ordenar por urgencia (alcance ascendente)
def calc_alcance(sku):
    vel, skus = velocidad_total(sku)
    if vel < 0.05: return 9999
    return stock_efectivo(skus) / vel

SKUS_LIDER.sort(key=calc_alcance)

print()
print('{:13} {:>7} {:>5} {:>6} {:>6} {:>6} {:>5} {:>5} {:>5} {:>10}'.format(
    'SKU', 'Lote_kg', 'fg', 'u/lote', 'Vel/d', 'Stock', 'Alc', 'Cad-D', 'Cad-T', 'Verdict'))
print('-' * 110)

for sku in SKUS_LIDER:
    eventos_sku = por_sku.get(sku, [])
    # Lote típico: mediana de los kg en eventos pasados (hechos) o todos
    kgs_validos = sorted([e['kg'] for e in eventos_sku if e['kg']])
    if kgs_validos:
        lote_kg = kgs_validos[len(kgs_validos)//2]
    else:
        lote_kg = None

    # Cadencia declarada: moda de todas las cadencias que aparecen
    cads_declaradas = [e['cadencia_declarada'] for e in eventos_sku if e['cadencia_declarada']]
    cad_decl = None
    if cads_declaradas:
        from collections import Counter
        cad_decl = Counter(cads_declaradas).most_common(1)[0][0]

    # Cadencia real: gaps entre eventos consecutivos
    fechas = sorted(e['fecha'] for e in eventos_sku)
    gaps = []
    if len(fechas) >= 2:
        for i in range(1, len(fechas)):
            gaps.append((fechas[i] - fechas[i-1]).days)
    cad_real = sum(gaps)/len(gaps) if gaps else None

    # Cadencia teórica: stock_lote / velocidad - margen 20d
    fg = FACTOR_G.get(sku, 30)
    vel, skus_grupo = velocidad_total(sku)
    if lote_kg and vel > 0.05:
        u_lote = lote_kg * 1000 / fg
        cad_teorica = (u_lote / vel) - MARGEN_MIN
    else:
        u_lote = None
        cad_teorica = None

    stock = stock_efectivo(skus_grupo)
    alcance = stock / vel if vel > 0.05 else None

    # Verdict
    if cad_decl and cad_teorica:
        diff = cad_decl - cad_teorica
        if abs(diff) < 10:
            verdict = 'OK'
        elif diff > 0:
            verdict = 'ACORTAR ' + str(int(round(diff))) + 'd'
        else:
            verdict = 'ALARGAR ' + str(int(round(-diff))) + 'd'
    elif not cad_decl:
        verdict = 'sin cad declarada'
    elif not cad_teorica:
        verdict = 'sin datos suficientes'
    else:
        verdict = '?'

    print('{:13} {:>6}{:>1} {:>5} {:>6} {:>6.2f} {:>6} {:>5} {:>5} {:>5} {:>10}'.format(
        sku,
        ('%.0f' % lote_kg) if lote_kg else '-',
        'k' if lote_kg else '',
        fg if fg else '-',
        ('%.0f' % u_lote) if u_lote else '-',
        vel,
        stock,
        ('%.0f' % alcance) + 'd' if alcance else '—',
        ('%dd' % cad_decl) if cad_decl else '—',
        ('%.0fd' % cad_teorica) if cad_teorica else '—',
        verdict,
    ))

# ─────────────────────────────────────────────────────────────────────
# 7) DETALLE: cadencias declaradas vs reales (eventos consecutivos)
# ─────────────────────────────────────────────────────────────────────
print('\n' + '=' * 110)
print('DETALLE — gaps entre eventos consecutivos por SKU')
print('=' * 110)
for sku in SKUS_LIDER:
    eventos_sku = por_sku.get(sku, [])
    if len(eventos_sku) < 2: continue
    fechas = sorted([(e['fecha'], e['kg'], e['cadencia_declarada']) for e in eventos_sku])
    print('\n' + sku + ' (' + str(len(fechas)) + ' eventos):')
    print('  Fechas: ', end='')
    for i, (f, kg, cd) in enumerate(fechas):
        kg_s = (str(kg) + 'kg') if kg else '-'
        cd_s = ('c/' + str(cd) + 'd') if cd else ''
        if i > 0:
            gap = (fechas[i][0] - fechas[i-1][0]).days
            print(' [+' + str(gap) + 'd] ', end='')
        print(str(f) + ' (' + kg_s + ' ' + cd_s + ')', end='')
    print()
