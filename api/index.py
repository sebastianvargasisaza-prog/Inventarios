import os
import json
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'hha-group-2026-secretkey-x9kq')
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)
COMPRAS_USERS = {
    'sebastian': os.environ.get('PASS_SEBASTIAN', 'hha2026'),
    'alejandro': os.environ.get('PASS_ALEJANDRO', 'hha2026'),
    'catalina':  os.environ.get('PASS_CATALINA',  'hha2026'),
    'luz':       os.environ.get('PASS_LUZ',       'hha2026'),
    'mayra':     os.environ.get('PASS_MAYRA',     'hha2026'),
}
ADMIN_USERS = {'sebastian', 'alejandro'}
CONTADORA_USERS = {'mayra'}   # puede todo EXCEPTO Aprobar/Pagar OC


DB_PATH = os.environ.get('DB_PATH', '/var/data/inventario.db')

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
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_mee TEXT NOT NULL,
        tipo TEXT NOT NULL,
        cantidad REAL NOT NULL,
        referencia TEXT DEFAULT '',
        observaciones TEXT DEFAULT '',
        operador TEXT DEFAULT '',
        fecha TEXT NOT NULL
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


init_db()
conn2 = __import__("sqlite3").connect(__import__("os").environ.get("DB_PATH","/var/data/inventario.db")); c2 = conn2.cursor(); seed_rrhh(c2); conn2.commit(); conn2.close()

from templates_py.rrhh_html import RRHH_HTML

# ─── HUB HHA GROUP ────────────────────────────────────────────
from templates_py.compromisos_html import COMPROMISOS_HTML

from templates_py.home_html import HOME_HTML

from templates_py.hub_html import HUB_HTML

# ─── LOGIN COMPRAS ────────────────────────────────────────────
# ─── MÓDULO CLIENTES ──────────────────────────────────────────
from templates_py.clientes_html import CLIENTES_HTML

# ─── MÓDULO CALIDAD BPM ────────────────────────────────────────
CALIDAD_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Calidad BPM — Espagiria</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#F5F4F0;min-height:100vh;}
.topbar{background:#1d5c5a;color:white;padding:13px 24px;display:flex;align-items:center;justify-content:space-between;}
.topbar-title{font-weight:800;letter-spacing:2px;font-size:1em;}
.topbar a{color:rgba(255,255,255,0.75);text-decoration:none;font-size:0.82em;padding:6px 14px;border:1px solid rgba(255,255,255,0.25);border-radius:6px;}
.tabs{background:white;border-bottom:2px solid #e5e7eb;padding:0 24px;display:flex;gap:2px;overflow-x:auto;}
.tab{padding:13px 20px;cursor:pointer;font-size:0.87em;font-weight:600;color:#6b7280;border-bottom:3px solid transparent;white-space:nowrap;transition:all 0.15s;}
.tab.active{color:#1d5c5a;border-bottom-color:#1d5c5a;}
.tab:hover:not(.active){color:#1d5c5a;background:#f0fdf4;}
.page{display:none;}.page.active{display:block;}
.content{padding:24px;max-width:1200px;margin:0 auto;}
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:24px;}
.kpi{background:white;border-radius:12px;padding:18px 20px;border-left:4px solid var(--c,#1d5c5a);box-shadow:0 1px 4px rgba(0,0,0,0.06);}
.kv{font-size:2em;font-weight:900;color:var(--c,#1d5c5a);line-height:1;}
.kl{font-size:0.75em;color:#6b7280;text-transform:uppercase;letter-spacing:0.8px;margin-top:5px;}
table{width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;box-shadow:0 1px 5px rgba(0,0,0,0.06);}
thead th{background:#f9fafb;color:#374151;font-size:0.77em;text-transform:uppercase;letter-spacing:0.6px;padding:10px 13px;text-align:left;border-bottom:1px solid #e5e7eb;}
tbody td{padding:10px 13px;border-bottom:1px solid #f3f4f6;font-size:0.87em;vertical-align:middle;}
tbody tr:hover{background:#fafafa;}
tbody tr:last-child td{border-bottom:none;}
.btn{display:inline-flex;align-items:center;gap:5px;padding:8px 16px;border:none;border-radius:8px;cursor:pointer;font-size:0.85em;font-weight:600;background:#1d5c5a;color:white;transition:all 0.15s;}
.btn:hover{background:#164848;transform:translateY(-1px);}
.btn-ghost{background:white;color:#1d5c5a;border:1.5px solid #1d5c5a;}
.btn-ghost:hover{background:#f0fdf4;}
.btn-sm{padding:5px 11px;font-size:0.8em;}
.btn-danger{background:#dc2626;}.btn-danger:hover{background:#b91c1c;}
.badge{display:inline-block;padding:3px 9px;border-radius:10px;font-size:0.74em;font-weight:700;}
.b-ok{background:#d1fae5;color:#065f46;}.b-warn{background:#fef3c7;color:#92400e;}.b-err{background:#fee2e2;color:#991b1b;}.b-gris{background:#f3f4f6;color:#374151;}.b-azul{background:#dbeafe;color:#1e40af;}
.section{background:white;border-radius:12px;padding:20px;margin-bottom:20px;box-shadow:0 1px 4px rgba(0,0,0,0.05);}
.section-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;}
.section-hdr h2{font-size:0.95em;font-weight:700;color:#111827;}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;}
.form-grid.triple{grid-template-columns:1fr 1fr 1fr;}
.fg label{display:block;font-size:0.78em;font-weight:700;color:#4b5563;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.4px;}
.fg input,.fg select,.fg textarea{width:100%;padding:8px 11px;border:1.5px solid #d1d5db;border-radius:7px;font-size:0.87em;background:#fafafa;transition:border 0.15s;}
.fg input:focus,.fg select:focus,.fg textarea:focus{outline:none;border-color:#1d5c5a;background:white;}
.msg{padding:10px 14px;border-radius:7px;margin:8px 0;font-size:0.85em;font-weight:600;}
.msg-ok{background:#d1fae5;color:#065f46;}.msg-err{background:#fee2e2;color:#991b1b;}
.empty{text-align:center;color:#9ca3af;padding:32px;font-size:0.88em;}
.panel-form{display:none;background:#f8fafc;border:1px solid #e5e7eb;border-radius:10px;padding:18px;margin-bottom:16px;}
</style>
</head>
<body>
<div class="topbar">
  <a href="/">&#8592; Inicio</a>
  <span class="topbar-title">&#x2705; CALIDAD BPM — Espagiria</span>
  <span style="font-size:0.8em;opacity:0.7;">Coordinadora: Catalina Torres</span>
</div>
<div class="tabs">
  <div class="tab active" data-tab="tab-dash">&#x1F4CA; Dashboard</div>
  <div class="tab" data-tab="tab-cc">&#x1F9EA; Control de Calidad MP</div>
  <div class="tab" data-tab="tab-nc">&#x26A0; No Conformidades</div>
  <div class="tab" data-tab="tab-cal">&#x1F4CF; Calibraciones</div>
</div>

<div class="content">

<!-- DASHBOARD -->
<div id="tab-dash" class="page active">
  <div class="kpi-row" id="kpi-cc">
    <div class="kpi" style="--c:#d97706"><div class="kv" id="kv-cuarentena">—</div><div class="kl">Lotes en Cuarentena</div></div>
    <div class="kpi" style="--c:#16a34a"><div class="kv" id="kv-aprobados">—</div><div class="kl">Aprobados (30d)</div></div>
    <div class="kpi" style="--c:#dc2626"><div class="kv" id="kv-rechazados">—</div><div class="kl">Rechazados (30d)</div></div>
    <div class="kpi" style="--c:#7c3aed"><div class="kv" id="kv-nc">—</div><div class="kl">NC Abiertas</div></div>
    <div class="kpi" style="--c:#dc2626"><div class="kv" id="kv-cals">—</div><div class="kl">Calibraciones Vencidas</div></div>
  </div>
  <div class="section">
    <div class="section-hdr"><h2>&#x1F4CB; Actividad reciente de calidad</h2></div>
    <div id="dash-actividad"><p class="empty">Cargando...</p></div>
  </div>
</div>

<!-- CONTROL DE CALIDAD MP -->
<div id="tab-cc" class="page">
  <div class="section">
    <div class="section-hdr"><h2>&#x1F9EA; Lotes de MP en Cuarentena — Pendientes de Revision CC</h2></div>
    <p style="font-size:0.83em;color:#6b7280;margin-bottom:14px;">Lotes recibidos que aun no han sido aprobados o rechazados por Control de Calidad.</p>
    <div id="cc-cuarentena-list"><p class="empty">Cargando...</p></div>
  </div>
</div>

<!-- NO CONFORMIDADES -->
<div id="tab-nc" class="page">
  <div class="section">
    <div class="section-hdr">
      <h2>&#x26A0; No Conformidades</h2>
      <button class="btn btn-ghost btn-sm" onclick="togglePanel('form-nc')">+ Registrar NC</button>
    </div>
    <!-- Form NC -->
    <div id="form-nc" class="panel-form">
      <div class="form-grid triple">
        <div class="fg"><label>Tipo</label>
          <select id="nc-tipo">
            <option value="MP">Materia Prima</option>
            <option value="PT">Producto Terminado</option>
            <option value="Proceso">Proceso</option>
            <option value="Proveedor">Proveedor</option>
            <option value="Infraestructura">Infraestructura</option>
            <option value="SGSST">SGSST</option>
          </select></div>
        <div class="fg"><label>Area</label>
          <select id="nc-area">
            <option>Produccion</option><option>Calidad</option><option>Almacen</option>
            <option>Logistica</option><option>Administracion</option></select></div>
        <div class="fg"><label>Impacto</label>
          <select id="nc-impacto"><option>Menor</option><option>Mayor</option><option>Critico</option></select></div>
      </div>
      <div class="form-grid">
        <div class="fg"><label>Lote / Referencia (opcional)</label><input type="text" id="nc-lote" placeholder="Ej: L-2026-001 o OC-260401"></div>
        <div class="fg"><label>Responsable</label><input type="text" id="nc-resp" placeholder="Nombre del responsable"></div>
      </div>
      <div class="fg" style="margin-bottom:10px;"><label>Descripcion de la No Conformidad</label>
        <textarea id="nc-desc" rows="3" placeholder="Describir detalladamente el hallazgo..."></textarea></div>
      <div class="fg" style="margin-bottom:12px;"><label>Accion Correctiva propuesta</label>
        <textarea id="nc-accion" rows="2" placeholder="Accion para eliminar la causa raiz..."></textarea></div>
      <button class="btn" onclick="registrarNC()">&#x2713; Registrar No Conformidad</button>
      <div id="nc-msg"></div>
    </div>
    <!-- Lista NC -->
    <div id="nc-list"><p class="empty">Cargando...</p></div>
  </div>
</div>

<!-- CALIBRACIONES -->
<div id="tab-cal" class="page">
  <div class="section">
    <div class="section-hdr"><h2>&#x1F4CF; Calibraciones de Instrumentos</h2></div>
    <p style="font-size:0.83em;color:#6b7280;margin-bottom:14px;">Estado de calibracion de equipos de medicion criticos. Frecuencia recomendada: cada 6 meses.</p>
    <div id="cal-list"><p class="empty">Cargando...</p></div>
  </div>
</div>

</div><!-- /content -->
<script>
// ─── Tab routing ──────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(function(t){
  t.addEventListener('click', function(){
    var id = t.getAttribute('data-tab');
    document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active');});
    document.querySelectorAll('.page').forEach(function(p){p.classList.remove('active');});
    t.classList.add('active');
    document.getElementById(id).classList.add('active');
    if(id==='tab-dash') loadDash();
    if(id==='tab-cc') loadCuarentena();
    if(id==='tab-nc') loadNC();
    if(id==='tab-cal') loadCal();
  });
});
function togglePanel(id){var el=document.getElementById(id);el.style.display=el.style.display==='block'?'none':'block';}
function fmt(n){return n?('$'+parseFloat(n).toLocaleString('es-CO')):'—';}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function showMsg(id,msg,type){var el=document.getElementById(id);if(el){el.innerHTML='<div class="msg msg-'+(type||'ok')+'">'+msg+'</div>';setTimeout(function(){el.innerHTML='';},4000);}}

// ─── Dashboard ────────────────────────────────────────────────────
async function loadDash(){
  try{
    var d=await fetch('/api/calidad/dashboard').then(function(r){return r.json();});
    document.getElementById('kv-cuarentena').textContent=d.cuarentena||0;
    document.getElementById('kv-aprobados').textContent=d.aprobados_30d||0;
    document.getElementById('kv-rechazados').textContent=d.rechazados_30d||0;
    document.getElementById('kv-nc').textContent=d.nc_abiertas||0;
    document.getElementById('kv-cals').textContent=d.cals_vencidas||0;
    var el=document.getElementById('dash-actividad');
    var act=d.actividad_reciente||[];
    if(!act.length){el.innerHTML='<p class="empty">Sin actividad reciente registrada.</p>';return;}
    var h='<table><thead><tr><th>Fecha</th><th>Tipo</th><th>Material / Detalle</th><th>Lote</th><th>Resultado</th><th>Firmante</th></tr></thead><tbody>';
    act.forEach(function(a){
      var bclass=a.estado==='APROBADO'||a.estado==='Aprobado'?'b-ok':a.estado==='RECHAZADO'||a.estado==='Rechazado'?'b-err':'b-warn';
      h+='<tr><td style="color:#6b7280;">'+(a.fecha||'').slice(0,16)+'</td>'
        +'<td><span class="badge b-azul">'+esc(a.tipo||'CC')+'</span></td>'
        +'<td><strong>'+esc(a.material||a.descripcion||'—')+'</strong></td>'
        +'<td style="font-family:monospace;font-size:0.85em;">'+esc(a.lote||'—')+'</td>'
        +'<td><span class="badge '+bclass+'">'+esc(a.estado||'—')+'</span></td>'
        +'<td>'+esc(a.firmante||a.responsable||'—')+'</td></tr>';
    });
    h+='</tbody></table>';
    el.innerHTML=h;
  }catch(e){document.getElementById('dash-actividad').innerHTML='<p class="empty" style="color:#dc2626;">Error al cargar</p>';}
}

// ─── Control Calidad MP (Cuarentena) ─────────────────────────────
async function loadCuarentena(){
  var el=document.getElementById('cc-cuarentena-list');
  el.innerHTML='<p class="empty">Cargando...</p>';
  try{
    var d=await fetch('/api/recepcion/lotes-cuarentena').then(function(r){return r.json();});
    if(!d.length){el.innerHTML='<div style="background:#d1fae5;border-radius:10px;padding:20px;text-align:center;font-weight:600;color:#065f46;">&#x2713; Sin lotes pendientes de revision CC.</div>';return;}
    var h='<table><thead><tr><th>Material</th><th>Lote</th><th>Cantidad</th><th>Proveedor</th><th>F.Ingreso</th><th>Vence</th><th>OC</th><th>Accion CC</th></tr></thead><tbody>';
    d.forEach(function(l){
      var fv=l.fecha_vencimiento?(l.fecha_vencimiento).slice(0,10):'—';
      h+='<tr><td><strong>'+esc(l.material_nombre||l.material_id)+'</strong></td>'
        +'<td style="font-family:monospace;">'+esc(l.lote||'—')+'</td>'
        +'<td>'+Number(l.cantidad||0).toLocaleString('es-CO')+'g</td>'
        +'<td>'+esc(l.proveedor||'—')+'</td>'
        +'<td style="color:#6b7280;">'+(l.fecha||'').slice(0,10)+'</td>'
        +'<td>'+fv+'</td>'
        +'<td style="font-family:monospace;font-size:0.82em;">'+esc(l.numero_oc||'—')+'</td>'
        +'<td style="white-space:nowrap;">'
        +'<button class="btn btn-sm" style="background:#16a34a;margin-right:4px;" onclick="aprobarLoteCC('+l.id+',\\'Aprobado\\')">&#x2713; Aprobar</button>'
        +'<button class="btn btn-sm btn-danger" onclick="aprobarLoteCC('+l.id+',\\'Rechazado\\')">&#x2717; Rechazar</button>'
        +'</td></tr>';
    });
    h+='</tbody></table>';
    el.innerHTML=h;
  }catch(e){el.innerHTML='<p class="empty" style="color:#dc2626;">Error: '+e.message+'</p>';}
}

async function aprobarLoteCC(movId, estado){
  if(!confirm('Confirmar: marcar lote como '+estado+'?')) return;
  try{
    var r=await fetch('/api/recepcion/aprobar-lote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mov_id:movId,estado:estado})});
    var d=await r.json();
    if(d.ok){loadCuarentena();loadDash();}
    else alert('Error: '+(d.error||'desconocido'));
  }catch(e){alert('Error: '+e.message);}
}

// ─── No Conformidades ────────────────────────────────────────────
async function registrarNC(){
  var desc=document.getElementById('nc-desc').value.trim();
  if(!desc){showMsg('nc-msg','Descripcion requerida','err');return;}
  var payload={
    tipo:document.getElementById('nc-tipo').value,
    area:document.getElementById('nc-area').value,
    impacto:document.getElementById('nc-impacto').value,
    lote:document.getElementById('nc-lote').value.trim(),
    responsable:document.getElementById('nc-resp').value.trim(),
    descripcion:desc,
    accion_correctiva:document.getElementById('nc-accion').value.trim()
  };
  try{
    var r=await fetch('/api/calidad/no-conformidades',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    var d=await r.json();
    if(d.ok){
      showMsg('nc-msg','No Conformidad registrada con ID #'+d.id,'ok');
      document.getElementById('nc-desc').value='';
      document.getElementById('nc-accion').value='';
      document.getElementById('nc-lote').value='';
      loadNC();
    }else{showMsg('nc-msg','Error: '+(d.error||'desconocido'),'err');}
  }catch(e){showMsg('nc-msg','Error: '+e.message,'err');}
}

async function loadNC(){
  var el=document.getElementById('nc-list');
  el.innerHTML='<p class="empty">Cargando...</p>';
  try{
    var d=await fetch('/api/calidad/no-conformidades').then(function(r){return r.json();});
    var ncs=d.no_conformidades||[];
    if(!ncs.length){el.innerHTML='<p class="empty">Sin No Conformidades registradas.</p>';return;}
    var h='<table><thead><tr><th>ID</th><th>Fecha</th><th>Tipo</th><th>Area</th><th>Impacto</th><th>Descripcion</th><th>Responsable</th><th>Estado</th><th>Accion</th></tr></thead><tbody>';
    ncs.forEach(function(nc){
      var bimpacto=nc.impacto==='Critico'?'b-err':(nc.impacto==='Mayor'?'b-warn':'b-gris');
      var bestado=nc.estado==='Cerrada'?'b-ok':(nc.estado==='En proceso'?'b-azul':'b-warn');
      h+='<tr><td style="font-family:monospace;font-weight:700;color:#7c3aed;">#'+nc.id+'</td>'
        +'<td style="color:#6b7280;">'+(nc.fecha||'').slice(0,10)+'</td>'
        +'<td><span class="badge b-azul">'+esc(nc.tipo)+'</span></td>'
        +'<td>'+esc(nc.area)+'</td>'
        +'<td><span class="badge '+bimpacto+'">'+esc(nc.impacto)+'</span></td>'
        +'<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="'+esc(nc.descripcion)+'">'+esc(nc.descripcion)+'</td>'
        +'<td>'+esc(nc.responsable||'—')+'</td>'
        +'<td><span class="badge '+besta+'">'+esc(nc.estado)+'</span></td>'
        +'<td>'+(nc.estado!=='Cerrada'?'<button class="btn btn-sm" style="background:#16a34a;" onclick="cerrarNC('+nc.id+')">Cerrar</button>':'<span style="color:#16a34a;">&#x2713;</span>')+'</td>'
        +'</tr>';
    });
    h+='</tbody></table>';
    el.innerHTML=h;
  }catch(e){el.innerHTML='<p class="empty" style="color:#dc2626;">Error: '+e.message+'</p>';}
}

async function cerrarNC(ncId){
  var accion=prompt('Accion correctiva aplicada (o confirmar si ya esta ingresada):');
  if(accion===null) return;
  try{
    var r=await fetch('/api/calidad/no-conformidades/'+ncId+'/cerrar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({accion_correctiva:accion})});
    var d=await r.json();
    if(d.ok) loadNC();
    else alert('Error: '+(d.error||'desconocido'));
  }catch(e){alert('Error: '+e.message);}
}

// ─── Calibraciones ────────────────────────────────────────────────
async function loadCal(){
  var el=document.getElementById('cal-list');
  el.innerHTML='<p class="empty">Cargando...</p>';
  try{
    var d=await fetch('/api/calidad/calibraciones').then(function(r){return r.json();});
    var cals=d.calibraciones||[];
    if(!cals.length){el.innerHTML='<p class="empty">Sin calibraciones registradas.</p>';return;}
    var hoy=new Date().toISOString().slice(0,10);
    var h='<table><thead><tr><th>Instrumento</th><th>Codigo</th><th>Ubicacion</th><th>Ultima Cal.</th><th>Proxima Cal.</th><th>Responsable</th><th>Estado</th></tr></thead><tbody>';
    cals.forEach(function(c){
      var vencida=c.fecha_proxima&&c.fecha_proxima<hoy;
      var pronto=!vencida&&c.fecha_proxima&&c.fecha_proxima<=(new Date(Date.now()+30*86400000).toISOString().slice(0,10));
      var bclass=vencida?'b-err':(pronto?'b-warn':'b-ok');
      var elabel=vencida?'Vencida':(pronto?'Proxima':'Vigente');
      h+='<tr style="'+(vencida?'background:#fff5f5;':'')+(pronto&&!vencida?'background:#fffbeb;':'')+'"><td><strong>'+esc(c.instrumento)+'</strong></td>'
        +'<td style="font-family:monospace;font-size:0.85em;">'+esc(c.codigo||'—')+'</td>'
        +'<td>'+esc(c.ubicacion||'—')+'</td>'
        +'<td style="color:#6b7280;">'+(c.fecha_ultima||'—')+'</td>'
        +'<td style="font-weight:600;">'+(c.fecha_proxima||'—')+'</td>'
        +'<td>'+esc(c.responsable||'—')+'</td>'
        +'<td><span class="badge '+bclass+'">'+elabel+'</span></td>'
        +'</tr>';
    });
    h+='</tbody></table>';
    el.innerHTML=h;
  }catch(e){el.innerHTML='<p class="empty" style="color:#dc2626;">Error: '+e.message+'</p>';}
}

// ─── Init ─────────────────────────────────────────────────────────
loadDash();
</script>
</body>
</html>"""

# ─── MÓDULO CALIDAD BPM ────────────────────────────────────────
CALIDAD_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Calidad BPM — Espagiria</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#0f172a;color:#e2e8f0;font-size:14px;min-height:100vh;}
.topbar{background:#1e293b;border-bottom:1px solid #334155;padding:12px 24px;display:flex;align-items:center;gap:16px;}
.logo{font-size:0.85em;font-weight:900;letter-spacing:3px;color:#fff;}
.badge{background:rgba(43,122,120,0.4);color:#7ACFCC;padding:3px 12px;border-radius:20px;font-size:0.7em;font-weight:700;letter-spacing:1px;}
.topbar a{color:rgba(255,255,255,0.45);text-decoration:none;font-size:0.78em;padding:5px 12px;border:1px solid rgba(255,255,255,0.12);border-radius:6px;margin-left:auto;}
.topbar a:hover{color:#fff;border-color:rgba(255,255,255,0.35);}
.tabs{display:flex;gap:0;background:#1e293b;border-bottom:1px solid #334155;padding:0 24px;}
.tab{padding:11px 20px;font-size:0.78em;font-weight:700;letter-spacing:.5px;color:#64748b;cursor:pointer;border-bottom:2px solid transparent;text-transform:uppercase;}
.tab.active{color:#7ACFCC;border-bottom-color:#7ACFCC;}
.tab:hover{color:#cbd5e1;}
.main{padding:24px;max-width:1300px;margin:0 auto;}
.kpi-row{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:24px;}
.kpi{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px 20px;flex:1;min-width:140px;}
.kpi-label{font-size:0.68em;text-transform:uppercase;letter-spacing:1.5px;color:#64748b;margin-bottom:6px;}
.kpi-val{font-size:2em;font-weight:800;color:#f1f5f9;}
.kpi-val.warn{color:#fb923c;}
.kpi-val.crit{color:#f87171;}
.kpi-val.good{color:#4ade80;}
.kpi-sub{font-size:0.7em;color:#475569;margin-top:3px;}
.card{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:18px;margin-bottom:16px;}
.card-title{font-size:0.7em;text-transform:uppercase;letter-spacing:1.5px;color:#64748b;margin-bottom:14px;font-weight:700;}
table{width:100%;border-collapse:collapse;}
th{font-size:0.67em;text-transform:uppercase;letter-spacing:.8px;color:#475569;padding:8px 10px;text-align:left;border-bottom:1px solid #334155;}
td{padding:9px 10px;font-size:0.82em;border-bottom:1px solid #1e293b;color:#cbd5e1;vertical-align:top;}
tr:hover td{background:#0f172a;}
.badge-verde{background:#052e16;color:#4ade80;padding:2px 10px;border-radius:20px;font-size:0.72em;font-weight:700;}
.badge-amarillo{background:#451a03;color:#fcd34d;padding:2px 10px;border-radius:20px;font-size:0.72em;font-weight:700;}
.badge-rojo{background:#450a0a;color:#fca5a5;padding:2px 10px;border-radius:20px;font-size:0.72em;font-weight:700;}
.badge-gris{background:#1e293b;color:#94a3b8;padding:2px 10px;border-radius:20px;font-size:0.72em;font-weight:700;border:1px solid #334155;}
.btn{padding:7px 16px;border-radius:7px;border:none;font-size:0.78em;font-weight:700;cursor:pointer;letter-spacing:.3px;}
.btn-primary{background:#2B7A78;color:#fff;}
.btn-primary:hover{background:#1e5c5a;}
.btn-danger{background:#7f1d1d;color:#fca5a5;}
.btn-danger:hover{background:#991b1b;}
.btn-sm{padding:4px 10px;font-size:0.72em;}
.form-row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px;align-items:flex-end;}
.form-group{display:flex;flex-direction:column;gap:4px;flex:1;min-width:160px;}
label{font-size:0.7em;text-transform:uppercase;letter-spacing:.8px;color:#64748b;font-weight:700;}
input,select,textarea{background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:7px 10px;border-radius:7px;font-size:0.82em;width:100%;}
input:focus,select:focus,textarea:focus{outline:none;border-color:#7ACFCC;}
textarea{resize:vertical;min-height:70px;}
.pane{display:none;} .pane.active{display:block;}
.empty{color:#475569;text-align:center;padding:32px;font-size:0.85em;}
.actividad{display:flex;flex-direction:column;gap:8px;}
.act-item{background:#0f172a;border-radius:8px;padding:10px 14px;border:1px solid #1e293b;display:flex;align-items:flex-start;gap:10px;}
.act-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;margin-top:4px;}
.dot-verde{background:#4ade80;} .dot-rojo{background:#f87171;} .dot-amari{background:#fcd34d;}
.act-body{flex:1;}
.act-title{font-size:0.78em;font-weight:700;color:#e2e8f0;}
.act-sub{font-size:0.68em;color:#64748b;margin-top:1px;}
.alert-box{background:#450a0a;border:1px solid #7f1d1d;border-radius:8px;padding:10px 14px;margin-bottom:12px;color:#fca5a5;font-size:0.8em;}
</style>
</head>
<body>
<div class="topbar">
  <span class="logo">ESPAGIRIA</span>
  <span class="badge">CALIDAD BPM</span>
  <a href="/">&#8592; Inicio</a>
</div>
<div class="tabs">
  <div class="tab active" onclick="goTab('tab-dash')">Dashboard</div>
  <div class="tab" onclick="goTab('tab-cc')">&#x1F9EA; Control Calidad MP</div>
  <div class="tab" onclick="goTab('tab-nc')">&#x26A0; No Conformidades</div>
  <div class="tab" onclick="goTab('tab-cal')">&#x1F527; Calibraciones</div>
</div>
<div class="main">

<!-- ── DASHBOARD ─────────────────────────────────────── -->
<div id="tab-dash" class="pane active">
  <div class="kpi-row">
    <div class="kpi"><div class="kpi-label">Lotes en Cuarentena</div><div class="kpi-val warn" id="kv-cuarentena">—</div><div class="kpi-sub">Pendientes CC</div></div>
    <div class="kpi"><div class="kpi-label">Aprobados (30d)</div><div class="kpi-val good" id="kv-aprobados">—</div><div class="kpi-sub">Lotes aprobados</div></div>
    <div class="kpi"><div class="kpi-label">Rechazados (30d)</div><div class="kpi-val crit" id="kv-rechazados">—</div><div class="kpi-sub">Lotes rechazados</div></div>
    <div class="kpi"><div class="kpi-label">NC Abiertas</div><div class="kpi-val warn" id="kv-nc">—</div><div class="kpi-sub">No conformidades</div></div>
    <div class="kpi"><div class="kpi-label">Calibraciones Vencidas</div><div class="kpi-val crit" id="kv-cals">—</div><div class="kpi-sub">Requieren accion</div></div>
  </div>
  <div class="card">
    <div class="card-title">Actividad Reciente</div>
    <div class="actividad" id="act-list"><p class="empty">Cargando...</p></div>
  </div>
</div>

<!-- ── CONTROL CALIDAD MP (cuarentena) ───────────────── -->
<div id="tab-cc" class="pane">
  <div class="card">
    <div class="card-title">Lotes en Cuarentena — Pendientes de Revision</div>
    <table>
      <thead><tr><th>MP / Lote</th><th>Cantidad</th><th>Proveedor</th><th>Fec. Vencimiento</th><th>OC</th><th>Accion</th></tr></thead>
      <tbody id="cc-tbody"><tr><td colspan="6" class="empty">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>

<!-- ── NO CONFORMIDADES ─────────────────────────────── -->
<div id="tab-nc" class="pane">
  <div class="card">
    <div class="card-title">Registrar No Conformidad</div>
    <div class="form-row">
      <div class="form-group"><label>Tipo</label><select id="nc-tipo"><option>Proceso</option><option>Producto</option><option>Proveedor</option><option>Equipo</option><option>Documentacion</option></select></div>
      <div class="form-group"><label>Area</label><select id="nc-area"><option>Produccion</option><option>Laboratorio</option><option>Calidad</option><option>Administrativa</option><option>Almacen</option></select></div>
      <div class="form-group"><label>Impacto</label><select id="nc-impacto"><option>Bajo</option><option>Medio</option><option>Alto</option><option>Critico</option></select></div>
    </div>
    <div class="form-row">
      <div class="form-group" style="flex:2"><label>Descripcion</label><textarea id="nc-desc" placeholder="Describir la no conformidad detectada..."></textarea></div>
      <div class="form-group"><label>Responsable</label><input id="nc-responsable" placeholder="Nombre responsable"/></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Lote (si aplica)</label><input id="nc-lote" placeholder="Ej: LOT-001"/></div>
      <div class="form-group"><label>Codigo MP (si aplica)</label><input id="nc-mp" placeholder="Ej: MPMP00001"/></div>
      <div class="form-group"><label>Accion Correctiva</label><textarea id="nc-accion" placeholder="Accion inmediata tomada..." style="min-height:50px"></textarea></div>
    </div>
    <button class="btn btn-primary" onclick="registrarNC()">Registrar NC</button>
  </div>
  <div class="card">
    <div class="card-title">Historial de No Conformidades</div>
    <table>
      <thead><tr><th>ID</th><th>Fecha</th><th>Tipo</th><th>Area</th><th>Descripcion</th><th>Impacto</th><th>Estado</th><th>Accion</th></tr></thead>
      <tbody id="nc-tbody"><tr><td colspan="8" class="empty">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>

<!-- ── CALIBRACIONES ────────────────────────────────── -->
<div id="tab-cal" class="pane">
  <div class="card">
    <div class="card-title">Instrumentos y Equipos — Estado de Calibracion</div>
    <table>
      <thead><tr><th>Instrumento</th><th>Codigo</th><th>Ubicacion</th><th>Ultima Cal.</th><th>Proxima Cal.</th><th>Responsable</th><th>Certificado</th><th>Estado</th></tr></thead>
      <tbody id="cal-tbody"><tr><td colspan="8" class="empty">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>

</div><!-- /main -->

<script>
function esc(s){const d=document.createElement('div');d.appendChild(document.createTextNode(s||''));return d.innerHTML;}
function fmt(d){return d?d.substring(0,10):'—';}

function goTab(id){
  document.querySelectorAll('.tab').forEach((t,i)=>{
    const ids=['tab-dash','tab-cc','tab-nc','tab-cal'];
    t.classList.toggle('active',ids[i]===id);
  });
  document.querySelectorAll('.pane').forEach(p=>p.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  if(id==='tab-dash') loadDash();
  else if(id==='tab-cc') loadCuarentena();
  else if(id==='tab-nc') loadNC();
  else if(id==='tab-cal') loadCal();
}

async function loadDash(){
  try{
    const r=await fetch('/api/calidad/dashboard');
    const d=await r.json();
    document.getElementById('kv-cuarentena').textContent=d.cuarentena||0;
    document.getElementById('kv-aprobados').textContent=d.aprobados||0;
    document.getElementById('kv-rechazados').textContent=d.rechazados||0;
    document.getElementById('kv-nc').textContent=d.nc_abiertas||0;
    document.getElementById('kv-cals').textContent=d.cals_vencidas||0;
    const act=document.getElementById('act-list');
    const items=(d.actividad_reciente||[]);
    if(!items.length){act.innerHTML='<p class="empty">Sin actividad reciente</p>';return;}
    act.innerHTML=items.map(a=>`
      <div class="act-item">
        <div class="act-dot dot-${a.color||'verde'}"></div>
        <div class="act-body">
          <div class="act-title">${esc(a.titulo)}</div>
          <div class="act-sub">${esc(a.subtitulo||'')} ${a.fecha?'&middot; '+fmt(a.fecha):''}</div>
        </div>
      </div>`).join('');
  }catch(e){document.getElementById('act-list').innerHTML='<p class="empty">Error: '+esc(e.message)+'</p>';}
}

async function loadCuarentena(){
  const tbody=document.getElementById('cc-tbody');
  try{
    const r=await fetch('/api/recepcion/lotes-cuarentena');
    const rows=await r.json();
    if(!rows.length){tbody.innerHTML='<tr><td colspan="6" class="empty">No hay lotes en cuarentena</td></tr>';return;}
    tbody.innerHTML=rows.map(l=>`<tr>
      <td><strong>${esc(l.material_nombre)}</strong><br><small style="color:#64748b">${esc(l.lote||'sin lote')}</small></td>
      <td>${esc(String(l.cantidad))} g</td>
      <td>${esc(l.proveedor||'—')}</td>
      <td>${fmt(l.fecha_vencimiento)}</td>
      <td>${esc(l.numero_oc||'—')}</td>
      <td style="display:flex;gap:6px">
        <button class="btn btn-primary btn-sm" data-aprobar="${l.id}" data-estado="Aprobado">Aprobar</button>
        <button class="btn btn-danger btn-sm" data-aprobar="${l.id}" data-estado="Rechazado">Rechazar</button>
      </td>
    </tr>`).join('');
  }catch(e){tbody.innerHTML='<tr><td colspan="6" class="empty">Error: '+esc(e.message)+'</td></tr>';}
}

document.addEventListener('click',async function(e){
  const btn=e.target.closest('[data-aprobar]');
  if(!btn) return;
  const movId=btn.dataset.aprobar;
  const estado=btn.dataset.estado;
  if(!confirm('Confirmar: '+estado+' este lote?')) return;
  try{
    const r=await fetch('/api/recepcion/aprobar-lote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mov_id:movId,estado})});
    if(r.ok) loadCuarentena();
    else alert('Error al actualizar');
  }catch(e){alert('Error: '+e.message);}
});

async function registrarNC(){
  const desc=document.getElementById('nc-desc').value.trim();
  if(!desc){alert('La descripcion es obligatoria');return;}
  const body={
    tipo:document.getElementById('nc-tipo').value,
    area:document.getElementById('nc-area').value,
    impacto:document.getElementById('nc-impacto').value,
    descripcion:desc,
    responsable:document.getElementById('nc-responsable').value,
    lote:document.getElementById('nc-lote').value,
    codigo_mp:document.getElementById('nc-mp').value,
    accion_correctiva:document.getElementById('nc-accion').value
  };
  try{
    const r=await fetch('/api/calidad/no-conformidades',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(r.ok){
      ['nc-desc','nc-responsable','nc-lote','nc-mp','nc-accion'].forEach(id=>document.getElementById(id).value='');
      loadNC();
    } else {const d=await r.json();alert(d.error||'Error al registrar');}
  }catch(e){alert('Error: '+e.message);}
}

async function loadNC(){
  const tbody=document.getElementById('nc-tbody');
  try{
    const r=await fetch('/api/calidad/no-conformidades');
    const rows=await r.json();
    if(!rows.length){tbody.innerHTML='<tr><td colspan="8" class="empty">No hay no conformidades registradas</td></tr>';return;}
    tbody.innerHTML=rows.map(nc=>{
      const bestado=nc.estado==='Abierta'?'badge-amarillo':(nc.estado==='Cerrada'?'badge-verde':'badge-gris');
      const bimpacto=nc.impacto==='Critico'?'badge-rojo':(nc.impacto==='Alto'?'badge-amarillo':'badge-gris');
      return `<tr>
        <td>#${nc.id}</td>
        <td>${fmt(nc.fecha)}</td>
        <td>${esc(nc.tipo)}</td>
        <td>${esc(nc.area)}</td>
        <td>${esc(nc.descripcion)}</td>
        <td><span class="${bimpacto}">${esc(nc.impacto)}</span></td>
        <td><span class="${bestado}">${esc(nc.estado)}</span></td>
        <td>${nc.estado==='Abierta'?`<button class="btn btn-sm btn-primary" data-cerrar-nc="${nc.id}">Cerrar</button>`:'—'}</td>
      </tr>`;
    }).join('');
  }catch(e){tbody.innerHTML='<tr><td colspan="8" class="empty">Error: '+esc(e.message)+'</td></tr>';}
}

document.addEventListener('click',async function(ev){
  const btn=ev.target.closest('[data-cerrar-nc]');
  if(!btn) return;
  const ncid=btn.dataset.cerrarNc;
  if(!confirm('Cerrar esta no conformidad?')) return;
  try{
    const r=await fetch('/api/calidad/no-conformidades/'+ncid+'/cerrar',{method:'POST'});
    if(r.ok) loadNC();
    else alert('Error al cerrar NC');
  }catch(e){alert('Error: '+e.message);}
});

async function loadCal(){
  const tbody=document.getElementById('cal-tbody');
  try{
    const r=await fetch('/api/calidad/calibraciones');
    const rows=await r.json();
    if(!rows.length){tbody.innerHTML='<tr><td colspan="8" class="empty">No hay instrumentos registrados</td></tr>';return;}
    tbody.innerHTML=rows.map(c=>{
      const bs=c.estado==='Vigente'?'badge-verde':(c.estado==='Vencida'?'badge-rojo':'badge-amarillo');
      const hoy=new Date().toISOString().substring(0,10);
      const vence=c.fecha_proxima&&c.fecha_proxima<hoy;
      return `<tr>
        <td><strong>${esc(c.instrumento)}</strong></td>
        <td>${esc(c.codigo)}</td>
        <td>${esc(c.ubicacion)}</td>
        <td>${fmt(c.fecha_ultima)}</td>
        <td style="${vence?'color:#f87171;font-weight:700':''}">${fmt(c.fecha_proxima)}</td>
        <td>${esc(c.responsable)}</td>
        <td><small style="color:#64748b">${esc(c.certificado||'—')}</small></td>
        <td><span class="${bs}">${esc(c.estado)}</span></td>
      </tr>`;
    }).join('');
  }catch(e){tbody.innerHTML='<tr><td colspan="8" class="empty">Error: '+esc(e.message)+'</td></tr>';}
}

loadDash();
</script>
</body>
</html>"""

# ─── MÓDULO HQ GERENCIA ────────────────────────────────────────
from templates_py.gerencia_html import GERENCIA_HTML

# ─── MÓDULO FINANCIERO ────────────────────────────────────────
from templates_py.financiero_html import FINANCIERO_HTML

from templates_py.login_html import LOGIN_HTML

# ─── MÓDULO COMPRAS ───────────────────────────────────────────
from templates_py.compras_html import COMPRAS_HTML

RECEPCION_HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Recepcion de Mercancia - Espagiria</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#f8f7f5;color:#1C1917;font-size:14px;}
.topbar{background:#292524;color:#fff;padding:12px 20px;display:flex;align-items:center;gap:16px;}
.topbar h1{font-size:18px;font-weight:600;}
.topbar a{color:#a8a29e;text-decoration:none;font-size:13px;}
.topbar a:hover{color:#fff;}
.topbar .hub-link{background:#4A6741;color:#fff;padding:6px 14px;border-radius:6px;font-size:12px;font-weight:600;}
.topbar .hub-link:hover{background:#3a5331;}
.container{max-width:1100px;margin:0 auto;padding:20px;}
.card{background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:20px;margin-bottom:20px;}
.card h2{font-size:16px;font-weight:600;margin-bottom:14px;color:#292524;display:flex;align-items:center;gap:8px;}
.oc-queue{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px;margin-bottom:16px;}
.oc-card{background:#fafaf9;border:1px solid #e7e5e4;border-radius:8px;padding:12px;cursor:pointer;transition:all .15s;}
.oc-card:hover{border-color:#57534e;background:#f5f5f4;}
.oc-card .oc-num{font-weight:700;font-size:13px;color:#292524;}
.oc-card .oc-prov{font-size:12px;color:#78716c;margin-top:2px;}
.oc-card .oc-val{font-size:12px;color:#4A6741;font-weight:600;margin-top:4px;}
.oc-card .oc-dias{font-size:11px;color:#a8a29e;}
.search-row{display:flex;gap:10px;align-items:center;margin-bottom:16px;}
.search-row input{flex:1;max-width:320px;padding:9px 12px;border:1px solid #d6d3d1;border-radius:6px;font-size:14px;}
.search-row input:focus{outline:none;border-color:#57534e;}
.btn{padding:9px 18px;border:none;border-radius:6px;font-size:14px;cursor:pointer;font-weight:500;}
.btn-primary{background:#292524;color:#fff;}
.btn-primary:hover{background:#1c1917;}
.btn-success{background:#16a34a;color:#fff;}
.btn-success:hover{background:#15803d;}
.btn-print{background:#1e40af;color:#fff;}
.btn-print:hover{background:#1d4ed8;}
.oc-info{background:#fafaf9;border:1px solid #e7e5e4;border-radius:8px;padding:14px;margin-bottom:16px;display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;}
.oc-info .lbl{font-size:11px;color:#78716c;text-transform:uppercase;letter-spacing:.5px;}
.oc-info .val{font-size:14px;font-weight:600;color:#292524;margin-top:2px;}
.badge{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;}
.badge-autorizada{background:#fef3c7;color:#92400e;}
.badge-pagada{background:#d1fae5;color:#065f46;}
.badge-recibida{background:#dbeafe;color:#1e40af;}
.badge-borrador{background:#f3f4f6;color:#374151;}
table{width:100%;border-collapse:collapse;font-size:13px;}
th{background:#f5f5f4;padding:9px 12px;text-align:left;font-weight:600;color:#57534e;border-bottom:1px solid #e7e5e4;}
td{padding:8px 12px;border-bottom:1px solid #f5f5f4;vertical-align:middle;}
tr:hover td{background:#fafaf9;}
td input[type=number]{width:100px;padding:5px 8px;border:1px solid #d6d3d1;border-radius:5px;font-size:13px;}
td input[type=number]:focus{outline:none;border-color:#57534e;}
td select{padding:5px 8px;border:1px solid #d6d3d1;border-radius:5px;font-size:13px;background:#fff;}
td input[type=text]{width:100%;padding:5px 8px;border:1px solid #d6d3d1;border-radius:5px;font-size:13px;}
.row-ok td{background:#f0fdf4;}
.row-disc td{background:#fff7ed;}
.row-falta td{background:#fef2f2;}
.obs-row{margin-top:12px;}
.obs-row label{font-size:13px;font-weight:600;display:block;margin-bottom:6px;color:#292524;}
.obs-row textarea{width:100%;padding:9px 12px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;resize:vertical;min-height:72px;}
.receptor-row{display:flex;gap:12px;align-items:center;margin-top:12px;}
.receptor-row label{font-size:13px;font-weight:600;white-space:nowrap;color:#292524;}
.receptor-row input{flex:1;max-width:260px;padding:8px 12px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;}
.submit-row{margin-top:16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;}
.msg{font-size:13px;padding:8px 14px;border-radius:6px;}
.msg-ok{background:#d1fae5;color:#065f46;}
.msg-err{background:#fee2e2;color:#991b1b;}
.tabs{display:flex;gap:2px;margin-bottom:16px;border-bottom:2px solid #e7e5e4;}
.tab-btn{padding:9px 18px;border:none;background:none;font-size:13px;font-weight:500;color:#78716c;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;}
.tab-btn.active{color:#292524;border-bottom-color:#292524;}
.tab-btn:hover{color:#292524;}
.tab-content{display:none;}
.tab-content.active{display:block;}
.empty{text-align:center;padding:32px;color:#a8a29e;font-size:13px;}
.cnt-badge{display:inline-block;background:#292524;color:#fff;border-radius:20px;font-size:11px;padding:1px 7px;margin-left:4px;}
.disc{color:#dc2626;font-weight:600;}
.valor{font-family:'Courier New',monospace;font-size:12px;}
.progress-bar{background:#e7e5e4;border-radius:4px;height:6px;margin-top:4px;}
.progress-fill{background:#16a34a;height:6px;border-radius:4px;transition:width .3s;}
.item-pct{font-size:11px;color:#78716c;margin-top:2px;}
.icon-ok{color:#16a34a;font-size:16px;}
.icon-disc{color:#d97706;font-size:16px;}
.icon-falta{color:#dc2626;font-size:16px;}
</style>
</head>
<body>
<div class="topbar">
  <a href="/" class="hub-link">&#8592; Inicio</a>
  <h1>&#128230; Recepcion de Mercancia</h1>
</div>
<div class="container">

  <div class="card">
    <h2>&#9203; OCs Pendientes de Recepcion</h2>
    <div id="queue-list"><p style="color:#a8a29e;font-size:13px;">Cargando...</p></div>
  </div>

  <div class="card">
    <h2>&#128269; Registrar Recepcion</h2>
    <div class="search-row">
      <input type="text" id="oc-input" placeholder="Numero de OC (ej: OC-2026-001)" onkeydown="if(event.key==='Enter')buscarOC()">
      <button class="btn btn-primary" onclick="buscarOC()">Buscar OC</button>
    </div>
    <div id="oc-msg"></div>

    <div id="oc-section" style="display:none">
      <div class="oc-info" id="oc-header"></div>
      <div style="overflow-x:auto;">
        <table>
          <thead>
            <tr>
              <th style="width:36px;"></th>
              <th>Material</th>
              <th>Solicitado</th>
              <th>Cantidad Recibida</th>
              <th>Diferencia</th>
              <th>% Cumpl.</th>
              <th>Estado</th>
              <th>Lote</th>
              <th>Vence</th>
              <th>Notas</th>
            </tr>
          </thead>
          <tbody id="items-body"></tbody>
        </table>
      </div>

      <div class="receptor-row">
        <label for="receptor-input">Recibido por:</label>
        <input type="text" id="receptor-input" placeholder="Tu nombre">
      </div>

      <div class="obs-row">
        <label>Observaciones generales:</label>
        <textarea id="obs-input" placeholder="Ej: Caja exterior golpeada pero producto en buen estado. Falto 1 item."></textarea>
      </div>

      <div class="submit-row">
        <button class="btn btn-success" onclick="registrarRecepcion()">&#10003; Registrar Recepcion</button>
        <div id="submit-msg"></div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>&#128202; Monitoreo: Pagado - Llego?</h2>
    <div class="tabs">
      <button class="tab-btn active" id="tab-btn-transito" onclick="showTab('transito')">
        En Transito <span class="cnt-badge" id="cnt-transito">0</span>
      </button>
      <button class="tab-btn" id="tab-btn-parcial" onclick="showTab('parcial')">
        Parciales <span class="cnt-badge" id="cnt-parcial">0</span>
      </button>
      <button class="tab-btn" id="tab-btn-recibidas" onclick="showTab('recibidas')">
        Recibidas <span class="cnt-badge" id="cnt-recibidas">0</span>
      </button>
      <button class="tab-btn" id="tab-btn-disc" onclick="showTab('disc')">
        Con Discrepancias <span class="cnt-badge" id="cnt-disc">0</span>
      </button>
    </div>
    <div id="tab-transito" class="tab-content active"></div>
    <div id="tab-parcial" class="tab-content"></div>
    <div id="tab-recibidas" class="tab-content"></div>
    <div id="tab-disc" class="tab-content"></div>
  </div>

  <div class="card">
    <h2>&#9203; Lotes en Cuarentena</h2>
    <p style="font-size:12px;color:#78716c;margin-bottom:12px;">Lotes recibidos pendientes de aprobacion de Control de Calidad.</p>
    <div id="cuarentena-list"><p style="color:#a8a29e;font-size:13px;">Cargando...</p></div>
  </div>

  <div class="card">
    <h2>&#128269; Trazabilidad de Lote</h2>
    <div class="search-row">
      <input type="text" id="lote-input" placeholder="Numero de lote (ej: L-2026-001)" onkeydown="if(event.key==='Enter')buscarLote()">
      <button class="btn btn-primary" onclick="buscarLote()">Buscar</button>
    </div>
    <div id="lote-result" style="margin-top:12px;"></div>
  </div>

</div>
<script>
var currentOC = null;

async function loadQueue() {
  try {
    var r = await fetch('/api/recepcion/seguimiento');
    var all = await r.json();
    if (!Array.isArray(all)) all = [];
    var pendientes = all.filter(function(x) {
      return (x.estado === 'Autorizada' && (!x.fecha_recepcion || x.fecha_recepcion.length < 3)) || x.estado === 'Parcial';
    });
    var el = document.getElementById('queue-list');
    if (pendientes.length === 0) {
      el.innerHTML = '<p style="color:#a8a29e;font-size:13px;">Sin OCs pendientes de recepcion.</p>';
      return;
    }
    var today = new Date();
    var html = '<div class="oc-queue">';
    pendientes.forEach(function(oc) {
      var dt = oc.fecha ? new Date(oc.fecha) : null;
      var dias = dt ? Math.floor((today - dt) / 86400000) : 0;
      html += '<div class="oc-card" onclick="cargarOC(\\'\'  + oc.numero_oc + '\\\')">'
        + '<div class="oc-num">' + oc.numero_oc + '</div>'
        + '<div class="oc-prov">' + (oc.proveedor || '') + '</div>'
        + '<div class="oc-val">$' + Number(oc.valor_total||0).toLocaleString() + '</div>'
        + '<div class="oc-dias">' + (dias > 0 ? dias + 'd en transito' : 'Reciente') + '</div>'
        + '</div>';
    });
    html += '</div>';
    el.innerHTML = html;
  } catch(e) { console.error(e); }
}

function cargarOC(num) {
  document.getElementById('oc-input').value = num;
  buscarOC();
  document.getElementById('oc-section').scrollIntoView({behavior:'smooth'});
}

async function buscarOC() {
  var num = document.getElementById('oc-input').value.trim().toUpperCase();
  if (!num) return;
  showMsg('oc-msg', '', '');
  try {
    var r = await fetch('/api/recepcion/detalle/' + encodeURIComponent(num));
    var d = await r.json();
    if (!r.ok || d.error) {
      showMsg('oc-msg', d.error || 'OC no encontrada', 'err');
      document.getElementById('oc-section').style.display = 'none';
      return;
    }
    currentOC = d;
    renderOC(d);
    document.getElementById('oc-section').style.display = 'block';
  } catch(e) { showMsg('oc-msg', 'Error de red: ' + e.message, 'err'); }
}

function getItemIcon(est, pct) {
  if (est === 'OK' && pct >= 100) return '<span class="icon-ok">&#10003;</span>';
  if (est === 'Danado' || est === 'NoLlego') return '<span class="icon-falta">&#10007;</span>';
  if (pct < 100 || est !== 'OK') return '<span class="icon-disc">&#9888;</span>';
  return '';
}

function renderOC(d) {
  var badgeCls = 'badge-' + (d.estado||'').toLowerCase();
  document.getElementById('oc-header').innerHTML =
    '<div><div class="lbl">OC</div><div class="val">' + d.numero_oc + '</div></div>' +
    '<div><div class="lbl">Proveedor</div><div class="val">' + d.proveedor + '</div></div>' +
    '<div><div class="lbl">Fecha</div><div class="val">' + (d.fecha||'').slice(0,10) + '</div></div>' +
    '<div><div class="lbl">Estado</div><div class="val"><span class="badge ' + badgeCls + '">' + d.estado + '</span></div></div>' +
    '<div><div class="lbl">Valor Total</div><div class="val">$' + Number(d.valor_total||0).toLocaleString() + '</div></div>' +
    '<div><div class="lbl">Categoria</div><div class="val">' + (d.categoria||'MP') + '</div></div>';

  var tbody = document.getElementById('items-body');
  tbody.innerHTML = '';
  var items = d.items || [];
  for (var idx = 0; idx < items.length; idx++) {
    (function(i, it) {
      var unidad = (d.categoria === 'MEE') ? 'uds' : 'g';
      var prevRec = (it.cantidad_recibida_g > 0) ? it.cantidad_recibida_g : it.cantidad_g;
      var pct = it.cantidad_g > 0 ? Math.round(prevRec / it.cantidad_g * 100) : 100;
      var tr = document.createElement('tr');
      tr.id = 'item-row-' + i;
      tr.innerHTML =
        '<td style="text-align:center;">' + getItemIcon('OK', pct) + '</td>' +
        '<td><strong>' + it.nombre_mp + '</strong><br><small style="color:#78716c">' + it.codigo_mp + '</small></td>' +
        '<td class="valor">' + Number(it.cantidad_g||0).toLocaleString() + ' ' + unidad + '</td>' +
        '<td><input type="number" id="cant-' + i + '" data-codigo="' + it.codigo_mp + '" data-sol="' + it.cantidad_g + '" value="' + prevRec + '" min="0" step="0.01" oninput="updateRow(' + i + ')"></td>' +
        '<td id="dif-' + i + '" class="valor" style="font-weight:600;"></td>' +
        '<td><div class="progress-bar"><div class="progress-fill" id="prog-' + i + '" style="width:' + Math.min(pct,100) + '%"></div></div><div class="item-pct" id="pct-' + i + '">' + pct + '%</div></td>' +
        '<td><select id="est-' + i + '" onchange="updateRow(' + i + ')">' +
          '<option value="OK">OK - Conforme</option>' +
          '<option value="Incompleto">Incompleto</option>' +
          '<option value="Danado">Danado</option>' +
          '<option value="NoLlego">No llego</option>' +
        '</select></td>' +
        '<td><input type="text" id="lote-' + i + '" placeholder="Ej: L-2026-001" style="width:110px;"></td>' +
        '<td><input type="date" id="fv-' + i + '" style="width:130px;"></td>' +
        '<td><input type="text" id="nota-' + i + '" placeholder="Observacion opcional"></td>';
      tbody.appendChild(tr);
      updateRow(i);
    })(idx, items[idx]);
  }
}

function updateRow(i) {
  var cantEl = document.getElementById('cant-' + i);
  var estEl = document.getElementById('est-' + i);
  var progEl = document.getElementById('prog-' + i);
  var pctEl = document.getElementById('pct-' + i);
  var difEl = document.getElementById('dif-' + i);
  var row = document.getElementById('item-row-' + i);
  if (!cantEl) return;
  var sol = parseFloat(cantEl.dataset.sol) || 0;
  var rec = parseFloat(cantEl.value) || 0;
  var est = estEl ? estEl.value : 'OK';
  var pct = sol > 0 ? Math.round(rec / sol * 100) : 100;
  var dif = rec - sol;
  if (difEl) {
    if (Math.abs(dif) < 0.001) { difEl.textContent = '\u2713'; difEl.style.color = '#16a34a'; }
    else if (dif < 0) { difEl.textContent = dif.toLocaleString(); difEl.style.color = '#dc2626'; }
    else { difEl.textContent = '+' + dif.toLocaleString(); difEl.style.color = '#d97706'; }
  }
  if (progEl) { progEl.style.width = Math.min(pct,100) + '%'; progEl.style.background = pct >= 100 ? '#16a34a' : pct > 50 ? '#d97706' : '#dc2626'; }
  if (pctEl) pctEl.textContent = pct + '%';
  if (row) { row.className = (est === 'OK' && pct >= 100) ? 'row-ok' : (est === 'Danado' || est === 'NoLlego' || pct === 0) ? 'row-falta' : 'row-disc'; }
}

async function registrarRecepcion() {
  if (!currentOC) return;
  var obs = document.getElementById('obs-input').value.trim();
  var receptor = document.getElementById('receptor-input').value.trim();
  if (!receptor) { showMsg('submit-msg', 'Ingresa quien recibe la mercancia', 'err'); return; }
  var items = [];
  var discrepancias = false;
  var ocItems = currentOC.items || [];
  for (var idx = 0; idx < ocItems.length; idx++) {
    var it = ocItems[idx];
    var cantEl = document.getElementById('cant-' + idx);
    var estEl = document.getElementById('est-' + idx);
    var notaEl = document.getElementById('nota-' + idx);
    var cant = cantEl ? (parseFloat(cantEl.value) || 0) : 0;
    var est = estEl ? estEl.value : 'OK';
    var nota = notaEl ? notaEl.value.trim() : '';
    var loteEl = document.getElementById('lote-' + idx);
    var fvEl = document.getElementById('fv-' + idx);
    var lote = loteEl ? loteEl.value.trim() : '';
    var fv = fvEl ? fvEl.value.trim() : '';
    if (est !== 'OK' || cant < it.cantidad_g) discrepancias = true;
    items.push({codigo_mp: it.codigo_mp, cantidad_recibida: cant, estado: est, notas: nota, lote: lote, fecha_vencimiento: fv});
  }
  var payload = {
    observaciones_recepcion: obs,
    tiene_discrepancias: discrepancias ? 1 : 0,
    items_recepcion: items,
    receptor_nombre: receptor
  };
  showMsg('submit-msg', 'Registrando...', '');
  try {
    var r = await fetch('/api/ordenes-compra/' + encodeURIComponent(currentOC.numero_oc) + '/recibir', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)
    });
    var d = await r.json();
    if (d.ok) {
      var discMsg = discrepancias ? ' \u26a0 Con discrepancias.' : '';
      var parcialMsg = d.parcial ? ' \u26a1 Recepcion PARCIAL — OC sigue abierta para completar.' : '';
      showMsg('submit-msg', 'Recepcion registrada. ' + (d.ingresos||0) + ' item(s) ingresado(s).' + discMsg + parcialMsg, 'ok');
      var submitRow = document.querySelector('.submit-row');
      if (submitRow) {
        var printBtn = document.createElement('button');
        printBtn.className = 'btn btn-print';
        printBtn.textContent = '🖨 Imprimir Acta de Recepcion';
        printBtn.onclick = function() { imprimirActaRecepcion(currentOC, payload, d); };
        submitRow.appendChild(printBtn);
      }
      document.getElementById('oc-section').style.display = 'none';
      currentOC = null;
      document.getElementById('oc-input').value = '';
      document.getElementById('obs-input').value = '';
      loadMonitoreo();
      loadQueue();
      loadCuarentena();
    } else {
      showMsg('submit-msg', d.error || 'Error al registrar', 'err');
    }
  } catch(e) { showMsg('submit-msg', 'Error de red: ' + e.message, 'err'); }
}

function imprimirActaRecepcion(oc, payload, result) {
  var w = window.open('', '_blank', 'width=760,height=900,toolbar=0,scrollbars=1,resizable=1');
  var hoy = new Date().toLocaleString('es-CO');
  var itemsHtml = (payload.items_recepcion || []).map(function(it) {
    var cls = it.estado === 'OK' ? 'color:#16a34a' : 'color:#dc2626';
    return '<tr><td>' + it.codigo_mp + '</td><td>' + it.cantidad_recibida.toLocaleString() + '</td><td style="' + cls + ';font-weight:600;">' + it.estado + '</td><td>' + (it.notas||'—') + '</td></tr>';
  }).join('');
  var discBanner = payload.tiene_discrepancias
    ? '<div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:6px;padding:12px;margin-bottom:16px;color:#92400e;font-weight:600;">⚠ Esta recepcion contiene discrepancias. Requiere revision.</div>'
    : '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;padding:12px;margin-bottom:16px;color:#166534;font-weight:600;">✓ Recepcion conforme sin discrepancias.</div>';
  w.document.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Acta Recepcion</title>'
    + '<style>body{font-family:Arial,sans-serif;padding:30px;font-size:13px;color:#1C1917;}'
    + 'h2{color:#292524;margin-bottom:4px;}h3{color:#57534e;margin:20px 0 10px;}'
    + '.header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px;}'
    + 'table{width:100%;border-collapse:collapse;margin-bottom:16px;}'
    + 'th{background:#f5f5f4;padding:8px 10px;text-align:left;font-size:11px;color:#57534e;border:1px solid #e7e5e4;}'
    + 'td{padding:7px 10px;border:1px solid #e7e5e4;}'
    + '.meta{background:#fafaf9;border-radius:6px;padding:14px;margin-bottom:16px;display:grid;grid-template-columns:1fr 1fr;gap:8px;}'
    + '.meta .lbl{font-size:10px;color:#78716c;text-transform:uppercase;} .meta .val{font-size:13px;font-weight:600;}'
    + '.firma{display:grid;grid-template-columns:1fr 1fr;gap:40px;margin-top:40px;}'
    + '.firma-box{border-top:1px solid #292524;padding-top:8px;font-size:11px;color:#78716c;text-align:center;}'
    + '.noPrint{text-align:center;margin-bottom:20px;} @media print{.noPrint{display:none!important;}}'
    + '</style></head><body>'
    + '<div class="noPrint"><button onclick="window.print()" style="padding:9px 24px;background:#292524;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;">Imprimir</button></div>'
    + '<div class="header"><div><h2>ACTA DE RECEPCION DE MERCANCIA</h2><p style="color:#78716c;font-size:12px;">Espagiria Laboratorio — COC-PRO-002-F07</p></div>'
    + '<div style="text-align:right;font-size:11px;color:#78716c;"><div>Fecha: ' + hoy + '</div></div></div>'
    + discBanner
    + '<div class="meta">'
    + '<div><div class="lbl">No. OC</div><div class="val">' + (oc ? oc.numero_oc : '—') + '</div></div>'
    + '<div><div class="lbl">Proveedor</div><div class="val">' + (oc ? oc.proveedor : '—') + '</div></div>'
    + '<div><div class="lbl">Categoria</div><div class="val">' + (oc ? (oc.categoria||'MP') : '—') + '</div></div>'
    + '<div><div class="lbl">Valor Total OC</div><div class="val">$' + Number((oc ? oc.valor_total : 0)||0).toLocaleString() + '</div></div>'
    + '</div>'
    + '<h3>Detalle de items recibidos</h3>'
    + '<table><thead><tr><th>Codigo MP</th><th>Cant. Recibida</th><th>Estado</th><th>Notas</th></tr></thead><tbody>' + itemsHtml + '</tbody></table>'
    + '<h3>Observaciones</h3>'
    + '<div style="background:#fafaf9;border:1px solid #e7e5e4;border-radius:6px;padding:12px;min-height:60px;">' + (payload.observaciones_recepcion||'Sin observaciones adicionales.') + '</div>'
    + '<div class="firma">'
    + '<div class="firma-box">Recibido por<br><br><strong>' + payload.receptor_nombre + '</strong></div>'
    + '<div class="firma-box">Control de Calidad<br><br>&nbsp;</div>'
    + '</div>'
    + '</body></html>');
  w.document.close();
}

function showMsg(id, text, type) {
  var el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = 'msg' + (type==='ok' ? ' msg-ok' : type==='err' ? ' msg-err' : '');
  el.style.display = text ? 'block' : 'none';
}

function showTab(name) {
  ['transito','parcial','recibidas','disc'].forEach(function(t) {
    document.getElementById('tab-' + t).classList.toggle('active', t === name);
    document.getElementById('tab-btn-' + t).classList.toggle('active', t === name);
  });
}

function fmtDate(s) { return s ? String(s).slice(0,10) : '—'; }
function fmtVal(v) { return '$' + Number(v||0).toLocaleString(); }

function buildTable(rows) {
  if (!rows.length) return '<div class="empty">Sin registros</div>';
  var h = '<div style="overflow-x:auto"><table><thead><tr>'
    + '<th>OC</th><th>Proveedor</th><th>Cat.</th><th>Valor</th>'
    + '<th>Fecha OC</th><th>F. Aut.</th><th>F. Pago</th><th>F. Recepcion</th><th>Observaciones</th>'
    + '</tr></thead><tbody>';
  rows.forEach(function(row) {
    var disc = row.tiene_discrepancias ? '<span class="disc"> &#9888; DISC</span>' : '';
    h += '<tr><td><strong>' + row.numero_oc + '</strong>' + disc + '</td>'
      + '<td>' + row.proveedor + '</td><td>' + row.categoria + '</td>'
      + '<td class="valor">' + fmtVal(row.valor_total) + '</td>'
      + '<td>' + fmtDate(row.fecha) + '</td>'
      + '<td>' + fmtDate(row.fecha_autorizacion) + '</td>'
      + '<td>' + fmtDate(row.fecha_pago) + '</td>'
      + '<td>' + (row.fecha_recepcion ? fmtDate(row.fecha_recepcion) : '<span style="color:#d97706">Pendiente</span>') + '</td>'
      + '<td style="max-width:200px;color:#57534e">' + (row.observaciones||'—') + '</td>'
      + '</tr>';
  });
  h += '</tbody></table></div>';
  return h;
}

async function loadMonitoreo() {
  try {
    var r = await fetch('/api/recepcion/seguimiento');
    var all = await r.json();
    if (!Array.isArray(all)) all = [];
    var transito = all.filter(function(x) { return x.estado === 'Autorizada' && (!x.fecha_recepcion || x.fecha_recepcion.length < 3); });
    var parcial = all.filter(function(x) { return x.estado === 'Parcial'; });
    var recibidas = all.filter(function(x) { return (x.estado === 'Recibida' || x.estado === 'Pagada') && x.fecha_recepcion && x.fecha_recepcion.length > 2; });
    var disc = all.filter(function(x) { return x.tiene_discrepancias; });
    document.getElementById('cnt-transito').textContent = transito.length;
    document.getElementById('cnt-parcial').textContent = parcial.length;
    document.getElementById('cnt-recibidas').textContent = recibidas.length;
    document.getElementById('cnt-disc').textContent = disc.length;
    document.getElementById('tab-transito').innerHTML = buildTable(transito);
    document.getElementById('tab-parcial').innerHTML = buildTable(parcial);
    document.getElementById('tab-recibidas').innerHTML = buildTable(recibidas);
    document.getElementById('tab-disc').innerHTML = buildTable(disc);
  } catch(e) { console.error(e); }
}

async function loadCuarentena() {
  try {
    var r = await fetch('/api/recepcion/lotes-cuarentena');
    var lotes = await r.json();
    var el = document.getElementById('cuarentena-list');
    if (!lotes.length) { el.innerHTML = '<p style="color:#16a34a;font-size:13px;">\u2713 Sin lotes en cuarentena.</p>'; return; }
    var h = '<div style="overflow-x:auto"><table><thead><tr><th>Material</th><th>Lote</th><th>Cantidad</th><th>Proveedor</th><th>F. Recepcion</th><th>Vence</th><th>OC</th><th>Accion</th></tr></thead><tbody>';
    lotes.forEach(function(l) {
      var fv = l.fecha_vencimiento ? l.fecha_vencimiento.slice(0,10) : '—';
      h += '<tr><td><strong>' + (l.material_nombre||'') + '</strong></td>'
        + '<td style="font-family:monospace;">' + (l.lote||'—') + '</td>'
        + '<td>' + Number(l.cantidad||0).toLocaleString() + '</td>'
        + '<td>' + (l.proveedor||'—') + '</td>'
        + '<td>' + (l.fecha||'—').slice(0,10) + '</td>'
        + '<td>' + fv + '</td>'
        + '<td>' + (l.numero_oc||'—') + '</td>'
        + '<td style="white-space:nowrap;">'
        + '<button class="btn" style="background:#16a34a;color:#fff;padding:4px 10px;font-size:11px;margin-right:4px;" data-aprobarlote="' + l.id + '" data-est="Aprobado">Aprobar</button>'
        + '<button class="btn" style="background:#dc2626;color:#fff;padding:4px 10px;font-size:11px;" data-aprobarlote="' + l.id + '" data-est="Rechazado">Rechazar</button>'
        + '</td></tr>';
    });
    h += '</tbody></table></div>';
    el.innerHTML = h;
  } catch(e) { document.getElementById('cuarentena-list').innerHTML = '<p style="color:#a8a29e;">Error al cargar.</p>'; }
}

document.addEventListener('click', function(e) {
  var btn = e.target.closest('[data-aprobarlote]');
  if (!btn) return;
  var movId = btn.getAttribute('data-aprobarlote');
  var est = btn.getAttribute('data-est');
  if (!confirm('Marcar lote como ' + est + '?')) return;
  fetch('/api/recepcion/aprobar-lote', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({mov_id: movId, estado: est})
  }).then(function(r){ return r.json(); }).then(function(d){
    if (d.ok) loadCuarentena();
    else alert('Error: ' + (d.error||'desconocido'));
  });
});

async function buscarLote() {
  var lote = document.getElementById('lote-input').value.trim();
  if (!lote) return;
  var el = document.getElementById('lote-result');
  el.innerHTML = '<p style="color:#a8a29e;font-size:13px;">Buscando...</p>';
  try {
    var r = await fetch('/api/recepcion/trazabilidad/' + encodeURIComponent(lote));
    var d = await r.json();
    var movs = d.movimientos || [];
    if (!movs.length) { el.innerHTML = '<p style="color:#dc2626;font-size:13px;">Lote no encontrado.</p>'; return; }
    var oc = d.oc;
    var h = '';
    if (oc) {
      h += '<div style="background:#fafaf9;border:1px solid #e7e5e4;border-radius:8px;padding:12px;margin-bottom:12px;">'
        + '<div style="font-weight:700;margin-bottom:6px;">OC de Origen: ' + oc.numero_oc + '</div>'
        + '<div style="font-size:12px;color:#57534e;">Proveedor: ' + (oc.proveedor||'—') + ' | Fecha: ' + (oc.fecha||'—').slice(0,10) + ' | Estado OC: ' + (oc.estado||'—') + ' | Recibido por: ' + (oc.recibido_por||'—') + '</div>'
        + '</div>';
    }
    h += '<table><thead><tr><th>Material</th><th>Cant.</th><th>Tipo</th><th>Fecha</th><th>Estado Lote</th><th>Proveedor</th><th>Vence</th></tr></thead><tbody>';
    movs.forEach(function(m) {
      var estadoColor = m.estado_lote === 'Aprobado' ? '#16a34a' : m.estado_lote === 'Rechazado' ? '#dc2626' : '#d97706';
      h += '<tr><td><strong>' + (m.material_nombre||m.material_id||'') + '</strong></td>'
        + '<td>' + Number(m.cantidad||0).toLocaleString() + '</td>'
        + '<td>' + (m.cantidad > 0 ? 'Entrada' : 'Salida') + '</td>'
        + '<td>' + (m.fecha||'—').slice(0,10) + '</td>'
        + '<td style="color:' + estadoColor + ';font-weight:600;">' + (m.estado_lote||'Sin estado') + '</td>'
        + '<td>' + (m.proveedor||'—') + '</td>'
        + '<td>' + (m.fecha_vencimiento||'—').slice(0,10) + '</td>'
        + '</tr>';
    });
    h += '</tbody></table>';
    el.innerHTML = h;
  } catch(e) { el.innerHTML = '<p style="color:#dc2626;">Error: ' + e.message + '</p>'; }
}

loadQueue();
loadMonitoreo();
loadCuarentena();
</script>
</body>
</html>
"""

SALIDA_HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Hub de Salida - ANIMUS Lab</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#f8f7f5;color:#1C1917;font-size:14px;}
.topbar{background:#1C1917;color:#fff;padding:12px 20px;display:flex;align-items:center;gap:16px;}
.topbar h1{font-size:18px;font-weight:600;}
.topbar a{color:#a8a29e;text-decoration:none;font-size:13px;}
.topbar a:hover{color:#fff;}
.topbar .rec-link{background:#292524;color:#fff;padding:6px 14px;border-radius:6px;font-size:12px;font-weight:600;}
.container{max-width:1100px;margin:0 auto;padding:20px;}
.card{background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:20px;margin-bottom:20px;}
.card h2{font-size:16px;font-weight:600;margin-bottom:14px;color:#292524;}
.ped-queue{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px;margin-bottom:8px;}
.ped-card{background:#fafaf9;border:1px solid #e7e5e4;border-radius:8px;padding:12px;cursor:pointer;transition:all .15s;border-left:3px solid #4A6741;}
.ped-card:hover{border-color:#292524;background:#f5f5f4;}
.ped-card.selected{border-left-color:#1e40af;background:#eff6ff;}
.ped-card .pn{font-weight:700;font-size:13px;}
.ped-card .pc{font-size:12px;color:#78716c;margin-top:2px;}
.ped-card .pv{font-size:12px;color:#4A6741;font-weight:600;margin-top:4px;}
.ped-card .pe{display:inline-block;padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700;background:#fef3c7;color:#92400e;margin-top:4px;}
.ped-card .pe.prep{background:#dbeafe;color:#1e40af;}
.btn{padding:9px 18px;border:none;border-radius:6px;font-size:14px;cursor:pointer;font-weight:500;}
.btn-primary{background:#292524;color:#fff;}
.btn-primary:hover{background:#1c1917;}
.btn-success{background:#4A6741;color:#fff;}
.btn-success:hover{background:#3a5331;}
.btn-print{background:#1e40af;color:#fff;}
.btn-print:hover{background:#1d4ed8;}
.btn-sm{padding:5px 12px;font-size:12px;}
.ped-info{background:#fafaf9;border:1px solid #e7e5e4;border-radius:8px;padding:14px;margin-bottom:16px;display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;}
.ped-info .lbl{font-size:11px;color:#78716c;text-transform:uppercase;letter-spacing:.5px;}
.ped-info .val{font-size:14px;font-weight:600;color:#292524;margin-top:2px;}
table{width:100%;border-collapse:collapse;font-size:13px;}
th{background:#f5f5f4;padding:9px 12px;text-align:left;font-weight:600;color:#57534e;border-bottom:1px solid #e7e5e4;}
td{padding:8px 12px;border-bottom:1px solid #f5f5f4;vertical-align:middle;}
tr:hover td{background:#fafaf9;}
td input[type=number]{width:100px;padding:5px 8px;border:1px solid #d6d3d1;border-radius:5px;font-size:13px;}
td input[type=text]{width:100%;padding:5px 8px;border:1px solid #d6d3d1;border-radius:5px;font-size:13px;}
.stock-ok{color:#16a34a;font-weight:600;}
.stock-low{color:#d97706;font-weight:600;}
.stock-zero{color:#dc2626;font-weight:600;}
.submit-row{margin-top:16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;}
.msg{font-size:13px;padding:8px 14px;border-radius:6px;}
.msg-ok{background:#d1fae5;color:#065f46;}
.msg-err{background:#fee2e2;color:#991b1b;}
.empty{text-align:center;padding:32px;color:#a8a29e;font-size:13px;}
.tabs{display:flex;gap:2px;margin-bottom:16px;border-bottom:2px solid #e7e5e4;}
.tab-btn{padding:9px 18px;border:none;background:none;font-size:13px;font-weight:500;color:#78716c;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;}
.tab-btn.active{color:#292524;border-bottom-color:#292524;}
.tab-btn:hover{color:#292524;}
.tab-content{display:none;}
.tab-content.active{display:block;}
.cnt-badge{display:inline-block;background:#292524;color:#fff;border-radius:20px;font-size:11px;padding:1px 7px;margin-left:4px;}
.section-title{font-size:13px;font-weight:600;color:#57534e;margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px;}
</style>
</head>
<body>
<div class="topbar">
  <a href="/" class="rec-link">&#8592; Inicio</a>
  <h1>&#128666; Hub de Salida — Despachos</h1>
</div>
<div class="container">

  <div class="card">
    <h2>&#128203; Pedidos Listos para Despachar</h2>
    <div id="ped-queue"><p style="color:#a8a29e;font-size:13px;">Cargando...</p></div>
  </div>

  <div class="card" id="despacho-form-card" style="display:none;">
    <h2>&#128230; Preparar Despacho</h2>
    <div class="ped-info" id="ped-header"></div>

    <div class="section-title">Items del Pedido</div>
    <div style="overflow-x:auto;">
      <table>
        <thead>
          <tr>
            <th>SKU</th>
            <th>Descripcion</th>
            <th>Cant. Pedida</th>
            <th>Stock Disp.</th>
            <th>Cant. a Despachar</th>
            <th>Lote PT</th>
          </tr>
        </thead>
        <tbody id="despacho-body"></tbody>
      </table>
    </div>

    <div style="margin-top:16px;">
      <label style="font-size:13px;font-weight:600;display:block;margin-bottom:6px;">Observaciones del despacho:</label>
      <textarea id="despacho-obs" style="width:100%;padding:9px 12px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;resize:vertical;min-height:60px;" placeholder="Condiciones de entrega, instrucciones especiales..."></textarea>
    </div>

    <div class="submit-row">
      <button class="btn btn-success" onclick="registrarDespacho()">&#10003; Confirmar Despacho</button>
      <button class="btn btn-print" onclick="previsualizarActa()">&#128438; Vista Previa Acta</button>
      <button class="btn btn-primary" onclick="cancelarDespacho()">Cancelar</button>
      <div id="despacho-msg"></div>
    </div>
  </div>

  <div class="card">
    <h2>&#128202; Historial de Despachos</h2>
    <div class="tabs">
      <button class="tab-btn active" id="tab-btn-recientes" onclick="showTab('recientes')">
        Recientes <span class="cnt-badge" id="cnt-recientes">0</span>
      </button>
      <button class="tab-btn" id="tab-btn-pendientes" onclick="showTab('pendientes')">
        Pedidos Pendientes <span class="cnt-badge" id="cnt-pendientes">0</span>
      </button>
    </div>
    <div id="tab-recientes" class="tab-content active"></div>
    <div id="tab-pendientes" class="tab-content"></div>
  </div>

</div>
<script>
var currentPed = null;
var stockCache = {};

async function loadPedQueue() {
  try {
    var r = await fetch('/api/hub-salida/pedidos-pendientes');
    var d = await r.json();
    var peds = d.pedidos || [];
    var el = document.getElementById('ped-queue');
    if (!peds.length) {
      el.innerHTML = '<p style="color:#a8a29e;font-size:13px;">Sin pedidos listos para despachar.</p>';
      return;
    }
    var html = '<div class="ped-queue">';
    peds.forEach(function(p) {
      var estCls = (p.estado||'').toLowerCase().includes('prep') ? 'prep' : '';
      html += '<div class="ped-card" onclick="cargarPedido(\\'\'  + p.numero + '\\\')" id="pc-' + p.numero + '">'
        + '<div class="pn">' + p.numero + '</div>'
        + '<div class="pc">' + (p.cliente||'Sin cliente') + '</div>'
        + '<div class="pv">$' + Number(p.valor_total||0).toLocaleString() + '</div>'
        + '<div><span class="pe ' + estCls + '">' + p.estado + '</span></div>'
        + '</div>';
    });
    html += '</div>';
    el.innerHTML = html;
  } catch(e) { console.error(e); }
}

async function cargarPedido(num) {
  document.querySelectorAll('.ped-card').forEach(function(c) { c.classList.remove('selected'); });
  var card = document.getElementById('pc-' + num);
  if (card) card.classList.add('selected');
  try {
    var r = await fetch('/api/hub-salida/pedido/' + encodeURIComponent(num));
    var d = await r.json();
    if (d.error) { alert(d.error); return; }
    currentPed = d;
    await renderDespachoForm(d);
    document.getElementById('despacho-form-card').style.display = 'block';
    document.getElementById('despacho-form-card').scrollIntoView({behavior:'smooth'});
  } catch(e) { alert('Error: ' + e.message); }
}

async function renderDespachoForm(d) {
  document.getElementById('ped-header').innerHTML =
    '<div><div class="lbl">Pedido</div><div class="val">' + d.numero + '</div></div>' +
    '<div><div class="lbl">Cliente</div><div class="val">' + (d.cliente||'—') + '</div></div>' +
    '<div><div class="lbl">Fecha</div><div class="val">' + (d.fecha||'').slice(0,10) + '</div></div>' +
    '<div><div class="lbl">Estado</div><div class="val">' + (d.estado||'—') + '</div></div>' +
    '<div><div class="lbl">Valor Total</div><div class="val">$' + Number(d.valor_total||0).toLocaleString() + '</div></div>';

  var tbody = document.getElementById('despacho-body');
  tbody.innerHTML = '';
  var items = d.items || [];
  for (var i = 0; i < items.length; i++) {
    var it = items[i];
    var stockData = await fetchStock(it.sku);
    var stockUds = stockData.total || 0;
    var stockCls = stockUds <= 0 ? 'stock-zero' : stockUds < it.cantidad ? 'stock-low' : 'stock-ok';
    var loteOpts = (stockData.lotes || []).map(function(l) {
      return '<option value="' + l.lote + '">' + l.lote + ' (' + l.disponible + ' uds)</option>';
    }).join('');
    if (!loteOpts) loteOpts = '<option value="">Sin lotes disponibles</option>';
    var tr = document.createElement('tr');
    tr.innerHTML =
      '<td><strong>' + it.sku + '</strong></td>' +
      '<td>' + (it.descripcion||'—') + '</td>' +
      '<td>' + it.cantidad + ' uds</td>' +
      '<td class="' + stockCls + '">' + stockUds + ' uds</td>' +
      '<td><input type="number" id="dsp-cant-' + i + '" value="' + Math.min(it.cantidad, stockUds) + '" min="0" max="' + stockUds + '" step="1" data-sku="' + it.sku + '" data-desc="' + (it.descripcion||'') + '" data-precio="' + (it.precio_unitario||0) + '"></td>' +
      '<td><select id="dsp-lote-' + i + '">' + loteOpts + '</select></td>';
    tbody.appendChild(tr);
  }
}

async function fetchStock(sku) {
  if (stockCache[sku]) return stockCache[sku];
  try {
    var r = await fetch('/api/hub-salida/stock/' + encodeURIComponent(sku));
    var d = await r.json();
    stockCache[sku] = d;
    return d;
  } catch(e) { return {total: 0, lotes: []}; }
}

function previsualizarActa() {
  if (!currentPed) return;
  var items = buildDespachoItems();
  imprimirActaEntrega(currentPed, items, null, true);
}

function buildDespachoItems() {
  var items = [];
  var rows = document.querySelectorAll('#despacho-body tr');
  rows.forEach(function(tr, i) {
    var cantEl = document.getElementById('dsp-cant-' + i);
    var loteEl = document.getElementById('dsp-lote-' + i);
    if (!cantEl) return;
    items.push({
      sku: cantEl.dataset.sku,
      descripcion: cantEl.dataset.desc,
      cantidad: parseInt(cantEl.value) || 0,
      precio_unitario: parseFloat(cantEl.dataset.precio) || 0,
      lote_pt: loteEl ? loteEl.value : ''
    });
  });
  return items;
}

async function registrarDespacho() {
  if (!currentPed) return;
  var items = buildDespachoItems();
  var obs = document.getElementById('despacho-obs').value.trim();
  if (!items.length || items.every(function(it) { return it.cantidad <= 0; })) {
    showMsg('despacho-msg', 'Ingresa al menos un item con cantidad > 0', 'err'); return;
  }
  showMsg('despacho-msg', 'Registrando despacho...', '');
  try {
    var r = await fetch('/api/hub-salida/despachar', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({numero_pedido: currentPed.numero, cliente_id: currentPed.cliente_id, items: items, observaciones: obs})
    });
    var d = await r.json();
    if (d.numero) {
      showMsg('despacho-msg', 'Despacho ' + d.numero + ' registrado correctamente.', 'ok');
      imprimirActaEntrega(currentPed, items, d.numero, false);
      setTimeout(function() {
        document.getElementById('despacho-form-card').style.display = 'none';
        currentPed = null;
        stockCache = {};
        loadPedQueue();
        loadHistorial();
      }, 1200);
    } else {
      showMsg('despacho-msg', d.error || 'Error al registrar', 'err');
    }
  } catch(e) { showMsg('despacho-msg', 'Error: ' + e.message, 'err'); }
}

function imprimirActaEntrega(ped, items, numDespacho, preview) {
  var w = window.open('', '_blank', 'width=760,height=900,toolbar=0,scrollbars=1,resizable=1');
  var hoy = new Date().toLocaleString('es-CO');
  var totalUds = items.reduce(function(a, it) { return a + it.cantidad; }, 0);
  var totalVal = items.reduce(function(a, it) { return a + it.cantidad * it.precio_unitario; }, 0);
  var itemsHtml = items.filter(function(it) { return it.cantidad > 0; }).map(function(it) {
    var sub = it.cantidad * it.precio_unitario;
    return '<tr><td>' + it.sku + '</td><td>' + (it.descripcion||'—') + '</td>'
      + '<td style="text-align:center;">' + it.cantidad + '</td>'
      + '<td>' + (it.lote_pt||'—') + '</td>'
      + '<td style="text-align:right;">$' + Number(it.precio_unitario||0).toLocaleString() + '</td>'
      + '<td style="text-align:right;font-weight:600;">$' + Number(sub||0).toLocaleString() + '</td></tr>';
  }).join('');
  var previewBanner = preview
    ? '<div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:6px;padding:10px;margin-bottom:16px;color:#92400e;font-size:12px;font-weight:600;">BORRADOR — Vista previa. El despacho aun no ha sido confirmado en el sistema.</div>'
    : '';
  w.document.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Acta de Entrega</title>'
    + '<style>body{font-family:Arial,sans-serif;padding:30px;font-size:13px;color:#1C1917;}'
    + 'h2{color:#1C1917;margin-bottom:4px;}h3{color:#57534e;margin:20px 0 10px;}'
    + '.header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px;}'
    + 'table{width:100%;border-collapse:collapse;margin-bottom:16px;}'
    + 'th{background:#f5f5f4;padding:8px 10px;text-align:left;font-size:11px;color:#57534e;border:1px solid #e7e5e4;}'
    + 'td{padding:7px 10px;border:1px solid #e7e5e4;}'
    + '.meta{background:#fafaf9;border-radius:6px;padding:14px;margin-bottom:16px;display:grid;grid-template-columns:1fr 1fr;gap:8px;}'
    + '.meta .lbl{font-size:10px;color:#78716c;text-transform:uppercase;} .meta .val{font-size:13px;font-weight:600;}'
    + '.total-row td{background:#f5f5f4;font-weight:700;}'
    + '.firma{display:grid;grid-template-columns:1fr 1fr 1fr;gap:30px;margin-top:40px;}'
    + '.firma-box{border-top:1px solid #292524;padding-top:8px;font-size:11px;color:#78716c;text-align:center;}'
    + '.noPrint{text-align:center;margin-bottom:20px;} @media print{.noPrint{display:none!important;}}'
    + '</style></head><body>'
    + '<div class="noPrint"><button onclick="window.print()" style="padding:9px 24px;background:#1C1917;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;">Imprimir</button></div>'
    + previewBanner
    + '<div class="header">'
    + '<div><h2>ACTA DE ENTREGA / REMISION</h2><p style="color:#78716c;font-size:12px;">ANIMUS Lab — HHA Group</p></div>'
    + '<div style="text-align:right;font-size:11px;color:#78716c;">'
    + '<div>No. Despacho: <strong>' + (numDespacho||'BORRADOR') + '</strong></div>'
    + '<div>Fecha: ' + hoy + '</div></div></div>'
    + '<div class="meta">'
    + '<div><div class="lbl">No. Pedido</div><div class="val">' + (ped ? ped.numero : '—') + '</div></div>'
    + '<div><div class="lbl">Cliente</div><div class="val">' + (ped ? (ped.cliente||'—') : '—') + '</div></div>'
    + '<div><div class="lbl">Total Unidades</div><div class="val">' + totalUds + ' uds</div></div>'
    + '<div><div class="lbl">Valor Total</div><div class="val">$' + Number(totalVal).toLocaleString() + '</div></div>'
    + '</div>'
    + '<h3>Detalle del despacho</h3>'
    + '<table><thead><tr><th>SKU</th><th>Descripcion</th><th style="text-align:center;">Cant.</th><th>Lote PT</th><th style="text-align:right;">P. Unit.</th><th style="text-align:right;">Subtotal</th></tr></thead>'
    + '<tbody>' + itemsHtml + '</tbody>'
    + '<tfoot><tr class="total-row"><td colspan="5" style="text-align:right;">TOTAL</td><td style="text-align:right;">$' + Number(totalVal).toLocaleString() + '</td></tr></tfoot>'
    + '</table>'
    + '<div class="firma">'
    + '<div class="firma-box">Despachado por<br><br>&nbsp;</div>'
    + '<div class="firma-box">Recibido por / Transportista<br><br>&nbsp;</div>'
    + '<div class="firma-box">Control de Calidad<br><br>&nbsp;</div>'
    + '</div>'
    + '</body></html>');
  w.document.close();
}

function cancelarDespacho() {
  currentPed = null;
  document.getElementById('despacho-form-card').style.display = 'none';
  document.querySelectorAll('.ped-card').forEach(function(c) { c.classList.remove('selected'); });
}

function showMsg(id, text, type) {
  var el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = 'msg' + (type==='ok' ? ' msg-ok' : type==='err' ? ' msg-err' : '');
  el.style.display = text ? 'block' : 'none';
}

function showTab(name) {
  ['recientes','pendientes'].forEach(function(t) {
    document.getElementById('tab-' + t).classList.toggle('active', t === name);
    document.getElementById('tab-btn-' + t).classList.toggle('active', t === name);
  });
}

async function loadHistorial() {
  try {
    var r = await fetch('/api/despachos');
    var d = await r.json();
    var desps = (d.despachos || []).slice(0, 20);
    var el = document.getElementById('tab-recientes');
    document.getElementById('cnt-recientes').textContent = desps.length;
    if (!desps.length) { el.innerHTML = '<div class="empty">Sin despachos registrados</div>'; return; }
    var h = '<div style="overflow-x:auto"><table><thead><tr><th>No. Despacho</th><th>Cliente</th><th>Pedido</th><th>Operador</th><th>Fecha</th><th>Estado</th></tr></thead><tbody>';
    desps.forEach(function(d) {
      h += '<tr><td><strong>' + d.numero + '</strong></td><td>' + (d.cliente||'—') + '</td><td>' + (d.numero_pedido||'—') + '</td><td>' + (d.operador||'—') + '</td><td>' + (d.fecha||'').slice(0,10) + '</td><td>' + (d.estado||'—') + '</td></tr>';
    });
    h += '</tbody></table></div>';
    el.innerHTML = h;

    var r2 = await fetch('/api/hub-salida/pedidos-pendientes');
    var d2 = await r2.json();
    var pend = d2.pedidos || [];
    document.getElementById('cnt-pendientes').textContent = pend.length;
    var el2 = document.getElementById('tab-pendientes');
    if (!pend.length) { el2.innerHTML = '<div class="empty">Sin pedidos pendientes</div>'; return; }
    var h2 = '<div style="overflow-x:auto"><table><thead><tr><th>Pedido</th><th>Cliente</th><th>Valor</th><th>Estado</th><th>Fecha</th><th>Accion</th></tr></thead><tbody>';
    pend.forEach(function(p) {
      h2 += '<tr><td><strong>' + p.numero + '</strong></td><td>' + (p.cliente||'—') + '</td><td>$' + Number(p.valor_total||0).toLocaleString() + '</td><td>' + p.estado + '</td><td>' + (p.fecha||'').slice(0,10) + '</td><td><button class="btn btn-primary btn-sm" onclick="cargarPedido(\\'\'  + p.numero + '\\\')" >Despachar</button></td></tr>';
    });
    h2 += '</tbody></table></div>';
    el2.innerHTML = h2;
  } catch(e) { console.error(e); }
}

loadPedQueue();
loadHistorial();
</script>
</body>
</html>
"""

from templates_py.solicitudes_html import SOLICITUDES_HTML

from templates_py.dashboard_html import DASHBOARD_HTML

@app.route('/')
def index():
    return Response(HOME_HTML, mimetype='text/html')

@app.route('/inventarios')
def inventarios():
    return Response(DASHBOARD_HTML, mimetype='text/html')

# ── Security: rate limiter ──────────────────────────────────────────────
_LOGIN_ATTEMPTS = {}
_MAX_ATTEMPTS   = 5
_LOCKOUT_SECS   = 900

def _client_ip():
    hdr = request.headers.get('X-Forwarded-For', request.remote_addr or '0.0.0.0')
    return hdr.split(',')[0].strip()

def _is_locked(ip):
    rec = _LOGIN_ATTEMPTS.get(ip)
    if not rec: return False
    if time.time() < rec['locked_until']: return True
    _LOGIN_ATTEMPTS.pop(ip, None)
    return False

def _record_failure(ip):
    rec = _LOGIN_ATTEMPTS.setdefault(ip, {'count': 0, 'locked_until': 0.0})
    rec['count'] += 1
    if rec['count'] >= _MAX_ATTEMPTS:
        rec['locked_until'] = time.time() + _LOCKOUT_SECS

def _clear_attempts(ip):
    _LOGIN_ATTEMPTS.pop(ip, None)

def _log_sec(event, username=None, ip=None, details=None):
    try:
        ua = request.headers.get("User-Agent", "")[:200]
        ts = datetime.utcnow().isoformat() + "Z"
        conn2 = sqlite3.connect(DB_PATH)
        conn2.execute(
            "INSERT INTO security_events(ts,event,username,ip,user_agent,details)"
            " VALUES(?,?,?,?,?,?)",
            (ts, event, username, ip, ua, details or "")
        )
        conn2.commit(); conn2.close()
    except Exception:
        pass

# ── Security: session timeout ───────────────────────────────────────────────
@app.before_request
def check_session_timeout():
    if session.get('compras_user'):
        if time.time() - session.get('login_time', 0) > 8 * 3600:
            session.clear()
            return redirect('/login')

# ── Security: headers ───────────────────────────────────────────────────────────
@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options']           = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options']    = 'nosniff'
    response.headers['Referrer-Policy']           = 'strict-origin-when-cross-origin'
    response.headers['X-XSS-Protection']          = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    csp = ("default-src 'self'; "
           "script-src 'self' 'unsafe-inline' cdnjs.cloudflare.com; "
           "style-src 'self' 'unsafe-inline' fonts.googleapis.com cdnjs.cloudflare.com; "
           "font-src 'self' fonts.gstatic.com cdnjs.cloudflare.com; "
           "img-src 'self' data:; connect-src 'self';")
    response.headers['Content-Security-Policy'] = csp
    return response

@app.route('/login', methods=['GET','POST'])
def login():
    error = ''
    if request.method == 'POST':
        ip = _client_ip()
        if _is_locked(ip):
            error = '<div class="err">Demasiados intentos. Espera 15 min.</div>'
            return Response(LOGIN_HTML.replace('{error}', error), mimetype='text/html')
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '').strip()
        expected = COMPRAS_USERS.get(username, '')
        # Soporte PBKDF2 (env var con hash) y plaintext legacy
        if expected and expected.startswith('pbkdf2:'):
            match = check_password_hash(expected, password)
        else:
            match = bool(expected) and hmac.compare_digest(expected, password)
        if match:
            _clear_attempts(ip)
            _log_sec("login_success", username, ip)
            session.clear()
            session.permanent = True
            session['compras_user'] = username
            session['login_time']   = time.time()
            nxt = request.args.get('next', '/compras')
            if not nxt.startswith('/') or nxt.startswith('//'):
                nxt = '/compras'
            return redirect(nxt)
        _record_failure(ip)
        _log_sec("login_failure", username, ip)
        error = '<div class="err">Usuario o contraseña incorrectos.</div>'
    return Response(LOGIN_HTML.replace('{error}', error), mimetype='text/html')

@app.route('/logout')
def logout():
    session.pop('compras_user', None)
    return redirect('/')

@app.route('/compras')
def compras():
    if 'compras_user' not in session:
        return redirect('/login')
    usuario = session.get('compras_user', '').capitalize()
    es_contadora = 'true' if session.get('compras_user','') in CONTADORA_USERS else 'false'
    html = COMPRAS_HTML.replace('{usuario}', usuario).replace('{es_contadora}', es_contadora)
    return Response(html, mimetype='text/html')


@app.route('/api/hub/resumen')
def hub_resumen():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # OCs
    c.execute("SELECT estado, COUNT(*), COALESCE(SUM(valor_total),0) FROM ordenes_compra GROUP BY estado")
    oc_data = {r[0]:{'count':r[1],'valor':r[2]} for r in c.fetchall()}
    hoy = datetime.now().strftime('%Y-%m-%d')
    semana_ini = (datetime.now() - __import__('datetime').timedelta(days=7)).strftime('%Y-%m-%d')
    # Pagado esta semana
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM ordenes_compra WHERE estado='Pagada' AND fecha_pago >= ?", (semana_ini,))
    pag_semana = c.fetchone()[0] or 0
    # Por pagar (Autorizada)
    val_por_pagar = oc_data.get('Autorizada',{}).get('valor',0)
    cnt_por_pagar = oc_data.get('Autorizada',{}).get('count',0)
    val_por_autorizar = oc_data.get('Revisada',{}).get('valor',0)
    cnt_por_autorizar = oc_data.get('Revisada',{}).get('count',0)
    # Stock crítico
    c.execute("""SELECT COUNT(*) FROM (
        SELECT m.material_id, COALESCE(SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad WHEN m.tipo='Salida' THEN -m.cantidad ELSE 0 END),0) as stock,
               mp.stock_minimo FROM movimientos m
        LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
        GROUP BY m.material_id HAVING stock < COALESCE(mp.stock_minimo,0) AND COALESCE(mp.stock_minimo,0)>0
    )""")
    stock_crit = c.fetchone()[0] or 0
    # Compromisos
    c.execute("SELECT estado, prioridad, COUNT(*) FROM compromisos GROUP BY estado, prioridad")
    comp_rows = c.fetchall()
    comp_vencidos = 0
    c.execute("SELECT COUNT(*) FROM compromisos WHERE estado NOT IN ('Completado','Cancelado') AND fecha_limite != '' AND fecha_limite < ?", (hoy,))
    comp_vencidos = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM compromisos WHERE estado NOT IN ('Completado','Cancelado')")
    comp_pendientes = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM compromisos WHERE prioridad='Critico' AND estado NOT IN ('Completado','Cancelado')")
    comp_criticos = c.fetchone()[0] or 0
    # Clientes activos
    c.execute("SELECT COUNT(*) FROM clientes WHERE activo=1")
    clientes_activos = c.fetchone()[0] or 0
    conn.close()
    return jsonify({
        'ocs': {'por_autorizar': cnt_por_autorizar, 'por_pagar': cnt_por_pagar,
                'valor_autorizar': val_por_autorizar, 'valor_pagar': val_por_pagar},
        'stock_critico': stock_crit,
        'pagado_semana': pag_semana,
        'compromisos': {'pendientes': comp_pendientes, 'vencidos': comp_vencidos, 'criticos': comp_criticos},
        'clientes': clientes_activos
    })

@app.route('/api/hub/alertas')
def hub_alertas():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    hoy = datetime.now().strftime('%Y-%m-%d')
    alertas = []
    # OCs Revisadas sin autorizar (> 2 dias)
    hace2 = (datetime.now() - __import__('datetime').timedelta(days=2)).isoformat()
    c.execute("SELECT numero_oc, proveedor, valor_total, fecha FROM ordenes_compra WHERE estado='Revisada' ORDER BY fecha ASC LIMIT 10")
    for row in c.fetchall():
        num, prov, val, fecha = row
        dias = max(0, (datetime.now() - datetime.fromisoformat(fecha[:19])).days) if fecha else 0
        nivel = 'critico' if dias >= 3 else 'atencion'
        alertas.append({'nivel':nivel,'tipo':'oc_autorizar','titulo':'OC pendiente de autorizar',
            'detalle':f'{num} — {prov or "?"} ${val:,.0f} — {dias}d sin autorizar',
            'accion':'/compras','oc_num':num,'valor':val})
    # OCs Autorizadas con fecha vencida
    c.execute("SELECT numero_oc, proveedor, valor_total, fecha_entrega_est FROM ordenes_compra WHERE estado='Autorizada' AND fecha_entrega_est != '' AND fecha_entrega_est < ? ORDER BY fecha_entrega_est ASC", (hoy,))
    for row in c.fetchall():
        num, prov, val, fecha = row
        alertas.append({'nivel':'critico','tipo':'pago_vencido','titulo':'Pago vencido',
            'detalle':f'{num} — {prov or "?"} ${val:,.0f} — vencio {fecha}',
            'accion':'/compras','oc_num':num,'valor':val})
    # OCs Autorizadas proximas a vencer (3 dias)
    en3 = (datetime.now() + __import__('datetime').timedelta(days=3)).strftime('%Y-%m-%d')
    c.execute("SELECT numero_oc, proveedor, valor_total, fecha_entrega_est FROM ordenes_compra WHERE estado='Autorizada' AND fecha_entrega_est BETWEEN ? AND ? ORDER BY fecha_entrega_est ASC", (hoy, en3))
    for row in c.fetchall():
        num, prov, val, fecha = row
        alertas.append({'nivel':'atencion','tipo':'pago_proximo','titulo':'Pago proximo',
            'detalle':f'{num} — {prov or "?"} ${val:,.0f} — vence {fecha}',
            'accion':'/compras','oc_num':num,'valor':val})
    # Compromisos vencidos
    c.execute("SELECT descripcion, responsable, fecha_limite, prioridad FROM compromisos WHERE estado NOT IN ('Completado','Cancelado') AND fecha_limite != '' AND fecha_limite < ? ORDER BY prioridad DESC, fecha_limite ASC LIMIT 5", (hoy,))
    for row in c.fetchall():
        desc, resp, fecha, prior = row
        nivel = 'critico' if prior == 'Critico' else 'atencion'
        alertas.append({'nivel':nivel,'tipo':'compromiso_vencido','titulo':'Compromiso vencido',
            'detalle':f'{desc[:60]} — {resp} — vencio {fecha}',
            'accion':'/compromisos'})
    # Lotes proximos a vencer o ya vencidos
    hoy_dt = datetime.now()
    en60 = (hoy_dt + timedelta(days=60)).strftime('%Y-%m-%d')
    hoy_str = hoy_dt.strftime('%Y-%m-%d')
    try:
        c.execute("""SELECT material_nombre, lote, fecha_vencimiento, material_id
                     FROM movimientos
                     WHERE tipo='Entrada' AND fecha_vencimiento IS NOT NULL AND fecha_vencimiento != ''
                     AND fecha_vencimiento <= ?
                     GROUP BY material_id, lote
                     ORDER BY fecha_vencimiento ASC LIMIT 8""", (en60,))
        for row in c.fetchall():
            nombre, lote, fv, mid = row
            try:
                fv_clean = (fv or '')[:10]
                fv_dt = datetime.strptime(fv_clean, '%Y-%m-%d')
                dias = (fv_dt - hoy_dt).days
            except Exception:
                continue
            nivel = 'critico' if dias <= 15 else 'atencion'
            if dias < 0:
                msg = f'VENCIDO hace {abs(dias)} dias'
            elif dias == 0:
                msg = 'VENCE HOY'
            else:
                msg = f'Vence en {dias} dias ({fv_clean})'
            alertas.append({'nivel': nivel, 'tipo': 'lote_vencimiento',
                'titulo': 'Lote proximo a vencer',
                'detalle': f'{nombre} — Lote {lote or "sin lote"} — {msg}',
                'accion': '/inventarios'})
    except Exception:
        pass
    # Sort: critico first
    orden = {'critico':0,'atencion':1,'info':2}
    alertas.sort(key=lambda x: orden.get(x['nivel'],2))
    resumen = {'critico': sum(1 for a in alertas if a['nivel']=='critico'),
               'atencion': sum(1 for a in alertas if a['nivel']=='atencion'),
               'info': sum(1 for a in alertas if a['nivel']=='info')}
    conn.close()
    return jsonify({'alertas': alertas[:15], 'resumen': resumen})

@app.route('/api/compromisos', methods=['GET','POST'])
def handle_compromisos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('descripcion'): conn.close(); return jsonify({'error':'Descripcion requerida'}),400
        c.execute("""INSERT INTO compromisos (descripcion,responsable,area,fecha_limite,estado,prioridad,origen,empresa,fecha_creacion)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (d['descripcion'],d.get('responsable',''),d.get('area',''),d.get('fecha_limite',''),
                   d.get('estado','Pendiente'),d.get('prioridad','Normal'),d.get('origen',''),
                   d.get('empresa','Espagiria'),datetime.now().strftime('%Y-%m-%d')))
        conn.commit(); conn.close()
        return jsonify({'ok':True,'id':c.lastrowid}), 201
    estado_f = request.args.get('estado','')
    empresa_f = request.args.get('empresa','')
    sql = "SELECT id,descripcion,responsable,area,fecha_limite,estado,prioridad,origen,empresa,fecha_creacion,notas FROM compromisos"
    clauses=[]; params=[]
    if estado_f and estado_f != 'Todos': clauses.append("estado=?"); params.append(estado_f)
    if empresa_f: clauses.append("empresa=?"); params.append(empresa_f)
    if clauses: sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY CASE prioridad WHEN 'Critico' THEN 0 WHEN 'Alta' THEN 1 WHEN 'Normal' THEN 2 ELSE 3 END, fecha_limite ASC"
    c.execute(sql, params)
    cols = ['id','descripcion','responsable','area','fecha_limite','estado','prioridad','origen','empresa','fecha_creacion','notas']
    rows = [dict(zip(cols,r)) for r in c.fetchall()]
    conn.close()
    return jsonify({'compromisos': rows})

@app.route('/api/compromisos/<int:cid>', methods=['PATCH'])
def update_compromiso(cid):
    d = request.json or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    sets=[]; params=[]
    for field in ['estado','notas','fecha_limite','responsable','prioridad']:
        if field in d: sets.append(f"{field}=?"); params.append(d[field])
    if d.get('estado') == 'Completado':
        sets.append("fecha_cierre=?"); params.append(datetime.now().strftime('%Y-%m-%d'))
    if not sets: conn.close(); return jsonify({'error':'Nada que actualizar'}),400
    params.append(cid)
    c.execute(f"UPDATE compromisos SET {', '.join(sets)} WHERE id=?", params)
    conn.commit(); conn.close()
    return jsonify({'ok':True})

@app.route('/compromisos')
def compromisos_page():
    if 'compras_user' not in session:
        return redirect('/login')
    return Response(COMPROMISOS_HTML, mimetype='text/html')

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Inventory system running'})

@app.route('/api/inventario')
def get_inventario():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM movimientos')
    mov = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM producciones')
    prod = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM alertas')
    alrt = c.fetchone()[0]
    c.execute('SELECT COALESCE(SUM(CASE WHEN tipo="Entrada" THEN cantidad ELSE -cantidad END),0) FROM movimientos')
    stock = c.fetchone()[0]
    conn.close()
    return jsonify({'total_items': mov, 'movimientos': mov, 'producciones': prod,
                    'alertas': alrt, 'stock_total': round(stock, 2)})

@app.route('/api/formulas', methods=['GET', 'POST'])
def handle_formulas():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        prod = data['producto_nombre']
        c.execute('INSERT OR REPLACE INTO formula_headers (producto_nombre, unidad_base_g, descripcion, fecha_creacion) VALUES (?,?,?,?)',
                  (prod, data.get('unidad_base_g', 1000), data.get('descripcion', ''), datetime.now().isoformat()))
        c.execute('DELETE FROM formula_items WHERE producto_nombre=?', (prod,))
        for item in data.get('items', []):
            c.execute('INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) VALUES (?,?,?,?)',
                      (prod, item['material_id'], item['material_nombre'], item['porcentaje']))
        conn.commit()
        conn.close()
        return jsonify({'message': f'Formula de {prod} guardada exitosamente'}), 201
    c.execute('SELECT producto_nombre, unidad_base_g, descripcion, fecha_creacion FROM formula_headers ORDER BY producto_nombre')
    headers = c.fetchall()
    formulas = []
    for h in headers:
        c.execute('SELECT material_id, material_nombre, porcentaje FROM formula_items WHERE producto_nombre=?', (h[0],))
        items = [{'material_id': r[0], 'material_nombre': r[1], 'porcentaje': r[2]} for r in c.fetchall()]
        formulas.append({'producto_nombre': h[0], 'unidad_base_g': h[1], 'descripcion': h[2],
                         'fecha_creacion': h[3], 'items': items})
    conn.close()
    return jsonify({'formulas': formulas})

@app.route('/api/formulas/<producto_nombre>', methods=['DELETE'])
def del_formula(producto_nombre):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM formula_items WHERE producto_nombre=?', (producto_nombre,))
    c.execute('DELETE FROM formula_headers WHERE producto_nombre=?', (producto_nombre,))
    conn.commit()
    conn.close()
    return jsonify({'message': f'Formula {producto_nombre} eliminada'})

@app.route('/api/movimientos', methods=['GET', 'POST'])
def handle_movimientos():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        c.execute("""INSERT INTO movimientos
                     (material_id, material_nombre, cantidad, tipo, fecha, observaciones,
                      lote, fecha_vencimiento, estanteria, posicion, proveedor, estado_lote, operador)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (data['material_id'], data['material_nombre'], data['cantidad'],
                   data['tipo'], datetime.now().isoformat(), data.get('observaciones',''),
                   data.get('lote',''), data.get('fecha_vencimiento',''),
                   data.get('estanteria',''), data.get('posicion',''),
                   data.get('proveedor',''), data.get('estado_lote','VIGENTE'),
                   data.get('operador','')))
        conn.commit(); conn.close()
        return jsonify({'message': 'Movimiento registrado exitosamente'}), 201
    c.execute('SELECT material_id, material_nombre, cantidad, tipo, fecha, observaciones, operador, lote FROM movimientos ORDER BY fecha DESC LIMIT 500')
    movimientos = [{'material_id': r[0] or '', 'material_nombre': r[1], 'cantidad': r[2], 'tipo': r[3], 'fecha': r[4], 'observaciones': r[5], 'operador': r[6] or '', 'lote': r[7] or ''} for r in c.fetchall()]
    conn.close()
    return jsonify({'movimientos': movimientos})

@app.route('/api/produccion', methods=['GET', 'POST'])
def handle_produccion():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        producto = data.get('producto', data.get('producto',''))
        presentacion = data.get('presentacion','')
        cantidad_kg = float(data.get('cantidad_kg', data.get('cantidad', 0)))
        cantidad_g = cantidad_kg * 1000
        fecha = datetime.now().isoformat()
        c.execute('INSERT INTO producciones (producto, cantidad, fecha, estado, observaciones, operador, presentacion) VALUES (?,?,?,?,?,?,?)',
                  (producto, cantidad_kg, fecha, 'Completado', data.get('observaciones', ''), data.get('operador', ''), presentacion))
        prod_id = c.lastrowid
        lote_ref = f'PROD-{prod_id:05d}'
        # Guardar lote_ref en producciones para trazabilidad
        try: c.execute("UPDATE producciones SET lote=? WHERE id=?", (lote_ref, prod_id))
        except: pass
        c.execute('SELECT material_id, material_nombre, porcentaje FROM formula_items WHERE producto_nombre=?', (producto,))
        formula_items = c.fetchall()
        descuentos = []
        for mat_id, mat_nombre, pct in formula_items:
            g_total = round((pct / 100) * cantidad_g, 2)
            if g_total <= 0: continue
            # FEFO: seleccionar lotes por fecha de vencimiento mas proxima con stock disponible
            c.execute("""SELECT lote, fecha_vencimiento,
                                SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock
                         FROM movimientos
                         WHERE material_id=? AND lote IS NOT NULL AND lote!='' AND lote!='S/L'
                           AND (estado_lote IS NULL OR estado_lote NOT IN ('CUARENTENA','CUARENTENA_EXTENDIDA','RECHAZADO'))
                         GROUP BY lote HAVING stock > 0
                         ORDER BY CASE WHEN fecha_vencimiento IS NULL OR fecha_vencimiento=''
                                  THEN '9999' ELSE fecha_vencimiento END ASC""", (mat_id,))
            lotes_fefo = c.fetchall()
            g_restante = g_total; lotes_usados = []
            for lrow in lotes_fefo:
                if g_restante <= 0: break
                lote_n, lote_v, lote_s = lrow
                g_lote = round(min(g_restante, lote_s), 2)
                c.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, observaciones, lote, operador) VALUES (?,?,?,?,?,?,?,?)",
                          (mat_id, mat_nombre, g_lote, 'Salida', fecha,
                           f'FEFO:{lote_ref}:{producto} x {cantidad_kg}kg', lote_n, data.get('operador','')))
                lotes_usados.append({'lote': lote_n, 'vence': str(lote_v)[:10] if lote_v else '', 'cantidad_g': g_lote})
                g_restante = round(g_restante - g_lote, 2)
            if g_restante > 0:
                c.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, observaciones, operador) VALUES (?,?,?,?,?,?,?)",
                          (mat_id, mat_nombre, g_restante, 'Salida', fecha, f'Produccion: {producto} x {cantidad_kg}kg', data.get('operador','')))
                lotes_usados.append({'lote': 'sin_lote', 'vence': '', 'cantidad_g': g_restante})
            descuentos.append({'material': mat_nombre, 'material_id': mat_id,
                                'cantidad_g': g_total, 'lotes_fefo': lotes_usados})
        # Auto-crear entrada en stock_pt si viene sku + unidades
        sku_pt = data.get('sku_pt', '').strip()
        unidades_pt = int(data.get('unidades_pt', 0) or 0)
        precio_pt = float(data.get('precio_pt', 0) or 0)
        if sku_pt and unidades_pt > 0:
            c.execute("""INSERT INTO stock_pt
                         (sku, descripcion, lote_produccion, fecha_produccion,
                          unidades_inicial, unidades_disponible, precio_base, empresa, estado, observaciones)
                         VALUES (?,?,?,?,?,?,?,?,?,?)""",
                      (sku_pt, producto, lote_ref, fecha,
                       unidades_pt, unidades_pt, precio_pt,
                       'ANIMUS', 'Disponible',
                       f'Produccion {lote_ref} — {cantidad_kg}kg'))
        conn.commit()
        conn.close()
        msg = f'Produccion registrada: {producto} x {cantidad_kg}kg (FEFO)'
        if descuentos:
            msg += f'. {len(descuentos)} MPs descontadas por FEFO.'
        if sku_pt and unidades_pt > 0:
            msg += f'. {unidades_pt} uds de {sku_pt} en stock PT.'
        return jsonify({'message': msg, 'descuentos': descuentos, 'lote': lote_ref,
                        'stock_pt_creado': bool(sku_pt and unidades_pt > 0)}), 201
    c.execute('SELECT producto, cantidad, fecha, estado, operador, COALESCE(presentacion,"") FROM producciones ORDER BY fecha DESC LIMIT 50')
    prod = [{'producto': r[0], 'cantidad': r[1], 'fecha': r[2], 'estado': r[3], 'operador': r[4] or '', 'presentacion': r[5] or ''} for r in c.fetchall()]
    conn.close()
    return jsonify({'producciones': prod})


@app.route('/api/produccion/simular', methods=['POST'])
def simular_produccion():
    """Pre-check de stock FEFO + estimado de costo sin commitear ningun movimiento."""
    data = request.json
    producto = data.get('producto', '')
    cantidad_kg = float(data.get('cantidad_kg', 1))
    cantidad_g = cantidad_kg * 1000
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT fi.material_id, fi.material_nombre, fi.porcentaje,
                        COALESCE(m.precio_referencia, 0)
                 FROM formula_items fi
                 LEFT JOIN maestro_mps m ON fi.material_id = m.codigo_mp
                 WHERE fi.producto_nombre=?""", (producto,))
    items = c.fetchall()
    if not items:
        conn.close()
        return jsonify({'error': f'Formula no encontrada: {producto}', 'factible': False}), 404
    resultado = []
    factible = True
    costo_total = 0.0
    sin_precio = 0
    for mat_id, mat_nombre, pct, precio_kg in items:
        g_req = round((pct / 100) * cantidad_g, 2)
        c.execute("""SELECT COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END),0)
                     FROM movimientos WHERE material_id=?
                     AND (estado_lote IS NULL OR estado_lote NOT IN ('CUARENTENA','CUARENTENA_EXTENDIDA','RECHAZADO'))""",
                  (mat_id,))
        g_disp = round(c.fetchone()[0] or 0, 2)
        suf = g_disp >= g_req
        if not suf:
            factible = False
        precio_g = (precio_kg or 0) / 1000.0
        costo_item = round(g_req * precio_g, 2)
        costo_total += costo_item
        if not precio_kg or precio_kg == 0:
            sin_precio += 1
        resultado.append({
            'material_id': mat_id, 'material_nombre': mat_nombre,
            'porcentaje': pct, 'g_requerido': g_req,
            'g_disponible': g_disp,
            'g_faltante': max(0, round(g_req - g_disp, 2)),
            'suficiente': suf,
            'precio_kg': round(precio_kg or 0, 2),
            'costo': costo_item
        })
    conn.close()
    faltantes = sum(1 for r in resultado if not r['suficiente'])
    n = len(resultado)
    return jsonify({
        'producto': producto, 'cantidad_kg': cantidad_kg,
        'factible': factible, 'faltantes': faltantes,
        'costo_total': round(costo_total, 2),
        'costo_por_kg': round(costo_total / cantidad_kg, 2) if cantidad_kg > 0 else 0,
        'ingredientes_sin_precio': sin_precio,
        'cobertura_precio_pct': round((n - sin_precio) / n * 100, 1) if n > 0 else 0,
        'ingredientes': sorted(resultado, key=lambda x: x['suficiente'])
    })


@app.route('/api/formula/costo', methods=['POST'])
def calcular_costo_formula():
    """Calcula costo estimado de un batch sin verificar stock."""
    data = request.json
    producto = data.get('producto', '')
    cantidad_kg = float(data.get('cantidad_kg', 1))
    cantidad_g = cantidad_kg * 1000
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT fi.material_id, fi.material_nombre, fi.porcentaje,
                        COALESCE(m.precio_referencia, 0)
                 FROM formula_items fi
                 LEFT JOIN maestro_mps m ON fi.material_id = m.codigo_mp
                 WHERE fi.producto_nombre=?""", (producto,))
    items = c.fetchall()
    conn.close()
    if not items:
        return jsonify({'error': f'Formula no encontrada: {producto}'}), 404
    resultado = []
    costo_total = 0.0
    sin_precio = 0
    for mat_id, mat_nombre, pct, precio_kg in items:
        g_req = round((pct / 100) * cantidad_g, 2)
        precio_g = (precio_kg or 0) / 1000.0
        costo_item = round(g_req * precio_g, 2)
        costo_total += costo_item
        if not precio_kg or precio_kg == 0:
            sin_precio += 1
        resultado.append({
            'material_id': mat_id, 'material_nombre': mat_nombre,
            'porcentaje': pct, 'g_requerido': g_req,
            'precio_kg': round(precio_kg or 0, 2),
            'precio_g': round(precio_g, 5),
            'costo': costo_item
        })
    n = len(resultado)
    return jsonify({
        'producto': producto, 'cantidad_kg': cantidad_kg,
        'costo_total': round(costo_total, 2),
        'costo_por_kg': round(costo_total / cantidad_kg, 2) if cantidad_kg > 0 else 0,
        'ingredientes_sin_precio': sin_precio,
        'cobertura_precio_pct': round((n - sin_precio) / n * 100, 1) if n > 0 else 0,
        'ingredientes': sorted(resultado, key=lambda x: x['costo'], reverse=True)
    })


@app.route('/api/trazabilidad/lote-pt/<lote_ref>')
def trazabilidad_lote_pt(lote_ref):
    """Traza hacia atrás: dado un lote PT (PROD-00001) devuelve MPs consumidas, proveedor, fecha vencimiento."""
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # Producción base
    c.execute("SELECT id, producto, cantidad, fecha, operador, observaciones FROM producciones WHERE lote=? OR id=?",
              (lote_ref, lote_ref.replace('PROD-','').lstrip('0') or 0))
    prod = c.fetchone()
    if not prod:
        conn.close()
        return jsonify({'error': f'Lote no encontrado: {lote_ref}', 'lote_ref': lote_ref}), 404
    prod_data = {'id': prod[0], 'producto': prod[1], 'cantidad_kg': prod[2],
                 'fecha': prod[3], 'operador': prod[4] or '', 'observaciones': prod[5] or ''}
    # MPs consumidas — buscar Salidas etiquetadas con este lote_ref O por fecha+producto (legacy)
    c.execute("""SELECT material_id, material_nombre, SUM(cantidad) as g_total,
                        GROUP_CONCAT(DISTINCT lote) as lotes_mp,
                        GROUP_CONCAT(DISTINCT proveedor) as proveedores
                 FROM movimientos
                 WHERE tipo='Salida'
                   AND (observaciones LIKE ? OR (fecha=? AND observaciones LIKE ?))
                 GROUP BY material_id, material_nombre
                 ORDER BY material_nombre""",
              (f'FEFO:{lote_ref}:%', prod[3], f'%{prod[1]}%'))
    mps = [{'material_id': r[0], 'material_nombre': r[1], 'g_consumido': round(r[2], 2),
             'lotes_mp': [l for l in (r[3] or '').split(',') if l and l != 'None'],
             'proveedores': list(set([p for p in (r[4] or '').split(',') if p and p != 'None']))}
           for r in c.fetchall()]
    # Para cada lote de MP consumido, obtener info del ingreso original
    detalle_lotes = []
    for mp in mps:
        for lote_mp in mp['lotes_mp']:
            c.execute("""SELECT fecha, proveedor, numero_oc, numero_factura, fecha_vencimiento, estado_lote
                         FROM movimientos WHERE lote=? AND tipo='Entrada' AND material_id=?
                         ORDER BY fecha DESC LIMIT 1""", (lote_mp, mp['material_id']))
            row = c.fetchone()
            if row:
                detalle_lotes.append({
                    'material_id': mp['material_id'], 'material_nombre': mp['material_nombre'],
                    'lote_mp': lote_mp, 'fecha_ingreso': row[0][:10] if row[0] else '',
                    'proveedor': row[1] or '', 'numero_oc': row[2] or '',
                    'numero_factura': row[3] or '', 'fecha_vencimiento': row[4] or '',
                    'estado_lote': row[5] or 'VIGENTE'
                })
    # Despachos que usaron este PT batch
    c.execute("""SELECT d.numero, cl.nombre, d.fecha,
                        di.sku, di.descripcion, di.cantidad
                 FROM despachos_items di
                 JOIN despachos d ON di.numero_despacho=d.numero
                 LEFT JOIN clientes cl ON d.cliente_id=cl.id
                 WHERE di.lote_pt=? OR di.lote_pt LIKE ?""", (lote_ref, f'%{lote_ref}%'))
    despachos = [{'numero': r[0], 'cliente': r[1] or '', 'fecha': r[2], 'sku': r[3],
                  'descripcion': r[4], 'cantidad': r[5]} for r in c.fetchall()]
    conn.close()
    return jsonify({
        'lote_ref': lote_ref, 'produccion': prod_data,
        'mps_consumidas': mps, 'detalle_lotes_mp': detalle_lotes,
        'despachos': despachos,
        'trazabilidad_completa': len(mps) > 0
    })


@app.route('/api/trazabilidad/lote-mp/<path:lote_mp>')
def trazabilidad_lote_mp(lote_mp):
    """Traza hacia adelante: dado un lote de MP devuelve en qué producciones se usó y a qué clientes llegó."""
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # Ingreso del lote
    c.execute("""SELECT material_id, material_nombre, cantidad, fecha, proveedor,
                        numero_oc, numero_factura, fecha_vencimiento, estado_lote
                 FROM movimientos WHERE lote=? AND tipo='Entrada' LIMIT 1""", (lote_mp,))
    ingreso = c.fetchone()
    if not ingreso:
        conn.close()
        return jsonify({'error': f'Lote MP no encontrado: {lote_mp}'}), 404
    mat_info = {
        'material_id': ingreso[0], 'material_nombre': ingreso[1],
        'cantidad_kg_ingresada': round((ingreso[2] or 0) / 1000, 3),
        'fecha_ingreso': ingreso[3][:10] if ingreso[3] else '', 'proveedor': ingreso[4] or '',
        'numero_oc': ingreso[5] or '', 'numero_factura': ingreso[6] or '',
        'fecha_vencimiento': ingreso[7] or '', 'estado_lote': ingreso[8] or 'VIGENTE'
    }
    # Salidas — producciones que consumieron este lote
    c.execute("""SELECT observaciones, cantidad, fecha FROM movimientos
                 WHERE lote=? AND tipo='Salida' ORDER BY fecha""", (lote_mp,))
    salidas = c.fetchall()
    producciones_ref = []
    for obs, cant, fec in salidas:
        # obs format: "FEFO:PROD-00001:Suero TRX x 10kg" or legacy "FEFO: Suero TRX x 10kg"
        lote_prod = ''
        if obs and obs.startswith('FEFO:PROD-'):
            parts = obs.split(':')
            lote_prod = parts[1] if len(parts) > 1 else ''
        producciones_ref.append({
            'lote_produccion': lote_prod, 'g_consumido': round(cant, 2),
            'fecha': fec[:10] if fec else '', 'observaciones': obs or ''
        })
    # Detallar producciones únicas
    lotes_prod_unicos = list(set(p['lote_produccion'] for p in producciones_ref if p['lote_produccion']))
    producciones_detalle = []
    for lp in lotes_prod_unicos:
        c.execute("SELECT producto, cantidad, fecha, operador FROM producciones WHERE lote=?", (lp,))
        pr = c.fetchone()
        if pr:
            # Despachos desde este lote PT
            c.execute("""SELECT d.numero, cl.nombre, d.fecha, di.cantidad
                         FROM despachos_items di
                         JOIN despachos d ON di.numero_despacho=d.numero
                         LEFT JOIN clientes cl ON d.cliente_id=cl.id
                         WHERE di.lote_pt=?""", (lp,))
            dsps = [{'numero': r[0], 'cliente': r[1] or '', 'fecha': r[2], 'cantidad': r[3]} for r in c.fetchall()]
            producciones_detalle.append({
                'lote_ref': lp, 'producto': pr[0], 'cantidad_kg': pr[1],
                'fecha': pr[2][:10] if pr[2] else '', 'operador': pr[3] or '',
                'despachos': dsps
            })
    conn.close()
    return jsonify({
        'lote_mp': lote_mp, 'material': mat_info,
        'salidas': producciones_ref,
        'producciones': producciones_detalle,
        'clientes_afectados': list(set(
            d['cliente'] for p in producciones_detalle for d in p['despachos']
        ))
    })


@app.route('/api/analisis-abc')
def get_analisis_abc():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT material_nombre, SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock
                 FROM movimientos GROUP BY material_nombre ORDER BY stock DESC""")
    items = [(r[0], r[1]) for r in c.fetchall() if r[1] and r[1] > 0]
    conn.close()
    if not items:
        return jsonify({'items': []})
    total = sum(i[1] for i in items)
    cumulative = 0
    abc = []
    for mat, qty in items:
        prev_pct = (cumulative / total) * 100   # % acumulado ANTES de este item
        cumulative += qty
        pct = (cumulative / total) * 100         # % acumulado DESPUÉS
        # Clasificacion basada en donde EMPIEZA el item (estandar Pareto)
        # Un item es A si al agregarlo aun no hemos superado el 80% previo
        clasificacion = 'A' if prev_pct < 80 else ('B' if prev_pct < 95 else 'C')
        abc.append({'material': mat, 'cantidad': qty, 'valor': f'{pct:.1f}%',
                    'clasificacion': clasificacion})
    return jsonify({'items': abc})

@app.route('/api/alertas', methods=['GET', 'POST'])
def handle_alertas():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        c.execute('INSERT INTO alertas (material_id, material_nombre, stock_actual, stock_minimo, fecha, estado) VALUES (?,?,?,?,?,?)',
                  (data['material_id'], data['material_nombre'], data['stock_actual'],
                   data['stock_minimo'], datetime.now().isoformat(), 'Activa'))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Alerta creada'}), 201
    c.execute('SELECT material_nombre, stock_actual, stock_minimo, estado, fecha FROM alertas ORDER BY fecha DESC')
    alertas = [{'material_nombre': r[0], 'stock_actual': r[1], 'stock_minimo': r[2], 'estado': r[3], 'fecha': r[4]} for r in c.fetchall()]
    conn.close()
    return jsonify({'alertas': alertas})



@app.route('/api/alertas-reabastecimiento')
def alertas_reabastecimiento():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT m.material_id,
                        COALESCE(mp.nombre_comercial, m.material_nombre) as nombre,
                        COALESCE(mp.proveedor,'') as proveedor,
                        COALESCE(mp.stock_minimo,0) as stock_minimo,
                        SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad ELSE -m.cantidad END) as stock_actual
                 FROM movimientos m
                 LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
                 GROUP BY m.material_id
                 HAVING stock_actual < stock_minimo AND stock_minimo > 0
                 ORDER BY (stock_actual/stock_minimo) ASC""")
    rows = c.fetchall(); conn.close()
    alertas = []
    for r in rows:
        stock_actual = round(r[4] or 0, 1)
        stock_minimo = round(r[3], 1)
        alertas.append({'codigo_mp': r[0] or '', 'nombre': r[1] or '', 'proveedor': r[2] or '',
                        'stock_minimo': stock_minimo, 'stock_actual': max(stock_actual, 0),
                        'deficit': round(max(stock_minimo - stock_actual, 0), 1)})
    return jsonify({'alertas': alertas, 'total': len(alertas)})

@app.route('/api/stock')
def get_stock():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT material_id, material_nombre, SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE 0 END), SUM(CASE WHEN tipo='Salida' THEN cantidad ELSE 0 END), SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) FROM movimientos GROUP BY material_id, material_nombre ORDER BY material_nombre")
    rows = c.fetchall(); conn.close()
    return jsonify({'items': [{'material_id':r[0],'material_nombre':r[1],'entradas':round(r[2] or 0,2),'salidas':round(r[3] or 0,2),'stock_actual':round(r[4] or 0,2)} for r in rows]})

@app.route('/api/lotes')
def get_lotes():
    from datetime import date; hoy = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT m.material_id, m.material_nombre, m.lote,
                        SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad ELSE -m.cantidad END) as stock_neto,
                        MAX(m.fecha_vencimiento) as fecha_vencimiento,
                        MAX(m.estanteria) as estanteria, MAX(m.posicion) as posicion,
                        MAX(m.proveedor) as proveedor, MAX(m.estado_lote) as estado_lote,
                        COALESCE(MAX(mp.nombre_inci),'') as inci,
                        COALESCE(MAX(mp.tipo),'') as tipo,
                        COALESCE(MAX(mp.stock_minimo),0) as smin
                 FROM movimientos m LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
                 GROUP BY m.material_id, m.lote
                 HAVING stock_neto > -999999
                 ORDER BY m.material_nombre ASC, fecha_vencimiento ASC""")
    rows = c.fetchall(); conn.close()
    result = []
    for r in rows:
        mid,mnm,lote,cant,fvenc,est,pos,prov,estado,inci,tipo,smin = r
        dias,alerta = None,'ok'
        if fvenc and len(str(fvenc))>=10:
            try:
                from datetime import datetime as dt2
                dias=(dt2.strptime(str(fvenc)[:10],'%Y-%m-%d').date()-dt2.strptime(hoy,'%Y-%m-%d').date()).days
                alerta='vencido' if dias<0 else ('critico' if dias<=30 else ('proximo' if dias<=90 else 'ok'))
            except: pass
        result.append({'material_id':mid or '','nombre_inci':inci,'material_nombre':mnm or '',
                       'tipo':tipo,'proveedor':prov or '','stock_min_g':round(smin,1),
                       'lote':lote or '','cantidad_g':round(cant or 0,2),'cantidad_kg':round((cant or 0)/1000,3),
                       'estanteria':est or '','posicion':pos or '',
                       'fecha_vencimiento':str(fvenc)[:10] if fvenc else '',
                       'dias_para_vencer':dias,'estado_lote':estado or '','alerta':alerta})
    return jsonify({'lotes': result, 'total': len(result)})

@app.route('/api/maestro-mps', methods=['GET','POST'])
def handle_maestro():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json
        c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo,proveedor,stock_minimo) VALUES (?,?,?,?,?,?)",
                  (d['codigo_mp'],d.get('nombre_inci',''),d.get('nombre_comercial',''),d.get('tipo',''),d.get('proveedor',''),d.get('stock_minimo',0)))
        conn.commit(); conn.close()
        return jsonify({'message': 'MP guardada'}), 201
    c.execute("SELECT codigo_mp,nombre_inci,nombre_comercial,tipo,proveedor,stock_minimo,COALESCE(precio_referencia,0) FROM maestro_mps WHERE activo=1 ORDER BY nombre_comercial")
    rows = c.fetchall(); conn.close()
    return jsonify({'mps': [{'codigo_mp':r[0],'nombre_inci':r[1],'nombre_comercial':r[2],'tipo':r[3],'proveedor':r[4],'stock_minimo':r[5],'precio_referencia':r[6]} for r in rows]})

@app.route('/api/maestro-mps/<codigo>')
def get_mp(codigo):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT codigo_mp,nombre_inci,nombre_comercial,tipo,proveedor,stock_minimo FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    r = c.fetchone(); conn.close()
    return jsonify({'codigo_mp':r[0],'nombre_inci':r[1],'nombre_comercial':r[2],'tipo':r[3],'proveedor':r[4],'stock_minimo':r[5]}) if r else (jsonify({'error':'not found'}),404)

@app.route('/api/recepcion', methods=['POST'])
def registrar_recepcion():
    d = request.json; codigo = (d.get('codigo_mp') or '').upper().strip()
    if not codigo: return jsonify({'error': 'Codigo MP requerido'}), 400
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT nombre_inci,nombre_comercial,tipo,proveedor FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    mp = c.fetchone()
    nombre = d.get('nombre_comercial','') or (mp[1] if mp else codigo)
    proveedor = d.get('proveedor','') or (mp[3] if mp else '')
    precio_kg = float(d.get('precio_kg') or 0)
    numero_factura = (d.get('numero_factura') or '').strip()
    numero_oc = (d.get('numero_oc') or '').strip()
    cuarentena = bool(d.get('cuarentena', False))
    estado_lote = 'CUARENTENA' if cuarentena else 'VIGENTE'
    # Si la MP es nueva y viene con datos, crearla en el catalogo
    if not mp and (d.get('nombre_inci') or d.get('nombre_comercial')):
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, tipo, proveedor, stock_minimo) VALUES (?,?,?,?,?,?)",
                  (codigo, d.get('nombre_inci',''), nombre, d.get('tipo',''), proveedor, d.get('stock_minimo',0)))
        conn.commit()
    # Actualizar precio_referencia en maestro_mps si viene precio
    if precio_kg > 0:
        try:
            c.execute("UPDATE maestro_mps SET precio_referencia=?, ultima_act_precio=datetime('now') WHERE codigo_mp=?", (precio_kg, codigo))
        except: pass
    lote = (d.get('lote') or '').strip()
    if not lote or lote.upper()=='AUTO':
        from datetime import date; lote = f"ESP{date.today().strftime('%y%m%d')}{codigo[-3:]}"
    c.execute("""INSERT INTO movimientos
                 (material_id,material_nombre,cantidad,tipo,fecha,observaciones,
                  lote,fecha_vencimiento,estanteria,posicion,proveedor,estado_lote,operador,
                  precio_kg,numero_factura,numero_oc)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (codigo,nombre,float(d.get('cantidad',0)),'Entrada',datetime.now().isoformat(),
               d.get('observaciones','Ingreso MP'),lote,d.get('fecha_vencimiento',''),
               d.get('estanteria',''),d.get('posicion',''),proveedor,estado_lote,
               d.get('operador',''),precio_kg,numero_factura,numero_oc))
    mov_id = c.lastrowid
    # Log precio historico
    if precio_kg > 0:
        try:
            c.execute("INSERT OR IGNORE INTO precios_mp_historico (codigo_mp,precio_kg,numero_factura,proveedor,fecha) VALUES (?,?,?,?,datetime('now'))",
                      (codigo, precio_kg, numero_factura, proveedor))
        except: pass
    # Cerrar OC si se referencia una
    if numero_oc:
        try:
            c.execute("UPDATE ordenes_compra_items SET cantidad_recibida_g=cantidad_recibida_g+?,lote_asignado=? WHERE numero_oc=? AND codigo_mp=?",
                      (float(d.get('cantidad',0)), lote, numero_oc, codigo))
            # verificar si todos los items de la OC estan recibidos
            c.execute("SELECT COUNT(*) FROM ordenes_compra_items WHERE numero_oc=? AND (cantidad_g - cantidad_recibida_g) > 1", (numero_oc,))
            pendientes = c.fetchone()[0]
            if pendientes == 0:
                c.execute("UPDATE ordenes_compra SET estado='RECIBIDA',fecha_recepcion=datetime('now'),recibido_por=? WHERE numero_oc=?",
                          (d.get('operador',''), numero_oc))
        except: pass
    conn.commit(); conn.close()
    msg = f'{nombre} ingresada. Lote: {lote}'
    if cuarentena: msg += ' — En CUARENTENA (pendiente aprobacion QC)'
    if numero_oc: msg += f' | OC {numero_oc} actualizada'
    return jsonify({'message': msg,'lote':lote,'codigo':codigo,'nombre':nombre,'cantidad':d.get('cantidad',0),'cuarentena':cuarentena}), 201

@app.route('/api/lotes/cuarentena', methods=['GET'])
def lotes_cuarentena():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT m.id, m.material_id, m.material_nombre, m.lote, m.cantidad,
                      m.fecha, m.proveedor, m.numero_factura, m.numero_oc, m.observaciones,
                      mp.nombre_inci
               FROM movimientos m
               LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
               WHERE m.estado_lote='CUARENTENA' AND m.tipo='Entrada'
               ORDER BY m.fecha DESC""")
    rows = c.fetchall()
    conn.close()
    cols = ['id','codigo_mp','nombre','lote','cantidad','fecha','proveedor','numero_factura','numero_oc','observaciones','nombre_inci']
    return jsonify([dict(zip(cols,r)) for r in rows])

@app.route('/api/lotes/liberar', methods=['POST'])
def liberar_lote():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'Solo administradores pueden liberar lotes'}), 401
    d = request.json or {}
    mov_id = d.get('id')
    accion = (d.get('accion') or 'APROBAR').upper()
    if accion not in ('APROBAR','RECHAZAR'):
        return jsonify({'error': 'Accion debe ser APROBAR o RECHAZAR'}), 400
    nuevo_estado = 'VIGENTE' if accion == 'APROBAR' else 'RECHAZADO'
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE movimientos SET estado_lote=? WHERE id=? AND estado_lote='CUARENTENA'", (nuevo_estado, mov_id))
    if c.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Lote no encontrado o ya procesado'}), 404
    c.execute("""INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                 VALUES (?,?,?,?,?,?,datetime('now'))""",
              (session.get('compras_user','?'), f'LOTE_{accion}', 'movimientos',
               str(mov_id), f'Lote liberado: {accion}', request.remote_addr))
    conn.commit(); conn.close()
    return jsonify({'message': f'Lote {accion.lower()}ado correctamente', 'estado': nuevo_estado})

@app.route('/api/trazabilidad/<lote>', methods=['GET'])
def trazabilidad_lote(lote):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # Ingreso del lote
    c.execute("""SELECT m.material_id, m.material_nombre, m.cantidad, m.fecha,
                      m.proveedor, m.numero_factura, m.numero_oc, m.precio_kg
               FROM movimientos m WHERE m.lote=? AND m.tipo='Entrada' LIMIT 1""", (lote,))
    ingreso = c.fetchone()
    # Consumos en produccion
    # consumos: buscar en producciones que mencionen el lote en observaciones
    c.execute("""SELECT producto, fecha, operador, cantidad
               FROM producciones WHERE observaciones LIKE ? ORDER BY fecha""", (f'%{lote}%',))
    producciones = c.fetchall()
    conn.close()
    return jsonify({
        'lote': lote,
        'ingreso': {'codigo_mp': ingreso[0], 'nombre': ingreso[1], 'cantidad_g': ingreso[2],
                    'fecha': ingreso[3], 'proveedor': ingreso[4], 'factura': ingreso[5],
                    'orden_compra': ingreso[6], 'precio_kg': ingreso[7]} if ingreso else None,
        'producciones': [{'producto': p[0], 'fecha': p[1], 'operador': p[2],
                          'cantidad_g': p[3]} for p in producciones],
        'total_producciones': len(producciones)
    })

# ── CONTEO CICLICO BDG-PRO-002 ──────────────────────────────────
@app.route('/api/conteo/estanterias', methods=['GET'])
def conteo_estanterias():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT COALESCE(NULLIF(estanteria,''),'Sin estanteria') as est,
                        COUNT(DISTINCT material_id) as total_mps,
                        SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock_total
                 FROM movimientos GROUP BY est ORDER BY est""")
    rows = c.fetchall()
    conn.close()
    return jsonify([{'estanteria': r[0], 'total_mps': r[1], 'stock_total': round(r[2] or 0, 1)} for r in rows])

@app.route('/api/conteo/materiales', methods=['GET'])
def conteo_materiales_estanteria():
    est = request.args.get('estanteria', '')
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if est and est != 'Sin estanteria':
        c.execute("""SELECT m.material_id, m.material_nombre,
                            COALESCE(mp.nombre_inci,'') as inci,
                            COALESCE(mp.precio_referencia,0) as precio_ref,
                            SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad ELSE -m.cantidad END) as stock_sistema,
                            MAX(m.estanteria) as estanteria
                     FROM movimientos m
                     LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
                     WHERE m.estanteria=?
                     GROUP BY m.material_id HAVING stock_sistema > 0
                     ORDER BY m.material_nombre""", (est,))
    else:
        c.execute("""SELECT m.material_id, m.material_nombre,
                            COALESCE(mp.nombre_inci,'') as inci,
                            COALESCE(mp.precio_referencia,0) as precio_ref,
                            SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad ELSE -m.cantidad END) as stock_sistema,
                            '' as estanteria
                     FROM movimientos m
                     LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
                     WHERE (m.estanteria IS NULL OR m.estanteria='')
                     GROUP BY m.material_id HAVING stock_sistema > 0
                     ORDER BY m.material_nombre""")
    rows = c.fetchall()
    conn.close()
    cols = ['codigo_mp','nombre','inci','precio_ref','stock_sistema','estanteria']
    return jsonify([dict(zip(cols, r)) for r in rows])

@app.route('/api/conteo/iniciar', methods=['POST'])
def conteo_iniciar():
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    d = request.json or {}
    est = d.get('estanteria', '')
    responsable = d.get('responsable', session.get('compras_user',''))
    from datetime import date
    numero = 'CNT-' + date.today().strftime('%Y%m%d') + '-' + est.replace(' ','')[:6].upper()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    try:
        c.execute("INSERT INTO conteos_fisicos (numero,fecha_inicio,estado,responsable,estanteria,tipo_conteo) VALUES (?,datetime('now'),'Abierto',?,?,'Ciclico')",
                  (numero, responsable, est))
        conteo_id = c.lastrowid
        conn.commit(); conn.close()
        return jsonify({'conteo_id': conteo_id, 'numero': numero, 'message': 'Conteo iniciado'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 400

@app.route('/api/conteo/<int:conteo_id>/guardar', methods=['POST'])
def conteo_guardar(conteo_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    d = request.json or {}
    items = d.get('items', [])
    UMBRAL_ESCALA = 0.05  # 5% -> escala a gerencia (BDG-PRO-002 num 8)
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT estado FROM conteos_fisicos WHERE id=?", (conteo_id,))
    row = c.fetchone()
    if not row or row[0] != 'Abierto':
        conn.close(); return jsonify({'error': 'Conteo no encontrado o ya cerrado'}), 400

    items_con_diff = 0
    for item in items:
        codigo = item.get('codigo_mp','')
        stock_sis = float(item.get('stock_sistema', 0))
        stock_fis = item.get('stock_fisico')
        if stock_fis is None or stock_fis == '': continue
        stock_fis = float(stock_fis)
        diff = stock_fis - stock_sis
        precio_ref = float(item.get('precio_ref', 0))
        valor_diff = abs(diff / 1000) * precio_ref  # diff en g, precio en /kg
        pct_diff = abs(diff / stock_sis) if stock_sis > 0 else 0
        requiere_gerencia = 1 if pct_diff > UMBRAL_ESCALA else 0
        causa = item.get('causa_diferencia', '')
        if abs(diff) > 0: items_con_diff += 1
        c.execute("""INSERT OR REPLACE INTO conteo_items
                     (conteo_id,codigo_mp,nombre_mp,stock_sistema,stock_fisico,diferencia,
                      estanteria,causa_diferencia,valor_diferencia,requiere_gerencia,observaciones)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (conteo_id, codigo, item.get('nombre',''), stock_sis, stock_fis, diff,
                   item.get('estanteria',''), causa, round(valor_diff,0), requiere_gerencia,
                   item.get('observaciones','')))
    c.execute("UPDATE conteos_fisicos SET items_diferencia=?,total_items=? WHERE id=?",
              (items_con_diff, len(items), conteo_id))
    conn.commit(); conn.close()
    return jsonify({'message': 'Conteo guardado', 'items_con_diferencia': items_con_diff})

@app.route('/api/conteo/<int:conteo_id>/cerrar', methods=['POST'])
def conteo_cerrar(conteo_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM conteo_items WHERE conteo_id=? AND requiere_gerencia=1 AND aprobado_gerencia=0", (conteo_id,))
    pendientes_gerencia = c.fetchone()[0]
    c.execute("UPDATE conteos_fisicos SET estado='Cerrado',fecha_cierre=datetime('now') WHERE id=?", (conteo_id,))
    conn.commit(); conn.close()
    msg = 'Conteo cerrado.'
    if pendientes_gerencia:
        msg += f' ATENCION: {pendientes_gerencia} item(s) con diferencia >5% pendientes de aprobacion Gerencia General antes de ajustar (BDG-PRO-002 num 8).'
    return jsonify({'message': msg, 'pendientes_gerencia': pendientes_gerencia})

@app.route('/api/conteo/<int:conteo_id>/ajustar', methods=['POST'])
def conteo_ajustar(conteo_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    user = session.get('compras_user','')
    d = request.json or {}
    item_id = d.get('item_id')
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT ci.*, cf.estado FROM conteo_items ci JOIN conteos_fisicos cf ON ci.conteo_id=cf.id WHERE ci.id=?", (item_id,))
    item = c.fetchone()
    if not item:
        conn.close(); return jsonify({'error': 'Item no encontrado'}), 404
    cols = [desc[0] for desc in c.description]
    it = dict(zip(cols, item))
    if it['requiere_gerencia'] and not it['aprobado_gerencia']:
        if user not in ADMIN_USERS:
            conn.close()
            return jsonify({'error': 'Diferencia >5% requiere aprobacion Gerencia General (BDG-PRO-002)'}), 403
        c.execute("UPDATE conteo_items SET aprobado_gerencia=1,aprobado_gerencia_por=? WHERE id=?", (user, item_id))
    diff = float(it['diferencia'])
    if diff == 0:
        conn.close(); return jsonify({'message': 'Sin diferencia, no se requiere ajuste'})
    tipo_mov = 'Entrada' if diff > 0 else 'Salida'
    obs = f'Ajuste inventario ciclico #{conteo_id} - {it.get("causa_diferencia","Sin causa")} - Aprobado: {user}'
    c.execute("""INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,observaciones,lote,estanteria,estado_lote,operador)
                 VALUES (?,?,?,?,datetime('now'),?,?,?,'VIGENTE',?)""",
              (it['codigo_mp'], it['nombre_mp'], abs(diff), tipo_mov, obs,
               'AJUSTE-'+str(conteo_id), it.get('estanteria',''), user))
    c.execute("UPDATE conteo_items SET ajuste_aplicado=1 WHERE id=?", (item_id,))
    c.execute("INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha) VALUES (?,?,?,?,?,?,datetime('now'))",
              (user, 'AJUSTE_INVENTARIO', 'conteo_items', str(item_id),
               f'MP:{it["codigo_mp"]} Diff:{diff}g Causa:{it.get("causa_diferencia","")}',
               request.remote_addr))
    conn.commit(); conn.close()
    return jsonify({'message': f'Ajuste aplicado: {tipo_mov} de {abs(diff):.0f}g para {it["nombre_mp"]}'})

@app.route('/api/conteo/historial', methods=['GET'])
def conteo_historial():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT cf.id, cf.numero, cf.estanteria, cf.fecha_inicio, cf.fecha_cierre,
                        cf.estado, cf.responsable, cf.total_items, cf.items_diferencia,
                        COUNT(CASE WHEN ci.requiere_gerencia=1 THEN 1 END) as items_gerencia
                 FROM conteos_fisicos cf
                 LEFT JOIN conteo_items ci ON cf.id=ci.conteo_id
                 GROUP BY cf.id ORDER BY cf.fecha_inicio DESC LIMIT 50""")
    rows = c.fetchall()
    conn.close()
    cols = ['id','numero','estanteria','fecha_inicio','fecha_cierre','estado','responsable','total_items','items_diferencia','items_gerencia']
    return jsonify([dict(zip(cols, r)) for r in rows])

@app.route('/api/conteo/<int:conteo_id>/items', methods=['GET'])
def conteo_get_items(conteo_id):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT * FROM conteo_items WHERE conteo_id=? ORDER BY codigo_mp", (conteo_id,))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return jsonify([dict(zip(cols, r)) for r in rows])

@app.route('/api/lotes/cc-review', methods=['POST'])
def cc_review():
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    user = session.get('compras_user', '')
    allowed = set(ADMIN_USERS) | {'hernando'}
    if user not in allowed:
        return jsonify({'error': 'Solo CC o administradores'}), 401
    d = request.json or {}
    mov_id = d.get('mov_id')
    if not mov_id:
        return jsonify({'error': 'mov_id requerido'}), 400
    solubilidad = d.get('solubilidad', '')
    resultado_aql = d.get('resultado_aql', '')
    if solubilidad == 'RECHAZO' or resultado_aql == 'NO_CONFORME':
        estado_final = 'RECHAZADO'
    elif resultado_aql == 'CUARENTENA_EXTENDIDA':
        estado_final = 'CUARENTENA_EXTENDIDA'
    else:
        estado_final = 'APROBADO'
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT id, material_id, lote, estado_lote FROM movimientos WHERE id=?", (mov_id,))
    mov = c.fetchone()
    if not mov:
        conn.close(); return jsonify({'error': 'Lote no encontrado'}), 404
    if mov[3] not in ('CUARENTENA', 'CUARENTENA_EXTENDIDA'):
        conn.close(); return jsonify({'error': 'Lote no esta en cuarentena'}), 400
    c.execute(
        "INSERT INTO cc_reviews (mov_id,lote,codigo_mp,coa_ok,lote_coincide,coa_vigente,ficha_ok,"
        "solubilidad,resultado_aql,observaciones_aql,muestra_retencion,observaciones,firmante,estado_final,fecha,ip) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?)",
        (mov_id, d.get('lote',''), d.get('codigo_mp',''),
         1 if d.get('coa_ok') else 0, 1 if d.get('lote_coincide') else 0,
         1 if d.get('coa_vigente') else 0, 1 if d.get('ficha_ok') else 0,
         solubilidad, resultado_aql, d.get('observaciones_aql',''),
         1 if d.get('muestra_retencion') else 0, d.get('observaciones',''),
         d.get('firmante', user), estado_final, request.remote_addr))
    c.execute("UPDATE movimientos SET estado_lote=? WHERE id=?", (estado_final, mov_id))
    c.execute(
        "INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha) VALUES (?,?,?,?,?,?,datetime('now'))",
        (user, 'CC_REVIEW_'+estado_final, 'movimientos', str(mov_id),
         'Lote '+d.get('lote','')+' AQL:'+resultado_aql+' Solub:'+solubilidad+' Firma:'+d.get('firmante',user),
         request.remote_addr))
    if estado_final == 'RECHAZADO':
        try:
            c.execute(
                "INSERT INTO solicitudes_compra (material_codigo,material_nombre,cantidad,unidad,justificacion,estado,empresa,area,solicitante,fecha) "
                "VALUES (?,?,0,'kg',?,'PENDIENTE','Espagiria','Calidad',?,datetime('now'))",
                (d.get('codigo_mp',''), d.get('lote',''),
                 'LOTE RECHAZADO QC - Devolucion proveedor. Lote: '+d.get('lote',''), user))
        except: pass
    conn.commit(); conn.close()
    msgs = {'APROBADO': 'Lote APROBADO. Disponible para produccion.',
            'RECHAZADO': 'Lote RECHAZADO. Notificacion creada en Compras.',
            'CUARENTENA_EXTENDIDA': 'CUARENTENA EXTENDIDA. Maximo 5 dias para definicion.'}
    return jsonify({'message': msgs.get(estado_final,''), 'estado': estado_final})

@app.route('/api/reset-movimientos', methods=['POST'])
def reset_mov():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado. Solo administradores.'}), 401
    d = request.json or {}
    if d.get('confirmacion','').upper() != 'BORRAR':
        return jsonify({'error': 'Debes enviar confirmacion="BORRAR"'}), 400
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("DELETE FROM movimientos")
    c.execute("""INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                 VALUES (?,?,?,?,?,?,datetime('now'))""",
              (session.get('compras_user','?'), 'RESET_MOVIMIENTOS', 'movimientos',
               'ALL', 'Borrado total de movimientos autorizado', request.remote_addr))
    conn.commit(); conn.close()
    return jsonify({'message': 'Movimientos borrados. Accion registrada en audit_log.'})

@app.route('/rotulos/<producto_nombre>/<cantidad_str>')
def generar_rotulos(producto_nombre, cantidad_str):
    try: cantidad_kg = float(cantidad_str)
    except: return "<h2>Cantidad invalida</h2>", 400
    from datetime import date; import urllib.parse
    hoy = date.today().strftime('%d-%b-%Y').upper()
    prod = urllib.parse.unquote(producto_nombre); op_num = "OP-"+date.today().strftime('%Y%m%d'); cant_g = cantidad_kg*1000
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT material_id,material_nombre,porcentaje FROM formula_items WHERE producto_nombre=?", (prod,))
    items = c.fetchall()
    lotes = {}; incis = {}
    for r in items:
        mid = r[0]
        c.execute("SELECT nombre_inci FROM maestro_mps WHERE codigo_mp=?", (mid,)); ir=c.fetchone(); incis[mid]=ir[0] if ir and ir[0] else ''
        c.execute("SELECT lote,estanteria,posicion,fecha_vencimiento FROM movimientos WHERE material_id=? AND tipo='Entrada' AND lote IS NOT NULL AND lote!='' AND lote!='S/L' ORDER BY CASE WHEN fecha_vencimiento IS NULL OR fecha_vencimiento='' THEN '9999' ELSE fecha_vencimiento END ASC LIMIT 1", (mid,))
        row=c.fetchone(); lotes[mid]={'lote':row[0] if row else 'S/L','est':row[1] if row else '','pos':row[2] if row else '','vence':str(row[3])[:10] if row and row[3] else ''}
    conn.close()
    if not items: return '<h2>Formula no encontrada: '+prod+'</h2>', 404
    rhtml=''; barcodes=''
    for i,r in enumerate(items):
        mid,mnm,pct=r; peso=round((pct/100)*cant_g,2); info=lotes.get(mid,{}); lote_mp=info.get('lote','S/L')
        ubicacion=('Est. '+str(info.get('est',''))+str(info.get('pos',''))).strip(); vence=info.get('vence',''); inci=incis.get(mid,'')
        bv=mid+'|'+lote_mp; barcodes+=f'try{{JsBarcode("#bc{i}","{bv}",{{format:"CODE128",width:1.2,height:35,displayValue:false,margin:0}})}}catch(e){{}};'
        rhtml+='<div class="r"><div class="rh"><span class="rt">ROTULO MATERIA PRIMA DISPENSADA</span><span class="rc">PRD-PRO-001-F08 | v1<br>04-Mar-2025 / 03-Mar-2028</span></div>'
        rhtml+='<table><tr><td class="l">OP:</td><td class="v">'+op_num+'</td><td class="l">Fecha:</td><td class="v">'+hoy+'</td></tr>'
        rhtml+='<tr><td class="l">Producto:</td><td class="v big" colspan="3"><b>'+prod+'</b> &mdash; '+str(cantidad_kg)+' kg</td></tr>'
        rhtml+='<tr><td class="l">Nombre MP:</td><td class="v bold" colspan="3"><b>'+mnm+'</b> <span style="color:#888;font-size:0.8em;">('+mid+')</span></td></tr>'
        if inci: rhtml+='<tr><td class="l">Nombre INCI:</td><td class="v" colspan="3" style="font-size:0.82em;color:#444;">'+inci+'</td></tr>'
        rhtml+='<tr><td class="l">Lote MP:</td><td class="v bold">'+lote_mp+'</td><td class="l">Ubicacion:</td><td class="v">'+ubicacion+'</td></tr>'
        rhtml+='<tr><td class="l">Vencimiento:</td><td class="v" style="color:#c0392b;">'+vence+'</td><td class="l">% formula:</td><td class="v">'+str(pct)+'%</td></tr>'
        rhtml+='<tr><td class="l">Peso teorico:</td><td class="v peso">'+f"{peso:,.2f} g"+'</td><td class="l">Lote Prod.:</td><td class="blank"></td></tr>'
        rhtml+='<tr><td class="l">Tara:</td><td class="blank"></td><td class="l">Peso Neto:</td><td class="blank"></td></tr>'
        rhtml+='<tr><td class="l">Pesado por:</td><td class="blank firma"></td><td class="l">Verificado:</td><td class="blank firma"></td></tr>'
        rhtml+='</table>'
        rhtml+='<div style="text-align:center;padding:4px;"><svg id="bc'+str(i)+'"></svg></div>'
        rhtml+='<div class="rf">'+mid+'|'+lote_mp+' | #'+str(i+1)+' de '+str(len(items))+'</div></div>'
    css=('<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script><title>Rotulos</title>'
         '<script src="https://cdnjs.cloudflare.com/ajax/libs/jsbarcode/3.11.5/JsBarcode.all.min.js"></script>'
         '<style>*{margin:0;padding:0;box-sizing:border-box;}body{font-family:Arial,sans-serif;font-size:9pt;background:#eee;}'
         '.ph{background:#1a252f;color:white;padding:10px 16px;display:flex;justify-content:space-between;align-items:center;}'
         '.pbtn{background:#27ae60;color:white;border:none;padding:7px 18px;border-radius:4px;cursor:pointer;font-weight:bold;}'
         '.wrap{display:flex;flex-wrap:wrap;gap:5px;padding:8px;}'
         '.r{background:white;border:2px solid #1a252f;border-radius:3px;width:370px;page-break-inside:avoid;}'
         '.rh{background:#1a252f;color:white;padding:5px 8px;display:flex;justify-content:space-between;align-items:center;}'
         '.rt{font-weight:bold;font-size:8pt;}.rc{font-size:6.5pt;text-align:right;line-height:1.4;}'
         'table{width:100%;border-collapse:collapse;}td{border:1px solid #bbb;padding:3px 5px;vertical-align:middle;}'
         '.l{background:#ecf0f1;font-weight:bold;font-size:7.5pt;color:#1a252f;white-space:nowrap;width:27%;}'
         '.v{font-size:8.5pt;width:23%;}.bold{font-size:9pt;}.big{font-size:9pt;}'
         '.peso{background:#fff3cd;color:#c0392b;font-size:12pt;font-weight:bold;}'
         '.blank{height:20px;width:23%;}.firma{height:26px;}.rf{background:#ecf0f1;padding:2px 6px;font-size:6.5pt;color:#888;text-align:right;}'
         '@media print{body{background:white;}.ph{display:none;}.wrap{padding:0;gap:3px;}.r{width:48%;}@page{size:letter landscape;margin:7mm;}}'
         '</style></head><body>')
    return (css+'<div class="ph"><div><h2>Rotulos &mdash; '+prod+' &mdash; '+str(cantidad_kg)+' kg</h2>'
            '<div style="font-size:8pt;opacity:0.8;">'+op_num+' | '+str(len(items))+' MPs | '+hoy+'</div></div>'
            '<button class="pbtn" onclick="window.print()">Imprimir todos</button></div>'
            '<div class="wrap">'+rhtml+'</div>'
            '<script>window.onload=function(){'+barcodes+'};</script>'
            '</body></html>')

@app.route('/rotulo-recepcion/<codigo>/<lote>/<cantidad_str>')
def rotulo_recepcion(codigo, lote, cantidad_str):
    try: cantidad = float(cantidad_str)
    except: return "<h2>Cantidad invalida</h2>", 400
    from datetime import date; import urllib.parse
    hoy = date.today().strftime('%d-%b-%Y').upper(); lote=urllib.parse.unquote(lote)
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT nombre_inci,nombre_comercial,tipo,proveedor FROM maestro_mps WHERE codigo_mp=?", (codigo,)); mp=c.fetchone()
    c.execute("SELECT fecha_vencimiento,estanteria,posicion FROM movimientos WHERE material_id=? AND lote=? ORDER BY fecha DESC LIMIT 1", (codigo,lote)); mov=c.fetchone(); conn.close()
    ni=mp[0] if mp else ''; nc=mp[1] if mp else codigo; tp=mp[2] if mp else ''; pv=mp[3] if mp else ''
    fv=str(mov[0])[:10] if mov and mov[0] else ''; ub=((mov[1] or '')+(mov[2] or '')) if mov else ''
    nr="REC-"+date.today().strftime('%Y%m%d')+"-"+codigo[-3:]; bv=codigo+'|'+lote
    h=('<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script><title>Rotulo Recepcion</title>'
       '<script src="https://cdnjs.cloudflare.com/ajax/libs/jsbarcode/3.11.5/JsBarcode.all.min.js"></script>'
       '<style>*{margin:0;padding:0;box-sizing:border-box;}body{font-family:Arial,sans-serif;font-size:10pt;background:#eee;padding:20px;}'
       '.ph{background:#1a252f;color:white;padding:10px 16px;display:flex;justify-content:space-between;margin-bottom:10px;}'
       '.pb{background:#27ae60;color:white;border:none;padding:7px 18px;border-radius:4px;cursor:pointer;font-weight:bold;}'
       '.r{background:white;border:3px solid #1a252f;border-radius:5px;max-width:520px;margin:auto;}'
       '.rh{background:#1a252f;color:white;padding:8px 12px;text-align:center;}'
       '.lote{background:#fff3cd;border:2px solid #f39c12;padding:10px;text-align:center;margin:10px;}'
       '.lnum{font-size:20pt;font-weight:bold;color:#c0392b;letter-spacing:2px;}'
       'table{width:100%;border-collapse:collapse;}td{border:1px solid #ccc;padding:6px 8px;}'
       '.l{background:#ecf0f1;font-weight:bold;font-size:8.5pt;width:35%;}'
       '@media print{.ph{display:none;}body{background:white;padding:0;}}'
       '</style></head><body>')
    h+=('<div class="ph"><b>Rotulo de Recepcion — Materia Prima</b><button class="pb" onclick="window.print()">Imprimir</button></div>'
        '<div class="r"><div class="rh">'
        '<span style="font-weight:bold;font-size:11pt;display:block;margin-bottom:2px;">ROTULO DE INGRESO DE MATERIA PRIMA</span>'
        '<span style="font-size:7.5pt;opacity:0.85;">Espagiria Laboratorios &nbsp;|&nbsp; COC-PRO-002-F07 &nbsp;|&nbsp; '+hoy+'</span>'
        '</div>'
        '<div class="lote"><div style="font-size:9pt;color:#888;margin-bottom:4px;">NUMERO DE LOTE — CODIGO DE BARRAS</div>'
        '<div class="lnum">'+lote+'</div>'
        '<svg id="bc" style="margin-top:6px;"></svg>'
        '<div style="font-size:7pt;color:#888;margin-top:2px;">'+bv+'</div>'
        '</div><table>'
        '<tr><td class="l">Codigo MP:</td><td style="font-weight:700;">'+codigo+'</td></tr>'
        '<tr><td class="l">Nombre INCI:</td><td style="font-size:0.9em;color:#1a5276;">'+ni+'</td></tr>'
        '<tr><td class="l">Nombre Comercial:</td><td style="font-weight:700;">'+nc+'</td></tr>'
        '<tr><td class="l">Tipo / Funcion:</td><td>'+tp+'</td></tr>'
        '<tr><td class="l">Proveedor:</td><td style="font-weight:700;">'+pv+'</td></tr>'
        '<tr><td class="l">Cantidad recibida:</td><td style="color:#27ae60;font-weight:700;">'+f"{cantidad:,.0f} g"+'</td></tr>'
        '<tr><td class="l">Fecha de recepcion:</td><td style="font-weight:700;">'+hoy+'</td></tr>'
        '<tr><td class="l">Fecha de vencimiento:</td><td style="color:#c0392b;font-weight:700;">'+fv+'</td></tr>'
        '<tr><td class="l">Fecha de analisis:</td><td style="height:28px;background:#fffde7;"></td></tr>'
        '<tr style="background:#e8f5e9;"><td class="l" style="color:#1b5e20;font-weight:800;">Estado de calidad:</td>'
        '<td style="height:28px;"><span style="margin-right:18px;">&#9744; Aprobado</span><span style="margin-right:18px;">&#9744; En cuarentena</span><span>&#9744; Rechazado</span></td></tr>'
        '<tr><td class="l">Ubicacion:</td><td>Est. '+ub+'</td></tr>'
        '<tr><td class="l">N de Recepcion:</td><td>'+nr+'</td></tr>'
        '<tr><td class="l">Recibido por:</td><td style="height:30px;"></td></tr>'
        '<tr><td class="l">Analizado / Aprobado por:</td><td style="height:30px;"></td></tr>'
        '</table>'
        '<div style="background:#ecf0f1;padding:4px 10px;font-size:7.5pt;color:#888;text-align:center;">'
        'COC-PRO-002-F07 &nbsp;|&nbsp; Ingreso registrado al sistema &nbsp;|&nbsp; '+hoy
        +'</div>'
        '</div>'
        '<script>window.onload=function(){try{JsBarcode("#bc","'+bv+'",{format:"CODE128",width:1.5,height:45,displayValue:false,margin:0});}catch(e){}}</script>'
        '</body></html>')
    return h


@app.route('/rotulo-recepcion-mee/<codigo>/<cantidad_str>')
def rotulo_recepcion_mee(codigo, cantidad_str):
    try: cantidad = int(float(cantidad_str))
    except: return "<h2>Cantidad invalida</h2>", 400
    from datetime import date; import urllib.parse
    hoy = date.today().strftime('%d-%b-%Y').upper()
    codigo = urllib.parse.unquote(codigo)
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT descripcion, categoria, proveedor FROM mee WHERE codigo=?", (codigo,))
    mee = c.fetchone()
    c.execute("SELECT referencia, operador, fecha FROM movimientos_mee WHERE codigo_mee=? AND tipo='entrada' ORDER BY id DESC LIMIT 1", (codigo,))
    mov = c.fetchone(); conn.close()
    desc = mee[0] if mee else codigo; cat = mee[1] if mee else ''; prov = mee[2] if mee else ''
    ref  = mov[0] if mov else ''; oper = mov[1] if mov else ''
    nr   = "REC-MEE-" + date.today().strftime('%Y%m%d') + "-" + codigo[-4:]
    bv   = codigo; prov_display = ref or prov
    h = ('<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
         '<script src="https://cdnjs.cloudflare.com/ajax/libs/jsbarcode/3.11.5/JsBarcode.all.min.js"></script>'
         '<style>*{margin:0;padding:0;box-sizing:border-box;}body{font-family:Arial,sans-serif;font-size:10pt;background:#eee;padding:20px;}'
         '.ph{background:#1a3a5c;color:white;padding:10px 16px;display:flex;justify-content:space-between;margin-bottom:10px;}'
         '.pb{background:#2980b9;color:white;border:none;padding:7px 18px;border-radius:4px;cursor:pointer;font-weight:bold;}'
         '.r{background:white;border:3px solid #1a3a5c;border-radius:5px;max-width:520px;margin:auto;}'
         '.rh{background:#1a3a5c;color:white;padding:8px 12px;text-align:center;}'
         '.lote{background:#e8f4fd;border:2px solid #2980b9;padding:10px;text-align:center;margin:10px;}'
         '.lnum{font-size:16pt;font-weight:bold;color:#1a3a5c;letter-spacing:2px;}'
         'table{width:100%;border-collapse:collapse;}td{border:1px solid #ccc;padding:6px 8px;}'
         '.l{background:#ecf0f1;font-weight:bold;font-size:8.5pt;width:38%;}'
         '.calidad{background:#e8f5e9;}'
         '@media print{.ph{display:none;}body{background:white;padding:0;}}'
         '</style></head><body>')
    h += ('<div class="ph"><b>Rótulo de Recepción — Material E&E</b>'
          '<button class="pb" onclick="window.print()">Imprimir</button></div>'
          '<div class="r"><div class="rh">'
          '<span style="font-weight:bold;font-size:11pt;display:block;margin-bottom:2px;">ROTULO DE INGRESO DE MATERIAL E&E</span>'
          '<span style="font-size:7.5pt;opacity:0.85;">Espagiria Laboratorios &nbsp;|&nbsp; COC-PRO-002-F07 &nbsp;|&nbsp; ' + hoy + '</span>'
          '</div>'
          '<div class="lote">'
          '<div style="font-size:9pt;color:#666;margin-bottom:4px;">CODIGO MATERIAL — CODIGO DE BARRAS</div>'
          '<div class="lnum">' + codigo + '</div>'
          '<svg id="bc" style="margin-top:6px;"></svg>'
          '</div><table>'
          '<tr><td class="l">Código MEE:</td><td style="font-weight:700;">' + codigo + '</td></tr>'
          '<tr><td class="l">Descripción:</td><td style="font-weight:700;">' + desc + '</td></tr>'
          '<tr><td class="l">Categoría:</td><td>' + cat + '</td></tr>'
          '<tr><td class="l">Proveedor / Ref. compra:</td><td style="font-weight:700;">' + prov_display + '</td></tr>'
          '<tr><td class="l">Cantidad recibida:</td><td style="color:#27ae60;font-weight:700;">' + f"{cantidad:,}" + ' unidades</td></tr>'
          '<tr><td class="l">Fecha de recepción:</td><td style="font-weight:700;">' + hoy + '</td></tr>'
          '<tr><td class="l">Fecha de análisis / inspección:</td><td style="height:28px;background:#fffde7;"></td></tr>'
          '<tr><td class="l">Piezas inspeccionadas (AQL):</td><td style="height:28px;"></td></tr>'
          '<tr class="calidad"><td class="l calidad" style="color:#1b5e20;font-weight:800;">Estado de calidad:</td>'
          '<td style="height:28px;"><span style="margin-right:14px;">&#9744; Aprobado</span>'
          '<span style="margin-right:14px;">&#9744; En cuarentena</span>'
          '<span>&#9744; Rechazado</span></td></tr>'
          '<tr><td class="l">Número de recepción:</td><td>' + nr + '</td></tr>'
          '<tr><td class="l">Recibido por:</td><td style="height:30px;">' + oper + '</td></tr>'
          '<tr><td class="l">Aprobado por (Calidad):</td><td style="height:30px;"></td></tr>'
          '</table>'
          '<div style="background:#dde8f0;padding:4px 10px;font-size:7.5pt;color:#555;text-align:center;">'
          'COC-PRO-002-F07 &nbsp;|&nbsp; Material Envase & Empaque &nbsp;|&nbsp; ' + hoy + '</div>'
          '</div>'
          '<script>window.onload=function(){try{JsBarcode("#bc","' + bv + '",{format:"CODE128",width:1.5,height:45,displayValue:false,margin:0});}catch(e){}}</script>'
          '</body></html>')
    return h


@app.route('/api/dashboard-stats')
def dashboard_stats():
    from datetime import date
    hoy = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()

    # Vencimientos por mes (próximos 6 meses)
    venc_por_mes = {}
    c.execute("""SELECT fecha_vencimiento, COUNT(*) as n, SUM(cantidad) as total_g
                 FROM movimientos WHERE tipo='Entrada' AND fecha_vencimiento IS NOT NULL
                 AND fecha_vencimiento >= ? AND fecha_vencimiento <= date(?, '+180 days')
                 GROUP BY substr(fecha_vencimiento,1,7) ORDER BY fecha_vencimiento""", (hoy, hoy))
    for row in c.fetchall():
        if row[0]:
            mes = str(row[0])[:7]
            venc_por_mes[mes] = {'lotes': row[1], 'kg': round((row[2] or 0)/1000, 1)}

    # Alertas de reabastecimiento: MPs bajo mínimo
    c.execute("""SELECT COUNT(*) FROM maestro_mps m
                 LEFT JOIN (SELECT material_id, SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock
                            FROM movimientos GROUP BY material_id) s ON m.codigo_mp=s.material_id
                 WHERE m.activo=1 AND m.stock_minimo>0 AND COALESCE(s.stock,0)<m.stock_minimo""")
    mps_bajo_minimo = c.fetchone()[0] or 0

    # Lotes vencidos / críticos / próximos
    c.execute("""SELECT estado_lote, COUNT(*) FROM movimientos WHERE tipo='Entrada' AND estado_lote IN ('VENCIDO','CRITICO','PROXIMO')
                 GROUP BY estado_lote""")
    estados = {r[0]: r[1] for r in c.fetchall()}

    # Top 5 MPs por stock actual
    c.execute("""SELECT material_id, material_nombre,
                        SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock
                 FROM movimientos GROUP BY material_id, material_nombre
                 HAVING stock > 0 ORDER BY stock DESC LIMIT 5""")
    top_stock = [{'codigo': r[0], 'nombre': r[1], 'kg': round(r[2]/1000, 1)} for r in c.fetchall()]

    # Stock total en kg
    c.execute("SELECT SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) FROM movimientos")
    stock_total_g = c.fetchone()[0] or 0

    conn.close()
    return jsonify({
        'vencimientos_por_mes': venc_por_mes,
        'mps_bajo_minimo': mps_bajo_minimo,
        'estados_lotes': estados,
        'top_stock': top_stock,
        'stock_total_kg': round(stock_total_g/1000, 1)
    })


@app.route('/api/generar-oc-automatica', methods=['POST'])
def generar_oc_automatica():
    """Genera OCs automaticas por proveedor para todas las MPs bajo minimo"""
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()

    # Obtener MPs bajo minimo
    c.execute("""SELECT m.codigo_mp, m.nombre_comercial, m.proveedor, m.stock_minimo,
                        COALESCE(s.stock_actual, 0) as stock_actual
                 FROM maestro_mps m
                 LEFT JOIN (SELECT material_id,
                            SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock_actual
                            FROM movimientos GROUP BY material_id) s ON m.codigo_mp=s.material_id
                 WHERE m.activo=1 AND m.stock_minimo>0 AND COALESCE(s.stock_actual,0)<m.stock_minimo
                 ORDER BY m.proveedor, m.nombre_comercial""")
    alertas = c.fetchall()

    if not alertas:
        conn.close()
        return jsonify({'message': 'No hay MPs bajo stock minimo', 'ordenes': []})

    # Agrupar por proveedor
    por_proveedor = {}
    for row in alertas:
        codigo, nombre, prov, smin, sact = row
        prov = prov or 'Sin proveedor'
        deficit = smin - sact
        cantidad_pedir = round(deficit * 1.1, 0)  # pedir el deficit + 10% extra
        if prov not in por_proveedor:
            por_proveedor[prov] = []
        por_proveedor[prov].append({
            'codigo_mp': codigo, 'nombre_mp': nombre,
            'stock_actual': round(sact, 0), 'stock_minimo': smin,
            'deficit': round(deficit, 0), 'cantidad_pedir': cantidad_pedir,
            'unidad': 'g'
        })

    # Crear OC por cada proveedor
    ordenes_creadas = []
    for prov, items in por_proveedor.items():
        c.execute("SELECT COUNT(*) FROM ordenes_compra"); num=(c.fetchone()[0] or 0)+1
        numero_oc = f"OC-{datetime.now().strftime('%Y')}-{num:04d}"
        c.execute("INSERT INTO ordenes_compra (numero_oc, fecha, estado, proveedor, observaciones) VALUES (?,?,?,?,?)",
                  (numero_oc, datetime.now().isoformat(), 'Pendiente', prov, 'Generada automaticamente por stock bajo minimo'))
        for item in items:
            c.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g) VALUES (?,?,?,?)",
                      (numero_oc, item['codigo_mp'], item['nombre_mp'], item['cantidad_pedir']))
        # Generar cuerpo del email
        sep = '-' * 50
        fecha_str = datetime.now().strftime('%d/%m/%Y')
        eb = 'ORDEN DE COMPRA: ' + numero_oc + '\n'
        eb += 'Fecha: ' + fecha_str + '\n'
        eb += 'Proveedor: ' + prov + '\n'
        eb += 'Generada por: Sistema de Inventarios Espagiria\n\n'
        eb += 'MATERIAS PRIMAS A COMPRAR:\n' + sep + '\n'
        for it in items:
            eb += str(it['codigo_mp']) + ' - ' + str(it['nombre_mp']) + '\n'
            eb += '  Stock actual: ' + str(int(it['stock_actual'])) + 'g | Minimo: ' + str(int(it['stock_minimo'])) + 'g\n'
            eb += '  CANTIDAD A PEDIR: ' + str(int(it['cantidad_pedir'])) + ' g = ' + str(round(it['cantidad_pedir']/1000, 2)) + ' kg\n'
            eb += sep + '\n'
        eb += '\nTotal: ' + str(len(items)) + ' items pendientes de compra.\n'
        eb += 'Por favor aprobar y contactar al proveedor.\n'
        eb += '\n--- Sistema de Inventarios Espagiria Laboratorios ---\n'
        email_body = eb
        ordenes_creadas.append({
            'numero_oc': numero_oc, 'proveedor': prov,
            'total_items': len(items), 'items': items,
            'email_subject': f'[OC] {numero_oc} - Espagiria Laboratorios',
            'email_body': email_body
        })

    conn.commit(); conn.close()
    return jsonify({
        'message': f'{len(ordenes_creadas)} OC(s) generadas automaticamente',
        'ordenes': ordenes_creadas
    }), 201


# ── MÓDULO COMPRAS ──────────────────────────────────────────────────────────
@app.route('/api/ordenes-compra', methods=['GET','POST'])
def handle_ordenes_compra():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json
        if not d.get('proveedor'): conn.close(); return jsonify({'error': 'Proveedor requerido'}), 400
        c.execute("SELECT COUNT(*) FROM ordenes_compra"); num = (c.fetchone()[0] or 0) + 1
        numero_oc = f"OC-{datetime.now().strftime('%Y')}-{num:04d}"
        categoria = d.get('categoria', 'MP')
        c.execute("INSERT INTO ordenes_compra (numero_oc,fecha,estado,proveedor,observaciones,creado_por,fecha_entrega_est,categoria) VALUES (?,?,?,?,?,?,?,?)",
                  (numero_oc, datetime.now().isoformat(), 'Borrador', d['proveedor'],
                   d.get('observaciones',''), d.get('creado_por',''), d.get('fecha_entrega_est',''), categoria))
        for it in (d.get('items') or []):
            subtotal = round((it.get('cantidad_g',0)) * (it.get('precio_unitario',0)), 2)
            c.execute("INSERT INTO ordenes_compra_items (numero_oc,codigo_mp,nombre_mp,cantidad_g,precio_unitario,subtotal) VALUES (?,?,?,?,?,?)",
                      (numero_oc, it.get('codigo_mp',''), it.get('nombre_mp',''),
                       it.get('cantidad_g',0), it.get('precio_unitario',0), subtotal))
        valor_total_calc = sum(
            round((it.get('cantidad_g',0))*(it.get('precio_unitario',0)),2)
            for it in (d.get('items') or [])
        )
        if valor_total_calc > 0:
            c.execute("UPDATE ordenes_compra SET valor_total=? WHERE numero_oc=?", (valor_total_calc, numero_oc))
        conn.commit(); conn.close()
        return jsonify({'message': f'OC {numero_oc} creada', 'numero_oc': numero_oc}), 201
    cat_filter = request.args.get('categoria', '')
    _sql = (
        "SELECT o.numero_oc, o.fecha, o.estado, o.proveedor, o.fecha_entrega_est,"
        " o.observaciones, o.creado_por, COUNT(i.id) as num_items,"
        " o.categoria, o.remision_code, o.autorizado_por,"
        " COALESCE(o.valor_total, 0) as valor_total"
        " FROM ordenes_compra o LEFT JOIN ordenes_compra_items i ON o.numero_oc=i.numero_oc"
    )
    if cat_filter:
        c.execute(_sql + " WHERE o.categoria=? GROUP BY o.numero_oc ORDER BY o.fecha DESC LIMIT 300", (cat_filter,))
    else:
        c.execute(_sql + " GROUP BY o.numero_oc ORDER BY o.fecha DESC LIMIT 300")
    cols = ['numero_oc','fecha','estado','proveedor','fecha_entrega_est','observaciones',
            'creado_por','num_items','categoria','remision_code','autorizado_por','valor_total']
    rows = c.fetchall(); conn.close()
    return jsonify({'ordenes': [dict(zip(cols, r)) for r in rows]})

@app.route('/api/ordenes-compra/<numero_oc>', methods=['GET','PUT'])
def handle_oc_detalle(numero_oc):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'PUT':
        d = request.json
        nuevo_estado = d.get('estado','')
        usuario_actual = session.get('compras_user','')
        if usuario_actual in CONTADORA_USERS and nuevo_estado in ('Aprobada','Pagada'):
            conn.close(); return jsonify({'error':'Sin permiso para esta accion'}), 403
        if d.get('estado'): c.execute("UPDATE ordenes_compra SET estado=? WHERE numero_oc=?", (d['estado'], numero_oc))
        conn.commit(); conn.close(); return jsonify({'message': f'OC {numero_oc} actualizada'})
    c.execute("SELECT * FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    oc_row = c.fetchone()
    oc_cols = [d[0] for d in c.description] if c.description else []
    c.execute("SELECT * FROM ordenes_compra_items WHERE numero_oc=?", (numero_oc,))
    items = c.fetchall(); conn.close()
    if not oc_row: return jsonify({'error': 'OC no encontrada'}), 404
    return jsonify({'oc': dict(zip(oc_cols, oc_row)), 'items': items})

@app.route('/api/proveedores-compras', methods=['GET','POST'])
def handle_proveedores_compras():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json
        if not d.get('nombre'): conn.close(); return jsonify({'error': 'Nombre requerido'}), 400
        try:
            c.execute("""INSERT INTO proveedores
                (nombre,contacto,email,telefono,categoria,condiciones_pago,
                 nit,direccion,num_cuenta,tipo_cuenta,banco,concepto_compra,fecha_creacion)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (d['nombre'],d.get('contacto',''),d.get('email',''),d.get('telefono',''),
                 d.get('categoria',''),d.get('condiciones_pago','30 dias'),
                 d.get('nit',''),d.get('direccion',''),d.get('num_cuenta',''),
                 d.get('tipo_cuenta',''),d.get('banco',''),d.get('concepto_compra',d.get('concepto','')),
                 datetime.now().isoformat()))
            conn.commit(); conn.close()
            return jsonify({'message': f"Proveedor '{d['nombre']}' creado"}), 201
        except Exception as e: conn.close(); return jsonify({'error': str(e)}), 400
    c.execute("""SELECT nombre,contacto,email,telefono,categoria,condiciones_pago,
                       nit,direccion,num_cuenta,tipo_cuenta,banco,concepto_compra
                FROM proveedores WHERE activo=1 ORDER BY nombre""")
    cols = ['nombre','contacto','email','telefono','categoria','condiciones_pago',
            'nit','direccion','num_cuenta','tipo_cuenta','banco','concepto_compra']
    provs = [dict(zip(cols, r)) for r in c.fetchall()]; conn.close()
    return jsonify({'proveedores': provs})

@app.route('/api/proveedores-compras/<path:nombre>/ficha')
def proveedor_ficha_360(nombre):
    """Proveedor 360: datos completos + historial OCs + scoring."""
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT id, nombre, contacto, email, telefono, categoria,
                        nit, direccion, num_cuenta, tipo_cuenta, banco, concepto_compra,
                        id_interno, estado_lpa, ultima_evaluacion, vencimiento_docs,
                        acuerdo_calidad, condiciones_pago
                 FROM proveedores WHERE nombre=? AND activo=1""", (nombre,))
    row = c.fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'Proveedor no encontrado'}), 404
    cols = ['id','nombre','contacto','email','telefono','categoria',
            'nit','direccion','num_cuenta','tipo_cuenta','banco','concepto_compra',
            'id_interno','estado_lpa','ultima_evaluacion','vencimiento_docs',
            'acuerdo_calidad','condiciones_pago']
    prov = dict(zip(cols, row))
    # OC stats
    c.execute("""SELECT COUNT(*), COALESCE(SUM(valor_total),0), MIN(fecha), MAX(fecha)
                 FROM ordenes_compra WHERE proveedor=?""", (nombre,))
    r = c.fetchone()
    oc_total, valor_total, primera_oc, ultima_oc = (r[0] or 0), (r[1] or 0), r[2], r[3]
    c.execute("SELECT COUNT(*) FROM ordenes_compra WHERE proveedor=? AND estado IN ('Recibida','Pagada','Parcial')", (nombre,))
    oc_recibidas = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM ordenes_compra WHERE proveedor=? AND tiene_discrepancias=1 AND estado IN ('Recibida','Pagada','Parcial')", (nombre,))
    oc_disc = c.fetchone()[0] or 0
    # Scoring: cumplimiento 70% + calidad (sin discrepancias) 30%
    cumplimiento = round((oc_recibidas / oc_total * 100) if oc_total > 0 else 0, 1)
    tasa_disc = round((oc_disc / oc_recibidas * 100) if oc_recibidas > 0 else 0, 1)
    score = min(100.0, round(cumplimiento * 0.7 + (100 - tasa_disc) * 0.3, 1))
    # Recent OCs
    c.execute("""SELECT numero_oc, fecha, estado, valor_total, categoria,
                        tiene_discrepancias, fecha_recepcion
                 FROM ordenes_compra WHERE proveedor=?
                 ORDER BY fecha DESC LIMIT 8""", (nombre,))
    oc_cols = ['numero_oc','fecha','estado','valor_total','categoria','tiene_discrepancias','fecha_recepcion']
    ocs_recientes = [dict(zip(oc_cols, r)) for r in c.fetchall()]
    # Materials bought from this supplier
    c.execute("""SELECT oci.codigo_mp, oci.nombre_mp, COUNT(*) as veces, SUM(oci.cantidad_g) as total_g
                 FROM ordenes_compra oc
                 JOIN ordenes_compra_items oci ON oc.numero_oc=oci.numero_oc
                 WHERE oc.proveedor=?
                 GROUP BY oci.codigo_mp, oci.nombre_mp
                 ORDER BY total_g DESC LIMIT 15""", (nombre,))
    mps = [{'codigo': r[0], 'nombre': r[1], 'veces': r[2], 'total_g': round(r[3] or 0, 1)}
           for r in c.fetchall()]
    conn.close()
    return jsonify({
        'proveedor': prov,
        'stats': {
            'oc_total': oc_total, 'oc_recibidas': oc_recibidas, 'oc_discrepancias': oc_disc,
            'valor_total': valor_total, 'primera_oc': primera_oc, 'ultima_oc': ultima_oc,
            'cumplimiento': cumplimiento, 'tasa_discrepancias': tasa_disc, 'score': score
        },
        'ocs_recientes': ocs_recientes,
        'materiales': mps
    })


@app.route('/api/solicitudes-compra', methods=['GET','POST'])
def handle_solicitudes_compra():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json
        c.execute("SELECT COUNT(*) FROM solicitudes_compra"); num = (c.fetchone()[0] or 0) + 1
        numero = f"SOL-{datetime.now().strftime('%Y')}-{num:04d}"
        emp = d.get('empresa','Espagiria')
        cat = d.get('categoria','Materia Prima')
        tip = d.get('tipo','Compra')
        area = d.get('area','Produccion')
        c.execute("""INSERT INTO solicitudes_compra
                     (numero,fecha,estado,solicitante,urgencia,observaciones,area,empresa,categoria,tipo)
                     VALUES (?,?,?,?,?,?,?,?,?,?)""",
                  (numero, datetime.now().isoformat(), 'Pendiente',
                   d.get('solicitante',''), d.get('urgencia','Normal'), d.get('observaciones',''),
                   area, emp, cat, tip))
        for it in (d.get('items') or []):
            c.execute("""INSERT INTO solicitudes_compra_items
                         (numero,codigo_mp,nombre_mp,cantidad_g,unidad,justificacion,valor_estimado)
                         VALUES (?,?,?,?,?,?,?)""",
                      (numero, it.get('codigo_mp',''), it.get('nombre_mp',''),
                       it.get('cantidad_g',0), it.get('unidad','g'),
                       it.get('justificacion',''), it.get('valor_estimado',0)))
        conn.commit(); conn.close()
        return jsonify({'message': f'Solicitud {numero} creada', 'numero': numero}), 201
    # GET: listar todas las solicitudes
    filtro_estado = request.args.get('estado', '')
    filtro_empresa = request.args.get('empresa', '')
    sql = "SELECT numero,fecha,estado,solicitante,urgencia,observaciones,empresa,categoria,tipo,area FROM solicitudes_compra WHERE 1=1"
    params = []
    if filtro_estado: sql += " AND estado=?"; params.append(filtro_estado)
    if filtro_empresa: sql += " AND empresa=?"; params.append(filtro_empresa)
    sql += " ORDER BY fecha DESC LIMIT 200"
    c.execute(sql, params)
    cols_sol = ['numero','fecha','estado','solicitante','urgencia','observaciones','empresa','categoria','tipo','area']
    rows_sol = [dict(zip(cols_sol, r)) for r in c.fetchall()]
    conn.close()
    return jsonify({'solicitudes': rows_sol})


@app.route('/api/solicitudes-compra/<numero>', methods=['GET'])
def get_solicitud_estado(numero):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT numero,fecha,estado,solicitante,urgencia,observaciones,numero_oc FROM solicitudes_compra WHERE numero=?", (numero.upper(),))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'No encontrada'}), 404
    cols = ['numero','fecha','estado','solicitante','urgencia','observaciones','numero_oc']
    sol = dict(zip(cols, row))
    for col in ['area','empresa','categoria','tipo','aprobado_por','fecha_aprobacion']:
        try:
            c.execute(f"SELECT {col} FROM solicitudes_compra WHERE numero=?", (numero.upper(),))
            r2 = c.fetchone()
            if r2: sol[col] = r2[0]
        except: pass
    c.execute("SELECT codigo_mp,nombre_mp,cantidad_g,unidad,valor_estimado FROM solicitudes_compra_items WHERE numero=?", (numero.upper(),))
    items = [dict(zip(['codigo_mp','nombre_mp','cantidad_g','unidad','valor_estimado'], r)) for r in c.fetchall()]
    conn.close()
    return jsonify({'solicitud': sol, 'items': items})

@app.route('/solicitudes')
def solicitudes_page():
    return Response(SOLICITUDES_HTML, mimetype='text/html')


@app.route('/api/solicitudes-compra/<numero>/estado', methods=['PATCH'])
def actualizar_estado_solicitud(numero):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.get_json() or {}
    nuevo = d.get('estado', 'Aprobada')
    numero_oc_param = d.get('numero_oc', '')
    obs = d.get('observaciones', '')
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("""UPDATE solicitudes_compra SET estado=?, aprobado_por=?, fecha_aprobacion=?
                 WHERE numero=?""",
              (nuevo, session.get('compras_user',''), datetime.now().isoformat(), numero.upper()))
    if numero_oc_param:
        cur.execute("UPDATE solicitudes_compra SET numero_oc=? WHERE numero=?", (numero_oc_param, numero.upper()))
    if nuevo == 'Rechazada' and obs:
        cur.execute("UPDATE solicitudes_compra SET observaciones=? WHERE numero=?", (obs, numero.upper()))
    conn.commit()
    oc_creada = ''
    if d.get('crear_oc'):
        cur.execute("SELECT codigo_mp, nombre_mp, cantidad_g, unidad FROM solicitudes_compra_items WHERE numero=?", (numero.upper(),))
        items_sol = cur.fetchall()
        proveedor_oc = d.get('proveedor', 'Por definir')
        cur.execute("SELECT COUNT(*) FROM ordenes_compra")
        n_oc = cur.fetchone()[0] + 1
        oc_num = f"OC-{datetime.now().year}-{n_oc:04d}"
        cur.execute("""INSERT INTO ordenes_compra (numero_oc, fecha, estado, proveedor, observaciones, creado_por)
                     VALUES (?,?,?,?,?,?)""",
                  (oc_num, datetime.now().isoformat(), 'Borrador', proveedor_oc,
                   f'Generado desde {numero.upper()}', session.get('compras_user','')))
        for it in items_sol:
            cur.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g) VALUES (?,?,?,?)",
                      (oc_num, it[0], it[1], it[2]))
        cur.execute("UPDATE solicitudes_compra SET numero_oc=? WHERE numero=?", (oc_num, numero.upper()))
        oc_creada = oc_num
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'estado': nuevo, 'numero_oc': oc_creada})

@app.route('/api/ordenes-compra/<numero_oc>/recibir', methods=['POST'])
def recibir_oc(numero_oc):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT estado, proveedor, categoria FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    oc_row = cur.fetchone()
    if not oc_row:
        conn.close(); return jsonify({'error': 'OC no encontrada'}), 404
    prov_nombre = oc_row[1] or ''
    categoria = oc_row[2] or 'MP'
    cur.execute("SELECT codigo_mp, nombre_mp, cantidad_g FROM ordenes_compra_items WHERE numero_oc=?", (numero_oc,))
    items_oc = cur.fetchall()
    fecha = datetime.now().isoformat()
    operador = session.get('compras_user', '')
    data2 = request.get_json(silent=True) or {}
    obs_r = data2.get('observaciones_recepcion', '')
    disc_r = 1 if data2.get('tiene_discrepancias') else 0
    items_r = data2.get('items_recepcion', [])
    receptor_nombre = data2.get('receptor_nombre', '') or operador
    # Build lookup dict for items_recepcion data keyed by codigo_mp
    rec_map = {ir.get('codigo_mp', ''): ir for ir in items_r}
    ingresos = 0
    es_parcial = False
    for item in items_oc:
        codigo, nombre, cantidad_pedida = item
        ir = rec_map.get(codigo, {})
        cant_recibida = float(ir.get('cantidad_recibida', 0) or cantidad_pedida)
        lote_num = ir.get('lote', '').strip()
        fv = ir.get('fecha_vencimiento', '').strip()
        estado_item = ir.get('estado', 'OK')
        notas_item = ir.get('notas', '')
        # Detectar recepcion parcial
        if cant_recibida < cantidad_pedida * 0.999:
            es_parcial = True
        # Solo registrar movimiento si hay algo recibido
        if cant_recibida > 0:
            if categoria == 'MEE':
                cur.execute("UPDATE maestro_mee SET stock_actual = stock_actual + ? WHERE codigo=?", (cant_recibida, codigo))
                cur.execute("INSERT INTO movimientos_mee (codigo_mee, tipo, cantidad, referencia, observaciones, operador, fecha) VALUES (?,?,?,?,?,?,?)",
                           (codigo, 'entrada', cant_recibida, numero_oc, f'Recepcion OC {numero_oc}', operador, fecha))
            else:
                cur.execute(
                    "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, "
                    "observaciones, proveedor, operador, lote, fecha_vencimiento, estado_lote, numero_oc) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (codigo, nombre, cant_recibida, 'Entrada', fecha,
                     f'Recepcion OC {numero_oc}' + (f' | {notas_item}' if notas_item else ''),
                     prov_nombre, operador, lote_num or None, fv or None, 'Cuarentena', numero_oc))
            ingresos += 1
        # Actualizar item OC
        try:
            cur.execute(
                "UPDATE ordenes_compra_items SET cantidad_recibida_g=?, estado_recepcion=?, notas_recepcion=?, lote_asignado=?"
                " WHERE numero_oc=? AND codigo_mp=?",
                (cant_recibida, estado_item, notas_item, lote_num, numero_oc, codigo))
        except Exception:
            pass
    # Estado final de la OC
    nuevo_estado = 'Parcial' if es_parcial else 'Recibida'
    try:
        cur.execute(
            "UPDATE ordenes_compra SET estado=?, fecha_recepcion=?,"
            " observaciones_recepcion=?, tiene_discrepancias=?, recibido_por=? WHERE numero_oc=?",
            (nuevo_estado, fecha, obs_r, disc_r, receptor_nombre, numero_oc))
    except Exception:
        cur.execute("UPDATE ordenes_compra SET estado=?, fecha_recepcion=? WHERE numero_oc=?", (nuevo_estado, fecha, numero_oc))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'numero_oc': numero_oc, 'ingresos': ingresos, 'estado': nuevo_estado, 'parcial': es_parcial})

# ============================================================
# Compras — Flujo de autorizacion y pago
# ============================================================

@app.route('/api/ordenes-compra/<numero_oc>/revisar', methods=['PATCH'])
def revisar_oc(numero_oc):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.get_json() or {}
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    sets = ["estado='Revisada'"]; params = []
    if d.get('proveedor'):
        sets.append('proveedor=?'); params.append(str(d['proveedor']))
    if d.get('valor_total') not in (None, '', 0):
        sets.append('valor_total=?'); params.append(float(d['valor_total'] or 0))
    if d.get('observaciones'):
        sets.append('observaciones=?'); params.append(str(d['observaciones']))
    params.append(numero_oc)
    cur.execute(f"UPDATE ordenes_compra SET {', '.join(sets)} WHERE numero_oc=?", params)
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'estado': 'Revisada'})

@app.route('/api/ordenes-compra/<numero_oc>/autorizar', methods=['PATCH'])
def autorizar_oc(numero_oc):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    usuario_actual = session.get('compras_user', '')
    if usuario_actual in CONTADORA_USERS:
        return jsonify({'error': 'Sin permiso para autorizar OCs'}), 403
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT estado FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    row = cur.fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'OC no encontrada'}), 404
    fecha_hoy = datetime.now().strftime('%Y%m%d')
    cur.execute("SELECT remision_code FROM ordenes_compra WHERE remision_code LIKE ? ORDER BY remision_code DESC LIMIT 1",
                (f'REM-ESP-{fecha_hoy}-%',))
    last = cur.fetchone()
    n = int(last[0].split('-')[-1]) + 1 if last and last[0] else 1
    remision_code = f'REM-ESP-{fecha_hoy}-{n:03d}'
    fecha_aut = datetime.now().isoformat()
    cur.execute("UPDATE ordenes_compra SET estado='Autorizada', remision_code=?, autorizado_por=?, fecha_autorizacion=? WHERE numero_oc=?",
                (remision_code, usuario_actual, fecha_aut, numero_oc))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'estado': 'Autorizada', 'remision_code': remision_code})

@app.route('/api/ordenes-compra/<numero_oc>/pagar', methods=['PATCH'])
def pagar_oc(numero_oc):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    usuario_actual = session.get('compras_user', '')
    if usuario_actual in CONTADORA_USERS:
        return jsonify({'error': 'Sin permiso para registrar pagos'}), 403
    d = request.get_json() or {}
    monto = float(d.get('monto', 0) or 0)
    medio = d.get('medio', 'Transferencia')
    obs = d.get('observaciones', '')
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT estado, categoria, proveedor, valor_total FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    row = cur.fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'OC no encontrada'}), 404
    categoria = row[1] or 'MP'
    proveedor = row[2] or ''
    if not monto: monto = float(row[3] or 0)
    cat_map = {'MPs':'MPs','MP':'MPs','Envase':'MEE','Insumos':'MEE','MEE':'MEE','Servicios':'Servicios','Analisis':'Servicios','Ánalisis':'Servicios','Acondicionamiento':'Servicios','Admin':'Administrativo','Nomina':'Administrativo','ADM':'Administrativo','Infraestructura':'Infraestructura','INF':'Infraestructura','CC':'Cuentas de Cobro'}
    cat_egreso = cat_map.get(categoria, 'Compras')
    fecha_pago = datetime.now().isoformat()
    cur.execute("UPDATE ordenes_compra SET estado='Pagada', pagado_por=?, fecha_pago=? WHERE numero_oc=?",
                (usuario_actual, fecha_pago, numero_oc))
    try:
        cur.execute("INSERT INTO flujo_egresos (fecha, empresa, concepto, categoria, monto, periodo, fuente, referencia, creado_por, observaciones) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (fecha_pago, 'Espagiria', f'Pago OC {numero_oc} - {proveedor}',
                    cat_egreso, monto, datetime.now().strftime('%Y-%m'),
                    'compras', numero_oc, usuario_actual, f'{medio}. {obs}'))
    except Exception:
        pass
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'estado': 'Pagada', 'monto': monto})

@app.route('/api/compras/buscar-remision/<remision_code>')
def buscar_remision(remision_code):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT * FROM ordenes_compra WHERE remision_code=?", (remision_code,))
    oc_row = cur.fetchone()
    oc_cols = [d[0] for d in cur.description] if cur.description else []
    if not oc_row:
        conn.close(); return jsonify({'error': 'No encontrado'}), 404
    oc = dict(zip(oc_cols, oc_row))
    cur.execute("SELECT * FROM ordenes_compra_items WHERE numero_oc=?", (oc['numero_oc'],))
    items = cur.fetchall()
    conn.close()
    return jsonify({'oc': oc, 'items': items})



# ════════════════════════════════════════════
# MEE — Materiales de Envase & Empaque
# ════════════════════════════════════════════

@app.route('/api/mee', methods=['GET','POST'])
def handle_mee():
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    if request.method == 'POST':
        d = request.get_json()
        if not d.get('codigo') or not d.get('descripcion'):
            conn.close(); return jsonify({'error':'codigo y descripcion requeridos'}), 400
        try:
            cur.execute("""INSERT INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (d['codigo'].upper().strip(), d['descripcion'].strip(),
                 d.get('categoria','Otro'), d.get('proveedor',''), d.get('fabricante',''),
                 'Activo', float(d.get('stock_actual',2000)), float(d.get('stock_minimo',1000)),
                 'und', datetime.now().isoformat()))
            conn.commit(); conn.close()
            return jsonify({'message':f"MEE '{d['codigo']}' creado"}), 201
        except Exception as e:
            conn.close(); return jsonify({'error':str(e)}), 400
    # GET
    cat = request.args.get('cat','')
    q   = request.args.get('q','')
    lim = int(request.args.get('limit',500))
    sql = "SELECT codigo,descripcion,categoria,proveedor,stock_actual,stock_minimo,estado FROM maestro_mee WHERE estado='Activo'"
    params = []
    if cat: sql += " AND categoria=?"; params.append(cat)
    if q:   sql += " AND (codigo LIKE ? OR descripcion LIKE ?)"; params += [f'%{q}%',f'%{q}%']
    sql += " ORDER BY categoria,codigo LIMIT ?"
    params.append(lim)
    cur.execute(sql, params)
    cols=['codigo','descripcion','categoria','proveedor','stock_actual','stock_minimo','estado']
    items=[dict(zip(cols,r)) for r in cur.fetchall()]
    conn.close()
    return jsonify({'items':items})

@app.route('/api/mee/<codigo>', methods=['GET','PUT'])
def handle_mee_item(codigo):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    if request.method == 'PUT':
        d = request.get_json()
        fields=[]; vals=[]
        for f in ['descripcion','categoria','proveedor','stock_minimo','estado']:
            if f in d: fields.append(f'{f}=?'); vals.append(d[f])
        if not fields: conn.close(); return jsonify({'error':'nada que actualizar'}), 400
        vals.append(codigo)
        cur.execute(f"UPDATE maestro_mee SET {','.join(fields)} WHERE codigo=?", vals)
        conn.commit(); conn.close()
        return jsonify({'message':'actualizado'})
    cur.execute("SELECT * FROM maestro_mee WHERE codigo=?", (codigo,))
    row=cur.fetchone(); conn.close()
    if not row: return jsonify({'error':'no encontrado'}), 404
    cols=[d[0] for d in cur.description]
    return jsonify(dict(zip(cols,row)))

@app.route('/api/mee/<codigo>/ajuste', methods=['POST'])
def ajuste_mee(codigo):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    d = request.get_json()
    nuevo = float(d.get('nuevo_stock',0))
    obs = d.get('observaciones','Ajuste manual')
    oper = d.get('operador','Sistema')
    cur.execute("SELECT stock_actual FROM maestro_mee WHERE codigo=?", (codigo,))
    row=cur.fetchone()
    if not row: conn.close(); return jsonify({'error':'MEE no encontrado'}), 404
    anterior=row[0]
    diff=nuevo-anterior
    cur.execute("UPDATE maestro_mee SET stock_actual=? WHERE codigo=?", (nuevo,codigo))
    cur.execute("INSERT INTO movimientos_mee (codigo_mee,tipo,cantidad,referencia,observaciones,operador,fecha) VALUES (?,?,?,?,?,?,?)",
                (codigo,'ajuste',diff,'ajuste_manual',obs,oper,datetime.now().isoformat()))
    conn.commit(); conn.close()
    return jsonify({'ok':True,'nuevo_stock':nuevo})

@app.route('/api/movimientos-mee', methods=['GET','POST'])
def handle_movimientos_mee():
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    if request.method == 'POST':
        d = request.get_json()
        cod  = d.get('codigo_mee')
        tipo = d.get('tipo','entrada')
        cant = float(d.get('cantidad',0))
        ref  = d.get('referencia','')
        obs  = d.get('observaciones','')
        oper = d.get('operador','')
        if not cod or cant<=0: conn.close(); return jsonify({'error':'datos invalidos'}), 400
        cur.execute("SELECT stock_actual FROM maestro_mee WHERE codigo=?", (cod,))
        row=cur.fetchone()
        if not row: conn.close(); return jsonify({'error':'MEE no encontrado'}), 404
        delta = cant if tipo=='entrada' else -cant
        nuevo = row[0]+delta
        if nuevo<0: conn.close(); return jsonify({'error':f'Stock insuficiente (actual: {row[0]})'}), 400
        cur.execute("UPDATE maestro_mee SET stock_actual=? WHERE codigo=?", (nuevo,cod))
        cur.execute("INSERT INTO movimientos_mee (codigo_mee,tipo,cantidad,referencia,observaciones,operador,fecha) VALUES (?,?,?,?,?,?,?)",
                    (cod,tipo,cant,ref,obs,oper,datetime.now().isoformat()))
        conn.commit(); conn.close()
        return jsonify({'ok':True,'nuevo_stock':nuevo}), 201
    # GET con filtros
    codigo = request.args.get('codigo','')
    tipo   = request.args.get('tipo','')
    limit  = int(request.args.get('limit',50))
    sql = """SELECT m.id,m.codigo_mee,mm.descripcion,m.tipo,m.cantidad,m.referencia,m.observaciones,m.operador,m.fecha
             FROM movimientos_mee m LEFT JOIN maestro_mee mm ON m.codigo_mee=mm.codigo WHERE 1=1"""
    params=[]
    if codigo: sql+=" AND m.codigo_mee=?"; params.append(codigo)
    if tipo:   sql+=" AND m.tipo=?"; params.append(tipo)
    sql+=" ORDER BY m.fecha DESC LIMIT ?"; params.append(limit)
    cur.execute(sql, params)
    cols=['id','codigo_mee','descripcion','tipo','cantidad','referencia','observaciones','operador','fecha']
    rows=[dict(zip(cols,r)) for r in cur.fetchall()]
    conn.close()
    return jsonify({'movimientos':rows})

@app.route('/api/movimientos-mee/lote', methods=['POST'])
def movimientos_mee_lote():
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    d = request.get_json()
    movs = d.get('movimientos',[])
    oper = d.get('operador','')
    ref  = d.get('referencia','')
    errores=[]
    for m in movs:
        cod=m.get('codigo_mee'); cant=float(m.get('cantidad',0))
        if not cod or cant<=0: continue
        cur.execute("SELECT stock_actual FROM maestro_mee WHERE codigo=?", (cod,))
        row=cur.fetchone()
        if not row: errores.append(f'{cod} no encontrado'); continue
        nuevo=row[0]-cant
        if nuevo<0: nuevo=0
        cur.execute("UPDATE maestro_mee SET stock_actual=? WHERE codigo=?", (nuevo,cod))
        cur.execute("INSERT INTO movimientos_mee (codigo_mee,tipo,cantidad,referencia,observaciones,operador,fecha) VALUES (?,?,?,?,?,?,?)",
                    (cod,'salida',cant,ref,'Consumo produccion',oper,datetime.now().isoformat()))
    conn.commit(); conn.close()
    if errores: return jsonify({'ok':True,'advertencias':errores})
    return jsonify({'ok':True})

@app.route('/api/alertas-mee', methods=['GET'])
def alertas_mee():
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("""SELECT codigo,descripcion,categoria,proveedor,stock_actual,stock_minimo
                   FROM maestro_mee WHERE estado='Activo' AND stock_actual < stock_minimo
                   ORDER BY (stock_actual - stock_minimo) ASC""")
    cols=['codigo','descripcion','categoria','proveedor','stock_actual','stock_minimo']
    alertas=[dict(zip(cols,r)) for r in cur.fetchall()]
    conn.close()
    return jsonify({'alertas':alertas,'total':len(alertas)})

# ─── MÓDULO CLIENTES — Rutas ──────────────────────────────────
@app.route('/clientes')
def clientes_page():
    if 'compras_user' not in session:
        return redirect(url_for('login'))
    return Response(CLIENTES_HTML, mimetype='text/html')

@app.route('/api/clientes', methods=['GET','POST'])
def handle_clientes():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('nombre'):
            conn.close(); return jsonify({'error': 'Nombre requerido'}), 400
        c.execute("SELECT COUNT(*) FROM clientes"); n = (c.fetchone()[0] or 0) + 1
        codigo = d.get('codigo') or f"CLI-{n:03d}"
        try:
            c.execute("""INSERT INTO clientes
                         (codigo,nombre,empresa,tipo,contacto,email,telefono,nit,
                          condiciones_pago,descuento_pct,activo,fecha_creacion,observaciones)
                         VALUES (?,?,?,?,?,?,?,?,?,?,1,datetime('now'),?)""",
                      (codigo, d['nombre'], d.get('empresa','ANIMUS'), d.get('tipo','Distribuidor'),
                       d.get('contacto',''), d.get('email',''), d.get('telefono',''),
                       d.get('nit',''), d.get('condiciones_pago','30 dias'),
                       float(d.get('descuento_pct',0)), d.get('observaciones','')))
            conn.commit(); conn.close()
            return jsonify({'message': f"Cliente creado", 'codigo': codigo}), 201
        except Exception as e:
            conn.close(); return jsonify({'error': str(e)}), 400
    c.execute("SELECT id,codigo,nombre,empresa,tipo,contacto,email,telefono,condiciones_pago,descuento_pct,activo,fecha_creacion FROM clientes WHERE activo=1 ORDER BY nombre")
    cols = ['id','codigo','nombre','empresa','tipo','contacto','email','telefono','condiciones_pago','descuento_pct','activo','fecha_creacion']
    clientes = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close(); return jsonify({'clientes': clientes})

@app.route('/api/clientes/<int:cid>', methods=['GET','PUT'])
def handle_cliente_detalle(cid):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'PUT':
        d = request.json or {}
        campos = ['nombre','empresa','tipo','contacto','email','telefono','nit','condiciones_pago','descuento_pct','observaciones','activo']
        sets = []; vals = []
        for campo in campos:
            if campo in d: sets.append(f"{campo}=?"); vals.append(d[campo])
        if sets:
            vals.append(cid)
            c.execute(f"UPDATE clientes SET {','.join(sets)} WHERE id=?", vals)
            conn.commit()
        conn.close(); return jsonify({'message': 'Cliente actualizado'})
    c.execute("SELECT id,codigo,nombre,empresa,tipo,contacto,email,telefono,nit,condiciones_pago,descuento_pct,activo,fecha_creacion,observaciones FROM clientes WHERE id=?", (cid,))
    row = c.fetchone(); conn.close()
    if not row: return jsonify({'error': 'No encontrado'}), 404
    cols = ['id','codigo','nombre','empresa','tipo','contacto','email','telefono','nit','condiciones_pago','descuento_pct','activo','fecha_creacion','observaciones']
    return jsonify({'cliente': dict(zip(cols, row))})

@app.route('/api/clientes/<int:cid>/historial')
def handle_cliente_historial(cid):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT numero,fecha,estado,valor_total,fecha_despacho FROM pedidos WHERE cliente_id=? ORDER BY fecha DESC LIMIT 50", (cid,))
    cols = ['numero','fecha','estado','valor_total','fecha_despacho']
    pedidos = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close(); return jsonify({'pedidos': pedidos})

@app.route('/api/clientes/<int:cid>/stats')
def handle_cliente_stats(cid):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT COUNT(*), COALESCE(SUM(valor_total),0), MAX(fecha) FROM pedidos WHERE cliente_id=?", (cid,))
    row = c.fetchone(); conn.close()
    return jsonify({'total_pedidos': row[0], 'valor_total': row[1], 'ultimo_pedido': row[2]})

@app.route('/api/clientes/alertas-recompra')
def clientes_alertas_recompra():
    """Clientes con >N dias sin pedido — churn detection."""
    umbral = int(request.args.get('dias', 75))
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT cl.id, cl.nombre, cl.tipo, cl.email, cl.telefono,
                        MAX(p.fecha) as ultimo_pedido,
                        COUNT(p.numero) as total_pedidos,
                        COALESCE(SUM(p.valor_total),0) as valor_total
                 FROM clientes cl
                 LEFT JOIN pedidos p ON p.cliente_id = cl.id
                 WHERE cl.activo=1
                 GROUP BY cl.id, cl.nombre
                 HAVING ultimo_pedido IS NOT NULL
                 ORDER BY ultimo_pedido ASC""")
    hoy = datetime.now()
    resultado = []
    for r in c.fetchall():
        cid, nombre, tipo, email, tel, ult, tot_ped, val = r
        try:
            dias = (hoy - datetime.fromisoformat(ult[:19])).days
        except Exception:
            dias = 0
        if dias >= umbral:
            resultado.append({
                'id': cid, 'nombre': nombre, 'tipo': tipo,
                'email': email, 'telefono': tel,
                'ultimo_pedido': (ult or '')[:10], 'dias_sin_pedido': dias,
                'total_pedidos': tot_ped, 'valor_total': val,
                'nivel': 'critico' if dias >= 120 else 'atencion'
            })
    conn.close()
    return jsonify({'alertas': resultado, 'umbral_dias': umbral})


@app.route('/api/clientes/<int:cid>/ficha360')
def cliente_ficha_360(cid):
    """Cliente 360: datos + stats + historial pedidos recientes + items."""
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT id, codigo, nombre, empresa, tipo, contacto, email,
                        telefono, nit, condiciones_pago, descuento_pct, observaciones, fecha_creacion
                 FROM clientes WHERE id=? AND activo=1""", (cid,))
    row = c.fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'Cliente no encontrado'}), 404
    cols_cli = ['id','codigo','nombre','empresa','tipo','contacto','email',
                'telefono','nit','condiciones_pago','descuento_pct','observaciones','fecha_creacion']
    cliente = dict(zip(cols_cli, row))
    # Stats
    c.execute("SELECT COUNT(*), COALESCE(SUM(valor_total),0), MAX(fecha), MIN(fecha) FROM pedidos WHERE cliente_id=?", (cid,))
    s = c.fetchone()
    total_ped, valor_total, ultimo_ped, primer_ped = s[0] or 0, s[1] or 0, s[2], s[3]
    hoy = datetime.now()
    dias_sin_pedido = None
    if ultimo_ped:
        try: dias_sin_pedido = (hoy - datetime.fromisoformat(ultimo_ped[:19])).days
        except Exception: pass
    # Ticket promedio
    ticket_prom = round(valor_total / total_ped, 0) if total_ped > 0 else 0
    # Pedidos recientes (last 10)
    c.execute("""SELECT numero, fecha, estado, valor_total, fecha_entrega_est, fecha_despacho
                 FROM pedidos WHERE cliente_id=? ORDER BY fecha DESC LIMIT 10""", (cid,))
    ped_cols = ['numero','fecha','estado','valor_total','fecha_entrega_est','fecha_despacho']
    pedidos_recientes = [dict(zip(ped_cols, r)) for r in c.fetchall()]
    # Top SKUs comprados
    c.execute("""SELECT pi.sku, pi.descripcion, SUM(pi.cantidad) as tot_uds, COUNT(DISTINCT p.numero) as en_pedidos
                 FROM pedidos_items pi JOIN pedidos p ON pi.numero_pedido=p.numero
                 WHERE p.cliente_id=?
                 GROUP BY pi.sku, pi.descripcion
                 ORDER BY tot_uds DESC LIMIT 10""", (cid,))
    top_skus = [{'sku':r[0],'descripcion':r[1],'unidades':r[2],'pedidos':r[3]} for r in c.fetchall()]
    conn.close()
    return jsonify({
        'cliente': cliente,
        'stats': {
            'total_pedidos': total_ped, 'valor_total': valor_total,
            'ticket_promedio': ticket_prom, 'ultimo_pedido': (ultimo_ped or '')[:10],
            'primer_pedido': (primer_ped or '')[:10], 'dias_sin_pedido': dias_sin_pedido
        },
        'pedidos_recientes': pedidos_recientes,
        'top_skus': top_skus
    })


@app.route('/api/pedidos', methods=['GET','POST'])
def handle_pedidos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('cliente_id'):
            conn.close(); return jsonify({'error': 'cliente_id requerido'}), 400
        c.execute("SELECT COUNT(*) FROM pedidos"); n = (c.fetchone()[0] or 0) + 1
        numero = f"PED-{datetime.now().strftime('%Y')}-{n:04d}"
        valor_total = sum(float(it.get('subtotal', float(it.get('cantidad',0))*float(it.get('precio_unitario',0)))) for it in (d.get('items') or []))
        c.execute("""INSERT INTO pedidos (numero,cliente_id,fecha,fecha_entrega_est,estado,empresa,valor_total,observaciones,creado_por)
                     VALUES (?,?,datetime('now'),?,?,?,?,?,?)""",
                  (numero, d['cliente_id'], d.get('fecha_entrega_est',''), d.get('estado','Confirmado'),
                   d.get('empresa','ANIMUS'), valor_total, d.get('observaciones',''), session.get('compras_user','sistema')))
        for it in (d.get('items') or []):
            subtotal = float(it.get('subtotal', float(it.get('cantidad',0))*float(it.get('precio_unitario',0))))
            c.execute("INSERT INTO pedidos_items (numero_pedido,sku,descripcion,cantidad,precio_unitario,subtotal) VALUES (?,?,?,?,?,?)",
                      (numero, it.get('sku',''), it.get('descripcion',''), int(it.get('cantidad',0)), float(it.get('precio_unitario',0)), subtotal))
        conn.commit(); conn.close()
        return jsonify({'message': f'Pedido {numero} creado', 'numero': numero}), 201
    estado = request.args.get('estado')
    q = "SELECT p.numero,c.nombre,p.fecha,p.estado,p.valor_total,p.empresa,p.fecha_entrega_est FROM pedidos p LEFT JOIN clientes c ON p.cliente_id=c.id"
    params = []
    if estado: q += " WHERE p.estado=?"; params.append(estado)
    q += " ORDER BY p.fecha DESC LIMIT 100"
    c.execute(q, params)
    cols = ['numero','cliente','fecha','estado','valor_total','empresa','fecha_entrega_est']
    rows = c.fetchall(); conn.close()
    return jsonify({'pedidos': [dict(zip(cols, r)) for r in rows]})

@app.route('/api/pedidos/<numero>', methods=['GET','PATCH'])
def handle_pedido_detalle(numero):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'PATCH':
        d = request.json or {}
        if d.get('estado'):
            c.execute("UPDATE pedidos SET estado=? WHERE numero=?", (d['estado'], numero))
            conn.commit()
        conn.close(); return jsonify({'message': f'Pedido {numero} actualizado'})
    c.execute("SELECT p.*,cl.nombre as cliente_nombre FROM pedidos p LEFT JOIN clientes cl ON p.cliente_id=cl.id WHERE p.numero=?", (numero,))
    row = c.fetchone()
    if not row: conn.close(); return jsonify({'error': 'No encontrado'}), 404
    cols = [d[0] for d in c.description]
    pedido = dict(zip(cols, row))
    c.execute("SELECT sku,descripcion,cantidad,precio_unitario,subtotal,lote_pt FROM pedidos_items WHERE numero_pedido=?", (numero,))
    items = [dict(zip(['sku','descripcion','cantidad','precio_unitario','subtotal','lote_pt'], r)) for r in c.fetchall()]
    conn.close(); return jsonify({'pedido': pedido, 'items': items})

@app.route('/api/stock-pt', methods=['GET','POST'])
def handle_stock_pt():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('sku'):
            conn.close(); return jsonify({'error': 'SKU requerido'}), 400
        unidades = int(d.get('unidades_inicial', d.get('unidades_disponible', 0)))
        c.execute("""INSERT INTO stock_pt (sku,descripcion,lote_produccion,fecha_produccion,unidades_inicial,unidades_disponible,precio_base,empresa,estado,observaciones)
                     VALUES (?,?,?,datetime('now'),?,?,?,?,?,?)""",
                  (d['sku'], d.get('descripcion',''), d.get('lote_produccion',''), unidades, unidades,
                   float(d.get('precio_base',0)), d.get('empresa','ANIMUS'), 'Disponible', d.get('observaciones','')))
        conn.commit(); conn.close()
        return jsonify({'message': f"Stock PT registrado: {d['sku']} — {unidades} uds"}), 201
    c.execute("SELECT sku,descripcion,SUM(unidades_disponible) as disponible,SUM(unidades_inicial) as inicial,MAX(fecha_produccion) as ultima_prod,empresa,precio_base FROM stock_pt WHERE estado='Disponible' GROUP BY sku,empresa ORDER BY sku")
    cols = ['sku','descripcion','disponible','inicial','ultima_prod','empresa','precio_base']
    rows = c.fetchall()
    conn.close()
    return jsonify({'stock_pt': [dict(zip(cols, r)) for r in rows]})

@app.route('/api/despachos', methods=['GET','POST'])
def handle_despachos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        c.execute("SELECT COUNT(*) FROM despachos"); n = (c.fetchone()[0] or 0) + 1
        numero = f"DSP-{datetime.now().strftime('%Y')}-{n:04d}"
        c.execute("INSERT INTO despachos (numero,numero_pedido,cliente_id,fecha,operador,observaciones,estado) VALUES (?,?,?,datetime('now'),?,?,?)",
                  (numero, d.get('numero_pedido',''), d.get('cliente_id'), session.get('compras_user','sistema'), d.get('observaciones',''), 'Completado'))
        for it in (d.get('items') or []):
            c.execute("INSERT INTO despachos_items (numero_despacho,sku,descripcion,lote_pt,cantidad,precio_unitario) VALUES (?,?,?,?,?,?)",
                      (numero, it.get('sku',''), it.get('descripcion',''), it.get('lote_pt',''), int(it.get('cantidad',0)), float(it.get('precio_unitario',0))))
            c.execute("UPDATE stock_pt SET unidades_disponible=MAX(0,unidades_disponible-?) WHERE sku=? AND unidades_disponible>0 ORDER BY fecha_produccion ASC LIMIT 1",
                      (int(it.get('cantidad',0)), it.get('sku','')))
        if d.get('numero_pedido'):
            c.execute("UPDATE pedidos SET estado='Despachado',fecha_despacho=datetime('now') WHERE numero=?", (d['numero_pedido'],))
        conn.commit(); conn.close()
        return jsonify({'message': f'Despacho {numero} registrado', 'numero': numero}), 201
    c.execute("SELECT d.numero,cl.nombre as cliente,d.fecha,d.numero_pedido,d.estado,d.operador FROM despachos d LEFT JOIN clientes cl ON d.cliente_id=cl.id ORDER BY d.fecha DESC LIMIT 100")
    cols = ['numero','cliente','fecha','numero_pedido','estado','operador']
    rows = c.fetchall(); conn.close()
    return jsonify({'despachos': [dict(zip(cols, r)) for r in rows]})

# ─── MÓDULO GERENCIA — Rutas ──────────────────────────────────
@app.route('/gerencia')
def gerencia_page():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return redirect(url_for('login'))
    return Response(HUB_HTML, mimetype='text/html')

@app.route('/gerencia-financiero')
def gerencia_financiero_page():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return redirect(url_for('login'))
    return Response(GERENCIA_HTML, mimetype='text/html')

@app.route('/api/gerencia/kpis')
def gerencia_kpis():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM maestro_mps m LEFT JOIN (SELECT material_id,SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as s FROM movimientos GROUP BY material_id) st ON m.codigo_mp=st.material_id WHERE m.activo=1 AND m.stock_minimo>0 AND COALESCE(st.s,0)<m.stock_minimo")
    mps_bajo_minimo = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM movimientos WHERE tipo='Entrada' AND fecha_vencimiento IS NOT NULL AND fecha_vencimiento!='' AND fecha_vencimiento<=date('now','+30 days') AND fecha_vencimiento>=date('now')")
    lotes_vence_30 = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM movimientos WHERE tipo='Entrada' AND fecha_vencimiento IS NOT NULL AND fecha_vencimiento!='' AND fecha_vencimiento<=date('now','+60 days') AND fecha_vencimiento>=date('now','+30 days')")
    lotes_vence_60 = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM producciones WHERE fecha>=date('now','start of month')")
    prod_mes = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM ordenes_compra WHERE estado IN ('Pendiente','Aprobada','Enviada')")
    ocs_pendientes = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(unidades_disponible),0) FROM stock_pt WHERE estado='Disponible'")
    uds_pt = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM pedidos WHERE estado IN ('Confirmado','En preparacion')")
    pedidos_activos = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(DISTINCT sku) FROM stock_pt WHERE unidades_disponible>0 AND estado='Disponible'")
    skus_stock = c.fetchone()[0] or 0
    c.execute("SELECT MAX(fecha) FROM pedidos WHERE cliente_id=(SELECT id FROM clientes WHERE codigo='CLI-002' LIMIT 1)")
    ult_fm = c.fetchone()[0]; dias_fm = None
    if ult_fm:
        from datetime import date as _d
        try: dt = datetime.fromisoformat(ult_fm[:10]); dias_fm = (_d.today() - dt.date()).days
        except: pass
    c.execute("SELECT periodo,saldo_caja,ingresos_animus,ingresos_maquila,notas,fecha FROM gerencia_inputs ORDER BY periodo DESC LIMIT 1")
    row = c.fetchone()
    cols_inp = ['periodo','saldo_caja','ingresos_animus','ingresos_maquila','notas','fecha']
    inputs_manuales = dict(zip(cols_inp, row)) if row else {}
    conn.close()
    semaforos = {
        'mps': 'rojo' if mps_bajo_minimo > 5 else ('amarillo' if mps_bajo_minimo > 0 else 'verde'),
        'vencimientos': 'rojo' if lotes_vence_30 > 0 else ('amarillo' if lotes_vence_60 > 0 else 'verde'),
        'pt': 'rojo' if uds_pt < 100 else ('amarillo' if uds_pt < 500 else 'verde'),
        'pedidos': 'amarillo' if pedidos_activos > 0 else 'verde',
    }
    return jsonify({'espagiria': {'mps_bajo_minimo': mps_bajo_minimo, 'lotes_vence_30': lotes_vence_30,
                                   'lotes_vence_60': lotes_vence_60, 'prod_mes': prod_mes, 'ocs_pendientes': ocs_pendientes},
                    'animus': {'uds_pt': uds_pt, 'pedidos_activos': pedidos_activos, 'skus_stock': skus_stock, 'dias_desde_fm': dias_fm},
                    'inputs_manuales': inputs_manuales, 'semaforos': semaforos})

@app.route('/api/gerencia/flujo-operacional')
def gerencia_flujo_operacional():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    from datetime import date
    today = date.today()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # OCs en tránsito (Autorizada, sin recepción)
    c.execute("""SELECT oc.numero_oc, oc.proveedor, oc.fecha, oc.valor_total
                 FROM ordenes_compra oc
                 WHERE oc.estado = 'Autorizada'
                 AND (oc.fecha_recepcion IS NULL OR oc.fecha_recepcion = '')
                 ORDER BY oc.fecha ASC LIMIT 20""")
    oc_cols = ['numero_oc','proveedor','fecha','valor_total']
    ocs_transito = []
    for r in c.fetchall():
        row = dict(zip(oc_cols, r))
        try:
            fd = date.fromisoformat(str(r[2])[:10])
            row['dias_transito'] = (today - fd).days
        except Exception:
            row['dias_transito'] = 0
        ocs_transito.append(row)
    # Recepciones con discrepancias
    c.execute("""SELECT numero_oc, proveedor, fecha_recepcion
                 FROM ordenes_compra
                 WHERE tiene_discrepancias = 1
                 ORDER BY fecha_recepcion DESC LIMIT 10""")
    recepciones_disc = [{'numero_oc': r[0], 'proveedor': r[1], 'fecha': r[2]} for r in c.fetchall()]
    # Pedidos listos para despachar
    c.execute("""SELECT p.numero, cl.nombre as cliente, p.fecha, p.valor_total, p.estado
                 FROM pedidos p LEFT JOIN clientes cl ON p.cliente_id=cl.id
                 WHERE p.estado IN ('Confirmado','En preparacion','En Produccion','Aprobado','Listo')
                 ORDER BY p.fecha ASC LIMIT 20""")
    ped_cols = ['numero','cliente','fecha','valor_total','estado']
    pedidos_listos = [dict(zip(ped_cols, r)) for r in c.fetchall()]
    # Despachos recientes (last 10)
    c.execute("""SELECT d.numero, cl.nombre as cliente, d.fecha, d.numero_pedido, d.estado
                 FROM despachos d LEFT JOIN clientes cl ON d.cliente_id=cl.id
                 ORDER BY d.fecha DESC LIMIT 10""")
    dsp_cols = ['numero','cliente','fecha','numero_pedido','estado']
    despachos_recientes = [dict(zip(dsp_cols, r)) for r in c.fetchall()]
    conn.close()
    return jsonify({
        'ocs_transito': ocs_transito,
        'recepciones_disc': recepciones_disc,
        'pedidos_listos': pedidos_listos,
        'despachos_recientes': despachos_recientes
    })

@app.route('/api/admin/security-log')
def admin_security_log():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'Solo admins'}), 401
    limit  = min(int(request.args.get('limit', 200)), 500)
    event  = request.args.get('event', '')
    conn   = sqlite3.connect(DB_PATH); c = conn.cursor()
    if event:
        c.execute('SELECT * FROM security_events WHERE event=? ORDER BY id DESC LIMIT ?', (event, limit))
    else:
        c.execute('SELECT * FROM security_events ORDER BY id DESC LIMIT ?', (limit,))
    cols = ['id','ts','event','username','ip','user_agent','details']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    # Summary counts
    c.execute('SELECT event, COUNT(*) FROM security_events GROUP BY event')
    summary = {r[0]: r[1] for r in c.fetchall()}
    conn.close()
    return jsonify({'events': rows, 'summary': summary})

@app.route('/api/admin/generate-hash', methods=['POST'])
def admin_generate_hash():
    """Utility: generate a PBKDF2 hash for a plaintext password.
    Use this to pre-hash passwords before storing them in env vars.
    POST {password: 'xxx'} -> {hash: 'pbkdf2:...'}
    """
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'Solo admins'}), 401
    d = request.get_json() or {}
    pw = d.get('password', '')
    if not pw:
        return jsonify({'error': 'Falta password'}), 400
    from werkzeug.security import generate_password_hash
    h = generate_password_hash(pw, method='pbkdf2:sha256', salt_length=16)
    return jsonify({'hash': h, 'note': 'Guarda este hash en la env var correspondiente'})

@app.route('/api/gerencia/dashboard-extra')
def gerencia_dashboard_extra():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    from datetime import date, timedelta
    today    = date.today()
    mes_str  = today.strftime('%Y-%m')
    year_str = today.strftime('%Y')
    cutoff7  = (today - timedelta(days=7)).isoformat()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()

    # Ingresos del mes desde transacciones reales
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM pedidos "
              "WHERE fecha LIKE ? AND estado NOT IN ('Cancelado')"
              " AND (empresa='ANIMUS' OR empresa IS NULL OR empresa='')",
              (mes_str+'%',))
    ing_animus = c.fetchone()[0] or 0
    try:
        c.execute("SELECT COALESCE(SUM(precio_lote),0) FROM maquila_ordenes "
                  "WHERE fecha_orden LIKE ? AND estado NOT IN ('Cotizacion','Cancelada')",
                  (mes_str+'%',))
        ing_maquila = c.fetchone()[0] or 0
    except Exception:
        ing_maquila = 0
    ingresos_mes = {'animus': ing_animus, 'maquila': ing_maquila, 'total': ing_animus + ing_maquila}

    # AR — cuentas por cobrar
    c.execute("SELECT COALESCE(SUM(valor_total),0), COUNT(*) FROM pedidos "
              "WHERE estado NOT IN ('Cancelado','Despachado') AND valor_total > 0")
    ar_row = c.fetchone()
    ar_total, ar_count = (ar_row[0] or 0), (ar_row[1] or 0)
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM pedidos "
              "WHERE estado NOT IN ('Cancelado','Despachado') "
              "AND valor_total > 0 AND fecha <= ?",
              ((today - timedelta(days=30)).isoformat(),))
    ar_v30 = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM pedidos "
              "WHERE estado NOT IN ('Cancelado','Despachado') "
              "AND valor_total > 0 AND fecha <= ?",
              ((today - timedelta(days=60)).isoformat(),))
    ar_v60 = c.fetchone()[0] or 0
    ar = {'total': ar_total, 'count': ar_count, 'vencido_30': ar_v30, 'vencido_60': ar_v60}

    # AP — cuentas por pagar
    c.execute("SELECT COALESCE(SUM(valor_total),0), COUNT(*) FROM ordenes_compra "
              "WHERE estado IN ('Autorizada','Recibida','Parcial') "
              "AND (pagado_por IS NULL OR pagado_por='')")
    ap_row = c.fetchone()
    ap_total, ap_count = (ap_row[0] or 0), (ap_row[1] or 0)
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM ordenes_compra "
              "WHERE estado IN ('Autorizada','Recibida','Parcial') "
              "AND (pagado_por IS NULL OR pagado_por='') AND fecha <= ?",
              ((today - timedelta(days=30)).isoformat(),))
    ap_v30 = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM ordenes_compra "
              "WHERE estado IN ('Autorizada','Recibida','Parcial') "
              "AND (pagado_por IS NULL OR pagado_por='') AND fecha <= ?",
              ((today - timedelta(days=60)).isoformat(),))
    ap_v60 = c.fetchone()[0] or 0
    ap = {'total': ap_total, 'count': ap_count, 'vencido_30': ap_v30, 'vencido_60': ap_v60}

    # Maquila pipeline activo
    try:
        c.execute("SELECT numero, cliente_nombre, producto, precio_lote, estado "
                  "FROM maquila_ordenes "
                  "WHERE estado NOT IN ('Cotizacion','Cancelada','Entregada') "
                  "ORDER BY fecha_orden DESC LIMIT 10")
        maquila_pipeline = [{'numero': r[0], 'cliente_nombre': r[1],
                              'producto': r[2], 'precio_lote': r[3],
                              'estado': r[4]} for r in c.fetchall()]
    except Exception:
        maquila_pipeline = []

    # Stock critico — MPs con stock < stock_minimo
    c.execute("""
        SELECT m.codigo_mp,
               COALESCE(m.nombre_comercial, m.nombre_inci,'') as nombre,
               m.stock_minimo,
               COALESCE(SUM(CASE WHEN mv.tipo='Entrada' THEN mv.cantidad
                                 WHEN mv.tipo='Salida'  THEN -mv.cantidad
                                 ELSE 0 END), 0) as stock_actual
        FROM maestro_mps m
        LEFT JOIN movimientos mv ON m.codigo_mp = mv.material_id
        WHERE m.activo=1 AND m.stock_minimo > 0
        GROUP BY m.codigo_mp
        HAVING stock_actual < m.stock_minimo
        ORDER BY (stock_actual / m.stock_minimo) ASC
        LIMIT 15
    """)
    stock_critico = [{'codigo_mp': r[0], 'nombre': r[1],
                       'stock_minimo': r[2], 'stock_actual': max(r[3], 0)}
                     for r in c.fetchall()]

    # SGSST — proximos vencimientos (60 dias)
    cutoff_sgsst = (today + timedelta(days=60)).isoformat()
    try:
        c.execute("""
            SELECT descripcion, proximo_vencimiento, responsable, estado
            FROM sgsst_items
            WHERE proximo_vencimiento IS NOT NULL
              AND proximo_vencimiento != ''
              AND proximo_vencimiento <= ?
              AND estado != 'Cumplido'
            ORDER BY proximo_vencimiento ASC LIMIT 8
        """, (cutoff_sgsst,))
        sgsst_rows = c.fetchall()
        sgsst_proximos = []
        for r in sgsst_rows:
            try:
                venc = date.fromisoformat(str(r[1])[:10])
                dias = (venc - today).days
            except Exception:
                dias = 999
            sgsst_proximos.append({'descripcion': r[0], 'proximo_vencimiento': r[1],
                                   'responsable': r[2], 'estado': r[3], 'dias_restantes': dias})
    except Exception:
        sgsst_proximos = []

    # Security summary — last 7 days
    try:
        c.execute("SELECT COUNT(*) FROM security_events WHERE event='login_success' AND ts >= ?",
                  (cutoff7+'T00:00:00Z',))
        succ7 = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM security_events WHERE event='login_failure' AND ts >= ?",
                  (cutoff7+'T00:00:00Z',))
        fail7 = c.fetchone()[0] or 0
        c.execute("SELECT ts FROM security_events ORDER BY id DESC LIMIT 1")
        last_ev = c.fetchone()
        last_event_ts = last_ev[0] if last_ev else None
        security = {'success_7d': succ7, 'fail_7d': fail7, 'last_event': last_event_ts}
    except Exception:
        security = {'success_7d': 0, 'fail_7d': 0, 'last_event': None}

    conn.close()
    return jsonify({
        'ingresos_mes': ingresos_mes,
        'ar': ar, 'ap': ap,
        'maquila_pipeline': maquila_pipeline,
        'stock_critico': stock_critico,
        'sgsst_proximos': sgsst_proximos,
        'security': security,
    })
@app.route('/api/admin/cleanup-test-data', methods=['POST'])
def admin_cleanup_test_data():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'Solo admins'}), 401
    d = request.get_json() or {}
    if not d.get('confirm'):
        return jsonify({'error': 'Enviar confirm:true para confirmar'}), 400
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    deleted = {}
    # Test OCs from audit
    test_oc_nums = ['OC-2026-0002','OC-2026-0003']
    for num in test_oc_nums:
        c.execute("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (num,))
        c.execute("DELETE FROM ordenes_compra WHERE numero_oc=? AND proveedor LIKE '%test%' OR numero_oc=?", (num, num))
    deleted['ocs'] = len(test_oc_nums)
    # Test solicitudes
    c.execute("DELETE FROM solicitudes WHERE numero='SOL-2026-0001' OR proveedor LIKE '%test%' OR proveedor LIKE '%prueba%'")
    deleted['solicitudes'] = c.rowcount
    # Test pedidos
    c.execute("DELETE FROM pedidos_items WHERE numero_pedido='PED-2026-0001'")
    c.execute("DELETE FROM pedidos WHERE numero='PED-2026-0001'")
    deleted['pedidos'] = c.rowcount
    # Test lotes
    c.execute("DELETE FROM lotes WHERE codigo_lote LIKE '%AUDIT%' OR codigo_lote LIKE '%TEST%' OR codigo_lote LIKE '%-test-%'")
    deleted['lotes'] = c.rowcount
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'deleted': deleted, 'message': 'Test data cleaned up'})

@app.route('/api/gerencia/input-manual', methods=['POST'])
def gerencia_input_manual():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.json or {}
    periodo = d.get('periodo', datetime.now().strftime('%Y-%m'))
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""INSERT INTO gerencia_inputs (periodo,saldo_caja,ingresos_animus,ingresos_maquila,notas,fecha)
                    VALUES (?,?,?,?,?,datetime('now'))
                    ON CONFLICT(periodo) DO UPDATE SET saldo_caja=excluded.saldo_caja,
                    ingresos_animus=excluded.ingresos_animus, ingresos_maquila=excluded.ingresos_maquila,
                    notas=excluded.notas, fecha=excluded.fecha""",
                 (periodo, float(d.get('saldo_caja',0)), float(d.get('ingresos_animus',0)),
                  float(d.get('ingresos_maquila',0)), d.get('notas','')))
    conn.commit(); conn.close()
    return jsonify({'message': f'Inputs de {periodo} guardados'})


# ─── MÓDULO FINANCIERO — Rutas ────────────────────────────────
@app.route('/financiero')
def financiero_page():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return redirect(url_for('login'))
    return Response(FINANCIERO_HTML, mimetype='text/html')

@app.route('/api/financiero/ingresos', methods=['GET','POST'])
def handle_fin_ingresos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('concepto') or not d.get('monto'):
            conn.close(); return jsonify({'error': 'Concepto y monto requeridos'}), 400
        periodo = (d.get('fecha') or datetime.now().isoformat())[:7]
        c.execute("""INSERT INTO flujo_ingresos (fecha,empresa,concepto,categoria,monto,periodo,fuente,referencia,creado_por)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (d.get('fecha', datetime.now().isoformat()[:10]), d.get('empresa','HHA'),
                   d['concepto'], d.get('categoria','Ventas'), float(d['monto']),
                   periodo, 'manual', d.get('referencia',''), session.get('compras_user','sistema')))
        conn.commit(); conn.close()
        return jsonify({'message': f"Ingreso de ${float(d['monto']):,.0f} registrado"}), 201
    mes = request.args.get('mes')
    q = "SELECT id,fecha,empresa,concepto,categoria,monto,periodo,referencia FROM flujo_ingresos"
    params = []
    if mes: q += " WHERE periodo=?"; params.append(mes)
    q += " ORDER BY fecha DESC LIMIT 200"
    c.execute(q, params)
    cols = ['id','fecha','empresa','concepto','categoria','monto','periodo','referencia']
    conn.close()
    return jsonify({'ingresos': [dict(zip(cols, r)) for r in c.fetchall()]})

@app.route('/api/financiero/egresos', methods=['GET','POST'])
def handle_fin_egresos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('concepto') or not d.get('monto'):
            conn.close(); return jsonify({'error': 'Concepto y monto requeridos'}), 400
        periodo = (d.get('fecha') or datetime.now().isoformat())[:7]
        c.execute("""INSERT INTO flujo_egresos (fecha,empresa,concepto,categoria,monto,periodo,fuente,referencia,creado_por)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (d.get('fecha', datetime.now().isoformat()[:10]), d.get('empresa','HHA'),
                   d['concepto'], d.get('categoria','MPs'), float(d['monto']),
                   periodo, 'manual', d.get('referencia',''), session.get('compras_user','sistema')))
        conn.commit(); conn.close()
        return jsonify({'message': f"Egreso de ${float(d['monto']):,.0f} registrado"}), 201
    mes = request.args.get('mes')
    q = "SELECT id,fecha,empresa,concepto,categoria,monto,periodo,referencia FROM flujo_egresos"
    params = []
    if mes: q += " WHERE periodo=?"; params.append(mes)
    q += " ORDER BY fecha DESC LIMIT 200"
    c.execute(q, params)
    cols = ['id','fecha','empresa','concepto','categoria','monto','periodo','referencia']
    conn.close()
    return jsonify({'egresos': [dict(zip(cols, r)) for r in c.fetchall()]})

@app.route('/api/financiero/kpis')
def financiero_kpis():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    periodo_actual = datetime.now().strftime('%Y-%m')
    # KPIs mes actual
    c.execute("SELECT COALESCE(SUM(monto),0), COUNT(*) FROM flujo_ingresos WHERE periodo=?", (periodo_actual,))
    ing_mes, ing_count = c.fetchone()
    c.execute("SELECT COALESCE(SUM(monto),0), COUNT(*) FROM flujo_egresos WHERE periodo=?", (periodo_actual,))
    egr_mes, egr_count = c.fetchone()
    # Saldo caja desde gerencia_inputs
    c.execute("SELECT saldo_caja FROM gerencia_inputs ORDER BY periodo DESC LIMIT 1")
    row = c.fetchone(); saldo_caja = row[0] if row else 0
    # Desglose por categoría mes actual
    c.execute("SELECT categoria, SUM(monto) as total FROM flujo_ingresos WHERE periodo=? GROUP BY categoria ORDER BY total DESC", (periodo_actual,))
    desglose_ing = [{'categoria': r[0], 'total': r[1]} for r in c.fetchall()]
    c.execute("SELECT categoria, SUM(monto) as total FROM flujo_egresos WHERE periodo=? GROUP BY categoria ORDER BY total DESC", (periodo_actual,))
    desglose_egr = [{'categoria': r[0], 'total': r[1]} for r in c.fetchall()]
    # Histórico 6 meses
    historico = []
    for i in range(5, -1, -1):
        from datetime import date as _d
        import calendar
        hoy = _d.today()
        mes = hoy.month - i
        anio = hoy.year
        while mes <= 0: mes += 12; anio -= 1
        p = f"{anio}-{mes:02d}"
        c.execute("SELECT COALESCE(SUM(monto),0) FROM flujo_ingresos WHERE periodo=?", (p,))
        ing = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(monto),0) FROM flujo_egresos WHERE periodo=?", (p,))
        egr = c.fetchone()[0]
        historico.append({'periodo': p, 'ingresos': ing, 'egresos': egr})
    conn.close()
    return jsonify({'ing_mes': ing_mes, 'ing_count': ing_count, 'egr_mes': egr_mes, 'egr_count': egr_count,
                    'saldo_caja': saldo_caja, 'desglose_ing': desglose_ing, 'desglose_egr': desglose_egr,
                    'historico': historico, 'periodo': periodo_actual})

@app.route('/api/financiero/flujo-mensual')
def financiero_flujo_mensual():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT periodo, SUM(monto) FROM flujo_ingresos GROUP BY periodo ORDER BY periodo")
    ings = {r[0]: r[1] for r in c.fetchall()}
    c.execute("SELECT periodo, SUM(monto) FROM flujo_egresos GROUP BY periodo ORDER BY periodo")
    egrs = {r[0]: r[1] for r in c.fetchall()}
    periodos = sorted(set(list(ings.keys()) + list(egrs.keys())))
    meses = [{'periodo': p, 'ingresos': ings.get(p, 0), 'egresos': egrs.get(p, 0)} for p in periodos]
    conn.close()
    return jsonify({'meses': meses})

@app.route('/api/financiero/config', methods=['GET','POST'])
def financiero_config():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        for clave, valor in d.items():
            c.execute("INSERT INTO flujo_config (clave,valor,descripcion) VALUES (?,?,?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor", (clave, str(valor), ''))
        conn.commit(); conn.close()
        return jsonify({'message': f'{len(d)} parámetros actualizados'})
    c.execute("SELECT clave, valor FROM flujo_config ORDER BY clave")
    config = {r[0]: r[1] for r in c.fetchall()}
    conn.close()
    return jsonify({'config': config})

@app.route('/api/financiero/importar-ocs', methods=['POST'])
def financiero_importar_ocs():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # Traer OCs recibidas que no estén ya importadas
    c.execute("""SELECT oc.numero_oc, oc.fecha, oc.proveedor,
                        COALESCE(SUM(i.cantidad_g * i.precio_unitario), oc.valor_total, 0) as total
                 FROM ordenes_compra oc
                 LEFT JOIN ordenes_compra_items i ON oc.numero_oc=i.numero_oc
                 WHERE oc.estado='Recibida'
                 AND oc.numero_oc NOT IN (SELECT referencia FROM flujo_egresos WHERE referencia LIKE 'OC-%')
                 GROUP BY oc.numero_oc""")
    ocs = c.fetchall()
    importadas = 0
    for numero_oc, fecha, proveedor, total in ocs:
        if total and total > 0:
            periodo = (fecha or datetime.now().isoformat())[:7]
            c.execute("""INSERT INTO flujo_egresos (fecha,empresa,concepto,categoria,monto,periodo,fuente,referencia,creado_por)
                         VALUES (?,?,?,?,?,?,?,?,?)""",
                      (fecha[:10] if fecha else datetime.now().isoformat()[:10],
                       'ESPAGIRIA', f'OC {numero_oc} — {proveedor or ""}',
                       'MPs', float(total), periodo, 'automatico', numero_oc, 'sistema'))
            importadas += 1
    conn.commit(); conn.close()
    return jsonify({'message': f'{importadas} OC(s) importadas como egresos'})


@app.route('/api/financiero/precios-mayorista', methods=['GET'])
def get_precios_mayorista():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT sku, descripcion, precio_base, precio_mayorista, unidad FROM sku_precios ORDER BY sku")
    rows = c.fetchall(); conn.close()
    return jsonify([{'sku':r[0],'descripcion':r[1],'precio_base':r[2],'precio_mayorista':r[3],'unidad':r[4]} for r in rows])

@app.route('/api/financiero/precios-mayorista/<sku>', methods=['POST'])
def update_precio_mayorista(sku):
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'Solo admins pueden editar precios'}), 401
    d = request.get_json()
    precio = float(d.get('precio_mayorista', 0) or 0)
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE sku_precios SET precio_mayorista=? WHERE sku=?", (precio, sku))
    conn.commit(); conn.close()
    return jsonify({'message': f'Precio actualizado para {sku}'})

@app.route('/api/financiero/ar-aging')
def financiero_ar_aging():
    from datetime import date
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    today = date.today()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT numero_pedido, cliente, fecha, valor_total
                 FROM pedidos
                 WHERE estado NOT IN ('Cancelado','Facturado','Entregado')
                 AND valor_total > 0""")
    rows = c.fetchall(); conn.close()
    buckets = {
        'corriente': {'total': 0, 'count': 0},
        'dias_30':   {'total': 0, 'count': 0},
        'dias_60':   {'total': 0, 'count': 0},
        'dias_90':   {'total': 0, 'count': 0},
    }
    pedidos = []
    ar_total = 0
    for r in rows:
        num, cliente, fecha_str, valor = r
        try:
            fd = date.fromisoformat(fecha_str[:10])
        except Exception:
            fd = today
        dias = (today - fd).days
        ar_total += (valor or 0)
        if dias <= 30:
            b = 'corriente'
        elif dias <= 60:
            b = 'dias_30'
        elif dias <= 90:
            b = 'dias_60'
        else:
            b = 'dias_90'
        buckets[b]['total'] += (valor or 0)
        buckets[b]['count'] += 1
        pedidos.append({'numero_pedido': num, 'cliente': cliente, 'fecha': fecha_str[:10] if fecha_str else '', 'dias': dias, 'valor_total': valor or 0})
    pedidos.sort(key=lambda x: x['dias'], reverse=True)
    return jsonify({'ar_total': ar_total, 'count': len(pedidos), 'buckets': buckets, 'pedidos': pedidos})

@app.route('/api/financiero/ap-aging')
def financiero_ap_aging():
    from datetime import date
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    today = date.today()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT numero_oc, proveedor, fecha, valor_total
                 FROM ordenes_compra
                 WHERE estado IN ('Autorizada','Recibida','Parcial')
                 AND (pagado_por IS NULL OR pagado_por = '')""")
    rows = c.fetchall(); conn.close()
    buckets = {
        'corriente': {'total': 0, 'count': 0},
        'dias_30':   {'total': 0, 'count': 0},
        'dias_60':   {'total': 0, 'count': 0},
        'dias_90':   {'total': 0, 'count': 0},
    }
    ocs = []
    ap_total = 0
    for r in rows:
        num, prov, fecha_str, valor = r
        try:
            fd = date.fromisoformat(fecha_str[:10])
        except Exception:
            fd = today
        dias = (today - fd).days
        ap_total += (valor or 0)
        if dias <= 30:
            b = 'corriente'
        elif dias <= 60:
            b = 'dias_30'
        elif dias <= 90:
            b = 'dias_60'
        else:
            b = 'dias_90'
        buckets[b]['total'] += (valor or 0)
        buckets[b]['count'] += 1
        ocs.append({'numero_oc': num, 'proveedor': prov, 'fecha': fecha_str[:10] if fecha_str else '', 'dias': dias, 'valor_total': valor or 0})
    ocs.sort(key=lambda x: x['dias'], reverse=True)
    return jsonify({'ap_total': ap_total, 'count': len(ocs), 'buckets': buckets, 'ocs': ocs})

@app.route('/api/financiero/working-capital')
def financiero_working_capital():
    from datetime import date, timedelta
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    today = date.today()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # AR
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM pedidos WHERE estado NOT IN ('Cancelado','Facturado','Entregado') AND valor_total > 0")
    ar_total = c.fetchone()[0] or 0
    # AP
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM ordenes_compra WHERE estado IN ('Autorizada','Recibida','Parcial') AND (pagado_por IS NULL OR pagado_por='')")
    ap_total = c.fetchone()[0] or 0
    # Cash from gerencia_inputs
    try:
        c.execute("SELECT valor FROM gerencia_inputs WHERE clave='saldo_caja' ORDER BY fecha DESC LIMIT 1")
        row = c.fetchone()
        cash = float(row[0]) if row else 0.0
    except Exception:
        cash = 0.0
    # Inventory value: lotes activos valorados a precio promedio por MP
    try:
        c.execute("""SELECT l.codigo_mp, l.cantidad_g,
                            COALESCE((SELECT AVG(oci.precio_unitario)
                                      FROM ordenes_compra_items oci
                                      WHERE oci.codigo_mp=l.codigo_mp AND oci.precio_unitario>0),0)
                     FROM lotes l WHERE l.estado='activo' AND l.cantidad_g>0""")
        inv_rows = c.fetchall()
        inventory_value = sum((r[1] or 0) * (r[2] or 0) for r in inv_rows)
    except Exception:
        inventory_value = 0.0
    # 90-day flows for DSO/DIO/DPO
    cutoff90 = (today - timedelta(days=90)).isoformat()
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM pedidos WHERE fecha >= ? AND estado NOT IN ('Cancelado')", (cutoff90,))
    ventas_90 = c.fetchone()[0] or 1
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM ordenes_compra WHERE fecha >= ? AND estado NOT IN ('Pendiente','Cancelada')", (cutoff90,))
    compras_90 = c.fetchone()[0] or 1
    c.execute("SELECT COALESCE(SUM(fi.cantidad * fi.precio_unitario),0) FROM flujo_egresos fi WHERE fi.fecha >= ? AND fi.categoria IN ('MP','Materia Prima','Insumo')", (cutoff90,))
    cogs_90 = c.fetchone()[0] or 1
    # Burn rate: promedio mensual de OCs pagadas (últimos 3 meses)
    cutoff3m = (today - timedelta(days=90)).isoformat()
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM ordenes_compra "
              "WHERE fecha >= ? AND estado NOT IN ('Pendiente','Cancelada','Borrador')",
              (cutoff3m,))
    egr3m = c.fetchone()[0] or 0
    burn_rate = max(egr3m / 3.0, 1.0)
    conn.close()
    dso = (ar_total / (ventas_90 / 90.0)) if ventas_90 > 0 else 0
    dpo = (ap_total / (compras_90 / 90.0)) if compras_90 > 0 else 0
    dio = (inventory_value / (cogs_90 / 90.0)) if cogs_90 > 0 else 0
    ccc = dio + dso - dpo
    working_capital = cash + inventory_value + ar_total - ap_total
    runway_meses = (cash / burn_rate) if burn_rate > 0 else 0
    return jsonify({
        'ar_total': ar_total, 'ap_total': ap_total, 'cash': cash,
        'inventory_value': inventory_value, 'working_capital': working_capital,
        'dso': dso, 'dpo': dpo, 'dio': dio, 'ccc': ccc,
        'burn_rate': burn_rate, 'runway_meses': runway_meses
    })

@app.route('/api/financiero/pnl')
def financiero_pnl():
    """P&L real: ingresos desde pedidos + maquila, egresos desde ordenes_compra."""
    from datetime import date, timedelta
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    today   = date.today()
    mes_str = today.strftime('%Y-%m')
    year_str= today.strftime('%Y')
    periodo = today.strftime('%b %Y')
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()

    def ing_animus(periodo_like):
        c.execute("SELECT COALESCE(SUM(valor_total),0) FROM pedidos "
                  "WHERE fecha LIKE ? AND estado NOT IN ('Cancelado')"
                  " AND (empresa='ANIMUS' OR empresa IS NULL OR empresa='')",
                  (periodo_like+'%',))
        return c.fetchone()[0] or 0

    def ing_maquila(periodo_like):
        try:
            c.execute("SELECT COALESCE(SUM(precio_lote),0) FROM maquila_ordenes "
                      "WHERE fecha_orden LIKE ? AND estado NOT IN ('Cotizacion','Cancelada')",
                      (periodo_like+'%',))
            return c.fetchone()[0] or 0
        except Exception:
            return 0

    def egr_total(periodo_like):
        c.execute("SELECT COALESCE(SUM(valor_total),0) FROM ordenes_compra "
                  "WHERE fecha LIKE ? AND estado NOT IN ('Pendiente','Cancelada','Borrador')",
                  (periodo_like+'%',))
        return c.fetchone()[0] or 0

    # Mes actual
    animus_ing  = ing_animus(mes_str)
    maqui_ing   = ing_maquila(mes_str)
    total_ing   = animus_ing + maqui_ing
    total_egr   = egr_total(mes_str)
    margen      = total_ing - total_egr
    margen_pct  = round((margen / total_ing * 100), 1) if total_ing > 0 else 0
    # YTD
    ytd_ing = ing_animus(year_str) + ing_maquila(year_str)
    ytd_egr = egr_total(year_str)
    empresas = {
        'ANIMUS':    {'ingresos': animus_ing, 'egresos': 0, 'margen': animus_ing,
                      'margen_pct': 100, 'ingresos_ytd': ing_animus(year_str),
                      'egresos_ytd': 0, 'ebitda': animus_ing},
        'ESPAGIRIA': {'ingresos': maqui_ing, 'egresos': 0, 'margen': maqui_ing,
                      'margen_pct': 100, 'ingresos_ytd': ing_maquila(year_str),
                      'egresos_ytd': 0, 'ebitda': maqui_ing},
        'TOTAL':     {'ingresos': total_ing, 'egresos': total_egr, 'margen': margen,
                      'margen_pct': margen_pct, 'ingresos_ytd': ytd_ing,
                      'egresos_ytd': ytd_egr, 'ebitda': margen},
    }
    # Histórico 6 meses
    historico = []
    for i in range(5, -1, -1):
        ref   = today.replace(day=1) - timedelta(days=i * 28)
        p     = ref.strftime('%Y-%m')
        label = ref.strftime('%b %y')
        h_ing = ing_animus(p) + ing_maquila(p)
        h_egr = egr_total(p)
        historico.append({'periodo': label, 'ingresos': h_ing,
                          'egresos': h_egr, 'margen': h_ing - h_egr})
    conn.close()
    return jsonify({'empresas': empresas, 'historico': historico, 'periodo': periodo})

# ===============================================================
# INVENTARIO v2 - NUEVOS ENDPOINTS
# ===============================================================

@app.route('/api/ordenes-compra/pendientes-recepcion')
def ocs_pendientes_recepcion():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT oc.numero_oc, oc.proveedor, oc.fecha, oc.valor_total,
                        oci.codigo_mp, oci.nombre_mp, oci.cantidad_g, oci.precio_unitario
                 FROM ordenes_compra oc
                 JOIN ordenes_compra_items oci ON oc.numero_oc = oci.numero_oc
                 WHERE oc.estado IN ('Aprobada','Enviada','Parcial')
                 ORDER BY oc.fecha DESC""")
    rows = c.fetchall(); conn.close()
    ocs = {}
    for r in rows:
        num = r[0]
        if num not in ocs:
            ocs[num] = {'numero_oc': num, 'proveedor': r[1], 'fecha': r[2],
                        'valor_total': r[3], 'items': []}
        ocs[num]['items'].append({'codigo_mp': r[4], 'nombre_mp': r[5],
                                   'cantidad_g': r[6], 'precio_unitario': r[7]})
    return jsonify(list(ocs.values()))

@app.route('/api/trazabilidad/lote/<path:lote>')
def trazabilidad_lote_path(lote):
    import urllib.parse; lote = urllib.parse.unquote(lote)
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT id, material_id, material_nombre, cantidad, tipo, fecha,
                        observaciones, proveedor, precio_kg, numero_factura, numero_oc
                 FROM movimientos WHERE lote=? ORDER BY fecha""", (lote,))
    cols = [d[0] for d in c.description]
    movs = [dict(zip(cols, r)) for r in c.fetchall()]
    c.execute("""SELECT id, producto, cantidad, fecha, observaciones, operador
                 FROM producciones WHERE observaciones LIKE ? ORDER BY fecha""", (f'%{lote}%',))
    cols2 = [d[0] for d in c.description]
    prods = [dict(zip(cols2, r)) for r in c.fetchall()]
    c.execute("""SELECT d.numero, cl.nombre, d.fecha, d.estado
                 FROM despachos d LEFT JOIN clientes cl ON d.cliente_id=cl.id
                 WHERE d.observaciones LIKE ?""", (f'%{lote}%',))
    cols3 = [d[0] for d in c.description]
    desps = [dict(zip(cols3, r)) for r in c.fetchall()]
    conn.close()
    return jsonify({'lote': lote, 'movimientos': movs, 'producciones': prods, 'despachos': desps})

@app.route('/api/mp/<codigo>/historial-precios')
def historial_precios_mp(codigo):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT fecha, proveedor, precio_kg, valor_total, numero_factura, numero_oc
                 FROM movimientos WHERE material_id=? AND tipo='Entrada' AND precio_kg>0
                 ORDER BY fecha DESC LIMIT 24""", (codigo,))
    hist = [{'fecha':r[0],'proveedor':r[1],'precio_kg':r[2],'valor_total':r[3],'factura':r[4],'oc':r[5]} for r in c.fetchall()]
    c.execute("SELECT precio_referencia, proveedor FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    mp = c.fetchone(); conn.close()
    return jsonify({'codigo': codigo, 'precio_referencia': mp[0] if mp else 0,
                    'proveedor_habitual': mp[1] if mp else '', 'historial': hist})

@app.route('/api/mp/<codigo>/consumo-historico')
def consumo_historico_mp(codigo):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT substr(fecha,1,7) as mes,
                        SUM(CASE WHEN tipo='Salida' THEN cantidad ELSE 0 END) as consumo_g,
                        COUNT(CASE WHEN tipo='Salida' THEN 1 END) as n_salidas
                 FROM movimientos WHERE material_id=?
                 GROUP BY substr(fecha,1,7) ORDER BY mes DESC LIMIT 12""", (codigo,))
    meses = [{'mes':r[0],'consumo_g':r[1],'n_salidas':r[2]} for r in c.fetchall()]
    consumos = [m['consumo_g'] for m in meses if m['consumo_g'] and m['consumo_g'] > 0]
    promedio = sum(consumos)/len(consumos) if consumos else 0
    c.execute("SELECT lead_time_dias, stock_minimo FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    mp = c.fetchone(); conn.close()
    lead = (mp[0] if mp and mp[0] else 7)
    stock_min = (mp[1] if mp and mp[1] else 0)
    punto_reorden = (promedio/30) * lead + stock_min
    return jsonify({'codigo': codigo, 'meses': meses,
                    'promedio_mes_g': round(promedio, 0),
                    'consumo_diario_g': round(promedio/30, 1),
                    'lead_time_dias': lead,
                    'punto_reorden_g': round(punto_reorden, 0)})

@app.route('/api/conteos', methods=['GET','POST'])
def conteos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        num = 'CNT-' + datetime.now().strftime('%Y%m%d-%H%M')
        c.execute("""INSERT INTO conteos_fisicos (numero,fecha_inicio,estado,responsable,observaciones)
                     VALUES (?,?,'Abierto',?,?)""",
                  (num, datetime.now().isoformat(), d.get('responsable',''), d.get('observaciones','')))
        cid = c.lastrowid
        c.execute("""SELECT mp.codigo_mp, mp.nombre_comercial,
                            COALESCE(SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad
                                         WHEN m.tipo='Salida' THEN -m.cantidad ELSE 0 END),0)
                     FROM maestro_mps mp
                     LEFT JOIN movimientos m ON mp.codigo_mp=m.material_id
                     WHERE mp.activo=1 GROUP BY mp.codigo_mp""")
        mps = c.fetchall()
        for mp in mps:
            c.execute("INSERT INTO conteo_items (conteo_id,codigo_mp,nombre_mp,stock_sistema) VALUES (?,?,?,?)",
                      (cid, mp[0], mp[1], max(0, mp[2])))
        c.execute("UPDATE conteos_fisicos SET total_items=? WHERE id=?", (len(mps), cid))
        conn.commit(); conn.close()
        return jsonify({'numero': num, 'id': cid, 'total_items': len(mps)}), 201
    c.execute("SELECT id,numero,fecha_inicio,estado,responsable,total_items,items_diferencia FROM conteos_fisicos ORDER BY fecha_inicio DESC LIMIT 20")
    rows = [{'id':r[0],'numero':r[1],'fecha':r[2],'estado':r[3],'responsable':r[4],'total':r[5],'diffs':r[6]} for r in c.fetchall()]
    conn.close(); return jsonify(rows)

@app.route('/api/conteos/<int:cid>', methods=['GET','PATCH'])
def conteo_detalle(cid):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'PATCH':
        d = request.json or {}; accion = d.get('accion')
        if accion == 'registrar_fisico':
            sf = float(d.get('stock_fisico', 0))
            c.execute("""UPDATE conteo_items SET stock_fisico=?,diferencia=?-stock_sistema,observaciones=?
                         WHERE conteo_id=? AND codigo_mp=?""",
                      (sf, sf, d.get('observaciones',''), cid, d.get('codigo_mp')))
            c.execute("""UPDATE conteos_fisicos SET
                         items_diferencia=(SELECT COUNT(*) FROM conteo_items
                                          WHERE conteo_id=? AND stock_fisico IS NOT NULL AND ABS(diferencia)>0.1)
                         WHERE id=?""", (cid, cid))
        elif accion == 'cerrar':
            c.execute("UPDATE conteos_fisicos SET estado='Cerrado',fecha_cierre=?,aprobado_por=? WHERE id=?",
                      (datetime.now().isoformat(), d.get('aprobado_por',''), cid))
        elif accion == 'aplicar_ajustes':
            c.execute("SELECT codigo_mp,nombre_mp,diferencia FROM conteo_items WHERE conteo_id=? AND ABS(diferencia)>0.1 AND ajuste_aplicado=0", (cid,))
            for cod, nom, dif in c.fetchall():
                tipo = 'Entrada' if dif > 0 else 'Salida'
                c.execute("""INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,observaciones,estado_lote,operador)
                             VALUES (?,?,?,?,?,?,'VIGENTE',?)""",
                          (cod, nom, abs(dif), tipo, datetime.now().isoformat(), f'Ajuste conteo {cid}', d.get('responsable','')))
                c.execute("UPDATE conteo_items SET ajuste_aplicado=1 WHERE conteo_id=? AND codigo_mp=?", (cid, cod))
        conn.commit()
        c.execute("SELECT id,numero,estado,total_items,items_diferencia FROM conteos_fisicos WHERE id=?", (cid,))
        r = c.fetchone(); conn.close()
        return jsonify({'id':r[0],'numero':r[1],'estado':r[2],'total':r[3],'diffs':r[4]})
    c.execute("SELECT * FROM conteos_fisicos WHERE id=?", (cid,)); h = c.fetchone()
    if not h: conn.close(); return jsonify({'error':'No encontrado'}), 404
    c.execute("SELECT codigo_mp,nombre_mp,stock_sistema,stock_fisico,diferencia,ajuste_aplicado,observaciones FROM conteo_items WHERE conteo_id=? ORDER BY nombre_mp", (cid,))
    items = [{'codigo':r[0],'nombre':r[1],'sistema':r[2],'fisico':r[3],'diff':r[4],'ajustado':r[5],'obs':r[6]} for r in c.fetchall()]
    conn.close()
    return jsonify({'header':{'id':h[0],'numero':h[1],'estado':h[4],'responsable':h[5],'total':h[7],'diffs':h[8]},'items':items})


@app.route('/api/lotes/cuarentena/<int:mov_id>/liberar', methods=['POST'])
def liberar_cuarentena(mov_id):
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error':'Solo admins pueden liberar cuarentena'}), 401
    d = request.json or {}; decision = d.get('decision','Aprobado')
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    nuevo_estado = 'VIGENTE' if decision == 'Aprobado' else 'RECHAZADO'
    c.execute("UPDATE movimientos SET estado_lote=? WHERE id=?", (nuevo_estado, mov_id))
    c.execute("""INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                 VALUES (?,?,?,?,?,?,datetime('now'))""",
              (session['compras_user'], f'{decision.upper()}_CUARENTENA', 'movimientos',
               str(mov_id), d.get('observaciones',''), request.remote_addr))
    conn.commit(); conn.close()
    return jsonify({'ok':True, 'decision':decision, 'estado':nuevo_estado})

@app.route('/api/maestro-mp/<codigo>/precio', methods=['POST'])
def actualizar_precio_mp(codigo):
    d = request.json or {}; precio = float(d.get('precio_kg', 0))
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE maestro_mps SET precio_referencia=?,ultima_act_precio=? WHERE codigo_mp=?",
              (precio, datetime.now().isoformat()[:10], codigo))
    c.execute("""INSERT INTO precios_mp_historico (codigo_mp,proveedor,precio_kg,fecha,origen,observaciones)
                 VALUES (?,?,?,?,?,?)""",
              (codigo, d.get('proveedor',''), precio, datetime.now().isoformat()[:10],
               d.get('origen','manual'), d.get('observaciones','')))
    conn.commit(); conn.close()
    return jsonify({'ok':True, 'precio_kg':precio})


@app.route('/api/admin/backfill-precios-mp', methods=['POST'])
def backfill_precios_mp():
    """Pobla precio_referencia en maestro_mps desde movimientos.precio_kg y precios_mp_historico.
    Solo actualiza MPs que tienen precio_referencia=0 o nulo."""
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    actualizados = 0
    # Fuente 1: promedio ponderado de movimientos de entrada con precio registrado
    c.execute("""SELECT material_id, AVG(precio_kg) as avg_precio
                 FROM movimientos
                 WHERE tipo='Entrada' AND precio_kg IS NOT NULL AND precio_kg > 0
                 GROUP BY material_id""")
    from_movs = c.fetchall()
    for mat_id, avg_p in from_movs:
        c.execute("""UPDATE maestro_mps SET precio_referencia=?, ultima_act_precio=datetime('now')
                     WHERE codigo_mp=? AND (precio_referencia IS NULL OR precio_referencia=0)""",
                  (round(avg_p, 2), mat_id))
        actualizados += c.rowcount
    # Fuente 2: precios_mp_historico (precio más reciente por MP)
    c.execute("""SELECT codigo_mp, precio_kg FROM precios_mp_historico
                 WHERE (codigo_mp, fecha) IN (
                     SELECT codigo_mp, MAX(fecha) FROM precios_mp_historico
                     WHERE precio_kg > 0 GROUP BY codigo_mp
                 )""")
    from_hist = c.fetchall()
    hist_count = 0
    for codigo, precio in from_hist:
        c.execute("""UPDATE maestro_mps SET precio_referencia=?, ultima_act_precio=datetime('now')
                     WHERE codigo_mp=? AND (precio_referencia IS NULL OR precio_referencia=0)""",
                  (round(precio, 2), codigo))
        hist_count += c.rowcount
    actualizados += hist_count
    # Stats
    c.execute("SELECT COUNT(*) FROM maestro_mps WHERE precio_referencia > 0")
    con_precio = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM maestro_mps WHERE activo=1")
    total_activos = c.fetchone()[0]
    conn.commit(); conn.close()
    return jsonify({
        'ok': True,
        'actualizados': actualizados,
        'con_precio_ahora': con_precio,
        'total_activos': total_activos,
        'cobertura_pct': round(con_precio / total_activos * 100, 1) if total_activos > 0 else 0
    })


# ═══════════════════════════════════════════════
#  MAQUILA 360 — API
# ═══════════════════════════════════════════════
@app.route('/api/maquila/prospectos', methods=['GET','POST'])
def api_maquila_prospectos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        empresa = (d.get('empresa') or '').strip()
        if not empresa:
            conn.close(); return jsonify({'error':'Empresa requerida'}), 400
        c.execute('''INSERT INTO maquila_prospectos
                     (empresa,contacto,email,whatsapp,categoria_producto,etapa,
                      observaciones,valor_estimado_lote,creado_por)
                     VALUES (?,?,?,?,?,?,?,?,?)''',
                  (empresa, d.get('contacto',''), d.get('email',''),
                   d.get('telefono',''), d.get('producto_tipo',''),
                   d.get('etapa','Contacto'), d.get('notas',''),
                   float(d.get('valor_estimado',0)),
                   session.get('compras_user') or d.get('operador','sistema')))
        conn.commit(); pid = c.lastrowid; conn.close()
        return jsonify({'id': pid}), 201
    c.execute('''SELECT id, empresa, contacto, email,
                        COALESCE(whatsapp,'') as telefono,
                        COALESCE(categoria_producto,'') as producto_tipo,
                        etapa,
                        COALESCE(observaciones,'') as notas,
                        COALESCE(valor_estimado_lote,0) as valor_estimado,
                        fecha_creacion as fecha_contacto
                 FROM maquila_prospectos ORDER BY id DESC''')
    cols=['id','empresa','contacto','email','telefono','producto_tipo',
          'etapa','notas','valor_estimado','fecha_contacto']
    rows=[dict(zip(cols,r)) for r in c.fetchall()]
    conn.close(); return jsonify(rows)

@app.route('/api/maquila/prospectos/<int:pid>', methods=['PATCH'])
def api_maquila_prospecto_patch(pid):
    d = request.json or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if 'etapa' in d:
        c.execute('UPDATE maquila_prospectos SET etapa=? WHERE id=?', (d['etapa'], pid))
    if 'valor_estimado' in d:
        c.execute('UPDATE maquila_prospectos SET valor_estimado_lote=? WHERE id=?',
                  (float(d['valor_estimado']), pid))
    if 'notas' in d:
        c.execute('UPDATE maquila_prospectos SET observaciones=? WHERE id=?', (d['notas'], pid))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/maquila/ordenes', methods=['GET','POST'])
def api_maquila_ordenes():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        empresa = (d.get('empresa') or '').strip()
        producto = (d.get('producto') or '').strip()
        if not empresa or not producto:
            conn.close(); return jsonify({'error':'Empresa y producto requeridos'}), 400
        c.execute('''INSERT INTO maquila_ordenes
                     (cliente_nombre,producto,lote_kg,fecha_orden,
                      fecha_entrega_est,estado,precio_lote,observaciones,creado_por)
                     VALUES (?,?,?,?,?,?,?,?,?)''',
                  (empresa, producto, float(d.get('batch_size_kg',0)),
                   d.get('fecha_inicio',''), d.get('fecha_entrega',''),
                   d.get('estado','Cotizacion'), float(d.get('valor_total',0)),
                   d.get('observaciones',''),
                   session.get('compras_user') or d.get('operador','sistema')))
        conn.commit(); oid=c.lastrowid; conn.close()
        return jsonify({'id': oid}), 201
    c.execute('''SELECT id,
                        COALESCE(cliente_nombre,'') as empresa,
                        producto,
                        COALESCE(lote_kg,0) as batch_size_kg,
                        COALESCE(fecha_orden,'') as fecha_inicio,
                        COALESCE(fecha_entrega_est,'') as fecha_entrega,
                        estado,
                        COALESCE(precio_lote,0) as valor_total,
                        COALESCE(observaciones,'') as observaciones,
                        fecha_creacion
                 FROM maquila_ordenes ORDER BY fecha_creacion DESC''')
    cols=['id','empresa','producto','batch_size_kg','fecha_inicio','fecha_entrega',
          'estado','valor_total','observaciones','fecha_creacion']
    rows=[dict(zip(cols,r)) for r in c.fetchall()]
    conn.close(); return jsonify(rows)

@app.route('/api/maquila/ordenes/<int:oid>', methods=['PATCH'])
def api_maquila_orden_patch(oid):
    d = request.json or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if 'estado' in d:
        c.execute('UPDATE maquila_ordenes SET estado=? WHERE id=?', (d['estado'], oid))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/maquila/cotizar', methods=['POST'])
def api_maquila_cotizar():
    d = request.json or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute('''INSERT INTO maquila_cotizaciones
                 (empresa,producto_tipo,batch_size_kg,costo_mp,costo_proceso,margen_pct,valor_total,usuario)
                 VALUES (?,?,?,?,?,?,?,?)''',
              (d.get('empresa',''), d.get('producto_tipo',''),
               float(d.get('batch_size_kg',0)), float(d.get('costo_mp',0)),
               float(d.get('costo_proceso',0)), float(d.get('margen_pct',0)),
               float(d.get('valor_total',0)),
               session.get('compras_user') or d.get('operador','sistema')))
    conn.commit(); cid=c.lastrowid; conn.close()
    return jsonify({'id': cid}), 201

@app.route('/api/maquila/kpis', methods=['GET'])
def api_maquila_kpis():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM maquila_prospectos WHERE etapa NOT IN ('Activo','Perdido') AND estado='Activo'")
    prosp = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM maquila_ordenes WHERE estado IN ('Cotizacion','Orden','En proceso','Produccion')")
    ords = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(valor_estimado_lote),0) FROM maquila_prospectos WHERE estado='Activo'")
    valor = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM maquila_prospectos WHERE etapa IN ('Negociacion','Cierre') AND estado='Activo'")
    cierre = c.fetchone()[0]
    conn.close()
    return jsonify({'prospectos_activos':prosp,'ordenes_activas':ords,
                    'valor_pipeline':valor,'en_cierre':cierre})


# ═══════════════════════════════════════════════════════
#  ÁNIMUS — Auto Producción + Recall Engine COC-PRO-016
# ═══════════════════════════════════════════════════════
@app.route('/api/animus/alertas-stock', methods=['GET'])
def animus_alertas_stock():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT sku, descripcion, empresa,
                        SUM(unidades_disponible) as disponible,
                        stock_minimo_ud, dias_reposicion, precio_base
                 FROM stock_pt
                 WHERE empresa='ANIMUS' AND estado='Disponible'
                 GROUP BY sku
                 HAVING disponible < stock_minimo_ud AND stock_minimo_ud > 0
                 ORDER BY (disponible*1.0/NULLIF(stock_minimo_ud,0)) ASC""")
    cols=['sku','descripcion','empresa','disponible','stock_minimo_ud','dias_reposicion','precio_base']
    alertas=[dict(zip(cols,r)) for r in c.fetchall()]
    # Check pending solicitudes
    for a in alertas:
        c.execute("""SELECT COUNT(*) FROM solicitudes_produccion
                     WHERE sku=? AND estado='Pendiente'""", (a['sku'],))
        a['solicitud_pendiente'] = c.fetchone()[0] > 0
        a['deficit'] = max(0, a['stock_minimo_ud'] - a['disponible'])
        a['cobertura_dias'] = round(a['disponible'] / max(a['stock_minimo_ud']/30, 1), 0)
    conn.close()
    return jsonify({'alertas': alertas, 'total': len(alertas)})

@app.route('/api/animus/solicitar-produccion', methods=['POST'])
def animus_solicitar_produccion():
    d = request.json or {}
    sku = d.get('sku','').strip()
    if not sku:
        return jsonify({'error': 'SKU requerido'}), 400
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # Get current stock info
    c.execute("SELECT descripcion, SUM(unidades_disponible), stock_minimo_ud FROM stock_pt WHERE sku=? AND empresa='ANIMUS' AND estado='Disponible' GROUP BY sku", (sku,))
    row = c.fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'SKU no encontrado en stock ANIMUS'}), 404
    desc, disponible, minimo = row[0], row[1] or 0, row[2] or 0
    # Check if there's already a pending solicitud
    c.execute("SELECT id FROM solicitudes_produccion WHERE sku=? AND estado='Pendiente'", (sku,))
    existente = c.fetchone()
    if existente:
        conn.close(); return jsonify({'warning': 'Ya existe una solicitud pendiente para este SKU', 'id': existente[0]}), 200
    unidades = int(d.get('unidades', max(minimo - disponible, minimo)))
    prioridad = 'Alta' if disponible == 0 else ('Normal' if disponible > minimo * 0.5 else 'Alta')
    c.execute("""INSERT INTO solicitudes_produccion
                 (sku, descripcion, unidades_solicitadas, motivo, estado,
                  prioridad, fecha_requerida, solicitado_por, observaciones)
                 VALUES (?,?,?,?,?,?,?,?,?)""",
              (sku, desc, unidades,
               f'Stock bajo: {disponible} uds disponibles (mínimo {minimo})',
               'Pendiente', prioridad,
               d.get('fecha_requerida',''),
               session.get('compras_user') or d.get('operador','sistema'),
               d.get('observaciones','')))
    sid = c.lastrowid
    # Audit log
    c.execute("""INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                 VALUES (?,?,?,?,?,?,datetime('now'))""",
              (session.get('compras_user','sistema'), 'SOLICITUD_PRODUCCION',
               'solicitudes_produccion', str(sid),
               f'{sku} — {unidades} uds — Stock: {disponible}/{minimo}',
               request.remote_addr))
    conn.commit(); conn.close()
    return jsonify({'id': sid, 'sku': sku, 'unidades': unidades, 'prioridad': prioridad}), 201

@app.route('/api/animus/solicitudes-produccion', methods=['GET'])
def animus_solicitudes_produccion():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT id,sku,descripcion,unidades_solicitadas,motivo,
                        estado,prioridad,fecha_solicitud,fecha_requerida,
                        solicitado_por,observaciones
                 FROM solicitudes_produccion ORDER BY
                 CASE prioridad WHEN 'Urgente' THEN 1 WHEN 'Alta' THEN 2 ELSE 3 END,
                 fecha_solicitud DESC""")
    cols=['id','sku','descripcion','unidades','motivo','estado','prioridad',
          'fecha_solicitud','fecha_requerida','solicitado_por','observaciones']
    rows=[dict(zip(cols,r)) for r in c.fetchall()]
    conn.close(); return jsonify(rows)

@app.route('/api/animus/solicitudes-produccion/<int:sid>', methods=['PATCH'])
def animus_update_solicitud(sid):
    d = request.json or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if 'estado' in d:
        c.execute("UPDATE solicitudes_produccion SET estado=? WHERE id=?", (d['estado'], sid))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/stock-pt/<sku>/reorden', methods=['POST'])
def actualizar_reorden_pt(sku):
    d = request.json or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE stock_pt SET stock_minimo_ud=?, dias_reposicion=? WHERE sku=?",
              (int(d.get('stock_minimo_ud', 0)),
               int(d.get('dias_reposicion', 15)), sku))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

# ── Recall Engine COC-PRO-016 ──────────────────────────────────────────
@app.route('/api/recall/simular/<path:lote_pt>', methods=['GET'])
def recall_simular(lote_pt):
    import urllib.parse; lote_pt = urllib.parse.unquote(lote_pt)
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # Find all dispatch items with this lote_pt
    c.execute("""SELECT di.numero_despacho, di.sku, di.descripcion,
                        di.cantidad, di.lote_pt,
                        d.fecha, d.estado,
                        cl.nombre as cliente, cl.email, cl.telefono
                 FROM despachos_items di
                 LEFT JOIN despachos d ON di.numero_despacho=d.numero
                 LEFT JOIN clientes cl ON d.cliente_id=cl.id
                 WHERE di.lote_pt=?
                 ORDER BY d.fecha DESC""", (lote_pt,))
    cols=['despacho','sku','descripcion','cantidad','lote_pt','fecha','estado_desp',
          'cliente','email','telefono']
    items=[dict(zip(cols,r)) for r in c.fetchall()]
    # Aggregates
    total_uds = sum(i['cantidad'] for i in items)
    clientes_afectados = list({i['cliente'] for i in items if i['cliente']})
    despachos_afectados = list({i['despacho'] for i in items})
    # Also check stock_pt (units still in warehouse)
    c.execute("SELECT SUM(unidades_disponible) FROM stock_pt WHERE lote_produccion=? AND estado='Disponible'", (lote_pt,))
    en_bodega = c.fetchone()[0] or 0
    conn.close()
    return jsonify({
        'lote_pt': lote_pt,
        'impacto': {
            'unidades_despachadas': total_uds,
            'unidades_en_bodega': en_bodega,
            'total_afectadas': total_uds + en_bodega,
            'despachos': len(despachos_afectados),
            'clientes': len(clientes_afectados)
        },
        'despachos_detalle': items,
        'clientes_afectados': clientes_afectados,
        'alerta': 'ALTO' if (total_uds + en_bodega) > 500 else ('MEDIO' if (total_uds + en_bodega) > 100 else 'BAJO')
    })

@app.route('/api/recall/ejecutar', methods=['POST'])
def recall_ejecutar():
    if 'compras_user' not in session or session.get('compras_user') not in ADMIN_USERS:
        return jsonify({'error': 'Solo administradores pueden ejecutar un recall'}), 401
    d = request.json or {}
    lote_pt = d.get('lote_pt','').strip()
    motivo  = d.get('motivo','').strip()
    if not lote_pt or not motivo:
        return jsonify({'error': 'lote_pt y motivo son requeridos'}), 400
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # Count impact
    c.execute("SELECT COUNT(*), SUM(di.cantidad) FROM despachos_items di WHERE di.lote_pt=?", (lote_pt,))
    n_desp, total_uds = c.fetchone(); total_uds = total_uds or 0
    # Block remaining stock in bodega
    c.execute("UPDATE stock_pt SET estado='Recall' WHERE lote_produccion=?", (lote_pt,))
    bloqueadas = c.rowcount
    # Log to recall_log
    c.execute("""INSERT INTO recall_log
                 (lote_pt,sku,motivo,total_despachos,total_unidades,ejecutado_por,estado)
                 VALUES (?,?,?,?,?,?,?)""",
              (lote_pt, d.get('sku',''), motivo,
               n_desp or 0, total_uds,
               session['compras_user'], 'Ejecutado'))
    rid = c.lastrowid
    # Audit log — immutable
    c.execute("""INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                 VALUES (?,?,?,?,?,?,datetime('now'))""",
              (session['compras_user'], 'RECALL_EJECUTADO', 'stock_pt',
               str(rid),
               f'Lote {lote_pt} — Motivo: {motivo} — {total_uds} uds en {n_desp} despachos — {bloqueadas} lotes bloqueados en bodega',
               request.remote_addr))
    conn.commit(); conn.close()
    return jsonify({
        'recall_id': rid,
        'lote_pt': lote_pt,
        'unidades_despachadas': total_uds,
        'despachos': n_desp,
        'lotes_bloqueados_bodega': bloqueadas,
        'estado': 'Ejecutado'
    }), 201




# ─── Panel de Recepcion — rutas standalone ────────────────────────────────────


@app.route('/hub-salida')
def hub_salida_page():
    if 'compras_user' not in session:
        return redirect(url_for('login'))
    return Response(SALIDA_HTML, mimetype='text/html')

@app.route('/api/hub-salida/pedidos-pendientes')
def hub_pedidos_pendientes():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT p.numero, p.cliente_id, cl.nombre as cliente, p.fecha, p.estado, p.valor_total
                 FROM pedidos p
                 LEFT JOIN clientes cl ON p.cliente_id = cl.id
                 WHERE p.estado IN ('Confirmado','En preparacion','En Produccion','Aprobado','Listo')
                 ORDER BY p.fecha DESC""")
    cols = ['numero','cliente_id','cliente','fecha','estado','valor_total']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return jsonify({'pedidos': rows})

@app.route('/api/hub-salida/pedido/<numero>')
def hub_pedido_detalle(numero):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT p.numero, p.cliente_id, cl.nombre as cliente, p.fecha, p.estado, p.valor_total
                 FROM pedidos p LEFT JOIN clientes cl ON p.cliente_id=cl.id
                 WHERE p.numero=?""", (numero,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Pedido no encontrado'}), 404
    ped = dict(zip(['numero','cliente_id','cliente','fecha','estado','valor_total'], row))
    c.execute("""SELECT sku, descripcion, cantidad, precio_unitario
                 FROM pedidos_items WHERE numero_pedido=?""", (numero,))
    ped['items'] = [dict(zip(['sku','descripcion','cantidad','precio_unitario'], r)) for r in c.fetchall()]
    conn.close()
    return jsonify(ped)

@app.route('/api/hub-salida/stock/<sku>')
def hub_stock_sku(sku):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT lote_pt, unidades_disponible, fecha_produccion
                 FROM stock_pt WHERE sku=? AND estado='Disponible' AND unidades_disponible>0
                 ORDER BY fecha_produccion ASC""", (sku,))
    lotes = [{'lote': r[0], 'disponible': r[1], 'fecha': r[2]} for r in c.fetchall()]
    total = sum(l['disponible'] for l in lotes)
    conn.close()
    return jsonify({'sku': sku, 'total': total, 'lotes': lotes})

@app.route('/api/hub-salida/despachar', methods=['POST'])
def hub_despachar():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    d = request.get_json() or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM despachos"); n = (c.fetchone()[0] or 0) + 1
    numero = f"DSP-{datetime.now().strftime('%Y')}-{n:04d}"
    c.execute("""INSERT INTO despachos (numero,numero_pedido,cliente_id,fecha,operador,observaciones,estado)
                 VALUES (?,?,?,datetime('now'),?,?,?)""",
              (numero, d.get('numero_pedido',''), d.get('cliente_id'),
               session.get('compras_user','sistema'), d.get('observaciones',''), 'Completado'))
    for it in (d.get('items') or []):
        if int(it.get('cantidad',0)) <= 0:
            continue
        c.execute("""INSERT INTO despachos_items (numero_despacho,sku,descripcion,lote_pt,cantidad,precio_unitario)
                     VALUES (?,?,?,?,?,?)""",
                  (numero, it.get('sku',''), it.get('descripcion',''), it.get('lote_pt',''),
                   int(it.get('cantidad',0)), float(it.get('precio_unitario',0))))
        lote = it.get('lote_pt','')
        if lote:
            c.execute("""UPDATE stock_pt SET unidades_disponible=MAX(0,unidades_disponible-?)
                         WHERE sku=? AND lote_pt=?""",
                      (int(it.get('cantidad',0)), it.get('sku',''), lote))
        else:
            c.execute("""UPDATE stock_pt SET unidades_disponible=MAX(0,unidades_disponible-?)
                         WHERE sku=? AND unidades_disponible>0
                         ORDER BY fecha_produccion ASC LIMIT 1""",
                      (int(it.get('cantidad',0)), it.get('sku','')))
    num_ped = d.get('numero_pedido','')
    if num_ped:
        c.execute("UPDATE pedidos SET estado='Despachado',fecha_despacho=datetime('now') WHERE numero=?", (num_ped,))
    conn.commit(); conn.close()
    return jsonify({'message': f'Despacho {numero} registrado', 'numero': numero}), 201


@app.route('/recepcion')
def recepcion_panel():
    return Response(RECEPCION_HTML, mimetype='text/html')


@app.route('/api/recepcion/detalle/<numero_oc>')
def recepcion_detalle_oc(numero_oc):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute(
        'SELECT numero_oc, proveedor, estado, categoria, fecha, '
        'COALESCE(valor_total,0), creado_por, observaciones '
        'FROM ordenes_compra WHERE numero_oc=?', (numero_oc,))
    oc = c.fetchone()
    if oc is None:
        conn.close(); return jsonify({'error': 'OC no encontrada'}), 404
    c.execute(
        'SELECT codigo_mp, nombre_mp, COALESCE(cantidad_g,0), '
        'COALESCE(precio_unitario,0), COALESCE(cantidad_recibida_g,0), '
        'COALESCE(lote_asignado,"") '
        'FROM ordenes_compra_items WHERE numero_oc=?', (numero_oc,))
    items = c.fetchall()
    conn.close()
    return jsonify({
        'numero_oc': oc[0], 'proveedor': oc[1], 'estado': oc[2],
        'categoria': oc[3], 'fecha': oc[4], 'valor_total': oc[5],
        'creado_por': oc[6], 'observaciones': oc[7],
        'items': [
            {'codigo_mp': i[0], 'nombre_mp': i[1], 'cantidad_g': i[2],
             'precio_unitario': i[3], 'cantidad_recibida_g': i[4], 'lote_asignado': i[5]}
            for i in items
        ]
    })


@app.route('/api/recepcion/seguimiento')
def recepcion_seguimiento():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute(
        'SELECT numero_oc, fecha, estado, proveedor, categoria, '
        'COALESCE(valor_total,0), COALESCE(fecha_recepcion,""), '
        'COALESCE(observaciones_recepcion,""), COALESCE(tiene_discrepancias,0), '
        'COALESCE(fecha_pago,""), COALESCE(fecha_autorizacion,"") '
        "FROM ordenes_compra WHERE estado IN ('Autorizada','Recibida','Pagada','Parcial') "
        'ORDER BY fecha DESC LIMIT 200')
    rows = c.fetchall()
    conn.close()
    return jsonify([
        {'numero_oc': r[0], 'fecha': r[1], 'estado': r[2], 'proveedor': r[3],
         'categoria': r[4], 'valor_total': r[5], 'fecha_recepcion': r[6],
         'observaciones': r[7], 'tiene_discrepancias': r[8],
         'fecha_pago': r[9], 'fecha_autorizacion': r[10]}
        for r in rows
    ])


@app.route('/api/recepcion/lotes-cuarentena')
def recepcion_lotes_cuarentena():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT id, material_id, material_nombre, cantidad, lote,
                        fecha_vencimiento, proveedor, fecha, numero_oc
                 FROM movimientos
                 WHERE tipo='Entrada' AND (estado_lote='Cuarentena' OR (estado_lote IS NULL AND lote IS NOT NULL AND lote != ''))
                 ORDER BY fecha DESC LIMIT 100""")
    rows = c.fetchall()
    conn.close()
    cols = ['id','material_id','material_nombre','cantidad','lote','fecha_vencimiento','proveedor','fecha','numero_oc']
    return jsonify([dict(zip(cols, r)) for r in rows])


@app.route('/api/recepcion/aprobar-lote', methods=['POST'])
def recepcion_aprobar_lote():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.get_json() or {}
    mov_id = d.get('mov_id')
    nuevo_estado = d.get('estado', 'Aprobado')  # Aprobado o Rechazado
    if not mov_id:
        return jsonify({'error': 'mov_id requerido'}), 400
    usuario = session.get('compras_user', '')
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE movimientos SET estado_lote=?, operador=? WHERE id=?",
              (nuevo_estado, usuario, mov_id))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'estado': nuevo_estado})


@app.route('/api/recepcion/trazabilidad/<path:lote>')
def recepcion_trazabilidad_lote(lote):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT m.id, m.material_id, m.material_nombre, m.cantidad,
                        m.lote, m.fecha_vencimiento, m.proveedor, m.fecha,
                        m.estado_lote, m.numero_oc, m.operador
                 FROM movimientos m
                 WHERE m.lote=? ORDER BY m.fecha DESC""", (lote,))
    rows = c.fetchall()
    cols = ['id','material_id','material_nombre','cantidad','lote','fecha_vencimiento',
            'proveedor','fecha','estado_lote','numero_oc','operador']
    movs = [dict(zip(cols, r)) for r in rows]
    oc_info = None
    if movs and movs[0].get('numero_oc'):
        c.execute("SELECT numero_oc, fecha, proveedor, estado, valor_total, recibido_por FROM ordenes_compra WHERE numero_oc=?",
                  (movs[0]['numero_oc'],))
        oc_row = c.fetchone()
        if oc_row:
            oc_info = dict(zip(['numero_oc','fecha','proveedor','estado','valor_total','recibido_por'], oc_row))
    conn.close()
    return jsonify({'lote': lote, 'movimientos': movs, 'oc': oc_info})


# ─── Recursos Humanos ────────────────────────────────────────────────────────

@app.route("/rrhh")
def rrhh_panel():
    if "compras_user" not in session:
        return redirect("/login?next=/rrhh")
    usuario = session.get("compras_user","").capitalize()
    return Response(RRHH_HTML.replace("{usuario}", usuario), mimetype="text/html")


@app.route("/api/rrhh/dashboard")
def rrhh_dashboard():
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM empleados WHERE estado='Activo'")
    headcount = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(salario_base),0) FROM empleados WHERE estado='Activo'")
    nomina_bruta = c.fetchone()[0]
    mes_actual = datetime.now().strftime("%Y-%m")
    c.execute("SELECT COALESCE(SUM(dias),0) FROM ausencias WHERE estado='Aprobada' AND fecha_inicio LIKE ?", (mes_actual+"%",))
    dias_ausentes = c.fetchone()[0]
    ausentismo_pct = round(dias_ausentes/(headcount*22)*100,1) if headcount>0 else 0
    c.execute("SELECT COUNT(*) FROM capacitaciones_empleados WHERE completado=0")
    caps_pendientes = c.fetchone()[0]
    c.execute("SELECT empresa, COUNT(*) FROM empleados WHERE estado='Activo' GROUP BY empresa ORDER BY 2 DESC")
    por_empresa = [{"empresa":r[0],"count":r[1]} for r in c.fetchall()]
    c.execute("SELECT area, COUNT(*) FROM empleados WHERE estado='Activo' GROUP BY area ORDER BY 2 DESC")
    por_area = [{"area":r[0],"count":r[1]} for r in c.fetchall()]
    alertas = []
    from datetime import date as ddate
    c.execute("SELECT id, nombre||' '||apellido, fecha_ingreso FROM empleados WHERE estado='Activo'")
    for emp in c.fetchall():
        if emp[2]:
            try:
                fi = ddate.fromisoformat(emp[2])
                if (ddate.today()-fi).days > 365:
                    c.execute("SELECT COALESCE(SUM(dias),0) FROM ausencias WHERE tipo='Vacaciones' AND estado='Aprobada' AND empleado_id=?", (emp[0],))
                    vac = c.fetchone()[0]
                    if vac < 15:
                        alertas.append({"tipo":"warn","msg":emp[1]+" tiene "+str(15-vac)+" dias de vacaciones pendientes"})
            except: pass
    c.execute("SELECT nombre||' '||apellido, fecha_fin_contrato FROM empleados WHERE tipo_contrato='Fijo' AND fecha_fin_contrato!='' AND estado='Activo'")
    for r in c.fetchall():
        if r[1]:
            try:
                fv = ddate.fromisoformat(r[1])
                d_days = (fv-ddate.today()).days
                if 0 < d_days <= 45:
                    alertas.append({"tipo":"danger","msg":"Contrato de "+r[0]+" vence en "+str(d_days)+" dias"})
            except: pass
    conn.close()
    return jsonify({"headcount":headcount,"nomina_bruta":nomina_bruta,"ausentismo_pct":ausentismo_pct,"caps_pendientes":caps_pendientes,"por_empresa":por_empresa,"por_area":por_area,"alertas":alertas})


@app.route("/api/rrhh/empleados", methods=["GET","POST"])
def rrhh_empleados():
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == "POST":
        d = request.get_json(silent=True) or {}
        c.execute("SELECT COUNT(*) FROM empleados"); n = c.fetchone()[0]+1
        codigo = "EMP"+str(n).zfill(4)
        c.execute("INSERT INTO empleados (codigo,nombre,apellido,cedula,cargo,area,empresa,tipo_contrato,fecha_ingreso,estado,salario_base,eps,afp,arl,caja_compensacion,email,telefono,nivel_riesgo,observaciones) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (codigo,d.get("nombre",""),d.get("apellido",""),d.get("cedula",""),d.get("cargo",""),d.get("area",""),d.get("empresa","Espagiria"),d.get("tipo_contrato","Indefinido"),d.get("fecha_ingreso",""),"Activo",float(d.get("salario_base",0)),d.get("eps",""),d.get("afp",""),d.get("arl",""),d.get("caja",""),d.get("email",""),d.get("telefono",""),int(d.get("nivel_riesgo",1)),d.get("observaciones","")))
        conn.commit(); new_id=c.lastrowid; conn.close()
        return jsonify({"ok":True,"id":new_id,"codigo":codigo}),201
    c.execute("SELECT id,codigo,nombre,apellido,cargo,area,empresa,tipo_contrato,fecha_ingreso,estado,salario_base,email,telefono,eps,afp,nivel_riesgo FROM empleados ORDER BY empresa,nombre")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"codigo":r[1],"nombre":r[2],"apellido":r[3],"cargo":r[4],"area":r[5],"empresa":r[6],"tipo_contrato":r[7],"fecha_ingreso":r[8],"estado":r[9],"salario_base":r[10],"email":r[11],"telefono":r[12],"eps":r[13],"afp":r[14],"nivel_riesgo":r[15]} for r in rows])


@app.route("/api/rrhh/empleados/<int:eid>", methods=["GET","PUT"])
def rrhh_empleado_det(eid):
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == "PUT":
        d = request.get_json(silent=True) or {}
        c.execute("UPDATE empleados SET nombre=?,apellido=?,cargo=?,area=?,empresa=?,tipo_contrato=?,salario_base=?,eps=?,afp=?,arl=?,caja_compensacion=?,email=?,telefono=?,nivel_riesgo=?,observaciones=?,estado=? WHERE id=?",
                 (d.get("nombre",""),d.get("apellido",""),d.get("cargo",""),d.get("area",""),d.get("empresa",""),d.get("tipo_contrato",""),float(d.get("salario_base",0)),d.get("eps",""),d.get("afp",""),d.get("arl",""),d.get("caja",""),d.get("email",""),d.get("telefono",""),int(d.get("nivel_riesgo",1)),d.get("observaciones",""),d.get("estado","Activo"),eid))
        conn.commit(); conn.close(); return jsonify({"ok":True})
    c.execute("SELECT * FROM empleados WHERE id=?", (eid,))
    r=c.fetchone()
    if not r: conn.close(); return jsonify({"error":"not found"}),404
    cols=[d[0] for d in c.description]; conn.close()
    return jsonify(dict(zip(cols,r)))


@app.route("/api/rrhh/nomina/<periodo>")
def rrhh_nomina(periodo):
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    SMMLV=1423500; AUX=202000
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    c.execute("SELECT id,nombre,apellido,cargo,salario_base,empresa,area,nivel_riesgo FROM empleados WHERE estado='Activo' ORDER BY empresa,nombre")
    emps=c.fetchall()
    c.execute("SELECT empleado_id,dias_trabajados,horas_extras,valor_horas_extras,bonificaciones,otros_descuentos FROM nomina_registros WHERE periodo=?", (periodo,))
    ex={r[0]:r for r in c.fetchall()}; conn.close()
    result=[]
    arl_rates={1:0.00522,2:0.01044,3:0.02436,4:0.04350,5:0.06960}
    for e in emps:
        eid,nom,ape,cargo,sal,emp,area,riesgo=e
        xr=ex.get(eid)
        dias=xr[1] if xr else 30; he=xr[2] if xr else 0; vhe=xr[3] if xr else 0
        bonos=xr[4] if xr else 0; otros=xr[5] if xr else 0
        aux=AUX if sal<=2*SMMLV else 0
        desc_salud=round(sal*0.04); desc_pension=round(sal*0.04)
        neto=sal+aux+vhe+bonos-desc_salud-desc_pension-otros
        ap_s=round(sal*0.085); ap_p=round(sal*0.12)
        ap_arl=round(sal*arl_rates.get(riesgo,0.00522))
        ap_sena=round(sal*0.02); ap_icbf=round(sal*0.03); ap_caja=round(sal*0.04)
        ap_tot=ap_s+ap_p+ap_arl+ap_sena+ap_icbf+ap_caja
        result.append({"id":eid,"nombre":nom+" "+ape,"cargo":cargo,"empresa":emp,"area":area,"salario_base":sal,"dias_trabajados":dias,"aux_transporte":aux,"horas_extras":he,"valor_horas_extras":vhe,"bonificaciones":bonos,"desc_salud":desc_salud,"desc_pension":desc_pension,"otros_descuentos":otros,"neto":neto,"aportes_empleador":{"salud":ap_s,"pension":ap_p,"arl":ap_arl,"sena":ap_sena,"icbf":ap_icbf,"caja":ap_caja,"total":ap_tot}})
    return jsonify(result)


@app.route("/api/rrhh/nomina/guardar", methods=["POST"])
def rrhh_nomina_guardar():
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    d=request.get_json(silent=True) or {}
    periodo=d.get("periodo",""); registros=d.get("registros",[])
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    for r in registros:
        c.execute("INSERT OR REPLACE INTO nomina_registros (periodo,empleado_id,salario_base,dias_trabajados,horas_extras,valor_horas_extras,subsidio_transporte,bonificaciones,descuento_salud,descuento_pension,otros_descuentos,salario_neto,estado) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (periodo,r["id"],r["salario_base"],r.get("dias_trabajados",30),r.get("horas_extras",0),r.get("valor_horas_extras",0),r.get("aux_transporte",0),r.get("bonificaciones",0),r["desc_salud"],r["desc_pension"],r.get("otros_descuentos",0),r["neto"],"Generada"))
    conn.commit(); conn.close()
    return jsonify({"ok":True,"periodo":periodo,"registros":len(registros)})


@app.route("/api/rrhh/ausencias", methods=["GET","POST"])
def rrhh_ausencias():
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    if request.method=="POST":
        d=request.get_json(silent=True) or {}
        c.execute("INSERT INTO ausencias (empleado_id,tipo,fecha_inicio,fecha_fin,dias,estado,observaciones) VALUES (?,?,?,?,?,'Pendiente',?)",
                 (int(d.get("empleado_id",0)),d.get("tipo","Vacaciones"),d.get("fecha_inicio",""),d.get("fecha_fin",""),int(d.get("dias",0)),d.get("observaciones","")))
        conn.commit(); conn.close(); return jsonify({"ok":True}),201
    c.execute("SELECT a.id,e.nombre||' '||e.apellido,a.tipo,a.fecha_inicio,a.fecha_fin,a.dias,a.estado,a.observaciones,a.aprobado_por FROM ausencias a JOIN empleados e ON a.empleado_id=e.id ORDER BY a.creado_en DESC LIMIT 200")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"empleado":r[1],"tipo":r[2],"fecha_inicio":r[3],"fecha_fin":r[4],"dias":r[5],"estado":r[6],"observaciones":r[7],"aprobado_por":r[8]} for r in rows])


@app.route("/api/rrhh/ausencias/<int:aid>", methods=["PATCH"])
def rrhh_ausencia_upd(aid):
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    d=request.get_json(silent=True) or {}
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    c.execute("UPDATE ausencias SET estado=?,aprobado_por=? WHERE id=?", (d.get("estado",""),session.get("compras_user",""),aid))
    conn.commit(); conn.close(); return jsonify({"ok":True})


@app.route("/api/rrhh/capacitaciones", methods=["GET","POST"])
def rrhh_caps():
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    if request.method=="POST":
        d=request.get_json(silent=True) or {}
        c.execute("INSERT INTO capacitaciones (nombre,tipo,fecha,duracion_horas,instructor,empresa,obligatoria) VALUES (?,?,?,?,?,?,?)",
                 (d.get("nombre",""),d.get("tipo","BPM"),d.get("fecha",""),float(d.get("duracion_horas",1)),d.get("instructor",""),d.get("empresa","Espagiria"),1 if d.get("obligatoria") else 0))
        cap_id=c.lastrowid
        c.execute("SELECT id FROM empleados WHERE estado='Activo'")
        for emp in c.fetchall():
            try: c.execute("INSERT OR IGNORE INTO capacitaciones_empleados (capacitacion_id,empleado_id,completado) VALUES (?,?,0)", (cap_id,emp[0]))
            except: pass
        conn.commit(); conn.close(); return jsonify({"ok":True,"id":cap_id}),201
    c.execute("SELECT c.id,c.nombre,c.tipo,c.fecha,c.duracion_horas,c.instructor,c.obligatoria,COUNT(ce.id),COALESCE(SUM(ce.completado),0) FROM capacitaciones c LEFT JOIN capacitaciones_empleados ce ON c.id=ce.capacitacion_id GROUP BY c.id ORDER BY c.fecha DESC")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"nombre":r[1],"tipo":r[2],"fecha":r[3],"horas":r[4],"instructor":r[5],"obligatoria":r[6],"total":r[7],"completados":r[8]} for r in rows])


@app.route("/api/rrhh/evaluaciones", methods=["GET","POST"])
def rrhh_evals():
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    if request.method=="POST":
        d=request.get_json(silent=True) or {}
        scores=[float(d.get(k,0)) for k in ["calidad","asistencia","actitud","conocimiento","productividad"]]
        total=round(sum(scores)/5,1)
        c.execute("INSERT INTO evaluaciones (empleado_id,periodo,evaluador,puntaje_total,puntaje_calidad,puntaje_asistencia,puntaje_actitud,puntaje_conocimiento,puntaje_productividad,comentarios,estado) VALUES (?,?,?,?,?,?,?,?,?,?,'Publicada')",
                 (int(d.get("empleado_id",0)),d.get("periodo",""),session.get("compras_user",""),total,scores[0],scores[1],scores[2],scores[3],scores[4],d.get("comentarios","")))
        conn.commit(); conn.close(); return jsonify({"ok":True}),201
    periodo=request.args.get("periodo","")
    q="SELECT ev.id,e.nombre||' '||e.apellido,e.cargo,ev.periodo,ev.evaluador,ev.puntaje_total,ev.puntaje_calidad,ev.puntaje_asistencia,ev.puntaje_actitud,ev.puntaje_conocimiento,ev.puntaje_productividad,ev.comentarios FROM evaluaciones ev JOIN empleados e ON ev.empleado_id=e.id"
    if periodo: c.execute(q+" WHERE ev.periodo=? ORDER BY ev.puntaje_total DESC",(periodo,))
    else: c.execute(q+" ORDER BY ev.periodo DESC,ev.puntaje_total DESC LIMIT 50")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"empleado":r[1],"cargo":r[2],"periodo":r[3],"evaluador":r[4],"total":r[5],"calidad":r[6],"asistencia":r[7],"actitud":r[8],"conocimiento":r[9],"productividad":r[10],"comentarios":r[11]} for r in rows])


@app.route("/api/rrhh/sgsst", methods=["GET","POST"])
def rrhh_sgsst():
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    if request.method=="POST":
        d=request.get_json(silent=True) or {}
        c.execute("INSERT INTO sgsst_items (categoria,descripcion,frecuencia,responsable,proximo_vencimiento,estado) VALUES (?,?,?,?,?,'Pendiente')",
                 (d.get("categoria",""),d.get("descripcion",""),d.get("frecuencia","Anual"),d.get("responsable",""),d.get("proximo_vencimiento","")))
        conn.commit(); conn.close(); return jsonify({"ok":True}),201
    c.execute("SELECT id,categoria,descripcion,frecuencia,ultimo_cumplimiento,proximo_vencimiento,responsable,estado FROM sgsst_items ORDER BY categoria,descripcion")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"categoria":r[1],"descripcion":r[2],"frecuencia":r[3],"ultimo":r[4],"proximo":r[5],"responsable":r[6],"estado":r[7]} for r in rows])


@app.route("/api/rrhh/sgsst/<int:sid>", methods=["PATCH"])
def rrhh_sgsst_upd(sid):
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    d=request.get_json(silent=True) or {}
    from datetime import date as ddate, timedelta
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    c.execute("SELECT frecuencia FROM sgsst_items WHERE id=?", (sid,))
    row=c.fetchone(); hoy=ddate.today().isoformat()
    freq_days={"Mensual":30,"Trimestral":90,"Semestral":180,"Anual":365}
    prox=d.get("proximo_vencimiento","") or (ddate.today()+timedelta(days=freq_days.get(row[0] if row else "Anual",365))).isoformat()
    c.execute("UPDATE sgsst_items SET estado='Cumplido',ultimo_cumplimiento=?,proximo_vencimiento=? WHERE id=?", (hoy,prox,sid))
    conn.commit(); conn.close(); return jsonify({"ok":True})

# ═══════════════════════════════════════════════════════
#  CALIDAD BPM — Página + API
# ═══════════════════════════════════════════════════════
@app.route('/calidad')
def calidad_page():
    if 'compras_user' not in session:
        return redirect('/login?next=/calidad')
    return Response(CALIDAD_HTML, mimetype='text/html')


@app.route('/api/calidad/dashboard')
def calidad_dashboard():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # Lotes en cuarentena
    c.execute("""SELECT COUNT(*) FROM movimientos
                 WHERE tipo='Entrada' AND (estado_lote='Cuarentena'
                 OR (estado_lote IS NULL AND lote IS NOT NULL AND lote != ''))""")
    cuarentena = c.fetchone()[0]
    # Aprobados y rechazados últimos 30d
    c.execute("""SELECT COUNT(*) FROM movimientos
                 WHERE estado_lote='Aprobado'
                 AND fecha >= date('now','-30 days')""")
    aprobados = c.fetchone()[0]
    c.execute("""SELECT COUNT(*) FROM movimientos
                 WHERE estado_lote='Rechazado'
                 AND fecha >= date('now','-30 days')""")
    rechazados = c.fetchone()[0]
    # NC abiertas
    c.execute("SELECT COUNT(*) FROM no_conformidades WHERE estado='Abierta'")
    nc_abiertas = c.fetchone()[0]
    # Calibraciones vencidas
    hoy = datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT COUNT(*) FROM calibraciones_instrumentos WHERE fecha_proxima < ? OR estado='Vencida'", (hoy,))
    cals_vencidas = c.fetchone()[0]
    # Actividad reciente: últimas NC + últimas acciones CC
    actividad = []
    c.execute("""SELECT 'NC' as tipo, descripcion, area, fecha, estado, impacto
                 FROM no_conformidades ORDER BY id DESC LIMIT 5""")
    for r in c.fetchall():
        color = 'rojo' if r[5] in ('Alto','Critico') else 'amari'
        actividad.append({'titulo': f'NC #{r[0]}: {r[1][:60]}' if False else f'NC — {r[1][:55]}',
                          'subtitulo': f'{r[2]} · {r[4]}', 'fecha': r[3], 'color': color})
    c.execute("""SELECT material_nombre, lote, estado_lote, fecha
                 FROM movimientos WHERE tipo='Entrada'
                 AND estado_lote IN ('Aprobado','Rechazado')
                 ORDER BY id DESC LIMIT 5""")
    for r in c.fetchall():
        color = 'verde' if r[2] == 'Aprobado' else 'rojo'
        actividad.append({'titulo': f'Lote {r[1] or "s/n"} — {r[2]}',
                          'subtitulo': r[0][:50], 'fecha': r[3], 'color': color})
    actividad.sort(key=lambda x: x.get('fecha','') or '', reverse=True)
    conn.close()
    return jsonify({
        'cuarentena': cuarentena,
        'aprobados': aprobados,
        'rechazados': rechazados,
        'nc_abiertas': nc_abiertas,
        'cals_vencidas': cals_vencidas,
        'actividad_reciente': actividad[:8]
    })


@app.route('/api/calidad/no-conformidades', methods=['GET', 'POST'])
def handle_no_conformidades():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        desc = (d.get('descripcion') or '').strip()
        if not desc:
            conn.close(); return jsonify({'error': 'descripcion requerida'}), 400
        c.execute("""INSERT INTO no_conformidades
                     (fecha,tipo,descripcion,area,responsable,lote,codigo_mp,
                      impacto,accion_correctiva,estado,creado_por)
                     VALUES (date('now'),?,?,?,?,?,?,?,?,'Abierta',?)""",
                  (d.get('tipo','Proceso'), desc,
                   d.get('area',''), d.get('responsable',''),
                   d.get('lote',''), d.get('codigo_mp',''),
                   d.get('impacto','Bajo'), d.get('accion_correctiva',''),
                   session.get('compras_user','')))
        conn.commit(); new_id = c.lastrowid; conn.close()
        return jsonify({'id': new_id}), 201
    # GET
    c.execute("""SELECT id,fecha,tipo,descripcion,area,responsable,lote,codigo_mp,
                        impacto,accion_correctiva,estado,fecha_cierre,cerrado_por,creado_por
                 FROM no_conformidades ORDER BY id DESC LIMIT 200""")
    cols = ['id','fecha','tipo','descripcion','area','responsable','lote','codigo_mp',
            'impacto','accion_correctiva','estado','fecha_cierre','cerrado_por','creado_por']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close(); return jsonify(rows)


@app.route('/api/calidad/no-conformidades/<int:ncid>/cerrar', methods=['POST'])
def cerrar_no_conformidad(ncid):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""UPDATE no_conformidades
                 SET estado='Cerrada', fecha_cierre=date('now'), cerrado_por=?
                 WHERE id=?""",
              (session.get('compras_user',''), ncid))
    conn.commit(); conn.close()
    return jsonify({'ok': True})


@app.route('/api/calidad/calibraciones')
def get_calibraciones():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    hoy = datetime.now().strftime('%Y-%m-%d')
    # Auto-update estado based on fecha_proxima
    c.execute("""UPDATE calibraciones_instrumentos
                 SET estado='Vencida' WHERE fecha_proxima < ? AND estado='Vigente'""", (hoy,))
    conn.commit()
    c.execute("""SELECT id,instrumento,codigo,ubicacion,fecha_ultima,fecha_proxima,
                        responsable,empresa,estado,certificado,observaciones
                 FROM calibraciones_instrumentos
                 ORDER BY CASE estado WHEN 'Vencida' THEN 0 ELSE 1 END, fecha_proxima ASC""")
    cols = ['id','instrumento','codigo','ubicacion','fecha_ultima','fecha_proxima',
            'responsable','empresa','estado','certificado','observaciones']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close(); return jsonify(rows)


@app.errorhandler(404)
def not_found(e):
    h = '<html><body style="background:#0d1117;color:#fff;font-family:sans-serif;text-align:center;padding-top:10vh"><h1>404</h1><p>Pagina no encontrada.</p><a href="/compras" style="color:#7ACFCC;">Volver</a></body></html>'
    return Response(h, status=404, mimetype='text/html')

@app.errorhandler(500)
def server_error(e):
    h = '<html><body style="background:#0d1117;color:#fff;font-family:sans-serif;text-align:center;padding-top:10vh"><h1>500</h1><p>Error interno del servidor.</p><a href="/compras" style="color:#7ACFCC;">Volver</a></body></html>'
    return Response(h, status=500, mimetype='text/html')

if __name__ == '__main__':

    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
