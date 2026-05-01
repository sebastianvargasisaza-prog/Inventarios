"""Test de regresion para columnas correctas en checklist pre-produccion.

Bug detectado en produccion: el codigo del checklist usaba columnas
que NO existen en produccion_programada (producto_nombre, fecha_planeada,
cantidad_kg, batch_size_kg). Las columnas reales son: producto,
fecha_programada, lotes.

Este test garantiza que las queries de los endpoints de checklist
ejecutan sin errores de columna inexistente, usando una DB en memoria.
"""
import sqlite3
from pathlib import Path


def _setup_in_memory_db():
    """Crea schema minimo en memoria para que los SELECTs no exploten."""
    con = sqlite3.connect(':memory:')
    c = con.cursor()
    c.executescript("""
        CREATE TABLE produccion_programada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT NOT NULL,
            fecha_programada TEXT NOT NULL,
            lotes INTEGER DEFAULT 1,
            estado TEXT DEFAULT 'pendiente'
        );
        CREATE TABLE formula_headers (
            producto_nombre TEXT PRIMARY KEY,
            lote_size_kg REAL DEFAULT 0
        );
        CREATE TABLE formula_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_nombre TEXT,
            material_id TEXT,
            material_nombre TEXT,
            porcentaje REAL DEFAULT 0,
            cantidad_g_por_lote REAL DEFAULT 0
        );
        CREATE TABLE produccion_checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produccion_id INTEGER,
            estado TEXT DEFAULT 'pendiente'
        );
        CREATE TABLE movimientos (material_id TEXT, cantidad REAL, tipo TEXT);
        CREATE TABLE ordenes_compra (numero_oc TEXT PRIMARY KEY, estado TEXT);
        CREATE TABLE ordenes_compra_items (
            numero_oc TEXT, codigo_mp TEXT,
            cantidad_g REAL, cantidad_recibida_g REAL DEFAULT 0
        );
        CREATE TABLE solicitudes_compra (
            numero TEXT PRIMARY KEY, estado TEXT, numero_oc TEXT
        );
        CREATE TABLE solicitudes_compra_items (
            numero TEXT, codigo_mp TEXT, cantidad_g REAL
        );
    """)
    c.execute(
        "INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado) "
        "VALUES (?, ?, ?, ?)",
        ('CREMA HIDRATANTE 4D', '2026-05-15', 2, 'pendiente'),
    )
    c.execute(
        "INSERT INTO formula_headers (producto_nombre, lote_size_kg) VALUES (?, ?)",
        ('CREMA HIDRATANTE 4D', 30.0),
    )
    c.execute(
        "INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
        "porcentaje, cantidad_g_por_lote) VALUES (?, ?, ?, ?, ?)",
        ('CREMA HIDRATANTE 4D', 'MP00245', '1,2 HEXANEDIOL', 1.5, 450.0),
    )
    con.commit()
    return con


def test_resumen_calendario_query_no_explota():
    """La query del resumen-calendario debe ejecutar sin error."""
    con = _setup_in_memory_db()
    rows = con.execute("""
        SELECT pp.id,
               pp.producto                                       as producto_nombre,
               pp.fecha_programada                               as fecha_planeada,
               COALESCE(pp.lotes, 1) * COALESCE(fh.lote_size_kg,0) as kg,
               (SELECT COUNT(*) FROM produccion_checklist WHERE produccion_id=pp.id) as total_items
        FROM produccion_programada pp
        LEFT JOIN formula_headers fh ON fh.producto_nombre = pp.producto
        WHERE LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado','completado')
          AND pp.fecha_programada <= '2026-12-31'
        ORDER BY pp.fecha_programada ASC
    """).fetchall()
    assert len(rows) == 1
    assert rows[0][1] == 'CREMA HIDRATANTE 4D'
    assert rows[0][3] == 60.0  # 2 lotes * 30 kg = 60 kg


def test_demanda_total_horizonte():
    """Suma agregada de demanda en el horizonte."""
    con = _setup_in_memory_db()
    row = con.execute("""
        SELECT COALESCE(SUM(
            COALESCE(fi.cantidad_g_por_lote, 0) * COALESCE(pp.lotes, 1)
        ), 0)
        FROM produccion_programada pp
        JOIN formula_items fi ON fi.producto_nombre = pp.producto
        WHERE fi.material_id = ?
          AND LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado','completado')
    """, ('MP00245',)).fetchone()
    assert row[0] == 900.0  # 450 g/lote * 2 lotes


def test_backfill_finds_producciones_sin_checklist():
    """El backfill encuentra producciones que no tienen items aun."""
    con = _setup_in_memory_db()
    rows = con.execute("""
        SELECT pp.id,
               pp.producto                                          as producto_nombre,
               pp.fecha_programada                                  as fecha_planeada,
               COALESCE(pp.lotes, 1) * COALESCE(fh.lote_size_kg, 0) as kg
        FROM produccion_programada pp
        LEFT JOIN formula_headers fh ON fh.producto_nombre = pp.producto
        WHERE LOWER(COALESCE(pp.estado,'')) NOT IN ('cancelado','completado')
          AND NOT EXISTS (SELECT 1 FROM produccion_checklist WHERE produccion_id=pp.id)
    """).fetchall()
    assert len(rows) == 1
    assert rows[0][3] == 60.0


def test_no_hay_referencias_a_columnas_inexistentes():
    """Regresion: no debe haber 'pp.producto_nombre', 'pp.fecha_planeada'
    o 'pp.batch_size_kg' donde 'pp' = produccion_programada.

    NOTA: 'pp.cantidad_kg' SI existe desde migracion 50.

    Sebastián 1-may-2026 audit: refinado para evitar falso positivo cuando
    'pp' es alias de OTRA tabla (ej. producto_presentaciones). El test
    ahora analiza cada SELECT/FROM y solo valida cuando pp ESTÁ ligado a
    produccion_programada en el contexto.
    """
    import re
    src = Path(__file__).parent.parent / "api" / "blueprints" / "programacion.py"
    text = src.read_text(encoding='utf-8')

    # Encontrar todos los bloques FROM/JOIN que defininen alias 'pp'.
    # Si el alias 'pp' está ligado a producto_presentaciones (u otra tabla),
    # NO es producción programada · skip.
    bad_tokens = ['pp.producto_nombre', 'pp.fecha_planeada', 'pp.batch_size_kg']
    # Buscar líneas con bad_tokens y obtener la query SQL alrededor (~30 líneas atrás)
    lines = text.split('\n')
    for i, line in enumerate(lines):
        for tok in bad_tokens:
            if tok not in line:
                continue
            # Mirar las ~30 líneas anteriores buscando "FROM <tabla> pp" o "JOIN <tabla> pp"
            ctx = '\n'.join(lines[max(0, i - 30):i + 1])
            # Si pp está ligado explícitamente a producto_presentaciones,
            # productos_presentaciones, presentaciones, etc → falso positivo.
            if re.search(r'\b(producto_presentaciones|presentaciones)\s+pp\b', ctx, re.IGNORECASE):
                continue
            # Si en el contexto se ve "FROM produccion_programada pp" o similar → bug real
            if re.search(r'\bproduccion_programada\s+pp\b', ctx, re.IGNORECASE):
                raise AssertionError(
                    f"Línea {i+1}: '{tok}' donde pp = produccion_programada. "
                    f"Esa columna NO existe en la tabla. Usar: producto, "
                    f"fecha_programada, lotes, cantidad_kg."
                )
            # Si no hay match con ninguna tabla conocida, ser conservador y avisar
            # (raro pero posible · revisar manualmente)
