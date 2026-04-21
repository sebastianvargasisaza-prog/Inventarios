# calidad_html.py Ã¢ÂÂ extraÃÂ­do de index.py (Fase C prep)
CALIDAD_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Calidad BPM Ã¢ÂÂ Espagiria</title>
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
<div class="topbar">
  <span class="logo">ESPAGIRIA</span>
  <span class="badge">CALIDAD BPM</span>
  <a href="/">&#8592; Inicio</a>
</div>
<div class="tabs">
  <div class="tab active" onclick="goTab('tab-dash')">&#128202; Dashboard</div>
  <div class="tab" onclick="goTab('tab-cron')">&#128203; Cronograma del Dia</div>
  <div class="tab" onclick="goTab('tab-cc')">&#x1F9EA; Control Calidad MP</div>
  <div class="tab" onclick="goTab('tab-nc')">&#x26A0; No Conformidades</div>
  <div class="tab" onclick="goTab('tab-cal')">&#x1F527; Calibraciones</div>
  
</div>
<div class="main">

<!-- Ã¢ÂÂÃ¢ÂÂ DASHBOARD Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ -->
<div id="tab-dash" class="pane active">
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
    <div class="card-title">Historial de No Conformidades</div>
    <table>
      <thead><tr><th>ID</th><th>Fecha</th><th>Tipo</th><th>Area</th><th>Descripcion</th><th>Impacto</th><th>Estado</th><th>Accion</th></tr></thead>
      <tbody id="nc-tbody"><tr><td colspan="8" class="empty">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>

<!-- Ã¢ÂÂÃ¢ÂÂ CALIBRACIONES Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ -->
<div id="tab-cal" class="pane">
  <div class="card">
    <div class="card-title">Instrumentos y Equipos Ã¢ÂÂ Estado de Calibracion</div>
    <table>
      <thead><tr><th>Instrumento</th><th>Codigo</th><th>Ubicacion</th><th>Ultima Cal.</th><th>Proxima Cal.</th><th>Responsable</th><th>Certificado</th><th>Estado</th></tr></thead>
      <tbody id="cal-tbody"><tr><td colspan="8" class="empty">Cargando...</td></tr></tbody>
    </table>
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

var _tabIds=['tab-dash','tab-cron','tab-cc','tab-nc','tab-cal'];
function goTab(id){
  document.querySelectorAll('.tab').forEach((t,i)=>{t.classList.toggle('active',_tabIds[i]===id);});
  document.querySelectorAll('.pane').forEach(p=>p.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  if(id==='tab-dash') loadDash();
  else if(id==='tab-cron') loadCronograma();
  else if(id==='tab-cc') loadCuarentena();
  else if(id==='tab-nc') loadNC();
  else if(id==='tab-cal') loadCal();
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
    document.getElementById('kv-lib-mes').textContent=d.liberados_mes\!=null?d.liberados_mes:'-';
    var tasa=d.tasa_liberacion;
    var tasaEl=document.getElementById('kv-tasa-lib');
    if(tasa\!=null){tasaEl.textContent=tasa+'%';tasaEl.className='kpi-val '+(tasa>=90?'good':(tasa>=70?'warn':'crit'));}
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
    await fetch('/api/calidad/cronograma/iniciar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tarea_id:parseInt(tid),fecha:_crDate})});
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
    const r=await fetch('/api/calidad/cronograma/completar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
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
    const r=await fetch('/api/recepcion/aprobar-lote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mov_id:movId,estado})});
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
    const r=await fetch('/api/calidad/no-conformidades',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(r.ok){['nc-desc','nc-responsable','nc-lote','nc-mp','nc-accion'].forEach(id=>document.getElementById(id).value='');loadNC();}
    else{const d=await r.json();alert(d.error||'Error al registrar');}
  }catch(e){alert('Error: '+e.message);}
}

async function loadNC(){
  const tbody=document.getElementById('nc-tbody');
  try{
    const r=await fetch('/api/calidad/no-conformidades');
    const rows=await r.json();
    if(!rows.length){tbody.innerHTML='<tr><td colspan="8" class="empty">No hay no conformidades registradas</td></tr>';return;}
    tbody.innerHTML=rows.map(nc=>{
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
    const r=await fetch('/api/calidad/no-conformidades/'+ncid+'/cerrar',{method:'POST'});
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
    if(!rows.length){tbody.innerHTML='<tr><td colspan="8" class="empty">No hay instrumentos registrados</td></tr>';return;}
    tbody.innerHTML=rows.map(c=>{
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