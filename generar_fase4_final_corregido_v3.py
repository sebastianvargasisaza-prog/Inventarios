#!/usr/bin/env python3
"""
FASE 4 FINAL: SQL CORREGIDO para Supabase
- Asigna nombre_mp correctamente en ambas columnas de destino
- CORRIGE: Usa "codigo_lote" en lugar de "lote" (nombre columna real en DB)
- CORRIGE: Cast de fecha_vencimiento a DATE en SELECT
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

excel_file = Path("inventario-espagiria/INVENTARIO REAL DE MATERIAS PRIMAS.xlsx")
df = pd.read_excel(excel_file)

print("Regenerando SQL con tipos de datos correctos...")

# LISTA MAESTRA
lista_maestra_path = Path("LISTA_MAESTRA_CONSOLIDADA.txt")
materiales_existentes = {}
if lista_maestra_path.exists():
    with open(lista_maestra_path, "r", encoding="utf-8") as f:
        for line in f.readlines()[2:]:
            parts = line.split("|")
            if len(parts) >= 3:
                codigo = parts[1].strip()
                nombre = parts[2].strip()
                if codigo.startswith("MPMP"):
                    materiales_existentes[nombre.upper()] = codigo

# EXTRAER MATERIALES
materiales_nuevo = {}
for idx, row in df.iterrows():
    nombre = str(row.get("NOMBRE MP", "")).strip().upper()
    if not nombre or nombre == "NAN":
        nombre = str(row.get("NOMBRE INCI", "")).strip().upper()
    if nombre and len(nombre) > 2 and nombre != "NAN":
        materiales_nuevo[nombre] = True

# MAPEO
mapeo_materiales = {}
siguiente = len(materiales_existentes) + 1
for nombre in sorted(materiales_nuevo.keys()):
    if nombre in materiales_existentes:
        mapeo_materiales[nombre] = materiales_existentes[nombre]
    else:
        mapeo_materiales[nombre] = f"MPMP{siguiente:05d}"
        siguiente += 1

# SQL MATERIALES
sql_mat = []
for nombre, codigo in sorted(mapeo_materiales.items()):
    nombre_esc = nombre.replace("'", "''")
    sql_mat.append(f"  ('{codigo}', '{nombre_esc}', '{nombre_esc}', 'g', TRUE)")

mat_insert = f"""-- PASO 1: INSERTAR MATERIALES ({len(mapeo_materiales)} total)
INSERT INTO materiales (codigo, nombre_inci, nombre_mp, unidad, activo)
VALUES
""" + ",\n".join(sql_mat) + """
ON CONFLICT(codigo) DO NOTHING;
"""

# SQL LOTES
def extraer_cantidad(val):
    if pd.isna(val): return 0
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        try: return float(val.replace(',', '.'))
        except: return 0
    return 0

lotes_data = []
for idx, row in df.iterrows():
    nombre = str(row.get("NOMBRE MP", "")).strip().upper()
    if not nombre or nombre == "NAN":
        nombre = str(row.get("NOMBRE INCI", "")).strip().upper()
    if not nombre or nombre == "NAN": continue

    lote = str(row.get("LOTE", "")).strip() or f"LOTE_{idx+1}"
    cantidad = extraer_cantidad(row.get("CANTIDAD"))
    ubicacion = str(row.get("ESTANTERIA", "")).strip() or "SIN_UBICACION"

    venc = row.get("FECHA DE VENCIMIENTO")
    if pd.isna(venc) or venc is None:
        vencimiento = "NULL"
    else:
        try:
            vencimiento = f"'{pd.Timestamp(venc).strftime('%Y-%m-%d')}'"
        except:
            vencimiento = "NULL"

    if nombre in mapeo_materiales:
        codigo = mapeo_materiales[nombre]
        lotes_data.append((codigo, lote, ubicacion, cantidad, vencimiento))

# SQL LOTES - CORREGIDO CON TIPOS
insert_lotes = []
for codigo, lote, ubicacion, cantidad, venc in lotes_data:
    lote_esc = lote.replace("'", "''")
    ubic_esc = ubicacion.replace("'", "''")
    insert_lotes.append(f"  ('{codigo}', '{lote_esc}', '{ubic_esc}', {cantidad}, {venc})")

lotes_insert = f"""-- PASO 2: INSERTAR LOTES ({len(lotes_data)} total)
INSERT INTO lotes (material_id, codigo_lote, ubicacion, cantidad, fecha_vencimiento, fecha_ingreso, activo)
SELECT m.id, t.lote, t.ubicacion, t.cantidad, t.fecha_vencimiento::date, CURRENT_DATE, TRUE
FROM (VALUES
""" + ",\n".join(insert_lotes) + """
) AS t(codigo_mp text, lote text, ubicacion text, cantidad numeric, fecha_vencimiento text)
INNER JOIN materiales m ON m.codigo = t.codigo_mp
ON CONFLICT DO NOTHING;
"""

sql_final = f"""-- FASE 4 FINAL - CARGA INVENTARIO A SUPABASE
-- Generado: {datetime.now().isoformat()}
-- Materiales: {len(mapeo_materiales)}
-- Lotes: {len(lotes_data)}

{mat_insert}

{lotes_insert}

-- VERIFICACIONES:
-- SELECT COUNT(*) FROM materiales;
-- SELECT COUNT(*) FROM lotes;
-- SELECT nombre_inci, SUM(l.cantidad) FROM materiales m LEFT JOIN lotes l ON m.id = l.material_id WHERE nombre_inci LIKE '%PALMITOYL%' GROUP BY m.id, m.nombre_inci;
"""

with open("FASE_4_INVENTARIO_CARGABLE_CORREGIDO.sql", "w", encoding="utf-8") as f:
    f.write(sql_final)

print("EXITO: SQL generado correctamente")
print(f"  Materiales: {len(mapeo_materiales)}")
print(f"  Lotes: {len(lotes_data)}")
print(f"  Cambios: codigo_lote + fecha_vencimiento::date")
