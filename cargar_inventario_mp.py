"""
cargar_inventario_mp.py — Genera stock_inicial_mp.sql desde el Excel de inventario.

Uso:
    python cargar_inventario_mp.py

Salida: stock_inicial_mp.sql (copiar y pegar en Render shell)
    sqlite3 /var/data/inventario.db < stock_inicial_mp.sql

Requisitos: pip install pandas openpyxl --break-system-packages
"""
import os
import sys
import re
from datetime import datetime

try:
    import pandas as pd
except ImportError:
    sys.exit("Instala pandas: pip install pandas openpyxl --break-system-packages")

HERE    = os.path.dirname(os.path.abspath(__file__))
EXCEL   = os.path.join(HERE, "INVENTARIO_MP_v8_2 (1).xlsx")
OUT_SQL = os.path.join(HERE, "stock_inicial_mp.sql")

HOY = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
FECHA_CONTEO = '2026-04-18'   # fecha del Excel


def esc(v):
    """Escapar string para SQL (comillas simples)."""
    return str(v or '').replace("'", "''")


def fmt_fecha(v):
    if pd.isna(v):
        return ''
    try:
        return pd.to_datetime(v).strftime('%Y-%m-%d')
    except Exception:
        s = str(v)[:10]
        return s if re.match(r'\d{4}-\d{2}-\d{2}', s) else ''


