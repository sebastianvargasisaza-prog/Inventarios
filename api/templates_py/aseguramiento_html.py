"""Template HTML del módulo Aseguramiento (ASG).

Pestañas:
- Dashboard ASG (KPIs)
- SGD electrónico (los 124 docs centralizados)
- Capacitaciones (firma SOPs)
- Conflictos (códigos repetidos detectados)
- Mis capacitaciones (vista del usuario actual)

Pestañas que MIGRARÁN desde /calidad (futuro):
- No Conformidades
- Auditorías
- CAPA
"""

ASEGURAMIENTO_HTML = r'''<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="google" content="notranslate">
<meta http-equiv="Content-Language" content="es">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes, viewport-fit=cover">
<title>Aseguramiento de Calidad · EOS</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos12">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
:root{--bg:#0f172a;--card:#1e293b;--text:#e2e8f0;--muted:#94a3b8;--accent:#7ACFCC;--good:#15803d;--warn:#fbbf24;--crit:#ef4444}
body{font-family:system-ui,-apple-system,sans-serif;background:#f8fafc;margin:0;color:#0f172a}
header{background:#0f172a;color:#f1f5f9;padding:14px 24px;display:flex;justify-content:space-between;align-items:center}
.logo{font-weight:800;letter-spacing:.5px;font-size:1.05em;color:#7ACFCC}
.tabs{display:flex;gap:0;background:#1e293b;border-bottom:1px solid #334155;padding:0 24px;flex-wrap:wrap;overflow-x:auto}
.tab{padding:11px 20px;font-size:0.78em;font-weight:700;letter-spacing:.5px;color:#64748b;cursor:pointer;border-bottom:2px solid transparent;text-transform:uppercase;white-space:nowrap}
.tab.active{color:#7ACFCC;border-bottom-color:#7ACFCC}
.tab:hover{color:#cbd5e1}
.main{padding:18px 24px;max-width:1400px;margin:0 auto}
.pane{display:none}.pane.active{display:block}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:14px;margin-bottom:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.card-title{font-size:1em;font-weight:700;color:#0f172a;margin-bottom:8px}
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:14px}
.kpi{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:10px;text-align:center}
.kpi-label{font-size:0.72em;color:#64748b;text-transform:uppercase;letter-spacing:.5px}
.kpi-val{font-size:1.6em;font-weight:800;color:#0f172a;margin-top:2px}
.kpi-val.good{color:#15803d}.kpi-val.warn{color:#fbbf24}.kpi-val.crit{color:#ef4444}
.kpi-sub{font-size:0.7em;color:#94a3b8;margin-top:2px}
table{width:100%;border-collapse:collapse;font-size:0.85em}
th,td{padding:6px 8px;border-bottom:1px solid #f1f5f9;text-align:left;vertical-align:top}
th{background:#f8fafc;font-weight:700;color:#475569;font-size:0.76em;text-transform:uppercase;letter-spacing:.5px}
tr:hover{background:#fafafa}
.empty{text-align:center;color:#94a3b8;padding:14px;font-style:italic}
.btn{padding:6px 14px;border:none;border-radius:6px;cursor:pointer;font-size:0.85em;font-weight:600}
.btn-primary{background:#7ACFCC;color:#0f172a}.btn-primary:hover{background:#5fb8b5}
.btn-ghost{background:#f1f5f9;color:#475569;border:1px solid #cbd5e1}
.btn-ghost:hover{background:#e2e8f0}
.btn-sm{padding:4px 10px;font-size:0.78em}
.form-group{margin-bottom:8px}
.form-group label{display:block;font-size:0.78em;color:#475569;font-weight:600;margin-bottom:2px}
.form-group input,.form-group select,.form-group textarea{width:100%;padding:6px 10px;border:1px solid #cbd5e1;border-radius:4px;font-size:0.9em;background:#fff;box-sizing:border-box}
.form-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:10px}
.modal-overlay{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.5);display:none;align-items:center;justify-content:center;z-index:9999;padding:20px}
.modal-overlay.open{display:flex}
.modal{background:#fff;border-radius:10px;padding:22px;max-width:600px;width:100%;max-height:88vh;overflow-y:auto;position:relative}
.modal-close{position:absolute;top:8px;right:8px;background:none;border:none;font-size:24px;cursor:pointer;color:#64748b;width:32px;height:32px;line-height:32px;border-radius:50%}
.modal-close:hover{background:#f1f5f9}
.modal-title{font-size:1.1em;font-weight:700;margin-bottom:14px;color:#0f172a}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:0.72em;font-weight:700;text-transform:uppercase}
.badge-vig{background:#d1fae5;color:#15803d}
.badge-venc{background:#fef2f2;color:#ef4444}
.badge-prox{background:#fef9c3;color:#a16207}
.badge-obs{background:#f3f4f6;color:#6b7280}
.badge-confl{background:#ffedd5;color:#c2410c}
.badge-bor{background:#dbeafe;color:#1e40af}
code{background:#f1f5f9;padding:1px 6px;border-radius:3px;font-family:SFMono-Regular,Consolas,monospace;font-size:0.85em}
</style>
</head>
<body>
<header>
  <div class="logo">EOS · ASEGURAMIENTO DE CALIDAD</div>
  <div style="display:flex;gap:10px;align-items:center">
    <a href="/calidad" class="btn btn-ghost btn-sm">&larr; Calidad</a>
    <a href="/" class="btn btn-ghost btn-sm">Inicio</a>
  </div>
</header>

<div class="tabs">
  <div class="tab active" onclick="goTab('tab-dash')">&#x1F4CA; Dashboard</div>
  <div class="tab" onclick="goTab('tab-sgd')">&#x1F4DA; SGD electrónico</div>
  <div class="tab" onclick="goTab('tab-cap')">&#x1F393; Capacitaciones</div>
  <div class="tab" onclick="goTab('tab-mis-cap')">&#x270D;&#xFE0F; Mis firmas</div>
  <div class="tab" onclick="goTab('tab-desv')">&#x1F4E2; Desviaciones</div>
  <div class="tab" onclick="goTab('tab-conf')">&#x26A0;&#xFE0F; Conflictos SGD</div>
</div>

<div class="main">

<!-- DASHBOARD -->
<div id="tab-dash" class="pane active">
  <div class="kpi-row" id="dash-kpis">
    <div class="kpi"><div class="kpi-label">Docs Vigentes</div><div class="kpi-val good" id="kp-vig">—</div></div>
    <div class="kpi"><div class="kpi-label">Vencen 30d</div><div class="kpi-val warn" id="kp-prox">—</div></div>
    <div class="kpi"><div class="kpi-label">Vencidos</div><div class="kpi-val crit" id="kp-venc">—</div></div>
    <div class="kpi"><div class="kpi-label">Conflictos</div><div class="kpi-val warn" id="kp-confl">—</div></div>
    <div class="kpi"><div class="kpi-label">Capacit. pendientes</div><div class="kpi-val warn" id="kp-cap">—</div></div>
    <div class="kpi"><div class="kpi-label">NCs abiertas</div><div class="kpi-val" id="kp-nc">—</div></div>
    <div class="kpi"><div class="kpi-label">Auditorías 60d</div><div class="kpi-val" id="kp-aud">—</div></div>
  </div>
  <div class="card">
    <div class="card-title">Resumen del SGD por área</div>
    <div id="dash-areas"><p class="empty">Cargando...</p></div>
  </div>
</div>

<!-- SGD ELECTRÓNICO -->
<div id="tab-sgd" class="pane">
  <div class="card">
    <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px">
      <input id="sgd-q" placeholder="Buscar por código o título" style="flex:1;min-width:200px;padding:6px 10px;border:1px solid #cbd5e1;border-radius:4px">
      <select id="sgd-area" onchange="loadSGD()" style="padding:6px 10px;border:1px solid #cbd5e1;border-radius:4px">
        <option value="">Todas áreas</option>
        <option value="COC">COC · Control Calidad</option>
        <option value="ASG">ASG · Aseguramiento</option>
        <option value="ADM">ADM · Administración</option>
        <option value="BDG">BDG · Bodega</option>
        <option value="GER">GER · Gerencia</option>
        <option value="PRD">PRD · Producción</option>
        <option value="RRH">RRH · Recursos Humanos</option>
        <option value="SST">SST · Seguridad</option>
      </select>
      <select id="sgd-tipo" onchange="loadSGD()" style="padding:6px 10px;border:1px solid #cbd5e1;border-radius:4px">
        <option value="">Todos tipos</option>
        <option value="PRO">Procedimientos</option>
        <option value="NOR">Normas</option>
        <option value="MAN">Manuales</option>
        <option value="INS">Instructivos</option>
        <option value="POL">Políticas</option>
        <option value="FOR">Formatos</option>
        <option value="LMA">Listados maestros</option>
      </select>
      <select id="sgd-estado" onchange="loadSGD()" style="padding:6px 10px;border:1px solid #cbd5e1;border-radius:4px">
        <option value="vigente">Vigentes</option>
        <option value="">Todos estados</option>
        <option value="borrador">Borrador</option>
        <option value="obsoleto">Obsoletos</option>
        <option value="conflicto">Conflicto</option>
      </select>
      <label style="display:flex;align-items:center;gap:4px;font-size:0.85em;color:#475569">
        <input type="checkbox" id="sgd-hijos" onchange="loadSGD()"> Incluir formatos hijos
      </label>
      <button class="btn btn-ghost btn-sm" onclick="loadSGD()">&#x1F50D; Buscar</button>
      <button class="btn btn-primary btn-sm" onclick="abrirNuevoSGD()">+ Nuevo</button>
    </div>
    <div id="sgd-resumen" style="font-size:0.78em;color:#64748b;margin-bottom:6px"></div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Código</th><th>Título</th><th>Versión</th><th>Estado</th><th>Próx. revisión</th><th>Aprobado por</th><th></th></tr></thead>
        <tbody id="sgd-tbody"><tr><td colspan="7" class="empty">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- CAPACITACIONES (asignación / supervisión) -->
<div id="tab-cap" class="pane">
  <div class="card">
    <div class="card-title">Asignar lectura/firma de un SOP</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px">
      <div class="form-group"><label>Código SGD *</label><input id="cap-codigo" placeholder="COC-PRO-001"></div>
      <div class="form-group"><label>Versión *</label><input id="cap-version" placeholder="v02"></div>
      <div class="form-group"><label>Fecha límite</label><input id="cap-fecha-lim" type="date"></div>
    </div>
    <div class="form-group"><label>Personas (usernames separados por coma)</label>
      <input id="cap-personas" placeholder="laura, miguel, yuliel">
    </div>
    <div style="text-align:right">
      <button class="btn btn-primary" onclick="asignarCap()">Asignar</button>
    </div>
    <div id="cap-msg" style="margin-top:8px;font-size:12px"></div>
  </div>
</div>

<!-- MIS CAPACITACIONES (vista del usuario actual) -->
<div id="tab-mis-cap" class="pane">
  <div class="card">
    <div class="card-title">Mis capacitaciones pendientes</div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Código</th><th>Versión</th><th>Documento</th><th>Asignada</th><th>Estado</th><th>Acción</th></tr></thead>
        <tbody id="mis-cap-tbody"><tr><td colspan="6" class="empty">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- DESVIACIONES · ASG-PRO-001 -->
<div id="tab-desv" class="pane">
  <div class="kpi-row" id="desv-kpis">
    <div class="kpi"><div class="kpi-label">Total</div><div class="kpi-val" id="desv-kp-tot">—</div></div>
    <div class="kpi"><div class="kpi-label">Críticas abiertas</div><div class="kpi-val crit" id="desv-kp-crit">—</div></div>
    <div class="kpi"><div class="kpi-label">Sin clasificar</div><div class="kpi-val warn" id="desv-kp-sin">—</div></div>
    <div class="kpi"><div class="kpi-label">Investigando</div><div class="kpi-val" id="desv-kp-inv">—</div></div>
    <div class="kpi"><div class="kpi-label">Cerradas 30d</div><div class="kpi-val good" id="desv-kp-cer">—</div></div>
  </div>

  <div class="card" style="margin-bottom:14px">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">
      <div class="card-title" style="margin:0">Lista</div>
      <div style="display:flex;gap:6px;align-items:center;font-size:12px">
        <select id="desv-f-estado" onchange="loadDesviaciones()">
          <option value="">Todos estados</option>
          <option value="detectada">Detectadas</option>
          <option value="clasificada">Clasificadas</option>
          <option value="en_investigacion">En investigación</option>
          <option value="capa_propuesto">CAPA propuesto</option>
          <option value="capa_implementado">CAPA implementado</option>
          <option value="cerrada">Cerradas</option>
        </select>
        <select id="desv-f-clasif" onchange="loadDesviaciones()">
          <option value="">Toda clasificación</option>
          <option value="critica">Crítica</option>
          <option value="mayor">Mayor</option>
          <option value="menor">Menor</option>
          <option value="informativa">Informativa</option>
        </select>
        <button class="btn btn-ghost btn-sm" onclick="loadDesviaciones()">↻</button>
        <button class="btn btn-primary btn-sm" onclick="abrirNuevaDesviacion()">+ Nueva</button>
      </div>
    </div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Código</th><th>Fecha</th><th>Tipo</th><th>Área</th><th>Descripción</th><th>Clasif.</th><th>Estado</th><th>Días</th><th></th></tr></thead>
        <tbody id="desv-tbody"><tr><td colspan="9" class="empty">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- Modal nueva desviación -->
<div class="modal-overlay" id="m-desv-new">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('m-desv-new')">&times;</button>
    <div class="modal-title">Reportar desviación</div>
    <div class="form-group"><label>Tipo *</label>
      <select id="m-desv-tipo">
        <option value="proceso">Proceso</option>
        <option value="equipo">Equipo</option>
        <option value="instalacion">Instalación</option>
        <option value="sistema_agua">Sistema de agua</option>
        <option value="ambiental">Ambiental (T/HR)</option>
        <option value="documental">Documental</option>
        <option value="personal">Personal</option>
        <option value="materia_prima">Materia prima</option>
        <option value="envase">Envase/empaque</option>
        <option value="otra">Otra</option>
      </select>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>Área origen</label><input id="m-desv-area" placeholder="Fab1, Disp, Lab..."></div>
      <div class="form-group"><label>Hora detección</label><input id="m-desv-hora" type="time"></div>
    </div>
    <div class="form-group"><label>Descripción * (≥10 chars)</label><textarea id="m-desv-desc" style="min-height:70px" placeholder="Qué pasó · cuándo · cómo se detectó"></textarea></div>
    <div class="form-group"><label>Contención inmediata</label><textarea id="m-desv-cont" style="min-height:50px" placeholder="Qué se hizo de inmediato para contener"></textarea></div>
    <div class="form-group"><label><input type="checkbox" id="m-desv-impacto"> Impacta producto / lote en proceso</label></div>
    <div class="form-group"><label>Lotes afectados (si aplica)</label><input id="m-desv-lotes" placeholder="LOTE-001, LOTE-002..."></div>
    <div class="form-actions">
      <button class="btn btn-ghost" onclick="closeModal('m-desv-new')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarDesviacion()">Reportar</button>
    </div>
    <div id="m-desv-new-msg" style="margin-top:8px;font-size:12px"></div>
  </div>
</div>

<!-- Modal detalle desviación + workflow -->
<div class="modal-overlay" id="m-desv-det">
  <div class="modal" style="max-width:900px">
    <button class="modal-close" onclick="closeModal('m-desv-det')">&times;</button>
    <div class="modal-title" id="m-desv-det-title">Detalle</div>
    <input type="hidden" id="m-desv-det-id">
    <div id="m-desv-det-body"><p class="empty">Cargando...</p></div>
  </div>
</div>

<!-- CONFLICTOS SGD -->
<div id="tab-conf" class="pane">
  <div class="card">
    <div class="card-title">&#x26A0;&#xFE0F; Conflictos detectados (códigos repetidos con temas distintos)</div>
    <div style="font-size:0.85em;color:#64748b;margin-bottom:8px">Estos códigos del SGD físico aparecen con temas diferentes en los archivos · resolver eligiendo qué tema queda con el código original.</div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Código</th><th>Temas detectados</th><th>Estado</th><th>Resolución</th><th></th></tr></thead>
        <tbody id="conf-tbody"><tr><td colspan="5" class="empty">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- Modal nuevo SGD -->
<div class="modal-overlay" id="m-sgd">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('m-sgd')">&times;</button>
    <div class="modal-title" id="m-sgd-title">Nuevo documento SGD</div>
    <div class="form-group"><label>Código (AAA-BBB-NNN[-FNN]) *</label>
      <input id="m-sgd-codigo" placeholder="COC-PRO-018">
    </div>
    <div class="form-group"><label>Título *</label>
      <input id="m-sgd-titulo" placeholder="Ej: Control de envases primarios">
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>Versión</label><input id="m-sgd-version" value="1"></div>
      <div class="form-group"><label>Estado</label>
        <select id="m-sgd-estado">
          <option value="vigente">Vigente</option>
          <option value="borrador">Borrador</option>
          <option value="revision">En revisión</option>
        </select>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="form-group"><label>Vigente desde</label><input id="m-sgd-vigente" type="date"></div>
      <div class="form-group"><label>Próxima revisión</label><input id="m-sgd-proxrev" type="date"></div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px">
      <div class="form-group"><label>Elaborado por</label><input id="m-sgd-elab"></div>
      <div class="form-group"><label>Revisado por</label><input id="m-sgd-rev"></div>
      <div class="form-group"><label>Aprobado por</label><input id="m-sgd-apr"></div>
    </div>
    <div class="form-group"><label>URL del PDF</label><input id="m-sgd-url" placeholder="opcional"></div>
    <div class="form-group"><label>Observaciones / motivo del cambio</label><textarea id="m-sgd-obs" style="min-height:60px"></textarea></div>
    <div class="form-actions">
      <button class="btn btn-ghost" onclick="closeModal('m-sgd')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarSGD()">Guardar</button>
    </div>
    <div id="m-sgd-msg" style="margin-top:8px;font-size:12px"></div>
  </div>
</div>

<!-- Modal detalle SGD -->
<div class="modal-overlay" id="m-sgd-det">
  <div class="modal" style="max-width:900px">
    <button class="modal-close" onclick="closeModal('m-sgd-det')">&times;</button>
    <div class="modal-title" id="m-sgd-det-title">Detalle</div>
    <div id="m-sgd-det-body"><p class="empty">Cargando...</p></div>
  </div>
</div>

</div>
<script>
function _esc(s){return String(s||'').replace(/[&<>"']/g,function(ch){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];});}
function openModal(id){document.getElementById(id).classList.add('open');}
function closeModal(id){document.getElementById(id).classList.remove('open');}

var _tabIds = ['tab-dash','tab-sgd','tab-cap','tab-mis-cap','tab-desv','tab-conf'];
function goTab(id){
  document.querySelectorAll('.tab').forEach((t,i)=>{t.classList.toggle('active',_tabIds[i]===id);});
  document.querySelectorAll('.pane').forEach(p=>p.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  if(id==='tab-dash') loadDashboard();
  else if(id==='tab-sgd') loadSGD();
  else if(id==='tab-mis-cap') loadMisCapacitaciones();
  else if(id==='tab-desv') loadDesviaciones();
  else if(id==='tab-conf') loadConflictos();
}

// === DESVIACIONES (ASG-PRO-001) ========================================
async function loadDesviaciones(){
  var estado = document.getElementById('desv-f-estado').value;
  var clasif = document.getElementById('desv-f-clasif').value;
  var qs = [];
  if(estado) qs.push('estado='+estado);
  if(clasif) qs.push('clasificacion='+clasif);
  var url = '/api/aseguramiento/desviaciones' + (qs.length ? '?'+qs.join('&') : '');
  try{
    var r = await fetch(url);
    var d = await r.json();
    var k = d.kpis || {};
    document.getElementById('desv-kp-tot').textContent = k.total || 0;
    document.getElementById('desv-kp-crit').textContent = k.criticas_abiertas || 0;
    document.getElementById('desv-kp-sin').textContent = k.sin_clasificar || 0;
    document.getElementById('desv-kp-inv').textContent = k.investigando || 0;
    document.getElementById('desv-kp-cer').textContent = k.cerradas_30d || 0;
    var tb = document.getElementById('desv-tbody');
    if(!d.items || !d.items.length){ tb.innerHTML = '<tr><td colspan="9" class="empty">Sin desviaciones</td></tr>'; return; }
    tb.innerHTML = d.items.map(function(it){
      var clasifBadge = it.clasificacion === 'critica' ? '<span class="badge badge-venc">crítica</span>'
        : it.clasificacion === 'mayor' ? '<span class="badge badge-prox">mayor</span>'
        : it.clasificacion === 'menor' ? '<span class="badge badge-bor">menor</span>'
        : it.clasificacion === 'informativa' ? '<span class="badge badge-obs">info</span>'
        : '<span style="color:#94a3b8;font-size:0.78em">—</span>';
      var estadoLabel = (it.estado||'').replace('_',' ');
      var estadoCol = it.estado === 'cerrada' ? '#15803d'
        : it.estado === 'rechazada' ? '#94a3b8'
        : it.estado === 'detectada' ? '#ef4444'
        : '#fbbf24';
      var icono = it.impacto_producto ? '⚠ ' : '';
      return '<tr>'
        +'<td><b><code>'+_esc(it.codigo)+'</code></b></td>'
        +'<td>'+_esc(it.fecha_deteccion||'')+(it.hora_deteccion?' '+_esc(it.hora_deteccion):'')+'</td>'
        +'<td>'+_esc(it.tipo||'')+'</td>'
        +'<td>'+_esc(it.area_origen||'')+'</td>'
        +'<td>'+icono+_esc((it.descripcion||'').slice(0,80))+(it.descripcion && it.descripcion.length > 80 ? '...' : '')+'</td>'
        +'<td>'+clasifBadge+'</td>'
        +'<td><span style="color:'+estadoCol+';font-weight:600;font-size:0.85em">'+_esc(estadoLabel)+'</span></td>'
        +'<td>'+(it.dias_abierta||0)+'d</td>'
        +'<td><button class="btn btn-ghost btn-sm" onclick="verDesviacion('+it.id+')">Abrir</button></td>'
        +'</tr>';
    }).join('');
  }catch(e){ document.getElementById('desv-tbody').innerHTML = '<tr><td colspan="9" class="empty">Error: '+_esc(e.message)+'</td></tr>'; }
}

function abrirNuevaDesviacion(){
  ['m-desv-area','m-desv-desc','m-desv-cont','m-desv-lotes','m-desv-new-msg'].forEach(function(id){
    var el = document.getElementById(id); if(el) el.value = '';
  });
  document.getElementById('m-desv-impacto').checked = false;
  document.getElementById('m-desv-hora').value = new Date().toTimeString().slice(0,5);
  openModal('m-desv-new');
}

async function guardarDesviacion(){
  var msg = document.getElementById('m-desv-new-msg');
  var body = {
    tipo: document.getElementById('m-desv-tipo').value,
    area_origen: document.getElementById('m-desv-area').value,
    hora_deteccion: document.getElementById('m-desv-hora').value,
    descripcion: document.getElementById('m-desv-desc').value,
    contencion_inmediata: document.getElementById('m-desv-cont').value,
    impacto_producto: document.getElementById('m-desv-impacto').checked,
    lotes_afectados: document.getElementById('m-desv-lotes').value,
  };
  if(!body.descripcion || body.descripcion.length < 10){
    msg.innerHTML = '<span style="color:#ef4444">Descripción requerida (≥10 chars)</span>'; return;
  }
  msg.innerHTML = '<span style="color:#64748b">Guardando...</span>';
  try{
    var r = await fetch('/api/aseguramiento/desviaciones', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if(d.ok){
      msg.innerHTML = '<span style="color:#15803d">&#x2705; '+_esc(d.codigo)+' creada</span>';
      setTimeout(function(){ closeModal('m-desv-new'); loadDesviaciones(); }, 700);
    } else { msg.innerHTML = '<span style="color:#ef4444">Error: '+_esc(d.error||'?')+'</span>'; }
  }catch(e){ msg.innerHTML = '<span style="color:#ef4444">Error red: '+_esc(e.message)+'</span>'; }
}

async function verDesviacion(id){
  document.getElementById('m-desv-det-id').value = id;
  var body = document.getElementById('m-desv-det-body');
  body.innerHTML = '<p class="empty">Cargando...</p>';
  openModal('m-desv-det');
  try{
    var r = await fetch('/api/aseguramiento/desviaciones/'+id);
    var d = await r.json();
    if(!r.ok){ body.innerHTML = '<p class="empty" style="color:#c00">'+_esc(d.error||'?')+'</p>'; return; }
    document.getElementById('m-desv-det-title').textContent = d.codigo + ' · ' + (d.estado||'').replace('_',' ');

    var html = '<div class="card" style="background:#f8fafc">'
      +'<div style="font-size:0.85em;color:#475569"><b>Detectada:</b> '+_esc(d.fecha_deteccion||'')+' '+_esc(d.hora_deteccion||'')+' · por '+_esc(d.detectado_por||'')+'</div>'
      +'<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Tipo:</b> '+_esc(d.tipo||'')+' · <b>Área:</b> '+_esc(d.area_origen||'—')+'</div>'
      +'<div style="margin-top:8px"><b>Descripción:</b><br>'+_esc(d.descripcion||'')+'</div>'
      +(d.contencion_inmediata ? '<div style="margin-top:6px"><b>Contención:</b><br>'+_esc(d.contencion_inmediata)+'</div>' : '')
      +(d.impacto_producto ? '<div style="margin-top:6px;color:#ef4444">⚠ <b>Impacta producto</b> · Lotes: '+_esc(d.lotes_afectados||'?')+'</div>' : '')
      +'</div>';

    // Workflow steps
    html += '<div class="card-title" style="margin-top:12px">Workflow</div>';

    // Paso 1: Clasificación
    if(d.clasificacion){
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid #15803d">'
        +'<div><b>1. Clasificada</b> como <b>'+_esc(d.clasificacion)+'</b></div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px">'+_esc(d.justificacion_clasificacion||'')+'</div>'
        +'<div style="font-size:0.78em;color:#94a3b8">por '+_esc(d.clasificado_por||'')+' · '+_esc(d.clasificado_at||'')+'</div>'
        +'</div>';
    } else {
      html += '<div class="card" style="background:#fef2f2;border-left:3px solid #ef4444">'
        +'<div><b>1. Clasificar</b> (pendiente)</div>'
        +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:6px">'
        +'<select id="cl-clasif" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px"><option value="">--</option><option value="critica">Crítica</option><option value="mayor">Mayor</option><option value="menor">Menor</option><option value="informativa">Informativa</option></select>'
        +'<input id="cl-just" placeholder="Justificación (≥10 chars)" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px">'
        +'</div>'
        +'<div style="text-align:right;margin-top:6px"><button class="btn btn-primary btn-sm" onclick="clasificarDesv('+id+')">Clasificar</button></div>'
        +'</div>';
    }

    // Paso 2: Investigación
    if(d.causa_raiz_descripcion){
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid #15803d">'
        +'<div><b>2. Investigada</b> · método: <b>'+_esc(d.metodo_investigacion||'')+'</b></div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Causa raíz:</b><br>'+_esc(d.causa_raiz_descripcion||'')+'</div>'
        +'<div style="font-size:0.78em;color:#94a3b8">por '+_esc(d.investigado_por||'')+' · '+_esc(d.investigacion_at||'')+'</div>'
        +'</div>';
    } else if(d.clasificacion){
      html += '<div class="card" style="background:#fefce8;border-left:3px solid #fbbf24">'
        +'<div><b>2. Investigar causa raíz</b> (pendiente)</div>'
        +'<div style="display:grid;grid-template-columns:1fr 2fr;gap:8px;margin-top:6px">'
        +'<select id="inv-metodo" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px"><option value="5_porques">5 Porqués</option><option value="ishikawa">Ishikawa</option><option value="arbol_decision">Árbol decisión</option><option value="otro">Otro</option></select>'
        +'<textarea id="inv-causa" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px;min-height:50px" placeholder="Causa raíz (≥20 chars)"></textarea>'
        +'</div>'
        +'<div style="text-align:right;margin-top:6px"><button class="btn btn-primary btn-sm" onclick="investigarDesv('+id+')">Registrar investigación</button></div>'
        +'</div>';
    }

    // Paso 3: CAPA
    if(d.capa_descripcion){
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid #15803d">'
        +'<div><b>3. CAPA propuesto</b></div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px">'+_esc(d.capa_descripcion||'')+'</div>'
        +'<div style="font-size:0.78em;color:#94a3b8">Resp: '+_esc(d.capa_responsable||'?')+' · Límite: '+_esc(d.capa_fecha_limite||'sin definir')+'</div>'
        +'</div>';
    } else if(d.causa_raiz_descripcion){
      html += '<div class="card" style="background:#fefce8;border-left:3px solid #fbbf24">'
        +'<div><b>3. Definir CAPA</b> (pendiente)</div>'
        +'<div class="form-group"><label>Descripción de acciones (≥20 chars)</label><textarea id="capa-desc" style="min-height:50px"></textarea></div>'
        +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">'
        +'<input id="capa-resp" placeholder="Responsable" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px">'
        +'<input id="capa-fecha" type="date" style="padding:6px;border:1px solid #cbd5e1;border-radius:4px">'
        +'</div>'
        +'<div style="text-align:right;margin-top:6px"><button class="btn btn-primary btn-sm" onclick="capaDesv('+id+')">Guardar CAPA</button></div>'
        +'</div>';
    }

    // Paso 4: Cierre
    if(d.estado === 'cerrada'){
      var efCol = d.efectividad_ok ? '#15803d' : '#ef4444';
      var efLabel = d.efectividad_ok ? '✅ EFECTIVIDAD OK' : '❌ EFECTIVIDAD NO OK';
      html += '<div class="card" style="background:#f0fdf4;border-left:3px solid '+efCol+'">'
        +'<div style="font-size:1em;font-weight:700;color:'+efCol+'">'+efLabel+'</div>'
        +'<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Verificación:</b> '+_esc(d.verificacion_efectividad||'')+'</div>'
        +(d.observaciones_cierre ? '<div style="font-size:0.85em;color:#475569;margin-top:4px"><b>Observaciones:</b> '+_esc(d.observaciones_cierre)+'</div>' : '')
        +'<div style="font-size:0.78em;color:#94a3b8;margin-top:4px">Cerrada '+_esc(d.fecha_cierre||'')+' por '+_esc(d.cerrado_por||'')+'</div>'
        +'</div>';
    } else if(d.capa_descripcion){
      html += '<div class="card" style="background:#fef2f2;border-left:3px solid #ef4444">'
        +'<div><b>4. Cerrar con verificación</b></div>'
        +'<div class="form-group"><label>Verificación de efectividad (≥20 chars)</label><textarea id="cer-verif" style="min-height:50px"></textarea></div>'
        +'<div class="form-group"><label><input type="checkbox" id="cer-ok"> CAPA fue efectiva</label></div>'
        +'<div class="form-group"><label>Observaciones cierre</label><input id="cer-obs"></div>'
        +'<div style="text-align:right"><button class="btn btn-primary btn-sm" onclick="cerrarDesv('+id+')">Cerrar desviación</button></div>'
        +'</div>';
    }

    // Timeline
    if(d.timeline && d.timeline.length){
      html += '<div class="card-title" style="margin-top:12px">Timeline</div>';
      html += '<div style="font-size:0.85em">';
      d.timeline.forEach(function(ev){
        html += '<div style="border-left:2px solid #cbd5e1;padding:4px 0 4px 10px;margin-bottom:4px">'
          +'<div style="font-weight:600">'+_esc(ev.evento_tipo)+(ev.estado_anterior ? ' · '+_esc(ev.estado_anterior)+'→'+_esc(ev.estado_nuevo) : '')+'</div>'
          +'<div style="color:#475569">'+_esc(ev.comentario||'')+'</div>'
          +'<div style="color:#94a3b8;font-size:0.85em">'+_esc(ev.usuario||'')+' · '+_esc(ev.creado_en||'')+'</div>'
          +'</div>';
      });
      html += '</div>';
    }
    body.innerHTML = html;
  }catch(e){ body.innerHTML = '<p class="empty" style="color:#c00">Error: '+_esc(e.message)+'</p>'; }
}

async function clasificarDesv(id){
  var clasif = document.getElementById('cl-clasif').value;
  var just = document.getElementById('cl-just').value;
  if(!clasif){ alert('Elige clasificación'); return; }
  if(!just || just.length < 10){ alert('Justificación ≥10 chars'); return; }
  await _postDesvAccion(id, 'clasificar', {clasificacion: clasif, justificacion: just});
}

async function investigarDesv(id){
  var metodo = document.getElementById('inv-metodo').value;
  var causa = document.getElementById('inv-causa').value;
  if(!causa || causa.length < 20){ alert('Causa raíz ≥20 chars'); return; }
  await _postDesvAccion(id, 'investigar', {metodo_investigacion: metodo, causa_raiz: causa});
}

async function capaDesv(id){
  var desc = document.getElementById('capa-desc').value;
  var resp = document.getElementById('capa-resp').value;
  var fecha = document.getElementById('capa-fecha').value;
  if(!desc || desc.length < 20){ alert('Descripción CAPA ≥20 chars'); return; }
  if(!resp){ alert('Responsable requerido'); return; }
  await _postDesvAccion(id, 'capa', {capa_descripcion: desc, capa_responsable: resp, capa_fecha_limite: fecha});
}

async function cerrarDesv(id){
  var verif = document.getElementById('cer-verif').value;
  var ok = document.getElementById('cer-ok').checked;
  var obs = document.getElementById('cer-obs').value;
  if(!verif || verif.length < 20){ alert('Verificación efectividad ≥20 chars'); return; }
  if(!confirm('Confirmas cerrar esta desviación con efectividad ' + (ok ? 'OK' : 'NO OK') + '?')) return;
  await _postDesvAccion(id, 'cerrar', {efectividad_ok: ok, verificacion_efectividad: verif, observaciones_cierre: obs});
}

async function _postDesvAccion(id, accion, body){
  try{
    var r = await fetch('/api/aseguramiento/desviaciones/'+id+'/'+accion, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if(d.ok){ verDesviacion(id); loadDesviaciones(); }
    else alert('Error: '+(d.error||'?'));
  }catch(e){ alert('Error red: '+e.message); }
}

async function loadDashboard(){
  try{
    var r = await fetch('/api/aseguramiento/dashboard');
    var d = await r.json();
    var sgd = d.sgd || {};
    var cap = d.capacitaciones || {};
    document.getElementById('kp-vig').textContent = sgd.vigentes || 0;
    document.getElementById('kp-prox').textContent = sgd.vencen_30d || 0;
    document.getElementById('kp-venc').textContent = sgd.vencidos || 0;
    document.getElementById('kp-confl').textContent = sgd.conflictos || 0;
    document.getElementById('kp-cap').textContent = cap.pendientes || 0;
    document.getElementById('kp-nc').textContent = d.ncs_abiertas || 0;
    document.getElementById('kp-aud').textContent = d.auditorias_60d || 0;

    // Resumen áreas vendrá del listado
    var rArea = await fetch('/api/aseguramiento/sgd/listado?estado=vigente');
    var dArea = await rArea.json();
    var areas = dArea.resumen_por_area || {};
    var div = document.getElementById('dash-areas');
    var html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px">';
    Object.keys(areas).sort().forEach(function(a){
      html += '<div style="background:#f8fafc;padding:10px;border-radius:6px;text-align:center">'
        +'<div style="font-size:0.72em;color:#64748b">'+_esc(dArea.areas[a]||a)+'</div>'
        +'<div style="font-size:1.4em;font-weight:700">'+areas[a]+'</div>'
        +'</div>';
    });
    html += '</div>';
    div.innerHTML = Object.keys(areas).length ? html : '<p class="empty">Sin documentos · importa el SGD primero</p>';
  }catch(e){ console.error(e); }
}

async function loadSGD(){
  var area = document.getElementById('sgd-area').value;
  var tipo = document.getElementById('sgd-tipo').value;
  var estado = document.getElementById('sgd-estado').value;
  var q = document.getElementById('sgd-q').value;
  var hijos = document.getElementById('sgd-hijos').checked ? '1' : '0';
  var qs = [];
  if(area) qs.push('area='+area);
  if(tipo) qs.push('tipo_doc='+tipo);
  if(estado) qs.push('estado='+estado);
  if(q) qs.push('q='+encodeURIComponent(q));
  qs.push('incluir_hijos='+hijos);
  try{
    var r = await fetch('/api/aseguramiento/sgd/listado?' + qs.join('&'));
    var d = await r.json();
    document.getElementById('sgd-resumen').textContent = (d.total||0) + ' documentos';
    var tb = document.getElementById('sgd-tbody');
    if(!d.items || d.items.length===0){
      tb.innerHTML = '<tr><td colspan="7" class="empty">Sin documentos</td></tr>';
      return;
    }
    tb.innerHTML = d.items.map(function(it){
      var bcls = 'badge-vig';
      if(it.estado_efectivo==='vencido') bcls='badge-venc';
      else if(it.estado_efectivo==='vence_pronto') bcls='badge-prox';
      else if(it.estado==='obsoleto') bcls='badge-obs';
      else if(it.estado==='conflicto') bcls='badge-confl';
      else if(it.estado==='borrador') bcls='badge-bor';
      return '<tr>'
        +'<td><b><code>'+_esc(it.codigo)+'</code></b></td>'
        +'<td>'+_esc(it.titulo||'')+(it.padre_codigo?' <span style="color:#94a3b8;font-size:0.85em">(hijo de '+_esc(it.padre_codigo)+')</span>':'')+'</td>'
        +'<td>'+_esc(it.version_actual||'')+'</td>'
        +'<td><span class="badge '+bcls+'">'+_esc(it.estado_efectivo||it.estado||'')+'</span></td>'
        +'<td>'+_esc(it.proxima_revision||'—')+'</td>'
        +'<td>'+_esc(it.aprobado_por||'')+'</td>'
        +'<td><button class="btn btn-ghost btn-sm" onclick="verSGD(\''+_esc(it.codigo)+'\')">Ver</button></td>'
        +'</tr>';
    }).join('');
  }catch(e){ document.getElementById('sgd-tbody').innerHTML = '<tr><td colspan="7" class="empty">Error: '+_esc(e.message)+'</td></tr>'; }
}

async function verSGD(codigo){
  var body = document.getElementById('m-sgd-det-body');
  document.getElementById('m-sgd-det-title').textContent = 'Detalle · ' + codigo;
  body.innerHTML = '<p class="empty">Cargando...</p>';
  openModal('m-sgd-det');
  try{
    var r = await fetch('/api/aseguramiento/sgd/'+encodeURIComponent(codigo));
    var d = await r.json();
    if(!r.ok){ body.innerHTML = '<p class="empty" style="color:#c00">'+_esc(d.error||'?')+'</p>'; return; }
    var html = '<div class="card" style="background:#f8fafc">'
      +'<div style="font-size:0.78em;color:#64748b">'+_esc(d.codigo)+' · '+_esc(d.area)+'/'+_esc(d.tipo_doc)+'</div>'
      +'<div style="font-size:1.2em;font-weight:700;margin-top:4px">'+_esc(d.titulo||'')+'</div>'
      +'<div style="font-size:0.85em;color:#475569;margin-top:6px">'+_esc(d.descripcion||'')+'</div>'
      +'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:10px;font-size:0.85em">'
      +'<div><b>Versión:</b> '+_esc(d.version_actual||'')+'</div>'
      +'<div><b>Estado:</b> '+_esc(d.estado||'')+'</div>'
      +'<div><b>Vigente desde:</b> '+_esc(d.vigente_desde||'—')+'</div>'
      +'<div><b>Próxima revisión:</b> '+_esc(d.proxima_revision||'—')+'</div>'
      +'<div><b>Elaborado:</b> '+_esc(d.elaborado_por||'—')+'</div>'
      +'<div><b>Revisado:</b> '+_esc(d.revisado_por||'—')+'</div>'
      +'<div><b>Aprobado:</b> '+_esc(d.aprobado_por||'—')+'</div>'
      +(d.archivo_pdf_url ? '<div><b>PDF:</b> <a href="'+_esc(d.archivo_pdf_url)+'" target="_blank">abrir &rarr;</a></div>' : '')
      +'</div>'
      +'</div>';
    if((d.hijos||[]).length>0){
      html += '<div class="card-title" style="margin-top:10px">Formatos hijos ('+d.hijos.length+')</div>';
      html += '<table><thead><tr><th>Código</th><th>Título</th><th>Versión</th><th>Estado</th></tr></thead><tbody>';
      d.hijos.forEach(function(h){
        html += '<tr><td><code>'+_esc(h.codigo)+'</code></td><td>'+_esc(h.titulo||'')+'</td><td>'+_esc(h.version||'')+'</td><td>'+_esc(h.estado||'')+'</td></tr>';
      });
      html += '</tbody></table>';
    }
    if((d.versiones||[]).length>0){
      html += '<div class="card-title" style="margin-top:10px">Histórico de versiones</div>';
      html += '<table><thead><tr><th>Versión</th><th>Aprobada</th><th>Por</th><th>Motivo</th></tr></thead><tbody>';
      d.versiones.forEach(function(v){
        html += '<tr><td><b>'+_esc(v.version)+'</b></td><td>'+_esc(v.fecha_aprobacion||'—')+'</td><td>'+_esc(v.aprobado_por||'—')+'</td><td>'+_esc(v.motivo_cambio||'')+'</td></tr>';
      });
      html += '</tbody></table>';
    }
    body.innerHTML = html;
  }catch(e){ body.innerHTML = '<p class="empty" style="color:#c00">Error: '+_esc(e.message)+'</p>'; }
}

function abrirNuevoSGD(){
  ['m-sgd-codigo','m-sgd-titulo','m-sgd-vigente','m-sgd-proxrev','m-sgd-elab','m-sgd-rev','m-sgd-apr','m-sgd-url','m-sgd-obs','m-sgd-msg'].forEach(function(id){
    var el = document.getElementById(id); if(el) el.value = '';
  });
  document.getElementById('m-sgd-version').value = '1';
  document.getElementById('m-sgd-estado').value = 'vigente';
  openModal('m-sgd');
}

async function guardarSGD(){
  var msg = document.getElementById('m-sgd-msg');
  var body = {
    codigo: document.getElementById('m-sgd-codigo').value.trim().toUpperCase(),
    titulo: document.getElementById('m-sgd-titulo').value.trim(),
    version: document.getElementById('m-sgd-version').value || '1',
    estado: document.getElementById('m-sgd-estado').value,
    vigente_desde: document.getElementById('m-sgd-vigente').value || null,
    proxima_revision: document.getElementById('m-sgd-proxrev').value || null,
    elaborado_por: document.getElementById('m-sgd-elab').value || null,
    revisado_por: document.getElementById('m-sgd-rev').value || null,
    aprobado_por: document.getElementById('m-sgd-apr').value || null,
    archivo_pdf_url: document.getElementById('m-sgd-url').value || null,
    observaciones: document.getElementById('m-sgd-obs').value || null,
  };
  if(!body.codigo || !body.titulo){ msg.innerHTML='<span style="color:#ef4444">Código y título requeridos</span>'; return; }
  msg.innerHTML = '<span style="color:#64748b">Guardando...</span>';
  try{
    var r = await fetch('/api/aseguramiento/sgd', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if(d.ok){
      msg.innerHTML = '<span style="color:#15803d">&#x2705; '+_esc(d.accion||'guardado')+'</span>';
      setTimeout(function(){ closeModal('m-sgd'); loadSGD(); loadDashboard(); }, 700);
    } else { msg.innerHTML = '<span style="color:#ef4444">Error: '+_esc(d.error||'?')+'</span>'; }
  }catch(e){ msg.innerHTML = '<span style="color:#ef4444">Error red: '+_esc(e.message)+'</span>'; }
}

async function asignarCap(){
  var msg = document.getElementById('cap-msg');
  var personasRaw = document.getElementById('cap-personas').value || '';
  var personas = personasRaw.split(',').map(function(p){return p.trim().toLowerCase();}).filter(Boolean);
  var body = {
    sgd_codigo: document.getElementById('cap-codigo').value.trim().toUpperCase(),
    sgd_version: document.getElementById('cap-version').value.trim(),
    fecha_limite: document.getElementById('cap-fecha-lim').value || null,
    personas: personas,
  };
  if(!body.sgd_codigo || !body.sgd_version || !personas.length){
    msg.innerHTML = '<span style="color:#ef4444">Código, versión y personas requeridos</span>'; return;
  }
  msg.innerHTML = '<span style="color:#64748b">Asignando...</span>';
  try{
    var r = await fetch('/api/aseguramiento/capacitaciones/asignar', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if(d.ok){
      msg.innerHTML = '<span style="color:#15803d">&#x2705; '+d.asignados+' asignaciones · '+d.saltados_ya_existian+' ya existían</span>';
    } else { msg.innerHTML = '<span style="color:#ef4444">Error: '+_esc(d.error||'?')+'</span>'; }
  }catch(e){ msg.innerHTML = '<span style="color:#ef4444">Error red: '+_esc(e.message)+'</span>'; }
}

async function loadMisCapacitaciones(){
  var tb = document.getElementById('mis-cap-tbody');
  try{
    var r = await fetch('/api/aseguramiento/capacitaciones/mias');
    var d = await r.json();
    if(!d.items || !d.items.length){ tb.innerHTML = '<tr><td colspan="6" class="empty">Sin capacitaciones asignadas</td></tr>'; return; }
    tb.innerHTML = d.items.map(function(it){
      var btn = '';
      if(it.estado === 'asignada' || it.estado === 'leida'){
        btn = '<button class="btn btn-primary btn-sm" onclick="firmarCap(\''+_esc(it.sgd_codigo)+'\',\''+_esc(it.sgd_version)+'\')">Firmar lectura</button>';
      } else if(it.estado === 'firmada' || it.estado === 'aprobada'){
        btn = '<span style="color:#15803d">&#x2713; Firmada '+_esc(it.firmado_at||'')+'</span>';
      }
      return '<tr>'
        +'<td><code>'+_esc(it.sgd_codigo)+'</code></td>'
        +'<td>'+_esc(it.sgd_version)+'</td>'
        +'<td>'+_esc(it.titulo||'—')+(it.archivo_pdf_url?' · <a href="'+_esc(it.archivo_pdf_url)+'" target="_blank">PDF</a>':'')+'</td>'
        +'<td>'+_esc(it.asignado_at||'')+'</td>'
        +'<td><span class="badge badge-bor">'+_esc(it.estado)+'</span></td>'
        +'<td>'+btn+'</td>'
        +'</tr>';
    }).join('');
  }catch(e){ tb.innerHTML = '<tr><td colspan="6" class="empty">Error: '+_esc(e.message)+'</td></tr>'; }
}

async function firmarCap(codigo, version){
  if(!confirm('¿Confirmas que leíste y comprendiste el SOP '+codigo+' v'+version+'?')) return;
  try{
    var r = await fetch('/api/aseguramiento/capacitaciones/firmar', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({sgd_codigo: codigo, sgd_version: version})});
    var d = await r.json();
    if(d.ok){ alert('Firmada con hash '+d.firma_hash); loadMisCapacitaciones(); }
    else alert('Error: '+(d.error||'?'));
  }catch(e){ alert('Error red: '+e.message); }
}

async function loadConflictos(){
  var tb = document.getElementById('conf-tbody');
  try{
    var r = await fetch('/api/aseguramiento/sgd/conflictos');
    var d = await r.json();
    if(!d.items || !d.items.length){ tb.innerHTML = '<tr><td colspan="5" class="empty">Sin conflictos detectados</td></tr>'; return; }
    tb.innerHTML = d.items.map(function(it){
      var btn = it.estado === 'pendiente'
        ? '<button class="btn btn-ghost btn-sm" onclick="resolverConf('+it.id+')">Marcar resuelto</button>'
        : '<span style="color:#94a3b8">'+_esc(it.estado)+'</span>';
      return '<tr>'
        +'<td><b><code>'+_esc(it.codigo)+'</code></b></td>'
        +'<td>'+_esc(it.temas||'')+'</td>'
        +'<td>'+_esc(it.estado)+'</td>'
        +'<td>'+_esc(it.resolucion||'—')+'</td>'
        +'<td>'+btn+'</td>'
        +'</tr>';
    }).join('');
  }catch(e){ tb.innerHTML = '<tr><td colspan="5" class="empty">Error: '+_esc(e.message)+'</td></tr>'; }
}

async function resolverConf(id){
  var resolucion = prompt('Describe cómo se resolvió (mín 10 chars):');
  if(!resolucion || resolucion.length < 10) return;
  try{
    var r = await fetch('/api/aseguramiento/sgd/conflictos/'+id+'/resolver', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({resolucion: resolucion})});
    var d = await r.json();
    if(d.ok){ loadConflictos(); }
    else alert('Error: '+(d.error||'?'));
  }catch(e){ alert('Error red: '+e.message); }
}

window.addEventListener('DOMContentLoaded', function(){ loadDashboard(); });
</script>
</body>
</html>'''
