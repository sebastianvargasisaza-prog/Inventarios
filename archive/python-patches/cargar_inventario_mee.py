"""
cargar_inventario_mee.py — Genera stock_inicial_mee.sql desde el Excel de MEE.

Uso:
    python cargar_inventario_mee.py

Salida: stock_inicial_mee.sql
    → Subir a GitHub, luego en Render shell:
      wget -q -O /tmp/seed_mee.py https://raw.githubusercontent.com/sebastianvargasisaza-prog/Inventarios/main/api/seed_mee.py
      python3 /tmp/seed_mee.py

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
EXCEL   = os.path.join(HERE, "Listado_Materiales_Envase_Empaque.xlsx")
OUT_SQL = os.path.join(HERE, "stock_inicial_mee.sql")

HOY          = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
FECHA_CONTEO = '2026-04-18'


# ── Columnas objetivo en maestro_mee ──────────────────────────────────────────
# codigo | descripcion | categoria | proveedor | fabricante | estado
# stock_actual | stock_minimo | unidad | fecha_creacion


def esc(v):
    """Escapar string para SQL."""
    return str(v or '').replace("'", "''")


def normalizar(col):
    """Normalizar nombre de columna para comparación."""
    return re.sub(r'[^a-z0-9]', '', str(col).lower().strip())


def detectar_header(df_raw):
    """Devuelve el índice de la fila con más valores no-NaN (hasta fila 10)."""
    candidates = min(10, len(df_raw))
    counts = [df_raw.iloc[i].notna().sum() for i in range(candidates)]
    return counts.index(max(counts))


def mapear_columnas(cols):
    """
    Mapea nombres de columna del Excel a los campos de maestro_mee.
    Devuelve dict {campo_db: nombre_col_excel} o None si no encontrado.
    """
    normas = {normalizar(c): c for c in cols}

    # Patrones de búsqueda por campo (en orden de prioridad)
    patrones = {
        'codigo': [
            'codigomee', 'codigo', 'cod', 'ref', 'referencia', 'id', 'item',
            'codigomaterial', 'codmee', 'codigodelmaterial',
        ],
        'descripcion': [
            'descripcion', 'nombre', 'material', 'descripcionmaterial',
            'nombrematerial', 'desc', 'articulo', 'producto', 'detalle',
        ],
        'categoria': [
            'categoria', 'tipo', 'tipomaterial', 'tipomee', 'clase', 'grupo',
            'family', 'familia', 'tipodeempaque', 'tipoenvase',
        ],
        'proveedor': [
            'proveedor', 'supplier', 'vendedor', 'proveedorprincipal',
            'proveedor1', 'proveedorhabitual', 'proveedor principal',
        ],
        'fabricante': [
            'fabricante', 'marca', 'manufacturer', 'brand', 'origen',
            'fabricacion', 'productor',
        ],
        'estado': [
            'estado', 'status', 'activo', 'vigente', 'situacion',
        ],
        'stock_actual': [
            'stockactual', 'cantidadactual', 'cantactual', 'stock',
            'existencias', 'cantidad', 'conteo', 'cantidadconteo',
            'stockfisico', 'cant', 'cantconteo', 'cantidadenconteo',
            'existencia', 'saldo',
        ],
        'stock_minimo': [
            'stockminimo', 'stockmin', 'minimo', 'min', 'puntoReorden',
            'reorden', 'stockminimum', 'cantminima', 'stockminimo',
        ],
        'unidad': [
            'unidad', 'und', 'um', 'unidadmedida', 'unidades', 'udm',
            'unidaddemedida', 'unit',
        ],
    }

    mapa = {}
    for campo, lista in patrones.items():
        for patron in lista:
            if patron in normas:
                mapa[campo] = normas[patron]
                break

    return mapa


def inferir_categoria(descripcion, codigo):
    """Infiere categoría MEE desde descripción si la columna no existe."""
    texto = (str(descripcion) + ' ' + str(codigo)).lower()
    if any(x in texto for x in ['caja', 'corrugado', 'carton', 'box']):
        return 'Caja'
    if any(x in texto for x in ['frasco', 'botella', 'envase', 'flask', 'bottle']):
        return 'Frasco'
    if any(x in texto for x in ['tapa', 'cap', 'tapón', 'tapon']):
        return 'Tapa'
    if any(x in texto for x in ['bomba', 'pump', 'dispensador']):
        return 'Bomba'
    if any(x in texto for x in ['etiqueta', 'label', 'sticker']):
        return 'Etiqueta'
    if any(x in texto for x in ['bolsa', 'bag', 'sachet', 'pouch']):
        return 'Bolsa'
    if any(x in texto for x in ['tubo', 'tube']):
        return 'Tubo'
    if any(x in texto for x in ['insert', 'inserto', 'prospecto']):
        return 'Inserto'
    if any(x in texto for x in ['cinta', 'tape', 'adhesivo']):
        return 'Cinta'
    return 'Otro'


def main():
    if not os.path.exists(EXCEL):
        sys.exit(f"❌ No encontré el archivo:\n   {EXCEL}")

    print(f"Leyendo: {EXCEL}")

    # ── 1. Detectar hojas ──────────────────────────────────────────────────────
    xl = pd.ExcelFile(EXCEL)
    print(f"Hojas disponibles: {xl.sheet_names}")

    # Usar primera hoja si hay varias
    sheet = xl.sheet_names[0]
    print(f"Usando hoja: '{sheet}'")

    # ── 2. Detectar header ─────────────────────────────────────────────────────
    df_raw = pd.read_excel(EXCEL, sheet_name=sheet, header=None)
    header_row = detectar_header(df_raw)
    print(f"Header detectado en fila: {header_row}")

    df = pd.read_excel(EXCEL, sheet_name=sheet, header=header_row)
    print(f"Columnas encontradas: {list(df.columns)}")
    print(f"Total filas raw: {len(df)}")

    # ── 3. Mapear columnas ─────────────────────────────────────────────────────
    mapa = mapear_columnas(df.columns)
    print(f"\nMapeo de columnas detectado:")
    for campo, col in mapa.items():
        print(f"  {campo:<15} → '{col}'")

    campos_criticos = ['codigo', 'descripcion']
    for c in campos_criticos:
        if c not in mapa:
            # Mostrar columnas disponibles y pedir al usuario
            print(f"\n⚠️  No pude detectar la columna '{c}'.")
            print(f"   Columnas disponibles: {list(df.columns)}")
            sys.exit(f"Edita el dict 'patrones' en el script para incluir el nombre exacto.")

    # ── 4. Limpieza ────────────────────────────────────────────────────────────
    def get_col(campo, default=''):
        col = mapa.get(campo)
        if col and col in df.columns:
            return df[col]
        return pd.Series([default] * len(df))

    df['_codigo']      = get_col('codigo').fillna('').astype(str).str.strip()
    df['_descripcion'] = get_col('descripcion').fillna('').astype(str).str.strip()
    df['_proveedor']   = get_col('proveedor').fillna('').astype(str).str.strip()
    df['_fabricante']  = get_col('fabricante').fillna('').astype(str).str.strip()
    df['_unidad']      = get_col('unidad', 'und').fillna('und').astype(str).str.strip().replace('nan', 'und')
    df['_estado']      = get_col('estado', 'Activo').fillna('Activo').astype(str).str.strip().replace('nan', 'Activo')

    # Stock y mínimos — numérico
    df['_stock_actual'] = pd.to_numeric(get_col('stock_actual', 0), errors='coerce').fillna(0)
    df['_stock_minimo'] = pd.to_numeric(get_col('stock_minimo', 0), errors='coerce').fillna(0)

    # Categoría — inferir si no existe columna
    if 'categoria' in mapa:
        df['_categoria'] = get_col('categoria').fillna('Otro').astype(str).str.strip().replace('nan', 'Otro')
    else:
        print("  ⚠️  Columna 'categoria' no encontrada — se inferirá desde descripción")
        df['_categoria'] = df.apply(
            lambda r: inferir_categoria(r['_descripcion'], r['_codigo']), axis=1
        )

    # Normalizar estado — solo Activo/Inactivo
    def norm_estado(v):
        v = str(v).strip().lower()
        if v in ('', 'nan', 'n/a'):
            return 'Activo'
        if any(x in v for x in ['inact', 'baja', 'obsoleto', 'descont', 'no']):
            return 'Inactivo'
        return 'Activo'
    df['_estado'] = df['_estado'].apply(norm_estado)

    # ── 5. Filtrar filas válidas ───────────────────────────────────────────────
    df = df[df['_codigo'] != '']
    df = df[df['_codigo'].str.upper() != 'NAN']
    df = df[df['_descripcion'] != '']
    # Eliminar filas de totales/cabeceras internas
    df = df[~df['_codigo'].str.lower().str.contains(
        r'total|resumen|leyenda|codigo|código|subtotal', na=False, regex=True
    )]

    print(f"\nFilas válidas para importar: {len(df)}")

    # Verificar unicidad de código
    duplicados = df[df['_codigo'].duplicated(keep=False)]
    if len(duplicados) > 0:
        print(f"  ⚠️  {len(duplicados)} filas con código duplicado:")
        for cod, grp in duplicados.groupby('_codigo'):
            print(f"     {cod}: {len(grp)} veces")
        print("  → Se conservará solo la primera ocurrencia (INSERT OR IGNORE)")

    # ── 6. Preview ────────────────────────────────────────────────────────────
    print(f"\nPrimeras 5 filas que se cargarán:")
    for _, row in df.head(5).iterrows():
        print(f"  {row['_codigo']:<12} | {row['_descripcion'][:30]:<30} | "
              f"{row['_categoria']:<12} | stock:{row['_stock_actual']:>8.1f} "
              f"| {row['_unidad']}")

    # ── 7. Generar SQL ─────────────────────────────────────────────────────────
    lines = []
    lines.append("-- ==========================================================")
    lines.append("-- stock_inicial_mee.sql")
    lines.append(f"-- Generado : {HOY}")
    lines.append(f"-- Fuente   : Listado_Materiales_Envase_Empaque.xlsx  (conteo {FECHA_CONTEO})")
    lines.append("-- Ejecutar : python3 /tmp/seed_mee.py  (en Render shell)")
    lines.append("-- NOTA     : INSERT OR REPLACE sobreescribe los 69 registros")
    lines.append("--            placeholder que tienen stock_actual=2000 (default)")
    lines.append("-- ==========================================================")
    lines.append("")
    lines.append("BEGIN TRANSACTION;")
    lines.append("")
    lines.append("-- ── maestro_mee ──────────────────────────────────────────────")

    codigos_vistos = set()
    count_insert   = 0
    count_dup      = 0

    for _, row in df.iterrows():
        cod = row['_codigo']
        if cod in codigos_vistos:
            count_dup += 1
            continue
        codigos_vistos.add(cod)

        lines.append(
            f"INSERT OR REPLACE INTO maestro_mee "
            f"(codigo,descripcion,categoria,proveedor,fabricante,"
            f"estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ("
            f"'{esc(row['_codigo'])}',"
            f"'{esc(row['_descripcion'])}',"
            f"'{esc(row['_categoria'])}',"
            f"'{esc(row['_proveedor'])}',"
            f"'{esc(row['_fabricante'])}',"
            f"'{esc(row['_estado'])}',"
            f"{row['_stock_actual']:.4f},"
            f"{row['_stock_minimo']:.4f},"
            f"'{esc(row['_unidad'])}',"
            f"'{FECHA_CONTEO}');"
        )
        count_insert += 1

    lines.append(f"-- {count_insert} registros MEE (INSERT OR REPLACE)")
    if count_dup:
        lines.append(f"-- {count_dup} duplicados omitidos (primera ocurrencia conservada)")
    lines.append("")
    lines.append("COMMIT;")
    lines.append("")
    lines.append("-- Verificación rápida post-import:")
    lines.append("-- SELECT COUNT(*) FROM maestro_mee;")
    lines.append("-- SELECT categoria, COUNT(*) c, SUM(stock_actual) stock")
    lines.append("--   FROM maestro_mee GROUP BY categoria ORDER BY c DESC;")
    lines.append("-- SELECT * FROM maestro_mee WHERE stock_actual < stock_minimo LIMIT 20;")

    # ── 8. Escribir archivo ───────────────────────────────────────────────────
    sql_text = '\n'.join(lines)
    with open(OUT_SQL, 'w', encoding='utf-8') as f:
        f.write(sql_text)

    print(f"\n✅ SQL generado: {OUT_SQL}")
    print(f"   MEEs en maestro_mee : {count_insert}")
    if count_dup:
        print(f"   Duplicados omitidos : {count_dup}")
    print(f"\nSiguiente paso:")
    print(f"  1. Revisa stock_inicial_mee.sql")
    print(f"  2. Sube a GitHub + ejecuta seed_mee.py en Render")


if __name__ == '__main__':
    main()
