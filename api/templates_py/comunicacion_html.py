"""HTML del modulo Comunicacion - tareas RACI + chat + actas + quejas."""

HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Comunicación — Tareas, Chat & Comité</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos5">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#0f172a;color:#e2e8f0}
  .header{background:linear-gradient(135deg,#78350f,#a16207);padding:18px 28px;display:flex;align-items:center;justify-content:space-between}
  .header h1{margin:0;font-size:1.4em}
  .header a{color:#fde68a;font-size:0.85em;text-decoration:none}
  .container{max-width:1400px;margin:0 auto;padding:24px}
  .tabs{display:flex;gap:6px;margin-bottom:18px;border-bottom:2px solid #334155;padding-bottom:8px;flex-wrap:wrap}
  .tab{padding:8px 16px;background:#1e293b;border:1px solid #334155;border-radius:8px 8px 0 0;cursor:pointer;font-size:13px;color:#94a3b8;font-weight:600}
  .tab.active{background:#a16207;color:#fff;border-color:#a16207}
  .badge-count{background:#dc2626;color:#fff;padding:1px 6px;border-radius:8px;font-size:10px;margin-left:6px}
  .grid{display:grid;gap:14px}
  .grid-4{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
  .grid-2{grid-template-columns:1fr 1fr}
  .card{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:18px}
  .card h3{margin:0 0 8px;font-size:0.78em;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em}
  .card .val{font-size:1.9em;font-weight:700;color:#fff}
  .panel{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:18px;margin-bottom:14px}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th{background:#0f172a;color:#94a3b8;font-weight:600;text-align:left;padding:8px 10px;font-size:11px;text-transform:uppercase}
  td{padding:8px 10px;border-bottom:1px solid #334155;vertical-align:top}
  .badge{padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;display:inline-block}
  .badge.alta{background:#7f1d1d;color:#fca5a5}
  .badge.media{background:#78350f;color:#fcd34d}
  .badge.baja{background:#064e3b;color:#34d399}
  .badge.estado-asig{background:#1e293b;color:#94a3b8;border:1px solid #475569}
  .badge.estado-enpr{background:#1e3a8a;color:#93c5fd}
  .badge.estado-bloq{background:#7f1d1d;color:#fca5a5}
  .badge.estado-hech{background:#064e3b;color:#34d399}
  .badge.estado-canc{background:#1e293b;color:#64748b}
  .raci{font-size:10px}
  .raci .R{color:#f87171;font-weight:700}
  .raci .A{color:#fbbf24;font-weight:700}
  .raci .C{color:#22d3ee}
  .raci .I{color:#94a3b8}
  .btn{padding:8px 16px;border:none;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600}
  .btn-primary{background:#a16207;color:#fff}
  .btn-secondary{background:#334155;color:#e2e8f0}
  .btn-danger{background:#7f1d1d;color:#fff}
  .btn-success{background:#15803d;color:#fff}
  input,textarea,select{background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:8px;font-size:13px;width:100%;font-family:inherit}
  label{display:block;font-size:11px;color:#94a3b8;text-transform:uppercase;font-weight:600;margin-bottom:4px;margin-top:10px}
  .hidden{display:none}
  .empty{color:#64748b;font-style:italic;padding:20px;text-align:center}
  .mensaje{background:#0f172a;padding:10px 14px;border-radius:8px;margin-bottom:8px}
  .mensaje.no-leido{border-left:3px solid #fbbf24;background:#0f172a}
  .mensaje .header-msg{display:flex;justify-content:space-between;font-size:11px;color:#94a3b8;margin-bottom:4px}
  .alert-ia{background:#1e1b3b;border-left:3px solid #818cf8;padding:10px 14px;margin-top:10px;border-radius:6px;font-size:12px}
  .modal{position:fixed;inset:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:9999}
  .modal-body{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:24px;width:560px;max-width:95vw;max-height:90vh;overflow-y:auto}
  .modal-body h2{margin:0 0 14px;font-size:1.1em}

  /* ─── MOBILE RESPONSIVE ─── */
  @media (max-width:900px) { .grid-2 { grid-template-columns:1fr; } }
  @media (max-width:768px) {
    .header { padding:14px 16px; flex-wrap:wrap; gap:8px; }
    .header h1 { font-size:1.15em; }
    .container { padding:12px; }
    .grid-4 { grid-template-columns:repeat(2,1fr); gap:10px; }
    .card { padding:12px; }
    .card .val { font-size:1.4em; }
    .card h3 { font-size:0.7em; }
    .tabs { gap:4px; padding-bottom:6px; overflow-x:auto; flex-wrap:nowrap; -webkit-overflow-scrolling:touch; }
    .tab { padding:6px 12px; font-size:12px; white-space:nowrap; flex-shrink:0; }
    .panel { padding:14px; }
    /* Tablas → cards apilados */
    table thead { display:none; }
    table, table tbody, table tr, table td { display:block; width:100%; }
    table tr { background:#0f172a; border-radius:8px; padding:10px; margin-bottom:8px; border:1px solid #334155; }
    table td { border-bottom:none; padding:4px 0; font-size:12px; }
    table td:first-child { font-weight:700; color:#fff; font-size:13px; padding-bottom:6px; }
    /* Modales 95% en mobile */
    .modal-body { padding:18px; width:95vw; }
    .modal-body h2 { font-size:1em; }
    /* Mensajes de chat más compactos */
    .mensaje { padding:8px 10px; }
    .mensaje .header-msg { flex-wrap:wrap; gap:4px; }
    /* Botones full-width en mobile */
    .btn { padding:10px 14px; font-size:13px; }
    /* RACI badges más pequeños */
    .raci { font-size:9px; }
    /* Inputs ocupan ancho completo */
    input, textarea, select { font-size:14px; }
  }
  @media (max-width:480px) {
    .grid-4 { grid-template-columns:1fr; }
    .container { padding:8px; }
    .tabs { margin-bottom:12px; }
    .tab { font-size:11px; padding:5px 10px; }
  }
</style>
</head>
<body>
  <header class="cx-mod-header cx-fade-in">
    <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:#6d28d9;"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
    <div>
      <div class="cx-mod-header__title">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#6d28d9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="9"/></svg>
        Compromisos &amp; Chat
      </div>
      <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; Tareas con RACI · Chat · Comité · Quejas con análisis IA</div>
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
    <!-- KPIs -->
    <div class="grid grid-4">
      <div class="card"><h3>Mis tareas activas</h3><div class="val" id="kpi-mis">—</div></div>
      <div class="card"><h3>Vencidas</h3><div class="val" id="kpi-venc" style="color:#fca5a5">—</div></div>
      <div class="card"><h3>Mensajes sin leer</h3><div class="val" id="kpi-msj" style="color:#fbbf24">—</div></div>
      <div class="card"><h3>Quejas Alta/Crítica</h3><div class="val" id="kpi-quejas" style="color:#f87171">—</div></div>
    </div>

    <!-- Tabs -->
    <div class="tabs" style="margin-top:24px">
      <div class="tab active" onclick="switchTab('tareas')">📋 Tareas</div>
      <div class="tab" onclick="switchTab('chat')">💬 Chat <span id="badge-chat" class="badge-count hidden">0</span></div>
      <div class="tab" onclick="switchTab('comite')">📑 Comité</div>
      <div class="tab" onclick="switchTab('quejas')">📢 Quejas / Problemas</div>
    </div>

    <!-- TAB: TAREAS -->
    <div id="tab-tareas">
      <div class="panel">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px">
          <div style="display:flex;gap:8px;align-items:center">
            <select id="filtro-mostrar" onchange="cargarTareas()" style="width:auto">
              <option value="mis">Mis tareas</option>
              <option value="todas">Todas</option>
            </select>
            <select id="filtro-estado" onchange="cargarTareas()" style="width:auto">
              <option value="">Todos los estados</option>
              <option value="Asignada">Asignada</option>
              <option value="EnProceso">En proceso</option>
              <option value="Bloqueada">Bloqueada</option>
              <option value="Hecha">Hecha</option>
            </select>
          </div>
          <button class="btn btn-primary" onclick="abrirModalTarea()">+ Nueva tarea</button>
        </div>
        <div id="tareas-list"><div class="empty">Cargando...</div></div>
      </div>
    </div>

    <!-- TAB: CHAT -->
    <div id="tab-chat" class="hidden">
      <div class="grid grid-2">
        <div class="panel">
          <h3 style="margin:0 0 12px">💬 Bandeja</h3>
          <div id="chat-bandeja"><div class="empty">Cargando...</div></div>
        </div>
        <div class="panel">
          <h3 style="margin:0 0 12px">Nuevo mensaje</h3>
          <label>Para</label>
          <input id="chat-a" placeholder="usuario (jefferson, luz, etc.)">
          <label>Asunto</label>
          <input id="chat-asunto" placeholder="Asunto opcional">
          <label>Mensaje</label>
          <textarea id="chat-msg" rows="6" placeholder="..."></textarea>
          <button class="btn btn-primary" onclick="enviarMensaje()" style="margin-top:12px;width:100%">Enviar</button>
        </div>
      </div>
    </div>

    <!-- TAB: COMITE -->
    <div id="tab-comite" class="hidden">
      <div class="panel">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <h3 style="margin:0">📑 Actas de comité</h3>
          <button class="btn btn-primary" onclick="abrirModalActa()">+ Cargar acta nueva</button>
        </div>
        <div id="actas-list"><div class="empty">Cargando...</div></div>
      </div>
    </div>

    <!-- TAB: QUEJAS -->
    <div id="tab-quejas" class="hidden">
      <div class="panel">
        <h3 style="margin:0 0 12px">📢 Reportar problema o queja</h3>
        <div style="font-size:12px;color:#94a3b8;margin-bottom:12px">
          Describe el problema. La IA lo analizará, sugerirá acción, y si es severidad Alta/Crítica se escalará automáticamente a gerencia.
        </div>
        <textarea id="queja-contexto" rows="6" placeholder="Ej: Hoy Catalina no me respondió cuando le solicité aprobación urgente para OC, llevo 3 días sin que avance la compra de glicerina..."></textarea>
        <button class="btn btn-primary" onclick="enviarQueja()" style="margin-top:12px">Enviar para análisis IA</button>
        <div id="queja-resultado"></div>
      </div>
      <div class="panel">
        <h3 style="margin:0 0 12px">Historial de quejas</h3>
        <div id="quejas-list"><div class="empty">Cargando...</div></div>
      </div>
    </div>
  </div>

  <!-- MODAL: Nueva/Editar tarea -->
  <div id="modal-tarea" class="modal hidden">
    <div class="modal-body">
      <h2 id="modal-tarea-title">Nueva tarea</h2>
      <input type="hidden" id="t-id">
      <label>Título *</label>
      <input id="t-titulo" placeholder="Lo que hay que hacer">
      <label>Descripción</label>
      <textarea id="t-desc" rows="3"></textarea>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <div>
          <label>Prioridad</label>
          <select id="t-prio"><option>Alta</option><option selected>Media</option><option>Baja</option></select>
        </div>
        <div>
          <label>Área</label>
          <select id="t-area">
            <option value="">--</option>
            <option>Producción</option><option>Calidad</option><option>Técnica</option>
            <option>Compras</option><option>Marketing</option><option>Comercial</option>
            <option>Gerencia</option><option>RRHH</option>
          </select>
        </div>
      </div>
      <label>Fecha compromiso</label>
      <input type="date" id="t-fecha">
      <label>RACI (Responsable / Accountable / Consulted / Informed)</label>
      <div style="font-size:11px;color:#94a3b8;margin-bottom:6px">
        <strong>R</strong>=Responsable (hace) · <strong>A</strong>=Aprueba (rinde cuentas) · <strong>C</strong>=Consultado · <strong>I</strong>=Informado
      </div>
      <div id="t-raci-rows"></div>
      <button class="btn btn-secondary" onclick="agregarRaciRow()" style="margin-top:6px">+ Agregar persona</button>
      <div style="display:flex;gap:8px;margin-top:18px;justify-content:flex-end">
        <button class="btn btn-secondary" onclick="cerrarModal('modal-tarea')">Cancelar</button>
        <button class="btn btn-primary" onclick="guardarTarea()">Guardar</button>
      </div>
    </div>
  </div>

  <!-- MODAL: Cargar acta -->
  <div id="modal-acta" class="modal hidden">
    <div class="modal-body">
      <h2>Cargar acta de comité</h2>
      <label>Fecha</label>
      <input type="date" id="a-fecha">
      <label>Asistentes (separados por coma)</label>
      <input id="a-asistentes" placeholder="sebastian, luz, jefferson, ...">
      <label>Transcripción completa (Gemini)</label>
      <textarea id="a-transcripcion" rows="12" placeholder="Pega la transcripción completa..."></textarea>
      <div style="font-size:11px;color:#94a3b8;margin-top:6px">
        Después de guardar puedes hacer click en "Parsear" para crear tareas automáticas.
      </div>
      <div style="display:flex;gap:8px;margin-top:18px;justify-content:flex-end">
        <button class="btn btn-secondary" onclick="cerrarModal('modal-acta')">Cancelar</button>
        <button class="btn btn-primary" onclick="guardarActa()">Guardar acta</button>
      </div>
    </div>
  </div>

<script>
const usuario = "{usuario}";
const _esc = s => String(s||'').replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));

let tabActiva = 'tareas';
function switchTab(t) {
  tabActiva = t;
  ['tareas','chat','comite','quejas'].forEach(x => {
    document.getElementById('tab-'+x).classList.toggle('hidden', x !== t);
  });
  document.querySelectorAll('.tab').forEach((el,i) => {
    el.classList.toggle('active', el.textContent.toLowerCase().includes(t));
  });
  if (t === 'tareas') cargarTareas();
  if (t === 'chat') cargarBandeja();
  if (t === 'comite') cargarActas();
  if (t === 'quejas') cargarQuejas();
}

async function cargarDashboard() {
  try {
    const d = await fetch('/api/comunicacion/dashboard').then(r=>r.json());
    document.getElementById('kpi-mis').textContent = d.mis_tareas;
    document.getElementById('kpi-venc').textContent = d.mis_vencidas;
    document.getElementById('kpi-msj').textContent = d.mensajes_no_leidos;
    document.getElementById('kpi-quejas').textContent = d.quejas_alta || 0;
    if (d.mensajes_no_leidos > 0) {
      const b = document.getElementById('badge-chat');
      b.textContent = d.mensajes_no_leidos;
      b.classList.remove('hidden');
    }
  } catch(e) { console.error(e); }
}

async function cargarTareas() {
  const mostrar = document.getElementById('filtro-mostrar').value;
  const estado = document.getElementById('filtro-estado').value;
  const params = new URLSearchParams();
  if (mostrar === 'mis') params.set('mis', '1');
  if (estado) params.set('estado', estado);
  try {
    const tareas = await fetch('/api/comunicacion/tareas?' + params).then(r=>r.json());
    const list = document.getElementById('tareas-list');
    if (!tareas || tareas.length === 0) {
      list.innerHTML = '<div class="empty">Sin tareas en esta vista</div>';
      return;
    }
    list.innerHTML = '<table><thead><tr>' +
      '<th>Tarea</th><th>Área</th><th>RACI</th><th>Prio</th><th>Estado</th><th>Comprom.</th><th></th>' +
      '</tr></thead><tbody>' +
      tareas.map(t => {
        const raci = '<span class="raci">' +
          (t.r ? '<span class="R">R:'+_esc(t.r)+'</span> ' : '') +
          (t.a ? '<span class="A">A:'+_esc(t.a)+'</span> ' : '') +
          (t.cc ? '<span class="C">C:'+_esc(t.cc)+'</span> ' : '') +
          (t.i ? '<span class="I">I:'+_esc(t.i)+'</span>' : '') +
          '</span>';
        const estadoBadge = '<span class="badge estado-'+(t.estado||'').toLowerCase().substring(0,4)+'">'+_esc(t.estado||'-')+'</span>';
        const prio = '<span class="badge '+(t.prioridad||'baja').toLowerCase()+'">'+(t.prioridad||'-')+'</span>';
        const venc = t.fecha_compromiso || '';
        const vencRojo = venc && venc < new Date().toISOString().slice(0,10) && t.estado !== 'Hecha';
        return '<tr>' +
          '<td><strong>'+_esc(t.titulo)+'</strong>'+(t.origen!='manual'?'<div style="font-size:10px;color:#64748b">('+t.origen+')</div>':'')+'</td>' +
          '<td style="font-size:11px;color:#94a3b8">'+_esc(t.area||'-')+'</td>' +
          '<td>'+raci+'</td>' +
          '<td>'+prio+'</td>' +
          '<td>'+estadoBadge+'</td>' +
          '<td style="font-size:11px;'+(vencRojo?'color:#fca5a5;font-weight:700':'color:#94a3b8')+'">'+_esc(venc||'-')+'</td>' +
          '<td><button class="btn btn-secondary" style="padding:4px 10px;font-size:11px" onclick="cambiarEstado('+t.id+')">Avanzar</button></td>' +
          '</tr>';
      }).join('') + '</tbody></table>';
  } catch(e) { console.error(e); }
}

async function cambiarEstado(tid) {
  const nuevo = prompt('Nuevo estado: Asignada / EnProceso / Bloqueada / Hecha / Cancelada');
  if (!nuevo) return;
  try {
    await fetch('/api/comunicacion/tareas/'+tid, {
      method:'PATCH', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({estado: nuevo})
    });
    cargarTareas(); cargarDashboard();
  } catch(e) { alert('Error: '+e.message); }
}

let raciRowCount = 0;
function abrirModalTarea() {
  document.getElementById('t-id').value = '';
  document.getElementById('t-titulo').value = '';
  document.getElementById('t-desc').value = '';
  document.getElementById('t-prio').value = 'Media';
  document.getElementById('t-area').value = '';
  document.getElementById('t-fecha').value = '';
  document.getElementById('t-raci-rows').innerHTML = '';
  raciRowCount = 0;
  agregarRaciRow();
  document.getElementById('modal-tarea').classList.remove('hidden');
}

function agregarRaciRow() {
  const div = document.createElement('div');
  div.style.cssText = 'display:flex;gap:6px;margin-bottom:6px';
  div.innerHTML = '<input class="raci-user" placeholder="usuario" style="flex:1">' +
    '<select class="raci-rol" style="width:80px"><option value="R">R</option><option value="A">A</option><option value="C">C</option><option value="I">I</option></select>' +
    '<button class="btn btn-secondary" style="padding:6px 10px" onclick="this.parentElement.remove()">×</button>';
  document.getElementById('t-raci-rows').appendChild(div);
  raciRowCount++;
}

async function guardarTarea() {
  const titulo = document.getElementById('t-titulo').value.trim();
  if (!titulo) { alert('Título requerido'); return; }
  const raci = [];
  document.querySelectorAll('#t-raci-rows > div').forEach(row => {
    const u = row.querySelector('.raci-user').value.trim().toLowerCase();
    const r = row.querySelector('.raci-rol').value;
    if (u) raci.push({usuario: u, rol: r});
  });
  const body = {
    titulo: titulo,
    descripcion: document.getElementById('t-desc').value,
    prioridad: document.getElementById('t-prio').value,
    area: document.getElementById('t-area').value,
    fecha_compromiso: document.getElementById('t-fecha').value || null,
    raci: raci
  };
  try {
    const r = await fetch('/api/comunicacion/tareas', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    const d = await r.json();
    if (!r.ok) { alert('Error: ' + (d.error||'')); return; }
    cerrarModal('modal-tarea');
    cargarTareas(); cargarDashboard();
  } catch(e) { alert('Error: '+e.message); }
}

function cerrarModal(id) {
  document.getElementById(id).classList.add('hidden');
}

async function cargarBandeja() {
  try {
    const ms = await fetch('/api/comunicacion/mensajes').then(r=>r.json());
    const list = document.getElementById('chat-bandeja');
    if (!ms.length) { list.innerHTML = '<div class="empty">Sin mensajes</div>'; return; }
    list.innerHTML = ms.map(m => {
      const noLeido = m.a_usuario === usuario && !m.leido_at;
      return '<div class="mensaje '+(noLeido?'no-leido':'')+'" '+(noLeido?'onclick="marcarLeido('+m.id+')"':'')+'>' +
        '<div class="header-msg"><span><strong>'+_esc(m.de_usuario)+'</strong> → '+_esc(m.a_usuario)+'</span><span>'+_esc(m.fecha)+'</span></div>' +
        (m.asunto ? '<div style="font-weight:600;font-size:13px;margin-bottom:4px">'+_esc(m.asunto)+'</div>' : '') +
        '<div style="font-size:13px;color:#cbd5e1">'+_esc(m.mensaje)+'</div></div>';
    }).join('');
  } catch(e) { console.error(e); }
}

async function marcarLeido(mid) {
  await fetch('/api/comunicacion/mensajes/'+mid+'/leido', {method:'POST'});
  cargarBandeja(); cargarDashboard();
}

async function enviarMensaje() {
  const a = document.getElementById('chat-a').value.trim().toLowerCase();
  const msg = document.getElementById('chat-msg').value.trim();
  if (!a || !msg) { alert('Destinatario y mensaje requeridos'); return; }
  try {
    await fetch('/api/comunicacion/mensajes', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({a_usuario: a, asunto: document.getElementById('chat-asunto').value, mensaje: msg})
    });
    document.getElementById('chat-a').value = '';
    document.getElementById('chat-asunto').value = '';
    document.getElementById('chat-msg').value = '';
    cargarBandeja();
    alert('Enviado');
  } catch(e) { alert('Error: '+e.message); }
}

async function cargarActas() {
  try {
    const actas = await fetch('/api/comunicacion/actas').then(r=>r.json());
    const list = document.getElementById('actas-list');
    if (!actas.length) { list.innerHTML = '<div class="empty">Sin actas registradas. Carga la primera del Gemini.</div>'; return; }
    list.innerHTML = '<table><thead><tr><th>Fecha</th><th>Título</th><th>Asistentes</th><th>Tareas creadas</th><th></th></tr></thead><tbody>' +
      actas.map(a =>
        '<tr><td>'+_esc(a.fecha)+'</td>' +
        '<td>'+_esc(a.titulo)+'</td>' +
        '<td style="font-size:11px;color:#94a3b8">'+(a.asistentes||[]).join(', ')+'</td>' +
        '<td>'+(a.parseada ? '<span style="color:#34d399">'+a.tareas_creadas+' ✓</span>' : 'Sin parsear')+'</td>' +
        '<td>'+(!a.parseada ? '<button class="btn btn-success" style="padding:4px 10px;font-size:11px" onclick="parsearActa('+a.id+')">Parsear</button>' : '')+'</td></tr>'
      ).join('') + '</tbody></table>';
  } catch(e) { console.error(e); }
}

async function parsearActa(aid) {
  if (!confirm('Parsear acta y crear tareas automaticas?')) return;
  try {
    const r = await fetch('/api/comunicacion/actas/'+aid+'/parsear', {method:'POST'});
    const d = await r.json();
    if (!r.ok) { alert('Error: ' + d.error); return; }
    alert('Listo. ' + d.tareas_creadas + ' tareas creadas.');
    cargarActas();
  } catch(e) { alert('Error: '+e.message); }
}

function abrirModalActa() {
  document.getElementById('a-fecha').value = new Date().toISOString().slice(0,10);
  document.getElementById('a-asistentes').value = '';
  document.getElementById('a-transcripcion').value = '';
  document.getElementById('modal-acta').classList.remove('hidden');
}

async function guardarActa() {
  const transcripcion = document.getElementById('a-transcripcion').value.trim();
  if (!transcripcion) { alert('Transcripción requerida'); return; }
  const asis = document.getElementById('a-asistentes').value.split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
  try {
    await fetch('/api/comunicacion/actas', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        fecha: document.getElementById('a-fecha').value,
        asistentes: asis,
        transcripcion: transcripcion
      })
    });
    cerrarModal('modal-acta');
    cargarActas();
    alert('Acta guardada. Click "Parsear" para crear tareas automáticas.');
  } catch(e) { alert('Error: '+e.message); }
}

async function enviarQueja() {
  const ctx = document.getElementById('queja-contexto').value.trim();
  if (!ctx) { alert('Describe el problema'); return; }
  try {
    document.getElementById('queja-resultado').innerHTML = '<div class="alert-ia">Analizando con IA...</div>';
    const r = await fetch('/api/comunicacion/quejas', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({contexto: ctx})
    });
    const d = await r.json();
    if (!r.ok) {
      document.getElementById('queja-resultado').innerHTML = '<div class="alert-ia" style="border-color:#dc2626">Error: '+_esc(d.error||'')+'</div>';
      return;
    }
    if (d.analisis) {
      document.getElementById('queja-resultado').innerHTML = '<div class="alert-ia">' +
        '<div style="font-weight:700;margin-bottom:4px">📊 Análisis IA — Severidad: <span style="color:#fbbf24">'+_esc(d.analisis.severidad||'-')+'</span></div>' +
        '<div style="margin-bottom:6px"><strong>Lectura:</strong> '+_esc(d.analisis.analisis||'')+'</div>' +
        '<div style="margin-bottom:6px"><strong>Acción sugerida:</strong> '+_esc(d.analisis.accion_sugerida||'')+'</div>' +
        '<div style="font-size:11px;color:#94a3b8">Escalado a: '+_esc(d.analisis.escalar_a||'-')+'</div>' +
        '</div>';
    } else {
      document.getElementById('queja-resultado').innerHTML = '<div class="alert-ia">Queja registrada. Análisis IA no disponible (API key no configurada).</div>';
    }
    document.getElementById('queja-contexto').value = '';
    cargarQuejas();
  } catch(e) {
    document.getElementById('queja-resultado').innerHTML = '<div class="alert-ia" style="border-color:#dc2626">Error: '+e.message+'</div>';
  }
}

async function cargarQuejas() {
  try {
    const qs = await fetch('/api/comunicacion/quejas').then(r=>r.json());
    const list = document.getElementById('quejas-list');
    if (!qs.length) { list.innerHTML = '<div class="empty">Sin quejas registradas</div>'; return; }
    list.innerHTML = '<table><thead><tr><th>Fecha</th><th>De</th><th>Sev.</th><th>Contexto</th><th>Estado</th></tr></thead><tbody>' +
      qs.map(q =>
        '<tr><td style="font-size:11px">'+_esc((q.fecha||'').substring(0,10))+'</td>' +
        '<td style="font-size:11px;color:#a5f3fc">'+_esc(q.de_usuario)+'</td>' +
        '<td><span class="badge '+(q.severidad_ia||'media').toLowerCase()+'">'+_esc(q.severidad_ia||'-')+'</span></td>' +
        '<td style="font-size:12px">'+_esc((q.contexto||'').substring(0,150))+(q.contexto && q.contexto.length>150?'...':'')+'</td>' +
        '<td><span class="badge estado-'+(q.estado||'').toLowerCase().substring(0,4)+'">'+_esc(q.estado||'-')+'</span></td></tr>'
      ).join('') + '</tbody></table>';
  } catch(e) { console.error(e); }
}

// Init
cargarDashboard();
cargarTareas();
setInterval(cargarDashboard, 60*1000); // refresh dashboard cada minuto
</script>
</body>
</html>
"""
