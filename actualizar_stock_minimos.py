"""
Actualiza el stock mínimo de cada MP en el catalogo basado en:
- Plan anual de producciones del Google Calendar
- Fórmulas maestras
- Metodología: Consumo anual / 12 × 2 meses × 1.10 (buffer 10%)

Ejecutar: python actualizar_stock_minimos.py
"""
import json, time, sys

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

BASE_URL = "https://inventarios-0363.onrender.com"

print(f"\n{'='*60}")
print("ACTUALIZACIÓN STOCK MÍNIMO - Basado en Plan Anual")
print("Metodología: Consumo anual ÷ 12 × 2 meses × 1.10")
print(f"{'='*60}\n")

# Cargar mínimos calculados
try:
    with open("stock_minimos_calculados.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    minimos = data["minimos"]
    print(f"MPs con mínimo calculado: {len(minimos)}")
    print(f"Metodología: {data.get('metodologia','')}\n")
except FileNotFoundError:
    print("ERROR: No se encuentra stock_minimos_calculados.json")
    sys.exit(1)

# Despertar servidor
print("Conectando al servidor...")
for i in range(5):
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=60)
        if r.status_code == 200:
            print("Servidor activo\n"); break
    except: pass
    print(f"  Intento {i+1}/5..."); time.sleep(8)

# Actualizar stock_minimo en maestro_mps
ok = 0; no_cat = 0
print("Actualizando stock mínimos en el catálogo...")
for mp in minimos:
    codigo = mp['codigo_mp']
    minimo = mp['stock_minimo']

    # Primero verificar si existe en catálogo
    try:
        r = requests.get(f"{BASE_URL}/api/maestro-mps/{codigo}", timeout=15)
        if r.status_code == 200:
            mp_data = r.json()
            # Actualizar con el nuevo mínimo
            mp_data['stock_minimo'] = minimo
            r2 = requests.post(f"{BASE_URL}/api/maestro-mps",
                              json=mp_data, timeout=20)
            if r2.status_code in [200, 201]:
                ok += 1
        else:
            no_cat += 1  # No está en catálogo aún
    except Exception as e:
        print(f"  Error {codigo}: {e}")
    time.sleep(0.05)

print(f"\n{'='*60}")
print(f"COMPLETADO")
print(f"  Actualizados: {ok} MPs")
print(f"  Sin catálogo: {no_cat} MPs (cargar maestro primero)")
print(f"{'='*60}")
print(f"\nTop 10 MPs con mayor mínimo:")
for m in minimos[:10]:
    print(f"  {m['codigo_mp']:<12} {m['nombre'][:28]:<28} mín: {m['stock_minimo']:>8,.0f}g = {m['stock_minimo']/1000:.1f}kg")
print(f"\nApp: {BASE_URL}")
