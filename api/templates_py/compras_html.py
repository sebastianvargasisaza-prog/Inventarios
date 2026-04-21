# Auto-extraído de index.py — Fase A refactor
COMPRAS_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Compras HHA</title>
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
  <h1>&#x1F6D2; Compras HHA</h1>
  <span style="font-size:13px;color:#a8a29e;">&#x1F464; {usuario}</span>&nbsp;&nbsp;
  <a href="/modulos" style="font-weight:700;">&#x1F4F1; M&#xF3;dulos</a>
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
  <button class="tn" data-tab="influencer" id="tn-influencer">&#x1F4B8; Influencers</button>
  <button class="tn" data-tab="solic" id="tn-solic">&#128203; Solicitudes</button>
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
  <div id="mp-alert-banner" style="display:none;background:#fef3c7;border:1px solid #f59e0b;border-radius:8px;padding:10px 14px;margin-bottom:10px;">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <span style="font-size:18px;">&#x26A0;&#xFE0F;</span>
      <div id="mp-alert-text" style="flex:1;font-size:13px;font-weight:600;color:#92400e;"></div>
      <button class="btn" style="background:#f59e0b;color:#fff;font-size:12px;padding:4px 12px;white-space:nowrap;" onclick="openOCSugerida()">&#x1F4CB; Crear OC Sugerida</button>
    </div>
    <div id="mp-alert-list" style="margin-top:6px;display:flex;flex-wrap:wrap;gap:6px;"></div>
  </div>
  <div class="bar">
    <input type="text" id="q-mp" placeholder="Buscar OC..." oninput="renderCat('mp')">
    <select id="s-mp" onchange="renderCat('mp')"><option value="">Todos los estados</option><option>Borrador</option><option>Revisada</option><option>Autorizada</option><option>Pagada</option><option>Recibida</option></select>
    <button class="btn bp" onclick="openNuevaOCMP()">+ Nueva OC</button>
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

<div id="pane-influencer" class="pane">
  <div id="kpi-influencer" style="display:flex;gap:12px;margin-bottom:12px;flex-wrap:wrap;"></div>
  <div class="bar">
    <input type="text" id="q-influencer" placeholder="Buscar influencer, solicitante..." oninput="renderInfluencers()">
    <select id="s-influencer" onchange="renderInfluencers()">
      <option value="">Todos los estados</option>
      <option value="Aprobada">Por pagar</option>
      <option value="Pagada">Pagadas</option>
      <option value="Rechazada">Rechazadas</option>
    </select>
  </div>
  <div id="pills-influencer" class="pills"></div>
  <div id="grid-influencer" class="grid"></div>
</div>
<!-- Modal rechazo influencer -->
<div id="m-rechazar-inf" class="ov">
  <div class="mc" style="max-width:440px;">
    <div class="mh"><h3>Rechazar cuenta de cobro</h3><button class="mc-x" onclick="closeModal('m-rechazar-inf')">&#x2715;</button></div>
    <div style="padding:20px;">
      <p style="margin:0 0 12px;color:#374151;">Motivo del rechazo (visible para el solicitante):</p>
      <textarea id="motivo-rechazo-inf" rows="3" style="width:100%;padding:8px;border:1px solid #d1d5db;border-radius:6px;font-size:14px;resize:vertical;" placeholder="Ej: Falta información de cuenta, monto incorrecto..."></textarea>
      <div style="display:flex;gap:8px;margin-top:16px;justify-content:flex-end;">
        <button class="btn" onclick="closeModal('m-rechazar-inf')" style="background:#6b7280;color:#fff;">Cancelar</button>
        <button class="btn" id="btn-confirmar-rechazo" style="background:#dc2626;color:#fff;">Confirmar Rechazo</button>
      </div>
    </div>
  </div>
</div>

<div id="pane-prov" class="pane">
  <div class="bar">
    <input type="text" id="q-prov" placeholder="Buscar proveedor..." oninput="renderProv()">
    <button class="btn bp" onclick="openModal('m-nprov')">+ Nuevo Proveedor</button>
  </div>
  <div id="prov-grid" class="pg"><div class="empty">Cargando...</div></div>
</div>

<div id="pane-solic" class="pane">
  <div class="bar">
    <input type="text" id="q-solic" placeholder="Buscar solicitud, solicitante..." oninput="renderSolicitudes()">
    <select id="s-solic" onchange="renderSolicitudes()">
      <option value="">Todos los estados</option>
      <option value="Pendiente">Pendiente</option>
      <option value="Aprobada">Aprobada</option>
      <option value="Rechazada">Rechazada</option>
    </select>
  </div>
  <div id="pills-solic" class="pills"></div>
  <div id="grid-solic" class="grid"></div>
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
      <div class="fg"><label>Valor base / subtotal ($)</label><input type="number" id="rev-val" min="0" step="0.01" placeholder="0" oninput="calcRevIva()"></div>
      <div class="fg"><label>Fecha entrega</label><input type="date" id="rev-fent"></div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;margin:6px 0 2px;">
      <input type="checkbox" id="rev-iva-chk" onchange="calcRevIva()" style="width:16px;height:16px;cursor:pointer;">
      <label for="rev-iva-chk" style="cursor:pointer;font-weight:600;font-size:13px;">Aplica IVA (19%)</label>
    </div>
    <div id="rev-iva-breakdown" style="display:none;background:#fefce8;border:1px solid #fde047;border-radius:6px;padding:8px 12px;font-size:12px;margin-bottom:4px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:2px;"><span>Subtotal</span><span id="rev-iva-sub">$0</span></div>
      <div style="display:flex;justify-content:space-between;margin-bottom:2px;color:#92400e;"><span>IVA 19%</span><span id="rev-iva-monto">$0</span></div>
      <div style="display:flex;justify-content:space-between;font-weight:700;border-top:1px solid #fde047;padding-top:4px;"><span>Total con IVA</span><span id="rev-iva-total">$0</span></div>
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


<!-- MODAL: Detalle OC -->
<div id="m-oc-det" class="ov">
<div class="mdl mdl-lg">
  <div class="mh"><h3>&#128203; Detalle Orden de Compra</h3><button class="mx" onclick="closeModal('m-oc-det')">&times;</button></div>
  <div class="mb" id="oc-det-body" style="padding:0 4px;"><div style="text-align:center;padding:40px;color:#78716c;">Cargando...</div></div>
  <div class="mf" id="oc-det-footer">
    <button class="btn bo" onclick="closeModal('m-oc-det')">Cerrar</button>
  </div>
</div>
</div>

<!-- MODAL: Aprobar / Rechazar OC -->
<div id="m-aut" class="ov">
<div class="mdl">
  <div class="mh"><h3>&#9997; Decision sobre OC</h3><button class="mx" onclick="closeModal('m-aut')">&times;</button></div>
  <div class="mb">
    <div id="m-aut-info" style="background:#f9f8f7;border:1px solid #e7e5e4;border-radius:6px;padding:10px;font-size:13px;margin-bottom:4px;"></div>
    <div class="fg"><label>Motivo / Comentario (recomendado)</label>
      <textarea id="aut-motivo" placeholder="Razon de la aprobacion o rechazo..." rows="3"></textarea>
    </div>
    <input type="hidden" id="aut-num">
  </div>
  <div class="mf">
    <button class="btn bo" onclick="closeModal('m-aut')">Cancelar</button>
    <button class="btn" style="background:#dc2626;color:#fff;font-weight:700;" onclick="decidirOC('Rechazada')">&#10005; Rechazar</button>
    <button class="btn bi" onclick="decidirOC('Autorizada')">&#10003; Autorizar</button>
  </div>
</div>
</div>

<!-- MODAL: Detalle Solicitud (Catalina) -->
<div id="m-sol-det" class="ov">
<div class="mdl mdl-lg">
  <div class="mh"><h3>&#128203; Solicitud de Compra</h3><button class="mx" onclick="closeModal('m-sol-det')">&times;</button></div>
  <div class="mb" id="sol-det-body" style="padding:0 4px;"><div style="text-align:center;padding:40px;color:#78716c;">Cargando...</div></div>
  <div class="mf" id="sol-det-footer">
    <button class="btn bo" onclick="closeModal('m-sol-det')">Cerrar</button>
  </div>
</div>
</div>

