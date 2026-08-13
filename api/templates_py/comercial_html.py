"""Template Comercial - Pipeline Maquila + EOS Leads."""

HTML = r"""<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Comercial · HHA Group</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:var(--cx-bg-alt);color:var(--cx-text);font-size:14px}
.topbar{background:linear-gradient(90deg,#581c87,#7c3aed);color:#fff;padding:14px 20px;display:flex;align-items:center;gap:14px}
.topbar h1{font-size:18px;font-weight:700;flex:1}
.topbar a{color:var(--cx-border);text-decoration:none;font-size:13px;padding:6px 12px;border-radius:6px;background:rgba(255,255,255,.1)}
.tabs{background:var(--cx-card);border-bottom:2px solid var(--cx-border);display:flex;gap:0}
.tabbtn{padding:12px 22px;font-size:13px;font-weight:600;color:var(--cx-text-mute);background:none;border:none;cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-2px}
.tabbtn:hover{background:var(--cx-bg-alt);color:var(--cx-primary-text)}
.tabbtn.on{color:var(--cx-primary-text);border-bottom-color:var(--cx-primary);font-weight:700}
.pane{display:none;padding:22px 24px;max-width:1400px;margin:0 auto}
.pane.on{display:block}
.btn{padding:7px 14px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer}
.btn-primary{background:var(--cx-primary);color:#fff}.btn-primary:hover{background:var(--cx-primary)}
.btn-secondary{background:var(--cx-border);color:var(--cx-text-soft)}
.btn-success{background:var(--cx-success);color:#fff}
.btn-danger{background:var(--cx-danger);color:#fff}
.btn-sm{padding:4px 8px;font-size:11px}
input,select,textarea{padding:7px 10px;border:1px solid var(--cx-border);border-radius:6px;font-size:13px;font-family:inherit;width:100%}
input:focus,select:focus,textarea:focus{border-color:var(--cx-primary);outline:none}
.row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.row > * {flex:1;min-width:180px}
label{font-size:12px;font-weight:600;color:var(--cx-text-soft);display:block;margin-bottom:4px}
.empty{text-align:center;color:var(--cx-text-faint);padding:30px;font-style:italic}
/* Kanban styles */
.kanban{display:flex;gap:12px;overflow-x:auto;padding:4px;align-items:flex-start}
.kcol{min-width:240px;background:var(--cx-border-soft);border-radius:10px;padding:8px}
.kcol-h{font-size:11px;text-transform:uppercase;letter-spacing:.5px;font-weight:700;color:var(--cx-text-soft);padding:4px 8px;display:flex;justify-content:space-between;align-items:center}
.kcard{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:8px;padding:10px;margin-top:8px;font-size:12px;cursor:pointer;transition:all .15s}
.kcard:hover{box-shadow:0 4px 12px rgba(0,0,0,.08);border-color:var(--cx-primary)}
.kcard b{display:block;color:var(--cx-text);font-size:13px;margin-bottom:4px}
.kcard .meta{font-size:10px;color:var(--cx-text-mute);margin-top:6px}
.kcard .v{font-weight:700;color:var(--cx-success-text);font-size:12px}
.b-stage-consulta{background:var(--cx-border);color:var(--cx-text-soft)}
.b-stage-nda{background:var(--cx-info-pale);color:var(--cx-info-text)}
.b-stage-brief{background:#e0e7ff;color:#3730a3}
.b-stage-cotizacion{background:var(--cx-warn-pale);color:var(--cx-warn-text)}
.b-stage-contrato{background:var(--cx-warn-pale);color:var(--cx-warn-text)}
.b-stage-produccion{background:var(--cx-success-pale);color:var(--cx-success-text)}
.b-stage-ganado{background:var(--cx-success);color:#fff}
.b-stage-perdido{background:var(--cx-danger-pale);color:var(--cx-danger-text)}
</style>
</head>
<body>
<div class="topbar">
  <h1>💼 Comercial · HHA Group</h1>
  <a href="/modulos">Módulos</a>
</div>

<div class="tabs">
  <button class="tabbtn on" data-pane="maq" onclick="switchPane('maq')">🏭 Pipeline Maquila B2B</button>
  <button class="tabbtn" data-pane="eos" onclick="switchPane('eos')">🚀 EOS Leads</button>
  <button class="tabbtn" data-pane="correo" onclick="switchPane('correo')">📬 Correo de direcci&oacute;n</button>
</div>

<!-- PANE: Maquila -->
<div id="pane-maq" class="pane on">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;flex-wrap:wrap;gap:8px">
    <h3 style="color:#581c87">Pipeline Maquila Full Service</h3>
    <div style="display:flex;align-items:center;gap:10px">
      <span style="font-size:12px;color:var(--cx-text-mute)">Pipeline activo: <b id="maq-valor" style="color:var(--cx-success-text)">$0</b></span>
      <button class="btn btn-primary" onclick="abrirModalMaquila()">+ Nuevo deal</button>
    </div>
  </div>
  <div id="maq-kanban" class="kanban"></div>
</div>

<!-- PANE: Correo de direccion · los prospectos de maquila que llegan al buzon -->
<div id="pane-correo" class="pane">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:8px">
    <div>
      <h3 style="color:#581c87">Prospectos que llegaron al correo</h3>
      <div style="font-size:12px;color:var(--cx-text-mute);margin-top:2px">A <b>direcci&oacute;n@animuslb.com</b> s&oacute;lo llegan los de maquila, as&iacute; que todo lo que aparece ac&aacute; es un prospecto. El correo se lee sin marcarlo como le&iacute;do.</div>
    </div>
    <button class="btn btn-primary" id="btn-leer-buzon" onclick="leerBuzon()">&#128229; Leer ahora</button>
  </div>
  <div id="correo-estado" style="margin-bottom:12px"></div>
  <div id="correo-list">Cargando&hellip;</div>
</div>

<!-- PANE: EOS Leads -->
<div id="pane-eos" class="pane">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;flex-wrap:wrap;gap:8px">
    <h3 style="color:#581c87">Leads de demo · landing eossuite.com</h3>
    <select id="eos-filtro" onchange="cargarEosLeads()" style="width:auto">
      <option value="">Todos</option>
      <option value="nuevo">Nuevos</option>
      <option value="contactado">Contactados</option>
      <option value="demo_agendada">Demo agendada</option>
      <option value="propuesta">Propuesta enviada</option>
      <option value="cerrado">Cerrados</option>
    </select>
  </div>
  <div style="background:var(--cx-warn-pale);border-left:4px solid var(--cx-accent-dark);padding:12px 16px;margin-bottom:16px;border-radius:0 6px 6px 0;font-size:13px">
    <b>📥 Webhook activo:</b> <code style="background:var(--cx-card);padding:2px 6px;border-radius:4px;font-size:11px">POST /api/eos/leads/webhook</code>
    - configura web3forms o cualquier form para enviar aquí. Llega notif in-app automática.
  </div>
  <div id="eos-list"></div>
</div>

<!-- MODAL: Nuevo deal maquila -->
<div id="modal-maq" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.7);z-index:9999;align-items:center;justify-content:center;padding:20px">
  <div style="background:var(--cx-card);border-radius:14px;padding:22px 26px;max-width:520px;width:100%;max-height:90vh;overflow-y:auto">
    <h3 style="color:#581c87;margin-bottom:14px" id="maq-modal-title">Nuevo deal maquila</h3>
    <input type="hidden" id="mq-id">
    <div style="margin-bottom:10px"><label>Empresa</label><input id="mq-empresa" type="text"></div>
    <div class="row">
      <div><label>Contacto nombre</label><input id="mq-contacto" type="text"></div>
      <div><label>Email</label><input id="mq-email" type="email"></div>
    </div>
    <div class="row">
      <div><label>Teléfono</label><input id="mq-tel" type="text"></div>
      <div><label>Origen</label><input id="mq-origen" type="text" placeholder="consulta web, referido..."></div>
    </div>
    <div class="row">
      <div><label>Stage</label>
        <select id="mq-stage">
          <option value="consulta">Consulta inicial</option>
          <option value="nda">NDA firmado</option>
          <option value="brief">Brief recibido</option>
          <option value="cotizacion">Cotización enviada</option>
          <option value="contrato">Contrato firmado</option>
          <option value="produccion">En producción</option>
          <option value="ganado">Ganado</option>
          <option value="perdido">Perdido</option>
        </select>
      </div>
      <div><label>Valor estimado COP</label><input id="mq-valor" type="number" min="0" value="0"></div>
    </div>
    <div class="row">
      <div><label>Volumen estimado (uds)</label><input id="mq-volumen" type="number" min="0" value="0"></div>
      <div><label>Cierre estimado</label><input id="mq-cierre" type="date"></div>
    </div>
    <div style="margin-bottom:10px"><label>Producto / descripción</label><textarea id="mq-prod" rows="2" placeholder="Ej: Suero hidratante x 30ml, 5000 uds"></textarea></div>
    <div style="margin-bottom:14px"><label>Notas</label><textarea id="mq-notas" rows="2"></textarea></div>
    <div style="display:flex;justify-content:flex-end;gap:8px">
      <button class="btn btn-secondary" onclick="document.getElementById('modal-maq').style.display='none'">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarMaquila()">Guardar</button>
    </div>
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
function _esc(s){return (s==null?'':String(s)).replace(/[<>&"']/g,function(c){return {'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c];});}
function _fmtCOP(n){if(n==null||n===0) return '-'; return '$'+Math.round(n).toLocaleString('es-CO');}
function _toast(m,ok){alert((ok?'✓ ':'⚠ ')+m);}

function switchPane(p){
  document.querySelectorAll('.pane').forEach(function(el){el.classList.toggle('on', el.id==='pane-'+p);});
  document.querySelectorAll('.tabbtn').forEach(function(b){b.classList.toggle('on', b.dataset.pane===p);});
  if(p==='maq') cargarMaquila();
  if(p==='eos') cargarEosLeads();
  if(p==='correo') cargarLeadsCorreo();
}

// ── MAQUILA ────────────────────────────────────────────────
async function cargarMaquila(){
  try{
    var r = await fetch('/api/comercial/maquila');
    var d = await r.json();
    document.getElementById('maq-valor').textContent = _fmtCOP(d.valor_pipeline_cop || 0);
    var stages = ['consulta','nda','brief','cotizacion','contrato','produccion','ganado','perdido'];
    var labels = {consulta:'1 · Consulta',nda:'2 · NDA',brief:'3 · Brief',cotizacion:'4 · Cotización',contrato:'5 · Contrato',produccion:'6 · Producción',ganado:'✓ Ganado',perdido:'✗ Perdido'};
    var box = document.getElementById('maq-kanban');
    box.innerHTML = stages.map(function(st){
      var deals = (d.grupos||{})[st] || [];
      var totalV = deals.reduce(function(s,x){return s + (x.valor_estimado_cop||0);}, 0);
      var html = '<div class="kcol">' +
        '<div class="kcol-h"><span>'+labels[st]+' ('+deals.length+')</span><span>'+_fmtCOP(totalV)+'</span></div>';
      if(!deals.length){
        html += '<div style="padding:12px;text-align:center;color:var(--cx-text-faint);font-size:11px">-</div>';
      } else {
        html += deals.map(function(deal){
          return '<div class="kcard" onclick="editarMaquila('+deal.id+')">' +
            '<b>'+_esc(deal.empresa)+'</b>' +
            (deal.contacto_nombre?'<div style="color:var(--cx-text-mute)">'+_esc(deal.contacto_nombre)+'</div>':'') +
            (deal.valor_estimado_cop>0?'<div class="v">'+_fmtCOP(deal.valor_estimado_cop)+'</div>':'') +
            (deal.notas?'<div style="font-size:11px;color:var(--cx-text-mute);margin-top:4px;line-height:1.3">'+_esc((deal.notas||'').substring(0,100))+'</div>':'') +
            '<div class="meta">Owner: '+_esc(deal.owner||'-')+'</div>' +
          '</div>';
        }).join('');
      }
      html += '</div>';
      return html;
    }).join('');
  }catch(e){ document.getElementById('maq-kanban').innerHTML = '<div class="empty">Error</div>'; }
}

function abrirModalMaquila(){
  document.getElementById('maq-modal-title').textContent = 'Nuevo deal';
  ['mq-id','mq-empresa','mq-contacto','mq-email','mq-tel','mq-origen','mq-prod','mq-notas','mq-cierre'].forEach(function(id){document.getElementById(id).value='';});
  document.getElementById('mq-stage').value = 'consulta';
  document.getElementById('mq-valor').value = 0;
  document.getElementById('mq-volumen').value = 0;
  document.getElementById('modal-maq').style.display = 'flex';
}

async function editarMaquila(id){
  try{
    var r = await fetch('/api/comercial/maquila');
    var d = await r.json();
    var deal = (d.maquila||[]).find(function(x){return x.id===id;});
    if(!deal){ _toast('No encontrado',0); return; }
    document.getElementById('maq-modal-title').textContent = 'Editar: '+deal.empresa;
    document.getElementById('mq-id').value = deal.id;
    document.getElementById('mq-empresa').value = deal.empresa || '';
    document.getElementById('mq-contacto').value = deal.contacto_nombre || '';
    document.getElementById('mq-email').value = deal.contacto_email || '';
    document.getElementById('mq-tel').value = deal.contacto_telefono || '';
    document.getElementById('mq-origen').value = deal.origen || '';
    document.getElementById('mq-stage').value = deal.stage || 'consulta';
    document.getElementById('mq-valor').value = deal.valor_estimado_cop || 0;
    document.getElementById('mq-volumen').value = deal.volumen_estimado_unds || 0;
    document.getElementById('mq-prod').value = deal.producto_descripcion || '';
    document.getElementById('mq-notas').value = deal.notas || '';
    document.getElementById('mq-cierre').value = deal.fecha_cierre_estimada || '';
    document.getElementById('modal-maq').style.display = 'flex';
  }catch(e){}
}

async function guardarMaquila(){
  var id = document.getElementById('mq-id').value;
  var body = {
    empresa: document.getElementById('mq-empresa').value.trim(),
    contacto_nombre: document.getElementById('mq-contacto').value,
    contacto_email: document.getElementById('mq-email').value,
    contacto_telefono: document.getElementById('mq-tel').value,
    origen: document.getElementById('mq-origen').value,
    stage: document.getElementById('mq-stage').value,
    valor_estimado_cop: parseFloat(document.getElementById('mq-valor').value) || 0,
    volumen_estimado_unds: parseInt(document.getElementById('mq-volumen').value) || 0,
    producto_descripcion: document.getElementById('mq-prod').value,
    notas: document.getElementById('mq-notas').value,
    fecha_cierre_estimada: document.getElementById('mq-cierre').value || null,
  };
  if(!body.empresa){ _toast('Empresa requerida',0); return; }
  try{
    var url = id ? '/api/comercial/maquila/'+id : '/api/comercial/maquila';
    var method = id ? 'PATCH' : 'POST';
    var r = await fetch(url, {method:method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if(d.ok){ _toast(id?'Actualizado':'Creado',1); document.getElementById('modal-maq').style.display='none'; cargarMaquila(); }
    else _toast('Error: '+(d.error||'?'),0);
  }catch(e){ _toast('Error de red',0); }
}

// ── EOS LEADS ────────────────────────────────────────────────
async function cargarEosLeads(){
  var estado = document.getElementById('eos-filtro').value;
  try{
    var r = await fetch('/api/eos/leads'+(estado?'?estado='+estado:''));
    var d = await r.json();
    var box = document.getElementById('eos-list');
    if(!d.leads.length){ box.innerHTML = '<div class="empty">Sin leads aún. Cuando lleguen via webhook /api/eos/leads/webhook aparecerán aquí.</div>'; return; }
    box.innerHTML = d.leads.map(function(l){
      var color = {nuevo:'#dc2626',contactado:'#d97706',demo_agendada:'#7c3aed',propuesta:'#6d28d9',cerrado:'#16a34a',descartado:'#94a3b8'}[l.estado] || '#64748b';
      return '<div class="card" style="background:var(--cx-card);border:1px solid var(--cx-border);border-radius:10px;padding:14px;margin-bottom:10px;border-left:4px solid '+color+'">' +
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">' +
          '<div><b>'+_esc(l.nombre || l.email || '(sin nombre)')+'</b>' +
            (l.empresa?' · <span style="color:var(--cx-text-mute)">'+_esc(l.empresa)+'</span>':'')+
            ' <span style="background:'+color+';color:#fff;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase;margin-left:6px">'+l.estado+'</span></div>' +
          '<span style="font-size:11px;color:var(--cx-text-faint)">'+_esc((l.creado_en||'').slice(0,16))+'</span>' +
        '</div>' +
        '<div style="font-size:12px;color:var(--cx-text-soft);margin-top:4px">' +
          (l.email?'📧 <a href="mailto:'+_esc(l.email)+'" style="color:var(--cx-primary-text)">'+_esc(l.email)+'</a>':'') +
          (l.telefono?' · 📞 '+_esc(l.telefono):'') +
        '</div>' +
        (l.mensaje?'<div style="font-size:13px;color:var(--cx-text-soft);margin-top:6px;background:var(--cx-bg-alt);padding:8px 10px;border-radius:6px">'+_esc(l.mensaje)+'</div>':'') +
        '<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">' +
          (l.estado==='nuevo'?'<button class="btn btn-success btn-sm" onclick="cambiarEstadoLead('+l.id+',\'contactado\')">Marqué contacto</button>':'') +
          (l.estado!=='cerrado' && l.estado!=='descartado' ?'<button class="btn btn-secondary btn-sm" onclick="cambiarEstadoLead('+l.id+',\'demo_agendada\')">Demo agendada</button><button class="btn btn-secondary btn-sm" onclick="cambiarEstadoLead('+l.id+',\'propuesta\')">Propuesta</button><button class="btn btn-success btn-sm" onclick="cambiarEstadoLead('+l.id+',\'cerrado\')">Cerrado</button><button class="btn btn-danger btn-sm" onclick="cambiarEstadoLead('+l.id+',\'descartado\')">Descartar</button>':'') +
        '</div>' +
        '</div>';
    }).join('');
  }catch(e){ document.getElementById('eos-list').innerHTML = '<div class="empty">Error</div>'; }
}

async function cambiarEstadoLead(id, nuevo){
  try{
    var r = await fetch('/api/eos/leads/'+id, _fetchOpts('PATCH', {estado: nuevo}));
    var d = await r.json();
    if(r.ok && d.ok){ cargarEosLeads(); }
    else { alert('No se pudo cambiar el estado: '+((d&&d.error)||('HTTP '+r.status))); }
  }catch(e){ alert('Error de red: '+e.message); }
}

// ── CORREO DE DIRECCION ───────────────────────────────────
// Lo que evita que se pierdan: la bandeja se mira desde ac&aacute;, no desde la memoria de alguien.
async function cargarLeadsCorreo(){
  var cont=document.getElementById('correo-list');
  try{
    var d=await (await fetch('/api/comercial/leads-correo',{credentials:'same-origin'})).json();
    var est=document.getElementById('correo-estado');
    // Una lista vacia tiene que decir si esta vacia porque no llego nada o porque no se pudo
    // leer: ese cero se lee como "no hay nada que hacer" y significa lo contrario.
    est.innerHTML = d.buzon_configurado
      ? '<div style="background:var(--cx-success-pale,#f0fdf4);color:var(--cx-success-text,#15803d);border:1px solid var(--cx-success-soft,#bbf7d0);border-radius:10px;padding:9px 13px;font-size:12px;font-weight:700">&#9989; Buz&oacute;n conectado &middot; se lee solo a las 7:20 y 15:20</div>'
      : '<div style="background:var(--cx-warn-pale,#fef3c7);color:var(--cx-warn-text,#92400e);border:1px solid var(--cx-warn-soft,#fde68a);border-radius:10px;padding:9px 13px;font-size:12px;font-weight:700">&#9888; '+_esc(d.aviso||'buz&oacute;n sin configurar')+'</div>';
    var L=d.leads||[]; window._LEADS=L;
    if(!L.length){ cont.innerHTML='<div style="color:var(--cx-text-faint);padding:22px;text-align:center">'+(d.buzon_configurado?'No hay correos nuevos.':'Todav&iacute;a no se ley&oacute; el buz&oacute;n.')+'</div>'; return; }
    var h='<div style="display:flex;flex-direction:column;gap:9px">';
    L.forEach(function(x){
      var ya=x.pipeline_id, des=x.descartado;
      var borde = des ? 'var(--cx-border,#e2e8f0)' : (ya ? 'var(--cx-success,#16a34a)' : 'var(--cx-warn,#f59e0b)');
      h+='<div style="background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#f1f5f9);border-left:4px solid '+borde+';border-radius:12px;padding:12px 14px;'+(des?'opacity:.55':'')+'">'
        +'<div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:flex-start">'
        +'<div style="flex:1;min-width:240px">'
        +'<div style="font-weight:800;font-size:14px;color:var(--cx-text,#0f172a)">'+_esc(x.empresa||'sin identificar')
        // Lo inferido se dice: un nombre propio leido como razon social ensucia todo lo que siga.
        +(x.empresa_inferida?'<span style="margin-left:6px;font-size:9.5px;font-weight:800;background:var(--cx-warn-pale,#fef3c7);color:var(--cx-warn-text,#92400e);border-radius:999px;padding:2px 8px">nombre del contacto, no razon social</span>':'')
        +'</div>'
        +'<div style="font-size:12px;color:var(--cx-text-soft,#475569);margin-top:3px">'+_esc(x.asunto||'')+'</div>'
        +'<div style="font-size:11px;color:var(--cx-text-mute,#64748b);margin-top:4px">'+_esc(x.remitente||'')+' &middot; '+_esc(String(x.fecha_correo||'').slice(0,16))+'</div>'
        +((x.contacto||x.telefono||x.producto)?('<div style="font-size:11.5px;color:var(--cx-text-soft,#475569);margin-top:5px">'+[x.contacto,x.telefono,x.producto].filter(Boolean).map(_esc).join(' &middot; ')+'</div>'):'')
        +'</div>'
        +'<div style="display:flex;gap:7px;align-items:center;white-space:nowrap">'
        +(des?('<span style="font-size:11px;font-weight:700;color:var(--cx-text-mute,#64748b)">descartado</span>')
           : ya?('<a href="#" onclick="switchPane(\'maq\');return false" style="font-size:11.5px;font-weight:700;color:var(--cx-success-text,#15803d);text-decoration:none">&#10003; ya est&aacute; en el pipeline</a>')
           : ('<button class="btn btn-primary" style="padding:6px 12px;font-size:12px" onclick="leadAlPipeline('+x.id+')">&rarr; Al pipeline</button>'
             +'<button class="btn" style="padding:6px 12px;font-size:12px" onclick="leadDescartar('+x.id+')">Descartar</button>'
             +'<button class="btn" style="padding:6px 10px;font-size:11.5px" title="Descarta todo lo pendiente de este remitente" onclick="descartarRemitente('+x.id+')">y todos los de este remitente</button>'))
        +'</div></div>'
        +(x.cuerpo?('<details style="margin-top:8px"><summary style="cursor:pointer;font-size:11px;color:var(--cx-text-mute,#64748b);font-weight:700">ver el correo como lleg&oacute;</summary><pre style="white-space:pre-wrap;font-size:11px;color:var(--cx-text-soft,#475569);background:var(--cx-border-soft,#f8fafc);border-radius:8px;padding:9px;margin-top:6px;max-height:220px;overflow:auto">'+_esc(x.cuerpo)+'</pre></details>'):'')
        +'</div>';
    });
    cont.innerHTML=h+'</div>';
  }catch(e){ cont.innerHTML='<div style="color:var(--cx-danger-text,#b91c1c);padding:18px">No pude cargar: '+_esc(e.message)+'</div>'; }
}

async function leerBuzon(){
  var b=document.getElementById('btn-leer-buzon');
  if(b&&b.disabled) return; if(b){b.disabled=true;b.textContent='Leyendo\u2026';}
  try{
    var r=await fetch('/api/comercial/leads-correo/leer', _fetchOpts('POST',{}));
    var d=await r.json();
    if(!r.ok){ _toast((d&&(d.como||d.error))||('HTTP '+r.status), false); return; }
    // ⚠ Refrescar ANTES de avisar. El alert BLOQUEA, asi que avisando primero el cartel dice
    // "40 nuevos" mientras la lista de atras sigue diciendo "no hay correos nuevos" -- y dos
    // partes de la misma pantalla contradiciendose hacen que se deje de creer en las dos (M161).
    await cargarLeadsCorreo();
    var est=document.getElementById('correo-estado');
    if(est){
      est.insertAdjacentHTML('beforeend','<div style="margin-top:8px;background:var(--cx-primary-pale,#f5f3ff);color:var(--cx-primary-text,#5b21b6);border:1px solid var(--cx-primary-soft,#ddd6fe);border-radius:10px;padding:9px 13px;font-size:12px;font-weight:700">'
        +(d.nuevos? ('&#128229; '+d.nuevos+' prospecto(s) nuevo(s) en esta lectura')
                  : '&#128229; Sin correos nuevos &middot; los que ya estaban no se vuelven a traer')
        +' &middot; revisados '+((d.detalle&&d.detalle.vistos)||0)+' en '+((d.detalle&&d.detalle.segundos)||0)+'s</div>');
    }
  }catch(e){ _toast('Error de red: '+e.message,false); }
  finally{ if(b){b.disabled=false;b.innerHTML='&#128229; Leer ahora';} }
}

async function leadAlPipeline(id){
  // Si la empresa la INFERIMOS (el formulario la trajo en blanco o escrita "Por definir"), se
  // pregunta en vez de abrir una tarjeta con nombre de persona: ese rotulo despues se lee como
  // razon social y ensucia todo lo que venga.
  var lead=(window._LEADS||[]).filter(function(x){return x.id===id;})[0];
  var body={};
  if(lead && lead.empresa_inferida){
    var e=prompt('El formulario no trajo el nombre de la empresa. Escribilo, o dejalo asi para usar el nombre del contacto:', lead.empresa||'');
    if(e===null) return;
    if(e.trim()) body.empresa=e.trim();
  }
  try{
    var r=await fetch('/api/comercial/leads-correo/'+id+'/al-pipeline', _fetchOpts('POST',body));
    var d=await r.json();
    if(!r.ok){ _toast((d&&d.error)||('HTTP '+r.status), false); return; }
    _toast(d.nueva_tarjeta? ('Abierta la tarjeta de '+d.empresa) : ('Se sum&oacute; a la tarjeta que ya exist&iacute;a'), true);
    cargarLeadsCorreo();
  }catch(e){ _toast('Error de red: '+e.message,false); }
}

function _correoDe(txt){
  var m=String(txt||'').match(/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/);
  return m? m[0] : '';
}

async function descartarRemitente(id){
  // El barrido va por REMITENTE, que es un hecho del mensaje. Un filtro por palabras del asunto
  // botaria el "cotizacion de maquila" con redaccion rara, y perder un cliente es mucho peor que
  // dejar pasar publicidad.
  var lead=(window._LEADS||[]).filter(function(x){return x.id===id;})[0];
  var correo=_correoDe(lead&&lead.remitente);
  if(!correo){ _toast('No pude leer el correo del remitente', false); return; }
  var n=(window._LEADS||[]).filter(function(x){
    return !x.descartado && !x.pipeline_id && String(x.remitente||'').toLowerCase().indexOf(correo.toLowerCase())>=0;
  }).length;
  var m=prompt('Descarto '+n+' correo(s) pendientes de '+correo+'. Queda registrado y se puede recuperar. Motivo:','no es un prospecto');
  if(m===null) return;
  try{
    var r=await fetch('/api/comercial/leads-correo/descartar-remitente', _fetchOpts('POST',{correo:correo, motivo:m}));
    var d=await r.json();
    if(!r.ok){ _toast((d&&d.error)||('HTTP '+r.status), false); return; }
    await cargarLeadsCorreo();
    _toast('Descartados '+d.descartados+' de '+correo, true);
  }catch(e){ _toast('Error de red: '+e.message,false); }
}

async function leadDescartar(id){
  // Se conserva con su motivo: un filtro que bota sin dejar rastro no es confiable.
  var m=prompt('&#191;Por qu&eacute; no es un prospecto? (queda registrado y se puede recuperar)','publicidad');
  if(m===null) return;
  try{
    var r=await fetch('/api/comercial/leads-correo/'+id+'/al-pipeline', _fetchOpts('POST',{descartar:true, motivo:m}));
    var d=await r.json();
    if(!r.ok){ _toast((d&&d.error)||('HTTP '+r.status), false); return; }
    cargarLeadsCorreo();
  }catch(e){ _toast('Error de red: '+e.message,false); }
}

// init
cargarMaquila();
</script>
</body>
</html>
"""