def main():
    # ── 1. Leer Excel ────────────────────────────────────────────
    print(f"Leyendo: {EXCEL}")
    df_raw = pd.read_excel(EXCEL, sheet_name='INVENTARIO', header=3)

    # Fila 0 es la segunda cabecera (CÓDIGO MP, NOMBRE INCI…) — descartar
    df_raw = df_raw.iloc[1:].reset_index(drop=True)

    # Renombrar columnas
    df_raw.columns = [
        'codigo_mp', 'nombre_inci', 'nombre_comercial', 'tipo_mp',
        'proveedor', 'stock_minimo', 'lote', 'cant_conteo',
        'cant_actual', 'estanteria', 'posicion',
        'fecha_venc', 'dias', 'estado'
    ]

    df = df_raw.copy()

    # ── 2. Limpieza ───────────────────────────────────────────────
    # Convertir a str y limpiar
    for col in ['codigo_mp', 'nombre_inci', 'nombre_comercial', 'tipo_mp',
                'proveedor', 'lote', 'estanteria', 'posicion', 'estado']:
        df[col] = df[col].fillna('').astype(str).str.strip()

    df['cant_conteo']  = pd.to_numeric(df['cant_conteo'], errors='coerce').fillna(0)
    df['stock_minimo'] = pd.to_numeric(df['stock_minimo'], errors='coerce').fillna(0)
    df['fecha_venc_str'] = df['fecha_venc'].apply(fmt_fecha)

    # Filtrar filas inválidas
    df = df[df['codigo_mp'] != '']
    df = df[df['codigo_mp'] != 'CÓDIGO MP']
    df = df[~df['codigo_mp'].str.lower().str.contains('total|resumen|leyenda', na=False)]

    # Filas sin lote real → PENDIENTE (se cargan en maestro pero sin movimiento)
    df_con_lote    = df[(df['lote'] != '') & (df['lote'].str.upper() != 'S/L')]
    df_sin_lote    = df[(df['lote'] == '') | (df['lote'].str.upper() == 'S/L')]

    # Omitir lotes con cantidad 0 (no aportan stock)
    df_stock = df_con_lote[df_con_lote['cant_conteo'] > 0]
    df_cero  = df_con_lote[df_con_lote['cant_conteo'] <= 0]

    print(f"\nResumen de filas:")
    print(f"  Con lote + cantidad > 0 → se cargan como Entrada : {len(df_stock)}")
    print(f"  Con lote + cantidad = 0 → se registran sin stock : {len(df_cero)}")
    print(f"  Sin lote (S/L)         → solo maestro_mps        : {len(df_sin_lote)}")
    print(f"  Total MPs únicos       : {df['codigo_mp'].nunique()}")

    # ── 3. Generar SQL ────────────────────────────────────────────
    lines = []
    lines.append("-- ==========================================================")
    lines.append("-- stock_inicial_mp.sql")
    lines.append(f"-- Generado: {HOY}")
    lines.append(f"-- Fuente  : INVENTARIO_MP_v8_2 (1).xlsx  (conteo {FECHA_CONTEO})")
    lines.append("-- Ejecutar: sqlite3 /var/data/inventario.db < stock_inicial_mp.sql")
    lines.append("-- ==========================================================")
    lines.append("")
    lines.append("BEGIN TRANSACTION;")
    lines.append("")

    # 3a. maestro_mps — todos los MPs únicos
    lines.append("-- ── maestro_mps ──────────────────────────────────────────")
    mps_vistos = set()
    for _, row in df.iterrows():
        cod = row['codigo_mp']
        if cod in mps_vistos:
            continue
        mps_vistos.add(cod)
        lines.append(
            f"INSERT OR IGNORE INTO maestro_mps "
            f"(codigo_mp,nombre_inci,nombre_comercial,tipo,proveedor,stock_minimo) VALUES ("
            f"'{esc(cod)}',"
            f"'{esc(row['nombre_inci'])}',"
            f"'{esc(row['nombre_comercial'])}',"
            f"'{esc(row['tipo_mp'])}',"
            f"'{esc(row['proveedor'])}',"
            f"{row['stock_minimo']:.2f});"
        )
    lines.append(f"-- {len(mps_vistos)} MPs insertados (INSERT OR IGNORE)")
    lines.append("")

    # 3b. movimientos — solo lotes con cantidad > 0
    lines.append("-- ── movimientos (stock inicial) ──────────────────────────")
    lines.append("-- NOTA: se omiten lotes con cantidad=0 y lotes S/L")
    obs = f'Stock inicial — conteo físico {FECHA_CONTEO}'
    count_mov = 0
    for _, row in df_stock.iterrows():
        zona = row['estanteria']
        if row['posicion']:
            zona = f"{zona}-{row['posicion']}"
        lines.append(
            f"INSERT INTO movimientos "
            f"(material_id,material_nombre,cantidad,tipo,fecha,observaciones,"
            f"lote,fecha_vencimiento,estanteria,posicion,proveedor,estado_lote) VALUES ("
            f"'{esc(row['codigo_mp'])}',"
            f"'{esc(row['nombre_comercial'])}',"
            f"{row['cant_conteo']:.4f},"
            f"'Entrada',"
            f"'{FECHA_CONTEO} 08:00:00',"
            f"'{esc(obs)}',"
            f"'{esc(row['lote'])}',"
            f"'{row['fecha_venc_str']}',"
            f"'{esc(row['estanteria'])}',"
            f"'{esc(row['posicion'])}',"
            f"'{esc(row['proveedor'])}',"
            f"'{esc(row['estado'])}');"
        )
        count_mov += 1
    lines.append(f"-- {count_mov} movimientos de Entrada insertados")
    lines.append("")

    # 3c. Fix duplicado limpiador ácido kójico
    lines.append("-- ── Fix duplicado limpiador ácido kójico ────────────────")
    lines.append("-- Verificar si existe el duplicado (ejecutar primero como SELECT):")
    lines.append("-- SELECT codigo_mp, nombre_comercial, COUNT(*) c FROM maestro_mps")
    lines.append("--   WHERE nombre_comercial LIKE '%kójico%' OR nombre_comercial LIKE '%kojico%'")
    lines.append("--   GROUP BY nombre_comercial;")
    lines.append("-- Si hay duplicado, descomentar el DELETE apropiado:")
    lines.append("-- DELETE FROM maestro_mps WHERE codigo_mp='<CÓDIGO_DUPLICADO>';")
    lines.append("")

    lines.append("COMMIT;")
    lines.append("")
    lines.append(f"-- Verificación rápida post-import:")
    lines.append("-- SELECT COUNT(*) as total_mps FROM maestro_mps;")
    lines.append("-- SELECT COUNT(*) as entradas_iniciales FROM movimientos WHERE observaciones LIKE 'Stock inicial%';")
    lines.append("-- SELECT material_id, material_nombre, SUM(cantidad) as stock")
    lines.append("--   FROM movimientos WHERE tipo='Entrada' AND observaciones LIKE 'Stock inicial%'")
    lines.append("--   GROUP BY material_id ORDER BY material_nombre LIMIT 20;")

    # ── 4. Escribir archivo ───────────────────────────────────────
    sql_text = '\n'.join(lines)
    with open(OUT_SQL, 'w', encoding='utf-8') as f:
        f.write(sql_text)

    print(f"\n✅ SQL generado: {OUT_SQL}")
    print(f"   MPs en maestro_mps : {len(mps_vistos)}")
    print(f"   Entradas de stock  : {count_mov}")
    print(f"\nSiguiente paso:")
    print(f"  1. Revisa el archivo stock_inicial_mp.sql")
    print(f"  2. En Render shell: sqlite3 /var/data/inventario.db < stock_inicial_mp.sql")

    # ── 5. Preview de las primeras 5 entradas ────────────────────
    print(f"\nPrimeras 5 entradas que se cargarán:")
    for _, row in df_stock.head(5).iterrows():
        print(f"  {row['codigo_mp']} | {row['nombre_comercial'][:25]:<25} | {row['lote']:<20} | {row['cant_conteo']:.1f}g | vence:{row['fecha_venc_str']}")


if __name__ == '__main__':
    main()