<!-- MODAL: Nueva OC Materias Primas (con catalogo) -->
<div id="m-noc-mp" class="ov">
<div class="mdl mdl-lg">
  <div class="mh"><h3>&#x1F9EA; Nueva OC &#x2014; Materias Primas</h3><button class="mx" onclick="closeModal('m-noc-mp')">&times;</button></div>
  <div class="mb">
    <div id="nmp-alert-info" style="display:none;background:#fef3c7;border:1px solid #f59e0b;border-radius:6px;padding:8px 12px;margin-bottom:10px;font-size:12px;color:#92400e;"></div>
    <div class="fg" style="margin-bottom:12px;">
      <label style="font-size:12px;font-weight:600;color:#57534e;display:block;margin-bottom:4px;">Proveedor</label>
      <select id="nmp-prov" onchange="fillProv('nmp-prov','nmp-ibox')" style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;"></select>
      <div id="nmp-ibox" class="ibox" style="display:none;margin-top:6px;"></div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">
      <div>
        <label style="font-size:12px;font-weight:600;color:#57534e;display:block;margin-bottom:4px;">Fecha entrega estimada</label>
        <input type="date" id="nmp-fent" style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">
      </div>
      <div>
        <label style="font-size:12px;font-weight:600;color:#57534e;display:block;margin-bottom:4px;">Observaciones</label>
        <input type="text" id="nmp-obs" placeholder="Opcional..." style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">
      </div>
    </div>
    <datalist id="mp-codes-dl"></datalist>
    <table style="width:100%;border-collapse:collapse;font-size:12px;">
      <thead><tr style="background:#f5f5f4;font-weight:600;color:#44403c;">
        <th style="padding:6px 4px;text-align:left;width:100px;">Codigo MP</th>
        <th style="padding:6px 4px;text-align:left;">Material</th>
        <th style="padding:6px 4px;text-align:center;width:85px;">Cant (g)</th>
        <th style="padding:6px 4px;text-align:center;width:90px;">Precio/g</th>
        <th style="padding:6px 4px;text-align:right;width:85px;">Subtotal</th>
        <th style="padding:6px 4px;width:30px;"></th>
      </tr></thead>
      <tbody id="nmp-tbody"></tbody>
    </table>
    <div style="display:flex;align-items:center;justify-content:space-between;margin-top:10px;">
      <button class="btn bo" style="font-size:12px;" onclick="addRowMP(null)">+ Agregar item</button>
      <div style="font-size:15px;font-weight:700;color:#1c1917;">Total: <span id="nmp-tot">$0</span></div>
    </div>
  </div>
  <div class="mf">
    <button class="btn bo" onclick="closeModal('m-noc-mp')">Cancelar</button>
    <button class="btn bp" onclick="crearOCMP()">&#x2713; Crear Orden de Compra</button>
  </div>
</div>
</div>

<!-- MODAL: OC Sugerida desde alertas de stock -->
<div id="m-oc-sug" class="ov">
<div class="mdl mdl-lg">
  <div class="mh"><h3>&#x26A0;&#xFE0F; OC Sugerida &#x2014; MPs Bajo Stock</h3><button class="mx" onclick="closeModal('m-oc-sug')">&times;</button></div>
  <div class="mb">
    <div style="font-size:12px;color:#78716c;margin-bottom:12px;">Cantidades sugeridas incluyen 20% de buffer sobre el deficit. Ajusta antes de crear.</div>
    <div class="fg" style="margin-bottom:12px;">
      <label style="font-size:12px;font-weight:600;color:#57534e;display:block;margin-bottom:4px;">Proveedor</label>
      <select id="sug-prov" onchange="fillProv('sug-prov','sug-ibox')" style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;"></select>
      <div id="sug-ibox" class="ibox" style="display:none;margin-top:6px;"></div>
    </div>
    <table style="width:100%;border-collapse:collapse;font-size:12px;">
      <thead><tr style="background:#fef3c7;font-weight:600;color:#78350f;">
        <th style="padding:6px 4px;text-align:left;">Material</th>
        <th style="padding:6px 4px;text-align:right;width:80px;">Stock actual</th>
        <th style="padding:6px 4px;text-align:right;width:70px;">Deficit</th>
        <th style="padding:6px 4px;text-align:center;width:100px;">Cantidad (g)</th>
        <th style="padding:6px 4px;text-align:center;width:90px;">Precio/g</th>
        <th style="padding:6px 4px;text-align:right;width:85px;">Subtotal</th>
      </tr></thead>
      <tbody id="sug-tbody"></tbody>
    </table>
    <div style="display:flex;justify-content:flex-end;margin-top:10px;font-size:15px;font-weight:700;color:#1c1917;">
      Total: <span id="sug-tot" style="margin-left:6px;">$0</span>
    </div>
  </div>
  <div class="mf">
    <button class="btn bo" onclick="closeModal('m-oc-sug')">Cancelar</button>
    <button class="btn bp" onclick="crearOCSugerida()">&#x2713; Crear OC Borrador</button>
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
var MP_ITMS = 0;
var _MPCAT = [];
var _ALERTAS_MP = [];

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
    else if(tab==='solic') loadSolicitudes();
    else if(tab==='influencer') loadInfluencers();
    else{ renderCat(tab); if(tab==='mp') renderMPAlerts(); }
    var fab = document.getElementById('fab-btn');
    if(tab==='prov'||tab==='solic'||tab==='influencer'){ fab.style.display='none'; }
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
  try{
    var r3 = await fetch('/api/maestro-mps');
    if(!r3.ok) throw new Error('Cat API '+r3.status);
    var d3 = await r3.json();
    _MPCAT = d3.mps||[];
  }catch(e){ console.error('MPCAT load error:',e); _MPCAT=[]; }
  try{
    var r4 = await fetch('/api/alertas-reabastecimiento');
    if(!r4.ok) throw new Error('Alert API '+r4.status);
    var d4 = await r4.json();
    _ALERTAS_MP = (d4.alertas||[]).filter(function(a){ return a.tipo==='MP'; });
  }catch(e){ console.error('Alert load error:',e); _ALERTAS_MP=[]; }
  renderDash();
  renderMPAlerts();
}

// ─── Dashboard ────────────────────────────────────────────────────
function renderDash(){
  var _noInfl=function(o){ return (o.categoria||'').indexOf('Influencer')<0; };
  var autList = OCS.filter(function(o){ return o.estado==='Revisada' && _noInfl(o); });
  var pagList = OCS.filter(function(o){ return o.estado==='Autorizada' && _noInfl(o); });
  var recList = OCS.filter(function(o){ return o.estado==='Pagada' && _noInfl(o); });
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
  var btns='<button class="btn bo bs" data-act="det" data-oc="'+esc(o.numero_oc)+'">Ver detalle</button>';
  if(o.estado==='Revisada'&&!ES_C) btns+='<button class="btn bi bs" data-act="aut" data-oc="'+esc(o.numero_oc)+'">Autorizar</button>';
  if(o.estado==='Autorizada'&&!ES_C) btns+='<button class="btn bg bs" data-act="pago" data-oc="'+esc(o.numero_oc)+'" data-val="'+parseFloat(o.valor_total||0)+'" data-prov="'+esc(o.proveedor||'')+'">Pagar</button>';
  return '<div class="card" style="margin-bottom:8px;">'+
    '<div class="ch"><div><div class="cnum">'+esc(o.numero_oc)+'</div><div class="cprov">'+esc(o.proveedor||'-')+'</div></div>'+badge(o.estado)+'</div>'+
    '<div class="cval">'+fmt(o.valor_total)+(o.con_iva?'<span style="font-size:10px;background:#fde047;color:#92400e;border-radius:3px;padding:1px 5px;margin-left:5px;">+IVA</span>':'')+'</div>'+
    '<div class="cmeta"><span>'+fdate(o.fecha)+'</span>'+(o.fecha_entrega_est?'<span>&#x23F0; '+fdate(o.fecha_entrega_est)+'</span>':'')+'</div>'+
    (btns?'<div class="acts">'+btns+'</div>':'')+'</div>';
}

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
  var btns='<button class="btn bo bs" data-act="det" data-oc="'+esc(o.numero_oc)+'">&#128203; Ver</button>';
  if(o.estado==='Borrador'&&ES_C) btns+='<button class="btn bw bs" data-act="rev" data-oc="'+esc(o.numero_oc)+'" data-prov="'+esc(o.proveedor||'')+'" data-val="'+parseFloat(o.valor_total||0)+'" data-obs="'+esc((o.observaciones||'').substring(0,80))+'">Revisar &amp; Asignar</button>';
  if(o.estado==='Revisada'&&!ES_C) btns+='<button class="btn bi bs" data-act="aut" data-oc="'+esc(o.numero_oc)+'">Autorizar</button>';
  if(o.estado==='Autorizada'&&!ES_C) btns+='<button class="btn bg bs" data-act="pago" data-oc="'+esc(o.numero_oc)+'" data-val="'+parseFloat(o.valor_total||0)+'" data-prov="'+esc(o.proveedor||'')+'">Registrar Pago</button>';
  if(o.estado==='Pagada'&&!ES_C&&(grp==='mp'||grp==='mee')) btns+='<button class="btn bo bs" data-act="rec" data-oc="'+esc(o.numero_oc)+'">Marcar Recibida</button>';
  return '<div class="card">'+
    '<div class="ch"><div><div class="cnum">'+esc(o.numero_oc)+'</div><div class="cprov">'+esc(o.proveedor||'-')+'</div></div>'+badge(o.estado)+'</div>'+
    '<div class="cmeta"><span>&#x1F4C5; '+fdate(o.fecha)+'</span>'+(o.fecha_entrega_est?'<span>&#x23F0; '+fdate(o.fecha_entrega_est)+'</span>':'')+'<span>'+o.num_items+' item(s)</span></div>'+
    (o.observaciones?'<div class="cobs">'+esc((o.observaciones||'').substring(0,90))+'</div>':'')+
    '<div class="cval">'+fmt(o.valor_total)+(o.con_iva?'<span style="font-size:10px;background:#fde047;color:#92400e;border-radius:3px;padding:1px 5px;margin-left:5px;">+IVA</span>':'')+'</div>'+
    (btns?'<div class="acts">'+btns+'</div>':'')+'</div>';
}

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
  if(catCode==='MP'||catCode==='mp'){ openNuevaOCMP(); return; }
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


