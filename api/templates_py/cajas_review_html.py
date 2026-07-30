# -*- coding: utf-8 -*-
"""Revisión CAJA POR CAJA de una recepción de envases · para Calidad (30-jul · mig 399).

Sebastián: *"ya cuando calidad haga verificación entonces revisa caja por caja y si es
necesario cambia los rótulos (...) pueden escanear entonces código de barras y hacer lo que
corresponde"*.

Se inyecta en la página de Calidad (patrón de `cc_review_html`) y vive al lado de la bandeja de
recepción, que es donde Laura trabaja. Nombres propios (`cjs…`) porque comparte documento con
una página grande: una función repetida pisa la de al lado sin un solo error (M59).
"""

CAJAS_REVIEW_MODAL_HTML = r'''
<div id="cjs-modal" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.62);z-index:9600;align-items:flex-start;justify-content:center;padding:28px 14px;overflow:auto">
  <div style="background:var(--cx-card);border:1px solid var(--cx-border);border-radius:14px;max-width:760px;width:100%;box-shadow:0 20px 60px rgba(0,0,0,.35)">
    <div style="padding:16px 22px;border-bottom:1px solid var(--cx-border);display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
      <div>
        <div style="font-size:15px;font-weight:800;color:var(--cx-primary-text)">&#128230; Revisi&oacute;n caja por caja</div>
        <div id="cjs-sub" style="font-size:12px;color:var(--cx-text-mute);margin-top:2px"></div>
      </div>
      <button onclick="cjsCerrar()" style="background:var(--cx-border-soft);color:var(--cx-text-soft);border:none;border-radius:8px;padding:7px 14px;font-size:12.5px;font-weight:700;cursor:pointer">Cerrar</button>
    </div>
    <div style="padding:16px 22px">
      <div style="font-size:12.5px;color:var(--cx-text-mute);line-height:1.55;margin-bottom:12px">
        Marc&aacute; cada caja. Lo aprobado pasa a stock disponible; lo rechazado sale en su propia
        fila del kardex y <b>no se mezcla</b>. Un rechazo va con motivo, y el r&oacute;tulo de esa caja
        se reimprime ya marcado.
      </div>
      <div id="cjs-cajas" style="max-height:46vh;overflow:auto"></div>
      <div id="cjs-resumen" style="display:flex;gap:22px;flex-wrap:wrap;margin-top:14px;font-size:12.5px"></div>
      <div id="cjs-msg"></div>
    </div>
    <div style="padding:14px 22px;border-top:1px solid var(--cx-border);display:flex;gap:10px;justify-content:flex-end;flex-wrap:wrap">
      <button onclick="cjsTodasOk()" style="background:transparent;border:1px solid var(--cx-primary-light);color:var(--cx-primary-text);border-radius:9px;padding:9px 16px;font-size:12.5px;font-weight:700;cursor:pointer">Marcar todas conformes</button>
      <button onclick="cjsGuardar(false)" style="background:var(--cx-primary-soft);color:var(--cx-primary-text);border:none;border-radius:9px;padding:9px 16px;font-size:12.5px;font-weight:700;cursor:pointer">Guardar sin cerrar</button>
      <button onclick="cjsGuardar(true)" style="background:var(--cx-primary-grad);color:#fff;border:none;border-radius:9px;padding:9px 18px;font-size:13px;font-weight:800;cursor:pointer">Cerrar la revisi&oacute;n</button>
    </div>
  </div>
</div>
'''

