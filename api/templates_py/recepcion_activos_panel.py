"""Pestaña OTROS ACTIVOS de /recepcion · Sebastián 31-jul.

*"Todo lo que llegue se debe recepcionar"*. Tenían puerta la materia prima, los envases, los
consumibles y los equipos. Un computador, una silla o un archivador **no son equipos de planta**:
hasta hoy sólo entraban al libro por el Excel, así que si llegaba un portátil no había dónde
recibirlo y el valor de la empresa quedaba viejo hasta la próxima carga manual.

No lleva calificación (una silla no se califica): entra directo al libro. Lo que sostiene su
valor es la FACTURA, y por eso se pide junto con el resto.

Ids `act-*` y funciones `actv*` propios: el panel se inyecta en una página ajena y una segunda
`function esc` pisaría la de la página sin dar un error (M120/M59).
"""

PANEL_ACTIVOS_HTML = r'''
<div class="actv-wrap">
  <div class="actv-intro">
    <b>Lo que llega y no es materia prima, envase ni equipo de planta:</b> computadores, sillas,
    archivadores, herramientas. Entra <b>directo al libro de activos</b> y suma al valor en libros
    desde que se registra. Lo que sostiene ese valor es la <b>factura</b>, así que conviene cargarla.
  </div>

  <div class="actv-grid">
    <div class="actv-f actv-w2">
      <label>¿Qué llegó? *</label>
      <input id="act-nombre" placeholder="Computador portátil HP 14&quot;" autocomplete="off">
    </div>
    <div class="actv-f">
      <label>Tipo (define el código)</label>
      <select id="act-tipo"></select>
    </div>
    <div class="actv-f">
      <label>Empresa</label>
      <select id="act-empresa">
        <option value="ANIMUS">Ánimus Lab</option>
        <option value="ESPAGIRIA">Espagiria</option>
      </select>
    </div>

    <div class="actv-f">
      <label>Ubicación / área</label>
      <input id="act-ubic" placeholder="Administrativa - Gerencia" autocomplete="off">
    </div>
    <div class="actv-f">
      <label>Responsable</label>
      <input id="act-resp" placeholder="Quién responde por él" autocomplete="off">
    </div>
    <div class="actv-f">
      <label>Proveedor</label>
      <input id="act-prov" autocomplete="off">
    </div>
    <div class="actv-f">
      <label>Factura</label>
      <input id="act-factura" autocomplete="off">
    </div>

    <div class="actv-f">
      <label>Valor (COP)</label>
      <input id="act-valor" type="number" min="0" step="1000" placeholder="0">
    </div>
    <div class="actv-f">
      <label>Fecha de ingreso</label>
      <input id="act-fecha" type="date">
    </div>
    <div class="actv-f">
      <label>¿Cuántos llegaron?</label>
      <input id="act-cant" type="number" min="1" max="50" value="1">
    </div>
    <div class="actv-f">
      <label>Categoría contable</label>
      <select id="act-cat">
        <option>Muebles y enseres</option>
        <option>Equipo de computo</option>
        <option>Maquinaria y equipo</option>
        <option>Otros activos</option>
      </select>
    </div>

    <div class="actv-f actv-w2">
      <label>Notas</label>
      <input id="act-notas" placeholder="Llegó con cargador y garantía de 1 año" autocomplete="off">
    </div>
  </div>

  <div class="actv-acciones">
    <button class="actv-btn actv-primary" id="act-guardar" onclick="actvGuardar()">Registrar en el libro</button>
    <span id="act-msg" class="actv-msg"></span>
  </div>

  <div class="actv-recientes">
    <div class="actv-th">Últimos activos recibidos por acá</div>
    <div id="act-lista" class="actv-lista">Cargando...</div>
  </div>
</div>

<style>
.actv-wrap{padding:4px 0 10px}
.actv-intro{background:var(--cx-primary-pale);border:1px solid var(--cx-primary-soft);border-radius:12px;padding:13px 16px;font-size:13px;color:var(--cx-text-soft);line-height:1.55;margin-bottom:16px}
.actv-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.actv-f{display:flex;flex-direction:column;min-width:0}
.actv-f.actv-w2{grid-column:span 2}
.actv-f label{font-size:11px;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px}
.actv-f input,.actv-f select{border:1px solid var(--cx-border);border-radius:9px;padding:9px 11px;font-size:13.5px;font-family:inherit;background:var(--cx-card);color:var(--cx-text);width:100%}
.actv-f input:focus,.actv-f select:focus{outline:none;border-color:var(--cx-primary-light);box-shadow:0 0 0 3px var(--cx-primary-pale)}
.actv-acciones{display:flex;align-items:center;gap:14px;margin-top:18px;flex-wrap:wrap}
.actv-btn{border:1px solid var(--cx-border);background:var(--cx-card);color:var(--cx-text-soft);border-radius:10px;padding:11px 22px;font-size:13.5px;font-weight:700;cursor:pointer;font-family:inherit}
.actv-btn.actv-primary{background:var(--cx-primary-grad);color:#fff;border-color:transparent}
.actv-btn:disabled{opacity:.55;cursor:default}
.actv-msg{font-size:13px;font-weight:600}
.actv-ok{color:var(--cx-success-text)}.actv-bad{color:var(--cx-danger-text)}
.actv-recientes{margin-top:26px}
.actv-th{font-size:11px;font-weight:800;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px}
.actv-lista{font-size:13px;color:var(--cx-text-soft)}
.actv-row{display:flex;gap:12px;align-items:center;padding:9px 12px;border:1px solid var(--cx-border);border-radius:10px;margin-bottom:7px;background:var(--cx-card);flex-wrap:wrap}
.actv-cod{font-family:ui-monospace,monospace;font-weight:800;color:var(--cx-primary-text)}
@media(max-width:1100px){.actv-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){.actv-grid{grid-template-columns:1fr}.actv-f.actv-w2{grid-column:span 1}}
</style>

<script>
function actvEsc(s){ var d=document.createElement('div'); d.textContent=(s===null||s===undefined)?'':String(s); return d.innerHTML; }
function actvNum(n){ return Number(n||0).toLocaleString('es-CO'); }
function actvCsrf(){ var m=document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/); return m?decodeURIComponent(m[1]):''; }

async function actvCargar(){
  try{
    var r = await fetch('/api/recepcion/activos', {credentials:'same-origin'});
    var d = await r.json();
    if(!r.ok||!d.ok){ document.getElementById('act-lista').textContent='No se pudo cargar.'; return; }
    var sel = document.getElementById('act-tipo');
    if(sel && !sel.options.length){
      (d.tipos||[]).forEach(function(t){
        var o=document.createElement('option'); o.value=t.prefijo; o.textContent=t.nombre; sel.appendChild(o);
      });
    }
    var f = document.getElementById('act-fecha');
    if(f && !f.value) f.value = d.hoy || '';
    if(d.puede_registrar===false){
      var b=document.getElementById('act-guardar');
      if(b){ b.disabled=true; b.title='Solo Compras, Luz o un admin'; }
    }
    actvPintar(d.items||[]);
  }catch(e){ document.getElementById('act-lista').textContent='Error de red.'; }
}

function actvPintar(items){
  var el = document.getElementById('act-lista');
  if(!items.length){ el.innerHTML='<div style="color:var(--cx-text-faint)">Todavía no se ha recibido ningún activo por acá.</div>'; return; }
  el.innerHTML = items.map(function(x){
    return '<div class="actv-row">'+
      '<span class="actv-cod">'+actvEsc(x.codigo)+'</span>'+
      '<span style="flex:1;min-width:170px">'+actvEsc(x.nombre)+'</span>'+
      '<span style="color:var(--cx-text-faint)">'+actvEsc(x.ubicacion||'')+' '+actvEsc(x.responsable||'')+'</span>'+
      (x.valor_cop? '<span style="font-weight:700">$'+actvNum(x.valor_cop)+'</span>':'')+
    '</div>';
  }).join('');
}

async function actvGuardar(){
  if(window._actvBusy) return;
  var msg = document.getElementById('act-msg');
  var val = function(id){ var e=document.getElementById(id); return e? String(e.value||'').trim() : ''; };
  var nombre = val('act-nombre');
  if(!nombre){ msg.className='actv-msg actv-bad'; msg.textContent='Falta decir qué llegó.'; return; }
  window._actvBusy = true;
  var btn = document.getElementById('act-guardar');
  if(btn) btn.disabled = true;
  msg.className='actv-msg'; msg.textContent='Registrando...';
  try{
    var body = {
      nombre: nombre, tipo_prefijo: val('act-tipo'), empresa: val('act-empresa'),
      tipo_bien: (document.getElementById('act-tipo')||{}).selectedOptions ?
                 document.getElementById('act-tipo').selectedOptions[0].textContent : '',
      ubicacion: val('act-ubic'), responsable: val('act-resp'), proveedor: val('act-prov'),
      factura: val('act-factura'), valor_cop: parseFloat(val('act-valor')||'0')||0,
      fecha_ingreso: val('act-fecha'), cantidad: parseInt(val('act-cant')||'1',10)||1,
      categoria_contable: val('act-cat'), notas: val('act-notas')
    };
    var r = await fetch('/api/recepcion/activos', {method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':actvCsrf()}, body: JSON.stringify(body)});
    var d = await r.json();
    if(!r.ok||!d.ok){
      msg.className='actv-msg actv-bad';
      msg.textContent = (d && d.error) ? d.error : ('No se pudo registrar (HTTP '+r.status+')');
      return;
    }
    msg.className='actv-msg actv-ok';
    msg.innerHTML = actvEsc(d.mensaje||'Listo.')+' &middot; <b>'+(d.codigos||[]).join(', ')+'</b>';
    ['act-nombre','act-notas','act-factura'].forEach(function(id){
      var e=document.getElementById(id); if(e) e.value='';
    });
    var c=document.getElementById('act-cant'); if(c) c.value='1';
    actvCargar();
  }catch(e){
    msg.className='actv-msg actv-bad'; msg.textContent='Error de red al registrar.';
  }finally{
    window._actvBusy = false;
    if(btn) btn.disabled = false;
  }
}

try{ actvCargar(); }catch(e){}
</script>
'''
