# Auto-extraído de index.py — Fase A refactor
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
  <a href="/hub" style="color:#fff;text-decoration:none;font-size:13px;font-weight:700;margin-right:8px;background:rgba(255,255,255,0.15);padding:5px 12px;border-radius:6px;border:1px solid rgba(255,255,255,0.3);">&#x1F3E0; Panel Central</a>
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
      h+='<td style="padding:8px 6px;"><button onclick="guardarPrecio(\\''+s.sku+'\\')" style="padding:5px 12px;background:#2B7A78;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:0.82em;font-weight:600;">Guardar</button></td>';
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

async function buscarTrazabilidadPT(){
  var lote=(document.getElementById('trz-lote-pt')||{}).value||'';
  lote=lote.trim();
  if(!lote){alert('Ingresa un numero de lote PT (ej: PROD-00001)');return;}
  var div=document.getElementById('trz-result');
  if(!div)return;
  div.innerHTML='<p style="color:#888;font-size:0.9em;">Buscando...</p>';
  try{
    var r=await fetch('/api/trazabilidad/lote-pt/'+encodeURIComponent(lote));
    var d=await r.json();
    if(d.error){div.innerHTML='<div style="color:#e74c3c;padding:12px;background:#ffeaea;border-radius:8px;">'+d.error+'</div>';return;}
    var html='<div style="background:#f8f9ff;border:1px solid #c3cfe2;border-radius:10px;padding:16px;margin-bottom:12px;">';
    html+='<h4 style="margin:0 0 10px;color:#6c5ce7;">&#128203; Lote PT: '+d.lote_ref+'</h4>';
    if(d.produccion){
      var p=d.produccion;
      html+='<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;font-size:0.88em;margin-bottom:12px;">';
      html+='<div><b>Producto:</b> '+(p.producto||'&#8212;')+'</div>';
      html+='<div><b>Cantidad:</b> '+(p.cantidad_kg?Number(p.cantidad_kg).toFixed(2)+' kg':'&#8212;')+'</div>';
      html+='<div><b>Fecha:</b> '+(p.fecha?p.fecha.substring(0,10):'&#8212;')+'</div>';
      html+='<div><b>Operador:</b> '+(p.operador||'&#8212;')+'</div>';
      html+='</div>';
    }
    var mps=d.mps_consumidas||[];
    html+='<h5 style="margin:0 0 8px;color:#2B7A78;">Materias Primas Consumidas ('+mps.length+')</h5>';
    if(mps.length){
      html+='<table style="width:100%;font-size:0.82em;border-collapse:collapse;">';
      html+='<thead><tr style="background:#f0f0f0;"><th style="padding:4px 8px;text-align:left;">Lote MP</th><th style="padding:4px 8px;text-align:left;">Material</th><th style="padding:4px 8px;text-align:right;">Cant (g)</th><th style="padding:4px 8px;text-align:left;">Proveedor</th><th style="padding:4px 8px;text-align:left;">Vence</th></tr></thead><tbody>';
      var det=d.detalle_lotes_mp||{};
      mps.forEach(function(m){
        var info=det[m.lote]||{};
        html+='<tr style="border-bottom:1px solid #eee;"><td style="padding:4px 8px;font-family:monospace;font-size:0.9em;">'+m.lote+'</td><td style="padding:4px 8px;">'+(m.material||'&#8212;')+'</td><td style="padding:4px 8px;text-align:right;">'+Number(m.cantidad_g||0).toLocaleString()+'</td><td style="padding:4px 8px;">'+(info.proveedor||'&#8212;')+'</td><td style="padding:4px 8px;">'+(info.vencimiento?info.vencimiento.substring(0,10):'&#8212;')+'</td></tr>';
      });
      html+='</tbody></table>';
    } else {
      html+='<p style="color:#999;font-size:0.85em;">No se encontraron lotes MP asociados (la produccion puede no tener lote asignado aun).</p>';
    }
    var desp=d.despachos||[];
    if(desp.length){
      html+='<h5 style="margin:12px 0 8px;color:#e17055;">Despachos a Clientes ('+desp.length+')</h5>';
      html+='<table style="width:100%;font-size:0.82em;border-collapse:collapse;"><thead><tr style="background:#fff3f0;"><th style="padding:4px 8px;text-align:left;">Fecha</th><th style="padding:4px 8px;text-align:left;">Cliente</th><th style="padding:4px 8px;text-align:right;">Cantidad</th><th style="padding:4px 8px;text-align:left;">Remision</th></tr></thead><tbody>';
      desp.forEach(function(ds){
        html+='<tr style="border-bottom:1px solid #fee;"><td style="padding:4px 8px;">'+(ds.fecha?ds.fecha.substring(0,10):'&#8212;')+'</td><td style="padding:4px 8px;">'+(ds.cliente||'&#8212;')+'</td><td style="padding:4px 8px;text-align:right;">'+(ds.cantidad||'&#8212;')+'</td><td style="padding:4px 8px;">'+(ds.remision||'&#8212;')+'</td></tr>';
      });
      html+='</tbody></table>';
    }
    html+='</div>';
    div.innerHTML=html;
  }catch(e){div.innerHTML='<div style="color:#e74c3c;padding:12px;background:#ffeaea;border-radius:8px;">Error: '+e.message+'</div>';}
}

