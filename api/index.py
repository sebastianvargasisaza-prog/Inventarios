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
    seed_compromisos(c)
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

RRHH_HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>RRHH — HHA Group</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#f5f4f0;color:#1C1917;font-size:14px;}
header{background:#fff;border-bottom:1px solid #e5e3e0;padding:0 24px;position:sticky;top:0;z-index:100;}
.header-top{display:flex;align-items:center;gap:12px;padding:12px 0 0;}
.header-top h1{font-size:17px;font-weight:700;color:#1C1917;flex:1;}
.header-top a{font-size:12px;color:#888;text-decoration:none;}
.header-top a:hover{color:#6d28d9;}
.user-chip{font-size:12px;background:#f0ede8;padding:4px 10px;border-radius:20px;color:#666;}
nav{display:flex;gap:0;overflow-x:auto;margin-top:4px;}
.tab{padding:11px 15px;background:none;border:none;border-bottom:3px solid transparent;cursor:pointer;font-size:13px;color:#888;white-space:nowrap;font-weight:500;}
.tab:hover{color:#1C1917;}
.tab.active{color:#6d28d9;border-bottom-color:#6d28d9;font-weight:700;}
main{max-width:1150px;margin:0 auto;padding:24px 16px;}
.page{display:none;}.page.active{display:block;}
/* KPIs */
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px;}
@media(max-width:900px){.kpi-grid{grid-template-columns:repeat(2,1fr);}}
.kpi{background:#fff;border-radius:12px;padding:18px 20px;border:1px solid #e8e5e0;border-left:4px solid #6d28d9;}
.kpi.green{border-left-color:#16a34a;}.kpi.amber{border-left-color:#d97706;}.kpi.red{border-left-color:#dc2626;}
.kpi-val{font-size:30px;font-weight:800;color:#1C1917;line-height:1;}
.kpi-lbl{font-size:11px;color:#888;margin-top:5px;text-transform:uppercase;letter-spacing:.4px;}
.kpi-sub{font-size:11px;color:#a8a29e;margin-top:2px;}
/* Cards */
.card{background:#fff;border:1px solid #e8e5e0;border-radius:12px;padding:20px;margin-bottom:18px;}
.card-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;}
.card-hd h2{font-size:14px;font-weight:700;color:#1C1917;}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:18px;}
@media(max-width:700px){.two-col{grid-template-columns:1fr;}}
/* Empleados grid */
.emp-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px;}
.emp-card{background:#fff;border:1px solid #e8e5e0;border-radius:12px;padding:18px;cursor:pointer;transition:all .2s;}
.emp-card:hover{border-color:#6d28d9;box-shadow:0 4px 16px rgba(109,40,217,.1);transform:translateY(-2px);}
.emp-avatar{width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:700;color:#fff;margin-bottom:12px;}
.emp-name{font-size:14px;font-weight:700;color:#1C1917;margin-bottom:2px;}
.emp-cargo{font-size:12px;color:#78716c;margin-bottom:8px;}
.emp-meta{display:flex;gap:6px;flex-wrap:wrap;}
/* Badges */
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;}
.badge-activo{background:#d1fae5;color:#065f46;}
.badge-inactivo{background:#fee2e2;color:#991b1b;}
.badge-esp{background:#ede9fe;color:#5b21b6;}
.badge-ani{background:#fef3c7;color:#92400e;}
.badge-hha{background:#dbeafe;color:#1e40af;}
.badge-indef{background:#f1f5f9;color:#475569;}
.badge-fijo{background:#fef9c3;color:#713f12;}
.badge-ps{background:#f0fdf4;color:#166534;}
/* Tables */
table{width:100%;border-collapse:collapse;font-size:13px;}
th{background:#f9f8f7;padding:9px 12px;text-align:left;font-weight:600;color:#57534e;border-bottom:1px solid #e7e5e4;font-size:11px;text-transform:uppercase;letter-spacing:.4px;}
td{padding:9px 12px;border-bottom:1px solid #f5f4f2;vertical-align:middle;}
tr:hover td{background:#fafaf8;}
td input[type=number]{width:90px;padding:5px 8px;border:1px solid #d6d3d1;border-radius:5px;font-size:13px;text-align:right;}
/* Buttons */
.btn{padding:8px 16px;border:none;border-radius:7px;cursor:pointer;font-size:13px;font-weight:600;}
.btn-primary{background:#6d28d9;color:#fff;}.btn-primary:hover{background:#5b21b6;}
.btn-success{background:#16a34a;color:#fff;}.btn-success:hover{background:#15803d;}
.btn-outline{background:#fff;border:1.5px solid #6d28d9;color:#6d28d9;}
.btn-danger{background:#dc2626;color:#fff;}.btn-danger:hover{background:#b91c1c;}
.btn-ghost{background:none;border:1px solid #e0ddd8;color:#78716c;}
.btn-sm{padding:5px 10px;font-size:12px;}
/* Forms */
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.form-group{display:flex;flex-direction:column;gap:4px;}
.form-group label{font-size:12px;font-weight:600;color:#555;}
.form-group input,.form-group select,.form-group textarea{padding:8px 10px;border:1.5px solid #e0ddd8;border-radius:7px;font-size:13px;font-family:inherit;}
.form-group input:focus,.form-group select:focus{outline:none;border-color:#6d28d9;}
/* Modal */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1000;align-items:flex-start;justify-content:center;padding-top:40px;overflow-y:auto;}
.modal-overlay.open{display:flex;}
.modal{background:#fff;border-radius:14px;width:90%;max-width:680px;max-height:88vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.25);}
.modal-hd{padding:18px 22px;border-bottom:1px solid #f0ede8;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;background:#fff;z-index:1;}
.modal-hd h3{font-size:15px;font-weight:700;}
.modal-body{padding:22px;}
.close-btn{background:none;border:none;font-size:20px;cursor:pointer;color:#888;padding:4px 8px;border-radius:6px;}
.close-btn:hover{background:#f0ede8;color:#333;}
/* Nomina */
.nomina-summary{background:#f9f8f7;border:1px solid #e7e5e4;border-radius:10px;padding:16px;margin-top:16px;display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;}
.sum-item .sum-lbl{font-size:11px;color:#78716c;text-transform:uppercase;letter-spacing:.4px;}
.sum-item .sum-val{font-size:18px;font-weight:700;color:#1C1917;margin-top:3px;}
.sum-item.purple .sum-val{color:#6d28d9;}
.sum-item.green .sum-val{color:#16a34a;}
.sum-item.red .sum-val{color:#dc2626;}
/* Alertas */
.alerta{padding:10px 14px;border-radius:8px;margin-bottom:8px;font-size:13px;display:flex;align-items:center;gap:8px;}
.alerta.warn{background:#fef9c3;color:#713f12;border:1px solid #fde68a;}
.alerta.danger{background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;}
.alerta.info{background:#ede9fe;color:#4c1d95;border:1px solid #c4b5fd;}
/* Progress bar */
.prog-bar{background:#e7e5e4;border-radius:20px;height:8px;overflow:hidden;margin-top:4px;}
.prog-fill{height:100%;border-radius:20px;background:#6d28d9;transition:width .4s;}
.prog-fill.green{background:#16a34a;}.prog-fill.amber{background:#d97706;}.prog-fill.red{background:#dc2626;}
/* Rating inputs */
.rating-group{display:flex;align-items:center;gap:10px;}
.rating-group label{min-width:130px;font-size:13px;}
.rating-group input[type=range]{flex:1;accent-color:#6d28d9;}
.rating-group .rval{min-width:28px;text-align:right;font-weight:700;color:#6d28d9;}
/* SGSST */
.sgsst-cat{margin-bottom:20px;}
.sgsst-cat-hd{font-size:13px;font-weight:700;color:#1C1917;padding:10px 14px;background:#f5f4f0;border-radius:8px 8px 0 0;border:1px solid #e7e5e4;display:flex;align-items:center;justify-content:space-between;}
.sgsst-item{display:flex;align-items:center;gap:12px;padding:10px 14px;border:1px solid #e7e5e4;border-top:none;background:#fff;}
.sgsst-item:last-child{border-radius:0 0 8px 8px;}
.sgsst-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0;}
.dot-cumplido{background:#16a34a;}.dot-pendiente{background:#d97706;}.dot-vencido{background:#dc2626;}
.empty-state{text-align:center;padding:40px;color:#a8a29e;font-size:13px;}
/* Eval score */
.eval-card{background:#fff;border:1px solid #e8e5e0;border-radius:12px;padding:18px;margin-bottom:12px;}
.score-bar-row{display:flex;align-items:center;gap:10px;margin-top:6px;}
.score-bar-row .lbl{min-width:110px;font-size:12px;color:#57534e;}
.score-bar-row .bar{flex:1;background:#e7e5e4;border-radius:20px;height:7px;overflow:hidden;}
.score-bar-row .fill{height:100%;border-radius:20px;background:#6d28d9;}
.score-bar-row .num{min-width:28px;text-align:right;font-size:12px;font-weight:700;}
.total-score{font-size:32px;font-weight:800;color:#6d28d9;}
/* Period selector */
.ctrl-bar{display:flex;gap:10px;align-items:center;margin-bottom:18px;flex-wrap:wrap;}
.ctrl-bar select,.ctrl-bar input{padding:8px 12px;border:1.5px solid #e0ddd8;border-radius:7px;font-size:13px;}
.ctrl-bar select:focus{outline:none;border-color:#6d28d9;}
/* Distribution */
.dist-row{display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid #f5f4f2;}
.dist-row:last-child{border:none;}
.dist-lbl{min-width:130px;font-size:13px;font-weight:500;}
.dist-bar{flex:1;background:#e7e5e4;border-radius:10px;height:10px;overflow:hidden;}
.dist-fill{height:100%;border-radius:10px;background:#6d28d9;}
.dist-cnt{min-width:24px;text-align:right;font-size:13px;font-weight:700;color:#6d28d9;}
</style>
</head>
<body>
<header>
  <div class="header-top">
    <a href="/">&#8592; Inicio</a>
    <h1>&#128101; Recursos Humanos &mdash; HHA Group</h1>
    <span class="user-chip">{usuario}</span>
  </div>
  <nav>
    <button class="tab active" id="t-dash" onclick="goTo('dash',this)">&#128202; Dashboard</button>
    <button class="tab" id="t-emp" onclick="goTo('emp',this)">&#128100; Empleados</button>
    <button class="tab" id="t-nom" onclick="goTo('nom',this)">&#128184; N&oacute;mina</button>
    <button class="tab" id="t-aus" onclick="goTo('aus',this)">&#128197; Ausencias</button>
    <button class="tab" id="t-cap" onclick="goTo('cap',this)">&#127891; Capacitaciones</button>
    <button class="tab" id="t-eva" onclick="goTo('eva',this)">&#11088; Evaluaciones</button>
    <button class="tab" id="t-sgsst" onclick="goTo('sgsst',this)">&#128737; SGSST</button>
  </nav>
</header>
<main>

<!-- ═══ DASHBOARD ═══ -->
<div id="dash" class="page active">
  <div class="kpi-grid" id="kpi-row">
    <div class="kpi"><div class="kpi-val" id="k-hc">—</div><div class="kpi-lbl">Empleados activos</div></div>
    <div class="kpi green"><div class="kpi-val" id="k-nom">—</div><div class="kpi-lbl">N&oacute;mina bruta / mes</div><div class="kpi-sub">Solo salarios base</div></div>
    <div class="kpi amber"><div class="kpi-val" id="k-aus">—</div><div class="kpi-lbl">Ausentismo este mes</div><div class="kpi-sub">% sobre d&iacute;as h&aacute;biles</div></div>
    <div class="kpi red"><div class="kpi-val" id="k-cap">—</div><div class="kpi-lbl">Capacitaciones pendientes</div></div>
  </div>
  <div class="two-col">
    <div class="card">
      <div class="card-hd"><h2>&#128680; Alertas</h2></div>
      <div id="alertas-list"><div class="empty-state">Cargando...</div></div>
    </div>
    <div class="card">
      <div class="card-hd"><h2>&#127970; Distribuci&oacute;n por empresa</h2></div>
      <div id="dist-empresa"></div>
      <div class="card-hd" style="margin-top:16px;"><h2>&#128204; Por &aacute;rea</h2></div>
      <div id="dist-area"></div>
    </div>
  </div>
</div>

<!-- ═══ EMPLEADOS ═══ -->
<div id="emp" class="page">
  <div class="card-hd" style="margin-bottom:16px;">
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
      <input type="text" id="emp-search" placeholder="Buscar empleado..." style="padding:8px 12px;border:1.5px solid #e0ddd8;border-radius:7px;font-size:13px;min-width:220px;" oninput="filterEmps()">
      <select id="emp-filter-empresa" style="padding:8px 12px;border:1.5px solid #e0ddd8;border-radius:7px;font-size:13px;" onchange="filterEmps()">
        <option value="">Todas las empresas</option>
        <option>Espagiria</option><option>ANIMUS</option><option>HHA Group</option>
      </select>
      <select id="emp-filter-estado" style="padding:8px 12px;border:1.5px solid #e0ddd8;border-radius:7px;font-size:13px;" onchange="filterEmps()">
        <option value="">Todos</option><option>Activo</option><option>Inactivo</option>
      </select>
    </div>
    <button class="btn btn-primary" onclick="openEmpModal(null)">+ Nuevo</button>
  </div>
  <div id="emp-grid" class="emp-grid"></div>
</div>

<!-- ═══ NÓMINA ═══ -->
<div id="nom" class="page">
  <div class="ctrl-bar">
    <select id="nom-mes">
      <option value="01">Enero</option><option value="02">Febrero</option>
      <option value="03">Marzo</option><option value="04">Abril</option>
      <option value="05">Mayo</option><option value="06">Junio</option>
      <option value="07">Julio</option><option value="08">Agosto</option>
      <option value="09">Septiembre</option><option value="10">Octubre</option>
      <option value="11">Noviembre</option><option value="12">Diciembre</option>
    </select>
    <select id="nom-anio"><option>2026</option><option>2025</option></select>
    <button class="btn btn-primary" onclick="loadNomina()">Calcular</button>
    <button class="btn btn-success" onclick="guardarNomina()" style="margin-left:auto;">&#128190; Guardar N&oacute;mina</button>
  </div>
  <div class="card" style="overflow-x:auto;">
    <table id="nom-table">
      <thead><tr>
        <th>Empleado</th><th>Empresa</th><th>D&iacute;as</th>
        <th>Salario Base</th><th>Aux.Trans</th><th>H.Extras</th><th>Bonos</th>
        <th>-Salud(4%)</th><th>-Pens.(4%)</th><th>NETO</th>
      </tr></thead>
      <tbody id="nom-body"></tbody>
    </table>
  </div>
  <div class="nomina-summary" id="nom-summary" style="display:none;"></div>
  <div class="card" style="margin-top:16px;" id="nom-aportes" style="display:none;">
    <div class="card-hd"><h2>&#127968; Aportes Empleador (no deducidos del empleado)</h2></div>
    <div id="nom-aportes-body"></div>
  </div>
</div>

<!-- ═══ AUSENCIAS ═══ -->
<div id="aus" class="page">
  <div class="ctrl-bar">
    <select id="aus-tipo" onchange="loadAusencias()">
      <option value="">Todos los tipos</option>
      <option>Vacaciones</option><option>Incapacidad</option>
      <option>Permiso</option><option>Licencia</option>
    </select>
    <select id="aus-estado" onchange="loadAusencias()">
      <option value="">Todos los estados</option>
      <option>Pendiente</option><option>Aprobada</option><option>Rechazada</option>
    </select>
    <button class="btn btn-primary" style="margin-left:auto;" onclick="openAusModal()">+ Registrar</button>
  </div>
  <div class="card" style="overflow-x:auto;">
    <table><thead><tr>
      <th>Empleado</th><th>Tipo</th><th>Desde</th><th>Hasta</th>
      <th>D&iacute;as</th><th>Estado</th><th>Observaciones</th><th>Acciones</th>
    </tr></thead>
    <tbody id="aus-body"></tbody>
    </table>
  </div>
</div>

<!-- ═══ CAPACITACIONES ═══ -->
<div id="cap" class="page">
  <div class="ctrl-bar">
    <button class="btn btn-primary" style="margin-left:auto;" onclick="openCapModal()">+ Nueva Capacitaci&oacute;n</button>
  </div>
  <div id="cap-list"></div>
</div>

<!-- ═══ EVALUACIONES ═══ -->
<div id="eva" class="page">
  <div class="ctrl-bar">
    <label style="font-size:13px;font-weight:600;">Per&iacute;odo:</label>
    <select id="eva-periodo" onchange="loadEvaluaciones()">
      <option value="">Todos</option>
      <option value="2026-Q1">2026 — Q1</option><option value="2026-Q2">2026 — Q2</option>
      <option value="2026-Q3">2026 — Q3</option><option value="2026-Q4">2026 — Q4</option>
      <option value="2025-Q4">2025 — Q4</option>
    </select>
    <button class="btn btn-primary" style="margin-left:auto;" onclick="openEvaModal()">+ Nueva Evaluaci&oacute;n</button>
  </div>
  <div id="eva-grid"></div>
</div>

<!-- ═══ SGSST ═══ -->
<div id="sgsst" class="page">
  <div class="ctrl-bar">
    <div style="font-size:13px;color:#78716c;">Sistema de Gesti&oacute;n de Seguridad y Salud en el Trabajo &mdash; BPM Cosm&eacute;ticos</div>
    <button class="btn btn-primary" style="margin-left:auto;" onclick="openSgsstModal()">+ Agregar Requisito</button>
  </div>
  <div id="sgsst-body"></div>
</div>

</main>

<!-- MODAL EMPLEADO -->
<div class="modal-overlay" id="m-emp">
  <div class="modal">
    <div class="modal-hd">
      <h3 id="m-emp-title">Nuevo Empleado</h3>
      <button class="close-btn" onclick="closeModal('m-emp')">&#10005;</button>
    </div>
    <div class="modal-body">
      <div class="form-grid">
        <div class="form-group"><label>Nombre *</label><input id="f-nombre" type="text"></div>
        <div class="form-group"><label>Apellido *</label><input id="f-apellido" type="text"></div>
        <div class="form-group"><label>C&eacute;dula</label><input id="f-cedula" type="text"></div>
        <div class="form-group"><label>Cargo *</label><input id="f-cargo" type="text"></div>
        <div class="form-group"><label>&Aacute;rea</label>
          <select id="f-area">
            <option>Gerencia</option><option>Operaciones</option><option>Control de Calidad</option>
            <option>Laboratorio</option><option>Planta</option><option>Administrativa</option>
            <option>Comercial</option><option>Log&iacute;stica</option>
          </select>
        </div>
        <div class="form-group"><label>Empresa</label>
          <select id="f-empresa"><option>Espagiria</option><option>ANIMUS</option><option>HHA Group</option></select>
        </div>
        <div class="form-group"><label>Tipo de contrato</label>
          <select id="f-contrato">
            <option>Indefinido</option><option>Fijo</option>
            <option>Prestaci&oacute;n de Servicios</option><option>Aprendizaje</option>
          </select>
        </div>
        <div class="form-group"><label>Fecha ingreso</label><input id="f-ingreso" type="date"></div>
        <div class="form-group"><label>Salario base (COP)</label><input id="f-salario" type="number" min="0" step="50000"></div>
        <div class="form-group"><label>Nivel de riesgo ARL (1-5)</label>
          <select id="f-riesgo"><option value="1">1 — M&iacute;nimo</option><option value="2">2 — Bajo</option><option value="3">3 — Medio</option><option value="4">4 — Alto</option><option value="5">5 — M&aacute;ximo</option></select>
        </div>
        <div class="form-group"><label>EPS</label><input id="f-eps" type="text" placeholder="Ej: Sura"></div>
        <div class="form-group"><label>AFP (Pens&iacute;on)</label><input id="f-afp" type="text" placeholder="Ej: Proteccion"></div>
        <div class="form-group"><label>ARL</label><input id="f-arl" type="text" placeholder="Ej: Sura"></div>
        <div class="form-group"><label>Caja de compensaci&oacute;n</label><input id="f-caja" type="text" placeholder="Ej: Comfenalco"></div>
        <div class="form-group"><label>Email</label><input id="f-email" type="email"></div>
        <div class="form-group"><label>Tel&eacute;fono</label><input id="f-tel" type="tel"></div>
        <div class="form-group"><label>Estado</label>
          <select id="f-estado"><option>Activo</option><option>Inactivo</option></select>
        </div>
      </div>
      <div class="form-group" style="margin-top:12px;"><label>Observaciones</label><textarea id="f-obs" rows="2" style="resize:vertical;"></textarea></div>
      <div style="margin-top:18px;display:flex;gap:10px;justify-content:flex-end;">
        <button class="btn btn-ghost" onclick="closeModal('m-emp')">Cancelar</button>
        <button class="btn btn-primary" onclick="saveEmp()">Guardar</button>
      </div>
    </div>
  </div>
</div>

<!-- MODAL AUSENCIA -->
<div class="modal-overlay" id="m-aus">
  <div class="modal" style="max-width:500px;">
    <div class="modal-hd">
      <h3>Registrar Ausencia</h3>
      <button class="close-btn" onclick="closeModal('m-aus')">&#10005;</button>
    </div>
    <div class="modal-body">
      <div class="form-grid">
        <div class="form-group"><label>Empleado *</label><select id="a-emp"></select></div>
        <div class="form-group"><label>Tipo *</label>
          <select id="a-tipo"><option>Vacaciones</option><option>Incapacidad</option><option>Permiso</option><option>Licencia</option></select>
        </div>
        <div class="form-group"><label>Fecha inicio *</label><input id="a-inicio" type="date"></div>
        <div class="form-group"><label>Fecha fin *</label><input id="a-fin" type="date"></div>
        <div class="form-group"><label>D&iacute;as</label><input id="a-dias" type="number" min="1" value="1"></div>
      </div>
      <div class="form-group" style="margin-top:12px;"><label>Observaciones</label><textarea id="a-obs" rows="2" style="resize:vertical;"></textarea></div>
      <div style="margin-top:18px;display:flex;gap:10px;justify-content:flex-end;">
        <button class="btn btn-ghost" onclick="closeModal('m-aus')">Cancelar</button>
        <button class="btn btn-primary" onclick="saveAus()">Registrar</button>
      </div>
    </div>
  </div>
</div>

<!-- MODAL CAPACITACION -->
<div class="modal-overlay" id="m-cap">
  <div class="modal" style="max-width:500px;">
    <div class="modal-hd">
      <h3>Nueva Capacitaci&oacute;n</h3>
      <button class="close-btn" onclick="closeModal('m-cap')">&#10005;</button>
    </div>
    <div class="modal-body">
      <div class="form-grid">
        <div class="form-group" style="grid-column:span 2;"><label>Nombre *</label><input id="c-nombre" type="text"></div>
        <div class="form-group"><label>Tipo</label>
          <select id="c-tipo"><option>BPM</option><option>SGSST</option><option>T&eacute;cnica</option><option>Blanda</option><option>Regulatoria</option></select>
        </div>
        <div class="form-group"><label>Fecha</label><input id="c-fecha" type="date"></div>
        <div class="form-group"><label>Duraci&oacute;n (horas)</label><input id="c-horas" type="number" value="2" min="0.5" step="0.5"></div>
        <div class="form-group"><label>Instructor / Entidad</label><input id="c-instructor" type="text"></div>
      </div>
      <div style="margin-top:18px;display:flex;gap:10px;justify-content:flex-end;">
        <button class="btn btn-ghost" onclick="closeModal('m-cap')">Cancelar</button>
        <button class="btn btn-primary" onclick="saveCap()">Crear y asignar</button>
      </div>
    </div>
  </div>
</div>

<!-- MODAL EVALUACION -->
<div class="modal-overlay" id="m-eva">
  <div class="modal" style="max-width:560px;">
    <div class="modal-hd">
      <h3>Nueva Evaluaci&oacute;n de Desempe&ntilde;o</h3>
      <button class="close-btn" onclick="closeModal('m-eva')">&#10005;</button>
    </div>
    <div class="modal-body">
      <div class="form-grid" style="margin-bottom:16px;">
        <div class="form-group"><label>Empleado *</label><select id="e-emp"></select></div>
        <div class="form-group"><label>Per&iacute;odo *</label>
          <select id="e-per">
            <option value="2026-Q2">2026 — Q2</option><option value="2026-Q1">2026 — Q1</option>
            <option value="2025-Q4">2025 — Q4</option>
          </select>
        </div>
      </div>
      <p style="font-size:12px;color:#78716c;margin-bottom:14px;">Puntaje 1 (muy por debajo) a 5 (sobresaliente)</p>
      <div id="ev-criteria"></div>
      <div class="form-group" style="margin-top:14px;"><label>Comentarios</label><textarea id="e-comentarios" rows="3" style="resize:vertical;"></textarea></div>
      <div style="margin-top:18px;display:flex;gap:10px;justify-content:flex-end;">
        <button class="btn btn-ghost" onclick="closeModal('m-eva')">Cancelar</button>
        <button class="btn btn-primary" onclick="saveEva()">Publicar</button>
      </div>
    </div>
  </div>
</div>

<!-- MODAL SGSST -->
<div class="modal-overlay" id="m-sgsst">
  <div class="modal" style="max-width:500px;">
    <div class="modal-hd">
      <h3>Agregar Requisito SGSST</h3>
      <button class="close-btn" onclick="closeModal('m-sgsst')">&#10005;</button>
    </div>
    <div class="modal-body">
      <div class="form-grid">
        <div class="form-group"><label>Categor&iacute;a</label>
          <select id="sg-cat">
            <option>Medicina del Trabajo</option><option>Higiene Industrial</option>
            <option>Seguridad</option><option>Emergencias</option>
            <option>Vigilancia Epidemiol&oacute;gica</option><option>Capacitaci&oacute;n SGSST</option>
          </select>
        </div>
        <div class="form-group"><label>Frecuencia</label>
          <select id="sg-freq"><option>Mensual</option><option>Trimestral</option><option>Semestral</option><option>Anual</option></select>
        </div>
        <div class="form-group" style="grid-column:span 2;"><label>Descripci&oacute;n *</label><input id="sg-desc" type="text"></div>
        <div class="form-group"><label>Responsable</label><input id="sg-resp" type="text"></div>
        <div class="form-group"><label>Pr&oacute;ximo vencimiento</label><input id="sg-prox" type="date"></div>
      </div>
      <div style="margin-top:18px;display:flex;gap:10px;justify-content:flex-end;">
        <button class="btn btn-ghost" onclick="closeModal('m-sgsst')">Cancelar</button>
        <button class="btn btn-primary" onclick="saveSgsst()">Agregar</button>
      </div>
    </div>
  </div>
</div>

<script>
// ─── state ───────────────────────────────────────────
var allEmps = [];
var currentEmpId = null;
var nominaData = [];

var CRITERIA = [
  {key:'calidad',   label:'Calidad del trabajo'},
  {key:'asistencia',label:'Puntualidad / Asistencia'},
  {key:'actitud',   label:'Actitud y trabajo en equipo'},
  {key:'conocimiento',label:'Conocimiento t\u00e9cnico'},
  {key:'productividad',label:'Productividad'}
];

// ─── navigation ──────────────────────────────────────
function goTo(id, btn) {
  document.querySelectorAll('.page').forEach(function(p){p.classList.remove('active');});
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
  if (id==='dash') loadDashboard();
  else if (id==='emp') loadEmpleados();
  else if (id==='nom') initNomina();
  else if (id==='aus') loadAusencias();
  else if (id==='cap') loadCapacitaciones();
  else if (id==='eva') loadEvaluaciones();
  else if (id==='sgsst') loadSgsst();
}

// ─── utils ───────────────────────────────────────────
function fmt(n){return '$'+Number(n||0).toLocaleString('es-CO');}
function fmtDate(s){return s?(String(s).slice(0,10)):'—';}
function closeModal(id){document.getElementById(id).classList.remove('open');}
function openModal(id){document.getElementById(id).classList.add('open');}

function avatarColor(name) {
  var colors=['#6d28d9','#0e7490','#16a34a','#d97706','#dc2626','#7c3aed','#0369a1','#065f46'];
  var h=0; for(var i=0;i<name.length;i++) h=(h<<5)-h+name.charCodeAt(i);
  return colors[Math.abs(h)%colors.length];
}

function badgeEmpresa(e) {
  var m={'Espagiria':'badge-esp','ANIMUS':'badge-ani','HHA Group':'badge-hha'};
  return '<span class="badge '+(m[e]||'badge-indef')+'">'+e+'</span>';
}

function badgeContrato(t) {
  var m={'Indefinido':'badge-indef','Fijo':'badge-fijo','Prestaci\u00f3n de Servicios':'badge-ps','Aprendizaje':'badge-ps'};
  return '<span class="badge '+(m[t]||'badge-indef')+'">'+t+'</span>';
}

// ─── DASHBOARD ───────────────────────────────────────
async function loadDashboard() {
  try {
    var d = await fetch('/api/rrhh/dashboard').then(function(r){return r.json();});
    document.getElementById('k-hc').textContent = d.headcount||0;
    document.getElementById('k-nom').textContent = fmt(d.nomina_bruta);
    document.getElementById('k-aus').textContent = (d.ausentismo_pct||0)+'%';
    document.getElementById('k-cap').textContent = d.caps_pendientes||0;

    var al = document.getElementById('alertas-list');
    if (!d.alertas || d.alertas.length===0) {
      al.innerHTML = '<div class="alerta info">&#10003; Sin alertas cr\u00edticas por el momento.</div>';
    } else {
      al.innerHTML = d.alertas.map(function(a){
        return '<div class="alerta '+(a.tipo||'info')+'">&#9679; '+a.msg+'</div>';
      }).join('');
    }

    var maxE = Math.max.apply(null,(d.por_empresa||[]).map(function(x){return x.count;}),1);
    document.getElementById('dist-empresa').innerHTML = (d.por_empresa||[]).map(function(x){
      var pct=Math.round(x.count/maxE*100);
      return '<div class="dist-row"><span class="dist-lbl">'+x.empresa+'</span><div class="dist-bar"><div class="dist-fill" style="width:'+pct+'%"></div></div><span class="dist-cnt">'+x.count+'</span></div>';
    }).join('');

    var maxA = Math.max.apply(null,(d.por_area||[]).map(function(x){return x.count;}),1);
    document.getElementById('dist-area').innerHTML = (d.por_area||[]).map(function(x){
      var pct=Math.round(x.count/maxA*100);
      return '<div class="dist-row"><span class="dist-lbl">'+x.area+'</span><div class="dist-bar"><div class="dist-fill" style="width:'+pct+'%"></div></div><span class="dist-cnt">'+x.count+'</span></div>';
    }).join('');
  } catch(e){console.error(e);}
}

// ─── EMPLEADOS ────────────────────────────────────────
async function loadEmpleados() {
  try {
    allEmps = await fetch('/api/rrhh/empleados').then(function(r){return r.json();});
    renderEmpleados(allEmps);
  } catch(e){console.error(e);}
}

function renderEmpleados(list) {
  var g = document.getElementById('emp-grid');
  if (!list.length){g.innerHTML='<div class="empty-state">Sin empleados registrados.</div>';return;}
  g.innerHTML = list.map(function(e){
    var initials = (e.nombre||'?').charAt(0)+(e.apellido||'').charAt(0);
    var color = avatarColor(e.nombre+e.apellido);
    return '<div class="emp-card" onclick="openEmpModal('+e.id+')">' +
      '<div class="emp-avatar" style="background:'+color+';">'+initials+'</div>' +
      '<div class="emp-name">'+e.nombre+' '+e.apellido+'</div>' +
      '<div class="emp-cargo">'+e.cargo+'</div>' +
      '<div class="emp-meta">'+badgeEmpresa(e.empresa)+' '+badgeContrato(e.tipo_contrato)+
      ' <span class="badge '+(e.estado==='Activo'?'badge-activo':'badge-inactivo')+'">'+e.estado+'</span></div>' +
      '<div style="margin-top:10px;font-size:13px;font-weight:700;color:#6d28d9;">'+fmt(e.salario_base)+'</div>' +
      '</div>';
  }).join('');
}

function filterEmps() {
  var q = (document.getElementById('emp-search').value||'').toLowerCase();
  var emp = document.getElementById('emp-filter-empresa').value;
  var est = document.getElementById('emp-filter-estado').value;
  var filtered = allEmps.filter(function(e){
    var name = (e.nombre+' '+e.apellido+' '+e.cargo).toLowerCase();
    return (name.includes(q)) && (!emp || e.empresa===emp) && (!est || e.estado===est);
  });
  renderEmpleados(filtered);
}

async function openEmpModal(id) {
  currentEmpId = id;
  document.getElementById('m-emp-title').textContent = id ? 'Editar Empleado' : 'Nuevo Empleado';
  var fields = ['nombre','apellido','cedula','cargo','area','empresa','contrato','ingreso','salario','riesgo','eps','afp','arl','caja','email','tel','estado','obs'];
  if (id) {
    try {
      var d = await fetch('/api/rrhh/empleados/'+id).then(function(r){return r.json();});
      document.getElementById('f-nombre').value = d.nombre||'';
      document.getElementById('f-apellido').value = d.apellido||'';
      document.getElementById('f-cedula').value = d.cedula||'';
      document.getElementById('f-cargo').value = d.cargo||'';
      document.getElementById('f-area').value = d.area||'Operaciones';
      document.getElementById('f-empresa').value = d.empresa||'Espagiria';
      document.getElementById('f-contrato').value = d.tipo_contrato||'Indefinido';
      document.getElementById('f-ingreso').value = (d.fecha_ingreso||'').slice(0,10);
      document.getElementById('f-salario').value = d.salario_base||0;
      document.getElementById('f-riesgo').value = d.nivel_riesgo||1;
      document.getElementById('f-eps').value = d.eps||'';
      document.getElementById('f-afp').value = d.afp||'';
      document.getElementById('f-arl').value = d.arl||'';
      document.getElementById('f-caja').value = d.caja_compensacion||'';
      document.getElementById('f-email').value = d.email||'';
      document.getElementById('f-tel').value = d.telefono||'';
      document.getElementById('f-estado').value = d.estado||'Activo';
      document.getElementById('f-obs').value = d.observaciones||'';
    } catch(e){console.error(e);}
  } else {
    fields.forEach(function(f){var el=document.getElementById('f-'+f);if(el)el.value='';});
    document.getElementById('f-empresa').value='Espagiria';
    document.getElementById('f-contrato').value='Indefinido';
    document.getElementById('f-area').value='Operaciones';
    document.getElementById('f-estado').value='Activo';
    document.getElementById('f-riesgo').value='1';
  }
  openModal('m-emp');
}

async function saveEmp() {
  var payload = {
    nombre: document.getElementById('f-nombre').value.trim(),
    apellido: document.getElementById('f-apellido').value.trim(),
    cedula: document.getElementById('f-cedula').value.trim(),
    cargo: document.getElementById('f-cargo').value.trim(),
    area: document.getElementById('f-area').value,
    empresa: document.getElementById('f-empresa').value,
    tipo_contrato: document.getElementById('f-contrato').value,
    fecha_ingreso: document.getElementById('f-ingreso').value,
    salario_base: parseFloat(document.getElementById('f-salario').value)||0,
    nivel_riesgo: parseInt(document.getElementById('f-riesgo').value)||1,
    eps: document.getElementById('f-eps').value.trim(),
    afp: document.getElementById('f-afp').value.trim(),
    arl: document.getElementById('f-arl').value.trim(),
    caja: document.getElementById('f-caja').value.trim(),
    email: document.getElementById('f-email').value.trim(),
    telefono: document.getElementById('f-tel').value.trim(),
    estado: document.getElementById('f-estado').value,
    observaciones: document.getElementById('f-obs').value.trim()
  };
  if (!payload.nombre || !payload.cargo) {alert('Nombre y cargo son obligatorios.');return;}
  var url = currentEmpId ? '/api/rrhh/empleados/'+currentEmpId : '/api/rrhh/empleados';
  var method = currentEmpId ? 'PUT' : 'POST';
  try {
    var r = await fetch(url,{method:method,headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    var d = await r.json();
    if (d.ok || d.id) {closeModal('m-emp'); loadEmpleados();}
    else alert(d.error||'Error al guardar');
  } catch(e){alert('Error: '+e.message);}
}

// ─── NÓMINA ──────────────────────────────────────────
function initNomina(){
  var now = new Date();
  document.getElementById('nom-mes').value = String(now.getMonth()+1).padStart(2,'0');
  document.getElementById('nom-anio').value = String(now.getFullYear());
  loadNomina();
}

async function loadNomina(){
  var mes = document.getElementById('nom-mes').value;
  var anio = document.getElementById('nom-anio').value;
  var periodo = anio+'-'+mes;
  try {
    nominaData = await fetch('/api/rrhh/nomina/'+periodo).then(function(r){return r.json();});
    renderNomina();
  } catch(e){console.error(e);}
}

function calcNeto(row){
  var base = parseFloat(row.salario_base)||0;
  var aux = parseFloat(row.aux_transporte)||0;
  var he = parseFloat(row.valor_horas_extras)||0;
  var bonos = parseFloat(row.bonificaciones)||0;
  var salud = Math.round(base*0.04);
  var pension = Math.round(base*0.04);
  var otros = parseFloat(row.otros_descuentos)||0;
  return base+aux+he+bonos-salud-pension-otros;
}

function renderNomina(){
  var tbody = document.getElementById('nom-body');
  var totalBruto=0,totalNeto=0,totalDed=0;
  var aportesTot={salud:0,pension:0,arl:0,sena:0,icbf:0,caja:0,total:0};
  tbody.innerHTML = nominaData.map(function(e,i){
    var neto = calcNeto(e);
    totalBruto += (e.salario_base||0)+(e.aux_transporte||0)+(e.valor_horas_extras||0)+(e.bonificaciones||0);
    totalDed += (e.desc_salud||0)+(e.desc_pension||0)+(e.otros_descuentos||0);
    totalNeto += neto;
    var ae = e.aportes_empleador||{};
    Object.keys(aportesTot).forEach(function(k){aportesTot[k]+=(ae[k]||0);});
    return '<tr>' +
      '<td><strong>'+e.nombre+'</strong><br><small style="color:#78716c;">'+e.cargo+'</small></td>' +
      '<td>'+badgeEmpresa(e.empresa)+'</td>' +
      '<td><input type="number" value="'+e.dias_trabajados+'" min="0" max="31" style="width:60px;" onchange="nominaData['+i+'].dias_trabajados=this.value;renderNomina();"></td>' +
      '<td>'+fmt(e.salario_base)+'</td>' +
      '<td style="color:#16a34a;">'+fmt(e.aux_transporte)+'</td>' +
      '<td><input type="number" value="'+(e.valor_horas_extras||0)+'" min="0" step="10000" onchange="nominaData['+i+'].valor_horas_extras=parseFloat(this.value)||0;renderNomina();"></td>' +
      '<td><input type="number" value="'+(e.bonificaciones||0)+'" min="0" step="10000" onchange="nominaData['+i+'].bonificaciones=parseFloat(this.value)||0;renderNomina();"></td>' +
      '<td style="color:#dc2626;">-'+fmt(e.desc_salud)+'</td>' +
      '<td style="color:#dc2626;">-'+fmt(e.desc_pension)+'</td>' +
      '<td style="font-weight:700;color:#6d28d9;">'+fmt(neto)+'</td>' +
      '</tr>';
  }).join('');

  var s = document.getElementById('nom-summary');
  s.style.display='grid';
  s.innerHTML =
    '<div class="sum-item"><div class="sum-lbl">Total Devengado</div><div class="sum-val">'+fmt(totalBruto)+'</div></div>' +
    '<div class="sum-item red"><div class="sum-lbl">Total Deducciones</div><div class="sum-val">-'+fmt(totalDed)+'</div></div>' +
    '<div class="sum-item green"><div class="sum-lbl">Total Neto a Pagar</div><div class="sum-val">'+fmt(totalNeto)+'</div></div>' +
    '<div class="sum-item purple"><div class="sum-lbl">Aportes Empleador</div><div class="sum-val">'+fmt(aportesTot.total)+'</div></div>' +
    '<div class="sum-item purple"><div class="sum-lbl">Costo Total Empresa</div><div class="sum-val">'+fmt(totalBruto+aportesTot.total)+'</div></div>';

  var ap = document.getElementById('nom-aportes');
  ap.style.display='block';
  ap.querySelector('#nom-aportes-body').innerHTML =
    '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;">' +
    [['Salud (8.5%)',aportesTot.salud],['Pensi\u00f3n (12%)',aportesTot.pension],
     ['ARL',aportesTot.arl],['SENA (2%)',aportesTot.sena],
     ['ICBF (3%)',aportesTot.icbf],['Caja (4%)',aportesTot.caja],['TOTAL',aportesTot.total]].map(function(x){
      return '<div style="text-align:center;background:#f9f8f7;border-radius:8px;padding:10px;">' +
        '<div style="font-size:11px;color:#78716c;">'+x[0]+'</div>' +
        '<div style="font-size:16px;font-weight:700;color:'+(x[0]==='TOTAL'?'#6d28d9':'#1C1917')+';">'+fmt(x[1])+'</div></div>';
    }).join('') + '</div>';
}

async function guardarNomina(){
  var mes = document.getElementById('nom-mes').value;
  var anio = document.getElementById('nom-anio').value;
  var periodo = anio+'-'+mes;
  nominaData.forEach(function(e){e.neto=calcNeto(e);});
  try {
    var r = await fetch('/api/rrhh/nomina/guardar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({periodo:periodo,registros:nominaData})});
    var d = await r.json();
    if(d.ok) alert('N\u00f3mina guardada: '+d.registros+' registros para '+periodo);
    else alert(d.error||'Error');
  } catch(e){alert('Error: '+e.message);}
}

// ─── AUSENCIAS ───────────────────────────────────────
async function loadAusencias(){
  var tipo = document.getElementById('aus-tipo').value;
  var estado = document.getElementById('aus-estado').value;
  try {
    var all = await fetch('/api/rrhh/ausencias').then(function(r){return r.json();});
    var filtered = all.filter(function(a){
      return (!tipo||a.tipo===tipo)&&(!estado||a.estado===estado);
    });
    var tbody = document.getElementById('aus-body');
    if(!filtered.length){tbody.innerHTML='<tr><td colspan="8" class="empty-state">Sin registros.</td></tr>';return;}
    var estadoColors = {'Aprobada':'badge-activo','Pendiente':'badge-fijo','Rechazada':'badge-inactivo'};
    tbody.innerHTML = filtered.map(function(a){
      return '<tr>' +
        '<td><strong>'+a.empleado+'</strong></td>' +
        '<td>'+a.tipo+'</td><td>'+fmtDate(a.fecha_inicio)+'</td><td>'+fmtDate(a.fecha_fin)+'</td>' +
        '<td style="text-align:center;font-weight:700;">'+a.dias+'</td>' +
        '<td><span class="badge '+(estadoColors[a.estado]||'badge-indef')+'">'+a.estado+'</span></td>' +
        '<td style="color:#78716c;max-width:150px;">'+(a.observaciones||'—')+'</td>' +
        '<td>' +
          (a.estado==='Pendiente'?
            '<button class="btn btn-success btn-sm" onclick="aprobarAus('+a.id+',\'Aprobada\')">Aprobar</button> '+
            '<button class="btn btn-danger btn-sm" style="margin-left:4px;" onclick="aprobarAus('+a.id+',\'Rechazada\')">Rechazar</button>':
            '<span style="color:#a8a29e;font-size:12px;">'+a.aprobado_por+'</span>') +
        '</td></tr>';
    }).join('');
  } catch(e){console.error(e);}
}

async function aprobarAus(id, estado){
  await fetch('/api/rrhh/ausencias/'+id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:estado})});
  loadAusencias();
}

function openAusModal(){
  var sel = document.getElementById('a-emp');
  sel.innerHTML = allEmps.filter(function(e){return e.estado==='Activo';}).map(function(e){
    return '<option value="'+e.id+'">'+e.nombre+' '+e.apellido+'</option>';
  }).join('');
  openModal('m-aus');
}

async function saveAus(){
  var payload={
    empleado_id: document.getElementById('a-emp').value,
    tipo: document.getElementById('a-tipo').value,
    fecha_inicio: document.getElementById('a-inicio').value,
    fecha_fin: document.getElementById('a-fin').value,
    dias: parseInt(document.getElementById('a-dias').value)||1,
    observaciones: document.getElementById('a-obs').value.trim()
  };
  if(!payload.fecha_inicio){alert('Fecha de inicio obligatoria.');return;}
  try {
    await fetch('/api/rrhh/ausencias',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    closeModal('m-aus');
    loadAusencias();
  } catch(e){alert('Error: '+e.message);}
}

// ─── CAPACITACIONES ──────────────────────────────────
async function loadCapacitaciones(){
  try {
    var caps = await fetch('/api/rrhh/capacitaciones').then(function(r){return r.json();});
    var div = document.getElementById('cap-list');
    if(!caps.length){div.innerHTML='<div class="empty-state">Sin capacitaciones registradas.</div>';return;}
    var tipoColors={'BPM':'#6d28d9','SGSST':'#dc2626','T\u00e9cnica':'#0e7490','Blanda':'#16a34a','Regulatoria':'#d97706'};
    div.innerHTML = caps.map(function(c){
      var pct = c.total>0 ? Math.round((c.completados||0)/c.total*100) : 0;
      var color = pct>=100?'green':pct>=50?'':'red';
      return '<div class="card" style="margin-bottom:12px;">' +
        '<div class="card-hd">' +
          '<div>' +
            '<span style="font-size:11px;font-weight:700;text-transform:uppercase;color:'+(tipoColors[c.tipo]||'#888')+';letter-spacing:.5px;">'+c.tipo+'</span>' +
            '<div style="font-size:15px;font-weight:700;margin-top:2px;">'+c.nombre+'</div>' +
            '<div style="font-size:12px;color:#78716c;margin-top:2px;">'+fmtDate(c.fecha)+' &bull; '+c.horas+'h &bull; '+c.instructor+'</div>' +
          '</div>' +
          '<div style="text-align:right;">' +
            '<div style="font-size:24px;font-weight:800;color:'+(color==='green'?'#16a34a':color==='red'?'#dc2626':'#d97706')+'">'+pct+'%</div>' +
            '<div style="font-size:11px;color:#78716c;">'+(c.completados||0)+'/'+c.total+' completados</div>' +
          '</div>' +
        '</div>' +
        '<div class="prog-bar"><div class="prog-fill '+color+'" style="width:'+pct+'%"></div></div>' +
        '</div>';
    }).join('');
  } catch(e){console.error(e);}
}

function openCapModal(){openModal('m-cap');}

async function saveCap(){
  var payload={
    nombre: document.getElementById('c-nombre').value.trim(),
    tipo: document.getElementById('c-tipo').value,
    fecha: document.getElementById('c-fecha').value,
    duracion_horas: parseFloat(document.getElementById('c-horas').value)||1,
    instructor: document.getElementById('c-instructor').value.trim(),
    obligatoria: true
  };
  if(!payload.nombre){alert('Nombre obligatorio.');return;}
  try {
    await fetch('/api/rrhh/capacitaciones',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    closeModal('m-cap');
    loadCapacitaciones();
  } catch(e){alert('Error: '+e.message);}
}

// ─── EVALUACIONES ────────────────────────────────────
async function loadEvaluaciones(){
  var periodo = document.getElementById('eva-periodo').value;
  var url = '/api/rrhh/evaluaciones'+(periodo?'?periodo='+periodo:'');
  try {
    var evals = await fetch(url).then(function(r){return r.json();});
    var div = document.getElementById('eva-grid');
    if(!evals.length){div.innerHTML='<div class="empty-state">Sin evaluaciones para este per\u00edodo.</div>';return;}
    div.innerHTML = evals.map(function(ev){
      var scores=[['Calidad',ev.calidad],['Asistencia',ev.asistencia],['Actitud',ev.actitud],['Conocimiento',ev.conocimiento],['Productividad',ev.productividad]];
      var color = ev.total>=4?'#16a34a':ev.total>=3?'#d97706':'#dc2626';
      return '<div class="eval-card">' +
        '<div style="display:flex;align-items:center;gap:16px;margin-bottom:14px;">' +
          '<div class="emp-avatar" style="background:'+avatarColor(ev.empleado)+';width:44px;height:44px;font-size:15px;flex-shrink:0;">'+ev.empleado.slice(0,2).toUpperCase()+'</div>' +
          '<div style="flex:1;">' +
            '<div style="font-size:14px;font-weight:700;">'+ev.empleado+'</div>' +
            '<div style="font-size:12px;color:#78716c;">'+ev.cargo+' &bull; '+ev.periodo+' &bull; Eval: '+ev.evaluador+'</div>' +
          '</div>' +
          '<div style="text-align:right;"><div class="total-score" style="color:'+color+';">'+ev.total+'</div><div style="font-size:11px;color:#78716c;">/ 5.0</div></div>' +
        '</div>' +
        scores.map(function(s){
          var pct=(s[1]/5)*100;
          return '<div class="score-bar-row"><span class="lbl">'+s[0]+'</span><div class="bar"><div class="fill" style="width:'+pct+'%;"></div></div><span class="num">'+s[1]+'</span></div>';
        }).join('') +
        (ev.comentarios?'<div style="margin-top:10px;font-size:12px;color:#57534e;background:#f9f8f7;padding:8px 10px;border-radius:6px;">'+ev.comentarios+'</div>':'') +
        '</div>';
    }).join('');
  } catch(e){console.error(e);}
}

function openEvaModal(){
  var sel = document.getElementById('e-emp');
  sel.innerHTML = allEmps.filter(function(e){return e.estado==='Activo';}).map(function(e){
    return '<option value="'+e.id+'">'+e.nombre+' '+e.apellido+'</option>';
  }).join('');
  document.getElementById('ev-criteria').innerHTML = CRITERIA.map(function(c){
    return '<div class="rating-group" style="margin-bottom:10px;">' +
      '<label>'+c.label+'</label>' +
      '<input type="range" id="ev-'+c.key+'" min="1" max="5" step="0.5" value="3" oninput="document.getElementById(\'rv-'+c.key+'\').textContent=this.value;">' +
      '<span class="rval" id="rv-'+c.key+'">3</span>' +
      '</div>';
  }).join('');
  openModal('m-eva');
}

async function saveEva(){
  var payload={
    empleado_id: document.getElementById('e-emp').value,
    periodo: document.getElementById('e-per').value,
    comentarios: document.getElementById('e-comentarios').value.trim()
  };
  CRITERIA.forEach(function(c){payload[c.key]=parseFloat(document.getElementById('ev-'+c.key).value)||3;});
  try {
    await fetch('/api/rrhh/evaluaciones',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    closeModal('m-eva');
    loadEvaluaciones();
  } catch(e){alert('Error: '+e.message);}
}

// ─── SGSST ───────────────────────────────────────────
async function loadSgsst(){
  try {
    var items = await fetch('/api/rrhh/sgsst').then(function(r){return r.json();});
    var div = document.getElementById('sgsst-body');
    if(!items.length){div.innerHTML='<div class="empty-state">Sin requisitos SGSST registrados.</div>';return;}
    var bycat={};
    items.forEach(function(it){
      if(!bycat[it.categoria])bycat[it.categoria]=[];
      bycat[it.categoria].push(it);
    });
    div.innerHTML = Object.keys(bycat).map(function(cat){
      var its = bycat[cat];
      var cumplidos = its.filter(function(x){return x.estado==='Cumplido';}).length;
      var pct = Math.round(cumplidos/its.length*100);
      var col = pct===100?'green':pct>=60?'amber':'red';
      return '<div class="sgsst-cat">' +
        '<div class="sgsst-cat-hd">' +
          '<span>'+cat+'</span>' +
          '<div style="display:flex;align-items:center;gap:10px;">' +
            '<div style="width:120px;"><div class="prog-bar"><div class="prog-fill '+col+'" style="width:'+pct+'%"></div></div></div>' +
            '<span style="font-size:12px;font-weight:700;color:'+(col==='green'?'#16a34a':col==='amber'?'#d97706':'#dc2626')+';">'+pct+'%</span>' +
          '</div>' +
        '</div>' +
        its.map(function(it){
          var dotCls = it.estado==='Cumplido'?'dot-cumplido':it.estado==='Vencido'?'dot-vencido':'dot-pendiente';
          return '<div class="sgsst-item">' +
            '<div class="sgsst-dot '+dotCls+'"></div>' +
            '<div style="flex:1;">' +
              '<div style="font-size:13px;font-weight:500;">'+it.descripcion+'</div>' +
              '<div style="font-size:11px;color:#78716c;margin-top:2px;">'+it.frecuencia+(it.responsable?' &bull; '+it.responsable:'')+(it.proximo?' &bull; Pr\u00f3ximo: '+fmtDate(it.proximo):'')+'</div>' +
            '</div>' +
            (it.estado!=='Cumplido'?'<button class="btn btn-success btn-sm" onclick="cumplirSgsst('+it.id+')">Marcar cumplido</button>':'<span style="font-size:12px;color:#16a34a;font-weight:600;">\u2713 '+fmtDate(it.ultimo)+'</span>') +
          '</div>';
        }).join('') +
      '</div>';
    }).join('');
  } catch(e){console.error(e);}
}

async function cumplirSgsst(id){
  await fetch('/api/rrhh/sgsst/'+id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:'Cumplido'})});
  loadSgsst();
}

function openSgsstModal(){openModal('m-sgsst');}

async function saveSgsst(){
  var payload={
    categoria: document.getElementById('sg-cat').value,
    descripcion: document.getElementById('sg-desc').value.trim(),
    frecuencia: document.getElementById('sg-freq').value,
    responsable: document.getElementById('sg-resp').value.trim(),
    proximo_vencimiento: document.getElementById('sg-prox').value
  };
  if(!payload.descripcion){alert('Descripci\u00f3n obligatoria.');return;}
  try {
    await fetch('/api/rrhh/sgsst',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    closeModal('m-sgsst');
    loadSgsst();
  } catch(e){alert('Error: '+e.message);}
}

// ─── init ────────────────────────────────────────────
loadDashboard();
loadEmpleados();
</script>
</body>
</html>
"""

# ─── HUB HHA GROUP ────────────────────────────────────────────
COMPROMISOS_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Compromisos — HHA Group</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#f5f4f2;color:#1C1917;font-size:14px;}
.topbar{background:#1e293b;color:#fff;padding:12px 20px;display:flex;align-items:center;gap:16px;}
.topbar h1{font-size:17px;font-weight:600;}
.tb-right{margin-left:auto;display:flex;gap:12px;font-size:13px;}
.tb-right a{color:#94a3b8;text-decoration:none;}
.tb-right a:hover{color:#fff;}
.content{padding:20px;max-width:1200px;margin:0 auto;}
.filter-bar{background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:12px 16px;margin-bottom:16px;display:flex;gap:10px;flex-wrap:wrap;align-items:center;}
.filter-bar select,.filter-bar input{padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;}
.stats-row{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;}
.stat-pill{padding:6px 14px;border-radius:20px;font-size:12px;font-weight:600;}
.sp-crit{background:#fee2e2;color:#991b1b;}
.sp-alta{background:#fef3c7;color:#92400e;}
.sp-pend{background:#dbeafe;color:#1e40af;}
.sp-done{background:#dcfce7;color:#166534;}
.comp-list{display:flex;flex-direction:column;gap:10px;}
.comp-card{background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:14px 16px;display:flex;align-items:flex-start;gap:12px;}
.comp-card:hover{border-color:#a8a29e;}
.comp-card.crit{border-left:4px solid #dc2626;}
.comp-card.alta{border-left:4px solid #d97706;}
.comp-card.norm{border-left:4px solid #3b82f6;}
.comp-card.done{border-left:4px solid #16a34a;opacity:.7;}
.comp-check{flex-shrink:0;width:22px;height:22px;border-radius:50%;border:2px solid #d6d3d1;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:13px;margin-top:2px;}
.comp-check.done{background:#16a34a;border-color:#16a34a;color:#fff;}
.comp-body{flex:1;}
.comp-desc{font-size:14px;font-weight:600;color:#1C1917;margin-bottom:4px;}
.comp-card.done .comp-desc{text-decoration:line-through;color:#78716c;}
.comp-meta{display:flex;gap:12px;flex-wrap:wrap;font-size:11px;color:#78716c;margin-bottom:4px;}
.badge-prior{display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;font-weight:700;}
.pr-c{background:#fee2e2;color:#991b1b;}
.pr-a{background:#fef3c7;color:#92400e;}
.pr-n{background:#f3f4f6;color:#6b7280;}
.pr-b{background:#f0fdf4;color:#166534;}
.est-badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;font-weight:600;}
.est-pend{background:#dbeafe;color:#1e40af;}
.est-proc{background:#fef3c7;color:#92400e;}
.est-comp{background:#dcfce7;color:#166534;}
.est-canc{background:#f3f4f6;color:#6b7280;}
.vencido-tag{color:#dc2626;font-weight:700;font-size:10px;}
.comp-actions{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;}
.btn{padding:5px 12px;border-radius:6px;font-size:11px;font-weight:600;border:none;cursor:pointer;}
.btn-prim{background:#1e293b;color:#fff;}
.btn-succ{background:#16a34a;color:#fff;}
.btn-warn{background:#d97706;color:#fff;}
.btn-outl{background:#fff;color:#374151;border:1px solid #d6d3d1;}
.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1000;display:flex;align-items:center;justify-content:center;padding:16px;}
.modal{background:#fff;border-radius:10px;width:100%;max-width:540px;box-shadow:0 20px 60px rgba(0,0,0,.3);}
.mh{padding:16px 20px;border-bottom:1px solid #e7e5e4;display:flex;align-items:center;justify-content:space-between;}
.mh h3{font-size:15px;font-weight:700;}
.mc{padding:20px;display:flex;flex-direction:column;gap:12px;}
.mf{padding:12px 20px;border-top:1px solid #e7e5e4;display:flex;gap:8px;justify-content:flex-end;}
.fg label{display:block;font-size:11px;font-weight:600;color:#44403c;margin-bottom:4px;}
.fg input,.fg select,.fg textarea{width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
.fab{position:fixed;bottom:20px;right:20px;background:#1e293b;color:#fff;border:none;width:50px;height:50px;border-radius:50%;font-size:22px;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.3);display:flex;align-items:center;justify-content:center;}
.hidden{display:none;}
.empty{text-align:center;padding:40px;color:#78716c;}
</style>
</head>
<body>
<div class="topbar">
  <h1>&#x1F4CB; Compromisos — HHA Group</h1>
  <div class="tb-right">
    <a href="/">&#x2190; Hub</a>
    <a href="/gerencia">Gerencia</a>
  </div>
</div>
<div class="content">
  <div class="filter-bar">
    <select id="f-estado" onchange="load()">
      <option value="Todos">Todos los estados</option>
      <option value="Pendiente" selected>Pendiente</option>
      <option value="En Proceso">En Proceso</option>
      <option value="Completado">Completado</option>
    </select>
    <select id="f-empresa" onchange="load()">
      <option value="">Ambas empresas</option>
      <option value="Espagiria">Espagiria</option>
      <option value="ANIMUS">ANIMUS Lab</option>
    </select>
    <input id="f-q" type="text" placeholder="Buscar..." oninput="render()" style="min-width:180px;">
    <button class="btn btn-prim" onclick="abrirModal()">+ Nuevo Compromiso</button>
  </div>
  <div id="stats" class="stats-row"></div>
  <div id="list" class="comp-list"><div class="empty">Cargando...</div></div>
</div>

<button class="fab" onclick="abrirModal()">+</button>

<div id="modal" class="modal-backdrop hidden">
<div class="modal">
  <div class="mh"><h3>Nuevo Compromiso</h3><button onclick="cerrar()" style="background:none;border:none;font-size:18px;cursor:pointer;">&times;</button></div>
  <div class="mc">
    <div class="fg"><label>Descripcion *</label><textarea id="n-desc" rows="2" placeholder="Que se comprometio a hacer..."></textarea></div>
    <div class="grid2">
      <div class="fg"><label>Responsable</label><input id="n-resp" placeholder="Nombre"></div>
      <div class="fg"><label>Area</label><input id="n-area" placeholder="Calidad, Produccion..."></div>
    </div>
    <div class="grid2">
      <div class="fg"><label>Fecha limite</label><input type="date" id="n-fecha"></div>
      <div class="fg"><label>Prioridad</label>
        <select id="n-prior"><option>Normal</option><option>Alta</option><option>Critico</option><option>Baja</option></select>
      </div>
    </div>
    <div class="grid2">
      <div class="fg"><label>Empresa</label>
        <select id="n-emp"><option>Espagiria</option><option>ANIMUS</option><option>HHA Group</option></select>
      </div>
      <div class="fg"><label>Origen (acta/reunion)</label><input id="n-origen" placeholder="ACTA-ESP-..."></div>
    </div>
  </div>
  <div class="mf">
    <button class="btn btn-outl" onclick="cerrar()">Cancelar</button>
    <button class="btn btn-prim" onclick="guardar()">Guardar</button>
  </div>
</div>
</div>

<script>
var _DATA = [];
var hoy = new Date().toISOString().substring(0,10);

function priClass(p){ return p==='Critico'?'crit':p==='Alta'?'alta':'norm'; }
function priBadge(p){ var c={'Critico':'pr-c','Alta':'pr-a','Normal':'pr-n','Baja':'pr-b'}[p]||'pr-n'; return '<span class="badge-prior '+c+'">'+p+'</span>'; }
function estBadge(e){ var c={'Pendiente':'est-pend','En Proceso':'est-proc','Completado':'est-comp','Cancelado':'est-canc'}[e]||'est-pend'; return '<span class="est-badge '+c+'">'+e+'</span>'; }
function esc(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function isVencido(c){ return c.estado!=='Completado'&&c.estado!=='Cancelado'&&c.fecha_limite&&c.fecha_limite<hoy; }

async function load(){
  var estado = document.getElementById('f-estado').value;
  var empresa = document.getElementById('f-empresa').value;
  var url = '/api/compromisos?estado='+encodeURIComponent(estado)+(empresa?'&empresa='+encodeURIComponent(empresa):'');
  var r = await fetch(url);
  var d = await r.json();
  _DATA = d.compromisos||[];
  render();
}

function render(){
  var q = document.getElementById('f-q').value.toLowerCase();
  var filtered = q ? _DATA.filter(function(c){ return (c.descripcion||'').toLowerCase().indexOf(q)>=0||(c.responsable||'').toLowerCase().indexOf(q)>=0; }) : _DATA;
  // Stats
  var crit=filtered.filter(function(c){return c.prioridad==='Critico'&&c.estado!=='Completado';}).length;
  var alta=filtered.filter(function(c){return c.prioridad==='Alta'&&c.estado!=='Completado';}).length;
  var pend=filtered.filter(function(c){return c.estado==='Pendiente'||c.estado==='En Proceso';}).length;
  var done=filtered.filter(function(c){return c.estado==='Completado';}).length;
  var venc=filtered.filter(isVencido).length;
  document.getElementById('stats').innerHTML =
    (crit?'<span class="stat-pill sp-crit">&#x1F534; '+crit+' critico(s)</span>':'')+
    (venc?'<span class="stat-pill sp-crit">&#x23F0; '+venc+' vencido(s)</span>':'')+
    (alta?'<span class="stat-pill sp-alta">&#x1F7E1; '+alta+' alta prioridad</span>':'')+
    '<span class="stat-pill sp-pend">&#x1F535; '+pend+' pendientes</span>'+
    '<span class="stat-pill sp-done">&#x2705; '+done+' completados</span>';
  if(!filtered.length){
    document.getElementById('list').innerHTML='<div class="empty">No hay compromisos con estos filtros</div>';
    return;
  }
  document.getElementById('list').innerHTML = filtered.map(function(c){
    var isDone = c.estado==='Completado';
    var isVenc = isVencido(c);
    var cardCls = isDone?'done':priClass(c.prioridad);
    var checkCls = isDone?'done':'';
    var checkIcon = isDone?'&#x2713;':'';
    return '<div class="comp-card '+cardCls+'">' +
      '<div class="comp-check '+checkCls+'" onclick="toggleDone('+c.id+','+isDone+')">'+checkIcon+'</div>'+
      '<div class="comp-body">'+
        '<div class="comp-desc">'+esc(c.descripcion)+'</div>'+
        '<div class="comp-meta">'+
          priBadge(c.prioridad)+' '+estBadge(c.estado)+
          (c.responsable?'<span>&#x1F464; '+esc(c.responsable)+'</span>':'')+
          (c.area?'<span>&#x1F3E2; '+esc(c.area)+'</span>':'')+
          (c.fecha_limite?'<span>'+(isVenc?'<span class="vencido-tag">VENCIDO </span>':'&#x1F4C5; ')+c.fecha_limite+'</span>':'')+
          (c.empresa?'<span>&#x1F3ED; '+esc(c.empresa)+'</span>':'')+
          (c.origen?'<span>&#x1F4CB; '+esc(c.origen)+'</span>':'')+
        '</div>'+
        (c.notas?'<div style="font-size:11px;color:#78716c;font-style:italic;margin-top:4px;">'+esc(c.notas)+'</div>':'')+
        '<div class="comp-actions">'+
          (!isDone?'<button class="btn btn-succ" onclick="marcar('+c.id+','Completado')">Completado</button>':'') +
          (c.estado==='Pendiente'?'<button class="btn btn-warn" onclick="marcar('+c.id+','En Proceso')">En Proceso</button>':'')+
          '<button class="btn btn-outl" onclick="promptNota('+c.id+')">Nota</button>'+
        '</div>'+
      '</div></div>';
  }).join('');
}

async function toggleDone(id, wasDone){
  var nuevoEstado = wasDone ? 'Pendiente' : 'Completado';
  await fetch('/api/compromisos/'+id, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:nuevoEstado})});
  load();
}
async function marcar(id, estado){
  await fetch('/api/compromisos/'+id, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:estado})});
  load();
}
async function promptNota(id){
  var nota = prompt('Agregar nota:');
  if(!nota) return;
  await fetch('/api/compromisos/'+id, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({notas:nota})});
  load();
}

function abrirModal(){
  ['n-desc','n-resp','n-area','n-origen'].forEach(function(id){document.getElementById(id).value='';});
  document.getElementById('n-prior').value='Normal';
  document.getElementById('n-emp').value='Espagiria';
  document.getElementById('n-fecha').value='';
  document.getElementById('modal').classList.remove('hidden');
}
function cerrar(){document.getElementById('modal').classList.add('hidden');}
async function guardar(){
  var desc=document.getElementById('n-desc').value.trim();
  if(!desc){alert('Descripcion requerida');return;}
  var body={
    descripcion:desc,responsable:document.getElementById('n-resp').value,
    area:document.getElementById('n-area').value,fecha_limite:document.getElementById('n-fecha').value,
    prioridad:document.getElementById('n-prior').value,empresa:document.getElementById('n-emp').value,
    origen:document.getElementById('n-origen').value
  };
  await fetch('/api/compromisos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  cerrar(); load();
}

document.getElementById('modal').addEventListener('click',function(e){if(e.target===this)cerrar();});
load();
</script>
</body>
</html>"""

HOME_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>HHA Group</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#f5f4f2;color:#1C1917;min-height:100vh;}
.hdr{background:#1C1917;color:#fff;padding:18px 28px;display:flex;align-items:center;gap:16px;}
.hdr-logo{font-size:22px;font-weight:900;}
.hdr-sub{font-size:12px;color:#a8a29e;margin-top:2px;}
.hdr-right{margin-left:auto;font-size:12px;color:#78716c;}
.wrap{max-width:960px;margin:40px auto;padding:0 20px;}
.greeting{font-size:24px;font-weight:800;margin-bottom:6px;}
.greeting-sub{font-size:14px;color:#78716c;margin-bottom:32px;}
.sect{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#a8a29e;margin-bottom:12px;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(175px,1fr));gap:14px;margin-bottom:32px;}
.card{background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:20px 16px;display:flex;flex-direction:column;align-items:center;gap:7px;text-decoration:none;color:#1C1917;transition:.15s;}
.card:hover{border-color:#a8a29e;box-shadow:0 4px 16px rgba(0,0,0,.08);transform:translateY(-2px);}
.card-icon{font-size:28px;}
.card-name{font-size:13px;font-weight:700;text-align:center;}
.card-desc{font-size:11px;color:#78716c;text-align:center;}
.card.ceo{border-color:#292524;background:#1C1917;color:#fff;}
.card.ceo .card-desc{color:#a8a29e;}
.card.ceo:hover{background:#292524;}
.note{text-align:center;font-size:12px;color:#a8a29e;margin-top:8px;}
.note a{color:#292524;font-weight:600;text-decoration:none;}
</style>
</head>
<body>
<div class="hdr"><div><div class="hdr-logo">HHA Group</div><div class="hdr-sub">Espagiria &middot; ANIMUS Lab</div></div><div class="hdr-right">Sistema de Gestion Interna</div></div>
<div class="wrap">
  <div class="greeting">&#128075; Bienvenido</div>
  <div class="greeting-sub">Selecciona el modulo al que deseas acceder.</div>
  <div class="sect">Produccion &amp; Inventario</div>
  <div class="grid">
    <a href="/inventarios" class="card"><div class="card-icon">&#128230;</div><div class="card-name">Inventario</div><div class="card-desc">Stock, lotes, trazabilidad</div></a>
    <a href="/recepcion" class="card"><div class="card-icon">&#128666;</div><div class="card-name">Recepcion</div><div class="card-desc">Ingreso de MP y MEE</div></a>
    <a href="/hub-salida" class="card"><div class="card-icon">&#128664;</div><div class="card-name">Despachos</div><div class="card-desc">Salidas y remisiones</div></a>
    <a href="/maquila" class="card"><div class="card-icon">&#127981;</div><div class="card-name">Maquila</div><div class="card-desc">Produccion por encargo</div></a>
  </div>
  <div class="sect">Comercial &amp; Compras</div>
  <div class="grid">
    <a href="/compras" class="card"><div class="card-icon">&#128722;</div><div class="card-name">Compras</div><div class="card-desc">OC, proveedores, pagos</div></a>
    <a href="/clientes" class="card"><div class="card-icon">&#128101;</div><div class="card-name">Clientes</div><div class="card-desc">Pedidos y despachos</div></a>
  </div>
  <div class="sect">Gerencia</div>
  <div class="grid">
    <a href="/gerencia" class="card ceo"><div class="card-icon">&#127759;</div><div class="card-name">Centro de Comando</div><div class="card-desc">Alertas, KPIs, decisiones</div></a>
    <a href="/gerencia-financiero" class="card ceo"><div class="card-icon">&#128200;</div><div class="card-name">Financiero</div><div class="card-desc">P&amp;L, flujo de caja, WC</div></a>
    <a href="/compromisos" class="card ceo"><div class="card-icon">&#128203;</div><div class="card-name">Compromisos</div><div class="card-desc">Actas y seguimiento</div></a>
    <a href="/rrhh" class="card ceo"><div class="card-icon">&#128101;</div><div class="card-name">RRHH</div><div class="card-desc">Nomina y empleados</div></a>
  </div>
  <div class="note">Los modulos oscuros requieren <a href="/login">iniciar sesion como CEO</a></div>
</div>
</body>
</html>"""

HUB_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>HHA Group — Centro de Comando</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;font-size:14px;min-height:100vh;}
.header{background:#1e293b;border-bottom:1px solid #334155;padding:14px 20px;display:flex;align-items:center;gap:12px;}
.header-logo{font-size:20px;font-weight:800;color:#fff;letter-spacing:-0.5px;}
.header-sub{font-size:12px;color:#94a3b8;margin-top:1px;}
.header-right{margin-left:auto;text-align:right;font-size:12px;color:#94a3b8;}
.header-right strong{display:block;color:#fff;font-size:13px;}
.alert-bar{padding:10px 20px;display:flex;gap:10px;align-items:center;background:#1e293b;border-bottom:1px solid #334155;flex-wrap:wrap;}
.al-pill{display:flex;align-items:center;gap:5px;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:700;cursor:pointer;}
.al-crit{background:#450a0a;color:#fca5a5;border:1px solid #7f1d1d;}
.al-aten{background:#451a03;color:#fcd34d;border:1px solid #78350f;}
.al-ok{background:#052e16;color:#86efac;border:1px solid #14532d;}
.al-pulse{width:8px;height:8px;border-radius:50%;animation:pulse 1.5s infinite;}
.al-crit .al-pulse{background:#ef4444;}
.al-aten .al-pulse{background:#f59e0b;}
.al-ok .al-pulse{background:#22c55e;}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:.4;}}
.main{padding:20px;max-width:1400px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;gap:16px;}
@media(max-width:768px){.main{grid-template-columns:1fr;}}
.card{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px;}
.card-title{font-size:12px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.7px;margin-bottom:12px;display:flex;align-items:center;gap:6px;}
.card-full{grid-column:1/-1;}
.alert-item{display:flex;align-items:flex-start;gap:10px;padding:10px;border-radius:8px;margin-bottom:8px;background:#0f172a;border:1px solid #1e293b;}
.alert-item.crit{border-left:3px solid #ef4444;}
.alert-item.aten{border-left:3px solid #f59e0b;}
.al-icon{font-size:16px;flex-shrink:0;margin-top:1px;}
.al-body{flex:1;}
.al-title{font-size:12px;font-weight:700;color:#e2e8f0;margin-bottom:2px;}
.al-detail{font-size:11px;color:#94a3b8;line-height:1.4;}
.al-action{display:inline-block;margin-top:5px;padding:3px 10px;background:#334155;color:#e2e8f0;border-radius:4px;font-size:10px;text-decoration:none;font-weight:600;}
.al-action:hover{background:#475569;}
.kpi-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;}
.kpi{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:12px;}
.kpi-label{font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px;}
.kpi-val{font-size:22px;font-weight:800;color:#f1f5f9;}
.kpi-val.warn{color:#fb923c;}
.kpi-val.crit{color:#f87171;}
.kpi-val.good{color:#4ade80;}
.kpi-sub{font-size:11px;color:#64748b;margin-top:2px;}
.module-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;}
.mod-btn{display:flex;flex-direction:column;align-items:center;gap:6px;padding:14px 10px;background:#0f172a;border:1px solid #334155;border-radius:10px;text-decoration:none;color:#e2e8f0;transition:.15s;cursor:pointer;}
.mod-btn:hover{background:#1e293b;border-color:#475569;}
.mod-icon{font-size:24px;}
.mod-name{font-size:12px;font-weight:600;text-align:center;}
.mod-badge{font-size:10px;padding:1px 7px;border-radius:10px;font-weight:700;}
.mb-warn{background:#451a03;color:#fcd34d;}
.mb-ok{background:#052e16;color:#86efac;}
.mb-neutral{background:#1e293b;color:#94a3b8;}
.comp-mini{display:flex;flex-direction:column;gap:6px;}
.comp-mini-item{display:flex;align-items:center;gap:8px;padding:8px 10px;background:#0f172a;border-radius:6px;border:1px solid #1e293b;}
.comp-mini-item.crit{border-left:2px solid #ef4444;}
.comp-mini-item.alta{border-left:2px solid #f59e0b;}
.comp-mini-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}
.dot-crit{background:#ef4444;}
.dot-alta{background:#f59e0b;}
.dot-norm{background:#3b82f6;}
.comp-mini-text{font-size:12px;color:#cbd5e1;flex:1;line-height:1.3;}
.comp-mini-meta{font-size:10px;color:#64748b;margin-left:auto;text-align:right;white-space:nowrap;}
.section-hdr{font-size:13px;font-weight:700;color:#f1f5f9;margin-bottom:10px;}
.loading{color:#64748b;font-size:12px;text-align:center;padding:20px;}
.spinner-txt{animation:pulse 1.5s infinite;}
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="header-logo">HHA Group</div>
    <div class="header-sub">Espagiria &nbsp;·&nbsp; ANIMUS Lab</div>
  </div>
  <div class="header-right">
    <strong id="fecha-hoy"></strong>
    <span>Centro de Comando</span>
  </div>
</div>

<div class="alert-bar" id="alert-bar">
  <span class="spinner-txt" style="font-size:12px;color:#64748b;">Calculando alertas...</span>
</div>

<div class="main">
  <!-- ALERTAS ACTIVAS -->
  <div class="card">
    <div class="card-title">&#x26A0; Requiere tu decision</div>
    <div id="alertas-list"><div class="loading spinner-txt">Cargando...</div></div>
  </div>

  <!-- PULSO FINANCIERO -->
  <div class="card">
    <div class="card-title">&#x1F4B0; Pulso Financiero</div>
    <div class="kpi-grid" id="kpi-fin">
      <div class="loading spinner-txt" style="grid-column:1/-1;">Cargando...</div>
    </div>
  </div>

  <!-- COMPROMISOS CRITICOS -->
  <div class="card">
    <div class="card-title">&#x1F4CB; Compromisos criticos &amp; vencidos</div>
    <div id="comp-list"><div class="loading spinner-txt">Cargando...</div></div>
    <a href="/compromisos" style="display:block;text-align:center;margin-top:10px;font-size:12px;color:#64748b;text-decoration:none;">Ver todos los compromisos &rarr;</a>
  </div>

  <!-- MODULOS -->
  <div class="card">
    <div class="card-title">&#x1F5C4; Modulos del sistema</div>
    <div class="module-grid" id="mod-grid">
      <a class="mod-btn" href="/inventarios"><span class="mod-icon">&#x1F4E6;</span><span class="mod-name">Inventario</span><span class="mod-badge mb-neutral" id="mb-inv">-</span></a>
      <a class="mod-btn" href="/compras"><span class="mod-icon">&#x1F6D2;</span><span class="mod-name">Compras</span><span class="mod-badge mb-neutral" id="mb-comp">-</span></a>
      <a class="mod-btn" href="/recepcion"><span class="mod-icon">&#x1F69A;</span><span class="mod-name">Recepcion</span><span class="mod-badge mb-ok">activo</span></a>
      <a class="mod-btn" href="/clientes"><span class="mod-icon">&#x1F464;</span><span class="mod-name">Clientes</span><span class="mod-badge mb-neutral" id="mb-cli">-</span></a>
      <a class="mod-btn" href="/financiero"><span class="mod-icon">&#x1F4CA;</span><span class="mod-name">Financiero</span><span class="mod-badge mb-ok">activo</span></a>
      <a class="mod-btn" href="/gerencia"><span class="mod-icon">&#x1F3DB;</span><span class="mod-name">Gerencia</span><span class="mod-badge mb-ok">activo</span></a>
      <a class="mod-btn" href="/compromisos"><span class="mod-icon">&#x2705;</span><span class="mod-name">Compromisos</span><span class="mod-badge mb-neutral" id="mb-comp2">-</span></a>
      <a class="mod-btn" href="/maquila"><span class="mod-icon">&#x1F9EA;</span><span class="mod-name">Maquila</span><span class="mod-badge mb-ok">activo</span></a>
    </div>
  </div>
</div>

<script>
document.getElementById('fecha-hoy').textContent = new Date().toLocaleDateString('es-CO',{weekday:'long',year:'numeric',month:'long',day:'numeric'});

function fmt(n){ return '$'+parseFloat(n||0).toLocaleString('es-CO',{minimumFractionDigits:0,maximumFractionDigits:0}); }

async function loadAll(){
  try{
    var [ra, rr] = await Promise.all([fetch('/api/hub/alertas'), fetch('/api/hub/resumen')]);
    var alertas = await ra.json();
    var resumen = await rr.json();
    renderAlerts(alertas);
    renderKpis(resumen);
    updateModuleBadges(alertas.resumen, resumen);
  }catch(e){ console.error(e); }
  try{
    var rc = await fetch('/api/compromisos?estado=Todos');
    var dc = await rc.json();
    renderCompromisos(dc.compromisos||[]);
  }catch(e){}
}

function renderAlerts(data){
  var alertas = data.alertas||[];
  var res = data.resumen||{};
  // Update alert bar
  var barHtml = '';
  if(res.critico>0) barHtml += '<div class="al-pill al-crit"><span class="al-pulse"></span>'+res.critico+' urgente'+(res.critico>1?'s':'')+'</div>';
  if(res.atencion>0) barHtml += '<div class="al-pill al-aten"><span class="al-pulse"></span>'+res.atencion+' atencion</div>';
  if(!res.critico && !res.atencion) barHtml = '<div class="al-pill al-ok"><span class="al-pulse"></span>Todo en orden</div>';
  document.getElementById('alert-bar').innerHTML = barHtml;
  // Alertas list
  if(!alertas.length){
    document.getElementById('alertas-list').innerHTML='<div class="loading" style="color:#4ade80;">&#x2705; Sin alertas activas</div>';
    return;
  }
  document.getElementById('alertas-list').innerHTML = alertas.slice(0,8).map(function(a){
    var icon = a.nivel==='critico' ? '&#x1F534;' : '&#x1F7E1;';
    return '<div class="alert-item '+a.nivel+'">'+
      '<span class="al-icon">'+icon+'</span>'+
      '<div class="al-body">'+
        '<div class="al-title">'+a.titulo+'</div>'+
        '<div class="al-detail">'+a.detalle+'</div>'+
        (a.accion?'<a class="al-action" href="'+a.accion+'">Ver &rarr;</a>':'')+
      '</div></div>';
  }).join('');
}

function renderKpis(r){
  var ocs = r.ocs||{};
  var comps = r.compromisos||{};
  document.getElementById('kpi-fin').innerHTML =
    mkKpi('Por autorizar', ocs.por_autorizar+' OCs', fmt(ocs.valor_autorizar||0), ocs.por_autorizar>0?'warn':'')+
    mkKpi('Por pagar', ocs.por_pagar+' OCs', fmt(ocs.valor_pagar||0), ocs.por_pagar>0?'warn':'')+
    mkKpi('Pagado esta semana', '',''+fmt(r.pagado_semana||0), 'good')+
    mkKpi('Stock critico', r.stock_critico+' materiales', 'bajo minimo', r.stock_critico>5?'crit':r.stock_critico>0?'warn':'')+
    mkKpi('Compromisos pendientes', comps.pendientes+' items', comps.vencidos+' vencidos', comps.vencidos>0?'crit':'')+
    mkKpi('Clientes activos', r.clientes||0,'en sistema','');
}

function mkKpi(label,val,sub,cls){
  return '<div class="kpi"><div class="kpi-label">'+label+'</div><div class="kpi-val'+(cls?' '+cls:'')+'" >'+val+'</div><div class="kpi-sub">'+sub+'</div></div>';
}

function renderCompromisos(items){
  var hoy = new Date().toISOString().substring(0,10);
  var urgent = items.filter(function(c){
    return c.estado!=='Completado'&&c.estado!=='Cancelado'&&(c.prioridad==='Critico'||(c.fecha_limite&&c.fecha_limite<hoy));
  }).slice(0,6);
  if(!urgent.length){
    document.getElementById('comp-list').innerHTML='<div class="loading" style="color:#4ade80;">&#x2705; Sin compromisos urgentes</div>';
    return;
  }
  document.getElementById('comp-list').innerHTML = urgent.map(function(c){
    var isVenc = c.fecha_limite && c.fecha_limite < hoy;
    var cls = c.prioridad==='Critico'?'crit':'alta';
    var dotCls = c.prioridad==='Critico'?'dot-crit':'dot-alta';
    return '<div class="comp-mini-item '+cls+'">'+
      '<span class="comp-mini-dot '+dotCls+'"></span>'+
      '<span class="comp-mini-text">'+c.descripcion.substring(0,55)+'</span>'+
      '<span class="comp-mini-meta">'+(isVenc?'<span style="color:#f87171;">VENC</span> ':'')+c.responsable+'<br>'+(c.fecha_limite||'')+'</span>'+
    '</div>';
  }).join('');
}

function updateModuleBadges(alRes, r){
  var compBadge = document.getElementById('mb-comp');
  if(compBadge){
    var cnt = (r.ocs||{}).por_autorizar||0;
    compBadge.textContent = cnt>0 ? cnt+' pendiente'+(cnt>1?'s':'') : 'ok';
    compBadge.className = 'mod-badge '+(cnt>0?'mb-warn':'mb-ok');
  }
  var cliBadge = document.getElementById('mb-cli');
  if(cliBadge){ cliBadge.textContent = r.clientes+' activos'; }
  var comp2 = document.getElementById('mb-comp2');
  if(comp2){
    var cv = (r.compromisos||{}).vencidos||0;
    comp2.textContent = cv>0?cv+' vencidos':'ok';
    comp2.className = 'mod-badge '+(cv>0?'mb-warn':'mb-ok');
  }
}

loadAll();
setInterval(loadAll, 60000);
</script>
</body>
</html>"""

# ─── LOGIN COMPRAS ────────────────────────────────────────────
# ─── MÓDULO CLIENTES ──────────────────────────────────────────
CLIENTES_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Clientes — HHA Group</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#F5F4F0;min-height:100vh;}
.topbar{background:#2B7A78;color:white;padding:14px 28px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 12px rgba(43,122,120,0.3);}
.topbar-title{font-size:1.1em;font-weight:800;letter-spacing:2px;}
.topbar a{color:rgba(255,255,255,0.75);text-decoration:none;font-size:0.82em;padding:6px 14px;border:1px solid rgba(255,255,255,0.25);border-radius:6px;transition:all 0.2s;}
.topbar a:hover{background:rgba(255,255,255,0.15);color:white;}
.tabs{background:white;border-bottom:1px solid #E8E4DE;padding:0 28px;display:flex;gap:4px;}
.tab{padding:14px 22px;cursor:pointer;font-size:0.88em;font-weight:600;color:#7A9E9C;border-bottom:3px solid transparent;transition:all 0.2s;white-space:nowrap;}
.tab.active{color:#2B7A78;border-bottom-color:#2B7A78;}
.tab:hover:not(.active){color:#2B7A78;background:#f5fafa;}
.content{padding:28px;max-width:1200px;margin:0 auto;}
.page{display:none;}.page.active{display:block;}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:28px;}
.kpi{background:white;border:1px solid #E8E4DE;border-radius:12px;padding:20px 22px;border-left:4px solid var(--c,#2B7A78);}
.kpi-val{font-size:2em;font-weight:900;color:var(--c,#2B7A78);line-height:1;}
.kpi-lbl{font-size:0.78em;color:#7A9E9C;text-transform:uppercase;letter-spacing:1px;margin-top:6px;}
.kpi-sub{font-size:0.82em;color:#9C8B7A;margin-top:4px;}
.tbl{width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,0.06);}
.tbl thead th{background:#f8fafa;color:#5C7A7A;font-size:0.78em;text-transform:uppercase;letter-spacing:0.8px;padding:10px 14px;text-align:left;border-bottom:1px solid #E8E4DE;}
.tbl tbody td{padding:11px 14px;border-bottom:1px solid #F0EEEA;font-size:0.88em;vertical-align:middle;}
.tbl tbody tr:hover{background:#fafcfc;}
.tbl tbody tr:last-child td{border-bottom:none;}
.btn{display:inline-flex;align-items:center;gap:6px;padding:9px 18px;border:none;border-radius:8px;cursor:pointer;font-size:0.88em;font-weight:600;transition:all 0.2s;background:#2B7A78;color:white;}
.btn:hover{background:#1d5c5a;transform:translateY(-1px);}
.btn-ghost{background:white;color:#2B7A78;border:1.5px solid #2B7A78;}
.btn-ghost:hover{background:#f0f9f9;}
.btn-sm{padding:5px 12px;font-size:0.8em;}
.badge{display:inline-block;padding:3px 10px;border-radius:12px;font-size:0.75em;font-weight:700;}
.badge-verde{background:#d1fae5;color:#065f46;}
.badge-amarillo{background:#fef3c7;color:#92400e;}
.badge-rojo{background:#fee2e2;color:#991b1b;}
.badge-gris{background:#f3f4f6;color:#374151;}
.badge-azul{background:#dbeafe;color:#1e40af;}
.empty{text-align:center;color:#aaa;padding:32px;font-size:0.9em;}
.msg-ok{background:#d1fae5;color:#065f46;padding:10px 14px;border-radius:8px;margin:8px 0;font-size:0.88em;}
.msg-err{background:#fee2e2;color:#991b1b;padding:10px 14px;border-radius:8px;margin:8px 0;font-size:0.88em;}
.section-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;}
.section-header h2{font-size:1.1em;font-weight:700;color:#1C2B30;}
.form-panel{background:white;border:1px solid #E8E4DE;border-radius:12px;padding:24px;margin-bottom:20px;display:none;}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;}
.form-row.single{grid-template-columns:1fr;}
.form-row.triple{grid-template-columns:1fr 1fr 1fr;}
.form-group label{display:block;font-size:0.8em;font-weight:600;color:#5C7A7A;margin-bottom:5px;text-transform:uppercase;letter-spacing:0.5px;}
.form-group input,.form-group select,.form-group textarea{width:100%;padding:9px 12px;border:1.5px solid #D8E4E4;border-radius:7px;font-size:0.88em;background:#fafcfc;transition:border 0.2s;}
.form-group input:focus,.form-group select:focus,.form-group textarea:focus{outline:none;border-color:#2B7A78;background:white;}
.semaforo{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;}
.sem-verde{background:#10b981;}.sem-amarillo{background:#f59e0b;}.sem-rojo{background:#ef4444;}
.stock-bar{height:6px;border-radius:3px;background:#E8E4DE;overflow:hidden;margin-top:4px;}
.stock-bar-fill{height:100%;border-radius:3px;background:#2B7A78;transition:width 0.4s;}
.kanban{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;}
.kanban-col{background:#f8fafa;border-radius:10px;padding:14px;}
.kanban-col-title{font-size:0.78em;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#5C7A7A;margin-bottom:10px;}
.kanban-card{background:white;border:1px solid #E8E4DE;border-radius:8px;padding:12px;margin-bottom:8px;cursor:pointer;}
.kanban-card:hover{border-color:#2B7A78;box-shadow:0 2px 8px rgba(43,122,120,0.1);}
</style>
</head>
<body>
<div class="topbar">
  <a href="/" class="hha-back">&#8592; Inicio</a>
  <span class="topbar-title">&#128101; CLIENTES — HHA Group</span>
</div>
<div class="tabs">
  <div class="tab active" onclick="goTab('tab-dash',this)">📊 Dashboard</div>
  <div class="tab" onclick="goTab('tab-clientes',this)">🏢 Clientes</div>
  <div class="tab" onclick="goTab('tab-pedidos',this)">📋 Pedidos</div>
  <div class="tab" onclick="goTab('tab-stock',this)">📦 Stock PT</div>
  <div class="tab" onclick="goTab('tab-despachos',this)">🚚 Despachos</div>
</div>

<div class="content">

<!-- DASHBOARD -->
<div id="tab-dash" class="page active">
  <div class="kpi-grid" id="kpi-clientes">
    <div class="kpi" style="--c:#2B7A78"><div class="kpi-val" id="kpi-uds">—</div><div class="kpi-lbl">Unidades PT disponibles</div></div>
    <div class="kpi" style="--c:#B5924A"><div class="kpi-val" id="kpi-ped-act">—</div><div class="kpi-lbl">Pedidos activos</div><div class="kpi-sub" id="kpi-ped-val">—</div></div>
    <div class="kpi" style="--c:#4A8B6A"><div class="kpi-val" id="kpi-skus">—</div><div class="kpi-lbl">SKUs con stock</div></div>
    <div class="kpi" style="--c:#7A4A8B"><div class="kpi-val" id="kpi-fm-dias">—</div><div class="kpi-lbl">Días último pedido FM</div><div class="kpi-sub">Ciclo normal: ~62 días</div></div>
  </div>
  <div style="background:white;border:1px solid #E8E4DE;border-radius:12px;padding:20px;margin-bottom:20px;">
    <h3 style="font-size:0.95em;font-weight:700;color:#1C2B30;margin-bottom:14px;">Stock PT por SKU</h3>
    <table class="tbl"><thead><tr><th>SKU</th><th>Descripción</th><th>Disponible</th><th>Total producido</th><th>Lotes</th><th>Estado</th></tr></thead>
    <tbody id="stock-dash-body"><tr><td colspan="6" class="empty">Cargando...</td></tr></tbody></table>
  </div>
  <div id="alertas-clientes"></div>
</div>

<!-- CLIENTES -->
<div id="tab-clientes" class="page">
  <div class="section-header">
    <h2>Clientes registrados</h2>
    <button class="btn btn-ghost" onclick="toggleForm('form-nuevo-cliente')">+ Nuevo cliente</button>
  </div>
  <div class="form-panel" id="form-nuevo-cliente">
    <h3 style="margin-bottom:16px;font-size:0.95em;font-weight:700;">Nuevo cliente</h3>
    <div class="form-row">
      <div class="form-group"><label>Nombre *</label><input type="text" id="cli-nombre" placeholder="Nombre del cliente"></div>
      <div class="form-group"><label>Empresa</label><select id="cli-empresa"><option value="ANIMUS">ÁNIMUS Lab</option><option value="Espagiria">Espagiria</option></select></div>
    </div>
    <div class="form-row triple">
      <div class="form-group"><label>Tipo</label><select id="cli-tipo"><option value="Distribuidor">Distribuidor</option><option value="Retail">Retail</option><option value="DTC">DTC</option><option value="Maquila">Maquila</option><option value="Interno">Interno</option></select></div>
      <div class="form-group"><label>Condiciones de pago</label><input type="text" id="cli-pago" placeholder="30 días" value="30 días"></div>
      <div class="form-group"><label>NIT</label><input type="text" id="cli-nit" placeholder="900.000.000-0"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Contacto</label><input type="text" id="cli-contacto" placeholder="Nombre del contacto"></div>
      <div class="form-group"><label>Email</label><input type="email" id="cli-email" placeholder="email@empresa.com"></div>
    </div>
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:8px;">
      <button class="btn btn-ghost" onclick="toggleForm('form-nuevo-cliente')">Cancelar</button>
      <button class="btn" onclick="crearCliente()">Guardar cliente</button>
    </div>
    <div id="cli-msg"></div>
  </div>
  <table class="tbl"><thead><tr><th>Código</th><th>Nombre</th><th>Tipo</th><th>Empresa</th><th>Pedidos</th><th>Facturado total</th><th>Último pedido</th><th>Acción</th></tr></thead>
  <tbody id="clientes-body"><tr><td colspan="8" class="empty">Cargando...</td></tr></tbody></table>
</div>

<!-- PEDIDOS -->
<div id="tab-pedidos" class="page">
  <div class="section-header">
    <h2>Pedidos</h2>
    <button class="btn btn-ghost" onclick="toggleForm('form-nuevo-pedido')">+ Nuevo pedido</button>
  </div>
  <div class="form-panel" id="form-nuevo-pedido">
    <h3 style="margin-bottom:16px;font-size:0.95em;font-weight:700;">Nuevo pedido</h3>
    <div class="form-row">
      <div class="form-group"><label>Cliente *</label><select id="ped-cliente"><option value="">Seleccionar...</option></select></div>
      <div class="form-group"><label>Fecha entrega estimada</label><input type="date" id="ped-fecha-ent"></div>
    </div>
    <div class="form-group" style="margin-bottom:14px;"><label>Observaciones</label><textarea id="ped-obs" rows="2" style="width:100%;padding:9px 12px;border:1.5px solid #D8E4E4;border-radius:7px;font-size:0.88em;"></textarea></div>
    <div style="margin-bottom:10px;">
      <div style="display:grid;grid-template-columns:15% 1fr 10% 15% 5%;gap:6px;font-size:11px;color:#888;font-weight:700;margin-bottom:4px;padding:0 2px;">
        <span>SKU</span><span>Descripción *</span><span>Cant.</span><span>Precio unit. $</span><span></span>
      </div>
      <div id="ped-items-list">
        <div class="ped-item-row" style="display:grid;grid-template-columns:15% 1fr 10% 15% 5%;gap:6px;margin-bottom:6px;align-items:center;">
          <input type="text" class="ped-sku" placeholder="TRX-120" style="font-family:monospace;padding:7px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.85em;">
          <input type="text" class="ped-desc" placeholder="Nombre del producto" style="padding:7px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.85em;">
          <input type="number" class="ped-cant" placeholder="500" min="1" style="padding:7px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.85em;">
          <input type="number" class="ped-precio" placeholder="31933" min="0" style="padding:7px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.85em;">
          <button onclick="this.parentElement.remove()" style="padding:5px;background:#fee2e2;border:none;border-radius:4px;cursor:pointer;">✕</button>
        </div>
      </div>
      <button class="btn btn-ghost btn-sm" onclick="addItemPedido()" style="margin-top:4px;">+ Agregar línea</button>
    </div>
    <div style="display:flex;gap:10px;justify-content:flex-end;">
      <button class="btn btn-ghost" onclick="toggleForm('form-nuevo-pedido')">Cancelar</button>
      <button class="btn" onclick="crearPedido()">Guardar pedido</button>
    </div>
    <div id="ped-msg"></div>
  </div>
  <div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap;">
    <button class="btn btn-ghost btn-sm" onclick="loadPedidos('')">Todos</button>
    <button class="btn btn-ghost btn-sm" onclick="loadPedidos('Confirmado')">Confirmados</button>
    <button class="btn btn-ghost btn-sm" onclick="loadPedidos('Produciendo')">Produciendo</button>
    <button class="btn btn-ghost btn-sm" onclick="loadPedidos('Listo')">Listos para despachar</button>
    <button class="btn btn-ghost btn-sm" onclick="loadPedidos('Despachado')">Despachados</button>
  </div>
  <table class="tbl"><thead><tr><th>Número</th><th>Cliente</th><th>Fecha</th><th>Entrega est.</th><th>Estado</th><th style="text-align:right;">Valor</th><th>Acción</th></tr></thead>
  <tbody id="pedidos-body"><tr><td colspan="7" class="empty">Cargando...</td></tr></tbody></table>
</div>

<!-- STOCK PT -->
<div id="tab-stock" class="page">
  <div class="section-header">
    <h2>Inventario Producto Terminado</h2>
    <button class="btn" onclick="toggleForm('form-ingreso-pt')">+ Registrar PT</button>
  </div>
  <div class="form-panel" id="form-ingreso-pt">
    <h3 style="margin-bottom:16px;font-size:0.95em;font-weight:700;">Registrar ingreso a Stock PT</h3>
    <div class="form-row triple">
      <div class="form-group"><label>SKU *</label><input type="text" id="pt-sku" placeholder="TRX-120-FM" style="text-transform:uppercase;"></div>
      <div class="form-group"><label>Descripción</label><input type="text" id="pt-desc" placeholder="Trébol x 120ml"></div>
      <div class="form-group"><label>Unidades *</label><input type="number" id="pt-uds" placeholder="500" min="1"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Lote de producción</label><input type="text" id="pt-lote" placeholder="PROD-00001"></div>
      <div class="form-group"><label>Precio base (unitario)</label><input type="number" id="pt-precio" placeholder="31933" min="0"></div>
    </div>
    <div style="display:flex;gap:10px;justify-content:flex-end;">
      <button class="btn btn-ghost" onclick="toggleForm('form-ingreso-pt')">Cancelar</button>
      <button class="btn" onclick="registrarPT()">Registrar</button>
    </div>
    <div id="pt-msg"></div>
  </div>
  <table class="tbl"><thead><tr><th>SKU</th><th>Descripción</th><th>Empresa</th><th style="text-align:right;">Disponible</th><th style="text-align:right;">Total</th><th>Lotes</th><th>Estado</th></tr></thead>
  <tbody id="stock-pt-body"><tr><td colspan="7" class="empty">Cargando...</td></tr></tbody></table>
</div>

<!-- DESPACHOS -->
<div id="tab-despachos" class="page">
  <div class="section-header">
    <h2>Historial de despachos</h2>
  </div>
  <table class="tbl"><thead><tr><th>Número</th><th>Fecha</th><th>Cliente</th><th>Pedido</th><th>Operador</th><th>Estado</th></tr></thead>
  <tbody id="despachos-body"><tr><td colspan="6" class="empty">Cargando...</td></tr></tbody></table>
</div>

</div><!-- /content -->

<script>
function goTab(id,btn){
  document.querySelectorAll('.page').forEach(function(p){p.classList.remove('active');});
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});
  document.getElementById(id).classList.add('active');
  if(btn) btn.classList.add('active');
  if(id==='tab-dash') loadDashboardClientes();
  if(id==='tab-clientes') loadClientes();
  if(id==='tab-pedidos') loadPedidos('');
  if(id==='tab-stock') loadStockPT();
  if(id==='tab-despachos') loadDespachos();
}
function toggleForm(id){var f=document.getElementById(id);f.style.display=f.style.display==='block'?'none':'block';}
function fmt(n){return n?('$'+parseFloat(n).toLocaleString('es-CO')):'—';}
function badgePed(e){
  var m={'Confirmado':'badge-azul','Produciendo':'badge-amarillo','Listo':'badge-verde',
         'Despachado':'badge-gris','Facturado':'badge-gris','Cancelado':'badge-rojo','Borrador':'badge-gris'};
  return '<span class="badge '+(m[e]||'badge-gris')+'">'+e+'</span>';
}

async function loadDashboardClientes(){
  try{
    var [st,pd]=await Promise.all([
      fetch('/api/stock-pt').then(function(r){return r.json();}),
      fetch('/api/pedidos').then(function(r){return r.json();})
    ]);
    var stock=st.stock_pt||[]; var peds=pd.pedidos||[];
    var uds=stock.reduce(function(a,s){return a+(s.disponible||0);},0);
    var skus=stock.filter(function(s){return s.disponible>0;}).length;
    var pedAct=peds.filter(function(p){return ['Confirmado','Produciendo','Listo'].includes(p.estado);});
    var valAct=pedAct.reduce(function(a,p){return a+(p.valor_total||0);},0);
    document.getElementById('kpi-uds').textContent=uds.toLocaleString('es-CO');
    document.getElementById('kpi-ped-act').textContent=pedAct.length;
    document.getElementById('kpi-ped-val').textContent=fmt(valAct);
    document.getElementById('kpi-skus').textContent=skus;
    // FM dias
    try{
      var fm=peds.filter(function(p){return p.cliente_codigo==='CLI-002'&&p.estado!='Cancelado';});
      if(fm.length){
        var ult=fm.sort(function(a,b){return b.fecha>a.fecha?1:-1;})[0];
        var dias=Math.floor((Date.now()-new Date(ult.fecha))/86400000);
        var el=document.getElementById('kpi-fm-dias');
        el.textContent=dias;
        el.style.color=dias>55?'#ef4444':'#2B7A78';
      }
    }catch(e){}
    // Tabla stock
    var tb=document.getElementById('stock-dash-body');
    if(!stock.length){tb.innerHTML='<tr><td colspan="6" class="empty">Sin stock PT registrado</td></tr>';return;}
    tb.innerHTML=stock.map(function(s){
      var pct=s.total>0?Math.round((s.disponible/s.total)*100):0;
      var color=pct>50?'#2B7A78':(pct>20?'#f59e0b':'#ef4444');
      var badge=pct>50?'badge-verde':(pct>20?'badge-amarillo':'badge-rojo');
      return '<tr><td style="font-family:monospace;font-weight:700;">'+s.sku+'</td>'
        +'<td>'+s.descripcion+'</td>'
        +'<td><span class="badge badge-gris">'+s.empresa+'</span></td>'
        +'<td style="text-align:right;font-weight:700;font-size:1.05em;">'+s.disponible.toLocaleString('es-CO')+'</td>'
        +'<td style="text-align:right;color:#999;">'+s.total.toLocaleString('es-CO')+'</td>'
        +'<td style="text-align:center;">'+s.lotes+'</td>'
        +'<td><span class="badge '+badge+'">'+pct+'% disponible</span>'
        +'<div class="stock-bar"><div class="stock-bar-fill" style="width:'+pct+'%;background:'+color+';"></div></div></td></tr>';
    }).join('');
  }catch(e){console.error(e);}
}

async function loadClientes(){
  try{
    var d=await fetch('/api/clientes').then(function(r){return r.json();});
    var tb=document.getElementById('clientes-body');
    var cls=d.clientes||[];
    if(!cls.length){tb.innerHTML='<tr><td colspan="8" class="empty">Sin clientes</td></tr>';return;}
    // Cargar también select de pedidos
    var sel=document.getElementById('ped-cliente');
    sel.innerHTML='<option value="">Seleccionar...</option>';
    cls.forEach(function(cl){sel.innerHTML+='<option value="'+cl.id+'">'+cl.nombre+' ('+cl.codigo+')</option>';});
    tb.innerHTML=cls.map(function(cl){
      var badge=cl.tipo==='Distribuidor'?'badge-azul':(cl.tipo==='Interno'?'badge-gris':'badge-amarillo');
      return '<tr>'
        +'<td style="font-family:monospace;font-size:0.82em;color:#888;">'+cl.codigo+'</td>'
        +'<td style="font-weight:600;">'+cl.nombre+'</td>'
        +'<td><span class="badge '+badge+'">'+cl.tipo+'</span></td>'
        +'<td><span class="badge badge-gris">'+cl.empresa+'</span></td>'
        +'<td style="text-align:center;">'+(cl.total_pedidos||0)+'</td>'
        +'<td style="text-align:right;font-weight:600;color:#2B7A78;">'+fmt(cl.facturado_total)+'</td>'
        +'<td style="color:#999;font-size:0.85em;">'+(cl.ultimo_pedido||'').substring(0,10)+'</td>'
        +'<td><button class="btn btn-ghost btn-sm" onclick="verHistorialCliente('+cl.id+',\\''+cl.nombre+'\\')">Historial</button></td>'
        +'</tr>';
    }).join('');
  }catch(e){console.error(e);}
}

async function crearCliente(){
  var nombre=document.getElementById('cli-nombre').value.trim();
  if(!nombre){alert('Nombre requerido');return;}
  var data={nombre:nombre,empresa:document.getElementById('cli-empresa').value,
    tipo:document.getElementById('cli-tipo').value,contacto:document.getElementById('cli-contacto').value,
    email:document.getElementById('cli-email').value,nit:document.getElementById('cli-nit').value,
    condiciones_pago:document.getElementById('cli-pago').value};
  try{
    var r=await fetch('/api/clientes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    document.getElementById('cli-msg').innerHTML=r.ok?'<div class="msg-ok">'+res.message+'</div>':'<div class="msg-err">'+(res.error||'Error')+'</div>';
    if(r.ok){loadClientes();document.getElementById('cli-nombre').value='';}
  }catch(e){document.getElementById('cli-msg').innerHTML='<div class="msg-err">Error</div>';}
}

async function loadPedidos(estado){
  try{
    var url='/api/pedidos'+(estado?'?estado='+estado:'');
    var d=await fetch(url).then(function(r){return r.json();});
    var tb=document.getElementById('pedidos-body');
    var peds=d.pedidos||[];
    if(!peds.length){tb.innerHTML='<tr><td colspan="7" class="empty">Sin pedidos'+(estado?' en estado '+estado:'')+'</td></tr>';return;}
    tb.innerHTML=peds.map(function(p){
      return '<tr>'
        +'<td style="font-family:monospace;font-weight:700;">'+p.numero+'</td>'
        +'<td style="font-weight:600;">'+(p.cliente||'—')+'</td>'
        +'<td style="color:#999;font-size:0.85em;">'+(p.fecha||'').substring(0,10)+'</td>'
        +'<td style="color:#999;font-size:0.85em;">'+(p.fecha_entrega_est||'—')+'</td>'
        +'<td>'+badgePed(p.estado)+'</td>'
        +'<td style="text-align:right;font-weight:700;color:#2B7A78;">'+fmt(p.valor_total)+'</td>'
        +'<td><button class="btn btn-ghost btn-sm" onclick="cambiarEstadoPedido(\\''+p.numero+'\\')">Estado</button></td>'
        +'</tr>';
    }).join('');
  }catch(e){console.error(e);}
}

function addItemPedido(){
  var div=document.createElement('div');
  div.className='ped-item-row';
  div.style.cssText='display:grid;grid-template-columns:15% 1fr 10% 15% 5%;gap:6px;margin-bottom:6px;align-items:center;';
  div.innerHTML='<input type="text" class="ped-sku" placeholder="SKU" style="font-family:monospace;padding:7px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.85em;">'
    +'<input type="text" class="ped-desc" placeholder="Descripción" style="padding:7px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.85em;">'
    +'<input type="number" class="ped-cant" placeholder="0" min="1" style="padding:7px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.85em;">'
    +'<input type="number" class="ped-precio" placeholder="0" min="0" style="padding:7px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.85em;">'
    +'<button onclick="this.parentElement.remove()" style="padding:5px;background:#fee2e2;border:none;border-radius:4px;cursor:pointer;">✕</button>';
  document.getElementById('ped-items-list').appendChild(div);
}

async function crearPedido(){
  var cid=document.getElementById('ped-cliente').value;
  if(!cid){alert('Selecciona un cliente');return;}
  var items=[];
  document.querySelectorAll('.ped-item-row').forEach(function(row){
    var sku=row.querySelector('.ped-sku').value.trim();
    var desc=row.querySelector('.ped-desc').value.trim();
    var cant=parseInt(row.querySelector('.ped-cant').value)||0;
    var precio=parseFloat(row.querySelector('.ped-precio').value)||0;
    if((sku||desc)&&cant>0) items.push({sku:sku,descripcion:desc,cantidad:cant,precio_unitario:precio,subtotal:cant*precio});
  });
  if(!items.length){alert('Agrega al menos un ítem');return;}
  var data={cliente_id:parseInt(cid),fecha_entrega_est:document.getElementById('ped-fecha-ent').value,
    observaciones:document.getElementById('ped-obs').value,items:items};
  try{
    var r=await fetch('/api/pedidos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    document.getElementById('ped-msg').innerHTML=r.ok?'<div class="msg-ok">'+res.message+'</div>':'<div class="msg-err">'+(res.error||'Error')+'</div>';
    if(r.ok){loadPedidos('');toggleForm('form-nuevo-pedido');}
  }catch(e){document.getElementById('ped-msg').innerHTML='<div class="msg-err">Error</div>';}
}

async function cambiarEstadoPedido(numero){
  var estados=['Confirmado','Produciendo','Listo','Despachado','Facturado','Cancelado'];
  var nuevo=prompt('Nuevo estado para '+numero+':\n'+estados.join(', '));
  if(!nuevo||!estados.includes(nuevo)) return;
  await fetch('/api/pedidos/'+numero,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:nuevo})});
  loadPedidos('');
}

async function loadStockPT(){
  try{
    var d=await fetch('/api/stock-pt').then(function(r){return r.json();});
    var tb=document.getElementById('stock-pt-body');
    var stock=d.stock_pt||[];
    if(!stock.length){tb.innerHTML='<tr><td colspan="7" class="empty">Sin stock PT registrado</td></tr>';return;}
    tb.innerHTML=stock.map(function(s){
      var pct=s.total>0?Math.round((s.disponible/s.total)*100):0;
      var badge=pct>50?'badge-verde':(pct>20?'badge-amarillo':'badge-rojo');
      return '<tr>'
        +'<td style="font-family:monospace;font-weight:700;color:#2B7A78;">'+s.sku+'</td>'
        +'<td>'+(s.descripcion||'—')+'</td>'
        +'<td><span class="badge badge-gris">'+s.empresa+'</span></td>'
        +'<td style="text-align:right;font-weight:900;font-size:1.1em;">'+(s.disponible||0).toLocaleString('es-CO')+' uds</td>'
        +'<td style="text-align:right;color:#999;">'+(s.total||0).toLocaleString('es-CO')+' uds</td>'
        +'<td style="text-align:center;">'+(s.lotes||0)+'</td>'
        +'<td><span class="badge '+badge+'">'+pct+'% disponible</span></td>'
        +'</tr>';
    }).join('');
  }catch(e){console.error(e);}
}

async function registrarPT(){
  var sku=(document.getElementById('pt-sku').value||'').trim().toUpperCase();
  var uds=parseInt(document.getElementById('pt-uds').value)||0;
  if(!sku||uds<=0){alert('SKU y unidades requeridos');return;}
  var data={sku:sku,descripcion:document.getElementById('pt-desc').value,
    unidades:uds,lote_produccion:document.getElementById('pt-lote').value,
    precio_base:parseFloat(document.getElementById('pt-precio').value)||0};
  try{
    var r=await fetch('/api/stock-pt',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    document.getElementById('pt-msg').innerHTML=r.ok?'<div class="msg-ok">'+res.message+'</div>':'<div class="msg-err">'+(res.error||'Error')+'</div>';
    if(r.ok){loadStockPT();document.getElementById('pt-sku').value='';document.getElementById('pt-uds').value='';}
  }catch(e){document.getElementById('pt-msg').innerHTML='<div class="msg-err">Error</div>';}
}

async function loadDespachos(){
  try{
    var d=await fetch('/api/despachos').then(function(r){return r.json();});
    var tb=document.getElementById('despachos-body');
    var desps=d.despachos||[];
    if(!desps.length){tb.innerHTML='<tr><td colspan="6" class="empty">Sin despachos registrados</td></tr>';return;}
    tb.innerHTML=desps.map(function(d){
      return '<tr>'
        +'<td style="font-family:monospace;font-weight:700;">'+d.numero+'</td>'
        +'<td style="color:#999;font-size:0.85em;">'+(d.fecha||'').substring(0,10)+'</td>'
        +'<td style="font-weight:600;">'+(d.cliente||'—')+'</td>'
        +'<td style="font-family:monospace;font-size:0.82em;color:#888;">'+(d.numero_pedido||'—')+'</td>'
        +'<td>'+(d.operador||'—')+'</td>'
        +'<td><span class="badge badge-verde">'+d.estado+'</span></td>'
        +'</tr>';
    }).join('');
  }catch(e){console.error(e);}
}

async function verHistorialCliente(id,nombre){
  var d=await fetch('/api/clientes/'+id+'/historial').then(function(r){return r.json();});
  var h='<b>Historial: '+nombre+'</b><br><br>';
  if(d.pedidos&&d.pedidos.length){
    h+='<b>Pedidos:</b><table style="width:100%;border-collapse:collapse;font-size:13px;margin-top:6px;">';
    h+='<tr style="background:#f5f5f5;"><th style="padding:5px;text-align:left;">Número</th><th>Estado</th><th style="text-align:right;">Valor</th><th>Despacho</th></tr>';
    d.pedidos.forEach(function(p){
      h+='<tr><td style="padding:5px;font-family:monospace;">'+p.numero+'</td><td>'+badgePed(p.estado)+'</td><td style="text-align:right;">'+fmt(p.valor_total)+'</td><td style="color:#999;font-size:0.85em;">'+(p.fecha_despacho||'—').substring(0,10)+'</td></tr>';
    });
    h+='</table>';
  } else { h+='Sin pedidos registrados.'; }
  var panel=document.createElement('div');
  panel.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;display:flex;align-items:center;justify-content:center;';
  panel.innerHTML='<div style="background:white;border-radius:14px;padding:28px;max-width:600px;width:92%;max-height:80vh;overflow-y:auto;position:relative;">'
    +'<button onclick="this.closest(\'div[style]\').remove()" style="position:absolute;top:12px;right:14px;background:none;border:none;font-size:20px;cursor:pointer;">✕</button>'
    +h+'</div>';
  document.body.appendChild(panel);
}

// Auto-cargar dashboard al iniciar
loadDashboardClientes();
</script>
</body>
</html>"""

# ─── MÓDULO HQ GERENCIA ────────────────────────────────────────
GERENCIA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Gerencia — HHA Group</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#1C2B30;min-height:100vh;color:white;}
.topbar{background:rgba(0,0,0,0.3);padding:14px 28px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,0.1);}
.topbar-left{display:flex;align-items:center;gap:16px;}
.logo{font-size:0.95em;font-weight:900;letter-spacing:3px;color:white;}
.badge-ceo{background:rgba(43,122,120,0.5);color:#7ACFCC;padding:3px 12px;border-radius:20px;font-size:0.72em;font-weight:700;letter-spacing:1px;}
.topbar a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.8em;padding:6px 14px;border:1px solid rgba(255,255,255,0.15);border-radius:6px;}
.topbar a:hover{color:white;border-color:rgba(255,255,255,0.4);}
.periodo-badge{background:rgba(43,122,120,0.3);padding:4px 14px;border-radius:20px;font-size:0.78em;color:#7ACFCC;}
.main{padding:28px;max-width:1300px;margin:0 auto;}
.section-title{font-size:0.72em;text-transform:uppercase;letter-spacing:2px;color:rgba(255,255,255,0.4);margin-bottom:14px;margin-top:28px;}
.section-title:first-child{margin-top:0;}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:8px;}
.kpi{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:20px 22px;position:relative;overflow:hidden;transition:all 0.2s;}
.kpi:hover{background:rgba(255,255,255,0.08);transform:translateY(-2px);}
.kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--ac,#2B7A78);}
.kpi.rojo::before{background:#ef4444;}.kpi.amarillo::before{background:#f59e0b;}.kpi.verde::before{background:#10b981;}
.kpi-val{font-size:2.2em;font-weight:900;line-height:1;color:white;}
.kpi-val.rojo{color:#fca5a5;}.kpi-val.amarillo{color:#fcd34d;}.kpi-val.verde{color:#6ee7b7;}
.kpi-lbl{font-size:0.72em;color:rgba(255,255,255,0.45);text-transform:uppercase;letter-spacing:1px;margin-top:8px;}
.kpi-sub{font-size:0.8em;color:rgba(255,255,255,0.3);margin-top:4px;}
.sem{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle;}
.sem.verde{background:#10b981;box-shadow:0 0 8px #10b981;}.sem.amarillo{background:#f59e0b;box-shadow:0 0 8px #f59e0b;}.sem.rojo{background:#ef4444;box-shadow:0 0 8px #ef4444;}
.alertas-panel{background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:12px;padding:20px;margin-bottom:28px;display:none;}
.alertas-panel.visible{display:block;}
.alerta-item{display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid rgba(239,68,68,0.15);}
.alerta-item:last-child{border-bottom:none;}
.alerta-icon{font-size:1.2em;margin-top:1px;}
.alerta-texto{font-size:0.88em;color:rgba(255,255,255,0.8);line-height:1.5;}
.two-cols{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px;}
.panel{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:22px;}
.panel-title{font-size:0.82em;font-weight:700;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:16px;display:flex;align-items:center;gap:8px;}
.data-row{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid rgba(255,255,255,0.06);}
.data-row:last-child{border-bottom:none;}
.data-lbl{font-size:0.85em;color:rgba(255,255,255,0.5);}
.data-val{font-size:0.92em;font-weight:700;color:white;}
.data-val.rojo{color:#fca5a5;}.data-val.amarillo{color:#fcd34d;}.data-val.verde{color:#6ee7b7;}
.input-panel{background:rgba(43,122,120,0.1);border:1px solid rgba(43,122,120,0.3);border-radius:12px;padding:22px;margin-top:20px;}
.input-panel-title{font-size:0.85em;font-weight:700;color:#7ACFCC;margin-bottom:16px;display:flex;align-items:center;gap:8px;}
.inp-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:14px;}
.inp-group label{display:block;font-size:0.72em;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:5px;}
.inp-group input{width:100%;padding:9px 12px;background:rgba(255,255,255,0.08);border:1.5px solid rgba(255,255,255,0.15);border-radius:7px;color:white;font-size:0.9em;transition:border 0.2s;}
.inp-group input:focus{outline:none;border-color:#2B7A78;background:rgba(255,255,255,0.12);}
.inp-group input::placeholder{color:rgba(255,255,255,0.25);}
.btn-save{background:#2B7A78;color:white;border:none;padding:10px 24px;border-radius:8px;font-size:0.88em;font-weight:700;cursor:pointer;transition:all 0.2s;}
.btn-save:hover{background:#1d5c5a;transform:translateY(-1px);}
.msg-ok-dark{background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);color:#6ee7b7;padding:9px 14px;border-radius:8px;font-size:0.85em;margin-top:10px;}
.msg-err-dark{background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);color:#fca5a5;padding:9px 14px;border-radius:8px;font-size:0.85em;margin-top:10px;}
.finanzas-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:8px;}
.fin-card{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:16px 18px;text-align:center;}
.fin-val{font-size:1.6em;font-weight:900;color:#7ACFCC;}
.fin-lbl{font-size:0.72em;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:1px;margin-top:5px;}
.refresh-btn{background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:6px 14px;border-radius:6px;font-size:0.8em;cursor:pointer;transition:all 0.2s;}
.refresh-btn:hover{background:rgba(255,255,255,0.15);color:white;}
.ultima-act{font-size:0.72em;color:rgba(255,255,255,0.25);margin-left:10px;}
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-left">
    <a href="/" style="color:#a8a29e;text-decoration:none;font-size:12px;margin-right:4px;">&#8592; Inicio</a>
    <span class="logo">HHA GROUP</span>
    <span class="badge-ceo">PANEL GERENCIAL</span>
    <span class="periodo-badge" id="periodo-label">Cargando...</span>
  </div>
  <div style="display:flex;align-items:center;gap:12px;">
    <button class="refresh-btn" onclick="loadKPIs()">⟳ Actualizar</button>
    <span class="ultima-act" id="ultima-actualizacion"></span>
    <a href="/" style="font-size:12px;color:#a8a29e;text-decoration:none;">&#8592; Inicio</a>
  </div>
</div>

<div class="main">

  <!-- ALERTAS CRÍTICAS -->
  <div class="alertas-panel" id="alertas-panel">
    <div style="font-size:0.82em;font-weight:700;color:#fca5a5;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">⚠ Alertas que requieren acción</div>
    <div id="alertas-list"></div>
  </div>

  <!-- FINANCIERO (inputs manuales) -->
  <div class="section-title">💰 Financiero del mes</div>
  <div class="finanzas-grid">
    <div class="fin-card"><div class="fin-val" id="fin-caja">—</div><div class="fin-lbl">Saldo de caja</div></div>
    <div class="fin-card"><div class="fin-val" id="fin-animus">—</div><div class="fin-lbl">Ingresos ÁNIMUS</div></div>
    <div class="fin-card"><div class="fin-val" id="fin-maquila">—</div><div class="fin-lbl">Ingresos Maquila</div></div>
  </div>

  <!-- ESPAGIRIA -->
  <div class="section-title">🏭 Espagiria Laboratorios</div>
  <div class="kpi-grid">
    <div class="kpi" id="kpi-mps-bajos">
      <div class="kpi-val" id="val-mps-bajos">—</div>
      <div class="kpi-lbl">MPs bajo mínimo</div>
      <div class="kpi-sub" id="sub-deficit">—</div>
    </div>
    <div class="kpi" id="kpi-vencen30">
      <div class="kpi-val" id="val-vencen30">—</div>
      <div class="kpi-lbl">Lotes vencen en 30 días</div>
      <div class="kpi-sub" id="sub-vencen60">—</div>
    </div>
    <div class="kpi" id="kpi-produccion">
      <div class="kpi-val" id="val-lotes-mes">—</div>
      <div class="kpi-lbl">Lotes producción mes</div>
      <div class="kpi-sub" id="sub-kg-mes">—</div>
    </div>
    <div class="kpi" id="kpi-ocs">
      <div class="kpi-val" id="val-ocs">—</div>
      <div class="kpi-lbl">OCs pendientes aprobación</div>
      <div class="kpi-sub" id="sub-ocs-val">—</div>
    </div>
  </div>

  <!-- ÁNIMUS -->
  <div class="section-title">✨ ÁNIMUS Lab</div>
  <div class="kpi-grid">
    <div class="kpi verde">
      <div class="kpi-val verde" id="val-uds-pt">—</div>
      <div class="kpi-lbl">Unidades PT disponibles</div>
      <div class="kpi-sub" id="sub-skus-pt">—</div>
    </div>
    <div class="kpi" id="kpi-pedidos-act">
      <div class="kpi-val" id="val-pedidos-act">—</div>
      <div class="kpi-lbl">Pedidos activos</div>
      <div class="kpi-sub" id="sub-pedidos-val">—</div>
    </div>
    <div class="kpi" id="kpi-fm">
      <div class="kpi-val" id="val-fm-dias">—</div>
      <div class="kpi-lbl">Días desde último pedido FM</div>
      <div class="kpi-sub">Ciclo promedio: ~62 días</div>
    </div>
  </div>

  <!-- DETALLE DOS COLUMNAS -->
  <div class="two-cols">
    <div class="panel">
      <div class="panel-title"><span class="sem verde" id="sem-inv"></span>Inventario Espagiria</div>
      <div id="detalle-inventario"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title"><span class="sem verde" id="sem-animus"></span>ÁNIMUS Lab</div>
      <div id="detalle-animus"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
  </div>

  <!-- INPUT MANUAL MENSUAL -->
  <div class="input-panel">
    <div class="input-panel-title">📝 Input manual mensual <span style="font-weight:400;color:rgba(255,255,255,0.3);font-size:0.85em;">— actualizar en 5 minutos al inicio de cada mes</span></div>
    <div class="inp-grid">
      <div class="inp-group"><label>Saldo de caja ($COP)</label><input type="number" id="inp-caja" placeholder="354800000"></div>
      <div class="inp-group"><label>Ingresos ÁNIMUS mes ($COP)</label><input type="number" id="inp-animus" placeholder="189000000"></div>
      <div class="inp-group"><label>Ingresos Maquila mes ($COP)</label><input type="number" id="inp-maquila" placeholder="30000000"></div>
      <div class="inp-group"><label>Nómina total mes ($COP)</label><input type="number" id="inp-nomina" placeholder="16100000"></div>
    </div>
    <div class="inp-group" style="margin-bottom:14px;"><label>Notas del período</label><input type="text" id="inp-notas" placeholder="Ej: Mes de lanzamiento NIAC, pago nómina atrasado..."></div>
    <button class="btn-save" onclick="guardarInputs()">💾 Guardar inputs del mes</button>
    <div id="inp-msg"></div>
  </div>

  <!-- FLUJO OPERACIONAL -->
  <div class="section-title" style="margin-top:32px;">🔄 Flujo Operacional — Vista Ejecutiva</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin-bottom:20px;">
    <div class="panel">
      <div class="panel-title">📦 Compras pendientes de recibir
        <a href="/recepcion" style="margin-left:auto;font-size:0.75em;color:#7ACFCC;text-decoration:none;font-weight:600;">→ Recepción</a>
      </div>
      <div id="g-ocs-transito"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">⚠ Recepciones con discrepancias</div>
      <div id="g-disc"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">🚚 Pedidos listos para despachar
        <a href="/hub-salida" style="margin-left:auto;font-size:0.75em;color:#7ACFCC;text-decoration:none;font-weight:600;">→ Hub Salida</a>
      </div>
      <div id="g-pedidos-listos"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">✅ Despachos recientes</div>
      <div id="g-despachos"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
  </div>

  <!-- QUICK NAV -->
  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:28px;">
    <a href="/recepcion" style="background:rgba(43,122,120,0.2);border:1px solid rgba(43,122,120,0.4);color:#7ACFCC;padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">📥 Recepción de Mercancía</a>
    <a href="/hub-salida" style="background:rgba(74,103,65,0.2);border:1px solid rgba(74,103,65,0.4);color:#8BC98A;padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">📤 Hub de Salida</a>
    <a href="/compras" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">🛒 Módulo Compras</a>
    <a href="/clientes" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">👤 Módulo Clientes</a>
    <a href="/financiero" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">💰 Financiero</a>
  </div>



  <!-- INDICADORES EJECUTIVOS -->
  <div class="section-title" style="margin-top:32px;">📊 Indicadores Ejecutivos — Tiempo Real</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:20px;">
    <div class="panel">
      <div class="panel-title">💰 Ingresos del mes (real)</div>
      <div id="gx-ingresos"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">📥 Cuentas por cobrar (AR)</div>
      <div id="gx-ar"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">📤 Cuentas por pagar (AP)</div>
      <div id="gx-ap"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">🏭 Pipeline Maquila activo</div>
      <div id="gx-maquila"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin-bottom:28px;">
    <div class="panel">
      <div class="panel-title">⚠ Stock Critico — MPs bajo minimo</div>
      <div id="gx-stock"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">✅ SGSST — Proximos vencimientos</div>
      <div id="gx-sgsst"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">🔒 Accesos recientes</div>
      <div id="gx-sec"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
  </div>

</div><!-- /main -->

<script>
function fmt(n,prefix){if(n==null||n===undefined)return '—';var v=Math.abs(parseFloat(n));var s=v>=1000000?(v/1000000).toFixed(1)+'M':(v>=1000?(v/1000).toFixed(0)+'K':v.toLocaleString('es-CO'));return (prefix||'$')+s;}
function fmtN(n){return n!=null?parseFloat(n).toLocaleString('es-CO'):'—';}
function setSemaforo(id,color){var el=document.getElementById(id);if(el){el.className='sem '+color;}}
function setKPIColor(kpiId,valId,color){
  var k=document.getElementById(kpiId),v=document.getElementById(valId);
  if(k) k.className='kpi '+(color||'');
  if(v) v.className='kpi-val '+(color||'');
}

async function loadKPIs(){
  try{
    var d=await fetch('/api/gerencia/kpis').then(function(r){return r.json();});
    if(d.error){document.querySelector('.main').innerHTML='<div style="color:#fca5a5;padding:40px;text-align:center;">'+d.error+'</div>';return;}

    var e=d.espagiria||{}; var a=d.animus||{}; var f=d.inputs_manuales||{}; var sem=d.semaforos||{};

    // Periodo
    document.getElementById('periodo-label').textContent=d.periodo||'';
    document.getElementById('ultima-actualizacion').textContent='Actualizado: '+new Date().toLocaleTimeString('es-CO');

    // Financiero
    document.getElementById('fin-caja').textContent=fmt(f.saldo_caja);
    document.getElementById('fin-animus').textContent=fmt(f.ingresos_animus);
    document.getElementById('fin-maquila').textContent=fmt(f.ingresos_maquila);

    // Espagiria KPIs
    var mpsBajos=e.mps_bajo_minimo||0;
    document.getElementById('val-mps-bajos').textContent=mpsBajos;
    document.getElementById('sub-deficit').textContent='Déficit: '+((e.deficit_total_kg||0).toFixed(1))+' kg';
    setKPIColor('kpi-mps-bajos','val-mps-bajos',mpsBajos>5?'rojo':(mpsBajos>0?'amarillo':'verde'));

    var v30=e.lotes_vencen_30d||0;
    document.getElementById('val-vencen30').textContent=v30;
    document.getElementById('sub-vencen60').textContent='En 60 días: '+(e.lotes_vencen_60d||0)+' lotes';
    setKPIColor('kpi-vencen30','val-vencen30',v30>0?'rojo':'verde');

    document.getElementById('val-lotes-mes').textContent=e.lotes_produccion_mes||0;
    document.getElementById('sub-kg-mes').textContent=(e.kg_producidos_mes||0)+' kg producidos';

    var ocs=e.ocs_pendientes_aprobacion||0;
    document.getElementById('val-ocs').textContent=ocs;
    document.getElementById('sub-ocs-val').textContent='Valor: '+fmt(e.valor_ocs_pendientes||0);
    setKPIColor('kpi-ocs','val-ocs',ocs>3?'amarillo':'verde');

    // ÁNIMUS KPIs
    document.getElementById('val-uds-pt').textContent=fmtN(a.unidades_pt_disponibles||0);
    document.getElementById('sub-skus-pt').textContent=(a.skus_con_stock_pt||0)+' SKUs con stock';

    var pedAct=a.pedidos_activos||0;
    document.getElementById('val-pedidos-act').textContent=pedAct;
    document.getElementById('sub-pedidos-val').textContent='Valor: '+fmt(a.valor_pedidos_activos||0);

    var diasFM=a.dias_desde_ultimo_pedido_fm;
    var diasFMEl=document.getElementById('val-fm-dias');
    diasFMEl.textContent=diasFM!=null?diasFM+' días':'Sin pedidos';
    setKPIColor('kpi-fm','val-fm-dias',diasFM>62?'amarillo':'verde');

    // Semáforos
    setSemaforo('sem-inv',sem.inventario||'verde');
    setSemaforo('sem-animus',sem.fm||'verde');

    // Detalle inventario
    var di='';
    di+='<div class="data-row"><span class="data-lbl">MPs bajo mínimo</span><span class="data-val '+(mpsBajos>0?'rojo':'verde')+'">'+mpsBajos+'</span></div>';
    di+='<div class="data-row"><span class="data-lbl">Déficit total</span><span class="data-val '+(e.deficit_total_kg>0?'amarillo':'verde')+'">'+((e.deficit_total_kg||0).toFixed(1))+' kg</span></div>';
    di+='<div class="data-row"><span class="data-lbl">Lotes vencen 30d</span><span class="data-val '+(v30>0?'rojo':'verde')+'">'+v30+'</span></div>';
    di+='<div class="data-row"><span class="data-lbl">Lotes vencen 60d</span><span class="data-val '+(e.lotes_vencen_60d>0?'amarillo':'verde')+'">'+(e.lotes_vencen_60d||0)+'</span></div>';
    di+='<div class="data-row"><span class="data-lbl">Producción este mes</span><span class="data-val">'+(e.lotes_produccion_mes||0)+' lotes / '+(e.kg_producidos_mes||0)+' kg</span></div>';
    di+='<div class="data-row"><span class="data-lbl">OCs pendientes</span><span class="data-val '+(ocs>0?'amarillo':'verde')+'">'+ocs+' ('+fmt(e.valor_ocs_pendientes||0)+')</span></div>';
    document.getElementById('detalle-inventario').innerHTML=di;

    // Detalle ÁNIMUS
    var da='';
    da+='<div class="data-row"><span class="data-lbl">Unidades PT disponibles</span><span class="data-val verde">'+fmtN(a.unidades_pt_disponibles||0)+'</span></div>';
    da+='<div class="data-row"><span class="data-lbl">SKUs con stock</span><span class="data-val">'+(a.skus_con_stock_pt||0)+'</span></div>';
    da+='<div class="data-row"><span class="data-lbl">Pedidos activos</span><span class="data-val">'+(a.pedidos_activos||0)+' ('+fmt(a.valor_pedidos_activos||0)+')</span></div>';
    da+='<div class="data-row"><span class="data-lbl">Último pedido FM</span><span class="data-val">'+(a.ultimo_pedido_fm||'Sin datos')+'</span></div>';
    da+='<div class="data-row"><span class="data-lbl">Días desde pedido FM</span><span class="data-val '+(diasFM>55?'amarillo':'verde')+'">'+(diasFM!=null?diasFM+' días':'—')+'</span></div>';
    document.getElementById('detalle-animus').innerHTML=da;

    // Alertas
    var alertas=[];
    if(mpsBajos>0) alertas.push({icon:'🔴',txt:'<strong>'+mpsBajos+' MPs bajo mínimo</strong> — Déficit total: '+((e.deficit_total_kg||0).toFixed(1))+' kg. Generar OC desde Compras.'});
    if(v30>0) alertas.push({icon:'🔴',txt:'<strong>'+v30+' lotes vencen en los próximos 30 días</strong> — Revisar y usar en próximas producciones (FEFO).'});
    if(ocs>3) alertas.push({icon:'🟡',txt:'<strong>'+ocs+' órdenes de compra</strong> esperando aprobación — Valor total: '+fmt(e.valor_ocs_pendientes||0)+'.'});
    if(diasFM!=null&&diasFM>55) alertas.push({icon:'🟡',txt:'<strong>Fernando Mesa: '+diasFM+' días sin pedir</strong> — Ciclo normal ~62 días. Próximo pedido inminente.'});
    if(f.saldo_caja>0&&f.nomina_total>0&&f.saldo_caja<f.nomina_total*2) alertas.push({icon:'🔴',txt:'<strong>Caja baja:</strong> Saldo '+fmt(f.saldo_caja)+' cubre menos de 2 nóminas.'});

    var panel=document.getElementById('alertas-panel');
    if(alertas.length>0){
      panel.classList.add('visible');
      document.getElementById('alertas-list').innerHTML=alertas.map(function(a){
        return '<div class="alerta-item"><span class="alerta-icon">'+a.icon+'</span><span class="alerta-texto">'+a.txt+'</span></div>';
      }).join('');
    } else {
      panel.classList.remove('visible');
    }

    // Pre-cargar inputs en el formulario
    if(f.saldo_caja) document.getElementById('inp-caja').value=f.saldo_caja;
    if(f.ingresos_animus) document.getElementById('inp-animus').value=f.ingresos_animus;
    if(f.ingresos_maquila) document.getElementById('inp-maquila').value=f.ingresos_maquila;
    if(f.nomina_total) document.getElementById('inp-nomina').value=f.nomina_total;
    if(f.notas) document.getElementById('inp-notas').value=f.notas;

  }catch(e){console.error(e);}
}

async function guardarInputs(){
  var data={
    saldo_caja:parseFloat(document.getElementById('inp-caja').value)||0,
    ingresos_animus:parseFloat(document.getElementById('inp-animus').value)||0,
    ingresos_maquila:parseFloat(document.getElementById('inp-maquila').value)||0,
    nomina_total:parseFloat(document.getElementById('inp-nomina').value)||0,
    notas:document.getElementById('inp-notas').value
  };
  try{
    var r=await fetch('/api/gerencia/input-manual',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    document.getElementById('inp-msg').innerHTML=r.ok?'<div class="msg-ok-dark">'+res.message+'</div>':'<div class="msg-err-dark">'+(res.error||'Error')+'</div>';
    if(r.ok) setTimeout(loadKPIs,500);
  }catch(e){document.getElementById('inp-msg').innerHTML='<div class="msg-err-dark">Error</div>';}
}

async function loadFlujoOperacional() {
  try {
    var d = await fetch('/api/gerencia/flujo-operacional').then(function(r){ return r.json(); });
    var nil = '<div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Sin datos</div>';

    // OCs en tránsito
    var elt = document.getElementById('g-ocs-transito');
    if (elt) {
      var ocs = d.ocs_transito || [];
      if (!ocs.length) { elt.innerHTML = '<div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Sin OCs pendientes ✓</div>'; }
      else {
        elt.innerHTML = ocs.slice(0,4).map(function(o) {
          return '<div class="data-row"><span class="data-lbl">' + o.numero_oc + ' — ' + (o.proveedor||'') + '</span>'
            + '<span class="data-val amarillo">' + (o.dias_transito||0) + 'd</span></div>';
        }).join('') + (ocs.length > 4 ? '<div style="color:rgba(255,255,255,0.3);font-size:0.8em;padding:6px 0;">+' + (ocs.length-4) + ' más</div>' : '');
      }
    }

    // Discrepancias
    var eld = document.getElementById('g-disc');
    if (eld) {
      var discs = d.recepciones_disc || [];
      if (!discs.length) { eld.innerHTML = '<div style="color:#6ee7b7;font-size:0.85em;">Sin discrepancias ✓</div>'; }
      else {
        eld.innerHTML = discs.slice(0,4).map(function(r) {
          return '<div class="data-row"><span class="data-lbl">' + r.numero_oc + '</span>'
            + '<span class="data-val rojo">DISC</span></div>';
        }).join('');
      }
    }

    // Pedidos listos
    var elp = document.getElementById('g-pedidos-listos');
    if (elp) {
      var peds = d.pedidos_listos || [];
      if (!peds.length) { elp.innerHTML = '<div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Sin pedidos pendientes</div>'; }
      else {
        elp.innerHTML = peds.slice(0,4).map(function(p) {
          return '<div class="data-row"><span class="data-lbl">' + p.numero + ' — ' + (p.cliente||'') + '</span>'
            + '<span class="data-val amarillo">$' + Number(p.valor_total||0).toLocaleString() + '</span></div>';
        }).join('') + (peds.length > 4 ? '<div style="color:rgba(255,255,255,0.3);font-size:0.8em;padding:6px 0;">+' + (peds.length-4) + ' más</div>' : '');
      }
    }

    // Despachos recientes
    var elsp = document.getElementById('g-despachos');
    if (elsp) {
      var desps = d.despachos_recientes || [];
      if (!desps.length) { elsp.innerHTML = '<div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Sin despachos recientes</div>'; }
      else {
        elsp.innerHTML = desps.slice(0,4).map(function(ds) {
          return '<div class="data-row"><span class="data-lbl">' + ds.numero + ' — ' + (ds.cliente||'') + '</span>'
            + '<span class="data-val verde">' + (ds.fecha||'').slice(0,10) + '</span></div>';
        }).join('');
      }
    }
  } catch(e) { console.error('loadFlujoOperacional:', e); }
}

// Cargar al iniciar
loadKPIs();
loadFlujoOperacional();
// Auto-refresh cada 5 minutos
setInterval(loadKPIs, 300000);
setInterval(loadFlujoOperacional, 300000);

async function loadGerenciaExtra() {
  try {
    var d = await fetch('/api/gerencia/dashboard-extra').then(function(r){ return r.json(); });
    var nil = '<div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Sin datos</div>';
    var fmtV = function(n){ return n==null?'—':'$'+Number(n).toLocaleString('es-CO',{maximumFractionDigits:0}); };
    var clr = function(v,warn,danger){ return v>=danger?'rojo':(v>=warn?'amarillo':'verde'); };

    // Ingresos del mes
    var ig = d.ingresos_mes||{};
    var elI = document.getElementById('gx-ingresos');
    if(elI) elI.innerHTML =
      '<div class="data-row"><span class="data-lbl">ANIMUS</span><span class="data-val verde">'+fmtV(ig.animus)+'</span></div>'
      +'<div class="data-row"><span class="data-lbl">Maquila</span><span class="data-val verde">'+fmtV(ig.maquila)+'</span></div>'
      +'<div class="data-row" style="border-top:1px solid rgba(255,255,255,0.1);margin-top:4px;padding-top:4px;"><span class="data-lbl"><strong>Total</strong></span><span class="data-val verde"><strong>'+fmtV(ig.total)+'</strong></span></div>';

    // AR
    var ar = d.ar||{};
    var elAR = document.getElementById('gx-ar');
    var arClr = ar.total>0?'amarillo':'verde';
    if(elAR) elAR.innerHTML =
      '<div class="data-row"><span class="data-lbl">Total</span><span class="data-val '+arClr+'">'+fmtV(ar.total)+'</span></div>'
      +'<div class="data-row"><span class="data-lbl"># Pedidos</span><span class="data-val">'+( ar.count||0)+'</span></div>'
      +'<div class="data-row"><span class="data-lbl">> 30 dias</span><span class="data-val '+(ar.vencido_30>0?'rojo':'verde')+'">'+fmtV(ar.vencido_30)+'</span></div>'
      +'<div class="data-row"><span class="data-lbl">> 60 dias</span><span class="data-val '+(ar.vencido_60>0?'rojo':'verde')+'">'+fmtV(ar.vencido_60)+'</span></div>';

    // AP
    var ap = d.ap||{};
    var elAP = document.getElementById('gx-ap');
    var apClr = ap.total>500000?'amarillo':'verde';
    if(elAP) elAP.innerHTML =
      '<div class="data-row"><span class="data-lbl">Total</span><span class="data-val '+apClr+'">'+fmtV(ap.total)+'</span></div>'
      +'<div class="data-row"><span class="data-lbl"># OCs</span><span class="data-val">'+( ap.count||0)+'</span></div>'
      +'<div class="data-row"><span class="data-lbl">> 30 dias</span><span class="data-val '+(ap.vencido_30>0?'rojo':'verde')+'">'+fmtV(ap.vencido_30)+'</span></div>'
      +'<div class="data-row"><span class="data-lbl">> 60 dias</span><span class="data-val '+(ap.vencido_60>0?'rojo':'verde')+'">'+fmtV(ap.vencido_60)+'</span></div>';

    // Maquila pipeline
    var mqs = d.maquila_pipeline||[];
    var elM = document.getElementById('gx-maquila');
    if(elM){
      if(!mqs.length){ elM.innerHTML='<div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Sin ordenes activas</div>'; }
      else{
        elM.innerHTML = mqs.slice(0,4).map(function(m){
          return '<div class="data-row"><span class="data-lbl">'+m.numero+' — '+(m.cliente_nombre||'')+'</span><span class="data-val amarillo">'+fmtV(m.precio_lote)+'</span></div>';
        }).join('');
        if(mqs.length>4) elM.innerHTML += '<div style="color:rgba(255,255,255,0.3);font-size:0.8em;padding:4px 0;">+'+(mqs.length-4)+' mas</div>';
      }
    }

    // Stock critico
    var sc = d.stock_critico||[];
    var elSC = document.getElementById('gx-stock');
    if(elSC){
      if(!sc.length){ elSC.innerHTML='<div style="color:#6ee7b7;font-size:0.85em;">Stock OK en todos los MPs</div>'; }
      else{
        elSC.innerHTML = sc.slice(0,6).map(function(mp){
          var pct = mp.stock_minimo>0?Math.round(mp.stock_actual/mp.stock_minimo*100):0;
          return '<div class="data-row"><span class="data-lbl">'+mp.codigo_mp+' '+mp.nombre+'</span>'
            +'<span class="data-val rojo">'+mp.stock_actual.toFixed(0)+'/'+mp.stock_minimo.toFixed(0)+' g ('+pct+'%)</span></div>';
        }).join('');
        if(sc.length>6) elSC.innerHTML += '<div style="color:rgba(255,255,255,0.3);font-size:0.8em;">+'+(sc.length-6)+' MPs mas</div>';
      }
    }

    // SGSST
    var ss = d.sgsst_proximos||[];
    var elSS = document.getElementById('gx-sgsst');
    if(elSS){
      if(!ss.length){ elSS.innerHTML='<div style="color:#6ee7b7;font-size:0.85em;">Sin vencimientos proximos</div>'; }
      else{
        elSS.innerHTML = ss.slice(0,5).map(function(s){
          var c=s.dias_restantes<=15?'rojo':(s.dias_restantes<=30?'amarillo':'verde');
          return '<div class="data-row"><span class="data-lbl">'+s.descripcion.slice(0,30)+'</span><span class="data-val '+c+'">'+s.dias_restantes+'d</span></div>';
        }).join('');
      }
    }

    // Security
    var sec = d.security||{};
    var elSec = document.getElementById('gx-sec');
    if(elSec){
      var secH = '<div class="data-row"><span class="data-lbl">Logins exitosos (7d)</span><span class="data-val verde">'+(sec.success_7d||0)+'</span></div>';
      secH += '<div class="data-row"><span class="data-lbl">Intentos fallidos (7d)</span><span class="data-val '+(sec.fail_7d>5?'rojo':(sec.fail_7d>0?'amarillo':'verde'))+'">'+( sec.fail_7d||0)+'</span></div>';
      if(sec.last_event) secH += '<div class="data-row"><span class="data-lbl">Ultimo evento</span><span class="data-val" style="font-size:0.75em;">'+(sec.last_event||'').slice(0,16)+'</span></div>';
      elSec.innerHTML = secH;
    }

  } catch(e){ console.error('loadGerenciaExtra:', e); }
}

loadGerenciaExtra();
setInterval(loadGerenciaExtra, 300000);
</script>
</body>
</html>"""

# ─── MÓDULO FINANCIERO ────────────────────────────────────────
FINANCIERO_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Financiero — HHA Group</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#F5F4F0;min-height:100vh;}
.topbar{background:#B5924A;color:white;padding:14px 28px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 12px rgba(181,146,74,0.3);}
.topbar-title{font-size:1.1em;font-weight:800;letter-spacing:2px;}
.topbar a{color:rgba(255,255,255,0.8);text-decoration:none;font-size:0.82em;padding:6px 14px;border:1px solid rgba(255,255,255,0.3);border-radius:6px;}
.tabs{background:white;border-bottom:1px solid #E8E4DE;padding:0 28px;display:flex;gap:4px;}
.tab{padding:14px 22px;cursor:pointer;font-size:0.88em;font-weight:600;color:#9C8B7A;border-bottom:3px solid transparent;transition:all 0.2s;white-space:nowrap;}
.tab.active{color:#B5924A;border-bottom-color:#B5924A;}
.tab:hover:not(.active){color:#B5924A;background:#fdf9f4;}
.content{padding:28px;max-width:1200px;margin:0 auto;}
.page{display:none;}.page.active{display:block;}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:28px;}
.kpi{background:white;border:1px solid #E8E4DE;border-radius:12px;padding:20px 22px;border-left:4px solid var(--c,#B5924A);}
.kpi-val{font-size:1.8em;font-weight:900;color:var(--c,#B5924A);line-height:1;}
.kpi-lbl{font-size:0.78em;color:#9C8B7A;text-transform:uppercase;letter-spacing:1px;margin-top:6px;}
.kpi-sub{font-size:0.82em;color:#9C8B7A;margin-top:4px;}
.kpi-delta{font-size:0.82em;margin-top:6px;font-weight:700;}
.kpi-delta.up{color:#2B7A78;}.kpi-delta.down{color:#c0392b;}
.tbl{width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,0.06);}
.tbl thead th{background:#fdf9f4;color:#9C8B7A;font-size:0.78em;text-transform:uppercase;letter-spacing:0.8px;padding:10px 14px;text-align:left;border-bottom:1px solid #E8E4DE;}
.tbl tbody td{padding:11px 14px;border-bottom:1px solid #F5F0EA;font-size:0.88em;vertical-align:middle;}
.tbl tbody tr:hover{background:#fdf9f4;}
.tbl tbody tr:last-child td{border-bottom:none;}
.btn{display:inline-flex;align-items:center;gap:6px;padding:9px 18px;border:none;border-radius:8px;cursor:pointer;font-size:0.88em;font-weight:600;transition:all 0.2s;background:#B5924A;color:white;}
.btn:hover{background:#9a7a3e;}
.btn-ghost{background:white;color:#B5924A;border:1.5px solid #B5924A;}
.btn-red{background:#c0392b;}.btn-green{background:#2B7A78;}
.card{background:white;border:1px solid #E8E4DE;border-radius:12px;padding:22px;margin-bottom:20px;}
.section-title{font-size:1em;font-weight:800;color:#1C2B30;margin-bottom:16px;display:flex;align-items:center;gap:8px;}
.form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:16px;}
.fg label{display:block;font-size:0.78em;color:#9C8B7A;text-transform:uppercase;letter-spacing:0.5px;font-weight:700;margin-bottom:5px;}
.fg input,.fg select,.fg textarea{width:100%;padding:9px 12px;border:1.5px solid #E8E4DE;border-radius:8px;font-size:0.9em;background:white;outline:none;transition:border-color 0.2s;}
.fg input:focus,.fg select:focus{border-color:#B5924A;}
.badge-ing{background:rgba(43,122,120,.1);color:#2B7A78;padding:3px 10px;border-radius:12px;font-size:0.75em;font-weight:700;}
.badge-egr{background:rgba(192,57,43,.1);color:#c0392b;padding:3px 10px;border-radius:12px;font-size:0.75em;font-weight:700;}
.chart-wrap{background:white;border:1px solid #E8E4DE;border-radius:12px;padding:22px;margin-bottom:20px;}
.flujo-pos{color:#2B7A78;font-weight:700;}
.flujo-neg{color:#c0392b;font-weight:700;}
.bar-container{width:100%;background:#f0eeea;border-radius:4px;height:8px;margin-top:6px;}
.bar-fill{height:8px;border-radius:4px;background:var(--bc,#B5924A);transition:width 0.5s;}
</style>
</head>
<body>
<div class="topbar">
  <a href="/" style="color:#a8a29e;text-decoration:none;font-size:13px;margin-right:8px;">&#8592; Inicio</a>
  <div class="topbar-title">💰 FINANCIERO — HHA GROUP</div>
  <div style="display:flex;gap:12px;align-items:center;">
    <span id="periodo-label" style="font-size:0.85em;opacity:0.85;"></span>
    <a href="/gerencia">← Gerencia</a>
    <a href="/">Portal</a>
  </div>
</div>
<div class="tabs">
  <div class="tab active" onclick="goTab('dashboard',this)">📊 Dashboard</div>
  <div class="tab" onclick="goTab('ingresos',this)">📈 Ingresos</div>
  <div class="tab" onclick="goTab('egresos',this)">📉 Egresos</div>
  <div class="tab" onclick="goTab('flujo',this)">🗓️ Flujo Mensual</div>
  <div class="tab" onclick="goTab('ar',this)">📬 Por Cobrar</div>
  <div class="tab" onclick="goTab('ap',this)">📤 Por Pagar</div>
  <div class="tab" onclick="goTab('pnl',this)">📊 P&amp;L</div>
  <div class="tab" onclick="goTab('wc',this)">💼 Capital</div>
  <div class="tab" onclick="goTab('config',this)">⚙️ Supuestos</div>
</div>
<div class="content">

<!-- ─── DASHBOARD ─── -->
<div id="page-dashboard" class="page active">
  <div class="kpi-grid" id="kpi-financiero">
    <div class="kpi" style="--c:#2B7A78"><div class="kpi-val" id="kpi-ing-mes">—</div><div class="kpi-lbl">Ingresos del mes</div><div class="kpi-sub" id="kpi-ing-sub"></div></div>
    <div class="kpi" style="--c:#c0392b"><div class="kpi-val" id="kpi-egr-mes">—</div><div class="kpi-lbl">Egresos del mes</div><div class="kpi-sub" id="kpi-egr-sub"></div></div>
    <div class="kpi" style="--c:#B5924A"><div class="kpi-val" id="kpi-flujo-mes">—</div><div class="kpi-lbl">Flujo neto mes</div><div class="kpi-sub" id="kpi-flujo-sub"></div></div>
    <div class="kpi" style="--c:#7A4A8B"><div class="kpi-val" id="kpi-caja">—</div><div class="kpi-lbl">Saldo de caja</div><div class="kpi-sub" id="kpi-caja-sub"></div></div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">
    <div class="chart-wrap">
      <div class="section-title">Ingresos vs Egresos — Últimos 6 meses</div>
      <canvas id="chart-ing-egr" height="200"></canvas>
    </div>
    <div class="card">
      <div class="section-title">📋 Desglose del mes</div>
      <div id="desglose-mes"></div>
    </div>
  </div>
  <div class="card">
    <div class="section-title">⚠️ Alertas financieras</div>
    <div id="alertas-fin"></div>
  </div>
</div>

<!-- ─── INGRESOS ─── -->
<div id="page-ingresos" class="page">
  <div class="card">
    <div class="section-title">+ Registrar Ingreso</div>
    <div class="form-grid">
      <div class="fg"><label>Fecha</label><input type="date" id="ing-fecha"></div>
      <div class="fg"><label>Empresa</label>
        <select id="ing-empresa">
          <option value="ANIMUS">ÁNIMUS Lab</option>
          <option value="ESPAGIRIA">Espagiria</option>
          <option value="HHA">HHA Group</option>
        </select>
      </div>
      <div class="fg"><label>Categoría</label>
        <select id="ing-cat">
          <option value="Ventas directas">Ventas directas</option>
          <option value="Maquila">Maquila</option>
          <option value="Distribuidor">Distribuidor (FM)</option>
          <option value="E-commerce">E-commerce</option>
          <option value="Otro">Otro</option>
        </select>
      </div>
      <div class="fg"><label>Concepto</label><input type="text" id="ing-concepto" placeholder="Ej: Pedido FM Abril"></div>
      <div class="fg"><label>Monto (COP)</label><input type="number" id="ing-monto" placeholder="0"></div>
      <div class="fg"><label>Referencia</label><input type="text" id="ing-ref" placeholder="Nro factura, pedido..."></div>
    </div>
    <button class="btn btn-green" onclick="guardarIngreso()">+ Registrar Ingreso</button>
    <div id="ing-msg" style="margin-top:10px;"></div>
  </div>
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <div class="section-title" style="margin:0;">Historial de Ingresos</div>
      <select id="ing-filtro-mes" onchange="loadIngresos()" style="padding:6px 12px;border:1px solid #E8E4DE;border-radius:6px;font-size:0.85em;">
        <option value="">Todos los meses</option>
      </select>
    </div>
    <table class="tbl">
      <thead><tr><th>Fecha</th><th>Empresa</th><th>Categoría</th><th>Concepto</th><th>Referencia</th><th style="text-align:right;">Monto</th></tr></thead>
      <tbody id="ing-tbody"><tr><td colspan="6" style="text-align:center;padding:20px;color:#999;">Cargando...</td></tr></tbody>
    </table>
    <div id="ing-total" style="text-align:right;font-weight:700;padding:12px 14px;font-size:1.05em;color:#2B7A78;"></div>
  </div>
</div>

<!-- ─── EGRESOS ─── -->
<div id="page-egresos" class="page">
  <div class="card">
    <div class="section-title">+ Registrar Egreso</div>
    <div class="form-grid">
      <div class="fg"><label>Fecha</label><input type="date" id="egr-fecha"></div>
      <div class="fg"><label>Empresa</label>
        <select id="egr-empresa">
          <option value="ESPAGIRIA">Espagiria</option>
          <option value="ANIMUS">ÁNIMUS Lab</option>
          <option value="HHA">HHA Group</option>
        </select>
      </div>
      <div class="fg"><label>Categoría</label>
        <select id="egr-cat">
          <option value="MPs">Materias Primas</option>
          <option value="MEE">Material Empaque/Envase</option>
          <option value="Nomina">Nómina</option>
          <option value="Arrendamiento">Arrendamiento</option>
          <option value="Servicios">Servicios públicos</option>
          <option value="Marketing">Marketing</option>
          <option value="Logistica">Logística</option>
          <option value="Regulatorio">Regulatorio / INVIMA</option>
          <option value="Otro">Otro</option>
        </select>
      </div>
      <div class="fg"><label>Concepto</label><input type="text" id="egr-concepto" placeholder="Ej: Compra MPs Abril"></div>
      <div class="fg"><label>Monto (COP)</label><input type="number" id="egr-monto" placeholder="0"></div>
      <div class="fg"><label>Referencia</label><input type="text" id="egr-ref" placeholder="Nro OC, factura..."></div>
    </div>
    <button class="btn btn-red" onclick="guardarEgreso()">+ Registrar Egreso</button>
    <div id="egr-msg" style="margin-top:10px;"></div>
  </div>
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <div class="section-title" style="margin:0;">Historial de Egresos</div>
      <select id="egr-filtro-mes" onchange="loadEgresos()" style="padding:6px 12px;border:1px solid #E8E4DE;border-radius:6px;font-size:0.85em;">
        <option value="">Todos los meses</option>
      </select>
    </div>
    <table class="tbl">
      <thead><tr><th>Fecha</th><th>Empresa</th><th>Categoría</th><th>Concepto</th><th>Referencia</th><th style="text-align:right;">Monto</th></tr></thead>
      <tbody id="egr-tbody"><tr><td colspan="6" style="text-align:center;padding:20px;color:#999;">Cargando...</td></tr></tbody>
    </table>
    <div id="egr-total" style="text-align:right;font-weight:700;padding:12px 14px;font-size:1.05em;color:#c0392b;"></div>
  </div>
</div>

<!-- ─── FLUJO MENSUAL ─── -->
<div id="page-flujo" class="page">
  <div class="card">
    <div class="section-title">🗓️ Flujo de Caja Mensual</div>
    <div style="overflow-x:auto;">
    <table class="tbl" id="flujo-tbl">
      <thead><tr>
        <th>Período</th>
        <th style="text-align:right;color:#2B7A78;">Ingresos</th>
        <th style="text-align:right;color:#c0392b;">Egresos</th>
        <th style="text-align:right;">Flujo Neto</th>
        <th style="text-align:right;">Acumulado</th>
        <th>Estado</th>
      </tr></thead>
      <tbody id="flujo-tbody"><tr><td colspan="6" style="text-align:center;padding:20px;color:#999;">Cargando...</td></tr></tbody>
    </table>
    </div>
  </div>
  <div class="chart-wrap">
    <div class="section-title">Flujo Neto Mensual</div>
    <canvas id="chart-flujo" height="180"></canvas>
  </div>
</div>

<!-- ─── SUPUESTOS ─── -->
<div id="page-config" class="page">
  <div class="card">
    <div class="section-title">⚙️ Supuestos y Configuración</div>
    <p style="font-size:0.88em;color:#9C8B7A;margin-bottom:20px;">Parámetros base del modelo financiero. Actualizar cuando cambien las condiciones del negocio.</p>
    <div id="config-list"></div>
    <button class="btn" onclick="guardarConfig()" style="margin-top:16px;">Guardar cambios</button>
    <div id="config-msg" style="margin-top:10px;"></div>
  </div>
  <div class="card">
    <div class="section-title">📤 Importar desde OCs (egresos automáticos)</div>
    <p style="font-size:0.88em;color:#9C8B7A;margin-bottom:16px;">Importa las órdenes de compra recibidas como egresos de MPs automáticamente.</p>
    <button class="btn btn-ghost" onclick="importarOCs()">📦 Importar OCs recibidas como egresos</button>
    <div id="import-msg" style="margin-top:10px;"></div>
  </div>
  <div class="card">
    <div class="section-title">💲 Precios Mayorista por SKU</div>
    <p style="font-size:0.88em;color:#9C8B7A;margin-bottom:16px;">Precio de venta mayorista en COP por unidad. Solo visible para administración — no aparece en el módulo de operarios.</p>
    <div id="precios-list"><p style="color:#9C8B7A;font-size:0.88em;">Cargando...</p></div>
    <div id="precios-msg" style="margin-top:10px;"></div>
  </div>
</div>

<!-- AR AGING -->
<div id="page-ar" class="page">
  <div class="card">
    <div class="section-title">📬 Cuentas por Cobrar — AR Aging</div>
    <p style="font-size:0.88em;color:#9C8B7A;margin-bottom:16px;">Pedidos activos con saldo pendiente, agrupados por antigüedad.</p>
    <div id="ar-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:20px;"></div>
    <div id="ar-table"></div>
  </div>
</div>

<!-- AP AGING -->
<div id="page-ap" class="page">
  <div class="card">
    <div class="section-title">📤 Cuentas por Pagar — AP Aging</div>
    <p style="font-size:0.88em;color:#9C8B7A;margin-bottom:16px;">Órdenes de compra autorizadas/recibidas sin registrar pago, agrupadas por antigüedad.</p>
    <div id="ap-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:20px;"></div>
    <div id="ap-table"></div>
  </div>
</div>

<!-- P&L -->
<div id="page-pnl" class="page">
  <div class="card">
    <div class="section-title">📊 P&amp;L — Estado de Resultados</div>
    <p style="font-size:0.88em;color:#9C8B7A;margin-bottom:16px;">Ingresos, egresos y margen operacional por empresa y consolidado. Actualización mensual.</p>
    <div id="pnl-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:20px;"></div>
    <div id="pnl-brands" style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px;"></div>
    <div class="section-title" style="font-size:0.9em;margin-bottom:8px;">📈 Histórico 6 meses</div>
    <canvas id="pnl-chart" height="100"></canvas>
  </div>
</div>

<!-- WORKING CAPITAL -->
<div id="page-wc" class="page">
  <div class="card">
    <div class="section-title">💼 Capital de Trabajo &amp; CCC</div>
    <p style="font-size:0.88em;color:#9C8B7A;margin-bottom:16px;">Working capital, ciclo de conversión de efectivo (CCC), burn rate y runway.</p>
    <div id="wc-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:20px;"></div>
    <div id="wc-ccc" style="margin-bottom:20px;"></div>
    <div id="wc-equation"></div>
  </div>
</div>

</div>

<script>
var _chartIngEgr=null, _chartFlujo=null;
var _config={};

function fmt(n){
  if(!n&&n!==0) return '—';
  var abs=Math.abs(n);
  if(abs>=1000000) return (n<0?'-':'')+'$'+(abs/1000000).toFixed(1)+'M';
  if(abs>=1000) return (n<0?'-':'')+'$'+(abs/1000).toFixed(0)+'K';
  return (n<0?'-':'')+'$'+abs.toLocaleString('es-CO');
}
function fmtFull(n){
  if(!n&&n!==0) return '—';
  return (n<0?'-':'')+'$'+Math.abs(n).toLocaleString('es-CO');
}

function goTab(id,el){
  document.querySelectorAll('.page').forEach(function(p){p.classList.remove('active');});
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});
  document.getElementById('page-'+id).classList.add('active');
  if(el)el.classList.add('active');
  if(id==='dashboard')loadDashboard();
  if(id==='ingresos')loadIngresos();
  if(id==='egresos')loadEgresos();
  if(id==='flujo')loadFlujo();
  if(id==='config'){loadConfig();loadPreciosMayorista();}
  if(id==='ar')loadARaging();
  if(id==='ap')loadAPaging();
  if(id==='pnl')loadPNL();
  if(id==='wc')loadWorkingCapital();
}

async function loadDashboard(){
  try{
    var d=await fetch('/api/financiero/kpis').then(function(r){return r.json();});
    var hoy=new Date();
    document.getElementById('periodo-label').textContent=hoy.toLocaleString('es',{month:'long',year:'numeric'});
    document.getElementById('kpi-ing-mes').textContent=fmt(d.ing_mes||0);
    document.getElementById('kpi-ing-sub').textContent=(d.ing_count||0)+' transacciones';
    document.getElementById('kpi-egr-mes').textContent=fmt(d.egr_mes||0);
    document.getElementById('kpi-egr-sub').textContent=(d.egr_count||0)+' transacciones';
    var flujo=(d.ing_mes||0)-(d.egr_mes||0);
    var kflujo=document.getElementById('kpi-flujo-mes');
    kflujo.textContent=fmt(flujo);
    kflujo.style.color=flujo>=0?'#2B7A78':'#c0392b';
    document.getElementById('kpi-flujo-sub').textContent=flujo>=0?'Superávit':'Déficit';
    document.getElementById('kpi-caja').textContent=fmt(d.saldo_caja||0);
    var meta=parseFloat(_config.meta_caja_min||50000000);
    document.getElementById('kpi-caja-sub').textContent=(d.saldo_caja||0)>=meta?'✓ Por encima del mínimo':'⚠️ Bajo el mínimo ($'+fmt(meta)+')';
    // Desglose
    var des='<table style="width:100%;font-size:0.88em;">';
    if(d.desglose_ing&&d.desglose_ing.length){
      des+='<tr><td colspan="2" style="font-weight:700;color:#2B7A78;padding:6px 0;">INGRESOS</td></tr>';
      d.desglose_ing.forEach(function(r){des+='<tr><td style="color:#666;">'+r.categoria+'</td><td style="text-align:right;font-weight:600;">'+fmt(r.total)+'</td></tr>';});
    }
    if(d.desglose_egr&&d.desglose_egr.length){
      des+='<tr><td colspan="2" style="font-weight:700;color:#c0392b;padding:6px 0;padding-top:14px;">EGRESOS</td></tr>';
      d.desglose_egr.forEach(function(r){des+='<tr><td style="color:#666;">'+r.categoria+'</td><td style="text-align:right;font-weight:600;">'+fmt(r.total)+'</td></tr>';});
    }
    des+='</table>';
    document.getElementById('desglose-mes').innerHTML=des;
    // Alertas
    var alertas='';
    var metaCaja=parseFloat(_config.meta_caja_min||50000000);
    if((d.saldo_caja||0)<metaCaja) alertas+='<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:12px 16px;margin-bottom:8px;">🟡 Saldo de caja ($'+fmt(d.saldo_caja||0)+') está por debajo del mínimo ($'+fmt(metaCaja)+')</div>';
    if(flujo<0) alertas+='<div style="background:#fde8e8;border:1px solid #f5c6cb;border-radius:8px;padding:12px 16px;margin-bottom:8px;">🔴 Flujo neto negativo este mes: '+fmt(flujo)+'</div>';
    if(!alertas) alertas='<div style="color:#2B7A78;font-size:0.92em;padding:8px;">✅ Sin alertas críticas este mes.</div>';
    document.getElementById('alertas-fin').innerHTML=alertas;
    // Chart
    if(d.historico&&d.historico.length){
      var labels=d.historico.map(function(h){return h.periodo;});
      var ings=d.historico.map(function(h){return h.ingresos||0;});
      var egrs=d.historico.map(function(h){return h.egresos||0;});
      if(_chartIngEgr)_chartIngEgr.destroy();
      _chartIngEgr=new Chart(document.getElementById('chart-ing-egr'),{
        type:'bar',
        data:{labels:labels,datasets:[
          {label:'Ingresos',data:ings,backgroundColor:'rgba(43,122,120,0.7)',borderRadius:4},
          {label:'Egresos',data:egrs,backgroundColor:'rgba(192,57,43,0.7)',borderRadius:4}
        ]},
        options:{responsive:true,plugins:{legend:{position:'top'}},scales:{y:{ticks:{callback:function(v){return fmt(v);}}}}}
      });
    }
  }catch(e){console.error(e);}
}

async function loadIngresos(){
  var mes=document.getElementById('ing-filtro-mes')&&document.getElementById('ing-filtro-mes').value||'';
  try{
    var url='/api/financiero/ingresos'+(mes?'?mes='+mes:'');
    var d=await fetch(url).then(function(r){return r.json();});
    var rows=d.ingresos||[];
    // populate mes filter
    var sel=document.getElementById('ing-filtro-mes');
    if(sel&&sel.options.length<=1){
      var meses=[...new Set(rows.map(function(r){return(r.periodo||r.fecha||'').substring(0,7);}))].sort().reverse();
      meses.forEach(function(m){var o=document.createElement('option');o.value=m;o.textContent=m;sel.appendChild(o);});
    }
    var total=rows.reduce(function(s,r){return s+(r.monto||0);},0);
    var h='';
    if(!rows.length){h='<tr><td colspan="6" style="text-align:center;padding:20px;color:#999;">Sin ingresos registrados</td></tr>';}
    rows.forEach(function(r){
      h+='<tr><td>'+((r.fecha||'').substring(0,10))+'</td>';
      h+='<td><span class="badge-ing">'+r.empresa+'</span></td>';
      h+='<td>'+r.categoria+'</td>';
      h+='<td>'+r.concepto+'</td>';
      h+='<td style="color:#888;font-size:0.85em;">'+(r.referencia||'')+'</td>';
      h+='<td style="text-align:right;font-weight:700;color:#2B7A78;">'+fmtFull(r.monto)+'</td></tr>';
    });
    document.getElementById('ing-tbody').innerHTML=h;
    document.getElementById('ing-total').textContent='Total: '+fmtFull(total);
  }catch(e){console.error(e);}
}

async function loadEgresos(){
  var mes=document.getElementById('egr-filtro-mes')&&document.getElementById('egr-filtro-mes').value||'';
  try{
    var url='/api/financiero/egresos'+(mes?'?mes='+mes:'');
    var d=await fetch(url).then(function(r){return r.json();});
    var rows=d.egresos||[];
    var sel=document.getElementById('egr-filtro-mes');
    if(sel&&sel.options.length<=1){
      var meses=[...new Set(rows.map(function(r){return(r.periodo||r.fecha||'').substring(0,7);}))].sort().reverse();
      meses.forEach(function(m){var o=document.createElement('option');o.value=m;o.textContent=m;sel.appendChild(o);});
    }
    var total=rows.reduce(function(s,r){return s+(r.monto||0);},0);
    var h='';
    if(!rows.length){h='<tr><td colspan="6" style="text-align:center;padding:20px;color:#999;">Sin egresos registrados</td></tr>';}
    rows.forEach(function(r){
      h+='<tr><td>'+((r.fecha||'').substring(0,10))+'</td>';
      h+='<td><span class="badge-egr">'+r.empresa+'</span></td>';
      h+='<td>'+r.categoria+'</td>';
      h+='<td>'+r.concepto+'</td>';
      h+='<td style="color:#888;font-size:0.85em;">'+(r.referencia||'')+'</td>';
      h+='<td style="text-align:right;font-weight:700;color:#c0392b;">'+fmtFull(r.monto)+'</td></tr>';
    });
    document.getElementById('egr-tbody').innerHTML=h;
    document.getElementById('egr-total').textContent='Total egresos: '+fmtFull(total);
  }catch(e){console.error(e);}
}

async function loadFlujo(){
  try{
    var d=await fetch('/api/financiero/flujo-mensual').then(function(r){return r.json();});
    var meses=d.meses||[];
    var acum=0;
    var h='';
    if(!meses.length){h='<tr><td colspan="6" style="text-align:center;padding:20px;color:#999;">Sin datos de flujo</td></tr>';}
    meses.forEach(function(m){
      var flujo=(m.ingresos||0)-(m.egresos||0);
      acum+=flujo;
      var cls=flujo>=0?'flujo-pos':'flujo-neg';
      var acls=acum>=0?'flujo-pos':'flujo-neg';
      h+='<tr><td style="font-weight:600;">'+m.periodo+'</td>';
      h+='<td style="text-align:right;color:#2B7A78;font-weight:700;">'+fmtFull(m.ingresos||0)+'</td>';
      h+='<td style="text-align:right;color:#c0392b;font-weight:700;">'+fmtFull(m.egresos||0)+'</td>';
      h+='<td style="text-align:right;" class="'+cls+'">'+fmtFull(flujo)+'</td>';
      h+='<td style="text-align:right;" class="'+acls+'">'+fmtFull(acum)+'</td>';
      h+='<td><span style="background:'+(flujo>=0?'rgba(43,122,120,.1)':'rgba(192,57,43,.1)')+';color:'+(flujo>=0?'#2B7A78':'#c0392b')+';padding:3px 10px;border-radius:12px;font-size:0.75em;font-weight:700;">'+(flujo>=0?'Superávit':'Déficit')+'</span></td></tr>';
    });
    document.getElementById('flujo-tbody').innerHTML=h;
    // Chart
    if(meses.length){
      var labels=meses.map(function(m){return m.periodo;});
      var flujos=meses.map(function(m){return(m.ingresos||0)-(m.egresos||0);});
      var colors=flujos.map(function(f){return f>=0?'rgba(43,122,120,0.7)':'rgba(192,57,43,0.7)';});
      if(_chartFlujo)_chartFlujo.destroy();
      _chartFlujo=new Chart(document.getElementById('chart-flujo'),{
        type:'bar',data:{labels:labels,datasets:[{label:'Flujo Neto',data:flujos,backgroundColor:colors,borderRadius:4}]},
        options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{ticks:{callback:function(v){return fmt(v);}}}}}
      });
    }
  }catch(e){console.error(e);}
}

async function loadConfig(){
  try{
    var d=await fetch('/api/financiero/config').then(function(r){return r.json();});
    _config=d.config||{};
    var h='<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;">';
    Object.entries(_config).forEach(function([k,v]){
      h+='<div class="fg"><label>'+k.replace(/_/g,' ').toUpperCase()+'</label>';
      h+='<input type="text" id="cfg-'+k+'" value="'+v+'"></div>';
    });
    h+='</div>';
    document.getElementById('config-list').innerHTML=h;
  }catch(e){}
}

async function guardarConfig(){
  var updates={};
  document.querySelectorAll('[id^="cfg-"]').forEach(function(el){
    var key=el.id.replace('cfg-','');
    updates[key]=el.value;
  });
  var r=await fetch('/api/financiero/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(updates)});
  var d=await r.json();
  document.getElementById('config-msg').innerHTML=r.ok?'<span style="color:#2B7A78;">✓ '+d.message+'</span>':'<span style="color:red;">'+d.error+'</span>';
}

async function guardarIngreso(){
  var fecha=document.getElementById('ing-fecha').value;
  var empresa=document.getElementById('ing-empresa').value;
  var cat=document.getElementById('ing-cat').value;
  var concepto=document.getElementById('ing-concepto').value.trim();
  var monto=parseFloat(document.getElementById('ing-monto').value)||0;
  var ref=document.getElementById('ing-ref').value.trim();
  if(!concepto||!monto){alert('Concepto y monto son requeridos');return;}
  if(!fecha){fecha=new Date().toISOString().substring(0,10);}
  var r=await fetch('/api/financiero/ingresos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fecha:fecha,empresa:empresa,categoria:cat,concepto:concepto,monto:monto,referencia:ref})});
  var d=await r.json();
  document.getElementById('ing-msg').innerHTML=r.ok?'<span style="color:#2B7A78;">✓ '+d.message+'</span>':'<span style="color:red;">'+d.error+'</span>';
  if(r.ok){document.getElementById('ing-concepto').value='';document.getElementById('ing-monto').value='';document.getElementById('ing-ref').value='';loadIngresos();}
}

async function guardarEgreso(){
  var fecha=document.getElementById('egr-fecha').value;
  var empresa=document.getElementById('egr-empresa').value;
  var cat=document.getElementById('egr-cat').value;
  var concepto=document.getElementById('egr-concepto').value.trim();
  var monto=parseFloat(document.getElementById('egr-monto').value)||0;
  var ref=document.getElementById('egr-ref').value.trim();
  if(!concepto||!monto){alert('Concepto y monto son requeridos');return;}
  if(!fecha){fecha=new Date().toISOString().substring(0,10);}
  var r=await fetch('/api/financiero/egresos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fecha:fecha,empresa:empresa,categoria:cat,concepto:concepto,monto:monto,referencia:ref})});
  var d=await r.json();
  document.getElementById('egr-msg').innerHTML=r.ok?'<span style="color:#c0392b;">✓ '+d.message+'</span>':'<span style="color:red;">'+d.error+'</span>';
  if(r.ok){document.getElementById('egr-concepto').value='';document.getElementById('egr-monto').value='';document.getElementById('egr-ref').value='';loadEgresos();}
}

async function importarOCs(){
  var r=await fetch('/api/financiero/importar-ocs',{method:'POST'});
  var d=await r.json();
  document.getElementById('import-msg').innerHTML=r.ok?'<span style="color:#2B7A78;">✓ '+d.message+'</span>':'<span style="color:red;">'+(d.error||'Error')+'</span>';
  if(r.ok)loadEgresos();
}

async function loadPreciosMayorista(){
  try{
    var r=await fetch('/api/financiero/precios-mayorista');
    var data=await r.json();
    if(!data.length){document.getElementById('precios-list').innerHTML='<p style="color:#9C8B7A;font-size:0.88em;">Sin SKUs registrados.</p>';return;}
    var h='<table style="width:100%;border-collapse:collapse;font-size:0.88em;">';
    h+='<thead><tr style="border-bottom:2px solid #eee;">';
    h+='<th style="text-align:left;padding:8px 6px;color:#555;">SKU</th>';
    h+='<th style="text-align:left;padding:8px 6px;color:#555;">Producto</th>';
    h+='<th style="text-align:right;padding:8px 6px;color:#555;">Precio Mayorista (COP)</th>';
    h+='<th style="text-align:center;padding:8px 6px;color:#555;">Unidad</th>';
    h+='<th style="padding:8px 6px;"></th>';
    h+='</tr></thead><tbody>';
    data.forEach(function(s){
      h+='<tr style="border-bottom:1px solid #f0f0f0;">';
      h+='<td style="padding:8px 6px;font-family:monospace;color:#2B7A78;font-weight:700;">'+s.sku+'</td>';
      h+='<td style="padding:8px 6px;">'+s.descripcion+'</td>';
      h+='<td style="padding:8px 6px;text-align:right;"><input type="number" id="pm-'+s.sku+'" value="'+(s.precio_mayorista||0)+'" min="0" step="100" style="width:120px;padding:5px 8px;border:1px solid #dde;border-radius:6px;text-align:right;font-size:0.95em;"></td>';
      h+='<td style="padding:8px 6px;text-align:center;color:#888;">'+s.unidad+'</td>';
      h+='<td style="padding:8px 6px;"><button onclick="guardarPrecio(\''+s.sku+'\')" style="padding:5px 12px;background:#2B7A78;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:0.82em;font-weight:600;">Guardar</button></td>';
      h+='</tr>';
    });
    h+='</tbody></table>';
    document.getElementById('precios-list').innerHTML=h;
  }catch(e){document.getElementById('precios-list').innerHTML='<p style="color:red;">Error cargando precios.</p>';}
}

async function guardarPrecio(sku){
  var input=document.getElementById('pm-'+sku);
  if(!input)return;
  var precio=parseFloat(input.value)||0;
  var r=await fetch('/api/financiero/precios-mayorista/'+encodeURIComponent(sku),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({precio_mayorista:precio})});
  var d=await r.json();
  var msg=document.getElementById('precios-msg');
  msg.innerHTML=r.ok?'<span style="color:#2B7A78;">✓ '+d.message+'</span>':'<span style="color:red;">'+(d.error||'Error')+'</span>';
  setTimeout(function(){msg.innerHTML='';},2500);
}

// Init

var _ccLoteActual = null;

async function cargarCuarentena(){
  try{
    var r=await fetch('/api/lotes/cuarentena');
    var data=await r.json();
    var tb=document.getElementById('cuar-tbody');
    if(!data.length){tb.innerHTML='<tr><td colspan="10" style="text-align:center;color:#999;padding:20px;">Sin lotes pendientes de revision QC</td></tr>';return;}
    var h='';
    data.forEach(function(l){
      var esAdmin=(OPER_ACTUAL==='sebastian'||OPER_ACTUAL==='alejandro'||OPER_ACTUAL==='hernando');
      var estadoColor=l.estado_lote==='CUARENTENA'?'#e67e22':l.estado_lote==='CUARENTENA_EXTENDIDA'?'#c0392b':'#888';
      h+='<tr>';
      h+='<td style="font-family:monospace;font-size:0.85em;">'+l.codigo_mp+'</td>';
      h+='<td style="font-size:0.8em;color:#555;">'+(l.nombre_inci||'')+'</td>';
      h+='<td>'+l.nombre+'</td>';
      h+='<td style="font-family:monospace;font-weight:600;">'+l.lote+'</td>';
      h+='<td style="text-align:right;font-weight:600;">'+l.cantidad.toLocaleString()+'</td>';
      h+='<td style="font-size:0.85em;">'+(l.proveedor||'')+'</td>';
      h+='<td style="font-size:0.82em;">'+(l.numero_oc||'')+'</td>';
      h+='<td style="font-size:0.82em;">'+l.fecha.substring(0,10)+'</td>';
      h+='<td><span style="background:'+estadoColor+'20;color:'+estadoColor+';padding:2px 8px;border-radius:10px;font-size:0.8em;font-weight:700;">'+l.estado_lote.replace('_',' ')+'</span></td>';
      h+='<td>';
      if(esAdmin){
        h+='<button onclick="abrirCCModal('+JSON.stringify(l)+')" style="padding:5px 12px;background:#2B7A78;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:0.82em;font-weight:600;">Revisar CC</button>';
      }else{
        h+='<span style="color:#999;font-size:0.82em;">Solo CC/Admin</span>';
      }
      h+='</td></tr>';
    });
    tb.innerHTML=h;
  }catch(e){console.error(e);}
}

function abrirCCModal(lote){
  _ccLoteActual=lote;
  document.getElementById('cc-modal-lote').textContent=lote.lote+' -- '+lote.nombre;
  document.getElementById('cc-firmante').textContent=OPER_ACTUAL;
  document.getElementById('cc-lote-info').innerHTML=
    '<div><b>Codigo:</b> '+lote.codigo_mp+'</div>'+
    '<div><b>INCI:</b> '+(lote.nombre_inci||'--')+'</div>'+
    '<div><b>Cantidad:</b> '+Number(lote.cantidad).toLocaleString()+' g</div>'+
    '<div><b>Proveedor:</b> '+(lote.proveedor||'--')+'</div>'+
    '<div><b>Factura:</b> '+(lote.numero_factura||'--')+'</div>'+
    '<div><b>OC:</b> '+(lote.numero_oc||'--')+'</div>';
  ['cc-coa-ok','cc-lote-coincide','cc-coa-vigente','cc-ficha-ok','cc-muestra-ret'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.checked=false;
  });
  ['cc-solub-ok','cc-solub-fail','cc-aql-ok','cc-aql-fail','cc-aql-ext'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.checked=false;
  });
  document.getElementById('cc-aql-obs').value='';
  document.getElementById('cc-obs-final').value='';
  document.getElementById('cc-modal-msg').innerHTML='';
  document.getElementById('cc-modal').style.display='flex';
}

function cerrarCCModal(){
  document.getElementById('cc-modal').style.display='none';
  _ccLoteActual=null;
}

async function enviarRevisionCC(){
  if(!_ccLoteActual){return;}
  var coaOk=document.getElementById('cc-coa-ok').checked;
  var loteCoincide=document.getElementById('cc-lote-coincide').checked;
  var coaVigente=document.getElementById('cc-coa-vigente').checked;
  var fichaOk=document.getElementById('cc-ficha-ok').checked;
  var solubResult=document.querySelector('input[name="cc-solub"]:checked');
  var aqlResult=document.querySelector('input[name="cc-aql"]:checked');
  var aqlObs=document.getElementById('cc-aql-obs').value.trim();
  var muestraRet=document.getElementById('cc-muestra-ret').checked;
  var obsFinal=document.getElementById('cc-obs-final').value.trim();
  var msg=document.getElementById('cc-modal-msg');
  if(!solubResult){msg.innerHTML='<div class="alert-error">Selecciona resultado de solubilidad</div>';return;}
  if(!aqlResult){msg.innerHTML='<div class="alert-error">Selecciona resultado AQL</div>';return;}
  if((aqlResult.value==='NO_CONFORME'||aqlResult.value==='CUARENTENA_EXTENDIDA')&&!aqlObs){
    msg.innerHTML='<div class="alert-error">Las observaciones son obligatorias para este resultado</div>';return;
  }
  var payload={
    mov_id:_ccLoteActual.id,
    lote:_ccLoteActual.lote,
    codigo_mp:_ccLoteActual.codigo_mp,
    coa_ok:coaOk,
    lote_coincide:loteCoincide,
    coa_vigente:coaVigente,
    ficha_ok:fichaOk,
    solubilidad:solubResult.value,
    resultado_aql:aqlResult.value,
    observaciones_aql:aqlObs,
    muestra_retencion:muestraRet,
    observaciones:obsFinal,
    firmante:OPER_ACTUAL
  };
  try{
    document.getElementById('cc-submit-btn').disabled=true;
    document.getElementById('cc-submit-btn').textContent='Registrando...';
    var r=await fetch('/api/lotes/cc-review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    var res=await r.json();
    if(r.ok){
      msg.innerHTML='<div class="alert-success">'+res.message+'</div>';
      document.getElementById('cuar-msg').innerHTML='<div class="alert-success">Revision CC registrada -- '+res.estado+' -- Lote: '+payload.lote+'</div>';
      setTimeout(function(){cerrarCCModal();cargarCuarentena();},1800);
    }else{
      msg.innerHTML='<div class="alert-error">'+(res.error||'Error al registrar')+'</div>';
    }
  }catch(e){
    msg.innerHTML='<div class="alert-error">Error: '+e.message+'</div>';
  }finally{
    document.getElementById('cc-submit-btn').disabled=false;
    document.getElementById('cc-submit-btn').textContent='Firmar y Registrar';
  }
}

async function buscarTrazabilidad(){
  var lote=(document.getElementById('trz-lote').value||'').trim();
  if(!lote){alert('Ingresa un numero de lote');return;}
  try{
    var r=await fetch('/api/trazabilidad/'+encodeURIComponent(lote));
    var data=await r.json();
    if(!data.ingreso){
      document.getElementById('trz-msg').innerHTML='<div class="alert-error">Lote no encontrado: '+lote+'</div>';
      document.getElementById('trz-result').style.display='none';
      return;
    }
    document.getElementById('trz-msg').innerHTML='';
    document.getElementById('trz-result').style.display='block';
    var ing=data.ingreso;
    document.getElementById('trz-ingreso').innerHTML=
      '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;">'+
      '<div><b>Codigo:</b> '+ing.codigo_mp+'</div>'+
      '<div><b>Nombre:</b> '+ing.nombre+'</div>'+
      '<div><b>INCI:</b> '+(ing.nombre_inci||'—')+'</div>'+
      '<div><b>Cantidad:</b> '+Number(ing.cantidad_g).toLocaleString()+' g</div>'+
      '<div><b>Proveedor:</b> '+(ing.proveedor||'—')+'</div>'+
      '<div><b>Factura:</b> '+(ing.factura||'—')+'</div>'+
      '<div><b>OC:</b> '+(ing.orden_compra||'—')+'</div>'+
      '<div><b>Precio/kg:</b> '+(ing.precio_kg?'$'+Number(ing.precio_kg).toLocaleString('es-CO'):'—')+'</div>'+
      '<div><b>Fecha:</b> '+(ing.fecha?ing.fecha.substring(0,10):'—')+'</div>'+
      '</div>';
    document.getElementById('trz-nprod').textContent=data.total_producciones;
    var tb=document.getElementById('trz-prod-tbody');
    if(!data.producciones.length){
      tb.innerHTML='<tr><td colspan="4" style="text-align:center;color:#999;">Este lote no ha sido usado en produccion</td></tr>';
    } else {
      var h='';
      data.producciones.forEach(function(p){
        h+='<tr><td>'+p.producto+'</td><td>'+p.fecha.substring(0,10)+'</td><td>'+p.operador+'</td><td style="text-align:right;">'+Number(p.cantidad_g).toLocaleString()+'</td></tr>';
      });
      tb.innerHTML=h;
    }
  }catch(e){document.getElementById('trz-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}

var _conteoActivo = null;
var _conteoItems = [];

async function cargarEstanterias(){
  try{
    var r = await fetch('/api/conteo/estanterias');
    var data = await r.json();
    var sel = document.getElementById('cnt-est-sel');
    if(!sel) return;
    while(sel.options.length > 1) sel.remove(1);
    data.forEach(function(e){
      var opt = document.createElement('option');
      opt.value = e.estanteria;
      opt.textContent = e.estanteria + ' (' + e.total_mps + ' MPs, ' + (e.stock_total/1000).toFixed(1) + ' kg)';
      sel.appendChild(opt);
    });
  }catch(e){}
}

async function iniciarConteo(){
  var est = document.getElementById('cnt-est-sel').value;
  var resp = document.getElementById('cnt-responsable').value.trim() || OPER_ACTUAL;
  if(!est){alert('Selecciona una estanteria'); return;}
  try{
    var r = await fetch('/api/conteo/iniciar',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({estanteria:est,responsable:resp})});
    var res = await r.json();
    if(!r.ok){alert(res.error||'Error'); return;}
    _conteoActivo = {id: res.conteo_id, numero: res.numero, estanteria: est};
    document.getElementById('cnt-numero').textContent = res.numero;
    document.getElementById('cnt-est-label').textContent = est;
    document.getElementById('cnt-panel').style.display = 'block';
    await cargarItemsConteo(est);
  }catch(e){alert('Error: '+e.message);}
}

async function cargarItemsConteo(est){
  try{
    var r = await fetch('/api/conteo/materiales?estanteria='+encodeURIComponent(est));
    _conteoItems = await r.json();
    var causas = ['Error de conteo','Consumo no descargado','Ingreso no registrado','Error unidad de medida','Merma justificada','Traslado no registrado','Material no identificado','Otro'];
    var causaOpts = causas.map(function(c){return '<option>'+c+'</option>';}).join('');
    var h = '';
    _conteoItems.forEach(function(mp, i){
      h += '<tr id="cnt-row-'+i+'">';
      h += '<td style="font-family:monospace;font-size:0.82em;">'+mp.codigo_mp+'</td>';
      h += '<td style="font-size:0.78em;color:#555;">'+(mp.inci||'')+'</td>';
      h += '<td style="font-size:0.88em;">'+mp.nombre+'</td>';
      h += '<td style="text-align:right;font-weight:600;font-family:monospace;">'+Number(mp.stock_sistema).toLocaleString()+'</td>';
      h += '<td><input type="number" id="cnt-fis-'+i+'" min="0" step="0.1" oninput="calcDiff('+i+','+mp.stock_sistema+','+mp.precio_ref+')" style="width:120px;padding:6px;border:1px solid #dde;border-radius:6px;text-align:right;font-family:monospace;"></td>';
      h += '<td id="cnt-diff-'+i+'" style="text-align:right;font-family:monospace;font-weight:700;">--</td>';
      h += '<td id="cnt-pct-'+i+'" style="font-size:0.85em;">--</td>';
      h += '<td id="cnt-val-'+i+'" style="font-size:0.82em;color:#888;">--</td>';
      h += '<td><select id="cnt-causa-'+i+'" style="width:150px;padding:5px;border:1px solid #dde;border-radius:6px;font-size:0.8em;"><option value="">Sin diferencia</option>'+causaOpts+'</select></td>';
      h += '<td id="cnt-adj-'+i+'"></td>';
      h += '</tr>';
    });
    document.getElementById('cnt-tbody').innerHTML = h || '<tr><td colspan="10" style="text-align:center;color:#999;">Sin materiales en esta estanteria</td></tr>';
  }catch(e){console.error(e);}
}

function calcDiff(i, stockSis, precioRef){
  var fis = parseFloat(document.getElementById('cnt-fis-'+i).value);
  var diffEl = document.getElementById('cnt-diff-'+i);
  var pctEl = document.getElementById('cnt-pct-'+i);
  var valEl = document.getElementById('cnt-val-'+i);
  var row = document.getElementById('cnt-row-'+i);
  if(isNaN(fis)){diffEl.textContent='--';pctEl.textContent='--';valEl.textContent='--';return;}
  var diff = fis - stockSis;
  var pct = stockSis > 0 ? Math.abs(diff/stockSis)*100 : 0;
  var valDiff = Math.abs(diff/1000) * precioRef;
  diffEl.textContent = (diff >= 0 ? '+' : '') + diff.toLocaleString('es-CO',{maximumFractionDigits:1});
  diffEl.style.color = diff === 0 ? '#27ae60' : diff > 0 ? '#2980b9' : '#e74c3c';
  pctEl.textContent = pct.toFixed(1) + '%';
  if(pct > 5){
    pctEl.style.color = '#e74c3c';
    pctEl.textContent += ' ⚠ GERENCIA';
    row.style.background = '#fff5f5';
  } else {
    pctEl.style.color = pct > 2 ? '#e67e22' : '#27ae60';
    row.style.background = '';
  }
  valEl.textContent = valDiff > 0 ? '$'+valDiff.toLocaleString('es-CO',{maximumFractionDigits:0}) : '--';
}

async function guardarConteo(){
  if(!_conteoActivo){alert('Inicia un conteo primero'); return;}
  var items = [];
  _conteoItems.forEach(function(mp, i){
    var fisEl = document.getElementById('cnt-fis-'+i);
    if(!fisEl || fisEl.value === '') return;
    items.push({
      codigo_mp: mp.codigo_mp,
      nombre: mp.nombre,
      stock_sistema: mp.stock_sistema,
      stock_fisico: parseFloat(fisEl.value),
      precio_ref: mp.precio_ref,
      estanteria: mp.estanteria,
      causa_diferencia: document.getElementById('cnt-causa-'+i).value
    });
  });
  try{
    var r = await fetch('/api/conteo/'+_conteoActivo.id+'/guardar',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({items:items})});
    var res = await r.json();
    if(r.ok){
      var msg = 'Guardado. ';
      if(res.items_con_diferencia > 0) msg += res.items_con_diferencia+' item(s) con diferencias.';
      document.getElementById('cnt-resumen').style.display = 'block';
      document.getElementById('cnt-resumen').innerHTML = msg + ' Revisa los items marcados con ⚠ GERENCIA antes de cerrar.';
      await cargarHistorialConteos();
    }
  }catch(e){alert('Error: '+e.message);}
}

async function cerrarConteo(){
  if(!_conteoActivo) return;
  if(!confirm('Cerrar el conteo? Ya no se podran editar los conteos fisicos.')) return;
  try{
    var r = await fetch('/api/conteo/'+_conteoActivo.id+'/cerrar',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    var res = await r.json();
    document.getElementById('cnt-msg').innerHTML = '<div class="alert-success">'+res.message+'</div>';
    document.getElementById('cnt-panel').style.display = 'none';
    _conteoActivo = null;
    await cargarHistorialConteos();
    await cargarEstanterias();
  }catch(e){alert('Error: '+e.message);}
}

async function aplicarAjuste(itemId){
  if(!confirm('Aplicar ajuste de inventario? Se registrara un movimiento de correccion en el sistema.')) return;
  try{
    var r = await fetch('/api/conteo/0/ajustar',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({item_id:itemId})});
    var res = await r.json();
    if(r.ok){
      document.getElementById('cnt-msg').innerHTML = '<div class="alert-success">'+res.message+'</div>';
    }else{
      document.getElementById('cnt-msg').innerHTML = '<div class="alert-error">'+(res.error||'Error')+'</div>';
    }
  }catch(e){}
}

async function cargarHistorialConteos(){
  try{
    var r = await fetch('/api/conteo/historial');
    var data = await r.json();
    var tb = document.getElementById('cnt-hist-tbody');
    if(!data.length){tb.innerHTML='<tr><td colspan="8" style="text-align:center;color:#999;">Sin conteos</td></tr>';return;}
    var h = '';
    data.forEach(function(c){
      var estadoColor = c.estado === 'Cerrado' ? '#27ae60' : '#e67e22';
      h += '<tr>';
      h += '<td style="font-family:monospace;font-size:0.85em;">'+c.numero+'</td>';
      h += '<td>'+(c.estanteria||'')+'</td>';
      h += '<td style="font-size:0.82em;">'+(c.fecha_inicio?c.fecha_inicio.substring(0,10):'')+'</td>';
      h += '<td>'+(c.responsable||'')+'</td>';
      h += '<td><span style="color:'+estadoColor+';font-weight:700;">'+c.estado+'</span></td>';
      h += '<td style="text-align:center;">'+c.total_items+'</td>';
      h += '<td style="text-align:center;color:'+(c.items_diferencia>0?'#e74c3c':'#27ae60')+';">'+c.items_diferencia+'</td>';
      h += '<td style="text-align:center;">';
      if(c.items_gerencia > 0) h += '<span style="color:#e74c3c;font-weight:700;">'+c.items_gerencia+' ⚠</span>';
      else h += '<span style="color:#27ae60;">OK</span>';
      h += '</td></tr>';
    });
    tb.innerHTML = h;
  }catch(e){}
}
document.addEventListener('DOMContentLoaded',function(){
  var hoy=new Date().toISOString().substring(0,10);
  var ingFecha=document.getElementById('ing-fecha');if(ingFecha)ingFecha.value=hoy;
  var egrFecha=document.getElementById('egr-fecha');if(egrFecha)egrFecha.value=hoy;
  loadConfig().then(function(){loadDashboard();cargarOCsPendientes();});
});
</script>
</body>
</html>"""

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
<title>Compras — Espagiria</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#f5f4f2;color:#1C1917;font-size:14px;}
.topbar{background:#292524;color:#fff;padding:12px 20px;display:flex;align-items:center;gap:16px;}
.topbar h1{font-size:17px;font-weight:600;flex:1;}
.topbar a{color:#d6d3d1;text-decoration:none;font-size:13px;}
.topbar a:hover{color:#fff;}
.tab-nav{background:#fff;border-bottom:2px solid #e7e5e4;display:flex;gap:0;overflow-x:auto;white-space:nowrap;}
.tn{padding:11px 14px;font-size:13px;font-weight:500;color:#78716c;border:none;background:none;cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-2px;}
.tn:hover{color:#292524;background:#fafaf9;}
.tn.on{color:#292524;border-bottom-color:#292524;font-weight:700;}
.pane{display:none;padding:18px 20px;max-width:1400px;margin:0 auto;}
.pane.on{display:block;}
/* KPI */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:18px;}
.kpi{background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:14px;}
.kpi-l{font-size:10px;color:#78716c;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px;}
.kpi-v{font-size:22px;font-weight:800;color:#292524;}
.kpi-v.w{color:#d97706;} .kpi-v.r{color:#dc2626;} .kpi-v.g{color:#16a34a;}
.kpi-s{font-size:11px;color:#78716c;margin-top:2px;}
/* Cards */
.bar{background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:10px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:14px;}
.bar input,.bar select{padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;color:#292524;}
.bar input{min-width:190px;}
.pills{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px;}
.pill{padding:3px 11px;border-radius:12px;font-size:11px;font-weight:600;background:#f3f4f6;color:#374151;}
.pill.y{background:#fef3c7;color:#92400e;} .pill.b{background:#dbeafe;color:#1e40af;} .pill.g{background:#dcfce7;color:#166534;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px;}
.card{background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:14px;display:flex;flex-direction:column;gap:7px;}
.card:hover{border-color:#a8a29e;}
.ch{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;}
.cnum{font-weight:700;font-size:13px;} .cprov{font-size:12px;color:#57534e;margin-top:1px;}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;}
.b-bor{background:#f3f4f6;color:#6b7280;} .b-rev{background:#fef3c7;color:#92400e;}
.b-aut{background:#dbeafe;color:#1e40af;} .b-pag{background:#dcfce7;color:#166534;}
.b-rec{background:#f0fdf4;color:#14532d;border:1px solid #bbf7d0;}
.cmeta{font-size:11px;color:#78716c;display:flex;gap:10px;flex-wrap:wrap;}
.cval{font-size:15px;font-weight:800;color:#292524;}
.cobs{font-size:11px;color:#78716c;font-style:italic;}
.acts{display:flex;gap:7px;flex-wrap:wrap;margin-top:3px;}
.btn{padding:6px 13px;border-radius:6px;font-size:12px;font-weight:600;border:none;cursor:pointer;}
.bp{background:#292524;color:#fff;} .bp:hover{background:#44403c;}
.bg{background:#16a34a;color:#fff;} .bg:hover{background:#15803d;}
.bw{background:#d97706;color:#fff;} .bw:hover{background:#b45309;}
.bi{background:#2563eb;color:#fff;} .bi:hover{background:#1d4ed8;}
.bo{background:#fff;color:#292524;border:1px solid #d6d3d1;} .bo:hover{background:#f5f4f2;}
.bs{padding:4px 10px;font-size:11px;}
.empty{text-align:center;padding:36px;color:#78716c;font-size:13px;}
.err{text-align:center;padding:20px;color:#dc2626;font-size:13px;}
/* Prov */
.pg{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:12px;}
.pc{background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:14px;}
.pn{font-weight:700;font-size:14px;margin-bottom:3px;}
.pnit{font-size:11px;color:#78716c;margin-bottom:8px;}
.pd{font-size:12px;color:#57534e;display:flex;flex-direction:column;gap:2px;}
/* Queue */
.queue-row{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:18px;}
@media(max-width:700px){.queue-row{grid-template-columns:1fr;}}
.qbox{background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:14px;}
.qtit{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#78716c;margin-bottom:10px;}
/* Modal */
.ov{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:900;display:none;align-items:center;justify-content:center;padding:16px;}
.ov.on{display:flex;}
.mdl{background:#fff;border-radius:10px;width:100%;max-width:560px;max-height:92vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.3);}
.mdl-lg{max-width:700px;}
.mh{padding:16px 20px;border-bottom:1px solid #e7e5e4;display:flex;align-items:center;justify-content:space-between;}
.mh h3{font-size:15px;font-weight:700;}
.mx{background:none;border:none;font-size:20px;cursor:pointer;color:#78716c;line-height:1;}
.mb{padding:18px 20px;display:flex;flex-direction:column;gap:12px;}
.mf{padding:12px 20px;border-top:1px solid #e7e5e4;display:flex;gap:8px;justify-content:flex-end;}
.fg label{display:block;font-size:11px;font-weight:600;color:#44403c;margin-bottom:4px;}
.fg input,.fg select,.fg textarea{width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;}
.fg textarea{min-height:65px;resize:vertical;}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
.ibox{background:#f9f8f7;border:1px solid #e7e5e4;border-radius:6px;padding:10px;font-size:12px;color:#57534e;display:grid;grid-template-columns:auto 1fr;gap:4px 10px;margin-top:4px;}
.ibox .lbl{color:#78716c;font-weight:600;white-space:nowrap;}
.itbl{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px;}
.itbl th{background:#f5f4f2;padding:5px 7px;text-align:left;font-size:11px;font-weight:700;color:#44403c;}
.itbl td{padding:5px 7px;border-bottom:1px solid #f3f4f6;}
.itbl input{width:100%;border:1px solid #e7e5e4;border-radius:4px;padding:3px 6px;font-size:12px;}
.total-row{text-align:right;margin-top:10px;font-size:15px;font-weight:700;}
.fab{position:fixed;bottom:22px;right:22px;background:#292524;color:#fff;border:none;width:50px;height:50px;border-radius:50%;font-size:22px;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.3);display:flex;align-items:center;justify-content:center;}
</style>
</head>
<body>
<div class="topbar">
  <h1>&#x1F6D2; Compras &mdash; Espagiria</h1>
  <span style="font-size:13px;color:#a8a29e;">&#x1F464; {usuario}</span>&nbsp;&nbsp;
  <a href="/">&#x2190; Hub</a>
</div>

<div class="tab-nav">
  <button class="tn on"  data-tab="dash">&#x1F4CA; Dashboard</button>
  <button class="tn"     data-tab="mp">&#x1F9EA; Mat. Primas</button>
  <button class="tn"     data-tab="mee">&#x1F4E6; Empaque</button>
  <button class="tn"     data-tab="svc">&#x1F527; Servicios</button>
  <button class="tn"     data-tab="adm">&#x1F4CB; Administrativo</button>
  <button class="tn"     data-tab="inf">&#x1F3DB; Infraestructura</button>
  <button class="tn"     data-tab="cc">&#x1F4B3; Cuentas Cobro</button>
  <button class="tn"     data-tab="prov">&#x1F3ED; Proveedores</button>
</div>

<!-- PANES -->
<div id="pane-dash" class="pane on">
  <div id="kpi-area" class="kpis"></div>
  <div class="queue-row">
    <div class="qbox"><div class="qtit">&#x23F3; Para Autorizar</div><div id="q-aut"></div></div>
    <div class="qbox"><div class="qtit">&#x1F4B8; Para Pagar</div><div id="q-pag"></div></div>
  </div>
</div>

<div id="pane-mp"  class="pane">
  <div class="bar">
    <input type="text" id="q-mp" placeholder="Buscar..." oninput="renderCat('mp')">
    <select id="s-mp" onchange="renderCat('mp')"><option value="">Todos los estados</option><option>Borrador</option><option>Revisada</option><option>Autorizada</option><option>Pagada</option><option>Recibida</option></select>
    <button class="btn bp" onclick="openNuevaOC('MP')">+ Nueva OC</button>
  </div>
  <div id="pills-mp" class="pills"></div>
  <div id="grid-mp" class="grid"></div>
</div>

<div id="pane-mee" class="pane">
  <div class="bar">
    <input type="text" id="q-mee" placeholder="Buscar..." oninput="renderCat('mee')">
    <select id="s-mee" onchange="renderCat('mee')"><option value="">Todos los estados</option><option>Borrador</option><option>Revisada</option><option>Autorizada</option><option>Pagada</option><option>Recibida</option></select>
    <button class="btn bp" onclick="openNuevaOC('MEE')">+ Nueva OC</button>
  </div>
  <div id="pills-mee" class="pills"></div>
  <div id="grid-mee" class="grid"></div>
</div>

<div id="pane-svc" class="pane">
  <div class="bar">
    <input type="text" id="q-svc" placeholder="Buscar..." oninput="renderCat('svc')">
    <select id="s-svc" onchange="renderCat('svc')"><option value="">Todos los estados</option><option>Borrador</option><option>Revisada</option><option>Autorizada</option><option>Pagada</option></select>
    <button class="btn bp" onclick="openNuevaOC('SVC')">+ Nueva OC</button>
  </div>
  <div id="pills-svc" class="pills"></div>
  <div id="grid-svc" class="grid"></div>
</div>

<div id="pane-adm" class="pane">
  <div class="bar">
    <input type="text" id="q-adm" placeholder="Buscar..." oninput="renderCat('adm')">
    <select id="s-adm" onchange="renderCat('adm')"><option value="">Todos los estados</option><option>Borrador</option><option>Revisada</option><option>Autorizada</option><option>Pagada</option></select>
    <button class="btn bp" onclick="openNuevaOC('ADM')">+ Nueva OC</button>
  </div>
  <div id="pills-adm" class="pills"></div>
  <div id="grid-adm" class="grid"></div>
</div>

<div id="pane-inf" class="pane">
  <div class="bar">
    <input type="text" id="q-inf" placeholder="Buscar..." oninput="renderCat('inf')">
    <select id="s-inf" onchange="renderCat('inf')"><option value="">Todos los estados</option><option>Borrador</option><option>Revisada</option><option>Autorizada</option><option>Pagada</option></select>
    <button class="btn bp" onclick="openNuevaOC('INF')">+ Nueva OC</button>
  </div>
  <div id="pills-inf" class="pills"></div>
  <div id="grid-inf" class="grid"></div>
</div>

<div id="pane-cc" class="pane">
  <div class="bar">
    <input type="text" id="q-cc" placeholder="Buscar..." oninput="renderCat('cc')">
    <select id="s-cc" onchange="renderCat('cc')"><option value="">Todos los estados</option><option>Borrador</option><option>Revisada</option><option>Autorizada</option><option>Pagada</option></select>
    <button class="btn bp" onclick="openNuevaOC('CC')">+ Nueva OC</button>
  </div>
  <div id="pills-cc" class="pills"></div>
  <div id="grid-cc" class="grid"></div>
</div>

<div id="pane-prov" class="pane">
  <div class="bar">
    <input type="text" id="q-prov" placeholder="Buscar proveedor..." oninput="renderProv()">
    <button class="btn bp" onclick="openModal('m-nprov')">+ Nuevo Proveedor</button>
  </div>
  <div id="prov-grid" class="pg"><div class="empty">Cargando...</div></div>
</div>

<!-- MODAL: Nueva OC -->
<div id="m-noc" class="ov">
<div class="mdl mdl-lg">
  <div class="mh"><h3>&#x1F4DD; Nueva Orden de Compra</h3><button class="mx" onclick="closeModal('m-noc')">&times;</button></div>
  <div class="mb">
    <div class="g2">
      <div class="fg"><label>Categoria</label>
        <select id="noc-cat">
          <option value="MP">Materias Primas</option><option value="MEE">Empaque &amp; Envase</option>
          <option value="SVC">Servicios</option><option value="ADM">Administrativo</option>
          <option value="INF">Infraestructura</option><option value="CC">Cuenta de Cobro</option>
        </select>
      </div>
      <div class="fg"><label>Fecha entrega est.</label><input type="date" id="noc-fent"></div>
    </div>
    <div class="fg">
      <label>Proveedor</label>
      <select id="noc-prov" onchange="fillProv('noc-prov','noc-ibox')"><option value="">-- Seleccionar --</option></select>
      <div id="noc-ibox" class="ibox" style="display:none"></div>
    </div>
    <div class="fg"><label>Concepto / Observaciones</label><textarea id="noc-obs" placeholder="Descripcion del pedido..."></textarea></div>
    <div>
      <label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:6px;">Items del pedido</label>
      <table class="itbl"><thead><tr><th>Codigo</th><th>Descripcion</th><th>Cantidad</th><th>Precio U.</th><th>Subtotal</th><th></th></tr></thead>
      <tbody id="noc-tbody"></tbody></table>
      <button class="btn bo bs" style="margin-top:8px;" onclick="addRow()">+ Item</button>
    </div>
    <div class="total-row">Total: <span id="noc-tot">$0</span></div>
  </div>
  <div class="mf">
    <button class="btn bo" onclick="closeModal('m-noc')">Cancelar</button>
    <button class="btn bp" onclick="crearOC()">Crear OC</button>
  </div>
</div>
</div>

<!-- MODAL: Revisar y Asignar -->
<div id="m-rev" class="ov">
<div class="mdl">
  <div class="mh"><h3>&#x270F; Revisar &amp; Asignar</h3><button class="mx" onclick="closeModal('m-rev')">&times;</button></div>
  <div class="mb">
    <div id="rev-info" style="background:#f9f8f7;border:1px solid #e7e5e4;border-radius:6px;padding:10px;font-size:13px;"></div>
    <div class="fg">
      <label>Proveedor / Beneficiario</label>
      <select id="rev-prov" onchange="fillProv('rev-prov','rev-ibox')"><option value="">-- Seleccionar --</option></select>
      <div id="rev-ibox" class="ibox" style="display:none"></div>
    </div>
    <div class="g2">
      <div class="fg"><label>Valor Total ($)</label><input type="number" id="rev-val" min="0" step="0.01" placeholder="0"></div>
      <div class="fg"><label>Fecha entrega</label><input type="date" id="rev-fent"></div>
    </div>
    <div class="fg"><label>Observaciones</label><textarea id="rev-obs" placeholder="Notas de revision..."></textarea></div>
    <input type="hidden" id="rev-num">
  </div>
  <div class="mf">
    <button class="btn bo" onclick="closeModal('m-rev')">Cancelar</button>
    <button class="btn bw" onclick="confirmarRev()">Marcar Revisada</button>
  </div>
</div>
</div>

<!-- MODAL: Registrar Pago -->
<div id="m-pago" class="ov">
<div class="mdl">
  <div class="mh"><h3>&#x1F4B8; Registrar Pago</h3><button class="mx" onclick="closeModal('m-pago')">&times;</button></div>
  <div class="mb">
    <div id="pago-info" style="background:#f9f8f7;border:1px solid #e7e5e4;border-radius:6px;padding:10px;font-size:13px;"></div>
    <div class="g2">
      <div class="fg"><label>Monto Pagado ($)</label><input type="number" id="pago-monto" min="0" step="0.01" placeholder="0"></div>
      <div class="fg"><label>Medio de Pago</label>
        <select id="pago-medio"><option>Transferencia</option><option>Efectivo</option><option>Cheque</option><option>PSE</option><option>Nequi</option></select>
      </div>
    </div>
    <div class="fg"><label>Comprobante / Referencia</label><textarea id="pago-obs" rows="2" placeholder="No. transaccion, referencia..."></textarea></div>
    <input type="hidden" id="pago-num">
  </div>
  <div class="mf">
    <button class="btn bo" onclick="closeModal('m-pago')">Cancelar</button>
    <button class="btn bg" onclick="confirmarPago()">Registrar Pago</button>
  </div>
</div>
</div>

<!-- MODAL: Nuevo Proveedor -->
<div id="m-nprov" class="ov">
<div class="mdl mdl-lg">
  <div class="mh"><h3>&#x1F3ED; Nuevo Proveedor</h3><button class="mx" onclick="closeModal('m-nprov')">&times;</button></div>
  <div class="mb">
    <div class="g2">
      <div class="fg"><label>Nombre / Razon Social *</label><input id="np-nom" placeholder="EMPRESA SAS"></div>
      <div class="fg"><label>NIT / CC</label><input id="np-nit" placeholder="800.000.000-0"></div>
    </div>
    <div class="g2">
      <div class="fg"><label>Categoria</label><select id="np-cat"><option value="MP">Mat. Primas</option><option value="MEE">Empaque</option><option value="Servicios">Servicios</option><option value="General">General</option></select></div>
      <div class="fg"><label>Condiciones de Pago</label><select id="np-cond"><option>Contado</option><option>15 dias</option><option>30 dias</option><option>45 dias</option><option>60 dias</option></select></div>
    </div>
    <div class="g2">
      <div class="fg"><label>Contacto</label><input id="np-ctc" placeholder="Nombre representante"></div>
      <div class="fg"><label>Telefono</label><input id="np-tel" placeholder="300 000 0000"></div>
    </div>
    <div class="g2">
      <div class="fg"><label>Email</label><input id="np-email" type="email" placeholder="ventas@empresa.co"></div>
      <div class="fg"><label>Direccion</label><input id="np-dir" placeholder="Calle / Carrera..."></div>
    </div>
    <div class="g2">
      <div class="fg"><label>Banco</label><input id="np-banco" placeholder="Bancolombia..."></div>
      <div class="fg"><label>Tipo Cuenta</label><select id="np-tcta"><option>Ahorros</option><option>Corriente</option></select></div>
    </div>
    <div class="g2">
      <div class="fg"><label>No. Cuenta</label><input id="np-ncta" placeholder="000-000000-00"></div>
      <div class="fg"><label>Concepto habitual</label><input id="np-conc" placeholder="Compra materias primas..."></div>
    </div>
  </div>
  <div class="mf">
    <button class="btn bo" onclick="closeModal('m-nprov')">Cancelar</button>
    <button class="btn bp" onclick="crearProv()">Guardar</button>
  </div>
</div>
</div>

<button class="fab" id="fab-btn" onclick="openNuevaOC('')" title="Nueva OC">+</button>

<script>
// ─── Estado global ────────────────────────────────────────────────
var OCS = [];
var PROVS = [];
var ES_C = {es_contadora};
var ITMS = 0;

// Mapa categoria → grupos de strings
var CMAP = {
  mp:  ['MPs','MP','Materia Prima','Materias Primas'],
  mee: ['Envase','Insumos','MEE','Empaque'],
  svc: ['Servicios','Analisis','Acondicionamiento','SVC','Servicio'],
  adm: ['Admin','Nomina','ADM','Administrativo'],
  inf: ['Infraestructura','INF'],
  cc:  ['CC','Cuenta de Cobro','Cuentas de Cobro']
};
// Acepta tildes normalizando
function inGroup(cat, grp){
  var c = (cat||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
  var list = CMAP[grp]||[];
  for(var i=0;i<list.length;i++){
    if(list[i].normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase()===c) return true;
  }
  return false;
}

// ─── Utilidades ───────────────────────────────────────────────────
function fmt(n){ return '$'+parseFloat(n||0).toLocaleString('es-CO',{minimumFractionDigits:0,maximumFractionDigits:0}); }
function fdate(d){ if(!d) return '-'; var p=d.substring(0,10).split('-'); return p.length===3?p[2]+'/'+p[1]+'/'+p[0]:d.substring(0,10); }
function esc(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function badge(e){
  var m={'Borrador':'b-bor','Revisada':'b-rev','Autorizada':'b-aut','Pagada':'b-pag','Recibida':'b-rec'};
  return '<span class="badge '+(m[e]||'b-bor')+'">'+e+'</span>';
}

// ─── Tabs ─────────────────────────────────────────────────────────
document.querySelectorAll('.tn').forEach(function(btn){
  btn.addEventListener('click', function(){
    var tab = this.getAttribute('data-tab');
    document.querySelectorAll('.tn').forEach(function(b){ b.classList.remove('on'); });
    document.querySelectorAll('.pane').forEach(function(p){ p.classList.remove('on'); });
    this.classList.add('on');
    var pane = document.getElementById('pane-'+tab);
    if(pane) pane.classList.add('on');
    if(tab==='dash') renderDash();
    else if(tab==='prov') renderProv();
    else renderCat(tab);
    var fab = document.getElementById('fab-btn');
    if(tab==='prov'){ fab.style.display='none'; }
    else{ fab.style.display='flex'; fab.onclick=function(){ openNuevaOC(tab==='dash'?'':tab.toUpperCase()); }; }
  });
});

// ─── Carga de datos ───────────────────────────────────────────────
async function loadData(){
  try{
    var r = await fetch('/api/ordenes-compra');
    if(!r.ok) throw new Error('OC API '+r.status);
    var d = await r.json();
    OCS = d.ordenes||[];
  }catch(e){ console.error('OC load error:',e); OCS=[]; }
  try{
    var r2 = await fetch('/api/proveedores-compras');
    if(!r2.ok) throw new Error('Prov API '+r2.status);
    var d2 = await r2.json();
    PROVS = d2.proveedores||[];
  }catch(e){ console.error('Prov load error:',e); PROVS=[]; }
  renderDash();
}

// ─── Dashboard ────────────────────────────────────────────────────
function renderDash(){
  var autList = OCS.filter(function(o){ return o.estado==='Revisada'; });
  var pagList = OCS.filter(function(o){ return o.estado==='Autorizada'; });
  var recList = OCS.filter(function(o){ return o.estado==='Pagada'; });
  var vAut = autList.reduce(function(s,o){ return s+parseFloat(o.valor_total||0); },0);
  var vPag = pagList.reduce(function(s,o){ return s+parseFloat(o.valor_total||0); },0);
  var mes = new Date().toISOString().substring(0,7);
  var pagMes = OCS.filter(function(o){ return o.estado==='Pagada'&&(o.fecha_pago||o.fecha||'').startsWith(mes); });
  var vMes = pagMes.reduce(function(s,o){ return s+parseFloat(o.valor_total||0); },0);
  document.getElementById('kpi-area').innerHTML =
    mkKpi('Por Autorizar', autList.length+' OCs', fmt(vAut), autList.length>0?'w':'')+
    mkKpi('Por Pagar', pagList.length+' OCs', fmt(vPag), pagList.length>0?'w':'')+
    mkKpi('Pagado este mes', pagMes.length+' OCs', fmt(vMes), 'g')+
    mkKpi('Pend. Recepcion', recList.length+' OCs', 'fisicos pagados', '');
  document.getElementById('q-aut').innerHTML = autList.length
    ? autList.map(function(o){ return miniCard(o); }).join('')
    : '<div class="empty">Sin OCs pendientes</div>';
  document.getElementById('q-pag').innerHTML = pagList.length
    ? pagList.map(function(o){ return miniCard(o); }).join('')
    : '<div class="empty">Sin OCs pendientes</div>';
}
function mkKpi(l,v,s,c){
  return '<div class="kpi"><div class="kpi-l">'+l+'</div><div class="kpi-v'+(c?' '+c:'')+'" >'+v+'</div><div class="kpi-s">'+s+'</div></div>';
}
function miniCard(o){
  var btns='';
  if(o.estado==='Revisada'&&!ES_C) btns+='<button class="btn bi bs" data-act="aut" data-oc="'+esc(o.numero_oc)+'">Autorizar</button>';
  if(o.estado==='Autorizada'&&!ES_C) btns+='<button class="btn bg bs" data-act="pago" data-oc="'+esc(o.numero_oc)+'" data-val="'+parseFloat(o.valor_total||0)+'" data-prov="'+esc(o.proveedor||'')+'">Pagar</button>';
  return '<div class="card" style="margin-bottom:8px;">'+
    '<div class="ch"><div><div class="cnum">'+esc(o.numero_oc)+'</div><div class="cprov">'+esc(o.proveedor||'-')+'</div></div>'+badge(o.estado)+'</div>'+
    '<div class="cval">'+fmt(o.valor_total)+'</div>'+
    '<div class="cmeta"><span>'+fdate(o.fecha)+'</span>'+(o.fecha_entrega_est?'<span>&#x23F0; '+fdate(o.fecha_entrega_est)+'</span>':'')+'</div>'+
    (btns?'<div class="acts">'+btns+'</div>':'')+'</div>';
}

// ─── Por categoria ────────────────────────────────────────────────
function renderCat(grp){
  var q=(document.getElementById('q-'+grp)||{value:''}).value.toLowerCase();
  var st=(document.getElementById('s-'+grp)||{value:''}).value;
  var list = OCS.filter(function(o){
    if(!inGroup(o.categoria,grp)) return false;
    if(st && o.estado!==st) return false;
    if(q && (o.numero_oc||'').toLowerCase().indexOf(q)<0 && (o.proveedor||'').toLowerCase().indexOf(q)<0 && (o.observaciones||'').toLowerCase().indexOf(q)<0) return false;
    return true;
  });
  var counts={total:list.length};
  ['Borrador','Revisada','Autorizada','Pagada','Recibida'].forEach(function(e){ counts[e]=list.filter(function(o){ return o.estado===e; }).length; });
  var vTotal=list.reduce(function(s,o){ return s+parseFloat(o.valor_total||0); },0);
  var pills='<span class="pill">'+list.length+' OCs</span>';
  if(counts.Borrador) pills+='<span class="pill">Borrador: '+counts.Borrador+'</span>';
  if(counts.Revisada) pills+='<span class="pill y">Revisada: '+counts.Revisada+'</span>';
  if(counts.Autorizada) pills+='<span class="pill b">Autorizada: '+counts.Autorizada+'</span>';
  if(counts.Pagada) pills+='<span class="pill g">Pagada: '+counts.Pagada+'</span>';
  pills+='<span class="pill" style="background:#e7e5e4;">'+fmt(vTotal)+'</span>';
  document.getElementById('pills-'+grp).innerHTML=pills;
  if(!list.length){
    document.getElementById('grid-'+grp).innerHTML='<div class="empty">No hay OCs en esta categoria</div>'; return;
  }
  document.getElementById('grid-'+grp).innerHTML=list.map(function(o){ return fullCard(o,grp); }).join('');
}
function fullCard(o,grp){
  var btns='';
  if(o.estado==='Borrador'&&ES_C) btns+='<button class="btn bw bs" data-act="rev" data-oc="'+esc(o.numero_oc)+'" data-prov="'+esc(o.proveedor||'')+'" data-val="'+parseFloat(o.valor_total||0)+'" data-obs="'+esc((o.observaciones||'').substring(0,80))+'">Revisar &amp; Asignar</button>';
  if(o.estado==='Revisada'&&!ES_C) btns+='<button class="btn bi bs" data-act="aut" data-oc="'+esc(o.numero_oc)+'">Autorizar</button>';
  if(o.estado==='Autorizada'&&!ES_C) btns+='<button class="btn bg bs" data-act="pago" data-oc="'+esc(o.numero_oc)+'" data-val="'+parseFloat(o.valor_total||0)+'" data-prov="'+esc(o.proveedor||'')+'">Registrar Pago</button>';
  if(o.estado==='Pagada'&&!ES_C&&(grp==='mp'||grp==='mee')) btns+='<button class="btn bo bs" data-act="rec" data-oc="'+esc(o.numero_oc)+'">Marcar Recibida</button>';
  return '<div class="card">'+
    '<div class="ch"><div><div class="cnum">'+esc(o.numero_oc)+'</div><div class="cprov">'+esc(o.proveedor||'-')+'</div></div>'+badge(o.estado)+'</div>'+
    '<div class="cmeta"><span>&#x1F4C5; '+fdate(o.fecha)+'</span>'+(o.fecha_entrega_est?'<span>&#x23F0; '+fdate(o.fecha_entrega_est)+'</span>':'')+'<span>'+o.num_items+' item(s)</span></div>'+
    (o.observaciones?'<div class="cobs">'+esc((o.observaciones||'').substring(0,90))+'</div>':'')+
    '<div class="cval">'+fmt(o.valor_total)+'</div>'+
    (btns?'<div class="acts">'+btns+'</div>':'')+'</div>';
}

// ─── Proveedores ──────────────────────────────────────────────────
function renderProv(){
  var q=(document.getElementById('q-prov')||{value:''}).value.toLowerCase();
  var list=PROVS.filter(function(p){ return !q||(p.nombre||'').toLowerCase().indexOf(q)>=0||(p.nit||'').toLowerCase().indexOf(q)>=0; });
  if(!list.length){ document.getElementById('prov-grid').innerHTML='<div class="empty">No hay proveedores</div>'; return; }
  document.getElementById('prov-grid').innerHTML=list.map(function(p){
    return '<div class="pc"><div class="pn">'+esc(p.nombre)+'</div><div class="pnit">NIT: '+(p.nit||'-')+'</div><div class="pd">'+
      (p.contacto?'<span>&#x1F464; '+esc(p.contacto)+'</span>':'')+
      (p.telefono?'<span>&#x1F4F1; '+esc(p.telefono)+'</span>':'')+
      (p.email?'<span>&#x1F4E7; '+esc(p.email)+'</span>':'')+
      (p.banco?'<span>&#x1F3E6; '+esc(p.banco)+' '+esc(p.tipo_cuenta||'')+'</span>':'')+
      (p.num_cuenta?'<span>&#x1F4B3; '+esc(p.num_cuenta)+'</span>':'')+
    '</div></div>';
  }).join('');
}

// ─── Proveedor autofill ────────────────────────────────────────────
function fillProvSelect(selId){
  var sel=document.getElementById(selId); if(!sel) return;
  var cur=sel.value;
  sel.innerHTML='<option value="">-- Seleccionar proveedor --</option>';
  PROVS.forEach(function(p){ var o=document.createElement('option'); o.value=p.nombre; o.textContent=p.nombre; sel.appendChild(o); });
  if(cur) sel.value=cur;
}
function fillProv(selId, boxId){
  var nombre=document.getElementById(selId).value;
  var box=document.getElementById(boxId);
  var p=PROVS.find(function(x){ return x.nombre===nombre; });
  if(!p||!nombre){ box.style.display='none'; return; }
  var rows=[['NIT',p.nit],['Tel',p.telefono],['Email',p.email],['Contacto',p.contacto],['Banco',p.banco],['Cuenta',(p.tipo_cuenta||'')+' '+(p.num_cuenta||'')],['Concepto',p.concepto_compra],['Direccion',p.direccion]];
  box.innerHTML=rows.filter(function(r){ return r[1]; }).map(function(r){ return '<span class="lbl">'+r[0]+'</span><span>'+esc(r[1])+'</span>'; }).join('');
  box.style.display='grid';
}

// ─── Modal helpers ─────────────────────────────────────────────────
function openModal(id){ document.getElementById(id).classList.add('on'); }
function closeModal(id){ document.getElementById(id).classList.remove('on'); }
document.querySelectorAll('.ov').forEach(function(ov){ ov.addEventListener('click',function(e){ if(e.target===ov) ov.classList.remove('on'); }); });

// ─── Nueva OC ─────────────────────────────────────────────────────
var _catMap={'mp':'MP','mee':'MEE','svc':'SVC','adm':'ADM','inf':'INF','cc':'CC'};
function openNuevaOC(catCode){
  var cat=_catMap[catCode]||catCode||'MP';
  document.getElementById('noc-cat').value=cat;
  document.getElementById('noc-fent').value='';
  document.getElementById('noc-obs').value='';
  document.getElementById('noc-ibox').style.display='none';
  document.getElementById('noc-tot').textContent='$0';
  document.getElementById('noc-tbody').innerHTML='';
  ITMS=0;
  fillProvSelect('noc-prov');
  document.getElementById('noc-prov').value='';
  addRow(); addRow();
  openModal('m-noc');
}
function addRow(){
  ITMS++;
  var n=ITMS;
  var tr=document.createElement('tr');
  tr.id='ir'+n;
  tr.innerHTML='<td><input id="ic'+n+'" placeholder="COD" style="width:65px"></td>'+
    '<td><input id="in'+n+'" placeholder="Descripcion" style="width:150px"></td>'+
    '<td><input id="iq'+n+'" type="number" value="1" min="0" oninput="calcTot()" style="width:55px"></td>'+
    '<td><input id="ip'+n+'" type="number" value="0" min="0" step="0.01" oninput="calcTot()" style="width:75px"></td>'+
    '<td id="is'+n+'" style="white-space:nowrap">$0</td>'+
    '<td><button class="btn bo" style="padding:2px 7px;font-size:11px;" onclick="rmRow('+n+')">x</button></td>';
  document.getElementById('noc-tbody').appendChild(tr);
}
function rmRow(n){var e=document.getElementById('ir'+n);if(e)e.remove();calcTot();}
function calcTot(){
  var tot=0;
  for(var i=1;i<=ITMS;i++){
    var q=document.getElementById('iq'+i),p=document.getElementById('ip'+i);
    if(!q||!p) continue;
    var s=parseFloat(q.value||0)*parseFloat(p.value||0);
    var el=document.getElementById('is'+i); if(el) el.textContent=fmt(s);
    tot+=s;
  }
  document.getElementById('noc-tot').textContent=fmt(tot);
}
async function crearOC(){
  var prov=document.getElementById('noc-prov').value;
  var cat=document.getElementById('noc-cat').value;
  var obs=document.getElementById('noc-obs').value;
  var fent=document.getElementById('noc-fent').value;
  if(!prov){ alert('Selecciona un proveedor'); return; }
  var items=[];
  for(var i=1;i<=ITMS;i++){
    var n=document.getElementById('in'+i);
    if(!n||(n.value||'').trim()==='') continue;
    items.push({codigo_mp:(document.getElementById('ic'+i)||{value:''}).value,nombre_mp:n.value.trim(),
      cantidad_g:parseFloat((document.getElementById('iq'+i)||{value:1}).value||1),
      precio_unitario:parseFloat((document.getElementById('ip'+i)||{value:0}).value||0)});
  }
  if(!items.length){ alert('Agrega al menos un item con descripcion'); return; }
  try{
    var r=await fetch('/api/ordenes-compra',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({proveedor:prov,categoria:cat,observaciones:obs,fecha_entrega_est:fent,items:items,creado_por:'{usuario}'})});
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    closeModal('m-noc');
    await loadData();
    renderCat(_catMap[Object.keys(_catMap).find(function(k){ return _catMap[k]===cat; })||'']||'mp');
    alert('Creada: '+d.numero_oc);
  }catch(e){ alert('Error de conexion: '+e); }
}

// ─── Revisar ──────────────────────────────────────────────────────
function openRev(num,prov,val,obs){
  document.getElementById('rev-num').value=num;
  document.getElementById('rev-info').innerHTML='<strong>'+num+'</strong><br><span style="color:#78716c;">'+esc(obs||'-')+'</span>';
  document.getElementById('rev-val').value=val||'';
  document.getElementById('rev-obs').value='';
  document.getElementById('rev-fent').value='';
  document.getElementById('rev-ibox').style.display='none';
  fillProvSelect('rev-prov');
  document.getElementById('rev-prov').value=prov;
  if(prov) fillProv('rev-prov','rev-ibox');
  openModal('m-rev');
}
async function confirmarRev(){
  var num=document.getElementById('rev-num').value;
  var prov=document.getElementById('rev-prov').value;
  var val=document.getElementById('rev-val').value;
  var obs=document.getElementById('rev-obs').value;
  var fent=document.getElementById('rev-fent').value;
  if(!prov){ alert('Selecciona proveedor'); return; }
  if(!val||parseFloat(val)<=0){ alert('Ingresa el valor total'); return; }
  try{
    var body={proveedor:prov,valor_total:parseFloat(val),observaciones:obs};
    if(fent) body.fecha_entrega_est=fent;
    var r=await fetch('/api/ordenes-compra/'+num+'/revisar',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    closeModal('m-rev');
    await loadData();
  }catch(e){ alert('Error: '+e); }
}

// ─── Autorizar ────────────────────────────────────────────────────
async function autorizarOC(num){
  if(!confirm('Autorizar OC '+num+'?')) return;
  try{
    var r=await fetch('/api/ordenes-compra/'+num+'/autorizar',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    await loadData();
    renderDash();
  }catch(e){ alert('Error: '+e); }
}

// ─── Pagar ────────────────────────────────────────────────────────
function openPago(num,val,prov){
  document.getElementById('pago-num').value=num;
  document.getElementById('pago-monto').value=val||'';
  document.getElementById('pago-obs').value='';
  document.getElementById('pago-info').innerHTML='<strong>'+num+'</strong> &mdash; '+esc(prov)+'<br>Valor autorizado: <strong>'+fmt(val)+'</strong>';
  openModal('m-pago');
}
async function confirmarPago(){
  var num=document.getElementById('pago-num').value;
  var monto=document.getElementById('pago-monto').value;
  var medio=document.getElementById('pago-medio').value;
  var obs=document.getElementById('pago-obs').value;
  if(!monto||parseFloat(monto)<=0){ alert('Ingresa el monto'); return; }
  try{
    var r=await fetch('/api/ordenes-compra/'+num+'/pagar',{method:'PATCH',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({monto:parseFloat(monto),medio:medio,observaciones:obs})});
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    closeModal('m-pago');
    await loadData();
    renderDash();
  }catch(e){ alert('Error: '+e); }
}

// ─── Recibir ──────────────────────────────────────────────────────
async function marcarRecibida(num){
  if(!confirm('Marcar '+num+' como Recibida?')) return;
  try{
    var r=await fetch('/api/ordenes-compra/'+num+'/recibir',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    await loadData();
  }catch(e){ alert('Error: '+e); }
}

// ─── Nuevo proveedor ──────────────────────────────────────────────
async function crearProv(){
  var nom=document.getElementById('np-nom').value.trim();
  if(!nom){ alert('Nombre requerido'); return; }
  var body={nombre:nom,nit:document.getElementById('np-nit').value,
    categoria:document.getElementById('np-cat').value,condiciones_pago:document.getElementById('np-cond').value,
    contacto:document.getElementById('np-ctc').value,telefono:document.getElementById('np-tel').value,
    email:document.getElementById('np-email').value,direccion:document.getElementById('np-dir').value,
    banco:document.getElementById('np-banco').value,tipo_cuenta:document.getElementById('np-tcta').value,
    num_cuenta:document.getElementById('np-ncta').value,concepto_compra:document.getElementById('np-conc').value};
  try{
    var r=await fetch('/api/proveedores-compras',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    closeModal('m-nprov');
    await loadData();
    renderProv();
    alert('Proveedor creado: '+nom);
  }catch(e){ alert('Error: '+e); }
}

// ─── Event delegation para botones de OC ────────────────────────
document.addEventListener('click',function(e){
  var btn=e.target.closest('[data-act]');
  if(!btn) return;
  var act=btn.getAttribute('data-act');
  var oc=btn.getAttribute('data-oc');
  if(act==='aut') autorizarOC(oc);
  else if(act==='pago') openPago(oc,parseFloat(btn.getAttribute('data-val')||0),btn.getAttribute('data-prov')||'');
  else if(act==='rev') openRev(oc,btn.getAttribute('data-prov')||'',parseFloat(btn.getAttribute('data-val')||0),btn.getAttribute('data-obs')||'');
  else if(act==='rec') marcarRecibida(oc);
});

// ─── Init ─────────────────────────────────────────────────────────
loadData();
</script>
</body>
</html>"""

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
              <th>% Cumpl.</th>
              <th>Estado</th>
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
      <button class="tab-btn" id="tab-btn-recibidas" onclick="showTab('recibidas')">
        Recibidas <span class="cnt-badge" id="cnt-recibidas">0</span>
      </button>
      <button class="tab-btn" id="tab-btn-disc" onclick="showTab('disc')">
        Con Discrepancias <span class="cnt-badge" id="cnt-disc">0</span>
      </button>
    </div>
    <div id="tab-transito" class="tab-content active"></div>
    <div id="tab-recibidas" class="tab-content"></div>
    <div id="tab-disc" class="tab-content"></div>
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
      return x.estado === 'Autorizada' && (!x.fecha_recepcion || x.fecha_recepcion.length < 3);
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
      html += '<div class="oc-card" onclick="cargarOC(\'' + oc.numero_oc + '\')">'
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
        '<td><div class="progress-bar"><div class="progress-fill" id="prog-' + i + '" style="width:' + Math.min(pct,100) + '%"></div></div><div class="item-pct" id="pct-' + i + '">' + pct + '%</div></td>' +
        '<td><select id="est-' + i + '" onchange="updateRow(' + i + ')">' +
          '<option value="OK">OK - Conforme</option>' +
          '<option value="Incompleto">Incompleto</option>' +
          '<option value="Danado">Danado</option>' +
          '<option value="NoLlego">No llego</option>' +
        '</select></td>' +
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
  var row = document.getElementById('item-row-' + i);
  if (!cantEl) return;
  var sol = parseFloat(cantEl.dataset.sol) || 0;
  var rec = parseFloat(cantEl.value) || 0;
  var est = estEl ? estEl.value : 'OK';
  var pct = sol > 0 ? Math.round(rec / sol * 100) : 100;
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
    if (est !== 'OK' || cant < it.cantidad_g) discrepancias = true;
    items.push({codigo_mp: it.codigo_mp, cantidad_recibida: cant, estado: est, notas: nota});
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
      var discMsg = discrepancias ? ' ⚠ Con discrepancias.' : '';
      showMsg('submit-msg', 'Recepcion registrada. ' + (d.ingresos||0) + ' item(s) ingresado(s).' + discMsg, 'ok');
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
  ['transito','recibidas','disc'].forEach(function(t) {
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
    var recibidas = all.filter(function(x) { return x.fecha_recepcion && x.fecha_recepcion.length > 2; });
    var disc = all.filter(function(x) { return x.tiene_discrepancias; });
    document.getElementById('cnt-transito').textContent = transito.length;
    document.getElementById('cnt-recibidas').textContent = recibidas.length;
    document.getElementById('cnt-disc').textContent = disc.length;
    document.getElementById('tab-transito').innerHTML = buildTable(transito);
    document.getElementById('tab-recibidas').innerHTML = buildTable(recibidas);
    document.getElementById('tab-disc').innerHTML = buildTable(disc);
  } catch(e) { console.error(e); }
}

loadQueue();
loadMonitoreo();
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
      html += '<div class="ped-card" onclick="cargarPedido(\'' + p.numero + '\')" id="pc-' + p.numero + '">'
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
      h2 += '<tr><td><strong>' + p.numero + '</strong></td><td>' + (p.cliente||'—') + '</td><td>$' + Number(p.valor_total||0).toLocaleString() + '</td><td>' + p.estado + '</td><td>' + (p.fecha||'').slice(0,10) + '</td><td><button class="btn btn-primary btn-sm" onclick="cargarPedido(\'' + p.numero + '\')">Despachar</button></td></tr>';
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
  <a href="/" class="hha-back">&#8592; Inicio</a>
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
      <select id="f-cat" onchange="onCatChange()">
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
  <div id="items-section">
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
  </div><!-- /items-section -->
  <div id="pago-section" style="display:none">
    <div style="background:#f9f4ff;border:1px solid #d4b8e8;border-radius:8px;padding:16px;margin-bottom:12px">
      <div class="row2">
        <div class="field"><label>Nombre completo *</label>
          <input type="text" id="p-nombre" placeholder="Nombre del beneficiario"></div>
        <div class="field"><label>Red social / Handle</label>
          <input type="text" id="p-handle" placeholder="@usuario o N/A"></div>
      </div>
      <div class="row2">
        <div class="field"><label>Banco *</label>
          <select id="p-banco">
            <option value="">-- Seleccionar --</option>
            <option>Bancolombia</option>
            <option>Davivienda</option>
            <option>Banco de Bogota</option>
            <option>BBVA</option>
            <option>Nequi</option>
            <option>Daviplata</option>
            <option>Banco Popular</option>
            <option>AV Villas</option>
            <option>Colpatria</option>
            <option>Banco Caja Social</option>
            <option>Itau</option>
            <option>Otro</option>
          </select></div>
        <div class="field"><label>Tipo de cuenta</label>
          <select id="p-tipo-cta">
            <option value="Ahorros">Ahorros</option>
            <option value="Corriente">Corriente</option>
            <option value="Nequi/Daviplata">Nequi / Daviplata</option>
          </select></div>
      </div>
      <div class="row2">
        <div class="field"><label>Numero de cuenta / Celular *</label>
          <input type="text" id="p-numcta" placeholder="Numero de cuenta o celular"></div>
        <div class="field"><label>Cedula / NIT</label>
          <input type="text" id="p-cedula" placeholder="Documento del beneficiario"></div>
      </div>
      <div class="row2">
        <div class="field"><label>Valor a pagar (COP) *</label>
          <input type="number" id="p-valor" placeholder="0" min="0" step="1000"></div>
        <div class="field"><label>Descripcion del servicio *</label>
          <input type="text" id="p-desc" placeholder="Ej: Publicacion en Instagram, honorarios de..."></div>
      </div>
    </div>
    <div class="field"><label>Observaciones adicionales</label>
      <textarea id="p-obs" placeholder="Informacion adicional..."></textarea></div>
    <button class="btn-primary" onclick="enviarSolicitud()">Enviar Solicitud de Pago</button>
  </div><!-- /pago-section -->
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
var PAGO_CATS=['Influencer/Marketing Digital','Servicios Profesionales'];
var uniMap={
  'Materia Prima':['g','kg','ml','L','und'],
  'Material de Empaque':['und','rollo','caja','paquete','kg'],
  'EPP':['und','par','caja','kit'],
  'Aseo/Limpieza':['und','L','galon','kg','paquete'],
  'Papeleria/Oficina':['und','resma','paquete','caja','kit'],
  'Mantenimiento':['und','servicio','hora','kit'],
  'Repuestos':['und','caja','kit'],
  'Servicios Profesionales':['servicio','hora','mes'],
  'Software/Tecnologia':['und','mes','licencia','servicio'],
  'Dotacion':['und','par','kit'],
  'Reactivos/Laboratorio':['und','g','kg','ml','L','caja'],
  'Otro':['und','g','kg','ml','L','servicio','mes']
};
function getUnits(){var cat=document.getElementById('f-cat').value;return uniMap[cat]||['und','g','kg','ml','L','servicio','mes'];}
function buildUniSelect(id,sel){
  var units=getUnits(),opts='';
  units.forEach(function(u){opts+='<option'+(u===sel?' selected':'')+'>'+u+'</option>';});
  return '<select id="'+id+'">'+opts+'</select>';
}
function onCatChange(){
  var cat=document.getElementById('f-cat').value;
  var esPago=PAGO_CATS.indexOf(cat)>=0;
  document.getElementById('items-section').style.display=esPago?'none':'block';
  document.getElementById('pago-section').style.display=esPago?'block':'none';
  if(esPago)setTipo('Pago');else setTipo('Compra');
  if(!esPago){
    var rows=document.getElementById('items-body').children;
    for(var i=0;i<rows.length;i++){
      var rid=rows[i].id.replace('ir-','');
      var sel=document.getElementById('i'+rid+'-uni');
      if(sel){var cur=sel.value;sel.outerHTML=buildUniSelect('i'+rid+'-uni',cur);}
    }
  }
}
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
    'Pago':'Incluye servicios, honorarios y cuentas de cobro.'};
  document.getElementById('tipo-hint').textContent=hints[t]||'';
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
    '<td>'+buildUniSelect('i'+n+'-uni','')+'</td>'+
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
  var cat=document.getElementById('f-cat').value;
  var esPago=PAGO_CATS.indexOf(cat)>=0;
  var body,items=[];
  if(esPago){
    var nombre=document.getElementById('p-nombre').value.trim();
    var banco=document.getElementById('p-banco').value;
    var tipoCta=document.getElementById('p-tipo-cta').value;
    var numcta=document.getElementById('p-numcta').value.trim();
    var cedula=document.getElementById('p-cedula').value.trim();
    var valor=parseFloat(document.getElementById('p-valor').value)||0;
    var desc=document.getElementById('p-desc').value.trim();
    var obsExtra=document.getElementById('p-obs').value.trim();
    if(!nombre){alert('Ingresa el nombre del beneficiario');return;}
    if(!banco){alert('Selecciona el banco');return;}
    if(!numcta){alert('Ingresa el numero de cuenta o celular');return;}
    if(!valor){alert('Ingresa el valor a pagar');return;}
    if(!desc){alert('Ingresa una descripcion del servicio');return;}
    var obsStr='BENEFICIARIO: '+nombre+' | BANCO: '+banco+' '+tipoCta+' | CUENTA/CEL: '+numcta+(cedula?' | CED/NIT: '+cedula:'')+' | VALOR: $'+valor+' | SERVICIO: '+desc+(obsExtra?' | '+obsExtra:'');
    items=[{codigo_mp:'',nombre_mp:desc,cantidad_g:1,unidad:'servicio',valor_estimado:valor}];
    body={solicitante:sol,area:document.getElementById('f-area').value,empresa:empresa,tipo:'Pago',
      categoria:cat,urgencia:urg,observaciones:obsStr,items:items};
  } else {
    var rows=document.getElementById('items-body').children;
    for(var i=0;i<rows.length;i++){
      var rid=rows[i].id.replace('ir-','');
      var nom=document.getElementById('i'+rid+'-nom');
      if(nom&&nom.value.trim()){
        items.push({codigo_mp:(document.getElementById('i'+rid+'-cod')||{}).value||'',
          nombre_mp:nom.value.trim(),
          cantidad_g:parseFloat((document.getElementById('i'+rid+'-cant')||{}).value)||0,
          unidad:(document.getElementById('i'+rid+'-uni')||{}).value||'und',
          valor_estimado:parseFloat((document.getElementById('i'+rid+'-val')||{}).value)||0});
      }
    }
    if(!items.length){alert('Agrega al menos un item');return;}
    body={solicitante:sol,area:document.getElementById('f-area').value,empresa:empresa,tipo:tipo,
      categoria:cat,urgencia:urg,observaciones:document.getElementById('f-obs').value,items:items};
  }
  var btn=document.querySelector('#btn-enviar,#pago-section .btn-primary');
  if(btn){btn.disabled=true;btn.textContent='Enviando...';}
  try{
    var r=await fetch('/api/solicitudes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(d.numero){
      document.getElementById('confirm-num').textContent=d.numero;
      document.getElementById('form-card').style.display='none';
      document.getElementById('confirm-card').style.display='block';
      window.scrollTo(0,0);
    }else{alert('Error: '+(d.error||'Intenta de nuevo'));if(btn){btn.disabled=false;btn.textContent='Enviar Solicitud';}}
  }catch(e){alert('Error de conexion.');if(btn){btn.disabled=false;btn.textContent='Enviar Solicitud';}}
}
function nuevaSolicitud(){
  document.getElementById('form-card').style.display='block';
  document.getElementById('confirm-card').style.display='none';
  document.getElementById('f-sol').value='';
  document.getElementById('f-obs').value='';
  document.getElementById('p-nombre').value='';document.getElementById('p-handle').value='';
  document.getElementById('p-banco').value='';document.getElementById('p-numcta').value='';
  document.getElementById('p-cedula').value='';document.getElementById('p-valor').value='';
  document.getElementById('p-desc').value='';document.getElementById('p-obs').value='';
  document.getElementById('items-section').style.display='block';
  document.getElementById('pago-section').style.display='none';
  document.getElementById('f-cat').value='Materia Prima';
  document.getElementById('items-body').innerHTML=
    '<tr id="ir-0"><td><input type="text" placeholder="Cod." id="i0-cod"></td>'+
    '<td><input type="text" placeholder="Descripcion del item" id="i0-nom"></td>'+
    '<td><input type="number" placeholder="0" min="0" step="0.01" id="i0-cant"></td>'+
    '<td><select id="i0-uni"><option>g</option><option>kg</option><option>ml</option><option>L</option><option>und</option></select></td>'+
    '<td><input type="number" placeholder="0" min="0" step="1000" id="i0-val"></td>'+
    '<td><button class="btn-del" onclick="delItem(0)">&#10005;</button></td></tr>';
  itemCount=1;urg='Normal';setUrg('Normal',document.getElementById('ub-n'));
  var eb=document.getElementById('btn-enviar');if(eb){eb.disabled=false;eb.textContent='Enviar Solicitud';}
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
    <button class="tab-button" onclick="switchTab('cuarentena',this)">&#128274; Cuarentena</button>
    <button class="tab-button" onclick="switchTab('trazabilidad',this)">&#128269; Trazabilidad</button>
    <button class="tab-button" onclick="switchTab('conteo',this)">&#9989; Conteo Ciclico</button>
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
      <!-- OC Receipt + Costos + Cuarentena -->
      <div style="background:#fff8e1;border:1px solid #ffe082;border-radius:8px;padding:14px;margin:12px 0;">
        <div style="font-size:0.82em;font-weight:700;color:#e65100;margin-bottom:10px;">&#128230; VINCULAR A ORDEN DE COMPRA (opcional)</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
          <div class="form-group" style="margin:0;">
            <label>OC Pendiente</label>
            <select id="ing-oc-sel" onchange="autocompletarDesdeOC()" style="width:100%;">
              <option value="">-- Ingreso libre (sin OC) --</option>
            </select>
          </div>
          <div class="form-group" style="margin:0;">
            <label>N° Factura / Remision</label>
            <input type="text" id="ing-factura" placeholder="Ej: FAC-2026-1234">
          </div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;padding:10px;background:#fff3e0;border-radius:6px;border:1px solid #ffe0b2;">
        <input type="checkbox" id="ing-cuarentena" style="width:18px;height:18px;">
        <label for="ing-cuarentena" style="margin:0;cursor:pointer;font-weight:600;color:#e65100;">
          &#128274; Ingresar en CUARENTENA (pendiente aprobacion de calidad)
        </label>
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
        <div style="display:flex;gap:10px;margin-top:14px;flex-wrap:wrap;">
          <button onclick="registrarIngresoMEE()" style="background:#27ae60;">&#10003; Registrar Entrada MEE</button>
          <button onclick="generarRotuloMEE()" style="background:#2980b9;" id="btn-rotulo-mee">&#128209; Generar Rotulo + Codigo de Barras</button>
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
    <div style="background:#f0f9f0;border:1px solid #c3e6cb;border-radius:10px;padding:16px;margin-bottom:16px;">
      <label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-weight:700;color:#1b5e20;margin-bottom:0;">
        <input type="checkbox" id="prod-pt-check" onchange="togglePTFields()" style="width:18px;height:18px;">
        &#127981; Registrar unidades en Stock PT (Producto Terminado)
      </label>
      <div id="prod-pt-fields" style="display:none;margin-top:14px;display:none;">
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
          <div class="form-group" style="margin:0;">
            <label>SKU Producto</label>
            <input type="text" id="prod-sku-pt" placeholder="Ej: TRX-15" list="sku-sugerencias">
            <datalist id="sku-sugerencias">
              <option value="LBHA-30"><option value="TRX-15"><option value="NIAC-30">
              <option value="AZHC-30"><option value="SBHA-30"><option value="ECEN-30">
              <option value="EILU-30"><option value="CUREA-50"><option value="GELH-120">
            </datalist>
          </div>
          <div class="form-group" style="margin:0;">
            <label>Unidades producidas</label>
            <input type="number" id="prod-uds-pt" placeholder="Ej: 500" min="1">
          </div>
        </div>
      </div>
    </div>
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
    <div style="background:#e8f4fd;border:1px solid #bee5f8;border-radius:10px;padding:16px 20px;margin-bottom:18px;font-size:0.9em;color:#1a4a6b;">
      <strong>&#8505; Para que sirve este modulo:</strong> Clasifica todas las materias primas segun el valor de stock que representan (Pareto 80/20).
      <ul style="margin:8px 0 0 16px;padding:0;">
        <li><span style="background:#28a745;color:white;padding:1px 8px;border-radius:8px;font-weight:700;font-size:0.85em;">A</span> — Top 80% del stock total. Son las MPs mas criticas: maxima atencion en control y reorden.</li>
        <li><span style="background:#fd7e14;color:white;padding:1px 8px;border-radius:8px;font-weight:700;font-size:0.85em;">B</span> — 80-95% acumulado. Control intermedio.</li>
        <li><span style="background:#6c757d;color:white;padding:1px 8px;border-radius:8px;font-weight:700;font-size:0.85em;">C</span> — 95-100%. Son muchos items pero representan poco stock. Control basico.</li>
      </ul>
      <p style="margin:8px 0 0;"><strong>Uso practico:</strong> Las MPs clase A son las que nunca pueden quedarse sin stock. Usar para definir frecuencia de conteo fisico y prioridad de compra.</p>
    </div>
    <button onclick="loadABC()" style="padding:9px 22px;background:#667eea;color:#fff;border:none;border-radius:8px;font-weight:600;cursor:pointer;">&#128257; Actualizar Analisis</button>
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

  <div id="cuarentena" class="tab-content">
    <h2>&#128274; Control de Calidad — Recepcion de Materiales</h2>
    <div style="background:#e8f4fd;border:1px solid #bee5f8;border-radius:10px;padding:14px 20px;margin-bottom:16px;font-size:0.9em;color:#1a4a6b;">
      <strong>&#8505; Como funciona:</strong> Cuando recibes una MP en la pestana <strong>Ingreso MP</strong> y marcas el checkbox <strong>"Poner en cuarentena"</strong>, ese lote aparece aqui hasta que alguien con rol admin lo revise y apruebe o rechace conforme a COC-PRO-001. Mientras esta en cuarentena, el sistema NO permite usarlo en produccion.<br>
      <span style="color:#27ae60;font-weight:600;">&#10003; Si esta vacia: ningun lote esta pendiente de revision CC — es la situacion ideal.</span> Si recibes un lote con dudas de calidad, usa "Poner en cuarentena" al hacer el ingreso.
    </div>
    <div id="cuar-msg"></div>

    <!-- Tabla de lotes pendientes -->
    <table class="table" id="cuar-table">
      <thead><tr><th>Codigo</th><th>INCI</th><th>Nombre</th><th>Lote</th><th>Cant. (g)</th><th>Proveedor</th><th>OC</th><th>Fecha ingreso</th><th>Estado</th><th>Accion</th></tr></thead>
      <tbody id="cuar-tbody"><tr><td colspan="10" style="text-align:center;color:#999;">Sin lotes en cuarentena</td></tr></tbody>
    </table>

    <!-- Modal de revision CC -->
    <div id="cc-modal" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.55);z-index:9999;align-items:center;justify-content:center;">
      <div style="background:#fff;border-radius:14px;padding:32px;max-width:680px;width:95%;max-height:90vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,0.3);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
          <h3 style="color:#1C2B30;margin:0;">&#128203; Revision CC — <span id="cc-modal-lote"></span></h3>
          <button onclick="cerrarCCModal()" style="background:none;border:none;font-size:1.4em;cursor:pointer;color:#999;">&#x2715;</button>
        </div>
        <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:12px 16px;margin-bottom:20px;font-size:0.88em;">
          <strong>COC-PRO-001 v03</strong> — Todos los campos son obligatorios. La firma queda registrada con timestamp en el sistema y no puede modificarse.
        </div>

        <!-- Info del lote -->
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;background:#f8f9ff;border-radius:8px;padding:14px;margin-bottom:20px;font-size:0.88em;" id="cc-lote-info"></div>

        <!-- Checklist COC-PRO-001 -->
        <div style="margin-bottom:20px;">
          <h4 style="color:#2c3e50;margin-bottom:14px;font-size:0.95em;text-transform:uppercase;letter-spacing:1px;">6. Revision Documental</h4>
          <div style="display:flex;flex-direction:column;gap:10px;">
            <label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-size:0.9em;">
              <input type="checkbox" id="cc-coa-ok" style="width:18px;height:18px;">
              <span>COA del proveedor presente y correspondiente al lote recibido</span>
            </label>
            <label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-size:0.9em;">
              <input type="checkbox" id="cc-lote-coincide" style="width:18px;height:18px;">
              <span>Numero de lote del COA coincide exactamente con el lote del empaque</span>
            </label>
            <label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-size:0.9em;">
              <input type="checkbox" id="cc-coa-vigente" style="width:18px;height:18px;">
              <span>COA vigente — no vencido segun politica de re-analisis</span>
            </label>
            <label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-size:0.9em;">
              <input type="checkbox" id="cc-ficha-ok" style="width:18px;height:18px;">
              <span>Ficha tecnica del proveedor disponible en archivo CC</span>
            </label>
          </div>
        </div>

        <div style="margin-bottom:20px;">
          <h4 style="color:#2c3e50;margin-bottom:14px;font-size:0.95em;text-transform:uppercase;letter-spacing:1px;">9. Prueba de Solubilidad / Compatibilidad</h4>
          <div style="display:flex;gap:12px;">
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;padding:10px 18px;border:2px solid #dde;border-radius:8px;font-size:0.9em;font-weight:600;">
              <input type="radio" name="cc-solub" value="ACEPTACION" id="cc-solub-ok"> <span style="color:#27ae60;">ACEPTACION</span>
            </label>
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;padding:10px 18px;border:2px solid #dde;border-radius:8px;font-size:0.9em;font-weight:600;">
              <input type="radio" name="cc-solub" value="RECHAZO" id="cc-solub-fail"> <span style="color:#e74c3c;">RECHAZO</span>
            </label>
          </div>
        </div>

        <div style="margin-bottom:20px;">
          <h4 style="color:#2c3e50;margin-bottom:10px;font-size:0.95em;text-transform:uppercase;letter-spacing:1px;">Resultado AQL / Inspeccion organolectica</h4>
          <div style="display:flex;gap:12px;margin-bottom:12px;">
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;padding:10px 18px;border:2px solid #dde;border-radius:8px;font-size:0.9em;font-weight:600;">
              <input type="radio" name="cc-aql" value="CONFORME" id="cc-aql-ok"> <span style="color:#27ae60;">CONFORME</span>
            </label>
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;padding:10px 18px;border:2px solid #dde;border-radius:8px;font-size:0.9em;font-weight:600;">
              <input type="radio" name="cc-aql" value="NO_CONFORME" id="cc-aql-fail"> <span style="color:#e74c3c;">NO CONFORME</span>
            </label>
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;padding:10px 18px;border:2px solid #dde;border-radius:8px;font-size:0.9em;font-weight:600;">
              <input type="radio" name="cc-aql" value="CUARENTENA_EXTENDIDA" id="cc-aql-ext"> <span style="color:#e67e22;">CUARENTENA EXTENDIDA</span>
            </label>
          </div>
          <input type="text" id="cc-aql-obs" placeholder="Observaciones AQL (requerido si NO CONFORME o CUARENTENA EXTENDIDA)" style="width:100%;padding:10px;border:1px solid #dde;border-radius:8px;font-size:0.88em;">
        </div>

        <div style="margin-bottom:20px;">
          <h4 style="color:#2c3e50;margin-bottom:10px;font-size:0.95em;text-transform:uppercase;letter-spacing:1px;">Muestra de retencion tomada</h4>
          <label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-size:0.9em;">
            <input type="checkbox" id="cc-muestra-ret" style="width:18px;height:18px;">
            <span>Se tomo muestra de retencion y quedo identificada en laboratorio CC</span>
          </label>
        </div>

        <div style="margin-bottom:24px;">
          <label style="display:block;font-weight:600;margin-bottom:6px;font-size:0.9em;color:#555;">Observaciones adicionales</label>
          <textarea id="cc-obs-final" rows="3" placeholder="Condiciones especiales, hallazgos, acciones tomadas..." style="width:100%;padding:10px;border:1px solid #dde;border-radius:8px;font-size:0.88em;resize:vertical;"></textarea>
        </div>

        <!-- Decision final -->
        <div style="background:#f8f9ff;border-radius:8px;padding:14px;margin-bottom:20px;">
          <p style="font-size:0.88em;color:#555;margin-bottom:10px;"><strong>Decision final:</strong> Se determina automaticamente por el resultado AQL y solubilidad. Firmante: <strong id="cc-firmante"></strong></p>
          <div style="display:flex;gap:10px;justify-content:flex-end;">
            <button onclick="cerrarCCModal()" style="padding:10px 20px;background:#f0f0f0;color:#555;border:none;border-radius:8px;font-weight:600;cursor:pointer;">Cancelar</button>
            <button onclick="enviarRevisionCC()" id="cc-submit-btn" style="padding:10px 28px;background:#2B7A78;color:#fff;border:none;border-radius:8px;font-weight:700;cursor:pointer;font-size:0.95em;">Firmar y Registrar</button>
          </div>
        </div>
        <div id="cc-modal-msg"></div>
      </div>
    </div>
  </div>

  <div id="trazabilidad" class="tab-content">
    <h2>&#128269; Trazabilidad de Lotes</h2>
    <div style="background:#e8f4fd;border:1px solid #bee5f8;border-radius:10px;padding:14px 20px;margin-bottom:16px;font-size:0.9em;color:#1a4a6b;">
      <strong>&#8505; Herramienta de busqueda — no es un dashboard.</strong> Escribe el numero de lote de una MP (el codigo que aparece en la etiqueta de recepcion, ej: <code style="background:#d0eaf9;padding:1px 5px;border-radius:4px;">ESP260417ACE</code>) y el sistema muestra: quien recibio ese lote, de que proveedor, en que fecha, y en que producciones fue utilizado. Util para auditorias, reclamos de proveedor y trazabilidad BPM.
    </div>
    <div id="trz-msg"></div>
    <div style="background:#f8f9ff;border:1px solid #dde;border-radius:10px;padding:18px;margin-bottom:18px;display:flex;gap:12px;align-items:flex-end;">
      <div style="flex:1;">
        <label style="display:block;font-weight:600;margin-bottom:4px;color:#555;">Numero de Lote</label>
        <input type="text" id="trz-lote" placeholder="Ej: ESP260417ACE" style="width:100%;padding:10px;border:1px solid #dde;border-radius:8px;font-size:1em;">
      </div>
      <button onclick="buscarTrazabilidad()" style="padding:10px 24px;background:#667eea;color:#fff;border:none;border-radius:8px;font-weight:600;cursor:pointer;">Buscar</button>
    </div>
    <div id="trz-result" style="display:none;">
      <div style="background:#fff;border:1px solid #dde;border-radius:10px;padding:20px;margin-bottom:16px;">
        <h3 style="color:#2c3e50;margin:0 0 12px;">Ingreso del Lote</h3>
        <div id="trz-ingreso"></div>
      </div>
      <div style="background:#fff;border:1px solid #dde;border-radius:10px;padding:20px;">
        <h3 style="color:#2c3e50;margin:0 0 12px;">Uso en Produccion (<span id="trz-nprod">0</span> registros)</h3>
        <table class="table"><thead><tr><th>Producto</th><th>Fecha</th><th>Operador</th><th>Cantidad usada (g)</th></tr></thead>
        <tbody id="trz-prod-tbody"></tbody></table>
      </div>
    </div>
  </div>


  <div id="conteo" class="tab-content">
    <h2>&#9989; Conteo Fisico Ciclico — BDG-FOR-003</h2>
    <div style="background:#e8f4fd;border:1px solid #bee5f8;border-radius:10px;padding:14px 20px;margin-bottom:16px;font-size:0.9em;color:#1a4a6b;">
      <strong>&#8505; Para que sirve:</strong> Permite verificar fisicamente el stock de una estanteria contra lo que dice el sistema. El operario cuenta los gramos reales, los ingresa, y el sistema calcula diferencias. Si la diferencia es mayor al 5% del valor, requiere aprobacion de gerencia antes de ajustar. Queda registro firmado conforme a BDG-PRO-002.<br>
      <strong>Como usar:</strong> (1) El dropdown se llena automaticamente con las estanterias que tienen stock. Si aparece <em>"Sin estanteria"</em>, son MPs ingresadas sin asignar ubicacion fisica — igual puedes contarlas. (2) Selecciona estanteria + escribe tu nombre + clic <strong>Iniciar Conteo</strong>. (3) Ingresa el peso fisico de cada MP. (4) Guarda y cierra.
    </div>

    <!-- Selector de estanteria -->
    <div style="background:#f8f9ff;border:1px solid #dde;border-radius:10px;padding:18px;margin-bottom:20px;display:grid;grid-template-columns:1fr auto auto;gap:12px;align-items:end;">
      <div>
        <label style="display:block;font-weight:600;margin-bottom:4px;font-size:0.88em;color:#555;">Estanteria / Seccion a contar</label>
        <select id="cnt-est-sel" style="width:100%;padding:10px;border:1px solid #dde;border-radius:8px;">
          <option value="">-- Selecciona estanteria --</option>
        </select>
      </div>
      <div>
        <label style="display:block;font-weight:600;margin-bottom:4px;font-size:0.88em;color:#555;">Responsable</label>
        <input type="text" id="cnt-responsable" placeholder="Nombre operario" style="padding:10px;border:1px solid #dde;border-radius:8px;">
      </div>
      <button onclick="iniciarConteo()" style="padding:10px 22px;background:#2B7A78;color:#fff;border:none;border-radius:8px;font-weight:700;cursor:pointer;">Iniciar Conteo</button>
    </div>

    <!-- Panel de conteo activo -->
    <div id="cnt-panel" style="display:none;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
        <div>
          <span id="cnt-numero" style="font-family:monospace;font-weight:700;font-size:1.1em;color:#2B7A78;"></span>
          <span style="margin-left:12px;font-size:0.85em;color:#888;">Estanteria: <strong id="cnt-est-label"></strong></span>
        </div>
        <div style="display:flex;gap:10px;">
          <button onclick="guardarConteo()" style="padding:8px 18px;background:#27ae60;color:#fff;border:none;border-radius:7px;font-weight:600;cursor:pointer;">Guardar</button>
          <button onclick="cerrarConteo()" style="padding:8px 18px;background:#e67e22;color:#fff;border:none;border-radius:7px;font-weight:600;cursor:pointer;">Cerrar Conteo</button>
        </div>
      </div>

      <div id="cnt-resumen" style="display:none;background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:12px 16px;margin-bottom:14px;font-size:0.88em;"></div>

      <table class="table" id="cnt-tabla">
        <thead>
          <tr>
            <th>Codigo</th><th>INCI</th><th>Material</th>
            <th style="text-align:right;">Stock Sistema (g)</th>
            <th style="text-align:right;width:130px;">Stock Fisico (g)</th>
            <th style="text-align:right;">Diferencia</th>
            <th>%</th><th>Valor diff</th>
            <th style="width:160px;">Causa</th>
            <th>Ajuste</th>
          </tr>
        </thead>
        <tbody id="cnt-tbody"></tbody>
      </table>
    </div>

    <!-- Historial de conteos -->
    <div style="margin-top:28px;">
      <h3 style="color:#2c3e50;margin-bottom:12px;">Historial de Conteos</h3>
      <div id="cnt-msg"></div>
      <table class="table">
        <thead><tr><th>Numero</th><th>Estanteria</th><th>Fecha</th><th>Responsable</th><th>Estado</th><th>Total MPs</th><th>Con diferencia</th><th>Pend. Gerencia</th></tr></thead>
        <tbody id="cnt-hist-tbody"><tr><td colspan="8" style="text-align:center;color:#999;">Sin conteos registrados</td></tr></tbody>
      </table>
    </div>
  </div>

  </div>

</div>
<script>
var fData=[], allStock=[], _cat={}, _ultimoIng=null;
var _lotes=[], _lotesFull=[], _meeData=[], _prodPendiente=null;
var OPER_ACTUAL='';
// Auto-login por localStorage (recordar operador por dispositivo)
(function(){
  try{
    var saved=localStorage.getItem('espagiria_operador');
    if(saved&&saved.trim()){
      OPER_ACTUAL=saved.trim();
      document.addEventListener('DOMContentLoaded',function(){
        var modal=document.getElementById('modal-operador');
        if(modal) modal.style.display='none';
        var c=document.getElementById('oper-chip');
        if(c) c.innerHTML='<span onclick="cambiarOperador()" title="Cambiar operador" style="cursor:pointer;">&#128100; '+OPER_ACTUAL+' <span style="font-size:0.75em;opacity:0.7;">[cambiar]</span></span>';
        loadDashboardCompleto();loadFormulas();
      });
    }
  }catch(e){}
})();
var _meeData=[], _prodPendiente=null;
var _ajDat={};
function _eq(s){return (s||'').split("'").join('&#39;');}
function selOper(n){
  OPER_ACTUAL=n;
  try{localStorage.setItem('espagiria_operador',n);}catch(e){}
  document.getElementById('modal-operador').style.display='none';
  var c=document.getElementById('oper-chip');if(c)c.innerHTML='<span onclick="cambiarOperador()" title="Cambiar operador" style="cursor:pointer;">&#128100; '+n+' <span style="font-size:0.75em;opacity:0.7;">[cambiar]</span></span>';
  loadDashboardCompleto();loadFormulas();
}
function cambiarOperador(){
  try{localStorage.removeItem('espagiria_operador');}catch(e){}
  document.getElementById('oper-input').value=OPER_ACTUAL||'';
  document.getElementById('modal-operador').style.display='flex';
  setTimeout(function(){document.getElementById('oper-input').focus();},100);
}
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
  if(n==='cuarentena') cargarCuarentena();
  if(n==='ingreso') initIngreso();
  if(n==='abc') loadABC();
  if(n==='conteo'){ cargarEstanterias(); cargarHistorialConteos(); }
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
  items.forEach(function(i,idx){ var gi=_lotes.indexOf(i); if(gi<0)gi=idx;
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
    h+='<td style="text-align:center;"><button onclick="abrirAjusteIdx('+gi+')" style="padding:3px 9px;font-size:0.75em;background:#f0ad4e;color:#fff;border-radius:4px;">Ajustar</button></td>';
    h+='<td style="text-align:center;"><button onclick="verHistorialLote('+gi+')" style="padding:3px 9px;font-size:0.75em;background:#667eea;color:#fff;border-radius:4px;">Historial</button></td>';
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


async function cargarOCsPendientes(){
  try{
    var r=await fetch('/api/ordenes-compra/pendientes-recepcion');
    if(!r.ok) return;
    var ocs=await r.json();
    var sel=document.getElementById('ing-oc-sel');
    if(!sel) return;
    // clear existing options except first placeholder
    while(sel.options.length>1) sel.remove(1);
    (ocs||[]).forEach(function(oc){
      (oc.items||[]).forEach(function(item){
        var opt=document.createElement('option');
        opt.value=oc.numero_oc+'|'+item.codigo_mp;
        var kg=(item.cantidad_pendiente_g/1000).toFixed(2);
        opt.textContent=oc.numero_oc+' — '+item.nombre_mp+' ('+kg+' kg pendientes)';
        opt.dataset.codigo=item.codigo_mp;
        opt.dataset.nombre=item.nombre_mp;
        opt.dataset.inci=item.nombre_inci||'';
        opt.dataset.proveedor=oc.proveedor||'';
        opt.dataset.precio=item.precio_unitario||'';
        sel.appendChild(opt);
      });
    });
  }catch(e){}
}
function autocompletarDesdeOC(){
  var sel=document.getElementById('ing-oc-sel');
  if(!sel||sel.selectedIndex<1) return;
  var opt=sel.options[sel.selectedIndex];
  if(!opt.dataset.codigo) return;
  var cod=document.getElementById('ing-cod');
  var nom=document.getElementById('ing-nombre');
  var inci=document.getElementById('ing-inci');
  var prov=document.getElementById('ing-prov');
  var precio=document.getElementById('ing-precio-kg');
  if(cod) cod.value=opt.dataset.codigo;
  if(nom) nom.value=opt.dataset.nombre||'';
  if(inci) inci.value=opt.dataset.inci||'';
  if(prov) prov.value=opt.dataset.proveedor||'';
  if(precio && opt.dataset.precio) precio.value=opt.dataset.precio;
  // trigger lookup & valor total
  if(cod) cod.dispatchEvent(new Event('input'));
  calcularValorTotal();
}
function calcularValorTotal(){
  var cant=parseFloat(document.getElementById('ing-cant')?document.getElementById('ing-cant').value:0)||0;
  var precio=parseFloat(document.getElementById('ing-precio-kg')?document.getElementById('ing-precio-kg').value:0)||0;
  var vt=document.getElementById('ing-valor-total');
  if(!vt) return;
  var val=(cant/1000)*precio;
  vt.value=val>0?'$'+val.toLocaleString('es-CO',{maximumFractionDigits:0}):'';
}
async function registrarIngreso(){
  var cod=(document.getElementById('ing-cod').value||'').toUpperCase().trim();
  var cant=parseFloat(document.getElementById('ing-cant').value)||0;
  if(!cod){alert('Ingresa el codigo MP');return;}
  if(cant<=0){alert('Ingresa una cantidad valida');return;}
  var esNueva=document.getElementById('ing-nueva-mp-inline')&&document.getElementById('ing-nueva-mp-inline').style.display!=='none';
  var ocSel=document.getElementById('ing-oc-sel');
  var ocVal=ocSel&&ocSel.value?ocSel.value:'';
  var numOC=ocVal?ocVal.split('|')[0]:'';
  var enCuarentena=document.getElementById('ing-cuarentena')&&document.getElementById('ing-cuarentena').checked;
  var data={codigo_mp:cod,nombre_comercial:document.getElementById('ing-nombre').value||'',
    lote:document.getElementById('ing-lote').value||'',cantidad:cant,operador:OPER_ACTUAL,
    fecha_vencimiento:document.getElementById('ing-vence').value||'',
    estanteria:document.getElementById('ing-est').value||'',
    posicion:document.getElementById('ing-pos').value||'',
    proveedor:document.getElementById('ing-prov').value||'',
    observaciones:document.getElementById('ing-obs').value||'',
    precio_kg:parseFloat(document.getElementById('ing-precio-kg')?document.getElementById('ing-precio-kg').value:0)||0,
    numero_factura:document.getElementById('ing-factura')?document.getElementById('ing-factura').value.trim():'',
    numero_oc:numOC,
    cuarentena:enCuarentena};
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
      document.getElementById('ing-msg').innerHTML='<div class="alert-success">'+res.message+(enCuarentena?' — CUARENTENA activa':'')+'</div>';
      await cargarHistIngreso();
      await cargarOCsPendientes();
    } else {document.getElementById('ing-msg').innerHTML='<div class="alert-error">'+(res.error||'Error')+'</div>';}
  }catch(e){document.getElementById('ing-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}
function generarRotuloIngreso(){
  if(!_ultimoIng){alert('Registra un ingreso primero');return;}
  window.open('/rotulo-recepcion/'+encodeURIComponent(_ultimoIng.codigo)+'/'+encodeURIComponent(_ultimoIng.lote||'SL')+'/'+(parseFloat(_ultimoIng.cantidad)||0).toFixed(1),'_blank');
}
function limpiarIngreso(){
  ['ing-cod','ing-inci','ing-nombre','ing-tipo','ing-prov','ing-lote','ing-cant','ing-vence','ing-est','ing-pos','ing-obs','ing-factura','ing-precio-kg','ing-valor-total'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='';});
  var ocSel=document.getElementById('ing-oc-sel');if(ocSel)ocSel.selectedIndex=0;
  var cuar=document.getElementById('ing-cuarentena');if(cuar)cuar.checked=false;
  ocultarFormNuevaMP();
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
function togglePTFields(){
  var checked=document.getElementById('prod-pt-check').checked;
  var fields=document.getElementById('prod-pt-fields');
  if(fields) fields.style.display=checked?'block':'none';
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
  if(r.ok){
    _ultimoMEE={codigo:cod,cant:cant,ref:ref};
    document.getElementById('mee-ing-msg').innerHTML='<span style="color:green;">Entrada registrada. Stock: '+d.nuevo_stock+' und &nbsp;<button onclick="generarRotuloMEE()" style="background:#2980b9;color:white;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:0.85em;">&#128209; Rotulo</button></span>';
    document.getElementById('btn-rotulo-mee').disabled=false;
    loadHistMEE();loadMEE();
  }else{document.getElementById('mee-ing-msg').innerHTML='<span style="color:red;">'+(d.error||'Error')+'</span>';}
}
var _ultimoMEE=null;
function generarRotuloMEE(){
  if(!_ultimoMEE){alert('Primero registra una entrada MEE');return;}
  window.open('/rotulo-recepcion-mee/'+encodeURIComponent(_ultimoMEE.codigo)+'/'+(parseFloat(_ultimoMEE.cant)||0),'_blank');
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
    +'<td style="text-align:center;"><button class="btn btn-ghost btn-sm" onclick="abrirAjusteMEE(&quot;'+m.codigo+'&quot;,&quot;'+_eq(m.descripcion)+'&quot;,'+m.stock_actual+')">Ajustar</button></td>'
    +'<td style="text-align:center;"><button class="btn btn-ghost btn-sm" onclick="verHistorialMEE(&quot;'+m.codigo+'&quot;)">Hist.</button></td>'
    +'<td style="text-align:center;"><button class="btn btn-sm" style="background:#4A6741;font-size:11px;" onclick="solicitarCompraMEE(&quot;'+m.codigo+'&quot;,&quot;'+_eq(m.descripcion)+'&quot;,'+m.stock_actual+','+m.stock_minimo+')">Solicitar</button></td>'
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
  var nuevo=prompt('Ajuste de stock: '+cod+' — '+desc+'\\nStock actual: '+stock+' und\\nNuevo valor:');
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
  var cant=prompt('Solicitar compra para: '+desc+'\\nStock actual: '+stock+' und / Minimo: '+smin+' und\\nCantidad a solicitar:');
  if(!cant||isNaN(parseFloat(cant)))return;
  var data={
    solicitante:OPER_ACTUAL||'Sistema',
    area:'Produccion',empresa:'Espagiria',categoria:'Envase y Empaque',tipo:'Compra',
    urgencia:'Urgente',observaciones:'Solicitud automatica desde alerta MEE',
    items:[{codigo_mp:cod,nombre_mp:desc,cantidad_g:parseFloat(cant),unidad:'und',valor_estimado:0}]
  };
  var r=await fetch('/api/solicitudes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  var d=await r.json();
  if(r.ok)alert('Solicitud creada: '+d.numero+'\\nVisible en modulo Compras > Solicitudes');
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
    +'<td style="text-align:center;"><button class="btn btn-sm" style="background:#4A6741;font-size:11px;" onclick="solicitarCompraMEE(&quot;'+m.codigo+'&quot;,&quot;'+_eq(m.descripcion)+'&quot;,'+m.stock_actual+','+m.stock_minimo+')">Solicitar</button></td>'
    +'</tr>';
  }).join('');
}
async function generarOCsDesdeAlertasMEE(){
  var r=await fetch('/api/alertas-mee'); var d=await r.json();
  if(!d.alertas||!d.alertas.length){alert('No hay alertas MEE activas');return;}
  var items=d.alertas.map(function(m){return {codigo_mp:m.codigo,nombre_mp:m.descripcion,cantidad_g:Math.max(m.stock_minimo*2-m.stock_actual,1),precio_unitario:0};});
  var r2=await fetch('/api/ordenes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({proveedor:'Por asignar',observaciones:'OC automatica desde alertas MEE',items:items,creado_por:OPER_ACTUAL||'Sistema'})});
  var d2=await r2.json();
  if(r2.ok)alert('OC creada: '+d2.numero_oc+'\\nVisible en Compras > Ordenes');
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
  var sku_pt=document.getElementById('prod-sku-pt')?document.getElementById('prod-sku-pt').value.trim():'';
  var uds_pt=document.getElementById('prod-uds-pt')?parseInt(document.getElementById('prod-uds-pt').value)||0:0;
  var precio_pt=document.getElementById('prod-precio-pt')?parseFloat(document.getElementById('prod-precio-pt').value)||0:0;
  var r=await fetch('/api/produccion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({producto:prod,cantidad_kg:kg,observaciones:obs,presentacion:pres,operador:OPER_ACTUAL,sku_pt:sku_pt,unidades_pt:uds_pt,precio_pt:precio_pt})});
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
      +'<select id="mee-cons-'+cat+'" onchange="toggleMEECant(&quot;'+cat+'&quot;)" style="width:100%;font-size:0.85em;">'+optsHtml+'</select>'
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

// ── Funciones CC / Trazabilidad / Conteo Ciclico ──
async function cargarCuarentena(){
  try{
    var r=await fetch('/api/lotes/cuarentena');
    var data=await r.json();
    var tb=document.getElementById('cuar-tbody');
    if(!data.length){tb.innerHTML='<tr><td colspan="10" style="text-align:center;color:#999;padding:20px;">Sin lotes pendientes de revision QC</td></tr>';return;}
    var h='';
    data.forEach(function(l){
      var esAdmin=(OPER_ACTUAL==='sebastian'||OPER_ACTUAL==='alejandro'||OPER_ACTUAL==='hernando');
      var estadoColor=l.estado_lote==='CUARENTENA'?'#e67e22':l.estado_lote==='CUARENTENA_EXTENDIDA'?'#c0392b':'#888';
      h+='<tr>';
      h+='<td style="font-family:monospace;font-size:0.85em;">'+l.codigo_mp+'</td>';
      h+='<td style="font-size:0.8em;color:#555;">'+(l.nombre_inci||'')+'</td>';
      h+='<td>'+l.nombre+'</td>';
      h+='<td style="font-family:monospace;font-weight:600;">'+l.lote+'</td>';
      h+='<td style="text-align:right;font-weight:600;">'+l.cantidad.toLocaleString()+'</td>';
      h+='<td style="font-size:0.85em;">'+(l.proveedor||'')+'</td>';
      h+='<td style="font-size:0.82em;">'+(l.numero_oc||'')+'</td>';
      h+='<td style="font-size:0.82em;">'+l.fecha.substring(0,10)+'</td>';
      h+='<td><span style="background:'+estadoColor+'20;color:'+estadoColor+';padding:2px 8px;border-radius:10px;font-size:0.8em;font-weight:700;">'+l.estado_lote.replace('_',' ')+'</span></td>';
      h+='<td>';
      if(esAdmin){
        h+='<button onclick="abrirCCModal('+JSON.stringify(l)+')" style="padding:5px 12px;background:#2B7A78;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:0.82em;font-weight:600;">Revisar CC</button>';
      }else{
        h+='<span style="color:#999;font-size:0.82em;">Solo CC/Admin</span>';
      }
      h+='</td></tr>';
    });
    tb.innerHTML=h;
  }catch(e){console.error(e);}
}

function abrirCCModal(lote){
  _ccLoteActual=lote;
  document.getElementById('cc-modal-lote').textContent=lote.lote+' -- '+lote.nombre;
  document.getElementById('cc-firmante').textContent=OPER_ACTUAL;
  document.getElementById('cc-lote-info').innerHTML=
    '<div><b>Codigo:</b> '+lote.codigo_mp+'</div>'+
    '<div><b>INCI:</b> '+(lote.nombre_inci||'--')+'</div>'+
    '<div><b>Cantidad:</b> '+Number(lote.cantidad).toLocaleString()+' g</div>'+
    '<div><b>Proveedor:</b> '+(lote.proveedor||'--')+'</div>'+
    '<div><b>Factura:</b> '+(lote.numero_factura||'--')+'</div>'+
    '<div><b>OC:</b> '+(lote.numero_oc||'--')+'</div>';
  ['cc-coa-ok','cc-lote-coincide','cc-coa-vigente','cc-ficha-ok','cc-muestra-ret'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.checked=false;
  });
  ['cc-solub-ok','cc-solub-fail','cc-aql-ok','cc-aql-fail','cc-aql-ext'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.checked=false;
  });
  document.getElementById('cc-aql-obs').value='';
  document.getElementById('cc-obs-final').value='';
  document.getElementById('cc-modal-msg').innerHTML='';
  document.getElementById('cc-modal').style.display='flex';
}

function cerrarCCModal(){
  document.getElementById('cc-modal').style.display='none';
  _ccLoteActual=null;
}

async function enviarRevisionCC(){
  if(!_ccLoteActual){return;}
  var coaOk=document.getElementById('cc-coa-ok').checked;
  var loteCoincide=document.getElementById('cc-lote-coincide').checked;
  var coaVigente=document.getElementById('cc-coa-vigente').checked;
  var fichaOk=document.getElementById('cc-ficha-ok').checked;
  var solubResult=document.querySelector('input[name="cc-solub"]:checked');
  var aqlResult=document.querySelector('input[name="cc-aql"]:checked');
  var aqlObs=document.getElementById('cc-aql-obs').value.trim();
  var muestraRet=document.getElementById('cc-muestra-ret').checked;
  var obsFinal=document.getElementById('cc-obs-final').value.trim();
  var msg=document.getElementById('cc-modal-msg');
  if(!solubResult){msg.innerHTML='<div class="alert-error">Selecciona resultado de solubilidad</div>';return;}
  if(!aqlResult){msg.innerHTML='<div class="alert-error">Selecciona resultado AQL</div>';return;}
  if((aqlResult.value==='NO_CONFORME'||aqlResult.value==='CUARENTENA_EXTENDIDA')&&!aqlObs){
    msg.innerHTML='<div class="alert-error">Las observaciones son obligatorias para este resultado</div>';return;
  }
  var payload={
    mov_id:_ccLoteActual.id,
    lote:_ccLoteActual.lote,
    codigo_mp:_ccLoteActual.codigo_mp,
    coa_ok:coaOk,
    lote_coincide:loteCoincide,
    coa_vigente:coaVigente,
    ficha_ok:fichaOk,
    solubilidad:solubResult.value,
    resultado_aql:aqlResult.value,
    observaciones_aql:aqlObs,
    muestra_retencion:muestraRet,
    observaciones:obsFinal,
    firmante:OPER_ACTUAL
  };
  try{
    document.getElementById('cc-submit-btn').disabled=true;
    document.getElementById('cc-submit-btn').textContent='Registrando...';
    var r=await fetch('/api/lotes/cc-review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    var res=await r.json();
    if(r.ok){
      msg.innerHTML='<div class="alert-success">'+res.message+'</div>';
      document.getElementById('cuar-msg').innerHTML='<div class="alert-success">Revision CC registrada -- '+res.estado+' -- Lote: '+payload.lote+'</div>';
      setTimeout(function(){cerrarCCModal();cargarCuarentena();},1800);
    }else{
      msg.innerHTML='<div class="alert-error">'+(res.error||'Error al registrar')+'</div>';
    }
  }catch(e){
    msg.innerHTML='<div class="alert-error">Error: '+e.message+'</div>';
  }finally{
    document.getElementById('cc-submit-btn').disabled=false;
    document.getElementById('cc-submit-btn').textContent='Firmar y Registrar';
  }
}

async function buscarTrazabilidad(){
  var lote=(document.getElementById('trz-lote').value||'').trim();
  if(!lote){alert('Ingresa un numero de lote');return;}
  try{
    var r=await fetch('/api/trazabilidad/'+encodeURIComponent(lote));
    var data=await r.json();
    if(!data.ingreso){
      document.getElementById('trz-msg').innerHTML='<div class="alert-error">Lote no encontrado: '+lote+'</div>';
      document.getElementById('trz-result').style.display='none';
      return;
    }
    document.getElementById('trz-msg').innerHTML='';
    document.getElementById('trz-result').style.display='block';
    var ing=data.ingreso;
    document.getElementById('trz-ingreso').innerHTML=
      '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;">'+
      '<div><b>Codigo:</b> '+ing.codigo_mp+'</div>'+
      '<div><b>Nombre:</b> '+ing.nombre+'</div>'+
      '<div><b>INCI:</b> '+(ing.nombre_inci||'—')+'</div>'+
      '<div><b>Cantidad:</b> '+Number(ing.cantidad_g).toLocaleString()+' g</div>'+
      '<div><b>Proveedor:</b> '+(ing.proveedor||'—')+'</div>'+
      '<div><b>Factura:</b> '+(ing.factura||'—')+'</div>'+
      '<div><b>OC:</b> '+(ing.orden_compra||'—')+'</div>'+
      '<div><b>Precio/kg:</b> '+(ing.precio_kg?'$'+Number(ing.precio_kg).toLocaleString('es-CO'):'—')+'</div>'+
      '<div><b>Fecha:</b> '+(ing.fecha?ing.fecha.substring(0,10):'—')+'</div>'+
      '</div>';
    document.getElementById('trz-nprod').textContent=data.total_producciones;
    var tb=document.getElementById('trz-prod-tbody');
    if(!data.producciones.length){
      tb.innerHTML='<tr><td colspan="4" style="text-align:center;color:#999;">Este lote no ha sido usado en produccion</td></tr>';
    } else {
      var h='';
      data.producciones.forEach(function(p){
        h+='<tr><td>'+p.producto+'</td><td>'+p.fecha.substring(0,10)+'</td><td>'+p.operador+'</td><td style="text-align:right;">'+Number(p.cantidad_g).toLocaleString()+'</td></tr>';
      });
      tb.innerHTML=h;
    }
  }catch(e){document.getElementById('trz-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}

var _conteoActivo = null;
var _conteoItems = [];

async function cargarEstanterias(){
  try{
    var r = await fetch('/api/conteo/estanterias');
    var data = await r.json();
    var sel = document.getElementById('cnt-est-sel');
    if(!sel) return;
    while(sel.options.length > 1) sel.remove(1);
    data.forEach(function(e){
      var opt = document.createElement('option');
      opt.value = e.estanteria;
      opt.textContent = e.estanteria + ' (' + e.total_mps + ' MPs, ' + (e.stock_total/1000).toFixed(1) + ' kg)';
      sel.appendChild(opt);
    });
  }catch(e){}
}

async function iniciarConteo(){
  var est = document.getElementById('cnt-est-sel').value;
  var resp = document.getElementById('cnt-responsable').value.trim() || OPER_ACTUAL;
  if(!est){alert('Selecciona una estanteria'); return;}
  try{
    var r = await fetch('/api/conteo/iniciar',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({estanteria:est,responsable:resp})});
    var res = await r.json();
    if(!r.ok){alert(res.error||'Error'); return;}
    _conteoActivo = {id: res.conteo_id, numero: res.numero, estanteria: est};
    document.getElementById('cnt-numero').textContent = res.numero;
    document.getElementById('cnt-est-label').textContent = est;
    document.getElementById('cnt-panel').style.display = 'block';
    await cargarItemsConteo(est);
  }catch(e){alert('Error: '+e.message);}
}

async function cargarItemsConteo(est){
  try{
    var r = await fetch('/api/conteo/materiales?estanteria='+encodeURIComponent(est));
    _conteoItems = await r.json();
    var causas = ['Error de conteo','Consumo no descargado','Ingreso no registrado','Error unidad de medida','Merma justificada','Traslado no registrado','Material no identificado','Otro'];
    var causaOpts = causas.map(function(c){return '<option>'+c+'</option>';}).join('');
    var h = '';
    _conteoItems.forEach(function(mp, i){
      h += '<tr id="cnt-row-'+i+'">';
      h += '<td style="font-family:monospace;font-size:0.82em;">'+mp.codigo_mp+'</td>';
      h += '<td style="font-size:0.78em;color:#555;">'+(mp.inci||'')+'</td>';
      h += '<td style="font-size:0.88em;">'+mp.nombre+'</td>';
      h += '<td style="text-align:right;font-weight:600;font-family:monospace;">'+Number(mp.stock_sistema).toLocaleString()+'</td>';
      h += '<td><input type="number" id="cnt-fis-'+i+'" min="0" step="0.1" oninput="calcDiff('+i+','+mp.stock_sistema+','+mp.precio_ref+')" style="width:120px;padding:6px;border:1px solid #dde;border-radius:6px;text-align:right;font-family:monospace;"></td>';
      h += '<td id="cnt-diff-'+i+'" style="text-align:right;font-family:monospace;font-weight:700;">--</td>';
      h += '<td id="cnt-pct-'+i+'" style="font-size:0.85em;">--</td>';
      h += '<td id="cnt-val-'+i+'" style="font-size:0.82em;color:#888;">--</td>';
      h += '<td><select id="cnt-causa-'+i+'" style="width:150px;padding:5px;border:1px solid #dde;border-radius:6px;font-size:0.8em;"><option value="">Sin diferencia</option>'+causaOpts+'</select></td>';
      h += '<td id="cnt-adj-'+i+'"></td>';
      h += '</tr>';
    });
    document.getElementById('cnt-tbody').innerHTML = h || '<tr><td colspan="10" style="text-align:center;color:#999;">Sin materiales en esta estanteria</td></tr>';
  }catch(e){console.error(e);}
}

function calcDiff(i, stockSis, precioRef){
  var fis = parseFloat(document.getElementById('cnt-fis-'+i).value);
  var diffEl = document.getElementById('cnt-diff-'+i);
  var pctEl = document.getElementById('cnt-pct-'+i);
  var valEl = document.getElementById('cnt-val-'+i);
  var row = document.getElementById('cnt-row-'+i);
  if(isNaN(fis)){diffEl.textContent='--';pctEl.textContent='--';valEl.textContent='--';return;}
  var diff = fis - stockSis;
  var pct = stockSis > 0 ? Math.abs(diff/stockSis)*100 : 0;
  var valDiff = Math.abs(diff/1000) * precioRef;
  diffEl.textContent = (diff >= 0 ? '+' : '') + diff.toLocaleString('es-CO',{maximumFractionDigits:1});
  diffEl.style.color = diff === 0 ? '#27ae60' : diff > 0 ? '#2980b9' : '#e74c3c';
  pctEl.textContent = pct.toFixed(1) + '%';
  if(pct > 5){
    pctEl.style.color = '#e74c3c';
    pctEl.textContent += ' ⚠ GERENCIA';
    row.style.background = '#fff5f5';
  } else {
    pctEl.style.color = pct > 2 ? '#e67e22' : '#27ae60';
    row.style.background = '';
  }
  valEl.textContent = valDiff > 0 ? '$'+valDiff.toLocaleString('es-CO',{maximumFractionDigits:0}) : '--';
}

async function guardarConteo(){
  if(!_conteoActivo){alert('Inicia un conteo primero'); return;}
  var items = [];
  _conteoItems.forEach(function(mp, i){
    var fisEl = document.getElementById('cnt-fis-'+i);
    if(!fisEl || fisEl.value === '') return;
    items.push({
      codigo_mp: mp.codigo_mp,
      nombre: mp.nombre,
      stock_sistema: mp.stock_sistema,
      stock_fisico: parseFloat(fisEl.value),
      precio_ref: mp.precio_ref,
      estanteria: mp.estanteria,
      causa_diferencia: document.getElementById('cnt-causa-'+i).value
    });
  });
  try{
    var r = await fetch('/api/conteo/'+_conteoActivo.id+'/guardar',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({items:items})});
    var res = await r.json();
    if(r.ok){
      var msg = 'Guardado. ';
      if(res.items_con_diferencia > 0) msg += res.items_con_diferencia+' item(s) con diferencias.';
      document.getElementById('cnt-resumen').style.display = 'block';
      document.getElementById('cnt-resumen').innerHTML = msg + ' Revisa los items marcados con ⚠ GERENCIA antes de cerrar.';
      await cargarHistorialConteos();
    }
  }catch(e){alert('Error: '+e.message);}
}

async function cerrarConteo(){
  if(!_conteoActivo) return;
  if(!confirm('Cerrar el conteo? Ya no se podran editar los conteos fisicos.')) return;
  try{
    var r = await fetch('/api/conteo/'+_conteoActivo.id+'/cerrar',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    var res = await r.json();
    document.getElementById('cnt-msg').innerHTML = '<div class="alert-success">'+res.message+'</div>';
    document.getElementById('cnt-panel').style.display = 'none';
    _conteoActivo = null;
    await cargarHistorialConteos();
    await cargarEstanterias();
  }catch(e){alert('Error: '+e.message);}
}

async function aplicarAjuste(itemId){
  if(!confirm('Aplicar ajuste de inventario? Se registrara un movimiento de correccion en el sistema.')) return;
  try{
    var r = await fetch('/api/conteo/0/ajustar',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({item_id:itemId})});
    var res = await r.json();
    if(r.ok){
      document.getElementById('cnt-msg').innerHTML = '<div class="alert-success">'+res.message+'</div>';
    }else{
      document.getElementById('cnt-msg').innerHTML = '<div class="alert-error">'+(res.error||'Error')+'</div>';
    }
  }catch(e){}
}

async function cargarHistorialConteos(){
  try{
    var r = await fetch('/api/conteo/historial');
    var data = await r.json();
    var tb = document.getElementById('cnt-hist-tbody');
    if(!data.length){tb.innerHTML='<tr><td colspan="8" style="text-align:center;color:#999;">Sin conteos</td></tr>';return;}
    var h = '';
    data.forEach(function(c){
      var estadoColor = c.estado === 'Cerrado' ? '#27ae60' : '#e67e22';
      h += '<tr>';
      h += '<td style="font-family:monospace;font-size:0.85em;">'+c.numero+'</td>';
      h += '<td>'+(c.estanteria||'')+'</td>';
      h += '<td style="font-size:0.82em;">'+(c.fecha_inicio?c.fecha_inicio.substring(0,10):'')+'</td>';
      h += '<td>'+(c.responsable||'')+'</td>';
      h += '<td><span style="color:'+estadoColor+';font-weight:700;">'+c.estado+'</span></td>';
      h += '<td style="text-align:center;">'+c.total_items+'</td>';
      h += '<td style="text-align:center;color:'+(c.items_diferencia>0?'#e74c3c':'#27ae60')+';">'+c.items_diferencia+'</td>';
      h += '<td style="text-align:center;">';
      if(c.items_gerencia > 0) h += '<span style="color:#e74c3c;font-weight:700;">'+c.items_gerencia+' ⚠</span>';
      else h += '<span style="color:#27ae60;">OK</span>';
      h += '</td></tr>';
    });
    tb.innerHTML = h;
  }catch(e){}
}
</script>
</body>
</html>
"""

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
                           f'FEFO: {producto} x {cantidad_kg}kg', lote_n, data.get('operador','')))
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
    ingresos = 0
    for item in items_oc:
        codigo, nombre, cantidad = item
        if categoria == 'MEE':
            cur.execute("UPDATE maestro_mee SET stock_actual = stock_actual + ? WHERE codigo=?", (cantidad, codigo))
            cur.execute("INSERT INTO movimientos_mee (codigo_mee, tipo, cantidad, referencia, observaciones, operador, fecha) VALUES (?,?,?,?,?,?,?)",
                       (codigo, 'entrada', cantidad, numero_oc, f'Recepcion OC {numero_oc}', operador, fecha))
        else:
            cur.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, observaciones, proveedor, operador) VALUES (?,?,?,?,?,?,?,?)",
                       (codigo, nombre, cantidad, 'Entrada', fecha, f'Recepcion OC {numero_oc}', prov_nombre, operador))
        ingresos += 1
    data2 = request.get_json(silent=True) or {}
    obs_r = data2.get('observaciones_recepcion', '')
    disc_r = 1 if data2.get('tiene_discrepancias') else 0
    items_r = data2.get('items_recepcion', [])
    receptor_nombre = data2.get('receptor_nombre', '') or operador
    for ir in items_r:
        try:
            cur.execute(
                "UPDATE ordenes_compra_items SET cantidad_recibida_g=?, estado_recepcion=?, notas_recepcion=?"
                " WHERE numero_oc=? AND codigo_mp=?",
                (float(ir.get('cantidad_recibida', 0)), ir.get('estado', 'OK'), ir.get('notas', ''), numero_oc, ir.get('codigo_mp', '')))
        except Exception:
            pass
    try:
        cur.execute(
            "UPDATE ordenes_compra SET estado='Recibida', fecha_recepcion=?,"
            " observaciones_recepcion=?, tiene_discrepancias=?, recibido_por=? WHERE numero_oc=?",
            (fecha, obs_r, disc_r, receptor_nombre, numero_oc))
    except Exception:
        cur.execute("UPDATE ordenes_compra SET estado='Recibida', fecha_recepcion=? WHERE numero_oc=?", (fecha, numero_oc))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'numero_oc': numero_oc, 'ingresos': ingresos})

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
        "FROM ordenes_compra WHERE estado IN ('Autorizada','Recibida','Pagada') "
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