// ─── MP: Banner de alertas ──────────────────────────────────
function renderMPAlerts(){
  var banner=document.getElementById('mp-alert-banner');
  var text=document.getElementById('mp-alert-text');
  var list=document.getElementById('mp-alert-list');
  if(!banner) return;
  if(!_ALERTAS_MP||!_ALERTAS_MP.length){ banner.style.display='none'; return; }
  var total_def=_ALERTAS_MP.reduce(function(s,a){ return s+parseFloat(a.deficit||0); },0);
  banner.style.display='block';
  text.textContent=_ALERTAS_MP.length+' MPs bajo stock mínimo — Deficit total: '+Math.round(total_def/1000)+'kg';
  list.innerHTML=_ALERTAS_MP.slice(0,8).map(function(a){
    var pct=a.stock_minimo>0?Math.round(a.stock_actual/a.stock_minimo*100):0;
    var col=pct<30?'#dc2626':'#d97706';
    return '<span style="background:#fff;border:1px solid '+col+';color:'+col
      +';border-radius:4px;padding:2px 8px;font-size:11px;font-weight:600;">'
      +esc(a.nombre.substring(0,24))+' ('+Math.round(a.stock_actual)+'g / min '+Math.round(a.stock_minimo)+'g)</span>';
  }).join('');
}

