# -*- coding: utf-8 -*-
"""Panel de recepción de envases · vive DENTRO de /recepcion (Sebastián 30-jul).

**Rediseñado con el flujo del MUELLE, no el de oficina.** La v1 pedía pegar un packing list;
Sebastián, mirándola desplegada: *"creo que no quedó lo mejor (...) en ubicación podrías listar
las zonas que hay en bodega de materiales, para el nombre podría ser: ¿existe la referencia? y
colocás la lista de lo que ya existe, y si no crear nueva referencia y allí preguntás: es MEE,
vidrio, plástico, ml, etc, todo lo necesario para configurar el código. Además falta después de
eso: en cuántas cajas llegaron, escoger 15 por ejemplo y se despliegan ya autollenadas, lo único
que toca cambiar es la cantidad que viene por caja y pegarles el rótulo (...) al lado debería
aparecer opción imprimir rótulo de recepción, con código de barras que dará la trazabilidad"*.

El orden es el de la operación, UNA referencia por vez:
  1. de dónde viene + **ubicación del catálogo** (zona / estante / posición). Ese catálogo YA
     existía (`/api/mee/ubicaciones`, 9-jul); poner un texto libre ahí fue el error de la v1 —
     un campo libre que alimenta una agrupación la destruye (M115).
  2. **¿existe la referencia?** → la lista de lo que ya está; si no, se crea con el wizard que
     arma el código (`/api/mee/crear-auto` · el código lo asigna el sistema).
  3. **¿en cuántas cajas llegó?** → se despliegan N filas ya autollenadas.
  4. cada caja: su cantidad y su **rótulo con código de barras** `MEE-<recepción>-<caja>`, que
     es lo que Calidad escanea después para disponer esa caja.

⚠ Todo prefijado (`env-` / `env…`): comparte documento con la página de recepción, que ya tiene
su propia `esc()`, y una segunda declaración del mismo nombre la pisa sin un solo error (M59).
"""

