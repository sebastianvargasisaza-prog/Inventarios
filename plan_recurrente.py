"""Plan de eventos RECURRENTES - 1 por SKU activo, repetición automática 2 años.

Cada SKU tiene:
  - Primera fecha (calculada según alcance hoy + lote pipeline)
  - Lote en kg
  - Cadencia en días (cuándo repetir)
  - Patrón: lunes/miércoles/jueves preferentemente, evitando festivos
"""
import csv, sys, io
from datetime import date, timedelta
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HOY = date(2026, 4, 30)

# Festivos Colombia 2026-2028 (los principales)
FESTIVOS = {
    date(2026,5,1), date(2026,5,18), date(2026,6,8), date(2026,6,15),
    date(2026,6,29), date(2026,7,20), date(2026,8,7), date(2026,8,17),
    date(2026,10,12), date(2026,11,2), date(2026,11,16), date(2026,12,8), date(2026,12,25),
    date(2027,1,1), date(2027,1,11), date(2027,3,22), date(2027,3,25), date(2027,3,26),
    date(2027,5,1), date(2027,5,10), date(2027,5,31), date(2027,6,7), date(2027,7,5),
    date(2027,7,20), date(2027,8,7), date(2027,8,16), date(2027,10,18), date(2027,11,1),
    date(2027,11,15), date(2027,12,8), date(2027,12,25),
    date(2028,1,1), date(2028,1,10), date(2028,3,20), date(2028,4,13), date(2028,4,14),
    date(2028,5,1), date(2028,5,29), date(2028,6,19), date(2028,6,26), date(2028,7,3),
    date(2028,7,20), date(2028,8,7), date(2028,8,21),
}

def proxima_lmj(desde_fecha):
    """Próximo lunes/miércoles/jueves no festivo."""
    f = desde_fecha
    DIAS_PREFERIDOS = (0, 2, 3)  # Mon, Wed, Thu
    DIAS_VALIDOS = (0, 1, 2, 3, 4)  # L-V
    for _ in range(60):
        if f.weekday() in DIAS_PREFERIDOS and f not in FESTIVOS:
            return f
        f += timedelta(days=1)
    # fallback: cualquier L-V
    f = desde_fecha
    for _ in range(60):
        if f.weekday() in DIAS_VALIDOS and f not in FESTIVOS:
            return f
        f += timedelta(days=1)
    return f

# DEFINICIÓN DEL PLAN: cada SKU con sus parámetros
# (sku, producto, lote_kg, cadencia_dias, primera_fecha_sugerida, notas)
# La primera fecha se calcula según urgencia (alcance hoy)
# Los datos vienen de mi tabla maestra validada

