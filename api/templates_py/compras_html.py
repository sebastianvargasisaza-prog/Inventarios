# Auto-extraído de index.py — Fase A refactor
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
  <button class="tn" data-tab="sol">&#x1F4CB; Solicitudes</button>
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

<div id="pane-sol" class="pane">
  <div id="sol-kpis" class="kpis" style="margin-bottom:12px;"></div>
  <div style="font-size:12px;color:#78716c;margin-bottom:8px;padding:0 4px;">&#x2139;&#xFE0F; <b>Catalina:</b> procesa las Pendientes asignando proveedor y generando OC. La OC pasa directo a autorizacion de Gerencia.</div>
  <div class="bar">
    <input type="text" id="q-sol" placeholder="Buscar por #, solicitante, area..." oninput="renderSol()">
    <select id="s-sol" onchange="renderSol()">
      <option value="">Todos los estados</option>
      <option>Pendiente</option>
      <option>Procesada</option>
      <option>Rechazada</option>
    </select>
  </div>
  <div id="grid-sol" class="grid"></div>
</div>

<!-- MODAL: Proveedor 360 -->
<div id="m-ficha360" class="ov">
<div class="mdl mdl-lg" style="max-width:780px;max-height:88vh;overflow-y:auto;">
  <div class="mh"><h3>&#x1F4CA; Proveedor 360</h3><button class="mx" onclick="closeModal('m-ficha360')">&times;</button></div>
  <div class="mb" id="ficha360-content" style="padding:0 4px;">
    <div style="text-align:center;color:#a8a29e;padding:40px;">Cargando ficha...</div>
  </div>
</div>
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
    return '<div class="pc"><div style="display:flex;justify-content:space-between;align-items:flex-start;">'
      +'<div><div class="pn">'+esc(p.nombre)+'</div><div class="pnit">NIT: '+(p.nit||'-')+'</div></div>'
      +'<button class="btn" style="font-size:11px;padding:4px 10px;white-space:nowrap;" data-ficha360="'+esc(p.nombre)+'">&#x1F4CA; Ver 360</button>'
      +'</div><div class="pd">'+
      (p.contacto?'<span>&#x1F464; '+esc(p.contacto)+'</span>':'')+
      (p.telefono?'<span>&#x1F4F1; '+esc(p.telefono)+'</span>':'')+
      (p.email?'<span>&#x1F4E7; '+esc(p.email)+'</span>':'')+
      (p.banco?'<span>&#x1F3E6; '+esc(p.banco)+' '+esc(p.tipo_cuenta||'')+'</span>':'')+
      (p.num_cuenta?'<span>&#x1F4B3; '+esc(p.num_cuenta)+'</span>':'')+
    '</div></div>';
  }).join('');
}

// ─── Proveedor 360 ────────────────────────────────────────────────
document.addEventListener('click', function(e){
  var btn = e.target.closest('[data-ficha360]');
  if (!btn) return;
  abrirFicha360(btn.getAttribute('data-ficha360'));
});

