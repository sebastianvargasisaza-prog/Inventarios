"""Template Compliance — Cronogramas BPM + CAPA + Hallazgos."""

HTML = r"""<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Compliance · HHA Group</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos12">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#f5f4f2;color:#1c1917;font-size:14px}
.topbar{background:linear-gradient(90deg,#0c4a6e,#0f766e);color:#fff;padding:14px 20px;display:flex;align-items:center;gap:14px}
.topbar h1{font-size:18px;font-weight:700;flex:1}
.topbar a{color:#cbd5e1;text-decoration:none;font-size:13px;padding:6px 12px;border-radius:6px;background:rgba(255,255,255,.1)}
.tabs{background:#fff;border-bottom:2px solid #e2e8f0;display:flex;gap:0;overflow-x:auto}
.tabbtn{padding:12px 22px;font-size:13px;font-weight:600;color:#64748b;background:none;border:none;cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-2px;white-space:nowrap}
.tabbtn:hover{background:#f8fafc;color:#0c4a6e}
.tabbtn.on{color:#0c4a6e;border-bottom-color:#0f766e;font-weight:700}
.pane{display:none;padding:22px 24px;max-width:1300px;margin:0 auto}
.pane.on{display:block}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:18px}
.kpi{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px;border-left:4px solid #0f766e}
.kpi.warn{border-left-color:#d97706}
.kpi.danger{border-left-color:#dc2626}
.kpi-l{font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.kpi-v{font-size:24px;font-weight:800;color:#0f172a}
.kpi-s{font-size:11px;color:#64748b;margin-top:2px}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:16px;margin-bottom:12px}
.btn{padding:7px 14px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer}
.btn-primary{background:#0f766e;color:#fff}.btn-primary:hover{background:#115e59}
.btn-secondary{background:#e2e8f0;color:#475569}
.btn-danger{background:#dc2626;color:#fff}
.btn-warn{background:#d97706;color:#fff}
.btn-success{background:#16a34a;color:#fff}
.btn-sm{padding:4px 8px;font-size:11px}
input,select,textarea{padding:8px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;font-family:inherit;width:100%}
input:focus,select:focus,textarea:focus{border-color:#0f766e;outline:none}
.row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.row > * {flex:1;min-width:180px}
label{font-size:12px;font-weight:600;color:#475569;display:block;margin-bottom:4px}
.badge{padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700;text-transform:uppercase}
.b-abierto,.b-abierta{background:#fee2e2;color:#991b1b}
.b-en_proceso,.b-en_investigacion,.b-en_implementacion{background:#fef3c7;color:#92400e}
.b-cerrado,.b-cerrada{background:#d1fae5;color:#065f46}
.b-pendiente{background:#dbeafe;color:#1e40af}
.b-ejecutado{background:#d1fae5;color:#065f46}
.b-vencido{background:#fee2e2;color:#991b1b}
.b-critico{background:#fee2e2;color:#991b1b;border:1px solid #dc2626}
.b-mayor{background:#fed7aa;color:#9a3412}
.b-menor{background:#fef3c7;color:#92400e}
.b-observacion{background:#e0e7ff;color:#3730a3}
.b-INVIMA{background:#fee2e2;color:#991b1b;font-weight:800}
.b-BPM_interna{background:#dbeafe;color:#1e40af}
.b-autoinspeccion{background:#e0e7ff;color:#3730a3}
.empty{text-align:center;color:#94a3b8;padding:30px;font-style:italic}
.progress{height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;margin-top:6px}
.progress-bar{height:100%;background:linear-gradient(90deg,#16a34a,#0f766e);transition:width .3s}
.progress-bar.warn{background:linear-gradient(90deg,#f59e0b,#d97706)}
.progress-bar.danger{background:linear-gradient(90deg,#dc2626,#991b1b)}
table{width:100%;border-collapse:collapse;font-size:12px}
th{padding:8px;text-align:left;color:#64748b;border-bottom:1px solid #e2e8f0;background:#f8fafc;text-transform:uppercase;font-size:10px;letter-spacing:.5px}
td{padding:8px;border-bottom:1px solid #f1f5f9;vertical-align:top}
tr:hover{background:#fafafa}
</style>
</head>
<body>
<div class="topbar">
  <h1>📋 Compliance · HHA Group</h1>
  <a href="/modulos">← Módulos</a>
</div>

<!-- KPIs globales -->
<div style="padding:16px 24px;max-width:1300px;margin:0 auto">
  <div id="kpis" class="kpis"></div>
</div>

<div class="tabs">
  <button class="tabbtn on" data-pane="cron" onclick="switchPane('cron')">📅 Cronogramas BPM</button>
  <button class="tabbtn" data-pane="capa" onclick="switchPane('capa')">⚠ CAPA / Desviaciones</button>
  <button class="tabbtn" data-pane="hall" onclick="switchPane('hall')">🔍 Hallazgos abiertos</button>
</div>

<!-- PANE: Cronogramas BPM -->
<div id="pane-cron" class="pane on">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px">
    <h3 style="color:#0c4a6e">Cronogramas BPM · año <span id="year-cron"></span></h3>
    <div style="font-size:11px;color:#64748b">Click en un cronograma → ver/agregar ejecuciones</div>
  </div>
  <div id="cronograma-list"></div>
</div>

<!-- PANE: CAPA -->
<div id="pane-capa" class="pane">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px">
    <h3 style="color:#0c4a6e">CAPA · Desviaciones, no-conformidades, quejas</h3>
    <button class="btn btn-primary" onclick="abrirModalCAPA()">+ Nueva desviación</button>
  </div>
  <div style="margin-bottom:10px">
    <select id="capa-filtro" onchange="cargarCAPA()" style="width:auto;display:inline-block">
      <option value="">Todas</option>
      <option value="abierta">Abiertas</option>
      <option value="en_investigacion">En investigación</option>
      <option value="en_implementacion">En implementación</option>
      <option value="cerrada">Cerradas</option>
    </select>
  </div>
  <div id="capa-list"></div>
</div>

<!-- PANE: Hallazgos -->
<div id="pane-hall" class="pane">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px">
    <h3 style="color:#0c4a6e">Hallazgos abiertos · INVIMA, auditoría, autoinspección</h3>
    <button class="btn btn-primary" onclick="abrirModalHallazgo()">+ Nuevo hallazgo</button>
  </div>
  <div style="margin-bottom:10px">
    <select id="hall-filtro" onchange="cargarHallazgos()" style="width:auto;display:inline-block">
      <option value="">Todos</option>
      <option value="abierto">Abiertos</option>
      <option value="en_proceso">En proceso</option>
      <option value="cerrado">Cerrados</option>
    </select>
    <select id="hall-origen" onchange="cargarHallazgos()" style="width:auto;display:inline-block">
      <option value="">Todos los orígenes</option>
      <option value="INVIMA">INVIMA</option>
      <option value="BPM_interna">BPM interna</option>
      <option value="autoinspeccion">Autoinspección</option>
      <option value="auditoria_externa">Auditoría externa</option>
      <option value="queja_cliente">Queja cliente</option>
    </select>
  </div>
  <div id="hall-list"></div>
</div>

<!-- MODAL: Nueva CAPA -->
<div id="modal-capa" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.7);z-index:9999;align-items:center;justify-content:center;padding:20px">
  <div style="background:#fff;border-radius:14px;padding:22px 26px;max-width:560px;width:100%;max-height:90vh;overflow-y:auto">
    <h3 style="color:#0c4a6e;margin-bottom:14px">Nueva desviación / no-conformidad</h3>
    <div class="row">
      <div><label>Tipo</label>
        <select id="cp-tipo">
          <option value="desviacion">Desviación</option>
          <option value="no_conformidad">No-conformidad</option>
          <option value="queja">Queja cliente</option>
          <option value="sugerencia">Sugerencia</option>
        </select>
      </div>
      <div><label>Severidad</label>
        <select id="cp-sev">
          <option value="alta">Alta</option>
          <option value="media" selected>Media</option>
          <option value="baja">Baja</option>
        </select>
      </div>
    </div>
    <div style="margin-bottom:10px"><label>Título</label><input id="cp-titulo" type="text" placeholder="Ej: Desviación procesado lote 261001"></div>
    <div style="margin-bottom:10px"><label>Descripción</label><textarea id="cp-descr" rows="3" placeholder="Qué pasó, cómo se detectó..."></textarea></div>
    <div class="row">
      <div><label>Producto / lote relacionado</label><input id="cp-producto" type="text" placeholder="Ej: Renova C10 lote 261001"></div>
      <div><label>Lote</label><input id="cp-lote" type="text"></div>
    </div>
    <div class="row">
      <div><label>Responsable (username)</label><input id="cp-resp" type="text" placeholder="aseguramiento.espagiria"></div>
      <div><label>Fecha objetivo</label><input id="cp-objetivo" type="date"></div>
    </div>
    <div style="margin-bottom:14px"><label>Acción inmediata tomada</label><textarea id="cp-inmediata" rows="2" placeholder="¿Qué se hizo apenas se detectó?"></textarea></div>
    <div style="display:flex;justify-content:flex-end;gap:8px">
      <button class="btn btn-secondary" onclick="cerrarModal('modal-capa')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarCAPA()">Crear</button>
    </div>
  </div>
</div>

<!-- MODAL: Nuevo hallazgo -->
<div id="modal-hall" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.7);z-index:9999;align-items:center;justify-content:center;padding:20px">
  <div style="background:#fff;border-radius:14px;padding:22px 26px;max-width:560px;width:100%;max-height:90vh;overflow-y:auto">
    <h3 style="color:#0c4a6e;margin-bottom:14px">Nuevo hallazgo</h3>
    <div class="row">
      <div><label>Origen</label>
        <select id="hl-origen">
          <option value="INVIMA">INVIMA</option>
          <option value="BPM_interna">BPM interna</option>
          <option value="autoinspeccion" selected>Autoinspección</option>
          <option value="auditoria_externa">Auditoría externa</option>
          <option value="queja_cliente">Queja cliente</option>
          <option value="otro">Otro</option>
        </select>
      </div>
      <div><label>Severidad</label>
        <select id="hl-sev">
          <option value="critico">Crítico</option>
          <option value="mayor">Mayor</option>
          <option value="menor" selected>Menor</option>
          <option value="observacion">Observación</option>
        </select>
      </div>
    </div>
    <div style="margin-bottom:10px"><label>Título</label><input id="hl-titulo" type="text" placeholder="Ej: Tubería sin identificar"></div>
    <div style="margin-bottom:10px"><label>Descripción</label><textarea id="hl-descr" rows="3"></textarea></div>
    <div class="row">
      <div><label>Área</label><input id="hl-area" type="text" placeholder="Planta, Calidad, Bodega..."></div>
      <div><label>Fecha límite</label><input id="hl-flim" type="date"></div>
    </div>
    <div style="margin-bottom:10px"><label>Responsable (username)</label><input id="hl-resp" type="text"></div>
    <div style="margin-bottom:14px"><label>Acción propuesta</label><textarea id="hl-accion" rows="2"></textarea></div>
    <div style="display:flex;justify-content:flex-end;gap:8px">
      <button class="btn btn-secondary" onclick="cerrarModal('modal-hall')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarHallazgo()">Crear</button>
    </div>
  </div>
</div>

<!-- MODAL: Detalle ejecuciones cronograma -->
<div id="modal-cron" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.7);z-index:9999;align-items:center;justify-content:center;padding:20px">
  <div style="background:#fff;border-radius:14px;padding:22px 26px;max-width:680px;width:100%;max-height:90vh;overflow-y:auto">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
      <h3 id="cron-modal-title" style="color:#0c4a6e"></h3>
      <button class="btn btn-secondary btn-sm" onclick="cerrarModal('modal-cron')">×</button>
    </div>
    <div id="cron-modal-body"></div>
  </div>
</div>

<script>
var ES_RESPONSABLE = ({es_responsable} === true);
var CRON_ID_ACTUAL = null;

function _esc(s){return (s==null?'':String(s)).replace(/[<>&"']/g,function(c){return {'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c];});}
function _toast(m,ok){alert((ok?'✓ ':'⚠ ')+m);}
function cerrarModal(id){document.getElementById(id).style.display='none';}

function switchPane(p){
  document.querySelectorAll('.pane').forEach(function(el){el.classList.toggle('on', el.id==='pane-'+p);});
  document.querySelectorAll('.tabbtn').forEach(function(b){b.classList.toggle('on', b.dataset.pane===p);});
  if(p==='cron') cargarCronogramas();
  if(p==='capa') cargarCAPA();
  if(p==='hall') cargarHallazgos();
}

async function cargarKPIs(){
  try{
    var r = await fetch('/api/compliance/kpis'); var d = await r.json();
    var box = document.getElementById('kpis');
    var pct = d.cronogramas_cumplimiento_promedio || 0;
    var clase_pct = pct < 50 ? 'danger' : pct < 80 ? 'warn' : '';
    box.innerHTML =
      '<div class="kpi '+clase_pct+'"><div class="kpi-l">📅 Cumplimiento BPM</div><div class="kpi-v">'+pct+'%</div><div class="kpi-s">'+d.cronogramas_total+' cronogramas activos</div></div>' +
      '<div class="kpi '+(d.capa_vencidas_5d>0?'danger':d.capa_abiertas>0?'warn':'')+'"><div class="kpi-l">⚠ CAPA abiertas</div><div class="kpi-v">'+d.capa_abiertas+'</div><div class="kpi-s">'+d.capa_vencidas_5d+' >5 días</div></div>' +
      '<div class="kpi '+(d.hallazgos_invima_abiertos>0?'danger':d.hallazgos_vencidos>0?'warn':'')+'"><div class="kpi-l">🔍 Hallazgos abiertos</div><div class="kpi-v">'+d.hallazgos_abiertos+'</div><div class="kpi-s">'+d.hallazgos_invima_abiertos+' INVIMA · '+d.hallazgos_vencidos+' vencidos</div></div>';
  }catch(e){}
}

// ── CRONOGRAMAS ────────────────────────────────────────────────────
async function cargarCronogramas(){
  document.getElementById('year-cron').textContent = new Date().getFullYear();
  try{
    var r = await fetch('/api/compliance/cronogramas');
    var d = await r.json();
    var box = document.getElementById('cronograma-list');
    if(!d.cronogramas.length){ box.innerHTML = '<div class="empty">Sin cronogramas activos.</div>'; return; }
    box.innerHTML = d.cronogramas.map(function(c){
      var pct = c.pct_cumplimiento;
      var clase = pct<50?'danger':pct<80?'warn':'';
      return '<div class="card" style="cursor:pointer" onclick="abrirCronograma('+c.id+',&quot;'+_esc(c.codigo+' — '+c.nombre)+'&quot;)">' +
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">' +
          '<div style="flex:1;min-width:200px">' +
            '<div style="font-weight:700;color:#0c4a6e;font-family:monospace;font-size:12px">'+_esc(c.codigo)+'</div>' +
            '<div style="font-size:14px;font-weight:600;color:#0f172a;margin-top:2px">'+_esc(c.nombre)+'</div>' +
            '<div style="font-size:11px;color:#64748b;margin-top:4px">Frecuencia: '+_esc(c.frecuencia||'—')+' · Responsable: '+_esc(c.responsable||'—')+'</div>' +
          '</div>' +
          '<div style="text-align:right">' +
            '<div style="font-size:24px;font-weight:800;color:'+(clase==='danger'?'#dc2626':clase==='warn'?'#d97706':'#16a34a')+'">'+pct+'%</div>' +
            '<div style="font-size:10px;color:#64748b">'+c.ejecutadas+'/'+c.objetivo+' año</div>' +
          '</div>' +
        '</div>' +
        '<div class="progress"><div class="progress-bar '+clase+'" style="width:'+pct+'%"></div></div>' +
        '<div style="margin-top:6px;font-size:11px;color:#64748b">' +
          '✅ '+c.ejecutadas+' ejecutadas · ' +
          '⚠ '+c.vencidas+' vencidas · ' +
          '📅 '+c.proximas+' próximas pendientes' +
        '</div>' +
      '</div>';
    }).join('');
  }catch(e){ document.getElementById('cronograma-list').innerHTML = '<div class="empty">Error al cargar.</div>'; }
}

async function abrirCronograma(cron_id, titulo){
  CRON_ID_ACTUAL = cron_id;
  document.getElementById('cron-modal-title').textContent = titulo;
  var body = document.getElementById('cron-modal-body');
  body.innerHTML = '<div class="empty">Cargando...</div>';
  document.getElementById('modal-cron').style.display = 'flex';
  try{
    var r = await fetch('/api/compliance/cronogramas/'+cron_id+'/ejecuciones');
    var d = await r.json();
    var ejs = d.ejecuciones || [];
    var html = '<div style="margin-bottom:14px"><label>Programar nueva ejecución (fecha planeada)</label>' +
      '<div style="display:flex;gap:6px"><input type="date" id="ej-fecha" style="flex:1">' +
      '<button class="btn btn-primary" onclick="agregarEjecucion()">+ Agregar</button></div></div>';
    if(!ejs.length){ html += '<div class="empty">Sin ejecuciones registradas. Agrega la primera arriba.</div>'; }
    else {
      html += '<table><thead><tr><th>Planeada</th><th>Real</th><th>Por</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>';
      ejs.forEach(function(e){
        var btn = (e.estado==='pendiente') ?
          '<button class="btn btn-success btn-sm" onclick="cumplirEjecucion('+e.id+')">✓ Marcar cumplido</button>'
          : '';
        html += '<tr><td>'+_esc(e.fecha_planeada)+'</td><td>'+_esc(e.fecha_real||'—')+
                '</td><td>'+_esc(e.ejecutado_por||'—')+
                '</td><td><span class="badge b-'+e.estado+'">'+e.estado+'</span></td><td>'+btn+'</td></tr>';
      });
      html += '</tbody></table>';
    }
    body.innerHTML = html;
  }catch(e){ body.innerHTML = '<div class="empty">Error.</div>'; }
}

async function agregarEjecucion(){
  var f = document.getElementById('ej-fecha').value;
  if(!f){ _toast('Selecciona fecha', 0); return; }
  try{
    var r = await fetch('/api/compliance/cronogramas/'+CRON_ID_ACTUAL+'/ejecuciones', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({fecha_planeada: f})
    });
    if((await r.json()).ok){ abrirCronograma(CRON_ID_ACTUAL, document.getElementById('cron-modal-title').textContent); cargarCronogramas(); cargarKPIs(); }
  }catch(e){ _toast('Error', 0); }
}

async function cumplirEjecucion(ej_id){
  var url = prompt('URL de evidencia (opcional, foto/registro):');
  try{
    var r = await fetch('/api/compliance/ejecuciones/'+ej_id+'/cumplir', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({evidencia_url: url||null})
    });
    if((await r.json()).ok){ abrirCronograma(CRON_ID_ACTUAL, document.getElementById('cron-modal-title').textContent); cargarCronogramas(); cargarKPIs(); _toast('Marcado cumplido', 1); }
  }catch(e){ _toast('Error', 0); }
}

// ── CAPA ────────────────────────────────────────────────────
function abrirModalCAPA(){
  document.getElementById('cp-titulo').value='';
  document.getElementById('cp-descr').value='';
  document.getElementById('cp-producto').value='';
  document.getElementById('cp-lote').value='';
  document.getElementById('cp-resp').value='aseguramiento.espagiria';
  document.getElementById('cp-objetivo').value='';
  document.getElementById('cp-inmediata').value='';
  document.getElementById('modal-capa').style.display='flex';
}

async function guardarCAPA(){
  var titulo = document.getElementById('cp-titulo').value.trim();
  if(!titulo){ _toast('Título requerido', 0); return; }
  var body = {
    tipo: document.getElementById('cp-tipo').value,
    severidad: document.getElementById('cp-sev').value,
    titulo: titulo,
    descripcion: document.getElementById('cp-descr').value,
    producto_relacionado: document.getElementById('cp-producto').value,
    lote: document.getElementById('cp-lote').value,
    responsable: document.getElementById('cp-resp').value,
    fecha_objetivo: document.getElementById('cp-objetivo').value,
    accion_inmediata: document.getElementById('cp-inmediata').value
  };
  try{
    var r = await fetch('/api/compliance/capa', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if(d.ok){ _toast('Creada: '+d.codigo, 1); cerrarModal('modal-capa'); cargarCAPA(); cargarKPIs(); }
    else { _toast('Error: '+(d.error||'?'), 0); }
  }catch(e){ _toast('Error de red', 0); }
}

async function cargarCAPA(){
  var estado = document.getElementById('capa-filtro').value;
  try{
    var r = await fetch('/api/compliance/capa'+(estado?'?estado='+estado:''));
    var d = await r.json();
    var box = document.getElementById('capa-list');
    if(!d.capa.length){ box.innerHTML = '<div class="empty">Sin desviaciones registradas.</div>'; return; }
    box.innerHTML = d.capa.map(function(x){
      var diasAlert = x.dias_abierta>5 && x.estado!=='cerrada' ? ' <span style="background:#dc2626;color:#fff;padding:2px 6px;border-radius:6px;font-size:10px">⚠ '+x.dias_abierta+' días</span>' : '';
      return '<div class="card">' +
        '<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px">' +
          '<div><b style="font-family:monospace;color:#0c4a6e">'+_esc(x.codigo)+'</b> <span class="badge b-'+x.severidad+'">'+x.severidad+'</span> <span class="badge b-'+x.estado+'">'+_esc(x.estado)+'</span>'+diasAlert+'</div>' +
          '<div style="font-size:11px;color:#94a3b8">'+_esc(x.fecha_apertura)+' → '+_esc(x.fecha_objetivo||'sin obj')+'</div>' +
        '</div>' +
        '<div style="font-weight:600;margin-top:6px">'+_esc(x.titulo)+'</div>' +
        (x.descripcion?'<div style="color:#475569;font-size:13px;margin-top:4px">'+_esc(x.descripcion)+'</div>':'') +
        (x.producto_relacionado?'<div style="font-size:11px;color:#64748b;margin-top:4px">📦 '+_esc(x.producto_relacionado)+(x.lote?' lote '+_esc(x.lote):'')+'</div>':'') +
        '<div style="font-size:11px;color:#64748b;margin-top:4px">Responsable: '+_esc(x.responsable||'—')+'</div>' +
        (ES_RESPONSABLE && x.estado!=='cerrada' ? '<div style="margin-top:8px"><button class="btn btn-success btn-sm" onclick="cerrarCAPA('+x.id+')">✓ Cerrar desviación</button></div>' : '') +
        '</div>';
    }).join('');
  }catch(e){ document.getElementById('capa-list').innerHTML = '<div class="empty">Error.</div>'; }
}

async function cerrarCAPA(id){
  var raiz = prompt('Causa raíz identificada:'); if(!raiz) return;
  var corr = prompt('Acción correctiva tomada:');
  var prev = prompt('Acción preventiva (opcional):');
  try{
    var r = await fetch('/api/compliance/capa/'+id, {method:'PATCH', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({estado:'cerrada', causa_raiz:raiz, accion_correctiva:corr||null, accion_preventiva:prev||null})});
    if((await r.json()).ok){ _toast('Cerrada', 1); cargarCAPA(); cargarKPIs(); }
  }catch(e){ _toast('Error', 0); }
}

// ── HALLAZGOS ────────────────────────────────────────────────────
function abrirModalHallazgo(){
  ['hl-titulo','hl-descr','hl-area','hl-flim','hl-resp','hl-accion'].forEach(function(id){document.getElementById(id).value='';});
  document.getElementById('hl-resp').value='aseguramiento.espagiria';
  document.getElementById('modal-hall').style.display='flex';
}

async function guardarHallazgo(){
  var t = document.getElementById('hl-titulo').value.trim();
  if(!t){ _toast('Título requerido', 0); return; }
  var body = {
    titulo: t,
    origen: document.getElementById('hl-origen').value,
    severidad: document.getElementById('hl-sev').value,
    descripcion: document.getElementById('hl-descr').value,
    area: document.getElementById('hl-area').value,
    fecha_limite: document.getElementById('hl-flim').value,
    responsable: document.getElementById('hl-resp').value,
    accion_propuesta: document.getElementById('hl-accion').value
  };
  try{
    var r = await fetch('/api/compliance/hallazgos', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if(d.ok){ _toast('Creado: '+d.codigo, 1); cerrarModal('modal-hall'); cargarHallazgos(); cargarKPIs(); }
  }catch(e){ _toast('Error', 0); }
}

async function cargarHallazgos(){
  var qs = [];
  var e = document.getElementById('hall-filtro').value; if(e) qs.push('estado='+e);
  var o = document.getElementById('hall-origen').value; if(o) qs.push('origen='+o);
  try{
    var r = await fetch('/api/compliance/hallazgos'+(qs.length?'?'+qs.join('&'):''));
    var d = await r.json();
    var box = document.getElementById('hall-list');
    if(!d.hallazgos.length){ box.innerHTML = '<div class="empty">Sin hallazgos.</div>'; return; }
    box.innerHTML = d.hallazgos.map(function(h){
      var venc = h.vencido ? ' <span style="background:#dc2626;color:#fff;padding:2px 6px;border-radius:6px;font-size:10px">VENCIDO '+Math.abs(h.dias_a_limite)+'d</span>' : (h.dias_a_limite!=null && h.dias_a_limite<=7 && h.estado!=='cerrado'?' <span style="background:#d97706;color:#fff;padding:2px 6px;border-radius:6px;font-size:10px">'+h.dias_a_limite+'d restantes</span>':'');
      return '<div class="card" style="border-left:4px solid '+(h.severidad==='critico'?'#dc2626':h.severidad==='mayor'?'#d97706':'#64748b')+'">' +
        '<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px">' +
          '<div><b style="font-family:monospace;color:#0c4a6e">'+_esc(h.codigo)+'</b> <span class="badge b-'+h.origen+'">'+_esc(h.origen)+'</span> <span class="badge b-'+h.severidad+'">'+_esc(h.severidad)+'</span> <span class="badge b-'+h.estado+'">'+_esc(h.estado)+'</span>'+venc+'</div>' +
          '<div style="font-size:11px;color:#94a3b8">'+_esc(h.fecha_deteccion)+(h.fecha_limite?' → '+_esc(h.fecha_limite):'')+'</div>' +
        '</div>' +
        '<div style="font-weight:600;margin-top:6px">'+_esc(h.titulo)+'</div>' +
        (h.descripcion?'<div style="color:#475569;font-size:13px;margin-top:4px">'+_esc(h.descripcion)+'</div>':'') +
        '<div style="font-size:11px;color:#64748b;margin-top:4px">Área: '+_esc(h.area||'—')+' · Responsable: '+_esc(h.responsable||'—')+'</div>' +
        (h.accion_propuesta?'<div style="font-size:12px;color:#475569;margin-top:4px"><b>Acción:</b> '+_esc(h.accion_propuesta)+'</div>':'') +
        (ES_RESPONSABLE && h.estado!=='cerrado' ? '<div style="margin-top:8px;display:flex;gap:6px"><button class="btn btn-warn btn-sm" onclick="enProcesoHallazgo('+h.id+')">→ En proceso</button><button class="btn btn-success btn-sm" onclick="cerrarHallazgo('+h.id+')">✓ Cerrar</button></div>' : '') +
        '</div>';
    }).join('');
  }catch(e){ document.getElementById('hall-list').innerHTML = '<div class="empty">Error.</div>'; }
}

async function enProcesoHallazgo(id){
  try{
    var r = await fetch('/api/compliance/hallazgos/'+id, {method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({estado:'en_proceso'})});
    if((await r.json()).ok){ cargarHallazgos(); cargarKPIs(); }
  }catch(e){ _toast('Error', 0); }
}

async function cerrarHallazgo(id){
  var url = prompt('URL de evidencia de cierre (opcional):');
  try{
    var r = await fetch('/api/compliance/hallazgos/'+id, {method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({estado:'cerrado', evidencia_cierre_url: url||null})});
    if((await r.json()).ok){ cargarHallazgos(); cargarKPIs(); _toast('Cerrado', 1); }
  }catch(e){ _toast('Error', 0); }
}

// init
cargarKPIs();
cargarCronogramas();
</script>
</body>
</html>
"""
