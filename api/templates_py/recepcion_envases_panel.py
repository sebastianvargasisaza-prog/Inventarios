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
#rt-env .env-w2{grid-column:1/-1}
.env-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
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
#rt-env .env-parte{display:flex;align-items:center;gap:14px;padding:11px 14px;border:1px solid var(--cx-border);
  border-radius:11px;margin-bottom:8px;flex-wrap:wrap}
#rt-env .env-parte.on{border-color:var(--cx-success);background:var(--cx-success-pale)}
#rt-env .env-parte-nom{font-weight:700;font-size:13.5px;color:var(--cx-text)}
#rt-env .env-parte-cod{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11.5px;color:var(--cx-text-mute)}
#rt-env .env-parte-sw{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}
#rt-env .env-parte-b{border:1.5px solid var(--cx-border);background:transparent;color:var(--cx-text-soft);
  border-radius:9px;padding:7px 13px;font-size:12.5px;font-weight:700;cursor:pointer;font-family:inherit}
#rt-env .env-parte-b.sel{background:var(--cx-success-pale);border-color:var(--cx-success);color:var(--cx-success-text)}
#rt-env .env-parte-b.sel.no{background:var(--cx-bg-soft);border-color:var(--cx-border);color:var(--cx-text-mute)}
#rt-env .env-parte-tot{font-size:11.5px;color:var(--cx-success-text);font-weight:700;width:100%}
#rt-env .env-parte-falta{font-size:11.5px;color:var(--cx-danger-text);font-weight:700;width:100%}
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
      <label>Lote del proveedor <span class="env-hint" style="text-transform:none;font-weight:600">(si no trae, dejalo vac&iacute;o)</span></label>
      <input id="env-lote" placeholder="CN-2607-A &middot; o vac&iacute;o si no trae">
      <div class="env-hint" style="margin:8px 0">Es el lote que Calidad necesita para el F01 y el que se imprime en el r&oacute;tulo.
      <b>Si el proveedor no manda lote, EOS genera uno interno</b> (<code>INT-260730-001</code>) para que igual haya trazabilidad:
      queda impreso en el r&oacute;tulo marcado como interno, y es el que se escanea.</div>
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
      <div class="env-w2">
        <label style="display:flex;align-items:center;gap:9px;text-transform:none;font-size:13px;font-weight:600;color:var(--cx-text-soft);cursor:pointer">
          <input type="checkbox" id="env-n-calif" style="width:17px;height:17px;flex:none">
          &iquest;Este material <b>requiere calificaci&oacute;n de Calidad</b>? (capacidad de llenado, material, medidas, documentos)
        </label>
        <div class="env-hint" style="margin-top:5px">Si no lo marc&aacute;s, entra directo y <b>no</b> aparece en la cola de Calidad.
        Marcalo cuando sea un envase nuevo que nadie ha validado todav&iacute;a.</div>
      </div>
      <div class="env-w2" style="border-top:1px solid var(--cx-border);padding-top:14px">
        <label>&iquest;Se arma con otras piezas?</label>
        <div class="env-hint" style="margin-bottom:9px">Gotero, tapa, plegadiza&hellip; Declaralas ac&aacute;
        <b>una vez</b> y en cada recepci&oacute;n el sistema te va a preguntar si vinieron adentro del bulto.
        Es tambi&eacute;n lo que hace que el abastecimiento las compre con el frasco.</div>
        <div style="display:flex;gap:9px;flex-wrap:wrap;align-items:flex-end">
          <div style="flex:1 1 260px"><select id="env-n-pieza"></select></div>
          <div style="width:130px"><label>Por envase</label>
            <input id="env-n-pieza-cant" type="number" min="0.01" step="0.5" value="1"></div>
          <button class="env-btn ghost mini" onclick="envPiezaAgregar()">+ Agregar pieza</button>
        </div>
        <div id="env-n-piezas" class="env-hint" style="margin-top:9px">Ninguna pieza declarada todav&iacute;a.</div>
      </div>
    </div>
    <div class="env-acciones">
      <button class="env-btn" onclick="envCrearRef()">Crear la referencia</button>
      <button class="env-btn ghost" onclick="envNuevaCerrar()">Cancelar</button>
    </div>
  </div>