PANEL_ENVASES_HTML = r'''
<style>
#rt-env .env-card{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:14px;padding:18px 20px;margin-bottom:16px}
#rt-env .env-card h3{margin:0 0 4px;font-size:15px;font-weight:800;color:var(--cx-primary-text)}
#rt-env .env-step{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;background:var(--cx-primary);color:#fff;font-size:12px;font-weight:800;margin-right:8px}
#rt-env .env-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
#rt-env label{display:block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--cx-text-mute);margin-bottom:5px}
#rt-env input,#rt-env select{width:100%;box-sizing:border-box;padding:9px 11px;border:1px solid var(--cx-border);border-radius:8px;background:var(--cx-bg-soft);color:var(--cx-text);font-size:13px;font-family:inherit}
#rt-env table{width:100%;border-collapse:collapse;font-size:13px}
#rt-env th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--cx-text-mute);padding:8px;border-bottom:1px solid var(--cx-border)}
#rt-env td{padding:7px 8px;border-bottom:1px solid var(--cx-border-soft);vertical-align:middle}
#rt-env td input{padding:8px 9px;font-size:14px;font-weight:700;max-width:130px}
#rt-env .env-btn{border:none;border-radius:9px;padding:10px 18px;font-size:13px;font-weight:700;cursor:pointer;background:var(--cx-primary-grad);color:#fff}
#rt-env .env-btn:disabled{opacity:.45;cursor:not-allowed}
#rt-env .env-btn.ghost{background:transparent;border:1px solid var(--cx-primary-light);color:var(--cx-primary-text)}
#rt-env .env-btn.mini{padding:6px 12px;font-size:12px}
#rt-env .env-kpi{display:flex;gap:26px;flex-wrap:wrap;margin-top:12px}
#rt-env .env-kpi div span{display:block;font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.06em}
#rt-env .env-kpi div b{font-size:22px;font-weight:800}
#rt-env .env-ok{background:var(--cx-success-pale);color:var(--cx-success-text);border-radius:10px;padding:14px 16px;font-size:13.5px;margin-top:12px}
#rt-env .env-err{background:var(--cx-danger-pale);color:var(--cx-danger-text);border-radius:10px;padding:12px 14px;font-size:13px;margin-top:12px}
#rt-env .env-acciones{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:14px}
#rt-env .env-hint{color:var(--cx-text-mute);font-size:12.5px;line-height:1.55}
#rt-env .env-oculto{display:none}
#rt-env .env-ref{display:flex;gap:14px;align-items:flex-start;flex-wrap:wrap}
#rt-env .env-ref > div{flex:1 1 280px}
</style>

<div class="env-card" style="background:var(--cx-primary-pale);border-left:4px solid var(--cx-primary)">
  <div class="env-hint"><b>&#128230; Material que llega SIN orden de compra en EOS.</b> Se recibe
  <b>una referencia por vez</b>, caja por caja, y cada caja sale con su r&oacute;tulo y su c&oacute;digo de
  barras. Entra <b>disponible en inventario</b> y se puede usar de una: Calidad lo revisa caja por
  caja escaneando, y lo que rechace sale del stock en ese momento.</div>
</div>

<div class="env-card">
  <h3><span class="env-step">1</span>De d&oacute;nde viene y d&oacute;nde queda</h3>
  <div class="env-hint" style="margin-bottom:12px">Se llena una vez y queda para todas las referencias del mismo contenedor.</div>
  <div class="env-grid">
    <div><label>Proveedor</label><input id="env-prov" placeholder="Proveedor"></div>
    <div><label>Factura o remisi&oacute;n</label><input id="env-fact" placeholder="IMP-2026-00"></div>
    <div><label>Zona</label><select id="env-zona"></select></div>
    <div><label>Estante</label><select id="env-est"></select></div>
    <div><label>Posici&oacute;n</label><select id="env-pos"></select></div>
    <div><label>Orden de compra (opcional)</label><input id="env-oc" placeholder="sin OC"></div>
  </div>
  <div class="env-acciones">
    <button class="env-btn ghost mini" onclick="envAgregarUbic('zona')">+ Zona nueva</button>
    <button class="env-btn ghost mini" onclick="envAgregarUbic('estante')">+ Estante</button>
    <button class="env-btn ghost mini" onclick="envAgregarUbic('posicion')">+ Posici&oacute;n</button>
  </div>
</div>

<div class="env-card">
  <h3><span class="env-step">2</span>&iquest;Existe la referencia?</h3>
  <div class="env-hint" style="margin-bottom:12px">Busc&aacute; el envase en el maestro. Si no est&aacute;, se crea ac&aacute; mismo y el sistema le asigna el c&oacute;digo.</div>
  <div class="env-ref">
    <div><label>Referencia del maestro</label>
      <input id="env-buscar" placeholder="Escrib&iacute; para filtrar (c&oacute;digo o nombre)" oninput="envFiltrar()">
      <select id="env-ref" size="6" style="margin-top:8px" onchange="envRefSel()"></select>
    </div>
    <div>
      <label>Lote del proveedor</label><input id="env-lote" placeholder="CN-2607-A">
      <div class="env-hint" style="margin:8px 0">Es el lote que Calidad necesita para el F01 y el que se imprime en el r&oacute;tulo.</div>
      <button class="env-btn ghost" onclick="envNuevaAbrir()">No existe &middot; crear referencia nueva</button>
    </div>
  </div>
  <div id="env-nueva" class="env-oculto" style="margin-top:14px;border-top:1px solid var(--cx-border);padding-top:14px">
    <div class="env-grid">
      <div><label>Tipo (define el c&oacute;digo)</label>
        <select id="env-n-tipo" onchange="envPreverCodigo()">
          <option value="">-- eleg&iacute; --</option>
          <option value="ENV">Envase / frasco</option>
          <option value="IMP">Impreso (serigrafiado)</option>
          <option value="GOT">Gotero</option>
          <option value="TAP">Tapa</option>
          <option value="ETI">Etiqueta</option>
          <option value="PLE">Plegadiza</option>
        </select></div>
      <div><label>Material</label>
        <select id="env-n-mat" onchange="envArmarNombre()">
          <option value="">-- eleg&iacute; --</option>
          <option>Vidrio</option><option>Pl&aacute;stico PET</option><option>Pl&aacute;stico PP</option>
          <option>Pl&aacute;stico HDPE</option><option>Aluminio</option><option>Acr&iacute;lico</option>
          <option>Cart&oacute;n</option><option>Papel</option><option>Otro</option>
        </select></div>
      <div><label>Volumen (ml)</label><input id="env-n-ml" type="number" min="0" step="0.1" placeholder="30" oninput="envArmarNombre()"></div>
      <div><label>Color / detalle</label><input id="env-n-color" placeholder="&Aacute;mbar, negro mate&hellip;" oninput="envArmarNombre()"></div>
      <div><label>Nombre del envase</label><input id="env-n-desc" placeholder="Frasco vidrio &aacute;mbar 30 ml"></div>
      <div><label>C&oacute;digo que se va a asignar</label><input id="env-n-cod" readonly placeholder="se calcula solo" style="background:var(--cx-border-soft)"></div>
    </div>
    <div class="env-acciones">
      <button class="env-btn" onclick="envCrearRef()">Crear la referencia</button>
      <button class="env-btn ghost" onclick="envNuevaCerrar()">Cancelar</button>
    </div>
  </div>
</div>

<div class="env-card">
  <h3><span class="env-step">3</span>&iquest;En cu&aacute;ntas cajas lleg&oacute;?</h3>
  <div class="env-grid" style="max-width:660px">
    <div><label>N&uacute;mero de cajas</label><input id="env-ncajas" type="number" min="1" max="500" value="1"></div>
    <div><label>Unidades por caja</label><input id="env-porcaja" type="number" min="1" placeholder="200"></div>
    <div style="display:flex;align-items:flex-end"><button class="env-btn" onclick="envDesplegar()">Desplegar las cajas</button></div>
  </div>
  <div id="env-cajas-wrap" class="env-oculto" style="margin-top:16px">
    <div class="env-hint" style="margin-bottom:8px">Vienen autollenadas: s&oacute;lo cambi&aacute; la cantidad de la caja que traiga distinto.</div>
    <div style="overflow-x:auto"><table><thead><tr>
      <th style="width:110px">Caja</th><th style="width:180px">Unidades</th><th>R&oacute;tulo</th>
    </tr></thead><tbody id="env-cajas-tb"></tbody></table></div>
    <div class="env-kpi">
      <div><span>Cajas</span><b id="env-k-c">0</b></div>
      <div><span>Unidades totales</span><b id="env-k-u">0</b></div>
    </div>
    <div class="env-acciones">
      <button class="env-btn" id="env-b-recibir" onclick="envRecibir()">Recibir e ingresar a inventario</button>
      <button class="env-btn ghost env-oculto" id="env-b-todos" onclick="envRotulosTodos()">Imprimir los r&oacute;tulos de todas las cajas</button>
      <button class="env-btn ghost env-oculto" id="env-b-otra" onclick="envOtraRef()">Recibir otra referencia</button>
    </div>
    <div id="env-msg"></div>
  </div>
</div>

<div class="env-card env-oculto" id="env-hechas-card">
  <h3>Recibido en esta sesi&oacute;n</h3>
  <div style="overflow-x:auto"><table><thead><tr><th>Referencia</th><th>Lote</th><th>Cajas</th><th>Unidades</th><th>R&oacute;tulos</th></tr></thead><tbody id="env-hechas"></tbody></table></div>
</div>

<script>
var ENV_MAESTRO=[], ENV_CAJAS=[], ENV_TOKEN=null, ENV_MOV=null, ENV_HECHAS=[];
function envEsc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function envG(id){var e=document.getElementById(id);return e?e.value:'';}
function envShow(id,on){var e=document.getElementById(id);if(e)e.classList.toggle('env-oculto',!on);}
async function envCsrf(){try{var r=await fetch('/api/csrf-token',{credentials:'same-origin'});var j=await r.json();return j.csrf_token||j.token||'';}catch(e){return '';}}

async function envInit(){
  try{
    var r=await fetch('/api/mee/ubicaciones',{credentials:'same-origin'}); var j=await r.json();
    envLlenarUbic('env-zona', j.zona||[]); envLlenarUbic('env-est', j.estante||[]); envLlenarUbic('env-pos', j.posicion||[]);
  }catch(e){}
  try{
    var r2=await fetch('/api/mee/stock',{credentials:'same-origin'}); var j2=await r2.json();
    ENV_MAESTRO=(j2.items||[]).map(function(x){return {codigo:x.codigo,desc:x.descripcion||'',unidad:x.unidad||'und'};});
    envFiltrar();
  }catch(e){}
}
function envLlenarUbic(id,arr){
  var s=document.getElementById(id); if(!s)return;
  s.innerHTML='<option value="">--</option>'+arr.map(function(v){return '<option>'+envEsc(v)+'</option>';}).join('');
}
function envFiltrar(){
  var q=(envG('env-buscar')||'').trim().toUpperCase();
  var s=document.getElementById('env-ref'); if(!s)return;
  var lista=ENV_MAESTRO.filter(function(x){ return !q || (x.codigo+' '+x.desc).toUpperCase().indexOf(q)>=0; }).slice(0,300);
  s.innerHTML=lista.map(function(x){
    return '<option value="'+envEsc(x.codigo)+'">'+envEsc(x.codigo)+' &middot; '+envEsc(x.desc)+'</option>';
  }).join('')||'<option value="">(no hay coincidencias &middot; cre&aacute; la referencia)</option>';
}
function envRefSel(){ envShow('env-nueva', false); }

function envNuevaAbrir(){ envShow('env-nueva', true); envPreverCodigo(); }
function envNuevaCerrar(){ envShow('env-nueva', false); }
function envArmarNombre(){
  var d=document.getElementById('env-n-desc'); if(!d || (d.value||'').trim()) return;
  d.placeholder=[envG('env-n-mat'), envG('env-n-color'), (envG('env-n-ml')?envG('env-n-ml')+' ml':'')]
    .filter(function(x){return x;}).join(' ') || 'Frasco vidrio &aacute;mbar 30 ml';
}
async function envPreverCodigo(){
  var t=envG('env-n-tipo'); var out=document.getElementById('env-n-cod'); if(!out)return;
  if(!t){out.value='';return;}
  try{
    var r=await fetch('/api/mee/siguiente-codigo?tipo='+encodeURIComponent(t),{credentials:'same-origin'});
    var j=await r.json(); out.value=(r.ok&&j.ok)?j.codigo:'';
  }catch(e){ out.value=''; }
}
async function envCrearRef(){
  var tipo=envG('env-n-tipo'); if(!tipo){alert('Elegi el tipo: define el codigo.');return;}
  var desc=(envG('env-n-desc')||'').trim();
  var mat=envG('env-n-mat'), ml=envG('env-n-ml'), col=(envG('env-n-color')||'').trim();
  if(!desc){
    var base={ENV:'Envase',IMP:'Impreso',GOT:'Gotero',TAP:'Tapa',ETI:'Etiqueta',PLE:'Plegadiza'}[tipo]||'Envase';
    desc=[base,mat,col,(ml?ml+' ml':'')].filter(function(x){return x;}).join(' ');
  }
  var t=await envCsrf();
  var r=await fetch('/api/mee/crear-auto',{method:'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json','X-CSRF-Token':t},
    body:JSON.stringify({tipo:tipo,descripcion:desc,volumen_ml:parseFloat(ml||0)||0})});
  var j=await r.json();
  if(!r.ok||!j.ok){alert('No se pudo crear: '+(j.error||r.status));return;}
  ENV_MAESTRO.unshift({codigo:j.codigo,desc:desc,unidad:'und'});
  var b=document.getElementById('env-buscar'); if(b)b.value=j.codigo;
  envFiltrar();
  var s=document.getElementById('env-ref'); if(s)s.value=j.codigo;
  envNuevaCerrar();
  alert('Referencia creada: '+j.codigo+' - '+desc);
}
async function envAgregarUbic(tipo){
  var v=prompt('Valor nuevo de '+tipo+':','');
  if(v===null||!String(v).trim())return;
  var t=await envCsrf();
  var r=await fetch('/api/mee/ubicaciones/agregar',{method:'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json','X-CSRF-Token':t},
    body:JSON.stringify({tipo:tipo,valor:String(v).trim()})});
  var j=await r.json();
  if(!r.ok){alert('Error: '+(j.error||r.status));return;}
  var id=(tipo==='zona')?'env-zona':(tipo==='estante'?'env-est':'env-pos');
  envLlenarUbic(id, j[tipo]||[]);
  var s=document.getElementById(id); if(s)s.value=String(v).trim();
}

function envDesplegar(){
  var n=parseInt(envG('env-ncajas')||'0',10)||0;
  var por=parseFloat(envG('env-porcaja')||'0')||0;
  if(n<1){alert('Cuantas cajas llegaron?');return;}
  if(por<=0){alert('Pone las unidades por caja: despues cambias la que venga distinta.');return;}
  if(n>500){alert('Maximo 500 cajas por referencia.');return;}
  ENV_CAJAS=[]; for(var i=1;i<=n;i++) ENV_CAJAS.push({caja:i,cantidad:por});
  ENV_MOV=null; ENV_TOKEN=null;
  envShow('env-cajas-wrap', true); envShow('env-b-todos', false); envShow('env-b-otra', false);
  var br=document.getElementById('env-b-recibir'); if(br)br.disabled=false;
  var m=document.getElementById('env-msg'); if(m)m.innerHTML='';
  envPintarCajas();
}
function envSetCaja(i,v){ ENV_CAJAS[i].cantidad=parseFloat(v||0)||0; envKpis(); }
function envPintarCajas(){
  var h='';
  for(var i=0;i<ENV_CAJAS.length;i++){var c=ENV_CAJAS[i];
    var rot = ENV_MOV
      ? '<a class="env-btn mini" style="text-decoration:none" target="_blank" href="/rotulos-recepcion-mee?mov='+ENV_MOV+'&caja='+c.caja+'">&#128424; Imprimir r&oacute;tulo</a>'
      : '<span class="env-hint">se habilita al recibir</span>';
    h+='<tr><td><b>'+c.caja+'</b> <span class="env-hint">de '+ENV_CAJAS.length+'</span></td>'
      +'<td><input type="number" min="0" step="1" value="'+c.cantidad+'" oninput="envSetCaja('+i+',this.value)"'+(ENV_MOV?' disabled':'')+'></td>'
      +'<td>'+rot+'</td></tr>';
  }
  var tb=document.getElementById('env-cajas-tb'); if(tb)tb.innerHTML=h;
  envKpis();
}
function envKpis(){
  var u=0; for(var i=0;i<ENV_CAJAS.length;i++) u+=(parseFloat(ENV_CAJAS[i].cantidad)||0);
  var a=document.getElementById('env-k-c'); if(a)a.textContent=ENV_CAJAS.length;
  var b=document.getElementById('env-k-u'); if(b)b.textContent=u.toLocaleString('es-CO');
}
async function envRecibir(){
  var cod=envG('env-ref'); if(!cod){alert('Elegi la referencia, o crea una nueva.');return;}
  if(!ENV_CAJAS.length){alert('Desplega las cajas primero.');return;}
  var u=0;
  for(var i=0;i<ENV_CAJAS.length;i++){
    if(!(ENV_CAJAS[i].cantidad>0)){alert('La caja '+ENV_CAJAS[i].caja+' esta en 0.');return;}
    u+=ENV_CAJAS[i].cantidad;
  }
  if(!confirm('Recibir '+ENV_CAJAS.length+' caja(s) de '+cod+' ('+u.toLocaleString('es-CO')+' unidades) en CUARENTENA?'))return;
  if(!ENV_TOKEN){ENV_TOKEN=(window.crypto&&crypto.randomUUID)?crypto.randomUUID():('t'+Date.now()+Math.random());}
  var zona=[envG('env-zona'),envG('env-est'),envG('env-pos')].filter(function(x){return x;}).join(' / ');
  var body={proveedor:envG('env-prov'),factura_numero:envG('env-fact'),zona:zona,
            oc_numero:envG('env-oc'),recepcion_id:ENV_TOKEN,
            lineas:[{codigo:cod,lote_proveedor:envG('env-lote'),
                     cajas_detalle:ENV_CAJAS.map(function(c){return c.cantidad;})}]};
  var btn=document.getElementById('env-b-recibir'); if(btn)btn.disabled=true;
  var t=await envCsrf();
  var r=await fetch('/api/mee/recepcion-lineas',{method:'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify(body)});
  var j=await r.json();
  var msg=document.getElementById('env-msg');
  if(!r.ok){ if(msg)msg.innerHTML='<div class="env-err">'+envEsc(j.error||'Error')+'</div>'; if(btn)btn.disabled=false; return; }
  ENV_TOKEN=null;
  var mv=(j.movimientos||[])[0]||{};
  ENV_MOV=mv.mov_id||null;
  envPintarCajas();
  envShow('env-b-todos', true); envShow('env-b-otra', true);
  if(msg)msg.innerHTML='<div class="env-ok"><b>Recibido y disponible en inventario.</b> '+ENV_CAJAS.length
    +' caja(s) &middot; '+u.toLocaleString('es-CO')+' unidades. Ya pod&eacute;s imprimir el r&oacute;tulo de cada caja: '
    +'cada uno lleva su c&oacute;digo de barras <b>MEE-'+ENV_MOV+'-(caja)</b>, que es lo que Calidad escanea '
    +'para revisar esa caja.</div>';
  ENV_HECHAS.push({codigo:cod,lote:envG('env-lote'),cajas:ENV_CAJAS.length,unidades:u,mov:ENV_MOV});
  envPintarHechas();
}
function envPintarHechas(){
  if(!ENV_HECHAS.length)return;
  envShow('env-hechas-card', true);
  var tb=document.getElementById('env-hechas'); if(!tb)return;
  tb.innerHTML=ENV_HECHAS.map(function(x){
    return '<tr><td><b>'+envEsc(x.codigo)+'</b></td><td>'+envEsc(x.lote||'-')+'</td><td>'+x.cajas+'</td>'
      +'<td>'+x.unidades.toLocaleString('es-CO')+'</td>'
      +'<td><a class="env-btn mini" style="text-decoration:none" target="_blank" href="/rotulos-recepcion-mee?mov='+x.mov+'">Todos los r&oacute;tulos</a></td></tr>';
  }).join('');
}
function envRotulosTodos(){ if(ENV_MOV) window.open('/rotulos-recepcion-mee?mov='+ENV_MOV,'_blank'); }
function envOtraRef(){
  ENV_CAJAS=[]; ENV_MOV=null; ENV_TOKEN=null;
  envShow('env-cajas-wrap', false); envShow('env-b-todos', false); envShow('env-b-otra', false);
  ['env-lote','env-buscar','env-n-desc','env-n-ml','env-n-color'].forEach(function(id){var e=document.getElementById(id); if(e)e.value='';});
  envFiltrar();
}
envInit();
</script>
'''
