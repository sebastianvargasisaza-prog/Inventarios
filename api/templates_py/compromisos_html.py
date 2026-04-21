# Auto-extraído de index.py — Fase A refactor
COMPROMISOS_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Compromisos — HHA Group</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#f5f4f2;color:#1C1917;font-size:14px;}
.topbar{background:#1e293b;color:#fff;padding:12px 20px;display:flex;align-items:center;gap:16px;}
.topbar h1{font-size:17px;font-weight:600;}
.tb-right{margin-left:auto;display:flex;gap:12px;font-size:13px;}
.tb-right a{color:#94a3b8;text-decoration:none;}
.tb-right a:hover{color:#fff;}
.content{padding:20px;max-width:1200px;margin:0 auto;}
.filter-bar{background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:12px 16px;margin-bottom:16px;display:flex;gap:10px;flex-wrap:wrap;align-items:center;}
.filter-bar select,.filter-bar input{padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;}
.stats-row{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;}
.stat-pill{padding:6px 14px;border-radius:20px;font-size:12px;font-weight:600;}
.sp-crit{background:#fee2e2;color:#991b1b;}
.sp-alta{background:#fef3c7;color:#92400e;}
.sp-pend{background:#dbeafe;color:#1e40af;}
.sp-done{background:#dcfce7;color:#166534;}
.comp-list{display:flex;flex-direction:column;gap:10px;}
.comp-card{background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:14px 16px;display:flex;align-items:flex-start;gap:12px;}
.comp-card:hover{border-color:#a8a29e;}
.comp-card.crit{border-left:4px solid #dc2626;}
.comp-card.alta{border-left:4px solid #d97706;}
.comp-card.norm{border-left:4px solid #3b82f6;}
.comp-card.done{border-left:4px solid #16a34a;opacity:.7;}
.comp-check{flex-shrink:0;width:22px;height:22px;border-radius:50%;border:2px solid #d6d3d1;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:13px;margin-top:2px;}
.comp-check.done{background:#16a34a;border-color:#16a34a;color:#fff;}
.comp-body{flex:1;}
.comp-desc{font-size:14px;font-weight:600;color:#1C1917;margin-bottom:4px;}
.comp-card.done .comp-desc{text-decoration:line-through;color:#78716c;}
.comp-meta{display:flex;gap:12px;flex-wrap:wrap;font-size:11px;color:#78716c;margin-bottom:4px;}
.badge-prior{display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;font-weight:700;}
.pr-c{background:#fee2e2;color:#991b1b;}
.pr-a{background:#fef3c7;color:#92400e;}
.pr-n{background:#f3f4f6;color:#6b7280;}
.pr-b{background:#f0fdf4;color:#166534;}
.est-badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;font-weight:600;}
.est-pend{background:#dbeafe;color:#1e40af;}
.est-proc{background:#fef3c7;color:#92400e;}
.est-comp{background:#dcfce7;color:#166534;}
.est-canc{background:#f3f4f6;color:#6b7280;}
.vencido-tag{color:#dc2626;font-weight:700;font-size:10px;}
.comp-actions{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;}
.btn{padding:5px 12px;border-radius:6px;font-size:11px;font-weight:600;border:none;cursor:pointer;}
.btn-prim{background:#1e293b;color:#fff;}
.btn-succ{background:#16a34a;color:#fff;}
.btn-warn{background:#d97706;color:#fff;}
.btn-outl{background:#fff;color:#374151;border:1px solid #d6d3d1;}
.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1000;display:flex;align-items:center;justify-content:center;padding:16px;}
.modal{background:#fff;border-radius:10px;width:100%;max-width:540px;box-shadow:0 20px 60px rgba(0,0,0,.3);}
.mh{padding:16px 20px;border-bottom:1px solid #e7e5e4;display:flex;align-items:center;justify-content:space-between;}
.mh h3{font-size:15px;font-weight:700;}
.mc{padding:20px;display:flex;flex-direction:column;gap:12px;}
.mf{padding:12px 20px;border-top:1px solid #e7e5e4;display:flex;gap:8px;justify-content:flex-end;}
.fg label{display:block;font-size:11px;font-weight:600;color:#44403c;margin-bottom:4px;}
.fg input,.fg select,.fg textarea{width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
.fab{position:fixed;bottom:20px;right:20px;background:#1e293b;color:#fff;border:none;width:50px;height:50px;border-radius:50%;font-size:22px;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.3);display:flex;align-items:center;justify-content:center;}
.hidden{display:none;}
.empty{text-align:center;padding:40px;color:#78716c;}
</style>
</head>
<body>
<div class="topbar">
  <h1>&#x1F4CB; Compromisos — HHA Group</h1>
  <div class="tb-right">
    <a href="/modulos" style="font-weight:700;">&#x1F4F1; M&#xF3;dulos</a>
    <a href="/gerencia">Gerencia</a>
  </div>
</div>
<div class="content">
  <div class="filter-bar">
    <select id="f-estado" onchange="load()">
      <option value="Todos">Todos los estados</option>
      <option value="Pendiente" selected>Pendiente</option>
      <option value="En Proceso">En Proceso</option>
      <option value="Completado">Completado</option>
    </select>
    <select id="f-empresa" onchange="load()">
      <option value="">Ambas empresas</option>
      <option value="Espagiria">Espagiria</option>
      <option value="ANIMUS">ANIMUS Lab</option>
    </select>
    <input id="f-q" type="text" placeholder="Buscar..." oninput="render()" style="min-width:180px;">
    <button class="btn btn-prim" onclick="abrirModal()">+ Nuevo Compromiso</button>
  </div>
  <div id="stats" class="stats-row"></div>
  <div id="list" class="comp-list"><div class="empty">Cargando...</div></div>
</div>

<button class="fab" onclick="abrirModal()">+</button>

<div id="modal" class="modal-backdrop hidden">
<div class="modal">
  <div class="mh"><h3>Nuevo Compromiso</h3><button onclick="cerrar()" style="background:none;border:none;font-size:18px;cursor:pointer;">&times;</button></div>
  <div class="mc">
    <div class="fg"><label>Descripcion *</label><textarea id="n-desc" rows="2" placeholder="Que se comprometio a hacer..."></textarea></div>
    <div class="grid2">
      <div class="fg"><label>Responsable</label><input id="n-resp" placeholder="Nombre"></div>
      <div class="fg"><label>Area</label><input id="n-area" placeholder="Calidad, Produccion..."></div>
    </div>
    <div class="grid2">
      <div class="fg"><label>Fecha limite</label><input type="date" id="n-fecha"></div>
      <div class="fg"><label>Prioridad</label>
        <select id="n-prior"><option>Normal</option><option>Alta</option><option>Critico</option><option>Baja</option></select>
      </div>
    </div>
    <div class="grid2">
      <div class="fg"><label>Empresa</label>
        <select id="n-emp"><option>Espagiria</option><option>ANIMUS</option><option>HHA Group</option></select>
      </div>
      <div class="fg"><label>Origen (acta/reunion)</label><input id="n-origen" placeholder="ACTA-ESP-..."></div>
    </div>
  </div>
  <div class="mf">
    <button class="btn btn-outl" onclick="cerrar()">Cancelar</button>
    <button class="btn btn-prim" onclick="guardar()">Guardar</button>
  </div>
</div>
</div>

<script>
var _DATA = [];
var hoy = new Date().toISOString().substring(0,10);

function priClass(p){ return p==='Critico'?'crit':p==='Alta'?'alta':'norm'; }
function priBadge(p){ var c={'Critico':'pr-c','Alta':'pr-a','Normal':'pr-n','Baja':'pr-b'}[p]||'pr-n'; return '<span class="badge-prior '+c+'">'+p+'</span>'; }
function estBadge(e){ var c={'Pendiente':'est-pend','En Proceso':'est-proc','Completado':'est-comp','Cancelado':'est-canc'}[e]||'est-pend'; return '<span class="est-badge '+c+'">'+e+'</span>'; }
function esc(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function isVencido(c){ return c.estado!=='Completado'&&c.estado!=='Cancelado'&&c.fecha_limite&&c.fecha_limite<hoy; }

async function load(){
  var estado = document.getElementById('f-estado').value;
  var empresa = document.getElementById('f-empresa').value;
  var url = '/api/compromisos?estado='+encodeURIComponent(estado)+(empresa?'&empresa='+encodeURIComponent(empresa):'');
  var r = await fetch(url);
  var d = await r.json();
  _DATA = d.compromisos||[];
  render();
}

function render(){
  var q = document.getElementById('f-q').value.toLowerCase();
  var filtered = q ? _DATA.filter(function(c){ return (c.descripcion||'').toLowerCase().indexOf(q)>=0||(c.responsable||'').toLowerCase().indexOf(q)>=0; }) : _DATA;
  // Stats
  var crit=filtered.filter(function(c){return c.prioridad==='Critico'&&c.estado!=='Completado';}).length;
  var alta=filtered.filter(function(c){return c.prioridad==='Alta'&&c.estado!=='Completado';}).length;
  var pend=filtered.filter(function(c){return c.estado==='Pendiente'||c.estado==='En Proceso';}).length;
  var done=filtered.filter(function(c){return c.estado==='Completado';}).length;
  var venc=filtered.filter(isVencido).length;
  document.getElementById('stats').innerHTML =
    (crit?'<span class="stat-pill sp-crit">&#x1F534; '+crit+' critico(s)</span>':'')+
    (venc?'<span class="stat-pill sp-crit">&#x23F0; '+venc+' vencido(s)</span>':'')+
    (alta?'<span class="stat-pill sp-alta">&#x1F7E1; '+alta+' alta prioridad</span>':'')+
    '<span class="stat-pill sp-pend">&#x1F535; '+pend+' pendientes</span>'+
    '<span class="stat-pill sp-done">&#x2705; '+done+' completados</span>';
  if(!filtered.length){
    document.getElementById('list').innerHTML='<div class="empty">No hay compromisos con estos filtros</div>';
    return;
  }
  document.getElementById('list').innerHTML = filtered.map(function(c){
    var isDone = c.estado==='Completado';
    var isVenc = isVencido(c);
    var cardCls = isDone?'done':priClass(c.prioridad);
    var checkCls = isDone?'done':'';
    var checkIcon = isDone?'&#x2713;':'';
    return '<div class="comp-card '+cardCls+'">' +
      '<div class="comp-check '+checkCls+'" onclick="toggleDone('+c.id+','+isDone+')">'+checkIcon+'</div>'+
      '<div class="comp-body">'+
        '<div class="comp-desc">'+esc(c.descripcion)+'</div>'+
        '<div class="comp-meta">'+
          priBadge(c.prioridad)+' '+estBadge(c.estado)+
          (c.responsable?'<span>&#x1F464; '+esc(c.responsable)+'</span>':'')+
          (c.area?'<span>&#x1F3E2; '+esc(c.area)+'</span>':'')+
          (c.fecha_limite?'<span>'+(isVenc?'<span class="vencido-tag">VENCIDO </span>':'&#x1F4C5; ')+c.fecha_limite+'</span>':'')+
          (c.empresa?'<span>&#x1F3ED; '+esc(c.empresa)+'</span>':'')+
          (c.origen?'<span>&#x1F4CB; '+esc(c.origen)+'</span>':'')+
        '</div>'+
        (c.notas?'<div style="font-size:11px;color:#78716c;font-style:italic;margin-top:4px;">'+esc(c.notas)+'</div>':'')+
        '<div class="comp-actions">'+
          (!isDone?'<button class="btn btn-succ" onclick="marcar('+c.id+','Completado')">Completado</button>':'') +
          (c.estado==='Pendiente'?'<button class="btn btn-warn" onclick="marcar('+c.id+','En Proceso')">En Proceso</button>':'')+
          '<button class="btn btn-outl" onclick="promptNota('+c.id+')">Nota</button>'+
        '</div>'+
      '</div></div>';
  }).join('');
}

async function toggleDone(id, wasDone){
  var nuevoEstado = wasDone ? 'Pendiente' : 'Completado';
  await fetch('/api/compromisos/'+id, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:nuevoEstado})});
  load();
}
async function marcar(id, estado){
  await fetch('/api/compromisos/'+id, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:estado})});
  load();
}
async function promptNota(id){
  var nota = prompt('Agregar nota:');
  if(!nota) return;
  await fetch('/api/compromisos/'+id, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({notas:nota})});
  load();
}

function abrirModal(){
  ['n-desc','n-resp','n-area','n-origen'].forEach(function(id){document.getElementById(id).value='';});
  document.getElementById('n-prior').value='Normal';
  document.getElementById('n-emp').value='Espagiria';
  document.getElementById('n-fecha').value='';
  document.getElementById('modal').classList.remove('hidden');
}
function cerrar(){document.getElementById('modal').classList.add('hidden');}
async function guardar(){
  var desc=document.getElementById('n-desc').value.trim();
  if(!desc){alert('Descripcion requerida');return;}
  var body={
    descripcion:desc,responsable:document.getElementById('n-resp').value,
    area:document.getElementById('n-area').value,fecha_limite:document.getElementById('n-fecha').value,
    prioridad:document.getElementById('n-prior').value,empresa:document.getElementById('n-emp').value,
    origen:document.getElementById('n-origen').value
  };
  await fetch('/api/compromisos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  cerrar(); load();
}

document.getElementById('modal').addEventListener('click',function(e){if(e.target===this)cerrar();});
load();
</script>
</body>
</html>"""