</div>

<div class="env-card env-oculto" id="env-partes-card">
  <h3><span class="env-step">3</span>&iquest;Qu&eacute; trae el bulto?</h3>
  <div class="env-hint" style="margin-bottom:12px">Este envase se arma con varias piezas. Marc&aacute;
    las que vinieron <b>adentro de la caja</b>: esas entran al inventario junto con el frasco, con su
    propio movimiento. Las que se compran sueltas no se tocan ac&aacute; &middot; entran por su propia
    recepci&oacute;n.</div>
  <div id="env-partes-lista"></div>
  <div id="env-partes-vacio" class="env-hint env-oculto">Esta referencia no tiene piezas declaradas
    en el maestro. Si lleva gotero, tapa o plegadiza, carg&aacute;selas y vuelven a aparecer ac&aacute;
    la pr&oacute;xima vez.</div>
</div>

<div class="env-card">
  <h3><span class="env-step">4</span>&iquest;En cu&aacute;ntas cajas lleg&oacute;?</h3>
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
function envRefSel(){ envShow('env-nueva', false); envCargarPartes(); }

// ── ¿Qué trae el bulto? ──────────────────────────────────────────────────────
// El maestro dice que el frasco LLEVA gotero (la receta del envase, no cambia). Que ESTE
// embarque VINO con el gotero adentro es un hecho del EMBARQUE: el mismo frasco puede venir
// armado de China y suelto de un proveedor local. Por eso se confirma al recibir y no allá.
var ENV_PARTES = [];
async function envCargarPartes(){
  var cod = envG('env-ref');
  ENV_PARTES = [];
  if(!cod){ envShow('env-partes-card', false); return; }
  try{
    var r = await fetch('/api/mee/partes?codigo=' + encodeURIComponent(cod), {credentials:'same-origin'});
    var j = await r.json();
    ENV_PARTES = (j.partes || []).map(function(x){
      return {codigo:x.codigo, desc:x.descripcion || x.codigo,
              cxu: parseFloat(x.cantidad_por_unidad || 1) || 1,
              en_maestro: x.en_maestro !== false,
              incluida: !!x.incluido_default};
    });
  }catch(e){ ENV_PARTES = []; }
  envShow('env-partes-card', true);
  envPintarPartes();
}
function envSetParte(i, val){ if(ENV_PARTES[i]){ ENV_PARTES[i].incluida = val; envPintarPartes(); } }
function envPintarPartes(){
  var box = document.getElementById('env-partes-lista');
  if(!box) return;
  if(!ENV_PARTES.length){ box.innerHTML=''; envShow('env-partes-vacio', true); return; }
  envShow('env-partes-vacio', false);
  var uds = envTotalUnidades();
  box.innerHTML = ENV_PARTES.map(function(p, i){
    var tot = uds ? Math.round(uds * p.cxu) : 0;
    var pie = '';
    if(!p.en_maestro){
      pie = '<div class="env-parte-falta">Esta pieza no existe en el maestro de envases, as&iacute; que '
          + 'no puede entrar al inventario. Cre&aacute;la primero.</div>';
    }else if(p.incluida && tot){
      pie = '<div class="env-parte-tot">&#10003; entran ' + tot.toLocaleString('es-CO')
          + ' al inventario junto con el frasco</div>';
    }else if(p.incluida){
      pie = '<div class="env-parte-tot">&#10003; se calcula al desplegar las cajas</div>';
    }
    return '<div class="env-parte' + (p.incluida ? ' on' : '') + '">'
      + '<div><div class="env-parte-nom">' + envEsc(p.desc) + '</div>'
      + '<div class="env-parte-cod">' + envEsc(p.codigo)
      + (p.cxu !== 1 ? ' &middot; ' + p.cxu + ' por envase' : '') + '</div></div>'
      + '<div class="env-parte-sw">'
      + '<button type="button" class="env-parte-b' + (p.incluida ? ' sel' : '')
      + '" onclick="envSetParte(' + i + ',true)">Vino adentro</button>'
      + '<button type="button" class="env-parte-b' + (!p.incluida ? ' sel no' : '')
      + '" onclick="envSetParte(' + i + ',false)">Se compra aparte</button>'
      + '</div>' + pie + '</div>';
  }).join('');
}
function envTotalUnidades(){
  var t = 0; for(var i=0;i<ENV_CAJAS.length;i++) t += (parseFloat(ENV_CAJAS[i].cantidad)||0);
  return t;
}
function envPartesPayload(){
  return ENV_PARTES.filter(function(p){ return p.incluida && p.en_maestro; })
                   .map(function(p){ return {codigo:p.codigo, cantidad_por_envase:p.cxu}; });
}

