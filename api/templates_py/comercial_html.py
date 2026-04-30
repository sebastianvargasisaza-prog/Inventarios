"""Template Comercial — Pipeline Maquila + EOS Leads."""

HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Comercial · HHA Group</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos11">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#f5f4f2;color:#1c1917;font-size:14px}
.topbar{background:linear-gradient(90deg,#581c87,#7c3aed);color:#fff;padding:14px 20px;display:flex;align-items:center;gap:14px}
.topbar h1{font-size:18px;font-weight:700;flex:1}
.topbar a{color:#cbd5e1;text-decoration:none;font-size:13px;padding:6px 12px;border-radius:6px;background:rgba(255,255,255,.1)}
.tabs{background:#fff;border-bottom:2px solid #e2e8f0;display:flex;gap:0}
.tabbtn{padding:12px 22px;font-size:13px;font-weight:600;color:#64748b;background:none;border:none;cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-2px}
.tabbtn:hover{background:#f8fafc;color:#7c3aed}
.tabbtn.on{color:#7c3aed;border-bottom-color:#7c3aed;font-weight:700}
.pane{display:none;padding:22px 24px;max-width:1400px;margin:0 auto}
.pane.on{display:block}
.btn{padding:7px 14px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer}
.btn-primary{background:#7c3aed;color:#fff}.btn-primary:hover{background:#6d28d9}
.btn-secondary{background:#e2e8f0;color:#475569}
.btn-success{background:#16a34a;color:#fff}
.btn-danger{background:#dc2626;color:#fff}
.btn-sm{padding:4px 8px;font-size:11px}
input,select,textarea{padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;font-family:inherit;width:100%}
input:focus,select:focus,textarea:focus{border-color:#7c3aed;outline:none}
.row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.row > * {flex:1;min-width:180px}
label{font-size:12px;font-weight:600;color:#475569;display:block;margin-bottom:4px}
.empty{text-align:center;color:#94a3b8;padding:30px;font-style:italic}
/* Kanban styles */
.kanban{display:flex;gap:12px;overflow-x:auto;padding:4px;align-items:flex-start}
.kcol{min-width:240px;background:#f1f5f9;border-radius:10px;padding:8px}
.kcol-h{font-size:11px;text-transform:uppercase;letter-spacing:.5px;font-weight:700;color:#475569;padding:4px 8px;display:flex;justify-content:space-between;align-items:center}
.kcard{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:10px;margin-top:8px;font-size:12px;cursor:pointer;transition:all .15s}
.kcard:hover{box-shadow:0 4px 12px rgba(0,0,0,.08);border-color:#7c3aed}
.kcard b{display:block;color:#0f172a;font-size:13px;margin-bottom:4px}
.kcard .meta{font-size:10px;color:#64748b;margin-top:6px}
.kcard .v{font-weight:700;color:#16a34a;font-size:12px}
.b-stage-consulta{background:#e2e8f0;color:#475569}
.b-stage-nda{background:#dbeafe;color:#1e40af}
.b-stage-brief{background:#e0e7ff;color:#3730a3}
.b-stage-cotizacion{background:#fef3c7;color:#92400e}
.b-stage-contrato{background:#fed7aa;color:#9a3412}
.b-stage-produccion{background:#d1fae5;color:#065f46}
.b-stage-ganado{background:#16a34a;color:#fff}
.b-stage-perdido{background:#fee2e2;color:#991b1b}
</style>
</head>
<body>
<div class="topbar">
  <h1>💼 Comercial · HHA Group</h1>
  <a href="/modulos">← Módulos</a>
</div>

<div class="tabs">
  <button class="tabbtn on" data-pane="maq" onclick="switchPane('maq')">🏭 Pipeline Maquila B2B</button>
  <button class="tabbtn" data-pane="eos" onclick="switchPane('eos')">🚀 EOS Leads</button>
</div>

<!-- PANE: Maquila -->
<div id="pane-maq" class="pane on">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;flex-wrap:wrap;gap:8px">
    <h3 style="color:#581c87">Pipeline Maquila Full Service</h3>
    <div style="display:flex;align-items:center;gap:10px">
      <span style="font-size:12px;color:#64748b">Pipeline activo: <b id="maq-valor" style="color:#16a34a">$0</b></span>
      <button class="btn btn-primary" onclick="abrirModalMaquila()">+ Nuevo deal</button>
    </div>
  </div>
  <div id="maq-kanban" class="kanban"></div>
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
  <div style="background:#fef3c7;border-left:4px solid #d97706;padding:12px 16px;margin-bottom:16px;border-radius:0 6px 6px 0;font-size:13px">
    <b>📥 Webhook activo:</b> <code style="background:#fff;padding:2px 6px;border-radius:4px;font-size:11px">POST /api/eos/leads/webhook</code>
    — configura web3forms o cualquier form para enviar aquí. Llega notif in-app automática.
  </div>
  <div id="eos-list"></div>
</div>

<!-- MODAL: Nuevo deal maquila -->
<div id="modal-maq" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.7);z-index:9999;align-items:center;justify-content:center;padding:20px">
  <div style="background:#fff;border-radius:14px;padding:22px 26px;max-width:520px;width:100%;max-height:90vh;overflow-y:auto">
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
function _esc(s){return (s==null?'':String(s)).replace(/[<>&"']/g,function(c){return {'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c];});}
function _fmtCOP(n){if(n==null||n===0) return '—'; return '$'+Math.round(n).toLocaleString('es-CO');}
function _toast(m,ok){alert((ok?'✓ ':'⚠ ')+m);}

function switchPane(p){
  document.querySelectorAll('.pane').forEach(function(el){el.classList.toggle('on', el.id==='pane-'+p);});
  document.querySelectorAll('.tabbtn').forEach(function(b){b.classList.toggle('on', b.dataset.pane===p);});
  if(p==='maq') cargarMaquila();
  if(p==='eos') cargarEosLeads();
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
        html += '<div style="padding:12px;text-align:center;color:#94a3b8;font-size:11px">—</div>';
      } else {
        html += deals.map(function(deal){
          return '<div class="kcard" onclick="editarMaquila('+deal.id+')">' +
            '<b>'+_esc(deal.empresa)+'</b>' +
            (deal.contacto_nombre?'<div style="color:#64748b">'+_esc(deal.contacto_nombre)+'</div>':'') +
            (deal.valor_estimado_cop>0?'<div class="v">'+_fmtCOP(deal.valor_estimado_cop)+'</div>':'') +
            (deal.notas?'<div style="font-size:11px;color:#64748b;margin-top:4px;line-height:1.3">'+_esc((deal.notas||'').substring(0,100))+'</div>':'') +
            '<div class="meta">Owner: '+_esc(deal.owner||'—')+'</div>' +
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
      var color = {nuevo:'#dc2626',contactado:'#d97706',demo_agendada:'#7c3aed',propuesta:'#0f766e',cerrado:'#16a34a',descartado:'#94a3b8'}[l.estado] || '#64748b';
      return '<div class="card" style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px;margin-bottom:10px;border-left:4px solid '+color+'">' +
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">' +
          '<div><b>'+_esc(l.nombre || l.email || '(sin nombre)')+'</b>' +
            (l.empresa?' · <span style="color:#64748b">'+_esc(l.empresa)+'</span>':'')+
            ' <span style="background:'+color+';color:#fff;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase;margin-left:6px">'+l.estado+'</span></div>' +
          '<span style="font-size:11px;color:#94a3b8">'+_esc((l.creado_en||'').slice(0,16))+'</span>' +
        '</div>' +
        '<div style="font-size:12px;color:#475569;margin-top:4px">' +
          (l.email?'📧 <a href="mailto:'+_esc(l.email)+'" style="color:#0f766e">'+_esc(l.email)+'</a>':'') +
          (l.telefono?' · 📞 '+_esc(l.telefono):'') +
        '</div>' +
        (l.mensaje?'<div style="font-size:13px;color:#475569;margin-top:6px;background:#f8fafc;padding:8px 10px;border-radius:6px">'+_esc(l.mensaje)+'</div>':'') +
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
    var r = await fetch('/api/eos/leads/'+id, {method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({estado: nuevo})});
    if((await r.json()).ok){ cargarEosLeads(); }
  }catch(e){}
}

// init
cargarMaquila();
</script>
</body>
</html>
"""
