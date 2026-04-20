# Auto-extraído de index.py — Fase A refactor
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
  <span class="topbar-title">&#x1F91D; MAQUILA 360 &amp; ALIADOS — HHA Group</span>
</div>
<div class="tabs">
  <div class="tab active" onclick="goTab('tab-dash',this)">&#x1F4CA; Dashboard</div>
  <div class="tab" onclick="goTab('tab-clientes',this)">&#x1F3ED; Aliados</div>
  <div class="tab" onclick="goTab('tab-pedidos',this)">&#x1F4CB; Pedidos</div>
  <div class="tab" onclick="goTab('tab-stock',this)">&#x1F4E6; Stock PT</div>
  <div class="tab" onclick="goTab('tab-despachos',this)">&#x1F69A; Despachos</div>
  <div class="tab" onclick="goTab('tab-churn',this)">&#x26A0; Riesgo Churn</div>
  <div class="tab" onclick="window.location='/solicitudes'">&#x1F4CB; Solicitudes</div>
</div>

<div class="content">

<!-- MODAL: Cliente 360 -->
<div id="m-cliente360" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:1000;overflow-y:auto;">
<div style="background:white;border-radius:14px;max-width:820px;margin:32px auto;padding:0;box-shadow:0 20px 60px rgba(0,0,0,0.3);">
  <div style="background:#2B7A78;color:white;padding:16px 20px;border-radius:14px 14px 0 0;display:flex;justify-content:space-between;align-items:center;">
    <strong style="font-size:1em;">&#x1F4CA; Cliente 360</strong>
    <button onclick="document.getElementById('m-cliente360').style.display='none'" style="background:rgba(255,255,255,0.2);border:none;color:white;font-size:1.3em;cursor:pointer;border-radius:6px;padding:2px 8px;">&times;</button>
  </div>
  <div id="cliente360-content" style="padding:20px;max-height:76vh;overflow-y:auto;">
    <p style="text-align:center;color:#aaa;padding:40px;">Cargando...</p>
  </div>
</div>
</div>

<!-- DASHBOARD -->
<div id="tab-dash" class="page active">
  <div class="kpi-grid" id="kpi-clientes">
    <div class="kpi" style="--c:#2B7A78"><div class="kpi-val" id="kpi-uds">—</div><div class="kpi-lbl">Unidades PT disponibles</div></div>
    <div class="kpi" style="--c:#B5924A"><div class="kpi-val" id="kpi-ped-act">—</div><div class="kpi-lbl">Pedidos activos</div><div class="kpi-sub" id="kpi-ped-val">—</div></div>
    <div class="kpi" style="--c:#4A8B6A"><div class="kpi-val" id="kpi-skus">—</div><div class="kpi-lbl">SKUs con stock</div></div>
    <div class="kpi" style="--c:#7A4A8B"><div class="kpi-val" id="kpi-fm-dias">—</div><div class="kpi-lbl">Dias ultimo pedido FM</div><div class="kpi-sub">Ciclo normal: ~62 dias</div></div>
    <div class="kpi" style="--c:#dc2626"><div class="kpi-val" id="kpi-churn">—</div><div class="kpi-lbl">Aliados en riesgo</div><div class="kpi-sub">&gt;75 dias sin pedido</div></div>
  </div>
  <div style="background:white;border:1px solid #E8E4DE;border-radius:12px;padding:20px;margin-bottom:20px;">
    <h3 style="font-size:0.95em;font-weight:700;color:#1C2B30;margin-bottom:14px;">Stock PT por SKU</h3>
    <table class="tbl"><thead><tr><th>SKU</th><th>Descripcion</th><th>Disponible</th><th>Total producido</th><th>Lotes</th><th>Estado</th></tr></thead>
    <tbody id="stock-dash-body"><tr><td colspan="6" class="empty">Cargando...</td></tr></tbody></table>
  </div>
  <div id="alertas-clientes"></div>
</div>

<!-- ALIADOS -->
<div id="tab-clientes" class="page">
  <div class="section-header">
    <h2>Aliados &amp; Clientes Maquila</h2>
    <button class="btn btn-ghost" onclick="toggleForm('form-nuevo-cliente')">+ Nuevo aliado</button>
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
  <table class="tbl"><thead><tr><th>Numero</th><th>Fecha</th><th>Cliente</th><th>Pedido</th><th>Operador</th><th>Estado</th></tr></thead>
  <tbody id="despachos-body"><tr><td colspan="6" class="empty">Cargando...</td></tr></tbody></table>
</div>

