"""
Carga las 28 formulas maestras a inventarios-0363.onrender.com
Ejecutar: python cargar_formulas.py
"""
import json, time, sys

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

BASE_URL = "https://inventarios-0363.onrender.com"

with open("formulas_data.json", "r", encoding="utf-8") as f:
    formulas = json.load(f)

print(f"\n{'='*55}")
print(f"CARGA DE FORMULAS MAESTRAS - ANIMUS Lab")
print(f"{'='*55}")
print(f"Formulas a cargar: {len(formulas)}")
print(f"Servidor: {BASE_URL}\n")

print("Conectando (puede tardar 30-50s si el servidor esta dormido)...")
try:
    r = requests.get(f"{BASE_URL}/api/health", timeout=60)
    print(f"Servidor activo: {r.status_code}\n")
except Exception as e:
    print(f"Error conectando: {e}")
    sys.exit(1)

ok = 0
for i, formula in enumerate(formulas, 1):
    try:
        r = requests.post(f"{BASE_URL}/api/formulas",
                          json=formula, timeout=20)
        if r.status_code == 201:
            ok += 1
            total_pct = sum(it['porcentaje'] for it in formula['items'])
            print(f"  [{i:02d}/28] OK  {formula['producto_nombre'][:40]} ({len(formula['items'])} MPs | {total_pct:.1f}%)")
        else:
            print(f"  [{i:02d}/28] ERR {formula['producto_nombre']}: {r.text[:60]}")
    except Exception as e:
        print(f"  [{i:02d}/28] ERR {formula['producto_nombre']}: {e}")
    time.sleep(0.1)

print(f"\n{'='*55}")
print(f"COMPLETADO: {ok}/28 formulas cargadas")
print(f"{'='*55}")
print(f"\nAbre tu app: {BASE_URL}")
print("Ve a la pestana 'Formulas' para verlas")
print("Ve a 'Produccion' para registrar un batch con descuento automatico")
