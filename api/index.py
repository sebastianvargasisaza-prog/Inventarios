import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string
from anthropic import Anthropic
import pandas as pd

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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS movimientos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  material_id TEXT, material_nombre TEXT, cantidad REAL,
                  tipo TEXT, fecha TEXT, observaciones TEXT,
                  lote TEXT, fecha_vencimiento TEXT, estanteria TEXT,
                  posicion TEXT, proveedor TEXT, estado_lote TEXT)""")
    # Agregar columnas nuevas si no existen (migracion segura)
    nuevas_cols = [
        ("lote", "TEXT"), ("fecha_vencimiento", "TEXT"), ("estanteria", "TEXT"),
        ("posicion", "TEXT"), ("proveedor", "TEXT"), ("estado_lote", "TEXT")
    ]
    for col, tipo in nuevas_cols:
        try:
            c.execute(f"ALTER TABLE movimientos ADD COLUMN {col} {tipo}")
        except Exception:
            pass  # columna ya existe
    c.execute("""CREATE TABLE IF NOT EXISTS producciones
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  producto TEXT, cantidad REAL, fecha TEXT, estado TEXT, observaciones TEXT)""")
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
    conn.commit()
    conn.close()

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
      <input type="text" id="stock-search" placeholder="Buscar MP, lote, proveedor..." oninput="filterStock()" style="width:220px;margin-top:0;">
      <select id="stock-estanteria" onchange="filterStock()" style="width:140px;padding:9px;border:1px solid #ddd;border-radius:6px;margin-top:0;"><option value="">Todas estanterias</option></select>
      <select id="stock-estado" onchange="filterStock()" style="width:140px;padding:9px;border:1px solid #ddd;border-radius:6px;margin-top:0;">
        <option value="">Todos estados</option>
        <option value="vencido">Vencido</option>
        <option value="critico">Critico menos 30d</option>
        <option value="proximo">Proximo menos 90d</option>
        <option value="ok">Vigente</option>
      </select>
      <button onclick="loadStock()">&#8635; Actualizar</button>
      <span id="stock-count" style="color:#888;font-size:0.88em;"></span>
    </div>
    <div style="overflow-x:auto;">
    <table class="table">
      <thead><tr>
        <th>Codigo MP</th><th>Material</th><th>Lote</th>
        <th>Proveedor</th><th style="text-align:center;">Est.</th><th style="text-align:center;">Pos.</th>
        <th style="text-align:right;">g</th><th style="text-align:right;">kg</th>
        <th style="text-align:center;">Vence</th><th style="text-align:center;">Estado</th>
      </tr></thead>
      <tbody id="stock-body"><tr><td colspan="10" style="text-align:center;color:#999;padding:20px;">Cargando...</td></tr></tbody>
    </table>
    </div>
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
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:5px;">
      <button onclick="registrarProd()">&#9989; Registrar Produccion</button>
      <button onclick="generarRotulos()" style="background:#c0392b;" id="btn-rotulos" disabled>&#128209; Generar Rotulos</button>
    </div>
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
var fData=[], allStock=[], allLotes=[];

function switchTab(n,btn){
  document.querySelectorAll('.tab-content').forEach(function(t){t.classList.remove('active');});
  document.querySelectorAll('.tab-button').forEach(function(b){b.classList.remove('active');});
  var el=document.getElementById(n);
  if(el){ el.classList.add('active'); }
  if(btn){ btn.classList.add('active'); }
  if(n==='stock'){ loadStock(); }
  else if(n==='formulas'){ loadFormulas(); }
  else if(n==='produccion'){ loadFormulas(); }
  else if(n==='abc'){ loadABC(); }
  else if(n==='alertas'){ loadAlertas(); }
  else if(n==='movimientos'){ loadMovimientos(); }
}

async function loadDashboard(){
  ['stock-total','materiales-count','alertas-count','producciones-count'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.textContent='...';
  });
  try{
    var r=await fetch('/api/inventario'), d=await r.json();
    document.getElementById('stock-total').textContent=((d.stock_total||0)/1000).toFixed(1)+' kg';
    document.getElementById('materiales-count').textContent=d.movimientos||'0';
    document.getElementById('alertas-count').textContent=d.alertas||'0';
    document.getElementById('producciones-count').textContent=d.producciones||'0';
  }catch(e){
    ['stock-total','materiales-count','alertas-count','producciones-count'].forEach(function(id){
      var el=document.getElementById(id); if(el) el.textContent='ERR';
    });
    console.error('loadDashboard error:',e);
  }
}

async function loadStock(){
  try{
    var r=await fetch('/api/stock'), d=await r.json();
    allStock=d.items||[];
    document.getElementById('stock-count').textContent=allStock.length+' materiales';
    renderStock(allStock);
  }catch(e){document.getElementById('stock-body').innerHTML='<tr><td colspan="6">Error</td></tr>';}
}

function renderStock(items){
  var tb=document.getElementById('stock-body');
  if(!items.length){tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:#999;padding:20px;">Sin datos</td></tr>';return;}
  tb.innerHTML=items.map(function(i){
    var c=i.stock_actual<=0?'color:#cc0000;font-weight:700;':i.stock_actual<500?'color:#e68a00;font-weight:700;':'color:#1a8a1a;font-weight:700;';
    return '<tr>'
      +'<td style="font-family:monospace;font-size:0.83em;color:#555;">'+i.material_id+'</td>'
      +'<td>'+i.material_nombre+'</td>'
      +'<td style="text-align:right;">'+i.entradas.toLocaleString()+'</td>'
      +'<td style="text-align:right;color:#cc4444;">'+i.salidas.toLocaleString()+'</td>'
      +'<td style="text-align:right;'+c+'">'+i.stock_actual.toLocaleString()+'</td>'
      +'<td style="text-align:right;color:#888;">'+(i.stock_actual/1000).toFixed(3)+'</td>'
      +'</tr>';
  }).join('');
}

function filterStock(){
  var q=document.getElementById('stock-search').value.toLowerCase();
  renderStock(allStock.filter(function(i){return i.material_nombre.toLowerCase().includes(q)||i.material_id.toLowerCase().includes(q);}));
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
  c.innerHTML=fl.map(function(f,idx){
    var total=f.items.reduce(function(s,i){return s+i.porcentaje;},0);
    return '<div style="border:1px solid #dde;border-radius:8px;padding:15px;margin-bottom:12px;background:white;">'
      +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
      +'<h4 style="color:#667eea;">'+f.producto_nombre+' <span style="font-weight:normal;color:#888;font-size:0.82em;">(base '+f.unidad_base_g+'g)</span></h4>'
      +'<div style="display:flex;gap:6px;">'
      +'<button onclick="editFormula("+idx+")" style="background:#667eea;padding:5px 10px;font-size:0.82em;">Editar</button>'
      +'<button onclick="delFormula("+idx+")" style="background:#cc4444;padding:5px 10px;font-size:0.82em;">Eliminar</button>'
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

function editFormula(idx){
  var f=fData[idx];
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

window.onload=function(){try{loadDashboard();}catch(e){console.error(e);} try{loadFormulas();}catch(e){console.error(e);}  };
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML)

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

@app.route('/api/stock')
def get_stock():
    """Vista consolidada por material (para dashboard)"""
    conn = sqlite3.connect(DB_PATH)
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

@app.route('/api/lotes')
def get_lotes():
    """Vista por lote individual con ubicacion, vencimiento y proveedor"""
    from datetime import date
    hoy = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT material_id, material_nombre, lote, cantidad, fecha_vencimiento,
                        estanteria, posicion, proveedor, estado_lote, fecha
                 FROM movimientos
                 WHERE tipo='Entrada'
                 ORDER BY material_nombre ASC, lote ASC""")
    rows = c.fetchall()
    conn.close()
    result = []
    for r in rows:
        mat_id, mat_nom, lote, cant, fvenc, estant, pos, prov, estado, fecha_mov = r
        # Calcular dias para vencer
        dias_venc = None
        alerta = 'ok'
        if fvenc and len(fvenc) >= 10:
            try:
                from datetime import datetime as dt2
                fv = fvenc[:10]
                dias = (dt2.strptime(fv, '%Y-%m-%d').date() - dt2.strptime(hoy, '%Y-%m-%d').date()).days
                dias_venc = dias
                if dias < 0: alerta = 'vencido'
                elif dias <= 30: alerta = 'critico'
                elif dias <= 90: alerta = 'proximo'
            except Exception:
                pass
        result.append({
            'material_id': mat_id or '',
            'material_nombre': mat_nom or '',
            'lote': lote or '',
            'cantidad_g': round(cant or 0, 2),
            'cantidad_kg': round((cant or 0) / 1000, 3),
            'fecha_vencimiento': fvenc[:10] if fvenc and len(fvenc) >= 10 else '',
            'dias_para_vencer': dias_venc,
            'estanteria': estant or '',
            'posicion': pos or '',
            'ubicacion': f"{estant or ''}{pos or ''}".strip(),
            'proveedor': prov or '',
            'estado_lote': estado or '',
            'alerta': alerta
        })
    return jsonify({'lotes': result, 'total': len(result)})

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
                      lote, fecha_vencimiento, estanteria, posicion, proveedor, estado_lote)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (data['material_id'], data['material_nombre'], data['cantidad'],
                   data['tipo'], datetime.now().isoformat(), data.get('observaciones', ''),
                   data.get('lote',''), data.get('fecha_vencimiento',''),
                   data.get('estanteria',''), data.get('posicion',''),
                   data.get('proveedor',''), data.get('estado_lote','VIGENTE')))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Movimiento registrado exitosamente'}), 201
    c.execute("""SELECT material_id, material_nombre, cantidad, tipo, fecha, observaciones,
                        lote, fecha_vencimiento, estanteria, posicion, proveedor, estado_lote
                 FROM movimientos ORDER BY fecha DESC LIMIT 500""")
    movimientos = [{'material_id': r[0], 'material_nombre': r[1], 'cantidad': r[2], 'tipo': r[3],
                    'fecha': r[4], 'observaciones': r[5], 'lote': r[6] or '',
                    'fecha_vencimiento': r[7] or '', 'estanteria': r[8] or '',
                    'posicion': r[9] or '', 'proveedor': r[10] or '',
                    'estado_lote': r[11] or ''} for r in c.fetchall()]
    conn.close()
    return jsonify({'movimientos': movimientos})