// ─── MP: Nueva OC con catálogo ───────────────────────────
function openNuevaOCMP(prefillItems){
  MP_ITMS=0;
  document.getElementById('nmp-tbody').innerHTML='';
  document.getElementById('nmp-prov').value='';
  document.getElementById('nmp-ibox').style.display='none';
  document.getElementById('nmp-fent').value='';
  document.getElementById('nmp-obs').value='';
  document.getElementById('nmp-tot').textContent='$0';
  fillProvSelect('nmp-prov');
  var dl=document.getElementById('mp-codes-dl');
  dl.innerHTML=_MPCAT.map(function(m){
    return '<option value="'+esc(m.codigo_mp)+'">'+esc(m.nombre_comercial||m.nombre_inci||m.codigo_mp)+'</option>';
  }).join('');
  var info=document.getElementById('nmp-alert-info');
  if(_ALERTAS_MP&&_ALERTAS_MP.length){
    info.style.display='block';
    info.textContent='⚠️ '+_ALERTAS_MP.length+' MPs bajo stock mínimo. Al escribir un código verás stock en tiempo real.';
  } else { info.style.display='none'; }
  if(prefillItems&&prefillItems.length){
    prefillItems.forEach(function(it){ addRowMP(it); });
  } else { addRowMP(null); addRowMP(null); }
  openModal('m-noc-mp');
}
function addRowMP(prefill){
  MP_ITMS++;
  var n=MP_ITMS;
  var cod=(prefill&&prefill.codigo_mp)||'';
  var nom=(prefill&&prefill.nombre_mp)||'';
  var qty=(prefill&&prefill.cantidad_g)||'';
  var prc=(prefill&&prefill.precio_unitario)||'';
  var tr=document.createElement('tr');
  tr.id='mpr'+n;
  tr.innerHTML=
    '<td style="padding:3px;">'
      +'<input id="mprc'+n+'" list="mp-codes-dl" placeholder="COD" value="'+esc(cod)+'"'
      +' style="width:95px;padding:5px;border:1px solid #d6d3d1;border-radius:4px;font-size:12px;"'
      +' onchange="mpLookup('+n+')" oninput="mpLookupDebounce('+n+')">';
  tr.innerHTML+=
    '</td>'
    +'<td style="padding:3px;min-width:150px;">'
      +'<input id="mprn'+n+'" placeholder="Descripcion" value="'+esc(nom)+'"'
      +' style="width:100%;padding:5px;border:1px solid #d6d3d1;border-radius:4px;font-size:12px;">'
      +'<div id="mpri'+n+'" style="font-size:10px;margin-top:2px;"></div>'
    +'</td>'
    +'<td style="padding:3px;">'
      +'<input id="mprq'+n+'" type="number" value="'+esc(qty)+'" min="0" placeholder="g"'
      +' oninput="calcTotMP()" style="width:80px;padding:5px;border:1px solid #d6d3d1;border-radius:4px;font-size:12px;text-align:right;">'
    +'</td>'
    +'<td style="padding:3px;">'
      +'<input id="mprp'+n+'" type="number" value="'+esc(prc)+'" min="0" step="0.001" placeholder="$/g"'
      +' oninput="calcTotMP()" style="width:85px;padding:5px;border:1px solid #d6d3d1;border-radius:4px;font-size:12px;text-align:right;">'
    +'</td>'
    +'<td id="mprs'+n+'" style="padding:3px 6px;text-align:right;white-space:nowrap;font-size:12px;">$0</td>'
    +'<td style="padding:3px 2px;">'
      +'<button class="btn bo" style="padding:2px 6px;font-size:11px;" onclick="rmRowMP('+n+')">x</button>'
    +'</td>';
  document.getElementById('nmp-tbody').appendChild(tr);
  if(prefill) calcTotMP();
}
function rmRowMP(n){ var e=document.getElementById('mpr'+n); if(e){ e.remove(); calcTotMP(); } }
var _mpLT={};
function mpLookupDebounce(n){
  if(_mpLT[n]) clearTimeout(_mpLT[n]);
  _mpLT[n]=setTimeout(function(){ mpLookup(n); },300);
}
function mpLookup(n){
  var codEl=document.getElementById('mprc'+n);
  var namEl=document.getElementById('mprn'+n);
  var infEl=document.getElementById('mpri'+n);
  var prcEl=document.getElementById('mprp'+n);
  if(!codEl||!infEl) return;
  var cod=(codEl.value||'').trim();
  if(!cod){ infEl.textContent=''; return; }
  var mp=_MPCAT.find(function(m){ return m.codigo_mp===cod; });
  if(!mp&&cod.length>=4){
    var q=cod.toLowerCase();
    mp=_MPCAT.find(function(m){
      return (m.nombre_comercial||'').toLowerCase().indexOf(q)>=0
          ||(m.nombre_inci||'').toLowerCase().indexOf(q)>=0;
    });
  }
  if(!mp){ infEl.textContent=''; infEl.style.color='#78716c'; return; }
  if(!(namEl.value||'').trim()) namEl.value=mp.nombre_comercial||mp.nombre_inci||cod;
  if((!prcEl.value||parseFloat(prcEl.value)===0)&&mp.precio_referencia&&mp.precio_referencia>0){
    prcEl.value=parseFloat(mp.precio_referencia).toFixed(4);
    calcTotMP();
  }
  var alerta=_ALERTAS_MP.find(function(a){ return a.codigo_mp===mp.codigo_mp; });
  if(alerta){
    infEl.style.color='#dc2626';
    infEl.textContent='⚠ Stock: '+Math.round(alerta.stock_actual)+'g / Min: '+Math.round(mp.stock_minimo)+'g | Deficit: '+Math.round(alerta.deficit)+'g';
  } else {
    infEl.style.color='#16a34a';
    infEl.textContent='✓ Stock OK | Min: '+Math.round(mp.stock_minimo||0)+'g'+(mp.precio_referencia?' | Ref: $'+parseFloat(mp.precio_referencia).toFixed(2)+'/g':'');
  }
}
function calcTotMP(){
  var tot=0;
  for(var i=1;i<=MP_ITMS;i++){
    var q=document.getElementById('mprq'+i),p=document.getElementById('mprp'+i);
    if(!q||!p) continue;
    var s=parseFloat(q.value||0)*parseFloat(p.value||0);
    var el=document.getElementById('mprs'+i); if(el) el.textContent=fmt(s);
    tot+=s;
  }
  var totEl=document.getElementById('nmp-tot'); if(totEl) totEl.textContent=fmt(tot);
}
async function crearOCMP(){
  var prov=document.getElementById('nmp-prov').value;
  var obs=document.getElementById('nmp-obs').value;
  var fent=document.getElementById('nmp-fent').value;
  if(!prov){ alert('Selecciona un proveedor'); return; }
  var items=[];
  for(var i=1;i<=MP_ITMS;i++){
    var n=document.getElementById('mprn'+i);
    if(!n||(n.value||'').trim()==='') continue;
    items.push({
      codigo_mp:(document.getElementById('mprc'+i)||{value:''}).value,
      nombre_mp:n.value.trim(),
      cantidad_g:parseFloat((document.getElementById('mprq'+i)||{value:1}).value||1),
      precio_unitario:parseFloat((document.getElementById('mprp'+i)||{value:0}).value||0)
    });
  }
  if(!items.length){ alert('Agrega al menos un item con descripcion'); return; }
  try{
    var body={proveedor:prov,categoria:'MP',observaciones:obs,items:items,creado_por:'{usuario}'};
    if(fent) body.fecha_entrega_est=fent;
    var r=await fetch('/api/ordenes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    closeModal('m-noc-mp');
    await loadData();
    renderCat('mp');
    alert('OC creada: '+d.numero_oc);
  }catch(e){ alert('Error de conexion: '+e); }
}

// ─── MP: OC Sugerida desde alertas ───────────────────────
function openOCSugerida(){
  if(!_ALERTAS_MP||!_ALERTAS_MP.length){ alert('No hay MPs bajo stock mínimo'); return; }
  fillProvSelect('sug-prov');
  document.getElementById('sug-prov').value='';
  document.getElementById('sug-ibox').style.display='none';
  var tbody=document.getElementById('sug-tbody');
  tbody.innerHTML=_ALERTAS_MP.map(function(a,i){
    var mp=_MPCAT.find(function(m){ return m.codigo_mp===a.codigo_mp; });
    var pref=(mp&&mp.precio_referencia>0)?parseFloat(mp.precio_referencia).toFixed(4):'';
    var qty=Math.ceil(a.deficit*1.2/100)*100;
    return '<tr id="sugr'+i+'">'
      +'<td style="padding:5px 4px;">'
        +'<div style="font-weight:600;font-size:12px;">'+esc(a.nombre.substring(0,35))+'</div>'
        +'<div style="font-size:10px;color:#78716c;">'+esc(a.codigo_mp)+(a.proveedor?' · '+esc(a.proveedor):'')+'</div>'
      +'</td>'
      +'<td style="padding:5px 4px;text-align:right;font-size:12px;">'+Math.round(a.stock_actual)+'g</td>'
      +'<td style="padding:5px 4px;text-align:right;font-size:12px;color:#dc2626;font-weight:600;">'+Math.round(a.deficit)+'g</td>'
      +'<td style="padding:5px 4px;">'
        +'<input id="sugq'+i+'" type="number" value="'+qty+'" min="0" oninput="calcTotSug()"'
        +' style="width:95px;padding:4px;border:1px solid #d6d3d1;border-radius:4px;font-size:12px;text-align:right;">'
      +'</td>'
      +'<td style="padding:5px 4px;">'
        +'<input id="sugp'+i+'" type="number" value="'+pref+'" min="0" step="0.001" placeholder="$/g" oninput="calcTotSug()"'
        +' style="width:85px;padding:4px;border:1px solid #d6d3d1;border-radius:4px;font-size:12px;text-align:right;">'
      +'</td>'
      +'<td id="sugs'+i+'" style="padding:5px 4px;text-align:right;font-size:12px;white-space:nowrap;">$0</td>'
      +'</tr>';
  }).join('');
  calcTotSug();
  openModal('m-oc-sug');
}
function calcTotSug(){
  var tot=0;
  for(var i=0;i<_ALERTAS_MP.length;i++){
    var q=document.getElementById('sugq'+i),p=document.getElementById('sugp'+i);
    if(!q||!p) continue;
    var s=parseFloat(q.value||0)*parseFloat(p.value||0);
    var el=document.getElementById('sugs'+i); if(el) el.textContent=fmt(s);
    tot+=s;
  }
  var totEl=document.getElementById('sug-tot'); if(totEl) totEl.textContent=fmt(tot);
}
async function crearOCSugerida(){
  var prov=document.getElementById('sug-prov').value;
  if(!prov){ alert('Selecciona un proveedor'); return; }
  var items=[];
  for(var i=0;i<_ALERTAS_MP.length;i++){
    var a=_ALERTAS_MP[i];
    var q=parseFloat((document.getElementById('sugq'+i)||{value:0}).value||0);
    var p=parseFloat((document.getElementById('sugp'+i)||{value:0}).value||0);
    if(q<=0) continue;
    items.push({codigo_mp:a.codigo_mp,nombre_mp:a.nombre,cantidad_g:q,precio_unitario:p});
  }
  if(!items.length){ alert('Todas las cantidades son 0 — ajusta antes de crear'); return; }
  try{
    var r=await fetch('/api/ordenes-compra',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({proveedor:prov,categoria:'MP',creado_por:'{usuario}',
        observaciones:'OC sugerida — MPs bajo stock ('+new Date().toLocaleDateString('es-CO')+')',
        items:items})});
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    closeModal('m-oc-sug');
    await loadData();
    renderCat('mp');
    alert('OC sugerida creada: '+d.numero_oc);
  }catch(e){ alert('Error de conexion: '+e); }
}

// ─── Revisar ──────────────────────────────────────────────────────
function openRev(num,prov,val,obs,conIva,valBase){
  var oc=OCS.find(function(o){ return o.numero_oc===num; })||{};
  var ivaActivo=conIva!==undefined ? !!conIva : !!(oc.con_iva);
  var base=valBase!==undefined ? valBase : (oc.valor_sin_iva>0 ? oc.valor_sin_iva : (ivaActivo ? parseFloat(val||0)/1.19 : parseFloat(val||0)));
  document.getElementById('rev-num').value=num;
  document.getElementById('rev-info').innerHTML='<strong>'+num+'</strong><br><span style="color:#78716c;">'+esc(obs||'-')+'</span>';
  document.getElementById('rev-val').value=base>0 ? base.toFixed(0) : (val||'');
  document.getElementById('rev-iva-chk').checked=ivaActivo;
  document.getElementById('rev-obs').value='';
  document.getElementById('rev-fent').value='';
  document.getElementById('rev-ibox').style.display='none';
  fillProvSelect('rev-prov');
  document.getElementById('rev-prov').value=prov;
  if(prov) fillProv('rev-prov','rev-ibox');
  calcRevIva();
  openModal('m-rev');
}
function calcRevIva(){
  var base=parseFloat(document.getElementById('rev-val').value)||0;
  var chk=document.getElementById('rev-iva-chk').checked;
  var bd=document.getElementById('rev-iva-breakdown');
  if(chk && base>0){
    var iva=base*0.19;
    var tot=base+iva;
    var fmt2=function(n){ return '$'+Math.round(n).toLocaleString('es-CO'); };
    document.getElementById('rev-iva-sub').textContent=fmt2(base);
    document.getElementById('rev-iva-monto').textContent=fmt2(iva);
    document.getElementById('rev-iva-total').textContent=fmt2(tot);
    bd.style.display='block';
  } else {
    bd.style.display='none';
  }
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
    var conIva=document.getElementById('rev-iva-chk').checked;
    var baseVal=parseFloat(val)||0;
    var totalVal=conIva ? Math.round(baseVal*1.19*100)/100 : baseVal;
    var body={proveedor:prov,valor_total:totalVal,observaciones:obs,con_iva:conIva,valor_sin_iva:baseVal};
    if(fent) body.fecha_entrega_est=fent;
    var r=await fetch('/api/ordenes-compra/'+num+'/revisar',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    closeModal('m-rev');
    await loadData();
  }catch(e){ alert('Error: '+e); }
}

