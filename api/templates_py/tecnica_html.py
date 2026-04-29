TECNICA_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Tecnica & Aseguramiento - Espagiria</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos6">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#0f172a;color:#e2e8f0;font-size:14px;min-height:100vh;}
.topbar{background:#1e293b;border-bottom:1px solid #334155;padding:12px 24px;display:flex;align-items:center;gap:16px;}
.logo{font-size:0.85em;font-weight:900;letter-spacing:3px;color:#fff;}
.badge{background:rgba(99,102,241,0.3);color:#a5b4fc;padding:3px 12px;border-radius:20px;font-size:0.7em;font-weight:700;letter-spacing:1px;}
.topbar a{color:rgba(255,255,255,0.45);text-decoration:none;font-size:0.78em;padding:5px 12px;border:1px solid rgba(255,255,255,0.12);border-radius:6px;margin-left:auto;}
.topbar a:hover{color:#fff;border-color:rgba(255,255,255,0.35);}
.tabs{display:flex;gap:0;background:#1e293b;border-bottom:1px solid #334155;padding:0 24px;overflow-x:auto;}
.tab{padding:11px 18px;font-size:0.75em;font-weight:700;letter-spacing:.5px;color:#64748b;cursor:pointer;border-bottom:2px solid transparent;text-transform:uppercase;white-space:nowrap;}
.tab.active{color:#a5b4fc;border-bottom-color:#a5b4fc;}
.tab:hover{color:#cbd5e1;}
.main{padding:24px;max-width:1300px;margin:0 auto;}
.kpi-row{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:24px;}
.kpi{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px 20px;flex:1;min-width:130px;}
.kpi-label{font-size:0.67em;text-transform:uppercase;letter-spacing:1.5px;color:#64748b;margin-bottom:6px;}
.kpi-val{font-size:2em;font-weight:800;color:#f1f5f9;}
.kpi-val.warn{color:#fb923c;} .kpi-val.crit{color:#f87171;} .kpi-val.good{color:#4ade80;}
.kpi-sub{font-size:0.68em;color:#475569;margin-top:3px;}
.card{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:18px;margin-bottom:16px;}
.card-title{font-size:0.7em;text-transform:uppercase;letter-spacing:1.5px;color:#64748b;margin-bottom:14px;font-weight:700;}
.card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;}
table{width:100%;border-collapse:collapse;}
th{font-size:0.67em;text-transform:uppercase;letter-spacing:.8px;color:#475569;padding:8px 10px;text-align:left;border-bottom:1px solid #334155;}
td{padding:8px 10px;font-size:0.8em;border-bottom:1px solid #1e293b;color:#cbd5e1;vertical-align:middle;}
tr:hover td{background:#0f172a;}
.badge-verde{background:#052e16;color:#4ade80;padding:2px 9px;border-radius:20px;font-size:0.7em;font-weight:700;}
.badge-amarillo{background:#451a03;color:#fcd34d;padding:2px 9px;border-radius:20px;font-size:0.7em;font-weight:700;}
.badge-rojo{background:#450a0a;color:#fca5a5;padding:2px 9px;border-radius:20px;font-size:0.7em;font-weight:700;}
.badge-azul{background:#1e1b4b;color:#a5b4fc;padding:2px 9px;border-radius:20px;font-size:0.7em;font-weight:700;}
.badge-gris{background:#1e293b;color:#94a3b8;padding:2px 9px;border-radius:20px;font-size:0.7em;font-weight:700;border:1px solid #334155;}
.badge-morado{background:#2e1065;color:#d8b4fe;padding:2px 9px;border-radius:20px;font-size:0.7em;font-weight:700;}
.btn{padding:7px 16px;border-radius:7px;border:none;font-size:0.78em;font-weight:700;cursor:pointer;letter-spacing:.3px;}
.btn-primary{background:#4f46e5;color:#fff;} .btn-primary:hover{background:#4338ca;}
.btn-danger{background:#7f1d1d;color:#fca5a5;} .btn-danger:hover{background:#991b1b;}
.btn-sm{padding:4px 10px;font-size:0.7em;}
.btn-link{background:none;border:none;color:#a5b4fc;cursor:pointer;font-size:0.75em;text-decoration:underline;padding:0;}
.form-row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px;align-items:flex-end;}
.form-group{display:flex;flex-direction:column;gap:4px;flex:1;min-width:150px;}
label{font-size:0.68em;text-transform:uppercase;letter-spacing:.8px;color:#64748b;font-weight:700;}
input,select,textarea{background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:7px 10px;border-radius:7px;font-size:0.82em;width:100%;}
input:focus,select:focus,textarea:focus{outline:none;border-color:#a5b4fc;}
textarea{resize:vertical;min-height:60px;}
.pane{display:none;} .pane.active{display:block;}
.empty{color:#475569;text-align:center;padding:32px;font-size:0.85em;}
.sep{height:1px;background:#334155;margin:16px 0;}
.row-alert{background:rgba(251,146,60,0.08) !important;}
.row-crit{background:rgba(248,113,113,0.1) !important;}
</style>
</head>
<body>
<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:#6d28d9;"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
  <div>
    <div class="cx-mod-header__title">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#6d28d9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><path d="M14.7 6.3a4 4 0 005.7-5.7L18 3l-2-1-1-2-2.6 2.6a4 4 0 005.3 5.4z"/><path d="M14 9 4 19l3 3 10-10"/></svg>
      Dirección Técnica
    </div>
    <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; Espagiria &middot; fórmulas, INVIMA, SOPs &amp; SGD</div>
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
  <div class="tab active" onclick="goTab('tab-dash')">&#128200; Dashboard</div>
  <div class="tab" onclick="goTab('tab-formulas')">&#129514; Formulas Maestras</div>
  <div class="tab" onclick="goTab('tab-fichas')">&#128196; Fichas Tecnicas</div>
  <div class="tab" onclick="goTab('tab-invima')">&#x2696;&#xfe0f; Registros INVIMA</div>
  <div class="tab" onclick="goTab('tab-sgd')">&#128193; Documentos SGD</div>
</div>
<div class="main">
<!-- Dashboard -->
<div id="tab-dash" class="pane active">
  <div class="kpi-row">
    <div class="kpi"><div class="kpi-label">Formulas Vigentes</div><div class="kpi-val good" id="kv-form">-</div><div class="kpi-sub">Maestras activas</div></div>
    <div class="kpi"><div class="kpi-label">Fichas Tecnicas</div><div class="kpi-val good" id="kv-fich">-</div><div class="kpi-sub">Vigentes</div></div>
    <div class="kpi"><div class="kpi-label">Reg. INVIMA Vigentes</div><div class="kpi-val good" id="kv-inv">-</div><div class="kpi-sub">Notificaciones activas</div></div>
    <div class="kpi"><div class="kpi-label">INVIMA por Vencer</div><div class="kpi-val warn" id="kv-pv">-</div><div class="kpi-sub">Proximos 90 dias</div></div>
    <div class="kpi"><div class="kpi-label">En Tramite</div><div class="kpi-val" id="kv-tram">-</div><div class="kpi-sub">INVIMA en proceso</div></div>
    <div class="kpi"><div class="kpi-label">Docs SGD Vigentes</div><div class="kpi-val good" id="kv-docs">-</div><div class="kpi-sub">SOPs y BPMs activos</div></div>
    <div class="kpi"><div class="kpi-label">Docs a Revisar</div><div class="kpi-val warn" id="kv-rev">-</div><div class="kpi-sub">Proximos 30 dias</div></div>
  </div>
  <div class="card">
    <div class="card-title">Proximos Vencimientos INVIMA</div>
    <table><thead><tr><th>Producto</th><th>N. Registro</th><th>Vencimiento</th><th>Estado</th></tr></thead>
      <tbody id="tb-proximos"><tr><td colspan="4" class="empty">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>
<!-- Formulas Maestras -->
<div id="tab-formulas" class="pane">
  <div class="card">
    <div class="card-header"><span class="card-title" style="margin:0">Nueva Formula Maestra</span></div>
    <div class="form-row">
      <div class="form-group"><label>Codigo</label><input id="fm-cod" placeholder="COC-FOR-001"></div>
      <div class="form-group"><label>Nombre del Producto</label><input id="fm-nom" placeholder="Serum Vitamina C"></div>
      <div class="form-group"><label>Version</label><input id="fm-ver" value="1.0" style="max-width:80px"></div>
      <div class="form-group"><label>Tipo</label><select id="fm-tipo"><option>COSMETICO</option><option>SUPLEMENTO</option><option>HIGIENE</option><option>OTRO</option></select></div>
      <div class="form-group"><label>Estado</label><select id="fm-est"><option>Vigente</option><option>En_Revision</option><option>Obsoleta</option></select></div>
      <div class="form-group"><label>Fecha Version</label><input type="date" id="fm-fv"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Descripcion / Observaciones</label><textarea id="fm-desc" rows="2"></textarea></div>
      <div class="form-group" style="max-width:140px;justify-content:flex-end"><button class="btn btn-primary" onclick="registrarFormula()">+ Registrar</button></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">Formulas Registradas</div>
    <table><thead><tr><th>Codigo</th><th>Nombre</th><th>Version</th><th>Tipo</th><th>Estado</th><th>Fecha Version</th><th>Creado por</th><th></th></tr></thead>
      <tbody id="tb-formulas"><tr><td colspan="8" class="empty">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>
<!-- Fichas Tecnicas -->
<div id="tab-fichas" class="pane">
  <div class="card">
    <div class="card-header"><span class="card-title" style="margin:0">Nueva Ficha Tecnica</span></div>
    <div class="form-row">
      <div class="form-group"><label>Codigo</label><input id="ft-cod" placeholder="COC-FT-001"></div>
      <div class="form-group"><label>Nombre del Producto</label><input id="ft-nom"></div>
      <div class="form-group"><label>Version</label><input id="ft-ver" value="1.0" style="max-width:80px"></div>
      <div class="form-group"><label>Estado</label><select id="ft-est"><option>Vigente</option><option>En_Revision</option><option>Obsoleta</option></select></div>
      <div class="form-group"><label>Fecha Actualizacion</label><input type="date" id="ft-fv"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>URL Documento</label><input id="ft-url" placeholder="https://..."></div>
      <div class="form-group"><label>Notas</label><input id="ft-notas"></div>
      <div class="form-group" style="max-width:140px;justify-content:flex-end"><button class="btn btn-primary" onclick="registrarFicha()">+ Registrar</button></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">Fichas Registradas</div>
    <table><thead><tr><th>Codigo</th><th>Nombre</th><th>Version</th><th>Estado</th><th>Actualizado</th><th>Documento</th><th></th></tr></thead>
      <tbody id="tb-fichas"><tr><td colspan="7" class="empty">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>
<!-- Registros INVIMA -->
<div id="tab-invima" class="pane">
  <div class="card">
    <div class="card-header"><span class="card-title" style="margin:0">Nuevo Registro INVIMA</span></div>
    <div class="form-row">
      <div class="form-group"><label>Producto</label><input id="inv-prod" placeholder="Serum Vitamina C"></div>
      <div class="form-group"><label>N. Registro</label><input id="inv-reg" placeholder="NSC-2024-0001"></div>
      <div class="form-group"><label>N. Lote INVIMA</label><input id="inv-lote"></div>
      <div class="form-group"><label>Tipo Tramite</label><select id="inv-tipo"><option>Notificacion Sanitaria</option><option>Registro Sanitario</option><option>Renovacion</option><option>Modificacion</option></select></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Fecha Expedicion</label><input type="date" id="inv-fexp"></div>
      <div class="form-group"><label>Fecha Vencimiento</label><input type="date" id="inv-fven"></div>
      <div class="form-group"><label>Estado</label><select id="inv-est"><option>Vigente</option><option>En_Tramite</option><option>Vencido</option><option>Suspendido</option></select></div>
      <div class="form-group"><label>Notas</label><input id="inv-notas"></div>
      <div class="form-group" style="max-width:140px;justify-content:flex-end"><button class="btn btn-primary" onclick="registrarInvima()">+ Registrar</button></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">Registros INVIMA</div>
    <table><thead><tr><th>Producto</th><th>N. Registro</th><th>Tipo</th><th>Expedicion</th><th>Vencimiento</th><th>Estado</th><th>Alertas</th><th></th></tr></thead>
      <tbody id="tb-invima"><tr><td colspan="8" class="empty">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>
<!-- Documentos SGD -->
<div id="tab-sgd" class="pane">
  <div class="card">
    <div class="card-header"><span class="card-title" style="margin:0">Nuevo Documento</span></div>
    <div class="form-row">
      <div class="form-group"><label>Tipo</label><select id="sg-tipo"><option>SOP</option><option>BPM</option><option>Instruccion</option><option>Formato</option><option>Manual</option><option>Protocolo</option><option>Otro</option></select></div>
      <div class="form-group"><label>Codigo</label><input id="sg-cod" placeholder="COC-SOP-001"></div>
      <div class="form-group"><label>Nombre</label><input id="sg-nom" placeholder="Control de Calidad MP"></div>
      <div class="form-group"><label>Version</label><input id="sg-ver" value="1.0" style="max-width:80px"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Fecha Emision</label><input type="date" id="sg-fem"></div>
      <div class="form-group"><label>Fecha Revision</label><input type="date" id="sg-frev"></div>
      <div class="form-group"><label>Responsable</label><input id="sg-resp" placeholder="Sebastian / Alejandro"></div>
      <div class="form-group"><label>Estado</label><select id="sg-est"><option>Vigente</option><option>En_Revision</option><option>Obsoleto</option></select></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>URL Documento</label><input id="sg-url" placeholder="https://..."></div>
      <div class="form-group"><label>Notas</label><input id="sg-notas"></div>
      <div class="form-group" style="max-width:140px;justify-content:flex-end"><button class="btn btn-primary" onclick="registrarDoc()">+ Registrar</button></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">Documentos del SGD</div>
    <table><thead><tr><th>Tipo</th><th>Codigo</th><th>Nombre</th><th>Ver.</th><th>Emision</th><th>Revision</th><th>Responsable</th><th>Estado</th><th></th></tr></thead>
      <tbody id="tb-sgd"><tr><td colspan="9" class="empty">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>
</div>
<script>
function goTab(id) {
  document.querySelectorAll('.pane').forEach(function(p){p.classList.remove('active');});
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});
  document.getElementById(id).classList.add('active');
  event.target.classList.add('active');
  if (id === 'tab-dash') loadDash();
  if (id === 'tab-formulas') loadFormulas();
  if (id === 'tab-fichas') loadFichas();
  if (id === 'tab-invima') loadInvima();
  if (id === 'tab-sgd') loadSgd();
}
function estadoBadge(e) {
  if (!e) return '<span class="badge-gris">-</span>';
  var m = {'Vigente':'badge-verde','vigente':'badge-verde','En_Revision':'badge-amarillo','En_Tramite':'badge-amarillo','Obsoleta':'badge-gris','Obsoleto':'badge-gris','Vencido':'badge-rojo','Suspendido':'badge-rojo'};
  return '<span class="' + (m[e]||'badge-gris') + '">' + e + '</span>';
}
function vencimientoBadge(fv) {
  if (!fv) return '<span class="badge-gris">-</span>';
  var hoy = new Date(); hoy.setHours(0,0,0,0);
  var d = new Date(fv + 'T00:00:00');
  var diff = Math.floor((d - hoy) / 86400000);
  if (diff < 0) return '<span class="badge-rojo">Vencido</span>';
  if (diff <= 30) return '<span class="badge-rojo">' + diff + ' dias</span>';
  if (diff <= 90) return '<span class="badge-amarillo">' + diff + ' dias</span>';
  return '<span class="badge-verde">' + diff + ' dias</span>';
}
function loadDash() {
  fetch('/api/tecnica/dashboard').then(function(r){return r.json();}).then(function(d) {
    document.getElementById('kv-form').textContent = d.formulas_vigentes || 0;
    document.getElementById('kv-fich').textContent = d.fichas_vigentes || 0;
    document.getElementById('kv-inv').textContent = d.registros_vigentes || 0;
    document.getElementById('kv-pv').textContent = d.por_vencer || 0;
    document.getElementById('kv-tram').textContent = d.registros_tramite || 0;
    document.getElementById('kv-docs').textContent = d.docs_vigentes || 0;
    document.getElementById('kv-rev').textContent = d.docs_revisar || 0;
    var tb = document.getElementById('tb-proximos');
    if (!d.proximos_vencimientos || d.proximos_vencimientos.length === 0) {
      tb.innerHTML = '<tr><td colspan="4" class="empty">Sin registros de vencimiento</td></tr>'; return;
    }
    tb.innerHTML = d.proximos_vencimientos.map(function(r) {
      return '<tr><td>' + (r.producto||'') + '</td><td>' + (r.num_registro||'-') + '</td><td>' + (r.fecha_vencimiento||'-') + '</td><td>' + estadoBadge(r.estado) + '</td></tr>';
    }).join('');
  });
}
function loadFormulas() {
  fetch('/api/tecnica/formulas').then(function(r){return r.json();}).then(function(data) {
    var tb = document.getElementById('tb-formulas');
    if (!data.length) { tb.innerHTML = '<tr><td colspan="8" class="empty">Sin formulas registradas</td></tr>'; return; }
    tb.innerHTML = data.map(function(r) {
      var acciones = '<button class="btn btn-secondary btn-sm" onclick="verHistorialFormula(' + r.id + ', \'' + (r.codigo||'').replace(/'/g,'\\\'')+ '\')" title="Ver historial">&#128214; Historial</button> ' +
                     '<button class="btn btn-danger btn-sm" onclick="eliminarFormula(' + r.id + ')">Eliminar</button>';
      return '<tr><td>' + r.codigo + '</td><td>' + r.nombre + '</td><td>' + r.version + '</td><td><span class="badge-azul">' + r.tipo + '</span></td><td>' + estadoBadge(r.estado) + '</td><td>' + (r.fecha_version||'-') + '</td><td>' + (r.creado_por||'-') + '</td><td>' + acciones + '</td></tr>';
    }).join('');
  });
}

// ── Versionado: ver historial y restaurar ─────────────────────────────────
function verHistorialFormula(fid, codigo) {
  fetch('/api/tecnica/formulas/' + fid + '/versiones').then(function(r){return r.json();}).then(function(versiones) {
    var modal = document.getElementById('modal-historial');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'modal-historial';
      modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:9999;';
      modal.innerHTML = '<div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:24px;width:780px;max-width:95vw;max-height:90vh;overflow-y:auto;color:#e2e8f0;"><div id="modal-historial-body"></div></div>';
      document.body.appendChild(modal);
      modal.addEventListener('click', function(e){ if(e.target===modal) modal.remove(); });
    }
    var body = document.getElementById('modal-historial-body');
    if (!versiones || !versiones.length) {
      body.innerHTML = '<h2 style="margin-top:0">&#128214; Historial — ' + codigo + '</h2>' +
        '<div style="color:#64748b;font-style:italic;padding:24px;text-align:center;">Sin cambios registrados todavia. El primer snapshot se crea al editar la formula.</div>' +
        '<div style="text-align:right;margin-top:16px"><button class="btn btn-secondary" onclick="document.getElementById(\'modal-historial\').remove()">Cerrar</button></div>';
      return;
    }
    var rows = versiones.map(function(v) {
      return '<tr style="border-bottom:1px solid #334155;">' +
        '<td style="padding:10px;font-weight:700;color:#fbbf24;">v' + v.version_num + '</td>' +
        '<td style="padding:10px;font-size:12px;">' + (v.fecha_creacion||'-').substring(0,16) + '</td>' +
        '<td style="padding:10px;font-size:12px;color:#a5f3fc;">' + (v.creado_por||'-') + '</td>' +
        '<td style="padding:10px;font-size:12px;">' + (v.motivo_cambio||'<em style="color:#64748b">sin motivo</em>') + '</td>' +
        '<td style="padding:10px;text-align:right;white-space:nowrap;">' +
          '<button class="btn btn-secondary btn-sm" onclick="verSnapshot(' + fid + ',' + v.id + ')" title="Ver detalle">&#128065; Ver</button> ' +
          '<button class="btn btn-warning btn-sm" style="background:#a16207;color:#fff;" onclick="restaurarFormula(' + fid + ',' + v.id + ',' + v.version_num + ')" title="Restaurar a esta version">&#8617; Restaurar</button>' +
        '</td>' +
      '</tr>';
    }).join('');
    body.innerHTML = '<h2 style="margin-top:0">&#128214; Historial — ' + codigo + '</h2>' +
      '<div style="font-size:12px;color:#64748b;margin-bottom:14px;">Snapshots tomados automaticamente antes de cada cambio. Click "Restaurar" para revertir (admins only). El restore tambien se snapshot, asi puedes deshacer el deshacer.</div>' +
      '<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#0f172a;color:#94a3b8;text-transform:uppercase;font-size:11px;">' +
      '<th style="padding:10px;text-align:left;">Version</th><th style="padding:10px;text-align:left;">Fecha</th><th style="padding:10px;text-align:left;">Por</th><th style="padding:10px;text-align:left;">Motivo</th><th style="padding:10px;text-align:right;">Acciones</th>' +
      '</tr></thead><tbody>' + rows + '</tbody></table>' +
      '<div style="text-align:right;margin-top:16px"><button class="btn btn-secondary" onclick="document.getElementById(\'modal-historial\').remove()">Cerrar</button></div>';
  });
}

function verSnapshot(fid, vid) {
  fetch('/api/tecnica/formulas/' + fid + '/versiones/' + vid).then(function(r){return r.json();}).then(function(d) {
    if (d.error) { alert('Error: ' + d.error); return; }
    var snap = d.snapshot || {};
    var lineas = Object.keys(snap).filter(function(k){return k!=='_componentes';}).map(function(k){
      return '<tr><td style="padding:6px 12px;color:#94a3b8;font-size:12px;">' + k + '</td>' +
             '<td style="padding:6px 12px;font-size:12px;color:#e2e8f0;">' + (snap[k]==null?'<em style="color:#64748b">null</em>':String(snap[k]).substring(0,200)) + '</td></tr>';
    }).join('');
    var html = '<h2 style="margin-top:0">&#128203; Snapshot v' + d.version_num + '</h2>' +
      '<div style="font-size:11px;color:#64748b;margin-bottom:10px;">Tomado el ' + (d.fecha_creacion||'-') + ' por ' + (d.creado_por||'-') + ' — motivo: ' + (d.motivo_cambio||'(no especificado)') + '</div>' +
      '<table style="width:100%;border-collapse:collapse;background:#0f172a;border-radius:8px;overflow:hidden;">' + lineas + '</table>' +
      '<div style="text-align:right;margin-top:16px;"><button class="btn btn-secondary" onclick="this.parentNode.parentNode.parentNode.parentNode.remove()">Cerrar</button></div>';
    var m = document.createElement('div');
    m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.85);display:flex;align-items:center;justify-content:center;z-index:10000;';
    m.innerHTML = '<div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:22px;width:680px;max-width:95vw;max-height:85vh;overflow-y:auto;color:#e2e8f0;">' + html + '</div>';
    m.addEventListener('click', function(e){ if(e.target===m) m.remove(); });
    document.body.appendChild(m);
  });
}

function restaurarFormula(fid, vid, vnum) {
  var msg = 'Restaurar formula a la version v' + vnum + '? El estado actual se guardara como snapshot adicional, asi puedes revertir el restore si te arrepientes. Solo admins pueden hacer esto.';
  if (!confirm(msg)) return;
  fetch('/api/tecnica/formulas/' + fid + '/restaurar/' + vid, {method:'POST'}).then(function(r){return r.json();}).then(function(d) {
    if (d.error) { alert('Error: ' + d.error); return; }
    alert('Formula restaurada a v' + d.restaurado_a_version);
    var m = document.getElementById('modal-historial'); if (m) m.remove();
    loadFormulas();
  });
}
function registrarFormula() {
  var fv = document.getElementById('fm-fv').value;
  if (!fv) { var hoy = new Date(); fv = hoy.toISOString().slice(0,10); }
  var payload = {codigo:document.getElementById('fm-cod').value,nombre:document.getElementById('fm-nom').value,version:document.getElementById('fm-ver').value,tipo:document.getElementById('fm-tipo').value,estado:document.getElementById('fm-est').value,fecha_version:fv,descripcion:document.getElementById('fm-desc').value};
  if (!payload.codigo || !payload.nombre) { alert('Codigo y nombre son obligatorios'); return; }
  fetch('/api/tecnica/formulas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).then(function(r){return r.json();}).then(function(d){if(d.ok){loadFormulas();document.getElementById('fm-cod').value='';document.getElementById('fm-nom').value='';document.getElementById('fm-desc').value='';}else alert(d.error||'Error');});
}
function eliminarFormula(id) {
  if (!confirm('Eliminar formula? Esta accion no se puede deshacer.')) return;
  fetch('/api/tecnica/formulas/' + id,{method:'DELETE'}).then(function(r){return r.json();}).then(function(){loadFormulas();});
}
function loadFichas() {
  fetch('/api/tecnica/fichas').then(function(r){return r.json();}).then(function(data) {
    var tb = document.getElementById('tb-fichas');
    if (!data.length) { tb.innerHTML = '<tr><td colspan="7" class="empty">Sin fichas registradas</td></tr>'; return; }
    tb.innerHTML = data.map(function(r) {
      var link = r.url_documento ? '<a href="' + r.url_documento + '" target="_blank" style="color:#a5b4fc">Ver doc</a>' : '-';
      return '<tr><td>' + r.codigo + '</td><td>' + r.nombre + '</td><td>' + r.version + '</td><td>' + estadoBadge(r.estado) + '</td><td>' + (r.fecha_actualizacion||'-') + '</td><td>' + link + '</td><td><button class="btn btn-danger btn-sm" onclick="eliminarFicha(' + r.id + ')">Eliminar</button></td></tr>';
    }).join('');
  });
}
function registrarFicha() {
  var fv = document.getElementById('ft-fv').value; if (!fv) fv = new Date().toISOString().slice(0,10);
  var payload = {codigo:document.getElementById('ft-cod').value,nombre:document.getElementById('ft-nom').value,version:document.getElementById('ft-ver').value,estado:document.getElementById('ft-est').value,fecha_actualizacion:fv,url_documento:document.getElementById('ft-url').value,notas:document.getElementById('ft-notas').value};
  if (!payload.codigo || !payload.nombre) { alert('Codigo y nombre son obligatorios'); return; }
  fetch('/api/tecnica/fichas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).then(function(r){return r.json();}).then(function(d){if(d.ok){loadFichas();document.getElementById('ft-cod').value='';document.getElementById('ft-nom').value='';document.getElementById('ft-url').value='';}else alert(d.error||'Error');});
}
function eliminarFicha(id) {
  if (!confirm('Eliminar ficha tecnica?')) return;
  fetch('/api/tecnica/fichas/' + id,{method:'DELETE'}).then(function(r){return r.json();}).then(function(){loadFichas();});
}
function loadInvima() {
  fetch('/api/tecnica/invima').then(function(r){return r.json();}).then(function(data) {
    var tb = document.getElementById('tb-invima');
    if (!data.length) { tb.innerHTML = '<tr><td colspan="8" class="empty">Sin registros INVIMA</td></tr>'; return; }
    var hoy = new Date(); hoy.setHours(0,0,0,0);
    tb.innerHTML = data.map(function(r) {
      var rowClass = '';
      if (r.fecha_vencimiento) { var d = new Date(r.fecha_vencimiento + 'T00:00:00'); var diff = Math.floor((d - hoy) / 86400000); if (diff < 0) rowClass = 'class="row-crit"'; else if (diff <= 90) rowClass = 'class="row-alert"'; }
      return '<tr ' + rowClass + '><td>' + r.producto + '</td><td>' + (r.num_registro||'-') + '</td><td><span class="badge-morado">' + (r.tipo_tramite||'-') + '</span></td><td>' + (r.fecha_expedicion||'-') + '</td><td>' + (r.fecha_vencimiento||'-') + '</td><td>' + estadoBadge(r.estado) + '</td><td>' + vencimientoBadge(r.fecha_vencimiento) + '</td><td><button class="btn btn-danger btn-sm" onclick="eliminarInvima(' + r.id + ')">Eliminar</button></td></tr>';
    }).join('');
  });
}
function registrarInvima() {
  var payload = {producto:document.getElementById('inv-prod').value,num_registro:document.getElementById('inv-reg').value,num_lote:document.getElementById('inv-lote').value,tipo_tramite:document.getElementById('inv-tipo').value,fecha_expedicion:document.getElementById('inv-fexp').value,fecha_vencimiento:document.getElementById('inv-fven').value,estado:document.getElementById('inv-est').value,notas:document.getElementById('inv-notas').value};
  if (!payload.producto) { alert('Producto es obligatorio'); return; }
  fetch('/api/tecnica/invima',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).then(function(r){return r.json();}).then(function(d){if(d.ok){loadInvima();loadDash();document.getElementById('inv-prod').value='';document.getElementById('inv-reg').value='';}else alert(d.error||'Error');});
}
function eliminarInvima(id) {
  if (!confirm('Eliminar registro INVIMA?')) return;
  fetch('/api/tecnica/invima/' + id,{method:'DELETE'}).then(function(r){return r.json();}).then(function(){loadInvima();loadDash();});
}
function loadSgd() {
  fetch('/api/tecnica/documentos').then(function(r){return r.json();}).then(function(data) {
    var tb = document.getElementById('tb-sgd');
    if (!data.length) { tb.innerHTML = '<tr><td colspan="9" class="empty">Sin documentos registrados</td></tr>'; return; }
    tb.innerHTML = data.map(function(r) {
      var link = r.url_documento ? '<a href="' + r.url_documento + '" target="_blank" style="color:#a5b4fc">Ver</a>' : '-';
      return '<tr><td><span class="badge-azul">' + (r.tipo||'SOP') + '</span></td><td>' + r.codigo + '</td><td>' + r.nombre + '</td><td>' + r.version + '</td><td>' + (r.fecha_emision||'-') + '</td><td>' + (r.fecha_revision||'-') + '</td><td>' + (r.responsable||'-') + '</td><td>' + estadoBadge(r.estado) + '</td><td>' + link + '</td></tr>';
    }).join('');
  });
}
function registrarDoc() {
  var fem = document.getElementById('sg-fem').value; if (!fem) fem = new Date().toISOString().slice(0,10);
  var payload = {tipo:document.getElementById('sg-tipo').value,codigo:document.getElementById('sg-cod').value,nombre:document.getElementById('sg-nom').value,version:document.getElementById('sg-ver').value,fecha_emision:fem,fecha_revision:document.getElementById('sg-frev').value,responsable:document.getElementById('sg-resp').value,estado:document.getElementById('sg-est').value,url_documento:document.getElementById('sg-url').value,notas:document.getElementById('sg-notas').value};
  if (!payload.codigo || !payload.nombre) { alert('Codigo y nombre son obligatorios'); return; }
  fetch('/api/tecnica/documentos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).then(function(r){return r.json();}).then(function(d){if(d.ok){loadSgd();document.getElementById('sg-cod').value='';document.getElementById('sg-nom').value='';document.getElementById('sg-url').value='';}else alert(d.error||'Error');});
}
loadDash();
</script>
</body>
</html>"""