PLAN = [
    # URGENTES esta semana (4-8 may)
    {'grupo':'LKJ','producto':'Limpiador Iluminador Ácido Kójico','lote_kg':167,'cadencia':60,'primera':date(2026,5,4),'tag':'🌿','nota':'Animus 100% · Lote típico 160-167 kg'},
    {'grupo':'BBM','producto':'Bush Balm (lanzamiento)','lote_kg':1,'cadencia':90,'primera':date(2026,5,4),'tag':'🆕','nota':'PRIMER LOTE · sin historial · revisar tras ventas'},
    {'grupo':'HKJ','producto':'Emulsión Hidratante Iluminadora','lote_kg':19,'cadencia':60,'primera':date(2026,5,5),'tag':'💡','nota':'Animus 100% · NO se hizo el 30-abr'},
    {'grupo':'HYDRAP','producto':'Hydra Peptide (lanzamiento)','lote_kg':30,'cadencia':70,'primera':date(2026,5,5),'tag':'🆕','nota':'PRIMER LOTE · reemplaza CRB3BHA · 50ml · revisar MP'},
    {'grupo':'HYDRABAL','producto':'Hydra Balance (lanzamiento)','lote_kg':30,'cadencia':70,'primera':date(2026,5,7),'tag':'🆕','nota':'PRIMER LOTE · reemplaza mascarilla hidratante · 50ml · revisar MP Puresil ORG01'},
    {'grupo':'GELH','producto':'Gel Hidratante','lote_kg':53,'cadencia':45,'primera':date(2026,5,7),'tag':'🧴','nota':'+ Fernando Mesa 300u trimestral'},
    {'grupo':'EMLIM','producto':'Emulsión Limpiadora','lote_kg':91,'cadencia':60,'primera':date(2026,5,8),'tag':'🧴','nota':'Animus 100%'},
    {'grupo':'GLOSSMALVA','producto':'Lip Sérum Voluminizador Malva','lote_kg':3,'cadencia':70,'primera':date(2026,5,14),'tag':'💋','nota':'Animus 100%'},
    {'grupo':'AZHC','producto':'Suero AZ Hybrid Clear (15+30 ml)','lote_kg':35,'cadencia':60,'primera':date(2026,5,11),'tag':'🧴','nota':'+ Fernando Mesa 200u · cubre AZHC15+AZHC30 · MP pendiente'},
    {'grupo':'TRIAC','producto':'Suero Triactive Retinoid+NAD','lote_kg':17,'cadencia':30,'primera':date(2026,6,1),'tag':'🔬','nota':'Animus 100% · alcance hoy 63d'},

    # MEDIANOS (alcance 25-50d)
    {'grupo':'CRCUREA','producto':'Crema Corporal ReNova Body (Urea)','lote_kg':70,'cadencia':60,'primera':date(2026,5,13),'tag':'🧴','nota':'+ Fernando Mesa 500u trimestral'},
    {'grupo':'MAXLASH','producto':'Suero Cejas y Pestañas','lote_kg':2,'cadencia':90,'primera':date(2026,5,13),'tag':'💄','nota':'Animus 100%'},
    {'grupo':'SVITC','producto':'Suero Vitamina C+ (FÓRMULA NUEVA, 30+15 ml)','lote_kg':29,'cadencia':45,'primera':date(2026,6,1),'tag':'🍊','nota':'Animus 100% · cubre SVITC33+SVITC3315'},
    {'grupo':'SMULPP','producto':'Suero Multipéptidos','lote_kg':30,'cadencia':30,'primera':date(2026,5,18),'tag':'🧬','nota':'Animus 100% · ciclo mensual fijo'},
    {'grupo':'LAH','producto':'Limpiador Facial Hidratante','lote_kg':87,'cadencia':60,'primera':date(2026,6,3),'tag':'🚿','nota':'Animus 100%'},
    {'grupo':'GLOSSPEACH','producto':'Lip Sérum Voluminizador Peach','lote_kg':2,'cadencia':70,'primera':date(2026,6,3),'tag':'💋','nota':'Animus 100%'},
    {'grupo':'GLOSSMERLOT','producto':'Lip Sérum Voluminizador Merlot','lote_kg':2,'cadencia':70,'primera':date(2026,6,4),'tag':'💋','nota':'Animus 100%'},
    {'grupo':'RECN','producto':'Suero Renova C10 (15+30 ml)','lote_kg':18,'cadencia':60,'primera':date(2026,6,4),'tag':'🧬','nota':'Animus 100% · cubre RECN-1+RECN-2'},

    # CÓMODOS (alcance 50-100d)
    {'grupo':'CRB3BHA','producto':'Emulsión Hidratante B3+BHA','lote_kg':33,'cadencia':60,'primera':date(2026,7,1),'tag':'🧴','nota':'⚠️ EVALUAR: posiblemente reemplazado por Hydra Peptide'},
    {'grupo':'CMULP','producto':'Contorno de Ojos Multipéptidos','lote_kg':9,'cadencia':60,'primera':date(2026,6,18),'tag':'👁️','nota':'Animus 100%'},
    {'grupo':'NIA','producto':'Suero Niacinamida (30+10 ml)','lote_kg':122,'cadencia':90,'primera':date(2026,7,2),'tag':'🔬','nota':'+ Fernando Mesa 300u trimestral · cubre NIA+NIA10'},
    {'grupo':'NPHA','producto':'Suero Exfoliante Nova-PHA (30+10 ml)','lote_kg':12,'cadencia':60,'primera':date(2026,7,16),'tag':'🧪','nota':'Animus 100% · cubre NPHA30+NPHA10 · revisar lote 10ml'},
    {'grupo':'CCAFE','producto':'Contorno de Ojos con Cafeína','lote_kg':10,'cadencia':60,'primera':date(2026,7,9),'tag':'☕','nota':'Animus 100%'},
    {'grupo':'BHA','producto':'Suero Exfoliante BHA 2% (30+10 ml)','lote_kg':57,'cadencia':90,'primera':date(2026,6,15),'tag':'🧪','nota':'+ Fernando Mesa 200u trimestral · cubre BHA33+BHA10'},
    {'grupo':'TRX','producto':'Suero Iluminador TRX (30+10 ml, regalo 1200)','lote_kg':107,'cadencia':90,'primera':date(2026,6,18),'tag':'✨','nota':'+ Fernando Mesa 300u trimestral · 1200 TRX10 fijas regalo'},
    {'grupo':'SAH','producto':'Suero Hidratante AH 1.5% (30+10 ml, regalo 1200)','lote_kg':103,'cadencia':70,'primera':date(2026,7,9),'tag':'💧','nota':'Animus 100% · 1200 SAH10 fijas regalo'},
    {'grupo':'CRETT','producto':'Contorno de Ojos con Retinal','lote_kg':14,'cadencia':90,'primera':date(2026,7,23),'tag':'🧪','nota':'Animus 100%'},

    # POR REVISAR
    {'grupo':'ECENT','producto':'Esencia Centella Asiática','lote_kg':36,'cadencia':90,'primera':date(2026,7,2),'tag':'🌿','nota':'+ Fernando Mesa 500u trimestral'},
    {'grupo':'EILU','producto':'Esencia Iluminadora (REACTIVADA)','lote_kg':10,'cadencia':90,'primera':date(2026,7,16),'tag':'💫','nota':'⚠️ POST-PAUSA SANITARIA · velocidad incierta · revisar 60 días'},
    {'grupo':'GLOSSMOCCA','producto':'Lip Sérum Voluminizador Mocca','lote_kg':2,'cadencia':90,'primera':date(2026,8,6),'tag':'💋','nota':'Animus 100% · alcance largo'},
]

