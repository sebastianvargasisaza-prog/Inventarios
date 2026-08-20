"""Plan de suplencias · quién cubre a quién, por qué y hasta cuándo.

Sebastián 20-ago-2026, sobre los roles del batch record: *"son backup, como reemplazos: en
caso de que no estén, ellos pueden hacerlo"* · *"lo puede hacer sólo por plan de suplencias"*.

La pantalla existe porque el permiso tiene que poder MIRARSE: una habilitación que sólo vive
en el código no se puede mostrar en una auditoría, y una que no caduca sola se olvida
encendida. Acá se ve quién está habilitado hoy, por qué y hasta qué día.

LECTURA abierta (saber quién cubre a quién es parte de operar) · ESCRITURA de Aseguramiento y
Dirección, y la pantalla lo dice en vez de ofrecer un botón que va a dar 403.
"""

SUPLENCIAS_HTML = r'''<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Plan de suplencias · EOS</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
body{font-family:"Inter",system-ui,-apple-system,Arial,sans-serif;background:var(--cx-bg);color:var(--cx-text);margin:0;padding:22px 2vw 60px}
.wrap{width:96vw;max-width:1720px;margin:0 auto}
.hero{display:flex;align-items:center;gap:15px;margin-bottom:4px}
.hero .ic{width:50px;height:50px;border-radius:15px;background:var(--cx-primary-grad);display:flex;align-items:center;justify-content:center;font-size:24px;flex-shrink:0;box-shadow:0 10px 24px -10px rgba(109,40,217,.6)}
.hero h1{margin:0;font-size:23px;letter-spacing:-.02em;font-weight:800}
.hero .nav{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap}
.sub{color:var(--cx-text-soft);font-size:13.5px;margin:4px 0 18px;max-width:980px;line-height:1.55}
.card{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:18px;box-shadow:0 1px 3px rgba(15,23,42,.04),0 10px 30px rgba(15,23,42,.05);padding:18px 20px;margin-bottom:16px}
.card h2{margin:0 0 4px;font-size:15px;font-weight:800;letter-spacing:-.01em}
.card .hint{font-size:12.5px;color:var(--cx-text-mute);margin-bottom:12px;line-height:1.5}
.vig{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}
.vcard{border:1px solid var(--cx-success);background:var(--cx-success-pale);border-radius:14px;padding:14px 16px}
.vcard .q{font-size:15px;font-weight:800;color:var(--cx-success-text)}
.vcard .d{font-size:12.5px;color:var(--cx-text-soft);margin-top:5px;line-height:1.5}
.vacio{font-size:13px;color:var(--cx-text-mute);padding:14px 0}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--cx-text-mute);font-weight:800;padding:8px 10px;border-bottom:1px solid var(--cx-hairline)}
td{padding:11px 10px;border-bottom:1px solid var(--cx-hairline);vertical-align:middle}
tr:hover td{background:var(--cx-bg-alt)}
.pill{display:inline-block;padding:3px 11px;border-radius:999px;font-size:11px;font-weight:800;letter-spacing:.2px}
.pill.on{background:var(--cx-success-pale);color:var(--cx-success-text);border:1px solid var(--cx-success)}
.pill.off{background:var(--cx-bg-alt);color:var(--cx-text-mute);border:1px solid var(--cx-hairline)}
.pill.old{background:var(--cx-warn-pale);color:var(--cx-warn-text);border:1px solid var(--cx-warn)}
.who{font-weight:700}
.mut{color:var(--cx-text-mute)}
.acc{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.ov{position:fixed;inset:0;background:rgba(15,23,42,.55);display:none;align-items:flex-start;justify-content:center;z-index:80;padding:40px 16px;overflow:auto}
.ov.on{display:flex}
.modal{background:var(--cx-card);border-radius:20px;width:min(760px,94vw);box-shadow:0 30px 80px -20px rgba(15,23,42,.5);overflow:hidden}
.mhead{display:flex;align-items:center;gap:12px;padding:18px 22px;border-bottom:1px solid var(--cx-hairline)}
.mhead h2{margin:0;font-size:17px;font-weight:800}
.mhead .x{margin-left:auto;background:none;border:0;font-size:26px;line-height:1;cursor:pointer;color:var(--cx-text-mute)}
.mbody{padding:20px 22px;display:grid;grid-template-columns:1fr 1fr;gap:14px}
.mbody .full{grid-column:1/-1}
.mfoot{padding:16px 22px;border-top:1px solid var(--cx-hairline);display:flex;gap:10px;justify-content:flex-end;align-items:center}
label.f{display:block;font-size:11.5px;font-weight:800;text-transform:uppercase;letter-spacing:.4px;color:var(--cx-text-mute);margin-bottom:5px}
.aviso{background:var(--cx-warn-pale);border:1px solid var(--cx-warn);color:var(--cx-warn-text);border-radius:12px;padding:11px 14px;font-size:12.5px;line-height:1.55}
.msg{font-size:12.5px;margin-right:auto}
.msg.err{color:var(--cx-danger-text)}
.msg.ok{color:var(--cx-success-text)}
@media(max-width:720px){.mbody{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <div class="ic">&#128100;</div>
    <div>
      <h1>Plan de suplencias</h1>
      <div class="mut" style="font-size:12.5px"><b>Aseguramiento</b> &middot; qui&eacute;n cubre a qui&eacute;n en el batch record</div>
    </div>
    <div class="nav">
      <a href="/aseguramiento" class="cx-btn cx-btn-ghost cx-btn-sm">&larr; Aseguramiento</a>
      <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm">M&oacute;dulos</a>
    </div>
  </div>
  <div class="sub">
    Una suplencia habilita a una persona a firmar en el puesto de otra <b>mientras esa otra
    no est&aacute;</b>. Se declara una vez y se <b>activa</b> cuando hace falta, con motivo y
    fecha de fin: sin fecha de fin no habilita nada, porque eso ya no es una suplencia sino un
    permiso permanente. Se apaga sola al vencer.
    <br>Lo que una suplencia <b>no</b> cambia: quien ejecuta un paso, un pesaje o un &iacute;tem
    de despeje sigue sin poder firmar su propia verificaci&oacute;n. Esa regla es por registro
    y no depende del puesto.
  </div>

  <div class="card">
    <h2>Habilitadas hoy</h2>
    <div class="hint">Lo que est&aacute; surtiendo efecto en este momento.</div>
    <div class="vig" id="vig"></div>
  </div>

  <div class="card">
    <h2>El plan</h2>
    <div class="hint" id="hint-plan">Qui&eacute;n puede cubrir qu&eacute; puesto. Declarado no es habilitado: hace falta activarlo.</div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr>
          <th>Suplente</th><th>Puesto que cubre</th><th>Titular</th><th>Motivo</th>
          <th>Desde</th><th>Hasta</th><th>Estado</th><th></th>
        </tr></thead>
        <tbody id="tb"><tr><td colspan="8" class="vacio">Cargando&hellip;</td></tr></tbody>
      </table>
    </div>
    <div style="margin-top:14px" id="zona-nueva"></div>
  </div>
</div>

<div class="ov" id="ov">
  <div class="modal">
    <div class="mhead"><h2 id="m-tit">Activar suplencia</h2><button class="x" onclick="cerrar()">&times;</button></div>
    <div class="mbody">
      <div>
        <label class="f" for="f-suplente">Suplente</label>
        <select id="f-suplente" class="cx-input"></select>
      </div>
      <div>
        <label class="f" for="f-rol">Puesto que cubre</label>
        <select id="f-rol" class="cx-input"></select>
      </div>
      <div>
        <label class="f" for="f-titular">Titular ausente</label>
        <select id="f-titular" class="cx-input"></select>
      </div>
      <div>
        <label class="f" for="f-desde">Desde</label>
        <input type="date" id="f-desde" class="cx-input">
      </div>
      <div>
        <label class="f" for="f-hasta">Hasta <span class="mut">&middot; obligatorio para activar</span></label>
        <input type="date" id="f-hasta" class="cx-input">
      </div>
      <div>
        <label class="f" for="f-activo">Estado</label>
        <select id="f-activo" class="cx-input">
          <option value="1">Activa &middot; habilita desde ya</option>
          <option value="0">Declarada &middot; no habilita nada</option>
        </select>
      </div>
      <div class="full">
        <label class="f" for="f-motivo">Motivo</label>
        <input type="text" id="f-motivo" class="cx-input" maxlength="300" placeholder="Ej: licencia de la analista de Calidad">
      </div>
      <div class="full aviso">
        Esto queda en el registro de auditor&iacute;a con qui&eacute;n habilit&oacute; a
        qui&eacute;n, para qu&eacute; puesto y por cu&aacute;nto tiempo &mdash; que es
        exactamente lo que una auditor&iacute;a pregunta.
      </div>
    </div>
    <div class="mfoot">
      <span class="msg" id="m-msg"></span>
      <button class="cx-btn cx-btn-ghost" onclick="cerrar()">Cancelar</button>
      <button class="cx-btn cx-btn-grad" id="btn-guardar" onclick="guardar()">Guardar</button>
    </div>
  </div>
</div>

<script>
var DATA = [], ROLES = [], PUEDE = false, USUARIOS = [];
function esc(s){ var d=document.createElement('div'); d.textContent=(s===null||s===undefined)?'':String(s); return d.innerHTML; }
function _csrf(){ var m=document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/); return m?decodeURIComponent(m[1]):''; }
function _opts(method, body){
  var h={}; var t=_csrf(); if(t) h['X-CSRF-Token']=t;
  var o={method:method||'GET', headers:h, credentials:'same-origin'};
  if(body){ h['Content-Type']='application/json'; o.body=JSON.stringify(body); }
  return o;
}
fetch('/api/csrf-token',{credentials:'same-origin'}).catch(function(){});

function estadoPill(f){
  if(f.vigente) return '<span class="pill on">Habilitada</span>';
  if(f.activo && f.hasta) return '<span class="pill old">Vencida</span>';
  return '<span class="pill off">Declarada</span>';
}

function pintar(){
  var vig = DATA.filter(function(f){ return f.vigente; });
  document.getElementById('vig').innerHTML = vig.length ? vig.map(function(f){
    return '<div class="vcard"><div class="q">'+esc(f.suplente)+' cubre '+esc(f.rol_label)+'</div>'
      + '<div class="d">'+(f.titular?('Por <b>'+esc(f.titular)+'</b>. '):'')
      + esc(f.motivo||'Sin motivo anotado')+'<br>Hasta el <b>'+esc(f.hasta)+'</b>.</div></div>';
  }).join('') : '<div class="vacio">Nadie est&aacute; cubriendo a nadie hoy. Cada quien firma su propio puesto.</div>';

  document.getElementById('tb').innerHTML = DATA.length ? DATA.map(function(f){
    var acc = PUEDE
      ? '<div class="acc"><button class="cx-btn cx-btn-ghost cx-btn-sm" onclick="abrir('+f.id+')">Editar</button>'
        + (f.activo ? '<button class="cx-btn cx-btn-ghost cx-btn-sm" onclick="revocar('+f.id+')">Terminar</button>' : '')
        + '</div>'
      : '';
    return '<tr><td class="who">'+esc(f.suplente)+'</td><td>'+esc(f.rol_label)+'</td>'
      + '<td>'+(f.titular?esc(f.titular):'<span class="mut">&mdash;</span>')+'</td>'
      + '<td>'+(f.motivo?esc(f.motivo):'<span class="mut">&mdash;</span>')+'</td>'
      + '<td>'+(f.desde?esc(f.desde):'<span class="mut">&mdash;</span>')+'</td>'
      + '<td>'+(f.hasta?esc(f.hasta):'<span class="mut">sin fin</span>')+'</td>'
      + '<td>'+estadoPill(f)+'</td><td>'+acc+'</td></tr>';
  }).join('') : '<tr><td colspan="8" class="vacio">No hay plan cargado.</td></tr>';

  document.getElementById('zona-nueva').innerHTML = PUEDE
    ? '<button class="cx-btn cx-btn-grad" onclick="abrir(0)">+ Nueva suplencia</button>'
    : '<div class="vacio">Para cambiar el plan hace falta Aseguramiento o Direcci&oacute;n.</div>';
}

async function cargar(){
  try{
    var r = await fetch('/api/aseguramiento/suplencias', {credentials:'same-origin'});
    var d = await r.json();
    if(!r.ok){ document.getElementById('tb').innerHTML='<tr><td colspan="8" class="vacio">'+esc(d.error||'Error')+'</td></tr>'; return; }
    DATA = d.suplencias||[]; ROLES = d.roles||[]; PUEDE = !!d.puede_editar;
    USUARIOS = d.usuarios||[];
    pintar();
  }catch(e){
    document.getElementById('tb').innerHTML='<tr><td colspan="8" class="vacio">No se pudo cargar.</td></tr>';
  }
}

function _sel(id, valores, valor){
  var el = document.getElementById(id);
  el.innerHTML = valores.map(function(v){
    var val = (typeof v === 'string') ? v : v.rol;
    var lbl = (typeof v === 'string') ? v : v.label;
    return '<option value="'+esc(val)+'"'+(val===valor?' selected':'')+'>'+esc(lbl)+'</option>';
  }).join('');
}

function abrir(id){
  var f = DATA.filter(function(x){ return x.id===id; })[0] || {};
  document.getElementById('m-tit').textContent = id ? 'Suplencia de ' + (f.suplente||'') : 'Nueva suplencia';
  document.getElementById('m-msg').textContent = '';
  _sel('f-suplente', USUARIOS, f.suplente||'');
  _sel('f-rol', ROLES, f.rol||'');
  _sel('f-titular', [''].concat(USUARIOS), f.titular||'');
  document.getElementById('f-desde').value = f.desde||'';
  document.getElementById('f-hasta').value = f.hasta||'';
  document.getElementById('f-motivo').value = f.motivo||'';
  document.getElementById('f-activo').value = f.activo ? '1' : '0';
  document.getElementById('ov').classList.add('on');
}
function cerrar(){ document.getElementById('ov').classList.remove('on'); }
document.addEventListener('keydown', function(e){ if(e.key==='Escape') cerrar(); });
document.getElementById('ov').addEventListener('click', function(e){ if(e.target===this) cerrar(); });

async function guardar(){
  var msg = document.getElementById('m-msg');
  var btn = document.getElementById('btn-guardar');
  var body = {
    suplente: document.getElementById('f-suplente').value,
    rol: document.getElementById('f-rol').value,
    titular: document.getElementById('f-titular').value,
    desde: document.getElementById('f-desde').value,
    hasta: document.getElementById('f-hasta').value,
    motivo: document.getElementById('f-motivo').value,
    activo: document.getElementById('f-activo').value === '1'
  };
  btn.disabled = true; msg.className='msg'; msg.textContent = 'Guardando...';
  try{
    var r = await fetch('/api/aseguramiento/suplencias/guardar', _opts('POST', body));
    var d = await r.json();
    if(!r.ok){ msg.className='msg err'; msg.textContent = d.error || 'No se pudo guardar'; btn.disabled=false; return; }
    cerrar(); await cargar();
  }catch(e){ msg.className='msg err'; msg.textContent='No se pudo guardar.'; }
  btn.disabled = false;
}

async function revocar(id){
  var f = DATA.filter(function(x){ return x.id===id; })[0] || {};
  if(!confirm('Terminar la suplencia de ' + (f.suplente||'') + ' en ' + (f.rol_label||'') + '?\nDeja de habilitar desde este momento. El registro se conserva.')) return;
  try{
    var r = await fetch('/api/aseguramiento/suplencias/revocar', _opts('POST', {id:id}));
    if(r.ok) await cargar();
  }catch(e){}
}

cargar();
</script>
<script src="/static/cortex.js?v=eos3"></script>
</body></html>'''
