# Auto-generado — Canal B2B HHA Group (ÁNIMUS Aliados + Espagiria Maquila 360)
CLIENTES_HTML = """\
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Canal B2B &#x2014; HHA Group</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#F5F4F0;min-height:100vh;}
.topbar{background:#1C2B30;color:white;padding:12px 28px;display:flex;align-items:center;justify-content:space-between;}
.topbar-title{font-size:1em;font-weight:800;letter-spacing:2px;color:rgba(255,255,255,0.9);}
.topbar a{color:rgba(255,255,255,0.7);text-decoration:none;font-size:0.82em;padding:5px 12px;border:1px solid rgba(255,255,255,0.2);border-radius:6px;}
.topbar a:hover{background:rgba(255,255,255,0.1);color:white;}
/* SWITCHER */
.switcher{display:grid;grid-template-columns:1fr 1fr;gap:0;border-bottom:3px solid #E8E4DE;}
.sw-card{padding:18px 28px;cursor:pointer;display:flex;align-items:center;gap:14px;background:white;transition:all 0.2s;border-bottom:4px solid transparent;margin-bottom:-3px;}
.sw-card:hover{background:#f8fafa;}
.sw-card.active-a{border-bottom-color:#2B7A78;background:#f0fafa;}
.sw-card.active-m{border-bottom-color:#5C4B99;background:#f5f0ff;}
.sw-icon{font-size:1.8em;}
.sw-title{font-size:1em;font-weight:800;color:#1C2B30;}
.sw-sub{font-size:0.78em;color:#7A9E9C;margin-top:1px;}
.sw-card.active-m .sw-sub{color:#9B89C4;}
/* TABS */
.module-tabs{background:white;border-bottom:1px solid #E8E4DE;padding:0 28px;display:flex;gap:4px;}
.tab{padding:12px 20px;cursor:pointer;font-size:0.86em;font-weight:600;color:#7A9E9C;border-bottom:3px solid transparent;transition:all 0.2s;white-space:nowrap;}
.tab.active-a{color:#2B7A78;border-bottom-color:#2B7A78;}
.tab.active-m{color:#5C4B99;border-bottom-color:#5C4B99;}
.tab:hover:not(.active-a):not(.active-m){background:#f5fafa;}
/* CONTENT */
.content{padding:24px 28px;max-width:1280px;margin:0 auto;}
.page{display:none;}.page.active{display:block;}
.section-block{display:none;}.section-block.active{display:block;}
/* KPIs */
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin-bottom:24px;}
.kpi{background:white;border:1px solid #E8E4DE;border-radius:12px;padding:18px 20px;border-left:4px solid var(--c,#2B7A78);}
.kpi-val{font-size:1.9em;font-weight:900;color:var(--c,#2B7A78);line-height:1;}
.kpi-lbl{font-size:0.75em;color:#7A9E9C;text-transform:uppercase;letter-spacing:1px;margin-top:5px;}
.kpi-sub{font-size:0.8em;color:#9C8B7A;margin-top:3px;}
/* TABLE */
.tbl{width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,0.06);}
.tbl thead th{background:#f8fafa;color:#5C7A7A;font-size:0.76em;text-transform:uppercase;letter-spacing:0.8px;padding:9px 13px;text-align:left;border-bottom:1px solid #E8E4DE;}
.tbl tbody td{padding:10px 13px;border-bottom:1px solid #F0EEEA;font-size:0.86em;vertical-align:middle;}
.tbl tbody tr:hover{background:#fafcfc;}.tbl tbody tr:last-child td{border-bottom:none;}
/* BUTTONS */
.btn{display:inline-flex;align-items:center;gap:5px;padding:8px 16px;border:none;border-radius:7px;cursor:pointer;font-size:0.85em;font-weight:600;transition:all 0.2s;background:#2B7A78;color:white;}
.btn:hover{background:#1d5c5a;transform:translateY(-1px);}
.btn-m{background:#5C4B99;}.btn-m:hover{background:#4a3a7a;}
.btn-ghost{background:white;color:#2B7A78;border:1.5px solid #2B7A78;}
.btn-ghost:hover{background:#f0f9f9;}
.btn-ghost-m{background:white;color:#5C4B99;border:1.5px solid #5C4B99;}
.btn-ghost-m:hover{background:#f5f0ff;}
.btn-sm{padding:4px 11px;font-size:0.78em;}
.btn-xs{padding:3px 8px;font-size:0.74em;}
/* BADGES */
.badge{display:inline-block;padding:3px 9px;border-radius:10px;font-size:0.73em;font-weight:700;}
.badge-verde{background:#d1fae5;color:#065f46;}.badge-amarillo{background:#fef3c7;color:#92400e;}
.badge-rojo{background:#fee2e2;color:#991b1b;}.badge-gris{background:#f3f4f6;color:#374151;}
.badge-azul{background:#dbeafe;color:#1e40af;}.badge-morado{background:#ede9fe;color:#5b21b6;}
/* SEMAFORO */
.sem{display:inline-block;width:11px;height:11px;border-radius:50%;vertical-align:middle;margin-right:5px;}
.sem-v{background:#10b981;}.sem-a{background:#f59e0b;}.sem-r{background:#ef4444;}
/* NIVEL */
.nv-ingreso{background:#dbeafe;color:#1e40af;}
.nv-estrategico{background:#d1fae5;color:#065f46;}
.nv-mayorista{background:#fef3c7;color:#92400e;}
/* FORMS */
.form-panel{background:white;border:1px solid #E8E4DE;border-radius:12px;padding:22px;margin-bottom:18px;display:none;}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;}
.form-row.triple{grid-template-columns:1fr 1fr 1fr;}
.form-row.single{grid-template-columns:1fr;}
.fg label{display:block;font-size:0.77em;font-weight:600;color:#5C7A7A;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.5px;}
.fg input,.fg select,.fg textarea{width:100%;padding:8px 11px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.86em;background:#fafcfc;}
.fg input:focus,.fg select:focus,.fg textarea:focus{outline:none;border-color:#2B7A78;}
/* MESSAGES */
.msg-ok{background:#d1fae5;color:#065f46;padding:9px 13px;border-radius:7px;margin:7px 0;font-size:0.85em;}
.msg-err{background:#fee2e2;color:#991b1b;padding:9px 13px;border-radius:7px;margin:7px 0;font-size:0.85em;}
.empty{text-align:center;color:#aaa;padding:28px;font-size:0.88em;}
.section-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;}
.section-header h2{font-size:1.05em;font-weight:700;color:#1C2B30;}
/* STOCK BAR */
.stock-bar{height:5px;border-radius:3px;background:#E8E4DE;overflow:hidden;margin-top:3px;}
.stock-bar-fill{height:100%;border-radius:3px;transition:width 0.4s;}
/* KANBAN */
.kanban-wrap{display:flex;gap:10px;overflow-x:auto;padding-bottom:12px;}
.kan-col{min-width:165px;max-width:185px;background:#f8fafa;border-radius:10px;padding:10px;}
.kan-col-hdr{font-size:0.72em;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:#5C7A7A;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;}
.kan-col-hdr .cnt{background:#e5e7eb;color:#6b7280;border-radius:8px;padding:1px 7px;font-size:0.9em;}
.kan-card{background:white;border:1px solid #E8E4DE;border-radius:8px;padding:10px;margin-bottom:7px;cursor:pointer;transition:box-shadow 0.15s;}
.kan-card:hover{box-shadow:0 2px 8px rgba(92,75,153,0.15);border-color:#9B89C4;}
.kan-card-emp{font-weight:700;font-size:0.85em;color:#1C2B30;margin-bottom:3px;}
.kan-card-prod{font-size:0.77em;color:#6b7280;margin-bottom:5px;}
.kan-card-val{font-size:0.8em;color:#5C4B99;font-weight:700;}
/* MODAL */
.mdl{position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:1000;display:none;align-items:center;justify-content:center;}
.mdl.show{display:flex;}
.mdl-box{background:white;border-radius:14px;width:92%;max-width:480px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,0.3);}
.mdl-hdr{padding:14px 18px;display:flex;justify-content:space-between;align-items:center;color:white;}
.mdl-hdr-a{background:#2B7A78;}.mdl-hdr-m{background:#5C4B99;}
.mdl-hdr strong{font-size:0.95em;}
.mdl-hdr button{background:rgba(255,255,255,0.2);border:none;color:white;font-size:1.2em;cursor:pointer;border-radius:5px;padding:2px 8px;}
.mdl-body{padding:20px;}
.mdl-footer{padding:0 20px 18px;display:flex;gap:10px;justify-content:flex-end;}
/* PROGRESS */
.meta-bar{height:22px;background:#e5e7eb;border-radius:11px;overflow:hidden;margin-top:6px;}
.meta-fill{height:100%;border-radius:11px;background:linear-gradient(90deg,#5C4B99,#9B89C4);transition:width 1s;}
</style>
</head>
<body>
<div class="topbar">
  <a href="/modulos">&#x1F4F1; M&#xF3;dulos</a>
  <span class="topbar-title">HHA Group &#x2014; Canal B2B</span>
  <span style="font-size:0.78em;color:rgba(255,255,255,0.5);" id="usr-lbl"></span>
</div>

<!-- SWITCHER PRINCIPAL -->
<div class="switcher">
  <div class="sw-card active-a" id="sw-animus" onclick="switchSeccion('animus')">
    <span class="sw-icon">&#x1F91D;</span>
    <div>
      <div class="sw-title">&#xC1;NIMUS Lab</div>
      <div class="sw-sub">Aliados Estrat&#xe9;gicos &#x2014; Canal B2B</div>
    </div>
  </div>
  <div class="sw-card" id="sw-maquila" onclick="switchSeccion('maquila')">
    <span class="sw-icon">&#x1F52C;</span>
    <div>
      <div class="sw-title">Espagiria Laboratorio</div>
      <div class="sw-sub" style="color:#9B89C4;">Maquila 360 &#x2014; Pipeline</div>
    </div>
  </div>
</div>


<!-- SECTION: ANIMUS -->
<div class="section-block active" id="sec-animus">
<div class="module-tabs" id="tabs-animus">
  <div class="tab active-a" onclick="goTabA('ta-dash',this)">&#x1F4CA; Dashboard</div>
  <div class="tab" onclick="goTabA('ta-aliados',this)">&#x1F3ED; Aliados</div>
  <div class="tab" onclick="goTabA('ta-pedidos',this)">&#x1F4CB; Pedidos</div>
  <div class="tab" onclick="goTabA('ta-stock',this)">&#x1F4E6; Stock PT</div>
  <div class="tab" onclick="goTabA('ta-despachos',this)">&#x1F69A; Despachos</div>
  <div class="tab" onclick="goTabA('ta-churn',this)">&#x26A0; Riesgo Churn</div>
</div>
<div class="content">


<!-- DASHBOARD ÁNIMUS -->
<div id="ta-dash" class="page active">
  <div class="kpi-grid" id="kpi-animus">
    <div class="kpi" style="--c:#2B7A78"><div class="kpi-val" id="ka-uds">&#x2014;</div><div class="kpi-lbl">Uds PT disponibles</div></div>
    <div class="kpi" style="--c:#B5924A"><div class="kpi-val" id="ka-ped">&#x2014;</div><div class="kpi-lbl">Pedidos activos</div><div class="kpi-sub" id="ka-ped-val">&#x2014;</div></div>
    <div class="kpi" style="--c:#4A8B6A"><div class="kpi-val" id="ka-skus">&#x2014;</div><div class="kpi-lbl">SKUs con stock</div></div>
    <div class="kpi" style="--c:#7A4A8B"><div class="kpi-val" id="ka-fm">&#x2014;</div><div class="kpi-lbl">D&#xed;as &#xfa;lt. pedido FM</div><div class="kpi-sub">Ciclo normal: ~62 d</div></div>
    <div class="kpi" style="--c:#dc2626"><div class="kpi-val" id="ka-churn">&#x2014;</div><div class="kpi-lbl">Aliados en riesgo</div><div class="kpi-sub">&gt;75 d&#xed;as sin pedido</div></div>
  </div>
  <div style="background:white;border:1px solid #E8E4DE;border-radius:12px;padding:18px;margin-bottom:18px;">
    <h3 style="font-size:0.92em;font-weight:700;color:#1C2B30;margin-bottom:12px;">Stock PT por SKU</h3>
    <table class="tbl"><thead><tr><th>SKU</th><th>Descripci&#xf3;n</th><th>Empresa</th><th style="text-align:right;">Disponible</th><th style="text-align:right;">Total</th><th>Lotes</th><th>Estado</th></tr></thead>
    <tbody id="stock-dash-body"><tr><td colspan="7" class="empty">Cargando...</td></tr></tbody></table>
  </div>
  <div id="alertas-dash-a"></div>
</div>


<!-- ALIADOS -->
<div id="ta-aliados" class="page">
  <div class="section-header">
    <h2>Aliados Comerciales</h2>
    <div style="display:flex;gap:8px;">
      <button class="btn btn-ghost btn-sm" onclick="toggleForm('f-aliado')">+ Nuevo aliado</button>
    </div>
  </div>
  <div class="form-panel" id="f-aliado">
    <h3 style="margin-bottom:14px;font-size:0.92em;font-weight:700;">Nuevo aliado</h3>
    <div class="form-row"><div class="fg"><label>Nombre *</label><input type="text" id="cli-nombre"></div>
      <div class="fg"><label>NIT</label><input type="text" id="cli-nit"></div></div>
    <div class="form-row triple">
      <div class="fg"><label>Tipo</label><select id="cli-tipo"><option>Distribuidor</option><option>Retail</option><option>DTC</option><option>Interno</option></select></div>
      <div class="fg"><label>Condiciones pago</label><input type="text" id="cli-pago" value="30 d&#xed;as"></div>
      <div class="fg"><label>Nivel inicial</label><select id="cli-nivel"><option value="Ingreso">Ingreso (&lt;$3M/mes)</option><option value="Estrat&#xe9;gico">Estrat&#xe9;gico ($3M&#x2013;$30M)</option><option value="Mayorista">Mayorista (&gt;$30M)</option></select></div>
    </div>
    <div class="form-row"><div class="fg"><label>Email</label><input type="email" id="cli-email"></div>
      <div class="fg"><label>Tel&#xe9;fono</label><input type="text" id="cli-tel"></div></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:6px;">
      <button class="btn btn-ghost btn-sm" onclick="toggleForm('f-aliado')">Cancelar</button>
      <button class="btn btn-sm" onclick="crearAliado()">Guardar</button>
    </div>
    <div id="cli-msg"></div>
  </div>
  <div style="margin-bottom:10px;font-size:0.8em;color:#7A9E9C;">
    <span style="margin-right:14px;"><span class="sem sem-v"></span>Verde = KPI cumplidos</span>
    <span style="margin-right:14px;"><span class="sem sem-a"></span>Amarillo = En observaci&#xf3;n</span>
    <span><span class="sem sem-r"></span>Rojo = Plan correctivo</span>
  </div>
  <table class="tbl"><thead><tr><th>C&#xf3;d.</th><th>Aliado</th><th>Nivel</th><th>Sem&#xe1;foro</th><th>Pedidos</th><th>Facturado total</th><th>&#xda;lt. pedido</th><th>Acci&#xf3;n</th></tr></thead>
  <tbody id="aliados-body"><tr><td colspan="8" class="empty">Cargando...</td></tr></tbody></table>
</div>


<!-- PEDIDOS -->
<div id="ta-pedidos" class="page">
  <div class="section-header"><h2>Pedidos</h2>
    <button class="btn btn-ghost btn-sm" onclick="toggleForm('f-pedido')">+ Nuevo pedido</button>
  </div>
  <div class="form-panel" id="f-pedido">
    <h3 style="margin-bottom:14px;font-size:0.92em;font-weight:700;">Nuevo pedido</h3>
    <div class="form-row">
      <div class="fg"><label>Aliado *</label><select id="ped-cliente"><option value="">Seleccionar...</option></select></div>
      <div class="fg"><label>Entrega estimada</label><input type="date" id="ped-fecha-ent"></div>
    </div>
    <div class="fg" style="margin-bottom:12px;"><label>Observaciones</label><textarea id="ped-obs" rows="2"></textarea></div>
    <div style="font-size:11px;color:#888;display:grid;grid-template-columns:15% 1fr 10% 15% 5%;gap:6px;padding:0 2px;margin-bottom:4px;font-weight:700;">
      <span>SKU</span><span>Descripci&#xf3;n</span><span>Cant.</span><span>Precio unit.</span><span></span></div>
    <div id="ped-items-list">
      <div class="ped-item-row" style="display:grid;grid-template-columns:15% 1fr 10% 15% 5%;gap:6px;margin-bottom:5px;align-items:center;">
        <input type="text" class="ped-sku" placeholder="TRX-120" style="font-family:monospace;padding:7px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.84em;">
        <input type="text" class="ped-desc" placeholder="Producto" style="padding:7px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.84em;">
        <input type="number" class="ped-cant" placeholder="500" min="1" style="padding:7px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.84em;">
        <input type="number" class="ped-precio" placeholder="31933" min="0" style="padding:7px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.84em;">
        <button onclick="this.parentElement.remove()" style="padding:4px;background:#fee2e2;border:none;border-radius:4px;cursor:pointer;">&#x2715;</button>
      </div>
    </div>
    <button class="btn btn-ghost btn-sm" onclick="addItemPedido()" style="margin-bottom:8px;">+ L&#xed;nea</button>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button class="btn btn-ghost btn-sm" onclick="toggleForm('f-pedido')">Cancelar</button>
      <button class="btn btn-sm" onclick="crearPedido()">Guardar</button>
    </div>
    <div id="ped-msg"></div>
  </div>
  <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
    <button class="btn btn-ghost btn-sm" onclick="loadPedidos('')">Todos</button>
    <button class="btn btn-ghost btn-sm" onclick="loadPedidos('Confirmado')">Confirmados</button>
    <button class="btn btn-ghost btn-sm" onclick="loadPedidos('Produciendo')">Produciendo</button>
    <button class="btn btn-ghost btn-sm" onclick="loadPedidos('Listo')">Listos</button>
    <button class="btn btn-ghost btn-sm" onclick="loadPedidos('Despachado')">Despachados</button>
  </div>
  <table class="tbl"><thead><tr><th>N&#xfa;mero</th><th>Aliado</th><th>Fecha</th><th>Entrega est.</th><th>Estado</th><th style="text-align:right;">Valor</th><th>Acci&#xf3;n</th></tr></thead>
  <tbody id="pedidos-body"><tr><td colspan="7" class="empty">Cargando...</td></tr></tbody></table>
</div>


<!-- STOCK PT -->
<div id="ta-stock" class="page">
  <div class="section-header"><h2>Inventario Producto Terminado</h2>
    <button class="btn btn-sm" onclick="toggleForm('f-pt')">+ Registrar PT</button>
  </div>
  <div class="form-panel" id="f-pt">
    <h3 style="margin-bottom:14px;font-size:0.92em;font-weight:700;">Registrar ingreso Stock PT</h3>
    <div class="form-row triple">
      <div class="fg"><label>SKU *</label><input type="text" id="pt-sku" style="text-transform:uppercase;" placeholder="TRX-120-FM"></div>
      <div class="fg"><label>Descripci&#xf3;n</label><input type="text" id="pt-desc" placeholder="Tr&#xe9;bol 120ml"></div>
      <div class="fg"><label>Unidades *</label><input type="number" id="pt-uds" placeholder="500" min="1"></div>
    </div>
    <div class="form-row">
      <div class="fg"><label>Lote de producci&#xf3;n</label><input type="text" id="pt-lote" placeholder="PROD-00001"></div>
      <div class="fg"><label>Precio base (unitario)</label><input type="number" id="pt-precio" placeholder="31933" min="0"></div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button class="btn btn-ghost btn-sm" onclick="toggleForm('f-pt')">Cancelar</button>
      <button class="btn btn-sm" onclick="registrarPT()">Registrar</button>
    </div>
    <div id="pt-msg"></div>
  </div>
  <table class="tbl"><thead><tr><th>SKU</th><th>Descripci&#xf3;n</th><th>Empresa</th><th style="text-align:right;">Disponible</th><th style="text-align:right;">Total</th><th>Lotes</th><th>Estado</th></tr></thead>
  <tbody id="stock-pt-body"><tr><td colspan="7" class="empty">Cargando...</td></tr></tbody></table>
</div>


<!-- DESPACHOS -->
<div id="ta-despachos" class="page">
  <div class="section-header"><h2>Historial de despachos</h2></div>
  <table class="tbl"><thead><tr><th>N&#xfa;mero</th><th>Fecha</th><th>Aliado</th><th>Pedido</th><th>Operador</th><th>Estado</th></tr></thead>
  <tbody id="despachos-body"><tr><td colspan="6" class="empty">Cargando...</td></tr></tbody></table>
</div>


<!-- CHURN -->
<div id="ta-churn" class="page">
  <div class="section-header"><h2>&#x26a0; Riesgo Churn &#x2014; Sin pedido reciente</h2></div>
  <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:12px 16px;margin-bottom:14px;font-size:0.83em;color:#92400e;">
    Aliados con m&#xe1;s de <strong>75 d&#xed;as</strong> sin pedido. Requieren contacto proactivo.
  </div>
  <div id="churn-list"><p style="color:#aaa;text-align:center;padding:28px;">Cargando...</p></div>
</div>
</div><!-- /content animus -->
</div><!-- /sec-animus -->


<!-- SECTION: MAQUILA 360 -->
<div class="section-block" id="sec-maquila">
<div class="module-tabs" style="background:white;border-bottom:1px solid #E8E4DE;padding:0 28px;display:flex;gap:4px;">
  <div class="tab active-m" onclick="goTabM('tm-dash',this)">&#x1F4CA; Dashboard</div>
  <div class="tab" onclick="goTabM('tm-pipeline',this)">&#x1F9E9; Pipeline</div>
  <div class="tab" onclick="goTabM('tm-prospectos',this)">&#x1F4C4; Prospectos</div>
  <div class="tab" onclick="goTabM('tm-ordenes',this)">&#x1F4CB; &#xd3;rdenes</div>
</div>
<div class="content">

<!-- DASHBOARD MAQUILA -->
<div id="tm-dash" class="page active">
  <div style="background:white;border:1px solid #ede9fe;border-radius:12px;padding:18px;margin-bottom:20px;border-left:4px solid #5C4B99;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
      <div>
        <div style="font-size:0.78em;font-weight:700;color:#5C4B99;text-transform:uppercase;letter-spacing:1px;">Meta Maquila 360 &#x2014; 12 meses</div>
        <div style="font-size:0.82em;color:#6b7280;margin-top:2px;">Pasar de $30M a $76M/mes en facturaci&#xf3;n externa</div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:1.5em;font-weight:900;color:#5C4B99;" id="mq-facturacion-mes">$0</div>
        <div style="font-size:0.75em;color:#9B89C4;">/ $76M objetivo</div>
      </div>
    </div>
    <div class="meta-bar"><div class="meta-fill" id="mq-meta-bar" style="width:0%"></div></div>
    <div style="display:flex;justify-content:space-between;font-size:0.75em;color:#9ca3af;margin-top:4px;">
      <span>$30M (base)</span><span id="mq-meta-pct">0%</span><span>$76M (meta)</span>
    </div>
  </div>
  <div class="kpi-grid">
    <div class="kpi" style="--c:#5C4B99"><div class="kpi-val" id="mq-prosp">&#x2014;</div><div class="kpi-lbl">Prospectos activos</div></div>
    <div class="kpi" style="--c:#059669"><div class="kpi-val" id="mq-ord">&#x2014;</div><div class="kpi-lbl">&#xd3;rdenes activas</div></div>
    <div class="kpi" style="--c:#D97706"><div class="kpi-val" id="mq-val">&#x2014;</div><div class="kpi-lbl">Valor pipeline</div></div>
    <div class="kpi" style="--c:#DC2626"><div class="kpi-val" id="mq-cierre">&#x2014;</div><div class="kpi-lbl">En negociaci&#xf3;n/cierre</div></div>
  </div>
  <div id="mq-ord-recientes"></div>
</div>

<!-- PIPELINE KANBAN -->
<div id="tm-pipeline" class="page">
  <div class="section-header">
    <h2>Pipeline Maquila 360</h2>
    <button class="btn btn-ghost-m btn-sm" onclick="toggleForm('f-prosp')">+ Nuevo prospecto</button>
  </div>
  <div class="form-panel" id="f-prosp" style="border-color:#ede9fe;">
    <h3 style="margin-bottom:14px;font-size:0.92em;font-weight:700;color:#5C4B99;">Nuevo prospecto / cliente</h3>
    <div class="form-row">
      <div class="fg"><label>Empresa / Marca *</label><input type="text" id="mp-emp" placeholder="Nombre de la marca"></div>
      <div class="fg"><label>Contacto</label><input type="text" id="mp-cont" placeholder="Nombre del contacto"></div>
    </div>
    <div class="form-row triple">
      <div class="fg"><label>Email</label><input type="email" id="mp-email"></div>
      <div class="fg"><label>WhatsApp</label><input type="text" id="mp-wa"></div>
      <div class="fg"><label>Etapa inicial</label>
        <select id="mp-etapa">
          <option value="Contacto">Contacto</option>
          <option value="Brief">Brief</option>
          <option value="Formulaci&#xf3;n">Formulaci&#xf3;n</option>
          <option value="Muestra">Muestra</option>
          <option value="Aprobaci&#xf3;n">Aprobaci&#xf3;n</option>
          <option value="Orden">Orden</option>
          <option value="Producci&#xf3;n">Producci&#xf3;n</option>
          <option value="Entrega">Entrega</option>
          <option value="Facturado">Facturado</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="fg"><label>Tipo de producto</label><input type="text" id="mp-prod" placeholder="S&#xe9;rum, crema, limpiador..."></div>
      <div class="fg"><label>Valor estimado lote (COP)</label><input type="number" id="mp-val" placeholder="8000000"></div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button class="btn btn-ghost-m btn-sm" onclick="toggleForm('f-prosp')">Cancelar</button>
      <button class="btn btn-m btn-sm" onclick="crearProspecto()">Guardar</button>
    </div>
    <div id="mp-msg"></div>
  </div>
  <div class="kanban-wrap" id="kanban-pipeline">
    <p style="color:#aaa;padding:20px;">Cargando pipeline...</p>
  </div>
</div>

<!-- PROSPECTOS TABLE -->
<div id="tm-prospectos" class="page">
  <div class="section-header"><h2>Todos los prospectos</h2>
    <button class="btn btn-ghost-m btn-sm" onclick="toggleForm('f-prosp2')">+ Nuevo</button>
  </div>
  <div class="form-panel" id="f-prosp2" style="border-color:#ede9fe;">
    <div class="form-row">
      <div class="fg"><label>Empresa *</label><input type="text" id="mp2-emp"></div>
      <div class="fg"><label>Contacto</label><input type="text" id="mp2-cont"></div>
    </div>
    <div class="form-row triple">
      <div class="fg"><label>Email</label><input type="email" id="mp2-email"></div>
      <div class="fg"><label>WhatsApp</label><input type="text" id="mp2-wa"></div>
      <div class="fg"><label>Etapa</label><select id="mp2-etapa"><option>Contacto</option><option>Brief</option><option>Formulaci&#xf3;n</option><option>Muestra</option><option>Aprobaci&#xf3;n</option><option>Orden</option><option>Producci&#xf3;n</option><option>Entrega</option><option>Facturado</option><option>Perdido</option></select></div>
    </div>
    <div class="form-row">
      <div class="fg"><label>Producto</label><input type="text" id="mp2-prod"></div>
      <div class="fg"><label>Valor est. lote (COP)</label><input type="number" id="mp2-val"></div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button class="btn btn-ghost-m btn-sm" onclick="toggleForm('f-prosp2')">Cancelar</button>
      <button class="btn btn-m btn-sm" onclick="crearProspecto2()">Guardar</button>
    </div>
    <div id="mp2-msg"></div>
  </div>
  <table class="tbl"><thead><tr><th>Empresa</th><th>Contacto</th><th>Producto</th><th>Etapa</th><th>Valor est.</th><th>Fecha</th><th>Acci&#xf3;n</th></tr></thead>
  <tbody id="prosp-body"><tr><td colspan="7" class="empty">Cargando...</td></tr></tbody></table>
</div>

<!-- ÓRDENES -->
<div id="tm-ordenes" class="page">
  <div class="section-header"><h2>&#xd3;rdenes de Maquila</h2>
    <button class="btn btn-ghost-m btn-sm" onclick="toggleForm('f-orden')">+ Nueva orden</button>
  </div>
  <div class="form-panel" id="f-orden" style="border-color:#ede9fe;">
    <div class="form-row">
      <div class="fg"><label>Empresa / Cliente *</label><input type="text" id="mo-emp"></div>
      <div class="fg"><label>Producto *</label><input type="text" id="mo-prod"></div>
    </div>
    <div class="form-row triple">
      <div class="fg"><label>Kg por lote</label><input type="number" id="mo-kg" placeholder="30"></div>
      <div class="fg"><label>Fecha entrega est.</label><input type="date" id="mo-fe"></div>
      <div class="fg"><label>Estado</label><select id="mo-estado"><option>Cotizacion</option><option>Orden</option><option>Producci&#xf3;n</option><option>Entregado</option><option>Facturado</option></select></div>
    </div>
    <div class="form-row">
      <div class="fg"><label>Valor lote (COP)</label><input type="number" id="mo-val"></div>
      <div class="fg"><label>Observaciones</label><input type="text" id="mo-obs"></div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button class="btn btn-ghost-m btn-sm" onclick="toggleForm('f-orden')">Cancelar</button>
      <button class="btn btn-m btn-sm" onclick="crearOrden()">Guardar</button>
    </div>
    <div id="mo-msg"></div>
  </div>
  <table class="tbl"><thead><tr><th>ID</th><th>Empresa</th><th>Producto</th><th>Kg lote</th><th>Entrega</th><th>Estado</th><th style="text-align:right;">Valor</th><th>Acci&#xf3;n</th></tr></thead>
  <tbody id="ordenes-body"><tr><td colspan="8" class="empty">Cargando...</td></tr></tbody></table>
</div>

</div><!-- /content maquila -->
</div><!-- /sec-maquila -->


<!-- MODAL: Cliente 360 -->
<div id="m-cliente360" class="mdl">
<div class="mdl-box" style="max-width:820px;">
  <div class="mdl-hdr mdl-hdr-a">
    <strong>&#x1F4CA; Aliado 360</strong>
    <button onclick="closeMdl('m-cliente360')">&times;</button>
  </div>
  <div id="cliente360-content" style="padding:20px;max-height:76vh;overflow-y:auto;">
    <p style="text-align:center;color:#aaa;padding:40px;">Cargando...</p>
  </div>
</div>
</div>

<!-- MODAL: Editar aliado -->
<div id="m-edit-aliado" class="mdl">
<div class="mdl-box">
  <div class="mdl-hdr mdl-hdr-a">
    <strong>Editar Aliado</strong>
    <button onclick="closeMdl('m-edit-aliado')">&times;</button>
  </div>
  <div class="mdl-body">
    <p style="font-size:0.85em;color:#5C7A7A;margin-bottom:14px;">Aliado: <strong id="ea-nombre"></strong></p>
    <div class="form-row">
      <div class="fg">
        <label>Sem&#xe1;foro KPI</label>
        <select id="ea-semaforo" style="padding:9px 12px;border:1.5px solid #D8E4E4;border-radius:7px;width:100%;">
          <option value="verde">&#x1F7E2; Verde &#x2014; KPI cumplidos</option>
          <option value="amarillo">&#x1F7E1; Amarillo &#x2014; En observaci&#xf3;n</option>
          <option value="rojo">&#x1F534; Rojo &#x2014; Plan correctivo</option>
        </select>
      </div>
      <div class="fg">
        <label>Nivel comercial</label>
        <select id="ea-nivel" style="padding:9px 12px;border:1.5px solid #D8E4E4;border-radius:7px;width:100%;">
          <option value="Ingreso">Ingreso (&lt;$3M/mes)</option>
          <option value="Estrat&#xe9;gico">Estrat&#xe9;gico ($3M&#x2013;$30M)</option>
          <option value="Mayorista">Mayorista (&gt;$30M)</option>
        </select>
      </div>
    </div>
    <div id="ea-msg"></div>
  </div>
  <div class="mdl-footer">
    <button class="btn btn-ghost btn-sm" onclick="closeMdl('m-edit-aliado')">Cancelar</button>
    <button class="btn btn-sm" onclick="guardarAliado()">Guardar</button>
  </div>
</div>
</div>

<!-- MODAL: Estado pedido -->
<div id="m-estado-ped" class="mdl">
<div class="mdl-box">
  <div class="mdl-hdr mdl-hdr-a">
    <strong>Cambiar estado del pedido</strong>
    <button onclick="closeMdl('m-estado-ped')">&times;</button>
  </div>
  <div class="mdl-body">
    <p style="margin-bottom:10px;font-size:0.84em;color:#5C7A7A;">Pedido: <strong id="m-estado-num" style="font-family:monospace;"></strong></p>
    <div class="fg">
      <label>Nuevo estado</label>
      <select id="m-estado-sel" style="padding:10px 12px;border:1.5px solid #D8E4E4;border-radius:7px;width:100%;font-size:0.9em;">
        <option value="">Seleccionar...</option>
        <option>Confirmado</option><option>Produciendo</option>
        <option>Listo</option><option>Despachado</option>
        <option>Facturado</option><option>Cancelado</option>
      </select>
    </div>
    <div id="m-estado-msg" style="margin-top:8px;min-height:22px;"></div>
  </div>
  <div class="mdl-footer">
    <button class="btn btn-ghost btn-sm" onclick="closeMdl('m-estado-ped')">Cancelar</button>
    <button class="btn btn-sm" onclick="confirmarEstadoPedido()">Guardar</button>
  </div>
</div>
</div>

<!-- MODAL: Etapa maquila -->
<div id="m-etapa-maq" class="mdl">
<div class="mdl-box">
  <div class="mdl-hdr mdl-hdr-m">
    <strong>Mover prospecto de etapa</strong>
    <button onclick="closeMdl('m-etapa-maq')">&times;</button>
  </div>
  <div class="mdl-body">
    <p style="margin-bottom:10px;font-size:0.84em;color:#5C7A7A;"><strong id="me-emp"></strong></p>
    <div class="fg">
      <label>Nueva etapa</label>
      <select id="me-etapa" style="padding:10px 12px;border:1.5px solid #ede9fe;border-radius:7px;width:100%;font-size:0.9em;">
        <option>Contacto</option><option>Brief</option><option>Formulaci&#xf3;n</option>
        <option>Muestra</option><option>Aprobaci&#xf3;n</option><option>Orden</option>
        <option>Producci&#xf3;n</option><option>Entrega</option><option>Facturado</option><option>Perdido</option>
      </select>
    </div>
    <div id="me-msg" style="margin-top:8px;"></div>
  </div>
  <div class="mdl-footer">
    <button class="btn btn-ghost-m btn-sm" onclick="closeMdl('m-etapa-maq')">Cancelar</button>
    <button class="btn btn-m btn-sm" onclick="confirmarEtapaMaq()">Mover</button>
  </div>
</div>
</div>


<script>
// ─── GLOBALS ──────────────────────────────────────────────────────────────
var _seccion='animus', _pedActivo=null, _aliadoActivo=null, _prospectoActivo=null;

function fmt(n){return n?('$'+parseFloat(n).toLocaleString('es-CO')):'—';}
function fmtM(n){if(!n)return'—';var m=n/1000000;return'$'+m.toFixed(1)+'M';}
function toggleForm(id){var f=document.getElementById(id);f.style.display=f.style.display==='block'?'none':'block';}
function closeMdl(id){document.getElementById(id).classList.remove('show');}
function openMdl(id){document.getElementById(id).classList.add('show');}

function badgePed(e){
  var m={'Confirmado':'badge-azul','Produciendo':'badge-amarillo','Listo':'badge-verde',
         'Despachado':'badge-gris','Facturado':'badge-gris','Cancelado':'badge-rojo'};
  return '<span class="badge '+(m[e]||'badge-gris')+'">'+e+'</span>';
}
function semHtml(s){
  var cls={'verde':'sem-v','amarillo':'sem-a','rojo':'sem-r'};
  var lab={'verde':'Verde','amarillo':'Amarillo','rojo':'Rojo'};
  return '<span class="sem '+(cls[s]||'sem-v')+'"></span>'+(lab[s]||'Verde');
}
function nivelBadge(n){
  var cls={'Ingreso':'nv-ingreso','Estratégico':'nv-estrategico','Mayorista':'nv-mayorista'};
  return '<span class="badge '+(cls[n]||'nv-ingreso')+'">'+n+'</span>';
}
function etapaBadge(e){
  var m={'Contacto':'badge-gris','Brief':'badge-azul','Formulación':'badge-azul',
         'Muestra':'badge-amarillo','Aprobación':'badge-verde','Orden':'badge-verde',
         'Producción':'badge-amarillo','Entrega':'badge-azul','Facturado':'badge-verde','Perdido':'badge-rojo'};
  return '<span class="badge '+(m[e]||'badge-gris')+'">'+e+'</span>';
}

// ─── SECTION SWITCHER ─────────────────────────────────────────────────────
function switchSeccion(sec){
  _seccion=sec;
  document.getElementById('sec-animus').classList.toggle('active',sec==='animus');
  document.getElementById('sec-maquila').classList.toggle('active',sec==='maquila');
  document.getElementById('sw-animus').className='sw-card'+(sec==='animus'?' active-a':'');
  document.getElementById('sw-maquila').className='sw-card'+(sec==='maquila'?' active-m':'');
  if(sec==='animus') loadDashA();
  else loadDashM();
}

// ─── ÁNIMUS TABS ──────────────────────────────────────────────────────────
function goTabA(id,btn){
  document.querySelectorAll('#sec-animus .page').forEach(function(p){p.classList.remove('active');});
  document.querySelectorAll('#tabs-animus .tab').forEach(function(t){t.classList.remove('active-a');});
  document.getElementById(id).classList.add('active');
  if(btn) btn.classList.add('active-a');
  var fn={'ta-dash':loadDashA,'ta-aliados':loadAliados,'ta-pedidos':function(){loadPedidos('');},'ta-stock':loadStockPT,'ta-despachos':loadDespachos,'ta-churn':loadChurn};
  if(fn[id]) fn[id]();
}

// ─── MAQUILA TABS ─────────────────────────────────────────────────────────
function goTabM(id,btn){
  document.querySelectorAll('#sec-maquila .page').forEach(function(p){p.classList.remove('active');});
  document.querySelectorAll('#sec-maquila .module-tabs .tab').forEach(function(t){t.classList.remove('active-m');});
  document.getElementById(id).classList.add('active');
  if(btn) btn.classList.add('active-m');
  var fn={'tm-dash':loadDashM,'tm-pipeline':loadPipeline,'tm-prospectos':loadProspectos,'tm-ordenes':loadOrdenes};
  if(fn[id]) fn[id]();
}

// ─── ÁNIMUS DASHBOARD ─────────────────────────────────────────────────────
async function loadDashA(){
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
    document.getElementById('ka-uds').textContent=uds.toLocaleString('es-CO');
    document.getElementById('ka-ped').textContent=pedAct.length;
    document.getElementById('ka-ped-val').textContent=fmt(valAct);
    document.getElementById('ka-skus').textContent=skus;
    try{
      var fm=peds.filter(function(p){return p.cliente_codigo==='CLI-002'&&p.estado!=='Cancelado';});
      if(fm.length){
        var ult=fm.sort(function(a,b){return b.fecha>a.fecha?1:-1;})[0];
        var dias=Math.floor((Date.now()-new Date(ult.fecha))/86400000);
        var el=document.getElementById('ka-fm');
        el.textContent=dias; el.style.color=dias>55?'#ef4444':'#2B7A78';
      }
    }catch(e){}
    try{
      var cr=await fetch('/api/clientes/alertas-recompra').then(function(r){return r.json();});
      var nc=(cr.alertas||[]).length;
      document.getElementById('ka-churn').textContent=nc;
      document.getElementById('ka-churn').style.color=nc>0?'#dc2626':'#16a34a';
    }catch(e){}
    var tb=document.getElementById('stock-dash-body');
    if(!stock.length){tb.innerHTML='<tr><td colspan="7" class="empty">Sin stock PT</td></tr>';return;}
    tb.innerHTML=stock.map(function(s){
      var pct=s.inicial>0?Math.round((s.disponible/s.inicial)*100):0;
      var color=pct>50?'#2B7A78':(pct>20?'#f59e0b':'#ef4444');
      var badge=pct>50?'badge-verde':(pct>20?'badge-amarillo':'badge-rojo');
      return '<tr><td style="font-family:monospace;font-weight:700;">'+s.sku+'</td>'
        +'<td>'+s.descripcion+'</td>'
        +'<td><span class="badge badge-gris">'+s.empresa+'</span></td>'
        +'<td style="text-align:right;font-weight:700;">'+s.disponible.toLocaleString('es-CO')+'</td>'
        +'<td style="text-align:right;color:#999;">'+(s.inicial||0).toLocaleString('es-CO')+'</td>'
        +'<td style="text-align:center;">'+(s.lotes||0)+'</td>'
        +'<td><span class="badge '+badge+'">'+pct+'%</span>'
        +'<div class="stock-bar"><div class="stock-bar-fill" style="width:'+pct+'%;background:'+color+';"></div></div></td></tr>';
    }).join('');
  }catch(e){console.error(e);}
}

// ─── ALIADOS ──────────────────────────────────────────────────────────────
async function loadAliados(){
  try{
    var d=await fetch('/api/clientes?empresa=ANIMUS').then(function(r){return r.json();});
    var tb=document.getElementById('aliados-body');
    var cls=d.clientes||[];
    if(!cls.length){tb.innerHTML='<tr><td colspan="8" class="empty">Sin aliados registrados</td></tr>';return;}
    var sel=document.getElementById('ped-cliente');
    sel.innerHTML='<option value="">Seleccionar...</option>';
    cls.forEach(function(cl){sel.innerHTML+='<option value="'+cl.id+'">'+cl.nombre+'</option>';});
    tb.innerHTML=cls.map(function(cl){
      return '<tr>'
        +'<td style="font-family:monospace;font-size:0.8em;color:#888;">'+cl.codigo+'</td>'
        +'<td style="font-weight:700;">'+cl.nombre+'</td>'
        +'<td>'+nivelBadge(cl.nivel_aliado||'Ingreso')+'</td>'
        +'<td>'+semHtml(cl.semaforo||'verde')+'</td>'
        +'<td style="text-align:center;">'+(cl.total_pedidos||0)+'</td>'
        +'<td style="text-align:right;font-weight:600;color:#2B7A78;">'+fmt(cl.facturado_total)+'</td>'
        +'<td style="color:#999;font-size:0.83em;">'+(cl.ultimo_pedido||'').substring(0,10)+'</td>'
        +'<td style="white-space:nowrap;">'
        +'<button class="btn btn-ghost btn-xs" onclick="abrirEditAliado('+cl.id+',\''+cl.nombre+'\',\''+cl.semaforo+'\',\''+cl.nivel_aliado+'\')">Editar</button> '
        +'<button class="btn btn-xs" onclick="abrirCliente360('+cl.id+')">360</button>'
        +'</td></tr>';
    }).join('');
  }catch(e){console.error(e);}
}

async function crearAliado(){
  var nombre=document.getElementById('cli-nombre').value.trim();
  if(!nombre){alert('Nombre requerido');return;}
  var data={nombre:nombre,empresa:'ANIMUS',tipo:document.getElementById('cli-tipo').value,
    nit:document.getElementById('cli-nit').value,
    email:document.getElementById('cli-email').value,
    telefono:document.getElementById('cli-tel').value,
    condiciones_pago:document.getElementById('cli-pago').value,
    nivel_aliado:document.getElementById('cli-nivel').value};
  try{
    var r=await fetch('/api/clientes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    document.getElementById('cli-msg').innerHTML=r.ok?'<div class="msg-ok">'+res.message+'</div>':'<div class="msg-err">'+(res.error||'Error')+'</div>';
    if(r.ok){loadAliados();document.getElementById('cli-nombre').value='';}
  }catch(e){document.getElementById('cli-msg').innerHTML='<div class="msg-err">Error</div>';}
}

function abrirEditAliado(cid,nom,sem,niv){
  _aliadoActivo=cid;
  document.getElementById('ea-nombre').textContent=nom;
  document.getElementById('ea-semaforo').value=sem||'verde';
  document.getElementById('ea-nivel').value=niv||'Ingreso';
  document.getElementById('ea-msg').innerHTML='';
  openMdl('m-edit-aliado');
}
async function guardarAliado(){
  var data={semaforo:document.getElementById('ea-semaforo').value,
            nivel_aliado:document.getElementById('ea-nivel').value};
  var r=await fetch('/api/aliados/'+_aliadoActivo,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  var res=await r.json();
  if(res.ok){
    document.getElementById('ea-msg').innerHTML='<div class="msg-ok">Guardado</div>';
    setTimeout(function(){closeMdl('m-edit-aliado');loadAliados();},500);
  }
}

// ─── PEDIDOS ──────────────────────────────────────────────────────────────
async function loadPedidos(estado){
  try{
    var url='/api/pedidos'+(estado?'?estado='+estado:'');
    var d=await fetch(url).then(function(r){return r.json();});
    var tb=document.getElementById('pedidos-body');
    var peds=d.pedidos||[];
    if(!peds.length){tb.innerHTML='<tr><td colspan="7" class="empty">Sin pedidos</td></tr>';return;}
    tb.innerHTML=peds.map(function(p){
      return '<tr>'
        +'<td style="font-family:monospace;font-weight:700;">'+p.numero+'</td>'
        +'<td style="font-weight:600;">'+(p.cliente||'—')+'</td>'
        +'<td style="color:#999;font-size:0.83em;">'+(p.fecha||'').substring(0,10)+'</td>'
        +'<td style="color:#999;font-size:0.83em;">'+(p.fecha_entrega_est||'—')+'</td>'
        +'<td>'+badgePed(p.estado)+'</td>'
        +'<td style="text-align:right;font-weight:700;color:#2B7A78;">'+fmt(p.valor_total)+'</td>'
        +'<td><button class="btn btn-ghost btn-xs" data-pnum="'+p.numero+'" onclick="cambEstBtn(this)">Estado</button></td>'
        +'</tr>';
    }).join('');
  }catch(e){console.error(e);}
}
function addItemPedido(){
  var div=document.createElement('div');div.className='ped-item-row';
  div.style.cssText='display:grid;grid-template-columns:15% 1fr 10% 15% 5%;gap:6px;margin-bottom:5px;align-items:center;';
  div.innerHTML='<input type="text" class="ped-sku" placeholder="SKU" style="font-family:monospace;padding:7px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.84em;">'
    +'<input type="text" class="ped-desc" placeholder="Descripción" style="padding:7px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.84em;">'
    +'<input type="number" class="ped-cant" placeholder="0" min="1" style="padding:7px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.84em;">'
    +'<input type="number" class="ped-precio" placeholder="0" min="0" style="padding:7px;border:1.5px solid #D8E4E4;border-radius:6px;font-size:0.84em;">'
    +'<button onclick="this.parentElement.remove()" style="padding:4px;background:#fee2e2;border:none;border-radius:4px;cursor:pointer;">✕</button>';
  document.getElementById('ped-items-list').appendChild(div);
}
async function crearPedido(){
  var cid=document.getElementById('ped-cliente').value;
  if(!cid){alert('Selecciona un aliado');return;}
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
  var r=await fetch('/api/pedidos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  var res=await r.json();
  document.getElementById('ped-msg').innerHTML=r.ok?'<div class="msg-ok">'+res.message+'</div>':'<div class="msg-err">'+(res.error||'Error')+'</div>';
  if(r.ok){loadPedidos('');toggleForm('f-pedido');}
}
var _pedidoEstadoActivo=null;
function cambiarEstadoPedido(numero){
  _pedidoEstadoActivo=numero;
  document.getElementById('m-estado-num').textContent=numero;
  document.getElementById('m-estado-sel').value='';
  document.getElementById('m-estado-msg').innerHTML='';
  openMdl('m-estado-ped');
}
async function confirmarEstadoPedido(){
  var nuevo=document.getElementById('m-estado-sel').value;
  var msg=document.getElementById('m-estado-msg');
  if(!nuevo){msg.innerHTML='<span style="color:#dc2626;font-size:0.84em;">Selecciona un estado</span>';return;}
  var r=await fetch('/api/pedidos/'+_pedidoEstadoActivo,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:nuevo})});
  var res=await r.json();
  if(r.ok){
    msg.innerHTML='<span style="color:#16a34a;font-size:0.84em;">✓ Actualizado</span>';
    setTimeout(function(){closeMdl('m-estado-ped');loadPedidos('');},500);
  } else {msg.innerHTML='<span style="color:#dc2626;font-size:0.84em;">'+(res.error||'Error')+'</span>';}
}
function cambEstBtn(el){cambiarEstadoPedido(el.dataset.pnum);}

// ─── STOCK PT ─────────────────────────────────────────────────────────────
async function loadStockPT(){
  var d=await fetch('/api/stock-pt').then(function(r){return r.json();});
  var tb=document.getElementById('stock-pt-body');
  var stock=d.stock_pt||[];
  if(!stock.length){tb.innerHTML='<tr><td colspan="7" class="empty">Sin stock PT</td></tr>';return;}
  tb.innerHTML=stock.map(function(s){
    var pct=s.inicial>0?Math.round((s.disponible/s.inicial)*100):0;
    var badge=pct>50?'badge-verde':(pct>20?'badge-amarillo':'badge-rojo');
    return '<tr><td style="font-family:monospace;font-weight:700;color:#2B7A78;">'+s.sku+'</td>'
      +'<td>'+(s.descripcion||'—')+'</td>'
      +'<td><span class="badge badge-gris">'+s.empresa+'</span></td>'
      +'<td style="text-align:right;font-weight:900;font-size:1.05em;">'+(s.disponible||0).toLocaleString('es-CO')+' uds</td>'
      +'<td style="text-align:right;color:#999;">'+(s.inicial||0).toLocaleString('es-CO')+' uds</td>'
      +'<td style="text-align:center;">'+(s.lotes||0)+'</td>'
      +'<td><span class="badge '+badge+'">'+pct+'%</span></td></tr>';
  }).join('');
}
async function registrarPT(){
  var sku=(document.getElementById('pt-sku').value||'').trim().toUpperCase();
  var uds=parseInt(document.getElementById('pt-uds').value)||0;
  if(!sku||uds<=0){alert('SKU y unidades requeridos');return;}
  var data={sku:sku,descripcion:document.getElementById('pt-desc').value,
    unidades:uds,lote_produccion:document.getElementById('pt-lote').value,
    precio_base:parseFloat(document.getElementById('pt-precio').value)||0};
  var r=await fetch('/api/stock-pt',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  var res=await r.json();
  document.getElementById('pt-msg').innerHTML=r.ok?'<div class="msg-ok">'+res.message+'</div>':'<div class="msg-err">'+(res.error||'Error')+'</div>';
  if(r.ok){loadStockPT();}
}

// ─── DESPACHOS ────────────────────────────────────────────────────────────
async function loadDespachos(){
  var d=await fetch('/api/despachos').then(function(r){return r.json();});
  var tb=document.getElementById('despachos-body');
  var desps=d.despachos||[];
  if(!desps.length){tb.innerHTML='<tr><td colspan="6" class="empty">Sin despachos</td></tr>';return;}
  tb.innerHTML=desps.map(function(d){
    return '<tr><td style="font-family:monospace;font-weight:700;">'+d.numero+'</td>'
      +'<td style="color:#999;font-size:0.83em;">'+(d.fecha||'').substring(0,10)+'</td>'
      +'<td style="font-weight:600;">'+(d.cliente||'—')+'</td>'
      +'<td style="font-family:monospace;font-size:0.8em;color:#888;">'+(d.numero_pedido||'—')+'</td>'
      +'<td>'+(d.operador||'—')+'</td>'
      +'<td><span class="badge badge-verde">'+d.estado+'</span></td></tr>';
  }).join('');
}

// ─── CHURN ────────────────────────────────────────────────────────────────
async function loadChurn(){
  var el=document.getElementById('churn-list');
  el.innerHTML='<p style="color:#aaa;text-align:center;padding:24px;">Cargando...</p>';
  var d=await fetch('/api/clientes/alertas-recompra').then(function(r){return r.json();});
  var lista=d.alertas||[];
  if(!lista.length){el.innerHTML='<div class="msg-ok">&#x2713; Todos los aliados con pedidos recientes.</div>';return;}
  var h='<table class="tbl"><thead><tr><th>Aliado</th><th>Tipo</th><th>&#xda;lt. Pedido</th><th>D&#xed;as</th><th>Total ped.</th><th>Valor</th><th>Email</th><th>Acci&#xf3;n</th></tr></thead><tbody>';
  lista.forEach(function(c){
    var nivelColor=c.nivel==='critico'?'#dc2626':'#d97706';
    var nivelBg=c.nivel==='critico'?'#fee2e2':'#fff7ed';
    h+='<tr style="background:'+nivelBg+';">'
      +'<td style="font-weight:700;">'+c.nombre+'</td><td><span class="badge badge-gris">'+c.tipo+'</span></td>'
      +'<td>'+(c.ultimo_pedido||'Nunca')+'</td>'
      +'<td><strong style="color:'+nivelColor+';">'+c.dias_sin_pedido+'</strong> d</td>'
      +'<td style="text-align:center;">'+c.total_pedidos+'</td>'
      +'<td style="text-align:right;">'+fmt(c.valor_total)+'</td>'
      +'<td style="font-size:0.8em;">'+(c.email?'<a href="mailto:'+c.email+'" style="color:#2B7A78;">'+c.email+'</a>':'—')+'</td>'
      +'<td><button class="btn btn-xs" onclick="abrirCliente360('+c.id+')">360</button></td></tr>';
  });
  h+='</tbody></table>';
  el.innerHTML=h;
}

// ─── CLIENTE 360 ──────────────────────────────────────────────────────────
async function abrirCliente360(cid){
  var el=document.getElementById('cliente360-content');
  openMdl('m-cliente360');
  el.innerHTML='<p style="text-align:center;color:#aaa;padding:32px;">Cargando...</p>';
  var d=await fetch('/api/clientes/'+cid+'/ficha360').then(function(r){return r.json();});
  if(d.error){el.innerHTML='<p style="color:#dc2626;">'+d.error+'</p>';return;}
  var cl=d.cliente,s=d.stats;
  var diasColor='#16a34a';
  if(s.dias_sin_pedido!==null&&s.dias_sin_pedido!==undefined)
    diasColor=s.dias_sin_pedido>120?'#dc2626':(s.dias_sin_pedido>75?'#d97706':'#16a34a');
  var h='<h2 style="font-size:1.1em;font-weight:800;color:#1C2B30;margin-bottom:4px;">'+cl.nombre+'</h2>'
    +'<div style="color:#78716c;font-size:0.83em;margin-bottom:14px;">'+cl.tipo+' — '+cl.empresa+(cl.nit?' | NIT: '+cl.nit:'')+'</div>'
    +'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:16px;">'
    +'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:9px;padding:12px;text-align:center;"><div style="font-size:1.9em;font-weight:900;color:#16a34a;">'+s.total_pedidos+'</div><div style="font-size:0.72em;color:#166534;text-transform:uppercase;letter-spacing:1px;">Pedidos</div></div>'
    +'<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:9px;padding:12px;text-align:center;"><div style="font-size:1.3em;font-weight:900;color:#2563eb;">'+fmt(s.valor_total)+'</div><div style="font-size:0.72em;color:#1e40af;text-transform:uppercase;letter-spacing:1px;">Total</div></div>'
    +'<div style="background:#fdf4ff;border:1px solid #e9d5ff;border-radius:9px;padding:12px;text-align:center;"><div style="font-size:1.9em;font-weight:900;color:'+diasColor+';">'+(s.dias_sin_pedido!==null&&s.dias_sin_pedido!==undefined?s.dias_sin_pedido:'N/A')+'</div><div style="font-size:0.72em;color:#581c87;text-transform:uppercase;letter-spacing:1px;">D&#xed;as sin pedido</div></div>'
    +'</div>';
  if(d.pedidos_recientes&&d.pedidos_recientes.length){
    h+='<div style="font-weight:700;font-size:0.88em;margin-bottom:7px;">&#xda;ltimos pedidos</div>'
      +'<table class="tbl"><thead><tr><th>N&#xfa;mero</th><th>Fecha</th><th>Estado</th><th style="text-align:right;">Valor</th></tr></thead><tbody>';
    d.pedidos_recientes.forEach(function(p){
      h+='<tr><td style="font-family:monospace;font-size:0.83em;">'+p.numero+'</td><td>'+(p.fecha||'').slice(0,10)+'</td><td>'+badgePed(p.estado)+'</td><td style="text-align:right;">'+fmt(p.valor_total)+'</td></tr>';
    });
    h+='</tbody></table>';
  }
  el.innerHTML=h;
}

// ─── MAQUILA DASHBOARD ────────────────────────────────────────────────────
async function loadDashM(){
  try{
    var [kp,ords]=await Promise.all([
      fetch('/api/maquila/kpis').then(function(r){return r.json();}),
      fetch('/api/maquila/ordenes').then(function(r){return r.json();})
    ]);
    document.getElementById('mq-prosp').textContent=kp.prospectos_activos||0;
    document.getElementById('mq-ord').textContent=kp.ordenes_activas||0;
    document.getElementById('mq-val').textContent=fmtM(kp.valor_pipeline||0);
    document.getElementById('mq-cierre').textContent=kp.en_cierre||0;
    // Meta progress ($30M base → $76M meta)
    var base=30000000, meta=76000000;
    var total=(ords||[]).filter(function(o){return o.estado==='Facturado';}).reduce(function(a,o){return a+(o.valor_total||0);},0);
    var pct=Math.min(Math.round(((total-base)/(meta-base))*100),100);
    pct=Math.max(pct,0);
    document.getElementById('mq-facturacion-mes').textContent=fmtM(total);
    document.getElementById('mq-meta-bar').style.width=pct+'%';
    document.getElementById('mq-meta-pct').textContent=pct+'%';
    // Órdenes activas table
    var ord_act=(ords||[]).filter(function(o){return ['Cotizacion','Orden','Producción'].includes(o.estado);}).slice(0,8);
    var el=document.getElementById('mq-ord-recientes');
    if(ord_act.length){
      var h='<div style="background:white;border:1px solid #ede9fe;border-radius:12px;padding:16px;">'
        +'<h3 style="font-size:0.88em;font-weight:700;color:#5C4B99;margin-bottom:12px;">&#xd3;rdenes activas</h3>'
        +'<table class="tbl"><thead><tr><th>Empresa</th><th>Producto</th><th>Estado</th><th style="text-align:right;">Valor</th></tr></thead><tbody>';
      ord_act.forEach(function(o){
        h+='<tr><td style="font-weight:600;">'+o.empresa+'</td><td>'+o.producto+'</td>'
          +'<td><span class="badge badge-amarillo">'+o.estado+'</span></td>'
          +'<td style="text-align:right;color:#5C4B99;font-weight:700;">'+fmt(o.valor_total)+'</td></tr>';
      });
      h+='</tbody></table></div>';
      el.innerHTML=h;
    } else {
      el.innerHTML='<div style="background:#f5f0ff;border:1px solid #ede9fe;border-radius:10px;padding:18px;text-align:center;color:#9B89C4;font-size:0.88em;">Sin órdenes activas</div>';
    }
  }catch(e){console.error(e);}
}

// ─── PIPELINE KANBAN ─────────────────────────────────────────────────────
var ETAPAS=['Contacto','Brief','Formulación','Muestra','Aprobación','Orden','Producción','Entrega','Facturado'];
var ETAPAS_COLORS={'Contacto':'#6b7280','Brief':'#2563eb','Formulación':'#0891b2','Muestra':'#d97706','Aprobación':'#16a34a','Orden':'#059669','Producción':'#7c3aed','Entrega':'#0284c7','Facturado':'#16a34a'};

async function loadPipeline(){
  var data=await fetch('/api/maquila/prospectos').then(function(r){return r.json();});
  var prosp=Array.isArray(data)?data:[];
  var kw=document.getElementById('kanban-pipeline');
  var byEtapa={};
  ETAPAS.forEach(function(e){byEtapa[e]=[];});
  prosp.forEach(function(p){
    var e=p.etapa||'Contacto';
    if(!byEtapa[e]) byEtapa[e]=[];
    byEtapa[e].push(p);
  });
  var h='';
  ETAPAS.forEach(function(etapa){
    var cards=byEtapa[etapa]||[];
    var col=ETAPAS_COLORS[etapa]||'#6b7280';
    h+='<div class="kan-col">'
      +'<div class="kan-col-hdr"><span style="color:'+col+';">'+etapa+'</span><span class="cnt">'+cards.length+'</span></div>';
    cards.forEach(function(p){
      h+='<div class="kan-card" onclick="abrirMoverEtapa('+p.id+',\''+p.empresa+'\',\''+p.etapa+'\')">'
        +'<div class="kan-card-emp">'+p.empresa+'</div>'
        +'<div class="kan-card-prod">'+(p.producto_tipo||'—')+'</div>'
        +'<div class="kan-card-val">'+fmt(p.valor_estimado)+'</div>'
        +'</div>';
    });
    if(!cards.length) h+='<div style="color:#ccc;font-size:0.78em;text-align:center;padding:10px;">Sin prospectos</div>';
    h+='</div>';
  });
  kw.innerHTML=h;
}

function abrirMoverEtapa(id,emp,etapaActual){
  _prospectoActivo=id;
  document.getElementById('me-emp').textContent=emp;
  document.getElementById('me-etapa').value=etapaActual||'Contacto';
  document.getElementById('me-msg').innerHTML='';
  openMdl('m-etapa-maq');
}
async function confirmarEtapaMaq(){
  var nueva=document.getElementById('me-etapa').value;
  var r=await fetch('/api/maquila/prospectos/'+_prospectoActivo,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({etapa:nueva})});
  var res=await r.json();
  if(res.ok){
    document.getElementById('me-msg').innerHTML='<div style="color:#16a34a;font-size:0.84em;">✓ Movido</div>';
    setTimeout(function(){closeMdl('m-etapa-maq');loadPipeline();},400);
  }
}

// ─── PROSPECTOS TABLE ─────────────────────────────────────────────────────
async function loadProspectos(){
  var data=await fetch('/api/maquila/prospectos').then(function(r){return r.json();});
  var prosp=Array.isArray(data)?data:[];
  var tb=document.getElementById('prosp-body');
  if(!prosp.length){tb.innerHTML='<tr><td colspan="7" class="empty">Sin prospectos</td></tr>';return;}
  tb.innerHTML=prosp.map(function(p){
    return '<tr>'
      +'<td style="font-weight:700;">'+p.empresa+'</td>'
      +'<td>'+(p.contacto||'—')+'</td>'
      +'<td style="font-size:0.83em;">'+(p.producto_tipo||'—')+'</td>'
      +'<td>'+etapaBadge(p.etapa)+'</td>'
      +'<td style="text-align:right;color:#5C4B99;font-weight:700;">'+fmt(p.valor_estimado)+'</td>'
      +'<td style="color:#999;font-size:0.82em;">'+(p.fecha_contacto||'').substring(0,10)+'</td>'
      +'<td><button class="btn btn-ghost-m btn-xs" onclick="abrirMoverEtapa('+p.id+',\''+p.empresa+'\',\''+p.etapa+'\')">Etapa</button></td>'
      +'</tr>';
  }).join('');
}

async function crearProspecto(){return crearProspectoData(1);}
async function crearProspecto2(){return crearProspectoData(2);}
async function crearProspectoData(form){
  var suf=form===2?'2':'';
  var emp=(document.getElementById('mp'+suf+'-emp').value||'').trim();
  if(!emp){alert('Empresa requerida');return;}
  var data={empresa:emp,contacto:document.getElementById('mp'+suf+'-cont').value,
    email:document.getElementById('mp'+suf+'-email').value,
    telefono:document.getElementById('mp'+suf+'-wa').value,
    producto_tipo:document.getElementById('mp'+suf+'-prod').value,
    etapa:document.getElementById('mp'+suf+'-etapa').value,
    valor_estimado:parseFloat(document.getElementById('mp'+suf+'-val').value)||0};
  var r=await fetch('/api/maquila/prospectos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  var msgEl=document.getElementById('mp'+suf+'-msg');
  if(r.ok){
    msgEl.innerHTML='<div class="msg-ok">Prospecto creado</div>';
    setTimeout(function(){toggleForm(form===2?'f-prosp2':'f-prosp');loadPipeline();loadProspectos();},700);
  } else {msgEl.innerHTML='<div class="msg-err">Error al crear</div>';}
}

// ─── ÓRDENES ──────────────────────────────────────────────────────────────
async function loadOrdenes(){
  var data=await fetch('/api/maquila/ordenes').then(function(r){return r.json();});
  var ords=Array.isArray(data)?data:[];
  var tb=document.getElementById('ordenes-body');
  if(!ords.length){tb.innerHTML='<tr><td colspan="8" class="empty">Sin órdenes</td></tr>';return;}
  var estColors={'Cotizacion':'badge-gris','Orden':'badge-azul','Producción':'badge-amarillo','Entregado':'badge-verde','Facturado':'badge-verde'};
  tb.innerHTML=ords.map(function(o){
    return '<tr>'
      +'<td style="font-family:monospace;font-size:0.8em;color:#888;">#'+o.id+'</td>'
      +'<td style="font-weight:700;">'+o.empresa+'</td>'
      +'<td>'+o.producto+'</td>'
      +'<td style="text-align:right;">'+(o.batch_size_kg||0)+' kg</td>'
      +'<td style="color:#999;font-size:0.82em;">'+(o.fecha_entrega||'—')+'</td>'
      +'<td><span class="badge '+(estColors[o.estado]||'badge-gris')+'">'+o.estado+'</span></td>'
      +'<td style="text-align:right;color:#5C4B99;font-weight:700;">'+fmt(o.valor_total)+'</td>'
      +'<td><button class="btn btn-ghost-m btn-xs" onclick="abrirEstOrden('+o.id+',\''+o.estado+'\')">Estado</button></td>'
      +'</tr>';
  }).join('');
}
async function crearOrden(){
  var emp=(document.getElementById('mo-emp').value||'').trim();
  var prod=(document.getElementById('mo-prod').value||'').trim();
  if(!emp||!prod){alert('Empresa y producto requeridos');return;}
  var data={empresa:emp,producto:prod,batch_size_kg:parseFloat(document.getElementById('mo-kg').value)||0,
    fecha_entrega:document.getElementById('mo-fe').value,estado:document.getElementById('mo-estado').value,
    valor_total:parseFloat(document.getElementById('mo-val').value)||0,
    observaciones:document.getElementById('mo-obs').value};
  var r=await fetch('/api/maquila/ordenes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  var res=await r.json();
  document.getElementById('mo-msg').innerHTML=r.ok?'<div class="msg-ok">Orden creada</div>':'<div class="msg-err">Error</div>';
  if(r.ok){loadOrdenes();toggleForm('f-orden');}
}
async function abrirEstOrden(oid,actual){
  document.getElementById('eo-oid').value=oid;
  document.getElementById('eo-sel').value=actual;
  document.getElementById('eo-msg').textContent='';
  document.getElementById('m-est-orden').style.display='flex';
}
async function confirmarEstOrden(){
  var oid=document.getElementById('eo-oid').value;
  var est=document.getElementById('eo-sel').value;
  var msg=document.getElementById('eo-msg');
  msg.textContent='Guardando...';
  var r=await fetch('/api/maquila/ordenes/'+oid,{method:'PATCH',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({estado:est})});
  if(r.ok){document.getElementById('m-est-orden').style.display='none';loadOrdenes();}
  else{msg.textContent='Error al guardar';}
}

// ─── INIT ─────────────────────────────────────────────────────────────────
loadDashA();
</script>


<!-- Modal cambio estado orden maquila -->
<div id="m-est-orden" class="mdl" style="display:none">
<div class="mdl-box" style="max-width:380px">
  <div class="mdl-hdr" style="background:#5C4B99">
    <strong style="color:white">Cambiar estado de orden</strong>
    <button onclick="document.getElementById('m-est-orden').style.display='none'">&times;</button>
  </div>
  <div class="mdl-body">
    <input type="hidden" id="eo-oid">
    <div class="fg">
      <label>Nuevo estado</label>
      <select id="eo-sel" class="form-control">
        <option>Cotizacion</option>
        <option>Orden</option>
        <option>Producción</option>
        <option>Entregado</option>
        <option>Facturado</option>
      </select>
    </div>
    <p id="eo-msg" style="color:#c0392b;font-size:0.82em;margin-top:6px"></p>
    <div class="mdl-ftr">
      <button class="btn" style="background:#5C4B99;color:white" onclick="confirmarEstOrden()">Guardar</button>
      <button class="btn btn-sec" onclick="document.getElementById('m-est-orden').style.display='none'">Cancelar</button>
    </div>
  </div>
</div>
</div>
</body>
</html>
"""
