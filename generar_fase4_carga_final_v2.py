#!/usr/bin/env python3
"""
FASE 4 v2: Generar SQL para Supabase - Usando NOMBRE MP como principal
El archivo tiene 390 lotes pero NOMBRE INCI tiene 327 valores nulos
Usamos NOMBRE MP como columna principal y recurrimos a CODIGO MP
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

print("=" * 80)
print("FASE 4 v2: GENERAR SQL CARGA INVENTARIO - USANDO NOMBRE MP")
print("=" * 80)

# 1. LEER INVENTARIO
print("\n1 Leyendo INVENTARIO REAL DE MATERIAS PRIMAS.xlsx...")
excel_file = Path("inventario-espagiria/INVENTARIO REAL DE MATERIAS PRIMAS.xlsx")

try:
    df = pd.read_excel(excel_file)
    print(f"   OK: {len(df)} lotes")
except Exception as e:
    print(f"   ERROR: {e}")
    exit(1)

# 2. CARGAR LISTA MAESTRA EXISTENTE
print("\n2 Cargando LISTA_MAESTRA_CONSOLIDADA.txt...")
lista_maestra_path = Path("LISTA_MAESTRA_CONSOLIDADA.txt")
materiales_existentes = {}

if lista_maestra_path.exists():
    with open(lista_maestra_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines[2:]:
            parts = line.split("|")
            if len(parts) >= 3:
                try:
                    codigo = parts[1].strip()
                    nombre = parts[2].strip()
                    if codigo.startswith("MPMP"):
                        materiales_existentes[nombre.upper()] = codigo
                except:
                    pass
    print(f"   OK: {len(materiales_existentes)} materiales existentes")
else:
    print(f"   AVISO: No encontrada LISTA_MAESTRA_CONSOLIDADA.txt")

# 3. EXTRAER MATERIALES - Usando NOMBRE MP como principal
print("\n3 Extrayendo materiales usando NOMBRE MP...")

materiales_nuevo = {}
for idx, row in df.iterrows():
    # Intentar NOMBRE MP primero, luego NOMBRE INCI
    nombre = str(row.get("NOMBRE MP", "")).strip().upper()
    if not nombre or nombre == "NAN":
        nombre = str(row.get("NOMBRE INCI", "")).strip().upper()

    if nombre and len(nombre) > 2 and nombre != "NAN":
        materiales_nuevo[nombre] = True

print(f"   OK: Materiales unicos: {len(materiales_nuevo)}")

# 4. MAPEAR MATERIALES A CODIGOS MPMP
print("\n4 Mapeando materiales a codigos MPMP...")

mapeo_materiales = {}
siguiente_codigo_num = len(materiales_existentes) + 1

for nombre in sorted(materiales_nuevo.keys()):
    if nombre in materiales_existentes:
        mapeo_materiales[nombre] = materiales_existentes[nombre]
    else:
        codigo = f"MPMP{siguiente_codigo_num:05d}"
        mapeo_materiales[nombre] = codigo
        siguiente_codigo_num += 1

print(f"   OK: Total unicos mapeados: {len(mapeo_materiales)}")

# 5. GENERAR SQL PARA MATERIALES
print("\n5 Generando INSERT para materiales...")

sql_materiales = []
for nombre, codigo in sorted(mapeo_materiales.items()):
    nombre_esc = nombre.replace("'", "''")
    sql_materiales.append(f"  ('{codigo}', '{nombre_esc}', 'KG', TRUE)")

lineas_mat = [
    "-- PASO 1: INSERTAR MATERIALES",
    f"-- Total: {len(mapeo_materiales)} materiales unicos",
    "INSERT INTO materiales (codigo, nombre_inci, unidad, activo)",
    "VALUES",
    ",".join(sql_materiales),
    "ON CONFLICT(codigo) DO NOTHING;",
    "",
    "-- Verificar: SELECT COUNT(*) FROM materiales;",
    ""
]

# 6. GENERAR DATOS DE LOTES
print("\n6 Preparando datos de lotes...")

def extraer_cantidad(val):
    if pd.isna(val):
        return 0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.replace(',', '.'))
        except:
            return 0
    return 0

lotes_data = []
for idx, row in df.iterrows():
    # Obtener nombre del material
    nombre = str(row.get("NOMBRE MP", "")).strip().upper()
    if not nombre or nombre == "NAN":
        nombre = str(row.get("NOMBRE INCI", "")).strip().upper()

    nombre = nombre.strip()
    if not nombre or nombre == "NAN":
        continue

    # Obtener datos del lote
    lote = str(row.get("LOTE", "")).strip() or f"LOTE_{idx+1}"
    cantidad = extraer_cantidad(row.get("CANTIDAD"))
    ubicacion = str(row.get("ESTANTERIA", "")).strip() or "SIN_UBICACION"

    # Procesar fecha de vencimiento
    venc = row.get("FECHA DE VENCIMIENTO")
    if pd.isna(venc) or venc is None:
        vencimiento_str = "NULL"
    else:
        try:
            venc_date = pd.Timestamp(venc)
            vencimiento_str = f"'{venc_date.strftime('%Y-%m-%d')}'"
        except:
            vencimiento_str = "NULL"

    # Buscar el codigo MPMP para este material
    if nombre in mapeo_materiales:
        codigo = mapeo_materiales[nombre]
        lotes_data.append({
            'codigo': codigo,
            'nombre': nombre,
            'lote': lote,
            'ubicacion': ubicacion,
            'cantidad': cantidad,
            'vencimiento': vencimiento_str
        })

print(f"   OK: Lotes procesados: {len(lotes_data)}")

# 7. GENERAR SQL PARA LOTES
print("\n7 Generando INSERT para lotes...")

insert_lotes_parts = []
for lote_info in lotes_data:
    lote_esc = lote_info['lote'].replace("'", "''")
    ubicacion_esc = lote_info['ubicacion'].replace("'", "''")
    insert_lotes_parts.append(
        f"  ('{lote_info['codigo']}', '{lote_esc}', '{ubicacion_esc}', {lote_info['cantidad']}, {lote_info['vencimiento']})"
    )

lineas_lotes = [
    "",
    "-- PASO 2: INSERTAR LOTES",
    f"-- Total: {len(lotes_data)} lotes",
    "INSERT INTO lotes (material_id, lote, ubicacion, cantidad, fecha_vencimiento, fecha_ingreso, activo)",
    "SELECT",
    "  m.id,",
    "  t.lote,",
    "  t.ubicacion,",
    "  t.cantidad,",
    "  t.fecha_vencimiento,",
    "  CURRENT_DATE as fecha_ingreso,",
    "  TRUE as activo",
    "FROM (",
    "  VALUES",
    ",".join(insert_lotes_parts),
    ") AS t(codigo_mp, lote, ubicacion, cantidad, fecha_vencimiento)",
    "INNER JOIN materiales m ON m.codigo = t.codigo_mp",
    "ON CONFLICT DO NOTHING;",
    "",
    "-- Verificar: SELECT COUNT(*) FROM lotes;",
    ""
]

# 8. GUARDAR ARCHIVO SQL FINAL
print("\n8 Generando archivo SQL final...")

timestamp = datetime.now().isoformat()
sql_final = "\n".join(lineas_mat + lineas_lotes)

sql_final_completo = f"""-- =====================================================
-- FASE 4 v2: CARGA COMPLETA INVENTARIO REAL A SUPABASE
-- =====================================================
-- Generado: {timestamp}
-- Materiales unicos: {len(mapeo_materiales)}
-- Lotes: {len(lotes_data)}
-- =====================================================

{sql_final}
"""

output_file = Path("FASE_4_INVENTARIO_REAL_COMPLETO_V2.sql")
with open(output_file, "w", encoding="utf-8") as f:
    f.write(sql_final_completo)

print(f"   OK: {output_file}")

# 9. GUARDAR MAPEO
print("\n9 Guardando mapeo de materiales...")

mapeo_file = Path("MAPEO_MPMP_FINAL_V2.txt")
with open(mapeo_file, "w", encoding="utf-8") as f:
    f.write("CODIGO    | NOMBRE MATERIAL\n")
    f.write("=" * 80 + "\n")
    for nombre, codigo in sorted(mapeo_materiales.items()):
        f.write(f"{codigo} | {nombre}\n")

print(f"   OK: {mapeo_file}")

print(f"\nRESUMEN:")
print(f"   Materiales unicos: {len(mapeo_materiales)}")
print(f"   Lotes: {len(lotes_data)}")
print(f"   Materiales nuevos: {len(mapeo_materiales) - len(materiales_existentes)}")
print(f"   Archivos generados:")
print(f"     - {output_file}")
print(f"     - {mapeo_file}")
print("=" * 80)
