# database.py — inicialización de BD y seeds
# Fase B refactor: extraído de index.py
import os
import sqlite3
import random
from datetime import datetime

from config import DB_PATH


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
    try:
        c.execute("ALTER TABLE producciones ADD COLUMN presentacion TEXT DEFAULT ''")
    except: pass

    # ── CC Review table (COC-PRO-001 digital) ────────────────────
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

    # ── Inventario v2: costos, OC receipt, cuarentena, conteo ────
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


    # ── audit_log (Capa 0) ────────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 usuario TEXT, accion TEXT, tabla TEXT, registro_id TEXT,
                 detalle TEXT, ip TEXT, fecha TEXT)""")

    # ── Clientes + Producto Terminado (Capa 2) ────────────────────────────
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

    # ── ANIMUS PT reorder + recall ──────────────────────────────────────
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
    # ── Financiero (Capa 4) ──────────────────────────────────────────
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
        ('meta_caja_min', '50000000', 'Saldo mínimo de caja alerta (COP)'),
        ('cmv_pct_animus', '35', 'CMV % objetivo ÁNIMUS Lab'),
        ('cmv_pct_espagiria', '40', 'CMV % objetivo Espagiria'),
        ('nomina_mensual', '15000000', 'Nómina mensual estimada HHA Group (COP)'),
    ]
    for clave, valor, desc in configs:
        c.execute("INSERT OR IGNORE INTO flujo_config (clave,valor,descripcion) VALUES (?,?,?)", (clave, valor, desc))

    # ── SKUs Fernando Mesa con precios mayorista ──────────────────
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
        ('TRX-15', 'Tónico Reparador 15ml', 38000, 26600, 'unidad'),
        ('NIAC-30', 'Sérum Niacinamida 30ml', 55000, 38500, 'unidad'),
        ('AZHC-30', 'Sérum AZ+HC 30ml', 52000, 36400, 'unidad'),
        ('SBHA-30', 'Sérum Salicílico BHA 30ml', 48000, 33600, 'unidad'),
        ('ECEN-30', 'Sérum Encapsulado Centella 30ml', 58000, 40600, 'unidad'),
        ('EILU-30', 'Emulsión Iluminadora 30ml', 45000, 31500, 'unidad'),
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
                 ('CLI-001','ANIMUS Lab','ANIMUS','Interno','Sebastian Vargas',
                  'sebastianvargasisaza@gmail.com','Inmediato',0,datetime('now')),
                 ('CLI-002','Fernando Mesa','ANIMUS','Distribuidor','Fernando Mesa',
                  '','30 dias',0,datetime('now'))""")

    # ── MAQUILA 360 ──────────────────────────────────────────────
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

    # ── maquila tables ──────────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS maquila_prospectos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa TEXT NOT NULL,
        contacto TEXT DEFAULT '',
        email TEXT DEFAULT '',
        telefono TEXT DEFAULT '',
        producto_tipo TEXT DEFAULT '',
        etapa TEXT DEFAULT 'Contacto',
        notas TEXT DEFAULT '',
        valor_estimado REAL DEFAULT 0,
        fecha_contacto TEXT DEFAULT (date('now')),
        usuario TEXT DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS maquila_ordenes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa TEXT NOT NULL,
        producto TEXT NOT NULL,
        batch_size_kg REAL DEFAULT 0,
        fecha_inicio TEXT DEFAULT '',
        fecha_entrega TEXT DEFAULT '',
        estado TEXT DEFAULT 'Pendiente',
        valor_total REAL DEFAULT 0,
        observaciones TEXT DEFAULT '',
        fecha_creacion TEXT DEFAULT (date('now')),
        usuario TEXT DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS maquila_cotizaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa TEXT DEFAULT '',
        producto_tipo TEXT DEFAULT '',
        batch_size_kg REAL DEFAULT 0,
        costo_mp REAL DEFAULT 0,
        costo_proceso REAL DEFAULT 0,
        margen_pct REAL DEFAULT 0,
        valor_total REAL DEFAULT 0,
        fecha TEXT DEFAULT (date('now')),
        usuario TEXT DEFAULT ''
    )""")
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
    # ── Calidad BPM Digital — tablas ──────────────────────────────────────
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

    # ── MIGRACIÓN: ampliar schema proveedores ──────────────────────────────
    for _pc in ['nit TEXT','id_interno TEXT','direccion TEXT',
                'num_cuenta TEXT','tipo_cuenta TEXT','banco TEXT','cert_bancario TEXT',
                'estado_lpa TEXT','ultima_evaluacion TEXT','vencimiento_docs TEXT',
                'acuerdo_calidad TEXT','rut INTEGER DEFAULT 0','camara_comercio INTEGER DEFAULT 0',
                'concepto_compra TEXT']:
        try: c.execute(f'ALTER TABLE proveedores ADD COLUMN {_pc}')
        except Exception: pass

    # ── SEED: 67 proveedores del Listado Oficial ────────────────────────────
    _provs = [{'nombre': 'PRESQUIM SAS', 'nit': '800.167.047-5', 'direccion': 'Carrera 13 N° 90 – 36 Of. 702 bogota', 'telefono': '318 4155087', 'correo': 'ventas1@presquim.com', 'contacto': 'ANDRES PAVA', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '473469991912', 'tipo_cuenta': 'CORRIENTE', 'banco': 'DAVIVIENDA', 'cert_bancario': None, 'id_interno': 'PROV-001', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-10-20', 'venc_docs': None, 'acuerdo_calidad': '✅ Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'MEGA DISTRIBUCIONES', 'nit': '1130665584', 'direccion': 'Carrera 3 # 12-59 Pereira Risaralda', 'telefono': '320 4126407', 'correo': 'contactenos@megadistribuciones.co', 'contacto': 'VALENTINA', 'concepto': 'INSUMOS DE EPP', 'num_cuenta': '127300065852', 'tipo_cuenta': 'AHORROS DAMAS', 'banco': 'DAVIVIENDA', 'cert_bancario': None, 'id_interno': 'PROV-002', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-09', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'VARIEDADES E IMPORTACIONES', 'nit': '901675287', 'direccion': 'calle 13 paso ancho # 43-52', 'telefono': '300 4649945', 'correo': 'ROBINSONSOLI12@GMAIL.COM', 'contacto': 'ROBINSON', 'concepto': 'MATERIAL DE ENVASE', 'num_cuenta': '20500004705', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-003', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-05-16', 'venc_docs': None, 'acuerdo_calidad': '✅ Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'ALEJANDRO GIRALDO TORREZ (MEGA VISUAL)', 'nit': '1107097226', 'direccion': 'Cra. 4 #18-69, COMUNA 3, Cali, Valle del Cauca', 'telefono': '317 5168170', 'correo': 'alejandrogiraldotorrez@gmail.com', 'contacto': 'BRAYAN', 'concepto': 'ACONDICIONAMIENTO', 'num_cuenta': '73605958351', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-004', 'categoria': '🟠 Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-11-17', 'venc_docs': None, 'acuerdo_calidad': '✅ Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'AGENQUIMICOS', 'nit': '800032931', 'direccion': 'calle 18 # 5-60 b/ san nicolas', 'telefono': '322 6815561', 'correo': 'venta4@agenquimicos.com', 'contacto': 'ERIKA CARDONA', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '062-032931-00', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-005', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-21', 'venc_docs': None, 'acuerdo_calidad': '⏳ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'EVACOL SAS', 'nit': '900062992', 'direccion': 'CR 23 13 40 Y 13 100 BRR ARROYOHONDO', 'telefono': '310 2102738', 'correo': 'jgerentecontabilidad@evacol.com', 'contacto': 'LILIANA', 'concepto': 'ZAPATOS', 'num_cuenta': '80327543789', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-006', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-11', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'LIMPIASEO DISTRIBUCIONES CALI SAS', 'nit': '901285074', 'direccion': 'Calle 7 # 25-05 Barrio el Cedro', 'telefono': '314 6819571', 'correo': 'limpiaseodistribuciones@hotmail.com', 'contacto': 'BAYRON JANSANSOY', 'concepto': 'ASEO', 'num_cuenta': '75000000844', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-007', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-07', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'CFC CAFARCOL SAS', 'nit': '860047379', 'direccion': 'calle 13 paso ancho # 43-52', 'telefono': '300 4649945', 'correo': 'cali@mencris.com', 'contacto': 'ROBINSON', 'concepto': 'MATERIAL DE ENVASE 2', 'num_cuenta': '23791226921', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-008', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-16', 'venc_docs': None, 'acuerdo_calidad': '✅ Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'TWO GLASS SAS BIC', 'nit': '9018126525', 'direccion': 'Calle 13 # 27a - 05', 'telefono': '305 4591891', 'correo': 'twoglasssitioweb@gmail.com', 'contacto': 'ANGELICA ALEJO', 'concepto': 'ACONDICIONAMIENTO SERIGRAFIA', 'num_cuenta': '24136806040', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCO CAJA SOCIAL', 'cert_bancario': None, 'id_interno': 'PROV-009', 'categoria': '🟠 Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-11-14', 'venc_docs': None, 'acuerdo_calidad': '⏳ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'PACTO IMPRESOS SAS', 'nit': '901131621', 'direccion': 'Calle 45 N° 2N - 68', 'telefono': '318 4905322', 'correo': 'Comercial@pactoimpresores.com', 'contacto': 'CAROLINA VELEZ', 'concepto': 'ACONDICIONAMIENTO', 'num_cuenta': '06200005487', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-010', 'categoria': '🟠 Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-05', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'MICROLAB', 'nit': '805019040', 'direccion': 'AV 2 G NORTE 51 N 71 BRR LA MERCED', 'telefono': '320 6802368', 'correo': 'impuestosmicrolab@gmail.com', 'contacto': None, 'concepto': 'ANALISIS MICROBIOLOGICOS', 'num_cuenta': '83600003511', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-011', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-10-30', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'SOS NATURAL COLOMBIA SAS', 'nit': '901587640', 'direccion': 'FINCA MIS ANOS DORADOS VEREDA EL HOGAR', 'telefono': '314 3751521', 'correo': 'info.sosnatural@gmail.com', 'contacto': 'ANDREA', 'concepto': 'MATERIA PRIMA VERDE ARMONIA', 'num_cuenta': '06400003041', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-012', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-11-17', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'TIENDA HAIKU', 'nit': '900983721', 'direccion': 'Cra 58 # 169a - 55 LC 131 bogota', 'telefono': '314 2229116', 'correo': 'ventas@tiendahaiku.com', 'contacto': None, 'concepto': 'MATERIA PRIMA VERDE ARMONIA Y PRODUCCION AGOSTO', 'num_cuenta': '22300007095', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-013', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-09-26', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'ALARMAR LTDA', 'nit': '8909192674', 'direccion': 'CALLE 24 N  8N-10', 'telefono': '3168781340', 'correo': 'angele.padilla@alarmar.com.co', 'contacto': 'ANGELE PADILLA', 'concepto': 'ALARMA', 'num_cuenta': '391437829', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCO DE BOGOTA', 'cert_bancario': None, 'id_interno': 'PROV-014', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-02', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'POCHTECA COLOMBIA', 'nit': '900161367', 'direccion': 'CRA 19 # 82 - 85 OFICINA 305', 'telefono': '3123799010', 'correo': 'mcardenasm@pochteca.net', 'contacto': 'JOHANA', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '69935569787', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-015', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-10-08', 'venc_docs': None, 'acuerdo_calidad': '⏳ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'SUMINISTROS DE LABORATORIO KASALAB S.A.S', 'nit': '900745087', 'direccion': 'Cra. 1 No. 49-35', 'telefono': '317 4961234', 'correo': 'brianobregon@kasalab.com', 'contacto': 'BRIAN STIVEN OBREGON MEJIA', 'concepto': 'MORTEROS', 'num_cuenta': '27427058846', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-016', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-26', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'ANA MARISOL SALDARRIAGA (LIDER DISTRIBUCIONES)', 'nit': '66870504', 'direccion': 'CALLE 23  31  39 BARRIO SANTA MONICA', 'telefono': '3206641705', 'correo': 'liderdistribucionescali@gmail.com', 'contacto': 'Ana', 'concepto': 'ENVASES', 'num_cuenta': '06501042995', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-017', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-05-19', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'COMPAÑIA COLOMBIANA DE QUIMICOS', 'nit': '860049957', 'direccion': 'CALLE 12  38-62 BOGOTA', 'telefono': '321 4903630', 'correo': 'nicolle.villamil@colquimicos.com', 'contacto': 'NICOLLE VILLAMIL', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '03100057271', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-018', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-02', 'venc_docs': None, 'acuerdo_calidad': '✅ Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'CHEMY JAM COLOMBIA SAS', 'nit': '901180048', 'direccion': 'Calle 1C 40D79Bogota', 'telefono': '310 2180922', 'correo': 'chemy.jamcol@gmail.com', 'contacto': 'Alexandra', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '046101192', 'tipo_cuenta': 'AHORROS', 'banco': 'AV VILLAS', 'cert_bancario': None, 'id_interno': 'PROV-019', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-04', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'YANETH VARGAS RUEDA', 'nit': '66777565', 'direccion': 'KR 1 #32', 'telefono': '313 6864461', 'correo': 'qf.yanethvargasrueda@gmail.com', 'contacto': 'YANETH VARGAS RUEDA', 'concepto': 'INSPECCIONES', 'num_cuenta': '103848813', 'tipo_cuenta': 'AHORROS', 'banco': 'AV VILLAS', 'cert_bancario': None, 'id_interno': 'PROV-020', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-08', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'TIAN IPS SALUD OCUPACIONAL MEDICINA ALTE', 'nit': '900293402', 'direccion': 'CLL 47N # 3F-56 B/ VIPASA', 'telefono': '317 7687630', 'correo': 'servicliente@tianips.com', 'contacto': None, 'concepto': 'EXAMENES MEDICOS', 'num_cuenta': '06656365232', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-021', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-09-16', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'RODOLFO ANDRES SANCHEZ CONCHA (COMPETRI)', 'nit': '1130665584', 'direccion': 'CR 36 4 B 63', 'telefono': '3124035294', 'correo': 'COMPETRI@OUTLOOK.COM', 'contacto': 'ANDRES RODOLFO SANCHEZ', 'concepto': 'EPP', 'num_cuenta': '74510642809', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-022', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-10-13', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'IN CHEMICAL SAS', 'nit': '900653299', 'direccion': 'Calle 69 A # 88 A - 32', 'telefono': '350 7533246', 'correo': 'SERVICLIENTE@INCHEMICAL.COM', 'contacto': 'DIANA', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '24113130143', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-023', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-05-16', 'venc_docs': None, 'acuerdo_calidad': '✅ Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'DISTRIBUIDORA CORDOBA S A S', 'nit': '860000615', 'direccion': 'Carrera 8 N° 49-64', 'telefono': '323 254 0422', 'correo': 'contacto@discordoba.com', 'contacto': 'PAOLA ANDREA RAMIREZ', 'concepto': 'ENVASES AMBAR 50ML', 'num_cuenta': '22769151361', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-024', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-09-30', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'TAPETES Y PISOS DEL PACIFICO SAS', 'nit': '805007745', 'direccion': 'AV 5 B NORTE 22 N 18', 'telefono': '316 5289374', 'correo': 'contabilidad@tapetesypisos.com.co', 'contacto': 'GILMA OSSA', 'concepto': 'TAPETE', 'num_cuenta': '82500001444', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-025', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-30', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'LEVER ASESORES SAS', 'nit': '901910221', 'direccion': 'AV ESTACION 45 BN 127 OF201', 'telefono': '301 7296448', 'correo': 'Santiago.laharenas@leverlegal.com.co', 'contacto': 'SANTIAGO', 'concepto': 'FACTURA AGOSTO ABOGADOS', 'num_cuenta': '74900006437', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-026', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-10-23', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'CONNPLANTS', 'nit': '900473144-6', 'direccion': 'Cra. 6a #30-12, COMUNA 4, Cali, Valle del Cauca, Colombia', 'telefono': '300 7258390', 'correo': 'andres.ramirez@connplants.com', 'contacto': 'ANDRES RAMIREZ', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '82396710626', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-027', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-11-05', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'SERPROASEO', 'nit': '900104742', 'direccion': 'CR 98 B 42 29', 'telefono': '310 6125805', 'correo': 'serproaseocontable@gmail.com', 'contacto': 'Laura hoyos', 'concepto': 'ASEO', 'num_cuenta': '146122759', 'tipo_cuenta': 'CORRIENTE', 'banco': 'AV VILLAS', 'cert_bancario': None, 'id_interno': 'PROV-028', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-09-26', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'ASEO DEL SUROCCIDENTE S.A. ESP', 'nit': '900414483-6', 'direccion': 'CL 11A # 32 - 108 YUMBO', 'telefono': '315 4106896', 'correo': 'admon.suraseo@gmail.com', 'contacto': None, 'concepto': 'RECOLECCION RESIDUOS', 'num_cuenta': '51470270380', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-029', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-25', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'ALMADINA SAS', 'nit': '901274606', 'direccion': 'CALLE 41 # 74 - 59', 'telefono': '300 5058181', 'correo': 'contacto@almadina.com.co', 'contacto': 'MARCELA', 'concepto': 'ENVASES LIP GLOSS', 'num_cuenta': '29800024887', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-030', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-07', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'IMCD COLOMBIA SAS', 'nit': '800134597', 'direccion': 'Cra 19 #95-20, Bogotá, Colombia', 'telefono': '318 2473413', 'correo': 'nicolas.lugo@imcdcolombia.com', 'contacto': 'ALEJANDRA', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '20018798278', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-031', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-09-01', 'venc_docs': None, 'acuerdo_calidad': '⏳ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'AVA CHEMICAL SAS', 'nit': '9004485872', 'direccion': 'CALLE 17 103B 37 BOGOTA', 'telefono': None, 'correo': None, 'contacto': 'LYDA PATRICIA VANEGAS', 'concepto': 'MATERIA PRIMA ALEJANDRO', 'num_cuenta': '188725116', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-032', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-10-07', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'MERCADEO VALLE SAS', 'nit': '900777239', 'direccion': 'CR 85 A 17 83 P 1', 'telefono': '301 7901807', 'correo': 'mercadeovallecali@gmail.com', 'contacto': None, 'concepto': 'ESTELIRIZADOR DE AGUA', 'num_cuenta': '73632624309', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-033', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-21', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'PALMERA JUNIOR S.A.S.', 'nit': '900.405.705-8', 'direccion': 'AV 3N 45N 10 BRR LA MERCED', 'telefono': '315 3351762', 'correo': 'cartera2@palmerajunior.com', 'contacto': 'IBARRA VELASQUEZ EMMANUEL', 'concepto': 'FUMIGACION', 'num_cuenta': '06470292758', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-034', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-12-03', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'HANDLER SAS', 'nit': '900677390', 'direccion': 'CRA 97 # 24C-23 Bodega 3,', 'telefono': '3244118931', 'correo': 'sguzman@handlercolombia.com', 'contacto': 'santiago guzman alonson', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '237252022-31', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-035', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-12-18', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'LUISA DE MARILLAC GIRALDO OSPINA', 'nit': '42062642', 'direccion': 'calle 18 #4-79', 'telefono': '319 2197419', 'correo': None, 'contacto': 'GERARDO', 'concepto': 'CAJAS PLEGADIZAS', 'num_cuenta': '51402263591', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-036', 'categoria': '🟠 Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-05-12', 'venc_docs': None, 'acuerdo_calidad': '⏳ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'SCIENTIFIC PRODUCTS', 'nit': '805014913', 'direccion': 'Cra. 4b #36a-71, Cali,', 'telefono': '3176461543', 'correo': 'VENTAS7@SPLTAD.COM', 'contacto': 'HENERSON RAMIREZ', 'concepto': 'PICNOMETRO', 'num_cuenta': '07700007741', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-037', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-11-20', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'ANAYCO SAS', 'nit': '811004746', 'direccion': 'Cra. 84 #37 - 61 Medellín Santa Monica', 'telefono': '312 4926639', 'correo': 'ventas@anayco.net', 'contacto': None, 'concepto': 'PIE DE REY', 'num_cuenta': '07200093339', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-038', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-12-02', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'DIEMPAQUES SAS', 'nit': '900048343', 'direccion': 'Carrera 59 # 14 - 79 Bogotá', 'telefono': '320 8995397', 'correo': 'serviclientes5@diempaques.com', 'contacto': 'PATRICIA AVILA', 'concepto': 'MATERIAL ENVASE', 'num_cuenta': '18623963661', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-039', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-19', 'venc_docs': None, 'acuerdo_calidad': '⏳ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'SAA LAB SAS', 'nit': '901848807', 'direccion': 'carrera 47 # 64-70', 'telefono': '3007758234', 'correo': 'saalabsas@gmail.com', 'contacto': 'Liliana castrillon', 'concepto': 'ESTUDIOS DE ESTABILIDAD', 'num_cuenta': '58000009082', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-040', 'categoria': None, 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-11-04', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'SUMIQUIM', 'nit': '805002736', 'direccion': 'Calle 15 No. 35-75 Bodega 2A / Parque Empresarial Servicomex Express / Acopi Yumbo', 'telefono': '316 7488717', 'correo': 'kamelhernandez@sumiquim.com', 'contacto': 'Kamel Andrez Hernández', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '83606734524', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-041', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-26', 'venc_docs': None, 'acuerdo_calidad': '⏳ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'SU PROVEEDOR QUIMICO PREFERIDO SAS', 'nit': '805023874', 'direccion': 'Carrera 4 # 22 - 59', 'telefono': '304 4209373', 'correo': 'suproquimltda@hotmail.com', 'contacto': 'Stephanie', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '06120211617', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-042', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-05', 'venc_docs': None, 'acuerdo_calidad': '✅ Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'CROMAROMA SAS', 'nit': '860533213', 'direccion': 'Transversal 93 # 53-32 Bodega 52 Parque Empresarial El Dorado', 'telefono': '313 4213746', 'correo': 'ruby.millan@cromaroma.com.co', 'contacto': 'Ruby Millan', 'concepto': 'FRAGANCIA', 'num_cuenta': '20787774582', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-043', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-21', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'JULIAN ANDRES QUICENO VALENCIA', 'nit': '1053786250', 'direccion': 'Carrera 43A # 45SUR - 55 B/ Primavera.', 'telefono': '300 3046652', 'correo': 'ventas@bolsasyempaquescolombia.com', 'contacto': 'JULIAN ANDRES QUICENO VALENCIA', 'concepto': 'BOLSAS ZIPLOC', 'num_cuenta': '50651916574', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-044', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-18', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'IDENTIFIK TECNOLOGIA SAS', 'nit': '901191042', 'direccion': 'AV 5 AN DN 68 PASARELA LOCAL 232', 'telefono': '3192880714', 'correo': 'info@identifik.com.co', 'contacto': None, 'concepto': 'ROLLOS DE IMPRESORA', 'num_cuenta': '82595595092', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-045', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-04', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'G & M QUIMICA SAS', 'nit': '900023607', 'direccion': 'CALLE 33 No 9-47', 'telefono': '311 7390527', 'correo': 'ventas3@gmquimica.com', 'contacto': 'Gonzalez Suarez', 'concepto': 'MATERIA PRIMA', 'num_cuenta': '82388090710', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-046', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-11-21', 'venc_docs': None, 'acuerdo_calidad': '⏳ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'RUBIELA RESTREPO DIAZ (ITALPLAST)', 'nit': '29.899.054-1', 'direccion': 'CALLE 18 No. 8 39', 'telefono': '3117198086', 'correo': 'italplastcali@hotmail.com', 'contacto': 'Juan Alberto Ossa', 'concepto': 'CINTA', 'num_cuenta': '80375991181', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-047', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-04', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'CI BALANZAS DE COLOMBIA LTDA', 'nit': '805023451', 'direccion': 'CL 23   17 D   43', 'telefono': '317 6369154', 'correo': 'auxiliar2@cibalanzasdecolombia.com', 'contacto': None, 'concepto': 'ADAPTADOR', 'num_cuenta': '83712557288', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-048', 'categoria': '🟠 Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-05', 'venc_docs': None, 'acuerdo_calidad': '⏳ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'SIILP SAS', 'nit': '901.005.198-0', 'direccion': 'CALLE 43 # 111-45 401A, Cali', 'telefono': '315 5389307', 'correo': 'jsobregon@siilp.com', 'contacto': 'JUAN SEBASTIAN', 'concepto': 'SEGURIDAD Y SALUD EN EL TRABAJO', 'num_cuenta': '015700036070', 'tipo_cuenta': 'AHORROS', 'banco': 'DAVIVIENDA', 'cert_bancario': None, 'id_interno': 'PROV-049', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-02', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'VELCO INGENIERÍA Y SERVICIOS S.A.S', 'nit': '901827384-1', 'direccion': 'Carrera 23 A Bis No. 26 - 105 Cali Valle', 'telefono': '315 974 4777', 'correo': 'velcoingenieriayservicios@gmail.com', 'contacto': 'Luis Felipe Velasco', 'concepto': 'MANTENIMIENTO', 'num_cuenta': '76000003535', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-050', 'categoria': '🟠 Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-15', 'venc_docs': None, 'acuerdo_calidad': '✅ Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'INDUSTRIAS IMPERIO RIAÑOS SAS', 'nit': '901356657', 'direccion': 'Calle 16 #14-37', 'telefono': '3113494475', 'correo': 'industriasimperio2018@gmail.com', 'contacto': None, 'concepto': 'ESTANTERIAS', 'num_cuenta': '81500000624', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-051', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-03', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'ALUMINIO Y VIDRIOS', 'nit': '9006329412', 'direccion': 'Calle 9 No. 10 - 111 Barrio San Bosco', 'telefono': '316 471 0070', 'correo': 'contabilidad@vidriospormetro.com', 'contacto': 'Nidia gutierrez', 'concepto': 'ADECUACIONES LUZ', 'num_cuenta': None, 'tipo_cuenta': None, 'banco': None, 'cert_bancario': 'https://checkout.wompi.co/l/VPOS_guWoHx', 'id_interno': 'PROV-052', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-11', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'LUIS MIGUEL MEZA', 'nit': '1143961591', 'direccion': 'CALLE 13 #10-53', 'telefono': '3185597565', 'correo': 'alejito115m@gmail.com', 'contacto': 'LUIS MIGUEL MEZA', 'concepto': 'INSTALACION ESTANTERIAS', 'num_cuenta': '81579850761', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-053', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-12-12', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'SEGURITA SG S.A.S', 'nit': '901342162', 'direccion': 'CALLE 34 #1-64', 'telefono': '301 2613222', 'correo': 'seguritas@gmail.com', 'contacto': 'Daniela', 'concepto': 'TARROS DE BASURA', 'num_cuenta': '80700004928', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-054', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-06', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'SU PROVEEDOR QUIMICO PREFERIDO SAS', 'nit': '805023874', 'direccion': 'Carrera 4 # 22 - 59', 'telefono': '304 4209373', 'correo': 'suproquimltda@hotmail.com', 'contacto': 'Stephanie', 'concepto': 'MATERIA PRIMA  2', 'num_cuenta': '06120211617', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-055', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-10-13', 'venc_docs': None, 'acuerdo_calidad': '✅ Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'GOLDEN BUSINESS CLASS SA', 'nit': '900299296', 'direccion': 'Autopista via bogota-Medellin KM 2,5', 'telefono': '3107891300', 'correo': 'ventas4@goldengbc.com', 'contacto': 'Gina Liliana', 'concepto': 'MICAS', 'num_cuenta': '65078825979', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-056', 'categoria': '🔴 Crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-07-16', 'venc_docs': None, 'acuerdo_calidad': '⏳ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'TRS PARTES SA', 'nit': '900013663', 'direccion': 'Cra. 1 No. 49-35', 'telefono': '317 4961234', 'correo': 'julian.benavides@trspartes.com', 'contacto': 'JULIAN', 'concepto': 'FILTROS AIRES', 'num_cuenta': '30685260722', 'tipo_cuenta': 'AHORROS', 'banco': '74510642809', 'cert_bancario': None, 'id_interno': 'PROV-057', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-12-02', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'PAPELERIA UNIVERSAL\nDISTRIBUIDORA SAS', 'nit': '901.160.842-9', 'direccion': 'CRA 9 11 04', 'telefono': '315 8155803', 'correo': 'distribuidorauniversaldigital@gmail.com', 'contacto': 'CARDONA FERNANDEZ DIDALIA', 'concepto': 'PAPELERIA', 'num_cuenta': '017069991945', 'tipo_cuenta': 'CORRIENTE', 'banco': 'DAVIVIENDA', 'cert_bancario': None, 'id_interno': 'PROV-058', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-05-21', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'MUPRO INTERNACIONAL SAS', 'nit': '901803010', 'direccion': 'CALLE 7ª 24-25 San Nicolas', 'telefono': '317 7604440', 'correo': 'ANDRESSARRIADORADO@GMAIL.COM', 'contacto': 'ANDRES SARRIA DORADO', 'concepto': 'MESA PARA ACONDICIONAMIENTO', 'num_cuenta': '82100007872', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-059', 'categoria': '🟠 Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-11-12', 'venc_docs': None, 'acuerdo_calidad': '⏳ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'SIAMED', 'nit': '9017515033', 'direccion': None, 'telefono': '320 6931797', 'correo': 'gerenciatecnica@amedasesorias.com', 'contacto': 'JORGE CHARRY', 'concepto': 'CALIBRACIÓN', 'num_cuenta': '0550108900617151', 'tipo_cuenta': 'AHORROS DAMAS', 'banco': 'DAVIVIENDA', 'cert_bancario': None, 'id_interno': 'PROV-060', 'categoria': '🟠 Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-09-04', 'venc_docs': None, 'acuerdo_calidad': '✅ Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'HENRY DELGADO NAVAS (MERCURIO)', 'nit': '16583442', 'direccion': 'CRA 5 #18-74', 'telefono': '313 5784211', 'correo': 'graficasmercurio@gmail.com', 'contacto': 'LUZ MARINA PRADO', 'concepto': 'TINTAS Y SELOS', 'num_cuenta': '06213774889', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-061', 'categoria': '🟢 No crítico', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-09-24', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'UNIVERSIDAD SANTIAGO DE CALI', 'nit': '8903037971', 'direccion': 'Cl. 5 #62-00, Cuarto de Legua, Cali,', 'telefono': '314 8901580', 'correo': 'comercialmetrologia@usc.edu.co', 'contacto': 'Ingrid Galeano', 'concepto': 'CALIBRACIÓN BALANZA', 'num_cuenta': '484467436', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCO DE BOGOTA', 'cert_bancario': None, 'id_interno': 'PROV-062', 'categoria': '🟠 Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-06-10', 'venc_docs': None, 'acuerdo_calidad': None, 'rut': 0, 'cam_com': 0}, {'nombre': 'CODIFICACION & ETIQUETADO S A', 'nit': '830116638', 'direccion': 'Calle 23 116 31 Bodega 5 Bogota', 'telefono': '318 4999402', 'correo': 'paola.soto@coditeq.com', 'contacto': None, 'concepto': 'INYET', 'num_cuenta': '63830606281', 'tipo_cuenta': 'CORRIENTE', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-063', 'categoria': '🟠 Mayor', 'estado_lpa': 'Aprobado', 'ultima_eval': '2025-08-14', 'venc_docs': None, 'acuerdo_calidad': '⏳ Pendiente', 'rut': 0, 'cam_com': 0}, {'nombre': 'Hebei Yayoujia Packaging Products Co., Ltd.', 'nit': '91130402MAE4JBHG94', 'direccion': 'Room 913, Building B, No.18 Hanqi Building, Dongliu West Street, Hanshan District, Handan City, Hebei Province', 'telefono': '0086 17703203040', 'correo': 'yayoujia_sarah@163.com', 'contacto': 'Sarah Li', 'concepto': 'ENVASES CHINA', 'num_cuenta': None, 'tipo_cuenta': None, 'banco': None, 'cert_bancario': None, 'id_interno': 'PROV-064', 'categoria': '🔴 Crítico', 'estado_lpa': 'En Calificación', 'ultima_eval': 'Pendiente', 'venc_docs': None, 'acuerdo_calidad': '✅ Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'Shaanxi Yuantai Biological Technology Co., Ltd', 'nit': '916101323337510488', 'direccion': "No.801, Building3, Dahua Stock Smart Industrial Park,\nTiangu 6th Road, Yanta District, Xi ''an, Shaanxi, China", 'telefono': '(+)86 180 9215 6330', 'correo': 'allen@sxytbio.com', 'contacto': 'ICEY', 'concepto': 'MATERIA PRIMA CHINA', 'num_cuenta': None, 'tipo_cuenta': None, 'banco': None, 'cert_bancario': None, 'id_interno': 'PROV-065', 'categoria': '🔴 Crítico', 'estado_lpa': 'En Calificación', 'ultima_eval': 'Pendiente', 'venc_docs': None, 'acuerdo_calidad': '✅ Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'Shanghai Kaijin Packaging Products Co., Ltd.', 'nit': '91310117MA1J1KY537', 'direccion': 'Edificio A874, No. 2, Carril 158, Calle Gangye, Pueblo de Xiaokunshan, Distrito de Songjiang, Shanghái.', 'telefono': '(+)86 158 6832 7130', 'correo': None, 'contacto': 'ELLA', 'concepto': 'ENVASES CHINA', 'num_cuenta': None, 'tipo_cuenta': None, 'banco': None, 'cert_bancario': None, 'id_interno': 'PROV-066', 'categoria': '🔴 Crítico', 'estado_lpa': 'En Calificación', 'ultima_eval': 'Pendiente', 'venc_docs': None, 'acuerdo_calidad': '✅ Firmado', 'rut': 0, 'cam_com': 0}, {'nombre': 'GERMAN ALZATE RAMIREZ (GALILEO)', 'nit': '16774136', 'direccion': 'CR 4 18 01 LC 04', 'telefono': '311 3472771', 'correo': None, 'contacto': 'German Alzate', 'concepto': 'ACONDICIONAMIENTO ETIQUETAS', 'num_cuenta': '06225334402', 'tipo_cuenta': 'AHORROS', 'banco': 'BANCOLOMBIA', 'cert_bancario': None, 'id_interno': 'PROV-067', 'categoria': '🟠 Mayor', 'estado_lpa': 'En Calificación', 'ultima_eval': 'Pendiente', 'venc_docs': None, 'acuerdo_calidad': '✅ Firmado', 'rut': 0, 'cam_com': 0}]
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

    # ── SEED: 19 OCs Abril 2026 — estado Borrador (pendiente autorización) ─
    _ocs_abr = [('OC-260401', '2026-02-25', 'Revisada', 'CFC CAFARCOL SAS', 551781.0, 'Gotero blanco pipeta x520 para Fernando Meza — pago límite 14 abr', 'sistema', '2026-04-14', 'Envase'), ('OC-260304', '2026-03-04', 'Revisada', 'POCHTECA COLOMBIA', 197540.0, 'Materia prima — pago límite 14 abr', 'sistema', '2026-04-14', 'MPs'), ('OC-260402-ESP', '2026-04-14', 'Revisada', 'AGENQUIMICOS', 885999.99, 'Materia prima — pago límite 14 abr', 'sistema', '2026-04-14', 'MPs'), ('OC-260307', '2026-03-07', 'Revisada', 'IN CHEMICAL SAS', 702100.0, 'Materia prima — pago límite 14 abr', 'sistema', '2026-04-14', 'MPs'), ('OC-260202', '2026-02-02', 'Revisada', 'GYM QUIMICA', 250376.0, 'Materia prima — pago límite 16 abr', 'sistema', '2026-04-16', 'MPs'), ('OC-260301', '2026-03-01', 'Revisada', 'CHEMY JAM COLOMBIA SAS', 1203090.0, 'LEXFEEL WOW — pago límite 16 abr', 'sistema', '2026-04-16', 'MPs'), ('OC-260403', '2026-04-20', 'Revisada', 'SU PROVEEDOR QUIMICO PREFERIDO SAS', 530000.01, 'Propilenglicol — pago límite 20 abr', 'sistema', '2026-04-20', 'MPs'), ('OC-260406', '2026-04-17', 'Revisada', 'FLOW CHEM SAS', 202800.0, 'Detergentes BIOACID + PURE ACID MAX + PURE ALCA FORTE + flete', 'alejandro', '', 'Insumos'), ('OC-260402-ETQ', '2026-04-13', 'Revisada', 'CODIFICACION & ETIQUETADO S A', 1149730.0, 'Inject / codificación — pago límite 13 abr', 'sistema', '2026-04-13', 'Insumos'), ('OC-260320', '2026-03-20', 'Revisada', 'DUQUE SALDARRIAGA Y CIA SAS', 37100.63, 'Envases MRP — pago límite 17 abr', 'sistema', '2026-04-17', 'Envase'), ('OC-260313', '2026-03-13', 'Revisada', 'PLASTIVALLE SAS', 91159.95, 'Envase plástico — pago límite 13 abr', 'sistema', '2026-04-13', 'Envase'), ('OC-260317', '2026-03-17', 'Revisada', 'ALARMAR LTDA', 183837.71, 'Alarma mes de marzo — pago límite 15 abr', 'sistema', '2026-04-15', 'Servicios'), ('OC-260316', '2026-03-16', 'Revisada', 'MICROLAB', 2850706.72, 'Análisis microbiológicos — pago límite 18 abr', 'sistema', '2026-04-18', 'Análisis'), ('OC-260207', '2026-02-07', 'Revisada', 'PAPELERIA UNIVERSA SAS', 164600.21, 'Insumos papelería — pago límite 22 abr', 'sistema', '2026-04-22', 'Insumos'), ('OC-260309', '2026-03-09', 'Revisada', 'MOL LABS LTDA', 164220.0, 'Buffer pH — pago límite 22 abr', 'sistema', '2026-04-22', 'Análisis'), ('OC-260312', '2026-03-12', 'Revisada', 'CIEL TECHNOLOGY SAS', 1244850.0, 'Software CIEL — pago límite 22 abr', 'sistema', '2026-04-22', 'Servicios'), ('OC-251209', '2025-12-09', 'Revisada', 'DE LA PAVA Y COMPANIA SAS', 809200.0, 'Seguridad — pago límite 24 abr', 'sistema', '2026-04-24', 'Servicios'), ('OC-251216', '2025-12-16', 'Revisada', 'ARMEPLAS PRODALCA SAS', 2527322.0, 'Acondicionamiento / cañitas — pago límite 24 abr', 'sistema', '2026-04-24', 'Acondicionamiento'), ('OC-260127', '2026-01-27', 'Revisada', 'RACKETBALL SA', 389699.99, 'Laboratorios — pago límite 25 abr', 'sistema', '2026-04-25', 'Análisis')]
    for _oc in _ocs_abr:
        try:
            c.execute('''INSERT OR IGNORE INTO ordenes_compra
                (numero_oc,fecha,estado,proveedor,valor_total,observaciones,creado_por,fecha_entrega_est,categoria)
                VALUES(?,?,?,?,?,?,?,?,?)''', _oc)
        except Exception: pass
    # Actualizar OCs ya sembradas como Borrador → Revisada (pendiente autorización CEO)
    _oc_nums = ['OC-260401','OC-260304','OC-260402-ESP','OC-260307','OC-260202',
                'OC-260301','OC-260403','OC-260406','OC-260402-ETQ','OC-260320',
                'OC-260313','OC-260317','OC-260316','OC-260207','OC-260309',
                'OC-260312','OC-251209','OC-251216','OC-260127']
    try:
        c.executemany("UPDATE ordenes_compra SET estado='Revisada' WHERE numero_oc=? AND estado='Borrador'",
                      [(n,) for n in _oc_nums])
    except Exception: pass

    # ── SEED: Nóminas 1Q Abril 2026 ─────────────────────────────────────────
    _nominas = [
        ('2026-04-15','ANIMUS','Nómina personal ÁNIMUS Lab — 1Q Abril 2026',
         'Nómina',12651985.0,'2026-04','nomina','NOM-ANIMUS-1Q-ABR26','sistema',
         '8 empleados — Denis Alejandro Morales Restrepo + 7'),
        ('2026-04-15','ESPAGIRIA','Nómina personal Espagiria — 1Q Abril 2026',
         'Nómina',17339902.0,'2026-04','nomina','NOM-ESP-1Q-ABR26','sistema',
         '11 empleados — Hernando Acevedo + Luis Dorronsoro + 9'),
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
    seed_compromisos(c)
    # Dedup RRHH seed tables (run once, idempotent)
    try:
        c.execute("DELETE FROM sgsst_items WHERE id NOT IN (SELECT MIN(id) FROM sgsst_items GROUP BY descripcion)")
        c.execute("DELETE FROM capacitaciones WHERE id NOT IN (SELECT MIN(id) FROM capacitaciones GROUP BY nombre)")
        c.execute("DELETE FROM capacitaciones_empleados WHERE rowid NOT IN (SELECT MIN(rowid) FROM capacitaciones_empleados GROUP BY capacitacion_id, empleado_id)")
    except: pass
    conn.commit()
    conn.close()


def seed_compromisos(c):
    items = [
        ('Revisar procedimiento limpieza con Fredy — definicion aseo profundo','Miguel Valencia','Calidad','2026-04-17','Completado','Alta','ACTA-ESP-2026-04-14-001','Espagiria'),
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
    # Guard: solo ejecutar si la tabla está vacía
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
        ('BPM — Buenas Practicas de Manufactura Cosmeticos','BPM','2026-01-15',8,'INVIMA / ANDI','Espagiria',1),
        ('SGSST — Induccion y Reinduccion Seguridad','SGSST','2026-01-20',4,'ARL Sura','HHA Group',1),
        ('Manejo Seguro de Materias Primas Quimicas','SGSST','2026-02-10',6,'Proveedor externo','Espagiria',1),
        ('Atencion al Cliente y Comunicacion Efectiva','Blanda','2026-03-05',3,'Coach externo','HHA Group',0),
        ('Control de Calidad — Metodos Analiticos','Tecnica','2026-03-20',5,'Catalina Torres','Espagiria',1),
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
        ('Medicina del Trabajo','Examenes medicos periodicos — todo el personal','Anual','Catalina Torres','2026-06-30'),
        ('Medicina del Trabajo','Programa de vigilancia epidemiologica respiratoria','Semestral','Catalina Torres','2026-06-01'),
        ('Higiene Industrial','Medicion de iluminacion en planta y laboratorio','Anual','Alejandro Rios','2026-08-01'),
        ('Higiene Industrial','Evaluacion de exposicion a sustancias quimicas','Semestral','Catalina Torres','2026-06-15'),
        ('Seguridad','Inspeccion de instalaciones locativas y equipos','Trimestral','Alejandro Rios','2026-04-30'),
        ('Seguridad','Revision y dotacion de EPP — todo personal planta','Semestral','Alejandro Rios','2026-07-01'),
        ('Seguridad','Señalizacion de seguridad actualizada','Anual','Alejandro Rios','2026-09-01'),
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


def run_seed_rrhh():
    """Ejecuta seed_rrhh con su propia conexión (llamada al arranque)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    seed_rrhh(c)
    conn.commit()
    conn.close()
