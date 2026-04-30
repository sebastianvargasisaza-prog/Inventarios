# -*- coding: utf-8 -*-
"""
Chat interno EOS — Fase 1 WhatsApp-style.

Sebastian (29-abr-2026): reemplaza Compromisos+Chat con un sistema
moderno de comunicación interna. Lateral con conversaciones, header
con presencia, mensajes 1-a-1 / grupo / broadcast, asignación de
tareas inline.

Endpoints:
  GET  /chat                              - UI (HTML)
  GET  /api/chat/users                    - usuarios + estado online
  POST /api/chat/heartbeat                - actualiza presence
  GET  /api/chat/threads                  - mis conversaciones
  POST /api/chat/threads                  - crear nueva (directo/grupo/broadcast)
  GET  /api/chat/threads/<id>/messages    - mensajes (paginado)
  POST /api/chat/threads/<id>/messages    - enviar mensaje
  POST /api/chat/threads/<id>/leer        - marcar leído
  POST /api/chat/messages/<id>            - editar/eliminar
  POST /api/chat/threads/<id>/miembros    - agregar miembros (grupos)
"""
from flask import Blueprint, jsonify, request, session, Response
from database import get_db
from config import COMPRAS_USERS

bp = Blueprint('chat', __name__)


@bp.route('/api/chat/widget.js')
def chat_widget_js():
    """JS del widget flotante 💬 que se inyecta en TODAS las paginas
    (excepto /chat /login /logout). Sebastian (29-abr-2026): "vista
    lateral persistente tipo WhatsApp Web — boton flotante en cualquier
    pagina"."""
    if 'compras_user' not in session:
        return Response("// no auth", mimetype="application/javascript")
    # No cachear el widget JS — Sebastian (29-abr-2026): los browsers
    # cacheaban version vieja con bugs y costaba forzar Ctrl+F5.
    # Inyectar user actual en el JS para que el widget sepa "soy yo"
    me = session.get('compras_user', '')
    js_prefix = "var __CW_ME = " + repr(me).replace("'", '"') + ";\n"
    js = js_prefix + r"""
(function(){
  var p = window.location.pathname;
  if (p === '/chat' || p === '/login' || p === '/logout') return;
  if (window.__chatWidgetLoaded) return;
  window.__chatWidgetLoaded = true;

  // ── Sebastian (30-abr-2026): chat flotante REAL — panel desplegable
  // tipo Messenger. Lista de hilos + visor de mensajes inline + envío.
  // Si el panel falla por cualquier motivo, "Abrir completo →" lleva a /chat.

  var s = document.createElement('style');
  s.textContent = ''+
    '#cw-fab{position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;background:#7c3aed;color:#fff;border:none;cursor:pointer;font-size:24px;box-shadow:0 4px 16px rgba(124,58,237,.4);z-index:9998;display:flex;align-items:center;justify-content:center;transition:transform .15s}'+
    '#cw-fab:hover{transform:scale(1.08);background:#6d28d9}'+
    '#cw-badge{position:absolute;top:-4px;right:-4px;background:#dc2626;color:#fff;border-radius:50%;min-width:22px;height:22px;font-size:12px;font-weight:800;display:none;align-items:center;justify-content:center;padding:0 4px;border:2px solid #fff}'+
    '#cw-panel{position:fixed;bottom:84px;right:20px;width:380px;max-width:94vw;height:540px;max-height:78vh;background:#fff;border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.22);z-index:9998;display:none;flex-direction:column;overflow:hidden;border:1px solid #e2e8f0;font-family:Segoe UI,sans-serif}'+
    '#cw-head{background:#7c3aed;color:#fff;padding:10px 14px;display:flex;justify-content:space-between;align-items:center;font-weight:700;font-size:14px;gap:6px}'+
    '#cw-head .actions{display:flex;align-items:center;gap:8px}'+
    '#cw-head a,#cw-head button{color:#e9d5ff;font-size:11px;font-weight:600;text-decoration:none;background:rgba(255,255,255,.15);border:none;padding:4px 8px;border-radius:6px;cursor:pointer}'+
    '#cw-head a:hover,#cw-head button:hover{color:#fff;background:rgba(255,255,255,.25)}'+
    '#cw-body{flex:1;overflow:hidden;display:flex;flex-direction:column}'+
    '#cw-tlist{overflow-y:auto;flex:1}'+
    '.cw-thread{padding:10px 14px;border-bottom:1px solid #f1f5f9;cursor:pointer;display:flex;align-items:flex-start;gap:8px;transition:background .15s}'+
    '.cw-thread:hover{background:#f8fafc}'+
    '.cw-thread.unread{background:#faf5ff;border-left:3px solid #7c3aed}'+
    '.cw-thread .nm{font-size:13px;font-weight:600;color:#0f172a;line-height:1.3}'+
    '.cw-thread .pv{font-size:11px;color:#64748b;line-height:1.4;margin-top:2px}'+
    '.cw-thread .ts{font-size:10px;color:#94a3b8;white-space:nowrap;margin-left:auto}'+
    '.cw-thread .uc{background:#dc2626;color:#fff;border-radius:10px;padding:1px 6px;font-size:10px;font-weight:700;margin-left:6px}'+
    '#cw-conv{display:none;flex-direction:column;height:100%}'+
    '#cw-conv-head{background:#f8fafc;padding:8px 14px;border-bottom:1px solid #e2e8f0;font-size:13px;font-weight:600;color:#0f172a;display:flex;align-items:center;gap:6px}'+
    '#cw-back{background:none;border:none;color:#7c3aed;cursor:pointer;font-size:16px;padding:0}'+
    '#cw-task-btn{margin-left:auto;background:#16a34a;color:#fff;border:none;padding:4px 8px;border-radius:5px;font-size:11px;cursor:pointer;font-weight:600}'+
    '#cw-task-btn:hover{background:#15803d}'+
    '#cw-new{display:none;flex-direction:column;height:100%}'+
    '#cw-new-head{background:#f8fafc;padding:8px 14px;border-bottom:1px solid #e2e8f0;display:flex;align-items:center;gap:8px;font-size:13px;font-weight:600;color:#0f172a}'+
    '#cw-new-body{flex:1;overflow-y:auto;padding:10px}'+
    '.cw-user{padding:8px 12px;border-radius:6px;cursor:pointer;display:flex;align-items:center;gap:8px;margin-bottom:4px;border:1px solid transparent}'+
    '.cw-user:hover{background:#faf5ff;border-color:#e9d5ff}'+
    '.cw-user.selected{background:#ede9fe;border-color:#7c3aed}'+
    '.cw-user .dot{width:8px;height:8px;border-radius:50%;background:#94a3b8}'+
    '.cw-user.online .dot{background:#16a34a}'+
    '.cw-user .nm{flex:1;font-size:13px;color:#0f172a}'+
    '.cw-user .est{font-size:10px;color:#94a3b8}'+
    '#cw-new-actions{padding:10px;border-top:1px solid #e2e8f0;background:#fff;display:flex;gap:6px}'+
    '#cw-task-modal{position:absolute;inset:0;background:rgba(255,255,255,.97);z-index:5;padding:14px;display:none;flex-direction:column;overflow-y:auto}'+
    '#cw-task-modal h4{font-size:14px;color:#0f172a;margin-bottom:10px}'+
    '#cw-task-modal label{font-size:11px;font-weight:600;color:#64748b;display:block;margin-top:8px;margin-bottom:3px}'+
    '#cw-task-modal input,#cw-task-modal textarea{width:100%;padding:6px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:12px;font-family:inherit}'+
    '#cw-msgs{overflow-y:auto;flex:1;padding:10px;background:#f8fafc}'+
    '.cw-m{max-width:80%;padding:6px 10px;border-radius:10px;font-size:12px;line-height:1.4;margin-bottom:6px;word-wrap:break-word}'+
    '.cw-m.own{background:#7c3aed;color:#fff;margin-left:auto}'+
    '.cw-m.other{background:#fff;color:#0f172a;border:1px solid #e2e8f0}'+
    '.cw-m .who{font-size:10px;font-weight:600;color:#7c3aed;margin-bottom:2px}'+
    '.cw-m.own .who{color:#e9d5ff}'+
    '#cw-inp{display:flex;gap:6px;padding:8px;border-top:1px solid #e2e8f0;background:#fff}'+
    '#cw-text{flex:1;border:1px solid #cbd5e1;border-radius:18px;padding:7px 12px;font-size:13px;font-family:inherit;outline:none}'+
    '#cw-text:focus{border-color:#7c3aed}'+
    '#cw-send{background:#7c3aed;color:#fff;border:none;border-radius:18px;padding:7px 14px;font-size:13px;font-weight:600;cursor:pointer}'+
    '#cw-send:hover{background:#6d28d9}'+
    '#cw-toast{position:fixed;bottom:90px;right:20px;background:#1e293b;color:#fff;padding:12px 16px;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.3);z-index:9999;max-width:320px;font-size:13px;cursor:pointer;animation:cwSlide .3s ease-out;border-left:4px solid #7c3aed}'+
    '@keyframes cwSlide{from{transform:translateY(20px);opacity:0}to{transform:translateY(0);opacity:1}}'+
    '.cw-empty{text-align:center;color:#94a3b8;padding:30px 14px;font-size:13px}';
  document.head.appendChild(s);

  var fab = document.createElement('button');
  fab.id = 'cw-fab';
  fab.title = 'EOS Chat';
  fab.innerHTML = '\u{1F4AC}<span id="cw-badge">0</span>';
  document.body.appendChild(fab);

  var panel = document.createElement('div');
  panel.id = 'cw-panel';
  panel.innerHTML = ''+
    '<div id="cw-head"><span>\u{1F4AC} EOS Chat</span>'+
      '<div class="actions">'+
        '<button id="cw-new-btn" title="Nueva conversación">+ Nueva</button>'+
        '<a href="/chat" target="_blank">Abrir →</a>'+
      '</div></div>'+
    '<div id="cw-body" style="position:relative;flex:1;overflow:hidden;display:flex;flex-direction:column">'+
      '<div id="cw-tlist"><div class="cw-empty">Cargando...</div></div>'+
      '<div id="cw-conv">'+
        '<div id="cw-conv-head"><button id="cw-back">←</button><span id="cw-conv-title" style="flex:1"></span><button id="cw-task-btn" title="Asignar tarea desde este chat">+ Tarea</button></div>'+
        '<div id="cw-msgs"></div>'+
        '<div id="cw-inp"><input id="cw-text" placeholder="Escribe..." autocomplete="off"><button id="cw-send">Enviar</button></div>'+
      '</div>'+
      '<div id="cw-new">'+
        '<div id="cw-new-head"><button id="cw-new-back" style="background:none;border:none;color:#7c3aed;cursor:pointer;font-size:16px;padding:0">←</button>'+
          '<span style="flex:1">Nueva conversación</span></div>'+
        '<div style="padding:10px;border-bottom:1px solid #e2e8f0;background:#fafafa">'+
          '<div style="display:flex;gap:6px;margin-bottom:6px">'+
            '<label style="font-size:11px;color:#64748b;display:flex;align-items:center;gap:4px;cursor:pointer">'+
              '<input type="radio" name="cw-tipo" value="directo" checked> 1-a-1</label>'+
            '<label style="font-size:11px;color:#64748b;display:flex;align-items:center;gap:4px;cursor:pointer">'+
              '<input type="radio" name="cw-tipo" value="grupo"> Grupo</label>'+
          '</div>'+
          '<input id="cw-new-name" type="text" placeholder="Nombre del grupo (opcional para 1-a-1)" style="display:none;width:100%;padding:6px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:12px;margin-bottom:6px">'+
          '<input id="cw-new-search" type="text" placeholder="Buscar usuario..." style="width:100%;padding:6px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:12px">'+
        '</div>'+
        '<div id="cw-new-body"></div>'+
        '<div id="cw-new-actions">'+
          '<span id="cw-new-count" style="flex:1;font-size:11px;color:#64748b;align-self:center">0 seleccionados</span>'+
          '<button id="cw-new-cancel" style="background:#e2e8f0;color:#475569;border:none;padding:6px 12px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">Cancelar</button>'+
          '<button id="cw-new-create" style="background:#7c3aed;color:#fff;border:none;padding:6px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">Crear</button>'+
        '</div>'+
      '</div>'+
      '<div id="cw-task-modal">'+
        '<h4>📋 Asignar tarea desde este chat</h4>'+
        '<label>Título</label><input id="cw-task-titulo" type="text" placeholder="Qué hay que hacer">'+
        '<label>Descripción</label><textarea id="cw-task-descr" rows="3" placeholder="Detalles..."></textarea>'+
        '<label>Asignar a (usernames separados por coma)</label><input id="cw-task-asign" type="text" placeholder="ej: mayerlin,camilo">'+
        '<label>Fecha objetivo (opcional)</label><input id="cw-task-fecha" type="date">'+
        '<div style="display:flex;gap:6px;margin-top:14px;justify-content:flex-end">'+
          '<button id="cw-task-cancel" style="background:#e2e8f0;color:#475569;border:none;padding:7px 12px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">Cancelar</button>'+
          '<button id="cw-task-save" style="background:#16a34a;color:#fff;border:none;padding:7px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">Crear tarea</button>'+
        '</div>'+
      '</div>'+
    '</div>';
  document.body.appendChild(panel);

  var ACTIVE_THREAD = null;
  var THREADS = [];
  var ME = (typeof __CW_ME !== 'undefined') ? __CW_ME : '';

  fab.onclick = function(e){
    e.stopPropagation();
    if (panel.style.display === 'flex') {
      panel.style.display = 'none';
    } else {
      panel.style.display = 'flex';
      cargarThreads();
    }
  };
  document.addEventListener('click', function(e){
    if (panel.style.display === 'flex' && !panel.contains(e.target) && e.target !== fab) {
      panel.style.display = 'none';
    }
  });

  document.getElementById('cw-back').onclick = function(){
    document.getElementById('cw-conv').style.display = 'none';
    document.getElementById('cw-tlist').style.display = 'block';
    ACTIVE_THREAD = null;
    cargarThreads();
  };

  document.getElementById('cw-send').onclick = enviarMensaje;
  document.getElementById('cw-text').addEventListener('keydown', function(e){
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviarMensaje(); }
  });

  // ── Nueva conversación ────────────────────────────────────────────
  var SELECTED_USERS = new Set();
  var ALL_USERS = [];

  document.getElementById('cw-new-btn').onclick = function(e){
    e.stopPropagation();
    abrirNuevaConv();
  };
  document.getElementById('cw-new-back').onclick = function(){
    document.getElementById('cw-new').style.display = 'none';
    document.getElementById('cw-tlist').style.display = 'block';
  };
  document.getElementById('cw-new-cancel').onclick = function(){
    document.getElementById('cw-new').style.display = 'none';
    document.getElementById('cw-tlist').style.display = 'block';
    SELECTED_USERS.clear();
  };
  document.getElementById('cw-new-create').onclick = crearNuevaConv;
  document.getElementById('cw-new-search').addEventListener('input', renderListaUsuarios);
  document.querySelectorAll('input[name="cw-tipo"]').forEach(function(rb){
    rb.addEventListener('change', function(){
      var tipo = document.querySelector('input[name="cw-tipo"]:checked').value;
      document.getElementById('cw-new-name').style.display = (tipo==='grupo') ? 'block' : 'none';
      // Si pasamos a 1-a-1, mantener solo 1 seleccionado
      if (tipo==='directo' && SELECTED_USERS.size > 1){
        var first = Array.from(SELECTED_USERS)[0];
        SELECTED_USERS.clear();
        SELECTED_USERS.add(first);
      }
      renderListaUsuarios();
    });
  });

  async function abrirNuevaConv(){
    document.getElementById('cw-tlist').style.display = 'none';
    document.getElementById('cw-conv').style.display = 'none';
    document.getElementById('cw-new').style.display = 'flex';
    document.getElementById('cw-new-search').value = '';
    document.getElementById('cw-new-name').value = '';
    document.querySelector('input[name="cw-tipo"][value="directo"]').checked = true;
    document.getElementById('cw-new-name').style.display = 'none';
    SELECTED_USERS.clear();
    var body = document.getElementById('cw-new-body');
    body.innerHTML = '<div class="cw-empty">Cargando usuarios...</div>';
    try{
      var r = await fetch('/api/chat/users');
      var d = await r.json();
      ALL_USERS = d.users || [];
      renderListaUsuarios();
    }catch(e){ body.innerHTML = '<div class="cw-empty">Error.</div>'; }
  }

  function renderListaUsuarios(){
    var q = (document.getElementById('cw-new-search').value || '').toLowerCase();
    var body = document.getElementById('cw-new-body');
    var tipo = document.querySelector('input[name="cw-tipo"]:checked').value;
    var lista = ALL_USERS.filter(function(u){
      if (!q) return true;
      return (u.username||'').toLowerCase().indexOf(q) >= 0 || (u.display_name||'').toLowerCase().indexOf(q) >= 0;
    });
    if (!lista.length){ body.innerHTML = '<div class="cw-empty">Sin coincidencias.</div>'; return; }
    body.innerHTML = lista.map(function(u){
      var sel = SELECTED_USERS.has(u.username);
      return '<div class="cw-user '+(u.estado==='conectado'?'online':'')+(sel?' selected':'')+'" data-u="'+_esc(u.username)+'">'+
        '<span class="dot"></span>'+
        '<span class="nm">'+_esc(u.display_name||u.username)+'</span>'+
        '<span class="est">'+u.estado+'</span>'+
        (sel?'<span style="color:#7c3aed;font-weight:700">✓</span>':'')+
      '</div>';
    }).join('');
    body.querySelectorAll('.cw-user').forEach(function(el){
      el.onclick = function(){
        var u = el.getAttribute('data-u');
        if (tipo === 'directo'){
          SELECTED_USERS.clear();
          SELECTED_USERS.add(u);
        } else {
          if (SELECTED_USERS.has(u)) SELECTED_USERS.delete(u);
          else SELECTED_USERS.add(u);
        }
        renderListaUsuarios();
        document.getElementById('cw-new-count').textContent = SELECTED_USERS.size + ' seleccionado'+(SELECTED_USERS.size===1?'':'s');
      };
    });
    document.getElementById('cw-new-count').textContent = SELECTED_USERS.size + ' seleccionado'+(SELECTED_USERS.size===1?'':'s');
  }

  async function crearNuevaConv(){
    if (!SELECTED_USERS.size){ alert('Selecciona al menos un usuario'); return; }
    var tipo = document.querySelector('input[name="cw-tipo"]:checked').value;
    var miembros = Array.from(SELECTED_USERS);
    var nombre = '';
    if (tipo === 'grupo'){
      nombre = document.getElementById('cw-new-name').value.trim();
      if (!nombre){ alert('Pon un nombre al grupo'); return; }
      if (miembros.length < 2){ alert('Un grupo necesita al menos 2 personas'); return; }
    }
    try{
      var r = await fetch('/api/chat/threads', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({tipo: tipo, miembros: miembros, nombre: nombre})
      });
      var d = await r.json();
      if (d.thread_id){
        document.getElementById('cw-new').style.display = 'none';
        SELECTED_USERS.clear();
        // Refrescar lista en cache primero
        await cargarThreads();
        // Buscar el thread y abrirlo
        var t = (THREADS||[]).find(function(x){ return x.id === d.thread_id; });
        if (!t) {
          // Si no aparece, crear manualmente uno mínimo y abrir
          THREADS.push({id: d.thread_id, nombre: nombre || (tipo==='directo' ? miembros[0] : 'Nuevo grupo')});
        }
        abrirConversacion(d.thread_id);
      } else {
        alert('Error: '+(d.error || 'no se pudo crear'));
      }
    }catch(e){ alert('Error de red'); }
  }

  // ── Asignar tarea desde el chat ─────────────────────────────────
  document.getElementById('cw-task-btn').onclick = function(){
    if (!ACTIVE_THREAD) return;
    document.getElementById('cw-task-titulo').value = '';
    document.getElementById('cw-task-descr').value = '';
    document.getElementById('cw-task-asign').value = '';
    document.getElementById('cw-task-fecha').value = '';
    document.getElementById('cw-task-modal').style.display = 'flex';
  };
  document.getElementById('cw-task-cancel').onclick = function(){
    document.getElementById('cw-task-modal').style.display = 'none';
  };
  document.getElementById('cw-task-save').onclick = async function(){
    var titulo = document.getElementById('cw-task-titulo').value.trim();
    var asign = document.getElementById('cw-task-asign').value.trim();
    if (!titulo){ alert('Título requerido'); return; }
    if (!asign){ alert('Asigna a al menos 1 usuario'); return; }
    try{
      var r = await fetch('/api/chat/threads/'+ACTIVE_THREAD+'/asignar-tarea', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          titulo: titulo,
          descripcion: document.getElementById('cw-task-descr').value,
          asignado_a: asign,
          fecha_objetivo: document.getElementById('cw-task-fecha').value || null
        })
      });
      var d = await r.json();
      if (d.ok || d.tarea_id){
        document.getElementById('cw-task-modal').style.display = 'none';
        abrirConversacion(ACTIVE_THREAD);  // refrescar mensajes — incluye el msg tipo 'tarea'
      } else {
        alert('Error: '+(d.error || 'no se creó'));
      }
    }catch(e){ alert('Error de red'); }
  };

  function _esc(s){ return (s==null?'':String(s)).replace(/[<>&"']/g, function(c){return {'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c]; }); }

  function _tiempoRel(iso){
    if(!iso) return '';
    var d = new Date(iso.replace(' ','T')+'Z');
    var diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return 'ahora';
    if (diff < 3600) return Math.floor(diff/60) + 'm';
    if (diff < 86400) return Math.floor(diff/3600) + 'h';
    return Math.floor(diff/86400) + 'd';
  }

  async function cargarThreads(){
    var box = document.getElementById('cw-tlist');
    try {
      var r = await fetch('/api/chat/threads');
      var d = await r.json();
      var threads = d.threads || [];
      THREADS = threads;
      if (!threads.length) {
        box.innerHTML = '<div class="cw-empty">Sin conversaciones aún. Abre el chat completo para iniciar una.</div>';
        return;
      }
      box.innerHTML = threads.map(function(t){
        var unread = t.no_leidos || t.unread_count || 0;
        // Sebastian (29-abr-2026): mostrar siempre con quien hablas.
        // El backend ya manda nombre_display con fallback al otro miembro.
        var nm = t.nombre_display || t.nombre || (t.otros_miembros||[])[0] || 'Sin nombre';
        var pv = t.ultimo_mensaje_preview || '';
        var ts = _tiempoRel(t.ultimo_mensaje_en || t.creado_en);
        return '<div class="cw-thread'+(unread>0?' unread':'')+'" data-id="'+t.id+'">'+
          '<div style="flex:1;min-width:0">'+
            '<div class="nm">'+_esc(nm)+(unread>0?'<span class="uc">'+unread+'</span>':'')+'</div>'+
            (pv?'<div class="pv">'+_esc(pv.substring(0,80))+'</div>':'')+
          '</div>'+
          '<div class="ts">'+ts+'</div>'+
        '</div>';
      }).join('');
      // Wire click
      box.querySelectorAll('.cw-thread').forEach(function(el){
        el.onclick = function(){ abrirConversacion(parseInt(el.dataset.id)); };
      });
      box.style.display = 'block';
    } catch(e) {
      box.innerHTML = '<div class="cw-empty">Error al cargar.</div>';
    }
  }

  async function abrirConversacion(thread_id){
    ACTIVE_THREAD = thread_id;
    var t = (THREADS||[]).find(function(x){ return x.id === thread_id; });
    document.getElementById('cw-conv-title').textContent = (t && (t.nombre_display || t.nombre)) || ('Hilo #'+thread_id);
    document.getElementById('cw-tlist').style.display = 'none';
    document.getElementById('cw-conv').style.display = 'flex';
    var msgsBox = document.getElementById('cw-msgs');
    msgsBox.innerHTML = '<div class="cw-empty">Cargando...</div>';
    try {
      var r = await fetch('/api/chat/threads/'+thread_id+'/messages?limit=40');
      var d = await r.json();
      var msgs = d.messages || [];
      if (!msgs.length) {
        msgsBox.innerHTML = '<div class="cw-empty">Sin mensajes — empieza la conversación.</div>';
      } else {
        msgsBox.innerHTML = msgs.map(function(m){
          var own = (m.sender||'').toLowerCase() === (ME||'').toLowerCase();
          return '<div class="cw-m '+(own?'own':'other')+'">'+
            (own?'':'<div class="who">'+_esc(m.sender)+'</div>')+
            _esc(m.contenido||'')+
          '</div>';
        }).join('');
        msgsBox.scrollTop = msgsBox.scrollHeight;
      }
      // Marcar leído
      fetch('/api/chat/threads/'+thread_id+'/leer', {method:'POST'}).catch(function(){});
      checkUnread();
    } catch(e) {
      msgsBox.innerHTML = '<div class="cw-empty">Error.</div>';
    }
  }

  async function enviarMensaje(){
    if (!ACTIVE_THREAD) return;
    var inp = document.getElementById('cw-text');
    var txt = (inp.value || '').trim();
    if (!txt) return;
    inp.value = '';
    try {
      var r = await fetch('/api/chat/threads/'+ACTIVE_THREAD+'/messages', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({contenido: txt, tipo_mensaje: 'texto'})
      });
      if (r.ok) {
        // Recargar mensajes
        abrirConversacion(ACTIVE_THREAD);
      }
    } catch(e){}
  }

  // Polling unread + refresh cuando panel abierto
  var lastTotal = 0;
  function checkUnread(){
    fetch('/api/chat/unread-summary').then(function(r){return r.json();}).then(function(d){
      var total = d.total || 0;
      var b = document.getElementById('cw-badge');
      if (b) {
        if (total > 0) { b.textContent = total > 99 ? '99+' : total; b.style.display = 'flex'; }
        else b.style.display = 'none';
      }
      if (total > lastTotal && lastTotal > 0) {
        var nuevo = total - lastTotal;
        showToast('\u{1F4AC} ' + nuevo + ' mensaje' + (nuevo>1?'s':'') + ' nuevo' + (nuevo>1?'s':''),
                  'Click para abrir el chat');
        try {
          var ctx = new (window.AudioContext || window.webkitAudioContext)();
          var osc = ctx.createOscillator(); var gain = ctx.createGain();
          osc.connect(gain); gain.connect(ctx.destination);
          osc.frequency.setValueAtTime(880, ctx.currentTime);
          osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.15);
          gain.gain.setValueAtTime(0.15, ctx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.18);
          osc.start(); osc.stop(ctx.currentTime + 0.2);
        } catch(e){}
      }
      lastTotal = total;
      // Si panel abierto y no estoy en una conv, recargar lista
      if (panel.style.display === 'flex' && !ACTIVE_THREAD) cargarThreads();
      // Si en una conv, recargar sus mensajes
      if (panel.style.display === 'flex' && ACTIVE_THREAD) {
        fetch('/api/chat/threads/'+ACTIVE_THREAD+'/messages?limit=40').then(function(r){return r.json();}).then(function(d){
          var msgs = d.messages || [];
          var box = document.getElementById('cw-msgs');
          if (!box) return;
          var prevScroll = box.scrollTop;
          var atBottom = (box.scrollHeight - prevScroll - box.clientHeight) < 50;
          box.innerHTML = msgs.map(function(m){
            var own = (m.sender||'').toLowerCase() === (ME||'').toLowerCase();
            return '<div class="cw-m '+(own?'own':'other')+'">'+
              (own?'':'<div class="who">'+_esc(m.sender)+'</div>')+_esc(m.contenido||'')+'</div>';
          }).join('');
          if (atBottom) box.scrollTop = box.scrollHeight;
        }).catch(function(){});
      }
    }).catch(function(){});
  }

  function showToast(titulo, sub){
    var prev = document.getElementById('cw-toast');
    if (prev) prev.remove();
    var t = document.createElement('div');
    t.id = 'cw-toast';
    t.innerHTML = '<div style="font-weight:700;margin-bottom:2px">'+titulo+'</div><div style="font-size:11px;color:#cbd5e1">'+sub+'</div>';
    t.onclick = function(){
      if (panel.style.display !== 'flex') { panel.style.display = 'flex'; cargarThreads(); }
      t.remove();
    };
    document.body.appendChild(t);
    setTimeout(function(){ if (t.parentNode) t.remove(); }, 6000);
  }

  checkUnread();
  setInterval(checkUnread, 12000);
})();
"""
    resp = Response(js, mimetype="application/javascript")
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    return resp


