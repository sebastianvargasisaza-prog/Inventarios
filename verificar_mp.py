"""Verifica si hay MP suficiente para los lotes de la próxima semana."""
import json, csv, sys, io
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 1) Stock MP del Excel (g por código)
mp_stock = defaultdict(lambda: {'nombre':'', 'total_g':0, 'lotes':[]})
with open(r'C:\Users\sebas\Downloads\Stock_2026-4-30.csv', 'r', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        cod = r.get('Codigo','').strip()
        nom = r.get('Nombre','').strip()
        try: cant = float(r.get('Cantidad_g') or 0)
        except: cant = 0
        estado = r.get('Estado','').lower()
        if estado == 'vencido':  # no contar vencidos
            continue
        mp_stock[cod]['nombre'] = nom
        mp_stock[cod]['total_g'] += cant
        mp_stock[cod]['lotes'].append((r.get('Lote',''), cant, estado))

# 2) Fórmulas
with open('archive/data-imports/formulas_data.json', 'r', encoding='utf-8') as f:
    formulas = json.load(f)

# Mapa nombre producto → fórmula
formula_map = {f['producto_nombre'].upper().strip(): f for f in formulas}

print(f'Total fórmulas en JSON: {len(formulas)}')
print(f'Total MP códigos en stock: {len(mp_stock)}\n')

# 3) Lotes de la próxima semana 4-8 mayo (con tamaños propuestos AJUSTADOS)
LOTES_SEMANA = [
    # (producto_nombre_clave, kg_lote, nota)
    ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 167, 'LKJ'),
    ('EMULSION HIDRATANTE ILUMINADORA', 19, 'HKJ'),
    ('EMULSION LIMPIADORA', 91, 'EMLIM'),
    ('GEL HIDRATANTE', 53, 'GELH'),
    ('SUERO AZ HYBRID CLEAR', 35, 'AZHC'),
    ('SUERO TRIACTIVE RETINOID', 17, 'TRIAC'),
    # Lanzamientos
    ('HYDRA PEPTIDE', 30, 'HYDRAP - reemplaza CRB3BHA'),
    ('HYDRA BALANCE', 30, 'HYDRABAL - reemplaza mascarilla hidratante'),
    ('BUSH BALM', 1, 'BBM'),
    ('LIP SERUM', 3, 'GLOSS MALVA'),
]

def buscar_formula(nombre_clave):
    """Busca formula por match parcial."""
    n = nombre_clave.upper().strip()
    # Match exacto
    if n in formula_map:
        return formula_map[n]
    # Match parcial: contiene palabras clave
    candidates = []
    for k, v in formula_map.items():
        if all(w in k for w in n.split() if len(w) > 3):
            candidates.append((k, v))
    if candidates:
        # Mejor: el más corto (más específico)
        candidates.sort(key=lambda x: len(x[0]))
        return candidates[0][1]
    return None

print('═' * 100)
print('VERIFICACIÓN MP — Lotes propuestos próxima semana')
print('═' * 100)

resumen_global = defaultdict(float)  # código → total g requerido

for prod_nom, kg_lote, nota in LOTES_SEMANA:
    f = buscar_formula(prod_nom)
    if not f:
        print(f'\n[!!] {prod_nom} ({nota}, {kg_lote} kg)')
        print(f'     ⚠️  Sin fórmula encontrada en JSON')
        continue

    print(f'\n▌ {prod_nom} ({nota}) · lote {kg_lote} kg')
    print(f'  Fórmula: {f["producto_nombre"]} ({f["descripcion"]})')

    items = f.get('items', [])
    total_g_lote = kg_lote * 1000
    falta_total = []
    ok_count = 0
    proximo_count = 0
    for item in items:
        mp_id = item.get('material_id')
        mp_nom = item.get('material_nombre','')
        pct = item.get('porcentaje', 0)
        g_req = total_g_lote * pct / 100
        resumen_global[mp_id] += g_req
        stock = mp_stock.get(mp_id, {})
        stock_g = stock.get('total_g', 0)
        if stock_g >= g_req:
            ok_count += 1
        elif stock_g >= g_req * 0.9:
            proximo_count += 1
        else:
            falta = g_req - stock_g
            falta_total.append((mp_id, mp_nom, g_req, stock_g, falta))
    if not falta_total:
        print(f'  ✅ MP OK para todo el lote ({ok_count} ingredientes)')
    else:
        print(f'  ⚠️  FALTA MP en {len(falta_total)} ingredientes:')
        for mp_id, mp_nom, req, stock, falta in falta_total[:5]:
            print(f'     - {mp_id} {mp_nom[:40]}: necesito {req:.0f}g, tengo {stock:.0f}g, FALTA {falta:.0f}g')

# Resumen global
print('\n' + '═' * 80)
print('RESUMEN MP CRÍTICAS — los 15 ingredientes con menos margen')
print('═' * 80)
analisis = []
for mp_id, g_req in resumen_global.items():
    stock = mp_stock.get(mp_id, {})
    g_disp = stock.get('total_g', 0)
    if g_req > 0:
        margen = g_disp - g_req
        ratio = g_disp / g_req if g_req > 0 else 99
        analisis.append((mp_id, stock.get('nombre','?'), g_req, g_disp, margen, ratio))

analisis.sort(key=lambda x: x[5])  # menor ratio = más crítico
print(f'{"Código":12} {"Nombre":35} {"Req":>9} {"Stock":>9} {"Margen":>9} {"Ratio":>6}')
print('-' * 90)
for mp_id, nom, req, stock, margen, ratio in analisis[:15]:
    flag = '🔴' if ratio < 1 else '🟡' if ratio < 1.3 else '🟢'
    print(f'{mp_id:12} {nom[:35]:35} {req:>7.0f}g {stock:>7.0f}g {margen:>7.0f}g {ratio:>5.1f}× {flag}')

# MP vencidas o próximas a vencer
print('\n' + '═' * 80)
print('MP VENCIDAS o PRÓXIMAS — alerta')
print('═' * 80)
with open(r'C:\Users\sebas\Downloads\Stock_2026-4-30.csv', 'r', encoding='utf-8') as f:
    vencidos = []
    proximos = []
    for r in csv.DictReader(f):
        if r.get('Estado','').lower() == 'vencido':
            vencidos.append((r.get('Codigo'), r.get('Nombre'), r.get('Lote'), r.get('Cantidad_g'), r.get('FechaVenc')))
        elif r.get('Estado','').lower() == 'proximo':
            proximos.append((r.get('Codigo'), r.get('Nombre'), r.get('Lote'), r.get('Cantidad_g'), r.get('FechaVenc')))

print(f'\nVENCIDOS ({len(vencidos)}):')
for v in vencidos: print(f'  {v[0]} {v[1][:40]:40} lote {v[2]} ({v[3]}g) venció {v[4]}')

print(f'\nPRÓXIMOS A VENCER ({len(proximos)}):')
for v in proximos[:10]: print(f'  {v[0]} {v[1][:40]:40} lote {v[2]} ({v[3]}g) vence {v[4]}')
