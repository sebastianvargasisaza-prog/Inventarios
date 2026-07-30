"""Pestaña EQUIPOS de /recepcion · Sebastián 30-jul.

*"Los equipos llegan, necesito que Compras los recepcione, o Luz en Espagiria"*. Va acá y no en
una página nueva: el punto de entrada lo define el TIPO de cosa que llega (M120).

El panel se INYECTA dentro de `/recepcion`, que es una página ajena y enorme. Por eso:
  · todos los ids empiezan con `eqp-` y todas las funciones con `eqp`: una segunda `function esc`
    pisaría la de la página sin dar un solo error (M120/M59);
  · no se reusa el conmutador de pestañas de la página (apaga todo antes de encender y dejaría
    la pantalla en blanco si el destino no es suyo · M61/M112);
  · se inyecta UNA vez, con assert en la ruta: si el placeholder no matchea, la pestaña queda
    con botones llamando a funciones que nunca se cargaron (M116).

Colores por token `var(--cx-*)`: sin hex propios, que el trinquete de diseño mide (M104).
"""

PANEL_EQUIPOS_HTML = r'''
<div class="eqp-wrap">
  <div class="eqp-intro">
    <b>Llegó un equipo.</b> Se registra acá con lo que trae (serial, marca, factura, cuánto costó)
    y queda <b>PENDIENTE de calificación</b>: hasta que Aseguramiento no lo califique (IQ/OQ/PQ)
    no se puede usar en producción, igual que una materia prima en cuarentena.
    Al guardar salen los rótulos con código de barras para pegarle a cada uno.
  </div>

  <div class="eqp-grid">
    <div class="eqp-f eqp-w2">
      <label>Nombre del equipo *</label>
      <input id="eqp-nombre" placeholder="Balanza analítica AXIS" autocomplete="off">
    </div>
    <div class="eqp-f">
      <label>Tipo (define el código)</label>
      <select id="eqp-tipo"></select>
    </div>
    <div class="eqp-f">
      <label>Empresa</label>
      <select id="eqp-empresa">
        <option value="ESPAGIRIA">Espagiria</option>
        <option value="ANIMUS">Ánimus Lab</option>
      </select>
    </div>

    <div class="eqp-f">
      <label>Área</label>
      <input id="eqp-area" list="eqp-areas" placeholder="FAB1" autocomplete="off">
      <datalist id="eqp-areas"></datalist>
    </div>
    <div class="eqp-f">
      <label>Ubicación (texto libre)</label>
      <input id="eqp-ubic" placeholder="Fabricación 1" autocomplete="off">
    </div>
    <div class="eqp-f">
      <label>Marca</label>
      <input id="eqp-marca" autocomplete="off">
    </div>
    <div class="eqp-f">
      <label>Modelo</label>
      <input id="eqp-modelo" autocomplete="off">
    </div>

    <div class="eqp-f">
      <label>Serial <span class="eqp-hint">(identifica UN equipo)</span></label>
      <input id="eqp-serial" autocomplete="off">
    </div>
    <div class="eqp-f">
      <label>Capacidad</label>
      <input id="eqp-cap" placeholder="220 g d=0,1 mg" autocomplete="off">
    </div>
    <div class="eqp-f">
      <label>Proveedor</label>
      <input id="eqp-prov" autocomplete="off">
    </div>
    <div class="eqp-f">
      <label>Factura</label>
      <input id="eqp-factura" autocomplete="off">
    </div>

    <div class="eqp-f">
      <label>Orden de compra <span class="eqp-hint">(si tiene)</span></label>
      <input id="eqp-oc" autocomplete="off">
    </div>
    <div class="eqp-f">
      <label>Valor (COP)</label>
      <input id="eqp-valor" type="number" min="0" step="1000" placeholder="0">
    </div>
    <div class="eqp-f">
      <label>Fecha de ingreso</label>
      <input id="eqp-fecha" type="date">
    </div>
    <div class="eqp-f">
      <label>¿Cuántos llegaron?</label>
      <input id="eqp-cant" type="number" min="1" max="20" value="1">
    </div>

    <div class="eqp-f eqp-w2">
      <label>Código <span class="eqp-hint">(dejalo vacío y EOS lo numera solo)</span></label>
      <input id="eqp-codigo" placeholder="BL-PRD-007" autocomplete="off">
    </div>
    <div class="eqp-f eqp-w2">
      <label>Notas</label>
      <input id="eqp-notas" placeholder="Llegó con cargador y certificado del fabricante" autocomplete="off">
    </div>
  </div>

  <div class="eqp-actions">
    <button class="eqp-btn eqp-primary" id="eqp-guardar" onclick="eqpGuardar()">Registrar la llegada</button>
    <span id="eqp-msg" class="eqp-msg"></span>
  </div>

  <div class="eqp-recientes">
    <div class="eqp-th">Últimos equipos recibidos</div>
    <div id="eqp-lista" class="eqp-lista">Cargando...</div>
  </div>
</div>

<style>
.eqp-wrap{padding:4px 0 10px}
.eqp-intro{background:var(--cx-primary-pale);border:1px solid var(--cx-primary-soft);border-radius:12px;padding:13px 16px;font-size:13px;color:var(--cx-text-soft);line-height:1.55;margin-bottom:16px}
.eqp-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.eqp-f{display:flex;flex-direction:column;min-width:0}
.eqp-f.eqp-w2{grid-column:span 2}
.eqp-f label{font-size:11px;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px}
.eqp-hint{text-transform:none;letter-spacing:0;font-weight:600;color:var(--cx-text-faint)}
.eqp-f input,.eqp-f select{border:1px solid var(--cx-border);border-radius:9px;padding:9px 11px;font-size:13.5px;font-family:inherit;background:var(--cx-card);color:var(--cx-text);width:100%}
.eqp-f input:focus,.eqp-f select:focus{outline:none;border-color:var(--cx-primary-light);box-shadow:0 0 0 3px var(--cx-primary-pale)}
.eqp-actions{display:flex;align-items:center;gap:14px;margin-top:18px;flex-wrap:wrap}
.eqp-btn{border:1px solid var(--cx-border);background:var(--cx-card);color:var(--cx-text-soft);border-radius:10px;padding:11px 22px;font-size:13.5px;font-weight:700;cursor:pointer;font-family:inherit}
.eqp-btn.eqp-primary{background:var(--cx-primary-grad);color:#fff;border-color:transparent}
.eqp-btn:disabled{opacity:.55;cursor:default}
.eqp-msg{font-size:13px;font-weight:600}
.eqp-ok{color:var(--cx-success-text)}.eqp-bad{color:var(--cx-danger-text)}
.eqp-recientes{margin-top:26px}
.eqp-th{font-size:11px;font-weight:800;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px}
.eqp-lista{font-size:13px;color:var(--cx-text-soft)}
.eqp-row{display:flex;gap:12px;align-items:center;padding:9px 12px;border:1px solid var(--cx-border);border-radius:10px;margin-bottom:7px;background:var(--cx-card);flex-wrap:wrap}
.eqp-cod{font-family:ui-monospace,monospace;font-weight:800;color:var(--cx-primary-text)}
.eqp-tag{font-size:10.5px;font-weight:800;border-radius:999px;padding:2px 10px;text-transform:uppercase;letter-spacing:.03em}
.eqp-tag.pend{background:var(--cx-warn-pale);color:var(--cx-warn-text)}
.eqp-tag.cal{background:var(--cx-success-pale);color:var(--cx-success-text)}
.eqp-tag.rech{background:var(--cx-danger-pale);color:var(--cx-danger-text)}
@media(max-width:1100px){.eqp-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.eqp-f.eqp-w2{grid-column:span 2}}
@media(max-width:620px){.eqp-grid{grid-template-columns:1fr}.eqp-f.eqp-w2{grid-column:span 1}}
</style>

<script>
function eqpEsc(s){ var d=document.createElement('div'); d.textContent=(s===null||s===undefined)?'':String(s); return d.innerHTML; }
function eqpNum(n){ return Number(n||0).toLocaleString('es-CO'); }
function eqpCsrf(){ var m=document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/); return m?decodeURIComponent(m[1]):''; }

async function eqpCargar(){
  try{
    var r = await fetch('/api/recepcion/equipos', {credentials:'same-origin'});
    var d = await r.json();
    if(!r.ok||!d.ok){ document.getElementById('eqp-lista').textContent='No se pudo cargar.'; return; }
    var sel = document.getElementById('eqp-tipo');
    if(sel && !sel.options.length){
      (d.tipos||[]).forEach(function(t){
        var o=document.createElement('option'); o.value=t.prefijo; o.textContent=t.nombre; sel.appendChild(o);
      });
    }
    var dl = document.getElementById('eqp-areas');
    if(dl && !dl.children.length){
      (d.areas||[]).forEach(function(a){ var o=document.createElement('option'); o.value=a; dl.appendChild(o); });
    }
    var f = document.getElementById('eqp-fecha');
    if(f && !f.value) f.value = d.hoy || '';
    if(d.puede_registrar===false){
      var b=document.getElementById('eqp-guardar');
      if(b){ b.disabled=true; b.title='Solo Compras, Luz o un admin registran equipos'; }
    }
    eqpPintar(d.items||[]);
  }catch(e){ document.getElementById('eqp-lista').textContent='Error de red.'; }
}

function eqpPintar(items){
  var el = document.getElementById('eqp-lista');
  if(!items.length){ el.innerHTML='<div style="color:var(--cx-text-faint)">Todavía no se ha recibido ningún equipo por acá.</div>'; return; }
  el.innerHTML = items.map(function(x){
    var est = String(x.estado_calificacion||'');
    var cls = est==='CALIFICADO' ? 'cal' : (est==='RECHAZADO' ? 'rech' : 'pend');
    var txt = est==='PENDIENTE' ? 'pendiente de calificar' : est.toLowerCase();
    return '<div class="eqp-row">'+
      '<span class="eqp-cod">'+eqpEsc(x.codigo)+'</span>'+
      '<span style="flex:1;min-width:160px">'+eqpEsc(x.nombre)+
        (x.serial? ' <span style="color:var(--cx-text-faint)">serial '+eqpEsc(x.serial)+'</span>':'')+'</span>'+
      '<span style="color:var(--cx-text-faint)">'+eqpEsc(x.area||'')+' '+eqpEsc(x.fecha_ingreso||'')+'</span>'+
      (x.valor_cop? '<span style="color:var(--cx-text-faint)">$'+eqpNum(x.valor_cop)+'</span>':'')+
      '<span class="eqp-tag '+cls+'">'+eqpEsc(txt)+'</span>'+
      '<button class="eqp-btn" style="padding:5px 12px;font-size:12px" onclick="eqpRotulo(\''+eqpEsc(x.codigo)+'\')">Rótulo</button>'+
    '</div>';
  }).join('');
}

function eqpRotulo(cod){ window.open('/rotulos-equipo?cods='+encodeURIComponent(cod), '_blank'); }

async function eqpGuardar(){
  if(window._eqpBusy) return;                 // doble click = dos equipos fantasma (M63)
  var msg = document.getElementById('eqp-msg');
  var val = function(id){ var e=document.getElementById(id); return e? String(e.value||'').trim() : ''; };
  var nombre = val('eqp-nombre');
  if(!nombre){ msg.className='eqp-msg eqp-bad'; msg.textContent='Falta el nombre del equipo.'; return; }
  var cant = parseInt(val('eqp-cant')||'1', 10) || 1;
  if(cant>1 && val('eqp-serial')){
    msg.className='eqp-msg eqp-bad';
    msg.textContent='El serial identifica UN equipo: registralos de a uno, o dejá el serial vacío.';
    return;
  }
  window._eqpBusy = true;
  var btn = document.getElementById('eqp-guardar');
  if(btn) btn.disabled = true;
  msg.className='eqp-msg'; msg.textContent='Registrando...';
  try{
    var body = {
      nombre: nombre, tipo_prefijo: val('eqp-tipo'), empresa: val('eqp-empresa'),
      area_codigo: val('eqp-area'), ubicacion: val('eqp-ubic'), marca: val('eqp-marca'),
      modelo: val('eqp-modelo'), serial: val('eqp-serial'), capacidad: val('eqp-cap'),
      proveedor: val('eqp-prov'), factura: val('eqp-factura'), numero_oc: val('eqp-oc'),
      valor_cop: parseFloat(val('eqp-valor')||'0')||0, fecha_ingreso: val('eqp-fecha'),
      cantidad: cant, codigo: val('eqp-codigo'), notas: val('eqp-notas')
    };
    var r = await fetch('/api/recepcion/equipos', {method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':eqpCsrf()}, body: JSON.stringify(body)});
    var d = await r.json();
    if(!r.ok||!d.ok){
      msg.className='eqp-msg eqp-bad';
      msg.textContent = (d && d.error) ? d.error : ('No se pudo registrar (HTTP '+r.status+')');
      return;
    }
    msg.className='eqp-msg eqp-ok';
    msg.innerHTML = eqpEsc(d.mensaje||'Listo.')+' &middot; <b>'+(d.codigos||[]).join(', ')+'</b>';
    ['eqp-nombre','eqp-serial','eqp-codigo','eqp-notas'].forEach(function(id){
      var e=document.getElementById(id); if(e) e.value='';
    });
    var c=document.getElementById('eqp-cant'); if(c) c.value='1';
    window.open('/rotulos-equipo?cods='+encodeURIComponent((d.codigos||[]).join(',')), '_blank');
    eqpCargar();
  }catch(e){
    msg.className='eqp-msg eqp-bad'; msg.textContent='Error de red al registrar.';
  }finally{
    window._eqpBusy = false;
    if(btn) btn.disabled = false;
  }
}

try{ eqpCargar(); }catch(e){}
</script>
'''