async function abrirFicha360(nombre) {
  openModal('m-ficha360');
  var el = document.getElementById('ficha360-content');
  el.innerHTML = '<div style="text-align:center;color:#a8a29e;padding:40px;">Cargando ficha 360...</div>';
  try {
    var r = await fetch('/api/proveedores-compras/' + encodeURIComponent(nombre) + '/ficha');
    var d = await r.json();
    if (d.error) { el.innerHTML = '<p style="color:#dc2626;">'+esc(d.error)+'</p>'; return; }
    var p = d.proveedor, s = d.stats;
    var scoreColor = s.score >= 80 ? '#16a34a' : s.score >= 50 ? '#d97706' : '#dc2626';
    var scoreLbl = s.score >= 80 ? 'Excelente' : s.score >= 50 ? 'Aceptable' : 'Critico';
    var catColor = (p.categoria||'').indexOf('Critico') >= 0 ? '#dc2626' : (p.categoria||'').indexOf('Mayor') >= 0 ? '#d97706' : '#16a34a';
    var h = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">'
      // Card: Info
      +'<div style="background:#fafaf9;border:1px solid #e7e5e4;border-radius:10px;padding:14px;">'
      +'<div style="font-weight:700;font-size:14px;margin-bottom:8px;">&#x1F3ED; Datos del Proveedor</div>'
      +'<div style="font-size:13px;line-height:1.9;">'
      +(p.nit?'<div><span style="color:#78716c;">NIT:</span> <strong>'+esc(p.nit)+'</strong></div>':'')+
      (p.contacto?'<div><span style="color:#78716c;">Contacto:</span> '+esc(p.contacto)+'</div>':'')+
      (p.email?'<div><span style="color:#78716c;">Email:</span> '+esc(p.email)+'</div>':'')+
      (p.telefono?'<div><span style="color:#78716c;">Tel:</span> '+esc(p.telefono)+'</div>':'')+
      (p.concepto_compra?'<div><span style="color:#78716c;">Concepto:</span> '+esc(p.concepto_compra)+'</div>':'')+
      (p.condiciones_pago?'<div><span style="color:#78716c;">Pago:</span> '+esc(p.condiciones_pago)+'</div>':'')+
      (p.banco?'<div><span style="color:#78716c;">Banco:</span> '+esc(p.banco)+'</div>':'')+
      (p.num_cuenta?'<div><span style="color:#78716c;">Cuenta:</span> '+esc((p.tipo_cuenta||'')+' '+p.num_cuenta)+'</div>':'')+
      (p.acuerdo_calidad?'<div><span style="color:#78716c;">Acuerdo calidad:</span> '+esc(p.acuerdo_calidad)+'</div>':'')+
      '<div><span style="color:#78716c;">Categoria:</span> <span style="color:'+catColor+';font-weight:600;">'+esc(p.categoria||'N/A')+'</span></div>'
      +'</div></div>'
      // Card: Score
      +'<div style="background:#fafaf9;border:1px solid #e7e5e4;border-radius:10px;padding:14px;">'
      +'<div style="font-weight:700;font-size:14px;margin-bottom:12px;">&#x2B50; Score Proveedor</div>'
      +'<div style="text-align:center;margin-bottom:12px;">'
      +'<div style="font-size:42px;font-weight:800;color:'+scoreColor+';">'+s.score+'</div>'
      +'<div style="font-size:12px;color:'+scoreColor+';font-weight:600;">'+scoreLbl+'</div>'
      +'</div>'
      +'<div style="font-size:12px;line-height:2;">'
      +'<div style="display:flex;justify-content:space-between;"><span>OCs totales</span><strong>'+s.oc_total+'</strong></div>'
      +'<div style="display:flex;justify-content:space-between;"><span>Recibidas/Pagadas</span><strong>'+s.oc_recibidas+'</strong></div>'
      +'<div style="display:flex;justify-content:space-between;"><span>Cumplimiento</span><strong style="color:'+scoreColor+';">'+s.cumplimiento+'%</strong></div>'
      +'<div style="display:flex;justify-content:space-between;"><span>Discrepancias</span><strong style="color:'+(s.tasa_discrepancias>0?'#dc2626':'#16a34a')+';">'+s.tasa_discrepancias+'%</strong></div>'
      +'<div style="display:flex;justify-content:space-between;"><span>Valor total comprado</span><strong>$'+Number(s.valor_total).toLocaleString('es-CO',{maximumFractionDigits:0})+'</strong></div>'
      +(s.ultima_oc?'<div style="display:flex;justify-content:space-between;"><span>Ultima OC</span><strong>'+(s.ultima_oc||'').slice(0,10)+'</strong></div>':'')+
      '</div></div>'
      +'</div>';
    // OCs recientes
    if (d.ocs_recientes && d.ocs_recientes.length) {
      h += '<div style="margin-bottom:16px;"><div style="font-weight:700;font-size:13px;margin-bottom:8px;">&#x1F4CB; Ultimas Ordenes de Compra</div>'
        +'<div style="overflow-x:auto;"><table><thead><tr><th>OC</th><th>Fecha</th><th>Estado</th><th>Categoria</th><th style="text-align:right;">Valor</th><th>Discrepancia</th></tr></thead><tbody>';
      d.ocs_recientes.forEach(function(o){
        var estColor = o.estado==='Recibida'||o.estado==='Pagada' ? '#16a34a' : o.estado==='Autorizada' ? '#2563eb' : o.estado==='Parcial' ? '#d97706' : '#78716c';
        h += '<tr><td style="font-family:monospace;font-size:12px;">'+esc(o.numero_oc)+'</td>'
          +'<td>'+(o.fecha||'').slice(0,10)+'</td>'
          +'<td style="color:'+estColor+';font-weight:600;">'+esc(o.estado)+'</td>'
          +'<td>'+esc(o.categoria||'')+'</td>'
          +'<td style="text-align:right;">$'+Number(o.valor_total||0).toLocaleString('es-CO',{maximumFractionDigits:0})+'</td>'
          +'<td style="text-align:center;">'+(o.tiene_discrepancias?'<span style="color:#dc2626;">&#x26A0; Si</span>':'<span style="color:#16a34a;">&#x2713;</span>')+'</td>'
          +'</tr>';
      });
      h += '</tbody></table></div></div>';
    }
    // Materiales comprados
    if (d.materiales && d.materiales.length) {
      h += '<div><div style="font-weight:700;font-size:13px;margin-bottom:8px;">&#x1F9EA; Materiales / Items Comprados</div>'
        +'<div style="overflow-x:auto;"><table><thead><tr><th>Codigo</th><th>Material</th><th style="text-align:center;">Veces</th><th style="text-align:right;">Total (g)</th></tr></thead><tbody>';
      d.materiales.forEach(function(m){
        h += '<tr><td style="font-family:monospace;font-size:12px;">'+esc(m.codigo||'')+'</td>'
          +'<td>'+esc(m.nombre||'')+'</td>'
          +'<td style="text-align:center;">'+m.veces+'</td>'
          +'<td style="text-align:right;">'+Number(m.total_g).toLocaleString('es-CO',{maximumFractionDigits:0})+'</td>'
          +'</tr>';
      });
      h += '</tbody></table></div></div>';
    }
    el.innerHTML = h;
  } catch(e) { el.innerHTML = '<p style="color:#dc2626;">Error: '+e.message+'</p>'; }
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


/* ─── SOLICITUDES MANAGEMENT ─────────────────────────────────────── */
var SOLS=[], _solActual=null, PROVS_LIST=[];
function loadSolicitudes(){
  fetch('/api/solicitudes-compra').then(function(r){return r.json();}).then(function(d){
    SOLS=d.solicitudes||[]; renderSol(); renderSolKpis();
  });
}
function renderSolKpis(){
  var cnt={Pendiente:0,Procesada:0,Rechazada:0};
  SOLS.forEach(function(s){var k=s.estado==='Pendiente'?'Pendiente':s.estado==='Rechazada'?'Rechazada':'Procesada'; cnt[k]++;});
  document.getElementById('sol-kpis').innerHTML=
    mkKpi('Pendientes',cnt.Pendiente,'Requieren accion',cnt.Pendiente>0?'w':'')+
    mkKpi('Con OC generada',cnt.Procesada,'En flujo autorizacion',cnt.Procesada>0?'g':'')+
    mkKpi('Rechazadas',cnt.Rechazada,'Con motivo','');
}
function renderSol(){
  var q=(document.getElementById('q-sol')||{value:''}).value.toLowerCase();
  var st=(document.getElementById('s-sol')||{value:''}).value;
  var list=SOLS.filter(function(s){
    if(st && s.estado!==st) return false;
    if(q && !(s.numero+s.solicitante+s.area+s.categoria).toLowerCase().includes(q)) return false;
    return true;
  });
  var bmap={Pendiente:'background:#fef3c7;color:#92400e',Procesada:'background:#d1fae5;color:#065f46',Verificada:'background:#dbeafe;color:#1e40af',Autorizada:'background:#d1fae5;color:#065f46',Rechazada:'background:#fee2e2;color:#991b1b'};
  var umap={Alta:'color:#dc2626;font-weight:700',Media:'color:#d97706',Baja:'color:#16a34a'};
  var html='';
  if(!list.length){html='<div class="empty">No hay solicitudes</div>';}
  else{
    html='<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f5f4f2;">'
      +'<th style="padding:8px 10px;">No</th><th style="padding:8px 10px;">Fecha</th>'
      +'<th style="padding:8px 10px;">Solicitante</th><th style="padding:8px 10px;">Area</th>'
      +'<th style="padding:8px 10px;">Urgencia</th><th style="padding:8px 10px;">Estado</th>'
      +'<th style="padding:8px 10px;">OC</th><th style="padding:8px 10px;"></th></tr></thead><tbody>';
    list.forEach(function(s){
      var bst=bmap[s.estado]||''; var ust=umap[s.urgencia]||'';
      var bg=s.estado==='Pendiente'?'background:#fffbeb;':'';
      var ocTxt=s.numero_oc?('<b>'+esc(s.numero_oc)+'</b>'):'-';
      var btn=s.estado==='Pendiente'?'<button class="btn bp" style="font-size:11px;padding:3px 8px;" data-num="'+esc(s.numero)+'" onclick="openSolBtn(this)">Procesar</button>':'';
      html+='<tr style="border-bottom:1px solid #f3f4f6;cursor:pointer;'+bg+'" data-num="'+esc(s.numero)+'" onclick="openSolRow(this)">'
        +'<td style="padding:8px 10px;font-weight:600;">'+esc(s.numero)+'</td>'
        +'<td style="padding:8px 10px;color:#78716c;">'+esc((s.fecha||'').substring(0,10))+'</td>'
        +'<td style="padding:8px 10px;">'+esc(s.solicitante||'')+'</td>'
        +'<td style="padding:8px 10px;">'+esc(s.area||'')+'</td>'
        +'<td style="padding:8px 10px;"><span style="'+ust+'">'+esc(s.urgencia||'')+'</span></td>'
        +'<td style="padding:8px 10px;"><span style="padding:3px 8px;border-radius:10px;font-size:11px;font-weight:600;'+bst+'">'+esc(s.estado)+'</span></td>'
        +'<td style="padding:8px 10px;font-size:11px;">'+ocTxt+'</td>'
        +'<td style="padding:8px 10px;">'+btn+'</td></tr>';
    });
    html+='</tbody></table>';
  }
  document.getElementById('grid-sol').innerHTML=html;
  // Re-attach row click via delegation
  document.getElementById('grid-sol').querySelectorAll('tr[data-num]').forEach(function(tr){
    tr.addEventListener('click',function(e){if(e.target.tagName!=='BUTTON') openSol(tr.dataset.num);});
  });
}
function openSolRow(el){openSol(el.dataset.num);}
function openSolBtn(el){event.stopPropagation(); openSol(el.dataset.num);}
function openSol(numero){
  _solActual=numero;
  Promise.all([
    fetch('/api/solicitudes-compra/'+encodeURIComponent(numero)).then(function(r){return r.json();}),
    fetch('/api/proveedores-compras').then(function(r){return r.json();})
  ]).then(function(res){
    var detail=res[0], provs=res[1].proveedores||[];
    PROVS_LIST=provs;
    var s=detail.solicitud||{}, items=detail.items||[];
    var bmap2={Pendiente:'background:#fef3c7;color:#92400e',Procesada:'background:#d1fae5;color:#065f46',Rechazada:'background:#fee2e2;color:#991b1b',Verificada:'background:#dbeafe;color:#1e40af',Autorizada:'background:#d1fae5;color:#065f46'};
    var bst2=bmap2[s.estado]||'';
    var urg_color=s.urgencia==='Alta'?'color:#dc2626':s.urgencia==='Media'?'color:#d97706':'color:#16a34a';
    var html='<div class="g2">'
      +'<div class="fg"><label>Numero</label><div style="font-weight:700;font-size:15px;">'+esc(s.numero)+'</div></div>'
      +'<div class="fg"><label>Estado</label><span style="padding:4px 12px;border-radius:10px;font-size:12px;font-weight:700;'+bst2+'">'+esc(s.estado)+'</span></div>'
      +'<div class="fg"><label>Solicitante</label><div>'+esc(s.solicitante||'')+'</div></div>'
      +'<div class="fg"><label>Area / Empresa</label><div>'+esc(s.area||'')+' - '+esc(s.empresa||'')+'</div></div>'
      +'<div class="fg"><label>Urgencia</label><div style="font-weight:600;'+urg_color+'">'+esc(s.urgencia||'')+'</div></div>'
      +'<div class="fg"><label>Categoria</label><div>'+esc(s.categoria||'')+'</div></div>'
      +'</div>';
    if(s.observaciones){html+='<div class="fg"><label>Observaciones</label><div style="background:#fffbeb;padding:8px 12px;border-radius:6px;font-size:12px;border-left:3px solid #f59e0b;">'+esc(s.observaciones)+'</div></div>';}
    html+='<div class="fg"><label>Items Solicitados ('+items.length+')</label><table class="itbl"><thead><tr><th>Codigo</th><th>Material</th><th>Cantidad</th><th>Unidad</th></tr></thead><tbody>';
    items.forEach(function(it){html+='<tr><td style="font-weight:600;">'+esc(it.codigo_mp||'')+'</td><td>'+esc(it.nombre_mp||'')+'</td><td style="text-align:right;">'+esc(String(it.cantidad_g||''))+'</td><td>'+esc(it.unidad||'')+'</td></tr>';});
    html+='</tbody></table></div>';
    if(s.estado==='Pendiente'){
      var popts='<option value="">-- Seleccionar proveedor --</option>';
      provs.forEach(function(p){popts+='<option value="'+esc(p.nombre)+'">'+esc(p.nombre)+'</option>';});
      html+='<div class="fg"><label>Proveedor</label>'
        +'<select id="sol-prov-sel" style="width:100%;padding:8px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">'+popts+'</select>'
        +'<button type="button" onclick="toggleNuevoProv()" style="margin-top:6px;background:none;border:none;color:#2563eb;font-size:12px;cursor:pointer;text-decoration:underline;">+ Crear proveedor nuevo</button></div>'
        +'<div id="div-nuevo-prov" style="display:none;background:#f9f8f7;border:1px solid #e7e5e4;border-radius:8px;padding:14px;margin-top:4px;">'
        +'<div style="font-weight:700;font-size:12px;margin-bottom:10px;">Nuevo Proveedor</div>'
        +'<div class="g2">'
        +'<div class="fg"><label>Nombre *</label><input id="np-nombre" type="text" placeholder="Nombre o razon social"></div>'
        +'<div class="fg"><label>Contacto</label><input id="np-contacto" type="text" placeholder="Nombre contacto"></div>'
        +'<div class="fg"><label>Email</label><input id="np-email" type="email"></div>'
        +'<div class="fg"><label>Telefono</label><input id="np-tel" type="text"></div>'
        +'<div class="fg"><label>Categoria</label><select id="np-cat"><option>MP</option><option>MEE</option><option>Servicios</option><option>Administrativo</option><option>Infraestructura</option></select></div>'
        +'<div class="fg"><label>Condiciones pago</label><input id="np-pago" type="text" placeholder="30 dias, contado..."></div>'
        +'</div>'
        +'<button class="btn bp" style="margin-top:8px;width:100%;" onclick="crearProveedorInline()">Guardar y Seleccionar</button></div>';
    } else if(s.numero_oc){
      html+='<div class="fg"><label>Orden de Compra Generada</label><div style="background:#ecfdf5;padding:10px 14px;border-radius:8px;border-left:4px solid #10b981;font-weight:700;font-size:14px;">'+esc(s.numero_oc)+'</div></div>';
    }
    document.getElementById('m-sol-body').innerHTML=html;
    var footer='';
    if(s.estado==='Pendiente'){
      footer='<button class="btn bp" style="font-size:13px;padding:8px 18px;" onclick="generarOCSol()">Generar OC</button> ';
      footer+='<button class="btn" style="background:#dc2626;color:#fff;font-size:13px;padding:8px 18px;" onclick="solRechazo()">Rechazar</button>';
    }
    footer+='<button class="btn" onclick="closeModal(&quot;m-sol&quot;)" style="margin-left:auto;font-size:13px;">Cerrar</button>';
    document.getElementById('m-sol-footer').innerHTML=footer;
    openModal('m-sol');
  });
}
function toggleNuevoProv(){
  var d=document.getElementById('div-nuevo-prov');
  d.style.display=d.style.display==='none'?'block':'none';
  if(d.style.display==='block') document.getElementById('sol-prov-sel').value='';
}
function crearProveedorInline(){
  var nombre=(document.getElementById('np-nombre')||{value:''}).value.trim();
  if(!nombre){alert('Nombre es obligatorio');return;}
  var body={nombre:nombre,contacto:(document.getElementById('np-contacto')||{value:''}).value,email:(document.getElementById('np-email')||{value:''}).value,telefono:(document.getElementById('np-tel')||{value:''}).value,categoria:(document.getElementById('np-cat')||{value:'MP'}).value,condiciones_pago:(document.getElementById('np-pago')||{value:''}).value};
  fetch('/api/proveedores-compras',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(body)})
  .then(function(r){return r.json();}).then(function(d){
    if(d.error){alert('Error: '+d.error);return;}
    var sel=document.getElementById('sol-prov-sel');
    if(sel){var opt=document.createElement('option');opt.value=nombre;opt.textContent=nombre;sel.appendChild(opt);sel.value=nombre;}
    document.getElementById('div-nuevo-prov').style.display='none';
    alert('Proveedor "'+nombre+'" creado y seleccionado.');
  });
}
function generarOCSol(){
  var prov=(document.getElementById('sol-prov-sel')||{value:''}).value;
  if(!prov){alert('Selecciona o crea un proveedor primero.');return;}
  if(!confirm('Generar OC para '+_solActual+' con proveedor: '+prov+'?')) return;
  fetch('/api/solicitudes-compra/'+encodeURIComponent(_solActual)+'/estado',{method:'PATCH',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({estado:'Procesada',crear_oc:true,proveedor:prov})})
  .then(function(r){return r.json();}).then(function(d){
    if(d.ok){alert('OC generada: '+d.numero_oc+'\\nAhora aparece en la cola Para Autorizar.');closeModal('m-sol');loadSolicitudes();load();}
    else alert('Error: '+(d.error||'Verifica que hayas iniciado sesion.'));
  });
}
function solRechazo(){
  var motivo=prompt('Motivo del rechazo:');
  if(motivo===null) return;
  if(!motivo.trim()){alert('Debes ingresar un motivo.');return;}
  fetch('/api/solicitudes-compra/'+encodeURIComponent(_solActual)+'/estado',{method:'PATCH',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({estado:'Rechazada',observaciones:motivo})})
  .then(function(r){return r.json();}).then(function(d){
    if(d.ok){alert('Solicitud rechazada.');closeModal('m-sol');loadSolicitudes();}
    else alert('Error: '+(d.error||'No autorizado'));
  });
}

</script>

<!-- MODAL: Gestionar Solicitud -->
<div id="m-sol" class="ov">
<div class="mdl mdl-lg" style="max-width:720px;">
  <div class="mh"><h3>&#x1F4CB; Gestionar Solicitud</h3><button class="mx" onclick="closeModal(&quot;m-sol&quot;)">&times;</button></div>
  <div class="mb" id="m-sol-body" style="gap:10px;"></div>
  <div class="mf" id="m-sol-footer"></div>
</div>
</div>

</body>
</html>"""