// ─── Autorizar ────────────────────────────────────────────────────
// ─── Autorizar (abre modal con opcion rechazar) ───────────────────
function autorizarOC(num){
  var oc=OCS.find(function(o){ return o.numero_oc===num; })||{};
  document.getElementById('aut-num').value=num;
  document.getElementById('aut-motivo').value='';
  document.getElementById('m-aut-info').innerHTML=
    '<strong>'+esc(num)+'</strong> &mdash; '+esc(oc.proveedor||'-')+
    '<br><span style="color:#78716c;font-size:12px;">Valor: <strong>'+fmt(oc.valor_total)+'</strong>'+
    (oc.observaciones?' &nbsp;|&nbsp; '+esc((oc.observaciones||'').substring(0,80)):'')+
    '</span>';
  openModal('m-aut');
}
async function decidirOC(decision){
  var num=document.getElementById('aut-num').value;
  var motivo=document.getElementById('aut-motivo').value.trim();
  if(decision==='Rechazada'&&!motivo){
    if(!confirm('Rechazar sin motivo. Confirmar?')) return;
  }
  if(decision==='Autorizada'){
    try{
      var r=await fetch('/api/ordenes-compra/'+num+'/autorizar',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({motivo:motivo})});
      var d=await r.json();
      if(d.error){ alert('Error: '+d.error); return; }
    }catch(e){ alert('Error: '+e); return; }
  } else {
    try{
      var r2=await fetch('/api/ordenes-compra/'+num,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:'Rechazada',motivo:motivo})});
      var d2=await r2.json();
      if(d2.error){ alert('Error: '+d2.error); return; }
    }catch(e){ alert('Error: '+e); return; }
  }
  closeModal('m-aut');
  await loadData();
  renderDash();
}

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
    var r=await fetch('/api/ordenes-compra/'+num+'/recibir',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
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

// ─── Event delegation para botones de OC ────────────────────
document.addEventListener('click',function(e){
  var btn=e.target.closest('[data-act]');
  if(!btn) return;
  var act=btn.getAttribute('data-act');
  var oc=btn.getAttribute('data-oc');
  if(act==='aut') autorizarOC(oc);
  else if(act==='pago') openPago(oc,parseFloat(btn.getAttribute('data-val')||0),btn.getAttribute('data-prov')||'');
  else if(act==='rev') openRev(oc,btn.getAttribute('data-prov')||'',parseFloat(btn.getAttribute('data-val')||0),btn.getAttribute('data-obs')||'');
  else if(act==='rec') marcarRecibida(oc);
  else if(act==='det') openOCDetail(oc);
  else if(act==='sdet') openSolicitudDetail(btn.getAttribute('data-sol')||'');
});

// ─── Globals para modales de detalle (evita escaping de quotes) ───
var _detOC={};  // OC abierta en modal detalle
var _detSol={estado:''}; // Solicitud abierta en modal detalle

// Wrappers sin argumentos para botones de footer (sin riesgo de escaping)
function _ocDetClose(){ closeModal('m-oc-det'); }
function _ocDetAut(){ closeModal('m-oc-det'); autorizarOC(_detOC.numero_oc||''); }
function _ocDetPago(){ closeModal('m-oc-det'); openPago(_detOC.numero_oc||'',parseFloat(_detOC.valor_total||0),_detOC.proveedor||''); }
function _ocDetRev(){ closeModal('m-oc-det'); openRev(_detOC.numero_oc||'',_detOC.proveedor||'',parseFloat(_detOC.valor_total||0),(_detOC.observaciones||'').substring(0,80),_detOC.con_iva,parseFloat(_detOC.valor_sin_iva||0)); }
function _solDetClose(){ closeModal('m-sol-det'); }
function _solDetApr(){ gestionarSol('Aprobada'); }
function _solDetRech(){ gestionarSol('Rechazada'); }
function _solFillProv(){
  var v=(document.getElementById('sol-prov-sel')||{value:''}).value;
  var tb=document.getElementById('sol-tercero-box');
  var nb=document.getElementById('sol-nuevo-prov-box');
  if(tb) tb.style.display = v==='__tercero__' ? 'block' : 'none';
  if(nb) nb.style.display = v==='__nuevo__' ? 'block' : 'none';
  if(v!=='__tercero__'&&v!=='__nuevo__') fillProv('sol-prov-sel','sol-prov-ibox');
}
async function _guardarNuevoProv(){
  var nombre=(document.getElementById('snp-nombre')||{value:''}).value.trim();
  if(!nombre){ alert('El nombre del proveedor es obligatorio'); return; }
  var banco=(document.getElementById('snp-banco')||{value:''}).value.trim();
  var tipo=(document.getElementById('snp-tipo')||{value:'Ahorros'}).value;
  var cuenta=(document.getElementById('snp-cuenta')||{value:''}).value.trim();
  var nit=(document.getElementById('snp-nit')||{value:''}).value.trim();
  var body={nombre:nombre,nit:nit,banco:banco,tipo_cuenta:tipo,numero_cuenta:cuenta,categoria:'Cuenta de Cobro',condiciones_pago:'Inmediato'};
  try{
    var r=await fetch('/api/proveedores-compras',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    PROVS.push({nombre:nombre,nit:nit,banco:banco,tipo_cuenta:tipo,numero_cuenta:cuenta});
    var sel=document.getElementById('sol-prov-sel');
    var opt=document.createElement('option');
    opt.value=nombre; opt.textContent=nombre; opt.selected=true;
    var nuevoOpt=sel.querySelector('option[value="__nuevo__"]');
    if(nuevoOpt) sel.insertBefore(opt, nuevoOpt); else sel.appendChild(opt);
    var nb=document.getElementById('sol-nuevo-prov-box');
    if(nb) nb.style.display='none';
    fillProv('sol-prov-sel','sol-prov-ibox');
    alert('Proveedor guardado y seleccionado.');
  }catch(e){ alert('Error: '+e); }
}

// ─── Detalle OC ─────────────────────────────────────────────────
async function openOCDetail(num){
  openModal('m-oc-det');
  var body=document.getElementById('oc-det-body');
  var footer=document.getElementById('oc-det-footer');
  body.innerHTML='<div style="text-align:center;padding:40px;color:#78716c;">Cargando...</div>';
  footer.innerHTML='<button class="btn bo" onclick="_ocDetClose()">Cerrar</button>';
  _detOC={};
  try{
    var r=await fetch('/api/ordenes-compra/'+encodeURIComponent(num));
    var d=await r.json();
    if(d.error){ body.innerHTML='<p style="color:#dc2626;">'+esc(d.error)+'</p>'; return; }
    var o=d.oc||{}; _detOC=o;
    var items=d.items||[];
    var estColor={'Borrador':'#78716c','Revisada':'#d97706','Autorizada':'#2563eb','Pagada':'#16a34a','Recibida':'#14532d','Rechazada':'#dc2626'}[o.estado]||'#78716c';
    var h='<div style="padding:16px 20px;">';
    h+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">';
    h+='<div><div style="font-weight:800;font-size:16px;font-family:monospace;">'+esc(o.numero_oc||num)+'</div>';
    h+='<div style="color:#57534e;font-size:13px;">'+esc(o.proveedor||'-')+'</div></div>';
    h+='<span class="badge" style="background:'+estColor+'22;color:'+estColor+';font-size:12px;">'+esc(o.estado||'')+'</span></div>';
    h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px;margin-bottom:12px;background:#f9f8f7;border-radius:6px;padding:10px;">';
    h+='<div><span style="color:#78716c;">Fecha:</span> '+fdate(o.fecha)+'</div>';
    h+='<div><span style="color:#78716c;">Entrega est.:</span> '+(o.fecha_entrega_est?fdate(o.fecha_entrega_est):'-')+'</div>';
    h+='<div><span style="color:#78716c;">Creado por:</span> '+esc(o.creado_por||'-')+'</div>';
    h+='<div><span style="color:#78716c;">Autorizado por:</span> '+esc(o.autorizado_por||'-')+'</div>';
    if(o.valor_total){
      var ivaTxt='';
      if(o.con_iva && o.valor_sin_iva>0){
        var ivaAmt=Math.round(o.valor_sin_iva*0.19);
        ivaTxt=' <span style="font-size:11px;background:#fde047;color:#92400e;border-radius:3px;padding:1px 6px;margin-left:4px;">+IVA incl.</span>'
          +'<div style="color:#78716c;font-size:11px;margin-top:2px;">Subtotal: '+fmt(o.valor_sin_iva)+' &nbsp;|&nbsp; IVA 19%: '+fmt(ivaAmt)+'</div>';
      }
      h+='<div style="grid-column:span 2;"><span style="color:#78716c;">Valor total:</span> <strong style="font-size:15px;">'+fmt(o.valor_total)+'</strong>'+ivaTxt+'</div>';
    }
    if(o.observaciones) h+='<div style="grid-column:span 2;"><span style="color:#78716c;">Observaciones:</span> '+esc(o.observaciones)+'</div>';
    h+='</div>';
    if(items.length){
      h+='<div style="font-weight:700;font-size:12px;color:#44403c;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">Items del pedido</div>';
      h+='<div style="overflow-x:auto;"><table class="itbl"><thead><tr><th>Codigo</th><th>Descripcion</th><th>Cantidad</th><th style="text-align:right;">Precio U.</th><th style="text-align:right;">Subtotal</th></tr></thead><tbody>';
      items.forEach(function(it){
        var cant=it[3]||it.cantidad_g||0;
        var pu=it[4]||it.precio_unitario||0;
        var sub=it[5]||it.subtotal||0;
        var nom=it[2]||it.nombre_mp||'';
        var cod=it[1]||it.codigo_mp||'';
        h+='<tr><td style="font-family:monospace;font-size:11px;">'+esc(cod)+'</td><td>'+esc(nom)+'</td>';
        h+='<td>'+Number(cant).toLocaleString('es-CO')+'</td>';
        h+='<td style="text-align:right;">'+(pu?fmt(pu):'-')+'</td>';
        h+='<td style="text-align:right;font-weight:700;">'+(sub?fmt(sub):'-')+'</td></tr>';
      });
      h+='</tbody></table></div>';
    } else { h+='<div style="color:#78716c;font-size:13px;">Sin items registrados</div>'; }
    h+='</div>';
    body.innerHTML=h;
    var fbtns='<button class="btn bo" onclick="_ocDetClose()">Cerrar</button>';
    if(o.estado==='Revisada'&&!ES_C) fbtns+='<button class="btn bi" onclick="_ocDetAut()">Autorizar / Rechazar</button>';
    if(o.estado==='Autorizada'&&!ES_C) fbtns+='<button class="btn bg" onclick="_ocDetPago()">Registrar Pago</button>';
    if(o.estado==='Borrador'&&ES_C) fbtns+='<button class="btn bw" onclick="_ocDetRev()">Revisar &amp; Asignar</button>';
    footer.innerHTML=fbtns;
  }catch(e){ body.innerHTML='<p style="color:#dc2626;">Error: '+e.message+'</p>'; }
}

// ─── Solicitudes para Catalina ────────────────────────────────────────
var SOLIC=[];
var INFLUENCERS=[];
async function loadSolicitudes(){
  try{
    var r=await fetch('/api/solicitudes-compra');
    var d=await r.json();
    SOLIC=d.solicitudes||[];
  }catch(e){ SOLIC=[]; }
  renderSolicitudes();
}
async function loadInfluencers(){
  try{
    var r=await fetch('/api/solicitudes-compra?categoria=Influencer%2FMarketing+Digital');
    var d=await r.json();
    INFLUENCERS=d.solicitudes||[];
  }catch(e){ INFLUENCERS=[]; }
  renderInfluencers();
}
function fmoney(v){ return '$'+Number(v||0).toLocaleString('es-CO'); }
function renderInfluencers(){
  var q=(document.getElementById('q-influencer')||{value:''}).value.toLowerCase();
  var st=(document.getElementById('s-influencer')||{value:''}).value;
  var list=INFLUENCERS.filter(function(s){
    if(st&&s.estado!==st) return false;
    if(q&&(s.numero||'').toLowerCase().indexOf(q)<0&&(s.solicitante||'').toLowerCase().indexOf(q)<0&&(s.observaciones||'').toLowerCase().indexOf(q)<0) return false;
    return true;
  });
  // KPI cards
  var pendAll=INFLUENCERS.filter(function(s){ return s.estado==='Aprobada'; });
  var totalPend=pendAll.reduce(function(a,s){ return a+(s.valor||0); },0);
  var kpiEl=document.getElementById('kpi-influencer');
  if(kpiEl){
    kpiEl.innerHTML=
      '<div style="background:#7c3aed;color:#fff;padding:12px 20px;border-radius:8px;min-width:160px;">'
      +'<div style="font-size:11px;opacity:.8;text-transform:uppercase;letter-spacing:.5px;">Por pagar</div>'
      +'<div style="font-size:22px;font-weight:700;margin-top:2px;">'+pendAll.length+' OCs</div>'
      +'<div style="font-size:13px;opacity:.9;margin-top:2px;">'+fmoney(totalPend)+'</div>'
      +'</div>'
      +'<div style="background:#059669;color:#fff;padding:12px 20px;border-radius:8px;min-width:160px;">'
      +'<div style="font-size:11px;opacity:.8;text-transform:uppercase;letter-spacing:.5px;">Pagadas</div>'
      +'<div style="font-size:22px;font-weight:700;margin-top:2px;">'+INFLUENCERS.filter(function(s){return s.estado==="Pagada";}).length+'</div>'
      +'</div>'
      +'<div style="background:#6b7280;color:#fff;padding:12px 20px;border-radius:8px;min-width:160px;">'
      +'<div style="font-size:11px;opacity:.8;text-transform:uppercase;letter-spacing:.5px;">Total influencers</div>'
      +'<div style="font-size:22px;font-weight:700;margin-top:2px;">'+INFLUENCERS.length+'</div>'
      +'</div>';
  }
  // Pills
  var pills='<span class="pill">'+list.length+' mostradas</span>';
  var el=document.getElementById('pills-influencer');
  var gel=document.getElementById('grid-influencer');
  if(el) el.innerHTML=pills;
  if(!gel) return;
  if(!list.length){ gel.innerHTML='<div class="empty">No hay cuentas de cobro</div>'; return; }
  var stCfg={
    'Aprobada':  {bg:'#ede9fe',fg:'#5b21b6',label:'Lista para pagar'},
    'Pagada':    {bg:'#d1fae5',fg:'#065f46',label:'Pagada'},
    'Rechazada': {bg:'#fee2e2',fg:'#991b1b',label:'Rechazada'},
    'Pendiente': {bg:'#fef3c7',fg:'#92400e',label:'Pendiente'}
  };
  gel.innerHTML=list.map(function(s){
    var cfg=stCfg[s.estado]||{bg:'#f3f4f6',fg:'#374151',label:s.estado};
    var obsCorta=(s.observaciones||'').substring(0,120);
    var btns='';
    if(s.estado==='Aprobada'){
      btns='<button class="btn inf-pagar" data-oc="'+esc(s.numero_oc||'')+'" data-sol="'+esc(s.numero)+'" data-val="'+Number(s.valor||0)+'" style="background:#7c3aed;color:#fff;font-size:13px;">&#x1F4B8; Pagar</button>'
          +'<button class="btn inf-rechazar" data-oc="'+esc(s.numero_oc||'')+'" data-sol="'+esc(s.numero)+'" style="background:#dc2626;color:#fff;font-size:13px;">&#x2715; Rechazar</button>';
    } else if(s.estado==='Pagada'){
      btns='<span style="color:#065f46;font-weight:600;font-size:13px;">&#x2713; Pagado</span>';
    } else if(s.estado==='Rechazada'){
      btns='<span style="color:#991b1b;font-weight:600;font-size:13px;">&#x2715; Rechazada</span>';
    }
    return '<div class="card">'
      +'<div class="ch"><div><div class="cnum" style="font-family:monospace;">'+esc(s.numero)+'</div>'
      +'<div class="cprov">'+esc(s.solicitante||'-')+' &mdash; '+esc(s.area||'-')+'</div></div>'
      +'<span class="badge" style="background:'+cfg.bg+';color:'+cfg.fg+';">'+cfg.label+'</span></div>'
      +'<div class="cmeta"><span>'+fdate(s.fecha)+'</span>'
      +(s.numero_oc?'<span style="font-family:monospace;font-size:11px;color:#6b7280;">'+esc(s.numero_oc)+'</span>':'')
      +'<span style="color:#7c3aed;font-weight:600;">'+fmoney(s.valor)+'</span></div>'
      +(obsCorta?'<div class="cobs">'+esc(obsCorta)+'</div>':'')
      +(btns?'<div class="acts">'+btns+'</div>':'')
      +'</div>';
  }).join('');
  // Event delegation for pagar/rechazar buttons
  gel.onclick=function(e){
    var bp=e.target.closest('.inf-pagar');
    var br=e.target.closest('.inf-rechazar');
    if(bp) pagarInfluencer(bp.dataset.oc, bp.dataset.sol, Number(bp.dataset.val));
    if(br) rechazarInfluencer(br.dataset.oc, br.dataset.sol);
  };
}
// ─── Pagar influencer ───────────────────────────────────────────────
function pagarInfluencer(oc_num, sol_num, valor){
  if(!oc_num){ alert('Esta solicitud no tiene OC vinculada. Contacta a Sebastian.'); return; }
  var confirmado=confirm('Confirmar pago ' + fmoney(valor) + ' para ' + sol_num + ' | OC: ' + oc_num + ' | Se registrará en Finanzas.');
  if(!confirmado) return;
  fetch('/api/ordenes-compra/'+encodeURIComponent(oc_num)+'/pagar',{
    method:'PATCH',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({monto:valor,medio:'Transferencia',observaciones:'Pago influencer '+sol_num})
  }).then(function(r){return r.json();}).then(function(d){
    if(d.ok){
      alert('Pago registrado. La OC quedó como Pagada y el egreso fue enviado a Finanzas.');
      loadInfluencers();
    } else { alert('Error: '+(d.error||'desconocido')); }
  }).catch(function(){ alert('Error de conexión'); });
}
// ─── Rechazar influencer ────────────────────────────────────────────
var _rechazarOC='', _rechazarSol='';
function rechazarInfluencer(oc_num, sol_num){
  if(!oc_num){ alert('Esta solicitud no tiene OC vinculada.'); return; }
  _rechazarOC=oc_num; _rechazarSol=sol_num;
  var m=document.getElementById('motivo-rechazo-inf');
  if(m) m.value='';
  openModal('m-rechazar-inf');
  var btn=document.getElementById('btn-confirmar-rechazo');
  if(btn){
    btn.onclick=function(){
      var motivo=(document.getElementById('motivo-rechazo-inf')||{value:''}).value.trim();
      if(!motivo){ alert('El motivo es obligatorio para rechazar.'); return; }
      fetch('/api/compras/oc/'+encodeURIComponent(_rechazarOC)+'/rechazar',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({motivo:motivo})
      }).then(function(r){return r.json();}).then(function(d){
        if(d.ok){
          closeModal('m-rechazar-inf');
          alert('OC rechazada. La solicitud volvió a estado Pendiente con el motivo registrado.');
          loadInfluencers();
        } else { alert('Error: '+(d.error||'desconocido')); }
      }).catch(function(){ alert('Error de conexión'); });
    };
  }
}

function renderSolicitudes(){
  var q=(document.getElementById('q-solic')||{value:''}).value.toLowerCase();
  var st=(document.getElementById('s-solic')||{value:''}).value;
  var list=SOLIC.filter(function(s){
    if(st&&s.estado!==st) return false;
    if(q&&(s.numero||'').toLowerCase().indexOf(q)<0&&(s.solicitante||'').toLowerCase().indexOf(q)<0&&(s.observaciones||'').toLowerCase().indexOf(q)<0) return false;
    return true;
  });
  var pend=list.filter(function(s){ return s.estado==='Pendiente'; }).length;
  var apro=list.filter(function(s){ return s.estado==='Aprobada'; }).length;
  var rech=list.filter(function(s){ return s.estado==='Rechazada'; }).length;
  var pills='<span class="pill">'+list.length+' solicitudes</span>';
  if(pend) pills+='<span class="pill y">Pendiente: '+pend+'</span>';
  if(apro) pills+='<span class="pill g">Aprobada: '+apro+'</span>';
  if(rech) pills+='<span class="pill" style="background:#fee2e2;color:#991b1b;">Rechazada: '+rech+'</span>';
  document.getElementById('pills-solic').innerHTML=pills;
  if(!list.length){ document.getElementById('grid-solic').innerHTML='<div class="empty">No hay solicitudes</div>'; return; }
  var urgColor={'Normal':'#16a34a','Urgente':'#d97706','Critico':'#dc2626'};
  var stBg={'Pendiente':'#fef3c7','Aprobada':'#dcfce7','Rechazada':'#fee2e2'};
  var stFg={'Pendiente':'#92400e','Aprobada':'#166534','Rechazada':'#991b1b'};
  document.getElementById('grid-solic').innerHTML=list.map(function(s){
    var urg=s.urgencia||'Normal';
    var urgC=urgColor[urg]||'#78716c';
    var stB=stBg[s.estado]||'#f3f4f6';
    var stF=stFg[s.estado]||'#374151';
    return '<div class="card">'
      +'<div class="ch"><div><div class="cnum" style="font-family:monospace;">'+esc(s.numero)+'</div>'
      +'<div class="cprov">'+esc(s.solicitante||'-')+' &mdash; '+esc(s.area||'-')+'</div></div>'
      +'<span class="badge" style="background:'+stB+';color:'+stF+';">'+s.estado+'</span></div>'
      +'<div class="cmeta"><span>'+fdate(s.fecha)+'</span><span>'+esc(s.empresa||'Espagiria')+'</span>'
      +'<span>'+esc(s.categoria||'-')+'</span>'
      +'<span style="color:'+urgC+';font-weight:700;">'+esc(urg)+'</span></div>'
      +(s.observaciones?'<div class="cobs">'+esc((s.observaciones||'').substring(0,100))+'</div>':'')
      +'<div class="acts"><button class="btn bo bs" data-act="sdet" data-sol="'+esc(s.numero)+'">&#128203; Ver &amp; Gestionar</button></div>'
      +'</div>';
  }).join('');
}
async function openSolicitudDetail(num){
  openModal('m-sol-det');
  var body=document.getElementById('sol-det-body');
  var footer=document.getElementById('sol-det-footer');
  body.innerHTML='<div style="text-align:center;padding:40px;color:#78716c;">Cargando...</div>';
  footer.innerHTML='<button class="btn bo" onclick="_solDetClose()">Cerrar</button>';
  try{
    var r=await fetch('/api/solicitudes-compra/'+encodeURIComponent(num));
    var d=await r.json();
    if(d.error){ body.innerHTML='<p style="color:#dc2626;">'+esc(d.error)+'</p>'; return; }
    var s=d.solicitud||{};
    var items=d.items||[];
    var stBg={'Pendiente':'#fef3c7','Aprobada':'#dcfce7','Rechazada':'#fee2e2'};
    var stFg={'Pendiente':'#92400e','Aprobada':'#166534','Rechazada':'#991b1b'};
    var h='<div style="padding:16px 20px;">';
    h+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">';
    h+='<div><div style="font-weight:800;font-size:16px;font-family:monospace;">'+esc(s.numero||num)+'</div>';
    h+='<div style="color:#57534e;font-size:13px;">'+esc(s.solicitante||'-')+' &mdash; '+esc(s.area||'-')+'</div></div>';
    h+='<span class="badge" style="background:'+(stBg[s.estado]||'#f3f4f6')+';color:'+(stFg[s.estado]||'#374151')+';font-size:12px;">'+esc(s.estado||'')+'</span></div>';
    h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px;margin-bottom:12px;background:#f9f8f7;border-radius:6px;padding:10px;">';
    h+='<div><span style="color:#78716c;">Empresa:</span> '+esc(s.empresa||'Espagiria')+'</div>';
    h+='<div><span style="color:#78716c;">Categoria:</span> '+esc(s.categoria||'-')+'</div>';
    h+='<div><span style="color:#78716c;">Tipo:</span> '+esc(s.tipo||'-')+'</div>';
    h+='<div><span style="color:#78716c;">Urgencia:</span> <strong>'+esc(s.urgencia||'Normal')+'</strong></div>';
    h+='<div><span style="color:#78716c;">Fecha:</span> '+fdate(s.fecha)+'</div>';
    if(s.aprobado_por) h+='<div><span style="color:#78716c;">Gestionado por:</span> '+esc(s.aprobado_por)+'</div>';
    if(s.numero_oc) h+='<div style="grid-column:span 2;"><span style="color:#78716c;">OC generada:</span> <strong style="color:#2563eb;">'+esc(s.numero_oc)+'</strong></div>';
    if(s.observaciones) h+='<div style="grid-column:span 2;"><span style="color:#78716c;">Observaciones / Justificacion:</span><br><em>'+esc(s.observaciones)+'</em></div>';
    h+='</div>';
    if(items.length){
      h+='<div style="font-weight:700;font-size:12px;color:#44403c;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">Items solicitados</div>';
      h+='<table class="itbl"><thead><tr><th>Codigo</th><th>Descripcion</th><th>Cantidad</th><th>Valor est.</th></tr></thead><tbody>';
      items.forEach(function(it){
        h+='<tr><td style="font-family:monospace;font-size:11px;">'+esc(it.codigo_mp||'-')+'</td>';
        h+='<td>'+esc(it.nombre_mp||'-')+'</td>';
        h+='<td>'+(it.cantidad_g||0)+' '+(it.unidad||'und')+'</td>';
        h+='<td>'+(it.valor_estimado?fmt(it.valor_estimado):'-')+'</td></tr>';
      });
      h+='</tbody></table>';
    }
    if(s.estado==='Pendiente'){
      h+='<div style="margin-top:16px;background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:14px;">';
      h+='<div style="font-weight:700;font-size:13px;margin-bottom:10px;">&#9997; Gestionar Solicitud</div>';
      h+='<div class="fg" style="margin-bottom:10px;"><label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:4px;">Proveedor / Beneficiario</label>';
      h+='<select id="sol-prov-sel" onchange="_solFillProv()" style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;"><option value="">-- Seleccionar proveedor --</option>';
      h+='<option value="__tercero__">&#x1F4B3; Pago a Terceros (ingrese nombre)</option>';
      PROVS.forEach(function(p){ h+='<option value="'+esc(p.nombre)+'">'+esc(p.nombre)+'</option>'; });
      h+='<option value="__nuevo__">&#x2795; Crear nuevo proveedor...</option>';
      h+='</select>';
      h+='<div id="sol-prov-ibox" class="ibox" style="display:none;margin-top:6px;"></div>';
      h+='<div id="sol-tercero-box" style="display:none;margin-top:6px;"><input type="text" id="sol-tercero-txt" placeholder="Nombre del beneficiario..." style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;"></div>';
      h+='<div id="sol-nuevo-prov-box" style="display:none;margin-top:10px;background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:12px;">';
      h+='<div style="font-weight:700;font-size:12px;color:#0369a1;margin-bottom:8px;">&#x2795; Nuevo Proveedor</div>';
      h+='<div class="g2" style="gap:6px;margin-bottom:6px;">';
      h+='<input type="text" id="snp-nombre" placeholder="Nombre / Razon social *" style="padding:6px 8px;border:1px solid #bae6fd;border-radius:6px;font-size:12px;width:100%;">';
      h+='<input type="text" id="snp-nit" placeholder="NIT / CC" style="padding:6px 8px;border:1px solid #bae6fd;border-radius:6px;font-size:12px;width:100%;"></div>';
      h+='<div class="g2" style="gap:6px;margin-bottom:6px;">';
      h+='<input type="text" id="snp-banco" placeholder="Banco" style="padding:6px 8px;border:1px solid #bae6fd;border-radius:6px;font-size:12px;width:100%;">';
      h+='<select id="snp-tipo" style="padding:6px 8px;border:1px solid #bae6fd;border-radius:6px;font-size:12px;width:100%;"><option value="Ahorros">Ahorros</option><option value="Corriente">Corriente</option></select></div>';
      h+='<input type="text" id="snp-cuenta" placeholder="Numero de cuenta" style="padding:6px 8px;border:1px solid #bae6fd;border-radius:6px;font-size:12px;width:100%;margin-bottom:6px;">';
      h+='<button class="btn bp" onclick="_guardarNuevoProv()" style="width:100%;font-size:12px;">&#x1F4BE; Guardar y seleccionar</button>';
      h+='</div>';
      h+='</div>';
      h+='<div class="g2" style="margin-bottom:10px;">';
      h+='<div class="fg"><label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:4px;">Valor estimado ($)</label>';
      h+='<input type="number" id="sol-valor" placeholder="0" min="0" step="1000" style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;"></div>';
      h+='<div class="fg"><label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:4px;">Fecha entrega est.</label>';
      h+='<input type="date" id="sol-fent" style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;"></div></div>';
      h+='<div class="fg" style="margin-bottom:0;"><label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:4px;">Motivo / Comentario</label>';
      h+='<textarea id="sol-motivo" placeholder="Razon de aprobacion o rechazo..." rows="2" style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;resize:vertical;"></textarea></div>';
      h+='<input type="hidden" id="sol-det-num" value="'+esc(s.numero||num)+'">';
      h+='<input type="hidden" id="sol-det-cat" value="'+esc(s.categoria||'MP')+'">';
      h+='</div>';
    }
    h+='</div>';
    body.innerHTML=h;
    var fbtns='<button class="btn bo" onclick="_solDetClose()">Cerrar</button>';
    if(s.estado==='Pendiente'){
      fbtns+='<button class="btn" style="background:#dc2626;color:#fff;font-weight:700;" onclick="_solDetRech()">&#10005; Rechazar</button>';
      if(s.categoria==='Influencer/Marketing Digital'){
        fbtns+='<button class="btn bg" onclick="_solDetApr()" style="background:#7c3aed;">&#x1F4B8; Pagar directamente</button>';
      } else {
        fbtns+='<button class="btn bg" onclick="_solDetApr()">&#9654; Enviar a Autorización</button>';
      }
    }
    footer.innerHTML=fbtns;
  }catch(e){ body.innerHTML='<p style="color:#dc2626;">Error: '+e.message+'</p>'; }
}
async function gestionarSol(decision){
  var num=document.getElementById('sol-det-num').value;
  var _provSel=(document.getElementById('sol-prov-sel')||{value:''}).value;
  if(_provSel==='__nuevo__'){ alert('Primero guarda el nuevo proveedor antes de continuar.'); return; }
  var prov=_provSel==='__tercero__'
    ? ((document.getElementById('sol-tercero-txt')||{value:''}).value.trim()||'Pago a Terceros')
    : _provSel;
  var valor=parseFloat((document.getElementById('sol-valor')||{value:0}).value||0);
  var motivo=(document.getElementById('sol-motivo')||{value:''}).value.trim();
  var fent=(document.getElementById('sol-fent')||{value:''}).value;
  if(decision==='Rechazada'&&!motivo){
    if(!confirm('Rechazar sin motivo. Confirmar?')) return;
  }
  var body={estado:decision,observaciones:motivo};
  if(decision==='Aprobada'){
    body.crear_oc=true;
    body.proveedor=prov||'Por definir';
    if(valor>0) body.valor_total=valor;
    if(fent) body.fecha_entrega_est=fent;
    var catEl=document.getElementById('sol-det-cat');
    if(catEl) body.categoria=catEl.value;
    body.observaciones_oc=motivo||('Generado desde '+num);
  }
  try{
    var r=await fetch('/api/solicitudes-compra/'+encodeURIComponent(num)+'/estado',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    closeModal('m-sol-det');
    await Promise.all([loadData(),loadSolicitudes(),loadInfluencers()]);
    alert(decision==='Aprobada'?'Solicitud aprobada. OC generada: '+(d.numero_oc||''):'Solicitud rechazada.');
  }catch(e){ alert('Error: '+e); }
}

// ─── Init ─────────────────────────────────────────────────────────────
loadData();
</script>
</body>
</html>"""
