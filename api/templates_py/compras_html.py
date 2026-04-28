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
.mh-ent{background:linear-gradient(135deg,#1c1917 0%,#292524 100%)!important;border-bottom:2px solid #57534e;}
.mh-ent h3{color:#f5f5f4!important;}
.mh-ent .mx{color:#d6d3d1!important;}
.cat-pills{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px;}
.pill{background:#44403c;border:1px solid #57534e;color:#d6d3d1;padding:4px 10px;border-radius:20px;cursor:pointer;font-size:11px;transition:all .15s;}
.pill:hover{background:#57534e;}
.pill-on{background:#ea580c!important;border-color:#ea580c!important;color:#fff!important;font-weight:700;}
.btn.br{background:#dc2626;color:#fff;border:1px solid #b91c1c;}
.btn.br:hover{background:#b91c1c;}
.ocs-cpill{padding:5px 13px;border-radius:20px;font-size:12px;font-weight:600;border:1.5px solid #d6d3d1;background:#fff;color:#57534e;cursor:pointer;transition:all .15s;white-space:nowrap;}
.ocs-cpill:hover{background:#f5f5f4;border-color:#a8a29e;}
.ocs-cpill.on{background:#ea580c;border-color:#ea580c;color:#fff;}
.ptbl{width:100%;border-collapse:collapse;font-size:13px;}
.ptbl th{background:#f5f5f4;color:#78716c;font-weight:600;padding:8px 10px;text-align:left;border-bottom:2px solid #e7e5e4;}
.ptbl td{padding:8px 10px;border-bottom:1px solid #f0edec;vertical-align:middle;}
.ptbl tr:hover td{background:#fafafa;}
.pgrp-card{background:#fff;border:1px solid #e7e5e4;border-radius:8px;margin-bottom:14px;overflow:hidden;}
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
  <button class="tn"     data-tab="pagos">&#x1F4B8; Pagos</button>
  <button class="tn"     data-tab="por-pagar">&#x1F4B0; Por Pagar</button>
  <button class="tn"     data-tab="alertas">&#x1F6A8; Alertas</button>
  <button class="tn"     data-tab="prov">&#x1F3ED; Proveedores</button>
  <button class="tn" data-tab="influencer" id="tn-influencer">&#x1F4B8; Influencers</button>
  <button class="tn" data-tab="solic" id="tn-solic">&#128203; Solicitudes</button>
  <button class="tn" data-tab="consol" id="tn-consol">&#x1F4E6; Consolidado</button>
</div>

<!-- PANES -->
<div id="pane-dash" class="pane on">
  <div id="kpi-area" class="kpis"></div>
  <div class="queue-row">
    <div class="qbox">
      <div class="qtit">&#x26A1; SOLs esperando aprobaci&#xF3;n</div>
      <div style="font-size:11px;color:#94a3b8;margin-bottom:8px;">Solicitudes de compra pendientes de revisi&#xF3;n gerencial</div>
      <div id="q-aut"></div>
    </div>
    <div class="qbox">
      <div class="qtit">&#x1F4B8; OCs autorizadas &middot; por pagar</div>
      <div style="font-size:11px;color:#94a3b8;margin-bottom:8px;">&#xD3;rdenes aprobadas sin pago ejecutado</div>
      <div id="q-pag"></div>
    </div>
  </div>
  <div id="dash-chart-wrap"></div>
</div>


<div id="pane-pagos" class="pane">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap;">
    <div style="font-weight:700;font-size:15px;color:#1c1917;">&#x1F4B8; Registro de Pagos</div>
    <input type="text" id="q-pagos" placeholder="Buscar proveedor, OC, medio..." oninput="renderPagos()"
      style="flex:1;min-width:180px;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">
    <select id="s-pagos-cat" onchange="renderPagos()" style="padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">
      <option value="">Todas las categorias</option>
      <option value="mp">Mat. Primas</option><option value="mee">Empaque</option>
      <option value="svc">Servicios</option><option value="adm">Adm</option>
      <option value="inf">Infra</option><option value="cc">CC</option>
    </select>
  </div>
  <div id="pagos-kpis" style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;"></div>
  <div id="pagos-wrap">
    <div class="empty">Cargando pagos...</div>
  </div>
</div>

<div id="pane-influencer" class="pane">
  <div id="kpi-influencer" style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;"></div>
  <div class="bar" style="flex-wrap:wrap;gap:8px;">
    <input type="text" id="q-influencer" placeholder="Buscar influencer, solicitante..." oninput="renderInfluencers()">
    <select id="s-influencer" onchange="renderInfluencers()" title="Filtrar por estado">
      <option value="Aprobada">Por pagar</option>
      <option value="">Todos los estados</option>
      <option value="Pagada">Pagadas</option>
      <option value="Rechazada">Rechazadas</option>
    </select>
    <select id="order-influencer" onchange="renderInfluencers()" title="Ordenar por" style="background:#faf5ff;border:1px solid #c4b5fd;color:#5b21b6;font-weight:600;">
      <option value="estado_fecha">📌 Por pagar primero (default)</option>
      <option value="urgente">⏰ Más urgente arriba (fecha pago)</option>
      <option value="valor_desc">💰 Mayor valor primero</option>
      <option value="valor_asc">💵 Menor valor primero</option>
      <option value="reciente">🆕 Más reciente arriba</option>
      <option value="antiguo">📜 Más antiguo arriba</option>
    </select>
  </div>
  <div id="pills-influencer-help" style="font-size:11px;color:#64748b;padding:0 4px 8px;"></div>
  <div id="pills-influencer" class="pills"></div>
  <div id="grid-influencer"></div>
  <div id="grid-influencer-pagadas"></div>
</div>
<!-- Modal rechazo influencer -->
<div id="m-rechazar-inf" class="ov">
  <div class="mdl" style="max-width:440px;">
    <div class="mh" style="background:#fef2f2;border-bottom:1px solid #fecaca;">
      <div style="display:flex;align-items:center;gap:10px;">
        <span style="font-size:22px;line-height:1;">&#x274C;</span>
        <div>
          <div style="font-size:15px;font-weight:700;color:#991b1b;">Rechazar solicitud</div>
          <div id="m-rechazar-inf-sub" style="font-size:12px;color:#b91c1c;margin-top:1px;"></div>
        </div>
      </div>
      <button class="mx" onclick="closeModal('m-rechazar-inf')">&#x2715;</button>
    </div>
    <div class="mb">
      <div class="fg">
        <label>Motivo del rechazo <span style="color:#dc2626;">*</span> <span style="font-weight:400;color:#78716c;">(visible para el solicitante)</span></label>
        <textarea id="motivo-rechazo-inf" rows="4" placeholder="Ej: Falta información de cuenta, monto incorrecto, valor no coincide..."></textarea>
      </div>
      <div style="background:#fef9c3;border:1px solid #fde047;border-radius:6px;padding:10px 12px;font-size:12px;color:#854d0e;">
        ⚠️ El solicitante recibirá un correo con este motivo. Sé específico para evitar reenvíos innecesarios.
      </div>
    </div>
    <div class="mf">
      <button class="btn" onclick="closeModal('m-rechazar-inf')" style="background:#f5f5f4;color:#44403c;border:1px solid #d6d3d1;">Cancelar</button>
      <button class="btn" id="btn-confirmar-rechazo" style="background:#dc2626;color:#fff;">&#x274C; Confirmar Rechazo</button>
    </div>
  </div>
</div>

<!-- Modal rechazo influencer -->
<div id="m-rechazar-inf" class="ov">
  <div class="mdl" style="max-width:440px;">
    <div class="mh" style="background:#fef2f2;border-bottom:1px solid #fecaca;">
      <div style="display:flex;align-items:center;gap:10px;">
        <span style="font-size:22px;line-height:1;">&#x274C;</span>
        <div>
          <div style="font-size:15px;font-weight:700;color:#991b1b;">Rechazar solicitud</div>
          <div id="m-rechazar-inf-sub" style="font-size:12px;color:#b91c1c;margin-top:1px;"></div>
        </div>
      </div>
      <button class="mx" onclick="closeModal('m-rechazar-inf')">&#x2715;</button>
    </div>
    <div class="mb">
      <div class="fg">
        <label>Motivo del rechazo <span style="color:#dc2626;">*</span> <span style="font-weight:400;color:#78716c;">(visible para el solicitante)</span></label>
        <textarea id="motivo-rechazo-inf" rows="4" placeholder="Ej: Falta información de cuenta, monto incorrecto, valor no coincide..."></textarea>
      </div>
      <div style="background:#fef9c3;border:1px solid #fde047;border-radius:6px;padding:10px 12px;font-size:12px;color:#854d0e;">
        ⚠️ El solicitante recibirá un correo con este motivo. Sé específico para evitar reenvíos innecesarios.
      </div>
    </div>
    <div class="mf">
      <button class="btn" onclick="closeModal('m-rechazar-inf')" style="background:#f5f5f4;color:#44403c;border:1px solid #d6d3d1;">Cancelar</button>
      <button class="btn" id="btn-confirmar-rechazo" style="background:#dc2626;color:#fff;">&#x274C; Confirmar Rechazo</button>
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
  <!-- Alertas MP restock -->
  <div id="mp-alert-banner" style="display:none;background:#fef3c7;border:1px solid #f59e0b;border-radius:8px;padding:10px 14px;margin-bottom:10px;">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <span style="font-size:18px;">&#x26A0;&#xFE0F;</span>
      <div id="mp-alert-text" style="flex:1;font-size:13px;font-weight:600;color:#92400e;"></div>
      <button class="btn" style="background:#f59e0b;color:#fff;font-size:12px;padding:4px 12px;white-space:nowrap;" onclick="openOCSugerida()">&#x1F4CB; Crear OC Sugerida</button>
    </div>
    <div id="mp-alert-list" style="margin-top:6px;display:flex;flex-wrap:wrap;gap:6px;"></div>
  </div>
  <!-- Alertas Programacion -->
  <div id="prog-alert-banner" style="display:none;background:#fde8e8;border:1px solid #dc3545;border-radius:8px;padding:10px 14px;margin-bottom:10px;">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <span style="font-size:18px;">&#x1F4E1;</span>
      <div style="flex:1;">
        <div id="prog-alert-text" style="font-size:13px;font-weight:600;color:#7f1d1d;"></div>
        <div style="font-size:11px;color:#991b1b;margin-top:2px;">Centro de Programaci&#xF3;n &mdash; velocidad Shopify + f&#xF3;rmulas + stock MP</div>
      </div>
      <a href="/planta" style="background:#dc3545;color:#fff;font-size:12px;padding:5px 12px;border-radius:5px;text-decoration:none;white-space:nowrap;font-weight:600;">&#x1F4CA; Ver Programaci&#xF3;n</a>
      <button onclick="generarOCDesdeCompras(this)" style="background:#7f1d1d;color:#fff;border:none;border-radius:5px;font-size:12px;padding:5px 12px;cursor:pointer;font-weight:600;white-space:nowrap;">&#x1F6D2; Generar OC</button>
    </div>
  </div>
  <!-- Filtros de categoria -->
  <div id="solic-cat-bar" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;">
    <button class="ocs-cpill on" data-scat="ALL" onclick="setSolicCat(this)">&#x1F4CB; Todas</button>
    <button class="ocs-cpill" data-scat="mp" onclick="setSolicCat(this)">&#x1F9EA; Mat. Primas</button>
    <button class="ocs-cpill" data-scat="mee" onclick="setSolicCat(this)">&#x1F4E6; Empaque</button>
    <button class="ocs-cpill" data-scat="svc" onclick="setSolicCat(this)">&#x1F527; Servicios</button>
    <button class="ocs-cpill" data-scat="adm" onclick="setSolicCat(this)">&#x1F4CB; Adm</button>
    <button class="ocs-cpill" data-scat="inf" onclick="setSolicCat(this)">&#x1F3DB; Infra</button>
    <button class="ocs-cpill" data-scat="cc" onclick="setSolicCat(this)">&#x1F4B3; CC</button>
  </div>
  <div class="bar">
    <input type="text" id="q-solic" placeholder="Buscar SOL, OC, solicitante, proveedor..." oninput="renderSolicitudes()">
    <select id="s-solic" onchange="renderSolicitudes()">
      <option value="">Todos los estados</option>
      <option value="Pendiente">Pendiente</option>
      <option value="Aprobada">Aprobada</option>
      <option value="Pagada">Pagada</option>
      <option value="Rechazada">Rechazada</option>
    </select>
    <button class="btn bp" onclick="openNuevaOC('')">&#x1F4DD; Nueva OC</button>
    <button class="btn" onclick="descargarSolicitudesPDF()" style="background:#1F5F5B;color:#fff;" title="PDF ejecutivo">&#x1F4C4; PDF</button>
    <button class="btn" onclick="regenerarSolicitudesAuto()" style="background:#7c3aed;color:#fff;" title="Regenerar solicitudes auto">&#x1F504; Regenerar</button>
  </div>
  <div id="pills-solic" class="pills"></div>
  <div id="grid-solic" class="grid"></div>
</div>

<div id="pane-consol" class="pane">
  <div class="bar" style="flex-wrap:wrap;gap:8px;">
    <span style="font-weight:700;color:#1e293b;font-size:15px;">&#x1F4E6; Pedidos consolidados por proveedor</span>
    <div style="display:flex;gap:8px;margin-left:auto;align-items:center;">
      <label style="font-size:12px;color:#64748b;">Estados:</label>
      <label style="font-size:12px;"><input type="checkbox" class="consol-est" value="Borrador" checked> Borrador</label>
      <label style="font-size:12px;"><input type="checkbox" class="consol-est" value="Revisada" checked> Revisada</label>
      <label style="font-size:12px;"><input type="checkbox" class="consol-est" value="Autorizada" checked> Autorizada</label>
      <button class="btn bp" onclick="loadConsolidado()" style="padding:6px 14px;font-size:12px;">&#x21BA; Actualizar</button>
    </div>
  </div>
  <div id="consol-body" style="padding:16px 0;">
    <div style="color:#94a3b8;text-align:center;padding:40px;">Cargando consolidado...</div>
  </div>
</div>

<!-- ════════════ TAB: POR PAGAR ════════════ -->
<div id="pane-por-pagar" class="pane">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:8px;">
    <div>
      <h2 style="margin:0;font-size:18px;color:#1e293b;">&#x1F4B0; Pendiente de pago</h2>
      <div style="font-size:12px;color:#64748b;margin-top:2px;">
        Mercanc&iacute;a recibida + servicios sin recepci&oacute;n (Influencers, Cuentas de Cobro)
      </div>
    </div>
    <button class="btn bp" onclick="loadPorPagar()" style="padding:6px 14px;font-size:12px;">&#x21BA; Actualizar</button>
  </div>

  <div id="por-pagar-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:16px;">
    <div style="background:#1e1b4b;border:1px solid #4c1d95;border-radius:10px;padding:14px;">
      <div style="font-size:10px;color:#a78bfa;text-transform:uppercase;letter-spacing:0.05em;">Total pendiente</div>
      <div style="font-size:22px;font-weight:800;color:#fff;" id="por-pagar-total">-</div>
    </div>
    <div style="background:#0c1a4d;border:1px solid #1e3a8a;border-radius:10px;padding:14px;">
      <div style="font-size:10px;color:#93c5fd;text-transform:uppercase;letter-spacing:0.05em;">Mercanc&iacute;a recibida</div>
      <div style="font-size:18px;font-weight:800;color:#fff;" id="por-pagar-merc">-</div>
    </div>
    <div style="background:#3a2a00;border:1px solid #92400e;border-radius:10px;padding:14px;">
      <div style="font-size:10px;color:#fbbf24;text-transform:uppercase;letter-spacing:0.05em;">Pago directo (servicios)</div>
      <div style="font-size:18px;font-weight:800;color:#fff;" id="por-pagar-svc">-</div>
    </div>
  </div>

  <!-- Sección destacada: pagos directos (Influencers) -->
  <div id="por-pagar-directos-wrap" style="display:none;margin-bottom:20px;">
    <div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:10px;padding:14px 16px;margin-bottom:10px;">
      <div style="font-weight:700;color:#92400e;font-size:14px;">&#x1F4B8; Pagos directos (Influencers, Cuentas de Cobro)</div>
      <div style="font-size:11px;color:#78350f;margin-top:4px;">Estas OCs no requieren recepci&oacute;n f&iacute;sica — son servicios listos para pagar.</div>
    </div>
    <div id="por-pagar-directos" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;"></div>
  </div>

  <!-- Mercancía recibida -->
  <div style="margin-bottom:14px;">
    <div style="font-weight:700;color:#1e293b;font-size:14px;margin-bottom:10px;">&#x1F4E6; Mercanc&iacute;a recibida pendiente de pago</div>
    <div id="por-pagar-merc-list" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;">
      <div style="color:#94a3b8;text-align:center;padding:20px;">Cargando...</div>
    </div>
  </div>
</div>

<!-- ════════════ TAB: ALERTAS ════════════ -->
<div id="pane-alertas" class="pane">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:8px;">
    <div>
      <h2 style="margin:0;font-size:18px;color:#1e293b;">&#x1F6A8; Alertas vivas de Compras</h2>
      <div style="font-size:12px;color:#64748b;margin-top:2px;">
        Lo que requiere atenci&oacute;n hoy. Revisa cada secci&oacute;n y ataca las cr&iacute;ticas primero.
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
      <span id="alertas-sev-pill" style="padding:4px 12px;border-radius:20px;font-size:12px;font-weight:700;background:#e2e8f0;color:#64748b;">cargando...</span>
      <button class="btn bp" onclick="loadAlertasCompras()" style="padding:6px 14px;font-size:12px;">&#x21BA; Actualizar</button>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;">
    <!-- Card 1: OCs sin recibir -->
    <div style="background:#fff;border:1px solid #fcd34d;border-radius:12px;padding:14px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div style="font-weight:700;font-size:13px;color:#92400e;">&#x23F3; OCs sin recibir &gt; 15 d&iacute;as</div>
        <span id="alertas-sin-recibir-count" style="background:#f59e0b;color:#fff;border-radius:12px;padding:2px 10px;font-size:11px;font-weight:700;">0</span>
      </div>
      <div id="alertas-sin-recibir" style="font-size:12px;color:#1e293b;max-height:280px;overflow-y:auto;">Cargando...</div>
    </div>

    <!-- Card 2: Pagos por vencer -->
    <div style="background:#fff;border:1px solid #fca5a5;border-radius:12px;padding:14px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div style="font-weight:700;font-size:13px;color:#7f1d1d;">&#x1F4B5; Pagos por vencer</div>
        <span id="alertas-pagos-vencer-count" style="background:#dc2626;color:#fff;border-radius:12px;padding:2px 10px;font-size:11px;font-weight:700;">0</span>
      </div>
      <div id="alertas-pagos-vencer" style="font-size:12px;color:#1e293b;max-height:280px;overflow-y:auto;">Cargando...</div>
    </div>

    <!-- Card 3: Solicitudes Pendientes -->
    <div style="background:#fff;border:1px solid #93c5fd;border-radius:12px;padding:14px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div style="font-weight:700;font-size:13px;color:#1e3a8a;">&#x1F4DD; Solicitudes pendientes &gt; 3 d&iacute;as</div>
        <span id="alertas-solic-count" style="background:#3b82f6;color:#fff;border-radius:12px;padding:2px 10px;font-size:11px;font-weight:700;">0</span>
      </div>
      <div id="alertas-solic" style="font-size:12px;color:#1e293b;max-height:280px;overflow-y:auto;">Cargando...</div>
    </div>

    <!-- Card 4: Borradores estancados -->
    <div style="background:#fff;border:1px solid #d4d4d8;border-radius:12px;padding:14px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div style="font-weight:700;font-size:13px;color:#52525b;">&#x1F4D1; OCs Borrador &gt; 7 d&iacute;as</div>
        <span id="alertas-borrador-count" style="background:#71717a;color:#fff;border-radius:12px;padding:2px 10px;font-size:11px;font-weight:700;">0</span>
      </div>
      <div id="alertas-borrador" style="font-size:12px;color:#1e293b;max-height:280px;overflow-y:auto;">Cargando...</div>
    </div>
  </div>
</div>
<!-- MODAL: Proveedor 360 -->
<div id="m-ficha360" class="ov">
<div class="mdl mdl-lg" style="max-width:780px;max-height:88vh;overflow-y:auto;">
  <div class="mh"><h3>&#x1F4CA; Proveedor 360</h3><button class="mx" onclick="closeModal('m-ficha360')">&times;</button></div>
  <div class="mb" id="ficha360-content" style="padding:0 4px;">
    <div style="text-align:center;color:#a8a29e;padding:40px;">Cargando ficha...</div>
  </div>
  <div class="mf" id="ficha360-footer" style="gap:8px;justify-content:flex-end;"></div>
</div>
</div>

<!-- MODAL: Nueva OC -->
<div id="m-noc" class="ov">
<div class="mdl mdl-lg">
  <div class="mh mh-ent">
    <div>
      <h3 id="noc-title">&#x1F4DD; Nueva Orden de Compra</h3>
      <div id="noc-cat-pills" class="cat-pills"></div>
    </div>
    <button class="mx" onclick="closeModal('m-noc')">&times;</button>
  </div>
  <div class="mb">
    <input type="hidden" id="noc-cat" value="MP">
    <div class="g2">
      <div class="fg">
        <label id="noc-prov-lbl">Proveedor</label>
        <select id="noc-prov" onchange="fillProv('noc-prov','noc-ibox')"><option value="">-- Seleccionar --</option></select>
        <input type="text" id="noc-prov-txt" list="prov-dl" placeholder="Nombre del proveedor o beneficiario" style="display:none">
        <datalist id="prov-dl"></datalist>
        <div id="noc-add-prov-link" style="display:none;margin-top:4px;">
          <button type="button" class="btn bo" style="font-size:11px;padding:3px 10px;" onclick="showNewProvForm()">&#x2795; Crear proveedor nuevo</button>
        </div>
        <div id="noc-ibox" class="ibox" style="display:none"></div>
        <div id="noc-new-prov-form" style="display:none;background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:12px;margin-top:8px;">
          <div style="font-weight:700;font-size:12px;color:#166534;margin-bottom:8px;">&#x2795; Nuevo Proveedor</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
            <div><label style="font-size:11px;font-weight:600;">Nombre *</label><input id="np-nombre" placeholder="Razon social o nombre" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:600;">NIT / Cedula</label><input id="np-nit" placeholder="NIT" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:600;">Telefono</label><input id="np-tel" placeholder="Telefono" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:600;">Email</label><input id="np-email" placeholder="Email" style="width:100%"></div>
          </div>
          <div style="margin-bottom:8px;"><label style="font-size:11px;font-weight:600;">Concepto de compra</label><input id="np-concepto" placeholder="Ej: Materias primas cosmeticas" style="width:100%"></div>
          <div style="display:flex;gap:8px;">
            <button class="btn bg" style="font-size:12px;" onclick="guardarNuevoProv()">Guardar proveedor</button>
            <button class="btn bo" style="font-size:12px;" onclick="cancelarNuevoProv()">Cancelar</button>
          </div>
        </div>
        <div id="noc-cc-pago" style="display:none;background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:12px;margin-top:8px;">
          <div style="font-weight:700;font-size:12px;color:#92400e;margin-bottom:8px;">&#x1F4B3; Datos bancarios del beneficiario</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
            <div><label style="font-size:11px;font-weight:600;">Banco *</label><input id="noc-cc-banco" placeholder="Bancolombia, Davivienda..." style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:600;">Tipo de cuenta</label><select id="noc-cc-tipo" style="width:100%;padding:6px 8px;border:1px solid #d6d3d1;border-radius:6px;font-size:12px;"><option value="Ahorros">Ahorros</option><option value="Corriente">Corriente</option><option value="Ahorros Damas">Ahorros Damas</option><option value="Nequi / Daviplata">Nequi / Daviplata</option></select></div>
            <div><label style="font-size:11px;font-weight:600;">N\u00BA de cuenta / Cel</label><input id="noc-cc-cuenta" placeholder="Numero de cuenta" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:600;">NIT / CC</label><input id="noc-cc-nit" placeholder="Documento de identidad" style="width:100%"></div>
          </div>
        </div>
      </div>
      <div class="fg"><label>Fecha entrega est.</label><input type="date" id="noc-fent"></div>
    </div>
    <div class="fg"><label>Concepto / Observaciones</label><textarea id="noc-obs" placeholder="Descripcion del pedido..."></textarea></div>
    <div>
      <label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:6px;">Items del pedido</label>
      <table class="itbl"><thead><tr><th>Codigo</th><th>Descripcion</th><th>Cantidad</th><th>Precio U.</th><th>Subtotal</th><th></th></tr></thead>
      <tbody id="noc-tbody"></tbody></table>
      <button class="btn bo bs" style="margin-top:8px;" onclick="addRow()">+ Item</button>
    </div>
    <div style="display:flex;align-items:center;gap:10px;margin:10px 0 4px;">
      <input type="checkbox" id="noc-iva-chk" onchange="calcTot()" style="width:16px;height:16px;cursor:pointer;">
      <label for="noc-iva-chk" style="cursor:pointer;font-weight:600;font-size:13px;">Aplica IVA (19%)</label>
    </div>
    <div id="noc-iva-row" style="display:none;background:#fefce8;border:1px solid #fde047;border-radius:6px;padding:8px 12px;font-size:12px;margin-bottom:4px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:2px;"><span>Subtotal sin IVA</span><span id="noc-sub">$0</span></div>
      <div style="display:flex;justify-content:space-between;margin-bottom:2px;color:#92400e;"><span>IVA 19%</span><span id="noc-iva-monto">$0</span></div>
      <div style="display:flex;justify-content:space-between;font-weight:700;border-top:1px solid #fde047;padding-top:4px;"><span>Total con IVA</span><span id="noc-iva-total">$0</span></div>
    </div>
    <div class="total-row">Total: <span id="noc-tot">$0</span></div>
  </div>
  <div class="mf">
    <button class="btn bo" onclick="closeModal('m-noc')">Cancelar</button>
    <button class="btn bp" id="noc-submit-btn" onclick="submitOC()">Crear OC</button>
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
    <div class="fg">
      <label>&#x1F4C4; N&uacute;mero factura proveedor (3-way matching)</label>
      <input type="text" id="pago-factura" placeholder="Ej: FAC-12345" style="text-transform:uppercase;">
      <div style="font-size:11px;color:#64748b;margin-top:3px;">Si esta factura ya fue usada en otro pago, el sistema te avisa antes de continuar.</div>
    </div>
    <!-- Toggles fiscales (retefuente/retica/IVA) — para legalidad -->
    <div class="fg" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 12px;">
      <label style="display:block;font-weight:700;color:#1e293b;margin-bottom:6px;">&#x1F4CA; Retenciones e IVA (opcional)</label>
      <div style="display:flex;gap:14px;flex-wrap:wrap;font-size:12px;">
        <label style="display:flex;align-items:center;gap:6px;cursor:pointer;">
          <input type="checkbox" id="pago-aplicar-retefuente"> Aplicar ReteFuente 10%
        </label>
        <label style="display:flex;align-items:center;gap:6px;cursor:pointer;">
          <input type="checkbox" id="pago-aplicar-retica"> Aplicar ReteICA 0.66 x mil (Cali)
        </label>
        <label style="display:flex;align-items:center;gap:6px;cursor:pointer;">
          <input type="checkbox" id="pago-aplicar-iva"> Aplicar IVA 19%
        </label>
      </div>
      <div style="font-size:11px;color:#64748b;margin-top:6px;">
        Por defecto NO se aplican (pago bruto al proveedor). Activa solo cuando corresponda fiscalmente.
      </div>
    </div>
    <div class="fg"><label>Comprobante / Referencia</label><textarea id="pago-obs" rows="2" placeholder="No. transaccion, referencia..."></textarea></div>
    <div class="fg"><label>&#x1F5BC; Captura de transferencia (opcional)</label>
      <input type="file" id="pago-img-file" accept="image/*" onchange="previewPagoImg()" style="display:block;margin-bottom:6px;font-size:12px;">
      <img id="pago-img-preview" src="" alt="" style="display:none;max-width:100%;max-height:160px;border-radius:6px;border:1px solid #e7e5e4;">
    </div>
    <!-- Historial de pagos previos (pagos parciales) -->
    <div id="pago-historial" style="display:none;margin-top:10px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:10px;">
      <div style="font-size:12px;font-weight:700;color:#1e293b;margin-bottom:6px;">&#x1F4DC; Pagos previos de esta OC</div>
      <div id="pago-historial-list" style="font-size:11px;color:#64748b;"></div>
    </div>
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

<!-- MODAL: Cambiar proveedor de UNA MP del catalogo -->
<div id="m-edit-prov-mp" class="ov" style="z-index:10000;">
<div class="mdl" style="max-width:480px;width:96vw;">
  <div style="background:#1F5F5B;color:#fff;padding:14px 18px;border-radius:14px 14px 0 0;display:flex;justify-content:space-between;align-items:center;">
    <h3 style="color:#fff;margin:0;font-size:16px;">&#9999;&#65039; Cambiar proveedor de la MP</h3>
    <button onclick="closeModal('m-edit-prov-mp')" style="background:none;border:none;color:#fff;font-size:22px;cursor:pointer;">&times;</button>
  </div>
  <div class="mb" style="padding:18px;">
    <div style="background:#f0fdfa;border:1px solid #99f6e4;border-radius:8px;padding:10px 14px;margin-bottom:12px;">
      <div style="font-size:11px;color:#0f766e;font-weight:700;text-transform:uppercase;letter-spacing:.5px;">MP</div>
      <div id="epm-info" style="font-weight:700;color:#0f172a;font-size:14px;">&mdash;</div>
      <div id="epm-prov-actual" style="color:#64748b;font-size:12px;margin-top:2px;">&mdash;</div>
    </div>
    <p style="font-size:12px;color:#64748b;margin-bottom:6px;">Solo afecta la MP seleccionada en el cat&aacute;logo (maestro_mps). Las dem&aacute;s MPs de la solicitud no se tocan. Audit log captura el cambio.</p>
    <div style="margin-bottom:10px;">
      <label style="font-size:12px;color:#374151;font-weight:600;display:block;margin-bottom:4px;">Proveedor *</label>
      <input type="text" id="epm-input" list="prov-dl" placeholder="Selecciona o escribe nuevo" autocomplete="off" style="width:100%;padding:8px 12px;border:1px solid #d6d3d1;border-radius:8px;font-size:13px;">
      <small id="epm-hint" style="color:#94a3b8;font-size:11px;display:block;margin-top:4px;">Usa el desplegable para evitar duplicados por typo.</small>
    </div>
    <div style="display:flex;gap:8px;">
      <button onclick="guardarProvItemMP()" style="flex:1;background:#0f766e;color:#fff;border:none;border-radius:8px;padding:9px;font-weight:700;cursor:pointer;">&#10003; Guardar</button>
      <button onclick="closeModal('m-edit-prov-mp')" style="flex:1;background:#e7e5e4;color:#374151;border:none;border-radius:8px;padding:9px;cursor:pointer;">Cancelar</button>
    </div>
    <div id="epm-msg" style="margin-top:10px;font-size:12px;"></div>
  </div>
</div>
</div>

<!-- MODAL: Detalle Solicitud (Catalina) -->
<div id="m-sol-det" class="ov">
<div class="mdl" style="max-width:1200px;width:96vw;max-height:94vh;overflow-y:auto;position:relative;">
  <div class="mh" style="display:none;"><h3>&#128203; Solicitud de Compra</h3><button class="mx" onclick="closeModal('m-sol-det')">&times;</button></div>
  <button onclick="closeModal('m-sol-det')" style="position:absolute;top:14px;right:16px;background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.3);color:#fff;width:34px;height:34px;border-radius:50%;cursor:pointer;font-size:20px;font-weight:700;z-index:10;display:flex;align-items:center;justify-content:center;">&times;</button>
  <div class="mb" id="sol-det-body" style="padding:0;"><div style="text-align:center;padding:60px 40px;color:#78716c;">Cargando...</div></div>
  <div class="mf" id="sol-det-footer" style="padding:14px 26px;background:#fafaf9;border-top:1px solid #e7e5e4;">
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
<div class="mdl mdl-lg" style="max-width:980px;">
  <div class="mh"><h3>&#x26A0;&#xFE0F; OC Sugerida &#x2014; MPs Bajo Stock</h3><button class="mx" onclick="closeModal('m-oc-sug')">&times;</button></div>
  <div class="mb">
    <div style="font-size:12px;color:#78716c;margin-bottom:12px;">Cantidades incluyen 20% buffer sobre deficit. Ajusta, selecciona proveedor y crea cada OC individualmente &#x2014; o usa <strong>Crear Todas</strong> para agrupar por proveedor automaticamente.</div>
    <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-size:12px;">
      <thead><tr style="background:#fef3c7;font-weight:600;color:#78350f;">
        <th style="padding:6px 8px;text-align:left;">Material</th>
        <th style="padding:6px 4px;text-align:right;width:72px;">Stock</th>
        <th style="padding:6px 4px;text-align:right;width:68px;">Deficit</th>
        <th style="padding:6px 4px;text-align:center;width:95px;">Cant. (g)</th>
        <th style="padding:6px 4px;text-align:center;width:78px;">$/g</th>
        <th style="padding:6px 4px;text-align:left;width:200px;">Proveedor</th>
        <th style="padding:6px 4px;text-align:right;width:82px;">Subtotal</th>
        <th style="padding:6px 4px;text-align:center;width:84px;">Accion</th>
      </tr></thead>
      <tbody id="sug-tbody"></tbody>
    </table>
    </div>
    <div style="display:flex;justify-content:flex-end;margin-top:10px;font-size:15px;font-weight:700;color:#1c1917;">
      Total: <span id="sug-tot" style="margin-left:6px;">$0</span>
    </div>
  </div>
  <div class="mf">
    <button class="btn bo" onclick="closeModal('m-oc-sug')">Cancelar</button>
    <button class="btn bp" onclick="crearOCSugerida()">&#x1F4E6; Crear Todas (por proveedor)</button>
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
var _ocsCatFilter = 'ALL';
var PAGOS = [];

// Mapa categoria → grupos de strings
var CMAP = {
  mp:  ['MPs','MP','Materia Prima','Materias Primas'],
  mee: ['Envase','Insumos','MEE','Empaque','Material de Empaque'],
  svc: ['Servicios','Analisis','Acondicionamiento','SVC','Servicio',
        'Servicios Profesionales','Software/Tecnologia'],
  adm: ['Admin','Nomina','ADM','Administrativo',
        'EPP','Aseo/Limpieza','Papeleria/Oficina','Dotacion','Otro'],
  inf: ['Infraestructura','INF','Mantenimiento','Repuestos','Reactivos/Laboratorio'],
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
    else if(tab==='consol') loadConsolidado();
    else if(tab==='pagos'){ loadPagos(); }
    else if(tab==='por-pagar'){ loadPorPagar(); }
    else if(tab==='alertas'){ loadAlertasCompras(); }
    var fab = document.getElementById('fab-btn');
    if(tab==='prov'||tab==='solic'||tab==='influencer'||tab==='consol'||tab==='pagos'||tab==='por-pagar'||tab==='alertas'){ fab.style.display='none'; }
    else{ fab.style.display='flex'; fab.onclick=function(){
      var cat=tab==='dash'?'':tab.toUpperCase();
      openNuevaOC(cat);
    }; }
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
    // Usar Centro de Programación (con velocidad Shopify + producciones
    // futuras) en vez de stock_actual<stock_minimo simple, que está
    // basado en una columna que no se actualiza y daba data engañosa.
    var r4 = await fetch('/api/programacion/mps-deficit');
    if(!r4.ok) throw new Error('Programacion deficit API '+r4.status);
    var d4 = await r4.json();
    _ALERTAS_MP = (d4.mps||[]).map(function(m){
      return {
        codigo_mp: m.codigo_mp,
        nombre: m.nombre,
        stock_actual: m.stock_actual_g === -1 ? Infinity : m.stock_actual_g,
        stock_minimo: 0, // ya no aplica el concepto de mínimo, es déficit real
        deficit: m.deficit_g,
        proveedor: m.proveedor || '',
        productos: m.productos_afectados || [],
        tipo: 'MP',
        es_china: m.es_china || false,
      };
    });
  }catch(e){ console.error('MPs deficit load error:',e); _ALERTAS_MP=[]; }
  renderDash();
  renderMPAlerts();
  // Load Programacion alerts (non-blocking)
  cargarAlertasProgramacion();
}

async function cargarAlertasProgramacion(){
  try{
    var r = await fetch('/api/programacion/n-alertas');
    var d = await r.json();
    var banner = document.getElementById('prog-alert-banner');
    var text = document.getElementById('prog-alert-text');
    if(!banner || !text) return;
    if(d.n > 0){
      banner.style.display = 'block';
      var label = d.criticos > 0
        ? d.criticos + ' alerta(s) CR\u00EDTICA(S) — ' + d.n + ' total'
        : d.n + ' alerta(s) de programaci\u00F3n activas';
      text.textContent = '\u26A0\uFE0F ' + label + ' — MPs faltantes o stock insuficiente a 60 d\u00EDas';
    } else {
      banner.style.display = 'none';
    }
  }catch(e){ /* silencioso si programacion no est\u00E1 disponible */ }
}

async function generarOCDesdeCompras(btnEl){
  if(!confirm('Crear solicitud de compra autom\u00E1tica para todos los MPs con d\u00E9ficit de producci\u00F3n?')) return;
  if(btnEl){ btnEl.disabled = true; btnEl.textContent = 'Generando...'; }
  try{
    var r = await fetch('/api/programacion/generar-oc', {
      method: 'POST', headers: {'Content-Type': 'application/json'}
    });
    var d = await r.json();
    if(d.ok){
      alert('\u2705 ' + d.mensaje);
      // Refresh dashboard
      renderDash();
    } else {
      alert('Error: ' + (d.error || 'desconocido'));
    }
  }catch(e){
    alert('Error de red: ' + e.message);
  }finally{
    if(btnEl){ btnEl.disabled = false; btnEl.textContent = '🛒 Generar OC'; }
  }
}

// ─── Dashboard ────────────────────────────────────────────────────
async function renderDash(){
  // Ensure SOLIC loaded (covers both regular + CC categories)
  if(!SOLIC||!SOLIC.length){
    try{
      var _r1=await fetch('/api/solicitudes-compra');
      var _d1=await _r1.json();
      var _r2=await fetch('/api/solicitudes-compra?categoria=Cuenta+de+Cobro');
      var _d2=await _r2.json();
      var _all=(_d1.solicitudes||[]).concat(_d2.solicitudes||[]);
      var _seen={};
      SOLIC=_all.filter(function(s){ if(_seen[s.numero]) return false; _seen[s.numero]=1; return true; });
    }catch(e){ SOLIC=[]; }
  }

  // KPI data
  var mes=new Date().toISOString().substring(0,7);
  var solicPend=SOLIC.filter(function(s){ return s.estado==='Pendiente'; });
  var ocsPorPagar=OCS.filter(function(o){ return o.estado==='Autorizada'; });
  var pagMes=OCS.filter(function(o){ return o.estado==='Pagada'&&(o.fecha_pago||o.fecha||'').startsWith(mes); });
  var vPorPagar=ocsPorPagar.reduce(function(s,o){ return s+parseFloat(o.valor_total||0); },0);
  var vMes=pagMes.reduce(function(s,o){ return s+parseFloat(o.valor_total||0); },0);
  var nDeficit=(_ALERTAS_MP||[]).filter(function(a){ return a.estado==='deficit'; }).length;

  // KPIs
  document.getElementById('kpi-area').innerHTML=
    mkKpi('SOLs pendientes',solicPend.length+' solicitudes','Esperando aprobación',solicPend.length>0?'w':'')+
    mkKpi('OCs por pagar',ocsPorPagar.length+' autorizadas',fmt(vPorPagar),ocsPorPagar.length>0?'w':'')+
    mkKpi('Pagado este mes',pagMes.length+' OCs',fmt(vMes),'g')+
    mkKpi('MPs en déficit',nDeficit+' materiales','Stock bajo punto reorden',nDeficit>0?'w':'');

  // Left queue: SOLs pending approval
  var urgColor={'Alta':'#dc2626','Media':'#f59e0b','Normal':'#64748b'};
  var stBg={'Pendiente':'#fef3c7','Aprobada':'#d1fae5','Rechazada':'#fee2e2','Pagada':'#e0f2fe'};
  var stFg={'Pendiente':'#92400e','Aprobada':'#065f46','Rechazada':'#991b1b','Pagada':'#075985'};
  document.getElementById('q-aut').innerHTML=solicPend.length
    ? solicPend.slice(0,8).map(function(s){
        var urg=s.urgencia||'Normal';
        var urgC=urgColor[urg]||'#78716c';
        return '<div class="card" style="margin-bottom:8px;">'
          +'<div class="ch"><div><div class="cnum" style="font-family:monospace;">'+esc(s.numero)+'</div>'
          +'<div class="cprov">'+esc(s.solicitante||'-')+' &mdash; '+esc(s.categoria||'-')+'</div></div>'
          +'<span class="badge" style="background:#fef3c7;color:#92400e;">Pendiente</span></div>'
          +'<div class="cmeta"><span>'+fdate(s.fecha)+'</span>'
          +(s.observaciones?'<span style="font-size:11px;color:#57534e;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px;">'+esc((s.observaciones||'').substring(0,50))+'</span>':'')
          +'<span style="color:'+urgC+';font-weight:700;">'+esc(urg)+'</span></div>'
          +'<div class="acts"><button class="btn bi bs" onclick="revisarSolicitudPendiente(&quot;'+esc(s.numero)+'&quot;)">Revisar</button></div>'
          +'</div>';
      }).join('')
    : '<div class="empty" style="padding:20px;text-align:center;color:#a8a29e;">Sin solicitudes pendientes ✓</div>';

  // Right queue: OCs autorizadas (ready to pay)
  document.getElementById('q-pag').innerHTML=ocsPorPagar.length
    ? ocsPorPagar.slice(0,8).map(function(o){ return miniCard(o); }).join('')
    : '<div class="empty" style="padding:20px;text-align:center;color:#a8a29e;">Sin OCs autorizadas ✓</div>';

  // Spending chart by category
  var _catLabels=['MP','MEE','SVC','ADM','INF','CC'];
  var _catColors=['#f59e0b','#3b82f6','#8b5cf6','#10b981','#ef4444','#ec4899'];
  var _catTotals=_catLabels.map(function(g){ return OCS.filter(function(o){ return inGroup(o.categoria,g.toLowerCase())&&o.estado==='Pagada'; }).reduce(function(s,o){ return s+parseFloat(o.valor_total||0); },0); });
  var _maxV=Math.max.apply(null,_catTotals)||1;
  var _chartHTML='<div style="background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:14px 16px;margin-top:14px;">';
  _chartHTML+='<div style="font-weight:700;font-size:13px;color:#1c1917;margin-bottom:12px;">&#x1F4CA; Gasto acumulado por categoría (OCs Pagadas)</div>';
  _chartHTML+='<div style="display:grid;gap:7px;">';
  _catLabels.forEach(function(g,i){
    var pct=_catTotals[i]/_maxV*100;
    _chartHTML+='<div style="display:grid;grid-template-columns:48px 1fr 80px;align-items:center;gap:8px;">';
    _chartHTML+='<span style="font-size:11px;font-weight:600;color:#57534e;">'+g+'</span>';
    _chartHTML+='<div style="background:#f5f5f4;border-radius:4px;height:18px;overflow:hidden;"><div style="background:'+_catColors[i]+';width:'+pct.toFixed(1)+'%;height:100%;border-radius:4px;transition:width .4s;"></div></div>';
    _chartHTML+='<span style="font-size:11px;color:#57534e;text-align:right;">'+fmt(_catTotals[i])+'</span>';
    _chartHTML+='</div>';
  });
  _chartHTML+='</div></div>';
  var _chartWrap=document.getElementById('dash-chart-wrap');
  if(!_chartWrap){ _chartWrap=document.createElement('div'); _chartWrap.id='dash-chart-wrap'; document.getElementById('kpi-area').after(_chartWrap); }
  _chartWrap.innerHTML=_chartHTML;
}
function mkKpi(l,v,s,c){
  return '<div class="kpi"><div class="kpi-l">'+l+'</div><div class="kpi-v'+(c?' '+c:'')+'" >'+v+'</div><div class="kpi-s">'+s+'</div></div>';
}
// Click "Revisar" en la mini-card del Centro de Mando — abre el tab Solicitudes
// y hace scroll suave a la solicitud específica. Antes esto vivía como onclick
// inline con triple-escape de comillas que rompía el parser de JS al render
// (SyntaxError "Invalid left-hand side in assignment") y dejaba TODO el
// <script> de compras inerte — todos los botones quedaban sin handlers.
function revisarSolicitudPendiente(numero){
  var tabBtn = document.querySelector('[data-tab=solic]');
  if (tabBtn) tabBtn.click();
  setTimeout(function(){
    var el = document.querySelector('[data-num="'+(numero||'')+'"]');
    if (el) el.scrollIntoView({behavior:'smooth', block:'center'});
  }, 400);
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
  var _effGrp=grp==='ocs'?(Object.keys(CMAP).find(function(k){return inGroup(o.categoria,k);})||'svc'):grp;
  if(o.estado==='Pagada'&&!ES_C&&(_effGrp==='mp'||_effGrp==='mee')) btns+='<button class="btn bo bs" data-act="rec" data-oc="'+esc(o.numero_oc)+'">Marcar Recibida</button>';
  if(o.estado==='Borrador') btns+='<button class="btn bi bs" data-act="edit" data-oc="'+esc(o.numero_oc)+'">&#9998; Editar</button>';
  if(o.estado==='Borrador'||o.estado==='Rechazada') btns+='<button class="btn br bs" data-act="del" data-oc="'+esc(o.numero_oc)+'">&#128465; Eliminar</button>';
  return '<div class="card">'+
    '<div class="ch"><div><div class="cnum">'+esc(o.numero_oc)+'</div><div class="cprov">'+esc(o.proveedor||'-')+'</div></div>'+badge(o.estado)+'</div>'+
    '<div class="cmeta"><span>&#x1F4C5; '+fdate(o.fecha)+'</span>'+(o.fecha_entrega_est?'<span>&#x23F0; '+fdate(o.fecha_entrega_est)+'</span>':'')+'<span>'+o.num_items+' item(s)</span></div>'+
    (o.observaciones?'<div class="cobs">'+esc((o.observaciones||'').substring(0,90))+'</div>':'')+
    '<div class="cval">'+fmt(o.valor_total)+(o.con_iva?'<span style="font-size:10px;background:#fde047;color:#92400e;border-radius:3px;padding:1px 5px;margin-left:5px;">+IVA</span>':'')+'</div>'+
    (btns?'<div class="acts">'+btns+'</div>':'')+'</div>';
}

// ─── OCS unified tab ─────────────────────────────────────────────────────────
function renderOCS(){
  // Wire up category filter pill clicks (idempotent)
  document.querySelectorAll('.ocs-cpill').forEach(function(btn){
    btn.onclick=function(){
      document.querySelectorAll('.ocs-cpill').forEach(function(b){ b.classList.remove('on'); });
      this.classList.add('on');
      _ocsCatFilter=this.getAttribute('data-cat');
      renderOCS();
    };
  });
  var q=(document.getElementById('q-ocs')||{value:''}).value.toLowerCase();
  var st=(document.getElementById('s-ocs')||{value:''}).value;
  // Show/hide context sections
  var mpBanner=document.getElementById('mp-alert-banner');
  var ccSolic=document.getElementById('cc-solic-wrap');
  if(mpBanner) mpBanner.style.display=(_ocsCatFilter==='ALL'||_ocsCatFilter==='mp')?'':'none';
  if(ccSolic){
    if(_ocsCatFilter==='ALL'||_ocsCatFilter==='cc'){
      ccSolic.style.display='';
      loadCCSolicitudes();
    } else {
      ccSolic.style.display='none';
    }
  }
  if(_ocsCatFilter==='mp'||_ocsCatFilter==='ALL') renderMPAlerts();
  var list;
  if(_ocsCatFilter==='ALL'){
    list=OCS.filter(function(o){ return (o.categoria||'').indexOf('Influencer')<0; });
  } else {
    list=OCS.filter(function(o){ return inGroup(o.categoria,_ocsCatFilter); });
  }
  if(q) list=list.filter(function(o){ return (o.numero_oc||'').toLowerCase().indexOf(q)>=0||(o.proveedor||'').toLowerCase().indexOf(q)>=0||(o.observaciones||'').toLowerCase().indexOf(q)<0?false:true; });
  if(q) list=OCS.filter(function(o){
    if(_ocsCatFilter!=='ALL'&&!inGroup(o.categoria,_ocsCatFilter)) return false;
    if((o.categoria||'').indexOf('Influencer')>=0) return false;
    var sq=(o.numero_oc||'').toLowerCase().indexOf(q)>=0||(o.proveedor||'').toLowerCase().indexOf(q)>=0||(o.observaciones||'').toLowerCase().indexOf(q)>=0;
    return sq;
  });
  if(st) list=list.filter(function(o){ return o.estado===st; });
  var counts={};
  ['Borrador','Revisada','Autorizada','Pagada','Recibida'].forEach(function(e){ counts[e]=(list.filter(function(o){ return o.estado===e; })).length; });
  var vTotal=list.reduce(function(s,o){ return s+parseFloat(o.valor_total||0); },0);
  var pills='<span class="pill">'+list.length+' OCs</span>';
  if(counts.Borrador) pills+='<span class="pill">Borrador: '+counts.Borrador+'</span>';
  if(counts.Revisada) pills+='<span class="pill y">Revisada: '+counts.Revisada+'</span>';
  if(counts.Autorizada) pills+='<span class="pill b">Autorizada: '+counts.Autorizada+'</span>';
  if(counts.Pagada) pills+='<span class="pill g">Pagada: '+counts.Pagada+'</span>';
  if(counts.Recibida) pills+='<span class="pill">Recibida: '+counts.Recibida+'</span>';
  pills+='<span class="pill" style="background:#e7e5e4;">'+fmt(vTotal)+'</span>';
  document.getElementById('pills-ocs').innerHTML=pills;
  if(!list.length){
    document.getElementById('grid-ocs').innerHTML='<div class="empty">No hay OCs'+(q?' para esa busqueda':_ocsCatFilter!=='ALL'?' en esta categor\u00EDa':'')+'</div>';
    return;
  }
  document.getElementById('grid-ocs').innerHTML=list.map(function(o){ return fullCard(o,'ocs'); }).join('');
}

// ─── Pagos tab ────────────────────────────────────────────────────────────────
async function loadPagos(){
  document.getElementById('pagos-wrap').innerHTML='<div class="empty">Cargando...</div>';
  try{
    var r=await fetch('/api/compras/pagos');
    if(!r.ok) throw new Error('Pagos '+r.status);
    var d=await r.json();
    PAGOS=d.pagos||[];
  }catch(e){ PAGOS=[]; console.error('loadPagos:',e); }
  renderPagos();
}
function renderPagos(){
  var q=(document.getElementById('q-pagos')||{value:''}).value.toLowerCase();
  var catF=(document.getElementById('s-pagos-cat')||{value:''}).value;
  var list=PAGOS.filter(function(p){
    if(catF&&!inGroup(p.categoria,catF)) return false;
    if(q&&(p.numero_oc||'').toLowerCase().indexOf(q)<0&&(p.proveedor||'').toLowerCase().indexOf(q)<0&&(p.medio_pago||'').toLowerCase().indexOf(q)<0) return false;
    return true;
  });
  var vTotal=list.reduce(function(s,p){ return s+parseFloat(p.monto||p.valor_total||0); },0);
  var kpiHTML='<div class="kpi"><div class="kpi-l">Pagos filtrados</div><div class="kpi-v">'+list.length+'</div></div>';
  kpiHTML+='<div class="kpi"><div class="kpi-l">Monto total</div><div class="kpi-v g">'+fmt(vTotal)+'</div></div>';
  document.getElementById('pagos-kpis').innerHTML=kpiHTML;
  if(!list.length){
    document.getElementById('pagos-wrap').innerHTML='<div class="empty">No hay pagos registrados</div>';
    return;
  }
  var rows=list.map(function(p){
    var tieneImg=p.tiene_comprobante;
    var imgBtn=tieneImg?'<button class="btn bo bs" data-oc="'+esc(p.numero_oc)+'" onclick="verComprobante(this.dataset.oc)">&#x1F4F8; Ver</button>':'<span style="color:#a8a29e;font-size:11px;">Sin imagen</span>';
    return '<tr>'
      +'<td><strong>'+esc(p.numero_oc)+'</strong></td>'
      +'<td>'+esc(p.proveedor||'-')+'</td>'
      +'<td><span style="font-size:10px;background:#e7e5e4;border-radius:3px;padding:2px 6px;">'+esc(p.categoria||'-')+'</span></td>'
      +'<td style="font-weight:600;color:#16a34a;">'+fmt(p.monto||p.valor_total)+'</td>'
      +'<td>'+esc(p.medio_pago||'-')+'</td>'
      +'<td>'+fdate(p.fecha_pago)+'</td>'
      +'<td>'+esc(p.pagado_por||'-')+'</td>'
      +'<td>'+imgBtn+'</td>'
      +'</tr>';
  }).join('');
  document.getElementById('pagos-wrap').innerHTML='<div style="overflow-x:auto;"><table class="ptbl"><thead><tr><th>OC</th><th>Proveedor</th><th>Categoría</th><th>Monto</th><th>Medio</th><th>Fecha</th><th>Por</th><th>Comprobante</th></tr></thead><tbody>'+rows+'</tbody></table></div>';
}
async function verComprobante(num){
  try{
    var r=await fetch('/api/ordenes-compra/'+encodeURIComponent(num)+'/comprobante');
    if(!r.ok){ alert('Sin comprobante guardado'); return; }
    var d=await r.json();
    if(!d.imagen){ alert('Sin comprobante guardado'); return; }
    var w=window.open('','_blank','width=700,height=600');
    w.document.write('<html><body style="margin:0;background:#111;display:flex;align-items:center;justify-content:center;min-height:100vh;"><img src="'+d.imagen+'" style="max-width:100%;max-height:100vh;"></body></html>');
    w.document.close();
  }catch(e){ alert('Error: '+e); }
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
    // Footer buttons
    var ft=document.getElementById('ficha360-footer');
    if(ft){
      ft.innerHTML=
        '<button class="btn bo" onclick="closeModal(\\'m-ficha360\\')">Cerrar</button>'
        +'<button class="btn bw" style="background:#2563eb;" onclick="editarProv360(\\''+ nombre.replace(/'/g,\"&#39;\")+'\\')">'
        +'&#x270F; Editar</button>'
        +'<button class="btn" style="background:#dc2626;color:#fff;font-weight:700;" '
        +'onclick="bajaProv360(\\''+ nombre.replace(/'/g,\"&#39;\")+'\\')">'
        +'&#x1F6AB; Dar de baja</button>';
    }
  } catch(e) { el.innerHTML = '<p style="color:#dc2626;">Error: '+e.message+'</p>'; }
}

// ─── Editar proveedor 360 ──────────────────────────────────────────
function editarProv360(nombre){
  var el=document.getElementById('ficha360-content');
  var ft=document.getElementById('ficha360-footer');
  // Pre-fill from PROVS cache
  var p=PROVS.find(function(x){ return x.nombre===nombre; })||{};
  function fld(id,lbl,val,ph){
    return '<div class="fg" style="margin-bottom:8px;">'
      +'<label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:3px;">'+lbl+'</label>'
      +'<input id="ep-'+id+'" value="'+esc(val||'')+'" placeholder="'+ph+'" '
      +'style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;"></div>';
  }
  var h='<div style="padding:16px 20px;">';
  h+='<div style="font-weight:800;font-size:14px;margin-bottom:14px;">&#x270F; Editar: '+esc(nombre)+'</div>';
  h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:0 14px;">';
  h+=fld('contacto','Contacto',p.contacto,'Nombre contacto');
  h+=fld('email','Email',p.email,'correo@ejemplo.com');
  h+=fld('telefono','Teléfono',p.telefono,'300 000 0000');
  h+=fld('nit','NIT / CC',p.nit,'NIT o cédula');
  h+='<div style="grid-column:span 2;">'+fld('direccion','Dirección',p.direccion,'Dirección completa')+'</div>';
  h+=fld('banco','Banco',p.banco,'Bancolombia, Davivienda...');
  h+='<div class="fg" style="margin-bottom:8px;"><label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:3px;">Tipo de cuenta</label>'
    +'<select id="ep-tipo_cuenta" style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">'
    +'<option value="Ahorros"'+(p.tipo_cuenta==='Ahorros'?' selected':'')+ '>Ahorros</option>'
    +'<option value="Corriente"'+(p.tipo_cuenta==='Corriente'?' selected':'')+'>Corriente</option>'
    +'<option value="Ahorros Damas"'+(p.tipo_cuenta==='Ahorros Damas'?' selected':'')+'>Ahorros Damas</option>'
    +'<option value="Nequi / Daviplata"'+(p.tipo_cuenta==='Nequi / Daviplata'?' selected':'')+'>Nequi / Daviplata</option>'
    +'</select></div>';
  h+=fld('num_cuenta','N° de cuenta',p.num_cuenta,'Número de cuenta');
  h+=fld('concepto_compra','Concepto de compra',p.concepto_compra,'Ej: Materias primas');
  h+='<div class="fg" style="margin-bottom:8px;"><label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:3px;">Categoría LPA</label>'
    +'<select id="ep-categoria" style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">'
    +'<option value="">-- Sin categoría --</option>'
    +'<option value="\U0001F534 Crítico"'+(( p.categoria||'').indexOf('rico')>=0?' selected':'')+'>🔴 Crítico</option>'
    +'<option value="\U0001F7E0 Mayor"'+((p.categoria||'').indexOf('ayor')>=0?' selected':'')+'>🟠 Mayor</option>'
    +'<option value="\U0001F7E2 No crítico"'+((p.categoria||'').indexOf('No')>=0?' selected':'')+'>🟢 No crítico</option>'
    +'</select></div>';
  h+='</div></div>';
  el.innerHTML=h;
  if(ft) ft.innerHTML=
    '<button class="btn bo" onclick="abrirFicha360(\\''+ nombre.replace(/'/g,\"&#39;\")+'\\')">'
    +'&#x2190; Volver</button>'
    +'<button class="btn bg" onclick="guardarEditProv360(\\''+ nombre.replace(/'/g,\"&#39;\")+'\\')">'
    +'&#x1F4BE; Guardar cambios</button>';
}
async function guardarEditProv360(nombre){
  var body={};
  var ids=['contacto','email','telefono','nit','direccion','banco','tipo_cuenta','num_cuenta','concepto_compra','categoria'];
  ids.forEach(function(id){ var el=document.getElementById('ep-'+id); if(el) body[id]=el.value.trim(); });
  try{
    var r=await fetch('/api/proveedores-compras/'+encodeURIComponent(nombre),
      {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    // Refresh PROVS and reload 360
    var rp=await fetch('/api/proveedores-compras'); var dp=await rp.json();
    PROVS=dp.proveedores||[];
    abrirFicha360(nombre);
  }catch(e){ alert('Error: '+e.message); }
}
function bajaProv360(nombre){
  var el=document.getElementById('ficha360-content');
  var ft=document.getElementById('ficha360-footer');
  var h='<div style="padding:24px 20px;">';
  h+='<div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:10px;padding:20px;">';
  h+='<div style="font-size:28px;text-align:center;margin-bottom:8px;">&#x1F6AB;</div>';
  h+='<div style="font-weight:800;font-size:15px;color:#dc2626;text-align:center;margin-bottom:4px;">Dar de baja al proveedor</div>';
  h+='<div style="font-size:13px;color:#7f1d1d;text-align:center;margin-bottom:16px;">'
    +'<strong>'+esc(nombre)+'</strong> dejará de aparecer en nuevas OCs.'
    +'<br>El historial de compras se conserva intacto.</div>';
  h+='<div class="fg"><label style="font-size:12px;font-weight:700;color:#7f1d1d;display:block;margin-bottom:6px;">'
    +'Motivo de baja <span style="color:#dc2626;">*</span></label>';
  h+='<textarea id="baja-motivo" rows="3" placeholder="Ej: Incumplimiento reiterado de fechas, pérdida de confianza, mejor alternativa disponible..." '
    +'style="width:100%;padding:8px 10px;border:1px solid #fca5a5;border-radius:6px;font-size:13px;resize:vertical;"></textarea></div>';
  h+='</div></div>';
  el.innerHTML=h;
  if(ft) ft.innerHTML=
    '<button class="btn bo" onclick="abrirFicha360(\\''+ nombre.replace(/'/g,\"&#39;\")+'\\')">'
    +'&#x2190; Cancelar</button>'
    +'<button class="btn" style="background:#dc2626;color:#fff;font-weight:700;" '
    +'onclick="confirmarBajaProv360(\\''+ nombre.replace(/'/g,\"&#39;\")+'\\')">'
    +'&#x26A0; Confirmar baja definitiva</button>';
}
async function confirmarBajaProv360(nombre){
  var motivo=(document.getElementById('baja-motivo')||{value:''}).value.trim();
  if(!motivo){ alert('El motivo de baja es obligatorio'); return; }
  try{
    var r=await fetch('/api/proveedores-compras/'+encodeURIComponent(nombre),
      {method:'DELETE',headers:{'Content-Type':'application/json'},
       body:JSON.stringify({motivo:motivo})});
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    // Refresh PROVS and close modal
    var rp=await fetch('/api/proveedores-compras'); var dp=await rp.json();
    PROVS=dp.proveedores||[];
    fillProvSelect('noc-prov');
    closeModal('m-ficha360');
    renderProveedores();
    alert('Proveedor dado de baja. Historial conservado.');
  }catch(e){ alert('Error: '+e.message); }
}

// ─── Proveedor autofill ────────────────────────────────────────────
function fillProvSelect(selId){
  var sel=document.getElementById(selId); if(!sel) return;
  var cur=sel.value;
  sel.innerHTML='<option value="">-- Seleccionar proveedor --</option>';
  PROVS.forEach(function(p){ var o=document.createElement('option'); o.value=p.nombre; o.textContent=p.nombre; sel.appendChild(o); });
  // Append inline-create option (only for noc-prov)
  if(selId==='noc-prov'){
    var no=document.createElement('option');
    no.value='__NEW__'; no.textContent='+ Crear proveedor nuevo';
    no.style.fontWeight='700'; no.style.color='#16a34a';
    sel.appendChild(no);
  }
  if(cur&&cur!=='__NEW__') sel.value=cur;
}
function fillProv(selId, boxId){
  var nombre=document.getElementById(selId).value;
  var box=document.getElementById(boxId);
  // Intercept inline-create selection
  if(nombre==='__NEW__'){
    box.style.display='none';
    var frm=document.getElementById('noc-new-prov-form');
    if(frm){
      frm.style.display='block';
      ['np-nombre','np-nit','np-tel','np-email','np-concepto'].forEach(function(id){
        var el=document.getElementById(id); if(el) el.value='';
      });
    }
    return;
  }
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

// ─── Nueva OC (enterprise) ───────────────────────────────────────────
var _catMap={'mp':'MP','mee':'MEE','svc':'SVC','adm':'ADM','inf':'INF','cc':'CC'};
var _ocMode='create';
var _ocEditNum='';
var _ocCatCode='MP';
var _MP_LIST=[];
var _OC_CATS=[
  {k:'MP',ico:'🧪',l:'Mat. Primas'},
  {k:'MEE',ico:'📦',l:'Empaque'},
  {k:'SVC',ico:'🔧',l:'Servicios'},
  {k:'ADM',ico:'📋',l:'Administrativo'},
  {k:'INF',ico:'🏗️',l:'Infraestructura'},
  {k:'CC',ico:'💳',l:'Cta. Cobro'},
];
function initCatPills(activeCat){
  var html='';
  _OC_CATS.forEach(function(c){
    var on=c.k===activeCat?' pill-on':'';
    html+='<button class="pill'+on+'" data-cat="'+c.k+'">'+c.ico+' '+c.l+'</button>';
  });
  document.getElementById('noc-cat-pills').innerHTML=html;
  document.getElementById('noc-cat-pills').querySelectorAll('.pill').forEach(function(p){
    p.addEventListener('click',function(){ setCat(this.getAttribute('data-cat')); });
  });
}
function setCat(k){
  _ocCatCode=k;
  document.getElementById('noc-cat').value=k;
  var pills=document.getElementById('noc-cat-pills').querySelectorAll('.pill');
  pills.forEach(function(p){
    p.classList.toggle('pill-on',p.getAttribute('data-cat')===k);
  });
  if(k==='MP') loadMPLookup();
  // ── Column header ──
  var colH={'MP':'Codigo MP','MEE':'Ref. MEE','SVC':'Servicio',
    'ADM':'Concepto','INF':'Ref.','CC':'Concepto'};
  var th=document.querySelector('#m-noc .itbl thead tr th');
  if(th) th.textContent=colH[k]||'Codigo';
  // ── Provider field: select for MP/MEE, free-text for the rest ──
  var isCatalog=(k==='MP'||k==='MEE');
  var sel=document.getElementById('noc-prov');
  var txt=document.getElementById('noc-prov-txt');
  var lbl=document.getElementById('noc-prov-lbl');
  var ibox=document.getElementById('noc-ibox');
  if(sel) sel.style.display=isCatalog?'':'none';
  if(txt) txt.style.display=isCatalog?'none':'';
  if(ibox) ibox.style.display='none';
  if(lbl) lbl.textContent=isCatalog?'Proveedor':(k==='CC'?'Beneficiario / Proveedor':'Proveedor / Beneficiario');
  var ccPago=document.getElementById('noc-cc-pago');
  if(ccPago) ccPago.style.display=(k==='CC'?'block':'none');
  var addProvLink=document.getElementById('noc-add-prov-link');
  if(addProvLink) addProvLink.style.display=isCatalog?'none':'block';
  if(!isCatalog&&txt){
    var dl=document.getElementById('prov-dl');
    if(dl&&typeof PROVS!=='undefined'){
      dl.innerHTML=PROVS.map(function(p){
        return '<option value="'+esc(p.nombre)+'">';
      }).join('');
    }
  }
  // ── Rebuild item rows ──
  document.getElementById('noc-tbody').innerHTML='';
  ITMS=0;
  addRow(); addRow();
}
function openNuevaOC(catCode){
  _ocMode='create'; _ocEditNum='';
  var key=(catCode||'').toLowerCase();
  _ocCatCode=_catMap[key]||catCode||'MP';
  document.getElementById('noc-cat').value=_ocCatCode;
  document.getElementById('noc-title').textContent='📝 Nueva Orden de Compra';
  document.getElementById('noc-submit-btn').textContent='Crear OC';
  document.getElementById('noc-fent').value='';
  document.getElementById('noc-obs').value='';
  var ic=document.getElementById('noc-iva-chk');
  if(ic) ic.checked=false;
  var ir=document.getElementById('noc-iva-row');
  if(ir) ir.style.display='none';
  document.getElementById('noc-tot').textContent='$0';
  document.getElementById('noc-tbody').innerHTML='';
  ITMS=0;
  fillProvSelect('noc-prov');
  document.getElementById('noc-prov').value='';
  initCatPills(_ocCatCode);
  setCat(_ocCatCode);
  openModal('m-noc');
}
function addRow(){
  ITMS++;
  var n=ITMS;
  var isMP=(document.getElementById('noc-cat').value==='MP');
  var _ph={'MP':'Buscar MP...','MEE':'Ref. MEE','SVC':'Servicio','ADM':'Concepto','INF':'Ref.','CC':'Concepto'};
  var _ph_val=_ph[document.getElementById('noc-cat').value]||'COD';
  var _w=isMP?'width:115px':'width:80px';
  var codCell=isMP
    ?'<td><input id="ic'+n+'" list="mp-dl" placeholder="Buscar MP..." style="'+_w+'" oninput="autoFillMP('+n+')" autocomplete="off"></td>'
    :'<td><input id="ic'+n+'" placeholder="'+_ph_val+'" style="'+_w+'"></td>';
  var tr=document.createElement('tr');
  tr.id='ir'+n;
  tr.innerHTML=codCell+
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
  var ivaChk=document.getElementById('noc-iva-chk');
  var ivaRow=document.getElementById('noc-iva-row');
  if(ivaChk&&ivaChk.checked){
    var iva=tot*0.19;
    var total=tot+iva;
    if(ivaRow) ivaRow.style.display='block';
    var es=document.getElementById('noc-sub'); if(es) es.textContent=fmt(tot);
    var em=document.getElementById('noc-iva-monto'); if(em) em.textContent=fmt(iva);
    var et=document.getElementById('noc-iva-total'); if(et) et.textContent=fmt(total);
    document.getElementById('noc-tot').textContent=fmt(total);
  } else {
    if(ivaRow) ivaRow.style.display='none';
    document.getElementById('noc-tot').textContent=fmt(tot);
  }
}
async function submitOC(){
  var cat=document.getElementById('noc-cat').value;
  var _isCat=(cat==='MP'||cat==='MEE');
  var prov=_isCat
    ?document.getElementById('noc-prov').value
    :((document.getElementById('noc-prov-txt')||{value:''}).value||'').trim();
  var obs=document.getElementById('noc-obs').value;
  var fent=document.getElementById('noc-fent').value;
  if(!prov){ alert('Selecciona un proveedor o beneficiario'); return; }
  // For CC: encode banking data into observaciones
  if(cat==='CC'){
    var _banco=(document.getElementById('noc-cc-banco')||{value:''}).value.trim();
    var _tipo=(document.getElementById('noc-cc-tipo')||{value:''}).value.trim();
    var _cuenta=(document.getElementById('noc-cc-cuenta')||{value:''}).value.trim();
    var _nit=(document.getElementById('noc-cc-nit')||{value:''}).value.trim();
    var _pagoStr='';
    if(_banco) _pagoStr+='BANCO: '+_banco+' '+_tipo;
    if(_cuenta) _pagoStr+=(_pagoStr?' | ':'')+'CUENTA/CEL: '+_cuenta;
    if(_nit) _pagoStr+=(_pagoStr?' | ':'')+'CED/NIT: '+_nit;
    if(_pagoStr) obs=(_pagoStr+(obs?' | '+obs:'')).trim();
  }
  var items=[];
  for(var i=1;i<=ITMS;i++){
    var n=document.getElementById('in'+i);
    if(!n||(n.value||'').trim()==='') continue;
    items.push({codigo_mp:(document.getElementById('ic'+i)||{value:''}).value,
      nombre_mp:n.value.trim(),
      cantidad_g:parseFloat((document.getElementById('iq'+i)||{value:1}).value||1),
      precio_unitario:parseFloat((document.getElementById('ip'+i)||{value:0}).value||0)});
  }
  if(!items.length){ alert('Agrega al menos un item con descripcion'); return; }
  var ivaChk=document.getElementById('noc-iva-chk');
  var conIva=ivaChk&&ivaChk.checked?1:0;
  var sub=items.reduce(function(a,it){return a+(it.cantidad_g||0)*(it.precio_unitario||0);},0);
  try{
    var url,method;
    if(_ocMode==='edit'){
      url='/api/ordenes-compra/'+encodeURIComponent(_ocEditNum)+'/editar';
      method='PATCH';
    } else {
      url='/api/ordenes-compra';
      method='POST';
    }
    var r=await fetch(url,{method:method,headers:{'Content-Type':'application/json'},
      body:JSON.stringify({proveedor:prov,categoria:cat,observaciones:obs,
        fecha_entrega_est:fent,items:items,creado_por:'{usuario}',
        con_iva:conIva,valor_sin_iva:sub})});
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    closeModal('m-noc');
    await loadData();
    renderDash();
    alert(_ocMode==='edit'?'OC actualizada: '+_ocEditNum:'Creada: '+d.numero_oc);
  }catch(e){ alert('Error de conexion: '+e); }
}
var crearOC=submitOC;
async function editarOC(oc){
  try{
    var r=await fetch('/api/ordenes-compra/'+encodeURIComponent(oc));
    var d=await r.json();
    if(d.error){ alert(d.error); return; }
    _ocMode='edit'; _ocEditNum=oc;
    _ocCatCode=d.categoria||'MP';
    document.getElementById('noc-cat').value=_ocCatCode;
    document.getElementById('noc-title').textContent='Editar OC '+oc;
    document.getElementById('noc-submit-btn').textContent='Guardar Cambios';
    document.getElementById('noc-fent').value=d.fecha_entrega_est||'';
    document.getElementById('noc-obs').value=d.observaciones||'';
    var ic=document.getElementById('noc-iva-chk');
    if(ic) ic.checked=!!d.con_iva;
    document.getElementById('noc-tbody').innerHTML='';
    ITMS=0;
    fillProvSelect('noc-prov');
    initCatPills(_ocCatCode);
    // Toggle provider field and set value
    var _isCat=(_ocCatCode==='MP'||_ocCatCode==='MEE');
    var _sel=document.getElementById('noc-prov');
    var _txt=document.getElementById('noc-prov-txt');
    var _lbl=document.getElementById('noc-prov-lbl');
    if(_sel) _sel.style.display=_isCat?'':'none';
    if(_txt) _txt.style.display=_isCat?'none':'';
    if(_lbl) _lbl.textContent=_isCat?'Proveedor':'Proveedor / Beneficiario';
    if(_isCat){
      setTimeout(function(){ document.getElementById('noc-prov').value=d.proveedor||''; },80);
    } else {
      if(_txt) _txt.value=d.proveedor||'';
    }
    if(_ocCatCode==='MP') loadMPLookup();
    (d.items||[]).forEach(function(it){
      addRow();
      var n=ITMS,el;
      el=document.getElementById('ic'+n); if(el) el.value=it.codigo_mp||'';
      el=document.getElementById('in'+n); if(el) el.value=it.nombre_mp||'';
      el=document.getElementById('iq'+n); if(el) el.value=it.cantidad_g||1;
      el=document.getElementById('ip'+n); if(el) el.value=it.precio_unitario||0;
    });
    if(!d.items||!d.items.length) addRow();
    calcTot();
    openModal('m-noc');
  }catch(e){ alert('Error cargando OC: '+e); }
}
async function eliminarOC(oc){
  if(!confirm('Eliminar OC '+oc+'? Esta accion no se puede deshacer.')) return;
  try{
    var r=await fetch('/api/ordenes-compra/'+encodeURIComponent(oc),{method:'DELETE'});
    var d=await r.json();
    if(d.error){ alert(d.error); return; }
    await loadData();
    var at=document.querySelector('.tn.on');
    if(at){
      var _tab=at.getAttribute('data-tab');
      if(_tab) try{renderCat(_tab);}catch(_){}
    }
    alert('OC '+oc+' eliminada');
  }catch(e){ alert('Error: '+e); }
}
async function loadMPLookup(){
  if(_MP_LIST.length) return;
  try{
    // /api/maestro-mps devuelve {mps:[{codigo_mp,nombre_comercial,...}]}.
    // Antes apuntaba a /api/materiales (404) con keys incorrectos
    // (codigo_interno/nombre_material) — el datalist quedaba vacío y
    // autoFillMP nunca acertaba ningún MP.
    var r=await fetch('/api/maestro-mps?tipo_material=MP');
    var d=await r.json();
    _MP_LIST=(d.mps||d.items||d||[]);
    var dl=document.getElementById('mp-dl');
    if(!dl){ dl=document.createElement('datalist'); dl.id='mp-dl'; document.body.appendChild(dl); }
    dl.innerHTML=_MP_LIST.map(function(m){
      var cod=m.codigo_mp||m.codigo_interno||'';
      var nom=m.nombre_comercial||m.nombre_material||m.nombre_inci||'';
      return '<option value="'+cod+'">'+nom+'</option>';
    }).join('');
  }catch(e){ console.warn('MP lookup unavailable',e); }
}
function autoFillMP(n){
  var codEl=document.getElementById('ic'+n);
  if(!codEl) return;
  var val=codEl.value.trim();
  var mp=_MP_LIST.find(function(m){ return (m.codigo_mp||m.codigo_interno)===val; });
  if(mp){
    var nameEl=document.getElementById('in'+n);
    if(nameEl&&!nameEl.value) nameEl.value=mp.nombre_comercial||mp.nombre_material||'';
  }
}
// ─── Inline provider creation ─────────────────────────────────────────
function showNewProvForm(){
  var frm=document.getElementById('noc-new-prov-form');
  if(!frm) return;
  frm.style.display='block';
  // Pre-fill nombre from free-text field if something was typed
  var txt=document.getElementById('noc-prov-txt');
  var nomEl=document.getElementById('np-nombre');
  if(nomEl&&txt&&txt.value.trim()&&!nomEl.value) nomEl.value=txt.value.trim();
  frm.scrollIntoView({behavior:'smooth',block:'nearest'});
}
function guardarNuevoProv(){
  var nombre=(document.getElementById('np-nombre').value||'').trim();
  if(!nombre){ alert('El nombre del proveedor es requerido'); return; }
  var btn=document.querySelector('#noc-new-prov-form .btn.bg');
  if(btn){ btn.disabled=true; btn.textContent='Guardando...'; }
  fetch('/api/proveedores-compras',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      nombre:nombre,
      nit:(document.getElementById('np-nit').value||'').trim(),
      telefono:(document.getElementById('np-tel').value||'').trim(),
      email:(document.getElementById('np-email').value||'').trim(),
      concepto_compra:(document.getElementById('np-concepto').value||'').trim()
    })
  }).then(function(r){ return r.json(); }).then(function(d){
    if(d.error){ alert('Error: '+d.error);
      if(btn){ btn.disabled=false; btn.textContent='Guardar proveedor'; } return; }
    reloadProvs(nombre);
  }).catch(function(e){
    alert('Error de conexion: '+e);
    if(btn){ btn.disabled=false; btn.textContent='Guardar proveedor'; }
  });
}
function cancelarNuevoProv(){
  var frm=document.getElementById('noc-new-prov-form');
  if(frm) frm.style.display='none';
  var sel=document.getElementById('noc-prov');
  if(sel) sel.value='';
  var box=document.getElementById('noc-ibox');
  if(box) box.style.display='none';
}
function reloadProvs(selectAfter){
  fetch('/api/proveedores-compras').then(function(r){ return r.json(); })
  .then(function(d){
    PROVS=d.proveedores||[];
    fillProvSelect('noc-prov');
    // Also refresh datalist for free-text categories
    var dl=document.getElementById('prov-dl');
    if(dl) dl.innerHTML=PROVS.map(function(p){
      return '<option value="'+esc(p.nombre)+'">';
    }).join('');
    var frm=document.getElementById('noc-new-prov-form');
    if(frm) frm.style.display='none';
    if(selectAfter){
      var isCat=(_ocCatCode==='MP'||_ocCatCode==='MEE');
      if(isCat){
        var sel=document.getElementById('noc-prov');
        if(sel) sel.value=selectAfter;
        fillProv('noc-prov','noc-ibox');
      } else {
        var txt=document.getElementById('noc-prov-txt');
        if(txt) txt.value=selectAfter;
      }
    }
  }).catch(function(e){ console.error('Error recargando proveedores',e); });
}


// ─── MP: Banner de alertas ──────────────────────────────────
// Fuente: Centro de Programación (velocidad Shopify + producciones futuras
// del calendario + stock real). Lista MPs con déficit operacional REAL,
// no items que tienen stock_actual<stock_minimo de un campo desactualizado.
function renderMPAlerts(){
  var banner=document.getElementById('mp-alert-banner');
  var text=document.getElementById('mp-alert-text');
  var list=document.getElementById('mp-alert-list');
  if(!banner) return;
  if(!_ALERTAS_MP||!_ALERTAS_MP.length){ banner.style.display='none'; return; }
  var total_def=_ALERTAS_MP.reduce(function(s,a){ return s+parseFloat(a.deficit||0); },0);
  var n_china = _ALERTAS_MP.filter(function(a){ return a.es_china; }).length;
  banner.style.display='block';
  var resumen = _ALERTAS_MP.length+' MPs en déficit real (Centro de Programación) — Faltante total: '+Math.round(total_def).toLocaleString('es-CO')+' g';
  if(n_china > 0) resumen += ' · ⚠ '+n_china+' de China (lead 60d)';
  text.textContent=resumen;
  list.innerHTML=_ALERTAS_MP.slice(0,8).map(function(a){
    var col = a.es_china ? '#b91c1c' : '#d97706';
    var deficit_g = Math.round(a.deficit||0);
    var deficit_str = deficit_g.toLocaleString('es-CO')+' g';
    var stock_str = a.stock_actual === Infinity ? '∞' :
                    Math.round(a.stock_actual||0).toLocaleString('es-CO')+' g';
    var prov_str = a.proveedor ? ' · '+a.proveedor : '';
    var china_mark = a.es_china ? '🇨🇳 ' : '';
    return '<span style="background:#fff;border:1px solid '+col+';color:'+col
      +';border-radius:4px;padding:2px 8px;font-size:11px;font-weight:600;" title="Stock: '+stock_str+prov_str+'">'
      +china_mark+esc(a.nombre.substring(0,28))+' (faltan '+deficit_str+')</span>';
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
    renderDash();
    alert('OC creada: '+d.numero_oc);
  }catch(e){ alert('Error de conexion: '+e); }
}

// ─── MP: OC Sugerida desde alertas ───────────────────────
function openOCSugerida(){
  if(!_ALERTAS_MP||!_ALERTAS_MP.length){ alert('No hay MPs bajo stock minimo'); return; }
  var tbody=document.getElementById('sug-tbody');
  tbody.innerHTML=_ALERTAS_MP.map(function(a,i){
    var mp=_MPCAT.find(function(m){ return m.codigo_mp===a.codigo_mp; });
    var pref=(mp&&mp.precio_referencia>0)?parseFloat(mp.precio_referencia).toFixed(4):'';
    var qty=Math.ceil(a.deficit*1.2/100)*100;
    var provOpts='<option value="">-- Proveedor --</option>';
    if(a.proveedor){ provOpts+='<option value="'+esc(a.proveedor)+'" selected>'+esc(a.proveedor)+'</option>'; }
    PROVS.forEach(function(p){
      if(p.nombre!==a.proveedor) provOpts+='<option value="'+esc(p.nombre)+'">'+esc(p.nombre)+'</option>';
    });
    return '<tr id="sugr'+i+'">'
      +'<td style="padding:5px 8px;">'
        +'<div style="font-weight:600;font-size:12px;">'+esc(a.nombre.substring(0,35))+'</div>'
        +'<div style="font-size:10px;color:#78716c;">'+esc(a.codigo_mp)+'</div>'
      +'</td>'
      +'<td style="padding:5px 4px;text-align:right;font-size:12px;">'+Math.round(a.stock_actual)+'g</td>'
      +'<td style="padding:5px 4px;text-align:right;font-size:12px;color:#dc2626;font-weight:600;">'+Math.round(a.deficit)+'g</td>'
      +'<td style="padding:5px 4px;">'
        +'<input id="sugq'+i+'" type="number" value="'+qty+'" min="0" oninput="calcTotSug()"'
        +' style="width:88px;padding:4px;border:1px solid #d6d3d1;border-radius:4px;font-size:12px;text-align:right;">'
      +'</td>'
      +'<td style="padding:5px 4px;">'
        +'<input id="sugp'+i+'" type="number" value="'+pref+'" min="0" step="0.001" placeholder="$/g" oninput="calcTotSug()"'
        +' style="width:72px;padding:4px;border:1px solid #d6d3d1;border-radius:4px;font-size:12px;text-align:right;">'
      +'</td>'
      +'<td style="padding:5px 4px;">'
        +'<select id="sugprov'+i+'" style="width:100%;padding:3px 4px;border:1px solid #d6d3d1;border-radius:4px;font-size:11px;">'+provOpts+'</select>'
      +'</td>'
      +'<td id="sugs'+i+'" style="padding:5px 4px;text-align:right;font-size:12px;white-space:nowrap;">$0</td>'
      +'<td style="padding:5px 4px;text-align:center;" id="sugact'+i+'">'
        +'<button onclick="crearOCFila('+i+')" style="padding:3px 8px;font-size:11px;background:#2563eb;color:#fff;border:none;border-radius:4px;cursor:pointer;white-space:nowrap;">Crear OC</button>'
      +'</td>'
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
  // Group items by their per-row selected provider; skip zero-qty rows
  var grupos={};
  for(var i=0;i<_ALERTAS_MP.length;i++){
    var a=_ALERTAS_MP[i];
    var q=parseFloat((document.getElementById('sugq'+i)||{value:0}).value||0);
    var p=parseFloat((document.getElementById('sugp'+i)||{value:0}).value||0);
    var prov=(document.getElementById('sugprov'+i)||{value:''}).value;
    if(q<=0) continue;
    if(!prov){ alert('Falta proveedor para: '+a.nombre); return; }
    if(!grupos[prov]) grupos[prov]=[];
    grupos[prov].push({codigo_mp:a.codigo_mp,nombre_mp:a.nombre,cantidad_g:q,precio_unitario:p});
  }
  var provList=Object.keys(grupos);
  if(!provList.length){ alert('Todas las cantidades son 0 — ajusta antes de crear'); return; }
  var creadas=[]; var errores=[];
  for(var pi=0;pi<provList.length;pi++){
    var prov=provList[pi]; var items=grupos[prov];
    try{
      var r=await fetch('/api/ordenes-compra',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({proveedor:prov,categoria:'MP',creado_por:'{usuario}',
          observaciones:'OC sugerida — MPs bajo stock ('+new Date().toLocaleDateString('es-CO')+')',
          items:items})});
      var res=null; try{res=await r.json();}catch(_){res=null;}
      if(r.ok&&res&&!res.error){ creadas.push(res.numero_oc||prov); }
      else{ errores.push(prov+': '+((res&&res.error)||'Error '+r.status)); }
    }catch(e){ errores.push(prov+': '+e.message); }
  }
  await loadData(); renderDash();
  if(errores.length){
    alert('Creadas: '+creadas.join(', ')+'\\nErrores:\\n'+errores.join('\\n'));
  } else {
    closeModal('m-oc-sug');
    alert('OCs creadas (agrupadas por proveedor): '+creadas.join(', '));
  }
}
async function crearOCFila(i){
  var a=_ALERTAS_MP[i];
  var q=parseFloat((document.getElementById('sugq'+i)||{value:0}).value||0);
  var p=parseFloat((document.getElementById('sugp'+i)||{value:0}).value||0);
  var prov=(document.getElementById('sugprov'+i)||{value:''}).value;
  if(q<=0){ alert('Ingresa una cantidad mayor a 0'); return; }
  if(!prov){ alert('Selecciona un proveedor para: '+a.nombre); return; }
  var actEl=document.getElementById('sugact'+i);
  if(actEl) actEl.innerHTML='<span style="font-size:11px;color:#78716c;">Enviando...</span>';
  try{
    var r=await fetch('/api/ordenes-compra',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({proveedor:prov,categoria:'MP',creado_por:'{usuario}',
        observaciones:'OC sugerida — '+a.nombre+' ('+new Date().toLocaleDateString('es-CO')+')',
        items:[{codigo_mp:a.codigo_mp,nombre_mp:a.nombre,cantidad_g:q,precio_unitario:p}]})});
    var res=null; try{res=await r.json();}catch(_){res=null;}
    if(r.ok&&res&&!res.error){
      if(actEl) actEl.innerHTML='<span style="color:#16a34a;font-size:13px;">&#x2713; '+esc(res.numero_oc||'OK')+'</span>';
      var row=document.getElementById('sugr'+i);
      if(row) row.style.background='#f0fdf4';
      await loadData(); renderDash();
    } else {
      var msg=(res&&res.error)?res.error:'Error '+r.status;
      if(actEl) actEl.innerHTML='<span style="color:#dc2626;font-size:11px;">'+esc(msg)+'</span>';
    }
  }catch(e){
    if(actEl) actEl.innerHTML='<span style="color:#dc2626;font-size:11px;">'+esc(e.message)+'</span>';
  }
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
function previewPagoImg(){
  var f=document.getElementById('pago-img-file').files[0];
  var prev=document.getElementById('pago-img-preview');
  if(f){ var rd=new FileReader(); rd.onload=function(e){ prev.src=e.target.result; prev.style.display='block'; }; rd.readAsDataURL(f); }
  else { prev.src=''; prev.style.display='none'; }
}
async function confirmarPago(){
  var num=document.getElementById('pago-num').value;
  var monto=document.getElementById('pago-monto').value;
  var medio=document.getElementById('pago-medio').value;
  var obs=document.getElementById('pago-obs').value;
  var factura=(document.getElementById('pago-factura').value||'').trim().toUpperCase();
  if(!monto||parseFloat(monto)<=0){ alert('Ingresa el monto'); return; }
  var imgData=null;
  var imgFile=document.getElementById('pago-img-file').files[0];
  if(imgFile){
    imgData=await new Promise(function(res){
      var rd=new FileReader(); rd.onload=function(e){ res(e.target.result); }; rd.readAsDataURL(imgFile);
    });
  }
  try{
    var payload={monto:parseFloat(monto),medio:medio,observaciones:obs};
    if(factura) payload.numero_factura_proveedor=factura;
    if(imgData) payload.comprobante_imagen=imgData;
    // Toggles fiscales — si están activos, el comprobante PDF se genera con retenciones/IVA
    var rf=document.getElementById('pago-aplicar-retefuente');
    var ri=document.getElementById('pago-aplicar-retica');
    var iv=document.getElementById('pago-aplicar-iva');
    if(rf && rf.checked) payload.aplicar_retefuente=true;
    if(ri && ri.checked) payload.aplicar_retica=true;
    if(iv && iv.checked) payload.aplicar_iva=true;
    var r=await fetch('/api/ordenes-compra/'+num+'/pagar',{method:'PATCH',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload)});
    var d=await r.json();
    if(r.status===409 && d.codigo==='FACTURA_DUPLICADA'){
      alert('⚠ Factura duplicada\\n\\n'+d.error+'\\n\\n'+d.detail);
      return;
    }
    if(r.status===403 && d.codigo==='EXCEDE_LIMITE_APROBACION'){
      alert('⚠ Excede tu límite\\n\\n'+d.error+'\\n\\n'+d.detail);
      return;
    }
    if(d.error){ alert('Error: '+d.error); return; }
    // Mensaje claro de pago parcial vs total + comprobante de egreso
    var msg = '';
    if(d.estado==='Parcial' && typeof d.pendiente==='number'){
      msg = 'Pago registrado. Estado: PARCIAL\\nPagado total: $'+(d.total_pagado_acumulado||0).toLocaleString('es-CO')+'\\nPendiente: $'+d.pendiente.toLocaleString('es-CO');
    } else if(d.estado==='Pagada'){
      msg = '✓ Pago completo registrado.';
    }
    // Si se generó comprobante, ofrecer descarga
    if(d.comprobante && d.comprobante.numero_ce){
      var ce = d.comprobante;
      msg += '\\n\\nComprobante: '+ce.numero_ce;
      msg += '\\nSubtotal: $'+(ce.subtotal||0).toLocaleString('es-CO');
      if(ce.iva > 0) msg += '\\nIVA: $'+ce.iva.toLocaleString('es-CO');
      if(ce.retefuente > 0) msg += '\\nReteFuente: -$'+ce.retefuente.toLocaleString('es-CO');
      if(ce.retica > 0) msg += '\\nReteICA: -$'+ce.retica.toLocaleString('es-CO');
      msg += '\\nTotal pagado: $'+(ce.total_pagado||0).toLocaleString('es-CO');
      if(confirm(msg + '\\n\\n¿Descargar el PDF del comprobante de egreso?')){
        window.open('/api/comprobantes-pago/'+ce.comprobante_id+'/pdf', '_blank');
      }
    } else if(msg){
      alert(msg);
    }
    closeModal('m-pago');
    // Reset image + toggles
    document.getElementById('pago-img-file').value='';
    document.getElementById('pago-img-preview').style.display='none';
    var rf=document.getElementById('pago-aplicar-retefuente'); if(rf) rf.checked=false;
    var ri=document.getElementById('pago-aplicar-retica'); if(ri) ri.checked=false;
    var iv=document.getElementById('pago-aplicar-iva'); if(iv) iv.checked=false;
    await loadData();
    renderDash();
    if(PAGOS.length) loadPagos();
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
  else if(act==='del-sol') eliminarSolicitud(btn.getAttribute('data-sol')||'');
  else if(act==='edit') editarOC(oc);
  else if(act==='del') eliminarOC(oc);
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

// ─── Editar proveedor de UNA MP del catálogo (per-item en solicitud) ─────────
// Event delegation para evitar problemas de escape de quotes en el HTML render.
// Se hookea una sola vez en DOMContentLoaded — captura clicks en cualquier
// boton .btn-edit-prov-mp de la tabla items.
var _epmActual = null;
document.addEventListener('click', function(e){
  var btn = e.target.closest && e.target.closest('.btn-edit-prov-mp');
  if (!btn) return;
  var td = btn.closest('.td-prov');
  if (!td) return;
  var cod = td.getAttribute('data-cod') || '';
  var nom = td.getAttribute('data-nom') || '';
  var prov = td.getAttribute('data-prov') || '';
  abrirEditarProvItem(cod, nom, prov);
});

function abrirEditarProvItem(cod, nom, provActual){
  if(!cod){alert('Codigo MP requerido'); return;}
  _epmActual = {cod: cod, nom: nom||'', provActual: provActual||''};
  document.getElementById('epm-info').textContent = (nom||'(sin nombre)') + ' · ' + cod;
  document.getElementById('epm-prov-actual').textContent = 'Proveedor actual: ' + (provActual || '(vacio)');
  document.getElementById('epm-input').value = provActual || '';
  document.getElementById('epm-msg').innerHTML = '';
  // Asegurar prov-dl populated (PROVS variable global)
  try {
    var dl = document.getElementById('prov-dl');
    if (dl && typeof PROVS !== 'undefined' && (!dl.children || dl.children.length === 0)) {
      dl.innerHTML = PROVS.map(function(p){
        return '<option value="'+esc(p.nombre)+'">';
      }).join('');
    }
  } catch(e) {}
  openModal('m-edit-prov-mp');
  setTimeout(function(){var el=document.getElementById('epm-input');if(el)el.focus();},120);
}

async function guardarProvItemMP(){
  if(!_epmActual)return;
  var msg = document.getElementById('epm-msg');
  var nuevo = (document.getElementById('epm-input').value || '').trim();
  if (nuevo.length < 2){
    msg.innerHTML = '<span style="color:#dc2626;">Proveedor invalido (min 2 chars).</span>';
    return;
  }
  if (nuevo === (_epmActual.provActual || '')){
    msg.innerHTML = '<span style="color:#64748b;">Sin cambios.</span>';
    return;
  }
  msg.innerHTML = '<span style="color:#64748b;">Guardando...</span>';
  try {
    var r = await fetch('/api/maestro-mps/' + encodeURIComponent(_epmActual.cod) + '/proveedor', {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({proveedor: nuevo})
    });
    var d = await r.json();
    if (r.ok) {
      msg.innerHTML = '<span style="color:#16a34a;font-weight:700;">&#10003; ' + (d.message || 'Proveedor actualizado') + '</span>';
      // Actualiza la celda + atributo data-prov para futuras ediciones
      try {
        var celda = document.querySelector('.td-prov[data-cod="'+_epmActual.cod+'"]');
        if (celda) {
          celda.setAttribute('data-prov', nuevo);
          var span = celda.firstChild;
          if (span && span.nodeType === Node.TEXT_NODE) {
            celda.removeChild(span);
          } else if (celda.firstElementChild && celda.firstElementChild.tagName === 'SPAN') {
            celda.removeChild(celda.firstElementChild);
          }
          var txt = document.createTextNode(nuevo + ' ');
          celda.insertBefore(txt, celda.firstChild);
        }
      } catch(e){}
      setTimeout(function(){closeModal('m-edit-prov-mp');}, 900);
    } else {
      msg.innerHTML = '<span style="color:#dc2626;">Error: ' + (d.error || r.status) + (d.detail ? ' &mdash; ' + d.detail : '') + '</span>';
    }
  } catch(e) {
    msg.innerHTML = '<span style="color:#dc2626;">Error de red: ' + e.message + '</span>';
  }
}
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

// ─── Confirmar / Cambiar proveedor desde el detalle de SOL ──────
// El user pidió: en lugar del bloque de abajo "Gestionar Solicitud", poner
// arriba la opción de Confirmar (sigue igual el proveedor) o Cambiar.
// Cuando confirma o cambia, alimenta el catálogo de proveedores y la OC.
async function confirmarProveedorOC(numOC){
  var btn = document.getElementById('btn-confirmar-prov');
  var nameEl = document.getElementById('prov-card-name');
  if (!nameEl) return;
  var prov = nameEl.textContent.trim();
  if (!prov) { alert('No hay proveedor para confirmar'); return; }
  if (btn) { btn.disabled = true; btn.textContent = 'Confirmando...'; }
  try {
    var r = await fetch('/api/ordenes-compra/'+encodeURIComponent(numOC)+'/proveedor', {
      method:'PATCH',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({proveedor: prov})
    });
    var d = await r.json();
    if (!d.ok) { alert('Error: '+(d.error||'no se pudo confirmar')); return; }
    if (btn) {
      btn.style.background = '#065f46';
      btn.textContent = '✓ Confirmado';
      setTimeout(function(){ if(btn) btn.disabled = false; }, 1500);
    }
  } catch (e) {
    alert('Error de red: '+e.message);
    if (btn) { btn.disabled = false; btn.textContent = '✓ Confirmar'; }
  }
}

function abrirCambiarProveedor(){
  var box = document.getElementById('prov-cambiar-box');
  if (!box) return;
  box.style.display = box.style.display === 'none' ? 'block' : 'none';
  if (box.style.display === 'block') {
    var input = document.getElementById('prov-cambiar-input');
    if (input) {
      // Pre-poblar con el proveedor actual para que el user solo edite
      var cur = document.getElementById('prov-card-name');
      if (cur && !input.value) input.value = cur.textContent.trim();
      input.focus();
      input.select();
    }
  }
}

async function guardarCambioProveedor(numOC){
  var input = document.getElementById('prov-cambiar-input');
  if (!input) return;
  var nuevo = (input.value||'').trim();
  if (!nuevo) { alert('Ingresá un nombre de proveedor'); return; }
  try {
    var r = await fetch('/api/ordenes-compra/'+encodeURIComponent(numOC)+'/proveedor', {
      method:'PATCH',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({proveedor: nuevo})
    });
    var d = await r.json();
    if (!d.ok) { alert('Error: '+(d.error||'no se pudo cambiar')); return; }
    // Update UI: nombre nuevo + ocultar selector + recargar lista de provs
    var nameEl = document.getElementById('prov-card-name');
    if (nameEl) nameEl.textContent = nuevo;
    var box = document.getElementById('prov-cambiar-box');
    if (box) box.style.display = 'none';
    if (d.creado_en_catalogo) {
      alert('Proveedor cambiado a "'+nuevo+'" — agregado al catálogo para próximos pedidos.');
      // Recargar proveedores en cache global
      try { await loadData(); } catch(e){}
    } else {
      // No alert if just confirmed existing — silent success
    }
  } catch (e) {
    alert('Error de red: '+e.message);
  }
}

// ─── Guardar precios de items (alimenta histórico de precios) ──────
async function guardarPreciosItems(numOC){
  var rows = document.querySelectorAll('#sol-items-table tbody tr[data-cod]');
  if (!rows.length) { alert('No hay items para actualizar'); return; }
  var btn = document.getElementById('btn-guardar-precios');
  if (btn) { btn.disabled = true; btn.textContent = 'Guardando...'; }
  var items = [];
  rows.forEach(function(tr){
    var cod = tr.getAttribute('data-cod');
    var inp = tr.querySelector('input.precio-unit');
    if (!cod || !inp) return;
    var precio = parseFloat((inp.value||'').replace(/[^\d.]/g,''));
    if (!isFinite(precio) || precio <= 0) return;
    items.push({codigo_mp: cod, precio_unitario: precio});
  });
  if (!items.length) {
    alert('Ingresá al menos un precio antes de guardar');
    if (btn) { btn.disabled = false; btn.textContent = '💾 Guardar precios'; }
    return;
  }
  try {
    var r = await fetch('/api/ordenes-compra/'+encodeURIComponent(numOC)+'/items-precios', {
      method:'PATCH',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({items: items})
    });
    var d = await r.json();
    if (!d.ok) { alert('Error: '+(d.error||'no se pudo guardar')); }
    else {
      var totalEl = document.getElementById('sol-valor-total');
      if (totalEl && d.valor_total_nuevo != null) totalEl.textContent = fmt(d.valor_total_nuevo);
      // Visual feedback
      if (btn) { btn.style.background = '#065f46'; btn.textContent = '✓ Guardado · '+d.items_actualizados+' items'; }
      setTimeout(function(){
        if (btn) { btn.disabled = false; btn.style.background = '#0f766e'; btn.textContent = '💾 Guardar precios'; }
      }, 2000);
    }
  } catch (e) {
    alert('Error de red: '+e.message);
    if (btn) { btn.disabled = false; btn.textContent = '💾 Guardar precios'; }
  }
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
    // ── Datos de Pago ──
    var _pd=d.prov_data||null;
    if(!_pd&&o.proveedor){
      var _pf=PROVS.find(function(x){ return x.nombre===o.proveedor; });
      if(_pf) _pd={banco:_pf.banco,tipo_cuenta:_pf.tipo_cuenta,num_cuenta:_pf.num_cuenta,nit:_pf.nit,email:_pf.email,telefono:_pf.telefono};
    }
    // Fallback: parse observaciones for CC orders with inline banking data
    if(!_pd&&o.observaciones&&o.observaciones.indexOf('BANCO:')>=0){
      var _ob=o.observaciones;
      function _xob(key){
        var idx=_ob.indexOf(key+':'); if(idx<0) return '';
        var rest=_ob.slice(idx+key.length+1).trim();
        var end=rest.indexOf(' | '); return end>=0?rest.slice(0,end).trim():rest.trim();
      }
      var _bancoRaw=_xob('BANCO');
      if(_bancoRaw){
        var _bparts=_bancoRaw.split(' ');
        _pd={banco:_bparts[0]||_bancoRaw,tipo_cuenta:_bparts.slice(1).join(' ')||'',
          num_cuenta:_xob('CUENTA/CEL'),nit:_xob('CED/NIT')};
      }
    }
    if(_pd&&(_pd.banco||_pd.num_cuenta)){
      h+='<div style="margin-top:14px;background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:12px;">';
      h+='<div style="font-weight:800;font-size:12px;color:#166534;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">&#x1F4B3; Datos de Pago</div>';
      h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;font-size:12px;">';
      if(_pd.banco) h+='<div><span style="color:#166534;font-weight:600;">Banco:</span> <strong>'+esc(_pd.banco)+'</strong></div>';
      if(_pd.tipo_cuenta) h+='<div><span style="color:#166534;font-weight:600;">Tipo cuenta:</span> '+esc(_pd.tipo_cuenta)+'</div>';
      if(_pd.num_cuenta) h+='<div style="grid-column:span 2;"><span style="color:#166534;font-weight:600;">N\u00BA cuenta:</span> <strong style="font-family:monospace;font-size:13px;letter-spacing:.5px;">'+esc(_pd.num_cuenta)+'</strong></div>';
      if(_pd.nit) h+='<div><span style="color:#166534;font-weight:600;">NIT / CC:</span> '+esc(_pd.nit)+'</div>';
      if(_pd.email) h+='<div><span style="color:#166534;font-weight:600;">Email:</span> '+esc(_pd.email)+'</div>';
      if(_pd.telefono) h+='<div><span style="color:#166534;font-weight:600;">Tel:</span> '+esc(_pd.telefono)+'</div>';
      h+='</div>';
      if(o.valor_total){
        h+='<div style="margin-top:10px;padding-top:8px;border-top:1px solid #bbf7d0;">';
        if(o.con_iva&&o.valor_sin_iva>0){
          var _iva=Math.round(o.valor_sin_iva*0.19);
          h+='<div style="font-size:11px;color:#166534;">Subtotal: '+fmt(o.valor_sin_iva)+'</div>';
          h+='<div style="font-size:11px;color:#166534;">IVA 19%: '+fmt(_iva)+'</div>';
        }
        h+='<div style="font-size:15px;font-weight:800;color:#15803d;margin-top:3px;">Total a pagar: '+fmt(o.valor_total)+'</div>';
      }
      h+='</div>';
    }
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
var CC_SOLIC=[];
var _SOLIC_CAT_FILTER='ALL';
function descargarSolicitudesPDF(){
  // Filtra por el estado seleccionado en el dropdown si lo hay; si no, baja
  // Pendientes+Aprobadas (lo más útil para que Gerencia revise lo que falta).
  var estados = (document.getElementById('s-solic')||{value:''}).value;
  var qs = estados ? '?estados='+encodeURIComponent(estados) : '?estados=Pendiente,Aprobada';
  window.open('/api/compras/solicitudes/pdf'+qs, '_blank');
}

async function regenerarSolicitudesAuto(){
  if(!confirm('REGENERAR solicitudes auto-generadas?\\n\\n' +
              'Esto va a:\\n' +
              ' • Borrar todas las solicitudes Pendiente que digan "Auto-generada Centro Programación"\\n' +
              ' • Borrar sus OCs Borrador asociadas\\n' +
              ' • Crear nuevas con los déficits ACTUALES de Programación\\n\\n' +
              'NO toca solicitudes Aprobadas ni Pagadas.\\n\\n' +
              '¿Confirmás?')) return;
  try{
    var r = await fetch('/api/programacion/regenerar-oc', {method:'POST'});
    var d = await r.json();
    if(!r.ok){
      alert('Error: ' + (d.error || 'desconocido') + (d.detalle ? '\\n' + d.detalle : ''));
      return;
    }
    alert(d.mensaje || 'Regeneración completa');
    await loadSolicitudes();
  }catch(e){
    alert('Error de red: ' + e.message);
  }
}

async function loadSolicitudes(){
  try{
    var _results=await Promise.all([
      fetch('/api/solicitudes-compra').then(function(r){ return r.json(); }),
      fetch('/api/solicitudes-compra?categoria=Cuenta+de+Cobro').then(function(r){ return r.json(); })
    ]);
    var _all=(_results[0].solicitudes||[]).concat(_results[1].solicitudes||[]);
    var _seen={};
    SOLIC=_all.filter(function(s){ if(_seen[s.numero]) return false; _seen[s.numero]=1; return true; });
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

// Helpers para ordenar — usados por renderInfluencers()
function _infFechaOrden(s){
  return (s.fecha_requerida && String(s.fecha_requerida).trim())
      || (s.fecha && String(s.fecha).trim())
      || '9999-12-31';
}
function _infEstadoRank(e){
  if(e==='Aprobada')  return 0;
  if(e==='Pendiente') return 1;
  if(e==='Pagada')    return 2;
  return 3;
}
function _infSortFn(criterio){
  // Devuelve la función de comparación según el criterio elegido por el user.
  if(criterio==='urgente'){
    return function(a,b){
      var fa=_infFechaOrden(a), fb=_infFechaOrden(b);
      if(fa!==fb) return fa<fb?-1:1;
      return (a.numero||'').localeCompare(b.numero||'');
    };
  }
  if(criterio==='valor_desc'){
    return function(a,b){ return (b.valor||0)-(a.valor||0); };
  }
  if(criterio==='valor_asc'){
    return function(a,b){ return (a.valor||0)-(b.valor||0); };
  }
  if(criterio==='reciente'){
    return function(a,b){
      var fa=(a.fecha||''), fb=(b.fecha||'');
      if(fa!==fb) return fa<fb?1:-1; // descendente
      return (a.numero||'').localeCompare(b.numero||'');
    };
  }
  if(criterio==='antiguo'){
    return function(a,b){
      var fa=(a.fecha||'9999'), fb=(b.fecha||'9999');
      if(fa!==fb) return fa<fb?-1:1;
      return (a.numero||'').localeCompare(b.numero||'');
    };
  }
  // default: estado_fecha (Aprobadas → Pendientes → Pagadas → resto, fecha asc)
  return function(a,b){
    var ra=_infEstadoRank(a.estado), rb=_infEstadoRank(b.estado);
    if(ra!==rb) return ra-rb;
    var fa=_infFechaOrden(a), fb=_infFechaOrden(b);
    if(fa!==fb) return fa<fb?-1:1;
    return (a.numero||'').localeCompare(b.numero||'');
  };
}
function fmoney(v){ return '$'+Number(v||0).toLocaleString('es-CO'); }
function renderInfluencers(){
  var q=(document.getElementById('q-influencer')||{value:''}).value.toLowerCase();
  var st=(document.getElementById('s-influencer')||{value:'Aprobada'}).value;
  var ordCriterio=(document.getElementById('order-influencer')||{value:'estado_fecha'}).value;
  // Sort defensivo: aplicamos el criterio elegido SIEMPRE antes de filtrar/render
  if(Array.isArray(INFLUENCERS) && INFLUENCERS.length){
    INFLUENCERS.sort(_infSortFn(ordCriterio));
  }
  // Mostrar al user el criterio activo + diagnóstico de fechas
  var helpEl=document.getElementById('pills-influencer-help');
  if(helpEl){
    var labels={
      estado_fecha:'Por pagar primero (Aprobadas → Pendientes → Pagadas, luego fecha más vieja)',
      urgente:'Fecha de pago debido — más antiguas arriba',
      valor_desc:'Mayor valor de pago primero',
      valor_asc:'Menor valor de pago primero',
      reciente:'Fecha de creación — más reciente arriba',
      antiguo:'Fecha de creación — más antiguo arriba',
    };
    // Cuántas tienen fecha_requerida (para que vea por qué a veces parece desordenado)
    var con_fecha_req = INFLUENCERS.filter(function(s){return s.fecha_requerida && String(s.fecha_requerida).trim();}).length;
    var msg='Orden: <strong>'+(labels[ordCriterio]||ordCriterio)+'</strong>';
    if((ordCriterio==='estado_fecha' || ordCriterio==='urgente') && INFLUENCERS.length){
      msg += ' · '+con_fecha_req+'/'+INFLUENCERS.length+' tienen fecha de pago debido';
      if(con_fecha_req===0){
        msg += ' <span style="color:#b94400;font-weight:600;">→ todas usan fecha de creación, prueba "Mayor valor" para mejor orden</span>';
      }
    }
    helpEl.innerHTML=msg;
  }

  // ── Parse beneficiary block from observaciones text ──────────────────────
  function parseBenef(obs){
    var out={nombre:'',banco:'',cuenta:'',cedNit:'',valor:''};
    if(!obs) return out;
    var m;
    m=obs.match(/BENEFICIARIO:\\s*([^|]+)/i); if(m) out.nombre=m[1].trim();
    m=obs.match(/BANCO:\\s*([^|]+)/i);        if(m) out.banco=m[1].trim();
    m=obs.match(/CUENTA\\/CEL:\\s*([^|]+)/i);  if(m) out.cuenta=m[1].trim();
    m=obs.match(/CED\\/NIT:\\s*([^|]+)/i);     if(m) out.cedNit=m[1].trim();
    m=obs.match(/VALOR:\\s*([^|]+)/i);        if(m) out.valor=m[1].trim();
    return out;
  }

  var pendAll=INFLUENCERS.filter(function(s){ return s.estado==='Aprobada'; });
  var pagaAll=INFLUENCERS.filter(function(s){ return s.estado==='Pagada'; });
  var totalPend=pendAll.reduce(function(a,s){ return a+(s.valor||0); },0);
  var totalPaga=pagaAll.reduce(function(a,s){ return a+(s.valor||0); },0);

  // ── KPI cards ────────────────────────────────────────────────────────────
  var kpiEl=document.getElementById('kpi-influencer');
  if(kpiEl){
    kpiEl.innerHTML=
      '<div style="background:#7c3aed;color:#fff;padding:14px 22px;border-radius:10px;min-width:170px;box-shadow:0 2px 8px rgba(124,58,237,.2)">'
      +'<div style="font-size:11px;opacity:.8;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Por pagar</div>'
      +'<div style="font-size:26px;font-weight:700;margin-top:4px;">'+pendAll.length+' OCs</div>'
      +'<div style="font-size:13px;opacity:.9;margin-top:2px;">'+fmoney(totalPend)+'</div>'
      +'</div>'
      +'<div style="background:#059669;color:#fff;padding:14px 22px;border-radius:10px;min-width:170px;box-shadow:0 2px 8px rgba(5,150,105,.2)">'
      +'<div style="font-size:11px;opacity:.8;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Pagadas este ciclo</div>'
      +'<div style="font-size:26px;font-weight:700;margin-top:4px;">'+pagaAll.length+'</div>'
      +'<div style="font-size:13px;opacity:.9;margin-top:2px;">'+fmoney(totalPaga)+'</div>'
      +'</div>'
      +'<div style="background:#374151;color:#fff;padding:14px 22px;border-radius:10px;min-width:170px;box-shadow:0 2px 8px rgba(55,65,81,.15)">'
      +'<div style="font-size:11px;opacity:.8;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Total influencers</div>'
      +'<div style="font-size:26px;font-weight:700;margin-top:4px;">'+INFLUENCERS.length+'</div>'
      +'</div>';
  }

  // ── Filter list ──────────────────────────────────────────────────────────
  var list=INFLUENCERS.filter(function(s){
    if(st && s.estado!==st) return false;
    if(q){
      var hay=(s.numero||'')+(s.solicitante||'')+(s.observaciones||'')+(s.numero_oc||'');
      if(hay.toLowerCase().indexOf(q)<0) return false;
    }
    return true;
  });

  var el=document.getElementById('pills-influencer');
  if(el) el.innerHTML='<span class="pill">'+list.length+' mostradas</span>';

  // ── Card builder ─────────────────────────────────────────────────────────
  function buildCard(s){
    var b=parseBenef(s.observaciones||'');
    // Fallback: si los datos NO vienen en observaciones, usar los del
    // influencer linkado (nuevo enriquecimiento desde marketing_influencers
    // via influencer_id). Así "Luisa" deja de aparecer sin datos cuando la
    // solicitud fue creada sin el bloque BENEFICIARIO en obs.
    if(!b.nombre && s.inf_nombre) b.nombre = s.inf_nombre;
    if(!b.banco && s.inf_banco) {
      b.banco = s.inf_banco + (s.inf_tipo_cuenta ? ' ' + s.inf_tipo_cuenta : '');
    }
    if(!b.cuenta && s.inf_cuenta) b.cuenta = s.inf_cuenta;
    if(!b.cedNit && s.inf_cedula) b.cedNit = s.inf_cedula;
    var isPagada=s.estado==='Pagada';
    var isRech=s.estado==='Rechazada';
    var borderColor=isPagada?'#059669':isRech?'#dc2626':'#7c3aed';
    var headerBg=isPagada?'#f0fdf4':isRech?'#fef2f2':'#faf5ff';

    // Badge
    var badgeMap={'Aprobada':{bg:'#ede9fe',fg:'#5b21b6',txt:'💸 Lista para pagar'},
                  'Pagada':{bg:'#d1fae5',fg:'#065f46',txt:'✅ Pagada'},
                  'Rechazada':{bg:'#fee2e2',fg:'#991b1b',txt:'❌ Rechazada'},
                  'Pendiente':{bg:'#fef3c7',fg:'#92400e',txt:'⏳ Pendiente'}};
    var cfg=badgeMap[s.estado]||{bg:'#f3f4f6',fg:'#374151',txt:s.estado};

    // Bank info row — only show if parsed
    var bankRow='';
    if(b.nombre||b.banco||b.cuenta){
      bankRow='<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 14px;margin:10px 0;display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;font-size:12px;">'
        +(b.nombre?'<div><span style="color:#64748b;font-weight:600;text-transform:uppercase;font-size:10px;">Beneficiario</span><div style="color:#1e293b;font-weight:600;margin-top:1px;">'+esc(b.nombre)+'</div></div>':'')
        +(b.banco?'<div><span style="color:#64748b;font-weight:600;text-transform:uppercase;font-size:10px;">Banco</span><div style="color:#1e293b;margin-top:1px;">'+esc(b.banco)+'</div></div>':'')
        +(b.cuenta?'<div><span style="color:#64748b;font-weight:600;text-transform:uppercase;font-size:10px;">Cuenta / Cel</span><div style="color:#1e293b;font-family:monospace;margin-top:1px;">'+esc(b.cuenta)+'</div></div>':'')
        +(b.cedNit?'<div><span style="color:#64748b;font-weight:600;text-transform:uppercase;font-size:10px;">Cédula / NIT</span><div style="color:#1e293b;font-family:monospace;margin-top:1px;">'+esc(b.cedNit)+'</div></div>':'')
        +'</div>';
    }

    // Action buttons
    var btns='';
    if(s.estado==='Aprobada'){
      btns='<button class="btn inf-pagar" data-oc="'+esc(s.numero_oc||'')+'" data-sol="'+esc(s.numero)+'" data-val="'+Number(s.valor||0)+'" style="background:#7c3aed;color:#fff;padding:7px 18px;font-size:13px;font-weight:600;">💸 Pagar ahora</button>'
          +'<button class="btn inf-rechazar" data-oc="'+esc(s.numero_oc||'')+'" data-sol="'+esc(s.numero)+'" style="background:#fee2e2;color:#dc2626;border:1px solid #fecaca;padding:7px 14px;font-size:13px;">✕ Rechazar</button>'
          +'<button class="btn inf-eliminar" data-sol="'+esc(s.numero)+'" data-nombre="'+esc((b.nombre||s.solicitante||s.numero))+'" style="background:#f3f4f6;color:#6b7280;border:1px solid #d1d5db;padding:7px 12px;font-size:12px;" title="Eliminar definitivamente esta solicitud (no genera comprobante)">🗑 Eliminar</button>';
    } else if(s.estado==='Pendiente'){
      btns='<button class="btn" data-act="del-sol" data-sol="'+esc(s.numero)+'" style="background:#fee2e2;color:#dc2626;border:1px solid #fecaca;font-size:12px;">🗑 Eliminar</button>';
    } else if(s.estado==='Rechazada'){
      btns='<button class="btn" data-act="del-sol" data-sol="'+esc(s.numero)+'" style="background:#fee2e2;color:#dc2626;border:1px solid #fecaca;font-size:11px;padding:3px 8px;">🗑</button>';
    }

    return '<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+borderColor+';border-radius:10px;padding:0;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,.06);overflow:hidden;">'
      // Header
      +'<div style="background:'+headerBg+';padding:12px 16px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">'
        +'<div style="display:flex;align-items:center;gap:10px;">'
          +'<div style="font-family:monospace;font-size:13px;font-weight:700;color:#374151;">'+esc(s.numero)+'</div>'
          +(s.numero_oc?'<div style="font-family:monospace;font-size:11px;color:#7c3aed;background:#ede9fe;padding:2px 8px;border-radius:4px;">'+esc(s.numero_oc)+'</div>':'')
        +'</div>'
        +'<div style="display:flex;align-items:center;gap:10px;">'
          +'<div style="font-size:18px;font-weight:700;color:'+borderColor+';">'+fmoney(s.valor)+'</div>'
          +'<span style="background:'+cfg.bg+';color:'+cfg.fg+';padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;">'+cfg.txt+'</span>'
        +'</div>'
      +'</div>'
      // Body
      +'<div style="padding:12px 16px;">'
        +'<div style="display:flex;gap:16px;font-size:12px;color:#64748b;margin-bottom:8px;flex-wrap:wrap;align-items:center;">'
          +'<span>👤 '+esc(s.solicitante||'-')+'</span>'
          +(s.fecha_requerida && String(s.fecha_requerida).trim()
              ? '<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:6px;font-weight:600;">📅 Pago debido: '+fdate(s.fecha_requerida)+'</span>'
              : '<span>📅 Solicitud: '+fdate(s.fecha)+'</span>')
          +'<span>🏢 '+esc(s.area||'Marketing/ANIMUS')+'</span>'
        +'</div>'
        +bankRow
        +(btns?'<div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap;">'+btns+'</div>':'')
      +'</div>'
    +'</div>';
  }

  // ── Render pending grid ───────────────────────────────────────────────────
  var gel=document.getElementById('grid-influencer');
  var gpag=document.getElementById('grid-influencer-pagadas');
  if(!gel) return;

  if(!list.length){
    gel.innerHTML='<div class="empty">No hay resultados para el filtro seleccionado</div>';
  } else {
    // Badge "#N en la cola" solo para Aprobadas (los Por pagar)
    var rank=0;
    var cards=list.map(function(s){
      var c=buildCard(s);
      if(s.estado==='Aprobada'){
        rank++;
        var badge='<div style="display:inline-block;background:#7c3aed;color:#fff;font-size:11px;font-weight:700;padding:3px 10px;border-radius:6px;margin-bottom:6px;">#'+rank+' en cola</div>';
        // Insertar el badge dentro del header de la card
        c=c.replace('<div style="font-family:monospace;font-size:13px;font-weight:700;color:#374151;">',
                    badge+'<div style="font-family:monospace;font-size:13px;font-weight:700;color:#374151;">');
      }
      return c;
    });
    gel.innerHTML=cards.join('');
  }

  // ── Paid section (always shown when filter is not "Pagada") ───────────────
  if(gpag){
    if(st==='' || st==='Aprobada'){
      // Show a collapsible paid section below
      if(pagaAll.length>0){
        gpag.innerHTML='<details style="margin-top:20px;">'
          +'<summary style="cursor:pointer;font-size:13px;font-weight:600;color:#059669;padding:10px 14px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;list-style:none;display:flex;align-items:center;gap:8px;">'
          +'✅ '+pagaAll.length+' pago'+(pagaAll.length>1?'s':'')+' realizados — '+fmoney(totalPaga)
          +' <span style="font-size:11px;color:#64748b;font-weight:400;margin-left:4px;">(click para ver)</span>'
          +'</summary>'
          +'<div style="margin-top:10px;">'+pagaAll.map(buildCard).join('')+'</div>'
          +'</details>';
      } else {
        gpag.innerHTML='';
      }
    } else {
      gpag.innerHTML='';
    }
  }

  // ── Event delegation ──────────────────────────────────────────────────────
  function attachEvents(container){
    if(!container) return;
    container.onclick=function(e){
      var bp=e.target.closest('.inf-pagar');
      var br=e.target.closest('.inf-rechazar');
      var bd=e.target.closest('[data-act="del-sol"]');
      var be=e.target.closest('.inf-eliminar');
      if(bp) pagarInfluencer(bp.dataset.oc, bp.dataset.sol, Number(bp.dataset.val));
      if(br) rechazarInfluencer(br.dataset.oc, br.dataset.sol);
      if(bd) eliminarSolicitud(bd.dataset.sol);
      if(be) eliminarSolicitudAprobada(be.dataset.sol, be.dataset.nombre);
    };
  }
  attachEvents(gel);
  attachEvents(gpag);
}

function eliminarSolicitudAprobada(sol_num, nombre){
  // Confirmación más fuerte porque la solicitud está Aprobada (lista para
  // pagar). Si la borrás se pierde la cola de pago.
  var msg = 'ELIMINAR ' + (nombre || sol_num) + '?\\n\\n'
          + 'Esta solicitud está APROBADA (lista para pagar). Si la eliminas se '
          + 'borra del sistema y NO podrás generar comprobante después.\\n\\n'
          + 'Solo confirma si:\\n'
          + ' · Ya pagaste por fuera y no necesitas comprobante en la app\\n'
          + ' · La cargaste por error\\n\\n'
          + '¿Eliminar definitivamente?';
  if(!confirm(msg)) return;
  fetch('/api/solicitudes-compra/'+encodeURIComponent(sol_num),
        {method:'DELETE'})
    .then(function(r){return r.json();})
    .then(function(d){
      if(d.ok || d.message){
        loadInfluencers();
      } else {
        alert('Error: ' + (d.error || 'no se pudo eliminar'));
      }
    })
    .catch(function(){ alert('Error de conexión'); });
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
  var sub=document.getElementById('m-rechazar-inf-sub');
  if(sub) sub.textContent=sol_num ? 'Solicitud '+sol_num : '';
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
  var cat=_SOLIC_CAT_FILTER||'ALL';

  // Build OC lookup map for inline display
  var ocMap={};
  (OCS||[]).forEach(function(o){ ocMap[o.numero_oc]=o; });

  var list=SOLIC.filter(function(s){
    // Always exclude Influencer/Marketing (has its own tab), unless cat filter is 'inf'
    if(cat==='ALL'||(cat!=='inf')){
      if((s.categoria||'').indexOf('Influencer')>=0) return false;
    }
    // Category filter
    if(cat==='ALL'){
      // show all except influencer (already excluded above)
    } else if(cat==='cc'){
      if((s.categoria||'').indexOf('Cuenta de Cobro')<0) return false;
    } else if(cat==='inf'){
      if((s.categoria||'').indexOf('Influencer')<0) return false;
    } else {
      if(!inGroup(s.categoria,cat)) return false;
    }
    // Estado filter
    if(st&&s.estado!==st) return false;
    // Search
    var oc=ocMap[s.numero_oc];
    var ocNum=oc?oc.numero_oc:'';
    if(q&&(s.numero||'').toLowerCase().indexOf(q)<0
        &&(s.solicitante||'').toLowerCase().indexOf(q)<0
        &&(s.observaciones||'').toLowerCase().indexOf(q)<0
        &&ocNum.toLowerCase().indexOf(q)<0) return false;
    return true;
  });

  var pend=list.filter(function(s){ return s.estado==='Pendiente'; }).length;
  var apro=list.filter(function(s){ return s.estado==='Aprobada'; }).length;
  var rech=list.filter(function(s){ return s.estado==='Rechazada'; }).length;
  var paga=list.filter(function(s){ return s.estado==='Pagada'; }).length;
  var pills='<span class="pill">'+list.length+' solicitudes</span>';
  if(pend) pills+='<span class="pill y">Pendiente: '+pend+'</span>';
  if(apro) pills+='<span class="pill g">Aprobada: '+apro+'</span>';
  if(rech) pills+='<span class="pill" style="background:#fee2e2;color:#991b1b;">Rechazada: '+rech+'</span>';
  if(paga) pills+='<span class="pill" style="background:#e0f2fe;color:#075985;">Pagada: '+paga+'</span>';
  document.getElementById('pills-solic').innerHTML=pills;

  if(!list.length){
    document.getElementById('grid-solic').innerHTML='<div class="empty">No hay solicitudes'+(cat!=='ALL'?' en esta categoría':'')+'</div>';
    return;
  }

  var urgColor={'Normal':'#16a34a','Urgente':'#d97706','Critico':'#dc2626','Alta':'#dc2626','Media':'#d97706'};
  var stBg={'Pendiente':'#fef3c7','Aprobada':'#dcfce7','Rechazada':'#fee2e2','Pagada':'#e0f2fe'};
  var stFg={'Pendiente':'#92400e','Aprobada':'#166534','Rechazada':'#991b1b','Pagada':'#075985'};

  document.getElementById('grid-solic').innerHTML=list.map(function(s){
    var urg=s.urgencia||'Normal';
    var urgC=urgColor[urg]||'#78716c';
    var stB=stBg[s.estado]||'#f3f4f6';
    var stF=stFg[s.estado]||'#374151';
    // OC inline badge
    var oc=ocMap[s.numero_oc];
    var ocBadge='';
    if(oc){
      var ocStBg={'Revisada':'#fef3c7','Autorizada':'#d1fae5','Pagada':'#e0f2fe','Recibida':'#f3e8ff'}[oc.estado]||'#f3f4f6';
      var ocStFg={'Revisada':'#92400e','Autorizada':'#065f46','Pagada':'#075985','Recibida':'#6b21a8'}[oc.estado]||'#374151';
      ocBadge='<span style="font-family:monospace;font-size:10px;background:'+ocStBg+';color:'+ocStFg+';border-radius:4px;padding:1px 6px;margin-left:6px;" title="Orden de Compra vinculada">'+esc(oc.numero_oc)+'</span>';
    } else if(s.numero_oc){
      ocBadge='<span style="font-family:monospace;font-size:10px;background:#f3f4f6;color:#9ca3af;border-radius:4px;padding:1px 6px;margin-left:6px;">'+esc(s.numero_oc)+'</span>';
    }
    return '<div class="card" data-num="'+esc(s.numero)+'">'
      +'<div class="ch"><div><div class="cnum" style="font-family:monospace;">'+esc(s.numero)+ocBadge+'</div>'
      +'<div class="cprov">'+esc(s.solicitante||'-')+' &mdash; '+esc(s.area||'-')+'</div></div>'
      +'<span class="badge" style="background:'+stB+';color:'+stF+';">'+s.estado+'</span></div>'
      +'<div class="cmeta"><span>'+fdate(s.fecha)+'</span><span>'+esc(s.empresa||'Espagiria')+'</span>'
      +'<span>'+esc(s.categoria||'-')+'</span>'
      +'<span style="color:'+urgC+';font-weight:700;">'+esc(urg)+'</span></div>'
      +(s.observaciones?'<div class="cobs">'+esc((s.observaciones||'').substring(0,100))+'</div>':'')
      +'<div class="acts" style="gap:6px;"><button class="btn bo bs" data-act="sdet" data-sol="'+esc(s.numero)+'">&#128203; Ver &amp; Gestionar</button>'+'<button class="btn" style="background:#fee2e2;color:#dc2626;border:1px solid #fecaca;padding:4px 10px;font-size:11px;" data-act="del-sol" data-sol="'+esc(s.numero)+'">&#x1F5D1;</button>'+'</div>'
      +'</div>';
  }).join('');
}
function setSolicCat(btn){
  _SOLIC_CAT_FILTER=(btn&&btn.getAttribute('data-scat'))||'ALL';
  document.querySelectorAll('.ocs-cpill').forEach(function(b){ b.classList.remove('on'); });
  if(btn) btn.classList.add('on');
  renderSolicitudes();
}

function renderCCSolicitudes(){
  var pend=CC_SOLIC.filter(function(s){ return s.estado==='Pendiente'; });
  var badge=document.getElementById('cc-solic-badge');
  if(badge) badge.textContent=pend.length;
  var pills=document.getElementById('pills-cc-solic');
  var grid=document.getElementById('grid-cc-solic');
  if(!grid) return;
  if(!pend.length){
    if(pills) pills.innerHTML='';
    grid.innerHTML='<div class="empty" style="color:#86efac;">&#10003; Sin solicitudes pendientes</div>';
    return;
  }
  if(pills) pills.innerHTML='<span class="pill y">Pendiente: '+pend.length+'</span>';
  var urgColor={'Normal':'#16a34a','Urgente':'#d97706','Critico':'#dc2626'};
  grid.innerHTML=pend.map(function(s){
    var urg=s.urgencia||'Normal';
    var urgC=urgColor[urg]||'#78716c';
    var obs=(s.observaciones||'').substring(0,100);
    var val=s.valor>0?(' &mdash; '+fmoney(s.valor)):'';  
    return '<div class="card" style="border-left:3px solid #f59e0b;">'
      +'<div class="ch"><div><div class="cnum" style="font-family:monospace;">'+esc(s.numero)+'</div>'
      +'<div class="cprov">'+esc(s.solicitante||'-')+' &mdash; '+esc(s.area||'-')+'</div></div>'
      +'<span class="badge" style="background:#fef3c7;color:#92400e;">Pendiente</span></div>'
      +'<div class="cmeta"><span>'+fdate(s.fecha)+'</span><span>'+esc(s.empresa||'Espagiria')+'</span>'
      +'<span style="color:'+urgC+';font-weight:700;">'+esc(urg)+'</span>'
      +(s.fecha_requerida?'<span>Req: '+fdate(s.fecha_requerida)+'</span>':'')+'</div>'
      +(obs?'<div class="cobs">'+esc(obs)+'</div>':'')
      +'<div class="acts" style="gap:6px;"><button class="btn bo bs" data-act="sdet" data-sol="'+esc(s.numero)+'">&#x1F4CB; Revisar &amp; Aprobar</button><button class="btn" style="background:#fee2e2;color:#dc2626;border:1px solid #fecaca;padding:4px 10px;font-size:11px;" data-act="del-sol" data-sol="'+esc(s.numero)+'">&#x1F5D1;</button></div>'
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
    var oc=d.oc||null;
    var stBg={'Pendiente':'#fef3c7','Aprobada':'#dcfce7','Rechazada':'#fee2e2','Pagada':'#dbeafe'};
    var stFg={'Pendiente':'#92400e','Aprobada':'#166534','Rechazada':'#991b1b','Pagada':'#1e40af'};
    var urgColor={'Alta':'#dc2626','Urgente':'#b91c1c','Normal':'#0891b2','Baja':'#6b7280'};

    var h='<div style="padding:0;background:#fff;">';
    // Header con paleta teal HHA
    h+='<div style="background:linear-gradient(135deg,#1F5F5B 0%,#10464a 100%);padding:18px 22px;color:#fff;">';
    h+='<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">';
    h+='<div style="display:flex;align-items:center;gap:14px;">';
    h+='<div style="font-size:11px;opacity:.8;text-transform:uppercase;letter-spacing:1px;">SOLICITUD DE COMPRA</div>';
    h+='</div>';
    h+='<span style="background:'+(stBg[s.estado]||'#f3f4f6')+';color:'+(stFg[s.estado]||'#374151')+';font-size:11px;font-weight:700;padding:5px 12px;border-radius:14px;letter-spacing:.4px;">'+esc((s.estado||'').toUpperCase())+'</span>';
    h+='</div>';
    h+='<div style="font-weight:800;font-size:24px;font-family:monospace;letter-spacing:.5px;margin-top:4px;">'+esc(s.numero||num)+'</div>';
    h+='<div style="display:flex;gap:18px;flex-wrap:wrap;font-size:12px;opacity:.92;margin-top:4px;">';
    h+='<span>👤 '+esc(s.solicitante||'-')+'</span>';
    h+='<span>🏭 '+esc(s.area||'-')+' · '+esc(s.empresa||'Espagiria')+'</span>';
    h+='<span>📅 '+fdate(s.fecha)+'</span>';
    h+='<span style="background:rgba(255,255,255,.15);padding:1px 8px;border-radius:6px;color:'+(urgColor[s.urgencia]||'#fff')+';background:rgba(255,255,255,.18);">⚡ '+esc(s.urgencia||'Normal')+'</span>';
    h+='</div>';
    h+='</div>';

    // Cuerpo
    h+='<div style="padding:24px 28px;">';

    // ── PROVEEDOR INTERACTIVO ─────────────────────────────────────────
    // Card del proveedor con acciones inline: Confirmar (verde) / Cambiar.
    // Esto reemplaza al "selector + valor + fecha" que vivía abajo.
    // Sirve para alimentar el sistema cuando Catalina valida/corrige.
    var provName = (oc && oc.proveedor) ? oc.proveedor : '';
    var ocNum = oc ? esc(oc.numero_oc) : '';
    if(provName && oc){
      h+='<div id="prov-card" data-oc="'+ocNum+'" style="background:linear-gradient(135deg,#f0fdfa 0%,#ccfbf1 100%);border:1px solid #5eead4;border-radius:12px;padding:16px 22px;margin-bottom:18px;box-shadow:0 1px 3px rgba(15,118,110,.08);">';
      h+='<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">';
      h+='<div style="display:flex;align-items:center;gap:14px;">';
      h+='<div style="font-size:34px;line-height:1;">🏢</div>';
      h+='<div>';
      h+='<div style="font-size:10px;color:#0f766e;text-transform:uppercase;letter-spacing:1px;font-weight:700;">PROVEEDOR SUGERIDO</div>';
      h+='<div id="prov-card-name" style="font-size:22px;font-weight:800;color:#0f766e;letter-spacing:.3px;margin-top:2px;">'+esc(provName)+'</div>';
      h+='</div>';
      h+='</div>';
      // Acciones (solo si la SOL está pendiente) + Valor total
      if(s.estado === 'Pendiente'){
        h+='<div style="display:flex;gap:8px;align-items:center;">';
        h+='<button id="btn-confirmar-prov" onclick="confirmarProveedorOC(&quot;'+ocNum+'&quot;)" style="background:#16a34a;color:#fff;border:none;border-radius:8px;padding:8px 14px;font-size:12px;font-weight:700;cursor:pointer;">✓ Confirmar</button>';
        h+='<button onclick="abrirCambiarProveedor()" style="background:#fff;color:#0f766e;border:1px solid #5eead4;border-radius:8px;padding:8px 14px;font-size:12px;font-weight:700;cursor:pointer;">↻ Cambiar</button>';
        h+='</div>';
      } else if(oc.valor_total > 0){
        h+='<div style="text-align:right;">';
        h+='<div style="font-size:10px;color:#0f766e;text-transform:uppercase;letter-spacing:.6px;font-weight:700;">Valor total OC</div>';
        h+='<div style="font-size:24px;font-weight:800;color:#0f766e;">'+fmt(oc.valor_total)+'</div>';
        h+='</div>';
      }
      h+='</div>';
      // Selector inline (oculto por defecto)
      h+='<div id="prov-cambiar-box" style="display:none;margin-top:12px;padding-top:12px;border-top:1px dashed #5eead4;">';
      h+='<div style="font-size:11px;color:#0f766e;font-weight:700;text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px;">Cambiar proveedor</div>';
      h+='<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">';
      h+='<input id="prov-cambiar-input" list="prov-dl-detail" placeholder="Nombre del proveedor..." style="flex:1;min-width:200px;padding:8px 12px;border:1px solid #5eead4;border-radius:8px;font-size:13px;">';
      h+='<datalist id="prov-dl-detail">';
      PROVS.forEach(function(p){ h+='<option value="'+esc(p.nombre)+'">'; });
      h+='</datalist>';
      h+='<button onclick="guardarCambioProveedor(&quot;'+ocNum+'&quot;)" style="background:#0f766e;color:#fff;border:none;border-radius:8px;padding:8px 16px;font-size:12px;font-weight:700;cursor:pointer;">Guardar</button>';
      h+='<button onclick="document.getElementById(&quot;prov-cambiar-box&quot;).style.display=&quot;none&quot;" style="background:#fff;color:#64748b;border:1px solid #cbd5e1;border-radius:8px;padding:8px 14px;font-size:12px;cursor:pointer;">Cancelar</button>';
      h+='</div>';
      h+='<div style="font-size:11px;color:#64748b;margin-top:6px;">Si el proveedor no existe se crea automáticamente y queda en el catálogo para próximos pedidos.</div>';
      h+='</div>';
      h+='</div>';
    } else if(oc){
      // OC existe pero sin proveedor asignado — selector grande para asignar
      h+='<div id="prov-card" style="background:#fef2f2;border:1px solid #fca5a5;border-radius:12px;padding:14px 22px;margin-bottom:18px;">';
      h+='<div style="font-size:11px;color:#991b1b;text-transform:uppercase;letter-spacing:.6px;font-weight:700;margin-bottom:8px;">⚠ Sin proveedor asignado</div>';
      if(s.estado==='Pendiente'){
        h+='<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">';
        h+='<input id="prov-cambiar-input" list="prov-dl-detail" placeholder="Asigna un proveedor..." style="flex:1;min-width:240px;padding:8px 12px;border:1px solid #fca5a5;border-radius:8px;font-size:13px;">';
        h+='<datalist id="prov-dl-detail">';
        PROVS.forEach(function(p){ h+='<option value="'+esc(p.nombre)+'">'; });
        h+='</datalist>';
        h+='<button onclick="guardarCambioProveedor(&quot;'+esc(oc.numero_oc)+'&quot;)" style="background:#dc2626;color:#fff;border:none;border-radius:8px;padding:8px 16px;font-size:12px;font-weight:700;cursor:pointer;">Asignar y guardar</button>';
        h+='</div>';
      } else {
        h+='<div style="font-size:13px;color:#7f1d1d;">Definir proveedor antes de avanzar la OC '+esc(oc.numero_oc)+'</div>';
      }
      h+='</div>';
    }

    // ── INFO COMPACTA (categoria, tipo, OC, fecha req) en 1 línea ────
    h+='<div style="display:flex;gap:24px;flex-wrap:wrap;font-size:12px;margin-bottom:18px;padding:8px 14px;background:#fafaf9;border-radius:6px;">';
    h+='<span><span style="color:#78716c;">Categoría:</span> <strong>'+esc(s.categoria||'-')+'</strong></span>';
    if(oc && oc.numero_oc) h+='<span><span style="color:#78716c;">OC:</span> <strong style="font-family:monospace;color:#0f766e;">'+esc(oc.numero_oc)+'</strong></span>';
    if(s.aprobado_por) h+='<span><span style="color:#78716c;">Gestionado por:</span> <strong>'+esc(s.aprobado_por)+'</strong></span>';
    if(s.fecha_requerida) h+='<span><span style="color:#78716c;">Fecha req:</span> <strong>'+esc(s.fecha_requerida)+'</strong></span>';
    h+='</div>';
    // ── Payment summary for non-pending solicitudes ──
    if(s.estado!=='Pendiente'&&s.observaciones&&s.observaciones.indexOf('BANCO:')>=0){
      var _obs=s.observaciones;
      function _xtr(key){
        var idx=_obs.indexOf(key+':');
        if(idx<0) return '';
        var rest=_obs.slice(idx+key.length+1).trim();
        var end=rest.indexOf(' | ');
        return end>=0?rest.slice(0,end).trim():rest.trim();
      }
      var _ben=_xtr('BENEFICIARIO')||_xtr('BENEFICIARIO');
      var _ban=_xtr('BANCO');
      var _cta=_xtr('CUENTA/CEL');
      var _ced=_xtr('CED/NIT');
      var _val=_xtr('VALOR');
      if(_ban||_cta){
        h+='<div style="margin-top:12px;background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:12px;">';
        h+='<div style="font-weight:800;font-size:12px;color:#166534;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">&#x1F4B3; Datos de Pago</div>';
        h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;font-size:12px;">';
        if(_ben) h+='<div style="grid-column:span 2;"><span style="color:#166534;font-weight:600;">Beneficiario:</span> <strong>'+esc(_ben)+'</strong></div>';
        if(_ban) h+='<div><span style="color:#166534;font-weight:600;">Banco:</span> <strong>'+esc(_ban)+'</strong></div>';
        if(_cta) h+='<div><span style="color:#166534;font-weight:600;">Cuenta/Cel:</span> <strong style="font-family:monospace;">'+esc(_cta)+'</strong></div>';
        if(_ced) h+='<div><span style="color:#166534;font-weight:600;">NIT/CC:</span> '+esc(_ced)+'</div>';
        if(_val) h+='<div><span style="color:#166534;font-weight:600;">Valor:</span> <strong>$'+esc(_val)+'</strong></div>';
        if(s.numero_oc) h+='<div style="grid-column:span 2;"><span style="color:#166534;font-weight:600;">OC:</span> <strong style="color:#2563eb;">'+esc(s.numero_oc)+'</strong></div>';
        h+='</div></div>';
      }
    }
    if(items.length){
      // Solo mostrar input de precio si la SOL está pendiente Y es categoría
      // tangible (MPs/MEE/Servicios). Influencers/CC tienen su propio flujo.
      var puedeEditarPrecios = (s.estado === 'Pendiente') &&
        ['Materia Prima','MP','MEE','Insumos','Servicio','SVC','Acondicionamiento'].indexOf(s.categoria||'') >= 0;
      h+='<div style="font-weight:800;font-size:11px;color:#1F5F5B;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px;">📦 Items solicitados ('+items.length+')'+(puedeEditarPrecios?' <span style="color:#0f766e;font-weight:600;text-transform:none;letter-spacing:0;">— editá los precios y guardá para alimentar el histórico</span>':'')+'</div>';
      h+='<div style="border:1px solid #e7e5e4;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.04);">';
      h+='<table id="sol-items-table" style="width:100%;border-collapse:collapse;font-size:13px;">';
      h+='<thead style="background:#1F5F5B;color:#fff;">';
      h+='<tr>';
      h+='<th style="text-align:left;padding:11px 14px;font-weight:700;font-size:11px;letter-spacing:.5px;width:11%;">CÓDIGO</th>';
      h+='<th style="text-align:left;padding:11px 14px;font-weight:700;font-size:11px;letter-spacing:.5px;width:'+(puedeEditarPrecios?'24':'32')+'%;">MATERIAL</th>';
      h+='<th style="text-align:left;padding:11px 14px;font-weight:700;font-size:11px;letter-spacing:.5px;width:14%;">PROVEEDOR</th>';
      h+='<th style="text-align:right;padding:11px 14px;font-weight:700;font-size:11px;letter-spacing:.5px;width:11%;">EN ESTANTERÍA</th>';
      h+='<th style="text-align:right;padding:11px 14px;font-weight:700;font-size:11px;letter-spacing:.5px;width:11%;">A PEDIR</th>';
      if(puedeEditarPrecios){
        h+='<th style="text-align:right;padding:11px 14px;font-weight:700;font-size:11px;letter-spacing:.5px;width:14%;">PRECIO UNIT (g)</th>';
      }
      h+='<th style="text-align:right;padding:11px 14px;font-weight:700;font-size:11px;letter-spacing:.5px;width:'+(puedeEditarPrecios?'19':'15')+'%;">VALOR EST.</th>';
      h+='</tr></thead><tbody>';
      // Formatea cantidades preservando decimales en péptidos (< 10g):
      // 0.4g → "0.4 g", 7g → "7 g", 1500g → "1.5 kg"
      // Antes Math.round() truncaba 0.4 → 0, ocultando las cantidades reales
      // de péptidos que cuestan caro pero se usan en pequeñas cantidades.
      function fmtCant(g, unidad){
        var n = parseFloat(g||0);
        if(unidad && unidad !== 'g') {
          // unidades distintas a g: 1 decimal si necesario
          var dec = (n % 1 === 0) ? 0 : 2;
          return n.toLocaleString('es-CO',{maximumFractionDigits:dec}) + ' ' + unidad;
        }
        // Normalizado: SIEMPRE gramos con separador de miles (acordado con Alejandro).
        if(n >= 10) return Math.round(n).toLocaleString('es-CO') + ' g';
        if(n >= 1) return n.toLocaleString('es-CO',{maximumFractionDigits:1}) + ' g';
        if(n > 0) return n.toLocaleString('es-CO',{maximumFractionDigits:2}) + ' g';
        return '0 g';
      }
      var totalValorEst = 0;
      var totalCantPedir = 0;
      var justificacionesUnicas = {};
      items.forEach(function(it, idx){
        var bg = (idx % 2 === 0) ? '#fff' : '#fafaf9';
        var stock = parseFloat(it.stock_actual_g||0);
        var pedir = parseFloat(it.cantidad_g||0);
        totalCantPedir += pedir;
        // Color y etiqueta de stock
        var stockColor, stockLbl;
        if(stock <= 0){
          stockColor='#dc2626'; stockLbl='⚠ Agotado';
        } else if(stock < pedir){
          stockColor='#d97706'; stockLbl=fmtCant(stock, it.unidad)+' (insuf.)';
        } else {
          stockColor='#16a34a'; stockLbl=fmtCant(stock, it.unidad);
        }
        var valor = parseFloat(it.valor_estimado||0) || parseFloat(it.valor_estimado_calculado||0) || 0;
        if(valor > 0) totalValorEst += valor;
        var valorHtml = valor > 0 ? '<strong style="color:#1F5F5B;">'+fmt(valor)+'</strong>'
                                  : '<span style="color:#a8a29e;font-size:11px;">—</span>';
        // Acumular justificaciones únicas (productos que necesitan estos MPs)
        if(it.justificacion){
          justificacionesUnicas[it.justificacion] = (justificacionesUnicas[it.justificacion]||0) + 1;
        }
        // precio unitario actual (si ya hay) para pre-poblar el input
        var precioActual = parseFloat(it.precio_unitario||0) || 0;
        var provActual = it.proveedor || '';
        var provHtml = provActual ? esc(provActual) : '<span style="color:#cbd5e1;font-style:italic;">— sin asignar —</span>';
        h+='<tr data-cod="'+esc(it.codigo_mp||'')+'" style="background:'+bg+';border-bottom:1px solid #f0edec;">';
        h+='<td style="padding:11px 14px;font-family:monospace;font-size:11px;color:#78716c;">'+esc(it.codigo_mp||'—')+'</td>';
        h+='<td style="padding:11px 14px;font-weight:600;color:#1c1917;">'+esc(it.nombre_mp||'—')+'</td>';
        h+='<td class="td-prov" data-cod="'+esc(it.codigo_mp||'')+'" data-nom="'+esc(it.nombre_mp||'')+'" data-prov="'+esc(provActual)+'" style="padding:11px 14px;font-size:12px;color:#475569;">'+provHtml+' <button class="btn-edit-prov-mp" title="Cambiar proveedor de esta MP" style="margin-left:4px;padding:2px 6px;font-size:11px;background:#e0f2fe;color:#0369a1;border:1px solid #bae6fd;border-radius:4px;cursor:pointer;">&#9999;&#65039;</button></td>';
        h+='<td style="padding:11px 14px;text-align:right;color:'+stockColor+';font-weight:700;">'+stockLbl+'</td>';
        h+='<td style="padding:11px 14px;text-align:right;font-weight:800;color:#1F5F5B;font-size:14px;">'+fmtCant(pedir, it.unidad)+'</td>';
        if(puedeEditarPrecios){
          // Input numérico inline. step 0.01 permite precios <$1/g (poco común
          // pero posible en commodities). placeholder con sugerencia si la
          // tabla precios_mp_historico devuelve uno (TODO en backend futuro).
          h+='<td style="padding:8px 10px;text-align:right;">';
          h+='<input class="precio-unit" type="number" min="0" step="0.01" value="'+(precioActual||'')+'" placeholder="$/g" style="width:100%;max-width:110px;text-align:right;padding:6px 8px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;font-family:monospace;">';
          h+='</td>';
        }
        h+='<td style="padding:11px 14px;text-align:right;">'+valorHtml+'</td>';
        h+='</tr>';
      });
      // Fila de total — colspan 3 para cubrir CÓDIGO + MATERIAL + PROVEEDOR
      var colspanTotal = 3;
      h+='<tr style="background:#f0fdfa;border-top:2px solid #1F5F5B;">';
      h+='<td colspan="'+colspanTotal+'" style="padding:12px 14px;font-weight:700;color:#0f766e;text-transform:uppercase;font-size:11px;letter-spacing:.5px;">📊 Total: '+items.length+' items</td>';
      h+='<td style="padding:12px 14px;text-align:right;color:#0f766e;font-size:11px;text-transform:uppercase;font-weight:700;">cantidad total</td>';
      h+='<td style="padding:12px 14px;text-align:right;font-weight:800;color:#1F5F5B;font-size:14px;">'+fmtCant(totalCantPedir,'g')+'</td>';
      if(puedeEditarPrecios){
        h+='<td style="padding:8px 10px;text-align:right;">';
        h+='<button id="btn-guardar-precios" onclick="guardarPreciosItems(&quot;'+esc((oc&&oc.numero_oc)||'')+'&quot;)" style="background:#0f766e;color:#fff;border:none;border-radius:8px;padding:7px 14px;font-size:11px;font-weight:700;cursor:pointer;width:100%;">💾 Guardar precios</button>';
        h+='</td>';
      }
      h+='<td style="padding:12px 14px;text-align:right;font-weight:800;color:#1F5F5B;font-size:14px;" id="sol-valor-total">'+(totalValorEst > 0 ? fmt(totalValorEst) : '—')+'</td>';
      h+='</tr>';
      h+='</tbody></table></div>';

      // ── BLOQUE OBSERVACIONES debajo del total ──────────────────────
      // Productos que necesitan estos MPs (deducidos de las justificaciones de cada item)
      var justifList = Object.keys(justificacionesUnicas);
      h+='<div style="margin-top:18px;background:#fffbeb;border:1px solid #fcd34d;border-radius:10px;padding:14px 18px;">';
      h+='<div style="font-size:11px;color:#92400e;font-weight:800;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px;">📝 Razón / Productos a fabricar</div>';
      if(justifList.length){
        h+='<ul style="margin:0;padding-left:20px;font-size:13px;color:#44403c;line-height:1.7;">';
        justifList.slice(0,10).forEach(function(j){
          h+='<li>'+esc(j)+'</li>';
        });
        if(justifList.length > 10) h+='<li style="color:#78716c;font-style:italic;">+'+(justifList.length-10)+' más...</li>';
        h+='</ul>';
      }
      // Observaciones libres del solicitante (si las hay y no son auto-generadas redundantes)
      var obs = (s.observaciones||'').trim();
      // Filtrar la línea auto-generada que ya está implícita arriba (proveedor + MPs listados)
      var obsLimpia = obs;
      if(obs.indexOf('Centro Programación') >= 0 || obs.indexOf('Centro Programacion') >= 0 || obs.indexOf('Planificación Estratégica') >= 0){
        // Es auto-generada — extraer solo la parte 'ACCIÓN:' si existe
        var ix = obs.indexOf('ACCIÓN:');
        if(ix >= 0){
          obsLimpia = obs.slice(ix);
        } else {
          obsLimpia = '';  // toda es redundante
        }
      }
      if(obsLimpia){
        h+='<div style="margin-top:10px;padding-top:10px;border-top:1px dashed #fcd34d;font-size:13px;color:#44403c;line-height:1.5;">';
        h+='<strong style="color:#92400e;font-size:11px;text-transform:uppercase;letter-spacing:.4px;">Comentario adicional:</strong> '+esc(obsLimpia);
        h+='</div>';
      }
      h+='</div>';
    }
    if(s.estado==='Pendiente'){
      // Bloque inferior reducido: solo textarea de motivo + hidden state.
      // El proveedor se confirma/cambia desde la card de arriba.
      // Los precios se editan inline en cada item de la tabla.
      // Esto elimina la duplicación que tenía el modal antes.
      h+='<div style="margin-top:16px;background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:14px;">';
      h+='<div class="fg" style="margin-bottom:0;"><label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:4px;">Motivo / Comentario (opcional)</label>';
      h+='<textarea id="sol-motivo" placeholder="Comentario al aprobar o motivo del rechazo..." rows="2" style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;resize:vertical;"></textarea></div>';
      // Hidden state — los pickers que ya no existen visualmente quedan
      // vacíos para que _solDetApr() use los defaults (proveedor de la OC,
      // valor calculado de items, sin fecha entrega).
      h+='<input type="hidden" id="sol-det-num" value="'+esc(s.numero||num)+'">';
      h+='<input type="hidden" id="sol-det-cat" value="'+esc(s.categoria||'MP')+'">';
      h+='<input type="hidden" id="sol-det-area" value="'+esc(s.area||'')+'">';
      h+='<input type="hidden" id="sol-prov-sel" value="">';
      h+='<input type="hidden" id="sol-tercero-txt" value="">';
      h+='<input type="hidden" id="sol-valor" value="0">';
      h+='<input type="hidden" id="sol-fent" value="">';
      h+='</div>';
    }
    h+='</div>';
    body.innerHTML=h;
    var fbtns='<button class="btn bo" onclick="_solDetClose()">Cerrar</button>';
    if(s.estado==='Pendiente'){
      fbtns+='<button class="btn" style="background:#dc2626;color:#fff;font-weight:700;" onclick="_solDetRech()">&#10005; Rechazar</button>';
      if(s.categoria==='Influencer/Marketing Digital'){
        fbtns+='<button class="btn bg" onclick="_solDetApr()" style="background:#7c3aed;">&#x1F4B8; Pagar directamente</button>';
      } else if(s.categoria==='Cuenta de Cobro'){
        fbtns+='<button class="btn bg" onclick="_solDetApr()" style="background:#d97706;">&#x1F4B3; Aprobar Cuenta de Cobro</button>';
      } else if(s.area==='Produccion'){
        fbtns+='<button class="btn bg" onclick="_solDetApr()" style="background:#16a34a;">&#x1F331; Aprobar &rarr; Planta</button>';
      } else {
        fbtns+='<button class="btn bg" onclick="_solDetApr()">&#9654; Enviar a Autorización</button>';
      }
    }
    footer.innerHTML=fbtns;
  }catch(e){ body.innerHTML='<p style="color:#dc2626;">Error: '+e.message+'</p>'; }
}
async function gestionarSol(decision){
  var num=document.getElementById('sol-det-num').value;
  // Bloque de campos viejos (selector + valor + fecha) ya no existe
  // visualmente pero los hidden quedan vacíos. El proveedor lo tomamos
  // de la card de arriba (donde se confirma/cambia). El valor de la OC
  // ya está calculado por items (no lo sobrescribimos). Esto reemplaza
  // el flujo viejo que duplicaba campos arriba/abajo.
  var _provSel=(document.getElementById('sol-prov-sel')||{value:''}).value;
  if(_provSel==='__nuevo__'){ alert('Primero guarda el nuevo proveedor antes de continuar.'); return; }
  var prov=_provSel==='__tercero__'
    ? ((document.getElementById('sol-tercero-txt')||{value:''}).value.trim()||'Pago a Terceros')
    : _provSel;
  // Fallback: si no hay selector activo, leer del card top (caso usual ahora)
  if (!prov) {
    var nameEl = document.getElementById('prov-card-name');
    if (nameEl) prov = (nameEl.textContent||'').trim();
  }
  var valor=parseFloat((document.getElementById('sol-valor')||{value:0}).value||0);
  var motivo=(document.getElementById('sol-motivo')||{value:''}).value.trim();
  var fent=(document.getElementById('sol-fent')||{value:''}).value;
  if(decision==='Rechazada'&&!motivo){
    if(!confirm('Rechazar sin motivo. Confirmar?')) return;
  }
  var _areaEl=document.getElementById('sol-det-area');
  var _esProduccion=(_areaEl&&_areaEl.value.trim()==='Produccion');
  var body={estado:decision,observaciones:motivo};
  if(decision==='Aprobada'){
    if(_esProduccion){ body.crear_oc=false; } else { body.crear_oc=true;
    body.proveedor=prov||'Por definir';
    if(valor>0) body.valor_total=valor;
    if(fent) body.fecha_entrega_est=fent;
    var catEl=document.getElementById('sol-det-cat');
    if(catEl) body.categoria=catEl.value;
    body.observaciones_oc=motivo||('Generado desde '+num);
    }
  }
  try{
    var r=await fetch('/api/solicitudes-compra/'+encodeURIComponent(num)+'/estado',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    closeModal('m-sol-det');
    await Promise.all([loadData(),loadSolicitudes(),loadInfluencers(),loadCCSolicitudes()]);
    alert(decision==='Aprobada'?'Solicitud aprobada. OC generada: '+(d.numero_oc||''):'Solicitud rechazada.');
  }catch(e){ alert('Error: '+e); }
}


// ─── Consolidado por Proveedor ────────────────────────────────────
var _consolCache = [];  // cache indexado por posición

async function loadConsolidado(){
  var body = document.getElementById('consol-body');
  body.innerHTML = '<div style="color:#94a3b8;text-align:center;padding:40px;">Cargando...</div>';
  var estados = Array.from(document.querySelectorAll('.consol-est:checked')).map(function(el){return el.value;});
  if(!estados.length){
    body.innerHTML = '<div style="color:#f59e0b;padding:16px;">Selecciona al menos un estado.</div>';
    return;
  }
  try{
    var qs = estados.map(function(e){return 'estados='+encodeURIComponent(e);}).join('&');
    var r = await fetch('/api/compras/consolidado-proveedor?'+qs);
    var d = await r.json();
    _consolCache = d.proveedores || [];
    if(!_consolCache.length){
      body.innerHTML = '<div style="color:#4ade80;text-align:center;padding:40px;">&#x2705; No hay OCs pendientes.</div>';
      return;
    }
    body.innerHTML = _consolCache.map(function(p, i){ return renderConsolCard(p, i); }).join('');
  }catch(e){
    body.innerHTML = '<div style="color:#f87171;padding:16px;">Error: '+e+'</div>';
  }
}

function renderConsolCard(p, idx){
  var estadoColors = {'Borrador':'#94a3b8','Revisada':'#f59e0b','Autorizada':'#22c55e'};

  // Contenido principal: ítems si los hay, OCs con observaciones si no
  var contenidoHtml;
  if(p.items && p.items.length > 0){
    var rows = p.items.map(function(it){
      var cant = Math.round(it.cantidad_total_g||0).toLocaleString('es-CO')+' g';
      var sub = it.subtotal_total > 0
        ? '$'+Number(it.subtotal_total).toLocaleString('es-CO',{maximumFractionDigits:0})
        : '—';
      var ocs = it.ocs_origen.length > 1 ? it.ocs_origen.join(', ') : (it.ocs_origen[0]||'');
      return '<tr>'
        +'<td style="padding:5px 8px;color:#1e293b;">'+escConH(it.nombre_mp)+'</td>'
        +'<td style="padding:5px 8px;font-weight:600;">'+cant+'</td>'
        +'<td style="padding:5px 8px;color:#64748b;">'+sub+'</td>'
        +'<td style="padding:5px 8px;font-size:11px;color:#94a3b8;">'+ocs+'</td>'
        +'</tr>';
    }).join('');
    contenidoHtml = '<table style="width:100%;border-collapse:collapse;">'
      +'<thead><tr>'
        +'<th style="text-align:left;font-size:11px;color:#94a3b8;padding:4px 8px;border-bottom:1px solid #f1f5f9;">Producto</th>'
        +'<th style="text-align:left;font-size:11px;color:#94a3b8;padding:4px 8px;border-bottom:1px solid #f1f5f9;">Cantidad total</th>'
        +'<th style="text-align:left;font-size:11px;color:#94a3b8;padding:4px 8px;border-bottom:1px solid #f1f5f9;">Subtotal</th>'
        +'<th style="text-align:left;font-size:11px;color:#94a3b8;padding:4px 8px;border-bottom:1px solid #f1f5f9;">OCs</th>'
      +'</tr></thead>'
      +'<tbody>'+rows+'</tbody>'
      +'</table>';
  } else {
    // Fallback: mostrar OCs con su descripción/observaciones
    var rows = p.ocs.map(function(o){
      var col = estadoColors[o.estado] || '#94a3b8';
      var desc = o.observaciones || o.categoria || '—';
      return '<tr>'
        +'<td style="padding:5px 8px;font-weight:600;color:#0f172a;">'+o.numero_oc+'</td>'
        +'<td style="padding:5px 8px;"><span style="color:'+col+';">'+o.estado+'</span></td>'
        +'<td style="padding:5px 8px;color:#475569;">'+escConH(desc)+'</td>'
        +'<td style="padding:5px 8px;color:#0f172a;">$'+Number(o.valor_total).toLocaleString('es-CO',{maximumFractionDigits:0})+'</td>'
        +'</tr>';
    }).join('');
    contenidoHtml = '<div style="font-size:11px;color:#94a3b8;margin-bottom:6px;">Esta OC no tiene ítems detallados. Se muestra el resumen por orden.</div>'
      +'<table style="width:100%;border-collapse:collapse;">'
        +'<thead><tr>'
          +'<th style="text-align:left;font-size:11px;color:#94a3b8;padding:4px 8px;border-bottom:1px solid #f1f5f9;">N° OC</th>'
          +'<th style="text-align:left;font-size:11px;color:#94a3b8;padding:4px 8px;border-bottom:1px solid #f1f5f9;">Estado</th>'
          +'<th style="text-align:left;font-size:11px;color:#94a3b8;padding:4px 8px;border-bottom:1px solid #f1f5f9;">Descripción / Concepto</th>'
          +'<th style="text-align:left;font-size:11px;color:#94a3b8;padding:4px 8px;border-bottom:1px solid #f1f5f9;">Valor</th>'
        +'</tr></thead>'
        +'<tbody>'+rows+'</tbody>'
      +'</table>';
  }

  var ocsHtml = p.ocs.map(function(o){
    var col = estadoColors[o.estado] || '#94a3b8';
    return '<span style="font-size:11px;background:#f1f5f9;border-radius:4px;padding:2px 8px;margin-right:4px;">'
      +o.numero_oc+' <span style="color:'+col+';">'+o.estado+'</span></span>';
  }).join('');

  var totalFmt = p.valor_total > 0 ? '$'+Number(p.valor_total).toLocaleString('es-CO',{maximumFractionDigits:0}) : '--';
  var metaLine = p.n_items > 0
    ? p.n_ocs+' OC'+(p.n_ocs>1?'s':'')+' &bull; '+p.n_items+' producto'+(p.n_items>1?'s':'')+' &bull; Total: <strong>'+totalFmt+'</strong>'
    : p.n_ocs+' OC'+(p.n_ocs>1?'s':'')+' &bull; Total: <strong>'+totalFmt+'</strong>';

  return '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;margin-bottom:16px;overflow:hidden;">'
    +'<div style="background:#f8fafc;padding:14px 18px;display:flex;align-items:flex-start;gap:12px;border-bottom:1px solid #e2e8f0;">'
      +'<span style="font-size:22px;margin-top:2px;">&#x1F3ED;</span>'
      +'<div style="flex:1;min-width:0;">'
        +'<div style="font-weight:700;font-size:16px;color:#0f172a;">'+escConH(p.proveedor)+'</div>'
        +'<div style="font-size:12px;color:#64748b;margin-top:2px;">'+metaLine+'</div>'
        +(p.nit||p.contacto||p.telefono
          ? '<div style="font-size:11px;color:#94a3b8;margin-top:3px;">'
            +(p.nit?'NIT: '+p.nit+' &nbsp;':'')
            +(p.contacto?'&#x1F464; '+escConH(p.contacto)+' &nbsp;':'')
            +(p.telefono?'&#x1F4DE; '+p.telefono:'')
            +'</div>'
          : '')
        +'<div style="margin-top:6px;">'+ocsHtml+'</div>'
      +'</div>'
      +'<div style="display:flex;gap:8px;flex-shrink:0;">'
        +'<button class="btn" data-consol-idx="'+idx+'" onclick="copiarPedido(parseInt(this.dataset.consolIdx))"'
          +' style="padding:8px 14px;font-size:12px;white-space:nowrap;background:#3b82f6;border-radius:8px;">&#x1F4CB; Copiar</button>'
        +'<button class="btn bp" data-print-idx="'+idx+'" onclick="imprimirPedido(parseInt(this.dataset.printIdx))"'
          +' style="padding:8px 14px;font-size:12px;white-space:nowrap;border-radius:8px;">&#x1F5A8; Imprimir</button>'
      +'</div>'
    +'</div>'
    +'<div style="padding:12px 18px;">'+contenidoHtml+'</div>'
  +'</div>';
}

async function copiarPedido(idx){
  var p = _consolCache[idx];
  if(!p){ alert('Error: proveedor no encontrado'); return; }
  var fecha = new Date().toLocaleDateString('es-CO',{day:'2-digit',month:'long',year:'numeric'});
  var lines = [];
  lines.push('SOLICITUD DE COMPRA — '+p.proveedor);
  if(p.nit) lines.push('NIT: '+p.nit);
  if(p.contacto) lines.push('Contacto: '+p.contacto);
  if(p.telefono) lines.push('Tel: '+p.telefono);
  lines.push('Fecha: '+fecha);
  lines.push('');
  if(p.items && p.items.length > 0){
    p.items.forEach(function(it){
      var cant = Math.round(it.cantidad_total_g||0).toLocaleString('es-CO')+' g';
      var sub = it.subtotal_total > 0
        ? '  ($'+Number(it.subtotal_total).toLocaleString('es-CO',{maximumFractionDigits:0})+')'
        : '';
      lines.push('- '+it.nombre_mp+': '+cant+sub);
    });
  } else {
    p.ocs.forEach(function(o){
      var desc = o.observaciones || o.categoria || '';
      lines.push('- '+o.numero_oc+' ('+o.estado+'): '+(desc?desc+' — ':'')+
        '$'+Number(o.valor_total).toLocaleString('es-CO',{maximumFractionDigits:0}));
    });
  }
  lines.push('');
  lines.push('Total: $'+Number(p.valor_total).toLocaleString('es-CO',{maximumFractionDigits:0}));
  lines.push('OCs: '+p.ocs.map(function(o){return o.numero_oc;}).join(', '));
  var texto = lines.join('\\n');
  try{
    await navigator.clipboard.writeText(texto);
    var btn = document.querySelector('[data-consol-idx="'+idx+'"]');
    if(btn){ var orig=btn.innerHTML; btn.innerHTML='&#x2705; Copiado!'; btn.style.background='#22c55e';
      setTimeout(function(){btn.innerHTML=orig;btn.style.background='#3b82f6';},2000); }
  }catch(e){
    var ta = document.createElement('textarea');
    ta.value = texto; document.body.appendChild(ta); ta.select();
    document.execCommand('copy'); document.body.removeChild(ta);
    alert('Copiado al portapapeles.');
  }
}

function imprimirPedido(idx){
  var p = _consolCache[idx];
  if(!p) return;
  var hoy = new Date();
  var fechaStr = hoy.toLocaleDateString('es-CO',{year:'numeric',month:'2-digit',day:'2-digit'});
  var numDoc = String(hoy.getFullYear()).slice(-2)
    +String(hoy.getMonth()+1).padStart(2,'0')
    +String(hoy.getDate()).padStart(2,'0')
    +'-'+(idx+1);

  // ── Calcular subtotal, IVA, total ──────────────────────────────────────
  var subtotal = 0;
  if(p.items && p.items.length > 0){
    p.items.forEach(function(it){ subtotal += it.subtotal_total || 0; });
  } else {
    p.ocs.forEach(function(o){ subtotal += o.valor_total || 0; });
  }
  if(subtotal === 0) subtotal = p.valor_total || 0;
  // IVA 19% si el total registrado sugiere que ya lo incluye, no lo sumamos doble
  // En el doc manual el IVA se muestra separado; aquí calculamos desde subtotal
  var iva = 0;  // Por defecto sin IVA; usuario puede editar al imprimir
  var total = subtotal + iva;
  var fmtCOP = function(n){ return '$'+Number(n||0).toLocaleString('es-CO',{minimumFractionDigits:0,maximumFractionDigits:0})+',00'; };

  // ── Filas de detalle ───────────────────────────────────────────────────
  var detalleRows = '';
  if(p.items && p.items.length > 0){
    p.items.forEach(function(it){
      var cant = Math.round(it.cantidad_total_g||0).toLocaleString('es-CO')+' g';
      detalleRows += '<tr>'
        +'<td>'+escConH(it.codigo_mp||'')+'</td>'
        +'<td>'+escConH(it.nombre_mp)+'</td>'
        +'<td class="c">'+cant+'</td>'
        +'<td class="r">'+(it.precio_unitario>0?fmtCOP(it.precio_unitario):'$0,00')+'</td>'
        +'<td class="r">'+(it.subtotal_total>0?fmtCOP(it.subtotal_total):'$0,00')+'</td>'
        +'</tr>';
    });
  } else {
    p.ocs.forEach(function(o){
      var desc = o.observaciones || o.categoria || '';
      detalleRows += '<tr>'
        +'<td></td>'
        +'<td>'+escConH(desc||o.numero_oc)+'</td>'
        +'<td class="c">1</td>'
        +'<td class="r">'+fmtCOP(o.valor_total)+'</td>'
        +'<td class="r">'+fmtCOP(o.valor_total)+'</td>'
        +'</tr>';
    });
  }
  // Filas vacías para completar mínimo 6 filas (como en el doc manual)
  var filledRows = p.items.length || p.ocs.length;
  for(var z=filledRows; z<6; z++){
    detalleRows += '<tr><td></td><td></td><td></td><td class="r">$0,00</td><td class="r">$0,00</td></tr>';
  }

  // ── Datos de pago del proveedor ────────────────────────────────────────
  var infoPago = p.banco && p.num_cuenta
    ? p.banco+'   '+escConH(p.proveedor)+'   '+p.num_cuenta+'   '+(p.tipo_cuenta||'')
    : '';

  // ── Observaciones consolidadas ─────────────────────────────────────────
  var justLines = [];
  p.ocs.forEach(function(o){ if(o.observaciones) justLines.push(o.numero_oc+': '+o.observaciones); });
  var justif = justLines.join(' | ') || p.ocs.map(function(o){return o.numero_oc;}).join(', ');

  var html = `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Orden de Compra ${numDoc}</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:Arial,sans-serif;font-size:11px;color:#000;background:#fff;}
.page{width:900px;margin:0 auto;padding:24px 28px;}
/* Encabezado empresa */
.hdr-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;}
.oc-title{font-size:22px;font-weight:900;color:#1a1a1a;letter-spacing:0.5px;text-transform:uppercase;}
.oc-lote{font-size:28px;font-weight:900;color:#1a6bbf;letter-spacing:1px;}
/* Tabla principal de estructura */
table.main{width:100%;border-collapse:collapse;}
table.main td, table.main th{border:1px solid #bbb;padding:4px 7px;vertical-align:middle;}
.label-cell{font-weight:700;text-align:right;background:#f0f0f0;width:140px;font-size:10px;}
.blue{color:#1a6bbf;font-weight:700;}
.hdr-company{font-size:12px;font-weight:700;color:#1a6bbf;}
.section-title{background:#1a1a1a;color:#fff;font-weight:700;font-size:11px;padding:5px 8px;text-align:center;letter-spacing:1px;}
/* Tabla de ítems */
table.items{width:100%;border-collapse:collapse;margin:0;}
table.items th{background:#3a3a3a;color:#fff;padding:5px 7px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;}
table.items td{border:1px solid #ccc;padding:4px 7px;font-size:11px;}
table.items td.c{text-align:center;}
table.items td.r{text-align:right;}
/* Totales */
.tot-label{font-weight:700;text-align:right;padding:4px 8px;border:1px solid #ccc;background:#f5f5f5;}
.tot-val{font-weight:700;text-align:right;padding:4px 10px;border:1px solid #ccc;}
.tot-bold{font-size:13px;font-weight:900;background:#1a1a1a;color:#fff;}
/* Info pago */
.info-row td{background:#e8f0fb;font-size:10px;padding:4px 7px;border:1px solid #bbb;}
/* Firma */
.firma-row td{padding:6px 8px;border:1px solid #ccc;font-size:10px;font-weight:700;}
.firma-val{height:28px;}
/* Botones */
.no-print{text-align:right;margin-bottom:16px;}
.no-print button{padding:9px 22px;border:none;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer;}
.btn-print{background:#1a6bbf;color:#fff;margin-right:8px;}
.btn-close{background:#e2e8f0;color:#333;}
@media print{
  .no-print{display:none!important;}
  .page{padding:12px 16px;width:100%;}
  @page{size:A4;margin:12mm 8mm;}
}
</style>
</head>
<body>
<div class="page">

<div class="no-print">
  <button class="btn-print" onclick="window.print()">&#x1F5A8; Imprimir / Guardar PDF</button>
  <button class="btn-close" onclick="window.close()">Cerrar</button>
</div>

<!-- TÍTULO -->
<table class="main" style="margin-bottom:2px;">
  <tr>
    <td colspan="2" style="border:none;padding-bottom:4px;vertical-align:middle;">
      <img src="data:image/png;base64,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" alt="HHA Group" style="height:72px;width:auto;display:block;margin-bottom:6px;">
    </td>
    <td style="text-align:right;border:none;vertical-align:middle;">
      <div class="oc-title">ORDEN DE COMPRA</div>
      <div class="oc-lomdte" style="font-size:20px;font-weight:900;color:#2d7a74;">${numDoc}</div>
      <div style="font-size:10px;color:#64748b;margin-top:4px;">Generado por Sistema HHA &bull; ${fechaStr}</div>
    </td>
  </tr>
</table>

<!-- DATOS ESPAGIRIA + FECHAS -->
<table class="main" style="margin-bottom:2px;">
  <tr>
    <td colspan="4" class="hdr-company">ESPAGIRIA LABORATORIO S.A.S</td>
    <td colspan="2" class="blue" style="text-align:center;background:#e8f0fb;">FECHA</td>
  </tr>
  <tr>
    <td class="label-cell">NIT:</td>
    <td colspan="3">901.622.676-6</td>
    <td colspan="2" style="text-align:center;">${fechaStr}</td>
  </tr>
  <tr>
    <td class="label-cell">DIRECCIÓN:</td>
    <td colspan="3">CARRERA 1 #32-46  SAN FRANCISCO, Cali</td>
    <td class="blue" style="text-align:center;background:#e8f0fb;">NÚMERO DE ORDEN</td>
    <td style="text-align:center;font-weight:700;">${numDoc}</td>
  </tr>
  <tr>
    <td class="label-cell">TELÉFONO:</td>
    <td colspan="3">3235180113</td>
    <td class="blue" style="text-align:center;background:#e8f0fb;"># PROVEEDOR</td>
    <td style="text-align:center;">${escConH(p.nit||'—')}</td>
  </tr>
  <tr>
    <td class="label-cell">EMAIL:</td>
    <td colspan="3">catalina.erazoa.el@gmail.com</td>
    <td colspan="2"></td>
  </tr>
</table>

<!-- DATOS PROVEEDOR + SOLICITADO POR -->
<table class="main" style="margin-bottom:2px;">
  <tr>
    <td colspan="4" class="hdr-company">${escConH(p.proveedor)}</td>
    <td colspan="2" class="blue" style="text-align:center;background:#e8f0fb;">SOLICITADO POR:</td>
  </tr>
  <tr>
    <td class="label-cell">DIRECCIÓN</td>
    <td colspan="3">&nbsp;</td>
    <td colspan="2"></td>
  </tr>
  <tr>
    <td class="label-cell">CORREO</td>
    <td colspan="3">${escConH(p.email||'')}</td>
    <td class="blue" style="text-align:center;background:#e8f0fb;">FECHA LÍMITE PAGO</td>
    <td></td>
  </tr>
  <tr>
    <td class="label-cell">CONTACTO VENTAS</td>
    <td colspan="3">${escConH(p.contacto||'')}</td>
    <td colspan="2"></td>
  </tr>
  <tr>
    <td class="label-cell">TELÉFONO</td>
    <td colspan="3">${escConH(p.telefono||'')}</td>
    <td colspan="2"></td>
  </tr>
</table>

<!-- TABLA ÍTEMS -->
<table class="items" style="margin-bottom:0;">
  <thead>
    <tr>
      <th style="width:90px;">CÓDIGO</th>
      <th>DESCRIPCIÓN</th>
      <th style="width:90px;">CANTIDAD</th>
      <th style="width:120px;">PRECIO UNITARIO</th>
      <th style="width:120px;">TOTAL</th>
    </tr>
  </thead>
  <tbody>
    ${detalleRows}
  </tbody>
</table>

<!-- JUSTIFICACIÓN + TOTALES -->
<table class="main" style="margin-top:0;">
  <tr>
    <td rowspan="4" colspan="3" style="vertical-align:top;width:55%;">
      <div style="font-weight:700;font-size:10px;margin-bottom:4px;">JUSTIFICACIÓN:</div>
      <div style="font-size:11px;">${escConH(justif)}</div>
    </td>
    <td class="tot-label">SUBTOTAL</td>
    <td class="tot-val">${fmtCOP(subtotal)}</td>
  </tr>
  <tr>
    <td class="tot-label">IVA</td>
    <td class="tot-val" id="iva-val">${fmtCOP(iva)}</td>
  </tr>
  <tr>
    <td class="tot-label">SALDO A FAVOR</td>
    <td class="tot-val">$0,00</td>
  </tr>
  <tr>
    <td class="tot-label tot-bold">TOTAL</td>
    <td class="tot-val tot-bold" id="total-val">${fmtCOP(total)}</td>
  </tr>
</table>

<!-- INFORMACIÓN DE PAGO -->
<table class="main" style="margin-top:2px;">
  <tr>
    <td class="label-cell blue" style="background:#d0e4fa;width:140px;">INFORMACIÓN DE PAGO</td>
    <td colspan="4" style="font-size:11px;">${infoPago}</td>
  </tr>
  <tr>
    <td class="label-cell blue" style="background:#d0e4fa;">CONDICIONES DE ENTREGA</td>
    <td colspan="4"></td>
  </tr>
  <tr>
    <td class="label-cell blue" style="background:#d0e4fa;">TIEMPO DE LLEGADA DESPUÉS PAGO</td>
    <td colspan="4"></td>
  </tr>
</table>

<!-- FIRMAS -->
<table class="main" style="margin-top:8px;">
  <tr>
    <td class="firma-row" style="width:25%;">REVISADO POR DT:</td>
    <td class="firma-row firma-val" style="width:25%;"></td>
    <td class="firma-row" style="width:25%;">REVISADO POR C:</td>
    <td class="firma-row firma-val" style="width:25%;"></td>
  </tr>
  <tr>
    <td class="firma-row">FECHA</td>
    <td class="firma-row firma-val"></td>
    <td class="firma-row">FECHA</td>
    <td class="firma-row firma-val"></td>
  </tr>
</table>

<!-- IVA selector (no se imprime) -->
<div class="no-print" style="margin-top:16px;padding:12px;background:#f0f4ff;border-radius:8px;display:flex;align-items:center;gap:16px;">
  <span style="font-weight:700;font-size:13px;">&#9432; Ajustar IVA:</span>
  <label><input type="radio" name="iva_opt" value="0" checked onchange="recalcIVA(this.value,${subtotal})"> Sin IVA</label>
  <label><input type="radio" name="iva_opt" value="0.19" onchange="recalcIVA(this.value,${subtotal})"> 19%</label>
  <label><input type="radio" name="iva_opt" value="0.05" onchange="recalcIVA(this.value,${subtotal})"> 5%</label>
  <label style="display:flex;align-items:center;gap:4px;">
    Otro %: <input type="number" id="iva-custom" min="0" max="100" step="1" style="width:56px;border:1px solid #ccc;border-radius:4px;padding:3px 6px;"
      oninput="recalcIVA(document.getElementById('iva-custom').value/100,${subtotal})">
  </label>
  <span style="font-size:11px;color:#64748b;">Ajusta y luego imprime</span>
</div>

</div>
<script>
function recalcIVA(rate,sub){
  var r = parseFloat(rate)||0;
  var iva = Math.round(sub*r);
  var tot = sub+iva;
  var fmt = function(n){ return '$'+Number(n).toLocaleString('es-CO',{minimumFractionDigits:0,maximumFractionDigits:0})+',00'; };
  var iv = document.getElementById('iva-val');
  var tv = document.getElementById('total-val');
  if(iv) iv.textContent = fmt(iva);
  if(tv) tv.textContent = fmt(tot);
}
<\\/script>
</body>
</html>`;

  var win = window.open('', '_blank', 'width=980,height=860');
  if(!win){ alert('Permite las ventanas emergentes para este sitio e intenta de nuevo.'); return; }
  win.document.write(html);
  win.document.close();
}


function escConH(s){
  var d = document.createElement('div');
  d.appendChild(document.createTextNode(s||''));
  return d.innerHTML;
}


async function eliminarSolicitud(num){
  if(!confirm('Eliminar solicitud '+num+'?')) return;
  try{
    var r=await fetch('/api/solicitudes-compra/'+encodeURIComponent(num),{method:'DELETE'});
    var d=await r.json();
    if(d.ok){
      // Remove card from DOM immediately for snappy UX
      var card=document.querySelector('[data-sol="'+num+'"]');
      if(card){var parent=card.closest('.card');if(parent)parent.remove();}
      // Reload all relevant data
      if(typeof loadSolicitudes==='function') loadSolicitudes();
      if(typeof loadCCSolicitudes==='function') loadCCSolicitudes();
      if(typeof loadMarketing==='function') loadMarketing();
      else if(typeof renderMarketing==='function') renderMarketing();
    } else {
      alert('No se pudo eliminar: '+(d.error||'error desconocido'));
    }
  }catch(e){alert('Error: '+e.message);}
}

// ════════════════════════════════════════════════════════════════════════
// Tab "Por Pagar" — vista unificada de pendientes de pago
// ════════════════════════════════════════════════════════════════════════

function _esc(s){return String(s||'').replace(/[<>&"']/g,function(c){return {'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c];});}
function _money(n){return '$'+Number(n||0).toLocaleString('es-CO');}

// Abre el modal de pago con info de la OC + historial de pagos previos.
async function payOC(numero_oc){
  // Reset modal
  document.getElementById('pago-num').value = numero_oc;
  document.getElementById('pago-monto').value = '';
  document.getElementById('pago-medio').value = 'Transferencia';
  document.getElementById('pago-obs').value = '';
  document.getElementById('pago-factura').value = '';
  document.getElementById('pago-img-file').value = '';
  document.getElementById('pago-img-preview').style.display = 'none';

  // Cargar info de la OC + historial de pagos
  try{
    var r = await fetch('/api/ordenes-compra/'+encodeURIComponent(numero_oc)+'/pagos');
    if(r.ok){
      var d = await r.json();
      var info = document.getElementById('pago-info');
      if(info){
        info.innerHTML = '<div><strong>'+_esc(numero_oc)+'</strong> · valor total '+_money(d.valor_total_oc)+
          ' · pagado '+_money(d.total_pagado)+' · pendiente <strong style="color:#dc2626;">'+_money(d.pendiente)+'</strong></div>';
      }
      // Pre-llenar con el monto pendiente
      if(d.pendiente > 0) document.getElementById('pago-monto').value = d.pendiente;

      // Historial de pagos previos (pagos parciales)
      var hist = document.getElementById('pago-historial');
      var histList = document.getElementById('pago-historial-list');
      if((d.pagos||[]).length){
        hist.style.display = 'block';
        histList.innerHTML = d.pagos.map(function(p){
          return '<div style="padding:4px 0;border-bottom:1px solid #e5e7eb;">'+
            (p.fecha_pago||'').replace('T',' ').slice(0,16)+' · '+_money(p.monto)+' · '+_esc(p.medio)+
            (p.numero_factura_proveedor ? ' · fac '+_esc(p.numero_factura_proveedor) : '')+
            ' · <em>'+_esc(p.registrado_por||'?')+'</em></div>';
        }).join('');
      } else {
        hist.style.display = 'none';
      }
    }
  }catch(e){}

  openModal('m-pago');
}

async function loadPorPagar(){
  try{
    var r = await fetch('/api/compras/por-pagar');
    if(!r.ok){ document.getElementById('por-pagar-merc-list').innerHTML='<div style="color:#dc2626;padding:20px;">Error '+r.status+'</div>'; return; }
    var d = await r.json();
    var desg = d.desglose || {};
    document.getElementById('por-pagar-total').textContent = _money(d.total_valor);
    document.getElementById('por-pagar-merc').textContent = _money((desg.mercancia_recibida||{}).valor) + ' · ' + ((desg.mercancia_recibida||{}).count||0)+' OCs';
    document.getElementById('por-pagar-svc').textContent = _money((desg.pagos_directos_servicios||{}).valor) + ' · ' + ((desg.pagos_directos_servicios||{}).count||0)+' OCs';

    var directos = (d.items||[]).filter(function(x){return x.pago_directo===true;});
    var fisicas = (d.items||[]).filter(function(x){return !x.pago_directo;});

    // Sección destacada de pagos directos
    var dirWrap = document.getElementById('por-pagar-directos-wrap');
    var dirEl = document.getElementById('por-pagar-directos');
    if(directos.length){
      dirWrap.style.display = 'block';
      dirEl.innerHTML = directos.map(function(o){
        return '<div style="background:#fffbeb;border:2px solid #f59e0b;border-radius:10px;padding:12px;">'+
          '<div style="font-weight:700;font-family:monospace;color:#92400e;font-size:13px;">'+_esc(o.numero_oc)+'</div>'+
          '<div style="font-size:13px;color:#1e293b;margin-top:4px;">'+_esc(o.proveedor||'(sin proveedor)')+'</div>'+
          '<div style="font-size:11px;color:#78350f;margin-top:2px;">'+_esc(o.categoria||'')+'</div>'+
          '<div style="font-size:18px;font-weight:800;color:#059669;margin-top:8px;">'+_money(o.valor_total)+'</div>'+
          '<button class="btn bs" style="margin-top:8px;padding:6px 14px;font-size:12px;background:#059669;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:700;" onclick="payOC(\\''+_esc(o.numero_oc)+'\\')">&#x1F4B5; Pagar ahora</button>'+
        '</div>';
      }).join('');
    } else {
      dirWrap.style.display = 'none';
    }

    // Mercancía física
    var mercEl = document.getElementById('por-pagar-merc-list');
    if(!fisicas.length){
      mercEl.innerHTML = '<div style="color:#94a3b8;padding:20px;text-align:center;">Sin mercanc&iacute;a recibida pendiente de pago.</div>';
    } else {
      mercEl.innerHTML = fisicas.map(function(o){
        var estCol = o.estado==='Parcial' ? '#d97706' : '#16a34a';
        return '<div style="background:#fff;border:1px solid #d1d5db;border-radius:10px;padding:12px;">'+
          '<div style="display:flex;justify-content:space-between;align-items:center;">'+
            '<div style="font-weight:700;font-family:monospace;font-size:13px;">'+_esc(o.numero_oc)+'</div>'+
            '<span style="background:'+estCol+';color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;">'+_esc(o.estado)+'</span>'+
          '</div>'+
          '<div style="font-size:13px;color:#1e293b;margin-top:4px;">'+_esc(o.proveedor||'(sin proveedor)')+'</div>'+
          '<div style="font-size:11px;color:#64748b;margin-top:2px;">'+_esc(o.categoria||'')+'</div>'+
          '<div style="font-size:18px;font-weight:800;color:#1e293b;margin-top:8px;">'+_money(o.valor_total)+'</div>'+
          '<button class="btn bs" style="margin-top:8px;padding:6px 14px;font-size:12px;background:#3b82f6;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:700;" onclick="payOC(\\''+_esc(o.numero_oc)+'\\')">&#x1F4B5; Pagar</button>'+
        '</div>';
      }).join('');
    }
  }catch(e){
    document.getElementById('por-pagar-merc-list').innerHTML = '<div style="color:#dc2626;padding:20px;">Error: '+_esc(e.message)+'</div>';
  }
}

// ════════════════════════════════════════════════════════════════════════
// Tab "Alertas" — 4 categorías de alertas vivas
// ════════════════════════════════════════════════════════════════════════

async function loadAlertasCompras(){
  try{
    var r = await fetch('/api/compras/alertas-vivas');
    if(!r.ok){ return; }
    var d = await r.json();

    // Severidad pill
    var sevPill = document.getElementById('alertas-sev-pill');
    var sev = d.severidad_max || 'ok';
    var sevColors = {critico:'#dc2626',alto:'#f59e0b',medio:'#3b82f6',bajo:'#71717a',ok:'#16a34a'};
    sevPill.style.background = sevColors[sev] || '#71717a';
    sevPill.style.color = '#fff';
    sevPill.textContent = sev==='ok' ? 'Sin alertas' : 'Severidad max: '+sev;

    // 1. OCs sin recibir
    var sr = d.ocs_sin_recibir || [];
    document.getElementById('alertas-sin-recibir-count').textContent = sr.length;
    document.getElementById('alertas-sin-recibir').innerHTML = sr.length === 0
      ? '<div style="color:#94a3b8;text-align:center;padding:14px;">Sin alertas</div>'
      : sr.map(function(o){
          return '<div style="border-bottom:1px solid #f1f5f9;padding:8px 0;">'+
            '<div style="display:flex;justify-content:space-between;"><strong style="font-family:monospace;font-size:11px;">'+_esc(o.numero_oc)+'</strong>'+
            '<span style="font-size:10px;color:#92400e;font-weight:700;">'+(o.dias_sin_recibir||'?')+' d</span></div>'+
            '<div style="font-size:11px;color:#64748b;">'+_esc(o.proveedor)+' · '+_money(o.valor_total)+'</div>'+
          '</div>';
        }).join('');

    // 2. Pagos por vencer
    var pv = d.pagos_por_vencer || [];
    document.getElementById('alertas-pagos-vencer-count').textContent = pv.length;
    document.getElementById('alertas-pagos-vencer').innerHTML = pv.length === 0
      ? '<div style="color:#94a3b8;text-align:center;padding:14px;">Sin alertas</div>'
      : pv.map(function(o){
          var dias = o.dias_restantes;
          var diasTxt = dias === null ? '?' : (dias < 0 ? Math.abs(dias)+' d en mora' : dias+' d restantes');
          var col = dias < 0 ? '#dc2626' : (dias <= 3 ? '#f59e0b' : '#3b82f6');
          return '<div style="border-bottom:1px solid #f1f5f9;padding:8px 0;">'+
            '<div style="display:flex;justify-content:space-between;"><strong style="font-family:monospace;font-size:11px;">'+_esc(o.numero_oc)+'</strong>'+
            '<span style="font-size:10px;color:'+col+';font-weight:700;">'+diasTxt+'</span></div>'+
            '<div style="font-size:11px;color:#64748b;">'+_esc(o.proveedor)+' · pendiente '+_money(o.pendiente)+'</div>'+
          '</div>';
        }).join('');

    // 3. Solicitudes pendientes
    var sp = d.solicitudes_pendientes || [];
    document.getElementById('alertas-solic-count').textContent = sp.length;
    document.getElementById('alertas-solic').innerHTML = sp.length === 0
      ? '<div style="color:#94a3b8;text-align:center;padding:14px;">Sin alertas</div>'
      : sp.map(function(s){
          var col = s.urgencia === 'Urgente' ? '#dc2626' : '#3b82f6';
          return '<div style="border-bottom:1px solid #f1f5f9;padding:8px 0;">'+
            '<div style="display:flex;justify-content:space-between;"><strong style="font-family:monospace;font-size:11px;">'+_esc(s.numero)+'</strong>'+
            '<span style="font-size:10px;color:'+col+';font-weight:700;">'+_esc(s.urgencia||'Normal')+'</span></div>'+
            '<div style="font-size:11px;color:#64748b;">'+_esc(s.solicitante||'')+' · '+(s.dias_pendiente||'?')+' d · '+_esc(s.area||'')+'</div>'+
          '</div>';
        }).join('');

    // 4. Borradores estancados
    var bb = d.ocs_borrador_estancadas || [];
    document.getElementById('alertas-borrador-count').textContent = bb.length;
    document.getElementById('alertas-borrador').innerHTML = bb.length === 0
      ? '<div style="color:#94a3b8;text-align:center;padding:14px;">Sin alertas</div>'
      : bb.map(function(o){
          return '<div style="border-bottom:1px solid #f1f5f9;padding:8px 0;">'+
            '<div style="display:flex;justify-content:space-between;"><strong style="font-family:monospace;font-size:11px;">'+_esc(o.numero_oc)+'</strong>'+
            '<span style="font-size:10px;color:#71717a;font-weight:700;">'+_esc(o.creado_por||'?')+'</span></div>'+
            '<div style="font-size:11px;color:#64748b;">'+_esc(o.proveedor)+' · '+_money(o.valor_total)+'</div>'+
          '</div>';
        }).join('');
  }catch(e){ console.error(e); }
}

// Stub no-op: el tab Cuentas de Cobro fue absorbido por Solicitudes en el
// refactor del Centro de Mando, pero quedaron 2 callsites sin protección
// (líneas init + post-decisión). El ReferenceError tiraba TODO el init
// async — todos los handlers quedaban sin engancharse. Stub idempotente
// = compras vuelve a la vida.
async function loadCCSolicitudes(){ /* no-op: tab absorbido en Solicitudes */ }

// ─── Init ─────────────────────────────────────────────────────────────
loadData();
</script>
</body>
</html>"""
