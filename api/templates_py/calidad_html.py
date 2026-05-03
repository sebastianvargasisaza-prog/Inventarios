# calidad_html.py Ã¢ÂÂ extraÃÂ­do de index.py (Fase C prep)
CALIDAD_HTML = r"""<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Calidad BPM Ã¢ÂÂ Espagiria</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos12">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#0f172a;color:#e2e8f0;font-size:14px;min-height:100vh;}
.topbar{background:#1e293b;border-bottom:1px solid #334155;padding:12px 24px;display:flex;align-items:center;gap:16px;}
.logo{font-size:0.85em;font-weight:900;letter-spacing:3px;color:#fff;}
.badge{background:rgba(43,122,120,0.4);color:#7ACFCC;padding:3px 12px;border-radius:20px;font-size:0.7em;font-weight:700;letter-spacing:1px;}
.topbar a{color:rgba(255,255,255,0.45);text-decoration:none;font-size:0.78em;padding:5px 12px;border:1px solid rgba(255,255,255,0.12);border-radius:6px;margin-left:auto;}
.topbar a:hover{color:#fff;border-color:rgba(255,255,255,0.35);}
.tabs{display:flex;gap:0;background:#1e293b;border-bottom:1px solid #334155;padding:0 24px;}
.tab{padding:11px 20px;font-size:0.78em;font-weight:700;letter-spacing:.5px;color:#64748b;cursor:pointer;border-bottom:2px solid transparent;text-transform:uppercase;}
.tab.active{color:#7ACFCC;border-bottom-color:#7ACFCC;}
.tab:hover{color:#cbd5e1;}
.main{padding:24px;max-width:1300px;margin:0 auto;}
.kpi-row{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:24px;}
.kpi{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px 20px;flex:1;min-width:140px;}
.kpi-label{font-size:0.68em;text-transform:uppercase;letter-spacing:1.5px;color:#64748b;margin-bottom:6px;}
.kpi-val{font-size:2em;font-weight:800;color:#f1f5f9;}
.kpi-val.warn{color:#fb923c;}
.kpi-val.crit{color:#f87171;}
.kpi-val.good{color:#4ade80;}
.kpi-sub{font-size:0.7em;color:#475569;margin-top:3px;}
.card{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:18px;margin-bottom:16px;}
.card-title{font-size:0.7em;text-transform:uppercase;letter-spacing:1.5px;color:#64748b;margin-bottom:14px;font-weight:700;}
table{width:100%;border-collapse:collapse;}
th{font-size:0.67em;text-transform:uppercase;letter-spacing:.8px;color:#475569;padding:8px 10px;text-align:left;border-bottom:1px solid #334155;}
td{padding:9px 10px;font-size:0.82em;border-bottom:1px solid #1e293b;color:#cbd5e1;vertical-align:top;}
tr:hover td{background:#0f172a;}
.badge-verde{background:#052e16;color:#4ade80;padding:2px 10px;border-radius:20px;font-size:0.72em;font-weight:700;}
.badge-amarillo{background:#451a03;color:#fcd34d;padding:2px 10px;border-radius:20px;font-size:0.72em;font-weight:700;}
.badge-rojo{background:#450a0a;color:#fca5a5;padding:2px 10px;border-radius:20px;font-size:0.72em;font-weight:700;}
.badge-gris{background:#1e293b;color:#94a3b8;padding:2px 10px;border-radius:20px;font-size:0.72em;font-weight:700;border:1px solid #334155;}
.btn{padding:7px 16px;border-radius:7px;border:none;font-size:0.78em;font-weight:700;cursor:pointer;letter-spacing:.3px;}
.btn-primary{background:#2B7A78;color:#fff;}
.btn-primary:hover{background:#1e5c5a;}
.btn-danger{background:#7f1d1d;color:#fca5a5;}
.btn-danger:hover{background:#991b1b;}
.btn-sm{padding:4px 10px;font-size:0.72em;}
.form-row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px;align-items:flex-end;}
.form-group{display:flex;flex-direction:column;gap:4px;flex:1;min-width:160px;}
label{font-size:0.7em;text-transform:uppercase;letter-spacing:.8px;color:#64748b;font-weight:700;}
input,select,textarea{background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:7px 10px;border-radius:7px;font-size:0.82em;width:100%;}
input:focus,select:focus,textarea:focus{outline:none;border-color:#7ACFCC;}
textarea{resize:vertical;min-height:70px;}
.pane{display:none;} .pane.active{display:block;}
.empty{color:#475569;text-align:center;padding:32px;font-size:0.85em;}
.actividad{display:flex;flex-direction:column;gap:8px;}
.act-item{background:#0f172a;border-radius:8px;padding:10px 14px;border:1px solid #1e293b;display:flex;align-items:flex-start;gap:10px;}
.act-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;margin-top:4px;}
.dot-verde{background:#4ade80;} .dot-rojo{background:#f87171;} .dot-amari{background:#fcd34d;}
.act-body{flex:1;}
.act-title{font-size:0.78em;font-weight:700;color:#e2e8f0;}
.act-sub{font-size:0.68em;color:#64748b;margin-top:1px;}
.alert-box{background:#450a0a;border:1px solid #7f1d1d;border-radius:8px;padding:10px 14px;margin-bottom:12px;color:#fca5a5;font-size:0.8em;}
.badge-azul{background:#172554;color:#93c5fd;padding:2px 10px;border-radius:20px;font-size:0.72em;font-weight:700;}
.btn-ghost{background:transparent;border:1px solid #334155;color:#94a3b8;}
.btn-ghost:hover{border-color:#7ACFCC;color:#7ACFCC;}
.cron-topbar{display:flex;align-items:center;gap:12px;margin-bottom:20px;flex-wrap:wrap;}
.cron-topbar input[type=date]{width:auto;flex:none;}
.cron-summary{display:flex;gap:16px;flex:1;flex-wrap:wrap;}
.cron-stat{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:8px 16px;font-size:0.78em;color:#94a3b8;display:flex;gap:6px;align-items:center;}
.cron-stat strong{color:#e2e8f0;font-size:1.2em;}
.cron-section{margin-bottom:20px;}
.cron-section-hdr{display:flex;align-items:center;gap:10px;padding:10px 14px;background:#1e293b;border:1px solid #334155;border-radius:8px 8px 0 0;cursor:pointer;user-select:none;}
.cron-section-hdr:hover{background:#243147;}
.cron-cat-name{font-size:0.72em;font-weight:900;letter-spacing:1.5px;text-transform:uppercase;color:#94a3b8;}
.cron-cat-prog{font-size:0.7em;color:#64748b;margin-left:auto;}
.cron-chevron{color:#475569;font-size:0.8em;transition:transform 0.2s;}
.cron-chevron.open{transform:rotate(180deg);}
.cron-rows{border:1px solid #334155;border-top:none;border-radius:0 0 8px 8px;overflow:hidden;}
.cron-row{display:flex;align-items:center;gap:10px;padding:10px 14px;background:#0f172a;border-bottom:1px solid #1e293b;}
.cron-row:last-child{border-bottom:none;}
.cron-row:hover{background:#111827;}
.cron-row.completada-late{border-left:3px solid #fb923c;}
.cron-row.completada-ok{border-left:3px solid #4ade80;}
.cron-row.oos{border-left:3px solid #f87171;}
.cron-status-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0;}
.cst-pend{background:#334155;} .cst-curso{background:#60a5fa;animation:pulse 1.5s infinite;}
.cst-ok{background:#4ade80;} .cst-late{background:#fb923c;} .cst-oos{background:#f87171;} .cst-na{background:#475569;}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:0.4;}}
.cron-nombre{flex:1;font-size:0.82em;color:#e2e8f0;font-weight:600;}
.cron-hora{font-size:0.7em;color:#475569;width:50px;text-align:center;flex-shrink:0;}
.cron-resp{font-size:0.66em;background:#172554;color:#93c5fd;padding:2px 8px;border-radius:12px;flex-shrink:0;}
.cron-proc{font-size:0.66em;color:#475569;font-style:italic;flex-shrink:0;max-width:90px;}
.cron-tiempos{font-size:0.68em;color:#64748b;flex-shrink:0;text-align:right;min-width:80px;}
.cron-btns{display:flex;gap:4px;flex-shrink:0;}
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:1000;align-items:center;justify-content:center;}
.modal-overlay.open{display:flex;}
.modal{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:24px;width:420px;max-width:92vw;}
.modal-title{font-size:0.85em;font-weight:800;color:#e2e8f0;margin-bottom:16px;}
.modal-close{float:right;background:none;border:none;color:#475569;font-size:1.2em;cursor:pointer;margin-top:-4px;}
.modal-close:hover{color:#e2e8f0;}
.modal-footer{display:flex;gap:8px;justify-content:flex-end;margin-top:16px;flex-wrap:wrap;}
.prog-bar{height:6px;background:#1e293b;border-radius:3px;overflow:hidden;margin-top:6px;}
.prog-fill{height:100%;border-radius:3px;background:#4ade80;transition:width 0.4s;}
.week-chart{display:flex;gap:6px;align-items:flex-end;height:60px;margin-top:8px;}
.week-bar-wrap{flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;}
.week-bar{width:100%;border-radius:3px 3px 0 0;background:#2B7A78;min-height:2px;}
.week-day{font-size:0.6em;color:#475569;text-align:center;}
.week-pct{font-size:0.62em;color:#94a3b8;text-align:center;}
</style>
</head>
<body>
<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:#6d28d9;"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
  <div>
    <div class="cx-mod-header__title">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#6d28d9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><path d="M9 3h6M10 3v6.5L4 19a2 2 0 001.7 3h12.6a2 2 0 001.7-3l-6-9.5V3"/><path d="M6 14h12"/></svg>
      Calidad BPM
    </div>
    <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; Espagiria &middot; cuarentena, NCs &amp; CAPA</div>
  </div>
  <div class="cx-mod-header__nav">
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">&larr; Módulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
    </button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>
<div class="tabs">
  <div class="tab active" onclick="goTab('tab-bandeja')">&#x1F3AF; Bandeja del Dia</div>
  <div class="tab" onclick="goTab('tab-dash')">&#128202; Dashboard</div>
  <div class="tab" onclick="goTab('tab-cron')">&#128203; Cronograma del Dia</div>
  <div class="tab" onclick="goTab('tab-cc')">&#x1F9EA; Control Calidad MP</div>
  <div class="tab" onclick="goTab('tab-nc')">&#x26A0; No Conformidades</div>
  <div class="tab" onclick="goTab('tab-cal')">&#x1F527; Calibraciones</div>
  <div class="tab" onclick="goTab('tab-micro')">&#x1F9EB; Micro &amp; Heatmap</div>
  <div class="tab" onclick="goTab('tab-agua')">&#x1F4A7; Sistema de Agua</div>
  <div class="tab" onclick="goTab('tab-equipos')">&#x1F527; Equipos</div>
  <div class="tab" onclick="goTab('tab-oos')">&#x26A0;&#xFE0F; OOS</div>
</div>
<div class="main">

<!-- Ã¢ÂÂÃ¢ÂÂ DASHBOARD Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ -->
<!-- BANDEJA DEL DIA · centro de mando QC -->
<div id="tab-bandeja" class="pane active">
  <div class="card" style="background:linear-gradient(135deg,#1e293b,#334155);color:#f1f5f9;border:none">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">
      <div>
        <div style="font-size:0.78em;color:#94a3b8;text-transform:uppercase;letter-spacing:.6px">Bandeja QC</div>
        <div id="bandeja-fecha" style="font-size:1.4em;font-weight:700;color:#7ACFCC">Cargando...</div>
      </div>
      <div style="display:flex;gap:14px;flex-wrap:wrap;align-items:center">
        <div style="text-align:center"><div style="font-size:0.7em;color:#94a3b8">PENDIENTES</div><div id="bandeja-total" style="font-size:1.6em;font-weight:800;color:#fbbf24">—</div></div>
        <div style="text-align:center"><div style="font-size:0.7em;color:#94a3b8">CRITICOS</div><div id="bandeja-criticos" style="font-size:1.6em;font-weight:800;color:#ef4444">—</div></div>
        <button class="btn btn-ghost btn-sm" onclick="loadBandeja()">&#x21BB; Refrescar</button>
      </div>
    </div>
  </div>
  <div id="bandeja-secciones" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:14px;margin-top:14px">
    <p class="empty">Cargando...</p>
  </div>
</div>

<!-- DASHBOARD -->
<div id="tab-dash" class="pane">
  <div class="kpi-row">
    <div class="kpi"><div class="kpi-label">Cronograma Hoy</div><div class="kpi-val good" id="kv-cron-pct">â</div><div class="kpi-sub">% completado</div></div>
    <div class="kpi"><div class="kpi-label">Lotes en Cuarentena</div><div class="kpi-val warn" id="kv-cuarentena">Ã¢ÂÂ</div><div class="kpi-sub">Pendientes CC</div></div>
    <div class="kpi"><div class="kpi-label">Aprobados (30d)</div><div class="kpi-val good" id="kv-aprobados">Ã¢ÂÂ</div><div class="kpi-sub">Lotes aprobados</div></div>
    <div class="kpi"><div class="kpi-label">Rechazados (30d)</div><div class="kpi-val crit" id="kv-rechazados">Ã¢ÂÂ</div><div class="kpi-sub">Lotes rechazados</div></div>
    <div class="kpi"><div class="kpi-label">NC Abiertas</div><div class="kpi-val warn" id="kv-nc">Ã¢ÂÂ</div><div class="kpi-sub">No conformidades</div></div>
    <div class="kpi"><div class="kpi-label">Calibraciones Vencidas</div><div class="kpi-val crit" id="kv-cals">Ã¢ÂÂ</div><div class="kpi-sub">Requieren accion</div>
    <div class="kpi"><div class="kpi-label">PT Liberados (30d)</div><div class="kpi-val good" id="kv-lib-mes">—</div><div class="kpi-sub">Productos terminados</div></div>
    <div class="kpi"><div class="kpi-label">Tasa Liberacion PT</div><div class="kpi-val good" id="kv-tasa-lib">—</div><div class="kpi-sub">% aprobados vs total</div></div></div>
  </div>
  <div class="card">
    <div class="card-title">Cumplimiento â Ultimos 7 dias</div>
    <div class="week-chart" id="week-chart"><p style="color:#475569;font-size:0.78em">Cargando...</p></div>
  </div>
    <div class="card">
    <div class="card-title">Actividad Reciente</div>
    <div class="actividad" id="act-list"><p class="empty">Cargando...</p></div>
  </div>
</div>

<!-- Ã¢ÂÂÃ¢ÂÂ CONTROL CALIDAD MP (cuarentena) Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ -->

<!-- ââ CRONOGRAMA DEL DIA ââââââââââââââââââââââââââââ -->
<div id="tab-cron" class="pane">
  <div class="cron-topbar">
    <input type="date" id="cron-fecha" onchange="loadCronograma()">
    <button class="btn btn-ghost btn-sm" onclick="cronHoy()">Hoy</button>
    <div class="cron-summary" id="cron-summary">
      <div class="cron-stat"><strong id="cs-comp">â</strong>&nbsp;completadas</div>
      <div class="cron-stat"><strong id="cs-total">â</strong>&nbsp;tareas</div>
      <div class="cron-stat"><strong id="cs-oos">â</strong>&nbsp;OOS</div>
      <div class="cron-stat"><strong id="cs-pct">â</strong>% cumplimiento</div>
    </div>
    <div id="cron-progbar" style="width:100%">
      <div class="prog-bar"><div class="prog-fill" id="cron-pfill" style="width:0%"></div></div>
    </div>
  </div>
  <div id="cron-sections"><p class="empty">Cargando cronograma...</p></div>
</div>

<div id="tab-cc" class="pane">
  <div class="card">
    <div class="card-title">Lotes en Cuarentena Ã¢ÂÂ Pendientes de Revision</div>
    <table>
      <thead><tr><th>MP / Lote</th><th>Cantidad</th><th>Proveedor</th><th>Fec. Vencimiento</th><th>OC</th><th>Accion</th></tr></thead>
      <tbody id="cc-tbody"><tr><td colspan="6" class="empty">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>

<!-- Ã¢ÂÂÃ¢ÂÂ NO CONFORMIDADES Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ -->
<div id="tab-nc" class="pane">
  <div class="card">
    <div class="card-title">Registrar No Conformidad</div>
    <div class="form-row">
      <div class="form-group"><label>Tipo</label><select id="nc-tipo"><option>Proceso</option><option>Producto</option><option>Proveedor</option><option>Equipo</option><option>Documentacion</option></select></div>
      <div class="form-group"><label>Area</label><select id="nc-area"><option>Produccion</option><option>Laboratorio</option><option>Calidad</option><option>Administrativa</option><option>Almacen</option></select></div>
      <div class="form-group"><label>Impacto</label><select id="nc-impacto"><option>Bajo</option><option>Medio</option><option>Alto</option><option>Critico</option></select></div>
    </div>
    <div class="form-row">
      <div class="form-group" style="flex:2"><label>Descripcion</label><textarea id="nc-desc" placeholder="Describir la no conformidad detectada..."></textarea></div>
      <div class="form-group"><label>Responsable</label><input id="nc-responsable" placeholder="Nombre responsable"/></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Lote (si aplica)</label><input id="nc-lote" placeholder="Ej: LOT-001"/></div>
      <div class="form-group"><label>Codigo MP (si aplica)</label><input id="nc-mp" placeholder="Ej: MPMP00001"/></div>
      <div class="form-group"><label>Accion Correctiva</label><textarea id="nc-accion" placeholder="Accion inmediata tomada..." style="min-height:50px"></textarea></div>
    </div>
    <button class="btn btn-primary" onclick="registrarNC()">Registrar NC</button>
  </div>
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">
      <span class="card-title" style="margin:0">Historial de No Conformidades</span>
      <input type="text" placeholder="Buscar..." oninput="buscarTabla('nc', this.value)" style="padding:6px 10px;border:1px solid #cbd5e1;border-radius:4px;max-width:200px">
    </div>
    <table>
      <thead><tr><th>ID</th><th>Fecha</th><th>Tipo</th><th>Area</th><th>Descripcion</th><th>Impacto</th><th>Estado</th><th>Accion</th></tr></thead>
      <tbody id="nc-tbody"><tr><td colspan="8" class="empty">Cargando...</td></tr></tbody>
    </table>
    <div id="pg-nc"></div>
  </div>
</div>

<!-- Ã¢ÂÂÃ¢ÂÂ CALIBRACIONES Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ -->
<div id="tab-cal" class="pane">
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px"><span class="card-title" style="margin:0">Instrumentos y Equipos &middot; Estado de Calibracion</span><input type="text" placeholder="Buscar..." oninput="buscarTabla('cal', this.value)" style="padding:6px 10px;border:1px solid #cbd5e1;border-radius:4px;max-width:200px"></div>
    <table>
      <thead><tr><th>Instrumento</th><th>Codigo</th><th>Ubicacion</th><th>Ultima Cal.</th><th>Proxima Cal.</th><th>Responsable</th><th>Certificado</th><th>Estado</th></tr></thead>
      <tbody id="cal-tbody"><tr><td colspan="8" class="empty">Cargando...</td></tr></tbody>
    </table>
    <div id="pg-cal"></div>
  </div>
</div>


<!-- MICRO HEATMAP -->
<div id="tab-micro" class="pane">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:14px">
    <div>
      <div class="card-title" style="margin:0">\u{1F9EB} Mapa de calor microbiologico</div>
      <div style="color:#94a3b8;font-size:12px;margin-top:2px">Doble limite: <b>industria</b> (INVIMA / farmacopea) y <b>meta lab</b> (interno mas estricto). Auto-OOS si supera limite industria.</div>
    </div>
    <div style="display:flex;gap:8px;align-items:center">
      <select id="micro-meses" onchange="loadMicroHeatmap()" style="padding:6px 10px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;border-radius:6px;font-size:12px">
        <option value="3">Ultimos 3 meses</option>
        <option value="6">Ultimos 6 meses</option>
        <option value="12" selected>Ultimos 12 meses</option>
        <option value="24">Ultimos 24 meses</option>
      </select>
      <button class="btn btn-primary btn-sm" onclick="abrirModalNuevoResultadoMicro()">+ Registrar resultado</button>
      <button class="btn btn-ghost btn-sm" onclick="loadMicroHeatmap()">\u21bb</button>
    </div>
  </div>
  <div id="micro-kpis" class="kpi-row" style="margin-bottom:14px"></div>
  <div class="card">
    <div style="overflow-x:auto">
      <table id="micro-heatmap-tbl" style="font-size:12px;min-width:900px">
        <thead id="micro-heatmap-thead"></thead>
        <tbody id="micro-heatmap-tbody"><tr><td class="empty">Cargando matriz...</td></tr></tbody>
      </table>
    </div>
  </div>
  <div class="card" style="margin-top:14px">
    <div class="card-title">Ultimos resultados registrados</div>
    <table>
      <thead><tr><th>Fecha</th><th>Lote</th><th>Producto</th><th>Microorganismo</th><th>Valor</th><th>Estado</th><th>OOS</th><th>Analista</th></tr></thead>
      <tbody id="micro-res-tbody"><tr><td colspan="8" class="empty">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>

<!-- SISTEMA DE AGUA \u00b7 COC-PRO-008 (v2 con estado-hoy + tendencia + filtros + export) -->
<div id="tab-agua" class="pane">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:14px">
    <div>
      <div class="card-title" style="margin:0">\u{1F4A7} Sistema de Agua (COC-PRO-008)</div>
      <div style="color:#94a3b8;font-size:12px;margin-top:2px">L\u00edmites USP: pH 5.0-7.5 \u00b7 cond \u2264 1.3 \u00b5S/cm \u00b7 TOC \u2264 500 ppb \u00b7 micro \u2264 100 UFC/100mL</div>
    </div>
    <div style="display:flex;gap:8px">
      <button class="btn btn-ghost btn-sm" onclick="loadAguaCompleto()">\u21bb Refrescar</button>
    </div>
  </div>

  <!-- Card 1: Estado de hoy -->
  <div id="agua-estado-hoy" class="card" style="margin-bottom:14px">
    <p class="empty">Cargando estado de hoy...</p>
  </div>

  <!-- Card 2: Form r\u00e1pido inline -->
  <div class="card" style="margin-bottom:14px">
    <div class="card-title">Registrar lectura</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px">
      <div class="form-group"><label>Punto muestreo *</label>
        <select id="ag-punto"><option value="">--</option><option>Tanque RO</option><option>Salida RO</option><option>Loop1</option><option>Loop2</option><option>POS-1</option><option>POS-2</option><option>Otro</option></select>
      </div>
      <div class="form-group"><label>Tipo agua</label>
        <select id="ag-tipo"><option value="purificada">Purificada</option><option value="potable">Potable</option><option value="destilada">Destilada</option><option value="wfi">WFI</option></select>
      </div>
      <div class="form-group"><label>pH</label><input id="ag-ph" type="number" step="0.01" placeholder="5.0-7.5"></div>
      <div class="form-group"><label>Cond. \u00b5S/cm</label><input id="ag-cond" type="number" step="0.001" placeholder="\u22641.3"></div>
      <div class="form-group"><label>TOC ppb</label><input id="ag-toc" type="number" step="0.1" placeholder="\u2264500"></div>
      <div class="form-group"><label>Micro UFC/mL</label><input id="ag-micro" type="number" step="0.1" placeholder="\u2264100"></div>
      <div class="form-group"><label>Cloro ppm</label><input id="ag-cloro" type="number" step="0.01"></div>
      <div class="form-group"><label>Temp \u00b0C</label><input id="ag-temp" type="number" step="0.1"></div>
    </div>
    <div class="form-group"><label>Observaciones</label><input id="ag-obs" placeholder="opcional"></div>
    <div style="text-align:right;margin-top:8px">
      <button class="btn btn-primary" onclick="guardarLecturaAguaInline()">Registrar</button>
    </div>
    <div id="ag-msg" style="margin-top:8px;font-size:12px"></div>
  </div>

  <!-- Card 3: Tendencia 30d -->
  <div class="card" style="margin-bottom:14px">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">
      <div class="card-title" style="margin:0">Tendencia</div>
      <select id="ag-dias" onchange="loadAguaTendencia()" style="padding:4px 8px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;border-radius:4px;font-size:12px">
        <option value="7">7 d\u00edas</option>
        <option value="30" selected>30 d\u00edas</option>
        <option value="90">90 d\u00edas</option>
      </select>
    </div>
    <div id="ag-kpis" style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:10px;font-size:12px"></div>
    <div id="ag-drift-alert" style="margin-bottom:8px"></div>
    <div id="ag-grafico" style="overflow-x:auto"><p class="empty">Cargando tendencia...</p></div>
  </div>

  <!-- Card 4: Hist\u00f3rico con filtros + export -->
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">
      <div class="card-title" style="margin:0">Hist\u00f3rico</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:12px">
        <input id="ag-f-desde" type="date" style="padding:4px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;border-radius:4px">
        <input id="ag-f-hasta" type="date" style="padding:4px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;border-radius:4px">
        <select id="ag-f-estado" style="padding:4px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;border-radius:4px">
          <option value="">Todos estados</option><option value="ok">OK</option><option value="alerta">Alerta</option><option value="fuera_spec">Fuera spec</option>
        </select>
        <button class="btn btn-ghost btn-sm" onclick="loadAguaRegistros()">Filtrar</button>
        <button class="btn btn-ghost btn-sm" onclick="exportarAguaCSV()">\u2b07 CSV</button>
      </div>
    </div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Fecha</th><th>Hora</th><th>Punto</th><th>Tipo</th><th>pH</th><th>Cond.</th><th>TOC</th><th>Micro</th><th>Estado</th><th>Operador</th></tr></thead>
        <tbody id="agua-tbody"><tr><td colspan="10" class="empty">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- EQUIPOS Y CALIBRACIONES · COC-PRO-006 + COC-PRO-012 + PRD-PRO-004 -->
<div id="tab-equipos" class="pane">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:14px">
    <div>
      <div class="card-title" style="margin:0">&#x1F527; Equipos &amp; Calibraciones</div>
      <div style="color:#94a3b8;font-size:12px;margin-top:2px">104 equipos del listado maestro · cronograma 2026 PRD-PRO-004 · hoja de vida por equipo</div>
    </div>
    <div style="display:flex;gap:8px">
      <button class="btn btn-ghost btn-sm" onclick="loadEquiposCompleto()">&#x21BB; Refrescar</button>
    </div>
  </div>

  <!-- KPIs estado equipos -->
  <div id="eq-kpis" class="kpi-row" style="margin-bottom:14px">
    <div class="kpi"><div class="kpi-label">Activos</div><div class="kpi-val" id="eq-kpi-total">—</div></div>
    <div class="kpi"><div class="kpi-label">Vigentes</div><div class="kpi-val good" id="eq-kpi-vig">—</div></div>
    <div class="kpi"><div class="kpi-label">Próximos 30d</div><div class="kpi-val warn" id="eq-kpi-prox">—</div></div>
    <div class="kpi"><div class="kpi-label">Vencidos</div><div class="kpi-val crit" id="eq-kpi-venc">—</div></div>
    <div class="kpi"><div class="kpi-label">Sin tracking</div><div class="kpi-val" id="eq-kpi-sin">—</div></div>
  </div>

  <!-- Card 1: Vencidos (rojos arriba) -->
  <div class="card" style="margin-bottom:14px;border-left:4px solid #ef4444">
    <div class="card-title">&#x26A0;&#xFE0F; Vencidos · BLOQUEADOS</div>
    <div style="font-size:12px;color:#94a3b8;margin-bottom:6px">Estos equipos NO se pueden usar hasta registrar una calibración nueva.</div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Código</th><th>Equipo</th><th>Área</th><th>Tipo</th><th>Vencido hace</th><th>Última calibración</th><th>Acción</th></tr></thead>
        <tbody id="eq-venc-tbody"><tr><td colspan="7" class="empty">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>

  <!-- Card 2: Próximos 30d -->
  <div class="card" style="margin-bottom:14px;border-left:4px solid #fbbf24">
    <div class="card-title">&#x23F0; Próximos 30 días</div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Código</th><th>Equipo</th><th>Área</th><th>Vence en</th><th>Fecha próxima</th><th>Acción</th></tr></thead>
        <tbody id="eq-prox-tbody"><tr><td colspan="6" class="empty">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>

  <!-- Card 3: Cronograma del mes -->
  <div class="card" style="margin-bottom:14px">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">
      <div class="card-title" style="margin:0">&#x1F4C5; Cronograma del mes (PRD-PRO-004)</div>
      <div style="display:flex;gap:6px;align-items:center;font-size:12px">
        <select id="eq-cron-mes" onchange="loadEquiposCronograma()" style="padding:4px 8px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;border-radius:4px">
          <option value="1">Enero</option><option value="2">Febrero</option><option value="3">Marzo</option>
          <option value="4">Abril</option><option value="5">Mayo</option><option value="6">Junio</option>
          <option value="7">Julio</option><option value="8">Agosto</option><option value="9">Septiembre</option>
          <option value="10">Octubre</option><option value="11">Noviembre</option><option value="12">Diciembre</option>
        </select>
        <span id="eq-cron-resumen" style="color:#94a3b8"></span>
      </div>
    </div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Código</th><th>Equipo</th><th>Tipo</th><th>Estado</th><th>Completado</th><th>Acción</th></tr></thead>
        <tbody id="eq-cron-tbody"><tr><td colspan="6" class="empty">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>

  <!-- Card 4: Sin tracking -->
  <div class="card">
    <div class="card-title" style="color:#64748b">Sin tracking de calibración (no urgente)</div>
    <div style="font-size:12px;color:#94a3b8;margin-bottom:6px">Equipos del listado maestro sin ningún evento registrado todavía.</div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Código</th><th>Equipo</th><th>Área</th><th>Tipo</th><th>Acción</th></tr></thead>
        <tbody id="eq-sin-tbody"><tr><td colspan="5" class="empty">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- Modal: hoja de vida del equipo -->
<div class="modal-overlay" id="m-eq-hv">
  <div class="modal" style="max-width:900px">
    <button class="modal-close" onclick="closeModal('m-eq-hv')">&times;</button>
    <div class="modal-title" id="m-eq-hv-title">Hoja de vida</div>
    <div id="m-eq-hv-body"><p class="empty">Cargando...</p></div>
  </div>
</div>

<!-- Modal: registrar evento -->
<div class="modal-overlay" id="m-eq-ev">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('m-eq-ev')">&times;</button>
    <div class="modal-title" id="m-eq-ev-title">Registrar evento</div>
    <input type="hidden" id="m-eq-ev-codigo">
    <div class="form-group"><label>Tipo de evento *</label>
      <select id="m-eq-ev-tipo">
        <option value="calibracion">Calibración (externa ONAC)</option>
        <option value="verificacion_diaria">Verificación diaria</option>
        <option value="verificacion_semestral">Verificación semestral</option>
        <option value="mantenimiento_preventivo">Mantenimiento preventivo</option>
        <option value="mantenimiento_correctivo">Mantenimiento correctivo</option>
        <option value="reparacion">Reparación</option>
        <option value="validacion">Validación (IQ/OQ/PQ)</option>
        <option value="reactivacion">Reactivación post-mantenimiento</option>
        <option value="baja">Baja del equipo</option>
      </select>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>Fecha</label><input id="m-eq-ev-fecha" type="date"></div>
      <div class="form-group"><label>Próxima vence</label><input id="m-eq-ev-prox" type="date"></div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>Responsable</label><input id="m-eq-ev-resp" placeholder="Quién ejecutó"></div>
      <div class="form-group"><label>Empresa externa</label><input id="m-eq-ev-emp" placeholder="(si aplica) ONAC, etc."></div>
    </div>
    <div class="form-group"><label>Resultado</label>
      <select id="m-eq-ev-res">
        <option value="aprobado">Aprobado · dentro de tolerancia</option>
        <option value="rechazado">Rechazado · fuera de tolerancia</option>
        <option value="con_observaciones">Con observaciones</option>
        <option value="">(sin resultado)</option>
      </select>
    </div>
    <div class="form-group"><label>Certificado URL</label><input id="m-eq-ev-cert" placeholder="opcional"></div>
    <div class="form-group"><label>Observaciones</label><textarea id="m-eq-ev-obs" style="min-height:60px"></textarea></div>
    <div class="form-actions">
      <button class="btn btn-ghost" onclick="closeModal('m-eq-ev')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarEventoEquipo()">Registrar</button>
    </div>
    <div id="m-eq-ev-msg" style="margin-top:8px;font-size:12px"></div>
  </div>
</div>

<!-- OOS -->
<div id="tab-oos" class="pane">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:14px">
    <div>
      <div class="card-title" style="margin:0">\u26a0\ufe0f Out Of Specification (OOS)</div>
      <div style="color:#94a3b8;font-size:12px;margin-top:2px">Workflow: lote a cuarentena \u2192 investigaci\u00f3n \u2192 causa ra\u00edz \u2192 aprobaci\u00f3n \u2192 cierre.</div>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <input type="text" placeholder="Buscar..." oninput="buscarTabla('oos', this.value)" style="padding:6px 10px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;border-radius:6px;font-size:12px;max-width:200px">
      <select id="oos-filtro" onchange="loadOOS()" style="padding:6px 10px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;border-radius:6px;font-size:12px">
        <option value="">Todos</option>
        <option value="abierto" selected>Abiertos</option>
        <option value="en_investigacion">En investigaci\u00f3n</option>
        <option value="en_aprobacion">En aprobaci\u00f3n</option>
        <option value="cerrado">Cerrados</option>
      </select>
      <button class="btn btn-ghost btn-sm" onclick="loadOOS()">\u21bb</button>
    </div>
  </div>
  <div class="card">
    <table>
      <thead><tr><th>Codigo</th><th>Origen</th><th>Lote</th><th>Producto</th><th>Parametro</th><th>Valor</th><th>Detectado</th><th>Estado</th><th>Acci\u00f3n</th></tr></thead>
      <tbody id="oos-tbody"><tr><td colspan="9" class="empty">Cargando...</td></tr></tbody>
    </table>
    <div id="pg-oos"></div>
  </div>
</div>

<!-- Modal nuevo resultado micro -->
<div class="modal-overlay" id="m-micro">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('m-micro')">&times;</button>
    <div class="modal-title">Registrar resultado microbiol\u00f3gico</div>
    <div class="form-group"><label>Producto</label><input id="m-micro-prod" placeholder="Ej: LBHA"></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>Lote</label><input id="m-micro-lote" placeholder="Ej: 261001"></div>
      <div class="form-group"><label>Fecha analisis</label><input id="m-micro-fecha" type="date"></div>
    </div>
    <div class="form-group"><label>Microorganismo</label>
      <select id="m-micro-org">
        <option value="Mes\u00f3filos aerobios totales">Mes\u00f3filos aerobios totales</option>
        <option value="Mohos y levaduras">Mohos y levaduras</option>
        <option value="E. coli">E. coli</option>
        <option value="Staphylococcus aureus">Staphylococcus aureus</option>
        <option value="Pseudomonas aeruginosa">Pseudomonas aeruginosa</option>
        <option value="Candida albicans">Candida albicans</option>
        <option value="Burkholderia cepacia">Burkholderia cepacia</option>
      </select>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>Valor (UFC/g)</label><input id="m-micro-val" type="number" min="0" step="any"></div>
      <div class="form-group"><label>O texto (ausencia)</label><input id="m-micro-txt" placeholder="ausencia, &lt;10"></div>
    </div>
    <div class="form-group"><label>Observaciones</label><textarea id="m-micro-obs" style="min-height:50px"></textarea></div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModal('m-micro')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarResultadoMicro()">Guardar</button>
    </div>
  </div>
</div>

<!-- Modal nuevo agua -->
<div class="modal-overlay" id="m-agua">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('m-agua')">&times;</button>
    <div class="modal-title">Registrar lectura sistema de agua</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>Punto muestreo</label><input id="m-agua-punto" placeholder="Loop1, POS-1"></div>
      <div class="form-group"><label>Tipo</label>
        <select id="m-agua-tipo">
          <option value="purificada" selected>Purificada</option>
          <option value="potable">Potable</option>
          <option value="destilada">Destilada</option>
          <option value="wfi">WFI</option>
        </select>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>Fecha</label><input id="m-agua-fecha" type="date"></div>
      <div class="form-group"><label>Hora</label><input id="m-agua-hora" type="time"></div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>pH</label><input id="m-agua-ph" type="number" step="0.01"></div>
      <div class="form-group"><label>Cond. \u00b5S/cm</label><input id="m-agua-cond" type="number" step="0.001"></div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>TOC ppb</label><input id="m-agua-toc" type="number" step="0.1"></div>
      <div class="form-group"><label>Micro UFC/ml</label><input id="m-agua-micro" type="number" step="0.1"></div>
    </div>
    <div class="form-group"><label>Observaciones</label><textarea id="m-agua-obs" style="min-height:50px"></textarea></div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModal('m-agua')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarLecturaAgua()">Guardar</button>
    </div>
  </div>
</div>

</div><!-- /main -->

<!-- ââ MODAL COMPLETAR TAREA âââââââââââââââââââââââââ -->
<div class="modal-overlay" id="m-cron-comp">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('m-cron-comp')">&times;</button>
    <div class="modal-title" id="m-cron-title">Completar tarea</div>
    <div id="m-cron-valor-wrap" style="display:none;margin-bottom:12px">
      <div class="form-group">
        <label id="m-cron-valor-lbl">Valor registrado</label>
        <input id="m-cron-valor" placeholder="Ingrese el valor medido"/>
      </div>
    </div>
    <div class="form-group" style="margin-bottom:12px">
      <label>Observaciones (opcional)</label>
      <textarea id="m-cron-obs" placeholder="Novedades, valores fuera de rango, etc..." style="min-height:60px"></textarea>
    </div>
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
      <input type="checkbox" id="m-cron-oos" style="width:auto;cursor:pointer">
      <label for="m-cron-oos" style="font-size:0.78em;color:#fca5a5;text-transform:none;letter-spacing:0;cursor:pointer">Resultado fuera de especificacion (OOS)</label>
    </div>
    <input type="hidden" id="m-cron-id">
    <div class="modal-footer">
      <button class="btn btn-ghost btn-sm" onclick="decidirTarea('No aplica')">No aplica hoy</button>
      <button class="btn btn-primary" onclick="decidirTarea('Completada')">&#10003; Completar</button>
    </div>
  </div>
</div>

<script>
function esc(s){const d=document.createElement('div');d.appendChild(document.createTextNode(s||'')); return d.innerHTML;}
function fmt(d){return d?d.substring(0,10):'â';}
function fmtH(s){return s?s.substring(0,5):'â';}
function openModal(id){document.getElementById(id).classList.add('open');}
function closeModal(id){document.getElementById(id).classList.remove('open');}

// CSRF defense-in-depth
function _csrf() {
  var m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}
function _fetchOpts(method, body) {
  var headers = {};
  var tok = _csrf();
  if (tok) headers['X-CSRF-Token'] = tok;
  var opts = {method: method || 'GET', headers: headers, credentials: 'same-origin'};
  if (body !== undefined && body !== null) {
    headers['Content-Type'] = 'application/json';
    opts.body = (typeof body === 'string') ? body : JSON.stringify(body);
  }
  return opts;
}
fetch('/api/csrf-token', {credentials: 'same-origin'}).catch(function(){});

// Filtros + Paginacion (client-side)
var TBL_STATE = {
  bandeja: {q: '', page: 1, size: 25, fields: ['titulo','tipo','estado','responsable']},
  nc:      {q: '', page: 1, size: 25, fields: ['codigo','tipo','origen','estado','descripcion']},
  cal:     {q: '', page: 1, size: 25, fields: ['equipo','codigo','tipo','estado']},
  cron:    {q: '', page: 1, size: 25, fields: ['codigo','tipo','estado','responsable']},
  esp:     {q: '', page: 1, size: 25, fields: ['producto','parametro','tipo']},
  coa:     {q: '', page: 1, size: 25, fields: ['lote','producto','aprobado_por','estado']},
  est:     {q: '', page: 1, size: 25, fields: ['producto','lote','condicion']},
  capa:    {q: '', page: 1, size: 25, fields: ['titulo','tipo','estado','responsable']},
  aud:     {q: '', page: 1, size: 25, fields: ['tipo','area','responsable','estado']},
  micro:   {q: '', page: 1, size: 25, fields: ['ubicacion','tipo','resultado']},
  agua:    {q: '', page: 1, size: 25, fields: ['punto','operario','observaciones']},
  oos:     {q: '', page: 1, size: 25, fields: ['lote','parametro','estado','asignado_a']},
  equipos: {q: '', page: 1, size: 25, fields: ['codigo','nombre','area','estado']},
};
function _filtrar(data, query, fields) {
  if (!query) return data || [];
  var q = query.toLowerCase().trim();
  return (data || []).filter(function(r) {
    return fields.some(function(f) {
      var v = r[f]; return v != null && String(v).toLowerCase().indexOf(q) !== -1;
    });
  });
}
function _paginar(data, page, size) {
  if (size >= 999) return {items: data, total: data.length, totalPages: 1, page: 1};
  var total = data.length;
  var totalPages = Math.max(1, Math.ceil(total / size));
  var p = Math.min(Math.max(1, page), totalPages);
  return {items: data.slice((p-1)*size, p*size), total: total, totalPages: totalPages, page: p};
}
function _renderPag(tabla, info) {
  var s = TBL_STATE[tabla];
  if (info.total <= s.size && info.total < 26) {
    return '<div style="font-size:11px;color:#64748b;padding:6px 0;">' + info.total + ' filas</div>';
  }
  var html = '<div style="display:flex;align-items:center;gap:8px;padding:8px 0;font-size:12px;color:#94a3b8;">';
  html += '<span>P' + String.fromCharCode(225) + 'g ' + info.page + '/' + info.totalPages + ' ' + String.fromCharCode(183) + ' ' + info.total + '</span>';
  html += '<span style="flex:1"></span>';
  html += '<button class="btn btn-ghost btn-sm" onclick="cambiarPag(\'' + tabla + '\',-1)"' +
          (info.page <= 1 ? ' disabled' : '') + '>&larr;</button>';
  html += '<button class="btn btn-ghost btn-sm" onclick="cambiarPag(\'' + tabla + '\',1)"' +
          (info.page >= info.totalPages ? ' disabled' : '') + '>&rarr;</button>';
  html += '<select onchange="cambiarPagSize(\'' + tabla + '\', this.value)" ' +
          'style="background:#0f172a;border:1px solid #334155;color:#cbd5e1;padding:4px 6px;border-radius:5px;font-size:12px;">';
  ['25','50','100','999'].forEach(function(o){
    var label = o === '999' ? 'Todas' : o;
    html += '<option value="' + o + '"' + (String(s.size)===o?' selected':'') + '>' + label + '</option>';
  });
  html += '</select></div>';
  return html;
}
var _PAG_REFRESH = {
  bandeja: function(){ if(window.loadBandeja) loadBandeja(); },
  nc: function(){ if(window.loadNC) loadNC(); },
  cal: function(){ if(window.loadCalibraciones) loadCalibraciones(); },
  cron: function(){ if(window.loadCronograma) loadCronograma(); },
  esp: function(){ if(window.loadEspecificaciones) loadEspecificaciones(); },
  coa: function(){ if(window.loadCOA) loadCOA(); },
  est: function(){ if(window.loadEstabilidades) loadEstabilidades(); },
  capa: function(){ if(window.loadCAPA) loadCAPA(); },
  aud: function(){ if(window.loadAuditorias) loadAuditorias(); },
  micro: function(){ if(window.loadMicro) loadMicro(); },
  agua: function(){ if(window.loadAgua) loadAgua(); },
  oos: function(){ if(window.loadOOS) loadOOS(); },
  equipos: function(){ if(window.loadEquipos) loadEquipos(); },
};
function cambiarPag(tabla, delta){ TBL_STATE[tabla].page = Math.max(1, TBL_STATE[tabla].page + delta); if(_PAG_REFRESH[tabla]) _PAG_REFRESH[tabla](); }
function cambiarPagSize(tabla, valor){ TBL_STATE[tabla].size = parseInt(valor,10)||25; TBL_STATE[tabla].page = 1; if(_PAG_REFRESH[tabla]) _PAG_REFRESH[tabla](); }
function buscarTabla(tabla, valor){ TBL_STATE[tabla].q = valor||''; TBL_STATE[tabla].page = 1; if(_PAG_REFRESH[tabla]) _PAG_REFRESH[tabla](); }


var _tabIds=['tab-bandeja','tab-dash','tab-cron','tab-cc','tab-nc','tab-cal','tab-micro','tab-agua','tab-equipos','tab-oos'];
function goTab(id){
  document.querySelectorAll('.tab').forEach((t,i)=>{t.classList.toggle('active',_tabIds[i]===id);});
  document.querySelectorAll('.pane').forEach(p=>p.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  if(id==='tab-bandeja') loadBandeja();
  else if(id==='tab-dash') loadDash();
  else if(id==='tab-cron') loadCronograma();
  else if(id==='tab-cc') loadCuarentena();
  else if(id==='tab-nc') loadNC();
  else if(id==='tab-cal') loadCal();
  else if(id==='tab-micro') loadMicroHeatmap();
  else if(id==='tab-agua') loadAguaRegistros();
  else if(id==='tab-equipos') loadEquiposCompleto();
  else if(id==='tab-oos') loadOOS();
}

// === EQUIPOS Y CALIBRACIONES (COC-PRO-006/012 + PRD-PRO-004) ===========
async function loadEquiposCompleto(){
  // Setear mes actual en el dropdown
  var mesEl = document.getElementById('eq-cron-mes');
  if(mesEl && !mesEl.value){ mesEl.value = (new Date().getMonth() + 1); }
  await Promise.all([loadEquiposDashboard(), loadEquiposCronograma()]);
}

async function loadEquiposDashboard(){
  try{
    var r = await fetch('/api/calidad/equipos/dashboard');
    if(!r.ok){ console.error('equipos dashboard fallo', r.status); return; }
    var d = await r.json();
    var k = d.kpis || {};
    document.getElementById('eq-kpi-total').textContent = k.total_activos || 0;
    document.getElementById('eq-kpi-vig').textContent = k.vigentes || 0;
    document.getElementById('eq-kpi-prox').textContent = k.proximos_30d || 0;
    document.getElementById('eq-kpi-venc').textContent = k.vencidos || 0;
    document.getElementById('eq-kpi-sin').textContent = k.sin_tracking || 0;

    // Vencidos
    var vencTb = document.getElementById('eq-venc-tbody');
    if((d.vencidos||[]).length === 0){
      vencTb.innerHTML = '<tr><td colspan="7" class="empty" style="color:#15803d">&#x2705; Sin equipos vencidos</td></tr>';
    } else {
      vencTb.innerHTML = d.vencidos.map(function(it){
        return '<tr style="background:#fef2f2">'
          +'<td><b><code>'+_escBan(it.codigo)+'</code></b></td>'
          +'<td>'+_escBan(it.nombre||'')+'</td>'
          +'<td>'+_escBan(it.area||'')+'</td>'
          +'<td>'+_escBan(it.tipo||'')+'</td>'
          +'<td style="color:#ef4444;font-weight:700">+'+(it.dias_vencido||0)+'d</td>'
          +'<td>'+_escBan(it.ultima_calibracion||'—')+'</td>'
          +'<td><button class="btn btn-primary btn-sm" onclick="abrirEventoEquipo(\''+_escBan(it.codigo)+'\',\''+_escBan(it.nombre||'')+'\')">+ Calibrar</button> '
          +'<button class="btn btn-ghost btn-sm" onclick="abrirHojaVidaEquipo(\''+_escBan(it.codigo)+'\')">Hoja vida</button></td>'
          +'</tr>';
      }).join('');
    }

    // Próximos 30d
    var proxTb = document.getElementById('eq-prox-tbody');
    if((d.proximos_30d||[]).length === 0){
      proxTb.innerHTML = '<tr><td colspan="6" class="empty">Sin equipos próximos a vencer</td></tr>';
    } else {
      proxTb.innerHTML = d.proximos_30d.map(function(it){
        return '<tr>'
          +'<td><b><code>'+_escBan(it.codigo)+'</code></b></td>'
          +'<td>'+_escBan(it.nombre||'')+'</td>'
          +'<td>'+_escBan(it.area||'')+'</td>'
          +'<td style="color:#fbbf24;font-weight:600">'+(it.dias_para_vencer||0)+'d</td>'
          +'<td>'+_escBan(it.fecha_proxima||'—')+'</td>'
          +'<td><button class="btn btn-primary btn-sm" onclick="abrirEventoEquipo(\''+_escBan(it.codigo)+'\',\''+_escBan(it.nombre||'')+'\')">+ Calibrar</button></td>'
          +'</tr>';
      }).join('');
    }

    // Sin tracking
    var sinTb = document.getElementById('eq-sin-tbody');
    if((d.sin_tracking||[]).length === 0){
      sinTb.innerHTML = '<tr><td colspan="5" class="empty">Todos los equipos tienen tracking &#x2705;</td></tr>';
    } else {
      sinTb.innerHTML = d.sin_tracking.slice(0, 30).map(function(it){
        return '<tr>'
          +'<td><b><code>'+_escBan(it.codigo)+'</code></b></td>'
          +'<td>'+_escBan(it.nombre||'')+'</td>'
          +'<td>'+_escBan(it.area||'')+'</td>'
          +'<td>'+_escBan(it.tipo||'')+'</td>'
          +'<td><button class="btn btn-ghost btn-sm" onclick="abrirEventoEquipo(\''+_escBan(it.codigo)+'\',\''+_escBan(it.nombre||'')+'\')">+ Iniciar tracking</button></td>'
          +'</tr>';
      }).join('');
    }
  }catch(e){ console.error('loadEquiposDashboard error:', e); }
}

async function loadEquiposCronograma(){
  var mesEl = document.getElementById('eq-cron-mes');
  var mes = mesEl ? mesEl.value : (new Date().getMonth() + 1);
  var tb = document.getElementById('eq-cron-tbody');
  var resumen = document.getElementById('eq-cron-resumen');
  try{
    var r = await fetch('/api/calidad/equipos/cronograma?mes='+mes);
    var d = await r.json();
    var k = d.kpis || {};
    if(resumen) resumen.textContent = (k.completados||0)+'/'+(k.total||0)+' completados ('+(k.cumplimiento_pct!=null?k.cumplimiento_pct+'%':'—')+')';
    if(!d.items || d.items.length === 0){
      tb.innerHTML = '<tr><td colspan="6" class="empty">Sin items programados este mes</td></tr>';
      return;
    }
    tb.innerHTML = d.items.map(function(it){
      var col = it.estado === 'completado' ? '#15803d' : (it.estado === 'reprogramado' ? '#fbbf24' : '#64748b');
      var btn = it.estado === 'completado'
        ? '<span style="color:#15803d;font-size:0.85em">&#x2713; '+_escBan(it.fecha_completado||'')+'</span>'
        : '<button class="btn btn-primary btn-sm" onclick="completarCronogramaEq('+it.id+')">Completar</button>';
      return '<tr>'
        +'<td><b><code>'+_escBan(it.equipo_codigo)+'</code></b></td>'
        +'<td>'+_escBan(it.equipo_nombre||'')+'</td>'
        +'<td><span style="text-transform:uppercase;font-weight:600;font-size:0.78em">'+_escBan(it.tipo_actividad)+'</span></td>'
        +'<td><span style="color:'+col+';font-weight:600">'+_escBan(it.estado)+'</span></td>'
        +'<td>'+_escBan(it.completado_por||'—')+'</td>'
        +'<td>'+btn+'</td>'
        +'</tr>';
    }).join('');
  }catch(e){ tb.innerHTML = '<tr><td colspan="6" class="empty" style="color:#c00">Error: '+_escBan(e.message||String(e))+'</td></tr>'; }
}

function abrirEventoEquipo(codigo, nombre){
  document.getElementById('m-eq-ev-codigo').value = codigo;
  document.getElementById('m-eq-ev-title').textContent = 'Registrar evento · '+codigo+(nombre ? ' · '+nombre : '');
  document.getElementById('m-eq-ev-fecha').value = new Date().toISOString().slice(0,10);
  ['m-eq-ev-prox','m-eq-ev-resp','m-eq-ev-emp','m-eq-ev-cert','m-eq-ev-obs','m-eq-ev-msg'].forEach(function(id){
    var el = document.getElementById(id); if(el) el.value = '';
  });
  document.getElementById('m-eq-ev-msg').innerHTML = '';
  openModal('m-eq-ev');
}

async function guardarEventoEquipo(){
  var codigo = document.getElementById('m-eq-ev-codigo').value;
  var msg = document.getElementById('m-eq-ev-msg');
  var body = {
    tipo_evento: document.getElementById('m-eq-ev-tipo').value,
    fecha: document.getElementById('m-eq-ev-fecha').value || null,
    fecha_proxima: document.getElementById('m-eq-ev-prox').value || null,
    responsable: document.getElementById('m-eq-ev-resp').value || null,
    empresa_externa: document.getElementById('m-eq-ev-emp').value || null,
    certificado_url: document.getElementById('m-eq-ev-cert').value || null,
    resultado: document.getElementById('m-eq-ev-res').value || null,
    observaciones: document.getElementById('m-eq-ev-obs').value || null,
  };
  msg.innerHTML = '<span style="color:#64748b">Guardando...</span>';
  try{
    var r = await fetch('/api/calidad/equipos/'+encodeURIComponent(codigo)+'/registrar-evento', _fetchOpts('POST', body));
    var d = await r.json();
    if(d.ok){
      msg.innerHTML = '<span style="color:#15803d;font-weight:600">&#x2705; Evento #'+d.evento_id+' registrado</span>';
      setTimeout(function(){ closeModal('m-eq-ev'); loadEquiposCompleto(); }, 800);
    } else {
      msg.innerHTML = '<span style="color:#ef4444">Error: '+_escBan(d.error||'?')+'</span>';
    }
  }catch(e){ msg.innerHTML = '<span style="color:#ef4444">Error red: '+_escBan(e.message||String(e))+'</span>'; }
}

async function completarCronogramaEq(cronId){
  var obs = prompt('Observaciones (opcional):');
  if(obs === null) return;
  try{
    var r = await fetch('/api/calidad/equipos/cronograma/'+cronId+'/completar', _fetchOpts('POST', {observaciones: obs}));
    var d = await r.json();
    if(d.ok){ loadEquiposCronograma(); }
    else alert('Error: '+(d.error||'?'));
  }catch(e){ alert('Error red: '+e.message); }
}

async function abrirHojaVidaEquipo(codigo){
  var body = document.getElementById('m-eq-hv-body');
  document.getElementById('m-eq-hv-title').textContent = 'Hoja de vida · '+codigo;
  body.innerHTML = '<p class="empty">Cargando...</p>';
  openModal('m-eq-hv');
  try{
    var r = await fetch('/api/calidad/equipos/'+encodeURIComponent(codigo)+'/hoja-vida');
    var d = await r.json();
    if(!r.ok){ body.innerHTML = '<p class="empty" style="color:#c00">'+_escBan(d.error||'?')+'</p>'; return; }
    var eq = d.equipo;
    var html = '<div class="card" style="background:#0f172a;color:#f1f5f9;margin-bottom:10px">'
      +'<div style="font-size:0.78em;color:#94a3b8">'+_escBan(eq.codigo)+'</div>'
      +'<div style="font-size:1.2em;font-weight:700">'+_escBan(eq.nombre||'')+'</div>'
      +'<div style="font-size:0.85em;color:#cbd5e1;margin-top:4px">'
      +_escBan(eq.tipo||'')+' · '+_escBan(eq.area||'')+' · '+_escBan(eq.ubicacion||'')
      +(eq.capacidad_raw ? ' · capacidad: '+_escBan(eq.capacidad_raw) : '')
      +'</div>'
      +'<div style="font-size:0.78em;color:#94a3b8;margin-top:4px">Estado: <b>'+_escBan(eq.estado_operacional||'?')+'</b> · Activo: '+(eq.activo?'sí':'no')+'</div>'
      +'</div>';
    html += '<div class="card-title" style="margin-top:10px">Eventos ('+(d.eventos||[]).length+')</div>';
    if(!d.eventos || d.eventos.length === 0){
      html += '<p class="empty">Sin eventos registrados</p>';
    } else {
      html += '<table style="font-size:0.85em"><thead><tr><th>Fecha</th><th>Tipo</th><th>Estado</th><th>Próxima</th><th>Responsable</th><th>Resultado</th></tr></thead><tbody>';
      d.eventos.forEach(function(ev){
        var col = ev.resultado === 'aprobado' ? '#15803d' : (ev.resultado === 'rechazado' ? '#ef4444' : '#64748b');
        html += '<tr>'
          +'<td>'+_escBan(ev.fecha||'')+'</td>'
          +'<td><b>'+_escBan(ev.tipo_evento||'')+'</b></td>'
          +'<td>'+_escBan(ev.estado||'')+'</td>'
          +'<td>'+_escBan(ev.fecha_proxima||'—')+'</td>'
          +'<td>'+_escBan(ev.responsable||'')+(ev.empresa_externa ? ' ('+_escBan(ev.empresa_externa)+')' : '')+'</td>'
          +'<td><span style="color:'+col+'">'+_escBan(ev.resultado||'—')+'</span></td>'
          +'</tr>';
      });
      html += '</tbody></table>';
    }
    html += '<div style="margin-top:10px;text-align:right"><button class="btn btn-primary" onclick="closeModal(\'m-eq-hv\');abrirEventoEquipo(\''+_escBan(eq.codigo)+'\',\''+_escBan(eq.nombre||'')+'\')">+ Nuevo evento</button></div>';
    body.innerHTML = html;
  }catch(e){ body.innerHTML = '<p class="empty" style="color:#c00">Error: '+_escBan(e.message||String(e))+'</p>'; }
}

// === BANDEJA QC DEL DIA · centro de mando ==============================
// Sebastián 1-may-2026: una sola pantalla con TODO lo pendiente del equipo
// Calidad. Reemplaza Excel + WhatsApp + revisar 5 tabs distintas.
function _escBan(s){return String(s||'').replace(/[&<>"']/g,function(ch){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];});}

function _bandejaCard(opts){
  var cls = opts.accent==='red' ? '#ef4444' : (opts.accent==='amber' ? '#fbbf24' : (opts.accent==='green' ? '#15803d' : '#7ACFCC'));
  var html = '<div class="card" style="border-left:4px solid '+cls+'">';
  html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">';
  html += '<div style="font-size:0.95em;font-weight:700;color:#0f172a">'+(opts.icon||'')+' '+_escBan(opts.titulo)+'</div>';
  html += '<div style="background:'+cls+';color:#fff;padding:3px 10px;border-radius:12px;font-size:0.78em;font-weight:700">'+(opts.total||0)+'</div>';
  html += '</div>';
  if(opts.subtitulo){
    html += '<div style="font-size:0.78em;color:#64748b;margin-bottom:6px">'+opts.subtitulo+'</div>';
  }
  if(!opts.items || opts.items.length===0){
    html += '<div style="padding:12px;text-align:center;color:#94a3b8;font-size:0.82em;font-style:italic">'+(opts.empty_msg||'Sin items')+'</div>';
  } else {
    html += '<div style="max-height:280px;overflow-y:auto">';
    for(var i=0;i<Math.min(opts.items.length,8);i++){
      html += opts.render_item(opts.items[i]);
    }
    if(opts.items.length>8){
      html += '<div style="text-align:center;padding:6px;font-size:0.78em;color:#64748b">+ '+(opts.items.length-8)+' más</div>';
    }
    html += '</div>';
  }
  html += '</div>';
  return html;
}

async function loadBandeja(){
  var sec = document.getElementById('bandeja-secciones');
  var fechaEl = document.getElementById('bandeja-fecha');
  var totalEl = document.getElementById('bandeja-total');
  var critEl = document.getElementById('bandeja-criticos');
  if(sec) sec.innerHTML = '<p class="empty">Cargando...</p>';
  try{
    var r = await fetch('/api/calidad/bandeja');
    if(!r.ok){
      if(sec) sec.innerHTML = '<p class="empty" style="color:#c00">Error '+r.status+'</p>';
      return;
    }
    var d = await r.json();
    var s = d.secciones || {};
    var k = d.kpis || {};

    if(fechaEl){
      var fecha = new Date(d.fecha_hoy + 'T00:00:00');
      fechaEl.textContent = fecha.toLocaleDateString('es-CO', {weekday:'long',day:'numeric',month:'long',year:'numeric'});
    }
    if(totalEl) totalEl.textContent = k.total_pendientes || 0;
    var criticos = (k.lotes_cuarentena_criticos||0) + ((s.ncs_abiertas&&s.ncs_abiertas.criticas)||0) + (k.calibraciones_vencidas||0);
    if(critEl) critEl.textContent = criticos;

    var html = '';

    // 1. Lotes en cuarentena
    html += _bandejaCard({
      titulo:'Lotes en Cuarentena', icon:'&#x1F4E6;',
      total: s.lotes_cuarentena.total,
      accent: s.lotes_cuarentena.criticos>0 ? 'red' : (s.lotes_cuarentena.total>0 ? 'amber' : 'green'),
      subtitulo: s.lotes_cuarentena.criticos>0 ? '&#x26A0;&#xFE0F; '+s.lotes_cuarentena.criticos+' lotes >5 días en cuarentena' : 'Esperando liberación QC',
      items: s.lotes_cuarentena.items,
      empty_msg:'Sin lotes en cuarentena',
      render_item: function(it){
        var col = it.critico ? '#ef4444' : '#64748b';
        return '<div style="padding:6px 8px;border-bottom:1px solid #f1f5f9;font-size:0.82em">'
          + '<b>'+_escBan(it.material_nombre||'')+'</b> · Lote <code>'+_escBan(it.lote||'s/n')+'</code><br>'
          + '<span style="color:'+col+';font-size:0.92em">' + _escBan(it.tipo||'MP') + ' · '+(it.dias_cuarentena||0)+'d en cuarentena · '+_escBan(it.proveedor||'')+'</span>'
          + '</div>';
      }
    });

    // 2. NCs abiertas
    html += _bandejaCard({
      titulo:'No Conformidades Abiertas', icon:'&#x26A0;',
      total: s.ncs_abiertas.total,
      accent: s.ncs_abiertas.criticas>0 ? 'red' : (s.ncs_abiertas.total>0 ? 'amber' : 'green'),
      subtitulo: s.ncs_abiertas.criticas>0 ? s.ncs_abiertas.criticas+' críticas/altas' : null,
      items: s.ncs_abiertas.items,
      empty_msg:'Sin NCs abiertas',
      render_item: function(it){
        var col = it.urgente ? '#ef4444' : (it.impacto==='Critico'||it.impacto==='Alto' ? '#fbbf24' : '#64748b');
        return '<div style="padding:6px 8px;border-bottom:1px solid #f1f5f9;font-size:0.82em">'
          + '<span style="background:'+col+';color:#fff;padding:1px 6px;border-radius:8px;font-size:0.75em;margin-right:4px">'+_escBan(it.impacto||'')+'</span>'
          + _escBan(it.descripcion||'')
          + '<br><span style="color:#94a3b8;font-size:0.92em">'+_escBan(it.area||'')+' · '+(it.dias_abierta||0)+'d abierta</span>'
          + '</div>';
      }
    });

    // 3. OOS abiertas
    html += _bandejaCard({
      titulo:'OOS Abiertos', icon:'&#x26A0;&#xFE0F;',
      total: s.oos_abiertas.total,
      accent: s.oos_abiertas.total>0 ? 'red' : 'green',
      items: s.oos_abiertas.items,
      empty_msg:'Sin OOS abiertos',
      render_item: function(it){
        return '<div style="padding:6px 8px;border-bottom:1px solid #f1f5f9;font-size:0.82em">'
          + '<b>'+_escBan(it.producto||'')+'</b> · Lote <code>'+_escBan(it.lote||'')+'</code><br>'
          + '<span style="color:#ef4444">'+_escBan(it.parametro||'')+': <b>'+_escBan(String(it.valor||''))+'</b> (spec: '+_escBan(String(it.spec||''))+')</span>'
          + ' · '+(it.dias_abierta||0)+'d'
          + '</div>';
      }
    });

    // 4. Calibraciones
    var cal = s.calibraciones;
    var calItems = (cal.vencidas||[]).concat(cal.proximas_7d||[]);
    html += _bandejaCard({
      titulo:'Calibraciones',  icon:'&#x1F527;',
      total: cal.total_vencidas + cal.total_proximas,
      accent: cal.total_vencidas>0 ? 'red' : (cal.total_proximas>0 ? 'amber' : 'green'),
      subtitulo: cal.total_vencidas>0 ? cal.total_vencidas+' vencidas · '+cal.total_proximas+' próximas 7d' : cal.total_proximas+' próximas 7d',
      items: calItems,
      empty_msg:'Sin calibraciones pendientes',
      render_item: function(it){
        var venc = (it.dias_vencida!==undefined && it.dias_vencida>0);
        var col = venc ? '#ef4444' : '#fbbf24';
        var diasTxt = venc ? '+'+it.dias_vencida+'d vencida' : it.dias_restantes+'d restantes';
        return '<div style="padding:6px 8px;border-bottom:1px solid #f1f5f9;font-size:0.82em">'
          + '<b>'+_escBan(it.instrumento||'')+'</b> ('+_escBan(it.codigo||'')+')<br>'
          + '<span style="color:'+col+'">'+diasTxt+'</span> · '+_escBan(it.ubicacion||'')+' · '+_escBan(it.responsable||'')
          + '</div>';
      }
    });

    // 5. Muestreo micro semana
    html += _bandejaCard({
      titulo:'Muestreo Microbiológico (semana)', icon:'&#x1F9EB;',
      total: s.muestreo_micro_semana.total,
      accent: s.muestreo_micro_semana.total>0 ? 'amber' : 'green',
      items: s.muestreo_micro_semana.items,
      empty_msg:'Sin muestreos pendientes esta semana',
      render_item: function(it){
        return '<div style="padding:6px 8px;border-bottom:1px solid #f1f5f9;font-size:0.82em">'
          + '<b>'+_escBan(it.area_nombre||it.area_codigo||'')+'</b> · '+_escBan(it.tipo||'')
          + '<br><span style="color:#64748b">'+_escBan(it.fecha||'')+' · '+_escBan(it.asignado_a||'sin asignar')+'</span>'
          + '</div>';
      }
    });

    // 6. Agua hoy
    var agua = s.registro_agua_hoy;
    var aguaItem = agua.registrado ? [{texto:'Conductividad: '+(agua.conductividad||'?')+' · pH: '+(agua.ph||'?')+' · Por: '+(agua.registrado_por||'?')}] : [];
    html += _bandejaCard({
      titulo:'Sistema de Agua (hoy)', icon:'&#x1F4A7;',
      total: agua.registrado ? 1 : 0,
      accent: agua.registrado ? 'green' : 'red',
      subtitulo: agua.registrado ? 'Registrado &#x2713;' : (agua.alerta || 'Falta registro hoy'),
      items: aguaItem,
      empty_msg:'&#x26A0;&#xFE0F; Falta registro de agua hoy',
      render_item: function(it){
        return '<div style="padding:6px 8px;font-size:0.82em">'+_escBan(it.texto)+'</div>';
      }
    });

    // 7. Cola liberación PT
    var cola = s.cola_liberacion;
    html += _bandejaCard({
      titulo:'Liberación PT', icon:'&#x1F510;',
      total: cola.total,
      accent: cola.listos_revisar_hoy>0 ? 'amber' : (cola.total>0 ? 'amber' : 'green'),
      subtitulo: cola.listos_revisar_hoy>0 ? '&#x1F525; '+cola.listos_revisar_hoy+' listos para revisar HOY' : null,
      items: cola.items,
      empty_msg:'Sin lotes en cola de liberación',
      render_item: function(it){
        var col = it.listo_hoy ? '#fbbf24' : '#64748b';
        var txt = it.listo_hoy ? 'LISTO HOY' : (it.dias_para||0)+'d';
        return '<div style="padding:6px 8px;border-bottom:1px solid #f1f5f9;font-size:0.82em">'
          + '<b>'+_escBan(it.producto||'')+'</b> · Lote <code>'+_escBan(it.lote||'')+'</code>'
          + '<br><span style="background:'+col+';color:#fff;padding:1px 6px;border-radius:8px;font-size:0.75em">'+txt+'</span>'
          + ' · '+_escBan(it.estado||'')
          + '</div>';
      }
    });

    // 8. Auditorías próximas
    html += _bandejaCard({
      titulo:'Auditorías Próximas (60d)', icon:'&#x1F50D;',
      total: s.auditorias_proximas.total,
      accent: 'amber',
      items: s.auditorias_proximas.items,
      empty_msg:'Sin auditorías programadas',
      render_item: function(it){
        return '<div style="padding:6px 8px;border-bottom:1px solid #f1f5f9;font-size:0.82em">'
          + '<b>'+_escBan(it.tipo||'')+'</b> · '+_escBan(it.fecha||'')
          + '<br><span style="color:#64748b">'+_escBan(it.descripcion||'')+'</span>'
          + '</div>';
      }
    });

    // 9. Estabilidades
    html += _bandejaCard({
      titulo:'Estabilidades (próximas 30d)', icon:'&#x1F4C8;',
      total: s.estabilidades_pendientes.total,
      accent: 'amber',
      items: s.estabilidades_pendientes.items,
      empty_msg:'Sin análisis de estabilidad próximos',
      render_item: function(it){
        return '<div style="padding:6px 8px;border-bottom:1px solid #f1f5f9;font-size:0.82em">'
          + '<b>'+_escBan(it.producto||'')+'</b> · Lote <code>'+_escBan(it.lote||'')+'</code>'
          + '<br><span style="color:#64748b">'+_escBan(it.condicion||'')+' · próximo: '+_escBan(it.fecha_proxima||'')+' ('+(it.dias||0)+'d)</span>'
          + '</div>';
      }
    });

    if(sec) sec.innerHTML = html;
  }catch(e){
    console.error('loadBandeja error:', e);
    if(sec) sec.innerHTML = '<p class="empty" style="color:#c00">Error de red: '+_escBan(e.message||String(e))+'</p>';
  }
}

// Auto-load bandeja al inicio
window.addEventListener('DOMContentLoaded', function(){ loadBandeja(); });

// === MICRO HEATMAP =====================================================
async function loadMicroHeatmap(){
  try{
    var meses = (document.getElementById('micro-meses')||{value:12}).value;
    var r = await fetch('/api/calidad/micro/heatmap?meses='+meses);
    var d = await r.json();
    // KPIs
    var kpis = d.kpis || {};
    var kbox = document.getElementById('micro-kpis');
    var tasaOk = kpis.tasa_ok != null ? kpis.tasa_ok+'%' : '—';
    kbox.innerHTML = ''+
      '<div class="kpi-card"><div class="kpi-l">Resultados (ventana)</div><div class="kpi-v">'+(kpis.total_resultados||0)+'</div></div>'+
      '<div class="kpi-card"><div class="kpi-l" style="color:#fca5a5">Fuera industria</div><div class="kpi-v" style="color:#fca5a5">'+(kpis.total_fuera_industria||0)+'</div></div>'+
      '<div class="kpi-card"><div class="kpi-l" style="color:#fcd34d">Fuera meta lab</div><div class="kpi-v" style="color:#fcd34d">'+(kpis.total_fuera_meta||0)+'</div></div>'+
      '<div class="kpi-card"><div class="kpi-l" style="color:#34d399">Tasa OK</div><div class="kpi-v" style="color:#34d399">'+tasaOk+'</div></div>';
    // Header heatmap
    var thead = document.getElementById('micro-heatmap-thead');
    var ths = '<tr><th style="text-align:left;background:#0f172a;position:sticky;left:0;z-index:1">Producto</th>';
    (d.microorganismos||[]).forEach(function(m){
      ths += '<th style="text-align:center;font-size:10px;writing-mode:vertical-rl;transform:rotate(180deg);min-width:30px;padding:6px 4px;">'+esc(m)+'</th>';
    });
    ths += '</tr>';
    thead.innerHTML = ths;
    // Cuerpo matriz
    var tbody = document.getElementById('micro-heatmap-tbody');
    if(!(d.matriz||[]).length){
      tbody.innerHTML = '<tr><td class="empty">Sin resultados en la ventana. Click "+ Registrar resultado" para empezar.</td></tr>';
      return;
    }
    tbody.innerHTML = d.matriz.map(function(row){
      var html = '<tr><td style="font-weight:700;background:#0f172a;position:sticky;left:0;padding:6px 10px">'+esc(row.producto)+'</td>';
      row.cells.forEach(function(c){
        var bg, color, txt='', title='';
        if(c.estado==='sin_dato'){ bg='#1e293b'; color='#475569'; txt='—'; title='Sin datos en la ventana'; }
        else if(c.estado==='ok'){ bg='#064e3b'; color='#34d399'; txt='✓'; title=c.n+' resultado(s) OK · ult: '+(c.ultima_fecha||'')+' valor '+(c.ultimo_valor!=null?c.ultimo_valor:c.ultimo_texto||''); }
        else if(c.estado==='fuera_meta'){ bg='#854d0e'; color='#fcd34d'; txt='⚠'; title=c.n_fuera_meta+'/'+c.n+' fuera meta · ult valor '+(c.ultimo_valor!=null?c.ultimo_valor:c.ultimo_texto||''); }
        else if(c.estado==='fuera_industria'){ bg='#7f1d1d'; color='#fca5a5'; txt='✘'; title=c.n_fuera_industria+'/'+c.n+' FUERA INDUSTRIA · ult valor '+(c.ultimo_valor!=null?c.ultimo_valor:c.ultimo_texto||''); }
        html += '<td style="background:'+bg+';color:'+color+';text-align:center;font-weight:700;font-size:14px;padding:8px;border:1px solid #0f172a;cursor:help" title="'+title.replace(/"/g,'&quot;')+'">'+txt+'</td>';
      });
      html += '</tr>';
      return html;
    }).join('');
    // Lista ultimos resultados
    var rr = await fetch('/api/calidad/micro/resultados');
    var dd = await rr.json();
    var rb = document.getElementById('micro-res-tbody');
    var lst = (dd.resultados||[]).slice(0,30);
    if(!lst.length){ rb.innerHTML = '<tr><td colspan="8" class="empty">Sin resultados.</td></tr>'; return; }
    rb.innerHTML = lst.map(function(p){
      var estColor = {ok:'#34d399',fuera_meta:'#fcd34d',fuera_industria:'#fca5a5',observacion:'#94a3b8'}[p.estado] || '#94a3b8';
      var oosLink = p.oos_id ? '<a href="#" onclick="event.preventDefault();goTab(\'tab-oos\')" style="color:#fca5a5">OOS</a>' : '';
      return '<tr>'
        +'<td>'+fmt(p.fecha_analisis)+'</td>'
        +'<td>'+esc(p.lote)+'</td>'
        +'<td>'+esc(p.producto_nombre)+'</td>'
        +'<td>'+esc(p.microorganismo)+'</td>'
        +'<td>'+(p.valor!=null?p.valor:esc(p.valor_texto||''))+' '+esc(p.unidad||'')+'</td>'
        +'<td><span style="color:'+estColor+';font-weight:700">'+p.estado+'</span></td>'
        +'<td>'+oosLink+'</td>'
        +'<td>'+esc(p.analista||'')+'</td>'
      +'</tr>';
    }).join('');
  }catch(e){
    document.getElementById('micro-heatmap-tbody').innerHTML = '<tr><td class="empty">Error: '+esc(e.message)+'</td></tr>';
  }
}

function abrirModalNuevoResultadoMicro(){
  ['m-micro-prod','m-micro-lote','m-micro-val','m-micro-txt','m-micro-obs'].forEach(function(id){document.getElementById(id).value='';});
  document.getElementById('m-micro-fecha').value = new Date().toISOString().slice(0,10);
  openModal('m-micro');
}

async function guardarResultadoMicro(){
  var body = {
    producto_nombre: document.getElementById('m-micro-prod').value.trim(),
    lote: document.getElementById('m-micro-lote').value.trim(),
    fecha_analisis: document.getElementById('m-micro-fecha').value,
    microorganismo: document.getElementById('m-micro-org').value,
    valor: document.getElementById('m-micro-val').value || null,
    valor_texto: document.getElementById('m-micro-txt').value || null,
    observaciones: document.getElementById('m-micro-obs').value || null,
  };
  if(!body.producto_nombre || !body.lote){ alert('Producto y lote requeridos'); return; }
  try{
    var r = await fetch('/api/calidad/micro/resultados', _fetchOpts('POST', body));
    var d = await r.json();
    if(d.ok){
      var msg = '✅ Guardado. Estado: '+d.estado;
      if(d.oos_codigo) msg += '\\n\\n⚠ SE CREO '+d.oos_codigo+' AUTOMATICAMENTE — lote a cuarentena.';
      alert(msg);
      closeModal('m-micro');
      loadMicroHeatmap();
    } else { alert('Error: '+(d.error||'?')); }
  }catch(e){ alert('Error de red: '+e.message); }
}

// === SISTEMA DE AGUA ====================================================
// === SISTEMA DE AGUA · COC-PRO-008 (versión avanzada) ===================
// Sebastián 1-may-2026: estado hoy + form inline + tendencia + drift + export
function loadAguaRegistros(){ loadAguaCompleto(); }

async function loadAguaCompleto(){
  await Promise.all([
    loadAguaEstadoHoy(),
    loadAguaTendencia(),
    loadAguaTabla(),
  ]);
}

async function loadAguaEstadoHoy(){
  var box = document.getElementById('agua-estado-hoy');
  if(!box) return;
  try{
    var r = await fetch('/api/calidad/agua/estado-hoy');
    var d = await r.json();
    if(!r.ok){ box.innerHTML = '<p class="empty" style="color:#c00">Error: '+(d.error||r.status)+'</p>'; return; }
    if(d.registrado){
      var ur = d.ultimo_registro;
      var estColor = {ok:'#15803d',alerta:'#fbbf24',fuera_spec:'#ef4444'}[ur.estado]||'#64748b';
      var estIcon = {ok:'✅',alerta:'⚠️',fuera_spec:'🔴'}[ur.estado]||'';
      box.style.borderLeft = '4px solid ' + estColor;
      box.innerHTML =
        '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">'
        +'<div>'
        +'<div style="font-size:0.78em;color:#64748b;text-transform:uppercase">Hoy '+_escBan(d.fecha_hoy)+'</div>'
        +'<div style="font-size:1.4em;font-weight:700;color:'+estColor+'">'+estIcon+' Registrado · '+_escBan(ur.estado)+'</div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px">'
        +'pH '+(ur.ph||'?')+' · cond '+(ur.conductividad_us_cm||'?')+' µS/cm · TOC '+(ur.toc_ppb||'?')+' ppb · micro '+(ur.microorganismos_ufc_ml||'?')+' UFC/mL'
        +'</div>'
        +'<div style="font-size:0.78em;color:#64748b;margin-top:2px">'
        +'Punto: '+_escBan(ur.punto_muestreo||'?')+' · Hora: '+_escBan(ur.hora||'?')+' · Por: '+_escBan(ur.operador||'?')
        +'</div>'
        +'</div>'
        +'</div>';
    } else {
      var col = d.necesita_alerta ? '#ef4444' : '#fbbf24';
      var titulo = d.necesita_alerta ? '🔴 FALTA REGISTRO HOY' : '⏳ Sin registro aún';
      var sub = d.necesita_alerta ? 'Pasada de las 12:00 PM · se notificará al equipo' : 'Recuerda registrar antes del mediodía';
      box.style.borderLeft = '4px solid ' + col;
      box.innerHTML =
        '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">'
        +'<div>'
        +'<div style="font-size:0.78em;color:#64748b;text-transform:uppercase">Hoy '+_escBan(d.fecha_hoy)+' · '+_escBan(d.hora_actual)+'</div>'
        +'<div style="font-size:1.4em;font-weight:700;color:'+col+'">'+titulo+'</div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px">'+sub+'</div>'
        +'</div>'
        +'</div>';
    }
  }catch(e){ box.innerHTML = '<p class="empty" style="color:#c00">Error red: '+_escBan(e.message||String(e))+'</p>'; }
}

async function loadAguaTendencia(){
  var graf = document.getElementById('ag-grafico');
  var kpisEl = document.getElementById('ag-kpis');
  var driftEl = document.getElementById('ag-drift-alert');
  if(!graf) return;
  var dias = (document.getElementById('ag-dias')||{value:30}).value;
  try{
    var r = await fetch('/api/calidad/agua/tendencia?dias='+dias);
    var d = await r.json();
    if(!r.ok){ graf.innerHTML = '<p class="empty" style="color:#c00">Error tendencia</p>'; return; }
    var k = d.kpis || {};
    if(kpisEl){
      kpisEl.innerHTML =
        '<div><b>'+(k.dias_con_registro||0)+'/'+(d.dias_ventana||0)+'</b> días con registro ('+(k.cobertura_pct||0)+'%)</div>'
        +'<div><b>'+(k.lecturas_totales||0)+'</b> lecturas</div>'
        +'<div style="color:#15803d"><b>'+((k.lecturas_totales||0)-(k.lecturas_fuera_spec||0)-(k.lecturas_alerta||0))+'</b> OK</div>'
        +'<div style="color:#fbbf24"><b>'+(k.lecturas_alerta||0)+'</b> alerta</div>'
        +'<div style="color:#ef4444"><b>'+(k.lecturas_fuera_spec||0)+'</b> fuera spec</div>'
        +'<div><b>'+(k.tasa_ok_pct!=null?k.tasa_ok_pct+'%':'—')+'</b> tasa OK</div>';
    }
    if(driftEl){
      if(d.drift_alerta){
        driftEl.innerHTML = '<div style="background:#fef2f2;border-left:3px solid #ef4444;padding:8px 12px;border-radius:4px;font-size:0.85em;color:#7f1d1d">⚠ <b>Alerta de drift</b>: conductividad creciendo durante '+(d.drift_dias_consecutivos||3)+' días consecutivos · revisar pre-filtros RO</div>';
      } else {
        driftEl.innerHTML = '';
      }
    }
    // SVG simple sparkline para conductividad y pH
    var serie = (d.serie || []).filter(function(s){ return s.conductividad!=null || s.ph!=null; });
    if(serie.length === 0){
      graf.innerHTML = '<p class="empty">Sin datos en el período</p>'; return;
    }
    var W = 800, H = 180, pad = 30;
    var n = serie.length;
    var condVals = serie.map(function(s){ return s.conductividad; }).filter(function(v){return v!=null;});
    var phVals = serie.map(function(s){ return s.ph; }).filter(function(v){return v!=null;});
    var condMax = Math.max.apply(null, condVals.concat([1.3])); // mínimo escala
    var condMin = 0;
    var phMax = Math.max.apply(null, phVals.concat([7.5]));
    var phMin = Math.min.apply(null, phVals.concat([5.0]));

    function xPos(i){ return pad + i * (W - 2*pad) / Math.max(1, n-1); }
    function yPosCond(v){ return H - pad - (v - condMin) / (condMax - condMin || 1) * (H - 2*pad); }
    function yPosPH(v){ return H - pad - (v - phMin) / (phMax - phMin || 1) * (H - 2*pad); }

    var pathCond = '', pathPH = '';
    serie.forEach(function(s, i){
      if(s.conductividad != null){
        pathCond += (pathCond ? 'L' : 'M') + xPos(i).toFixed(1) + ',' + yPosCond(s.conductividad).toFixed(1) + ' ';
      }
      if(s.ph != null){
        pathPH += (pathPH ? 'L' : 'M') + xPos(i).toFixed(1) + ',' + yPosPH(s.ph).toFixed(1) + ' ';
      }
    });

    // Línea umbral conductividad 1.3
    var yLimit = yPosCond(1.3);

    // Marcadores fuera_spec
    var markers = serie.map(function(s, i){
      if(s.n_fuera_spec > 0){
        return '<circle cx="'+xPos(i).toFixed(1)+'" cy="'+yPosCond(s.conductividad||0).toFixed(1)+'" r="4" fill="#ef4444" />';
      }
      return '';
    }).join('');

    var labels = '';
    if(n > 1){
      [0, Math.floor(n/2), n-1].forEach(function(i){
        if(serie[i]) labels += '<text x="'+xPos(i).toFixed(1)+'" y="'+(H-8)+'" text-anchor="middle" font-size="10" fill="#64748b">'+_escBan(serie[i].fecha.slice(5))+'</text>';
      });
    }

    graf.innerHTML =
      '<svg viewBox="0 0 '+W+' '+H+'" style="width:100%;height:'+H+'px;background:#0f172a;border-radius:6px">'
      +'<line x1="'+pad+'" y1="'+yLimit.toFixed(1)+'" x2="'+(W-pad)+'" y2="'+yLimit.toFixed(1)+'" stroke="#ef4444" stroke-width="1" stroke-dasharray="4,4" opacity="0.6" />'
      +'<text x="'+(W-pad)+'" y="'+(yLimit-4).toFixed(1)+'" text-anchor="end" font-size="10" fill="#ef4444">USP máx 1.3 µS/cm</text>'
      +(pathCond ? '<path d="'+pathCond+'" fill="none" stroke="#7ACFCC" stroke-width="2" />' : '')
      +(pathPH ? '<path d="'+pathPH+'" fill="none" stroke="#fbbf24" stroke-width="2" stroke-dasharray="3,3" opacity="0.8" />' : '')
      +markers
      +labels
      +'<text x="'+pad+'" y="14" font-size="11" fill="#7ACFCC" font-weight="700">━ Conductividad</text>'
      +'<text x="'+(pad+120)+'" y="14" font-size="11" fill="#fbbf24" font-weight="700">┄ pH</text>'
      +'</svg>';
  }catch(e){ graf.innerHTML = '<p class="empty" style="color:#c00">Error: '+_escBan(e.message||String(e))+'</p>'; }
}

async function loadAguaTabla(){
  var tb = document.getElementById('agua-tbody');
  if(!tb) return;
  var desde = (document.getElementById('ag-f-desde')||{value:''}).value;
  var hasta = (document.getElementById('ag-f-hasta')||{value:''}).value;
  var estado = (document.getElementById('ag-f-estado')||{value:''}).value;
  var qs = [];
  if(desde) qs.push('desde='+encodeURIComponent(desde));
  if(hasta) qs.push('hasta='+encodeURIComponent(hasta));
  var url = '/api/calidad/agua/registros' + (qs.length ? '?'+qs.join('&') : '');
  try{
    var r = await fetch(url);
    var d = await r.json();
    var lst = (d.registros || []).filter(function(rec){
      return !estado || rec.estado === estado;
    });
    if(!lst.length){ tb.innerHTML='<tr><td colspan="10" class="empty">Sin registros</td></tr>'; return; }
    tb.innerHTML = lst.map(function(rec){
      var col = {ok:'#34d399',alerta:'#fbbf24',fuera_spec:'#ef4444'}[rec.estado]||'#94a3b8';
      return '<tr>'
        +'<td>'+_escBan(rec.fecha||'')+'</td>'
        +'<td>'+_escBan(rec.hora||'—')+'</td>'
        +'<td><b>'+_escBan(rec.punto_muestreo||'')+'</b></td>'
        +'<td>'+_escBan(rec.tipo_agua||'')+'</td>'
        +'<td>'+(rec.ph!=null?rec.ph:'—')+'</td>'
        +'<td>'+(rec.conductividad_us_cm!=null?rec.conductividad_us_cm:'—')+'</td>'
        +'<td>'+(rec.toc_ppb!=null?rec.toc_ppb:'—')+'</td>'
        +'<td>'+(rec.microorganismos_ufc_ml!=null?rec.microorganismos_ufc_ml:'—')+'</td>'
        +'<td><span style="color:'+col+';font-weight:700;text-transform:uppercase;font-size:10px">'+_escBan(rec.estado||'')+'</span></td>'
        +'<td>'+_escBan(rec.operador||'')+'</td>'
      +'</tr>';
    }).join('');
  }catch(e){ tb.innerHTML = '<tr><td colspan="10" class="empty" style="color:#c00">Error: '+_escBan(e.message||String(e))+'</td></tr>'; }
}

async function guardarLecturaAguaInline(){
  var msg = document.getElementById('ag-msg');
  var punto = (document.getElementById('ag-punto')||{value:''}).value.trim();
  if(!punto){ if(msg) msg.innerHTML = '<span style="color:#ef4444">Punto de muestreo requerido</span>'; return; }
  var body = {
    punto_muestreo: punto,
    tipo_agua: (document.getElementById('ag-tipo')||{value:'purificada'}).value,
    ph: (document.getElementById('ag-ph')||{value:''}).value || null,
    conductividad_us_cm: (document.getElementById('ag-cond')||{value:''}).value || null,
    toc_ppb: (document.getElementById('ag-toc')||{value:''}).value || null,
    microorganismos_ufc_ml: (document.getElementById('ag-micro')||{value:''}).value || null,
    cloro_residual_ppm: (document.getElementById('ag-cloro')||{value:''}).value || null,
    temperatura_c: (document.getElementById('ag-temp')||{value:''}).value || null,
    observaciones: (document.getElementById('ag-obs')||{value:''}).value || null,
  };
  if(msg) msg.innerHTML = '<span style="color:#64748b">Registrando...</span>';
  try{
    var r = await fetch('/api/calidad/agua/registros', _fetchOpts('POST', body));
    var d = await r.json();
    if(d.ok){
      var col = d.estado === 'fuera_spec' ? '#ef4444' : (d.estado === 'alerta' ? '#fbbf24' : '#15803d');
      var msgTxt = '✅ Registrado · estado: '+d.estado;
      if(d.warnings && d.warnings.length) msgTxt += ' · ⚠ ' + d.warnings.join('; ');
      if(msg) msg.innerHTML = '<span style="color:'+col+';font-weight:600">'+_escBan(msgTxt)+'</span>';
      // Limpiar form
      ['ag-ph','ag-cond','ag-toc','ag-micro','ag-cloro','ag-temp','ag-obs'].forEach(function(id){
        var el = document.getElementById(id); if(el) el.value='';
      });
      // Refrescar todo
      loadAguaCompleto();
    } else {
      if(msg) msg.innerHTML = '<span style="color:#ef4444">Error: '+_escBan(d.error||'?')+'</span>';
    }
  }catch(e){
    if(msg) msg.innerHTML = '<span style="color:#ef4444">Error red: '+_escBan(e.message||String(e))+'</span>';
  }
}

function exportarAguaCSV(){
  var desde = (document.getElementById('ag-f-desde')||{value:''}).value;
  var hasta = (document.getElementById('ag-f-hasta')||{value:''}).value;
  var qs = [];
  if(desde) qs.push('desde='+encodeURIComponent(desde));
  if(hasta) qs.push('hasta='+encodeURIComponent(hasta));
  window.open('/api/calidad/agua/exportar-csv' + (qs.length ? '?'+qs.join('&') : ''), '_blank');
}

function abrirModalNuevoAgua(){
  ['m-agua-punto','m-agua-ph','m-agua-cond','m-agua-toc','m-agua-micro','m-agua-obs'].forEach(function(id){document.getElementById(id).value='';});
  document.getElementById('m-agua-fecha').value = new Date().toISOString().slice(0,10);
  document.getElementById('m-agua-hora').value = new Date().toTimeString().slice(0,5);
  openModal('m-agua');
}

async function guardarLecturaAgua(){
  var body = {
    punto_muestreo: document.getElementById('m-agua-punto').value.trim(),
    tipo_agua: document.getElementById('m-agua-tipo').value,
    fecha: document.getElementById('m-agua-fecha').value,
    hora: document.getElementById('m-agua-hora').value,
    ph: document.getElementById('m-agua-ph').value || null,
    conductividad_us_cm: document.getElementById('m-agua-cond').value || null,
    toc_ppb: document.getElementById('m-agua-toc').value || null,
    microorganismos_ufc_ml: document.getElementById('m-agua-micro').value || null,
    observaciones: document.getElementById('m-agua-obs').value || null,
  };
  if(!body.punto_muestreo){ alert('Punto de muestreo requerido'); return; }
  try{
    var r = await fetch('/api/calidad/agua/registros', _fetchOpts('POST', body));
    var d = await r.json();
    if(d.ok){
      var msg = '✅ Registrado. Estado: '+d.estado;
      if(d.warnings && d.warnings.length) msg += '\\n\\n⚠ '+d.warnings.join('; ');
      alert(msg);
      closeModal('m-agua');
      loadAguaRegistros();
    } else alert('Error: '+(d.error||'?'));
  }catch(e){ alert('Error de red: '+e.message); }
}

// === OOS ================================================================
async function loadOOS(){
  try{
    var f = (document.getElementById('oos-filtro')||{value:''}).value;
    var r = await fetch('/api/calidad/oos'+(f?'?estado='+f:''));
    var d = await r.json();
    var tb = document.getElementById('oos-tbody');
    var lst = d.oos || [];
    var s = TBL_STATE.oos;
    var filtrado = _filtrar(lst, s.q, s.fields);
    var info = _paginar(filtrado, s.page, s.size);
    s.page = info.page;
    var pgEl = document.getElementById('pg-oos');
    if(!info.items.length){
      tb.innerHTML='<tr><td colspan="9" class="empty">' + (s.q ? 'Sin coincidencias' : 'Sin OOS.') + '</td></tr>';
      if(pgEl) pgEl.innerHTML='';
      return;
    }
    if(pgEl) pgEl.innerHTML = _renderPag('oos', info);
    tb.innerHTML = info.items.map(function(o){
      var estColor = {abierto:'#fca5a5',en_investigacion:'#fcd34d',en_aprobacion:'#a78bfa',cerrado:'#34d399',rechazado:'#94a3b8'}[o.estado]||'#94a3b8';
      var btn = '';
      if(o.estado==='abierto') btn = '<button class="btn btn-primary btn-sm" onclick="oosTransicion('+o.id+',&quot;en_investigacion&quot;)">Investigar</button>';
      else if(o.estado==='en_investigacion') btn = '<button class="btn btn-primary btn-sm" onclick="oosCerrarConDatos('+o.id+')">Cerrar</button>';
      return '<tr>'
        +'<td><b>'+esc(o.codigo)+'</b></td>'
        +'<td>'+esc(o.origen)+'</td>'
        +'<td>'+esc(o.lote||'')+'</td>'
        +'<td>'+esc(o.producto||'')+'</td>'
        +'<td>'+esc(o.parametro||'')+'</td>'
        +'<td>'+(o.valor_obtenido!=null?o.valor_obtenido:esc(o.valor_obtenido_texto||''))+'</td>'
        +'<td>'+esc(o.fecha_deteccion)+'</td>'
        +'<td><span style="color:'+estColor+';font-weight:700;text-transform:uppercase;font-size:10px">'+o.estado+'</span></td>'
        +'<td>'+btn+'</td>'
      +'</tr>';
    }).join('');
  }catch(e){ document.getElementById('oos-tbody').innerHTML='<tr><td class="empty">Error: '+e.message+'</td></tr>'; }
}

async function oosTransicion(id, nuevo){
  // Acepta tanto string directo como evento desde onclick HTML-encoded
  try{
    var r = await fetch('/api/calidad/oos/'+id, _fetchOpts('PATCH', {estado: String(nuevo)}));
    var d = await r.json();
    if(d.ok){ loadOOS(); }
    else alert('Error: '+(d.error||'?'));
  }catch(e){ alert('Error de red: '+e.message); }
}

async function oosCerrarConDatos(id){
  var causa = prompt('Causa raiz identificada:');
  if(!causa) return;
  var disp = prompt('Disposicion (liberado/reprocesado/rechazado/destruido/reanalisis):', 'rechazado');
  if(!disp) return;
  try{
    var r = await fetch('/api/calidad/oos/'+id, _fetchOpts('PATCH', {estado:'cerrado', causa_raiz: causa, disposicion: disp}));
    var d = await r.json();
    if(d.ok){ alert('OOS cerrado'); loadOOS(); }
    else alert('Error: '+(d.error||'?'));
  }catch(e){ alert('Error de red: '+e.message); }
}

/* ââ DASHBOARD ââââââââââââââââââââââââââââââ */
async function loadDash(){
  try{
    const r=await fetch('/api/calidad/dashboard');
    const d=await r.json();
    document.getElementById('kv-cuarentena').textContent=d.cuarentena||0;
    document.getElementById('kv-aprobados').textContent=d.aprobados||0;
    document.getElementById('kv-rechazados').textContent=d.rechazados||0;
    document.getElementById('kv-nc').textContent=d.nc_abiertas||0;
    document.getElementById('kv-cals').textContent=d.cals_vencidas||0;
    document.getElementById('kv-lib-mes').textContent=d.liberados_mes!=null?d.liberados_mes:'-';
    var tasa=d.tasa_liberacion;
    var tasaEl=document.getElementById('kv-tasa-lib');
    if(tasa!=null){tasaEl.textContent=tasa+'%';tasaEl.className='kpi-val '+(tasa>=90?'good':(tasa>=70?'warn':'crit'));}
    else{tasaEl.textContent='N/A';tasaEl.className='kpi-val';}
    const act=document.getElementById('act-list');
    
    loadWeekChart();
    const items=(d.actividad_reciente||[]);
    if(!items.length){act.innerHTML='<p class="empty">Sin actividad reciente</p>';return;}
    act.innerHTML=items.map(a=>`
      <div class="act-item">
        <div class="act-dot dot-${a.color||'verde'}"></div>
        <div class="act-body">
          <div class="act-title">${esc(a.titulo)}</div>
          <div class="act-sub">${esc(a.subtitulo||'')} ${a.fecha?'&middot; '+fmt(a.fecha):''}</div>
        </div>
      </div>`).join('');
  }catch(e){document.getElementById('act-list').innerHTML='<p class="empty">Error: '+esc(e.message)+'</p>';}
}

async function loadWeekChart(){
  try{
    const r=await fetch('/api/calidad/cronograma/resumen');
    const d=await r.json();
    const dias=d.dias||[];
    const total=d.total_tareas||1;
    const hoy=dias[dias.length-1]||{};
    const pctHoy=total>0?Math.round((hoy.completadas||0)*100/total):0;
    const elPct=document.getElementById('kv-cron-pct');
    if(elPct){
      elPct.textContent=pctHoy+'%';
      elPct.className='kpi-val '+(pctHoy>=80?'good':(pctHoy>=50?'warn':'crit'));
    }
    const maxPct=Math.max(...dias.map(d=>total>0?Math.round((d.completadas||0)*100/total):0),1);
    const wc=document.getElementById('week-chart');
    wc.innerHTML=dias.map((dia,i)=>{
      const pct=total>0?Math.round((dia.completadas||0)*100/total):0;
      const h=Math.round((pct/maxPct)*52)+2;
      const col=pct>=80?'#4ade80':(pct>=50?'#fb923c':'#f87171');
      const label=dia.fecha?new Date(dia.fecha+'T12:00:00').toLocaleDateString('es',{weekday:'short'}).substring(0,1).toUpperCase():'?';
      return '<div class="week-bar-wrap"><div class="week-pct">'+pct+'%</div><div class="week-bar" style="height:'+h+'px;background:'+col+'"></div><div class="week-day">'+label+'</div></div>';
    }).join('');
  }catch(e){}
}

/* ââ CRONOGRAMA DEL DIA ââââââââââââââââââ */
var _crDate='', _crTareas=[], _crReg={};

function cronHoy(){
  document.getElementById('cron-fecha').value=new Date().toISOString().substring(0,10);
  loadCronograma();
}

async function loadCronograma(){
  const el=document.getElementById('cron-fecha');
  if(!el.value) el.value=new Date().toISOString().substring(0,10);
  _crDate=el.value;
  const sec=document.getElementById('cron-sections');
  sec.innerHTML='<p class="empty">Cargando...</p>';
  try{
    const r=await fetch('/api/calidad/cronograma?fecha='+_crDate);
    const d=await r.json();
    _crTareas=d.tareas||[];
    _crReg=d.registros||{};
    renderCronograma();
  }catch(e){sec.innerHTML='<p class="empty">Error: '+esc(e.message)+'</p>';}
}
function renderCronograma(){
  const categorias=['Apertura','Produccion','Recepcion','Analisis','Cierre'];
  var totalComp=0,totalOos=0;
  const total=_crTareas.length;
  const byCat={};
  categorias.forEach(c=>{byCat[c]=[];});
  _crTareas.forEach(t=>{
    const cat=t.categoria||'General';
    if(!byCat[cat]) byCat[cat]=[];
    byCat[cat].push(t);
    const reg=_crReg[t.id];
    if(reg&&(reg.estado==='Completada'||reg.estado==='No aplica'||reg.estado==='OOS')){totalComp++;}
    if(reg&&reg.estado==='OOS') totalOos++;
  });
  document.getElementById('cs-comp').textContent=totalComp;
  document.getElementById('cs-total').textContent=total;
  document.getElementById('cs-oos').textContent=totalOos;
  const pct=total>0?Math.round(totalComp*100/total):0;
  document.getElementById('cs-pct').textContent=pct;
  document.getElementById('cron-pfill').style.width=pct+'%';
  document.getElementById('cron-pfill').style.background=pct>=80?'#4ade80':(pct>=50?'#fb923c':'#f87171');
  const ahora=new Date().toISOString().substring(11,16);
  const hoy=new Date().toISOString().substring(0,10);
  const isHoy=_crDate===hoy;
  let html='';
  categorias.forEach(cat=>{
    const tareas=byCat[cat]||[];
    if(!tareas.length) return;
    const catComp=tareas.filter(t=>{const r=_crReg[t.id];return r&&(r.estado==='Completada'||r.estado==='No aplica'||r.estado==='OOS');}).length;
    const catEmoji={'Apertura':'🌅','Produccion':'⚙️','Recepcion':'📦','Analisis':'🔬','Cierre':'🔒'}[cat]||'📋';
    html+='<div class="cron-section"><div class="cron-section-hdr" onclick="toggleCat(this)">';
    html+='<span class="cron-cat-name">'+catEmoji+' '+esc(cat)+'</span>';
    html+='<span class="cron-cat-prog">'+catComp+'/'+tareas.length+'</span>';
    html+='<span class="cron-chevron open">&#9660;</span></div>';
    html+='<div class="cron-rows">';
    tareas.forEach(t=>{
      const reg=_crReg[t.id]||{};
      const est=reg.estado||'Pendiente';
      var dotCls='cst-pend', rowCls='';
      if(est==='En curso'){dotCls='cst-curso';}
      else if(est==='Completada'){const tard=t.hora_limite&&reg.hora_fin&&reg.hora_fin>t.hora_limite;dotCls=tard?'cst-late':'cst-ok';rowCls=tard?'completada-late':'completada-ok';}
      else if(est==='OOS'){dotCls='cst-oos';rowCls='oos';}
      else if(est==='No aplica'){dotCls='cst-na';}
      const vencida=isHoy&&t.hora_limite&&ahora>t.hora_limite&&est==='Pendiente';
      if(vencida) dotCls='cst-late';
      var btns='';
      if(est==='Pendiente'||est==='En curso'){
        if(est==='Pendiente'){btns='<button class="btn btn-ghost btn-sm" data-cron-ini="'+t.id+'">â¶ Iniciar</button>';}
        btns+='<button class="btn btn-primary btn-sm" data-cron-comp="'+t.id+'" data-cron-req="'+t.requiere_valor+'" data-cron-unit="'+esc(t.unidad_valor)+'" data-cron-nom="'+esc(t.nombre)+'">â Completar</button>';
      }else{
        btns='<button class="btn btn-ghost btn-sm" style="font-size:0.68em" data-cron-comp="'+t.id+'" data-cron-req="'+t.requiere_valor+'" data-cron-unit="'+esc(t.unidad_valor)+'" data-cron-nom="'+esc(t.nombre)+'">Editar</button>';
      }
      var tiempoStr='';
      if(reg.hora_inicio) tiempoStr+='Ini: '+fmtH(reg.hora_inicio);
      if(reg.hora_fin) tiempoStr+=(tiempoStr?' ':'')+'Fin: '+fmtH(reg.hora_fin);
      if(reg.valor_registrado) tiempoStr+='<br><span style="color:#7ACFCC">'+esc(reg.valor_registrado)+' '+(t.unidad_valor?esc(t.unidad_valor):'')+'</span>';
      html+='<div class="cron-row '+rowCls+'">';
      html+='<div class="cron-status-dot '+dotCls+'"></div>';
      html+='<div class="cron-nombre">'+esc(t.nombre)+'</div>';
      html+='<div class="cron-hora">'+(t.hora_objetivo?t.hora_objetivo:'â')+'</div>';
      html+='<div class="cron-resp">'+esc(t.responsable)+'</div>';
      if(t.procedimiento) html+='<div class="cron-proc">'+esc(t.procedimiento)+'</div>';
      html+='<div class="cron-tiempos">'+tiempoStr+'</div>';
      html+='<div class="cron-btns">'+btns+'</div>';
      html+='</div>';
    });
    html+='</div></div>';
  });
  document.getElementById('cron-sections').innerHTML=html||'<p class="empty">Sin tareas configuradas</p>';
}

function toggleCat(hdr){
  const rows=hdr.nextElementSibling;
  const chev=hdr.querySelector('.cron-chevron');
  const open=rows.style.display!=='none';
  rows.style.display=open?'none':'';
  chev.classList.toggle('open',!open);
}

document.addEventListener('click',async function(e){
  const ini=e.target.closest('[data-cron-ini]');
  if(ini){
    const tid=ini.dataset.cronIni;
    await fetch('/api/calidad/cronograma/iniciar', _fetchOpts('POST', {tarea_id:parseInt(tid),fecha:_crDate}));
    loadCronograma();
    return;
  }
  const comp=e.target.closest('[data-cron-comp]');
  if(comp){
    _crPendId=comp.dataset.cronComp;
    const req=parseInt(comp.dataset.cronReq)||0;
    const unit=comp.dataset.cronUnit||'';
    const nom=comp.dataset.cronNom||'';
    document.getElementById('m-cron-id').value=_crPendId;
    document.getElementById('m-cron-title').textContent='Completar: '+nom;
    document.getElementById('m-cron-valor-wrap').style.display=req?'block':'none';
    document.getElementById('m-cron-valor-lbl').textContent='Valor registrado'+(unit?' ('+unit+')':'')+'';
    document.getElementById('m-cron-valor').value='';
    document.getElementById('m-cron-obs').value='';
    document.getElementById('m-cron-oos').checked=false;
    const reg=_crReg[parseInt(_crPendId)];
    if(reg){
      if(reg.valor_registrado) document.getElementById('m-cron-valor').value=reg.valor_registrado;
      if(reg.observaciones) document.getElementById('m-cron-obs').value=reg.observaciones;
      if(reg.estado==='OOS') document.getElementById('m-cron-oos').checked=true;
    }
    openModal('m-cron-comp');
    return;
  }
});
var _crPendId=null;

async function decidirTarea(estado){
  const tid=document.getElementById('m-cron-id').value;
  const oos=document.getElementById('m-cron-oos').checked;
  const finalEstado=oos?'OOS':estado;
  const body={tarea_id:parseInt(tid),fecha:_crDate,estado:finalEstado,valor:document.getElementById('m-cron-valor').value,observaciones:document.getElementById('m-cron-obs').value};
  try{
    const r=await fetch('/api/calidad/cronograma/completar',_fetchOpts('POST', body));
    if(r.ok){closeModal('m-cron-comp');loadCronograma();}
    else{const d=await r.json();alert(d.error||'Error al guardar');}
  }catch(e){alert('Error: '+e.message);}
}

/* ââ CUARENTENA ââââââââââââââââââââââââââââââââââââââ */
async function loadCuarentena(){
  const tbody=document.getElementById('cc-tbody');
  try{
    const r=await fetch('/api/recepcion/lotes-cuarentena');
    const rows=await r.json();
    if(!rows.length){tbody.innerHTML='<tr><td colspan="6" class="empty">No hay lotes en cuarentena</td></tr>';return;}
    tbody.innerHTML=rows.map(l=>`<tr>
      <td><strong>${esc(l.material_nombre)}</strong><br><small style="color:#64748b">${esc(l.lote||'sin lote')}</small></td>
      <td>${esc(String(l.cantidad))} g</td>
      <td>${esc(l.proveedor||'â')}</td>
      <td>${fmt(l.fecha_vencimiento)}</td>
      <td>${esc(l.numero_oc||'â')}</td>
      <td style="display:flex;gap:6px">
        <button class="btn btn-primary btn-sm" data-aprobar="${l.id}" data-estado="Aprobado">Aprobar</button>
        <button class="btn btn-danger btn-sm" data-aprobar="${l.id}" data-estado="Rechazado">Rechazar</button>
      </td>
    </tr>`).join('');
  }catch(e){tbody.innerHTML='<tr><td colspan="6" class="empty">Error: '+esc(e.message)+'</td></tr>';}
}

document.addEventListener('click',async function(e){
  const btn=e.target.closest('[data-aprobar]');
  if(!btn) return;
  const movId=btn.dataset.aprobar;
  const estado=btn.dataset.estado;
  if(!confirm('Confirmar: '+estado+' este lote?')) return;
  try{
    const r=await fetch('/api/recepcion/aprobar-lote',_fetchOpts('POST', {mov_id:movId,estado}));
    if(r.ok) loadCuarentena();
    else alert('Error al actualizar');
  }catch(e){alert('Error: '+e.message);}
});

/* ââ NO CONFORMIDADES ââââââââââââââââââââââââââââââââââ */
async function registrarNC(){
  const desc=document.getElementById('nc-desc').value.trim();
  if(!desc){alert('La descripcion es obligatoria');return;}
  const body={tipo:document.getElementById('nc-tipo').value,area:document.getElementById('nc-area').value,impacto:document.getElementById('nc-impacto').value,descripcion:desc,responsable:document.getElementById('nc-responsable').value,lote:document.getElementById('nc-lote').value,codigo_mp:document.getElementById('nc-mp').value,accion_correctiva:document.getElementById('nc-accion').value};
  try{
    const r=await fetch('/api/calidad/no-conformidades',_fetchOpts('POST', body));
    if(r.ok){['nc-desc','nc-responsable','nc-lote','nc-mp','nc-accion'].forEach(id=>document.getElementById(id).value='');loadNC();}
    else{const d=await r.json();alert(d.error||'Error al registrar');}
  }catch(e){alert('Error: '+e.message);}
}

async function loadNC(){
  const tbody=document.getElementById('nc-tbody');
  try{
    const r=await fetch('/api/calidad/no-conformidades');
    const rows=await r.json();
    var s = TBL_STATE.nc;
    var filtrado = _filtrar(rows || [], s.q, s.fields);
    var info = _paginar(filtrado, s.page, s.size);
    s.page = info.page;
    var pgEl = document.getElementById('pg-nc');
    if(!info.items.length){
      tbody.innerHTML='<tr><td colspan="8" class="empty">' + (s.q ? 'Sin coincidencias' : 'No hay no conformidades registradas') + '</td></tr>';
      if(pgEl) pgEl.innerHTML='';
      return;
    }
    if(pgEl) pgEl.innerHTML = _renderPag('nc', info);
    tbody.innerHTML=info.items.map(nc=>{
      const bestado=nc.estado==='Abierta'?'badge-amarillo':(nc.estado==='Cerrada'?'badge-verde':'badge-gris');
      const bimpacto=nc.impacto==='Critico'?'badge-rojo':(nc.impacto==='Alto'?'badge-amarillo':'badge-gris');
      return `<tr>
        <td>#${nc.id}</td>
        <td>${fmt(nc.fecha)}</td>
        <td>${esc(nc.tipo)}</td>
        <td>${esc(nc.area)}</td>
        <td>${esc(nc.descripcion)}</td>
        <td><span class="${bimpacto}">${esc(nc.impacto)}</span></td>
        <td><span class="${bestado}">${esc(nc.estado)}</span></td>
        <td>${nc.estado==='Abierta'?'<button class="btn btn-sm btn-primary" data-cerrar-nc="'+nc.id+'">Cerrar</button>':'â'}</td>
      </tr>`;
    }).join('');
  }catch(e){tbody.innerHTML='<tr><td colspan="8" class="empty">Error: '+esc(e.message)+'</td></tr>';}
}

document.addEventListener('click',async function(ev){
  const btn=ev.target.closest('[data-cerrar-nc]');
  if(!btn) return;
  const ncid=btn.dataset.cerrarNc;
  if(!confirm('Cerrar esta no conformidad?')) return;
  try{
    const r=await fetch('/api/calidad/no-conformidades/'+ncid+'/cerrar', _fetchOpts('POST'));
    if(r.ok) loadNC();
    else alert('Error al cerrar NC');
  }catch(e){alert('Error: '+e.message);}
});

/* ââ CALIBRACIONES âââââââââââââââââââââââââââââââââââââââââââ */
async function loadCal(){
  const tbody=document.getElementById('cal-tbody');
  try{
    const r=await fetch('/api/calidad/calibraciones');
    const rows=await r.json();
    var s = TBL_STATE.cal;
    var filtrado = _filtrar(rows || [], s.q, s.fields);
    var info = _paginar(filtrado, s.page, s.size);
    s.page = info.page;
    var pgEl = document.getElementById('pg-cal');
    if(!info.items.length){
      tbody.innerHTML='<tr><td colspan="8" class="empty">' + (s.q ? 'Sin coincidencias' : 'No hay instrumentos registrados') + '</td></tr>';
      if(pgEl) pgEl.innerHTML='';
      return;
    }
    if(pgEl) pgEl.innerHTML = _renderPag('cal', info);
    tbody.innerHTML=info.items.map(c=>{
      const bs=c.estado==='Vigente'?'badge-verde':(c.estado==='Vencida'?'badge-rojo':'badge-amarillo');
      const hoy=new Date().toISOString().substring(0,10);
      const vence=c.fecha_proxima&&c.fecha_proxima<hoy;
      return `<tr>
        <td><strong>${esc(c.instrumento)}</strong></td>
        <td>${esc(c.codigo)}</td>
        <td>${esc(c.ubicacion)}</td>
        <td>${fmt(c.fecha_ultima)}</td>
        <td style="${vence?'color:#f87171;font-weight:700':''}">${fmt(c.fecha_proxima)}</td>
        <td>${esc(c.responsable)}</td>
        <td><small style="color:#64748b">${esc(c.certificado||'â')}</small></td>
        <td><span class="${bs}">${esc(c.estado)}</span></td>
      </tr>`;
    }).join('');
  }catch(e){tbody.innerHTML='<tr><td colspan="8" class="empty">Error: '+esc(e.message)+'</td></tr>';}
}

// Init
document.getElementById('cron-fecha').value=new Date().toISOString().substring(0,10);
_crDate=new Date().toISOString().substring(0,10);
loadDash();
</script>
</body>
</html>"""