CAJAS_REVIEW_JS = r'''
var CJS_MOV=null, CJS_CAJAS=[], CJS_META={}, CJS_FOCO=null;
function cjsEsc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
async function cjsCsrf(){try{var r=await fetch('/api/csrf-token',{credentials:'same-origin'});var j=await r.json();return j.csrf_token||j.token||'';}catch(e){return '';}}
function cjsCerrar(){var m=document.getElementById('cjs-modal'); if(m)m.style.display='none'; CJS_FOCO=null;}
async function cjsEscanear(){
  var inp=document.getElementById('cjs-scan'); var msg=document.getElementById('cjs-scan-msg');
  var tok=((inp&&inp.value)||'').trim();
  if(!tok){if(msg)msg.textContent='Escane&aacute; o escrib&iacute; el c&oacute;digo de la caja.';return;}
  try{
    var r=await fetch('/api/mee/escanear?token='+encodeURIComponent(tok),{credentials:'same-origin'});
    var j=await r.json();
    if(!r.ok){if(msg)msg.innerHTML='<span style="color:var(--cx-danger-text)">'+cjsEsc(j.error||'No se pudo leer')+'</span>';return;}
    if(msg)msg.innerHTML='<span style="color:var(--cx-success-text)">'+cjsEsc(j.codigo)+' &middot; caja '+j.caja+' de '+j.n_cajas+'</span>';
    if(inp)inp.value='';
    CJS_FOCO=j.caja;
    cjsAbrir(j.mov_id);
  }catch(e){ if(msg)msg.textContent='Error de red'; }
}
async function cjsAbrir(mov){
  CJS_MOV=mov;
  try{
    var r=await fetch('/api/mee/cuarentena/'+mov+'/cajas',{credentials:'same-origin'});
    var j=await r.json();
    if(!r.ok){alert('No se pudo abrir: '+(j.error||r.status));return;}
    CJS_META=j; CJS_CAJAS=(j.cajas||[]).map(function(c){return {caja:c.caja,cantidad:c.cantidad,estado:(c.estado||'CUARENTENA').toUpperCase(),motivo:c.motivo||''};});
    var sub=document.getElementById('cjs-sub');
    if(sub)sub.innerHTML=cjsEsc(j.codigo)+' &middot; lote '+cjsEsc(j.lote||'sin lote')
      +' &middot; '+CJS_CAJAS.length+' caja(s) &middot; total '+Number(j.total||0).toLocaleString('es-CO')+' '+cjsEsc(j.unidad||'und');
    var m=document.getElementById('cjs-modal'); if(m)m.style.display='flex';
    var mg=document.getElementById('cjs-msg'); if(mg)mg.innerHTML='';
    cjsPintar();
  }catch(e){ alert('Error de red'); }
}
function cjsSet(i,est){ CJS_CAJAS[i].estado=est; cjsPintar(); }
function cjsMotivo(i,v){ CJS_CAJAS[i].motivo=v; }
function cjsTodasOk(){ for(var i=0;i<CJS_CAJAS.length;i++) CJS_CAJAS[i].estado='APROBADO'; cjsPintar(); }
function cjsPintar(){
  var h='<table style="width:100%;border-collapse:collapse;font-size:13px">'
    +'<thead><tr><th style="text-align:left;padding:6px;font-size:11px;text-transform:uppercase;color:var(--cx-text-mute)">Caja</th>'
    +'<th style="text-align:left;padding:6px;font-size:11px;text-transform:uppercase;color:var(--cx-text-mute)">Unid.</th>'
    +'<th style="text-align:left;padding:6px;font-size:11px;text-transform:uppercase;color:var(--cx-text-mute)">Disposici&oacute;n</th>'
    +'<th style="text-align:left;padding:6px;font-size:11px;text-transform:uppercase;color:var(--cx-text-mute)">Motivo si rechaza</th>'
    +'<th style="padding:6px"></th></tr></thead><tbody>';
  for(var i=0;i<CJS_CAJAS.length;i++){
    var c=CJS_CAJAS[i];
    var foco=(CJS_FOCO===c.caja)?'background:var(--cx-primary-pale)':'';
    h+='<tr style="border-bottom:1px solid var(--cx-border-soft);'+foco+'">'
      +'<td style="padding:6px;font-weight:800">'+c.caja+'</td>'
      +'<td style="padding:6px">'+Number(c.cantidad||0).toLocaleString('es-CO')+'</td>'
      +'<td style="padding:6px"><select onchange="cjsSet('+i+',this.value)" style="padding:5px 8px;border:1px solid var(--cx-border);border-radius:7px;background:var(--cx-bg-soft);color:var(--cx-text);font-size:12.5px">'
        +'<option value="CUARENTENA"'+(c.estado==='CUARENTENA'?' selected':'')+'>Sin revisar</option>'
        +'<option value="APROBADO"'+(c.estado==='APROBADO'?' selected':'')+'>Aprobada</option>'
        +'<option value="RECHAZADO"'+(c.estado==='RECHAZADO'?' selected':'')+'>Rechazada</option>'
      +'</select></td>'
      +'<td style="padding:6px"><input value="'+cjsEsc(c.motivo)+'" oninput="cjsMotivo('+i+',this.value)" placeholder="'+(c.estado==='RECHAZADO'?'obligatorio':'')+'" style="width:100%;padding:5px 8px;border:1px solid var(--cx-border);border-radius:7px;background:var(--cx-bg-soft);color:var(--cx-text);font-size:12.5px"></td>'
      +'<td style="padding:6px"><a href="/rotulos-recepcion-mee?mov='+CJS_MOV+'&caja='+c.caja+'" target="_blank" style="font-size:11.5px;color:var(--cx-primary-text);font-weight:700;text-decoration:none">R&oacute;tulo</a></td></tr>';
  }
  h+='</tbody></table>';
  var box=document.getElementById('cjs-cajas'); if(box)box.innerHTML=h;
  var ap=0,re=0,cu=0,uap=0,ure=0;
  for(var k=0;k<CJS_CAJAS.length;k++){var x=CJS_CAJAS[k];
    if(x.estado==='APROBADO'){ap++;uap+=(x.cantidad||0);}
    else if(x.estado==='RECHAZADO'){re++;ure+=(x.cantidad||0);}
    else cu++;}
  var rs=document.getElementById('cjs-resumen');
  if(rs)rs.innerHTML='<div><b style="color:var(--cx-success-text)">'+ap+'</b> aprobadas &middot; '+uap.toLocaleString('es-CO')+' und</div>'
    +'<div><b style="color:var(--cx-danger-text)">'+re+'</b> rechazadas &middot; '+ure.toLocaleString('es-CO')+' und</div>'
    +'<div><b style="color:var(--cx-warn-text)">'+cu+'</b> sin revisar</div>';
}
async function cjsGuardar(cerrar){
  if(!CJS_MOV)return;
  var payload=CJS_CAJAS.filter(function(c){return c.estado!=='CUARENTENA';})
    .map(function(c){return {caja:c.caja,estado:c.estado,motivo:c.motivo||''};});
  if(!payload.length){alert('Marc&aacute; al menos una caja.');return;}
  var faltan=payload.filter(function(c){return c.estado==='RECHAZADO' && !String(c.motivo||'').trim();});
  if(faltan.length){alert('La caja '+faltan[0].caja+' est&aacute; rechazada sin motivo.');return;}
  if(cerrar){
    var sin=CJS_CAJAS.filter(function(c){return c.estado==='CUARENTENA';}).length;
    if(sin){alert('Quedan '+sin+' caja(s) sin revisar. No se puede cerrar a medias.');return;}
    if(!confirm('Cerrar la revisi&oacute;n? Lo aprobado pasa a stock disponible y lo rechazado queda aparte.'))return;
  }
  var t=await cjsCsrf();
  var r=await fetch('/api/mee/cuarentena/'+CJS_MOV+'/cajas',{method:'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json','X-CSRF-Token':t},
    body:JSON.stringify({cajas:payload,cerrar:!!cerrar})});
  var j=await r.json();
  var mg=document.getElementById('cjs-msg');
  if(!r.ok){ if(mg)mg.innerHTML='<div style="background:var(--cx-danger-pale);color:var(--cx-danger-text);border-radius:9px;padding:10px 13px;font-size:12.5px;margin-top:10px">'+cjsEsc(j.error||'Error')+'</div>'; return; }
  if(cerrar){
    if(mg)mg.innerHTML='<div style="background:var(--cx-success-pale);color:var(--cx-success-text);border-radius:9px;padding:12px 14px;font-size:13px;margin-top:10px"><b>Revisi&oacute;n cerrada.</b> '
      +Number(j.aprobado||0).toLocaleString('es-CO')+' und aprobadas &middot; '+Number(j.rechazado||0).toLocaleString('es-CO')+' und rechazadas.'
      +'<br><a href="'+cjsEsc(j.rotulos_url||'#')+'" target="_blank" style="color:var(--cx-success-text);font-weight:800">Reimprimir los r&oacute;tulos con su estado</a></div>';
    if(typeof loadCC==='function'){try{loadCC();}catch(e){}}
  } else {
    if(mg)mg.innerHTML='<div style="background:var(--cx-primary-pale);color:var(--cx-primary-text);border-radius:9px;padding:10px 13px;font-size:12.5px;margin-top:10px">Guardado. Pod&eacute;s seguir revisando.</div>';
  }
}
'''