# Ajustar primeras fechas a próximo L/Mi/J no festivo
print('═'*100)
print(f'PLAN RECURRENTE 2 AÑOS — {len(PLAN)} eventos (1 por SKU)')
print(f'Inicio: 4-may-2026 · Fin: ~30-abr-2028')
print('═'*100)

print(f'\n{"#":>2} {"SKU":13} {"Lote":>5} {"Cad":>5} {"1ra fecha":12} {"Día":4} {"Producto":50}')
print('-' * 100)
total_lotes_2anos = 0
for i, p in enumerate(PLAN, 1):
    primera = proxima_lmj(p['primera'])
    if primera != p['primera']:
        nota_ajuste = f' (ajustada de {p["primera"]})'
    else:
        nota_ajuste = ''
    p['primera_real'] = primera
    nombres_dia = ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']
    n_lotes_2a = (730 // p['cadencia'])
    total_lotes_2anos += n_lotes_2a
    print(f'{i:>2} {p["grupo"]:13} {p["lote_kg"]:>3}kg {p["cadencia"]:>3}d {str(primera):12} {nombres_dia[primera.weekday()]:4} {p["tag"]} {p["producto"][:46]:46}')

print(f'\nTOTAL eventos individuales (~720d / cadencia): {total_lotes_2anos}')

# Verificar conflictos: días con muchas producciones
print('\n' + '═'*60)
print('SIMULACIÓN — días con 2+ producciones en próximas 8 semanas')
print('═'*60)
ocupacion = defaultdict(list)
for p in PLAN:
    f = p['primera_real']
    for ciclo in range((56 // p['cadencia']) + 1):
        dia = f + timedelta(days=ciclo * p['cadencia'])
        if dia <= HOY + timedelta(days=56):
            ocupacion[dia].append(p['grupo'])

conflictos = [(d, skus) for d, skus in ocupacion.items() if len(skus) >= 2]
conflictos.sort()
if conflictos:
    print(f'  {len(conflictos)} días con 2+ SKUs (capacidad 2/día Mayerlin AM/PM = OK):')
    for d, skus in conflictos[:15]:
        flag = '✅ AM/PM' if len(skus) == 2 else f'⚠️ {len(skus)} SKUs (sobrepasa)'
        print(f'  {d} ({["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"][d.weekday()]}): {", ".join(skus)} {flag}')
else:
    print('  ✅ Ninguno · todos los días con 1 producción')
