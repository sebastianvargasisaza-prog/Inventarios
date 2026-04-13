#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

excel_file = Path("inventario-espagiria/INVENTARIO REAL DE MATERIAS PRIMAS.xlsx")
df = pd.read_excel(excel_file)

print("=" * 80)
print("DIAGNOSTICO: INVENTARIO REAL DE MATERIAS PRIMAS.xlsx")
print("=" * 80)

print(f"\nTotal filas: {len(df)}")
print(f"Columnas: {list(df.columns)}")

# Analizar columna NOMBRE INCI
nombre_col = "NOMBRE INCI"
print(f"\nAnalisis de {nombre_col}:")
print(f"  Valores totales: {len(df)}")
print(f"  Valores no nulos: {df[nombre_col].notna().sum()}")
print(f"  Valores nulos: {df[nombre_col].isna().sum()}")
print(f"  Valores duplicados: {(~df[nombre_col].duplicated()).sum()}")
print(f"  Valores unicos: {df[nombre_col].nunique()}")

# Mostrar algunos valores
print(f"\nPrimeros 10 valores en {nombre_col}:")
for i, v in enumerate(df[nombre_col].head(10)):
    print(f"  {i+1}. {v}")

# Mostrar valores nulos
null_indices = df[df[nombre_col].isna()].index.tolist()
print(f"\nIndices con valores nulos en {nombre_col}: {null_indices[:10]}")

# Mostrar duplicados (primeros 5)
duplicadas = df[df[nombre_col].duplicated(keep=False)].sort_values(nombre_col)
print(f"\nValores duplicados (primeros 5):")
for v in duplicadas[nombre_col].unique()[:5]:
    count = (df[nombre_col] == v).sum()
    print(f"  {v}: {count} veces")

# Analizar columna CODIGO MP
codigo_col = "CODIGO MP"
print(f"\n\nAnalisis de {codigo_col}:")
print(f"  Valores no nulos: {df[codigo_col].notna().sum()}")
print(f"  Valores nulos: {df[codigo_col].isna().sum()}")

# Mostrar algunos valores
print(f"\nPrimeros 20 valores en {codigo_col}:")
for i, v in enumerate(df[codigo_col].head(20)):
    print(f"  {i+1}. {v}")
