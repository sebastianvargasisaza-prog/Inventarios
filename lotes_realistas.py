"""Lotes realistas con MAX kg histórico + cadencia preferida.

Reglas Sebastián:
  - Máximo lote físico ya hecho: 200 kg (LBHA, también probable techo en otros)
  - Algunos productos cada 30 días, otros cada 60 días
  - Si lote óptimo > max histórico, hacer lotes a max y aceptar cadencia más corta
"""
import csv, sys, io
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Velocidades bulk g/d (de mi cálculo anterior, ya validadas)
VEL_G = {
    'SAH': 898,        # SAH+SAH10 sin regalo
    'NIA': 1065,
    'TRX': 927,         # sin regalo
    'TRIAC': 316,
    'NPHA': 147,
    'AZHC': 412,
    'SVITC': 414,
    'RECN': 248,
    'BHA': 495,
    'CCAFE': 101,
    'CMULP': 105,
    'CRETT': 121,
    'SMULPP': 726,
    'LBHA': 5106,       # con Fernando 500u/90d
    'LAH': 1018,
    'LKJ': 1964,
    'EMLIM': 1065,
    'GELH': 751,        # con Fernando 300u/90d
    'CRB3BHA': 347,
    'HKJ': 228,
    'MAXLASH': 18,
    'GLOSSN': 48,
    'GLOSSMERLOT': 26,
    'GLOSSMALVA': 34,
    'GLOSSPEACH': 25,
    'CRCUREA': 821,     # con Fernando 500u/90d
    'ECENT': 311,       # con Fernando 500u/90d
    'EILU': 5,
}

# Cadencias preferidas por Sebastián (algunos cada mes, otros cada 60d)
CADENCIA_PREFERIDA = {
    'SAH': 90,    # core, lote grande, gusta c/90d
    'NIA': 90,
    'TRX': 90,
    'BHA': 90,
    'LBHA': 30,   # alta rotación
    'LKJ': 60,
    'EMLIM': 60,
    'LAH': 60,
    'GELH': 45,
    'HKJ': 60,
    'CRB3BHA': 60,
    'AZHC': 60,
    'NPHA': 60,
    'SVITC': 45,
    'RECN': 60,
    'TRIAC': 30,
    'CMULP': 60,
    'CRETT': 60,
    'CCAFE': 60,
    'SMULPP': 30,
    'MAXLASH': 90,
    'GLOSSN': 60,
    'GLOSSMERLOT': 70,
    'GLOSSMALVA': 70,
    'GLOSSPEACH': 70,
    'CRCUREA': 60,
    'ECENT': 90,
    'EILU': 90,  # post-reactivación, ajustar luego
}

# Lote máximo histórico observado (kg) — necesito que Sebastián confirme
MAX_LOTE = {
    'LBHA': 200,
    # Resto: asumo no hay límite si no me dice, usar lote óptimo
}

MARGEN_MIN = 20
MARGEN_IDEAL = 25

print('═'*100)
print('LOTES REALISTAS — con cadencia preferida + límite físico')
print('═'*100)
print()
print('{:13} {:>6} {:>9} {:>10} {:>10} {:>10} {:>15}'.format(
    'SKU', 'Cad', 'Vel g/d', 'Lote óptimo', 'Lote real', 'Lote dura', 'Verdict'))
print('-' * 100)

filas = []
for sku, vel in VEL_G.items():
    cad = CADENCIA_PREFERIDA.get(sku, 60)
    # Lote óptimo en kg para esa cadencia + margen 25d
    lote_opt_kg = (cad + MARGEN_IDEAL) * vel / 1000
    # Lote real considerando límite físico
    lote_max = MAX_LOTE.get(sku, 999)
    lote_real_kg = min(lote_opt_kg, lote_max)
    # Días que dura el lote real
    lote_dura = (lote_real_kg * 1000) / vel
    # Cadencia REAL alcanzable
    cad_real = lote_dura - MARGEN_IDEAL
    # Verdict
    if lote_real_kg < lote_opt_kg - 5:
        verdict = f'ajustar c/{round(cad_real)}d'
    else:
        verdict = 'OK c/' + str(cad) + 'd ✓'
    filas.append((sku, cad, vel, lote_opt_kg, lote_real_kg, lote_dura, cad_real, verdict))

# Ordenar por velocidad descendente (los más críticos arriba)
filas.sort(key=lambda x: -x[2])
for sku, cad, vel, opt, real, dura, cad_real, verdict in filas:
    print('{:13} {:>5}d {:>7.0f} g/d {:>7.0f} kg {:>7.0f} kg {:>7.0f}d {:>15}'.format(
        sku, cad, vel, opt, real, dura, verdict))

print()
print('Lote óptimo = (cadencia + margen 25d) × velocidad / 1000')
print('Lote real = min(óptimo, máximo físico)')

# Casos críticos
print('\n' + '═'*80)
print('CASOS QUE NO CUMPLEN cadencia preferida (lote insuficiente)')
print('═'*80)
print()
for sku, cad, vel, opt, real, dura, cad_real, verdict in filas:
    if abs(real - opt) > 5:
        print(f'  {sku:13} querías c/{cad}d  →  con lote {real:.0f}kg solo alcanza c/{cad_real:.0f}d')
        print(f'                    Para c/{cad}d necesitarías lote {opt:.0f}kg (vs max {MAX_LOTE.get(sku,"sin límite")}kg)')

# Lo que pediría a Sebastián confirmar
print('\n' + '═'*80)
print('CAPACIDAD MÁXIMA — necesito que confirmes para cada SKU')
print('═'*80)
print()
print('Estos son los lotes "ideales" según mi cálculo. Confirma cuáles SÍ se pueden hacer:')
print()
print('{:13} {:>10} {:>15}'.format('SKU', 'Lote ideal', '¿Físicamente posible?'))
print('-' * 50)
for sku, cad, vel, opt, real, dura, cad_real, verdict in filas:
    if opt > 50:  # solo los grandes son los que importan
        print(f'  {sku:13} {opt:>7.0f} kg  → ?')