<!-- CHURN / RIESGO RECOMPRA -->
<div id="tab-churn" class="page">
  <div class="section-header">
    <h2>&#x26A0; Riesgo de Churn — Aliados sin pedido reciente</h2>
  </div>
  <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:14px;margin-bottom:16px;font-size:0.85em;color:#92400e;">
    Aliados con mas de <strong>75 dias</strong> sin realizar un pedido. Requieren contacto proactivo.
  </div>
  <div id="churn-list"><p style="color:#aaa;text-align:center;padding:32px;">Cargando...</p></div>
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
  if(id==='tab-churn') loadChurn();
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
    // Churn KPI
    try{
      var cr=await fetch('/api/clientes/alertas-recompra').then(function(r){return r.json();});
      var nChurn=(cr.alertas||[]).length;
      var elCh=document.getElementById('kpi-churn');
      elCh.textContent=nChurn;
      elCh.style.color=nChurn>0?'#dc2626':'#16a34a';
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
        +'<td style="white-space:nowrap;">'
        +'<button class="btn btn-ghost btn-sm" onclick="verHistorialCliente('+cl.id+',\\''+cl.nombre+'\\')">Historial</button> '
        +'<button class="btn btn-sm" style="background:#2B7A78;" onclick="abrirCliente360('+cl.id+')">&#x1F4CA; 360</button>'
        +'</td>'
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
    +'<button onclick="this.closest(\\'div[style]\\').remove()" style="position:absolute;top:12px;right:14px;background:none;border:none;font-size:20px;cursor:pointer;">✕</button>'
    +h+'</div>';
  document.body.appendChild(panel);
}

// ─── Churn Detection ──────────────────────────────────────────────
async function loadChurn(){
  var el=document.getElementById('churn-list');
  el.innerHTML='<p style="color:#aaa;text-align:center;padding:32px;">Cargando...</p>';
  try{
    var d=await fetch('/api/clientes/alertas-recompra').then(function(r){return r.json();});
    var lista=d.alertas||[];
    if(!lista.length){el.innerHTML='<div style="background:#d1fae5;color:#065f46;border-radius:10px;padding:20px;text-align:center;font-weight:600;">&#x2713; Todos los aliados con pedidos recientes. Sin riesgo de churn.</div>';return;}
    var h='<table class="tbl"><thead><tr><th>Aliado</th><th>Tipo</th><th>Ultimo Pedido</th><th>Dias sin pedido</th><th>Total pedidos</th><th>Valor total</th><th>Contacto</th><th>Accion</th></tr></thead><tbody>';
    lista.forEach(function(c){
      var nivelColor=c.nivel==='critico'?'#dc2626':'#d97706';
      var nivelBg=c.nivel==='critico'?'#fee2e2':'#fff7ed';
      h+='<tr style="background:'+nivelBg+';">'
        +'<td style="font-weight:700;">'+c.nombre+'</td>'
        +'<td><span class="badge badge-gris">'+c.tipo+'</span></td>'
        +'<td>'+(c.ultimo_pedido||'Nunca')+'</td>'
        +'<td><strong style="color:'+nivelColor+';font-size:1.1em;">'+c.dias_sin_pedido+'</strong> dias</td>'
        +'<td style="text-align:center;">'+c.total_pedidos+'</td>'
        +'<td style="text-align:right;">'+fmt(c.valor_total)+'</td>'
        +'<td style="font-size:0.82em;">'+(c.email?'<a href="mailto:'+c.email+'" style="color:#2B7A78;">'+c.email+'</a>':'—')+'</td>'
        +'<td><button class="btn btn-sm" style="background:#2B7A78;" onclick="abrirCliente360('+c.id+')">Ver 360</button></td>'
        +'</tr>';
    });
    h+='</tbody></table>';
    el.innerHTML=h;
  }catch(e){el.innerHTML='<p style="color:#dc2626;">Error: '+e.message+'</p>';}
}

