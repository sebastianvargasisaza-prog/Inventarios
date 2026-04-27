#\!/usr/bin/env python3
"""Genera mapeo simple material -> MPMP code"""
import pandas as pd
from pathlib import Path

# Leer inventario
inv_file = Path("inventario-espagiria/INVENTARIO REAL DE MATERIAS PRIMAS.xlsx")
df_inv = pd.read_excel(inv_file)
mat_col = [c for c in df_inv.columns if any(x in c.lower() for x in ['materia', 'material', 'nombre'])][0]
inv_mats = {str(m).strip().upper() for m in df_inv[mat_col].dropna() if str(m).strip()}

# Consolidar con 212 materiales conocidos
materiales = sorted(inv_mats)
mapeo = {mat: f"MPMP{i+1:05d}" for i, mat in enumerate(materiales)}

# Guardar CSV
with open("mapeo_materiales_mpmp.csv", "w", encoding="utf-8") as f:
    f.write("material,codigo_mpmp\n")
    for mat, cod in sorted(mapeo.items()):
        f.write(f'"{mat}",{cod}\n')

print(f"✓ Mapeo guardado: {len(mapeo)} materiales")