@app.route('/api/produccion', methods=['GET', 'POST'])
def handle_produccion():
    conn = sqlite3.connect(DB_PATH)
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
            g = round((pct / 100) * cantidad_g, 2)
            if g > 0:
                c.execute('INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, observaciones) VALUES (?,?,?,?,?,?)',
                          (mat_id, mat_nombre, g, 'Salida', fecha, f'Produccion: {producto} x {cantidad_kg}kg'))
                descuentos.append({'material': mat_nombre, 'cantidad_g': g})
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


@app.route('/api/reset-movimientos', methods=['POST'])
def reset_movimientos():
    """Borra todos los movimientos para recargar limpio"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM movimientos')
    conn.commit()
    c.execute('SELECT COUNT(*) FROM movimientos')
    count = c.fetchone()[0]
    conn.close()
    return jsonify({'message': 'Movimientos borrados', 'restantes': count})


@app.route('/rotulos/<producto_nombre>/<float:cantidad_kg>')
def generar_rotulos(producto_nombre, cantidad_kg):
    from datetime import date
    import urllib.parse
    hoy = date.today().strftime('%d-%b-%Y').upper()
    cantidad_g = cantidad_kg * 1000
    prod = urllib.parse.unquote(producto_nombre)
    op_num = "OP-" + date.today().strftime('%Y%m%d')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT material_id, material_nombre, porcentaje FROM formula_items WHERE producto_nombre=?", (prod,))
    items = c.fetchall()

    lotes = {}
    for mat_id, mat_nom, pct in items:
        c.execute("SELECT lote, estanteria, posicion, proveedor FROM movimientos WHERE material_id=? AND tipo='Entrada' AND lote IS NOT NULL AND lote!='' AND lote!='S/L' ORDER BY fecha DESC LIMIT 1", (mat_id,))
        row = c.fetchone()
        lotes[mat_id] = {"lote": row[0] if row else "S/L", "est": row[1] if row else "", "pos": row[2] if row else "", "prov": row[3] if row else ""}
    conn.close()

    if not items:
        return "<h2>Formula no encontrada: " + prod + "</h2>", 404

    rhtml = ""
    for i, (mat_id, mat_nom, pct) in enumerate(items):
        peso = round((pct / 100) * cantidad_g, 2)
        info = lotes.get(mat_id, {})
        lote_mp = info.get("lote", "")
        ubicacion = ("Est. " + info.get("est","") + info.get("pos","")).strip()
        rhtml += """<div class="r">
  <div class="rh"><span class="rt">ROTULO MATERIA PRIMA DISPENSADA</span><span class="rc">Codigo: PRD-PRO-001-F08 | v1<br>Vigencia: 04-Mar-2025 / 03-Mar-2028</span></div>
  <table><tr>
    <td class="l">OP:</td><td class="v">"""+op_num+"""</td>
    <td class="l">Fecha:</td><td class="v">"""+hoy+"""</td>
  </tr><tr>
    <td class="l">Producto:</td><td class="v big" colspan="3"><b>"""+prod+"""</b> &mdash; """+str(cantidad_kg)+""" kg</td>
  </tr><tr>
    <td class="l">Nombre MP:</td><td class="v bold" colspan="3"><b>"""+mat_nom+"""</b> <span style="color:#888;font-size:0.8em;">("""+mat_id+""")</span></td>
  </tr><tr>
    <td class="l">Lote MP:</td><td class="v bold">"""+lote_mp+"""</td>
    <td class="l">Ubicacion:</td><td class="v">"""+ubicacion+"""</td>
  </tr><tr>
    <td class="l">Peso teorico:</td><td class="v peso">"""+f"{peso:,.2f} g"+"""</td>
    <td class="l">% formula:</td><td class="v">"""+str(pct)+"""%</td>
  </tr><tr>
    <td class="l">Tara:</td><td class="blank"></td>
    <td class="l">Peso Neto:</td><td class="blank"></td>
  </tr><tr>
    <td class="l">Peso Bruto:</td><td class="blank"></td>
    <td class="l">Lote Prod.:</td><td class="blank"></td>
  </tr><tr>
    <td class="l">Pesado por:</td><td class="blank firma"></td>
    <td class="l">Verificado:</td><td class="blank firma"></td>
  </tr></table>
  <div class="rf">MP: Materia Prima &nbsp; | &nbsp; #"""+str(i+1)+""" de """+str(len(items))+"""</div>
