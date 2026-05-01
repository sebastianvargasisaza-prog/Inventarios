# database.py â inicializaciÃ³n de BD y seeds
# Fase B refactor: extraÃ­do de index.py
import os
import sqlite3
import random
from datetime import datetime

from config import DB_PATH


def _configure_conn(conn):
    """Aplica pragmas de performance y seguridad a cada conexion SQLite.
    
    WAL (Write-Ahead Log): permite N lectores concurrentes mientras hay
    un escritor activo. Critico para multiples workers Gunicorn.
    busy_timeout: los workers esperan hasta 5s por el lock de escritura
    en lugar de fallar inmediatamente — elimina 'database is locked'.
    cache_size: 20MB de cache en memoria por conexion.
    temp_store: tablas temporales en RAM (mas rapido para sorts/joins).
    """
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")   # durabilidad vs velocidad optima
    conn.execute("PRAGMA cache_size=-20000")    # 20MB cache (negativo = KB)
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA busy_timeout=5000")    # 5s espera por lock — multi-worker
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_db():
    """Conexion SQLite per-request usando Flask g (patron recomendado Flask).

    Cerrada automaticamente por teardown_appcontext al final del request
    incluyendo error paths. Con WAL mode y busy_timeout, segura para uso
    con multiples workers Gunicorn simultaneos.
    """
    try:
        from flask import g
        if "db" not in g:
            g.db = _configure_conn(sqlite3.connect(DB_PATH))
        return g.db
    except RuntimeError:
        # Sin app context: scripts de init, tests, herramientas CLI
        return _configure_conn(sqlite3.connect(DB_PATH))


# ── Helper para migraciones idempotentes ──────────────────────────────────────
# Errores benignos que indicam "el cambio ya está aplicado" — NO se loguean.
# Cualquier otro OperationalError SE LOGUEA y SE RELANZA (típico de typo SQL,
# columna referencia inválida, etc.).
_BENIGN_DDL_ERRORS = (
    "duplicate column",
    "already exists",
    "no such table",   # legítimo en DROP IF NOT EXISTS-style code
)


def safe_alter(conn, sql):
    """Ejecuta un ALTER/CREATE idempotente.

    Reemplaza el patrón legacy `try: conn.execute(sql); except: pass` que
    silencia TODOS los errores incluyendo typos. Solo ignora "duplicate column",
    "already exists" y similares — cualquier otro error se loguea con contexto
    y se relanza para que la migración falle visiblemente.

    Args:
        conn: conexion SQLite
        sql:  sentencia DDL (ALTER TABLE, CREATE INDEX, etc.)

    Returns:
        True si se ejecutó nuevo cambio, False si ya estaba aplicado.

    Raises:
        sqlite3.OperationalError si el error NO es benigno.
    """
    import logging as _logging
    try:
        conn.execute(sql)
        return True
    except sqlite3.OperationalError as e:
        msg = str(e).lower()
        if any(b in msg for b in _BENIGN_DDL_ERRORS):
            return False
        _logging.getLogger("inventario.db").error(
            "safe_alter failed: %s -- %s", sql[:100], e
        )
        raise


# ─── Sistema de migración de esquema ─────────────────────────────────────────
# Reglas:
#   • Añadir migraciones SOLO al final de la lista. Nunca modificar existentes.
#   • Cada versión es idempotente: los errores de "duplicate column name" se
#     ignoran, cualquier otro error de SQLite propaga la excepción.
#   • Versión 1 = baseline: toda la estructura inicial de init_db() ya existe
#     en producción — se registra sin ejecutar sentencias.
#
# Para añadir una columna nueva a una tabla existente:
#   1. Agregar tupla al final de MIGRATIONS con la sentencia ALTER TABLE.
#   2. NO añadir try/except inline en init_db() — usar solo este sistema.

# Seed de equipos del Excel "LISTADO MAESTRO DE EQUIPOS 2026" (Alejandro,
# 30-abr-2026). 104 equipos en areas reales post-INVIMA. Usado por
# migracion 63. UNIQUE(codigo, ubicacion_raw) para idempotencia.
_SEED_EQUIPOS_PLANTA_SQL = r"""INSERT OR IGNORE INTO equipos_planta
  (codigo, nombre, area_codigo, ubicacion_raw, tipo, capacidad_raw, capacidad_litros, capacidad_kg)
VALUES
    ('BL-PRD-001', 'Balanza EJ-6100', 'DISP', 'Dispensación', 'balanza', '', NULL, NULL),
    ('BL-PRD-002', 'Balanza Precisa 620M', 'DISP', 'Producción-Dispensación', 'balanza', '620 g', NULL, NULL),
    ('PC-COC-002', 'Picnómetro de acero', 'CC', 'Control de Calidad', 'picnometro', '37ml', 0.037, NULL),
    ('BL-COC-001', 'Balanza Mix - A3000g', 'CC', 'Control de Calidad', 'balanza', '2,0-3000g d:0.1g', NULL, NULL),
    ('BL-PRD-003', 'Balanza Mix - H', 'ENV2', 'Envasado 2', 'balanza', '0,01-600g', NULL, NULL),
    ('BC-PRD-001', 'Bascula Digital TCS-150Kg', 'DISP', 'Producción-Dispensación', 'bascula', '150Kg', NULL, 150.0),
    ('BL-PRD-004', 'Balanza Mix-A3000g', 'DISP', 'Dispensación', 'balanza', '2,0-3000g d:0.1g', NULL, NULL),
    ('TM-PRD-001', 'Termómetro Digital HI98509', 'FAB2', 'Fabricacion 2', 'termometro', '< 50 A 150°C', NULL, NULL),
    ('HG-PRD-001', 'Homogeneizador D-500 DLAB', 'FAB1', 'Fabricación 1', 'homogenizador', '10000-29000RPM', NULL, NULL),
    ('AG-PRD-001', 'Agitador OS40 DLAB', 'FAB3', 'Fabricación 3', 'agitador', '50-2200RPM', NULL, NULL),
    ('AG-PRD-002', 'Agitador OS40 DLAB', 'FAB2', 'Fabricación 2', 'agitador', '50-2200RPM', NULL, NULL),
    ('AG-PRD-003', 'Agitador OS-70 PRO', 'FAB1', 'Fabricación 1', 'agitador', '50-1100RPM', NULL, NULL),
    ('BM-PRD-001', 'Equipo de Mano (Batidor Manual) DD653', 'FAB1', 'Fabricación 1', 'batidor', 'N/A', NULL, NULL),
    ('BM-PRD-002', 'Equipo de Mano (Batidor Manual) DD653', 'FAB2', 'Fabricación 2', 'batidor', 'N/A', NULL, NULL),
    ('BM-PRD-003', 'Equipo de Mano (Batidor Manual) DD653', 'FAB2', 'Fabricación 2', 'batidor', 'N/A', NULL, NULL),
    ('SA-PRD-001', 'Sistema de Agua Blue Tide Ro', 'LAV', 'Área de lavado', 'sistema_agua', 'N/A', NULL, NULL),
    ('PL-PRD-001', 'Plancha Calentamiento 3P', 'FAB1', 'Fabricación 1', 'plancha', '60-300°C', NULL, NULL),
    ('PL-PRD-002', 'Plancha Calentamiento 3P', 'FAB2', 'Fabricación 2', 'plancha', '60-300°C', NULL, NULL),
    ('ES-PRD-001', 'Envasadora Semiautomática FLUITEC', 'ENV2', 'Envasado 2', 'envasadora', 'N/A', NULL, NULL),
    ('RF-PRD-001', 'Nevera', 'ALM_MP', 'Producción-Almacenamiento de materias primas', 'nevera', '2-8°C', NULL, NULL),
    ('HA-PRD-001', 'Hervidor de agua', 'FAB2', 'Fabricación 2', 'hervidor', 'N/A', NULL, NULL),
    ('TF-PRD-001', 'Tanque de fabricación 100L', 'FAB1', 'Fabricación 1', 'tanque', '100L', 100.0, NULL),
    ('TF-PRD-002', 'Tanque de fabricación 70L', 'FAB1', 'Fabricación 1', 'tanque', '70L', 70.0, NULL),
    ('TF-PRD-003', 'Tanque de fabricación 50L', 'FAB2', 'Fabricación 2', 'tanque', '50L', 50.0, NULL),
    ('TF-PRD-004', 'Tanque de fabricación 50L', 'FAB2', 'Fabricación 2', 'tanque', '50L', 50.0, NULL),
    ('DA-PRD-001', 'Destilador de agua', 'LAV', 'ÁREA DE LAVADO', 'destilador', 'N/A', NULL, NULL),
    ('BC-PRD-001', 'Bascula Digital TCS-150Kg', 'RECEP', 'Recepción de Insumos', 'bascula', '150Kg', NULL, 150.0),
    ('TH-PRD-001', 'Termohigrómetro Digital', 'PAS', 'Pasillo general', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('TH-PRD-002', 'Termohigrómetro Digital', 'ALM_ENV', 'Almacenamiento envases', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('TH-PRD-003', 'Termohigrómetro Digital', 'ALM_MP', 'Almacenamiento materias primas', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('TH-PRD-004', 'Termohigrómetro Digital', 'SAGUA', 'Sistema de agua', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('TH-PRD-005', 'Termohigrómetro Digital', 'DISP', 'Dispensación', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('TH-PRD-008', 'Termohigrómetro Digital', 'FAB1', 'Fabricación 1', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('TH-PRD-007', 'Termohigrómetro Digital', 'ENV1', 'Envasado 1', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('TH-PRD-006', 'Termohigrómetro Digital', 'FAB2', 'Fabricación 2', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('TH-PRD-009', 'Termohigrómetro Digital', 'ENV2', 'Envasado 2', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('TH-COC-001', 'Termohigrómetro Digital', 'CC', 'Control de calidad', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('TH-BDG-001', 'Termohigrómetro Digital', 'BDG', 'Bodega producto terminado', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('TH-BDG-002', 'Termohigrómetro Digital', 'OTROS', 'Producto en proceso', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('TH-PRD-002B', 'Termohigrómetro Digital', 'FAB3', 'Fabricacion 3', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('TH-BDG-003', 'Termohigrómetro Digital', 'MUESTRAS', 'Muestras de retención', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('TH-PRD-010', 'Termohigrómetro Digital', 'ESC', 'Esclusa posterior', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('TH-PRD-011', 'Termohigrómetro Digital', 'RECEP', 'Recepción de insumos', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('TH-BDG-003B', 'Termohigrómetro Digital', 'ACOND', 'Acondicionamiento', 'termohigrometro', '-10°C ͂ 50°', NULL, NULL),
    ('CA-PRD-001', 'Compresor de aire', 'VENT', 'Producción-Sistema de Ventilación', 'compresor', '53 - 118 °F', NULL, NULL),
    ('BL-PRD-005', 'Balanza Mix - H', 'ENV1', 'Envasado 1', 'balanza', '0,01-600g', NULL, NULL),
    ('PP-COC-001', 'Pesa patrón 1g', 'CC', 'Control de Calidad', 'pesa_patron', '1g', NULL, NULL),
    ('PP-COC-002', 'Pesa patrón 50 g', 'CC', 'Control de Calidad', 'pesa_patron', '50g', NULL, NULL),
    ('PP-COC-003', 'Pesa patrón 10kg', 'CC', 'Control de Calidad', 'pesa_patron', '10kg', NULL, 10.0),
    ('PP-COC-004', 'Pesa patrón 20kg', 'CC', 'Control de Calidad', 'pesa_patron', '20kg', NULL, 20.0),
    ('ML-BDG-001', 'Maquina loteadora inject', 'ACOND', 'Acondicionamiento', 'loteadora', 'Hasta 5 líneas de impresión', NULL, NULL),
    ('LM-BDG-001', 'Loteadora manual de tinta', 'ACOND', 'Acondicionamiento', 'loteadora', '1mm hasta 12mm', NULL, NULL),
    ('AG-PRD-004', 'Agitador Digital OS40-PRO Wisdom', 'FAB2', 'Fabricación 2', 'agitador', '50-2200RPM', NULL, NULL),
    ('HG-PRD-002', 'Homogenizador D-500 WISDOM', 'FAB3', 'Fabricación 3', 'homogenizador', '10,000-30,000 RPM', NULL, NULL),
    ('VS-COC-001', 'Viscosímetro Brookfield', 'CC', 'Control de Calidad', 'viscosimetro', '1-1000,000mp.s', NULL, NULL),
    ('MR-PRD-001', 'Molino de 3 rodillos', 'FAB2', 'Fabricación 2', 'molino', '1 a 18 micras / 2 a 5 kg/h', NULL, 5.0),
    ('VS-COC-002', 'Viscosímetro Wisdom', 'CC', 'Control de Calidad', 'viscosimetro', '1-1000,000mp.s', NULL, NULL),
    ('PA-PRD-001', 'Plancha de calentamiento con agitador', 'FAB1', 'Fabricación 1', 'agitador', '0°C-550°C Y 1500rpm', NULL, NULL),
    ('PA-PRD-002', 'Plancha de calentamiento con agitador', 'FAB2', 'Fabricación 2', 'agitador', '0°C-550°C Y 1500rpm', NULL, NULL),
    ('PA-PRD-003', 'Plancha de calentamiento con agitador', 'FAB3', 'Fabricación 3', 'agitador', '0°C-550°C Y 1500rpm', NULL, NULL),
    ('EF-COC-001', 'Espectrofotómetro (Colorimetro)', 'CC', 'Control de Calidad', 'espectrofotometro', '360 nm - 700 nm', NULL, NULL),
    ('PC-COC-003', 'Picnómetro de vidrio', 'CC', 'Control de Calidad', 'picnometro', '10,3108 ±0,01 cm', NULL, NULL),
    ('PC-COC-004', 'Picnómetro de vidrio', 'CC', 'Control de Calidad', 'picnometro', '10,3108 ±0,01 cm', NULL, NULL),
    ('PC-COC-001', 'Picnómetro de vidrio', 'CC', 'Control de Calidad', 'picnometro', '10,3108 ±0,01 cm', NULL, NULL),
    ('PR-COC-001', 'Pie de Rey', 'CC', 'Control de Calidad', 'pie_de_rey', '0-150mm/0-6 in', NULL, NULL),
    ('CL-PRD-001', 'Cabina de Flujo laminar', 'DISP', 'Producción - Dispensación', 'cabina_flujo', '220V / 330W / 60Hz', NULL, NULL),
    ('ES-PRD-002', 'Envasadora Semiautomática XIAOYING', 'ENV1', 'Envasado 1', 'envasadora', '10-120ML', 0.12, NULL),
    ('HG-PRD-003', 'Homogenizador Mixer de 100 L', 'FAB1', 'Fabricación 1', 'homogenizador', '0-3000rpm. T 0-100°C', NULL, NULL),
    ('PH-COC-001', 'pHmetro HANNA HI', 'CC', 'Control de Calidad', 'phmetro', '0-14,00 ph', NULL, NULL),
    ('HG-PRD-004', 'Homogenizador D-160 Wisdom', 'FAB2', 'Fabricación 2', 'homogenizador', '8000-32000rpm', NULL, NULL),
    ('MM-PRD-001', 'Marmita', 'PROD', 'Producción', 'marmita', '250L', 250.0, NULL),
    ('ST-PRD-001', 'Soplador térmico (pistola de calor)', 'DISP', 'Dispensación', 'soplador', '60°C-500°C', NULL, NULL),
    ('BL-COC-002', 'Balanza analitica AXIS', 'CC', 'Control de calidad', 'balanza', '0-210g d:0,001g', NULL, NULL),
    ('EM-PRD-003', 'Envasadora Manual KITEM', 'ENV1', 'Envasado 1', 'envasadora', '10ml-50ml', 0.01, NULL),
    ('EM-PRD-004', 'Envasadora Manual KITEM', 'ENV2', 'Envasado 2', 'envasadora', '10ml-50ml', 0.01, NULL),
    ('OF-PRD-001', 'Olla de fabricación BESNEL', 'FAB_FLOAT', 'Fabricación', 'olla', '7.5 L', 7.5, NULL),
    ('OF-PRD-002', 'Olla de fabricación BESNEL', 'FAB_FLOAT', 'Fabricación', 'olla', '7.5 L', 7.5, NULL),
    ('OF-PRD-003', 'Olla de fabricación BESNEL', 'FAB_FLOAT', 'Fabricación', 'olla', '7.5 L', 7.5, NULL),
    ('OF-PRD-004', 'Olla de fabricación BESNEL', 'FAB_FLOAT', 'Fabricación', 'olla', '7.5 L', 7.5, NULL),
    ('ES-PRD-003', 'Envasadora semiautomática BOINES', 'ENV1', 'Envasado 1', 'envasadora', '30g-10000g', NULL, NULL),
    ('CA-PRD-002', 'Compresor de aire TRUPER', 'CUB', 'Cubierta', 'compresor', '24 L / 800 kPa (116 PSI)', 24.0, NULL),
    ('GE-PRD-001', 'Generador eléctrico portátil PRETUL', 'PISO3', 'Tercer piso', 'generador', '2,500 W (Potencia máxima) / 2,200 W', NULL, NULL),
    ('ME-PRD-001', 'Mezclador eléctrico', 'FAB1', 'Fabricación 1', 'homogenizador', '2400W. / Hasta 1200 r/min', NULL, NULL),
    ('ME-PRD-002', 'Mezclador eléctrico', 'FAB2', 'Fabricación 2', 'homogenizador', '2400W. / Hasta 1200 r/min', NULL, NULL),
    ('ME-PRD-003', 'Mezclador eléctrico', 'FAB3', 'Fabricación 3', 'homogenizador', '2400W. / Hasta 1200 r/min', NULL, NULL),
    ('NV-PRD-001', 'Nevera Midea (secado)', 'FAB2', 'Fabricación 2', 'nevera', '-5°C a -18°C', NULL, NULL),
    ('TF-PRD-005', 'Tanque de fabricación 120L', 'FAB3', 'Fabricación 3', 'tanque', '100L', 100.0, NULL),
    ('TF-PRD-006', 'Tanque de fabricación 400L', 'FAB3', 'Fabricación 3', 'tanque', '400L', 400.0, NULL),
    ('TF-PRD-007', 'Tanque de fabricación 400L', 'FAB3', 'Fabricación 3', 'tanque', '400L', 400.0, NULL),
    ('TF-PRD-008', 'Tanque de fabricación 200L', 'FAB1', 'Fabricación 1', 'tanque', '200L', 200.0, NULL),
    ('TF-PRD-009', 'Tanque de fabricación Enjuague bucal 25L', 'FAB2', 'Fabricación 2', 'tanque', '20L', 20.0, NULL),
    ('TF-PRD-010', 'Tanque de fabricación Repelentes 30L', 'FAB2', 'Fabricación 2', 'tanque', '30L', 30.0, NULL),
    ('TF-PRD-011', 'Tanque de fabricación 50L', 'FAB2', 'Fabricación 2', 'tanque', '50L', 50.0, NULL),
    ('TF-PRD-012', 'Tanque de fabricación 30L', 'FAB_FLOAT', 'Fabricación según la necesidad', 'tanque', '20L', 20.0, NULL),
    ('TF-PRD-013', 'Tanque de fabricación 15L', 'FAB_FLOAT', 'Fabricación según la necesidad', 'tanque', '10L', 10.0, NULL),
    ('TF-PRD-014', 'Tanque de fabricación 20L', 'FAB_FLOAT', 'Fabricación según la necesidad', 'tanque', '6L', 6.0, NULL),
    ('TF-PRD-015', 'Tanque de fabricación 3L', 'FAB_FLOAT', 'Fabricación', 'tanque', '3L', 3.0, NULL),
    ('TF-PRD-016', 'Tanque de fabricación 10L', 'FAB_FLOAT', 'Fabricación según la necesidad', 'tanque', '10L', 10.0, NULL),
    ('ML-BDG-002', 'Inkjet printer', 'ACOND', 'Acondicionamiento', 'loteadora', '2 mm a 12.7 mm', NULL, NULL),
    ('TN-PRD-001', 'Tapadora neumático', 'ENV1', 'Envasado', 'tapadora', '', NULL, NULL),
    ('TN-PRD-002', 'Tapadora neumático', 'ENV2', 'Envasado', 'tapadora', '', NULL, NULL),
    ('ST-PRD-002', 'Soplador térmico (pistola de calor) BAUKER', 'ACOND', 'Acondicionamiento', 'soplador', '50°C- 600°C', NULL, NULL),
    ('ES-PRD-004', 'Envasadora semiautomática KM-B1000V', 'FAB_FLOAT', 'Fabricación según necesidad', 'envasadora', '', NULL, NULL),
    ('TP-PRD-001', 'Tapadora Electroneumática', 'FAB_FLOAT', 'Envasado según necesidad', 'tapadora', '', NULL, NULL)"""


# Seed de cronograma de limpieza profunda (Sebastian + Alejandro 30-abr-2026,
# brief K). Rotación L-Ma-J-V de las 9 áreas obligatorias. Vacío al inicio —
# se llena vía scheduler /api/planta/limpieza-profunda/generar.
_AREAS_LIMPIEZA_PROFUNDA = (
    'FAB1', 'FAB2', 'FAB3', 'ENV1', 'ENV2',
    'DISP', 'LAV', 'ESC1', 'ALMP'
)


MIGRATIONS: list[tuple[int, str, list[str]]] = [
    (1, "baseline — sistema de migraciones instalado", []),
    (2, "maestro_mps: proveedor_preferido", [
        "ALTER TABLE maestro_mps ADD COLUMN proveedor_preferido TEXT DEFAULT \'\'",
    ]),
    (3, "clientes: monto_credito_cop, dias_credito", [
        "ALTER TABLE clientes ADD COLUMN monto_credito_cop REAL DEFAULT 0",
        "ALTER TABLE clientes ADD COLUMN dias_credito INTEGER DEFAULT 30",
    ]),
    (4, "pedidos: canal_venta, descuento_total_cop", [
        "ALTER TABLE pedidos ADD COLUMN canal_venta TEXT DEFAULT \'Directo\'",
        "ALTER TABLE pedidos ADD COLUMN descuento_total_cop REAL DEFAULT 0",
    ]),
    # Próximas migraciones aquí — nunca modificar las anteriores
    (5, "formula_items: cantidad_g_por_lote + formula_headers: lote_size_kg", [
        "ALTER TABLE formula_items ADD COLUMN cantidad_g_por_lote REAL DEFAULT 0",
        "ALTER TABLE formula_headers ADD COLUMN lote_size_kg REAL DEFAULT 0",
        """CREATE TABLE IF NOT EXISTS sku_producto_map (
            sku TEXT PRIMARY KEY,
            producto_nombre TEXT NOT NULL,
            activo INTEGER DEFAULT 1
        )""",
    ]),
    (6, "seed: formulas maestras desde xlsx (31 productos)", [
        "DELETE FROM formula_headers",
        """INSERT OR REPLACE INTO formula_headers (producto_nombre, unidad_base_g, lote_size_kg) VALUES
        ('AZ HIBRID CLEAR', 36000.0, 36.0),
        ('CONTORNO DE CAFEINA', 10000.0, 10.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 10000.0, 10.0),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 14000.0, 14.0),
        ('CREMA CORPORAL RENOVA BODY', 90000.0, 90.0),
        ('CREMA DE UREA', 7000.0, 7.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 25000.0, 25.0),
        ('EMULSION HIDRATANTE  B3+BHA', 40000.0, 40.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 30000.0, 30.0),
        ('EMULSION LIMPIADORA', 100000.0, 100.0),
        ('ESENCIA DE CENTELLA ASIATICA', 50000.0, 50.0),
        ('ESENCIA ILUMINADORA', 30000.0, 30.0),
        ('GEL HIDRATANTE', 35000.0, 35.0),
        ('LIMPIADOR FACIAL BHA 2%', 200000.0, 200.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 70000.0, 70.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 200000.0, 200.0),
        ('MASCARILLA HIDRATANTE', 10000.0, 10.0),
        ('SUERO ANTIOXIDANTE RENOVA C10', 12000.0, 12.0),
        ('SUERO ANTIOXIDANTE VITAMINA C+B3', 30000.0, 30.0),
        ('SUERO AZ + B3', 15000.0, 15.0),
        ('Suero Exfoliante BHA 2%', 60000.0, 60.0),
        ('SUERO EXFOLIANTE NOVA PHA', 14000.0, 14.0),
        ('SUERO HIDRATANTE AH 1.5%', 90000.0, 90.0),
        ('SUERO ILUMINADOR AHA+AH.', 1000.0, 1.0),
        ('SUERO ILUMINADOR TRX', 90000.0, 90.0),
        ('SUERO MULTIPEPTIDOS', 35000.0, 35.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 120000.0, 120.0),
        ('Suero RETINAL +', 60000.0, 60.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 10000.0, 10.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 20000.0, 20.0)""",
        "DELETE FROM formula_items",
        """INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) VALUES
        ('AZ HIBRID CLEAR', 'MPAGUALI01', 'AGUA DESIONIZADA', 47.77, 17197.199999999997),
        ('AZ HIBRID CLEAR', 'MPCARBSO01', 'CARBOPOL', 0.2, 72.00000000000001),
        ('AZ HIBRID CLEAR', 'MPGOXASO01', 'GOMA XANTAN', 0.1, 36.00000000000001),
        ('AZ HIBRID CLEAR', 'MPEDDISO01', 'EDTA DISODICO', 0.05, 18.000000000000004),
        ('AZ HIBRID CLEAR', 'MPTRIELO01', 'TRIETANOLAMINA 85%', 1.25, 450.0),
        ('AZ HIBRID CLEAR', 'MPPROLISO01', 'PROPILENGLICOL', 20.0, 7200.0),
        ('AZ HIBRID CLEAR', 'MPACCASAS01', 'ACIDO CAPRILOIL SALICILICO', 0.5, 180.0),
        ('AZ HIBRID CLEAR', 'MPACAZSO01', 'ACIDO AZELAICO', 6.0, 2160.0),
        ('AZ HIBRID CLEAR', 'MPHIDSOLI01', 'HIDROXIDO DE SODIO (SODA CAUSTICA)', 0.95, 341.99999999999994),
        ('AZ HIBRID CLEAR', 'MPAZDISO01', 'AZELOLIL DIGLICINATO DE POTASIO', 5.0, 1800.0),
        ('AZ HIBRID CLEAR', 'MPAZEDILO01', 'EPI-ON (AZELAMIDOPROPIL DIMETIL AMINA)', 4.0, 1440.0),
        ('AZ HIBRID CLEAR', 'MPNIACSO01', 'NIACINAMIDA', 5.0, 1800.0),
        ('AZ HIBRID CLEAR', 'MPACTRSO01', 'ACIDO TRANEXAMICO', 3.0, 1080.0),
        ('AZ HIBRID CLEAR', 'MPFOASSO01', 'FOSFATO DE ASCORBILO SODICO', 2.0, 720.0),
        ('AZ HIBRID CLEAR', 'MPZINPCASO1', 'ZINC PCA', 0.5, 180.0),
        ('AZ HIBRID CLEAR', 'MPACHISO01', 'ACIDO HIALURONICO 50 KD', 0.05, 18.000000000000004),
        ('AZ HIBRID CLEAR', 'MPACHISO02', 'ACIDO HIALURONICO 300 KD', 0.05, 18.000000000000004),
        ('AZ HIBRID CLEAR', 'MPPANTSO01', 'PANTENOL POLVO', 0.05, 18.000000000000004),
        ('AZ HIBRID CLEAR', 'MPECTOSO01', 'ECTOINA', 0.1, 36.00000000000001),
        ('AZ HIBRID CLEAR', 'MPBETASO02', 'BETAINA', 0.05, 18.000000000000004),
        ('AZ HIBRID CLEAR', 'MPTERSSO01', 'TERPENOS SOLUBLES 80%', 0.05, 18.000000000000004),
        ('AZ HIBRID CLEAR', 'MPFISOSO01', 'FITATO DE SODIO', 0.03, 10.8),
        ('AZ HIBRID CLEAR', 'MPACETETSO01', 'ACETYL TETRAPEPTIDE-40', 0.003, 1.08),
        ('AZ HIBRID CLEAR', 'MPHEXDILI01', '1,2 HEXANEDIOL', 0.5, 180.0),
        ('AZ HIBRID CLEAR', 'MPVITESO01', 'VITAMINA E POLVO', 0.8, 288.00000000000006),
        ('AZ HIBRID CLEAR', 'MPGRANLI01', 'GRANSIL VX419', 1.0, 360.0),
        ('AZ HIBRID CLEAR', 'MPBIOFELI01', 'BIOSURE FE', 1.0, 360.0),
        ('CONTORNO DE CAFEINA', 'MPAGUALI01', 'AGUA DESIONIZADA', 82.57, 8257.0),
        ('CONTORNO DE CAFEINA', 'MPPROPLI01', 'PROPILENGLICOL', 5.0, 500.0),
        ('CONTORNO DE CAFEINA', 'MPACTRSO01', 'ACIDO TRANEXAMICO', 3.0, 300.0),
        ('CONTORNO DE CAFEINA', 'MPGLICLI01', 'GLICERINA', 3.0, 300.0),
        ('CONTORNO DE CAFEINA', 'MPCAANSO01', 'CAFEINA', 1.5, 150.0),
        ('CONTORNO DE CAFEINA', 'MPGLUCSO02', 'GLUCONOLACTONA', 1.0, 100.0),
        ('CONTORNO DE CAFEINA', 'MPFENOLI01', 'FENOXIETANOL', 1.0, 100.0),
        ('CONTORNO DE CAFEINA', 'MPALANSO01', 'ALANTOINA', 0.5, 50.0),
        ('CONTORNO DE CAFEINA', 'MPVITESO01', 'VITAMINA E POLVO', 0.5, 50.0),
        ('CONTORNO DE CAFEINA', 'MPACHISO01', 'ACIDO HIALURONICO 50KD', 0.3, 30.0),
        ('CONTORNO DE CAFEINA', 'MPSILILI01', 'SILICONA LIQUIDA', 0.3, 30.0),
        ('CONTORNO DE CAFEINA', 'MPSOPOSO01', 'SORBATO DE POTASIO', 0.3, 30.0),
        ('CONTORNO DE CAFEINA', 'MPACLALI02', 'ACIDO LACTICO', 0.3, 30.0),
        ('CONTORNO DE CAFEINA', 'MPBESOSO01', 'BENZOATO DE SODIO', 0.3, 30.0),
        ('CONTORNO DE CAFEINA', 'MPACHISO03', 'ACIDO HIALURONICO 1500 KD', 0.2, 20.0),
        ('CONTORNO DE CAFEINA', 'MPADENSO01', 'ADENOSINA', 0.1, 10.0),
        ('CONTORNO DE CAFEINA', 'MPALVESO01', 'ALOE VERA', 0.05, 5.0),
        ('CONTORNO DE CAFEINA', 'MPEXGOSO01', 'CENTELLA', 0.05, 5.0),
        ('CONTORNO DE CAFEINA', 'MPACTESO01', 'ACETYL TETRAPETIDE-5', 0.03, 3.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPAGUALI01', 'AGUA DESIONIZADA', 78.51, 7851.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPPROPLI01', 'PROPILENGLICOL', 5.0, 500.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPNIACSO01', 'NIACINAMIDA', 5.0, 500.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPGLICLI01', 'GLICERINA', 3.0, 300.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPSILILI01', 'SILICONA LIQUIDA', 1.5, 150.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPGLUCSO01', 'N-ACETIL GLUCOSAMINA', 1.0, 100.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPGLUCSO02', 'GLUCONOLACTONA', 1.0, 100.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPFENOLI01', 'FENOXIETANOL', 1.0, 100.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPTRIESO01', 'TRIETANOLAMINA 85%', 1.0, 100.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPCAANSO01', 'CAFEINA', 0.5, 50.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPASGLSO01', 'ASCORBIL GLUCOSIDE', 0.5, 50.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPVITESO01', 'VITAMINA E POLVO', 0.5, 50.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPACHISO03', 'ACIDO HIALURONICO 1500 KD', 0.3, 30.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPACHISO01', 'ACIDO HIALURONICO 50 KD', 0.3, 30.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPACHISO02', 'ACIDO HIALURONICO 300 KD', 0.3, 30.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPEZ4USO01', 'EZ-4U', 0.2, 20.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPPECOSO01', 'PEPTIDOS DE COLAGENO POLVO', 0.1, 10.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPPANTSO01', 'PANTENOL POLVO', 0.1, 10.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPADENSO01', 'ADENOSINA', 0.05, 5.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPGLICSO01', 'GLICINA', 0.05, 5.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPPALTRISO02', 'PALMIYOL TRIPEPTIDE-1', 0.015, 1.5),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPACTESO01', 'ACETYL TETRAPEPTIDE-5', 0.015, 1.5),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPACHESO01', 'ACETYL HEXAPEPTIDE-8', 0.015, 1.5),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPPALTRISO01', 'PALMIYOL TRIPEPTIDE-5', 0.015, 1.5),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPPALTESO01', 'PALMIYOL TETRAPEPTIDE-7', 0.01, 1.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPCOTRSO01', 'COOPER TRIPEPTIDE-1', 0.01, 1.0),
        ('CONTORNO DE OJOS MULTIPEPTIDOS', 'MPEXGOSO01', 'CENTELLA ASIATICA POLVO', 0.01, 1.0),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPAGUAS01', 'AGUA DESIONIZADA', 71.625, 10027.5),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPACTRSO01', 'ACIDO TRANEXAMICO', 5.0, 700.0),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPGLICLI01', 'GLICERINA', 5.0, 700.0),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPPROPLI01', 'PROPILENGLICOL', 5.0, 700.0),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPNIACSO01', 'NIACINAMIDA', 3.0, 420.0),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPSILILI01', 'SILICONA LIQUIDA', 2.0, 280.0),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPALCESO01', 'ALCOHOL CETILICO', 1.5, 210.0),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPESCULI01', 'ESCUALENO', 1.5, 210.0),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPGLUCSO01', 'N-ACETILGLUCOSAMINA', 1.5, 210.0),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPBETASO01', 'BETAINA', 1.0, 140.0),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPGLUCSO02', 'GLUCONOLACTONA', 0.5, 70.0),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPACHISO01', 'ACIDO HILAURONICO 50 KD', 0.5, 70.0),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPALANSO01', 'ALANTOINA', 0.5, 70.0),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPVITESO01', 'VITAMINA E POLVO', 0.5, 70.0),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPEZ4USO01', 'EZ-4U', 0.4, 56.00000000000001),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPTEANSO01', 'L-TEANINA', 0.1, 14.000000000000002),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPBETASO02', 'BETAGLUCAM', 0.05, 7.000000000000001),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPPECOSO01', 'PEPTIDOS DE COLAGENO POLVO', 0.05, 7.000000000000001),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPTINSO001', 'TINOGARD TT', 0.03, 4.2),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPRETSO01', 'RETINALDEHIDO', 0.025, 3.5000000000000004),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPPALTRISO02', 'PALMITOYL TRIPEPTIDE-1', 0.01, 1.4000000000000001),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPPALTRISO01', 'PALMITOYL TETRAPEPTIDE-7', 0.01, 1.4000000000000001),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPACHESO01', 'ACETYL HEXAPEPTIDE-8', 0.01, 1.4000000000000001),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPSILISO01', 'SILIMARINA', 0.01, 1.4000000000000001),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'MPBAKULI01', 'BAKUCHIOL', 0.15, 21.0),
        ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', '', 'ADENOSINA', 0.03, 4.2),
        ('CREMA CORPORAL RENOVA BODY', 'MPAGUALI01', 'AGUA DESIONIZADA', 64.2, 57780.0),
        ('CREMA CORPORAL RENOVA BODY', 'MPNIACSO01', 'NIACINAMIDA', 2.0, 1800.0),
        ('CREMA CORPORAL RENOVA BODY', 'MPUREASO01', 'UREA', 10.0, 9000.0),
        ('CREMA CORPORAL RENOVA BODY', 'MPGLICLI01', 'GLICERINA', 5.0, 4500.0),
        ('CREMA CORPORAL RENOVA BODY', 'MPPROPLI01', 'PROPILENGLICOL', 5.0, 4500.0),
        ('CREMA CORPORAL RENOVA BODY', 'MPQUCRE01', 'QUINCREAM', 2.0, 1800.0),
        ('CREMA CORPORAL RENOVA BODY', 'MPFENOLI01', 'FENOXIETANOL', 1.0, 900.0),
        ('CREMA CORPORAL RENOVA BODY', 'MPPALISO01', 'PALMITATO DE ISOPROPILO', 1.0, 900.0),
        ('CREMA CORPORAL RENOVA BODY', 'MPSILILI01', 'SILICONA LIQUIDA', 5.0, 4500.0),
        ('CREMA CORPORAL RENOVA BODY', 'MPDIADI01', 'ADIPATO DE BUTIL', 2.0, 1800.0),
        ('CREMA CORPORAL RENOVA BODY', 'MPVITAELI01', 'VITAMINA E LIQUIDA', 0.5, 450.0),
        ('CREMA CORPORAL RENOVA BODY', 'MPACJOLI01', 'ACEITE DE JOJOBA', 1.0, 900.0),
        ('CREMA CORPORAL RENOVA BODY', 'MPACARLI01', 'ACEITE DE ARGAN', 1.0, 900.0),
        ('CREMA CORPORAL RENOVA BODY', 'MPPISTALI01', 'FRAGANCIA PISTACHO', 0.2, 180.0),
        ('CREMA CORPORAL RENOVA BODY', 'MPYOCRLI01', 'FRAGANCIA YOGURT CREMOSO', 0.1, 90.0),
        ('CREMA DE UREA', 'MPACHISO01', 'ÁCIDO HIALURÓNICO 50 KD', 0.3, 21.0),
        ('CREMA DE UREA', 'MPACHISO03', 'ÁCIDO HIALURÓNICO 1500 KD', 0.3, 21.0),
        ('CREMA DE UREA', 'MPACSASO01', 'ÁCIDO SALICILICO', 0.1, 7.0),
        ('CREMA DE UREA', 'MPPROPLI01', 'PROPILENGLICOL', 5.0, 350.0),
        ('CREMA DE UREA', 'MPAGUALI01', 'AGUA DESIONIZADA', 61.7, 4319.0),
        ('CREMA DE UREA', 'MPUREASO01', 'ÚREA', 10.0, 700.0),
        ('CREMA DE UREA', 'MPALCESO01', 'ALCOHOL CETILICO', 4.0, 280.0),
        ('CREMA DE UREA', 'MPACJOLI01', 'ACEITE DE JOJOBA', 1.0, 70.0),
        ('CREMA DE UREA', 'MPSILILI01', 'SILICONA LIQUIDA', 2.0, 140.0),
        ('CREMA DE UREA', 'MPEZ4USO01', 'EZ-4U', 0.4, 28.0),
        ('CREMA DE UREA', 'MPSILISO01', 'SILIMARINA', 0.1, 7.0),
        ('CREMA DE UREA', 'MPACTRSO01', 'ÁCIDO TRANEXAMICO', 2.0, 140.0),
        ('CREMA DE UREA', 'MPNIACSO01', 'NIACINAMIDA', 2.0, 140.0),
        ('CREMA DE UREA', 'MPREGASO01', 'REGALIZ', 0.05, 3.5),
        ('CREMA DE UREA', 'MPEXGOSO01', 'CENTELLA', 0.05, 3.5),
        ('CREMA DE UREA', 'MPALVESO01', 'ALOE VERA', 0.3, 21.0),
        ('CREMA DE UREA', 'MPBESOSO01', 'BENZOATO DE SODIO', 0.3, 21.0),
        ('CREMA DE UREA', 'MPSOPOSO01', 'SORBATO DE POTASIO', 0.3, 21.0),
        ('CREMA DE UREA', 'MPFENOLI01', 'FENOXIETANOL', 0.5, 35.0),
        ('CREMA DE UREA', 'MPVITELI01', 'VITAMINA E - ACEITE', 1.0, 70.0),
        ('CREMA DE UREA', 'MPPANTLI01', 'PANTENOL - LIQUIDO', 2.0, 140.0),
        ('CREMA DE UREA', 'MPALANSO01', 'ALANTOINA', 0.5, 35.0),
        ('CREMA DE UREA', 'MPBETASO01', 'BETAINA', 1.0, 70.0),
        ('CREMA DE UREA', 'MPBISALI01', 'BISABOLOL', 0.1, 7.0),
        ('CREMA DE UREA', 'MPTWEELI02', 'TWEEN 80', 1.0, 70.0),
        ('CREMA DE UREA', 'MPTWEELI01', 'TWEEN 20', 4.0, 280.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPACHISO01', 'ÁCIDO HIALURÓNICO 50 KD', 0.2, 50.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPACHISO03', 'ÁCIDO HIALURÓNICO 1500 KD', 0.2, 50.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPPROPLI01', 'PROPILENGLICOL', 3.0, 750.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPGLICLI01', 'GLICERINA', 2.0, 500.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPQUCRELI01', 'QUIMCREAM', 2.0, 500.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPSILILI01', 'SILICONA LIQUIDA', 2.0, 500.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPTRICAL01', 'TRIGLICERIDO CAPRICO', 2.0, 500.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPNIACSO01', 'NIACINAMIDA', 2.0, 500.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPPANTLI01', 'PANTENOL LIQUIDO', 0.5, 125.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPVITAELI01', 'VITAMINA E LIQUIDA', 0.5, 125.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPALVESO01', 'ALOE VERA', 0.05, 12.5),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPALANSO01', 'ALANTOINA', 0.5, 125.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPMELASO01', 'MELATONINA', 0.03, 7.5),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPRESVSO01', 'RESVERATROL', 0.5, 125.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPGLUTSO01', 'GLUTATION', 0.03, 7.5),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPBETASO01', 'BETAINA', 0.5, 125.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPTEANSO01', 'L-TEANINA', 0.1, 25.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPBETASO02', 'BETAGLUCAN', 0.1, 25.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPFENOLI01', 'FENOXIETANOL', 1.0, 250.0),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPAGUALI01', 'AGUA DESIONIZADA', 82.779, 20694.75),
        ('EMULSION HIDRATANTE ANTIOXIDANTE', 'MPASTAXLI01', 'ASTAXANTINA', 0.001, 0.25),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPAGUALI01', 'AGUA DESIONIZADA', 75.1, 30040.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPPROPLI01', 'PROPILENGLICOL', 5.0, 2000.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPUREASO01', 'UREA', 5.0, 2000.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPNIACSO01', 'NIACINAMIDA', 5.0, 2000.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPALCESO01', 'ALCOHOL CETILICO', 3.0, 1200.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPCARNSO01', 'L-CARNITINA', 1.0, 400.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPFENOLI01', 'FENOXIETANOL', 1.0, 400.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPTRIESO01', 'TRIETANOLAMINA 85%', 1.0, 400.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPSILILI01', 'SILICONA LIQUIDA', 0.5, 200.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPVITAELI01', 'VITAMINA E LIQUIDA', 0.5, 200.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPALANSO01', 'ALANTOINA', 0.5, 200.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPEZ4USO01', 'EZ-4U', 0.4, 160.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPCARBSO01', 'CARBOPOL', 0.35, 140.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPACHISO03', 'ACIDO HIALURÓNICO 1500 KD', 0.3, 120.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPACSASO01', 'ACIDO SALICILICO', 0.3, 120.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPSOPOSO01', 'SORBATO DE POTASIO', 0.3, 120.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPBESOSO01', 'BENZOATO DE SODIO', 0.3, 120.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPACHISO01', 'ÁCIDO HIALURÓNICO 50 KD', 0.2, 80.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPSILISO01', 'SILIMARINA', 0.1, 40.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPACKOSO01', 'ACIDO KOJICO', 0.1, 40.0),
        ('EMULSION HIDRATANTE  B3+BHA', 'MPALVESO01', 'ALOE VERA', 0.05, 20.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPAGUALI01', 'AGUA DESIONIZADA', 72.4, 21720.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPUREASO01', 'UREA', 1.5, 450.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPESCULI01', 'ESCUALENO', 1.5, 450.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPSILILI01', 'SILICONA LIQUIDA', 1.5, 450.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPEZ4USO01', 'EZ-4U', 0.4, 120.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPACHISO01', 'ACIDO HIALURONICO 50 KD', 0.35, 105.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPPROPLI01', 'PROPILENGLICOL', 5.0, 1500.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPBETASO01', 'BETAGLUCAN', 0.1, 30.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPNIACSO01', 'NIACINAMIDA', 5.0, 1500.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPUPASO001', 'UNDECILENOIL FENILALANINA', 2.0, 600.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPGIWHSO01', 'GIGA WHITE', 0.1, 30.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPFENOLI01', 'FENOXIETANOL', 1.0, 300.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPVITAELI01', 'VITAMINA E ACEITE', 0.3, 90.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPPANTLI01', 'PANTENOL LIQUIDO', 0.1, 30.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPREGASO01', 'REGALIZ', 0.05, 15.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPALARSO01', 'ALFA ARBUTINA', 2.0, 600.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPTEANSO01', 'L-TEANINA', 0.1, 30.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPACHISO03', 'ACIDO HIALURONICO 1500 KD', 0.3, 90.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPCARBSO01', 'CARBOPOL', 0.3, 90.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPALCESO01', 'ALCOHOL CETILICO', 4.0, 1200.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MPGLUCSO01', 'N-ACETILGLUCOSAMINA', 2.0, 600.0),
        ('EMULSION LIMPIADORA', 'MPAGUALI01', 'AGUA DESIONIZADA', 78.5, 78500.0),
        ('EMULSION LIMPIADORA', 'MPGOXASO01', 'GOMA XANTAN', 0.4, 400.0),
        ('EMULSION LIMPIADORA', 'MPGLICLI01', 'GLICERINA', 4.0, 4000.0),
        ('EMULSION LIMPIADORA', 'MPCENTESO01', 'CENTELLA', 0.05, 50.0),
        ('EMULSION LIMPIADORA', 'MPBETASO02', 'BETAGLUCAN', 0.3, 300.0),
        ('EMULSION LIMPIADORA', 'MPALOESO01', 'ALOE VERA', 0.05, 50.0),
        ('EMULSION LIMPIADORA', 'MPACHISO03', 'ACIDO HIALURONICO 1500 KD', 1.0, 1000.0),
        ('EMULSION LIMPIADORA', 'MPALANSO01', 'ALANTOINA', 0.3, 300.0),
        ('EMULSION LIMPIADORA', 'MPPROBSO01', 'PROBETAINA', 2.5, 2500.0),
        ('EMULSION LIMPIADORA', 'MPLAGLLI01', 'LAURIL GLUCOSIDO', 3.0, 3000.0),
        ('EMULSION LIMPIADORA', 'MPAOSLI01', 'AOS 40', 1.5, 1500.0),
        ('EMULSION LIMPIADORA', 'MPTWEEL02', 'TWEEN 80', 2.3, 2300.0),
        ('EMULSION LIMPIADORA', 'MPBIOSSO01', 'BIOSURE FE', 0.8, 800.0),
        ('EMULSION LIMPIADORA', 'MPACCISO01', 'ACIDO CITRICO', 0.2, 200.0),
        ('EMULSION LIMPIADORA', 'MPSILILI02', 'SILICONA BM 600', 1.7, 1700.0),
        ('EMULSION LIMPIADORA', 'MPACJOLI01', 'ACEITE JOJOBA', 1.0, 1000.0),
        ('EMULSION LIMPIADORA', 'MPTRICA01', 'TRIGLICERIDO CAPRICO', 1.5, 1500.0),
        ('EMULSION LIMPIADORA', 'MPVITAELI01', 'VITAMINA E ACEITE', 0.5, 500.0),
        ('EMULSION LIMPIADORA', 'MPYOCRLI01', 'FRAGANCIA YOGURT CREMOSO', 0.3, 300.0),
        ('EMULSION LIMPIADORA', 'MPFRSALI01', 'FRAGANCIA FRESA CREMOSO', 0.1, 100.0),
        ('ESENCIA DE CENTELLA ASIATICA', 'MPAGUALI02', 'AGUA DESIONIZADA', 92.05, 46025.0),
        ('ESENCIA DE CENTELLA ASIATICA', 'MPACHISO01', 'ACIDO HILAURONICO 50 KD', 0.3, 150.0),
        ('ESENCIA DE CENTELLA ASIATICA', 'MPGLICLI01', 'GLICERINA', 3.0, 1500.0),
        ('ESENCIA DE CENTELLA ASIATICA', 'MPGLICLI01', 'GLICINA', 0.05, 25.0),
        ('ESENCIA DE CENTELLA ASIATICA', 'MPGLUCOSO02', 'GLUCONOLACTONA', 0.5, 250.0),
        ('ESENCIA DE CENTELLA ASIATICA', 'MPREGASO01', 'REGALIZ', 0.1, 50.0),
        ('ESENCIA DE CENTELLA ASIATICA', 'MPNIACSO01', 'NIACINAMIDA', 2.0, 1000.0),
        ('ESENCIA DE CENTELLA ASIATICA', 'MPBETASO01', 'BETAINA', 0.3, 150.0),
        ('ESENCIA DE CENTELLA ASIATICA', 'MPECTOSO01', 'ECTOINA', 0.3, 150.0),
        ('ESENCIA DE CENTELLA ASIATICA', 'MPFENOLI01', 'FENOXIETANOL', 1.0, 500.0),
        ('ESENCIA DE CENTELLA ASIATICA', 'MPASIASO01', 'ASIATICOSIDO', 0.1, 50.0),
        ('ESENCIA DE CENTELLA ASIATICA', 'MPTERPESO01', 'TERPENOS SOLUBLE', 0.1, 50.0),
        ('ESENCIA DE CENTELLA ASIATICA', 'MPBETASO03', 'BETAGLUCAN', 0.05, 25.0),
        ('ESENCIA DE CENTELLA ASIATICA', 'MPEXGOSO01', 'CENTELLA ASIATICA POLVO', 0.15, 75.0),
        ('ESENCIA ILUMINADORA', 'MPACSASO01', 'ÁCIDO SALICILICO', 0.05, 15.0),
        ('ESENCIA ILUMINADORA', 'MPGLUCSO02', 'GLUCONOLACTONA', 1.0, 300.0),
        ('ESENCIA ILUMINADORA', 'MPACHISO01', 'ÁCIDO HIALURÓNICO 50 KD', 0.3, 90.0),
        ('ESENCIA ILUMINADORA', 'MPACHISO02', 'ÁCIDO HIALURÓNICO 300 KD', 0.1, 30.0),
        ('ESENCIA ILUMINADORA', 'MPPROPLI01', 'PROPILENGLICOL', 5.0, 1500.0),
        ('ESENCIA ILUMINADORA', 'MPTEANSO01', 'L-TEANINA', 0.05, 15.0),
        ('ESENCIA ILUMINADORA', 'MPSOPOSO01', 'SORBATO DE POTASIO', 0.3, 90.0),
        ('ESENCIA ILUMINADORA', 'MPBESOSO01', 'BENZOATO DE SODIO', 0.3, 90.0),
        ('ESENCIA ILUMINADORA', 'MPACKOSO01', 'ÁCIDO KOJICO', 2.0, 600.0),
        ('ESENCIA ILUMINADORA', 'MPBISOSO01', 'BICARBONATO SODIO', 0.45, 135.0),
        ('ESENCIA ILUMINADORA', 'MPSILISO01', 'SILIMARINA', 0.3, 90.0),
        ('ESENCIA ILUMINADORA', 'MPACLALI02', 'ÁCIDO LÁCTICO', 1.0, 300.0),
        ('ESENCIA ILUMINADORA', 'MPAGUALI01', 'AGUA DESIONIZADA', 89.15, 26745.0),
        ('GEL HIDRATANTE', 'MPAGUALI01', 'AGUA DESIONIZADA', 76.48, 26768.0),
        ('GEL HIDRATANTE', 'MPPROPLI01', 'PROPILENGLICOL', 5.0, 1750.0),
        ('GEL HIDRATANTE', 'MPUREASO01', 'UREA', 3.0, 1050.0),
        ('GEL HIDRATANTE', 'MPGLICLI01', 'GLICERINA', 3.0, 1050.0),
        ('GEL HIDRATANTE', 'MPACTRSO01', 'ACIDO TRANEXAMICO', 3.0, 1050.0),
        ('GEL HIDRATANTE', 'MPALCESO01', 'ALCOHOL CETILICO', 2.25, 787.5),
        ('GEL HIDRATANTE', 'MPNIACSO01', 'NIACINAMIDA', 2.0, 700.0),
        ('GEL HIDRATANTE', 'MPSILILI01', 'SILICONA LIQUIDA', 1.25, 437.5),
        ('GEL HIDRATANTE', 'MPFENOLI01', 'FENOXIETANOL', 1.0, 350.0),
        ('GEL HIDRATANTE', 'MPBETASO01', 'BETAINA', 0.5, 175.0),
        ('GEL HIDRATANTE', 'MPALANSO01', 'ALANTOINA', 0.5, 175.0),
        ('GEL HIDRATANTE', 'MPEZ4USO01', 'EZ-4U', 0.4, 140.0),
        ('GEL HIDRATANTE', 'MPPANTLI01', 'PANTENOL LIQUIDO', 0.3, 105.0),
        ('GEL HIDRATANTE', 'MPSOPOSO01', 'SORBATO DE POTASIO', 0.3, 105.0),
        ('GEL HIDRATANTE', 'MPBESOSO01', 'BENZOATO DE SODIO', 0.3, 105.0),
        ('GEL HIDRATANTE', 'MPACHISO01', 'ACIDO HIALURÓNICO 50 KD', 0.2, 70.0),
        ('GEL HIDRATANTE', 'MPACHISO02', 'ACIDO HIALURÓNICO 300 KD', 0.2, 70.0),
        ('GEL HIDRATANTE', 'MPACHISO03', 'ACIDO HIALURÓNICO 1500 KD', 0.2, 70.0),
        ('GEL HIDRATANTE', 'MPALVESO01', 'ALOE VERA', 0.05, 17.5),
        ('GEL HIDRATANTE', 'MPEXGOSO01', 'CENTELLA ASIATICA POLVO', 0.03, 10.5),
        ('GEL HIDRATANTE', 'MPREGASO01', 'REGALIZ', 0.03, 10.5),
        ('GEL HIDRATANTE', 'MPACSASO01', 'ACIDO SALICILICO', 0.01, 3.5000000000000004),
        ('LIMPIADOR FACIAL BHA 2%', 'MPAGUALI01', 'AGUA DESIONIZADA', 63.0, 126000.0),
        ('LIMPIADOR FACIAL BHA 2%', 'MPPROPLI01', 'PROPILENGLICOL', 10.0, 20000.0),
        ('LIMPIADOR FACIAL BHA 2%', 'MPGLICLI01', 'GLICERINA', 10.0, 20000.0),
        ('LIMPIADOR FACIAL BHA 2%', 'MPPEGLI01',  'POLIETILENGLICOL 400', 5.0, 10000.0),
        ('LIMPIADOR FACIAL BHA 2%', 'MPALCESO01', 'AOS 40', 4.0, 8000.0),
        ('LIMPIADOR FACIAL BHA 2%', 'MPCARNSO01', 'ÁCIDO SALICILICO', 2.0, 4000.0),
        ('LIMPIADOR FACIAL BHA 2%', 'MPFENOLI01', 'PROBETAINA', 2.0, 4000.0),
        ('LIMPIADOR FACIAL BHA 2%', 'MPTRIESO01', 'TRIETANOLAMINA 85%', 1.9, 3800.0),
        ('LIMPIADOR FACIAL BHA 2%', 'MPSILILI01', 'GOMA XANTAN', 1.0, 2000.0),
        ('LIMPIADOR FACIAL BHA 2%', 'MPVITAELI01', 'FENOXIETANOL', 1.0, 2000.0),
        ('LIMPIADOR FACIAL BHA 2%', 'MPALANSO01', 'ACEITE ARBOL DE TE', 0.05, 100.0),
        ('LIMPIADOR FACIAL BHA 2%', 'MPEZ4USO01', 'CENTELLA ASIATICA POLVO', 0.05, 100.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPAGUALI02', 'AGUA DESIONIZADA', 66.56, 46592.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPPROPLI01', 'PROPILENGLICOL', 10.0, 7000.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPGLICLI01', 'GLICERINA', 10.0, 7000.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPPROBLI01', 'PROBETAINA', 3.5, 2450.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPASCOLI01', 'AOS 40', 3.5, 2450.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPTWEELI01', 'TWEEN 20', 2.0, 1400.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPFENOLI01', 'FENOXIETANOL', 1.0, 700.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPACLALI01', 'ÁCIDO LACTICO', 1.0, 700.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPGOXASO01', 'GOMA XANTAN', 0.5, 350.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPCARBSO01', 'CARBOPOL', 0.5, 350.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPBETASO01', 'BETAINA', 0.5, 350.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPACHISO01', 'ÁCIDO HIALURÓNICO 50 KD', 0.2, 140.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPACHISO02', 'ÁCIDO HIALURÓNICO 300 KD', 0.2, 140.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPACHISO03', 'ÁCIDO HIALURÓNICO 1500 KD', 0.2, 140.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPACGLSO01', 'ACIDO GLUTAMICO', 0.1, 70.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPBETASO02', 'BETAGLUCAN', 0.1, 70.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPGLICSO01', 'GLICINA', 0.1, 70.0),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPEXGOSO01', 'CENTELLA ASIATICA POLVO', 0.01, 7.000000000000001),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPALVESO01', 'ALOE VERA', 0.01, 7.000000000000001),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPREGASO01', 'REGALIZ', 0.01, 7.000000000000001),
        ('LIMPIADOR FACIAL HIDRATANTE', 'MPPECOSO01', 'PEPTIDOS DE COLAGENO', 0.01, 7.000000000000001),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPAGUALI01', 'AGUA DESIONIZADA', 71.15, 142300.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPGLICLI01', 'GLICERINA', 10.0, 20000.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPPROPLI02', 'PROPILENGLICOL', 5.0, 10000.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPASCOLI01', 'AOS 40', 4.0, 8000.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPPROBLI01', 'PROBETAINA', 3.0, 6000.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPTWEEL01', 'TWEEN 20', 2.0, 4000.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPACKOSO01', 'ÁCIDO KOJICO', 1.0, 2000.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPGOXASO01', 'GOMA XANTAN', 1.0, 2000.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPCARBSO01', 'CARBOPOL', 0.5, 1000.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPACSASO01', 'ACIDO SALICILICO', 0.5, 1000.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPTWEEL02', 'TWEEN 80', 0.5, 1000.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPACLALI02', 'ACIDO LACTICO', 0.3, 600.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPSOPOSO01', 'SORBATO DE POTASIO', 0.3, 600.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPBESOSO01', 'BENZOATO DE SODIO', 0.3, 600.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPBETASO02', 'BETAGLUCAN', 0.3, 600.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPACHISO03', 'ÁCIDO HIALURÓNICO 1500 KD', 0.1, 200.0),
        ('LIMPIADOR ILUMINADOR ACIDO KOJICO', 'MPREGASO01', 'REGALIZ', 0.05, 100.0),
        ('MASCARILLA HIDRATANTE', 'MPAGUALI01', 'AGUA DESIONIZADA', 74.77, 7476.999999999999),
        ('MASCARILLA HIDRATANTE', 'MPGLICLI01', 'GLICERINA', 7.5, 750.0),
        ('MASCARILLA HIDRATANTE', 'MPALCESO01', 'ALCOHOL CETILICO', 5.0, 500.0),
        ('MASCARILLA HIDRATANTE', 'MPACTRSO01', 'ACIDO TRANEXAMICO', 5.0, 500.0),
        ('MASCARILLA HIDRATANTE', 'MPNIACSO01', 'NIACINAMIDA', 2.0, 200.0),
        ('MASCARILLA HIDRATANTE', 'MPACHISO01', 'ACIDO HIALURÓNICO 50 KD', 1.0, 100.0),
        ('MASCARILLA HIDRATANTE', 'MPESCULI01', 'ESCUALENO', 1.0, 100.0),
        ('MASCARILLA HIDRATANTE', 'MPSILILI01', 'SILICONA LIQUIDA', 1.0, 100.0),
        ('MASCARILLA HIDRATANTE', 'MPFENOLI01', 'FENOXIETANOL', 1.0, 100.0),
        ('MASCARILLA HIDRATANTE', 'MPALANSO01', 'ALANTOINA', 0.5, 50.0),
        ('MASCARILLA HIDRATANTE', 'MPEZ4USO01', 'EZ-4U', 0.4, 40.0),
        ('MASCARILLA HIDRATANTE', 'MPACHISO03', 'ACIDO HIALURÓNICO 1500 KD', 0.5, 50.0),
        ('MASCARILLA HIDRATANTE', 'MPVITAELI01', 'VITAMINA E LIQUIDA', 0.15, 15.0),
        ('MASCARILLA HIDRATANTE', 'MPACROLI01', 'ACEITE DE ROSA MOSQUETA', 0.1, 10.0),
        ('MASCARILLA HIDRATANTE', 'MPPANTLI01', 'PANTENOL LIQUIDO', 0.05, 5.0),
        ('MASCARILLA HIDRATANTE', 'MPPECOSO01', 'PEPTIDOS DE COLAGENO POLVO', 0.02, 2.0),
        ('MASCARILLA HIDRATANTE', 'MPALVESO01', 'ALOE VERA', 0.01, 1.0),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPAGUALI01', 'AGUA DESIONIZADA', 79.87, 9584.4),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPNIACSO01', 'NIACINAMIDA', 5.0, 600.0),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPACIETASO01', '3-O ACIDO ETIL ASCORBICO', 4.0, 480.0),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPFOASSO01', 'FOSFATO DE ASCORBILO SODICO', 3.5, 420.0),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPTEISASO01', 'ASCORBATO DE TETRAHEXILDECILO', 2.0, 240.0),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPQUCRELI01', 'QUINCREAM', 1.2, 144.0),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPBIOFELI01', 'BIOSURE FE', 1.0, 120.0),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPASGLSO01', 'ASCORBYL GLUCOSIDE', 0.5, 60.0),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPGLICSO02', 'GLICINAMIDA', 0.3, 36.0),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPVITESO01', 'VITAMINA E POLVO', 0.3, 36.0),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPACHISO01', 'ACIDO HIALURONICO 50 KD', 0.2, 24.000000000000004),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPESCULI01', 'ESCUALENO', 0.05, 6.000000000000001),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPPANTSO01', 'PANTENOL POLVO', 0.05, 6.000000000000001),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPEXGOSO01', 'CENTELLA ASIATICA POLVO', 0.05, 6.000000000000001),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPBAKULI01', 'BAKUCHIOL', 0.03, 3.6),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPACHESO01', 'ACETYL HEXAPEPTIDE-8', 0.01, 1.2),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPPROPLI01', 'PROPILENGLICOL', 0.5, 60.0),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPGLICLI01', 'GLICERINA', 0.5, 60.0),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPTRICAL01', 'TRIGLICERIDO CAPRICO', 0.6, 72.0),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPGRANLI01', 'GRANSIL VX419', 0.3, 36.0),
        ('SUERO ANTIOXIDANTE RENOVA C10', 'MPTINOSO01', 'TINOGARD TT', 0.04, 4.8),
        ('SUERO ANTIOXIDANTE VITAMINA C+B3', 'MPACHISO01', 'ÁCIDO HIALURÓNICO 50 KD', 0.5, 150.0),
        ('SUERO ANTIOXIDANTE VITAMINA C+B3', 'MPPROPLI01', 'PROPILENGLICOL', 3.0, 900.0),
        ('SUERO ANTIOXIDANTE VITAMINA C+B3', 'MPAGUALI01', 'AGUA DESIONIZADA', 83.4, 25020.0),
        ('SUERO ANTIOXIDANTE VITAMINA C+B3', 'MPGLICLI01', 'GLICERINA', 1.0, 300.0),
        ('SUERO ANTIOXIDANTE VITAMINA C+B3', 'MPGLUCSO01', 'GLUCOSAMINA NAG', 1.0, 300.0),
        ('SUERO ANTIOXIDANTE VITAMINA C+B3', 'MPASGLSO01', 'ASCORBIC GLUCOSIDE', 2.0, 600.0),
        ('SUERO ANTIOXIDANTE VITAMINA C+B3', 'MPBISOSO01', 'BICARBONATO DE SODIO', 0.3, 90.0),
        ('SUERO ANTIOXIDANTE VITAMINA C+B3', 'MPSILILI01', 'SILICONA LIQUIDA', 0.35, 105.0),
        ('SUERO ANTIOXIDANTE VITAMINA C+B3', 'MPEZ4USO01', 'EZ-4U', 0.2, 60.0),
        ('SUERO ANTIOXIDANTE VITAMINA C+B3', 'MPNIACSO01', 'NIACINAMIDA', 5.0, 1500.0),
        ('SUERO ANTIOXIDANTE VITAMINA C+B3', 'MPVITESO01', 'VITAMINA E POLVO', 0.1, 30.0),
        ('SUERO ANTIOXIDANTE VITAMINA C+B3', 'MPPECOSO01', 'PEPTIDOS DE COLAGENO', 0.1, 30.0),
        ('SUERO ANTIOXIDANTE VITAMINA C+B3', 'MPALARSO01', 'ALFA ARBUTINA', 2.0, 600.0),
        ('SUERO ANTIOXIDANTE VITAMINA C+B3', 'MPGLICSO01', 'GLICINA', 0.05, 15.0),
        ('SUERO ANTIOXIDANTE VITAMINA C+B3', 'MPFENOLI01', 'FENOXIETANOL', 1.0, 300.0),
        ('SUERO AZ + B3', 'MPAGUAL01', 'AGUA DESIONIZADA', 40.42, 6063.0),
        ('SUERO AZ + B3', 'MPPROPLI01', 'PROPILENGLICOL', 40.0, 6000.0),
        ('SUERO AZ + B3', 'MPACAZSO01', 'ÁCIDO AZELAICO', 10.0, 1500.0),
        ('SUERO AZ + B3', 'MPNIACSO01', 'NIACINAMIDA', 5.0, 750.0),
        ('SUERO AZ + B3', 'MPBISOSO01', 'BICARBONATO SODIO', 3.0, 450.0),
        ('SUERO AZ + B3', 'MPCHITSO01', 'CHITOSAN', 0.4, 60.0),
        ('SUERO AZ + B3', 'MPACHISO01', 'ÁCIDO HIALURÓNICO 50 KD', 0.3, 45.0),
        ('SUERO AZ + B3', 'MPESOPOS01', 'SORBATO DE POTASIO', 0.3, 45.0),
        ('SUERO AZ + B3', 'MPBESOSO01', 'BENZOATO DE SODIO', 0.3, 45.0),
        ('SUERO AZ + B3', 'MPACHISO03', 'ÁCIDO HIALURÓNICO 1500 KD', 0.2, 30.0),
        ('SUERO AZ + B3', 'MPTEANSO01', 'L-TEANINA', 0.05, 7.5),
        ('SUERO AZ + B3', 'MPEXGOSO01', 'CENTELLA ASIATICA POLVO', 0.03, 4.5),
        ('Suero Exfoliante BHA 2%', 'MPAGUALI01', 'AGUA DESIONIZADA', 62.75, 37650.0),
        ('Suero Exfoliante BHA 2%', 'MPPROPLI01', 'PROPILENGLICOL', 20.0, 12000.0),
        ('Suero Exfoliante BHA 2%', 'MPGLICLI01', 'GLICERINA', 5.0, 3000.0),
        ('Suero Exfoliante BHA 2%', 'MPACTRSO01', 'ÁCIDO TRANEXAMICO', 5.0, 3000.0),
        ('Suero Exfoliante BHA 2%', 'MPACSASO01', 'ÁCIDO SALICILICO', 2.0, 1200.0),
        ('Suero Exfoliante BHA 2%', 'MPALARSO01', 'ALFA ARBUTINA  (LYPHAR)', 2.0, 1200.0),
        ('Suero Exfoliante BHA 2%', 'MPACAZSO01', 'ÁCIDO AZELAICO', 1.0, 600.0),
        ('Suero Exfoliante BHA 2%', 'MPMETISO01', 'METILSULFONILMETANO', 1.0, 600.0),
        ('Suero Exfoliante BHA 2%', 'MPCARBSO01', 'CARBOPOL', 0.3, 180.0),
        ('Suero Exfoliante BHA 2%', 'MPSOPOSO01', 'SORBATO DE POTASIO', 0.3, 180.0),
        ('Suero Exfoliante BHA 2%', 'MPBESOSO01', 'BENZOATO DE SODIO', 0.3, 180.0),
        ('Suero Exfoliante BHA 2%', 'MPGOXASO01', 'GOMA XANTAN', 0.2, 120.0),
        ('Suero Exfoliante BHA 2%', 'MPSILISO01', 'SILIMARINA', 0.15, 90.0),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPAGUALI01', 'AGUA DESIONIZADA', 77.79, 10890.6),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPGLUCSO02', 'GLUCONOLACTONA', 8.0, 1120.0),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPACLALI02', 'ACIDO LACTICO', 4.0, 560.0),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPHIDSOLI01', 'HIDROXIDO DE SODIO (SOLUCION 50%)', 3.0, 420.0),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPALARSO01', 'ALFA  ARBUTINA', 2.0, 280.0),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPGLUCSO01', 'N-ACETIL GLUCOSAMINA', 1.0, 140.0),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPPROPLI01', 'PROPILENGLICOL', 1.0, 140.0),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPFENOLI01', 'FENOXIETANOL', 1.0, 140.0),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPACSASO01', 'ACIDO SALICILICO', 0.5, 70.0),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPUREASO01', 'UREA', 0.5, 70.0),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPACAZSO01', 'ACIDO AZELAICO', 0.2, 28.000000000000004),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPACKOSO01', 'ACIDO KOJICO', 0.2, 28.000000000000004),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPACHISO01', 'ACIDO HIALURONICO 50 KD', 0.2, 28.000000000000004),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPCICLOS01', 'BETA-CICLODEXTRINA', 0.2, 28.000000000000004),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPEXGOSO01', 'CENTELLA ASIATICA POLVO', 0.05, 7.000000000000001),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPREGASO01', 'REGALIZ', 0.01, 1.4000000000000001),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPGRANLI01', 'GRANSIL VX 419', 0.3, 42.0),
        ('SUERO EXFOLIANTE NOVA PHA', 'MPEDDISO01', 'EDTA DISODICO', 0.05, 7.000000000000001),
        ('SUERO HIDRATANTE AH 1.5%', 'MPAGUAL01', 'AGUA DESIONIZADA', 95.21, 85689.0),
        ('SUERO HIDRATANTE AH 1.5%', 'MPGLICLI01', 'GLICERINA', 1.0, 900.0),
        ('SUERO HIDRATANTE AH 1.5%', 'MPFENOLI01', 'FENOXIETANOL', 1.0, 900.0),
        ('SUERO HIDRATANTE AH 1.5%', 'MPACHISO01', 'ACIDO HIALURONICO 50 KD (LYPHAR)', 0.8, 720.0),
        ('SUERO HIDRATANTE AH 1.5%', 'MPACHISO02', 'ACIDO HIALURONICO 300 KD (LYPHAR)', 0.4, 360.0),
        ('SUERO HIDRATANTE AH 1.5%', 'MPBETASO01', 'BETAINA', 0.35, 314.99999999999994),
        ('SUERO HIDRATANTE AH 1.5%', 'MPACHISO03', 'ACIDO HIALURONICO 1500 KD (LYPHAR)', 0.3, 270.0),
        ('SUERO HIDRATANTE AH 1.5%', 'MPALANSO01', 'ALANTOINA', 0.3, 270.0),
        ('SUERO HIDRATANTE AH 1.5%', 'MPGLUCSO01', 'GLUCONOLACTONA', 0.3, 270.0),
        ('SUERO HIDRATANTE AH 1.5%', 'MPVITESO01', 'VITAMINA E POLVO', 0.2, 180.0),
        ('SUERO HIDRATANTE AH 1.5%', 'MPPANTSO01', 'PANTENOL POLVO', 0.1, 90.0),
        ('SUERO HIDRATANTE AH 1.5%', 'MPBETASO02', 'BETAGLUCAM', 0.03, 26.999999999999996),
        ('SUERO HIDRATANTE AH 1.5%', 'MPALVESO01', 'ALOE VERA', 0.01, 9.000000000000002),
        ('SUERO ILUMINADOR AHA+AH.', 'MPAGUALI02', 'AGUA DESIONIZADA', 78.3, 0.0),
        ('SUERO ILUMINADOR AHA+AH.', 'MPACHISO01', 'ÁCIDO HIALURONICO 50 KD', 0.3, 0.0),
        ('SUERO ILUMINADOR AHA+AH.', 'MPACSASO01', 'ÁCIDO SALICILICO', 1.0, 0.0),
        ('SUERO ILUMINADOR AHA+AH.', 'MPACLALI02', 'ÁCIDO LACTICO', 4.0, 0.0),
        ('SUERO ILUMINADOR AHA+AH.', 'MPUREASO01', 'UREA', 1.0, 0.0),
        ('SUERO ILUMINADOR AHA+AH.', 'MPACKOSO01', 'ÁCIDO KOJICO', 0.2, 0.0),
        ('SUERO ILUMINADOR AHA+AH.', 'MPALARSO01', 'ALFA ARBUTINA', 2.0, 0.0),
        ('SUERO ILUMINADOR AHA+AH.', 'MPFENOLI01', 'FENOXIETANOL', 1.0, 0.0),
        ('SUERO ILUMINADOR AHA+AH.', 'MPGLUCSO02', 'GLUCONOLACTONA', 8.0, 0.0),
        ('SUERO ILUMINADOR AHA+AH.', 'MPGLICLI01', 'GLICERINA', 1.0, 0.0),
        ('SUERO ILUMINADOR AHA+AH.', 'MPGLUCSO01', 'GLUCOSAMINA NAG', 1.0, 0.0),
        ('SUERO ILUMINADOR AHA+AH.', 'MPACAZSO01', 'ÁCIDO AZELAICO', 0.2, 0.0),
        ('SUERO ILUMINADOR AHA+AH.', 'MPPROPLI01', 'PROPILENGLICOL', 2.0, 0.0),
        ('SUERO ILUMINADOR AHA+AH.', 'MPEREGASO01', 'REGALIZ', 0.01, 0.0),
        ('SUERO ILUMINADOR AHA+AH.', 'MPTERSOL01', 'TERPENOS SOLUBLES', 0.01, 0.0),
        ('SUERO ILUMINADOR AHA+AH.', 'MPHIDROLI01', 'HIDROXIDO SODIO', 1.5, 0.0),
        ('SUERO ILUMINADOR TRX', 'MPAGUALI01', 'AGUA DESIONIZADA', 79.37, 71433.0),
        ('SUERO ILUMINADOR TRX', 'MPROPLI01', 'PROPILENGLICOL', 1.5, 1350.0),
        ('SUERO ILUMINADOR TRX', 'MPNIACSO01', 'NIACINAMIDA', 5.0, 4500.0),
        ('SUERO ILUMINADOR TRX', 'MPACTRSO01', 'ÁCIDO TRANEXAMICO', 5.0, 4500.0),
        ('SUERO ILUMINADOR TRX', 'MPALARSO01', 'ALFA ARBUTINA', 2.0, 1800.0),
        ('SUERO ILUMINADOR TRX', 'MPHEXDILI01', '1,2 HEXANEDIOL', 0.5, 450.0),
        ('SUERO ILUMINADOR TRX', 'MPGLUCSO02', 'GLUCONOLACTONA', 1.0, 900.0),
        ('SUERO ILUMINADOR TRX', 'MPUREASO01', 'UREA', 0.5, 450.0),
        ('SUERO ILUMINADOR TRX', 'MPGLICSO02', 'GLICINAMIDA', 0.5, 450.0),
        ('SUERO ILUMINADOR TRX', 'MPEDDISO01', 'EDTA DISODICO', 0.05, 45.0),
        ('SUERO ILUMINADOR TRX', 'MPALANSO01', 'ALANTOÍNA', 0.5, 450.0),
        ('SUERO ILUMINADOR TRX', 'MPACHISO01', 'ACIDO HIALURONICO 50 KD', 0.05, 45.0),
        ('SUERO ILUMINADOR TRX', 'MPACHISO02', 'ACIDO HIALURONICO 300 KD', 0.05, 45.0),
        ('SUERO ILUMINADOR TRX', 'MPACHISO03', 'ACIDO HIALURONICO 1500 KD', 0.1, 90.0),
        ('SUERO ILUMINADOR TRX', 'MPBIOFELI01', 'BIOSURE FE', 1.0, 900.0),
        ('SUERO ILUMINADOR TRX', 'MPACSASO01', 'GRANSIL VX419', 0.25, 225.0),
        ('SUERO ILUMINADOR TRX', 'MPACSASO01', 'ACIDO SALICILICO', 0.1, 90.0),
        ('SUERO ILUMINADOR TRX', 'MPGLUTSO01', 'GLUTATIÓN', 0.05, 45.0),
        ('SUERO ILUMINADOR TRX', 'MPMELASO01', 'MELATONINA', 0.1, 90.0),
        ('SUERO ILUMINADOR TRX', 'MPACKOSO01', 'ACIDO KOJICO', 0.1, 90.0),
        ('SUERO ILUMINADOR TRX', 'MPREGASO01', 'REGALIZ', 0.05, 45.0),
        ('SUERO ILUMINADOR TRX', 'MPGLUCSO01', 'N-ACETILGLUCOSAMINA', 2.0, 1800.0),
        ('SUERO ILUMINADOR TRX', 'MPEXGOSO01', 'CENTELLA ASIATICA POLVO', 0.03, 26.999999999999996),
        ('SUERO ILUMINADOR TRX', 'MPOLIPESO01', 'OLIGOPEPTIDO 68', 0.001, 0.9),
        ('SUERO ILUMINADOR TRX', 'MPCICLOS01', 'BETA-CICLODEXTRINA', 0.15, 135.0),
        ('SUERO ILUMINADOR TRX', 'MPFISOSO01', 'FITATO DE SODIO', 0.05, 45.0),
        ('SUERO ILUMINADOR TRX', 'MPAGUALI01', 'AGUA DESIONIZADA', 72.62, 21786.0),
        ('SUERO ILUMINADOR TRX', 'MPROPLI01', 'PROPILENGLICOL', 7.0, 2100.0),
        ('SUERO ILUMINADOR TRX', 'MPNIACSO01', 'NIACINAMIDA', 5.0, 1500.0),
        ('SUERO ILUMINADOR TRX', 'MPACTRSO01', 'ÁCIDO TRANEXAMICO', 5.0, 1500.0),
        ('SUERO ILUMINADOR TRX', 'MPALARSO01', 'ALFA ARBUTINA', 2.0, 600.0),
        ('SUERO ILUMINADOR TRX', 'MPGLUCOSO01', 'N-ACETIL GLUCOSAMINA', 2.0, 600.0),
        ('SUERO ILUMINADOR TRX', 'MPGLUCSO02', 'GLUCONOLACTONA', 1.5, 450.0),
        ('SUERO ILUMINADOR TRX', 'MPUREASO01', 'UREA', 1.0, 300.0),
        ('SUERO ILUMINADOR TRX', 'MPFENOLI01', 'FENOXIETANOL', 1.0, 300.0),
        ('SUERO ILUMINADOR TRX', 'MPACCISO01', 'ACIDO CITRICO', 0.73, 219.0),
        ('SUERO ILUMINADOR TRX', 'MPALANSO01', 'ALANTOÍNA', 0.5, 150.0),
        ('SUERO ILUMINADOR TRX', 'MPACHISO01', 'ACIDO HIALURONICO 50 KD', 0.4, 120.0),
        ('SUERO ILUMINADOR TRX', 'MPSOPOS01', 'SORBATO DE POTASIO', 0.3, 90.0),
        ('SUERO ILUMINADOR TRX', 'MPBESOSO01', 'BENZOATO DE SODIO', 0.3, 90.0),
        ('SUERO ILUMINADOR TRX', 'MPACSASO01', 'ACIDO SALICILICO', 0.15, 45.0),
        ('SUERO ILUMINADOR TRX', 'MPGLUTSO01', 'GLUTATIÓN', 0.15, 45.0),
        ('SUERO ILUMINADOR TRX', 'MPALVESO01', 'ALOE VERA', 0.1, 30.0),
        ('SUERO ILUMINADOR TRX', 'MPMELASO01', 'MELATONINA', 0.1, 30.0),
        ('SUERO ILUMINADOR TRX', 'MPACKOSO01', 'ACIDO KOJICO', 0.1, 30.0),
        ('SUERO ILUMINADOR TRX', 'MPREGASO01', 'REGALIZ', 0.05, 15.0),
        ('SUERO MULTIPEPTIDOS', 'MPAGUALI01', 'AGUA DESIONIZADA', 88.794, 31077.9),
        ('SUERO MULTIPEPTIDOS', 'MPNIACSO01', 'NIACINAMIDA', 5.0, 1750.0),
        ('SUERO MULTIPEPTIDOS', 'MPPROPLI01', 'PROPILENGLICOL', 2.5, 875.0),
        ('SUERO MULTIPEPTIDOS', 'MPGLUCSO01', 'GLUCOSAMINA (NAG)', 1.0, 350.0),
        ('SUERO MULTIPEPTIDOS', 'MPBIOFELI01', 'BIOSURE FE', 1.0, 350.0),
        ('SUERO MULTIPEPTIDOS', 'MPGLUCSO02', 'GLUCONOLACTONA', 0.5, 175.0),
        ('SUERO MULTIPEPTIDOS', 'MPCOTRSO01', 'COPPER TRIPEPTIDE 1', 0.1, 35.0),
        ('SUERO MULTIPEPTIDOS', 'MPPALTRISO02', 'PALMITOYL TRIPEPTIDE 1', 0.01, 3.5000000000000004),
        ('SUERO MULTIPEPTIDOS', 'MPPALTESO01', 'PALMITOYL TETRAPEPTIDE 7', 0.01, 3.5000000000000004),
        ('SUERO MULTIPEPTIDOS', 'MPPAPESO01', 'PALMITOYL PENTAPEPTIDE 4', 0.005, 1.7500000000000002),
        ('SUERO MULTIPEPTIDOS', 'MPACHESO01', 'ACETYL HEXAPEPTIDE 8', 0.03, 10.5),
        ('SUERO MULTIPEPTIDOS', 'MPACTESO01', 'ACETYL TETRAPEPTIDE 5', 0.001, 0.35000000000000003),
        ('SUERO MULTIPEPTIDOS', 'MPDIBEDISO01', 'DIPÉPTIDO DIAMINOBUTIROIL BENZALAMIDA DIACETATO', 0.01, 3.5000000000000004),
        ('SUERO MULTIPEPTIDOS', 'MPPOBOSO01', 'PDRN (SODIUM DNA)', 0.01, 3.5000000000000004),
        ('SUERO MULTIPEPTIDOS', 'MPADENSO01', 'ADENOSINA', 0.01, 3.5000000000000004),
        ('SUERO MULTIPEPTIDOS', 'MPGLICSO01', 'GLICINA', 0.05, 17.5),
        ('SUERO MULTIPEPTIDOS', 'MPGLUTSO01', 'GLUTATION', 0.01, 3.5000000000000004),
        ('SUERO MULTIPEPTIDOS', 'MPPALTRISO01', 'PALMITOYL TRIPEPTIDE 5', 0.01, 3.5000000000000004),
        ('SUERO MULTIPEPTIDOS', 'MPACHISO01', 'ACIDO HIALURONICO 50KD', 0.2, 70.0),
        ('SUERO MULTIPEPTIDOS', 'MPACHISO03', 'ACIDO HIALURONICO 1500KD', 0.1, 35.0),
        ('SUERO MULTIPEPTIDOS', 'MPACHISO02', 'ACIDO HIALURONICO 300KD', 0.2, 70.0),
        ('SUERO MULTIPEPTIDOS', 'MPPECOSO01', 'PEPTIDOS DE COLAGENO POLVO', 0.05, 17.5),
        ('SUERO MULTIPEPTIDOS', 'MPEDDISO01', 'EDTA DISODICO', 0.05, 17.5),
        ('SUERO MULTIPEPTIDOS', 'MPGRANLI01', 'GRANSIL VX 419', 0.25, 87.5),
        ('SUERO MULTIPEPTIDOS', 'MPTRIELO01', 'TRIETANOLAMINA 85%', 0.1, 35.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPAGUALI01', 'AGUA DESIONIZADA', 91.43, 109716.00000000001),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPNIACSO01', 'NIACINAMIDA', 5.0, 6000.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPBIOFELI01', 'BIOSURE FE', 1.0, 1200.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPGLUCSO01', 'N-ACETIL GLUCOSAMINA', 0.5, 600.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPGLUCSO02', 'GLUCONOLACTONA', 0.3, 360.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPACHISO03', 'ÁCIDO HIALURÓNICO 50 KD', 0.35, 420.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPACHISO01', 'ÁCIDO HIALURÓNICO 1500 KD', 0.05, 60.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPACHISO02', 'ÁCIDO HIALURÓNICO 300 KD', 0.05, 60.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPBETASO02', 'BETAINA', 0.05, 60.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPECTOSO01', 'ECTOINA', 0.1, 120.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPPANTSO01', 'PANTENOL POLVO', 0.05, 60.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPVITESO01', 'VITAMINA E POLVO', 0.15, 180.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPTERSSO01', 'TERPENOS SOLUBLES 98%', 0.01, 12.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPASIASO01', 'ASIATICOSIDO', 0.01, 12.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPHEXDILI01', '1,2 HEXANEDIOL', 0.5, 600.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPGRANLI01', 'GRANSIL VX419', 0.3, 360.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPEDDISO01', 'EDTA DISODICO', 0.05, 60.0),
        ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA', 'MPGLICLI01', 'GLICERINA', 0.1, 120.0),
        ('Suero RETINAL +', 'MPAGUALI01', 'AGUA DESIONIZADA', 78.13, 46878.0),
        ('Suero RETINAL +', 'MPPROPLI01', 'PROPILENGLICOL', 5.0, 3000.0),
        ('Suero RETINAL +', 'MPNIACSO01', 'NIACINAMIDA', 5.0, 3000.0),
        ('Suero RETINAL +', 'MPACTRSO01', 'ACIDO TRANEXAMICO', 5.0, 3000.0),
        ('Suero RETINAL +', 'MPALCESO01', 'ALCOHOL CETITLICO', 2.0, 1200.0),
        ('Suero RETINAL +', 'MPUREASO01', 'UREA', 1.0, 600.0),
        ('Suero RETINAL +', 'MPRESVSO01', 'RESVERATROL', 1.0, 600.0),
        ('Suero RETINAL +', 'MPACHISO01', 'ACIDO HIALURONICO 50 KD', 0.5, 300.0),
        ('Suero RETINAL +', 'MPVITAELI01', 'VITAMINA E LIQUIDA', 0.5, 300.0),
        ('Suero RETINAL +', 'MPALANSO01', 'ALANTOINA', 0.5, 300.0),
        ('Suero RETINAL +', 'MPEZ4USO01', 'EZ-4U', 0.4, 240.0),
        ('Suero RETINAL +', 'MPSOPOSO01', 'SORBATO DE POTASIO', 0.3, 180.0),
        ('Suero RETINAL +', 'MPBESOSO01', 'BENZOATO DE SODIO', 0.3, 180.0),
        ('Suero RETINAL +', 'MPBAKULI01', 'BACKUCHIOL', 0.3, 180.0),
        ('Suero RETINAL +', 'MPRETISO01', 'RETINALDEHIDO', 0.05, 30.0),
        ('Suero RETINAL +', 'MPPALTRISO02', 'PALMITOYL TRIPEPTIDE-1', 0.01, 6.0),
        ('Suero RETINAL +', 'MPPALTESO01', 'PALMITOYL TETRAPEPTIDE-7', 0.01, 6.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPAGUALI01', 'AGUA DESIONIZADA', 76.77, 7677.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPPROPLI01', 'PROPILENGLICOL', 5.0, 500.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPNIACSO01', 'NIACINAMIDA', 5.0, 500.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPACTRSO01', 'ÁCIDO TRANEXAMICO', 5.0, 500.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPUREASO01', 'UREA', 3.0, 300.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPALCESO01', 'ALCOHOL CETILICO', 1.0, 100.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPFENOLI01', 'FENOXIETANOL', 1.0, 100.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPACHSO01', 'ÁCIDO HIALURÓNICO 50 KD', 0.6, 60.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPVITAELI01', 'VITAMINA E LIQUIDA', 0.5, 50.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPALANSO01', 'ALANTOINA', 0.5, 50.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPEZ4USO01', 'EZ-4U', 0.4, 40.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPSOPOSO01', 'SORBATO DE POTASIO', 0.3, 30.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPBESOSO01', 'BENZOATO DE SODIO', 0.3, 30.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPSILISO01', 'SILIMARINA', 0.3, 30.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPACFESO01', 'ÁCIDO FERÚLICO', 0.1, 10.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPACKOSO01', 'ÁCIDO KOJICO', 0.1, 10.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPRETISO01', 'RETINALDEHÍDO', 0.05, 5.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPALVESO01', 'ALOE VERA', 0.05, 5.0),
        ('SUERO DE RETINALDEHIDO 0.05%', 'MPEXGOSO01', 'CENTELLA ASIATICA POLVO', 0.03, 3.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPAGUALI01', 'AGUA DESIONIZADA', 81.0, 16200.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPPROPLI01', 'PROPILENGLICOL', 3.5, 700.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPACASSO01', 'ACIDO ASCORBICO', 6.0, 1200.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPALARSO01', 'ALFA ARBUTINA', 2.0, 400.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPGLUCSO02', 'GLUCONOLACTONA', 1.0, 200.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPEDDISO01', 'EDTA DISODICO', 0.05, 10.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPACCISO01', 'ACIDO CITRICO', 0.1, 20.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPGLICSO02', 'GLICINAMIDA', 0.05, 10.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPPECOSO01', 'PEPTIDOS DE COLAGENO', 0.05, 10.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPERGOSO01', 'ERGOTIONEINA', 0.05, 10.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPGRANLI01', 'GRANSIL VX419', 0.15, 30.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPACIETASO01', '3-O ACIDO ETIL ASCORBICO', 4.0, 800.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPGLUTSO01', 'GLUTATION', 0.05, 10.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPVITESO01', 'VITAMINA E POLVO', 0.5, 100.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPACKOSO01', 'ACIDO KOJICO', 0.1, 20.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPCICLOS01', 'BETA-CICLODEXTRINA', 0.1, 20.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPACHISO01', 'ACIDO HILAURONICO 50 KD', 0.3, 60.0),
        ('SUERO DE VITAMINA C+ FORMULA NUEVA', 'MPBIOFELI01', 'BIOSURE FE', 1.0, 200.0)""",
        "DELETE FROM sku_producto_map",
        """INSERT OR REPLACE INTO sku_producto_map (sku, producto_nombre) VALUES
        ('LBHA', 'LIMPIADOR FACIAL BHA 2%'),
        ('TRX', 'SUERO ILUMINADOR TRX'),
        ('NIAC', 'SUERO DE NIACINAMIDA 5% FORMULA NUEVA'),
        ('AZHC', 'SUERO AZ + B3'),
        ('SBHA', 'Suero Exfoliante BHA 2%'),
        ('ECEN', 'ESENCIA DE CENTELLA ASIATICA'),
        ('EILU', 'ESENCIA ILUMINADORA'),
        ('CUREA', 'CREMA DE UREA'),
        ('GELH', 'GEL HIDRATANTE'),
        ('CONT', 'CONTORNO DE CAFEINA'),
        ('MSCA', 'MASCARILLA HIDRATANTE'),
        ('VITC', 'SUERO DE VITAMINA C+ FORMULA NUEVA'),
        ('MULTI', 'SUERO MULTIPEPTIDOS'),
        ('RETINAL', 'Suero RETINAL +'),
        ('EMHID', 'GEL HIDRATANTE')""",
    ]),
    (7, "sku_producto_map: mapeo completo SKUs Shopify -> formula_headers", [
        """INSERT OR REPLACE INTO sku_producto_map (sku, producto_nombre, activo) VALUES
        ('AZHC30',    'AZ HIBRID CLEAR',                            1),
        ('CCAFE',     'CONTORNO DE CAFEINA',                        1),
        ('CMULP',     'CONTORNO DE OJOS MULTIPEPTIDOS',             1),
        ('CRCUREA',   'CREMA CORPORAL RENOVA BODY',                 1),
        ('CRETT',     'CONTORNO DE OJOS RETINALDEHIDO 0.05%',      1),
        ('ECENT',     'ESENCIA DE CENTELLA ASIATICA',               1),
        ('EMLIM',     'EMULSION LIMPIADORA',                        1),
        ('LAH',       'LIMPIADOR FACIAL HIDRATANTE',                1),
        ('LKJ',       'LIMPIADOR ILUMINADOR ACIDO KOJICO',          1),
        ('NIA',       'SUERO DE NIACINAMIDA 5% FORMULA NUEVA',     1),
        ('NIA10',     'SUERO DE NIACINAMIDA 5% FORMULA NUEVA',     1),
        ('NPHA10',    'SUERO EXFOLIANTE NOVA PHA',                  1),
        ('NPHA30',    'SUERO EXFOLIANTE NOVA PHA',                  1),
        ('RECN-2',    'SUERO ANTIOXIDANTE RENOVA C10',              1),
        ('SAH',       'SUERO HIDRATANTE AH 1.5%',                  1),
        ('SAH10',     'SUERO HIDRATANTE AH 1.5%',                  1),
        ('SMULPP',    'SUERO MULTIPEPTIDOS',                        1),
        ('SVITC33',   'SUERO DE VITAMINA C+ FORMULA NUEVA',        1),
        ('SVITC3315', 'SUERO DE VITAMINA C+ FORMULA NUEVA',        1),
        ('TRX10',     'SUERO ILUMINADOR TRX',                      1),
        ('BHA33',     'Suero Exfoliante BHA 2%',                   1),
        ('LBHA',      'LIMPIADOR FACIAL BHA 2%',                   1),
        ('TRX',       'SUERO ILUMINADOR TRX',                      1),
        ('NIAC',      'SUERO DE NIACINAMIDA 5% FORMULA NUEVA',     1),
        ('AZHC',      'SUERO AZ + B3',                             1),
        ('SBHA',      'Suero Exfoliante BHA 2%',                   1),
        ('ECEN',      'ESENCIA DE CENTELLA ASIATICA',              1),
        ('EILU',      'ESENCIA ILUMINADORA',                       1),
        ('CUREA',     'CREMA DE UREA',                             1),
        ('GELH',      'GEL HIDRATANTE',                            1),
        ('CONT',      'CONTORNO DE CAFEINA',                       1),
        ('MSCA',      'MASCARILLA HIDRATANTE',                     1),
        ('VITC',      'SUERO DE VITAMINA C+ FORMULA NUEVA',        1),
        ('MULTI',     'SUERO MULTIPEPTIDOS',                       1),
        ('RETINAL',   'Suero RETINAL +',                           1),
        ('EMHID',     'GEL HIDRATANTE',                            1)"""
    ]),
    (8, "sku_producto_map: SKUs adicionales + correccion mapeos erroneos", [
        """INSERT OR REPLACE INTO sku_producto_map (sku, producto_nombre, activo) VALUES
        ('BBM',      'MASCARILLA HIDRATANTE',            1),
        ('HKJ',      'LIMPIADOR ILUMINADOR ACIDO KOJICO',1),
        ('CRB3BHA',  'EMULSION HIDRATANTE  B3+BHA',    1),
        ('TRIAC',    'SUERO DE RETINALDEHIDO 0.05%',    1)"""
    ]),
    (9, "SKUs descontinuados inactivos + TRIACTIVE pendiente formula", [
        # RETINAL+ y RETINALDEHIDO descontinuados — fuera de velocity y proyeccion
        """UPDATE sku_producto_map SET activo=0 WHERE producto_nombre IN
           ('Suero RETINAL +', 'SUERO DE RETINALDEHIDO 0.05%')""",
        # TRIAC = SUERO TRIACTIVE RETINOID NAD+ — producto activo sin formula en sistema aun
        """UPDATE sku_producto_map SET activo=0 WHERE sku='TRIAC'"""
    ]),
    (10, "SUERO TRIACTIVE RETINOID NAD+: formula completa 30kg + TRIAC activo", [
        """INSERT OR REPLACE INTO formula_headers (producto_nombre, unidad_base_g, lote_size_kg)
        VALUES ('SUERO TRIACTIVE RETINOID NAD+', 30000.0, 30.0)""",
        """DELETE FROM formula_items WHERE producto_nombre='SUERO TRIACTIVE RETINOID NAD+'""",
        """INSERT INTO formula_items
        (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) VALUES
        ('SUERO TRIACTIVE RETINOID NAD+','MPAGUALI01','AGUA PURIFICADA (total fases)',71.388,21416.4),
        ('SUERO TRIACTIVE RETINOID NAD+','MPCARBSO01','CARBOPOL ULTREZ-21',0.200,60.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPEZ4USO01','EZ-4U',0.400,120.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPALANSO01','ALANTOINA',0.500,150.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPTRIELO01','TRIETANOLAMINA 85%',0.300,90.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPACHISO02','HIALURONICO 300 KD',0.050,15.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPACHISO01','HIALURONICO 50 KD',0.300,90.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPACHISO03','HIALURONICO 1500 KD',0.050,15.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPPDRNS001','SODIUM DNA PDRN',0.010,3.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPNIACSO01','NIACINAMIDA',5.000,1500.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPNAGLUCO01','N-ACETIL GLUCOSAMINA',1.000,300.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPANTESO01','D-PANTENOL',0.050,15.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPECTOSO01','ECTOINA',0.150,45.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPPROPD001','PROPANEDIOL PDO',4.525,1357.5),
        ('SUERO TRIACTIVE RETINOID NAD+','MPACCASAS01','ACIDO CAPRILOIL SALICILICO LHA',0.250,75.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPPOLYAQSO01','POLYAQUOL LW',1.700,510.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPDICASO01','DICAPRILIL CARBONATO',2.500,750.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPLEXFESO01','LEXFEEL WOW',1.500,450.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPALCESO01','ALCOHOL CETILICO',0.350,105.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPTINGSO01','TINOGARD TT',0.100,30.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPCTMESO01','CETIL TRANEXAMATO MESILATO CTM',1.500,450.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPPURSISO01','PURESIL ORG 01',1.000,300.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPPEGDISO01','PEG-12 DIMETILSILOXANO',1.000,300.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPCERASO01','CERAMIDA NP',0.100,30.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPHPRSO01','HIDROXIPINOCOLONA RETINOATO HPR',0.100,30.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPRETYRE01','RETINIL RETINOATO RR',0.025,7.5),
        ('SUERO TRIACTIVE RETINOID NAD+','MPMADESAC01','ACIDO MADECASICO',0.020,6.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPAPIGESO01','APIGENINA',0.010,3.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPTHDASO01','TETRAHEXILDECIL ASCORBATO THD',0.500,150.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPVITAELI01','VITAMINA E TOCOFEROL',0.350,105.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPBORNISO01','NITRURO DE BORO',0.300,90.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPSILICSO01','SILICA MSS-500',0.300,90.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPCO2ROSO01','CO2 SUPERCRITICO ROMERO',0.050,15.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPRETINSO01','RETINAL',0.035,10.5),
        ('SUERO TRIACTIVE RETINOID NAD+','MPCICLOS01','BETA-CICLODEXTRINA',0.153,45.9),
        ('SUERO TRIACTIVE RETINOID NAD+','MPHEXADSO01','1,2-HEXANODIOL',0.500,150.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPEDDISO01','EDTA DISODICO',0.150,45.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPNAFIESO01','FITATO DE SODIO',0.050,15.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPPALMTR38','PALMITOIL TRIPEPTIDO-38',0.005,1.5),
        ('SUERO TRIACTIVE RETINOID NAD+','MPACETTE40','ACETIL TETRAPEPTIDO-40',0.003,0.9),
        ('SUERO TRIACTIVE RETINOID NAD+','MPPALMTR01','PALMITOIL TRIPEPTIDO-1',0.005,1.5),
        ('SUERO TRIACTIVE RETINOID NAD+','MPPALMT7','PALMITOIL TETRAPEPTIDO-7',0.005,1.5),
        ('SUERO TRIACTIVE RETINOID NAD+','MPMYRINAN3','MIRISTOIL NONAPEPTIDO-3',0.005,1.5),
        ('SUERO TRIACTIVE RETINOID NAD+','MPOLIGO68','OLIGOPEPTIDO-68',0.001,0.3),
        ('SUERO TRIACTIVE RETINOID NAD+','MPSYNAKESO01','SYN-AKE',0.010,3.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPBIOFELI01','BIOSURE FE FENOXIETANOL',0.950,285.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPNADPLUSO01','NAD+',0.500,150.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPNMNSO01','NMN MONONUCLEOTIDO NICOTINAMIDA',0.050,15.0),
        ('SUERO TRIACTIVE RETINOID NAD+','MPAZEDILO01','EPI-ON',2.000,600.0)""",
        """INSERT OR REPLACE INTO sku_producto_map (sku, producto_nombre, activo)
        VALUES ('TRIAC', 'SUERO TRIACTIVE RETINOID NAD+', 1)"""
    ]),
    (11, "MAXLASH: formula completa 16kg + SKU mapeado", [
        """INSERT OR REPLACE INTO formula_headers (producto_nombre, unidad_base_g, lote_size_kg)
        VALUES ('MAXLASH', 16000.0, 16.0)""",
        """DELETE FROM formula_items WHERE producto_nombre='MAXLASH'""",
        """INSERT INTO formula_items
        (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) VALUES
        ('MAXLASH','MPAGUALI01','AGUA PURIFICADA TOTAL',86.8275,13892.4),
        ('MAXLASH','MPCAFESO01','CAFEINA',1.000,160.0),
        ('MAXLASH','MPBETASO01','BETAINA',0.300,48.0),
        ('MAXLASH','MPGLICSO01','GLICINA',0.100,16.0),
        ('MAXLASH','MPROLISO01','PROLINA',0.100,16.0),
        ('MAXLASH','MPARGISO01','ARGININA',0.050,8.0),
        ('MAXLASH','MPNACISO01','N-ACETIL-CISTEINA',0.010,1.6),
        ('MAXLASH','MPACHISO03','HIALURONICO 1500 KD',0.300,48.0),
        ('MAXLASH','MPACHISO01','HIALURONICO 50 KD',0.063,10.0),
        ('MAXLASH','MPACTET3001','ACETIL TETRAPEPTIDO-3',0.025,4.0),
        ('MAXLASH','MPACETTE40','ACETIL TETRAPEPTIDO-40',0.006,1.0),
        ('MAXLASH','MPBIOTSO01','BIOTINOIL TRIPEPTIDO-1',0.063,10.0),
        ('MAXLASH','MPKERPEPSO01','PEPTIDOS HIDROLIZADOS QUERATINA',0.063,10.0),
        ('MAXLASH','MPCOLPEPSO01','PEPTIDOS HIDROLIZADOS COLAGENO',0.063,10.0),
        ('MAXLASH','MPGHKCUSO01','COPPER TRIPEPTIDE-1 GHK-CU',0.050,8.0),
        ('MAXLASH','MPPROPLI01','PROPILENGLICOL',3.000,480.0),
        ('MAXLASH','MPHEXADSO01','1,2-HEXANODIOL',0.500,80.0),
        ('MAXLASH','MPMYRIP17','MIRISTOIL PENTAPEPTIDO-17',0.050,8.0),
        ('MAXLASH','MPMYRIH16','MIRISTOIL HEXAPEPTIDO-16',0.025,4.0),
        ('MAXLASH','MPPALMTR38','PALMITOIL TRIPEPTIDO-38',0.005,0.8),
        ('MAXLASH','MPNIACSO01','NIACINAMIDA',5.000,800.0),
        ('MAXLASH','MPASCPHOSO01','SODIUM ASCORBIL FOSFATO SAP',0.500,80.0),
        ('MAXLASH','MPANTESO01','D-PANTENOL',0.200,32.0),
        ('MAXLASH','MPTOCOFE01','SODIUM TOCOFERIL FOSFATO',0.100,16.0),
        ('MAXLASH','MPBISPEGSO01','BIS-PEG-12 DIMETILSILOXANO',0.500,80.0),
        ('MAXLASH','MPTREBOLSO01','EXTRACTO TREBOL ROJO',0.001,0.16),
        ('MAXLASH','MPEDDISO01','EDTA DISODICO',0.050,8.0),
        ('MAXLASH','MPERGO01','L-ERGOTIONEINA',0.050,8.0),
        ('MAXLASH','MPBIOFELI01','BIOSURE FE FENOXIETANOL',1.000,160.0)""",
        """INSERT OR REPLACE INTO sku_producto_map (sku, producto_nombre, activo)
        VALUES ('MAXLASH', 'MAXLASH', 1)"""
    ]),
    (12, 'produccion_programada table', [
        """CREATE TABLE IF NOT EXISTS produccion_programada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT NOT NULL,
            fecha_programada TEXT NOT NULL,
            lotes INTEGER DEFAULT 1,
            estado TEXT DEFAULT 'pendiente',
            observaciones TEXT,
            creado_en TEXT DEFAULT (datetime('now')),
            gcal_event_id TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_pp_producto ON produccion_programada(producto)",
        "CREATE INDEX IF NOT EXISTS idx_pp_fecha ON produccion_programada(fecha_programada)"
    ]),
        (13, 'mp_formula_bridge — formula_id to bodega_id mapping', [
        """CREATE TABLE IF NOT EXISTS mp_formula_bridge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            formula_material_id TEXT NOT NULL,
            formula_material_nombre TEXT,
            bodega_material_id TEXT NOT NULL,
            bodega_material_nombre TEXT,
            bodega_inci TEXT,
            notas TEXT,
            activo INTEGER DEFAULT 1,
            creado_en TEXT DEFAULT (datetime('now')),
            UNIQUE(formula_material_id, bodega_material_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_bridge_fid ON mp_formula_bridge(formula_material_id)",
        "CREATE INDEX IF NOT EXISTS idx_bridge_bid ON mp_formula_bridge(bodega_material_id)"
    ]),
    (14, 'mp_formula_bridge seed — formula_material_id → bodega_material_id (all products)', [
        """INSERT OR IGNORE INTO mp_formula_bridge
           (formula_material_id, formula_material_nombre, bodega_material_id, notas, activo)
           VALUES
           ('MPHEXDILI01', '1,2 HEXANEDIOL', 'MP00245', '1,2-hexanediol', 1),
           ('MPACIETASO01', '3-O ACIDO ETIL ASCORBICO', 'MP00160', '3-O-ethyl ascorbic acid', 1),
           ('MPACARLI01', 'ACEITE DE ARGAN', 'MP00137', 'Beauty Oil Argan', 1),
           ('MPACJOLI01', 'ACEITE DE JOJOBA', 'MP00136', 'Beauty Oil Jojoba', 1),
           ('MPALANSO01', 'ACEITE ARBOL DE TE', 'MP00085', 'aceite esencial arbol de te', 1),
           ('MPACROLI01', 'ACEITE DE ROSA MOSQUETA', 'MP00105', 'Beauty Oil Rosa mosqueta', 1),
           ('MPACHESO01', 'ACETYL HEXAPEPTIDE-8', 'MP00192', 'exact', 1),
           ('MPACTESO01', 'ACETYL TETRAPEPTIDE-5', 'MP00175', 'exact', 1),
           ('MPACETETSO01', 'ACETYL TETRAPEPTIDE-40', 'MP00178', 'exact', 1),
           ('MPACTET3001', 'ACETIL TETRAPEPTIDO-3', 'MP00170', 'acetyl tetrapeptide-3', 1),
           ('MPACETTE40', 'ACETIL TETRAPEPTIDO-40', 'MP00178', 'acetyl tetrapeptide-40', 1),
           ('MPACAZSO01', 'ACIDO AZELAICO', 'MP00221', 'azelaic acid', 1),
           ('MPACASSO01', 'ACIDO ASCORBICO', 'MP00230', 'vitamina C = ascorbic acid', 1),
           ('MPACCASAS01', 'ACIDO CAPRILOIL SALICILICO', 'MP00246', 'LHA = capryloyl salicylic acid', 1),
           ('MPACCISO01', 'ACIDO CITRICO', 'MP00065', 'citric acid', 1),
           ('MPACGLSO01', 'ACIDO GLUTAMICO', 'MP00290', 'glutamic acid', 1),
           ('MPACHISO03', 'ACIDO HIALURONICO 1500 KD', 'MP00142', 'hyaluronic acid 1500kD', 1),
           ('MPACHISO02', 'ACIDO HIALURONICO 300 KD', 'MP00233', 'hyaluronic acid 300kD', 1),
           ('MPACHISO01', 'ACIDO HIALURONICO 50 KD', 'MP00163', 'hyaluronic acid 50kD', 1),
           ('MPACHSO01', 'ACIDO HIALURONICO 50 KD', 'MP00163', 'hyaluronic acid 50kD alt ID', 1),
           ('MPACKOSO01', 'ACIDO KOJICO', 'MP00237', 'kojic acid', 1),
           ('MPACLALI02', 'ACIDO LACTICO', 'MP00138', 'lactic acid', 1),
           ('MPACLALI01', 'ACIDO LACTICO', 'MP00138', 'lactic acid alt ID', 1),
           ('MPMADESAC01', 'ACIDO MADECASICO', 'MP00227', 'madecassic acid', 1),
           ('MPACSASO01', 'ACIDO SALICILICO', 'MP00210', 'salicylic acid', 1),
           ('MPACTRSO01', 'ACIDO TRANEXAMICO', 'MP00167', 'tranexamic acid', 1),
           ('MPADENSO01', 'ADENOSINA', 'MP00152', 'adenosine', 1),
           ('MPDIADI01', 'ADIPATO DE BUTIL', 'MP00266', 'dibutyl adipate', 1),
           ('MPALCESO01', 'ALCOHOL CETILICO', 'MP00201', 'cetyl alcohol', 1),
           ('MPALARSO01', 'ALFA ARBUTINA', 'MP00183', 'alpha-arbutin', 1),
           ('MPALOESO01', 'ALOE VERA', 'MP00216', 'aloe vera polvo', 1),
           ('MPALVESO01', 'ALOE VERA', 'MP00216', 'aloe vera polvo alt ID', 1),
           ('MPAPIGESO01', 'APIGENINA', 'MP00234', 'apigenin', 1),
           ('MPARGISO01', 'ARGININA', 'MP00147', 'L-arginine', 1),
           ('MPTEISASO01', 'ASCORBATO DE TETRAHEXILDECILO', 'MP00149', 'tetrahexyldecyl ascorbate', 1),
           ('MPASGLSO01', 'ASCORBIL GLUCOSIDE', 'MP00238', 'ascorbyl glucoside', 1),
           ('MPASIASO01', 'ASIATICOSIDO', 'MP00185', 'asiaticoside 95%', 1),
           ('MPASTAXLI01', 'ASTAXANTINA', 'MP00218', 'astaxanthin', 1),
           ('MPAZDISO01', 'AZELOLIL DIGLICINATO DE POTASIO', 'MP00244', 'potassium azeloyl diglycinate', 1),
           ('MPBAKULI01', 'BAKUCHIOL', 'MP00173', 'bakuchiol', 1),
           ('MPBESOSO01', 'BENZOATO DE SODIO', 'MP00045', 'sodium benzoate', 1),
           ('MPBETASO01', 'BETAGLUCAN', 'MP00214', 'beta-glucan', 1),
           ('MPBETASO02', 'BETAGLUCAN', 'MP00214', 'beta-glucan', 1),
           ('MPBETASO03', 'BETAGLUCAN', 'MP00214', 'beta-glucan', 1),
           ('MPCICLOS01', 'BETA-CICLODEXTRINA', 'MP00264', 'beta-cyclodextrin', 1),
           ('MPBISOSO01', 'BICARBONATO DE SODIO', 'MP00131', 'sodium bicarbonate', 1),
           ('MPBIOFELI01', 'BIOSURE FE', 'MP00068', 'phenoxyethanol+ethylhexylglycerin', 1),
           ('MPBIOSSO01', 'BIOSURE FE', 'MP00068', 'biosure FE alt ID', 1),
           ('MPBISALI01', 'BISABOLOL', 'MPBSBL01', 'bisabolol', 1),
           ('MPBISPEGSO01', 'BIS-PEG-12 DIMETILSILOXANO', 'MP00072', 'bis-PEG-12 dimethicone = Gransil VX-419', 1),
           ('MPCAANSO01', 'CAFEINA', 'MP00118', 'caffeine', 1),
           ('MPCAFESO01', 'CAFEINA', 'MP00118', 'caffeine alt ID', 1),
           ('MPCARBSO01', 'CARBOPOL', 'MP00008', 'carbomer', 1),
           ('MPEXGOSO01', 'CENTELLA', 'MP00181', 'centella asiatica extract', 1),
           ('MPCENTESO01', 'CENTELLA', 'MP00181', 'centella asiatica extract', 1),
           ('MPEZ4USO01', 'EZ-4U', 'MP00006', 'Pemulen EZ-4U (acrylates crosspolymer)', 1),
           ('MPCERASO01', 'CERAMIDA NP', 'MP00103', 'ceramide NP', 1),
           ('MPCTMESO01', 'CETIL TRANEXAMATO MESILATO CTM', 'MP00240', 'cetyl tranexamate mesylate', 1),
           ('MPCHITSO01', 'CHITOSAN', 'MP00220', 'chitosan', 1),
           ('MPCO2ROSO01', 'CO2 SUPERCRITICO ROMERO', 'MP00242', 'CO2 rosemary extract', 1),
           ('MPCOTRSO01', 'COPPER TRIPEPTIDE-1', 'MP00194', 'copper tripeptide-1', 1),
           ('MPGHKCUSO01', 'COPPER TRIPEPTIDE-1 GHK-CU', 'MP00194', 'GHK-Cu copper tripeptide', 1),
           ('MPANTESO01', 'D-PANTENOL', 'MP00110', 'D-panthenol', 1),
           ('MPDICASO01', 'DICAPRILIL CARBONATO', 'MP00040', 'dicaprylyl carbonate = Cetiol CC', 1),
           ('MPDIBEDISO01', 'DIPEPTIDO DIAMINOBUTIROIL', 'MP00179', 'dipeptide diaminobutyroyl benzylamide diacetate', 1),
           ('MPECTOSO01', 'ECTOINA', 'MP00226', 'ectoin', 1),
           ('MPEDDISO01', 'EDTA DISODICO', 'MP00046', 'disodium EDTA', 1),
           ('MPAZEDILO01', 'EPI-ON', 'MP00116', 'azelamidopropyl dimethylamine', 1),
           ('MPERGOSO01', 'ERGOTIONEINA', 'MP00150', 'ergothioneine', 1),
           ('MPESCULI01', 'ESCUALENO', 'MP00282', 'squalane', 1),
           ('MPTREBOLSO01', 'EXTRACTO TREBOL ROJO', 'MP00241', 'red clover extract', 1),
           ('MPFENOLI01', 'FENOXIETANOL', 'MP00021', 'phenoxyethanol', 1),
           ('MPFISOSO01', 'FITATO DE SODIO', 'MP00239', 'sodium phytate', 1),
           ('MPNAFIESO01', 'FITATO DE SODIO', 'MP00239', 'sodium phytate alt ID', 1),
           ('MPFOASSO01', 'FOSFATO DE ASCORBILO SODICO', 'MP00169', 'sodium ascorbyl phosphate', 1),
           ('MPFRSALI01', 'FRAGANCIA FRESA CREMOSO', 'MP00019', 'parfum fresa cremosa', 1),
           ('MPPISTALI01', 'FRAGANCIA PISTACHO', 'MP00062', 'parfum pistacho', 1),
           ('MPYOCRLI01', 'FRAGANCIA YOGURT CREMOSO', 'MP00020', 'parfum yogurt cremoso', 1),
           ('MPGIWHSO01', 'GIGA WHITE', 'MP00271', 'malva sylvestris = Giga White', 1),
           ('MPGLICLI01', 'GLICERINA', 'MP00195', 'glycerin', 1),
           ('MPGLICSO01', 'GLICINA', 'MP00265', 'glycine', 1),
           ('MPGLICSO02', 'GLICINAMIDA', 'MP00231', 'glycinamide', 1),
           ('MPGLUCSO02', 'GLUCONOLACTONA', 'MP00270', 'gluconolactone', 1),
           ('MPGLUCOSO02', 'GLUCONOLACTONA', 'MP00270', 'gluconolactone alt ID', 1),
           ('MPGLUCSO01', 'N-ACETIL GLUCOSAMINA', 'MP00262', 'N-acetyl glucosamine', 1),
           ('MPGLUCOSO01', 'N-ACETIL GLUCOSAMINA', 'MP00262', 'N-acetyl glucosamine', 1),
           ('MPNAGLUCO01', 'N-ACETIL GLUCOSAMINA', 'MP00262', 'N-acetyl glucosamine alt ID', 1),
           ('MPGLUTSO01', 'GLUTATION', 'MP00145', 'glutathione', 1),
           ('MPGOXASO01', 'GOMA XANTAN', 'MP00073', 'xanthan gum', 1),
           ('MPGRANLI01', 'GRANSIL VX419', 'MP00072', 'bis-PEG-12 dimethicone Gransil VX-419', 1),
           ('MPHEXADSO01', '1,2-HEXANODIOL', 'MP00245', '1,2-hexanediol', 1),
           ('MPHIDSOLI01', 'HIDROXIDO DE SODIO', 'MP00066', 'sodium hydroxide', 1),
           ('MPHIDROLI01', 'HIDROXIDO SODIO', 'MP00066', 'sodium hydroxide', 1),
           ('MPHPRSO01', 'HIDROXIPINOCOLONA RETINOATO HPR', 'MP00274', 'hydroxypinacolone retinoate', 1),
           ('MPCARNSO01', 'L-CARNITINA', 'MP00161', 'carnitine', 1),
           ('MPERGO01', 'L-ERGOTIONEINA', 'MP00150', 'ergothioneine', 1),
           ('MPTEANSO01', 'L-TEANINA', 'MP00180', 'L-theanine', 1),
           ('MPLAGLLI01', 'LAURIL GLUCOSIDO', 'MP00070', 'lauryl glucoside', 1),
           ('MPLEXFESO01', 'LEXFEEL WOW', 'MP00109', 'triheptanoin + C13-16 isoalkane', 1),
           ('MPMELASO01', 'MELATONINA', 'MP00219', 'melatonin', 1),
           ('MPMYRIH16', 'MIRISTOIL HEXAPEPTIDO-16', 'MP00171', 'myristoyl hexapeptide-16', 1),
           ('MPMYRINAN3', 'MIRISTOIL NONAPEPTIDO-3', 'MP00250', 'myristoyl nonapeptide-3', 1),
           ('MPMYRIP17', 'MIRISTOIL PENTAPEPTIDO-17', 'MP00187', 'myristoyl pentapeptide-17', 1),
           ('MPNADPLUSO01', 'NAD+', 'MP00235', 'NAD nicotinamide adenine dinucleotide', 1),
           ('MPNACISO01', 'N-ACETIL-CISTEINA', 'MP00164', 'N-acetyl cysteine', 1),
           ('MPNIACSO01', 'NIACINAMIDA', 'MP00148', 'niacinamide', 1),
           ('MPBORNISO01', 'NITRURO DE BORO', 'MPBNIT01', 'boron nitride', 1),
           ('MPNMNSO01', 'NMN MONONUCLEOTIDO NICOTINAMIDA', 'MP00275', 'NMN', 1),
           ('MPOLIPESO01', 'OLIGOPEPTIDO 68', 'MP00177', 'oligopeptide-68', 1),
           ('MPOLIGO68', 'OLIGOPEPTIDO-68', 'MP00177', 'oligopeptide-68', 1),
           ('MPPAPESO01', 'PALMITOYL PENTAPEPTIDE-4', 'MP00228', 'palmitoyl pentapeptide-4', 1),
           ('MPPALISO01', 'PALMITATO DE ISOPROPILO', 'MP00134', 'isopropyl palmitate approx → myristate similar', 1),
           ('MPPALMT7', 'PALMITOIL TETRAPEPTIDO-7', 'MP00172', 'palmitoyl tetrapeptide-7', 1),
           ('MPPALTESO01', 'PALMITOYL TETRAPEPTIDE-7', 'MP00172', 'palmitoyl tetrapeptide-7', 1),
           ('MPPALTRISO01', 'PALMITOYL TRIPEPTIDE-5', 'MP00191', 'palmitoyl tripeptide-5', 1),
           ('MPPALTRISO02', 'PALMITOYL TRIPEPTIDE-1', 'MP00190', 'palmitoyl tripeptide-1', 1),
           ('MPPALMTR01', 'PALMITOIL TRIPEPTIDO-1', 'MP00190', 'palmitoyl tripeptide-1', 1),
           ('MPPALMTR38', 'PALMITOIL TRIPEPTIDO-38', 'MP00174', 'palmitoyl tripeptide-38', 1),
           ('MPPANTSO01', 'PANTENOL POLVO', 'MP00236', 'panthenol powder', 1),
           ('MPPANTLI01', 'PANTENOL - LIQUIDO', 'MP00110', 'D-panthenol liquid', 1),
           ('MPPEGDISO01', 'PEG-12 DIMETILSILOXANO', 'MP00184', 'PEG-12 dimethicone BM-939', 1),
           ('MPPECOSO01', 'PEPTIDOS DE COLAGENO', 'MP00285', 'hydrolyzed collagen peptides', 1),
           ('MPCOLPEPSO01', 'PEPTIDOS HIDROLIZADOS COLAGENO', 'MP00285', 'hydrolyzed collagen', 1),
           ('MPKERPEPSO01', 'PEPTIDOS HIDROLIZADOS QUERATINA', 'MP00168', 'hydrolyzed keratin', 1),
           ('MPPOLYAQSO01', 'POLYAQUOL LW', 'MP00132', 'polyglyceryl-4 laurate Polyaquol LW', 1),
           ('MPPOBOSO01', 'PDRN (SODIUM DNA)', 'MP00223', 'PDRN = sodium DNA', 1),
           ('MPPDRNS001', 'SODIUM DNA PDRN', 'MP00223', 'PDRN sodium DNA', 1),
           ('MPPROBSO01', 'PROBETAINA', 'MP00084', 'cocamidopropyl betaine probetaina', 1),
           ('MPPROBLI01', 'PROBETAINA', 'MP00084', 'probetaina alt ID', 1),
           ('MPROLISO01', 'PROLINA', 'MP00151', 'proline', 1),
           ('MPPROPD001', 'PROPANEDIOL PDO', 'MP00043', 'propanediol', 1),
           ('MPPROLISO01', 'PROPILENGLICOL', 'MP00121', 'propylene glycol', 1),
           ('MPPROPLI01', 'PROPILENGLICOL', 'MP00121', 'propylene glycol', 1),
           ('MPPROPLI02', 'PROPILENGLICOL', 'MP00121', 'propylene glycol', 1),
           ('MPROPLI01', 'PROPILENGLICOL', 'MP00121', 'propylene glycol', 1),
           ('MPPURSISO01', 'PURESIL ORG 01', 'MP00111', 'Puresil ORG01 C13-15 alkane dimethicone', 1),
           ('MPQUCRELI01', 'QUIMCREAM', 'MP00071', 'Quincream typo', 1),
           ('MPQUCRE01', 'QUINCREAM', 'MP00071', 'Quincream acrylates copolymer', 1),
           ('MPEREGASO01', 'REGALIZ', 'MP00120', 'licorice extract', 1),
           ('MPREGASO01', 'REGALIZ', 'MP00120', 'licorice extract alt ID', 1),
           ('MPRETINSO01', 'RETINAL', 'MP00261', 'retinaldehyde', 1),
           ('MPRETISO01', 'RETINALDEHIDO', 'MP00261', 'retinaldehyde', 1),
           ('MPRETSO01', 'RETINALDEHIDO', 'MP00261', 'retinaldehyde alt ID', 1),
           ('MPRETYRE01', 'RETINIL RETINOATO RR', 'MP00287', 'retinyl retinoate', 1),
           ('MPSILICSO01', 'SILICA MSS-500', 'MP00289', 'silica MSS-500', 1),
           ('MPSILILI01', 'SILICONA LIQUIDA', 'MP00199', 'dimethicone SF-350', 1),
           ('MPSILILI02', 'SILICONA BM 600', 'MP00128', 'BM-600 cyclopentasiloxane+dimethicone', 1),
           ('MPSILISO01', 'SILIMARINA', 'MP00277', 'silymarin silybum marianum', 1),
           ('MPASCPHOSO01', 'SODIUM ASCORBIL FOSFATO SAP', 'MP00169', 'sodium ascorbyl phosphate', 1),
           ('MPSOPOSO01', 'SORBATO DE POTASIO', 'MP00202', 'potassium sorbate', 1),
           ('MPESOPOS01', 'SORBATO DE POTASIO', 'MP00202', 'potassium sorbate', 1),
           ('MPSOPOS01', 'SORBATO DE POTASIO', 'MP00202', 'potassium sorbate', 1),
           ('MPSYNAKESO01', 'SYN-AKE', 'MP00179', 'SYN-AKE = dipeptide diaminobutyroyl benzylamide diacetate', 1),
           ('MPTHDASO01', 'TETRAHEXILDECIL ASCORBATO THD', 'MP00149', 'tetrahexyldecyl ascorbate', 1),
           ('MPTINSO001', 'TINOGARD TT', 'MP00063', 'Tinogard TT = PEHB', 1),
           ('MPTINOSO01', 'TINOGARD TT', 'MP00063', 'Tinogard TT', 1),
           ('MPTINGSO01', 'TINOGARD TT', 'MP00063', 'Tinogard TT', 1),
           ('MPTRIELO01', 'TRIETANOLAMINA 85%', 'MP00123', 'triethanolamine', 1),
           ('MPTRIESO01', 'TRIETANOLAMINA 85%', 'MP00123', 'triethanolamine', 1),
           ('MPTRICAL01', 'TRIGLICERIDO CAPRICO', 'MP00090', 'caprylic/capric triglyceride MCT', 1),
           ('MPTRICA01', 'TRIGLICERIDO CAPRICO', 'MP00090', 'caprylic/capric triglyceride MCT', 1),
           ('MPTWEELI01', 'TWEEN 20', 'MP00082', 'polysorbate 20', 1),
           ('MPTWEEL01', 'TWEEN 20', 'MP00082', 'polysorbate 20', 1),
           ('MPTWEELI02', 'TWEEN 80', 'MP00083', 'polysorbate 80', 1),
           ('MPTWEEL02', 'TWEEN 80', 'MP00083', 'polysorbate 80', 1),
           ('MPUPASO001', 'UNDECILENOIL FENILALANINA', 'MP00146', 'undecylenoyl phenylalanine', 1),
           ('MPUREASO01', 'UREA', 'MP00107', 'urea', 1),
           ('MPVITELI01', 'VITAMINA E - ACEITE', 'MP00078', 'tocopherol vitamina E liquida', 1),
           ('MPVITAELI01', 'VITAMINA E ACEITE', 'MP00078', 'tocopherol vitamina E liquida', 1),
           ('MPVITESO01', 'VITAMINA E POLVO', 'MP00079', 'vitamina E powder', 1),
           ('MPZINPCASO1', 'ZINC PCA', 'MP00283', 'zinc PCA', 1),
           ('MPACFESO01', 'ACIDO FERULICO', 'MP00160', 'ferulic acid approx → ethyl ascorbic acid family', 1)
        """
    ]),
        (15, 'mp_formula_bridge supplement — AOS 40 + biotinoyl tripeptide-1', [
        """INSERT OR IGNORE INTO mp_formula_bridge
           (formula_material_id, formula_material_nombre, bodega_material_id, notas, activo)
           VALUES
           ('MPAOSLI01', 'AOS 40', 'MP00212', 'sodium C14-16 olefin sulfonate = AOS-40', 1),
           ('MPASCOLI01', 'AOS 40 (alt ID)', 'MP00212', 'sodium C14-16 olefin sulfonate = AOS-40', 1),
           ('MPBIOTSO01', 'BIOTINOIL TRIPEPTIDO-1', 'MP00193', 'biotinoyl tripeptide-1', 1)
        """
    ]),
        (16, 'mp_formula_bridge — bisabolol, boron nitride, terpenos, tocoferil', [
        """INSERT OR IGNORE INTO mp_formula_bridge
           (formula_material_id, formula_material_nombre, bodega_material_id, notas, activo)
           VALUES
           ('MPBISALI01', 'BISABOLOL', 'MPBSBL01', 'bisabolol — bodega usa codigo MPBSBL01 (no MP00XXX)', 1),
           ('MPBORNISO01', 'NITRURO DE BORO', 'MPBNIT01', 'boron nitride — bodega usa codigo MPBNIT01', 1),
           ('MPTERPESO01', 'TERPENOS SOLUBLE', 'MP00176', 'terpenos solubles = centella asiatica extract', 1),
           ('MPTERSOL01', 'TERPENOS SOLUBLES', 'MP00176', 'terpenos solubles = centella asiatica extract', 1),
           ('MPTERSSO01', 'TERPENOS SOLUBLES 80-98%', 'MP00176', 'terpenos solubles = centella asiatica extract', 1),
           ('MPTOCOFE01', 'SODIUM TOCOFERIL FOSFATO', 'MP00078', 'sodium tocopheryl phosphate = vitamina E', 1)
        """
    ]),
    (18, "fix proveedor: En quimica → Inchemical en maestro_mps y proveedores", [
        """UPDATE maestro_mps
           SET proveedor = 'Inchemical'
           WHERE LOWER(TRIM(proveedor)) IN ('en química','en quimica','enquimica','en química ','en quimica ')
              OR LOWER(TRIM(proveedor)) LIKE '%en q%mica%'""",
        """INSERT OR IGNORE INTO proveedores (nombre, contacto, email, telefono,
               categoria, condiciones_pago, nit, direccion, num_cuenta,
               tipo_cuenta, banco, concepto_compra, fecha_creacion)
           VALUES ('Inchemical','','','','mp','30 dias','','','','','',
                   'Materias Primas', datetime('now'))""",
    ]),
    (17, "sku_producto_map: codigos cortos de calendario de produccion", [
        """INSERT OR REPLACE INTO sku_producto_map (sku, producto_nombre, activo) VALUES
        ('NPHA',   'SUERO EXFOLIANTE NOVA PHA',          1),
        ('RECN',   'SUERO ANTIOXIDANTE RENOVA C10',       1),
        ('AZHC',   'AZ HIBRID CLEAR',                     1),
        ('B3BHA',  'EMULSION HIDRATANTE  B3+BHA',         1),
        ('SVITC',  'SUERO DE VITAMINA C+ FORMULA NUEVA',  1),
        ('SBHA',   'Suero Exfoliante BHA 2%',             1),
        ('LBHA',   'LIMPIADOR FACIAL BHA 2%',             1),
        ('CUREA',  'CREMA DE UREA',                       1)"""
    ]),
    (19, "sku_producto_map fallback - SBHA y SKUs calendario garantizados en prod", [
        """INSERT OR REPLACE INTO sku_producto_map (sku, producto_nombre, activo) VALUES
        ('SBHA',   'Suero Exfoliante BHA 2%',             1),
        ('NPHA',   'SUERO EXFOLIANTE NOVA PHA',            1),
        ('RECN',   'SUERO ANTIOXIDANTE RENOVA C10',         1),
        ('AZHC',   'AZ HIBRID CLEAR',                       1),
        ('B3BHA',  'EMULSION HIDRATANTE  B3+BHA',           1),
        ('SVITC',  'SUERO DE VITAMINA C+ FORMULA NUEVA',    1),
        ('LBHA',   'LIMPIADOR FACIAL BHA 2%',               1),
        ('CUREA',  'CREMA DE UREA',                         1)"""
    ]),
    (20, "solicitudes_compra: influencer_id FK + marketing_influencers: banco/cuenta/cedula", [
        """ALTER TABLE solicitudes_compra ADD COLUMN influencer_id INTEGER REFERENCES marketing_influencers(id)""",
        """ALTER TABLE marketing_influencers ADD COLUMN banco TEXT DEFAULT ''""",
        """ALTER TABLE marketing_influencers ADD COLUMN cuenta_bancaria TEXT DEFAULT ''""",
        """ALTER TABLE marketing_influencers ADD COLUMN cedula_nit TEXT DEFAULT ''""",
        """ALTER TABLE marketing_influencers ADD COLUMN tipo_cuenta TEXT DEFAULT 'Ahorros'""",
    ]),
    (21, "marketing_influencers: importar perfiles desde solicitudes_compra (beneficiario + datos bancarios)", [
        """WITH parsed AS (
            SELECT DISTINCT
                CASE WHEN observaciones LIKE '%BENEFICIARIO: %'
                     THEN TRIM(SUBSTR(observaciones,
                          INSTR(observaciones, 'BENEFICIARIO: ') + 14,
                          CASE WHEN INSTR(SUBSTR(observaciones, INSTR(observaciones, 'BENEFICIARIO: ') + 14), ' | ') > 0
                               THEN INSTR(SUBSTR(observaciones, INSTR(observaciones, 'BENEFICIARIO: ') + 14), ' | ') - 1
                               ELSE 200 END))
                     ELSE TRIM(solicitante) END AS nombre,
                CASE WHEN observaciones LIKE '%BANCO: %'
                     THEN TRIM(SUBSTR(observaciones,
                          INSTR(observaciones, 'BANCO: ') + 7,
                          CASE WHEN INSTR(SUBSTR(observaciones, INSTR(observaciones, 'BANCO: ') + 7), ' | ') > 0
                               THEN INSTR(SUBSTR(observaciones, INSTR(observaciones, 'BANCO: ') + 7), ' | ') - 1
                               ELSE 100 END))
                     ELSE '' END AS banco,
                CASE WHEN observaciones LIKE '%CUENTA/CEL: %'
                     THEN TRIM(SUBSTR(observaciones,
                          INSTR(observaciones, 'CUENTA/CEL: ') + 12,
                          CASE WHEN INSTR(SUBSTR(observaciones, INSTR(observaciones, 'CUENTA/CEL: ') + 12), ' | ') > 0
                               THEN INSTR(SUBSTR(observaciones, INSTR(observaciones, 'CUENTA/CEL: ') + 12), ' | ') - 1
                               ELSE 50 END))
                     ELSE '' END AS cuenta,
                CASE WHEN observaciones LIKE '%CED/NIT: %'
                     THEN TRIM(SUBSTR(observaciones,
                          INSTR(observaciones, 'CED/NIT: ') + 9,
                          CASE WHEN INSTR(SUBSTR(observaciones, INSTR(observaciones, 'CED/NIT: ') + 9), ' | ') > 0
                               THEN INSTR(SUBSTR(observaciones, INSTR(observaciones, 'CED/NIT: ') + 9), ' | ') - 1
                               ELSE 30 END))
                     ELSE '' END AS cedula
            FROM solicitudes_compra
            WHERE categoria = 'Influencer/Marketing Digital'
              AND TRIM(COALESCE(solicitante, '')) != ''
        )
        INSERT INTO marketing_influencers
            (nombre, estado, red_social, banco, cuenta_bancaria, cedula_nit, tipo_cuenta, notas, fecha_registro)
        SELECT nombre, 'Activo', 'Instagram', banco, cuenta, cedula,
               'Ahorros', 'Importado desde Compras', datetime('now')
        FROM parsed
        WHERE TRIM(COALESCE(nombre, '')) != ''
          AND nombre NOT IN (SELECT nombre FROM marketing_influencers)""",
        """UPDATE solicitudes_compra
           SET influencer_id = (
               SELECT mi.id FROM marketing_influencers mi
               WHERE LOWER(TRIM(mi.nombre)) = LOWER(TRIM(solicitudes_compra.solicitante))
               LIMIT 1
           )
           WHERE categoria = 'Influencer/Marketing Digital'
             AND influencer_id IS NULL""",
    ]),
    (22, "add bank columns idempotent - retry mig20 sin FK inline", [
        # Se omite REFERENCES para evitar error de SQLite en algunos contextos
        # duplicate column name es ignorado por el runner (idempotente)
        """ALTER TABLE solicitudes_compra ADD COLUMN influencer_id INTEGER""",
        """ALTER TABLE marketing_influencers ADD COLUMN banco TEXT DEFAULT ''""",
        """ALTER TABLE marketing_influencers ADD COLUMN cuenta_bancaria TEXT DEFAULT ''""",
        """ALTER TABLE marketing_influencers ADD COLUMN cedula_nit TEXT DEFAULT ''""",
        """ALTER TABLE marketing_influencers ADD COLUMN tipo_cuenta TEXT DEFAULT 'Ahorros'""",
    ]),
    (23, "pagos_influencers: tabla dedicada + 17 perfiles Excel + 138 pagos historicos", [
        """CREATE TABLE IF NOT EXISTS pagos_influencers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    influencer_id INTEGER,
    influencer_nombre TEXT NOT NULL,
    valor INTEGER NOT NULL DEFAULT 0,
    fecha TEXT NOT NULL,
    estado TEXT DEFAULT 'Pendiente',
    concepto TEXT DEFAULT '',
    numero_oc TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
)""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('Camila Correal', 'Davivienda', '488409582803', 'Davivienda', '1094970527', 'Armenia', 'Activo')""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('Oscar Mauricio Sierra', 'Bancolombia', '91222512412', 'ahorros', '1098811687', 'Medellin', 'Activo')""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('Laura.lafauxx', 'Nequi', '3018100699', 'Nequi', '1006191486', 'Cali', 'Activo')""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('María Paula patiño', 'Bancolombia', '91269451691', 'ahorros', '1089380322', 'Pereira', 'Activo')""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('Silvana', 'Nequi', '3196289872', 'Nequi', '100085192', 'Chia', 'Activo')""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('daisy lopez', 'Bancolombia', '0-1924759573', 'ahorros', '21562825', 'Medellin', 'Activo')""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('Maria Camila Soto', 'Nequi', '3114902203', 'Nequi', '1192785380', 'Cali', 'Activo')""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('sara agudelo', 'Bancolombia', '91295083323', 'ahorros', '1035443463', 'Copacabana', 'Activo')""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('Val sierra', 'Bancolombia', '71656729613', 'ahorros', '1144064620', 'Cali', 'Activo')""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('Camila Camico Torres', 'Bancolombia', '10000007331', 'ahorros', '5002105211', 'Bogota', 'Activo')""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('Ana Sofía', 'Bancolombia', '00-554321887', 'ahorros', '10052805594', 'Bucaramanga', 'Activo')""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('David Calao', 'Bancolombia', '23618267318', 'ahorros', '23618267318', 'Medellin', 'Activo')""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('Valentina Hernandez', 'Bancolombia', '91208276790', 'ahorros', '1020837694', 'Bogota', 'Activo')""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('Juanito rebel', 'Bancolombia', '00-700011693', 'ahorros', '901861007', 'Medellin', 'Activo')""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('Jhon stiven', 'Bancolombia', '51400051295', 'ahorros', '1006035092', 'Cali', 'Activo')""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('Valeria osorno', 'Bancolombia', '55300000468', 'ahorros', '1035441588', 'Copacabana', 'Activo')""",
        """INSERT OR IGNORE INTO marketing_influencers (nombre, banco, cuenta_bancaria, tipo_cuenta, cedula_nit, notas, estado) VALUES ('Samira Kure', 'Nequi', '3053336443', 'Nequi', '1007914341', 'Cali', 'Activo')""",
        """UPDATE marketing_influencers SET banco='Davivienda', cuenta_bancaria='488409582803', tipo_cuenta='Davivienda', cedula_nit='1094970527' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Camila Correal')) AND (banco IS NULL OR banco='')""",
        """UPDATE marketing_influencers SET banco='Bancolombia', cuenta_bancaria='91222512412', tipo_cuenta='ahorros', cedula_nit='1098811687' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Oscar Mauricio Sierra')) AND (banco IS NULL OR banco='')""",
        """UPDATE marketing_influencers SET banco='Nequi', cuenta_bancaria='3018100699', tipo_cuenta='Nequi', cedula_nit='1006191486' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Laura.lafauxx')) AND (banco IS NULL OR banco='')""",
        """UPDATE marketing_influencers SET banco='Bancolombia', cuenta_bancaria='91269451691', tipo_cuenta='ahorros', cedula_nit='1089380322' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('María Paula patiño')) AND (banco IS NULL OR banco='')""",
        """UPDATE marketing_influencers SET banco='Nequi', cuenta_bancaria='3196289872', tipo_cuenta='Nequi', cedula_nit='100085192' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Silvana')) AND (banco IS NULL OR banco='')""",
        """UPDATE marketing_influencers SET banco='Bancolombia', cuenta_bancaria='0-1924759573', tipo_cuenta='ahorros', cedula_nit='21562825' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('daisy lopez')) AND (banco IS NULL OR banco='')""",
        """UPDATE marketing_influencers SET banco='Nequi', cuenta_bancaria='3114902203', tipo_cuenta='Nequi', cedula_nit='1192785380' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Maria Camila Soto')) AND (banco IS NULL OR banco='')""",
        """UPDATE marketing_influencers SET banco='Bancolombia', cuenta_bancaria='91295083323', tipo_cuenta='ahorros', cedula_nit='1035443463' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('sara agudelo')) AND (banco IS NULL OR banco='')""",
        """UPDATE marketing_influencers SET banco='Bancolombia', cuenta_bancaria='71656729613', tipo_cuenta='ahorros', cedula_nit='1144064620' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Val sierra')) AND (banco IS NULL OR banco='')""",
        """UPDATE marketing_influencers SET banco='Bancolombia', cuenta_bancaria='10000007331', tipo_cuenta='ahorros', cedula_nit='5002105211' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Camila Camico Torres')) AND (banco IS NULL OR banco='')""",
        """UPDATE marketing_influencers SET banco='Bancolombia', cuenta_bancaria='00-554321887', tipo_cuenta='ahorros', cedula_nit='10052805594' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Ana Sofía')) AND (banco IS NULL OR banco='')""",
        """UPDATE marketing_influencers SET banco='Bancolombia', cuenta_bancaria='23618267318', tipo_cuenta='ahorros', cedula_nit='23618267318' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('David Calao')) AND (banco IS NULL OR banco='')""",
        """UPDATE marketing_influencers SET banco='Bancolombia', cuenta_bancaria='91208276790', tipo_cuenta='ahorros', cedula_nit='1020837694' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Valentina Hernandez')) AND (banco IS NULL OR banco='')""",
        """UPDATE marketing_influencers SET banco='Bancolombia', cuenta_bancaria='00-700011693', tipo_cuenta='ahorros', cedula_nit='901861007' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Juanito rebel')) AND (banco IS NULL OR banco='')""",
        """UPDATE marketing_influencers SET banco='Bancolombia', cuenta_bancaria='51400051295', tipo_cuenta='ahorros', cedula_nit='1006035092' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Jhon stiven')) AND (banco IS NULL OR banco='')""",
        """UPDATE marketing_influencers SET banco='Bancolombia', cuenta_bancaria='55300000468', tipo_cuenta='ahorros', cedula_nit='1035441588' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Valeria osorno')) AND (banco IS NULL OR banco='')""",
        """UPDATE marketing_influencers SET banco='Nequi', cuenta_bancaria='3053336443', tipo_cuenta='Nequi', cedula_nit='1007914341' WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Samira Kure')) AND (banco IS NULL OR banco='')""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Laura.lafauxx', 230000, '2025-01-02', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Laura.lafauxx')) UNION ALL SELECT NULL, 'Laura.lafauxx', 230000, '2025-01-02', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Laura.lafauxx')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'David Calao', 200000, '2025-01-03', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('David Calao')) UNION ALL SELECT NULL, 'David Calao', 200000, '2025-01-03', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('David Calao')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Rous', 250000, '2025-01-04', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Rous')) UNION ALL SELECT NULL, 'Rous', 250000, '2025-01-04', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Rous')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Camila Correal', 300000, '2025-01-05', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Camila Correal')) UNION ALL SELECT NULL, 'Camila Correal', 300000, '2025-01-05', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Camila Correal')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'sara agudelo', 350000, '2025-01-06', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('sara agudelo')) UNION ALL SELECT NULL, 'sara agudelo', 350000, '2025-01-06', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('sara agudelo')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Maria Camila Soto', 1000000, '2025-01-07', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Maria Camila Soto')) UNION ALL SELECT NULL, 'Maria Camila Soto', 1000000, '2025-01-07', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Maria Camila Soto')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Diana Bejarano', 400000, '2025-01-08', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Diana Bejarano')) UNION ALL SELECT NULL, 'Diana Bejarano', 400000, '2025-01-08', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Diana Bejarano')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Darian Hernandez', 250000, '2025-01-09', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Darian Hernandez')) UNION ALL SELECT NULL, 'Darian Hernandez', 250000, '2025-01-09', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Darian Hernandez')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Kamila Parra', 170000, '2025-01-10', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Kamila Parra')) UNION ALL SELECT NULL, 'Kamila Parra', 170000, '2025-01-10', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Kamila Parra')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Stiven Sants', 550000, '2025-01-11', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Stiven Sants')) UNION ALL SELECT NULL, 'Stiven Sants', 550000, '2025-01-11', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Stiven Sants')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Laura Toro', 200000, '2025-01-12', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Laura Toro')) UNION ALL SELECT NULL, 'Laura Toro', 200000, '2025-01-12', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Laura Toro')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Valentina Hernandez', 280000, '2025-01-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Valentina Hernandez')) UNION ALL SELECT NULL, 'Valentina Hernandez', 280000, '2025-01-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Valentina Hernandez')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Susana Piedrahíta', 1200000, '2025-01-13', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Susana Piedrahíta')) UNION ALL SELECT NULL, 'Susana Piedrahíta', 1200000, '2025-01-13', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Susana Piedrahíta')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Silvana', 210000, '2025-01-14', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Silvana')) UNION ALL SELECT NULL, 'Silvana', 210000, '2025-01-14', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Silvana')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'María Paula patiño', 420000, '2025-01-15', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('María Paula patiño')) UNION ALL SELECT NULL, 'María Paula patiño', 420000, '2025-01-15', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('María Paula patiño')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Fabián', 400000, '2025-01-17', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Fabián')) UNION ALL SELECT NULL, 'Fabián', 400000, '2025-01-17', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Fabián')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Ana Sofía', 365000, '2025-01-18', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Ana Sofía')) UNION ALL SELECT NULL, 'Ana Sofía', 365000, '2025-01-18', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Ana Sofía')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Monssa', 250000, '2025-01-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Monssa')) UNION ALL SELECT NULL, 'Monssa', 250000, '2025-01-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Monssa')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Alessa', 600000, '2025-01-20', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Alessa')) UNION ALL SELECT NULL, 'Alessa', 600000, '2025-01-20', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Alessa')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Alejandra duque', 2500000, '2025-01-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Alejandra duque')) UNION ALL SELECT NULL, 'Alejandra duque', 2500000, '2025-01-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Alejandra duque')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'pao mendes', 290000, '2025-01-22', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('pao mendes')) UNION ALL SELECT NULL, 'pao mendes', 290000, '2025-01-22', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('pao mendes')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'daisy lopez', 650000, '2025-01-23', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('daisy lopez')) UNION ALL SELECT NULL, 'daisy lopez', 650000, '2025-01-23', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('daisy lopez')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Catalina Valbuena', 250000, '2025-01-24', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Catalina Valbuena')) UNION ALL SELECT NULL, 'Catalina Valbuena', 250000, '2025-01-24', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Catalina Valbuena')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Valentina Peña', 120000, '2025-01-25', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Valentina Peña')) UNION ALL SELECT NULL, 'Valentina Peña', 120000, '2025-01-25', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Valentina Peña')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Camila Correal', 300000, '2025-01-26', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Camila Correal')) UNION ALL SELECT NULL, 'Camila Correal', 300000, '2025-01-26', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Camila Correal')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Samira', 300000, '2025-01-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Samira')) UNION ALL SELECT NULL, 'Samira', 300000, '2025-01-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Samira')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Lorel muñoz', 250000, '2025-01-27', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Lorel muñoz')) UNION ALL SELECT NULL, 'Lorel muñoz', 250000, '2025-01-27', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Lorel muñoz')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Stiven', 250000, '2025-01-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Stiven')) UNION ALL SELECT NULL, 'Stiven', 250000, '2025-01-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Stiven')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'María José Grisales', 450000, '2025-01-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('María José Grisales')) UNION ALL SELECT NULL, 'María José Grisales', 450000, '2025-01-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('María José Grisales')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Val sierra', 2500000, '2025-01-29', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Val sierra')) UNION ALL SELECT NULL, 'Val sierra', 2500000, '2025-01-29', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Val sierra')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Luisa Maria Lopez', 1700000, '2025-01-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Luisa Maria Lopez')) UNION ALL SELECT NULL, 'Luisa Maria Lopez', 1700000, '2025-01-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Luisa Maria Lopez')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'sara agudelo', 300000, '2025-01-30', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('sara agudelo')) UNION ALL SELECT NULL, 'sara agudelo', 300000, '2025-01-30', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('sara agudelo')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Juanito', 1785000, '2025-01-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Juanito')) UNION ALL SELECT NULL, 'Juanito', 1785000, '2025-01-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Juanito')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Diana Bejarano', 400000, '2025-01-31', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Diana Bejarano')) UNION ALL SELECT NULL, 'Diana Bejarano', 400000, '2025-01-31', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Diana Bejarano')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Ana Sofía', 400000, '2025-02-02', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Ana Sofía')) UNION ALL SELECT NULL, 'Ana Sofía', 400000, '2025-02-02', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Ana Sofía')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Dani zuleta', 800000, '2025-02-04', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Dani zuleta')) UNION ALL SELECT NULL, 'Dani zuleta', 800000, '2025-02-04', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Dani zuleta')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Camila Correal', 300000, '2025-02-05', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Camila Correal')) UNION ALL SELECT NULL, 'Camila Correal', 300000, '2025-02-05', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Camila Correal')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Daniel felipe Garzon', 250000, '2025-02-06', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Daniel felipe Garzon')) UNION ALL SELECT NULL, 'Daniel felipe Garzon', 250000, '2025-02-06', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Daniel felipe Garzon')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Rous', 300000, '2025-02-07', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Rous')) UNION ALL SELECT NULL, 'Rous', 300000, '2025-02-07', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Rous')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Maria Camila Soto', 1200000, '2025-02-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Maria Camila Soto')) UNION ALL SELECT NULL, 'Maria Camila Soto', 1200000, '2025-02-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Maria Camila Soto')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Camila Correal', 600000, '2025-02-10', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Camila Correal')) UNION ALL SELECT NULL, 'Camila Correal', 600000, '2025-02-10', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Camila Correal')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Diana Bejarano', 490000, '2025-02-11', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Diana Bejarano')) UNION ALL SELECT NULL, 'Diana Bejarano', 490000, '2025-02-11', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Diana Bejarano')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Laura.lafauxx', 230000, '2025-02-12', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Laura.lafauxx')) UNION ALL SELECT NULL, 'Laura.lafauxx', 230000, '2025-02-12', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Laura.lafauxx')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Valeria osorno', 450000, '2025-02-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Valeria osorno')) UNION ALL SELECT NULL, 'Valeria osorno', 450000, '2025-02-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Valeria osorno')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Joha tovar', 150000, '2025-02-13', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Joha tovar')) UNION ALL SELECT NULL, 'Joha tovar', 150000, '2025-02-13', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Joha tovar')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'María Paula patiño', 280000, '2025-02-14', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('María Paula patiño')) UNION ALL SELECT NULL, 'María Paula patiño', 280000, '2025-02-14', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('María Paula patiño')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Stiven', 250000, '2025-02-15', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Stiven')) UNION ALL SELECT NULL, 'Stiven', 250000, '2025-02-15', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Stiven')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Juliana Brito', 320000, '2025-02-16', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Juliana Brito')) UNION ALL SELECT NULL, 'Juliana Brito', 320000, '2025-02-16', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Juliana Brito')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'sara agudelo', 400000, '2025-02-17', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('sara agudelo')) UNION ALL SELECT NULL, 'sara agudelo', 400000, '2025-02-17', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('sara agudelo')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'David Calao', 200000, '2025-02-18', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('David Calao')) UNION ALL SELECT NULL, 'David Calao', 200000, '2025-02-18', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('David Calao')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Juan daniel ocampo', 280000, '2025-02-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Juan daniel ocampo')) UNION ALL SELECT NULL, 'Juan daniel ocampo', 280000, '2025-02-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Juan daniel ocampo')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Monssa', 250000, '2025-02-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Monssa')) UNION ALL SELECT NULL, 'Monssa', 250000, '2025-02-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Monssa')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Frank trejos', 1500000, '2025-02-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Frank trejos')) UNION ALL SELECT NULL, 'Frank trejos', 1500000, '2025-02-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Frank trejos')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'tatiana g', 250000, '2025-02-19', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('tatiana g')) UNION ALL SELECT NULL, 'tatiana g', 250000, '2025-02-19', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('tatiana g')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Catalina Choachi', 420000, '2025-02-20', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Catalina Choachi')) UNION ALL SELECT NULL, 'Catalina Choachi', 420000, '2025-02-20', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Catalina Choachi')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Val sierra', 2500000, '2025-02-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Val sierra')) UNION ALL SELECT NULL, 'Val sierra', 2500000, '2025-02-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Val sierra')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Alejandra duque', 2500000, '2025-02-21', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Alejandra duque')) UNION ALL SELECT NULL, 'Alejandra duque', 2500000, '2025-02-21', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Alejandra duque')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Juliana Giraldo', 800000, '2025-02-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Juliana Giraldo')) UNION ALL SELECT NULL, 'Juliana Giraldo', 800000, '2025-02-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Juliana Giraldo')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Silvana', 380000, '2025-02-22', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Silvana')) UNION ALL SELECT NULL, 'Silvana', 380000, '2025-02-22', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Silvana')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Diana Bejarano', 490000, '2025-02-23', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Diana Bejarano')) UNION ALL SELECT NULL, 'Diana Bejarano', 490000, '2025-02-23', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Diana Bejarano')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'sara agudelo', 400000, '2025-02-25', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('sara agudelo')) UNION ALL SELECT NULL, 'sara agudelo', 400000, '2025-02-25', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('sara agudelo')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Diana Bejarano', 490000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Diana Bejarano')) UNION ALL SELECT NULL, 'Diana Bejarano', 490000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Diana Bejarano')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Camila Correal', 300000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Camila Correal')) UNION ALL SELECT NULL, 'Camila Correal', 300000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Camila Correal')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Valentina Hernandez', 350000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Valentina Hernandez')) UNION ALL SELECT NULL, 'Valentina Hernandez', 350000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Valentina Hernandez')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'daisy lopez', 650000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('daisy lopez')) UNION ALL SELECT NULL, 'daisy lopez', 650000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('daisy lopez')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Juanito rebel', 1844500, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Juanito rebel')) UNION ALL SELECT NULL, 'Juanito rebel', 1844500, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Juanito rebel')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'María Paula patiño', 700000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('María Paula patiño')) UNION ALL SELECT NULL, 'María Paula patiño', 700000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('María Paula patiño')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'LINNA PATRICIA ANGE', 400000, '2025-03-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('LINNA PATRICIA ANGE')) UNION ALL SELECT NULL, 'LINNA PATRICIA ANGE', 400000, '2025-03-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('LINNA PATRICIA ANGE')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Maria Camila Soto', 1000000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Maria Camila Soto')) UNION ALL SELECT NULL, 'Maria Camila Soto', 1000000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Maria Camila Soto')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'David Calao', 200000, '2025-03-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('David Calao')) UNION ALL SELECT NULL, 'David Calao', 200000, '2025-03-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('David Calao')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'tatiana g', 250000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('tatiana g')) UNION ALL SELECT NULL, 'tatiana g', 250000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('tatiana g')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Stiven', 250000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Stiven')) UNION ALL SELECT NULL, 'Stiven', 250000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Stiven')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Valeria osorno', 450000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Valeria osorno')) UNION ALL SELECT NULL, 'Valeria osorno', 450000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Valeria osorno')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Lorel muñoz', 300000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Lorel muñoz')) UNION ALL SELECT NULL, 'Lorel muñoz', 300000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Lorel muñoz')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'sara agudelo', 350000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('sara agudelo')) UNION ALL SELECT NULL, 'sara agudelo', 350000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('sara agudelo')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Yisel Vienna', 600000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Yisel Vienna')) UNION ALL SELECT NULL, 'Yisel Vienna', 600000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Yisel Vienna')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Laura.lafauxx', 230000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Laura.lafauxx')) UNION ALL SELECT NULL, 'Laura.lafauxx', 230000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Laura.lafauxx')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Diana bejarano', 1000000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Diana bejarano')) UNION ALL SELECT NULL, 'Diana bejarano', 1000000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Diana bejarano')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Val sierra', 2500000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Val sierra')) UNION ALL SELECT NULL, 'Val sierra', 2500000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Val sierra')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Adriana Morelo', 300000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Adriana Morelo')) UNION ALL SELECT NULL, 'Adriana Morelo', 300000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Adriana Morelo')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Emmanuel luzan García', 360000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Emmanuel luzan García')) UNION ALL SELECT NULL, 'Emmanuel luzan García', 360000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Emmanuel luzan García')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Monssa', 250000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Monssa')) UNION ALL SELECT NULL, 'Monssa', 250000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Monssa')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Dani zuleta', 800000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Dani zuleta')) UNION ALL SELECT NULL, 'Dani zuleta', 800000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Dani zuleta')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Silvana', 210000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Silvana')) UNION ALL SELECT NULL, 'Silvana', 210000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Silvana')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Alejandra duque', 2500000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Alejandra duque')) UNION ALL SELECT NULL, 'Alejandra duque', 2500000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Alejandra duque')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Juanito rebel', 2765000, '2025-03-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Juanito rebel')) UNION ALL SELECT NULL, 'Juanito rebel', 2765000, '2025-03-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Juanito rebel')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Ana Sofía', 530000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Ana Sofía')) UNION ALL SELECT NULL, 'Ana Sofía', 530000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Ana Sofía')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Diana Bejarano', 490000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Diana Bejarano')) UNION ALL SELECT NULL, 'Diana Bejarano', 490000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Diana Bejarano')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Camila Correal', 300000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Camila Correal')) UNION ALL SELECT NULL, 'Camila Correal', 300000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Camila Correal')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'David Calao', 400000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('David Calao')) UNION ALL SELECT NULL, 'David Calao', 400000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('David Calao')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Maria akasa', 5236000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Maria akasa')) UNION ALL SELECT NULL, 'Maria akasa', 5236000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Maria akasa')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'sara agudelo', 450000, '2025-03-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('sara agudelo')) UNION ALL SELECT NULL, 'sara agudelo', 450000, '2025-03-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('sara agudelo')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Rous', 350000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Rous')) UNION ALL SELECT NULL, 'Rous', 350000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Rous')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'David Calao', 200000, '2025-04-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('David Calao')) UNION ALL SELECT NULL, 'David Calao', 200000, '2025-04-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('David Calao')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Oscar Mauricio Sierra', 200000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Oscar Mauricio Sierra')) UNION ALL SELECT NULL, 'Oscar Mauricio Sierra', 200000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Oscar Mauricio Sierra')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Laura.lafauxx', 230000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Laura.lafauxx')) UNION ALL SELECT NULL, 'Laura.lafauxx', 230000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Laura.lafauxx')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Camila Correal', 300000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Camila Correal')) UNION ALL SELECT NULL, 'Camila Correal', 300000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Camila Correal')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'María Paula patiño', 700000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('María Paula patiño')) UNION ALL SELECT NULL, 'María Paula patiño', 700000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('María Paula patiño')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Silvana', 210000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Silvana')) UNION ALL SELECT NULL, 'Silvana', 210000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Silvana')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'daisy lopez', 650000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('daisy lopez')) UNION ALL SELECT NULL, 'daisy lopez', 650000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('daisy lopez')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Maria Camila Soto', 1000000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Maria Camila Soto')) UNION ALL SELECT NULL, 'Maria Camila Soto', 1000000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Maria Camila Soto')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Sara', 250000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Sara')) UNION ALL SELECT NULL, 'Sara', 250000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Sara')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'sara agudelo', 400000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('sara agudelo')) UNION ALL SELECT NULL, 'sara agudelo', 400000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('sara agudelo')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Stiven', 300000, '2025-04-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Stiven')) UNION ALL SELECT NULL, 'Stiven', 300000, '2025-04-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Stiven')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Val sierra', 2500000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Val sierra')) UNION ALL SELECT NULL, 'Val sierra', 2500000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Val sierra')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Stiven sants', 500000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Stiven sants')) UNION ALL SELECT NULL, 'Stiven sants', 500000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Stiven sants')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Camila Camico Torres', 450000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Camila Camico Torres')) UNION ALL SELECT NULL, 'Camila Camico Torres', 450000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Camila Camico Torres')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Ana Sofía', 530000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Ana Sofía')) UNION ALL SELECT NULL, 'Ana Sofía', 530000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Ana Sofía')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Luisa Alejandra hoyos', 160000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Luisa Alejandra hoyos')) UNION ALL SELECT NULL, 'Luisa Alejandra hoyos', 160000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Luisa Alejandra hoyos')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Valeria osorno', 450000, '2025-04-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Valeria osorno')) UNION ALL SELECT NULL, 'Valeria osorno', 450000, '2025-04-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Valeria osorno')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Samira Kure', 400000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Samira Kure')) UNION ALL SELECT NULL, 'Samira Kure', 400000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Samira Kure')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Angie Aguilar', 380000, '2025-04-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Angie Aguilar')) UNION ALL SELECT NULL, 'Angie Aguilar', 380000, '2025-04-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Angie Aguilar')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Leidy Diana Hidalgo Perea', 420000, '2025-04-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Leidy Diana Hidalgo Perea')) UNION ALL SELECT NULL, 'Leidy Diana Hidalgo Perea', 420000, '2025-04-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Leidy Diana Hidalgo Perea')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Laura moscote guerra', 330000, '2025-04-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Laura moscote guerra')) UNION ALL SELECT NULL, 'Laura moscote guerra', 330000, '2025-04-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Laura moscote guerra')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Camila Correal', 300000, '2025-04-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Camila Correal')) UNION ALL SELECT NULL, 'Camila Correal', 300000, '2025-04-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Camila Correal')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Dani zuleta', 800000, '2025-04-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Dani zuleta')) UNION ALL SELECT NULL, 'Dani zuleta', 800000, '2025-04-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Dani zuleta')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'David Calao', 200000, '2025-04-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('David Calao')) UNION ALL SELECT NULL, 'David Calao', 200000, '2025-04-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('David Calao')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Lorel muñoz', 300000, '2025-04-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Lorel muñoz')) UNION ALL SELECT NULL, 'Lorel muñoz', 300000, '2025-04-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Lorel muñoz')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'sara agudelo', 400000, '2025-04-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('sara agudelo')) UNION ALL SELECT NULL, 'sara agudelo', 400000, '2025-04-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('sara agudelo')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Kamila Parra', 200000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Kamila Parra')) UNION ALL SELECT NULL, 'Kamila Parra', 200000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Kamila Parra')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Alejandra bejarano', 490000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Alejandra bejarano')) UNION ALL SELECT NULL, 'Alejandra bejarano', 490000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Alejandra bejarano')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Camila Correal', 300000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Camila Correal')) UNION ALL SELECT NULL, 'Camila Correal', 300000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Camila Correal')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Luisa Maria Lopez', 750000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Luisa Maria Lopez')) UNION ALL SELECT NULL, 'Luisa Maria Lopez', 750000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Luisa Maria Lopez')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Maria Camila Soto', 1000000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Maria Camila Soto')) UNION ALL SELECT NULL, 'Maria Camila Soto', 1000000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Maria Camila Soto')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'María Paula patiño', 420000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('María Paula patiño')) UNION ALL SELECT NULL, 'María Paula patiño', 420000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('María Paula patiño')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Resolana', 1000000, '2025-05-01', 'Pagada', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Resolana')) UNION ALL SELECT NULL, 'Resolana', 1000000, '2025-05-01', 'Pagada', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Resolana')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Camila Camico Torres', 450000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Camila Camico Torres')) UNION ALL SELECT NULL, 'Camila Camico Torres', 450000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Camila Camico Torres')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Val sierra', 2500000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Val sierra')) UNION ALL SELECT NULL, 'Val sierra', 2500000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Val sierra')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'sara agudelo', 400000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('sara agudelo')) UNION ALL SELECT NULL, 'sara agudelo', 400000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('sara agudelo')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Juliana Chaparro', 200000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Juliana Chaparro')) UNION ALL SELECT NULL, 'Juliana Chaparro', 200000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Juliana Chaparro')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Silvana', 210000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Silvana')) UNION ALL SELECT NULL, 'Silvana', 210000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Silvana')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Ana Sofía', 365000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Ana Sofía')) UNION ALL SELECT NULL, 'Ana Sofía', 365000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Ana Sofía')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Angie Paola Samboni', 250000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Angie Paola Samboni')) UNION ALL SELECT NULL, 'Angie Paola Samboni', 250000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Angie Paola Samboni')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Camila Correal', 300000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Camila Correal')) UNION ALL SELECT NULL, 'Camila Correal', 300000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Camila Correal')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Stiven', 300000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Stiven')) UNION ALL SELECT NULL, 'Stiven', 300000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Stiven')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Lorel muñoz', 300000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Lorel muñoz')) UNION ALL SELECT NULL, 'Lorel muñoz', 300000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Lorel muñoz')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Alejandra duque', 2500000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Alejandra duque')) UNION ALL SELECT NULL, 'Alejandra duque', 2500000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Alejandra duque')))""",
        """INSERT OR IGNORE INTO pagos_influencers (influencer_id, influencer_nombre, valor, fecha, estado, concepto) SELECT mi.id, 'Valeria osorno', 450000, '2025-05-01', 'Pendiente', 'Pago histórico importado' FROM marketing_influencers mi WHERE TRIM(LOWER(mi.nombre))=TRIM(LOWER('Valeria osorno')) UNION ALL SELECT NULL, 'Valeria osorno', 450000, '2025-05-01', 'Pendiente', 'Pago histórico importado' WHERE NOT EXISTS (SELECT 1 FROM marketing_influencers WHERE TRIM(LOWER(nombre))=TRIM(LOWER('Valeria osorno')))""",
    ]),
    (24, "marketing_influencers: motivo_baja + fecha_publicacion en pagos_influencers", [
        """ALTER TABLE marketing_influencers ADD COLUMN motivo_baja TEXT DEFAULT ''""",
        """ALTER TABLE marketing_influencers ADD COLUMN fecha_baja TEXT DEFAULT ''""",
        """ALTER TABLE pagos_influencers ADD COLUMN fecha_publicacion TEXT DEFAULT ''""",
        """ALTER TABLE pagos_influencers ADD COLUMN entregable TEXT DEFAULT ''""",
    ]),
    (25, "users_passwords: tabla para self-service password change (lazy fallback a env)", [
        """CREATE TABLE IF NOT EXISTS users_passwords (
            username      TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            changed_at    TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
            changed_by    TEXT NOT NULL DEFAULT ''
        )""",
    ]),
    (26, "backup_log: registro de backups automaticos para auditoria y locking multi-worker", [
        """CREATE TABLE IF NOT EXISTS backup_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at   TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
            completed_at TEXT,
            file_path    TEXT,
            size_bytes   INTEGER,
            status       TEXT NOT NULL DEFAULT 'running',
            error        TEXT,
            triggered_by TEXT NOT NULL DEFAULT 'auto'
        )""",
        "CREATE INDEX IF NOT EXISTS idx_backup_log_started ON backup_log(started_at DESC)",
    ]),
    (27, "maestro_mps: tipo_material para distinguir MP / Envase Primario / Envase Secundario / Empaque", [
        # Categoría unificada para inventario cíclico de E&E (envase + empaque).
        # Valores válidos:
        #   'MP'                — Materia prima (default)
        #   'Envase Primario'   — Envase que toca el producto (frasco, tubo)
        #   'Envase Secundario' — Cajas, displays
        #   'Empaque'           — Etiquetas, insertos, sellos, blisters
        # Backfill: si tipo legacy contiene "envase" o "empaque", se infiere.
        # Para todo lo demás queda 'MP'.
        "ALTER TABLE maestro_mps ADD COLUMN tipo_material TEXT DEFAULT 'MP'",
        # Backfill heurístico — palabra-clave en el campo 'tipo' o 'nombre_inci'
        """UPDATE maestro_mps SET tipo_material='Envase Primario'
           WHERE LOWER(COALESCE(tipo,'')) LIKE '%envase%primario%'
              OR LOWER(COALESCE(tipo,'')) LIKE '%frasco%'
              OR LOWER(COALESCE(nombre_comercial,'')) LIKE '%frasco%'
              OR LOWER(COALESCE(nombre_comercial,'')) LIKE '%tubo%'""",
        """UPDATE maestro_mps SET tipo_material='Envase Secundario'
           WHERE LOWER(COALESCE(tipo,'')) LIKE '%envase%secundario%'
              OR LOWER(COALESCE(tipo,'')) LIKE '%caja%'
              OR LOWER(COALESCE(nombre_comercial,'')) LIKE '%caja%'""",
        """UPDATE maestro_mps SET tipo_material='Empaque'
           WHERE LOWER(COALESCE(tipo,'')) LIKE '%empaque%'
              OR LOWER(COALESCE(tipo,'')) LIKE '%etiqueta%'
              OR LOWER(COALESCE(tipo,'')) LIKE '%inserto%'
              OR LOWER(COALESCE(nombre_comercial,'')) LIKE '%etiqueta%'
              OR LOWER(COALESCE(nombre_comercial,'')) LIKE '%inserto%'""",
        # Índice para búsquedas filtradas por tipo
        "CREATE INDEX IF NOT EXISTS idx_maestro_mps_tipo_material ON maestro_mps(tipo_material)",
    ]),
    (28, "compras: pagos_oc (auditoria pagos parciales) + centro_costos en OC", [
        # Tabla de pagos: 1 OC puede tener N pagos (parciales). Permite auditar
        # cada movimiento de dinero por separado en lugar de sobrescribir el
        # estado de la OC.
        """CREATE TABLE IF NOT EXISTS pagos_oc (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_oc            TEXT NOT NULL,
            monto                REAL NOT NULL,
            medio                TEXT DEFAULT 'Transferencia',
            fecha_pago           TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
            registrado_por       TEXT NOT NULL DEFAULT '',
            numero_factura_proveedor TEXT DEFAULT '',
            comprobante_imagen   TEXT DEFAULT '',
            observaciones        TEXT DEFAULT ''
        )""",
        "CREATE INDEX IF NOT EXISTS idx_pagos_oc_numero ON pagos_oc(numero_oc)",
        # Constraint suave para detectar facturas duplicadas (3-way matching).
        # WHERE clause: SQLite respeta NULL como distinto, pero queremos también
        # tratar '' como "no factura aún" — entonces el índice unique solo aplica
        # cuando hay factura real registrada.
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_pagos_oc_factura_unique ON pagos_oc(numero_factura_proveedor) WHERE numero_factura_proveedor != ''",
        # Centro de costos para reportes por proyecto/empresa.
        "ALTER TABLE ordenes_compra ADD COLUMN centro_costos TEXT DEFAULT 'general'",
    ]),
    (29, "compras: cotizaciones (3 proveedores) — workflow opcional pre-OC", [
        # Workflow opcional para items de alto valor que ameriten comparar 3
        # cotizaciones antes de generar OC. La OC final referencia la
        # cotización ganadora vía numero_oc.
        """CREATE TABLE IF NOT EXISTS cotizaciones (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            ronda_id        TEXT NOT NULL,
            proveedor       TEXT NOT NULL,
            fecha_solicitud TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
            fecha_recibida  TEXT,
            valor_total     REAL DEFAULT 0,
            condiciones     TEXT DEFAULT '',
            descripcion     TEXT DEFAULT '',
            tiempo_entrega_dias INTEGER DEFAULT 0,
            ganadora        INTEGER DEFAULT 0,
            numero_oc       TEXT DEFAULT '',
            archivo         TEXT DEFAULT '',
            creado_por      TEXT NOT NULL DEFAULT '',
            estado          TEXT NOT NULL DEFAULT 'Pendiente'
        )""",
        "CREATE INDEX IF NOT EXISTS idx_cotizaciones_ronda ON cotizaciones(ronda_id)",
        "CREATE INDEX IF NOT EXISTS idx_cotizaciones_proveedor ON cotizaciones(proveedor)",
        "CREATE INDEX IF NOT EXISTS idx_cotizaciones_oc ON cotizaciones(numero_oc)",
    ]),
    (30, "compras: comprobantes_pago (CE) con numeracion secuencial + retenciones", [
        # Cada pago a proveedor/influencer genera 1 comprobante con numeración
        # CE-YYYY-NNNN secuencial por año. Vinculado a pagos_oc.
        """CREATE TABLE IF NOT EXISTS comprobantes_pago (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_ce       TEXT UNIQUE NOT NULL,
            anio            INTEGER NOT NULL,
            fecha_emision   TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
            pago_oc_id      INTEGER,
            numero_oc       TEXT,
            beneficiario_nombre  TEXT NOT NULL,
            beneficiario_cedula  TEXT,
            beneficiario_banco   TEXT,
            beneficiario_cuenta  TEXT,
            beneficiario_tipo_cta TEXT,
            beneficiario_ciudad  TEXT,
            subtotal        REAL NOT NULL DEFAULT 0,
            iva             REAL DEFAULT 0,
            iva_pct         REAL DEFAULT 0,
            retefuente      REAL DEFAULT 0,
            retefuente_pct  REAL DEFAULT 0,
            retica          REAL DEFAULT 0,
            retica_pct      REAL DEFAULT 0,
            total_pagado    REAL NOT NULL,
            medio_pago      TEXT,
            observaciones   TEXT,
            pagado_por      TEXT,
            empresa         TEXT DEFAULT 'Espagiria',
            pdf_archivo     TEXT,
            FOREIGN KEY (pago_oc_id) REFERENCES pagos_oc(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_comprobantes_pago_oc ON comprobantes_pago(numero_oc)",
        "CREATE INDEX IF NOT EXISTS idx_comprobantes_pago_fecha ON comprobantes_pago(fecha_emision DESC)",
        """CREATE TABLE IF NOT EXISTS comprobantes_seq (
            anio    INTEGER PRIMARY KEY,
            ultimo  INTEGER NOT NULL DEFAULT 0
        )""",
    ]),
    (31, "marketing_influencers: ciudad + instagram + tipo (usados por sync Excel)", [
        # Estas columnas las usa el script de sync_influencers_excel y el
        # importador de pagos. Si no existen, los SELECT con LEFT JOIN tiran
        # OperationalError 'no such column' y se rompe /compras Influencers.
        """ALTER TABLE marketing_influencers ADD COLUMN ciudad TEXT DEFAULT ''""",
        """ALTER TABLE marketing_influencers ADD COLUMN instagram TEXT DEFAULT ''""",
        """ALTER TABLE marketing_influencers ADD COLUMN tipo TEXT DEFAULT ''""",
    ]),
    (32, "atribucion: discount_code en influencers + discount_codes en shopify orders", [
        # Discount code asignado al influencer. Cuando un cliente usa este code
        # en Shopify, la venta se atribuye automáticamente al influencer.
        # Convención: prefijo 'ANIMUS_' + slug del nombre, ej: ANIMUS_LAURA10.
        """ALTER TABLE marketing_influencers ADD COLUMN discount_code TEXT DEFAULT ''""",
        # Lista (JSON) de discount codes usados en cada orden de Shopify.
        # Necesario para hacer el matching → ventas atribuidas por influencer.
        """ALTER TABLE animus_shopify_orders ADD COLUMN discount_codes TEXT DEFAULT ''""",
        # Subtotal pre-descuento (para calcular ROI real de la campaña descuento).
        """ALTER TABLE animus_shopify_orders ADD COLUMN subtotal REAL DEFAULT 0""",
        """ALTER TABLE animus_shopify_orders ADD COLUMN total_descuentos REAL DEFAULT 0""",
        # Index para búsquedas rápidas por código (LIKE %CODE%)
        """CREATE INDEX IF NOT EXISTS idx_shopify_discount_codes ON animus_shopify_orders(discount_codes)""",
        """CREATE INDEX IF NOT EXISTS idx_influencer_discount_code ON marketing_influencers(discount_code)""",
    ]),
    (33, "kanban contenido + feedback agentes + push alerts", [
        # Kanban estados: Brief → Produccion → Pendiente → Publicado → Performance
        # `estado` ya existe en marketing_contenido; los nuevos campos enriquecen.
        """ALTER TABLE marketing_contenido ADD COLUMN sku_objetivo TEXT DEFAULT ''""",
        """ALTER TABLE marketing_contenido ADD COLUMN mensaje_principal TEXT DEFAULT ''""",
        """ALTER TABLE marketing_contenido ADD COLUMN fecha_programada TEXT DEFAULT ''""",
        """CREATE INDEX IF NOT EXISTS idx_contenido_estado ON marketing_contenido(estado)""",
        """CREATE INDEX IF NOT EXISTS idx_contenido_fecha_prog ON marketing_contenido(fecha_programada)""",
        # Feedback loop sobre agentes IA: el usuario marca cada ejecución como
        # útil / no útil / ejecutado. Permite medir tasa de acierto y mejorar
        # los prompts con el tiempo.
        """CREATE TABLE IF NOT EXISTS marketing_agentes_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id        INTEGER NOT NULL,
            agente        TEXT NOT NULL,
            feedback      TEXT NOT NULL CHECK(feedback IN ('util','no_util','ejecutado')),
            comentario    TEXT,
            usuario       TEXT,
            fecha         TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(log_id) REFERENCES marketing_agentes_log(id)
        )""",
        """CREATE INDEX IF NOT EXISTS idx_feedback_log ON marketing_agentes_feedback(log_id)""",
        """CREATE INDEX IF NOT EXISTS idx_feedback_agente ON marketing_agentes_feedback(agente)""",
        # Push alerts: log de alertas disparadas para no enviar duplicadas.
        # Cada combinación (tipo_alerta + clave_unica) se envía solo 1 vez por día.
        """CREATE TABLE IF NOT EXISTS marketing_push_alerts_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo          TEXT NOT NULL,
            clave_unica   TEXT NOT NULL,
            destinatario  TEXT NOT NULL,
            asunto        TEXT,
            cuerpo_resumen TEXT,
            severidad     TEXT DEFAULT 'medio',
            fecha         TEXT DEFAULT (datetime('now')),
            UNIQUE(tipo, clave_unica, destinatario, fecha)
        )""",
        """CREATE INDEX IF NOT EXISTS idx_push_alerts_fecha ON marketing_push_alerts_log(fecha DESC)""",
    ]),
    (34, "animus: caja menor (Daniela) + inventario ciclico vs Shopify", [
        # Caja menor: Daniela recibe efectivo de ventas contraentrega y
        # registra ingresos/egresos del fondo de la tienda. Saldo
        # acumulado = sum(ingresos) - sum(egresos).
        """CREATE TABLE IF NOT EXISTS animus_caja_menor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha           TEXT NOT NULL,
            tipo            TEXT NOT NULL CHECK(tipo IN ('ingreso','egreso')),
            concepto        TEXT NOT NULL,
            monto           REAL NOT NULL,
            metodo          TEXT DEFAULT 'efectivo',
            referencia      TEXT DEFAULT '',
            observaciones   TEXT DEFAULT '',
            registrado_por  TEXT,
            fecha_creacion  TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE INDEX IF NOT EXISTS idx_caja_fecha ON animus_caja_menor(fecha DESC)""",
        """CREATE INDEX IF NOT EXISTS idx_caja_tipo ON animus_caja_menor(tipo)""",
        # Inventario ciclico: Daniela cuenta fisico vs lo que dice
        # Shopify (snapshot al momento del conteo) y registra explicacion
        # de la diferencia (rotura, devolucion no registrada, robo, etc).
        """CREATE TABLE IF NOT EXISTS animus_conteos_ciclicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku                TEXT NOT NULL,
            producto_nombre    TEXT,
            fecha_conteo       TEXT NOT NULL,
            cantidad_shopify   INTEGER DEFAULT 0,
            cantidad_fisica    INTEGER NOT NULL,
            diferencia         INTEGER NOT NULL,
            explicacion        TEXT,
            registrado_por     TEXT,
            fecha_creacion     TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE INDEX IF NOT EXISTS idx_conteo_sku ON animus_conteos_ciclicos(sku)""",
        """CREATE INDEX IF NOT EXISTS idx_conteo_fecha ON animus_conteos_ciclicos(fecha_conteo DESC)""",
    ]),
    (35, "marketing_influencers: ciclo_pago (Mensual/Bimensual/Trimestral/Unico) para alerta automatica 'Toca pagar'", [
        """ALTER TABLE marketing_influencers ADD COLUMN ciclo_pago TEXT DEFAULT 'Mensual'""",
    ]),
    (36, "tecnica: versionado historico de formulas + tablas comunicacion (tareas RACI, chat, actas, quejas)", [
        # Versionado de formulas: snapshot completo en cada cambio
        """CREATE TABLE IF NOT EXISTS formulas_versiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            formula_id      INTEGER NOT NULL,
            version_num     INTEGER NOT NULL,
            snapshot_json   TEXT NOT NULL,
            motivo_cambio   TEXT DEFAULT '',
            creado_por      TEXT,
            fecha_creacion  TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE INDEX IF NOT EXISTS idx_form_ver_id ON formulas_versiones(formula_id, version_num DESC)""",

        # Sistema de comunicacion interna - tareas con RACI
        """CREATE TABLE IF NOT EXISTS tareas_internas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo            TEXT NOT NULL,
            descripcion       TEXT DEFAULT '',
            estado            TEXT DEFAULT 'Asignada' CHECK(estado IN ('Asignada','EnProceso','Bloqueada','Hecha','Cancelada')),
            prioridad         TEXT DEFAULT 'Media' CHECK(prioridad IN ('Alta','Media','Baja')),
            area              TEXT DEFAULT '',
            origen            TEXT DEFAULT 'manual',
            origen_ref        TEXT DEFAULT '',
            fecha_compromiso  TEXT,
            fecha_creacion    TEXT DEFAULT (datetime('now')),
            fecha_completada  TEXT,
            creado_por        TEXT,
            reincidente_de_id INTEGER,
            notas_avance      TEXT DEFAULT ''
        )""",
        """CREATE INDEX IF NOT EXISTS idx_tareas_estado ON tareas_internas(estado, fecha_compromiso)""",
        """CREATE INDEX IF NOT EXISTS idx_tareas_origen ON tareas_internas(origen, origen_ref)""",

        # Tabla RACI: relacion N:M entre tareas y usuarios con rol
        """CREATE TABLE IF NOT EXISTS tareas_raci (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarea_id        INTEGER NOT NULL,
            usuario         TEXT NOT NULL,
            rol             TEXT NOT NULL CHECK(rol IN ('R','A','C','I')),
            asignado_por    TEXT,
            fecha_asignacion TEXT DEFAULT (datetime('now')),
            UNIQUE(tarea_id, usuario, rol)
        )""",
        """CREATE INDEX IF NOT EXISTS idx_raci_usuario ON tareas_raci(usuario, rol)""",
        """CREATE INDEX IF NOT EXISTS idx_raci_tarea ON tareas_raci(tarea_id)""",

        # Chat interno entre usuarios
        """CREATE TABLE IF NOT EXISTS mensajes_internos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            de_usuario          TEXT NOT NULL,
            a_usuario           TEXT NOT NULL,
            asunto              TEXT DEFAULT '',
            mensaje             TEXT NOT NULL,
            fecha               TEXT DEFAULT (datetime('now')),
            leido_at            TEXT,
            relacionado_tarea_id INTEGER
        )""",
        """CREATE INDEX IF NOT EXISTS idx_msj_a ON mensajes_internos(a_usuario, leido_at)""",
        """CREATE INDEX IF NOT EXISTS idx_msj_de ON mensajes_internos(de_usuario, fecha DESC)""",

        # Actas de comites semanales (parser Gemini)
        """CREATE TABLE IF NOT EXISTS comites_actas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha               TEXT NOT NULL,
            plataforma          TEXT DEFAULT 'Google Meet',
            titulo              TEXT DEFAULT 'Comite Semanal Espagiria',
            asistentes_json     TEXT DEFAULT '[]',
            transcripcion       TEXT DEFAULT '',
            transcripcion_url   TEXT DEFAULT '',
            parseada            INTEGER DEFAULT 0,
            tareas_creadas      INTEGER DEFAULT 0,
            registrado_por      TEXT,
            fecha_creacion      TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE INDEX IF NOT EXISTS idx_actas_fecha ON comites_actas(fecha DESC)""",

        # Quejas / problemas reportados (input para chat IA secundario)
        """CREATE TABLE IF NOT EXISTS quejas_internas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            de_usuario          TEXT NOT NULL,
            contexto            TEXT NOT NULL,
            severidad_ia        TEXT,
            analisis_ia         TEXT,
            accion_sugerida_ia  TEXT,
            escalada_a          TEXT,
            estado              TEXT DEFAULT 'Pendiente' CHECK(estado IN ('Pendiente','Analizada','Escalada','Resuelta','Descartada')),
            fecha               TEXT DEFAULT (datetime('now')),
            fecha_resolucion    TEXT,
            resolucion          TEXT
        )""",
        """CREATE INDEX IF NOT EXISTS idx_quejas_estado ON quejas_internas(estado, fecha DESC)""",
    ]),
    (37, "shopify_orders: flag flujo_synced para sync automatico de ingresos a flujo_ingresos", [
        """ALTER TABLE animus_shopify_orders ADD COLUMN flujo_synced INTEGER DEFAULT 0""",
        """ALTER TABLE animus_shopify_orders ADD COLUMN flujo_ingreso_id INTEGER""",
        """CREATE INDEX IF NOT EXISTS idx_shopify_flujo_pending ON animus_shopify_orders(flujo_synced) WHERE flujo_synced=0""",
    ]),
    (43, "precio_historico_mp: memoria de precios por MP+proveedor — detectar aumentos y sugerir nuevos proveedores", [
        # Cada vez que Catalina (o el sistema) registra un precio para un MP
        # — sea en una SOL editada, una OC creada, o una recepcion — se inserta
        # una fila aqui. Asi tenemos serie temporal por MP+proveedor.
        """CREATE TABLE IF NOT EXISTS precio_historico_mp (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_mp       TEXT NOT NULL,
            nombre_mp       TEXT DEFAULT '',
            proveedor       TEXT DEFAULT '',
            precio_unit_g   REAL NOT NULL,
            cantidad_g      REAL DEFAULT 0,
            valor_total     REAL DEFAULT 0,
            fecha           TEXT NOT NULL DEFAULT (datetime('now')),
            fuente          TEXT DEFAULT 'manual'
                CHECK(fuente IN ('manual','sol_editada','oc_creada','oc_pagada','recepcion','import')),
            sol_numero      TEXT DEFAULT '',
            oc_numero       TEXT DEFAULT '',
            usuario         TEXT DEFAULT '',
            observaciones   TEXT DEFAULT ''
        )""",
        """CREATE INDEX IF NOT EXISTS idx_phist_mp_fecha ON precio_historico_mp(codigo_mp, fecha DESC)""",
        """CREATE INDEX IF NOT EXISTS idx_phist_proveedor ON precio_historico_mp(proveedor)""",
        """CREATE INDEX IF NOT EXISTS idx_phist_fecha ON precio_historico_mp(fecha DESC)""",

        # Asegurar que solicitudes_compra_items tenga campos editables consistentes.
        # cantidad_g y valor_estimado ya existen; agregamos precio_unit_g para
        # claridad (catalina edita precio por gramo, no valor total).
        """ALTER TABLE solicitudes_compra_items ADD COLUMN precio_unit_g REAL DEFAULT 0""",
        """ALTER TABLE solicitudes_compra_items ADD COLUMN proveedor_sugerido TEXT DEFAULT ''""",
        """ALTER TABLE solicitudes_compra_items ADD COLUMN actualizado_at TEXT""",
        """ALTER TABLE solicitudes_compra_items ADD COLUMN actualizado_por TEXT DEFAULT ''""",
    ]),
    (45, "produccion_programada: columna origen para distinguir manual de auto-sync calendar (fix dedup en Planificacion Estrategica)", [
        # Bug 29-abr-2026: Planificacion Estrategica leia 2 fuentes (Google
        # Calendar + tabla produccion_programada) y mi sync auto que copio
        # eventos del calendar a la tabla causo duplicados (cada produccion
        # aparecia 2 veces — ej. "GEL HIDRATANTE (50kg)" y "GEL HIDRATANTE
        # (35kg)" mismo dia, ambos del mismo evento de calendar).
        # Solucion: marcar las filas auto-sync con origen='calendar' y
        # filtrarlas en planificacion_estrategica. Las manuales: 'manual'.
        """ALTER TABLE produccion_programada ADD COLUMN origen TEXT DEFAULT 'manual'""",
        # Backfill: filas insertadas por mi sync tienen "[auto-sync calendar]"
        # al inicio de observaciones — marcarlas como origen='calendar'.
        """UPDATE produccion_programada
              SET origen='calendar'
            WHERE COALESCE(observaciones,'') LIKE '[auto-sync calendar]%'""",
    ]),
    (44, "formula_headers: imagen_url para mostrar foto del producto en checklist Pre-Produccion", [
        # Sebastian (28-abr-2026): el modal del checklist muestra foto del
        # producto. Esta migracion ya corrio en produccion con 2 columnas.
        # NO MODIFICAR — las migraciones son inmutables una vez deployadas.
        # Para columnas adicionales de Shopify ver migracion #46.
        """ALTER TABLE formula_headers ADD COLUMN imagen_url TEXT DEFAULT ''""",
        """ALTER TABLE formula_headers ADD COLUMN imagen_actualizada_at TEXT""",
    ]),
    (46, "formula_headers: metadata Shopify completa (SKU + descripcion + precio + peso + galeria)", [
        # Bug 29-abr-2026: agregue estas columnas dentro de la #44 retroactivamente.
        # Como #44 ya estaba marcada como aplicada en prod, las nuevas no se crearon
        # y el endpoint imagen-shopify-sync fallaba con 500 "no such column".
        # Se separan en #46 para que corran en el proximo boot.
        # Idempotente: ALTER ADD con duplicate column name se ignora silenciosa.
        """ALTER TABLE formula_headers ADD COLUMN shopify_id TEXT DEFAULT ''""",
        """ALTER TABLE formula_headers ADD COLUMN shopify_handle TEXT DEFAULT ''""",
        """ALTER TABLE formula_headers ADD COLUMN descripcion_html TEXT DEFAULT ''""",
        """ALTER TABLE formula_headers ADD COLUMN descripcion_plain TEXT DEFAULT ''""",
        """ALTER TABLE formula_headers ADD COLUMN sku_principal TEXT DEFAULT ''""",
        """ALTER TABLE formula_headers ADD COLUMN precio_venta REAL DEFAULT 0""",
        """ALTER TABLE formula_headers ADD COLUMN peso_g REAL DEFAULT 0""",
        """ALTER TABLE formula_headers ADD COLUMN imagenes_extra_json TEXT DEFAULT '[]'""",
        """ALTER TABLE formula_headers ADD COLUMN shopify_synced_at TEXT""",
    ]),
    (42, "produccion_checklist: pre-flight checklist por produccion programada (MPs + envases + etiquetas + serigrafia/tampografia)", [
        # Master de plantillas: cada producto puede tener items default
        # configurables. Si un producto no tiene plantilla, usa la generica.
        """CREATE TABLE IF NOT EXISTS checklist_plantillas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_nombre   TEXT,
            item_tipo         TEXT NOT NULL CHECK(item_tipo IN
                ('mp','envase_primario','envase_secundario','tapa',
                 'etiqueta_frontal','etiqueta_posterior','etiqueta_lateral',
                 'serigrafia','tampografia','caja_exterior','instructivo',
                 'estuche','sello','otro')),
            descripcion       TEXT NOT NULL,
            proveedor_default TEXT DEFAULT '',
            dias_anticipacion INTEGER DEFAULT 30,
            obligatorio       INTEGER DEFAULT 1,
            orden             INTEGER DEFAULT 0,
            creado_por        TEXT,
            fecha_creacion    TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE INDEX IF NOT EXISTS idx_checklist_plant_prod ON checklist_plantillas(producto_nombre)""",

        # Items concretos del checklist por cada produccion programada.
        # Se generan automaticamente cuando una produccion entra al calendario.
        """CREATE TABLE IF NOT EXISTS produccion_checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produccion_id      INTEGER,
            produccion_ref     TEXT,
            producto_nombre    TEXT NOT NULL,
            fecha_planeada     TEXT NOT NULL,
            cantidad_kg        REAL DEFAULT 0,
            item_tipo          TEXT NOT NULL,
            descripcion        TEXT NOT NULL,
            cantidad_requerida REAL DEFAULT 0,
            unidad             TEXT DEFAULT 'g',
            codigo_mp          TEXT DEFAULT '',
            stock_actual       REAL DEFAULT 0,
            deficit            REAL DEFAULT 0,
            estado             TEXT DEFAULT 'pendiente'
                CHECK(estado IN ('pendiente','verificado_ok','solicitado',
                                 'en_transito','recibido','listo','no_aplica')),
            proveedor          TEXT DEFAULT '',
            solicitud_numero   TEXT DEFAULT '',
            oc_numero          TEXT DEFAULT '',
            fecha_solicitud    TEXT,
            fecha_eta          TEXT,
            fecha_recibido     TEXT,
            responsable        TEXT DEFAULT '',
            observaciones      TEXT DEFAULT '',
            dias_anticipacion  INTEGER DEFAULT 30,
            actualizado_at     TEXT DEFAULT (datetime('now')),
            actualizado_por    TEXT,
            fecha_creacion     TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE INDEX IF NOT EXISTS idx_pchk_produccion ON produccion_checklist(produccion_id, item_tipo)""",
        """CREATE INDEX IF NOT EXISTS idx_pchk_fecha ON produccion_checklist(fecha_planeada, estado)""",
        """CREATE INDEX IF NOT EXISTS idx_pchk_estado ON produccion_checklist(estado)""",

        # Plantilla generica default — si producto no tiene plantilla propia
        # se usan estos items basicos.
        """INSERT INTO checklist_plantillas (producto_nombre, item_tipo, descripcion, dias_anticipacion, orden, obligatorio) VALUES
            ('', 'envase_primario',  'Envase primario (frasco/contenedor)', 30, 1, 1),
            ('', 'tapa',              'Tapa o sistema dosificador',          30, 2, 1),
            ('', 'etiqueta_frontal',  'Etiqueta frontal',                    25, 3, 1),
            ('', 'etiqueta_posterior','Etiqueta posterior con info legal',   25, 4, 1),
            ('', 'caja_exterior',     'Caja exterior individual',            20, 5, 0),
            ('', 'serigrafia',        'Serigrafia en envase si aplica',      30, 6, 0),
            ('', 'tampografia',       'Tampografia en tapa si aplica',       30, 7, 0)
        """,
    ]),
    (41, "animus_conteos_ciclicos: flag aplicado + movimiento_id_ajuste para Gap 8 (cierre conteo Daniela)", [
        """ALTER TABLE animus_conteos_ciclicos ADD COLUMN aplicado INTEGER DEFAULT 0""",
        """ALTER TABLE animus_conteos_ciclicos ADD COLUMN movimiento_id_ajuste INTEGER""",
    ]),
    (39, "calidad: tablas avanzadas — coa_resultados, especificaciones_mp, estabilidades, capa_acciones", [
        # Especificaciones MP: limites por parametro para validar CoA
        """CREATE TABLE IF NOT EXISTS especificaciones_mp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_mp        TEXT NOT NULL,
            parametro        TEXT NOT NULL,
            unidad           TEXT DEFAULT '',
            valor_min        REAL,
            valor_max        REAL,
            metodo_ensayo    TEXT DEFAULT '',
            obligatorio      INTEGER DEFAULT 1,
            tipo             TEXT DEFAULT 'fisicoquimico',
            farmacopea_ref   TEXT DEFAULT '',
            creado_por       TEXT,
            fecha_creacion   TEXT DEFAULT (datetime('now')),
            UNIQUE(codigo_mp, parametro)
        )""",
        """CREATE INDEX IF NOT EXISTS idx_espec_mp ON especificaciones_mp(codigo_mp)""",

        # CoA resultados: por lote ingresado, parametro analizado, resultado
        """CREATE TABLE IF NOT EXISTS coa_resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lote             TEXT NOT NULL,
            codigo_mp        TEXT NOT NULL,
            material_nombre  TEXT,
            parametro        TEXT NOT NULL,
            unidad           TEXT DEFAULT '',
            valor_obtenido   TEXT NOT NULL,
            valor_min_spec   REAL,
            valor_max_spec   REAL,
            conforme         INTEGER DEFAULT 1,
            metodo_ensayo    TEXT DEFAULT '',
            analista         TEXT,
            fecha_analisis   TEXT DEFAULT (date('now')),
            equipo_id        INTEGER,
            observaciones    TEXT DEFAULT '',
            decision         TEXT DEFAULT 'Aprobado',
            creado_en        TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE INDEX IF NOT EXISTS idx_coa_lote ON coa_resultados(lote)""",
        """CREATE INDEX IF NOT EXISTS idx_coa_mp ON coa_resultados(codigo_mp)""",
        """CREATE INDEX IF NOT EXISTS idx_coa_conforme ON coa_resultados(conforme)""",

        # Estabilidades: estudios T0/T1/T3/T6/T12 con condiciones
        """CREATE TABLE IF NOT EXISTS estabilidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto         TEXT NOT NULL,
            lote_piloto      TEXT NOT NULL,
            condicion        TEXT NOT NULL,
            tiempo_dias      INTEGER NOT NULL,
            tiempo_etiqueta  TEXT,
            fecha_inicio     TEXT NOT NULL,
            fecha_evaluacion TEXT,
            parametros_json  TEXT DEFAULT '{}',
            conforme         INTEGER DEFAULT 1,
            observaciones    TEXT DEFAULT '',
            analista         TEXT,
            estado           TEXT DEFAULT 'Programado'
                CHECK(estado IN ('Programado','Iniciado','En curso','Concluido','Suspendido')),
            creado_en        TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE INDEX IF NOT EXISTS idx_estab_producto ON estabilidades(producto, lote_piloto)""",

        # CAPA workflow real para no_conformidades
        """CREATE TABLE IF NOT EXISTS capa_acciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nc_id            INTEGER NOT NULL,
            tipo             TEXT NOT NULL CHECK(tipo IN ('correctiva','preventiva','contencion')),
            descripcion      TEXT NOT NULL,
            responsable      TEXT,
            fecha_compromiso TEXT,
            fecha_ejecucion  TEXT,
            evidencia_url    TEXT DEFAULT '',
            efectiva         INTEGER,
            verificada_por   TEXT,
            fecha_verificacion TEXT,
            estado           TEXT DEFAULT 'Pendiente'
                CHECK(estado IN ('Pendiente','EnEjecucion','Ejecutada','Verificada','Cerrada','NoEfectiva')),
            creado_en        TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE INDEX IF NOT EXISTS idx_capa_nc ON capa_acciones(nc_id)""",

        # Auditorias internas + a proveedores
        """CREATE TABLE IF NOT EXISTS auditorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo             TEXT NOT NULL CHECK(tipo IN ('Interna','Externa','Proveedor','Cliente')),
            ente_auditado    TEXT NOT NULL,
            fecha_planeada   TEXT,
            fecha_ejecutada  TEXT,
            auditor          TEXT,
            alcance          TEXT DEFAULT '',
            hallazgos_count  INTEGER DEFAULT 0,
            no_conformes    INTEGER DEFAULT 0,
            estado           TEXT DEFAULT 'Planeada',
            informe_url      TEXT DEFAULT '',
            creado_en        TEXT DEFAULT (datetime('now'))
        )""",
    ]),
    (38, "tecnica documentos_sgd: campos de revision periodica + vinculo con producciones", [
        # documentos_sgd ya tiene fecha_revision; agregamos:
        # frecuencia_revision_meses (cada cuantos meses se revisa el SOP)
        # fecha_proxima_revision (calculada)
        # responsable_revision (quien revisa)
        """ALTER TABLE documentos_sgd ADD COLUMN frecuencia_revision_meses INTEGER DEFAULT 12""",
        """ALTER TABLE documentos_sgd ADD COLUMN fecha_proxima_revision TEXT DEFAULT ''""",
        """ALTER TABLE documentos_sgd ADD COLUMN responsable_revision TEXT DEFAULT ''""",
        # producciones puede referenciar SOP usado para trazabilidad BPM
        """ALTER TABLE producciones ADD COLUMN sop_referencia TEXT DEFAULT ''""",
        """ALTER TABLE producciones ADD COLUMN sop_version TEXT DEFAULT ''""",
        # Backfill: para SGDs sin fecha_proxima, calcularla desde fecha_emision + 12 meses
        """UPDATE documentos_sgd
            SET fecha_proxima_revision = date(fecha_emision, '+12 months')
            WHERE COALESCE(fecha_proxima_revision,'') = ''
              AND COALESCE(fecha_emision,'') != ''""",
    ]),
    (48, "RH ampliado: documentos + eventos detallados (incapacidad/accidente/licencias) + llamados atencion + compromisos mejora", [
        # Sebastian (29-abr-2026): "termina de montar recursos humanos".
        # Tabla 'empleados' ya existe. Agregamos:
        # 1) Documentos del empleado (contrato, hoja vida, examenes, etc)
        # 2) Eventos RH detallados (incapacidad comun/laboral, accidentes,
        #    licencias maternidad/paternidad/luto, vacaciones, etc)
        #    con calculo legal Colombia (Ley 100, Ley 776)
        # 3) Llamados de atencion (verbal/escrito/suspension) - transversal,
        #    cualquier jefe puede registrarlos en cualquier area
        # 4) Compromisos de mejora (auto-creados por llamados con
        #    plan de reinduccion / capacitacion correctiva)

        """CREATE TABLE IF NOT EXISTS empleados_documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
              -- contrato | hoja_vida | examen_medico_ingreso |
              -- examen_medico_periodico | examen_medico_egreso |
              -- afiliacion_eps | afiliacion_arl | afiliacion_afp |
              -- afiliacion_caja | cedula | rut | foto |
              -- certificado_estudios | certificado_laboral_anterior |
              -- libreta_militar | otro
            nombre TEXT DEFAULT '',
            archivo_url TEXT DEFAULT '',  -- ruta al archivo o URL
            archivo_data TEXT DEFAULT '',  -- base64 si es chico
            mime_type TEXT DEFAULT '',
            fecha_emision TEXT,
            fecha_vencimiento TEXT,
            observaciones TEXT DEFAULT '',
            cargado_por TEXT DEFAULT '',
            fecha_carga TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE INDEX IF NOT EXISTS idx_empdoc_empleado ON empleados_documentos(empleado_id, tipo)""",
        """CREATE INDEX IF NOT EXISTS idx_empdoc_venc ON empleados_documentos(fecha_vencimiento)""",

        """CREATE TABLE IF NOT EXISTS rh_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
              -- incapacidad_comun | incapacidad_laboral | accidente_trabajo |
              -- licencia_maternidad | licencia_paternidad | licencia_luto |
              -- licencia_no_remunerada | licencia_calamidad |
              -- vacaciones | permiso_remunerado |
              -- llamado_atencion_verbal | llamado_atencion_escrito |
              -- suspension | felicitacion | reinduccion | otro
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT,
            dias INTEGER DEFAULT 0,
            descripcion TEXT DEFAULT '',
            -- Para incapacidades / accidentes:
            diagnostico TEXT DEFAULT '',
            cie10 TEXT DEFAULT '',  -- codigo diagnostico
            entidad_emisora TEXT DEFAULT '',  -- EPS / ARL / hospital
            origen TEXT DEFAULT '',  -- comun | laboral
            -- Para llamados de atencion:
            motivo TEXT DEFAULT '',
            severidad TEXT DEFAULT '',  -- leve | grave | muy_grave
            jefe_id INTEGER,  -- empleado que registra el llamado
            jefe_nombre TEXT DEFAULT '',
            area TEXT DEFAULT '',
            -- Calculo legal de pago:
            salario_diario_referencia REAL DEFAULT 0,
            pago_empleador REAL DEFAULT 0,
            pago_eps REAL DEFAULT 0,
            pago_arl REAL DEFAULT 0,
            descuento_nomina REAL DEFAULT 0,
            calculo_detalle_json TEXT DEFAULT '[]',
            -- Documentos / soportes:
            documento_url TEXT DEFAULT '',
            -- Estado:
            estado TEXT DEFAULT 'registrada'
              CHECK(estado IN ('registrada','aprobada','rechazada','cerrada','cancelada')),
            aprobado_por TEXT DEFAULT '',
            fecha_aprobacion TEXT,
            observaciones_cierre TEXT DEFAULT '',
            -- Sync con tesoreria/nomina:
            nomina_registro_id INTEGER,  -- FK a nomina_registros si aplica
            sincronizado_tesoreria INTEGER DEFAULT 0,
            -- Meta:
            registrado_por TEXT DEFAULT '',
            fecha_registro TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE INDEX IF NOT EXISTS idx_rheventos_empleado ON rh_eventos(empleado_id, fecha_inicio DESC)""",
        """CREATE INDEX IF NOT EXISTS idx_rheventos_tipo ON rh_eventos(tipo, estado)""",
        """CREATE INDEX IF NOT EXISTS idx_rheventos_estado ON rh_eventos(estado)""",

        """CREATE TABLE IF NOT EXISTS rh_compromisos_mejora (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL,
            evento_origen_id INTEGER,  -- FK rh_eventos (llamado de atencion)
            titulo TEXT NOT NULL,
            descripcion TEXT DEFAULT '',
            tipo TEXT DEFAULT 'reinduccion',
              -- reinduccion | capacitacion_correctiva | seguimiento_disciplinario
            plan_accion TEXT DEFAULT '',
            fecha_compromiso TEXT NOT NULL,  -- fecha de creacion
            fecha_objetivo TEXT,             -- fecha limite cumplimiento
            estado TEXT DEFAULT 'pendiente'
              CHECK(estado IN ('pendiente','en_progreso','completado','vencido','cancelado')),
            video_url TEXT DEFAULT '',  -- link a video IA de reinduccion
            evidencia_url TEXT DEFAULT '',
            firma_empleado TEXT DEFAULT '',  -- nombre o aceptacion
            fecha_firma_empleado TEXT,
            verificado_por TEXT DEFAULT '',
            fecha_verificacion TEXT,
            jefe_responsable TEXT DEFAULT '',
            observaciones TEXT DEFAULT '',
            creado_por TEXT DEFAULT '',
            fecha_creacion TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE INDEX IF NOT EXISTS idx_compmejora_empleado ON rh_compromisos_mejora(empleado_id, estado)""",
        """CREATE INDEX IF NOT EXISTS idx_compmejora_evento ON rh_compromisos_mejora(evento_origen_id)""",
    ]),
    (49, "chat interno EOS — threads, messages, presence (Fase 1 WhatsApp-style)", [
        # Sebastian (29-abr-2026): "compromisos y chat desaparezca como esta y
        # se convierta en algo como un lateral chat estilo whatsapp donde
        # tu nombre arriba, las personas conectadas, asignar tareas, etc."
        # Fase 1: chat 1-a-1 + grupos + broadcast + presencia online.
        # Las tareas/compromisos se asignan via /tareas-operativas existente
        # (mensaje tipo='tarea' linkea a tarea_operativa_id).

        # 1) Threads (conversaciones): 1-a-1, grupo, broadcast
        """CREATE TABLE IF NOT EXISTS chat_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL CHECK(tipo IN ('directo','grupo','broadcast')),
            nombre TEXT DEFAULT '',
            creado_por TEXT NOT NULL,
            creado_en TEXT DEFAULT (datetime('now')),
            ultimo_mensaje_id INTEGER,
            ultimo_mensaje_en TEXT,
            ultimo_mensaje_preview TEXT DEFAULT '',
            activo INTEGER DEFAULT 1
        )""",
        """CREATE INDEX IF NOT EXISTS idx_threads_actividad ON chat_threads(activo, ultimo_mensaje_en DESC)""",

        # 2) Members: quien participa de cada thread
        """CREATE TABLE IF NOT EXISTS chat_thread_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            rol TEXT DEFAULT 'miembro',
            silenciado INTEGER DEFAULT 0,
            ultimo_leido_id INTEGER DEFAULT 0,
            agregado_en TEXT DEFAULT (datetime('now')),
            UNIQUE(thread_id, username)
        )""",
        """CREATE INDEX IF NOT EXISTS idx_members_user ON chat_thread_members(username)""",
        """CREATE INDEX IF NOT EXISTS idx_members_thread ON chat_thread_members(thread_id)""",

        # 3) Messages: el contenido
        """CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            contenido TEXT NOT NULL,
            tipo_mensaje TEXT DEFAULT 'texto'
              CHECK(tipo_mensaje IN ('texto','tarea','compromiso','archivo','imagen','sistema','llamado_atencion')),
            metadata_json TEXT DEFAULT '{}',
            tarea_operativa_id INTEGER,
            compromiso_id INTEGER,
            reply_to_id INTEGER,
            creado_en TEXT DEFAULT (datetime('now')),
            editado_en TEXT,
            eliminado INTEGER DEFAULT 0
        )""",
        """CREATE INDEX IF NOT EXISTS idx_msgs_thread ON chat_messages(thread_id, creado_en DESC)""",
        """CREATE INDEX IF NOT EXISTS idx_msgs_sender ON chat_messages(sender)""",

        # 4) Presence: heartbeat de usuarios conectados
        """CREATE TABLE IF NOT EXISTS chat_user_presence (
            username TEXT PRIMARY KEY,
            last_heartbeat TEXT,
            estado TEXT DEFAULT 'desconectado'
              CHECK(estado IN ('conectado','ausente','desconectado')),
            last_thread_visto INTEGER,
            display_name TEXT DEFAULT '',
            avatar_color TEXT DEFAULT ''
        )""",
        """CREATE INDEX IF NOT EXISTS idx_presence_estado ON chat_user_presence(estado, last_heartbeat DESC)""",
    ]),
    (47, "checklist editable + solicitudes de produccion + tareas operativas", [
        # Sebastian (29-abr-2026): el modal del checklist Pre-Produccion debe
        # tener cada item editable (dropdown de maestro_mee), cantidad
        # calculada automaticamente, y boton "Solicitar" que cree una solicitud
        # para Catalina. Catalina decide: sacar de inventario, OC al proveedor
        # o serigrafia/tampografia (genera tarea operativa para sacar envases).

        # 1) Volumen unitario por producto (para calcular unidades de envases)
        """ALTER TABLE formula_headers ADD COLUMN volumen_unitario_ml REAL DEFAULT 0""",

        # 2) Columnas en produccion_checklist
        """ALTER TABLE produccion_checklist ADD COLUMN mee_codigo_asignado TEXT DEFAULT ''""",
        """ALTER TABLE produccion_checklist ADD COLUMN decoracion_tipo TEXT DEFAULT ''""",
        """ALTER TABLE produccion_checklist ADD COLUMN cantidad_unidades REAL DEFAULT 0""",
        """ALTER TABLE produccion_checklist ADD COLUMN solicitud_produccion_id INTEGER""",

        # 3) Tabla nueva: solicitudes de produccion (queue de Catalina)
        """CREATE TABLE IF NOT EXISTS solicitudes_compra_anticipada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checklist_item_id INTEGER NOT NULL,
            produccion_id     INTEGER,
            producto_nombre   TEXT NOT NULL,
            tipo_item         TEXT NOT NULL,
            mee_codigo        TEXT DEFAULT '',
            descripcion       TEXT DEFAULT '',
            cantidad_unidades REAL DEFAULT 0,
            decoracion_tipo   TEXT DEFAULT '',
            fecha_objetivo    TEXT,
            estado            TEXT DEFAULT 'pendiente'
              CHECK(estado IN ('pendiente','decidida','completada','cancelada')),
            decision          TEXT DEFAULT '',
            decidido_por      TEXT DEFAULT '',
            fecha_decision    TEXT,
            oc_numero         TEXT DEFAULT '',
            tarea_operativa_id INTEGER,
            proveedor         TEXT DEFAULT '',
            observaciones     TEXT DEFAULT '',
            solicitado_por    TEXT DEFAULT '',
            fecha_creacion    TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE INDEX IF NOT EXISTS idx_solprod_estado ON solicitudes_compra_anticipada(estado, fecha_creacion DESC)""",
        """CREATE INDEX IF NOT EXISTS idx_solprod_producto ON solicitudes_compra_anticipada(producto_nombre)""",

        # 4) Tabla nueva: tareas operativas (para planta/operarios)
        """CREATE TABLE IF NOT EXISTS tareas_operativas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo            TEXT NOT NULL,
            descripcion       TEXT DEFAULT '',
            tipo              TEXT DEFAULT 'general',
            producto_relacionado TEXT DEFAULT '',
            mee_codigo           TEXT DEFAULT '',
            cantidad             REAL DEFAULT 0,
            asignado_a           TEXT DEFAULT '',
            fecha_objetivo       TEXT,
            estado               TEXT DEFAULT 'pendiente'
              CHECK(estado IN ('pendiente','en_progreso','completada','cancelada')),
            origen_tipo          TEXT DEFAULT 'manual',
            origen_id            INTEGER,
            creado_por           TEXT DEFAULT '',
            completado_por       TEXT DEFAULT '',
            fecha_creacion       TEXT DEFAULT (datetime('now')),
            fecha_completado     TEXT,
            observaciones_cierre TEXT DEFAULT ''
        )""",
        """CREATE INDEX IF NOT EXISTS idx_tareas_estado ON tareas_operativas(estado, fecha_objetivo)""",
        """CREATE INDEX IF NOT EXISTS idx_tareas_asignado ON tareas_operativas(asignado_a)""",
    ]),
    (50, "produccion_programada: cantidad_kg explicita (auto-derivada del calendario, no depende del JOIN con formula_headers)", [
        # Sebastian (29-abr-2026): el modal del checklist mostraba "0 kg" porque
        # el SELECT hacia 'COALESCE(pp.lotes,1) * COALESCE(fh.lote_size_kg,0)' y
        # cuando el JOIN con formula_headers fallaba (mismatch de capitalizacion
        # o espacios), lote_size_kg salia NULL → 0. Ahora persistimos el kg
        # directo en la fila al sincronizar del calendario.
        "ALTER TABLE produccion_programada ADD COLUMN cantidad_kg REAL DEFAULT 0",
    ]),
    (51, "chat: reacciones a mensajes (Fase 3 — emoji reactions)", [
        # Sebastian (29-abr-2026): Fase 3 del chat — reacciones rapidas
        # con 5 emojis. UNIQUE(message_id, username, emoji) evita duplicados.
        """CREATE TABLE IF NOT EXISTS chat_reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            emoji TEXT NOT NULL,
            creado_en TEXT DEFAULT (datetime('now')),
            UNIQUE(message_id, username, emoji)
        )""",
        """CREATE INDEX IF NOT EXISTS idx_chat_react_msg ON chat_reactions(message_id)""",
    ]),
    (52, "produccion_programada: flag inventario_descontado_at (idempotencia descuento)", [
        # Sebastian (29-abr-2026): "que todo descuente que el inventario este
        # perfecto". Bug: completar produccion solo cambiaba estado, no
        # descontaba MPs ni MEEs. Ahora descontamos al completar; este flag
        # garantiza idempotencia (si se llama 2x, no descontar 2x).
        "ALTER TABLE produccion_programada ADD COLUMN inventario_descontado_at TEXT",
    ]),
    (54, "marketing_alertas_enviadas: tracking de alertas críticas notificadas (anti-spam email)", [
        # Sebastian (29-abr-2026): cuando un agente detecta algo crítico,
        # mandamos email — pero solo UNA vez por (agente, sku, fecha). Para
        # evitar mandar el mismo aviso todos los días.
        """CREATE TABLE IF NOT EXISTS marketing_alertas_enviadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agente TEXT NOT NULL,
            sku TEXT,
            tipo_alerta TEXT,
            severidad TEXT,
            mensaje TEXT,
            destinatarios TEXT,
            fecha_envio TEXT NOT NULL DEFAULT (date('now')),
            enviado_at TEXT DEFAULT (datetime('now'))
        )""",
        # UNIQUE como índice separado (SQLite no permite expresiones en
        # UNIQUE inline pero SÍ en CREATE UNIQUE INDEX). Usamos fecha_envio
        # (date solo) para garantizar 1 alerta por día por (agente,sku,tipo).
        """CREATE UNIQUE INDEX IF NOT EXISTS uq_mkt_alerts_dia
           ON marketing_alertas_enviadas(agente, COALESCE(sku,''), COALESCE(tipo_alerta,''), fecha_envio)""",
        """CREATE INDEX IF NOT EXISTS idx_mkt_alerts_at ON marketing_alertas_enviadas(enviado_at DESC)""",
    ]),
    (53, "marketing_influencers_metrics: histórico de followers/engagement (Fase 1 marketing)", [
        # Sebastian (29-abr-2026): "que sea agencia de marketing tirando todo".
        # Captura snapshots diarios de métricas desde socialblade + Instagram
        # Graph API para mostrar tendencias, alertar caídas, y alimentar
        # decisiones del agente estrategia.
        """CREATE TABLE IF NOT EXISTS marketing_influencers_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            influencer_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            seguidores INTEGER,
            siguiendo INTEGER,
            posts_total INTEGER,
            engagement_rate REAL,
            avg_likes INTEGER,
            avg_comments INTEGER,
            rank_global INTEGER,
            grade TEXT,
            fuente TEXT NOT NULL,
            raw_json TEXT,
            creado_en TEXT DEFAULT (datetime('now')),
            UNIQUE(influencer_id, fecha, fuente)
        )""",
        """CREATE INDEX IF NOT EXISTS idx_inf_metrics_inf_fecha
           ON marketing_influencers_metrics(influencer_id, fecha DESC)""",
    ]),
    (55, "planta: catalogo de areas fisicas + operarios + asignacion en produccion (post-INVIMA)", [
        # Sebastian (30-abr-2026): INVIMA amplio el uso de salas. 4 quedaron
        # MIXTAS (prod+env), 1 solo envasado, 2 con marmita (100ml y 250ml),
        # 1 con manejo especial de alcoholes. Necesitamos asignar sala +
        # operario por fase y rotar (Mayerlin fija en dispensacion).
        """CREATE TABLE IF NOT EXISTS areas_planta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            puede_producir INTEGER NOT NULL DEFAULT 0,
            puede_envasar INTEGER NOT NULL DEFAULT 0,
            marmita_ml INTEGER,
            especial TEXT,
            estado TEXT NOT NULL DEFAULT 'libre',
            activo INTEGER NOT NULL DEFAULT 1,
            orden INTEGER DEFAULT 0,
            creado_en TEXT DEFAULT (datetime('now'))
        )""",
        # Seed con las 5 salas post-INVIMA (ver project_planta_crew_areas.md)
        """INSERT OR IGNORE INTO areas_planta
           (codigo, nombre, puede_producir, puede_envasar, marmita_ml, especial, orden) VALUES
           ('PROD1', 'Produccion 1', 1, 1, NULL, 'alcoholes', 1),
           ('ENV1',  'Envasado 1',   0, 1, NULL, NULL,        2),
           ('PROD2', 'Produccion 2', 1, 1, 100,  NULL,        3),
           ('PROD3', 'Produccion 3', 1, 1, 250,  NULL,        4),
           ('PROD4', 'Produccion 4', 1, 1, NULL, NULL,        5)""",
        """CREATE TABLE IF NOT EXISTS operarios_planta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT,
            rol_predeterminado TEXT,
            fija_en_dispensacion INTEGER NOT NULL DEFAULT 0,
            es_jefe_produccion INTEGER NOT NULL DEFAULT 0,
            activo INTEGER NOT NULL DEFAULT 1,
            creado_en TEXT DEFAULT (datetime('now'))
        )""",
        # Seed crew real abr-2026. Mayerlin fija dispensacion (regla dura).
        # Sebastian Murillo es operario (NO el CEO Sebastian Vargas).
        # Luis Enrique es jefe de produccion (no operario rotativo).
        """INSERT OR IGNORE INTO operarios_planta
           (nombre, apellido, rol_predeterminado, fija_en_dispensacion, es_jefe_produccion) VALUES
           ('Mayerlin',     'Rivera',              'dispensacion',     1, 0),
           ('Camilo',       'Garcia',              'acondicionamiento', 0, 0),
           ('Milton',       'Sanabria',            'todero',           0, 0),
           ('Sebastian',    'Murillo',             'envasado',         0, 0),
           ('Luis Enrique', 'Dorronsoro Gamboa',   'jefe',             0, 1)""",
        # Asignacion sala + operarios por fase en cada produccion programada.
        # area_id NULL al crear la produccion; se asigna despues desde el plano.
        "ALTER TABLE produccion_programada ADD COLUMN area_id INTEGER",
        "ALTER TABLE produccion_programada ADD COLUMN operario_dispensacion_id INTEGER",
        "ALTER TABLE produccion_programada ADD COLUMN operario_elaboracion_id INTEGER",
        "ALTER TABLE produccion_programada ADD COLUMN operario_envasado_id INTEGER",
        "ALTER TABLE produccion_programada ADD COLUMN operario_acondicionamiento_id INTEGER",
        "CREATE INDEX IF NOT EXISTS idx_pp_area ON produccion_programada(area_id, fecha_programada)",
    ]),
    (56, "rh: notificaciones empleados (salud, permisos, citas, enfermedades) + capacitaciones con auto-examen Claude", [
        # Sebastian (30-abr-2026): "falta modulo de notificaciones donde los
        # empleados notifiquen estado de salud, soliciten permisos, citas,
        # enfermedades... y modulo de educacion: jefe asigna videos, operario
        # ve, hace autoexamen Claude, da nota, suma a historial reinducciones".
        #
        # Tabla 1: notificaciones_empleados
        # Empleados (operarios, admin, todos) crean entradas. Tipo y estado
        # gobiernan el flujo. Adjuntos opcionales (URL imagen incapacidad,
        # cita, etc.) en adjunto_url. notificado_a: lista coma-separada de
        # usernames a quienes notificar (ej. "sebastian,luis_enrique" para
        # gerencia + jefe planta).
        """CREATE TABLE IF NOT EXISTS notificaciones_empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_username TEXT NOT NULL,
            empleado_nombre TEXT,
            tipo TEXT NOT NULL CHECK(tipo IN
                ('salud','permiso','cita_medica','enfermedad','licencia','otro')),
            asunto TEXT NOT NULL,
            descripcion TEXT,
            fecha_inicio TEXT,
            fecha_fin TEXT,
            adjunto_url TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente'
                CHECK(estado IN ('pendiente','aprobada','rechazada','vista')),
            notificado_a TEXT,
            comentario_jefe TEXT,
            resuelto_por TEXT,
            resuelto_en TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_notif_emp_user ON notificaciones_empleados(empleado_username, creado_en DESC)",
        "CREATE INDEX IF NOT EXISTS idx_notif_emp_estado ON notificaciones_empleados(estado, tipo)",
        # Tabla 2: bienestar_capacitaciones (asignacion + material)
        # OJO: usamos prefijo 'bienestar_' para no chocar con la tabla
        # 'capacitaciones' legacy de RRHH (catalogo corporativo de cursos
        # con instructor, duracion_horas, etc — concepto distinto).
        # Aqui es: jefe asigna recurso URL puntual + autoexamen Claude.
        """CREATE TABLE IF NOT EXISTS bienestar_capacitaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descripcion TEXT,
            material_tipo TEXT CHECK(material_tipo IN
                ('video','pdf','notebooklm','articulo','otro')),
            material_url TEXT,
            material_notas TEXT,
            asignado_a TEXT NOT NULL,
            asignado_por TEXT NOT NULL,
            fecha_asignacion TEXT NOT NULL DEFAULT (datetime('now')),
            fecha_limite TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente'
                CHECK(estado IN ('pendiente','en_curso','completada','reprobada','vencida')),
            nota_minima INTEGER DEFAULT 70,
            nota_obtenida INTEGER,
            intentos INTEGER DEFAULT 0,
            completada_en TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_bcapac_user ON bienestar_capacitaciones(asignado_a, estado)",
        "CREATE INDEX IF NOT EXISTS idx_bcapac_fecha ON bienestar_capacitaciones(fecha_limite)",
        # Tabla 3: bienestar_capacitaciones_intentos (cada autoexamen es 1 intento)
        # preguntas_json: array de preguntas generadas por Claude
        # respuestas_json: array de respuestas del operario
        # evaluacion_json: feedback por pregunta + nota global
        """CREATE TABLE IF NOT EXISTS bienestar_capacitaciones_intentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            capacitacion_id INTEGER NOT NULL,
            empleado_username TEXT NOT NULL,
            preguntas_json TEXT NOT NULL,
            respuestas_json TEXT,
            evaluacion_json TEXT,
            nota INTEGER,
            iniciado_en TEXT NOT NULL DEFAULT (datetime('now')),
            terminado_en TEXT,
            FOREIGN KEY (capacitacion_id) REFERENCES bienestar_capacitaciones(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_bcap_int_cap ON bienestar_capacitaciones_intentos(capacitacion_id, empleado_username)",
    ]),
    (57, "users_mfa: TOTP de 2 factores (Google Authenticator) — Sebastian 30-abr-2026", [
        """CREATE TABLE IF NOT EXISTS users_mfa (
            username           TEXT PRIMARY KEY,
            secret             TEXT NOT NULL,
            enabled            INTEGER NOT NULL DEFAULT 0,
            backup_code_hash   TEXT,
            created_at         TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
            enabled_at         TEXT,
            last_used_at       TEXT,
            disabled_at        TEXT,
            FOREIGN KEY (username) REFERENCES users_passwords(username) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_users_mfa_enabled ON users_mfa(enabled)",
    ]),
    (58, "planta: Centro de Mando — areas extra asignables (acond, bodegas) + tracking real inicio/fin + audit log", [
        # Sebastian (30-abr-2026): "incluir bodega y materia prima recuerda
        # que hay inventarios ciclicos para eso, entonces los puedes asignar
        # tambien". Y: "cuando inician y terminan asi sabemos tiempos nos
        # sirve de indicadores".
        #
        # Cambios:
        # 1. areas_planta gana columna 'tipo' (produccion / conteo_ciclico /
        #    apoyo_asignable) para distinguir uso. Default 'produccion'.
        "ALTER TABLE areas_planta ADD COLUMN tipo TEXT NOT NULL DEFAULT 'produccion'",
        # 2. Marcar las 5 salas existentes como tipo='produccion' explicito
        "UPDATE areas_planta SET tipo='produccion' WHERE codigo IN ('PROD1','PROD2','PROD3','PROD4','ENV1')",
        # 3. Agregar Acondicionamiento, Almacen MP, Almacen PT como asignables
        #    para conteos ciclicos. Tienen puede_producir=0/puede_envasar=0
        #    pero pueden tener un operario asignado (para conteo / movimientos).
        """INSERT OR IGNORE INTO areas_planta
           (codigo, nombre, puede_producir, puede_envasar, marmita_ml, especial, orden, tipo) VALUES
           ('ACOND',  'Acondicionamiento PT',     0, 0, NULL, NULL, 6, 'apoyo_asignable'),
           ('ALMP',   'Almacenamiento Mat.Prima', 0, 0, NULL, NULL, 7, 'conteo_ciclico'),
           ('ALMPT',  'Almacenamiento PT',        0, 0, NULL, NULL, 8, 'conteo_ciclico')""",
        # 4. produccion_programada gana columnas para tracking real inicio/fin.
        #    inicio_real_at: cuando el operario aprieta "Iniciar producción".
        #    fin_real_at:    cuando aprieta "Terminar".
        #    Permite calcular cycle time real vs estimado para KPIs.
        "ALTER TABLE produccion_programada ADD COLUMN inicio_real_at TEXT",
        "ALTER TABLE produccion_programada ADD COLUMN fin_real_at TEXT",
        # 5. area_eventos: log de TODO cambio de estado + iniciar/terminar.
        #    Sirve para timeline de cada sala, KPIs (tiempo promedio prod por
        #    SKU, tiempo de limpieza, ocupacion %, etc).
        """CREATE TABLE IF NOT EXISTS area_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_id INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN
                ('estado_cambio','iniciar_prod','terminar_prod',
                 'inicio_limpieza','fin_limpieza','iniciar_conteo','terminar_conteo')),
            estado_anterior TEXT,
            estado_nuevo TEXT,
            produccion_id INTEGER,
            operario_id INTEGER,
            usuario TEXT,
            nota TEXT,
            ts TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (area_id) REFERENCES areas_planta(id),
            FOREIGN KEY (produccion_id) REFERENCES produccion_programada(id),
            FOREIGN KEY (operario_id) REFERENCES operarios_planta(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_area_eventos_area_ts ON area_eventos(area_id, ts DESC)",
        "CREATE INDEX IF NOT EXISTS idx_area_eventos_prod ON area_eventos(produccion_id, ts)",
    ]),
    (59, "notif app: sistema unificado de alertas in-app (campana 🔔 + dropdown + badge)", [
        # Sebastian (30-abr-2026): "asignacion de tareas con alerta al usuario
        # en la app" — sistema centralizado de notificaciones in-app que
        # reemplaza polling fragmentado y emails. Todos los modulos pueden
        # llamar a push_notif() para dejar avisos a usuarios.
        """CREATE TABLE IF NOT EXISTS notificaciones_app (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            destinatario TEXT NOT NULL,
            tipo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            body TEXT,
            link TEXT,
            remitente TEXT,
            importante INTEGER NOT NULL DEFAULT 0,
            leido_at TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_notif_app_dest ON notificaciones_app(destinatario, leido_at, creado_en DESC)",
        "CREATE INDEX IF NOT EXISTS idx_notif_app_tipo ON notificaciones_app(tipo, creado_en DESC)",
    ]),
    (60, "compliance: cronogramas BPM + CAPA desviaciones + hallazgos abiertos", [
        # Sebastian (30-abr-2026): basado en correos reales — cronogramas
        # BPM atrasados (fumigacion 20%, ducha emergencia 25%), DESV-007
        # cerrada por email, "tuberias aguas + areas rechazo" pendientes
        # de cierre INVIMA. Modulo digital con alertas.
        # ── Tabla 1: cronogramas_bpm ────────────────────────────────────────
        """CREATE TABLE IF NOT EXISTS cronogramas_bpm (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            frecuencia TEXT,
            ejecuciones_year_objetivo INTEGER DEFAULT 12,
            responsable TEXT,
            activo INTEGER NOT NULL DEFAULT 1,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        # Seed con los cronogramas reales encontrados en Drive/correo
        """INSERT OR IGNORE INTO cronogramas_bpm
           (codigo, nombre, frecuencia, ejecuciones_year_objetivo, responsable) VALUES
           ('ASG-PGM-001-C01', 'Fumigaciones Espagiria', 'Mensual', 10, 'aseguramiento'),
           ('PRD-PRO-004-C01', 'Mantenimiento áreas y equipos', 'Mensual', 12, 'produccion'),
           ('COC-PRO-011-C01', 'Muestreo microbiologico equipos/areas/personal', 'Mensual', 12, 'controlcalidad'),
           ('RRH-PRO-007-C01', 'Capacitaciones personal', 'Trimestral', 4, 'recursoshumanos'),
           ('PRD-PRO-004-C01-DUCHA', 'Ducha emergencia y lavaojos verificación mensual', 'Mensual', 12, 'aseguramiento')""",
        """CREATE TABLE IF NOT EXISTS cronograma_ejecuciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cronograma_id INTEGER NOT NULL,
            fecha_planeada TEXT NOT NULL,
            fecha_real TEXT,
            ejecutado_por TEXT,
            evidencia_url TEXT,
            observaciones TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente'
                CHECK(estado IN ('pendiente','ejecutado','vencido','no_aplica')),
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (cronograma_id) REFERENCES cronogramas_bpm(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_cron_ej_id ON cronograma_ejecuciones(cronograma_id, fecha_planeada)",
        "CREATE INDEX IF NOT EXISTS idx_cron_ej_estado ON cronograma_ejecuciones(estado, fecha_planeada)",
        # ── Tabla 2: capa_desviaciones (DESV-NNN) ──────────────────────────
        """CREATE TABLE IF NOT EXISTS capa_desviaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            tipo TEXT NOT NULL CHECK(tipo IN ('desviacion','no_conformidad','queja','sugerencia')),
            titulo TEXT NOT NULL,
            descripcion TEXT,
            producto_relacionado TEXT,
            lote TEXT,
            severidad TEXT NOT NULL DEFAULT 'media' CHECK(severidad IN ('alta','media','baja')),
            fecha_apertura TEXT NOT NULL DEFAULT (date('now')),
            fecha_objetivo TEXT,
            fecha_cierre TEXT,
            responsable TEXT,
            accion_inmediata TEXT,
            causa_raiz TEXT,
            accion_correctiva TEXT,
            accion_preventiva TEXT,
            evidencia_url TEXT,
            estado TEXT NOT NULL DEFAULT 'abierta'
                CHECK(estado IN ('abierta','en_investigacion','en_implementacion','cerrada','cancelada')),
            creado_por TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_capa_estado ON capa_desviaciones(estado, fecha_apertura DESC)",
        "CREATE INDEX IF NOT EXISTS idx_capa_resp ON capa_desviaciones(responsable, estado)",
        # ── Tabla 3: hallazgos (auditoría / INVIMA / autoinspección) ──────
        """CREATE TABLE IF NOT EXISTS hallazgos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            origen TEXT NOT NULL CHECK(origen IN ('INVIMA','BPM_interna','autoinspeccion','auditoria_externa','queja_cliente','otro')),
            titulo TEXT NOT NULL,
            descripcion TEXT,
            area TEXT,
            severidad TEXT NOT NULL DEFAULT 'media' CHECK(severidad IN ('critico','mayor','menor','observacion')),
            fecha_deteccion TEXT NOT NULL DEFAULT (date('now')),
            fecha_limite TEXT,
            fecha_cierre TEXT,
            responsable TEXT,
            accion_propuesta TEXT,
            evidencia_cierre_url TEXT,
            capa_relacionada_id INTEGER,
            estado TEXT NOT NULL DEFAULT 'abierto'
                CHECK(estado IN ('abierto','en_proceso','cerrado','rechazado')),
            creado_por TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (capa_relacionada_id) REFERENCES capa_desviaciones(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_hall_estado ON hallazgos(estado, fecha_limite)",
        "CREATE INDEX IF NOT EXISTS idx_hall_origen ON hallazgos(origen, severidad)",
        # ── Tabla 4: maquila_pipeline (B2B Full Service) ──────────────────
        # Sebastian (30-abr-2026): correo JGB SA pidio maquila Full Service
        # 29 abr — NDA firmado mismo dia. Fernando Mesa unico activo,
        # ERLENMEYER ya cliente. Pipeline para no perder otro JGB.
        """CREATE TABLE IF NOT EXISTS maquila_pipeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa TEXT NOT NULL,
            contacto_nombre TEXT,
            contacto_email TEXT,
            contacto_telefono TEXT,
            origen TEXT,
            stage TEXT NOT NULL DEFAULT 'consulta'
                CHECK(stage IN ('consulta','nda','brief','cotizacion','contrato','produccion','ganado','perdido')),
            valor_estimado_cop REAL DEFAULT 0,
            volumen_estimado_unds INTEGER DEFAULT 0,
            producto_descripcion TEXT,
            nda_firmado_at TEXT,
            brief_recibido_at TEXT,
            cotizacion_enviada_at TEXT,
            contrato_firmado_at TEXT,
            fecha_cierre_estimada TEXT,
            owner TEXT,
            notas TEXT,
            motivo_perdida TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            actualizado_en TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_maq_stage ON maquila_pipeline(stage, creado_en DESC)",
        "CREATE INDEX IF NOT EXISTS idx_maq_owner ON maquila_pipeline(owner, stage)",
        # Seed con casos reales abiertos:
        """INSERT OR IGNORE INTO maquila_pipeline
           (empresa, contacto_nombre, contacto_email, origen, stage,
            nda_firmado_at, owner, notas) VALUES
           ('JGB SA', 'Yudy Alejandra Londoño', 'ylondono@jgb.com.co',
            'consulta web Espagiria', 'nda', '2026-04-29',
            'sebastian', 'Equipo compras JGB explorando proveedores Full Service. NDA firmado 29 abr. Esperan brief.'),
           ('ERLENMEYER SAS', 'Ana Maria Correa', 'erlenmeyer@erlenmeyer.com.co',
            'cliente recurrente', 'contrato', NULL,
            'sebastian', 'Cliente activo. Contrato y formatos en revision por RH.'),
           ('Fernando Mesa', 'Fernando Mesa', '', 'aliado B2B',
            'produccion', NULL, 'sebastian',
            'Pedido recurrente ~60 dias, ~$94.5M COP por ciclo.')""",
        # ── Tabla 5: eos_leads (form demo landing) ────────────────────────
        """CREATE TABLE IF NOT EXISTS eos_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            email TEXT,
            telefono TEXT,
            empresa TEXT,
            mensaje TEXT,
            fuente TEXT DEFAULT 'web3forms',
            payload_raw TEXT,
            estado TEXT NOT NULL DEFAULT 'nuevo'
                CHECK(estado IN ('nuevo','contactado','demo_agendada','propuesta','cerrado','descartado')),
            owner TEXT,
            notas TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_eos_leads_estado ON eos_leads(estado, creado_en DESC)",
        # ── Tabla 6: actividades_sala (turno operario por sala) ─────────────
        # Sebastian (30-abr-2026): "asignar operarios, hora inicio + fin por
        # actividad, asi medimos indicadores". Granularidad por OPERARIO
        # (no solo por produccion entera) — permite ver cuanto trabajo
        # cada operario en cada fase/sala.
        """CREATE TABLE IF NOT EXISTS actividades_sala (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_id INTEGER NOT NULL,
            operario_id INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN
                ('produccion','dispensacion','envasado','acondicionamiento',
                 'conteo_ciclico','limpieza','mantenimiento','otro')),
            descripcion TEXT,
            produccion_id INTEGER,
            inicio_at TEXT NOT NULL DEFAULT (datetime('now')),
            fin_at TEXT,
            duracion_min INTEGER,
            observaciones TEXT,
            creado_por TEXT,
            FOREIGN KEY (area_id) REFERENCES areas_planta(id),
            FOREIGN KEY (operario_id) REFERENCES operarios_planta(id),
            FOREIGN KEY (produccion_id) REFERENCES produccion_programada(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_act_area_inicio ON actividades_sala(area_id, inicio_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_act_operario ON actividades_sala(operario_id, inicio_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_act_prod ON actividades_sala(produccion_id)",
        # Seed con hallazgos abiertos reales de los correos:
        """INSERT OR IGNORE INTO hallazgos
           (codigo, origen, titulo, descripcion, area, severidad,
            fecha_deteccion, fecha_limite, responsable, estado, creado_por) VALUES
           ('HLZ-INV-001', 'INVIMA',
            'Identificación tuberías sistema de aguas',
            'Hallazgo abierto desde visita INVIMA — necesita levantamiento e identificación de todas las tuberías de aguas en planta.',
            'Planta', 'mayor', '2026-04-15', '2026-05-01',
            'luza.torresg', 'abierto', 'sebastian'),
           ('HLZ-AI-001',  'autoinspeccion',
            'Definir área Rechazos e ID Fabricación 3',
            'Solicitud Laura (calidad) 29 abr — definir espacio en área gris/negra para almacenamiento de rechazos según COC-PRO-002.',
            'Calidad', 'menor', '2026-04-29', '2026-05-15',
            'aseguramiento.espagiria', 'en_proceso', 'aseguramiento.espagiria')""",
    ]),
    (61, "calidad ampliada: micro specs + resultados + sistema de agua + OOS workflow", [
        # Sebastian (30-abr-2026): "los resultados de los microbiologicos a
        # todo producto le hacemos micro y sale resultado como tener un mapa
        # de calor o de resultados consolidados con alerta la industria
        # permite hasta un punto, pero un punto de meta y corte propio del
        # laboratorio asi tenemos un solo consolidado para saber como se
        # comportan". + COC-PRO-008 (sistema agua) + OOS (Out Of Spec).

        # ── Tabla 1: calidad_micro_specs ──────────────────────────────────
        # Limites por (producto × microorganismo). Doble: limite_industria
        # (norma INVIMA / farmacopea) y meta_lab (interno mas estricto).
        """CREATE TABLE IF NOT EXISTS calidad_micro_specs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_nombre TEXT NOT NULL,
            microorganismo TEXT NOT NULL,
            unidad TEXT NOT NULL DEFAULT 'UFC/g',
            limite_industria REAL,
            meta_lab REAL,
            tipo_limite TEXT NOT NULL DEFAULT 'maximo'
                CHECK(tipo_limite IN ('maximo','minimo','rango','ausencia')),
            metodo_referencia TEXT,
            activa INTEGER NOT NULL DEFAULT 1,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(producto_nombre, microorganismo)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_micro_specs_prod ON calidad_micro_specs(producto_nombre)",
        # Seed con microorganismos típicos de cosméticos colombianos
        # (Resolución 2950/2017 INVIMA + farmacopea USP/EP):
        #   Mesófilos aerobios totales ≤ 1000 UFC/g (industria), meta lab 100
        #   Mohos y levaduras ≤ 100 UFC/g, meta lab 10
        #   E. coli — ausencia/g
        #   S. aureus — ausencia/g
        #   P. aeruginosa — ausencia/g
        # Estos se aplican a TODOS los productos por default. Se seedearán
        # automáticamente al crear/migrar fórmulas via endpoint.
        """CREATE TABLE IF NOT EXISTS calidad_micro_specs_default (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            microorganismo TEXT NOT NULL UNIQUE,
            unidad TEXT NOT NULL DEFAULT 'UFC/g',
            limite_industria REAL,
            meta_lab REAL,
            tipo_limite TEXT NOT NULL DEFAULT 'maximo',
            descripcion TEXT
        )""",
        """INSERT OR IGNORE INTO calidad_micro_specs_default
           (microorganismo, unidad, limite_industria, meta_lab, tipo_limite, descripcion) VALUES
           ('Mesófilos aerobios totales', 'UFC/g', 1000, 100, 'maximo',
            'INVIMA Res 2950/2017 — productos no estériles. Meta lab más estricta para detección temprana.'),
           ('Mohos y levaduras',          'UFC/g',  100,  10, 'maximo',
            'INVIMA — indicador de contaminación ambiental / materia prima.'),
           ('E. coli',                    'UFC/g',    0,   0, 'ausencia',
            'INVIMA — patógeno indicador de contaminación fecal. Cero tolerancia.'),
           ('Staphylococcus aureus',      'UFC/g',    0,   0, 'ausencia',
            'INVIMA — patógeno indicador de contaminación de personal/manipulación.'),
           ('Pseudomonas aeruginosa',     'UFC/g',    0,   0, 'ausencia',
            'INVIMA — patógeno oportunista, contaminación por agua.'),
           ('Candida albicans',           'UFC/g',    0,   0, 'ausencia',
            'Patógeno fúngico — usual en productos íntimos / boca.'),
           ('Burkholderia cepacia',       'UFC/g',    0,   0, 'ausencia',
            'Recomendado FDA para cosméticos sin alcohol — detección obligatoria post-2017.')""",

        # ── Tabla 2: calidad_micro_resultados ─────────────────────────────
        # Cada análisis micro de un lote PT con su lectura por microorganismo.
        # Estado calculado al insertar: ok / fuera_meta / fuera_industria.
        """CREATE TABLE IF NOT EXISTS calidad_micro_resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lote TEXT NOT NULL,
            producto_nombre TEXT NOT NULL,
            fecha_muestreo TEXT,
            fecha_analisis TEXT NOT NULL DEFAULT (date('now')),
            microorganismo TEXT NOT NULL,
            valor REAL,
            valor_texto TEXT,
            unidad TEXT NOT NULL DEFAULT 'UFC/g',
            estado TEXT NOT NULL DEFAULT 'ok'
                CHECK(estado IN ('ok','fuera_meta','fuera_industria','observacion')),
            laboratorio TEXT DEFAULT 'Interno',
            analista TEXT,
            metodo TEXT,
            observaciones TEXT,
            oos_id INTEGER,
            creado_por TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_micro_res_prod ON calidad_micro_resultados(producto_nombre, fecha_analisis DESC)",
        "CREATE INDEX IF NOT EXISTS idx_micro_res_lote ON calidad_micro_resultados(lote)",
        "CREATE INDEX IF NOT EXISTS idx_micro_res_estado ON calidad_micro_resultados(estado, fecha_analisis DESC)",

        # ── Tabla 3: calidad_sistema_agua (COC-PRO-008) ──────────────────
        # Registros diarios/semanales del sistema de agua purificada.
        # Parámetros: pH, conductividad (µS/cm), TOC (ppb), microorgs,
        # cloro residual (si aplica), temperatura.
        """CREATE TABLE IF NOT EXISTS calidad_sistema_agua (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL DEFAULT (date('now')),
            hora TEXT,
            punto_muestreo TEXT NOT NULL,
            tipo_agua TEXT NOT NULL DEFAULT 'purificada'
                CHECK(tipo_agua IN ('purificada','potable','destilada','wfi','grado_reactivo')),
            ph REAL,
            conductividad_us_cm REAL,
            toc_ppb REAL,
            microorganismos_ufc_ml REAL,
            cloro_residual_ppm REAL,
            temperatura_c REAL,
            estado TEXT NOT NULL DEFAULT 'ok'
                CHECK(estado IN ('ok','alerta','fuera_spec')),
            observaciones TEXT,
            operador TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_agua_fecha ON calidad_sistema_agua(fecha DESC)",
        "CREATE INDEX IF NOT EXISTS idx_agua_punto ON calidad_sistema_agua(punto_muestreo, fecha DESC)",
        "CREATE INDEX IF NOT EXISTS idx_agua_estado ON calidad_sistema_agua(estado, fecha DESC)",

        # ── Tabla 4: calidad_oos (Out Of Specification) ──────────────────
        # Workflow formal cuando un análisis sale OOS:
        #   - Lote a cuarentena automática
        #   - Investigación obligatoria (causa raíz)
        #   - Disposición (release, reproceso, rechazo, destrucción)
        #   - Aprobación gerencial
        """CREATE TABLE IF NOT EXISTS calidad_oos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            origen TEXT NOT NULL DEFAULT 'micro'
                CHECK(origen IN ('micro','fisicoquimico','agua','estabilidad','otro')),
            lote TEXT,
            producto TEXT,
            parametro TEXT NOT NULL,
            valor_obtenido REAL,
            valor_obtenido_texto TEXT,
            valor_esperado_texto TEXT,
            limite_violado TEXT NOT NULL DEFAULT 'meta_lab'
                CHECK(limite_violado IN ('meta_lab','limite_industria','ambos')),
            fecha_deteccion TEXT NOT NULL DEFAULT (date('now')),
            fecha_objetivo_cierre TEXT,
            fecha_cierre TEXT,
            estado TEXT NOT NULL DEFAULT 'abierto'
                CHECK(estado IN ('abierto','en_investigacion','en_aprobacion','cerrado','rechazado')),
            accion_inmediata TEXT,
            causa_raiz TEXT,
            disposicion TEXT
                CHECK(disposicion IS NULL OR disposicion IN ('liberado','reprocesado','rechazado','destruido','reanalisis')),
            aprobado_por TEXT,
            fecha_aprobacion TEXT,
            capa_id INTEGER,
            creado_por TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (capa_id) REFERENCES capa_desviaciones(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_oos_estado ON calidad_oos(estado, fecha_deteccion DESC)",
        "CREATE INDEX IF NOT EXISTS idx_oos_lote ON calidad_oos(lote)",
        "CREATE INDEX IF NOT EXISTS idx_oos_producto ON calidad_oos(producto)",
    ]),
    (62, "planta inteligente fase 0: presentaciones por SKU (suero 30/15/10mL, etc)", [
        # Sebastian + Alejandro (30-abr-2026): "Sueros tienen varias presentaciones,
        # vienen de 30ml, 10ml y 15mL... contornos de ojos: 15ml multipeptidos y
        # retinal, cafeina 10mL... Maxlash 4.5mL... Blush balm 6g". Sin esto la
        # planificacion "produzcamos suero para 2 meses" es ambigua.
        #
        # Tabla nueva, NO toca formula_headers. Una formula puede tener N
        # presentaciones; cada una indica volumen, envase MEE asociado, y
        # factor (gramos por unidad).
        """CREATE TABLE IF NOT EXISTS producto_presentaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_nombre TEXT NOT NULL,
            categoria TEXT,
            presentacion_codigo TEXT NOT NULL,
            etiqueta TEXT NOT NULL,
            volumen_ml REAL,
            peso_g REAL,
            envase_codigo TEXT,
            factor_g_por_unidad REAL,
            sku_shopify TEXT,
            es_default INTEGER NOT NULL DEFAULT 0,
            activo INTEGER NOT NULL DEFAULT 1,
            notas TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            actualizado_en TEXT,
            UNIQUE(producto_nombre, presentacion_codigo)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_pp_producto ON producto_presentaciones(producto_nombre, activo)",
        "CREATE INDEX IF NOT EXISTS idx_pp_sku ON producto_presentaciones(sku_shopify)",
        "CREATE INDEX IF NOT EXISTS idx_pp_envase ON producto_presentaciones(envase_codigo)",
        # Seed de plantillas por categoria (Alejandro 30-abr-2026).
        # producto_nombre vacio inicialmente — son plantillas que se
        # asignan a productos especificos via UI. Permitimos producto_nombre=''
        # con presentacion_codigo unico para plantilla generica.
        # Nota: el seed real por producto se hace despues via endpoint cuando
        # Alejandro asigne presentaciones a cada formula.
        # Por ahora dejamos solo la estructura — seed de plantillas no aplica
        # porque UNIQUE(producto, presentacion) requiere producto.
    ]),
    (63, "planta inteligente fase 1: catalogo equipos del Excel + 9 areas reales", [
        # Sebastian + Alejandro (30-abr-2026): Excel "LISTADO MAESTRO DE
        # EQUIPOS 2026" trae 104 equipos en 9+ areas reales. Hoy
        # areas_planta solo tiene 5 codigos (PROD1-4, ENV1) que no
        # representan la planta real post-INVIMA. Esta migracion:
        #  1. Renombra PROD1->Fabricacion 1 (mantiene codigo PROD1 para
        #     no romper produccion_programada.area_id historico).
        #  2. Marca PROD4 como activo=0 (no existe en la realidad).
        #  3. Agrega areas nuevas: FAB1/2/3, ENV2, DISP, LAV, ESC1, FAB_FLOAT,
        #     CC, RECEP. FAB1/2/3 conviven con PROD1/2/3 — los nuevos son
        #     los oficiales para nueva data.
        #  4. Marca las 9 areas que requieren limpieza profunda (brief K).
        #  5. Crea tabla equipos_planta.
        #  6. Seed con 104 equipos del Excel (idempotente con OR IGNORE).
        "ALTER TABLE areas_planta ADD COLUMN requiere_limpieza_profunda INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE areas_planta ADD COLUMN ultima_limpieza_profunda TEXT",
        "UPDATE areas_planta SET nombre='Fabricación 1' WHERE codigo='PROD1'",
        "UPDATE areas_planta SET nombre='Fabricación 2' WHERE codigo='PROD2'",
        "UPDATE areas_planta SET nombre='Fabricación 3' WHERE codigo='PROD3'",
        "UPDATE areas_planta SET activo=0, nombre='Producción 4 (deprecated)' WHERE codigo='PROD4'",
        """INSERT OR IGNORE INTO areas_planta
           (codigo, nombre, puede_producir, puede_envasar, marmita_ml, especial, orden, tipo, requiere_limpieza_profunda) VALUES
           ('FAB1', 'Fabricación 1', 1, 0, NULL, NULL, 1, 'produccion', 1),
           ('FAB2', 'Fabricación 2', 1, 1, 50, NULL, 2, 'produccion', 1),
           ('FAB3', 'Fabricación 3', 1, 1, 400, NULL, 3, 'produccion', 1),
           ('ENV2', 'Envasado 2', 0, 1, NULL, NULL, 5, 'produccion', 1),
           ('DISP', 'Dispensación', 0, 0, NULL, 'asepsia', 6, 'apoyo_asignable', 1),
           ('LAV',  'Área de Lavado', 0, 0, NULL, NULL, 7, 'apoyo_asignable', 1),
           ('ESC1', 'Esclusa 1', 0, 0, NULL, NULL, 8, 'apoyo_asignable', 1),
           ('FAB_FLOAT', 'Fabricación según necesidad', 1, 0, NULL, NULL, 9, 'produccion', 0),
           ('CC',   'Control de Calidad', 0, 0, NULL, NULL, 10, 'apoyo_asignable', 0),
           ('RECEP','Recepción de Insumos', 0, 0, NULL, NULL, 11, 'apoyo_asignable', 0)""",
        # Marcar las 9 areas que pide Alejandro K (brief de limpieza profunda).
        # Usamos los codigos nuevos (FAB1..FAB3, ENV1..ENV2, DISP, LAV, ESC1, ALMP).
        "UPDATE areas_planta SET requiere_limpieza_profunda=1 WHERE codigo IN ('FAB1','FAB2','FAB3','ENV1','ENV2','DISP','LAV','ESC1','ALMP')",
        # Catalogo de equipos. Acepta duplicados de codigo en distintas
        # ubicaciones porque el Excel los tiene (errores marcados como
        # observacion, validos hasta que Alejandro corrija).
        """CREATE TABLE IF NOT EXISTS equipos_planta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL,
            nombre TEXT NOT NULL,
            area_codigo TEXT,
            ubicacion_raw TEXT,
            tipo TEXT NOT NULL DEFAULT 'otro',
            capacidad_raw TEXT,
            capacidad_litros REAL,
            capacidad_kg REAL,
            estado_operacional TEXT NOT NULL DEFAULT 'operativo'
                CHECK(estado_operacional IN ('operativo','mantenimiento','baja','calibracion')),
            activo INTEGER NOT NULL DEFAULT 1,
            notas TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            actualizado_en TEXT,
            UNIQUE(codigo, ubicacion_raw)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_equipos_area ON equipos_planta(area_codigo, activo)",
        "CREATE INDEX IF NOT EXISTS idx_equipos_tipo ON equipos_planta(tipo, activo)",
        "CREATE INDEX IF NOT EXISTS idx_equipos_capacidad ON equipos_planta(capacidad_litros)",
        # Seed: 104 equipos del Excel "LISTADO MAESTRO DE EQUIPOS 2026".
        # Multi-row INSERT idempotente. Si Alejandro corrige el Excel mas
        # adelante, se puede re-ejecutar sin duplicar (UNIQUE codigo+ubicacion).
        _SEED_EQUIPOS_PLANTA_SQL,
    ]),
    (64, "planta inteligente fase 3: envasado→micro 5d, cola liberación, scheduler limpieza", [
        # Sebastian + Alejandro (30-abr-2026, brief D/F/C):
        #  D. Envío de muestra micro al INICIAR envasado (tarda 5 días)
        #  F. Liberación 1-2 productos/día tras esperar el resultado
        #  C. Rotación limpieza profunda L-Ma-J-V con preferencia al área
        #     que se produjo el día anterior
        # Tres tablas + columnas en calidad_micro_resultados (link a evento).

        # 1) produccion_envasado: cada vez que un operario marca "iniciar envasado"
        #    se crea un registro. Permite linkear lote PT con muestra micro.
        """CREATE TABLE IF NOT EXISTS produccion_envasado (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produccion_id INTEGER NOT NULL,
            producto_nombre TEXT NOT NULL,
            lote TEXT NOT NULL,
            presentacion_id INTEGER,
            presentacion_etiqueta TEXT,
            unidades_planeadas INTEGER,
            unidades_envasadas INTEGER,
            envase_codigo TEXT,
            iniciado_at TEXT NOT NULL DEFAULT (datetime('now')),
            iniciado_por TEXT,
            terminado_at TEXT,
            terminado_por TEXT,
            estado TEXT NOT NULL DEFAULT 'en_proceso'
                CHECK(estado IN ('en_proceso','terminado','cancelado')),
            muestra_micro_id INTEGER,
            notas TEXT,
            FOREIGN KEY (produccion_id) REFERENCES produccion_programada(id),
            FOREIGN KEY (presentacion_id) REFERENCES producto_presentaciones(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_pe_estado ON produccion_envasado(estado, iniciado_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_pe_lote ON produccion_envasado(lote, producto_nombre)",
        "CREATE INDEX IF NOT EXISTS idx_pe_micro ON produccion_envasado(muestra_micro_id)",

        # 2) cola_liberacion: lote PT esperando liberación QC (post-micro 5d).
        """CREATE TABLE IF NOT EXISTS cola_liberacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            envasado_id INTEGER,
            producto_nombre TEXT NOT NULL,
            lote TEXT NOT NULL,
            presentacion_etiqueta TEXT,
            unidades INTEGER,
            fecha_envasado TEXT NOT NULL,
            fecha_min_liberacion TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'esperando_micro'
                CHECK(estado IN ('esperando_micro','listo_revisar','liberado','rechazado','reanalisis')),
            micro_resultado_id INTEGER,
            disposicion TEXT
                CHECK(disposicion IS NULL OR disposicion IN ('aprobado','rechazado','reanalizar')),
            aprobado_por TEXT,
            aprobado_at TEXT,
            notas TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (envasado_id) REFERENCES produccion_envasado(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_cl_estado ON cola_liberacion(estado, fecha_min_liberacion)",
        "CREATE INDEX IF NOT EXISTS idx_cl_producto ON cola_liberacion(producto_nombre, lote)",

        # 3) limpieza_profunda_calendario: programación rotativa L-Ma-J-V.
        """CREATE TABLE IF NOT EXISTS limpieza_profunda_calendario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            area_codigo TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'programada'
                CHECK(estado IN ('programada','en_proceso','completada','cancelada','reagendada')),
            asignado_a TEXT,
            iniciado_at TEXT,
            terminado_at TEXT,
            iniciado_por TEXT,
            terminado_por TEXT,
            generado_por TEXT NOT NULL DEFAULT 'auto',
            razon_asignacion TEXT,
            notas TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(fecha, area_codigo)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_lpc_fecha ON limpieza_profunda_calendario(fecha, estado)",
        "CREATE INDEX IF NOT EXISTS idx_lpc_area ON limpieza_profunda_calendario(area_codigo, fecha DESC)",

        # 4) Link bidireccional desde calidad_micro_resultados a envasado
        # (no FK estricta para no romper si la tabla ya tiene datos sin envasado_id).
        "ALTER TABLE calidad_micro_resultados ADD COLUMN envasado_id INTEGER",
        "ALTER TABLE calidad_micro_resultados ADD COLUMN deadline_resultado TEXT",
        "CREATE INDEX IF NOT EXISTS idx_cmr_envasado ON calidad_micro_resultados(envasado_id)",
    ]),
    (67, "maquila inteligente: clientes_maquila + maquila_pedidos integrados al plan", [
        # Sebastian (30-abr-2026): "Kelly Guerra compra productos para marca
        # de ella pero misma fórmula Animus, ejemplo LBHA hacemos 200 kilos
        # pero son también para ella... espacio de maquila inteligente, si
        # Fernando lleva 500 le adiciona a la producción esas 500 unidades".
        # Modelo: el motor del Plan suma pedidos de maquila a la producción
        # base de Animus, todo en el mismo lote cuando comparten fórmula.

        """CREATE TABLE IF NOT EXISTS clientes_maquila (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            nit_cedula TEXT,
            email TEXT,
            telefono TEXT,
            es_marca_propia INTEGER NOT NULL DEFAULT 0,
            empresa_grupo TEXT,
            comparte_formula_con TEXT,
            margen_seguridad_pct INTEGER NOT NULL DEFAULT 5,
            activo INTEGER NOT NULL DEFAULT 1,
            notas TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            actualizado_en TEXT
        )""",
        # Seed con clientes conocidos
        """INSERT OR IGNORE INTO clientes_maquila
           (nombre, es_marca_propia, empresa_grupo, comparte_formula_con, notas) VALUES
           ('Animus Lab',      1, 'HHA Group', NULL, 'Marca propia · venta directa Shopify'),
           ('Kelly Guerra',    0, NULL, 'Animus Lab', 'Misma fórmula Animus · marca propia de cliente'),
           ('Fernando',        0, NULL, NULL, 'Cliente maquila — pendiente confirmar fórmulas')""",

        """CREATE TABLE IF NOT EXISTS maquila_pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL UNIQUE,
            cliente_id INTEGER NOT NULL,
            cliente_nombre TEXT,
            producto_nombre TEXT NOT NULL,
            presentacion_id INTEGER,
            unidades INTEGER NOT NULL,
            kg_estimados REAL,
            fecha_pedido TEXT NOT NULL DEFAULT (date('now')),
            fecha_entrega_objetivo TEXT,
            estado TEXT NOT NULL DEFAULT 'recibido'
                CHECK(estado IN ('recibido','planificado','en_produccion','listo_entrega','entregado','cancelado')),
            produccion_id INTEGER,
            precio_unidad REAL,
            valor_total REAL,
            observaciones TEXT,
            creado_por TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            actualizado_en TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes_maquila(id),
            FOREIGN KEY (presentacion_id) REFERENCES producto_presentaciones(id),
            FOREIGN KEY (produccion_id) REFERENCES produccion_programada(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_maquila_estado ON maquila_pedidos(estado, fecha_entrega_objetivo)",
        "CREATE INDEX IF NOT EXISTS idx_maquila_cliente ON maquila_pedidos(cliente_id, estado)",
        "CREATE INDEX IF NOT EXISTS idx_maquila_producto ON maquila_pedidos(producto_nombre, estado)",
        "CREATE INDEX IF NOT EXISTS idx_maquila_prod ON maquila_pedidos(produccion_id)",
    ]),
    (69, "planta: estado SKU + descontinuados auto-detectados", [
        # Sebastian (30-abr-2026): "estos en rojo ya no los producimos varias
        # cosas". Necesidad: marcar SKUs como descontinuados/sin_ventas para
        # que el motor NO los siga programando como críticos.
        "ALTER TABLE sku_planeacion_config ADD COLUMN estado TEXT NOT NULL DEFAULT 'activo'",
        "ALTER TABLE sku_planeacion_config ADD COLUMN descontinuado_at TEXT",
        "ALTER TABLE sku_planeacion_config ADD COLUMN descontinuado_por TEXT",
        "ALTER TABLE sku_planeacion_config ADD COLUMN razon_estado TEXT",
        # Estados validos: activo, sin_ventas, baja_rotacion, descontinuado, pausado, nuevo
    ]),
    (70, "envasado: consumo MEE real al terminar (cantidad envasada vs planificada)", [
        # Sebastian (1-may-2026): "en produccion dicen envasado, para que coloquen
        # cuanto fue y de alli mismo descuenta automaticamente envases y demas".
        # Hoy el descuento MEE ocurre al COMPLETAR producción usando cantidad
        # planificada del checklist. Se mueve al terminar envasado, descontando
        # la cantidad REAL envasada (proporcional). Flag consumido_at evita doble
        # descuento cuando luego se completa la producción.
        "ALTER TABLE produccion_checklist ADD COLUMN consumido_at TEXT",
        "ALTER TABLE produccion_checklist ADD COLUMN consumido_por TEXT DEFAULT ''",
        "ALTER TABLE produccion_checklist ADD COLUMN cantidad_consumida_real REAL DEFAULT 0",
        "ALTER TABLE produccion_checklist ADD COLUMN consumido_contexto TEXT DEFAULT ''",
        # contexto = 'envasado' (envase/tapa/etiqueta al terminar) o 'completar' (legacy/resto)
        "CREATE INDEX IF NOT EXISTS idx_pc_consumido ON produccion_checklist(produccion_id, consumido_at)",
    ]),
    (68, "planta MRP: alias_calendar + log eventos + auto-area producciones", [
        # Sebastian (30-abr-2026, ULTRATHINK): "en calendar dice kg, revisa
        # bien y que sea perfecto, zero-error-enterprise". El motor MRP
        # necesita match robusto producto↔evento Calendar, parser kg agresivo
        # y auto-asignación de área.

        # Alias del producto en Google Calendar (CSV de aliases)
        # Ejemplo: SUERO HIDRATANTE AH 1.5% → "AH 1.5%, AH, Hidratante AH"
        "ALTER TABLE sku_planeacion_config ADD COLUMN alias_calendar TEXT",

        # Log de eventos de Calendar para auditoría/debug
        """CREATE TABLE IF NOT EXISTS calendar_eventos_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id_externo TEXT,
            titulo TEXT NOT NULL,
            fecha TEXT NOT NULL,
            descripcion TEXT,
            kg_detectados REAL,
            producto_matcheado TEXT,
            score_match INTEGER,
            estado TEXT NOT NULL DEFAULT 'leido'
                CHECK(estado IN ('leido','matcheado','sin_match','conflicto','manual')),
            notas TEXT,
            ts_leido TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_cal_log_estado ON calendar_eventos_log(estado, fecha)",
        "CREATE INDEX IF NOT EXISTS idx_cal_log_producto ON calendar_eventos_log(producto_matcheado, fecha)",

        # Seed de aliases razonables para los productos clave
        # Sebastian + Alejandro: cadencias críticas Vit C y AH 1.5%
        """UPDATE sku_planeacion_config SET alias_calendar = 'AH 1.5%, AH, Suero AH, Hidratante AH'
            WHERE producto_nombre = 'SUERO HIDRATANTE AH 1.5%'""",
        """UPDATE sku_planeacion_config SET alias_calendar = 'Vit C+B3, Vitamina C+B3, C+B3'
            WHERE producto_nombre = 'SUERO ANTIOXIDANTE VITAMINA C+B3'""",
        """UPDATE sku_planeacion_config SET alias_calendar = 'Vit C, Vitamina C, Suero Vit C'
            WHERE producto_nombre = 'SUERO DE VITAMINA C+ FORMULA NUEVA'""",
        """UPDATE sku_planeacion_config SET alias_calendar = 'Renova C10, C10, RENOVA C10'
            WHERE producto_nombre = 'SUERO ANTIOXIDANTE RENOVA C10'""",
        """UPDATE sku_planeacion_config SET alias_calendar = 'BHA 2%, Limpiador BHA, BHA'
            WHERE producto_nombre = 'LIMPIADOR FACIAL BHA 2%'""",
        """UPDATE sku_planeacion_config SET alias_calendar = 'Iluminador Kojico, Kojico, Limpiador Kojico'
            WHERE producto_nombre = 'LIMPIADOR ILUMINADOR ACIDO KOJICO'""",
        """UPDATE sku_planeacion_config SET alias_calendar = 'Maxlash'
            WHERE producto_nombre = 'MAXLASH'""",
        """UPDATE sku_planeacion_config SET alias_calendar = 'Cafeina, Contorno Cafeina'
            WHERE producto_nombre = 'CONTORNO DE CAFEINA'""",
        """UPDATE sku_planeacion_config SET alias_calendar = 'Multipeptidos, Contorno Multi'
            WHERE producto_nombre = 'CONTORNO DE OJOS MULTIPEPTIDOS'""",
        """UPDATE sku_planeacion_config SET alias_calendar = 'Retinaldehido Contorno, Contorno Retinal'
            WHERE producto_nombre = 'CONTORNO DE OJOS RETINALDEHIDO 0.05%'""",
        """UPDATE sku_planeacion_config SET alias_calendar = 'AZ Hibrid, AZ HIBRID'
            WHERE producto_nombre = 'AZ HIBRID CLEAR'""",
        """UPDATE sku_planeacion_config SET alias_calendar = 'BHA Limpiador, Limpiador BHA, BHA'
            WHERE producto_nombre = 'LIMPIADOR FACIAL BHA 2%'""",
    ]),
    (66, "planta polish: perfil riesgo arrastre + auto_plan_cron_state + asistente acciones", [
        # Sebastian (30-abr-2026): "termina de hacer todo lo que falta entrégame
        # cuando ya sea perfecta" — piezas finales del módulo planta:
        # 1. Perfil de riesgo por producto (color/pigmento/viscosidad) para
        #    detectar arrastre crítico (pigmento → claro = limpieza obligatoria)
        # 2. Estado del cron (start/stop desde UI sin tocar env vars)
        # 3. Log de acciones del asistente Claude
        """CREATE TABLE IF NOT EXISTS producto_perfil_riesgo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_nombre TEXT NOT NULL UNIQUE,
            tiene_pigmento INTEGER NOT NULL DEFAULT 0,
            color_descripcion TEXT,
            es_acido INTEGER NOT NULL DEFAULT 0,
            requiere_asepsia_extra INTEGER NOT NULL DEFAULT 0,
            riesgo_arrastre_pct INTEGER NOT NULL DEFAULT 5,
            notas TEXT,
            actualizado_en TEXT
        )""",
        # Seed con perfiles conocidos (Sebastian, brief notas presentaciones)
        """INSERT OR IGNORE INTO producto_perfil_riesgo
           (producto_nombre, tiene_pigmento, color_descripcion, es_acido, requiere_asepsia_extra, riesgo_arrastre_pct, notas) VALUES
           ('MAXLASH',                              1, 'negro/oscuro', 0, 1, 90, 'Pigmento intenso — limpieza profunda obligatoria después'),
           ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 0, 'amarillo claro', 0, 1, 30, 'Retinaldehído — sensible a luz/oxidación'),
           ('SUERO DE RETINALDEHIDO 0.05%',         0, 'amarillo claro', 0, 1, 30, 'Retinaldehído — sensible a luz/oxidación'),
           ('Suero RETINAL +',                      0, 'amarillo claro', 0, 1, 30, 'Retinaldehído — sensible a luz/oxidación'),
           ('SUERO ANTIOXIDANTE VITAMINA C+B3',     0, 'transparente/amarillo', 1, 0, 20, 'Vit C oxida — proteger de luz'),
           ('SUERO DE VITAMINA C+ FORMULA NUEVA',   0, 'transparente/amarillo', 1, 0, 20, 'Vit C oxida'),
           ('SUERO ANTIOXIDANTE RENOVA C10',        0, 'transparente/amarillo', 1, 0, 20, 'Vit C oxida'),
           ('SUERO EXFOLIANTE NOVA PHA',            0, 'transparente', 1, 0, 25, 'Ácido — controlar pH'),
           ('Suero Exfoliante BHA 2%',              0, 'transparente', 1, 0, 25, 'BHA ácido'),
           ('LIMPIADOR FACIAL BHA 2%',              0, 'transparente', 1, 0, 20, 'BHA ácido'),
           ('LIMPIADOR ILUMINADOR ACIDO KOJICO',    0, 'transparente claro', 1, 0, 25, 'Ácido kójico'),
           ('SUERO HIDRATANTE AH 1.5%',             0, 'transparente', 0, 0, 5, 'Sin riesgo arrastre relevante')""",

        """CREATE TABLE IF NOT EXISTS auto_plan_cron_state (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            habilitado INTEGER NOT NULL DEFAULT 0,
            activado_por TEXT,
            activado_at TEXT,
            ultima_ejecucion_at TEXT,
            proxima_ejecucion_at TEXT,
            errores_consecutivos INTEGER NOT NULL DEFAULT 0,
            notas TEXT
        )""",
        "INSERT OR IGNORE INTO auto_plan_cron_state (id, habilitado) VALUES (1, 0)",

        """CREATE TABLE IF NOT EXISTS asistente_acciones_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL DEFAULT (datetime('now')),
            usuario TEXT NOT NULL,
            pregunta TEXT,
            tool_invocado TEXT,
            tool_args TEXT,
            tool_resultado TEXT,
            exitoso INTEGER NOT NULL DEFAULT 1
        )""",
        "CREATE INDEX IF NOT EXISTS idx_aal_ts ON asistente_acciones_log(ts DESC)",
        "CREATE INDEX IF NOT EXISTS idx_aal_usuario ON asistente_acciones_log(usuario, ts DESC)",
    ]),
    (65, "planta auto-plan: configs SKU/MP/email/conteo + log runs", [
        # Sebastian (30-abr-2026): "Vitamina C mensual, suero AH 90 días para
        # 90 días, lotes típicos 90kg, MP mínimo 30d ideal 60d, envases mínimo
        # 3 meses (China lead 180d)... usa toda tu capacidad para que quede
        # perfecto, debe ser la herramienta más avanzada del mundo".
        # L/M/V producir, Ma/Ju acondicionar/envasar/conteo cíclico, 7am L-V.

        # 1) Config por SKU: cadencia + cobertura + merma + presentación default
        """CREATE TABLE IF NOT EXISTS sku_planeacion_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_nombre TEXT NOT NULL UNIQUE,
            categoria TEXT,
            cadencia_dias INTEGER,
            cobertura_target_dias INTEGER NOT NULL DEFAULT 60,
            cobertura_max_dias INTEGER NOT NULL DEFAULT 90,
            cobertura_min_dias INTEGER NOT NULL DEFAULT 30,
            merma_pct REAL NOT NULL DEFAULT 5.0,
            prioridad INTEGER NOT NULL DEFAULT 5,
            presentacion_default_id INTEGER,
            activo INTEGER NOT NULL DEFAULT 1,
            notas TEXT,
            actualizado_en TEXT,
            FOREIGN KEY (presentacion_default_id) REFERENCES producto_presentaciones(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_spc_activo ON sku_planeacion_config(activo, prioridad)",

        # 2) Config lead-time MP/envases por proveedor
        """CREATE TABLE IF NOT EXISTS mp_lead_time_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id TEXT NOT NULL,
            material_nombre TEXT,
            proveedor_principal TEXT,
            lead_time_dias INTEGER NOT NULL DEFAULT 14,
            buffer_dias INTEGER NOT NULL DEFAULT 30,
            cobertura_min_dias INTEGER NOT NULL DEFAULT 30,
            cobertura_ideal_dias INTEGER NOT NULL DEFAULT 60,
            origen TEXT NOT NULL DEFAULT 'local'
                CHECK(origen IN ('local','nacional','china','usa','europa','otro')),
            es_envase INTEGER NOT NULL DEFAULT 0,
            activo INTEGER NOT NULL DEFAULT 1,
            actualizado_en TEXT,
            UNIQUE(material_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_mlt_origen ON mp_lead_time_config(origen, activo)",
        "CREATE INDEX IF NOT EXISTS idx_mlt_envase ON mp_lead_time_config(es_envase, activo)",

        # 3) Emails por rol — la app envía notificaciones a estos correos
        """CREATE TABLE IF NOT EXISTS email_destinatarios_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rol TEXT NOT NULL UNIQUE,
            nombre TEXT,
            email TEXT NOT NULL,
            recibe_resumen_diario INTEGER NOT NULL DEFAULT 1,
            recibe_alertas_criticas INTEGER NOT NULL DEFAULT 1,
            recibe_compras_aprob INTEGER NOT NULL DEFAULT 0,
            recibe_calidad INTEGER NOT NULL DEFAULT 0,
            recibe_agenda_personal INTEGER NOT NULL DEFAULT 0,
            activo INTEGER NOT NULL DEFAULT 1,
            actualizado_en TEXT
        )""",
        # Seed con roles esperados (email '' hasta que Sebastian los configure)
        """INSERT OR IGNORE INTO email_destinatarios_config
           (rol, nombre, email, recibe_resumen_diario, recibe_alertas_criticas, recibe_compras_aprob, recibe_calidad, recibe_agenda_personal) VALUES
           ('ceo', 'Sebastián Vargas', '', 1, 1, 0, 0, 0),
           ('gerencia_produccion', 'Alejandro', '', 1, 1, 0, 1, 0),
           ('compras', 'Catalina', '', 1, 0, 1, 0, 0),
           ('jefe_planta', 'Luis Enrique', '', 1, 1, 0, 0, 1),
           ('operario_dispensacion', 'Mayerlin Rivera', '', 0, 0, 0, 0, 1),
           ('operario_envasado', 'Sebastián Murillo', '', 0, 0, 0, 0, 1),
           ('operario_acondicionamiento', 'Camilo García', '', 0, 0, 0, 0, 1),
           ('operario_todero', 'Milton Sanabria', '', 0, 0, 0, 0, 1)""",

        # 4) Log de ejecuciones del auto-plan (para debug + auditoría)
        """CREATE TABLE IF NOT EXISTS auto_plan_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ejecutado_at TEXT NOT NULL DEFAULT (datetime('now')),
            ejecutado_por TEXT NOT NULL DEFAULT 'cron',
            tipo TEXT NOT NULL DEFAULT 'auto'
                CHECK(tipo IN ('auto','manual','dry_run')),
            horizonte_dias INTEGER NOT NULL DEFAULT 60,
            producciones_creadas INTEGER NOT NULL DEFAULT 0,
            compras_creadas INTEGER NOT NULL DEFAULT 0,
            alertas_criticas INTEGER NOT NULL DEFAULT 0,
            emails_enviados INTEGER NOT NULL DEFAULT 0,
            error TEXT,
            payload_json TEXT,
            duracion_ms INTEGER
        )""",
        "CREATE INDEX IF NOT EXISTS idx_apr_fecha ON auto_plan_runs(ejecutado_at DESC)",

        # 5) Conteo cíclico ABC (Sebastian: "días de asignación de inventario
        # cíclico, si alguna duda de materia prima generar alerta revisar")
        """CREATE TABLE IF NOT EXISTS conteo_ciclico_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id TEXT NOT NULL UNIQUE,
            categoria_abc TEXT NOT NULL DEFAULT 'C'
                CHECK(categoria_abc IN ('A','B','C')),
            frecuencia_dias INTEGER NOT NULL DEFAULT 90,
            ultimo_conteo_fecha TEXT,
            ultimo_conteo_diferencia REAL,
            requiere_validacion INTEGER NOT NULL DEFAULT 0,
            actualizado_en TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS conteo_ciclico_calendario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            material_id TEXT NOT NULL,
            material_nombre TEXT,
            categoria_abc TEXT,
            asignado_a TEXT,
            stock_esperado_g REAL,
            stock_real_g REAL,
            diferencia_g REAL,
            estado TEXT NOT NULL DEFAULT 'programado'
                CHECK(estado IN ('programado','contado','con_diferencia','cerrado','reprogramado')),
            iniciado_at TEXT,
            terminado_at TEXT,
            iniciado_por TEXT,
            terminado_por TEXT,
            notas TEXT,
            generado_por TEXT NOT NULL DEFAULT 'auto',
            UNIQUE(fecha, material_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ccc_fecha ON conteo_ciclico_calendario(fecha, estado)",
        "CREATE INDEX IF NOT EXISTS idx_ccc_material ON conteo_ciclico_calendario(material_id, fecha DESC)",

        # 6) Seed inicial de cadencias por SKU según brief Sebastian + Alejandro.
        # Vit C cada 30d, Suero AH cada 90d para 90d cobertura, lote típico 90kg.
        # Otros sueros 60d, sólidos (blush/maxlash) 90d, limpiadores/hidratantes
        # auto por umbral (sin cadencia fija).
        """INSERT OR IGNORE INTO sku_planeacion_config
           (producto_nombre, categoria, cadencia_dias, cobertura_target_dias, cobertura_max_dias, cobertura_min_dias, merma_pct, prioridad, notas) VALUES
           ('SUERO ANTIOXIDANTE VITAMINA C+B3',     'suero_vit_c', 30, 60, 90, 30, 10.0, 1, 'Vit C oxida — cadencia mensual'),
           ('SUERO DE VITAMINA C+ FORMULA NUEVA',   'suero_vit_c', 30, 60, 90, 30, 10.0, 1, 'Vit C oxida — cadencia mensual'),
           ('SUERO ANTIOXIDANTE RENOVA C10',        'suero_vit_c', 30, 60, 90, 30, 10.0, 1, 'Vit C oxida — cadencia mensual'),
           ('SUERO HIDRATANTE AH 1.5%',             'suero_ah', 90, 90, 120, 60, 5.0, 1, 'Lote típico 90kg, cobertura 90d'),
           ('SUERO ILUMINADOR TRX',                 'suero', NULL, 60, 90, 30, 5.0, 3, 'Auto por umbral'),
           ('SUERO MULTIPEPTIDOS',                  'suero', NULL, 60, 90, 30, 5.0, 3, NULL),
           ('SUERO TRIACTIVE RETINOID NAD+',        'suero', NULL, 60, 90, 30, 5.0, 3, NULL),
           ('SUERO DE NIACINAMIDA 5% FORMULA NUEVA','suero', NULL, 60, 90, 30, 5.0, 3, NULL),
           ('SUERO DE RETINALDEHIDO 0.05%',         'suero', NULL, 60, 90, 30, 5.0, 3, NULL),
           ('SUERO AZ + B3',                        'suero', NULL, 60, 90, 30, 5.0, 3, NULL),
           ('SUERO EXFOLIANTE NOVA PHA',            'suero', NULL, 60, 90, 30, 5.0, 3, NULL),
           ('SUERO ILUMINADOR AHA+AH.',             'suero', NULL, 60, 90, 30, 5.0, 4, 'Lote pequeño 1kg — revisar'),
           ('Suero Exfoliante BHA 2%',              'suero', NULL, 60, 90, 30, 5.0, 3, NULL),
           ('Suero RETINAL +',                      'suero', NULL, 60, 90, 30, 5.0, 3, NULL),
           ('LIMPIADOR FACIAL BHA 2%',              'limpiador', NULL, 60, 90, 30, 3.0, 2, 'Auto por umbral'),
           ('LIMPIADOR FACIAL HIDRATANTE',          'limpiador', NULL, 60, 90, 30, 3.0, 2, NULL),
           ('LIMPIADOR ILUMINADOR ACIDO KOJICO',    'limpiador', NULL, 60, 90, 30, 3.0, 2, NULL),
           ('EMULSION LIMPIADORA',                  'limpiador', NULL, 60, 90, 30, 3.0, 2, NULL),
           ('EMULSION HIDRATANTE  B3+BHA',          'hidratante', NULL, 60, 90, 30, 3.0, 2, NULL),
           ('EMULSION HIDRATANTE ANTIOXIDANTE',     'hidratante', NULL, 60, 90, 30, 3.0, 2, NULL),
           ('EMULSION HIDRATANTE ILUMINADORA',      'hidratante', NULL, 60, 90, 30, 3.0, 2, NULL),
           ('GEL HIDRATANTE',                       'hidratante', NULL, 60, 90, 30, 3.0, 2, NULL),
           ('CREMA CORPORAL RENOVA BODY',           'crema_corporal', NULL, 60, 90, 30, 3.0, 3, NULL),
           ('CREMA DE UREA',                        'crema_corporal', NULL, 60, 90, 30, 3.0, 3, NULL),
           ('CONTORNO DE OJOS MULTIPEPTIDOS',       'contorno', 60, 60, 90, 30, 5.0, 2, NULL),
           ('CONTORNO DE CAFEINA',                  'contorno', 60, 60, 90, 30, 5.0, 2, NULL),
           ('CONTORNO DE OJOS RETINALDEHIDO 0.05%', 'contorno', 60, 60, 90, 30, 5.0, 2, NULL),
           ('MAXLASH',                              'maxlash', 90, 90, 120, 60, 8.0, 4, 'Sólido — lote pequeño'),
           ('MASCARILLA HIDRATANTE',                'mascarilla', NULL, 60, 90, 30, 3.0, 4, NULL),
           ('AZ HIBRID CLEAR',                      'esencia', NULL, 60, 90, 30, 3.0, 3, NULL),
           ('ESENCIA DE CENTELLA ASIATICA',         'esencia', NULL, 60, 90, 30, 3.0, 3, NULL),
           ('ESENCIA ILUMINADORA',                  'esencia', NULL, 60, 90, 30, 3.0, 3, NULL)""",
    ]),
]


def run_migrations(conn: "sqlite3.Connection") -> int:
    """Aplica migraciones de esquema pendientes y retorna cuántas se aplicaron.

    Diseñado para ejecutarse en cada arranque de la app y en scripts de deploy.
    Seguro ante múltiples workers: el commit por migración usa el lock de SQLite
    como barrera — si dos workers arrancan simultáneamente, el segundo encontrará
    la versión ya registrada en schema_migrations y la saltará.

    Args:
        conn: Conexión SQLite activa (no necesita row_factory).

    Returns:
        Número de migraciones nuevas aplicadas en esta llamada.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     INTEGER PRIMARY KEY,
            applied_at  TEXT    NOT NULL DEFAULT (datetime('now', 'utc')),
            description TEXT    NOT NULL DEFAULT ''
        )
    """)
    conn.commit()

    applied: set[int] = {
        row[0] for row in conn.execute("SELECT version FROM schema_migrations")
    }
    applied_count = 0

    # Sebastian (30-abr-2026): hardening del runner — retries idempotentes
    # tras fallas parciales. Se silencia "ya existe" en todas sus formas
    # ("duplicate column name", "already exists", "index ... already exists")
    # para que un commit subsiguiente que vuelve a aplicar la misma migracion
    # despues de un fallo a mitad de camino pueda completarla.
    BENIGN_PATTERNS = (
        "duplicate column name",
        "already exists",
    )

    for version, description, stmts in MIGRATIONS:
        if version in applied:
            continue
        for stmt in stmts:
            try:
                conn.execute(stmt)
            except Exception as exc:
                msg = str(exc).lower()
                if not any(pat in msg for pat in BENIGN_PATTERNS):
                    raise RuntimeError(
                        f"Migración {version} falló en: {stmt!r}"
                    ) from exc
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, description) VALUES(?,?)",
            (version, description),
        )
        conn.commit()
        applied_count += 1

    return applied_count

def init_db():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS movimientos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  material_id TEXT, material_nombre TEXT, cantidad REAL,
                  tipo TEXT, fecha TEXT, observaciones TEXT,
                  lote TEXT, fecha_vencimiento TEXT, estanteria TEXT,
                  posicion TEXT, proveedor TEXT, estado_lote TEXT)""")
    for col in ["lote","fecha_vencimiento","estanteria","posicion","proveedor","estado_lote","operador"]:
        try: c.execute(f"ALTER TABLE movimientos ADD COLUMN {col} TEXT")
        except: pass
    c.execute("""CREATE TABLE IF NOT EXISTS maestro_mps
                 (codigo_mp TEXT PRIMARY KEY, nombre_inci TEXT, nombre_comercial TEXT,
                  tipo TEXT, proveedor TEXT, stock_minimo REAL DEFAULT 0, activo INTEGER DEFAULT 1)""")
    c.execute("""CREATE TABLE IF NOT EXISTS producciones
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  producto TEXT, cantidad REAL, fecha TEXT, estado TEXT, observaciones TEXT)""")
    try: c.execute("ALTER TABLE producciones ADD COLUMN operador TEXT")
    except: pass
    try: c.execute("ALTER TABLE producciones ADD COLUMN lote TEXT DEFAULT ''")
    except: pass
    try: c.execute("ALTER TABLE producciones ADD COLUMN presentacion TEXT DEFAULT ''")
    except: pass
    c.execute("""CREATE TABLE IF NOT EXISTS alertas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  material_id TEXT, material_nombre TEXT, stock_actual REAL,
                  stock_minimo REAL, fecha TEXT, estado TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS formula_headers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  producto_nombre TEXT UNIQUE, unidad_base_g REAL DEFAULT 1000,
                  descripcion TEXT, fecha_creacion TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS formula_items
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  producto_nombre TEXT, material_id TEXT,
                  material_nombre TEXT, porcentaje REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS proveedores
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nombre TEXT UNIQUE, contacto TEXT, email TEXT, telefono TEXT,
                  categoria TEXT, condiciones_pago TEXT, activo INTEGER DEFAULT 1,
                  fecha_creacion TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS ordenes_compra
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  numero_oc TEXT UNIQUE, fecha TEXT, estado TEXT DEFAULT 'Borrador',
                  proveedor TEXT, valor_total REAL DEFAULT 0,
                  observaciones TEXT, creado_por TEXT, fecha_entrega_est TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS ordenes_compra_items
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  numero_oc TEXT, codigo_mp TEXT, nombre_mp TEXT,
                  cantidad_g REAL, precio_unitario REAL DEFAULT 0, subtotal REAL DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS solicitudes_compra
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  numero TEXT UNIQUE, fecha TEXT, estado TEXT DEFAULT 'Pendiente',
                  solicitante TEXT, urgencia TEXT DEFAULT 'Normal',
                  observaciones TEXT, aprobado_por TEXT, fecha_aprobacion TEXT,
                  numero_oc TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS solicitudes_compra_items
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  numero TEXT, codigo_mp TEXT, nombre_mp TEXT,
                  cantidad_g REAL, unidad TEXT DEFAULT 'g', justificacion TEXT)""")
    # Migracion: columna area en solicitudes_compra
    try:
        c.execute("ALTER TABLE solicitudes_compra ADD COLUMN area TEXT DEFAULT 'Produccion'")
    except: pass
    # Compras redesign migrations
    for _col in [
        "categoria TEXT DEFAULT 'MP'",
        "remision_code TEXT DEFAULT ''",
        "autorizado_por TEXT DEFAULT ''",
        "fecha_autorizacion TEXT DEFAULT ''",
        "pagado_por TEXT DEFAULT ''",
        "fecha_pago TEXT DEFAULT ''",
        "fecha_recepcion TEXT DEFAULT ''"
    ]:
        try: c.execute(f"ALTER TABLE ordenes_compra ADD COLUMN {_col}")
        except: pass
    # Reception tracking columns
    for _rc in ["observaciones_recepcion TEXT DEFAULT ''", "tiene_discrepancias INTEGER DEFAULT 0"]:
        try: c.execute(f"ALTER TABLE ordenes_compra ADD COLUMN {_rc}")
        except: pass
    # IVA columns
    for _iva in ["con_iva INTEGER DEFAULT 0", "valor_sin_iva REAL DEFAULT 0"]:
        try: c.execute(f"ALTER TABLE ordenes_compra ADD COLUMN {_iva}")
        except: pass
    # Payment detail columns (comprobante image + payment method)
    for _pc in ["comprobante_imagen TEXT DEFAULT ''", "medio_pago TEXT DEFAULT ''"]:
        try: c.execute(f"ALTER TABLE ordenes_compra ADD COLUMN {_pc}")
        except: pass
    for _ri in ["estado_recepcion TEXT DEFAULT 'OK'", "notas_recepcion TEXT DEFAULT ''"]:
        try: c.execute(f"ALTER TABLE ordenes_compra_items ADD COLUMN {_ri}")
        except: pass

    try:
        c.execute("ALTER TABLE solicitudes_compra ADD COLUMN empresa TEXT DEFAULT 'Espagiria'")
    except: pass
    try:
        c.execute("ALTER TABLE solicitudes_compra ADD COLUMN categoria TEXT DEFAULT 'Materia Prima'")
    except: pass
    try:
        c.execute("ALTER TABLE solicitudes_compra ADD COLUMN tipo TEXT DEFAULT 'Compra'")
    except: pass
    try:
        c.execute("ALTER TABLE solicitudes_compra_items ADD COLUMN valor_estimado REAL DEFAULT 0")
    except: pass
    # Migracion: email del solicitante para notificaciones directas
    try:
        c.execute("ALTER TABLE solicitudes_compra ADD COLUMN email_solicitante TEXT DEFAULT ''")
    except: pass
    # Migracion: fecha en que se necesita el pedido (para priorizacion)
    try:
        c.execute("ALTER TABLE solicitudes_compra ADD COLUMN fecha_requerida TEXT DEFAULT ''")
    except: pass
    try:
        c.execute("ALTER TABLE solicitudes_compra ADD COLUMN valor REAL DEFAULT 0")
    except: pass
    try:
        c.execute("ALTER TABLE producciones ADD COLUMN presentacion TEXT DEFAULT ''")
    except: pass

    # ââ CC Review table (COC-PRO-001 digital) ââââââââââââââââââââ
    c.execute("""CREATE TABLE IF NOT EXISTS cc_reviews (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 mov_id INTEGER NOT NULL,
                 lote TEXT NOT NULL,
                 codigo_mp TEXT NOT NULL,
                 coa_ok INTEGER DEFAULT 0,
                 lote_coincide INTEGER DEFAULT 0,
                 coa_vigente INTEGER DEFAULT 0,
                 ficha_ok INTEGER DEFAULT 0,
                 solubilidad TEXT DEFAULT \'\',
                 resultado_aql TEXT DEFAULT \'\',
                 observaciones_aql TEXT DEFAULT \'\',
                 muestra_retencion INTEGER DEFAULT 0,
                 observaciones TEXT DEFAULT \'\',
                 firmante TEXT NOT NULL,
                 estado_final TEXT NOT NULL,
                 fecha TEXT DEFAULT \'\',
                 ip TEXT DEFAULT \'\')""")

    # ââ Inventario v2: costos, OC receipt, cuarentena, conteo ââââ
    for _col in [
        "precio_kg REAL DEFAULT 0",
        "numero_factura TEXT DEFAULT ''",
        "numero_oc TEXT DEFAULT ''",
        "valor_total REAL DEFAULT 0",
        "zona TEXT DEFAULT 'Almacen'",
    ]:
        try: c.execute(f"ALTER TABLE movimientos ADD COLUMN {_col}")
        except: pass
    for _col in [
        "precio_referencia REAL DEFAULT 0",
        "unidad_compra TEXT DEFAULT 'kg'",
        "lead_time_dias INTEGER DEFAULT 7",
        "ultima_act_precio TEXT DEFAULT ''",
    ]:
        try: c.execute(f"ALTER TABLE maestro_mps ADD COLUMN {_col}")
        except: pass
    for _col in [
        "fecha_recepcion TEXT DEFAULT ''",
        "recibido_por TEXT DEFAULT ''",
        "numero_factura_proveedor TEXT DEFAULT ''",
    ]:
        try: c.execute(f"ALTER TABLE ordenes_compra ADD COLUMN {_col}")
        except: pass
    for _col in [
        "precio_unitario_real REAL DEFAULT 0",
        "cantidad_recibida_g REAL DEFAULT 0",
        "lote_asignado TEXT DEFAULT ''",
    ]:
        try: c.execute(f"ALTER TABLE ordenes_compra_items ADD COLUMN {_col}")
        except: pass
    c.execute("""CREATE TABLE IF NOT EXISTS conteos_fisicos (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 numero TEXT UNIQUE,
                 fecha_inicio TEXT, fecha_cierre TEXT,
                 estado TEXT DEFAULT 'Abierto',
                 responsable TEXT DEFAULT '',
                 observaciones TEXT DEFAULT '',
                 total_items INTEGER DEFAULT 0,
                 items_diferencia INTEGER DEFAULT 0,
                 aprobado_por TEXT DEFAULT '')""")
    c.execute("""CREATE TABLE IF NOT EXISTS conteo_items (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 conteo_id INTEGER NOT NULL,
                 codigo_mp TEXT NOT NULL, nombre_mp TEXT,
                 stock_sistema REAL DEFAULT 0,
                 stock_fisico REAL DEFAULT NULL,
                 diferencia REAL DEFAULT 0,
                 lote TEXT DEFAULT '', zona TEXT DEFAULT '',
                 ajuste_aplicado INTEGER DEFAULT 0,
                 observaciones TEXT DEFAULT '')""")
    # Columnas extra para conteo ciclico con escalonamiento
    for _col in [
        "estanteria TEXT DEFAULT ''",
        "causa_diferencia TEXT DEFAULT ''",
        "valor_diferencia REAL DEFAULT 0",
        "requiere_gerencia INTEGER DEFAULT 0",
        "aprobado_gerencia INTEGER DEFAULT 0",
        "aprobado_gerencia_por TEXT DEFAULT ''",
    ]:
        try: c.execute(f"ALTER TABLE conteo_items ADD COLUMN {_col}")
        except: pass
    for _col in [
        "estanteria TEXT DEFAULT ''",
        "tipo_conteo TEXT DEFAULT 'Ciclico'",
    ]:
        try: c.execute(f"ALTER TABLE conteos_fisicos ADD COLUMN {_col}")
        except: pass

    c.execute("""CREATE TABLE IF NOT EXISTS precios_mp_historico (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 codigo_mp TEXT NOT NULL, proveedor TEXT NOT NULL,
                 precio_kg REAL NOT NULL, fecha TEXT NOT NULL,
                 numero_oc TEXT DEFAULT '', numero_factura TEXT DEFAULT '',
                 origen TEXT DEFAULT 'ingreso', observaciones TEXT DEFAULT '')""")
    c.execute("""CREATE TABLE IF NOT EXISTS maestro_mee (
        codigo TEXT PRIMARY KEY,
        descripcion TEXT NOT NULL,
        categoria TEXT DEFAULT 'Otro',
        proveedor TEXT DEFAULT '',
        fabricante TEXT DEFAULT '',
        estado TEXT DEFAULT 'Activo',
        stock_actual REAL DEFAULT 2000,
        stock_minimo REAL DEFAULT 1000,
        unidad TEXT DEFAULT 'und',
        fecha_creacion TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS movimientos_mee (
        id          INTEGER  PRIMARY KEY AUTOINCREMENT,
        mee_codigo  TEXT     NOT NULL,
        tipo        TEXT     NOT NULL CHECK(tipo IN ('Entrada','Salida','Ajuste')),
        cantidad    REAL     NOT NULL,
        unidad      TEXT     DEFAULT 'und',
        lote_ref    TEXT     DEFAULT '',
        batch_ref   TEXT     DEFAULT '',
        responsable TEXT     DEFAULT '',
        observaciones TEXT   DEFAULT '',
        fecha       DATETIME DEFAULT (datetime('now')),
        anulado     INTEGER  DEFAULT 0
    )""")
    # Seed MEE
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('TA-SPRAY-100-01','TAPA SPRAY','Tapa','Cafarcol','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('TA-PL-PU-01','PLASTIC AIRLESS PUM','Tapa','China','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('TA-PLATEADA-30-02','TAPA PLATEADA ENVASE BLANCO','Tapa','China','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('TA-PLATEADA-30-01','TAPA PLATEADA ENVASE MATE','Tapa','China','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('TA-PATO-120-01','TAPA PATO','Tapa','Cafarcol','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('SERIG-VITAC-001','suero de vitamina c+','Serigrafia','TAMPOGRAFIC','TAMPOGRAFIC','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('SERIG-TRIACTIVE-001','Triactive + NAD','Serigrafia','Mencriss','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('SERIG-RENOVAC10-001','RENOVA C10','Serigrafia','Mencriss','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('SERIG-CRETINALD-001','Contorno de retinaldehido 0.05% etiqueta blanca','Serigrafia','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('SERIG-CCAFEINA-001','Contorno de cafeina','Serigrafia','Mencriss','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('PLEG-TRX-001','Suero iluminador TRX','Plegable','Mencriss','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('PLEG-SRETINALDHIDO-001','Suero de retinaldehido 0.05%','Plegable','Mencriss','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('PLEG-SMULTIP-001','Suero multipeptidos','Plegable','Mencriss','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('PLEG-SAH-001','Suero hidratantre AH 1.5&','Plegable','Mencriss','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('PLEG-RETINAL-001','Suero retinal +','Plegable','Mencriss','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('PLEG-PHA-001','suero exfoliante PHA','Plegable','Mencriss','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('PLEG-NIA-001','Suero de niacinamida 5%','Plegable','Mencriss','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('PLEG-MAXLASH-001','Maxlash','Plegable','Mencriss','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('PLEG-BHA-001','Suero exfoliante BHA 2%','Plegable','Mencriss','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('PLEG-AZ+B3-001','Suero AZ+B3','Plegable','Mencriss','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('GO-BLANCO-89-01','GOTERO BLANCO 89mm','Gotero','Mencriss','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('GO-BLANCO-72-01','GOTERO BLANCO 72mm','Gotero','Mencriss','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('GO-BLANCO-55-01','GOTERO BLANCO 55mm','Gotero','Mencriss','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('FR-NE-PL-050-1','PLASTIC JAR 50ml','Frasco','China','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-UREA-001','Crema hidratante de urea 10%','Etiqueta','Cafarcol','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-TRX-001','Suero iluminador TRX con lote y fv sep','Etiqueta','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-SRET-001','Suero de retinaldehido 0.05%','Etiqueta','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-SNIA-001','Suero de niacinamida 5%','Etiqueta','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-SMULTIP-001','Suero multipeptidos','Etiqueta','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-SHIDRAH-001','Suero hidratante AH 1.5%','Etiqueta','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-SBHA-001','Suero exfoliente BHA 2%','Etiqueta','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-SAH-001','Suero hidratante AH 1.5% con f.v y lote','Etiqueta','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-RBODY-001','Crema corporal renova body','Etiqueta','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-LKJ-001','Limpiador iluminador acido kojico','Etiqueta','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-LIMPBHA-001','Limpiador facial BHA 2%','Etiqueta','Pacto','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-LAH-001','Etiqueta limpiador facial hidratante','Etiqueta','Megavisual','Megavisual','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-GHIDRAT-001','Gel hidratante','Etiqueta','Pacto','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-EMLIMPANT-001','Emulsion hidratante antioxidantwe','Etiqueta','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-EMLIMP-001','Emulsion limpiadora','Etiqueta','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-EILUM-001','Esencia iluminadora','Etiqueta','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-CCENT-001','esencia de centella asiatica','Etiqueta','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-CCAFEINA-001','contorno de cafeina','Etiqueta','Pacto','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-B3+BHA-002','Emulsion hidratante B3+BHA','Etiqueta','Pacto','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-B3+BHA-001','Emulsion hidratante B3+BHA','Etiqueta','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-AZ+B3-001','Suero AZ + B3','Etiqueta','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ETIQ-AHA+AH-001','Suero iluminador AHA+AH','Etiqueta','Megavisual','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-TRX-025','ENVASE TRX SERIGRAFIA','Envase','China','GUANGZHOU','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-SMUL-027','ENVASE SUERO MULTIPEPTIDOS','Envase','China','CHINA','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-OPAL-30-01','ENVASE OPALIZADO','Envase','Cafarcol','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-NIA-026','ENVASE NIACINAMIDA SERIGRAFIA','Envase','China','GUANGZHOU JIAXING GLASS','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-NEG-30-SLOGO-01','ENVASE NEGRO MATE SIN LOGO','Envase','China','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-NEG-30-LOGO-01','ENVASE NEGRO MATE  LOGO','Envase','China','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-NEG-10-01','ENVASE NEGRO 10mL','Envase','Cafarcol','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-NEG-100-01','ENVASE NEGRO 100mL','Envase','Cafarcol','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-GOT-006','GOTERO 65mm','Envase','Mencriss','mencriss','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-COLGLOSS-15-01','Envase colapsible de 15 ml','Envase','China','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-BTAP-038','PLASTIC BOTTLE','Envase','China','GUANGZHOU','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-BLAN-LBHA-150','ENVASE BLANCO TAPA DISC TOP 150 ml','Envase','China','HEBEI YAYOUJIA PACKAGING','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-AZUL-10-01','ENVASE AZUL mL','Envase','Cafarcol','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-AMBAR-50-01','ENVASE AMBAR A 18 50mL','Envase','Cafarcol','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-AMBAR-30-01','ENVASE AMBAR 30mL','Envase','Cafarcol','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-AMBAR-120-01','ENVASE AMBAR 125mL','Envase','Cafarcol','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-AMBAR-10-01','ENVASE AMBAR 10mL','Envase','Cafarcol','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-AMB-10','ENVASE AMBAR 10ml','Envase','Cafarcol','N.A','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-30-PET-01','ENVASE CUADRADO 30mL','Envase','China','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('ENV-15-PET-01','ENVASE CUADRADO 15mL','Envase','China','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('EMP-ETIQ-021','ETIQUETA SUERO ILUMINADOR TRX','Etiqueta','Mencriss','MENCRISS','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('CONT-LIKARILESS-15-01','LIK AIRLESS X 15ML BL CONTORNO PUNTA ZINC PLTA','Contorno','Cafarcol','China','Activo',2000,1000,'und',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion) VALUES ('CA-PL-PU-01','PLASTIC CAP','Tapa','China','China','Activo',2000,1000,'und',datetime('now'))")


    # ââ audit_log (Capa 0) ââââââââââââââââââââââââââââââââââââââââââââââââ
    c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 usuario TEXT, accion TEXT, tabla TEXT, registro_id TEXT,
                 detalle TEXT, ip TEXT, fecha TEXT)""")

    # ââ Clientes + Producto Terminado (Capa 2) ââââââââââââââââââââââââââââ
    c.execute("""CREATE TABLE IF NOT EXISTS clientes (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 codigo TEXT UNIQUE, nombre TEXT NOT NULL,
                 empresa TEXT DEFAULT 'ANIMUS', tipo TEXT DEFAULT 'Distribuidor',
                 contacto TEXT DEFAULT '', email TEXT DEFAULT '',
                 telefono TEXT DEFAULT '', nit TEXT DEFAULT '',
                 condiciones_pago TEXT DEFAULT '30 dias', descuento_pct REAL DEFAULT 0,
                 activo INTEGER DEFAULT 1, fecha_creacion TEXT, observaciones TEXT DEFAULT '')""")
    c.execute("""CREATE TABLE IF NOT EXISTS pedidos (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 numero TEXT UNIQUE, cliente_id INTEGER REFERENCES clientes(id),
                 fecha TEXT, fecha_entrega_est TEXT, estado TEXT DEFAULT 'Confirmado',
                 empresa TEXT DEFAULT 'ANIMUS', valor_total REAL DEFAULT 0,
                 observaciones TEXT DEFAULT '', creado_por TEXT DEFAULT '',
                 fecha_despacho TEXT DEFAULT '', numero_factura TEXT DEFAULT '')""")
    c.execute("""CREATE TABLE IF NOT EXISTS pedidos_items (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 numero_pedido TEXT, sku TEXT, descripcion TEXT,
                 cantidad INTEGER DEFAULT 0, precio_unitario REAL DEFAULT 0,
                 subtotal REAL DEFAULT 0, lote_pt TEXT DEFAULT '')""")
    c.execute("""CREATE TABLE IF NOT EXISTS stock_pt (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 sku TEXT NOT NULL, descripcion TEXT DEFAULT '',
                 lote_produccion TEXT DEFAULT '', fecha_produccion TEXT,
                 unidades_inicial INTEGER DEFAULT 0, unidades_disponible INTEGER DEFAULT 0,
                 precio_base REAL DEFAULT 0, empresa TEXT DEFAULT 'ANIMUS',
                 estado TEXT DEFAULT 'Disponible', observaciones TEXT DEFAULT '')""")
    c.execute("""CREATE TABLE IF NOT EXISTS despachos (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 numero TEXT UNIQUE, numero_pedido TEXT DEFAULT '',
                 cliente_id INTEGER, fecha TEXT, operador TEXT DEFAULT '',
                 observaciones TEXT DEFAULT '', estado TEXT DEFAULT 'Completado')""")
    c.execute("""CREATE TABLE IF NOT EXISTS despachos_items (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 numero_despacho TEXT, sku TEXT, descripcion TEXT,
                 lote_pt TEXT, cantidad INTEGER DEFAULT 0, precio_unitario REAL DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS gerencia_inputs (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, periodo TEXT UNIQUE,
                 saldo_caja REAL DEFAULT 0, ingresos_animus REAL DEFAULT 0,
                 ingresos_maquila REAL DEFAULT 0, notas TEXT DEFAULT '', fecha TEXT)""")

    # ââ ANIMUS PT reorder + recall ââââââââââââââââââââââââââââââââââââââ
    # ── Aliados: nivel + semáforo ────────────────────────────────────
    try: c.execute("ALTER TABLE clientes ADD COLUMN nivel_aliado TEXT DEFAULT 'Ingreso'")
    except: pass
    try: c.execute("ALTER TABLE clientes ADD COLUMN semaforo TEXT DEFAULT 'verde'")
    except: pass
    try: c.execute("ALTER TABLE clientes ADD COLUMN fecha_vinculacion TEXT DEFAULT ''")
    except: pass
    try: c.execute("ALTER TABLE clientes ADD COLUMN ciudad TEXT DEFAULT ''")
    except: pass
    try: c.execute("ALTER TABLE pedidos ADD COLUMN monto_pagado REAL DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE pedidos ADD COLUMN estado_pago TEXT DEFAULT 'Pendiente'")
    except: pass
    # ── Aliados: campos de seguimiento Valentina ─────────────────────────────
    try: c.execute("ALTER TABLE clientes ADD COLUMN categoria_profesional TEXT DEFAULT ''")
    except: pass
    try: c.execute("ALTER TABLE clientes ADD COLUMN canal_captacion TEXT DEFAULT ''")
    except: pass
    try: c.execute("ALTER TABLE clientes ADD COLUMN redes_sociales TEXT DEFAULT '{}'")
    except: pass
    try: c.execute("ALTER TABLE clientes ADD COLUMN notas_seguimiento TEXT DEFAULT ''")
    except: pass
    # Desactivar ghost aliados seeded incorrectamente (ANIMUS Lab interno + seed placeholder)
    try: c.execute("UPDATE clientes SET activo=0 WHERE codigo IN ('CLI-001','CLI-002') AND empresa='ANIMUS'")
    except: pass
    try: c.execute("ALTER TABLE stock_pt ADD COLUMN stock_minimo_ud INTEGER DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE stock_pt ADD COLUMN dias_reposicion INTEGER DEFAULT 15")
    except: pass
    c.execute("""CREATE TABLE IF NOT EXISTS solicitudes_produccion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT NOT NULL, descripcion TEXT DEFAULT '',
        unidades_solicitadas INTEGER DEFAULT 0,
        motivo TEXT DEFAULT 'Stock bajo',
        estado TEXT DEFAULT 'Pendiente',
        prioridad TEXT DEFAULT 'Normal',
        fecha_solicitud TEXT DEFAULT (date('now')),
        fecha_requerida TEXT DEFAULT '',
        solicitado_por TEXT DEFAULT 'sistema',
        observaciones TEXT DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS recall_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lote_pt TEXT NOT NULL,
        sku TEXT, motivo TEXT,
        total_despachos INTEGER DEFAULT 0,
        total_unidades INTEGER DEFAULT 0,
        fecha_recall TEXT DEFAULT (datetime('now')),
        ejecutado_por TEXT,
        estado TEXT DEFAULT 'Simulacion'
    )""")
    # ââ Financiero (Capa 4) ââââââââââââââââââââââââââââââââââââââââââ
    c.execute("""CREATE TABLE IF NOT EXISTS flujo_ingresos (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 fecha TEXT, empresa TEXT DEFAULT 'HHA',
                 concepto TEXT NOT NULL, categoria TEXT DEFAULT 'Ventas',
                 monto REAL DEFAULT 0, periodo TEXT,
                 fuente TEXT DEFAULT 'manual', referencia TEXT DEFAULT '',
                 creado_por TEXT DEFAULT '', observaciones TEXT DEFAULT '')""")
    c.execute("""CREATE TABLE IF NOT EXISTS flujo_egresos (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 fecha TEXT, empresa TEXT DEFAULT 'HHA',
                 concepto TEXT NOT NULL, categoria TEXT DEFAULT 'MPs',
                 monto REAL DEFAULT 0, periodo TEXT,
                 fuente TEXT DEFAULT 'manual', referencia TEXT DEFAULT '',
                 creado_por TEXT DEFAULT '', observaciones TEXT DEFAULT '')""")
    c.execute("""CREATE TABLE IF NOT EXISTS flujo_config (
                 clave TEXT PRIMARY KEY, valor TEXT, descripcion TEXT)""")
    # Seed config supuestos
    configs = [
        ('trm_usd', '4100', 'TRM COP/USD'),
        ('meta_caja_min', '50000000', 'Saldo mÃ­nimo de caja alerta (COP)'),
        ('cmv_pct_animus', '35', 'CMV % objetivo ÃNIMUS Lab'),
        ('cmv_pct_espagiria', '40', 'CMV % objetivo Espagiria'),
        ('nomina_mensual', '15000000', 'NÃ³mina mensual estimada HHA Group (COP)'),
    ]
    for clave, valor, desc in configs:
        c.execute("INSERT OR IGNORE INTO flujo_config (clave,valor,descripcion) VALUES (?,?,?)", (clave, valor, desc))

    # ââ SKUs Fernando Mesa con precios mayorista ââââââââââââââââââ
    c.execute("""CREATE TABLE IF NOT EXISTS sku_precios (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 sku TEXT NOT NULL, descripcion TEXT,
                 precio_base REAL DEFAULT 0,
                 precio_mayorista REAL DEFAULT 0,
                 unidad TEXT DEFAULT 'unidad',
                 empresa TEXT DEFAULT 'ANIMUS',
                 activo INTEGER DEFAULT 1)""")
    fm_skus = [
        ('LBHA-30', 'Limpiador Balanceador HA 30ml', 42000, 29400, 'unidad'),
        ('TRX-15', 'Tonico Reparador 15ml', 38000, 26600, 'unidad'),
        ('NIAC-30', 'Serum Niacinamida 30ml', 55000, 38500, 'unidad'),
        ('AZHC-30', 'Serum AZ+HC 30ml', 52000, 36400, 'unidad'),
        ('SBHA-30', 'Serum Salicilico BHA 30ml', 48000, 33600, 'unidad'),
        ('ECEN-30', 'Serum Encapsulado Centella 30ml', 58000, 40600, 'unidad'),
        ('EILU-30', 'Emulsion Iluminadora 30ml', 45000, 31500, 'unidad'),
        ('CUREA-50', 'Crema Urea 50ml', 40000, 28000, 'unidad'),
        ('GELH-120', 'Gel Hidratante 120ml', 35000, 24500, 'unidad'),
    ]
    for sku, desc, precio, mayorista, unidad in fm_skus:
        c.execute("INSERT OR IGNORE INTO sku_precios (sku,descripcion,precio_base,precio_mayorista,unidad,empresa) VALUES (?,?,?,?,?,?)",
                  (sku, desc, precio, mayorista, unidad, 'ANIMUS'))

    # Seed clientes iniciales
    c.execute("""INSERT OR IGNORE INTO clientes
                 (codigo,nombre,empresa,tipo,contacto,email,condiciones_pago,descuento_pct,fecha_creacion)
                 VALUES
                 ('CLI-001','ANIMUS Lab','Espagiria','Maquila','Sebastian Vargas',
                  'sebastianvargasisaza@gmail.com','Inmediato',0,datetime('now')),
                 ('CLI-002','Fernando Mesa','Espagiria','Maquila','Fernando Mesa',
                  '','30 dias',0,datetime('now'))""")
    # Ensure seeded clients are always active + in correct empresa
    c.execute("UPDATE clientes SET activo=1, empresa='Espagiria', tipo='Maquila' WHERE codigo IN ('CLI-001','CLI-002')")

    # ââ MAQUILA 360 ââââââââââââââââââââââââââââââââââââââââââââââ
    c.execute("""CREATE TABLE IF NOT EXISTS maquila_prospectos (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 numero_brief TEXT DEFAULT '',
                 fecha TEXT, kam TEXT DEFAULT '',
                 empresa TEXT NOT NULL, contacto TEXT DEFAULT '',
                 cargo TEXT DEFAULT '', whatsapp TEXT DEFAULT '',
                 email TEXT DEFAULT '', ciudad TEXT DEFAULT '',
                 canal_origen TEXT DEFAULT '',
                 categoria_producto TEXT DEFAULT '',
                 descripcion_producto TEXT DEFAULT '',
                 claims TEXT DEFAULT '',
                 restricciones TEXT DEFAULT '',
                 estado_formula TEXT DEFAULT 'Sin formular',
                 volumen_lote TEXT DEFAULT '',
                 frecuencia TEXT DEFAULT '',
                 empaque TEXT DEFAULT '',
                 mercado TEXT DEFAULT 'Nacional',
                 nso TEXT DEFAULT 'No tiene',
                 presupuesto TEXT DEFAULT '',
                 etapa TEXT DEFAULT 'Contacto',
                 nivel_recomendado TEXT DEFAULT '',
                 viabilidad TEXT DEFAULT '',
                 riesgos TEXT DEFAULT '',
                 valor_estimado_lote REAL DEFAULT 0,
                 ticket_mes REAL DEFAULT 0,
                 proxima_accion TEXT DEFAULT '',
                 observaciones TEXT DEFAULT '',
                 estado TEXT DEFAULT 'Activo',
                 creado_por TEXT DEFAULT '',
                 fecha_creacion TEXT DEFAULT (datetime('now')))""")
    for _col in [
        "es_incubacion INTEGER DEFAULT 0",
        "nivel_servicio TEXT DEFAULT ''",
        "kam_asignado TEXT DEFAULT 'Luz'",
        "contacto_referido TEXT DEFAULT ''",
    ]:
        try: c.execute(f"ALTER TABLE maquila_prospectos ADD COLUMN {_col}")
        except: pass

    # Seed real maquila clients
    c.execute("""INSERT OR IGNORE INTO maquila_prospectos
        (id, empresa, contacto, email, whatsapp, etapa, nivel_servicio,
         kam_asignado, categoria_producto, observaciones, valor_estimado_lote,
         ticket_mes, es_incubacion, estado, fecha_creacion)
        VALUES
        (1, 'Kelly Guerra', 'Kelly Guerra', '', '', 'Orden',
         'Asistida', 'Luz', 'Skincare - Hidratacion y cuidado facial',
         'Contacto referido: Fernando Mesa (esposo). Cliente activa de maquila.',
         500000, 2000000, 0, 'Activo', '2026-04-18'),
        (2, 'Camila & Chomim', 'Camila', '', '', 'Contacto',
         'Operativa', 'Luz', 'Skincare - Corrector ojeras, Serum, Limpiador',
         'Programa incubacion. Emprendedoras con audiencia digital. Sin capital de arranque.',
         300000, 900000, 1, 'Activo', '2026-04-23')""")
    # Update Fernando Mesa to be contact reference for Kelly's project
    c.execute("UPDATE clientes SET observaciones='Contacto del cliente Kelly Guerra (esposo). La clienta de maquila es Kelly Guerra.' WHERE codigo='CLI-002'")


    c.execute("""CREATE TABLE IF NOT EXISTS maquila_ordenes (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 numero TEXT UNIQUE,
                 prospecto_id INTEGER,
                 cliente_nombre TEXT NOT NULL,
                 producto TEXT NOT NULL,
                 categoria TEXT DEFAULT '',
                 formato_ml REAL DEFAULT 30,
                 lote_kg REAL DEFAULT 30,
                 unidades_lote REAL DEFAULT 1000,
                 costo_mp_kg REAL DEFAULT 0,
                 costo_envase_ud REAL DEFAULT 2000,
                 dias_acondicionamiento INTEGER DEFAULT 1,
                 costo_mo_lote REAL DEFAULT 0,
                 cf_prorateados REAL DEFAULT 0,
                 costo_micro REAL DEFAULT 2000000,
                 costo_total_lote REAL DEFAULT 0,
                 costo_por_unidad REAL DEFAULT 0,
                 margen REAL DEFAULT 0.35,
                 precio_ud REAL DEFAULT 0,
                 precio_lote REAL DEFAULT 0,
                 estado TEXT DEFAULT 'Cotizacion',
                 fecha_orden TEXT,
                 fecha_entrega_est TEXT DEFAULT '',
                 fecha_entrega_real TEXT DEFAULT '',
                 facturado INTEGER DEFAULT 0,
                 monto_facturado REAL DEFAULT 0,
                 fecha_factura TEXT DEFAULT '',
                 observaciones TEXT DEFAULT '',
                 creado_por TEXT DEFAULT '',
                 fecha_creacion TEXT DEFAULT (datetime('now')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS maquila_ingredientes (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 orden_id INTEGER NOT NULL,
                 ingrediente TEXT NOT NULL,
                 porcentaje REAL DEFAULT 0,
                 precio_mp_kg REAL DEFAULT 0,
                 aporte_kg REAL DEFAULT 0)""")
    maquila_configs = [
        ('maquila_nomina_mes', '39100000', 'Nomina produccion directa Espagiria/mes'),
        ('maquila_dias_lab', '22', 'Dias laborales por mes'),
        ('maquila_cf_lote', '998742', 'CF operativos prorateados por lote (COP)'),
        ('maquila_micro', '2000000', 'Costo microbiologia estandar por lote (COP)'),
        ('maquila_margen', '0.35', 'Margen Espagiria 35%'),
        ('maquila_trm', '4200', 'TRM COP/USD'),
        ('maquila_envase_basico', '2000', 'Costo envase basico/ud (COP)'),
    ]
    for clave, valor, desc in maquila_configs:
        c.execute("INSERT OR IGNORE INTO flujo_config (clave,valor,descripcion) VALUES (?,?,?)", (clave, valor, desc))

    # maquila_prospectos y maquila_ordenes definidas arriba en el bloque MAQUILA 360.
    # Segunda definicion eliminada (schema incompleto, IF NOT EXISTS garantiza que
    # la primera definicion con schema completo siempre prevalece en produccion).
    c.execute("""CREATE TABLE IF NOT EXISTS empleados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE, nombre TEXT, apellido TEXT, cedula TEXT UNIQUE,
        cargo TEXT, area TEXT, empresa TEXT DEFAULT 'Espagiria',
        tipo_contrato TEXT DEFAULT 'Indefinido', fecha_ingreso TEXT,
        fecha_fin_contrato TEXT, estado TEXT DEFAULT 'Activo',
        salario_base REAL DEFAULT 0, eps TEXT, afp TEXT, arl TEXT,
        caja_compensacion TEXT, email TEXT, telefono TEXT,
        nivel_riesgo INTEGER DEFAULT 1, observaciones TEXT,
        creado_en TEXT DEFAULT (datetime('now')))""")
    for _col in ["banco TEXT DEFAULT NULL","numero_cuenta TEXT DEFAULT NULL","tipo_cuenta TEXT DEFAULT NULL"]:
        try: c.execute(f"ALTER TABLE empleados ADD COLUMN {_col}")
        except: pass
    c.execute("""CREATE TABLE IF NOT EXISTS nomina_registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        periodo TEXT, empleado_id INTEGER, salario_base REAL,
        dias_trabajados INTEGER DEFAULT 30, horas_extras REAL DEFAULT 0,
        valor_horas_extras REAL DEFAULT 0, subsidio_transporte REAL DEFAULT 0,
        bonificaciones REAL DEFAULT 0, descuento_salud REAL DEFAULT 0,
        descuento_pension REAL DEFAULT 0, otros_descuentos REAL DEFAULT 0,
        salario_neto REAL DEFAULT 0, estado TEXT DEFAULT 'Generada',
        UNIQUE(periodo,empleado_id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS ausencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empleado_id INTEGER, tipo TEXT, fecha_inicio TEXT, fecha_fin TEXT,
        dias INTEGER DEFAULT 0, estado TEXT DEFAULT 'Pendiente',
        observaciones TEXT, aprobado_por TEXT,
        creado_en TEXT DEFAULT (datetime('now')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS capacitaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, tipo TEXT, fecha TEXT, duracion_horas REAL DEFAULT 1,
        instructor TEXT, empresa TEXT, obligatoria INTEGER DEFAULT 0,
        creado_en TEXT DEFAULT (datetime('now')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS capacitaciones_empleados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        capacitacion_id INTEGER, empleado_id INTEGER,
        completado INTEGER DEFAULT 0, fecha_completado TEXT, calificacion REAL,
        UNIQUE(capacitacion_id,empleado_id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS evaluaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empleado_id INTEGER, periodo TEXT, evaluador TEXT,
        puntaje_total REAL, puntaje_calidad REAL, puntaje_asistencia REAL,
        puntaje_actitud REAL, puntaje_conocimiento REAL,
        puntaje_productividad REAL, comentarios TEXT,
        estado TEXT DEFAULT 'Borrador',
        creado_en TEXT DEFAULT (datetime('now')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS sgsst_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria TEXT, descripcion TEXT, frecuencia TEXT DEFAULT 'Anual',
        ultimo_cumplimiento TEXT, proximo_vencimiento TEXT,
        responsable TEXT, estado TEXT DEFAULT 'Pendiente',
        creado_en TEXT DEFAULT (datetime('now')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS security_events (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 ts        TEXT NOT NULL,
                 event     TEXT NOT NULL,
                 username  TEXT,
                 ip        TEXT,
                 user_agent TEXT,
                 details   TEXT)""")
    # ââ Calidad BPM Digital â tablas ââââââââââââââââââââââââââââââââââââââ
    c.execute("""CREATE TABLE IF NOT EXISTS no_conformidades (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 fecha TEXT NOT NULL,
                 tipo TEXT DEFAULT 'MP',
                 descripcion TEXT NOT NULL,
                 area TEXT DEFAULT 'Produccion',
                 responsable TEXT DEFAULT '',
                 lote TEXT DEFAULT '',
                 codigo_mp TEXT DEFAULT '',
                 impacto TEXT DEFAULT 'Menor',
                 accion_correctiva TEXT DEFAULT '',
                 estado TEXT DEFAULT 'Abierta',
                 fecha_cierre TEXT DEFAULT '',
                 cerrado_por TEXT DEFAULT '',
                 creado_por TEXT DEFAULT '')""")
    c.execute("""CREATE TABLE IF NOT EXISTS calibraciones (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 instrumento TEXT NOT NULL,
                 codigo TEXT DEFAULT '',
                 ubicacion TEXT DEFAULT '',
                 fecha_ultima TEXT DEFAULT '',
                 fecha_proxima TEXT NOT NULL,
                 responsable TEXT DEFAULT '',
                 empresa TEXT DEFAULT '',
                 estado TEXT DEFAULT 'Pendiente',
                 certificado TEXT DEFAULT '',
                 observaciones TEXT DEFAULT '')""")
    # Seed calibraciones si no existen
    c.execute("SELECT COUNT(*) FROM calibraciones")
    if c.fetchone()[0] == 0:
        _cals = [
            ('Balanza analitica principal', 'BAL-001', 'Lab Calidad', '2026-01-15', '2026-07-15', 'Catalina Torres', 'Espagiria', 'Vigente'),
            ('Balanza de conteo', 'BAL-002', 'Produccion', '2026-01-15', '2026-07-15', 'Catalina Torres', 'Espagiria', 'Vigente'),
            ('Viscosimetro Brookfield', 'VISC-001', 'Lab Calidad', '2025-10-01', '2026-04-01', 'Catalina Torres', 'Espagiria', 'Vencida'),
            ('pH-metro digital', 'PH-001', 'Lab Calidad', '2026-02-01', '2026-08-01', 'Catalina Torres', 'Espagiria', 'Vigente'),
            ('Termometro digital', 'TERM-001', 'Almacen MP', '2026-01-10', '2027-01-10', 'Alejandro Guzman', 'Espagiria', 'Vigente'),
        ]
        for cal in _cals:
            try:
                c.execute("INSERT INTO calibraciones (instrumento,codigo,ubicacion,fecha_ultima,fecha_proxima,responsable,empresa,estado) VALUES (?,?,?,?,?,?,?,?)", cal)
            except Exception: pass

    # ââ MIGRACIÃN: ampliar schema proveedores ââââââââââââââââââââââââââââââ
    for _pc in ['nit TEXT','id_interno TEXT','direccion TEXT',
                'num_cuenta TEXT','tipo_cuenta TEXT','banco TEXT','cert_bancario TEXT',
                'estado_lpa TEXT','ultima_evaluacion TEXT','vencimiento_docs TEXT',
                'acuerdo_calidad TEXT','rut INTEGER DEFAULT 0','camara_comercio INTEGER DEFAULT 0',
                'concepto_compra TEXT','motivo_baja TEXT','fecha_baja TEXT']:
        try: c.execute(f'ALTER TABLE proveedores ADD COLUMN {_pc}')
        except Exception: pass

    # ââ SEED: 67 proveedores del Listado Oficial ââââââââââââââââââââââââââââ
    _provs = [{'nombre': 'PRESQUIM SAS', 'nit': '800.167.047-5', 'direccion': 'Carrera 13 NÂ° 90 â 36 Of. 702 bogota', 'telefono': '318 4155087', 'correo': 'ventas1@presquim.com', 'contacto': 'ANDRES PAVA', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '473469991912', 'tipo_cuenta': 'CORRIENTE', 'banco': 'DAVIVIENDA', 'cert_bancario': None, 'id_interno': 'PROV-001', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-10-20', 'venc_docs': None, 'acuerdo_calidad': 'â Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'MEGA DISTRIBUCIONES', 'nit': '1130665584', 'direccion': 'Carrera 3 # 12-59 Pereira Risaralda', 'telefono': '320 4126407', 'correo': 'contactenos@megadistribuciones.co', 'contacto': 'VALENTINA', 'concepto': 'INSUMOS DE EPP', 'num_cuenta': '127300065852', 'tipo_cuenta': 'AHORROS DAMAS', 'banco': 'DAVIVIENDA', 'cert_bancario': None, 'id_interno': 'PROV-002', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-09', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'VARIEDADES E IMPORTACIONES', 'nit': '901675287', 'direccion': 'calle 13 paso ancho # 43-52', 'telefono': '300 4649945', 'correo': 'ROBINSONSOLI12@GMAIL.COM', 'contacto': 'ROBINSON', 'concepto': 'MATERIAL DE ENVASE', 'num_cuenta': '20500004705', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-003', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-05-16', 'venc_docs': None, 'acuerdo_calidad': 'â Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'ALEJANDRO GIRALDO TORREZ (MEGA VISUAL)', 'nit': '1107097226', 'direccion': 'Cra. 4 #18-69, COMUNA 3, Cali, Valle del Cauca', 'telefono': '317 5168170', 'correo': 'alejandrogiraldotorrez@gmail.com', 'contacto': 'BRAYAN', 'concepto': 'ACONDICIONAMIENTO', 'num_cuenta': '73605958351', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-004', 'categoria': 'ð  Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-11-17', 'venc_docs': None, 'acuerdo_calidad': 'â Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'AGENQUIMICOS', 'nit': '800032931', 'direccion': 'calle 18 # 5-60 b/ san nicolas', 'telefono': '322 6815561', 'correo': 'venta4@agenquimicos.com', 'contacto': 'ERIKA CARDONA', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '062-032931-00', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-005', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-21', 'venc_docs': None, 'acuerdo_calidad': 'â³ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'EVACOL SAS', 'nit': '900062992', 'direccion': 'CR 23 13 40 Y 13 100 BRR ARROYOHONDO', 'telefono': '310 2102738', 'correo': 'jgerentecontabilidad@evacol.com', 'contacto': 'LILIANA', 'concepto': 'ZAPATOS', 'num_cuenta': '80327543789', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-006', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-11', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'LIMPIASEO DISTRIBUCIONES CALI SAS', 'nit': '901285074', 'direccion': 'Calle 7 # 25-05 Barrio el Cedro', 'telefono': '314 6819571', 'correo': 'limpiaseodistribuciones@hotmail.com', 'contacto': 'BAYRON JANSANSOY', 'concepto': 'ASEO', 'num_cuenta': '75000000844', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-007', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-07', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'CFC CAFARCOL SAS', 'nit': '860047379', 'direccion': 'calle 13 paso ancho # 43-52', 'telefono': '300 4649945', 'correo': 'cali@mencris.com', 'contacto': 'ROBINSON', 'concepto': 'MATERIAL DE ENVASE 2', 'num_cuenta': '23791226921', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-008', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-16', 'venc_docs': None, 'acuerdo_calidad': 'â Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'TWO GLASS SAS BIC', 'nit': '9018126525', 'direccion': 'Calle 13 # 27a - 05', 'telefono': '305 4591891', 'correo': 'twoglasssitioweb@gmail.com', 'contacto': 'ANGELICA ALEJO', 'concepto': 'ACONDICIONAMIENTO SERIGRAFIA', 'num_cuenta': '24136806040', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCO CAJA SOCIAL', 'cert_bancario': None, 'id_interno': 'PROV-009', 'categoria': 'ð  Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-11-14', 'venc_docs': None, 'acuerdo_calidad': 'â³ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'PACTO IMPRESOS SAS', 'nit': '901131621', 'direccion': 'Calle 45 NÂ° 2N - 68', 'telefono': '318 4905322', 'correo': 'Comercial@pactoimpresores.com', 'contacto': 'CAROLINA VELEZ', 'concepto': 'ACONDICIONAMIENTO', 'num_cuenta': '06200005487', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-010', 'categoria': 'ð  Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-05', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'MICROLAB', 'nit': '805019040', 'direccion': 'AV 2 G NORTE 51 N 71 BRR LA MERCED', 'telefono': '320 6802368', 'correo': 'impuestosmicrolab@gmail.com', 'contacto': None, 'concepto': 'ANALISIS MICROBIOLOGICOS', 'num_cuenta': '83600003511', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-011', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-10-30', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'SOS NATURAL COLOMBIA SAS', 'nit': '901587640', 'direccion': 'FINCA MIS ANOS DORADOS VEREDA EL HOGAR', 'telefono': '314 3751521', 'correo': 'info.sosnatural@gmail.com', 'contacto': 'ANDREA', 'concepto': 'MATERIA PRIMA VERDE ARMONIA', 'num_cuenta': '06400003041', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-012', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-11-17', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'TIENDA HAIKU', 'nit': '900983721', 'direccion': 'Cra 58 # 169a - 55 LC 131 bogota', 'telefono': '314 2229116', 'correo': 'ventas@tiendahaiku.com', 'contacto': None, 'concepto': 'MATERIA PRIMA VERDE ARMONIA Y PRODUCCION AGOSTO', 'num_cuenta': '22300007095', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-013', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-09-26', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'ALARMAR LTDA', 'nit': '8909192674', 'direccion': 'CALLE 24 N  8N-10', 'telefono': '3168781340', 'correo': 'angele.padilla@alarmar.com.co', 'contacto': 'ANGELE PADILLA', 'concepto': 'ALARMA', 'num_cuenta': '391437829', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCO DE BOGOTA', 'cert_bancario': None, 'id_interno': 'PROV-014', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-02', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'POCHTECA COLOMBIA', 'nit': '900161367', 'direccion': 'CRA 19 # 82 - 85 OFICINA 305', 'telefono': '3123799010', 'correo': 'mcardenasm@pochteca.net', 'contacto': 'JOHANA', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '69935569787', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-015', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-10-08', 'venc_docs': None, 'acuerdo_calidad': 'â³ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'SUMINISTROS DE LABORATORIO KASALAB S.A.S', 'nit': '900745087', 'direccion': 'Cra. 1 No. 49-35', 'telefono': '317 4961234', 'correo': 'brianobregon@kasalab.com', 'contacto': 'BRIAN STIVEN OBREGON MEJIA', 'concepto': 'MORTEROS', 'num_cuenta': '27427058846', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-016', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-26', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'ANA MARISOL SALDARRIAGA (LIDER DISTRIBUCIONES)', 'nit': '66870504', 'direccion': 'CALLE 23  31  39 BARRIO SANTA MONICA', 'telefono': '3206641705', 'correo': 'liderdistribucionescali@gmail.com', 'contacto': 'Ana', 'concepto': 'ENVASES', 'num_cuenta': '06501042995', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-017', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-05-19', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'COMPAÃIA COLOMBIANA DE QUIMICOS', 'nit': '860049957', 'direccion': 'CALLE 12  38-62 BOGOTA', 'telefono': '321 4903630', 'correo': 'nicolle.villamil@colquimicos.com', 'contacto': 'NICOLLE VILLAMIL', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '03100057271', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-018', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-02', 'venc_docs': None, 'acuerdo_calidad': 'â Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'CHEMY JAM COLOMBIA SAS', 'nit': '901180048', 'direccion': 'Calle 1C 40D79Bogota', 'telefono': '310 2180922', 'correo': 'chemy.jamcol@gmail.com', 'contacto': 'Alexandra', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '046101192', 'tipo_cuenta': 'AHORROS', 'banco': 'AV VILLAS', 'cert_bancario': None, 'id_interno': 'PROV-019', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-04', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'YANETH VARGAS RUEDA', 'nit': '66777565', 'direccion': 'KR 1 #32', 'telefono': '313 6864461', 'correo': 'qf.yanethvargasrueda@gmail.com', 'contacto': 'YANETH VARGAS RUEDA', 'concepto': 'INSPECCIONES', 'num_cuenta': '103848813', 'tipo_cuenta': 'AHORROS', 'banco': 'AV VILLAS', 'cert_bancario': None, 'id_interno': 'PROV-020', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-08', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'TIAN IPS SALUD OCUPACIONAL MEDICINA ALTE', 'nit': '900293402', 'direccion': 'CLL 47N # 3F-56 B/ VIPASA', 'telefono': '317 7687630', 'correo': 'servicliente@tianips.com', 'contacto': None, 'concepto': 'EXAMENES MEDICOS', 'num_cuenta': '06656365232', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-021', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-09-16', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'RODOLFO ANDRES SANCHEZ CONCHA (COMPETRI)', 'nit': '1130665584', 'direccion': 'CR 36 4 B 63', 'telefono': '3124035294', 'correo': 'COMPETRI@OUTLOOK.COM', 'contacto': 'ANDRES RODOLFO SANCHEZ', 'concepto': 'EPP', 'num_cuenta': '74510642809', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-022', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-10-13', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'IN CHEMICAL SAS', 'nit': '900653299', 'direccion': 'Calle 69 A # 88 A - 32', 'telefono': '350 7533246', 'correo': 'SERVICLIENTE@INCHEMICAL.COM', 'contacto': 'DIANA', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '24113130143', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-023', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-05-16', 'venc_docs': None, 'acuerdo_calidad': 'â Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'DISTRIBUIDORA CORDOBA S A S', 'nit': '860000615', 'direccion': 'Carrera 8 NÂ° 49-64', 'telefono': '323 254 0422', 'correo': 'contacto@discordoba.com', 'contacto': 'PAOLA ANDREA RAMIREZ', 'concepto': 'ENVASES AMBAR 50ML', 'num_cuenta': '22769151361', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-024', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-09-30', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'TAPETES Y PISOS DEL PACIFICO SAS', 'nit': '805007745', 'direccion': 'AV 5 B NORTE 22 N 18', 'telefono': '316 5289374', 'correo': 'contabilidad@tapetesypisos.com.co', 'contacto': 'GILMA OSSA', 'concepto': 'TAPETE', 'num_cuenta': '82500001444', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-025', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-30', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'LEVER ASESORES SAS', 'nit': '901910221', 'direccion': 'AV ESTACION 45 BN 127 OF201', 'telefono': '301 7296448', 'correo': 'Santiago.laharenas@leverlegal.com.co', 'contacto': 'SANTIAGO', 'concepto': 'FACTURA AGOSTO ABOGADOS', 'num_cuenta': '74900006437', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-026', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-10-23', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'CONNPLANTS', 'nit': '900473144-6', 'direccion': 'Cra. 6a #30-12, COMUNA 4, Cali, Valle del Cauca, Colombia', 'telefono': '300 7258390', 'correo': 'andres.ramirez@connplants.com', 'contacto': 'ANDRES RAMIREZ', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '82396710626', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-027', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-11-05', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'SERPROASEO', 'nit': '900104742', 'direccion': 'CR 98 B 42 29', 'telefono': '310 6125805', 'correo': 'serproaseocontable@gmail.com', 'contacto': 'Laura hoyos', 'concepto': 'ASEO', 'num_cuenta': '146122759', 'tipo_cuenta': 'CORRIENTE', 'banco': 'AV VILLAS', 'cert_bancario': None, 'id_interno': 'PROV-028', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-09-26', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'ASEO DEL SUROCCIDENTE S.A. ESP', 'nit': '900414483-6', 'direccion': 'CL 11A # 32 - 108 YUMBO', 'telefono': '315 4106896', 'correo': 'admon.suraseo@gmail.com', 'contacto': None, 'concepto': 'RECOLECCION RESIDUOS', 'num_cuenta': '51470270380', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-029', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-25', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'ALMADINA SAS', 'nit': '901274606', 'direccion': 'CALLE 41 # 74 - 59', 'telefono': '300 5058181', 'correo': 'contacto@almadina.com.co', 'contacto': 'MARCELA', 'concepto': 'ENVASES LIP GLOSS', 'num_cuenta': '29800024887', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-030', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-07', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'IMCD COLOMBIA SAS', 'nit': '800134597', 'direccion': 'Cra 19 #95-20, BogotÃ¡, Colombia', 'telefono': '318 2473413', 'correo': 'nicolas.lugo@imcdcolombia.com', 'contacto': 'ALEJANDRA', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '20018798278', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-031', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-09-01', 'venc_docs': None, 'acuerdo_calidad': 'â³ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'AVA CHEMICAL SAS', 'nit': '9004485872', 'direccion': 'CALLE 17 103B 37 BOGOTA', 'telefono': None, 'correo': None, 'contacto': 'LYDA PATRICIA VANEGAS', 'concepto': 'MATERIA PRIMA ALEJANDRO', 'num_cuenta': '188725116', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-032', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-10-07', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'MERCADEO VALLE SAS', 'nit': '900777239', 'direccion': 'CR 85 A 17 83 P 1', 'telefono': '301 7901807', 'correo': 'mercadeovallecali@gmail.com', 'contacto': None, 'concepto': 'ESTELIRIZADOR DE AGUA', 'num_cuenta': '73632624309', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-033', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-21', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'PALMERA JUNIOR S.A.S.', 'nit': '900.405.705-8', 'direccion': 'AV 3N 45N 10 BRR LA MERCED', 'telefono': '315 3351762', 'correo': 'cartera2@palmerajunior.com', 'contacto': 'IBARRA VELASQUEZ EMMANUEL', 'concepto': 'FUMIGACION', 'num_cuenta': '06470292758', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-034', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-12-03', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'HANDLER SAS', 'nit': '900677390', 'direccion': 'CRA 97 # 24C-23 Bodega 3,', 'telefono': '3244118931', 'correo': 'sguzman@handlercolombia.com', 'contacto': 'santiago guzman alonson', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '237252022-31', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-035', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-12-18', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'LUISA DE MARILLAC GIRALDO OSPINA', 'nit': '42062642', 'direccion': 'calle 18 #4-79', 'telefono': '319 2197419', 'correo': None, 'contacto': 'GERARDO', 'concepto': 'CAJAS PLEGADIZAS', 'num_cuenta': '51402263591', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-036', 'categoria': 'ð  Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-05-12', 'venc_docs': None, 'acuerdo_calidad': 'â³ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'SCIENTIFIC PRODUCTS', 'nit': '805014913', 'direccion': 'Cra. 4b #36a-71, Cali,', 'telefono': '3176461543', 'correo': 'VENTAS7@SPLTAD.COM', 'contacto': 'HENERSON RAMIREZ', 'concepto': 'PICNOMETRO', 'num_cuenta': '07700007741', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-037', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-11-20', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'ANAYCO SAS', 'nit': '811004746', 'direccion': 'Cra. 84 #37 - 61 MedellÃ­n Santa Monica', 'telefono': '312 4926639', 'correo': 'ventas@anayco.net', 'contacto': None, 'concepto': 'PIE DE REY', 'num_cuenta': '07200093339', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-038', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-12-02', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'DIEMPAQUES SAS', 'nit': '900048343', 'direccion': 'Carrera 59 # 14 - 79 BogotÃ¡', 'telefono': '320 8995397', 'correo': 'serviclientes5@diempaques.com', 'contacto': 'PATRICIA AVILA', 'concepto': 'MATERIAL ENVASE', 'num_cuenta': '18623963661', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-039', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-19', 'venc_docs': None, 'acuerdo_calidad': 'â³ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'SAA LAB SAS', 'nit': '901848807', 'direccion': 'carrera 47 # 64-70', 'telefono': '3007758234', 'correo': 'saalabsas@gmail.com', 'contacto': 'Liliana castrillon', 'concepto': 'ESTUDIOS DE ESTABILIDAD', 'num_cuenta': '58000009082', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-040', 'categoria': None, 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-11-04', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'SUMIQUIM', 'nit': '805002736', 'direccion': 'Calle 15 No. 35-75 Bodega 2A / Parque Empresarial Servicomex Express / Acopi Yumbo', 'telefono': '316 7488717', 'correo': 'kamelhernandez@sumiquim.com', 'contacto': 'Kamel Andrez HernÃ¡ndez', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '83606734524', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-041', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-26', 'venc_docs': None, 'acuerdo_calidad': 'â³ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'SU PROVEEDOR QUIMICO PREFERIDO SAS', 'nit': '805023874', 'direccion': 'Carrera 4 # 22 - 59', 'telefono': '304 4209373', 'correo': 'suproquimltda@hotmail.com', 'contacto': 'Stephanie', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '06120211617', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-042', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-05', 'venc_docs': None, 'acuerdo_calidad': 'â Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'CROMAROMA SAS', 'nit': '860533213', 'direccion': 'Transversal 93 # 53-32 Bodega 52 Parque Empresarial El Dorado', 'telefono': '313 4213746', 'correo': 'ruby.millan@cromaroma.com.co', 'contacto': 'Ruby Millan', 'concepto': 'FRAGANCIA', 'num_cuenta': '20787774582', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-043', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-21', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'JULIAN ANDRES QUICENO VALENCIA', 'nit': '1053786250', 'direccion': 'Carrera 43A # 45SUR - 55 B/ Primavera.', 'telefono': '300 3046652', 'correo': 'ventas@bolsasyempaquescolombia.com', 'contacto': 'JULIAN ANDRES QUICENO VALENCIA', 'concepto': 'BOLSAS ZIPLOC', 'num_cuenta': '50651916574', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-044', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-18', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'IDENTIFIK TECNOLOGIA SAS', 'nit': '901191042', 'direccion': 'AV 5 AN DN 68 PASARELA LOCAL 232', 'telefono': '3192880714', 'correo': 'info@identifik.com.co', 'contacto': None, 'concepto': 'ROLLOS DE IMPRESORA', 'num_cuenta': '82595595092', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-045', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-04', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'G & M QUIMICA SAS', 'nit': '900023607', 'direccion': 'CALLE 33 No 9-47', 'telefono': '311 7390527', 'correo': 'ventas3@gmquimica.com', 'contacto': 'Gonzalez Suarez', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '82388090710', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-046', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-11-21', 'venc_docs': None, 'acuerdo_calidad': 'â³ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'RUBIELA RESTREPO DIAZ (ITALPLAST)', 'nit': '29.899.054-1', 'direccion': 'CALLE 18 No. 8 39', 'telefono': '3117198086', 'correo': 'italplastcali@hotmail.com', 'contacto': 'Juan Alberto Ossa', 'concepto': 'CINTA', 'num_cuenta': '80375991181', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-047', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-04', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'CI BALANZAS DE COLOMBIA LTDA', 'nit': '805023451', 'direccion': 'CL 23   17 D   43', 'telefono': '317 6369154', 'correo': 'auxiliar2@cibalanzasdecolombia.com', 'contacto': None, 'concepto': 'ADAPTADOR', 'num_cuenta': '83712557288', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-048', 'categoria': 'ð  Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-05', 'venc_docs': None, 'acuerdo_calidad': 'â³ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'SIILP SAS', 'nit': '901.005.198-0', 'direccion': 'CALLE 43 # 111-45 401A, Cali', 'telefono': '315 5389307', 'correo': 'jsobregon@siilp.com', 'contacto': 'JUAN SEBASTIAN', 'concepto': 'SEGURIDAD Y SALUD EN EL TRABAJO', 'num_cuenta': '015700036070', 'tipo_cuenta': 'AHORROS', 'banco': 'DAVIVIENDA', 'cert_bancario': None, 'id_interno': 'PROV-049', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-02', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'VELCO INGENIERÃA Y SERVICIOS S.A.S', 'nit': '901827384-1', 'direccion': 'Carrera 23 A Bis No. 26 - 105 Cali Valle', 'telefono': '315 974 4777', 'correo': 'velcoingenieriayservicios@gmail.com', 'contacto': 'Luis Felipe Velasco', 'concepto': 'MANTENIMIENTO', 'num_cuenta': '76000003535', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-050', 'categoria': 'ð  Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-15', 'venc_docs': None, 'acuerdo_calidad': 'â Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'INDUSTRIAS IMPERIO RIAÃOS SAS', 'nit': '901356657', 'direccion': 'Calle 16 #14-37', 'telefono': '3113494475', 'correo': 'industriasimperio2018@gmail.com', 'contacto': None, 'concepto': 'ESTANTERIAS', 'num_cuenta': '81500000624', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-051', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-03', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'ALUMINIO Y VIDRIOS', 'nit': '9006329412', 'direccion': 'Calle 9 No. 10 - 111 Barrio San Bosco', 'telefono': '316 471 0070', 'correo': 'contabilidad@vidriospormetro.com', 'contacto': 'Nidia gutierrez', 'concepto': 'ADECUACIONES LUZ', 'num_cuenta': None, 'tipo_cuenta': None, 'banco': None, 'cert_bancario': 'https://checkout.wompi.co/l/VPOS_guWoHx', 'id_interno': 'PROV-052', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-11', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'LUIS MIGUEL MEZA', 'nit': '1143961591', 'direccion': 'CALLE 13 #10-53', 'telefono': '3185597565', 'correo': 'alejito115m@gmail.com', 'contacto': 'LUIS MIGUEL MEZA', 'concepto': 'INSTALACION ESTANTERIAS', 'num_cuenta': '81579850761', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-053', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-12-12', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'SEGURITA SG S.A.S', 'nit': '901342162', 'direccion': 'CALLE 34 #1-64', 'telefono': '301 2613222', 'correo': 'seguritas@gmail.com', 'contacto': 'Daniela', 'concepto': 'TARROS DE BASURA', 'num_cuenta': '80700004928', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-054', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-06', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'SU PROVEEDOR QUIMICO PREFERIDO SAS', 'nit': '805023874', 'direccion': 'Carrera 4 # 22 - 59', 'telefono': '304 4209373', 'correo': 'suproquimltda@hotmail.com', 'contacto': 'Stephanie', 'concepto': 'MATERIA PRIMA  2', 'num_cuenta': '06120211617', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-055', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-10-13', 'venc_docs': None, 'acuerdo_calidad': 'â Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'GOLDEN BUSINESS CLASS SA', 'nit': '900299296', 'direccion': 'Autopista via bogota-Medellin KM 2,5', 'telefono': '3107891300', 'correo': 'ventas4@goldengbc.com', 'contacto': 'Gina Liliana', 'concepto': 'MICAS', 'num_cuenta': '65078825979', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-056', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-16', 'venc_docs': None, 'acuerdo_calidad': 'â³ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'TRS PARTES SA', 'nit': '900013663', 'direccion': 'Cra. 1 No. 49-35', 'telefono': '317 4961234', 'correo': 'julian.benavides@trspartes.com', 'contacto': 'JULIAN', 'concepto': 'FILTROS AIRES', 'num_cuenta': '30685260722', 'tipo_cuenta': 'AHORROS', 'banco': '74510642809', 'cert_bancario': None, 'id_interno': 'PROV-057', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-12-02', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'PAPELERIA UNIVERSAL\nDISTRIBUIDORA SAS', 'nit': '901.160.842-9', 'direccion': 'CRA 9 11 04', 'telefono': '315 8155803', 'correo': 'distribuidorauniversaldigital@gmail.com', 'contacto': 'CARDONA FERNANDEZ DIDALIA', 'concepto': 'PAPELERIA', 'num_cuenta': '017069991945', 'tipo_cuenta': 'CORRIENTE', 'banco': 'DAVIVIENDA', 'cert_bancario': None, 'id_interno': 'PROV-058', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-05-21', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'MUPRO INTERNACIONAL SAS', 'nit': '901803010', 'direccion': 'CALLE 7Âª 24-25 San Nicolas', 'telefono': '317 7604440', 'correo': 'ANDRESSARRIADORADO@GMAIL.COM', 'contacto': 'ANDRES SARRIA DORADO', 'concepto': 'MESA PARA ACONDICIONAMIENTO', 'num_cuenta': '82100007872', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-059', 'categoria': 'ð  Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-11-12', 'venc_docs': None, 'acuerdo_calidad': 'â³ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'SIAMED', 'nit': '9017515033', 'direccion': None, 'telefono': '320 6931797', 'correo': 'gerenciatecnica@amedasesorias.com', 'contacto': 'JORGE CHARRY', 'concepto': 'CALIBRACIÃN', 'num_cuenta': '0550108900617151', 'tipo_cuenta': 'AHORROS DAMAS', 'banco': 'DAVIVIENDA', 'cert_bancario': None, 'id_interno': 'PROV-060', 'categoria': 'ð  Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-09-04', 'venc_docs': None, 'acuerdo_calidad': 'â Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'HENRY DELGADO NAVAS (MERCURIO)', 'nit': '16583442', 'direccion': 'CRA 5 #18-74', 'telefono': '313 5784211', 'correo': 'graficasmercurio@gmail.com', 'contacto': 'LUZ MARINA PRADO', 'concepto': 'TINTAS Y SELOS', 'num_cuenta': '06213774889', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-061', 'categoria': 'ð¢ No crÃ­tico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-09-24', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'UNIVERSIDAD SANTIAGO DE CALI', 'nit': '8903037971', 'direccion': 'Cl. 5 #62-00, Cuarto de Legua, Cali,', 'telefono': '314 8901580', 'correo': 'comercialmetrologia@usc.edu.co', 'contacto': 'Ingrid Galeano', 'concepto': 'CALIBRACIÃN BALANZA', 'num_cuenta': '484467436', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCO DE BOGOTA', 'cert_bancario': None, 'id_interno': 'PROV-062', 'categoria': 'ð  Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-10', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'CODIFICACION & ETIQUETADO S A', 'nit': '830116638', 'direccion': 'Calle 23 116 31 Bodega 5 Bogota', 'telefono': '318 4999402', 'correo': 'paola.soto@coditeq.com', 'contacto': None, 'concepto': 'INYET', 'num_cuenta': '63830606281', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-063', 'categoria': 'ð  Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-14', 'venc_docs': None, 'acuerdo_calidad': 'â³ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'Hebei Yayoujia Packaging Products Co., Ltd.', 'nit': '91130402MAE4JBHG94', 'direccion': 'Room 913, Building B, No.18 Hanqi Building, Dongliu West Street, Hanshan District, Handan City, Hebei Province', 'telefono': '0086 17703203040', 'correo': 'yayoujia_sarah@163.com', 'contacto': 'Sarah Li', 'concepto': 'ENVASES CHINA', 'num_cuenta': None, 'tipo_cuenta': None, 'banco': None, 'cert_bancario': None, 'id_interno': 'PROV-064', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'En CalificaciÃ³n', 'ultima_eval': 'Pendiente', 'venc_docs': None, 'acuerdo_calidad': 'â Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'Shaanxi Yuantai Biological Technology Co., Ltd', 'nit': '916101323337510488', 'direccion': "No.801, Building3, Dahua Stock Smart Industrial Park,\nTiangu 6th Road, Yanta District, Xi ''an, Shaanxi, China", 'telefono': '(+)86 180 9215 6330', 'correo': 'allen@sxytbio.com', 'contacto': 'ICEY', 'concepto': 'MATERIA PRIMA CHINA', 'num_cuenta': None, 'tipo_cuenta': None, 'banco': None, 'cert_bancario': None, 'id_interno': 'PROV-065', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'En CalificaciÃ³n', 'ultima_eval': 'Pendiente', 'venc_docs': None, 'acuerdo_calidad': 'â Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'Shanghai Kaijin Packaging Products Co., Ltd.', 'nit': '91310117MA1J1KY537', 'direccion': 'Edificio A874, No. 2, Carril 158, Calle Gangye, Pueblo de Xiaokunshan, Distrito de Songjiang, ShanghÃ¡i.', 'telefono': '(+)86 158 6832 7130', 'correo': None, 'contacto': 'ELLA', 'concepto': 'ENVASES CHINA', 'num_cuenta': None, 'tipo_cuenta': None, 'banco': None, 'cert_bancario': None, 'id_interno': 'PROV-066', 'categoria': 'ð´ CrÃ­tico', 'estado_lpa': 'En CalificaciÃ³n', 'ultima_eval': 'Pendiente', 'venc_docs': None, 'acuerdo_calidad': 'â Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'GERMAN ALZATE RAMIREZ (GALILEO)', 'nit': '16774136', 'direccion': 'CR 4 18 01 LC 04', 'telefono': '311 3472771', 'correo': None, 'contacto': 'German Alzate', 'concepto': 'ACONDICIONAMIENTO ETIQUETAS', 'num_cuenta': '06225334402', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-067', 'categoria': 'ð  Mayor', 'estado_lpa': 'En CalificaciÃ³n', 'ultima_eval': 'Pendiente', 'venc_docs': None, 'acuerdo_calidad': 'â Firmado', 'rut': 0, 'cam_com': 0}]
    for _p in _provs:
        try:
            c.execute('''INSERT OR IGNORE INTO proveedores
                (nombre,contacto,email,telefono,categoria,nit,direccion,num_cuenta,
                 tipo_cuenta,banco,cert_bancario,id_interno,estado_lpa,
                 ultima_evaluacion,vencimiento_docs,acuerdo_calidad,rut,camara_comercio,concepto_compra,fecha_creacion)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime("now"))''',
                (_p['nombre'],_p['contacto'],_p['correo'],_p['telefono'],_p['categoria'],
                 _p['nit'],_p['direccion'],_p['num_cuenta'],_p['tipo_cuenta'],_p['banco'],
                 _p['cert_bancario'],_p['id_interno'],_p['estado_lpa'],_p['ultima_eval'],
                 _p['venc_docs'],_p['acuerdo_calidad'],_p['rut'],_p['cam_com'],_p['concepto']))
        except Exception: pass

    # ââ SEED: 19 OCs Abril 2026 â estado Borrador (pendiente autorizaciÃ³n) â
    _ocs_abr = [('OC-260401', '2026-02-25', 'Revisada', 'CFC CAFARCOL SAS', 551781.0, 'Gotero blanco pipeta x520 para Fernando Meza â pago lÃ­mite 14 abr', 'sistema', '2026-04-14', 'Envase'), ('OC-260304', '2026-03-04', 'Revisada', 'POCHTECA COLOMBIA', 197540.0, 'Materia prima â pago lÃ­mite 14 abr', 'sistema', '2026-04-14', 'MPs'), ('OC-260402-ESP', '2026-04-14', 'Revisada', 'AGENQUIMICOS', 885999.99, 'Materia prima â pago lÃ­mite 14 abr', 'sistema', '2026-04-14', 'MPs'), ('OC-260307', '2026-03-07', 'Revisada', 'IN CHEMICAL SAS', 702100.0, 'Materia prima â pago lÃ­mite 14 abr', 'sistema', '2026-04-14', 'MPs'), ('OC-260202', '2026-02-02', 'Revisada', 'GYM QUIMICA', 250376.0, 'Materia prima â pago lÃ­mite 16 abr', 'sistema', '2026-04-16', 'MPs'), ('OC-260301', '2026-03-01', 'Revisada', 'CHEMY JAM COLOMBIA SAS', 1203090.0, 'LEXFEEL WOW â pago lÃ­mite 16 abr', 'sistema', '2026-04-16', 'MPs'), ('OC-260403', '2026-04-20', 'Revisada', 'SU PROVEEDOR QUIMICO PREFERIDO SAS', 530000.01, 'Propilenglicol â pago lÃ­mite 20 abr', 'sistema', '2026-04-20', 'MPs'), ('OC-260406', '2026-04-17', 'Revisada', 'FLOW CHEM SAS', 202800.0, 'Detergentes BIOACID + PURE ACID MAX + PURE ALCA FORTE + flete', 'alejandro', '', 'Insumos'), ('OC-260402-ETQ', '2026-04-13', 'Revisada', 'CODIFICACION & ETIQUETADO S A', 1149730.0, 'Inject / codificaciÃ³n â pago lÃ­mite 13 abr', 'sistema', '2026-04-13', 'Insumos'), ('OC-260320', '2026-03-20', 'Revisada', 'DUQUE SALDARRIAGA Y CIA SAS', 37100.63, 'Envases MRP â pago lÃ­mite 17 abr', 'sistema', '2026-04-17', 'Envase'), ('OC-260313', '2026-03-13', 'Revisada', 'PLASTIVALLE SAS', 91159.95, 'Envase plÃ¡stico â pago lÃ­mite 13 abr', 'sistema', '2026-04-13', 'Envase'), ('OC-260317', '2026-03-17', 'Revisada', 'ALARMAR LTDA', 183837.71, 'Alarma mes de marzo â pago lÃ­mite 15 abr', 'sistema', '2026-04-15', 'Servicios'), ('OC-260316', '2026-03-16', 'Revisada', 'MICROLAB', 2850706.72, 'AnÃ¡lisis microbiolÃ³gicos â pago lÃ­mite 18 abr', 'sistema', '2026-04-18', 'AnÃ¡lisis'), ('OC-260207', '2026-02-07', 'Revisada', 'PAPELERIA UNIVERSA SAS', 164600.21, 'Insumos papelerÃ­a â pago lÃ­mite 22 abr', 'sistema', '2026-04-22', 'Insumos'), ('OC-260309', '2026-03-09', 'Revisada', 'MOL LABS LTDA', 164220.0, 'Buffer pH â pago lÃ­mite 22 abr', 'sistema', '2026-04-22', 'AnÃ¡lisis'), ('OC-260312', '2026-03-12', 'Revisada', 'CIEL TECHNOLOGY SAS', 1244850.0, 'Software CIEL â pago lÃ­mite 22 abr', 'sistema', '2026-04-22', 'Servicios'), ('OC-251209', '2025-12-09', 'Revisada', 'DE LA PAVA Y COMPANIA SAS', 809200.0, 'Seguridad â pago lÃ­mite 24 abr', 'sistema', '2026-04-24', 'Servicios'), ('OC-251216', '2025-12-16', 'Revisada', 'ARMEPLAS PRODALCA SAS', 2527322.0, 'Acondicionamiento / caÃ±itas â pago lÃ­mite 24 abr', 'sistema', '2026-04-24', 'Acondicionamiento'), ('OC-260127', '2026-01-27', 'Revisada', 'RACKETBALL SA', 389699.99, 'Laboratorios â pago lÃ­mite 25 abr', 'sistema', '2026-04-25', 'AnÃ¡lisis')]
    for _oc in _ocs_abr:
        try:
            c.execute('''INSERT OR IGNORE INTO ordenes_compra
                (numero_oc,fecha,estado,proveedor,valor_total,observaciones,creado_por,fecha_entrega_est,categoria)
                VALUES(?,?,?,?,?,?,?,?,?)''', _oc)
        except Exception: pass
    # Actualizar OCs ya sembradas como Borrador â Revisada (pendiente autorizaciÃ³n CEO)
    _oc_nums = ['OC-260401','OC-260304','OC-260402-ESP','OC-260307','OC-260202',
                'OC-260301','OC-260403','OC-260406','OC-260402-ETQ','OC-260320',
                'OC-260313','OC-260317','OC-260316','OC-260207','OC-260309',
                'OC-260312','OC-251209','OC-251216','OC-260127']
    try:
        c.executemany("UPDATE ordenes_compra SET estado='Revisada' WHERE numero_oc=? AND estado='Borrador'",
                      [(n,) for n in _oc_nums])
    except Exception: pass

    # ââ SEED: NÃ³minas 1Q Abril 2026 âââââââââââââââââââââââââââââââââââââââââ
    _nominas = [
        ('2026-04-15','ANIMUS','NÃ³mina personal ÃNIMUS Lab â 1Q Abril 2026',
         'NÃ³mina',12651985.0,'2026-04','nomina','NOM-ANIMUS-1Q-ABR26','sistema',
         '8 empleados â Denis Alejandro Morales Restrepo + 7'),
        ('2026-04-15','ESPAGIRIA','NÃ³mina personal Espagiria â 1Q Abril 2026',
         'NÃ³mina',17339902.0,'2026-04','nomina','NOM-ESP-1Q-ABR26','sistema',
         '11 empleados â Hernando Acevedo + Luis Dorronsoro + 9'),
    ]
    for _n in _nominas:
        try:
            if not c.execute('SELECT 1 FROM flujo_egresos WHERE referencia=?',(_n[7],)).fetchone():
                c.execute('''INSERT INTO flujo_egresos
                    (fecha,empresa,concepto,categoria,monto,periodo,fuente,referencia,creado_por,observaciones)
                    VALUES(?,?,?,?,?,?,?,?,?,?)''', _n)
        except Exception: pass
    c.execute("""CREATE TABLE IF NOT EXISTS compromisos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  descripcion TEXT NOT NULL,
                  responsable TEXT DEFAULT '',
                  area TEXT DEFAULT '',
                  fecha_limite TEXT DEFAULT '',
                  estado TEXT DEFAULT 'Pendiente',
                  prioridad TEXT DEFAULT 'Normal',
                  origen TEXT DEFAULT '',
                  empresa TEXT DEFAULT 'Espagiria',
                  fecha_creacion TEXT,
                  fecha_cierre TEXT DEFAULT '',
                  notas TEXT DEFAULT '')""")
    c.execute("""CREATE TABLE IF NOT EXISTS no_conformidades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  fecha TEXT DEFAULT (date('now')),
                  tipo TEXT DEFAULT 'Proceso',
                  descripcion TEXT NOT NULL,
                  area TEXT DEFAULT '',
                  responsable TEXT DEFAULT '',
                  lote TEXT DEFAULT '',
                  codigo_mp TEXT DEFAULT '',
                  impacto TEXT DEFAULT 'Bajo',
                  accion_correctiva TEXT DEFAULT '',
                  estado TEXT DEFAULT 'Abierta',
                  fecha_cierre TEXT DEFAULT '',
                  cerrado_por TEXT DEFAULT '',
                  creado_por TEXT DEFAULT '')""")
    c.execute("""CREATE TABLE IF NOT EXISTS calibraciones_instrumentos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  instrumento TEXT NOT NULL,
                  codigo TEXT NOT NULL UNIQUE,
                  ubicacion TEXT DEFAULT '',
                  fecha_ultima TEXT DEFAULT '',
                  fecha_proxima TEXT DEFAULT '',
                  responsable TEXT DEFAULT '',
                  empresa TEXT DEFAULT 'Espagiria',
                  estado TEXT DEFAULT 'Vigente',
                  certificado TEXT DEFAULT '',
                  observaciones TEXT DEFAULT '')""")
    for _cal in [
        ('Balanza Analitica','BAL-001','Laboratorio','2026-01-15','2026-07-15','Catalina Torres','Espagiria','Vigente','CAL-BAL-001-2026',''),
        ('Balanza Gramera','BAL-002','Planta','2026-01-20','2026-07-20','Alejandro Rios','Espagiria','Vigente','CAL-BAL-002-2026',''),
        ('Viscosimetro','VISC-001','Laboratorio','2025-10-01','2026-04-01','Catalina Torres','Espagiria','Vencida','CAL-VISC-001-2025','Pendiente renovacion'),
        ('pH-metro','PH-001','Laboratorio','2026-02-10','2026-08-10','Catalina Torres','Espagiria','Vigente','CAL-PH-001-2026',''),
        ('Termometro Digital','TERM-001','Planta','2026-03-01','2026-09-01','Alejandro Rios','Espagiria','Vigente','CAL-TERM-001-2026',''),
    ]:
        try:
            c.execute("""INSERT OR IGNORE INTO calibraciones_instrumentos
                         (instrumento,codigo,ubicacion,fecha_ultima,fecha_proxima,
                          responsable,empresa,estado,certificado,observaciones)
                         VALUES (?,?,?,?,?,?,?,?,?,?)""", _cal)
        except Exception: pass
    # -- Cronograma calidad
    c.execute("""CREATE TABLE IF NOT EXISTS calidad_tareas (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 nombre TEXT NOT NULL,
                 categoria TEXT DEFAULT 'General',
                 hora_objetivo TEXT DEFAULT '',
                 hora_limite TEXT DEFAULT '',
                 responsable TEXT DEFAULT 'Jefe CC',
                 procedimiento TEXT DEFAULT '',
                 requiere_valor INTEGER DEFAULT 0,
                 unidad_valor TEXT DEFAULT '',
                 activa INTEGER DEFAULT 1,
                 orden INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS calidad_registros (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 fecha TEXT NOT NULL,
                 tarea_id INTEGER,
                 usuario TEXT DEFAULT '',
                 estado TEXT DEFAULT 'Pendiente',
                 hora_inicio TEXT DEFAULT '',
                 hora_fin TEXT DEFAULT '',
                 valor_registrado TEXT DEFAULT '',
                 observaciones TEXT DEFAULT '',
                 created_at TEXT DEFAULT (datetime('now')))""")
    _tareas_cal = [
        ('Temp y HR - Area Produccion','Apertura','07:00','07:30','Analista','','C / %HR',1,1),
        ('Temp y HR - Laboratorio CC','Apertura','07:00','07:30','Analista','','C / %HR',1,2),
        ('Liberacion de balanzas','Apertura','07:15','07:30','Jefe CC','BAL-001/002','g (ajuste)',1,3),
        ('Verificacion agua desionizada Blue Tide RO','Apertura','07:30','08:00','Analista','SA-PRD-001','uS/cm',1,4),
        ('Verificacion nevera RF-PRD-001 cadena frio','Apertura','07:00','07:30','Analista','COC-PRO-011','C',1,5),
        ('Despeje de linea / Liberacion de area batch','Produccion','08:00','09:00','Jefe CC','PRD-PRO-001','',0,6),
        ('Control en proceso - pH granel','Produccion','','','Analista','COC-PRO-010','pH',1,7),
        ('Control en proceso - Viscosidad','Produccion','','','Analista','COC-PRO-010','cP',1,8),
        ('Control en proceso - Apariencia color olor','Produccion','','','Analista','COC-PRO-010','',0,9),
        ('Muestreo MP ingresadas','Recepcion','','','Jefe CC','COC-PRO-001','',0,10),
        ('Inspeccion MEM ingresada','Recepcion','','','Jefe CC','COC-PRO-002','',0,11),
        ('Analisis fisicoquimico MP pH viscosidad densidad','Analisis','','','Analista','COC-PRO-001','pH / cP',1,12),
        ('Temp final - Nevera RF-PRD-001','Cierre','17:00','17:30','Analista','COC-PRO-011','C',1,13),
        ('Temp final - Area Produccion','Cierre','17:00','17:30','Analista','','C / %HR',1,14),
        ('Revision y archivo documentacion del dia','Cierre','16:30','17:30','Jefe CC','','',0,15),
    ]
    c.execute("SELECT COUNT(*) FROM calidad_tareas")
    if c.fetchone()[0] == 0:
        for _t in _tareas_cal:
            try:
                c.execute("""INSERT INTO calidad_tareas
                             (nombre,categoria,hora_objetivo,hora_limite,responsable,
                              procedimiento,unidad_valor,requiere_valor,orden)
                             VALUES (?,?,?,?,?,?,?,?,?)""", _t)
            except Exception: pass
    seed_compromisos(c)
    # Dedup RRHH seed tables (run once, idempotent)
    # ── Migrate nomina_registros: add aprobado_por, aprobado_en, pagado_por, pagado_en if missing ──
    for _col, _def in [("aprobado_por","TEXT DEFAULT NULL"), ("aprobado_en","TEXT DEFAULT NULL"),
                       ("pagado_por","TEXT DEFAULT NULL"), ("pagado_en","TEXT DEFAULT NULL")]:
        try:
            c.execute("ALTER TABLE nomina_registros ADD COLUMN "+_col+" "+_def)
        except Exception:
            pass  # column already exists
    try:
        c.execute("DELETE FROM sgsst_items WHERE id NOT IN (SELECT MIN(id) FROM sgsst_items GROUP BY descripcion)")
        c.execute("DELETE FROM capacitaciones WHERE id NOT IN (SELECT MIN(id) FROM capacitaciones GROUP BY nombre)")
        c.execute("DELETE FROM capacitaciones_empleados WHERE rowid NOT IN (SELECT MIN(rowid) FROM capacitaciones_empleados GROUP BY capacitacion_id, empleado_id)")
    except: pass
    # ── One-time production data corrections ──────────────────────────────────
    apply_production_corrections(c)
    # ── Envasado ─────────────────────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS envasado (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        produccion_id       INTEGER DEFAULT 0,
        lote                TEXT NOT NULL,
        producto            TEXT NOT NULL,
        presentacion        TEXT DEFAULT '',
        batch_g             REAL DEFAULT 0,
        unidades            INTEGER DEFAULT 0,
        envase_codigo       TEXT DEFAULT '',
        tapa_codigo         TEXT DEFAULT '',
        operador            TEXT DEFAULT '',
        fecha               TEXT DEFAULT '',
        estado              TEXT DEFAULT 'Completado',
        observaciones       TEXT DEFAULT ''
    )""")
    # Add envasado_id to acondicionamiento if not present
    try:
        c.execute("ALTER TABLE acondicionamiento ADD COLUMN envasado_id INTEGER DEFAULT 0")
    except: pass
    try:
        c.execute("ALTER TABLE liberaciones ADD COLUMN acondicionamiento_id INTEGER DEFAULT 0")
    except: pass


    # ── Limpieza permanente OCs de prueba (cargadas desde Excel) ──────────────
    # Estas OCs son datos de prueba identificados por su numero (formato OC-YYMMNN)
    # y por no tener categoria Influencer/CC. Se eliminan en cada startup.
    _test_ocs = [
        'OC-260403','OC-260406','OC-260402-ESP','OC-260402-ETQ',
        'OC-260320','OC-260317','OC-260316','OC-260313','OC-260312',
        'OC-260309','OC-260307','OC-260304','OC-260301','OC-260401',
        'OC-260207','OC-260202','OC-260127','OC-251216','OC-251209'
    ]
    _ph = ','.join('?' * len(_test_ocs))
    c.execute(f'DELETE FROM ordenes_compra_items WHERE numero_oc IN ({_ph})', _test_ocs)
    c.execute(f'DELETE FROM ordenes_compra WHERE numero_oc IN ({_ph})', _test_ocs)


    # ── Empleados reales HHA Group (seeded 2026-04-23) ──────────────────
    # Primero eliminar empleados dummy sin referencias (cedulas ficticias del seed previo)
    _dummy_ced = ('1090432100','1090512210','1043218870','1090388900','1092101530','1090600610','1043320780')
    for _dc in _dummy_ced:
        try:
            _row = c.execute("SELECT id FROM empleados WHERE cedula=?", (_dc,)).fetchone()
            if _row:
                _refs = c.execute("SELECT COUNT(*) FROM nomina_registros WHERE empleado_id=?", (_row[0],)).fetchone()[0]
                if _refs == 0:
                    c.execute("DELETE FROM empleados WHERE cedula=?", (_dc,))
        except Exception:
            pass
    # Insertar empleados reales (cedulas reales — INSERT OR IGNORE protege contra re-runs)
    _emp_data = [
        ("HHA001","Alvaro Julio","Gonz\u00e1lez Londo\u00f1o","16632635","Mensajero","Log\u00edstica","\u00c1NIMUS Lab","Indefinido","2021-06-01","Activo",1750905,1),
        ("HHA002","Daniela","Murillo Sol\u00eds","1143874047","Log\u00edstica Despachos","Log\u00edstica","\u00c1NIMUS Lab","Indefinido","2022-05-16","Activo",3000000,1),
        ("HHA003","Haidy Samira","Garc\u00eda Mosquera","1128724125","Auxiliar de Despachos","Log\u00edstica","\u00c1NIMUS Lab","Indefinido","2021-03-08","Activo",1750905,1),
        ("HHA004","Jefferson","Mu\u00f1oz Cachimbo","1026560691","Marketing","Marketing","\u00c1NIMUS Lab","Indefinido","2023-01-16","Activo",1850905,1),
        ("HHA005","Valentina","Mu\u00f1oz Cachimbo","1026560690","Ventas","Ventas","\u00c1NIMUS Lab","Indefinido","2022-09-01","Activo",1750905,1),
        ("HHA006","Karol Yulieth","Cer\u00f3n Trullo","1109663762","Auxiliar de Despachos","Log\u00edstica","\u00c1NIMUS Lab","Indefinido","2023-10-01","Activo",1750905,1),
        ("HHA007","Lina Marcela","Gaviria Pati\u00f1o","1098307374","Oficios Varios","Servicios","\u00c1NIMUS Lab","Indefinido","2023-10-15","Activo",1750905,1),
        ("HHA008","Sebasti\u00e1n","Vargas Isaza","1097397765","Gerente Ejecutivo","Gerencia","HHA Group","Indefinido","2025-02-01","Activo",6000000,1),
        ("ESP001","Catalina","Erazo Aristizabal","1006054219","Asistente de Gerencia","Administraci\u00f3n","Espagiria","Indefinido","2023-06-02","Activo",1750905,1),
        ("ESP002","Luz Adriana","Torres Garc\u00eda","1007854652","Aux. Admtiva. Producci\u00f3n y Compras","Administraci\u00f3n","Espagiria","Indefinido","2021-02-15","Activo",2000000,2),
        ("ESP003","Maierlin","Rivera Mej\u00eda","1005875757","Operaria Producci\u00f3n","Producci\u00f3n","Espagiria","Indefinido","2021-03-08","Activo",1750905,2),
        ("ESP004","Yeison Camilo","Garc\u00eda Mosquera","1007601298","Auxiliar de Bodega MP y Empaque","Bodega","Espagiria","Indefinido","2022-03-01","Activo",1750905,2),
        ("ESP005","Mar\u00eda Yuliel","Rivera Vargas","43976397","Jefe Control de Calidad","Calidad","Espagiria","Indefinido","2024-03-04","Activo",3000000,2),
        ("ESP006","Johan Sebasti\u00e1n","Murillo Sol\u00eds","1143846075","Operario Envasado","Producci\u00f3n","Espagiria","Indefinido","2024-10-21","Activo",1750905,2),
        ("ESP007","Hernando","Acevedo D\u00edaz","1044912921","Director T\u00e9cnico","Direcci\u00f3n T\u00e9cnica","Espagiria","Indefinido","2024-10-28","Activo",8500000,2),
        ("ESP008","Miguel","Valencia Medina","1007932197","Jefe de Aseguramiento de la Calidad","Calidad","Espagiria","Indefinido","2026-03-19","Activo",3500000,2),
        ("ESP009","Luis Enrique","Dorronsoro Gamboa","14639995","Jefe de Producci\u00f3n","Producci\u00f3n","Espagiria","Indefinido","2026-03-19","Activo",5500000,2),
        ("ESP010","Laura Isabel","Gonz\u00e1lez Largo","1193447691","Jefe de Calidad","Calidad","Espagiria","Indefinido","2026-01-05","Activo",4500000,2),
        ("ESP011","Sergio Andr\u00e9s","Burbano Pardo","1001937292","Operario Producci\u00f3n","Producci\u00f3n","Espagiria","Indefinido","2026-01-13","Activo",1750905,2),
    ]
    for _e in _emp_data:
        try:
            c.execute("INSERT OR IGNORE INTO empleados (codigo,nombre,apellido,cedula,cargo,area,empresa,tipo_contrato,fecha_ingreso,estado,salario_base,nivel_riesgo) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", _e)
        except Exception:
            pass

    # Seed banco/cuenta bancaria por cedula (UPDATE seguro — no falla si ya existe)
    _bank_data = [
        # ANIMUS Lab (8 empleados)
        ("16632635",    "BBVA",         "813000200051521",    "AHORROS"),
        ("1143874047",  "DAVIVIENDA",   "10470059592",        "AHORROS"),
        ("1128724125",  "BANCOLOMBIA",  "91220528389",        "AHORROS"),
        ("1026560691",  "BANCOLOMBIA",  "91291991802",        "AHORROS"),
        ("1026560690",  "BANCOLOMBIA",  "91246950747",        "AHORROS"),
        ("1109663762",  "BANCOLOMBIA",  "6160474104",         "AHORROS"),
        ("1098307374",  "DAVIVIENDA",   "0550488436467077",   "AHORROS DAMAS"),
        ("1097397765",  "BANCOLOMBIA",  "91273689724",        "AHORROS"),
        # Genesis (posible 9no de ANIMUS Lab)
        ("1235252199",  "BANCOLOMBIA",  "6107281001",         "AHORROS"),
        # Espagiria (11 empleados)
        ("1006054219",  "AV-VILLAS",    "148707529",          "AHORROS"),
        ("1007854652",  "BANCOLOMBIA",  "91219764516",        "AHORROS"),
        ("1005875757",  "BANCOLOMBIA",  "91219757421",        "AHORROS"),
        ("1007601298",  "BANCOLOMBIA",  "3146792620",         "NEQUI"),
        ("43976397",    "BANCOLOMBIA",  "81583095349",        "AHORROS"),
        ("1143846075",  "DAVIVIENDA",   "0570019170026397",   "AHORROS"),
        ("1044912921",  "BANCOLOMBIA",  "80798012383",        "AHORROS"),
        ("1007932197",  "DAVIVIENDA",   "0570488471748506",   "AHORROS"),
        ("14639995",    "BANCOLOMBIA",  "60566122726",        "AHORROS"),
        ("1193447691",  "CAJA SOCIAL",  "24103175746",        "AHORROS"),
        ("1001937292",  "BANCO BOGOTA", "164579443",          "AHORROS"),
    ]
    for _ced, _banco, _num_cta, _tipo in _bank_data:
        try:
            c.execute(
                "UPDATE empleados SET banco=?, numero_cuenta=?, tipo_cuenta=? WHERE cedula=?",
                (_banco, _num_cta, _tipo, _ced)
            )
        except Exception:
            pass




    # ── Módulo Marketing ─────────────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS marketing_campanas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        tipo TEXT DEFAULT 'Digital',
        estado TEXT DEFAULT 'Planificada',
        presupuesto REAL DEFAULT 0,
        presupuesto_gastado REAL DEFAULT 0,
        fecha_inicio TEXT,
        fecha_fin TEXT,
        sku_objetivo TEXT,
        objetivo_unidades INTEGER DEFAULT 0,
        resultado_unidades INTEGER DEFAULT 0,
        resultado_ventas REAL DEFAULT 0,
        canal TEXT,
        notas TEXT,
        creada_por TEXT,
        fecha_creacion TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS marketing_influencers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        red_social TEXT DEFAULT 'Instagram',
        usuario_red TEXT,
        seguidores INTEGER DEFAULT 0,
        engagement_rate REAL DEFAULT 0,
        nicho TEXT,
        tarifa REAL DEFAULT 0,
        estado TEXT DEFAULT 'Activo',
        email TEXT,
        telefono TEXT,
        notas TEXT,
        fecha_registro TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS marketing_campana_influencer (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campana_id INTEGER NOT NULL,
        influencer_id INTEGER NOT NULL,
        monto_pactado REAL DEFAULT 0,
        monto_pagado REAL DEFAULT 0,
        fecha_pago TEXT,
        alcance_real INTEGER DEFAULT 0,
        impresiones INTEGER DEFAULT 0,
        clicks INTEGER DEFAULT 0,
        conversiones INTEGER DEFAULT 0,
        estado TEXT DEFAULT 'Pendiente',
        notas TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS marketing_contenido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campana_id INTEGER,
        influencer_id INTEGER,
        tipo TEXT DEFAULT 'Post',
        plataforma TEXT DEFAULT 'Instagram',
        fecha_publicacion TEXT,
        estado TEXT DEFAULT 'Borrador',
        caption TEXT,
        url_publicacion TEXT,
        likes INTEGER DEFAULT 0,
        comentarios INTEGER DEFAULT 0,
        shares INTEGER DEFAULT 0,
        guardados INTEGER DEFAULT 0,
        alcance INTEGER DEFAULT 0,
        impresiones INTEGER DEFAULT 0,
        clicks INTEGER DEFAULT 0,
        conversiones INTEGER DEFAULT 0,
        notas TEXT,
        creado_por TEXT,
        fecha_creacion TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS marketing_agentes_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agente TEXT NOT NULL,
        accion TEXT,
        resultado TEXT,
        fecha TEXT DEFAULT (datetime('now')),
        ejecutado_por TEXT
    )""")


    # ── Centro de Mando ÁNIMUS Lab ──────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS animus_config (
        clave TEXT PRIMARY KEY,
        valor TEXT,
        actualizado TEXT DEFAULT (datetime('now'))
    )""")
    # Todas las credenciales desde variables de entorno de Render — nunca hardcodeadas
    import os as _os
    for _clave, _env in [
        ('ghl_api_key',      'GHL_API_KEY'),        # GoHighLevel API key
        ('ghl_location_id',  'GHL_LOCATION_ID'),    # GoHighLevel Location ID
        ('shopify_token',    'SHOPIFY_TOKEN'),
        ('shopify_shop',     'SHOPIFY_SHOP'),
        ('anthropic_api_key','ANTHROPIC_API_KEY'),
        ('instagram_token',  'INSTAGRAM_TOKEN'),
        ('instagram_user_id','INSTAGRAM_USER_ID'),
        ('meta_app_id',      'META_APP_ID'),
        ('meta_app_secret',  'META_APP_SECRET'),
    ]:
        _val = _os.environ.get(_env)
        if _val:
            c.execute("INSERT OR REPLACE INTO animus_config(clave,valor) VALUES(?,?)", (_clave, _val))

    c.execute("""CREATE TABLE IF NOT EXISTS animus_shopify_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shopify_id TEXT UNIQUE,
        nombre TEXT,
        email TEXT,
        total REAL DEFAULT 0,
        moneda TEXT DEFAULT 'COP',
        estado TEXT,
        estado_pago TEXT,
        sku_items TEXT,
        unidades_total INTEGER DEFAULT 0,
        ciudad TEXT,
        pais TEXT DEFAULT 'CO',
        creado_en TEXT,
        synced_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS animus_shopify_customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shopify_id TEXT UNIQUE,
        nombre TEXT,
        email TEXT,
        telefono TEXT,
        total_gastado REAL DEFAULT 0,
        num_pedidos INTEGER DEFAULT 0,
        ciudad TEXT,
        pais TEXT DEFAULT 'CO',
        tags TEXT,
        creado_en TEXT,
        synced_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS animus_ghl_contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ghl_id TEXT UNIQUE,
        nombre TEXT,
        email TEXT,
        telefono TEXT,
        etiquetas TEXT,
        pipeline_etapa TEXT,
        valor_oportunidad REAL DEFAULT 0,
        fuente TEXT,
        creado_en TEXT,
        synced_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS animus_ghl_oportunidades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ghl_id TEXT UNIQUE,
        contacto_nombre TEXT,
        pipeline TEXT,
        etapa TEXT,
        valor REAL DEFAULT 0,
        estado TEXT,
        creado_en TEXT,
        synced_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS animus_instagram_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        instagram_id TEXT UNIQUE,
        tipo TEXT,
        descripcion TEXT,
        url_media TEXT,
        url_permalink TEXT,
        likes INTEGER DEFAULT 0,
        comentarios INTEGER DEFAULT 0,
        alcance INTEGER DEFAULT 0,
        impresiones INTEGER DEFAULT 0,
        guardados INTEGER DEFAULT 0,
        publicado_en TEXT,
        synced_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS animus_contenido_generado (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT,
        tipo TEXT,
        plataforma TEXT,
        tono TEXT,
        contenido TEXT,
        usado INTEGER DEFAULT 0,
        generado_por TEXT,
        creado_en TEXT DEFAULT (datetime('now'))
    )""")


    # ── Rate limiter persistente (multi-worker safe) ──────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS rate_limit (
        ip   TEXT PRIMARY KEY,
        attempts   INTEGER DEFAULT 0,
        locked_until REAL DEFAULT 0,
        last_attempt REAL DEFAULT 0
    )""")
    # Limpiar bloqueos vencidos de sesiones anteriores al arrancar
    import time as _time
    c.execute("DELETE FROM rate_limit WHERE locked_until < ? AND locked_until > 0",
              (_time.time(),))



    # ── Contabilidad: Facturación ─────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS facturas (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        numero          TEXT    UNIQUE NOT NULL,
        tipo            TEXT    NOT NULL DEFAULT 'Factura',
        numero_pedido   TEXT    DEFAULT '',
        cliente_id      INTEGER,
        cliente_nombre  TEXT    DEFAULT '',
        cliente_nit     TEXT    DEFAULT '',
        empresa         TEXT    NOT NULL DEFAULT 'ANIMUS',
        fecha_emision   TEXT    NOT NULL,
        fecha_vencimiento TEXT  DEFAULT '',
        subtotal        REAL    DEFAULT 0,
        descuento       REAL    DEFAULT 0,
        iva_pct         REAL    DEFAULT 0,
        iva_valor       REAL    DEFAULT 0,
        total           REAL    DEFAULT 0,
        estado          TEXT    DEFAULT 'Emitida',
        notas           TEXT    DEFAULT '',
        creado_por      TEXT    DEFAULT '',
        fecha_creacion  TEXT    DEFAULT (datetime('now'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS facturas_items (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_factura  TEXT    NOT NULL,
        sku             TEXT    DEFAULT '',
        descripcion     TEXT    DEFAULT '',
        cantidad        INTEGER DEFAULT 0,
        precio_unitario REAL    DEFAULT 0,
        descuento_pct   REAL    DEFAULT 0,
        subtotal        REAL    DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS facturas_pagos (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_factura  TEXT    NOT NULL,
        fecha           TEXT    NOT NULL,
        monto           REAL    NOT NULL,
        medio           TEXT    DEFAULT 'Transferencia',
        referencia      TEXT    DEFAULT '',
        registrado_por  TEXT    DEFAULT '',
        fecha_creacion  TEXT    DEFAULT (datetime('now'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS config_facturacion (
        empresa         TEXT    NOT NULL,
        anio            INTEGER NOT NULL,
        tipo            TEXT    NOT NULL DEFAULT 'FV',
        siguiente       INTEGER DEFAULT 1,
        PRIMARY KEY (empresa, anio, tipo)
    )""")

    # ─── Migraciones de esquema: aplicar al arranque ─────────────────────────
    run_migrations(conn)

    conn.commit()
    conn.close()

def seed_compromisos(c):
    items = [
        ('Revisar procedimiento limpieza con Fredy â definicion aseo profundo','Miguel Valencia','Calidad','2026-04-17','Completado','Alta','ACTA-ESP-2026-04-14-001','Espagiria'),
        ('Solicitar certificados calibracion viscosimetros a Catalina','Miguel Valencia','Calidad','2026-04-17','Pendiente','Alta','ACTA-ESP-2026-04-14-001','Espagiria'),
        ('Confirmar calibracion viscosimetros con Catalina','Sebastian Vargas','Gerencia','2026-04-17','Pendiente','Alta','ACTA-ESP-2026-04-14-001','Espagiria'),
        ('Enviar correo a Hernando para visto bueno de cronogramas SGD','Sebastian Vargas','Gerencia','2026-04-17','En Proceso','Critico','ACTA-ESP-2026-04-14-001','Espagiria'),
        ('Crear eventos calendario para seguimiento cronogramas SGD','Sebastian Vargas','Gerencia','2026-04-18','Pendiente','Alta','ACTA-ESP-2026-04-14-001','Espagiria'),
        ('Enviar listado de equipos pendientes de rotular','Miguel Valencia','Produccion','2026-04-17','Pendiente','Normal','ACTA-ESP-2026-04-14-001','Espagiria'),
        ('Diligenciar reporte retrospectivo reproceso Renova C10','Laura Gonzalez','Calidad','2026-04-17','Pendiente','Alta','ACTA-ESP-2026-04-14-002','Espagiria'),
        ('Abrir desviacion formalmente y compartir plan de accion','Laura Gonzalez','Calidad','2026-04-18','Pendiente','Critico','ACTA-ESP-2026-04-14-002','Espagiria'),
        ('Enviar rango de llenado real Renova C10 a gerencia','Laura Gonzalez','Calidad','2026-04-17','Pendiente','Alta','ACTA-ESP-2026-04-14-002','Espagiria'),
        ('Revisar procedimiento desviaciones/reprocesos','Laura Gonzalez','Calidad','2026-04-20','Pendiente','Normal','ACTA-ESP-2026-04-14-002','Espagiria'),
        ('Analisis de Causa Raiz formal Renova C10','Fredy Mantilla','Produccion','2026-04-20','Pendiente','Alta','ACTA-ESP-2026-04-14-002','Espagiria'),
        ('Consultar a Hernando que proveedores requieren contrato','Sebastian Vargas','Gerencia','2026-04-19','Pendiente','Alta','ACTA-ESP-2026-04-15-002','Espagiria'),
        ('Corregir sistema generacion rotulos de produccion','Sebastian Vargas','Sistemas','2026-04-20','En Proceso','Alta','ACTA-ESP-2026-04-15-001','Espagiria'),
        ('Reunirse con Fredy y Hernando para ajustar procedimiento desviaciones','Miguel Valencia','Calidad','2026-04-21','Pendiente','Normal','ACTA-ESP-2026-04-14-002','Espagiria'),
        ('Preguntar a Yul sobre coordinacion cronograma sanitizantes','Miguel Valencia','Produccion','2026-04-17','Pendiente','Normal','ACTA-ESP-2026-04-14-001','Espagiria'),
        ('Solicitar a Hernando visto bueno cronograma capacitaciones','Miguel Valencia','Calidad','2026-04-17','Pendiente','Alta','ACTA-ESP-2026-04-14-001','Espagiria'),
    ]
    for it in items:
        try:
            c.execute("""INSERT OR IGNORE INTO compromisos
                (descripcion,responsable,area,fecha_limite,estado,prioridad,origen,empresa,fecha_creacion)
                VALUES (?,?,?,?,?,?,?,?,date('now'))""", it)
        except: pass


def seed_rrhh(c):
    # Guard: solo ejecutar si la tabla estÃ¡ vacÃ­a
    c.execute("SELECT COUNT(*) FROM empleados")
    if c.fetchone()[0] > 0:
        return
    emps = [
        ('EMP0001','Sebastian','Vargas Isaza','1090432100','CEO / Gerente General','Gerencia','HHA Group','Indefinido','2020-01-01',8000000,'Sura','Proteccion','Sura','Comfenalco','sebastian@hhagroup.co','3105001001',1,'Fundador HHA Group'),
        ('EMP0002','Alejandro','Rios Garcia','1090512210','Jefe de Operaciones','Operaciones','Espagiria','Indefinido','2021-03-15',3500000,'Sura','Colpensiones','Sura','Comfenalco','alejandro@espagiria.co','3112002002',2,'Encargado produccion e inventarios'),
        ('EMP0003','Catalina','Torres Mejia','1043218870','Coordinadora Control de Calidad','Control de Calidad','Espagiria','Indefinido','2022-01-10',2800000,'Sanitas','Proteccion','Sura','Comfenalco','catalina@espagiria.co','3203003003',1,'Responsable BPM y CC'),
        ('EMP0004','Luz Marina','Cardona','1090388900','Contadora','Administrativa','HHA Group','Indefinido','2021-07-01',2500000,'Nueva EPS','Colpensiones','Bolivar','Comfenalco','luz@hhagroup.co','3154004004',1,'Contabilidad y nomina'),
        ('EMP0005','Mayra','Jimenez Cano','1092101530','Asistente Administrativa','Administrativa','HHA Group','Fijo','2023-02-01',1800000,'Sura','Porvenir','Bolivar','Comfenalco','mayra@hhagroup.co','3165005005',1,'Apoyo administrativo'),
        ('EMP0006','Carlos','Herrera Zapata','1090600610','Operario de Planta','Planta','Espagiria','Indefinido','2022-09-01',1500000,'Nueva EPS','Colpensiones','Sura','Comfenalco','carlos@espagiria.co','3176006006',3,'Operaciones de manufactura'),
        ('EMP0007','Ana Patricia','Rodriguez','1043320780','Tecnica de Laboratorio','Laboratorio','Espagiria','Indefinido','2023-05-15',2000000,'Sanitas','Porvenir','Sura','Comfenalco','ana@espagiria.co','3187007007',2,'Formulacion y control'),
    ]
    for e in emps:
        try:
            c.execute("INSERT OR IGNORE INTO empleados (codigo,nombre,apellido,cedula,cargo,area,empresa,tipo_contrato,fecha_ingreso,salario_base,eps,afp,arl,caja_compensacion,email,telefono,nivel_riesgo,observaciones) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", e)
        except: pass

    caps = [
        ('BPM â Buenas Practicas de Manufactura Cosmeticos','BPM','2026-01-15',8,'INVIMA / ANDI','Espagiria',1),
        ('SGSST â Induccion y Reinduccion Seguridad','SGSST','2026-01-20',4,'ARL Sura','HHA Group',1),
        ('Manejo Seguro de Materias Primas Quimicas','SGSST','2026-02-10',6,'Proveedor externo','Espagiria',1),
        ('Atencion al Cliente y Comunicacion Efectiva','Blanda','2026-03-05',3,'Coach externo','HHA Group',0),
        ('Control de Calidad â Metodos Analiticos','Tecnica','2026-03-20',5,'Catalina Torres','Espagiria',1),
    ]
    cap_ids = []
    for cap in caps:
        c.execute("INSERT INTO capacitaciones (nombre,tipo,fecha,duracion_horas,instructor,empresa,obligatoria) VALUES (?,?,?,?,?,?,?)", cap)
        cap_ids.append(c.lastrowid)
    c.execute("SELECT id FROM empleados")
    emp_ids = [r[0] for r in c.fetchall()]
    import random
    for cap_id in cap_ids:
        for emp_id in emp_ids:
            completado = 1 if random.random() > 0.4 else 0
            fecha_c = '2026-02-15' if completado else ''
            try:
                c.execute("INSERT OR IGNORE INTO capacitaciones_empleados (capacitacion_id,empleado_id,completado,fecha_completado) VALUES (?,?,?,?)", (cap_id,emp_id,completado,fecha_c))
            except: pass

    sgsst = [
        ('Medicina del Trabajo','Examenes medicos ocupacionales de ingreso','Anual','Catalina Torres','2026-12-01'),
        ('Medicina del Trabajo','Examenes medicos periodicos â todo el personal','Anual','Catalina Torres','2026-06-30'),
        ('Medicina del Trabajo','Programa de vigilancia epidemiologica respiratoria','Semestral','Catalina Torres','2026-06-01'),
        ('Higiene Industrial','Medicion de iluminacion en planta y laboratorio','Anual','Alejandro Rios','2026-08-01'),
        ('Higiene Industrial','Evaluacion de exposicion a sustancias quimicas','Semestral','Catalina Torres','2026-06-15'),
        ('Seguridad','Inspeccion de instalaciones locativas y equipos','Trimestral','Alejandro Rios','2026-04-30'),
        ('Seguridad','Revision y dotacion de EPP â todo personal planta','Semestral','Alejandro Rios','2026-07-01'),
        ('Seguridad','SeÃ±alizacion de seguridad actualizada','Anual','Alejandro Rios','2026-09-01'),
        ('Emergencias','Plan de emergencia y evacuacion actualizado','Anual','Sebastian Vargas','2026-11-01'),
        ('Emergencias','Simulacro de evacuacion','Semestral','Sebastian Vargas','2026-06-01'),
        ('Emergencias','Revision extintores y kit de primeros auxilios','Trimestral','Alejandro Rios','2026-04-15'),
        ('Capacitacion SGSST','Capacitacion BPM anual obligatoria','Anual','Catalina Torres','2026-12-31'),
        ('Capacitacion SGSST','Induccion SGSST nuevos ingresos','Mensual','Catalina Torres','2026-04-30'),
        ('Vigilancia Epidemiologica','Reporte ATEL (accidentes y enfermedades laborales)','Mensual','Catalina Torres','2026-04-30'),
    ]
    for idx, sg in enumerate(sgsst):
        estado = 'Cumplido' if idx % 3 == 0 else 'Pendiente'
        ultimo = '2026-01-15' if estado == 'Cumplido' else ''
        c.execute("INSERT INTO sgsst_items (categoria,descripcion,frecuencia,responsable,proximo_vencimiento,estado,ultimo_cumplimiento) VALUES (?,?,?,?,?,?,?)", (sg[0],sg[1],sg[2],sg[3],sg[4],estado,ultimo))

    evals = [
        (1,'2025-Q4','alejandro',4.5,5.0,4.5,4.5,4.0,4.5,'Liderazgo estrategico sobresaliente.'),
        (2,'2025-Q4','sebastian',4.2,4.5,4.0,4.5,4.0,4.0,'Excelente gestion de inventarios y equipo.'),
        (3,'2025-Q4','alejandro',4.6,5.0,4.5,4.5,4.5,4.5,'Conocimiento tecnico BPM excepcional.'),
        (4,'2025-Q4','alejandro',4.0,4.0,4.5,4.0,4.0,3.5,'Buen manejo contable y financiero.'),
        (5,'2025-Q4','alejandro',3.5,3.5,4.0,3.5,3.5,3.0,'Buena actitud, en proceso de desarrollo.'),
        (6,'2025-Q4','alejandro',3.8,4.0,4.0,4.0,3.5,3.5,'Operario comprometido con calidad.'),
        (7,'2025-Q4','alejandro',4.3,4.5,4.5,4.0,4.5,4.0,'Aportes valiosos en formulacion.'),
    ]
    for i,ev in enumerate(evals):
        total = round((ev[4]+ev[5]+ev[6]+ev[7]+ev[8])/5,1)
        c.execute("INSERT INTO evaluaciones (empleado_id,periodo,evaluador,puntaje_total,puntaje_calidad,puntaje_asistencia,puntaje_actitud,puntaje_conocimiento,puntaje_productividad,comentarios,estado) VALUES (?,?,?,?,?,?,?,?,?,?,'Publicada')", (ev[0],ev[1],ev[2],total,ev[4],ev[5],ev[6],ev[7],ev[8],ev[9]))


def apply_production_corrections(c):
    """One-time corrections for known data-entry errors in producciones."""
    # ── Correction 1: EMULSION LIMPIADORA NF 2026-04-22 ──────────────────────
    # Luis entered 20,000 kg instead of 20 kg (1000x over-consumption of 21 MPs)
    # Guard: skip if already corrected
    c.execute("""SELECT COUNT(*) FROM movimientos
                 WHERE tipo='Entrada'
                 AND observaciones LIKE '%CORRECCION%EMULSION LIMPIADORA NF%20000kg%'""")
    already_done = c.fetchone()[0]
    if already_done:
        return

    c.execute("""SELECT id FROM producciones
                 WHERE producto='EMULSION LIMPIADORA NF'
                 AND cantidad=20000
                 AND fecha LIKE '2026-04-22%'""")
    bad_prod = c.fetchone()
    if not bad_prod:
        return  # Either already fixed or doesn't exist

    # Get all erroneous Salida movements from that production
    c.execute("""SELECT id, material_id, material_nombre, cantidad
                 FROM movimientos
                 WHERE tipo='Salida'
                 AND fecha LIKE '2026-04-22%'
                 AND (observaciones LIKE '%EMULSION LIMPIADORA%' OR observaciones LIKE '%PROD-00007%')
                 AND observaciones NOT LIKE '[ANULADO]%'
                 AND observaciones NOT LIKE '[ANULACION]%'""")
    bad_movs = c.fetchall()
    if not bad_movs:
        return

    # Create corrective Entrada for 999/1000 of each erroneous Salida
    for mov_id, mat_id, mat_nom, qty in bad_movs:
        correction = round(qty * 999.0 / 1000.0, 4)
        c.execute("""INSERT INTO movimientos
                     (material_id, material_nombre, cantidad, tipo, observaciones, fecha)
                     VALUES (?,?,?,'Entrada',?,datetime('now'))""",
                  (mat_id, mat_nom, correction,
                   f'[CORRECCION] Error ingreso EMULSION LIMPIADORA NF 2026-04-22: '
                   f'registrada como 20000kg era 20kg. Restaura {correction}g (mov#{mov_id})'))

    # Fix the production record
    c.execute("""UPDATE producciones SET cantidad=20
                 WHERE producto='EMULSION LIMPIADORA NF'
                 AND cantidad=20000
                 AND fecha LIKE '2026-04-22%'""")

    try:
        c.execute("""INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                     VALUES ('sistema','CORRECCION_PRODUCCION','producciones','auto',
                     'EMULSION LIMPIADORA NF 2026-04-22: cantidad 20000kg→20kg. '
                     'Entradas correctivas para 21 MPs generadas automaticamente.',
                     '127.0.0.1', datetime('now'))""")
    except Exception:
        pass


def run_seed_rrhh():
    """Ejecuta seed_rrhh con su propia conexiÃ³n (llamada al arranque)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    seed_rrhh(c)
    conn.commit()
    conn.close()
