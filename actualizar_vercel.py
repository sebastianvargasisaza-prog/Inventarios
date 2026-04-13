#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from pathlib import Path

print("=" * 70)
print("ACTUALIZADOR DE PANEL - Vercel Deploy")
print("=" * 70)

# Ruta del proyecto
proyecto = Path(r"C:\Users\sebas\OneDrive\Documentos\Claude\Projects\Inventarios\inventario-espagiria")
archivo_corregido = Path(r"C:\Users\sebas\OneDrive\Documentos\Claude\Projects\Inventarios\route_panel_CORREGIDO.js")
archivo_destino = proyecto / "app" / "api" / "panel" / "route.js"

print(f"\n📁 Proyecto: {proyecto}")
print(f"📄 Archivo corregido: {archivo_corregido}")
print(f"🎯 Destino: {archivo_destino}")

# Verificar archivos
if not archivo_corregido.exists():
    print(f"\n❌ ERROR: No existe {archivo_corregido}")
    exit(1)

if not archivo_destino.exists():
    print(f"\n❌ ERROR: No existe {archivo_destino}")
    exit(1)

print(f"\n✅ Archivos encontrados correctamente")

# Leer archivo corregido
print(f"\n📖 Leyendo archivo corregido...")
with open(archivo_corregido, 'r', encoding='utf-8') as f:
    contenido_nuevo = f.read()

print(f"✅ Contenido leído: {len(contenido_nuevo)} caracteres")

# Crear backup
backup = archivo_destino.with_suffix('.js.bak')
print(f"\n💾 Creando backup en: {backup.name}")
with open(archivo_destino, 'r', encoding='utf-8') as f:
    contenido_original = f.read()
with open(backup, 'w', encoding='utf-8') as f:
    f.write(contenido_original)

print(f"✅ Backup creado")

# Reemplazar contenido
print(f"\n✏️  Reemplazando contenido en route.js...")
with open(archivo_destino, 'w', encoding='utf-8') as f:
    f.write(contenido_nuevo)

print(f"✅ Archivo actualizado correctamente")

# Navegar a la carpeta y hacer deploy
print(f"\n" + "=" * 70)
print("🚀 Preparando deploy a Vercel...")
print("=" * 70)

os.chdir(proyecto)

print(f"\n📍 Directorio actual: {os.getcwd()}")
print(f"\n▸ Ejecutando: vercel deploy --prod\n")

resultado = os.system("vercel deploy --prod")

if resultado == 0:
    print(f"\n✅ ¡DEPLOY EXITOSO!")
else:
    print(f"\n⚠️  El deploy se ejecutó. Si hay error, verifica la consola arriba.")

print(f"\n" + "=" * 70)
print("✅ ACTUALIZACIÓN COMPLETADA")
print("=" * 70)
print(f"""
Próximos pasos:
1. El panel estará en vivo en 1-2 minutos
2. Abre: https://inventario-espagiria-xxxxx.vercel.app
3. Actualiza la página (F5)
4. Verifica que MOVIMIENTOS HOY ahora muestra valores

Si algo falla, revisa el Vercel dashboard:
https://vercel.com/dashboard
""")

input("\n▸ Presiona Enter para cerrar...")