</div>"""

    return """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>Rotulos """ + prod + """</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:Arial,sans-serif;font-size:9pt;background:#eee;}
.ph{background:#1a252f;color:white;padding:10px 16px;display:flex;justify-content:space-between;align-items:center;}
.ph h2{font-size:11pt;}
.pbtn{background:#27ae60;color:white;border:none;padding:7px 18px;border-radius:4px;cursor:pointer;font-weight:bold;}
.wrap{display:flex;flex-wrap:wrap;gap:5px;padding:8px;}
.r{background:white;border:2px solid #1a252f;border-radius:3px;width:370px;page-break-inside:avoid;}
.rh{background:#1a252f;color:white;padding:5px 8px;display:flex;justify-content:space-between;align-items:center;}
.rt{font-weight:bold;font-size:8pt;}
.rc{font-size:6.5pt;text-align:right;line-height:1.4;}
table{width:100%;border-collapse:collapse;}
td{border:1px solid #bbb;padding:3px 5px;vertical-align:middle;}
.l{background:#ecf0f1;font-weight:bold;font-size:7.5pt;color:#1a252f;white-space:nowrap;width:27%;}
.v{font-size:8.5pt;width:23%;}
.bold{font-size:9pt;}
.big{font-size:9pt;}
.peso{background:#fff3cd;color:#c0392b;font-size:12pt;font-weight:bold;}
.blank{height:20px;width:23%;}
.firma{height:26px;}
.rf{background:#ecf0f1;padding:2px 6px;font-size:6.5pt;color:#888;text-align:right;}
@media print{
  body{background:white;}
  .ph{display:none;}
  .wrap{padding:0;gap:3px;}
  .r{width:48%;}
  @page{size:letter landscape;margin:7mm;}
}
</style></head><body>
<div class="ph">
  <div><h2>Rotulos de Dispensacion &mdash; """ + prod + """</h2>
  <div style="font-size:8pt;opacity:0.8;">""" + op_num + """ &nbsp;|&nbsp; """ + str(cantidad_kg) + """ kg &nbsp;|&nbsp; """ + str(len(items)) + """ MPs &nbsp;|&nbsp; """ + hoy + """</div></div>
  <button class="pbtn" onclick="window.print()">Imprimir todos</button>
</div>
<div class="wrap">""" + rhtml + """</div></body></html>"""


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
