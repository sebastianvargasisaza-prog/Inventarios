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
.gbox{margin-top:10px;border:1px solid var(--cx-info-light);background:var(--cx-info-pale);border-radius:11px;padding:11px 13px}
.gtit{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.4px;color:var(--cx-info-text);margin-bottom:7px}
.grow{display:flex;gap:11px;align-items:flex-start;padding:5px 0;border-top:1px solid var(--cx-info-light)}
.grow:first-of-type{border-top:0}
.gdet{font-size:12px;color:var(--cx-text-soft);line-height:1.45}
.gmsg{margin-top:9px;font-size:12.5px;color:var(--cx-text-mute)}

    .sug{grid-column:1/-1;font-size:11.5px;font-weight:700;color:var(--cx-warn-text);background:var(--cx-warn-pale);border:1px solid var(--cx-warn-light);border-radius:8px;padding:4px 9px;margin-top:5px}
    .edit{grid-column:1/-1;margin-top:8px;padding:11px 12px;background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:11px}
    .edgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:9px}
    .edf{display:flex;flex-direction:column;gap:3px;font-size:11px;font-weight:700;color:var(--cx-text-mute)}
    .edf span{text-transform:uppercase;letter-spacing:.3px}
    .edacc{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:9px;flex-wrap:wrap}
    .edmsg{font-size:11.5px;color:var(--cx-text-mute)}