function envNuevaAbrir(){ envShow('env-nueva', true); envPreverCodigo(); envPiezasLlenar(); }
function envNuevaCerrar(){ envShow('env-nueva', false); }

// ── Piezas de una referencia NUEVA ──────────────────────────────────────────
// Se declaran una sola vez, acá, porque son la RECETA del envase (qué lleva) y no cambian
// embarque a embarque. Lo que sí cambia -- si vinieron adentro de la caja -- se confirma en
// el paso 3 de cada recepción.
var ENV_NPIEZAS = [];
function envPiezasLlenar(){
  var s=document.getElementById('env-n-pieza'); if(!s)return;
  s.innerHTML='<option value="">-- eleg&iacute; la pieza del maestro --</option>'
    + ENV_MAESTRO.map(function(x){
        return '<option value="'+envEsc(x.codigo)+'">'+envEsc(x.codigo)+' &middot; '+envEsc(x.desc)+'</option>';
      }).join('');
}
function envPiezaAgregar(){
  var cod=envG('env-n-pieza');
  if(!cod){alert('Elegi la pieza del maestro.');return;}
  var cant=parseFloat(envG('env-n-pieza-cant')||'1')||0;
  if(cant<=0){alert('La cantidad por envase tiene que ser mayor que cero.');return;}
  for(var i=0;i<ENV_NPIEZAS.length;i++){
    if(ENV_NPIEZAS[i].codigo===cod){ ENV_NPIEZAS[i].cantidad=cant; envPiezasPintar(); return; }
  }
  var m=ENV_MAESTRO.filter(function(x){return x.codigo===cod;})[0]||{};
  ENV_NPIEZAS.push({codigo:cod, descripcion:m.desc||'', cantidad:cant});
  envPiezasPintar();
}
function envPiezaQuitar(i){ ENV_NPIEZAS.splice(i,1); envPiezasPintar(); }
function envPiezasPintar(){
  var b=document.getElementById('env-n-piezas'); if(!b)return;
  if(!ENV_NPIEZAS.length){ b.innerHTML='Ninguna pieza declarada todav&iacute;a.'; return; }
  b.innerHTML=ENV_NPIEZAS.map(function(p,i){
    return '<span class="env-parte-b sel" style="display:inline-block;margin:0 7px 7px 0;cursor:default">'
      + envEsc(p.codigo) + ' &times; ' + p.cantidad
      + ' <a href="#" onclick="envPiezaQuitar('+i+');return false;" style="text-decoration:none">&#10005;</a></span>';
  }).join('');
}
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
    body:JSON.stringify({tipo:tipo,descripcion:desc,volumen_ml:parseFloat(ml||0)||0,
      requiere_calificacion: !!(document.getElementById('env-n-calif')||{}).checked,
      partes:ENV_NPIEZAS})});
  var j=await r.json();
  if(!r.ok||!j.ok){alert('No se pudo crear: '+(j.error||r.status));return;}
  ENV_MAESTRO.unshift({codigo:j.codigo,desc:desc,unidad:'und'});
  var b=document.getElementById('env-buscar'); if(b)b.value=j.codigo;
  envFiltrar();
  var s=document.getElementById('env-ref'); if(s)s.value=j.codigo;
  envNuevaCerrar();
  // Las piezas que el maestro NO aceptó se NOMBRAN. Antes viajaban en la respuesta y nadie las
  // leía: el envase quedaba sin su gotero y sólo se notaba al envasar.
  var _rech=(j.partes_rechazadas||[]);
  alert('Referencia creada: '+j.codigo+' - '+desc
    + (ENV_NPIEZAS.length ? '\npiezas declaradas: '+(ENV_NPIEZAS.length-_rech.length) : '')
    + (_rech.length ? '\nNO se pudieron declarar: '
        + _rech.map(function(x){return x.codigo+' ('+x.motivo+')';}).join(', ') : ''));
  ENV_NPIEZAS=[]; envPiezasPintar();
  envCargarPartes();   // el paso "¿qué trae?" ya muestra lo que se acaba de declarar
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
function envSetCaja(i,v){ ENV_CAJAS[i].cantidad=parseFloat(v||0)||0; envKpis(); envPintarPartes(); }
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
  envPintarPartes();   // el total de piezas depende de las unidades del bulto
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
  // El texto del confirm dice lo que de verdad va a pasar: desde el 30-jul los envases entran
  // DISPONIBLES (la revisión de Calidad dejó de ser un candado sobre el stock). Decía
  // "en CUARENTENA" y contradecía al propio encabezado de la pantalla.
  var _pz=envPartesPayload();
  var _txtP=_pz.length ? ('\ncon ' + _pz.length + ' pieza(s) incluidas: '
              + _pz.map(function(x){return x.codigo;}).join(', ')) : '';
  if(!confirm('Recibir '+ENV_CAJAS.length+' caja(s) de '+cod+' ('+u.toLocaleString('es-CO')
      +' unidades)?'+_txtP+'\nEntra DISPONIBLE en inventario.'))return;
  if(!ENV_TOKEN){ENV_TOKEN=(window.crypto&&crypto.randomUUID)?crypto.randomUUID():('t'+Date.now()+Math.random());}
  var zona=[envG('env-zona'),envG('env-est'),envG('env-pos')].filter(function(x){return x;}).join(' / ');
  var body={proveedor:envG('env-prov'),factura_numero:envG('env-fact'),zona:zona,
            oc_numero:envG('env-oc'),recepcion_id:ENV_TOKEN,
            lineas:[{codigo:cod,lote_proveedor:envG('env-lote'),
                     cajas_detalle:ENV_CAJAS.map(function(c){return c.cantidad;}),
                     partes:_pz}]};
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
  // Las piezas que entraron se NOMBRAN una por una. Sumarlas al total dejaría a quien recibe
  // sin forma de verificar que el gotero quedó registrado, que es justo lo que este paso viene
  // a garantizar.
  var _pi=(j.partes_ingresadas||[]);
  var _htmlP = _pi.length
    ? '<div style="margin-top:8px">Adem&aacute;s entraron las piezas que vinieron adentro: '
      + _pi.map(function(x){ return '<b>'+envEsc(x.codigo)+'</b> ('
          + Number(x.cantidad).toLocaleString('es-CO')+')'; }).join(' &middot; ') + '.</div>'
    : '';
  var _htmlA = (j.avisos||[]).length
    ? '<div class="env-err">'+(j.avisos||[]).map(envEsc).join('<br>')+'</div>' : '';
  if(msg)msg.innerHTML='<div class="env-ok"><b>Recibido y disponible en inventario.</b> '+ENV_CAJAS.length
    +' caja(s) &middot; '+u.toLocaleString('es-CO')+' unidades. Ya pod&eacute;s imprimir el r&oacute;tulo de cada caja: '
    +'cada uno lleva su c&oacute;digo de barras <b>MEE-'+ENV_MOV+'-(caja)</b>, que es lo que Calidad escanea '
    +'para revisar esa caja.'+_htmlP+'</div>'+_htmlA;
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
  // Las piezas son de la referencia anterior: si no se limpian, la próxima recepción arrastra
  // el gotero del frasco que se acaba de recibir (M113: un estado que sobrevive al reset miente).
  ENV_PARTES=[]; envShow('env-partes-card', false);
  envShow('env-cajas-wrap', false); envShow('env-b-todos', false); envShow('env-b-otra', false);
  ['env-lote','env-buscar','env-n-desc','env-n-ml','env-n-color'].forEach(function(id){var e=document.getElementById(id); if(e)e.value='';});
  envFiltrar();
}
envInit();
</script>
'''
