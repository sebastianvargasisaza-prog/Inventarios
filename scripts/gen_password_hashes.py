#!/usr/bin/env python3
"""
gen_password_hashes.py — Genera hashes PBKDF2 para migrar passwords de texto
plano a hash en Render.

Uso:
    python scripts/gen_password_hashes.py

Salida: imprime cada usuario con su hash listo para pegar en
Render → Service → Environment como variable PASS_<USERNAME>.

Esto elimina el riesgo de tener passwords en texto plano en env vars y
neutraliza el fallback hardcoded en config.py si el SECRET_KEY también
se pone en env var. El sistema actual (api/blueprints/core.py:118-121)
ya soporta PBKDF2: si la env var empieza con 'pbkdf2:', usa
check_password_hash; si no, fallback a comparacion directa.

Migracion sin downtime:
  1. Correr este script localmente con las passwords reales
  2. Pegar cada PASS_<USER>=pbkdf2:... en Render Environment
  3. Hacer deploy (o reiniciar service)
  4. Verificar login de cada usuario funciona
  5. Una vez validado, eliminar fallbacks plaintext de config.py
"""
import getpass
import sys
from werkzeug.security import generate_password_hash

USUARIOS = [
    "sebastian", "alejandro", "hernando", "catalina", "luz", "daniela",
    "valentina", "jefferson", "felipe", "mayra", "gloria", "laura",
    "miguel", "yuliel", "luis", "smurillo", "sergio", "mayerlin", "camilo",
]

print("=" * 70)
print("Generador de hashes PBKDF2 para passwords de Inventarios")
print("=" * 70)
print()
print("Para cada usuario, ingresa el password (no se mostrara en pantalla).")
print("Enter en blanco = saltar ese usuario.")
print()

resultados = {}
for u in USUARIOS:
    pwd = getpass.getpass(f"  Password para {u}: ").strip()
    if not pwd:
        print(f"  → saltado ({u})")
        continue
    if len(pwd) < 6:
        print(f"  ⚠ password muy corto, minimo 6 chars. Saltando {u}.")
        continue
    h = generate_password_hash(pwd, method="pbkdf2:sha256:600000")
    resultados[u] = h

print()
print("=" * 70)
print("Variables de entorno para Render (Service → Environment)")
print("=" * 70)
print()
for u, h in resultados.items():
    print(f"PASS_{u.upper()}={h}")

print()
print("=" * 70)
print(f"  {len(resultados)} hashes generados.")
print("  Copialos a Render como env vars y haz redeploy.")
print("  Despues de validar, elimina los fallbacks plaintext de config.py.")
print("=" * 70)
