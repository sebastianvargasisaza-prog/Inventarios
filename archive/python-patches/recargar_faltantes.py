"""
RECARGA LIMPIA COMPLETA - Borra duplicados y carga los 410 lotes correctamente.
Ejecutar DESPUES de que el nuevo deploy este live en Render.
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
print("RECARGA LIMPIA DE INVENTARIO - ANIMUS Lab")
print(f"{'='*55}\n")

# Cargar JSON
with open("inventario_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
todos = data["movimientos"]
print(f"Lotes en JSON: {len(todos)}")

# Despertar servidor
print("\nConectando al servidor (hasta 60s si esta dormido)...")
for i in range(6):
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=60)
        if r.status_code == 200:
            print("Servidor activo\n")
            break
    except Exception:
        pass
    print(f"  Intento {i+1}/6...")
    time.sleep(10)

# Verificar conteo actual
try:
    r = requests.get(f"{BASE_URL}/api/inventario", timeout=20)
    d = r.json()
    print(f"Movimientos actuales en app: {d.get('movimientos', '?')}")
except Exception:
    pass

# PASO 1: Borrar todos los movimientos (reset limpio)
print("\nPASO 1: Borrando movimientos duplicados...")
try:
    r = requests.post(f"{BASE_URL}/api/reset-movimientos", timeout=30)
    if r.status_code == 200:
        print(f"  Reset OK: {r.json()}")
    else:
        print(f"  Error en reset: {r.status_code} - {r.text[:100]}")
        sys.exit(1)
except Exception as e:
    print(f"  Error: {e}")
    sys.exit(1)

time.sleep(2)

# PASO 2: Cargar todos los 410 lotes desde cero
print(f"\nPASO 2: Cargando {len(todos)} lotes limpios...")
ok = 0
errores = []

for i, mov in enumerate(todos):
    cargado = False
    for intento in range(5):
        try:
            r = requests.post(
                f"{BASE_URL}/api/movimientos",
                json=mov, timeout=25,
                headers={"Content-Type": "application/json"}
            )
            if r.status_code == 201:
                ok += 1
                cargado = True
                break
            elif "<!DOCTYPE" in r.text or r.status_code in [502, 503, 504]:
                time.sleep(5 + intento * 3)
            else:
                break
        except requests.exceptions.Timeout:
            time.sleep(8)
        except Exception:
            time.sleep(4)

    if not cargado:
        errores.append(f"{mov['material_id']} - {mov['material_nombre'][:25]}")

    if (i + 1) % 50 == 0:
        pct = round((i + 1) / len(todos) * 100)
        print(f"  {i+1}/{len(todos)} ({pct}%) | OK: {ok} | Errores: {len(errores)}")

    time.sleep(0.12)

# Resultado final
print(f"\n{'='*55}")
print(f"COMPLETADO")
print(f"  Cargados:  {ok}/{len(todos)}")
print(f"  Errores:   {len(errores)}")
if errores:
    print(f"\nLotes con error:")
    for e in errores:
        print(f"  - {e}")
print(f"\nRevisa la app: {BASE_URL}")
