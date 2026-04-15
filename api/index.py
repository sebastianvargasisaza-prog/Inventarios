import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, request, Response
from anthropic import Anthropic
import pandas as pd

DATABASE_URL = os.environ.get('DATABASE_URL')
DB_PATH = '/tmp/inventario.db'

class _Cur:
    def __init__(self, c, pg): self._c, self._pg = c, pg
    def execute(self, q, p=None):
        if self._pg: q = q.replace('?','%s')
        self._c.execute(q, p) if p is not None else self._c.execute(q)
    def fetchone(self): return self._c.fetchone()
    def fetchall(self): return self._c.fetchall()

class _Conn:
    def __init__(self, c, pg): self._c, self._pg = c, pg
    def cursor(self): return _Cur(self._c.cursor(), self._pg)
    def commit(self): self._c.commit()
    def rollback(self):
        try: self._c.rollback()
        except: pass
    def close(self): self._c.close()

IS_PG = False
if DATABASE_URL:
    try:
        import psycopg2 as _pg2
        def get_conn(): return _Conn(_pg2.connect(DATABASE_URL, sslmode='require'), True)
        _t = get_conn(); _t.close()
        IS_PG = True
        print("PostgreSQL connected OK")
    except BaseException as _e:
        import sys as _sys
        print(f"PostgreSQL unavailable, using SQLite: {_e}", file=_sys.stderr)
        IS_PG = False

if not IS_PG:
    def get_conn():
        r = sqlite3.connect(DB_PATH)
        r.row_factory = sqlite3.Row
        return _Conn(r, False)


app = Flask(__name__)

_anthropic_client = None
def get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurada")
        _anthropic_client = Anthropic(api_key=api_key)
    return _anthropic_client

DB_PATH = '/tmp/inventario.db'

def init_db():
    conn = get_conn(); c = conn.cursor()
    pk = "SERIAL PRIMARY KEY" if IS_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
    c.execute(f"CREATE TABLE IF NOT EXISTS movimientos (id {pk}, material_id TEXT, material_nombre TEXT, cantidad REAL, tipo TEXT, fecha TEXT, observaciones TEXT, lote TEXT, fecha_vencimiento TEXT, estanteria TEXT, posicion TEXT, proveedor TEXT, estado_lote TEXT)")
    for col in ["lote","fecha_vencimiento","estanteria","posicion","proveedor","estado_lote"]:
        try: c.execute(f"ALTER TABLE movimientos ADD COLUMN {col} TEXT"); conn.commit()
        except: conn.rollback() if IS_PG else None
    c.execute(f"CREATE TABLE IF NOT EXISTS producciones (id {pk}, producto TEXT, cantidad REAL, fecha TEXT, estado TEXT, observaciones TEXT)")
    c.execute(f"CREATE TABLE IF NOT EXISTS alertas (id {pk}, material_id TEXT, material_nombre TEXT, stock_actual REAL, stock_minimo REAL, fecha TEXT, estado TEXT)")
    c.execute(f"CREATE TABLE IF NOT EXISTS formula_headers (id {pk}, producto_nombre TEXT UNIQUE, unidad_base_g REAL DEFAULT 1000, descripcion TEXT, fecha_creacion TEXT)")
    c.execute(f"CREATE TABLE IF NOT EXISTS formula_items (id {pk}, producto_nombre TEXT, material_id TEXT, material_nombre TEXT, porcentaje REAL)")
    c.execute(f"CREATE TABLE IF NOT EXISTS maestro_mps (codigo_mp TEXT PRIMARY KEY, nombre_inci TEXT, nombre_comercial TEXT, tipo TEXT, proveedor TEXT, stock_minimo REAL DEFAULT 0, activo INTEGER DEFAULT 1)")
    c.execute(f"CREATE TABLE IF NOT EXISTS ordenes_compra (id {pk}, numero_oc TEXT UNIQUE, fecha TEXT, estado TEXT DEFAULT 'Pendiente', proveedor TEXT, observaciones TEXT)")
    c.execute(f"CREATE TABLE IF NOT EXISTS ordenes_compra_items (id {pk}, numero_oc TEXT, codigo_mp TEXT, nombre_mp TEXT, cantidad_solicitada REAL, unidad TEXT DEFAULT 'g')")
    conn.commit(); conn.close()

