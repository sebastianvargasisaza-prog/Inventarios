"""
Script para cargar inventario inicial desde Excel a la aplicación en producción.
Ejecutar en PowerShell: python cargar_inventario.py
"""
import json
import time
import sys

try:
    import requests
except ImportError:
    print("Instalando requests...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

BASE_URL = "https://inventarios-0363.onrender.com"

# Cargar datos procesados
with open("inventario_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

movimientos = data["movimientos"]
alertas = data["alertas"]

print(f"\n{'='*50}")
print(f"CARGA DE INVENTARIO - ÁNIMUS Lab")
print(f"{'='*50}")
print(f"Movimientos a cargar: {len(movimientos)}")
print(f"Alertas a registrar:  {len(alertas)}")
print(f"Servidor: {BASE_URL}\n")

# Despertar servidor
print("Conectando al servidor (puede tardar 30-50s si está dormido)...")
try:
    r = requests.get(f"{BASE_URL}/api/health", timeout=60)
    print(f"✓ Servidor activo: {r.status_code}\n")
except Exception as e:
    print(f"✗ Error conectando: {e}")
    sys.exit(1)

# Cargar movimientos en lotes de 20
print("Cargando inventario...")
ok = 0
errores = 0
total = len(movimientos)

for i, mov in enumerate(movimientos):
    try:
        r = requests.post(f"{BASE_URL}/api/movimientos", json=mov, timeout=15)
        if r.status_code == 201:
            ok += 1
        else:
            errores += 1
            print(f"  ✗ Error en {mov['material_id']}: {r.text[:80]}")
    except Exception as e:
        errores += 1
        print(f"  ✗ Error en {mov['material_id']}: {e}")

    # Progreso cada 50
    if (i + 1) % 50 == 0:
        print(f"  → {i+1}/{total} cargados ({ok} exitosos, {errores} errores)")

    # Pequeña pausa para no saturar
    time.sleep(0.05)

print(f"\n✓ Movimientos: {ok}/{total} cargados exitosamente")

# Cargar alertas
print(f"\nRegistrando {len(alertas)} alertas de vencimiento/stock...")
ok_alertas = 0
for alerta in alertas:
    try:
        r = requests.post(f"{BASE_URL}/api/alertas", json=alerta, timeout=15)
        if r.status_code == 201:
            ok_alertas += 1
    except Exception as e:
        print(f"  ✗ Error alerta {alerta['material_id']}: {e}")

print(f"✓ Alertas: {ok_alertas}/{len(alertas)} registradas")

print(f"\n{'='*50}")
print("¡CARGA COMPLETADA!")
print(f"{'='*50}")
print(f"✓ {ok} lotes de inventario cargados")
print(f"✓ {ok_alertas} alertas registradas")
print(f"\nAbre tu dashboard: {BASE_URL}")
