"""ULTRATHINK V3 — SAH con TODAS las reglas correctas:
   - Available + Pipeline + Espagiria
   - 10ml regalo: 1200 fijas por lote
   - Fernando trimestral (sin info SAH específica, no aplica acá)
   - SAH no es B2B Fernando, solo Shopify

Y comparativa con regla "como esta" vs "como debería"."""
import csv, sys, io
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Datos
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
        if 'NIMUS' in loc:
            inv[sku]['animus_avail'] += a
        elif 'ESPAGIRIA' in loc:
            inv[sku]['esp_avail'] += a
            inv[sku]['esp_unavail'] += u

ventas = {}
with open(r'C:\Users\sebas\Downloads\Ventas totales por variante de producto - 2026-01-01 - 2026-04-30.csv', 'r', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        sku = (r.get('SKU de variante de producto') or '').strip()
        if not sku: continue
        try: u = int(r.get('Articulos netos vendidos') or r.get('Artículos netos vendidos') or 0)
        except: u = 0
        ventas[sku] = u

DIAS = 120
MARGEN_MIN = 20
MARGEN_IDEAL = 25

# Pipeline (lote hoy)
PIPE_SAH_30ML_KG = 78  # 90 kg total - 12 kg para SAH10 regalo
PIPE_SAH_30ML_U = int(PIPE_SAH_30ML_KG * 1000 / 30)  # 2600 u
PIPE_SAH_10ML_U = 1200  # fijas por regalo

print('═'*72)
print('SAH — análisis con regla 10ml regalo (1200 fijas por lote)')
print('═'*72)
print()

# SAH 30ml
print('▌ SAH 30 ml (presentación venta)')
print('─'*60)
sah30 = inv['SAH']
stock_sah30 = sah30['animus_avail'] + sah30['esp_avail'] + sah30['esp_unavail']
v_sah30 = ventas.get('SAH', 0)
vel_sah30 = v_sah30 / DIAS
print(f'  Stock Shopify (Available):        {sah30["animus_avail"]} u')
print(f'  Stock Espagiria (avail+unavail):  {sah30["esp_avail"] + sah30["esp_unavail"]} u')
print(f'  Pipeline lote 78 kg / 30g:        {PIPE_SAH_30ML_U} u (entra en ~7d)')
print(f'  ──────────────────────────────────')
print(f'  TOTAL efectivo SAH 30ml:          {stock_sah30 + PIPE_SAH_30ML_U} u')
print(f'  Vendido 4 meses (Shopify):        {v_sah30} u')
print(f'  Velocidad:                        {vel_sah30:.2f} u/d ({vel_sah30*30:.0f} u/mes)')
print(f'  Días alcance:                     {(stock_sah30 + PIPE_SAH_30ML_U) / vel_sah30:.1f} días')
print()

# SAH 10ml
print('▌ SAH 10 ml (regalo + venta esporádica)')
print('─'*60)
sah10 = inv['SAH10']
stock_sah10 = sah10['animus_avail'] + sah10['esp_avail'] + sah10['esp_unavail']
v_sah10 = ventas.get('SAH10', 0)
vel_sah10_venta = v_sah10 / DIAS
print(f'  Stock Shopify:                    {sah10["animus_avail"]} u')
print(f'  Stock Espagiria:                  {sah10["esp_avail"] + sah10["esp_unavail"]} u')
print(f'  Pipeline regalo (1200 fijas):     {PIPE_SAH_10ML_U} u (entra en ~7d)')
print(f'  ──────────────────────────────────')
print(f'  TOTAL efectivo SAH 10ml:          {stock_sah10 + PIPE_SAH_10ML_U} u')
print(f'  Vendido 4 meses (Shopify):        {v_sah10} u')
print(f'  Velocidad venta directa:          {vel_sah10_venta:.2f} u/d')
print(f'  + Regalo: 1200 cada cadencia → si cadencia ~80d → {1200/80:.1f} u/d')
print(f'  Velocidad combinada estimada:     {vel_sah10_venta + 1200/80:.2f} u/d')
print()

# Cálculo bulk del LOTE perfecto
print('═'*72)
print('CADENCIA óptima — bulk en gramos')
print('═'*72)
# Bulk consumido diariamente (g)
# = ventas_30ml × 30g + ventas_10ml × 10g + regalo_fijo_por_ciclo
# Asumimos cadencia X. Bulk en X días = vel_30 × X × 30 + vel_10 × X × 10 + 12000
# Quiero: bulk_consumido(X) = lote_kg × 1000 = 90000g
# 30g·29×X + 10g·3×X + 12000 = 90000
# 870X + 30X = 90000 - 12000
# 900X = 78000 → X = 87 días
bulk_diario_30ml = vel_sah30 * 30
bulk_diario_10ml_venta = vel_sah10_venta * 10
print(f'  Bulk consumido por venta SAH 30ml: {bulk_diario_30ml:.0f} g/día')
print(f'  Bulk consumido por venta SAH 10ml: {bulk_diario_10ml_venta:.0f} g/día')
print(f'  Bulk fijo regalo 10ml por lote:    12 000 g (1 200 u × 10g)')
print()

LOTE_KG = 90
print(f'  Lote planeado:                    {LOTE_KG} kg = {LOTE_KG*1000} g')
print(f'  Bulk para regalo (fijo):          12 000 g')
print(f'  Bulk para venta:                  {LOTE_KG*1000 - 12000} g')
print()
# Cadencia X tal que bulk venta diario × X = bulk_para_venta
bulk_venta_diario = bulk_diario_30ml + bulk_diario_10ml_venta
cadencia_optima = (LOTE_KG*1000 - 12000) / bulk_venta_diario
cadencia_min = cadencia_optima - MARGEN_MIN
cadencia_ideal = cadencia_optima - MARGEN_IDEAL
print(f'  Bulk venta diario total:          {bulk_venta_diario:.0f} g/día')
print(f'  Días que dura el lote:            {cadencia_optima:.0f} días')
print(f'  Cadencia con margen 20d:          {cadencia_min:.0f} días entre lotes')
print(f'  Cadencia con margen 25d (ideal):  {cadencia_ideal:.0f} días entre lotes')
print()

# Comparación
print('▌ Comparación con cadencia declarada Calendar')
print('─'*60)
CADENCIA_CALENDAR = 90
print(f'  Calendar dice:    cada {CADENCIA_CALENDAR} días')
print(f'  Cálculo real:     cada {cadencia_min:.0f}-{cadencia_optima:.0f} días')
diff = CADENCIA_CALENDAR - cadencia_min
if diff > 5:
    print(f'  Verdict: ⚠️  c/90d es DEMASIADO LARGO. Toca acortar a c/{cadencia_min:.0f}d (margen 20d).')
elif diff < -5:
    print(f'  Verdict: ✅ c/90d sobra, podría alargar a c/{cadencia_optima:.0f}d')
else:
    print(f'  Verdict: ✅ c/90d cuadra')

# Próxima fecha
from datetime import date, timedelta
ULTIMO_LOTE = date(2026, 4, 30)
print()
print('▌ Próxima producción SAH (con lote hoy 30-abr)')
print('─'*60)
prox_optima = ULTIMO_LOTE + timedelta(days=int(cadencia_min))
prox_ideal = ULTIMO_LOTE + timedelta(days=int(cadencia_ideal))
print(f'  Si margen 20d → próximo lote: {prox_optima} ({(prox_optima-ULTIMO_LOTE).days}d después)')
print(f'  Si margen 25d → próximo lote: {prox_ideal} ({(prox_ideal-ULTIMO_LOTE).days}d después)')
