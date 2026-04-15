"""
Carga el catálogo maestro de MPs desde maestro_data.json
(Código MP, Nombre INCI, Nombre Comercial, Tipo, Proveedor, Stock mínimo)
Ejecutar: python cargar_maestro.py
"""
import json, time, sys

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

BASE_URL = "https://inventarios-0363.onrender.com"

print(f"\n{'='*55}")
print("CARGA CATÁLOGO MAESTRO MPs - ÁNIMUS Lab")
print(f"{'='*55}\n")

# Leer JSON generado
try:
    with open("maestro_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    mps = data["mps"]
    print(f"MPs en catálogo: {len(mps)}")
    print(f"Con INCI: {sum(1 for m in mps if m.get('nombre_inci'))}")
except FileNotFoundError:
    print("ERROR: No se encuentra maestro_data.json"); sys.exit(1)

# Despertar servidor
print("\nConectando al servidor...")
for i in range(5):
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=60)
        if r.status_code == 200:
            print("Servidor activo\n"); break
    except: pass
    print(f"  Intento {i+1}/5..."); time.sleep(8)

# Cargar catálogo
ok = 0
for mp in mps:
    try:
        r = requests.post(f"{BASE_URL}/api/maestro-mps", json=mp, timeout=20)
        if r.status_code in [200, 201]:
            ok += 1
    except Exception as e:
        print(f"  Error {mp['codigo_mp']}: {e}")
    time.sleep(0.05)

print(f"Catálogo cargado: {ok}/{len(mps)} MPs con INCI, tipo y proveedor")
print(f"\nApp: {BASE_URL}")
