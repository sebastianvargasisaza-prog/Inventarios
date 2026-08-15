"""Pantalla del director tecnico para configurar las verificaciones GMP (15-ago-2026).

En MyBatch los items del despeje de linea y los controles de atributos son pantallas de
configuracion del DT. En EOS eran constantes del codigo: cambiar un item exigia un
despliegue. Esta pantalla los hace configurables SIN perder lo que el codigo daba gratis
-cada cambio queda en el audit trail y el texto de lo YA FIRMADO no se toca nunca-, que
es justo la parte que MyBatch no muestra por ningun lado.
"""

CHECKLISTS_HTML = r"""<!DOCTYPE html><html lang="es" translate="no"><head><meta charset="UTF-8">
<meta name="google" content="notranslate">
<meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover"><title>Verificaciones GMP &middot; Aseguramiento &middot; EOS</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
body{background:var(--cx-bg);color:var(--cx-text);margin:0;font-family:'Inter',system-ui,-apple-system,sans-serif;}
*{box-sizing:border-box}
.ck-wrap{width:96vw;max-width:1360px;margin:0 auto;padding:22px 18px 72px;}
.card{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:18px;box-shadow:0 1px 3px rgba(15,23,42,.04),0 10px 30px rgba(15,23,42,.05);padding:20px 22px;margin-bottom:16px;}
.ck-intro{color:var(--cx-text-mute);font-size:13.5px;line-height:1.55;max-width:900px;margin:0 0 16px;}
.selectores{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:6px;}
.estado{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:14px;}
.pill{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:800;padding:5px 12px;border-radius:999px;border:1px solid var(--cx-hairline);color:var(--cx-text-soft);}
.pill.fabrica{color:var(--cx-text-mute);}
.pill.configurado{color:var(--cx-primary-text);border-color:var(--cx-primary-light);background:var(--cx-primary-soft);}
.pill.aviso{color:var(--cx-warn-text, #b45309);border-color:rgba(180,83,9,.35);background:rgba(180,83,9,.10);}
.item{display:flex;gap:10px;align-items:flex-start;padding:10px 0;border-bottom:1px solid var(--cx-hairline);}
.item .n{font-size:12px;font-weight:800;color:var(--cx-text-faint);min-width:26px;padding-top:9px;font-variant-numeric:tabular-nums;}
.item textarea{flex:1;min-height:44px;resize:vertical;font-family:inherit;font-size:13.5px;line-height:1.45;}
.item .uni{width:92px;}
.item .ctrl{display:flex;flex-direction:column;gap:4px;padding-top:2px;}
.item button{background:var(--cx-bg-alt);border:1px solid var(--cx-hairline);color:var(--cx-text-soft);border-radius:7px;width:30px;height:26px;cursor:pointer;font-size:13px;line-height:1;padding:0;}
.item button:hover{border-color:var(--cx-primary-light);color:var(--cx-primary-text);}
.item.retirado{opacity:.55;}
.item .firmado{font-size:10.5px;color:var(--cx-warn-text, #b45309);font-weight:700;padding-top:10px;white-space:nowrap;}
.acciones{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:18px;}
#msg{font-size:12.5px;font-weight:700;}
.nota{font-size:11.5px;color:var(--cx-text-faint);line-height:1.6;margin-top:14px;}
.solo-lectura{background:rgba(180,83,9,.09);border:1px solid rgba(180,83,9,.3);border-radius:12px;padding:12px 15px;font-size:13px;color:var(--cx-warn-text, #b45309);margin-bottom:14px;}
</style></head><body>
<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:var(--cx-primary-text);"><svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg></span>
  <div>
    <div class="cx-mod-header__title">Verificaciones GMP</div>
    <div class="cx-mod-header__sub"><strong>Aseguramiento</strong> &middot; despeje de l&iacute;nea y controles en proceso</div>
  </div>
  <div class="cx-mod-header__nav">
    <a href="/aseguramiento" class="cx-btn cx-btn-ghost cx-btn-sm">&larr; Aseguramiento</a>
    <a href="/calidad/maestro-lotes" class="cx-btn cx-btn-ghost cx-btn-sm" title="Unidades por lote y presentaci&oacute;n">&#128202; Maestro de lotes</a>
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm">M&oacute;dulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg></button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var n=h.getAttribute('data-theme')==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>
<div class="ck-wrap">
<div class="card">
<div class="ck-intro">Ac&aacute; se define <b>qu&eacute; verifica el piso</b>: los &iacute;tems del despeje de l&iacute;nea y los controles en proceso de cada fase. Lo que guardes ac&aacute; es lo que aparece en el legajo y en la cola de Calidad. <b>Nada de esto toca lo ya firmado</b>: un &iacute;tem que un operario firm&oacute; conserva para siempre el texto que ten&iacute;a delante cuando firm&oacute;, y uno que retires sigue apareciendo en los lotes donde se registr&oacute;.</div>
<div class="selectores">
  <select id="tipo" class="cx-input" style="max-width:280px">
    <option value="despeje">Despeje de l&iacute;nea</option>
    <option value="ipc">Controles en proceso</option>
  </select>
  <select id="ambito" class="cx-input" style="max-width:260px"></select>
  <button class="cx-btn cx-btn-ghost" onclick="ckCargar()">Ver</button>
  <span id="msg"></span>
</div>
<div id="estado" class="estado"></div>
</div>
<div id="ro" class="solo-lectura" style="display:none">Est&aacute;s viendo el procedimiento en modo consulta. Cambiar una verificaci&oacute;n GMP es del director t&eacute;cnico o Aseguramiento: qui&eacute;n <b>ejecuta</b> el procedimiento no es quien lo <b>define</b>.</div>
<div class="card">
  <div id="items"></div>
  <div class="acciones">
    <button id="btn-agregar" class="cx-btn cx-btn-ghost" onclick="ckAgregar()">&#10133; Agregar verificaci&oacute;n</button>
    <button id="btn-guardar" class="cx-btn cx-btn-grad" onclick="ckGuardar()">Guardar procedimiento</button>
    <button id="btn-restaurar" class="cx-btn cx-btn-ghost" onclick="ckRestaurar()" title="Vuelve a la lista que EOS trae de f&aacute;brica">Volver a la de f&aacute;brica</button>
  </div>
  <div class="nota">Cada cambio queda registrado con tu usuario, la fecha, y el antes y el despu&eacute;s completos (21 CFR Part 11 &sect;11.10(e)). Un &iacute;tem nuevo <b>nunca</b> reutiliza la clave de uno que ya se firm&oacute;.</div>
</div>
</div>
<script>
var CK = {tipo:'despeje', ambito:'', items:[], puede:false, ambitos:[]};
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function ckNombreAmbito(a){
  return a==='dispensacion'?'Dispensación':a==='fabricacion'?'Fabricación':a==='envasado'?'Envasado':a==='acondicionamiento'?'Acondicionamiento':a;}
function ckCargar(){
  var tipo=document.getElementById('tipo').value;
  var amb=document.getElementById('ambito').value||'';
  document.getElementById('msg').textContent='Cargando...';
  fetch('/api/brd/checklists?tipo='+encodeURIComponent(tipo)+'&ambito='+encodeURIComponent(amb),{credentials:'same-origin'})
   .then(function(r){return r.json();}).then(function(j){
    if(!j||!j.ok){document.getElementById('msg').textContent='No se pudo cargar';return;}
    document.getElementById('msg').textContent='';
    CK.tipo=j.tipo; CK.ambito=j.ambito; CK.puede=!!j.puede_configurar; CK.ambitos=j.ambitos||[];
    CK.items=(j.items||[]).map(function(i){return {clave:i.clave,texto:i.texto,unidad:i.unidad||'',activo:i.activo!==false};});
    var sel=document.getElementById('ambito');
    sel.innerHTML=CK.ambitos.map(function(a){return '<option value="'+esc(a)+'"'+(a===j.ambito?' selected':'')+'>'+esc(ckNombreAmbito(a))+'</option>';}).join('');
    var e=[];
    e.push('<span class="pill '+(j.origen==='configurado'?'configurado':'fabrica')+'">'+(j.origen==='configurado'?'Configurado por el director técnico':'Lista de fábrica de EOS')+'</span>');
    if(j.ultimo_por) e.push('<span class="pill">Último cambio: '+esc(j.ultimo_por)+' · '+esc((j.ultimo_cambio||'').replace('T',' ').slice(0,16))+'</span>');
    e.push('<span class="pill">'+CK.items.filter(function(i){return i.activo;}).length+' verificaciones vigentes</span>');
    if(j.legajos_en_curso>0) e.push('<span class="pill aviso">'+j.legajos_en_curso+' legajo(s) en curso con esta lista: lo ya firmado no cambia, pero lo nuevo se les va a pedir</span>');
    document.getElementById('estado').innerHTML=e.join('');
    document.getElementById('ro').style.display=CK.puede?'none':'block';
    ['btn-agregar','btn-guardar','btn-restaurar'].forEach(function(b){document.getElementById(b).disabled=!CK.puede;});
    ckPintar();
  }).catch(function(e){document.getElementById('msg').textContent='Error: '+e;});
}
function ckPintar(){
  var esIpc=CK.tipo==='ipc';
  var h=CK.items.map(function(it,i){
    var d=CK.puede?'':' disabled';
    return '<div class="item'+(it.activo?'':' retirado')+'">'
      +'<div class="n">'+(i+1)+'</div>'
      +'<textarea class="cx-input" oninput="ckSet('+i+',this.value)"'+d+'>'+esc(it.texto)+'</textarea>'
      +(esIpc?'<input class="cx-input uni" placeholder="unidad" value="'+esc(it.unidad)+'" oninput="ckSetU('+i+',this.value)"'+d+'>':'')
      +'<div class="ctrl">'
      +'<button onclick="ckMover('+i+',-1)" title="Subir"'+d+'>&#9650;</button>'
      +'<button onclick="ckMover('+i+',1)" title="Bajar"'+d+'>&#9660;</button>'
      +'<button onclick="ckQuitar('+i+')" title="Retirar del procedimiento (no borra lo ya registrado)"'+d+'>&#10005;</button>'
      +'</div>'
      +(it.clave!==''&&it.clave!=null?'<div class="firmado" title="Clave estable del ítem">'+esc(it.clave)+'</div>':'')
      +'</div>';
  }).join('');
  document.getElementById('items').innerHTML=h||'<div style="color:var(--cx-text-mute);padding:20px 0">Sin verificaciones.</div>';
}
function ckSet(i,v){CK.items[i].texto=v;}
function ckSetU(i,v){CK.items[i].unidad=v;}
function ckMover(i,d){var j=i+d; if(j<0||j>=CK.items.length)return; var t=CK.items[i]; CK.items[i]=CK.items[j]; CK.items[j]=t; ckPintar();}
function ckQuitar(i){CK.items.splice(i,1); ckPintar();}
function ckAgregar(){CK.items.push({clave:'',texto:'',unidad:'',activo:true}); ckPintar();
  var ta=document.getElementById('items').querySelectorAll('textarea'); if(ta.length)ta[ta.length-1].focus();}
function ckGuardar(){
  var items=CK.items.filter(function(i){return (i.texto||'').trim();})
                    .map(function(i){return {clave:i.clave,texto:i.texto,unidad:i.unidad};});
  if(!items.length){document.getElementById('msg').textContent='La lista no puede quedar vacia';return;}
  var motivo=window.prompt('Motivo del cambio (queda en el registro de auditoria):','');
  if(motivo===null)return;
  if(window._ckBusy)return; window._ckBusy=true;
  document.getElementById('msg').textContent='Guardando...';
  fetch('/api/brd/checklists',{method:'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({tipo:CK.tipo,ambito:CK.ambito,items:items,motivo:motivo})})
   .then(function(r){return r.json().then(function(j){return {s:r.status,j:j};});})
   .then(function(x){
     window._ckBusy=false;
     if(x.s!==200){document.getElementById('msg').textContent=(x.j&&x.j.error)||'No se pudo guardar';return;}
     document.getElementById('msg').textContent='Guardado'+(x.j.retirados?' · '+x.j.retirados+' retirado(s)':'');
     ckCargar();
   }).catch(function(e){window._ckBusy=false;document.getElementById('msg').textContent='Error: '+e;});
}
function ckRestaurar(){
  if(!window.confirm('Vuelve a la lista que EOS trae de fabrica. Lo ya registrado no se toca.'))return;
  if(window._ckBusy)return; window._ckBusy=true;
  fetch('/api/brd/checklists/restaurar',{method:'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({tipo:CK.tipo,ambito:CK.ambito})})
   .then(function(r){return r.json();}).then(function(j){
     window._ckBusy=false;
     document.getElementById('msg').textContent=j&&j.ok?'Restaurado':'No se pudo restaurar';
     ckCargar();
   }).catch(function(e){window._ckBusy=false;document.getElementById('msg').textContent='Error: '+e;});
}
document.getElementById('tipo').addEventListener('change',function(){document.getElementById('ambito').innerHTML='';ckCargar();});
document.getElementById('ambito').addEventListener('change',ckCargar);
ckCargar();
</script>
</body></html>"""
