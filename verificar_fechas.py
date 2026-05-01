"""Verifica que ninguna ocurrencia caiga en sábado, domingo o festivo Colombia."""
import sys, io
from datetime import date, timedelta
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Festivos Colombia 2026-2028
FESTIVOS = {
    # 2026
    date(2026,5,1), date(2026,5,18), date(2026,6,8), date(2026,6,15),
    date(2026,6,29), date(2026,7,20), date(2026,8,7), date(2026,8,17),
    date(2026,10,12), date(2026,11,2), date(2026,11,16), date(2026,12,8), date(2026,12,25),
    # 2027
    date(2027,1,1), date(2027,1,11), date(2027,3,22), date(2027,3,25), date(2027,3,26),
    date(2027,5,1), date(2027,5,10), date(2027,5,31), date(2027,6,7), date(2027,7,5),
    date(2027,7,20), date(2027,8,7), date(2027,8,16), date(2027,10,18), date(2027,11,1),
    date(2027,11,15), date(2027,12,8), date(2027,12,25),
    # 2028
    date(2028,1,1), date(2028,1,10), date(2028,3,20), date(2028,4,13), date(2028,4,14),
    date(2028,5,1), date(2028,5,29), date(2028,6,19), date(2028,6,26), date(2028,7,3),
    date(2028,7,20), date(2028,8,7), date(2028,8,21),
}

# Plan según los 31 eventos creados
PLAN = [
    ('LKJ',         date(2026,5,4),  60, 12),
    ('BBM',         date(2026,5,4),  90, 8),
    ('HKJ',         date(2026,5,6),  60, 12),
    ('HYDRAP',      date(2026,5,6),  70, 11),
    ('HYDRABAL',    date(2026,5,7),  70, 11),
    ('GELH',        date(2026,5,7),  45, 16),
    ('EMLIM',       date(2026,5,11), 60, 12),
    ('AZHC',        date(2026,5,11), 60, 12),
    ('CRCUREA',     date(2026,5,13), 60, 12),
    ('MAXLASH',     date(2026,5,13), 90, 8),
    ('GLOSSMALVA',  date(2026,5,14), 70, 11),
    ('SMULPP',      date(2026,5,20), 30, 24),
    ('LBHA',        date(2026,5,21), 45, 16),
    ('TRIAC',       date(2026,6,1),  30, 24),
    ('SVITC',       date(2026,6,1),  45, 16),
    ('LAH',         date(2026,6,3),  60, 12),
    ('GLOSSPEACH',  date(2026,6,3),  70, 11),
    ('GLOSSMERLOT', date(2026,6,4),  70, 11),
    ('RECN',        date(2026,6,4),  60, 12),
    ('BHA',         date(2026,6,17), 90, 8),
    ('TRX',         date(2026,6,18), 90, 8),
    ('CMULP',       date(2026,6,18), 60, 12),
    ('CRB3BHA',     date(2026,7,1),  60, 12),
    ('NIA',         date(2026,7,2),  90, 8),
    ('ECENT',       date(2026,7,2),  90, 8),
    ('SAH',         date(2026,7,9),  70, 11),
    ('CCAFE',       date(2026,7,9),  60, 12),
    ('NPHA',        date(2026,7,16), 60, 12),
    ('EILU',        date(2026,7,16), 90, 8),
    ('CRETT',       date(2026,7,23), 90, 8),
    ('GLOSSMOCCA',  date(2026,8,6),  90, 8),
]

def es_problema(d):
    if d.weekday() == 5: return 'SÁBADO'
    if d.weekday() == 6: return 'DOMINGO'
    if d in FESTIVOS: return 'FESTIVO'
    return None

print('='*80)
print('VERIFICACIÓN DE FECHAS — ¿Caen sábado/domingo/festivo?')
print('='*80)

total_ocurrencias = 0
total_problemas = 0
problemas_por_sku = {}
NOMBRES_DIA = ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']

for sku, primera, cad, count in PLAN:
    problemas = []
    for i in range(count):
        d = primera + timedelta(days=i*cad)
        total_ocurrencias += 1
        problema = es_problema(d)
        if problema:
            problemas.append((d, problema, NOMBRES_DIA[d.weekday()]))
            total_problemas += 1
    if problemas:
        problemas_por_sku[sku] = problemas

print(f'\nTotal ocurrencias: {total_ocurrencias}')
print(f'Total problemas:   {total_problemas}')
print(f'Productos afectados: {len(problemas_por_sku)} de {len(PLAN)}')
print()

if problemas_por_sku:
    print('PROBLEMAS DETECTADOS:')
    print('-'*80)
    for sku, probs in problemas_por_sku.items():
        print(f'\n{sku}: {len(probs)} ocurrencias mal')
        for d, motivo, dia in probs[:5]:
            # Sugerir nueva fecha (siguiente L/Mi/J no festivo)
            nueva = d
            for _ in range(7):
                nueva = nueva + timedelta(days=1)
                if nueva.weekday() in (0,2,3) and nueva not in FESTIVOS:
                    break
            print(f'  ❌ {d} ({dia}) {motivo}  →  mover a {nueva} ({NOMBRES_DIA[nueva.weekday()]})')
        if len(probs) > 5:
            print(f'  ... y {len(probs)-5} más')