@bp.route('/chat')
def chat_ui():
    if 'compras_user' not in session:
        from flask import redirect
        return redirect('/login?next=/chat')
    from templates_py.chat_html import CHAT_HTML
    user = session.get('compras_user', '')
    html = CHAT_HTML.replace('{usuario}', user)
    return Response(html, mimetype='text/html; charset=utf-8')


# ─── PRESENCIA ───────────────────────────────────────────────────────
@bp.route('/api/chat/heartbeat', methods=['POST'])
def chat_heartbeat():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    c.execute("""
        INSERT INTO chat_user_presence (username, last_heartbeat, estado, display_name)
        VALUES (?, datetime('now'), 'conectado', ?)
        ON CONFLICT(username) DO UPDATE SET
          last_heartbeat = datetime('now'),
          estado = 'conectado'
    """, (user, user.capitalize()))
    conn.commit()
    return jsonify({'ok': True, 'username': user})


@bp.route('/api/chat/users', methods=['GET'])
def chat_users():
    """Lista todos los usuarios del sistema con su estado de presencia."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    me = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    # Leer presence (auto-degradar a 'desconectado' si > 90s sin heartbeat)
    rows = c.execute("""
        SELECT username,
               COALESCE(display_name, username) as display_name,
               CASE
                 WHEN last_heartbeat IS NULL THEN 'desconectado'
                 WHEN (julianday('now') - julianday(last_heartbeat)) * 86400 > 90 THEN 'desconectado'
                 ELSE 'conectado'
               END as estado_real,
               last_heartbeat
        FROM chat_user_presence
    """).fetchall()
    presence = {r[0]: {'display_name': r[1], 'estado': r[2], 'last_heartbeat': r[3]} for r in rows}
    # Fusionar con la lista total de usuarios del sistema
    users = []
    for u in (COMPRAS_USERS or []):
        if u == me:
            continue  # no me listo a mí mismo
        p = presence.get(u, {})
        users.append({
            'username': u,
            'display_name': p.get('display_name') or u.capitalize(),
            'estado': p.get('estado') or 'desconectado',
            'last_heartbeat': p.get('last_heartbeat'),
        })
    # Ordenar: conectados primero, luego alfabético
    users.sort(key=lambda x: (0 if x['estado'] == 'conectado' else 1, x['username']))
    return jsonify({'users': users, 'me': me})


# ─── THREADS ──────────────────────────────────────────────────────────
@bp.route('/api/chat/threads', methods=['GET', 'POST'])
def chat_threads():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        d = request.json or {}
        tipo = (d.get('tipo') or 'directo').strip()
        if tipo not in ('directo', 'grupo', 'broadcast'):
            return jsonify({'error': 'tipo invalido'}), 400
        miembros = [u.strip() for u in (d.get('miembros') or []) if u.strip()]
        nombre = (d.get('nombre') or '').strip()

        # Para 1-a-1: si ya existe thread con esos 2 miembros, devolverlo
        if tipo == 'directo' and len(miembros) == 1:
            otro = miembros[0]
            existing = c.execute("""
                SELECT t.id FROM chat_threads t
                WHERE t.tipo='directo' AND t.activo=1
                  AND EXISTS (SELECT 1 FROM chat_thread_members WHERE thread_id=t.id AND username=?)
                  AND EXISTS (SELECT 1 FROM chat_thread_members WHERE thread_id=t.id AND username=?)
                  AND (SELECT COUNT(*) FROM chat_thread_members WHERE thread_id=t.id) = 2
                LIMIT 1
            """, (user, otro)).fetchone()
            if existing:
                return jsonify({'ok': True, 'thread_id': existing[0], 'ya_existia': True})

        # Broadcast: solo creador, al "Todos · HHA Group" único
        if tipo == 'broadcast':
            existing = c.execute("SELECT id FROM chat_threads WHERE tipo='broadcast' LIMIT 1").fetchone()
            if existing:
                return jsonify({'ok': True, 'thread_id': existing[0], 'ya_existia': True})
            nombre = nombre or 'Todos · HHA Group'

        cur = c.execute("""
            INSERT INTO chat_threads (tipo, nombre, creado_por)
            VALUES (?, ?, ?)
        """, (tipo, nombre, user))
        thread_id = cur.lastrowid

        # Yo siempre soy miembro
        c.execute("""INSERT OR IGNORE INTO chat_thread_members (thread_id, username, rol)
                     VALUES (?, ?, 'creador')""", (thread_id, user))
        # Agregar miembros adicionales
        for m in miembros:
            if m == user:
                continue
            c.execute("""INSERT OR IGNORE INTO chat_thread_members (thread_id, username)
                         VALUES (?, ?)""", (thread_id, m))
        # Para broadcast, agregar TODOS los usuarios
        if tipo == 'broadcast':
            for u in (COMPRAS_USERS or []):
                if u == user:
                    continue
                c.execute("""INSERT OR IGNORE INTO chat_thread_members (thread_id, username)
                             VALUES (?, ?)""", (thread_id, u))
        conn.commit()
        return jsonify({'ok': True, 'thread_id': thread_id})

    # GET — mis threads con preview del último mensaje + unread count
    rows = c.execute("""
        SELECT t.id, t.tipo, t.nombre, t.ultimo_mensaje_preview, t.ultimo_mensaje_en,
               t.creado_por,
               m.ultimo_leido_id,
               t.ultimo_mensaje_id,
               (SELECT COUNT(*) FROM chat_messages WHERE thread_id=t.id
                  AND id > COALESCE(m.ultimo_leido_id, 0)
                  AND sender != ? AND eliminado=0) as no_leidos,
               (SELECT GROUP_CONCAT(username, ',') FROM chat_thread_members
                  WHERE thread_id=t.id AND username != ?) as otros_miembros
        FROM chat_threads t
        JOIN chat_thread_members m ON m.thread_id = t.id AND m.username = ?
        WHERE t.activo = 1
        ORDER BY t.ultimo_mensaje_en DESC NULLS LAST, t.creado_en DESC
        LIMIT 100
    """, (user, user, user)).fetchall()
    threads = []
    for r in rows:
        tipo = r[1]
        nombre_raw = (r[2] or '').strip()
        otros = (r[9] or '').split(',') if r[9] else []
        otros = [o for o in otros if o]
        # Sebastian (29-abr-2026): "no sale con quien estoy hablando".
        # 'directo' guarda nombre='' en BD; calculamos nombre_display aqui
        # cayendo al otro miembro. Para grupos sin nombre, lista corta.
        # Mantenemos 'nombre' raw para que /chat siga mapeando display_name.
        if nombre_raw:
            nombre_disp = nombre_raw
        elif tipo == 'directo' and otros:
            nombre_disp = otros[0]
        elif tipo == 'broadcast':
            nombre_disp = 'Todos · HHA Group'
        elif otros:
            nombre_disp = ', '.join(otros[:3]) + ('…' if len(otros) > 3 else '')
        else:
            nombre_disp = f'Hilo #{r[0]}'
        threads.append({
            'id': r[0], 'tipo': tipo,
            'nombre': nombre_raw,           # raw (puede ser '')
            'nombre_display': nombre_disp,  # siempre con fallback
            'ultimo_mensaje_preview': r[3], 'ultimo_mensaje_en': r[4],
            'creado_por': r[5],
            'no_leidos': r[8] or 0,
            'otros_miembros': otros,
        })
    return jsonify({'threads': threads})


@bp.route('/api/chat/threads/<int:thread_id>/messages', methods=['GET', 'POST'])
def chat_messages(thread_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    # Verificar que soy miembro
    member = c.execute(
        "SELECT 1 FROM chat_thread_members WHERE thread_id=? AND username=?",
        (thread_id, user)
    ).fetchone()
    if not member:
        return jsonify({'error': 'No eres miembro de este chat'}), 403

    if request.method == 'POST':
        d = request.json or {}
        contenido = (d.get('contenido') or '').strip()
        if not contenido:
            return jsonify({'error': 'contenido requerido'}), 400
        tipo = (d.get('tipo_mensaje') or 'texto').strip()
        if tipo not in ('texto', 'tarea', 'compromiso', 'archivo', 'imagen', 'sistema', 'llamado_atencion'):
            tipo = 'texto'
        # Parsear @menciones del contenido (Fase 4) — solo nombres de
        # usuarios que SI son miembros del thread. Esto evita spam y
        # crear menciones invalidas.
        import re as _re
        mention_candidates = set(
            m.lower() for m in _re.findall(r'(?:^|\s)@([a-z0-9_.-]+)', contenido, _re.IGNORECASE)
        )
        valid_mentions = []
        if mention_candidates:
            placeholders = ','.join('?' * len(mention_candidates))
            cands = list(mention_candidates)
            members_rows = c.execute(
                f"SELECT LOWER(username) FROM chat_thread_members WHERE thread_id=? "
                f"AND LOWER(username) IN ({placeholders})",
                [thread_id] + cands
            ).fetchall()
            valid_mentions = [r[0] for r in members_rows]
        import json as _json
        meta_dict = d.get('metadata') or {}
        if valid_mentions:
            meta_dict['mentions'] = valid_mentions
        meta = _json.dumps(meta_dict)
        cur = c.execute("""
            INSERT INTO chat_messages
              (thread_id, sender, contenido, tipo_mensaje, metadata_json,
               tarea_operativa_id, compromiso_id, reply_to_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (thread_id, user, contenido, tipo, meta,
              d.get('tarea_operativa_id'), d.get('compromiso_id'),
              d.get('reply_to_id')))
        msg_id = cur.lastrowid
        # Update thread metadata
        preview = contenido[:120] if tipo == 'texto' else f'[{tipo}] {contenido[:100]}'
        c.execute("""
            UPDATE chat_threads SET
              ultimo_mensaje_id=?, ultimo_mensaje_en=datetime('now'),
              ultimo_mensaje_preview=?
            WHERE id=?
        """, (msg_id, preview, thread_id))
        # Marcar como leído para mí (el sender)
        c.execute("""
            UPDATE chat_thread_members SET ultimo_leido_id=?
            WHERE thread_id=? AND username=?
        """, (msg_id, thread_id, user))
        conn.commit()

        # Push notif in-app a TODOS los miembros del hilo (excepto el sender).
        # Tipo: chat_msg (genérico) o chat_mencion (importante) si fue @mencionado.
        try:
            from blueprints.notif import push_notif
            miembros = c.execute("""
                SELECT username FROM chat_thread_members
                WHERE thread_id=? AND username != ?
            """, (thread_id, user)).fetchall()
            # Datos del thread para mostrar nombre
            t_row = c.execute("SELECT nombre FROM chat_threads WHERE id=?", (thread_id,)).fetchone()
            t_nombre = t_row[0] if t_row else f'hilo #{thread_id}'
            preview_short = (contenido[:120]) if tipo=='texto' else f'[{tipo}]'
            for (m,) in miembros:
                if not m: continue
                m_low = m.lower()
                es_mencion = m_low in {x.lower() for x in (valid_mentions or [])}
                push_notif(
                    m_low,
                    'chat_mencion' if es_mencion else 'chat_msg',
                    (f'@{user} te mencionó' if es_mencion else f'{user} en {t_nombre}'),
                    body=preview_short,
                    link=f'/chat?thread={thread_id}',
                    remitente=user,
                    importante=es_mencion
                )
        except Exception as _e:
            logger.warning('push_notif chat fallo: %s', _e)

        # Email solo a los mencionados (no a todos los miembros).
        # Sebastian (29-abr-2026): asi en grupos grandes no se spamea
        # cuando alguien escribe algo no relevante para todos.
        if valid_mentions:
            try:
                import sys, os, threading as _th
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from notificaciones import SistemaNotificaciones
                from config import USER_EMAILS
                destinos = [USER_EMAILS.get(m, '') for m in valid_mentions if m != user.lower()]
                destinos = [e for e in destinos if e]
                if destinos:
                    asunto = f"@{user} te mencionó en el chat"
                    body = (
                        f"<h2>Te mencionaron en EOS Chat</h2>"
                        f"<p><b>{user}</b> escribió:</p>"
                        f"<div style='background:#f5f5f4;padding:14px;border-radius:8px;border-left:4px solid #6d28d9'>"
                        f"<i>{contenido[:500]}</i>"
                        f"</div>"
                        f"<p><a href='/chat'>Abrir el chat</a> para responder.</p>"
                        f"<p style='color:#94a3b8;font-size:11px'>Mensaje automatico HHA Group · EOS</p>"
                    )
                    notif = SistemaNotificaciones()
                    _th.Thread(
                        target=notif._enviar_email,
                        args=(asunto, body, destinos),
                        daemon=True
                    ).start()
            except Exception as _em:
                import logging
                logging.getLogger('chat').warning("Email mencion fallo: %s", _em)
        return jsonify({'ok': True, 'message_id': msg_id, 'mentions': valid_mentions})

    # GET — paginated (default últimos 50)
    limit = min(int(request.args.get('limit', 50)), 200)
    before_id = request.args.get('before_id')
    where_extra = "AND id < ?" if before_id else ""
    params = [thread_id]
    if before_id:
        params.append(int(before_id))
    params.append(limit)
    rows = c.execute(f"""
        SELECT id, sender, contenido, tipo_mensaje, metadata_json,
               tarea_operativa_id, compromiso_id, reply_to_id,
               creado_en, editado_en, eliminado
        FROM chat_messages
        WHERE thread_id=? AND eliminado=0 {where_extra}
        ORDER BY id DESC
        LIMIT ?
    """, params).fetchall()
    cols = [d[0] for d in c.description]
    messages = [dict(zip(cols, r)) for r in rows]
    # Enriquecer con reacciones (Fase 3) — agrega un dict {emoji: [users]} por msg
    if messages:
        msg_ids = [m['id'] for m in messages]
        placeholders = ','.join('?' * len(msg_ids))
        try:
            r_rows = c.execute(
                f"SELECT message_id, emoji, username FROM chat_reactions "
                f"WHERE message_id IN ({placeholders})",
                msg_ids
            ).fetchall()
            by_msg = {}
            for mid, em, uname in r_rows:
                by_msg.setdefault(mid, {}).setdefault(em, []).append(uname)
            for m in messages:
                m['reactions'] = by_msg.get(m['id'], {})
        except Exception:
            for m in messages:
                m['reactions'] = {}
    messages.reverse()  # cronológico ascendente
    return jsonify({'messages': messages})


