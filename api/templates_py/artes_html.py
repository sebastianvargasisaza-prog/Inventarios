ARTES_HTML = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Artes & Etiquetas</title>
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<style>
  body{margin:0;background:var(--cx-bg,#faf9f7);color:var(--cx-text,#1c1917);font-family:Inter,system-ui,-apple-system,sans-serif;}
  .wrap{max-width:1500px;margin:0 auto;padding:18px 22px 60px;}
  .hd{display:flex;align-items:center;gap:14px;margin-bottom:6px;}
  .hd h1{font-size:20px;margin:0;font-weight:800;letter-spacing:-.01em;}
  .hd .sub{color:var(--cx-text-mute,#78716c);font-size:12.5px;}
  .hd .nav{margin-left:auto;display:flex;gap:8px;align-items:center;}
  .btn{appearance:none;border:1px solid var(--cx-hairline,#e7e5e4);background:var(--cx-card,#fff);color:var(--cx-text,#1c1917);border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:6px;}
  .btn:hover{border-color:var(--cx-primary,#6d28d9);color:var(--cx-primary,#6d28d9);}
  .btn.primary{background:var(--cx-primary,#6d28d9);color:#fff;border-color:var(--cx-primary,#6d28d9);}
  .btn.primary:hover{filter:brightness(1.06);color:#fff;}
  .btn.ok{background:#16a34a;color:#fff;border-color:#16a34a;}
  .btn.danger{background:#dc2626;color:#fff;border-color:#dc2626;}
  .btn.sm{padding:5px 10px;font-size:12px;}
  .kpis{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0;}
  .kpi{background:var(--cx-card,#fff);border:1px solid var(--cx-hairline,#e7e5e4);border-radius:12px;padding:12px 18px;min-width:120px;}
  .kpi .n{font-size:24px;font-weight:800;}
  .kpi .l{font-size:11px;color:var(--cx-text-mute,#78716c);text-transform:uppercase;letter-spacing:.05em;margin-top:2px;}
  .bar{background:var(--cx-card,#fff);border:1px solid var(--cx-hairline,#e7e5e4);border-radius:12px;padding:14px 16px;margin-bottom:16px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;}
  .chips{display:flex;gap:6px;flex-wrap:wrap;}
  .chip{border:1px solid #d6d3d1;background:transparent;color:#57534e;border-radius:20px;padding:5px 14px;font-size:12px;font-weight:600;cursor:pointer;}
  .chip.on{background:var(--cx-primary,#6d28d9);color:#fff;border-color:var(--cx-primary,#6d28d9);}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(460px,1fr));gap:14px;}
  .card{background:var(--cx-card,#fff);border:1px solid var(--cx-hairline,#e7e5e4);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;}
  .card .top{padding:14px 16px 10px;}
  .card .pt{font-weight:700;font-size:15px;}
  .card .meta{color:var(--cx-text-mute,#78716c);font-size:12px;margin-top:3px;}
  .card .prev{background:#f5f5f4;border-top:1px solid var(--cx-hairline,#e7e5e4);border-bottom:1px solid var(--cx-hairline,#e7e5e4);height:240px;display:flex;align-items:center;justify-content:center;}
  .card .prev iframe{width:100%;height:100%;border:0;}
  .card .prev .nofile{color:#a8a29e;font-size:13px;text-align:center;padding:20px;}
  .card .acts{padding:12px 16px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;}
  .st{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;padding:3px 9px;border-radius:20px;}
  .st.pendiente_dt{background:#fef3c7;color:#b45309;}
  .st.aprobado{background:#dcfce7;color:#15803d;}
  .st.rechazado{background:#fee2e2;color:#b91c1c;}
  .st.borrador,.st.obsoleto{background:#f5f5f4;color:#78716c;}
  .tag{font-size:11px;color:#78716c;}
  .field{display:flex;flex-direction:column;gap:4px;}
  .field label{font-size:11px;font-weight:600;color:#78716c;text-transform:uppercase;letter-spacing:.04em;}
  input,select,textarea{font-family:inherit;font-size:13px;padding:8px 10px;border:1px solid var(--cx-hairline,#e7e5e4);border-radius:8px;background:var(--cx-card,#fff);color:var(--cx-text,#1c1917);}
  .modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.45);display:none;align-items:center;justify-content:center;z-index:50;}
  .modal{background:var(--cx-card,#fff);border-radius:16px;padding:24px;width:min(440px,92vw);box-shadow:0 20px 60px rgba(0,0,0,.25);}
  .modal h3{margin:0 0 14px;font-size:17px;}
  .modal .row{display:flex;flex-direction:column;gap:10px;}
  .modal .foot{display:flex;gap:8px;justify-content:flex-end;margin-top:18px;}
  .muted{color:#a8a29e;font-size:13px;}
  .empty{text-align:center;color:#a8a29e;padding:40px;font-style:italic;}
  @media(max-width:700px){.grid{grid-template-columns:1fr;}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hd">
    <span style="font-size:26px">🏷️</span>
    <div>
      <h1>Artes &amp; Etiquetas <span class="sub" id="rol-tag"></span></h1>
      <div class="sub">Dirección Técnica revisa e-firma el arte (INCI) &middot; sin aprobación no va a marcación</div>
    </div>
    <div class="nav">
      <a class="btn" id="bib-btn" href="#" target="_blank" rel="noopener" style="display:none">📁 Biblioteca (Drive)</a>
      <button class="btn sm" id="bib-set" onclick="setBiblioteca()" style="display:none">Configurar Drive</button>
      <a class="btn" href="/tecnica">← Técnica</a>
    </div>
  </div>

  <div class="kpis">
    <div class="kpi"><div class="n" id="k-pend" style="color:#b45309">-</div><div class="l">Pendientes DT</div></div>
    <div class="kpi"><div class="n" id="k-aprob" style="color:#15803d">-</div><div class="l">Aprobados</div></div>
    <div class="kpi"><div class="n" id="k-recibir" style="color:#0891b2">-</div><div class="l">Por recibir (2ª mirada)</div></div>
  </div>

  <div class="bar">
    <div class="chips" id="chips"></div>
    <input id="q" placeholder="Buscar producto..." oninput="render()" style="margin-left:auto;min-width:200px">
    <button class="btn primary" id="sol-btn" onclick="abrirSolicitar()" style="display:none">+ Solicitar revisión</button>
  </div>

  <!-- Cola de arte de envases que volvieron de serigrafía (Sebastián 21-jul) -->
  <div id="arte-cola-dt"></div>

  <div class="grid" id="lista"><div class="empty">Cargando...</div></div>
</div>

<!-- Modal: solicitar -->
<div class="modal-bg" id="m-sol">
  <div class="modal">
    <h3>Solicitar revisión a Dirección Técnica</h3>
    <div class="row">
      <div class="field"><label>Producto</label><input id="s-prod" placeholder="Nombre del producto"></div>
      <div class="field"><label>Presentación (opcional)</label><input id="s-pres" placeholder="15ml, 30ml, V15..."></div>
      <div class="field"><label>Tipo</label><select id="s-tipo"><option value="etiqueta">Etiqueta</option><option value="arte">Arte</option><option value="serigrafia">Serigrafía</option><option value="plegadiza">Plegadiza</option><option value="inserto">Inserto</option></select></div>
      <div class="field"><label>Link del arte en Drive</label><input id="s-drive" placeholder="https://drive.google.com/file/d/.../view"></div>
      <div class="field"><label>Nota para DT (opcional)</label><textarea id="s-notas" rows="2" placeholder="Qué revisar, cambios, etc."></textarea></div>
    </div>
    <div class="foot">
      <button class="btn" onclick="cerrar('m-sol')">Cancelar</button>
      <button class="btn primary" onclick="enviarSolicitud()">Solicitar</button>
    </div>
  </div>
</div>

<!-- Modal: e-firma -->
<div class="modal-bg" id="m-firma">
  <div class="modal">
    <h3 id="firma-tit">Firmar</h3>
    <p class="muted" id="firma-desc"></p>
    <div class="row">
      <div class="field" id="firma-inci-wrap" style="display:none">
        <label><input type="checkbox" id="firma-inci" style="width:auto"> Revisé INCI / ingredientes / rotulado</label>
      </div>
      <div class="field" id="firma-motivo-wrap" style="display:none">
        <label>Motivo del rechazo</label><textarea id="firma-motivo" rows="2"></textarea>
      </div>
      <div class="field"><label>Contraseña</label><input id="firma-pass" type="password" autocomplete="off"></div>
      <div class="field"><label>Token MFA (si aplica)</label><input id="firma-totp" inputmode="numeric" autocomplete="off" placeholder="000000"></div>
    </div>
    <div class="foot">
      <button class="btn" onclick="cerrar('m-firma')">Cancelar</button>
      <button class="btn primary" id="firma-go" onclick="ejecutarFirma()">Firmar</button>
    </div>
  </div>
</div>

<script>
var DATA = {artes:[], biblioteca:'', soy_dt:false, puedo_solicitar:false};
var FILTRO = 'pendiente_dt';
var _firmaCtx = null;
function esc(s){return String(s==null?'':s).replace(/[<>&"']/g,function(c){return {'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c];});}
function abrir(id){document.getElementById(id).style.display='flex';}
function cerrar(id){document.getElementById(id).style.display='none';}

function driveEmbed(url){
  if(!url) return null;
  var m = url.match(/\/file\/d\/([^/]+)/) || url.match(/[?&]id=([^&]+)/);
  if(m) return 'https://drive.google.com/file/d/'+m[1]+'/preview';
  return null;
}

// ── Cola de arte de envases que volvieron de serigrafía (Sebastián 21-jul · misma que Calidad) ──
async function loadArteColaDT(){
  var box=document.getElementById('arte-cola-dt'); if(!box) return;
  try{
    var d=await (await fetch('/api/programacion/marcacion-arte-pendiente',{cache:'no-store'})).json();
    var its=(d&&d.items)||[];
    if(!its.length){ box.innerHTML=''; return; }
    var cards=its.map(function(it){
      return '<div style="background:#fff;border:1px solid #ede9f6;border-left:4px solid #7c3aed;border-radius:12px;padding:13px 16px;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:8px">'
        +'<div><div style="font-weight:800;font-size:14px;color:#1e1b2e">'+esc(it.serigrafiado_desc||it.serigrafiado)+'</div>'
        +'<div style="font-size:11.5px;color:#78716c;margin-top:2px">'+esc(it.serigrafiado)+' &middot; '+esc(it.producto||'?')+' &middot; '+esc(it.metodo||'')+' &middot; '+esc(it.proveedor||'')+' &middot; '+esc(it.cantidad||0)+' uds &middot; volvió '+esc(it.fecha_retorno||'')+'</div></div>'
        +'<button onclick="abrirArteChkDT('+it.id+',this)" data-desc="'+esc((it.serigrafiado_desc||it.serigrafiado)+' · '+(it.producto||''))+'" style="background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;border:none;border-radius:9px;padding:9px 15px;font-size:12px;font-weight:800;cursor:pointer;white-space:nowrap">🎨 Revisar arte / liberar</button></div>';
    }).join('');
    box.innerHTML='<div style="background:#fff;border:1px solid #ece9f6;border-radius:14px;padding:16px 18px;margin:16px 0">'
      +'<div style="display:flex;align-items:center;gap:9px;margin-bottom:4px"><span style="font-size:16px">🎨</span><b style="font-size:15px;color:#1e1b2e">Arte de envases por revisar</b><span style="background:#fef3c7;color:#92400e;font-size:10px;font-weight:800;border-radius:999px;padding:2px 9px">'+its.length+'</span></div>'
      +'<div style="font-size:11.5px;color:#78716c;margin-bottom:12px">Envases que volvieron de serigrafía/tampografía · verificá <b>arte, estado y características</b> y liberá.</div>'
      +cards+'</div>';
  }catch(e){ box.innerHTML=''; }
}
function abrirArteChkDT(oid, btn){
  var desc=btn?btn.getAttribute('data-desc'):'';
  var ov=document.getElementById('arte-chk-ov'); if(ov) ov.remove();
  ov=document.createElement('div'); ov.id='arte-chk-ov';
  ov.style.cssText='position:fixed;inset:0;background:rgba(20,18,40,.55);z-index:100000;display:flex;align-items:flex-start;justify-content:center;padding:24px;overflow:auto';
  ov.innerHTML='<div style="background:#fff;border-radius:16px;max-width:540px;width:100%;box-shadow:0 30px 80px -24px rgba(24,24,45,.55);overflow:hidden">'
    +'<div style="background:linear-gradient(120deg,#f5f3ff,#faf5ff,#fff);border-bottom:1px solid #ece9f6;padding:18px 22px;display:flex;justify-content:space-between;align-items:center"><div><div style="font-size:16px;font-weight:800;color:#1e1b2e">🎨 Checklist de arte</div><div style="font-size:11px;color:#8b8b9e;margin-top:2px">'+desc+'</div></div><button onclick="document.getElementById(\'arte-chk-ov\').remove()" style="background:none;border:none;font-size:22px;cursor:pointer;color:#a1a1b0">&times;</button></div>'
    +'<div style="padding:18px 22px">'
    +'<div style="font-size:11px;color:#78716c;margin-bottom:14px">Lo firma <b>Dirección Técnica o Calidad</b>. Si algo no cumple, no liberes y dejá la observación.</div>'
    +'<label style="display:flex;gap:9px;align-items:flex-start;margin-bottom:11px;cursor:pointer"><input type="checkbox" id="ak-arte" style="width:17px;height:17px;margin-top:1px"><span><b>Arte conforme</b> al aprobado por DT <span style="color:#dc2626">*</span></span></label>'
    +'<label style="display:flex;gap:9px;align-items:flex-start;margin-bottom:11px;cursor:pointer"><input type="checkbox" id="ak-estado" style="width:17px;height:17px;margin-top:1px"><span><b>Estado</b> OK (sin daños, limpio) <span style="color:#dc2626">*</span></span></label>'
    +'<label style="display:flex;gap:9px;align-items:flex-start;margin-bottom:11px;cursor:pointer"><input type="checkbox" id="ak-caract" style="width:17px;height:17px;margin-top:1px"><span><b>Características</b> correctas (color, ubicación, impresión) <span style="color:#dc2626">*</span></span></label>'
    +'<label style="display:flex;gap:9px;align-items:flex-start;margin-bottom:13px;cursor:pointer"><input type="checkbox" id="ak-cant" style="width:17px;height:17px;margin-top:1px"><span><b>Cantidad</b> coincide con lo enviado</span></label>'
    +'<textarea id="ak-obs" rows="2" placeholder="Observaciones (opcional)" style="width:100%;padding:9px 11px;border:1px solid #d6d3d1;border-radius:9px;font-size:13px;box-sizing:border-box;resize:vertical"></textarea>'
    +'<div id="ak-msg" style="font-size:12px;margin-top:8px"></div></div>'
    +'<div style="border-top:1px solid #eef2f7;padding:14px 22px;display:flex;justify-content:flex-end;gap:8px"><button onclick="document.getElementById(\'arte-chk-ov\').remove()" style="background:#f1f5f9;color:#475569;border:1px solid #e2e8f0;border-radius:8px;padding:8px 15px;cursor:pointer">Cancelar</button><button onclick="guardarArteChkDT('+oid+')" style="background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;border:none;border-radius:8px;padding:8px 16px;font-weight:800;cursor:pointer">✓ Firmar y liberar</button></div></div>';
  document.body.appendChild(ov);
}
async function guardarArteChkDT(oid){
  var arte=document.getElementById('ak-arte').checked, estado=document.getElementById('ak-estado').checked, caract=document.getElementById('ak-caract').checked, cant=document.getElementById('ak-cant').checked;
  var obs=document.getElementById('ak-obs').value.trim(), msg=document.getElementById('ak-msg');
  if(!(arte&&estado&&caract)){ msg.innerHTML='<span style="color:#dc2626">Arte + estado + características deben estar OK para liberar.</span>'; return; }
  try{
    var t=await csrf();
    var r=await fetch('/api/programacion/marcacion-orden/'+oid+'/liberar-checklist',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':t},credentials:'same-origin',body:JSON.stringify({arte:arte,estado:estado,caracteristicas:caract,cantidad:cant,observaciones:obs})});
    var d=await r.json();
    if(d.ok){ var ov=document.getElementById('arte-chk-ov'); if(ov) ov.remove(); alert('✓ Liberado por '+(d.rol||'')); loadArteColaDT(); }
    else msg.innerHTML='<span style="color:#dc2626">'+esc(d.error||'Error')+'</span>';
  }catch(e){ msg.innerHTML='<span style="color:#dc2626">Error de red</span>'; }
}
async function cargar(){
  loadArteColaDT();
  try{
    var d = await fetch('/api/artes').then(function(r){return r.json();});
    if(d.error){document.getElementById('lista').innerHTML='<div class="empty">'+esc(d.error)+'</div>';return;}
    DATA = d;
    document.getElementById('rol-tag').textContent = d.soy_dt ? '· Dirección Técnica' : '· Compras';
    var r = d.resumen||{};
    document.getElementById('k-pend').textContent = r.pendientes||0;
    document.getElementById('k-aprob').textContent = r.aprobados||0;
    document.getElementById('k-recibir').textContent = r.por_recibir||0;
    var bib = document.getElementById('bib-btn');
    if(d.biblioteca){ bib.href=d.biblioteca; bib.style.display=''; }
    if(d.soy_dt) document.getElementById('bib-set').style.display='';
    if(d.puedo_solicitar) document.getElementById('sol-btn').style.display='';
    pintarChips();
    render();
  }catch(e){ console.error(e); document.getElementById('lista').innerHTML='<div class="empty">Error cargando</div>'; }
}

function pintarChips(){
  var defs=[['pendiente_dt','Pendientes'],['aprobado','Aprobados'],['rechazado','Rechazados'],['','Todos']];
  document.getElementById('chips').innerHTML = defs.map(function(x){
    var on = FILTRO===x[0];
    var n = x[0] ? DATA.artes.filter(function(a){return a.estado===x[0];}).length : DATA.artes.length;
    return '<button class="chip'+(on?' on':'')+'" onclick="FILTRO=\''+x[0]+'\';pintarChips();render()">'+x[1]+' ('+n+')</button>';
  }).join('');
}

function render(){
  var q = (document.getElementById('q').value||'').trim().toUpperCase();
  var lista = DATA.artes.filter(function(a){
    if(FILTRO && a.estado!==FILTRO) return false;
    if(q && (a.producto_nombre||'').toUpperCase().indexOf(q)<0) return false;
    return true;
  });
  var cont = document.getElementById('lista');
  if(!lista.length){ cont.innerHTML='<div class="empty">Sin artes en este filtro</div>'; return; }
  cont.innerHTML = lista.map(function(a){
    var emb = driveEmbed(a.drive_url);
    var prev = emb ? '<iframe src="'+esc(emb)+'" allow="autoplay"></iframe>'
      : (a.drive_url ? '<div class="nofile"><a href="'+esc(a.drive_url)+'" target="_blank" rel="noopener">Abrir arte en Drive →</a></div>'
      : '<div class="nofile">Sin link de Drive</div>');
    var acts = '';
    if(DATA.soy_dt){
      if(a.estado==='pendiente_dt'){
        acts += '<button class="btn ok sm" onclick="pedirFirma('+a.id+',\'aprueba\')">✓ Aprobar arte</button>'
             +  '<button class="btn danger sm" onclick="pedirFirma('+a.id+',\'rechaza\')">✗ Rechazar</button>';
      } else if(a.estado==='aprobado' && !a.fisica_aprobada){
        acts += '<button class="btn ok sm" onclick="pedirFirma('+a.id+',\'libera\')">✓ 2ª mirada (llegó)</button>';
      }
    }
    var extra='';
    if(a.estado==='aprobado'){ extra = '<span class="tag">arte OK: '+esc(a.arte_aprobado_por||'')+(a.inci_revisado?' · INCI ✓':'')+(a.fisica_aprobada?' · física ✓ '+esc(a.fisica_aprobada_por||''):' · falta 2ª mirada')+'</span>'; }
    if(a.estado==='rechazado' && a.rechazo_motivo){ extra='<span class="tag" style="color:#b91c1c">Rechazo: '+esc(a.rechazo_motivo)+'</span>'; }
    if(a.estado==='pendiente_dt'){ extra='<span class="tag">solicitó '+esc(a.solicitado_por||'')+(a.solicitud_notas?' · '+esc(a.solicitud_notas):'')+'</span>'; }
    return '<div class="card">'
      + '<div class="top"><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><span class="pt">'+esc(a.producto_nombre)+'</span><span class="st '+esc(a.estado)+'">'+esc(a.estado.replace("_"," "))+'</span></div>'
      + '<div class="meta">'+esc(a.tipo)+(a.presentacion_codigo?' · '+esc(a.presentacion_codigo):'')+' · v'+a.version+(a.mee_codigo?' · '+esc(a.mee_codigo):'')+'</div></div>'
      + '<div class="prev">'+prev+'</div>'
      + '<div class="acts">'+acts+extra+'</div>'
      + '</div>';
  }).join('');
}

// ── Solicitar ──
function abrirSolicitar(){ ['s-prod','s-pres','s-drive','s-notas'].forEach(function(i){document.getElementById(i).value='';}); abrir('m-sol'); }
async function enviarSolicitud(){
  var prod=(document.getElementById('s-prod').value||'').trim();
  if(!prod){ alert('Producto requerido'); return; }
  var body={producto_nombre:prod, presentacion_codigo:document.getElementById('s-pres').value, tipo:document.getElementById('s-tipo').value, drive_url:document.getElementById('s-drive').value, solicitud_notas:document.getElementById('s-notas').value};
  var t=await csrf();
  var r=await fetch('/api/artes/solicitar',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify(body)});
  var j=await r.json();
  if(r.ok){ cerrar('m-sol'); cargar(); } else { alert('Error: '+(j.error||'')); }
}

// ── e-firma ──
function pedirFirma(id, meaning){
  _firmaCtx = {id:id, meaning:meaning};
  var tit={aprueba:'Aprobar arte (e-firma)',rechaza:'Rechazar arte (e-firma)',libera:'Liberar etiqueta física (e-firma)'}[meaning];
  document.getElementById('firma-tit').textContent = tit;
  document.getElementById('firma-desc').textContent = meaning==='aprueba' ? 'Confirmás que revisaste el arte e ingredientes.' : (meaning==='libera'?'Confirmás que lo impreso coincide con lo aprobado.':'');
  document.getElementById('firma-inci-wrap').style.display = meaning==='aprueba'?'':'none';
  document.getElementById('firma-motivo-wrap').style.display = meaning==='rechaza'?'':'none';
  document.getElementById('firma-inci').checked=false;
  document.getElementById('firma-motivo').value='';
  document.getElementById('firma-pass').value='';
  document.getElementById('firma-totp').value='';
  abrir('m-firma');
}
async function ejecutarFirma(){
  if(!_firmaCtx) return;
  var go=document.getElementById('firma-go'); go.disabled=true;
  try{
    var pass=document.getElementById('firma-pass').value;
    var totp=document.getElementById('firma-totp').value;
    if(!pass){ alert('Contraseña requerida'); go.disabled=false; return; }
    var t=await csrf();
    var ch=await fetch('/api/sign/challenge',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify({password:pass,totp_token:totp})});
    var chj=await ch.json();
    if(!ch.ok){ alert('Firma: '+(chj.error||'credenciales')); go.disabled=false; return; }
    var sg=await fetch('/api/sign',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify({record_table:'artes_etiquetas',record_id:String(_firmaCtx.id),meaning:_firmaCtx.meaning,challenge_token:chj.token})});
    var sgj=await sg.json();
    if(!sg.ok){ alert('Firma: '+(sgj.error||'')); go.disabled=false; return; }
    var sid=sgj.signature_id;
    var ep, body={signature_id:sid};
    if(_firmaCtx.meaning==='aprueba'){ ep='/api/artes/'+_firmaCtx.id+'/aprobar-arte'; body.inci_revisado=document.getElementById('firma-inci').checked; }
    else if(_firmaCtx.meaning==='rechaza'){ ep='/api/artes/'+_firmaCtx.id+'/rechazar'; body.motivo=document.getElementById('firma-motivo').value; }
    else { ep='/api/artes/'+_firmaCtx.id+'/aprobar-fisica'; }
    var ar=await fetch(ep,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify(body)});
    var arj=await ar.json();
    if(ar.ok){ cerrar('m-firma'); cargar(); } else { alert('Error: '+(arj.error||'')); }
  }catch(e){ alert('Error: '+e); }
  go.disabled=false;
}

async function setBiblioteca(){
  var cur=DATA.biblioteca||'';
  var url=prompt('Link de la carpeta de Drive con todos los artes:', cur);
  if(url===null) return;
  var t=await csrf();
  var r=await fetch('/api/artes/biblioteca',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify({url:url.trim()})});
  if(r.ok) cargar(); else alert('Error');
}

async function csrf(){ try{ var r=await fetch('/api/csrf-token',{credentials:'same-origin'}); var j=await r.json(); return j.csrf_token||j.token||''; }catch(e){ return ''; } }

// Embebido en una pestaña (Compras): ocultar el header propio para que se vea como sub-pestaña
if(location.search.indexOf('embed=1')>=0){
  var _hd=document.querySelector('.hd'); if(_hd) _hd.style.display='none';
  var _wr=document.querySelector('.wrap'); if(_wr){ _wr.style.paddingTop='4px'; _wr.style.paddingLeft='6px'; _wr.style.paddingRight='6px'; }
  document.body.style.background='transparent';
}

cargar();
</script>
</body>
</html>
"""