body{font-family:"Inter",system-ui,-apple-system,Arial,sans-serif;background:var(--cx-bg);color:var(--cx-text);margin:0;padding:18px 2vw 90px}
.wrap{width:96vw;max-width:1500px;margin:0 auto}
.hero{display:flex;align-items:center;gap:14px;margin-bottom:6px}
.hero .ic{width:46px;height:46px;border-radius:14px;background:var(--cx-primary-grad);display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0}
.hero h1{margin:0;font-size:21px;font-weight:800;letter-spacing:-.02em}
.hero .nav{margin-left:auto;display:flex;gap:8px}
.sub{color:var(--cx-text-soft);font-size:13px;margin:2px 0 14px;max-width:900px;line-height:1.5}
.card{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:16px;padding:14px 16px;margin-bottom:14px;box-shadow:0 1px 3px rgba(15,23,42,.04)}
.ests{display:flex;gap:8px;flex-wrap:wrap}
.apart{margin:10px 0 0;padding:12px 14px;border:1px solid var(--cx-warn,#f59e0b);border-radius:12px;background:var(--cx-warn-pale,#fffbeb)}
.apart .ap-t{font-weight:800;font-size:14px;color:var(--cx-warn-text,#92400e);margin-bottom:4px}
.apart .ap-d{font-size:12px;color:var(--cx-text-mute,#6b7280);margin-bottom:6px}
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
.lote.rev{background:var(--cx-success-pale);border-left:3px solid var(--cx-success-light)}
.chip-rev{font-size:10.5px;font-weight:800;color:var(--cx-success-text);background:var(--cx-card);
  border:1px solid var(--cx-success-light);border-radius:999px;padding:2px 9px;white-space:nowrap;
  margin-left:8px}
.barra-fin{display:flex;gap:9px;flex-wrap:wrap;align-items:center;margin:12px 0}
.b-fin{border:none;border-radius:10px;padding:9px 18px;font-size:13px;font-weight:800;
  cursor:pointer;font-family:inherit;background:var(--cx-success-pale);
  color:var(--cx-success-text);border:1px solid var(--cx-success-light)}
.b-falta{border:1px solid var(--cx-border);background:var(--cx-card);color:var(--cx-text-soft);
  border-radius:10px;padding:8px 14px;font-size:12.5px;font-weight:700;cursor:pointer;
  font-family:inherit}
.b-falta.on{border-color:var(--cx-warn-light);background:var(--cx-warn-pale);
  color:var(--cx-warn-text)}
.cierre{border:1px solid var(--cx-warn-light);background:var(--cx-warn-pale);border-radius:14px;
  padding:15px 18px;margin:12px 0}
.cierre.todo{border-color:var(--cx-success-light);background:var(--cx-success-pale)}
.cierre-t{font-size:15px;font-weight:800;color:var(--cx-warn-text);margin-bottom:3px}
.cierre.todo .cierre-t{color:var(--cx-success-text)}
.cierre-s{font-size:12.5px;color:var(--cx-text-soft);margin-bottom:12px;line-height:1.5}
.pend{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;
  background:var(--cx-card);border:1px solid var(--cx-border);border-radius:10px;
  padding:9px 13px;margin-bottom:6px}
.pend-n{font-size:12.5px;color:var(--cx-text)}
.pend-m{font-size:11.5px;color:var(--cx-text-mute)}
.pend input{width:92px;padding:5px 8px;border:1px solid var(--cx-border);border-radius:8px;
  font-size:12.5px;font-family:inherit;text-align:right}
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
    <div id="aviso-partidas" class="apart" style="display:none"></div>
    <div class="barra">
      <input id="q" class="cx-input" type="search" placeholder="Buscar material o lote en TODO el inventario..." autocomplete="off" oninput="filtrar()" title="Filtra esta estanteria; si no esta aca, busca en todo el inventario y te dice donde">
      <button class="cx-btn cx-btn-ghost cx-btn-sm" onclick="abrirAlta()">+ Est&aacute; en el estante y no aparece</button>
      <button class="cx-btn cx-btn-ghost cx-btn-sm" onclick="abrirUbic()" title="La misma estanteria escrita de varias formas parte el inventario en pedazos">&#129513; Unificar ubicaciones</button>
      <span class="prog" id="prog"></span>
    </div>
    <div id="busca-global"></div>
  </div>
<div class="barra-fin">
  <button class="b-fin" onclick="acabe()" title="Dice que lotes de esta vista no se declararon todavia">&#10003; Acab&eacute; &middot; qu&eacute; me falt&oacute;</button>
  <button class="b-falta" id="b-falta" onclick="verSoloFalta()">Ver solo lo que falta</button>
  <a class="b-falta" href="/planta/cuadre-informe" target="_blank" style="text-decoration:none;display:inline-block" title="El cierre de TODO el inventario: lo que se encontro, lo que no, y la lista para ir a buscar">&#128203; Informe de cierre</a>
</div>
<div id="cierre" style="display:none"></div>

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

// El orden de la BODEGA, no el del diccionario: la 2 va antes que la 10. Ordenar como
// texto daba "10 11 12 13 14 2 3 4..." y quien camina el pasillo no sabe cual sigue.
// Lo que empieza con numero va primero y por NUMERO; el resto por nombre; sin ubicar al final.
function _ordenEstanteria(nom){
  var t=String(nom||'').trim();
  if(/^sin estanter/i.test(t)) return [3,0,''];
  var m=t.match(/^(\d+)/);
  if(m) return [0, parseInt(m[1],10), t.toLowerCase()];
  return [1,0,t.toLowerCase()];
}
function _cmpEstanteria(a,b){
  var x=_ordenEstanteria(a.estanteria), y=_ordenEstanteria(b.estanteria);
  if(x[0]!==y[0]) return x[0]-y[0];
  if(x[1]!==y[1]) return x[1]-y[1];
  return x[2]<y[2]? -1 : (x[2]>y[2]? 1 : 0);
}

// Mismo criterio que la herramienta de unificar (sin mayusculas, sin acentos, sin
// puntuacion, sin el plural final), asi lo que se avisa aca se puede resolver ahi mismo.
// Los numeros no se tocan: la 1 y la 10 son estanterias distintas.
function _claveUbic(v){
  var t=String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  t=t.replace(/[^a-zA-Z0-9]+/g,' ').trim().toLowerCase();
  // Palabra por palabra y con el MISMO criterio que `_ubic_norm` del servidor: si la
  // pantalla agrupara distinto, avisaria de un grupo que el endpoint despues rechaza.
  return t.split(' ').map(function(w){
    if(w.length>3 && w.charAt(w.length-1)==='s' && !/\d/.test(w.charAt(w.length-2))) return w.slice(0,-1);
    return w;
  }).join(' ');
}
function _avisoPartidas(d){
  var caja=document.getElementById('aviso-partidas'); if(!caja) return;
  var g={};
  d.forEach(function(e){
    var nom=e.estanteria; if(/^sin estanter/i.test(nom)) return;
    var k=_claveUbic(nom); if(!k) return;
    if(!g[k]) g[k]={nombres:[],mats:0};
    g[k].nombres.push(nom); g[k].mats+=(e.total_mps||0);
  });
  var part=Object.keys(g).filter(function(k){ return g[k].nombres.length>1; });
  if(!part.length){ caja.innerHTML=''; caja.style.display='none'; return; }
  var mats=0, det=[];
  part.forEach(function(k){ mats+=g[k].mats; det.push('<b>'+esc(g[k].nombres.join(' / '))+'</b>'); });
  caja.style.display='';
  caja.innerHTML='<div class="ap-t">&#9888; '+part.length+' ubicaci'
    +(part.length===1?'&oacute;n est&aacute;':'ones est&aacute;n')+' escrita'
    +(part.length===1?'':'s')+' de varias formas &middot; '+mats+' material(es) repartidos</div>'
    +'<div class="ap-d">'+det.join(' &middot; ')+'</div>'
    +'<div class="ap-d">Es el mismo lugar y sale como botones distintos: quien camina ah&iacute; s&oacute;lo abre uno.</div>'
    +'<button class="cx-btn cx-btn-sm cx-btn-grad" onclick="abrirUbic()">&#129513; Unificarlas ahora</button>';
}

async function cargarEstanterias(){
  try{
    var r=await fetch('/api/conteo/estanterias?tipo_material=MP',{credentials:'same-origin'});
    var d=await r.json();
    var box=document.getElementById('ests');
    if(!Array.isArray(d)||!d.length){ box.innerHTML='<span class="vacio">No hay estanter&iacute;as cargadas.</span>'; return; }
    d=d.slice().sort(_cmpEstanteria);
    box.innerHTML=d.map(function(e){
      var nom=e.estanteria, sinUbic=/^sin estanter/i.test(nom);
      return '<button class="est'+(sinUbic?' pend':'')+'" data-est="'+esc(e.estanteria)+'" onclick="elegir(this,\''+esc(e.estanteria).replace(/'/g,"\\'")+'\')">'
        +(sinUbic?'&#128205; Sin ubicaci&oacute;n &middot; para ubicar':esc(nom))+'<span class="n">'+(e.total_mps||0)+'</span></button>';
    }).join('');
    _avisoPartidas(d);
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
      // Lo revisado HOY sale del audit_log, asi que sobrevive al refresco y vale aunque
      // revisen entre dos personas. Sin esto la fila se ve identica a una sin tocar.
      var _rv = l.revisado_hoy
        ? ('<span class="chip-rev" title="Ya se declaro en esta jornada">&#10003; '
           + esc(l.revisado_como||'revisado')
           + (l.revisado_hora?(' '+esc(l.revisado_hora)):'')
           + (l.revisado_por?(' &middot; '+esc(l.revisado_por)):'') + '</span>')
        : '';
      html+='<div class="lote'+(l.revisado_hoy?' rev':'')+'" id="row-'+id+'" data-rev="'
        +(l.revisado_hoy?'1':'0')+'">'
        +'<div class="id"><b>'+(l.lote?esc(l.lote):'<span style="color:var(--cx-text-mute)">sin lote</span>')+'</b>'+_rv
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
        +'<button class="cx-btn cx-btn-sm cx-btn-ghost" onclick="editar(\''+id+'\')" title="Corregir lote, vencimiento, INCI o ubicacion">&#9998; Editar</button>'
        +'</div><span class="msg" id="msg-'+id+'"></span>'
        + _sugUbic(l)
        + '<div class="edit" id="ed-'+id+'" style="display:none"></div></div>';
      DATOS_MAP[id]=l;
    });
    html+='</div>';
  });
  cont.innerHTML=html;
  filtrar(); pintarProg();
}
var DATOS_MAP={};

// «Esto tambien esta en otra parte»: viaja con los lotes, no detras de un clic. Parado frente
// al estante es cuando se puede resolver -- despues nadie vuelve (Sebastian 21-ago).
function _sugUbic(l){
  var o=(l.otras_ubic||[]);
  if(!o.length) return '';
  var d=o.map(function(u){ return esc(u.estanteria)+' ('+Number(u.g||0).toLocaleString('es-CO')+' g)'; }).join(' &middot; ');
  return '<div class="sug">&#9888; Este material tambi&eacute;n est&aacute; en: '+d+'</div>';
}

// El panel de edicion: cada campo guarda por su cuenta al salir, contra el endpoint que YA
// existe para ese dato. Un endpoint nuevo que los junte duplicaria la mutacion (M3).
function editar(id){
  var box=document.getElementById('ed-'+id); if(!box) return;
  if(box.style.display!=='none'){ box.style.display='none'; return; }
  var l=DATOS_MAP[id]||{};
  box.style.display='block';
  box.innerHTML=
     '<div class="edgrid">'
    +_campo(id,'lote','N&uacute;mero de lote', l.lote||'', 'el del envase')
    +_campo(id,'vence','Vence', (l.fecha_vencimiento||'').substring(0,10), 'aaaa-mm-dd','date')
    +_campo(id,'est','Ubicaci&oacute;n', l.estanteria||'', 'estanteria')
    +_campo(id,'pos','Posici&oacute;n', l.posicion||'', 'opcional')
    +_campo(id,'inci','INCI (identidad qu&iacute;mica)', l.nombre_inci||'', 'nombre INCI')
    +'</div>'
    +'<div class="edacc">'
    +'<span class="edmsg" id="edmsg-'+id+'">Cada campo se guarda al salir de &eacute;l.</span>'
    +'<button class="cx-btn cx-btn-sm cx-btn-ghost" style="color:var(--cx-danger-text)" onclick="borrarLote(\''+id+'\')" title="Borra el lote del kardex. Si el material se uso, mejor declarar que ya no esta con &quot;No existe&quot;.">&#128465; Eliminar lote</button>'
    +'</div>';
}
function _campo(id,k,lbl,val,ph,tipo){
  return '<label class="edf"><span>'+lbl+'</span>'
    +'<input class="cx-input" type="'+(tipo||'text')+'" id="ed-'+k+'-'+id+'" value="'+esc(val)+'" placeholder="'+esc(ph||'')+'" '
    +'onchange="guardarCampo(\''+id+'\',\''+k+'\')"></label>';
}
function _edmsg(id,txt,err){
  var e=document.getElementById('edmsg-'+id); if(!e) return;
  e.textContent=txt; e.style.color= err? 'var(--cx-danger-text)':'var(--cx-success-text)';
}
async function guardarCampo(id,k){
  var l=DATOS_MAP[id]; if(!l) return;
  var el=document.getElementById('ed-'+k+'-'+id); if(!el) return;
  var v=(el.value||'').trim();
  var cod=encodeURIComponent(l.codigo_mp||''), lote=encodeURIComponent(l.lote||'_SIN_LOTE_');
  var url='', body={}, metodo='PUT';
  if(k==='lote'){ url='/api/lotes/'+cod+'/'+lote+'/codigo-lote'; body={lote_nuevo:v}; }
  else if(k==='vence'){ url='/api/lotes/'+cod+'/'+lote+'/fecha-vencimiento'; body={fecha_vencimiento:v, motivo:'Correccion desde el cuadre de inventario'}; }
  else if(k==='est'||k==='pos'){
    var est=(document.getElementById('ed-est-'+id)||{}).value||'';
    var pos=(document.getElementById('ed-pos-'+id)||{}).value||'';
    url='/api/lotes/'+cod+'/'+lote+'/ubicacion'; body={estanteria:est.trim(), posicion:pos.trim()};
  }
  else if(k==='inci'){ url='/api/inventario/mp/'+cod+'/inci'; body={nombre_inci:v}; }
  else return;
  _edmsg(id,'Guardando...');
  try{
    var r=await fetch(url,_opts(metodo,body));
    var d=await r.json();
    if(!r.ok||d.error){ _edmsg(id, d.error||('Error '+r.status), true); return; }
    // El lote es la LLAVE: si cambio, las proximas ediciones tienen que ir contra el nuevo,
    // o el segundo cambio se aplicaria a un lote que ya no existe.
    if(k==='lote'&&v) l.lote=v;
    if(k==='est') l.estanteria=(document.getElementById('ed-est-'+id)||{}).value||'';
    if(k==='pos') l.posicion=(document.getElementById('ed-pos-'+id)||{}).value||'';
    if(k==='vence') l.fecha_vencimiento=v;
    if(k==='inci') l.nombre_inci=v;
    _edmsg(id,'&#10003; guardado'.replace('&#10003;','\u2713'));
  }catch(e){ _edmsg(id,'No se pudo guardar: '+e, true); }
}
async function borrarLote(id){
  var l=DATOS_MAP[id]; if(!l) return;
  if(!confirm('Borrar del kardex el lote '+(l.lote||'(sin lote)')+' de '+(l.nombre||l.codigo_mp)+'?\n\nSi el material se USO, es mejor declarar que ya no esta con el boton "No existe": eso deja el consumo registrado. Borrar quita el rastro.')) return;
  var cod=encodeURIComponent(l.codigo_mp||''), lote=encodeURIComponent(l.lote||'_SIN_LOTE_');
  _edmsg(id,'Borrando...');
  try{
    var r=await fetch('/api/lotes/'+cod+'/'+lote,_opts('DELETE'));
    var d=await r.json();
    if(!r.ok||d.error){ _edmsg(id, d.error||('Error '+r.status), true); return; }
    var row=document.getElementById('row-'+id); if(row) row.remove();
  }catch(e){ _edmsg(id,'No se pudo borrar: '+e, true); }
}


function pintarProg(){
  // El conteo sale de lo que el audit_log dice que se revisó HOY, mas lo que se apreto recien
  // en esta pestaña. Antes contaba SOLO lo segundo: con la estanteria entera declarada decia
  // "0 de 54", y ahi es donde se pierde el trabajo hecho.
  var tot=Object.keys(DATOS_MAP).length;
  var yaHoy=0;
  for(var k in DATOS_MAP){
    if(Object.prototype.hasOwnProperty.call(DATOS_MAP,k) && DATOS_MAP[k].revisado_hoy) yaHoy++;
  }
  var e=document.getElementById('prog');
  if(!tot){ e.textContent=''; return; }
  e.textContent = yaHoy + ' de ' + tot + ' revisados hoy'
    + ((tot-yaHoy) ? (' \u00b7 faltan ' + (tot-yaHoy)) : '');
}
// ── "Acabe" · que lotes no se vieron · Sebastian 22-ago-2026 ────────────────────────
// "Lo mas importante es que si digo acabe me diga: estos lotes, donde estan, no los
// encontraste". Una lista que solo se puede leer manda a empezar de nuevo (M121), asi que
// cada pendiente se resuelve ahi mismo.
function _pendientes(){
  var out=[];
  for(var k in DATOS_MAP){
    if(!Object.prototype.hasOwnProperty.call(DATOS_MAP,k)) continue;
    if(!DATOS_MAP[k].revisado_hoy) out.push({id:k, l:DATOS_MAP[k]});
  }
  return out;
}
function acabe(){
  var p=_pendientes();
  var cont=document.getElementById('cierre');
  if(!cont) return;
  if(!p.length){
    cont.innerHTML='<div class="cierre todo"><div class="cierre-t">&#10003; No qued&oacute; '
      + 'nada sin revisar</div><div class="cierre-s">Los '+Object.keys(DATOS_MAP).length
      + ' lote(s) de esta vista est&aacute;n declarados. Lo que corregiste ya est&aacute; en el '
      + 'inventario.</div><button class="b-falta" onclick="cerrarCierre()">Cerrar</button></div>';
    cont.style.display='';
    cont.scrollIntoView({behavior:'smooth'});
    return;
  }
  var h='<div class="cierre"><div class="cierre-t">&#9888; Estos no los viste &middot; '
    + p.length + ' lote(s)</div>'
    + '<div class="cierre-s">&iquest;D&oacute;nde est&aacute;n? Si no los encontraste, marc&aacute; '
    + '<b>No existe</b> y el lote queda en CERO con su motivo. Si estaban y coinciden, '
    + '<b>= Igual</b>. Si hay otra cantidad, escribila.</div>';
  p.forEach(function(x){
    var l=x.l;
    h+='<div class="pend" id="pend-'+esc(x.id)+'">'
      +'<div><div class="pend-n"><b>'+esc(l.nombre||l.codigo_mp)+'</b> &middot; lote '
      +esc(l.lote||'sin lote')+'</div>'
      +'<div class="pend-m">'+(parseFloat(l.stock_sistema)||0).toLocaleString('es-CO')+' g'
      +(l.posicion?(' &middot; pos. '+esc(l.posicion)):'')
      +(l.sin_ubicar?' &middot; sin ubicar':(EST?(' &middot; '+esc(EST)):''))
      +(l.fecha_vencimiento?(' &middot; vence '+esc(l.fecha_vencimiento)):'')+'</div></div>'
      +'<div class="acc">'
      +'<button class="cx-btn cx-btn-sm cx-btn-ghost" onclick="igual(\''+x.id+'\')">= Igual</button>'
      +'<button class="cx-btn cx-btn-sm cx-btn-ghost" onclick="noExiste(\''+x.id+'\')">No existe</button>'
      +'<input type="number" step="0.001" min="0" placeholder="hay" '
      +'onkeydown="if(event.key===\'Enter\'){document.getElementById(\'in-'+x.id+'\').value=this.value;guardar(\''+x.id+'\')}">'
      +'</div><span class="msg" id="pmsg-'+esc(x.id)+'"></span></div>';
  });
  h+='<div style="margin-top:11px"><button class="b-falta" onclick="cerrarCierre()">Volver a la '
    + 'lista</button></div></div>';
  cont.innerHTML=h;
  cont.style.display='';
  cont.scrollIntoView({behavior:'smooth'});
}
function cerrarCierre(){
  var c=document.getElementById('cierre'); if(c){ c.innerHTML=''; c.style.display='none'; }
}
function _sacarDePendientes(id){
  // Declarar desde el cierre lo saca de la lista: si siguiera ahi, la persona no sabria cual
  // ya cerro y volveria a buscarlo (M129).
  var e=document.getElementById('pend-'+id); if(e) e.remove();
  var c=document.getElementById('cierre');
  if(c && c.style.display!=='none' && !c.querySelector('.pend')) acabe();
}
function verSoloFalta(){
  var b=document.getElementById('b-falta');
  var on=!b.classList.contains('on');
  b.classList.toggle('on', on);
  b.textContent = on ? 'Viendo solo lo que falta' : 'Ver solo lo que falta';
  document.querySelectorAll('.lote').forEach(function(el){
    el.style.display = (on && el.dataset.rev==='1') ? 'none' : '';
  });
}
var _BUSCA_T=null;
function filtrar(){
  var q=(document.getElementById('q').value||'').trim().toLowerCase();
  var visibles=0;
  document.querySelectorAll('.mat').forEach(function(el){
    var oculto = !!q && (el.dataset.buscar||'').indexOf(q)<0;
    el.classList.toggle('oculto', oculto);
    if(!oculto) visibles++;
  });
  // Si lo que busca NO esta en esta estanteria, se busca en TODO el inventario. Sin esto,
  // "no aparece nada" significa dos cosas distintas -- no existe, o esta en otro estante -- y
  // desde la silla se leen igual (M100). Con retardo: una consulta por tecla satura los
  // tres workers (M43).
  var av=document.getElementById('busca-global');
  if(av) av.innerHTML='';
  if(_BUSCA_T){ clearTimeout(_BUSCA_T); _BUSCA_T=null; }
  if(q.length>=3 && visibles===0){
    if(av) av.innerHTML='<div class="gmsg">Buscando en todo el inventario...</div>';
    _BUSCA_T=setTimeout(function(){ buscarGlobal(q); }, 350);
  }
}
async function buscarGlobal(q){
  var av=document.getElementById('busca-global'); if(!av) return;
  try{
    var r=await fetch('/api/inventario/cuadre-lotes?q='+encodeURIComponent(q),{credentials:'same-origin'});
    var d=await r.json();
    if(!r.ok||d.error){ av.innerHTML='<div class="gmsg">No se pudo buscar: '+esc(d.error||r.status)+'</div>'; return; }
    var ls=(d.lotes||[]);
    if(!ls.length){
      av.innerHTML='<div class="gmsg">No hay ning&uacute;n lote con stock que coincida con "'+esc(q)+'" en todo el inventario.</div>';
      return;
    }
    // Se agrupa por ubicacion: lo que se necesita saber es A DONDE ir.
    var porEst={};
    ls.forEach(function(l){
      var k=(l.estanteria||'').trim() || '\u2014 sin ubicar';
      (porEst[k]=porEst[k]||[]).push(l);
    });
    var h='<div class="gbox"><div class="gtit">'+ls.length+' lote(s) fuera de esta estanter&iacute;a</div>';
    Object.keys(porEst).sort().forEach(function(k){
      var real=(k.indexOf('sin ubicar')>=0)?'':k;
      h+='<div class="grow"><button class="cx-btn cx-btn-sm cx-btn-ghost" onclick="irA('+JSON.stringify(real).replace(/"/g,'&quot;')+')">'+esc(k)+'</button>';
      h+='<span class="gdet">'+porEst[k].map(function(l){
            return esc(l.nombre||l.codigo_mp)+' &middot; '+esc(l.lote||'sin lote')+' &middot; '+Number(l.stock_sistema||0).toLocaleString('es-CO')+' g';
          }).join('<br>')+'</span></div>';
    });
    av.innerHTML=h+'</div>';
  }catch(e){ av.innerHTML='<div class="gmsg">No se pudo buscar: '+esc(String(e))+'</div>'; }
}
function irA(est){
  var b=document.querySelector('.est[data-est="'+(est||'').replace(/"/g,'\\"')+'"]');
  if(b){ b.click(); return; }
  EST=est||''; cargarMateriales();
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
    // La fila queda marcada como revisada HOY sin esperar a recargar: si no, el contador y
    // el filtro dirian que sigue pendiente algo que se acaba de declarar (M5).
    l.revisado_hoy = true;
    l.revisado_como = d.sin_cambio ? 'coincide' : (parseFloat(v) > 0 ? 'ajustado' : 'no existe');
    l.revisado_por = ''; l.revisado_hora = '';
    var _row = document.getElementById('row-'+id);
    if(_row){ _row.dataset.rev='1'; _row.classList.add('rev'); }
    _sacarDePendientes(id);
    HECHOS++; pintarProg();
    document.getElementById('pie-msg').textContent=l.nombre+(l.lote?(' · '+l.lote):'')+': '+(d.sin_cambio?'coincide':(d.mensaje||'ajustado'));
  }catch(e){ msg.className='msg err'; msg.textContent='Sin conexión'; }
}

async function ubicarAqui(id){
  var l=DATOS_MAP[id]; if(!l||!EST) return;
  var msg=document.getElementById('msg-'+id);
  msg.className='msg'; msg.textContent='Ubicando...';
  try{
    // PUT, que es lo que la ruta acepta: con PATCH contestaba 405, el r.json() reventaba
    // sobre el HTML del error y la pantalla decia "Sin conexion" -- o sea que el boton
    // nunca ubico nada y encima le echaba la culpa a la red.
    var r=await fetch('/api/lotes/'+encodeURIComponent(l.codigo_mp)+'/'+encodeURIComponent(l.lote||'_SIN_LOTE_')+'/ubicacion',
      _opts('PUT', {estanteria:EST, motivo:'ubicado durante el cuadre'}));
    var d={}; try{ d=await r.json(); }catch(_je){}
    if(!r.ok){ msg.className='msg err'; msg.textContent=d.error||('No se pudo ubicar (error '+r.status+')'); return; }
    msg.className='msg ok'; msg.textContent='Ubicado en '+EST;
    // La fila tiene que quedar diciendo la verdad: si sigue mostrando la ubicacion vieja,
    // la proxima edicion se guarda contra un dato que ya no es (M129).
    l.estanteria=EST; l.sin_ubicar=false;
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