// ─── Cliente 360 ──────────────────────────────────────────────────
async function abrirCliente360(cid){
  var modal=document.getElementById('m-cliente360');
  var el=document.getElementById('cliente360-content');
  modal.style.display='block';
  el.innerHTML='<p style="text-align:center;color:#aaa;padding:40px;">Cargando ficha 360...</p>';
  try{
    var d=await fetch('/api/clientes/'+cid+'/ficha360').then(function(r){return r.json();});
    if(d.error){el.innerHTML='<p style="color:#dc2626;">'+d.error+'</p>';return;}
    var cl=d.cliente,s=d.stats;
    var diasColor='#16a34a';
    if(s.dias_sin_pedido!==null&&s.dias_sin_pedido!==undefined){
      diasColor=s.dias_sin_pedido>120?'#dc2626':(s.dias_sin_pedido>75?'#d97706':'#16a34a');
    }
    var h='<div style="margin-bottom:4px;"><h2 style="font-size:1.2em;font-weight:800;color:#1C2B30;">'+cl.nombre+'</h2>'
      +'<div style="color:#78716c;font-size:0.85em;margin-bottom:14px;">'+cl.tipo+' — '+cl.empresa+(cl.nit?' | NIT: '+cl.nit:'')+'</div></div>'
      +'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:18px;">'
      +'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:14px;text-align:center;">'
        +'<div style="font-size:2em;font-weight:900;color:#16a34a;">'+s.total_pedidos+'</div>'
        +'<div style="font-size:0.75em;color:#166534;text-transform:uppercase;letter-spacing:1px;">Total Pedidos</div></div>'
      +'<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:14px;text-align:center;">'
        +'<div style="font-size:1.5em;font-weight:900;color:#2563eb;">'+fmt(s.valor_total)+'</div>'
        +'<div style="font-size:0.75em;color:#1e40af;text-transform:uppercase;letter-spacing:1px;">Valor Total</div></div>'
      +'<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:14px;text-align:center;">'
        +'<div style="font-size:1.5em;font-weight:900;color:#d97706;">'+fmt(s.ticket_promedio)+'</div>'
        +'<div style="font-size:0.75em;color:#92400e;text-transform:uppercase;letter-spacing:1px;">Ticket Promedio</div></div>'
      +'<div style="background:#fdf4ff;border:1px solid #e9d5ff;border-radius:10px;padding:14px;text-align:center;">'
        +'<div style="font-size:2em;font-weight:900;color:'+diasColor+';">'+(s.dias_sin_pedido!==null&&s.dias_sin_pedido!==undefined?s.dias_sin_pedido:'N/A')+'</div>'
        +'<div style="font-size:0.75em;color:#581c87;text-transform:uppercase;letter-spacing:1px;">Dias sin Pedido</div></div>'
      +'</div>';
    // Pedidos recientes
    if(d.pedidos_recientes&&d.pedidos_recientes.length){
      h+='<div style="margin-bottom:16px;"><div style="font-weight:700;font-size:13px;margin-bottom:8px;">Ultimos Pedidos</div>'
        +'<table class="tbl"><thead><tr><th>Numero</th><th>Fecha</th><th>Estado</th><th style="text-align:right;">Valor</th><th>Despacho</th></tr></thead><tbody>';
      d.pedidos_recientes.forEach(function(p){
        var m={'Confirmado':'badge-azul','Produciendo':'badge-amarillo','Listo':'badge-verde','Despachado':'badge-gris','Cancelado':'badge-rojo','Borrador':'badge-gris'};
        h+='<tr><td style="font-family:monospace;font-size:0.85em;">'+p.numero+'</td>'
          +'<td>'+(p.fecha||'').slice(0,10)+'</td>'
          +'<td><span class="badge '+(m[p.estado]||'badge-gris')+'">'+p.estado+'</span></td>'
          +'<td style="text-align:right;">'+fmt(p.valor_total)+'</td>'
          +'<td style="color:#999;font-size:0.85em;">'+(p.fecha_despacho||'—').slice(0,10)+'</td></tr>';
      });
      h+='</tbody></table></div>';
    }
    // Top SKUs
    if(d.top_skus&&d.top_skus.length){
      h+='<div><div style="font-weight:700;font-size:13px;margin-bottom:8px;">Top SKUs Comprados</div>'
        +'<table class="tbl"><thead><tr><th>SKU</th><th>Descripcion</th><th style="text-align:center;">Unidades</th><th style="text-align:center;">En pedidos</th></tr></thead><tbody>';
      d.top_skus.forEach(function(sk){
        h+='<tr><td style="font-family:monospace;font-weight:700;font-size:0.85em;">'+sk.sku+'</td>'
          +'<td>'+sk.descripcion+'</td>'
          +'<td style="text-align:center;font-weight:700;">'+Number(sk.unidades).toLocaleString('es-CO')+'</td>'
          +'<td style="text-align:center;color:#78716c;">'+sk.pedidos+'</td></tr>';
      });
      h+='</tbody></table></div>';
    }
    el.innerHTML=h;
  }catch(e){el.innerHTML='<p style="color:#dc2626;">Error: '+e.message+'</p>';}
}

// Auto-cargar dashboard al iniciar
loadDashboardClientes();
</script>
</body>
</html>"""
