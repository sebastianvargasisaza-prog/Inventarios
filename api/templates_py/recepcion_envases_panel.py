# -*- coding: utf-8 -*-
"""Panel de recepción de envases por LÍNEAS · vive DENTRO de /recepcion (Sebastián 30-jul).

Sebastián: *"no puede quedar todo de manera loca, pueden quedar en recepción pero como una
pestaña para recepcionar este tipo de cosas"*. Nació como página aparte
(`/planta/recepcion-envases`) y estaba en el lugar equivocado: el punto de entrada lo define el
TIPO de cosa que llega, no la feature que la construyó.

Está en su propio módulo y se INYECTA una sola vez en `RECEPCION_HTML` (con assert en el
caller): dos copias del mismo panel divergen y la que queda vieja es la que alguien usa.

⚠ Todo va prefijado (`env-` en los ids, `env` en las funciones) porque comparte documento con
la página de recepción, que ya tiene su propia `esc()`: una segunda declaración con el mismo
nombre pisa la primera y rompe la pantalla ajena sin un solo error (M59).
"""

PANEL_ENVASES_HTML = r'''
<style>
#rt-env .env-card{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:14px;padding:18px 20px;margin-bottom:16px}
#rt-env .env-card h3{margin:0 0 14px;font-size:15px;font-weight:800;color:var(--cx-primary-text)}
#rt-env .env-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
#rt-env label{display:block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--cx-text-mute);margin-bottom:5px}
#rt-env input,#rt-env textarea{width:100%;box-sizing:border-box;padding:9px 11px;border:1px solid var(--cx-border);border-radius:8px;background:var(--cx-bg-soft);color:var(--cx-text);font-size:13px;font-family:inherit}
#rt-env textarea{min-height:110px;resize:vertical;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px}
#rt-env table{width:100%;border-collapse:collapse;font-size:13px}
#rt-env th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--cx-text-mute);padding:8px;border-bottom:1px solid var(--cx-border)}
#rt-env td{padding:6px 8px;border-bottom:1px solid var(--cx-border-soft);vertical-align:middle}
#rt-env td input{padding:7px 9px;font-size:12.5px}
#rt-env .env-btn{border:none;border-radius:9px;padding:10px 18px;font-size:13px;font-weight:700;cursor:pointer;background:var(--cx-primary-grad);color:#fff}
#rt-env .env-btn:disabled{opacity:.45;cursor:not-allowed}
#rt-env .env-btn.ghost{background:transparent;border:1px solid var(--cx-primary-light);color:var(--cx-primary-text)}
#rt-env .env-btn.warn{background:var(--cx-warn-pale);color:var(--cx-warn-text);border:1px solid var(--cx-warn)}
#rt-env .env-chip{display:inline-block;border-radius:999px;padding:2px 9px;font-size:10.5px;font-weight:800}
#rt-env .env-chip.ok{background:var(--cx-success-pale);color:var(--cx-success-text)}
#rt-env .env-chip.no{background:var(--cx-danger-pale);color:var(--cx-danger-text)}
#rt-env .env-kpi{display:flex;gap:26px;flex-wrap:wrap;margin-top:12px}
#rt-env .env-kpi div span{display:block;font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.06em}
#rt-env .env-kpi div b{font-size:22px;font-weight:800}
#rt-env .env-aviso{background:var(--cx-warn-pale);color:var(--cx-warn-text);border-radius:9px;padding:9px 12px;font-size:12.5px;margin-top:10px}
#rt-env .env-ok{background:var(--cx-success-pale);color:var(--cx-success-text);border-radius:10px;padding:14px 16px;font-size:13.5px;margin-top:12px}
#rt-env .env-err{background:var(--cx-danger-pale);color:var(--cx-danger-text);border-radius:10px;padding:12px 14px;font-size:13px;margin-top:12px}
#rt-env .env-acciones{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:16px}
#rt-env .env-hint{color:var(--cx-text-mute);font-size:12.5px;line-height:1.55}
</style>
<div class="env-card" style="background:var(--cx-primary-pale);border-left:4px solid var(--cx-primary)">
  <div class="env-hint"><b>&#128230; Para material que llega SIN orden de compra en EOS</b> (un contenedor
  que pidi&oacute; otra persona, por ejemplo). Se cuenta por <b>CAJAS</b> y el sistema calcula las unidades.
  Todo entra en <b>cuarentena</b>: Calidad lo libera con el F01 revisando caja por caja, y hasta entonces
  no cuenta como stock disponible.</div>
</div>

<div class="env-card"><h3>1. De d&oacute;nde viene</h3>
<div class="env-grid">
  <div><label>Proveedor</label><input id="env-prov" placeholder="Proveedor"></div>
  <div><label>Factura o remisi&oacute;n</label><input id="env-fact" placeholder="IMP-2026-00"></div>
  <div><label>Zona / ubicaci&oacute;n</label><input id="env-zona" placeholder="Bodega envases"></div>
  <div><label>Orden de compra (opcional)</label><input id="env-oc" placeholder="sin OC"></div>
</div></div>

<div class="env-card"><h3>2. Pegar el packing list</h3>
<div class="env-hint" style="margin-bottom:10px">Una l&iacute;nea por referencia: <b>c&oacute;digo, cajas,
unidades por caja, lote</b> (separados por tabulaci&oacute;n o coma). Se puede pegar directo desde Excel.</div>
<textarea id="env-pega" placeholder="MEE-IMP-019	24	200	CN-2607-A&#10;MEE-TAP-004	42	200	CN-2607-B"></textarea>
<div class="env-acciones">
  <button class="env-btn ghost" onclick="envPegar()">Cargar las l&iacute;neas</button>
  <button class="env-btn ghost" onclick="envAgregar()">+ L&iacute;nea vac&iacute;a</button>
</div></div>

<div class="env-card"><h3>3. L&iacute;neas a recibir</h3>
<div style="overflow-x:auto">
<table><thead><tr><th style="width:200px">C&oacute;digo</th><th style="width:85px">Cajas</th>
<th style="width:110px">Und/caja</th><th style="width:110px">&Uacute;ltima caja</th>
<th style="width:140px">Lote proveedor</th><th style="width:105px">Unidades</th>
<th>Maestro</th><th style="width:40px"></th></tr></thead><tbody id="env-tb"></tbody></table>
</div>
<div class="env-kpi">
  <div><span>L&iacute;neas</span><b id="env-k-l">0</b></div>
  <div><span>Cajas</span><b id="env-k-c">0</b></div>
  <div><span>Unidades</span><b id="env-k-u">0</b></div>
</div>
<div id="env-avisos"></div>
<div class="env-acciones">
  <button class="env-btn ghost" onclick="envVerificar()">Ver qu&eacute; cruza contra el maestro</button>
  <button class="env-btn warn" id="env-b-crear" onclick="envCrearFaltantes()" style="display:none">Crear los c&oacute;digos que faltan</button>
  <button class="env-btn" id="env-b-recibir" onclick="envRecibir()" disabled>Recibir en cuarentena</button>
</div>
<div id="env-msg"></div>
</div>
<script>
var ENV_FILAS=[]; var ENV_TOKEN=null; var ENV_FALTAN=[];
function envEsc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function envAgregar(f){ENV_FILAS.push(f||{codigo:'',n_cajas:'',unidades_por_caja:'',unidades_ultima_caja:'',lote:'',existe:null,descripcion:''});envPintar();}
function envQuitar(i){ENV_FILAS.splice(i,1);envPintar();}
function envSet(i,campo,v){ENV_FILAS[i][campo]=v; if(campo==='codigo'){ENV_FILAS[i].existe=null;ENV_FILAS[i].descripcion='';} envKpis();}
function envUnidades(f){
  var n=parseInt(f.n_cajas||0,10)||0, p=parseFloat(f.unidades_por_caja||0)||0;
  var u=(f.unidades_ultima_caja===''||f.unidades_ultima_caja==null)?null:parseFloat(f.unidades_ultima_caja);
  if(n>0&&p>0){return (u!=null&&u>0)?(p*(n-1)+u):(p*n);}
  return 0;
}
function envPintar(){
  var h='';
  for(var i=0;i<ENV_FILAS.length;i++){var f=ENV_FILAS[i];
    var mae = f.existe===null?'<span style="color:var(--cx-text-faint)">sin verificar</span>'
            :(f.existe?('<span class="env-chip ok">est&aacute;</span> '+envEsc(f.descripcion)):'<span class="env-chip no">no existe</span>');
    h+='<tr><td><input value="'+envEsc(f.codigo)+'" oninput="envSet('+i+',&quot;codigo&quot;,this.value)"></td>'
      +'<td><input type="number" min="1" value="'+envEsc(f.n_cajas)+'" oninput="envSet('+i+',&quot;n_cajas&quot;,this.value)"></td>'
      +'<td><input type="number" min="1" value="'+envEsc(f.unidades_por_caja)+'" oninput="envSet('+i+',&quot;unidades_por_caja&quot;,this.value)"></td>'
      +'<td><input type="number" min="1" placeholder="igual" value="'+envEsc(f.unidades_ultima_caja)+'" oninput="envSet('+i+',&quot;unidades_ultima_caja&quot;,this.value)"></td>'
      +'<td><input value="'+envEsc(f.lote)+'" oninput="envSet('+i+',&quot;lote&quot;,this.value)"></td>'
      +'<td id="env-u-'+i+'" style="font-weight:800">'+envUnidades(f).toLocaleString('es-CO')+'</td>'
      +'<td style="font-size:12px">'+mae+'</td>'
      +'<td><button class="env-btn ghost" style="padding:4px 9px" onclick="envQuitar('+i+')">x</button></td></tr>';
  }
  var tb=document.getElementById('env-tb');
  if(tb) tb.innerHTML=h||'<tr><td colspan="8" style="color:var(--cx-text-faint);padding:14px">Pega el packing list arriba o agrega una l&iacute;nea.</td></tr>';
  envKpis();
}
function envKpis(){
  var c=0,u=0,n=0;
  for(var i=0;i<ENV_FILAS.length;i++){var f=ENV_FILAS[i]; if(!String(f.codigo||'').trim())continue;
    n++; c+=parseInt(f.n_cajas||0,10)||0; u+=envUnidades(f);
    var td=document.getElementById('env-u-'+i); if(td)td.textContent=envUnidades(f).toLocaleString('es-CO');}
  var e1=document.getElementById('env-k-l'); if(e1)e1.textContent=n;
  var e2=document.getElementById('env-k-c'); if(e2)e2.textContent=c.toLocaleString('es-CO');
  var e3=document.getElementById('env-k-u'); if(e3)e3.textContent=u.toLocaleString('es-CO');
}
function envPegar(){
  var ta=document.getElementById('env-pega'); var txt=(ta&&ta.value)||'';
  var lineas=txt.split(/\r?\n/); var nuevas=[];
  for(var i=0;i<lineas.length;i++){
    var L=lineas[i].trim(); if(!L)continue;
    var p=L.split(/\t|;|,/).map(function(x){return x.trim();});
    if(!p[0])continue;
    nuevas.push({codigo:p[0],n_cajas:p[1]||'',unidades_por_caja:p[2]||'',
                 unidades_ultima_caja:(p[3]&&isFinite(p[3])&&p[4])?p[3]:'',
                 lote:(p[4]||p[3]||''),existe:null,descripcion:''});
  }
  if(!nuevas.length){alert('No se reconocio ninguna linea. Formato: codigo, cajas, unidades por caja, lote');return;}
  ENV_FILAS=nuevas; envPintar();
}
function envCuerpo(){
  var ls=[];
  for(var i=0;i<ENV_FILAS.length;i++){var f=ENV_FILAS[i]; if(!String(f.codigo||'').trim())continue;
    ls.push({codigo:f.codigo,n_cajas:parseInt(f.n_cajas||0,10)||0,
             unidades_por_caja:parseFloat(f.unidades_por_caja||0)||0,
             unidades_ultima_caja:(f.unidades_ultima_caja===''||f.unidades_ultima_caja==null)?null:parseFloat(f.unidades_ultima_caja),
             lote_proveedor:f.lote});}
  var g=function(id){var e=document.getElementById(id);return e?e.value:'';};
  return {proveedor:g('env-prov'),factura_numero:g('env-fact'),zona:g('env-zona'),
          oc_numero:g('env-oc'),lineas:ls};
}
async function envCsrf(){try{var r=await fetch('/api/csrf-token',{credentials:'same-origin'});var j=await r.json();return j.csrf_token||j.token||'';}catch(e){return '';}}
async function envVerificar(){
  var b=envCuerpo(); if(!b.lineas.length){alert('No hay lineas.');return;}
  b.preview=true;
  var t=await envCsrf();
  var r=await fetch('/api/mee/recepcion-lineas',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':t},credentials:'same-origin',body:JSON.stringify(b)});
  var j=await r.json();
  var msg=document.getElementById('env-msg');
  if(!r.ok){if(msg)msg.innerHTML='<div class="env-err">'+envEsc(j.error||'Error')+'</div>';return;}
  var porCod={}; (j.lineas||[]).forEach(function(x){porCod[String(x.codigo).trim().toUpperCase()]=x;});
  ENV_FILAS.forEach(function(f){var x=porCod[String(f.codigo||'').trim().toUpperCase()]; if(x){f.existe=!!x.existe;f.descripcion=x.descripcion||'';}});
  ENV_FALTAN=j.faltantes||[];
  var bc=document.getElementById('env-b-crear'); if(bc)bc.style.display=ENV_FALTAN.length?'inline-block':'none';
  var br=document.getElementById('env-b-recibir'); if(br)br.disabled=ENV_FALTAN.length>0;
  var av=document.getElementById('env-avisos');
  if(av)av.innerHTML=(j.avisos||[]).map(function(a){return '<div class="env-aviso">'+envEsc(a)+'</div>';}).join('');
  if(msg)msg.innerHTML=ENV_FALTAN.length
    ? '<div class="env-err">Faltan '+ENV_FALTAN.length+' codigo(s) en el maestro: '+envEsc(ENV_FALTAN.join(', '))+'. Crealos y volve a verificar.</div>'
    : '<div class="env-ok">Los '+(j.total_lineas||0)+' codigos cruzan. '+(j.total_cajas||0)+' cajas, '+(j.total_unidades||0).toLocaleString('es-CO')+' unidades listas para recibir.</div>';
  envPintar();
}
async function envCrearFaltantes(){
  if(!ENV_FALTAN.length)return;
  if(!confirm('Crear '+ENV_FALTAN.length+' codigo(s) en el maestro de envases con stock 0?'))return;
  var t=await envCsrf(); var creados=0, errores=[];
  for(var i=0;i<ENV_FALTAN.length;i++){
    var cod=ENV_FALTAN[i];
    var f=ENV_FILAS.filter(function(x){return String(x.codigo||'').trim().toUpperCase()===String(cod).toUpperCase();})[0]||{};
    var desc=prompt('Descripcion para '+cod+' (nombre del envase):',f.descripcion||'');
    if(desc===null){continue;}
    if(!String(desc).trim()){errores.push(cod+': sin descripcion');continue;}
    var r=await fetch('/api/mee',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':t},credentials:'same-origin',
        body:JSON.stringify({codigo:cod,descripcion:desc,categoria:'Envase',unidad:'und',stock_actual:0,stock_minimo:0})});
    var j=await r.json();
    if(r.ok&&!j.error){creados++;}else{errores.push(cod+': '+(j.error||r.status));}
  }
  var msg=document.getElementById('env-msg');
  if(msg)msg.innerHTML=(errores.length?'<div class="env-err">'+envEsc(errores.join(' &middot; '))+'</div>':'')
    +'<div class="env-ok">'+creados+' codigo(s) creados con stock 0. Verifica de nuevo.</div>';
  if(creados)envVerificar();
}
async function envRecibir(){
  var b=envCuerpo(); if(!b.lineas.length){alert('No hay lineas.');return;}
  if(!confirm('Recibir '+b.lineas.length+' linea(s) en CUARENTENA? Calidad las libera despues con el F01.'))return;
  if(!ENV_TOKEN){ENV_TOKEN=(window.crypto&&crypto.randomUUID)?crypto.randomUUID():('t'+Date.now()+Math.random());}
  b.recepcion_id=ENV_TOKEN;
  var btn=document.getElementById('env-b-recibir'); if(btn)btn.disabled=true;
  var t=await envCsrf();
  var r=await fetch('/api/mee/recepcion-lineas',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':t},credentials:'same-origin',body:JSON.stringify(b)});
  var j=await r.json();
  var msg=document.getElementById('env-msg');
  if(!r.ok){
    if(msg)msg.innerHTML='<div class="env-err">'+envEsc(j.error||'Error')+'</div>';
    if(btn)btn.disabled=false; return;
  }
  ENV_TOKEN=null;
  if(msg)msg.innerHTML='<div class="env-ok"><b>Recibido:</b> '+j.recibidas
    +' linea(s), '+j.total_cajas+' caja(s), '+(j.total_unidades||0).toLocaleString('es-CO')+' unidades en CUARENTENA.'
    +'<br>Calidad tiene que liberar con el F01 antes de que cuenten como stock.'
    +'<br><br><a class="env-btn" style="text-decoration:none;display:inline-block" href="'+envEsc(j.rotulos_url)+'" target="_blank">Imprimir los rotulos por caja</a></div>';
}
envPintar();
</script>
'''
