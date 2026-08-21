"""Cuadre rápido de inventario · parado frente al estante.

Sebastián 21-ago-2026: *"el inventario está descuadrado ... necesito algo súper rápido: que
aparezca estantería por cada cosa A B C D E, productos, y si ese producto tiene varios lotes que
los muestre, con la opción de corregir o de colocar 'no existe' ... lo más importante es que sea
muy rápido y se refleje"*.

Por qué no es el conteo cíclico: ese es un PROCESO (iniciar, contar, cerrar, ajustar) y sirve
para el conteo programado. Esto es otra cosa -- una acción por lote, que escribe el kardex en el
mismo momento. Se escribe la cantidad, se aprieta Enter, y el stock ya quedó.

Lo que NO se relaja por ser rápido: cada ajuste deja su rastro con quién, cuándo y por qué, y
conserva el lote, su estado y su vencimiento.
"""

CUADRE_HTML = r'''<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cuadre de inventario · EOS</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
body{font-family:"Inter",system-ui,-apple-system,Arial,sans-serif;background:var(--cx-bg);color:var(--cx-text);margin:0;padding:18px 2vw 90px}
.wrap{width:96vw;max-width:1500px;margin:0 auto}
.hero{display:flex;align-items:center;gap:14px;margin-bottom:6px}
.hero .ic{width:46px;height:46px;border-radius:14px;background:var(--cx-primary-grad);display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0}
.hero h1{margin:0;font-size:21px;font-weight:800;letter-spacing:-.02em}
.hero .nav{margin-left:auto;display:flex;gap:8px}
.sub{color:var(--cx-text-soft);font-size:13px;margin:2px 0 14px;max-width:900px;line-height:1.5}
.card{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:16px;padding:14px 16px;margin-bottom:14px;box-shadow:0 1px 3px rgba(15,23,42,.04)}
.ests{display:flex;gap:8px;flex-wrap:wrap}
.est{padding:9px 18px;border-radius:999px;border:1px solid var(--cx-hairline);background:var(--cx-card);font-weight:800;font-size:14px;cursor:pointer;display:flex;align-items:center;gap:8px}
.est:hover{border-color:var(--cx-primary-light)}
.est.on{background:var(--cx-primary);color:#fff;border-color:var(--cx-primary)}
.est .n{font-size:11px;font-weight:700;opacity:.75}
.barra{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:12px}
.barra input[type=search]{flex:1;max-width:420px}
.prog{margin-left:auto;font-size:12.5px;font-weight:700;color:var(--cx-text-mute)}
.mat{border:1px solid var(--cx-hairline);border-radius:14px;margin-bottom:10px;overflow:hidden;background:var(--cx-card)}
.mat.oculto{display:none}
.mhead{display:flex;align-items:baseline;gap:10px;padding:10px 14px;background:var(--cx-bg-alt);flex-wrap:wrap}
.mhead b{font-size:14.5px}
.mhead .cod{font-family:ui-monospace,monospace;font-size:11.5px;color:var(--cx-text-mute)}
.mhead .tot{margin-left:auto;font-size:12.5px;font-weight:800;color:var(--cx-text-soft);font-variant-numeric:tabular-nums}
.lote{display:flex;align-items:center;gap:12px;padding:10px 14px;border-top:1px solid var(--cx-hairline);flex-wrap:wrap}
.lote .id{min-width:190px}
.lote .id b{font-family:ui-monospace,monospace;font-size:13px}
.lote .meta{font-size:11px;color:var(--cx-text-mute);display:block;margin-top:2px}
.lote .sis{min-width:120px;font-size:15px;font-weight:800;font-variant-numeric:tabular-nums}
.lote input[type=number]{width:130px}
.lote .acc{display:flex;gap:6px;margin-left:auto;flex-wrap:wrap}
.lote.ok{background:var(--cx-success-pale)}
.lote.ok .sis{color:var(--cx-success-text)}
.chip-sinubic{display:inline-block;margin-left:8px;padding:1px 8px;border-radius:999px;font-size:10.5px;font-weight:800;background:var(--cx-warn-pale);color:var(--cx-warn-text);border:1px solid var(--cx-warn)}
.est.pend{border-color:var(--cx-warn);color:var(--cx-warn-text)}
.est.pend.on{background:var(--cx-warn);color:#fff;border-color:var(--cx-warn)}
.msg{font-size:12px;font-weight:700;min-width:120px}
.msg.ok{color:var(--cx-success-text)}
.msg.err{color:var(--cx-danger-text)}
.vacio{padding:18px;color:var(--cx-text-mute);font-size:13.5px}
.pie{position:fixed;left:0;right:0;bottom:0;background:var(--cx-card);border-top:1px solid var(--cx-hairline);padding:10px 20px;display:flex;gap:12px;align-items:center;box-shadow:0 -4px 18px rgba(15,23,42,.07);z-index:40}
.ov{position:fixed;inset:0;background:rgba(15,23,42,.55);display:none;align-items:center;justify-content:center;z-index:80;padding:20px}
.ov.on{display:flex}
.modal{background:var(--cx-card);border-radius:18px;width:min(560px,95vw);overflow:hidden}
.modal .h{padding:16px 20px;border-bottom:1px solid var(--cx-hairline);font-weight:800;font-size:16px}
.modal .b{padding:16px 20px;display:grid;grid-template-columns:1fr 1fr;gap:12px}
.modal .b .full{grid-column:1/-1}
.modal .f{padding:14px 20px;border-top:1px solid var(--cx-hairline);display:flex;gap:10px;justify-content:flex-end;align-items:center}
label.f2{display:block;font-size:11.5px;font-weight:800;text-transform:uppercase;letter-spacing:.4px;color:var(--cx-text-mute);margin-bottom:4px}
@media(max-width:700px){.modal .b{grid-template-columns:1fr}.lote .acc{margin-left:0;width:100%}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <div class="ic">&#128230;</div>
    <div>
      <h1>Cuadre de inventario</h1>
      <div style="font-size:12.5px;color:var(--cx-text-mute)"><b>Bodega</b> &middot; lo que hay en el estante manda</div>
    </div>
    <div class="nav">
      <a href="/inventarios" class="cx-btn cx-btn-ghost cx-btn-sm">&larr; Planta</a>
      <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm">M&oacute;dulos</a>
    </div>
  </div>
  <div class="sub">
    Eleg&iacute; la estanter&iacute;a, escrib&iacute; lo que hay y apret&aacute; <b>Enter</b>: el kardex queda
    ajustado en el momento. <b>No existe</b> lo deja en cero. Cada ajuste guarda qui&eacute;n, cu&aacute;ndo y
    por qu&eacute;, y conserva el lote con su vencimiento.
  </div>

  <div class="card">
    <div class="ests" id="ests"><span class="vacio">Cargando estanter&iacute;as&hellip;</span></div>
    <div class="barra">
      <input id="q" class="cx-input" type="search" placeholder="Buscar material o lote..." autocomplete="off" oninput="filtrar()">
      <button class="cx-btn cx-btn-ghost cx-btn-sm" onclick="abrirAlta()">+ Est&aacute; en el estante y no aparece</button>
      <button class="cx-btn cx-btn-ghost cx-btn-sm" onclick="abrirUbic()" title="La misma estanteria escrita de varias formas parte el inventario en pedazos">&#129513; Unificar ubicaciones</button>
      <span class="prog" id="prog"></span>
    </div>
  </div>

  <div id="lista"><div class="vacio">Eleg&iacute; una estanter&iacute;a para empezar.</div></div>
</div>

<div class="pie">
  <span id="pie-msg" style="font-size:13px;font-weight:700"></span>
  <span style="margin-left:auto;font-size:12px;color:var(--cx-text-mute)">Enter guarda &middot; lo ajustado queda en verde</span>
</div>

<div class="ov" id="ov-ubic">
  <div class="modal" style="width:min(720px,95vw)">
    <div class="h">Ubicaciones escritas de varias formas</div>
    <div class="b" style="display:block;max-height:60vh;overflow:auto">
      <div style="font-size:13px;color:var(--cx-text-soft);line-height:1.55;margin-bottom:12px">
        Para el sistema, <b>Estiba</b> y <b>ESTIBAS</b> son dos lugares distintos, as&iacute; que el
        material queda partido y el inventario por estanter&iacute;a no cuadra. Ac&aacute; se dejan con un
        solo nombre. No se mueve ni una unidad: s&oacute;lo c&oacute;mo se llama el lugar.
      </div>
      <div id="ubic-lista"><div class="vacio">Buscando&hellip;</div></div>
    </div>
    <div class="f">
      <span class="msg" id="u-msg"></span>
      <button class="cx-btn cx-btn-ghost" onclick="cerrarUbic()">Cerrar</button>
    </div>
  </div>
</div>

<div class="ov" id="ov-alta">
  <div class="modal">
    <div class="h">Dar de alta lo que est&aacute; en el estante</div>
    <div class="b">
      <div class="full">
        <label class="f2" for="a-cod">Material</label>
        <select id="a-cod" class="cx-input"></select>
      </div>
      <div>
        <label class="f2" for="a-lote">Lote</label>
        <input id="a-lote" class="cx-input" placeholder="el del envase">
      </div>
      <div>
        <label class="f2" for="a-cant">Cantidad</label>
        <input id="a-cant" class="cx-input" type="number" step="0.001" min="0">
      </div>
      <div>
        <label class="f2" for="a-vence">Vence</label>
        <input id="a-vence" class="cx-input" type="date">
      </div>
      <div>
        <label class="f2" for="a-est">Estanter&iacute;a</label>
        <input id="a-est" class="cx-input">
      </div>
      <div class="full">
        <label class="f2" for="a-motivo">&iquest;De d&oacute;nde sali&oacute;? <span style="text-transform:none;font-weight:600">&middot; obligatorio</span></label>
        <input id="a-motivo" class="cx-input" maxlength="200" placeholder="Ej: estaba en bodega sin registrar, sobrante de produccion...">
      </div>
    </div>
    <div class="f">
      <span class="msg" id="a-msg"></span>
      <button class="cx-btn cx-btn-ghost" onclick="cerrarAlta()">Cancelar</button>
      <button class="cx-btn cx-btn-grad" onclick="guardarAlta()">Dar de alta</button>
    </div>
  </div>
</div>

<script>
var EST='', DATOS=[], HECHOS=0;
function esc(s){var d=document.createElement('div');d.textContent=(s===null||s===undefined)?'':String(s);return d.innerHTML;}
function _csrf(){var m=document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);return m?decodeURIComponent(m[1]):'';}
function _opts(method, body){var h={};var t=_csrf();if(t)h['X-CSRF-Token']=t;var o={method:method||'GET',headers:h,credentials:'same-origin'};if(body){h['Content-Type']='application/json';o.body=JSON.stringify(body);}return o;}
function _tok(){return 'cuadre-'+Date.now()+'-'+Math.random().toString(36).slice(2,10);}
fetch('/api/csrf-token',{credentials:'same-origin'}).catch(function(){});

async function cargarEstanterias(){
  try{
    var r=await fetch('/api/conteo/estanterias?tipo_material=MP',{credentials:'same-origin'});
    var d=await r.json();
    var box=document.getElementById('ests');
    if(!Array.isArray(d)||!d.length){ box.innerHTML='<span class="vacio">No hay estanter&iacute;as cargadas.</span>'; return; }
    box.innerHTML=d.map(function(e){
      var nom=e.estanteria, sinUbic=/^sin estanter/i.test(nom);
      return '<button class="est'+(sinUbic?' pend':'')+'" data-est="'+esc(e.estanteria)+'" onclick="elegir(this,\''+esc(e.estanteria).replace(/'/g,"\\'")+'\')">'
        +(sinUbic?'&#128205; Sin ubicaci&oacute;n &middot; para ubicar':esc(nom))+'<span class="n">'+(e.total_mps||0)+'</span></button>';
    }).join('');
  }catch(e){ document.getElementById('ests').innerHTML='<span class="vacio">No se pudieron cargar.</span>'; }
}

function elegir(btn, est){
  document.querySelectorAll('.est').forEach(function(b){b.classList.remove('on');});
  if(btn) btn.classList.add('on');
  EST=est; HECHOS=0; cargarMateriales();
}

async function cargarMateriales(){
  var cont=document.getElementById('lista');
  cont.innerHTML='<div class="vacio">Cargando&hellip;</div>';
  try{
    var r=await fetch('/api/inventario/cuadre-lotes?est='+encodeURIComponent(EST),{credentials:'same-origin'});
    var _d=await r.json(); DATOS=(_d&&_d.lotes)||[];
  }catch(e){ cont.innerHTML='<div class="vacio">No se pudo cargar la estanter&iacute;a.</div>'; return; }
  if(!Array.isArray(DATOS)||!DATOS.length){ cont.innerHTML='<div class="vacio">Esta estanter&iacute;a no tiene material con stock.</div>'; pintarProg(); return; }
  // Un material puede tener VARIOS lotes: se agrupan para verlos juntos, que es como estan
  // fisicamente en el estante.
  var porMat={};
  DATOS.forEach(function(x){ (porMat[x.codigo_mp]=porMat[x.codigo_mp]||{nombre:x.nombre,cod:x.codigo_mp,lotes:[]}).lotes.push(x); });
  var html='';
  Object.keys(porMat).forEach(function(k){
    var m=porMat[k]; var tot=m.lotes.reduce(function(a,b){return a+(parseFloat(b.stock_sistema)||0);},0);
    var busca=(m.nombre+' '+m.cod+' '+m.lotes.map(function(l){return l.lote;}).join(' ')).toLowerCase();
    html+='<div class="mat" data-buscar="'+esc(busca)+'">';
    html+='<div class="mhead"><b>'+esc(m.nombre)+'</b><span class="cod">'+esc(m.cod)+'</span>'
       +'<span class="tot">'+m.lotes.length+' lote(s) &middot; '+tot.toLocaleString('es-CO')+'</span></div>';
    m.lotes.forEach(function(l,i){
      var id=esc(m.cod)+'__'+i;
      html+='<div class="lote" id="row-'+id+'">'
        +'<div class="id"><b>'+(l.lote?esc(l.lote):'<span style="color:var(--cx-text-mute)">sin lote</span>')+'</b>'
        +(l.sin_ubicar?'<span class="chip-sinubic" title="Existe pero nadie sabe donde esta: aparece aca porque su material si esta en esta estanteria">&#128205; sin ubicar</span>':'')
        +'<span class="meta">'+(l.posicion?('pos. '+esc(l.posicion)+' &middot; '):'')+(l.fecha_vencimiento?('vence '+esc(l.fecha_vencimiento)):'sin vencimiento')+'</span></div>'
        +'<div class="sis" id="sis-'+id+'">'+(parseFloat(l.stock_sistema)||0).toLocaleString('es-CO')+'</div>'
        +'<input type="number" step="0.001" min="0" class="cx-input" id="in-'+id+'" placeholder="lo que hay" '
        +'onkeydown="if(event.key===\'Enter\'){guardar(\''+id+'\')}">'
        +'<div class="acc">'
        +'<button class="cx-btn cx-btn-sm cx-btn-ghost" onclick="igual(\''+id+'\')">= Igual</button>'
        +'<button class="cx-btn cx-btn-sm cx-btn-ghost" onclick="noExiste(\''+id+'\')">No existe</button>'
        +'<button class="cx-btn cx-btn-sm cx-btn-grad" onclick="guardar(\''+id+'\')">Guardar</button>'
        +((l.sin_ubicar&&EST)?('<button class="cx-btn cx-btn-sm cx-btn-ghost" onclick="ubicarAqui(\''+id+'\')" title="Dejar este lote en la estanteria que estas revisando">&#128205; Ubicar aqu&iacute;</button>'):'')
        +'</div><span class="msg" id="msg-'+id+'"></span></div>';
      DATOS_MAP[id]=l;
    });
    html+='</div>';
  });
  cont.innerHTML=html;
  filtrar(); pintarProg();
}
var DATOS_MAP={};

function pintarProg(){
  var tot=Object.keys(DATOS_MAP).length;
  document.getElementById('prog').textContent = tot? (HECHOS+' de '+tot+' revisados') : '';
}
function filtrar(){
  var q=(document.getElementById('q').value||'').trim().toLowerCase();
  document.querySelectorAll('.mat').forEach(function(el){
    el.classList.toggle('oculto', !!q && (el.dataset.buscar||'').indexOf(q)<0);
  });
}
function igual(id){ var l=DATOS_MAP[id]; if(!l) return; document.getElementById('in-'+id).value=l.stock_sistema; guardar(id); }
function noExiste(id){ var l=DATOS_MAP[id]; if(!l) return;
  if(!confirm('Vas a dejar este lote en CERO. El sistema cree que hay '+l.stock_sistema+'.')) return;
  document.getElementById('in-'+id).value=0; guardar(id, 'no existe en el estante'); }

async function guardar(id, motivo){
  var l=DATOS_MAP[id]; if(!l) return;
  var inp=document.getElementById('in-'+id), msg=document.getElementById('msg-'+id);
  var v=(inp.value||'').trim();
  if(v===''){ msg.className='msg err'; msg.textContent='Escribí la cantidad'; inp.focus(); return; }
  msg.className='msg'; msg.textContent='Guardando...';
  try{
    var r=await fetch('/api/inventario/cuadre', _opts('POST', {
      codigo_mp:l.codigo_mp, lote:l.lote||'', fisico:parseFloat(v),
      motivo:motivo||'', token:_tok(), estanteria:EST, nombre:l.nombre}));
    var d=await r.json();
    if(!r.ok){ msg.className='msg err'; msg.textContent=d.error||'No se pudo'; return; }
    document.getElementById('sis-'+id).textContent=(parseFloat(d.stock)||0).toLocaleString('es-CO');
    l.stock_sistema=d.stock;
    document.getElementById('row-'+id).classList.add('ok');
    msg.className='msg ok'; msg.textContent=d.sin_cambio?'Cuadrado':(d.mensaje||'Ajustado');
    HECHOS++; pintarProg();
    document.getElementById('pie-msg').textContent=l.nombre+(l.lote?(' · '+l.lote):'')+': '+(d.sin_cambio?'coincide':(d.mensaje||'ajustado'));
  }catch(e){ msg.className='msg err'; msg.textContent='Sin conexión'; }
}

async function ubicarAqui(id){
  var l=DATOS_MAP[id]; if(!l||!EST) return;
  var msg=document.getElementById('msg-'+id);
  msg.className='msg'; msg.textContent='Ubicando...';
  try{
    var r=await fetch('/api/lotes/'+encodeURIComponent(l.codigo_mp)+'/'+encodeURIComponent(l.lote||'_SIN_LOTE_')+'/ubicacion',
      _opts('PATCH', {estanteria:EST, motivo:'ubicado durante el cuadre'}));
    var d=await r.json();
    if(!r.ok){ msg.className='msg err'; msg.textContent=d.error||'No se pudo ubicar'; return; }
    msg.className='msg ok'; msg.textContent='Ubicado en '+EST;
    var chip=document.querySelector('#row-'+id+' .chip-sinubic'); if(chip) chip.remove();
  }catch(e){ msg.className='msg err'; msg.textContent='Sin conexion'; }
}

async function abrirUbic(){
  document.getElementById('ov-ubic').classList.add('on');
  var box=document.getElementById('ubic-lista');
  box.innerHTML='<div class="vacio">Buscando&hellip;</div>';
  try{
    var r=await fetch('/api/inventario/ubicaciones-agrupadas',{credentials:'same-origin'});
    var d=await r.json();
    var g=(d&&d.grupos)||[];
    if(!g.length){ box.innerHTML='<div class="vacio">Ninguna ubicaci&oacute;n est&aacute; partida: todas se escriben de una sola forma.</div>'; return; }
    box.innerHTML=g.map(function(x,i){
      var opts=x.variantes.map(function(v){return '<option value="'+esc(v.nombre)+'"'+(v.nombre===x.sugerida?' selected':'')+'>'+esc(v.nombre)+' ('+v.lotes+')</option>';}).join('');
      return '<div style="border:1px solid var(--cx-hairline);border-radius:12px;padding:12px;margin-bottom:10px">'
        +'<div style="font-weight:800;font-size:14px">'+x.variantes.map(function(v){return esc(v.nombre)+' <span style="font-weight:600;color:var(--cx-text-mute)">('+v.lotes+')</span>';}).join(' &nbsp;+&nbsp; ')+'</div>'
        +'<div style="font-size:12px;color:var(--cx-text-mute);margin:6px 0">'+x.lotes+' lote(s) repartidos en '+x.variantes.length+' formas de escribirlo</div>'
        +'<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">'
        +'<span style="font-size:12px;font-weight:700">Queda como:</span>'
        +'<select id="u-sel-'+i+'" class="cx-input" style="max-width:260px">'+opts+'</select>'
        +'<button class="cx-btn cx-btn-sm cx-btn-grad" onclick="unificar('+i+')">Unificar</button>'
        +'<span class="msg" id="u-msg-'+i+'"></span></div></div>';
    }).join('');
    window._UBIC=g;
  }catch(e){ box.innerHTML='<div class="vacio">No se pudo consultar.</div>'; }
}
function cerrarUbic(){ document.getElementById('ov-ubic').classList.remove('on'); }

async function unificar(i){
  var g=(window._UBIC||[])[i]; if(!g) return;
  var canonica=document.getElementById('u-sel-'+i).value;
  var msg=document.getElementById('u-msg-'+i);
  var variantes=g.variantes.map(function(v){return v.nombre;}).filter(function(n){return n!==canonica;});
  if(!confirm('Todo lo que está en ' + variantes.join(', ') + ' pasa a llamarse "' + canonica + '". No se mueve material.')) return;
  msg.className='msg'; msg.textContent='Unificando...';
  try{
    var r=await fetch('/api/inventario/unificar-ubicacion', _opts('POST', {canonica:canonica, variantes:variantes}));
    var d=await r.json();
    if(!r.ok){ msg.className='msg err'; msg.textContent=d.error||'No se pudo'; return; }
    msg.className='msg ok'; msg.textContent='Listo · '+d.movidos+' movimiento(s)';
    cargarEstanterias();
  }catch(e){ msg.className='msg err'; msg.textContent='Sin conexión'; }
}

async function abrirAlta(){
  document.getElementById('a-est').value=EST||'';
  document.getElementById('a-msg').textContent='';
  var sel=document.getElementById('a-cod');
  if(!sel.options.length){
    try{
      var r=await fetch('/api/maestro-mps',{credentials:'same-origin'});
      var d=await r.json(); var arr=(d&&(d.items||d.mps))||(Array.isArray(d)?d:[]);
      sel.innerHTML=arr.map(function(m){var cod=m.codigo_mp||m.codigo||'';return '<option value="'+esc(cod)+'">'+esc((m.nombre||cod))+' · '+esc(cod)+'</option>';}).join('');
    }catch(e){ sel.innerHTML='<option value="">(no se pudo cargar el maestro)</option>'; }
  }
  document.getElementById('ov-alta').classList.add('on');
}
function cerrarAlta(){ document.getElementById('ov-alta').classList.remove('on'); }
document.addEventListener('keydown', function(e){ if(e.key==='Escape'){ cerrarAlta(); cerrarUbic(); } });

async function guardarAlta(){
  var msg=document.getElementById('a-msg');
  function val(id){ var e=document.getElementById(id); return e?(e.value||'').trim():''; }
  var cod=val('a-cod'), cant=val('a-cant'), motivo=val('a-motivo');
  if(!cod){ msg.className='msg err'; msg.textContent='Elegí el material'; return; }
  if(cant===''){ msg.className='msg err'; msg.textContent='Falta la cantidad'; return; }
  if(!motivo){ msg.className='msg err'; msg.textContent='Decí de dónde salió'; return; }
  msg.className='msg'; msg.textContent='Guardando...';
  try{
    var r=await fetch('/api/inventario/cuadre', _opts('POST', {
      codigo_mp:cod, lote:val('a-lote'), fisico:parseFloat(cant), motivo:motivo,
      token:_tok(), estanteria:val('a-est'), vence:val('a-vence')}));
    var d=await r.json();
    if(!r.ok){ msg.className='msg err'; msg.textContent=d.error||'No se pudo'; return; }
    cerrarAlta(); cargarMateriales();
    document.getElementById('pie-msg').textContent='Dado de alta: '+cod+' · '+cant;
  }catch(e){ msg.className='msg err'; msg.textContent='Sin conexión'; }
}

cargarEstanterias();
</script>
<script src="/static/cortex.js?v=eos3"></script>
</body></html>'''
