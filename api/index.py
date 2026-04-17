import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, request, Response, session, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'hha-group-2026-secretkey-x9kq')
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

    conn.commit()
    conn.close()

init_db()

# ─── HUB HHA GROUP ────────────────────────────────────────────
HUB_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>HHA Group — Portal Interno</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#F5F4F0;min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:50px 20px;}
.logo-wrap{text-align:center;margin-bottom:52px;}
.logo-badge{display:inline-block;background:#2B7A78;border-radius:16px;padding:16px 40px;margin-bottom:14px;box-shadow:0 4px 20px rgba(43,122,120,0.25);}
.logo-text{font-size:2.2em;font-weight:900;color:white;letter-spacing:6px;text-transform:uppercase;}
.logo-sub{color:#7A9E9C;font-size:0.82em;letter-spacing:3px;text-transform:uppercase;margin-top:6px;}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:20px;max-width:1080px;width:100%;}
.card{background:#fff;border:1px solid #DDE8E8;border-radius:14px;padding:32px 26px;text-decoration:none;display:block;position:relative;overflow:hidden;transition:all 0.25s ease;}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--c);border-radius:14px 14px 0 0;}
.card:hover:not(.disabled){transform:translateY(-4px);border-color:var(--c);box-shadow:0 12px 32px rgba(43,122,120,0.12);}
.card.disabled{opacity:0.4;cursor:not-allowed;pointer-events:none;}
.card-icon{font-size:2.4em;margin-bottom:16px;display:block;}
.card-title{font-size:1.25em;font-weight:700;color:#1C2B30;margin-bottom:4px;}
.card-co{font-size:0.72em;color:var(--c);text-transform:uppercase;letter-spacing:1.5px;font-weight:700;margin-bottom:12px;}
.card-desc{font-size:0.87em;color:#5C7A7A;line-height:1.65;margin-bottom:20px;}
.badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:0.72em;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;}
.badge-on{background:rgba(43,122,120,.1);color:#2B7A78;}
.badge-lock{background:rgba(180,148,60,.1);color:#B5924A;}
.badge-soon{background:#F0EEEA;color:#9C8B7A;}
.badge-open{background:#d1fae5;color:#065f46;}
.c-inv{--c:#2B7A78;}.c-buy{--c:#B5924A;}.c-trz{--c:#4A8B6A;}.c-sol{--c:#7A4A8B;}
.footer{margin-top:52px;color:#9C8B7A;font-size:0.78em;text-align:center;border-top:1px solid #E8E4DE;width:100%;max-width:1080px;padding-top:20px;}
.credit{margin-top:6px;color:#B5A898;font-size:0.72em;text-align:center;}
</style>
</head>
<body>
<div class="logo-wrap">
  <div class="logo-badge">
    <div class="logo-text">HHA Group</div>
    <div style="font-size:0.7em;font-weight:400;letter-spacing:2px;opacity:0.85;margin-top:5px;">TRANSFORMAMOS CIENCIA EN CUIDADO</div>
  </div>
  <div class="logo-sub" style="margin-bottom:22px;">Sistema Operativo Interno</div>
  <div style="display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin-bottom:8px;">
    <div style="background:#fff;border:1px solid #DDE8E8;border-radius:12px;padding:14px 28px;text-align:center;box-shadow:0 2px 8px rgba(43,122,120,0.07);min-width:180px;">
      <div style="font-weight:800;font-size:0.95em;color:#1C2B30;letter-spacing:2px;">ÁNIMUS LAB</div>
      <div style="font-size:0.72em;color:#7A9E9C;letter-spacing:1px;margin-top:3px;">Autocuidado consciente</div>
    </div>
    <div style="background:#fff;border:1px solid #DDE8E8;border-radius:12px;padding:14px 28px;text-align:center;box-shadow:0 2px 8px rgba(43,122,120,0.07);min-width:180px;">
      <div style="font-weight:800;font-size:0.95em;color:#1C2B30;letter-spacing:2px;">ESPAGIRIA</div>
      <div style="font-size:0.72em;color:#7A9E9C;letter-spacing:1px;margin-top:3px;">Ciencia que crea</div>
    </div>
  </div>
</div>
<div class="grid">
  <a href="/inventarios" class="card c-inv">
    <span class="card-icon">📦</span>
    <div class="card-title">Inventarios</div>
    <div class="card-co">Espagiria Laboratorios</div>
    <div class="card-desc">Control de stock, recepción por lotes, FEFO, alertas de reabastecimiento y órdenes de compra automáticas.</div>
    <span class="badge badge-on">● Activo</span>
  </a>
  <a href="/compras" class="card c-buy">
    <span class="card-icon">🛒</span>
    <div class="card-title">Compras</div>
    <div class="card-co">HHA Group</div>
    <div class="card-desc">Gestión de órdenes de compra, proveedores, aprobaciones y seguimiento de pedidos. Acceso restringido.</div>
    <span class="badge badge-lock">🔒 Acceso restringido</span>
  </a>
  <a href="#" class="card c-trz disabled">
    <span class="card-icon">🔬</span>
    <div class="card-title">Trazabilidad</div>
    <div class="card-co">Espagiria Laboratorios</div>
    <div class="card-desc">Registro de qué lotes de materias primas se usaron en cada producción. Cumplimiento BPM.</div>
    <span class="badge badge-soon">Próximamente</span>
  </a>
  <a href="/solicitudes" class="card c-sol">
    <span class="card-icon">📋</span>
    <div class="card-title">Solicitudes</div>
    <div class="card-co">HHA Group</div>
    <div class="card-desc">Solicitudes de compra del equipo. Crea y haz seguimiento de tus pedidos internos.</div>
    <span class="badge badge-open">Abierto</span>
  </a>
</div>
<div class="footer">HHA Group © 2026 · Sistema interno de operaciones</div>
<div class="credit">Diseñado y desarrollado por <strong>Sebastián Vargas Isaza</strong></div>
</body>
</html>"""

# ─── LOGIN COMPRAS ────────────────────────────────────────────
LOGIN_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>HHA Group — Acceso Compras</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#0f172a;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;}
.card{background:#1e293b;border:1px solid #334155;border-radius:20px;padding:48px 40px;width:100%;max-width:420px;}
.logo{text-align:center;margin-bottom:36px;}
.logo-badge{display:inline-block;background:linear-gradient(135deg,#f59e0b,#ef4444);border-radius:12px;padding:10px 28px;margin-bottom:14px;}
.logo-text{font-size:1.5em;font-weight:900;color:white;letter-spacing:4px;}
.logo-mod{color:#f59e0b;font-weight:700;font-size:1.05em;margin-bottom:4px;}
.logo-sub{color:#64748b;font-size:0.82em;}
label{display:block;color:#94a3b8;font-size:0.8em;font-weight:700;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;}
.fg{margin-bottom:20px;}
input[type=text],input[type=password]{width:100%;background:#0f172a;border:1px solid #334155;border-radius:10px;padding:14px 16px;color:white;font-size:1em;outline:none;}
.btn{width:100%;background:linear-gradient(135deg,#f59e0b,#ef4444);color:white;border:none;border-radius:10px;padding:14px;font-size:1em;font-weight:700;cursor:pointer;margin-top:8px;}
.err{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:#f87171;padding:12px 16px;border-radius:8px;font-size:0.88em;margin-bottom:20px;text-align:center;}
.back{text-align:center;margin-top:24px;}
.back a{color:#475569;font-size:0.83em;text-decoration:none;}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <div class="logo-badge"><div class="logo-text">HHA</div></div>
    <div class="logo-mod">Módulo de Compras</div>
    <div class="logo-sub">Solo acceso autorizado</div>
  </div>
  {error}
  <form method="POST" action="/login">
    <div class="fg"><label>Usuario</label><input type="text" name="username" placeholder="Ej: Sebastian, Catalina..." required autofocus autocomplete="username"></div>
    <div class="fg"><label>Contraseña</label><input type="password" name="password" placeholder="••••••••" required></div>
    <button type="submit" class="btn">Ingresar al sistema →</button>
  </form>
  <div style="text-align:center;color:#475569;font-size:0.78em;margin-top:12px;margin-bottom:4px;">Usuarios: Sebastian · Alejandro · Catalina · Luz · Mayra</div>
  <div class="back"><a href="/">← Volver al portal HHA Group</a></div>
</div>
</body>
</html>"""

# ─── MÓDULO COMPRAS ───────────────────────────────────────────
COMPRAS_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Compras — HHA Group</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#FAF8F5;color:#1C1917;min-height:100vh;}
.topbar{background:#fff;border-bottom:1px solid #E8E4DE;padding:0 32px;display:flex;align-items:center;justify-content:space-between;height:56px;position:sticky;top:0;z-index:100;}
.brand{display:flex;align-items:center;gap:10px;}
.brand-dot{width:10px;height:10px;background:#4A6741;border-radius:50%;}
.brand-name{font-weight:700;font-size:1em;color:#1C1917;}
.brand-mod{font-size:0.78em;color:#9C8B7A;margin-left:4px;}
.topbar-right{display:flex;align-items:center;gap:16px;}
.user-chip{background:#FAF8F5;border:1px solid #E8E4DE;padding:5px 14px;border-radius:20px;font-size:0.82em;color:#4A6741;font-weight:600;}
.btn-logout{background:none;border:none;color:#9C8B7A;font-size:0.82em;cursor:pointer;text-decoration:underline;}
.nav{display:flex;border-bottom:1px solid #E8E4DE;background:#fff;padding:0 32px;overflow-x:auto;}
.nav-btn{padding:14px 20px;background:none;border:none;border-bottom:2px solid transparent;cursor:pointer;font-size:0.88em;font-weight:500;color:#9C8B7A;white-space:nowrap;transition:all 0.2s;}
.nav-btn:hover{color:#1C1917;}
.nav-btn.active{color:#4A6741;border-bottom-color:#4A6741;font-weight:700;}
.page{display:none;padding:28px 32px;max-width:1200px;margin:0 auto;}
.page.active{display:block;}
h2{font-size:1.2em;font-weight:700;margin-bottom:4px;}
.page-sub{color:#9C8B7A;font-size:0.85em;margin-bottom:24px;}
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:28px;}
.kpi{background:#fff;border:1px solid #E8E4DE;border-radius:10px;padding:18px 20px;}
.kpi-label{font-size:0.75em;color:#9C8B7A;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;}
.kpi-val{font-size:1.7em;font-weight:700;}
.kpi-val.green{color:#4A6741;}.kpi-val.gold{color:#B5924A;}.kpi-val.red{color:#B54A4A;}
.card{background:#fff;border:1px solid #E8E4DE;border-radius:10px;padding:22px;margin-bottom:16px;}
.card-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;}
.btn{background:#4A6741;color:#fff;border:none;border-radius:7px;padding:9px 18px;font-size:0.88em;font-weight:600;cursor:pointer;}
.btn:hover{opacity:0.85;}
.btn-gold{background:#B5924A;}
.btn-ghost{background:none;border:1px solid #E8E4DE;color:#1C1917;}
.btn-ghost:hover{background:#FAF8F5;}
.btn-sm{padding:5px 12px;font-size:0.8em;}
.btn-danger{background:#B54A4A;}
table{width:100%;border-collapse:collapse;font-size:0.87em;}
th{background:#FAF8F5;color:#9C8B7A;font-weight:600;font-size:0.78em;text-transform:uppercase;letter-spacing:0.4px;padding:10px 12px;text-align:left;border-bottom:1px solid #E8E4DE;}
td{padding:11px 12px;border-bottom:1px solid #F0EDE8;}
tr:hover td{background:#FDFCFB;}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:0.75em;font-weight:600;}
.badge-pend{background:#FFF3E0;color:#B5924A;}.badge-aprov{background:#E8F5E9;color:#4A6741;}
.badge-env{background:#E3F2FD;color:#1565C0;}.badge-rec{background:#E8F5E9;color:#2E7D32;}
.badge-rech{background:#FFEBEE;color:#B54A4A;}.badge-bor{background:#F5F5F5;color:#9C8B7A;}
label{font-size:0.82em;font-weight:600;display:block;margin-bottom:4px;}
input,select,textarea{width:100%;padding:9px 12px;border:1px solid #E8E4DE;border-radius:7px;font-size:0.9em;color:#1C1917;background:#fff;outline:none;}
input:focus,select:focus{border-color:#4A6741;}
.fg{margin-bottom:14px;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;}
.msg-ok{background:#E8F5E9;color:#2E7D32;padding:10px 14px;border-radius:7px;font-size:0.87em;margin-top:10px;}
.msg-err{background:#FFEBEE;color:#B54A4A;padding:10px 14px;border-radius:7px;font-size:0.87em;margin-top:10px;}
.empty{text-align:center;color:#9C8B7A;padding:32px;font-size:0.9em;}
.divider{height:1px;background:#E8E4DE;margin:20px 0;}
.footer-credit{text-align:center;color:#C5BDB5;font-size:0.75em;padding:24px 0 16px;}
.footer-credit a{color:#B5924A;text-decoration:none;}
</style>
</head>
<body>
<div class="topbar">
  <div class="brand"><div class="brand-dot"></div><span class="brand-name">HHA Group <span class="brand-mod">/ Compras</span></span></div>
  <div class="topbar-right">
    <span class="user-chip" id="user-label">...</span>
    <a href="/" style="font-size:0.82em;color:#9C8B7A;text-decoration:none;margin-right:8px;">← HHA</a>
    <button class="btn-logout" onclick="location.href='/logout'">Cerrar sesión</button>
  </div>
</div>
<div class="nav">
  <button class="nav-btn active" onclick="goTo('dashboard',this)">Dashboard</button>
  <button class="nav-btn" onclick="goTo('alertas',this)">Alertas de compra</button>
  <button class="nav-btn" onclick="goTo('ordenes',this)">Órdenes de compra</button>
  <button class="nav-btn" onclick="goTo('solicitudes',this)">Solicitudes</button>
  <button class="nav-btn" onclick="goTo('proveedores',this)">Proveedores</button>
</div>

<div id="dashboard" class="page active">
  <h2>Resumen de Compras</h2><p class="page-sub">Estado actual del módulo de compras HHA Group</p>
  <div class="kpi-row">
    <div class="kpi"><div class="kpi-label">MPs bajo mínimo</div><div class="kpi-val red" id="k-alertas">—</div></div>
    <div class="kpi"><div class="kpi-label">OCs pendientes</div><div class="kpi-val gold" id="k-oc-pend">—</div></div>
    <div class="kpi"><div class="kpi-label">OCs en tránsito</div><div class="kpi-val" id="k-oc-trans">—</div></div>
    <div class="kpi"><div class="kpi-label">Solicitudes pendientes</div><div class="kpi-val" id="k-sol-pend">—</div></div>
    <div class="kpi"><div class="kpi-label">Proveedores activos</div><div class="kpi-val green" id="k-provs">—</div></div>
  </div>
  <div class="card">
    <div class="card-head"><strong>Órdenes recientes</strong><button class="btn btn-sm" onclick="goTo('ordenes',document.querySelectorAll('.nav-btn')[2])">Ver todas</button></div>
    <table><thead><tr><th>Número OC</th><th>Proveedor</th><th>Fecha</th><th>Estado</th><th>Acción</th></tr></thead>
    <tbody id="dash-oc-body"><tr><td colspan="5" class="empty">Cargando...</td></tr></tbody></table>
  </div>
  <div class="card">
    <div class="card-head"><strong>Solicitudes recientes</strong><button class="btn btn-sm btn-ghost" onclick="goTo('solicitudes',document.querySelectorAll('.nav-btn')[3])">Ver todas</button></div>
    <table><thead><tr><th>Número</th><th>Solicitante</th><th>Fecha</th><th>Urgencia</th><th>Estado</th></tr></thead>
    <tbody id="dash-sol-body"><tr><td colspan="5" class="empty">Cargando...</td></tr></tbody></table>
  </div>
</div>

<div id="alertas" class="page">
  <h2>Alertas de reabastecimiento</h2><p class="page-sub">Materias primas bajo stock mínimo</p>
  <div style="display:flex;gap:10px;margin-bottom:20px;">
    <button class="btn" onclick="generarOCAutomatica()">⚡ Generar OCs automáticas</button>
    <button class="btn btn-ghost" onclick="loadAlertas()">↻ Actualizar</button>
  </div>
  <div id="alertas-msg"></div>
  <div class="card" style="padding:0;overflow:hidden;">
    <table><thead><tr><th>Código</th><th>Materia Prima</th><th>Proveedor</th><th>Stock mín.</th><th>Stock actual</th><th>Déficit</th><th>Nivel</th></tr></thead>
    <tbody id="alertas-body"><tr><td colspan="7" class="empty">Cargando...</td></tr></tbody></table>
  </div>
</div>

<div id="ordenes" class="page">
  <h2>Órdenes de Compra</h2><p class="page-sub">Gestión completa de órdenes</p>
  <div style="display:flex;gap:10px;margin-bottom:20px;">
    <button class="btn" onclick="showFormOC()">+ Nueva OC</button>
    <button class="btn btn-ghost" onclick="loadOCs()">↻ Actualizar</button>
  </div>
  <div id="form-oc" style="display:none;" class="card">
    <div class="card-head"><strong>Nueva Orden de Compra</strong><button class="btn btn-ghost btn-sm" onclick="document.getElementById('form-oc').style.display='none'">✕</button></div>
    <div class="grid2">
      <div class="fg"><label>Proveedor *</label><input type="text" id="oc-prov" placeholder="Nombre del proveedor"></div>
      <div class="fg"><label>Fecha entrega estimada</label><input type="date" id="oc-fecha-ent"></div>
    </div>
    <div class="fg"><label>Observaciones</label><textarea id="oc-obs" rows="2" placeholder="Condiciones, notas..."></textarea></div>
    <div class="divider"></div>
    <strong style="font-size:0.88em;">Items</strong>
    <div style="margin-top:12px;">
      <div class="grid3" style="margin-bottom:8px;font-size:0.78em;font-weight:700;color:#9C8B7A;text-transform:uppercase;"><span>Código MP</span><span>Cantidad (g)</span><span>Precio unit. ($)</span></div>
      <div id="oc-items-list">
        <div class="grid3 oc-item-row" style="margin-bottom:8px;"><input type="text" class="oc-cod" placeholder="MP00001"><input type="number" class="oc-cant" placeholder="0" step="0.01"><input type="number" class="oc-precio" placeholder="0" step="0.01"></div>
      </div>
      <button class="btn btn-ghost btn-sm" onclick="addItemOC()">+ Agregar ítem</button>
    </div>
    <div style="margin-top:16px;display:flex;gap:10px;">
      <button class="btn" onclick="crearOC()">Guardar OC</button>
      <button class="btn btn-ghost" onclick="document.getElementById('form-oc').style.display='none'">Cancelar</button>
    </div>
    <div id="oc-msg"></div>
  </div>
  <div class="card" style="padding:0;overflow:hidden;">
    <table><thead><tr><th>Número OC</th><th>Proveedor</th><th>Fecha</th><th>Entrega est.</th><th>Estado</th><th>Items</th><th>Acción</th></tr></thead>
    <tbody id="oc-body"><tr><td colspan="7" class="empty">Cargando...</td></tr></tbody></table>
  </div>
</div>

<div id="solicitudes" class="page">
  <h2>Solicitudes de Compra</h2><p class="page-sub">Solicitudes del equipo pendientes de aprobación</p>
  <div style="margin-bottom:20px;"><button class="btn btn-ghost" onclick="loadSolicitudes()">↻ Actualizar</button></div>
  <div class="card" style="padding:0;overflow:hidden;">
    <table><thead><tr><th>Número</th><th>Solicitante</th><th>Fecha</th><th>Urgencia</th><th>Estado</th><th>Acción</th></tr></thead>
    <tbody id="sol-body"><tr><td colspan="6" class="empty">Cargando...</td></tr></tbody></table>
  </div>
</div>

<div id="proveedores" class="page">
  <h2>Proveedores</h2><p class="page-sub">Directorio de proveedores activos</p>
  <div style="display:flex;gap:10px;margin-bottom:20px;">
    <button class="btn" onclick="showFormProv()">+ Nuevo proveedor</button>
    <button class="btn btn-ghost" onclick="loadProveedores()">↻ Actualizar</button>
  </div>
  <div id="form-prov" style="display:none;" class="card">
    <div class="card-head"><strong>Nuevo Proveedor</strong><button class="btn btn-ghost btn-sm" onclick="document.getElementById('form-prov').style.display='none'">✕</button></div>
    <div class="grid2">
      <div class="fg"><label>Nombre *</label><input type="text" id="p-nombre" placeholder="Nombre del proveedor"></div>
      <div class="fg"><label>Contacto</label><input type="text" id="p-contacto" placeholder="Nombre del contacto"></div>
      <div class="fg"><label>Email</label><input type="email" id="p-email" placeholder="correo@empresa.com"></div>
      <div class="fg"><label>Teléfono</label><input type="tel" id="p-tel" placeholder="+57..."></div>
      <div class="fg"><label>Categoría</label><select id="p-cat"><option>Materias primas</option><option>Material de empaque</option><option>Insumos generales</option><option>Servicios</option></select></div>
      <div class="fg"><label>Condiciones de pago</label><input type="text" id="p-pago" placeholder="30 días, contado..."></div>
    </div>
    <div style="display:flex;gap:10px;margin-top:8px;">
      <button class="btn" onclick="crearProveedor()">Guardar</button>
      <button class="btn btn-ghost" onclick="document.getElementById('form-prov').style.display='none'">Cancelar</button>
    </div>
    <div id="prov-msg"></div>
  </div>
  <div class="card" style="padding:0;overflow:hidden;">
    <table><thead><tr><th>Nombre</th><th>Contacto</th><th>Email</th><th>Teléfono</th><th>Categoría</th><th>Pago</th></tr></thead>
    <tbody id="prov-body"><tr><td colspan="6" class="empty">Cargando...</td></tr></tbody></table>
  </div>
</div>

<div class="footer-credit">Desarrollado por <a href="#">Sebastián Vargas Isaza</a> · HHA Group Sistema Operativo Interno · 2026</div>

<script>
var USUARIO = '{usuario}';
var ES_CONTADORA = {es_contadora};
document.getElementById('user-label').textContent = '👤 ' + USUARIO;

function goTo(id,btn){
  document.querySelectorAll('.page').forEach(function(p){p.classList.remove('active');});
  document.querySelectorAll('.nav-btn').forEach(function(b){b.classList.remove('active');});
  document.getElementById(id).classList.add('active');
  if(btn) btn.classList.add('active');
  if(id==='dashboard') loadDashboard();
  if(id==='alertas') loadAlertas();
  if(id==='ordenes') loadOCs();
  if(id==='solicitudes') loadSolicitudes();
  if(id==='proveedores') loadProveedores();
}

function badgeEstado(e){
  var map={'Borrador':'badge-bor','Pendiente':'badge-pend','Aprobada':'badge-aprov',
           'Enviada':'badge-env','En tránsito':'badge-env','Recibida':'badge-rec',
           'Rechazada':'badge-rech','Normal':'badge-bor','Urgente':'badge-pend','Crítico':'badge-rech'};
  return '<span class="badge '+(map[e]||'badge-bor')+'">'+e+'</span>';
}

async function loadDashboard(){
  try{
    var ra=await fetch('/api/alertas-reabastecimiento').then(function(r){return r.json();});
    var roc=await fetch('/api/ordenes-compra').then(function(r){return r.json();});
    var rsol=await fetch('/api/solicitudes-compra').then(function(r){return r.json();});
    var rprov=await fetch('/api/proveedores-compras').then(function(r){return r.json();});
    document.getElementById('k-alertas').textContent=(ra.alertas||[]).length;
    var ocs=roc.ordenes||[];
    document.getElementById('k-oc-pend').textContent=ocs.filter(function(o){return o.estado==='Pendiente';}).length;
    document.getElementById('k-oc-trans').textContent=ocs.filter(function(o){return o.estado==='En tránsito';}).length;
    var sols=rsol.solicitudes||[];
    document.getElementById('k-sol-pend').textContent=sols.filter(function(s){return s.estado==='Pendiente';}).length;
    document.getElementById('k-provs').textContent=(rprov.proveedores||[]).length;
    var ocR=ocs.slice(0,5);
    document.getElementById('dash-oc-body').innerHTML=ocR.length?ocR.map(function(o){
      return '<tr><td style="font-family:monospace;">'+o.numero_oc+'</td><td>'+o.proveedor+'</td><td>'+o.fecha.substring(0,10)+'</td><td>'+badgeEstado(o.estado)+'</td><td><button class="btn btn-ghost btn-sm" onclick="cambiarEstadoOC(\''+o.numero_oc+'\')">Estado</button></td></tr>';
    }).join(''):'<tr><td colspan="5" class="empty">Sin órdenes</td></tr>';
    var solR=sols.slice(0,5);
    document.getElementById('dash-sol-body').innerHTML=solR.length?solR.map(function(s){
      return '<tr><td style="font-family:monospace;">'+s.numero+'</td><td>'+s.solicitante+'</td><td>'+s.fecha.substring(0,10)+'</td><td>'+badgeEstado(s.urgencia)+'</td><td>'+badgeEstado(s.estado)+'</td></tr>';
    }).join(''):'<tr><td colspan="5" class="empty">Sin solicitudes</td></tr>';
  }catch(e){console.error(e);}
}

async function loadAlertas(){
  try{
    var d=await fetch('/api/alertas-reabastecimiento').then(function(r){return r.json();});
    var tb=document.getElementById('alertas-body');
    if(!d.alertas||!d.alertas.length){tb.innerHTML='<tr><td colspan="7" class="empty">✓ Todo el stock está sobre el mínimo</td></tr>';return;}
    tb.innerHTML=d.alertas.map(function(a){
      var pct=a.stock_minimo>0?Math.round((a.stock_actual/a.stock_minimo)*100):0;
      var nivel=pct<25?'Crítico':pct<50?'Urgente':'Bajo';
      var badge=pct<25?'badge-rech':pct<50?'badge-pend':'badge-bor';
      return '<tr><td style="font-family:monospace;font-size:0.85em;">'+a.codigo_mp+'</td><td style="font-weight:600;">'+a.nombre+'</td><td style="color:#9C8B7A;">'+a.proveedor+'</td><td style="text-align:right;">'+a.stock_minimo.toLocaleString()+' g</td><td style="text-align:right;color:#B54A4A;font-weight:700;">'+a.stock_actual.toLocaleString()+' g</td><td style="text-align:right;font-weight:700;">'+a.deficit.toLocaleString()+' g</td><td><span class="badge '+badge+'">'+nivel+' ('+pct+'%)</span></td></tr>';
    }).join('');
  }catch(e){}
}

async function generarOCAutomatica(){
  document.getElementById('alertas-msg').innerHTML='<div class="msg-ok">Generando OCs...</div>';
  try{
    var r=await fetch('/api/generar-oc-automatica',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    var d=await r.json();
    document.getElementById('alertas-msg').innerHTML='<div class="msg-ok">'+d.message+'</div>';
    loadAlertas();loadOCs();
  }catch(e){document.getElementById('alertas-msg').innerHTML='<div class="msg-err">Error al generar OCs</div>';}
}

async function loadOCs(){
  try{
    var d=await fetch('/api/ordenes-compra').then(function(r){return r.json();});
    var tb=document.getElementById('oc-body');
    if(!d.ordenes||!d.ordenes.length){tb.innerHTML='<tr><td colspan="7" class="empty">Sin órdenes de compra</td></tr>';return;}
    tb.innerHTML=d.ordenes.map(function(o){
      var pR=['En transito','Enviada'].indexOf(o.estado)>=0;
      var bR=pR?'<button class="btn btn-sm" style="margin-left:6px;background:#2B7A78;" onclick="recibirOC(\''+o.numero_oc+'\')" >Recibir</button>':'';
      return '<tr><td style="font-family:monospace;font-weight:600;">'+o.numero_oc+'</td><td>'+o.proveedor+'</td><td>'+o.fecha.substring(0,10)+'</td><td>'+(o.fecha_entrega_est||'—')+'</td><td>'+badgeEstado(o.estado)+'</td><td style="text-align:center;">'+(o.num_items||0)+'</td><td><button class="btn btn-ghost btn-sm" onclick="cambiarEstadoOC(\''+o.numero_oc+'\')" >Estado</button>'+bR+'</td></tr>';
    }).join('');
  }catch(e){}
}

function showFormOC(){var f=document.getElementById('form-oc');f.style.display=f.style.display==='none'?'block':'none';}
function addItemOC(){
  var div=document.createElement('div');div.className='grid3 oc-item-row';div.style.marginBottom='8px';
  div.innerHTML='<input type="text" class="oc-cod" placeholder="MP00001"><input type="number" class="oc-cant" placeholder="0" step="0.01"><input type="number" class="oc-precio" placeholder="0" step="0.01">';
  document.getElementById('oc-items-list').appendChild(div);
}
async function crearOC(){
  var items=[];
  document.querySelectorAll('.oc-item-row').forEach(function(row){
    var cod=row.querySelector('.oc-cod').value.trim();
    var cant=parseFloat(row.querySelector('.oc-cant').value)||0;
    var precio=parseFloat(row.querySelector('.oc-precio').value)||0;
    if(cod&&cant>0) items.push({codigo_mp:cod,cantidad_g:cant,precio_unitario:precio});
  });
  var data={proveedor:document.getElementById('oc-prov').value,fecha_entrega_est:document.getElementById('oc-fecha-ent').value,observaciones:document.getElementById('oc-obs').value,items:items,creado_por:USUARIO};
  try{
    var r=await fetch('/api/ordenes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    if(r.ok){document.getElementById('oc-msg').innerHTML='<div class="msg-ok">'+res.message+'</div>';loadOCs();}
    else{document.getElementById('oc-msg').innerHTML='<div class="msg-err">'+(res.error||'Error')+'</div>';}
  }catch(e){document.getElementById('oc-msg').innerHTML='<div class="msg-err">Error</div>';}
}
async function cambiarEstadoOC(numero){
  var todoEstados=['Borrador','Aprobada','Enviada','En transito','Recibida','Pagada','Cancelada'];
  var estados=ES_CONTADORA?todoEstados.filter(function(e){return e!=='Aprobada'&&e!=='Pagada';}):[...todoEstados];
  var est={'Borrador':'btn-ghost','Aprobada':'btn','Enviada':'btn btn-gold','En transito':'btn btn-gold','Recibida':'btn','Pagada':'btn','Cancelada':'btn btn-danger'};
  document.getElementById('modal-oc-num').textContent=numero;
  document.getElementById('oc-estado-btns').innerHTML=estados.map(function(e){
    return '<button class="btn '+(est[e]||'btn-ghost')+'" style="text-align:left;margin-bottom:2px;" onclick="setEstadoOC(\''+numero+'\',\''+e+'\')" >'+e+'</button>';
  }).join('');
  openModal('modal-oc-estado');
}
async function setEstadoOC(numero,nuevo){
  await fetch('/api/ordenes-compra/'+numero,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:nuevo})});
  closeModal('modal-oc-estado');loadOCs();loadDashboard();
}
async function recibirOC(numero){
  if(!confirm('Confirmar recepcion de '+numero+'?\nEsto creara ingresos de inventario.')) return;
  var r=await fetch('/api/ordenes-compra/'+numero+'/recibir',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
  var d=await r.json();
  if(d.ok) alert('Recepcion OK. '+d.ingresos+' ingreso(s) en inventario.');
  else alert('Error: '+(d.error||''));
  loadOCs();loadDashboard();
}
async function loadSolicitudes(){
  try{
    var d=await fetch('/api/solicitudes-compra').then(function(r){return r.json();});
    var tb=document.getElementById('sol-body');
    if(!d.solicitudes||!d.solicitudes.length){tb.innerHTML='<tr><td colspan="6" class="empty">Sin solicitudes</td></tr>';return;}
    tb.innerHTML=d.solicitudes.map(function(s){
      var eBadge=s.empresa&&s.empresa.indexOf('ANIMUS')>=0?'<span style="display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;background:#f3e8ff;color:#7A4A8B;font-weight:600;margin-right:4px;">AN</span>':'<span style="display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;background:#e8f4f0;color:#2B7A78;font-weight:600;margin-right:4px;">ESP</span>';
      var acc='<button class="btn btn-ghost btn-sm" onclick="verSolicitud(\''+s.numero+'\')" >Ver</button>';
      if(s.estado==='Pendiente') acc+=' <button class="btn btn-sm" style="font-size:11px;" onclick="verSolicitud(\''+s.numero+'\',true)">Gestionar</button>';
      return '<tr><td style="font-family:monospace;font-weight:600;">'+s.numero+'</td><td>'+s.solicitante+'</td><td>'+s.fecha.substring(0,10)+'</td><td>'+badgeEstado(s.urgencia)+'</td><td>'+badgeEstado(s.estado)+'</td><td>'+eBadge+acc+'</td></tr>';
    }).join('');
  }catch(e){}
}

async function verSolicitud(numero,gestionar){
  openModal('modal-sol');
  document.getElementById('modal-sol-content').innerHTML='<div style="padding:20px;text-align:center;color:#999;">Cargando...</div>';
  try{
    var d=await fetch('/api/solicitudes-compra/'+numero).then(function(r){return r.json();});
    var sol=d.solicitud||{}; var items=d.items||[];
    var urgCls={'Normal':'badge-bor','Urgente':'badge-pend','Critico':'badge-rech'};
    var h='<h3 style="font-size:17px;font-weight:700;margin-bottom:4px;">'+numero+'</h3>';
    if(sol.empresa) h+='<div style="font-size:12px;color:#888;margin-bottom:10px;">'+sol.empresa+(sol.categoria?' &middot; '+sol.categoria:'')+(sol.tipo?' &middot; '+sol.tipo:'')+'</div>';
    h+='<div style="margin-bottom:12px;display:flex;gap:8px;">'+badgeEstado(sol.estado)+'<span class="badge '+(urgCls[sol.urgencia]||'badge-bor')+'">'+(sol.urgencia||'Normal')+'</span></div>';
    h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;font-size:13px;">';
    h+='<div><strong>Solicitante:</strong><br>'+(sol.solicitante||'&mdash;')+'</div>';
    h+='<div><strong>Area:</strong><br>'+(sol.area||'&mdash;')+'</div>';
    h+='<div><strong>Fecha:</strong><br>'+(sol.fecha||'').substring(0,10)+'</div>';
    if(sol.numero_oc) h+='<div><strong>OC:</strong><br><span style="font-family:monospace;color:#4A6741;font-weight:700;">'+sol.numero_oc+'</span></div>';
    if(sol.aprobado_por) h+='<div><strong>Aprobado por:</strong><br>'+sol.aprobado_por+'</div>';
    h+='</div>';
    if(sol.observaciones) h+='<div style="background:#fafafa;border-radius:8px;padding:10px 12px;font-size:13px;margin-bottom:14px;"><strong>Obs:</strong> '+sol.observaciones+'</div>';
    h+='<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr>';
    h+='<th style="text-align:left;padding:5px 8px;background:#f5f5f5;font-size:11px;color:#888;">Cod.</th><th style="text-align:left;padding:5px 8px;background:#f5f5f5;font-size:11px;color:#888;">Descripcion</th><th style="text-align:right;padding:5px 8px;background:#f5f5f5;font-size:11px;color:#888;">Cant.</th><th style="text-align:right;padding:5px 8px;background:#f5f5f5;font-size:11px;color:#888;">Valor est.</th>';
    h+='</tr></thead><tbody>';
    items.forEach(function(it){h+='<tr><td style="padding:5px 8px;font-family:monospace;font-size:12px;color:#666;">'+(it.codigo_mp||'&mdash;')+'</td><td style="padding:5px 8px;">'+it.nombre_mp+'</td><td style="padding:5px 8px;text-align:right;">'+(it.cantidad_g||0)+' '+(it.unidad||'g')+'</td><td style="padding:5px 8px;text-align:right;">'+(it.valor_estimado?'$'+it.valor_estimado:'&mdash;')+'</td></tr>';});
    h+='</tbody></table>';
    if(gestionar&&sol.estado==='Pendiente'){
      h+='<div style="margin-top:18px;padding-top:16px;border-top:1px solid #eee;"><div style="font-size:13px;font-weight:600;margin-bottom:10px;">Gestionar</div><div style="display:flex;gap:8px;flex-wrap:wrap;">';
      h+='<button class="btn" onclick="aprobarSol(\''+numero+'\')">✓ Aprobar</button>';
      h+='<button class="btn btn-gold" onclick="aprobarCrearOC(\''+numero+'\')">+ Aprobar y crear OC</button>';
      h+='<button class="btn btn-danger" onclick="rechazarSol(\''+numero+'\')">✕ Rechazar</button>';
      h+='</div></div>';
    }
    document.getElementById('modal-sol-content').innerHTML=h;
  }catch(e){document.getElementById('modal-sol-content').innerHTML='<div style="color:#dc2626;padding:16px;">Error al cargar</div>';}
}
async function aprobarSol(numero){
  if(!confirm('Aprobar '+numero+'?')) return;
  var r=await fetch('/api/solicitudes-compra/'+numero+'/estado',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:'Aprobada'})});
  var d=await r.json();
  if(d.ok){closeModal('modal-sol');loadSolicitudes();loadDashboard();}
  else alert('Error: '+(d.error||''));
}
async function aprobarCrearOC(numero){
  var prov=prompt('Proveedor (Enter=Por definir):');
  if(prov===null) return;
  var r=await fetch('/api/solicitudes-compra/'+numero+'/estado',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:'Aprobada',crear_oc:true,proveedor:prov||'Por definir'})});
  var d=await r.json();
  if(d.ok){closeModal('modal-sol');if(d.numero_oc)alert('OC creada: '+d.numero_oc);loadSolicitudes();loadOCs();loadDashboard();}
  else alert('Error: '+(d.error||''));
}
async function rechazarSol(numero){
  var motivo=prompt('Motivo (opcional):');
  if(motivo===null) return;
  var r=await fetch('/api/solicitudes-compra/'+numero+'/estado',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:'Rechazada',observaciones:motivo||''})});
  var d=await r.json();
  if(d.ok){closeModal('modal-sol');loadSolicitudes();loadDashboard();}
  else alert('Error: '+(d.error||''));
}
function openModal(id){document.getElementById(id).style.display='flex';}
function closeModal(id){document.getElementById(id).style.display='none';}
document.addEventListener('keydown',function(e){if(e.key==='Escape'){closeModal('modal-sol');closeModal('modal-oc-estado');}});

async function loadProveedores(){
  try{
    var d=await fetch('/api/proveedores-compras').then(function(r){return r.json();});
    var tb=document.getElementById('prov-body');
    if(!d.proveedores||!d.proveedores.length){tb.innerHTML='<tr><td colspan="6" class="empty">Sin proveedores</td></tr>';return;}
    tb.innerHTML=d.proveedores.map(function(p){
      return '<tr><td style="font-weight:600;">'+p.nombre+'</td><td>'+(p.contacto||'—')+'</td><td>'+(p.email||'—')+'</td><td>'+(p.telefono||'—')+'</td><td>'+(p.categoria||'—')+'</td><td>'+(p.condiciones_pago||'—')+'</td></tr>';
    }).join('');
  }catch(e){}
}
function showFormProv(){var f=document.getElementById('form-prov');f.style.display=f.style.display==='none'?'block':'none';}
async function crearProveedor(){
  var data={nombre:document.getElementById('p-nombre').value,contacto:document.getElementById('p-contacto').value,email:document.getElementById('p-email').value,telefono:document.getElementById('p-tel').value,categoria:document.getElementById('p-cat').value,condiciones_pago:document.getElementById('p-pago').value};
  if(!data.nombre){document.getElementById('prov-msg').innerHTML='<div class="msg-err">El nombre es requerido</div>';return;}
  try{
    var r=await fetch('/api/proveedores-compras',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    if(r.ok){document.getElementById('prov-msg').innerHTML='<div class="msg-ok">'+res.message+'</div>';loadProveedores();document.getElementById('form-prov').style.display='none';}
    else{document.getElementById('prov-msg').innerHTML='<div class="msg-err">'+(res.error||'Error')+'</div>';}
  }catch(e){document.getElementById('prov-msg').innerHTML='<div class="msg-err">Error</div>';}
}

window.onload=function(){loadDashboard();};
</script>
<!-- Modal Solicitud -->
<div id="modal-sol" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:2000;align-items:flex-start;justify-content:center;padding-top:60px;">
  <div style="background:#fff;border-radius:14px;padding:28px 32px;max-width:640px;width:94%;max-height:78vh;overflow-y:auto;position:relative;box-shadow:0 20px 60px rgba(0,0,0,.2);">
    <button onclick="closeModal('modal-sol')" style="position:absolute;top:14px;right:16px;background:none;border:none;font-size:22px;cursor:pointer;color:#bbb;">&#x2715;</button>
    <div id="modal-sol-content">Cargando...</div>
  </div>
</div>
<!-- Modal Estado OC -->
<div id="modal-oc-estado" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:2000;align-items:center;justify-content:center;">
  <div style="background:#fff;border-radius:14px;padding:28px 32px;max-width:380px;width:94%;position:relative;box-shadow:0 20px 60px rgba(0,0,0,.2);">
    <button onclick="closeModal('modal-oc-estado')" style="position:absolute;top:14px;right:16px;background:none;border:none;font-size:22px;cursor:pointer;color:#bbb;">&#x2715;</button>
    <h3 style="margin-bottom:6px;font-size:15px;font-weight:700;">Cambiar estado OC</h3>
    <p id="modal-oc-num" style="font-family:monospace;font-weight:700;color:#4A6741;margin-bottom:18px;font-size:14px;"></p>
    <div style="display:flex;flex-direction:column;gap:8px;" id="oc-estado-btns"></div>
  </div>
</div>
</body>
</html>"""

SOLICITUDES_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Compras &amp; Pagos - Solicitudes</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f7;color:#1d1d1f;min-height:100vh}
.topbar{background:#1a1a2e;color:#fff;padding:14px 24px;display:flex;align-items:center;gap:12px}
.hha-back{font-size:13px;color:#9C8B7A;text-decoration:none;margin-right:4px;opacity:.85}
.hha-back:hover{opacity:1}
.topbar-logo{font-size:17px;font-weight:700;letter-spacing:-.5px}
.topbar-sub{font-size:12px;opacity:.55;margin-left:auto}
.container{max-width:760px;margin:28px auto;padding:0 16px}
.card{background:#fff;border-radius:12px;padding:22px 24px;margin-bottom:20px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.card-title{font-size:15px;font-weight:700;margin-bottom:16px;padding-bottom:10px;border-bottom:1px solid #f0f0f0}
label{display:block;font-size:12px;font-weight:600;color:#666;margin-bottom:4px;text-transform:uppercase;letter-spacing:.4px}
input,select,textarea{width:100%;border:1px solid #ddd;border-radius:8px;padding:9px 12px;font-size:14px;background:#fafafa;transition:border .15s;color:#1d1d1f}
input:focus,select:focus,textarea:focus{outline:none;border-color:#7A4A8B;background:#fff}
textarea{resize:vertical;min-height:80px}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.field{margin-bottom:16px}
.emp-tabs{display:flex;gap:10px;margin-bottom:22px}
.emp-tab{flex:1;padding:14px 10px;border:2px solid #eee;border-radius:10px;background:#fff;cursor:pointer;font-size:14px;font-weight:600;text-align:center;transition:all .15s;color:#888}
.emp-tab.active-esp{border-color:#2B7A78;background:#edf7f7;color:#2B7A78}
.emp-tab.active-ani{border-color:#7A4A8B;background:#f5eeff;color:#7A4A8B}
.tipo-row{display:flex;gap:8px;margin-bottom:14px}
.tipo-tab{flex:1;padding:10px;border:2px solid #eee;border-radius:8px;background:#fff;cursor:pointer;font-size:13px;font-weight:600;text-align:center;transition:all .15s;color:#888}
.tipo-tab.active{border-color:#4A6741;background:#f0f7ee;color:#4A6741}
.tipo-hint{font-size:12px;color:#888;background:#fafafa;border-radius:6px;padding:8px 12px;margin-bottom:16px;line-height:1.5}
.urg-row{display:flex;gap:8px}
.urg-btn{flex:1;padding:9px;border:2px solid #ddd;border-radius:8px;background:#fff;font-size:13px;font-weight:600;cursor:pointer;transition:all .15s;text-align:center}
.urg-n{border-color:#2B7A78;background:#edf7f7;color:#2B7A78}
.urg-u{border-color:#B5924A;background:#fdf6ec;color:#B5924A}
.urg-c{border-color:#dc2626;background:#fef2f2;color:#dc2626}
.items-tbl{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:10px}
.items-tbl th{text-align:left;padding:6px 6px;background:#f9f9f9;font-weight:600;font-size:11px;color:#999;border-bottom:1px solid #eee;text-transform:uppercase;letter-spacing:.3px}
.items-tbl td{padding:4px 3px;vertical-align:middle}
.items-tbl input,.items-tbl select{padding:6px 7px;font-size:13px;border-radius:6px}
.btn-add-item{font-size:13px;color:#7A4A8B;background:none;border:none;cursor:pointer;padding:4px 0;font-weight:600}
.btn-add-item:hover{text-decoration:underline}
.btn-del{background:none;border:none;color:#ddd;cursor:pointer;font-size:16px;padding:4px 8px;transition:color .1s}
.btn-del:hover{color:#dc2626}
.btn-primary{width:100%;background:#4A6741;color:#fff;border:none;border-radius:10px;padding:14px;font-size:15px;font-weight:700;cursor:pointer;margin-top:4px;transition:background .15s}
.btn-primary:hover{background:#3a5331}
.btn-primary:disabled{background:#ccc;cursor:not-allowed}
.confirm-box{text-align:center;padding:36px 16px}
.confirm-ico{font-size:52px;margin-bottom:12px}
.confirm-sol{font-size:30px;font-weight:800;color:#4A6741;letter-spacing:1px;margin:8px 0}
.confirm-msg{font-size:14px;color:#666;line-height:1.6;margin-bottom:20px}
.btn-new{display:inline-block;padding:10px 28px;background:#4A6741;color:#fff;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;border:none}
.lookup-row{display:flex;gap:8px}
.lookup-row input{flex:1}
.lookup-btn{padding:9px 20px;background:#1a1a2e;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;white-space:nowrap}
.status-box{margin-top:16px;display:none}
.sol-detail{margin-top:12px;background:#fafafa;border-radius:8px;padding:14px;font-size:13px}
.sol-detail table{width:100%;border-collapse:collapse}
.sol-detail th{text-align:left;font-size:11px;color:#aaa;padding:4px 6px;border-bottom:1px solid #eee;text-transform:uppercase}
.sol-detail td{padding:5px 6px;font-size:13px}
.sbadge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700}
.s-pend{background:#fef3c7;color:#92400e}
.s-apro{background:#d1fae5;color:#065f46}
.s-rech{background:#fee2e2;color:#991b1b}
.s-blue{background:#dbeafe;color:#1e40af}
.err-msg{color:#dc2626;font-size:13px;margin-top:8px;display:none}
.footer{text-align:center;font-size:12px;color:#bbb;margin:40px 0 20px}
</style>
</head>
<body>
<div class="topbar">
  <a href="/" class="hha-back">&#8592; HHA</a>
  <div class="topbar-logo">&#128203; Compras &amp; Pagos</div>
  <div class="topbar-sub">Nueva Solicitud</div>
</div>
<div class="container">

<div class="emp-tabs">
  <button class="emp-tab active-esp" id="tab-esp" onclick="setEmpresa('Espagiria')">&#129514; Espagiria Laboratorio</button>
  <button class="emp-tab" id="tab-ani" onclick="setEmpresa('ANIMUS')">&#10024; ANIMUS Lab</button>
</div>

<div class="card" id="form-card">
  <div class="card-title">&#128221; Nueva Solicitud</div>
  <div class="tipo-row">
    <button class="tipo-tab active" id="ttab-compra" onclick="setTipo('Compra')">&#128230; Compra</button>
    <button class="tipo-tab" id="ttab-pago" onclick="setTipo('Pago')">&#128176; Pago / Cuenta de Cobro</button>
  </div>
  <div class="tipo-hint" id="tipo-hint">Se espera recibir producto fisico. El equipo de compras emitira una Orden de Compra.</div>
  <div class="row2">
    <div class="field">
      <label>Tu nombre *</label>
      <input type="text" id="f-sol" placeholder="Ej: Maria Garcia" required>
    </div>
    <div class="field">
      <label>Area / Proceso</label>
      <select id="f-area">
        <option value="Produccion">Produccion</option>
        <option value="Control de Calidad">Control de Calidad</option>
        <option value="Aseguramiento de Calidad">Aseguramiento de Calidad</option>
        <option value="Almacen">Almacen</option>
        <option value="Gerencia/Admin">Gerencia / Admin</option>
        <option value="Marketing/ANIMUS">Marketing / ANIMUS</option>
        <option value="Compras">Compras</option>
        <option value="Otro">Otro</option>
      </select>
    </div>
  </div>
  <div class="row2">
    <div class="field">
      <label>Categoria</label>
      <select id="f-cat">
        <option value="Materia Prima">Materia Prima</option>
        <option value="Material de Empaque">Material de Empaque</option>
        <option value="EPP">EPP</option>
        <option value="Aseo/Limpieza">Aseo / Limpieza</option>
        <option value="Papeleria/Oficina">Papeleria / Oficina</option>
        <option value="Mantenimiento">Mantenimiento / Reparacion</option>
        <option value="Repuestos">Repuestos</option>
        <option value="Servicios Profesionales">Servicios Profesionales</option>
        <option value="Software/Tecnologia">Software / Tecnologia</option>
        <option value="Dotacion">Dotacion</option>
        <option value="Influencer/Marketing Digital">Influencer / Marketing Digital</option>
        <option value="Reactivos/Laboratorio">Reactivos / Laboratorio</option>
        <option value="Otro">Otro</option>
      </select>
    </div>
    <div class="field">
      <label>Urgencia</label>
      <div class="urg-row">
        <button class="urg-btn urg-n" id="ub-n" onclick="setUrg('Normal',this)">Normal</button>
        <button class="urg-btn" id="ub-u" onclick="setUrg('Urgente',this)">Urgente</button>
        <button class="urg-btn" id="ub-c" onclick="setUrg('Critico',this)">Critico</button>
      </div>
    </div>
  </div>
  <div class="field">
    <label>Items / Descripcion *</label>
    <table class="items-tbl">
      <thead><tr>
        <th style="width:17%">Codigo (opt)</th>
        <th style="width:33%">Descripcion *</th>
        <th style="width:11%">Cantidad</th>
        <th style="width:13%">Unidad</th>
        <th style="width:18%">Valor est.</th>
        <th style="width:8%"></th>
      </tr></thead>
      <tbody id="items-body">
        <tr id="ir-0">
          <td><input type="text" placeholder="Cod." id="i0-cod"></td>
          <td><input type="text" placeholder="Descripcion del item" id="i0-nom"></td>
          <td><input type="number" placeholder="0" min="0" step="0.01" id="i0-cant"></td>
          <td><select id="i0-uni"><option>g</option><option>kg</option><option>ml</option><option>L</option><option>und</option><option>servicio</option><option>mes</option></select></td>
          <td><input type="number" placeholder="0" min="0" step="1000" id="i0-val"></td>
          <td><button class="btn-del" onclick="delItem(0)">&#10005;</button></td>
        </tr>
      </tbody>
    </table>
    <button class="btn-add-item" onclick="addItem()">+ Agregar item</button>
  </div>
  <div class="field">
    <label id="obs-label">Observaciones / Justificacion</label>
    <textarea id="f-obs" placeholder="Motivo, especificaciones adicionales..."></textarea>
  </div>
  <button class="btn-primary" id="btn-enviar" onclick="enviarSolicitud()">Enviar Solicitud</button>
</div>

<div class="card" id="confirm-card" style="display:none">
  <div class="confirm-box">
    <div class="confirm-ico">&#9989;</div>
    <div style="font-size:14px;color:#888;margin-bottom:4px">Solicitud registrada</div>
    <div class="confirm-sol" id="confirm-num">SOL-2026-0001</div>
    <div class="confirm-msg">Guarda este numero para seguimiento.<br>El equipo de compras revisara tu solicitud pronto.</div>
    <button class="btn-new" onclick="nuevaSolicitud()">+ Nueva Solicitud</button>
  </div>
</div>

<div class="card">
  <div class="card-title">&#128269; Consultar Estado</div>
  <div class="lookup-row">
    <input type="text" id="sol-lookup" placeholder="SOL-2026-0001" maxlength="20">
    <button class="lookup-btn" onclick="consultarSol()">Buscar</button>
  </div>
  <div class="err-msg" id="lookup-err">No encontrada. Verifica el numero.</div>
  <div class="status-box" id="status-box">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap;">
      <strong id="sol-num-disp" style="font-size:15px;font-family:monospace;"></strong>
      <span class="sbadge" id="sol-badge"></span>
      <span style="font-size:12px;color:#aaa;" id="sol-fecha-disp"></span>
    </div>
    <div class="sol-detail">
      <div style="margin-bottom:8px;font-size:13px;">
        <strong>Solicitante:</strong> <span id="s-who"></span>
        &nbsp;&middot;&nbsp;<strong>Area:</strong> <span id="s-area"></span>
        &nbsp;&middot;&nbsp;<strong>Empresa:</strong> <span id="s-emp"></span>
      </div>
      <div style="margin-bottom:8px;font-size:13px;">
        <strong>Tipo:</strong> <span id="s-tipo"></span>
        &nbsp;&middot;&nbsp;<strong>Categoria:</strong> <span id="s-cat"></span>
        &nbsp;&middot;&nbsp;<strong>Urgencia:</strong> <span id="s-urg"></span>
      </div>
      <table><thead><tr><th>Codigo</th><th>Descripcion</th><th>Cantidad</th><th>Valor est.</th></tr></thead>
        <tbody id="s-items"></tbody></table>
      <div id="s-obs" style="margin-top:8px;color:#666;font-size:12px"></div>
      <div id="s-oc" style="margin-top:6px;font-size:12px;color:#1e40af;font-weight:700"></div>
    </div>
  </div>
</div>
<div class="footer">Espagiria / ANIMUS Lab &middot; Sistema interno &middot; 2026</div>
</div>
<script>
var empresa='Espagiria',tipo='Compra',urg='Normal',itemCount=1;
function setEmpresa(e){
  empresa=e;
  document.getElementById('tab-esp').className='emp-tab'+(e==='Espagiria'?' active-esp':'');
  document.getElementById('tab-ani').className='emp-tab'+(e==='ANIMUS'?' active-ani':'');
}
function setTipo(t){
  tipo=t;
  document.getElementById('ttab-compra').className='tipo-tab'+(t==='Compra'?' active':'');
  document.getElementById('ttab-pago').className='tipo-tab'+(t==='Pago'?' active':'');
  var hints={'Compra':'Se espera recibir producto fisico. El equipo de compras emitira una Orden de Compra.',
    'Pago':'Incluye servicios, honorarios y cuentas de cobro. Ingresa datos bancarios en Observaciones.'};
  document.getElementById('tipo-hint').textContent=hints[t]||'';
  document.getElementById('obs-label').textContent=t==='Pago'?'Datos bancarios / Descripcion del pago':'Observaciones / Justificacion';
  document.getElementById('f-obs').placeholder=t==='Pago'?'Nombre, banco, cuenta, descripcion del cobro...':'Motivo, especificaciones adicionales...';
}
function setUrg(v,el){
  urg=v;
  var clsMap={'Normal':'urg-n','Urgente':'urg-u','Critico':'urg-c'};
  ['ub-n','ub-u','ub-c'].forEach(function(id){document.getElementById(id).className='urg-btn';});
  el.className='urg-btn '+(clsMap[v]||'urg-n');
}
function addItem(){
  var n=itemCount++;
  var tr=document.createElement('tr');tr.id='ir-'+n;
  tr.innerHTML='<td><input type="text" placeholder="Cod." id="i'+n+'-cod"></td>'+
    '<td><input type="text" placeholder="Descripcion" id="i'+n+'-nom"></td>'+
    '<td><input type="number" placeholder="0" min="0" step="0.01" id="i'+n+'-cant"></td>'+
    '<td><select id="i'+n+'-uni"><option>g</option><option>kg</option><option>ml</option><option>L</option><option>und</option><option>servicio</option><option>mes</option></select></td>'+
    '<td><input type="number" placeholder="0" min="0" step="1000" id="i'+n+'-val"></td>'+
    '<td><button class="btn-del" onclick="delItem('+n+')">&#10005;</button></td>';
  document.getElementById('items-body').appendChild(tr);
}
function delItem(n){
  var tr=document.getElementById('ir-'+n);
  if(tr&&document.getElementById('items-body').children.length>1)tr.remove();
}
async function enviarSolicitud(){
  var sol=document.getElementById('f-sol').value.trim();
  if(!sol){alert('Ingresa tu nombre');return;}
  var items=[],rows=document.getElementById('items-body').children;
  for(var i=0;i<rows.length;i++){
    var rid=rows[i].id.replace('ir-','');
    var nom=document.getElementById('i'+rid+'-nom');
    if(nom&&nom.value.trim()){
      items.push({
        codigo_mp:(document.getElementById('i'+rid+'-cod')||{}).value||'',
        nombre_mp:nom.value.trim(),
        cantidad_g:parseFloat((document.getElementById('i'+rid+'-cant')||{}).value)||0,
        unidad:(document.getElementById('i'+rid+'-uni')||{}).value||'und',
        valor_estimado:parseFloat((document.getElementById('i'+rid+'-val')||{}).value)||0
      });
    }
  }
  if(!items.length){alert('Agrega al menos un item');return;}
  var btn=document.getElementById('btn-enviar');
  btn.disabled=true;btn.textContent='Enviando...';
  try{
    var r=await fetch('/api/solicitudes-compra',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        solicitante:sol,area:document.getElementById('f-area').value,
        empresa:empresa,tipo:tipo,categoria:document.getElementById('f-cat').value,
        urgencia:urg,observaciones:document.getElementById('f-obs').value,items:items})});
    var d=await r.json();
    if(d.numero){
      document.getElementById('confirm-num').textContent=d.numero;
      document.getElementById('form-card').style.display='none';
      document.getElementById('confirm-card').style.display='block';
      window.scrollTo(0,0);
    }else{
      alert('Error: '+(d.error||'Intenta de nuevo'));
      btn.disabled=false;btn.textContent='Enviar Solicitud';
    }
  }catch(e){alert('Error de conexion.');btn.disabled=false;btn.textContent='Enviar Solicitud';}
}
function nuevaSolicitud(){
  document.getElementById('form-card').style.display='block';
  document.getElementById('confirm-card').style.display='none';
  document.getElementById('f-sol').value='';document.getElementById('f-obs').value='';
  document.getElementById('items-body').innerHTML=
    '<tr id="ir-0"><td><input type="text" placeholder="Cod." id="i0-cod"></td>'+
    '<td><input type="text" placeholder="Descripcion del item" id="i0-nom"></td>'+
    '<td><input type="number" placeholder="0" min="0" step="0.01" id="i0-cant"></td>'+
    '<td><select id="i0-uni"><option>g</option><option>kg</option><option>ml</option><option>L</option><option>und</option><option>servicio</option><option>mes</option></select></td>'+
    '<td><input type="number" placeholder="0" min="0" step="1000" id="i0-val"></td>'+
    '<td><button class="btn-del" onclick="delItem(0)">&#10005;</button></td></tr>';
  itemCount=1;urg='Normal';setUrg('Normal',document.getElementById('ub-n'));
  document.getElementById('btn-enviar').disabled=false;
  document.getElementById('btn-enviar').textContent='Enviar Solicitud';
}
async function consultarSol(){
  var num=document.getElementById('sol-lookup').value.trim().toUpperCase();
  if(!num)return;
  document.getElementById('lookup-err').style.display='none';
  document.getElementById('status-box').style.display='none';
  try{
    var r=await fetch('/api/solicitudes-compra/'+encodeURIComponent(num));
    if(r.status===404){document.getElementById('lookup-err').style.display='block';return;}
    var d=await r.json();var sol=d.solicitud;
    document.getElementById('sol-num-disp').textContent=sol.numero;
    var eb=document.getElementById('sol-badge');eb.textContent=sol.estado;
    var stCls={'Pendiente':'s-pend','Aprobada':'s-apro','Rechazada':'s-rech'};
    eb.className='sbadge '+(stCls[sol.estado]||'s-blue');
    document.getElementById('sol-fecha-disp').textContent=(sol.fecha||'').slice(0,10);
    document.getElementById('s-who').textContent=sol.solicitante||'---';
    document.getElementById('s-area').textContent=sol.area||'---';
    document.getElementById('s-emp').textContent=sol.empresa||'Espagiria';
    document.getElementById('s-tipo').textContent=sol.tipo||'Compra';
    document.getElementById('s-cat').textContent=sol.categoria||'---';
    document.getElementById('s-urg').textContent=sol.urgencia||'Normal';
    document.getElementById('s-obs').textContent=sol.observaciones?'Obs: '+sol.observaciones:'';
    document.getElementById('s-oc').textContent=sol.numero_oc?'OC asignada: '+sol.numero_oc:'';
    var items=d.items||[];
    document.getElementById('s-items').innerHTML=items.length?items.map(function(it){
      return '<tr><td>'+esc(it.codigo_mp||'---')+'</td><td>'+esc(it.nombre_mp)+'</td><td>'+(it.cantidad_g||0)+' '+(it.unidad||'und')+'</td><td>'+(it.valor_estimado?'$'+it.valor_estimado:'---')+'</td></tr>';
    }).join(''):'<tr><td colspan="4" style="color:#aaa">Sin items</td></tr>';
    document.getElementById('status-box').style.display='block';
  }catch(e){document.getElementById('lookup-err').style.display='block';}
}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
document.getElementById('sol-lookup').addEventListener('keydown',function(e){if(e.key==='Enter')consultarSol();});

</script>
</body>
</html>

"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Inventarios - Espagiria Laboratorios</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Segoe UI',sans-serif; background:#F5F4F0; min-height:100vh; padding:20px; }
.container { max-width:1400px; margin:0 auto; background:white; border-radius:12px; box-shadow:0 20px 60px rgba(0,0,0,0.3); overflow:hidden; }
.header { background:#2B7A78; color:white; padding:25px; text-align:center; }
.header h1 { font-size:1.8em; margin-bottom:6px; }
.tabs { display:flex; background:#f5f5f5; border-bottom:2px solid #ddd; overflow-x:auto; }
.tab-button { flex:1; padding:13px 12px; background:none; border:none; cursor:pointer; font-size:0.9em; font-weight:500; color:#666; white-space:nowrap; min-width:90px; transition:all 0.2s; }
.tab-button:hover { background:white; color:#2B7A78; }
.tab-button.active { background:white; color:#2B7A78; border-bottom:3px solid #2B7A78; }
.tab-content { display:none; padding:25px; }
.tab-content.active { display:block; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:15px; margin:15px 0; }
.card { background:#2B7A78; color:white; padding:18px; border-radius:10px; text-align:center; }
.card h3 { font-size:0.85em; opacity:0.9; margin-bottom:6px; }
.card p { font-size:1.8em; font-weight:700; }
button { background:#2B7A78; color:white; border:none; padding:10px 18px; border-radius:6px; cursor:pointer; font-size:0.9em; font-weight:500; }
button:hover { opacity:0.9; }
input,select,textarea { width:100%; padding:9px; border:1px solid #ddd; border-radius:6px; font-size:0.95em; margin-top:3px; }
.form-group { margin-bottom:14px; }
label { font-weight:600; font-size:0.88em; color:#444; }
.table { width:100%; border-collapse:collapse; margin-top:12px; font-size:0.88em; }
.table th { background:#2B7A78; color:white; padding:9px 10px; text-align:left; }
.table td { padding:8px 10px; border-bottom:1px solid #eee; }
.table tr:hover { background:#f8f9ff; }
.alert-success { background:#d4edda; color:#155724; padding:10px; border-radius:6px; margin-top:8px; }
.alert-error { background:#f8d7da; color:#721c24; padding:10px; border-radius:6px; margin-top:8px; }
.chat-box { height:320px; overflow-y:auto; border:1px solid #ddd; border-radius:8px; padding:12px; margin-bottom:12px; background:#f9f9f9; }
.mp-item:hover { background:#f0f8ff !important; }
.msg { margin-bottom:10px; padding:9px 13px; border-radius:8px; max-width:85%; }
.msg.user { background:#667eea; color:white; margin-left:auto; }
.msg.bot { background:white; border:1px solid #ddd; }
h2 { color:#333; margin-bottom:12px; font-size:1.3em; }
</style>
</head>
<body>
<div id="modal-operador" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.78);z-index:9999;display:flex;align-items:center;justify-content:center;">
  <div style="background:white;border-radius:16px;padding:40px;max-width:400px;width:90%;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
    <div style="font-size:2.5em;margin-bottom:8px;">&#128100;</div>
    <h2 style="color:#2B7A78;margin-top:0;margin-bottom:6px;">&#191;Con qui&#233;n trabajamos hoy?</h2>
    <p style="color:#888;font-size:0.88em;margin-bottom:24px;">Escribe tu nombre para registrar los movimientos</p>
    <input type="text" id="oper-input" placeholder="Tu nombre..." style="font-size:1.1em;text-align:center;padding:12px;border:2px solid #2B7A78;border-radius:8px;margin-bottom:14px;" onkeypress="if(event.key==='Enter')confirmarOper()">
    <br>
    <button onclick="confirmarOper()" style="background:#2B7A78;padding:13px 40px;border-radius:8px;font-size:1em;font-weight:600;width:100%;">Entrar</button>
    <div id="oper-error" style="color:#cc0000;font-size:0.85em;margin-top:8px;display:none;">Por favor escribe tu nombre</div>
  </div>
</div>
<div id="modal-solicitud-compra" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.78);z-index:9996;display:none;align-items:center;justify-content:center;">
  <div style="background:white;border-radius:16px;padding:32px;max-width:480px;width:95%;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
    <h2 style="color:#2B7A78;margin-bottom:4px;">&#128722; Solicitar Compra</h2>
    <p id="sol-mp-info" style="color:#666;font-size:0.9em;margin-bottom:18px;"></p>
    <div class="form-group"><label>Tu nombre *</label><input type="text" id="sol-nombre" placeholder="Ej: Alejandro, Catalina..."></div>
    <div class="form-group"><label>Cantidad a pedir (g) *</label><input type="number" id="sol-cantidad" placeholder="0" step="0.01" min="1" style="border:2px solid #2B7A78;"></div>
    <div class="form-group"><label>Urgencia</label><select id="sol-urgencia"><option value="Normal">Normal</option><option value="Urgente">Urgente</option><option value="Critica">Critica</option></select></div>
    <div class="form-group"><label>Observacion</label><input type="text" id="sol-obs" placeholder="Opcional"></div>
    <div id="sol-msg" style="margin-bottom:10px;"></div>
    <div style="display:flex;gap:10px;">
      <button onclick="enviarSolicitudCompra()" style="flex:1;background:#2B7A78;">&#10003; Enviar Solicitud</button>
      <button onclick="cerrarSolicitudCompra()" style="flex:1;background:#6c757d;">Cancelar</button>
    </div>
  </div>
</div>
<div id="modal-historial" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.78);z-index:9997;display:none;align-items:center;justify-content:center;">
  <div style="background:white;border-radius:16px;padding:32px;max-width:680px;width:95%;max-height:80vh;overflow-y:auto;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h2 style="color:#2B7A78;margin:0;">&#128203; Historial del Lote</h2>
      <button onclick="cerrarHistorial()" style="background:#6c757d;padding:6px 14px;">&#10005; Cerrar</button>
    </div>
    <p id="hist-lote-info" style="color:#666;font-size:0.9em;margin-bottom:16px;"></p>
    <table class="table"><thead><tr><th>Tipo</th><th>Cantidad (g)</th><th>Fecha</th><th>Observaciones</th><th>Operador</th></tr></thead>
    <tbody id="hist-lote-body"><tr><td colspan="5" style="text-align:center;color:#999;">Cargando...</td></tr></tbody></table>
  </div>
</div>
<div id="modal-ajuste" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.78);z-index:9998;display:none;align-items:center;justify-content:center;"><div id="modal-ajuste-body" style="background:white;border-radius:16px;padding:0;max-width:700px;width:96%;max-height:90vh;overflow-y:auto;">
  <div style="background:white;border-radius:16px;padding:32px;max-width:440px;width:90%;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
    <h2 style="color:#2B7A78;margin-bottom:4px;">&#9878; Ajustar Inventario</h2>
    <p id="ajuste-info" style="color:#666;font-size:0.88em;margin-bottom:16px;"></p>
    <div class="form-group"><label>Stock en sistema (g)</label><input type="number" id="ajuste-sistema" readonly style="background:#f5f5f5;color:#888;"></div>
    <div class="form-group"><label style="color:#2B7A78;font-weight:700;">Cantidad f&#237;sica real (g) *</label><input type="number" id="ajuste-fisico" placeholder="Lo que tienes f&#237;sicamente" step="0.01" min="0" style="border:2px solid #2B7A78;"></div>
    <div class="form-group"><label>Observaci&#243;n</label><input type="text" id="ajuste-obs" placeholder="Ej: Conteo del 15/04"></div>
    <div style="display:flex;gap:10px;margin-top:18px;">
      <button onclick="confirmarAjuste()" style="flex:1;background:#2B7A78;">&#10003; Confirmar Ajuste</button>
      <button onclick="cerrarAjuste()" style="flex:1;background:#6c757d;">Cancelar</button>
    </div>
    <div id="ajuste-msg" style="margin-top:10px;"></div>
  </div>
</div>
</div>
<div class="container">
  <div class="header" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;">
    <div><div style="display:flex;align-items:center;gap:12px;"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="34" height="34"><path d="M30 18 L30 38 L16 60 L64 60 L50 38 L50 18 Z" fill="none" stroke="white" stroke-width="3"/><line x1="27" y1="24" x2="53" y2="24" stroke="white" stroke-width="2.5"/><path d="M40 48 Q33 40 33 33 Q40 38 40 48Z" fill="white" opacity="0.8"/><path d="M40 48 Q47 40 47 33 Q40 38 40 48Z" fill="white" opacity="0.8"/><path d="M40 48 Q29 45 27 52 Q34 50 40 48Z" fill="white" opacity="0.6"/><path d="M40 48 Q51 45 53 52 Q46 50 40 48Z" fill="white" opacity="0.6"/></svg><div><div style="font-size:1.4em;font-weight:700;">Sistema de Inventarios</div><div style="font-size:0.75em;letter-spacing:2px;opacity:0.8;font-weight:500;margin-top:2px;">ESPAGIRIA LABORATORIOS</div></div></div>
    <p>Espagiria Laboratorios - Control de Materias Primas</p>
    </div>
    <a href="/" style="color:rgba(255,255,255,0.75);font-size:0.82em;text-decoration:none;white-space:nowrap;">← Portal HHA</a><span id="oper-chip" style="font-size:0.78em;background:rgba(255,255,255,0.2);padding:3px 10px;border-radius:12px;color:white;margin-top:4px;display:block;"></span>
  </div>
  <div class="tabs">
    <button class="tab-button active" onclick="switchTab('dashboard',this)">&#128202; Dashboard</button>
    <button class="tab-button" onclick="switchTab('stock',this)">&#128230; Stock</button>
            <button class="tab-button" onclick="switchTab('ingreso',this)">&#128666; Ingreso MP</button>
    <button class="tab-button" onclick="switchTab('formulas',this)">&#129514; Formulas</button>
    <button class="tab-button" onclick="switchTab('produccion',this)">&#127981; Produccion</button>
    <button class="tab-button" onclick="switchTab('abc',this)">&#128200; ABC</button>
    <button class="tab-button" onclick="switchTab('alertas',this)">&#9888; Alertas</button>
    <button class="tab-button" onclick="switchTab('movimientos',this)">&#128203; Movimientos</button>
  </div>

  <div id="dashboard" class="tab-content active">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h2 style="margin:0;">Dashboard Ejecutivo</h2>
      <button onclick="loadDashboardCompleto()" style="padding:7px 16px;font-size:0.88em;">&#8635; Actualizar</button>
    </div>

    <!-- KPI Cards -->
    <div class="grid" style="margin-bottom:20px;">
      <div class="card"><h3>Stock Total</h3><p id="stock-total">-</p></div>
      <div class="card"><h3>Lotes en Bodega</h3><p id="materiales-count">-</p></div>
      <div class="card" id="card-alertas" style="cursor:pointer;" onclick="switchTab('alertas',document.querySelector('[onclick*=alertas]'))"><h3>MPs bajo Minimo</h3><p id="alertas-count" style="color:#e65100;">-</p></div>
      <div class="card"><h3>Producciones</h3><p id="producciones-count">-</p></div>
    </div>

    <!-- Alertas criticas rápidas -->
    <div id="dash-alertas-rapidas" style="display:none;background:#ffebeb;border:1px solid #cc0000;border-radius:8px;padding:12px;margin-bottom:20px;">
      <h4 style="color:#cc0000;margin-bottom:8px;">&#128308; MPs criticas — bajo stock minimo ahora</h4>
      <div id="dash-alertas-lista" style="font-size:0.88em;"></div>
    </div>

    <!-- Gráficas -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">
      <div style="background:white;border:1px solid #dde;border-radius:8px;padding:16px;">
        <h4 style="margin-bottom:12px;color:#333;">&#128308; Vencimientos próximos 6 meses</h4>
        <canvas id="chart-vencimientos" height="180"></canvas>
        <p id="chart-venc-empty" style="text-align:center;color:#999;font-size:0.88em;display:none;">Sin vencimientos próximos</p>
      </div>
      <div style="background:white;border:1px solid #dde;border-radius:8px;padding:16px;">
        <h4 style="margin-bottom:12px;color:#333;">&#128230; Top 5 MPs por Stock</h4>
        <canvas id="chart-top-stock" height="180"></canvas>
        <p id="chart-stock-empty" style="text-align:center;color:#999;font-size:0.88em;display:none;">Sin datos de stock</p>
      </div>
    </div>

    <!-- Estado de lotes -->
    <div style="background:white;border:1px solid #dde;border-radius:8px;padding:16px;">
      <h4 style="margin-bottom:12px;color:#333;">Estado general de lotes</h4>
      <div style="display:flex;gap:15px;flex-wrap:wrap;" id="dash-estados">
        <div style="text-align:center;padding:10px 20px;background:#ffebeb;border-radius:8px;">
          <div style="font-size:1.8em;font-weight:700;color:#cc0000;" id="dash-vencidos">-</div>
          <div style="font-size:0.82em;color:#888;">Vencidos</div>
        </div>
        <div style="text-align:center;padding:10px 20px;background:#fff3e0;border-radius:8px;">
          <div style="font-size:1.8em;font-weight:700;color:#e65100;" id="dash-criticos">-</div>
          <div style="font-size:0.82em;color:#888;">Críticos &lt;30d</div>
        </div>
        <div style="text-align:center;padding:10px 20px;background:#fffde7;border-radius:8px;">
          <div style="font-size:1.8em;font-weight:700;color:#f57f17;" id="dash-proximos">-</div>
          <div style="font-size:0.82em;color:#888;">Próximos &lt;90d</div>
        </div>
      </div>
    </div>
  </div>

  <div id="stock" class="tab-content">
    <h2>&#128230; Stock por Lote</h2>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:14px;">
      <input type="text" id="stock-search" placeholder="MP, INCI, lote, proveedor..." oninput="filterStock()" style="width:210px;margin-top:0;">
      <div style="display:flex;gap:10px;"><button onclick="loadStock()">&#8635; Actualizar</button><button onclick="exportarExcelStock()" style="background:#217346;">&#128196; Descargar Excel</button></div>
      <span id="stock-count" style="color:#888;font-size:0.88em;"></span>
    </div>
    <div style="overflow-x:auto;">
    <table class="table" style="font-size:0.83em;">
      <thead><tr>
        <th>Cod. MP</th><th>Nombre INCI</th><th>Nombre Comercial</th>
        <th>Tipo</th><th>Proveedor</th>
        <th style="text-align:right;">Stock Min (g)</th><th>Lote</th>
        <th style="text-align:right;">Cantidad (g)</th>
        <th style="text-align:center;">Est.</th><th style="text-align:center;">Pos.</th>
        <th style="text-align:center;">Fecha Venc.</th>
        <th style="text-align:right;">Dias</th><th style="text-align:center;">Estado</th><th style="text-align:center;">Ajuste</th><th style="text-align:center;">Historial</th>
      </tr></thead>
      <tbody id="stock-body"><tr><td colspan="13" style="text-align:center;color:#999;padding:20px;">Cargando...</td></tr></tbody>
    </table>
    </div>
  
  <!-- MEE STOCK -->
  <div style="margin-top:32px;border-top:3px solid #2B7A78;padding-top:24px;">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:14px;">
      <h2 style="margin:0;">&#128230; Stock Materiales de Envase & Empaque</h2>
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <select id="mee-cat-filter" onchange="loadMEE()" style="width:auto;margin:0;padding:7px 12px;font-size:0.88em;">
          <option value="">Todas las categorias</option>
          <option>Envase</option><option>Tapa</option><option>Etiqueta</option>
          <option>Plegable</option><option>Serigrafia</option><option>Gotero</option>
          <option>Frasco</option><option>Contorno</option><option>Otro</option>
        </select>
        <input type="text" id="mee-search" placeholder="Buscar..." oninput="loadMEE()" style="width:160px;margin:0;padding:7px 12px;font-size:0.88em;">
        <button onclick="loadMEE()" style="padding:7px 14px;font-size:0.85em;">&#8635;</button>
        <button onclick="abrirNuevoMEE()" style="background:#27ae60;padding:7px 14px;font-size:0.85em;">+ Nuevo</button>
      </div>
    </div>
    <div id="nuevo-mee-form" style="display:none;background:#e8f5e9;border:2px solid #27ae60;border-radius:8px;padding:18px;margin-bottom:16px;">
      <h4 style="color:#1b5e20;margin-bottom:12px;">+ Nuevo Material E&E</h4>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
        <div><label style="font-size:0.82em;font-weight:700;display:block;margin-bottom:4px;">Codigo *</label><input type="text" id="nmee-cod" placeholder="ENV-XXX-01" style="text-transform:uppercase;"></div>
        <div><label style="font-size:0.82em;font-weight:700;display:block;margin-bottom:4px;">Descripcion *</label><input type="text" id="nmee-desc" placeholder="Descripcion del material"></div>
        <div><label style="font-size:0.82em;font-weight:700;display:block;margin-bottom:4px;">Categoria *</label>
          <select id="nmee-cat" style="width:100%;"><option>Envase</option><option>Tapa</option><option>Etiqueta</option><option>Plegable</option><option>Serigrafia</option><option>Gotero</option><option>Frasco</option><option>Contorno</option><option>Otro</option></select></div>
        <div><label style="font-size:0.82em;font-weight:700;display:block;margin-bottom:4px;">Proveedor</label><input type="text" id="nmee-prov" placeholder="Proveedor"></div>
        <div><label style="font-size:0.82em;font-weight:700;display:block;margin-bottom:4px;">Stock Inicial (und)</label><input type="number" id="nmee-stock" value="2000"></div>
        <div><label style="font-size:0.82em;font-weight:700;display:block;margin-bottom:4px;">Stock Minimo (und)</label><input type="number" id="nmee-min" value="1000"></div>
      </div>
      <div style="display:flex;gap:10px;margin-top:12px;">
        <button onclick="crearMEE()" style="background:#1b5e20;">Crear</button>
        <button onclick="document.getElementById('nuevo-mee-form').style.display='none'" style="background:#95a5a6;">Cancelar</button>
      </div>
      <div id="nmee-msg" style="margin-top:8px;"></div>
    </div>
    <div style="overflow-x:auto;">
      <table class="table" style="font-size:0.84em;">
        <thead><tr>
          <th>Codigo</th><th>Descripcion</th><th>Categoria</th><th>Proveedor</th>
          <th style="text-align:right;">Stock Min</th>
          <th style="text-align:right;">Stock Actual</th>
          <th style="text-align:center;">Estado</th>
          <th style="text-align:center;">Ajuste</th>
          <th style="text-align:center;">Historial</th>
          <th style="text-align:center;">Compra</th>
        </tr></thead>
        <tbody id="mee-stock-body"><tr><td colspan="10" style="text-align:center;color:#999;padding:20px;">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
  </div>

  <div id="ingreso" class="tab-content">
    <div style="display:flex;gap:0;margin-bottom:22px;border-bottom:2px solid #ddd;">
      <button id="ing-tab-mp" onclick="switchIngreso('mp')" style="padding:11px 28px;border:none;background:#2B7A78;color:white;font-weight:700;font-size:0.92em;border-radius:8px 8px 0 0;cursor:pointer;">&#128230; Materia Prima</button>
      <button id="ing-tab-mee" onclick="switchIngreso('mee')" style="padding:11px 28px;border:none;background:#eee;color:#555;font-weight:600;font-size:0.92em;border-radius:8px 8px 0 0;cursor:pointer;margin-left:4px;">&#128230; Envase & Empaque</button>
    </div>
    <div id="ing-panel-mp">
    <h2>&#128666; Ingreso de Materia Prima</h2>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;">
      <p style="color:#666;">Escribe el codigo MP y el sistema completa automaticamente desde el catalogo.</p>
      <button onclick="mostrarFormNuevaMP()" style="background:#27ae60;white-space:nowrap;margin-left:15px;">&#43; Nueva MP en Catalogo</button>
    </div>
    <div id="ing-nueva-mp" style="display:none;background:#e8f5e9;border:2px solid #27ae60;border-radius:8px;padding:18px;margin-bottom:15px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h4 style="color:#1b5e20;">&#43; Crear Nueva Materia Prima en el Catalogo</h4>
        <button onclick="ocultarFormNuevaMP()" style="background:#95a5a6;padding:4px 12px;font-size:0.85em;">&#10005; Cerrar</button>
      </div>
      <p style="font-size:0.88em;color:#2e7d32;margin-bottom:12px;">Esta MP quedara registrada en el catalogo y disponible para futuros ingresos.</p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div class="form-group"><label>Codigo MP * (ej: MP00350)</label><input type="text" id="nmp-cod" placeholder="MP00350" style="text-transform:uppercase;"></div>
        <div class="form-group"><label>Nombre INCI *</label><input type="text" id="nmp-inci" placeholder="Ej: NIACINAMIDE"></div>
        <div class="form-group"><label>Nombre Comercial *</label><input type="text" id="nmp-nombre" placeholder="Ej: Niacinamida"></div>
        <div class="form-group"><label>Tipo</label><input type="text" id="nmp-tipo" placeholder="Ej: Activo, Emoliente, Conservante..."></div>
        <div class="form-group"><label>Proveedor</label><input type="text" id="nmp-prov" placeholder="Nombre del proveedor"></div>
        <div class="form-group"><label>Stock Minimo (g)</label><input type="number" id="nmp-smin" placeholder="0" value="500"></div>
      </div>
      <div style="display:flex;gap:10px;margin-top:12px;">
        <button onclick="crearNuevaMP()" style="background:#1b5e20;">&#10003; Crear en Catalogo</button>
      </div>
      <div id="nmp-msg" style="margin-top:10px;"></div>
    </div>
    <div style="background:#f8f9ff;border:1px solid #dde;border-radius:10px;padding:20px;margin-bottom:20px;">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;">
        <div class="form-group"><label>Codigo MP *</label><div style="position:relative;"><input type="text" id="ing-cod" placeholder="Código (MP00001) o nombre..." autocomplete="off" style="text-transform:uppercase;" oninput="buscarMPIngreso(this.value)" onblur="setTimeout(ocultarDropMP,250)"><div id="mp-dropdown" style="position:absolute;top:100%;left:0;right:0;background:white;border:1px solid #2B7A78;border-radius:0 0 8px 8px;max-height:220px;overflow-y:auto;z-index:1000;display:none;box-shadow:0 4px 12px rgba(0,0,0,0.15);"></div></div><datalist id="mp-sugerencias"></datalist><small id="ing-status" style="color:#667eea;font-size:0.85em;margin-top:4px;display:block;"></small></div>
        <div class="form-group"><label>Nombre INCI</label><input type="text" id="ing-inci" placeholder="Auto" readonly style="background:#f5f5f5;"></div>
        <div class="form-group"><label>Nombre Comercial</label><input type="text" id="ing-nombre" placeholder="Auto" readonly style="background:#f5f5f5;"></div>
        <div class="form-group"><label>Tipo</label><input type="text" id="ing-tipo" placeholder="Auto" readonly style="background:#f5f5f5;"></div>
        <div class="form-group"><label>Proveedor</label><input type="text" id="ing-prov" placeholder="Auto (editable)"></div>
      </div>
      <div id="ing-nueva-mp-inline" style="display:none;background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:15px;margin-top:10px;">
        <h4 style="color:#856404;margin-bottom:10px;">&#43; Nueva Materia Prima — Datos para el Catalogo</h4><p style="font-size:0.88em;color:#666;margin-bottom:10px;">Al registrar el ingreso, esta MP quedara creada automaticamente en el catalogo.</p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
          <div class="form-group"><label>Nombre INCI *</label><input type="text" id="ing-inci-new" placeholder="Ej: NIACINAMIDE"></div>
          <div class="form-group"><label>Tipo</label><input type="text" id="ing-tipo-new" placeholder="Ej: Activo, Emoliente..."></div>
          <div class="form-group"><label>Stock Minimo (g)</label><input type="number" id="ing-smin-new" placeholder="0" value="0"></div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;">
        <div class="form-group"><label>N Lote (vacio = auto)</label><input type="text" id="ing-lote" placeholder="Ej: LYPH250727"></div>
        <div class="form-group"><label>Cantidad recibida (g) *</label><input type="number" id="ing-cant" placeholder="0" step="0.01"></div>
        <div class="form-group"><label>Fecha Vencimiento</label><input type="date" id="ing-vence"></div>
        <div class="form-group"><label>Estanteria</label><input type="text" id="ing-est" placeholder="Ej: 9"></div>
        <div class="form-group"><label>Posicion</label><input type="text" id="ing-pos" placeholder="Ej: B"></div>
      </div>
      <div class="form-group" style="margin-top:10px;"><label>Observaciones</label><input type="text" id="ing-obs" placeholder="Opcional"></div>
      <div style="display:flex;gap:10px;margin-top:15px;flex-wrap:wrap;">
        <button onclick="registrarIngreso()" style="background:#27ae60;">&#10003; Registrar Entrada</button>
        <button onclick="generarRotuloIngreso()" style="background:#2980b9;" id="btn-rotulo-ing">&#128209; Generar Rotulo + Codigo de Barras</button>
        <button onclick="limpiarIngreso()" style="background:#95a5a6;">Limpiar</button>
      </div>
      <div id="ing-msg" style="margin-top:12px;"></div>
    </div>
    <h3 style="margin-bottom:10px;">Ultimas Entradas</h3>
    <div style="overflow-x:auto;"><table class="table" id="ing-hist">
      <thead><tr><th>Codigo</th><th>INCI</th><th>Nombre Comercial</th><th>Lote</th><th style="text-align:right;">g</th><th>Proveedor</th><th>Vence</th><th>Fecha</th></tr></thead>
      <tbody><tr><td colspan="8" style="text-align:center;color:#999;">Sin entradas</td></tr></tbody>
    </table></div>
    </div><!-- end ing-panel-mp -->
    <div id="ing-panel-mee" style="display:none;">
      <h2>&#128230; Ingreso Materiales Envase & Empaque</h2>
      <div style="background:#f8f9ff;border:1px solid #dde;border-radius:10px;padding:20px;margin-bottom:20px;">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;">
          <div class="form-group"><label>Categoria</label>
            <select id="mee-ing-cat" onchange="filtrarMEEIngreso()" style="width:100%;">
              <option value="">Todas</option>
              <option>Envase</option><option>Tapa</option><option>Etiqueta</option>
              <option>Plegable</option><option>Serigrafia</option><option>Gotero</option>
              <option>Frasco</option><option>Contorno</option><option>Otro</option>
            </select>
          </div>
          <div class="form-group"><label>Material *</label>
            <select id="mee-ing-cod" style="width:100%;"><option value="">-- Selecciona --</option></select>
          </div>
          <div class="form-group"><label>Cantidad recibida (unidades) *</label>
            <input type="number" id="mee-ing-cant" placeholder="Ej: 500" min="1"></div>
          <div class="form-group"><label>Proveedor / Referencia</label>
            <input type="text" id="mee-ing-ref" placeholder="Factura, OC, remision..."></div>
        </div>
        <div class="form-group" style="margin-top:10px;"><label>Observaciones</label>
          <input type="text" id="mee-ing-obs" placeholder="Opcional"></div>
        <div style="display:flex;gap:10px;margin-top:14px;">
          <button onclick="registrarIngresoMEE()" style="background:#27ae60;">&#10003; Registrar Entrada MEE</button>
          <button onclick="limpiarIngresoMEE()" style="background:#95a5a6;">Limpiar</button>
        </div>
        <div id="mee-ing-msg" style="margin-top:10px;"></div>
      </div>
      <h3 style="margin-bottom:10px;">Ultimas Entradas MEE</h3>
      <div style="overflow-x:auto;"><table class="table" style="font-size:0.85em;">
        <thead><tr><th>Codigo</th><th>Descripcion</th><th>Tipo</th><th style="text-align:right;">Cant.</th><th>Referencia</th><th>Operador</th><th>Fecha</th></tr></thead>
        <tbody id="mee-hist-body"><tr><td colspan="7" style="text-align:center;color:#999;">Sin entradas</td></tr></tbody>
      </table></div>
    </div><!-- end ing-panel-mee -->
  </div>

  <div id="formulas" class="tab-content">
    <h2>&#129514; Formulas Maestras de Produccion</h2>
    <p style="color:#666;margin-bottom:18px;">Define la receta de cada producto. Al registrar una produccion, las MPs se descuentan automaticamente del inventario.</p>
    <div style="background:#f8f9ff;border:1px solid #dde;border-radius:10px;padding:18px;margin-bottom:22px;">
      <h3 style="margin-bottom:12px;">Nueva Formula / Editar Existente</h3>
      <div style="display:grid;grid-template-columns:1fr 200px;gap:12px;">
        <div class="form-group"><label>Nombre del Producto</label><input type="text" id="formula-producto" placeholder="Ej: Renova C 10"></div>
        <div class="form-group"><label>Base (g) = 100%</label><input type="number" id="formula-base" value="1000"></div>
      </div>
      <div class="form-group"><label>Descripcion (opcional)</label><input type="text" id="formula-desc" placeholder="Descripcion breve"></div>
      <label style="display:block;margin-bottom:8px;font-weight:600;font-size:0.88em;color:#444;">Ingredientes (materias primas)</label>
      <div style="display:grid;grid-template-columns:140px 1fr 90px 38px;gap:6px;margin-bottom:6px;">
        <span style="font-size:0.8em;color:#888;font-weight:600;">CODIGO MP</span>
        <span style="font-size:0.8em;color:#888;font-weight:600;">NOMBRE MATERIAL</span>
        <span style="font-size:0.8em;color:#888;font-weight:600;">% EN FORMULA</span>
        <span></span>
      </div>
      <div id="fi-container"></div>
      <div style="display:flex;gap:10px;margin-top:10px;align-items:center;flex-wrap:wrap;">
        <button onclick="addFRow()" style="background:#28a745;">+ Ingrediente</button>
        <button onclick="guardarFormula()">&#128190; Guardar Formula</button>
        <span id="pct-total" style="font-size:0.9em;color:#666;font-weight:600;"></span>
      </div>
      <div id="formula-msg"></div>
    </div>
    <h3 style="margin-bottom:12px;">Formulas Guardadas</h3>
    <div id="formulas-list"><p style="color:#999;">Cargando...</p></div>
  </div>

  <div id="produccion" class="tab-content">
    <h2>&#127981; Registrar Produccion</h2>
    <p style="color:#666;margin-bottom:16px;">Si el producto tiene formula maestra, las MPs se descuentan automaticamente del inventario al registrar.</p>
    <div class="form-group">
      <label>Producto (con formula maestra)</label>
      <select id="prod-sel" onchange="previewProd()">
        <option value="">-- Selecciona un producto --</option>
      </select>
    </div>
    <div class="form-group">
      <label>O escribe nombre manualmente (sin formula)</label>
      <input type="text" id="prod-manual" placeholder="Producto sin formula registrada" oninput="previewProd()">
    </div>
    <div class="form-group">
      <label>Cantidad a producir (kg)</label>
      <input type="number" id="prod-kg" placeholder="Ej: 20" step="0.001" oninput="previewProd()">
    </div>
    <div id="prod-preview" style="background:#f0f8ff;border:1px solid #b8d4f0;border-radius:8px;padding:14px;margin-bottom:14px;display:none;">
      <strong style="color:#2c5f8a;">MPs que se descontaran automaticamente:</strong>
      <table class="table" style="margin-top:8px;">
        <thead><tr><th>Material</th><th style="text-align:right;">Cantidad (g)</th></tr></thead>
        <tbody id="prod-preview-body"></tbody>
      </table>
    </div>
    <div class="form-group">
      <label>Presentacion del producto</label>
      <input type="text" id="prod-presentacion" placeholder="Ej: 15ml, 30ml, 50g..." list="pres-sugerencias">
      <datalist id="pres-sugerencias">
        <option value="10ml"><option value="15ml"><option value="20ml"><option value="30ml">
        <option value="50ml"><option value="60ml"><option value="100ml"><option value="120ml">
        <option value="150ml"><option value="50g"><option value="100g"><option value="250g">
      </datalist>
    </div>
    <div class="form-group"><label>Observaciones</label><textarea id="prod-obs" rows="2" placeholder="Opcional"></textarea></div>
    <div style="display:flex;gap:10px;"><button onclick="iniciarRegistroProd()">&#9989; Registrar Produccion</button><button onclick="abrirRotulos()" style="background:#c0392b;">&#128209; Generar Rotulos</button></div>
    <div id="prod-msg"></div>
    <div id="mee-consumo-panel" style="display:none;margin-top:24px;background:#f0f9f0;border:2px solid #27ae60;border-radius:12px;padding:22px;">
      <h3 style="color:#1b5e20;margin-bottom:6px;">&#128230; Paso 2: Consumo de Materiales E&E</h3>
      <p style="font-size:0.88em;color:#555;margin-bottom:16px;">Completa el empaque usado en esta produccion. Marca <strong>No aplica</strong> si alguna categoria no corresponde.</p>
      <div id="mee-rows-container"></div>
      <div style="display:flex;gap:10px;margin-top:18px;">
        <button onclick="confirmarProdCompleta()" style="background:#1b5e20;font-size:1em;padding:11px 28px;">&#10003; Confirmar Produccion Completa</button>
        <button onclick="cancelarMEEConsumoProd()" style="background:#95a5a6;">Cancelar</button>
      </div>
      <div id="mee-consumo-msg" style="margin-top:10px;"></div>
    </div>
    <div style="margin-top:28px;border-top:2px solid #eee;padding-top:20px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;"><h3 style="color:#2B7A78;margin:0;">&#128202; Historial de Producciones</h3><button onclick="exportarExcelProducciones()" style="background:#217346;padding:7px 14px;font-size:0.85em;">&#128196; Descargar Excel</button></div>
      <table class="table"><thead><tr><th>Producto</th><th style="text-align:right;">Cantidad (kg)</th><th>Fecha</th><th>Operador</th><th style="text-align:center;">Estado</th></tr></thead>
      <tbody id="hist-prod-body"><tr><td colspan="5" style="text-align:center;color:#999;padding:16px;">Cargando...</td></tr></tbody></table>
    </div>
  </div>

  <div id="abc" class="tab-content">
    <h2>&#128200; Analisis ABC de Inventario</h2>
    <button onclick="loadABC()">Generar Analisis</button>
    <div id="abc-results" style="margin-top:18px;"></div>
  </div>

  <div id="alertas" class="tab-content">
    <h2>&#9888; Alertas de Inventario</h2>
    <div style="background:#fff3e0;border:2px solid #ff9800;border-radius:10px;padding:18px;margin-bottom:20px;">
      <h3 style="color:#e65100;margin-bottom:10px;">&#128197; Lotes que vencen en 30 dias o menos</h3>
      <div id="venc30-content" style="color:#999;">Cargando...</div>
    </div>

    <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:16px;margin-bottom:20px;">
      <h3 style="color:#856404;margin-bottom:10px;">&#128308; MPs bajo stock minimo (basado en plan anual)</h3>
      <p style="font-size:0.88em;color:#664d03;margin-bottom:12px;">Stock minimo calculado: consumo anual / 12 x 2 meses x 1.10 de buffer</p>
      <div id="alertas-reabas-tabla">
        <table class="table">
          <thead><tr><th>Codigo</th><th>Material</th><th>Proveedor</th><th style="text-align:right;">Stock Min (g)</th><th style="text-align:right;">Stock Actual (g)</th><th style="text-align:right;">Deficit (g)</th><th style="text-align:center;">Criticidad</th><th style="text-align:center;">Accion</th></tr></thead>
          <tbody id="reabas-body"><tr><td colspan="7" style="text-align:center;color:#999;">Calculando...</td></tr></tbody>
        </table>
      </div>
    </div>

    <h3 style="margin-bottom:10px;">Alertas manuales de stock</h3>
    <button onclick="loadAlertas()" style="margin-bottom:12px;">Actualizar</button>
    <table class="table" id="alertas-table">
      <thead><tr><th>Material</th><th>Stock Actual</th><th>Stock Minimo</th><th>Estado</th><th>Fecha</th></tr></thead>
      <tbody><tr><td colspan="5" style="text-align:center;color:#999;">Sin alertas</td></tr></tbody>
    </table>

    <!-- ALERTAS MEE -->
    <div style="margin-top:28px;border-top:3px solid #2B7A78;padding-top:24px;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:14px;">
        <h3 style="color:#c0392b;margin:0;">&#128308; Materiales E&E bajo stock minimo</h3>
        <div style="display:flex;gap:8px;">
          <button onclick="loadAlertasMEE()" style="padding:7px 14px;font-size:0.85em;">&#8635; Actualizar</button>
          <button onclick="generarOCsDesdeAlertasMEE()" style="background:#4A6741;padding:7px 16px;font-size:0.85em;">&#9889; Generar OCs automaticas MEE</button>
        </div>
      </div>
      <div style="overflow-x:auto;">
        <table class="table" style="font-size:0.85em;">
          <thead><tr>
            <th>Codigo</th><th>Descripcion</th><th>Categoria</th>
            <th style="text-align:right;">Min (und)</th>
            <th style="text-align:right;">Stock Actual (und)</th>
            <th style="text-align:right;">Deficit</th>
            <th style="text-align:center;">Nivel</th>
            <th style="text-align:center;">Accion</th>
          </tr></thead>
          <tbody id="mee-alertas-body"><tr><td colspan="8" style="text-align:center;color:#999;padding:20px;">Cargando...</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>

  </div>

  <div id="movimientos" class="tab-content">
    <h2>&#128203; Movimientos de Inventario</h2>
    <div style="background:#f8f9ff;border:1px solid #dde;border-radius:10px;padding:18px;margin-bottom:18px;">
      <h3 style="margin-bottom:12px;">Registrar Movimiento Manual</h3>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div class="form-group"><label>Codigo MP</label><input type="text" id="mov-id" placeholder="MP00001"></div>
        <div class="form-group"><label>Nombre Material</label><input type="text" id="mov-nombre" placeholder="Nombre"></div>
        <div class="form-group"><label>Cantidad (g)</label><input type="number" id="mov-cant" placeholder="0" step="0.01"></div>
        <div class="form-group"><label>Tipo</label>
          <select id="mov-tipo"><option value="Entrada">Entrada</option><option value="Salida">Salida</option></select>
        </div>
      </div>
      <div class="form-group"><label>Observaciones</label><input type="text" id="mov-obs" placeholder="Opcional"></div>
      <button onclick="registrarMov()">Registrar</button>
      <div id="mov-msg"></div>
    </div>
    <div style="display:flex;gap:10px;margin-bottom:10px;"><button onclick="loadMovimientos()">Ver Ultimos Movimientos</button><button onclick="exportarExcelMovimientos()" style="background:#217346;">&#128196; Descargar Excel</button></div>
    <table class="table" id="mov-table">
      <thead><tr><th>Material</th><th>Cantidad (g)</th><th>Tipo</th><th>Fecha</th><th>Observaciones</th></tr></thead>
      <tbody><tr><td colspan="5" style="text-align:center;color:#999;">Sin movimientos</td></tr></tbody>
    </table>
  </div>

</div>
<script>
var fData=[], allStock=[], _cat={}, _ultimoIng=null;
var _lotes=[], _lotesFull=[], _meeData=[], _prodPendiente=null;
var OPER_ACTUAL='';
var _meeData=[], _prodPendiente=null;
var _ajDat={};
function selOper(n){OPER_ACTUAL=n;document.getElementById('modal-operador').style.display='none';var c=document.getElementById('oper-chip');if(c)c.textContent='Operador: '+n;loadDashboardCompleto();loadFormulas();}
function confirmarOper(){var inp=document.getElementById('oper-input');var n=(inp?inp.value:'').trim();if(!n){var e=document.getElementById('oper-error');if(e)e.style.display='block';return;}selOper(n);}
function abrirAjusteIdx(idx){
  var i=_lotes[idx];
  if(!i)return;
  abrirAjuste(i.material_id,i.material_nombre,i.lote||"",i.cantidad_g);
}
function abrirAjuste(mid,mn,lt,sa){
  if(!OPER_ACTUAL){alert('Primero selecciona tu nombre al inicio');return;}
  _ajDat={mid:mid,mn:mn,lt:lt,sa:sa};
  document.getElementById('ajuste-info').textContent=mid+' — '+mn+(lt&&lt!='S/L'?' (Lote: '+lt+')':'');
  document.getElementById('ajuste-sistema').value=sa;
  document.getElementById('ajuste-fisico').value='';
  document.getElementById('ajuste-obs').value='';
  document.getElementById('ajuste-msg').innerHTML='';
  document.getElementById('modal-ajuste').style.display='flex';
}
function cerrarAjuste(){document.getElementById('modal-ajuste').style.display='none';document.getElementById('modal-ajuste-body').innerHTML='';}
function abrirSolIdx(ri){
  var a=(window._alertasData||[])[ri];if(!a)return;
  abrirSolicitudCompra(a.codigo_mp,a.nombre,a.deficit);
}
var _solMP={};
function abrirSolicitudCompra(cod,nom,deficit){
  _solMP={cod:cod,nom:nom,deficit:deficit};
  document.getElementById("modal-solicitud-compra").style.display="flex";
  document.getElementById("sol-mp-info").textContent=cod+" - "+nom+" | Deficit: "+deficit.toLocaleString()+"g";
  document.getElementById("sol-cantidad").value=deficit>0?deficit:"";
  document.getElementById("sol-nombre").value=OPER_ACTUAL||"";
  document.getElementById("sol-msg").innerHTML="";
}
function cerrarSolicitudCompra(){
  document.getElementById("modal-solicitud-compra").style.display="none";
}
async function enviarSolicitudCompra(){
  var nom=document.getElementById("sol-nombre").value.trim();
  var cant=parseFloat(document.getElementById("sol-cantidad").value);
  if(!nom){alert("Escribe tu nombre");return;}
  if(!cant||cant<=0){alert("Ingresa una cantidad valida");return;}
  var data={solicitante:nom,urgencia:document.getElementById("sol-urgencia").value,observaciones:document.getElementById("sol-obs").value,
    items:[{codigo_mp:_solMP.cod,nombre_mp:_solMP.nom,cantidad_g:cant,unidad:"g",justificacion:"Solicitud desde alertas de stock"}]};
  try{
    var r=await fetch("/api/solicitudes-compra",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
    var res=await r.json();
    if(r.ok){
      document.getElementById("sol-msg").innerHTML='<div class="alert-success">&#10003; Solicitud '+res.numero+' creada correctamente.</div>';
      setTimeout(function(){cerrarSolicitudCompra();},3000);
    } else { document.getElementById("sol-msg").innerHTML='<div class="alert-error">Error al crear solicitud</div>'; }
  }catch(e){ document.getElementById("sol-msg").innerHTML='<div class="alert-error">Error de conexion</div>'; }
}
function cerrarHistorial(){document.getElementById('modal-historial').style.display='none';}
async function verHistorialLote(idx){
  var i=_lotes[idx];if(!i)return;
  document.getElementById('modal-historial').style.display='flex';
  document.getElementById('hist-lote-info').textContent=i.material_id+' - '+i.material_nombre+' Lote:'+(i.lote||'S/L')+' Stock:'+i.cantidad_g+'g';
  var tb=document.getElementById('hist-lote-body');
  tb.innerHTML='<tr><td colspan=4 style=text-align:center>Cargando...</td></tr>';
  try{
    var r=await fetch('/api/movimientos'),d=await r.json();
    var mv=(d.movimientos||[]).filter(function(m){return m.lote===i.lote&&m.material_id===i.material_id;});
    if(!mv.length){tb.innerHTML='<tr><td colspan=5 style=text-align:center>Sin movimientos</td></tr>';return;}
    tb.innerHTML=mv.map(function(m){var f=m.fecha?m.fecha.substring(0,16).replace("T"," "):"";return "<tr><td>"+m.tipo+"</td><td>"+m.cantidad+"</td><td>"+f+"</td><td>"+(m.observaciones||"")+"</td><td>"+(m.operador||"")+"</td></tr>";}).join("");
  }catch(e){tb.innerHTML='<tr><td colspan=5>Error</td></tr>';}
}

async function confirmarAjuste(){
  var fis=parseFloat(document.getElementById('ajuste-fisico').value);
  if(isNaN(fis)||fis<0){alert('Cantidad inválida');return;}
  var dif=Math.round((fis-_ajDat.sa)*100)/100;
  if(dif===0){alert('El stock físico coincide con el sistema');return;}
  var tipo=dif>0?'Entrada':'Salida';
  var obs='AJUSTE: '+(document.getElementById('ajuste-obs').value||'Conteo físico')+' | Op: '+OPER_ACTUAL;
  try{
    var r=await fetch('/api/movimientos',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({material_id:_ajDat.mid,material_nombre:_ajDat.mn,
        cantidad:Math.abs(dif),tipo:tipo,observaciones:obs,lote:_ajDat.lt,operador:OPER_ACTUAL})});
    var res=await r.json();
    var sg=dif>0?'+':'';
    document.getElementById('ajuste-msg').innerHTML='<div class="alert-success">✓ Ajuste registrado: '+sg+dif.toLocaleString()+'g ('+tipo+'). Stock actualizado.</div>';
    setTimeout(function(){cerrarAjuste();loadStock();},2500);
  }catch(e){document.getElementById('ajuste-msg').innerHTML='<div class="alert-error">Error al registrar ajuste</div>';}
}

async function exportarExcelStock(){
  var r=await fetch('/api/lotes'),d=await r.json(),L=d.lotes||[];
  if(!L.length){alert('Sin datos');return;}
  var h='Codigo,Nombre,Lote,Cantidad_g,Estanteria,Posicion,FechaVenc,Estado';
  var rows=L.map(function(i){return [i.material_id,i.material_nombre,i.lote,i.cantidad_g,i.estanteria,i.posicion,i.fecha_vencimiento,i.alerta].join(',');});
  dlCSV('Stock_'+fhoy()+'.csv',[h].concat(rows).join(String.fromCharCode(10)));
}
async function exportarExcelMovimientos(){
  var r=await fetch('/api/movimientos'),d=await r.json(),M=d.movimientos||[];
  if(!M.length){alert('Sin movimientos');return;}
  var h='Material,Cantidad_g,Tipo,Fecha,Observaciones,Operador';
  var rows=M.map(function(m){return [m.material_nombre,m.cantidad,m.tipo,m.fecha,(m.observaciones||'').replace(/,/g,';'),m.operador||''].join(',');});
  dlCSV('Movimientos_'+fhoy()+'.csv',[h].concat(rows).join(String.fromCharCode(10)));
}
async function exportarExcelProducciones(){
  var r=await fetch('/api/produccion'),d=await r.json(),P=d.producciones||[];
  if(!P.length){alert('Sin producciones');return;}
  var h='Producto,Cantidad_kg,Fecha,Operador,Estado';
  var rows=P.map(function(p){return [p.producto,p.cantidad,p.fecha,p.operador||'',p.estado].join(',');});
  dlCSV('Producciones_'+fhoy()+'.csv',[h].concat(rows).join(String.fromCharCode(10)));
}
function fhoy(){var d=new Date();return d.getFullYear()+'-'+(d.getMonth()+1)+'-'+d.getDate();}
function dlCSV(n,csv){
  var b=new Blob([csv],{type:'text/csv'});
  var u=URL.createObjectURL(b);
  var a=document.createElement('a');
  a.href=u;a.download=n;
  document.body.appendChild(a);a.click();
  document.body.removeChild(a);URL.revokeObjectURL(u);
}
function descargarCSV(nombre,cols,rows){
  var sep=',';
  var lines=[cols.join(sep)];
  rows.forEach(function(r){
    lines.push(r.map(function(c){
      var s=c==null?'':String(c);
      if(s.indexOf(',')>=0||s.indexOf('"')>=0){s='"'+s.replace(/"/g,'""')+'"';}
      return s;
    }).join(sep));
  });
  var csv=lines.join(String.fromCharCode(10));
  var blob=new Blob([csv],{type:'text/csv'});
  var url=URL.createObjectURL(blob);
  var a=document.createElement('a');
  a.href=url;a.download=nombre;
  document.body.appendChild(a);a.click();document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

async function cargarHistProd(){
  try{
    var r=await fetch('/api/produccion'),d=await r.json();
    var ps=d.producciones||[];
    var tb=document.getElementById('hist-prod-body');
    if(!tb)return;
    if(!ps.length){tb.innerHTML='<tr><td colspan="5" style="text-align:center;color:#999;padding:16px;">Sin producciones registradas</td></tr>';return;}
    tb.innerHTML=ps.map(function(p){
      var f=p.fecha?p.fecha.substring(0,16).replace('T',' '):'';
      var op=p.operador||'<span style="color:#bbb;font-style:italic;">-</span>';
      return '<tr><td style="font-weight:600;">'+p.producto+'</td><td style="text-align:right;font-weight:700;color:#2B7A78;">'+p.cantidad.toLocaleString()+' kg</td><td style="font-size:0.85em;color:#666;">'+f+'</td><td>'+op+'</td><td style="text-align:center;"><span style="background:#d4edda;color:#155724;padding:2px 8px;border-radius:10px;font-size:0.8em;font-weight:600;">'+p.estado+'</span></td></tr>';
    }).join('');
  }catch(e){}
}


function switchTab(n,btn){
  document.querySelectorAll('.tab-content').forEach(function(t){t.classList.remove('active');});
  document.querySelectorAll('.tab-button').forEach(function(b){b.classList.remove('active');});
  document.getElementById(n).classList.add('active');
  if(btn) btn.classList.add('active');
  if(n==='stock') loadStock();
  if(n==='formulas'||n==='produccion') loadFormulas();
  if(n==='ingreso') initIngreso();
  if(n==='abc') loadABC();
  if(n==='alertas'){ loadAlertas(); loadAlertasReabas(); loadVenc30(); loadAlertasMEE(); }
  if(n==='stock') loadMEE();
  if(n==='produccion') cargarHistProd();
  if(n==='movimientos') loadMovimientos();
}

var _charts={};
async function loadDashboard(){
  try{
    var r=await fetch('/api/inventario'), d=await r.json();
    document.getElementById('stock-total').textContent=((d.stock_total||0)/1000).toFixed(1)+' kg';
    document.getElementById('materiales-count').textContent=d.movimientos||'0';
    document.getElementById('producciones-count').textContent=d.producciones||'0';
    fetch('/api/alertas-reabastecimiento').then(function(r2){return r2.json();}).then(function(ar){
      var n=ar.alertas?ar.alertas.length:0;
      var el=document.getElementById('alertas-count');
      if(el) el.textContent=n>0?n+' alertas!':'OK';
      var panel=document.getElementById('dash-alertas-rapidas');
      if(panel&&n>0){
        panel.style.display='block';
        var lista=document.getElementById('dash-alertas-lista');
        if(lista) lista.innerHTML=ar.alertas.slice(0,3).map(function(a){
          return '<div style="margin-bottom:4px;"><b>'+a.codigo_mp+'</b> '+a.nombre+' - Stock: '+a.stock_actual.toLocaleString()+'g / Min: '+a.stock_minimo.toLocaleString()+'g <span style="color:#cc0000;font-weight:700;">Deficit: '+a.deficit.toLocaleString()+'g</span></div>';
        }).join('')+(n>3?'<div style="color:#888;font-size:0.85em;">... y '+(n-3)+' mas</div>':'');
      } else if(panel){ panel.style.display='none'; }
    }).catch(function(){});
  }catch(e){ console.error(e); }
}

async function loadDashboardCompleto(){
  loadDashboard();
  try{
    var r=await fetch('/api/dashboard-stats'), d=await r.json();
    var estados=d.estados_lotes||{};
    var ev=document.getElementById('dash-vencidos'); if(ev) ev.textContent=estados.VENCIDO||0;
    var ec=document.getElementById('dash-criticos'); if(ec) ec.textContent=estados.CRITICO||0;
    var ep=document.getElementById('dash-proximos'); if(ep) ep.textContent=estados.PROXIMO||0;
    var venc=d.vencimientos_por_mes||{}; var meses=Object.keys(venc);
    var ctx1=document.getElementById('chart-vencimientos');
    if(ctx1){
      if(_charts.venc){ _charts.venc.destroy(); }
      var emp=document.getElementById('chart-venc-empty');
      if(meses.length>0){
        ctx1.style.display='block'; if(emp) emp.style.display='none';
        _charts.venc=new Chart(ctx1.getContext('2d'),{
          type:'bar',
          data:{labels:meses,datasets:[{label:'Kg que vencen',data:meses.map(function(m){return venc[m].kg;}),
            backgroundColor:meses.map(function(m,i){return i===0?'rgba(204,0,0,0.7)':i<=1?'rgba(230,81,0,0.7)':'rgba(245,127,23,0.7)';}),borderRadius:4}]},
          options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,title:{display:true,text:'kg'}}}}
        });
      } else { ctx1.style.display='none'; if(emp) emp.style.display='block'; }
    }
    var top=d.top_stock||[]; var ctx2=document.getElementById('chart-top-stock');
    if(ctx2){
      if(_charts.top){ _charts.top.destroy(); }
      var emp2=document.getElementById('chart-stock-empty');
      if(top.length>0){
        ctx2.style.display='block'; if(emp2) emp2.style.display='none';
        _charts.top=new Chart(ctx2.getContext('2d'),{
          type:'bar',
          data:{labels:top.map(function(t){return t.nombre.length>18?t.nombre.substring(0,16)+'...':t.nombre;}),
            datasets:[{label:'Stock (kg)',data:top.map(function(t){return t.kg;}),backgroundColor:'rgba(102,126,234,0.7)',borderRadius:4}]},
          options:{indexAxis:'y',responsive:true,plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,title:{display:true,text:'kg'}}}}
        });
      } else { ctx2.style.display='none'; if(emp2) emp2.style.display='block'; }
    }
  }catch(e){ console.error('Stats error:',e); }
}

async function loadStock(){
  try{
    var r=await fetch('/api/lotes'), d=await r.json();
    _lotes=d.lotes||[];
    document.getElementById('stock-count').textContent=_lotes.length+' lotes';
    renderStock(_lotes);
  }catch(e){
    document.getElementById('stock-body').innerHTML='<tr><td colspan="13" style="padding:20px;color:#c00;">Error al cargar.</td></tr>';
  }
}
function renderStock(items){
  var tb=document.getElementById('stock-body');
  if(!items.length){tb.innerHTML='<tr><td colspan="13" style="text-align:center;color:#999;padding:20px;">Sin datos</td></tr>';return;}
  var bg={vencido:'#ffebeb',critico:'#fff3e0',proximo:'#fffde7',ok:'transparent'};
  var fc={vencido:'#cc0000',critico:'#e65100',proximo:'#f57f17',ok:'#1a8a1a'};
  var lb={vencido:'VENCIDO',critico:'CRITICO',proximo:'PROXIMO',ok:'VIGENTE'};
  var h='';
  items.forEach(function(i,idx){
    var a=i.alerta||'ok';
    var qc=i.cantidad_g<=0?'color:#cc0000;font-weight:700;':i.cantidad_g<500?'color:#e68a00;font-weight:700;':'color:#1a8a1a;font-weight:700;';
    var bajo_min=i.stock_min_g>0&&i.cantidad_g<i.stock_min_g;
    var min_style=bajo_min?'background:#ffebeb;color:#cc0000;font-weight:700;':'';
    var dias=i.dias_para_vencer!=null?i.dias_para_vencer:'';
    var dc=i.dias_para_vencer!=null&&i.dias_para_vencer<0?'color:#cc0000;font-weight:700;':i.dias_para_vencer<=30?'color:#e65100;font-weight:700;':'';
    h+='<tr style="background:'+bg[a]+';font-size:0.83em;">';
    h+='<td style="font-family:monospace;color:#555;">'+i.material_id+'</td>';
    h+='<td style="color:#444;font-size:0.82em;">'+i.nombre_inci+'</td>';
    h+='<td style="font-weight:600;">'+i.material_nombre+'</td>';
    h+='<td style="color:#888;">'+i.tipo+'</td>';
    h+='<td style="color:#555;">'+i.proveedor+'</td>';
    h+='<td style="text-align:right;'+min_style+'">'+i.stock_min_g.toLocaleString()+'</td>';
    h+='<td style="font-family:monospace;">'+i.lote+'</td>';
    h+='<td style="text-align:right;'+qc+'">'+i.cantidad_g.toLocaleString()+'</td>';
    h+='<td style="text-align:center;font-weight:700;color:#667eea;">'+i.estanteria+'</td>';
    h+='<td style="text-align:center;">'+i.posicion+'</td>';
    h+='<td style="text-align:center;color:'+fc[a]+';">'+i.fecha_vencimiento+'</td>';
    h+='<td style="text-align:right;'+dc+'">'+dias+'</td>';
    h+='<td style="text-align:center;"><span style="background:'+bg[a]+';color:'+fc[a]+';padding:2px 7px;border-radius:10px;font-weight:700;font-size:0.78em;border:1px solid '+fc[a]+';">'+lb[a]+'</span></td>';
    h+='<td style="text-align:center;"><button onclick="abrirAjusteIdx('+idx+')" style="padding:3px 9px;font-size:0.75em;background:#f0ad4e;color:#fff;border-radius:4px;">Ajustar</button></td>';
    h+='<td style="text-align:center;"><button onclick="verHistorialLote('+idx+')" style="padding:3px 9px;font-size:0.75em;background:#667eea;color:#fff;border-radius:4px;">Historial</button></td>';
    h+='</tr>';
  });
  tb.innerHTML=h;
}
function filterStock(){
  var q=document.getElementById('stock-search').value.toLowerCase();
  var f=_lotes.filter(function(i){
    return !q||(i.material_id.toLowerCase().includes(q)||i.material_nombre.toLowerCase().includes(q)||
               i.nombre_inci.toLowerCase().includes(q)||(i.lote||'').toLowerCase().includes(q)||
               (i.proveedor||'').toLowerCase().includes(q));
  });
  document.getElementById('stock-count').textContent=f.length+' de '+_lotes.length;
  renderStock(f);
}

async function initIngreso(){
  if(Object.keys(_cat).length===0){
    try{var r=await fetch('/api/maestro-mps'),d=await r.json();(d.mps||[]).forEach(function(mp){_cat[mp.codigo_mp]=mp;});}catch(e){}
  }
  cargarHistIngreso();
}
function ocultarDropMP(){var d=document.getElementById('mp-dropdown');if(d)d.style.display='none';}
function seleccionarMP(mp){
  document.getElementById('ing-cod').value=mp.codigo_mp;
  document.getElementById('ing-inci').value=mp.nombre_inci||'';
  document.getElementById('ing-nombre').value=mp.nombre_comercial||'';
  document.getElementById('ing-tipo').value=mp.tipo||'';
  var p=document.getElementById('ing-prov');if(p&&!p.value)p.value=mp.proveedor||'';
  var st=document.getElementById('ing-status');
  if(st){st.textContent='✓ '+mp.nombre_comercial+' ('+mp.codigo_mp+')';st.style.color='#27ae60';}
  var panel=document.getElementById('ing-nueva-mp-inline');if(panel)panel.style.display='none';
  ocultarDropMP();
}
async function buscarMPIngreso(val){
  val=(val||'').trim();
  var st=document.getElementById('ing-status'),panel=document.getElementById('ing-nueva-mp-inline'),dd=document.getElementById('mp-dropdown');
  if(val.length<2){
    if(st)st.textContent='';
    ['ing-inci','ing-nombre','ing-tipo'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='';});
    if(panel)panel.style.display='none';
    if(dd)dd.style.display='none';
    return;
  }
  try{
    var r2=await fetch('/api/maestro-mps'),d2=await r2.json(),mps=d2.mps||[];
    var busq=val.toLowerCase();
    var matches=mps.filter(function(m){
      return (m.codigo_mp||'').toLowerCase().includes(busq)||(m.nombre_comercial||'').toLowerCase().includes(busq)||(m.nombre_inci||'').toLowerCase().includes(busq);
    }).slice(0,12);
    window._mpMatches=matches;
    if(dd){
      if(!matches.length){dd.style.display='none';}
      else{
        dd.style.display='block';
        dd.innerHTML=matches.map(function(m,i){return '<div class="mp-item" style="padding:9px 14px;cursor:pointer;border-bottom:1px solid #eee;font-size:0.9em;" onmousedown="seleccionarMP(_mpMatches['+i+'])">'+'<span style="font-family:monospace;color:#667eea;font-size:0.85em;">'+m.codigo_mp+'</span> &mdash; <strong>'+m.nombre_comercial+'</strong>'+(m.proveedor?' <span style="color:#888;font-size:0.82em;">('+m.proveedor+')</span>':'')+'</div>';}).join('');
      }
    }
    var found=mps.find(function(m){return (m.codigo_mp||'').toLowerCase()===busq;});
    if(found){seleccionarMP(found);}
    else if(!matches.length){
      if(st){st.textContent='MP nueva — llena los datos';st.style.color='#e67e22';}
      if(panel)panel.style.display='block';
    } else {
      if(st){st.textContent='Selecciona una opcion de la lista';st.style.color='#667eea';}
    }
  }catch(e){if(st){st.textContent='Error buscando';st.style.color='#c0392b';}}
}

async function registrarIngreso(){
  var cod=(document.getElementById('ing-cod').value||'').toUpperCase().trim();
  var cant=parseFloat(document.getElementById('ing-cant').value)||0;
  if(!cod){alert('Ingresa el codigo MP');return;}
  if(cant<=0){alert('Ingresa una cantidad valida');return;}
  var esNueva=document.getElementById('ing-nueva-mp-inline')&&document.getElementById('ing-nueva-mp-inline').style.display!=='none';
  var data={codigo_mp:cod,nombre_comercial:document.getElementById('ing-nombre').value||'',
    lote:document.getElementById('ing-lote').value||'',cantidad:cant,operador:OPER_ACTUAL,
    fecha_vencimiento:document.getElementById('ing-vence').value||'',
    estanteria:document.getElementById('ing-est').value||'',
    posicion:document.getElementById('ing-pos').value||'',
    proveedor:document.getElementById('ing-prov').value||'',
    observaciones:document.getElementById('ing-obs').value||''};
  if(esNueva){
    data.nombre_inci=document.getElementById('ing-inci-new')?document.getElementById('ing-inci-new').value:'';
    data.tipo=document.getElementById('ing-tipo-new')?document.getElementById('ing-tipo-new').value:'';
    data.stock_minimo=parseFloat(document.getElementById('ing-smin-new')?document.getElementById('ing-smin-new').value:0)||0;
  }
  try{
    var r=await fetch('/api/recepcion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    if(r.ok){
      _ultimoIng=res;
      document.getElementById('ing-msg').innerHTML='<div class="alert-success">'+res.message+'</div>';
      await cargarHistIngreso();
    } else {document.getElementById('ing-msg').innerHTML='<div class="alert-error">'+(res.error||'Error')+'</div>';}
  }catch(e){document.getElementById('ing-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}
function generarRotuloIngreso(){
  if(!_ultimoIng){alert('Registra un ingreso primero');return;}
  window.open('/rotulo-recepcion/'+encodeURIComponent(_ultimoIng.codigo)+'/'+encodeURIComponent(_ultimoIng.lote||'SL')+'/'+(parseFloat(_ultimoIng.cantidad)||0).toFixed(1),'_blank');
}
function limpiarIngreso(){
  ['ing-cod','ing-inci','ing-nombre','ing-tipo','ing-prov','ing-lote','ing-cant','ing-vence','ing-est','ing-pos','ing-obs'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='';});ocultarFormNuevaMP();
  var st=document.getElementById('ing-status');if(st){st.textContent='';st.style.color='#667eea';}
  document.getElementById('ing-msg').innerHTML='';
}
async function cargarHistIngreso(){
  try{
    var r=await fetch('/api/movimientos'),d=await r.json();
    var entradas=(d.movimientos||[]).filter(function(m){return m.tipo==='Entrada';}).slice(0,20);
    var tb=document.querySelector('#ing-hist tbody'); if(!tb) return;
    if(!entradas.length){tb.innerHTML='<tr><td colspan="8" style="text-align:center;color:#999;">Sin entradas</td></tr>';return;}
    var h='';
    entradas.forEach(function(m){
      h+='<tr><td style="font-family:monospace;font-size:0.85em;">'+(m.material_id||'')+'</td>';
      var cat=_cat[m.material_id]||{};
      h+='<td style="font-size:0.8em;color:#444;">'+(cat.nombre_inci||'')+'</td>';
      h+='<td>'+m.material_nombre+'</td>';
      h+='<td style="font-family:monospace;">'+(m.lote||'')+'</td>';
      h+='<td style="text-align:right;font-weight:600;">'+m.cantidad.toLocaleString()+'</td>';
      h+='<td style="font-size:0.85em;">'+(m.proveedor||'')+'</td>';
      h+='<td style="color:#c0392b;font-size:0.85em;">'+(m.fecha_vencimiento?m.fecha_vencimiento.substring(0,10):'')+'</td>';
      h+='<td style="font-size:0.82em;color:#888;">'+m.fecha.substring(0,10)+'</td></tr>';
    });
    tb.innerHTML=h;
  }catch(e){}
}
function abrirRotulos(){
  var prod=document.getElementById('prod-sel')?document.getElementById('prod-sel').value:'';
  var manual=document.getElementById('prod-manual')?document.getElementById('prod-manual').value.trim():'';
  var producto=prod||manual;
  var kg=parseFloat(document.getElementById('prod-kg')?document.getElementById('prod-kg').value:0)||0;
  if(!producto){alert('Selecciona un producto primero');return;}
  if(kg<=0){alert('Ingresa la cantidad en kg');return;}
  window.open('/rotulos/'+encodeURIComponent(producto)+'/'+(parseFloat(kg)||0).toFixed(1),'_blank');
}

async function loadFormulas(){
  try{
    var r=await fetch('/api/formulas'), d=await r.json();
    fData=d.formulas||[];
    renderFormulas(fData);
    var sel=document.getElementById('prod-sel');
    if(sel){
      var cur=sel.value;
      sel.innerHTML='<option value="">-- Selecciona un producto --</option>';
      fData.forEach(function(f){var o=document.createElement('option');o.value=f.producto_nombre;o.textContent=f.producto_nombre;sel.appendChild(o);});
      sel.value=cur;
    }
  }catch(e){}
}

function renderFormulas(fl){
  var c=document.getElementById('formulas-list'); if(!c) return;
  if(!fl.length){c.innerHTML='<p style="color:#999;">Sin formulas aun.</p>';return;}
  var html='';
  fl.forEach(function(f,idx){
    var total=f.items.reduce(function(s,i){return s+i.porcentaje;},0);
    var ok=Math.abs(total-100)<0.1;
    var rows='';
    f.items.forEach(function(it){
      rows+='<tr><td style="font-family:monospace;">'+it.material_id+'</td><td>'+it.material_nombre+'</td><td>'+it.porcentaje+'%</td><td style="font-weight:600;">'+(it.porcentaje*10).toFixed(2)+'g</td></tr>';
    });
    html+='<div style="border:1px solid #dde;border-radius:8px;padding:15px;margin-bottom:12px;background:white;">';
    html+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">';
    html+='<h4 style="color:#667eea;">'+f.producto_nombre+' <span style="font-weight:normal;color:#888;font-size:0.82em;">(base '+f.unidad_base_g+'g)</span></h4>';
    html+='<div style="display:flex;gap:6px;">';
    html+='<button onclick="editFormula('+idx+')" style="background:#667eea;padding:5px 10px;font-size:0.82em;">Editar</button>';
    html+='<button onclick="delFormula('+idx+')" style="background:#cc4444;padding:5px 10px;font-size:0.82em;">Eliminar</button>';
    html+='</div></div>';
    html+='<table class="table" style="font-size:0.85em;"><thead><tr><th>Codigo MP</th><th>Material</th><th>%</th><th>g/kg</th></tr></thead><tbody>'+rows+'</tbody></table>';
    html+='<small style="color:'+(ok?'#28a745':'#e68a00')+';">Total: '+total.toFixed(2)+'%'+(ok?' OK':' revisar')+'</small>';
    html+='</div>';
  });
  c.innerHTML=html;
}

function addFRow(){
  var div=document.createElement('div');
  div.style.cssText='display:grid;grid-template-columns:140px 1fr 90px 38px;gap:6px;margin-bottom:6px;';
  div.innerHTML='<input type="text" placeholder="MP00001" class="fi-id" style="padding:7px;border:1px solid #ddd;border-radius:5px;">'
    +'<input type="text" placeholder="Nombre material" class="fi-nm" style="padding:7px;border:1px solid #ddd;border-radius:5px;">'
    +'<input type="number" placeholder="%" step="0.001" class="fi-pc" style="padding:7px;border:1px solid #ddd;border-radius:5px;" oninput="calcPct()">'
    +'<button onclick="this.parentElement.remove();calcPct();" style="background:#ff4444;color:white;border:none;border-radius:5px;cursor:pointer;padding:7px;font-size:0.9em;">x</button>';
  document.getElementById('fi-container').appendChild(div);
}

function calcPct(){
  var t=Array.from(document.querySelectorAll('.fi-pc')).reduce(function(s,i){return s+(parseFloat(i.value)||0);},0);
  var el=document.getElementById('pct-total');
  el.textContent='Total: '+t.toFixed(2)+'%';
  el.style.color=Math.abs(t-100)<0.1?'#28a745':(t>100?'#cc0000':'#e68a00');
}

async function guardarFormula(){
  var prod=document.getElementById('formula-producto').value.trim();
  if(!prod){alert('Ingresa el nombre del producto');return;}
  var base=parseFloat(document.getElementById('formula-base').value)||1000;
  var desc=document.getElementById('formula-desc').value.trim();
  var rows=document.querySelectorAll('#fi-container > div');
  var items=[];
  rows.forEach(function(row){
    var id=row.querySelector('.fi-id').value.trim();
    var nm=row.querySelector('.fi-nm').value.trim();
    var pc=parseFloat(row.querySelector('.fi-pc').value)||0;
    if(id&&nm&&pc>0) items.push({material_id:id,material_nombre:nm,porcentaje:pc});
  });
  if(!items.length){alert('Agrega al menos un ingrediente');return;}
  try{
    var r=await fetch('/api/formulas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({producto_nombre:prod,unidad_base_g:base,descripcion:desc,items:items})});
    var res=await r.json();
    document.getElementById('formula-msg').innerHTML='<div class="alert-success">'+res.message+'</div>';
    await loadFormulas();
    setTimeout(function(){document.getElementById('formula-msg').innerHTML='';},3000);
  }catch(e){document.getElementById('formula-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}

function editFormula(idx){
  var f=fData[idx]; if(!f) return;
  document.getElementById('formula-producto').value=f.producto_nombre;
  document.getElementById('formula-base').value=f.unidad_base_g;
  document.getElementById('formula-desc').value=f.descripcion||'';
  document.getElementById('fi-container').innerHTML='';
  f.items.forEach(function(item){
    addFRow();
    var rows=document.getElementById('fi-container').querySelectorAll('div');
    var row=rows[rows.length-1];
    row.querySelector('.fi-id').value=item.material_id;
    row.querySelector('.fi-nm').value=item.material_nombre;
    row.querySelector('.fi-pc').value=item.porcentaje;
  });
  calcPct();
  document.getElementById('formula-producto').scrollIntoView({behavior:'smooth'});
}

async function delFormula(idx){
  var nombre=fData[idx]?fData[idx].producto_nombre:'';
  if(!nombre||!confirm('Eliminar formula de '+nombre+'?')) return;
  await fetch('/api/formulas/'+encodeURIComponent(nombre),{method:'DELETE'});
  await loadFormulas();
}

function previewProd(){
  var prod=document.getElementById('prod-sel').value||document.getElementById('prod-manual').value.trim();
  var kg=parseFloat(document.getElementById('prod-kg').value)||0;
  var preview=document.getElementById('prod-preview');
  if(!prod||kg<=0){preview.style.display='none';return;}
  var f=fData.find(function(x){return x.producto_nombre===prod;});
  if(!f||!f.items.length){preview.style.display='none';return;}
  var g=kg*1000;
  document.getElementById('prod-preview-body').innerHTML=f.items.map(function(it){
    return '<tr><td>'+it.material_nombre+'</td><td style="text-align:right;font-weight:700;">'+((it.porcentaje/100)*g).toFixed(1)+' g</td></tr>';
  }).join('');
  preview.style.display='block';
}

async function registrarProd(){
  var prod=document.getElementById('prod-sel').value||document.getElementById('prod-manual').value.trim();
  if(!prod){alert('Ingresa un producto');return;}
  var kg=parseFloat(document.getElementById('prod-kg').value);
  if(!kg||kg<=0){alert('Ingresa una cantidad valida');return;}
  try{
    var r=await fetch('/api/produccion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({producto:prod,cantidad:kg,observaciones:document.getElementById('prod-obs').value,operador:OPER_ACTUAL})});
    var res=await r.json();
    var html='<div class="alert-success">'+res.message+'</div>';
    if(res.descuentos&&res.descuentos.length){
      html+='<div style="margin-top:8px;font-size:0.88em;color:#555;"><strong>MPs descontadas del inventario:</strong><ul style="margin-top:4px;padding-left:18px;">';
      res.descuentos.forEach(function(d){html+='<li>'+d.material+': '+d.cantidad_g.toLocaleString()+' g</li>';});
      html+='</ul></div>';
    }
    document.getElementById('prod-msg').innerHTML=html;
    document.getElementById('prod-preview').style.display='none';
    setTimeout(function(){
      document.getElementById('prod-sel').value='';
      document.getElementById('prod-manual').value='';
      document.getElementById('prod-kg').value='';
      document.getElementById('prod-obs').value='';
      document.getElementById('prod-msg').innerHTML='';
    },5000);
  }catch(e){document.getElementById('prod-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}

async function loadABC(){
  try{
    var r=await fetch('/api/analisis-abc'), d=await r.json();
    var html='';
    if(d.items&&d.items.length){
      html='<div style="overflow-x:auto;"><table class="table"><thead><tr><th>Clase</th><th>Material</th><th>Stock (g)</th><th>% Acumulado</th></tr></thead><tbody>';
      d.items.forEach(function(i){
        var bg=i.clasificacion==='A'?'#28a745':i.clasificacion==='B'?'#fd7e14':'#6c757d';
        html+='<tr><td><span style="background:'+bg+';color:white;padding:3px 10px;border-radius:10px;font-weight:700;">'+i.clasificacion+'</span></td>'
          +'<td>'+i.material+'</td><td style="text-align:right;">'+Number(i.cantidad).toLocaleString()+'</td>'
          +'<td style="text-align:right;color:#667eea;">'+i.valor+'</td></tr>';
      });
      html+='</tbody></table></div>';
    } else { html='<p style="color:#999;">Sin datos de inventario para analizar</p>'; }
    document.getElementById('abc-results').innerHTML=html;
  }catch(e){document.getElementById('abc-results').innerHTML='<div class="alert-error">Error</div>';}
}

async function loadAlertas(){
  try{
    var r=await fetch('/api/alertas'), d=await r.json();
    var tb=document.querySelector('#alertas-table tbody');
    if(d.alertas&&d.alertas.length){
      tb.innerHTML=d.alertas.map(function(a){return '<tr><td>'+a.material_nombre+'</td><td>'+a.stock_actual+'</td><td>'+a.stock_minimo+'</td><td>'+a.estado+'</td><td style="font-size:0.85em;">'+a.fecha+'</td></tr>';}).join('');
    }else{tb.innerHTML='<tr><td colspan="5" style="text-align:center;color:#999;">Sin alertas</td></tr>';}
  }catch(e){}
}

async function loadMovimientos(){
  try{
    var r=await fetch('/api/movimientos'), d=await r.json();
    var tb=document.querySelector('#mov-table tbody');
    if(d.movimientos&&d.movimientos.length){
      tb.innerHTML=d.movimientos.map(function(m){
        var t=m.tipo==='Entrada'?'<span style="color:#28a745;font-weight:600;">Entrada</span>':'<span style="color:#cc4444;font-weight:600;">Salida</span>';
        return '<tr><td>'+m.material_nombre+'</td><td style="text-align:right;">'+m.cantidad.toLocaleString()+'</td><td>'+t+'</td><td style="font-size:0.82em;color:#888;">'+m.fecha+'</td><td style="font-size:0.82em;color:#888;">'+m.observaciones+'</td></tr>';
      }).join('');
    }else{tb.innerHTML='<tr><td colspan="5" style="text-align:center;color:#999;">Sin movimientos</td></tr>';}
  }catch(e){}
}

async function registrarMov(){
  var data={material_id:document.getElementById('mov-id').value,material_nombre:document.getElementById('mov-nombre').value,cantidad:parseFloat(document.getElementById('mov-cant').value),tipo:document.getElementById('mov-tipo').value,observaciones:document.getElementById('mov-obs').value};
  try{
    var r=await fetch('/api/movimientos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    document.getElementById('mov-msg').innerHTML='<div class="alert-success">'+res.message+'</div>';
    loadMovimientos();
  }catch(e){document.getElementById('mov-msg').innerHTML='<div class="alert-error">Error</div>';}
}

async function loadVenc30(){
  try{
    var r=await fetch('/api/lotes'),d=await r.json(),lotes=d.lotes||[];
    var prox=lotes.filter(function(l){return l.dias_para_vencer!=null&&l.dias_para_vencer>=0&&l.dias_para_vencer<=30;});
    var div=document.getElementById('venc30-content');if(!div)return;
    if(!prox.length){div.innerHTML='<span style="color:#28a745;font-weight:600;">Sin lotes proximos a vencer en 30 dias.</span>';return;}
    prox.sort(function(a,b){return a.dias_para_vencer-b.dias_para_vencer;});
    div.innerHTML='<table class="table" style="margin-top:8px;"><thead><tr><th>Codigo</th><th>Material</th><th>Lote</th><th style="text-align:right;">Cantidad(g)</th><th>Vence</th><th style="text-align:center;">Dias</th></tr></thead><tbody>'+
    prox.map(function(l){
      var c2=l.dias_para_vencer<=7?'color:#cc0000;font-weight:700;':'color:#e65100;font-weight:600;';
      return '<tr><td style="font-family:monospace;font-size:0.82em;">'+l.material_id+'</td><td style="font-weight:600;">'+l.material_nombre+'</td><td style="font-family:monospace;font-size:0.82em;">'+l.lote+'</td><td style="text-align:right;">'+l.cantidad_g.toLocaleString()+'</td><td>'+l.fecha_vencimiento+'</td><td style="text-align:center;'+c2+'">'+l.dias_para_vencer+'d</td></tr>';
    }).join('')+'</tbody></table>';
  }catch(e){}
}
async function loadAlertasReabas(){
  try{
    var r=await fetch('/api/alertas-reabastecimiento'), d=await r.json();
    var alertas=d.alertas||[];
    var tb=document.getElementById('reabas-body');
    if(!tb) return;
    if(!alertas.length){
      tb.innerHTML='<tr><td colspan="7" style="text-align:center;color:#28a745;padding:15px;">&#10003; Todo el stock esta sobre el minimo calculado</td></tr>';
      return;
    }
    var h='';
    window._alertasData=alertas;
    alertas.forEach(function(a,ri){
      var pct=a.stock_minimo>0?Math.round((a.stock_actual/a.stock_minimo)*100):0;
      var critico=pct<25;
      var urgente=pct>=25&&pct<50;
      var color=critico?'#ffebeb':urgente?'#fff3e0':'#fffde7';
      var badge=critico?'<span style="background:#cc0000;color:white;padding:2px 8px;border-radius:10px;font-size:0.82em;font-weight:700;">CRITICO</span>':
                urgente?'<span style="background:#e65100;color:white;padding:2px 8px;border-radius:10px;font-size:0.82em;font-weight:700;">URGENTE</span>':
                '<span style="background:#f57f17;color:white;padding:2px 8px;border-radius:10px;font-size:0.82em;font-weight:700;">BAJO</span>';
      h+='<tr style="background:'+color+';">';
      h+='<td style="font-family:monospace;font-size:0.85em;">'+a.codigo_mp+'</td>';
      h+='<td style="font-weight:600;">'+a.nombre+'</td>';
      h+='<td style="font-size:0.85em;color:#666;">'+a.proveedor+'</td>';
      h+='<td style="text-align:right;font-weight:600;">'+a.stock_minimo.toLocaleString()+'</td>';
      h+='<td style="text-align:right;color:#cc0000;font-weight:700;">'+a.stock_actual.toLocaleString()+'</td>';
      h+='<td style="text-align:right;color:#cc0000;font-weight:700;">'+a.deficit.toLocaleString()+'</td>';
      h+='<td style="text-align:center;">'+badge+' '+pct+'%</td>';
      var _cod=a.codigo_mp,_nom=a.nombre.substring(0,40),_def=a.deficit,_ri=ri;
      h+='<td style="text-align:center;"><button onclick="abrirSolIdx('+_ri+')" style="padding:4px 10px;font-size:0.78em;background:#2B7A78;color:white;border-radius:4px;">Solicitar</button></td>';
      h+='</tr>';
    });
    tb.innerHTML=h;
  }catch(e){
    var tb2=document.getElementById('reabas-body');
    if(tb2) tb2.innerHTML='<tr><td colspan="7" style="text-align:center;color:#999;">Carga el catalogo maestro primero (python cargar_maestro.py)</td></tr>';
  }
}

/* ===== MEE FUNCTIONS ===== */
var MEE_CATS=['Envase','Tapa','Etiqueta','Plegable','Serigrafia','Gotero','Frasco','Contorno','Otro'];

function switchIngreso(t){
  document.getElementById('ing-panel-mp').style.display=t==='mp'?'block':'none';
  document.getElementById('ing-panel-mee').style.display=t==='mee'?'block':'none';
  document.getElementById('ing-tab-mp').style.background=t==='mp'?'#2B7A78':'#eee';
  document.getElementById('ing-tab-mp').style.color=t==='mp'?'white':'#555';
  document.getElementById('ing-tab-mee').style.background=t==='mee'?'#2B7A78':'#eee';
  document.getElementById('ing-tab-mee').style.color=t==='mee'?'white':'#555';
  if(t==='mee'){cargarSelectsMEE();loadHistMEE();}
}
async function cargarSelectsMEE(){
  var r=await fetch('/api/mee'); var d=await r.json();
  _meeData=d.items||[];
  filtrarMEEIngreso();
}
function filtrarMEEIngreso(){
  var cat=document.getElementById('mee-ing-cat').value;
  var sel=document.getElementById('mee-ing-cod');
  sel.innerHTML='<option value="">-- Selecciona --</option>';
  _meeData.filter(function(x){return !cat||x.categoria===cat;}).forEach(function(x){
    var o=document.createElement('option');o.value=x.codigo;o.textContent=x.codigo+' — '+x.descripcion;sel.appendChild(o);
  });
}
async function registrarIngresoMEE(){
  var cod=document.getElementById('mee-ing-cod').value;
  var cant=parseFloat(document.getElementById('mee-ing-cant').value);
  var ref=document.getElementById('mee-ing-ref').value;
  var obs=document.getElementById('mee-ing-obs').value;
  if(!cod||!cant){document.getElementById('mee-ing-msg').innerHTML='<span style="color:red;">Selecciona material y cantidad</span>';return;}
  var r=await fetch('/api/movimientos-mee',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({codigo_mee:cod,tipo:'entrada',cantidad:cant,referencia:ref,observaciones:obs,operador:OPER_ACTUAL})});
  var d=await r.json();
  if(r.ok){document.getElementById('mee-ing-msg').innerHTML='<span style="color:green;">Entrada registrada. Stock: '+d.nuevo_stock+' und</span>';limpiarIngresoMEE();loadHistMEE();loadMEE();}
  else{document.getElementById('mee-ing-msg').innerHTML='<span style="color:red;">'+(d.error||'Error')+'</span>';}
}
function limpiarIngresoMEE(){document.getElementById('mee-ing-cod').value='';document.getElementById('mee-ing-cant').value='';document.getElementById('mee-ing-ref').value='';document.getElementById('mee-ing-obs').value='';}
async function loadHistMEE(){
  var r=await fetch('/api/movimientos-mee?limit=20'); var d=await r.json();
  var tb=document.getElementById('mee-hist-body');
  if(!d.movimientos||!d.movimientos.length){tb.innerHTML='<tr><td colspan="7" style="text-align:center;color:#999;">Sin movimientos</td></tr>';return;}
  tb.innerHTML=d.movimientos.map(function(m){
    var col=m.tipo==='entrada'?'#27ae60':m.tipo==='ajuste'?'#f39c12':'#e74c3c';
    return '<tr><td style="font-family:monospace;font-size:11px;">'+m.codigo_mee+'</td><td>'+m.descripcion+'</td><td><span style="color:'+col+';font-weight:600;">'+m.tipo+'</span></td><td style="text-align:right;font-weight:600;">'+m.cantidad+'</td><td>'+m.referencia+'</td><td>'+m.operador+'</td><td>'+m.fecha.substring(0,16)+'</td></tr>';
  }).join('');
}
async function loadMEE(){
  var cat=document.getElementById('mee-cat-filter')?document.getElementById('mee-cat-filter').value:'';
  var q=document.getElementById('mee-search')?document.getElementById('mee-search').value:'';
  var url='/api/mee?';if(cat)url+='cat='+encodeURIComponent(cat)+'&';if(q)url+='q='+encodeURIComponent(q);
  var r=await fetch(url); var d=await r.json();
  var tb=document.getElementById('mee-stock-body');
  if(!d.items||!d.items.length){tb.innerHTML='<tr><td colspan="10" style="text-align:center;color:#999;padding:20px;">Sin materiales</td></tr>';return;}
  tb.innerHTML=d.items.map(function(m){
    var deficit=m.stock_actual-m.stock_minimo;
    var est=deficit<0?'<span style="color:#e74c3c;font-weight:700;">BAJO</span>':deficit<m.stock_minimo*0.3?'<span style="color:#f39c12;font-weight:700;">ALERTA</span>':'<span style="color:#27ae60;font-weight:700;">OK</span>';
    return '<tr><td style="font-family:monospace;font-size:11px;">'+m.codigo+'</td><td>'+m.descripcion+'</td><td><span style="font-size:11px;background:#f0f4ff;padding:2px 8px;border-radius:10px;">'+m.categoria+'</span></td><td>'+m.proveedor+'</td>'
    +'<td style="text-align:right;">'+m.stock_minimo+'</td>'
    +'<td style="text-align:right;font-weight:700;">'+m.stock_actual+'</td>'
    +'<td style="text-align:center;">'+est+'</td>'
    +'<td style="text-align:center;"><button class="btn btn-ghost btn-sm" onclick="abrirAjusteMEE(\''+m.codigo+'\',\''+m.descripcion.replace(/'/g,"'")+'\','+m.stock_actual+')">Ajustar</button></td>'
    +'<td style="text-align:center;"><button class="btn btn-ghost btn-sm" onclick="verHistorialMEE(\''+m.codigo+'\')">Hist.</button></td>'
    +'<td style="text-align:center;"><button class="btn btn-sm" style="background:#4A6741;font-size:11px;" onclick="solicitarCompraMEE(\''+m.codigo+'\',\''+m.descripcion.replace(/'/g,"'")+'\','+m.stock_actual+','+m.stock_minimo+')">Solicitar</button></td>'
    +'</tr>';
  }).join('');
}
function abrirNuevoMEE(){document.getElementById('nuevo-mee-form').style.display='block';}
async function crearMEE(){
  var cod=document.getElementById('nmee-cod').value.trim().toUpperCase();
  var desc=document.getElementById('nmee-desc').value.trim();
  var cat=document.getElementById('nmee-cat').value;
  var prov=document.getElementById('nmee-prov').value.trim();
  var stock=parseFloat(document.getElementById('nmee-stock').value)||2000;
  var smin=parseFloat(document.getElementById('nmee-min').value)||1000;
  if(!cod||!desc){document.getElementById('nmee-msg').innerHTML='<span style="color:red;">Codigo y descripcion requeridos</span>';return;}
  var r=await fetch('/api/mee',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({codigo:cod,descripcion:desc,categoria:cat,proveedor:prov,stock_actual:stock,stock_minimo:smin})});
  var d=await r.json();
  if(r.ok){document.getElementById('nmee-msg').innerHTML='<span style="color:green;">Creado exitosamente</span>';document.getElementById('nuevo-mee-form').style.display='none';loadMEE();}
  else{document.getElementById('nmee-msg').innerHTML='<span style="color:red;">'+(d.error||'Error')+'</span>';}
}
async function abrirAjusteMEE(cod,desc,stock){
  if(!OPER_ACTUAL){alert('Selecciona tu nombre primero');return;}
  var nuevo=prompt('Ajuste de stock: '+cod+' — '+desc+'\nStock actual: '+stock+' und\nNuevo valor:');
  if(nuevo===null||nuevo==='')return;
  var n=parseFloat(nuevo);if(isNaN(n)||n<0){alert('Valor invalido');return;}
  var obs=prompt('Motivo del ajuste:','Inventario fisico');
  var r=await fetch('/api/mee/'+encodeURIComponent(cod)+'/ajuste',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nuevo_stock:n,observaciones:obs||'Ajuste',operador:OPER_ACTUAL})});
  var d=await r.json();
  if(d.ok){alert('Ajuste registrado. Stock: '+d.nuevo_stock+' und');loadMEE();}
  else alert('Error: '+(d.error||''));
}
async function verHistorialMEE(cod){
  var r=await fetch('/api/movimientos-mee?codigo='+encodeURIComponent(cod)+'&limit=30');
  var d=await r.json();
  var rows=d.movimientos||[];
  var html='<div style="max-height:400px;overflow-y:auto;"><table style="width:100%;border-collapse:collapse;font-size:13px;">'
    +'<thead style="background:#2B7A78;color:white;"><tr><th style="padding:7px;">Tipo</th><th>Cant.</th><th>Referencia</th><th>Operador</th><th>Fecha</th></tr></thead><tbody>'
    +rows.map(function(m){
      var col=m.tipo==='entrada'?'#27ae60':m.tipo==='ajuste'?'#f39c12':'#e74c3c';
      return '<tr style="border-bottom:1px solid #eee;"><td style="padding:6px;color:'+col+';font-weight:600;">'+m.tipo+'</td><td style="padding:6px;text-align:right;font-weight:700;">'+m.cantidad+'</td><td style="padding:6px;">'+m.referencia+'</td><td style="padding:6px;">'+m.operador+'</td><td style="padding:6px;font-size:11px;">'+m.fecha.substring(0,16)+'</td></tr>';
    }).join('')+'</tbody></table></div>';
  document.getElementById('modal-ajuste-body').innerHTML='<div style="padding:16px;"><h3 style="color:#2B7A78;">Historial — '+cod+'</h3>'+html+'</div>';
  document.getElementById('modal-ajuste').style.display='flex';
}
async function solicitarCompraMEE(cod,desc,stock,smin){
  var cant=prompt('Solicitar compra para: '+desc+'\nStock actual: '+stock+' und / Minimo: '+smin+' und\nCantidad a solicitar:');
  if(!cant||isNaN(parseFloat(cant)))return;
  var data={
    solicitante:OPER_ACTUAL||'Sistema',
    area:'Produccion',empresa:'Espagiria',categoria:'Envase y Empaque',tipo:'Compra',
    urgencia:'Urgente',observaciones:'Solicitud automatica desde alerta MEE',
    items:[{codigo_mp:cod,nombre_mp:desc,cantidad_g:parseFloat(cant),unidad:'und',valor_estimado:0}]
  };
  var r=await fetch('/api/solicitudes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  var d=await r.json();
  if(r.ok)alert('Solicitud creada: '+d.numero+'\nVisible en modulo Compras > Solicitudes');
  else alert('Error: '+(d.error||''));
}
async function loadAlertasMEE(){
  var r=await fetch('/api/alertas-mee'); var d=await r.json();
  var tb=document.getElementById('mee-alertas-body');
  if(!d.alertas||!d.alertas.length){tb.innerHTML='<tr><td colspan="8" style="text-align:center;color:green;padding:16px;">Todo el stock MEE por encima del minimo</td></tr>';return;}
  tb.innerHTML=d.alertas.map(function(m){
    var def=m.stock_actual-m.stock_minimo;
    var niv=def<-m.stock_minimo?'<span style="color:#e74c3c;font-weight:700;">CRITICO</span>':'<span style="color:#f39c12;font-weight:700;">BAJO</span>';
    return '<tr><td style="font-family:monospace;font-size:11px;">'+m.codigo+'</td><td>'+m.descripcion+'</td>'
    +'<td><span style="background:#f0f4ff;padding:2px 8px;border-radius:10px;font-size:11px;">'+m.categoria+'</span></td>'
    +'<td style="text-align:right;">'+m.stock_minimo+'</td>'
    +'<td style="text-align:right;font-weight:700;color:#e74c3c;">'+m.stock_actual+'</td>'
    +'<td style="text-align:right;color:#e74c3c;font-weight:700;">'+def+'</td>'
    +'<td style="text-align:center;">'+niv+'</td>'
    +'<td style="text-align:center;"><button class="btn btn-sm" style="background:#4A6741;font-size:11px;" onclick="solicitarCompraMEE(\''+m.codigo+'\',\''+m.descripcion.replace(/'/g,"'")+'\','+m.stock_actual+','+m.stock_minimo+')">Solicitar</button></td>'
    +'</tr>';
  }).join('');
}
async function generarOCsDesdeAlertasMEE(){
  var r=await fetch('/api/alertas-mee'); var d=await r.json();
  if(!d.alertas||!d.alertas.length){alert('No hay alertas MEE activas');return;}
  var items=d.alertas.map(function(m){return {codigo_mp:m.codigo,nombre_mp:m.descripcion,cantidad_g:Math.max(m.stock_minimo*2-m.stock_actual,1),precio_unitario:0};});
  var r2=await fetch('/api/ordenes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({proveedor:'Por asignar',observaciones:'OC automatica desde alertas MEE',items:items,creado_por:OPER_ACTUAL||'Sistema'})});
  var d2=await r2.json();
  if(r2.ok)alert('OC creada: '+d2.numero_oc+'\nVisible en Compras > Ordenes');
  else alert('Error: '+(d2.error||''));
}
/* MEE en producción */
async function iniciarRegistroProd(){
  var prod=document.getElementById('prod-sel').value||document.getElementById('prod-manual').value;
  var kg=parseFloat(document.getElementById('prod-kg').value);
  if(!prod||!kg||kg<=0){document.getElementById('prod-msg').innerHTML='<span style="color:red;">Completa producto y cantidad</span>';return;}
  // Registrar producción MP
  var obs=document.getElementById('prod-obs').value;
  var pres=document.getElementById('prod-presentacion').value;
  var r=await fetch('/api/produccion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({producto:prod,cantidad_kg:kg,observaciones:obs,presentacion:pres,operador:OPER_ACTUAL})});
  var d=await r.json();
  if(!r.ok){document.getElementById('prod-msg').innerHTML='<span style="color:red;">'+(d.error||'Error')+'</span>';return;}
  document.getElementById('prod-msg').innerHTML='<span style="color:green;">&#10003; Produccion registrada: '+d.lote+'</span>';
  _prodPendiente={lote:d.lote};
  // Cargar MEE catalogos y mostrar panel
  var rm=await fetch('/api/mee?limit=500'); var dm=await rm.json();
  _meeData=dm.items||[];
  renderMEEConsumoRows();
  document.getElementById('mee-consumo-panel').style.display='block';
  document.getElementById('mee-consumo-panel').scrollIntoView({behavior:'smooth'});
}
function renderMEEConsumoRows(){
  var cats=['Envase','Tapa','Etiqueta','Plegable','Serigrafia','Gotero','Otro'];
  var html=cats.map(function(cat){
    var opts=_meeData.filter(function(x){return x.categoria===cat||cat==='Otro';});
    if(cat!=='Otro') opts=_meeData.filter(function(x){return x.categoria===cat;});
    var optsHtml='<option value="__NA__">No aplica</option>'+opts.map(function(x){return '<option value="'+x.codigo+'">'+x.codigo+' — '+x.descripcion+'</option>';}).join('');
    return '<div style="display:grid;grid-template-columns:110px 1fr 140px;gap:10px;align-items:center;margin-bottom:10px;padding:10px;background:white;border-radius:8px;border:1px solid #e0e0e0;">'
      +'<span style="font-size:0.85em;font-weight:700;color:#4A6741;">'+cat+'</span>'
      +'<select id="mee-cons-'+cat+'" onchange="toggleMEECant(\''+cat+'\')" style="width:100%;font-size:0.85em;">'+optsHtml+'</select>'
      +'<input type="number" id="mee-cant-'+cat+'" placeholder="Cantidad (und)" min="0" style="font-size:0.85em;display:none;">'
      +'</div>';
  }).join('');
  document.getElementById('mee-rows-container').innerHTML=html;
}
function toggleMEECant(cat){
  var sel=document.getElementById('mee-cons-'+cat).value;
  document.getElementById('mee-cant-'+cat).style.display=sel==='__NA__'?'none':'block';
  if(sel!=='__NA__') document.getElementById('mee-cant-'+cat).focus();
}
async function confirmarProdCompleta(){
  if(!_prodPendiente){alert('No hay produccion pendiente');return;}
  var cats=['Envase','Tapa','Etiqueta','Plegable','Serigrafia','Gotero','Otro'];
  var consumos=[];
  for(var i=0;i<cats.length;i++){
    var cat=cats[i];
    var sel=document.getElementById('mee-cons-'+cat);
    if(!sel)continue;
    var cod=sel.value;
    if(cod==='__NA__')continue;
    var cant=parseFloat(document.getElementById('mee-cant-'+cat).value)||0;
    if(cod&&cant>0)consumos.push({codigo_mee:cod,cantidad:cant,referencia:_prodPendiente.lote});
  }
  if(consumos.length>0){
    var r=await fetch('/api/movimientos-mee/lote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({movimientos:consumos,operador:OPER_ACTUAL,referencia:_prodPendiente.lote})});
    var d=await r.json();
    if(!r.ok){document.getElementById('mee-consumo-msg').innerHTML='<span style="color:red;">Error al registrar MEE: '+(d.error||'')+'</span>';return;}
  }
  document.getElementById('mee-consumo-panel').style.display='none';
  document.getElementById('mee-consumo-msg').innerHTML='';
  _prodPendiente=null;
  var nm=consumos.length;
  document.getElementById('prod-msg').innerHTML='<span style="color:green;font-size:1em;">&#10003; Produccion completa: '+nm+' tipo(s) de MEE descontados.</span>';
  cargarHistProd(); loadMEE();
}
function cancelarMEEConsumoProd(){
  document.getElementById('mee-consumo-panel').style.display='none';
  _prodPendiente=null;
}


window.onload=function(){/* Data loads after operator confirms name */};
function mostrarFormNuevaMP(){
  var panel=document.getElementById('ing-nueva-mp');
  if(panel){ panel.style.display='block'; panel.scrollIntoView({behavior:'smooth',block:'nearest'}); }
}
function ocultarFormNuevaMP(){
  var panel=document.getElementById('ing-nueva-mp');
  if(panel) panel.style.display='none';
  ['nmp-cod','nmp-inci','nmp-nombre','nmp-tipo','nmp-prov'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.value='';
  });
  var ns=document.getElementById('nmp-smin'); if(ns) ns.value='500';
  var nm=document.getElementById('nmp-msg'); if(nm) nm.innerHTML='';
}
async function crearNuevaMP(){
  var cod=(document.getElementById('nmp-cod').value||'').toUpperCase().trim();
  var inci=(document.getElementById('nmp-inci').value||'').trim();
  var nombre=(document.getElementById('nmp-nombre').value||'').trim();
  if(!cod||!nombre){alert('Codigo y Nombre Comercial son obligatorios');return;}
  var data={codigo_mp:cod,nombre_inci:inci,nombre_comercial:nombre,
    tipo:(document.getElementById('nmp-tipo').value||'').trim(),
    proveedor:(document.getElementById('nmp-prov').value||'').trim(),
    stock_minimo:parseFloat(document.getElementById('nmp-smin').value)||500};
  try{
    var r=await fetch('/api/maestro-mps',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    if(r.ok){
      document.getElementById('nmp-msg').innerHTML='<div class="alert-success">MP '+cod+' creada en catalogo. Ya puedes usarla en el ingreso.</div>';
      _cat[cod]=data;  // Agregar al catalogo local
      // Pre-llenar el formulario de ingreso
      var f={'ing-cod':cod,'ing-inci':inci,'ing-nombre':nombre,'ing-tipo':data.tipo,'ing-prov':data.proveedor};
      Object.keys(f).forEach(function(id){var el=document.getElementById(id);if(el)el.value=f[id];});
      var st=document.getElementById('ing-status'); if(st){st.textContent='Nueva MP creada y lista para ingresar';st.style.color='#28a745';}
    } else {
      document.getElementById('nmp-msg').innerHTML='<div class="alert-error">'+(res.error||'Error al crear')+'</div>';
    }
  }catch(e){document.getElementById('nmp-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return Response(HUB_HTML, mimetype='text/html')

@app.route('/inventarios')
def inventarios():
    return Response(DASHBOARD_HTML, mimetype='text/html')

@app.route('/login', methods=['GET','POST'])
def login():
    error = ''
    if request.method == 'POST':
        username = request.form.get('username','').strip().lower().capitalize() if request.form.get('username','').strip() else ''
        
        password = request.form.get('password','').strip()
        if username in COMPRAS_USERS and COMPRAS_USERS[username] == password:
            session['compras_user'] = username
            return redirect('/compras')
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
                           f'FEFO: {producto} x {cantidad_kg}kg', lote_n, data.get('operador','')))
                lotes_usados.append({'lote': lote_n, 'vence': str(lote_v)[:10] if lote_v else '', 'cantidad_g': g_lote})
                g_restante = round(g_restante - g_lote, 2)
            if g_restante > 0:
                c.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, observaciones, operador) VALUES (?,?,?,?,?,?,?)",
                          (mat_id, mat_nombre, g_restante, 'Salida', fecha, f'Produccion: {producto} x {cantidad_kg}kg', data.get('operador','')))
                lotes_usados.append({'lote': 'sin_lote', 'vence': '', 'cantidad_g': g_restante})
            descuentos.append({'material': mat_nombre, 'material_id': mat_id,
                                'cantidad_g': g_total, 'lotes_fefo': lotes_usados})
        conn.commit()
        conn.close()
        msg = f'Produccion registrada: {producto} x {cantidad_kg}kg (FEFO)'
        if descuentos:
            msg += f'. {len(descuentos)} MPs descontadas por FEFO.'
        return jsonify({'message': msg, 'descuentos': descuentos, 'lote': lote_ref}), 201
    c.execute('SELECT producto, cantidad, fecha, estado, operador, COALESCE(presentacion,"") FROM producciones ORDER BY fecha DESC LIMIT 50')
    prod = [{'producto': r[0], 'cantidad': r[1], 'fecha': r[2], 'estado': r[3], 'operador': r[4] or '', 'presentacion': r[5] or ''} for r in c.fetchall()]
    conn.close()
    return jsonify({'producciones': prod})


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
        cumulative += qty
        pct = (cumulative / total) * 100
        abc.append({'material': mat, 'cantidad': qty, 'valor': f'{pct:.1f}%',
                    'clasificacion': 'A' if pct <= 80 else ('B' if pct <= 95 else 'C')})
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
    c.execute("SELECT codigo_mp,nombre_inci,nombre_comercial,tipo,proveedor,stock_minimo FROM maestro_mps WHERE activo=1 ORDER BY nombre_comercial")
    rows = c.fetchall(); conn.close()
    return jsonify({'mps': [{'codigo_mp':r[0],'nombre_inci':r[1],'nombre_comercial':r[2],'tipo':r[3],'proveedor':r[4],'stock_minimo':r[5]} for r in rows]})

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
    # Si la MP es nueva y viene con datos, crearla en el catalogo
    if not mp and (d.get('nombre_inci') or d.get('nombre_comercial')):
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, tipo, proveedor, stock_minimo) VALUES (?,?,?,?,?,?)",
                  (codigo, d.get('nombre_inci',''), nombre, d.get('tipo',''), proveedor, d.get('stock_minimo',0)))
        conn.commit()
    lote = (d.get('lote') or '').strip()
    if not lote or lote.upper()=='AUTO':
        from datetime import date; lote = f"ESP{date.today().strftime('%y%m%d')}{codigo[-3:]}"
    c.execute("""INSERT INTO movimientos
                 (material_id,material_nombre,cantidad,tipo,fecha,observaciones,
                  lote,fecha_vencimiento,estanteria,posicion,proveedor,estado_lote,operador)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (codigo,nombre,float(d.get('cantidad',0)),'Entrada',datetime.now().isoformat(),
               d.get('observaciones','Ingreso MP'),lote,d.get('fecha_vencimiento',''),
               d.get('estanteria',''),d.get('posicion',''),proveedor,'VIGENTE',
               d.get('operador','')))
    conn.commit(); conn.close()
    return jsonify({'message': f'{nombre} ingresada. Lote: {lote}','lote':lote,'codigo':codigo,'nombre':nombre,'cantidad':d.get('cantidad',0)}), 201

@app.route('/api/reset-movimientos', methods=['POST'])
def reset_mov():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("DELETE FROM movimientos"); conn.commit(); conn.close()
    return jsonify({'message': 'Borrado'})

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
    h+=('<div class="ph"><b>Rotulo de Recepcion</b><button class="pb" onclick="window.print()">Imprimir</button></div>'
        '<div class="r"><div class="rh"><span style="font-weight:bold;font-size:11pt;display:block;margin-bottom:3px;">ROTULO DE INGRESO DE MATERIA PRIMA</span>'
        '<span style="font-size:7.5pt;opacity:0.8;">Espagiria Laboratorios | PRD-REC-001 | '+hoy+'</span></div>'
        '<div class="lote"><div style="font-size:9pt;color:#888;margin-bottom:4px;">NUMERO DE LOTE — CODIGO DE BARRAS</div>'
        '<div class="lnum">'+lote+'</div>'
        '<svg id="bc" style="margin-top:6px;"></svg>'
        '<div style="font-size:7pt;color:#888;margin-top:2px;">'+bv+'</div>'
        '</div><table>'
        '<tr><td class="l">Codigo MP:</td><td style="font-weight:700;">'+codigo+'</td></tr>'
        '<tr><td class="l">Nombre INCI:</td><td style="font-size:0.9em;color:#444;">'+ni+'</td></tr>'
        '<tr><td class="l">Nombre Comercial:</td><td style="font-weight:700;">'+nc+'</td></tr>'
        '<tr><td class="l">Tipo:</td><td>'+tp+'</td></tr>'
        '<tr><td class="l">Proveedor:</td><td style="font-weight:700;">'+pv+'</td></tr>'
        '<tr><td class="l">Cantidad:</td><td style="color:#27ae60;font-weight:700;">'+f"{cantidad:,.0f} g"+'</td></tr>'
        '<tr><td class="l">Vencimiento:</td><td style="color:#c0392b;font-weight:700;">'+fv+'</td></tr>'
        '<tr><td class="l">Ubicacion:</td><td>Est. '+ub+'</td></tr>'
        '<tr><td class="l">N Recepcion:</td><td>'+nr+'</td></tr>'
        '<tr><td class="l">Recibido por:</td><td style="height:30px;"></td></tr>'
        '<tr><td class="l">Verificado por:</td><td style="height:30px;"></td></tr>'
        '</table>'
        '<div style="background:#ecf0f1;padding:4px 10px;font-size:7.5pt;color:#888;text-align:center;">Ingreso registrado al sistema | '+hoy+'</div>'
        '</div>'
        '<script>window.onload=function(){try{JsBarcode("#bc","'+bv+'",{format:"CODE128",width:1.5,height:45,displayValue:false,margin:0});}catch(e){}}</script>'
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
            c.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_solicitada, unidad) VALUES (?,?,?,?,?)",
                      (numero_oc, item['codigo_mp'], item['nombre_mp'], item['cantidad_pedir'], 'g'))
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
        c.execute("INSERT INTO ordenes_compra (numero_oc,fecha,estado,proveedor,observaciones,creado_por,fecha_entrega_est) VALUES (?,?,?,?,?,?,?)",
                  (numero_oc, datetime.now().isoformat(), 'Pendiente', d['proveedor'],
                   d.get('observaciones',''), d.get('creado_por',''), d.get('fecha_entrega_est','')))
        for it in (d.get('items') or []):
            subtotal = round((it.get('cantidad_g',0)) * (it.get('precio_unitario',0)), 2)
            c.execute("INSERT INTO ordenes_compra_items (numero_oc,codigo_mp,nombre_mp,cantidad_g,precio_unitario,subtotal) VALUES (?,?,?,?,?,?)",
                      (numero_oc, it.get('codigo_mp',''), it.get('nombre_mp',''),
                       it.get('cantidad_g',0), it.get('precio_unitario',0), subtotal))
        conn.commit(); conn.close()
        return jsonify({'message': f'OC {numero_oc} creada', 'numero_oc': numero_oc}), 201
    c.execute("""SELECT o.numero_oc, o.fecha, o.estado, o.proveedor, o.fecha_entrega_est,
                        o.observaciones, o.creado_por, COUNT(i.id) as num_items
                 FROM ordenes_compra o LEFT JOIN ordenes_compra_items i ON o.numero_oc=i.numero_oc
                 GROUP BY o.numero_oc ORDER BY o.fecha DESC LIMIT 100""")
    cols = ['numero_oc','fecha','estado','proveedor','fecha_entrega_est','observaciones','creado_por','num_items']
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
    oc = c.fetchone()
    c.execute("SELECT * FROM ordenes_compra_items WHERE numero_oc=?", (numero_oc,))
    items = c.fetchall(); conn.close()
    if not oc: return jsonify({'error': 'OC no encontrada'}), 404
    return jsonify({'oc': oc, 'items': items})

@app.route('/api/proveedores-compras', methods=['GET','POST'])
def handle_proveedores_compras():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json
        if not d.get('nombre'): conn.close(); return jsonify({'error': 'Nombre requerido'}), 400
        try:
            c.execute("INSERT INTO proveedores (nombre,contacto,email,telefono,categoria,condiciones_pago,fecha_creacion) VALUES (?,?,?,?,?,?,?)",
                      (d['nombre'],d.get('contacto',''),d.get('email',''),d.get('telefono',''),
                       d.get('categoria',''),d.get('condiciones_pago',''),datetime.now().isoformat()))
            conn.commit(); conn.close()
            return jsonify({'message': f"Proveedor '{d['nombre']}' creado"}), 201
        except Exception as e: conn.close(); return jsonify({'error': str(e)}), 400
    c.execute("SELECT nombre,contacto,email,telefono,categoria,condiciones_pago FROM proveedores WHERE activo=1 ORDER BY nombre")
    cols = ['nombre','contacto','email','telefono','categoria','condiciones_pago']
    provs = [dict(zip(cols, r)) for r in c.fetchall()]; conn.close()
    return jsonify({'proveedores': provs})

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
    cur.execute("SELECT estado, proveedor FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    oc_row = cur.fetchone()
    if not oc_row:
        conn.close(); return jsonify({'error': 'OC no encontrada'}), 404
    prov_nombre = oc_row[1] or ''
    cur.execute("SELECT codigo_mp, nombre_mp, cantidad_g FROM ordenes_compra_items WHERE numero_oc=?", (numero_oc,))
    items_oc = cur.fetchall()
    fecha = datetime.now().isoformat()
    for item in items_oc:
        codigo, nombre, cantidad = item
        cur.execute("""INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, observaciones, proveedor, operador)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (codigo, nombre, cantidad, 'ingreso', fecha,
                   f'Recepcion OC {numero_oc}', prov_nombre, session.get('compras_user','')))
    cur.execute("UPDATE ordenes_compra SET estado='Recibida' WHERE numero_oc=?", (numero_oc,))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'numero_oc': numero_oc, 'ingresos': len(items_oc)})


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

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
