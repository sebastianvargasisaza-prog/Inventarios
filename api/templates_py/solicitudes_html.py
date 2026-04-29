# Auto-extraído de index.py — Fase A refactor
SOLICITUDES_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Compras &amp; Pagos - Solicitudes</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos3">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
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
<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:#6d28d9;"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
  <div>
    <div class="cx-mod-header__title">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#6d28d9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M9 13h6M9 17h6M9 9h2"/></svg>
      Solicitudes de Compra
    </div>
    <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; pedidos de materiales e insumos</div>
  </div>
  <div class="cx-mod-header__nav">
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">&larr; Módulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
    </button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>
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
      <label>Tu correo (para notificaciones)</label>
      <input type="email" id="f-email" placeholder="correo@ejemplo.com">
    </div>
    <div class="field" id="fecha-req-box">
      <label>Fecha requerida (opcional)</label>
      <input type="date" id="f-fecha-req">
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
        <option value="Cuenta de Cobro">Cuenta de Cobro</option>
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
        <div class="field" id="p-handle-box"><label>Red social / Handle</label>
          <input type="text" id="p-handle" placeholder="@usuario"></div>
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
    <button class="btn-primary" id="btn-enviar-pago" onclick="enviarSolicitud()">Enviar Solicitud de Pago</button>
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
var PAGO_CATS=['Influencer/Marketing Digital','Servicios Profesionales','Software/Tecnologia','Cuenta de Cobro'];
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
  var esInfl=cat==='Influencer/Marketing Digital';
  document.getElementById('items-section').style.display=esPago?'none':'block';
  document.getElementById('pago-section').style.display=esPago?'block':'none';
  var hbox=document.getElementById('p-handle-box');
  if(hbox) hbox.style.display=esInfl?'block':'none';
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
    var handle=document.getElementById('p-handle').value.trim();
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
    var obsStr='BENEFICIARIO: '+nombre+(handle?' | HANDLE: '+handle:'')+' | BANCO: '+banco+' '+tipoCta+' | CUENTA/CEL: '+numcta+(cedula?' | CED/NIT: '+cedula:'')+' | VALOR: $'+valor+' | SERVICIO: '+desc+(obsExtra?' | '+obsExtra:'');
    items=[{codigo_mp:'',nombre_mp:desc,cantidad_g:1,unidad:'servicio',valor_estimado:valor}];
    body={solicitante:sol,area:document.getElementById('f-area').value,empresa:empresa,tipo:'Pago',
      categoria:cat,urgencia:urg,observaciones:obsStr,items:items,
      email_solicitante:document.getElementById('f-email').value.trim(),
      fecha_requerida:document.getElementById('f-fecha-req').value};
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
      categoria:cat,urgencia:urg,observaciones:document.getElementById('f-obs').value,items:items,
      email_solicitante:document.getElementById('f-email').value.trim(),
      fecha_requerida:document.getElementById('f-fecha-req').value};
  }
  var btn=esPago ? document.getElementById('btn-enviar-pago') : document.getElementById('btn-enviar');
  if(btn){btn.disabled=true;btn.textContent='Enviando...';}
  try{
    var r=await fetch('/api/solicitudes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(d.numero){
      document.getElementById('confirm-num').textContent=d.numero;
      document.getElementById('form-card').style.display='none';
      document.getElementById('confirm-card').style.display='block';
      window.scrollTo(0,0);
    }else{
      alert('Error: '+(d.error||'Intenta de nuevo'));
      if(btn){btn.disabled=false;btn.textContent=esPago?'Enviar Solicitud de Pago':'Enviar Solicitud';}
    }
  }catch(e){
    alert('Error de conexion.');
    if(btn){btn.disabled=false;btn.textContent=esPago?'Enviar Solicitud de Pago':'Enviar Solicitud';}
  }
}
function nuevaSolicitud(){
  document.getElementById('form-card').style.display='block';
  document.getElementById('confirm-card').style.display='none';
  document.getElementById('f-sol').value='';
  document.getElementById('f-email').value='';
  document.getElementById('f-fecha-req').value='';
  document.getElementById('f-obs').value='';
  document.getElementById('p-nombre').value='';document.getElementById('p-handle').value='';
  document.getElementById('p-banco').value='';document.getElementById('p-numcta').value='';
  document.getElementById('p-cedula').value='';document.getElementById('p-valor').value='';
  document.getElementById('p-desc').value='';document.getElementById('p-obs').value='';
  document.getElementById('items-section').style.display='block';
  document.getElementById('pago-section').style.display='none';
  document.getElementById('f-cat').value='Materia Prima';
  var _defCat=document.getElementById('f-cat').value||'Materia Prima';
  document.getElementById('items-body').innerHTML=
    '<tr id="ir-0"><td><input type="text" placeholder="Cod." id="i0-cod"></td>'+
    '<td><input type="text" placeholder="Descripcion del item" id="i0-nom"></td>'+
    '<td><input type="number" placeholder="0" min="0" step="0.01" id="i0-cant"></td>'+
    '<td>'+buildUniSelect('i0-uni','')+'</td>'+
    '<td><input type="number" placeholder="0" min="0" step="1000" id="i0-val"></td>'+
    '<td><button class="btn-del" onclick="delItem(0)">&#10005;</button></td></tr>';
  itemCount=1;urg='Normal';tipo='Compra';setUrg('Normal',document.getElementById('ub-n'));setTipo('Compra');
  var eb=document.getElementById('btn-enviar');if(eb){eb.disabled=false;eb.textContent='Enviar Solicitud';}
  var ep=document.getElementById('btn-enviar-pago');if(ep){ep.disabled=false;ep.textContent='Enviar Solicitud de Pago';}
  var hbox=document.getElementById('p-handle-box');if(hbox)hbox.style.display='none';
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
