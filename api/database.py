# database.py â inicializaciÃ³n de BD y seeds
# Fase B refactor: extraÃ­do de index.py
import os
import sqlite3
import random
from datetime import datetime

from config import DB_PATH


def _configure_conn(conn):
    """Aplica pragmas de performance y seguridad a cada conexion SQLite.

    Sebastian 16-may-2026: BD corrompida 4 veces en 2 dias ('database
    disk image is malformed' / 'disk I/O error'). Causa raiz: WAL mode
    usa un archivo de memoria compartida (-shm) via mmap; el disco
    persistente de Render no es local sino un volumen montado, y mmap
    sobre filesystem de red corrompe el WAL.
    FIX: journal_mode=DELETE (el default robusto de SQLite). No usa
    -wal ni -shm, no depende de mmap. Mas lento bajo concurrencia
    (un escritor bloquea), pero con busy_timeout=15s y el bajo volumen
    de este ERP es perfectamente aceptable. synchronous=FULL para
    maxima durabilidad (cada commit se fuerza a disco).
    busy_timeout: los workers esperan por el lock de escritura en
    lugar de fallar — elimina 'database is locked'.
    """
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=DELETE")  # robusto en disco de red
    conn.execute("PRAGMA synchronous=FULL")     # maxima durabilidad
    conn.execute("PRAGMA cache_size=-20000")    # 20MB cache (negativo = KB)
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA busy_timeout=15000")   # 15s espera por lock — multi-worker
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _usa_postgres() -> bool:
    """True si el backend es PostgreSQL (migración Fase 3+).

    Por DEFAULT es False -> SQLite, producción sin cambios. Solo se activa
    seteando EOS_DB_BACKEND=postgres en el entorno.
    """
    return os.environ.get('EOS_DB_BACKEND', '').strip().lower() == 'postgres'


def _abrir_conn():
    """Abre una conexión nueva del backend configurado."""
    if _usa_postgres():
        # Import perezoso · en modo SQLite no se necesita psycopg instalado.
        from pg_adapter import connect as _pg_connect
        return _pg_connect()
    return _configure_conn(sqlite3.connect(DB_PATH))


def db_connect(*args, **kwargs):
    """Conexión nueva al backend activo · para call sites que abren y
    cierran su propia conexión (fuera del scope per-request de get_db()).

    Migración Fase 3: ~135 call sites hacían `sqlite3.connect(DB_PATH)`
    directo, saltándose get_db(). Este helper los hace conmutables.

    SQLite: equivale a `sqlite3.connect(DB_PATH, ...)` — producción sin
    cambios (los args extra, p.ej. timeout, se pasan tal cual). Postgres:
    devuelve el adaptador (los kwargs estilo SQLite se ignoran).
    """
    if _usa_postgres():
        from pg_adapter import connect as _pg_connect
        return _pg_connect()
    return sqlite3.connect(DB_PATH, *args, **kwargs)


def get_db():
    """Conexion per-request usando Flask g (patron recomendado Flask).

    Backend conmutable: SQLite (default) o PostgreSQL si EOS_DB_BACKEND=
    postgres. Cerrada automaticamente por teardown_appcontext al final del
    request incluyendo error paths.
    """
    try:
        from flask import g
        if "db" not in g:
            g.db = _abrir_conn()
        return g.db
    except RuntimeError:
        # Sin app context: scripts de init, tests, herramientas CLI
        return _abrir_conn()


def recepcion_auto_vigente(conn=None):
    """Sebastián 16-jun · interruptor 'recepción entra directo a inventario' (sin
    cuarentena de Calidad · día de inventario). Resolución:
      1) app_settings.clave='recepcion_auto_vigente' (toggle desde la UI · admin ·
         NO requiere variable de entorno en Render · efecto inmediato y reversible).
      2) si no hay fila en BD → variable de entorno RECEPCION_AUTO_VIGENTE.
    Default OFF = posición INVIMA (cuarentena-first). Lo apaga el mismo botón.
    """
    try:
        c = conn or get_db()
        row = c.execute(
            "SELECT valor FROM app_settings WHERE clave='recepcion_auto_vigente' LIMIT 1"
        ).fetchone()
        if row is not None and row[0] is not None:
            return str(row[0]).strip().lower() in ("1", "true", "yes", "si", "sí", "on")
    except Exception:
        pass  # tabla ausente / sin conexión → cae al env
    try:
        from config import recepcion_auto_vigente_env
        return recepcion_auto_vigente_env()
    except Exception:
        return False


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


# Mig 121 SQL statements vienen del módulo api/mig_121_formulas_data.py
# (generado por scripts/generate_mig_121_formulas.py desde Excel Alejandro mayo-2026)
try:
    from mig_121_formulas_data import STATEMENTS as _MIG_121_STMTS
except ImportError:
    try:
        from api.mig_121_formulas_data import STATEMENTS as _MIG_121_STMTS
    except ImportError:
        _MIG_121_STMTS = []  # falla silenciosa si archivo no existe en deploy

# Mig 127 SQL statements vienen del módulo api/mig_127_data.py
# (generado por scripts/generate_mig_127_reimport.py · regenera desde Excel
# completo: maestro_mps + formula_headers + formula_items con agua q.s.p.)
try:
    from mig_127_data import STATEMENTS as _MIG_127_STMTS
except ImportError:
    try:
        from api.mig_127_data import STATEMENTS as _MIG_127_STMTS
    except ImportError:
        _MIG_127_STMTS = []

# Mig 130 SQL statements · canónicos 12 meses con frecuencias confirmadas
# Sebastián (LIMP BHA 200/45d, LKJ 90/60d, SAH 90/90d, etc · 7 productos)
try:
    from mig_130_canonicos_data import STATEMENTS as _MIG_130_STMTS
except ImportError:
    try:
        from api.mig_130_canonicos_data import STATEMENTS as _MIG_130_STMTS
    except ImportError:
        _MIG_130_STMTS = []

# Mig 136 · PLAN LIMPIO · cancela TODO y genera solo eos_canonico
# Sebastián 14-may-2026: "quiero que quede solo una cosa, canónico"
try:
    from mig_136_plan_limpio_data import STATEMENTS as _MIG_136_STMTS
except ImportError:
    try:
        from api.mig_136_plan_limpio_data import STATEMENTS as _MIG_136_STMTS
    except ImportError:
        _MIG_136_STMTS = []

try:
    from mig_137_plan_denso_data import STATEMENTS as _MIG_137_STMTS
except ImportError:
    try:
        from api.mig_137_plan_denso_data import STATEMENTS as _MIG_137_STMTS
    except ImportError:
        _MIG_137_STMTS = []

try:
    from mig_246_micro_microlab_data import STATEMENTS as _MIG_246_STMTS
except ImportError:
    try:
        from api.mig_246_micro_microlab_data import STATEMENTS as _MIG_246_STMTS
    except ImportError:
        _MIG_246_STMTS = []

try:
    from mig_248_micro_fechas_data import STATEMENTS as _MIG_248_STMTS
except ImportError:
    try:
        from api.mig_248_micro_fechas_data import STATEMENTS as _MIG_248_STMTS
    except ImportError:
        _MIG_248_STMTS = []

MIGRATIONS: list[tuple[int, str, list[str]]] = [
    (262, "Multi-volumen por SKU (Sebastián 16-jun): volumen_ml por SKU en "
          "sku_producto_map · un producto puede venderse en varios tamaños (30+10, "
          "30+15, o solo 30). La planeación pasa a GRAMOS (demanda = Σ ventas×volumen "
          "por tamaño). 'duplicate column' benigno.", [
        "ALTER TABLE sku_producto_map ADD COLUMN volumen_ml REAL",
    ]),
    (261, "Planeación por VOLUMEN directo (Sebastián 16-jun): volumen_ml_unidad por "
          "producto en sku_planeacion_config · si está, el cálculo kg→unidades lo usa "
          "PRIMERO (exacto), sin depender de presentaciones/envase. 'duplicate column' "
          "es benigno (idempotente).", [
        "ALTER TABLE sku_planeacion_config ADD COLUMN volumen_ml_unidad REAL",
    ]),
    (260, "Renombrar MAXLASH → ANIMUSLASH (Sebastián 16-jun) en fórmula, Necesidades "
          "(sku_planeacion_config + sku_producto_map), presentaciones y producciones "
          "programadas. + arregla el Vit E de esa fórmula: MPTOCOFE01 (Sodium Tocoferil "
          "Fosfato · código fantasma, no cruzaba) → MP00078 (Vitamina E líquida · "
          "TOCOPHEROL, activo). Renombrado vía UPDATE de producto_nombre (NO toca "
          "material_id · no dispara el trigger FK). 'no such table/column' es benigno.", [
        "UPDATE formula_items SET producto_nombre='ANIMUSLASH' WHERE producto_nombre='MAXLASH'",
        "UPDATE formula_headers SET producto_nombre='ANIMUSLASH', producto_canonico='ANIMUSLASH' WHERE producto_nombre='MAXLASH'",
        "UPDATE formula_headers SET producto_canonico='ANIMUSLASH' WHERE producto_canonico='MAXLASH'",
        # Vit E real (después del rename · WHERE ya es ANIMUSLASH) · UPDATE OF material_id pasa el trigger (MP00078 activo)
        "UPDATE formula_items SET material_id='MP00078', material_nombre='Vitamina E liquida' WHERE producto_nombre='ANIMUSLASH' AND material_id='MPTOCOFE01'",
        # Necesidades + ventas + presentaciones + calendario
        "UPDATE sku_planeacion_config SET producto_nombre='ANIMUSLASH' WHERE producto_nombre='MAXLASH'",
        "UPDATE sku_producto_map SET producto_nombre='ANIMUSLASH' WHERE producto_nombre='MAXLASH'",
        "UPDATE producto_presentaciones SET producto_nombre='ANIMUSLASH' WHERE producto_nombre='MAXLASH'",
        "UPDATE produccion_programada SET producto='ANIMUSLASH' WHERE producto='MAXLASH'",
        "UPDATE producto_canonico_config SET producto_nombre='ANIMUSLASH' WHERE producto_nombre='MAXLASH'",
    ]),
    (259, "Fórmula NUEVA · CREMA FACIAL UREA 10 (Sebastián 16-jun): carga la formulación "
          "final mapeada a los códigos MP exactos de la app para que descuente bien al "
          "producir. + normaliza MP00040 (Cetiol → Cetiol CC · INCI DICAPRYLYL CARBONATE, "
          "estaba en blanco) y MP00078 (Vit E líquida · INCI TOCOPHEROL). Idempotente "
          "(borra y recarga la fórmula). Lote default 30kg · ajustar al programar. "
          "INSERTs de una sola fila c/u (PG-safe, sin multi-row + RETURNING).", [
        # Normalización de MPs (solo setea el INCI/nombre · no toca stock)
        "UPDATE maestro_mps SET nombre_comercial='Cetiol CC', nombre_inci='DICAPRYLYL CARBONATE' "
        "WHERE codigo_mp='MP00040'",
        "UPDATE maestro_mps SET nombre_inci='TOCOPHEROL' "
        "WHERE codigo_mp='MP00078' AND COALESCE(nombre_inci,'')=''",
        # CRÍTICO · trigger formula_items exige material_id en maestro_mps activo=1.
        # Garantizamos que los 22 MP de la fórmula existan y estén ACTIVOS antes de
        # insertar (si alguno quedó inactivo/ausente en prod desde el 28-may, la mig
        # fallaba con 'FK violation'). Reversible: el usuario re-desactiva si aplica.
        "UPDATE maestro_mps SET activo=1 WHERE codigo_mp IN ('MPAGUALI01','MP00107','MP00195','MP00043','MP00148','MP00262','MP00245','MP00215','MP00110','MP00226','MP00223','MP00008','MP00006','MP00254','MP00040','MP00184','MP00240','MP00078','MP00233','MP00163','MP00068','MP00123') AND COALESCE(activo,0)<>1",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MPAGUALI01','Agua Desionizada','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MPAGUALI01')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00107','Urea','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00107')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00195','Glicerina','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00195')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00043','Propanediol','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00043')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00148','Niacinamida','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00148')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00262','N-acetil glucosamina','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00262')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00245','1,2-Hexanediol','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00245')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00215','Betaina','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00215')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00110','Pantenol','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00110')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00226','Ectoina','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00226')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00223','PDRN','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00223')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00008','Carbopol','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00008')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00006','Pemulen EZ-4U','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00006')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00254','C13-C15 Alkane','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00254')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00040','Cetiol CC','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00040')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00184','BM-939','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00184')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00240','Cetyl tranexamate','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00240')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00078','Vitamina E liquida','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00078')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00233','Ac. hialuronico 300 kD','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00233')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00163','Ac. hialuronico 50 kD','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00163')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00068','Biosure FE','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00068')",
        "INSERT INTO maestro_mps (codigo_mp,nombre_comercial,tipo_material,activo) SELECT 'MP00123','Trietanolamina 85','MP',1 WHERE NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp='MP00123')",
        # Fórmula idempotente (sin '%' en el nombre · evita cualquier riesgo de paramstyle PG)
        "DELETE FROM formula_items WHERE producto_nombre='CREMA FACIAL UREA 10'",
        "DELETE FROM formula_headers WHERE producto_nombre='CREMA FACIAL UREA 10'",
        "INSERT INTO formula_headers (producto_nombre, unidad_base_g, descripcion, fecha_creacion, "
        "lote_size_kg, activo, producto_canonico) VALUES "
        "('CREMA FACIAL UREA 10', 1000, 'Crema facial urea 10 por ciento - pH 6.5 - neutraliza TEA "
        "- conserva BioSure FE 1 por ciento', '2026-06-16', 30, 1, 'CREMA FACIAL UREA 10')",
        # Items: una fila por INSERT (bulletproof en PG)
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MPAGUALI01','Agua Desionizada',67.8)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00107','Urea',10.0)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00195','Glicerina',3.0)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00043','Propanediol',3.0)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00148','Niacinamida',3.0)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00262','N-acetil glucosamina',1.0)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00245','1,2-Hexanediol',0.5)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00215','Betaina',0.3)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00110','Pantenol',0.1)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00226','Ectoina',0.05)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00223','PDRN',0.05)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00008','Carbopol',0.1)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00006','Pemulen EZ-4U',0.4)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00254','C13-C15 Alkane',3.0)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00040','Cetiol CC',3.0)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00184','BM-939 PEG-12 Dimethicone',2.0)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00240','Cetyl tranexamate',1.0)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00078','Vitamina E liquida',0.3)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00233','Ac. hialuronico 300 kD',0.15)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00163','Ac. hialuronico 50 kD',0.15)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00068','Biosure FE',1.0)",
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('CREMA FACIAL UREA 10','MP00123','Trietanolamina 85 pct',0.1)",
    ]),
    (258, "Necesidades · forzar re-sync de imágenes Shopify (15-jun): limpia shopify_synced_at "
          "de los productos SIN imagen para que el sync en background los vuelva a buscar con "
          "el nuevo match por SKU (más confiable que por nombre) y traiga la foto al modal. "
          "One-time; el sync lazy (al ver páginas) los re-procesa 50 a la vez.", [
        "UPDATE formula_headers SET shopify_synced_at='' WHERE COALESCE(imagen_url,'')=''",
    ]),
    (257, "PQRSF · alinear con el SOP real ASG-PRO-003 'Manejo de PQRSF' (15-jun): carga el "
          "documento vigente + su formato F01 en el SGD con link de Drive, corrige el código "
          "mal sembrado (ASG-PRO-013 → obsoleto), y agrega columnas PQRSF (clase + criticidad "
          "Bajo/Medio/Alto) + SLA (fecha_limite_respuesta 15 días hábiles) + acuse de recibo.", [
        # SGD: el código real es ASG-PRO-003, no 013 (que fue una suposición del seed)
        "UPDATE sgd_documentos SET estado='obsoleto', observaciones='Código corregido → ASG-PRO-003 (Manejo de PQRSF)' WHERE codigo='ASG-PRO-013'",
        "INSERT OR IGNORE INTO sgd_documentos (codigo,area,tipo_doc,numero,titulo,version_actual,"
        "archivo_pdf_url,estado,vigente_desde,proxima_revision,aprobado_por,observaciones,creado_por) VALUES "
        "('ASG-PRO-003','ASG','PRO',3,'Manejo de PQRSF','01',"
        "'https://drive.google.com/file/d/1AeEtQqPmi3rd1alO_pqJHyR2YX0Duxqu/view',"
        "'vigente','2025-05-30','2028-05-29','Director Técnico','Cargado del SGD (Drive)','seed_mig257')",
        "INSERT OR IGNORE INTO sgd_documentos (codigo,area,tipo_doc,numero,subtipo,titulo,version_actual,"
        "padre_codigo,archivo_pdf_url,estado,vigente_desde,proxima_revision,creado_por) VALUES "
        "('ASG-PRO-003-F01','ASG','FOR',1,'F01','Reporte de PQRSF','01','ASG-PRO-003',"
        "'https://drive.google.com/file/d/1hP2pZ8aNoWAjK5ysab8cDKkEEb_o0PNa/view',"
        "'vigente','2025-05-27','2028-05-26','seed_mig257')",
        # quejas_clientes: clase PQRSF + criticidad + SLA + acuse
        "ALTER TABLE quejas_clientes ADD COLUMN clase_pqrsf TEXT",
        "ALTER TABLE quejas_clientes ADD COLUMN criticidad TEXT",
        "ALTER TABLE quejas_clientes ADD COLUMN fecha_limite_respuesta TEXT",
        "ALTER TABLE quejas_clientes ADD COLUMN acuse_enviado_at TEXT",
        # pqr_inbox: sugerencia IA de clase + criticidad (se ve en triaje)
        "ALTER TABLE pqr_inbox ADD COLUMN ia_clase TEXT",
        "ALTER TABLE pqr_inbox ADD COLUMN ia_criticidad TEXT",
    ]),
    (256, "PQR · limpieza one-time de las entradas de PRUEBA de la integración GHL (14-jun). "
          "Borra los PQR de prueba de pqr_inbox y sus quejas/animus_pqr enrutados (vía el "
          "vínculo destino_id). Marcadores distintivos de test → no toca datos reales; corre "
          "una sola vez. En BD sin esos datos (test/fresca) no borra nada.", [
        # Hijos enrutados DESDE un inbox de prueba (por linkage destino_id) — primero los hijos
        "DELETE FROM quejas_clientes WHERE id IN (SELECT destino_id FROM pqr_inbox WHERE "
        "destino_tabla='quejas_clientes' AND destino_id IS NOT NULL AND ("
        "mensaje LIKE '%[PRUEBA%' OR contacto_nombre LIKE 'Demo %' OR contacto_nombre LIKE 'ZZ Prueba%' "
        "OR ghl_message_id LIKE 'demo-%' OR ghl_message_id LIKE 'TEST-%' OR ghl_message_id LIKE 'AUTO35-%' "
        "OR ghl_message_id LIKE 'trazabilidad-%' OR ghl_message_id LIKE 'diag-%'))",
        "DELETE FROM animus_pqr WHERE id IN (SELECT destino_id FROM pqr_inbox WHERE "
        "destino_tabla='animus_pqr' AND destino_id IS NOT NULL AND ("
        "mensaje LIKE '%[PRUEBA%' OR contacto_nombre LIKE 'Demo %' OR contacto_nombre LIKE 'ZZ Prueba%' "
        "OR ghl_message_id LIKE 'demo-%' OR ghl_message_id LIKE 'TEST-%' OR ghl_message_id LIKE 'AUTO35-%' "
        "OR ghl_message_id LIKE 'trazabilidad-%' OR ghl_message_id LIKE 'diag-%'))",
        # Y por fin las entradas de prueba del buzón
        "DELETE FROM pqr_inbox WHERE "
        "mensaje LIKE '%[PRUEBA%' OR contacto_nombre LIKE 'Demo %' OR contacto_nombre LIKE 'ZZ Prueba%' "
        "OR ghl_message_id LIKE 'demo-%' OR ghl_message_id LIKE 'TEST-%' OR ghl_message_id LIKE 'AUTO35-%' "
        "OR ghl_message_id LIKE 'trazabilidad-%' OR ghl_message_id LIKE 'diag-%'",
    ]),
    (255, "PQR · trazabilidad desde GHL (14-jun): producto/lote (calidad) y nº de pedido "
          "(comercial) leídos de los custom fields del contacto. Columnas en pqr_inbox + "
          "pedido_numero en animus_pqr (quejas_clientes ya tiene producto/lote).", [
        "ALTER TABLE pqr_inbox ADD COLUMN producto TEXT",
        "ALTER TABLE pqr_inbox ADD COLUMN lote TEXT",
        "ALTER TABLE pqr_inbox ADD COLUMN pedido_numero TEXT",
        "ALTER TABLE animus_pqr ADD COLUMN pedido_numero TEXT",
    ]),
    (254, "PQR omnicanal (14-jun): bandeja de triaje desde GHL (pqr_inbox · webhook "
          "/api/pqr/inbound · clasificación IA Espagiria vs Ánimus) + tabla animus_pqr "
          "(PQR comercial: envíos, producto equivocado, devoluciones, servicio). Los de "
          "calidad (Espagiria) se enrutan a quejas_clientes; los comerciales a animus_pqr.", [
        """CREATE TABLE IF NOT EXISTS pqr_inbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ghl_message_id TEXT UNIQUE,
            ghl_contact_id TEXT,
            canal TEXT DEFAULT 'otro',
            contacto_nombre TEXT,
            contacto_email TEXT,
            contacto_telefono TEXT,
            mensaje TEXT NOT NULL,
            recibido_en TEXT,
            ia_empresa TEXT,
            ia_tipo TEXT,
            ia_severidad TEXT,
            ia_confianza REAL,
            ia_resumen TEXT,
            ia_razon TEXT,
            ia_fuente TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente'
                CHECK(estado IN ('pendiente','enrutado','descartado')),
            destino_empresa TEXT,
            destino_tabla TEXT,
            destino_id INTEGER,
            enrutado_por TEXT,
            enrutado_en TEXT,
            descartado_por TEXT,
            motivo_descarte TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_pqr_inbox_estado ON pqr_inbox(estado, creado_en)",
        """CREATE TABLE IF NOT EXISTS animus_pqr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE,
            canal TEXT DEFAULT 'otro',
            contacto_nombre TEXT,
            contacto_email TEXT,
            contacto_telefono TEXT,
            ghl_contact_id TEXT,
            tipo TEXT NOT NULL DEFAULT 'otro'
                CHECK(tipo IN ('envio','producto_equivocado','faltante','devolucion',
                               'servicio','facturacion','comercial','otro')),
            descripcion TEXT NOT NULL,
            prioridad TEXT NOT NULL DEFAULT 'media'
                CHECK(prioridad IN ('alta','media','baja')),
            estado TEXT NOT NULL DEFAULT 'nuevo'
                CHECK(estado IN ('nuevo','en_proceso','resuelto','cerrado')),
            asignado_a TEXT,
            respuesta TEXT,
            respondido_por TEXT,
            respondido_en TEXT,
            origen_inbox_id INTEGER,
            creado_por TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            actualizado_en TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_animus_pqr_estado ON animus_pqr(estado, creado_en)",
    ]),
    (253, "Aseguramiento · cuadro de indicadores cross-módulo (14-jun): tabla "
          "aseguramiento_kpi_metas (meta+umbral+dirección+semáforo) con seed de los KPIs "
          "que el sistema de calidad debe cumplir — propios de Aseguramiento + de Planta + "
          "de Calidad. Idéntico patrón a calidad_kpi_metas (mig 244). Idempotente.", [
        """CREATE TABLE IF NOT EXISTS aseguramiento_kpi_metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            unidad TEXT DEFAULT '%',
            direccion TEXT NOT NULL DEFAULT 'mayor_mejor'
                CHECK(direccion IN ('mayor_mejor','menor_mejor')),
            meta REAL,
            umbral_amarillo REAL,
            categoria TEXT DEFAULT 'aseguramiento',
            orden INTEGER DEFAULT 100,
            activo INTEGER NOT NULL DEFAULT 1,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_asg_kpi_orden ON aseguramiento_kpi_metas(orden, activo)",
        # Seed · meta/umbral razonables · dirección define el semáforo
        "INSERT OR IGNORE INTO aseguramiento_kpi_metas (codigo,nombre,descripcion,unidad,direccion,meta,umbral_amarillo,categoria,orden) VALUES "
        "('desv_a_tiempo','Desviaciones cerradas a tiempo','% de desviaciones cerradas dentro del SLA (30 días desde su apertura).','%','mayor_mejor',90,75,'aseguramiento',10),"
        "('desv_abiertas','Desviaciones abiertas','Número de desviaciones sin cerrar (incluye críticas).','#','menor_mejor',3,6,'aseguramiento',20),"
        "('capa_a_tiempo','CAPA cerradas a tiempo','% de acciones CAPA ejecutadas dentro de la fecha comprometida.','%','mayor_mejor',90,75,'aseguramiento',30),"
        "('cambios_invima_ok','Cambios INVIMA notificados a tiempo','% de cambios que requieren INVIMA notificados ANTES de implementar.','%','mayor_mejor',100,90,'aseguramiento',40),"
        "('quejas_sla','Quejas/PQR respondidas en SLA','% de quejas de cliente respondidas dentro de 15 días.','%','mayor_mejor',90,70,'aseguramiento',50),"
        "('recalls_abiertos','Recalls abiertos','Número de retiros de producto en curso.','#','menor_mejor',0,1,'aseguramiento',60),"
        "('sgd_vigente_pct','Documentos SGD vigentes','% de documentos del SGD vigentes (no vencidos).','%','mayor_mejor',95,85,'documental',70),"
        "('capacitacion_cumplimiento','Capacitación al día','% de capacitaciones SGD asignadas que ya fueron firmadas/leídas.','%','mayor_mejor',90,70,'documental',80),"
        "('cronogramas_cumplimiento','Cumplimiento cronogramas BPM','% promedio de ejecución de los cronogramas BPM del año (capacitación, mantenimiento, fumigación, micro, duchas).','%','mayor_mejor',90,70,'documental',90),"
        "('proveedores_criticos_ok','Proveedores críticos aprobados','% de proveedores críticos con calificación aprobada.','%','mayor_mejor',95,80,'aseguramiento',100),"
        "('rft_mp','RFT materia prima','Right First Time: % de lotes de MP aprobados sin rechazo (Control de Calidad).','%','mayor_mejor',95,90,'planta',110),"
        "('liberacion_pt','Liberación de PT','% de producto terminado liberado vs rechazado (Calidad).','%','mayor_mejor',95,90,'planta',120),"
        "('oos_abiertos','OOS abiertos','Resultados fuera de especificación sin cerrar (Calidad).','#','menor_mejor',0,2,'planta',130)",
    ]),
    (252, "Aseguramiento · 5 elementos de gobierno GMP (14-jun): (a) revision_direccion "
          "(Revisión por la Dirección / APR anual · INVIMA Res.2214 art.8), (b) "
          "proveedores_calificacion (aprobación + reevaluación + protocolo de visita · reusa "
          "proveedores de compras y su scorecard), (c) validacion_equipos (IQ/OQ/PQ/CSV · reusa "
          "equipos_planta), (d) producto_fmea (riesgo ICH Q9), (e) acuerdos_calidad (quality "
          "agreements maquila). Solo tablas; los datos base se reusan de los módulos existentes.", [
        # (a) Revisión por la Dirección
        """CREATE TABLE IF NOT EXISTS revision_direccion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            periodo TEXT NOT NULL,
            fecha_planeada TEXT,
            fecha_ejecutada TEXT,
            conducido_por TEXT,
            participantes TEXT,
            kpis_json TEXT,
            fortalezas TEXT,
            debilidades TEXT,
            decisiones TEXT,
            acciones_mejora TEXT,
            acta_url TEXT,
            estado TEXT NOT NULL DEFAULT 'planeada'
                CHECK(estado IN ('planeada','ejecutada','cerrada')),
            signature_id INTEGER,
            creado_por TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_rev_dir_estado ON revision_direccion(estado, periodo)",
        # (b) Calificación de proveedores (reusa proveedores de compras + scorecard)
        """CREATE TABLE IF NOT EXISTS proveedores_calificacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proveedor TEXT NOT NULL UNIQUE,
            criticidad TEXT NOT NULL DEFAULT 'no_critico'
                CHECK(criticidad IN ('critico','no_critico')),
            requiere_visita INTEGER NOT NULL DEFAULT 0,
            categoria TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente'
                CHECK(estado IN ('pendiente','en_evaluacion','aprobado','aprobado_condicional','rechazado','suspendido')),
            cuestionario_url TEXT,
            certificaciones TEXT,
            fecha_aprobacion TEXT,
            fecha_reevaluacion TEXT,
            fecha_ultima_visita TEXT,
            observaciones TEXT,
            evaluado_por TEXT,
            actualizado_en TEXT,
            creado_por TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_provcal_estado ON proveedores_calificacion(estado)",
        # (c) Validación de equipos IQ/OQ/PQ/CSV (reusa equipos_planta)
        """CREATE TABLE IF NOT EXISTS validacion_equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_codigo TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('IQ','OQ','PQ','CSV','revalidacion')),
            protocolo_url TEXT,
            criterios_aceptacion TEXT,
            resultado TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente'
                CHECK(estado IN ('pendiente','en_ejecucion','aprobado','rechazado')),
            fecha_ejecucion TEXT,
            ejecutado_por TEXT,
            aprobado_por TEXT,
            fecha_revalidacion TEXT,
            observaciones TEXT,
            creado_por TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_valeq_equipo ON validacion_equipos(equipo_codigo, tipo)",
        # (d) FMEA / riesgo ICH Q9
        """CREATE TABLE IF NOT EXISTS producto_fmea (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_nombre TEXT NOT NULL,
            modo_falla TEXT NOT NULL,
            efecto TEXT,
            causa TEXT,
            severidad INTEGER,
            ocurrencia INTEGER,
            deteccion INTEGER,
            rpn INTEGER,
            control_actual TEXT,
            accion_recomendada TEXT,
            responsable TEXT,
            estado TEXT NOT NULL DEFAULT 'abierto'
                CHECK(estado IN ('abierto','mitigado','cerrado')),
            creado_por TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_fmea_prod ON producto_fmea(producto_nombre)",
        "CREATE INDEX IF NOT EXISTS idx_fmea_rpn ON producto_fmea(rpn DESC)",
        # (e) Acuerdos de calidad (quality agreements) con maquila/terceros
        """CREATE TABLE IF NOT EXISTS acuerdos_calidad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tercero TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'maquila'
                CHECK(tipo IN ('maquila','proveedor','cliente','laboratorio')),
            documento_url TEXT,
            version TEXT DEFAULT '1',
            fecha_efectiva TEXT,
            fecha_renovacion TEXT,
            alcance TEXT,
            estado TEXT NOT NULL DEFAULT 'vigente'
                CHECK(estado IN ('borrador','vigente','expirado','suspendido')),
            ultima_auditoria TEXT,
            responsable TEXT,
            observaciones TEXT,
            creado_por TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_acuerdos_estado ON acuerdos_calidad(estado, tipo)",
    ]),
    (251, "Siembra el catálogo de documentos que el sistema YA referencia en el SGD "
          "(biblioteca de Documentos · 14-jun). Registra como BORRADOR (pendiente de adjuntar "
          "PDF/versión en Aseguramiento) los 13 procedimientos conocidos (COC-PRO-002/006/008/"
          "011/012/016, COC-EVA-002, ASG-NOR/LMA-001, ASG-PRO-001/004/007/013). Así la "
          "biblioteca deja de estar vacía y sirve de checklist. Idempotente (INSERT OR IGNORE "
          "por código · no pisa los que Miguel ya haya creado).", [
        "INSERT OR IGNORE INTO sgd_documentos (codigo,area,tipo_doc,numero,titulo,estado,observaciones,creado_por) VALUES "
        "('COC-PRO-002','COC','PRO',2,'Rotulado e identificación de materiales en bodega','borrador','Sembrado · adjuntar PDF/versión','seed_mig251')",
        "INSERT OR IGNORE INTO sgd_documentos (codigo,area,tipo_doc,numero,titulo,estado,observaciones,creado_por) VALUES "
        "('COC-PRO-006','COC','PRO',6,'Equipos e instrumentos: calibración y verificación','borrador','Sembrado · adjuntar PDF/versión','seed_mig251')",
        "INSERT OR IGNORE INTO sgd_documentos (codigo,area,tipo_doc,numero,titulo,estado,observaciones,creado_por) VALUES "
        "('COC-PRO-008','COC','PRO',8,'Control del sistema de agua purificada','borrador','Sembrado · adjuntar PDF/versión','seed_mig251')",
        "INSERT OR IGNORE INTO sgd_documentos (codigo,area,tipo_doc,numero,titulo,estado,observaciones,creado_por) VALUES "
        "('COC-PRO-011','COC','PRO',11,'Muestreo microbiológico','borrador','Sembrado · adjuntar PDF/versión','seed_mig251')",
        "INSERT OR IGNORE INTO sgd_documentos (codigo,area,tipo_doc,numero,titulo,estado,observaciones,creado_por) VALUES "
        "('COC-PRO-012','COC','PRO',12,'Vencimiento y cronograma de calibración de equipos','borrador','Sembrado · adjuntar PDF/versión','seed_mig251')",
        "INSERT OR IGNORE INTO sgd_documentos (codigo,area,tipo_doc,numero,titulo,estado,observaciones,creado_por) VALUES "
        "('COC-PRO-016','COC','PRO',16,'Recall / simulacro de retiro de producto','borrador','Sembrado · adjuntar PDF/versión','seed_mig251')",
        "INSERT OR IGNORE INTO sgd_documentos (codigo,area,tipo_doc,numero,titulo,estado,observaciones,creado_por) VALUES "
        "('COC-EVA-002','COC','EVA',2,'Evaluación: examen de envase y empaque','borrador','Sembrado · adjuntar PDF/versión','seed_mig251')",
        "INSERT OR IGNORE INTO sgd_documentos (codigo,area,tipo_doc,numero,titulo,estado,observaciones,creado_por) VALUES "
        "('ASG-NOR-001','ASG','NOR',1,'Norma documental del SGD','borrador','Sembrado · adjuntar PDF/versión','seed_mig251')",
        "INSERT OR IGNORE INTO sgd_documentos (codigo,area,tipo_doc,numero,titulo,estado,observaciones,creado_por) VALUES "
        "('ASG-LMA-001','ASG','LMA',1,'Listado maestro de documentos','borrador','Sembrado · adjuntar PDF/versión','seed_mig251')",
        "INSERT OR IGNORE INTO sgd_documentos (codigo,area,tipo_doc,numero,titulo,estado,observaciones,creado_por) VALUES "
        "('ASG-PRO-001','ASG','PRO',1,'Manejo de desviaciones','borrador','Sembrado · adjuntar PDF/versión','seed_mig251')",
        "INSERT OR IGNORE INTO sgd_documentos (codigo,area,tipo_doc,numero,titulo,estado,observaciones,creado_por) VALUES "
        "('ASG-PRO-004','ASG','PRO',4,'Recall / retiro de producto','borrador','Sembrado · adjuntar PDF/versión','seed_mig251')",
        "INSERT OR IGNORE INTO sgd_documentos (codigo,area,tipo_doc,numero,titulo,estado,observaciones,creado_por) VALUES "
        "('ASG-PRO-007','ASG','PRO',7,'Control de cambios','borrador','Sembrado · adjuntar PDF/versión','seed_mig251')",
        "INSERT OR IGNORE INTO sgd_documentos (codigo,area,tipo_doc,numero,titulo,estado,observaciones,creado_por) VALUES "
        "('ASG-PRO-013','ASG','PRO',13,'Quejas y reclamos de clientes','borrador','Sembrado · adjuntar PDF/versión','seed_mig251')",
    ]),
    (250, "OOS: doble aprobación para disposiciones de rechazo/destrucción (GMP · 14-jun). "
          "Agrega calidad_oos.aprobado_gerencia (2ª firma de gerencia, distinta del Jefe de "
          "Calidad que cierra). Idempotente (duplicate column benigno).", [
        "ALTER TABLE calidad_oos ADD COLUMN aprobado_gerencia TEXT",
    ]),
    (249, "Sección fisicoquímica de Control de Calidad (14-jun): tabla "
          "calidad_fisicoquimica_resultados (análisis FQ del lab: pH, densidad, fósforo, "
          "viscosidad… valor medido vs referencia, sin recuento micro) + siembra el informe FQ "
          "de Microlab (ref 26734-26, Limpiador Facial Hidratante, Fósforo). Idempotente.", [
        """CREATE TABLE IF NOT EXISTS calidad_fisicoquimica_resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lote TEXT,
            producto_nombre TEXT NOT NULL,
            categoria TEXT DEFAULT 'producto',
            n_referencia TEXT,
            fecha_muestreo TEXT,
            fecha_analisis TEXT,
            parametro TEXT NOT NULL,
            metodo TEXT,
            resultado TEXT,
            unidad TEXT,
            valor_referencia TEXT,
            estado TEXT DEFAULT 'informado',
            laboratorio TEXT DEFAULT 'Interno',
            analista TEXT,
            archivo_coa_url TEXT,
            ebr_id INTEGER,
            observaciones TEXT,
            creado_por TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_fq_prod ON calidad_fisicoquimica_resultados(producto_nombre, fecha_analisis DESC)",
        "CREATE INDEX IF NOT EXISTS idx_fq_ref ON calidad_fisicoquimica_resultados(n_referencia)",
        "INSERT INTO calidad_fisicoquimica_resultados "
        "(lote,producto_nombre,categoria,n_referencia,fecha_analisis,parametro,metodo,resultado,unidad,estado,laboratorio,creado_por) "
        "SELECT 'LP260971','LIMPIADOR FACIAL HIDRATANTE','producto','26734-26','2026-04-10',"
        "'Determinación de Fósforo','ASTM D820-93 (2016). Numeral 29','<0.05','g/100g','informado','Microlab Cali','seed_mig249' "
        "WHERE NOT EXISTS (SELECT 1 FROM calidad_fisicoquimica_resultados WHERE n_referencia='26734-26' AND parametro='Determinación de Fósforo')",
    ]),
    (248, "Rellena fecha_analisis/fecha_muestreo de los resultados Microlab que quedaron "
          "vacíos en mig 246 (la extracción del PDF no halló la fecha en 105 informes · se usa "
          "la fecha del correo como fallback). Sin fecha, los paneles de análisis por ventana "
          "temporal perdían el 64% de los datos. Idempotente (solo filas con fecha vacía).",
        _MIG_248_STMTS),
    (247, "Limpia nombres de producto en calidad_micro_resultados (audit nombres workflow · "
          "14-jun): arregla mojibake de la extracción del PDF (FABRICACIÓN/PRODUCCIÓN), quita el "
          "sufijo/prefijo '(PRODUCTO TERMINADO)' y alinea variantes al nombre canónico de "
          "formula_headers (trazabilidad QC↔producción). Corrige 2 categorías mal puestas "
          "(Agua Micelar=producto, Ceramide NP=materia_prima). Idempotente (WHERE LIKE).", [
        # mojibake (U+FFFD) que dejó la extracción del PDF en nombres con acento
        "UPDATE calidad_micro_resultados SET producto_nombre = REPLACE(producto_nombre, 'FABRICACI�N', 'FABRICACIÓN') WHERE producto_nombre LIKE '%FABRICACI�N%'",
        "UPDATE calidad_micro_resultados SET producto_nombre = REPLACE(producto_nombre, 'PRODUCCI�N', 'PRODUCCIÓN') WHERE producto_nombre LIKE '%PRODUCCI�N%'",
        # sufijo/prefijo '(PRODUCTO TERMINADO)' (orden: más específico primero)
        "UPDATE calidad_micro_resultados SET producto_nombre = TRIM(REPLACE(producto_nombre, ' - (PRODUCTO TERMINADO)', '')) WHERE producto_nombre LIKE '% - (PRODUCTO TERMINADO)%'",
        "UPDATE calidad_micro_resultados SET producto_nombre = TRIM(REPLACE(producto_nombre, ' (PRODUCTO TERMINADO)', '')) WHERE producto_nombre LIKE '% (PRODUCTO TERMINADO)%'",
        "UPDATE calidad_micro_resultados SET producto_nombre = TRIM(REPLACE(producto_nombre, '(PRODUCTO TERMINADO)', '')) WHERE producto_nombre LIKE '%(PRODUCTO TERMINADO)%'",
        "UPDATE calidad_micro_resultados SET producto_nombre = TRIM(REPLACE(producto_nombre, 'PRODUCTO TERMINADO ', '')) WHERE producto_nombre LIKE 'PRODUCTO TERMINADO %'",
        # alineaciones canónicas (verificadas por el agente vs formula_headers)
        "UPDATE calidad_micro_resultados SET producto_nombre = 'CREMA DE UREA' WHERE producto_nombre = 'CREMA CORPORAL DE UREA'",
        "UPDATE calidad_micro_resultados SET producto_nombre = 'LIMPIADOR ILUMINADOR ACIDO KOJICO' WHERE producto_nombre = 'LIMPIADOR ILUMINADOR DE ACIDO KOJICO'",
        # 'PRODUCTO TERMINADO' embebido en el medio (no como sufijo entre paréntesis)
        "UPDATE calidad_micro_resultados SET producto_nombre = 'SUERO MULTIPEPTIDOS' WHERE producto_nombre LIKE 'SUERO MULTIPEPTIDOS - PRODUCTO TERMINADO%'",
        # categorías mal puestas por el heurístico del seed
        "UPDATE calidad_micro_resultados SET categoria = 'producto' WHERE producto_nombre LIKE '%AGUA MICELAR%' AND COALESCE(categoria,'')='ambiente'",
        "UPDATE calidad_micro_resultados SET categoria = 'materia_prima' WHERE producto_nombre IN ('CERAMIDE NP') AND COALESCE(categoria,'')<>'materia_prima'",
        # agua de servicio (desionizada/potable/filtrada/manguera) = monitoreo ambiental, NO producto
        "UPDATE calidad_micro_resultados SET categoria = 'ambiente' WHERE producto_nombre LIKE 'AGUA %' AND producto_nombre NOT LIKE '%MICELAR%' AND COALESCE(categoria,'')='producto'",
    ]),
    (246, "Carga histórica de resultados micro de Microlab Cali (lab externo · 14-jun). "
          "Agrega categoria (producto/materia_prima/ambiente) + n_referencia (N° informe del "
          "lab, p.ej. 27861-26) a calidad_micro_resultados; luego siembra 458 resultados de "
          "32 informes (.eml→PDF parseados localmente · 2025-05 a 2026-05) con el veredicto del "
          "lab (C→ok, N.C→fuera_industria). El ambiente se etiqueta aparte para no ensuciar el "
          "heatmap de producto. Idempotente (cada INSERT con NOT EXISTS por n_referencia+micro+lab).",
        [
            "ALTER TABLE calidad_micro_resultados ADD COLUMN categoria TEXT",
            "ALTER TABLE calidad_micro_resultados ADD COLUMN n_referencia TEXT",
            "CREATE INDEX IF NOT EXISTS idx_micro_res_ref ON calidad_micro_resultados(n_referencia)",
            "CREATE INDEX IF NOT EXISTS idx_micro_res_cat ON calidad_micro_resultados(categoria)",
        ] + _MIG_246_STMTS),
    (245, "Micro brutal (Fase 2 · 14-jun): liga los análisis micro al lote de PT/EBR y "
          "permite adjuntar el COA/informe del laboratorio. Agrega a "
          "calidad_micro_resultados: archivo_coa_url (URL del informe del lab) y ebr_id "
          "(FK suave a ebr_ejecuciones para trazar el resultado al legajo del lote). "
          "Idempotente (duplicate column = benigno).", [
        "ALTER TABLE calidad_micro_resultados ADD COLUMN archivo_coa_url TEXT",
        "ALTER TABLE calidad_micro_resultados ADD COLUMN ebr_id INTEGER",
        "CREATE INDEX IF NOT EXISTS idx_micro_res_ebr ON calidad_micro_resultados(ebr_id)",
    ]),
    (244, "Cuadro de mando de indicadores de calidad (Fase 1 · 14-jun). Tabla "
          "calidad_kpi_metas: cada indicador tiene meta/objetivo + umbral_amarillo + "
          "direccion (mayor_mejor/menor_mejor) para semaforo verde/amarillo/rojo. Seed con "
          "el set estandar de una planta cosmetica regulada INVIMA (RFT, tasa rechazo, NCs, "
          "tiempo cierre NC, CAPA vencidas/a-tiempo, OOS, calibraciones, agua, micro, "
          "liberacion PT). La jefa de calidad puede editar las metas. Idempotente.", [
        """CREATE TABLE IF NOT EXISTS calidad_kpi_metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo           TEXT UNIQUE NOT NULL,
            nombre           TEXT NOT NULL,
            descripcion      TEXT DEFAULT '',
            unidad           TEXT DEFAULT '%',
            direccion        TEXT NOT NULL DEFAULT 'mayor_mejor'
                CHECK(direccion IN ('mayor_mejor','menor_mejor')),
            meta             REAL,
            umbral_amarillo  REAL,
            categoria        TEXT DEFAULT 'General',
            orden            INTEGER DEFAULT 100,
            activo           INTEGER DEFAULT 1,
            actualizado_por  TEXT DEFAULT '',
            actualizado_at   TEXT DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_calidad_kpi_codigo ON calidad_kpi_metas(codigo)",
        # Seed · meta = objetivo (verde si lo cumple), umbral_amarillo = frontera ámbar→rojo
        "INSERT OR IGNORE INTO calidad_kpi_metas (codigo,nombre,descripcion,unidad,direccion,meta,umbral_amarillo,categoria,orden) VALUES "
        "('rft_mp','Right-First-Time lotes MP','% de lotes de MP aprobados sin rechazo (mes)','%','mayor_mejor',95,90,'Liberación',10)",
        "INSERT OR IGNORE INTO calidad_kpi_metas (codigo,nombre,descripcion,unidad,direccion,meta,umbral_amarillo,categoria,orden) VALUES "
        "('tasa_rechazo_mp','Tasa de rechazo lotes MP','% de lotes de MP rechazados (mes)','%','menor_mejor',5,10,'Liberación',20)",
        "INSERT OR IGNORE INTO calidad_kpi_metas (codigo,nombre,descripcion,unidad,direccion,meta,umbral_amarillo,categoria,orden) VALUES "
        "('liberacion_pt','Tasa de liberación PT','% de PT liberados vs total decidido (mes)','%','mayor_mejor',95,85,'Liberación',30)",
        "INSERT OR IGNORE INTO calidad_kpi_metas (codigo,nombre,descripcion,unidad,direccion,meta,umbral_amarillo,categoria,orden) VALUES "
        "('nc_abiertas','No Conformidades abiertas','NC sin cerrar a la fecha','NC','menor_mejor',0,3,'Desviaciones',40)",
        "INSERT OR IGNORE INTO calidad_kpi_metas (codigo,nombre,descripcion,unidad,direccion,meta,umbral_amarillo,categoria,orden) VALUES "
        "('nc_cierre_dias','Tiempo promedio cierre NC','Días promedio entre apertura y cierre de NC (90d)','días','menor_mejor',15,30,'Desviaciones',50)",
        "INSERT OR IGNORE INTO calidad_kpi_metas (codigo,nombre,descripcion,unidad,direccion,meta,umbral_amarillo,categoria,orden) VALUES "
        "('capa_vencidas','CAPA vencidas','Acciones CAPA con fecha de compromiso vencida y sin cerrar','CAPA','menor_mejor',0,2,'Desviaciones',60)",
        "INSERT OR IGNORE INTO calidad_kpi_metas (codigo,nombre,descripcion,unidad,direccion,meta,umbral_amarillo,categoria,orden) VALUES "
        "('capa_a_tiempo','% CAPA cerradas a tiempo','% de CAPA cerradas dentro de la fecha de compromiso','%','mayor_mejor',90,75,'Desviaciones',70)",
        "INSERT OR IGNORE INTO calidad_kpi_metas (codigo,nombre,descripcion,unidad,direccion,meta,umbral_amarillo,categoria,orden) VALUES "
        "('oos_abiertos','OOS abiertos','Resultados fuera de especificación sin cerrar','OOS','menor_mejor',0,2,'Análisis',80)",
        "INSERT OR IGNORE INTO calidad_kpi_metas (codigo,nombre,descripcion,unidad,direccion,meta,umbral_amarillo,categoria,orden) VALUES "
        "('micro_ok','Tasa OK microbiología','% de resultados micro dentro de spec de industria (mes)','%','mayor_mejor',98,90,'Análisis',90)",
        "INSERT OR IGNORE INTO calidad_kpi_metas (codigo,nombre,descripcion,unidad,direccion,meta,umbral_amarillo,categoria,orden) VALUES "
        "('agua_conforme','Cumplimiento sistema de agua','% de registros de agua conformes (mes · COC-PRO-008)','%','mayor_mejor',100,95,'Análisis',100)",
        "INSERT OR IGNORE INTO calidad_kpi_metas (codigo,nombre,descripcion,unidad,direccion,meta,umbral_amarillo,categoria,orden) VALUES "
        "('calibraciones_vigentes','Cumplimiento calibraciones','% de equipos con calibración vigente','%','mayor_mejor',100,90,'Equipos',110)",
    ]),
    (243, "Alinea INCI al MAESTRO de Alejandro (FORMULAS_MAESTRO_v2_1 · unica verdad · "
          "13-jun). Verificado: de 153 INCI del maestro, 148 YA coincidian con la app; solo "
          "4 ajustes. (1) Llena los 2 vacios con el INCI del maestro: MP00040 Cetiol=DICAPRYLYL "
          "CARBONATE (es Cetiol CC), MP00103 Beauty Oil Ceramidas=CERAMIDE NP. (2) Corrige "
          "MP00101 Vainilla: el maestro dice FRUIT OIL (no EXTRACT). (3) Alinea formato del "
          "blend MP00207 al maestro. NO toca MP00079 (la app ya tiene TOCOPHERYL ACETATE "
          "confirmado por Sebastian · el maestro aun tiene el marcador 'pendiente', la app esta "
          "mas al dia). La COMPOSICION de las formulas ya coincide con el maestro (sin extras "
          "que borrar; MP00123 esta en 0% en el Excel = correctamente ausente; Lip Serum PIB-24 "
          "q.s.p. es caso aparte). Idempotente.", [
        "UPDATE maestro_mps SET nombre_inci='DICAPRYLYL CARBONATE' WHERE codigo_mp='MP00040'",
        "UPDATE maestro_mps SET nombre_inci='CERAMIDE NP' WHERE codigo_mp='MP00103'",
        "UPDATE maestro_mps SET nombre_inci='VANILLA PLANIFOLIA FRUIT OIL' WHERE codigo_mp='MP00101'",
        "UPDATE maestro_mps SET nombre_inci='PHENETHYL ALCOHOL (AND) CAPRYLYL GLYCOL' WHERE codigo_mp='MP00207'",
    ]),
    (242, "Backfill INCI confirmados POR SEBASTIAN/ALEJANDRO (13-jun · datos del dueno, no "
          "adivinados): Vit E liquida=TOCOPHEROL, Vit E polvo=TOCOPHERYL ACETATE (resuelve el "
          "'pendiente'), Tinogard TT, BM-956, Stabil (blend), PMSS, Microcristalina, Neroli, "
          "Ceresine, Murumuru, Vainilla. Quedan PENDIENTES (variante exacta a definir): MP00040 "
          "Cetiol (CC/AB/HE) y MP00103 Beauty Oil Ceramidas. Idempotente (UPDATE por codigo).", [
        "UPDATE maestro_mps SET nombre_inci='TOCOPHEROL' WHERE codigo_mp='MP00078'",
        "UPDATE maestro_mps SET nombre_inci='TOCOPHERYL ACETATE' WHERE codigo_mp='MP00079'",
        "UPDATE maestro_mps SET nombre_inci='PENTAERYTHRITYL TETRA-DI-T-BUTYL HYDROXYHYDROCINNAMATE' WHERE codigo_mp='MP00063'",
        "UPDATE maestro_mps SET nombre_inci='PHENYL TRIMETHICONE' WHERE codigo_mp='MP00127'",
        "UPDATE maestro_mps SET nombre_inci='PHENETHYL ALCOHOL, CAPRYLYL GLYCOL' WHERE codigo_mp='MP00207'",
        "UPDATE maestro_mps SET nombre_inci='POLYMETHYLSILSESQUIOXANE' WHERE codigo_mp='MP00055'",
        "UPDATE maestro_mps SET nombre_inci='MICROCRYSTALLINE WAX' WHERE codigo_mp='MP00024'",
        "UPDATE maestro_mps SET nombre_inci='CITRUS AURANTIUM AMARA FLOWER OIL' WHERE codigo_mp='MP00025'",
        "UPDATE maestro_mps SET nombre_inci='CERESIN' WHERE codigo_mp='MP00041'",
        "UPDATE maestro_mps SET nombre_inci='ASTROCARYUM MURUMURU SEED BUTTER' WHERE codigo_mp='MP00077'",
        "UPDATE maestro_mps SET nombre_inci='VANILLA PLANIFOLIA FRUIT EXTRACT' WHERE codigo_mp='MP00101'",
    ]),
    (241, "Backfill INCI SOLO de los MPs cuyo nombre comercial ES el nombre INCI estandar "
          "verbatim (audit formulas 13-jun · NO es adivinar, es copiar el INCI = comercial). "
          "Los nombres de marca/ambiguos (Cetiol, Tinogard, Stabil, Vit E polvo vs liquida, "
          "aceites esenciales, BM-956, etc.) NO se tocan: requieren la ficha tecnica de Alejandro "
          "(riesgo de etiquetado INVIMA · M17/M19). Idempotente: solo rellena si esta vacio (no "
          "pisa un INCI ya corregido). INCI en MAYUSCULAS = convencion del maestro.", [
        "UPDATE maestro_mps SET nombre_inci='PALMITOYL TETRAPEPTIDE-7' WHERE codigo_mp='MP00172' AND COALESCE(nombre_inci,'')=''",
        "UPDATE maestro_mps SET nombre_inci='PALMITOYL TRIPEPTIDE-38' WHERE codigo_mp='MP00174' AND COALESCE(nombre_inci,'')=''",
        "UPDATE maestro_mps SET nombre_inci='PALMITOYL TRIPEPTIDE-1' WHERE codigo_mp='MP00190' AND COALESCE(nombre_inci,'')=''",
        "UPDATE maestro_mps SET nombre_inci='POLYGLYCERYL-2 TRIISOSTEARATE' WHERE codigo_mp='MP00051' AND COALESCE(nombre_inci,'')=''",
        "UPDATE maestro_mps SET nombre_inci='LAUROYL LYSINE' WHERE codigo_mp='MP00054' AND COALESCE(nombre_inci,'')=''",
        "UPDATE maestro_mps SET nombre_inci='SYNTHETIC WAX' WHERE codigo_mp='MP00257' AND COALESCE(nombre_inci,'')=''",
        "UPDATE maestro_mps SET nombre_inci='BORON NITRIDE' WHERE codigo_mp='MPBNIT01' AND COALESCE(nombre_inci,'')=''",
        "UPDATE maestro_mps SET nombre_inci='COCO-CAPRYLATE' WHERE codigo_mp='MPCOCP01' AND COALESCE(nombre_inci,'')=''",
    ]),
    (240, "Homologa el nombre de MP00297 (NaOH) en formula_items (audit formulas 13-jun · "
          "Sebastian confirmo: fisicamente es UNA sola solucion al 50% · las 3 formulas activas "
          "que lo usan dosifican de ella · el % de cada una ya lo contempla). Antes el mismo "
          "codigo aparecia con 3 etiquetas distintas ('Hidroxido sodio', 'Soda caustica 10%', "
          "'Hidroxido sodio sol. 50%') = confusion visual, NO error de dosificacion (el descuento "
          "resuelve por codigo). Cosmetico: alinea material_nombre al comercial del maestro. "
          "Idempotente.", [
        "UPDATE formula_items SET material_nombre = "
        "COALESCE((SELECT nombre_comercial FROM maestro_mps WHERE codigo_mp='MP00297'), material_nombre) "
        "WHERE material_id='MP00297'",
    ]),
    (239, "P0 INVIMA · normalizar movimientos.estado_lote a MAYUSCULAS canonicas "
          "(Sebastian 12-jun · hallazgo Fable). Calidad escribia 'Aprobado'/'Rechazado' "
          "(Title-case) en aprobar-lote, pero el FEFO del descuento filtra "
          "NOT IN ('...','RECHAZADO') case-sensitive -> un lote RECHAZADO se colaba a "
          "produccion ('Rechazado' != 'RECHAZADO'). Esta mig pasa todo a UPPER y mapea "
          "APROBADO->VIGENTE para que los ~10 filtros NOT IN (mayusculas) coincidan. "
          "Idempotente · reversible (solo normaliza case). NO toca cantidades/lotes.", [
        "UPDATE movimientos SET estado_lote=UPPER(estado_lote) "
        "WHERE estado_lote IS NOT NULL AND estado_lote <> '' AND estado_lote <> UPPER(estado_lote)",
        "UPDATE movimientos SET estado_lote='VIGENTE' WHERE estado_lote='APROBADO'",
    ]),

    (238, "Blush Balm · mapear los 8 tonos (SKU Shopify) al producto 'Blush Balm' (Sebastian "
          "12-jun). Los tonos son variantes Shopify (BB101..BB801) que comparten el mismo "
          "bulk base -> sus ventas deben SUMAR a 'Blush Balm' para que aparezca en "
          "necesidades y se solicite la produccion del bulk. Antes no estaban mapeados -> "
          "Blush Balm no salia en necesidades (Malva BB201=-29 y Borgona BB801=-7 estan "
          "sobrevendidos). El desglose POR TONO (ventas/unidades/pigmento) se maneja aparte "
          "(capa de tonos · pendiente pigmentos). Idempotente · reversible (activo=0).", [
        # Tonos: BB101 Hot Pink · BB201 Malva · BB301 Peach · BB401 Carolina ·
        #        BB501 Himalayan Pink · BB601 Cinnamon · BB701 Moca · BB801 Borgona
        "INSERT OR IGNORE INTO sku_producto_map (sku, producto_nombre, activo) VALUES "
        "('BB101','Blush Balm',1),('BB201','Blush Balm',1),('BB301','Blush Balm',1),"
        "('BB401','Blush Balm',1),('BB501','Blush Balm',1),('BB601','Blush Balm',1),"
        "('BB701','Blush Balm',1),('BB801','Blush Balm',1)",
        "UPDATE sku_producto_map SET producto_nombre='Blush Balm', activo=1 "
        "WHERE UPPER(sku) IN ('BB101','BB201','BB301','BB401','BB501','BB601','BB701','BB801')",
    ]),

    (237, "Reconciliacion formulas vs maestro Alejandro (Sebastian 12-jun · AUTORIZADO) · "
          "cruce FORMULAS_MAESTRO_v2_1 + INVENTARIO_MP_v8_2 uno-a-uno. Arregla 3 mapeos "
          "MAL que rompian descuento/necesidades; deja Centella(#3) y Vit E(#4) para "
          "decision de grado de Alejandro. DETALLE: "
          "#1 Propylheptyl Caprylate / Beauty Sensoft estaban apuntados a MP00137, que "
          "ES Argania Spinosa (ARGAN, otro material) -> por eso MP00137 quedo en -724g. "
          "Re-apunta SOLO esos items a MP00030 (PROPYLHEPTYL CAPRYLATE). NO toca el stock "
          "fisico de Argan/Sensoft (requiere conteo fisico de bodega). "
          "#2 'Beauty oil Kakai' usaba MP00444 (codigo fuera del inventario) -> unifica a "
          "MPCAKY01 (CACAY OIL): mueve los ~530g y re-apunta formulas. El Excel decia "
          "MP00103 pero eso es CERAMIDE NP (error del Excel) -> NO se sigue. "
          "#3 agrega Myristoyl Nonapeptide-3 (MP00250) que faltaba en Suero Exfoliante "
          "BHA (0.0015%) y Booster Tensor (0.003%). Idempotente + reversible (movimientos "
          "marcados con [unif ... mig237]; nada se borra, MP00444 queda activo=0).", [
        # ── Paso 0: los codigos destino deben existir ACTIVOS con su INCI correcto.
        #    El trigger FK de mig 98 aborta si material_id no esta en maestro activo.
        "INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
        "VALUES ('MP00030','PROPYLHEPTYL CAPRYLATE','Beauty Sensoft',1)",
        "INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
        "VALUES ('MPCAKY01','CACAY OIL','Aceite de cacay',1)",
        "INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
        "VALUES ('MP00250','MYRISTOYL NONAPEPTIDE-3','Myristoyl nonapeptide-3',1)",
        "UPDATE maestro_mps SET activo=1 WHERE codigo_mp IN ('MP00030','MPCAKY01','MP00250')",
        # rellenar INCI solo si estaba vacio o PENDIENTE (no pisar uno bueno distinto)
        "UPDATE maestro_mps SET nombre_inci='PROPYLHEPTYL CAPRYLATE' WHERE codigo_mp='MP00030' "
        "AND (nombre_inci IS NULL OR TRIM(nombre_inci)='' OR UPPER(nombre_inci)='PENDIENTE INCI')",
        "UPDATE maestro_mps SET nombre_inci='CACAY OIL' WHERE codigo_mp='MPCAKY01' "
        "AND (nombre_inci IS NULL OR TRIM(nombre_inci)='' OR UPPER(nombre_inci)='PENDIENTE INCI')",
        "UPDATE maestro_mps SET nombre_inci='MYRISTOYL NONAPEPTIDE-3' WHERE codigo_mp='MP00250' "
        "AND (nombre_inci IS NULL OR TRIM(nombre_inci)='' OR UPPER(nombre_inci)='PENDIENTE INCI')",

        # ── #1: re-apuntar SOLO los items Sensoft/Propylheptyl de MP00137 -> MP00030.
        #    Scope por material_nombre: un uso legitimo de MP00137 como Argan
        #    (material_nombre LIKE Argan) queda INTACTO.
        "UPDATE formula_items SET material_id='MP00030' "
        "WHERE material_id='MP00137' AND ("
        "UPPER(material_nombre) LIKE '%SENSOFT%' "
        "OR UPPER(material_nombre) LIKE '%PROPYLHEPTYL%' "
        "OR UPPER(material_nombre) LIKE '%PROPYL HEPTYL%')",

        # ── #2: unificar Kakai MP00444 -> MPCAKY01 (mismo aceite Cacay/Kakai).
        #    a) re-apunta formulas
        "UPDATE formula_items SET material_id='MPCAKY01' WHERE material_id='MP00444'",
        #    b) mueve el stock (re-key movimientos · preserva lote/fecha · marca origen)
        "UPDATE movimientos SET material_id='MPCAKY01', "
        "observaciones=COALESCE(observaciones,'')||' [unif MP00444->MPCAKY01 mig237]' "
        "WHERE material_id='MP00444'",
        #    c) archiva el codigo sucio (NO se borra · trazabilidad INVIMA)
        "UPDATE maestro_mps SET activo=0 WHERE codigo_mp='MP00444'",

        # ── #3: agregar Myristoyl Nonapeptide-3 (MP00250) que faltaba en 2 formulas.
        #    Usa el producto_nombre REAL guardado (match normalizado) e idempotente.
        "INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) "
        "SELECT DISTINCT fi.producto_nombre, 'MP00250', 'Myristoyl nonapeptide-3', 0.0015 "
        "FROM formula_items fi "
        "WHERE REPLACE(REPLACE(UPPER(fi.producto_nombre),' ',''),'%','') LIKE '%SUEROEXFOLIANTEBHA%' "
        "AND NOT EXISTS (SELECT 1 FROM formula_items x "
        "WHERE x.producto_nombre=fi.producto_nombre AND x.material_id='MP00250')",
        "INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) "
        "SELECT DISTINCT fi.producto_nombre, 'MP00250', 'Myristoyl nonapeptide-3', 0.003 "
        "FROM formula_items fi "
        "WHERE REPLACE(UPPER(fi.producto_nombre),' ','') LIKE '%BOOSTERTENSOR%' "
        "AND NOT EXISTS (SELECT 1 FROM formula_items x "
        "WHERE x.producto_nombre=fi.producto_nombre AND x.material_id='MP00250')",
    ]),

    (236, "EBR · presentaciones MANUALES del legajo (Sebastián 11-jun): permite agregar/"
          "editar/borrar a mano una presentación (por si no cargó del plan), además de las "
          "auto-cargadas. Tabla aparte · no toca el envasado real ni la inmutabilidad.", [
        "CREATE TABLE IF NOT EXISTS ebr_presentaciones_manual ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " ebr_id INTEGER NOT NULL,"
        " presentacion TEXT DEFAULT '',"
        " cliente TEXT DEFAULT '',"
        " volumen_ml REAL,"
        " envase_codigo TEXT DEFAULT '',"
        " unidades REAL,"
        " area TEXT DEFAULT '',"
        " lote TEXT DEFAULT '',"
        " creado_por TEXT DEFAULT '',"
        " creado_at TEXT DEFAULT (datetime('now','-5 hours')))",
        "CREATE INDEX IF NOT EXISTS idx_ebr_pres_man ON ebr_presentaciones_manual(ebr_id)",
    ]),

    (235, "EBR · materiales de envase MANUALES del legajo (Sebastián 11-jun): permite "
          "elegir/agregar/editar a mano un material de envase desde el desplegable de TODOS "
          "los envases (maestro_mee), además del auto-cargado del plan. Tabla aparte · no "
          "toca el envasado real ni la inmutabilidad del EBR liberado.", [
        "CREATE TABLE IF NOT EXISTS ebr_envase_materiales ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " ebr_id INTEGER NOT NULL,"
        " lote_envasado TEXT DEFAULT '',"
        " material_codigo TEXT NOT NULL,"
        " material_nombre TEXT DEFAULT '',"
        " lote_material TEXT DEFAULT '',"
        " requerida REAL DEFAULT 0,"
        " devuelta REAL,"
        " utilizada REAL,"
        " averiada REAL,"
        " creado_por TEXT DEFAULT '',"
        " creado_at TEXT DEFAULT (datetime('now','-5 hours')))",
        "CREATE INDEX IF NOT EXISTS idx_ebr_env_mat ON ebr_envase_materiales(ebr_id)",
    ]),

    (234, "envasado · area_codigo (semi-auto envasado en el flujo REAL · 9-jun): la cola "
          "'Envasar' usa /api/envasado (tabla envasado), no el /iniciar huérfano. Agrega "
          "area_codigo para registrar el área asignada (con gate de limpieza). operador ya "
          "existía.", [
        "ALTER TABLE envasado ADD COLUMN area_codigo TEXT DEFAULT ''",
    ]),

    (233, "Corrige INCI equivocado en bridges (audit corazón 9-jun): (1) BETAÍNA MPBETASO01 → "
          "MP00215 (Betaína/BETAINE) · apuntaba MAL a MP00214 (Betaglucano/BETA-GLUCAN, molécula "
          "distinta) → consumo de betaína se imputaba al betaglucano. Afecta MAXLASH (activo · "
          "Betaína 0.3% confirmada en el docx). MP00215 existe. (2) Desactiva el bridge "
          "MPACFESO01 (Ác. Ferúlico) → MP00160 (Etil ascórbico, MAL): su único uso está "
          "descontinuado; desactivar evita que consuma la MP equivocada si se reactiva (que "
          "muera y avise > mis-map silencioso). Idempotente.", [
        "UPDATE mp_formula_bridge SET bodega_material_id='MP00215' "
        "WHERE formula_material_id='MPBETASO01'",
        "UPDATE mp_formula_bridge SET activo=0 "
        "WHERE formula_material_id='MPACFESO01' AND bodega_material_id='MP00160'",
    ]),

    (232, "MAXLASH · crea las 8 MPs que faltaban en maestro_mps (Sebastián subió la fórmula "
          "MaxLash · audit corazón 9-jun). La fórmula del MAXLASH en la app ya era correcta "
          "(% = docx) pero 8 ingredientes MORÍAN porque su código canónico (destino del bridge) "
          "no existía en maestro. Se crean con el código del bridge (verificado) + INCI del docx "
          "MaxLash (no inventado). Tras esto MAXLASH cruza 100%. Idempotente (codigo_mp es PK).", [
        "INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) VALUES "
        "('MP00151', 'Prolina', 'PROLINE', 1), "
        "('MP00164', 'N-Acetil-cisteína', 'ACETYL CYSTEINE', 1), "
        "('MP00168', 'Péptidos hidrolizados de queratina', 'HYDROLYZED KERATIN', 1), "
        "('MP00170', 'Acetil tetrapéptido-3', 'ACETYL TETRAPEPTIDE-3', 1), "
        "('MP00171', 'Miristoil hexapéptido-16', 'MYRISTOYL HEXAPEPTIDE-16', 1), "
        "('MP00187', 'Miristoil pentapéptido-17', 'MYRISTOYL PENTAPEPTIDE-17', 1), "
        "('MP00193', 'Biotinoil tripéptido-1', 'BIOTINOYL TRIPEPTIDE-1', 1), "
        "('MP00241', 'Extracto de trébol rojo', 'TRIFOLIUM PRATENSE (RED CLOVER) FLOWER EXTRACT', 1)",
    ]),

    (231, "DESCONTINÚA 6 fórmulas que ya no se venden (decisión Sebastián 9-jun · audit corazón · "
          "productos propios que no estaban en el Excel maestro; MAXLASH se CONSERVA porque "
          "Sebastián lo subirá al Excel): CREMA DE UREA, EMULSION HIDRATANTE ANTIOXIDANTE, ESENCIA "
          "ILUMINADORA, SUERO ANTIOXIDANTE VITAMINA C+B3, SUERO DE RETINALDEHIDO 0.05%, SUERO "
          "ILUMINADOR AHA+AH. activo=0 (GMP · reversible · conserva registros). Sin producciones "
          "programadas (0 refs · verificado). Idempotente.", [
        "UPDATE formula_headers SET activo=0 WHERE producto_nombre IN "
        "('CREMA DE UREA', 'EMULSION HIDRATANTE ANTIOXIDANTE', 'ESENCIA ILUMINADORA', "
        "'SUERO ANTIOXIDANTE VITAMINA C+B3', 'SUERO DE RETINALDEHIDO 0.05%', "
        "'SUERO ILUMINADOR AHA+AH.')",
    ]),

    (230, "Dedup BLUSH BALM (audit corazón 9-jun): existían 2 fórmulas del mismo SKU — 'Blush "
          "Balm' (INCOMPLETA, 67%, lote 0, sin producciones) y 'BLUSH BALM' (COMPLETA 100%, "
          "idéntica al Excel maestro con MP00127/MPCOCP01/MPBNIT01, en producción). Descontinúa "
          "la incompleta (activo=0 · reversible · GMP); queda la completa = Excel. Idempotente.", [
        "UPDATE formula_headers SET activo=0 WHERE producto_nombre='Blush Balm' "
        "AND COALESCE(lote_size_kg,0)=0",
    ]),

    (229, "DESCONTINÚA 3 fórmulas (decisión Sebastián 9-jun · audit corazón): 'SUERO AZ + B3' "
          "y 'Suero RETINAL +' ya no se venden; 'SUERO TRIACTIVE RETINOID NAD+' (49 ítems, "
          "reformulado/legacy) es duplicado del SKU — queda 'SUERO TRIACTIVE RETINOID NAD' (40 "
          "ítems = idéntico al Excel maestro). GMP/INVIMA: NO se borran registros · activo=0 los "
          "oculta de producción/planeación/venta/cruce y es REVERSIBLE. Sin producciones "
          "programadas (0 refs · verificado). Idempotente.", [
        "UPDATE formula_headers SET activo=0 WHERE producto_nombre IN "
        "('SUERO TRIACTIVE RETINOID NAD+', 'Suero RETINAL +', 'SUERO AZ + B3')",
    ]),

    (228, "Corrige bridge MPALANSO01 (Alantoína) → MP00047 · audit corazón 9-jun: el "
          "destino MP00085 NO existe en maestro_mps (bridge roto fantasma→fantasma) y la "
          "Alantoína real es MP00047 (match EXACTO por nombre · único activo). Los otros 23 "
          "bridges rotos + RESVERATROL + 2 de INCI necesitan el Excel maestro · NO se "
          "adivinan (matching difuso corrompe el kardex · regla cero-error). Idempotente.", [
        "UPDATE mp_formula_bridge SET bodega_material_id='MP00047' "
        "WHERE formula_material_id='MPALANSO01' AND bodega_material_id='MP00085'",
    ]),

    (227, "produccion_envasado · operario_asignado + area_codigo (semi-auto envasado: "
          "el jefe de producción asigna operario + área LIMPIA al dar el clock de "
          "iniciar · Sebastián 8-jun-2026)", [
        "ALTER TABLE produccion_envasado ADD COLUMN operario_asignado TEXT DEFAULT ''",
        "ALTER TABLE produccion_envasado ADD COLUMN area_codigo TEXT DEFAULT ''",
    ]),

    (226, "portal_solicitudes.cliente_id INTEGER→TEXT · bug VIVO en PG: el portal B2B "
          "guarda códigos de cliente TEXT (portal_clientes_credenciales.cliente_id es "
          "TEXT) pero esta columna era INTEGER → crear solicitud (RFQ/cotización) daba "
          "HTTP 500 en producción (SQLite lo toleraba por tipado dinámico). Cazado por la "
          "suite golden en modo PostgreSQL · 8-jun-2026. Solo aplica en PG (en SQLite el "
          "tipo es irrelevante y el CREATE TABLE base ya quedó TEXT).", (
        ["ALTER TABLE portal_solicitudes ALTER COLUMN cliente_id TYPE TEXT "
         "USING cliente_id::text"]
        if _usa_postgres() else []
    )),

    (225, "ipc_estandar_resultados · controles en proceso ESTÁNDAR siempre presentes (Densidad/pH/Olor/Color/Apariencia) con opción 'No aplica' (conforme=2) · 6-jun-2026", [
        # Sebastián: la sección 6 (Controles en Proceso) debe mostrar SIEMPRE un set
        # estándar aunque el MBR del producto no lo defina, y cada control se puede
        # registrar con valor o marcar 'No aplica'. Como ipc_resultados.ipc_spec_id es
        # NOT NULL + FK a ipc_specs (y triggers impiden agregar specs a MBR aprobados),
        # los estándar viven en tabla propia, identificados por control_codigo.
        # conforme: 1=Cumple · 0=No cumple · 2=No aplica · NULL=pendiente.
        """CREATE TABLE IF NOT EXISTS ipc_estandar_resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ebr_id INTEGER NOT NULL,
            control_codigo TEXT NOT NULL,
            control_nombre TEXT NOT NULL,
            valor_texto TEXT DEFAULT '',
            conforme INTEGER DEFAULT NULL,
            observaciones TEXT DEFAULT '',
            medido_por TEXT DEFAULT '',
            medido_at_utc TEXT DEFAULT '',
            FOREIGN KEY (ebr_id) REFERENCES ebr_ejecuciones(id) ON DELETE CASCADE,
            UNIQUE(ebr_id, control_codigo)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ipcest_ebr ON ipc_estandar_resultados(ebr_id)",
    ]),

    (224, "areas_planta · consolidar a las 7 áreas oficiales (Sebastián 6-jun-2026) · elimina duplicados FAB*/PROD* · renombra · DISP/ACOND visibles no-fabricables", [
        # AS-IS: convivían PROD1/2/3 (legacy, con historial produccion_programada.area_id)
        # y FAB1/2/3 (nuevas, solo para equipos) → el mapa mostraba "Fabricación 1/2/3"
        # DUPLICADO. Las 7 oficiales según Sebastián:
        #   Fabricación 1 · Fabricación y Envasado 2 · Fabricación y Envasado 3 ·
        #   Envasado 1 · Envasado 2 · Dispensación · Acondicionamiento.
        # Mantenemos los códigos PROD*/ENV*/DISP/ACOND (cargan el historial), y
        # DESACTIVAMOS los duplicados FAB1/FAB2/FAB3 + FAB_FLOAT. Los equipos siguen
        # OK por el puente PROD→FAB del rótulo (_SALA_EQUIPO_ALIAS).
        "UPDATE areas_planta SET nombre='Fabricación 1', puede_producir=1, puede_envasar=0, orden=1, tipo='produccion', requiere_limpieza_profunda=1, activo=1 WHERE codigo='PROD1'",
        "UPDATE areas_planta SET nombre='Fabricación y Envasado 2', puede_producir=1, puede_envasar=1, orden=2, tipo='produccion', requiere_limpieza_profunda=1, activo=1 WHERE codigo='PROD2'",
        "UPDATE areas_planta SET nombre='Fabricación y Envasado 3', puede_producir=1, puede_envasar=1, orden=3, tipo='produccion', requiere_limpieza_profunda=1, activo=1 WHERE codigo='PROD3'",
        "UPDATE areas_planta SET nombre='Envasado 1', puede_producir=0, puede_envasar=1, orden=4, tipo='produccion', requiere_limpieza_profunda=1, activo=1 WHERE codigo='ENV1'",
        "UPDATE areas_planta SET nombre='Envasado 2', puede_producir=0, puede_envasar=1, orden=5, tipo='produccion', requiere_limpieza_profunda=1, activo=1 WHERE codigo='ENV2'",
        # Dispensación y Acondicionamiento: visibles (mapa + rótulos de limpieza) pero
        # tipo='apoyo_asignable' → el auto-asignador de FABRICACIÓN NO las usa.
        "UPDATE areas_planta SET nombre='Dispensación', orden=6, tipo='apoyo_asignable', requiere_limpieza_profunda=1, activo=1 WHERE codigo='DISP'",
        "UPDATE areas_planta SET nombre='Acondicionamiento', orden=7, tipo='apoyo_asignable', requiere_limpieza_profunda=1, activo=1 WHERE codigo='ACOND'",
        # Desactivar duplicados (no romper FKs: solo activo=0).
        "UPDATE areas_planta SET activo=0 WHERE codigo IN ('FAB1','FAB2','FAB3','FAB_FLOAT')",
    ]),

    (223, "rotulos_limpieza · rótulo virtual PRD-PRO-002-F02 (Estado de Limpieza de Áreas/Equipos) · snapshot inmutable Part 11 · fluye con producción · 6-jun-2026", [
        # Rótulo virtual e interactivo de limpieza de áreas/equipos (formato
        # PRD-PRO-002-F02 v02). El ESTADO físico (Limpio/En uso/Sucio) NO vive
        # acá — su fuente de verdad es areas_planta.estado (libre/ocupada/sucia).
        # Esta tabla guarda el REGISTRO F02 por ciclo de limpieza: un snapshot
        # inmutable (21 CFR Part 11) de qué se elaboró, qué había antes,
        # sanitizante/detergente, equipos limpiados, y las dos firmas
        # (operario realiza · Calidad verifica). Una fila por ciclo: nace al
        # 'realizar' y se cierra al 'verificar'. producto/lote se FOTOGRAFÍAN al
        # firmar (no se re-derivan luego · M9 snapshot vs vivo).
        """CREATE TABLE IF NOT EXISTS rotulos_limpieza (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_id INTEGER NOT NULL,
            area_codigo TEXT DEFAULT '',
            produccion_id INTEGER DEFAULT NULL,
            producto_elaborar TEXT DEFAULT '',
            lote_elaborar TEXT DEFAULT '',
            producto_anterior TEXT DEFAULT '',
            lote_anterior TEXT DEFAULT '',
            sanitizante TEXT DEFAULT 'Alcohol 70%',
            detergente TEXT DEFAULT 'Detergente Neutro Industrial',
            equipos_json TEXT DEFAULT '',
            estado TEXT NOT NULL DEFAULT 'realizado',
            realizado_por TEXT DEFAULT '',
            realizado_at TEXT DEFAULT '',
            verificado_por TEXT DEFAULT '',
            verificado_at TEXT DEFAULT '',
            verificado_sign_id INTEGER DEFAULT NULL,
            despeje_checklist_id INTEGER DEFAULT NULL,
            observaciones TEXT DEFAULT '',
            creado_en TEXT DEFAULT (datetime('now')),
            actualizado_en TEXT DEFAULT NULL,
            FOREIGN KEY (area_id) REFERENCES areas_planta(id)
        )""",
        # Búsqueda del ciclo abierto/último por área.
        "CREATE INDEX IF NOT EXISTS idx_rotlimp_area ON rotulos_limpieza(area_id, id DESC)",
    ]),

    (222, "ebr_despeje_items.etapa · soporta DOS despejes (dispensación + fabricación) con el mismo checklist · MyBatch sección 2 y 4 · 6-jun-2026", [
        # MyBatch tiene 2 despejes en el instructivo: '2. Despeje - Dispensación' y
        # '4. Despeje - Fabricación', mismas 13 verificaciones pero independientes.
        # Discriminamos por 'etapa'. Las filas existentes quedan como 'dispensacion'.
        "ALTER TABLE ebr_despeje_items ADD COLUMN etapa TEXT DEFAULT 'dispensacion'",
        # El UNIQUE viejo (ebr_id,item_idx) impediría tener las 2 etapas → se
        # reemplaza por (ebr_id,item_idx,etapa).
        "DROP INDEX IF EXISTS idx_ebrdespitem_uniq",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_ebrdespitem_uniq2 ON ebr_despeje_items(ebr_id, item_idx, etapa)",
    ]),

    (221, "conteo_items · UNIQUE(conteo_id,codigo_mp,lote) anti-duplicado · arregla doble-ajuste por INSERT OR REPLACE sin clave en PG · 6-jun-2026", [
        # Incidente 6-jun: conteo_items NO tenía clave única, y el guardado usa
        # INSERT OR REPLACE → en PostgreSQL el ON CONFLICT caía a la PK 'id' (que
        # no va en el INSERT) → NUNCA reemplazaba, INSERTABA filas duplicadas por
        # cada re-guardado. Al cerrar el conteo eso aplicaría DOBLE ajuste al kardex.
        # 1) normalizar lote NULL→'' (para que el UNIQUE agrupe bien).
        "UPDATE conteo_items SET lote='' WHERE lote IS NULL",
        # 2) de-duplicar conservando la fila más reciente (MAX id = último guardado
        #    = valor final que el operario dejó). Borra solo duplicados del bug.
        """DELETE FROM conteo_items WHERE id NOT IN (
              SELECT MAX(id) FROM conteo_items
              GROUP BY conteo_id, codigo_mp, lote)""",
        # 3) clave única → desde ahora INSERT OR REPLACE reemplaza (pg_adapter elige
        #    este keyset como target del ON CONFLICT) en vez de duplicar.
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_conteo_items ON conteo_items(conteo_id, codigo_mp, lote)",
    ]),

    (220, "ebr_despeje_items · checklist granular de despeje de línea (13 verificaciones GMP por ítem · MyBatch estación ② detalle) · 5-jun-2026", [
        # MyBatch muestra el despeje como tabla VERIFICACIÓN/CUMPLE/ACCIONES con 13
        # verificaciones. Esta tabla guarda el CUMPLE (Sí/No) por ítem, con e-firma del
        # responsable. La tabla coarse ebr_despeje_linea sigue para el gate de liberación.
        """CREATE TABLE IF NOT EXISTS ebr_despeje_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ebr_id INTEGER NOT NULL,
            item_idx INTEGER NOT NULL,
            item_texto TEXT NOT NULL,
            cumple INTEGER DEFAULT NULL,
            observaciones TEXT DEFAULT '',
            registrado_por TEXT DEFAULT '',
            registrado_at_utc TEXT DEFAULT '',
            FOREIGN KEY (ebr_id) REFERENCES ebr_ejecuciones(id) ON DELETE CASCADE
        )""",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_ebrdespitem_uniq ON ebr_despeje_items(ebr_id, item_idx)",
    ]),

    (219, "ebr_ejecuciones.area_codigo · Área o Línea de la orden (MyBatch parity · 4 áreas autorizadas INVIMA) · 5-jun-2026", [
        "ALTER TABLE ebr_ejecuciones ADD COLUMN area_codigo TEXT DEFAULT ''",
    ]),

    (218, "maestro_mps.controla_stock · MP de fabricación propia/infinita (AGUA del lab) no exige ni descuenta stock · 4-jun-2026", [
        # Default 1 = se controla normal. 0 = infinita / fabricada en casa (agua
        # desionizada del laboratorio): producción la ignora (no bloquea, no descuenta).
        "ALTER TABLE maestro_mps ADD COLUMN controla_stock INTEGER DEFAULT 1",
        # El agua se produce en el lab (desionizada), es prácticamente infinita y no
        # se compra → nunca debe bloquear producción ni generar faltantes/negativos.
        "UPDATE maestro_mps SET controla_stock=0 WHERE UPPER(TRIM(COALESCE(nombre_inci,''))) IN ('AQUA','AGUA','WATER','AGUA DESIONIZADA','AGUA DESTILADA','AQUA (WATER)','AQUA/WATER') OR UPPER(TRIM(COALESCE(nombre_comercial,''))) LIKE 'AGUA%' OR codigo_mp='MPAGUALI01'",
    ]),

    (217, "ebr_registros_fisicos · adjuntar registros físicos/PDF al legajo (MyBatch estación ⑦) · 3-jun-2026", [
        """CREATE TABLE IF NOT EXISTS ebr_registros_fisicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ebr_id INTEGER NOT NULL,
            descripcion TEXT NOT NULL,
            tipo TEXT DEFAULT 'registro',
            archivo_nombre TEXT DEFAULT '',
            archivo_b64 TEXT DEFAULT NULL,
            registrado_por TEXT NOT NULL,
            registrado_at_utc TEXT NOT NULL,
            FOREIGN KEY (ebr_id) REFERENCES ebr_ejecuciones(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ebrreg_ebr ON ebr_registros_fisicos(ebr_id)",
    ]),

    (216, "ebr_precauciones · precauciones + equipos del proceso (MyBatch estación ①) · 3-jun-2026", [
        """CREATE TABLE IF NOT EXISTS ebr_precauciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ebr_id INTEGER NOT NULL,
            tipo TEXT DEFAULT 'precaucion',
            descripcion TEXT NOT NULL,
            registrado_por TEXT NOT NULL,
            registrado_at_utc TEXT NOT NULL,
            FOREIGN KEY (ebr_id) REFERENCES ebr_ejecuciones(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ebrprec_ebr ON ebr_precauciones(ebr_id)",
    ]),

    (215, "ebr_despeje_linea · despeje de línea por legajo (checklist CUMPLE · MyBatch estación ②) · 3-jun-2026", [
        # MyBatch · antes de fabricar/envasar: despeje de línea (área limpia, sin
        # producto anterior, equipos limpios/identificados, documentación). Un
        # registro por EBR, con e-firma del responsable. Gate de liberación opcional.
        """CREATE TABLE IF NOT EXISTS ebr_despeje_linea (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ebr_id INTEGER NOT NULL,
            area_limpia INTEGER DEFAULT 0,
            sin_producto_anterior INTEGER DEFAULT 0,
            equipos_limpios INTEGER DEFAULT 0,
            documentacion_ok INTEGER DEFAULT 0,
            conforme INTEGER DEFAULT 0,
            observaciones TEXT DEFAULT '',
            realizado_por TEXT,
            realizado_at_utc TEXT,
            e_sign_id INTEGER DEFAULT NULL,
            FOREIGN KEY (ebr_id) REFERENCES ebr_ejecuciones(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ebrdesp_ebr ON ebr_despeje_linea(ebr_id)",
    ]),

    (214, "ebr_ejecuciones · rendimiento por unidades (Envasado/Acondicionamiento) · reemplazo MyBatch Batch C · 3-jun-2026", [
        # El yield de granel (yield_pct) es g_real/g_objetivo · sirve para
        # Fabricación. En Envasado/Acondicionamiento el rendimiento se mide en
        # UNIDADES (buenas vs teóricas). Aditivo · NULL por defecto · no toca el
        # yield de granel. yield_uds_pct = unidades_buenas_real / unidades_teoricas.
        "ALTER TABLE ebr_ejecuciones ADD COLUMN unidades_teoricas REAL DEFAULT NULL",
        "ALTER TABLE ebr_ejecuciones ADD COLUMN unidades_buenas_real REAL DEFAULT NULL",
        "ALTER TABLE ebr_ejecuciones ADD COLUMN yield_uds_pct REAL DEFAULT NULL",
    ]),

    (213, "ebr_observaciones · observaciones generales del proceso (bitácora del legajo) · reemplazo MyBatch · Sebastián 2-jun-2026", [
        # MyBatch tiene "Observaciones Generales del Proceso": bitácora libre
        # (quién, cuándo, qué) durante la ejecución. Tabla nueva append-only.
        """CREATE TABLE IF NOT EXISTS ebr_observaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ebr_id INTEGER NOT NULL,
            descripcion TEXT NOT NULL,
            registrado_por TEXT NOT NULL,
            registrado_at_utc TEXT NOT NULL,
            FOREIGN KEY (ebr_id) REFERENCES ebr_ejecuciones(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ebrobs_ebr ON ebr_observaciones(ebr_id)",
    ]),

    (212, "ebr_ejecuciones · densidad + mL envasable (puente OP→OF · cuánto bulk pasa a envasado) · reemplazo MyBatch · Sebastián 2-jun-2026", [
        # MyBatch al cerrar la OP captura densidad (g/mL) y calcula la "cantidad
        # disponible" en mL que pasa a envasado (lot_amount_filling). Es el puente
        # OP→OF: el granel fabricado (g) se convierte a mL envasables.
        # Aditivo · NULL por defecto. ml_envasable = cantidad_real_g / densidad.
        "ALTER TABLE ebr_ejecuciones ADD COLUMN densidad_g_ml REAL DEFAULT NULL",
        "ALTER TABLE ebr_ejecuciones ADD COLUMN ml_envasable REAL DEFAULT NULL",
    ]),

    (211, "ebr_artes_codificacion · gate de etiquetado en Acondicionamiento (aprobar arte + código lote/vencimiento) · reemplazo MyBatch OA · Sebastián 2-jun-2026", [
        # MyBatch en OA tiene "Aprobación de Artes / Codificación" + "Aprobar
        # Etiqueta": antes de liberar se verifica que el ARTE de la etiqueta y la
        # CODIFICACIÓN (lote/vencimiento impreso) sean correctos. Gate GMP de
        # etiquetado. Tabla nueva · la aprobación lleva e-firma (meaning='aprueba').
        """CREATE TABLE IF NOT EXISTS ebr_artes_codificacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ebr_id INTEGER NOT NULL,
            descripcion TEXT NOT NULL,
            codigo_lote TEXT DEFAULT '',
            codigo_vencimiento TEXT DEFAULT '',
            aprobado_por TEXT DEFAULT '',
            aprobado_at_utc TEXT DEFAULT NULL,
            e_sign_id INTEGER DEFAULT NULL,
            creado_por TEXT NOT NULL,
            creado_at_utc TEXT NOT NULL,
            notas TEXT DEFAULT '',
            FOREIGN KEY (ebr_id) REFERENCES ebr_ejecuciones(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_artescod_ebr ON ebr_artes_codificacion(ebr_id)",
        """CREATE TRIGGER IF NOT EXISTS trg_artescod_no_edit_liberado
           BEFORE UPDATE ON ebr_artes_codificacion
           FOR EACH ROW
           WHEN EXISTS (SELECT 1 FROM ebr_ejecuciones
                        WHERE id = NEW.ebr_id AND estado IN ('liberado','rechazado'))
                AND OLD.aprobado_at_utc IS NOT NULL
           BEGIN
               SELECT RAISE(ABORT, 'arte/codificación aprobada de EBR liberado es inmutable');
           END""",
    ]),

    (210, "ebr_conciliacion_material · conciliación de material de envase/empaque (requerida/recibida/devuelta/utilizada) · reemplazo MyBatch fase envasado/acond · Sebastián 2-jun-2026", [
        # MyBatch en OF/OA controla el material de empaque: cuánto se PIDIÓ, cuánto
        # se RECIBIÓ, cuánto se DEVOLVIÓ y cuánto se UTILIZÓ (conciliación GMP).
        # Tabla nueva (no toca nada existente). utilizada = recibida - devuelta si
        # no se especifica. Inmutable tras liberar (trigger SQLite + guard en el
        # endpoint para paridad PG, donde el trigger se omite).
        """CREATE TABLE IF NOT EXISTS ebr_conciliacion_material (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ebr_id INTEGER NOT NULL,
            tipo TEXT DEFAULT 'envase',
            material_codigo TEXT DEFAULT '',
            material_nombre TEXT NOT NULL,
            lote_material TEXT DEFAULT '',
            cant_requerida REAL DEFAULT 0,
            cant_recibida REAL DEFAULT 0,
            cant_devuelta REAL DEFAULT 0,
            cant_utilizada REAL DEFAULT 0,
            registrado_por TEXT NOT NULL,
            registrado_at_utc TEXT NOT NULL,
            e_sign_id INTEGER DEFAULT NULL,
            notas TEXT DEFAULT '',
            FOREIGN KEY (ebr_id) REFERENCES ebr_ejecuciones(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_concmat_ebr ON ebr_conciliacion_material(ebr_id)",
        """CREATE TRIGGER IF NOT EXISTS trg_concmat_no_edit_liberado
           BEFORE UPDATE ON ebr_conciliacion_material
           FOR EACH ROW
           WHEN EXISTS (SELECT 1 FROM ebr_ejecuciones
                        WHERE id = NEW.ebr_id AND estado IN ('liberado','rechazado'))
           BEGIN
               SELECT RAISE(ABORT, 'conciliación de EBR liberado/rechazado es inmutable');
           END""",
        """CREATE TRIGGER IF NOT EXISTS trg_concmat_no_delete_liberado
           BEFORE DELETE ON ebr_conciliacion_material
           FOR EACH ROW
           WHEN EXISTS (SELECT 1 FROM ebr_ejecuciones
                        WHERE id = OLD.ebr_id AND estado IN ('liberado','rechazado'))
           BEGIN
               SELECT RAISE(ABORT, 'conciliación de EBR liberado/rechazado es inmutable · DELETE prohibido');
           END""",
    ]),

    (209, "ebr · discriminador de FASE del legajo (fabricacion/envasado/acondicionamiento) · motor EBR único por fases · reemplazo MyBatch · Sebastián 2-jun-2026", [
        # MyBatch usa el MISMO esqueleto EBR para OP/OF/OA. Acá habilitamos UN
        # motor por fases:
        #   ebr_ejecuciones.fase      → qué fase ejecuta este legajo
        #   ebr_pasos_ejecutados.fase → se arrastra desde mbr_pasos.fase (que YA
        #                               existe) para agrupar los pasos por fase.
        # 100% ADITIVO · DEFAULT 'fabricacion' → legajos existentes = fabricación
        # (que es lo que son hoy). NO toca el constraint UNIQUE de mbr_templates:
        # los pasos por fase ya viven en mbr_pasos.fase dentro de un único template.
        "ALTER TABLE ebr_ejecuciones ADD COLUMN fase TEXT DEFAULT 'fabricacion'",
        "ALTER TABLE ebr_pasos_ejecutados ADD COLUMN fase TEXT DEFAULT ''",
    ]),

    (208, "ebr_pesajes · 2ª firma de verificación de pesaje (verified_weight estilo MyBatch) · reemplazo MyBatch · Sebastián 2-jun-2026", [
        # Reemplazo MyBatch: cada pesaje de MP puede ser VERIFICADO por una 2ª
        # persona (Calidad), igual que el `verified_weight` de MyBatch. Es la
        # segregación de funciones GMP: el verificador NO puede ser quien pesó.
        # 100% ADITIVO · DEFAULT ''/NULL → los pesajes existentes quedan "sin
        # verificar" sin romper nada. La verificación solo aplica mientras el EBR
        # está iniciado/en_proceso (el trigger trg_pesajes_no_edit_liberado ya
        # bloquea cualquier UPDATE tras liberar/rechazar).
        "ALTER TABLE ebr_pesajes ADD COLUMN verificado_por TEXT DEFAULT ''",
        "ALTER TABLE ebr_pesajes ADD COLUMN verificado_at_utc TEXT DEFAULT NULL",
        "ALTER TABLE ebr_pesajes ADD COLUMN verificado_e_sign_id INTEGER DEFAULT NULL",
    ]),

    (207, "facturas_proveedor_pdf · blob del PDF en tabla 1:1 (saca el base64 de la tabla transaccional · anti-OOM/bloat en listados) · Sebastián 1-jun-2026", [
        # Audit escalabilidad: el PDF base64 (hasta 6MB) vivía en
        # facturas_proveedor.pdf_adjunto → SELECT * arrastraba MB por fila. Ahora
        # vive en tabla 1:1; la tabla padre queda liviana para listados/índices.
        "CREATE TABLE IF NOT EXISTS facturas_proveedor_pdf (factura_id INTEGER PRIMARY KEY, pdf_adjunto TEXT)",
        "INSERT INTO facturas_proveedor_pdf (factura_id, pdf_adjunto) SELECT id, pdf_adjunto FROM facturas_proveedor WHERE COALESCE(pdf_adjunto,'') != ''",
        "UPDATE facturas_proveedor SET pdf_adjunto='' WHERE COALESCE(pdf_adjunto,'') != ''",
    ]),

    (206, "facturas_proveedor · libro de facturas de proveedor (cuentas por pagar formal): factura = padre de pagos, con retenciones (IVA/retefuente/reteICA), vencimiento/estado, PDF y vínculo a OC · Sebastián 31-may-2026", [
        # Sebastián 31-may-2026 · hasta ahora la factura de proveedor vivía SOLO
        # como pagos_oc.numero_factura_proveedor (un texto + imagen). Esta tabla la
        # vuelve una ENTIDAD: una factura (documento real del proveedor) puede
        # tener 1+ pagos parciales (pagos_oc.factura_proveedor_id la liga). El
        # estado (pendiente/parcial/pagada/vencida/anulada) se recalcula por
        # SUM(pagos) vs total. Retenciones a nivel factura (no solo en el CE de
        # egreso). 3-way: numero_oc liga a la OC y a lo recibido.
        """CREATE TABLE IF NOT EXISTS facturas_proveedor (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_factura    TEXT NOT NULL,
            proveedor         TEXT NOT NULL DEFAULT '',
            nit               TEXT DEFAULT '',
            numero_oc         TEXT DEFAULT '',
            fecha_emision     TEXT NOT NULL DEFAULT (date('now','-5 hours')),
            fecha_vencimiento TEXT DEFAULT '',
            subtotal          REAL DEFAULT 0,
            iva               REAL DEFAULT 0,
            iva_pct           REAL DEFAULT 0,
            retefuente        REAL DEFAULT 0,
            retefuente_pct    REAL DEFAULT 0,
            retica            REAL DEFAULT 0,
            retica_pct        REAL DEFAULT 0,
            total             REAL DEFAULT 0,
            estado            TEXT DEFAULT 'pendiente',
            pdf_adjunto       TEXT DEFAULT '',
            observaciones     TEXT DEFAULT '',
            creado_por        TEXT DEFAULT '',
            created_at        TEXT DEFAULT (datetime('now')),
            empresa           TEXT DEFAULT 'Espagiria'
        )""",
        "CREATE INDEX IF NOT EXISTS idx_facturas_prov_oc ON facturas_proveedor(numero_oc)",
        "CREATE INDEX IF NOT EXISTS idx_facturas_prov_prov ON facturas_proveedor(proveedor)",
        "CREATE INDEX IF NOT EXISTS idx_facturas_prov_estado ON facturas_proveedor(estado)",
        "CREATE INDEX IF NOT EXISTS idx_facturas_prov_venc ON facturas_proveedor(fecha_vencimiento)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_facturas_prov_unq ON facturas_proveedor(proveedor, numero_factura) WHERE numero_factura != ''",
        "ALTER TABLE pagos_oc ADD COLUMN factura_proveedor_id INTEGER",
        "CREATE INDEX IF NOT EXISTS idx_pagos_oc_factura_id ON pagos_oc(factura_proveedor_id) WHERE factura_proveedor_id IS NOT NULL",
    ]),

    (205, "produccion_programada.fija_override_json · override de cantidad fija POR LOTE (ajustar minis de un lote puntual sin cambiar el default del producto) · Sebastián 30-may-2026", [
        # Sebastián 30-may-2026 · el default de la cantidad fija vive en
        # producto_presentaciones.cantidad_fija_uds (mig 204 · se edita en el
        # modal admin). Este campo permite, AL PROGRAMAR un lote, subir/bajar la
        # cantidad fija SOLO para ese lote (ej. promo: 2000 minis en vez de 1200)
        # sin tocar el default. JSON map {presentacion_codigo: uds}. NULL = usar
        # el default del producto. Lo lee composicion-mee (override > default).
        "ALTER TABLE produccion_programada ADD COLUMN fija_override_json TEXT",
    ]),

    (204, "producto_presentaciones.cantidad_fija_uds · presentaciones con cantidad FIJA por lote (ej. mini 10ml regalo = 1200 uds siempre, resto al envase principal) · Sebastián 30-may-2026", [
        # Sebastián 30-may-2026 · SUERO ILUMINADOR TRX: el 10ml es SIEMPRE 1200
        # uds, NO un % del bulk. Si cantidad_fija_uds > 0, composicion-mee reserva
        # primero esas uds (con su kg) y reparte el RESTO del bulk por ratio entre
        # las demás presentaciones. 0 = ratio % normal (comportamiento previo).
        "ALTER TABLE producto_presentaciones ADD COLUMN cantidad_fija_uds REAL DEFAULT 0",
    ]),

    (203, "ipc_resultados.desviacion_id · enlace IPC fuera de spec → desviación/CAPA automática (reemplazo MyBatch fase 2) · 30-may-2026", [
        # Cuando un IPC del EBR sale NO conforme se abre una desviación
        # automáticamente (aseguramiento) y se enlaza acá para trazabilidad
        # bidireccional EBR/IPC ↔ desviación. El EBR no se libera con la
        # desviación abierta.
        "ALTER TABLE ipc_resultados ADD COLUMN desviacion_id INTEGER",
        "CREATE INDEX IF NOT EXISTS idx_ipcres_desviacion ON ipc_resultados(desviacion_id) WHERE desviacion_id IS NOT NULL",
    ]),

    (202, "rate_limit_hits · rate limit cross-worker para webhooks públicos (el limiter en memoria se anulaba con 3 workers gunicorn) · audit ronda2 29-may-2026", [
        # Audit ronda2 29-may-2026: comercial._rate_limit_check usaba un dict en
        # memoria por proceso · con 3 workers el límite efectivo era 3×. Esta
        # tabla permite un limiter por ventana deslizante compartido entre
        # workers. El código es deploy-safe: si la tabla no existe (mig sin
        # aplicar en PG) cae al limiter en memoria, sin regresión.
        "CREATE TABLE IF NOT EXISTS rate_limit_hits (clave TEXT NOT NULL, ts REAL NOT NULL)",
        "CREATE INDEX IF NOT EXISTS idx_rlh_clave_ts ON rate_limit_hits(clave, ts)",
    ]),

    (201, "movimientos.produccion_id · reversión precisa del descuento MP (evita cross-reversal entre producciones mismo producto+fecha) · audit profundo 28-may-2026", [
        # Sebastián 28-may-2026 (audit profundo): /revertir-completado filtraba
        # las Salidas de MP por LIKE 'Producción ... {producto} — {fecha}%'. Dos
        # producciones del MISMO producto+fecha (split B2B/DTC) colisionaban y
        # revertir UNA devolvía el MP de AMBAS → inventario fantasma (drift +).
        # Ahora cada Salida de producción guarda produccion_id y la reversión
        # filtra por id exacto (con fallback LIKE solo para movimientos legacy
        # sin produccion_id). Mismo patrón que ya usaba MEE vía lote_ref.
        "ALTER TABLE movimientos ADD COLUMN produccion_id INTEGER",
        "CREATE INDEX IF NOT EXISTS idx_mov_produccion_id ON movimientos(produccion_id)",
    ]),

    (200, "marketing_cmo_plan · CMO IA agencia autónoma · plan diario decisiones · Sebastián 27-may-2026 PM", [
        # Sebastián 27-may-2026 · "marketing debe ser superior, debe ser una
        # agencia de marketing impulsada por IA". CMO IA cron diario 7 AM
        # toma snapshot completo (Shopify+IG+stock+influencers+eventos) y
        # Claude devuelve plan estructurado: qué hacer hoy + prioridad +
        # justificación. UI tab nueva con botones [Aprobar/Posponer/Descartar].
        # Aprobar → dispara workflow/aplicar-agente correspondiente.
        """CREATE TABLE IF NOT EXISTS marketing_cmo_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            acciones_json TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente'
                CHECK(estado IN ('pendiente','parcial','completado','descartado')),
            generado_por TEXT NOT NULL DEFAULT 'cron-cmo-7am',
            snapshot_json TEXT,
            aprobado_por TEXT,
            aprobado_at TEXT,
            notas TEXT,
            creado_at TEXT NOT NULL DEFAULT (datetime('now','-5 hours'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_mcmo_fecha ON marketing_cmo_plan(fecha DESC)",
        # Acciones individuales tracking (cada item del plan)
        """CREATE TABLE IF NOT EXISTS marketing_cmo_acciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            prioridad TEXT NOT NULL DEFAULT 'media'
                CHECK(prioridad IN ('critica','alta','media','baja')),
            titulo TEXT NOT NULL,
            descripcion TEXT,
            agente_workflow TEXT,
            payload_json TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente'
                CHECK(estado IN ('pendiente','aprobada','descartada','ejecutada','fallida','pospuesta')),
            resultado_ejecucion TEXT,
            decidido_por TEXT,
            decidido_at TEXT,
            FOREIGN KEY (plan_id) REFERENCES marketing_cmo_plan(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_mca_plan ON marketing_cmo_acciones(plan_id, estado)",
        "CREATE INDEX IF NOT EXISTS idx_mca_estado ON marketing_cmo_acciones(estado, prioridad)",
    ]),

    (199, "producto_presentaciones.ventas_mes_referencia · override manual ratio Shopify · Sebastián 27-may-2026 PM", [
        # Sebastián 27-may-2026 PM · "AZ lo vendemos de 30 y 15, de 15 200
        # unidades al mes". Cuando Shopify sync no captura bien el ratio
        # (SKU mismatch o cadencia >180d), el user puede fijar el ratio real
        # poniendo uds/mes referencia por presentación. Si AL MENOS una
        # presentación del producto tiene este campo > 0, el cálculo usa
        # ESTOS números (treating 0 como "no se vende") en vez de Shopify.
        "ALTER TABLE producto_presentaciones ADD COLUMN ventas_mes_referencia REAL DEFAULT 0",
    ]),

    (198, "cron_alerts_sent · anti-spam notificaciones cron · Sebastián 27-may-2026 PM", [
        # Sebastián 27-may-2026 PM · audit round 3 · OCs atrasadas y otros
        # crons notificaban DIARIO mientras la alerta seguía activa → spam.
        # Tabla guarda última notif por (tipo_alerta, registro_id) · cron
        # consulta antes de notificar y solo dispara si pasaron N días.
        """CREATE TABLE IF NOT EXISTS cron_alerts_sent (
            tipo_alerta TEXT NOT NULL,
            registro_id TEXT NOT NULL,
            ultima_notif TEXT NOT NULL,
            count_notifs INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (tipo_alerta, registro_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_cron_alerts_ultima ON cron_alerts_sent(ultima_notif)",
    ]),

    (197, "volumen_unitario_producto · idempotente · Sebastián 27-may-2026 PM", [
        # La tabla se referenciaba en programacion.py:7689 con except OperationalError
        # silencioso · si nunca se creó (PG legacy), volumen_ml=0 para todos y
        # MEE necesidades=0. Garantía idempotente con safe create.
        """CREATE TABLE IF NOT EXISTS volumen_unitario_producto (
            producto_nombre TEXT PRIMARY KEY,
            volumen_ml REAL DEFAULT 0,
            activo INTEGER DEFAULT 1
        )""",
    ]),

    (196, "mee_aliases · normalización abreviaturas envases · réplica patrón mp_aliases · Sebastián 27-may-2026 PM", [
        # Sebastián 27-may-2026 PM · "necesidades MEE sigue sin calcular".
        # Causa: si descripcion en sku_mee_config o nombre tipeado por
        # Catalina/Jefferson NO matchea exacto con maestro_mee.codigo o
        # maestro_mee.descripcion → consumo_mee_agregado = 0 silencioso.
        # Solución: réplica de mp_aliases (mig 158) para MEE.
        #  · alias → codigo_mee / descripcion_canonical
        #  · cron 4:35 AM normaliza sku_mee_config.mee_codigo
        #  · endpoint audit/fix para revisión manual
        """CREATE TABLE IF NOT EXISTS mee_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias TEXT NOT NULL,
            codigo_mee TEXT,
            descripcion_canonical TEXT,
            tipo TEXT DEFAULT 'abreviatura'
                CHECK(tipo IN ('abreviatura','sinonimo','typo_comun','translation')),
            fuente TEXT DEFAULT 'manual'
                CHECK(fuente IN ('manual','seed','auto-detectado','catalina','sebastian','jefferson')),
            creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            creado_por TEXT,
            activo INTEGER NOT NULL DEFAULT 1
        )""",
        "CREATE INDEX IF NOT EXISTS idx_mee_aliases_alias ON mee_aliases(LOWER(alias))",
        "CREATE INDEX IF NOT EXISTS idx_mee_aliases_codigo ON mee_aliases(codigo_mee)",
        # Seeds conservadores · solo abreviaturas estructurales obvias.
        # Sebastián agregará más vía endpoint CRUD según patrones que detecte.
        "INSERT OR IGNORE INTO mee_aliases (alias, descripcion_canonical, tipo, fuente) VALUES ('TA', 'TAPA', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mee_aliases (alias, descripcion_canonical, tipo, fuente) VALUES ('ENV', 'ENVASE', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mee_aliases (alias, descripcion_canonical, tipo, fuente) VALUES ('ETIQ', 'ETIQUETA', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mee_aliases (alias, descripcion_canonical, tipo, fuente) VALUES ('FCO', 'FRASCO', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mee_aliases (alias, descripcion_canonical, tipo, fuente) VALUES ('PLEG', 'PLEGADIZA', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mee_aliases (alias, descripcion_canonical, tipo, fuente) VALUES ('SERIG', 'SERIGRAFIA', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mee_aliases (alias, descripcion_canonical, tipo, fuente) VALUES ('TAMPOG', 'TAMPOGRAFIA', 'abreviatura', 'seed')",
        # Typos comunes ES
        "INSERT OR IGNORE INTO mee_aliases (alias, descripcion_canonical, tipo, fuente) VALUES ('plateada', 'PLATEADA', 'typo_comun', 'seed')",
        "INSERT OR IGNORE INTO mee_aliases (alias, descripcion_canonical, tipo, fuente) VALUES ('cuentagotas', 'CUENTAGOTAS', 'translation', 'seed')",
        "INSERT OR IGNORE INTO mee_aliases (alias, descripcion_canonical, tipo, fuente) VALUES ('airless', 'AIRLESS', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mee_aliases (alias, descripcion_canonical, tipo, fuente) VALUES ('spray', 'SPRAY', 'abreviatura', 'seed')",
    ]),

    (195, "pagos_influencers.fecha_contenido + vence_pago_at · flujo urgencia pago 30d · Sebastián 27-may-2026 PM", [
        # FEATURE 27-may PM · "promesa de pago a 30 días desde creación del
        # contenido". Jefferson registra fecha_contenido al solicitar pago ·
        # vence_pago_at = fecha_contenido + 30d (calculado en backend al insert).
        # Dashboard puede mostrar atrasados/próximos a vencer en rojo/amarillo.
        # Cron diario alerta a Sebastián si hay pagos atrasados.
        "ALTER TABLE pagos_influencers ADD COLUMN fecha_contenido TEXT DEFAULT ''",
        "ALTER TABLE pagos_influencers ADD COLUMN vence_pago_at TEXT DEFAULT ''",
        "CREATE INDEX IF NOT EXISTS idx_pi_vence ON pagos_influencers(vence_pago_at, estado)",
    ]),
    (194, "marketing_ads_campaigns · sync Meta/Google Ads · Sebastián 27-may-2026 AM", [
        # FEATURE 27-may · sync campañas pagadas Meta/Google · cierra ROI
        # real cross-channel (orgánico + paid).
        # Diseño unificado · una sola tabla con `platform` discriminator ·
        # facilita queries comparativas (sumar spend Meta + Google · etc).
        """CREATE TABLE IF NOT EXISTS marketing_ads_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL CHECK(platform IN ('meta','google','tiktok')),
            external_id TEXT NOT NULL,
            nombre TEXT,
            estado TEXT,
            objetivo TEXT,
            spend_total REAL DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            conversiones INTEGER DEFAULT 0,
            ctr REAL DEFAULT 0,
            cpc REAL DEFAULT 0,
            cpm REAL DEFAULT 0,
            roas REAL DEFAULT 0,
            fecha_inicio TEXT,
            fecha_fin TEXT,
            marketing_campana_id INTEGER,
            synced_at TEXT DEFAULT (datetime('now','-5 hours')),
            UNIQUE(platform, external_id),
            FOREIGN KEY (marketing_campana_id) REFERENCES marketing_campanas(id) ON DELETE SET NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ads_platform ON marketing_ads_campaigns(platform, estado)",
        "CREATE INDEX IF NOT EXISTS idx_ads_campana_link ON marketing_ads_campaigns(marketing_campana_id)",
    ]),
    (193, "marketing_ab_tests · A/B testing piezas IG · Sebastián 27-may-2026 AM", [
        # FEATURE 27-may · A/B testing nativo · "publicás 1 versión, no
        # sabés si la otra hubiera vendido más". Esta tabla relaciona 2
        # piezas marketing_contenido como variantes A/B y calcula ganador
        # cuando hay suficiente data.
        """CREATE TABLE IF NOT EXISTS marketing_ab_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            hipotesis TEXT,
            contenido_a_id INTEGER NOT NULL,
            contenido_b_id INTEGER NOT NULL,
            metrica_objetivo TEXT DEFAULT 'engagement'
                CHECK(metrica_objetivo IN ('engagement','clicks','conversiones','alcance')),
            ganadora TEXT
                CHECK(ganadora IN ('a','b','tie','indeterminado') OR ganadora IS NULL),
            ganadora_diff_pct REAL,
            ganadora_calculado_en TEXT,
            estado TEXT DEFAULT 'activo'
                CHECK(estado IN ('activo','cerrado','cancelado')),
            notas TEXT,
            creado_por TEXT,
            fecha_creacion TEXT DEFAULT (datetime('now','-5 hours')),
            FOREIGN KEY (contenido_a_id) REFERENCES marketing_contenido(id) ON DELETE CASCADE,
            FOREIGN KEY (contenido_b_id) REFERENCES marketing_contenido(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ab_estado ON marketing_ab_tests(estado, fecha_creacion)",
    ]),
    (192, "animus_instagram_comments · sentiment analysis comentarios IG · Sebastián 27-may-2026 AM", [
        # FEATURE 27-may · "detección de crisis temprana" del audit Marketing.
        # 5 quejas seguidas sobre un SKU debería disparar alerta antes de
        # que se viralice. Almacenamos comentarios reales del Graph API +
        # clasificación sentiment vía Claude (batch barato).
        #
        # Todos los tipos son cross-DB (TEXT/REAL/INTEGER · sin BLOB).
        """CREATE TABLE IF NOT EXISTS animus_instagram_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comment_id TEXT UNIQUE,
            post_id TEXT,
            autor_username TEXT,
            texto TEXT,
            publicado_en TEXT,
            sentiment TEXT,
            sentiment_score REAL,
            sku_detectado TEXT,
            analizado_en TEXT,
            synced_at TEXT DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ig_comm_post ON animus_instagram_comments(post_id)",
        "CREATE INDEX IF NOT EXISTS idx_ig_comm_sentiment ON animus_instagram_comments(sentiment, publicado_en)",
    ]),
    (191, "marketing_outreach_log · audit de mensajes pre-armados a influencers · Sebastián 26-may-2026 PM", [
        # FEATURE 26-may · cada vez que Sebastián genera/usa un mensaje
        # pre-armado de outreach a un influencer, queda registrado aquí ·
        # sirve para:
        #   1. Audit trail (quién contactó a quién, cuándo, por qué SKU)
        #   2. Anti-spam: warning si ya enviaste mensaje en últimos 14d
        #   3. Métricas: cuántos outreach al mes, conversión a colaboración
        """CREATE TABLE IF NOT EXISTS marketing_outreach_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            influencer_id INTEGER NOT NULL,
            sku_objetivo TEXT,
            campana_id INTEGER,
            canal TEXT CHECK(canal IN ('whatsapp','email','instagram','manual')),
            mensaje_preview TEXT,            -- primeros 200 chars del texto generado
            generado_por TEXT,
            usado_en TEXT,                   -- timestamp si user marcó "ya envié"
            fecha_creacion TEXT DEFAULT (datetime('now','-5 hours')),
            FOREIGN KEY (influencer_id) REFERENCES marketing_influencers(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_outreach_influencer ON marketing_outreach_log(influencer_id, fecha_creacion)",
        "CREATE INDEX IF NOT EXISTS idx_outreach_fecha ON marketing_outreach_log(fecha_creacion)",
    ]),
    (190, "users_mfa.secret_enc · TOTP secrets encriptados at rest · Sebastián 26-may-2026 PM", [
        # P1 audit MFA · TOTP secrets se guardaban PLAINTEXT en users_mfa.secret
        # · si DB dump leak, atacante puede generar códigos MFA válidos.
        # AHORA encriptamos con Fernet (AES-128-CBC + HMAC-SHA256) usando
        # MFA_MASTER_KEY env var como llave.
        #
        # Modo dual durante transición:
        #   - secret (plaintext legacy) · si secret_enc IS NULL
        #   - secret_enc TEXT (Fernet output es base64 ASCII · cross-DB safe).
        # Si MFA_MASTER_KEY no está configurada en Render, secret queda plaintext
        # con warn en startup (modo degradado · igual que como estaba antes).
        #
        # HOTFIX 27-may · usar TEXT en lugar de BLOB · PostgreSQL no soporta
        # BLOB y pg_compat NO lo traduce · esto rompía mig 190 en deploy
        # Render (app caía con 500 "Error interno del servidor" en startup).
        "ALTER TABLE users_mfa ADD COLUMN secret_enc TEXT DEFAULT NULL",
    ]),
    (189, "animus_ghl_opportunities · pipelines GHL · Sebastián 26-may-2026 PM", [
        # FEATURE 26-may · GHL sync actual SOLO trae contactos básicos
        # (nombre/email/telefono/tags). Falta lo más valioso de GHL:
        # opportunities (deals con monetary_value, status, pipeline_stage).
        # Esta tabla espeja la API /opportunities/ de GHL v2.
        """CREATE TABLE IF NOT EXISTS animus_ghl_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ghl_id TEXT UNIQUE,
            ghl_contact_id TEXT,
            ghl_pipeline_id TEXT,
            ghl_stage_id TEXT,
            nombre TEXT,
            pipeline_nombre TEXT,
            stage_nombre TEXT,
            status TEXT,                    -- open/won/lost/abandoned
            monetary_value REAL DEFAULT 0,
            source TEXT,
            assigned_to TEXT,
            ghl_created_at TEXT,
            ghl_updated_at TEXT,
            synced_at TEXT DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ghl_opp_contact ON animus_ghl_opportunities(ghl_contact_id)",
        "CREATE INDEX IF NOT EXISTS idx_ghl_opp_status ON animus_ghl_opportunities(status, ghl_updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_ghl_opp_pipeline ON animus_ghl_opportunities(ghl_pipeline_id, ghl_stage_id)",
    ]),
    (188, "users_mfa_backup_codes · 10 códigos one-time por user · Sebastián 26-may-2026 PM", [
        # P1 audit MFA · "si pierdo el teléfono pierdo acceso 60 días" era
        # el riesgo · ahora cada user enroll genera 10 backup codes one-time
        # (estándar industria · GitHub/Google/Microsoft hacen igual).
        #
        # Diseño:
        #   - 1 fila por código (max 10 activos por user)
        #   - code_hash con pbkdf2:sha256:600000 (igual que passwords)
        #   - used_at TIMESTAMP cuando se consume · NO se borra (audit trail)
        #   - regenerar invalida TODOS los anteriores (set used_at=now)
        #
        # users_mfa.backup_code_hash queda como legacy fallback (1 code old)
        # para no romper users existentes hasta que regeneren.
        """CREATE TABLE IF NOT EXISTS users_mfa_backup_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT NOT NULL,
            code_hash  TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now','utc')),
            used_at    TEXT,
            used_from_ip TEXT,
            FOREIGN KEY (username) REFERENCES users_passwords(username) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_mfa_backup_user ON users_mfa_backup_codes(username, used_at)",
    ]),
    (187, "marketing_metas · objetivos mensuales Dashboard · Sebastián 26-may-2026 AM", [
        # FEATURE 26-may · "Marketing decisional" #4
        # Metas mensuales de revenue/pedidos/clientes para mostrar
        # % cumplimiento vs realidad Shopify en Dashboard.
        # Una fila por mes (YYYY-MM) · upsert · audit_log al cambiar.
        """CREATE TABLE IF NOT EXISTS marketing_metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mes TEXT NOT NULL UNIQUE,                -- 'YYYY-MM'
            revenue_meta REAL DEFAULT 0,
            pedidos_meta INTEGER DEFAULT 0,
            clientes_nuevos_meta INTEGER DEFAULT 0,
            notas TEXT DEFAULT '',
            creada_por TEXT,
            fecha_creacion TEXT DEFAULT (datetime('now','-5 hours')),
            fecha_actualizacion TEXT DEFAULT (datetime('now','-5 hours'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_meta_mes ON marketing_metas(mes)",
    ]),
    (186, "marketing_eventos_calendario · calendario cosmético editable · Sebastián 26-may-2026 AM", [
        # FEATURE 26-may · "Marketing decisional" #4
        # CALENDARIO_COSMETICO estaba hardcoded en marketing.py (10 eventos fijos).
        # Ahora editable desde UI · agentes leen de aquí con fallback al hardcoded.
        # multiplicador: factor de demanda vs día normal (Black Friday 3.5, etc).
        """CREATE TABLE IF NOT EXISTS marketing_eventos_calendario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento TEXT NOT NULL,
            fecha TEXT NOT NULL,                       -- 'YYYY-MM-DD'
            color TEXT DEFAULT '#94a3b8',
            multiplicador REAL DEFAULT 1.0 CHECK(multiplicador > 0),
            activo INTEGER DEFAULT 1,
            notas TEXT DEFAULT '',
            creado_por TEXT,
            fecha_creacion TEXT DEFAULT (datetime('now','-5 hours'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_evento_cal_fecha ON marketing_eventos_calendario(fecha, activo)",
        # Sembrar con los 10 hardcoded del módulo · idempotente (UNIQUE evento+fecha)
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_evento_cal_evento_fecha ON marketing_eventos_calendario(evento, fecha)",
        "INSERT OR IGNORE INTO marketing_eventos_calendario (evento, fecha, color, multiplicador, creado_por) VALUES ('Día de la Mujer','2026-03-08','#e91e8c',1.8,'seed_185')",
        "INSERT OR IGNORE INTO marketing_eventos_calendario (evento, fecha, color, multiplicador, creado_por) VALUES ('Día de la Madre','2026-05-10','#d4af37',3.0,'seed_185')",
        "INSERT OR IGNORE INTO marketing_eventos_calendario (evento, fecha, color, multiplicador, creado_por) VALUES ('Día del Padre','2026-06-21','#81c784',1.4,'seed_185')",
        "INSERT OR IGNORE INTO marketing_eventos_calendario (evento, fecha, color, multiplicador, creado_por) VALUES ('Mitad de Año','2026-06-30','#4fc3f7',1.5,'seed_185')",
        "INSERT OR IGNORE INTO marketing_eventos_calendario (evento, fecha, color, multiplicador, creado_por) VALUES ('Amor y Amistad','2026-09-19','#ff8a65',2.2,'seed_185')",
        "INSERT OR IGNORE INTO marketing_eventos_calendario (evento, fecha, color, multiplicador, creado_por) VALUES ('Halloween','2026-10-31','#ff6f00',1.3,'seed_185')",
        "INSERT OR IGNORE INTO marketing_eventos_calendario (evento, fecha, color, multiplicador, creado_por) VALUES ('Black Friday','2026-11-27','#212121',3.5,'seed_185')",
        "INSERT OR IGNORE INTO marketing_eventos_calendario (evento, fecha, color, multiplicador, creado_por) VALUES ('Cyber Monday','2026-11-30','#1565c0',2.5,'seed_185')",
        "INSERT OR IGNORE INTO marketing_eventos_calendario (evento, fecha, color, multiplicador, creado_por) VALUES ('Navidad','2026-12-25','#c62828',2.8,'seed_185')",
        "INSERT OR IGNORE INTO marketing_eventos_calendario (evento, fecha, color, multiplicador, creado_por) VALUES ('Fin de Año / Rituales','2026-12-31','#6a1b9a',2.0,'seed_185')",
    ]),
    (185, "marketing_campanas.discount_code · atribución automática Shopify · Sebastián 26-may-2026 AM", [
        # FEATURE 26-may-2026 · Sebastián: "atribución con cupones único · resuelve
        # ROI y Score creadores · marketing decisional vs decorativo".
        #
        # Migración 32 ya creó `discount_code` en marketing_influencers y
        # `discount_codes` en animus_shopify_orders (JSON array de códigos usados
        # por orden). Faltaba el mismo campo en marketing_campanas para atribución
        # de campañas (no solo influencers). Convención del código:
        #   - Influencer: ANIMUS_<SLUG_NOMBRE><PCT>  (ej. ANIMUS_LAURA15)
        #   - Campaña:    ANIMUS_<SLUG_CAMP><PCT>    (ej. ANIMUS_DIAMADRE20)
        #
        # Atribución se calcula en SQL · LIKE '%<CODIGO>%' contra discount_codes
        # de cada orden Shopify. Si una orden usó 2 códigos (ej. cupón
        # influencer + cupón campaña), la venta se atribuye a AMBOS (multi-touch
        # default linear) · puedes desambiguar con el frontend si querés.
        "ALTER TABLE marketing_campanas ADD COLUMN discount_code TEXT DEFAULT ''",
        "CREATE INDEX IF NOT EXISTS idx_campana_discount_code ON marketing_campanas(discount_code)",
    ]),
    (184, "produccion_programada.envase_codigo_override · admin elige envase distinto al default por lote · Sebastián 25-may-2026 PM", [
        # FEATURE 25-may-2026 PM · Sebastián: "en calendario faltaría poder
        # agregarle el envase para empezar a calcular esas necesidades".
        # Hoy el cálculo MEE usa sku_mee_config (mapping global producto→envase).
        # Cuando un lote particular usa envase diferente al default (ej.
        # promo edición especial, faltan envases del default, etc.) no hay
        # forma de override. Este campo permite anular el default para
        # ESE lote sin tocar la config global · si está vacío, sigue el default.
        "ALTER TABLE produccion_programada ADD COLUMN envase_codigo_override TEXT DEFAULT ''",
    ]),
    (183, "pedidos_b2b_lote · plan_envasado_uds + plan_envasado_notas · Sebastián 25-may-2026 PM", [
        # FEATURE 25-may-2026 PM · Sebastián: "como ya estas primeras
        # producciones estan deberias colocar que yo mismo lo escriba,
        # y tenga algo como observaciones".
        # Hoy unidades_aporte se calcula automático (kg*1000/ml). Pero
        # admin quiere PODER SOBREESCRIBIR la cantidad real a envasar
        # por cliente (rendimiento real puede dar más o menos) +
        # observaciones libres por cliente para el operario envasador
        # (ej. "Fernando quiere etiqueta azul · revisar arte adjunto").
        "ALTER TABLE pedidos_b2b_lote ADD COLUMN plan_envasado_uds INTEGER DEFAULT 0",
        "ALTER TABLE pedidos_b2b_lote ADD COLUMN plan_envasado_notas TEXT DEFAULT ''",
    ]),
    (182, "pedidos_b2b.urgencia · campo de prioridad del cliente portal · Sebastián 25-may-2026 PM", [
        # FEATURE 25-may-2026 PM · Sebastián: "le pone la urgencia". Cliente
        # B2B logueado al portal tiene select alta/media/baja al solicitar.
        # Aparece en Necesidades planta para que se priorice. Default 'media'
        # permite seguir aceptando pedidos viejos sin migrar data.
        "ALTER TABLE pedidos_b2b ADD COLUMN urgencia TEXT DEFAULT 'media'",
    ]),
    (181, "mfa_tokens_usados · replay protection compartido cross-worker · Sebastián 25-may-2026", [
        # SEC-FIX 25-may-2026 · audit zero-error · Sebastián.
        # mfa.py _verify_totp tenía replay protection in-memory por worker
        # (dict _MFA_USED_TOKENS). Con 3 workers gunicorn, un MITM podía
        # gastar un token en worker 1 y replay en worker 2 dentro de la
        # ventana de ±90s. Ahora INSERT con UNIQUE(username, token_hash)
        # gana atomicidad cross-worker · cleanup oportunista al verify.
        """CREATE TABLE IF NOT EXISTS mfa_tokens_usados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            usado_at TEXT DEFAULT (datetime('now', 'utc')),
            UNIQUE(username, token_hash)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_mfa_tokens_cleanup ON mfa_tokens_usados(usado_at)",
    ]),
    (180, "portal_solicitudes · RFQ + muestras + ficha técnica del portal cliente B2B · Sebastián 25-may-2026", [
        # FEATURE 25-may-2026 · Tarea pendiente #4 "Módulo portal solicitud B2B".
        # Hoy el portal /portal/login tiene Pedidos (cliente existente) + PQR
        # (post-venta). Falta el flujo PRE-VENTA · cliente nuevo o existente
        # pide cotización antes de comprometer · admin responde con precio +
        # lead time + MOQ · cliente convierte a pedido o lo deja en histórico.
        # Cubre 3 tipos: cotización, muestras, ficha técnica.
        """CREATE TABLE IF NOT EXISTS portal_solicitudes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id TEXT,
            cliente_nombre TEXT NOT NULL,
            cliente_email TEXT,
            tipo TEXT NOT NULL DEFAULT 'cotizacion',
            producto_nombre TEXT NOT NULL,
            cantidad_estimada INTEGER DEFAULT 0,
            unidad TEXT DEFAULT 'unidades',
            envase_preferencia TEXT DEFAULT '',
            fecha_requerida TEXT,
            mensaje TEXT DEFAULT '',
            adjunto_filename TEXT DEFAULT '',
            estado TEXT NOT NULL DEFAULT 'nueva',
            respuesta_precio_cop REAL DEFAULT 0,
            respuesta_lead_time_dias INTEGER DEFAULT 0,
            respuesta_moq INTEGER DEFAULT 0,
            respuesta_validez_dias INTEGER DEFAULT 15,
            respuesta_notas TEXT DEFAULT '',
            respondido_por TEXT DEFAULT '',
            respondido_at TEXT,
            convertida_pedido_id INTEGER,
            creada_at TEXT DEFAULT (datetime('now', '-5 hours')),
            actualizada_at TEXT DEFAULT (datetime('now', '-5 hours'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_portal_sol_cliente ON portal_solicitudes(cliente_id, creada_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_portal_sol_estado ON portal_solicitudes(estado, creada_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_portal_sol_tipo ON portal_solicitudes(tipo)",
    ]),
    (179, "compras_fast_track_config · categorías que saltan a Autorizada sin doble paso · Sebastián 24-may-2026", [
        # FEATURE 24-may-2026 · Audit Solicitudes · Sebastián.
        # Antes: hardcoded en compras.py _FAST_TRACK = ('Influencer/Marketing Digital',
        # 'Cuenta de Cobro'). Otras categorías SIEMPRE crean OC en Borrador, requiriendo
        # autorizar 2 veces (aprobar SOL + autorizar OC). Para categorías de bajo monto
        # y rutina (Papelería, EPP, Aseo), Catalina quiere saltar directo a Autorizada
        # si el monto está por debajo de un threshold configurable. Tabla persiste la
        # config para que Sebastián la edite sin tocar código.
        """CREATE TABLE IF NOT EXISTS compras_fast_track_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT NOT NULL UNIQUE,
            monto_max_cop REAL DEFAULT 0,
            activo INTEGER DEFAULT 1,
            configurado_por TEXT DEFAULT '',
            configurado_at TEXT DEFAULT (datetime('now', '-5 hours')),
            notas TEXT DEFAULT ''
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ftc_cat ON compras_fast_track_config(categoria)",
        # Seeds defaults · refleja el comportamiento legacy + agrega rutina baja
        "INSERT INTO compras_fast_track_config (categoria, monto_max_cop, activo, configurado_por, notas) VALUES ('Influencer/Marketing Digital', 0, 1, 'mig179', 'Legacy fast-track · sin tope · monto_max_cop=0 = sin límite') ON CONFLICT(categoria) DO NOTHING",
        "INSERT INTO compras_fast_track_config (categoria, monto_max_cop, activo, configurado_por, notas) VALUES ('Cuenta de Cobro', 0, 1, 'mig179', 'Legacy fast-track · sin tope') ON CONFLICT(categoria) DO NOTHING",
    ]),
    (178, "produccion_eventos · timeline estructurada (reemplaza basura concatenada en observaciones) · Sebastián 24-may-2026 noche", [
        # FEATURE 24-may-2026 noche · Refactor pendiente del audit:
        # produccion_programada.observaciones se concatenaba con cada
        # operación (cancelación, ajuste kg, B2B sumado, etc.) acumulando
        # KB de basura. La mig 168 trunca a 1500 chars pero es paliativo.
        # Esta tabla almacena cada evento como una fila estructurada para
        # mostrar timeline limpio + audit trail nativo.
        """CREATE TABLE IF NOT EXISTS produccion_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produccion_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            detalles TEXT DEFAULT '',
            usuario TEXT DEFAULT '',
            fecha_at TEXT DEFAULT (datetime('now', '-5 hours'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_pev_prod ON produccion_eventos(produccion_id, fecha_at)",
        "CREATE INDEX IF NOT EXISTS idx_pev_tipo ON produccion_eventos(tipo)",
    ]),
    (177, "sku_producto_map.tono_label · etiqueta visible para sub-SKUs con tonos (BB101=ROSA, BB201=DURAZNO, etc.) · Sebastián 24-may-2026 noche", [
        # FEATURE 24-may-2026 noche · BLUSH BALM y LIP SERUM tienen multi-SKUs
        # que comparten el mismo bulk pero cambian el tono (color). Antes
        # solo se diferenciaban por el código SKU (BB101 vs BB201). Ahora
        # tono_label tiene etiqueta humana para mostrar en UI.
        "ALTER TABLE sku_producto_map ADD COLUMN tono_label TEXT DEFAULT ''",
    ]),
    (176, "produccion_programada.distribucion_resumen · etiqueta DTC+B2B legible · Sebastián 24-may-2026 noche", [
        # FEATURE 24-may-2026 noche · Sebastián: 'que salga aquí la
        # observación 1000 unidades para fernando mesa/kelly guerra · que
        # sea automático diciendo como queda distribuido el lote'.
        # Antes el lote tenía la info dispersa en observaciones (string
        # concatenado por cada operación). Ahora una columna dedicada que
        # se regenera al cambiar aportes B2B con el desglose limpio:
        # "DTC: 150 kg + Fernando Mesa: 350 kg + Kelly Guerra: 150 kg"
        "ALTER TABLE produccion_programada ADD COLUMN distribucion_resumen TEXT DEFAULT ''",
    ]),
    (175, "índice formula_items(producto_nombre) · perf Abastecimiento · Sebastián 24-may-2026 noche", [
        # AUDITORÍA Abastecimiento 24-may-2026 · agente reportó: JOIN
        # formula_headers↔formula_items por producto_nombre hace full
        # table scan de formula_items cada request. Gana ~45ms (30%
        # mejora con 365d de data).
        "CREATE INDEX IF NOT EXISTS idx_fi_producto ON formula_items(producto_nombre)",
    ]),
    (174, "formula_headers.producto_canonico + variante_label · fórmulas alternativas · Sebastián 24-may-2026 noche", [
        # FEATURE FÓRMULAS ALTERNATIVAS 24-may-2026 · Sebastián: "tenemos
        # PIB de dos orígenes Chino y de otro lado · realmente lo que
        # cambia es el PIB" (LIP SERUM puede formularse de 2 maneras).
        # Modelo: cada formula_headers sigue siendo 1 fila por producto_nombre
        # exacto (UNIQUE preservado para no romper queries existentes), pero
        # ahora se agrupa por `producto_canonico` (LIP SERUM agrupa "LIP
        # SERUM PIB CHINO" y "LIP SERUM PIB LOCAL"). El helper de selección
        # escoge la variante con menos déficit MP en tiempo real.
        # `variante_label` es etiqueta legible ("PIB CHINO" / "PIB LOCAL").
        # `prioridad` 0=auto-seleccionar por stock · 1+=preferir manual.
        "ALTER TABLE formula_headers ADD COLUMN producto_canonico TEXT DEFAULT ''",
        "ALTER TABLE formula_headers ADD COLUMN variante_label TEXT DEFAULT ''",
        "ALTER TABLE formula_headers ADD COLUMN prioridad INTEGER DEFAULT 0",
        # Seed: producto_canonico = producto_nombre para los existentes
        # (mantiene comportamiento default · 1 producto canónico = 1 fórmula).
        "UPDATE formula_headers SET producto_canonico = producto_nombre WHERE COALESCE(producto_canonico,'') = ''",
        "CREATE INDEX IF NOT EXISTS idx_formula_canonico ON formula_headers(producto_canonico)",
    ]),
    (173, "clientes_b2b_envases · whitelist cliente↔envase · Sebastián 24-may-2026 noche", [
        # FEATURE B2B 24-may-2026 · si NO existe whitelist para un cliente,
        # tiene acceso a TODOS los envases activos (default permisivo, no
        # rompe Fase 1). Si hay al menos 1 fila para el cliente, solo
        # esos envases son válidos para sus pedidos.
        # Permite que Fernando vea sus envases branded y NO el envase
        # premium de otro cliente. La regla "todos activos" para clientes
        # sin whitelist mantiene backward-compat (clientes existentes
        # siguen pidiendo lo mismo que antes).
        """CREATE TABLE IF NOT EXISTS clientes_b2b_envases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id TEXT NOT NULL,
            envase_codigo TEXT NOT NULL,
            envase_descripcion TEXT DEFAULT '',
            activo INTEGER NOT NULL DEFAULT 1,
            notas TEXT DEFAULT '',
            creado_at TEXT DEFAULT (datetime('now', '-5 hours')),
            UNIQUE(cliente_id, envase_codigo)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_cbe_cliente ON clientes_b2b_envases(cliente_id, activo)",
    ]),
    (172, "pedidos_b2b.envase_codigo · multi-envase MVP · Sebastián 24-may-2026 noche", [
        # FEATURE B2B MULTI-ENVASE 24-may-2026 · Sebastián: "lo único que
        # cambiaría es el envase". Mismo bulk LBHA va a 2 envases distintos
        # según cliente: Animus 250ml propio vs Fernando 250ml branded
        # (mismo formato, distinto sticker) o incluso 500ml personalizado.
        # MVP: el pedido lleva envase_codigo opcional (FK soft a maestro_mee)
        # · si null → asume envase default del producto (producto_presentaciones).
        "ALTER TABLE pedidos_b2b ADD COLUMN envase_codigo TEXT DEFAULT ''",
        "ALTER TABLE pedidos_b2b ADD COLUMN envase_notas TEXT DEFAULT ''",
    ]),
    (171, "pedidos_b2b_lote · link estructurado pedido B2B ↔ lote producción · Sebastián 24-may-2026 noche", [
        # FEATURE B2B 24-may-2026 · Sebastián: "Fernando maquila productos
        # que también vende Animus · ejemplo LBHA · si pide tantas unidades
        # la idea es que aumentamos producción para hacer todo junto · lo
        # único que cambiaría es el envase".
        # El modo HÍBRIDO actual (plan.py:283) suma kg al lote canónico y
        # anota en observaciones — pero query/UI no puede leer audit trail
        # estructurado. Esta tabla normaliza el link: cada pedido_b2b aporta
        # X kg a un lote específico · permite desglose DTC vs B2B por lote
        # + ver "qué pedidos cubre este lote" + (futuro) envase distinto.
        """CREATE TABLE IF NOT EXISTS pedidos_b2b_lote (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_b2b_id INTEGER NOT NULL,
            lote_produccion_id INTEGER NOT NULL,
            kg_aporte REAL NOT NULL DEFAULT 0,
            unidades_aporte INTEGER NOT NULL DEFAULT 0,
            ml_unidad REAL DEFAULT 0,
            envase_codigo TEXT DEFAULT '',
            modo TEXT NOT NULL DEFAULT 'sumado_a_lote_canonico'
                CHECK(modo IN ('sumado_a_lote_canonico','lote_dedicado')),
            cliente_nombre TEXT DEFAULT '',
            creado_at TEXT DEFAULT (datetime('now', '-5 hours')),
            UNIQUE(pedido_b2b_id, lote_produccion_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_pbl_lote ON pedidos_b2b_lote(lote_produccion_id)",
        "CREATE INDEX IF NOT EXISTS idx_pbl_pedido ON pedidos_b2b_lote(pedido_b2b_id)",
    ]),
    (170, "sku_producto_map.es_regalo · BBM mini es regalo + futuras promociones · Sebastián 24-may-2026 PM", [
        # FEATURE 24-may-2026 · Sebastián: "BBM mini es regalo no se vende,
        # el resto de BBM si los vendemos". Sin esta columna, BBM mini contaba
        # como velocidad de venta cuando en realidad es promo. Ahora:
        # es_regalo=1 → no cuenta para vel_30/60/90d ni urgencia.
        "ALTER TABLE sku_producto_map ADD COLUMN es_regalo INTEGER DEFAULT 0",
        # Seed conocidos · BBM mini (regalo · NO vendido)
        "UPDATE sku_producto_map SET es_regalo = 1 WHERE UPPER(sku) IN ('BBM', 'BBM-MINI', 'CH-RUBOR-MINI-PLT01')",
    ]),
    (169, "producto_perfil_riesgo.requiere_envasado_mismo_dia · reemplaza hard-code PRODUCTOS_COMPLEJOS · Sebastián 24-may-2026 PM", [
        # AUDITORÍA-FIX 24-may-2026 · agente reportó: lista hard-coded
        # PRODUCTOS_COMPLEJOS_SUBSTR = ("VITAMINA C", "TRIACTIVE") en plan.py
        # era inaccesible para edición. Ahora se mueve a producto_perfil_riesgo
        # como columna `requiere_envasado_mismo_dia`. La lista hard-coded
        # queda como fallback si la BD no tiene perfil del producto.
        "ALTER TABLE producto_perfil_riesgo ADD COLUMN requiere_envasado_mismo_dia INTEGER DEFAULT 0",
        # Seed inicial · marcar Vit C y Triactive como requieren envasado mismo día
        "UPDATE producto_perfil_riesgo SET requiere_envasado_mismo_dia = 1 WHERE UPPER(producto_nombre) LIKE '%VITAMINA C%' OR UPPER(producto_nombre) LIKE '%TRIACTIVE%'",
    ]),
    (168, "truncar produccion_programada.observaciones acumuladas >2000 chars · keep last 1500 · Sebastián 24-may-2026 PM", [
        # AUDITORÍA-FIX 24-may-2026 · agente reportó: 30+ updates concatenan
        # ' · OPERACIÓN_<timestamp>' en observaciones sin truncamiento.
        # Después de meses de crons, filas individuales tienen kilobytes
        # de basura. Esta mig limpia el histórico. Refactor futuro: tabla
        # produccion_programada_eventos (id, prod_id, evento, ts, usuario)
        # para audit trail estructurado sin strings infinitos.
        "UPDATE produccion_programada SET observaciones = '…(truncado por mig 168 · keep last 1500)… ' || SUBSTR(observaciones, -1500) WHERE LENGTH(COALESCE(observaciones,'')) > 2000",
    ]),
    (167, "mp_lead_time_config.n_recepciones · EWMA warm-up (n<3 usa media simple) · Sebastián 24-may-2026 PM", [
        # AUDITORÍA-FIX 24-may-2026 · agente reportó: el EWMA 0.7/0.3 se
        # aplicaba desde la 1ª muestra, lo que dejaba el lead_time en
        # 0.3*lead_real (porque el prior era NULL/default 14). 1 muestra
        # anómala movía el promedio 30%. Ahora n_recepciones cuenta el
        # número de aprendizajes · si n<3 → media simple acumulada · si
        # n>=3 → EWMA estándar.
        "ALTER TABLE mp_lead_time_config ADD COLUMN n_recepciones INTEGER DEFAULT 0",
    ]),
    (166, "animus_shopify_orders.tags + customer_tags · base filtro B2B vs DTC · Sebastián 23-may-2026 PM", [
        # SHOPIFY-AUDIT 23-may PM · agente reportó "no hay separación B2B
        # vs DTC en animus_shopify_orders · si la tienda Shopify recibe
        # un pedido mayorista, se cuenta como velocidad DTC". Solución:
        # guardar order.tags y customer.tags (Shopify ya los devuelve).
        # Filtro opt-in vía env var SHOPIFY_B2B_TAGS (CSV) · si el tag
        # del pedido o cliente está ahí, se excluye de velocidad DTC.
        "ALTER TABLE animus_shopify_orders ADD COLUMN tags TEXT DEFAULT ''",
        "ALTER TABLE animus_shopify_orders ADD COLUMN customer_tags TEXT DEFAULT ''",
        "CREATE INDEX IF NOT EXISTS idx_shopify_tags ON animus_shopify_orders(tags)",
    ]),
    (165, "bulk fix · TODOS los productos con lote_size_kg<1 → copiar de producto_canonico_config.kg_por_lote · Sebastián 23-may-2026 PM", [
        # Sebastián vio EMULSION LIMPIADORA mismo bug que AZH · BD tiene
        # lote_size_kg=0.1 absurdo. Mig 163 solo arregló AZH puntual.
        # Esta sincroniza TODOS los productos cuyo lote_size_kg sea
        # menor a 1 kg (claramente mal) copiando el kg_por_lote de
        # producto_canonico_config (donde Alejandro/Sebastián definieron
        # los valores reales del Excel). Solo aplica si el canonico tiene
        # valor sensato (>= 1 kg). Sintaxis compatible PG + SQLite via
        # correlated subquery (UPDATE FROM no funciona igual en SQLite).
        """UPDATE formula_headers
            SET lote_size_kg = (
                SELECT pcc.kg_por_lote
                  FROM producto_canonico_config pcc
                 WHERE UPPER(TRIM(pcc.producto_nombre)) = UPPER(TRIM(formula_headers.producto_nombre))
                   AND COALESCE(pcc.kg_por_lote, 0) >= 1
                 LIMIT 1),
                unidad_base_g = (
                SELECT pcc.kg_por_lote * 1000
                  FROM producto_canonico_config pcc
                 WHERE UPPER(TRIM(pcc.producto_nombre)) = UPPER(TRIM(formula_headers.producto_nombre))
                   AND COALESCE(pcc.kg_por_lote, 0) >= 1
                 LIMIT 1)
          WHERE COALESCE(lote_size_kg, 0) < 1
            AND EXISTS (
                SELECT 1 FROM producto_canonico_config pcc
                 WHERE UPPER(TRIM(pcc.producto_nombre)) = UPPER(TRIM(formula_headers.producto_nombre))
                   AND COALESCE(pcc.kg_por_lote, 0) >= 1)""",
    ]),
    (164, "sync producto_canonico_config.kg_por_lote para AZH (si tabla existe) · Sebastián 23-may-2026 PM", [
        # Agente auditor reportó: producto_canonico_config.kg_por_lote NO
        # se sincroniza con formula_headers.lote_size_kg · si AZH tiene 22
        # ahí, regenerar_canonicos sigue mal aunque arreglemos formula_headers.
        # Sync defensivo: si la tabla y la fila existen, actualizar a 33.
        """UPDATE producto_canonico_config SET kg_por_lote = 33
          WHERE UPPER(TRIM(producto_nombre)) = 'AZ HIBRID CLEAR'""",
    ]),
    (163, "FORZAR AZ HIBRID CLEAR lote_size_kg=33 (mig 161 puede haber quedado registrada sin aplicar UPDATE) · Sebastián 23-may-2026 PM", [
        # Agente auditor: mig 161 puede haber quedado en schema_migrations
        # pero su WHERE `lote_size_kg < 1` puede no haber matcheado por
        # cualquier razón · banner sigue mostrando "BD = 0.1 kg".
        # Mig 163 fuerza el UPDATE sin guard, idempotente si ya está en 33.
        """UPDATE formula_headers
            SET lote_size_kg = 33, unidad_base_g = 33000
          WHERE UPPER(TRIM(producto_nombre)) = 'AZ HIBRID CLEAR'
            AND COALESCE(lote_size_kg, 0) <> 33""",
    ]),
    (162, "limpieza AGRESIVA · cancela TODAS las Sugeridas futuras (incluida primera semana junio) · Sebastián 23-may-2026 PM", [
        # Sebastián 23-may-2026 PM · "me siguen apareciendo, son las azules"
        # · screenshot Junio 2026 muestra Sugeridas del 1-7 jun que tampoco
        # quiere (mig 161 solo borraba > 2026-06-07, dejaba 1-7 jun).
        # Esta limpieza es total: cancela TODAS las Sugeridas con fecha >=
        # hoy (2026-05-23). El usuario crea las nuevas manualmente desde
        # el botón 🤖 Programar · o el cron 5 AM las regenera con la
        # lógica nueva ya correcta (Fix #2-b lote_kg_efectivo).
        # NUNCA toca Fijo (eos_plan/b2b/retroactivo).
        # NUNCA toca lo ya descontado.
        """UPDATE produccion_programada
            SET estado = 'cancelado',
                observaciones = COALESCE(observaciones,'') || ' · cancelado limpieza total mig162'
          WHERE substr(fecha_programada,1,10) >= '2026-05-23'
            AND COALESCE(origen,'') IN ('eos_canonico','auto_plan','sugerido','manual','calendar')
            AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')
            AND fin_real_at IS NULL
            AND inventario_descontado_at IS NULL""",
    ]),
    (161, "limpiar Sugeridas > 2026-06-07 + fix AZH lote_size_kg=33 · Sebastián 23-may-2026 PM", [
        # Sebastián 23-may-2026 PM · "limpiarlo dejando lo que ya puse yo en
        # mayo y la primera semana de junio" + "AZ HIBRID CLEAR tenía lote
        # 0.1 kg en BD generando 23 lotes diarios". Como el usuario no pudo
        # ejecutar los endpoints vía consola/UI, lo hacemos via migración
        # idempotente. Se ejecuta UNA VEZ al primer arranque post-deploy.
        # NUNCA toca Fijo (eos_plan/b2b/retroactivo).
        # NUNCA toca lo ya descontado (fin_real_at o inventario_descontado_at).
        """UPDATE produccion_programada
            SET estado = 'cancelado',
                observaciones = COALESCE(observaciones,'') || ' · cancelado limpieza mig161 23-may-PM'
          WHERE substr(fecha_programada,1,10) > '2026-06-07'
            AND COALESCE(origen,'') IN ('eos_canonico','auto_plan','sugerido','manual','calendar')
            AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')
            AND fin_real_at IS NULL
            AND inventario_descontado_at IS NULL""",
        # Fix AZH lote_size_kg correcto · 33 kg (según mig 127)
        """UPDATE formula_headers
            SET lote_size_kg = 33, unidad_base_g = 33000
          WHERE UPPER(TRIM(producto_nombre)) = 'AZ HIBRID CLEAR'
            AND COALESCE(lote_size_kg, 0) < 1""",
    ]),
    (160, "clientes_b2b_maestro · tabla maestra para módulo solicitud B2B · Sebastián 23-may-2026", [
        # FIX #4 · auditoría · "cliente B2B" hasta hoy es derivado de
        # DISTINCT pedidos_b2b.cliente_id (TEXT libre sin FK) · cualquier
        # typo crea cliente nuevo silencioso · cliente sin pedidos no
        # aparece en Necesidades. Tabla maestra unifica el universo
        # de clientes y es base para el portal de solicitudes futuro.
        """CREATE TABLE IF NOT EXISTS clientes_b2b_maestro (
            cliente_id TEXT PRIMARY KEY,
            cliente_nombre TEXT NOT NULL,
            contacto TEXT DEFAULT '',
            telefono TEXT DEFAULT '',
            email TEXT DEFAULT '',
            activo INTEGER NOT NULL DEFAULT 1,
            tipo TEXT NOT NULL DEFAULT 'B2B'
                CHECK(tipo IN ('B2B','MAQUILA','INFLUENCER','OTRO')),
            notas TEXT DEFAULT '',
            creado_at_utc TEXT NOT NULL DEFAULT (datetime('now','utc')),
            actualizado_at_utc TEXT NOT NULL DEFAULT (datetime('now','utc'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_clientes_b2b_activo ON clientes_b2b_maestro(activo)",
        "CREATE INDEX IF NOT EXISTS idx_clientes_b2b_tipo ON clientes_b2b_maestro(tipo, activo)",
        # Backfill desde pedidos_b2b · upsert idempotente
        """INSERT OR IGNORE INTO clientes_b2b_maestro (cliente_id, cliente_nombre, tipo, activo)
           SELECT DISTINCT cliente_id, cliente_nombre, 'B2B', 1
             FROM pedidos_b2b
            WHERE cliente_id IS NOT NULL AND TRIM(cliente_id) != ''""",
    ]),
    (159, "OC Pagada+parcial flag separado · cierre flujo · Sebastián 23-may-2026", [
        # AUDITORÍA C17 · 23-may-2026 · OC pagada con anticipo + recepción
        # parcial quedaba en estado='Pagada' sin distinguir que aún falta
        # mercancía · ahora flag recepcion_parcial separado del estado
        # · valor 1 = aún falta mercancía · 0 = recepción completa
        "ALTER TABLE ordenes_compra ADD COLUMN recepcion_parcial INTEGER NOT NULL DEFAULT 0",
        "CREATE INDEX IF NOT EXISTS idx_oc_recepcion_parcial ON ordenes_compra(recepcion_parcial)",
    ]),
    (137, "PLAN DENSO MENSUAL · cada producto = 1 lote/mes × 12 meses · Sebastián 14-may-2026",
     _MIG_137_STMTS),
    (136, "PLAN LIMPIO · cancela TODO activo + genera solo eos_canonico · Sebastián 14-may-2026",
     _MIG_136_STMTS),
    (135, "Cancelar TODO Calendar/manual legacy · solo dejar eos_plan + eos_canonico · Sebastián 14-may-2026", [
        # Sebastián: "siguen apareciendo los canónicos legacy y eos,
        # debemos resolver eso, que solo aparezca lo que construí contigo
        # que es la realidad".
        #
        # Mig 134 solo cancela duplicados (≤21d). Pero los Calendar legacy
        # con fechas que NO chocan con eos_canonico sobreviven.
        # Mig 135 cancela TODO origen calendar/manual activo · solo deja:
        # - eos_plan (lo que Sebastián programó manualmente)
        # - eos_canonico (algoritmo nuevo)
        # - eos_retroactivo (historial · back-fills)
        # - completados / en_curso / cancelados (no se tocan)
        #
        # Idempotente · marca AUTO_LIMPIEZA_LEGACY_MIG135
        """UPDATE produccion_programada
           SET estado = 'cancelado',
               observaciones = COALESCE(observaciones,'') ||
                 ' · AUTO_LIMPIEZA_LEGACY_MIG135_' || datetime('now','-5 hours')
           WHERE origen IN ('calendar','manual')
             AND estado IN ('pendiente','programado','esperando_recurso')
             AND fin_real_at IS NULL
             AND inicio_real_at IS NULL
             AND COALESCE(observaciones,'') NOT LIKE '%AUTO_LIMPIEZA_LEGACY_MIG135%'""",
    ]),
    (134, "Auto-limpieza duplicados post-mig133 · Sebastián 14-may-2026", [
        # Sebastián: "ah entonces como solucionamos legacy y canonico
        # porque entonces me van a quedar programadas dos producciones
        # siempre". Mig 133 unificó nombres → ahora los duplicados son
        # visibles. Esta mig los cancela automáticamente.
        #
        # Regla: para cada producto, si hay 2+ lotes ACTIVOS con fechas
        # a ≤21 días entre sí, conservar el de MAYOR prioridad por origen:
        #   eos_plan > eos_canonico > calendar > manual
        # Si misma prioridad, conserva el de menor id (más viejo).
        #
        # NUNCA toca lotes con fin_real_at, inicio_real_at, o cancelados.
        # NUNCA toca eos_retroactivo (historial).
        # Idempotente · WHERE NOT LIKE marca.
        """UPDATE produccion_programada
           SET estado = 'cancelado',
               observaciones = COALESCE(observaciones,'') ||
                 ' · AUTO_DEDUP_MIG134_' || datetime('now','-5 hours')
           WHERE id IN (
             SELECT pp1.id
             FROM produccion_programada pp1
             JOIN produccion_programada pp2
               ON UPPER(TRIM(pp1.producto)) = UPPER(TRIM(pp2.producto))
              AND pp1.id != pp2.id
              AND ABS(julianday(pp1.fecha_programada) - julianday(pp2.fecha_programada)) <= 21
             WHERE pp1.estado IN ('pendiente','programado','esperando_recurso')
               AND pp1.fin_real_at IS NULL
               AND pp1.inicio_real_at IS NULL
               AND pp1.origen != 'eos_retroactivo'
               AND pp2.estado IN ('pendiente','programado','esperando_recurso','en_curso')
               AND pp2.fin_real_at IS NULL
               AND pp2.origen != 'eos_retroactivo'
               -- pp2 es PRIORITARIO sobre pp1 si:
               --   a) pp2 tiene mayor prioridad de origen (más bajo número), o
               --   b) misma prioridad pero pp2 tiene menor id
               AND (
                 CASE pp2.origen
                   WHEN 'eos_plan' THEN 0
                   WHEN 'eos_canonico' THEN 1
                   WHEN 'calendar' THEN 2
                   WHEN 'manual' THEN 3
                   ELSE 4
                 END <
                 CASE pp1.origen
                   WHEN 'eos_plan' THEN 0
                   WHEN 'eos_canonico' THEN 1
                   WHEN 'calendar' THEN 2
                   WHEN 'manual' THEN 3
                   ELSE 4
                 END
                 OR (
                   CASE pp2.origen
                     WHEN 'eos_plan' THEN 0
                     WHEN 'eos_canonico' THEN 1
                     WHEN 'calendar' THEN 2
                     WHEN 'manual' THEN 3
                     ELSE 4
                   END =
                   CASE pp1.origen
                     WHEN 'eos_plan' THEN 0
                     WHEN 'eos_canonico' THEN 1
                     WHEN 'calendar' THEN 2
                     WHEN 'manual' THEN 3
                     ELSE 4
                   END
                   AND pp2.id < pp1.id
                 )
               )
           )
           AND COALESCE(observaciones,'') NOT LIKE '%AUTO_DEDUP_MIG134%'""",
    ]),
    (133, "FIX URGENTE · sincronizar produccion_programada con nombres canónicos del Excel mig 127 · Sebastián 14-may-2026", [
        # Sebastián 14-may-2026: "en planta no salen ni materias primas".
        # Causa raíz: mig 127 importó fórmulas con nombres CANÓNICOS pero
        # produccion_programada tiene lotes legacy con nombres viejos.
        # El JOIN `UPPER(TRIM(fh.producto_nombre))=UPPER(TRIM(pp.producto))`
        # falla cuando los nombres difieren · planta ve "sin MPs".
        #
        # Fix: UPDATE produccion_programada SET producto = canónico
        # donde producto = legacy. Solo lotes NO completados (preserva
        # historial · audit trail).
        #
        # Mapeo extraído de SHEET_TO_BD en scripts/generate_mig_127_reimport.py
        """UPDATE produccion_programada SET producto = 'LIMPIADOR FACIAL HIDRATANTE'
           WHERE producto = 'Limpiador Hidratante' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'SUERO DE VITAMINA C+ FORMULA NUEVA'
           WHERE producto = 'Suero Vitamina C' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'SUERO DE NIACINAMIDA 5% FORMULA NUEVA'
           WHERE producto = 'Suero Niacinamida 5%' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'SUERO ANTIOXIDANTE RENOVA C10'
           WHERE producto = 'Suero Antioxidante Renova C' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'SUERO TRIACTIVE RETINOID NAD'
           WHERE producto = 'Suero Triactive Retinoid + NAD' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'CONTORNO DE OJOS RETINALDEHIDO 0.05%'
           WHERE producto IN ('Contorno de Ojos Retinaldehído',
                              'Contorno de Ojos Retinaldehído ')
             AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'ESENCIA DE CENTELLA ASIATICA'
           WHERE producto = 'Esencia Centella Asiática' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'EMULSION HIDRATANTE  B3+BHA'
           WHERE producto = 'Emulsión Hidratante B3 BHA' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'LIMPIADOR ILUMINADOR ACIDO KOJICO'
           WHERE producto IN ('Limpiador Iluminador Ácido Kójico',
                              'Limpiador Iluminador Ácido Kóji')
             AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'EMULSION LIMPIADORA'
           WHERE producto IN ('Emulsión Limpiadora','EMULSION LIMPIADORA NF')
             AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'GEL HIDRATANTE'
           WHERE producto IN ('Gel Hidratante','GEL HIDRATANTE NF')
             AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'LIMPIADOR FACIAL BHA 2%'
           WHERE producto = 'Limpiador Facial BHA 2%' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'MASCARILLA HIDRATANTE'
           WHERE producto = 'Mascarilla Hidratante' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'SUERO HIDRATANTE AH 1.5%'
           WHERE producto = 'Suero Hidratante AH 1.5%' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'SUERO ILUMINADOR TRX'
           WHERE producto = 'Suero Iluminador TRX' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'SUERO MULTIPEPTIDOS'
           WHERE producto = 'Suero Multipéptidos' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'SUERO EXFOLIANTE NOVA PHA'
           WHERE producto = 'Suero Exfoliante Nova PHA' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'AZ HIBRID CLEAR'
           WHERE producto = 'AZ Híbrid Clear' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'CONTORNO DE CAFEINA'
           WHERE producto = 'Contorno de Cafeína' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'CONTORNO DE OJOS MULTIPEPTIDOS'
           WHERE producto = 'Contorno de Ojos Multipéptidos' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'CREMA CORPORAL RENOVA BODY'
           WHERE producto = 'Crema Corporal Renova Body' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'BOOSTER TENSOR'
           WHERE producto = 'Booster Tensor' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'HYDRAPEPTIDE'
           WHERE producto = 'HydraPeptide' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'EMULSION HIDRATANTE ILUMINADORA'
           WHERE producto = 'Emulsión Hidratante Iluminadora' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'LIP SERUM VOLUMINIZADOR PEPTIDOS'
           WHERE producto IN ('Lip Sérum Voluminizador','LIP SERUM (PIB CHINO)')
             AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'BLUSH BALM'
           WHERE producto = 'Blush Balm' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'HYDRA BALANCE'
           WHERE producto = 'Hydra-Balance' AND fin_real_at IS NULL""",
        """UPDATE produccion_programada SET producto = 'Suero Exfoliante BHA 2%'
           WHERE producto = 'SUERO EXFOLIANTE BHA 2%' AND fin_real_at IS NULL""",
    ]),
    (132, "producto_canonico_config · tabla para frecuencias de canónicos · Sebastián 14-may-2026", [
        # Tabla para que Sebastián configure manualmente kg/lote, ml y
        # frecuencia_dias por producto. UI /admin/configurar-canonicos.
        """CREATE TABLE IF NOT EXISTS producto_canonico_config (
            producto_nombre TEXT PRIMARY KEY,
            kg_por_lote REAL DEFAULT 0,
            ml_unidad INTEGER DEFAULT 30,
            frecuencia_dias INTEGER DEFAULT 0,
            activo INTEGER DEFAULT 1,
            actualizado_at TEXT,
            actualizado_por TEXT,
            notas TEXT DEFAULT ''
        )""",
        """CREATE INDEX IF NOT EXISTS idx_canonico_config_activo
           ON producto_canonico_config(activo) WHERE activo = 1""",
    ]),
    (131, "Limpiar autoplan_decisiones viejas · forzar re-cálculo IA con fórmulas correctas · paso 1/6", [
        # Sebastián 14-may-2026: las decisiones IA previas fueron tomadas
        # con fórmulas incompletas (sin agua) y sin back-fills. Hay que
        # invalidar el cache para que próxima invocación re-piense todo
        # con datos correctos.
        # Marca las decisiones VIEJAS como obsoletas para que el cache 24h
        # no las reutilice. NO borra (preserva historial · IA aprende del feedback).
        """UPDATE autoplan_decisiones
           SET accion_usuario = 'obsoleta_mig131',
               accion_at = datetime('now','-5 hours'),
               comentario_usuario = 'Auto-marcada obsoleta · fórmulas viejas pre-mig127'
           WHERE accion_usuario IS NULL""",
    ]),
    (130, "Programar canónicos 12 meses con frecuencias Sebastián · paso 5/6",
     _MIG_130_STMTS),
    (129, "Cancelar Calendar legacy duplicado/obsoleto · Sebastián 14-may-2026", [
        # Sebastián 14-may-2026: paso 2/6 limpieza de programación.
        # Calendar legacy tiene lotes que YA pasaron sin ejecutar (Alejandro
        # nunca los marcó) y duplicados con eos_plan/eos_retroactivo.
        # Mig 129 cancela 2 categorías:
        #
        # A) Calendar/manual con fecha pasada > 14 días sin ejecutar
        #    (estado pendiente/programado · fin_real_at NULL · 14d para
        #    margen · si pasó >2 semanas y no se hizo, no se va a hacer)
        # B) Calendar/manual duplicado con producción ya completada (back-fill
        #    mig 128) del mismo producto en ventana ±21 días · si se hizo
        #    real el lote planificado de Calendar es obsoleto
        #
        # Idempotente: WHERE estado != 'cancelado' AND
        # observaciones NOT LIKE '%AUTOCLEAN_MIG129%'
        # NO toca lotes con fin_real_at o inicio_real_at (inmutabilidad).

        # ── A) Cancelar Calendar legacy >14 días pasado sin ejecutar ──
        """UPDATE produccion_programada
           SET estado = 'cancelado',
               observaciones = COALESCE(observaciones,'') ||
                 ' · AUTOCLEAN_MIG129_A · fecha pasada >14d sin ejecutar · ' ||
                 datetime('now','-5 hours')
           WHERE origen IN ('calendar','manual')
             AND estado IN ('pendiente','programado')
             AND fin_real_at IS NULL
             AND inicio_real_at IS NULL
             AND date(fecha_programada) < date('now','-5 hours','-14 day')
             AND COALESCE(observaciones,'') NOT LIKE '%AUTOCLEAN_MIG129%'""",

        # ── B) Cancelar Calendar legacy duplicado con back-fill reciente ──
        """UPDATE produccion_programada
           SET estado = 'cancelado',
               observaciones = COALESCE(observaciones,'') ||
                 ' · AUTOCLEAN_MIG129_B · duplicado con eos_retroactivo · ' ||
                 datetime('now','-5 hours')
           WHERE id IN (
             SELECT pp1.id
             FROM produccion_programada pp1
             JOIN produccion_programada pp2
               ON pp2.producto = pp1.producto
              AND pp2.id != pp1.id
              AND pp2.origen = 'eos_retroactivo'
              AND pp2.fin_real_at IS NOT NULL
              AND ABS(julianday(pp1.fecha_programada) - julianday(pp2.fecha_programada)) < 21
             WHERE pp1.origen IN ('calendar','manual')
               AND pp1.estado IN ('pendiente','programado')
               AND pp1.fin_real_at IS NULL
               AND pp1.inicio_real_at IS NULL
               AND COALESCE(pp1.observaciones,'') NOT LIKE '%AUTOCLEAN_MIG129%'
           )""",
    ]),
    (128, "Back-fill 13 producciones reales abril-mayo 2026 · Sebastián 14-may-2026", [
        # Sebastián 14-may-2026: registrar las producciones que Luis hizo
        # entre 15-abr y 13-may pero NO estaban en EOS con fin_real_at.
        # Con esto el sistema sabe que ya hay stock pipeline · evita
        # programar duplicados.
        #
        # Idempotente: WHERE NOT EXISTS con marcador único en observaciones.
        # Mapeo nombres del kardex viejo (NF / + / Cód mixto) a canónico
        # del Excel mig 127.
        #
        # Estado: completado · origen: eos_retroactivo (no descuenta MPs).
        """INSERT INTO produccion_programada
            (producto, fecha_programada, cantidad_kg, kg_real, estado, origen,
             fin_real_at, lotes, observaciones)
           SELECT 'LIP SERUM VOLUMINIZADOR PEPTIDOS', '2026-05-13', 12, 12,
                  'completado', 'eos_retroactivo',
                  '2026-05-13 20:07:00', 1, 'BACKFILL_MIG128_001 · Luis · LIP SERUM (PIB CHINO)'
           WHERE NOT EXISTS (
             SELECT 1 FROM produccion_programada
             WHERE observaciones LIKE '%BACKFILL_MIG128_001%')""",
        """INSERT INTO produccion_programada
            (producto, fecha_programada, cantidad_kg, kg_real, estado, origen,
             fin_real_at, lotes, observaciones)
           SELECT 'GEL HIDRATANTE', '2026-05-05', 34.228, 34.228,
                  'completado', 'eos_retroactivo',
                  '2026-05-05 17:56:00', 1, 'BACKFILL_MIG128_002 · Luis · GEL HIDRATANTE NF→GEL HIDRATANTE'
           WHERE NOT EXISTS (
             SELECT 1 FROM produccion_programada
             WHERE observaciones LIKE '%BACKFILL_MIG128_002%')""",
        """INSERT INTO produccion_programada
            (producto, fecha_programada, cantidad_kg, kg_real, estado, origen,
             fin_real_at, lotes, observaciones)
           SELECT 'GEL HIDRATANTE', '2026-04-30', 20.6, 20.6,
                  'completado', 'eos_retroactivo',
                  '2026-04-30 19:33:00', 1, 'BACKFILL_MIG128_003 · Luis · GEL HIDRATANTE NF→GEL HIDRATANTE'
           WHERE NOT EXISTS (
             SELECT 1 FROM produccion_programada
             WHERE observaciones LIKE '%BACKFILL_MIG128_003%')""",
        """INSERT INTO produccion_programada
            (producto, fecha_programada, cantidad_kg, kg_real, estado, origen,
             fin_real_at, lotes, observaciones)
           SELECT 'SUERO HIDRATANTE AH 1.5%', '2026-04-30', 90, 90,
                  'completado', 'eos_retroactivo',
                  '2026-04-30 18:34:00', 1, 'BACKFILL_MIG128_004 · Luis · SAH'
           WHERE NOT EXISTS (
             SELECT 1 FROM produccion_programada
             WHERE observaciones LIKE '%BACKFILL_MIG128_004%')""",
        """INSERT INTO produccion_programada
            (producto, fecha_programada, cantidad_kg, kg_real, estado, origen,
             fin_real_at, lotes, observaciones)
           SELECT 'LIMPIADOR FACIAL BHA 2%', '2026-04-28', 150, 150,
                  'completado', 'eos_retroactivo',
                  '2026-04-28 21:07:00', 1, 'BACKFILL_MIG128_005 · Luis · LIMP BHA 2%'
           WHERE NOT EXISTS (
             SELECT 1 FROM produccion_programada
             WHERE observaciones LIKE '%BACKFILL_MIG128_005%')""",
        """INSERT INTO produccion_programada
            (producto, fecha_programada, cantidad_kg, kg_real, estado, origen,
             fin_real_at, lotes, observaciones)
           SELECT 'CONTORNO DE OJOS RETINALDEHIDO 0.05%', '2026-04-23', 9, 9,
                  'completado', 'eos_retroactivo',
                  '2026-04-23 21:59:00', 1, 'BACKFILL_MIG128_006 · Luis · CONT RETINALDEHIDO'
           WHERE NOT EXISTS (
             SELECT 1 FROM produccion_programada
             WHERE observaciones LIKE '%BACKFILL_MIG128_006%')""",
        """INSERT INTO produccion_programada
            (producto, fecha_programada, cantidad_kg, kg_real, estado, origen,
             fin_real_at, lotes, observaciones)
           SELECT 'SUERO EXFOLIANTE NOVA PHA', '2026-04-23', 7, 7,
                  'completado', 'eos_retroactivo',
                  '2026-04-23 18:00:00', 1, 'BACKFILL_MIG128_007 · Luis · PHA'
           WHERE NOT EXISTS (
             SELECT 1 FROM produccion_programada
             WHERE observaciones LIKE '%BACKFILL_MIG128_007%')""",
        """INSERT INTO produccion_programada
            (producto, fecha_programada, cantidad_kg, kg_real, estado, origen,
             fin_real_at, lotes, observaciones)
           SELECT 'EMULSION LIMPIADORA', '2026-04-22', 20, 20,
                  'completado', 'eos_retroactivo',
                  '2026-04-22 21:46:00', 1, 'BACKFILL_MIG128_008 · Luis · EMUL LIMP NF→EMUL LIMPIADORA'
           WHERE NOT EXISTS (
             SELECT 1 FROM produccion_programada
             WHERE observaciones LIKE '%BACKFILL_MIG128_008%')""",
        """INSERT INTO produccion_programada
            (producto, fecha_programada, cantidad_kg, kg_real, estado, origen,
             fin_real_at, lotes, observaciones)
           SELECT 'LIP SERUM VOLUMINIZADOR PEPTIDOS', '2026-04-21', 2.323, 2.323,
                  'completado', 'eos_retroactivo',
                  '2026-04-21 14:20:00', 1, 'BACKFILL_MIG128_009 · Luis · LIP SERUM VOLUMINIZADOR'
           WHERE NOT EXISTS (
             SELECT 1 FROM produccion_programada
             WHERE observaciones LIKE '%BACKFILL_MIG128_009%')""",
        """INSERT INTO produccion_programada
            (producto, fecha_programada, cantidad_kg, kg_real, estado, origen,
             fin_real_at, lotes, observaciones)
           SELECT 'SUERO TRIACTIVE RETINOID NAD', '2026-04-17', 13, 13,
                  'completado', 'eos_retroactivo',
                  '2026-04-17 14:06:00', 1, 'BACKFILL_MIG128_010 · Luis · TRIACTIVE NAD'
           WHERE NOT EXISTS (
             SELECT 1 FROM produccion_programada
             WHERE observaciones LIKE '%BACKFILL_MIG128_010%')""",
        """INSERT INTO produccion_programada
            (producto, fecha_programada, cantidad_kg, kg_real, estado, origen,
             fin_real_at, lotes, observaciones)
           SELECT 'CONTORNO DE OJOS MULTIPEPTIDOS', '2026-04-16', 6, 6,
                  'completado', 'eos_retroactivo',
                  '2026-04-16 15:26:00', 1, 'BACKFILL_MIG128_011 · Luis · CONT MULTIPEPTIDOS'
           WHERE NOT EXISTS (
             SELECT 1 FROM produccion_programada
             WHERE observaciones LIKE '%BACKFILL_MIG128_011%')""",
        """INSERT INTO produccion_programada
            (producto, fecha_programada, cantidad_kg, kg_real, estado, origen,
             fin_real_at, lotes, observaciones)
           SELECT 'BLUSH BALM', '2026-04-15', 1, 1,
                  'completado', 'eos_retroactivo',
                  '2026-04-15 16:37:00', 1, 'BACKFILL_MIG128_012 · Luis · BLUSH BALM'
           WHERE NOT EXISTS (
             SELECT 1 FROM produccion_programada
             WHERE observaciones LIKE '%BACKFILL_MIG128_012%')""",
        """INSERT INTO produccion_programada
            (producto, fecha_programada, cantidad_kg, kg_real, estado, origen,
             fin_real_at, lotes, observaciones)
           SELECT 'LIMPIADOR ILUMINADOR ACIDO KOJICO', '2026-04-15', 40, 40,
                  'completado', 'eos_retroactivo',
                  '2026-04-15 03:53:00', 1, 'BACKFILL_MIG128_013 · Luis · LKJ'
           WHERE NOT EXISTS (
             SELECT 1 FROM produccion_programada
             WHERE observaciones LIKE '%BACKFILL_MIG128_013%')""",
    ]),
    (127, "Re-import COMPLETO Excel mayo-2026 · limpia residuos viejos · Sebastián 14-may-2026",
     _MIG_127_STMTS),
    (126, "Agregar AGUA DESIONIZADA a fórmulas (q.s.p.) · Sebastián 14-may-2026", [
        # Sebastián 14-may-2026: "las formulas deben estar perfectas para
        # que funcione · revisa eso del agua, el excel lo que tenemos en
        # la BD, y resuelvelo".
        #
        # Causa raíz: el Excel mig 121 lista solo activos (4-37% del lote)
        # sin el AGUA (60-95% del peso · q.s.p. quantum satis para).
        # Resultado: cobertura de fórmulas 4-60% · sistema no puede
        # calcular consumo real de agua ni descontar inventario correcto.
        #
        # Solución: asumir AGUA DESIONIZADA (MPAGUALI01) como ingrediente
        # implícito · cantidad = (lote_size_kg × 1000) - SUM(otros items).
        # Idempotente: solo agrega si NO existe ya.

        # Paso 0 · Asegurar que MPAGUALI01 existe en maestro_mps
        """INSERT OR IGNORE INTO maestro_mps
           (codigo_mp, nombre_comercial, nombre_inci, activo, stock_minimo, proveedor)
           VALUES ('MPAGUALI01', 'Agua Desionizada', 'AQUA', 1, 0, 'Planta')""",
        """UPDATE maestro_mps SET activo = 1
           WHERE codigo_mp = 'MPAGUALI01' AND COALESCE(activo, 0) = 0""",

        # Paso 1 · Para cada formula_headers ACTIVO, si NO tiene AGUA en
        # formula_items, agregar con cantidad = (lote_size_kg*1000) - suma_actual
        # Usa subquery · INSERT ... SELECT FROM ... WHERE NOT EXISTS
        """INSERT INTO formula_items
              (producto_nombre, material_id, material_nombre,
               porcentaje, cantidad_g_por_lote)
           SELECT
              fh.producto_nombre,
              'MPAGUALI01',
              'AGUA DESIONIZADA',
              ROUND(100.0 - COALESCE((
                SELECT SUM(porcentaje) FROM formula_items fi2
                WHERE fi2.producto_nombre = fh.producto_nombre
                  AND fi2.material_id != 'MPAGUALI01'
              ), 0), 4),
              ROUND(fh.lote_size_kg * 1000 - COALESCE((
                SELECT SUM(cantidad_g_por_lote) FROM formula_items fi3
                WHERE fi3.producto_nombre = fh.producto_nombre
                  AND fi3.material_id != 'MPAGUALI01'
              ), 0), 2)
           FROM formula_headers fh
           WHERE COALESCE(fh.activo, 1) = 1
             AND fh.lote_size_kg > 0
             AND NOT EXISTS (
               SELECT 1 FROM formula_items fi
               WHERE fi.producto_nombre = fh.producto_nombre
                 AND fi.material_id = 'MPAGUALI01'
             )
             AND (fh.lote_size_kg * 1000 - COALESCE((
               SELECT SUM(cantidad_g_por_lote) FROM formula_items fi4
               WHERE fi4.producto_nombre = fh.producto_nombre
             ), 0)) > 0""",
    ]),
    (125, "limpieza formula_items con cantidad_g_por_lote=0 + Blush Balm dup · Sebastián 14-may-2026", [
        # Sebastián 14-may-2026: durante análisis de necesidad anual de
        # Phenyl Trimethicone (MP00127), apareció que GEL HIDRATANTE NF
        # y BLUSH BALM tenían entradas en formula_items con
        # cantidad_g_por_lote=0 → distorsionaban el cálculo de necesidad
        # (aparecían como productos que usan la MP pero con 0g aportando
        # ruido). Decisión: borrar entradas vacías.
        #
        # IDEMPOTENTE · usa NOT EXISTS para no romper si ya se aplicó.
        # Audit: deja huella en tabla migrations_history (si existe).
        """DELETE FROM formula_items
           WHERE COALESCE(cantidad_g_por_lote, 0) = 0
             AND material_id = 'MP00127'
             AND producto_nombre IN ('GEL HIDRATANTE NF','BLUSH BALM','Blush Balm')""",

        # Unificar nombres "Blush Balm" (capitalizado) → "BLUSH BALM" (upper).
        # Sebastián 13-may-2026 mig 121 importó como "BLUSH BALM" pero
        # hay registros viejos como "Blush Balm". Mover formula_items y
        # producciones referenciando "Blush Balm" al canónico "BLUSH BALM"
        # solo si BLUSH BALM existe en formula_headers (para no perder fórmula).
        """UPDATE formula_items
           SET producto_nombre = 'BLUSH BALM'
           WHERE producto_nombre = 'Blush Balm'
             AND EXISTS (SELECT 1 FROM formula_headers
                         WHERE producto_nombre = 'BLUSH BALM')""",

        # Borrar formula_headers duplicado "Blush Balm" si "BLUSH BALM"
        # ya existe (idempotente).
        """DELETE FROM formula_headers
           WHERE producto_nombre = 'Blush Balm'
             AND EXISTS (SELECT 1 FROM formula_headers
                         WHERE producto_nombre = 'BLUSH BALM')""",

        # Deduplicar formula_items: si quedaron 2+ filas con mismo
        # (producto_nombre, material_id), dejar la que tiene MAYOR
        # cantidad_g_por_lote (porque cantidad>0 es la real · 0 es vacía).
        # Usa MAX por (cantidad DESC, id ASC) implícitamente con CTE.
        """DELETE FROM formula_items
           WHERE id IN (
             SELECT fi1.id
             FROM formula_items fi1
             JOIN formula_items fi2 ON fi1.producto_nombre = fi2.producto_nombre
                                    AND fi1.material_id = fi2.material_id
                                    AND fi1.id != fi2.id
             WHERE COALESCE(fi1.cantidad_g_por_lote, 0) < COALESCE(fi2.cantidad_g_por_lote, 0)
                OR (COALESCE(fi1.cantidad_g_por_lote, 0) = COALESCE(fi2.cantidad_g_por_lote, 0)
                    AND fi1.id > fi2.id)
           )""",
    ]),
    (124, "autoplan IA · tabla aprendizaje · Sebastián 14-may-2026", [
        # Sebastián: "podemos usar api kay de antropic para que lo haga,
        # ya sabemos las necesidades hay que ponerle reglas, exportan el
        # tamaño del producto, cuanto se vende al mes, y ver si se hace
        # para 30 dias 60 o 90 asi va aprendiendo".
        #
        # Cada decisión de autoplan se persiste con su contexto y la
        # acción real del usuario (aceptada / movida / cancelada) para
        # que la IA aprenda de feedback en futuras corridas.
        """CREATE TABLE IF NOT EXISTS autoplan_decisiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            producto_nombre TEXT NOT NULL,
            fecha_decision TEXT NOT NULL,
            horizonte_dias INTEGER NOT NULL,
            stock_kg REAL,
            velocidad_uds_mes INTEGER,
            ml_unidad INTEGER,
            lote_size_kg REAL,
            sugerencia_kg REAL,
            sugerencia_fecha TEXT,
            sugerencia_cobertura_dias INTEGER,
            motivo_ia TEXT,
            usuario TEXT,
            -- feedback usuario (NULL hasta que actúe)
            accion_usuario TEXT,
            accion_at TEXT,
            kg_real REAL,
            fecha_real TEXT,
            comentario_usuario TEXT,
            -- metadata
            modelo_ia TEXT,
            tokens_usados INTEGER,
            confianza_ia REAL,
            payload_completo TEXT
        )""",
        """CREATE INDEX IF NOT EXISTS idx_autoplan_cliente_fecha
           ON autoplan_decisiones(cliente, fecha_decision)""",
        """CREATE INDEX IF NOT EXISTS idx_autoplan_producto
           ON autoplan_decisiones(producto_nombre)""",
    ]),
    (123, "produccion_programada · motivo_pausa + estado esperando_recurso · Sebastián 13-may-2026", [
        # Sebastián: "coloquemos en plan en curso un boton pendiente
        # reprogramar o algo asi como que quede pendiente programarla
        # digamos algunas es por materia prima entonces debemos dejarla
        # pendiente hasta que llegue la materia prima".
        #
        # Diseño: estado='esperando_recurso' + motivo_pausa TEXT (razón
        # libre). NO se borra la fecha · queda como referencia de cuándo
        # estaba originalmente programada. Cuando llega el recurso →
        # endpoint /reactivar pone estado='programado' + nueva_fecha.
        "ALTER TABLE produccion_programada ADD COLUMN motivo_pausa TEXT DEFAULT NULL",
        "ALTER TABLE produccion_programada ADD COLUMN pausado_at TEXT DEFAULT NULL",
        "ALTER TABLE produccion_programada ADD COLUMN pausado_por TEXT DEFAULT NULL",
        # Index para listar pausadas rápido
        """CREATE INDEX IF NOT EXISTS idx_pp_estado_pausa
           ON produccion_programada(estado, motivo_pausa)
           WHERE estado='esperando_recurso'""",
    ]),
    (122, "Mapeo SKU Shopify · Triactive Retinoid + Gel Hidratante · Sebastián 13-may-2026", [
        # Sebastián 13-may-2026: estos productos aparecían SIN_VENTAS en
        # Necesidades porque sus SKUs Shopify no estaban en sku_producto_map.
        # SKUs extraídos de animuslb.com/products.json (mayo-2026).
        # Booster Tensor pendiente · NO aparece en products.json público
        # (canal B2B o draft) · Sebastián confirma.
        """INSERT OR IGNORE INTO sku_producto_map (sku, producto_nombre, activo) VALUES
            ('TRIAC',    'SUERO TRIACTIVE RETINOID NAD', 1),
            ('TRIAC30',  'SUERO TRIACTIVE RETINOID NAD', 1),
            ('GELH',     'GEL HIDRATANTE',                1)""",
        # Si los SKUs ya existían pero con producto_nombre vacío o distinto,
        # actualizar y reactivar
        """UPDATE sku_producto_map SET producto_nombre = 'SUERO TRIACTIVE RETINOID NAD', activo = 1
           WHERE sku IN ('TRIAC', 'TRIAC30')""",
        """UPDATE sku_producto_map SET producto_nombre = 'GEL HIDRATANTE', activo = 1
           WHERE sku = 'GELH'""",
    ]),
    (121, "Importar 26 fórmulas reales del Excel Alejandro mayo-2026 · Sebastián 13-may-2026",
     _MIG_121_STMTS),
    (120, "Reactivar 5 MPs inactivas usadas en Excel Alejandro mayo-2026 · Sebastián 13-may-2026", [
        # Verificador /admin/verificar-codigos-mp 13-may-2026: de los 146
        # códigos del Excel FORMULAS_MAESTRO_v2_1 Alejandro, 141 estaban
        # activos · 5 inactivos · 0 faltantes. Reactivar los 5 para que
        # el trigger mig 98 permita los nuevos formula_items.
        #
        # MP00181 y MP00176 ambos son "Centella asiática" · ambos siguen
        # usándose en fórmulas del Excel (Esencia Centella + Suero
        # Multipéptidos respectivamente, según las hojas).
        """UPDATE maestro_mps SET activo = 1
           WHERE codigo_mp IN (
             'MP00111',  -- Puresil ORG01 · C13-15 ALCANO
             'MP00176',  -- Triterpenos de centella asiática 80%
             'MP00181',  -- extracto de Centella asiática
             'MP00236',  -- Pantenol en polvo
             'MP00297'   -- Hidróxido de sodio sol.
           )""",
    ]),
    (119, "pedidos_b2b · necesidades B2B (Fernando + futuros) · Sebastián 13-may-2026", [
        # Sprint 2A · Plan v3 · Sebastián 13-may-2026: cada cliente B2B
        # tiene sus pedidos pendientes que se suman a las necesidades de
        # Animus DTC para generar el plan de producción consolidado.
        #
        # Hoy solo Fernando Mesa (CLI-002). Cuando lleguen más B2B, simplemente
        # se agregan filas con cliente_id distinto · misma tabla escalable.
        #
        # Workflow:
        #   pendiente     → cliente solicitó (manual hoy · portal futuro)
        #   confirmado    → Sebastián cuadró cantidad y fecha
        #   en_produccion → ya está agendado en Calendar
        #   despachado    → entregado al cliente · estado terminal
        #   cancelado     → no se produce · estado terminal
        """CREATE TABLE IF NOT EXISTS pedidos_b2b (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id TEXT NOT NULL,
            cliente_nombre TEXT NOT NULL,
            producto_nombre TEXT NOT NULL,
            cantidad_uds INTEGER NOT NULL,
            ml_unidad REAL NOT NULL DEFAULT 30,
            fecha_estimada TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente'
                CHECK(estado IN ('pendiente','confirmado','en_produccion','despachado','cancelado')),
            notas TEXT DEFAULT '',
            creado_por TEXT NOT NULL,
            creado_at_utc TEXT NOT NULL DEFAULT (datetime('now','utc')),
            actualizado_at_utc TEXT NOT NULL DEFAULT (datetime('now','utc'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_pedidos_b2b_cliente ON pedidos_b2b(cliente_id, estado)",
        "CREATE INDEX IF NOT EXISTS idx_pedidos_b2b_estado ON pedidos_b2b(estado, fecha_estimada)",
        "CREATE INDEX IF NOT EXISTS idx_pedidos_b2b_producto ON pedidos_b2b(producto_nombre, estado)",
        # Trigger actualizado_at_utc fresh en cada UPDATE
        """CREATE TRIGGER IF NOT EXISTS trg_pedidos_b2b_updated
           AFTER UPDATE ON pedidos_b2b
           FOR EACH ROW
           WHEN OLD.actualizado_at_utc = NEW.actualizado_at_utc
           BEGIN
               UPDATE pedidos_b2b SET actualizado_at_utc = datetime('now','utc')
               WHERE id = NEW.id;
           END""",
    ]),
    (118, "Activar productos Animus + presentaciones 10ml/15ml · Sebastián 13-may-2026", [
        # Sebastián 13-may-2026: definimos el modelo de "productos hermanos"
        # de Animus que comparten producción (mismo bulk genera presentación
        # principal + 10ml regalo/venta + 15ml en algunos).
        #
        # Datos confirmados por Sebastián vía chat:
        #   · SAH (Suero Hidratante AH 1.5%): 1200 uds 10ml regalo por lote
        #   · TRX (Suero Iluminador TRX): 1200 uds 10ml regalo por lote
        #   · PHA (Nova PHA): 200 uds 10ml de VENTA por lote
        #   · AZ HIBRID CLEAR: presentación 15ml también (uds TBD)
        #   · "renova" y "triactive" 15ml pendiente confirmar nombres BD
        #
        # Inactivos confirmados (no producir más):
        #   · SUERO DE RETINALDEHIDO 0.05%
        #   · Suero RETINAL +
        #   · SUERO ILUMINADOR AHA+AH.
        #   · EMULSION HIDRATANTE  B3+BHA (reemplazada por nueva)

        # Columna activo · DEFAULT 1 · permite desactivar productos sin borrar
        "ALTER TABLE formula_headers ADD COLUMN activo INTEGER NOT NULL DEFAULT 1",

        # Columnas variants · 10ml y 15ml por lote bulk
        # uds_*_por_lote = unidades que salen de cada producción del bulk
        # tipo_10ml: 'regalo' (no vende, demanda fija por producción) o
        #            'venta' (vende como SKU separado en Shopify)
        "ALTER TABLE formula_headers ADD COLUMN tiene_10ml INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE formula_headers ADD COLUMN uds_10ml_por_lote INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE formula_headers ADD COLUMN tipo_10ml TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE formula_headers ADD COLUMN tiene_15ml INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE formula_headers ADD COLUMN uds_15ml_por_lote INTEGER NOT NULL DEFAULT 0",

        # Marcar inactivos
        """UPDATE formula_headers SET activo=0
           WHERE producto_nombre IN (
             'SUERO DE RETINALDEHIDO 0.05%',
             'Suero RETINAL +',
             'SUERO ILUMINADOR AHA+AH.',
             'EMULSION HIDRATANTE  B3+BHA'
           )""",

        # Seed codigo_pt + variant info para productos confirmados
        """UPDATE formula_headers
           SET codigo_pt='SAH', tiene_10ml=1, uds_10ml_por_lote=1200, tipo_10ml='regalo'
           WHERE producto_nombre='SUERO HIDRATANTE AH 1.5%'""",
        """UPDATE formula_headers
           SET codigo_pt='TRX', tiene_10ml=1, uds_10ml_por_lote=1200, tipo_10ml='regalo'
           WHERE producto_nombre='SUERO ILUMINADOR TRX'""",
        """UPDATE formula_headers
           SET codigo_pt='PHA', tiene_10ml=1, uds_10ml_por_lote=200, tipo_10ml='venta'
           WHERE producto_nombre='SUERO EXFOLIANTE NOVA PHA'""",
        """UPDATE formula_headers
           SET codigo_pt='AZH', tiene_15ml=1
           WHERE producto_nombre='AZ HIBRID CLEAR'""",
    ]),
    (117, "codigo_pt + numero_op + zona · MyBatch compat · Sebastián 13-may-2026", [
        # Pieza mínima de Bloque B2 del PLAN_VERTICAL_2026. Tres conceptos
        # que MyBatch (sistema legacy a reemplazar) usa y que necesitamos
        # poder ingerir + emitir para compat de vista. Ver
        # `docs/PLAN_VERTICAL_2026.md` Bloque B2.
        #
        # === codigo_pt en formula_headers ===
        # Identificador corto de producto terminado que MyBatch usa en la
        # nomenclatura de OPs y etiquetas. Manual seed por Calidad (Daniela)
        # — NULL aceptado hasta que se asigne. Único cuando set (índice
        # parcial WHERE codigo_pt IS NOT NULL para permitir varios NULL).
        "ALTER TABLE formula_headers ADD COLUMN codigo_pt TEXT DEFAULT NULL",
        """CREATE UNIQUE INDEX IF NOT EXISTS idx_fh_codigo_pt
           ON formula_headers(codigo_pt) WHERE codigo_pt IS NOT NULL""",

        # === numero_op en ebr_ejecuciones ===
        # Identificador secuencial anual MyBatch-compat. Format 'OP-YYYY-NNNN'
        # (4 dígitos zero-padded). Auto-asignado en hook al crear EBR via
        # tabla op_counters (atómico bajo WAL · ver brd.assign_numero_op).
        # Legacy NULL: EBRs anteriores a esta mig se quedan sin numero_op
        # (ya no se asigna retroactivo · evita pisar lotes Blush Balm seed).
        "ALTER TABLE ebr_ejecuciones ADD COLUMN numero_op TEXT DEFAULT NULL",
        """CREATE UNIQUE INDEX IF NOT EXISTS idx_ebr_numero_op
           ON ebr_ejecuciones(numero_op) WHERE numero_op IS NOT NULL""",

        # op_counters: contador atómico por año. Una fila por año, counter
        # arranca en 0 y sube +1 con cada EBR creado. SQLite WAL serializa
        # writes · safe ante races concurrentes (worker A y B no pueden
        # UPDATE simultáneo). Reset implícito en año nuevo: nueva fila
        # (INSERT OR IGNORE) con counter=0.
        """CREATE TABLE IF NOT EXISTS op_counters (
            year INTEGER PRIMARY KEY,
            counter INTEGER NOT NULL DEFAULT 0,
            updated_at_utc TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
        )""",

        # === zona en areas_planta ===
        # Clasificación regulatoria INVIMA (mapea a Cosmetics GMP zonas):
        #   'limpia'      → manufactura crítica (aséptica, baja carga
        #                   microbiana) · no aplica hoy en HHA pero queda
        #                   en el enum para futuros productos.
        #   'controlada'  → manufactura cosmética estándar (PROD/FAB/ENV/
        #                   DISP) · el grueso de las áreas HHA.
        #   'general'     → almacenamiento, oficinas, áreas no productivas.
        #   'restringida' → acceso limitado (QC, archivos regulatorios).
        # NOT NULL DEFAULT 'general' · filas existentes arrancan en general
        # y se reclasifican abajo según codigo.
        "ALTER TABLE areas_planta ADD COLUMN zona TEXT NOT NULL DEFAULT 'general'",
        # Reclasificación de las áreas conocidas (ver project_planta_crew_areas.md
        # y el seed de migs 55/58). Las salas de fabricación/envasado/dispensación
        # son CONTROLADAS porque tienen requisitos GMP de limpieza,
        # cross-contamination control, gowning. ESC1 (escaleras) y ACOND
        # (acondicionamiento post-envasado) se quedan general porque ya
        # no manipulan bulk.
        "UPDATE areas_planta SET zona='controlada' WHERE codigo IN ('PROD1','PROD2','PROD3','PROD4','FAB1','FAB2','FAB3','ENV1','ENV2','DISP','LAV')",
        "UPDATE areas_planta SET zona='general'    WHERE codigo IN ('ACOND','ALMP','ALMPT','ESC1')",
    ]),
    (116, "produccion_programada · kg_real + unidades_real + merma_pct · Planta Mejora A · Sebastián 12-may-2026", [
        # Sebastián pidió "planta puede tener cosas" como prioridad. El primer
        # dolor detectado: hoy NO se captura cuántos kg/unidades salieron al
        # terminar producción. Sin eso, cero data de yield/merma a nivel
        # operativo (el BRD/EBR sí lo tiene pero solo para producciones con
        # MBR aprobado · la mayoría siguen sin EBR).
        #
        # Columnas opcionales · NO bloquean el flujo de terminar (operario
        # puede saltarlo en versión inicial · UI lo recordará). Si se reportan,
        # el sistema calcula merma_pct = (1 - kg_real/cantidad_kg) * 100.
        "ALTER TABLE produccion_programada ADD COLUMN kg_real REAL DEFAULT NULL",
        "ALTER TABLE produccion_programada ADD COLUMN unidades_real INTEGER DEFAULT NULL",
        "ALTER TABLE produccion_programada ADD COLUMN merma_pct REAL DEFAULT NULL",
        # Índice para reportes agrupados por mes
        "CREATE INDEX IF NOT EXISTS idx_pp_fin_real ON produccion_programada(fin_real_at, producto) WHERE fin_real_at IS NOT NULL",
    ]),
    (115, "MBR auto-seed · drafts para todos los productos en formula_headers · Sebastián 12-may-2026", [
        # Para cada producto en formula_headers que TODAVÍA no tiene MBR,
        # crear un MBR draft con 3 pasos genéricos (dispensación / fabricación
        # / envasado). Calidad después ajusta los detalles específicos por
        # producto antes de submit a revisión.
        #
        # Condición NOT EXISTS evita duplicar Blush Balm (ya creado por mig 110)
        # y permite re-correr la migración después de agregar nuevos productos
        # a formula_headers (idempotente).
        """INSERT OR IGNORE INTO mbr_templates
             (producto_nombre, version, estado, titulo, descripcion,
              lote_size_g, tiempo_total_estimado_min, creado_por)
           SELECT
             fh.producto_nombre,
             1,
             'draft',
             fh.producto_nombre || ' · MBR v1 (auto-seed)',
             'Procedimiento auto-generado desde formula_headers. '
              || 'PENDIENTE: Calidad debe ajustar pasos específicos antes '
              || 'de submit a revisión. ' || COALESCE(fh.descripcion, ''),
             COALESCE(fh.unidad_base_g, 1000.0),
             270,
             'system-seed'
           FROM formula_headers fh
           WHERE NOT EXISTS (
             SELECT 1 FROM mbr_templates m
             WHERE m.producto_nombre = fh.producto_nombre
           )""",

        # Paso 1: dispensación (con e-sign · pesaje crítico)
        """INSERT INTO mbr_pasos
             (mbr_template_id, orden, fase, descripcion, tipo_paso,
              equipo_requerido, tiempo_estimado_min, requiere_e_sign,
              requiere_qc, notas)
           SELECT m.id, 1, 'dispensacion',
                  'Pesar y dispensar las MPs según fórmula maestra',
                  'dispensacion', 'BAL01,DISP', 60, 1, 0,
                  'Verificar lote y vencimiento de cada MP. Mayerlin · dispensación.'
           FROM mbr_templates m
           WHERE m.creado_por = 'system-seed'
             AND m.estado = 'draft'
             AND NOT EXISTS (SELECT 1 FROM mbr_pasos p WHERE p.mbr_template_id = m.id)""",

        # Paso 2: fabricación (genérico · Calidad detalla)
        """INSERT INTO mbr_pasos
             (mbr_template_id, orden, fase, descripcion, tipo_paso,
              equipo_requerido, tiempo_estimado_min, requiere_e_sign,
              requiere_qc, notas)
           SELECT m.id, 2, 'fabricacion',
                  'Fabricar el producto siguiendo procedimiento aprobado · '
                  || 'PENDIENTE: Calidad debe completar parámetros específicos '
                  || '(temperatura, tiempo de mezclado, secuencia de adición)',
                  'mezclado', 'TQ01', 120, 0, 0, ''
           FROM mbr_templates m
           WHERE m.creado_por = 'system-seed'
             AND m.estado = 'draft'
             AND (SELECT COUNT(*) FROM mbr_pasos p WHERE p.mbr_template_id = m.id) = 1""",

        # Paso 3: envasado (con QC firma)
        """INSERT INTO mbr_pasos
             (mbr_template_id, orden, fase, descripcion, tipo_paso,
              equipo_requerido, tiempo_estimado_min, requiere_e_sign,
              requiere_qc, notas)
           SELECT m.id, 3, 'envasado',
                  'Envasar producto y etiquetar · QC firma liberación',
                  'envasado', 'ENV1', 90, 0, 1,
                  'Verificar etiquetado, cierre, hermeticidad. QC inspección visual.'
           FROM mbr_templates m
           WHERE m.creado_por = 'system-seed'
             AND m.estado = 'draft'
             AND (SELECT COUNT(*) FROM mbr_pasos p WHERE p.mbr_template_id = m.id) = 2""",
    ]),
    (114, "ebr_pesajes · reconciliación granular MP teórico vs real · Fase 1 F7 · Sebastián 12-may-2026", [
        # Cada pesaje individual del operario durante un paso de dispensación.
        # Permite reconciliación MP-por-MP entre lo que la fórmula PEDÍA
        # (formula_items.porcentaje × cantidad_objetivo_g) y lo que realmente
        # se pesó. delta_g y delta_pct se calculan en el endpoint al insertar.
        # lote_mp captura el lote real del kardex usado (auditabilidad de lote
        # de origen → lote de producto terminado).
        """CREATE TABLE IF NOT EXISTS ebr_pesajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ebr_id INTEGER NOT NULL,
            ebr_paso_id INTEGER DEFAULT NULL,
            material_id TEXT NOT NULL,
            material_nombre TEXT DEFAULT '',
            cantidad_teorica_g REAL NOT NULL,
            cantidad_real_g REAL NOT NULL,
            delta_g REAL,
            delta_pct REAL,
            lote_mp TEXT DEFAULT '',
            pesado_por TEXT NOT NULL,
            pesado_at_utc TEXT NOT NULL,
            e_sign_id INTEGER DEFAULT NULL,
            notas TEXT DEFAULT '',
            FOREIGN KEY (ebr_id) REFERENCES ebr_ejecuciones(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_pesajes_ebr ON ebr_pesajes(ebr_id, material_id)",
        "CREATE INDEX IF NOT EXISTS idx_pesajes_lote_mp ON ebr_pesajes(lote_mp) WHERE lote_mp != ''",

        # Inmutabilidad post-liberación del EBR (igual lógica que ebr_pasos).
        """CREATE TRIGGER IF NOT EXISTS trg_pesajes_no_edit_liberado
           BEFORE UPDATE ON ebr_pesajes
           FOR EACH ROW
           WHEN EXISTS (SELECT 1 FROM ebr_ejecuciones
                        WHERE id = NEW.ebr_id AND estado IN ('liberado','rechazado'))
           BEGIN
               SELECT RAISE(ABORT, 'pesajes de EBR liberado/rechazado son inmutables');
           END""",
        """CREATE TRIGGER IF NOT EXISTS trg_pesajes_no_delete_liberado
           BEFORE DELETE ON ebr_pesajes
           FOR EACH ROW
           WHEN EXISTS (SELECT 1 FROM ebr_ejecuciones
                        WHERE id = OLD.ebr_id AND estado IN ('liberado','rechazado'))
           BEGIN
               SELECT RAISE(ABORT, 'pesajes de EBR liberado/rechazado son inmutables · DELETE prohibido');
           END""",
    ]),
    (113, "equipo_limpieza_log · cleaning records por equipo · Fase 1 BRD · Sebastián 12-may-2026", [
        # GMP requiere demostrar que cada equipo está limpio antes de un nuevo
        # lote (especialmente cambio de producto). Si auditor pregunta "cómo
        # sabe que TQ01 no contaminó el lote N con residuos del N-1", la
        # respuesta es este log: limpieza con timestamp + operario + QC visual.
        #
        # tipo_limpieza:
        #   rutinaria         → entre lotes del mismo producto.
        #   profunda          → mensual / programada (ya existe limpieza_profunda_calendario).
        #   cambio_producto   → al fabricar un producto distinto (mayor riesgo).
        #
        # visual_ok=1 lo setea QC al firmar inspección visual. Solo entonces
        # el equipo se considera apto para próximo uso.
        """CREATE TABLE IF NOT EXISTS equipo_limpieza_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_codigo TEXT NOT NULL,
            lote_anterior TEXT DEFAULT '',
            lote_siguiente TEXT DEFAULT '',
            tipo_limpieza TEXT NOT NULL DEFAULT 'rutinaria',
            operario_username TEXT NOT NULL,
            operario_e_sign_id INTEGER DEFAULT NULL,
            qc_username TEXT DEFAULT '',
            qc_e_sign_id INTEGER DEFAULT NULL,
            visual_ok INTEGER DEFAULT NULL,
            iniciado_at_utc TEXT NOT NULL,
            completado_at_utc TEXT DEFAULT NULL,
            observaciones TEXT DEFAULT ''
        )""",
        "CREATE INDEX IF NOT EXISTS idx_limpieza_equipo ON equipo_limpieza_log(equipo_codigo, completado_at_utc DESC)",
        "CREATE INDEX IF NOT EXISTS idx_limpieza_lote_sig ON equipo_limpieza_log(lote_siguiente) WHERE lote_siguiente != ''",

        # Inmutabilidad post-validación QC: una vez visual_ok seteado y QC
        # firmó, el log no se modifica. Si hubo error, abrir desviación
        # nueva, no editar el record.
        """CREATE TRIGGER IF NOT EXISTS trg_limpieza_no_edit_qc
           BEFORE UPDATE ON equipo_limpieza_log
           FOR EACH ROW
           WHEN OLD.qc_e_sign_id IS NOT NULL
                AND (NEW.visual_ok IS NOT OLD.visual_ok
                  OR NEW.qc_e_sign_id IS NOT OLD.qc_e_sign_id
                  OR NEW.completado_at_utc IS NOT OLD.completado_at_utc
                  OR NEW.equipo_codigo IS NOT OLD.equipo_codigo)
           BEGIN
               SELECT RAISE(ABORT, 'cleaning log validado por QC es inmutable');
           END""",
    ]),
    (112, "IPCs · In-Process Controls · specs (MBR) + resultados (EBR) · Fase 1 BRD · Sebastián 12-may-2026", [
        # ipc_specs: parámetros de control (pH, viscosidad, T°, apariencia, etc.)
        # asociados a un MBR. Pueden estar atados a un paso específico o ser
        # globales del MBR (mbr_paso_id NULL = aplica al cierre, no a un paso).
        # valor_min y valor_max son rangos de aceptación. Si min y max son NULL,
        # el parámetro es cualitativo (se mide vía valor_texto).
        # obligatorio=1: si no se reporta o NO conforme, bloquea completar EBR.
        """CREATE TABLE IF NOT EXISTS ipc_specs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mbr_template_id INTEGER NOT NULL,
            mbr_paso_id INTEGER DEFAULT NULL,
            parametro TEXT NOT NULL,
            unidad TEXT NOT NULL DEFAULT '',
            valor_min REAL DEFAULT NULL,
            valor_max REAL DEFAULT NULL,
            metodo TEXT DEFAULT '',
            obligatorio INTEGER DEFAULT 1,
            notas TEXT DEFAULT '',
            FOREIGN KEY (mbr_template_id) REFERENCES mbr_templates(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ipcspec_mbr ON ipc_specs(mbr_template_id, parametro)",
        # Inmutabilidad: especs son editables solo mientras el MBR está en draft.
        # Si el MBR está aprobado, NO se permite UPDATE/DELETE/INSERT de specs.
        """CREATE TRIGGER IF NOT EXISTS trg_ipcspec_no_edit_aprobado
           BEFORE UPDATE ON ipc_specs
           FOR EACH ROW
           WHEN EXISTS (SELECT 1 FROM mbr_templates
                        WHERE id = NEW.mbr_template_id AND estado IN ('aprobado','obsoleto'))
           BEGIN
               SELECT RAISE(ABORT, 'IPC specs de MBR aprobado son inmutables');
           END""",
        """CREATE TRIGGER IF NOT EXISTS trg_ipcspec_no_delete_aprobado
           BEFORE DELETE ON ipc_specs
           FOR EACH ROW
           WHEN EXISTS (SELECT 1 FROM mbr_templates
                        WHERE id = OLD.mbr_template_id AND estado IN ('aprobado','obsoleto'))
           BEGIN
               SELECT RAISE(ABORT, 'IPC specs de MBR aprobado son inmutables · DELETE prohibido');
           END""",
        """CREATE TRIGGER IF NOT EXISTS trg_ipcspec_no_insert_aprobado
           BEFORE INSERT ON ipc_specs
           FOR EACH ROW
           WHEN EXISTS (SELECT 1 FROM mbr_templates
                        WHERE id = NEW.mbr_template_id AND estado IN ('aprobado','obsoleto'))
           BEGIN
               SELECT RAISE(ABORT, 'IPC specs de MBR aprobado son inmutables · INSERT prohibido');
           END""",

        # ipc_resultados: medición concreta en un EBR. conforme se calcula
        # en el endpoint si hay rango numérico, o lo setea QC si es cualitativo.
        # qc_e_sign_id es para mediciones que requieren validación QC explícita.
        """CREATE TABLE IF NOT EXISTS ipc_resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ebr_id INTEGER NOT NULL,
            ipc_spec_id INTEGER NOT NULL,
            valor_medido REAL DEFAULT NULL,
            valor_texto TEXT DEFAULT '',
            conforme INTEGER DEFAULT NULL,
            medido_por TEXT NOT NULL,
            medido_at_utc TEXT NOT NULL,
            qc_username TEXT DEFAULT '',
            qc_e_sign_id INTEGER DEFAULT NULL,
            notas TEXT DEFAULT '',
            FOREIGN KEY (ebr_id) REFERENCES ebr_ejecuciones(id) ON DELETE CASCADE,
            FOREIGN KEY (ipc_spec_id) REFERENCES ipc_specs(id),
            UNIQUE(ebr_id, ipc_spec_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ipcres_ebr ON ipc_resultados(ebr_id, ipc_spec_id)",
        "CREATE INDEX IF NOT EXISTS idx_ipcres_conforme ON ipc_resultados(conforme, ebr_id)",

        # Inmutabilidad post-liberación del EBR (espejo de la lógica EBR).
        """CREATE TRIGGER IF NOT EXISTS trg_ipcres_no_edit_liberado
           BEFORE UPDATE ON ipc_resultados
           FOR EACH ROW
           WHEN EXISTS (SELECT 1 FROM ebr_ejecuciones
                        WHERE id = NEW.ebr_id AND estado IN ('liberado','rechazado'))
           BEGIN
               SELECT RAISE(ABORT, 'IPC resultados de EBR liberado/rechazado son inmutables');
           END""",
        """CREATE TRIGGER IF NOT EXISTS trg_ipcres_no_delete_liberado
           BEFORE DELETE ON ipc_resultados
           FOR EACH ROW
           WHEN EXISTS (SELECT 1 FROM ebr_ejecuciones
                        WHERE id = OLD.ebr_id AND estado IN ('liberado','rechazado'))
           BEGIN
               SELECT RAISE(ABORT, 'IPC resultados de EBR liberado/rechazado son inmutables');
           END""",
    ]),
    (111, "EBR (Executed Batch Record) · ejecución de lote real · Fase 1 BRD · Sebastián 12-may-2026", [
        # EBR = instancia ejecutada de un MBR aprobado para UN lote real.
        # Workflow:
        #   iniciado          → al crear · pasos_ejecutados clonados de MBR
        #                       en estado='pendiente'.
        #   en_proceso        → primer paso completado.
        #   completado        → todos los pasos completados + cantidad_real_g
        #                       reportada · esperando QC.
        #   en_revision_qc    → QC mirando el EBR (transición opcional).
        #   liberado          → QC firmó liberación · INMUTABLE post este punto.
        #   rechazado         → QC firmó rechazo · INMUTABLE post este punto.
        #
        # liberado_signature_id es FK lógico a e_signatures con meaning='libera'.
        # mbr_version es snapshot · si el MBR fuente cambia (no debería poder,
        # por trigger mig 109) el EBR sigue mostrando la versión que ejecutó.
        #
        # cantidad_objetivo_g se snapshotea de mbr.lote_size_g al iniciar para
        # que la reconciliación teórico vs real (cantidad_real_g / objetivo)
        # sea estable aunque el MBR fuente se obsoletee.
        """CREATE TABLE IF NOT EXISTS ebr_ejecuciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mbr_template_id INTEGER NOT NULL,
            mbr_version INTEGER NOT NULL,
            produccion_id INTEGER DEFAULT NULL,
            lote TEXT NOT NULL UNIQUE,
            estado TEXT NOT NULL DEFAULT 'iniciado',
            iniciado_por TEXT NOT NULL,
            iniciado_at_utc TEXT NOT NULL,
            completado_at_utc TEXT DEFAULT NULL,
            liberado_por TEXT DEFAULT '',
            liberado_at_utc TEXT DEFAULT NULL,
            liberado_signature_id INTEGER DEFAULT NULL,
            rechazado_motivo TEXT DEFAULT '',
            cantidad_objetivo_g REAL NOT NULL,
            cantidad_real_g REAL DEFAULT NULL,
            yield_pct REAL DEFAULT NULL,
            notas TEXT DEFAULT '',
            FOREIGN KEY (mbr_template_id) REFERENCES mbr_templates(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ebr_estado ON ebr_ejecuciones(estado, iniciado_at_utc DESC)",
        "CREATE INDEX IF NOT EXISTS idx_ebr_mbr ON ebr_ejecuciones(mbr_template_id, iniciado_at_utc DESC)",
        "CREATE INDEX IF NOT EXISTS idx_ebr_produccion ON ebr_ejecuciones(produccion_id) WHERE produccion_id IS NOT NULL",

        # ebr_pasos_ejecutados: snapshot de los pasos del MBR + estado de
        # ejecución por cada uno. Se clonan al iniciar el EBR (orden +
        # descripcion + flags) para que el record sobreviva a un eventual
        # cambio del MBR fuente.
        """CREATE TABLE IF NOT EXISTS ebr_pasos_ejecutados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ebr_id INTEGER NOT NULL,
            mbr_paso_id INTEGER NOT NULL,
            orden INTEGER NOT NULL,
            descripcion TEXT NOT NULL,
            tipo_paso TEXT DEFAULT 'otro',
            equipo_requerido TEXT DEFAULT '',
            requiere_e_sign INTEGER DEFAULT 0,
            requiere_qc INTEGER DEFAULT 0,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            operario_username TEXT DEFAULT '',
            iniciado_at_utc TEXT DEFAULT NULL,
            completado_at_utc TEXT DEFAULT NULL,
            observaciones TEXT DEFAULT '',
            e_sign_id INTEGER DEFAULT NULL,
            qc_username TEXT DEFAULT '',
            qc_e_sign_id INTEGER DEFAULT NULL,
            desviacion_id INTEGER DEFAULT NULL,
            UNIQUE(ebr_id, orden),
            FOREIGN KEY (ebr_id) REFERENCES ebr_ejecuciones(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_ebr_pasos_ebr ON ebr_pasos_ejecutados(ebr_id, orden)",
        "CREATE INDEX IF NOT EXISTS idx_ebr_pasos_estado ON ebr_pasos_ejecutados(estado, ebr_id)",

        # Trigger inmutabilidad: una vez liberado/rechazado, NO se modifican
        # campos críticos del EBR (los QA/QC pueden agregar comentarios
        # postliberación a través del audit_log, NO modificando el EBR).
        """CREATE TRIGGER IF NOT EXISTS trg_ebr_liberado_no_edit
           BEFORE UPDATE ON ebr_ejecuciones
           FOR EACH ROW
           WHEN OLD.estado IN ('liberado', 'rechazado')
                AND (NEW.estado IS NOT OLD.estado
                  OR NEW.cantidad_real_g IS NOT OLD.cantidad_real_g
                  OR NEW.yield_pct IS NOT OLD.yield_pct
                  OR NEW.liberado_signature_id IS NOT OLD.liberado_signature_id
                  OR NEW.notas IS NOT OLD.notas)
           BEGIN
               SELECT RAISE(ABORT, 'EBR liberado/rechazado es inmutable (Part 11 11.10(e))');
           END""",

        # Trigger inmutabilidad pasos post-liberación
        """CREATE TRIGGER IF NOT EXISTS trg_ebr_pasos_liberado_no_edit
           BEFORE UPDATE ON ebr_pasos_ejecutados
           FOR EACH ROW
           WHEN EXISTS (SELECT 1 FROM ebr_ejecuciones
                        WHERE id = NEW.ebr_id
                          AND estado IN ('liberado', 'rechazado'))
           BEGIN
               SELECT RAISE(ABORT, 'pasos de EBR liberado/rechazado son inmutables');
           END""",
        """CREATE TRIGGER IF NOT EXISTS trg_ebr_pasos_liberado_no_delete
           BEFORE DELETE ON ebr_pasos_ejecutados
           FOR EACH ROW
           WHEN EXISTS (SELECT 1 FROM ebr_ejecuciones
                        WHERE id = OLD.ebr_id
                          AND estado IN ('liberado', 'rechazado'))
           BEGIN
               SELECT RAISE(ABORT, 'pasos de EBR liberado/rechazado son inmutables · DELETE prohibido');
           END""",
    ]),
    (110, "MBR seed · Blush Balm v1 draft (primer template real) · Sebastián 12-may-2026", [
        # Primer MBR draft real con Blush Balm (fórmula oficial v1, mig 104).
        # Se crea como DRAFT para que Sebastián/Calidad lo revise y ajuste
        # los pasos antes de aprobar. 7 pasos genéricos como punto de partida
        # — se editan vía PATCH /api/brd/mbr/<id>/pasos/<paso_id>.
        #
        # creado_por='system-seed' indica origen automático. En el aprobar
        # final, aprobado_por será un user real con e-signature válida.
        """INSERT OR IGNORE INTO mbr_templates
             (producto_nombre, version, estado, titulo, descripcion,
              lote_size_g, tiempo_total_estimado_min, creado_por)
           VALUES (
             'Blush Balm', 1, 'draft',
             'Blush Balm · Master Batch Record v1',
             'Procedimiento estándar para fabricación de Blush Balm. '
              || 'Lote referencia 1kg con 21 MPs (mig 104). '
              || 'PENDIENTE: Calidad debe ajustar parámetros específicos '
              || 'antes de submit a revisión.',
             1000.0, 360, 'system-seed'
           )""",

        # Pasos seedeados · cubrir las 3 fases típicas de una crema/balm.
        # tiempo_estimado_min totaliza ~360min (6h). Calidad ajusta.
        """INSERT OR IGNORE INTO mbr_pasos
             (mbr_template_id, orden, fase, descripcion, tipo_paso,
              equipo_requerido, tiempo_estimado_min, requiere_e_sign,
              requiere_qc, notas)
           SELECT
             (SELECT id FROM mbr_templates WHERE producto_nombre='Blush Balm' AND version=1),
             orden, fase, descripcion, tipo_paso, equipo_requerido,
             tiempo_estimado_min, requiere_e_sign, requiere_qc, notas
           FROM (
             SELECT 1 AS orden, 'dispensacion' AS fase,
                    'Pesar las 21 MPs según fórmula maestra (referencia 1kg)' AS descripcion,
                    'pesaje' AS tipo_paso, 'BAL01,DISP' AS equipo_requerido,
                    60 AS tiempo_estimado_min, 1 AS requiere_e_sign, 0 AS requiere_qc,
                    'Mayerlin · dispensación. Verificar lote+vencimiento de cada MP.' AS notas
             UNION ALL SELECT 2, 'fabricacion',
                    'Fundir fase oleosa: ceras (Synthetic, Microcristalina, Ceresine) + oils a 75°C en TQ01',
                    'caliente', 'TQ01', 45, 1, 0,
                    'Verificar fusión completa antes de pasar al paso 3'
             UNION ALL SELECT 3, 'fabricacion',
                    'Adicionar y dispersar pigmentos CI + Boron nitride en fase oleosa',
                    'mezclado', 'TQ01,DISP', 30, 0, 0,
                    'Mezclado homogéneo · sin grumos visibles'
             UNION ALL SELECT 4, 'fabricacion',
                    'Adicionar manteca de murumuru, beauty oil ceramidas',
                    'mezclado', 'TQ01', 20, 0, 0, ''
             UNION ALL SELECT 5, 'fabricacion',
                    'Enfriar a 50°C y adicionar peptides + Vit E + AE Vainilla + AE Neroli + Tinogard',
                    'enfriamiento', 'TQ01', 30, 1, 0,
                    'Activos sensibles a calor · NO superar 50°C en este paso'
             UNION ALL SELECT 6, 'control_ipc',
                    'Control en proceso: apariencia, color, textura',
                    'control_ipc', '', 15, 0, 1,
                    'QC visual · comparar contra muestra patrón'
             UNION ALL SELECT 7, 'envasado',
                    'Envasar en frascos definidos por presentación',
                    'envasado', 'ENV1', 90, 0, 1,
                    'Verificar etiquetado y cierre · QC firma liberación'
           )""",
    ]),
    (109, "MBR (Master Batch Record) · templates + pasos · Fase 1 BRD · Sebastián 12-may-2026", [
        # Master Batch Record = procedimiento aprobado para fabricar UN
        # producto en UN tamaño de lote estándar. Estructura:
        #   mbr_templates: header con producto + versión + estado del workflow.
        #   mbr_pasos: secuencia ordenada de instrucciones para el operario.
        #
        # WORKFLOW de estados (mbr_templates.estado):
        #   draft        → puede editarse libremente por el creador.
        #   en_revision  → submit a QA · ya no editable.
        #   aprobado     → vigente · puede instanciarse en EBR. Inmutable.
        #   obsoleto     → reemplazado por versión nueva. NO instanciable.
        #
        # Solo UN MBR aprobado por (producto, versión). El producto puede
        # tener múltiples versiones a lo largo del tiempo (v1 obsoleto +
        # v2 aprobado + v3 draft) — los EBR siempre referencian la versión
        # exacta vigente al momento de iniciar.
        #
        # aprobado_signature_id es FK lógico (no SQL) a e_signatures: la
        # aprobación QA debe pasar por POST /api/sign con meaning='aprueba'
        # y el signature_id resultante se persiste aquí. Sin firma, el
        # endpoint /api/brd/mbr/<id>/aprobar rechaza.
        """CREATE TABLE IF NOT EXISTS mbr_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_nombre TEXT NOT NULL,
            formula_version_id INTEGER,
            version INTEGER NOT NULL,
            estado TEXT NOT NULL DEFAULT 'draft',
            titulo TEXT DEFAULT '',
            descripcion TEXT DEFAULT '',
            lote_size_g REAL NOT NULL,
            tiempo_total_estimado_min INTEGER DEFAULT 0,
            creado_por TEXT NOT NULL,
            creado_at_utc TEXT DEFAULT (datetime('now', 'utc')),
            updated_at_utc TEXT DEFAULT (datetime('now', 'utc')),
            aprobado_por TEXT DEFAULT '',
            aprobado_at_utc TEXT DEFAULT NULL,
            aprobado_signature_id INTEGER DEFAULT NULL,
            obsoleto_at_utc TEXT DEFAULT NULL,
            obsoleto_motivo TEXT DEFAULT '',
            UNIQUE(producto_nombre, version)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_mbr_producto_estado ON mbr_templates(producto_nombre, estado)",
        "CREATE INDEX IF NOT EXISTS idx_mbr_estado ON mbr_templates(estado, producto_nombre)",

        # mbr_pasos: secuencia de instrucciones. orden es 1-based.
        # tipo_paso ∈ {'pesaje', 'dispensacion', 'mezclado', 'caliente',
        #              'enfriamiento', 'control_ipc', 'envasado', 'inspeccion',
        #              'limpieza', 'otro'}.
        # requiere_e_sign=1 → el operario debe firmar electrónicamente al
        # marcar el paso como completado (común en pesajes críticos, IPCs).
        # requiere_qc=1 → además del operario, QC debe firmar.
        """CREATE TABLE IF NOT EXISTS mbr_pasos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mbr_template_id INTEGER NOT NULL,
            orden INTEGER NOT NULL,
            fase TEXT DEFAULT '',
            descripcion TEXT NOT NULL,
            tipo_paso TEXT DEFAULT 'otro',
            equipo_requerido TEXT DEFAULT '',
            tiempo_estimado_min INTEGER DEFAULT 0,
            requiere_e_sign INTEGER DEFAULT 0,
            requiere_qc INTEGER DEFAULT 0,
            notas TEXT DEFAULT '',
            UNIQUE(mbr_template_id, orden),
            FOREIGN KEY (mbr_template_id) REFERENCES mbr_templates(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_mbr_pasos_template ON mbr_pasos(mbr_template_id, orden)",

        # Trigger updated_at fresh en cada UPDATE de mbr_templates
        """CREATE TRIGGER IF NOT EXISTS trg_mbr_templates_updated_at
           AFTER UPDATE ON mbr_templates
           FOR EACH ROW
           WHEN OLD.updated_at_utc = NEW.updated_at_utc
           BEGIN
               UPDATE mbr_templates SET updated_at_utc = datetime('now', 'utc') WHERE id = NEW.id;
           END""",

        # Trigger inmutabilidad post-aprobación: una vez estado='aprobado',
        # los campos críticos (titulo, descripcion, lote_size_g, formula_version_id)
        # no se pueden modificar. Solo se permite obsoletar (cambiar a
        # estado='obsoleto' + obsoleto_at_utc + obsoleto_motivo).
        """CREATE TRIGGER IF NOT EXISTS trg_mbr_aprobado_no_edit
           BEFORE UPDATE ON mbr_templates
           FOR EACH ROW
           WHEN OLD.estado = 'aprobado'
                AND NEW.estado = 'aprobado'
                AND (OLD.titulo IS NOT NEW.titulo
                  OR OLD.descripcion IS NOT NEW.descripcion
                  OR OLD.lote_size_g IS NOT NEW.lote_size_g
                  OR OLD.formula_version_id IS NOT NEW.formula_version_id)
           BEGIN
               SELECT RAISE(ABORT, 'MBR aprobado es inmutable · obsoletá y crea v+1 (Part 11 11.10(e))');
           END""",

        # Trigger inmutabilidad sobre mbr_pasos cuando el template está aprobado
        """CREATE TRIGGER IF NOT EXISTS trg_mbr_pasos_no_edit_aprobado
           BEFORE UPDATE ON mbr_pasos
           FOR EACH ROW
           WHEN EXISTS (SELECT 1 FROM mbr_templates
                        WHERE id = NEW.mbr_template_id AND estado = 'aprobado')
           BEGIN
               SELECT RAISE(ABORT, 'pasos de MBR aprobado son inmutables');
           END""",
        """CREATE TRIGGER IF NOT EXISTS trg_mbr_pasos_no_delete_aprobado
           BEFORE DELETE ON mbr_pasos
           FOR EACH ROW
           WHEN EXISTS (SELECT 1 FROM mbr_templates
                        WHERE id = OLD.mbr_template_id AND estado = 'aprobado')
           BEGIN
               SELECT RAISE(ABORT, 'pasos de MBR aprobado son inmutables · DELETE prohibido');
           END""",
        """CREATE TRIGGER IF NOT EXISTS trg_mbr_pasos_no_insert_aprobado
           BEFORE INSERT ON mbr_pasos
           FOR EACH ROW
           WHEN EXISTS (SELECT 1 FROM mbr_templates
                        WHERE id = NEW.mbr_template_id AND estado = 'aprobado')
           BEGIN
               SELECT RAISE(ABORT, 'pasos de MBR aprobado son inmutables · INSERT prohibido');
           END""",
    ]),
    (107, "e_signatures · Part 11 §11.50 §11.70 §11.200 firma electrónica · Sebastián 12-may-2026", [
        # Tabla central de firmas electrónicas con binding inmutable al record
        # firmado. 21 CFR Part 11:
        #   §11.50  - Signature manifestations (printed name + date + meaning)
        #   §11.70  - Signature/record linking (firma no separable del registro)
        #   §11.200 - Electronic signature components (re-auth + meaning)
        #
        # signer_full_name/cedula/cargo se snapshotean al momento de firma
        # (no FK) para que la evidencia sobreviva al rename/eliminación de
        # la persona en usuarios_identidad — auditoría puede ver "quién era
        # esa persona el día que firmó".
        #
        # record_hash captura el estado del record al momento de firma
        # (calculado por el caller del endpoint /api/sign). signature_hash
        # es HMAC-SHA256 de todos los campos críticos con SECRET_KEY como
        # llave — si alguien rota el SECRET_KEY las firmas pasadas siguen
        # siendo verificables porque el hash quedó persistido (no se
        # re-calcula). El tamper-evidence depende de que SECRET_KEY no
        # haya sido leakeada antes del intento de adulteración.
        """CREATE TABLE IF NOT EXISTS e_signatures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_table TEXT NOT NULL,
            record_id TEXT NOT NULL,
            meaning TEXT NOT NULL,
            signer_username TEXT NOT NULL,
            signer_full_name TEXT DEFAULT '',
            signer_cedula TEXT DEFAULT '',
            signer_cargo TEXT DEFAULT '',
            signed_at_utc TEXT NOT NULL,
            ip TEXT DEFAULT '',
            auth_factor TEXT NOT NULL,
            comment TEXT DEFAULT '',
            record_hash TEXT DEFAULT '',
            signature_hash TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_esig_record ON e_signatures(record_table, record_id, signed_at_utc DESC)",
        "CREATE INDEX IF NOT EXISTS idx_esig_signer ON e_signatures(signer_username, signed_at_utc DESC)",
        "CREATE INDEX IF NOT EXISTS idx_esig_meaning ON e_signatures(meaning, signed_at_utc DESC)",
        # Triggers append-only · misma protección que audit_log (mig 105)
        """CREATE TRIGGER IF NOT EXISTS trg_esig_no_update
           BEFORE UPDATE ON e_signatures
           BEGIN
               SELECT RAISE(ABORT, 'e_signatures es append-only (Part 11 11.50)');
           END""",
        """CREATE TRIGGER IF NOT EXISTS trg_esig_no_delete
           BEFORE DELETE ON e_signatures
           BEGIN
               SELECT RAISE(ABORT, 'e_signatures es append-only (Part 11 11.50)');
           END""",
    ]),
    (108, "sign_challenges · single-use re-auth tokens para firma · Sebastián 12-may-2026", [
        # Tokens de corta vida que prueban que el firmante se re-autenticó
        # con password (+TOTP si tiene MFA) en los últimos 5 minutos. El
        # workflow es:
        #   1. Frontend muestra modal "Firmar como liberado"
        #   2. Modal pide password + TOTP
        #   3. POST /api/sign/challenge → verifica + emite token corto
        #   4. POST /api/sign con el token → consume + crea e_signature
        #
        # consumed=1 garantiza single-use. El cron cleanup_logs limpia los
        # vencidos (no urgente, los expira el endpoint igual).
        """CREATE TABLE IF NOT EXISTS sign_challenges (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            auth_factor TEXT NOT NULL,
            created_at_utc TEXT NOT NULL,
            expires_at_utc TEXT NOT NULL,
            consumed INTEGER DEFAULT 0,
            consumed_at_utc TEXT DEFAULT NULL,
            ip TEXT DEFAULT ''
        )""",
        "CREATE INDEX IF NOT EXISTS idx_signchall_username ON sign_challenges(username, expires_at_utc DESC)",
        "CREATE INDEX IF NOT EXISTS idx_signchall_expires ON sign_challenges(expires_at_utc)",
    ]),
    (106, "usuarios_identidad · Part 11 §11.100(b) identity binding · Sebastián 12-may-2026", [
        # Tabla de identidad humana detrás de cada `username` de la app.
        # Part 11 §11.100(b): "before an organization establishes, assigns,
        # certifies, or otherwise sanctions an individual's electronic
        # signature... the organization shall verify the identity of the
        # individual." Hoy COMPRAS_USERS son strings hardcoded en config.py;
        # esta tabla aporta el binding con la persona real (cédula, cargo,
        # manager) que un auditor INVIMA exige para validar quién firmó qué.
        #
        # username es texto (no FK a una tabla `users` que no existe todavía)
        # para no acoplarnos al refactor RBAC futuro. Cuando exista `users`
        # tabla se agrega FK con migración aparte.
        #
        # Manager: username del jefe directo (auto-referencia textual). Útil
        # para workflow de aprobación donde la firma de un junior debe ser
        # contra-verificada por su manager.
        """CREATE TABLE IF NOT EXISTS usuarios_identidad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            cedula TEXT DEFAULT '',
            nombre_completo TEXT DEFAULT '',
            cargo TEXT DEFAULT 'Por definir',
            area TEXT DEFAULT '',
            email TEXT DEFAULT '',
            manager_username TEXT DEFAULT '',
            activo INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_usuarios_identidad_activo ON usuarios_identidad(activo, username)",
        "CREATE INDEX IF NOT EXISTS idx_usuarios_identidad_manager ON usuarios_identidad(manager_username) WHERE manager_username != ''",

        # Seed básico de los 19 usuarios actuales (config.py:16-44).
        # Cargo y area como 'Por definir'; admin completa por UI después.
        # cedula y nombre_completo NO se seedean (datos personales · admin
        # los carga directamente). INSERT OR IGNORE para idempotencia.
        """INSERT OR IGNORE INTO usuarios_identidad (username, cargo, area, manager_username) VALUES
            ('sebastian',  'CEO · Founder',                'Gerencia',     ''),
            ('alejandro',  'Co-Founder · Director',        'Gerencia',     ''),
            ('hernando',   'Director Técnico',             'Técnica',      'sebastian'),
            ('catalina',   'Asistente de Compras',         'Compras',      'mayra'),
            ('luz',        'Asistente Gerencia Espagiria', 'Espagiria',    'alejandro'),
            ('daniela',    'Asistente Gerencia ÁNIMUS',    'Animus',       'alejandro'),
            ('valentina',  'Asistente Comercial',          'Comercial',    'daniela'),
            ('jefferson',  'Marketing Lead',               'Marketing',    'sebastian'),
            ('felipe',     'Marketing',                    'Marketing',    'jefferson'),
            ('mayra',      'Contadora',                    'Contabilidad', 'sebastian'),
            ('gloria',     'RRHH',                         'RRHH',         'mayra'),
            ('laura',      'Calidad',                      'Calidad',      'alejandro'),
            ('miguel',     'Técnica · Calidad',            'Técnica',      'hernando'),
            ('yuliel',     'Calidad',                      'Calidad',      'laura'),
            ('luis',       'Jefe de Planta',               'Producción',   'alejandro'),
            ('smurillo',   'Operario Planta',              'Producción',   'luis'),
            ('sergio',     'Operario Planta',              'Producción',   'luis'),
            ('mayerlin',   'Operaria · Dispensación',      'Producción',   'luis'),
            ('camilo',     'Operario Planta',              'Producción',   'luis')""",

        # Trigger para mantener updated_at fresco en cada UPDATE.
        """CREATE TRIGGER IF NOT EXISTS trg_usuarios_identidad_updated_at
           AFTER UPDATE ON usuarios_identidad
           FOR EACH ROW
           BEGIN
               UPDATE usuarios_identidad SET updated_at = datetime('now') WHERE id = NEW.id;
           END""",
    ]),
    (105, "audit_log append-only · Part 11 §11.10(e) · Sebastián 12-may-2026", [
        # Bloquea UPDATE/DELETE sobre audit_log para que la evidencia
        # regulatoria sea inmutable. 21 CFR Part 11 §11.10(e) requiere
        # "use of secure, computer-generated, time-stamped audit trails to
        # independently record the date and time of operator entries and
        # actions that create, modify, or delete electronic records."
        # Una columna audit no inmutable es inválida en auditoría INVIMA
        # (cualquier admin con shell SQLite podía sobreescribir el rastro).
        #
        # Si en el futuro se necesita archivar audit_log >3 años (política
        # de retención EOS), hacerlo con una migración explícita que
        # DROP TRIGGER → mueva filas → CREATE TRIGGER. NUNCA en runtime.
        """CREATE TRIGGER IF NOT EXISTS trg_audit_log_no_update
           BEFORE UPDATE ON audit_log
           BEGIN
               SELECT RAISE(ABORT, 'audit_log es append-only (Part 11 11.10(e))');
           END""",
        """CREATE TRIGGER IF NOT EXISTS trg_audit_log_no_delete
           BEFORE DELETE ON audit_log
           BEGIN
               SELECT RAISE(ABORT, 'audit_log es append-only (Part 11 11.10(e))');
           END""",
    ]),
    (104, "Blush Balm · fórmula oficial v1 (21 MPs · 1kg) + remap BBM · Sebastián 12-may-2026", [
        # Fórmula completa Blush Balm aprobada por Sebastián CEO 12-may-2026.
        # Origen: archive/data-imports/formulas_data.json:2357 (v1 · 100% activos).
        # 20 MPs con código existente + 1 pigmento nuevo MPPIGCI01 (Pigmentos CI
        # como mezcla · si Dirección Técnica quiere desglose por CI individual,
        # crear MPs separados en migration posterior y reasignar % aquí).
        #
        # Trigger FK de migration 98 exige que codigo_mp exista en maestro_mps
        # ANTES de insertar en formula_items. Por eso primero INSERT OR IGNORE
        # los 21 codigos (preserva nombre_comercial si ya existe), después la
        # fórmula. Idempotente.

        # Paso 1a: garantizar que los 21 MPs existan en maestro_mps
        """INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, activo) VALUES
            ('MP00051', 'Polyglyceryl-2 triisostearate', 1),
            ('MP00063', 'Tinogard TT',                  1),
            ('MPPIGCI01','Pigmentos CI (mezcla)',       1),
            ('MP00054', 'Lauroyl lysine',               1),
            ('MP00127', 'BM-956',                       1),
            ('MP00040', 'Cetiol',                       1),
            ('MPCOCP01','Coco caprylate',               1),
            ('MP00103', 'Beauty Oil Cerámidas',         1),
            ('MP00257', 'Synthetic wax',                1),
            ('MP00024', 'Microcristalina 127',          1),
            ('MP00041', 'Ceresine wax',                 1),
            ('MP00077', 'Manteca murumuru',             1),
            ('MP00055', 'PMSS',                         1),
            ('MPBNIT01','Boron nitride',                1),
            ('MP00207', 'Stabil',                       1),
            ('MP00078', 'Vitamina E líquida',           1),
            ('MP00101', 'AE Vainilla',                  1),
            ('MP00025', 'AE Neroli',                    1),
            ('MP00190', 'Palmitoyl tripeptide-1',       1),
            ('MP00172', 'Palmitoyl tetrapeptide-7',     1),
            ('MP00174', 'Palmitoyl tripeptide-38',      1)""",

        # Paso 1b: forzar activo=1 (INSERT OR IGNORE no actualiza filas
        # existentes · si algún MP existía con activo=0 el trigger FK de
        # migration 98 abortaría el paso 4 con 'material_id no existe en
        # maestro_mps activo'). Fix del deploy fallido 12-may-2026 6pm.
        """UPDATE maestro_mps SET activo=1 WHERE codigo_mp IN (
            'MP00051','MP00063','MPPIGCI01','MP00054','MP00127','MP00040',
            'MPCOCP01','MP00103','MP00257','MP00024','MP00041','MP00077',
            'MP00055','MPBNIT01','MP00207','MP00078','MP00101','MP00025',
            'MP00190','MP00172','MP00174'
        )""",

        # Paso 2: formula_headers (lote ref 1kg)
        """INSERT OR REPLACE INTO formula_headers (producto_nombre, unidad_base_g, descripcion)
           VALUES ('Blush Balm', 1000.0, 'v1 oficial · lote 1kg · 21 MPs · Sebastián 12-may-2026')""",

        # Paso 3: limpiar items previos (idempotencia)
        """DELETE FROM formula_items WHERE producto_nombre='Blush Balm'""",

        # Paso 4: insertar 21 items de la fórmula
        """INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) VALUES
            ('Blush Balm', 'MP00051',  'Polyglyceryl-2 triisostearate', 10.0),
            ('Blush Balm', 'MP00063',  'Tinogard TT',                   0.1),
            ('Blush Balm', 'MPPIGCI01','Pigmentos CI (mezcla)',         7.5),
            ('Blush Balm', 'MP00054',  'Lauroyl lysine',                1.0),
            ('Blush Balm', 'MP00127',  'BM-956',                        20.271),
            ('Blush Balm', 'MP00040',  'Cetiol',                        20.271),
            ('Blush Balm', 'MPCOCP01', 'Coco caprylate',                3.0),
            ('Blush Balm', 'MP00103',  'Beauty Oil Cerámidas',          0.3),
            ('Blush Balm', 'MP00257',  'Synthetic wax',                 11.5),
            ('Blush Balm', 'MP00024',  'Microcristalina 127',           10.0),
            ('Blush Balm', 'MP00041',  'Ceresine wax',                  10.0),
            ('Blush Balm', 'MP00077',  'Manteca murumuru',              0.15),
            ('Blush Balm', 'MP00055',  'PMSS',                          3.0),
            ('Blush Balm', 'MPBNIT01', 'Boron nitride',                 2.0),
            ('Blush Balm', 'MP00207',  'Stabil',                        0.75),
            ('Blush Balm', 'MP00078',  'Vitamina E líquida',            0.1),
            ('Blush Balm', 'MP00101',  'AE Vainilla',                   0.035),
            ('Blush Balm', 'MP00025',  'AE Neroli',                     0.02),
            ('Blush Balm', 'MP00190',  'Palmitoyl tripeptide-1',        0.001),
            ('Blush Balm', 'MP00172',  'Palmitoyl tetrapeptide-7',      0.001),
            ('Blush Balm', 'MP00174',  'Palmitoyl tripeptide-38',       0.001)""",

        # Paso 5: remapear BBM → 'Blush Balm' (reemplaza el activo=0 de migration 103)
        """INSERT OR REPLACE INTO sku_producto_map (sku, producto_nombre, activo)
           VALUES ('BBM', 'Blush Balm', 1)"""
    ]),
    (103, "BBM (Blush Balm) · desactivar mapeo erróneo a MASCARILLA HIDRATANTE · Sebastián 12-may-2026", [
        # Migration #8 mapeo BBM → MASCARILLA HIDRATANTE incorrectamente.
        # BBM es 'Blush Balm', producto nuevo de la línea de creadoras
        # (royalty 15%). Hasta que se cargue la fórmula real, desactivamos
        # el mapeo para que el panel de prioridad-agotamiento no infle MPs
        # de la mascarilla cuando BBM venda. BBM seguirá apareciendo en
        # listado SKUs (porque vende en Shopify), solo que sin producto_base
        # resuelto · no contribuirá a mps_necesarias.
        # Reemplazada en migration 104 (carga fórmula real + remap correcto).
        """UPDATE sku_producto_map SET activo=0 WHERE sku='BBM'"""
    ]),
    (98, "FK enforcement formula_items → maestro_mps (Sebastián 10-may-2026)", [
        # Sebastián 10-may-2026: tras normalizar formula_items con remapeo
        # bulk, AHORA es safe activar enforcement · cero huérfanos confirmado.
        # Estos triggers garantizan que NUNCA se pueda crear/actualizar un
        # formula_items con material_id que no exista en maestro_mps activo.
        # Resultado: cero huérfanos a futuro · descuento de producción 100%
        # confiable.
        """CREATE TRIGGER IF NOT EXISTS trg_fi_material_id_fk
        BEFORE INSERT ON formula_items
        FOR EACH ROW
        WHEN NEW.material_id IS NOT NULL AND TRIM(NEW.material_id) != ''
          AND NOT EXISTS (
            SELECT 1 FROM maestro_mps
            WHERE codigo_mp = NEW.material_id AND activo = 1
          )
        BEGIN
            SELECT RAISE(ABORT, 'material_id no existe en maestro_mps activo (FK violation)');
        END""",
        """CREATE TRIGGER IF NOT EXISTS trg_fi_material_id_fk_upd
        BEFORE UPDATE OF material_id ON formula_items
        FOR EACH ROW
        WHEN NEW.material_id IS NOT NULL AND TRIM(NEW.material_id) != ''
          AND NEW.material_id != OLD.material_id
          AND NOT EXISTS (
            SELECT 1 FROM maestro_mps
            WHERE codigo_mp = NEW.material_id AND activo = 1
          )
        BEGIN
            SELECT RAISE(ABORT, 'UPDATE material_id no existe en maestro_mps activo (FK violation)');
        END""",
    ]),
    (100, "audit_zero_error_runs (historial scores) · Sebastián 8-may-2026", [
        """CREATE TABLE IF NOT EXISTS audit_zero_error_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL DEFAULT (datetime('now')),
            score_global REAL,
            veredicto_global TEXT,
            score_real REAL,
            veredicto_real TEXT,
            alta INTEGER DEFAULT 0,
            media INTEGER DEFAULT 0,
            baja INTEGER DEFAULT 0,
            detalles_json TEXT,
            origen TEXT DEFAULT 'cron'
        )""",
        "CREATE INDEX IF NOT EXISTS idx_aze_fecha ON audit_zero_error_runs(fecha DESC)",
    ]),
    (102, "db_health_log · histórico de integrity checks · Sebastián 12-may-2026", [
        # Tracking de integridad de la BD. Cron diario corre PRAGMA
        # quick_check y registra resultado. Si falla, alerta SEC HIGH.
        # Permite ver retrospectivamente cuándo empezó la corrupción.
        """CREATE TABLE IF NOT EXISTS db_health_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL DEFAULT (datetime('now')),
            integrity TEXT,
            db_size_kb INTEGER,
            wal_size_kb INTEGER,
            error TEXT,
            origen TEXT DEFAULT 'cron'
        )""",
        "CREATE INDEX IF NOT EXISTS idx_dbhealth_fecha ON db_health_log(fecha DESC)",
    ]),
    (101, "mp_alcanza_snapshots · cron diario tracking COMPRAR_YA · Sebastián 12-may-2026", [
        # Tracking diario de MPs en COMPRAR_YA para alertar cuando aparecen
        # nuevas (delta vs ayer). Una fila por día. comprar_ya_codigos es
        # JSON array de codigo_mp para computar delta entre dias.
        """CREATE TABLE IF NOT EXISTS mp_alcanza_snapshots (
            fecha TEXT PRIMARY KEY,
            total_mps INTEGER,
            comprar_ya_total INTEGER,
            comprar_1_2_sem_total INTEGER,
            comprar_1_mes_total INTEGER,
            ok_total INTEGER,
            sin_uso_total INTEGER,
            comprar_ya_codigos TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            origen TEXT DEFAULT 'cron'
        )""",
        "CREATE INDEX IF NOT EXISTS idx_mps_fecha ON mp_alcanza_snapshots(fecha DESC)",
    ]),
    (99, "producciones: formula_snapshot_json (anti drift retroactivo · Sebastián 8-may-2026)", [
        # Snapshot inmutable de la fórmula al momento exacto de la producción.
        # Resuelve el bug raíz descubierto por audit profundo: si la fórmula
        # se modifica DESPUÉS de una producción, el audit comparaba contra la
        # versión actual y reportaba drift falso. Con snapshot: comparación
        # siempre contra la versión usada en ese momento.
        # JSON: [{material_id, material_nombre, porcentaje}, ...]
        "ALTER TABLE producciones ADD COLUMN formula_snapshot_json TEXT",
    ]),
    (97, "Triggers BD invariantes Planta (Sebastián 10-may-2026 cero-error)", [
        # Trigger: BLOQUEAR movimientos con cantidad <= 0 o NULL.
        # Antes el endpoint POST /api/movimientos validaba, pero algunos
        # scripts internos podían insertar sin pasar por el endpoint. Esta
        # es defensa en profundidad: BD rechaza antes de aceptar.
        """CREATE TRIGGER IF NOT EXISTS trg_mov_cantidad_positiva
        BEFORE INSERT ON movimientos
        FOR EACH ROW
        WHEN NEW.cantidad IS NULL OR NEW.cantidad <= 0
        BEGIN
            SELECT RAISE(ABORT, 'cantidad debe ser > 0 (no NULL ni cero ni negativo)');
        END""",
        # Trigger: BLOQUEAR movimientos con tipo inválido. Solo permitidos:
        # Entrada, Salida, Ajuste. Cualquier typo o valor inventado rechazado.
        """CREATE TRIGGER IF NOT EXISTS trg_mov_tipo_valido
        BEFORE INSERT ON movimientos
        FOR EACH ROW
        WHEN NEW.tipo NOT IN ('Entrada','Salida','Ajuste')
        BEGIN
            SELECT RAISE(ABORT, 'tipo invalido (debe ser Entrada/Salida/Ajuste)');
        END""",
        # Trigger: BLOQUEAR movimientos sin material_id (huérfanos absolutos).
        # No bloqueo "material_id no está en maestro_mps" porque algunos
        # legacy lo permiten (movs históricos de MPs archivadas). Solo bloqueo
        # NULL/vacío que es claramente bug.
        """CREATE TRIGGER IF NOT EXISTS trg_mov_material_id_requerido
        BEFORE INSERT ON movimientos
        FOR EACH ROW
        WHEN NEW.material_id IS NULL OR TRIM(NEW.material_id) = ''
        BEGIN
            SELECT RAISE(ABORT, 'material_id requerido (no puede ser vacio)');
        END""",
        # Trigger: BLOQUEAR formula_items con porcentaje claramente inválido.
        # Acepta 0 (item placeholder sin descuento) y hasta 100. Solo rechaza
        # NEGATIVO o > 100 que no tienen sentido cosmético/regulatorio.
        """CREATE TRIGGER IF NOT EXISTS trg_fi_porcentaje_valido
        BEFORE INSERT ON formula_items
        FOR EACH ROW
        WHEN NEW.porcentaje IS NOT NULL AND (NEW.porcentaje < 0 OR NEW.porcentaje > 100)
        BEGIN
            SELECT RAISE(ABORT, 'porcentaje fuera de rango [0,100]');
        END""",
        # Trigger: prevenir UPDATE que llevaría porcentaje fuera de rango.
        """CREATE TRIGGER IF NOT EXISTS trg_fi_porcentaje_valido_upd
        BEFORE UPDATE OF porcentaje ON formula_items
        FOR EACH ROW
        WHEN NEW.porcentaje IS NOT NULL AND (NEW.porcentaje < 0 OR NEW.porcentaje > 100)
        BEGIN
            SELECT RAISE(ABORT, 'UPDATE porcentaje fuera de rango [0,100]');
        END""",
        # Trigger: BLOQUEAR maestro_mps con codigo_mp vacío.
        """CREATE TRIGGER IF NOT EXISTS trg_mps_codigo_requerido
        BEFORE INSERT ON maestro_mps
        FOR EACH ROW
        WHEN NEW.codigo_mp IS NULL OR TRIM(NEW.codigo_mp) = ''
        BEGIN
            SELECT RAISE(ABORT, 'codigo_mp requerido (no puede ser vacio)');
        END""",
        # Trigger: BLOQUEAR stock_minimo negativo en maestro_mps.
        """CREATE TRIGGER IF NOT EXISTS trg_mps_stock_min_no_negativo
        BEFORE INSERT ON maestro_mps
        FOR EACH ROW
        WHEN NEW.stock_minimo IS NOT NULL AND NEW.stock_minimo < 0
        BEGIN
            SELECT RAISE(ABORT, 'stock_minimo no puede ser negativo');
        END""",
        """CREATE TRIGGER IF NOT EXISTS trg_mps_stock_min_no_negativo_upd
        BEFORE UPDATE OF stock_minimo ON maestro_mps
        FOR EACH ROW
        WHEN NEW.stock_minimo IS NOT NULL AND NEW.stock_minimo < 0
        BEGIN
            SELECT RAISE(ABORT, 'UPDATE stock_minimo no puede ser negativo');
        END""",
        # Trigger: BLOQUEAR conteo_items con stock_fisico negativo (físico
        # nunca puede ser < 0).
        """CREATE TRIGGER IF NOT EXISTS trg_conteo_stock_fisico_no_negativo
        BEFORE INSERT ON conteo_items
        FOR EACH ROW
        WHEN NEW.stock_fisico IS NOT NULL AND NEW.stock_fisico < 0
        BEGIN
            SELECT RAISE(ABORT, 'stock_fisico no puede ser negativo (lo que cuentas no puede ser negativo)');
        END""",
    ]),
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
    (79, "Bloqueo semanal lunes 7am (Sebastián 1-may-2026 · todo automático)", [
        # Sebastián 1-may-2026: 'el lunes 7am todo debe estar programado y
        # bloqueado · jefe de producción no hace nada · solo entra y ve'.
        # Producciones bloqueadas no son re-asignables hasta desbloquear.
        "ALTER TABLE produccion_programada ADD COLUMN bloqueado_at TEXT",
        "ALTER TABLE produccion_programada ADD COLUMN bloqueado_por TEXT DEFAULT ''",
        "ALTER TABLE produccion_programada ADD COLUMN semana_workflow_id TEXT DEFAULT ''",
        "CREATE INDEX IF NOT EXISTS idx_pp_bloq ON produccion_programada(bloqueado_at)",
        # Tabla histórico de workflows lunes 7am
        """CREATE TABLE IF NOT EXISTS workflow_lunes_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ejecutado_at TEXT NOT NULL DEFAULT (datetime('now')),
            ejecutado_por TEXT NOT NULL DEFAULT 'cron-lunes-7am',
            fecha_lunes TEXT NOT NULL,
            producciones_bloqueadas INTEGER DEFAULT 0,
            sincronizadas INTEGER DEFAULT 0,
            asignadas INTEGER DEFAULT 0,
            limpiezas_creadas INTEGER DEFAULT 0,
            email_enviado INTEGER DEFAULT 0,
            error TEXT,
            payload_json TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_wll_lunes ON workflow_lunes_log(fecha_lunes DESC)",
    ]),
    (80, "Índices de performance planta + gcal_event_id (Sebastián 1-may-2026)", [
        # Auditoría: queries filtraban por semana_workflow_id sin índice.
        "CREATE INDEX IF NOT EXISTS idx_pp_workflow ON produccion_programada(semana_workflow_id)",
        # Para dedupe robusto si en futuro se reactiva sync (por ahora Calendar-first)
        "ALTER TABLE produccion_programada ADD COLUMN gcal_event_id TEXT DEFAULT ''",
        "CREATE INDEX IF NOT EXISTS idx_pp_gcal ON produccion_programada(gcal_event_id)",
        # Índice para queries del centro-mando que filtran por fecha + estado
        "CREATE INDEX IF NOT EXISTS idx_pp_fecha_estado ON produccion_programada(fecha_programada, estado)",
    ]),
    (138, "Performance: indexes faltantes detectados por health/critical-paths", [
        # Sebastián 7-may-2026: dashboard zero-error detectó que estos 5
        # indexes no estaban creados. Sin ellos las queries de movimientos
        # por material/lote/fecha hacen full table scan en una tabla con
        # decenas de miles de filas · degrade real de performance.
        "CREATE INDEX IF NOT EXISTS idx_mov_material ON movimientos(material_id)",
        "CREATE INDEX IF NOT EXISTS idx_mov_lote ON movimientos(material_id, lote)",
        "CREATE INDEX IF NOT EXISTS idx_mov_fecha ON movimientos(fecha DESC)",
        "CREATE INDEX IF NOT EXISTS idx_oc_estado ON ordenes_compra(estado, fecha DESC)",
        "CREATE INDEX IF NOT EXISTS idx_sol_estado ON solicitudes_compra(estado, fecha DESC)",
    ]),

    (96, "agent_memory: memoria persistente para agentes IA (zero-error sprint)", [
        # Sebastián 7-may-2026: tabla simple key-value que los agentes IA
        # usan entre sesiones. Resuelve el problema de "amnesia entre
        # sesiones" sin depender de la memoria del LLM.
        #
        # Uso típico:
        #   agent_memory.set('last_deploy_commit', 'abc123', 'release')
        #   agent_memory.get('last_deploy_commit')
        #   agent_memory.list(category='release', limit=10)
        #
        # Categorías sugeridas:
        #   release · último deploy, último build, último rollback
        #   bug_pattern · síntoma + causa + fix conocidos
        #   user_preference · "Sebastián prefiere gramos, no kg"
        #   blocker · cosas pendientes que afectan futuras decisiones
        #   regression · golden path que rompió y cómo se arregló
        """CREATE TABLE IF NOT EXISTS agent_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'general',
            created_by TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
            UNIQUE(key)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_agent_memory_category ON agent_memory(category, updated_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_agent_memory_updated ON agent_memory(updated_at DESC)",
    ]),

    (95, "Animus inventario fisico: baseline + movimientos (asistente Daniela)", [
        # Sebastian 3-may-2026: la asistente cuenta inventario fisico cada
        # tanto y siempre hay desfase con Shopify. Solucion: ecuacion
        # contable.
        #   stock_esperado(sku) = baseline + Σ(entradas) − Σ(ventas_shopify) − Σ(salidas_otras)
        # Si conteo_fisico ≠ stock_esperado → discrepancia rastreable.
        #
        # Tabla 1: baseline · cuanto habia en una fecha de inicio (snapshot 1 vez)
        """CREATE TABLE IF NOT EXISTS animus_inventario_baseline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL UNIQUE,
            descripcion TEXT,
            unidades_baseline INTEGER NOT NULL,
            fecha_baseline TEXT NOT NULL,
            creado_por TEXT,
            observaciones TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        # Tabla 2: movimientos · TODO movimiento entre baseline y ahora
        """CREATE TABLE IF NOT EXISTS animus_inventario_movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN
                ('ENTRADA','SALIDA','SHOPIFY_VENTA','CONTEO','AJUSTE','BASELINE')),
            cantidad INTEGER NOT NULL,
            fecha TEXT NOT NULL DEFAULT (date('now')),
            origen TEXT,
            referencia TEXT,
            motivo TEXT,
            usuario TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        # Index para calcular esperado por SKU rapido
        "CREATE INDEX IF NOT EXISTS idx_aim_sku_fecha ON animus_inventario_movimientos(sku, fecha DESC)",
        "CREATE INDEX IF NOT EXISTS idx_aim_tipo_fecha ON animus_inventario_movimientos(tipo, fecha DESC)",
        # Tabla 3: asignaciones de conteo ciclico (cron diario)
        """CREATE TABLE IF NOT EXISTS animus_conteos_asignados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL,
            fecha_asignado TEXT NOT NULL DEFAULT (date('now')),
            asignado_a TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente'
                CHECK(estado IN ('pendiente','contado','omitido')),
            cantidad_fisica INTEGER,
            cantidad_esperada INTEGER,
            diferencia INTEGER,
            motivo_diferencia TEXT,
            contado_en TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_aca_estado_fecha ON animus_conteos_asignados(estado, fecha_asignado DESC)",
        "CREATE INDEX IF NOT EXISTS idx_aca_sku ON animus_conteos_asignados(sku, fecha_asignado DESC)",
    ]),
    (94, "Re-aplicar indexes mig 92 que fallaron por orden (tablas creadas en 87/88)", [
        # Bug detectado 2-may-2026: el array de MIGRATIONS está en orden
        # parcial · 92 (indexes sobre desviaciones/control_cambios) corre
        # ANTES de 87 (crea desviaciones) y 88 (crea control_cambios).
        # Como BENIGN_PATTERNS incluye "no such table", CREATE INDEX falla
        # silenciosamente. Esta migración 94 los re-crea (CREATE IF NOT EXISTS
        # es idempotente · si ya existen no rompe).
        "CREATE INDEX IF NOT EXISTS idx_desv_detectado ON desviaciones(detectado_por, estado)",
        "CREATE INDEX IF NOT EXISTS idx_chg_solicitante ON control_cambios(solicitado_por, estado)",
        "CREATE INDEX IF NOT EXISTS idx_chg_responsable ON control_cambios(responsable_implementacion, estado) WHERE responsable_implementacion IS NOT NULL",
        "CREATE INDEX IF NOT EXISTS idx_qc_recibido ON quejas_clientes(recibido_por, estado)",
        "CREATE INDEX IF NOT EXISTS idx_rcl_iniciado ON recalls(iniciado_por, estado)",
    ]),
    (93, "Performance: indexes faltantes en pedidos + clientes (audit zero-error)", [
        # Audit zero-error 2-may-2026: clientes.ficha360 hacía full scan por cliente
        # porque pedidos.cliente_id no tenía índice. Con 1k pedidos cada GET llamaba
        # 3 full scans (stats + pedidos_recientes + top_skus).
        "CREATE INDEX IF NOT EXISTS idx_pedidos_cliente ON pedidos(cliente_id, fecha DESC)",
        "CREATE INDEX IF NOT EXISTS idx_pedidos_items_numero ON pedidos_items(numero_pedido)",
        "CREATE INDEX IF NOT EXISTS idx_pedidos_estado_fecha ON pedidos(estado, fecha DESC)",
        "CREATE INDEX IF NOT EXISTS idx_despachos_cliente ON despachos(cliente_id, fecha DESC)",
    ]),
    (91, "Audit log regulatorio: agregar columnas antes/despues + indexes", [
        # Sebastián 2-may-2026: los inserts en aseguramiento.py usaban
        # columnas `antes` y `despues` que no existían en audit_log
        # (creado en init_db() con schema mínimo). Como estaban envueltos
        # en `try: except: pass`, INVIMA tiene cero trazabilidad de cierres
        # regulatorios desde el commit 60e399f. Esta migración cierra el gap.

        # Agregar columnas SIN romper inserts existentes
        "ALTER TABLE audit_log ADD COLUMN antes TEXT",
        "ALTER TABLE audit_log ADD COLUMN despues TEXT",

        # Indexes para búsqueda rápida en auditoría INVIMA
        "CREATE INDEX IF NOT EXISTS idx_audit_accion ON audit_log(accion, fecha DESC)",
        "CREATE INDEX IF NOT EXISTS idx_audit_registro ON audit_log(registro_id, fecha DESC)",
        "CREATE INDEX IF NOT EXISTS idx_audit_usuario ON audit_log(usuario, fecha DESC)",

        # Backfill: si hay timestamps viejos en formato no ISO, no tocamos
        # (el campo `fecha` es TEXT). Las nuevas filas usarán datetime('now').
    ]),
    (92, "Aseguramiento: indexes de performance para mis-tareas (4 columnas frecuentes)", [
        # Sebastián 2-may-2026: auditoría detectó que mis-tareas hace
        # full-scan en columnas de "creado_por" porque no había index.
        # Con 1k-10k rows, esto pasaba de 1ms a 50-100ms por columna.
        "CREATE INDEX IF NOT EXISTS idx_desv_detectado ON desviaciones(detectado_por, estado)",
        "CREATE INDEX IF NOT EXISTS idx_chg_solicitante ON control_cambios(solicitado_por, estado)",
        "CREATE INDEX IF NOT EXISTS idx_chg_responsable ON control_cambios(responsable_implementacion, estado) WHERE responsable_implementacion IS NOT NULL",
        "CREATE INDEX IF NOT EXISTS idx_qc_recibido ON quejas_clientes(recibido_por, estado)",
        "CREATE INDEX IF NOT EXISTS idx_rcl_iniciado ON recalls(iniciado_por, estado)",
    ]),
    (90, "Aseguramiento: tabla recalls (ASG-PRO-004) retiro producto del mercado", [
        # Sebastián 2-may-2026: workflow de recall según ASG-PRO-004 + Resolución
        # 2214/2021 INVIMA. Cuando se descubre un defecto que pone en riesgo al
        # consumidor (vía desviación, queja, hallazgo interno), se inicia un
        # recall: clasificación (I/II/III), notificación INVIMA <24h si Clase I,
        # notificación a distribuidores, recolección del mercado, disposición
        # final (destrucción/reproceso) y reporte de efectividad.

        """CREATE TABLE IF NOT EXISTS recalls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE,
            fecha_inicio TEXT NOT NULL DEFAULT (date('now')),
            iniciado_por TEXT NOT NULL,
            origen TEXT NOT NULL DEFAULT 'otro'
              CHECK(origen IN ('desviacion','queja_cliente','hallazgo_interno',
                                'auditoria','reaccion_adversa','invima','otro')),
            origen_referencia TEXT,
            desviacion_id INTEGER,
            queja_id INTEGER,
            producto TEXT NOT NULL,
            lotes_afectados TEXT NOT NULL,
            cantidad_fabricada INTEGER,
            cantidad_distribuida INTEGER,
            motivo TEXT NOT NULL,
            riesgo_descripcion TEXT,
            clase_recall TEXT
              CHECK(clase_recall IN ('clase_I','clase_II','clase_III') OR clase_recall IS NULL),
            alcance_geografico TEXT
              CHECK(alcance_geografico IN ('local','regional','nacional','internacional')
                    OR alcance_geografico IS NULL),
            clasificado_por TEXT,
            clasificado_at TEXT,
            justificacion_clasificacion TEXT,
            notificacion_invima_at TEXT,
            notificacion_invima_ref TEXT,
            notificacion_invima_por TEXT,
            notificacion_distribuidores_at TEXT,
            distribuidores_notificados TEXT,
            notificacion_distribuidores_por TEXT,
            recoleccion_inicio_at TEXT,
            recoleccion_completada_at TEXT,
            cantidad_recolectada INTEGER,
            disposicion_final TEXT
              CHECK(disposicion_final IN ('destruccion','reproceso','devolver_proveedor','cuarentena')
                    OR disposicion_final IS NULL),
            disposicion_descripcion TEXT,
            efectividad_porcentaje INTEGER,
            efectividad_descripcion TEXT,
            estado TEXT NOT NULL DEFAULT 'iniciado'
              CHECK(estado IN ('iniciado','clasificado','invima_notificado',
                                'distribuidores_notificados','en_recoleccion',
                                'completado','cerrado','cancelado')),
            fecha_cierre TEXT,
            cerrado_por TEXT,
            observaciones_cierre TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            actualizado_en TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_rcl_estado ON recalls(estado, fecha_inicio DESC)",
        "CREATE INDEX IF NOT EXISTS idx_rcl_clase ON recalls(clase_recall, estado)",
        "CREATE INDEX IF NOT EXISTS idx_rcl_lotes ON recalls(lotes_afectados, fecha_inicio DESC)",

        # Eventos del workflow (timeline)
        """CREATE TABLE IF NOT EXISTS recalls_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recall_id INTEGER NOT NULL,
            evento_tipo TEXT NOT NULL,
            estado_anterior TEXT,
            estado_nuevo TEXT,
            usuario TEXT,
            comentario TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (recall_id) REFERENCES recalls(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_rcl_ev ON recalls_eventos(recall_id, creado_en)",
    ]),
    (89, "Aseguramiento: tabla quejas_clientes (ASG-PRO-013) workflow completo", [
        # Sebastián 2-may-2026: workflow de quejas/reclamos según ASG-PRO-013.
        # Toda queja entra como 'nueva' → triaje (severidad + ¿desviación? ¿recall?)
        # → investigación → respuesta al cliente → cierre con análisis efectividad.
        # Si severidad crítica con impacto en salud → notificación INVIMA inmediata.

        """CREATE TABLE IF NOT EXISTS quejas_clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE,
            fecha_recepcion TEXT NOT NULL DEFAULT (date('now')),
            recibido_por TEXT NOT NULL,
            canal TEXT NOT NULL DEFAULT 'otro'
              CHECK(canal IN ('email','telefono','whatsapp','redes_sociales',
                              'presencial','distribuidor','formulario_web','otro')),
            cliente_nombre TEXT NOT NULL,
            cliente_contacto TEXT,
            cliente_tipo TEXT
              CHECK(cliente_tipo IN ('consumidor_final','distribuidor','retail','medico','otro')
                    OR cliente_tipo IS NULL),
            producto TEXT,
            lote TEXT,
            fecha_compra TEXT,
            establecimiento_compra TEXT,
            tipo_queja TEXT NOT NULL DEFAULT 'otro'
              CHECK(tipo_queja IN ('reaccion_adversa','calidad_producto','envase_empaque',
                                    'cantidad_volumen','fecha_vencimiento',
                                    'sabor_olor_textura','eficacia','documentacion',
                                    'servicio','otro')),
            descripcion TEXT NOT NULL,
            impacto_salud INTEGER NOT NULL DEFAULT 0,
            severidad TEXT
              CHECK(severidad IN ('critica','mayor','menor','informativa') OR severidad IS NULL),
            triaje_descripcion TEXT,
            triaje_por TEXT,
            triaje_at TEXT,
            requiere_desviacion INTEGER NOT NULL DEFAULT 0,
            desviacion_id INTEGER,
            requiere_recall INTEGER NOT NULL DEFAULT 0,
            causa_raiz TEXT,
            investigacion_por TEXT,
            investigacion_at TEXT,
            respuesta_descripcion TEXT,
            respuesta_canal TEXT
              CHECK(respuesta_canal IN ('email','telefono','whatsapp','presencial',
                                          'carta','formulario_web','otro')
                    OR respuesta_canal IS NULL),
            respondido_por TEXT,
            respondido_at TEXT,
            fecha_compromiso TEXT,
            cliente_satisfecho INTEGER,
            accion_correctiva TEXT,
            cerrado_por TEXT,
            fecha_cierre TEXT,
            observaciones_cierre TEXT,
            estado TEXT NOT NULL DEFAULT 'nueva'
              CHECK(estado IN ('nueva','en_triaje','en_investigacion',
                                'respondida','cerrada','rechazada')),
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            actualizado_en TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_qc_estado ON quejas_clientes(estado, fecha_recepcion DESC)",
        "CREATE INDEX IF NOT EXISTS idx_qc_severidad ON quejas_clientes(severidad, estado)",
        "CREATE INDEX IF NOT EXISTS idx_qc_lote ON quejas_clientes(lote, fecha_recepcion DESC)",
        "CREATE INDEX IF NOT EXISTS idx_qc_salud ON quejas_clientes(impacto_salud, estado) WHERE impacto_salud=1",

        # Eventos del workflow (timeline)
        """CREATE TABLE IF NOT EXISTS quejas_clientes_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            queja_id INTEGER NOT NULL,
            evento_tipo TEXT NOT NULL,
            estado_anterior TEXT,
            estado_nuevo TEXT,
            usuario TEXT,
            comentario TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (queja_id) REFERENCES quejas_clientes(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_qc_ev ON quejas_clientes_eventos(queja_id, creado_en)",
    ]),
    (88, "Aseguramiento: tabla control_cambios (ASG-PRO-007) workflow completo", [
        # Sebastián 1-may-2026: workflow estructurado de control de cambios
        # según ASG-PRO-007. Si toca BPM → notificación INVIMA. Cumple
        # Resolución 2214/2021 sobre cambios reportables.

        """CREATE TABLE IF NOT EXISTS control_cambios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE,
            fecha_solicitud TEXT NOT NULL DEFAULT (date('now')),
            solicitado_por TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'otro'
              CHECK(tipo IN ('formulacion','proceso','equipo','instalacion',
                              'proveedor','documental','sistema','envase','otro')),
            titulo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            justificacion TEXT,
            impacto_bpm INTEGER NOT NULL DEFAULT 0,
            impacto_regulatorio INTEGER NOT NULL DEFAULT 0,
            areas_afectadas TEXT,
            severidad TEXT
              CHECK(severidad IN ('mayor','menor') OR severidad IS NULL),
            evaluado_por TEXT,
            evaluado_at TEXT,
            evaluacion_descripcion TEXT,
            aprobado_por TEXT,
            aprobado_at TEXT,
            aprobacion_observaciones TEXT,
            requiere_invima INTEGER NOT NULL DEFAULT 0,
            notificacion_invima_at TEXT,
            notificacion_invima_ref TEXT,
            plan_implementacion TEXT,
            fecha_implementacion_propuesta TEXT,
            responsable_implementacion TEXT,
            implementado_at TEXT,
            implementado_por TEXT,
            verificacion_post TEXT,
            verificado_por TEXT,
            verificado_at TEXT,
            verificacion_ok INTEGER,
            estado TEXT NOT NULL DEFAULT 'solicitado'
              CHECK(estado IN ('solicitado','en_evaluacion','aprobado','rechazado',
                                'en_implementacion','implementado','cerrado')),
            fecha_cierre TEXT,
            cerrado_por TEXT,
            observaciones_cierre TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            actualizado_en TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_chg_estado ON control_cambios(estado, fecha_solicitud DESC)",
        "CREATE INDEX IF NOT EXISTS idx_chg_severidad ON control_cambios(severidad, estado)",
        "CREATE INDEX IF NOT EXISTS idx_chg_invima ON control_cambios(requiere_invima, estado) WHERE requiere_invima=1",

        # Eventos del workflow (timeline)
        """CREATE TABLE IF NOT EXISTS control_cambios_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cambio_id INTEGER NOT NULL,
            evento_tipo TEXT NOT NULL,
            estado_anterior TEXT,
            estado_nuevo TEXT,
            usuario TEXT,
            comentario TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (cambio_id) REFERENCES control_cambios(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_chg_ev ON control_cambios_eventos(cambio_id, creado_en)",
    ]),
    (87, "Aseguramiento: tabla desviaciones (ASG-PRO-001) workflow completo", [
        # Sebastián 1-may-2026: workflow estructurado de manejo de desviaciones
        # según ASG-PRO-001. Plazos: crítica reportar 4h · clasificación 24h ·
        # investigación 5d · CAPA 10-15d. Cumplimiento Resolución 2214/2021.

        """CREATE TABLE IF NOT EXISTS desviaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE,
            fecha_deteccion TEXT NOT NULL DEFAULT (date('now')),
            hora_deteccion TEXT,
            detectado_por TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'otra'
              CHECK(tipo IN ('proceso','equipo','instalacion','sistema_agua','ambiental',
                              'documental','personal','materia_prima','envase','otra')),
            area_origen TEXT,
            descripcion TEXT NOT NULL,
            contencion_inmediata TEXT,
            impacto_producto INTEGER NOT NULL DEFAULT 0,
            lotes_afectados TEXT,
            clasificacion TEXT
              CHECK(clasificacion IN ('critica','mayor','menor','informativa') OR clasificacion IS NULL),
            clasificado_por TEXT,
            clasificado_at TEXT,
            justificacion_clasificacion TEXT,
            metodo_investigacion TEXT
              CHECK(metodo_investigacion IN ('5_porques','ishikawa','arbol_decision','otro') OR metodo_investigacion IS NULL),
            causa_raiz_descripcion TEXT,
            investigado_por TEXT,
            investigacion_at TEXT,
            capa_descripcion TEXT,
            capa_responsable TEXT,
            capa_fecha_limite TEXT,
            capa_implementado_at TEXT,
            verificacion_efectividad TEXT,
            verificado_at TEXT,
            verificado_por TEXT,
            efectividad_ok INTEGER,
            estado TEXT NOT NULL DEFAULT 'detectada'
              CHECK(estado IN ('detectada','clasificada','en_investigacion',
                                'capa_propuesto','capa_implementado','cerrada','rechazada')),
            fecha_cierre TEXT,
            cerrado_por TEXT,
            observaciones_cierre TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            actualizado_en TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_desv_estado ON desviaciones(estado, fecha_deteccion DESC)",
        "CREATE INDEX IF NOT EXISTS idx_desv_clasif ON desviaciones(clasificacion, estado)",
        "CREATE INDEX IF NOT EXISTS idx_desv_fecha ON desviaciones(fecha_deteccion DESC)",
        "CREATE INDEX IF NOT EXISTS idx_desv_area ON desviaciones(area_origen, estado)",

        # Eventos del workflow (timeline visible)
        """CREATE TABLE IF NOT EXISTS desviaciones_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            desviacion_id INTEGER NOT NULL,
            evento_tipo TEXT NOT NULL,
            estado_anterior TEXT,
            estado_nuevo TEXT,
            usuario TEXT,
            comentario TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (desviacion_id) REFERENCES desviaciones(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_desv_ev ON desviaciones_eventos(desviacion_id, creado_en)",
    ]),
    (86, "Aseguramiento: SGD electrónico · sgd_documentos + sgd_versiones + sgd_capacitaciones", [
        # Sebastián 1-may-2026: SGD electrónico vivo. Reemplaza 124 .docx
        # sueltos en Downloads por catálogo central · 32 docs vivos vs ~92 borradores
        # detectados como duplicados. Cumple ASG-NOR-001 (norma documental).

        # Documento principal (procedimiento, norma, manual, política, formato, etc.)
        """CREATE TABLE IF NOT EXISTS sgd_documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            area TEXT NOT NULL,
            tipo_doc TEXT NOT NULL,
            numero INTEGER,
            subtipo TEXT,
            titulo TEXT NOT NULL,
            descripcion TEXT,
            padre_codigo TEXT,
            version_actual TEXT NOT NULL DEFAULT '1',
            archivo_pdf_url TEXT,
            archivo_origen TEXT,
            fecha_creacion TEXT,
            fecha_aprobacion TEXT,
            vigente_desde TEXT,
            proxima_revision TEXT,
            estado TEXT NOT NULL DEFAULT 'vigente'
              CHECK(estado IN ('borrador','revision','vigente','obsoleto','retirado','conflicto')),
            elaborado_por TEXT,
            revisado_por TEXT,
            aprobado_por TEXT,
            observaciones TEXT,
            creado_por TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            actualizado_en TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_sgd_area ON sgd_documentos(area, estado)",
        "CREATE INDEX IF NOT EXISTS idx_sgd_tipo ON sgd_documentos(tipo_doc, estado)",
        "CREATE INDEX IF NOT EXISTS idx_sgd_proxima ON sgd_documentos(proxima_revision) WHERE estado='vigente'",
        "CREATE INDEX IF NOT EXISTS idx_sgd_padre ON sgd_documentos(padre_codigo)",

        # Histórico de versiones (cada versión aprobada queda registrada)
        """CREATE TABLE IF NOT EXISTS sgd_versiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL,
            version TEXT NOT NULL,
            fecha_aprobacion TEXT,
            archivo_url TEXT,
            archivo_origen TEXT,
            motivo_cambio TEXT,
            aprobado_por TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(codigo, version)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_sgd_ver_codigo ON sgd_versiones(codigo, fecha_aprobacion DESC)",

        # Capacitaciones: quién leyó/firmó qué versión de qué SOP (evidencia INVIMA)
        """CREATE TABLE IF NOT EXISTS sgd_capacitaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sgd_codigo TEXT NOT NULL,
            sgd_version TEXT NOT NULL,
            persona_username TEXT NOT NULL,
            asignado_at TEXT NOT NULL DEFAULT (datetime('now')),
            leido_at TEXT,
            firmado_at TEXT,
            firma_hash TEXT,
            evaluado INTEGER DEFAULT 0,
            nota_evaluacion REAL,
            nota_minima REAL,
            estado TEXT NOT NULL DEFAULT 'asignada'
              CHECK(estado IN ('asignada','leida','firmada','aprobada','reprobada','vencida')),
            fecha_limite TEXT,
            asignado_por TEXT,
            UNIQUE(sgd_codigo, sgd_version, persona_username)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_sgd_cap_persona ON sgd_capacitaciones(persona_username, estado)",
        "CREATE INDEX IF NOT EXISTS idx_sgd_cap_codigo ON sgd_capacitaciones(sgd_codigo, sgd_version)",

        # Conflictos detectados (códigos repetidos con temas distintos · 14 detectados)
        """CREATE TABLE IF NOT EXISTS sgd_conflictos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL,
            archivos_detectados TEXT,
            temas_detectados TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente'
              CHECK(estado IN ('pendiente','en_revision','resuelto','ignorado')),
            resolucion TEXT,
            resuelto_por TEXT,
            resuelto_at TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_sgd_conf_estado ON sgd_conflictos(estado, codigo)",
    ]),
    (85, "Calidad VIVA: equipos_eventos (hoja de vida) + equipos_cronograma (calendario 2026)", [
        # Sebastián 1-may-2026: Calidad necesita VER cuándo vence cada equipo
        # y BLOQUEAR si calibración expiró. La tabla `calibraciones_instrumentos`
        # existente sirve para 5 instrumentos genéricos, pero los 104 equipos
        # del seed (`equipos_planta`) no tienen tracking de calibración/
        # mantenimiento. Esta migración agrega tracking por código de equipo
        # del listado maestro real (BL-PRD-001, AG-PRD-001, etc.).

        # Hoja de vida unificada por equipo: cada calibración, verificación,
        # mantenimiento, baja, etc. queda registrado.
        """CREATE TABLE IF NOT EXISTS equipos_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_codigo TEXT NOT NULL,
            tipo_evento TEXT NOT NULL
              CHECK(tipo_evento IN (
                'calibracion','verificacion_diaria','verificacion_semestral',
                'mantenimiento_preventivo','mantenimiento_correctivo',
                'baja','reparacion','validacion','reactivacion'
              )),
            fecha TEXT NOT NULL DEFAULT (date('now')),
            fecha_proxima TEXT,
            estado TEXT NOT NULL DEFAULT 'completado'
              CHECK(estado IN ('completado','programado','en_curso','cancelado')),
            responsable TEXT,
            empresa_externa TEXT,
            certificado_url TEXT,
            resultado TEXT,
            observaciones TEXT,
            creado_por TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_eq_ev_codigo ON equipos_eventos(equipo_codigo, fecha DESC)",
        "CREATE INDEX IF NOT EXISTS idx_eq_ev_proxima ON equipos_eventos(fecha_proxima)",
        "CREATE INDEX IF NOT EXISTS idx_eq_ev_tipo ON equipos_eventos(tipo_evento, fecha DESC)",

        # Cronograma anual: para cada (equipo, año, mes) qué tipo de actividad
        # toca. Importado del xlsx PRD-PRO-004-C01 vía endpoint o seed manual.
        """CREATE TABLE IF NOT EXISTS equipos_cronograma (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_codigo TEXT NOT NULL,
            anio INTEGER NOT NULL DEFAULT 2026,
            mes INTEGER NOT NULL CHECK(mes BETWEEN 1 AND 12),
            tipo_actividad TEXT NOT NULL
              CHECK(tipo_actividad IN ('preventivo','correctivo','verificacion','calibracion')),
            estado TEXT NOT NULL DEFAULT 'programado'
              CHECK(estado IN ('programado','completado','reprogramado','cancelado')),
            fecha_completado TEXT,
            completado_por TEXT,
            evento_id INTEGER,
            observaciones TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(equipo_codigo, anio, mes, tipo_actividad)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_eq_cron_mes ON equipos_cronograma(anio, mes, estado)",
        "CREATE INDEX IF NOT EXISTS idx_eq_cron_codigo ON equipos_cronograma(equipo_codigo, anio)",
    ]),
    (84, "UNIQUE constraints contra duplicados de numero (OC/SOL/factura)", [
        # Sebastián 1-may-2026 round 3: race condition en MAX(numero)+1.
        # Si 2 requests concurrentes generan número, ambos pueden insertar el
        # mismo. UNIQUE INDEX previene el INSERT duplicado · el segundo falla
        # con IntegrityError y debe reintentarse en código.
        #
        # IMPORTANTE: Si en producción YA hay duplicados (race ya ocurrió),
        # el CREATE UNIQUE INDEX falla y crashea el deploy. Por eso primero
        # renombramos los duplicados (mantenemos el ID más bajo, los demás
        # quedan con sufijo "-DUP-{id}") · esto preserva data y deja audit
        # trail visible para que humano revise.
        """UPDATE ordenes_compra SET numero_oc = numero_oc || '-DUP-' || id
        WHERE id IN (
            SELECT id FROM ordenes_compra o1
            WHERE EXISTS (
                SELECT 1 FROM ordenes_compra o2
                WHERE o2.numero_oc = o1.numero_oc AND o2.id < o1.id
            )
        )""",
        """UPDATE solicitudes_compra SET numero = numero || '-DUP-' || id
        WHERE id IN (
            SELECT id FROM solicitudes_compra s1
            WHERE EXISTS (
                SELECT 1 FROM solicitudes_compra s2
                WHERE s2.numero = s1.numero AND s2.id < s1.id
            )
        )""",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_ordenes_compra_numero ON ordenes_compra(numero_oc)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_solicitudes_compra_numero ON solicitudes_compra(numero)",
    ]),
    (83, "Trigger BD: proteger operarios_planta.fija_en_dispensacion · log cambios", [
        # Sebastián 1-may-2026 round 3: si alguien hace UPDATE manual quitando
        # el flag a Mayerlin (UPDATE operarios_planta SET fija_en_dispensacion=0
        # WHERE id=...), la regla dura cae sin alarma. Trigger BEFORE UPDATE
        # registra el cambio en audit_log para visibilidad. NO bloquea (admin
        # legítimamente puede querer transferir el rol a otra persona) pero
        # deja rastro auditable.
        """CREATE TABLE IF NOT EXISTS operarios_fija_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operario_id INTEGER NOT NULL,
            valor_anterior INTEGER NOT NULL,
            valor_nuevo INTEGER NOT NULL,
            cambiado_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        """CREATE TRIGGER IF NOT EXISTS trg_op_fija_audit
        AFTER UPDATE OF fija_en_dispensacion ON operarios_planta
        FOR EACH ROW WHEN OLD.fija_en_dispensacion != NEW.fija_en_dispensacion
        BEGIN
            INSERT INTO operarios_fija_audit (operario_id, valor_anterior, valor_nuevo)
            VALUES (NEW.id, OLD.fija_en_dispensacion, NEW.fija_en_dispensacion);
        END""",
        # Si se INTENTA setear fija_en_dispensacion=1 a un operario marcado
        # como jefe, eso es contradictorio (jefe no rota · no es operario activo).
        # Bloquear con mensaje claro.
        """CREATE TRIGGER IF NOT EXISTS trg_op_fija_no_jefe
        BEFORE UPDATE OF fija_en_dispensacion ON operarios_planta
        FOR EACH ROW WHEN NEW.fija_en_dispensacion = 1
          AND COALESCE(NEW.es_jefe_produccion, OLD.es_jefe_produccion, 0) = 1
        BEGIN SELECT RAISE(ABORT, 'fija_en_dispensacion=1 incompatible con es_jefe_produccion=1'); END""",
        """CREATE TRIGGER IF NOT EXISTS trg_op_fija_no_jefe_ins
        BEFORE INSERT ON operarios_planta
        FOR EACH ROW WHEN NEW.fija_en_dispensacion = 1
          AND NEW.es_jefe_produccion = 1
        BEGIN SELECT RAISE(ABORT, 'fija_en_dispensacion=1 incompatible con es_jefe_produccion=1'); END""",
    ]),
    (82, "Triggers BD: enforce regla fija_en_dispensacion (defense-in-depth)", [
        # Sebastián 1-may-2026 round 2: enforce regla dura a nivel BD para que
        # NINGÚN path (UI manual, scripts, endpoints futuros) pueda asignar un
        # operario fija_en_dispensacion=1 a roles ≠ dispensación.
        # Estos triggers re-NULLean el campo si alguien intenta violarlo y
        # registran el intento en audit_log.
        """CREATE TRIGGER IF NOT EXISTS trg_pp_fija_elab_block
        BEFORE UPDATE OF operario_elaboracion_id ON produccion_programada
        FOR EACH ROW WHEN NEW.operario_elaboracion_id IS NOT NULL
          AND (SELECT COALESCE(fija_en_dispensacion,0) FROM operarios_planta
               WHERE id = NEW.operario_elaboracion_id) = 1
        BEGIN SELECT RAISE(ABORT, 'fija_en_dispensacion: este operario solo puede ir a dispensacion'); END""",
        """CREATE TRIGGER IF NOT EXISTS trg_pp_fija_env_block
        BEFORE UPDATE OF operario_envasado_id ON produccion_programada
        FOR EACH ROW WHEN NEW.operario_envasado_id IS NOT NULL
          AND (SELECT COALESCE(fija_en_dispensacion,0) FROM operarios_planta
               WHERE id = NEW.operario_envasado_id) = 1
        BEGIN SELECT RAISE(ABORT, 'fija_en_dispensacion: este operario solo puede ir a dispensacion'); END""",
        """CREATE TRIGGER IF NOT EXISTS trg_pp_fija_acond_block
        BEFORE UPDATE OF operario_acondicionamiento_id ON produccion_programada
        FOR EACH ROW WHEN NEW.operario_acondicionamiento_id IS NOT NULL
          AND (SELECT COALESCE(fija_en_dispensacion,0) FROM operarios_planta
               WHERE id = NEW.operario_acondicionamiento_id) = 1
        BEGIN SELECT RAISE(ABORT, 'fija_en_dispensacion: este operario solo puede ir a dispensacion'); END""",
        # Idem en INSERT
        """CREATE TRIGGER IF NOT EXISTS trg_pp_fija_elab_block_ins
        BEFORE INSERT ON produccion_programada
        FOR EACH ROW WHEN NEW.operario_elaboracion_id IS NOT NULL
          AND (SELECT COALESCE(fija_en_dispensacion,0) FROM operarios_planta
               WHERE id = NEW.operario_elaboracion_id) = 1
        BEGIN SELECT RAISE(ABORT, 'fija_en_dispensacion: este operario solo puede ir a dispensacion'); END""",
        """CREATE TRIGGER IF NOT EXISTS trg_pp_fija_env_block_ins
        BEFORE INSERT ON produccion_programada
        FOR EACH ROW WHEN NEW.operario_envasado_id IS NOT NULL
          AND (SELECT COALESCE(fija_en_dispensacion,0) FROM operarios_planta
               WHERE id = NEW.operario_envasado_id) = 1
        BEGIN SELECT RAISE(ABORT, 'fija_en_dispensacion: este operario solo puede ir a dispensacion'); END""",
        """CREATE TRIGGER IF NOT EXISTS trg_pp_fija_acond_block_ins
        BEFORE INSERT ON produccion_programada
        FOR EACH ROW WHEN NEW.operario_acondicionamiento_id IS NOT NULL
          AND (SELECT COALESCE(fija_en_dispensacion,0) FROM operarios_planta
               WHERE id = NEW.operario_acondicionamiento_id) = 1
        BEGIN SELECT RAISE(ABORT, 'fija_en_dispensacion: este operario solo puede ir a dispensacion'); END""",
    ]),
    (81, "Audit zero-error: cron_locks + indexes + rol_afinidad_config + UNIQUE cron_jobs_runs", [
        # Serialización de workers concurrentes en multi-cron. Antes: 2 workers
        # podían ejecutar el mismo job el mismo día (race en _ya_ejecutado_hoy).
        # cron_locks con TTL 2h: si crash sin liberar, se libera solo.
        """CREATE TABLE IF NOT EXISTS cron_locks (
            job_name TEXT PRIMARY KEY,
            locked_at TEXT NOT NULL DEFAULT (datetime('now')),
            locked_by TEXT
        )""",
        # Si en producción ya hay duplicados ok=1 mismo job+día (race ya
        # ocurrió pre-fix), mantener solo el más reciente para que el UNIQUE
        # INDEX pueda crearse. Los duplicados antiguos se preservan con
        # ok=2 (estado custom "duplicate-ignored") · no se borran.
        """UPDATE cron_jobs_runs SET ok = 2
        WHERE ok = 1 AND id IN (
            SELECT cjr1.id FROM cron_jobs_runs cjr1
            WHERE cjr1.ok = 1 AND EXISTS (
                SELECT 1 FROM cron_jobs_runs cjr2
                WHERE cjr2.ok = 1
                  AND cjr2.job_name = cjr1.job_name
                  AND date(cjr2.ejecutado_at) = date(cjr1.ejecutado_at)
                  AND cjr2.id > cjr1.id
            )
        )""",
        # Previene doble registro de éxito hoy (defensa secundaria al lock).
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_cjr_unique_ok_today "
        "ON cron_jobs_runs(job_name, date(ejecutado_at)) WHERE ok=1",
        # Tabla rol_afinidad_config: pesos para asignación de operarios.
        # Antes hardcoded en auto_plan.py:7256 y programacion.py:8450 (duplicado).
        # Ahora: una sola fuente. Si está vacía, código usa fallback hardcoded.
        """CREATE TABLE IF NOT EXISTS rol_afinidad_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rol_destino TEXT NOT NULL,
            rol_predeterminado TEXT NOT NULL,
            peso INTEGER NOT NULL DEFAULT 1,
            UNIQUE(rol_destino, rol_predeterminado)
        )""",
        # Seed AFINIDAD por defecto. Pesos: 4=preferido fuerte · 2=todero · 1=fallback.
        # Sin peso 3 (legacy buggy que dejaba caer Mayerlin en elaboracion).
        """INSERT OR IGNORE INTO rol_afinidad_config (rol_destino, rol_predeterminado, peso) VALUES
           ('dispensacion','dispensacion',4),('dispensacion','elaboracion',1),
           ('dispensacion','envasado',1),('dispensacion','acondicionamiento',1),
           ('dispensacion','todero',2),
           ('elaboracion','dispensacion',1),('elaboracion','elaboracion',4),
           ('elaboracion','envasado',1),('elaboracion','acondicionamiento',1),
           ('elaboracion','todero',2),
           ('envasado','envasado',4),('envasado','dispensacion',1),
           ('envasado','elaboracion',1),('envasado','acondicionamiento',1),
           ('envasado','todero',2),
           ('acondicionamiento','acondicionamiento',4),('acondicionamiento','envasado',2),
           ('acondicionamiento','dispensacion',1),('acondicionamiento','elaboracion',1),
           ('acondicionamiento','todero',2)""",
        # Índices que el audit detectó faltantes.
        "CREATE INDEX IF NOT EXISTS idx_areas_tipo ON areas_planta(tipo)",
        "CREATE INDEX IF NOT EXISTS idx_aso_creado ON animus_shopify_orders(creado_en)",
        "CREATE INDEX IF NOT EXISTS idx_pchk_prod ON produccion_checklist(produccion_id, item_tipo)",
        "CREATE INDEX IF NOT EXISTS idx_lpc_fecha_asig ON limpieza_profunda_calendario(fecha, asignado_a)",
        "CREATE INDEX IF NOT EXISTS idx_ccc_fecha_asig ON conteo_ciclico_calendario(fecha, asignado_a)",
    ]),
    (78, "Aliases Calendar · códigos cortos TRIAC/LBHA/CRETT/etc (Sebastián 1-may-2026)", [
        # Sebastián 1-may-2026: el Calendar usa códigos cortos en eventos
        # (TRIAC, LBHA, CRETT, NPHA, CMULP, EMLIM, CRCUREA, etc.) pero los
        # SKUs no tenían esos códigos como aliases → 0 match → IA no asignaba.
        # Sobrescribimos alias_calendar con lista comprensiva (código + nombres)
        # para máxima cobertura de matching.
        "UPDATE sku_planeacion_config SET alias_calendar='SUERO TRIACTIVE, TRIAC, TRIACTIVE, Suero TRIAC, Triactive Retinoid' WHERE producto_nombre='SUERO TRIACTIVE RETINOID NAD+'",
        "UPDATE sku_planeacion_config SET alias_calendar='LBHA, BHA 2%, Limpiador BHA, BHA, Limpiador Facial BHA' WHERE producto_nombre='LIMPIADOR FACIAL BHA 2%'",
        "UPDATE sku_planeacion_config SET alias_calendar='CRETT, Contorno Retinal, Retinaldehido Contorno, Contorno Retinaldehido' WHERE producto_nombre='CONTORNO DE OJOS RETINALDEHIDO 0.05%'",
        "UPDATE sku_planeacion_config SET alias_calendar='NPHA, Nova PHA, Suero PHA, Exfoliante PHA, Exfoliante Nova' WHERE producto_nombre='SUERO EXFOLIANTE NOVA PHA'",
        "UPDATE sku_planeacion_config SET alias_calendar='CMULP, SMULP, Multipeptidos, Suero Multi, Suero Multipeptidos' WHERE producto_nombre='SUERO MULTIPEPTIDOS'",
        "UPDATE sku_planeacion_config SET alias_calendar='EMLIM, Emulsion Limpiadora, Limpiadora Emulsion' WHERE producto_nombre='EMULSION LIMPIADORA'",
        "UPDATE sku_planeacion_config SET alias_calendar='CRCUREA, Crema Urea, Urea, Crema de Urea' WHERE producto_nombre='CREMA DE UREA'",
        "UPDATE sku_planeacion_config SET alias_calendar='NIA, Niacinamida, Suero Niacinamida, Niacin' WHERE producto_nombre='SUERO DE NIACINAMIDA 5% FORMULA NUEVA'",
        "UPDATE sku_planeacion_config SET alias_calendar='BHA, Suero BHA, BHA Suero, Exfoliante BHA' WHERE producto_nombre='Suero Exfoliante BHA 2%'",
        "UPDATE sku_planeacion_config SET alias_calendar='HYDRAP, Hidratante Antiox, EMULSION ANTIOX, Hidratante Antioxidante, Emulsion Hidratante Antioxidante' WHERE producto_nombre='EMULSION HIDRATANTE ANTIOXIDANTE'",
        "UPDATE sku_planeacion_config SET alias_calendar='HYDRABAL, Hidratante Bal, Hidratante Iluminadora, EMULSION ILUM' WHERE producto_nombre='EMULSION HIDRATANTE ILUMINADORA'",
        "UPDATE sku_planeacion_config SET alias_calendar='B3+BHA, Hidratante B3+BHA, Emulsion B3+BHA, B3 BHA, B3 + BHA' WHERE producto_nombre='EMULSION HIDRATANTE  B3+BHA'",
        "UPDATE sku_planeacion_config SET alias_calendar='GELH, Gel Hidratante, Gel H, Gel Hidra' WHERE producto_nombre='GEL HIDRATANTE'",
        "UPDATE sku_planeacion_config SET alias_calendar='AZHC, AZ Hibrid, AZ HIBRID, AZ Hibrid Clear, AZ' WHERE producto_nombre='AZ HIBRID CLEAR'",
        "UPDATE sku_planeacion_config SET alias_calendar='AZ+B3, Suero AZ+B3, AZ B3, AZ + B3' WHERE producto_nombre='SUERO AZ + B3'",
        "UPDATE sku_planeacion_config SET alias_calendar='SAH, Suero AH, AH 1.5%, AH, Hidratante AH, Suero Hialuronico, Suero Hidratante AH' WHERE producto_nombre='SUERO HIDRATANTE AH 1.5%'",
        "UPDATE sku_planeacion_config SET alias_calendar='CCAFE, Cafeina, Contorno Cafeina, Contorno de Cafeina' WHERE producto_nombre='CONTORNO DE CAFEINA'",
        "UPDATE sku_planeacion_config SET alias_calendar='RECN, Renova C10, C10, RENOVA C10, Renova' WHERE producto_nombre='SUERO ANTIOXIDANTE RENOVA C10'",
        "UPDATE sku_planeacion_config SET alias_calendar='SVITC, Vit C, Vitamina C, Suero Vit C, Suero Vitamina C, Vit C Formula Nueva' WHERE producto_nombre='SUERO DE VITAMINA C+ FORMULA NUEVA'",
        "UPDATE sku_planeacion_config SET alias_calendar='CRB3BHA, Suero C+B3, Suero CB3, Vit C+B3, Vitamina C+B3, C+B3' WHERE producto_nombre='SUERO ANTIOXIDANTE VITAMINA C+B3'",
        "UPDATE sku_planeacion_config SET alias_calendar='ECENT, Centella, Esencia Centella, Esencia de Centella' WHERE producto_nombre='ESENCIA DE CENTELLA ASIATICA'",
        "UPDATE sku_planeacion_config SET alias_calendar='EILU, Esencia Iluminadora, Esencia Ilum, Iluminadora Esencia' WHERE producto_nombre='ESENCIA ILUMINADORA'",
        "UPDATE sku_planeacion_config SET alias_calendar='LAH, Limpiador AH, Limpiador Hialuronico, Limpiador Hidratante AH' WHERE producto_nombre='LIMPIADOR FACIAL HIDRATANTE'",
        "UPDATE sku_planeacion_config SET alias_calendar='LKJ, Limpiador Kojico, Iluminador Kojico, Kojico, Limpiador Iluminador' WHERE producto_nombre='LIMPIADOR ILUMINADOR ACIDO KOJICO'",
        "UPDATE sku_planeacion_config SET alias_calendar='MAXLASH, Maxlash, Max Lash' WHERE producto_nombre='MAXLASH'",
        "UPDATE sku_planeacion_config SET alias_calendar='CMULPP, Contorno Multipeptidos, Multipeptidos Contorno' WHERE producto_nombre='CONTORNO DE OJOS MULTIPEPTIDOS'",
        "UPDATE sku_planeacion_config SET alias_calendar='HKJ, Hidratante Kojico, Hidrante Iluminadora Kojico' WHERE producto_nombre='EMULSION HIDRATANTE ILUMINADORA' AND alias_calendar NOT LIKE '%HKJ%'",
        "UPDATE sku_planeacion_config SET alias_calendar='SUERO RETINAL+, Retinal+, Retinal Plus, Suero Retinal' WHERE producto_nombre='Suero RETINAL +'",
        "UPDATE sku_planeacion_config SET alias_calendar='SUERO ILUMINADOR AHA+AH, Iluminador AHA+AH, AHA+AH, Suero Iluminador' WHERE producto_nombre='SUERO ILUMINADOR AHA+AH.'",
        "UPDATE sku_planeacion_config SET alias_calendar='Suero Iluminador TRX, TRX, Iluminador TRX' WHERE producto_nombre='SUERO ILUMINADOR TRX'",
        "UPDATE sku_planeacion_config SET alias_calendar='Mascarilla Hidratante, MAH, Mascarilla H' WHERE producto_nombre='MASCARILLA HIDRATANTE'",
        "UPDATE sku_planeacion_config SET alias_calendar='RENOVA BODY, Body Crema, Crema Renova Body, Crema Corporal Renova' WHERE producto_nombre='CREMA CORPORAL RENOVA BODY'",
        "UPDATE sku_planeacion_config SET alias_calendar='SUERO RETINALDEHIDO, Retinaldehido, Suero Retinal' WHERE producto_nombre='SUERO DE RETINALDEHIDO 0.05%'",
    ]),
    (77, "Self-healing · activar cron + perfil riesgo SKUs faltantes (Sebastián)", [
        # Sebastián 1-may-2026: "que se programe solo automatico, todo perfecto".
        # 1) Habilitar el auto_plan_cron por default (estaba en 0)
        "UPDATE auto_plan_cron_state SET habilitado=1, notas='Auto-habilitado migración 77' WHERE id=1 AND habilitado=0",
        # 2) Asegurar entrada del cron state si no existe
        "INSERT OR IGNORE INTO auto_plan_cron_state (id, habilitado, activado_por, activado_at, notas) VALUES (1, 1, 'auto-migracion', datetime('now'), 'Seed migración 77')",
        # 3) Seed perfil riesgo para SKUs sin perfil (default sin pigmento, riesgo bajo)
        """INSERT OR IGNORE INTO producto_perfil_riesgo
           (producto_nombre, tiene_pigmento, color_descripcion, es_acido,
            requiere_asepsia_extra, riesgo_arrastre_pct, notas, actualizado_en)
           SELECT spc.producto_nombre, 0, 'transparente', 0, 0, 5,
                  'Auto-seed default (sin pigmento, riesgo bajo)',
                  datetime('now')
           FROM sku_planeacion_config spc
           WHERE spc.activo=1
             AND COALESCE(spc.estado,'activo') NOT IN ('descontinuado','pausado')
             AND spc.producto_nombre NOT IN (SELECT producto_nombre FROM producto_perfil_riesgo)""",
        # Tabla para errores acumulados de jobs (notificación)
        """CREATE TABLE IF NOT EXISTS cron_jobs_health (
            job_name TEXT PRIMARY KEY,
            errores_consecutivos INTEGER NOT NULL DEFAULT 0,
            ultimo_error_at TEXT,
            ultimo_error_msg TEXT,
            notificado_at TEXT
        )""",
    ]),
    (76, "produccion_programada: area_envasado_id (Sebastián 1-may-2026 · IA asigna FAB+ENV)", [
        # Sebastián: "asigna el area de produccion y el area de envasado".
        # El motor IA mapea FAB1→ENV1, FAB2/3/FLOAT→ENV2 y necesita persistirlo.
        "ALTER TABLE produccion_programada ADD COLUMN area_envasado_id INTEGER",
        "CREATE INDEX IF NOT EXISTS idx_pp_area_env ON produccion_programada(area_envasado_id)",
    ]),
    (75, "Auto-asignación IA · rotación operarios + limpieza mismo día (Sebastián)", [
        # Sebastián 1-may-2026: "TODOS rotan no necesariamente deja a Camilo
        # y Mayerlin fijos, queden limpias el mismo día, IA que sepa que usar
        # si es producción de 200 kilos debe decir producción donde está la
        # marmita de 250 litros, si lo haces automático sería maravilloso".
        """CREATE TABLE IF NOT EXISTS rotacion_operarios_state (
            rol TEXT PRIMARY KEY,
            ultimo_operario_id INTEGER,
            ultimo_asignado_at TEXT,
            actualizado_por TEXT
        )""",
        """INSERT OR IGNORE INTO rotacion_operarios_state (rol, ultimo_operario_id, ultimo_asignado_at, actualizado_por)
           VALUES
             ('dispensacion', NULL, datetime('now'), 'seed'),
             ('elaboracion', NULL, datetime('now'), 'seed'),
             ('envasado', NULL, datetime('now'), 'seed'),
             ('acondicionamiento', NULL, datetime('now'), 'seed'),
             ('limpieza', NULL, datetime('now'), 'seed')""",
        # Tabla de log de auto-asignaciones para auditoría
        """CREATE TABLE IF NOT EXISTS auto_asignacion_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produccion_id INTEGER NOT NULL,
            ejecutado_at TEXT NOT NULL DEFAULT (datetime('now')),
            ejecutado_por TEXT NOT NULL DEFAULT 'auto-ia',
            area_asignada TEXT,
            tanque_asignado TEXT,
            area_envasado_asignada TEXT,
            operarios_json TEXT,
            score INTEGER,
            razon TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_aal_prod ON auto_asignacion_log(produccion_id)",
    ]),
    (74, "Cron multi-job interno (Sebastián 1-may-2026: sin cron Render externos)", [
        # Sebastián: "configurar 4 crons" lo hago internamente para que no
        # dependa de Render Cron Jobs (que requieren plan paid). Tabla
        # cron_jobs_runs trackea última ejecución por job + dedupe.
        """CREATE TABLE IF NOT EXISTS cron_jobs_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name TEXT NOT NULL,
            ejecutado_at TEXT NOT NULL DEFAULT (datetime('now')),
            duracion_ms INTEGER,
            ok INTEGER NOT NULL DEFAULT 1,
            resultado_json TEXT,
            error TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_cjr_job ON cron_jobs_runs(job_name, ejecutado_at DESC)",
    ]),
    (73, "Auto-SC MEE: backfill proveedor desde maestro_mee (normalización Sebastián)", [
        # Sebastian (1-may-2026): "82 MEE configurados, 0 con proveedor". El
        # seed migración 72 dejó proveedor_principal=''. Pero maestro_mee.proveedor
        # YA tenía el dato real (69/69 con proveedor). Backfill: copiar maestro_mee.proveedor
        # a mee_lead_time_config.proveedor_principal donde esté vacío. Idempotente.
        """UPDATE mee_lead_time_config
              SET proveedor_principal = (
                    SELECT m.proveedor FROM maestro_mee m
                    WHERE m.codigo = mee_lead_time_config.mee_codigo
                  )
            WHERE COALESCE(proveedor_principal,'') = ''
              AND mee_codigo IN (
                SELECT codigo FROM maestro_mee
                WHERE COALESCE(proveedor,'') != ''
              )""",
        # Si el origen viene como 'China' en proveedor maestro, sugerir origen=China
        # para esos MEE (idempotente: solo si origen quedó en default 'Local').
        """UPDATE mee_lead_time_config
              SET origen = 'China'
            WHERE proveedor_principal = 'China'
              AND origen = 'Local'""",
    ]),
    (72, "Auto-SC MEE: seed inteligente + flag disparo_post_envasado (etiquetas)", [
        # Sebastian (1-may-2026): "etiquetas las pedimos el dia que sabemos
        # cuanto envasamos". Flag disparo_post_envasado=1 las saca del cron
        # mensual proyectivo y las muestra en alerta post-envasado.
        "ALTER TABLE mee_lead_time_config ADD COLUMN disparo_post_envasado INTEGER NOT NULL DEFAULT 0",

        # Seed inteligente desde maestro_mee.categoria. INSERT OR IGNORE para
        # no pisar configs manuales previas.
        # Envase/Frasco → China 180d MOQ 5000
        """INSERT OR IGNORE INTO mee_lead_time_config
           (mee_codigo, proveedor_principal, origen, lead_time_dias, moq_unidades,
            precio_unit, disparo_d20, disparo_post_envasado, aplica, notas, actualizado_en)
           SELECT codigo, '', 'China', 180, 5000, 0, 0, 0, 1,
                  'Seed automático cat=' || COALESCE(categoria,'?'),
                  datetime('now')
           FROM maestro_mee
           WHERE COALESCE(categoria,'') IN ('Envase','Frasco')
             AND COALESCE(estado,'Activo')='Activo'""",
        # Tapa/Gotero/Contorno → Local 30d
        """INSERT OR IGNORE INTO mee_lead_time_config
           (mee_codigo, proveedor_principal, origen, lead_time_dias, moq_unidades,
            precio_unit, disparo_d20, disparo_post_envasado, aplica, notas, actualizado_en)
           SELECT codigo, '', 'Local', 30, 0, 0, 0, 0, 1,
                  'Seed automático cat=' || COALESCE(categoria,'?'),
                  datetime('now')
           FROM maestro_mee
           WHERE COALESCE(categoria,'') IN ('Tapa','Gotero','Contorno')
             AND COALESCE(estado,'Activo')='Activo'""",
        # Etiqueta → Local 15d disparo_post_envasado=1
        """INSERT OR IGNORE INTO mee_lead_time_config
           (mee_codigo, proveedor_principal, origen, lead_time_dias, moq_unidades,
            precio_unit, disparo_d20, disparo_post_envasado, aplica, notas, actualizado_en)
           SELECT codigo, '', 'Local', 15, 0, 0, 0, 1, 1,
                  'Seed automático: etiqueta se pide post-envasado',
                  datetime('now')
           FROM maestro_mee
           WHERE COALESCE(categoria,'')='Etiqueta'
             AND COALESCE(estado,'Activo')='Activo'""",
        # Serigrafia → Local 20d disparo_d20=1
        """INSERT OR IGNORE INTO mee_lead_time_config
           (mee_codigo, proveedor_principal, origen, lead_time_dias, moq_unidades,
            precio_unit, disparo_d20, disparo_post_envasado, aplica, notas, actualizado_en)
           SELECT codigo, '', 'Local', 20, 0, 0, 1, 0, 1,
                  'Seed automático: serigrafía D-20 antes de producción',
                  datetime('now')
           FROM maestro_mee
           WHERE COALESCE(categoria,'')='Serigrafia'
             AND COALESCE(estado,'Activo')='Activo'""",
        # Plegable → no aplica (Sebastián: "plegadiza no estamos usando")
        """INSERT OR IGNORE INTO mee_lead_time_config
           (mee_codigo, proveedor_principal, origen, lead_time_dias, moq_unidades,
            precio_unit, disparo_d20, disparo_post_envasado, aplica, notas, actualizado_en)
           SELECT codigo, '', 'Local', 30, 0, 0, 0, 0, 0,
                  'Seed automático: plegadiza no usamos (Sebastián 1-may-2026)',
                  datetime('now')
           FROM maestro_mee
           WHERE COALESCE(categoria,'')='Plegable'
             AND COALESCE(estado,'Activo')='Activo'""",

        # Seed sku_mee_config desde envasado histórico (DISTINCT producto+codigo)
        """INSERT OR IGNORE INTO sku_mee_config
           (sku_codigo, mee_codigo, componente_tipo, cantidad_por_unidad, aplica, notas)
           SELECT DISTINCT e.producto, e.envase_codigo, 'envase', 1, 1,
                  'Seed desde envasado histórico'
           FROM envasado e
           WHERE COALESCE(e.envase_codigo,'') != ''
             AND e.envase_codigo IN (SELECT codigo FROM maestro_mee)""",
        """INSERT OR IGNORE INTO sku_mee_config
           (sku_codigo, mee_codigo, componente_tipo, cantidad_por_unidad, aplica, notas)
           SELECT DISTINCT e.producto, e.tapa_codigo, 'tapa', 1, 1,
                  'Seed desde envasado histórico'
           FROM envasado e
           WHERE COALESCE(e.tapa_codigo,'') != ''
             AND e.tapa_codigo IN (SELECT codigo FROM maestro_mee)""",
    ]),
    (71, "Auto-SC MEE: mee_lead_time_config + sku_mee_config (para proyección 9m China + 90d local)", [
        # Sebastian (1-may-2026): "envases China 9m, etiquetas las pedimos al
        # envasar, serigrafía 20d antes, plegadiza no aplica, el resto local
        # 60-90d como MP". Tablas paralelas a mp_lead_time_config para que el
        # Auto-SC IA pueda proyectar también MEE.
        """CREATE TABLE IF NOT EXISTS mee_lead_time_config (
            mee_codigo TEXT PRIMARY KEY,
            proveedor_principal TEXT NOT NULL DEFAULT '',
            origen TEXT NOT NULL DEFAULT 'Local'
                CHECK(origen IN ('China','Local','Mixto')),
            lead_time_dias INTEGER NOT NULL DEFAULT 30,
            moq_unidades INTEGER NOT NULL DEFAULT 0,
            precio_unit REAL NOT NULL DEFAULT 0,
            disparo_d20 INTEGER NOT NULL DEFAULT 0,
            aplica INTEGER NOT NULL DEFAULT 1,
            notas TEXT,
            actualizado_en TEXT,
            actualizado_por TEXT
        )""",
        # disparo_d20=1 → cron diario revisa Calendar y dispara SC en D-20
        # (serigrafía/tampografía); aplica=0 → ignorado por Auto-SC (plegadiza).
        "CREATE INDEX IF NOT EXISTS idx_mlt_origen ON mee_lead_time_config(origen, aplica)",

        """CREATE TABLE IF NOT EXISTS sku_mee_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku_codigo TEXT NOT NULL,
            mee_codigo TEXT NOT NULL,
            componente_tipo TEXT NOT NULL DEFAULT 'envase'
                CHECK(componente_tipo IN ('envase','tapa','etiqueta','caja',
                                          'serigrafia','tampografia','plegadiza','otro')),
            cantidad_por_unidad REAL NOT NULL DEFAULT 1,
            aplica INTEGER NOT NULL DEFAULT 1,
            notas TEXT,
            UNIQUE(sku_codigo, mee_codigo)
        )""",
        # cantidad_por_unidad típica = 1 (un envase por SKU vendido). Para caja
        # master de 24 unidades = 0.0417. Para etiquetas con cara dual = 2.
        "CREATE INDEX IF NOT EXISTS idx_smc_sku ON sku_mee_config(sku_codigo, aplica)",
        "CREATE INDEX IF NOT EXISTS idx_smc_mee ON sku_mee_config(mee_codigo, aplica)",
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

    (158, "MP aliases · búsqueda inteligente por abreviatura INCI · 22-may-2026", [
        # Sebastián 22-may-2026: 'fórmula MAXLASH dice SAP es Sodium Ascorbyl
        # Phosphate · cuando busco SAP en inventario no sale'.
        # Solución: tabla de alias que mapea abbreviatura ↔ código_mp + INCI completo.
        """CREATE TABLE IF NOT EXISTS mp_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias TEXT NOT NULL,
            codigo_mp TEXT,
            nombre_inci_canonical TEXT,
            tipo TEXT DEFAULT 'abreviatura'
                CHECK(tipo IN ('abreviatura','sinonimo','typo_comun','translation')),
            fuente TEXT DEFAULT 'manual'
                CHECK(fuente IN ('manual','seed','auto-detectado','catalina','sebastian')),
            creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            creado_por TEXT,
            activo INTEGER NOT NULL DEFAULT 1
        )""",
        "CREATE INDEX IF NOT EXISTS idx_mp_aliases_alias ON mp_aliases(LOWER(alias))",
        "CREATE INDEX IF NOT EXISTS idx_mp_aliases_codigo ON mp_aliases(codigo_mp)",
        # Seed abreviaturas comunes INCI cosmética
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('SAP', 'Sodium Ascorbyl Phosphate', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('MAP', 'Magnesium Ascorbyl Phosphate', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('HA',  'Hyaluronic Acid', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('SHA', 'Sodium Hyaluronate', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('PG',  'Propylene Glycol', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('BG',  'Butylene Glycol', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('CG',  'Caprylyl Glycol', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('SCI', 'Sodium Cocoyl Isethionate', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('SLES','Sodium Laureth Sulfate', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('CAPB','Cocamidopropyl Betaine', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('EDTA','Ethylenediaminetetraacetic Acid', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('TEA', 'Triethanolamine', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('DEA', 'Diethanolamine', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('MEA', 'Monoethanolamine', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('SLS', 'Sodium Lauryl Sulfate', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('PEG', 'Polyethylene Glycol', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('DMDM','DMDM Hydantoin', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('BHT', 'Butylated Hydroxytoluene', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('BHA', 'Butylated Hydroxyanisole', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('AHA', 'Alpha Hydroxy Acid', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('BHA', 'Beta Hydroxy Acid', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('PCA', 'Pyrrolidone Carboxylic Acid', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('NaPCA','Sodium PCA', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('VitC','Ascorbic Acid', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('VitE','Tocopherol', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('VitB5','Panthenol', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('VitB3','Niacinamide', 'abreviatura', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('CoQ10','Ubiquinone', 'abreviatura', 'seed')",
        # Typos comunes
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('ascorbil', 'Ascorbic Acid', 'typo_comun', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('ascorbyl', 'Ascorbic Acid', 'typo_comun', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('hialuronic', 'Hyaluronic Acid', 'typo_comun', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('hialuronico', 'Hyaluronic Acid', 'typo_comun', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('niacinamida', 'Niacinamide', 'translation', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('pantenol', 'Panthenol', 'translation', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('glicerina', 'Glycerin', 'translation', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('propilenglicol', 'Propylene Glycol', 'translation', 'seed')",
        "INSERT OR IGNORE INTO mp_aliases (alias, nombre_inci_canonical, tipo, fuente) VALUES ('butilenglicol', 'Butylene Glycol', 'translation', 'seed')",
    ]),

    (157, "Estados OC simplificación 8→6 · 22-may-2026", [
        # Sebastián 22-may-2026 · consultor LEAN: menos estados = menos confusión.
        # Antes 8: Borrador, Revisada, Autorizada, Parcial, Recibida, Pagada, Cancelada, Rechazada
        # Después 6: Borrador, Autorizada, Recibida, Pagada, Cancelada, Rechazada
        # · Revisada → Borrador (revisión es un sub-estado interno · no expone)
        # · Parcial → Autorizada (count parcial via cantidad_recibida_g per item)
        # Migración data: traslada existentes (sin perder histórico via observaciones)
        "UPDATE ordenes_compra SET "
        "  observaciones = COALESCE(observaciones,'') || ' [migrado-Revisada→Borrador 22-may-2026]', "
        "  estado='Borrador' "
        "WHERE estado='Revisada'",
        "UPDATE ordenes_compra SET "
        "  observaciones = COALESCE(observaciones,'') || ' [migrado-Parcial→Autorizada 22-may-2026]', "
        "  estado='Autorizada' "
        "WHERE estado='Parcial'",
    ]),

    (156, "cron_jobs_runs · indices performance · 22-may-2026", [
        # Sebastián 22-may-2026 · Bug #7 audit Crons.
        # _ya_ejecutado_hoy hacía full-scan sin índice · 5 min × 30 jobs = caro
        "CREATE INDEX IF NOT EXISTS idx_cron_runs_job_date "
        "ON cron_jobs_runs(job_name, ejecutado_at DESC)",
    ]),

    (155, "turnos_operario · UNIQUE constraint anti-overlap · 22-may-2026", [
        # Sebastián 22-may-2026 · Bug #10 audit Operario.
        # Antes: operario podía estar en 2 turnos paralelos (capacidad fantasma)
        # · _asignar_operarios_a_produccion no chequeaba overlap
        # · mi_dia mostraba 4 lotes en paralelo al mismo operario
        # Fix: UNIQUE INDEX previene INSERT duplicado (operario+fecha+turno)
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_turnos_op_fecha "
        "ON turnos_operario(operario_id, fecha, turno)",
    ]),

    (154, "formula_items · flag incluye_merma · doble-merma fix · 22-may-2026", [
        # Sebastián 22-may-2026 · Bug #11 audit abastecimiento.
        # Si `cantidad_g_por_lote` ya tiene merma incluida (convención cosmética),
        # auto_plan línea 716 la inflaba otra vez → over-ordering 5-15%.
        # Flag opt-in (default 0) · si =1 auto_plan NO re-aplica merma.
        "ALTER TABLE formula_items ADD COLUMN incluye_merma INTEGER DEFAULT 0",
    ]),

    (153, "BRD · alias columnas para MyBatch · 21-may-2026", [
        # Sebastián 21-may-2026 · BRD vista-completa, timeline, cuarentena
        # explícita usaban columnas con nombres distintos al schema real.
        # Agregamos los aliases para que las queries no rompan en PG/SQLite.
        "ALTER TABLE ebr_ejecuciones ADD COLUMN lote_codigo TEXT",
        "ALTER TABLE ebr_ejecuciones ADD COLUMN operario TEXT",
        "ALTER TABLE ebr_ejecuciones ADD COLUMN observaciones TEXT",
        "ALTER TABLE ebr_ejecuciones ADD COLUMN tiempo_total_min REAL",
        "ALTER TABLE ebr_ejecuciones ADD COLUMN rechazado_at_utc TEXT",
        # Sync inicial · poblar aliases desde columnas originales
        "UPDATE ebr_ejecuciones SET lote_codigo = COALESCE(lote_codigo, lote)",
        "UPDATE ebr_ejecuciones SET operario = COALESCE(operario, iniciado_por)",
        "UPDATE ebr_ejecuciones SET observaciones = COALESCE(observaciones, notas)",
    ]),

    (152, "Indexes performance · queries frecuentes · 21-may-2026", [
        # Sebastián 21-may-2026 · auditoría performance · indexes faltantes
        # en columnas que se filtran/joinean en endpoints calientes.
        # Acelera FEFO, factibilidad, scorecard proveedor, dedup motor SOL.
        "CREATE INDEX IF NOT EXISTS idx_mov_material_id ON movimientos(material_id, tipo, fecha)",
        "CREATE INDEX IF NOT EXISTS idx_mov_lote ON movimientos(lote, fecha_vencimiento)",
        "CREATE INDEX IF NOT EXISTS idx_mov_estado_lote ON movimientos(estado_lote)",
        "CREATE INDEX IF NOT EXISTS idx_oc_proveedor ON ordenes_compra(proveedor, fecha DESC)",
        "CREATE INDEX IF NOT EXISTS idx_oc_fecha_recepcion ON ordenes_compra(fecha_recepcion)",
        "CREATE INDEX IF NOT EXISTS idx_pagos_factura ON pagos_oc(numero_factura_proveedor)",
        "CREATE INDEX IF NOT EXISTS idx_sol_numero_oc ON solicitudes_compra(numero_oc)",
        "CREATE INDEX IF NOT EXISTS idx_sol_categoria ON solicitudes_compra(categoria, estado)",
        "CREATE INDEX IF NOT EXISTS idx_sci_codigo_mp ON solicitudes_compra_items(codigo_mp)",
        "CREATE INDEX IF NOT EXISTS idx_oci_codigo_mp ON ordenes_compra_items(codigo_mp)",
        "CREATE INDEX IF NOT EXISTS idx_fi_material_id ON formula_items(material_id)",
        "CREATE INDEX IF NOT EXISTS idx_precios_mp_codigo ON precios_mp_historico(codigo_mp, fecha DESC)",
        "CREATE INDEX IF NOT EXISTS idx_precios_mp_proveedor ON precios_mp_historico(proveedor)",
        "CREATE INDEX IF NOT EXISTS idx_pp_estado_fecha ON produccion_programada(estado, fecha_programada)",
        "CREATE INDEX IF NOT EXISTS idx_pp_origen ON produccion_programada(origen)",
    ]),

    (151, "COA + lote proveedor en movimientos · INVIMA · 21-may-2026", [
        # Sebastián 21-may-2026 · consultor procurement: 'COA + lote proveedor
        # en recepción es no-negociable para GMP cosmético INVIMA. Cuando llegue
        # auditoría no perdés 2 días armando el dossier.'
        # safe_alter trata IF NOT EXISTS para ser idempotente entre boots.
        "ALTER TABLE movimientos ADD COLUMN coa_url TEXT",
        "ALTER TABLE movimientos ADD COLUMN coa_filename TEXT",
        "ALTER TABLE movimientos ADD COLUMN lote_proveedor TEXT",
        "ALTER TABLE movimientos ADD COLUMN ficha_seguridad_url TEXT",
        "CREATE INDEX IF NOT EXISTS idx_mov_lote_proveedor ON movimientos(lote_proveedor)",
    ]),

    (150, "Órdenes de Servicio · Serigrafía/Tampografía · 21-may-2026", [
        # Sebastián 21-may-2026: "planta pide envases o toca hacer serigrafía
        # · Catalina da la orden desde compras preparar tales envases · recogen
        # · envían · planta confirma recibido". Distinto de OC: NO compra
        # material, manda a procesar material existente.
        """CREATE TABLE IF NOT EXISTS ordenes_servicio (
            numero_os TEXT PRIMARY KEY,
            proveedor TEXT NOT NULL,
            tipo_servicio TEXT NOT NULL DEFAULT 'Serigrafía',
            producto_final TEXT,
            envase_codigo_mee TEXT,
            envase_descripcion TEXT,
            cantidad_unidades INTEGER NOT NULL DEFAULT 0,
            arte_descripcion TEXT,
            arte_archivo_url TEXT,
            fecha_solicitud TEXT NOT NULL,
            fecha_requerida_entrega TEXT,
            fecha_real_entrega TEXT,
            estado TEXT NOT NULL DEFAULT 'Borrador'
                CHECK(estado IN ('Borrador','Enviada','Recogida','En proceso',
                                  'Entregada','Confirmada','Cancelada')),
            costo_estimado_cop REAL DEFAULT 0,
            costo_real_cop REAL DEFAULT 0,
            observaciones TEXT,
            creado_por TEXT NOT NULL,
            creado_at_utc TEXT DEFAULT (datetime('now','utc')),
            planta_confirmado_por TEXT,
            planta_confirmado_at_utc TEXT,
            cancelada_motivo TEXT,
            tenant_id INTEGER DEFAULT 1
        )""",
        "CREATE INDEX IF NOT EXISTS idx_os_estado ON ordenes_servicio(estado, fecha_solicitud DESC)",
        "CREATE INDEX IF NOT EXISTS idx_os_proveedor ON ordenes_servicio(proveedor)",
        # Tabla de eventos · timeline auditable de cada cambio de estado
        """CREATE TABLE IF NOT EXISTS ordenes_servicio_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_os TEXT NOT NULL,
            estado_anterior TEXT,
            estado_nuevo TEXT NOT NULL,
            usuario TEXT NOT NULL,
            ts_utc TEXT DEFAULT (datetime('now','utc')),
            observaciones TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_os_eventos_os ON ordenes_servicio_eventos(numero_os, id)",
    ]),

    (149, "Usuarios PRO · metadata + activo flag · 21-may-2026", [
        # Sebastián 21-may-2026: "hoy entra jefe de producción nuevo y
        # sale Luis · no tenemos donde generar usuarios". Tabla
        # users_passwords ya existe (mig 25) pero le falta metadata
        # (rol, activo, nombre, cargo, email) para gestionar usuarios
        # desde UI sin tocar Render env vars.
        "ALTER TABLE users_passwords ADD COLUMN activo INTEGER DEFAULT 1",
        "ALTER TABLE users_passwords ADD COLUMN nombre_completo TEXT",
        "ALTER TABLE users_passwords ADD COLUMN cargo TEXT",
        "ALTER TABLE users_passwords ADD COLUMN email TEXT",
        "ALTER TABLE users_passwords ADD COLUMN roles_csv TEXT DEFAULT 'compras'",
        "ALTER TABLE users_passwords ADD COLUMN creado_por TEXT",
        "ALTER TABLE users_passwords ADD COLUMN creado_at_utc TEXT",
        "ALTER TABLE users_passwords ADD COLUMN ultimo_login_at_utc TEXT",
        "ALTER TABLE users_passwords ADD COLUMN baja_motivo TEXT",
        "CREATE INDEX IF NOT EXISTS idx_users_activo ON users_passwords(activo)",
    ]),

    (148, "Fabricación PRO · costo_estimado_cop + lote_pt index · 20-may-2026", [
        # Costo estimado guardado al registrar producción (calculado de
        # precio_referencia × cantidad_g por MP). Antes solo se computaba
        # en /simular sin persistir.
        "ALTER TABLE producciones ADD COLUMN costo_estimado_cop REAL",
        "CREATE INDEX IF NOT EXISTS idx_producciones_lote ON producciones(lote)",
        "CREATE INDEX IF NOT EXISTS idx_producciones_producto_fecha ON producciones(producto, fecha DESC)",
    ]),

    (147, "Fórmulas PRO · app_settings + versionado + import_excel · 20-may-2026", [
        """CREATE TABLE IF NOT EXISTS app_settings (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL,
            descripcion TEXT,
            actualizado_at_utc TEXT DEFAULT (datetime('now','utc')),
            actualizado_por TEXT,
            tenant_id INTEGER DEFAULT 1
        )""",
        """CREATE TABLE IF NOT EXISTS formula_versiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_nombre TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            unidad_base_g REAL NOT NULL DEFAULT 1000,
            descripcion TEXT,
            items_json TEXT NOT NULL,
            creado_at_utc TEXT DEFAULT (datetime('now','utc')),
            creado_por TEXT,
            motivo_cambio TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_formula_versiones_producto ON formula_versiones(producto_nombre, version DESC)",
    ]),

    (146, "OLA 3 Op Live · roles + notificaciones_outbox (bases futuras) · 20-may-2026", [
        # Tabla roles · futura migración desde {sebastian,alejandro} hardcoded
        # en config.py a tabla. Por ahora coexisten (compat).
        """CREATE TABLE IF NOT EXISTS roles_catalogo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            descripcion TEXT,
            activo INTEGER DEFAULT 1,
            creado_at_utc TEXT DEFAULT (datetime('now','utc'))
        )""",
        """CREATE TABLE IF NOT EXISTS usuario_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            rol_codigo TEXT NOT NULL,
            asignado_por TEXT,
            asignado_at_utc TEXT DEFAULT (datetime('now','utc')),
            activo INTEGER DEFAULT 1,
            UNIQUE(usuario, rol_codigo)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_usuario_roles_lookup ON usuario_roles(usuario, activo)",
        # Seed de roles base (idempotente con INSERT OR IGNORE)
        """INSERT OR IGNORE INTO roles_catalogo (codigo, descripcion) VALUES
            ('admin', 'Administrador completo (Sebastián, Alejandro)'),
            ('jefe_planta', 'Jefe de planta · operación + aprobación QC'),
            ('operario', 'Operario de planta'),
            ('calidad', 'Control de calidad · libera lotes'),
            ('compras', 'Compras · gestiona SOLs y OCs'),
            ('contabilidad', 'Contabilidad'),
            ('comercial', 'Comercial · ÁNIMUS DTC'),
            ('cliente_b2b', 'Cliente B2B · solo portal /portal'),
            ('auditor_externo', 'Auditor externo · solo lectura')""",
        # Outbox de notificaciones · permite fan-out async cuando crezca
        # el sistema. Por ahora se llena para visibilidad pero NO se usa
        # como reemplazo de push_notif sincrónico (sería breaking).
        """CREATE TABLE IF NOT EXISTS notificaciones_outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            destinatario TEXT NOT NULL,
            tipo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            body TEXT,
            link TEXT,
            remitente TEXT,
            importante INTEGER DEFAULT 0,
            estado TEXT NOT NULL DEFAULT 'pendiente' CHECK(estado IN ('pendiente','enviada','fallida','descartada')),
            intentos INTEGER DEFAULT 0,
            ultimo_error TEXT,
            creado_at_utc TEXT DEFAULT (datetime('now','utc')),
            enviado_at_utc TEXT,
            tenant_id INTEGER DEFAULT 1
        )""",
        "CREATE INDEX IF NOT EXISTS idx_outbox_pendientes ON notificaciones_outbox(estado, creado_at_utc)",
    ]),

    (145, "OLA 2 Op Live · Takt time + Andon · 20-may-2026", [
        # Tiempo objetivo (takt) por producto + etapa · base para OEE, ETA,
        # score productividad operario. Sin esto no hay benchmark.
        """CREATE TABLE IF NOT EXISTS tiempo_objetivo_sku (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT NOT NULL,
            etapa TEXT NOT NULL,
            minutos_objetivo REAL NOT NULL,
            minutos_p50_historico REAL,
            minutos_p90_historico REAL,
            actualizado_at_utc TEXT DEFAULT (datetime('now','utc')),
            actualizado_por TEXT
        )""",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_tiempo_objetivo ON tiempo_objetivo_sku(producto, etapa)",
        # Andon · botón "Problema" en Mi Día · operario reporta sin WhatsApp
        """CREATE TABLE IF NOT EXISTS andon_alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL CHECK(tipo IN ('mp_faltante','equipo_caido','consulta_qc','accidente','otro')),
            operario TEXT NOT NULL,
            produccion_id INTEGER,
            area_codigo TEXT,
            descripcion TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'abierta' CHECK(estado IN ('abierta','en_atencion','resuelta','cancelada')),
            ts_abierta TEXT NOT NULL DEFAULT (datetime('now','utc')),
            atendida_por TEXT,
            ts_atendida TEXT,
            resolucion TEXT,
            ts_resuelta TEXT,
            tenant_id INTEGER DEFAULT 1
        )""",
        "CREATE INDEX IF NOT EXISTS idx_andon_estado ON andon_alertas(estado, ts_abierta DESC)",
    ]),

    (144, "OLA 1 Op Live · multi-tenant + turnos_operario (decisiones FUTURO) · 20-may-2026", [
        # tenant_id default 1 en las 15 tablas grandes · NO usar todavía,
        # solo dejar listo para multi-planta / multi-cliente cuando llegue.
        # Costo HOY: 1 migración trivial. Costo si se hace después: tocar
        # 200+ queries (analizado por agente FUTURO 20-may).
        "ALTER TABLE produccion_programada ADD COLUMN tenant_id INTEGER DEFAULT 1",
        "ALTER TABLE movimientos ADD COLUMN tenant_id INTEGER DEFAULT 1",
        "ALTER TABLE maestro_mps ADD COLUMN tenant_id INTEGER DEFAULT 1",
        "ALTER TABLE maestro_mee ADD COLUMN tenant_id INTEGER DEFAULT 1",
        "ALTER TABLE ordenes_compra ADD COLUMN tenant_id INTEGER DEFAULT 1",
        "ALTER TABLE solicitudes_compra ADD COLUMN tenant_id INTEGER DEFAULT 1",
        "ALTER TABLE pedidos_b2b ADD COLUMN tenant_id INTEGER DEFAULT 1",
        "ALTER TABLE formula_headers ADD COLUMN tenant_id INTEGER DEFAULT 1",
        "ALTER TABLE areas_planta ADD COLUMN tenant_id INTEGER DEFAULT 1",
        "ALTER TABLE operarios_planta ADD COLUMN tenant_id INTEGER DEFAULT 1",
        # turnos_operario · clock-in/clock-out · soporte nómina + 3 turnos.
        # Empieza vacía · cuando llegue el segundo turno, todo listo.
        """CREATE TABLE IF NOT EXISTS turnos_operario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operario_id INTEGER NOT NULL,
            operario_nombre TEXT NOT NULL,
            fecha TEXT NOT NULL,
            turno TEXT NOT NULL DEFAULT 'unico',
            inicio_at_utc TEXT,
            fin_at_utc TEXT,
            horas_extra_min INTEGER DEFAULT 0,
            ausencia INTEGER DEFAULT 0,
            motivo_ausencia TEXT,
            tenant_id INTEGER DEFAULT 1
        )""",
        "CREATE INDEX IF NOT EXISTS idx_turnos_operario_fecha ON turnos_operario(fecha, operario_id)",
        "CREATE INDEX IF NOT EXISTS idx_turnos_operario_op ON turnos_operario(operario_id, fecha DESC)",
    ]),

    (143, "OLA 1 Op Live · gates INVIMA (QC release + despeje línea) · 20-may-2026", [
        # Gate QC release Elaboración → Envasado · Luis Enrique firma
        # "granel aprobado" antes que Envasado pueda iniciar (hallazgo
        # INVIMA esperando ocurrir · auditoría 20-may).
        "ALTER TABLE produccion_programada ADD COLUMN granel_aprobado_at TEXT",
        "ALTER TABLE produccion_programada ADD COLUMN granel_aprobado_por TEXT",
        "ALTER TABLE produccion_programada ADD COLUMN granel_aprobado_motivo TEXT",
        # Checklist despeje de línea (5 ítems BPM) · al marcar sala limpia
        """CREATE TABLE IF NOT EXISTS despeje_linea_checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_id INTEGER NOT NULL,
            area_codigo TEXT NOT NULL,
            marcado_por TEXT NOT NULL,
            ts TEXT NOT NULL DEFAULT (datetime('now','utc')),
            item1_sin_etiquetas INTEGER NOT NULL DEFAULT 0,
            item2_sin_producto_suelto INTEGER NOT NULL DEFAULT 0,
            item3_equipos_lavados INTEGER NOT NULL DEFAULT 0,
            item4_registros_archivados INTEGER NOT NULL DEFAULT 0,
            item5_sala_vacia INTEGER NOT NULL DEFAULT 0,
            observaciones TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_despeje_area_ts ON despeje_linea_checklist(area_id, ts DESC)",
    ]),

    (142, "Alertas silenciadas · Sprint Alertas PRO · Sebastián 20-may-2026", [
        # Permite "silenciar" una alerta puntual con motivo + expira_at
        # opcional. Si vence el silencio, vuelve a aparecer.
        """CREATE TABLE IF NOT EXISTS alertas_silenciadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_alerta TEXT NOT NULL,
            codigo_referencia TEXT NOT NULL,
            motivo TEXT NOT NULL,
            silenciado_por TEXT NOT NULL,
            silenciado_at_utc TEXT NOT NULL DEFAULT (datetime('now','utc')),
            expira_at_utc TEXT,
            activo INTEGER NOT NULL DEFAULT 1
        )""",
        "CREATE INDEX IF NOT EXISTS idx_alertas_silenciadas_lookup ON alertas_silenciadas(tipo_alerta, codigo_referencia, activo)",
    ]),

    (141, "Portal Clientes B2B Fase 2 · PQR · Sebastián 20-may-2026", [
        # Sebastián 15-may-2026: "solo tuviera dos módulos, solicitar y pqr".
        # Fase 2 = PQR. Tab adicional en /portal · cliente envía petición,
        # queja, reclamo o sugerencia · admin responde desde backoffice.
        """CREATE TABLE IF NOT EXISTS portal_pqr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id TEXT NOT NULL,
            cliente_nombre TEXT NOT NULL,
            email_cliente TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('peticion','queja','reclamo','sugerencia')),
            titulo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'abierto'
                CHECK(estado IN ('abierto','en_revision','respondido','cerrado')),
            respuesta_admin TEXT DEFAULT '',
            respondido_por TEXT DEFAULT '',
            respondido_at_utc TEXT,
            creado_at_utc TEXT NOT NULL DEFAULT (datetime('now','utc')),
            actualizado_at_utc TEXT NOT NULL DEFAULT (datetime('now','utc'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_portal_pqr_cliente ON portal_pqr(cliente_id, estado)",
        "CREATE INDEX IF NOT EXISTS idx_portal_pqr_estado ON portal_pqr(estado, creado_at_utc DESC)",
    ]),

    (140, "Portal Clientes B2B Fase 1 · credenciales y sesiones · Sebastián 20-may-2026", [
        # Sebastián 15-may-2026: portal minimalista para Fernando Mesa
        # (y futuros mayoristas). Solo 2 módulos: Solicitar + PQR. Fase 1
        # = Solicitar. Acceso aislado · NUNCA toca compras_user / rutas
        # internas. Sebastián crea las credenciales manualmente desde
        # admin (no hay self-signup).
        """CREATE TABLE IF NOT EXISTS portal_clientes_credenciales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id TEXT NOT NULL,
            cliente_nombre TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1,
            creado_por TEXT NOT NULL,
            creado_at_utc TEXT NOT NULL DEFAULT (datetime('now','utc')),
            ultimo_login_at_utc TEXT,
            ultimo_login_ip TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_portal_creds_email ON portal_clientes_credenciales(email)",
        "CREATE INDEX IF NOT EXISTS idx_portal_creds_cliente ON portal_clientes_credenciales(cliente_id, activo)",
    ]),

    (139, "Kanban de Estaciones · timestamps por etapa · Sebastián 19-may-2026", [
        # Sebastián 19-may-2026: pieza 3 del Kanban de Estaciones de Planta.
        # Hasta hoy `produccion_programada` solo guardaba inicio_real_at y
        # fin_real_at a nivel de la producción TOTAL. Con esto NO se puede
        # representar el flujo "Mayerlin terminó dispensación · Camilo
        # arranca elaboración · ahora le toca a Milton envasar". 8 columnas
        # nuevas (4 etapas × 2 timestamps) hacen el pase de testigo posible.
        #
        # Modelo:
        #   etapa_X_inicio_at NULL → etapa pendiente (no ha empezado)
        #   etapa_X_inicio_at SET y etapa_X_fin_at NULL → etapa en curso
        #   etapa_X_fin_at SET → etapa terminada
        #
        # Convención fechas: ISO local Colombia (igual que inicio_real_at).
        # NULL por default · todas las producciones legacy siguen funcionando.
        "ALTER TABLE produccion_programada ADD COLUMN etapa_disp_inicio_at TEXT",
        "ALTER TABLE produccion_programada ADD COLUMN etapa_disp_fin_at TEXT",
        "ALTER TABLE produccion_programada ADD COLUMN etapa_elab_inicio_at TEXT",
        "ALTER TABLE produccion_programada ADD COLUMN etapa_elab_fin_at TEXT",
        "ALTER TABLE produccion_programada ADD COLUMN etapa_env_inicio_at TEXT",
        "ALTER TABLE produccion_programada ADD COLUMN etapa_env_fin_at TEXT",
        "ALTER TABLE produccion_programada ADD COLUMN etapa_acond_inicio_at TEXT",
        "ALTER TABLE produccion_programada ADD COLUMN etapa_acond_fin_at TEXT",
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
        "no such table",  # ALTER en tabla que aún no se ha creado
    )

    # Audit zero-error 2-may-2026: ordenar por número de versión antes de aplicar.
    # El array de MIGRATIONS estaba en orden parcial (newer-first arriba,
    # older-first abajo). Eso causaba que migración 92 (indexes sobre tablas
    # 87/88) corriera ANTES de las migraciones que creaban esas tablas, con
    # el resultado de que CREATE INDEX fallaba silenciosamente por "no such
    # table" (en BENIGN_PATTERNS) y los indexes nunca se creaban.
    # Ordenar garantiza que dependencias siempre estén aplicadas primero.
    # Migraciones marcadas como best-effort: si fallan, log warning + skip
    # registro (no abortan arranque). Permite que prod siga viva mientras
    # diagnosticamos sintaxis específica del SQLite del runtime.
    # Sebastián 8-may-2026: migración 98 falló en Render con error que no
    # se logueaba (el `from exc` no se mostraba). Ahora incluimos str(exc)
    # en el mensaje y permitimos best-effort para no tumbar prod.
    BEST_EFFORT_VERSIONS = {97, 98}

    for version, description, stmts in sorted(MIGRATIONS, key=lambda m: m[0]):
        if version in applied:
            continue
        migration_ok = True
        for stmt in stmts:
            try:
                conn.execute(stmt)
            except Exception as exc:
                msg = str(exc).lower()
                if any(pat in msg for pat in BENIGN_PATTERNS):
                    continue
                # Migración best-effort: log y sigue sin abortar arranque
                if version in BEST_EFFORT_VERSIONS:
                    print(
                        f"[migration] WARN: migración {version} stmt falló "
                        f"(best-effort, no aborta): {type(exc).__name__}: {exc} "
                        f"· stmt: {stmt[:120]}..."
                    )
                    migration_ok = False
                    continue
                # Migración crítica: abortar con info completa (causa raíz visible)
                raise RuntimeError(
                    f"Migración {version} falló en: {stmt!r} · causa: "
                    f"{type(exc).__name__}: {exc}"
                ) from exc
        # Solo registrar como aplicada si todos los stmts pasaron.
        # Si fue best-effort fallida, queda fuera de applied y reintenta
        # en el próximo arranque (idempotente con CREATE IF NOT EXISTS).
        if migration_ok:
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, description) VALUES(?,?)",
                (version, description),
            )
            conn.commit()
            applied_count += 1

    return applied_count

def init_db():
    # Migración Fase 3: en modo PostgreSQL init_db NO corre las migraciones
    # SQLite (re-ejecutarlas sobre el esquema PG ya construido falla: los
    # triggers precargados rechazan datos históricos). El esquema y los
    # datos PG se cargan aparte: conftest para tests, script de cutover
    # para producción (construye un SQLite con init_db y copia los datos).
    if _usa_postgres():
        return
    # Sebastián 12-may-2026: integrity_check al startup ANTES de
    # cualquier escritura. Si la BD está corrupta ('database disk
    # image is malformed'), logueamos CRITICAL para que el dev se
    # entere y pueda restaurar con /api/admin/emergency-restore antes
    # de que el sistema produzca data inconsistente.
    try:
        _check_conn = sqlite3.connect(DB_PATH, timeout=3.0)
        try:
            _check_row = _check_conn.execute('PRAGMA integrity_check').fetchone()
            _integrity = (_check_row[0] if _check_row else 'unknown')
            if _integrity != 'ok':
                import logging as _logging
                _log = _logging.getLogger('inventario.db_integrity')
                _log.critical(
                    'DB INTEGRITY FAILED al startup · integrity_check=%s · '
                    'RESTAURAR DESDE BACKUP via /api/admin/emergency-restore',
                    _integrity
                )
        finally:
            _check_conn.close()
    except sqlite3.DatabaseError as _e:
        # 'database disk image is malformed' cae aquí
        import logging as _logging
        _log = _logging.getLogger('inventario.db_integrity')
        _log.critical(
            'DB CORRUPTA al startup · %s · RESTAURAR via '
            '/api/admin/emergency-restore', str(_e)[:200]
        )
    except Exception:
        pass

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
    if _usa_postgres():
        return  # en PostgreSQL los datos se cargan aparte (ver init_db)
    conn = db_connect()
    c = conn.cursor()
    seed_rrhh(c)
    conn.commit()
    conn.close()