@bp.route('/api/chat/threads/<int:thread_id>/leer', methods=['POST'])
def chat_marcar_leido(thread_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    last_msg = c.execute(
        "SELECT MAX(id) FROM chat_messages WHERE thread_id=?",
        (thread_id,)
    ).fetchone()
    last_id = last_msg[0] if last_msg else 0
    c.execute("""
        UPDATE chat_thread_members SET ultimo_leido_id=?
        WHERE thread_id=? AND username=?
    """, (last_id or 0, thread_id, user))
    conn.commit()
    return jsonify({'ok': True, 'ultimo_leido_id': last_id})


@bp.route('/api/chat/messages/<int:message_id>', methods=['DELETE', 'PATCH'])
def chat_mensaje_modificar(message_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    msg = c.execute("SELECT sender FROM chat_messages WHERE id=?", (message_id,)).fetchone()
    if not msg:
        return jsonify({'error': 'Mensaje no encontrado'}), 404
    if msg[0] != user:
        return jsonify({'error': 'Solo el autor puede modificar'}), 403
    if request.method == 'DELETE':
        c.execute("UPDATE chat_messages SET eliminado=1 WHERE id=?", (message_id,))
    else:
        d = request.json or {}
        nuevo = (d.get('contenido') or '').strip()
        if not nuevo:
            return jsonify({'error': 'contenido vacío'}), 400
        c.execute("""
            UPDATE chat_messages SET contenido=?, editado_en=datetime('now')
            WHERE id=?
        """, (nuevo, message_id))
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/chat/threads/<int:thread_id>/miembros', methods=['POST'])
def chat_agregar_miembros(thread_id):
    """Agregar miembros a un grupo. Solo el creador."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    th = c.execute("SELECT creado_por, tipo FROM chat_threads WHERE id=?", (thread_id,)).fetchone()
    if not th:
        return jsonify({'error': 'Thread no existe'}), 404
    if th[0] != user:
        return jsonify({'error': 'Solo el creador puede agregar miembros'}), 403
    if th[1] == 'directo':
        return jsonify({'error': 'No se pueden agregar miembros a un chat directo'}), 400
    d = request.json or {}
    miembros = [u.strip() for u in (d.get('miembros') or []) if u.strip()]
    added = 0
    for m in miembros:
        cur = c.execute(
            "INSERT OR IGNORE INTO chat_thread_members (thread_id, username) VALUES (?, ?)",
            (thread_id, m)
        )
        if cur.rowcount > 0:
            added += 1
    conn.commit()
    return jsonify({'ok': True, 'agregados': added})


@bp.route('/api/chat/threads/<int:thread_id>/asignar-tarea', methods=['POST'])
def chat_asignar_tarea(thread_id):
    """Crear tarea_operativa desde el chat + insertar mensaje tipo 'tarea'
    linkeado a la tarea + notificar por email a los asignados.

    Sebastian (29-abr-2026): Fase 2 del chat — asignacion de tareas inline.

    Body: {titulo, descripcion, asignado_a (csv), fecha_objetivo (YYYY-MM-DD)}
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    # Verificar membresia
    member = c.execute(
        "SELECT 1 FROM chat_thread_members WHERE thread_id=? AND username=?",
        (thread_id, user)
    ).fetchone()
    if not member:
        return jsonify({'error': 'No eres miembro de este chat'}), 403

    d = request.json or {}
    titulo = (d.get('titulo') or '').strip()
    descripcion = (d.get('descripcion') or '').strip()
    asignado_a = (d.get('asignado_a') or '').strip()
    fecha_obj = (d.get('fecha_objetivo') or '').strip()

    if not titulo:
        return jsonify({'error': 'titulo requerido'}), 400
    if not asignado_a:
        return jsonify({'error': 'asignado_a requerido (csv: usuario1,usuario2)'}), 400

    # 1. Crear la tarea operativa
    try:
        cur = c.execute("""
            INSERT INTO tareas_operativas
              (titulo, descripcion, tipo, asignado_a, fecha_objetivo, estado,
               origen_tipo, origen_id, creado_por)
            VALUES (?, ?, 'chat_asignacion', ?, ?, 'pendiente',
                    'chat', ?, ?)
        """, (titulo, descripcion or titulo, asignado_a, fecha_obj or '',
              thread_id, user))
        tarea_id = cur.lastrowid
    except Exception as e:
        return jsonify({'error': f'Error creando tarea: {e}'}), 500

    # 2. Insertar mensaje en el chat tipo='tarea' linkeado a la tarea
    contenido = f"📋 {titulo}"
    if fecha_obj:
        contenido += f"  ·  ⏰ {fecha_obj}"
    contenido += f"  ·  → {asignado_a}"
    cur2 = c.execute("""
        INSERT INTO chat_messages
          (thread_id, sender, contenido, tipo_mensaje, tarea_operativa_id)
        VALUES (?, ?, ?, 'tarea', ?)
    """, (thread_id, user, contenido, tarea_id))
    msg_id = cur2.lastrowid

    # 3. Update thread metadata (igual que en POST messages normal)
    preview = f"[tarea] {titulo[:100]}"
    c.execute("""
        UPDATE chat_threads SET
          ultimo_mensaje_id=?, ultimo_mensaje_en=datetime('now'),
          ultimo_mensaje_preview=?
        WHERE id=?
    """, (msg_id, preview, thread_id))
    c.execute("""
        UPDATE chat_thread_members SET ultimo_leido_id=?
        WHERE thread_id=? AND username=?
    """, (msg_id, thread_id, user))
    conn.commit()

    # 4. Notificar por email a los asignados (no-bloqueante)
    try:
        import sys, os, threading
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from notificaciones import SistemaNotificaciones
        from config import USER_EMAILS
        destinos = []
        for asig in asignado_a.split(','):
            asig_clean = asig.strip().lower()
            email = USER_EMAILS.get(asig_clean, '')
            if email:
                destinos.append(email)
        if destinos:
            asunto = f"📋 Nueva tarea asignada: {titulo[:80]}"
            body = (
                f"<h2>Nueva tarea desde el chat EOS</h2>"
                f"<p><b>{user}</b> te asignó:</p>"
                f"<div style='background:#f5f5f4;padding:14px;border-radius:8px;border-left:4px solid #7c3aed'>"
                f"<b>{titulo}</b>"
                + (f"<br><i>{descripcion}</i>" if descripcion and descripcion != titulo else "")
                + (f"<br>⏰ <b>Fecha objetivo:</b> {fecha_obj}" if fecha_obj else "")
                + f"<br>👥 <b>Asignados:</b> {asignado_a}"
                + f"</div>"
                + f"<p>Revisa la tarea en <a href='/chat'>el chat</a> o en /planta → Tareas Operativas.</p>"
                + f"<p style='color:#94a3b8;font-size:11px'>Mensaje automatico HHA Group · EOS</p>"
            )
            notif = SistemaNotificaciones()
            threading.Thread(
                target=notif._enviar_email,
                args=(asunto, body, destinos),
                daemon=True
            ).start()
    except Exception as _e:
        # Falla silenciosa — el chat no debe bloquearse por email
        import logging
        logging.getLogger('chat').warning("Email asignacion tarea fallo: %s", _e)

    return jsonify({
        'ok': True,
        'tarea_id': tarea_id,
        'message_id': msg_id,
        'mensaje': f'Tarea creada y asignada a {asignado_a}'
    })


# ─── Fase 3: Reacciones a mensajes ──────────────────────────────────────
@bp.route('/api/chat/messages/<int:message_id>/react', methods=['POST', 'DELETE'])
def chat_message_reaccion(message_id):
    """Toggle de una reaccion (emoji) a un mensaje.
    POST con body {emoji} agrega; DELETE quita. Idempotente."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    msg = c.execute(
        "SELECT thread_id FROM chat_messages WHERE id=?", (message_id,)
    ).fetchone()
    if not msg:
        return jsonify({'error': 'Mensaje no existe'}), 404
    member = c.execute(
        "SELECT 1 FROM chat_thread_members WHERE thread_id=? AND username=?",
        (msg[0], user)
    ).fetchone()
    if not member:
        return jsonify({'error': 'No eres miembro de este chat'}), 403
    d = request.json or {}
    emoji = (d.get('emoji') or '').strip()
    EMOJIS_OK = ('👍', '❤️', '😂', '🔥', '👀', '✅', '❌', '🙏')
    if emoji not in EMOJIS_OK:
        return jsonify({'error': f'emoji invalido (usar uno de {EMOJIS_OK})'}), 400
    if request.method == 'DELETE':
        c.execute(
            "DELETE FROM chat_reactions WHERE message_id=? AND username=? AND emoji=?",
            (message_id, user, emoji)
        )
    else:
        # Toggle: si ya existe, borrar. Si no, agregar.
        existing = c.execute(
            "SELECT id FROM chat_reactions WHERE message_id=? AND username=? AND emoji=?",
            (message_id, user, emoji)
        ).fetchone()
        if existing:
            c.execute("DELETE FROM chat_reactions WHERE id=?", (existing[0],))
        else:
            c.execute(
                "INSERT INTO chat_reactions (message_id, username, emoji) VALUES (?, ?, ?)",
                (message_id, user, emoji)
            )
    conn.commit()
    # Devolver counts actualizados de ese mensaje
    rows = c.execute(
        "SELECT emoji, COUNT(*) FROM chat_reactions WHERE message_id=? GROUP BY emoji",
        (message_id,)
    ).fetchall()
    return jsonify({
        'ok': True,
        'reactions': [{'emoji': r[0], 'count': r[1]} for r in rows]
    })


# ─── Fase 3: Busqueda global en mensajes ──────────────────────────────
@bp.route('/api/chat/search', methods=['GET'])
def chat_search():
    """Busca en chat_messages por contenido — solo en threads donde el user
    es miembro. Devuelve top 30 matches con contexto."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return jsonify({'results': [], 'q': q, 'mensaje': 'Escribe al menos 2 letras'})
    conn = get_db(); c = conn.cursor()
    rows = c.execute("""
        SELECT m.id, m.thread_id, m.sender, m.contenido, m.tipo_mensaje,
               m.creado_en, t.tipo as thread_tipo, t.nombre as thread_nombre
        FROM chat_messages m
        JOIN chat_threads t ON t.id = m.thread_id
        WHERE m.eliminado=0
          AND m.thread_id IN (
            SELECT thread_id FROM chat_thread_members WHERE username=?
          )
          AND LOWER(m.contenido) LIKE LOWER(?)
        ORDER BY m.creado_en DESC
        LIMIT 30
    """, (user, f"%{q}%")).fetchall()
    cols = [d[0] for d in c.description]
    results = [dict(zip(cols, r)) for r in rows]
    return jsonify({'results': results, 'q': q, 'count': len(results)})


# ─── Fase 3: Resumen global de mensajes no leidos (badge widget) ─────
@bp.route('/api/chat/unread-summary', methods=['GET'])
def chat_unread_summary():
    """Devuelve total de mensajes no leidos del usuario para el badge
    del widget flotante. Liviano — usado por polling cada 10-15s."""
    if 'compras_user' not in session:
        return jsonify({'total': 0, 'threads': []}), 200  # 200 silencioso
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    try:
        rows = c.execute("""
            SELECT t.id, t.tipo, t.nombre, t.ultimo_mensaje_preview,
                   t.ultimo_mensaje_en, m.username as me_user,
                   m.ultimo_leido_id,
                   (SELECT COUNT(*) FROM chat_messages msg
                    WHERE msg.thread_id=t.id
                      AND msg.eliminado=0
                      AND msg.sender != ?
                      AND (m.ultimo_leido_id IS NULL OR msg.id > m.ultimo_leido_id)
                   ) as unread
            FROM chat_threads t
            JOIN chat_thread_members m ON m.thread_id=t.id
            WHERE m.username=?
        """, (user, user)).fetchall()
        cols = [d[0] for d in c.description]
        threads_unread = [dict(zip(cols, r)) for r in rows if (r[-1] or 0) > 0]
        total = sum(t['unread'] for t in threads_unread)
        return jsonify({'total': total, 'threads': threads_unread})
    except Exception as e:
        return jsonify({'total': 0, 'threads': [], '_err': str(e)}), 200