async function buscarTrazabilidadMP(){
  var lote=(document.getElementById('trz-lote-mp')||{}).value||'';
  lote=lote.trim();
  if(!lote){alert('Ingresa un numero de lote MP (ej: ESP240115MP1)');return;}
  var div=document.getElementById('trz-result');
  if(!div)return;
  div.innerHTML='<p style="color:#888;font-size:0.9em;">Buscando...</p>';
  try{
    var r=await fetch('/api/trazabilidad/lote-mp/'+encodeURIComponent(lote));
    var d=await r.json();
    if(d.error){div.innerHTML='<div style="color:#e74c3c;padding:12px;background:#ffeaea;border-radius:8px;">'+d.error+'</div>';return;}
    var html='<div style="background:#f8fff8;border:1px solid #c3e2cf;border-radius:10px;padding:16px;margin-bottom:12px;">';
    html+='<h4 style="margin:0 0 10px;color:#00b894;">&#128203; Lote MP: '+d.lote_mp+'</h4>';
    if(d.material){
      var mat=d.material;
      html+='<div style="font-size:0.88em;margin-bottom:12px;"><b>Material:</b> '+(mat.nombre||d.lote_mp)+' <span style="color:#888;">('+d.lote_mp+')</span>';
      if(mat.proveedor) html+=' | <b>Proveedor:</b> '+mat.proveedor;
      if(mat.fecha_ingreso) html+=' | <b>Ingreso:</b> '+mat.fecha_ingreso.substring(0,10);
      html+='</div>';
    }
    var prods=d.producciones||[];
    html+='<h5 style="margin:0 0 8px;color:#6c5ce7;">Producciones donde se uso ('+prods.length+')</h5>';
    if(prods.length){
      html+='<table style="width:100%;font-size:0.82em;border-collapse:collapse;"><thead><tr style="background:#f0f0f8;"><th style="padding:4px 8px;text-align:left;">Lote PT</th><th style="padding:4px 8px;text-align:left;">Producto</th><th style="padding:4px 8px;text-align:left;">Fecha</th><th style="padding:4px 8px;text-align:right;">Cant (g)</th></tr></thead><tbody>';
      prods.forEach(function(p){
        html+='<tr style="border-bottom:1px solid #eee;"><td style="padding:4px 8px;font-family:monospace;font-size:0.9em;">'+(p.lote_ref||'&#8212;')+'</td><td style="padding:4px 8px;">'+(p.producto||'&#8212;')+'</td><td style="padding:4px 8px;">'+(p.fecha?p.fecha.substring(0,10):'&#8212;')+'</td><td style="padding:4px 8px;text-align:right;">'+Number(p.cantidad_g||0).toLocaleString()+'</td></tr>';
      });
      html+='</tbody></table>';
    } else {
      html+='<p style="color:#999;font-size:0.85em;">No se encontraron producciones para este lote.</p>';
    }
    var clientes=d.clientes_afectados||[];
    if(clientes.length){
      html+='<h5 style="margin:12px 0 8px;color:#e17055;">Clientes que recibieron este material ('+clientes.length+')</h5>';
      html+='<table style="width:100%;font-size:0.82em;border-collapse:collapse;"><thead><tr style="background:#fff3f0;"><th style="padding:4px 8px;text-align:left;">Cliente</th><th style="padding:4px 8px;text-align:left;">Lote PT</th><th style="padding:4px 8px;text-align:left;">Producto</th><th style="padding:4px 8px;text-align:left;">Fecha</th></tr></thead><tbody>';
      clientes.forEach(function(cl){
        html+='<tr style="border-bottom:1px solid #fee;"><td style="padding:4px 8px;">'+(cl.cliente||'&#8212;')+'</td><td style="padding:4px 8px;font-family:monospace;font-size:0.9em;">'+(cl.lote_ref||'&#8212;')+'</td><td style="padding:4px 8px;">'+(cl.producto||'&#8212;')+'</td><td style="padding:4px 8px;">'+(cl.fecha?cl.fecha.substring(0,10):'&#8212;')+'</td></tr>';
      });
      html+='</tbody></table>';
    }
    html+='</div>';
    div.innerHTML=html;
  }catch(e){div.innerHTML='<div style="color:#e74c3c;padding:12px;background:#ffeaea;border-radius:8px;">Error: '+e.message+'</div>';}
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
