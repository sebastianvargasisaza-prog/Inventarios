"""Template Bienestar — notificaciones empleados + capacitaciones.

Sebastian (30-abr-2026): UI minimalista con 3 tabs:
  Mis Notificaciones (crear + ver propias)
  Mis Capacitaciones (ver, abrir examen Claude, calificar)
  Bandeja Jefe (solo es_jefe=true) — ver TODAS, asignar capacitaciones, resolver
"""

HTML = r"""<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Bienestar · HHA Group</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos12">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#f5f4f2;color:#1c1917;font-size:14px}
.topbar{background:linear-gradient(90deg,#1a4a7a,#0f766e);color:#fff;padding:14px 20px;display:flex;align-items:center;gap:14px}
.topbar h1{font-size:18px;font-weight:700;flex:1}
.topbar a{color:#cbd5e1;text-decoration:none;font-size:13px;padding:6px 12px;border-radius:6px;background:rgba(255,255,255,0.1)}
.topbar a:hover{background:rgba(255,255,255,0.2);color:#fff}
.tabs{background:#fff;border-bottom:2px solid #e2e8f0;display:flex;gap:0}
.tabbtn{padding:12px 22px;font-size:13px;font-weight:600;color:#64748b;background:none;border:none;cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-2px}
.tabbtn:hover{background:#f8fafc;color:#1a4a7a}
.tabbtn.on{color:#1a4a7a;border-bottom-color:#0f766e;font-weight:700}
.pane{display:none;padding:22px 24px;max-width:1200px;margin:0 auto}
.pane.on{display:block}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:16px;margin-bottom:14px}
.card h3{font-size:15px;color:#1a4a7a;margin-bottom:10px}
.btn{padding:8px 16px;border:none;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer}
.btn-primary{background:#0f766e;color:#fff}.btn-primary:hover{background:#115e59}
.btn-secondary{background:#e2e8f0;color:#475569}.btn-secondary:hover{background:#cbd5e1}
.btn-danger{background:#dc2626;color:#fff}
.btn-warn{background:#d97706;color:#fff}
.btn-success{background:#16a34a;color:#fff}
.btn-sm{padding:5px 10px;font-size:12px}
input,select,textarea{padding:8px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;font-family:inherit;width:100%}
input:focus,select:focus,textarea:focus{border-color:#0f766e;outline:none}
.row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.row > * {flex:1;min-width:180px}
label{font-size:12px;font-weight:600;color:#475569;display:block;margin-bottom:4px}
.badge{padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700;text-transform:uppercase}
.b-pendiente{background:#fef3c7;color:#92400e}
.b-aprobada{background:#d1fae5;color:#065f46}
.b-rechazada{background:#fee2e2;color:#991b1b}
.b-vista{background:#e0e7ff;color:#3730a3}
.b-en_curso{background:#dbeafe;color:#1e40af}
.b-completada{background:#d1fae5;color:#065f46}
.b-reprobada{background:#fee2e2;color:#991b1b}
.b-vencida{background:#fee2e2;color:#991b1b}
.empty{text-align:center;color:#94a3b8;padding:30px;font-style:italic}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media (max-width:768px){.grid-2{grid-template-columns:1fr}}
.q-block{background:#f8fafc;border-left:3px solid #0f766e;padding:10px 14px;margin-bottom:10px;border-radius:0 6px 6px 0}
.q-block .q{font-weight:600;color:#1a4a7a;margin-bottom:6px}
.q-block .ctx{font-size:11px;color:#64748b;font-style:italic;margin-bottom:6px}
.q-block textarea{min-height:60px;font-size:13px}
.score-card{background:linear-gradient(135deg,#0f766e,#16a34a);color:#fff;padding:18px;border-radius:10px;text-align:center;margin-bottom:14px}
.score-card.fail{background:linear-gradient(135deg,#dc2626,#92400e)}
.score-card .num{font-size:48px;font-weight:800}
</style>
</head>
<body>
<div class="topbar">
  <h1>🌱 Bienestar HHA · <span style="font-weight:400">{usuario}</span></h1>
  <a href="/modulos">← Módulos</a>
</div>

<div class="tabs">
  <button class="tabbtn on" data-pane="mis-notif" onclick="switchPane('mis-notif')">📩 Mis Notificaciones</button>
  <button class="tabbtn" data-pane="mis-cap" onclick="switchPane('mis-cap')">🎓 Mis Capacitaciones</button>
  <button class="tabbtn" data-pane="trimestral" onclick="switchPane('trimestral')">🏆 Empleado destacado</button>
  <button class="tabbtn" data-pane="bandeja" id="tn-bandeja" style="display:none" onclick="switchPane('bandeja')">📊 Bandeja jefe</button>
</div>

<!-- PANE: Mis Notificaciones -->
<div id="pane-mis-notif" class="pane on">
  <div class="card">
    <h3>📨 Crear nueva notificación</h3>
    <p style="color:#64748b;font-size:12px;margin-bottom:12px">Reporta a tus jefes: estado de salud, permisos, citas médicas, enfermedades, licencias.</p>
    <div class="row">
      <div>
        <label>Tipo</label>
        <select id="nf-tipo">
          <option value="cita_medica">🏥 Cita médica</option>
          <option value="enfermedad">🤒 Enfermedad / Incapacidad</option>
          <option value="permiso">📋 Permiso</option>
          <option value="salud">💊 Estado de salud</option>
          <option value="licencia">📄 Licencia</option>
          <option value="otro">📝 Otro</option>
        </select>
      </div>
      <div>
        <label>Asunto (corto)</label>
        <input id="nf-asunto" type="text" placeholder="Ej: Cita IPS jueves 9am">
      </div>
    </div>
    <div class="row">
      <div>
        <label>Fecha inicio (opcional)</label>
        <input id="nf-fini" type="date">
      </div>
      <div>
        <label>Fecha fin (opcional)</label>
        <input id="nf-ffin" type="date">
      </div>
    </div>
    <div style="margin-bottom:10px">
      <label>Descripción / detalles</label>
      <textarea id="nf-descr" rows="3" placeholder="Cuéntale al jefe los detalles..."></textarea>
    </div>
    <div style="margin-bottom:14px">
      <label>URL adjunto (foto incapacidad, orden médica)</label>
      <input id="nf-adjunto" type="url" placeholder="https://...">
    </div>
    <button class="btn btn-primary" onclick="crearNotificacion()">Enviar al jefe</button>
  </div>

  <h3 style="font-size:15px;color:#1a4a7a;margin-bottom:10px">📜 Mi historial</h3>
  <div id="lista-mis-notif"></div>
</div>

<!-- PANE: Mis Capacitaciones -->
<div id="pane-mis-cap" class="pane">
  <h3 style="font-size:15px;color:#1a4a7a;margin-bottom:10px">🎓 Mis capacitaciones asignadas</h3>
  <p style="color:#64748b;font-size:12px;margin-bottom:14px">Tu jefe te asigna material (videos, PDFs, NotebookLM). Revisa, haz el autoexamen y obtén tu nota. Las completadas suman a tu historial RH.</p>
  <div id="lista-mis-cap"></div>
</div>

<!-- PANE: Empleado destacado trimestral -->
<div id="pane-trimestral" class="pane">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:8px">
    <h3 style="font-size:15px;color:#1a4a7a">🏆 Ranking trimestral con métricas objetivas</h3>
    <div style="display:flex;gap:8px;align-items:center">
      <select id="tri-year" onchange="cargarTrimestral()" style="width:auto"></select>
      <select id="tri-quarter" onchange="cargarTrimestral()" style="width:auto">
        <option value="1">Q1 (ene-mar)</option>
        <option value="2">Q2 (abr-jun)</option>
        <option value="3">Q3 (jul-sep)</option>
        <option value="4">Q4 (oct-dic)</option>
      </select>
    </div>
  </div>
  <p style="color:#64748b;font-size:12px;margin-bottom:14px">
    Score = capacitaciones aprobadas × 25 + nota_prom × 0.4 + tareas × 5 +
    producciones × 4 − desviaciones_pendientes × 10. Sebastian (30-abr-2026):
    "trimestral, no mensual — mensual se vuelve costumbre".
  </p>
  <div id="trimestral-content"></div>
</div>

<!-- PANE: Bandeja jefe (admin/jefes) -->
<div id="pane-bandeja" class="pane">
  <div class="grid-2">
    <div>
      <h3 style="font-size:15px;color:#1a4a7a;margin-bottom:10px">📩 Notificaciones pendientes (todo el equipo)</h3>
      <div id="bandeja-notif"></div>
    </div>
    <div>
      <h3 style="font-size:15px;color:#1a4a7a;margin-bottom:10px">🎓 Asignar nueva capacitación</h3>
      <div class="card">
        <div class="row">
          <div>
            <label>Asignar a (username)</label>
            <select id="cap-asignado-a">
              <option value="mayerlin">Mayerlin Rivera</option>
              <option value="camilo">Camilo García</option>
              <option value="milton">Milton Sanabria</option>
              <option value="sebastian_murillo">Sebastian Murillo</option>
            </select>
          </div>
          <div>
            <label>Tipo material</label>
            <select id="cap-tipo">
              <option value="video">▶ Video</option>
              <option value="notebooklm">🧠 NotebookLM</option>
              <option value="pdf">📄 PDF</option>
              <option value="articulo">📰 Artículo</option>
              <option value="otro">Otro</option>
            </select>
          </div>
        </div>
        <div style="margin-bottom:10px">
          <label>Título de la capacitación</label>
          <input id="cap-titulo" type="text" placeholder="Ej: BPM básico — manejo de marmita">
        </div>
        <div style="margin-bottom:10px">
          <label>URL del material (video / NotebookLM / PDF)</label>
          <input id="cap-url" type="url" placeholder="https://www.youtube.com/... o https://notebooklm.google.com/...">
        </div>
        <div style="margin-bottom:10px">
          <label>Notas / contexto para Claude (qué evaluar)</label>
          <textarea id="cap-notas" rows="2" placeholder="Ej: Que entiendan límites de temperatura, presión, registro en bitácora"></textarea>
        </div>
        <div class="row">
          <div>
            <label>Fecha límite</label>
            <input id="cap-flim" type="date">
          </div>
          <div>
            <label>Nota mínima (0-100)</label>
            <input id="cap-notamin" type="number" min="0" max="100" value="70">
          </div>
        </div>
        <button class="btn btn-primary" onclick="asignarCapacitacion()" style="margin-top:8px">Asignar</button>
      </div>
      <h3 style="font-size:15px;color:#1a4a7a;margin:18px 0 10px">📊 Historial de capacitaciones del equipo</h3>
      <div id="bandeja-capacitaciones"></div>
    </div>
  </div>
</div>

<!-- MODAL: Examen autoevaluacion Claude -->
<div id="modal-examen" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,0.7);z-index:9999;align-items:center;justify-content:center;padding:20px">
  <div style="background:#fff;border-radius:14px;padding:22px 26px;max-width:680px;width:100%;max-height:90vh;overflow-y:auto">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
      <h3 style="color:#1a4a7a;font-size:17px">🧠 Autoexamen con Claude</h3>
      <button onclick="cerrarExamen()" class="btn btn-secondary btn-sm">×</button>
    </div>
    <div id="exam-info" style="background:#f0f9ff;border-left:3px solid #0ea5e9;padding:10px 14px;margin-bottom:14px;border-radius:0 6px 6px 0;font-size:13px"></div>
    <div id="exam-body"></div>
    <div id="exam-result" style="display:none;margin-top:16px"></div>
  </div>
</div>

<script>

// CSRF defense-in-depth - Sebastian 3-may-2026
function _csrf() {
  var m = document.cookie.match(/(?:^|;[ \t]*)csrf_token=([^;]+)/);
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
var ES_JEFE = ({es_jefe} === true);
var MI_USERNAME = '';

function switchPane(p){
  document.querySelectorAll('.pane').forEach(function(el){ el.classList.toggle('on', el.id==='pane-'+p); });
  document.querySelectorAll('.tabbtn').forEach(function(b){ b.classList.toggle('on', b.dataset.pane===p); });
  if(p==='mis-notif')   cargarMisNotif();
  if(p==='mis-cap')     cargarMisCap();
  if(p==='trimestral')  cargarTrimestral();
  if(p==='bandeja')     cargarBandeja();
}

async function cargarTrimestral(){
  // Llenar selectors si vacios
  var yr = document.getElementById('tri-year');
  if(!yr.options.length){
    var thisYear = new Date().getFullYear();
    for(var y=thisYear; y>=thisYear-2; y--){
      var op = document.createElement('option'); op.value=y; op.textContent=y; yr.appendChild(op);
    }
    yr.value = thisYear;
    var thisQ = Math.floor((new Date().getMonth())/3) + 1;
    document.getElementById('tri-quarter').value = thisQ;
  }
  var year = yr.value;
  var q = document.getElementById('tri-quarter').value;
  var box = document.getElementById('trimestral-content');
  box.innerHTML = '<div class="empty">⏳ Calculando...</div>';
  try{
    var r = await fetch('/api/bienestar/empleado-trimestral?year='+year+'&quarter='+q);
    var d = await r.json();
    var rk = d.ranking || [];
    if(!rk.length){ box.innerHTML='<div class="empty">Sin datos para este trimestre.</div>'; return; }
    var dest = rk.find(function(x){return x.destacado;});
    var html = '';
    if(dest && dest.score > 0){
      html += '<div style="background:linear-gradient(135deg,#fbbf24,#d97706);color:#fff;padding:24px;border-radius:14px;text-align:center;margin-bottom:18px;box-shadow:0 8px 24px rgba(217,119,6,.3)">' +
        '<div style="font-size:13px;text-transform:uppercase;letter-spacing:2px;font-weight:700;margin-bottom:6px">🏆 Empleado destacado · '+_esc(d.rango)+'</div>' +
        '<div style="font-size:32px;font-weight:800;margin:8px 0">'+_esc(dest.nombre_completo)+'</div>' +
        '<div style="font-size:18px;font-weight:600">Score: '+dest.score+' pts</div>' +
        '<div style="font-size:12px;margin-top:10px;opacity:.9">'+
          dest.capacitaciones_aprobadas+' capacitaciones · '+dest.tareas_completadas+' tareas · '+dest.producciones+' producciones'+
        '</div>' +
      '</div>';
    }
    html += '<table style="width:100%;border-collapse:collapse;font-size:13px;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.05)">' +
      '<thead><tr style="background:#1a4a7a;color:#fff">' +
      '<th style="padding:10px;text-align:left">#</th>' +
      '<th style="padding:10px;text-align:left">Operario</th>' +
      '<th style="padding:10px;text-align:center">Capac.</th>' +
      '<th style="padding:10px;text-align:center">Nota prom.</th>' +
      '<th style="padding:10px;text-align:center">Tareas</th>' +
      '<th style="padding:10px;text-align:center">Producciones</th>' +
      '<th style="padding:10px;text-align:center">Desv. abiertas</th>' +
      '<th style="padding:10px;text-align:right">Score</th>' +
      '</tr></thead><tbody>';
    rk.forEach(function(p,i){
      var rowBg = i===0 ? '#fef3c7' : i===1 ? '#f1f5f9' : i===2 ? '#fed7aa' : '#fff';
      html += '<tr style="background:'+rowBg+';border-bottom:1px solid #e2e8f0">' +
        '<td style="padding:8px;font-weight:700;color:#0f766e">'+(i+1)+(i===0?' 🥇':i===1?' 🥈':i===2?' 🥉':'')+'</td>' +
        '<td style="padding:8px;font-weight:600">'+_esc(p.nombre_completo)+'</td>' +
        '<td style="padding:8px;text-align:center">'+p.capacitaciones_aprobadas+'</td>' +
        '<td style="padding:8px;text-align:center;color:#0f766e">'+p.nota_promedio+'</td>' +
        '<td style="padding:8px;text-align:center">'+p.tareas_completadas+'</td>' +
        '<td style="padding:8px;text-align:center">'+p.producciones+'</td>' +
        '<td style="padding:8px;text-align:center;color:'+(p.desviaciones_pendientes>0?'#dc2626':'#94a3b8')+'">'+p.desviaciones_pendientes+'</td>' +
        '<td style="padding:8px;text-align:right;font-weight:800;color:'+(p.score>50?'#16a34a':p.score>0?'#0f766e':'#94a3b8')+'">'+p.score+'</td>' +
      '</tr>';
    });
    html += '</tbody></table>';
    box.innerHTML = html;
  }catch(e){ box.innerHTML='<div class="empty">Error al cargar.</div>'; }
}

function _esc(s){ return (s==null?'':String(s)).replace(/[<>&"']/g,function(c){return {'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c];}); }
function _toast(msg, ok){ alert((ok?'✓ ':'⚠ ')+msg); }

// ─── NOTIFICACIONES ─────────────────────────────────────────────────
async function crearNotificacion(){
  var tipo = document.getElementById('nf-tipo').value;
  var asunto = document.getElementById('nf-asunto').value.trim();
  if(!asunto){ _toast('Pon un asunto corto', 0); return; }
  var body = {
    tipo: tipo, asunto: asunto,
    descripcion: document.getElementById('nf-descr').value,
    fecha_inicio: document.getElementById('nf-fini').value,
    fecha_fin: document.getElementById('nf-ffin').value,
    adjunto_url: document.getElementById('nf-adjunto').value
  };
  try{
    var r = await fetch('/api/bienestar/notificaciones', _fetchOpts('POST', body));
    var d = await r.json();
    if(d.ok){
      _toast('Notificación enviada al jefe', 1);
      document.getElementById('nf-asunto').value = '';
      document.getElementById('nf-descr').value = '';
      cargarMisNotif();
    } else { _toast('Error: '+(d.error||'?'), 0); }
  }catch(e){ _toast('Error de red', 0); }
}

async function cargarMisNotif(){
  try{
    var r = await fetch('/api/bienestar/notificaciones?solo_mias=1');
    var d = await r.json();
    var box = document.getElementById('lista-mis-notif');
    if(!d.notificaciones.length){
      box.innerHTML = '<div class="empty">Aún no has enviado notificaciones.</div>';
      return;
    }
    box.innerHTML = d.notificaciones.map(function(n){
      var coment = n.comentario_jefe ? '<div style="margin-top:8px;background:#f0fdf4;border-left:3px solid #16a34a;padding:8px 12px;font-size:12px;border-radius:0 6px 6px 0"><b>Comentario jefe:</b> '+_esc(n.comentario_jefe)+'</div>' : '';
      var fechas = '';
      if(n.fecha_inicio || n.fecha_fin){
        fechas = '<span style="color:#64748b;font-size:11px"> · '+(_esc(n.fecha_inicio||'')+(n.fecha_fin?' → '+_esc(n.fecha_fin):''))+'</span>';
      }
      return '<div class="card"><div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">' +
        '<div><b>'+_esc(n.asunto)+'</b> <span class="badge b-'+n.estado+'">'+_esc(n.estado)+'</span>' + fechas + '</div>' +
        '<span style="color:#94a3b8;font-size:11px">'+_esc((n.creado_en||'').slice(0,16))+'</span>' +
        '</div>' +
        '<div style="font-size:11px;color:#64748b;margin-top:4px">'+_esc(n.tipo)+'</div>' +
        (n.descripcion?'<div style="margin-top:8px;font-size:13px">'+_esc(n.descripcion)+'</div>':'') +
        coment +
        '</div>';
    }).join('');
  }catch(e){
    document.getElementById('lista-mis-notif').innerHTML = '<div class="empty">Error al cargar.</div>';
  }
}

// ─── CAPACITACIONES ─────────────────────────────────────────────────
async function cargarMisCap(){
  try{
    var r = await fetch('/api/bienestar/capacitaciones');
    var d = await r.json();
    MI_USERNAME = d.mi_username || '';
    var box = document.getElementById('lista-mis-cap');
    var caps = d.capacitaciones || [];
    if(!caps.length){
      box.innerHTML = '<div class="empty">Aún no tienes capacitaciones asignadas.</div>';
      return;
    }
    box.innerHTML = caps.map(_capCardHTML).join('');
  }catch(e){
    document.getElementById('lista-mis-cap').innerHTML = '<div class="empty">Error al cargar.</div>';
  }
}

function _capCardHTML(c){
  var tipoIcon = {video:'▶',notebooklm:'🧠',pdf:'📄',articulo:'📰',otro:'📦'}[c.material_tipo]||'📦';
  var verBoton = (c.material_url
    ? '<a href="'+_esc(c.material_url)+'" target="_blank" class="btn btn-secondary btn-sm">'+tipoIcon+' Ver material</a>'
    : '<span style="color:#94a3b8;font-size:12px">Sin URL</span>');
  var examBoton = (c.estado==='pendiente' || c.estado==='en_curso' || c.estado==='reprobada')
    ? '<button class="btn btn-primary btn-sm" onclick="iniciarExamen('+c.id+')">🧠 Hacer autoexamen</button>'
    : '';
  var nota = (c.nota_obtenida!=null)
    ? '<span style="margin-left:8px;font-weight:700;color:'+(c.nota_obtenida>=c.nota_minima?'#16a34a':'#dc2626')+'">'+c.nota_obtenida+'/100</span>'
    : '';
  var asignador = c.asignado_por ? '<span style="font-size:11px;color:#94a3b8">por '+_esc(c.asignado_por)+'</span>' : '';
  var flim = c.fecha_limite ? '<span style="font-size:11px;color:#dc2626;margin-left:8px">📅 Hasta '+_esc(c.fecha_limite)+'</span>' : '';
  return '<div class="card">' +
    '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">' +
      '<div><b>'+_esc(c.titulo)+'</b> <span class="badge b-'+c.estado+'">'+_esc(c.estado)+'</span>'+nota+flim+'</div>' +
      asignador +
    '</div>' +
    (c.descripcion?'<div style="font-size:13px;color:#475569;margin-top:6px">'+_esc(c.descripcion)+'</div>':'') +
    (c.material_notas?'<div style="font-size:11px;color:#64748b;margin-top:6px;font-style:italic">📝 '+_esc(c.material_notas)+'</div>':'') +
    '<div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap">'+verBoton+' '+examBoton+'</div>' +
    '</div>';
}

async function iniciarExamen(capId){
  var modal = document.getElementById('modal-examen');
  modal.style.display = 'flex';
  document.getElementById('exam-result').style.display = 'none';
  document.getElementById('exam-info').textContent = 'Generando preguntas con Claude... un momento.';
  document.getElementById('exam-body').innerHTML = '<div style="text-align:center;color:#64748b;padding:30px">⏳ Pensando...</div>';
  try{
    var r = await fetch('/api/bienestar/capacitaciones/'+capId+'/iniciar-examen', _fetchOpts('POST'));
    var d = await r.json();
    if(!d.ok){ _toast('Error: '+(d.error||'?'), 0); cerrarExamen(); return; }
    document.getElementById('exam-info').innerHTML = '<b>5 preguntas generadas.</b> Responde con tus palabras (no copies). Claude va a calificar al final con base en comprensión real.';
    var html = d.preguntas.map(function(p, i){
      return '<div class="q-block">' +
        '<div class="q">'+(i+1)+'. '+_esc(p.pregunta)+'</div>' +
        (p.contexto?'<div class="ctx">'+_esc(p.contexto)+'</div>':'') +
        '<textarea id="resp-'+i+'" placeholder="Tu respuesta..."></textarea>' +
        '</div>';
    }).join('');
    html += '<button class="btn btn-success" onclick="enviarRespuestas('+d.intento_id+','+d.preguntas.length+')" style="margin-top:10px">Enviar para calificar</button>';
    document.getElementById('exam-body').innerHTML = html;
  }catch(e){ _toast('Error de red al iniciar examen', 0); cerrarExamen(); }
}

async function enviarRespuestas(intentoId, n){
  var respuestas = [];
  for(var i=0; i<n; i++){
    respuestas.push((document.getElementById('resp-'+i).value||'').trim());
  }
  if(respuestas.every(function(r){return !r;})){ _toast('Responde al menos una', 0); return; }
  document.getElementById('exam-body').innerHTML += '<div style="margin-top:14px;color:#64748b;text-align:center">⏳ Claude está calificando...</div>';
  try{
    var r = await fetch('/api/bienestar/intentos/'+intentoId+'/calificar', _fetchOpts('POST', {respuestas: respuestas}));
    var d = await r.json();
    if(!d.ok){ _toast('Error: '+(d.error||'?'), 0); return; }
    var resBox = document.getElementById('exam-result');
    var aprobado = d.aprobado;
    var fbHTML = (d.evaluacion.feedback||[]).map(function(f){
      return '<div style="background:'+(f.puntaje>=14?'#f0fdf4':'#fef2f2')+';padding:8px 12px;margin-bottom:6px;border-left:3px solid '+(f.puntaje>=14?'#16a34a':'#dc2626')+';border-radius:0 6px 6px 0;font-size:12px">' +
        '<b>P'+(f.pregunta_idx+1)+': '+f.puntaje+'/20</b> · '+_esc(f.feedback||'') + '</div>';
    }).join('');
    resBox.innerHTML = '<div class="score-card '+(aprobado?'':'fail')+'">' +
      '<div style="font-size:13px;text-transform:uppercase;letter-spacing:1px">'+(aprobado?'APROBADO ✓':'REPROBADO ✗')+'</div>' +
      '<div class="num">'+d.nota+'</div>' +
      '<div style="font-size:12px">de 100 (mínimo: '+d.nota_minima+')</div>' +
      '</div>' +
      (d.evaluacion.resumen?'<div style="background:#f8fafc;padding:10px 14px;border-radius:6px;margin-bottom:10px;font-size:13px"><b>📝 Resumen:</b> '+_esc(d.evaluacion.resumen)+'</div>':'') +
      '<div><b>Feedback por pregunta:</b></div>' + fbHTML +
      (aprobado?'':'<button class="btn btn-warn" onclick="iniciarExamen('+intentoId+')" style="margin-top:10px">Reintentar</button>');
    resBox.style.display = 'block';
    cargarMisCap();
  }catch(e){ _toast('Error de red', 0); }
}

function cerrarExamen(){
  document.getElementById('modal-examen').style.display = 'none';
}

// ─── BANDEJA JEFE ─────────────────────────────────────────────────
async function cargarBandeja(){
  // Notificaciones de TODO el equipo
  try{
    var r1 = await fetch('/api/bienestar/notificaciones');
    var d1 = await r1.json();
    var box1 = document.getElementById('bandeja-notif');
    if(!d1.notificaciones.length){
      box1.innerHTML = '<div class="empty">Sin notificaciones del equipo 🎉</div>';
    } else {
      box1.innerHTML = d1.notificaciones.map(function(n){
        var btns = (n.estado==='pendiente') ? (
          '<div style="display:flex;gap:6px;margin-top:8px">' +
          '<button class="btn btn-success btn-sm" onclick="resolverNotif('+n.id+',\'aprobada\')">Aprobar</button>' +
          '<button class="btn btn-danger btn-sm" onclick="resolverNotif('+n.id+',\'rechazada\')">Rechazar</button>' +
          '<button class="btn btn-secondary btn-sm" onclick="resolverNotif('+n.id+',\'vista\')">Vista</button>' +
          '</div>'
        ) : '';
        return '<div class="card" style="border-left:4px solid '+(n.estado==='pendiente'?'#d97706':'#94a3b8')+'">' +
          '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">' +
            '<div><b>'+_esc(n.empleado_nombre||n.empleado_username)+'</b> · '+_esc(n.tipo)+
              ' <span class="badge b-'+n.estado+'">'+_esc(n.estado)+'</span></div>' +
            '<span style="color:#94a3b8;font-size:11px">'+_esc((n.creado_en||'').slice(0,16))+'</span>' +
          '</div>' +
          '<div style="margin-top:6px;font-weight:600">'+_esc(n.asunto)+'</div>' +
          (n.descripcion?'<div style="font-size:13px;color:#475569;margin-top:4px">'+_esc(n.descripcion)+'</div>':'') +
          (n.adjunto_url?'<a href="'+_esc(n.adjunto_url)+'" target="_blank" style="font-size:12px;color:#0f766e">📎 Ver adjunto</a>':'') +
          btns +
          '</div>';
      }).join('');
    }
  }catch(e){ document.getElementById('bandeja-notif').innerHTML = '<div class="empty">Error.</div>'; }
  // Capacitaciones del equipo
  try{
    var r2 = await fetch('/api/bienestar/capacitaciones');
    var d2 = await r2.json();
    var box2 = document.getElementById('bandeja-capacitaciones');
    if(!d2.capacitaciones.length){
      box2.innerHTML = '<div class="empty">Sin capacitaciones asignadas aún.</div>';
    } else {
      box2.innerHTML = d2.capacitaciones.map(function(c){
        return '<div class="card" style="padding:10px 14px">' +
          '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap">' +
            '<div><b>'+_esc(c.titulo)+'</b> · <span style="color:#64748b">'+_esc(c.asignado_a)+'</span> ' +
              '<span class="badge b-'+c.estado+'">'+_esc(c.estado)+'</span>' +
              (c.nota_obtenida!=null?' <b style="margin-left:6px;color:'+(c.nota_obtenida>=c.nota_minima?'#16a34a':'#dc2626')+'">'+c.nota_obtenida+'/100</b>':'') +
            '</div>' +
            '<span style="color:#94a3b8;font-size:11px">'+_esc((c.fecha_asignacion||'').slice(0,10))+'</span>' +
          '</div>' +
          '</div>';
      }).join('');
    }
  }catch(e){ document.getElementById('bandeja-capacitaciones').innerHTML = '<div class="empty">Error.</div>'; }
}

async function resolverNotif(id, estado){
  var coment = prompt('Comentario para el empleado (opcional):', '');
  try{
    var r = await fetch('/api/bienestar/notificaciones/'+id+'/resolver', _fetchOpts('POST', {estado: estado, comentario_jefe: coment||null}));
    var d = await r.json();
    if(d.ok){ _toast('Notificación '+estado, 1); cargarBandeja(); }
    else { _toast('Error: '+(d.error||'?'), 0); }
  }catch(e){ _toast('Error de red', 0); }
}

async function asignarCapacitacion(){
  var titulo = document.getElementById('cap-titulo').value.trim();
  var asignado_a = document.getElementById('cap-asignado-a').value;
  if(!titulo){ _toast('Pon un título', 0); return; }
  var body = {
    titulo: titulo, asignado_a: asignado_a,
    material_tipo: document.getElementById('cap-tipo').value,
    material_url: document.getElementById('cap-url').value,
    material_notas: document.getElementById('cap-notas').value,
    fecha_limite: document.getElementById('cap-flim').value,
    nota_minima: parseInt(document.getElementById('cap-notamin').value)||70
  };
  try{
    var r = await fetch('/api/bienestar/capacitaciones', _fetchOpts('POST', body));
    var d = await r.json();
    if(d.ok){
      _toast('Capacitación asignada', 1);
      ['cap-titulo','cap-url','cap-notas','cap-flim'].forEach(function(id){ document.getElementById(id).value=''; });
      cargarBandeja();
    } else { _toast('Error: '+(d.error||'?'), 0); }
  }catch(e){ _toast('Error de red', 0); }
}

// Init
if(ES_JEFE){ document.getElementById('tn-bandeja').style.display = 'inline-block'; }
cargarMisNotif();
</script>
</body>
</html>
"""
