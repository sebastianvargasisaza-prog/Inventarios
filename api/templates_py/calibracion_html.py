"""Bitácora de calibración de equipos · Aseguramiento (Miguel) · INVIMA.

Sebastián 21-jul-2026: "importante saber CUÁNDO se calibró cada equipo y cuándo vence la
próxima". Vive en Aseguramiento, no en Compras/Recepción (las OCs de calibración son un
cargo administrativo, no una recepción de material).

La página es LECTURA + el registro, que se manda a la ruta canónica que ya existía
(POST /api/calidad/equipos/<codigo>/registrar-evento) para no tener dos escrituras.
"""

CALIBRACION_HTML = r'''<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bitácora de calibración · EOS</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<style>
body{font-family:"Inter",system-ui,-apple-system,Arial,sans-serif;background:var(--cx-bg,#f7f6fb);color:var(--cx-text,#18181b);margin:0;padding:22px 2vw 60px}
.wrap{width:96vw;max-width:1720px;margin:0 auto}
.hero{display:flex;align-items:center;gap:15px;margin-bottom:4px}
.hero .ic{width:50px;height:50px;border-radius:15px;background:linear-gradient(135deg,#7c3aed,#a78bfa);display:flex;align-items:center;justify-content:center;font-size:24px;flex-shrink:0;box-shadow:0 10px 24px -10px rgba(109,40,217,.6)}
.hero h1{margin:0;font-size:23px;letter-spacing:-.02em;font-weight:800}
.hero .who{margin-left:auto;font-size:12px;color:var(--cx-text-mute,#8b8b9e);text-align:right}
.sub{color:var(--cx-text-soft,#64748b);font-size:13.5px;margin:4px 0 18px;max-width:900px;line-height:1.5}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:13px;margin-bottom:18px}
.kpi{background:var(--cx-surface,#fff);border:1px solid var(--cx-border,#ece9f6);border-radius:15px;padding:15px 17px;box-shadow:0 2px 12px rgba(109,40,217,.05);position:relative;overflow:hidden}
.kpi::after{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:#cbd5e1}
.kpi.v::after{background:#16a34a}.kpi.p::after{background:#d97706}.kpi.x::after{background:#dc2626}.kpi.s::after{background:#64748b}
.kpi .n{font-size:29px;font-weight:800;letter-spacing:-.03em;line-height:1.05}
.kpi .l{font-size:11px;color:var(--cx-text-mute,#8b8b9e);text-transform:uppercase;letter-spacing:.05em;font-weight:700;margin-top:3px}
.kpi.v .n{color:#16a34a}.kpi.p .n{color:#d97706}.kpi.x .n{color:#dc2626}
.bar{display:flex;gap:9px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.bar input.q{flex:1;min-width:230px;max-width:420px}
.fchip{border:1px solid var(--cx-border,#e4e2ee);background:var(--cx-surface,#fff);color:var(--cx-text-soft,#64748b);border-radius:22px;padding:7px 15px;font-size:12.5px;font-weight:700;cursor:pointer;transition:.15s}
.fchip:hover{border-color:#a78bfa}
.fchip.on{background:linear-gradient(135deg,#7c3aed,#a78bfa);color:#fff;border-color:transparent;box-shadow:0 6px 16px -8px rgba(109,40,217,.7)}
.panel{background:var(--cx-surface,#fff);border:1px solid var(--cx-border,#ece9f6);border-radius:16px;overflow:hidden;box-shadow:0 2px 14px rgba(109,40,217,.05)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:var(--cx-bg-alt,#f7f6fb);text-align:left;padding:11px 13px;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--cx-text-mute,#78788a);font-weight:800;white-space:nowrap;position:sticky;top:0;z-index:2}
td{padding:11px 13px;border-top:1px solid var(--cx-border,#f1f0f7);vertical-align:middle}
tbody tr:hover{background:rgba(124,58,237,.045)}
.eq{font-weight:800}
.eqsub{font-size:11px;color:var(--cx-text-mute,#8b8b9e);margin-top:2px}
code{background:var(--cx-bg-alt,#f1f5f9);padding:1px 6px;border-radius:5px;font-size:11.5px}
.chip{display:inline-block;padding:4px 11px;border-radius:20px;font-size:11px;font-weight:800;white-space:nowrap}
.c-vigente{background:#dcfce7;color:#15803d}
.c-proximo{background:#fef3c7;color:#b45309}
.c-vencido{background:#fee2e2;color:#b91c1c}
.c-sin_calibrar{background:#eef2f7;color:#64748b}
tr.r-vencido{background:rgba(220,38,38,.05)}
tr.r-proximo{background:rgba(217,119,6,.045)}
.acts{display:flex;gap:7px;justify-content:flex-end}
.empty{padding:38px;text-align:center;color:var(--cx-text-mute,#8b8b9e);font-size:13.5px}
.mask{position:fixed;inset:0;background:rgba(24,24,27,.55);backdrop-filter:blur(3px);display:none;align-items:flex-start;justify-content:center;padding:40px 16px;z-index:60;overflow:auto}
.mask.on{display:flex}
.modal{background:var(--cx-surface,#fff);border-radius:20px;width:min(920px,94vw);box-shadow:0 30px 70px -20px rgba(0,0,0,.5);overflow:hidden}
.mhead{display:flex;justify-content:space-between;align-items:center;padding:18px 22px;background:linear-gradient(120deg,#f5f3ff,#faf5ff);border-bottom:1px solid var(--cx-border,#ece9f6)}
.mhead h2{margin:0;font-size:17px;font-weight:800}
.mbody{padding:20px 22px;max-height:70vh;overflow:auto}
.mfoot{display:flex;justify-content:flex-end;gap:9px;padding:15px 22px;border-top:1px solid var(--cx-border,#ece9f6);background:var(--cx-bg-alt,#faf9fd)}
.frm{display:grid;grid-template-columns:1fr 1fr;gap:14px 18px}
.frm .full{grid-column:1/-1}
.lbl{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--cx-text-mute,#8b8b9e);font-weight:800;margin-bottom:5px}
.hint{font-size:11.5px;color:var(--cx-text-mute,#8b8b9e);margin-top:5px}
.msg{font-size:13px;min-height:18px;margin-top:6px}
.note{background:#eff6ff;border:1px solid #bfdbfe;color:#1e40af;border-radius:13px;padding:12px 15px;font-size:12.5px;margin-bottom:16px;line-height:1.5}
.x{background:none;border:none;font-size:24px;line-height:1;cursor:pointer;color:var(--cx-text-mute,#8b8b9e)}
@media(max-width:820px){.frm{grid-template-columns:1fr}.hero .who{display:none}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <div class="ic">&#128295;</div>
    <div>
      <h1>Bit&aacute;cora de calibraci&oacute;n de equipos</h1>
      <div class="sub" style="margin:2px 0 0">Aseguramiento de la Calidad &middot; INVIMA</div>
    </div>
    <div class="who"><a href="/aseguramiento" class="cx-btn cx-btn-ghost cx-btn-sm">&#8592; Aseguramiento</a></div>
  </div>
  <div class="sub">Cu&aacute;ndo se calibr&oacute; cada equipo, cu&aacute;ndo vence la pr&oacute;xima, qui&eacute;n la hizo y con qu&eacute; certificado. Un equipo con la calibraci&oacute;n vencida NO puede usarse para fabricar: es de lo primero que revisa una auditor&iacute;a.</div>

  <div class="kpis">
    <div class="kpi"><div class="n" id="k-total">&middot;</div><div class="l">Equipos activos</div></div>
    <div class="kpi v"><div class="n" id="k-vig">&middot;</div><div class="l">Calibraci&oacute;n vigente</div></div>
    <div class="kpi p"><div class="n" id="k-prox">&middot;</div><div class="l">Vencen en 30 d&iacute;as</div></div>
    <div class="kpi x"><div class="n" id="k-venc">&middot;</div><div class="l">Vencidos</div></div>
    <div class="kpi s"><div class="n" id="k-sin">&middot;</div><div class="l">Sin calibrar</div></div>
  </div>

  <div class="bar">
    <input class="cx-input q" id="q" placeholder="Buscar equipo, c&oacute;digo o &aacute;rea..." oninput="pintar()">
    <button class="fchip on" data-f="todos" onclick="filtrar(this)">Todos</button>
    <button class="fchip" data-f="vencido" onclick="filtrar(this)">Vencidos</button>
    <button class="fchip" data-f="proximo" onclick="filtrar(this)">Por vencer</button>
    <button class="fchip" data-f="sin_calibrar" onclick="filtrar(this)">Sin calibrar</button>
    <button class="fchip" data-f="vigente" onclick="filtrar(this)">Vigentes</button>
    <button class="cx-btn cx-btn-ghost cx-btn-sm" style="margin-left:auto" onclick="cargar()">Actualizar</button>
  </div>

  <div class="panel">
    <table>
      <thead><tr>
        <th>Equipo</th><th>&Aacute;rea</th><th>&Uacute;ltima calibraci&oacute;n</th><th>Pr&oacute;xima</th>
        <th>Estado</th><th>Realiz&oacute;</th><th>Orden de compra</th><th>Certificado</th><th></th>
      </tr></thead>
      <tbody id="tb"><tr><td colspan="9" class="empty">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>

<div class="mask" id="m-reg">
  <div class="modal">
    <div class="mhead"><h2 id="reg-t">Registrar calibraci&oacute;n</h2><button class="x" onclick="cerrar('m-reg')">&times;</button></div>
    <div class="mbody">
      <div class="note">Queda en la hoja de vida del equipo con qui&eacute;n la hizo, el certificado y la orden de compra con que se pag&oacute;. La <b>pr&oacute;xima fecha</b> es la que dispara la alerta de la campana 30 d&iacute;as antes.</div>
      <div class="frm">
        <div><label class="lbl">Fecha de calibraci&oacute;n</label><input type="date" class="cx-input" id="r-fecha"></div>
        <div><label class="lbl">Pr&oacute;xima calibraci&oacute;n (vence)</label><input type="date" class="cx-input" id="r-prox"></div>
        <div><label class="lbl">Qui&eacute;n la realiz&oacute;</label><input class="cx-input" id="r-resp" placeholder="Nombre del t&eacute;cnico"></div>
        <div><label class="lbl">Entidad / empresa externa</label><input class="cx-input" id="r-emp" placeholder="Ej: CI Balanzas de Colombia"></div>
        <div><label class="lbl">Orden de compra</label><input class="cx-input" id="r-oc" list="ocs" placeholder="OC-2026-0000"><datalist id="ocs"></datalist><div class="hint">Ancla la calibraci&oacute;n a la compra del servicio.</div></div>
        <div><label class="lbl">Resultado</label><select class="cx-input" id="r-res"><option value="conforme">Conforme</option><option value="conforme_con_ajuste">Conforme con ajuste</option><option value="no_conforme">No conforme</option></select></div>
        <div class="full"><label class="lbl">Certificado (enlace)</label><input class="cx-input" id="r-cert" placeholder="https://..."></div>
        <div class="full"><label class="lbl">Observaciones</label><textarea class="cx-input" id="r-obs" rows="3"></textarea></div>
      </div>
      <div class="msg" id="r-msg"></div>
    </div>
    <div class="mfoot">
      <button class="cx-btn cx-btn-ghost" onclick="cerrar('m-reg')">Cancelar</button>
      <button class="cx-btn cx-btn-primary" id="r-save" onclick="guardar()">Registrar calibraci&oacute;n</button>
    </div>
  </div>
</div>

<div class="mask" id="m-hist">
  <div class="modal">
    <div class="mhead"><h2 id="h-t">Historial</h2><button class="x" onclick="cerrar('m-hist')">&times;</button></div>
    <div class="mbody" id="h-body"></div>
    <div class="mfoot"><button class="cx-btn cx-btn-ghost" onclick="cerrar('m-hist')">Cerrar</button></div>
  </div>
</div>

<script>
var DATA = [], FILTRO = 'todos', PUEDE = false;
function esc(s){ var d=document.createElement('div'); d.textContent = (s===null||s===undefined)?'':String(s); return d.innerHTML; }
function _csrf(){ var m=document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/); return m?decodeURIComponent(m[1]):''; }
function _opts(method, body){
  var h={}; var t=_csrf(); if(t) h['X-CSRF-Token']=t;
  var o={method:method||'GET', headers:h, credentials:'same-origin'};
  if(body){ h['Content-Type']='application/json'; o.body=JSON.stringify(body); }
  return o;
}
fetch('/api/csrf-token',{credentials:'same-origin'}).catch(function(){});

var LBL={vigente:'Vigente', proximo:'Por vencer', vencido:'VENCIDO', sin_calibrar:'Sin calibrar'};

async function cargar(){
  try{
    var r = await fetch('/api/aseguramiento/calibracion', {credentials:'same-origin'});
    var d = await r.json();
    if(!r.ok){ document.getElementById('tb').innerHTML='<tr><td colspan="9" class="empty">'+esc(d.error||'Error')+'</td></tr>'; return; }
    DATA = d.items||[]; PUEDE = !!d.puede_registrar;
    var k = d.kpis||{};
    document.getElementById('k-total').textContent = k.total||0;
    document.getElementById('k-vig').textContent = k.vigentes||0;
    document.getElementById('k-prox').textContent = k.proximos||0;
    document.getElementById('k-venc').textContent = k.vencidos||0;
    document.getElementById('k-sin').textContent = k.sin_calibrar||0;
    pintar();
  }catch(e){ document.getElementById('tb').innerHTML='<tr><td colspan="9" class="empty">Error de red: '+esc(e.message)+'</td></tr>'; }
}

function filtrar(btn){
  FILTRO = btn.getAttribute('data-f');
  document.querySelectorAll('.fchip').forEach(function(b){ b.classList.toggle('on', b===btn); });
  pintar();
}

function pintar(){
  var q = (document.getElementById('q').value||'').toLowerCase().trim();
  var rows = DATA.filter(function(it){
    if(FILTRO!=='todos' && it.estado!==FILTRO) return false;
    if(!q) return true;
    return (it.codigo+' '+it.nombre+' '+it.area+' '+it.tipo).toLowerCase().indexOf(q)>=0;
  });
  var tb = document.getElementById('tb');
  if(!rows.length){ tb.innerHTML='<tr><td colspan="9" class="empty">No hay equipos que coincidan.</td></tr>'; return; }
  tb.innerHTML = rows.map(function(it){
    var dias = '';
    if(it.estado==='vencido') dias = ' &middot; hace '+Math.abs(it.dias)+' d';
    else if(it.dias!==null && it.dias!==undefined && it.estado!=='sin_calibrar') dias = ' &middot; en '+it.dias+' d';
    var cert = it.certificado_url
      ? '<a href="'+esc(it.certificado_url)+'" target="_blank" rel="noopener" class="cx-btn cx-btn-ghost cx-btn-sm">Ver</a>'
      : '<span class="cx-text-mute">-</span>';
    var reg = PUEDE ? '<button class="cx-btn cx-btn-primary cx-btn-sm" data-cod="'+esc(it.codigo)+'" data-nom="'+esc(it.nombre)+'" onclick="abrirReg(this)">Registrar</button>' : '';
    return '<tr class="r-'+it.estado+'">'
      +'<td><div class="eq">'+esc(it.nombre||it.codigo)+'</div><div class="eqsub"><code>'+esc(it.codigo)+'</code> '+esc(it.tipo||'')+'</div></td>'
      +'<td>'+esc(it.area||'-')+'</td>'
      +'<td>'+(it.ultima?esc(it.ultima):'<span class="cx-text-mute">nunca</span>')+'</td>'
      +'<td>'+(it.proxima?esc(it.proxima):'<span class="cx-text-mute">-</span>')+'</td>'
      +'<td><span class="chip c-'+it.estado+'">'+LBL[it.estado]+dias+'</span></td>'
      +'<td>'+esc(it.responsable||it.empresa||'-')+'</td>'
      +'<td>'+(it.numero_oc?'<code>'+esc(it.numero_oc)+'</code>':'<span class="cx-text-mute">-</span>')+'</td>'
      +'<td>'+cert+'</td>'
      +'<td><div class="acts"><button class="cx-btn cx-btn-ghost cx-btn-sm" data-cod="'+esc(it.codigo)+'" onclick="abrirHist(this)">Historial</button>'+reg+'</div></td>'
      +'</tr>';
  }).join('');
}

function cerrar(id){ document.getElementById(id).classList.remove('on'); }

async function abrirReg(btn){
  var cod = btn.getAttribute('data-cod'), nom = btn.getAttribute('data-nom');
  document.getElementById('reg-t').textContent = 'Registrar calibracion  ·  ' + (nom||cod);
  document.getElementById('r-save').setAttribute('data-cod', cod);
  var hoy = new Date().toISOString().slice(0,10);
  document.getElementById('r-fecha').value = hoy;
  var y = new Date(); y.setFullYear(y.getFullYear()+1);
  document.getElementById('r-prox').value = y.toISOString().slice(0,10);
  ['r-resp','r-emp','r-oc','r-cert','r-obs'].forEach(function(i){ document.getElementById(i).value=''; });
  document.getElementById('r-msg').innerHTML='';
  document.getElementById('m-reg').classList.add('on');
  try{
    var r = await fetch('/api/aseguramiento/calibracion/ocs-sugeridas',{credentials:'same-origin'});
    var d = await r.json();
    document.getElementById('ocs').innerHTML = (d.items||[]).map(function(o){
      return '<option value="'+esc(o.numero_oc)+'">'+esc(o.proveedor)+' '+esc(o.fecha)+'</option>';
    }).join('');
  }catch(e){}
}

async function guardar(){
  var btn = document.getElementById('r-save'), cod = btn.getAttribute('data-cod');
  var msg = document.getElementById('r-msg');
  var fecha = document.getElementById('r-fecha').value;
  if(!fecha){ msg.innerHTML='<span style="color:#dc2626">La fecha de calibraci&oacute;n es obligatoria.</span>'; return; }
  btn.disabled = true;
  msg.innerHTML = '<span class="cx-text-mute">Guardando...</span>';
  var body = {
    tipo_evento: 'calibracion', estado: 'completado', fecha: fecha,
    fecha_proxima: document.getElementById('r-prox').value || null,
    responsable: document.getElementById('r-resp').value || null,
    empresa_externa: document.getElementById('r-emp').value || null,
    numero_oc: document.getElementById('r-oc').value || null,
    certificado_url: document.getElementById('r-cert').value || null,
    resultado: document.getElementById('r-res').value || null,
    observaciones: document.getElementById('r-obs').value || null
  };
  try{
    var r = await fetch('/api/calidad/equipos/'+encodeURIComponent(cod)+'/registrar-evento', _opts('POST', body));
    var d = await r.json();
    if(r.ok && d.ok){
      msg.innerHTML = '<span style="color:#15803d;font-weight:700">Calibraci&oacute;n registrada.</span>';
      setTimeout(function(){ cerrar('m-reg'); cargar(); }, 700);
    } else {
      msg.innerHTML = '<span style="color:#dc2626">'+esc(d.error||'No se pudo guardar')+'</span>';
    }
  }catch(e){ msg.innerHTML = '<span style="color:#dc2626">Error de red: '+esc(e.message)+'</span>'; }
  btn.disabled = false;
}

async function abrirHist(btn){
  var cod = btn.getAttribute('data-cod');
  var body = document.getElementById('h-body');
  document.getElementById('h-t').textContent = 'Historial de calibracion  ·  ' + cod;
  body.innerHTML = '<div class="empty">Cargando...</div>';
  document.getElementById('m-hist').classList.add('on');
  try{
    var r = await fetch('/api/aseguramiento/calibracion/'+encodeURIComponent(cod)+'/historial',{credentials:'same-origin'});
    var d = await r.json();
    if(!r.ok){ body.innerHTML='<div class="empty">'+esc(d.error||'Error')+'</div>'; return; }
    var ev = d.eventos||[];
    if(!ev.length){ body.innerHTML='<div class="empty">Este equipo todav&iacute;a no tiene calibraciones registradas.</div>'; return; }
    body.innerHTML = '<table><thead><tr><th>Fecha</th><th>Pr&oacute;xima</th><th>Realiz&oacute;</th><th>Entidad</th>'
      +'<th>Resultado</th><th>OC</th><th>Certificado</th><th>Registr&oacute;</th></tr></thead><tbody>'
      + ev.map(function(e){
          return '<tr><td><b>'+esc(e.fecha)+'</b></td><td>'+esc(e.proxima||'-')+'</td><td>'+esc(e.responsable||'-')+'</td>'
            +'<td>'+esc(e.empresa||'-')+'</td><td>'+esc(e.resultado||'-')+'</td>'
            +'<td>'+(e.numero_oc?'<code>'+esc(e.numero_oc)+'</code>':'-')+'</td>'
            +'<td>'+(e.certificado_url?'<a href="'+esc(e.certificado_url)+'" target="_blank" rel="noopener">Ver</a>':'-')+'</td>'
            +'<td>'+esc(e.creado_por||'-')+'<div class="eqsub">'+esc(e.creado_en||'')+'</div></td></tr>'
            + (e.observaciones ? '<tr><td colspan="8" class="eqsub" style="padding-top:0">'+esc(e.observaciones)+'</td></tr>' : '');
        }).join('')
      + '</tbody></table>';
  }catch(e){ body.innerHTML='<div class="empty">Error de red: '+esc(e.message)+'</div>'; }
}

document.querySelectorAll('.mask').forEach(function(m){
  m.addEventListener('click', function(ev){ if(ev.target===m) m.classList.remove('on'); });
});
cargar();
</script>
</body>
</html>'''
