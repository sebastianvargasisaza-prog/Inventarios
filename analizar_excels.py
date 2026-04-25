"""
analizar_excels.py — Lee ambos Excel y muestra estructura para diseñar importación.
Ejecutar: python analizar_excels.py
Requiere: pip install openpyxl pandas --break-system-packages
"""
import os
import sys
try:
    import pandas as pd
except ImportError:
    sys.exit("Instala pandas: pip install pandas openpyxl --break-system-packages")

HERE = os.path.dirname(os.path.abspath(__file__))

MP_FILE  = os.path.join(HERE, "INVENTARIO_MP_v8_2 (1).xlsx")
MEE_FILE = os.path.join(HERE, "Listado_Materiales_Envase_Empaque-26bf75d0.xlsx")

def analizar_mp(path):
    print(f"\n{'='*60}")
    print(f"  INVENTARIO MATERIAS PRIMAS — análisis detallado")
    print('='*60)
    # Leer con header en fila 3 (0-indexed) para ver columnas reales
    df = pd.read_excel(path, sheet_name='INVENTARIO', header=3, skiprows=[])
    # Renombrar columnas con sus posiciones para claridad
    cols = list(df.columns)
    print(f"\n  Columnas reales (header=3): {cols}")
    print(f"  Total filas (incluye vacías): {len(df)}")
    df_data = df.dropna(how='all')
    print(f"  Filas con algún dato: {len(df_data)}")

    # Ver primeras 8 filas reales
    print("\n  Primeras 8 filas de datos:")
    for i, row in df_data.head(8).iterrows():
        vals = {str(c)[:15]: str(v)[:25] for c, v in row.items() if str(v) != 'nan'}
        print(f"    [{i:3}] {vals}")

    # Análisis de columna 0 (MATERIA PRIMA)
    col0 = cols[0]
    col0_vals = df[col0].dropna()
    print(f"\n  Col 0 '{col0}': {col0_vals.nunique()} únicos")
    print(f"  Primeros 10 valores: {list(col0_vals.head(10))}")

    # Ver últimas 5 filas para detectar totales o footers
    print("\n  Últimas 5 filas con datos:")
    for i, row in df_data.tail(5).iterrows():
        vals = {str(c)[:15]: str(v)[:25] for c, v in row.items() if str(v) != 'nan'}
        print(f"    [{i:3}] {vals}")

def analizar_mee(path):
    print(f"\n{'='*60}")
    print(f"  MATERIALES ENVASE Y EMPAQUE — análisis detallado")
    print('='*60)
    xl = pd.ExcelFile(path)
    print(f"  Hojas: {xl.sheet_names}")
    for sheet in xl.sheet_names:
        df_raw = pd.read_excel(path, sheet_name=sheet, header=None)
        print(f"\n  ── Hoja: '{sheet}' — {df_raw.shape[0]} filas x {df_raw.shape[1]} cols")
        print("  Primeras 6 filas (sin header):")
        for i, row in df_raw.head(6).iterrows():
            vals = [str(v)[:30] for v in row]
            print(f"    [{i}] {vals}")
        if df_raw.shape[0] > 3:
            # Buscar fila header (la que tiene más valores no-nan)
            non_nan = [df_raw.iloc[i].notna().sum() for i in range(min(10, len(df_raw)))]
            header_row = non_nan.index(max(non_nan))
            print(f"  → Fila header detectada: {header_row}")
            df = pd.read_excel(path, sheet_name=sheet, header=header_row)
            cols = list(df.columns)
            print(f"  Columnas: {cols}")
            df_data = df.dropna(how='all')
            print(f"  Filas con datos: {len(df_data)}")
            for col in cols[:12]:
                sample = df[col].dropna()
                if len(sample) > 0:
                    print(f"    '{col}': {sample.nunique()} únicos — ej: {list(sample.head(3))}")

analizar_mp(MP_FILE)

import os as _os
if _os.path.exists(MEE_FILE):
    analizar_mee(MEE_FILE)
else:
    print(f"\n⚠️  MEE no encontrado — copia el archivo aquí:\n   {MEE_FILE}")

print("\n\n✅ Análisis completado. Pega este output completo en el chat.")
