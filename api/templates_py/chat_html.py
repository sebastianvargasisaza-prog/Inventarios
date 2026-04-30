# -*- coding: utf-8 -*-
"""HTML del módulo Chat — WhatsApp-style.

Sebastian (29-abr-2026): comunicación interna del holding con
sidebar de conversaciones, presencia online, mensajes 1-a-1, grupos
y broadcast. Polling 5s. Tareas inline (Fase 2).
"""

CHAT_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Chat — EOS</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos11">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,'Inter','Segoe UI',sans-serif;background:#0a0a0b;color:#e8e8ea;height:100vh;overflow:hidden}
.app{display:flex;height:100vh;background:#fff;color:#1c1917}

/* Sidebar */
.sidebar{width:340px;background:#fafaf9;border-right:1px solid #e7e5e4;display:flex;flex-direction:column;flex-shrink:0;height:100vh}
.me-bar{padding:14px 16px;background:#fff;border-bottom:1px solid #e7e5e4;display:flex;align-items:center;gap:12px}
.me-avatar{width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#a78bfa,#6d28d9);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;flex-shrink:0}
.me-info{flex:1;min-width:0}
.me-name{font-weight:700;font-size:14px;color:#1c1917;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.me-status{font-size:11px;color:#15803d;display:flex;align-items:center;gap:4px;margin-top:1px}
.dot-online{width:7px;height:7px;border-radius:50%;background:#15803d}
.btn-icon{width:34px;height:34px;border-radius:6px;background:transparent;border:1px solid #e7e5e4;cursor:pointer;display:flex;align-items:center;justify-content:center;color:#78716c}
.btn-icon:hover{background:#f5f5f4;color:#1c1917;border-color:#d6d3d1}
.btn-icon svg{width:18px;height:18px}

.search-wrap{padding:10px 12px;background:#fff;border-bottom:1px solid #e7e5e4}
.search-input{width:100%;padding:8px 12px;border:1px solid #e7e5e4;border-radius:8px;font-size:13px;background:#f5f5f4;outline:none}
.search-input:focus{background:#fff;border-color:#a78bfa}

.tabs-bar{padding:6px 12px;background:#fff;border-bottom:1px solid #e7e5e4;display:flex;gap:4px;overflow-x:auto;flex-wrap:wrap}
.tab-pill{padding:5px 10px;font-size:11px;border-radius:14px;border:1px solid #e7e5e4;background:#fff;cursor:pointer;font-weight:600;color:#78716c;white-space:nowrap}
.tab-pill.on{background:#1c1917;color:#fff;border-color:#1c1917}

.thread-list{flex:1;overflow-y:auto;background:#fafaf9}
.thread-item{padding:11px 14px;border-bottom:1px solid #f5f5f4;display:flex;align-items:center;gap:11px;cursor:pointer;background:#fff;margin:0}
.thread-item:hover{background:#fafaf9}
.thread-item.active{background:#f3e8ff;border-left:3px solid #6d28d9;padding-left:11px}
.t-avatar{width:42px;height:42px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:13px;position:relative;background:#94a3b8}
.t-avatar.online::after{content:'';position:absolute;bottom:0;right:0;width:11px;height:11px;background:#15803d;border:2px solid #fff;border-radius:50%}
.t-body{flex:1;min-width:0}
.t-row1{display:flex;justify-content:space-between;align-items:center}
.t-name{font-weight:700;font-size:13px;color:#1c1917;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.t-time{font-size:10px;color:#a8a29e;flex-shrink:0;margin-left:6px}
.t-row2{display:flex;justify-content:space-between;align-items:center;margin-top:2px}
.t-preview{font-size:12px;color:#78716c;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}
.t-badge{background:#6d28d9;color:#fff;border-radius:10px;font-size:10px;font-weight:700;padding:1px 6px;min-width:18px;text-align:center;margin-left:4px}

/* Main chat */
.main{flex:1;display:flex;flex-direction:column;background:#f5f4f0;background-image:radial-gradient(circle at 20% 30%, rgba(167,139,250,.04) 0, transparent 50%), radial-gradient(circle at 80% 70%, rgba(109,40,217,.04) 0, transparent 50%);min-width:0}
.empty-main{flex:1;display:flex;align-items:center;justify-content:center;color:#a8a29e;font-size:14px;padding:40px;text-align:center;flex-direction:column;gap:16px}
.empty-main svg{width:80px;height:80px;color:#cbd5e1}

.chat-header{padding:13px 18px;background:#fff;border-bottom:1px solid #e7e5e4;display:flex;align-items:center;gap:12px;flex-shrink:0}
.ch-info{flex:1;min-width:0}
.ch-name{font-weight:700;font-size:15px;color:#1c1917}
.ch-status{font-size:11px;color:#78716c;margin-top:1px}
.ch-status.online{color:#15803d}

.msgs-wrap{flex:1;overflow-y:auto;padding:18px;background:#f5f4f0}
.msg{display:flex;margin-bottom:10px;max-width:75%}
.msg.mine{margin-left:auto;flex-direction:row-reverse}
.bubble{padding:9px 13px;border-radius:14px;font-size:13.5px;line-height:1.5;color:#1c1917;background:#fff;border:1px solid #e7e5e4;box-shadow:0 1px 2px rgba(0,0,0,.03);max-width:100%;word-wrap:break-word;overflow-wrap:break-word}
.msg.mine .bubble{background:#dcfce7;border-color:#bbf7d0;color:#14532d}
.bubble-meta{font-size:10px;color:#a8a29e;margin-top:3px}
.msg.mine .bubble-meta{text-align:right;color:#15803d}
.sender-name{font-size:11px;font-weight:700;color:#6d28d9;margin-bottom:2px}
.day-divider{text-align:center;margin:14px 0;font-size:11px;color:#78716c;font-weight:600}
.day-divider span{background:#fff;padding:3px 12px;border-radius:10px;border:1px solid #e7e5e4}

.composer{padding:11px 16px;background:#fff;border-top:1px solid #e7e5e4;display:flex;align-items:flex-end;gap:8px;flex-shrink:0}
.composer-input{flex:1;padding:9px 13px;border:1px solid #e7e5e4;border-radius:18px;font-size:13.5px;outline:none;resize:none;font-family:inherit;background:#fafaf9;max-height:120px;min-height:36px}
.composer-input:focus{border-color:#6d28d9;background:#fff}
.send-btn{width:38px;height:38px;border:none;background:#6d28d9;color:#fff;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.send-btn:hover{background:#5b21b6}
.send-btn:disabled{background:#cbd5e1;cursor:default}
.send-btn svg{width:18px;height:18px;transform:translateX(1px)}

/* Modal nuevo chat */
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;display:none;align-items:center;justify-content:center;padding:20px}
.modal-bg.on{display:flex}
.modal-box{background:#fff;border-radius:14px;padding:24px;width:480px;max-width:100%;max-height:90vh;overflow-y:auto;color:#1c1917}
.modal-box h3{font-size:16px;margin-bottom:14px}
.user-row{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:8px;cursor:pointer;border:1px solid transparent}
.user-row:hover{background:#fafaf9;border-color:#e7e5e4}
.user-row.selected{background:#f3e8ff;border-color:#6d28d9}
.u-name{font-size:13px;color:#1c1917;flex:1}
.u-status{font-size:11px}
.u-status.online{color:#15803d;font-weight:600}
.u-status.offline{color:#a8a29e}

@media(max-width:768px){
  .sidebar{width:100%;display:none}
  .sidebar.show-mobile{display:flex}
  .main{display:none}
  .main.show-mobile{display:flex}
}
</style>
</head>
<body>

<div class="app">

  <!-- ─── SIDEBAR ─── -->
  <aside class="sidebar" id="sidebar">
    <div class="me-bar">
      <div class="me-avatar" id="me-avatar">{usuario}</div>
      <div class="me-info">
        <div class="me-name" id="me-name">{usuario}</div>
        <div class="me-status"><span class="dot-online"></span>Conectado</div>
      </div>
      <button class="btn-icon" onclick="abrirNuevoChat()" title="Nuevo chat"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg></button>
      <a class="btn-icon" href="/modulos" title="Volver a módulos"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg></a>
    </div>

    <div class="search-wrap">
      <input class="search-input" id="search-input" placeholder="Buscar conversación o mensaje..." oninput="onSearchInput(this.value)">
    </div>
    <div id="search-results" style="display:none;max-height:280px;overflow-y:auto;border-bottom:1px solid #e7e5e4;background:#fff;"></div>

    <div class="tabs-bar">
      <div class="tab-pill on" data-filter="todos" onclick="setFiltro('todos',this)">Todos</div>
      <div class="tab-pill" data-filter="no-leidos" onclick="setFiltro('no-leidos',this)">Sin leer <span id="ftr-unread">0</span></div>
      <div class="tab-pill" data-filter="grupos" onclick="setFiltro('grupos',this)">Grupos</div>
    </div>

    <div class="thread-list" id="thread-list">
      <div style="padding:30px;text-align:center;color:#a8a29e;font-size:12px">Cargando conversaciones...</div>
    </div>
  </aside>

  <!-- ─── MAIN CHAT ─── -->
  <section class="main" id="main">
    <div class="empty-main" id="empty-main">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
      <div style="font-size:18px;font-weight:600;color:#475569">EOS · Chat interno del holding</div>
      <div style="font-size:13px;max-width:420px;line-height:1.5">Selecciona una conversación o inicia una nueva con el botón <b>+</b> arriba a la izquierda. Polling cada 5s — los mensajes nuevos llegan solos.</div>
    </div>

    <div id="chat-active" style="display:none;flex:1;flex-direction:column;min-height:0">
      <div class="chat-header">
        <div class="t-avatar" id="ch-avatar">?</div>
        <div class="ch-info">
          <div class="ch-name" id="ch-name">—</div>
          <div class="ch-status" id="ch-status">—</div>
        </div>
      </div>
      <div class="msgs-wrap" id="msgs-wrap"></div>
      <div class="composer">
        <button class="send-btn" id="task-btn" onclick="abrirModalTarea()" title="Asignar tarea (crea tarea operativa + email a asignados)" style="background:#a16207;flex-shrink:0">📋</button>
        <textarea class="composer-input" id="composer" rows="1" placeholder="Escribe un mensaje..." onkeydown="composerKeydown(event)" oninput="autoresize(this)"></textarea>
        <button class="send-btn" id="send-btn" onclick="enviarMensaje()"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M2 21l21-9L2 3v7l15 2-15 2z"/></svg></button>
      </div>
    </div>
  </section>

</div>

<!-- Modal nuevo chat -->
<!-- Modal: Asignar tarea desde el chat -->
<div class="modal-bg" id="modal-tarea">
  <div class="modal-box">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
      <h3>📋 Asignar tarea</h3>
      <button class="btn-icon" onclick="cerrarModalTarea()">&times;</button>
    </div>
    <div style="background:#fff7ed;border:1px solid #fdba74;border-radius:8px;padding:10px 12px;margin-bottom:12px;font-size:11px;color:#92400e;line-height:1.5">
      Crea una <b>tarea operativa</b> visible en /planta. El asignado recibe email automático.
      Aparece como card en este chat.
    </div>
    <div style="margin-bottom:10px">
      <label style="font-size:11px;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Título *</label>
      <input id="tarea-titulo" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px;margin-top:4px;font-size:13px" placeholder="Ej. Sacar 100 envases para serigrafía">
    </div>
    <div style="margin-bottom:10px">
      <label style="font-size:11px;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Descripción</label>
      <textarea id="tarea-desc" rows="2" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px;margin-top:4px;font-size:13px;resize:vertical" placeholder="Detalle opcional..."></textarea>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px">
      <div>
        <label style="font-size:11px;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Asignar a *</label>
        <select id="tarea-asignado" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px;margin-top:4px;font-size:13px"></select>
      </div>
      <div>
        <label style="font-size:11px;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Fecha objetivo</label>
        <input type="date" id="tarea-fecha" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px;margin-top:4px;font-size:13px">
      </div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">
      <button class="tab-pill" onclick="cerrarModalTarea()">Cancelar</button>
      <button class="tab-pill on" onclick="crearTareaChat()" style="background:#a16207;color:#fff;border-color:#a16207">📋 Asignar y notificar</button>
    </div>
  </div>
</div>

<div class="modal-bg" id="modal-nuevo">
  <div class="modal-box">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
      <h3>Nuevo chat</h3>
      <button class="btn-icon" onclick="cerrarModalNuevo()">&times;</button>
    </div>
    <div style="display:flex;gap:6px;margin-bottom:14px">
      <button class="tab-pill on" data-tipo="directo" onclick="setTipoChat('directo',this)">1-a-1</button>
      <button class="tab-pill" data-tipo="grupo" onclick="setTipoChat('grupo',this)">Grupo</button>
      <button class="tab-pill" data-tipo="broadcast" onclick="setTipoChat('broadcast',this)">📢 Todos</button>
    </div>
    <div id="grupo-nombre-wrap" style="display:none;margin-bottom:14px">
      <label style="font-size:11px;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Nombre del grupo</label>
      <input id="grupo-nombre" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px;margin-top:6px;font-size:13px" placeholder="Ej. Equipo Planta">
    </div>
    <label style="font-size:11px;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Personas</label>
    <div id="users-list" style="margin-top:6px;max-height:300px;overflow-y:auto;border:1px solid #e7e5e4;border-radius:8px;padding:6px"></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">
      <button class="tab-pill" onclick="cerrarModalNuevo()">Cancelar</button>
      <button class="tab-pill on" onclick="crearNuevoChat()">Crear chat →</button>
    </div>
  </div>
</div>

<script>
var ME = '{usuario}';
var THREADS = [];
var USERS = [];
var ACTIVE_THREAD = null;
var FILTRO = 'todos';
var BUSCAR = '';
var TIPO_NUEVO = 'directo';
var SELECTED_USERS = [];

function _esc(s){ return String(s||'').replace(/[<>&"]/g,function(c){return ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'})[c]; }); }

function avatarColor(name){
  var colors=['#0891b2','#dc2626','#7c3aed','#16a34a','#d97706','#0e7490','#9333ea','#0369a1','#65a30d','#ea580c'];
  var h=0; for(var i=0;i<(name||'').length;i++) h=(h<<5)-h+name.charCodeAt(i);
  return colors[Math.abs(h)%colors.length];
}
function inicial(s){ return (s||'?').substring(0,2).toUpperCase(); }
function fmtTimeShort(ts){
  if(!ts) return '';
  var d = new Date(ts.includes('T')?ts:ts.replace(' ','T'));
  var now = new Date();
  if(d.toDateString() === now.toDateString()){
    return d.toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit'});
  }
  var diff = (now - d)/86400000;
  if(diff < 7) return ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'][d.getDay()];
  return d.toLocaleDateString('es-CO',{day:'2-digit',month:'2-digit'});
}

// ─── Setup inicial ──────────────────────────────────────────────────
document.getElementById('me-avatar').textContent = inicial(ME);
document.getElementById('me-name').textContent = ME.charAt(0).toUpperCase()+ME.slice(1);

heartbeat();
setInterval(heartbeat, 30*1000);
cargarThreads();
setInterval(function(){
  cargarThreads();
  if(ACTIVE_THREAD) cargarMensajes(ACTIVE_THREAD, true);
}, 5*1000);

async function heartbeat(){
  try { await fetch('/api/chat/heartbeat',{method:'POST'}); } catch(e){}
}

// ─── Threads ────────────────────────────────────────────────────────
async function cargarThreads(){
  try {
    var r = await fetch('/api/chat/threads');
    var d = await r.json();
    THREADS = d.threads || [];
    renderThreads();
  } catch(e){ console.error('threads:',e); }
}

function renderThreads(){
  var list = document.getElementById('thread-list');
  var unreadTotal = THREADS.reduce(function(a,t){return a + (t.no_leidos||0);}, 0);
  document.getElementById('ftr-unread').textContent = unreadTotal;
  var filtered = THREADS.filter(function(t){
    if(FILTRO==='no-leidos' && (t.no_leidos||0)===0) return false;
    if(FILTRO==='grupos' && t.tipo!=='grupo' && t.tipo!=='broadcast') return false;
    if(BUSCAR){
      var nombre = displayName(t).toLowerCase();
      var preview = (t.ultimo_mensaje_preview||'').toLowerCase();
      if(nombre.indexOf(BUSCAR)<0 && preview.indexOf(BUSCAR)<0) return false;
    }
    return true;
  });
  if(!filtered.length){
    list.innerHTML = '<div style="padding:30px;text-align:center;color:#a8a29e;font-size:12px">Sin conversaciones'+(BUSCAR?' que coincidan con "'+_esc(BUSCAR)+'"':'')+'</div>';
    return;
  }
  list.innerHTML = filtered.map(function(t){
    var nombre = displayName(t);
    var color = avatarColor(nombre);
    var isOnline = false;
    if(t.tipo==='directo' && t.otros_miembros.length){
      var otro = t.otros_miembros[0];
      var u = USERS.find(function(x){return x.username===otro;});
      isOnline = u && u.estado==='conectado';
    }
    var emoji = t.tipo==='broadcast' ? '📢' : t.tipo==='grupo' ? '👥' : '';
    var avContent = emoji || inicial(nombre);
    var avBg = (t.tipo==='broadcast' ? '#1c1917' : (t.tipo==='grupo' ? 'linear-gradient(135deg,#6d28d9,#0891b2)' : color));
    return '<div class="thread-item'+(ACTIVE_THREAD===t.id?' active':'')+'" onclick="abrirThread('+t.id+')">'+
      '<div class="t-avatar'+(isOnline?' online':'')+'" style="background:'+avBg+'">'+avContent+'</div>'+
      '<div class="t-body">'+
        '<div class="t-row1"><span class="t-name">'+_esc(nombre)+'</span><span class="t-time">'+fmtTimeShort(t.ultimo_mensaje_en)+'</span></div>'+
        '<div class="t-row2"><span class="t-preview">'+_esc(t.ultimo_mensaje_preview||'Sin mensajes aún')+'</span>'+
          (t.no_leidos>0?'<span class="t-badge">'+t.no_leidos+'</span>':'')+
        '</div>'+
      '</div>'+
    '</div>';
  }).join('');
}

function displayName(t){
  if(t.nombre) return t.nombre;
  if(t.tipo==='directo' && t.otros_miembros.length){
    var u = USERS.find(function(x){return x.username===t.otros_miembros[0];});
    return u ? u.display_name : t.otros_miembros[0];
  }
  if(t.tipo==='broadcast') return 'Todos · HHA Group';
  return 'Conversación '+t.id;
}

function setFiltro(f, btn){
  FILTRO = f;
  document.querySelectorAll('.tab-pill[data-filter]').forEach(function(b){b.classList.remove('on');});
  btn.classList.add('on');
  renderThreads();
}

function filtrarThreads(){
  BUSCAR = (document.getElementById('search-input').value||'').toLowerCase().trim();
  renderThreads();
}

// ─── Abrir thread ───────────────────────────────────────────────────
async function abrirThread(thread_id){
  ACTIVE_THREAD = thread_id;
  document.getElementById('empty-main').style.display = 'none';
  document.getElementById('chat-active').style.display = 'flex';
  document.querySelectorAll('.thread-item').forEach(function(el){el.classList.remove('active');});
  // Header
  var t = THREADS.find(function(x){return x.id===thread_id;});
  if(!t){ return; }
  var nombre = displayName(t);
  var color = avatarColor(nombre);
  var emoji = t.tipo==='broadcast' ? '📢' : t.tipo==='grupo' ? '👥' : '';
  var avEl = document.getElementById('ch-avatar');
  avEl.textContent = emoji || inicial(nombre);
  avEl.style.background = (t.tipo==='broadcast' ? '#1c1917' : (t.tipo==='grupo' ? 'linear-gradient(135deg,#6d28d9,#0891b2)' : color));
  document.getElementById('ch-name').textContent = nombre;
  var stEl = document.getElementById('ch-status');
  if(t.tipo==='directo' && t.otros_miembros.length){
    var otro = t.otros_miembros[0];
    var u = USERS.find(function(x){return x.username===otro;});
    if(u && u.estado==='conectado'){ stEl.textContent='En línea'; stEl.className='ch-status online'; }
    else { stEl.textContent='Desconectado'; stEl.className='ch-status'; }
  } else if(t.tipo==='broadcast'){
    stEl.textContent = 'Mensaje a TODOS los usuarios';
    stEl.className='ch-status';
  } else {
    stEl.textContent = (t.otros_miembros.length+1)+' miembros';
    stEl.className='ch-status';
  }
  await cargarMensajes(thread_id);
  document.getElementById('composer').focus();
  // Marcar leído
  fetch('/api/chat/threads/'+thread_id+'/leer',{method:'POST'}).catch(function(){});
}

async function cargarMensajes(thread_id, append){
  try {
    var r = await fetch('/api/chat/threads/'+thread_id+'/messages?limit=80');
    var d = await r.json();
    var msgs = d.messages || [];
    if(thread_id !== ACTIVE_THREAD) return;
    var wrap = document.getElementById('msgs-wrap');
    var atBottom = (wrap.scrollHeight - wrap.scrollTop - wrap.clientHeight) < 60;
    var html = '';
    var lastDay = '';
    msgs.forEach(function(m){
      var d = new Date((m.creado_en||'').replace(' ','T'));
      var dKey = d.toDateString();
      if(dKey !== lastDay){
        var label = d.toDateString()===new Date().toDateString() ? 'Hoy' :
                    new Date(Date.now()-86400000).toDateString()===dKey ? 'Ayer' :
                    d.toLocaleDateString('es-CO',{weekday:'long',day:'numeric',month:'long'});
        html += '<div class="day-divider"><span>'+label+'</span></div>';
        lastDay = dKey;
      }
      var mine = (m.sender||'') === ME;
      var senderHtml = (!mine && (ACTIVE_THREAD_TIPO!=='directo')) ? '<div class="sender-name">'+_esc(m.sender)+'</div>' : '';
      var hora = d.toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit'});
      // Render especial para mensajes tipo 'tarea': card con accion completar
      if(m.tipo_mensaje === 'tarea' && m.tarea_operativa_id){
        var tareaCard = '<div style="background:#fff7ed;border:1px solid #fdba74;border-left:4px solid #f59e0b;border-radius:10px;padding:12px 14px;margin:4px 0;max-width:380px">'+
          '<div style="font-size:11px;color:#92400e;font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">📋 Tarea asignada</div>'+
          '<div style="font-size:13px;color:#1c1917;line-height:1.4">'+_esc(m.contenido)+'</div>'+
          '<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">'+
            '<button onclick="completarTareaChat('+m.tarea_operativa_id+')" style="background:#16a34a;color:#fff;border:none;border-radius:6px;padding:5px 12px;font-size:11px;font-weight:700;cursor:pointer">✓ Completar</button>'+
            '<a href="/planta#tareas" target="_blank" style="background:#f5f5f4;color:#44403c;text-decoration:none;border-radius:6px;padding:5px 12px;font-size:11px;font-weight:600">Ver en /planta</a>'+
          '</div>'+
        '</div>';
        html += '<div class="msg'+(mine?' mine':'')+'"><div>'+
          senderHtml +
          tareaCard +
          '<div class="bubble-meta">'+hora+(mine?' · ✓':'')+'</div>'+
          '</div></div>';
      } else {
        // Render reacciones existentes (Fase 3)
        var reactsHtml = '';
        if(m.reactions){
          var pairs = [];
          for(var em in m.reactions){
            if(!m.reactions.hasOwnProperty(em)) continue;
            var users = m.reactions[em] || [];
            var meReact = users.indexOf(ME) >= 0;
            pairs.push('<button onclick="toggleReaccion('+m.id+',&quot;'+em+'&quot;)" '+
                      'style="background:'+(meReact?'#ede9fe':'#f5f5f4')+';border:1px solid '+(meReact?'#a78bfa':'#e7e5e4')+';border-radius:12px;padding:1px 8px;font-size:11px;cursor:pointer;margin-right:3px" '+
                      'title="'+_esc(users.join(', '))+'">'+em+' '+users.length+'</button>');
          }
          if(pairs.length) reactsHtml = '<div style="margin-top:3px;display:flex;flex-wrap:wrap">'+pairs.join('')+'</div>';
        }
        // Botón "+" para agregar reacción (al hover)
        var btnAddReact = '<button class="add-react" onclick="abrirPickerReact('+m.id+',event)" '+
          'style="position:absolute;'+(mine?'left:-32px':'right:-32px')+';top:0;background:#fff;border:1px solid #e7e5e4;border-radius:50%;width:26px;height:26px;cursor:pointer;font-size:12px;display:none;align-items:center;justify-content:center" title="Reaccionar">😊</button>';
        html += '<div class="msg'+(mine?' mine':'')+'" style="position:relative" onmouseenter="this.querySelector(\\'.add-react\\').style.display=\\'flex\\'" onmouseleave="this.querySelector(\\'.add-react\\').style.display=\\'none\\'"><div style="position:relative">'+
          btnAddReact +
          '<div class="bubble">'+senderHtml+_esc(m.contenido).replace(/\n/g,'<br>')+'</div>'+
          reactsHtml +
          '<div class="bubble-meta">'+hora+(mine?' · ✓':'')+'</div>'+
          '</div></div>';
      }
    });
    if(!msgs.length) html = '<div style="text-align:center;padding:60px 20px;color:#a8a29e;font-size:13px">Sin mensajes aún. ¡Sé el primero en escribir!</div>';
    wrap.innerHTML = html;
    if(atBottom || !append){ wrap.scrollTop = wrap.scrollHeight; }
  } catch(e){ console.error('msgs:',e); }
}

var ACTIVE_THREAD_TIPO = 'directo';
async function enviarMensaje(){
  var txt = document.getElementById('composer').value.trim();
  if(!txt || !ACTIVE_THREAD) return;
  var btn = document.getElementById('send-btn');
  btn.disabled = true;
  try {
    var r = await fetch('/api/chat/threads/'+ACTIVE_THREAD+'/messages',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({contenido: txt})
    });
    if(r.ok){
      document.getElementById('composer').value='';
      autoresize(document.getElementById('composer'));
      await cargarMensajes(ACTIVE_THREAD);
      cargarThreads();
    }
  } finally { btn.disabled = false; }
}

function composerKeydown(e){
  if(e.key === 'Enter' && !e.shiftKey){
    e.preventDefault();
    enviarMensaje();
  }
}
function autoresize(el){
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

// ─── Modal nuevo chat ───────────────────────────────────────────────
async function abrirNuevoChat(){
  document.getElementById('modal-nuevo').classList.add('on');
  TIPO_NUEVO = 'directo';
  SELECTED_USERS = [];
  document.querySelectorAll('.tab-pill[data-tipo]').forEach(function(b){
    b.classList.toggle('on', b.dataset.tipo==='directo');
  });
  document.getElementById('grupo-nombre-wrap').style.display = 'none';
  await cargarUsuarios();
  renderUsersList();
}
function cerrarModalNuevo(){
  document.getElementById('modal-nuevo').classList.remove('on');
}
function setTipoChat(tipo, btn){
  TIPO_NUEVO = tipo;
  SELECTED_USERS = [];
  document.querySelectorAll('.tab-pill[data-tipo]').forEach(function(b){b.classList.remove('on');});
  btn.classList.add('on');
  document.getElementById('grupo-nombre-wrap').style.display = (tipo==='grupo') ? 'block' : 'none';
  renderUsersList();
}

async function cargarUsuarios(){
  try {
    var r = await fetch('/api/chat/users');
    var d = await r.json();
    USERS = d.users || [];
  } catch(e){ console.error(e); }
}

function renderUsersList(){
  var list = document.getElementById('users-list');
  if(TIPO_NUEVO === 'broadcast'){
    list.innerHTML = '<div style="padding:14px;text-align:center;color:#475569;font-size:12px">📢 Mensaje a <b>TODOS</b> los usuarios del sistema (sebastian, alejandro, catalina, mayra, luz, daniela, miguel, luis, etc).</div>';
    return;
  }
  if(!USERS.length){ list.innerHTML='<div style="padding:14px;color:#a8a29e">Sin usuarios</div>'; return; }
  list.innerHTML = USERS.map(function(u){
    var sel = SELECTED_USERS.indexOf(u.username) >= 0;
    var color = avatarColor(u.username);
    return '<div class="user-row'+(sel?' selected':'')+'" onclick="toggleUser(\\''+u.username+'\\')">'+
      '<div class="t-avatar'+(u.estado==='conectado'?' online':'')+'" style="background:'+color+';width:32px;height:32px;font-size:11px">'+inicial(u.username)+'</div>'+
      '<div class="u-name">'+_esc(u.display_name)+'</div>'+
      '<div class="u-status '+(u.estado==='conectado'?'online':'offline')+'">'+
        (u.estado==='conectado'?'● en línea':'desconectado')+
      '</div>'+
    '</div>';
  }).join('');
}

function toggleUser(u){
  if(TIPO_NUEVO==='directo'){ SELECTED_USERS = [u]; }
  else {
    var i = SELECTED_USERS.indexOf(u);
    if(i>=0) SELECTED_USERS.splice(i,1);
    else SELECTED_USERS.push(u);
  }
  renderUsersList();
}

async function crearNuevoChat(){
  var body = {tipo: TIPO_NUEVO, miembros: SELECTED_USERS};
  if(TIPO_NUEVO==='grupo'){
    body.nombre = document.getElementById('grupo-nombre').value.trim() || ('Grupo de '+ME);
    if(!SELECTED_USERS.length){ alert('Selecciona al menos un miembro'); return; }
  } else if(TIPO_NUEVO==='directo'){
    if(SELECTED_USERS.length !== 1){ alert('Selecciona una persona'); return; }
  }
  var r = await fetch('/api/chat/threads', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body)
  });
  var d = await r.json();
  if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
  cerrarModalNuevo();
  await cargarThreads();
  // Cargar usuarios para que el header muestre nombres
  if(!USERS.length) await cargarUsuarios();
  abrirThread(d.thread_id);
}

// Cargar usuarios al inicio (para mostrar nombres en threads)
cargarUsuarios();

// ─── Asignación de tareas desde el chat (Fase 2) ────────────────────────
function abrirModalTarea(){
  if(!ACTIVE_THREAD){ alert('Abre un chat primero.'); return; }
  // Llenar dropdown de asignados con la lista de USERS
  var sel = document.getElementById('tarea-asignado');
  sel.innerHTML = '<option value="">— Selecciona —</option>'
    + USERS.filter(function(u){ return u.username !== ME; })
           .map(function(u){ return '<option value="'+_esc(u.username)+'">'+_esc(u.username)+'</option>'; }).join('');
  document.getElementById('tarea-titulo').value = '';
  document.getElementById('tarea-desc').value = '';
  document.getElementById('tarea-fecha').value = '';
  document.getElementById('modal-tarea').classList.add('on');
  setTimeout(function(){ document.getElementById('tarea-titulo').focus(); }, 50);
}

function cerrarModalTarea(){
  document.getElementById('modal-tarea').classList.remove('on');
}

async function crearTareaChat(){
  var titulo = document.getElementById('tarea-titulo').value.trim();
  var descripcion = document.getElementById('tarea-desc').value.trim();
  var asignado_a = document.getElementById('tarea-asignado').value;
  var fecha_objetivo = document.getElementById('tarea-fecha').value;
  if(!titulo){ alert('Escribe un título.'); return; }
  if(!asignado_a){ alert('Selecciona a quién asignar.'); return; }
  try {
    var r = await fetch('/api/chat/threads/'+ACTIVE_THREAD+'/asignar-tarea',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({titulo:titulo, descripcion:descripcion,
                            asignado_a:asignado_a, fecha_objetivo:fecha_objetivo})
    });
    var raw = await r.text();
    var d = null; try { d = JSON.parse(raw); } catch(_){}
    if(!r.ok){ alert('Error: '+ (d&&d.error || raw.substring(0,200))); return; }
    cerrarModalTarea();
    await cargarMensajes(ACTIVE_THREAD);
    cargarThreads();
  } catch(e){ alert('Error de red: '+e.message); }
}

// ─── Fase 3: Busqueda global de mensajes ──────────────────────────────
var _searchTimer = null;
function onSearchInput(val){
  // Filtrar threads localmente (comportamiento previo)
  filtrarThreads();
  // Si el query tiene >=2 chars, buscar mensajes en backend
  clearTimeout(_searchTimer);
  var box = document.getElementById('search-results');
  if(!val || val.length < 2){ box.style.display = 'none'; box.innerHTML = ''; return; }
  _searchTimer = setTimeout(async function(){
    try {
      var r = await fetch('/api/chat/search?q=' + encodeURIComponent(val));
      var d = await r.json();
      var results = d.results || [];
      if(!results.length){
        box.innerHTML = '<div style="padding:14px;color:#a8a29e;font-size:12px;text-align:center">Sin mensajes que coincidan con "'+_esc(val)+'"</div>';
        box.style.display = 'block';
        return;
      }
      var html = '<div style="padding:8px 14px;color:#78716c;font-size:11px;font-weight:700;text-transform:uppercase">'+results.length+' mensaje'+(results.length>1?'s':'')+' encontrado'+(results.length>1?'s':'')+'</div>';
      results.forEach(function(m){
        var threadLabel = m.thread_tipo === 'directo' ? '@'+_esc(m.sender) :
                          (m.thread_nombre || (m.thread_tipo==='broadcast'?'Todos':'Grupo'));
        html += '<div onclick="abrirThread('+m.thread_id+');document.getElementById(\\'search-input\\').value=\\'\\';onSearchInput(\\'\\');" '+
          'style="padding:10px 14px;border-bottom:1px solid #f5f5f4;cursor:pointer" '+
          'onmouseover="this.style.background=\\'#fafaf9\\'" onmouseout="this.style.background=\\'\\'">'+
          '<div style="font-size:11px;color:#7c3aed;font-weight:700">'+_esc(threadLabel)+' · '+_esc(m.sender)+'</div>'+
          '<div style="font-size:13px;color:#1c1917;margin-top:2px">'+_esc(m.contenido.substring(0,120))+'</div>'+
          '<div style="font-size:10px;color:#a8a29e;margin-top:2px">'+(m.creado_en||'').substring(0,16)+'</div>'+
          '</div>';
      });
      box.innerHTML = html;
      box.style.display = 'block';
    } catch(e){ console.error('search:',e); }
  }, 280);
}

// ─── Fase 3: Reacciones ─────────────────────────────────────────────────
var EMOJIS_RAPIDOS = ['👍','❤️','😂','🔥','✅'];
function abrirPickerReact(msgId, ev){
  if(ev) ev.stopPropagation();
  // Quitar picker previo
  var prev = document.getElementById('cw-picker-react');
  if(prev) prev.remove();
  var picker = document.createElement('div');
  picker.id = 'cw-picker-react';
  picker.style.cssText = 'position:fixed;background:#fff;border:1px solid #e7e5e4;border-radius:24px;padding:6px 10px;box-shadow:0 4px 14px rgba(0,0,0,.18);z-index:99999;display:flex;gap:4px';
  // Posicionar cerca del click
  var x = (ev && ev.clientX) || 100;
  var y = (ev && ev.clientY) || 100;
  picker.style.left = Math.max(10, x - 90) + 'px';
  picker.style.top = (y - 50) + 'px';
  EMOJIS_RAPIDOS.forEach(function(em){
    var b = document.createElement('button');
    b.textContent = em;
    b.style.cssText = 'background:transparent;border:none;font-size:18px;cursor:pointer;padding:4px 6px;border-radius:6px';
    b.onmouseover = function(){ this.style.background = '#f5f5f4'; };
    b.onmouseout = function(){ this.style.background = 'transparent'; };
    b.onclick = function(){ toggleReaccion(msgId, em); picker.remove(); };
    picker.appendChild(b);
  });
  document.body.appendChild(picker);
  // Cerrar si click fuera
  setTimeout(function(){
    document.addEventListener('click', function _close(e){
      if(!picker.contains(e.target)){ picker.remove(); document.removeEventListener('click', _close); }
    });
  }, 50);
}

async function toggleReaccion(msgId, emoji){
  try {
    var r = await fetch('/api/chat/messages/'+msgId+'/react',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({emoji: emoji})
    });
    if(r.ok && ACTIVE_THREAD) await cargarMensajes(ACTIVE_THREAD);
  } catch(e){}
}

// Marcar tarea como completada desde el card del chat
async function completarTareaChat(tareaId){
  var obs = prompt('Observaciones de cierre (opcional):', '');
  if(obs === null) return;
  try {
    var r = await fetch('/api/tareas-operativas/'+tareaId+'/completar',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({observaciones: obs||''})
    });
    var raw = await r.text();
    var d = null; try { d = JSON.parse(raw); } catch(_){}
    if(!r.ok){ alert('Error: '+(d&&d.error || raw.substring(0,200))); return; }
    alert('✓ Tarea completada');
    await cargarMensajes(ACTIVE_THREAD);
  } catch(e){ alert('Error: '+e.message); }
}
</script>

</body>
</html>"""
