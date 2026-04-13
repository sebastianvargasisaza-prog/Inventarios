#!/usr/bin/env python3
import os
import shutil
from pathlib import Path

# Rutas
proyecto_path = Path(r"C:\Users\sebas\OneDrive\Documentos\Claude\Projects\Inventarios\inventario-espagiria")
archivo_corregido = Path(r"C:\Users\sebas\OneDrive\Documentos\Claude\Projects\Inventarios\route_panel_CORREGIDO.js")
archivo_destino = proyecto_path / "app" / "api" / "panel" / "route.js"

print("=" * 60)
print("ACTUALIZADOR DE PANEL - Inventario Espagiria")
print("=" * 60)

# Verificar que existen los archivos
if not archivo_corregido.exists():
    print(f"❌ ERROR: No encontré {archivo_corregido}")
    exit(1)

if not archivo_destino.exists():
    print(f"❌ ERROR: No encontré {archivo_destino}")
    print(f"   Ruta esperada: {archivo_destino}")
    exit(1)

print(f"\n✅ Archivo corregido encontrado: {archivo_corregido.name}")
print(f"✅ Archivo destino encontrado: {archivo_destino.name}")

# Leer archivo corregido
try:
    with open(archivo_corregido, 'r', encoding='utf-8') as f:
        contenido_nuevo = f.read()
    print(f"\n✅ Contenido leído: {len(contenido_nuevo)} caracteres")
except Exception as e:
    print(f"❌ Error al leer archivo: {e}")
    exit(1)

# Crear backup del archivo original
backup_path = archivo_destino.with_suffix('.js.backup')
try:
    shutil.copy(archivo_destino, backup_path)
    print(f"✅ Backup creado: {backup_path.name}")
except Exception as e:
    print(f"⚠️  Aviso: No se pudo crear backup: {e}")

# Reemplazar contenido
try:
    with open(archivo_destino, 'w', encoding='utf-8') as f:
        f.write(contenido_nuevo)
    print(f"✅ Archivo actualizado: {archivo_destino.name}")
except Exception as e:
    print(f"❌ Error al escribir archivo: {e}")
    exit(1)

# Hacer git commit y push
print("\n" + "=" * 60)
print("Realizando Git Commit y Push...")
print("=" * 60)

os.chdir(proyecto_path)

# Verificar git
try:
    os.system("git status")
    print("\n✅ Repositorio git encontrado")
except:
    print("❌ Error con git")
    exit(1)

# Add
print("\n📝 Agregando archivo...")
resultado = os.system("git add app/api/panel/route.js")
if resultado == 0:
    print("✅ Archivo agregado a git")
else:
    print("⚠️  Error al agregar archivo")

# Commit
print("\n💾 Haciendo commit...")
resultado = os.system('git commit -m "Fix: panel endpoint - filter produccion movements and fix timezone for movimientos_hoy"')
if resultado == 0:
    print("✅ Commit exitoso")
else:
    print("⚠️  Posible que no haya cambios o error en commit")

# Push
print("\n🚀 Haciendo push a GitHub...")
resultado = os.system("git push")
if resultado == 0:
    print("✅ Push exitoso - Cambios en vivo!")
else:
    print("❌ Error en push - verifica tu conexión a internet o permisos de GitHub")

print("\n" + "=" * 60)
print("✅ ¡ACTUALIZACIÓN COMPLETADA!")
print("=" * 60)
print("\nPróximos pasos:")
print("1. El panel debería actualizarse automáticamente en Vercel")
print("2. Espera 2-3 minutos para que se despliegue")
print("3. Ve al panel y actualiza (F5)")
print("4. Verifica que MOVIMIENTOS HOY ahora muestre valores")