init_db()
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Inventarios - ANIMUS Lab</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Segoe UI',sans-serif; background:linear-gradient(135deg,#667eea,#764ba2); min-height:100vh; padding:20px; }
.container { max-width:1400px; margin:0 auto; background:white; border-radius:12px; box-shadow:0 20px 60px rgba(0,0,0,0.3); overflow:hidden; }
.header { background:linear-gradient(135deg,#667eea,#764ba2); color:white; padding:25px; text-align:center; }
.header h1 { font-size:1.8em; margin-bottom:6px; }
.tabs { display:flex; background:#f5f5f5; border-bottom:2px solid #ddd; overflow-x:auto; }
.tab-button { flex:1; padding:13px 12px; background:none; border:none; cursor:pointer; font-size:0.9em; font-weight:500; color:#666; white-space:nowrap; min-width:90px; transition:all 0.2s; }
.tab-button:hover { background:white; color:#667eea; }
.tab-button.active { background:white; color:#667eea; border-bottom:3px solid #667eea; }
.tab-content { display:none; padding:25px; }
.tab-content.active { display:block; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:15px; margin:15px 0; }
.card { background:linear-gradient(135deg,#667eea,#764ba2); color:white; padding:18px; border-radius:10px; text-align:center; }
.card h3 { font-size:0.85em; opacity:0.9; margin-bottom:6px; }
.card p { font-size:1.8em; font-weight:700; }
button { background:linear-gradient(135deg,#667eea,#764ba2); color:white; border:none; padding:10px 18px; border-radius:6px; cursor:pointer; font-size:0.9em; font-weight:500; }
button:hover { opacity:0.9; }
input,select,textarea { width:100%; padding:9px; border:1px solid #ddd; border-radius:6px; font-size:0.95em; margin-top:3px; }
.form-group { margin-bottom:14px; }
label { font-weight:600; font-size:0.88em; color:#444; }
.table { width:100%; border-collapse:collapse; margin-top:12px; font-size:0.88em; }
.table th { background:#667eea; color:white; padding:9px 10px; text-align:left; }
.table td { padding:8px 10px; border-bottom:1px solid #eee; }
.table tr:hover { background:#f8f9ff; }
.alert-success { background:#d4edda; color:#155724; padding:10px; border-radius:6px; margin-top:8px; }
.alert-error { background:#f8d7da; color:#721c24; padding:10px; border-radius:6px; margin-top:8px; }
.chat-box { height:320px; overflow-y:auto; border:1px solid #ddd; border-radius:8px; padding:12px; margin-bottom:12px; background:#f9f9f9; }
.msg { margin-bottom:10px; padding:9px 13px; border-radius:8px; max-width:85%; }
.msg.user { background:#667eea; color:white; margin-left:auto; }
.msg.bot { background:white; border:1px solid #ddd; }
h2 { color:#333; margin-bottom:12px; font-size:1.3em; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>&#128230; Sistema de Inventarios</h1>
    <p>ANIMUS Lab - Gestion Inteligente de Inventario</p>
  </div>
  <div class="tabs">
    <button class="tab-button active" onclick="switchTab('dashboard',this)">&#128202; Dashboard</button>
    <button class="tab-button" onclick="switchTab('stock',this)">&#128230; Stock</button>
    <button class="tab-button" onclick="switchTab('formulas',this)">&#129514; Formulas</button>
    <button class="tab-button" onclick="switchTab('produccion',this)">&#127981; Produccion</button>
    <button class="tab-button" onclick="switchTab('abc',this)">&#128200; ABC</button>
    <button class="tab-button" onclick="switchTab('alertas',this)">&#9888; Alertas</button>
    <button class="tab-button" onclick="switchTab('chat',this)">&#129302; Chat IA</button>
    <button class="tab-button" onclick="switchTab('movimientos',this)">&#128203; Movimientos</button>
  </div>

  <div id="dashboard" class="tab-content active">
    <h2>Dashboard Principal</h2>
    <div class="grid">
      <div class="card"><h3>Stock Total</h3><p id="stock-total">-</p></div>
      <div class="card"><h3>Materiales</h3><p id="materiales-count">-</p></div>
      <div class="card"><h3>Alertas</h3><p id="alertas-count">-</p></div>
      <div class="card"><h3>Producciones</h3><p id="producciones-count">-</p></div>
    </div>
    <button onclick="loadDashboard()">Actualizar</button>
  </div>

  <div id="stock" class="tab-content">
    <h2>&#128230; Stock por Lote</h2>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:14px;">
      <input type="text" id="stock-search" placeholder="MP, lote, proveedor..." oninput="filterStock()" style="width:200px;margin-top:0;">
      <select id="stock-est" onchange="filterStock()" style="padding:9px;border:1px solid #ddd;border-radius:6px;margin-top:0;"><option value="">Todas estanterias</option></select>
      <select id="stock-alerta" onchange="filterStock()" style="padding:9px;border:1px solid #ddd;border-radius:6px;margin-top:0;"><option value="">Todos estados</option><option value="vencido">Vencido</option><option value="critico">Critico &lt;30d</option><option value="proximo">Proximo &lt;90d</option><option value="ok">Vigente</option></select>
      <button onclick="loadStock()">&#8635; Actualizar</button>
      <span id="stock-count" style="color:#888;font-size:0.88em;"></span>
    </div>
    <div style="overflow-x:auto;">
    <table class="table">
      <thead><tr>
        <th>Codigo</th><th>Material</th><th>Lote</th><th>Proveedor</th>
        <th style="text-align:center;">Est.</th><th style="text-align:center;">Pos.</th>
        <th style="text-align:right;">g</th><th style="text-align:right;">kg</th>
        <th style="text-align:center;">Vence</th><th style="text-align:center;">Estado</th>
      </tr></thead>
      <tbody id="stock-body"><tr><td colspan="10" style="text-align:center;color:#999;padding:20px;">Cargando...</td></tr></tbody>
    </table>
    </div>
  </div>

  <div id="recepcion" class="tab-content">
    <h2>&#128666; Recepcion de Materia Prima</h2>
    <p style="color:#666;margin-bottom:18px;">Ingresa el codigo MP y el sistema completa los datos del catalogo automaticamente.</p>
    <div style="background:#f8f9ff;border:1px solid #dde;border-radius:10px;padding:20px;margin-bottom:20px;">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;">
        <div class="form-group"><label>Codigo MP</label><input type="text" id="rec-cod" placeholder="MP00001" style="text-transform:uppercase;" oninput="buscarMP(this.value)"><small id="rec-info" style="color:#667eea;font-size:0.85em;margin-top:4px;display:block;"></small></div>
        <div class="form-group"><label>Nombre Comercial</label><input type="text" id="rec-nombre" placeholder="Auto-completado"></div>
        <div class="form-group"><label>Proveedor</label><input type="text" id="rec-prov" placeholder="Auto-completado"></div>
        <div class="form-group"><label>N Lote (vacio = auto)</label><input type="text" id="rec-lote" placeholder="Ej: LYPH250727"></div>
        <div class="form-group"><label>Cantidad (g)</label><input type="number" id="rec-cant" placeholder="0" step="0.01"></div>
        <div class="form-group"><label>Fecha Vencimiento</label><input type="date" id="rec-vence"></div>
        <div class="form-group"><label>Estanteria</label><input type="text" id="rec-est" placeholder="Ej: 9"></div>
        <div class="form-group"><label>Posicion</label><input type="text" id="rec-pos" placeholder="Ej: B"></div>
      </div>
      <div class="form-group"><label>Observaciones</label><input type="text" id="rec-obs" placeholder="Opcional"></div>
      <div style="display:flex;gap:10px;margin-top:15px;">
        <button onclick="registrarRecepcion()" style="background:#27ae60;">&#10003; Registrar Entrada</button>
        <button onclick="generarRotuloRec()" style="background:#2980b9;">&#128209; Rotulo Recepcion</button>
        <button onclick="limpiarRec()" style="background:#95a5a6;">Limpiar</button>
      </div>
      <div id="rec-msg" style="margin-top:12px;"></div>
    </div>
    <h3 style="margin-bottom:10px;">Ultimas Recepciones</h3>
    <table class="table" id="rec-table">
      <thead><tr><th>Codigo</th><th>Material</th><th>Lote</th><th>Cantidad (g)</th><th>Proveedor</th><th>Vence</th><th>Fecha</th></tr></thead>
      <tbody><tr><td colspan="7" style="text-align:center;color:#999;">Sin recepciones</td></tr></tbody>
    </table>
  </div>

  <div id="compras" class="tab-content">
    <h2>&#128722; Ordenes de Compra</h2>
    <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:15px;margin-bottom:20px;">
      <h4 style="color:#856404;margin-bottom:8px;">MPs bajo stock minimo</h4>
      <div id="reabas-list" style="font-size:0.9em;">Calculando...</div>
      <button onclick="genOCAuto()" style="background:#e67e22;margin-top:10px;padding:7px 14px;font-size:0.88em;">Generar OC Automatica</button>
    </div>
    <div style="background:#f8f9ff;border:1px solid #dde;border-radius:10px;padding:18px;margin-bottom:20px;">
      <h3 style="margin-bottom:12px;">Nueva OC Manual</h3>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div class="form-group"><label>Proveedor</label><input type="text" id="oc-prov" placeholder="Nombre del proveedor"></div>
        <div class="form-group"><label>Observaciones</label><input type="text" id="oc-obs" placeholder="Opcional"></div>
      </div>
      <div id="oc-items"></div>
      <div style="display:flex;gap:10px;margin-top:10px;">
        <button onclick="addOCRow()" style="background:#28a745;">+ Agregar MP</button>
        <button onclick="crearOC()">&#128190; Crear OC</button>
      </div>
      <div id="oc-msg" style="margin-top:10px;"></div>
    </div>
    <h3 style="margin-bottom:10px;">Ordenes de Compra</h3>
    <div id="oc-list"><p style="color:#999;">Cargando...</p></div>
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
    <div class="form-group"><label>Observaciones</label><textarea id="prod-obs" rows="2" placeholder="Opcional"></textarea></div>
    <div style="display:flex;gap:10px;"><button onclick="registrarProd()">&#9989; Registrar Produccion</button><button onclick="abrirRotulos()" style="background:#c0392b;">&#128209; Generar Rotulos FEFO</button></div>
    <div id="prod-msg"></div>
  </div>

  <div id="abc" class="tab-content">
    <h2>&#128200; Analisis ABC de Inventario</h2>
    <button onclick="loadABC()">Generar Analisis</button>
    <div id="abc-results" style="margin-top:18px;"></div>
  </div>

  <div id="alertas" class="tab-content">
    <h2>&#9888; Alertas de Inventario</h2>
    <button onclick="loadAlertas()" style="margin-bottom:12px;">Actualizar Alertas</button>
    <table class="table" id="alertas-table">
      <thead><tr><th>Material</th><th>Stock Actual</th><th>Stock Minimo</th><th>Estado</th><th>Fecha</th></tr></thead>
      <tbody><tr><td colspan="5" style="text-align:center;color:#999;">Sin alertas</td></tr></tbody>
    </table>
  </div>

  <div id="chat" class="tab-content">
    <h2>&#129302; Chat IA - Asesor de Inventarios</h2>
    <div class="chat-box" id="chat-box">
      <div class="msg bot">Hola! Soy tu asesor de inventarios con IA. Preguntame sobre stock, puntos de reorden, analisis ABC o cualquier tema de gestion de inventarios para manufactura cosmetica.</div>
    </div>
    <div style="display:flex;gap:8px;">
      <input type="text" id="chat-in" placeholder="Escribe tu pregunta..." onkeypress="if(event.key==='Enter')enviarChat()" style="margin-top:0;">
      <button onclick="enviarChat()" style="min-width:70px;">Enviar</button>
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
    <button onclick="loadMovimientos()" style="margin-bottom:10px;">Ver Ultimos Movimientos</button>
    <table class="table" id="mov-table">
      <thead><tr><th>Material</th><th>Cantidad (g)</th><th>Tipo</th><th>Fecha</th><th>Observaciones</th></tr></thead>
      <tbody><tr><td colspan="5" style="text-align:center;color:#999;">Sin movimientos</td></tr></tbody>
    </table>
  </div>

</div>
<script>
var fData=[], allStock=[];

function switchTab(n,btn){
  document.querySelectorAll('.tab-content').forEach(function(t){t.classList.remove('active');});
  document.querySelectorAll('.tab-button').forEach(function(b){b.classList.remove('active');});
  document.getElementById(n).classList.add('active');
  if(btn) btn.classList.add('active');
  if(n==='stock') loadStock();
  if(n==='formulas'||n==='produccion') loadFormulas();
  if(n==='abc') loadABC();
  if(n==='alertas') loadAlertas();
  if(n==='movimientos') loadMovimientos();
}

async function loadDashboard(){
  try{
    var r=await fetch('/api/inventario'), d=await r.json();
    document.getElementById('stock-total').textContent=((d.stock_total||0)/1000).toFixed(1)+' kg';
    document.getElementById('materiales-count').textContent=d.movimientos||'0';
    document.getElementById('alertas-count').textContent=d.alertas||'0';
    document.getElementById('producciones-count').textContent=d.producciones||'0';
  }catch(e){}
}

var _lotes=[], _cat={}, _ocs=[];
async function loadStock(){
  try{
    var r=await fetch('/api/lotes'), d=await r.json();
    _lotes=d.lotes||[];
    var ests=[...new Set(_lotes.map(function(l){return l.estanteria;}).filter(Boolean))].sort(function(a,b){return Number(a)-Number(b)||a.localeCompare(b);});
    var sel=document.getElementById('stock-est');
    if(sel){
      sel.innerHTML='<option value="">Todas estanterias</option>';
      ests.forEach(function(e){
        var o=document.createElement('option');
        o.value=e; o.textContent='Est. '+e;
        sel.appendChild(o);
      });
    }
    document.getElementById('stock-count').textContent=_lotes.length+' lotes';
    renderStock(_lotes);
  }catch(e){document.getElementById('stock-body').innerHTML='<tr><td colspan="10" style="padding:20px;color:#c00;">Error al cargar stock.</td></tr>';}
}
function renderStock(items){
  var tb=document.getElementById('stock-body');
  if(!items.length){tb.innerHTML='<tr><td colspan="10" style="text-align:center;color:#999;padding:20px;">Sin datos</td></tr>';return;}
  var bg={vencido:'#ffebeb',critico:'#fff3e0',proximo:'#fffde7',ok:'transparent'};
  var fc={vencido:'#cc0000',critico:'#e65100',proximo:'#f57f17',ok:'#1a8a1a'};
  var lb={vencido:'VENCIDO',critico:'CRITICO',proximo:'PROXIMO',ok:'VIGENTE'};
  var h='';
  items.forEach(function(i){
    var a=i.alerta||'ok';
    var qc=i.cantidad_g<=0?'color:#cc0000;':i.cantidad_g<100?'color:#e68a00;':'color:#1a8a1a;';
    var dias=i.dias_para_vencer!=null?(i.dias_para_vencer<0?'Vencido hace '+(Math.abs(i.dias_para_vencer))+'d':i.dias_para_vencer+'d'):'';
    h+='<tr style="background:'+bg[a]+';">';
    h+='<td style="font-family:monospace;font-size:0.8em;color:#555;">'+i.material_id+'</td>';
    h+='<td style="font-weight:500;">'+i.material_nombre+'</td>';
    h+='<td style="font-family:monospace;font-size:0.82em;">'+i.lote+'</td>';
    h+='<td style="font-size:0.85em;color:#666;">'+i.proveedor+'</td>';
    h+='<td style="text-align:center;font-weight:700;color:#667eea;">'+i.estanteria+'</td>';
    h+='<td style="text-align:center;">'+i.posicion+'</td>';
    h+='<td style="text-align:right;font-weight:700;'+qc+'">'+i.cantidad_g.toLocaleString()+'</td>';
    h+='<td style="text-align:right;color:#888;">'+i.cantidad_kg.toFixed(3)+'</td>';
    h+='<td style="text-align:center;font-size:0.82em;color:'+fc[a]+';">'+i.fecha_vencimiento+'<br><b>'+dias+'</b></td>';
    h+='<td style="text-align:center;"><span style="background:'+bg[a]+';color:'+fc[a]+';padding:2px 8px;border-radius:10px;font-weight:700;font-size:0.78em;border:1px solid '+fc[a]+';">'+lb[a]+'</span></td>';
    h+='</tr>';
  });
  tb.innerHTML=h;
}
function filterStock(){
  var q=document.getElementById('stock-search').value.toLowerCase();
  var est=document.getElementById('stock-est')?document.getElementById('stock-est').value:'';
  var al=document.getElementById('stock-alerta')?document.getElementById('stock-alerta').value:'';
  var f=_lotes.filter(function(i){
    return(!q||i.material_nombre.toLowerCase().includes(q)||i.material_id.toLowerCase().includes(q)||(i.lote||'').toLowerCase().includes(q)||(i.proveedor||'').toLowerCase().includes(q))
      &&(!est||i.estanteria===est)&&(!al||i.alerta===al);
  });
  document.getElementById('stock-count').textContent=f.length+' de '+_lotes.length;
  renderStock(f);
}

// ── CATALOGO ──────────────────────────────────────────────────
async function cargarCatalogo(){
  try{
    var r=await fetch('/api/maestro-mps'), d=await r.json();
    _cat={};
    (d.mps||[]).forEach(function(mp){_cat[mp.codigo_mp]=mp;});
  }catch(e){}
}
async function buscarMP(cod){
  var mp=_cat[cod.toUpperCase()];
  if(!mp && cod.length>=5){
    try{
      var r=await fetch('/api/maestro-mps/'+cod.toUpperCase());
      if(r.ok) mp=await r.json();
    }catch(e){}
  }
  if(mp){
    var n=document.getElementById('rec-nombre'); if(n) n.value=mp.nombre_comercial||'';
    var p=document.getElementById('rec-prov'); if(p) p.value=mp.proveedor||'';
    var i=document.getElementById('rec-info'); if(i) i.textContent='Catalogo: '+mp.nombre_comercial+(mp.tipo?' | '+mp.tipo:'');
  }
}

// ── RECEPCION ─────────────────────────────────────────────────
var _ultimaRec=null;
function initRecepcion(){
  cargarCatalogo();
  cargarHistorialRec();
}
async function registrarRecepcion(){
  var data={
    codigo_mp:(document.getElementById('rec-cod').value||'').trim().toUpperCase(),
    nombre_comercial:(document.getElementById('rec-nombre').value||'').trim(),
    lote:(document.getElementById('rec-lote').value||'').trim(),
    cantidad:parseFloat(document.getElementById('rec-cant').value)||0,
    fecha_vencimiento:document.getElementById('rec-vence').value||'',
    estanteria:(document.getElementById('rec-est').value||'').trim(),
    posicion:(document.getElementById('rec-pos').value||'').trim(),
    proveedor:(document.getElementById('rec-prov').value||'').trim(),
    observaciones:(document.getElementById('rec-obs').value||'').trim()
  };
  if(!data.codigo_mp){alert('Ingresa el codigo MP');return;}
  if(data.cantidad<=0){alert('Ingresa una cantidad valida');return;}
  try{
    var r=await fetch('/api/recepcion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    _ultimaRec={codigo:data.codigo_mp,lote:res.lote||data.lote,cantidad:data.cantidad};
    document.getElementById('rec-msg').innerHTML='<div class="alert-success">'+res.message+'</div>';
    await cargarHistorialRec();
  }catch(e){document.getElementById('rec-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}
function generarRotuloRec(){
  if(!_ultimaRec){alert('Registra una recepcion primero');return;}
  window.open('/rotulo-recepcion/'+encodeURIComponent(_ultimaRec.codigo)+'/'+encodeURIComponent(_ultimaRec.lote)+'/'+_ultimaRec.cantidad,'_blank');
}
function limpiarRec(){
  ['rec-cod','rec-nombre','rec-prov','rec-lote','rec-cant','rec-vence','rec-est','rec-pos','rec-obs'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.value='';
  });
  var i=document.getElementById('rec-info'); if(i) i.textContent='';
  document.getElementById('rec-msg').innerHTML='';
}
async function cargarHistorialRec(){
  try{
    var r=await fetch('/api/movimientos'), d=await r.json();
    var entradas=(d.movimientos||[]).filter(function(m){return m.tipo==='Entrada';}).slice(0,15);
    var tb=document.querySelector('#rec-table tbody');
    if(!tb) return;
    if(entradas.length){
      var h='';
      entradas.forEach(function(m){
        h+='<tr><td style="font-family:monospace;font-size:0.85em;">'+m.material_id+'</td>';
        h+='<td>'+m.material_nombre+'</td>';
        h+='<td style="font-family:monospace;">'+(m.lote||'')+'</td>';
        h+='<td style="text-align:right;">'+m.cantidad.toLocaleString()+'</td>';
        h+='<td>'+(m.proveedor||'')+'</td>';
        h+='<td style="color:#c0392b;">'+(m.fecha_vencimiento?m.fecha_vencimiento.substring(0,10):'')+'</td>';
        h+='<td style="font-size:0.82em;color:#888;">'+m.fecha.substring(0,10)+'</td></tr>';
      });
      tb.innerHTML=h;
    }else{tb.innerHTML='<tr><td colspan="7" style="text-align:center;color:#999;">Sin recepciones</td></tr>';}
  }catch(e){}
}

// ── COMPRAS ───────────────────────────────────────────────────
async function initCompras(){
  await cargarAlertasReabas();
  await cargarOCs();
}
async function cargarAlertasReabas(){
  try{
    var r=await fetch('/api/alertas-reabastecimiento'), d=await r.json();
    var alertas=d.alertas||[];
    var el=document.getElementById('reabas-list');
    if(!el) return;
    if(!alertas.length){el.innerHTML='<span style="color:#28a745;">Todo el stock esta sobre el minimo</span>';return;}
    var h='';
    alertas.slice(0,5).forEach(function(a){
      h+='<div style="margin-bottom:4px;"><b>'+a.nombre+'</b> ('+a.codigo_mp+'): '+a.stock_actual.toLocaleString()+'g / min '+a.stock_minimo.toLocaleString()+'g <span style="color:#cc4444;">deficit: '+a.deficit.toLocaleString()+'g</span></div>';
    });
    if(alertas.length>5) h+='<div style="color:#888;">... y '+(alertas.length-5)+' mas</div>';
    el.innerHTML=h;
    window._alertasReabas=alertas;
  }catch(e){var el2=document.getElementById('reabas-list'); if(el2) el2.textContent='Error';}
}
async function genOCAuto(){
  var alertas=window._alertasReabas||[];
  if(!alertas.length){alert('No hay MPs bajo stock minimo');return;}
  var por={};
  alertas.forEach(function(a){
    var p=a.proveedor||'Sin proveedor';
    if(!por[p]) por[p]=[];
    por[p].push({codigo_mp:a.codigo_mp,nombre_mp:a.nombre,cantidad_solicitada:Math.ceil(a.deficit*1.1),unidad:'g'});
  });
  var nums=[];
  for(var prov in por){
    try{
      var r=await fetch('/api/ordenes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({proveedor:prov,observaciones:'OC automatica',items:por[prov]})});
      var res=await r.json();
      nums.push(res.numero_oc);
    }catch(e){}
  }
  alert('OCs creadas: '+nums.join(', '));
  await cargarOCs();
}
function addOCRow(){
  var c=document.getElementById('oc-items'); if(!c) return;
  var d=document.createElement('div');
  d.style.cssText='display:grid;grid-template-columns:120px 1fr 110px 38px;gap:6px;margin-bottom:6px;';
  var h2='';
  h2+='<input type="text" placeholder="MP00001" class="oc-c" style="padding:7px;border:1px solid #ddd;border-radius:5px;text-transform:uppercase;">';
  h2+='<input type="text" placeholder="Nombre" class="oc-n" style="padding:7px;border:1px solid #ddd;border-radius:5px;">';
  h2+='<input type="number" placeholder="g" class="oc-g" style="padding:7px;border:1px solid #ddd;border-radius:5px;">';
  h2+='<button onclick="this.parentElement.remove()" style="background:#ff4444;color:white;border:none;border-radius:5px;cursor:pointer;padding:7px;font-size:0.9em;">x</button>';
  d.innerHTML=h2;
  c.appendChild(d);
}
async function crearOC(){
  var prov=(document.getElementById('oc-prov').value||'').trim();
  var obs=(document.getElementById('oc-obs').value||'').trim();
  var rows=document.querySelectorAll('#oc-items > div');
  var items=[];
  rows.forEach(function(row){
    var cod=row.querySelector('.oc-c').value.trim();
    var nom=row.querySelector('.oc-n').value.trim();
    var cant=parseFloat(row.querySelector('.oc-g').value)||0;
    if(cod&&cant>0) items.push({codigo_mp:cod,nombre_mp:nom,cantidad_solicitada:cant,unidad:'g'});
  });
  if(!items.length){alert('Agrega al menos un item');return;}
  try{
    var r=await fetch('/api/ordenes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({proveedor:prov,observaciones:obs,items:items})});
    var res=await r.json();
    document.getElementById('oc-msg').innerHTML='<div class="alert-success">'+(res.message||'OC creada')+'</div>';
    await cargarOCs();
  }catch(e){document.getElementById('oc-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}
async function cargarOCs(){
  try{
    var r=await fetch('/api/ordenes-compra'), d=await r.json();
    _ocs=d.ordenes||[];
    var el=document.getElementById('oc-list'); if(!el) return;
    if(!_ocs.length){el.innerHTML='<p style="color:#999;">Sin ordenes de compra</p>';return;}
    var h='';
    _ocs.forEach(function(oc,idx){
      var col=oc.estado==='Recibida'?'#28a745':'#e67e22';
      var its='';
      (oc.items||[]).forEach(function(it){
        its+='<li>'+it.codigo_mp+': '+it.nombre_mp+' - '+it.cantidad.toLocaleString()+' '+it.unidad+'</li>';
      });
      h+='<div style="border:1px solid #dde;border-radius:8px;padding:15px;margin-bottom:10px;background:white;">';
      h+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">';
      h+='<h4 style="color:#667eea;">'+oc.numero_oc+' &mdash; '+oc.proveedor+'</h4>';
      h+='<span style="background:'+col+';color:white;padding:3px 10px;border-radius:10px;font-size:0.85em;font-weight:600;">'+oc.estado+'</span>';
      h+='</div>';
      h+='<ul style="list-style:none;padding:0;margin:0 0 8px;">'+its+'</ul>';
      h+='<small style="color:#888;">'+oc.fecha.substring(0,10)+'</small>';
      if(oc.estado!=='Recibida'){
        h+=' &nbsp;<button data-idx="'+idx+'" class="btn-recibir" style="padding:4px 10px;font-size:0.82em;background:#27ae60;color:white;border:none;border-radius:4px;cursor:pointer;">Marcar Recibida</button>';
      }
      h+='</div>';
    });
    el.innerHTML=h;
    el.querySelectorAll('.btn-recibir').forEach(function(btn){
      btn.addEventListener('click',function(){
        var idx=parseInt(this.getAttribute('data-idx'));
        if(_ocs[idx]) recibirOC(_ocs[idx].numero_oc);
      });
    });
  }catch(e){}
}
async function recibirOC(numero_oc){
  try{
    await fetch('/api/ordenes-compra/'+encodeURIComponent(numero_oc)+'/recibir',{method:'POST'});
    await cargarOCs();
  }catch(e){}
}

// ── ROTULOS ───────────────────────────────────────────────────
function abrirRotulos(){
  var prod=document.getElementById('prod-sel')?document.getElementById('prod-sel').value:'';
  var manual=document.getElementById('prod-manual')?document.getElementById('prod-manual').value.trim():'';
  var producto=prod||manual;
  var kg=parseFloat(document.getElementById('prod-kg')?document.getElementById('prod-kg').value:0)||0;
  if(!producto){alert('Selecciona un producto primero');return;}
  if(kg<=0){alert('Ingresa la cantidad en kg');return;}
  window.open('/rotulos/'+encodeURIComponent(producto)+'/'+kg,'_blank');
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
  if(!fl.length){c.innerHTML='<p style="color:#999;">Sin formulas aun. Crea la primera arriba.</p>';return;}
  c.innerHTML=fl.map(function(f){
    var total=f.items.reduce(function(s,i){return s+i.porcentaje;},0);
    return '<div style="border:1px solid #dde;border-radius:8px;padding:15px;margin-bottom:12px;background:white;">'
      +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
      +'<h4 style="color:#667eea;">'+f.producto_nombre+' <span style="font-weight:normal;color:#888;font-size:0.82em;">(base '+f.unidad_base_g+'g)</span></h4>'
      +'<div style="display:flex;gap:6px;">'
      +'<button onclick="editFormula(\''+f.producto_nombre+'\')" style="background:#667eea;padding:5px 10px;font-size:0.82em;">Editar</button>'
      +'<button onclick="delFormula(\''+f.producto_nombre+'\')" style="background:#cc4444;padding:5px 10px;font-size:0.82em;">Eliminar</button>'
      +'</div></div>'
      +'<table class="table" style="font-size:0.85em;">'
      +'<thead><tr><th>Codigo MP</th><th>Material</th><th>%</th><th>g por kg producto</th></tr></thead>'
      +'<tbody>'+f.items.map(function(it){return '<tr><td style="font-family:monospace;">'+it.material_id+'</td><td>'+it.material_nombre+'</td><td>'+it.porcentaje+'%</td><td style="font-weight:600;">'+(it.porcentaje*10).toFixed(2)+'g</td></tr>';}).join('')+'</tbody>'
      +'</table>'
      +'<small style="color:'+(Math.abs(total-100)<0.1?'#28a745':'#e68a00')+';">Total: '+total.toFixed(2)+'%'+(Math.abs(total-100)<0.1?' (OK)':' - revisar')+'</small>'
      +'</div>';
  }).join('');
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

function editFormula(nombre){
  var f=fData.find(function(x){return x.producto_nombre===nombre;});
  if(!f) return;
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

async function delFormula(nombre){
  if(!confirm('Eliminar formula de '+nombre+'?')) return;
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
    var r=await fetch('/api/produccion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({producto:prod,cantidad:kg,observaciones:document.getElementById('prod-obs').value})});
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

async function enviarChat(){
  var inp=document.getElementById('chat-in'), msg=inp.value.trim();
  if(!msg) return;
  var box=document.getElementById('chat-box');
  box.innerHTML+='<div class="msg user">'+msg+'</div>';
  inp.value='';
  try{
    var r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
    var d=await r.json();
    box.innerHTML+='<div class="msg bot">'+d.response+'</div>';
    box.scrollTop=box.scrollHeight;
  }catch(e){box.innerHTML+='<div class="msg bot">Error: '+e.message+'</div>';}
}

window.onload=function(){loadDashboard();loadFormulas();cargarCatalogo();};
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return Response(DASHBOARD_HTML, mimetype="text/html")

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Inventory system running'})

@app.route('/api/inventario')
def get_inventario():
    conn = get_conn()
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

@app.route('/api/stock')
def get_stock():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT material_id, material_nombre,
                 SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE 0 END),
                 SUM(CASE WHEN tipo='Salida' THEN cantidad ELSE 0 END),
                 SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END)
                 FROM movimientos GROUP BY material_id, material_nombre ORDER BY material_nombre""")
    rows = c.fetchall()
    conn.close()
    return jsonify({'items': [{'material_id': r[0], 'material_nombre': r[1],
                                'entradas': round(r[2] or 0, 2), 'salidas': round(r[3] or 0, 2),
                                'stock_actual': round(r[4] or 0, 2)} for r in rows]})

@app.route('/api/formulas', methods=['GET', 'POST'])
def handle_formulas():
    conn = get_conn()
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
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM formula_items WHERE producto_nombre=?', (producto_nombre,))
    c.execute('DELETE FROM formula_headers WHERE producto_nombre=?', (producto_nombre,))
    conn.commit()
    conn.close()
    return jsonify({'message': f'Formula {producto_nombre} eliminada'})

@app.route('/api/movimientos', methods=['GET', 'POST'])
def handle_movimientos():
    conn = get_conn()
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        c.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, observaciones, lote, fecha_vencimiento, estanteria, posicion, proveedor, estado_lote) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (data['material_id'], data['material_nombre'], data['cantidad'],
                   data['tipo'], datetime.now().isoformat(), data.get('observaciones',''),
                   data.get('lote',''), data.get('fecha_vencimiento',''),
                   data.get('estanteria',''), data.get('posicion',''),
                   data.get('proveedor',''), data.get('estado_lote','VIGENTE')))
        conn.commit(); conn.close()
        return jsonify({'message': 'Movimiento registrado exitosamente'}), 201
    c.execute('SELECT material_nombre, cantidad, tipo, fecha, observaciones FROM movimientos ORDER BY fecha DESC LIMIT 200')
    movimientos = [{'material_nombre': r[0], 'cantidad': r[1], 'tipo': r[2], 'fecha': r[3], 'observaciones': r[4]} for r in c.fetchall()]
    conn.close()
    return jsonify({'movimientos': movimientos})

@app.route('/api/produccion', methods=['GET', 'POST'])
def handle_produccion():
    conn = get_conn()
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        producto = data['producto']
        cantidad_kg = float(data['cantidad'])
        cantidad_g = cantidad_kg * 1000
        fecha = datetime.now().isoformat()
        c.execute('INSERT INTO producciones (producto, cantidad, fecha, estado, observaciones) VALUES (?,?,?,?,?)',
                  (producto, cantidad_kg, fecha, 'Completado', data.get('observaciones', '')))
        c.execute('SELECT material_id, material_nombre, porcentaje FROM formula_items WHERE producto_nombre=?', (producto,))
        formula_items = c.fetchall()
        descuentos = []
        for mat_id, mat_nombre, pct in formula_items:
            g_total = round((pct / 100) * cantidad_g, 2)
            if g_total <= 0: continue
            c.execute("SELECT lote, SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock FROM movimientos WHERE material_id=? AND lote IS NOT NULL AND lote!='' AND lote!='S/L' GROUP BY lote HAVING stock > 0 ORDER BY CASE WHEN fecha_vencimiento IS NULL OR fecha_vencimiento='' THEN '9999' ELSE fecha_vencimiento END ASC", (mat_id,))
            lotes_disp = c.fetchall()
            g_rest = g_total; lotes_usados = []
            for lr in lotes_disp:
                if g_rest <= 0: break
                lote_n, lote_s = lr[0], lr[1]
                g_lote = min(g_rest, lote_s)
                c.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, observaciones, lote) VALUES (?,?,?,?,?,?,?)",
                          (mat_id, mat_nombre, g_lote, 'Salida', fecha, f'Produccion: {producto} x {cantidad_kg}kg FEFO', lote_n))
                lotes_usados.append(f"{lote_n}:{g_lote}g"); g_rest -= g_lote
            if g_rest > 0:
                c.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, observaciones) VALUES (?,?,?,?,?,?)",
                          (mat_id, mat_nombre, g_rest, 'Salida', fecha, f'Produccion: {producto} x {cantidad_kg}kg'))
            descuentos.append({'material': mat_nombre, 'cantidad_g': g_total, 'lotes': lotes_usados})
        conn.commit()
        conn.close()
        msg = f'Produccion registrada: {producto} x {cantidad_kg}kg'
        if descuentos:
            msg += f'. {len(descuentos)} MPs descontadas automaticamente.'
        return jsonify({'message': msg, 'descuentos': descuentos}), 201
    c.execute('SELECT producto, cantidad, fecha, estado FROM producciones ORDER BY fecha DESC LIMIT 50')
    prod = [{'producto': r[0], 'cantidad': r[1], 'fecha': r[2], 'estado': r[3]} for r in c.fetchall()]
    conn.close()
    return jsonify({'producciones': prod})

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    data = request.json
    try:
        client = get_anthropic_client()
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022", max_tokens=1024,
            messages=[{"role": "user", "content": f"Eres asesor experto en gestion de inventarios para manufactura cosmetica. Responde brevemente en espanol. Pregunta: {data.get('message', '')}"}]
        )
        return jsonify({'response': response.content[0].text})
    except Exception as e:
        return jsonify({'response': f'Error: {str(e)}'}), 500

@app.route('/api/analisis-abc')
def get_analisis_abc():
    conn = get_conn()
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
    conn = get_conn()
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


@app.route('/api/stock')
def get_stock():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT material_id, material_nombre, SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE 0 END), SUM(CASE WHEN tipo='Salida' THEN cantidad ELSE 0 END), SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) FROM movimientos GROUP BY material_id, material_nombre ORDER BY material_nombre")
    rows = c.fetchall(); conn.close()
    return jsonify({'items': [{'material_id':r[0],'material_nombre':r[1],'entradas':round(r[2] or 0,2),'salidas':round(r[3] or 0,2),'stock_actual':round(r[4] or 0,2)} for r in rows]})

@app.route('/api/lotes')
def get_lotes():
    from datetime import date; hoy = date.today().isoformat()
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT material_id, material_nombre, lote, cantidad, fecha_vencimiento, estanteria, posicion, proveedor, estado_lote FROM movimientos WHERE tipo='Entrada' ORDER BY material_nombre ASC, fecha_vencimiento ASC")
    rows = c.fetchall(); conn.close()
    result = []
    for r in rows:
        mid,mnm,lote,cant,fvenc,est,pos,prov,estado = r
        dias,alerta = None,'ok'
        if fvenc and len(str(fvenc)) >= 10:
            try:
                from datetime import datetime as dt2
                dias = (dt2.strptime(str(fvenc)[:10],'%Y-%m-%d').date() - dt2.strptime(hoy,'%Y-%m-%d').date()).days
                alerta = 'vencido' if dias < 0 else ('critico' if dias <= 30 else ('proximo' if dias <= 90 else 'ok'))
            except: pass
        result.append({'material_id':mid or '','material_nombre':mnm or '','lote':lote or '','cantidad_g':round(cant or 0,2),'cantidad_kg':round((cant or 0)/1000,3),'fecha_vencimiento':str(fvenc)[:10] if fvenc else '','dias_para_vencer':dias,'estanteria':est or '','posicion':pos or '','proveedor':prov or '','estado_lote':estado or '','alerta':alerta})
    return jsonify({'lotes': result, 'total': len(result)})

@app.route('/api/maestro-mps', methods=['GET','POST'])
def handle_maestro():
    conn = get_conn(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json
        c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, tipo, proveedor, stock_minimo) VALUES (?,?,?,?,?,?)",
                  (d['codigo_mp'],d.get('nombre_inci',''),d.get('nombre_comercial',''),d.get('tipo',''),d.get('proveedor',''),d.get('stock_minimo',0)))
        conn.commit(); conn.close()
        return jsonify({'message': 'MP guardada'}), 201
    c.execute("SELECT codigo_mp, nombre_inci, nombre_comercial, tipo, proveedor, stock_minimo FROM maestro_mps WHERE activo=1 ORDER BY nombre_comercial")
    rows = c.fetchall(); conn.close()
    return jsonify({'mps': [{'codigo_mp':r[0],'nombre_inci':r[1],'nombre_comercial':r[2],'tipo':r[3],'proveedor':r[4],'stock_minimo':r[5]} for r in rows]})

@app.route('/api/maestro-mps/<codigo>')
def get_mp(codigo):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT codigo_mp, nombre_inci, nombre_comercial, tipo, proveedor, stock_minimo FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    r = c.fetchone(); conn.close()
    return jsonify({'codigo_mp':r[0],'nombre_inci':r[1],'nombre_comercial':r[2],'tipo':r[3],'proveedor':r[4],'stock_minimo':r[5]}) if r else (jsonify({'error':'not found'}),404)

@app.route('/api/recepcion', methods=['POST'])
def registrar_recepcion():
    d = request.json; codigo = d.get('codigo_mp','')
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT nombre_comercial, proveedor FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    mp = c.fetchone()
    nombre = mp[0] if mp else d.get('nombre_comercial', codigo)
    proveedor = mp[1] if mp else d.get('proveedor','')
    lote = d.get('lote','') or f"ESP{datetime.now().strftime('%y%m%d')}{codigo[-3:]}"
    c.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, observaciones, lote, fecha_vencimiento, estanteria, posicion, proveedor, estado_lote) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
              (codigo, nombre, float(d.get('cantidad',0)), 'Entrada', datetime.now().isoformat(), d.get('observaciones','Recepcion'), lote, d.get('fecha_vencimiento',''), d.get('estanteria',''), d.get('posicion',''), proveedor, 'VIGENTE'))
    conn.commit(); conn.close()
    return jsonify({'message': f'MP {nombre} recibida. Lote: {lote}', 'lote': lote}), 201

@app.route('/api/ordenes-compra', methods=['GET','POST'])
def handle_oc():
    conn = get_conn(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json
        c.execute("SELECT COUNT(*) FROM ordenes_compra"); num = (c.fetchone()[0] or 0) + 1
        numero_oc = f"OC-{datetime.now().strftime('%Y')}-{num:04d}"
        c.execute("INSERT INTO ordenes_compra (numero_oc, fecha, estado, proveedor, observaciones) VALUES (?,?,?,?,?)",
                  (numero_oc, datetime.now().isoformat(), 'Pendiente', d.get('proveedor',''), d.get('observaciones','')))
        for item in d.get('items',[]):
            c.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_solicitada, unidad) VALUES (?,?,?,?,?)",
                      (numero_oc, item['codigo_mp'], item['nombre_mp'], item['cantidad_solicitada'], item.get('unidad','g')))
        conn.commit(); conn.close()
        return jsonify({'message': f'OC {numero_oc} creada', 'numero_oc': numero_oc}), 201
    c.execute("SELECT numero_oc, fecha, estado, proveedor FROM ordenes_compra ORDER BY fecha DESC LIMIT 50")
    ocs = []
    for oc in c.fetchall():
        c.execute("SELECT codigo_mp, nombre_mp, cantidad_solicitada, unidad FROM ordenes_compra_items WHERE numero_oc=?", (oc[0],))
        items = [{'codigo_mp':r[0],'nombre_mp':r[1],'cantidad':r[2],'unidad':r[3]} for r in c.fetchall()]
        ocs.append({'numero_oc':oc[0],'fecha':oc[1],'estado':oc[2],'proveedor':oc[3],'items':items})
    conn.close()
    return jsonify({'ordenes': ocs})

@app.route('/api/ordenes-compra/<numero_oc>/recibir', methods=['POST'])
def recibir_oc(numero_oc):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE ordenes_compra SET estado='Recibida' WHERE numero_oc=?", (numero_oc,))
    conn.commit(); conn.close()
    return jsonify({'message': 'OC recibida'})

@app.route('/api/reset-movimientos', methods=['POST'])
def reset_mov():
    conn = get_conn(); c = conn.cursor()
    c.execute("DELETE FROM movimientos"); conn.commit()
    c.execute("SELECT COUNT(*) FROM movimientos"); n = c.fetchone()[0]; conn.close()
    return jsonify({'message': 'Borrado', 'restantes': n})

@app.route('/rotulos/<producto_nombre>/<float:cantidad_kg>')
def generar_rotulos(producto_nombre, cantidad_kg):
    from datetime import date; import urllib.parse
    hoy = date.today().strftime('%d-%b-%Y').upper()
    prod = urllib.parse.unquote(producto_nombre)
    op_num = "OP-" + date.today().strftime('%Y%m%d')
    cant_g = cantidad_kg * 1000
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT material_id, material_nombre, porcentaje FROM formula_items WHERE producto_nombre=?", (prod,))
    items = c.fetchall()
    lotes = {}
    for r in items:
        mid = r[0]
        c.execute("SELECT lote, estanteria, posicion, fecha_vencimiento FROM movimientos WHERE material_id=? AND tipo='Entrada' AND lote IS NOT NULL AND lote!='' AND lote!='S/L' ORDER BY fecha_vencimiento ASC LIMIT 1", (mid,))
        row = c.fetchone()
        lotes[mid] = {'lote': row[0] if row else 'S/L', 'est': row[1] if row else '', 'pos': row[2] if row else '', 'vence': str(row[3])[:10] if row and row[3] else ''}
    conn.close()
    if not items: return '<h2>Formula no encontrada</h2>', 404
    rhtml = ''
    for i, r in enumerate(items):
        mid, mnm, pct = r; peso = round((pct/100)*cant_g, 2)
        info = lotes.get(mid, {}); lote_mp = info.get('lote','S/L')
        ubicacion = ('Est. ' + str(info.get('est','')) + str(info.get('pos',''))).strip()
        vence = info.get('vence','')
        rhtml += '<div class="r"><div class="rh"><span class="rt">ROTULO MATERIA PRIMA DISPENSADA</span><span class="rc">PRD-PRO-001-F08 | v1<br>04-Mar-2025 / 03-Mar-2028</span></div>'
        rhtml += '<table><tr><td class="l">OP:</td><td class="v">' + op_num + '</td><td class="l">Fecha:</td><td class="v">' + hoy + '</td></tr>'
        rhtml += '<tr><td class="l">Producto:</td><td class="v big" colspan="3"><b>' + prod + '</b> &mdash; ' + str(cantidad_kg) + ' kg</td></tr>'
        rhtml += '<tr><td class="l">MP:</td><td class="v bold" colspan="3"><b>' + mnm + '</b> (' + mid + ')</td></tr>'
        rhtml += '<tr><td class="l">Lote:</td><td class="v bold">' + lote_mp + '</td><td class="l">Ubicacion:</td><td class="v">' + ubicacion + '</td></tr>'
        rhtml += '<tr><td class="l">Vence:</td><td class="v" style="color:#c0392b;">' + vence + '</td><td class="l">% formula:</td><td class="v">' + str(pct) + '%</td></tr>'
        rhtml += '<tr><td class="l">Peso teorico:</td><td class="v peso">' + f"{peso:,.2f} g" + '</td><td class="l">Lote Prod.:</td><td class="blank"></td></tr>'
        rhtml += '<tr><td class="l">Tara:</td><td class="blank"></td><td class="l">Peso Neto:</td><td class="blank"></td></tr>'
        rhtml += '<tr><td class="l">Pesado por:</td><td class="blank firma"></td><td class="l">Verificado:</td><td class="blank firma"></td></tr>'
        rhtml += '</table><div class="rf">FEFO | #' + str(i+1) + ' de ' + str(len(items)) + '</div></div>'
    css = '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Rotulos</title><style>*{margin:0;padding:0;box-sizing:border-box;}body{font-family:Arial,sans-serif;font-size:9pt;background:#eee;}.ph{background:#1a252f;color:white;padding:10px 16px;display:flex;justify-content:space-between;align-items:center;}.pbtn{background:#27ae60;color:white;border:none;padding:7px 18px;border-radius:4px;cursor:pointer;font-weight:bold;}.wrap{display:flex;flex-wrap:wrap;gap:5px;padding:8px;}.r{background:white;border:2px solid #1a252f;border-radius:3px;width:370px;page-break-inside:avoid;}.rh{background:#1a252f;color:white;padding:5px 8px;display:flex;justify-content:space-between;align-items:center;}.rt{font-weight:bold;font-size:8pt;}.rc{font-size:6.5pt;text-align:right;line-height:1.4;}table{width:100%;border-collapse:collapse;}td{border:1px solid #bbb;padding:3px 5px;vertical-align:middle;}.l{background:#ecf0f1;font-weight:bold;font-size:7.5pt;color:#1a252f;white-space:nowrap;width:27%;}.v{font-size:8.5pt;width:23%;}.bold{font-size:9pt;}.big{font-size:9pt;}.peso{background:#fff3cd;color:#c0392b;font-size:12pt;font-weight:bold;}.blank{height:20px;width:23%;}.firma{height:26px;}.rf{background:#ecf0f1;padding:2px 6px;font-size:6.5pt;color:#888;text-align:right;}@media print{body{background:white;}.ph{display:none;}.wrap{padding:0;gap:3px;}.r{width:48%;}@page{size:letter landscape;margin:7mm;}}</style></head><body>'
    return css + '<div class="ph"><div><h2>Rotulos FEFO &mdash; ' + prod + ' &mdash; ' + str(cantidad_kg) + ' kg</h2><div style="font-size:8pt;opacity:0.8;">' + op_num + ' | ' + str(len(items)) + ' MPs | ' + hoy + '</div></div><button class="pbtn" onclick="window.print()">Imprimir todos</button></div><div class="wrap">' + rhtml + '</div></body></html>'


@app.route('/api/alertas-reabastecimiento')
def alertas_reabas():
    conn = get_conn(); c = conn.cursor()
    c.execute("""SELECT m.codigo_mp, m.nombre_comercial, m.proveedor, m.stock_minimo,
                        COALESCE(s.stock_actual, 0) as stock_actual
                 FROM maestro_mps m
                 LEFT JOIN (SELECT material_id, SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock_actual FROM movimientos GROUP BY material_id) s
                 ON m.codigo_mp = s.material_id
                 WHERE m.activo=1 AND m.stock_minimo > 0 AND COALESCE(s.stock_actual,0) < m.stock_minimo
                 ORDER BY (m.stock_minimo - COALESCE(s.stock_actual,0)) DESC""")
    rows = c.fetchall(); conn.close()
    return jsonify({'alertas': [{'codigo_mp':r[0],'nombre':r[1],'proveedor':r[2],'stock_minimo':r[3],'stock_actual':round(r[4],2),'deficit':round(r[3]-r[4],2)} for r in rows]})

@app.route('/rotulo-recepcion/<codigo_mp>/<lote>/<float:cantidad_g>')
def rotulo_recepcion(codigo_mp, lote, cantidad_g):
    from datetime import date; import urllib.parse
    hoy = date.today().strftime('%d-%b-%Y').upper()
    lote = urllib.parse.unquote(lote)
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT nombre_inci, nombre_comercial, tipo, proveedor FROM maestro_mps WHERE codigo_mp=?", (codigo_mp,))
    mp = c.fetchone()
    c.execute("SELECT fecha_vencimiento, estanteria, posicion FROM movimientos WHERE material_id=? AND lote=? ORDER BY fecha DESC LIMIT 1", (codigo_mp, lote))
    mov = c.fetchone(); conn.close()
    nc = mp[1] if mp else codigo_mp; ni = mp[0] if mp else ''
    tp = mp[2] if mp else ''; pv = mp[3] if mp else ''
    fv = str(mov[0])[:10] if mov and mov[0] else ''
    ub = ((mov[1] or '') + (mov[2] or '')) if mov else ''
    nr = "REC-" + date.today().strftime('%Y%m%d') + "-" + codigo_mp[-3:]
    html = '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Rotulo Recepcion</title>'
    html += '<style>*{margin:0;padding:0;box-sizing:border-box;}body{font-family:Arial,sans-serif;font-size:10pt;background:#eee;padding:20px;}'
    html += '.r{background:white;border:3px solid #1a252f;border-radius:5px;max-width:500px;margin:auto;}'
    html += '.rh{background:#1a252f;color:white;padding:8px 12px;text-align:center;}'
    html += 'table{width:100%;border-collapse:collapse;}td{border:1px solid #ccc;padding:6px 8px;}'
    html += '.l{background:#ecf0f1;font-weight:bold;font-size:8.5pt;width:35%;}'
    html += '.lote{background:#fff3cd;border:2px solid #f39c12;padding:10px;text-align:center;margin:10px;}'
    html += '.lnum{font-size:20pt;font-weight:bold;color:#c0392b;letter-spacing:2px;}'
    html += '.ph{background:#1a252f;color:white;padding:10px 16px;display:flex;justify-content:space-between;margin-bottom:10px;}'
    html += '.pb{background:#27ae60;color:white;border:none;padding:7px 18px;border-radius:4px;cursor:pointer;font-weight:bold;}'
    html += '@media print{.ph{display:none;}body{background:white;padding:0;}}</style></head><body>'
    html += '<div class="ph"><div><b>Rotulo de Recepcion</b></div><button class="pb" onclick="window.print()">Imprimir</button></div>'
    html += '<div class="r"><div class="rh"><span style="font-weight:bold;font-size:11pt;display:block;margin-bottom:3px;">ROTULO DE INGRESO DE MATERIA PRIMA</span>'
    html += '<span style="font-size:7.5pt;opacity:0.8;">Espagiria Laboratorios | PRD-REC-001 | ' + hoy + '</span></div>'
    html += '<div class="lote"><div style="font-size:9pt;color:#888;margin-bottom:4px;">NUMERO DE LOTE</div>'
    html += '<div class="lnum">' + lote + '</div></div><table>'
    html += '<tr><td class="l">Codigo MP:</td><td style="font-weight:700;">' + codigo_mp + '</td></tr>'
    html += '<tr><td class="l">Nombre INCI:</td><td>' + ni + '</td></tr>'
    html += '<tr><td class="l">Nombre Comercial:</td><td style="font-weight:700;">' + nc + '</td></tr>'
    html += '<tr><td class="l">Tipo:</td><td>' + tp + '</td></tr>'
    html += '<tr><td class="l">Proveedor:</td><td style="font-weight:700;">' + pv + '</td></tr>'
    html += '<tr><td class="l">Cantidad:</td><td style="color:#27ae60;font-weight:700;">' + f"{cantidad_g:,.0f} g = {cantidad_g/1000:.3f} kg" + '</td></tr>'
    html += '<tr><td class="l">Vencimiento:</td><td style="color:#c0392b;font-weight:700;">' + fv + '</td></tr>'
    html += '<tr><td class="l">Ubicacion:</td><td>Est. ' + ub + '</td></tr>'
    html += '<tr><td class="l">N Recepcion:</td><td>' + nr + '</td></tr>'
    html += '<tr><td class="l">Recibido por:</td><td style="height:30px;"></td></tr>'
    html += '<tr><td class="l">Verificado por:</td><td style="height:30px;"></td></tr></table>'
    html += '<div style="background:#ecf0f1;padding:4px 10px;font-size:7.5pt;color:#888;text-align:center;">Ingreso registrado | ' + hoy + '</div></div></body></html>'
    return html

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
