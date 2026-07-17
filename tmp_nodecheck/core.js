
var fData=[], allStock=[], _cat={}, _ultimoIng=null;
var formulasPin=false;
var _lotes=[], _lotesFull=[], _meeData=[], _prodPendiente=null;
// PERF 26-jun (Increment 2) · usuario/es_admin se inyectan en el script inline de arriba
// (window.__DASH_USR/__DASH_ADMIN) para que ESTE bloque quede SIN interpolaciones y se pueda extraer
// a /planta-core.js cacheable. Mismo valor que antes.
var OPER_ACTUAL=window.__DASH_USR||'';
// BUG-4 fix · 20-may-2026 Dashboard PRO audit · es_admin REAL desde
// backend (core.py:444 inyecta el placeholder desde ADMIN_USERS).
// Antes había listas hardcoded en JS que mentían a la UI.
window._ES_ADMIN_DASH=(window.__DASH_ADMIN===true);
// BUG-6 fix · 20-may-2026 Dashboard PRO audit: cargar CSRF token al boot
// y guardar en window._csrfTok. Antes los helpers leían cookie inexistente.
window._csrfTok=window._csrfTok||'';
fetch('/api/csrf-token', {credentials:'same-origin'})
  .then(function(r){return r.ok ? r.json() : null;})
  .then(function(d){if(d&&d.csrf_token) window._csrfTok=d.csrf_token;})
  .catch(function(){});

// Sebastián 20-may-2026 · Fix masivo: 84 fetch POST en dashboard solo 26
// tenían X-CSRF-Token explícito · el resto fallaba con 403/400 cuando el
// middleware exigía CSRF (PIN, registrar producción, etc.). Este
// interceptor parchea window.fetch UNA VEZ y agrega:
//   - X-CSRF-Token automático en todo non-GET/HEAD
//   - credentials: 'same-origin' default
// Idempotente (window._FETCH_CSRF_PATCHED). No toca llamadas que ya
// pusieron su propio header (case-insensitive).
(function(){
  if(window._FETCH_CSRF_PATCHED) return;
  window._FETCH_CSRF_PATCHED = true;
  var origFetch = window.fetch;
  window.fetch = function(input, init){
    try{
      init = init || {};
      var method = ((init.method) || (typeof input === 'object' && input && input.method) || 'GET').toUpperCase();
      if(method !== 'GET' && method !== 'HEAD'){
        // Normalizar headers a plain object para inspeccionar/agregar
        var h = init.headers;
        if(!h) h = {};
        else if(h instanceof Headers){
          var tmp = {};
          h.forEach(function(v,k){ tmp[k] = v; });
          h = tmp;
        }
        var hasCsrf = false;
        for(var k in h){ if(k.toLowerCase() === 'x-csrf-token'){ hasCsrf = true; break; } }
        if(!hasCsrf){
          var tok = '';
          if(typeof csrfTokenNec === 'function'){ try{ tok = csrfTokenNec(); }catch(_){} }
          if(!tok && window._csrfTok) tok = window._csrfTok;
          if(!tok){
            var m = (document.cookie || '').match(/(?:^|; )csrf_token=([^;]*)/);
            if(m) try{ tok = decodeURIComponent(m[1]); }catch(_){ tok = m[1]; }
          }
          if(tok) h['X-CSRF-Token'] = tok;
        }
        init.headers = h;
        if(!init.credentials) init.credentials = 'same-origin';
      }
    }catch(_){}
    return origFetch.call(this, input, init);
  };
})();
document.addEventListener('DOMContentLoaded',function(){
  // Restaurar operador desde localStorage si no vino por sesión
  if(!OPER_ACTUAL){
    try{var saved=localStorage.getItem('espagiria_operador');if(saved)OPER_ACTUAL=saved;}catch(e){}
  }
  // Pre-cargar lista de proveedores para los datalists (recepcion, catalogo,
  // editar lote, solicitar). Idempotente: si ya se cargo, no hace nada.
  if(typeof _cargarProveedoresUnicos==='function'){_cargarProveedoresUnicos();}
  var c=document.getElementById('oper-chip');
  if(OPER_ACTUAL){
    if(c) c.innerHTML='<span onclick="cambiarOperador()" title="Cambiar operador" style="cursor:pointer;">&#128100; '+OPER_ACTUAL+' <span style="font-size:0.75em;opacity:0.7;">[cambiar]</span></span>';
    loadDashboardCompleto();loadFormulas();
  setTimeout(cargarEnvasadoSimpleTab, 1500);
  } else {
    // Sin operador identificado: mostrar modal antes de cargar
    document.getElementById('modal-operador').style.display='flex';
    setTimeout(function(){var inp=document.getElementById('oper-input');if(inp)inp.focus();},150);
  }
  // Sebastián 31-may-2026 · abrir pestaña según el hash de la URL (ej. /inventarios#cuarentena)
  setTimeout(_openTabFromHash, 700);
});
// Abre la pestaña indicada en location.hash (deep-link desde el menú de módulos)
function _openTabFromHash(){
  var h = (location.hash || '').replace('#','').trim();
  if(!h) return;
  var valid = ['dashboard','stock','empaque','programacion','formulas','produccion',
               'cuarentena','alertas','movimientos','ingreso','abc'];
  if(valid.indexOf(h) < 0) return;
  var btn = null;
  document.querySelectorAll('.tab-button').forEach(function(b){
    if((b.getAttribute('onclick')||'').indexOf("'"+h+"'") >= 0) btn = b;
  });
  try{ switchTab(h, btn); }catch(e){}
}
window.addEventListener('hashchange', _openTabFromHash);
var _ajDat={};
function _eq(s){return (s||'').split("'").join('&#39;');}
function selOper(n){
  OPER_ACTUAL=n;
  try{localStorage.setItem('espagiria_operador',n);}catch(e){}
  document.getElementById('modal-operador').style.display='none';
  var c=document.getElementById('oper-chip');if(c)c.innerHTML='<span onclick="cambiarOperador()" title="Cambiar operador" style="cursor:pointer;">&#128100; '+n+' <span style="font-size:0.75em;opacity:0.7;">[cambiar]</span></span>';
  loadDashboardCompleto();loadFormulas();
}
function cambiarOperador(){
  try{localStorage.removeItem('espagiria_operador');}catch(e){}
  document.getElementById('oper-input').value=OPER_ACTUAL||'';
  document.getElementById('modal-operador').style.display='flex';
  setTimeout(function(){document.getElementById('oper-input').focus();},100);
}
function confirmarOper(){var inp=document.getElementById('oper-input');var n=(inp?inp.value:'').trim();if(!n){var e=document.getElementById('oper-error');if(e)e.style.display='block';return;}selOper(n);}
function abrirAjusteIdx(idx){
  var i=_lotes[idx];
  if(!i)return;
  abrirAjuste(i.material_id,i.material_nombre,i.lote||"",i.cantidad_g,i.estanteria||"",i.posicion||"",i.fecha_vencimiento||"");
}
function reimprimirRotuloLote(idx){
  // Sebastián 9-jul: re-imprimir el rótulo de un lote desde Stock por Lote (si se dañó/perdió la etiqueta).
  var i=_lotes[idx];
  if(!i)return;
  var cod=i.material_id||'';
  var lote=i.lote||'SL';
  var cant=parseFloat(i.cantidad_g)||0;
  if(!cod){alert('Este lote no tiene código de MP');return;}
  window.open('/rotulo-recepcion/'+encodeURIComponent(cod)+'/'+encodeURIComponent(lote)+'/'+cant.toFixed(1),'_blank');
}

// ─── Solicitar MP (a nivel materia prima, no lote) ─────────────────────────
var _solLote=null;
function abrirSolicitarLote(idx){
  var i=_lotes[idx]; if(!i){alert('Lote no encontrado'); return;}
  _solLote=i;
  document.getElementById('sol-mp-nombre').textContent=(i.material_nombre||'')+(i.nombre_inci?' ('+i.nombre_inci+')':'');
  document.getElementById('sol-mp-cod').textContent='Codigo: '+(i.material_id||'-');
  var stock_label='Stock min: '+(i.stock_min_g||0).toLocaleString()+' g';
  if(i.lote){stock_label+=' · Lote ref.: '+i.lote;}
  document.getElementById('sol-mp-stock').textContent=stock_label;
  document.getElementById('sol-prov').value=i.proveedor||'';
  document.getElementById('sol-cant').value='';
  document.getElementById('sol-unidad').value='g';
  document.getElementById('sol-urg').value='Normal';
  document.getElementById('sol-obs').value='';
  document.getElementById('sol-msg').innerHTML='';
  // Cargar proveedores existentes en el desplegable (mismo datalist global
  // que usa Editar Proveedor) — evita typos y registra implicitamente
  // proveedores nuevos cuando el usuario escribe uno que no esta en la lista.
  _cargarProveedoresUnicos();
  document.getElementById('modal-solicitar-lote').style.display='flex';
}
function cerrarSolicitarLote(){document.getElementById('modal-solicitar-lote').style.display='none';_solLote=null;}
async function enviarSolicitarLote(){
  if(!_solLote)return;
  var msg=document.getElementById('sol-msg');
  var prov=document.getElementById('sol-prov').value.trim();
  var cant=parseFloat(document.getElementById('sol-cant').value||0);
  var und=document.getElementById('sol-unidad').value;
  var urg=document.getElementById('sol-urg').value;
  var obs=document.getElementById('sol-obs').value.trim();
  if(!cant||cant<=0){msg.innerHTML='<span style="color:#c00;">Cantidad debe ser mayor a 0.</span>';return;}
  if(obs.length<5){msg.innerHTML='<span style="color:#c00;">Justificacion requerida (min. 5 chars).</span>';return;}
  // Convertir a gramos para solicitudes_compra (cantidad_g)
  var cant_g=cant; if(und==='kg')cant_g=cant*1000;
  var obs_full=obs+(prov?(' · Proveedor sugerido: '+prov):'');
  var mp_codigo = _solLote.material_id;
  var mp_nombre = _solLote.material_nombre;
  // Sprint Bodega MP PRO · 20-may-2026 fix #12: si no hay OPER_ACTUAL,
  // bloquear (antes mandaba 'planta' genérico · pérdida de trazabilidad).
  var solicitante = window.OPER_ACTUAL || window._usuario || '';
  if(!solicitante){
    msg.innerHTML='<span style="color:#c00;">Identificate primero · click "Cambiar operador" arriba.</span>';
    return;
  }
  var payload={
    solicitante:solicitante,
    urgencia:urg,
    observaciones:obs_full,
    empresa:'Espagiria',
    categoria:'Materia Prima',
    tipo:'Compra',
    area:'Produccion',
    items:[{
      codigo_mp:mp_codigo,
      nombre_mp:mp_nombre,
      cantidad_g:cant_g,
      unidad:und,
      justificacion:obs,
      valor_estimado:0
    }]
  };
  msg.innerHTML='<span style="color:#666;">Enviando...</span>';
  try{
    var r=await fetch('/api/solicitudes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    var d=await r.json();
    if(r.ok){
      // Sebastian 5-may-2026 (Luis Enrique): ANTES feedback duraba 1.8s
      // dentro del modal y luego se cerraba · operario decia "no hace
      // nada". AHORA toast persistente fuera del modal + refresh de lista
      // para que aparezca badge "💼 Solicitada" en el lote.
      cerrarSolicitarLote();
      _toastSolicitudCreada(d.numero || '?', mp_codigo, mp_nombre,
                              cant, und);
      // Refresh stock para que el badge "Solicitada" aparezca de inmediato
      try{ await loadStock(); }catch(e){/* no critico */}
    }else{
      msg.innerHTML='<span style="color:#c00;">Error: '+_escHTML(d.error||r.status)+'</span>';
    }
  }catch(e){
    msg.innerHTML='<span style="color:#c00;">Error de red: '+_escHTML(e.message)+'</span>';
  }
}

// Sebastian 5-may-2026: toast persistente para feedback de solicitud
// creada · imposible de ignorar. Aparece arriba a la derecha por 8s.
function _toastSolicitudCreada(numero, codigo, nombre, cant, und){
  // Cerrar uno previo si lo hay
  var prev = document.getElementById('toast-sol-creada');
  if(prev) prev.remove();
  var t = document.createElement('div');
  t.id = 'toast-sol-creada';
  t.style.cssText = 'position:fixed;top:24px;right:24px;z-index:99999;'+
    'background:#fff;border:2px solid #16a34a;border-radius:12px;'+
    'box-shadow:0 12px 40px rgba(0,0,0,0.18);max-width:360px;'+
    'animation:slideInToast 0.3s ease-out';
  t.innerHTML =
    '<div style="background:#16a34a;color:#fff;padding:10px 16px;'+
      'border-radius:10px 10px 0 0;display:flex;align-items:center;gap:10px">'+
      '<div style="font-size:22px">&#x2705;</div>'+
      '<div style="flex:1">'+
        '<div style="font-weight:700;font-size:14px">Solicitud enviada a Compras</div>'+
        '<div style="font-size:11px;opacity:0.9;font-family:monospace">'+_escHTML(numero)+'</div>'+
      '</div>'+
      '<button onclick="document.getElementById(\'toast-sol-creada\').remove()" '+
        'style="background:transparent;color:#fff;border:none;font-size:18px;'+
        'cursor:pointer;padding:0 6px;line-height:1">&#10005;</button>'+
    '</div>'+
    '<div style="padding:12px 16px">'+
      '<div style="font-size:13px;color:#1f2937;margin-bottom:4px">'+
        '<b>'+_escHTML(nombre||codigo)+'</b></div>'+
      '<div style="font-size:12px;color:#475569">'+
        Number(cant).toLocaleString()+' '+_escHTML(und)+
        ' · queda como <b>Solicitada</b> en este lote</div>'+
      '<div style="margin-top:8px;font-size:11px;color:#64748b">'+
        '&#x2192; Catalina la procesará en <a href="/compras" target="_blank" '+
        'style="color:#7c3aed;text-decoration:underline">Compras</a></div>'+
    '</div>';
  document.body.appendChild(t);
  // Auto-dismiss en 8s (suficiente para que Luis lo vea)
  setTimeout(function(){
    var el = document.getElementById('toast-sol-creada');
    if(el){
      el.style.transition='opacity 0.5s';
      el.style.opacity='0';
      setTimeout(function(){ if(el.parentNode) el.remove(); }, 500);
    }
  }, 8000);
}

// ─── Editar Proveedor (afecta lote + catalogo MP) ──────────────────────────
var _epLote=null; var _epProveedoresCargados=false;
async function _cargarProveedoresUnicos(){
  if(_epProveedoresCargados)return;
  try{
    var r=await fetch('/api/proveedores-unicos');
    if(!r.ok)return;
    var d=await r.json();
    var dl=document.getElementById('prov-list-global');
    if(!dl)return;
    dl.innerHTML='';
    (d.proveedores||[]).forEach(function(p){
      var o=document.createElement('option'); o.value=p; dl.appendChild(o);
    });
    _epProveedoresCargados=true;
  }catch(e){/* no critico */}
}
function abrirEditarProveedor(idx){
  var i=_lotes[idx]; if(!i){alert('Lote no encontrado'); return;}
  _epLote=i;
  var info=(i.material_nombre||'')+' · '+(i.material_id||'');
  if(i.lote)info+=' · Lote '+i.lote;
  document.getElementById('ep-mp-info').textContent=info;
  document.getElementById('ep-prov-actual').textContent='Proveedor actual: '+(i.proveedor||'(vacio)');
  document.getElementById('ep-input').value=i.proveedor||'';
  document.getElementById('ep-msg').innerHTML='';
  document.getElementById('ep-hint').textContent='Sugerencia: usa el desplegable para evitar duplicados por typo.';
  _cargarProveedoresUnicos();
  document.getElementById('modal-editar-prov').style.display='flex';
  setTimeout(function(){var el=document.getElementById('ep-input');if(el)el.focus();},120);
}
function cerrarEditarProveedor(){document.getElementById('modal-editar-prov').style.display='none';_epLote=null;}
async function guardarProveedor(){
  if(!_epLote)return;
  var msg=document.getElementById('ep-msg');
  var nuevo=document.getElementById('ep-input').value.trim();
  if(nuevo.length<2){msg.innerHTML='<span style="color:#c00;">Proveedor debe tener al menos 2 caracteres.</span>';return;}
  if(nuevo===(_epLote.proveedor||'')){msg.innerHTML='<span style="color:#888;">Sin cambios — el proveedor es el mismo.</span>';return;}
  msg.innerHTML='<span style="color:#666;">Guardando...</span>';
  var loteSeg=_epLote.lote||'_SIN_LOTE_';
  var url='/api/lotes/'+encodeURIComponent(_epLote.material_id)+'/'+encodeURIComponent(loteSeg)+'/proveedor';
  try{
    var r=await fetch(url,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({proveedor:nuevo})});
    var d=await r.json();
    if(r.ok){
      msg.innerHTML='<span style="color:#1a8a1a;font-weight:700;">✓ '+(d.message||'Proveedor actualizado')+'</span>';
      _epProveedoresCargados=false; // re-cargar lista la proxima vez (incluye nuevo si lo creo)
      setTimeout(function(){cerrarEditarProveedor();loadStock();},1500);
    }else{
      msg.innerHTML='<span style="color:#c00;">Error: '+(d.error||r.status)+(d.detail?' — '+d.detail:'')+'</span>';
    }
  }catch(e){
    msg.innerHTML='<span style="color:#c00;">Error de red: '+e.message+'</span>';
  }
}

// ─── Helpers globales de formato ───────────────────────────────────────────
function _escHTML(s){return String(s||'').replace(/[&<>"']/g,function(ch){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];});}

/**
 * jsonFetch · helper resiliente para fetch + JSON.parse.
 * Sebastián 1-may-2026: Render devuelve HTML en 502/503 → JSON.parse crash.
 * Este helper intenta JSON, si falla detecta HTML/text y devuelve {error}.
 *
 * Uso:
 *   var d = await jsonFetch('/api/x');           // GET con credentials
 *   var d = await jsonFetch('/api/x', {method:'POST', body: JSON.stringify({})});
 *
 * Throws solo si network fail. Para errores HTTP/parse devuelve objeto:
 *   { ok: false, status: N, error: '...', _raw: '...' }
 */
async function jsonFetch(url, opts){
  opts = opts || {};
  if(!opts.credentials) opts.credentials = 'same-origin';
  if(opts.body && !(opts.headers && opts.headers['Content-Type'])){
    opts.headers = Object.assign({'Content-Type':'application/json'}, opts.headers||{});
  }
  var r;
  try { r = await fetch(url, opts); }
  catch(e){ return {ok:false, status:0, error:'Sin conexión: '+(e.message||e)}; }
  var text = '';
  try { text = await r.text(); } catch(e){ text = ''; }
  // Detectar HTML (Render 502, login redirect, etc)
  if(text && (text.charAt(0) === '<' || text.indexOf('<!DOCTYPE') === 0 || text.indexOf('<html') >= 0)){
    return {
      ok: false, status: r.status,
      error: r.status === 502 || r.status === 503
        ? 'Servidor reiniciando · espera 10s y reintenta'
        : (r.status === 401 ? 'Sesión expirada · recarga la página' : 'Error '+r.status+' (HTML)'),
      _raw: text.substring(0, 200),
    };
  }
  // Intentar JSON
  var d = null;
  try { d = text ? JSON.parse(text) : {}; }
  catch(e){
    return {ok:false, status:r.status, error:'Respuesta no es JSON: '+(text.substring(0,80)||'(vacío)')};
  }
  // Adjuntar status si no lo trae
  if(typeof d.ok === 'undefined') d.ok = r.ok && !d.error;
  if(typeof d.status === 'undefined') d.status = r.status;
  return d;
}
// _fmtMiles: separador de miles estilo Colombia (1.234.567). Usado por
// MP rolling forecast y otros paneles. (Sebastian 1-may-2026: error global
// "_fmtMiles no está definido" reportado en producción.)
function _fmtMiles(n){
  if(n===null||n===undefined||isNaN(n)) return '0';
  try{ return Math.round(Number(n)).toLocaleString('es-CO'); }
  catch(e){ return String(Math.round(Number(n))).replace(/\B(?=(\d{3})+(?!\d))/g,'.'); }
}
// ── Sebastian 5-may-2026 (Bodega MP): revisar mínimos de stock_minimo ──
// Antes la auditoria solo era accesible desde /admin · operario tipico
// no la veia. Ahora boton dentro de Bodega MP que abre modal con audit
// completo. Apply sigue siendo admin-only en backend.
var _RMIN_DATA = null;

function abrirRevisarMinimos(){
  document.getElementById('modal-revisar-minimos').style.display='flex';
  if(!_RMIN_DATA){ cargarRevisarMinimos(); }
}
function cerrarRevisarMinimos(){
  document.getElementById('modal-revisar-minimos').style.display='none';
}

async function cargarRevisarMinimos(){
  var btn = document.getElementById('btn-rmin-load');
  var out = document.getElementById('rmin-result');
  btn.disabled = true; btn.innerHTML='Calculando...';
  out.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:24px;">Proyectando consumo del calendario × fórmulas vs mínimos actuales...</div>';
  document.getElementById('rmin-stats').style.display='none';
  document.getElementById('rmin-aplicar-box').style.display='none';
  try{
    var proy = document.getElementById('rmin-proy').value || '90';
    var cob = (document.getElementById('rmin-cob')||{}).value || '';
    var qsCob = cob ? ('&dias_cobertura_minimo='+encodeURIComponent(cob)) : '';
    var r = await fetch('/api/planta/auditar-minimos?proyeccion_dias='+encodeURIComponent(proy)+qsCob);
    var d = await r.json();
    btn.disabled = false; btn.innerHTML='&#x1F50D; Calcular';
    if(!r.ok){
      out.innerHTML = '<div style="color:#dc2626;padding:18px;">Error: '+_escHTML(d.error||r.status)+'</div>';
      return;
    }
    _RMIN_DATA = d;
    // Stats
    document.getElementById('rmin-stats').style.display='grid';
    document.getElementById('rmin-total').textContent = d.stats.total;
    document.getElementById('rmin-ok').textContent = d.stats.ok;
    document.getElementById('rmin-sub').textContent = d.stats.sub_protegido;
    document.getElementById('rmin-sobre').textContent = d.stats.sobre_protegido;
    document.getElementById('rmin-vacio').textContent = d.stats.sin_minimo;
    document.getElementById('rmin-uso').textContent = d.stats.sin_uso;
    // Aplicar box solo si hay algo que aplicar
    var totalAplic = d.stats.sub_protegido + d.stats.sobre_protegido + d.stats.sin_minimo;
    document.getElementById('rmin-aplicar-box').style.display = totalAplic > 0 ? 'block' : 'none';
    // Sebastián 20-may-2026: resumen del impacto si se aplicara
    var impactoBox = document.getElementById('rmin-impacto');
    if(impactoBox && totalAplic > 0){
      var deltaTotal = 0, sumActual = 0, sumNuevo = 0;
      (d.auditoria||[]).forEach(function(a){
        if(['SUB_PROTEGIDO','SOBRE_PROTEGIDO','SIN_MINIMO_CONFIGURADO'].indexOf(a.estado) === -1) return;
        sumActual += a.stock_minimo_actual_g||0;
        sumNuevo += a.minimo_recomendado_g||0;
      });
      deltaTotal = sumNuevo - sumActual;
      var modoTxt = d.modo_uniforme ? ('cobertura uniforme '+d.dias_cobertura_minimo+'d') : 'lead+buffer por proveedor';
      impactoBox.innerHTML = '<b>'+totalAplic+'</b> MPs cambiarían si aplicás · '+
        'método: <i>'+modoTxt+'</i> · suma mínimos actual <b>'+Math.round(sumActual).toLocaleString('es-CO')+
        ' g</b> → nuevo <b>'+Math.round(sumNuevo).toLocaleString('es-CO')+' g</b> · ' +
        (deltaTotal>=0?'incremento neto +':'reducción neta ')+Math.abs(Math.round(deltaTotal)).toLocaleString('es-CO')+' g';
      impactoBox.style.display = 'block';
    } else if(impactoBox){
      impactoBox.style.display = 'none';
    }
    // Render tabla con orden por prioridad
    var orden = {'SUB_PROTEGIDO':0, 'SIN_MINIMO_CONFIGURADO':1, 'SOBRE_PROTEGIDO':2, 'OK':3, 'SIN_USO_CON_MIN':4, 'SIN_USO':5};
    var items = (d.auditoria||[]).slice().sort(function(a,b){
      var oa = orden[a.estado]!==undefined?orden[a.estado]:9;
      var ob = orden[b.estado]!==undefined?orden[b.estado]:9;
      if(oa!==ob) return oa-ob;
      return (b.consumo_diario_g||0)-(a.consumo_diario_g||0);
    });
    var colors = {OK:'#22c55e',SUB_PROTEGIDO:'#dc2626',SOBRE_PROTEGIDO:'#f59e0b',SIN_MINIMO_CONFIGURADO:'#6366f1',SIN_USO:'#94a3b8',SIN_USO_CON_MIN:'#94a3b8'};
    var labels = {OK:'OK',SUB_PROTEGIDO:'SUB',SOBRE_PROTEGIDO:'SOBRE',SIN_MINIMO_CONFIGURADO:'VACIO',SIN_USO:'SIN USO',SIN_USO_CON_MIN:'SIN USO'};
    // Render metodología según modo (uniforme vs lead+buffer)
    var metoTxt;
    if(d.modo_uniforme && d.dias_cobertura_minimo){
      metoTxt = 'Modo uniforme · <code>m&iacute;nimo = consumo_diario &times; '+d.dias_cobertura_minimo+'d</code> · TODOS los MPs cubren el mismo horizonte. Piso 50g para peptides.';
    } else {
      metoTxt = 'Modo lead+buffer · <code>m&iacute;nimo = consumo_diario &times; (lead_time + buffer)</code> · China 90d, local 21d, sin proveedor 28d. Piso 50g para peptides.';
    }
    var html = '<div style="font-size:11px;color:#64748b;margin-bottom:8px;">Metodolog&iacute;a: '+metoTxt+'</div>';
    html += '<div style="overflow-x:auto;"><table style="width:100%;font-size:11px;border-collapse:collapse;">';
    html += '<thead><tr style="background:#f1f5f9;"><th style="text-align:left;padding:6px 8px;border-bottom:2px solid #e2e8f0;">Estado</th><th style="text-align:left;padding:6px 8px;border-bottom:2px solid #e2e8f0;">Material</th><th style="text-align:left;padding:6px 8px;border-bottom:2px solid #e2e8f0;">Origen</th><th style="text-align:right;padding:6px 8px;border-bottom:2px solid #e2e8f0;">Consumo/día</th><th style="text-align:right;padding:6px 8px;border-bottom:2px solid #e2e8f0;">Mín. actual</th><th style="text-align:right;padding:6px 8px;border-bottom:2px solid #e2e8f0;">Mín. recomendado</th><th style="text-align:left;padding:6px 8px;border-bottom:2px solid #e2e8f0;">Razonamiento</th></tr></thead><tbody>';
    items.forEach(function(a){
      var col = colors[a.estado] || '#94a3b8';
      var lab = labels[a.estado] || a.estado;
      html += '<tr style="border-bottom:1px solid #f1f5f9;">';
      html += '<td style="padding:6px 8px;"><span style="background:'+col+'20;color:'+col+';border:1px solid '+col+';border-radius:10px;padding:2px 7px;font-size:10px;font-weight:700;">'+_escHTML(lab)+'</span></td>';
      html += '<td style="padding:6px 8px;"><div style="font-weight:600;">'+_escHTML(a.nombre)+'</div><div style="font-size:9px;color:#94a3b8;font-family:monospace;">'+_escHTML(a.codigo_mp)+'</div></td>';
      html += '<td style="padding:6px 8px;color:#64748b;">'+_escHTML(a.origen)+'</td>';
      html += '<td style="padding:6px 8px;text-align:right;">'+(a.consumo_diario_g||0).toLocaleString(undefined,{maximumFractionDigits:2})+' g</td>';
      html += '<td style="padding:6px 8px;text-align:right;">'+(a.stock_minimo_actual_g||0).toLocaleString()+' g</td>';
      html += '<td style="padding:6px 8px;text-align:right;font-weight:700;color:'+col+';">'+(a.minimo_recomendado_g||0).toLocaleString()+' g</td>';
      html += '<td style="padding:6px 8px;color:#475569;font-size:11px;">'+_escHTML(a.razonamiento||'')+'</td>';
      html += '</tr>';
    });
    html += '</tbody></table></div>';
    out.innerHTML = html;
  }catch(e){
    btn.disabled = false; btn.innerHTML='&#x1F50D; Calcular';
    out.innerHTML = '<div style="color:#dc2626;padding:18px;">Error: '+_escHTML(e.message)+'</div>';
  }
}

// Sebastián 20-may-2026: helper para pre-llenar el token (admin de
// confianza · evita typo manual). Sigue requiriendo click "Aplicar"
// y confirm() · doble fricción.
function autollenarTokenMinimos(){
  var inp = document.getElementById('rmin-token');
  if(inp){ inp.value = 'APLICAR_MINIMOS_RECALCULADOS_2026'; inp.focus(); }
}

async function aplicarRevisarMinimos(){
  var token = (document.getElementById('rmin-token').value||'').trim();
  if(token !== 'APLICAR_MINIMOS_RECALCULADOS_2026'){
    alert('Token incorrecto. Debe ser exactamente: APLICAR_MINIMOS_RECALCULADOS_2026 · usá el botón 📝 Token para autollenarlo.');
    return;
  }
  if(!confirm('Esto va a actualizar stock_minimo en maestro_mps para los SUB/SOBRE/SIN_MINIMO. Crea backup automatico previo. ¿Continuar?')) return;
  var proy = document.getElementById('rmin-proy').value || '90';
  var cob = (document.getElementById('rmin-cob')||{}).value || '';
  var btn = document.getElementById('btn-rmin-aplicar');
  btn.disabled = true; btn.innerHTML='Aplicando...';
  try{
    var bodyApl = {token: token, proyeccion_dias: parseInt(proy)};
    if(cob) bodyApl.dias_cobertura_minimo = parseInt(cob);
    var r = await fetch('/api/admin/aplicar-minimos', {
      method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':window._csrfTok||''},
      body: JSON.stringify(bodyApl)
    });
    var d = await r.json();
    btn.disabled = false; btn.innerHTML='&#x1F4A5; Aplicar recálculo';
    if(!r.ok){
      if(r.status===403){
        alert('Solo admins pueden aplicar el recálculo. Contacta a Sebastián o Alejandro.');
      } else {
        alert('Error: '+(d.error||r.status));
      }
      return;
    }
    alert('✓ '+(d.mensaje||(d.count_cambios+' mínimos actualizados.')));
    document.getElementById('rmin-token').value='';
    // Recargar audit
    cargarRevisarMinimos();
    // Refrescar stock para que la columna stock_min_g muestre los nuevos valores
    if(typeof loadStock === 'function') loadStock();
  }catch(e){
    btn.disabled = false; btn.innerHTML='&#x1F4A5; Aplicar recálculo';
    alert('Error de red: '+e.message);
  }
}

// Sprint Inventario MP · 20-may-2026 · Unificar MPs duplicadas (purisil, etc).
// Detecta MPs con nombre/INCI normalizados iguales pero codigo_mp distintos.
function abrirUnificarMPs(){
  document.getElementById('modal-unif-mp').style.display='flex';
  // Reset contenido para que sea fresh cada vez
  document.getElementById('umpd-content').innerHTML =
    '<button onclick="cargarDuplicadosMP()" style="background:#be185d;color:#fff;padding:10px 22px;font-size:14px;font-weight:700">&#x1F50D; Detectar duplicados</button>';
}
function cerrarUnificarMPs(){document.getElementById('modal-unif-mp').style.display='none';}
async function cargarDuplicadosMP(){
  var box=document.getElementById('umpd-content');
  box.innerHTML='<div style="color:#94a3b8;padding:14px">Detectando grupos... (puede tardar 5-10s con 400 MPs)</div>';
  try{
    var r=await fetch('/api/maestro-mps/duplicados-deteccion');
    if(r.status===403){ box.innerHTML='<div style="color:#dc2626;padding:14px">Solo admins · contactá a Sebastián o Alejandro.</div>'; return; }
    var d=await r.json();
    if(!r.ok){ box.innerHTML='<div style="color:#dc2626;padding:14px">Error: '+_escHTML(d.error||r.status)+'</div>'; return; }
    var grupos=d.grupos||[];
    if(!grupos.length){
      box.innerHTML='<div style="color:#16a34a;padding:24px;text-align:center;font-size:14px;font-weight:600">&#x2705; Sin duplicados detectados · catálogo está normalizado.</div>';
      return;
    }
    var html='<div style="font-size:12px;color:#64748b;margin-bottom:10px"><b>'+grupos.length+'</b> grupos · <b>'+(d.total_mps_afectadas||0)+'</b> MPs duplicadas. Elegí el código canónico (el que va a quedar) en cada grupo. Los demás se desactivan + sus referencias se redirigen al canónico.</div>';
    html += '<div style="max-height:55vh;overflow-y:auto;border:1px solid #e2e8f0;border-radius:6px">';
    grupos.forEach(function(g, gIdx){
      var gid='gump-'+gIdx;
      html += '<div style="border-bottom:1px solid #e2e8f0;padding:10px 14px;background:#fafafa">';
      html += '<div style="font-size:11px;color:#7c2d12;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px"><b>Grupo '+(gIdx+1)+'</b> · match por <code>'+_escHTML(g.tipo_match)+'</code> · "'+_escHTML(g.nombre_normalizado)+'"</div>';
      html += '<table style="width:100%;font-size:12px;border-collapse:collapse"><thead><tr style="background:#fff;color:#475569"><th style="padding:4px 6px;text-align:center">Canónico</th><th style="padding:4px 6px;text-align:left">Código</th><th style="padding:4px 6px;text-align:left">Nombre</th><th style="padding:4px 6px;text-align:left">INCI</th><th style="padding:4px 6px;text-align:left">Proveedor</th><th style="padding:4px 6px;text-align:right">Stock g</th><th style="padding:4px 6px;text-align:right">Movs</th><th style="padding:4px 6px;text-align:right">Lotes</th><th style="padding:4px 6px;text-align:right">Fórm</th><th style="padding:4px 6px;text-align:right">SOLs</th><th style="padding:4px 6px;text-align:center">Activo</th></tr></thead><tbody>';
      g.variantes.forEach(function(v, idx){
        // default canonico = primero (que es el más movido)
        html += '<tr style="border-top:1px solid #f1f5f9">';
        html += '<td style="text-align:center;padding:3px"><input type="radio" name="'+gid+'-canon" value="'+_escHTML(v.codigo_mp)+'"'+(idx===0?' checked':'')+'></td>';
        html += '<td style="font-family:monospace;padding:3px 6px">'+_escHTML(v.codigo_mp)+'</td>';
        html += '<td style="padding:3px 6px;font-weight:600">'+_escHTML(v.nombre_comercial)+'</td>';
        html += '<td style="padding:3px 6px;color:#475569">'+_escHTML(v.nombre_inci)+'</td>';
        html += '<td style="padding:3px 6px;color:#64748b">'+_escHTML(v.proveedor)+'</td>';
        html += '<td style="text-align:right;padding:3px 6px;font-family:monospace">'+v.stock_actual_g.toLocaleString('es-CO')+'</td>';
        html += '<td style="text-align:right;padding:3px 6px">'+v.n_movimientos+'</td>';
        html += '<td style="text-align:right;padding:3px 6px">'+v.n_lotes+'</td>';
        html += '<td style="text-align:right;padding:3px 6px">'+v.n_formulas+'</td>';
        html += '<td style="text-align:right;padding:3px 6px">'+v.n_sols+'</td>';
        html += '<td style="text-align:center;padding:3px">'+(v.activo?'&#x2705;':'<span style="color:#dc2626">&#x274C;</span>')+'</td>';
        html += '</tr>';
      });
      html += '</tbody></table>';
      html += '<div style="display:flex;gap:6px;margin-top:6px;justify-content:flex-end">';
      html += '<button onclick="dryRunUnificarMP('+gIdx+')" style="background:#7c3aed;color:#fff;padding:5px 12px;font-size:12px">Dry-run (preview)</button>';
      html += '<button onclick="aplicarUnificarMP('+gIdx+')" style="background:#be185d;color:#fff;padding:5px 12px;font-size:12px">&#x1F4A5; Unificar grupo</button>';
      html += '<span id="ump-msg-'+gIdx+'" style="font-size:11px;align-self:center;color:#475569"></span>';
      html += '</div></div>';
    });
    html += '</div>';
    box.innerHTML = html;
    window._UMP_GRUPOS = grupos;
  }catch(e){
    box.innerHTML='<div style="color:#dc2626;padding:14px">Error red: '+_escHTML(e.message)+'</div>';
  }
}
function _ump_get_canon_y_unir(gIdx){
  var g = (window._UMP_GRUPOS||[])[gIdx];
  if(!g) return null;
  var inputs = document.getElementsByName('gump-'+gIdx+'-canon');
  var canon = '';
  for(var i=0;i<inputs.length;i++){ if(inputs[i].checked){ canon = inputs[i].value; break; } }
  if(!canon){ alert('Elegí un canónico para el grupo'); return null; }
  var aUnir = g.variantes.map(function(v){return v.codigo_mp;}).filter(function(c){return c!==canon;});
  return {canon: canon, a_unir: aUnir};
}
async function dryRunUnificarMP(gIdx){
  var sel = _ump_get_canon_y_unir(gIdx); if(!sel) return;
  var msg = document.getElementById('ump-msg-'+gIdx);
  msg.textContent = 'Calculando preview...';
  try{
    var r = await fetch('/api/maestro-mps/unificar', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({canonico: sel.canon, codigos_a_unir: sel.a_unir, dry_run: true}),
    });
    var d = await r.json();
    if(!r.ok){ msg.innerHTML = '<span style="color:#dc2626">Error: '+_escHTML(d.error||r.status)+'</span>'; return; }
    var plan = d.plan_updates_por_tabla || {};
    var lineas = Object.keys(plan).map(function(t){return t+': '+plan[t];}).join(' · ');
    msg.innerHTML = '<span style="color:#7c3aed;font-weight:700">'+(d.total_filas_a_actualizar||0)+' filas (' + lineas + ')</span>';
  }catch(e){ msg.innerHTML = '<span style="color:#dc2626">Error red: '+_escHTML(e.message)+'</span>'; }
}
async function aplicarUnificarMP(gIdx){
  var sel = _ump_get_canon_y_unir(gIdx); if(!sel) return;
  var token = prompt('Esto reescribe TODAS las referencias al canónico ' + sel.canon + ' y desactiva ' + sel.a_unir.length + ' códigos. ESCRIBÍ EXACTO: UNIFICAR_MP_2026');
  if(token !== 'UNIFICAR_MP_2026'){ alert('Token incorrecto, cancelado.'); return; }
  var msg = document.getElementById('ump-msg-'+gIdx);
  msg.textContent = 'Aplicando...';
  try{
    var r = await fetch('/api/maestro-mps/unificar', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({canonico: sel.canon, codigos_a_unir: sel.a_unir, dry_run: false, token: token}),
    });
    var d = await r.json();
    if(!r.ok){ msg.innerHTML = '<span style="color:#dc2626">Error: '+_escHTML(d.error||r.status)+'</span>'; return; }
    msg.innerHTML = '<span style="color:#16a34a;font-weight:700">&#x2705; '+(d.mensaje||'Unificado')+'</span>';
    // Refrescar inventario después de unificar
    if(typeof loadStock==='function') setTimeout(loadStock, 800);
  }catch(e){ msg.innerHTML = '<span style="color:#dc2626">Error red: '+_escHTML(e.message)+'</span>'; }
}

async function abrirLimpiezaProveedores(){
  document.getElementById('modal-limpieza-prov').style.display='flex';
  await _renderLimpiezaProveedores();
}
function cerrarLimpiezaProveedores(){
  document.getElementById('modal-limpieza-prov').style.display='none';
  // Refrescar datalist global por si hubo cambios
  _epProveedoresCargados=false;
  _cargarProveedoresUnicos();
}
async function _renderLimpiezaProveedores(){
  var cont=document.getElementById('lp-content');
  cont.innerHTML='<div style="text-align:center;color:#888;padding:24px;">Detectando duplicados...</div>';
  try{
    var r=await fetch('/api/proveedores-duplicados');
    var d=await r.json();
    var grupos=d.grupos||[];
    if(!grupos.length){
      cont.innerHTML='<div style="text-align:center;color:#1a8a1a;padding:24px;font-weight:700;">&#10003; Sin duplicados detectados — todos los proveedores tienen formato unico.</div>';
      return;
    }
    var html='<div style="margin-bottom:8px;color:#7c3aed;font-weight:700;">'+grupos.length+' grupo(s) con variantes</div>';
    grupos.forEach(function(g,gi){
      html+='<div id="lp-grupo-'+gi+'" style="border:1px solid #ddd;border-radius:8px;padding:12px;margin-bottom:10px;background:#fafafa;">';
      html+='<div style="font-size:0.78em;color:#888;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;">'+g.count_variantes+' variantes &middot; clave: <code>'+_escHTML(g.clave_normalizada)+'</code></div>';
      html+='<div style="margin-bottom:8px;">';
      g.variantes.forEach(function(v,vi){
        var uso=g.usos[v]||0;
        var checked=(v===g.canonico_sugerido)?'checked':'';
        html+='<label style="display:flex;align-items:center;gap:8px;padding:4px 0;cursor:pointer;">';
        html+='<input type="radio" name="lp-canon-'+gi+'" value="'+_escHTML(v)+'" '+checked+'>';
        html+='<span style="flex:1;"><b>'+_escHTML(v)+'</b> <span style="color:#888;font-size:0.85em;">('+uso+' mov)</span></span>';
        html+='</label>';
      });
      html+='</div>';
      html+='<div id="lp-msg-'+gi+'" style="font-size:0.85em;margin-bottom:6px;"></div>';
      html+='<button onclick="unificarGrupo('+gi+')" style="background:#7c3aed;color:white;padding:6px 12px;font-size:0.85em;border-radius:6px;">&#128279; Unificar este grupo</button>';
      html+='</div>';
    });
    cont.innerHTML=html;
    // Guardamos los grupos en una variable global para acceder desde unificarGrupo
    window._lpGrupos=grupos;
  }catch(e){
    cont.innerHTML='<div style="color:#c00;padding:24px;">Error: '+e.message+'</div>';
  }
}
async function unificarGrupo(gi){
  var grupos=window._lpGrupos||[]; var g=grupos[gi]; if(!g)return;
  var radios=document.getElementsByName('lp-canon-'+gi);
  var canonico='';
  for(var i=0;i<radios.length;i++){if(radios[i].checked){canonico=radios[i].value;break;}}
  if(!canonico){alert('Selecciona el proveedor canonico');return;}
  if(!confirm('Unificar todas las variantes a "'+canonico+'"?\n\nEsto actualiza movimientos + catalogo de MPs. Reversible solo via audit_log.')){return;}
  var msg=document.getElementById('lp-msg-'+gi);
  msg.innerHTML='<span style="color:#666;">Unificando...</span>';
  try{
    var r=await fetch('/api/proveedores-unificar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({canonico:canonico,variantes:g.variantes})});
    var d=await r.json();
    if(r.ok){
      msg.innerHTML='<span style="color:#1a8a1a;font-weight:700;">✓ '+(d.message||'Unificado')+'</span>';
      // Re-render despues de un momento
      setTimeout(function(){_renderLimpiezaProveedores();loadStock();},1500);
    }else{
      msg.innerHTML='<span style="color:#c00;">Error: '+_escHTML(d.error||r.status)+'</span>';
    }
  }catch(e){
    msg.innerHTML='<span style="color:#c00;">Error de red: '+_escHTML(e.message)+'</span>';
  }
}

// ─── Eliminar Lote (a nivel lote, motivo obligatorio) ──────────────────────
var _delLote=null;
function abrirEliminarLote(idx){
  var i=_lotes[idx]; if(!i){alert('Lote no encontrado'); return;}
  _delLote=i;
  document.getElementById('del-mp-nombre').textContent=(i.material_nombre||'')+' · '+(i.material_id||'');
  var partes=[];
  if(i.lote)partes.push('Lote: '+i.lote); else partes.push('Lote: (sin lote)');
  partes.push('Cantidad actual: '+(i.cantidad_g||0).toLocaleString()+' g');
  if(i.fecha_vencimiento)partes.push('Vence: '+i.fecha_vencimiento);
  if(i.proveedor)partes.push('Prov.: '+i.proveedor);
  document.getElementById('del-mp-info').textContent=partes.join(' · ');
  document.getElementById('del-motivo').value='';
  document.getElementById('del-msg').innerHTML='';
  document.getElementById('modal-eliminar-lote').style.display='flex';
}
function cerrarEliminarLote(){document.getElementById('modal-eliminar-lote').style.display='none';_delLote=null;}
async function confirmarEliminarLote(){
  if(!_delLote)return;
  var msg=document.getElementById('del-msg');
  var motivo=document.getElementById('del-motivo').value.trim();
  if(motivo.length<10){msg.innerHTML='<span style="color:#c00;">Motivo min. 10 caracteres.</span>';return;}
  // Sprint Bodega MP PRO · 20-may-2026 fix #3: quitar confirm() nativo
  // duplicado. El modal ya pidió motivo de 10+ chars + el user apretó
  // "Confirmar" · doble confirmación es fricción innecesaria.
  msg.innerHTML='<span style="color:#666;">Eliminando...</span>';
  var loteSeg=_delLote.lote||'_SIN_LOTE_';
  var url='/api/lotes/'+encodeURIComponent(_delLote.material_id)+'/'+encodeURIComponent(loteSeg);
  try{
    var r=await fetch(url,{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({motivo:motivo})});
    var d=await r.json();
    if(r.ok){
      msg.innerHTML='<span style="color:#1a8a1a;font-weight:700;">✓ '+(d.message||'Lote eliminado')+'</span>';
      setTimeout(function(){cerrarEliminarLote();loadStock();},1500);
    }else{
      msg.innerHTML='<span style="color:#c00;">Error: '+(d.error||r.status)+(d.detail?' — '+d.detail:'')+'</span>';
    }
  }catch(e){
    msg.innerHTML='<span style="color:#c00;">Error de red: '+e.message+'</span>';
  }
}
async function abrirAjuste(mid,mn,lt,sa,est,pos,fv){
  if(!OPER_ACTUAL){alert('Primero selecciona tu nombre al inicio');return;}
  _ajDat={mid:mid,mn:mn,lt:lt,sa:sa,est:est||'',pos:pos||'',fv:fv||''};
  document.getElementById('ajuste-info').textContent=mid+' — '+mn+(lt&&lt!='S/L'?' (Lote: '+lt+')':'');
  document.getElementById('ajuste-sistema').value=sa;
  document.getElementById('ajuste-fisico').value='';
  document.getElementById('ajuste-obs').value='';
  document.getElementById('ajuste-msg').innerHTML='';
  document.getElementById('ajuste-smin-msg').innerHTML='';
  document.getElementById('ajuste-consumo-msg').innerHTML='';
  document.getElementById('ajuste-arch-msg').innerHTML='';
  document.getElementById('ajuste-consumo').value='';
  // Sebastian 8-may-2026: hidratar bloque ubicacion del lote
  var ubicActual=document.getElementById('ajuste-ubic-actual');
  if(ubicActual){
    var resumen=((est||'').trim()||'(sin estanteria)')+' / '+((pos||'').trim()||'(sin posicion)');
    ubicActual.textContent=resumen;
  }
  var inpEst=document.getElementById('ajuste-estanteria');if(inpEst)inpEst.value=est||'';
  var inpPos=document.getElementById('ajuste-posicion');if(inpPos)inpPos.value=pos||'';
  var inpMot=document.getElementById('ajuste-ubic-motivo');if(inpMot)inpMot.value='';
  var ubicMsg=document.getElementById('ajuste-ubic-msg');if(ubicMsg)ubicMsg.innerHTML='';
  // Sebastián 9-may-2026: hidratar bloque fecha de vencimiento
  var fvNorm = (fv||'').slice(0,10);
  var fvActual=document.getElementById('ajuste-fv-actual');
  if(fvActual) fvActual.textContent = fvNorm || '(sin fecha)';
  var fvInp=document.getElementById('ajuste-fv'); if(fvInp) fvInp.value=fvNorm;
  var fvMot=document.getElementById('ajuste-fv-motivo'); if(fvMot) fvMot.value='';
  var fvMsg=document.getElementById('ajuste-fv-msg'); if(fvMsg) fvMsg.innerHTML='';
  // Sebastián 9-may-2026: hidratar bloque número de lote
  var ltActual=document.getElementById('ajuste-lt-actual');
  if(ltActual) ltActual.textContent = (lt && lt!=='S/L') ? lt : '(sin lote)';
  var ltInp=document.getElementById('ajuste-lt-nuevo'); if(ltInp) ltInp.value=(lt && lt!=='S/L')?lt:'';
  var ltMot=document.getElementById('ajuste-lt-motivo'); if(ltMot) ltMot.value='';
  var ltMsg=document.getElementById('ajuste-lt-msg'); if(ltMsg) ltMsg.innerHTML='';
  try{var r=await fetch('/api/maestro-mps/'+encodeURIComponent(mid));if(r.ok){var d=await r.json();document.getElementById('ajuste-smin').value=d.stock_minimo||0;}}catch(e){document.getElementById('ajuste-smin').value=0;}
  document.getElementById('modal-ajuste').style.display='flex';
}
async function actualizarStockMinimo(){
  var mid=_ajDat&&_ajDat.mid;if(!mid)return;
  var val=parseFloat(document.getElementById('ajuste-smin').value);
  if(isNaN(val)||val<0){document.getElementById('ajuste-smin-msg').innerHTML='<span style="color:red;">Valor inválido</span>';return;}
  // Sebastián 9-may-2026: persistir + reflejar en Bodega MP. Antes solo
  // refrescaba alertas-reabas, no la tabla Bodega · el user veía el valor
  // viejo en columna "Stock Min" aunque la BD ya tenía el nuevo (bug
  // visual interpretado como "no se guardó").
  document.getElementById('ajuste-smin-msg').innerHTML='<span style="color:#666;">⏳ Guardando...</span>';
  try{
    var r=await fetch('/api/maestro-mps/'+encodeURIComponent(mid)+'/stock-minimo',
      {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({stock_minimo:val})});
    var d={};try{d=await r.json();}catch(je){}
    if(r.ok){
      document.getElementById('ajuste-smin-msg').innerHTML=
        '<span style="color:#28a745;font-weight:700;">✓ Stock mínimo actualizado a '+val.toLocaleString('es-CO')+' g · persistido en BD</span>';
      // Refrescar tabla Bodega MP (columna "Stock Min" usa _lotes·stock_min_g
      // que viene de /api/lotes con MAX(stock_minimo)) Y alertas reabastec.
      try{ if(typeof loadStock==='function') setTimeout(loadStock, 400); }catch(e){}
      try{ if(typeof loadAlertasReabas==='function') setTimeout(loadAlertasReabas, 500); }catch(e){}
    } else {
      document.getElementById('ajuste-smin-msg').innerHTML=
        '<span style="color:red;">Error: '+(d.error||r.status)+'</span>';
    }
  }catch(e){
    document.getElementById('ajuste-smin-msg').innerHTML='<span style="color:red;">Error de red: '+e.message+'</span>';
  }
}
async function registrarConsumo(){
  var mid=_ajDat&&_ajDat.mid;if(!mid)return;
  var cant=parseFloat(document.getElementById('ajuste-consumo').value);
  if(isNaN(cant)||cant<=0){document.getElementById('ajuste-consumo-msg').innerHTML='<span style="color:red;">Cantidad positiva requerida</span>';return;}
  var r=await fetch('/api/consumo-manual',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({codigo_mp:mid,cantidad:cant,lote:_ajDat.lt||'',operador:OPER_ACTUAL})});
  var d=await r.json();
  document.getElementById('ajuste-consumo-msg').innerHTML=r.ok?'<span style="color:#28a745;">✓ '+d.message+'</span>':'<span style="color:red;">'+(d.error||'Error')+'</span>';
  if(r.ok){var ns=Math.max(0,(_ajDat.sa||0)-cant);document.getElementById('ajuste-sistema').value=ns;_ajDat.sa=ns;document.getElementById('ajuste-consumo').value='';setTimeout(loadStock,500);}
}
async function archivarMP(){
  var mid=_ajDat&&_ajDat.mid;if(!mid)return;
  if(!confirm('Archivar '+mid+' — '+(_ajDat.mn||'')+'. Quedará oculto del catálogo activo. ¿Confirmar?'))return;
  try{
    var r=await fetch('/api/maestro-mps/'+encodeURIComponent(mid)+'/archivar',{method:'PUT',headers:{'Content-Type':'application/json','X-CSRF-Token':window._csrfTok||''}});
    var d={}; try{d=await r.json();}catch(je){}
    document.getElementById('ajuste-arch-msg').innerHTML=r.ok?'<span style="color:#28a745;">✓ Archivado</span>':'<span style="color:red;">'+(d.error||'Error al archivar')+'</span>';
    setTimeout(function(){cerrarAjuste();loadStock();},1500);
  }catch(e){
    document.getElementById('ajuste-arch-msg').innerHTML='<span style="color:red;">Error: '+e.message+'</span>';
    setTimeout(function(){cerrarAjuste();},3000);
  }
}
// Sebastian 8-may-2026: corregir ubicacion fisica del lote.
// PUT /api/lotes/<mid>/<lote>/ubicacion · UPDATE estanteria/posicion en
// TODOS los movimientos del lote (para que /api/lotes refleje MAX nuevo).
async function actualizarUbicacionLote(){
  var mid=_ajDat&&_ajDat.mid;
  var lt=_ajDat&&_ajDat.lt;
  if(!mid){return;}
  var msgEl=document.getElementById('ajuste-ubic-msg');
  var nuevaEst=(document.getElementById('ajuste-estanteria').value||'').trim();
  var nuevaPos=(document.getElementById('ajuste-posicion').value||'').trim();
  var motivo=(document.getElementById('ajuste-ubic-motivo').value||'').trim();
  if(!nuevaEst && !nuevaPos){
    msgEl.innerHTML='<span style="color:red;">Indica al menos estanteria o posicion</span>';
    return;
  }
  var actEst=(_ajDat.est||'').trim();
  var actPos=(_ajDat.pos||'').trim();
  if(nuevaEst===actEst && nuevaPos===actPos){
    msgEl.innerHTML='<span style="color:#666;">Sin cambios respecto al actual</span>';
    return;
  }
  // Lote vacio → placeholder _SIN_LOTE_ (mismo patron que /proveedor)
  var loteUrl=lt && lt!=='S/L' ? encodeURIComponent(lt) : '_SIN_LOTE_';
  msgEl.innerHTML='<span style="color:#666;">Guardando...</span>';
  try{
    var r=await fetch('/api/lotes/'+encodeURIComponent(mid)+'/'+loteUrl+'/ubicacion',
      {method:'PUT',headers:{'Content-Type':'application/json'},
       body:JSON.stringify({estanteria:nuevaEst,posicion:nuevaPos,motivo:motivo})});
    var d={};try{d=await r.json();}catch(je){}
    if(r.ok){
      msgEl.innerHTML='<span style="color:#28a745;">&#10003; '+(d.message||'Actualizado')+
        ' ('+(d.movimientos_actualizados||0)+' movimiento(s))</span>';
      // Hidratar _ajDat y display con valores nuevos
      _ajDat.est=d.estanteria_nueva||nuevaEst;
      _ajDat.pos=d.posicion_nueva||nuevaPos;
      var ubicActual=document.getElementById('ajuste-ubic-actual');
      if(ubicActual){
        ubicActual.textContent=(_ajDat.est||'(sin estanteria)')+' / '+(_ajDat.pos||'(sin posicion)');
      }
      // Refrescar la tabla de Bodega para que muestre la posicion nueva
      setTimeout(loadStock,500);
    }else{
      msgEl.innerHTML='<span style="color:red;">'+(d.error||'Error '+r.status)+
        (d.detail?' &mdash; '+d.detail:'')+'</span>';
    }
  }catch(e){msgEl.innerHTML='<span style="color:red;">Error: '+e.message+'</span>';}
}
// Sebastián 9-may-2026: actualizar fecha de vencimiento del lote (algunos
// lotes ingresaron sin fecha y se necesita corregir).
async function actualizarFechaVencimiento(){
  var mid=_ajDat&&_ajDat.mid;
  var lt=_ajDat&&_ajDat.lt;
  if(!mid){return;}
  var msgEl=document.getElementById('ajuste-fv-msg');
  var nuevaFv=((document.getElementById('ajuste-fv')||{}).value||'').trim();
  var motivo=((document.getElementById('ajuste-fv-motivo')||{}).value||'').trim();
  var actFv=((_ajDat.fv||'')+'').slice(0,10);
  if(nuevaFv===actFv){
    msgEl.innerHTML='<span style="color:#666;">Sin cambios respecto a la fecha actual.</span>';
    return;
  }
  if(!nuevaFv && !confirm('Vas a DEJAR EL LOTE SIN FECHA DE VENCIMIENTO. ¿Continuar?')){return;}
  var loteUrl=lt && lt!=='S/L' ? encodeURIComponent(lt) : '_SIN_LOTE_';
  msgEl.innerHTML='<span style="color:#666;">Guardando...</span>';
  try{
    var r=await fetch('/api/lotes/'+encodeURIComponent(mid)+'/'+loteUrl+'/fecha-vencimiento',
      {method:'PUT',headers:{'Content-Type':'application/json'},
       body:JSON.stringify({fecha_vencimiento:nuevaFv,motivo:motivo})});
    var d={};try{d=await r.json();}catch(je){}
    if(r.ok){
      msgEl.innerHTML='<span style="color:#28a745;font-weight:700;">&#10003; '+
        (d.message||'Fecha actualizada')+' ('+(d.movimientos_actualizados||0)+' mov)</span>';
      _ajDat.fv=d.fecha_nueva||nuevaFv;
      var fvActual=document.getElementById('ajuste-fv-actual');
      if(fvActual) fvActual.textContent=(_ajDat.fv||'(sin fecha)');
      setTimeout(loadStock,500);
    }else{
      msgEl.innerHTML='<span style="color:#c00;">Error: '+(d.error||r.status)+
        (d.detail?' &mdash; '+d.detail:'')+'</span>';
    }
  }catch(e){msgEl.innerHTML='<span style="color:#c00;">Error de red: '+e.message+'</span>';}
}
// Sebastián 9-may-2026: renombrar el código de lote (caso típico:
// '20250703' debe ser 'YT20250703'). UPDATE de TODOS los movimientos
// del lote en una transacción + audit log. Soporta fusión opcional.
async function actualizarCodigoLote(){
  var mid=_ajDat&&_ajDat.mid;
  var ltActual=_ajDat&&_ajDat.lt;
  if(!mid){return;}
  var msgEl=document.getElementById('ajuste-lt-msg');
  var ltNuevo=((document.getElementById('ajuste-lt-nuevo')||{}).value||'').trim();
  var motivo=((document.getElementById('ajuste-lt-motivo')||{}).value||'').trim();
  if(!ltNuevo){
    msgEl.innerHTML='<span style="color:#c00;">El nuevo número de lote no puede estar vacío.</span>';
    return;
  }
  var ltActualNorm=(ltActual==='S/L'?'':(ltActual||''));
  if(ltNuevo===ltActualNorm){
    msgEl.innerHTML='<span style="color:#666;">Sin cambios respecto al lote actual.</span>';
    return;
  }
  if(!confirm('Vas a renombrar el lote "'+(ltActualNorm||'(sin lote)')+'" a "'+ltNuevo+'"\n\n'+
              'Esto actualiza TODOS los movimientos del lote en BD. Si el lote nuevo ya existe se te pedirá confirmar fusión. ¿Continuar?')){
    return;
  }
  var loteUrl=ltActual && ltActual!=='S/L' ? encodeURIComponent(ltActual) : '_SIN_LOTE_';
  msgEl.innerHTML='<span style="color:#666;">⏳ Renombrando...</span>';
  try{
    var body={lote_nuevo:ltNuevo,motivo:motivo};
    var r=await fetch('/api/lotes/'+encodeURIComponent(mid)+'/'+loteUrl+'/codigo-lote',
      {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d={};try{d=await r.json();}catch(je){}
    // 409 = colisión · pedir confirmación de fusión
    if(r.status===409){
      var nExist=d.lote_existente_movs||0;
      var nRen=d.lote_a_renombrar_movs||0;
      var ok2=confirm('⚠️ COLISIÓN: ya existe un lote "'+ltNuevo+'" para este material con '+nExist+' movimiento(s).\n\n'+
                      'Si confirmás, se FUSIONAN los dos lotes en uno solo:\n'+
                      '  · '+nRen+' movs del lote viejo "'+(ltActualNorm||'(sin lote)')+'"\n'+
                      '  · '+nExist+' movs del lote existente "'+ltNuevo+'"\n'+
                      'Total: '+(nExist+nRen)+' movs bajo "'+ltNuevo+'" (stock se suma).\n\n'+
                      '¿Fusionar?');
      if(!ok2){msgEl.innerHTML='<span style="color:#666;">Cancelado · sin cambios.</span>';return;}
      body.merge=true;
      msgEl.innerHTML='<span style="color:#666;">⏳ Fusionando...</span>';
      r=await fetch('/api/lotes/'+encodeURIComponent(mid)+'/'+loteUrl+'/codigo-lote',
        {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      d={};try{d=await r.json();}catch(je){}
    }
    if(r.ok){
      msgEl.innerHTML='<span style="color:#28a745;font-weight:700;">✓ '+(d.message||'Lote renombrado')+'</span>';
      _ajDat.lt=ltNuevo;
      var ltActEl=document.getElementById('ajuste-lt-actual');
      if(ltActEl) ltActEl.textContent=ltNuevo;
      // Refrescar Bodega MP para que la columna "Lote" muestre el nuevo
      try{ if(typeof loadStock==='function') setTimeout(loadStock, 500); }catch(e){}
    }else{
      msgEl.innerHTML='<span style="color:#c00;">Error: '+(d.error||r.status)+
        (d.detail?' &mdash; '+d.detail:'')+'</span>';
    }
  }catch(e){msgEl.innerHTML='<span style="color:#c00;">Error de red: '+e.message+'</span>';}
}
function cerrarAjuste(){document.getElementById('modal-ajuste').style.display='none';['ajuste-msg','ajuste-smin-msg','ajuste-consumo-msg','ajuste-arch-msg','ajuste-ubic-msg','ajuste-fv-msg','ajuste-lt-msg'].forEach(function(id){var el=document.getElementById(id);if(el)el.innerHTML='';});}
var _provSaveTimers={};
function guardarProveedorMP(inp){
  var cod=inp.dataset.cod;
  var val=inp.value.trim();
  if(!cod) return;
  inp.style.borderColor='#ffc107';
  inp.title='Guardando...';
  clearTimeout(_provSaveTimers[cod]);
  _provSaveTimers[cod]=setTimeout(function(){
    fetch('/api/maestro-mps/'+encodeURIComponent(cod)+'/proveedor',{
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({proveedor:val})
    }).then(function(r){ return r.json(); }).then(function(d){
      if(d.ok){
        inp.style.borderColor='#28a745';
        inp.title=val ? 'Guardado en maestro y directorio de proveedores' : 'Proveedor borrado';
        setTimeout(function(){ inp.style.borderColor=''; inp.title='Edita y presiona Enter o Tab para guardar'; },2500);
        // Actualizar _alertasData para que solicitarTodasMPs use datos frescos
        var ad=window._alertasData||[];
        var found=ad.find(function(a){return a.codigo_mp===cod;});
        if(found) found.proveedor=val;
        // Actualizar datalist de compras si esta disponible
        if(window._proveedoresList && val && !window._proveedoresList.includes(val)){
          window._proveedoresList.push(val);
        }
        if(val) _toast('Proveedor guardado: '+val,1);
      } else {
        inp.style.borderColor='#dc3545';
        inp.title='Error: '+(d.error||'desconocido');
        _toast('Error guardando proveedor: '+(d.error||''), 0);
      }
    }).catch(function(e){
      inp.style.borderColor='#dc3545';
      inp.title='Error de conexion';
      _toast('Error de conexion al guardar proveedor', 0);
    });
  },700);
}

async function solicitarTodasMPs(){
  var alertas=(window._alertasData||[]).filter(function(a){return a.tipo!=='MEE';});
  if(!alertas.length){alert('No hay MPs bajo minimo para solicitar.');return;}
  var sinProv=alertas.filter(function(a){return !a.proveedor;});
  if(sinProv.length){
    var names=sinProv.slice(0,5).map(function(a){return a.nombre;}).join(', ');
    if(!confirm('Hay '+sinProv.length+' MP(s) sin proveedor asignado: '+names+'. Se incluiran de todas formas. Continuar?')) return;
  }
  var sol=OPER_ACTUAL||'Planta';
  var items=alertas.map(function(a){
    return {codigo_mp:a.codigo_mp,nombre_mp:a.nombre,cantidad_g:a.deficit>0?a.deficit:a.stock_minimo,
            unidad:'g',justificacion:'Bajo stock minimo. Stock actual: '+a.stock_actual+'g / Minimo: '+a.stock_minimo+'g'};
  });
  var data={solicitante:sol,empresa:'Espagiria',area:'Produccion',
            categoria:'Materia Prima',tipo:'Compra',urgencia:'Alta',
            observaciones:'Solicitud automatica desde alertas de stock — '+items.length+' MPs',
            items:items};
  try{
    var r=await fetch('/api/solicitudes-compra',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    if(r.ok&&res.numero){
      alert('Solicitud '+res.numero+' enviada a Compras con '+items.length+' MPs. En Compras > Tab Planta podras asignar precios y generar OCs por proveedor.');
    } else {
      alert('Error: '+(res.error||'desconocido'));
    }
  }catch(e){alert('Error de red: '+e.message);}
}

function abrirSolIdx(ri){
  var a=(window._alertasData||[])[ri];if(!a)return;
  abrirSolicitudCompra(a.codigo_mp,a.nombre,a.deficit);
}
var _solMP={};
function abrirSolicitudCompra(cod,nom,deficit){
  _solMP={cod:cod,nom:nom,deficit:deficit};
  document.getElementById("modal-solicitud-compra").style.display="flex";
  document.getElementById("sol-mp-info").textContent=cod+" - "+nom+" | Deficit: "+deficit.toLocaleString()+"g";
  document.getElementById("sol-cantidad").value=deficit>0?deficit:"";
  document.getElementById("sol-nombre").value=OPER_ACTUAL||"";
  document.getElementById("sol-msg").innerHTML="";
}
function cerrarSolicitudCompra(){
  document.getElementById("modal-solicitud-compra").style.display="none";
}
async function enviarSolicitudCompra(){
  var nom=document.getElementById("sol-nombre").value.trim();
  var cant=parseFloat(document.getElementById("sol-cantidad").value);
  if(!nom){alert("Escribe tu nombre");return;}
  if(!cant||cant<=0){alert("Ingresa una cantidad valida");return;}
  var btn=document.querySelector("#modal-solicitud-compra button");
  if(btn){btn.disabled=true;btn.textContent="Enviando..."}
  try{
    var urgEl=document.getElementById("sol-urgencia");
    var obsEl=document.getElementById("sol-obs");
    var data={solicitante:nom,empresa:"Espagiria",
      urgencia:urgEl?urgEl.value:"Normal",
      observaciones:obsEl?obsEl.value:"",
      items:[{codigo_mp:(_solMP&&_solMP.cod)||"S/C",nombre_mp:(_solMP&&_solMP.nom)||"Sin nombre",
              cantidad_g:cant,unidad:"g",justificacion:"Solicitud desde alertas de stock"}]};
    var r=await fetch("/api/solicitudes-compra",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
    var res=null;
    try{res=await r.json();}catch(_){res=null;}
    if(r.ok&&res){
      document.getElementById("sol-msg").innerHTML='<div style="padding:12px;background:#d4edda;border:1px solid #28a745;border-radius:6px;color:#155724;font-weight:600;">&#10003; Solicitud '+res.numero+' creada. El equipo de compras fue notificado.</div>';
      if(btn){btn.disabled=true;btn.textContent="✓ Enviado";btn.style.background="#28a745";}
      setTimeout(function(){cerrarSolicitudCompra();},3500);
    } else {
      var errMsg=(res&&res.error)?res.error:(res&&res.detail)?res.detail.slice(-200):"Error "+r.status+" — recarga la pagina e intenta de nuevo";
      document.getElementById("sol-msg").innerHTML='<div style="padding:10px;background:#f8d7da;border:1px solid #dc3545;border-radius:6px;color:#721c24;font-size:0.88em;">&#10060; '+errMsg+'</div>';
      if(btn){btn.disabled=false;btn.textContent="✓ Enviar Solicitud";}
    }
  }catch(e){
    document.getElementById("sol-msg").innerHTML='<div style="padding:10px;background:#f8d7da;border:1px solid #dc3545;border-radius:6px;color:#721c24;">&#10060; Error: '+e.message+'</div>';
    if(btn){btn.disabled=false;btn.textContent="✓ Enviar Solicitud";}
  }
}
function cerrarHistorial(){document.getElementById('modal-historial').style.display='none';}
async function verHistorialLote(idx){
  // Sprint Bodega MP PRO · 20-may-2026 fix #1+#14: usa endpoint
  // server-side /api/lotes/<mid>/<lote>/movimientos · NO baja /api/movimientos
  // completo. Fix #9: colspan consistente en 5 columnas.
  var i=_lotes[idx];if(!i)return;
  document.getElementById('modal-historial').style.display='flex';
  document.getElementById('hist-lote-info').textContent=i.material_id+' - '+i.material_nombre+' Lote:'+(i.lote||'S/L')+' Stock:'+i.cantidad_g+'g';
  var tb=document.getElementById('hist-lote-body');
  tb.innerHTML='<tr><td colspan=5 style="text-align:center;padding:14px;color:#94a3b8">Cargando movimientos del lote...</td></tr>';
  try{
    var loteSeg = i.lote || '_SIN_LOTE_';
    var url='/api/lotes/'+encodeURIComponent(i.material_id)+'/'+encodeURIComponent(loteSeg)+'/movimientos';
    var r=await fetch(url);
    if(!r.ok){
      tb.innerHTML='<tr><td colspan=5 style="text-align:center;padding:14px;color:#dc2626">Error '+r.status+' · '+(r.statusText||'')+'</td></tr>';
      return;
    }
    var d=await r.json();
    var mv=d.movimientos||[];
    if(!mv.length){tb.innerHTML='<tr><td colspan=5 style="text-align:center;padding:14px;color:#94a3b8">Sin movimientos para este lote</td></tr>';return;}
    tb.innerHTML=mv.map(function(m){
      var f=m.fecha?String(m.fecha).substring(0,16).replace('T',' '):'';
      var tipoColor=m.tipo==='Entrada'?'#16a34a':'#dc2626';
      return '<tr><td style="color:'+tipoColor+';font-weight:600">'+_escHTML(m.tipo)+'</td>'+
             '<td style="text-align:right;font-family:monospace">'+_escHTML(Number(m.cantidad).toLocaleString('es-CO'))+'</td>'+
             '<td style="font-family:monospace;color:#475569">'+_escHTML(f)+'</td>'+
             '<td>'+_escHTML(m.observaciones||'')+'</td>'+
             '<td>'+_escHTML(m.operador||'')+'</td></tr>';
    }).join('');
  }catch(e){tb.innerHTML='<tr><td colspan=5 style="text-align:center;padding:14px;color:#dc2626">Error de red: '+_escHTML(e.message)+'</td></tr>';}
}

async function confirmarAjuste(){
  var fis=parseFloat(document.getElementById('ajuste-fisico').value);
  if(isNaN(fis)||fis<0){alert('Cantidad inválida');return;}
  var dif=Math.round((fis-_ajDat.sa)*100)/100;
  if(dif===0){alert('El stock físico coincide con el sistema');return;}
  var tipo=dif>0?'Entrada':'Salida';
  var obs='AJUSTE: '+(document.getElementById('ajuste-obs').value||'Conteo físico')+' | Op: '+OPER_ACTUAL;
  try{
    var r=await fetch('/api/movimientos',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({material_id:_ajDat.mid,material_nombre:_ajDat.mn,
        cantidad:Math.abs(dif),tipo:tipo,observaciones:obs,lote:_ajDat.lt,operador:OPER_ACTUAL})});
    var res=await r.json();
    var sg=dif>0?'+':'';
    document.getElementById('ajuste-msg').innerHTML='<div class="alert-success">✓ Ajuste registrado: '+sg+dif.toLocaleString()+'g ('+tipo+'). Stock actualizado · podés seguir editando o cerrar el modal.</div>';
    // Sebastián 9-may-2026: NO auto-cerrar el modal · el user puede
    // querer hacer más cambios al mismo lote (ubicación, fecha, lote,
    // proveedor) sin tener que volver a buscar la MP. Solo refrescamos
    // el stock visible y actualizamos _ajDat.sa con el nuevo total.
    _ajDat.sa = fis;  // hidratar nuevo stock_actual para próximos ajustes
    var sysInp=document.getElementById('ajuste-sistema'); if(sysInp) sysInp.value=fis;
    var fisInp=document.getElementById('ajuste-fisico'); if(fisInp) fisInp.value='';
    setTimeout(loadStock, 500);
  }catch(e){document.getElementById('ajuste-msg').innerHTML='<div class="alert-error">Error al registrar ajuste</div>';}
}

// Sebastián 10-may-2026: exports a Excel ahora generan archivos que
// Excel español/Latam abre con columnas correctas (antes bajaba todo
// "colapsado" en una sola columna).
//
// Solución: generar archivos .xls con tabla HTML simple. Excel parsea
// HTML como hoja con columnas, formato y encoding correctos. Es el
// método más universal: NO depende de configuración regional ni de
// separadores · funciona en Excel, LibreOffice y Google Sheets.
//
// _csvEscape: para casos de respaldo cuando se quiera CSV puro.
function _csvEscape(v){
  var s = (v==null) ? '' : String(v);
  if (s.indexOf(';')>=0 || s.indexOf('"')>=0 || s.indexOf('\n')>=0 || s.indexOf('\r')>=0) {
    s = '"' + s.replace(/"/g,'""') + '"';
  }
  return s;
}
function _htmlEsc(v){
  var s = (v==null) ? '' : String(v);
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
// dlExcelHTML: descarga un archivo .xls que Excel abre como tabla
// con columnas separadas. Acepta cols (array de strings) y rows
// (array de arrays). Cada fila se renderiza como <tr><td>...</td></tr>.
function dlExcelHTML(nombre, cols, rows){
  var head = '<tr>' + cols.map(function(c){
    return '<th style="background:#6d28d9;color:white;font-weight:bold;border:1px solid #888;padding:4px">'+_htmlEsc(c)+'</th>';
  }).join('') + '</tr>';
  var body = rows.map(function(r){
    return '<tr>' + r.map(function(v){
      var isNum = (typeof v === 'number') && isFinite(v);
      var align = isNum ? 'right' : 'left';
      return '<td style="border:1px solid #ccc;padding:3px 6px;text-align:'+align+'">'+_htmlEsc(v)+'</td>';
    }).join('') + '</tr>';
  }).join('');
  var html = '<!DOCTYPE html><html><head><meta charset="utf-8"></head>'+
             '<body><table style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:12px">'+
             '<thead>'+head+'</thead><tbody>'+body+'</tbody></table></body></html>';
  // BOM UTF-8 + content type que Excel reconoce
  var blob = new Blob(['﻿'+html], {type:'application/vnd.ms-excel;charset=utf-8'});
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  // Forzar extensión .xls para que Excel lo abra directo (no .csv)
  a.download = nombre.replace(/\.csv$/i, '.xls');
  if(!/\.xls$/i.test(a.download)) a.download += '.xls';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
function exportarExcelStock(){
  // .xlsx NATIVO desde el backend (openpyxl · Sebastián 27-jun) · antes usaba dlExcelHTML = tabla HTML
  // servida como Excel → abría con advertencia "el formato y la extensión no coinciden". Ahora descarga
  // el archivo .xlsx real directamente.
  window.location = '/api/lotes/export-xlsx';
}
async function exportarExcelMovimientos(){
  var r=await fetch('/api/movimientos'),d=await r.json(),M=d.movimientos||[];
  if(!M.length){alert('Sin movimientos');return;}
  var cols=['ID','Codigo MP','Material','Cantidad (g)','Tipo','Lote',
            'Proveedor','Fecha','Observaciones','Operador','N° Factura'];
  var rows=M.map(function(m){return [
    m.id||'', m.material_id||'', m.material_nombre||'', Number(m.cantidad)||0,
    m.tipo||'', m.lote||'', m.proveedor||'',
    (m.fecha||'').slice(0,19).replace('T',' '),
    m.observaciones||'', m.operador||'', m.numero_factura||''
  ];});
  dlExcelHTML('Movimientos_'+fhoy(), cols, rows);
}
async function exportarExcelProducciones(){
  var r=await fetch('/api/produccion'),d=await r.json(),P=d.producciones||[];
  if(!P.length){alert('Sin producciones');return;}
  var cols=['ID','Producto','Lote PT','Cantidad (kg)','Presentacion','Fecha','Operador','Estado'];
  var rows=P.map(function(p){return [
    p.id||'', p.producto||'', p.lote||'', Number(p.cantidad)||0,
    p.presentacion||'', (p.fecha||'').slice(0,19).replace('T',' '),
    p.operador||'', p.estado||''
  ];});
  dlExcelHTML('Producciones_'+fhoy(), cols, rows);
}
function fhoy(){var d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');}
// Compat: dlCSV y descargarCSV mantenidos para callers existentes ·
// usan ; como separador (Excel ES/Latam) + BOM UTF-8 + escape correcto.
function dlCSV(n,csv){
  // Si el caller ya pasa CSV armado, agregar BOM y bajarlo. Convertimos
  // comas por ; SOLO si no hay ya ; en el contenido (heuristica simple).
  var content = '﻿' + csv;
  var b=new Blob([content],{type:'text/csv;charset=utf-8'});
  var u=URL.createObjectURL(b);
  var a=document.createElement('a');
  a.href=u;a.download=n;
  document.body.appendChild(a);a.click();
  document.body.removeChild(a);URL.revokeObjectURL(u);
}
function descargarCSV(nombre,cols,rows){
  var sep=';';
  var lines=[cols.map(_csvEscape).join(sep)];
  rows.forEach(function(r){
    lines.push(r.map(_csvEscape).join(sep));
  });
  var csv='﻿'+lines.join('\r\n');
  var blob=new Blob([csv],{type:'text/csv;charset=utf-8'});
  var url=URL.createObjectURL(blob);
  var a=document.createElement('a');
  a.href=url;a.download=nombre;
  document.body.appendChild(a);a.click();document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Sprint Fabricación PRO · 20-may-2026 · paginación + búsqueda server-side
window._histProdOffset = 0;
window._histProdLimit = 50;
window._histProdDebounceTimer = null;
function _histProdDebounced(){
  if(window._histProdDebounceTimer) clearTimeout(window._histProdDebounceTimer);
  window._histProdDebounceTimer = setTimeout(function(){
    window._histProdOffset = 0;
    cargarHistProd();
  }, 350);
}
async function cargarHistProd(){
  // 4-jun-2026 · ahora pinta las ÓRDENES DE PRODUCCIÓN unificadas estilo MyBatch
  // (legajos EBR + registros simples) en el mismo contenedor. Mantiene los ids
  // hist-prod-body/footer/q para no romper los call-sites existentes.
  var tb=document.getElementById('hist-prod-body');
  var ft=document.getElementById('hist-prod-footer');
  if(!tb)return;
  var q = (((document.getElementById('hist-prod-q')||{}).value)||'').trim().toLowerCase();
  function gfmt(n){return n==null?'<span style="color:#94a3b8">—</span>':Number(n).toLocaleString('es-CO')+' g';}
  function estadoPill(e){
    var s=(e||'').toLowerCase(), bg='#f1f5f9', col='#475569';
    if(s.indexOf('cuarentena')>=0){bg='#dbeafe';col='#1e40af';}
    else if(s.indexOf('proceso')>=0){bg='#fef9c3';col='#854d0e';}
    else if(s.indexOf('aprob')>=0){bg='#dcfce7';col='#166534';}
    else if(s.indexOf('rechaz')>=0||s.indexOf('cancel')>=0){bg='#fee2e2';col='#991b1b';}
    return '<span style="background:'+bg+';color:'+col+';padding:2px 8px;border-radius:10px;font-size:0.78em;font-weight:700;white-space:nowrap">'+_escHTML(e||'')+'</span>';
  }
  try{
    var d=await (window._ordUnifFabFetch ? window._ordUnifFabFetch() : (await fetch('/api/brd/ordenes-unificadas?fase=fabricacion',{credentials:'same-origin'})).json());
    var ordenes=(d&&d.ordenes)||[];
    if(q){
      ordenes=ordenes.filter(function(o){
        return ((o.numero_op||'')+' '+(o.lote_bulk||'')+' '+(o.producto||'')).toLowerCase().indexOf(q)>=0;
      });
    }
    if(!ordenes.length){
      tb.innerHTML='<tr><td colspan="10" style="text-align:center;color:#999;padding:16px;">Sin órdenes que coincidan</td></tr>';
      if(ft) ft.innerHTML='Total: 0';
      return;
    }
    tb.innerHTML=ordenes.map(function(o){
      var aprob = o.aprobada!=null ? gfmt(o.aprobada) : (o.ml_envasable!=null ? (Number(o.ml_envasable).toLocaleString('es-CO')+' mL') : '<span style="color:#94a3b8">—</span>');
      var org = o.origen==='legajo'
        ? '<span style="background:#ede9fe;color:#6d28d9;padding:1px 7px;border-radius:8px;font-size:0.72em;font-weight:700">LEGAJO</span>'
        : '<span style="background:#f1f5f9;color:#64748b;padding:1px 7px;border-radius:8px;font-size:0.72em;font-weight:700">SIMPLE</span>';
      var _estLow=(o.estado||'').toLowerCase();
      // Solo legajos en proceso (no lotes reales: aprobado/rechazado/cuarentena·completado).
      var _puedeDescartar = (o.origen==='legajo' && o.ebr_id && _estLow.indexOf('aprob')<0 && _estLow.indexOf('rechaz')<0 && _estLow.indexOf('cuarentena')<0);
      var _btnDescartar = _puedeDescartar
        ? ' <button data-descartar-ebr data-id="'+o.ebr_id+'" data-prod="'+_escHTML(o.producto||'')+'" data-op="'+_escHTML(o.numero_op||'')+'" title="Eliminar este legajo (creado por error del sistema · solo Admin)" style="background:#fef2f2;color:#b91c1c;border:1px solid #fecaca;border-radius:5px;padding:3px 7px;font-size:11px;cursor:pointer">🗑️</button>'
        : '';
      var _btnFin = o.produccion_id
        ? '<button onclick="finalizarFabVivo('+o.produccion_id+')" style="background:#d97706;color:#fff;border:none;border-radius:5px;padding:4px 9px;font-size:10px;font-weight:700;cursor:pointer" title="Finalizar esta fabricación · el área queda sucia hasta limpiarla">&#9632; Finalizar</button>'
        : '';
      var acc;
      if(o.link){ acc = (_btnFin?_btnFin+' ':'')+'<a href="'+o.link+'" style="color:#7c3aed;font-weight:700;text-decoration:none;font-size:11px">Abrir →</a>'+_btnDescartar; }
      else if(o.produccion_id){ acc = _btnFin; }
      else { acc = '<button data-crear-legajo data-prod="'+_escHTML(o.producto||'')+'" data-g="'+(o.producida_g||o.teorica_g||'')+'" data-lote="'+_escHTML(o.lote_bulk||'')+'" style="background:#16a34a;color:#fff;border:none;border-radius:5px;padding:4px 9px;font-size:10px;font-weight:700;cursor:pointer" title="Crear el legajo electrónico (batch record) de esta orden">➕ Crear legajo</button>'; }
      return '<tr>'+
        '<td style="font-family:monospace;font-weight:700;color:#1e40af">'+_escHTML(o.numero_op||'')+'</td>'+
        '<td style="font-family:monospace;color:#6d28d9">'+_escHTML(o.lote_bulk||'—')+'</td>'+
        '<td style="font-weight:600">'+_escHTML(o.producto||'—')+'</td>'+
        '<td style="text-align:right">'+gfmt(o.teorica_g)+'</td>'+
        '<td style="text-align:right">'+gfmt(o.producida_g)+'</td>'+
        '<td style="text-align:right">'+aprob+'</td>'+
        '<td style="text-align:center">'+estadoPill(o.estado)+'</td>'+
        '<td style="text-align:center">'+org+'</td>'+
        '<td style="font-size:0.85em;color:#666">'+_escHTML(o.fecha||'—')+'</td>'+
        '<td style="text-align:center">'+acc+'</td>'+
      '</tr>';
    }).join('');
    if(ft){
      var rs=(d&&d.resumen)||{};
      ft.innerHTML='<span>'+(rs.total||ordenes.length)+' órdenes · '+(rs.legajos||0)+' con legajo EBR · '+(rs.simples||0)+' registro simple</span><span></span>';
    }
  }catch(e){
    console.error('cargarHistProd (ordenes) fallo:',e);
    tb.innerHTML='<tr><td colspan="10" style="text-align:center;color:#c00;padding:16px;">Error cargando órdenes: '+_escHTML(e.message)+'</td></tr>';
  }
}

// 4-jun-2026 · Crear legajo electrónico (EBR) para una orden SIMPLE, encadenando
// los endpoints YA existentes (cero backend nuevo): generar MBR desde fórmula →
// submit → firma e-Part11 (tu contraseña) → aprobar MBR → crear EBR → abrir detalle.
async function crearLegajoDesdeOrden(producto, gramos, loteDefault){
  producto=(producto||'').trim();
  if(!producto){producto=(prompt('Producto para crear el legajo:')||'').trim();}
  if(!producto)return;
  // La cantidad del legajo = la REALMENTE producida en esta orden (no el tamaño por
  // defecto del MBR). Si la orden no la trae, el backend cae al lote_size_g del MBR.
  var _gPlan = parseFloat(gramos);
  var lote=(prompt('N° de lote físico/comercial para el legajo de "'+producto+'":', (loteDefault||''))||'').trim();
  if(!lote)return;
  var pass=prompt('Tu contraseña de EOS (firma electrónica · aprueba el MBR · 21 CFR Part 11):');
  if(!pass)return;
  // Admins/usuarios con MFA: la firma exige también el código del autenticador.
  // Si no usas MFA, deja este campo vacío.
  var totp=(prompt('Código MFA de 6 dígitos (déjalo vacío si NO usas MFA):')||'').trim();
  function H(){var t=(typeof csrfTokenNec==='function')?csrfTokenNec():(window._csrfTok||'');return {'Content-Type':'application/json','X-CSRF-Token':t};}
  async function jpost(url,body){
    var r=await fetch(url,{method:'POST',credentials:'same-origin',headers:H(),body:JSON.stringify(body||{})});
    var d={}; try{d=await r.json();}catch(e){}
    return {ok:r.ok,status:r.status,d:d};
  }
  try{
    // 1) generar/obtener MBR desde la fórmula
    var g=await jpost('/api/brd/mbr/generar-desde-formula',{producto_nombre:producto});
    if(!g.ok){alert('No se pudo generar el MBR: '+((g.d&&g.d.error)||g.status)+(g.status===404?' · ¿el producto tiene fórmula registrada?':''));return;}
    var mbrId=g.d.id, estado=g.d.estado||'draft';
    // 2-5) si no está aprobado: submit → firmar → aprobar
    if(estado!=='aprobado'){
      if(estado==='draft'){
        var s=await jpost('/api/brd/mbr/'+mbrId+'/submit',{});
        if(!s.ok){alert('No se pudo enviar el MBR a revisión: '+((s.d&&s.d.error)||s.status));return;}
      }
      var ch=await jpost('/api/sign/challenge',{password:pass,totp_token:totp});
      if(!ch.ok){alert('No se pudo firmar: '+((ch.d&&ch.d.error)||ch.status)+'\n\n(Si dice "Token MFA inválido", revisá el código de 6 dígitos de tu app. Si dice "Credenciales inválidas", es la contraseña.)');return;}
      var sg=await jpost('/api/sign',{record_table:'mbr_templates',record_id:String(mbrId),meaning:'aprueba',challenge_token:ch.d.token});
      if(!sg.ok){alert('No se pudo firmar (¿tenés cédula en tu identidad?): '+((sg.d&&sg.d.error)||sg.status));return;}
      var ap=await jpost('/api/brd/mbr/'+mbrId+'/aprobar',{signature_id:sg.d.signature_id});
      if(!ap.ok){alert('No se pudo aprobar el MBR: '+((ap.d&&ap.d.error)||ap.status));return;}
    }
    // 6) crear el EBR (legajo) de fabricación con la cantidad REAL producida y abrir
    var _ebrBody={mbr_template_id:mbrId,lote:lote,fase:'fabricacion'};
    if(_gPlan && _gPlan>0){ _ebrBody.cantidad_objetivo_g=_gPlan; }
    var e=await jpost('/api/brd/ebr',_ebrBody);
    if(!e.ok){alert('No se pudo crear el legajo: '+((e.d&&e.d.error)||e.status));return;}
    location.href='/planta/orden/'+e.d.id;
  }catch(err){alert('Error de red: '+(err&&err.message||err));}
}
if(typeof document !== 'undefined' && !window._CREAR_LEGAJO_DELEG){
  window._CREAR_LEGAJO_DELEG = true;
  document.addEventListener('click', function(ev){
    var b = ev.target && ev.target.closest && ev.target.closest('[data-crear-legajo]');
    if(!b) return;
    crearLegajoDesdeOrden(b.getAttribute('data-prod')||'', b.getAttribute('data-g')||'', b.getAttribute('data-lote')||'');
  });
}
// Descartar (anular) un legajo creado por error · solo Admin · queda auditado.
if(typeof document !== 'undefined' && !window._DESCARTAR_EBR_DELEG){
  window._DESCARTAR_EBR_DELEG = true;
  document.addEventListener('click', async function(ev){
    var b = ev.target && ev.target.closest && ev.target.closest('[data-descartar-ebr]');
    if(!b) return;
    var id=b.getAttribute('data-id'); var op=b.getAttribute('data-op')||('EBR-'+id);
    if(!id) return;
    if(!confirm('¿ELIMINAR el legajo '+op+'?\n\nSe borra por completo (creado por error del sistema · solo Admin). NO aplica a lotes reales (completado/aprobado/rechazado).')) return;
    try{
      var t=(typeof csrfTokenNec==='function')?csrfTokenNec():(window._csrfTok||'');
      var r=await fetch('/api/brd/ebr/'+id+'/descartar',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:'{}'});
      var d={}; try{d=await r.json();}catch(e){}
      if(!r.ok){
        // 404 "EBR no encontrado" = ya estaba eliminado (p.ej. doble clic) → refrescá igual.
        if(r.status===404){ if(typeof cargarHistProd==='function') cargarHistProd(); }
        alert((r.status===403?'🔒 Solo Admin puede eliminar.':(r.status===404?'Ese legajo ya no existe (ya estaba eliminado).':'No se pudo eliminar: '+((d&&d.error)||r.status))));
        return;
      }
      if(typeof cargarHistProd==='function') cargarHistProd();
      else if(typeof cargarEBRs==='function') cargarEBRs();
    }catch(e){alert('Error de red: '+(e.message||e));}
  });
}

// Event delegation · ver detalle / reimprimir rótulos
if(typeof document !== 'undefined' && !window._PROD_HIST_DELEG){
  window._PROD_HIST_DELEG = true;
  document.addEventListener('click', function(ev){
    var btn = ev.target && ev.target.closest && ev.target.closest('[data-prod-act]');
    if(!btn) return;
    var act = btn.getAttribute('data-prod-act');
    var pid = btn.getAttribute('data-pid');
    if(!pid) return;
    if(act === 'rotulo'){
      // FIX 27-may-2026 PM · Sebastián · "los rotulos que salian era para
      // dispensar materias primas ahora salen unos raros". El botón antes
      // abría /api/produccion/<pid>/rotulo-reimprimir (rótulo simplificado
      // de 6 etiquetas identificación lote) · ahora abre el rótulo COMPLETO
      // de dispensación /rotulos/<producto>/<kg> con MPs + lotes FEFO + INCI.
      var prod = btn.getAttribute('data-prod');
      var kg = btn.getAttribute('data-kg');
      if (prod && kg){
        window.open('/rotulos/'+encodeURIComponent(prod)+'/'+(parseFloat(kg)||0).toFixed(1), '_blank');
      } else {
        // Fallback al endpoint legacy si data-* no está disponible (cache JS viejo)
        window.open('/api/produccion/'+pid+'/rotulo-reimprimir', '_blank');
      }
    } else if(act === 'detalle'){
      verDetalleProduccion(pid);
    }
  });
}

async function verDetalleProduccion(pid){
  try{
    var r = await fetch('/api/produccion/'+pid+'/detalle', {credentials:'same-origin'});
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    var existe = document.getElementById('modal-prod-detalle');
    if(existe) existe.remove();
    var div = document.createElement('div');
    div.id = 'modal-prod-detalle';
    div.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px';
    var costoStr = d.costo_estimado_cop ? '$'+Number(d.costo_estimado_cop).toLocaleString('es-CO') : '—';
    var descRows = (d.descuentos||[]).map(function(dt){
      return '<tr><td style="font-family:monospace">'+_escHTML(dt.material_id)+'</td><td>'+_escHTML(dt.material_nombre)+'</td>'+
        '<td style="font-family:monospace">'+_escHTML(dt.lote||'—')+'</td>'+
        '<td style="text-align:right;font-weight:700">'+Number(dt.cantidad_g).toLocaleString()+' g</td></tr>';
    }).join('');
    var snapRows = (d.formula_snapshot||[]).map(function(s){
      return '<tr><td style="font-family:monospace">'+_escHTML(s.material_id||'')+'</td><td>'+_escHTML(s.material_nombre||'')+'</td><td style="text-align:right">'+(s.porcentaje||0)+'%</td></tr>';
    }).join('');
    div.innerHTML =
      '<div style="background:#fff;border-radius:14px;padding:24px;max-width:840px;width:100%;max-height:90vh;overflow-y:auto">'+
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><h3 style="margin:0;color:#6d28d9">📋 Detalle producción · '+_escHTML(d.lote)+'</h3>'+
      '<button id="prod-det-close" style="background:none;border:none;font-size:1.4em;cursor:pointer">×</button></div>'+
      '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;background:#f8fafc;padding:12px;border-radius:8px;margin-bottom:14px;font-size:13px">'+
        '<div><b>Producto</b><br>'+_escHTML(d.producto)+'</div>'+
        '<div><b>Cantidad</b><br>'+d.cantidad_kg+' kg</div>'+
        '<div><b>Lote PT</b><br><span style="font-family:monospace;color:#dc2626;font-weight:700">'+_escHTML(d.lote)+'</span></div>'+
        '<div><b>Fecha</b><br>'+_escHTML((d.fecha||'').substring(0,16).replace('T',' '))+'</div>'+
        '<div><b>Operador</b><br>'+_escHTML(d.operador)+'</div>'+
        '<div><b>Presentación</b><br>'+_escHTML(d.presentacion||'—')+'</div>'+
        '<div><b>Costo estimado</b><br><span style="color:#6d28d9;font-weight:700">'+costoStr+'</span></div>'+
        '<div><b>Estado</b><br>'+_escHTML(d.estado)+'</div>'+
      '</div>'+
      '<h4 style="margin:14px 0 6px;color:#475569;font-size:13px">📉 MPs descontadas (con lotes FEFO usados)</h4>'+
      '<table class="table" style="font-size:11px"><thead><tr><th>Código</th><th>Material</th><th>Lote MP</th><th style="text-align:right">Cantidad</th></tr></thead><tbody>'+
        (descRows || '<tr><td colspan="4" style="text-align:center;color:#94a3b8">Sin descuentos registrados</td></tr>')+
      '</tbody></table>'+
      (snapRows ? '<h4 style="margin:14px 0 6px;color:#475569;font-size:13px">🧪 Fórmula al momento de producir (snapshot inmutable INVIMA)</h4>'+
      '<table class="table" style="font-size:11px"><thead><tr><th>Código</th><th>Material</th><th style="text-align:right">%</th></tr></thead><tbody>'+snapRows+'</tbody></table>' : '')+
      (d.observaciones ? '<div style="margin-top:12px;padding:8px;background:#fef3c7;border-left:3px solid #ca8a04;font-size:12px"><b>Observaciones:</b><br>'+_escHTML(d.observaciones)+'</div>' : '')+
      '<div style="margin-top:14px;display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap">'+
        '<button id="prod-det-ajustar" data-pid="'+pid+'" data-actual="'+d.cantidad_kg+'" style="background:#ca8a04;color:#fff;padding:8px 16px;border:none;border-radius:6px;font-weight:700;cursor:pointer" title="Corregir cantidad registrada (admin)">✏ Corregir cantidad</button>'+
        '<button id="prod-det-reimp" data-pid="'+pid+'" data-prod="'+_escHTML(d.producto||'')+'" data-kg="'+(d.cantidad_kg||0)+'" style="background:#c0392b;color:#fff;padding:8px 16px;border:none;border-radius:6px;font-weight:700;cursor:pointer" title="Rótulos completos de dispensación (MPs + lotes FEFO + INCI)">🏷 Re-imprimir rótulos</button>'+
      '</div>'+
      '</div>';
    document.body.appendChild(div);
    document.getElementById('prod-det-close').onclick = function(){
      var m = document.getElementById('modal-prod-detalle'); if(m) m.remove();
    };
    var reimpBtn = document.getElementById('prod-det-reimp');
    if(reimpBtn) reimpBtn.onclick = function(){
      // FIX 27-may-2026 PM · usar rótulo completo de dispensación, no el
      // simplificado de identificación lote (que es 'totalmente diferente').
      var prod = reimpBtn.getAttribute('data-prod');
      var kg = reimpBtn.getAttribute('data-kg');
      if (prod && kg){
        window.open('/rotulos/'+encodeURIComponent(prod)+'/'+(parseFloat(kg)||0).toFixed(1), '_blank');
      } else {
        window.open('/api/produccion/' + reimpBtn.getAttribute('data-pid') + '/rotulo-reimprimir', '_blank');
      }
    };
    var ajustBtn = document.getElementById('prod-det-ajustar');
    if(ajustBtn) ajustBtn.onclick = async function(){
      var aPid = ajustBtn.getAttribute('data-pid');
      var aAct = parseFloat(ajustBtn.getAttribute('data-actual')) || 0;
      var nueva = prompt('Cantidad actual: ' + aAct + ' kg\n\nNueva cantidad correcta (kg):', aAct.toString());
      if(!nueva) return;
      var nVal = parseFloat(nueva);
      if(!nVal || nVal <= 0){ alert('Cantidad inválida'); return; }
      if(Math.abs(nVal - aAct) < 0.001){ alert('Sin cambio · misma cantidad'); return; }
      var delta = (nVal - aAct).toFixed(2);
      var motivo = prompt('Motivo del ajuste (≥10 chars · INVIMA audit):\n\nEj: "registré 29kg por error, eran 30kg"');
      if(!motivo || motivo.trim().length < 10){ alert('Motivo requerido (≥10 chars)'); return; }
      if(!confirm('Ajustar de '+aAct+'kg → '+nVal+'kg (delta '+(delta>=0?'+':'')+delta+'kg)?\n\nSe ajustará el descuento de MPs automáticamente:\n- Si +: descontará más MP (FEFO)\n- Si -: devolverá MP al stock')) return;
      try{
        var r = await fetch('/api/produccion/'+aPid+'/ajustar-cantidad', {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({nueva_cantidad_kg: nVal, motivo: motivo.trim()}),
        });
        var dr = await r.json();
        if(!r.ok){
          var det = '';
          if(dr.faltantes && dr.faltantes.length){
            det = '\n\nMPs sin stock para subir cantidad:\n' + dr.faltantes.map(function(f){ return '• '+f.material+': faltan '+f.falta_g+'g'; }).join('\n');
          }
          alert('No se pudo ajustar: ' + (dr.error||r.status) + det);
          return;
        }
        var lines = ['✓ '+dr.mensaje];
        if((dr.movimientos_aplicados||[]).length){
          lines.push('\nMovimientos aplicados:');
          dr.movimientos_aplicados.forEach(function(m){
            lines.push('• '+m.tipo+': '+m.material+' · '+m.g+'g');
          });
        }
        alert(lines.join('\n'));
        var m = document.getElementById('modal-prod-detalle'); if(m) m.remove();
        if(typeof cargarHistProd === 'function') cargarHistProd();
      }catch(e){ alert('Error red: '+e.message); }
    };
    div.addEventListener('click', function(e){
      if(e.target === div){ var m = document.getElementById('modal-prod-detalle'); if(m) m.remove(); }
    });
  }catch(e){ alert('Error red: '+e.message); }
}


function switchTab(n,btn){
  document.querySelectorAll('.tab-content').forEach(function(t){t.classList.remove('active');});
  document.querySelectorAll('.tab-button').forEach(function(b){b.classList.remove('active');});
  document.querySelectorAll('.sub-tab-bar').forEach(function(b){b.classList.remove('visible');});
  document.getElementById(n).classList.add('active');
  if(btn) btn.classList.add('active');
  if(n==='stock') loadStock();
  if(n==='formulas'||n==='produccion') loadFormulas();
  if(n==='produccion'){ if(typeof cargarPendientesFab==='function') cargarPendientesFab(); if(typeof cargarHistProd==='function') cargarHistProd(); if(typeof cargarAreasFab==='function') cargarAreasFab(); }
  if(n==='cuarentena'){ cargarCuarentena(); cargarRetenido(); cargarModoInventario(); }
  if(n==='ingreso') initIngreso();
  if(n==='abc') loadABC();
  if(n==='conteo'){ cargarEstanterias(); cargarHistorialConteos(); cargarProgramacionCiclica(); }
  if(n==='empaque'){ cargarMeeAlertas(); cargarMeeStock(); cargarMeeHistorial(); meeCargarCuarentena(); meeCargarPorCalificar(); }
  if(n==='alertas'){ loadAlertasAll(); }
  // 'stock' (Inventario MP) ya NO incluye MEE · vive en tab 'empaque' aparte.
  if(n==='acondicionamiento'){loadAcond();cargarMeeParaAcond();}
  if(n==='liberacion'){loadLiberaciones('');cargarClientesLib();}
  if(n==='movimientos') loadMovimientosNuevo(true);
  if(n==='produccion') cargarHistProd();
  if(n==='movimientos') loadMovimientosNuevo(true);
  if(n==='programacion'){
    cargarProgramacion(null);
    // Sebastián 13-may-2026: default a Necesidades (no a Plan v2 legacy)
    // porque ahora Necesidades es la vista de decisión y Plan en curso
    // es solo la bitácora.
    if(typeof switchProgTab==='function') switchProgTab('necesidades');
  }
}


function switchGroup(barId,defaultTab,mainBtn){
  document.querySelectorAll('.tab-content').forEach(function(t){t.classList.remove('active');});
  document.querySelectorAll('.tab-button').forEach(function(b){b.classList.remove('active');});
  document.querySelectorAll('.sub-tab-bar').forEach(function(b){b.classList.remove('visible');});
  if(mainBtn) mainBtn.classList.add('active');
  var bar=document.getElementById(barId);
  if(bar){ bar.classList.add('visible'); bar.querySelectorAll('.sub-btn').forEach(function(b){b.classList.remove('active');}); bar.querySelectorAll('.sub-btn').forEach(function(b){ if(b.getAttribute('onclick')&&b.getAttribute('onclick').indexOf("'"+defaultTab+"'")>=0) b.classList.add('active'); }); }
  subSwitchTab(defaultTab,null,barId);
}
function subSwitchTab(tabId,btn,barId){
  document.querySelectorAll('.tab-content').forEach(function(t){t.classList.remove('active');});
  var bar=document.getElementById(barId);
  if(bar){ bar.querySelectorAll('.sub-btn').forEach(function(b){b.classList.remove('active');}); }
  if(btn) btn.classList.add('active');
  var target=document.getElementById(tabId);
  if(target) target.classList.add('active');
  if(tabId==='stock'){loadStock();}  /* MEE vive en tab 'empaque' separado */
  if(tabId==='formulas'||tabId==='produccion') loadFormulas();
  if(tabId==='produccion'){ if(typeof cargarEnCurso==='function')cargarEnCurso(); if(typeof cargarAreasFab==='function') cargarAreasFab(); }
  if(tabId==='historicos'){ if(typeof cargarHistProd==='function')cargarHistProd(); }
  if(tabId==='envasado') cargarEnvasadoRunner();
  if(tabId==='acondicionamiento') cargarAcondSimpleTab();
  if(tabId==='programacion') cargarProgramacion(null);
  if(tabId==='cuarentena'){ cargarCuarentena(); cargarModoInventario(); }
  if(tabId==='ingreso') initIngreso();
  if(tabId==='abc') loadABC();
  if(tabId==='conteo'){ cargarEstanterias(); cargarHistorialConteos(); cargarProgramacionCiclica(); }
  if(tabId==='alertas'){ loadAlertasAll(); }
  if(tabId==='movimientos') loadMovimientos();
}
// Deep-link · /inventarios#envasado abre Producción → Envasado (desde el redirect del
// tab OF de Órdenes · quitar redundancia · 9-jun). Defensivo: no-op si no hay hash/botones.
function _deepLinkTab(){
  try{
    var h=(location.hash||'').toLowerCase();
    var subkey=null;
    if(h==='#envasado') subkey='envasado';
    else if(h==='#acondicionamiento') subkey='acondicionamiento';
    else if(h==='#fabricacion'||h==='#produccion') subkey='produccion';
    else return;
    var mod=[].slice.call(document.querySelectorAll('.tab-button')).filter(function(b){return /switchGroup\(.bar-prodHub./.test(b.getAttribute('onclick')||'');})[0];
    if(mod) mod.click();
    var bar=document.getElementById('bar-prodHub');
    var sub=bar?[].slice.call(bar.querySelectorAll('.sub-btn')).filter(function(b){return (b.getAttribute('onclick')||'').indexOf("subSwitchTab('"+subkey+"'")>=0;})[0]:null;
    if(sub) sub.click();
  }catch(e){}
}
if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',_deepLinkTab);}else{setTimeout(_deepLinkTab,0);}
var _charts={};
async function loadDashboard(){
  try{
    var r=await fetch('/api/inventario'), d=await r.json();
    document.getElementById('stock-total').textContent=Math.round(d.stock_total||0).toLocaleString('es-CO')+' g';
    document.getElementById('materiales-count').textContent=d.movimientos||'0';
    var elProx=document.getElementById('producciones-proximas-count');
    if(elProx){
      var nProx = d.producciones_proximas||0;
      elProx.textContent = nProx;
      elProx.style.color = nProx>0 ? '#16a34a' : '#94a3b8';
    }
    document.getElementById('producciones-count').textContent=d.producciones||'0';

    // KPIs nuevos del dashboard replanteado en zonas AHORA/CERCA/CONTEXTO
    var k = d.kpis || {ahora:{}, cerca:{}, contexto:{}};
    function setKpi(id, val, fallbackZero){
      var el = document.getElementById(id);
      if(!el) return;
      var n = val||0;
      el.textContent = n;
      // Atenuar si está en cero (visual: todo OK)
      if(fallbackZero && n===0) el.style.opacity = '0.4';
      else el.style.opacity = '1';
    }
    var a = k.ahora || {};
    setKpi('kpi-mps-sin-stock', a.mps_sin_stock, true);
    setKpi('kpi-lotes-vencidos', a.lotes_vencidos, true);
    var ce = k.cerca || {};
    setKpi('kpi-venc-criticos', ce.venc_criticos_30d, true);
    setKpi('kpi-cuarentena', ce.lotes_cuarentena, true);
    setKpi('kpi-ocs-transito', ce.ocs_en_transito, true);
    setKpi('kpi-mees-bajo', ce.mees_bajo_minimo, true);
    // Sebastián 16-jun · si RECEPCION_AUTO_VIGENTE está encendido, la mercancía
    // entra disponible directo (sin Calidad): destildar la casilla de cuarentena.
    if (d.recepcion_auto_vigente){
      window._RECEPCION_AUTO_VIGENTE = true;
      ['ing-cuarentena','nmp-ing-cuarentena'].forEach(function(cid){
        var cb=document.getElementById(cid); if(cb) cb.checked=false;
      });
      var _invb=document.getElementById('cuar-inv-banner'); if(_invb) _invb.style.display='block';
    }
    fetch('/api/alertas-reabastecimiento').then(function(r2){return r2.json();}).then(function(ar){
      var n=ar.alertas?ar.alertas.length:0;
      var el=document.getElementById('alertas-count');
      if(el) el.textContent=n>0?n+' alertas!':'OK';
      var panel=document.getElementById('dash-alertas-rapidas');
      if(panel&&n>0){
        panel.style.display='block';
        var lista=document.getElementById('dash-alertas-lista');
        if(lista) lista.innerHTML=ar.alertas.slice(0,3).map(function(a){
          return '<div style="margin-bottom:4px;"><b>'+a.codigo_mp+'</b> '+a.nombre+' - Stock: '+a.stock_actual.toLocaleString()+'g / Min: '+a.stock_minimo.toLocaleString()+'g <span style="color:#cc0000;font-weight:700;">Deficit: '+a.deficit.toLocaleString()+'g</span></div>';
        }).join('')+(n>3?'<div style="color:#888;font-size:0.85em;">... y '+(n-3)+' mas</div>':'');
      } else if(panel){ panel.style.display='none'; }
    }).catch(function(){});
  }catch(e){ console.error(e); }
}

// Dashboard PRO #2 · render de los widgets Planta AHORA + Mes actual
function _renderDashInsights(d){
  if(!d) return;
  var pa = d.planta_ahora || {};
  var box = document.getElementById('dash-planta-ahora');
  if(box){
    box.style.display = 'block';
    var elEC = document.getElementById('pa-en-curso');
    if(elEC) elEC.textContent = pa.produciendo_ahora || 0;
    var elSL = document.getElementById('pa-salas-libres');
    if(elSL) elSL.textContent = pa.salas_libres || 0;
    var elSD = document.getElementById('pa-salas-detalle');
    if(elSD) elSD.textContent = 'de ' + (pa.salas_total||0) +
      ' · ocupadas ' + (pa.salas_ocupadas||0) +
      ' · sucias ' + (pa.salas_sucias||0);
    var elOp = document.getElementById('pa-operarios');
    if(elOp) elOp.textContent = pa.operarios_con_tarea_hoy || 0;
    var pp = pa.proxima_produccion;
    var elPP = document.getElementById('pa-proxima-prod');
    var elPF = document.getElementById('pa-proxima-fecha');
    if(pp && pp.producto){
      if(elPP) elPP.textContent = (pp.producto||'').slice(0,28);
      if(elPF) elPF.textContent = '📅 ' + (pp.fecha||'') + ' · ' + (pp.kg||0).toFixed(1) + ' kg';
    } else {
      if(elPP) elPP.textContent = 'Sin próximas';
      if(elPF) elPF.textContent = '—';
    }
  }
  // Mes actual
  var m = d.mes_actual || {};
  var mesBox = document.getElementById('dash-mes-actual');
  if(mesBox){
    mesBox.style.display = 'block';
    var elML = document.getElementById('mes-mes-label');
    if(elML) elML.textContent = '📊 ' + (m.mes||'');
    var elMR = document.getElementById('mes-resumen');
    if(elMR) elMR.textContent =
      (m.producciones_completadas||0) + ' de ' + (m.producciones_programadas||0) +
      ' producciones · ' + (m.kg_producidos||0).toLocaleString('es-CO') + ' kg';
    var pct = Math.max(0, Math.min(100, m.progreso_pct||0));
    var elPct = document.getElementById('mes-pct');
    if(elPct){
      elPct.textContent = pct.toFixed(0) + '%';
      elPct.style.color = pct >= 80 ? '#16a34a' : pct >= 50 ? '#ca8a04' : '#dc2626';
    }
    var elBar = document.getElementById('mes-bar');
    if(elBar) elBar.style.width = pct + '%';
  }
}
function _renderDashAlertasIa(d){
  var box = document.getElementById('dash-alertas-ia');
  if(!box) return;
  var al = (d && d.alertas) || [];
  if(!al.length){ box.style.display = 'none'; return; }
  var SEV = {
    critica: {bg:'#fee2e2', border:'#dc2626', txt:'#991b1b', emoji:'🚨'},
    advertencia: {bg:'#fef3c7', border:'#ca8a04', txt:'#854d0e', emoji:'⚠️'},
    info: {bg:'#dbeafe', border:'#1e40af', txt:'#1e40af', emoji:'ℹ️'},
  };
  var totals = d.por_severidad || {};
  var html = '<div style="background:#0f172a;color:#fff;border-radius:10px;padding:10px 14px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">' +
    '<div><span style="font-size:13px;font-weight:800">🤖 Alertas IA del Plan</span> <span style="font-size:11px;opacity:.8;margin-left:8px">' +
    (totals.critica||0) + ' crítica(s) · ' + (totals.advertencia||0) + ' advertencia(s)</span></div>' +
    '<button onclick="switchProgTab(\'calendario\')" style="background:rgba(255,255,255,.15);border:1px solid #fff;color:#fff;padding:4px 10px;border-radius:5px;font-size:11px;cursor:pointer">Abrir Calendario →</button>' +
  '</div>';
  al.slice(0, 4).forEach(function(a){
    var sev = SEV[a.severidad] || SEV.info;
    html += '<div style="background:' + sev.bg + ';border-left:4px solid ' + sev.border + ';border-radius:6px;padding:8px 12px;margin-top:6px;color:' + sev.txt + '">' +
      '<div style="font-weight:700;font-size:12px">' + sev.emoji + ' ' + _escHTML(a.titulo||'') + '</div>' +
      '<div style="font-size:11px;margin-top:1px;opacity:.95">' + _escHTML(a.detalle||'') + '</div>' +
    '</div>';
  });
  if(al.length > 4){
    html += '<div style="text-align:center;font-size:11px;color:#64748b;margin-top:6px">+' + (al.length - 4) + ' más · ver Calendario</div>';
  }
  box.innerHTML = html;
  box.style.display = 'block';
}

// Dashboard PRO · timer global auto-refresh + helper toast errores
var _DASH_TIMER=null;
function _dashToast(msg, isErr){
  var box=document.createElement('div');
  box.textContent=msg;
  box.style.cssText='position:fixed;bottom:20px;right:20px;background:'+(isErr?'#dc2626':'#16a34a')+';color:#fff;padding:10px 16px;border-radius:8px;font-size:13px;font-weight:600;box-shadow:0 4px 14px rgba(0,0,0,.25);z-index:99999';
  document.body.appendChild(box);
  setTimeout(function(){box.style.opacity='0';box.style.transition='opacity .4s';},2500);
  setTimeout(function(){if(box.parentNode)box.parentNode.removeChild(box);},3000);
}
function _dashStartAutoRefresh(){
  if(_DASH_TIMER) clearInterval(_DASH_TIMER);
  _DASH_TIMER=setInterval(function(){
    var chk=document.getElementById('dash-autorefresh');
    if(!chk||!chk.checked) return;
    if(typeof document!=='undefined' && document.visibilityState==='hidden') return;
    var dashTab=document.getElementById('dashboard');
    if(!dashTab||dashTab.style.display==='none') return;
    loadDashboardCompleto(true /*silent*/);
  }, 60000);
}
if(typeof document!=='undefined' && !window._DASH_VIS_LISTENER){
  window._DASH_VIS_LISTENER=true;
  document.addEventListener('visibilitychange',function(){
    if(document.visibilityState!=='visible') return;
    var dashTab=document.getElementById('dashboard');
    if(dashTab && dashTab.style.display!=='none') loadDashboardCompleto(true);
  });
}

async function loadDashboardCompleto(silent){
  // Dashboard PRO · Promise.all paraleliza los 3 fetches (antes serial).
  // Sebastián 20-may-2026 · audit Dashboard PRO.
  var t0=Date.now();
  var errores=[];
  try {
    // Dashboard PRO #2 · 4 fetches paralelos · loadDashboard ya hace su
    // propio fetch interno a /api/inventario + /api/alertas-reabastecimiento.
    var [statsR, _ignored, insightsR, alertasIaR] = await Promise.all([
      fetch('/api/dashboard-stats').then(function(r){return r.ok?r.json():null;}).catch(function(){errores.push('dashboard-stats');return null;}),
      loadDashboard(silent),  // KPIs principales · /api/inventario + alertas
      fetch('/api/dashboard/insights').then(function(r){return r.ok?r.json():null;}).catch(function(){errores.push('insights');return null;}),
      // PERF 9-jul (speed-audit #2): alertas-ia corre el motor COMPLETO de Necesidades · en el
      // refresh silencioso (timer 60s / visibilitychange) NO lo recomputamos (mantiene el banner
      // anterior). Solo en carga/refresh explícito. El backend además cachea la respuesta (TTL).
      silent ? Promise.resolve(null) : fetch('/api/plan/alertas-ia').then(function(r){return r.ok?r.json():null;}).catch(function(){return null;}),
    ]);
    if(insightsR) _renderDashInsights(insightsR);
    if(alertasIaR) _renderDashAlertasIa(alertasIaR);
    var d=statsR||{};
    var estados=d.estados_lotes||{};
    var ev=document.getElementById('dash-vencidos'); if(ev) ev.textContent=estados.VENCIDO||0;
    var ec=document.getElementById('dash-criticos'); if(ec) ec.textContent=estados.CRITICO||0;
    var ep=document.getElementById('dash-proximos'); if(ep) ep.textContent=estados.PROXIMO||0;
    var venc=d.vencimientos_por_mes||{}; var meses=Object.keys(venc);
    var ctx1=document.getElementById('chart-vencimientos');
    // Sebastián 20-may-2026 fix urgente · guard Chart.js no cargado
    if(typeof Chart === 'undefined'){
      ctx1 = null; // skip charts si CDN bloqueado
    }
    if(ctx1){
      if(_charts.venc){ _charts.venc.destroy(); }
      var emp=document.getElementById('chart-venc-empty');
      if(meses.length>0){
        ctx1.style.display='block'; if(emp) emp.style.display='none';
        _charts.venc=new Chart(ctx1.getContext('2d'),{
          type:'bar',
          data:{labels:meses,datasets:[{label:'Kg que vencen',data:meses.map(function(m){return venc[m].kg;}),
            backgroundColor:meses.map(function(m,i){return i===0?'rgba(204,0,0,0.7)':i<=1?'rgba(230,81,0,0.7)':'rgba(245,127,23,0.7)';}),borderRadius:4}]},
          options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,title:{display:true,text:'kg'}}}}
        });
      } else { ctx1.style.display='none'; if(emp) emp.style.display='block'; }
    }
    var top=d.top_stock||[]; var ctx2=document.getElementById('chart-top-stock');
    if(typeof Chart === 'undefined'){ ctx2 = null; }
    if(ctx2){
      if(_charts.top){ _charts.top.destroy(); }
      var emp2=document.getElementById('chart-stock-empty');
      if(top.length>0){
        ctx2.style.display='block'; if(emp2) emp2.style.display='none';
        _charts.top=new Chart(ctx2.getContext('2d'),{
          type:'bar',
          data:{labels:top.map(function(t){return t.nombre.length>18?t.nombre.substring(0,16)+'...':t.nombre;}),
            datasets:[{label:'Stock (kg)',data:top.map(function(t){return t.kg;}),backgroundColor:'rgba(102,126,234,0.7)',borderRadius:4}]},
          options:{indexAxis:'y',responsive:true,plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,title:{display:true,text:'kg'}}}}
        });
      } else { ctx2.style.display='none'; if(emp2) emp2.style.display='block'; }
    }
    // Alertas reabastecimiento ya las pinta loadDashboard internamente.
    // Dashboard PRO · timestamp última actualización + toast si hubo errores
    var lu=document.getElementById('dash-last-update');
    if(lu){
      var hora=new Date().toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
      var dur=Math.max(1,Math.round((Date.now()-t0)/100)/10);
      var sufijo=errores.length?(' · ⚠ '+errores.length+' fallos: '+errores.join(',')):'';
      lu.textContent='Última actualización '+hora+' · '+dur+'s'+sufijo;
      lu.style.color=errores.length?'#dc2626':'#94a3b8';
    }
    if(errores.length && !silent) _dashToast('Falló: '+errores.join(', '), true);
  }catch(e){
    console.error('Dashboard error:',e);
    if(!silent) _dashToast('Error cargando dashboard: '+(e.message||e), true);
    var lu=document.getElementById('dash-last-update');
    if(lu){ lu.textContent='⚠ Error · reintentá'; lu.style.color='#dc2626'; }
  }
  if(!_DASH_TIMER) _dashStartAutoRefresh();
}

async function loadStock(){
  var t0 = Date.now();
  try{
    // Sebastian 12-jun: por defecto la Bodega muestra SOLO lo que tiene stock real.
    // Las MPs en 0 (catalogo · a comprar) solo si el usuario marca el checkbox.
    var _verSin=(document.getElementById('stock-ver-sin')||{}).checked;
    var r=await fetch('/api/lotes'+(_verSin?'?incluir_sin_stock=1':'')), d=await r.json();
    _lotes=d.lotes||[];
    var _nSin=_lotes.filter(function(x){return (x.cantidad_g||0)<=0.01;}).length;
    document.getElementById('stock-count').textContent=
      _lotes.length+' filas'+(_verSin&&_nSin?(' ('+_nSin+' en 0)'):'');
    // Fix #6 + #10: aplicar sort si user pinó alguna columna · actualizar timestamp
    if(_STOCK_SORT && _STOCK_SORT.col) _aplicarSortStock();
    var qGen=((document.getElementById('stock-search')||{}).value||'').trim();
    var qLote=((document.getElementById('stock-search-lote')||{}).value||'').trim();
    if(qGen || qLote){
      _filterStockNow();
    } else {
      renderStock(_lotes);
    }
    _attachStockSortHandlers();
    var lu = document.getElementById('stock-last-update');
    if(lu){
      var hora = new Date().toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
      var dur = Math.max(1, Math.round((Date.now()-t0)/100)/10);
      lu.textContent = 'Última actualización ' + hora + ' · ' + dur + 's · ' + _lotes.length + ' lotes';
      lu.style.color = '#94a3b8';
    }
  }catch(e){
    document.getElementById('stock-body').innerHTML='<tr><td colspan="13" style="padding:20px;color:#c00;">Error al cargar: '+(e.message||e)+'</td></tr>';
    var lu2 = document.getElementById('stock-last-update');
    if(lu2){ lu2.textContent = '⚠ Error · reintentá'; lu2.style.color = '#dc2626'; }
  }
}
// Sprint Bodega MP PRO · 20-may-2026 · render con fix #4 (badge sutil),
// #8 (Estado consolidado · sin redundancia con Días), #15 (tooltip Min MP).
function renderStock(items){
  var tb=document.getElementById('stock-body');
  if(!items.length){tb.innerHTML='<tr><td colspan="13" style="text-align:center;color:#999;padding:20px;">Sin datos</td></tr>';return;}
  var bg={vencido:'#ffebeb',critico:'#fff3e0',proximo:'#fffde7',ok:'transparent',sin_stock:'#fafafa'};
  var fc={vencido:'#cc0000',critico:'#e65100',proximo:'#f57f17',ok:'#1a8a1a',sin_stock:'#64748b'};
  var lb={vencido:'VENCIDO',critico:'CRITICO',proximo:'PROXIMO',ok:'VIGENTE',sin_stock:'SIN STOCK'};
  var h='';
  // Fix #4: badge "Solicitada" solo en la PRIMERA fila visible de cada MP.
  // Antes aparecía en TODAS las filas del mismo MP · Luis veía "Solicitada"
  // en 3 lotes cuando en realidad hay 1 sola SOL al material.
  var primerLoteDelMP = {};
  items.forEach(function(i){
    var k = i.material_id || '';
    if(primerLoteDelMP[k] === undefined) primerLoteDelMP[k] = i.lote;
  });
  // Sebastián 21-may-2026 · marcar la primera fila de cada MP para que el
  // Min MP (g) solo se muestre una vez (las demás filas del mismo MP
  // muestran "↑" para indicar "ver fila de arriba"). Antes parecía que
  // cada lote tenía mínimo propio · confundía a Sebastián.
  var __primerLoteVisto = {};
  items.forEach(function(i){
    var mid = i.material_id || '';
    if(!__primerLoteVisto[mid]){ __primerLoteVisto[mid] = i.lote; }
  });
  items.forEach(function(i,idx){ var gi=_lotes.indexOf(i); if(gi<0)gi=idx;
    var a=i.alerta||'ok';
    var esPrimerLoteDeMP = __primerLoteVisto[i.material_id||''] === i.lote;
    var qc=i.cantidad_g<=0?'color:#cc0000;font-weight:700;':i.cantidad_g<500?'color:#e68a00;font-weight:700;':'color:#1a8a1a;font-weight:700;';
    var stockTotalMP=(typeof i.stock_total_mp_g==='number')?i.stock_total_mp_g:i.cantidad_g;
    var bajo_min=i.stock_min_g>0 && stockTotalMP < i.stock_min_g;
    var min_style=bajo_min?'background:#ffebeb;color:#cc0000;font-weight:700;':'';
    var min_title='Mínimo del MP completo: '+(i.stock_min_g||0).toLocaleString('es-CO')+' g · '+
                  'Total MP (suma de todos sus lotes): '+stockTotalMP.toLocaleString('es-CO')+' g'+
                  (bajo_min?' · ⚠ por debajo del mínimo':' · OK');
    var dias=i.dias_para_vencer!=null?i.dias_para_vencer:'';
    // Columna Estado consolidada: chip color + días dentro
    var estadoCell='—';
    if(a==='sin_stock'){
      estadoCell='<span style="background:#f1f5f9;color:#64748b;padding:2px 7px;border-radius:10px;font-weight:700;font-size:0.78em;border:1px solid #cbd5e1;">SIN STOCK</span>';
    } else if(i.fecha_vencimiento){
      var diasTxt = (dias===''?'':' · '+dias+'d');
      estadoCell='<div style="display:flex;flex-direction:column;align-items:center;gap:1px">'+
        '<span style="background:'+bg[a]+';color:'+fc[a]+';padding:2px 7px;border-radius:10px;font-weight:700;font-size:0.78em;border:1px solid '+fc[a]+';">'+lb[a]+'</span>'+
        '<span style="font-size:10px;color:#64748b">'+_escHTML(i.fecha_vencimiento)+diasTxt+'</span>'+
      '</div>';
    }
    h+='<tr style="background:'+bg[a]+';font-size:0.83em;">';
    h+='<td style="font-family:monospace;color:#555;">'+_escHTML(i.material_id||'')+'</td>';
    h+='<td style="font-weight:600;">'+_escHTML(i.nombre_inci||i.material_nombre||'')+'</td>';
    h+='<td style="color:#888;font-size:0.78em;">'+_escHTML(i.material_nombre||'')+'</td>';
    h+='<td style="color:#888;">'+_escHTML(i.tipo||'')+'</td>';
    h+='<td style="color:#555;">'+(i.proveedor?_escHTML(i.proveedor):'<span style="color:#bbb;">— sin proveedor —</span>')+' <button onclick="abrirEditarProveedor('+gi+')" title="Editar proveedor" style="margin-left:4px;padding:1px 6px;font-size:0.75em;background:#e8f5f5;color:#6d28d9;border:1px solid #b8dada;border-radius:4px;cursor:pointer;">&#9999;&#65039;</button></td>';
    // Mostrar Min solo en primera fila de cada MP · "↑" en las demás (gris)
    var celdaMin = esPrimerLoteDeMP
      ? (i.stock_min_g||0).toLocaleString()
      : '<span style="color:#cbd5e1" title="Mínimo aplica al material completo · ver primera fila del mismo MP">↑</span>';
    h+='<td style="text-align:right;'+(esPrimerLoteDeMP?min_style:'')+'" title="'+_escHTML(min_title)+'">'+celdaMin+'</td>';
    h+='<td style="font-family:monospace;">'+_escHTML(i.lote||'')+'</td>';
    h+='<td style="text-align:right;'+qc+'">'+(i.cantidad_g||0).toLocaleString()+'</td>';
    h+='<td style="text-align:center;font-weight:700;color:#667eea;">'+_escHTML(i.estanteria||'')+'</td>';
    h+='<td style="text-align:center;">'+_escHTML(i.posicion||'')+'</td>';
    h+='<td style="text-align:center;color:'+fc[a]+';white-space:nowrap">'+_escHTML(i.fecha_vencimiento||'—')+'</td>';
    h+='<td style="text-align:center;">'+estadoCell+'</td>';
    // Fix #4 + #13: acciones agrupadas + badge sutil solicitada
    var esPrimerLote = primerLoteDelMP[i.material_id||''] === i.lote;
    var btnSolicitar;
    if(i.tiene_solicitud_pendiente && esPrimerLote){
      btnSolicitar = '<button onclick="abrirSolicitarLote('+gi+')" style="padding:3px 7px;font-size:0.72em;background:#fef3c7;color:#92400e;border:1px solid #f59e0b;border-radius:4px;font-weight:700;" title="Ya hay SOL pendiente para este MP">&#x1F4BC;</button>';
    } else if(i.tiene_solicitud_pendiente){
      btnSolicitar = '<button onclick="abrirSolicitarLote('+gi+')" style="padding:3px 7px;font-size:0.72em;background:#f1f5f9;color:#475569;border:1px solid #cbd5e1;border-radius:4px;" title="SOL pendiente al MP · podés crear otra">Sol+</button>';
    } else {
      btnSolicitar = '<button onclick="abrirSolicitarLote('+gi+')" style="padding:3px 7px;font-size:0.72em;background:#27ae60;color:#fff;border-radius:4px;" title="Crear SOL de compra">Sol</button>';
    }
    h+='<td style="text-align:center;white-space:nowrap"><div style="display:inline-flex;gap:3px;flex-wrap:wrap;justify-content:center">'+
      '<button onclick="abrirAjusteIdx('+gi+')" style="padding:3px 7px;font-size:0.72em;background:#f0ad4e;color:#fff;border-radius:4px;" title="Ajustar stock / ubicación / fecha / lote">Ajustar</button>'+
      '<button onclick="verHistorialLote('+gi+')" style="padding:3px 7px;font-size:0.72em;background:#667eea;color:#fff;border-radius:4px;" title="Ver movimientos del lote">Hist</button>'+
      '<button onclick="reimprimirRotuloLote('+gi+')" style="padding:3px 7px;font-size:0.72em;background:#6d28d9;color:#fff;border-radius:4px;" title="Re-imprimir el rótulo de este lote">&#128424;</button>'+
      btnSolicitar+
      (window._ES_ADMIN_DASH ? '<button onclick="abrirEliminarLote('+gi+')" style="padding:3px 7px;font-size:0.72em;background:#c0392b;color:#fff;border-radius:4px;" title="Eliminar lote (admin)">Borrar</button>' : '')+
    '</div></td>';
    h+='</tr>';
  });
  tb.innerHTML=h;
}

// Sprint Bodega MP PRO · 20-may-2026 fix #6: ordenamiento por columna.
// Cualquier <th data-sort="X"> ordena por ese campo. Click toggle asc/desc.
var _STOCK_SORT = {col:null, dir:'asc'};
function _attachStockSortHandlers(){
  var row = document.getElementById('stock-thead-row');
  if(!row || row._sortBound) return;
  row._sortBound = true;
  row.querySelectorAll('th[data-sort]').forEach(function(th){
    th.addEventListener('click', function(){
      var col = th.getAttribute('data-sort');
      if(_STOCK_SORT.col === col){
        _STOCK_SORT.dir = (_STOCK_SORT.dir === 'asc') ? 'desc' : 'asc';
      } else {
        _STOCK_SORT.col = col; _STOCK_SORT.dir = 'asc';
      }
      _aplicarSortStock();
      _refreshStockSortIcons();
    });
  });
}
function _refreshStockSortIcons(){
  var row = document.getElementById('stock-thead-row');
  if(!row) return;
  row.querySelectorAll('th[data-sort]').forEach(function(th){
    var ico = th.querySelector('.sort-ico');
    if(!ico) return;
    if(th.getAttribute('data-sort') === _STOCK_SORT.col){
      ico.textContent = (_STOCK_SORT.dir === 'asc') ? '▲' : '▼';
      ico.style.color = '#7c3aed';
    } else { ico.textContent = ''; }
  });
}
function _aplicarSortStock(){
  if(!_STOCK_SORT.col) return;
  var col = _STOCK_SORT.col, dir = _STOCK_SORT.dir;
  _lotes.sort(function(a, b){
    var va = a[col], vb = b[col];
    if(va == null) va = '';
    if(vb == null) vb = '';
    var cmp;
    if(typeof va === 'number' && typeof vb === 'number'){
      cmp = va - vb;
    } else {
      cmp = String(va).localeCompare(String(vb), 'es', {numeric:true, sensitivity:'base'});
    }
    return dir === 'asc' ? cmp : -cmp;
  });
  // Re-aplicar filtro para que orden se vea
  if(typeof _filterStockNow === 'function') _filterStockNow();
  else renderStock(_lotes);
}
// Sebastian 8-may-2026: input dedicado para buscar por LOTE +
// el input general (MP/INCI/proveedor). Ambos se aplican en AND.
// Si ambos vacios → muestra todo. Si solo lote → filtra por lote.
// Si ambos llenos → match en general Y lote.
// Sprint Bodega MP PRO · 20-may-2026 fix #5: debounce 180ms para evitar
// re-render en cada keystroke (387 MPs × varios lotes lag en mobile).
var _STOCK_FILTER_TIMER = null;
function filterStock(){
  if(_STOCK_FILTER_TIMER) clearTimeout(_STOCK_FILTER_TIMER);
  _STOCK_FILTER_TIMER = setTimeout(_filterStockNow, 180);
}
function _filterStockNow(){
  var qGen=(document.getElementById('stock-search')||{}).value||'';
  var qLote=(document.getElementById('stock-search-lote')||{}).value||'';
  qGen=qGen.toLowerCase().trim();
  qLote=qLote.toLowerCase().trim();
  var f=_lotes.filter(function(i){
    var matchGen=!qGen||(
      (i.material_id||'').toLowerCase().includes(qGen)||
      (i.material_nombre||'').toLowerCase().includes(qGen)||
      (i.nombre_inci||'').toLowerCase().includes(qGen)||
      (i.proveedor||'').toLowerCase().includes(qGen)||
      (i.lote||'').toLowerCase().includes(qGen));
    var matchLote=!qLote||(i.lote||'').toLowerCase().includes(qLote);
    return matchGen && matchLote;
  });
  var hint=qLote?(' lote~"'+qLote+'"'):'';
  document.getElementById('stock-count').textContent=f.length+' de '+_lotes.length+hint;
  renderStock(f);
}

async function initIngreso(){
  if(Object.keys(_cat).length===0){
    try{var r=await fetch('/api/maestro-mps'),d=await r.json();(d.mps||[]).forEach(function(mp){_cat[mp.codigo_mp]=mp;});}catch(e){}
  }
  cargarHistIngreso(true);
  cargarOCsPendientes();
  // Sprint Recepciones PRO: persistencia + auto-save + restore draft
  if(typeof mostrarUltimoIngresoPersistido==='function') mostrarUltimoIngresoPersistido();
  if(typeof engancharAutoSaveIngreso==='function') engancharAutoSaveIngreso();
  if(typeof restaurarIngresoDraft==='function') restaurarIngresoDraft();
}
function ocultarDropMP(){var d=document.getElementById('mp-dropdown');if(d)d.style.display='none';}
// FIX 6-jun-2026: escapeHtml faltaba en este <script> (estaba escapeHtmlNec en
// otro scope) → el dropdown del Ingreso MP tiraba "escapeHtml is not defined" y
// no dejaba ingresar materias primas. Definición global aquí.
function escapeHtml(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function seleccionarMP(mp){
  document.getElementById('ing-cod').value=mp.codigo_mp;
  document.getElementById('ing-inci').value=mp.nombre_inci||'';
  document.getElementById('ing-nombre').value=mp.nombre_comercial||'';
  document.getElementById('ing-tipo').value=mp.tipo||'';
  var p=document.getElementById('ing-prov');if(p&&!p.value)p.value=mp.proveedor||'';
  var st=document.getElementById('ing-status');
  if(st){st.textContent='✓ '+mp.nombre_comercial+' ('+mp.codigo_mp+')';st.style.color='#27ae60';}
  var panel=document.getElementById('ing-nueva-mp-inline');if(panel)panel.style.display='none';
  ocultarDropMP();
}
async function buscarMPIngreso(val){
  val=(val||'').trim();
  var st=document.getElementById('ing-status'),panel=document.getElementById('ing-nueva-mp-inline'),dd=document.getElementById('mp-dropdown');
  if(val.length<2){
    if(st)st.textContent='';
    ['ing-inci','ing-nombre','ing-tipo'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='';});
    if(panel)panel.style.display='none';
    if(dd)dd.style.display='none';
    return;
  }
  // Búsqueda local primero (rápido · sin HTTP)
  var mps=Object.values(_cat);
  var busq=val.toLowerCase();
  var matches=mps.filter(function(m){
    return (m.codigo_mp||'').toLowerCase().includes(busq)||(m.nombre_comercial||'').toLowerCase().includes(busq)||(m.nombre_inci||'').toLowerCase().includes(busq);
  }).slice(0,12);

  // SHOPIFY-FIX · 22-may-2026 · si no matchea local · fallback a endpoint
  // inteligente con aliases INCI (SAP → Sodium Ascorbyl Phosphate)
  var aliasInfo=null;
  if(!matches.length && val.length>=2){
    try{
      var r=await fetch('/api/maestro-mps/buscar-inteligente?q='+encodeURIComponent(val));
      if(r.ok){
        var d=await r.json();
        if(d.mps && d.mps.length){
          matches=d.mps.slice(0,12);
          if(d.aliases_aplicados && d.aliases_aplicados.length){
            aliasInfo=d.aliases_aplicados[0];
          }
        }
      }
    }catch(e){}
  }

  window._mpMatches=matches;
  if(dd){
    if(!matches.length){dd.style.display='none';}
    else{
      dd.style.display='block';
      var header='';
      if(aliasInfo){
        header='<div style="padding:7px 14px;background:#fff3cd;border-bottom:1px solid #ffc107;font-size:0.82em;color:#856404">💡 <b>'+escapeHtml(aliasInfo.alias)+'</b> = <i>'+escapeHtml(aliasInfo.inci_canonical)+'</i></div>';
      }
      dd.innerHTML=header+matches.map(function(m,i){
        var via=m.match_via?' <span style="color:#10b981;font-size:0.75em">['+m.match_via+']</span>':'';
        var _sec=(m.nombre_comercial&&m.nombre_inci&&m.nombre_comercial!==m.nombre_inci)?' <span style="color:#888;font-size:0.82em;">'+escapeHtml(m.nombre_comercial)+'</span>':'';
        return '<div class="mp-item" style="padding:9px 14px;cursor:pointer;border-bottom:1px solid #eee;font-size:0.9em;" onmousedown="seleccionarMP(_mpMatches['+i+'])">'+'<span style="font-family:monospace;color:#667eea;font-size:0.85em;">'+escapeHtml(m.codigo_mp)+'</span> &mdash; <strong>'+escapeHtml(m.nombre_inci||m.nombre_comercial||'')+'</strong>'+_sec+via+(m.proveedor?' <span style="color:#888;font-size:0.82em;">('+escapeHtml(m.proveedor)+')</span>':'')+'</div>';
      }).join('');
    }
  }
  var found=mps.find(function(m){return (m.codigo_mp||'').toLowerCase()===busq;});
  if(found){seleccionarMP(found);}
  else if(!matches.length){
    if(st){st.textContent='MP nueva — llena los datos';st.style.color='#e67e22';}
    if(panel)panel.style.display='block';
  } else {
    if(st){st.textContent='Selecciona una opcion de la lista';st.style.color='#667eea';}
  }
}


async function cargarOCsPendientes(){
  try{
    var r=await fetch('/api/ordenes-compra/pendientes-recepcion');
    if(!r.ok) return;
    var ocs=await r.json();
    var sel=document.getElementById('ing-oc-sel');
    if(!sel) return;
    // clear existing options except first placeholder
    while(sel.options.length>1) sel.remove(1);
    (ocs||[]).forEach(function(oc){
      (oc.items||[]).forEach(function(item){
        var opt=document.createElement('option');
        opt.value=oc.numero_oc+'|'+item.codigo_mp;
        var kg=((item.cantidad_g||0)/1000).toFixed(2);
        opt.textContent=oc.numero_oc+' — '+item.nombre_mp+' ('+kg+' kg pendientes)';
        opt.dataset.codigo=item.codigo_mp;
        opt.dataset.nombre=item.nombre_mp;
        opt.dataset.inci=item.nombre_inci||'';
        opt.dataset.proveedor=oc.proveedor||'';
        opt.dataset.precio=item.precio_unitario||'';
        sel.appendChild(opt);
      });
    });
  }catch(e){}
}
function autocompletarDesdeOC(){
  var sel=document.getElementById('ing-oc-sel');
  if(!sel||sel.selectedIndex<1) return;
  var opt=sel.options[sel.selectedIndex];
  if(!opt.dataset.codigo) return;
  var cod=document.getElementById('ing-cod');
  var nom=document.getElementById('ing-nombre');
  var inci=document.getElementById('ing-inci');
  var prov=document.getElementById('ing-prov');
  var precio=document.getElementById('ing-precio-kg');
  // Sprint Recepciones PRO fix #16: confirm si OC pisa proveedor manual escrito
  if(prov && prov.value && prov.value.trim() && opt.dataset.proveedor &&
     prov.value.trim().toLowerCase() !== (opt.dataset.proveedor||'').toLowerCase()){
    if(!confirm('Ya escribiste proveedor "'+prov.value+'" y la OC tiene "'+opt.dataset.proveedor+'". ¿Reemplazar con el de la OC?')){
      // mantener el manual · solo autocompletar el resto
    } else {
      prov.value = opt.dataset.proveedor || '';
    }
  } else if(prov) {
    prov.value = opt.dataset.proveedor || '';
  }
  if(cod) cod.value=opt.dataset.codigo;
  if(nom) nom.value=opt.dataset.nombre||'';
  if(inci) inci.value=opt.dataset.inci||'';
  if(precio && opt.dataset.precio) precio.value=opt.dataset.precio;
  if(cod) cod.dispatchEvent(new Event('input'));
  calcularValorTotal();
}
function calcularValorTotal(){
  var cant=parseFloat(document.getElementById('ing-cant')?document.getElementById('ing-cant').value:0)||0;
  var precio=parseFloat(document.getElementById('ing-precio-kg')?document.getElementById('ing-precio-kg').value:0)||0;
  var vt=document.getElementById('ing-valor-total');
  if(!vt) return;
  var val=(cant/1000)*precio;
  vt.value=val>0?'$'+val.toLocaleString('es-CO',{maximumFractionDigits:0}):'';
}
async function checkLoteExistente(){
  // Sebastián 9-jul: si el (material, lote) YA existe en bodega, avisar que esta recepción SUMA al lote
  // existente (no crea uno nuevo) + auto-rellenar vencimiento/ubicación. Read-only.
  var cod=(document.getElementById('ing-cod').value||'').toUpperCase().trim();
  var lote=(document.getElementById('ing-lote').value||'').trim();
  var box=document.getElementById('ing-lote-info');
  if(!box) return;
  if(!cod||!lote){ box.style.display='none'; return; }
  try{
    var r=await fetch('/api/recepcion/lote-info?codigo='+encodeURIComponent(cod)+'&lote='+encodeURIComponent(lote),{credentials:'same-origin'});
    var d=await r.json();
    if(d && d.existe){
      var cant=parseFloat((document.getElementById('ing-cant')||{}).value)||0;
      var total=d.stock_g+cant;
      box.innerHTML='&#128230; <b>El lote '+lote+' ya existe</b> con <b>'+d.stock_g.toLocaleString('es-CO')+' g</b>'+(d.estado_lote?(' ('+d.estado_lote+')'):'')+'. Esta recepci&oacute;n <b>SUMA</b> al mismo lote'+(cant>0?(' &rarr; nuevo total <b>'+total.toLocaleString('es-CO')+' g</b>'):'')+'. No se crea un lote nuevo.';
      box.style.display='block';
      var ev=document.getElementById('ing-vence'); if(ev&&!ev.value&&d.vencimiento){ev.value=d.vencimiento;}
      var ee=document.getElementById('ing-est'); if(ee&&!ee.value&&d.estanteria){ee.value=d.estanteria;}
      var ep=document.getElementById('ing-pos'); if(ep&&!ep.value&&d.posicion){ep.value=d.posicion;}
    } else { box.style.display='none'; }
  }catch(e){ box.style.display='none'; }
}
async function registrarIngreso(){
  var cod=(document.getElementById('ing-cod').value||'').toUpperCase().trim();
  var cant=parseFloat(document.getElementById('ing-cant').value)||0;
  if(!cod){alert('Ingresa el codigo MP');return;}
  if(cant<=0){alert('Ingresa una cantidad valida');return;}
  var esNueva=document.getElementById('ing-nueva-mp-inline')&&document.getElementById('ing-nueva-mp-inline').style.display!=='none';
  var ocSel=document.getElementById('ing-oc-sel');
  var ocVal=ocSel&&ocSel.value?ocSel.value:'';
  var numOC=ocVal?ocVal.split('|')[0]:'';
  var enCuarentena=document.getElementById('ing-cuarentena')&&document.getElementById('ing-cuarentena').checked;
  var data={codigo_mp:cod,nombre_comercial:document.getElementById('ing-nombre').value||'',
    lote:document.getElementById('ing-lote').value||'',cantidad:cant,operador:OPER_ACTUAL,
    fecha_vencimiento:document.getElementById('ing-vence').value||'',
    estanteria:document.getElementById('ing-est').value||'',
    posicion:document.getElementById('ing-pos').value||'',
    proveedor:document.getElementById('ing-prov').value||'',
    observaciones:document.getElementById('ing-obs').value||'',
    precio_kg:parseFloat(document.getElementById('ing-precio-kg')?document.getElementById('ing-precio-kg').value:0)||0,
    numero_factura:document.getElementById('ing-factura')?document.getElementById('ing-factura').value.trim():'',
    numero_oc:numOC,
    cuarentena:enCuarentena};
  if(esNueva){
    data.nombre_inci=document.getElementById('ing-inci-new')?document.getElementById('ing-inci-new').value:'';
    data.tipo=document.getElementById('ing-tipo-new')?document.getElementById('ing-tipo-new').value:'';
    data.stock_minimo=parseFloat(document.getElementById('ing-smin-new')?document.getElementById('ing-smin-new').value:0)||0;
  }
  // Idempotencia (M31/M45 · 7-jul): token unico por ENVIO · el backend lo reclama con UNIQUE. Mismo token si un
  // doble-click se cuela antes del disable o en un reintento de red; se limpia SOLO al exito (proximo envio regenera).
  window._recTok = window._recTok || (crypto.randomUUID ? crypto.randomUUID() : String(Date.now())+'-'+Math.random());
  data.recepcion_id = window._recTok;
  // B4: disable button to prevent double-submission
  var btn=document.querySelector('button[onclick="registrarIngreso()"]');
  if(btn){btn.disabled=true;btn.textContent='Registrando...';}
  try{
    var r=await fetch('/api/recepcion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    if(r.ok){
      _ultimoIng=res;
      // Sprint Recepciones PRO fix #6: persistir en localStorage
      try{ localStorage.setItem('eos_ultimo_ingreso', JSON.stringify({
        codigo:res.codigo, lote:res.lote, cantidad:res.cantidad,
        nombre:res.nombre, mov_id:res.mov_id, at:Date.now(),
      })); }catch(_ls){}
      // Sprint Recepciones PRO fix #12: alerta precio si llegó
      var alertaP = res.alerta_precio ? '<div style="background:#fef3c7;color:#92400e;border:1px solid #f59e0b;padding:8px 12px;margin-top:4px;border-radius:6px;font-size:13px">'+res.alerta_precio+'</div>' : '';
      var ocWarn = res.oc_warning?'<br><span style="color:#e65100;font-size:0.9em;">⚠ '+res.oc_warning+'</span>':'';
      var successMsg='<div class="alert-success">'+res.message+(enCuarentena?' — CUARENTENA (Calidad notificada)':'')+ocWarn+'</div>' + alertaP;
      limpiarIngreso();
      window._recTok=null;  // envio exitoso -> el proximo ingreso genera token nuevo (7-jul)
      // Sprint Recepciones PRO fix #11: limpiar auto-save draft
      try{ localStorage.removeItem('eos_ing_draft'); }catch(_ls2){}
      document.getElementById('ing-msg').innerHTML=successMsg;
      if(btn){btn.disabled=false;btn.textContent='✓ Registrar Entrada';}
      if(typeof mostrarUltimoIngresoPersistido==='function') mostrarUltimoIngresoPersistido();
      await cargarHistIngreso(true);
      await cargarOCsPendientes();
    } else {
      // Sprint Recepciones PRO · errores con hints accionables
      var errMsg = res.error || 'Error al registrar';
      var hint = '';
      if(res.factura_obligatoria){
        hint = '<div style="margin-top:6px;font-size:12px"><b>Cómo arreglarlo:</b> escribí el N° de factura en el campo "N° Factura / Remisión" antes de registrar.</div>';
      } else if(res.cantidad_excede_oc){
        hint = '<div style="margin-top:6px;font-size:12px">Pendiente real: <b>'+(res.pendiente_oc_g||0).toLocaleString()+'g</b>. Si recibiste de más a propósito, registrá la diferencia como ingreso libre (sin vincular OC).</div>';
      } else if(res.posible_duplicado){
        hint = '<div style="margin-top:6px;font-size:12px">Si es un ingreso intencional distinto, cambiá <b>lote</b> o <b>cantidad</b> y reintentá.</div>';
      }
      document.getElementById('ing-msg').innerHTML='<div class="alert-error">'+errMsg+hint+'</div>';
      if(btn){btn.disabled=false;btn.textContent='✓ Registrar Entrada';}
    }
  }catch(e){
    document.getElementById('ing-msg').innerHTML='<div class="alert-error">Error de red: '+e.message+'</div>';
    if(btn){btn.disabled=false;btn.textContent='✓ Registrar Entrada';}
  }
}
function generarRotuloIngreso(){
  // Sprint Recepciones PRO fix #6: si _ultimoIng está vacío, leer de localStorage
  if(!_ultimoIng){
    try{ _ultimoIng = JSON.parse(localStorage.getItem('eos_ultimo_ingreso')||'null'); }catch(e){}
  }
  if(!_ultimoIng){alert('Registra un ingreso primero');return;}
  window.open('/rotulo-recepcion/'+encodeURIComponent(_ultimoIng.codigo)+'/'+encodeURIComponent(_ultimoIng.lote||'SL')+'/'+(parseFloat(_ultimoIng.cantidad)||0).toFixed(1),'_blank');
}

// Sprint Recepciones PRO · 20-may-2026 · fix #6: mostrar último ingreso
// persistido al cargar el tab (sobrevive refresh por hasta 24h).
function mostrarUltimoIngresoPersistido(){
  var box = document.getElementById('ing-ultimo-persistido');
  if(!box) return;
  try{
    var data = localStorage.getItem('eos_ultimo_ingreso');
    if(!data){ box.style.display='none'; return; }
    var u = JSON.parse(data);
    var hace = Math.round((Date.now() - (u.at||0))/60000);
    if(hace > 60*24){ localStorage.removeItem('eos_ultimo_ingreso'); box.style.display='none'; return; }
    box.style.display='block';
    box.innerHTML = '📋 Último ingreso: <b>'+_escHTML(u.nombre||u.codigo)+'</b> · lote <code>'+_escHTML(u.lote||'')+'</code> · ' +
      (u.cantidad||0).toLocaleString()+'g · hace '+(hace<1?'<1':hace)+'min · ' +
      '<a href="#" onclick="generarRotuloIngreso();return false" style="color:#7c3aed;text-decoration:underline;font-weight:600">🏷 Generar rótulo</a>';
  }catch(e){ box.style.display='none'; }
}

// Sprint Recepciones PRO · 20-may-2026 · fix #11 · auto-save draft del form.
var _ING_DRAFT_TIMER = null;
function _autoSaveIngresoDraft(){
  if(_ING_DRAFT_TIMER) clearTimeout(_ING_DRAFT_TIMER);
  _ING_DRAFT_TIMER = setTimeout(function(){
    try{
      var ids=['ing-cod','ing-inci','ing-nombre','ing-tipo','ing-prov','ing-lote','ing-cant','ing-vence','ing-est','ing-pos','ing-obs','ing-factura','ing-precio-kg'];
      var draft={};
      ids.forEach(function(id){var el=document.getElementById(id); if(el && el.value) draft[id]=el.value;});
      if(Object.keys(draft).length > 0){
        localStorage.setItem('eos_ing_draft', JSON.stringify({d:draft, at:Date.now()}));
      }
    }catch(e){}
  }, 800);
}
function restaurarIngresoDraft(){
  try{
    var saved = localStorage.getItem('eos_ing_draft');
    if(!saved) return;
    var raw = JSON.parse(saved);
    if(!raw || !raw.d) return;
    // Si el draft tiene >2 horas, descartar
    if(Date.now() - (raw.at||0) > 2*60*60*1000){
      localStorage.removeItem('eos_ing_draft'); return;
    }
    if(!confirm('Hay un borrador de ingreso sin enviar de hace '+Math.round((Date.now()-(raw.at||0))/60000)+'min · ¿Restaurarlo?')){
      localStorage.removeItem('eos_ing_draft'); return;
    }
    var draft = raw.d;
    Object.keys(draft).forEach(function(id){
      var el=document.getElementById(id); if(el) el.value=draft[id];
    });
    if(typeof calcularValorTotal==='function') calcularValorTotal();
  }catch(e){}
}
// Engancha auto-save a los inputs cuando el tab carga
function engancharAutoSaveIngreso(){
  var ids=['ing-cod','ing-inci','ing-nombre','ing-tipo','ing-prov','ing-lote','ing-cant','ing-vence','ing-est','ing-pos','ing-obs','ing-factura','ing-precio-kg'];
  ids.forEach(function(id){
    var el=document.getElementById(id);
    if(el && !el._autoSaveBound){
      el._autoSaveBound = true;
      el.addEventListener('input', _autoSaveIngresoDraft);
    }
  });
}
function limpiarIngreso(){
  ['ing-cod','ing-inci','ing-nombre','ing-tipo','ing-prov','ing-lote','ing-cant','ing-vence','ing-est','ing-pos','ing-obs','ing-factura','ing-precio-kg','ing-valor-total'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='';});
  var ocSel=document.getElementById('ing-oc-sel');if(ocSel)ocSel.selectedIndex=0;
  var cuar=document.getElementById('ing-cuarentena');if(cuar)cuar.checked=!window._RECEPCION_AUTO_VIGENTE;  // INVIMA: cuarentena-first por defecto (13-jun) · salvo interruptor auto-VIGENTE (16-jun)
  ocultarFormNuevaMP();
  var st=document.getElementById('ing-status');if(st){st.textContent='';st.style.color='#667eea';}
  document.getElementById('ing-msg').innerHTML='';
}
// Sprint Recepciones PRO · 20-may-2026 · estado paginado + búsqueda
var _ING_HIST_STATE = {limit: 25, offset: 0, q: '', total: 0};
async function cargarHistIngreso(reset){
  if(reset){ _ING_HIST_STATE.offset = 0; }
  try{
    var qs = 'limit='+_ING_HIST_STATE.limit+'&offset='+_ING_HIST_STATE.offset+
             (_ING_HIST_STATE.q?'&q='+encodeURIComponent(_ING_HIST_STATE.q):'');
    var r = await fetch('/api/recepcion/recientes?'+qs);
    if(!r.ok) return;
    var d = await r.json();
    _ING_HIST_STATE.total = d.total || 0;
    var items = d.items || [];
    var tb = document.querySelector('#ing-hist tbody'); if(!tb) return;
    if(!items.length){
      tb.innerHTML='<tr><td colspan="10" style="text-align:center;color:#999;padding:18px;">Sin entradas'+(_ING_HIST_STATE.q?' que coincidan con "'+_escHTML(_ING_HIST_STATE.q)+'"':'')+'</td></tr>';
      _refreshHistPager(); return;
    }
    var esAdmin = window._ES_ADMIN_DASH === true;
    tb.innerHTML = items.map(function(m){
      var fec = (m.fecha||'').substring(0,16).replace('T',' ');
      var venc = m.fecha_vencimiento ? m.fecha_vencimiento.substring(0,10) : '';
      var ocLink = m.numero_oc ? '<a href="/oc/'+encodeURIComponent(m.numero_oc)+'" target="_blank" style="color:#7c3aed;font-family:monospace">'+_escHTML(m.numero_oc)+'</a>' : '<span style="color:#cbd5e1">—</span>';
      var cuarTag = (m.estado_lote==='CUARENTENA') ? '<span style="background:#fef3c7;color:#92400e;padding:1px 6px;border-radius:8px;font-size:9px;font-weight:700;margin-left:4px">🔒 CUAR</span>' : '';
      var anulado = (m.estado_lote==='ANULADO') ? 'opacity:.5;text-decoration:line-through;' : '';
      var anularBtn = (esAdmin && m.estado_lote!=='ANULADO') ?
        '<button onclick="anularRecepcion('+m.id+')" style="padding:2px 6px;font-size:0.7em;background:#dc2626;color:#fff;border-radius:3px" title="Anular esta entrada">×</button>' : '';
      return '<tr style="'+anulado+'">' +
        '<td style="font-family:monospace;font-size:0.85em">'+_escHTML(m.material_id)+'</td>'+
        '<td style="font-size:0.8em;color:#444">'+_escHTML(m.nombre_inci)+'</td>'+
        '<td>'+_escHTML(m.material_nombre)+cuarTag+'</td>'+
        '<td style="font-family:monospace">'+_escHTML(m.lote)+'</td>'+
        '<td style="text-align:right;font-weight:600">'+m.cantidad_g.toLocaleString()+'</td>'+
        '<td style="font-size:0.85em">'+_escHTML(m.proveedor)+'</td>'+
        '<td>'+ocLink+'</td>'+
        '<td style="color:#c0392b;font-size:0.85em">'+_escHTML(venc)+'</td>'+
        '<td style="font-size:0.82em;color:#888">'+_escHTML(fec)+'</td>'+
        '<td style="text-align:center">'+anularBtn+'</td></tr>';
    }).join('');
    _refreshHistPager();
  }catch(e){ console.warn('cargarHistIngreso:', e); }
}
function _refreshHistPager(){
  var box = document.getElementById('ing-hist-pager');
  if(!box) return;
  var s = _ING_HIST_STATE;
  var hasta = Math.min(s.offset + s.limit, s.total);
  var hayMas = s.offset + s.limit < s.total;
  box.innerHTML =
    '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12px;color:#475569;margin-top:8px">' +
    '<span>Mostrando '+(s.offset+1)+'-'+hasta+' de '+s.total+'</span>' +
    '<button onclick="histAvanzar(-1)" '+(s.offset===0?'disabled':'')+' style="padding:3px 10px;font-size:11px">‹ Atrás</button>' +
    '<button onclick="histAvanzar(1)" '+(!hayMas?'disabled':'')+' style="padding:3px 10px;font-size:11px">Siguiente ›</button>' +
    '</div>';
}
function histAvanzar(dir){
  _ING_HIST_STATE.offset = Math.max(0, _ING_HIST_STATE.offset + dir * _ING_HIST_STATE.limit);
  cargarHistIngreso();
}
var _HIST_BUSC_TIMER = null;
function histBuscar(val){
  if(_HIST_BUSC_TIMER) clearTimeout(_HIST_BUSC_TIMER);
  _HIST_BUSC_TIMER = setTimeout(function(){
    _ING_HIST_STATE.q = (val||'').trim();
    _ING_HIST_STATE.offset = 0;
    cargarHistIngreso();
  }, 220);
}
// Sprint Recepciones PRO fix #8: anular recepción (admin)
async function anularRecepcion(mov_id){
  var motivo = prompt('Motivo de anulación (≥10 chars) · esto NO borra el movimiento original, crea un Salida inverso con audit:');
  if(motivo === null) return;
  motivo = motivo.trim();
  if(motivo.length < 10){ alert('Motivo demasiado corto (mín 10 chars)'); return; }
  try{
    var r = await fetch('/api/recepcion/'+mov_id+'/anular', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({motivo: motivo}),
    });
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    alert('✓ '+d.mensaje);
    cargarHistIngreso();
    if(typeof loadStock==='function') loadStock();
  }catch(e){ alert('Error red: '+e.message); }
}
function abrirRotulos(){
  var prod=document.getElementById('prod-sel')?document.getElementById('prod-sel').value:'';
  var manual=document.getElementById('prod-manual')?document.getElementById('prod-manual').value.trim():'';
  var producto=prod||manual;
  var kg=parseFloat(document.getElementById('prod-kg')?document.getElementById('prod-kg').value:0)||0;
  if(!producto){alert('Selecciona un producto primero');return;}
  if(kg<=0){alert('Ingresa la cantidad en kg');return;}
  window.open('/rotulos/'+encodeURIComponent(producto)+'/'+(parseFloat(kg)||0).toFixed(1),'_blank');
}

// Sprint Fórmulas PRO · 20-may-2026
function _formulasPinPersistido(){
  try{ return localStorage.getItem('eos_formulas_pin_ok') === '1'; }catch(_){ return false; }
}
function _setFormulasPinPersistido(ok){
  try{
    if(ok) localStorage.setItem('eos_formulas_pin_ok','1');
    else localStorage.removeItem('eos_formulas_pin_ok');
  }catch(_){}
}
// Init: si ya desbloqueó antes en esta máquina, mantenerlo (TTL implícito
// por la sesión del navegador)
if(typeof formulasPin !== 'undefined') formulasPin = _formulasPinPersistido();

function filtrarFormulas(q){
  q = (q||'').trim().toLowerCase();
  if(!q){ renderFormulas(fData); return; }
  var f = fData.filter(function(x){
    return (x.producto_nombre||'').toLowerCase().indexOf(q) >= 0;
  });
  renderFormulas(f);
}

async function cambiarFormulaPin(){
  // Helper CSRF · usa el patrón del dashboard
  function _csrfTokFP(){
    try{
      if(typeof csrfTokenNec === 'function') return csrfTokenNec();
      var m = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/);
      return m ? decodeURIComponent(m[1]) : (window._csrfTok || '');
    }catch(_){ return window._csrfTok || ''; }
  }
  try{
    // GET info (sin CSRF · es GET)
    var rInfo = await fetch('/api/admin/formulas/pin', {credentials:'same-origin'});
    var dInfo = null;
    try{ dInfo = await rInfo.json(); }catch(_){}
    if(rInfo.status === 401){
      alert('Sesión expirada · iniciá sesión de nuevo y reintentá');
      return;
    }
    if(rInfo.status === 403){
      var msg403 = (dInfo && dInfo.error) ? dInfo.error : 'No autorizado';
      alert('Solo admin puede cambiar el PIN · ' + msg403);
      return;
    }
    if(!rInfo.ok){
      var errTxt = (dInfo && dInfo.error) ? dInfo.error : ('HTTP ' + rInfo.status);
      alert('Error consultando PIN (HTTP ' + rInfo.status + '): ' + errTxt + '\n\nReporta este texto a soporte si persiste.');
      return;
    }
    var info = dInfo || {};
    var origen = info.configurado_en_bd ? ('BD · último cambio por ' + (info.cambiado_por||'?'))
                : (info.configurado_en_env ? 'env var FORMULA_PIN (Render)'
                : (info.es_pin_random_efimero ? 'PIN aleatorio efímero (NADIE lo conoce)' : 'desconocido'));
    var msg = 'PIN actual: ' + origen + '\n\nNuevo PIN (≥4 chars, máx 32):';
    var nuevo = prompt(msg);
    if(!nuevo) return;
    nuevo = nuevo.trim();
    if(nuevo.length < 4){ alert('PIN debe tener ≥4 chars'); return; }
    if(nuevo.length > 32){ alert('PIN máximo 32 chars'); return; }
    var r = await fetch('/api/admin/formulas/pin', {
      method: 'POST',
      headers: {
        'Content-Type':'application/json',
        'X-CSRF-Token': _csrfTokFP(),
      },
      credentials: 'same-origin',
      body: JSON.stringify({nuevo_pin: nuevo}),
    });
    var d = null;
    try{ d = await r.json(); }catch(_){ d = {error: 'respuesta no-JSON · HTTP ' + r.status}; }
    if(!r.ok){
      alert('No se cambió el PIN · ' + (d && d.error ? d.error : ('HTTP ' + r.status)));
      return;
    }
    alert('✓ PIN actualizado · ahora "' + nuevo + '" desbloquea las fórmulas. Guardalo bien.');
    // Auto-desbloquear con el nuevo PIN
    try{
      var rUn = await fetch('/api/formulas/unlock', {
        method:'POST',
        headers:{'Content-Type':'application/json','X-CSRF-Token': _csrfTokFP()},
        credentials:'same-origin',
        body: JSON.stringify({pin: nuevo}),
      });
      if(rUn.ok){ formulasPin = true; _setFormulasPinPersistido(true); renderFormulas(fData); }
    }catch(_){}
  }catch(e){ alert('Error de red: ' + (e && e.message ? e.message : e)); }
}

async function abrirBasesFormulas(){
  try{
    var r = await fetch('/api/formulas/bases-stats', {credentials:'same-origin'});
    if(!r.ok){ alert('Error: HTTP ' + r.status); return; }
    var d = await r.json();
    var grupos = d.grupos || [];
    var existe = document.getElementById('modal-bases-form');
    if(existe) existe.remove();
    var html = '<div id="modal-bases-form" style="position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px">';
    html += '<div style="background:#fff;border-radius:14px;padding:24px;max-width:780px;width:100%;max-height:90vh;overflow-y:auto">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><h3 style="margin:0;color:#7c3aed">📊 Distribución de bases de fórmulas</h3>';
    html += '<button id="bases-close-btn" style="background:none;border:none;font-size:1.4em;cursor:pointer">×</button></div>';
    var color = d.es_uniforme ? '#16a34a' : '#ca8a04';
    html += '<div style="background:#f0f9ff;border:1px solid '+color+';border-radius:8px;padding:10px 14px;margin-bottom:14px;color:#7c3aed;font-size:13px"><b>'+_escHTML(d.mensaje||'')+'</b><br>Total fórmulas: '+(d.total_formulas||0)+'</div>';
    if(grupos.length){
      html += '<table class="table" style="font-size:12px"><thead><tr><th>Base (g)</th><th>Cantidad</th><th>Productos (primeros 5)</th></tr></thead><tbody>';
      grupos.forEach(function(g){
        var dominante = (d.base_dominante_g === g.unidad_base_g);
        var rowStyle = dominante ? 'background:#dcfce7' : '';
        var prods = (g.productos||[]).slice(0,5).join(', ');
        if((g.productos||[]).length > 5) prods += ' …+' + (g.productos.length - 5);
        html += '<tr style="'+rowStyle+'"><td><b>'+g.unidad_base_g+' g</b>'+(dominante?' <span style="color:#16a34a;font-size:10px">(dominante)</span>':'')+'</td>';
        html += '<td>'+g.count+'</td><td style="font-size:11px;color:#475569">'+_escHTML(prods)+'</td></tr>';
      });
      html += '</tbody></table>';
    }
    html += '<div style="margin-top:14px;border-top:1px solid #e2e8f0;padding-top:14px">';
    html += '<h4 style="margin:0 0 8px;color:#7c3aed">🔧 Normalizar todas a una base común (admin)</h4>';
    html += '<div style="background:#fef3c7;border:1px solid #ca8a04;border-radius:6px;padding:10px 12px;margin-bottom:10px;font-size:11px;color:#78350f">';
    html += '<b>Por qué 100g es el estándar cosmético:</b><br>';
    html += '• Los % de la fórmula suman 100% · base 100g = "% es exactamente igual a g"<br>';
    html += '• Ejemplo: si Vit C es 10%, en base 100g leés "10g de Vit C" directamente<br>';
    html += '• Los descuentos REALES al producir NO cambian (siempre usan % × kg pedidos)';
    html += '</div>';
    html += '<p style="font-size:11px;color:#475569;margin:0 0 8px">Los porcentajes NO se tocan · solo cambia el lote nominal mostrado.</p>';
    html += '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">';
    html += '<label style="font-size:12px;color:#475569">Base nueva (g):</label>';
    html += '<input id="bases-nuevo-input" type="number" value="100" min="50" max="100000" step="50" style="width:120px;padding:6px 10px;border:1px solid #cbd5e1;border-radius:5px">';
    html += '<button id="bases-aplicar-btn" style="background:#7c3aed;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-weight:700;cursor:pointer">⚙ Normalizar TODAS a esta base</button>';
    html += '</div></div>';
    html += '</div></div>';
    var div = document.createElement('div');
    div.innerHTML = html;
    document.body.appendChild(div.firstChild);
    document.getElementById('bases-close-btn').onclick = function(){
      var m = document.getElementById('modal-bases-form'); if(m) m.remove();
    };
    var btnAplicar = document.getElementById('bases-aplicar-btn');
    if(btnAplicar){
      btnAplicar.onclick = async function(){
        var base = parseFloat(document.getElementById('bases-nuevo-input').value);
        if(!base || base < 50 || base > 100000){ alert('Base debe ser 50-100000'); return; }
        if(!confirm('Normalizar TODAS las fórmulas a base ' + base + 'g? Los % se mantienen.')) return;
        var _csrf = (typeof csrfTokenNec === 'function') ? csrfTokenNec() : (window._csrfTok || '');
        var r2 = await fetch('/api/formulas/normalizar-base', {
          method:'POST', credentials:'same-origin',
          headers:{'Content-Type':'application/json','X-CSRF-Token':_csrf},
          body: JSON.stringify({base_g: base}),
        });
        var d2 = await r2.json();
        if(!r2.ok){ alert('Error: ' + (d2.error||r2.status)); return; }
        alert('✓ ' + d2.mensaje);
        var m = document.getElementById('modal-bases-form'); if(m) m.remove();
        await loadFormulas();
      };
    }
  }catch(e){ alert('Error red: ' + e.message); }
}

function abrirImportExcelFormulas(){
  var modal = document.getElementById('modal-import-formulas');
  if(!modal){
    // Crear modal lazy
    var m = document.createElement('div');
    m.id = 'modal-import-formulas';
    m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px';
    m.innerHTML =
      '<div style="background:#fff;border-radius:14px;padding:24px;max-width:720px;width:100%;max-height:90vh;overflow-y:auto">'+
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><h3 style="margin:0;color:#7c3aed">📤 Importar fórmulas desde Excel</h3>'+
      '<button id="imp-form-close-btn" style="background:none;border:none;font-size:1.3em;cursor:pointer">×</button></div>'+
      '<div style="background:#f0f9ff;border:1px solid #7c3aed;border-radius:8px;padding:12px;margin-bottom:14px;font-size:12px;color:#7c3aed">'+
      '<b>Formato requerido</b> · 1 fila por ingrediente:<br>'+
      'Columnas obligatorias: <code>producto</code>, <code>codigo_mp</code>, <code>porcentaje</code><br>'+
      'Columnas opcionales: <code>nombre_mp</code>, <code>unidad_base_g</code>, <code>descripcion</code><br>'+
      '<a href="/api/formulas/export-excel" target="_blank" style="color:#7c3aed;font-weight:700">📥 Descargar plantilla (export actual)</a>'+
      '</div>'+
      '<input type="file" id="imp-form-file" accept=".xlsx,.csv" style="margin-bottom:14px">'+
      '<div style="display:flex;gap:8px;margin-bottom:14px">'+
      '<button onclick="impFormulasPreview()" style="background:#7c3aed;color:#fff;padding:8px 16px;border:none;border-radius:6px;cursor:pointer;font-weight:700">🔍 Preview (dry-run)</button>'+
      '<button onclick="impFormulasApply()" id="imp-form-apply" style="background:#7c3aed;color:#fff;padding:8px 16px;border:none;border-radius:6px;cursor:pointer;font-weight:700" disabled>💾 Aplicar import</button>'+
      '</div>'+
      '<div id="imp-form-msg" style="font-size:12px"></div>'+
      '</div>';
    document.body.appendChild(m);
    var cb = document.getElementById('imp-form-close-btn');
    if(cb) cb.onclick = function(){
      var x = document.getElementById('modal-import-formulas');
      if(x) x.remove();
    };
  } else {
    modal.style.display = 'flex';
  }
}
async function impFormulasPreview(){
  var fp = document.getElementById('imp-form-file');
  var msg = document.getElementById('imp-form-msg');
  if(!fp.files.length){ msg.innerHTML = '<span style="color:#dc2626">Elegí un archivo</span>'; return; }
  var fd = new FormData();
  fd.append('file', fp.files[0]);
  msg.innerHTML = '<span style="color:#94a3b8">Analizando…</span>';
  var _csrf = (typeof csrfTokenNec === 'function') ? csrfTokenNec() : (window._csrfTok || '');
  try{
    var r = await fetch('/api/formulas/import-excel?dry_run=1', {
      method:'POST', body:fd, credentials:'same-origin',
      headers: {'X-CSRF-Token': _csrf},
    });
    var d = await r.json();
    if(!r.ok){
      msg.innerHTML = '<div style="color:#dc2626;font-weight:700">Error: '+_escHTML(d.error||r.status)+'</div>'+
        (d.headers_detectados ? '<div style="font-size:11px;color:#64748b;margin-top:4px">Headers detectados: '+_escHTML(JSON.stringify(d.headers_detectados))+'</div>' : '')+
        (d.hint ? '<div style="font-size:11px;color:#475569;margin-top:4px">'+_escHTML(d.hint)+'</div>' : '');
      return;
    }
    var html = '<div style="background:#ecfdf5;border:1px solid #16a34a;color:#065f46;padding:10px;border-radius:6px;margin-bottom:10px"><b>'+(d.formulas_detectadas||0)+' fórmulas detectadas</b> · '+(d.errores_filas?d.errores_filas.length:0)+' filas con error</div>';
    if((d.plan||[]).length){
      html += '<table class="table" style="font-size:11px"><thead><tr><th>Producto</th><th>Base g</th><th>Items</th><th>Total %</th><th>Existe?</th><th>MPs faltantes</th></tr></thead><tbody>';
      d.plan.forEach(function(p){
        var rowCol = (!p.pct_ok || p.mps_faltantes.length) ? 'background:#fef3c7' : '';
        html += '<tr style="'+rowCol+'">';
        html += '<td><b>'+_escHTML(p.producto)+'</b></td><td>'+p.unidad_base_g+'</td>';
        html += '<td>'+p.items_count+'</td><td style="color:'+(p.pct_ok?'#16a34a':'#dc2626')+'">'+p.total_pct+'%</td>';
        html += '<td>'+(p.ya_existe?'✓ Actualiza':'+ Nueva')+'</td>';
        html += '<td style="color:#dc2626">'+(p.mps_faltantes.length?p.mps_faltantes.join(', '):'—')+'</td>';
        html += '</tr>';
      });
      html += '</tbody></table>';
    }
    if((d.errores_filas||[]).length){
      html += '<div style="margin-top:10px;background:#fee2e2;padding:8px;border-radius:6px;font-size:11px;color:#991b1b"><b>Errores fila:</b><br>'+
        d.errores_filas.slice(0,10).map(function(e){return 'Fila '+e.fila+': '+_escHTML(e.razon);}).join('<br>')+
        '</div>';
    }
    msg.innerHTML = html;
    document.getElementById('imp-form-apply').disabled = !(d.formulas_detectadas > 0);
  }catch(e){ msg.innerHTML = '<span style="color:#dc2626">Error red: '+_escHTML(e.message)+'</span>'; }
}
async function impFormulasApply(){
  var fp = document.getElementById('imp-form-file');
  var msg = document.getElementById('imp-form-msg');
  if(!fp.files.length){ msg.innerHTML = '<span style="color:#dc2626">Elegí archivo</span>'; return; }
  if(!confirm('Aplicar import? Las fórmulas existentes se ACTUALIZAN (versión anterior queda archivada).')) return;
  var fd = new FormData();
  fd.append('file', fp.files[0]);
  msg.innerHTML = '<span style="color:#94a3b8">Aplicando…</span>';
  var _csrf = (typeof csrfTokenNec === 'function') ? csrfTokenNec() : (window._csrfTok || '');
  try{
    var r = await fetch('/api/formulas/import-excel', {
      method:'POST', body:fd, credentials:'same-origin',
      headers: {'X-CSRF-Token': _csrf},
    });
    var d = await r.json();
    if(!r.ok){ msg.innerHTML = '<div style="color:#dc2626">Error: '+_escHTML(d.error||r.status)+'</div>'; return; }
    msg.innerHTML = '<div style="background:#dcfce7;color:#166534;padding:10px;border-radius:6px;font-weight:700">✓ '+_escHTML(d.mensaje)+'</div>'+
      ((d.rechazadas||[]).length ? '<div style="margin-top:8px;background:#fee2e2;color:#991b1b;padding:8px;border-radius:6px;font-size:11px"><b>Rechazadas:</b><br>'+d.rechazadas.map(function(r){return _escHTML(r.producto)+': '+_escHTML(r.razon);}).join('<br>')+'</div>' : '');
    await loadFormulas();
  }catch(e){ msg.innerHTML = '<span style="color:#dc2626">Error red: '+_escHTML(e.message)+'</span>'; }
}

async function loadFormulas(){
  try{
    var r=await fetch('/api/formulas'), d=await r.json();
    fData=d.formulas||[];
    renderFormulas(fData);
    var sel=document.getElementById('prod-sel');
    if(sel){
      var cur=sel.value;
      sel.innerHTML='<option value="">-- Selecciona un producto --</option>';
      fData.forEach(function(f){var o=document.createElement('option');o.value=f.producto_nombre;o.textContent=f.producto_nombre;sel.appendChild(o);});
      sel.value=cur;
    }
  }catch(e){}
}

function toggleFormula(idx){
  var b=document.getElementById('fbody-'+idx), ch=document.getElementById('fchev-'+idx);
  if(!b) return;
  var abierto = b.style.display!=='none';
  b.style.display = abierto ? 'none' : 'block';
  if(ch) ch.innerHTML = abierto ? '&#9654;' : '&#9660;';
}
function renderFormulas(fl){
  var c=document.getElementById('formulas-list'); if(!c) return;
  if(!fl.length){c.innerHTML='<p style="color:#999;">Sin formulas aun.</p>';return;}
  var html='';
  if(!formulasPin){
    html+='<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:6px;padding:10px 15px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:center;">'
         +'<span>&#128274; Cantidades ocultas &mdash; activa el PIN para ver la f&oacute;rmula completa</span>'
         +'<button onclick="pedirPinFormula()" style="background:#667eea;color:white;border:none;padding:5px 14px;border-radius:4px;cursor:pointer;font-weight:600;font-size:0.85em;">&#128275; Desbloquear</button>'
         +'</div>';
  } else {
    html+='<div style="background:#d4edda;border:1px solid #28a745;border-radius:6px;padding:8px 15px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:center;">'
         +'<span style="color:#155724;">&#128275; F&oacute;rmulas desbloqueadas</span>'
         +'<button onclick="formulasPin=false;renderFormulas(fData)" style="background:#6c757d;color:white;border:none;padding:5px 14px;border-radius:4px;cursor:pointer;font-size:0.85em;">&#128274; Bloquear</button>'
         +'</div>';
  }
  var MASK='<span style="filter:blur(5px);user-select:none;pointer-events:none;color:#555;">&#x2588;&#x2588;.&#x2588;&#x2588;</span>';
  fl.forEach(function(f,idx){
    var total=f.items.reduce(function(s,i){return s+i.porcentaje;},0);
    var ok=Math.abs(total-100)<0.1;
    var rows='';
    // Sprint Fórmulas PRO · 20-may-2026: mostrar "g por base de la fórmula"
    // en vez de "g/kg" hardcoded · si la fórmula está en base 100g (estándar
    // cosmético), el valor es el % directamente. Si está en 1000g, es ×10.
    var baseF = parseFloat(f.unidad_base_g) || 1000;
    f.items.forEach(function(it){
      var pctVal=formulasPin?it.porcentaje+'%':MASK+'%';
      var gPorBase = formulasPin ? (it.porcentaje * baseF / 100).toFixed(2) + 'g' : MASK + 'g';
      var nmF=(it.nombre_inci||it.material_nombre||'')+((it.nombre_inci&&it.material_nombre&&it.nombre_inci!==it.material_nombre)?' <span style="color:#999;font-size:0.85em;">('+it.material_nombre+')</span>':'');
      rows+='<tr><td style="font-family:monospace;">'+it.material_id+'</td><td>'+nmF+'</td><td>'+pctVal+'</td><td style="font-weight:600;">'+gPorBase+'</td></tr>';
    });
    var unidadCol = 'g por ' + baseF + 'g';
    var totalStr=formulasPin?total.toFixed(2)+'%'+(ok?' OK':' revisar'):MASK+'%';
    var editBtn=formulasPin
      ?'<button onclick="editFormula('+idx+')" style="background:#667eea;padding:5px 10px;font-size:0.82em;">Editar</button>'
      :'<button onclick="pedirPinFormula()" style="background:#aaa;color:white;border:none;padding:5px 10px;font-size:0.82em;border-radius:3px;cursor:pointer;" title="Requiere PIN">&#128274; Editar</button>';
    html+='<div style="border:1px solid #dde;border-radius:8px;margin-bottom:10px;background:white;overflow:hidden;">';
    // Cabecera CLICKEABLE · colapsa/expande la tabla (lista compacta)
    html+='<div onclick="toggleFormula('+idx+')" style="display:flex;justify-content:space-between;align-items:center;padding:12px 15px;cursor:pointer;gap:8px;">';
    html+='<h4 style="color:#667eea;margin:0;display:flex;align-items:center;gap:9px;"><span id="fchev-'+idx+'" style="font-size:0.75em;color:#999;transition:transform .12s;">&#9654;</span>'+f.producto_nombre+' <span style="font-weight:normal;color:#888;font-size:0.82em;">(base '+f.unidad_base_g+'g · '+f.items.length+' MP)</span></h4>';
    html+='<div style="display:flex;gap:6px;" onclick="event.stopPropagation();">'+editBtn;
    html+='<button data-form-act="duplicar" data-prod="'+_escHTML(f.producto_nombre)+'" style="background:#7c3aed;padding:5px 10px;font-size:0.82em;" title="Crear copia con nuevo nombre">Duplicar</button>';
    html+='<button onclick="delFormula('+idx+')" style="background:#cc4444;padding:5px 10px;font-size:0.82em;">Eliminar</button>';
    html+='</div></div>';
    // Cuerpo colapsable (oculto por defecto)
    html+='<div id="fbody-'+idx+'" style="display:none;padding:0 15px 14px;">';
    html+='<table class="table" style="font-size:0.85em;"><thead><tr><th>Código MP</th><th>Material</th><th>%</th><th>'+_escHTML(unidadCol)+'</th></tr></thead><tbody>'+rows+'</tbody></table>';
    html+='<small style="color:'+(ok?'#28a745':'#e68a00')+';"> '+totalStr+'</small>';
    html+='</div>';
    html+='</div>';
  });
  c.innerHTML=html;
}

async function pedirPinFormula(){
  var pin=prompt('PIN de acceso a fórmulas (admin puede cambiarlo con botón PIN):');
  if(!pin) return;
  try{
    var r=await fetch('/api/formulas/unlock',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin:pin})});
    if(r.ok){
      formulasPin=true;
      if(typeof _setFormulasPinPersistido==='function') _setFormulasPinPersistido(true);
      renderFormulas(fData);
    }
    else{alert('PIN incorrecto · si lo olvidaste, pedíselo a Sebastián / Alejandro o usá el botón PIN para resetear');}
  }catch(e){alert('Error al verificar PIN');}
}
if(typeof document !== 'undefined' && !window._FORMULAS_DELEG){
  window._FORMULAS_DELEG = true;
  document.addEventListener('click', function(ev){
    var btn = ev.target && ev.target.closest && ev.target.closest('[data-form-act="duplicar"]');
    if(!btn) return;
    var prod = btn.getAttribute('data-prod') || '';
    if(prod) duplicarFormula(prod);
  });
}
async function duplicarFormula(prod){
  if(!formulasPin){ pedirPinFormula(); return; }
  var nuevo = prompt('Duplicar "'+prod+'" como nueva fórmula. Nombre nuevo:');
  if(!nuevo) return;
  nuevo = nuevo.trim();
  if(!nuevo) return;
  var _csrf = (typeof csrfTokenNec === 'function') ? csrfTokenNec() : (window._csrfTok || '');
  try{
    var r = await fetch('/api/formulas/duplicar', {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json', 'X-CSRF-Token': _csrf},
      body: JSON.stringify({producto_origen: prod, producto_nuevo: nuevo}),
    });
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    alert('Duplicado: '+d.mensaje+' · '+d.items_count+' items copiados');
    await loadFormulas();
  }catch(e){ alert('Error red: '+e.message); }
}

function addFRow(){
  var div=document.createElement('div');
  div.style.cssText='display:grid;grid-template-columns:140px 1fr 90px 38px;gap:6px;margin-bottom:6px;';
  div.innerHTML='<input type="text" placeholder="MP00001" class="fi-id" style="padding:7px;border:1px solid #ddd;border-radius:5px;">'
    +'<input type="text" placeholder="Nombre material" class="fi-nm" style="padding:7px;border:1px solid #ddd;border-radius:5px;">'
    +'<input type="number" placeholder="%" step="0.001" class="fi-pc" style="padding:7px;border:1px solid #ddd;border-radius:5px;" oninput="calcPct()">'
    +'<button onclick="this.parentElement.remove();calcPct();" style="background:#ff4444;color:white;border:none;border-radius:5px;cursor:pointer;padding:7px;font-size:0.9em;">x</button>';
  document.getElementById('fi-container').appendChild(div);
}

function calcPct(){
  var t=Array.from(document.querySelectorAll('.fi-pc')).reduce(function(s,i){return s+(parseFloat(i.value)||0);},0);
  var el=document.getElementById('pct-total');
  el.textContent='Total: '+t.toFixed(2)+'%';
  el.style.color=Math.abs(t-100)<0.1?'#28a745':(t>100?'#cc0000':'#e68a00');
}

async function guardarFormula(){
  var prod=document.getElementById('formula-producto').value.trim();
  if(!prod){alert('Ingresa el nombre del producto');return;}
  var base=parseFloat(document.getElementById('formula-base').value)||1000;
  var desc=document.getElementById('formula-desc').value.trim();
  var rows=document.querySelectorAll('#fi-container > div');
  var items=[];
  rows.forEach(function(row){
    var id=row.querySelector('.fi-id').value.trim();
    var nm=row.querySelector('.fi-nm').value.trim();
    var pc=parseFloat(row.querySelector('.fi-pc').value)||0;
    if(id&&nm&&pc>0) items.push({material_id:id,material_nombre:nm,porcentaje:pc});
  });
  if(!items.length){alert('Agrega al menos un ingrediente');return;}
  // Sebastián 12-may-2026: bug critico · antes mostraba "alert-success" siempre
  // aunque el POST devolviera 400 (FK violation por material_id sin registrar
  // en maestro_mps activo, etc). Luis Enrique creía que guardaba pero la BD
  // nunca recibía el INSERT. Ahora chequea r.ok y muestra error real.
  await _postFormula(prod,base,desc,items,false);
}

async function _postFormula(prod,base,desc,items,forzar){
  try{
    var r=await fetch('/api/formulas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({producto_nombre:prod,unidad_base_g:base,descripcion:desc,items:items,forzar_mismatch:!!forzar})});
    var res=await r.json();
    // 409 · el nombre de una línea no coincide con su código (mapeo cruzado)
    if(r.status===409 && res.mismatches){
      var det='<div class="alert-error"><b>&#x26A0; El nombre no coincide con el código</b>';
      det+='<div style="margin-top:6px;font-size:12px;">'+_escHTML(res.detalle||'')+'</div><ul style="margin:8px 0 0 0;padding-left:18px;font-size:12px;">';
      res.mismatches.forEach(function(m){
        det+='<li style="margin-bottom:4px"><b>'+_escHTML(m.material_nombre)+'</b> tiene el código <span style="font-family:monospace">'+_escHTML(m.material_id)+'</span>, que en el catálogo es <b>'+_escHTML(m.codigo_es_en_catalogo||'?')+'</b>.';
        if(m.codigo_sugerido){ det+=' &#x2192; ¿Querías <span style="font-family:monospace">'+_escHTML(m.codigo_sugerido)+'</span> ('+_escHTML(m.nombre_sugerido||'')+')?'; }
        det+='</li>';
      });
      det+='</ul><div style="margin-top:10px"><button onclick="_forzarFormula()" style="background:#b45309;color:#fff;border:none;padding:7px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">Guardar de todos modos (forzar)</button> <span style="font-size:11px;color:#7f1d1d">Solo si estás 100% seguro del código.</span></div></div>';
      document.getElementById('formula-msg').innerHTML=det;
      window.__formForzar={prod:prod,base:base,desc:desc,items:items};
      return;
    }
    if(!r.ok){
      var msg='<div class="alert-error"><b>&#x274C; No se guardó la fórmula</b>';
      msg+='<div style="margin-top:6px;font-size:13px;">'+_escHTML(res.error||'Error desconocido')+'</div>';
      if(res.detalle){ msg+='<div style="margin-top:4px;font-size:12px;color:#7f1d1d;">'+_escHTML(res.detalle)+'</div>'; }
      if(res.material_id_invalido){
        msg+='<div style="margin-top:8px;font-size:12px;color:#7f1d1d;">';
        msg+='&#x2192; MP <b>'+_escHTML(res.material_id_invalido)+'</b> no existe en el catálogo o está inactiva.';
        msg+='Crea la MP primero en <b>Bodega MP</b> antes de usarla en una fórmula.</div>';
      }
      msg+='</div>';
      document.getElementById('formula-msg').innerHTML=msg;
      alert('❌ No se guardó la fórmula:\n\n'+(res.error||'')+(res.detalle?'\n\n'+res.detalle:''));
      return;
    }
    document.getElementById('formula-msg').innerHTML='<div class="alert-success">&#x2705; '+_escHTML(res.message||'Fórmula guardada')+'</div>';
    await loadFormulas();
    setTimeout(function(){document.getElementById('formula-msg').innerHTML='';},3000);
  }catch(e){document.getElementById('formula-msg').innerHTML='<div class="alert-error">Error red: '+_escHTML(e.message)+'</div>';}
}

async function _forzarFormula(){
  var f=window.__formForzar; if(!f) return;
  if(!confirm('Vas a guardar con códigos que NO coinciden con el nombre del ingrediente. Esto puede cruzar el stock al producir. ¿Estás 100% seguro?')) return;
  await _postFormula(f.prod,f.base,f.desc,f.items,true);
}

function editFormula(idx){
  if(!formulasPin){pedirPinFormula();return;}
  var f=fData[idx]; if(!f) return;
  document.getElementById('formula-producto').value=f.producto_nombre;
  document.getElementById('formula-base').value=f.unidad_base_g;
  document.getElementById('formula-desc').value=f.descripcion||'';
  document.getElementById('fi-container').innerHTML='';
  f.items.forEach(function(item){
    addFRow();
    var rows=document.getElementById('fi-container').querySelectorAll('div');
    var row=rows[rows.length-1];
    row.querySelector('.fi-id').value=item.material_id;
    row.querySelector('.fi-nm').value=item.material_nombre;
    row.querySelector('.fi-pc').value=item.porcentaje;
  });
  calcPct();
  mbrCargar(f.producto_nombre);   // integración MyBatch · cargar procedimiento+IPC
  document.getElementById('formula-producto').scrollIntoView({behavior:'smooth'});
}

// ── Integración MyBatch · paso 1 · Procedimiento + IPC del MBR en el editor ──
function _mbrCsrf(){ try{ var m=(window._csrfTok||''); return m; }catch(_){ return ''; } }
async function _mbrEnsureCsrf(){ if(!window._csrfTok){ try{ var r=await fetch('/api/csrf-token',{credentials:'same-origin'}); if(r.ok){ var d=await r.json(); window._csrfTok=d.csrf_token||''; } }catch(_){ } } }
function mbrAddPaso(fase, desc, registrar){
  var div=document.createElement('div');
  div.style.cssText='display:grid;grid-template-columns:90px 1fr 150px 38px;gap:6px;margin-bottom:6px;align-items:start';
  div.innerHTML='<input type="text" class="mbr-fase" value="'+_escHTML(fase||'Fabricación')+'" style="padding:6px;border:1px solid #ddd;border-radius:5px;font-size:12px">'
    +'<textarea class="mbr-desc" rows="2" placeholder="Ej: Premezcla 1: 90% agua + niacinamida, agitar a 65°C" style="padding:6px;border:1px solid #ddd;border-radius:5px;font-size:12px;resize:vertical">'+_escHTML(desc||'')+'</textarea>'
    +'<input type="text" class="mbr-reg" value="'+_escHTML(registrar||'')+'" placeholder="temperatura / RPM" style="padding:6px;border:1px solid #ddd;border-radius:5px;font-size:12px">'
    +'<button onclick="this.parentElement.remove()" style="background:#ef4444;color:#fff;border:none;border-radius:5px;cursor:pointer;padding:6px;font-size:.9em">x</button>';
  document.getElementById('mbr-pasos').appendChild(div);
}
function mbrAddIpc(par, uni, vmin, vmax, texto){
  var div=document.createElement('div');
  div.style.cssText='display:grid;grid-template-columns:1fr 80px 70px 70px 1fr 38px;gap:6px;margin-bottom:6px';
  function _v(x){ return (x===null||x===undefined)?'':x; }
  div.innerHTML='<input type="text" class="ipc-par" value="'+_escHTML(par||'')+'" placeholder="pH / Densidad / Color" style="padding:6px;border:1px solid #ddd;border-radius:5px;font-size:12px">'
    +'<input type="text" class="ipc-uni" value="'+_escHTML(uni||'')+'" placeholder="°C, etc" style="padding:6px;border:1px solid #ddd;border-radius:5px;font-size:12px">'
    +'<input type="number" step="any" class="ipc-min" value="'+_v(vmin)+'" style="padding:6px;border:1px solid #ddd;border-radius:5px;font-size:12px">'
    +'<input type="number" step="any" class="ipc-max" value="'+_v(vmax)+'" style="padding:6px;border:1px solid #ddd;border-radius:5px;font-size:12px">'
    +'<input type="text" class="ipc-txt" value="'+_escHTML(texto||'')+'" placeholder="Blanco hueso / Líquido viscoso" style="padding:6px;border:1px solid #ddd;border-radius:5px;font-size:12px">'
    +'<button onclick="this.parentElement.remove()" style="background:#ef4444;color:#fff;border:none;border-radius:5px;cursor:pointer;padding:6px;font-size:.9em">x</button>';
  document.getElementById('mbr-ipc').appendChild(div);
}
async function mbrCargar(producto){
  document.getElementById('mbr-pasos').innerHTML='';
  document.getElementById('mbr-ipc').innerHTML='';
  document.getElementById('mbr-msg').innerHTML='';
  document.getElementById('mbr-estado-badge').textContent='';
  if(!producto) return;
  try{
    var r=await fetch('/api/brd/mbr/por-producto?producto='+encodeURIComponent(producto),{credentials:'same-origin'});
    var d=await r.json();
    if(d && d.existe){
      var est=d.estado||''; var col=est==='aprobado'?'#15803d':(est==='en_revision'?'#9a3412':'#64748b');
      document.getElementById('mbr-estado-badge').innerHTML='MBR v'+(d.version||1)+' · <b style="color:'+col+'">'+est+'</b>';
      (d.pasos||[]).forEach(function(p){ mbrAddPaso(p.fase, p.descripcion, p.resultado_label); });
      (d.ipc||[]).forEach(function(s){ mbrAddIpc(s.parametro, s.unidad, s.valor_min, s.valor_max, s.especificacion); });
    } else {
      document.getElementById('mbr-estado-badge').innerHTML='<span style="color:#94a3b8">sin MBR aún · agregá pasos y guardá</span>';
    }
  }catch(e){ document.getElementById('mbr-estado-badge').textContent=''; }
}
function _mbrRecoger(){
  var pasos=[]; document.querySelectorAll('#mbr-pasos > div').forEach(function(row){
    var desc=(row.querySelector('.mbr-desc').value||'').trim();
    if(desc) pasos.push({descripcion:desc, fase:(row.querySelector('.mbr-fase').value||'Fabricación').trim(), resultado_label:(row.querySelector('.mbr-reg').value||'').trim()});
  });
  var ipc=[]; document.querySelectorAll('#mbr-ipc > div').forEach(function(row){
    var par=(row.querySelector('.ipc-par').value||'').trim();
    if(par) ipc.push({parametro:par, unidad:(row.querySelector('.ipc-uni').value||'').trim(), valor_min:row.querySelector('.ipc-min').value, valor_max:row.querySelector('.ipc-max').value, especificacion:(row.querySelector('.ipc-txt').value||'').trim()});
  });
  return {pasos:pasos, ipc:ipc};
}
async function mbrGuardarProcedimiento(){
  var prod=(document.getElementById('formula-producto').value||'').trim();
  if(!prod){ document.getElementById('mbr-msg').innerHTML='<span style="color:#b91c1c">Poné el nombre del producto (y guardá la fórmula primero)</span>'; return; }
  var data=_mbrRecoger();
  if(!data.pasos.length){ document.getElementById('mbr-msg').innerHTML='<span style="color:#b91c1c">Agregá al menos un paso</span>'; return; }
  document.getElementById('mbr-msg').textContent='Guardando…';
  await _mbrEnsureCsrf();
  try{
    var r=await fetch('/api/brd/mbr/sync-procedimiento',{method:'POST',credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':window._csrfTok||''},
      body:JSON.stringify({producto_nombre:prod, pasos:data.pasos, ipc:data.ipc})});
    var d=await r.json();
    if(!r.ok||!d.ok){ document.getElementById('mbr-msg').innerHTML='<span style="color:#b91c1c">Error: '+_escHTML(d.error||r.status)+'</span>'; return; }
    document.getElementById('mbr-msg').innerHTML='<span style="color:#15803d;font-weight:700">✓ '+d.n_pasos+' pasos · '+d.n_ipc+' IPC guardados (MBR draft)</span>';
    window._mbrLastId=d.mbr_id;
  }catch(e){ document.getElementById('mbr-msg').innerHTML='<span style="color:#b91c1c">Error red: '+_escHTML(e.message)+'</span>'; }
}
async function mbrEnviarAprobacion(){
  await mbrGuardarProcedimiento();
  if(!window._mbrLastId){ return; }
  await _mbrEnsureCsrf();
  try{
    var r=await fetch('/api/brd/mbr/'+window._mbrLastId+'/submit',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':window._csrfTok||''}});
    var d=await r.json();
    if(!r.ok||!d.ok){ document.getElementById('mbr-msg').innerHTML='<span style="color:#b91c1c">Error al enviar: '+_escHTML(d.error||r.status)+'</span>'; return; }
    document.getElementById('mbr-msg').innerHTML='<span style="color:#15803d;font-weight:700">✓ Enviado a revisión.</span> <a href="/brd" target="_blank" style="color:#7c3aed;font-weight:700">Aprobar con e-firma en Calidad/BRD →</a>';
  }catch(e){ document.getElementById('mbr-msg').innerHTML='<span style="color:#b91c1c">Error red: '+_escHTML(e.message)+'</span>'; }
}

async function delFormula(idx){
  var nombre=fData[idx]?fData[idx].producto_nombre:'';
  if(!nombre||!confirm('Eliminar formula de '+nombre+'?')) return;
  await fetch('/api/formulas/'+encodeURIComponent(nombre),{method:'DELETE'});
  await loadFormulas();
}

function previewProd(){
  var prod=document.getElementById('prod-sel').value||document.getElementById('prod-manual').value.trim();
  var kg=parseFloat(document.getElementById('prod-kg').value)||0;
  var preview=document.getElementById('prod-preview');
  if(!prod||kg<=0){preview.style.display='none';return;}
  var f=fData.find(function(x){return x.producto_nombre===prod;});
  if(!f||!f.items.length){preview.style.display='none';return;}
  var g=kg*1000;
  document.getElementById('prod-preview-body').innerHTML=f.items.map(function(it){
    return '<tr><td>'+(it.nombre_inci||it.material_nombre||'')+'</td><td style="text-align:right;font-weight:700;">'+((it.porcentaje/100)*g).toFixed(1)+' g</td></tr>';
  }).join('');
  preview.style.display='block';
}

async function registrarProd(){
  var prod=document.getElementById('prod-sel').value||document.getElementById('prod-manual').value.trim();
  if(!prod){alert('Ingresa un producto');return;}
  var kg=parseFloat(document.getElementById('prod-kg').value);
  if(!kg||kg<=0){alert('Ingresa una cantidad valida');return;}
  // Validacion: advertir si la cantidad parece inusualmente alta
  if(kg>1000){
    var msg='⚠️ ADVERTENCIA: Ingresaste '+kg.toLocaleString()+' kg de producción.';
    msg+=' | Equivale a '+(kg*1000).toLocaleString()+' g.';
    msg+=' | Las producciones normales son menores a 1,000 kg. Confirmar?';
    msg+=' | Si querias gramos, divide entre 1000 (ej: 20 kg = ingresa 20).';
    if(!confirm(msg)) return;
  }
  try{
    var _csrf3 = (typeof csrfTokenNec === 'function') ? csrfTokenNec() : (window._csrfTok || '');
    var r=await fetch('/api/produccion',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':_csrf3},body:JSON.stringify({producto:prod,cantidad:kg,observaciones:document.getElementById('prod-obs').value,operador:OPER_ACTUAL})});
    var res=await r.json();
    var html='<div class="alert-success">'+res.message+'</div>';
    if(res.descuentos&&res.descuentos.length){
      html+='<div style="margin-top:8px;font-size:0.88em;color:#555;"><strong>MPs descontadas del inventario:</strong><ul style="margin-top:4px;padding-left:18px;">';
      res.descuentos.forEach(function(d){html+='<li>'+d.material+': '+d.cantidad_g.toLocaleString()+' g</li>';});
      html+='</ul></div>';
    }
    document.getElementById('prod-msg').innerHTML=html;
    document.getElementById('prod-preview').style.display='none';
    setTimeout(function(){
      document.getElementById('prod-sel').value='';
      document.getElementById('prod-manual').value='';
      document.getElementById('prod-kg').value='';
      document.getElementById('prod-obs').value='';
      document.getElementById('prod-msg').innerHTML='';
    },5000);
  }catch(e){document.getElementById('prod-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}

// Sprint ABC PRO · 20-may-2026 · render con stats + gráfico + tabla completa
var _ABC_LAST = null;
async function loadABC(){
  var resBox = document.getElementById('abc-results');
  var statsBox = document.getElementById('abc-stats');
  if(resBox) resBox.innerHTML = '<div style="color:#94a3b8;padding:20px;text-align:center">Calculando…</div>';
  try{
    var modo = (document.getElementById('abc-modo')||{}).value || 'valor';
    var tipo = (document.getElementById('abc-tipo')||{}).value || 'MP';
    var sub = (document.getElementById('abc-subtipo')||{}).value || '';
    var exc = document.getElementById('abc-excluir-cuar') && document.getElementById('abc-excluir-cuar').checked ? '1' : '';
    var qs = 'modo='+encodeURIComponent(modo) + '&tipo_material='+encodeURIComponent(tipo) +
             (sub?'&subtipo='+encodeURIComponent(sub):'') +
             (exc?'&excluir_cuarentena=1':'');
    var r = await fetch('/api/analisis-abc?'+qs);
    if(!r.ok){ resBox.innerHTML='<div class="alert-error">Error '+r.status+'</div>'; return; }
    var d = await r.json();
    _ABC_LAST = d;
    var items = d.items || [];
    // Stats cards
    if(statsBox){
      statsBox.style.display = 'grid';
      var fmt = function(v){ return d.metric_unit==='g' ? Math.round(v).toLocaleString()+' g' : '$'+Math.round(v).toLocaleString('es-CO'); };
      var counts = d.counts||{};
      var vals = d.valor_por_clase||{};
      statsBox.innerHTML =
        '<div style="background:#f0fdf4;border-left:4px solid #16a34a;padding:10px;border-radius:6px"><div style="font-size:10px;color:#166534;text-transform:uppercase;font-weight:700">Clase A</div><div style="font-size:1.4em;font-weight:800;color:#16a34a">'+(counts.A||0)+'</div><div style="font-size:11px;color:#475569">'+fmt(vals.A||0)+' · '+(vals.A?Math.round(vals.A/d.total_metric*100):0)+'%</div></div>'+
        '<div style="background:#fff7ed;border-left:4px solid #fd7e14;padding:10px;border-radius:6px"><div style="font-size:10px;color:#9a3412;text-transform:uppercase;font-weight:700">Clase B</div><div style="font-size:1.4em;font-weight:800;color:#fd7e14">'+(counts.B||0)+'</div><div style="font-size:11px;color:#475569">'+fmt(vals.B||0)+' · '+(vals.B?Math.round(vals.B/d.total_metric*100):0)+'%</div></div>'+
        '<div style="background:#f8fafc;border-left:4px solid #6c757d;padding:10px;border-radius:6px"><div style="font-size:10px;color:#475569;text-transform:uppercase;font-weight:700">Clase C</div><div style="font-size:1.4em;font-weight:800;color:#6c757d">'+(counts.C||0)+'</div><div style="font-size:11px;color:#475569">'+fmt(vals.C||0)+' · '+(vals.C?Math.round(vals.C/d.total_metric*100):0)+'%</div></div>'+
        ((counts.D||0)>0 ? '<div style="background:#fef2f2;border-left:4px solid #94a3b8;padding:10px;border-radius:6px"><div style="font-size:10px;color:#475569;text-transform:uppercase;font-weight:700">Sin métrica</div><div style="font-size:1.4em;font-weight:800;color:#94a3b8">'+counts.D+'</div><div style="font-size:11px;color:#475569">sin movs y/o sin precio</div></div>' : '')+
        '<div style="background:#eff6ff;border-left:4px solid #2563eb;padding:10px;border-radius:6px"><div style="font-size:10px;color:#1e40af;text-transform:uppercase;font-weight:700">Total métrica</div><div style="font-size:1.4em;font-weight:800;color:#2563eb">'+fmt(d.total_metric)+'</div><div style="font-size:11px;color:#475569">'+d.total_items+' MPs · modo '+_escHTML(modo)+'</div></div>';
    }
    // Gráfico Pareto top 30
    var chartWrap = document.getElementById('abc-chart-wrap');
    var ctx = document.getElementById('abc-chart');
    // Sebastián 20-may-2026 fix urgente · "Chart is not defined" en ABC:
    // si Chart.js (CDN externo) no cargó (red/firewall) seguimos pintando
    // la tabla y stats · solo skipeamos el gráfico con aviso suave.
    if(typeof Chart === 'undefined'){
      if(chartWrap){
        chartWrap.style.display = 'block';
        chartWrap.innerHTML = '<div style="padding:14px;color:#94a3b8;font-size:12px;text-align:center">📊 Gráfico Pareto no disponible · Chart.js no se pudo cargar (verificá conexión a CDN o usá el botón Excel para análisis offline).</div>';
      }
    } else if(chartWrap && ctx && items.length > 0){
      chartWrap.style.display = 'block';
      var top = items.filter(function(i){return i.metric>0;}).slice(0, 30);
      if(_charts.abc){ _charts.abc.destroy(); }
      _charts.abc = new Chart(ctx.getContext('2d'),{
        type:'bar',
        data:{
          labels: top.map(function(i){var n=(i.nombre_inci||i.material_id||''); return n.length>14?n.substring(0,12)+'…':n;}),
          datasets:[
            {type:'bar', label:d.metric_unit==='g'?'g':'$', data:top.map(function(i){return i.metric;}),
             backgroundColor: top.map(function(i){return i.clasificacion==='A'?'rgba(34,197,94,0.7)':i.clasificacion==='B'?'rgba(253,126,20,0.7)':'rgba(148,163,184,0.7)';}),
             borderRadius:3, yAxisID:'y'},
            {type:'line', label:'% acumulado', data:top.map(function(i){return i.pct_acumulado;}),
             borderColor:'#7c3aed', backgroundColor:'rgba(8,145,178,0.1)', tension:0.2, yAxisID:'y1', borderWidth:2, pointRadius:2},
          ],
        },
        options:{responsive:true, interaction:{intersect:false},
          plugins:{legend:{position:'top'}},
          scales:{
            y:{position:'left', beginAtZero:true, title:{display:true, text:d.metric_unit||'metric'}},
            y1:{position:'right', beginAtZero:true, max:100, grid:{drawOnChartArea:false}, title:{display:true, text:'%'}},
          },
        },
      });
    } else if(chartWrap){ chartWrap.style.display = 'none'; }
    // Tabla detalle
    if(!items.length){
      resBox.innerHTML = '<p style="color:#999;padding:20px;text-align:center">Sin datos para los filtros seleccionados</p>';
      return;
    }
    var html = '<div style="overflow-x:auto"><table class="table" style="font-size:12px"><thead><tr>'+
      '<th>#</th><th>Clase</th><th>Código</th><th>INCI</th><th>Proveedor</th><th>Origen</th><th style="text-align:right">Stock g</th><th style="text-align:right">Precio/kg</th><th style="text-align:right">Valor COP</th><th style="text-align:right">Consumo 90d g</th><th style="text-align:right">% Acum</th></tr></thead><tbody>';
    items.forEach(function(i){
      var bg = i.clasificacion==='A'?'#28a745':i.clasificacion==='B'?'#fd7e14':(i.clasificacion==='C'?'#6c757d':'#94a3b8');
      var origenIcon = i.origen==='china'?'🇨🇳':i.origen==='colombia'?'🇨🇴':i.origen==='otro'?'🌐':'❓';
      html += '<tr>'+
        '<td style="text-align:right;color:#94a3b8;font-family:monospace">'+i.ranking+'</td>'+
        '<td><span style="background:'+bg+';color:white;padding:2px 8px;border-radius:8px;font-weight:700;font-size:10px">'+i.clasificacion+'</span></td>'+
        '<td style="font-family:monospace;color:#555">'+_escHTML(i.material_id)+'</td>'+
        '<td style="font-weight:600">'+_escHTML(i.nombre_inci||i.material_id||'—')+'</td>'+
        '<td style="font-size:11px;color:#475569">'+_escHTML(i.proveedor||'—')+'</td>'+
        '<td style="font-size:11px">'+origenIcon+' '+_escHTML(i.origen)+'</td>'+
        '<td style="text-align:right">'+Math.round(i.stock_g).toLocaleString()+'</td>'+
        '<td style="text-align:right;color:#475569">'+(i.precio_kg?'$'+Math.round(i.precio_kg).toLocaleString('es-CO'):'—')+'</td>'+
        '<td style="text-align:right;font-weight:600">'+(i.valor_cop?'$'+Math.round(i.valor_cop).toLocaleString('es-CO'):'—')+'</td>'+
        '<td style="text-align:right;color:#475569">'+(i.consumo_90d_g?Math.round(i.consumo_90d_g).toLocaleString():'—')+'</td>'+
        '<td style="text-align:right;color:#7c3aed;font-weight:600">'+i.pct_acumulado.toFixed(1)+'%</td>'+
      '</tr>';
    });
    html += '</tbody></table></div>';
    resBox.innerHTML = html;
  }catch(e){
    resBox.innerHTML='<div class="alert-error">Error: '+_escHTML(e.message)+'</div>';
  }
}
function exportarExcelABC(){
  if(!_ABC_LAST || !(_ABC_LAST.items||[]).length){ alert('Calculá primero el análisis ABC'); return; }
  var d = _ABC_LAST;
  var cols = ['#', 'Clase', 'Código', 'Material', 'INCI', 'Proveedor', 'Origen',
              'Stock g', 'Precio/kg COP', 'Valor COP', 'Consumo 90d g',
              'Métrica usada', '% Acumulado'];
  var rows = d.items.map(function(i){return [
    i.ranking, i.clasificacion, i.material_id, i.nombre_comercial,
    i.nombre_inci, i.proveedor, i.origen,
    Number(i.stock_g)||0, Number(i.precio_kg)||0, Number(i.valor_cop)||0,
    Number(i.consumo_90d_g)||0, Number(i.metric)||0, Number(i.pct_acumulado)||0,
  ];});
  dlExcelHTML('ABC_'+(d.modo||'valor')+'_'+(d.tipo_material||'MP')+'_'+fhoy(), cols, rows);
}

async function loadAlertas(){
  try{
    var r=await fetch('/api/alertas'), d=await r.json();
    var tb=document.querySelector('#alertas-table tbody');
    if(!tb) return;
    if(d.alertas&&d.alertas.length){
      tb.innerHTML=d.alertas.map(function(a){return '<tr><td>'+a.material_nombre+'</td><td>'+a.stock_actual+'</td><td>'+a.stock_minimo+'</td><td>'+a.estado+'</td><td style="font-size:0.85em;">'+a.fecha+'</td></tr>';}).join('');
    }else{tb.innerHTML='<tr><td colspan="5" style="text-align:center;color:#999;">Sin alertas</td></tr>';}
  }catch(e){}
}

async function loadMovimientos(){
  // Sprint Movimientos PRO · 20-may-2026 · usa endpoint paginado
  return loadMovimientosNuevo(false);
}

// ============== Sprint Movimientos PRO · 20-may-2026 ==============
var _MOV_STATE = {limit:50, offset:0, q:'', tipo:'', desde:'', hasta:'', solo_anul:false};
var _MOV_TIMER = null;
var _MOV_LAST_DATA = null;
async function loadMovimientosNuevo(reset){
  if(reset){ _MOV_STATE.offset = 0; }
  var t0 = Date.now();
  var tb = document.querySelector('#mov-table tbody'); if(!tb) return;
  try{
    var s = _MOV_STATE;
    var qs = 'limit='+s.limit+'&offset='+s.offset+
             (s.q?'&q='+encodeURIComponent(s.q):'')+
             (s.tipo?'&tipo='+encodeURIComponent(s.tipo):'')+
             (s.desde?'&desde='+encodeURIComponent(s.desde):'')+
             (s.hasta?'&hasta='+encodeURIComponent(s.hasta):'')+
             (s.solo_anul?'&solo_anulados=1':'');
    var r = await fetch('/api/movimientos/recientes?'+qs);
    if(!r.ok){ tb.innerHTML='<tr><td colspan="12" style="text-align:center;color:#c00">Error '+r.status+'</td></tr>'; return; }
    var d = await r.json();
    _MOV_LAST_DATA = d;
    var items = d.items||[];
    if(!items.length){
      tb.innerHTML='<tr><td colspan="12" style="text-align:center;color:#999;padding:18px">Sin movimientos para los filtros'+(s.q?' "'+_escHTML(s.q)+'"':'')+'</td></tr>';
      _refreshMovPager(d); _updateMovTimestamp(t0, d); return;
    }
    var esAdmin = window._ES_ADMIN_DASH === true;
    tb.innerHTML = items.map(function(m){
      var fec = (m.fecha||'').substring(0,16).replace('T',' ');
      var tipoBadge;
      if(m.tipo==='Entrada') tipoBadge = '<span style="background:#dcfce7;color:#166534;padding:1px 7px;border-radius:8px;font-size:10px;font-weight:700">📥 IN</span>';
      else if(m.tipo==='Salida') tipoBadge = '<span style="background:#fee2e2;color:#991b1b;padding:1px 7px;border-radius:8px;font-size:10px;font-weight:700">📤 OUT</span>';
      else tipoBadge = '<span style="background:#fef3c7;color:#92400e;padding:1px 7px;border-radius:8px;font-size:10px;font-weight:700">⚖ AJU</span>';
      var ocLink = m.numero_oc ? '<a href="/oc/'+encodeURIComponent(m.numero_oc)+'" target="_blank" style="color:#7c3aed;font-family:monospace">'+_escHTML(m.numero_oc)+'</a>' : '<span style="color:#cbd5e1">—</span>';
      var anulBtn = m.anulado
        ? '<span style="color:#aaa;font-size:10px">Anulado</span>'
        : (esAdmin ? '<button data-act="mov-anul" data-id="'+m.id+'" data-mat="'+_escHTML(m.material_nombre)+'" data-cant="'+m.cantidad+'" data-tipo="'+_escHTML(m.tipo)+'" style="padding:2px 7px;font-size:11px;background:#c0392b;color:#fff;border-radius:3px" title="Anular movimiento">✕</button>' : '<span style="color:#cbd5e1;font-size:10px">—</span>');
      var rowStyle = m.anulado ? 'opacity:.5;text-decoration:line-through' : '';
      return '<tr style="'+rowStyle+'">' +
        '<td style="font-family:monospace;color:#94a3b8">'+m.id+'</td>'+
        '<td style="font-family:monospace;font-size:11px">'+_escHTML(m.material_id)+'</td>'+
        '<td style="font-weight:600">'+_escHTML(m.material_nombre)+'</td>'+
        '<td style="font-family:monospace;font-size:11px">'+_escHTML(m.lote||'—')+'</td>'+
        '<td style="text-align:right;font-weight:600">'+m.cantidad.toLocaleString()+'</td>'+
        '<td>'+tipoBadge+'</td>'+
        '<td style="font-size:11px">'+_escHTML(m.proveedor||'—')+'</td>'+
        '<td>'+ocLink+'</td>'+
        '<td style="font-size:11px;color:#475569">'+_escHTML(fec)+'</td>'+
        '<td style="font-size:11px;color:#475569">'+_escHTML(m.operador||'—')+'</td>'+
        '<td style="font-size:11px;color:#475569;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="'+_escHTML(m.observaciones)+'">'+_escHTML(m.observaciones||'')+'</td>'+
        '<td style="text-align:center">'+anulBtn+'</td>'+
      '</tr>';
    }).join('');
    _refreshMovPager(d);
    _updateMovTimestamp(t0, d);
    if(!_MOV_TIMER) _startMovAutoRefresh();
  }catch(e){
    tb.innerHTML='<tr><td colspan="12" style="text-align:center;color:#c00">Error: '+_escHTML(e.message)+'</td></tr>';
  }
}
function _updateMovTimestamp(t0, d){
  var lu = document.getElementById('mov-last-update');
  if(!lu) return;
  var hora = new Date().toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  var dur = Math.max(1, Math.round((Date.now()-t0)/100)/10);
  lu.textContent = 'Actualizado '+hora+' · '+dur+'s · '+(d.total||0)+' total';
}
function _refreshMovPager(d){
  var box = document.getElementById('mov-pager'); if(!box) return;
  var s = _MOV_STATE;
  var hasta = Math.min(s.offset + s.limit, d.total||0);
  var hayMas = d.has_more;
  box.innerHTML =
    '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12px;color:#475569;margin-top:8px">' +
    '<span>Mostrando '+(s.offset+1)+'-'+hasta+' de '+(d.total||0)+'</span>' +
    '<button onclick="movPag(-1)" '+(s.offset===0?'disabled':'')+' style="padding:3px 10px;font-size:11px">‹ Atrás</button>' +
    '<button onclick="movPag(1)" '+(!hayMas?'disabled':'')+' style="padding:3px 10px;font-size:11px">Siguiente ›</button>' +
    '</div>';
}
function movPag(dir){
  _MOV_STATE.offset = Math.max(0, _MOV_STATE.offset + dir * _MOV_STATE.limit);
  loadMovimientosNuevo(false);
}
var _MOV_BUSC_TIMER = null;
function movBuscar(val){
  if(_MOV_BUSC_TIMER) clearTimeout(_MOV_BUSC_TIMER);
  _MOV_BUSC_TIMER = setTimeout(function(){
    _MOV_STATE.q = (val||'').trim();
    loadMovimientosNuevo(true);
  }, 220);
}
function movFiltrar(){
  _MOV_STATE.tipo = (document.getElementById('mov-tipo-filtro')||{}).value || '';
  _MOV_STATE.desde = (document.getElementById('mov-desde')||{}).value || '';
  _MOV_STATE.hasta = (document.getElementById('mov-hasta')||{}).value || '';
  _MOV_STATE.solo_anul = document.getElementById('mov-anul') && document.getElementById('mov-anul').checked;
  loadMovimientosNuevo(true);
}
function _startMovAutoRefresh(){
  if(_MOV_TIMER) clearInterval(_MOV_TIMER);
  _MOV_TIMER = setInterval(function(){
    var chk = document.getElementById('mov-autorefresh');
    if(!chk || !chk.checked) return;
    if(document.visibilityState==='hidden') return;
    var tab = document.getElementById('movimientos');
    if(!tab || tab.style.display==='none') return;
    loadMovimientosNuevo(false);
  }, 60000);
}
async function registrarMovNuevo(){
  var btn = document.getElementById('btn-mov-reg');
  var msg = document.getElementById('mov-msg');
  msg.innerHTML = '';
  var data = {
    material_id: (document.getElementById('mov-id').value||'').trim().toUpperCase(),
    material_nombre: (document.getElementById('mov-nombre').value||'').trim(),
    cantidad: parseFloat(document.getElementById('mov-cant').value||'0'),
    tipo: document.getElementById('mov-tipo').value,
    lote: (document.getElementById('mov-lote').value||'').trim(),
    proveedor: (document.getElementById('mov-prov').value||'').trim(),
    observaciones: (document.getElementById('mov-obs').value||'').trim(),
    operador: window.OPER_ACTUAL || '',
  };
  // Validación frontend rápida (backend valida también)
  if(!data.material_id){ msg.innerHTML='<div class="alert-error">Código MP requerido</div>'; return; }
  if(!data.material_nombre){ msg.innerHTML='<div class="alert-error">Nombre Material requerido</div>'; return; }
  if(!data.cantidad || data.cantidad <= 0){ msg.innerHTML='<div class="alert-error">Cantidad debe ser > 0</div>'; return; }
  if(data.tipo==='Entrada' && !data.lote){ msg.innerHTML='<div class="alert-error">Lote requerido para Entrada · sin lote rompe el kardex</div>'; return; }
  if(btn){ btn.disabled = true; btn.textContent = 'Registrando…'; }
  try{
    var r = await fetch('/api/movimientos', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(data),
    });
    var res = await r.json();
    if(r.ok){
      msg.innerHTML = '<div class="alert-success">✓ '+res.message+' · mov #'+res.mov_id+'</div>';
      limpiarFormMov();
      loadMovimientosNuevo(true);
    } else {
      // Sprint Movimientos PRO fix #9: muestra res.error real
      var hint = res.lote_obligatorio ? '<div style="font-size:11px;margin-top:4px">Tip: poné el lote del proveedor o de ajuste cíclico.</div>' : '';
      msg.innerHTML = '<div class="alert-error">'+(res.error||'Error al registrar')+hint+'</div>';
    }
  }catch(e){
    msg.innerHTML = '<div class="alert-error">Error de red: '+_escHTML(e.message)+'</div>';
  }
  if(btn){ btn.disabled = false; btn.textContent = '✓ Registrar'; }
}
function limpiarFormMov(){
  ['mov-id','mov-nombre','mov-cant','mov-lote','mov-prov','mov-obs'].forEach(function(id){
    var el = document.getElementById(id); if(el) el.value = '';
  });
}
async function anularMovDelegado(movId, matNombre, cantidad, tipo){
  if(!confirm('Anular movimiento #'+movId+'? '+tipo+' · '+matNombre+' · '+cantidad+' g · Se creará nota [ANULADO] en observaciones.')) return;
  var motivo = prompt('Motivo de anulación (≥3 chars):');
  if(!motivo || motivo.trim().length < 3){ alert('Motivo requerido'); return; }
  try{
    var r = await fetch('/api/movimientos/'+movId+'/anular',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({motivo: motivo.trim()}),
    });
    var d = await r.json();
    if(r.ok){
      loadMovimientosNuevo(false);
    } else {
      alert('Error: '+(d.error||r.status));
    }
  }catch(e){ alert('Error red: '+e.message); }
}
// Delegate clicks para [data-act="mov-anul"]
if(typeof document !== 'undefined' && !window._MOV_DELEG){
  window._MOV_DELEG = true;
  document.addEventListener('click', function(ev){
    var btn = ev.target && ev.target.closest && ev.target.closest('[data-act="mov-anul"]');
    if(!btn) return;
    anularMovDelegado(btn.dataset.id, btn.dataset.mat,
                       parseFloat(btn.dataset.cant)||0, btn.dataset.tipo);
  });
}
function exportarExcelMovimientosNuevo(){
  if(!_MOV_LAST_DATA || !(_MOV_LAST_DATA.items||[]).length){
    alert('Cargá movimientos primero'); return;
  }
  var cols = ['ID','Cod MP','Material','Lote','Cantidad g','Tipo','Proveedor',
              'OC','Factura','Fecha','Operador','Estado lote','Observaciones'];
  var rows = (_MOV_LAST_DATA.items||[]).map(function(m){
    return [m.id, m.material_id, m.material_nombre, m.lote||'',
            Number(m.cantidad)||0, m.tipo, m.proveedor||'',
            m.numero_oc||'', m.numero_factura||'',
            (m.fecha||'').substring(0,19).replace('T',' '),
            m.operador||'', m.estado_lote||'', m.observaciones||''];
  });
  dlExcelHTML('Movimientos_'+fhoy(), cols, rows);
}

async function anularMovimiento(movId){
  var motivo=prompt('Motivo de anulacion (obligatorio):');
  if(!motivo||!motivo.trim()){alert('Debes ingresar un motivo.');return;}
  try{
    var r=await fetch('/api/movimientos/'+movId+'/anular',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({motivo:motivo.trim()})});
    var res=await r.json();
    if(res.ok){
      document.getElementById('mov-msg').innerHTML='<div class="alert-success">'+res.message+'</div>';
      loadMovimientos();
    }else{
      document.getElementById('mov-msg').innerHTML='<div class="alert-error">'+(res.error||'Error al anular')+'</div>';
    }
  }catch(e){document.getElementById('mov-msg').innerHTML='<div class="alert-error">Error de conexion</div>';}
}

async function registrarMov(){
  var data={material_id:document.getElementById('mov-id').value,material_nombre:document.getElementById('mov-nombre').value,cantidad:parseFloat(document.getElementById('mov-cant').value),tipo:document.getElementById('mov-tipo').value,observaciones:document.getElementById('mov-obs').value};
  try{
    var r=await fetch('/api/movimientos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    document.getElementById('mov-msg').innerHTML='<div class="alert-success">'+res.message+'</div>';
    loadMovimientos();
  }catch(e){document.getElementById('mov-msg').innerHTML='<div class="alert-error">Error</div>';}
}

// Sprint Alertas PRO · 20-may-2026 · endpoint consolidado + 6 secciones
function scrollAlertaSec(anchor){
  var el = document.getElementById(anchor);
  if(el) el.scrollIntoView({behavior:'smooth'});
}
// Event delegation · evita onclick inline con apostrofes anidados
if(typeof document !== 'undefined' && !window._ALERTAS_DELEG){
  window._ALERTAS_DELEG = true;
  document.addEventListener('click', function(ev){
    var btn = ev.target && ev.target.closest && ev.target.closest('[data-act]');
    if(!btn) return;
    var act = btn.getAttribute('data-act');
    if(act === 'sol-mp'){
      solicitarMPAlerta(btn.dataset.cod, btn.dataset.nom,
        parseFloat(btn.dataset.def)||0, btn.dataset.prov||'');
    } else if(act === 'silenciar'){
      silenciarAlerta(btn.dataset.tipo, btn.dataset.cod);
    } else if(act === 'dar-baja'){
      darBajaLoteAlerta(btn.dataset.mid, btn.dataset.lote);
    } else if(act === 'ir-qc'){
      if(typeof switchGroup === 'function') switchGroup('bar-calidadHub','cuarentena',null);
    }
  });
}
var _ALERTAS_DATA = null;
var _ALERTAS_TIMER = null;
var _ALERTAS_PREV_TOTAL = -1;
async function loadAlertasAll(silent){
  var statsBox = document.getElementById('alertas-stats');
  var secBox = document.getElementById('alertas-secciones');
  if(!secBox) return;
  var t0 = Date.now();
  try{
    var r = await fetch('/api/alertas/all');
    if(!r.ok){
      secBox.innerHTML = '<div class="alert-error">Error '+r.status+'</div>';
      return;
    }
    var d = await r.json();
    _ALERTAS_DATA = d;
    var s = d.stats || {};
    // Stats cards
    if(statsBox){
      statsBox.style.display = 'grid';
      function statCard(label, val, color, icon, anchor){
        var bg = color==='red'?'#fef2f2':color==='orange'?'#fff7ed':color==='yellow'?'#fefce8':color==='purple'?'#faf5ff':color==='teal'?'#f0fdfa':'#f8fafc';
        var fg = color==='red'?'#dc2626':color==='orange'?'#ea580c':color==='yellow'?'#ca8a04':color==='purple'?'#7c3aed':color==='teal'?'#7c3aed':'#475569';
        return '<a href="#" onclick="scrollAlertaSec(\''+anchor+'\');return false" style="text-decoration:none;background:'+bg+';border-left:4px solid '+fg+';padding:10px;border-radius:6px;display:block">'+
          '<div style="font-size:10px;color:'+fg+';text-transform:uppercase;font-weight:700;letter-spacing:.5px">'+icon+' '+label+'</div>'+
          '<div style="font-size:1.4em;font-weight:800;color:'+fg+';margin-top:2px">'+val+'</div>'+
        '</a>';
      }
      statsBox.innerHTML =
        statCard('Sin stock', s.mps_sin_stock||0, 'red', '🚫', 'sec-sin-stock') +
        statCard('Bajo mínimo', s.mps_bajo_minimo||0, 'orange', '⚠️', 'sec-bajo-min') +
        statCard('Vencidos', s.lotes_vencidos||0, 'red', '☠️', 'sec-vencidos') +
        statCard('Próximos <30d', s.lotes_proximos||0, 'yellow', '📅', 'sec-proximos') +
        statCard('MEE bajo min', s.mees_bajo_minimo||0, 'orange', '🧤', 'sec-mee') +
        statCard('Cuarentena', s.lotes_cuarentena||0, 'purple', '🔒', 'sec-cuar');
    }
    // Toast si entraron nuevas alertas críticas
    var totalCritico = (s.mps_sin_stock||0) + (s.lotes_vencidos||0);
    if(_ALERTAS_PREV_TOTAL >= 0 && totalCritico > _ALERTAS_PREV_TOTAL && !silent){
      if(typeof _dashToast === 'function'){
        _dashToast('⚠ Nuevas alertas críticas detectadas', true);
      }
    }
    _ALERTAS_PREV_TOTAL = totalCritico;
    // Render secciones
    var html = '';
    // 1. MPs sin stock
    html += '<a name="sec-sin-stock"></a><div id="sec-sin-stock"></div>';
    html += _renderSeccionMP('🚫 MPs sin stock (críticas)', d.mps_sin_stock||[], '#dc2626', 'mps_sin_stock');
    // 2. MPs bajo mínimo
    html += '<div id="sec-bajo-min"></div>';
    html += _renderSeccionMP('⚠️ MPs bajo stock mínimo', d.mps_bajo_minimo||[], '#ea580c', 'mps_bajo_minimo');
    // 2.5 Agrupado por proveedor
    if((d.agrupado_por_proveedor||[]).length){
      html += '<div style="background:#ecfeff;border:1px solid #7c3aed;border-radius:8px;padding:14px;margin:14px 0">';
      html += '<h3 style="color:#7c3aed;margin:0 0 10px;font-size:14px">📨 Agrupado por proveedor · Crear SOL combinada</h3>';
      html += '<div style="display:flex;flex-wrap:wrap;gap:8px">';
      d.agrupado_por_proveedor.forEach(function(g, gi){
        html += '<div style="background:#fff;border:1px solid #bae6fd;border-radius:6px;padding:8px 12px;flex:1;min-width:240px">';
        html += '<div style="font-weight:700;font-size:13px;color:#7c3aed">'+_escHTML(g.proveedor)+'</div>';
        html += '<div style="font-size:11px;color:#475569;margin:3px 0">'+g.items.length+' MP(s) · déficit total '+Math.round(g.deficit_total_g).toLocaleString()+' g</div>';
        html += '<button onclick="crearSolCombinada('+gi+')" style="padding:4px 10px;font-size:11px;background:#7c3aed;color:#fff;border-radius:4px">📨 Crear SOL combinada</button>';
        html += '</div>';
      });
      html += '</div></div>';
    }
    // 3. Lotes vencidos
    html += '<div id="sec-vencidos"></div>';
    html += _renderSeccionLotes('☠️ Lotes YA vencidos (dar de baja)', d.lotes_vencidos||[], '#dc2626', true);
    // 4. Lotes próximos
    html += '<div id="sec-proximos"></div>';
    html += _renderSeccionLotes('📅 Lotes que vencen en próximos 30 días', d.lotes_proximos||[], '#ca8a04', false);
    // 5. MEE
    html += '<div id="sec-mee"></div>';
    html += _renderSeccionMEE(d.mees_bajo_minimo||[]);
    // 6. Cuarentena
    html += '<div id="sec-cuar"></div>';
    html += _renderSeccionCuarentena(d.lotes_cuarentena||[]);
    secBox.innerHTML = html;
    // Timestamp
    var lu = document.getElementById('alertas-last-update');
    if(lu){
      var hora = new Date().toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
      var dur = Math.max(1, Math.round((Date.now()-t0)/100)/10);
      lu.textContent = 'Actualizado '+hora+' · '+dur+'s · '+s.total+' alertas total' +
        (s.silenciadas_activas?(' · '+s.silenciadas_activas+' silenciadas'):'');
    }
    if(!_ALERTAS_TIMER) _startAlertasAutoRefresh();
  }catch(e){
    secBox.innerHTML = '<div class="alert-error">Error: '+_escHTML(e.message)+'</div>';
  }
}
function _startAlertasAutoRefresh(){
  if(_ALERTAS_TIMER) clearInterval(_ALERTAS_TIMER);
  _ALERTAS_TIMER = setInterval(function(){
    var chk = document.getElementById('alertas-autorefresh');
    if(!chk || !chk.checked) return;
    if(document.visibilityState==='hidden') return;
    var tab = document.getElementById('alertas');
    if(!tab || tab.style.display==='none') return;
    loadAlertasAll(true);
  }, 60000);
}
function _renderSeccionMP(titulo, items, color, tipoSilen){
  var h = '<div style="margin-top:18px"><h3 style="color:'+color+';font-size:14px;margin-bottom:8px">'+titulo+' <span style="font-size:11px;color:#94a3b8;font-weight:400">('+items.length+')</span></h3>';
  if(!items.length){
    h += '<div style="background:#f0fdf4;color:#166534;border:1px solid #86efac;padding:10px;border-radius:6px;font-size:13px">✓ Sin alertas en esta categoría</div></div>';
    return h;
  }
  h += '<div style="overflow-x:auto"><table class="table" style="font-size:12px"><thead><tr>'+
    '<th>Código</th><th>Nombre</th><th>INCI</th><th>Proveedor</th>'+
    '<th style="text-align:right">Mín g</th><th style="text-align:right">Stock g</th>'+
    '<th style="text-align:right">Déficit</th><th style="text-align:center">Cobertura</th>'+
    '<th style="text-align:center">Acción</th></tr></thead><tbody>';
  items.forEach(function(it){
    var pct = it.cobertura_pct;
    var pctColor = pct<25?'#dc2626':pct<50?'#ea580c':'#ca8a04';
    h += '<tr>'+
      '<td style="font-family:monospace;font-size:11px">'+_escHTML(it.codigo_mp)+'</td>'+
      '<td style="font-size:11px;color:#888">'+_escHTML(it.nombre)+'</td>'+
      '<td style="font-weight:600">'+_escHTML(it.nombre_inci||it.nombre)+'</td>'+
      '<td style="font-size:11px;color:#475569">'+_escHTML(it.proveedor||'—')+'</td>'+
      '<td style="text-align:right">'+Math.round(it.stock_minimo_g).toLocaleString()+'</td>'+
      '<td style="text-align:right;color:'+pctColor+';font-weight:600">'+Math.round(it.stock_actual_g).toLocaleString()+'</td>'+
      '<td style="text-align:right;color:#dc2626;font-weight:700">'+Math.round(it.deficit_g).toLocaleString()+'</td>'+
      '<td style="text-align:center"><span style="color:'+pctColor+';font-weight:700">'+pct+'%</span></td>'+
      '<td style="text-align:center;white-space:nowrap">'+
        '<button data-act="sol-mp" data-cod="'+_escHTML(it.codigo_mp)+'" data-nom="'+_escHTML(it.nombre)+'" data-def="'+it.deficit_g+'" data-prov="'+_escHTML(it.proveedor||'')+'" style="padding:2px 7px;font-size:11px;background:#27ae60;color:#fff;border-radius:3px">Solicitar</button> '+
        '<button data-act="silenciar" data-tipo="'+tipoSilen+'" data-cod="'+_escHTML(it.codigo_mp)+'" style="padding:2px 7px;font-size:11px;background:#94a3b8;color:#fff;border-radius:3px" title="Silenciar esta alerta">🔇</button>'+
      '</td></tr>';
  });
  h += '</tbody></table></div></div>';
  return h;
}
function _renderSeccionLotes(titulo, items, color, esVencido){
  var h = '<div style="margin-top:18px"><h3 style="color:'+color+';font-size:14px;margin-bottom:8px">'+titulo+' <span style="font-size:11px;color:#94a3b8;font-weight:400">('+items.length+')</span></h3>';
  if(!items.length){
    h += '<div style="background:#f0fdf4;color:#166534;border:1px solid #86efac;padding:10px;border-radius:6px;font-size:13px">✓ Sin lotes</div></div>';
    return h;
  }
  h += '<div style="overflow-x:auto"><table class="table" style="font-size:12px"><thead><tr>'+
    '<th>Código</th><th>Material</th><th>Lote</th><th>Proveedor</th>'+
    '<th style="text-align:right">Cantidad g</th>'+
    '<th style="text-align:center">Vence</th><th style="text-align:center">Días</th>'+
    '<th style="text-align:center">Acción</th></tr></thead><tbody>';
  items.forEach(function(it){
    var dCol = it.dias_para_vencer<0?'#dc2626':(it.dias_para_vencer<=7?'#dc2626':'#ea580c');
    h += '<tr>'+
      '<td style="font-family:monospace;font-size:11px">'+_escHTML(it.material_id)+'</td>'+
      '<td style="font-weight:600">'+_escHTML(it.nombre)+'</td>'+
      '<td style="font-family:monospace;font-size:11px">'+_escHTML(it.lote)+'</td>'+
      '<td style="font-size:11px;color:#475569">'+_escHTML(it.proveedor||'—')+'</td>'+
      '<td style="text-align:right;font-weight:600">'+Math.round(it.cantidad_g).toLocaleString()+'</td>'+
      '<td style="text-align:center">'+_escHTML(it.fecha_vencimiento)+'</td>'+
      '<td style="text-align:center;color:'+dCol+';font-weight:700">'+(it.dias_para_vencer<0?(it.dias_para_vencer+'d (VENCIDO)'):(it.dias_para_vencer+'d'))+'</td>'+
      '<td style="text-align:center;white-space:nowrap">'+
        (esVencido ? '<button data-act="dar-baja" data-mid="'+_escHTML(it.material_id)+'" data-lote="'+_escHTML(it.lote)+'" style="padding:2px 7px;font-size:11px;background:#c0392b;color:#fff;border-radius:3px">Dar de baja</button>' : '') + ' ' +
        '<button data-act="silenciar" data-tipo="lote_venc" data-cod="'+_escHTML(it.material_id)+'::'+_escHTML(it.lote)+'" style="padding:2px 7px;font-size:11px;background:#94a3b8;color:#fff;border-radius:3px" title="Silenciar">🔇</button>'+
      '</td></tr>';
  });
  h += '</tbody></table></div></div>';
  return h;
}
function _renderSeccionMEE(items){
  var h = '<div style="margin-top:18px"><h3 style="color:#ea580c;font-size:14px;margin-bottom:8px">🧤 Materiales E&E bajo stock mínimo <span style="font-size:11px;color:#94a3b8;font-weight:400">('+items.length+')</span></h3>';
  if(!items.length){
    h += '<div style="background:#f0fdf4;color:#166534;border:1px solid #86efac;padding:10px;border-radius:6px;font-size:13px">✓ Sin MEE bajo mínimo</div></div>';
    return h;
  }
  h += '<div style="overflow-x:auto"><table class="table" style="font-size:12px"><thead><tr>'+
    '<th>Código</th><th>Descripción</th><th>Categoría</th><th>Proveedor</th>'+
    '<th style="text-align:right">Mín und</th><th style="text-align:right">Stock</th>'+
    '<th style="text-align:right">Déficit</th><th style="text-align:center">Acción</th></tr></thead><tbody>';
  items.forEach(function(m){
    h += '<tr>'+
      '<td style="font-family:monospace;font-size:11px">'+_escHTML(m.codigo)+'</td>'+
      '<td style="font-weight:600">'+_escHTML(m.descripcion)+'</td>'+
      '<td>'+_escHTML(m.categoria)+'</td>'+
      '<td style="font-size:11px">'+_escHTML(m.proveedor||'—')+'</td>'+
      '<td style="text-align:right">'+m.stock_minimo+'</td>'+
      '<td style="text-align:right;color:#dc2626;font-weight:700">'+m.stock_actual+'</td>'+
      '<td style="text-align:right;color:#dc2626;font-weight:700">'+m.deficit+'</td>'+
      '<td style="text-align:center"><button data-act="silenciar" data-tipo="mee_bajo_minimo" data-cod="'+_escHTML(m.codigo)+'" style="padding:2px 7px;font-size:11px;background:#94a3b8;color:#fff;border-radius:3px" title="Silenciar">🔇</button></td>'+
    '</tr>';
  });
  h += '</tbody></table></div></div>';
  return h;
}
function _renderSeccionCuarentena(items){
  var h = '<div style="margin-top:18px"><h3 style="color:#7c3aed;font-size:14px;margin-bottom:8px">🔒 Lotes en cuarentena · pendiente QC <span style="font-size:11px;color:#94a3b8;font-weight:400">('+items.length+')</span></h3>';
  if(!items.length){
    h += '<div style="background:#f0fdf4;color:#166534;border:1px solid #86efac;padding:10px;border-radius:6px;font-size:13px">✓ Sin lotes en cuarentena</div></div>';
    return h;
  }
  h += '<div style="overflow-x:auto"><table class="table" style="font-size:12px"><thead><tr>'+
    '<th>Código</th><th>Material</th><th>Lote</th><th>Proveedor</th>'+
    '<th>OC</th><th style="text-align:right">Cantidad g</th><th>Ingresado</th><th>Acción</th></tr></thead><tbody>';
  items.forEach(function(it){
    h += '<tr>'+
      '<td style="font-family:monospace;font-size:11px">'+_escHTML(it.material_id)+'</td>'+
      '<td style="font-weight:600">'+_escHTML(it.nombre)+'</td>'+
      '<td style="font-family:monospace;font-size:11px">'+_escHTML(it.lote)+'</td>'+
      '<td style="font-size:11px">'+_escHTML(it.proveedor||'—')+'</td>'+
      '<td style="font-family:monospace;font-size:11px">'+_escHTML(it.numero_oc||'—')+'</td>'+
      '<td style="text-align:right">'+Math.round(it.cantidad_g).toLocaleString()+'</td>'+
      '<td style="font-size:11px;color:#475569">'+_escHTML(it.fecha_ingreso)+'</td>'+
      '<td><button data-act="ir-qc" style="padding:2px 7px;font-size:11px;background:#7c3aed;color:#fff;border-radius:3px">Ir a QC</button></td>'+
    '</tr>';
  });
  h += '</tbody></table></div></div>';
  return h;
}
async function silenciarAlerta(tipo, cod){
  var motivo = prompt('Motivo para silenciar esta alerta (≥10 chars):\nEj: "MP en descontinuación", "Lote rotado a Animus", etc.');
  if(motivo === null) return;
  motivo = motivo.trim();
  if(motivo.length < 10){ alert('Motivo demasiado corto'); return; }
  var dias = prompt('¿En cuántos días reactivar? (vacío = silencio permanente)');
  try{
    var body = {tipo_alerta: tipo, codigo_referencia: cod, motivo: motivo};
    if(dias && parseInt(dias)>0) body.expira_dias = parseInt(dias);
    var r = await fetch('/api/alertas/silenciar', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body),
    });
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    loadAlertasAll(true);
  }catch(e){ alert('Error red: '+e.message); }
}
async function darBajaLoteAlerta(mid, lote){
  if(!confirm('Dar de baja DEFINITIVA el lote '+lote+'? Esto elimina los movimientos y queda en audit_log.')) return;
  var motivo = prompt('Motivo (≥10 chars):');
  if(!motivo || motivo.trim().length < 10){ alert('Motivo requerido'); return; }
  try{
    var url = '/api/lotes/'+encodeURIComponent(mid)+'/'+encodeURIComponent(lote||'_SIN_LOTE_');
    var r = await fetch(url, {method:'DELETE', headers:{'Content-Type':'application/json'},
                                body: JSON.stringify({motivo: motivo.trim()})});
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    alert('✓ Lote dado de baja');
    loadAlertasAll(true);
  }catch(e){ alert('Error red: '+e.message); }
}
function solicitarMPAlerta(codigo, nombre, deficit, proveedor){
  // Reusa el modal de Solicitar de Bodega MP
  _solLote = {
    material_id: codigo, material_nombre: nombre,
    lote: '', proveedor: proveedor, stock_min_g: deficit,
  };
  document.getElementById('sol-mp-nombre').textContent = nombre;
  document.getElementById('sol-mp-cod').textContent = 'Codigo: '+codigo;
  document.getElementById('sol-mp-stock').textContent = 'Déficit: '+Math.round(deficit).toLocaleString()+' g';
  document.getElementById('sol-prov').value = proveedor || '';
  document.getElementById('sol-cant').value = Math.round(deficit*1.5);
  document.getElementById('sol-unidad').value = 'g';
  document.getElementById('sol-urg').value = 'Urgente';
  document.getElementById('sol-obs').value = 'Generado desde Alertas · déficit '+Math.round(deficit)+' g';
  document.getElementById('sol-msg').innerHTML = '';
  _cargarProveedoresUnicos();
  document.getElementById('modal-solicitar-lote').style.display = 'flex';
}
async function crearSolCombinada(gIdx){
  var g = ((_ALERTAS_DATA||{}).agrupado_por_proveedor||[])[gIdx];
  if(!g){ alert('Grupo no encontrado'); return; }
  if(!confirm('Crear SOL combinada para '+g.proveedor+' con '+g.items.length+' MPs?')) return;
  var items = g.items.map(function(it){
    return {codigo_mp: it.codigo_mp, nombre_mp: it.nombre,
            cantidad_g: Math.max(it.deficit_g*1.5, 100),
            unidad: 'g', justificacion: 'Reabastecimiento agrupado · alerta bajo mínimo',
            valor_estimado: 0};
  });
  var payload = {
    solicitante: window.OPER_ACTUAL || 'planta',
    urgencia: 'Urgente',
    observaciones: 'SOL combinada generada desde Alertas · '+g.items.length+' MPs · déficit total '+Math.round(g.deficit_total_g)+' g',
    empresa: 'Espagiria', categoria: 'Materia Prima', tipo: 'Compra', area: 'Produccion',
    items: items,
  };
  try{
    var r = await fetch('/api/solicitudes-compra', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload),
    });
    var d = await r.json();
    if(r.ok){
      alert('✓ SOL combinada creada: '+(d.numero||'?')+' · '+items.length+' items');
      loadAlertasAll(true);
    } else {
      alert('Error: '+(d.error||r.status));
    }
  }catch(e){ alert('Error red: '+e.message); }
}
function exportarExcelAlertas(){
  if(!_ALERTAS_DATA){ alert('Cargá primero las alertas'); return; }
  var d = _ALERTAS_DATA;
  var rows = [];
  (d.mps_sin_stock||[]).forEach(function(it){ rows.push(['Sin stock', it.codigo_mp, it.nombre, it.proveedor, it.stock_minimo_g, it.stock_actual_g, it.deficit_g, it.cobertura_pct+'%']); });
  (d.mps_bajo_minimo||[]).forEach(function(it){ rows.push(['Bajo mín', it.codigo_mp, it.nombre, it.proveedor, it.stock_minimo_g, it.stock_actual_g, it.deficit_g, it.cobertura_pct+'%']); });
  (d.lotes_vencidos||[]).forEach(function(it){ rows.push(['Vencido', it.material_id, it.nombre+' ('+it.lote+')', it.proveedor, '', it.cantidad_g, '', it.dias_para_vencer+'d (VENCIDO)']); });
  (d.lotes_proximos||[]).forEach(function(it){ rows.push(['Próximo', it.material_id, it.nombre+' ('+it.lote+')', it.proveedor, '', it.cantidad_g, '', it.dias_para_vencer+'d']); });
  (d.mees_bajo_minimo||[]).forEach(function(m){ rows.push(['MEE bajo', m.codigo, m.descripcion, m.proveedor, m.stock_minimo, m.stock_actual, m.deficit, '']); });
  (d.lotes_cuarentena||[]).forEach(function(it){ rows.push(['Cuarentena', it.material_id, it.nombre+' ('+it.lote+')', it.proveedor, '', it.cantidad_g, '', 'OC '+(it.numero_oc||'—')]); });
  if(!rows.length){ alert('Sin alertas para exportar'); return; }
  var cols = ['Tipo','Código','Material','Proveedor','Mín','Stock/Cant','Déficit','Detalle'];
  dlExcelHTML('Alertas_'+fhoy(), cols, rows);
}

async function loadVenc30(){
  try{
    var r=await fetch('/api/lotes'),d=await r.json(),lotes=d.lotes||[];
    var prox=lotes.filter(function(l){return l.dias_para_vencer!=null&&l.dias_para_vencer>=0&&l.dias_para_vencer<=30;});
    var div=document.getElementById('venc30-content');if(!div)return;
    if(!prox.length){div.innerHTML='<span style="color:#28a745;font-weight:600;">Sin lotes proximos a vencer en 30 dias.</span>';return;}
    prox.sort(function(a,b){return a.dias_para_vencer-b.dias_para_vencer;});
    div.innerHTML='<table class="table" style="margin-top:8px;"><thead><tr><th>Codigo</th><th>Material</th><th>Lote</th><th style="text-align:right;">Cantidad(g)</th><th>Vence</th><th style="text-align:center;">Dias</th></tr></thead><tbody>'+
    prox.map(function(l){
      var c2=l.dias_para_vencer<=7?'color:#cc0000;font-weight:700;':'color:#e65100;font-weight:600;';
      return '<tr><td style="font-family:monospace;font-size:0.82em;">'+l.material_id+'</td><td style="font-weight:600;">'+l.material_nombre+'</td><td style="font-family:monospace;font-size:0.82em;">'+l.lote+'</td><td style="text-align:right;">'+l.cantidad_g.toLocaleString()+'</td><td>'+l.fecha_vencimiento+'</td><td style="text-align:center;'+c2+'">'+l.dias_para_vencer+'d</td></tr>';
    }).join('')+'</tbody></table>';
  }catch(e){}
}
async function loadAlertasReabas(){
  try{
    var r=await fetch('/api/alertas-reabastecimiento'), d=await r.json();
    var alertas=d.alertas||[];
    var tb=document.getElementById('reabas-body');
    if(!tb) return;
    if(!alertas.length){
      tb.innerHTML='<tr><td colspan="9" style="text-align:center;color:#28a745;padding:15px;">&#10003; Todo el stock esta sobre el minimo calculado</td></tr>';
      return;
    }
    var h='';
    window._alertasData=alertas;
    alertas.forEach(function(a,ri){
      var pct=a.stock_minimo>0?Math.round((a.stock_actual/a.stock_minimo)*100):0;
      var critico=pct<25;var urgente=pct>=25&&pct<50;
      var color=critico?'#ffebeb':urgente?'#fff3e0':'#fffde7';
      var badge=critico?'<span style="background:#cc0000;color:white;padding:2px 8px;border-radius:10px;font-size:0.82em;font-weight:700;">CRÍTICO</span>':
                urgente?'<span style="background:#e65100;color:white;padding:2px 8px;border-radius:10px;font-size:0.82em;font-weight:700;">URGENTE</span>':
                '<span style="background:#f57f17;color:white;padding:2px 8px;border-radius:10px;font-size:0.82em;font-weight:700;">BAJO</span>';
      var esMEE=a.tipo==='MEE';
      var tipoBadge=esMEE?'<span style="background:#6d28d9;color:white;padding:1px 7px;border-radius:8px;font-size:0.78em;font-weight:700;">MEE</span>':
                         '<span style="background:#555;color:white;padding:1px 7px;border-radius:8px;font-size:0.78em;font-weight:700;">MP</span>';
      var unidad=esMEE?'und':'g';
      h+='<tr style="background:'+color+';">';
      h+='<td style="text-align:center;">'+tipoBadge+'</td>';
      h+='<td style="font-family:monospace;font-size:0.85em;">'+a.codigo_mp+'</td>';
      h+='<td style="font-weight:600;">'+a.nombre+'</td>';
      var provId='prov-inp-'+a.codigo_mp.replace(/[^a-zA-Z0-9]/g,'');
      h+='<td style="min-width:140px;">';
      h+='<input type="text" id="'+provId+'" value="'+(a.proveedor||'')+'"';
      h+=' data-cod="'+a.codigo_mp+'"';
      h+=' placeholder="Sin proveedor"';
      h+=' style="width:100%;padding:3px 6px;border:1px solid #ccc;border-radius:4px;font-size:0.82em;"';
      h+=' onchange="guardarProveedorMP(this)" oninput="guardarProveedorMP(this)"';
      h+=' title="Edita y presiona Enter o Tab para guardar">';
      h+='</td>';
      h+='<td style="text-align:right;font-weight:600;">'+a.stock_minimo.toLocaleString()+' '+unidad+'</td>';
      h+='<td style="text-align:right;color:#cc0000;font-weight:700;">'+a.stock_actual.toLocaleString()+' '+unidad+'</td>';
      h+='<td style="text-align:right;color:#cc0000;font-weight:700;">'+a.deficit.toLocaleString()+' '+unidad+'</td>';
      h+='<td style="text-align:center;">'+badge+' '+pct+'%</td>';
      var accion=esMEE?'<button onclick="switchTab(&apos;mee&apos;,null)" style="padding:4px 10px;font-size:0.78em;background:#6d28d9;color:white;border-radius:4px;">Ver MEE</button>':
                       '<button onclick="abrirSolIdx('+ri+')" style="padding:4px 10px;font-size:0.78em;background:#6d28d9;color:white;border-radius:4px;">Solicitar</button>';
      h+='<td style="text-align:center;">'+accion+'</td>';
      h+='</tr>';
    });
    tb.innerHTML=h;
  }catch(e){
    var tb2=document.getElementById('reabas-body');
    if(tb2) tb2.innerHTML='<tr><td colspan="9" style="text-align:center;color:#999;">Carga el catalogo maestro primero (python cargar_maestro.py)</td></tr>';
  }
}

/* ===== MEE FUNCTIONS ===== */
var MEE_CATS=['Envase','Tapa','Etiqueta','Plegable','Serigrafia','Gotero','Frasco','Contorno','Otro'];

async function cargarSelectsMEE(){
  var r=await fetch('/api/mee/stock'); var d=await r.json();
  _meeData=d.items||[];
  filtrarMEEIngreso();
}
function filtrarMEEIngreso(){
  var cat=document.getElementById('mee-ing-cat').value;
  var sel=document.getElementById('mee-ing-cod');
  sel.innerHTML='<option value="">-- Selecciona --</option>';
  _meeData.filter(function(x){return !cat||x.categoria===cat;}).forEach(function(x){
    var o=document.createElement('option');o.value=x.codigo;o.textContent=x.codigo+' — '+x.descripcion;sel.appendChild(o);
  });
}
async function registrarIngresoMEE(){
  var cod=document.getElementById('mee-ing-cod').value;
  var cant=parseFloat(document.getElementById('mee-ing-cant').value);
  var ref=document.getElementById('mee-ing-ref').value;
  var obs=document.getElementById('mee-ing-obs').value;
  if(!cod||!cant){document.getElementById('mee-ing-msg').innerHTML='<span style="color:red;">Selecciona material y cantidad</span>';return;}
  var r=await fetch('/api/mee/movimiento',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({codigo:cod,tipo:'Entrada',cantidad:cant,lote_ref:ref,observaciones:obs,responsable:OPER_ACTUAL})});
  var d=await r.json();
  if(r.ok){
    _ultimoMEE={codigo:cod,cant:cant,ref:ref};
    document.getElementById('mee-ing-msg').innerHTML='<span style="color:green;">Entrada registrada. Stock: '+d.stock_nuevo+' und &nbsp;<button onclick="generarRotuloMEE()" style="background:#2980b9;color:white;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:0.85em;">&#128209; Rotulo</button></span>';
    document.getElementById('btn-rotulo-mee').disabled=false;
    loadHistMEE();loadMEE();
  }else{document.getElementById('mee-ing-msg').innerHTML='<span style="color:red;">'+(d.error||'Error')+'</span>';}
}
var _ultimoMEE=null;
function generarRotuloMEE(){
  if(!_ultimoMEE){alert('Primero registra una entrada MEE');return;}
  window.open('/rotulo-recepcion-mee/'+encodeURIComponent(_ultimoMEE.codigo)+'/'+(parseFloat(_ultimoMEE.cant)||0),'_blank');
}
function limpiarIngresoMEE(){document.getElementById('mee-ing-cod').value='';document.getElementById('mee-ing-cant').value='';document.getElementById('mee-ing-ref').value='';document.getElementById('mee-ing-obs').value='';}
async function loadHistMEE(){
  var r=await fetch('/api/mee/movimientos?tipo=Entrada&limit=20'); var d=await r.json();
  var tb=document.getElementById('mee-hist-body');
  if(!d.movimientos||!d.movimientos.length){tb.innerHTML='<tr><td colspan="7" style="text-align:center;color:#999;">Sin movimientos</td></tr>';return;}
  tb.innerHTML=d.movimientos.map(function(m){
    var col=m.tipo==='Entrada'?'#27ae60':m.tipo==='Ajuste'?'#f39c12':'#e74c3c';
    return '<tr><td style="font-family:monospace;font-size:11px;">'+m.mee_codigo+'</td><td>'+m.descripcion+'</td><td><span style="color:'+col+';font-weight:600;">'+m.tipo+'</span></td><td style="text-align:right;font-weight:600;">'+m.cantidad+'</td><td>'+(m.lote_ref||'')+'</td><td>'+m.responsable+'</td><td>'+(m.fecha||'').substring(0,16)+'</td></tr>';
  }).join('');
}
async function loadMEE(){
  var cat=document.getElementById('mee-cat-filter')?document.getElementById('mee-cat-filter').value:'';
  var q=document.getElementById('mee-search')?document.getElementById('mee-search').value:'';
  var url='/api/mee/stock?';if(cat)url+='categoria='+encodeURIComponent(cat)+'&';if(q)url+='q='+encodeURIComponent(q);
  var r=await fetch(url); var d=await r.json();
  var tb=document.getElementById('mee-stock-body');
  if(!d.items||!d.items.length){tb.innerHTML='<tr><td colspan="10" style="text-align:center;color:#999;padding:20px;">Sin materiales</td></tr>';return;}
  tb.innerHTML=d.items.map(function(m){
    var deficit=m.stock_actual-m.stock_minimo;
    var est=deficit<0?'<span style="color:#e74c3c;font-weight:700;">BAJO</span>':deficit<m.stock_minimo*0.3?'<span style="color:#f39c12;font-weight:700;">ALERTA</span>':'<span style="color:#27ae60;font-weight:700;">OK</span>';
    return '<tr><td style="font-family:monospace;font-size:11px;">'+m.codigo+'</td><td>'+m.descripcion+'</td><td><span style="font-size:11px;background:#f0f4ff;padding:2px 8px;border-radius:10px;">'+m.categoria+'</span></td><td>'+m.proveedor+'</td>'
    +'<td style="text-align:right;">'+m.stock_minimo+'</td>'
    +'<td style="text-align:right;font-weight:700;">'+m.stock_actual+'</td>'
    +'<td style="text-align:center;">'+est+'</td>'
    +'<td style="text-align:center;"><button class="btn btn-ghost btn-sm" onclick="abrirAjusteMEE(&quot;'+m.codigo+'&quot;,&quot;'+_eq(m.descripcion)+'&quot;,'+m.stock_actual+')">Ajustar</button></td>'
    +'<td style="text-align:center;"><button class="btn btn-ghost btn-sm" onclick="verHistorialMEE(&quot;'+m.codigo+'&quot;)">Hist.</button></td>'
    +'<td style="text-align:center;"><button class="btn btn-sm" style="background:#4A6741;font-size:11px;" onclick="solicitarCompraMEE(&quot;'+m.codigo+'&quot;,&quot;'+_eq(m.descripcion)+'&quot;,'+m.stock_actual+','+m.stock_minimo+')">Solicitar</button></td>'
    +'</tr>';
  }).join('');
}
function abrirNuevoMEE(){document.getElementById('nuevo-mee-form').style.display='block';}
async function crearMEE(){
  var cod=document.getElementById('nmee-cod').value.trim().toUpperCase();
  var desc=document.getElementById('nmee-desc').value.trim();
  var cat=document.getElementById('nmee-cat').value;
  var prov=document.getElementById('nmee-prov').value.trim();
  var stock=parseFloat(document.getElementById('nmee-stock').value)||2000;
  var smin=parseFloat(document.getElementById('nmee-min').value)||1000;
  if(!cod||!desc){document.getElementById('nmee-msg').innerHTML='<span style="color:red;">Codigo y descripcion requeridos</span>';return;}
  var r=await fetch('/api/mee',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({codigo:cod,descripcion:desc,categoria:cat,proveedor:prov,stock_actual:stock,stock_minimo:smin})});
  var d=await r.json();
  if(r.ok){document.getElementById('nmee-msg').innerHTML='<span style="color:green;">Creado exitosamente</span>';document.getElementById('nuevo-mee-form').style.display='none';loadMEE();}
  else{document.getElementById('nmee-msg').innerHTML='<span style="color:red;">'+(d.error||'Error')+'</span>';}
}
async function abrirAjusteMEE(cod,desc,stock){
  if(!OPER_ACTUAL){alert('Selecciona tu nombre primero');return;}
  var nuevo=prompt('Ajuste de stock: '+cod+' — '+desc+'\nStock actual: '+stock+' und\nNuevo valor:');
  if(nuevo===null||nuevo==='')return;
  var n=parseFloat(nuevo);if(isNaN(n)||n<0){alert('Valor invalido');return;}
  var obs=prompt('Motivo del ajuste:','Inventario fisico');
  var r=await fetch('/api/mee/movimiento',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({codigo:cod,tipo:'Ajuste',cantidad:n,observaciones:obs||'Ajuste',responsable:OPER_ACTUAL})});
  var d=await r.json();
  if(d.ok){alert('Ajuste registrado. Stock: '+d.stock_nuevo+' und');loadMEE();}
  else alert('Error: '+(d.error||''));
}
async function verHistorialMEE(cod){
  var r=await fetch('/api/mee/movimientos?codigo='+encodeURIComponent(cod)+'&limit=30');
  var d=await r.json();
  var rows=d.movimientos||[];
  var html=rows.map(function(m){
    var col=m.tipo==='Entrada'?'#27ae60':m.tipo==='Ajuste'?'#f39c12':'#e74c3c';
    return '<tr style="border-bottom:1px solid #eee;"><td style="padding:6px;color:'+col+';font-weight:600;">'+m.tipo+'</td><td style="padding:6px;text-align:right;">'+m.cantidad+'</td><td style="padding:6px;color:#888;">'+(m.lote_ref||m.batch_ref||'—')+'</td><td style="padding:6px;">'+(m.responsable||'—')+'</td><td style="padding:6px;font-size:0.82em;color:#666;">'+m.fecha+'</td></tr>';
  }).join('') || '<tr><td colspan="5" style="text-align:center;color:#999;padding:12px;">Sin movimientos</td></tr>';
  document.getElementById('hist-lote-info').textContent='MEE — '+cod+' ('+rows.length+' movimientos)';
  document.getElementById('hist-lote-body').innerHTML=html;
  document.getElementById('modal-historial').style.display='flex';
}
async function solicitarCompraMEE(cod,desc,stock,smin){
  var cant=prompt('Solicitar compra para: '+desc+'\nStock actual: '+stock+' und / Minimo: '+smin+' und\nCantidad a solicitar:');
  if(!cant||isNaN(parseFloat(cant)))return;
  var data={
    solicitante:OPER_ACTUAL||'Sistema',
    area:'Produccion',empresa:'Espagiria',categoria:'Envase y Empaque',tipo:'Compra',
    urgencia:'Urgente',observaciones:'Solicitud automatica desde alerta MEE',
    items:[{codigo_mp:cod,nombre_mp:desc,cantidad_g:parseFloat(cant),unidad:'und',valor_estimado:0}]
  };
  var r=await fetch('/api/solicitudes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  var d=await r.json();
  if(r.ok)alert('Solicitud creada: '+d.numero+'\nVisible en modulo Compras > Solicitudes');
  else alert('Error: '+(d.error||''));
}
async function loadAlertasMEE(){
  var r=await fetch('/api/alertas-mee'); var d=await r.json();
  var tb=document.getElementById('mee-alertas-body');
  if(!d.alertas||!d.alertas.length){tb.innerHTML='<tr><td colspan="8" style="text-align:center;color:green;padding:16px;">Todo el stock MEE por encima del minimo</td></tr>';return;}
  tb.innerHTML=d.alertas.map(function(m){
    var def=m.stock_actual-m.stock_minimo;
    var niv=def<-m.stock_minimo?'<span style="color:#e74c3c;font-weight:700;">CRITICO</span>':'<span style="color:#f39c12;font-weight:700;">BAJO</span>';
    return '<tr><td style="font-family:monospace;font-size:11px;">'+m.codigo+'</td><td>'+m.descripcion+'</td>'
    +'<td><span style="background:#f0f4ff;padding:2px 8px;border-radius:10px;font-size:11px;">'+m.categoria+'</span></td>'
    +'<td style="text-align:right;">'+m.stock_minimo+'</td>'
    +'<td style="text-align:right;font-weight:700;color:#e74c3c;">'+m.stock_actual+'</td>'
    +'<td style="text-align:right;color:#e74c3c;font-weight:700;">'+def+'</td>'
    +'<td style="text-align:center;">'+niv+'</td>'
    +'<td style="text-align:center;"><button class="btn btn-sm" style="background:#4A6741;font-size:11px;" onclick="solicitarCompraMEE(&quot;'+m.codigo+'&quot;,&quot;'+_eq(m.descripcion)+'&quot;,'+m.stock_actual+','+m.stock_minimo+')">Solicitar</button></td>'
    +'</tr>';
  }).join('');
}
async function generarOCsDesdeAlertasMEE(){
  var r=await fetch('/api/alertas-mee'); var d=await r.json();
  if(!d.alertas||!d.alertas.length){alert('No hay alertas MEE activas');return;}
  var items=d.alertas.map(function(m){return {codigo_mp:m.codigo,nombre_mp:m.descripcion,cantidad_g:Math.max(m.stock_minimo*2-m.stock_actual,1),precio_unitario:0};});
  var r2=await fetch('/api/ordenes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({proveedor:'Por asignar',observaciones:'OC automatica desde alertas MEE',items:items,creado_por:OPER_ACTUAL||'Sistema'})});
  var d2=await r2.json();
  if(r2.ok)alert('OC creada: '+d2.numero_oc+'\nVisible en Compras > Ordenes');
  else alert('Error: '+(d2.error||''));
}
/* MEE en producción */
async function simularProduccion(){
  var prod=document.getElementById('prod-sel').value||document.getElementById('prod-manual').value.trim();
  var kg=parseFloat(document.getElementById('prod-kg').value);
  var panel=document.getElementById('prod-simul-result');
  if(!prod){panel.innerHTML='<span style="color:#e74c3c;">Selecciona un producto primero</span>';return;}
  if(!kg||kg<=0){panel.innerHTML='<span style="color:#e74c3c;">Ingresa la cantidad (kg) primero</span>';return;}
  panel.innerHTML='<span style="color:#667eea;">&#9203; Verificando stock y estimando costos...</span>';
  try{
    var _csrf = (typeof csrfTokenNec === 'function') ? csrfTokenNec() : (window._csrfTok || '');
    var r=await fetch('/api/produccion/simular',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':_csrf},body:JSON.stringify({producto:prod,cantidad_kg:kg})});
    var d=await r.json();
    if(!r.ok){panel.innerHTML='<span style="color:#e74c3c;">'+(d.error||'Error al simular')+'</span>';return;}
    var bg=d.factible?'#f0fff4':'#fff5f5';
    var brd=d.factible?'#28a745':'#dc3545';
    var ico=d.factible?'&#9989;':'&#10060;';
    var titulo=d.factible
      ?'Stock suficiente para '+d.cantidad_kg+'kg de '+d.producto
      :d.faltantes+' ingrediente(s) insuficiente(s) para producir '+d.cantidad_kg+'kg';
    var rows=d.ingredientes.map(function(i){
      var rowbg=i.suficiente?'':'#fff0f0';
      var badge=i.suficiente
        ?'<span style="color:#28a745;font-weight:700;">OK</span>'
        :'<span style="color:#dc3545;font-weight:700;">FALTA '+i.g_faltante.toLocaleString()+'g</span>';
      var costoCell=i.precio_kg>0
        ?'<span style="color:#2d3748;">$'+Number(i.costo).toLocaleString('es-CO')+'</span>'
        :'<span style="color:#a0aec0;font-size:0.8em;">sin precio</span>';
      return '<tr style="background:'+rowbg+';">'
        +'<td>'+i.material_nombre+'</td>'
        +'<td style="text-align:right;">'+i.g_requerido.toLocaleString()+'g</td>'
        +'<td style="text-align:right;">'+i.g_disponible.toLocaleString()+'g</td>'
        +'<td style="text-align:right;">'+badge+'</td>'
        +'<td style="text-align:right;">'+costoCell+'</td></tr>';
    }).join('');
    var costoHtml='';
    if(d.costo_total>0){
      costoHtml='<div style="margin-top:10px;padding:10px 14px;background:#eef2ff;border-radius:8px;display:flex;gap:20px;flex-wrap:wrap;align-items:center;">'
        +'<span>&#128176; <strong>Costo estimado batch:</strong> $'+Number(d.costo_total).toLocaleString('es-CO')+'</span>'
        +'<span>&#128197; <strong>Costo/kg:</strong> $'+Number(d.costo_por_kg).toLocaleString('es-CO')+'</span>'
        +(d.ingredientes_sin_precio>0?'<span style="color:#e67e22;font-size:0.85em;">&#9888; '+d.ingredientes_sin_precio+' ingrediente(s) sin precio — costo subestimado ('+d.cobertura_precio_pct+'% cobertura)</span>':'')
        +'</div>';
    } else if(d.ingredientes_sin_precio>0){
      costoHtml='<div style="margin-top:8px;padding:8px 12px;background:#fffbeb;border-radius:6px;font-size:0.84em;color:#b7791f;">&#9888; No hay precios de referencia. <a href="#" onclick="abrirPreciosMP();return false;">Configura precios por material</a> para ver costo estimado.</div>';
    }
    panel.innerHTML='<div style="background:'+bg+';border:2px solid '+brd+';border-radius:10px;padding:14px 16px;">'
      +'<strong style="color:'+brd+';font-size:1em;">'+ico+' '+titulo+'</strong>'
      +'<div style="overflow-x:auto;margin-top:10px;"><table class="table" style="font-size:0.85em;margin:0;">'
      +'<thead><tr><th>Material</th><th style="text-align:right;">Requerido</th>'
      +'<th style="text-align:right;">Disponible</th><th style="text-align:right;">Estado</th>'
      +'<th style="text-align:right;">Costo</th></tr></thead>'
      +'<tbody>'+rows+'</tbody></table></div>'
      +costoHtml
      +(d.factible?'<p style="margin:10px 0 0;font-size:0.85em;color:#555;">&#128994; Puedes registrar la produccion con seguridad.</p>'
        :'<p style="margin:10px 0 0;font-size:0.85em;color:#c0392b;">&#9888; Revisa el stock o genera OC de compra antes de producir.</p>')
      +'</div>';
    panel.scrollIntoView({behavior:'smooth'});
  }catch(e){panel.innerHTML='<span style="color:#e74c3c;">Error: '+e.message+'</span>';}
}
async function abrirPreciosMP(){
  /* Abre un modal para editar precios de referencia de MPs */
  var r=await fetch('/api/maestro-mps');
  var d=await r.json();
  var mps=d.mps||[];
  var rows=mps.map(function(m){
    var _nm=(m.nombre_inci||m.nombre_comercial||'')+((m.nombre_comercial&&m.nombre_inci&&m.nombre_comercial!==m.nombre_inci)?' <span style="color:#94a3b8;font-size:0.8em;">('+m.nombre_comercial+')</span>':'');
    return '<tr><td>'+m.codigo_mp+'</td><td>'+_nm+'</td>'
      +'<td><input type="number" step="0.01" min="0" value="'+(m.precio_referencia||0)+'" id="pr-'+m.codigo_mp+'" style="width:110px;padding:3px 6px;border:1px solid #ccc;border-radius:4px;"></td>'
      +'<td><button onclick="guardarPrecioMP(\''+m.codigo_mp+'\')" style="padding:3px 10px;font-size:0.8em;background:#6c5ce7;color:#fff;border:none;border-radius:4px;cursor:pointer;">Guardar</button></td></tr>';
  }).join('');
  var modal=document.createElement('div');
  modal.id='modal-precios-mp';
  modal.style.cssText='position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.55);z-index:9999;display:flex;align-items:center;justify-content:center;';
  modal.innerHTML='<div style="background:#fff;border-radius:12px;padding:24px;max-width:700px;width:95%;max-height:80vh;overflow-y:auto;">'
    +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">'
    +'<h3 style="margin:0;">&#128176; Precios de Referencia — Materias Primas</h3>'
    +'<button onclick="document.getElementById(\'modal-precios-mp\').remove()" style="background:none;border:none;font-size:1.4em;cursor:pointer;">&#10006;</button></div>'
    +'<p style="font-size:0.85em;color:#718096;margin:0 0 12px;">Precio por kg (usado para estimar costo de fórmulas). Fuente: última OC o manual.</p>'
    +'<div style="overflow-x:auto;"><table class="table" style="font-size:0.85em;">'
    +'<thead><tr><th>Código</th><th>Material</th><th>Precio/kg ($)</th><th></th></tr></thead>'
    +'<tbody>'+rows+'</tbody></table></div></div>';
  document.body.appendChild(modal);
  modal.addEventListener('click',function(e){if(e.target===modal)modal.remove();});
}
async function guardarPrecioMP(codigo){
  var inp=document.getElementById('pr-'+codigo);
  if(!inp)return;
  var precio=parseFloat(inp.value)||0;
  var r=await fetch('/api/maestro-mp/'+codigo+'/precio',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({precio_kg:precio,origen:'manual'})});
  var d=await r.json();
  if(d.ok){inp.style.background='#f0fff4';setTimeout(function(){inp.style.background='';},1500);}
  else alert('Error al guardar precio');
}

// Sebastian 5-may-2026 (Luis Enrique): popup centrado para "no se puede
// fabricar por falta de tal cosa". Imposible de ignorar · backdrop oscuro
// + tabla con MPs faltantes + acciones.
function _showStockInsuficientePopup(producto, cantidad_kg, faltantes){
  // Cerrar uno previo si existe
  var prev = document.getElementById('popup-stock-insuf');
  if(prev) prev.remove();
  var rows = (faltantes||[]).map(function(f){
    var nom = f.material || f.material_id || f.nombre || '?';
    var base = '<tr style="border-top:1px solid #fecaca;">'+
      '<td style="padding:8px 10px;font-weight:600;color:#1f2937;">'+nom+'</td>'+
      '<td style="padding:8px 10px;text-align:right;color:#475569;">'+
        (f.requerido_g||0).toLocaleString()+' g</td>'+
      '<td style="padding:8px 10px;text-align:right;color:#78716c;">'+
        (f.disponible_g||0).toLocaleString()+' g</td>'+
      '<td style="padding:8px 10px;text-align:right;font-weight:800;color:#dc2626;font-size:14px;">'+
        (f.falta_g||0).toLocaleString()+' g</td>'+
    '</tr>';
    // 2-jun-2026 · TRANSPARENCIA: stock RETENIDO (cuarentena, etc) del MISMO código.
    // Caso "bodega tiene 600g pero producción ve 17.5g" = el resto está sin liberar.
    if(f.retenido_g && f.retenido_g>0){
      var det=[]; var rpe=f.retenido_por_estado||{};
      Object.keys(rpe).forEach(function(k){ det.push((rpe[k]||0).toLocaleString()+' g en '+k); });
      base += '<tr style="background:#fff7ed"><td colspan="4" style="padding:6px 10px;font-size:11px;color:#9a3412;border-top:1px dashed #fed7aa">'+
        '&#9888; Hay <b>'+(f.retenido_g||0).toLocaleString()+' g</b> de este MP en bodega pero <b>NO disponible</b>: '+det.join(' · ')+'. '+
        'Si es CUARENTENA, <b>liberá el lote en Calidad</b> (control de calidad → aprobar) y volvé a producir.</td></tr>';
    }
    // código de fórmula ≠ código de bodega → mapeo cruzado (revisar mapeo)
    if(f.codigo_mp_formula && f.codigo_mp && f.codigo_mp_formula!==f.codigo_mp){
      base += '<tr style="background:#fef2f2"><td colspan="4" style="padding:5px 10px;font-size:10px;color:#7f1d1d">'+
        'Código fórmula <b>'+f.codigo_mp_formula+'</b> → bodega <b>'+f.codigo_mp+'</b>. Si no es el mismo material, revisá <b>/admin/formulas-mismapeo</b>.</td></tr>';
    }
    // FIX 1-jun-2026 · pista de MP duplicada con stock (mismo MP, otro código)
    if(f.pista){
      base += '<tr style="background:#fffbeb"><td colspan="4" style="padding:6px 10px;font-size:11px;color:#92400e;border-top:1px dashed #fde68a">'+
        '💡 Posible MP duplicada en bodega con stock: <b>'+(f.pista.nombre||'')+'</b> '+
        '(cód. '+(f.pista.codigo_mp||'')+') · <b>'+(f.pista.stock_g||0).toLocaleString()+' g</b> disponibles. '+
        'Parece el mismo material con otro código → unificá en <b>Bodega MP → Unificar MPs</b> '+
        '(o creá el puente fórmula↔bodega) y volvé a producir.</td></tr>';
    }
    return base;
  }).join('');
  var modal = document.createElement('div');
  modal.id = 'popup-stock-insuf';
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:99999;'+
    'display:flex;align-items:center;justify-content:center;padding:20px';
  modal.innerHTML =
    '<div style="background:#fff;border-radius:12px;max-width:640px;width:100%;'+
    'box-shadow:0 20px 60px rgba(0,0,0,0.3);overflow:hidden">'+
      // Header rojo de impacto
      '<div style="background:linear-gradient(135deg,#dc2626,#991b1b);color:#fff;padding:18px 24px">'+
        '<div style="display:flex;align-items:center;gap:12px">'+
          '<div style="font-size:32px">&#x274C;</div>'+
          '<div style="flex:1">'+
            '<div style="font-size:18px;font-weight:800">No se puede fabricar</div>'+
            '<div style="font-size:13px;opacity:0.9;margin-top:2px">Falta stock de '+
              faltantes.length+' materia'+(faltantes.length===1?'':'s')+' prima'+
              (faltantes.length===1?'':'s')+' &middot; <b>'+producto+'</b> &times; '+
              cantidad_kg+'kg</div>'+
          '</div>'+
        '</div>'+
      '</div>'+
      // Body con tabla
      '<div style="padding:18px 24px;max-height:50vh;overflow-y:auto">'+
        '<div style="font-size:13px;color:#475569;margin-bottom:12px">'+
          'No se descontó <u>nada</u> del inventario (transacción atómica abortó). '+
          'Una vez se reciba el faltante, podés volver a intentar.</div>'+
        '<table style="width:100%;border-collapse:collapse;font-size:13px;'+
          'background:#fff;border:1px solid #fecaca;border-radius:6px;overflow:hidden">'+
          '<thead><tr style="background:#fee2e2">'+
            '<th style="padding:10px;text-align:left;color:#7f1d1d;font-weight:700;font-size:12px">Materia prima</th>'+
            '<th style="padding:10px;text-align:right;color:#7f1d1d;font-weight:700;font-size:12px">Necesita</th>'+
            '<th style="padding:10px;text-align:right;color:#7f1d1d;font-weight:700;font-size:12px">Hay</th>'+
            '<th style="padding:10px;text-align:right;color:#7f1d1d;font-weight:700;font-size:12px">FALTA</th>'+
          '</tr></thead><tbody>'+rows+'</tbody></table>'+
      '</div>'+
      // Footer con acciones
      '<div style="background:#f8fafc;padding:14px 24px;display:flex;'+
        'gap:10px;justify-content:flex-end;border-top:1px solid #e2e8f0">'+
        '<button onclick="window.location.href=\'/compras\'" '+
          'style="background:#fff;color:#6d28d9;border:1px solid #6d28d9;border-radius:6px;'+
          'padding:8px 16px;font-size:13px;font-weight:600;cursor:pointer">'+
          '&#x1F6D2; Ir a Compras</button>'+
        '<button onclick="document.getElementById(\'popup-stock-insuf\').remove()" '+
          'style="background:#dc2626;color:#fff;border:none;border-radius:6px;'+
          'padding:8px 20px;font-size:13px;font-weight:700;cursor:pointer">'+
          'Entendido</button>'+
      '</div>'+
    '</div>';
  document.body.appendChild(modal);
  // Click fuera del modal cierra
  modal.addEventListener('click', function(e){
    if(e.target === modal) modal.remove();
  });
}

async function auditarFormulasHuerfanas(){
  try{
    var r = await fetch('/api/produccion/auditar-formulas-huerfanas');
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    var prods = d.productos || [];
    if(!prods.length){
      alert('✓ Sin codigo_mp huérfanos detectados · todas las fórmulas OK');
      return;
    }
    var existe = document.getElementById('modal-huerf');
    if(existe) existe.remove();
    var div = document.createElement('div');
    div.id = 'modal-huerf';
    div.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px';
    var html = '<div style="background:#fff;border-radius:14px;padding:24px;max-width:960px;width:100%;max-height:90vh;overflow-y:auto">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><h3 style="margin:0;color:#9a3412">🔧 Auditoría fórmulas con codigo_mp huérfanos</h3>';
    html += '<button id="huerf-close" style="background:none;border:none;font-size:1.4em;cursor:pointer">×</button></div>';
    html += '<div style="background:#fef3c7;color:#78350f;padding:12px;border-radius:8px;margin-bottom:14px;font-weight:700">⚠ '+(d.total_huerfanos||0)+' codigo_mp huérfanos en '+(d.productos_afectados_count||0)+' fórmula(s)</div>';
    html += '<table class="table" style="font-size:12px"><thead><tr><th>Producto</th><th>Huérfano</th><th>Reemplazo sugerido</th><th style="text-align:right">Stock g</th></tr></thead><tbody>';
    prods.forEach(function(p){
      p.cambios.forEach(function(ch, i){
        html += '<tr>';
        html += '<td>' + (i===0 ? '<b>'+_escHTML(p.producto)+'</b>' : '') + '</td>';
        html += '<td style="font-family:monospace;color:#dc2626">'+_escHTML(ch.huerfano.codigo)+' · '+_escHTML(ch.huerfano.nombre)+'</td>';
        html += '<td style="font-family:monospace;color:#16a34a;font-weight:700">'+_escHTML(ch.reemplazo.codigo)+' · '+_escHTML(ch.reemplazo.nombre)+'</td>';
        html += '<td style="text-align:right;font-weight:700">'+Number(ch.reemplazo.stock_g).toLocaleString()+'</td>';
        html += '</tr>';
      });
    });
    html += '</tbody></table>';
    html += '<div style="margin-top:14px;display:flex;gap:8px;justify-content:flex-end">';
    html += '<button id="huerf-aplicar" style="background:#9a3412;color:#fff;padding:10px 20px;border:none;border-radius:6px;font-weight:700;cursor:pointer">🔧 Aplicar TODAS las correcciones</button>';
    html += '</div></div>';
    div.innerHTML = html;
    document.body.appendChild(div);
    document.getElementById('huerf-close').onclick = function(){ var m = document.getElementById('modal-huerf'); if(m) m.remove(); };
    div.addEventListener('click', function(e){ if(e.target === div){ var m = document.getElementById('modal-huerf'); if(m) m.remove(); } });
    document.getElementById('huerf-aplicar').onclick = async function(){
      if(!confirm('Aplicar '+(d.total_huerfanos||0)+' correcciones masivamente?\n\nLos % NO se tocan · solo los material_id huérfanos se reemplazan por los candidatos con stock real.')) return;
      try{
        var ra = await fetch('/api/produccion/auto-reparar-todas', {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({dry_run: false}),
        });
        var da = await ra.json();
        if(!ra.ok){ alert('Error: '+(da.error||ra.status)); return; }
        alert('✓ '+da.mensaje+' · ahora las producciones encontrarán los lotes correctos');
        var m = document.getElementById('modal-huerf'); if(m) m.remove();
        if(typeof loadFormulas==='function') loadFormulas();
      }catch(e){ alert('Error red: '+e.message); }
    };
  }catch(e){ alert('Error red: '+e.message); }
}

async function diagnosticarFormulaActual(){
  var prod = (document.getElementById('prod-sel').value || document.getElementById('prod-manual').value || '').trim();
  if(!prod){ alert('Seleccioná un producto primero'); return; }
  return diagnosticarFormula(prod);
}
if(typeof document !== 'undefined' && !window._DIAG_FORM_DELEG){
  window._DIAG_FORM_DELEG = true;
  document.addEventListener('click', function(ev){
    var b = ev.target && ev.target.closest && ev.target.closest('[data-act-diag-form]');
    if(b){
      var prod = b.getAttribute('data-prod') || '';
      if(prod) diagnosticarFormula(prod);
      return;
    }
    var br = ev.target && ev.target.closest && ev.target.closest('[data-act-autorep-retry]');
    if(br){
      var prod2 = br.getAttribute('data-prod') || '';
      var kg2 = parseFloat(br.getAttribute('data-kg')) || 0;
      if(prod2) autoRepararYReintentar(prod2, kg2, br);
    }
  });
}
async function autoRepararYReintentar(prod, kg, btn){
  if(!confirm('Auto-reparar la fórmula de "'+prod+'" reemplazando codigo_mp huérfanos por los reales con stock · y luego reintentar registrar la producción?')) return;
  if(btn) btn.disabled = true;
  try{
    // 1) Apply auto-repair
    var ra = await fetch('/api/produccion/auto-reparar-formula/'+encodeURIComponent(prod), {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({dry_run: false}),
    });
    var da = await ra.json();
    if(!ra.ok){ alert('Error auto-repair: '+(da.error||ra.status)); if(btn) btn.disabled = false; return; }
    if(!(da.aplicados||[]).length){
      alert('Sin cambios aplicados · no se detectaron candidatos válidos.');
      if(btn) btn.disabled = false; return;
    }
    // 2) Recargar fórmulas para que el preview funcione si vuelve a usarse
    if(typeof loadFormulas==='function') await loadFormulas();
    // 3) Reintentar registro
    var msgEl = document.getElementById('prod-msg');
    if(msgEl) msgEl.innerHTML = '<div style="background:#dbeafe;color:#1e40af;padding:8px 12px;border-radius:6px;font-size:12px">✓ Fórmula auto-reparada ('+da.aplicados.length+' cambios) · reintentando registro…</div>';
    setTimeout(function(){
      if(typeof iniciarRegistroProd === 'function') iniciarRegistroProd();
    }, 600);
  }catch(e){ alert('Error red: '+e.message); if(btn) btn.disabled = false; }
}
async function diagnosticarFormula(producto){
  try{
    var r = await fetch('/api/produccion/diagnose/' + encodeURIComponent(producto));
    var d = await r.json();
    if(!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
    var existe = document.getElementById('modal-diag-form'); if(existe) existe.remove();
    var div = document.createElement('div');
    div.id = 'modal-diag-form';
    div.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px';
    var html = '<div style="background:#fff;border-radius:14px;padding:24px;max-width:920px;width:100%;max-height:90vh;overflow-y:auto">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><h3 style="margin:0;color:#7c3aed">🔍 Diagnóstico fórmula · '+_escHTML(producto)+'</h3>';
    html += '<button id="diag-close" style="background:none;border:none;font-size:1.4em;cursor:pointer">×</button></div>';
    var probTotal = 0;
    (d.diagnostico||[]).forEach(function(it){ probTotal += (it.problemas||[]).length; });
    if(probTotal === 0){
      html += '<div style="background:#dcfce7;color:#166534;padding:14px;border-radius:8px;font-weight:700">✓ Todos los ingredientes OK · sin problemas detectados</div>';
    } else {
      html += '<div style="background:#fef3c7;color:#78350f;padding:12px;border-radius:8px;margin-bottom:14px;font-weight:700">⚠ '+probTotal+' problema(s) detectado(s) · revisar abajo</div>';
      // Si hay MPs huérfanos (con similares), botón auto-reparar
      var huerfanos = (d.diagnostico||[]).filter(function(it){
        return (it.mps_similares_por_nombre||[]).length > 0;
      });
      if(huerfanos.length){
        html += '<div style="background:#fff7ed;border:1px solid #fb923c;padding:12px;border-radius:8px;margin-bottom:14px">';
        html += '<b style="color:#9a3412">🔧 Auto-reparar (admin)</b><br>';
        html += '<span style="font-size:12px;color:#7c2d12">Detectados '+huerfanos.length+' codigo_mp huérfanos con candidatos en catálogo. Click "Auto-reparar" para reemplazar en la fórmula (audit_log).</span><br>';
        html += '<button id="diag-autoreparar" data-prod="'+_escHTML(d.producto||'')+'" style="margin-top:8px;background:#9a3412;color:#fff;border:none;padding:8px 16px;border-radius:5px;font-weight:700;cursor:pointer">🔧 Auto-reparar fórmula</button>';
        html += '</div>';
      }
    }
    (d.diagnostico||[]).forEach(function(it){
      var hasIssue = (it.problemas||[]).length > 0;
      var bg = hasIssue ? '#fff7ed' : '#f8fafc';
      var border = hasIssue ? '#fb923c' : '#cbd5e1';
      html += '<div style="background:'+bg+';border:1px solid '+border+';border-radius:8px;padding:12px;margin-bottom:10px">';
      html += '<div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:8px">';
      html += '<div><b style="color:#0f172a">'+_escHTML(it.material_nombre||'')+'</b> <span style="font-family:monospace;color:#475569;font-size:12px">('+_escHTML(it.material_id||'')+')</span><br><span style="font-size:11px;color:#64748b">'+it.porcentaje+'% en fórmula</span></div>';
      html += '<div style="text-align:right;font-size:11px">'+
        '<div>Stock total con stock: <b>'+(it.stock_total_g||0).toLocaleString()+' g</b> ('+(it.lotes_con_stock||0)+' lotes)</div>'+
        '<div>FEFO disponible: <b style="color:'+(it.fefo_g>0?'#16a34a':'#dc2626')+'">'+(it.fefo_g||0).toLocaleString()+' g</b> ('+(it.fefo_disponibles||0)+' lotes usables)</div>'+
        '</div></div>';
      if((it.problemas||[]).length){
        html += '<ul style="margin:8px 0 4px;padding-left:18px;font-size:12px;color:#7f1d1d">';
        it.problemas.forEach(function(p){ html += '<li>'+_escHTML(p)+'</li>'; });
        html += '</ul>';
      }
      if((it.lotes_detalle||[]).length){
        html += '<details style="margin-top:6px"><summary style="cursor:pointer;font-size:11px;color:#475569">Ver lotes ('+it.lotes_detalle.length+')</summary>';
        html += '<table style="width:100%;font-size:11px;margin-top:4px;border-collapse:collapse">';
        html += '<thead><tr style="background:#e2e8f0"><th style="text-align:left;padding:3px 6px">Lote</th><th style="text-align:right;padding:3px 6px">Stock g</th><th style="padding:3px 6px">Estado</th></tr></thead><tbody>';
        it.lotes_detalle.forEach(function(l){
          var estCol = (l.estado_lote && /(cuarentena|rechazado)/i.test(l.estado_lote)) ? '#dc2626' : '#475569';
          html += '<tr><td style="padding:3px 6px;font-family:monospace">'+_escHTML(l.lote)+'</td><td style="text-align:right;padding:3px 6px">'+l.stock_g+'</td><td style="padding:3px 6px;color:'+estCol+'">'+_escHTML(l.estado_lote||'OK')+'</td></tr>';
        });
        html += '</tbody></table></details>';
      }
      if((it.mps_similares_por_nombre||[]).length){
        html += '<div style="margin-top:8px;padding:8px;background:#fef2f2;border-left:3px solid #dc2626;font-size:11px">';
        html += '<b style="color:#991b1b">🔥 MPs similares en catálogo (probable duplicado huérfano):</b><br>';
        it.mps_similares_por_nombre.forEach(function(s){
          html += '• <span style="font-family:monospace">'+_escHTML(s.codigo_mp)+'</span> · '+_escHTML(s.nombre_comercial)+' · INCI: '+_escHTML(s.nombre_inci||'—')+'<br>';
        });
        html += '<div style="margin-top:6px;color:#7f1d1d">→ Ir a Bodega MP → "Maestro" → "Detector de duplicados" → unificar (incluye actualización de fórmulas).</div>';
        html += '</div>';
      }
      html += '</div>';
    });
    html += '</div>';
    div.innerHTML = html;
    document.body.appendChild(div);
    document.getElementById('diag-close').onclick = function(){ var m = document.getElementById('modal-diag-form'); if(m) m.remove(); };
    div.addEventListener('click', function(e){ if(e.target === div){ var m = document.getElementById('modal-diag-form'); if(m) m.remove(); } });
    var arBtn = document.getElementById('diag-autoreparar');
    if(arBtn) arBtn.onclick = async function(){
      var prod = arBtn.getAttribute('data-prod');
      // 1) Dry-run preview
      try{
        var rp = await fetch('/api/produccion/auto-reparar-formula/'+encodeURIComponent(prod), {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({dry_run: true}),
        });
        var dp = await rp.json();
        if(!rp.ok){ alert('Error preview: '+(dp.error||rp.status)); return; }
        var cambios = dp.cambios_propuestos || [];
        if(!cambios.length){ alert('Sin cambios propuestos · no hay codigo_mp huérfanos con candidatos.'); return; }
        var preview = cambios.map(function(c){
          return '• '+c.huerfano.nombre+'\n  '+c.huerfano.codigo+' → '+c.reemplazo.codigo+' ('+c.reemplazo.stock_g+'g disponibles)';
        }).join('\n\n');
        if(!confirm('Aplicar '+cambios.length+' cambio(s) en la fórmula de "'+prod+'"?\n\n'+preview+'\n\nLos % NO se tocan · solo el material_id se reemplaza por el candidato con stock.')) return;
        // 2) Apply
        var ra = await fetch('/api/produccion/auto-reparar-formula/'+encodeURIComponent(prod), {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({dry_run: false}),
        });
        var da = await ra.json();
        if(!ra.ok){ alert('Error aplicando: '+(da.error||ra.status)); return; }
        alert('✓ '+da.mensaje+' · ahora reintentá registrar la producción');
        var m = document.getElementById('modal-diag-form'); if(m) m.remove();
        if(typeof loadFormulas==='function') loadFormulas();
      }catch(e){ alert('Error red: '+e.message); }
    };
  }catch(e){ alert('Error: '+e.message); }
}

async function cargarPendientesFab(){
  var banner = document.getElementById('fab-pendientes-banner');
  if(!banner) return;
  try{
    var r = await fetch('/api/produccion/pendientes-hoy');
    if(!r.ok){ banner.style.display='none'; return; }
    var d = await r.json();
    var items = d.items || [];
    if(!items.length){ banner.style.display='none'; return; }
    banner.style.display = 'block';
    var html = '<b style="font-size:14px">📋 Pendientes hoy según Programación · ' + items.length + ' lote(s)</b><div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:6px">';
    items.forEach(function(p){
      html += '<button data-fab-pend-prod="'+_escHTML(p.producto)+'" data-fab-pend-kg="'+p.kg+'" style="background:#fff;border:1px solid #ca8a04;color:#78350f;padding:4px 10px;border-radius:5px;font-size:11px;cursor:pointer">▶ '+_escHTML(p.producto)+' · '+p.kg+'kg</button>';
    });
    html += '</div>';
    banner.innerHTML = html;
  }catch(_){ banner.style.display='none'; }
}
if(typeof document !== 'undefined' && !window._FAB_PEND_DELEG){
  window._FAB_PEND_DELEG = true;
  document.addEventListener('click', function(ev){
    var b = ev.target && ev.target.closest && ev.target.closest('[data-fab-pend-prod]');
    if(!b) return;
    var prod = b.getAttribute('data-fab-pend-prod') || '';
    var kg = b.getAttribute('data-fab-pend-kg') || '';
    var sel = document.getElementById('prod-sel');
    var inp = document.getElementById('prod-kg');
    if(sel){
      // si el producto está en select, seleccionarlo
      var found = false;
      Array.from(sel.options).forEach(function(o){ if(o.value === prod){ sel.value = prod; found = true; } });
      if(!found){ var pm = document.getElementById('prod-manual'); if(pm) pm.value = prod; }
    }
    if(inp) inp.value = kg;
    if(typeof previewProd === 'function') previewProd();
    var pmsg = document.getElementById('prod-msg');
    if(pmsg) pmsg.innerHTML = '<div style="background:#dbeafe;color:#1e40af;padding:8px 12px;border-radius:6px;font-size:12px">📋 Pre-cargado de Programación: '+_escHTML(prod)+' · '+kg+'kg · Revisá y apretá ▶ Registrar Producción</div>';
  });
}

async function cargarAreasFab(){
  // Carga las áreas de FABRICACIÓN (puede_producir) en el desplegable del form.
  var sel=document.getElementById('prod-area'); if(!sel) return;
  try{
    var r=await fetch('/api/planta/areas',{credentials:'same-origin'});
    var d=await r.json(); var arr=(d&&(d.areas||d.items))||(Array.isArray(d)?d:[]);
    // Dedup por NOMBRE: FAB1/PROD1 (y FAB2/PROD2, FAB3/PROD3) son el MISMO cuarto físico con
    // códigos duplicados → mostrar "Fabricación 1" una sola vez (el plano ya los fusiona vía TWIN).
    var opts='<option value="">-- Selecciona área --</option>'; var _seenAr={};
    arr.filter(function(a){return a.puede_producir;}).forEach(function(a){
      var _k=(a.nombre||'').trim().toLowerCase(); if(_seenAr[_k]) return; _seenAr[_k]=1;
      opts+='<option value="'+a.id+'" data-codigo="'+_escHTML(a.codigo||'')+'">'+_escHTML(a.nombre)+'</option>';
    });
    sel.innerHTML=opts;
  }catch(e){}
}
async function iniciarRegistroProd(){
  var msgEl = document.getElementById('prod-msg');
  var prod=document.getElementById('prod-sel').value||document.getElementById('prod-manual').value;
  var kg=parseFloat(document.getElementById('prod-kg').value);
  if(!prod){
    if(msgEl) msgEl.innerHTML = '<div style="background:#fee2e2;color:#991b1b;padding:8px 12px;border-radius:6px;font-size:12px">❌ Seleccioná un producto (con fórmula) o escribí uno manual</div>';
    return;
  }
  if(!kg || kg<=0){
    if(msgEl) msgEl.innerHTML = '<div style="background:#fee2e2;color:#991b1b;padding:8px 12px;border-radius:6px;font-size:12px">❌ Ingresá cantidad en kg (mayor a 0)</div>';
    return;
  }
  var obs=document.getElementById('prod-obs').value;
  var pres=document.getElementById('prod-presentacion').value;
  var _selAr=document.getElementById('prod-area');
  var areaCod=(_selAr&&_selAr.selectedOptions&&_selAr.selectedOptions[0]?(_selAr.selectedOptions[0].getAttribute('data-codigo')||''):'');
  var loteIn=((document.getElementById('prod-lote')||{}).value||'').trim();
  if(!pres || !pres.trim()){
    if(!confirm('⚠ Sin presentación · los rótulos saldrán incompletos. ¿Continuar sin presentación?')) return;
  }
  try{
    var _csrf2 = (typeof csrfTokenNec === 'function') ? csrfTokenNec() : (window._csrfTok || '');
    var r=await fetch('/api/produccion',{method:'POST',credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':_csrf2},
      body:JSON.stringify({producto:prod,cantidad_kg:kg,observaciones:obs,presentacion:pres,operador:OPER_ACTUAL,area_codigo:areaCod,lote:loteIn})});
    var d=await r.json();
    if(!r.ok){
      // Sebastian 5-may-2026 (Luis Enrique): popup + detalle inline.
      // Antes solo decia "Stock insuficiente" generico y Luis tenia que
      // adivinar. Ahora popup explicito + tabla detallada en pantalla.
      if(d.faltantes && d.faltantes.length){
        // Popup tipo modal centrado · imposible de ignorar
        _showStockInsuficientePopup(prod, kg, d.faltantes);
      } else {
        // Otros errores (sin formula, validacion, etc.) → alert nativo
        // CRÍTICO 20-may-2026: incluir tipo + detalle + status code para
        // diagnóstico inmediato cuando Sebastián reporte fallas.
        var detTxt = '';
        if(d.tipo) detTxt += '\n\nTipo: ' + d.tipo;
        if(d.detalle) detTxt += '\n\nDetalle: ' + d.detalle;
        if(d.origen) detTxt += '\n\nOrigen: ' + d.origen;
        if(d.rollback) detTxt += '\n\nRollback: ' + d.rollback;
        if(!detTxt && d){ try{ detTxt = '\n\nResp: ' + JSON.stringify(d).substring(0,500); }catch(_){} }
        alert('No se puede registrar producción\n\nHTTP '+r.status+': '+(d.error||'Error desconocido')+
              detTxt+'\n\nReporta este texto a soporte.');
        // También log en consola para devtools
        console.error('[registrar-produccion] HTTP', r.status, d);
      }
      // Tambien mostrar detalle inline (para historial visual)
      var html='<div style="background:#fee2e2;border:1px solid #dc2626;border-radius:8px;padding:12px 16px;color:#7f1d1d;">';
      html+='<b style="font-size:14px;">&#x274C; '+(d.error||'Error registrando produccion')+'</b>';
      // Si hubo MPs faltantes · botón diagnóstico para auto-detectar duplicados
      if(d.faltantes && d.faltantes.length){
        // 21-may-2026: si auto_repair_candidatos > 0, mostrar botón de
        // auto-repair PROMINENTE arriba del diagnóstico · arregla en 1 clic.
        if(d.auto_repair_disponible && (d.auto_repair_candidatos||[]).length){
          html+='<div style="margin-top:10px;background:#fff7ed;border:2px solid #fb923c;border-radius:8px;padding:10px 14px">';
          html+='<b style="color:#9a3412;font-size:13px">🔥 Codigo_mp huérfano detectado · auto-reparable</b><br>';
          html+='<span style="font-size:11px;color:#7c2d12">Tu fórmula apunta a un código sin stock, pero existe el MISMO material con otro código que SÍ tiene lotes:</span><br>';
          d.auto_repair_candidatos.forEach(function(ar){
            html+='<div style="margin-top:4px;font-size:12px;color:#7c2d12">• <b>'+_escHTML(ar.huerfano.nombre)+'</b>: <span style="font-family:monospace">'+_escHTML(ar.huerfano.codigo)+'</span> → <span style="font-family:monospace;color:#16a34a;font-weight:700">'+_escHTML(ar.reemplazo.codigo)+'</span> ('+Number(ar.reemplazo.stock_g).toLocaleString()+'g disponibles)</div>';
          });
          html+='<button data-act-autorep-retry data-prod="'+_escHTML(prod)+'" data-kg="'+kg+'" style="margin-top:10px;background:#9a3412;color:#fff;border:none;padding:8px 18px;border-radius:6px;font-size:13px;font-weight:700;cursor:pointer">🔧 Auto-reparar Y reintentar registro</button>';
          html+='</div>';
        }
        html+='<div style="margin-top:8px"><button data-act-diag-form data-prod="'+_escHTML(prod)+'" style="background:#7c3aed;color:#fff;border:none;padding:6px 14px;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer">🔍 Diagnosticar fórmula</button> <span style="font-size:11px;color:#7f1d1d">← ver detalle completo</span></div>';
      }
      if(d.faltantes && d.faltantes.length){
        html+='<div style="margin-top:8px;font-size:13px;">No se descontó nada (transacción atómica abortó).</div>';
        html+='<div style="margin-top:8px;font-size:12px;font-weight:700;color:#991b1b;">MPs faltantes:</div>';
        html+='<table style="width:100%;font-size:12px;margin-top:4px;border-collapse:collapse;">';
        html+='<thead><tr style="background:#fecaca;"><th style="text-align:left;padding:4px 8px;">Material</th><th style="text-align:right;padding:4px 8px;">Necesita</th><th style="text-align:right;padding:4px 8px;">Hay</th><th style="text-align:right;padding:4px 8px;">FALTA</th></tr></thead><tbody>';
        d.faltantes.forEach(function(f){
          html+='<tr style="border-top:1px solid #fecaca;">';
          html+='<td style="padding:4px 8px;">'+(f.material||f.material_id||'?')+'</td>';
          html+='<td style="padding:4px 8px;text-align:right;">'+(f.requerido_g||0).toLocaleString()+' g</td>';
          html+='<td style="padding:4px 8px;text-align:right;color:#78716c;">'+(f.disponible_g||0).toLocaleString()+' g</td>';
          html+='<td style="padding:4px 8px;text-align:right;font-weight:700;color:#dc2626;">'+(f.falta_g||0).toLocaleString()+' g</td>';
          html+='</tr>';
        });
        html+='</tbody></table>';
        html+='<div style="margin-top:8px;font-size:11px;color:#7f1d1d;">&#x2192; Verifica entradas en <b>Bodega MP</b> o crea OC en <b>/compras</b>.</div>';
      } else if(d.detalle){
        html+='<div style="margin-top:6px;font-size:12px;">'+d.detalle+'</div>';
      }
      html+='</div>';
      document.getElementById('prod-msg').innerHTML=html;
      return;
    }
    var html='<div class="alert-success">'+(d.message||'Produccion registrada')+' &mdash; Lote: <strong>'+d.lote+'</strong></div>';
    if(d.descuentos&&d.descuentos.length){
      html+='<div style="margin-top:8px;font-size:0.88em;color:#555;"><strong>MPs descontadas:</strong><ul style="margin-top:4px;padding-left:18px;">';
      d.descuentos.forEach(function(mp){html+='<li>'+mp.material+': '+mp.cantidad_g.toLocaleString()+'g</li>';});
      html+='</ul></div>';
    }
    html+='<div style="margin-top:8px;padding:8px 14px;background:#e8f4fd;border-radius:6px;font-size:0.85em;color:#1a4a7a;">';
    html+='&#8594; Ve a <strong>Acondicionamiento</strong> para registrar cada presentacion, descontar MEE y crear Stock PT.</div>';
    document.getElementById('prod-msg').innerHTML=html;
    document.getElementById('prod-preview').style.display='none';
    document.getElementById('prod-sel').value='';
    document.getElementById('prod-manual').value='';
    document.getElementById('prod-kg').value='';
    document.getElementById('prod-obs').value='';
    cargarHistProd();
    // Sprint Fabricación PRO 20-may-2026: mensaje PERSISTENTE (no auto-hide).
    // Antes desaparecía a 10s · si Sebastián no lo veía perdía el lote.
    // Ahora queda hasta que el usuario lo cierre o registre otra producción.
  }catch(e){document.getElementById('prod-msg').innerHTML='<span style="color:red;">Error: '+e.message+'</span>';}
}

window.onload=function(){/* Data loads after operator confirms name */};
async function mostrarFormNuevaMP(){
  var panel=document.getElementById('ing-nueva-mp');
  if(panel){ panel.style.display='block'; panel.scrollIntoView({behavior:'smooth',block:'nearest'}); }
  // Sebastian 8-may-2026: auto-rellenar código MP con el siguiente
  // consecutivo · evitar que el user adivine y duplique.
  var codInput=document.getElementById('nmp-cod');
  if(codInput && !codInput.value){
    codInput.value='⏳ Calculando...';
    codInput.disabled=true;
    try{
      var r=await fetch('/api/maestro-mps/next-codigo');
      var d=await r.json();
      if(r.ok && d.siguiente){
        codInput.value=d.siguiente;
        var hint=document.getElementById('nmp-cod-hint');
        if(hint){
          hint.textContent='Auto-asignado · último: '+(d.ultimo||'(ninguno)')+
                           ' · catálogo: '+d.total_en_catalogo+' MPs';
        }
      } else {
        codInput.value='';
        codInput.placeholder='MP00350 (auto-fetch falló · escribí manual)';
      }
    }catch(e){
      codInput.value='';
      codInput.placeholder='MP00350';
    } finally {
      codInput.disabled=false;
    }
  }
}
function ocultarFormNuevaMP(){
  var panel=document.getElementById('ing-nueva-mp');
  if(panel) panel.style.display='none';
  ['nmp-cod','nmp-inci','nmp-nombre','nmp-tipo','nmp-prov'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.value='';
  });
  var ns=document.getElementById('nmp-smin'); if(ns) ns.value='500';
  var nm=document.getElementById('nmp-msg'); if(nm) nm.innerHTML='';
  var hint=document.getElementById('nmp-cod-hint'); if(hint) hint.textContent='';
}
async function crearNuevaMP(){
  var cod=(document.getElementById('nmp-cod').value||'').toUpperCase().trim();
  var inci=(document.getElementById('nmp-inci').value||'').trim();
  var nombre=(document.getElementById('nmp-nombre').value||'').trim();
  if(!cod||!nombre){alert('Codigo y Nombre Comercial son obligatorios');return;}
  var tipoMatEl=document.getElementById('nmp-tipo-mat');
  var tipoMaterial=tipoMatEl ? (tipoMatEl.value || 'MP') : 'MP';
  var data={codigo_mp:cod,nombre_inci:inci,nombre_comercial:nombre,
    tipo:(document.getElementById('nmp-tipo').value||'').trim(),
    tipo_material:tipoMaterial,
    proveedor:(document.getElementById('nmp-prov').value||'').trim(),
    stock_minimo:parseFloat(document.getElementById('nmp-smin').value)||500};
  // Sebastián 9-may-2026: si hay cantidad > 0 en el bloque "Primer ingreso",
  // tras crear el catálogo registramos el movimiento de Entrada en la misma
  // acción · evita que el usuario tenga que cerrar este form y rellenar el
  // de abajo (era el bug de UX).
  var ingCant = parseFloat((document.getElementById('nmp-ing-cant')||{}).value)||0;
  var ingLote = ((document.getElementById('nmp-ing-lote')||{}).value||'').trim();
  var ingVence = ((document.getElementById('nmp-ing-vence')||{}).value||'').trim();
  var ingEst = ((document.getElementById('nmp-ing-est')||{}).value||'').trim();
  var ingPos = ((document.getElementById('nmp-ing-pos')||{}).value||'').trim();
  var ingPrecioKg = parseFloat((document.getElementById('nmp-ing-precio-kg')||{}).value)||0;
  var ingCuar = !!((document.getElementById('nmp-ing-cuarentena')||{}).checked);

  var msgEl = document.getElementById('nmp-msg');
  msgEl.innerHTML = '<div style="color:#666">⏳ Creando...</div>';
  try{
    var r=await fetch('/api/maestro-mps',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':window._csrfTok||''},body:JSON.stringify(data)});
    var res=await r.json();
    if(!r.ok){
      msgEl.innerHTML='<div class="alert-error">'+(res.error||'Error al crear catálogo')+'</div>';
      return;
    }
    _cat[cod]=data;  // Agregar al catalogo local
    // Pre-llenar el formulario de ingreso (compat con flow viejo)
    var f={'ing-cod':cod,'ing-inci':inci,'ing-nombre':nombre,'ing-tipo':data.tipo,'ing-prov':data.proveedor};
    Object.keys(f).forEach(function(id){var el=document.getElementById(id);if(el)el.value=f[id];});

    if(ingCant > 0){
      // Registrar también el primer ingreso (movimiento Entrada)
      msgEl.innerHTML='<div style="color:#666">⏳ MP creada · registrando entrada...</div>';
      // Auto-generar lote si está vacío (formato corto: PROV-YYMMDD)
      var loteFinal = ingLote;
      if(!loteFinal){
        var d2=new Date();
        var ymd = String(d2.getFullYear()).slice(2)+String(d2.getMonth()+1).padStart(2,'0')+String(d2.getDate()).padStart(2,'0');
        var provPrefix = (data.proveedor||'AUTO').replace(/[^A-Z]/gi,'').slice(0,4).toUpperCase()||'AUTO';
        loteFinal = provPrefix+ymd;
      }
      // 6-jun-2026: el primer ingreso de MP nueva ahora va por /api/recepcion
      // (igual que la recepción de MP existente) para soportar CUARENTENA. Si
      // cuarentena=true → estado_lote=CUARENTENA + notifica a Calidad. Si va a
      // cuarentena y no se indicó estante, lo dejamos en el estante "CUARENTENA".
      var estCuar = ingEst || (ingCuar ? 'CUARENTENA' : '');
      var recPayload = {
        codigo_mp: cod,
        nombre_comercial: nombre,
        nombre_inci: inci,
        cantidad: ingCant,
        observaciones: 'Primer ingreso al crear MP en catálogo' + (ingPrecioKg>0 ? ' · $'+ingPrecioKg.toLocaleString('es-CO')+'/kg' : ''),
        lote: loteFinal,
        fecha_vencimiento: ingVence||'',
        estanteria: estCuar,
        posicion: ingPos,
        proveedor: data.proveedor||'',
        precio_kg: ingPrecioKg||0,
        cuarentena: ingCuar,
        operador: (typeof OPER_ACTUAL !== 'undefined' ? OPER_ACTUAL : '') || ''
      };
      var rm = await fetch('/api/recepcion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(recPayload)});
      var resm={};try{resm=await rm.json();}catch(e){}
      if(!rm.ok){
        msgEl.innerHTML='<div class="alert-error">MP creada pero el ingreso falló: '+(resm.error||rm.status)+'. Podés reintentar el ingreso desde el form de abajo.</div>';
        var st=document.getElementById('ing-status'); if(st){st.textContent='MP creada · completa el ingreso abajo';st.style.color='#e67e22';}
        return;
      }
      msgEl.innerHTML='<div class="alert-success">✓ MP <b>'+cod+'</b> creada en catálogo · ingreso registrado: lote <b>'+loteFinal+'</b> con <b>'+ingCant.toLocaleString('es-CO')+' g</b>'+(ingCuar?' · <span style="color:#e65100;font-weight:700">🔒 EN CUARENTENA (pendiente Calidad)</span>':'')+'.</div>';
      // Refrescar el stock visible si la pantalla lo permite
      try{ if(typeof loadStock==='function') setTimeout(loadStock, 600); }catch(e){}
      try{ if(typeof cargarHistIngreso==='function') setTimeout(cargarHistIngreso, 600); }catch(e){}
      // Limpiar inputs del bloque ingreso para próxima vez
      ['nmp-ing-lote','nmp-ing-cant','nmp-ing-vence','nmp-ing-est','nmp-ing-pos','nmp-ing-precio-kg'].forEach(function(id){
        var el=document.getElementById(id); if(el) el.value='';
      });
    } else {
      msgEl.innerHTML='<div class="alert-success">✓ MP '+cod+' creada en catálogo. Si la quieres ingresar, completa cantidad / lote / posición arriba y vuelve a presionar.</div>';
      var st=document.getElementById('ing-status'); if(st){st.textContent='Nueva MP creada y lista para ingresar';st.style.color='#28a745';}
    }
  }catch(e){msgEl.innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}

// ── Funciones CC / Trazabilidad / Conteo Ciclico ──
async function cargarModoInventario(){
  try{
    var r=await fetch('/api/inventario/modo-inventario');
    var d=await r.json().catch(function(){return {};});
    var activo=!!d.activo;
    window._RECEPCION_AUTO_VIGENTE=activo;
    var ctrl=document.getElementById('modo-inv-ctrl');
    var est=document.getElementById('modo-inv-estado');
    var btn=document.getElementById('btn-modo-inv');
    var banner=document.getElementById('cuar-inv-banner');
    var esAdmin=(window._ES_ADMIN_DASH===true);
    if(ctrl) ctrl.style.display = esAdmin ? 'flex' : 'none';
    if(est) est.innerHTML = activo ? '<span style="color:#0d9488">ACTIVO &middot; recepciones directo a inventario</span>' : '<span style="color:#9a3412">apagado &middot; cuarentena INVIMA</span>';
    if(btn) btn.textContent = activo ? 'Apagar modo inventario' : 'Activar modo inventario';
    if(banner) banner.style.display = activo ? 'block' : 'none';
    if(activo){ ['ing-cuarentena','nmp-ing-cuarentena'].forEach(function(cid){var cb=document.getElementById(cid); if(cb) cb.checked=false;}); }
  }catch(e){}
}
async function toggleModoInventario(){
  var nuevo = !window._RECEPCION_AUTO_VIGENTE;
  if(nuevo && !confirm('Activar MODO INVENTARIO? Las recepciones nuevas entraran directo a inventario, SIN cuarentena de Calidad. Usalo solo durante el inventario y apagalo al terminar.')) return;
  var btn=document.getElementById('btn-modo-inv'); if(btn){btn.disabled=true;}
  try{
    var r=await fetch('/api/inventario/modo-inventario',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({activo:nuevo})});
    var d=await r.json().catch(function(){return {};});
    if(!r.ok||!d.ok){ alert('No se pudo cambiar: '+(d.error||r.status)); }
  }catch(e){ alert('Error: '+e); }
  if(btn){btn.disabled=false;}
  cargarModoInventario();
}
async function liberarCuarentenaInventario(){
  if(!confirm('Liberar a inventario TODOS los lotes que están en cuarentena (pasan a VIGENTE/disponible)? Acción del día de inventario · queda auditada.')) return;
  var btn=document.getElementById('btn-liberar-inv');
  if(btn){btn.disabled=true;btn.textContent='Liberando...';}
  try{
    var r=await fetch('/api/lotes/cuarentena/liberar-inventario',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
    var d=await r.json().catch(function(){return {};});
    var msg=document.getElementById('cuar-msg');
    if(!r.ok||!d.ok){
      if(msg) msg.innerHTML='<div class="alert-error">No se pudo liberar: '+(d.error||r.status)+'</div>';
    }else{
      if(msg) msg.innerHTML='<div class="alert-success">&#9989; '+(d.liberados||0)+' lote(s) liberados a inventario.</div>';
      if(typeof cargarCuarentena==='function') cargarCuarentena();
      if(typeof cargarRetenido==='function') cargarRetenido();
    }
  }catch(e){
    var m2=document.getElementById('cuar-msg'); if(m2) m2.innerHTML='<div class="alert-error">Error: '+e+'</div>';
  }
  if(btn){btn.disabled=false;btn.innerHTML='&#9989; Liberar TODO a inventario';}
}
async function cargarCuarentena(){
  try{
    var r=await fetch('/api/lotes/cuarentena');
    var data=await r.json();
    var tb=document.getElementById('cuar-tbody');
    if(!data.length){tb.innerHTML='<tr><td colspan="10" style="text-align:center;color:#999;padding:20px;">Sin lotes pendientes de revision QC</td></tr>';return;}
    var h='';
    data.forEach(function(l){
      // BUG-4 fix · 20-may-2026 Dashboard PRO audit: leer el placeholder
      // es_admin que core.py:444 inyecta desde ADMIN_USERS de config.
      // Antes la lista hardcoded incluía 'hernando' que NO es admin →
      // la UI le pintaba botones que el backend rechazaba con 403.
      var esAdmin=(window._ES_ADMIN_DASH===true);
      var estadoColor=l.estado_lote==='CUARENTENA'?'#e67e22':l.estado_lote==='CUARENTENA_EXTENDIDA'?'#c0392b':'#888';
      h+='<tr>';
      h+='<td style="font-family:monospace;font-size:0.85em;">'+l.codigo_mp+'</td>';
      h+='<td style="font-weight:600;">'+(l.nombre_inci||l.nombre||'')+'</td>';
      h+='<td style="font-size:0.78em;color:#888;">'+(l.nombre||'')+'</td>';
      h+='<td style="font-family:monospace;font-weight:600;">'+l.lote+'</td>';
      h+='<td style="text-align:right;font-weight:600;">'+l.cantidad.toLocaleString()+'</td>';
      h+='<td style="font-size:0.85em;">'+(l.proveedor||'')+'</td>';
      h+='<td style="font-size:0.82em;">'+(l.numero_oc||'')+'</td>';
      h+='<td style="font-size:0.82em;">'+l.fecha.substring(0,10)+'</td>';
      h+='<td><span style="background:'+estadoColor+'20;color:'+estadoColor+';padding:2px 8px;border-radius:10px;font-size:0.8em;font-weight:700;">'+l.estado_lote.replace('_',' ')+'</span></td>';
      h+='<td>';
      if(esAdmin){
        h+='<button onclick="abrirCCReview(JSON.parse(this.dataset.lote))" data-lote="'+JSON.stringify(l).replace(/"/g,'&quot;')+'" style="padding:5px 12px;background:#6d28d9;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:0.82em;font-weight:600;">Revisar CC</button>';
      }else{
        h+='<span style="color:#999;font-size:0.82em;">Solo CC/Admin</span>';
      }
      h+='</td></tr>';
    });
    tb.innerHTML=h;
  }catch(e){console.error(e);}
}

// Lotes NO disponibles (rechazado/vencido/bloqueado) con saldo fisico · trazabilidad INVIMA
async function cargarRetenido(){
  try{
    var r=await fetch('/api/lotes/retenido');
    var data=await r.json();
    var tb=document.getElementById('ret-tbody');
    if(!tb)return;
    if(!Array.isArray(data)||!data.length){tb.innerHTML='<tr><td colspan="9" style="text-align:center;color:#999;padding:18px;">Sin material retenido con saldo</td></tr>';return;}
    var colores={'RECHAZADO':'#dc2626','VENCIDO':'#d97706','BLOQUEADO':'#6b7280'};
    var h='';
    data.forEach(function(l){
      var est=(l.estado_lote||'').toUpperCase();
      var col=colores[est]||'#888';
      h+='<tr>';
      h+='<td style="font-family:monospace;font-size:0.85em;">'+(l.codigo_mp||'')+'</td>';
      h+='<td style="font-weight:600;">'+(l.nombre_inci||l.nombre||'')+'</td>';
      h+='<td style="font-size:0.78em;color:#888;">'+(l.nombre||'')+'</td>';
      h+='<td style="font-family:monospace;font-weight:600;">'+(l.lote||'')+'</td>';
      h+='<td style="text-align:right;font-weight:600;">'+Number(l.cantidad||0).toLocaleString()+'</td>';
      h+='<td style="font-size:0.85em;">'+(l.proveedor||'')+'</td>';
      h+='<td style="font-size:0.82em;">'+(l.numero_oc||'')+'</td>';
      h+='<td style="font-size:0.82em;">'+((l.fecha_vencimiento||'')+'').substring(0,10)+'</td>';
      h+='<td><span style="background:'+col+'20;color:'+col+';padding:2px 8px;border-radius:10px;font-size:0.8em;font-weight:700;">'+est+'</span></td>';
      h+='</tr>';
    });
    tb.innerHTML=h;
  }catch(e){console.error(e);}
}

function abrirCCModal(lote){
  _ccLoteActual=lote;
  document.getElementById('cc-modal-lote').textContent=lote.lote+' -- '+lote.nombre;
  document.getElementById('cc-firmante').textContent=OPER_ACTUAL;
  document.getElementById('cc-lote-info').innerHTML=
    '<div><b>Codigo:</b> '+lote.codigo_mp+'</div>'+
    '<div><b>INCI:</b> '+(lote.nombre_inci||'--')+'</div>'+
    '<div><b>Cantidad:</b> '+Number(lote.cantidad).toLocaleString()+' g</div>'+
    '<div><b>Proveedor:</b> '+(lote.proveedor||'--')+'</div>'+
    '<div><b>Factura:</b> '+(lote.numero_factura||'--')+'</div>'+
    '<div><b>OC:</b> '+(lote.numero_oc||'--')+'</div>';
  ['cc-coa-ok','cc-lote-coincide','cc-coa-vigente','cc-ficha-ok','cc-muestra-ret'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.checked=false;
  });
  ['cc-solub-ok','cc-solub-fail','cc-aql-ok','cc-aql-fail','cc-aql-ext'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.checked=false;
  });
  document.getElementById('cc-aql-obs').value='';
  document.getElementById('cc-obs-final').value='';
  var _ef=document.getElementById('cc-est-final'); if(_ef)_ef.value='';
  var _pf=document.getElementById('cc-pos-final'); if(_pf)_pf.value='';
  document.getElementById('cc-modal-msg').innerHTML='';
  document.getElementById('cc-modal').style.display='flex';
}

function cerrarCCModal(){
  document.getElementById('cc-modal').style.display='none';
  _ccLoteActual=null;
}

// Firma electrónica Part 11 §11.200 · re-autenticación (password + MFA si aplica)
// y emisión de signature_id sobre el movimiento. Devuelve {signature_id} o {error}.
async function _firmarLoteEsign(meaning, recordId){
  var pwd=prompt('FIRMA ELECTRÓNICA (21 CFR Part 11)\n\nIngresá tu contraseña para firmar la disposición del lote ('+meaning+'):');
  if(!pwd){return null;}
  var totp=prompt('Si tenés MFA activo, ingresá el código de 6 dígitos.\nSi no usás MFA, dejá vacío y presioná OK.')||'';
  try{
    var rc=await fetch('/api/sign/challenge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pwd,totp_token:totp})});
    var dc=await rc.json();
    if(!rc.ok){return {error:dc.error||'Credenciales inválidas'};}
    var rs=await fetch('/api/sign',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record_table:'movimientos',record_id:String(recordId),meaning:meaning,challenge_token:dc.token})});
    var ds=await rs.json();
    if(!rs.ok){return {error:ds.error||'Error al firmar'};}
    return {signature_id:ds.signature_id};
  }catch(e){return {error:'Error de red al firmar: '+e.message};}
}

// ═══ Runner EBR · reemplazo MyBatch · Sebastián 2-jun-2026 ═══
// Firma electrónica generalizada (cualquier record_table) · Part 11.
async function _firmarEsign(meaning, table, recordId){
  var pwd=prompt('Firma electrónica (21 CFR Part 11) · contraseña para firmar ('+meaning+'):');
  if(!pwd){return null;}
  var totp=prompt('Código MFA de 6 dígitos (si no usás MFA, dejá vacío y OK):')||'';
  try{
    var rc=await fetch('/api/sign/challenge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pwd,totp_token:totp})});
    var dc=await rc.json();
    if(!rc.ok){return {error:dc.error||'Credenciales inválidas'};}
    var rs=await fetch('/api/sign',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record_table:table,record_id:String(recordId),meaning:meaning,challenge_token:dc.token})});
    var ds=await rs.json();
    if(!rs.ok){return {error:ds.error||'Error al firmar'};}
    return {signature_id:ds.signature_id};
  }catch(e){return {error:'Error de red al firmar'};}
}
function _ebrBadge(est){
  var c={iniciado:'#f59e0b',en_proceso:'#3b82f6',completado:'#8b5cf6',liberado:'#16a34a',rechazado:'#dc2626'}[est]||'#64748b';
  return '<span style="background:'+c+';color:#fff;border-radius:10px;padding:2px 8px;font-size:10px;">'+(est||'')+'</span>';
}
function ebrSetFase(btn){
  window._ebrFase=btn.getAttribute('data-fase')||'';
  var btns=document.querySelectorAll('#ebr-fase-tabs .ebr-fbtn');
  for(var i=0;i<btns.length;i++){
    var on=(btns[i]===btn);
    btns[i].style.background=on?'#6d28d9':'#fff';
    btns[i].style.color=on?'#fff':'#6d28d9';
  }
  cargarEBRs();
}
async function cargarEBRs(){
  var cont=document.getElementById('ebr-list');
  if(!cont){return;}
  var fase=window._ebrFase||'';
  cont.innerHTML='<span style="color:#999;">Cargando…</span>';
  try{
    var url='/api/brd/ebr'+(fase?('?fase='+encodeURIComponent(fase)):'');
    var r=await fetch(url,{credentials:'same-origin'});
    var d=await r.json();
    var items=(d&&d.items)||[];
    if(!items.length){
      cont.innerHTML='<div style="background:#faf8ff;border:1px dashed #c4b5fd;border-radius:8px;padding:14px;font-size:13px;color:#555;">'+
        '<b>No hay legajos'+(fase?(' en fase '+fase):'')+' todavía.</b><br>'+
        'El batch record nace cuando hay un MBR aprobado y se acepta una producción (o lo creás a mano).<br>'+
        '<div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">'+
        '<button onclick="ebrGenerarMBR()" style="background:#6d28d9;color:#fff;border:none;border-radius:6px;padding:7px 12px;cursor:pointer;">1) Generar MBR desde fórmula</button>'+
        '<a href="/brd" target="_blank"><button type="button" style="background:#0891b2;color:#fff;border:none;border-radius:6px;padding:7px 12px;cursor:pointer;">2) Revisar y aprobar MBR (/brd)</button></a>'+
        '<button onclick="ebrNuevoLegajo()" style="background:#16a34a;color:#fff;border:none;border-radius:6px;padding:7px 12px;cursor:pointer;">3) ➕ Nuevo legajo</button>'+
        '</div></div>';
      return;
    }
    var em={fabricacion:'🏭',envasado:'📦',acondicionamiento:'🔧'};
    var h='<table class="table" style="font-size:12px;"><thead><tr><th>N° OP</th><th>Lote</th><th>Fase</th><th>Estado</th><th></th></tr></thead><tbody>';
    for(var i=0;i<items.length;i++){
      var it=items[i];var fa=it.fase||'fabricacion';
      h+='<tr><td>'+(it.numero_op||('#'+it.id))+'</td><td>'+(it.lote||'')+'</td><td>'+(em[fa]||'')+' '+fa+'</td><td>'+_ebrBadge(it.estado)+'</td><td style="text-align:right;"><button onclick="abrirEBR('+it.id+')" style="background:#6d28d9;color:#fff;border:none;border-radius:5px;padding:5px 10px;font-size:11px;cursor:pointer;">▶ Abrir</button></td></tr>';
    }
    h+='</tbody></table>';
    cont.innerHTML=h;
  }catch(e){cont.innerHTML='<div style="color:#c0392b;">Error cargando legajos.</div>';}
}
var _ebrTarget='ebr-runner';
async function _ebrJson(url){ try{ var r=await fetch(url,{credentials:'same-origin'}); if(!r.ok) return {}; return await r.json(); }catch(e){ return {}; } }
function ebrCerrarRunner(){var b=document.getElementById(_ebrTarget);if(b){b.style.display='none';b.innerHTML='';}}
async function abrirEBR(id, targetId){
  if(targetId) _ebrTarget=targetId;   // 25-jun · runner inline en Fabricación (#encurso-runner) o en Históricos (#ebr-runner)
  var box=document.getElementById(_ebrTarget);
  if(!box){return;}
  box.style.display='block';
  box.innerHTML='<span style="color:#999;">Cargando legajo…</span>';
  try{
    var r=await fetch('/api/brd/ebr/'+id,{credentials:'same-origin'});
    var d=await r.json();
    if(!r.ok){box.innerHTML='<div style="color:#c0392b;">'+(d.error||'Error')+'</div>';return;}
    // 25-jun PERF · todos los sub-recursos en PARALELO (antes 11 fetches en serie = ~1-2s de latencia)
    var _arr=function(x){return (x&&x.items)?x.items:(Array.isArray(x)?x:[]);};
    var P=await Promise.all([
      _ebrJson('/api/brd/ebr/'+id+'/pesajes-plan'),
      _ebrJson('/api/brd/ebr/'+id+'/conciliacion-material'),
      _ebrJson('/api/brd/ebr/'+id+'/artes'),
      _ebrJson('/api/brd/ebr/'+id+'/observaciones'),
      (d.mbr_template_id?_ebrJson('/api/brd/mbr/'+d.mbr_template_id+'/ipc-specs'):Promise.resolve({})),
      _ebrJson('/api/brd/ebr/'+id+'/ipc-resultados'),
      _ebrJson('/api/brd/ebr/'+id+'/ipc-estandar'),
      _ebrJson('/api/brd/ebr/'+id+'/despeje'),
      _ebrJson('/api/brd/ebr/'+id+'/precauciones'),
      _ebrJson('/api/brd/ebr/'+id+'/registros-fisicos'),
      _ebrJson('/api/brd/ebr/'+id+'/despeje-items')
    ]);
    var dp=P[0],dcm=P[1],dar=P[2],dob=P[3];
    var ipcSpecs=_arr(P[4]),ipcRes=_arr(P[5]),ipcEstandar=_arr(P[6]);
    var despeje=_arr(P[7]),prec=_arr(P[8]),regs=_arr(P[9]),despejeChk=P[10]||{};
    box.innerHTML=_ebrRender(d,(dp&&dp.items)||[],(dcm&&dcm.items)||[],(dar&&dar.items)||[],(dob&&dob.items)||[],ipcSpecs,ipcRes,despeje,prec,regs,ipcEstandar,despejeChk);
    if((d.fase||'fabricacion')==='envasado'){ try{ cargarEnvasesPlan(id); }catch(_e){} }  // Fase 3 · llena la sección de presentaciones
    if((d.fase||'fabricacion')==='acondicionamiento'){ try{ acondAddMat(id); }catch(_e){} }  // OA · siembra 1 fila de material
    box.scrollIntoView({behavior:'smooth',block:'start'});
  }catch(e){box.innerHTML='<div style="color:#c0392b;padding:8px">No se pudo abrir el legajo: '+_escHTML((e&&e.message)?e.message:String(e))+'</div>';}
}
function _ebrRender(d, pesajes, conc, artes, obs, ipcSpecs, ipcRes, despeje, prec, regs, ipcEstandar, despejeChk){
  ipcEstandar=ipcEstandar||[]; despejeChk=despejeChk||{};
  ipcSpecs=ipcSpecs||[]; ipcRes=ipcRes||[]; despeje=despeje||[]; prec=prec||[]; regs=regs||[];
  var editable=(d.estado==='iniciado'||d.estado==='en_proceso');
  var em={fabricacion:'🏭',envasado:'📦',acondicionamiento:'🔧'};
  var fa=d.fase||'fabricacion';
  var _dt=function(s){return s?String(s).replace('T',' ').slice(0,16):'';};
  var _kv=function(lbl,val){return '<div><div style="font-size:10px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:.3px">'+lbl+'</div><div style="font-size:12px;color:#1e293b;font-weight:600;margin-top:2px;line-height:1.35">'+((val||val===0)&&val!==''?val:'<span style="color:#cbd5e1">—</span>')+'</div></div>';};
  var loteBtn=editable?(' <button onclick="ebrAsignarLoteFisico('+d.id+",'"+(d.lote||'')+"'"+')" title="Asignar el lote físico/comercial real" style="background:#ddd6fe;color:#4c1d95;border:none;border-radius:4px;padding:1px 6px;font-size:9px;cursor:pointer;">✏️</button>'):'';
  var prodMl=(d.cantidad_real_g?((d.cantidad_real_g)+' Gr'+(d.ml_envasable?(' - '+d.ml_envasable+' mL'):'')):'');
  // Encabezado estilo MyBatch · INSTRUCCIONES DE MANUFACTURA
  var h='<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;border-bottom:1px solid #e4e4e7;padding-bottom:10px;margin-bottom:12px">';
  h+='<div><div style="font-weight:800;color:#6d28d9;font-size:12px;letter-spacing:.6px">'+(em[fa]||'')+' INSTRUCCIONES DE MANUFACTURA</div>';
  h+='<div style="font-weight:800;color:#1e293b;font-size:17px;margin-top:4px">'+(d.numero_op||('EBR #'+d.id))+'</div>';
  if(d.producto_nombre){ h+='<div style="font-weight:600;color:#334155;font-size:13px;margin-top:1px">'+_escHTML(d.producto_nombre)+'</div>'; }
  h+='</div>';
  var _loteDoss=encodeURIComponent(d.lote_codigo||d.lote||'');
  h+='<div style="display:flex;flex-direction:column;gap:5px;align-items:flex-end"><a href="/api/brd/ebr/'+d.id+'/pdf" target="_blank" style="background:#dc2626;color:#fff;border-radius:5px;padding:5px 12px;font-size:11px;text-decoration:none;font-weight:700">📄 Descargar</a><a href="/api/planta/dossier-lote/'+_loteDoss+'" target="_blank" title="Expediente completo del lote: producción + envasado + micro + MP consumidas" style="background:#6d28d9;color:#fff;border-radius:5px;padding:5px 12px;font-size:11px;text-decoration:none;font-weight:700">📦 Dossier lote</a><button onclick="verLoteFases(&#39;'+_loteDoss+'&#39;)" title="Ver Fabricación + Envasado + Acondicionamiento de este lote juntos" style="background:#7c3aed;color:#fff;border:none;border-radius:5px;padding:5px 12px;font-size:11px;cursor:pointer;font-weight:700">🔗 Lote completo</button><button onclick="ebrCerrarRunner()" style="background:#94a3b8;color:#fff;border:none;border-radius:5px;padding:5px 10px;font-size:11px;cursor:pointer;">Cerrar ✕</button></div></div>';
  // Grilla de datos de la orden (como MyBatch)
  h+='<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:11px 18px;background:#fafafa;border:1px solid #f1f5f9;border-radius:10px;padding:13px 15px;margin-bottom:10px">';
  h+=_kv('N° de Lote Bulk', _escHTML(d.lote||'')+loteBtn);
  h+=_kv('Cantidad Ordenada', (d.cantidad_objetivo_g||0)+' Gr');
  h+=_kv('Área o Línea', _escHTML(d.area_nombre||''));
  h+=_kv('Fecha Inicio', _dt(d.iniciado_at_utc));
  h+=_kv('Fecha Final', _dt(d.completado_at_utc||d.liberado_at_utc));
  h+=_kv('Estado Actual', _ebrBadge(d.estado));
  h+=_kv('Cant. Producida/Aprobada', prodMl);
  h+=_kv('Densidad', d.densidad_g_ml?(d.densidad_g_ml+' g/mL'):'');
  h+=_kv('Rendimiento', (d.yield_pct!=null&&d.yield_pct!=='')?(d.yield_pct+'%'):'');
  h+=_kv('Elaborado por', _escHTML(d.iniciado_por||'')+(d.iniciado_at_utc?(' · '+_dt(d.iniciado_at_utc)):''));
  h+=_kv('Aprobado por (Calidad)', _escHTML(d.liberado_por||'')+(d.liberado_at_utc?(' · '+_dt(d.liberado_at_utc)):''));
  h+=_kv('Observaciones', _escHTML(d.notas||''));
  h+='</div>';
  // ── Rol del usuario · la vista se adapta (segregación de funciones GMP) ──
  var miRol=d.mi_rol||{tipo:'consulta',rol:'Consulta',realiza:false,verifica:false};
  var _rc=({operario:'#16a34a',jefe_produccion:'#2563eb',calidad:'#0891b2',director_tecnico:'#7c3aed',aseguramiento:'#b45309',administrativo:'#64748b',admin:'#6d28d9',consulta:'#94a3b8'})[miRol.tipo]||'#94a3b8';
  var _tareas=[];
  if(editable&&miRol.realiza){
    var _dp=(((despejeChk&&despejeChk.dispensacion)||[]).concat((despejeChk&&despejeChk.fabricacion)||[])).filter(function(it){return it.cumple!==1;}).length;
    if(_dp)_tareas.push('Marcar '+_dp+' verificación(es) de despeje');
    var _pw=(pesajes||[]).filter(function(p){return !(p.pesado_por||'').trim();}).length;
    if(_pw)_tareas.push('Pesar '+_pw+' materia(s) prima(s)');
    var _pp=(d.pasos||[]).filter(function(s){return s.estado==='pendiente'||s.estado==='en_proceso';}).length;
    if(_pp)_tareas.push('Ejecutar '+_pp+' paso(s) de fabricación');
  }
  if(editable&&miRol.verifica){
    var _dvend=(((despejeChk&&despejeChk.dispensacion)||[]).concat((despejeChk&&despejeChk.fabricacion)||[])).filter(function(it){return it.cumple===1&&!(it.verificado_por||'').trim();}).length;
    if(_dvend)_tareas.push('Verificar '+_dvend+' ítem(s) de despeje');
    var _pv=(pesajes||[]).filter(function(p){return (p.pesado_por||'').trim()&&!(p.verificado_por||'').trim();}).length;
    if(_pv)_tareas.push('Verificar '+_pv+' pesaje(s)');
    var _iv=(ipcSpecs||[]).filter(function(sp){return !(ipcRes||[]).some(function(r){return r.ipc_spec_id===sp.id;});}).length;
    if(_iv)_tareas.push('Reportar '+_iv+' control(es) IPC');
  }
  h+='<div style="display:flex;align-items:center;gap:11px;background:'+_rc+'14;border:1px solid '+_rc+'55;border-radius:12px;padding:11px 14px;margin-bottom:14px;flex-wrap:wrap">';
  h+='<span style="display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:50%;background:'+_rc+';color:#fff;font-size:17px">&#128100;</span>';
  h+='<div><div style="font-size:9px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:.4px">Estás en este legajo como</div><div style="font-size:14px;font-weight:800;color:'+_rc+'">'+_escHTML(miRol.rol||'Usuario')+'</div></div>';
  if(editable){
    h+='<div style="margin-left:auto;min-width:180px;text-align:right">';
    if(_tareas.length){
      h+='<div style="font-size:11px;font-weight:800;color:'+_rc+';margin-bottom:2px">&#9203; TU TRABAJO &middot; '+_tareas.length+' pendiente(s)</div>';
      _tareas.forEach(function(t){h+='<div style="font-size:11px;color:#475569">&bull; '+t+'</div>';});
    } else if(miRol.realiza||miRol.verifica){
      h+='<div style="font-size:12px;font-weight:700;color:#16a34a">&#10003; Sin tareas pendientes para tu rol</div>';
    } else {
      h+='<div style="font-size:11px;color:#94a3b8">Solo lectura (administrativo)</div>';
    }
    h+='</div>';
  }
  h+='</div>';
  // ── Secciones numeradas en tarjetas premium (estilo MyBatch) ──
  var _cn=0;
  function _secOpen(titulo){
    _cn++;
    return '<div style="background:#fff;border:1px solid #ececf0;border-radius:14px;box-shadow:0 1px 2px rgba(24,24,27,.04),0 6px 22px rgba(24,24,27,.05);padding:16px 18px;margin:0 0 14px"><div style="display:flex;align-items:center;gap:10px;margin-bottom:12px"><span style="display:inline-flex;align-items:center;justify-content:center;min-width:26px;height:26px;padding:0 6px;border-radius:8px;background:linear-gradient(135deg,#a78bfa,#6d28d9);color:#fff;font-weight:800;font-size:13px;box-shadow:0 2px 6px rgba(109,40,217,.3)">'+_cn+'</span><div style="font-size:14px;font-weight:800;color:#1e293b;letter-spacing:.2px">'+titulo+'</div></div>';
  }
  // 1 · Precauciones + equipos
  h+=_secOpen('⚠️ Precauciones y equipos');
  if(prec.length){
    h+='<ul style="font-size:12px;margin:4px 0 0;padding-left:18px;">';
    for(var pi=0;pi<prec.length;pi++){var pp2=prec[pi];h+='<li><b>'+(pp2.tipo==='equipo'?'🔧 ':'⚠️ ')+'</b>'+(pp2.descripcion||'')+' <span style="color:#999;font-size:11px;">· '+(pp2.registrado_por||'')+'</span></li>';}
    h+='</ul>';
  } else {h+='<div style="color:#999;font-size:12px;">Sin precauciones/equipos registrados.</div>';}
  if(editable){h+='<div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;"><button onclick="ebrAgregarPrecaucion('+d.id+',\'precaucion\')" style="background:#f59e0b;color:#fff;border:none;border-radius:5px;padding:5px 10px;font-size:11px;cursor:pointer;">+ Precaución</button><button onclick="ebrAgregarPrecaucion('+d.id+',\'equipo\')" style="background:#0891b2;color:#fff;border:none;border-radius:5px;padding:5px 10px;font-size:11px;cursor:pointer;">+ Equipo</button></div>';}
  // Despeje de línea · checklist 13 ítems × 2 etapas (MyBatch §2 Dispensación + §4 Fabricación)
  function _despEtapa(titulo, etapa, items){
    var oh=''; titulo=titulo;
    items=items||[];
    var done=items.filter(function(it){return it.cumple===1;}).length;
    var verif=items.filter(function(it){return (it.verificado_por||'').trim();}).length;
    var allOk=items.length>0 && done===items.length;
    var allVer=items.length>0 && verif===items.length;
    var pctR=items.length?Math.round(done/items.length*100):0;
    var pctV=items.length?Math.round(verif/items.length*100):0;
    // Doble barra · regla 2 personas: Realizó (Operario) + Verificó (Calidad)
    oh+='<div style="display:flex;gap:14px;margin-bottom:9px;font-size:11px">';
    oh+='<div style="flex:1"><div style="color:#64748b;font-weight:700;margin-bottom:2px">Realizó · Operario &middot; '+done+'/'+items.length+(allOk?' ✓':'')+'</div><div style="height:6px;background:#f1f5f9;border-radius:99px;overflow:hidden"><div style="height:100%;width:'+pctR+'%;background:'+(allOk?'#16a34a':'#a78bfa')+'"></div></div></div>';
    oh+='<div style="flex:1"><div style="color:#64748b;font-weight:700;margin-bottom:2px">Verificó · Calidad &middot; '+verif+'/'+items.length+(allVer?' ✓':'')+'</div><div style="height:6px;background:#f1f5f9;border-radius:99px;overflow:hidden"><div style="height:100%;width:'+pctV+'%;background:'+(allVer?'#16a34a':'#0ea5e9')+'"></div></div></div>';
    oh+='</div>';
    // Sebastián 7-jul (v3): tiempo de respuesta de Calidad (aviso → 1ª verificación) · una vez, en Dispensación.
    if(etapa==='dispensacion'){
      if(d.despeje_respuesta_min!=null){ oh+='<div style="margin:0 0 8px;font-size:11px;color:#166534;background:#dcfce7;border-radius:6px;padding:5px 10px;display:inline-block">&#9201; Calidad respondió en <b>'+d.despeje_respuesta_min+' min</b> (aviso &rarr; 1ª verificación)</div>'; }
      else if(d.despeje_espera_min!=null){ oh+='<div style="margin:0 0 8px;font-size:11px;color:#92400e;background:#fef3c7;border-radius:6px;padding:5px 10px;display:inline-block">&#9201; <b>'+d.despeje_espera_min+' min</b> desde el aviso &middot; esperando 1ª verificaci\u00f3n de Calidad</div>'; }
    }
    oh+='<table class="table" style="font-size:11px"><thead><tr><th style="text-align:left">Verificación</th><th style="text-align:center">Realizó</th><th style="text-align:center">Verificó</th></tr></thead><tbody>';
    items.forEach(function(it){
      var rz;
      // Sebastián 7-jul (v2): el operario VA HACIENDO sin trabarse (sin lock); al marcar, se AVISA a Calidad
      // para que esté al lado verificando (el backend manda la notificación a la campana). Sin "marcar todo".
      if(it.cumple===1){ rz='<span style="color:#16a34a;font-weight:700">✓ Sí</span>'+(it.registrado_por?('<div style="font-size:9px;color:#94a3b8">'+_escHTML(it.registrado_por)+'</div>'):''); }
      else if(it.cumple===0){ rz='<span style="color:#dc2626;font-weight:700">✗ No</span>'; }
      else if(editable&&miRol.realiza){ rz='<button onclick="ebrMarcarDespeje('+d.id+','+it.idx+',&#39;'+etapa+'&#39;)" style="background:#16a34a;color:#fff;border:none;border-radius:4px;padding:2px 9px;font-size:10px;cursor:pointer">✓ Sí</button>'; }
      else { rz='<span style="color:#94a3b8">pendiente</span>'; }
      var vf;
      if((it.verificado_por||'').trim()){ vf='<span style="color:#16a34a;font-weight:700">✓</span><div style="font-size:9px;color:#94a3b8">'+_escHTML(it.verificado_por)+'</div>'; }
      else if(it.cumple===1&&editable&&miRol.verifica){ vf='<button onclick="ebrVerificarDespeje('+d.id+','+it.idx+',&#39;'+etapa+'&#39;)" style="background:#0ea5e9;color:#fff;border:none;border-radius:4px;padding:2px 9px;font-size:10px;cursor:pointer">Verificar</button>'; }
      else if(it.cumple===1){ vf='<span style="color:#f59e0b;font-size:10px">&#9203; espera Calidad</span>'; }
      else { vf='<span style="color:#cbd5e1">—</span>'; }
      oh+='<tr><td style="font-size:10px;line-height:1.3">'+_escHTML(it.texto)+'</td><td style="text-align:center;white-space:nowrap;vertical-align:top">'+rz+'</td><td style="text-align:center;white-space:nowrap;vertical-align:top">'+vf+'</td></tr>';
    });
    oh+='</tbody></table>';
    // Sebastián 7-jul: SIN "Marcar TODO / Verificar TODO" — el despeje es SECUENCIAL (operario marca un ítem →
    // Calidad lo verifica → se habilita el siguiente) para asegurar que alguien supervisa CADA paso (GMP/INVIMA).
    if(editable&&(miRol.realiza||miRol.verifica)){ oh+='<div style="margin-top:6px;font-size:10px;color:#94a3b8">&#8505; Secuencial: el operario marca un ítem, Calidad lo verifica y se habilita el siguiente.</div>'; }
    if(editable&&miRol.realiza){ oh+=' <button onclick="ebrAgregarRegistroFisico('+d.id+',&#39;Rotulo limpieza '+etapa+'&#39;)" title="Adjuntar foto del rótulo de limpieza diligenciado" style="margin-top:6px;margin-left:6px;background:#fff;border:1px solid #cbd5e1;border-radius:5px;padding:6px 11px;font-size:11px;cursor:pointer">&#128247; Foto rótulo limpieza</button>'; }
    if(editable&&!miRol.realiza&&!miRol.verifica){ oh+='<div style="margin-top:6px;font-size:11px;color:#94a3b8">Solo lectura</div>'; }
    return oh;
  }
  var _dch=despejeChk||{};
  // ENVASADO 26-jun · las secciones de MP (despeje dispensación, pesaje, ajustes, despeje fabricación)
  // SOLO aplican a FABRICACIÓN. En envasado/acondicionamiento no hay pesaje de MP → se ocultan. El balance
  // de </div> se mantiene: el </div> que abre la sección de Pasos cierra Precauciones cuando este bloque se salta.
  if(fa==='fabricacion'){
  h+='</div>'+_secOpen('🧹 Despeje de Línea · Dispensación')+_despEtapa('Despeje de Línea · Dispensación', 'dispensacion', _dch.dispensacion);
  // 3 · Dispensado de Materias Primas (pesaje · 2ª firma)
  h+='</div>'+_secOpen('⚖️ Dispensado de Materias Primas');
  if(!pesajes.length){h+='<div style="color:#999;font-size:12px;">Esta fórmula no tiene materias primas cargadas.</div>';}
  else{
    var _pesados=pesajes.filter(function(p){return (p.pesado_por||'').trim();}).length;
    h+='<div style="font-size:11px;color:#64748b;font-weight:700;margin-bottom:6px">'+_pesados+'/'+pesajes.length+' materias primas pesadas</div>';
    h+='<table class="table" style="font-size:12px;"><thead><tr><th>Material</th><th style="text-align:right;">%</th><th>N° lote</th><th style="text-align:right;">% pureza</th><th style="text-align:right;">Teórico g</th><th style="text-align:right;">Real g</th><th>Pesó</th><th>Verificó</th><th></th></tr></thead><tbody>';
    for(var i=0;i<pesajes.length;i++){
      var p=pesajes[i];
      var pesado=(p.pesado_por||'').trim();
      var verif=(p.verificado_por||'').trim();
      var verifCell=verif?('<span style="color:#16a34a;font-weight:700;">✓ '+verif+'</span>'):(pesado?'<span style="color:#f59e0b;">pendiente</span>':'<span style="color:#cbd5e1;">—</span>');
      var acc='<span style="color:#999;">—</span>';
      if(!pesado){
        if(editable&&miRol.realiza){ acc='<button onclick="ebrPesarMp('+d.id+',&#39;'+(p.material_id||'')+'&#39;,'+(p.cantidad_teorica_g||0)+')" style="background:#16a34a;color:#fff;border:none;border-radius:5px;padding:4px 12px;font-size:11px;font-weight:700;cursor:pointer;">Pesar</button>'; }
        else { acc='<span style="color:#f59e0b;font-size:11px;">&#9203; falta pesar</span>'; }
      } else if(!verif){
        if(editable&&miRol.verifica){ acc='<button onclick="ebrVerificarPesaje('+d.id+','+p.id+')" style="background:#0ea5e9;color:#fff;border:none;border-radius:5px;padding:4px 9px;font-size:11px;cursor:pointer;">Verificar</button>'; }
        else { acc='<span style="color:#f59e0b;font-size:11px;">&#9203; espera Calidad</span>'; }
      }
      var _pctv=(p.porcentaje!=null?p.porcentaje:(d.cantidad_objetivo_g>0?((p.cantidad_teorica_g||0)/d.cantidad_objetivo_g*100):null));
      var _foto=(pesado&&editable&&miRol.realiza)?(' <button onclick="ebrAgregarRegistroFisico('+d.id+',&#39;Rotulo pesaje '+(p.material_id||'')+'&#39;)" title="Adjuntar foto del rótulo de pesaje (MyBatch)" style="background:#fff;border:1px solid #cbd5e1;border-radius:4px;padding:2px 6px;font-size:12px;cursor:pointer">&#128247;</button>'):'';
      h+='<tr style="'+(pesado?'':'background:#fffbeb')+'"><td>'+_escHTML(p.material_nombre||p.material_id||'')+'</td><td style="text-align:right;">'+(_pctv!=null?parseFloat(Number(_pctv).toFixed(3)):'—')+'</td><td style="font-family:monospace;font-size:11px">'+_escHTML(p.lote_mp||'—')+'</td><td style="text-align:right;">100</td><td style="text-align:right;">'+(p.cantidad_teorica_g!=null?Number(p.cantidad_teorica_g).toLocaleString("es-CO"):'—')+'</td><td style="text-align:right;font-weight:'+(pesado?'700':'400')+'">'+(p.cantidad_real_g!=null?Number(p.cantidad_real_g).toLocaleString("es-CO"):'<span style="color:#cbd5e1">&mdash;</span>')+'</td><td style="font-size:10px">'+_escHTML(pesado||'—')+'</td><td>'+verifCell+'</td><td style="text-align:right;white-space:nowrap;">'+acc+_foto+'</td></tr>';
    }
    h+='</tbody></table>';
  }
  h+='<div style="margin-top:14px;font-size:12px;font-weight:700;color:#6d28d9;">Ajustes de Materias Primas</div>';
  var _adj=d.ajustes_mp||[];
  if(_adj.length){
    h+='<table class="table" style="font-size:11px"><thead><tr><th>Materia prima</th><th style="text-align:right">Cantidad</th><th>Motivo</th><th>Por</th></tr></thead><tbody>';
    _adj.forEach(function(aj){ h+='<tr><td>'+_escHTML(aj.material||'')+'</td><td style="text-align:right">'+(aj.cantidad_g||0)+' g</td><td>'+_escHTML(aj.motivo||'')+'</td><td style="font-size:10px">'+_escHTML(aj.registrado_por||'')+'</td></tr>'; });
    h+='</tbody></table>';
  } else { h+='<div style="color:#94a3b8;font-size:12px;">Sin registro de ajustes de materia prima.</div>'; }
  if(editable&&miRol.realiza){ h+='<button onclick="ebrAgregarAjusteMp('+d.id+')" style="margin-top:6px;background:#d97706;color:#fff;border:none;border-radius:5px;padding:6px 12px;font-size:11px;font-weight:700;cursor:pointer">+ Registrar ajuste de MP</button>'; }
  // 4 · Despeje de Línea · Fabricación (tras dispensar/pesar)
  h+='</div>'+_secOpen('🧹 Despeje de Línea · Fabricación')+_despEtapa('Despeje de Línea · Fabricación', 'fabricacion', _dch.fabricacion);
  } // fin if(fa==='fabricacion') · secciones de MP solo en fabricación
  // 5 · Pasos del proceso (Realizó + Verificó QC) · título por fase
  h+='</div>'+_secOpen(fa==='envasado'?'📦 Envasado':(fa==='acondicionamiento'?'🎁 Acondicionamiento':'📋 Fabricación / Mezcla'));
  var pasos=d.pasos||[];
  if(!pasos.length){h+='<div style="color:#999;font-size:12px;">Este MBR no tiene pasos.</div>';}
  else{
    h+='<table class="table" style="font-size:12px;"><thead><tr><th>#</th><th>Actividad</th><th>Estado</th><th>Realizó por</th><th>Verificó por</th><th></th></tr></thead><tbody>';
    for(var j=0;j<pasos.length;j++){
      var s=pasos[j];var acc2='<span style="color:#999;">'+(s.estado==='completado'?'✓':'—')+'</span>';
      if(editable&&miRol.realiza){
        if(s.estado==='pendiente'){acc2='<button onclick="ebrIniciarPaso('+d.id+','+s.orden+')" style="background:#f59e0b;color:#fff;border:none;border-radius:5px;padding:4px 9px;font-size:11px;cursor:pointer;">Iniciar</button>';}
        else if(s.estado==='en_proceso'){acc2='<button onclick="ebrCompletarPaso('+d.id+','+s.orden+','+s.id+','+(s.requiere_e_sign?1:0)+','+(s.requiere_qc?1:0)+')" style="background:#16a34a;color:#fff;border:none;border-radius:5px;padding:4px 9px;font-size:11px;cursor:pointer;">Completar</button>';}
      }
      var qcTag=s.requiere_qc?' <span title="requiere 2ª firma QC" style="color:#0ea5e9;font-weight:700;">◆QC</span>':'';
      var _res=(s.observaciones||'').trim();
      var _rdt=s.completado_at_utc?String(s.completado_at_utc).replace('T',' ').slice(0,16):'';
      h+='<tr style="vertical-align:top"><td style="font-weight:800;color:#6d28d9">'+s.orden+'</td>'+
         '<td><div style="font-size:11px;line-height:1.4">'+_escHTML(s.descripcion||'')+qcTag+'</div>'+(_res?('<div style="margin-top:4px;font-size:11px;background:#f5f3ff;border-radius:5px;padding:3px 8px;display:inline-block"><b style="color:#6d28d9">Resultado:</b> '+_escHTML(_res)+'</div>'):'')+'</td>'+
         '<td>'+_ebrBadge(s.estado)+'</td>'+
         '<td style="font-size:11px">'+_escHTML(s.operario_username||'')+(_rdt?('<div style="font-size:9px;color:#94a3b8">'+_rdt+'</div>'):'')+'</td>'+
         '<td style="font-size:11px">'+_escHTML(s.qc_username||'')+'</td>'+
         '<td style="text-align:right;">'+acc2+'</td></tr>';
    }
    h+='</tbody></table>';
  }
  // IPC · Controles en proceso (spec del MBR + resultado del EBR) · MyBatch ⑤
  // ENVASADO Fase 3 (26-jun) · unidades por presentación + cerrar/descontar envases (gated a envasado ·
  // se llena lazy con cargarEnvasesPlan desde abrirEBR · balance </div>: la sección IPC de abajo lo cierra).
  if(fa==='envasado'){ h+='</div>'+_secOpen('📦 Presentaciones envasadas · unidades y descuento de envases')+'<div id="env-pres-'+d.id+'" style="font-size:12px;color:#64748b">Cargando&hellip;</div>'; }
  // ACONDICIONAMIENTO (27-jun · huecos #2/#3) · materiales consumidos + cierre canónico (movimientos_mee · CAS).
  if(fa==='acondicionamiento'){
    h+='</div>'+_secOpen('🎁 Materiales de acondicionamiento · cierre y descuento');
    var _adesc=(String(d.envases_descontados_at||'').trim()!=='')||['completado','liberado','rechazado'].indexOf(String(d.estado||'').toLowerCase())>=0;
    if(_adesc){ h+='<div style="font-size:12px;color:#16a34a">&#10003; Acondicionamiento cerrado &middot; materiales descontados.</div>'; }
    else if(editable&&miRol.realiza){
      h+='<div style="font-size:11px;color:#64748b;margin-bottom:6px">List&aacute; los materiales consumidos (etiquetas, estuches, insertos&hellip;) y cerr&aacute; para descontarlos del inventario.</div>';
      h+='<div id="acond-mat-rows-'+d.id+'"></div>';
      h+='<button onclick="acondAddMat('+d.id+')" style="background:#fff;border:1px solid #c4b5fd;color:#6d28d9;border-radius:6px;padding:5px 12px;font-size:12px;cursor:pointer;margin:4px 0">&#43; material</button><br>';
      h+='<button onclick="ebrCerrarAcond('+d.id+')" style="margin-top:8px;background:#6d28d9;color:#fff;border:none;border-radius:6px;padding:8px 18px;font-size:13px;font-weight:700;cursor:pointer">&#128274; Cerrar acondicionamiento y descontar</button>';
    } else { h+='<div style="font-size:12px;color:#94a3b8">Solo el ejecutor puede registrar y cerrar el acondicionamiento.</div>'; }
  }
  h+='</div>'+_secOpen('🔬 Controles en Proceso (IPC)');
  if(!ipcSpecs.length){h+='<div style="color:#999;font-size:12px;">Este MBR no tiene IPCs definidos. Agregalos en /brd (specs del MBR).</div>';}
  else{
    var resBySpec={}; ipcRes.forEach(function(rr){resBySpec[rr.ipc_spec_id]=rr;});
    h+='<table class="table" style="font-size:12px;"><thead><tr><th>Parámetro</th><th>Rango/Spec</th><th>Resultado</th><th>Conf.</th><th>Midió</th><th></th></tr></thead><tbody>';
    for(var k=0;k<ipcSpecs.length;k++){
      var sp=ipcSpecs[k]; var rr=resBySpec[sp.id];
      var rango = (sp.valor_min!=null||sp.valor_max!=null) ? ((sp.valor_min!=null?sp.valor_min:'')+' – '+(sp.valor_max!=null?sp.valor_max:'')+' '+(sp.unidad||'')) : (sp.criterio||'cualitativo');
      var resTxt = rr ? ((rr.valor_medido!=null?rr.valor_medido:'')+' '+(rr.valor_texto||'')) : '<span style="color:#f59e0b;">pendiente</span>';
      var confTxt = rr ? (rr.conforme===1?'<span style="color:#16a34a;font-weight:700;">✓</span>':(rr.conforme===0?'<span style="color:#dc2626;font-weight:700;">✗ OOS</span>':(rr.conforme===2?'<span style="color:#64748b;font-weight:700;">N/A</span>':'<span style="color:#999;">—</span>'))) : '';
      var oblig = sp.obligatorio?' <span title="obligatorio" style="color:#dc2626;">*</span>':'';
      var ipcAcc = (!rr && editable && miRol.verifica) ? '<button onclick="ebrReportarIpc('+d.id+','+sp.id+','+((sp.valor_min!=null||sp.valor_max!=null)?1:0)+')" style="background:#0ea5e9;color:#fff;border:none;border-radius:5px;padding:4px 9px;font-size:11px;cursor:pointer;">Reportar</button>' : '<span style="color:#999;">'+(rr?(rr.conforme===2?'N/A':'✓'):'—')+'</span>';
      h+='<tr><td>'+(sp.parametro||'')+oblig+'</td><td style="font-size:11px;color:#777;">'+rango+'</td><td>'+resTxt+'</td><td style="text-align:center;">'+confTxt+'</td><td style="font-size:11px;">'+((rr&&rr.medido_por)||'')+'</td><td style="text-align:right;">'+ipcAcc+'</td></tr>';
    }
    h+='</tbody></table>';
  }
  // Controles ESTÁNDAR (siempre presentes) · valor o "No aplica"
  h+='<div style="margin-top:10px;font-size:12px;font-weight:700;color:#6d28d9;">Controles estándar (Densidad · pH · Olor · Color · Apariencia)</div>';
  h+='<table class="table" style="font-size:12px;"><thead><tr><th>Control</th><th>Resultado</th><th>Conf.</th><th>Midió</th><th></th></tr></thead><tbody>';
  for(var e=0;e<ipcEstandar.length;e++){
    var ec=ipcEstandar[e];
    var ecConf=ec.conforme===1?'<span style="color:#16a34a;font-weight:700;">✓</span>':(ec.conforme===0?'<span style="color:#dc2626;font-weight:700;">✗</span>':(ec.conforme===2?'<span style="color:#64748b;font-weight:700;">N/A</span>':'<span style="color:#999;">—</span>'));
    var ecRes=ec.conforme===2?'No aplica':(ec.valor_texto||'<span style="color:#f59e0b;">pendiente</span>');
    var ecAcc=(editable&&miRol.verifica)?'<button onclick="ebrReportarIpcEstandar('+d.id+',\''+ec.control_codigo+'\')" style="background:#0ea5e9;color:#fff;border:none;border-radius:5px;padding:4px 9px;font-size:11px;cursor:pointer;">Registrar</button>':'<span style="color:#999;">—</span>';
    h+='<tr><td>'+ec.control_nombre+'</td><td>'+ecRes+'</td><td style="text-align:center;">'+ecConf+'</td><td style="font-size:11px;">'+(ec.medido_por||'')+'</td><td style="text-align:right;">'+ecAcc+'</td></tr>';
  }
  h+='</tbody></table>';
  // Conciliación de material de envase/empaque (SOLO envasado/acondicionamiento)
  if((d.fase||'')!=='fabricacion'){
  h+='</div>'+_secOpen('📦 Conciliación de material (envase/empaque)');
  if(conc&&conc.length){
    h+='<table class="table" style="font-size:12px;"><thead><tr><th>Tipo</th><th>Material</th><th>Lote</th><th style="text-align:right;">Req.</th><th style="text-align:right;">Recib.</th><th style="text-align:right;">Devuelta</th><th style="text-align:right;">Utilizada</th></tr></thead><tbody>';
    for(var k=0;k<conc.length;k++){var m=conc[k];
      h+='<tr><td>'+(m.tipo||'')+'</td><td>'+(m.material_nombre||'')+'</td><td>'+(m.lote_material||'')+'</td><td style="text-align:right;">'+(m.cant_requerida||0)+'</td><td style="text-align:right;">'+(m.cant_recibida||0)+'</td><td style="text-align:right;">'+(m.cant_devuelta||0)+'</td><td style="text-align:right;font-weight:700;">'+(m.cant_utilizada||0)+'</td></tr>';
    }
    h+='</tbody></table>';
  }else{h+='<div style="color:#999;font-size:12px;">Sin material conciliado aún.</div>';}
  if(editable){
    h+='<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:12px;">';
    h+='<select id="cm-tipo-'+d.id+'" style="padding:5px;border:1px solid #ccc;border-radius:5px;"><option value="envase">envase</option><option value="etiqueta">etiqueta</option><option value="estuche">estuche</option><option value="caja">caja</option><option value="inserto">inserto</option><option value="otro">otro</option></select>';
    h+='<input id="cm-nom-'+d.id+'" placeholder="Material" style="padding:5px;border:1px solid #ccc;border-radius:5px;min-width:150px;">';
    h+='<input id="cm-lote-'+d.id+'" placeholder="Lote" style="padding:5px;border:1px solid #ccc;border-radius:5px;width:90px;">';
    h+='<input id="cm-req-'+d.id+'" type="number" placeholder="Req." style="padding:5px;border:1px solid #ccc;border-radius:5px;width:70px;">';
    h+='<input id="cm-rec-'+d.id+'" type="number" placeholder="Recib." style="padding:5px;border:1px solid #ccc;border-radius:5px;width:70px;">';
    h+='<input id="cm-dev-'+d.id+'" type="number" placeholder="Devuelta" style="padding:5px;border:1px solid #ccc;border-radius:5px;width:80px;">';
    h+='<button onclick="ebrAgregarConciliacion('+d.id+')" style="background:#16a34a;color:#fff;border:none;border-radius:5px;padding:6px 12px;cursor:pointer;">+ Agregar</button>';
    h+='<span style="color:#999;">utilizada = recibida &minus; devuelta</span>';
    h+='</div>';
  }
  }
  // Aprobación de Artes / Codificación (gate de etiquetado · solo acondicionamiento)
  if((d.fase||'')==='acondicionamiento'){
    h+='</div>'+_secOpen('🎨 Aprobación de Artes / Codificación');
    if(artes&&artes.length){
      h+='<table class="table" style="font-size:12px;"><thead><tr><th>Descripción</th><th>Cód. Lote</th><th>Cód. Vto.</th><th>Aprobó</th><th></th></tr></thead><tbody>';
      for(var a=0;a<artes.length;a++){var ar=artes[a];
        var ap=(ar.aprobado_por||'').trim();
        var apCell=ap?('<span style="color:#16a34a;font-weight:700;">✓ '+ap+'</span>'):'<span style="color:#f59e0b;">pendiente</span>';
        var apAcc='<span style="color:#999;">—</span>';
        if(!ap&&editable){apAcc='<button onclick="ebrAprobarArte('+d.id+','+ar.id+')" style="background:#16a34a;color:#fff;border:none;border-radius:5px;padding:4px 9px;font-size:11px;cursor:pointer;">Aprobar etiqueta</button>';}
        h+='<tr><td>'+(ar.descripcion||'')+'</td><td>'+(ar.codigo_lote||'')+'</td><td>'+(ar.codigo_vencimiento||'')+'</td><td>'+apCell+'</td><td style="text-align:right;">'+apAcc+'</td></tr>';
      }
      h+='</tbody></table>';
    }else{h+='<div style="color:#999;font-size:12px;">Sin artes/codificación registrados aún.</div>';}
    if(editable){
      h+='<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:12px;">';
      h+='<input id="ar-desc-'+d.id+'" placeholder="Arte/etiqueta (descripción)" style="padding:5px;border:1px solid #ccc;border-radius:5px;min-width:180px;">';
      h+='<input id="ar-lote-'+d.id+'" placeholder="Código lote" style="padding:5px;border:1px solid #ccc;border-radius:5px;width:110px;">';
      h+='<input id="ar-venc-'+d.id+'" placeholder="Código vto." style="padding:5px;border:1px solid #ccc;border-radius:5px;width:110px;">';
      h+='<button onclick="ebrAgregarArte('+d.id+')" style="background:#6d28d9;color:#fff;border:none;border-radius:5px;padding:6px 12px;cursor:pointer;">+ Agregar</button>';
      h+='</div>';
    }
  }
  // Observaciones generales del proceso (bitácora)
  h+='</div>'+_secOpen('📝 Observaciones Generales del Proceso');
  if(obs&&obs.length){
    h+='<ul style="font-size:12px;color:#333;margin:0 0 8px;padding-left:18px;">';
    for(var o=0;o<obs.length;o++){var ob=obs[o];
      h+='<li><span style="color:#6d28d9;">'+(ob.registrado_por||'')+'</span> &middot; <span style="color:#999;">'+(ob.registrado_at_utc||'')+'</span><br>'+(ob.descripcion||'')+'</li>';
    }
    h+='</ul>';
  }else{h+='<div style="color:#999;font-size:12px;">Sin observaciones aún.</div>';}
  if(editable){
    h+='<div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;align-items:flex-start;font-size:12px;">';
    h+='<textarea id="ob-txt-'+d.id+'" rows="2" placeholder="Observación del proceso…" style="flex:1;min-width:220px;padding:6px;border:1px solid #ccc;border-radius:5px;"></textarea>';
    h+='<button onclick="ebrAgregarObservacion('+d.id+')" style="background:#6d28d9;color:#fff;border:none;border-radius:5px;padding:6px 12px;cursor:pointer;">+ Registrar</button>';
    h+='</div>';
  }
  // Registros físicos (adjuntar PDF · MyBatch ⑦)
  h+='</div>'+_secOpen('📎 Registros Físicos del Proceso Manufactura');
  if(regs.length){
    h+='<ul style="font-size:12px;margin:0 0 8px;padding-left:18px;">';
    for(var rg=0;rg<regs.length;rg++){var rr2=regs[rg];
      var pdfL=rr2.tiene_pdf?(' · <a href="/api/brd/ebr/'+d.id+'/registros-fisicos/'+rr2.id+'/pdf" target="_blank" style="color:#16a34a;">📄 PDF</a>'):'';
      h+='<li>'+(rr2.descripcion||'')+pdfL+' <span style="color:#999;font-size:11px;">· '+(rr2.registrado_por||'')+'</span></li>';
    }
    h+='</ul>';
  } else {h+='<div style="color:#999;font-size:12px;">Sin registros físicos adjuntos. Acá van las FOTOS de los rótulos diligenciados a mano (pesaje, limpieza) — la evidencia física del lote.</div>';}
  if(editable){h+='<button onclick="ebrAgregarRegistroFisico('+d.id+')" style="margin-top:4px;background:#0891b2;color:#fff;border:none;border-radius:5px;padding:6px 12px;font-size:11px;cursor:pointer;">&#128247; Adjuntar foto / PDF</button>';}
  // Cierre y Aprobaciones finales (Producción + Calidad · MyBatch pie del instructivo)
  h+='</div>'+_secOpen('&#9989; Cierre y Aprobaciones');
  var _est=(d.estado||'');
  h+='<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px">';
  h+='<div style="border:1px solid #e2e8f0;border-radius:10px;padding:12px">';
  h+='<div style="font-size:10px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:.3px">Aprobado por &middot; Producción</div>';
  if(_est==='completado'||_est==='en_revision_qc'||_est==='liberado'){
    h+='<div style="font-size:13px;font-weight:700;color:#16a34a;margin-top:4px">&#10003; Producción terminada</div><div style="font-size:11px;color:#64748b">'+(d.completado_at_utc?String(d.completado_at_utc).replace('T',' ').slice(0,16):'')+(d.cantidad_real_g?(' &middot; '+d.cantidad_real_g+' g real'):'')+'</div>';
  } else if(editable&&miRol.realiza&&fa==='envasado'){
    h+='<div style="font-size:11px;color:#64748b;margin:5px 0">Cerr&aacute; el envasado en la secci&oacute;n <b>&#128230; Presentaciones envasadas</b> de arriba (registra unidades y descuenta los envases · marca completado).</div>';
  } else if(editable&&miRol.realiza){
    h+='<div style="font-size:11px;color:#64748b;margin:5px 0 7px">Cierra la producción con la cantidad real (requiere todos los pasos completos).</div><button onclick="ebrTerminarLote('+d.id+')" style="background:#d97706;color:#fff;border:none;border-radius:7px;padding:8px 14px;font-size:12px;font-weight:700;cursor:pointer">&#10003; Terminar producción</button>';
  } else {
    h+='<div style="font-size:11px;color:#f59e0b;margin-top:4px">&#9203; Pendiente &middot; lo cierra Producción (Operario / Jefe)</div>';
  }
  h+='</div>';
  h+='<div style="border:1px solid #e2e8f0;border-radius:10px;padding:12px">';
  h+='<div style="font-size:10px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:.3px">Aprobado por &middot; Calidad (liberación)</div>';
  if(_est==='liberado'){
    h+='<div style="font-size:13px;font-weight:700;color:#16a34a;margin-top:4px">&#128275; Liberado por '+_escHTML(d.liberado_por||'')+'</div><div style="font-size:11px;color:#64748b">'+(d.liberado_at_utc?String(d.liberado_at_utc).replace('T',' ').slice(0,16):'')+'</div>';
  } else if((_est==='completado'||_est==='en_revision_qc')&&miRol.puede_liberar){
    h+='<div style="font-size:11px;color:#64748b;margin:5px 0 7px">Libera el lote con tu e-firma (cierra el batch record &middot; Part 11).</div><button onclick="ebrLiberarLote('+d.id+')" style="background:#15803d;color:#fff;border:none;border-radius:7px;padding:8px 14px;font-size:12px;font-weight:700;cursor:pointer">&#128274; Liberar lote</button>';
  } else if(_est==='completado'||_est==='en_revision_qc'){
    h+='<div style="font-size:11px;color:#f59e0b;margin-top:4px">&#9203; Espera liberación de Calidad / Aseguramiento</div>';
  } else {
    h+='<div style="font-size:11px;color:#cbd5e1;margin-top:4px">&mdash; (primero Producción termina)</div>';
  }
  h+='</div>';
  h+='<div style="border:1px solid #e2e8f0;border-radius:10px;padding:12px">';
  h+='<div style="font-size:10px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:.3px">Visto bueno &middot; Director Técnico</div>';
  if((d.aprobado_dt_por||'').trim()){
    h+='<div style="font-size:13px;font-weight:700;color:#16a34a;margin-top:4px">&#9989; '+_escHTML(d.aprobado_dt_por)+'</div><div style="font-size:11px;color:#64748b">'+(d.aprobado_dt_at?String(d.aprobado_dt_at).replace('T',' ').slice(0,16):'')+'</div>';
  } else if((_est==='liberado'||_est==='completado'||_est==='en_revision_qc')&&miRol.aprueba_dt){
    h+='<div style="font-size:11px;color:#64748b;margin:5px 0 7px">Visto bueno final del responsable técnico (INVIMA) con tu e-firma.</div><button onclick="ebrAprobarDt('+d.id+')" style="background:#7c3aed;color:#fff;border:none;border-radius:7px;padding:8px 14px;font-size:12px;font-weight:700;cursor:pointer">&#9989; Dar visto bueno</button>';
  } else {
    h+='<div style="font-size:11px;color:#cbd5e1;margin-top:4px">&mdash; (lo firma el Director Técnico)</div>';
  }
  h+='</div></div>';
  // Correcciones del registro (Part 11 · enmiendas trazadas)
  h+='</div>'+_secOpen('✏️ Correcciones del Registro');
  var _corr=d.correcciones||[];
  if(_corr.length){
    h+='<table class="table" style="font-size:11px"><thead><tr><th>Motivo</th><th>Descripción</th><th>Autor</th><th>Fecha</th></tr></thead><tbody>';
    _corr.forEach(function(cc){ h+='<tr><td>'+_escHTML(cc.motivo||'')+(cc.campo_afectado?('<div style="font-size:9px;color:#94a3b8">campo: '+_escHTML(cc.campo_afectado)+'</div>'):'')+'</td><td>'+_escHTML(cc.descripcion||'')+'</td><td style="font-size:10px">'+_escHTML(cc.registrado_por||'')+'</td><td style="font-size:10px;color:#94a3b8">'+(cc.registrado_at_utc?String(cc.registrado_at_utc).replace('T',' ').slice(0,16):'')+'</td></tr>'; });
    h+='</tbody></table>';
  } else { h+='<div style="color:#94a3b8;font-size:12px;">Sin correcciones registradas. Toda enmienda a un registro firmado queda trazada aquí (motivo &middot; autor &middot; fecha &middot; 21 CFR Part 11).</div>'; }
  if(editable&&miRol.corrige){ h+='<button onclick="ebrAgregarCorreccion('+d.id+')" style="margin-top:8px;background:#6d28d9;color:#fff;border:none;border-radius:5px;padding:6px 12px;font-size:11px;font-weight:700;cursor:pointer">+ Registrar corrección</button>'; }
  else if(editable){ h+='<div style="margin-top:6px;font-size:11px;color:#94a3b8">Las correcciones las registra Calidad / Aseguramiento.</div>'; }
  h+='</div>';
  // 🔍 TRAZABILIDAD (27-jun · Sebastián · INVIMA) · quién hizo qué + cuándo, consolidado del audit trail del
  // EBR (vista-completa ya trae d.audit · acciones a nivel orden + por paso/pesaje/IPC/despeje). Cronológico.
  h+=_secOpen('🔍 Trazabilidad de responsables (quién hizo qué · INVIMA)');
  var _aud=(d.audit||[]).slice().reverse();
  if(!_aud.length){ h+='<div style="color:#94a3b8;font-size:12px;">Sin acciones registradas todavía. Cada acción del lote (iniciar/pesar/verificar/completar/liberar) queda con responsable, fecha y hora (21 CFR Part 11).</div>'; }
  else{
    h+='<table class="table" style="font-size:11px"><thead><tr><th>Fecha y hora</th><th>Responsable</th><th>Acción</th><th>Detalle</th></tr></thead><tbody>';
    _aud.forEach(function(a){
      var _f=a.fecha?String(a.fecha).replace('T',' ').slice(0,16):'';
      var _ac=String(a.accion||'').replace(/_/g,' ').toLowerCase();
      h+='<tr style="vertical-align:top"><td style="font-size:10px;color:#94a3b8;white-space:nowrap">'+_escHTML(_f)+'</td><td style="font-weight:700;color:#6d28d9">'+_escHTML(a.usuario||'—')+'</td><td style="font-size:11px">'+_escHTML(_ac)+'</td><td style="font-size:10px;color:#64748b">'+_escHTML(a.detalle||'')+'</td></tr>';
    });
    h+='</tbody></table><div style="font-size:10px;color:#94a3b8;margin-top:6px">Registro inmutable de acciones del lote · responsable + fecha/hora de cada operación (INVIMA / 21 CFR Part 11).</div>';
  }
  h+='</div>';
  return h;
}
async function ebrAgregarObservacion(ebrId){
  var el=document.getElementById('ob-txt-'+ebrId);
  var txt=el?(el.value||'').trim():'';
  if(!txt){alert('Escribe la observación');return;}
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/observaciones',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({descripcion:txt})});
    var d=await r.json();
    if(!r.ok){alert(d.error||'No se pudo registrar');return;}
    abrirEBR(ebrId);
  }catch(e){alert('Error de red');}
}
async function ebrAgregarArte(ebrId){
  var g=function(p){var el=document.getElementById(p+ebrId);return el?el.value:'';};
  var desc=(g('ar-desc-')||'').trim();
  if(!desc){alert('Indica el arte/etiqueta');return;}
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/artes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({descripcion:desc,codigo_lote:g('ar-lote-'),codigo_vencimiento:g('ar-venc-')})});
    var d=await r.json();
    if(!r.ok){alert(d.error||'No se pudo agregar');return;}
    abrirEBR(ebrId);
  }catch(e){alert('Error de red');}
}
async function ebrAprobarArte(ebrId, arteId){
  var f=await _firmarEsign('aprueba','ebr_artes_codificacion',arteId);
  if(!f){return;}
  if(f.error){alert(f.error);return;}
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/artes/'+arteId+'/aprobar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({signature_id:f.signature_id})});
    var d=await r.json();
    if(!r.ok){alert(d.error||'No se pudo aprobar');return;}
    abrirEBR(ebrId);
  }catch(e){alert('Error de red');}
}
async function ebrAgregarPrecaucion(ebrId, tipo){
  var d=prompt((tipo==='equipo'?'Equipo usado:':'Precaución del proceso:'));
  if(d===null)return; d=(d||'').trim(); if(!d)return;
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/precauciones',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tipo:tipo,descripcion:d})});
    var j=await r.json(); if(!r.ok){alert(j.error||'Error');return;}
    abrirEBR(ebrId);
  }catch(e){alert('Error de red');}
}
async function ebrMarcarDespeje(ebrId, idx, etapa){
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/despeje-item',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({item_idx:idx,cumple:1,etapa:etapa})});
    if(!r.ok){ var j=await r.json(); alert('Error: '+(j.error||r.status)); return; }
    // Sebastián 7-jul (v2): pop-up no-bloqueante · el operario sigue, y Calidad ya recibió la alerta (campana).
    if(typeof _toast==='function'){ _toast('Registrado ✓ · Calidad avisada para verificar al lado', 1); }
    abrirEBR(ebrId);
  }catch(e){ alert('Error: '+(e.message||e)); }
}
async function ebrDespejeTodoCumple(ebrId, etapa){
  if(!confirm('\u00bfMarcar TODAS las verificaciones de despeje como CUMPLE? (firm\u00e1s como responsable)')) return;
  try{
    for(var i=0;i<13;i++){
      await fetch('/api/brd/ebr/'+ebrId+'/despeje-item',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({item_idx:i,cumple:1,etapa:etapa})});
    }
    abrirEBR(ebrId);
  }catch(e){ alert('Error: '+(e.message||e)); }
}
async function ebrTerminarLote(ebrId){
  var v=prompt('Cantidad REAL producida (gramos) · cierra la producción:');
  if(v===null)return;
  var n=parseFloat(String(v).replace(',','.'));
  if(!(n>0)){alert('Cantidad inválida');return;}
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/completar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cantidad_real_g:n})});
    if(!r.ok){ var j=await r.json(); alert('Error: '+(j.error||r.status)); return; }
    abrirEBR(ebrId);
  }catch(e){ alert('Error: '+(e.message||e)); }
}
async function ebrLiberarLote(ebrId){
  if(!confirm('\u00bfLiberar el lote? Vas a firmar electr\u00f3nicamente (21 CFR Part 11). Cierra el batch record.'))return;
  var f=await _firmarEsign('libera','ebr_ejecuciones',ebrId);
  if(!f)return;
  if(f.error){ alert(f.error); return; }
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/liberar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({signature_id:f.signature_id})});
    if(!r.ok){ var j=await r.json(); alert('Error: '+(j.error||r.status)); return; }
    alert('\u2713 Lote liberado \u00b7 batch record cerrado');
    abrirEBR(ebrId);
  }catch(e){ alert('Error: '+(e.message||e)); }
}
async function ebrPesarMp(ebrId, materialId, teorico){
  var v=prompt('Cantidad REAL pesada de '+materialId+' (gramos)'+(teorico?(' \u00b7 te\u00f3rico '+teorico+' g'):'')+':');
  if(v===null)return;
  var n=parseFloat(String(v).replace(',','.'));
  if(!(n>=0)){ alert('Cantidad inválida'); return; }
  var lote=prompt('N\u00b0 de lote de la materia prima (de la etiqueta):')||'';
  var f=await _firmarEsign('ejecuta','ebr_pesajes',ebrId+':'+materialId);
  if(!f)return;
  if(f.error){ alert(f.error); return; }
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/pesajes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({material_id:materialId,cantidad_real_g:n,lote_mp:lote,signature_id:f.signature_id})});
    if(!r.ok){ var j=await r.json(); alert('Error: '+(j.error||r.status)); return; }
    abrirEBR(ebrId);
  }catch(e){ alert('Error: '+(e.message||e)); }
}
async function ebrAprobarDt(ebrId){
  if(!confirm('\u00bfDar el visto bueno final como Director T\u00e9cnico? Vas a firmar electr\u00f3nicamente (21 CFR Part 11).'))return;
  var f=await _firmarEsign('aprueba_dt','ebr_ejecuciones',ebrId);
  if(!f)return;
  if(f.error){ alert(f.error); return; }
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/aprobar-dt',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({signature_id:f.signature_id})});
    if(!r.ok){ var j=await r.json(); alert('Error: '+(j.error||r.status)); return; }
    abrirEBR(ebrId);
  }catch(e){ alert('Error: '+(e.message||e)); }
}
async function ebrAgregarCorreccion(ebrId){
  var motivo=prompt('Motivo de la corrección (qué se corrige y por qué):');
  if(motivo===null)return;
  motivo=(motivo||'').trim(); if(!motivo){ alert('Indicá el motivo'); return; }
  var desc=prompt('Descripción de la corrección (opcional):')||'';
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/correcciones',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({motivo:motivo,descripcion:desc})});
    if(!r.ok){ var j=await r.json(); alert('Error: '+(j.error||r.status)); return; }
    abrirEBR(ebrId);
  }catch(e){ alert('Error: '+(e.message||e)); }
}
async function ebrAgregarAjusteMp(ebrId){
  var mat=prompt('Materia prima ajustada (ej. Trietanolamina 85%):');
  if(mat===null)return;
  mat=(mat||'').trim(); if(!mat){ alert('Indicá la materia prima'); return; }
  var cant=prompt('Cantidad ajustada en gramos (ej. 60):')||'0';
  var mot=prompt('Motivo del ajuste (ej. ajustar pH a 6.0):')||'';
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/ajustes-mp',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({material:mat,cantidad_g:cant,motivo:mot})});
    if(!r.ok){ var j=await r.json(); alert('Error: '+(j.error||r.status)); return; }
    abrirEBR(ebrId);
  }catch(e){ alert('Error: '+(e.message||e)); }
}
async function ebrVerificarDespeje(ebrId, idx, etapa){
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/despeje-verificar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({item_idx:idx,etapa:etapa})});
    if(!r.ok){ var j=await r.json(); alert('Error: '+(j.error||r.status)); return; }
    abrirEBR(ebrId);
  }catch(e){ alert('Error: '+(e.message||e)); }
}
async function ebrVerificarDespejeTodo(ebrId, etapa){
  if(!confirm('\u00bfVerificar (2\u00aa firma de Calidad) todas las verificaciones de despeje ya marcadas por el operario?')) return;
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/despeje-verificar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({todos:true,etapa:etapa})});
    if(!r.ok){ var j=await r.json(); alert('Error: '+(j.error||r.status)); return; }
    var d=await r.json();
    if(d.verificados===0){ alert('No se verific\u00f3 nada: o no hay \u00edtems marcados, o los marcaste vos mismo (la 2\u00aa firma debe ser de otra persona \u00b7 regla de las 2 personas).'); }
    abrirEBR(ebrId);
  }catch(e){ alert('Error: '+(e.message||e)); }
}
async function ebrRegistrarDespeje(ebrId){
  if(!confirm('Registrar despeje de línea?\n\nConfirmá que se cumple: área limpia, sin producto anterior, equipos limpios e identificados, documentación presente.\nAceptar = TODO cumple (CONFORME) · Cancelar = abrir checklist parcial'))
  { // checklist parcial
    var al=confirm('¿Área limpia?'); var sp=confirm('¿Sin producto anterior?');
    var eq=confirm('¿Equipos limpios e identificados?'); var doc=confirm('¿Documentación presente?');
    var obs=prompt('Observaciones del despeje (opcional):')||'';
    return _ebrPostDespeje(ebrId,{area_limpia:al,sin_producto_anterior:sp,equipos_limpios:eq,documentacion_ok:doc,observaciones:obs});
  }
  return _ebrPostDespeje(ebrId,{area_limpia:1,sin_producto_anterior:1,equipos_limpios:1,documentacion_ok:1});
}
async function _ebrPostDespeje(ebrId, body){
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/despeje',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var j=await r.json(); if(!r.ok){alert(j.error||'Error');return;}
    if(!j.conforme){alert('Despeje registrado como NO CONFORME · revisá antes de producir.');}
    abrirEBR(ebrId);
  }catch(e){alert('Error de red');}
}
async function ebrAgregarRegistroFisico(ebrId, descPre){
  var desc;
  if(descPre){ desc=descPre; }
  else{
    desc=prompt('Descripci\u00f3n del registro f\u00edsico (ej. "R\u00f3tulo MP00138 \u00c1cido L\u00e1ctico", "R\u00f3tulo limpieza Fabricaci\u00f3n", "Tirilla balanza"):');
    if(desc===null)return; desc=(desc||'').trim(); if(!desc)return;
  }
  // Foto del rótulo (lo único que se llena a mano) o PDF · en celular abre la cámara
  var inp=document.createElement('input'); inp.type='file'; inp.accept='image/*,application/pdf';
  try{ inp.setAttribute('capture','environment'); }catch(e){}
  inp.onchange=async function(){
    var f=inp.files&&inp.files[0];
    if(!f){ return; }
    if(f.size>8*1024*1024){ alert('Archivo muy grande (m\u00e1x 8MB)'); return; }
    var body={descripcion:desc, archivo_nombre:f.name};
    body.archivo_b64=await new Promise(function(res){var rd=new FileReader();rd.onload=function(){res((rd.result||'').toString().split(',').pop());};rd.readAsDataURL(f);});
    try{
      var r=await fetch('/api/brd/ebr/'+ebrId+'/registros-fisicos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      var j=await r.json(); if(!r.ok){alert(j.error||'Error');return;}
      abrirEBR(ebrId);
    }catch(e){alert('Error de red');}
  };
  inp.click();
}
async function ebrAgregarConciliacion(ebrId){
  var g=function(p){var el=document.getElementById(p+ebrId);return el?el.value:'';};
  var nom=(g('cm-nom-')||'').trim();
  if(!nom){alert('Indica el material');return;}
  var body={tipo:g('cm-tipo-'),material_nombre:nom,lote_material:g('cm-lote-'),
            cant_requerida:g('cm-req-')||0,cant_recibida:g('cm-rec-')||0,cant_devuelta:g('cm-dev-')||0};
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/conciliacion-material',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(!r.ok){alert(d.error||'No se pudo agregar');return;}
    abrirEBR(ebrId);
  }catch(e){alert('Error de red');}
}
async function ebrIniciarPaso(ebrId, orden){
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/pasos/'+orden+'/iniciar',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    var d=await r.json();
    if(!r.ok){alert(d.error||'No se pudo iniciar el paso');return;}
    abrirEBR(ebrId);
  }catch(e){alert('Error de red');}
}
async function ebrCompletarPaso(ebrId, orden, pasoId, reqSign, reqQc){
  var body={observaciones:(prompt('Resultado del paso (pH, temperatura, tiempo\u2026 \u00b7 opcional):')||'')};
  if(reqSign){
    var f=await _firmarEsign('ejecuta','ebr_pasos_ejecutados',pasoId);
    if(!f){return;}
    if(f.error){alert(f.error);return;}
    body.signature_id=f.signature_id;
  }
  if(reqQc){
    alert('Este paso requiere 2ª firma de Calidad (QC) · debe firmar una persona DISTINTA del operario.');
    var fq=await _firmarEsign('supervisa','ebr_pasos_ejecutados',pasoId);
    if(!fq){return;}
    if(fq.error){alert(fq.error);return;}
    body.qc_signature_id=fq.signature_id;
  }
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/pasos/'+orden+'/completar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(!r.ok){alert(d.error||'No se pudo completar el paso');return;}
    abrirEBR(ebrId);
  }catch(e){alert('Error de red');}
}
async function ebrVerificarPesaje(ebrId, pid){
  var f=await _firmarEsign('supervisa','ebr_pesajes',pid);
  if(!f){return;}
  if(f.error){alert(f.error);return;}
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/pesajes/'+pid+'/verificar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({signature_id:f.signature_id})});
    var d=await r.json();
    if(!r.ok){alert(d.error||'No se pudo verificar el pesaje');return;}
    abrirEBR(ebrId);
  }catch(e){alert('Error de red');}
}

async function ebrGenerarMBR(){
  var prod=prompt('Producto para generar su MBR desde la fórmula (ej. BLUSH BALM):');
  if(prod===null)return; prod=(prod||'').trim(); if(!prod)return;
  try{
    var r=await fetch('/api/brd/mbr/generar-desde-formula',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({producto_nombre:prod})});
    var d=await r.json();
    if(!r.ok){alert((d&&d.error)||'No se pudo generar el MBR');return;}
    if(d.ya_existe){alert('Ese producto ya tiene un MBR ('+(d.estado||'')+'). Aprobalo en /brd si está en draft.');}
    else{alert('✓ MBR generado ('+(d.pasos||0)+' pasos, draft). Ahora aprobalo en /brd con e-firma y volvé a "➕ Nuevo legajo".');}
  }catch(e){alert('Error de red');}
}
async function ebrNuevoLegajo(){
  var prod=prompt('Producto (debe tener un MBR aprobado):');
  if(!prod){return;} prod=prod.trim();
  var fase=(prompt('Fase del legajo:\n- fabricacion\n- envasado\n- acondicionamiento','fabricacion')||'').trim().toLowerCase();
  if(['fabricacion','envasado','acondicionamiento'].indexOf(fase)<0){alert('Fase inválida');return;}
  var lote=prompt('Lote físico/comercial del lote:');
  if(!lote){return;} lote=lote.trim();
  try{
    var rm=await fetch('/api/brd/mbr?producto='+encodeURIComponent(prod)+'&estado=aprobado',{credentials:'same-origin'});
    var md=await rm.json();var arr=(md&&md.items)||[];
    if(!arr.length){alert('No hay MBR aprobado para "'+prod+'". Generá y aprobá el MBR primero (/brd).');return;}
    var mbrId=arr[0].id;
    var loteEbr=lote+(fase==='envasado'?'-OF':(fase==='acondicionamiento'?'-OA':''));
    var r=await fetch('/api/brd/ebr',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mbr_template_id:mbrId,lote:loteEbr,fase:fase})});
    var d=await r.json();
    if(!r.ok){alert(d.error||'No se pudo crear el legajo');return;}
    cargarEBRs();abrirEBR(d.id);
  }catch(e){alert('Error de red');}
}
async function ebrReportarIpc(ebrId, specId, esNumerico){
  var body={ipc_spec_id:specId};
  var aplica=confirm('¿Este control APLICA al producto?\n\nAceptar = Sí (registrar medición)\nCancelar = NO APLICA');
  if(!aplica){
    body.no_aplica=true;
  } else if(esNumerico){
    var v=prompt('Valor medido del IPC:'); if(v===null)return; v=(v||'').trim(); if(v==='')return;
    if(isNaN(parseFloat(v))){alert('Valor numérico inválido');return;}
    body.valor_medido=parseFloat(v);
  } else {
    var conf=confirm('¿El control CUMPLE (conforme)?\nAceptar = Conforme · Cancelar = NO conforme');
    var txt=prompt('Observación/valor cualitativo (opcional):')||'';
    body.conforme=conf?1:0; body.valor_texto=txt.trim();
  }
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/ipc-resultados',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(!r.ok){alert((d&&d.error)||'No se pudo reportar el IPC');return;}
    if(d.conforme===0 && d.desviacion){alert('⚠ IPC FUERA DE SPEC · se abrió la desviación '+(d.desviacion.codigo||'')+' automáticamente.');}
    abrirEBR(ebrId);
  }catch(e){alert('Error de red');}
}
async function ebrReportarIpcEstandar(ebrId, codigo){
  var body={control_codigo:codigo};
  var aplica=confirm('¿Este control APLICA al producto?\n\nAceptar = Sí (registrar)\nCancelar = NO APLICA');
  if(!aplica){
    body.no_aplica=true;
  } else {
    var conf=confirm('¿CUMPLE?\nAceptar = Cumple · Cancelar = No cumple');
    var txt=prompt('Resultado / valor (ej: 1,056 g/mL · Inodoro · Amarillento…):')||'';
    body.conforme=conf?1:0; body.valor_texto=txt.trim();
  }
  try{
    var r=await fetch('/api/brd/ebr/'+ebrId+'/ipc-estandar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(!r.ok){alert((d&&d.error)||'No se pudo registrar el control');return;}
    abrirEBR(ebrId);
  }catch(e){alert('Error de red');}
}
async function ebrAsignarLoteFisico(id, actual){
  var sug=(actual && actual.indexOf('PP')===0)?'':actual;
  var nuevo=prompt('Lote físico/comercial real (reemplaza el provisional '+(actual||'')+'):', sug);
  if(nuevo===null){return;}
  nuevo=(nuevo||'').trim();
  if(!nuevo){return;}
  try{
    var r=await fetch('/api/brd/ebr/'+id+'/asignar-lote-fisico',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lote_fisico:nuevo})});
    var d=await r.json();
    if(!r.ok){alert(d.error||'No se pudo asignar el lote');return;}
    abrirEBR(id);
  }catch(e){alert('Error de red');}
}

async function enviarRevisionCC(){
  if(!_ccLoteActual){return;}
  var coaOk=document.getElementById('cc-coa-ok').checked;
  var loteCoincide=document.getElementById('cc-lote-coincide').checked;
  var coaVigente=document.getElementById('cc-coa-vigente').checked;
  var fichaOk=document.getElementById('cc-ficha-ok').checked;
  var solubResult=document.querySelector('input[name="cc-solub"]:checked');
  var aqlResult=document.querySelector('input[name="cc-aql"]:checked');
  var aqlObs=document.getElementById('cc-aql-obs').value.trim();
  var muestraRet=document.getElementById('cc-muestra-ret').checked;
  var obsFinal=document.getElementById('cc-obs-final').value.trim();
  var msg=document.getElementById('cc-modal-msg');
  if(!solubResult){msg.innerHTML='<div class="alert-error">Selecciona resultado de solubilidad</div>';return;}
  if(!aqlResult){msg.innerHTML='<div class="alert-error">Selecciona resultado AQL</div>';return;}
  if((aqlResult.value==='NO_CONFORME'||aqlResult.value==='CUARENTENA_EXTENDIDA')&&!aqlObs){
    msg.innerHTML='<div class="alert-error">Las observaciones son obligatorias para este resultado</div>';return;
  }
  var payload={
    mov_id:_ccLoteActual.id,
    lote:_ccLoteActual.lote,
    codigo_mp:_ccLoteActual.codigo_mp,
    coa_ok:coaOk,
    lote_coincide:loteCoincide,
    coa_vigente:coaVigente,
    ficha_ok:fichaOk,
    solubilidad:solubResult.value,
    resultado_aql:aqlResult.value,
    observaciones_aql:aqlObs,
    muestra_retencion:muestraRet,
    observaciones:obsFinal,
    estanteria_final:((document.getElementById('cc-est-final')||{}).value||'').trim(),
    posicion_final:((document.getElementById('cc-pos-final')||{}).value||'').trim(),
    firmante:OPER_ACTUAL
  };
  try{
    document.getElementById('cc-submit-btn').disabled=true;
    document.getElementById('cc-submit-btn').textContent='Registrando...';
    var r=await fetch('/api/lotes/cc-review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    var res=await r.json();
    if(!r.ok && res.requiere_firma){
      var firma=await _firmarLoteEsign(res.sign_meaning, res.record_id);
      if(firma===null){ msg.innerHTML='<div class="alert-error">Firma cancelada · la disposición NO se registró</div>'; return; }
      if(firma.error){ msg.innerHTML='<div class="alert-error">'+firma.error+'</div>'; return; }
      payload.signature_id=firma.signature_id;
      r=await fetch('/api/lotes/cc-review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      res=await r.json();
    }
    if(r.ok){
      msg.innerHTML='<div class="alert-success">'+res.message+'</div>';
      document.getElementById('cuar-msg').innerHTML='<div class="alert-success">Revision CC registrada -- '+res.estado+' -- Lote: '+payload.lote+'</div>';
      setTimeout(function(){cerrarCCModal();cargarCuarentena();},1800);
    }else{
      msg.innerHTML='<div class="alert-error">'+(res.error||'Error al registrar')+'</div>';
    }
  }catch(e){
    msg.innerHTML='<div class="alert-error">Error: '+e.message+'</div>';
  }finally{
    document.getElementById('cc-submit-btn').disabled=false;
    document.getElementById('cc-submit-btn').textContent='Firmar y Registrar';
  }
}

async function buscarTrazabilidad(){
  var lote=(document.getElementById('trz-lote').value||'').trim();
  if(!lote){alert('Ingresa un numero de lote');return;}
  try{
    // BUG-2 fix · 20-may-2026 Dashboard PRO audit: la ruta corta
    // /api/trazabilidad/<lote> fue eliminada · usar /lote/<path:lote>
    // (mismo patrón que líneas siguientes con /lote-pt/ y /lote-mp/).
    var r=await fetch('/api/trazabilidad/lote/'+encodeURIComponent(lote));
    var data=await r.json();
    if(!data.ingreso){
      document.getElementById('trz-msg').innerHTML='<div class="alert-error">Lote no encontrado: '+lote+'</div>';
      document.getElementById('trz-result-lote').style.display='none';
      return;
    }
    document.getElementById('trz-msg').innerHTML='';
    document.getElementById('trz-result-lote').style.display='block';
    var ing=data.ingreso;
    document.getElementById('trz-ingreso').innerHTML=
      '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;">'+
      '<div><b>Codigo:</b> '+ing.codigo_mp+'</div>'+
      '<div><b>Nombre:</b> '+ing.nombre+'</div>'+
      '<div><b>INCI:</b> '+(ing.nombre_inci||'—')+'</div>'+
      '<div><b>Cantidad:</b> '+Number(ing.cantidad_g).toLocaleString()+' g</div>'+
      '<div><b>Proveedor:</b> '+(ing.proveedor||'—')+'</div>'+
      '<div><b>Factura:</b> '+(ing.factura||'—')+'</div>'+
      '<div><b>OC:</b> '+(ing.orden_compra||'—')+'</div>'+
      '<div><b>Precio/kg:</b> '+(ing.precio_kg?'$'+Number(ing.precio_kg).toLocaleString('es-CO'):'—')+'</div>'+
      '<div><b>Fecha:</b> '+(ing.fecha?ing.fecha.substring(0,10):'—')+'</div>'+
      '</div>';
    document.getElementById('trz-nprod').textContent=data.total_producciones;
    var tb=document.getElementById('trz-prod-tbody');
    if(!data.producciones.length){
      tb.innerHTML='<tr><td colspan="4" style="text-align:center;color:#999;">Este lote no ha sido usado en produccion</td></tr>';
    } else {
      var h='';
      data.producciones.forEach(function(p){
        h+='<tr><td>'+p.producto+'</td><td>'+p.fecha.substring(0,10)+'</td><td>'+p.operador+'</td><td style="text-align:right;">'+Number(p.cantidad_g).toLocaleString()+'</td></tr>';
      });
      tb.innerHTML=h;
    }
  }catch(e){document.getElementById('trz-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}

async function buscarTrazabilidadPT(){
  var lote=(document.getElementById('trz-lote-pt')||{}).value||'';
  lote=lote.trim();
  if(!lote){alert('Ingresa un numero de lote PT (ej: PROD-00001)');return;}
  var div=document.getElementById('trz-result');
  if(!div)return;
  div.innerHTML='<p style="color:#888;font-size:0.9em;">Buscando...</p>';
  try{
    var r=await fetch('/api/trazabilidad/lote-pt/'+encodeURIComponent(lote));
    var d=await r.json();
    if(d.error){div.innerHTML='<div style="color:#e74c3c;padding:12px;background:#ffeaea;border-radius:8px;">'+_escHTML(d.error)+'</div>';return;}
    var html='<div style="background:#f8f9ff;border:1px solid #c3cfe2;border-radius:10px;padding:16px;margin-bottom:12px;">';
    html+='<h4 style="margin:0 0 10px;color:#6c5ce7;">&#128203; Lote PT: '+d.lote_ref+'</h4>';
    if(d.produccion){
      var p=d.produccion;
      html+='<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;font-size:0.88em;margin-bottom:12px;">';
      html+='<div><b>Producto:</b> '+(p.producto||'&#8212;')+'</div>';
      html+='<div><b>Cantidad:</b> '+(p.cantidad_kg?Math.round(Number(p.cantidad_kg)*1000).toLocaleString('es-CO')+' g':'&#8212;')+'</div>';
      html+='<div><b>Fecha:</b> '+(p.fecha?p.fecha.substring(0,10):'&#8212;')+'</div>';
      html+='<div><b>Operador:</b> '+(p.operador||'&#8212;')+'</div>';
      html+='</div>';
    }
    var mps=d.mps_consumidas||[];
    html+='<h5 style="margin:0 0 8px;color:#6d28d9;">Materias Primas Consumidas ('+mps.length+')</h5>';
    if(mps.length){
      html+='<table style="width:100%;font-size:0.82em;border-collapse:collapse;">';
      html+='<thead><tr style="background:#f0f0f0;"><th style="padding:4px 8px;text-align:left;">Lote MP</th><th style="padding:4px 8px;text-align:left;">Material</th><th style="padding:4px 8px;text-align:right;">Cant (g)</th><th style="padding:4px 8px;text-align:left;">Proveedor</th><th style="padding:4px 8px;text-align:left;">Vence</th></tr></thead><tbody>';
      var det=d.detalle_lotes_mp||{};
      mps.forEach(function(m){
        var info=det[m.lote]||{};
        html+='<tr style="border-bottom:1px solid #eee;"><td style="padding:4px 8px;font-family:monospace;font-size:0.9em;">'+m.lote+'</td><td style="padding:4px 8px;">'+(m.material||'&#8212;')+'</td><td style="padding:4px 8px;text-align:right;">'+Number(m.cantidad_g||0).toLocaleString()+'</td><td style="padding:4px 8px;">'+(info.proveedor||'&#8212;')+'</td><td style="padding:4px 8px;">'+(info.vencimiento?info.vencimiento.substring(0,10):'&#8212;')+'</td></tr>';
      });
      html+='</tbody></table>';
    } else {
      html+='<p style="color:#999;font-size:0.85em;">No se encontraron lotes MP asociados (la produccion puede no tener lote asignado aun).</p>';
    }
    var desp=d.despachos||[];
    if(desp.length){
      html+='<h5 style="margin:12px 0 8px;color:#e17055;">Despachos a Clientes ('+desp.length+')</h5>';
      html+='<table style="width:100%;font-size:0.82em;border-collapse:collapse;"><thead><tr style="background:#fff3f0;"><th style="padding:4px 8px;text-align:left;">Fecha</th><th style="padding:4px 8px;text-align:left;">Cliente</th><th style="padding:4px 8px;text-align:right;">Cantidad</th><th style="padding:4px 8px;text-align:left;">Remision</th></tr></thead><tbody>';
      desp.forEach(function(ds){
        html+='<tr style="border-bottom:1px solid #fee;"><td style="padding:4px 8px;">'+(ds.fecha?ds.fecha.substring(0,10):'&#8212;')+'</td><td style="padding:4px 8px;">'+(ds.cliente||'&#8212;')+'</td><td style="padding:4px 8px;text-align:right;">'+(ds.cantidad||'&#8212;')+'</td><td style="padding:4px 8px;">'+(ds.remision||'&#8212;')+'</td></tr>';
      });
      html+='</tbody></table>';
    }
    html+='</div>';
    div.innerHTML=html;
  }catch(e){div.innerHTML='<div style="color:#e74c3c;padding:12px;background:#ffeaea;border-radius:8px;">Error: '+e.message+'</div>';}
}

async function buscarTrazabilidadMP(){
  var lote=(document.getElementById('trz-lote-mp')||{}).value||'';
  lote=lote.trim();
  if(!lote){alert('Ingresa un numero de lote MP (ej: ESP240115MP1)');return;}
  var div=document.getElementById('trz-result');
  if(!div)return;
  div.innerHTML='<p style="color:#888;font-size:0.9em;">Buscando...</p>';
  try{
    var r=await fetch('/api/trazabilidad/lote-mp/'+encodeURIComponent(lote));
    var d=await r.json();
    if(d.error){div.innerHTML='<div style="color:#e74c3c;padding:12px;background:#ffeaea;border-radius:8px;">'+_escHTML(d.error)+'</div>';return;}
    var html='<div style="background:#f8fff8;border:1px solid #c3e2cf;border-radius:10px;padding:16px;margin-bottom:12px;">';
    html+='<h4 style="margin:0 0 10px;color:#00b894;">&#128203; Lote MP: '+d.lote_mp+'</h4>';
    if(d.material){
      var mat=d.material;
      html+='<div style="font-size:0.88em;margin-bottom:12px;"><b>Material:</b> '+(mat.nombre||d.lote_mp)+' <span style="color:#888;">('+d.lote_mp+')</span>';
      if(mat.proveedor) html+=' | <b>Proveedor:</b> '+mat.proveedor;
      if(mat.fecha_ingreso) html+=' | <b>Ingreso:</b> '+mat.fecha_ingreso.substring(0,10);
      html+='</div>';
    }
    var prods=d.producciones||[];
    html+='<h5 style="margin:0 0 8px;color:#6c5ce7;">Producciones donde se uso ('+prods.length+')</h5>';
    if(prods.length){
      html+='<table style="width:100%;font-size:0.82em;border-collapse:collapse;"><thead><tr style="background:#f0f0f8;"><th style="padding:4px 8px;text-align:left;">Lote PT</th><th style="padding:4px 8px;text-align:left;">Producto</th><th style="padding:4px 8px;text-align:left;">Fecha</th><th style="padding:4px 8px;text-align:right;">Cant (g)</th></tr></thead><tbody>';
      prods.forEach(function(p){
        html+='<tr style="border-bottom:1px solid #eee;"><td style="padding:4px 8px;font-family:monospace;font-size:0.9em;">'+(p.lote_ref||'&#8212;')+'</td><td style="padding:4px 8px;">'+(p.producto||'&#8212;')+'</td><td style="padding:4px 8px;">'+(p.fecha?p.fecha.substring(0,10):'&#8212;')+'</td><td style="padding:4px 8px;text-align:right;">'+Number(p.cantidad_g||0).toLocaleString()+'</td></tr>';
      });
      html+='</tbody></table>';
    } else {
      html+='<p style="color:#999;font-size:0.85em;">No se encontraron producciones para este lote.</p>';
    }
    var clientes=d.clientes_afectados||[];
    if(clientes.length){
      html+='<h5 style="margin:12px 0 8px;color:#e17055;">Clientes que recibieron este material ('+clientes.length+')</h5>';
      html+='<table style="width:100%;font-size:0.82em;border-collapse:collapse;"><thead><tr style="background:#fff3f0;"><th style="padding:4px 8px;text-align:left;">Cliente</th><th style="padding:4px 8px;text-align:left;">Lote PT</th><th style="padding:4px 8px;text-align:left;">Producto</th><th style="padding:4px 8px;text-align:left;">Fecha</th></tr></thead><tbody>';
      clientes.forEach(function(cl){
        html+='<tr style="border-bottom:1px solid #fee;"><td style="padding:4px 8px;">'+(cl.cliente||'&#8212;')+'</td><td style="padding:4px 8px;font-family:monospace;font-size:0.9em;">'+(cl.lote_ref||'&#8212;')+'</td><td style="padding:4px 8px;">'+(cl.producto||'&#8212;')+'</td><td style="padding:4px 8px;">'+(cl.fecha?cl.fecha.substring(0,10):'&#8212;')+'</td></tr>';
      });
      html+='</tbody></table>';
    }
    html+='</div>';
    div.innerHTML=html;
  }catch(e){div.innerHTML='<div style="color:#e74c3c;padding:12px;background:#ffeaea;border-radius:8px;">Error: '+e.message+'</div>';}
}

var _conteoActivo = null;
var _conteoItems = [];
// Filtro actual de tipo_material: '' = todos, 'MP' / 'Envase Primario' /
// 'Envase Secundario' / 'Empaque'
var _conteoTipoFiltro = '';

function setConteoTipo(tipo){
  _conteoTipoFiltro = tipo || '';
  // Marcar tab activo
  document.querySelectorAll('#cnt-tipo-tabs .cnt-tipo-tab').forEach(function(b){
    var isActive = (b.getAttribute('data-tipo') || '') === _conteoTipoFiltro;
    if(isActive){
      b.style.background = '#6d28d9';
      b.style.color = '#fff';
      b.style.borderColor = '#6d28d9';
      b.classList.add('active');
    } else {
      b.style.background = '#fff';
      b.style.color = '#555';
      b.style.borderColor = '#dde';
      b.classList.remove('active');
    }
  });
  // Mostrar etiqueta del tipo seleccionado
  var lbl = document.getElementById('cnt-tipo-label');
  if(lbl){
    if(_conteoTipoFiltro){
      lbl.textContent = '· tipo: ' + _conteoTipoFiltro;
      lbl.style.display = 'inline';
    } else {
      lbl.style.display = 'none';
    }
  }
  // Recargar estanterías + programación cíclica con filtro aplicado
  cargarEstanterias();
  cargarProgramacionCiclica();
}

function _esTipoEE(tipo){
  if(!tipo) return false;
  var t = tipo.toLowerCase();
  return t.indexOf('envase') >= 0 || t.indexOf('empaque') >= 0;
}

async function cargarEstanterias(){
  var sel = document.getElementById('cnt-est-sel');
  if(!sel) return;
  // Si el filtro es E&E, el selector de estantería NO aplica (no hay
  // localización). Mostramos un único option informativo y dejamos que
  // el usuario use el botón "Iniciar" de la fila "Esta semana" arriba.
  if(_esTipoEE(_conteoTipoFiltro)){
    while(sel.options.length > 1) sel.remove(1);
    sel.options[0].textContent = '— No aplica para E&E (cuenta los 3 items asignados arriba)';
    sel.disabled = true;
    return;
  }
  sel.disabled = false;
  if(sel.options[0]) sel.options[0].textContent = '-- Selecciona estanteria --';
  try{
    var url = '/api/conteo/estanterias';
    if(_conteoTipoFiltro){
      url += '?tipo_material=' + encodeURIComponent(_conteoTipoFiltro);
    }
    var r = await fetch(url);
    var data = await r.json();
    while(sel.options.length > 1) sel.remove(1);
    if(!data || data.length === 0){
      var opt = document.createElement('option');
      opt.value = '';
      opt.textContent = _conteoTipoFiltro
        ? '(sin estanterías para tipo "' + _conteoTipoFiltro + '")'
        : '(sin estanterías con stock)';
      opt.disabled = true;
      sel.appendChild(opt);
      return;
    }
    data.forEach(function(e){
      var opt = document.createElement('option');
      opt.value = e.estanteria;
      opt.textContent = e.estanteria + ' (' + e.total_mps + ' items, ' + Math.round(e.stock_total||0).toLocaleString('es-CO') + ' g)';
      sel.appendChild(opt);
    });
  }catch(e){}
}

async function cargarProgramacionCiclica(){
  try{
    // El endpoint cambia de comportamiento según tipo_material:
    //   sin filtro o 'MP'  → rotación por estantería (modo legacy)
    //   E&E (Envase/Empaque) → rotación de 3 ítems determinista por semana
    var url = '/api/conteo/programacion';
    if(_conteoTipoFiltro && _conteoTipoFiltro !== 'MP'){
      url += '?tipo_material=' + encodeURIComponent(_conteoTipoFiltro);
    }
    var r = await fetch(url);
    var d = await r.json();
    var tbody = document.getElementById('cnt-prog-rows');
    if(!tbody) return;
    if(!d.semanas || d.semanas.length === 0){
      var msg = d.mensaje || 'Sin datos de estanter&iacute;as';
      var html = '<tr><td colspan="5" style="padding:18px;background:#fffaf2;border:1px dashed #f0c674;">';
      html += '<div style="font-size:14px;font-weight:600;color:#8b5a00;margin-bottom:8px;">&#x26A0; '+msg+'</div>';
      if(d.diagnostico){
        var dx = d.diagnostico;
        html += '<div style="font-size:12px;color:#555;line-height:1.7;">';
        html += '<div><strong>Catálogo total:</strong> '+dx.total_catalogo+' items activos</div>';
        if(dx.sin_clasificar > 0){
          html += '<div style="color:#b94400;"><strong>'+dx.sin_clasificar+' items</strong> sin tipo asignado (“MP” por defecto)</div>';
        }
        if(dx.tipos_existentes && dx.tipos_existentes.length){
          html += '<div style="margin-top:6px;"><strong>Tipos actualmente en catálogo:</strong></div>';
          html += '<ul style="margin:4px 0 8px 22px;color:#444;">';
          dx.tipos_existentes.forEach(function(t){
            html += '<li><code style="background:#f3f0ea;padding:1px 6px;border-radius:3px;">'+t.tipo+'</code> &mdash; '+t.total+' items</li>';
          });
          html += '</ul>';
        }
        html += '<div style="margin-top:10px;padding:10px 12px;background:#fff;border-left:3px solid #6d28d9;color:#1f5f5b;">'
              + '<strong>Acción sugerida:</strong> '+dx.accion_sugerida+'</div>';
        html += '<div style="margin-top:10px;"><a href="/admin" target="_blank" '
              + 'style="display:inline-block;background:#6d28d9;color:#fff;padding:6px 14px;border-radius:6px;font-size:12px;text-decoration:none;font-weight:600;">'
              + 'Abrir /admin &raquo; tab Banco / diagnóstico</a> '
              + '<span style="margin-left:8px;font-size:11px;color:#888;">(o ir directo al Catálogo MPs en Planta)</span></div>';
        html += '</div>';
      }
      html += '</td></tr>';
      tbody.innerHTML = html;
      return;
    }
    var modoItems = (d.modo === 'items');
    var html = '';
    d.semanas.forEach(function(s){
      var bg = s.es_actual ? 'background:linear-gradient(135deg,#d4f7f2,#e8faf7);font-weight:700;' : '';
      var badge = '';
      if(s.conteo_estado === 'Abierto') badge = '<span style="background:#fff3cd;color:#856404;padding:2px 8px;border-radius:10px;font-size:0.82em;">En Curso</span>';
      else if(s.conteo_estado === 'Cerrado') badge = '<span style="background:#d1f2d1;color:#1a6b1a;padding:2px 8px;border-radius:10px;font-size:0.82em;">Completado</span>';
      else badge = '<span style="background:#f0f0f0;color:#666;padding:2px 8px;border-radius:10px;font-size:0.82em;">Pendiente</span>';
      var semLabel = s.es_actual ? 'Sem. '+s.semana+' (Esta semana)' : 'Sem. '+s.semana;
      var accion = '';
      if(s.es_actual && s.conteo_estado !== 'Cerrado'){
        accion = '<button onclick="iniciarConteoProgramado(\''+_escHTML(String(s.estanteria||'').replace(/\x27/g,"\\\x27"))+'\')" style="padding:4px 12px;background:#6d28d9;color:#fff;border:none;border-radius:6px;font-size:0.82em;cursor:pointer;">'+(s.conteo_estado==='Abierto'?'Retomar':'Iniciar')+'</button>';
      }
      // En modo items, mostrar los códigos+nombres de los 3 ítems en lugar
      // del label sintético "E&E-Empaque-S05"
      var asignacionTxt;
      if(modoItems && s.items_programados){
        asignacionTxt = '<div style="font-size:0.78em;color:#555;font-weight:600;margin-bottom:3px;">3 items a contar:</div>';
        s.items_programados.forEach(function(it){
          asignacionTxt += '<div style="font-size:0.8em;font-family:monospace;color:#1e293b;">• '+_escHTML(it.codigo_mp||'')+' — '+_escHTML(it.nombre||'')+'</div>';
        });
      } else {
        asignacionTxt = _escHTML(s.estanteria||'');
      }
      html += '<tr style="border-bottom:1px solid #e0ece9;'+bg+'">'
            + '<td style="padding:7px 12px;vertical-align:top;">'+semLabel+'</td>'
            + '<td style="padding:7px 12px;vertical-align:top;">'+s.lunes+'</td>'
            + '<td style="padding:7px 12px;font-weight:600;">'+asignacionTxt+'</td>'
            + '<td style="padding:7px 12px;text-align:center;vertical-align:top;">'+badge+'</td>'
            + '<td style="padding:7px 12px;text-align:center;vertical-align:top;">'+accion+'</td>'
            + '</tr>';
    });
    var resumen;
    if(modoItems){
      resumen = 'Tipo: <strong>'+d.tipo_material+'</strong> · Total &iacute;tems: '+d.total_items+
                ' · 3 items por semana · Ciclo completo en ~'+Math.ceil(d.total_items/3)+' semanas';
    } else {
      // Modo legacy MP: aclarar al usuario que solo cubre Materias Primas
      // físicas. Para Envase/Empaque hay que cambiar el filtro arriba.
      var hint = (!_conteoTipoFiltro || _conteoTipoFiltro === 'MP')
        ? ' · <span style="color:#1f5f5b;">Solo Materias Primas. Para Envase Primario/Secundario o Empaque cambia el filtro arriba.</span>'
        : '';
      resumen = 'Total estanter&iacute;as en rotaci&oacute;n: '+d.total_estanterias+
                ' &mdash; ciclo completo cada '+d.total_estanterias+' semanas' + hint;
    }
    html += '<tr style="background:#f5f5f5;font-size:0.8em;color:#888;"><td colspan="5" style="padding:6px 12px;">'+resumen+'</td></tr>';
    tbody.innerHTML = html;
  }catch(e){
    var tbody = document.getElementById('cnt-prog-rows');
    if(tbody) tbody.innerHTML = '<tr><td colspan="5" style="color:#c00;padding:10px;">Error cargando programaci&oacute;n: '+(e.message||e)+'</td></tr>';
  }
}

function iniciarConteoProgramado(estanteria){
  var sel = document.getElementById('cnt-est-sel');
  if(sel){
    for(var i=0; i<sel.options.length; i++){
      if(sel.options[i].value === estanteria){ sel.selectedIndex = i; break; }
    }
  }
  iniciarConteo();
}

async function iniciarConteo(){
  var est = document.getElementById('cnt-est-sel').value;
  var resp = document.getElementById('cnt-responsable').value.trim() || OPER_ACTUAL;
  if(!est){alert('Selecciona una estanteria'); return;}
  try{
    var r = await fetch('/api/conteo/iniciar',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({estanteria:est,responsable:resp})});
    var res = await r.json();
    if(!r.ok){alert(res.error||'Error'); return;}
    _conteoActivo = {id: res.conteo_id, numero: res.numero, estanteria: est};
    if(res.resuming){
      document.getElementById('cnt-msg').innerHTML = '<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:6px;padding:8px 12px;color:#856404;font-size:0.88em;">&#9888; Retomando conteo abierto existente: '+res.numero+'</div>';
    }
    document.getElementById('cnt-numero').textContent = res.numero;
    document.getElementById('cnt-est-label').textContent = est;
    document.getElementById('cnt-panel').style.display = 'block';
    await cargarItemsConteo(est);
  }catch(e){alert('Error: '+e.message);}
}

// Event delegation: botones editar proveedor / eliminar lote dentro del
// conteo ciclico. Reusan los modales de Stock por Lote (mismo patron) —
// se construye un objeto compatible y se pushea a _lotes para que los
// handlers existentes lo encuentren por indice.
document.addEventListener('click', function(e){
  var btnProv = e.target.closest && e.target.closest('.cnt-prov-edit');
  var btnDel = e.target.closest && e.target.closest('.cnt-del-lote');
  // Sebastian 7-may-2026: botón aplicar ajuste por fila (post-guardar)
  var btnAplicar = e.target.closest && e.target.closest('.cnt-aplicar-ajuste');
  // Sebastian 8-may-2026: editar ubicacion (estanteria/posicion) desde el conteo
  var btnUbic = e.target.closest && e.target.closest('.cnt-ubic-edit');
  if(btnAplicar){
    var idxA = parseInt(btnAplicar.getAttribute('data-idx'),10);
    if(!isNaN(idxA)) aplicarAjusteFila(idxA);
    return;
  }
  if(btnUbic){
    var idxU = parseInt(btnUbic.getAttribute('data-idx'),10);
    if(!isNaN(idxU)) abrirEditarUbicacionConteo(idxU);
    return;
  }
  if (!btnProv && !btnDel) return;
  var idx = parseInt((btnProv||btnDel).getAttribute('data-idx'),10);
  if (isNaN(idx) || !_conteoItems || !_conteoItems[idx]) return;
  var ci = _conteoItems[idx];
  // Adaptar al formato que esperan los modales existentes (mismo shape de /api/lotes)
  var fakeIdx = _lotes.push({
    material_id: ci.codigo_mp,
    material_nombre: ci.nombre,
    nombre_inci: ci.inci || '',
    proveedor: ci.proveedor || '',
    lote: ci.lote || '',
    cantidad_g: ci.stock_sistema,
    fecha_vencimiento: ci.fecha_vencimiento || '',
    stock_min_g: 0,
  }) - 1;
  if (btnProv) {
    abrirEditarProveedor(fakeIdx);
  } else {
    abrirEliminarLote(fakeIdx);
  }
});

// ─── Editar ubicacion del lote desde Conteo Ciclico ─────────────────
// Sebastian 8-may-2026: durante el conteo, descubrir que la posicion
// esta mal es comun. Sin esto, hay que cerrar el conteo, ir a Bodega
// MP, ajustar, volver. Mas friccion = menos correcciones = mas drift.
// Llama al endpoint PUT /api/lotes/<mp>/<lote>/ubicacion ya existente.
var _ubicConteoIdx = null;
function abrirEditarUbicacionConteo(idx){
  var ci = _conteoItems && _conteoItems[idx];
  if(!ci){alert('Item no encontrado'); return;}
  _ubicConteoIdx = idx;
  var info = (ci.nombre||'')+' · '+(ci.codigo_mp||'')+(ci.lote?' · Lote '+ci.lote:' · (sin lote)');
  document.getElementById('ubic-cnt-info').textContent = info;
  document.getElementById('ubic-cnt-actual').textContent = 'Actual: '+
    ((ci.estanteria||'').trim()||'(sin estanteria)')+' / '+
    ((ci.posicion||'').trim()||'(sin posicion)');
  document.getElementById('ubic-cnt-est').value = ci.estanteria||'';
  document.getElementById('ubic-cnt-pos').value = ci.posicion||'';
  document.getElementById('ubic-cnt-motivo').value = '';
  document.getElementById('ubic-cnt-msg').innerHTML = '';
  document.getElementById('modal-editar-ubicacion-cnt').style.display = 'flex';
  setTimeout(function(){var el=document.getElementById('ubic-cnt-est');if(el)el.focus();},120);
}
function cerrarEditarUbicacionConteo(){
  document.getElementById('modal-editar-ubicacion-cnt').style.display='none';
  _ubicConteoIdx=null;
}
async function guardarUbicacionConteo(){
  if(_ubicConteoIdx===null) return;
  var ci = _conteoItems[_ubicConteoIdx];
  if(!ci){return;}
  var msgEl = document.getElementById('ubic-cnt-msg');
  var nuevaEst=(document.getElementById('ubic-cnt-est').value||'').trim();
  var nuevaPos=(document.getElementById('ubic-cnt-pos').value||'').trim();
  var motivo=(document.getElementById('ubic-cnt-motivo').value||'').trim();
  if(!nuevaEst && !nuevaPos){
    msgEl.innerHTML='<span style="color:#c00;">Indica al menos estanteria o posicion.</span>';
    return;
  }
  var actEst=(ci.estanteria||'').trim();
  var actPos=(ci.posicion||'').trim();
  if(nuevaEst===actEst && nuevaPos===actPos){
    msgEl.innerHTML='<span style="color:#666;">Sin cambios respecto al actual.</span>';
    return;
  }
  msgEl.innerHTML='<span style="color:#666;">Guardando...</span>';
  var loteUrl = ci.lote && ci.lote!=='S/L' ? encodeURIComponent(ci.lote) : '_SIN_LOTE_';
  try{
    var r=await fetch('/api/lotes/'+encodeURIComponent(ci.codigo_mp)+'/'+loteUrl+'/ubicacion',
      {method:'PUT',headers:{'Content-Type':'application/json'},
       body:JSON.stringify({estanteria:nuevaEst,posicion:nuevaPos,motivo:motivo})});
    var d={};try{d=await r.json();}catch(je){}
    if(r.ok){
      msgEl.innerHTML='<span style="color:#1a8a1a;font-weight:700;">&#10003; '+
        (d.message||'Ubicacion actualizada')+' ('+(d.movimientos_actualizados||0)+' mov)</span>';
      // Hidratar el item en _conteoItems para que el modal no muestre datos viejos
      ci.estanteria = d.estanteria_nueva || nuevaEst;
      ci.posicion = d.posicion_nueva || nuevaPos;
      // Actualizar visualmente la fila (sin re-fetch)
      var estEl = document.getElementById('cnt-est-'+_ubicConteoIdx);
      var posEl = document.getElementById('cnt-pos-'+_ubicConteoIdx);
      if(estEl){estEl.textContent='Est: '+(ci.estanteria||'—');estEl.style.color=ci.estanteria?'#888':'#bbb';}
      if(posEl){posEl.textContent='Pos: '+(ci.posicion||'—');posEl.style.color=ci.posicion?'#888':'#bbb';}
      setTimeout(cerrarEditarUbicacionConteo, 1400);
    }else{
      msgEl.innerHTML='<span style="color:#c00;">Error: '+(d.error||r.status)+
        (d.detail?' &mdash; '+d.detail:'')+'</span>';
    }
  }catch(e){msgEl.innerHTML='<span style="color:#c00;">Error de red: '+e.message+'</span>';}
}

async function cargarItemsConteo(est){
  try{
    var url = '/api/conteo/materiales?estanteria='+encodeURIComponent(est);
    if(_conteoTipoFiltro){
      url += '&tipo_material=' + encodeURIComponent(_conteoTipoFiltro);
    }
    var r = await fetch(url);
    _conteoItems = await r.json();
    var causas = ['Error de conteo','Consumo no descargado','Ingreso no registrado','Error unidad de medida','Merma justificada','Traslado no registrado','Material no identificado','Otro'];
    var causaOpts = causas.map(function(c){return '<option>'+c+'</option>';}).join('');
    // Color por tipo_material para diferenciar visualmente
    var tipoColor = {'MP':'#666','Envase Primario':'#0a66c2','Envase Secundario':'#2980b9','Empaque':'#7c3aed'};
    var h = '';
    _conteoItems.forEach(function(mp, i){
      var tipo = mp.tipo_material || 'MP';
      var col = tipoColor[tipo] || '#666';
      var lote = mp.lote || '';
      var prov = mp.proveedor || '';
      var loteSeg = lote || '_SIN_LOTE_';
      // Wrap row en index para que los handlers _conteoItems[i] sigan funcionando.
      h += '<tr id="cnt-row-'+i+'" data-cod="'+mp.codigo_mp+'" data-lote="'+lote+'">';
      h += '<td style="font-family:monospace;font-size:0.82em;">'+mp.codigo_mp+'<br><span style="font-size:0.7em;color:'+col+';font-weight:700;text-transform:uppercase;letter-spacing:0.4px;">'+tipo+'</span></td>';
      h += '<td style="font-size:0.85em;">'+mp.nombre+(mp.inci?'<br><span style="font-size:0.72em;color:#888;">'+mp.inci+'</span>':'')+'</td>';
      var loteTxt = lote ? '<span style="font-family:monospace;font-size:0.82em;">'+lote+'</span>' : '<span style="color:#bbb;font-style:italic;font-size:0.78em;">— sin lote —</span>';
      var estTxt = mp.estanteria ? '<br><span style="font-size:0.72em;color:#888;" id="cnt-est-'+i+'">Est: '+mp.estanteria+'</span>' : '<br><span style="font-size:0.72em;color:#bbb;" id="cnt-est-'+i+'">Est: —</span>';
      var posTxt = mp.posicion ? '<br><span style="font-size:0.72em;color:#888;" id="cnt-pos-'+i+'">Pos: '+mp.posicion+'</span>' : '<br><span style="font-size:0.72em;color:#bbb;" id="cnt-pos-'+i+'">Pos: —</span>';
      var venTxt = mp.fecha_vencimiento ? '<br><span style="font-size:0.72em;color:#888;">Vence: '+mp.fecha_vencimiento.substr(0,10)+'</span>' : '';
      // Sebastian 8-may-2026: boton para editar ubicacion (estanteria/posicion) desde el conteo
      var btnUbic = '<button class="cnt-ubic-edit" data-idx="'+i+'" title="Cambiar estanteria/posicion del lote" style="margin-left:4px;padding:1px 5px;font-size:0.72em;background:#dbeafe;color:#1e40af;border:1px solid #93c5fd;border-radius:4px;cursor:pointer;">&#128205;&#9999;&#65039;</button>';
      h += '<td>'+loteTxt+btnUbic+estTxt+posTxt+venTxt+'</td>';
      // Proveedor con boton editar (reusa modal y datalist global del flujo Stock por Lote)
      var provHtml = prov ? prov : '<span style="color:#bbb;font-style:italic;font-size:0.78em;">— sin proveedor —</span>';
      h += '<td class="cnt-prov-cell" data-idx="'+i+'" style="font-size:0.82em;color:#475569;">'+provHtml+' <button class="cnt-prov-edit" data-idx="'+i+'" title="Editar proveedor del lote" style="margin-left:3px;padding:1px 5px;font-size:0.72em;background:#e0f2fe;color:#0369a1;border:1px solid #bae6fd;border-radius:4px;cursor:pointer;">&#9999;&#65039;</button></td>';
      h += '<td style="text-align:right;font-weight:600;font-family:monospace;">'+Number(mp.stock_sistema).toLocaleString()+'</td>';
      h += '<td><input type="number" id="cnt-fis-'+i+'" min="0" step="0.1" oninput="calcDiff('+i+','+mp.stock_sistema+','+mp.precio_ref+')" style="width:120px;padding:6px;border:1px solid #dde;border-radius:6px;text-align:right;font-family:monospace;"></td>';
      h += '<td id="cnt-diff-'+i+'" style="text-align:right;font-family:monospace;font-weight:700;">--</td>';
      h += '<td id="cnt-pct-'+i+'" style="font-size:0.85em;">--</td>';
      h += '<td><select id="cnt-causa-'+i+'" style="width:140px;padding:5px;border:1px solid #dde;border-radius:6px;font-size:0.8em;"><option value="">Sin diferencia</option>'+causaOpts+'</select></td>';
      // Acciones: eliminar lote (motivo) + aplicar ajuste (admin · post-guardar)
      h += '<td style="text-align:center;white-space:nowrap;">';
      // Botón aplicar ajuste · solo aparece si el item ya fue guardado y tiene diff != 0
      // Se renderiza placeholder · `cntRefreshAjusteButtons()` lo activa después.
      h += '<button class="cnt-aplicar-ajuste" data-idx="'+i+'" '+
            'style="display:none;margin-right:4px;padding:3px 8px;font-size:0.75em;'+
            'background:#16a34a;color:#fff;border:none;border-radius:4px;cursor:pointer;font-weight:700" '+
            'title="Aplicar ajuste (admin: aprueba >5% como gerencia)">✅ Aplicar</button>';
      h += '<button class="cnt-del-lote" data-idx="'+i+'" title="Eliminar lote (motivo obligatorio)" style="padding:3px 8px;font-size:0.75em;background:#c0392b;color:#fff;border-radius:4px;cursor:pointer;">&#128465;</button>';
      h += '</td>';
      h += '</tr>';
    });
    document.getElementById('cnt-tbody').innerHTML = h || '<tr><td colspan="10" style="text-align:center;color:#999;">Sin materiales en esta estanteria con el filtro seleccionado</td></tr>';
  }catch(e){console.error(e);}
}

function calcDiff(i, stockSis, precioRef){
  var fis = parseFloat(document.getElementById('cnt-fis-'+i).value);
  var diffEl = document.getElementById('cnt-diff-'+i);
  var pctEl = document.getElementById('cnt-pct-'+i);
  var row = document.getElementById('cnt-row-'+i);
  if(isNaN(fis)){diffEl.textContent='--';pctEl.textContent='--';return;}
  var diff = fis - stockSis;
  var pct = stockSis > 0 ? Math.abs(diff/stockSis)*100 : 0;
  diffEl.textContent = (diff >= 0 ? '+' : '') + diff.toLocaleString('es-CO',{maximumFractionDigits:1});
  diffEl.style.color = diff === 0 ? '#27ae60' : diff > 0 ? '#2980b9' : '#e74c3c';
  pctEl.textContent = pct.toFixed(1) + '%';
  if(pct > 5){
    pctEl.style.color = '#e74c3c';
    pctEl.textContent += ' ⚠ GERENCIA';
    row.style.background = '#fff5f5';
  } else {
    pctEl.style.color = pct > 2 ? '#e67e22' : '#27ae60';
    row.style.background = '';
  }
}

async function guardarConteo(){
  if(!_conteoActivo){alert('Inicia un conteo primero'); return;}
  var items = [];
  _conteoItems.forEach(function(mp, i){
    var fisEl = document.getElementById('cnt-fis-'+i);
    if(!fisEl || fisEl.value === '') return;
    items.push({
      codigo_mp: mp.codigo_mp,
      nombre: mp.nombre,
      lote: mp.lote || '',
      stock_sistema: mp.stock_sistema,
      stock_fisico: parseFloat(fisEl.value),
      precio_ref: mp.precio_ref,
      estanteria: mp.estanteria,
      causa_diferencia: document.getElementById('cnt-causa-'+i).value
    });
  });
  try{
    var r = await fetch('/api/conteo/'+_conteoActivo.id+'/guardar',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({items:items})});
    var res = await r.json();
    if(r.ok){
      var msg = 'Guardado. ';
      if(res.items_con_diferencia > 0) msg += res.items_con_diferencia+' item(s) con diferencias.';
      document.getElementById('cnt-resumen').style.display = 'block';
      document.getElementById('cnt-resumen').innerHTML = msg +
        ' Click <b>✅ Aplicar</b> en cada fila con diferencia para que el ajuste se cargue al kardex. '+
        'Diferencias >5% son aprobadas por gerencia (sebastián/alejandro pueden hacerlo desde acá).';
      // Sebastian 7-may-2026: hidratar _conteoItems con item_id de DB y
      // mostrar el botón ✅ Aplicar en filas que tienen diff != 0 y aún no se aplicó.
      if(res.items && res.items.length){
        cntHidratarItemIds(res.items);
      }
      await cargarHistorialConteos();
    } else {
      alert('Error guardar: '+(res.error||r.status));
    }
  }catch(e){alert('Error: '+e.message);}
}

// Sebastian 7-may-2026: tras guardar, asocia cada fila con su conteo_items.id
// (DB) y muestra el botón Aplicar para las que tienen diferencia != 0.
function cntHidratarItemIds(savedItems){
  // Index los items DB por (codigo_mp, lote) para emparejar con _conteoItems[i]
  var idx = {};
  savedItems.forEach(function(it){
    var k = (it.codigo_mp||'')+'|'+(it.lote||'');
    idx[k] = it;
  });
  _conteoItems.forEach(function(mp, i){
    var k = (mp.codigo_mp||'')+'|'+(mp.lote||'');
    var it = idx[k];
    if(!it) return;
    mp._item_id = it.id;
    mp._diferencia = it.diferencia;
    mp._aplicado = it.ajuste_aplicado;
    mp._requiere_gerencia = it.requiere_gerencia;
    mp._aprobado_gerencia = it.aprobado_gerencia;
    var btn = document.querySelector('.cnt-aplicar-ajuste[data-idx="'+i+'"]');
    if(!btn) return;
    if(it.ajuste_aplicado){
      btn.style.display = 'none';
      // Tachar la fila para feedback visual
      var row = document.getElementById('cnt-row-'+i);
      if(row) row.style.opacity = '0.6';
    } else if(Math.abs(it.diferencia) > 0){
      btn.style.display = 'inline-block';
      // Si requiere gerencia, etiquetar
      if(it.requiere_gerencia && !it.aprobado_gerencia){
        btn.innerHTML = '✅ Aplicar (Gerencia)';
        btn.style.background = '#7c3aed';
        btn.title = 'Aprobar como gerencia y aplicar ajuste >5% (admin only)';
      } else {
        btn.innerHTML = '✅ Aplicar';
        btn.style.background = '#16a34a';
      }
    }
  });
}

// Click en botón ✅ Aplicar de una fila · llama /ajustar con item_id
async function aplicarAjusteFila(idx){
  var mp = _conteoItems[idx];
  if(!mp || !mp._item_id){
    alert('Primero hacé click en Guardar para que el item tenga ID en la DB.');
    return;
  }
  if(mp._aplicado){
    alert('Este ajuste ya se aplicó.');
    return;
  }
  var diff = mp._diferencia || 0;
  var tipo = diff > 0 ? 'Entrada' : 'Salida';
  var prefix = (mp._requiere_gerencia && !mp._aprobado_gerencia)
                  ? 'APROBAR como GERENCIA y aplicar ajuste\n\n'
                  : 'Aplicar ajuste\n\n';
  var msg = prefix +
            'Material: '+(mp.nombre||mp.codigo_mp)+'\n'+
            'Diferencia: '+(diff>0?'+':'')+diff.toLocaleString('es-CO')+' g\n'+
            'Movimiento: '+tipo+' de '+Math.abs(diff).toLocaleString('es-CO')+' g\n'+
            'Lote: '+(mp.lote||'sin lote')+'\n\n'+
            '¿Confirmar?';
  if(!confirm(msg)) return;
  try{
    var r = await fetch('/api/conteo/'+_conteoActivo.id+'/ajustar', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({item_id: mp._item_id})
    });
    var d = await r.json();
    if(!r.ok){
      alert('Error: '+(d.error||r.status));
      return;
    }
    mp._aplicado = true;
    mp._aprobado_gerencia = true;
    var btn = document.querySelector('.cnt-aplicar-ajuste[data-idx="'+idx+'"]');
    if(btn) btn.style.display = 'none';
    var row = document.getElementById('cnt-row-'+idx);
    if(row){ row.style.opacity = '0.6'; row.style.background = '#dcfce7'; }
    var resumen = document.getElementById('cnt-resumen');
    if(resumen){
      var loteInfo = d.lote_ajustado ? ' (lote '+d.lote_ajustado+')' : '';
      var stockInfo = (typeof d.stock_lote_post === 'number')
                        ? '<br><small style="color:#16a34a">Stock post-ajuste del lote: '+
                          d.stock_lote_post.toLocaleString('es-CO')+' g · '+
                          'Refrescá Bodega Materias Primas para ver el cambio reflejado.</small>'
                        : '';
      resumen.innerHTML = '✅ '+(d.message||'Ajuste aplicado.')+loteInfo+stockInfo;
    }
  }catch(e){
    alert('Error de red: '+e.message);
  }
}

async function cerrarConteo(){
  if(!_conteoActivo) return;
  if(!confirm('Cerrar el conteo? Ya no se podran editar los conteos fisicos.')) return;
  try{
    var r = await fetch('/api/conteo/'+_conteoActivo.id+'/cerrar',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    var res = await r.json();
    document.getElementById('cnt-msg').innerHTML = '<div class="alert-success">'+res.message+'</div>';
    document.getElementById('cnt-panel').style.display = 'none';
    _conteoActivo = null;
    await cargarHistorialConteos();
    await cargarEstanterias();
  }catch(e){alert('Error: '+e.message);}
}

async function aplicarAjuste(itemId){
  if(!confirm('Aplicar ajuste de inventario? Se registrara un movimiento de correccion en el sistema.')) return;
  try{
    var r = await fetch('/api/conteo/0/ajustar',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({item_id:itemId})});
    var res = await r.json();
    if(r.ok){
      document.getElementById('cnt-msg').innerHTML = '<div class="alert-success">'+res.message+'</div>';
    }else{
      document.getElementById('cnt-msg').innerHTML = '<div class="alert-error">'+(res.error||'Error')+'</div>';
    }
  }catch(e){}
}

async function cargarHistorialConteos(){
  try{
    var r = await fetch('/api/conteo/historial');
    var data = await r.json();
    var tb = document.getElementById('cnt-hist-tbody');
    if(!data.length){tb.innerHTML='<tr><td colspan="8" style="text-align:center;color:#999;">Sin conteos</td></tr>';return;}
    var h = '';
    data.forEach(function(c){
      var estadoColor = c.estado === 'Cerrado' ? '#27ae60' : '#e67e22';
      h += '<tr>';
      h += '<td style="font-family:monospace;font-size:0.85em;">'+c.numero+'</td>';
      h += '<td>'+(c.estanteria||'')+'</td>';
      h += '<td style="font-size:0.82em;">'+(c.fecha_inicio?c.fecha_inicio.substring(0,10):'')+'</td>';
      h += '<td>'+(c.responsable||'')+'</td>';
      h += '<td><span style="color:'+estadoColor+';font-weight:700;">'+c.estado+'</span></td>';
      h += '<td style="text-align:center;">'+c.total_items+'</td>';
      h += '<td style="text-align:center;color:'+(c.items_diferencia>0?'#e74c3c':'#27ae60')+';">'+c.items_diferencia+'</td>';
      h += '<td style="text-align:center;">';
      if(c.items_gerencia > 0) h += '<span style="color:#e74c3c;font-weight:700;">'+c.items_gerencia+' ⚠</span>';
      else h += '<span style="color:#27ae60;">OK</span>';
      h += '</td></tr>';
    });
    tb.innerHTML = h;
  }catch(e){}
}

// Sprint MEE PRO · 20-may-2026
var _MEE_LAST_DATA = null;
var _MEE_TIMER = null;
async function cargarMeeAlertas(){
  var t0 = Date.now();
  try{
    var r=await fetch('/api/mee/alertas'); var d=await r.json(); var res=d.resumen||{};
    var cT=document.getElementById('mee-c-total'); var cB=document.getElementById('mee-c-bajo');
    var cS=document.getElementById('mee-c-semana'); var cM=document.getElementById('mee-c-mes');
    if(cT) cT.textContent=res.total_mee||0;
    if(cB){ cB.textContent=res.bajo_minimo||0; var card=document.getElementById('mee-card-bajo'); if(card) card.style.background=(res.bajo_minimo>0)?'#e74c3c':'#27ae60'; }
    if(cS) cS.textContent=res.movimientos_semana||0;
    if(cM) cM.textContent=res.entradas_mes||0;
    // Sprint MEE PRO · card obsoletos + sección visible
    var cObs = document.getElementById('mee-c-obs');
    var obs = d.obsolescencia||[];
    if(cObs) cObs.textContent = obs.length;
    var obsWrap = document.getElementById('mee-obsoletos-wrap');
    var obsBody = document.getElementById('mee-obsoletos-tbody');
    var obsCount = document.getElementById('mee-obs-count');
    if(obsWrap && obsBody){
      if(obs.length){
        obsWrap.style.display = 'block';
        if(obsCount) obsCount.textContent = '('+obs.length+')';
        obsBody.innerHTML = '<div style="display:flex;flex-wrap:wrap;gap:6px">'+
          obs.slice(0,20).map(function(o){
            return '<div style="background:#fff;border:1px solid #fde68a;border-radius:6px;padding:6px 10px;font-size:11px"><b>'+_escHTML(o.descripcion)+'</b> · '+(o.stock_actual||0)+' '+_escHTML(o.unidad||'und')+' · último '+_escHTML(o.ultimo_mov||'Nunca')+'</div>';
          }).join('')+
          (obs.length>20?'<div style="font-size:11px;color:#92400e;align-self:center;margin-left:6px">+'+(obs.length-20)+' más</div>':'')+
          '</div>';
      } else {
        obsWrap.style.display = 'none';
      }
    }
    var panel=document.getElementById('mee-alertas-panel');
    if(panel){
      if(d.bajo_minimo&&d.bajo_minimo.length>0){
        var h='<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:10px;padding:14px;margin-bottom:10px;"><strong style="color:#856404;">&#9888; '+d.bajo_minimo.length+' materiales bajo stock mínimo</strong><div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:8px;">';
        d.bajo_minimo.forEach(function(m){ var pct=Math.round(m.ratio*100); var col=pct<=0?'#e74c3c':'#e67e22'; h+='<div style="background:white;border:1px solid #ffc107;border-radius:6px;padding:6px 12px;font-size:0.85em;"><span style="font-weight:700;color:'+col+';">'+_escHTML(m.descripcion)+'</span> <span style="color:#888;">['+_escHTML(m.categoria)+'] </span><span style="color:'+col+';">'+m.stock_actual+'/'+m.stock_minimo+' '+_escHTML(m.unidad)+' ('+pct+'%)</span></div>'; });
        h+='</div></div>';
        panel.innerHTML=h;
      } else { panel.innerHTML='<div style="background:#d4edda;border:1px solid #c3e6cb;border-radius:8px;padding:10px 14px;color:#155724;margin-bottom:10px;">&#10003; Todos los MEE sobre stock mínimo</div>'; }
    }
    // Timestamp + auto-refresh boot
    var lu = document.getElementById('mee-last-update');
    if(lu){
      var hora = new Date().toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
      var dur = Math.max(1, Math.round((Date.now()-t0)/100)/10);
      lu.textContent = 'Actualizado '+hora+' · '+dur+'s';
    }
    if(!_MEE_TIMER) _startMeeAutoRefresh();
  }catch(e){}
}
function _startMeeAutoRefresh(){
  if(_MEE_TIMER) clearInterval(_MEE_TIMER);
  _MEE_TIMER = setInterval(function(){
    var chk = document.getElementById('mee-autorefresh');
    if(!chk || !chk.checked) return;
    if(document.visibilityState==='hidden') return;
    var tab = document.getElementById('empaque');
    if(!tab || tab.style.display==='none') return;
    cargarMeeAlertas(); cargarMeeStock();
  }, 60000);
}
function meeScrollToObsoletos(anchor){
  var el = document.getElementById(anchor) || document.getElementsByName(anchor)[0];
  if(el) el.scrollIntoView({behavior:'smooth'});
}
function _cliChip(m){ var cli=(m.cliente||'').trim(); var txt=cli||'General'; var col=cli?'#1d4ed8':'#94a3b8'; var bg=cli?'#dbeafe':'#f1f5f9'; return ' <span onclick="meeSetCliente(&quot;'+_escHTML(m.codigo).replace(/"/g,'&quot;')+'&quot;,&quot;'+_escHTML(txt)+'&quot;)" title="cambiar cliente" style="cursor:pointer;background:'+bg+';color:'+col+';border-radius:8px;padding:1px 7px;font-size:10px;font-weight:700">&#128100; '+_escHTML(txt)+'</span>'; }
async function meeSetCliente(cod, actual){ var c=prompt('Cliente para '+cod+' (vacío = General):', actual==='General'?'':actual); if(c===null) return; try{ var r=await fetch('/api/mee/set-cliente',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({codigo:cod,cliente:c.trim()})}); var d=await r.json(); if(d.ok){ cargarMeeStock(); } else { alert('Error: '+(d.error||'')); } }catch(e){ alert('Error de conexión'); } }
function meeFotoUpload(codigo){
  var i=document.createElement('input'); i.type='file'; i.accept='image/*';
  i.onchange=function(){ var f=i.files[0]; if(!f) return; var rd=new FileReader();
    rd.onload=function(){ var img=new Image(); img.onload=function(){
      var max=440; var sc=Math.min(1, max/Math.max(img.width,img.height));
      var cv=document.createElement('canvas'); cv.width=Math.round(img.width*sc); cv.height=Math.round(img.height*sc);
      cv.getContext('2d').drawImage(img,0,0,cv.width,cv.height);
      var data; try{ data=cv.toDataURL('image/jpeg',0.82); }catch(e){ data=rd.result; }
      _meeSetFoto(codigo, data);
    }; img.onerror=function(){ _meeSetFoto(codigo, rd.result); }; img.src=rd.result; };
    rd.readAsDataURL(f); };
  i.click();
}
async function _meeSetFoto(codigo, data){
  try{ var r=await fetch('/api/mee/set-imagen',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({codigo:codigo,imagen_url:data})}); var d=await r.json(); if(d.ok){ cargarMeeStock(); } else { alert('Error: '+(d.error||'')); } }catch(e){ alert('Error de conexión'); }
}
async function meeFotosShopify(){
  if(!confirm('¿Traer fotos de Shopify para los envases SIN foto (por match de producto Ánimus)?')) return;
  try{ var r=await fetch('/api/mee/shopify-fotos-bulk',{method:'POST'}); var d=await r.json(); if(d.ok){ alert('✓ '+d.actualizados+' envases ahora tienen foto de Shopify'); cargarMeeStock(); } else { alert('Error: '+(d.error||'')); } }catch(e){ alert('Error de conexión'); } }
async function meeVerificarStock(){
  if(!confirm('Recalcular stock_actual de TODOS los MEE desde SUM(movimientos_mee)? Detecta drift entre cache y movimientos. Solo admin para masivo.')) return;
  try{
    var r = await fetch('/api/mee/recalcular-stock', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({}),
    });
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    if(d.cambios && d.cambios.length){
      var resumen = d.cambios.slice(0, 10).map(function(c){
        return c.codigo+': '+c.stock_anterior+' → '+c.stock_calculado+' ('+(c.delta>=0?'+':'')+c.delta+')';
      }).join(' · ');
      alert('✓ '+d.mensaje+' · Primeros 10 cambios: '+resumen);
    } else {
      alert('✓ '+d.mensaje);
    }
    cargarMeeStock(); cargarMeeAlertas();
  }catch(e){ alert('Error red: '+e.message); }
}
function meeExportarExcel(){
  if(!_MEE_LAST_DATA || !(_MEE_LAST_DATA.items||[]).length){
    alert('Cargá MEE primero'); return;
  }
  var cols = ['Código','Descripción','Categoría','Proveedor','Stock','Mínimo','Unidad','Estado',
              'Última Entrada','Última Salida','Días sin mov','Obsoleto'];
  var rows = (_MEE_LAST_DATA.items||[]).map(function(m){
    return [m.codigo||'', m.descripcion||'', m.categoria||'', m.proveedor||'',
            Number(m.stock_actual)||0, Number(m.stock_minimo)||0,
            m.unidad||'und', m.alerta||'',
            m.ultima_entrada||'', m.ultima_salida||'',
            m.dias_sin_mov==null?'':m.dias_sin_mov,
            m.obsoleto?'SI':''];
  });
  dlExcelHTML('MEE_'+fhoy(), cols, rows);
}
async function cargarMeeStock(){
  var cat = '';
  var sel = document.getElementById('mee-cat-filter-bodega') || document.getElementById('mee-cat-filter');
  if(sel) cat = sel.value || '';
  try{
    var r = await fetch('/api/mee/stock?categoria='+encodeURIComponent(cat));
    var d = await r.json();
    if(sel && d.categorias){
      var cur = sel.value;
      // Build full HTML once · Sebastián 1-may-2026 audit: antes era innerHTML+= en loop (N reflows)
      var optsCat = '<option value="">Todas ('+d.total+')</option>';
      d.categorias.forEach(function(c){
        optsCat += '<option value="'+_escHTML(c)+'"'+(c===cur?' selected':'')+'>'+_escHTML(c)+'</option>';
      });
      sel.innerHTML = optsCat;
    }
    var codSel = document.getElementById('mee-codigo-sel');
    if(codSel && d.items){
      var cur2 = codSel.value;
      var optsCod = '<option value="">-- Seleccionar material --</option>';
      window._MEE_IMG = window._MEE_IMG || {};
      window._MEE_DATA = window._MEE_DATA || {};
      d.items.forEach(function(m){
        window._MEE_IMG[m.codigo] = m.imagen_url || '';
        window._MEE_DATA[m.codigo] = {desc:m.descripcion||'', cat:m.categoria||'', prov:m.proveedor||'', stock:(m.stock_actual!=null?m.stock_actual:0), min:(m.stock_minimo||0), unidad:(m.unidad||'und'), zona:(m.zona||''), estante:(m.estanteria||''), pos:(m.posicion||'')};
        optsCod += '<option value="'+_escHTML(m.codigo)+'" data-stock="'+_escHTML(m.stock_actual)+'" data-unidad="'+_escHTML(m.unidad)+'" data-min="'+_escHTML(m.stock_minimo)+'">'+_escHTML(m.codigo)+' — '+_escHTML(m.descripcion)+'</option>';
      });
      codSel.innerHTML = optsCod;
      if(cur2) codSel.value = cur2;
    }
    var tb = document.getElementById('mee-stock-tbody');
    if(!tb) return;
    var search = (document.getElementById('mee-search-input')||{}).value || '';
    var items = d.items || [];
    if(search){
      var q = search.toLowerCase();
      items = items.filter(function(m){
        return (m.descripcion||'').toLowerCase().indexOf(q)>=0 ||
               (m.codigo||'').toLowerCase().indexOf(q)>=0 ||
               (m.proveedor||'').toLowerCase().indexOf(q)>=0;
      });
    }
    var _cliF=(document.getElementById('mee-cli-filter')||{}).value||'';
    if(_cliF==='__GEN__'){ items=items.filter(function(m){return !((m.cliente||'').trim());}); }
    else if(_cliF){ items=items.filter(function(m){return (m.cliente||'')===_cliF;}); }
    window._meeItems = items;  // cache para vista agrupada
    _MEE_LAST_DATA = d;  // Sprint MEE PRO · para Excel + dashboard
    // Sprint MEE PRO · calcular valor total stock COP
    var valorTotal = 0;
    items.forEach(function(m){
      var precio = parseFloat(m.precio_unitario||m.precio||0)||0;
      var stock = parseFloat(m.stock_actual)||0;
      valorTotal += precio * stock;
    });
    var cVal = document.getElementById('mee-c-valor');
    if(cVal) cVal.textContent = '$'+Math.round(valorTotal).toLocaleString('es-CO');
    if(!items.length){
      tb.innerHTML='<tr><td colspan="9" style="text-align:center;color:#999;">Sin items activos</td></tr>'; return;
    }
    var aC={critico:'#e74c3c',bajo:'#e67e22',advertencia:'#f39c12',ok:'#27ae60',sin_minimo:'#95a5a6'};
    var aL={critico:'&#9940; Critico',bajo:'&#9888; Bajo',advertencia:'&#128993; Alerta',ok:'&#10003; OK',sin_minimo:'—'};
    // Agrupar por categoría · envases (Frasco) primero (Sebastián 28-jun)
    var _catOrd={'Envase':1,'Frasco':1,'Impreso':2,'Impresion':2,'Impresión':2,'Serigrafia':2,'Serigrafía':2,'Gotero':3,'Tapa':4,'Etiqueta':5,'Plegadiza':6,'Caja':6};
    items=items.slice().sort(function(a,b){ var oa=_catOrd[a.categoria||'']||50, ob=_catOrd[b.categoria||'']||50; if(oa!==ob) return oa-ob; return (a.descripcion||'').localeCompare(b.descripcion||''); });
    var _catCnt={}; items.forEach(function(m){ var k=m.categoria||'Otros'; _catCnt[k]=(_catCnt[k]||0)+1; });
    var h=''; var _lastCat=null;
    items.forEach(function(m){
      var _cat=m.categoria||'Otros';
      if(_cat!==_lastCat){ _lastCat=_cat; h+='<tr style="background:#ede9fe"><td colspan="9" style="font-weight:800;color:#5b21b6;padding:8px 12px;font-size:13px">&#128230; '+_escHTML(_cat)+' <span style="color:#a78bfa;font-weight:600">('+(_catCnt[_cat]||0)+')</span></td></tr>'; }
      var c=aC[m.alerta]||'#95a5a6';
      var lbl=aL[m.alerta]||'';
      var ob=m.obsoleto?' <span style="background:#ffc107;color:#856404;border-radius:3px;padding:1px 5px;font-size:0.75em;">+90d</span>':'';
      h+='<tr data-cod="'+_escHTML(m.codigo)+'">';
      h+='<td onclick="meeFotoUpload(&quot;'+_escHTML(m.codigo).replace(/"/g,'&quot;')+'&quot;)" title="Subir/cambiar foto" style="cursor:pointer">'+(m.imagen_url?'<img src="'+_escHTML(m.imagen_url)+'" loading="lazy" style="width:72px;height:72px;object-fit:contain;border-radius:6px;border:1px solid #eee;background:#fafafa">':'<span style="display:inline-flex;flex-direction:column;align-items:center;justify-content:center;width:72px;height:72px;border:1.5px dashed #c4b5fd;border-radius:8px;color:#7c3aed;font-size:10px;font-weight:700;background:#faf5ff">&#128247;<span style="font-weight:600;margin-top:2px">subir foto</span></span>')+'</td>';
      h+='<td style="font-family:monospace;font-size:0.78em;color:#555;">'+_escHTML(m.codigo)+'</td>';
      var _loc=[m.zona,m.estanteria,m.posicion].filter(function(x){return x&&String(x).trim();}).join('/');
      var _locChip=_loc?' <span style="background:#ecfeff;color:#0e7490;border:1px solid #a5f3fc;border-radius:4px;padding:1px 5px;font-size:0.72em;font-weight:600;white-space:nowrap" title="Ubicación">&#128205; '+_escHTML(_loc)+'</span>':'';
      h+='<td style="font-size:0.88em;">'+_escHTML(m.descripcion)+ob+_cliChip(m)+_locChip+'</td>';
      h+='<td style="font-size:0.8em;color:#777;">'+_escHTML(m.categoria||'')+'</td>';
      h+='<td style="font-weight:700;">'+m.stock_actual+' <span style="color:#999;font-size:0.8em;">'+_escHTML(m.unidad||'und')+'</span></td>';
      h+='<td style="color:#aaa;font-size:0.88em;">'+(m.stock_minimo||'—')+'</td>';
      h+='<td><span style="color:'+c+';font-weight:600;font-size:0.82em;">'+lbl+'</span></td>';
      h+='<td style="font-size:0.78em;color:#666;max-width:120px;overflow:hidden;text-overflow:ellipsis">'+_escHTML(m.proveedor||'-')+'</td>';
      h+='<td style="white-space:nowrap">';
      h+='<button onclick="meeAjustar(&quot;'+_escHTML(m.codigo).replace(/"/g,'&quot;')+'&quot;)" title="Ajustar stock, mínimo, proveedor, ubicación + rótulo" style="padding:5px 10px;border:none;background:#7c3aed;color:#fff;border-radius:6px;cursor:pointer;font-size:11px;font-weight:700;margin-right:3px">&#9878; Ajustar</button>';
      h+='<button onclick="meeRotulo(&quot;'+_escHTML(m.codigo).replace(/"/g,'&quot;')+'&quot;)" title="Imprimir rótulo del envase" style="padding:5px 9px;border:none;background:#0891b2;color:#fff;border-radius:6px;cursor:pointer;font-size:11px;margin-right:3px">&#128424;&#65039; R&oacute;tulo</button>';
      h+='<button onclick="meeKit(&quot;'+_escHTML(m.codigo).replace(/"/g,'&quot;')+'&quot;)" title="Kit: partes que van juntas (gotero/tapa/etiqueta/plegadiza)" style="padding:5px 9px;border:none;background:#db2777;color:#fff;border-radius:6px;cursor:pointer;font-size:11px;margin-right:3px">&#129513; Kit</button>';
      h+='<button onclick="meeHistorico(&quot;'+_escHTML(m.codigo).replace(/"/g,'&quot;')+'&quot;)" title="Histórico de movimientos" style="padding:5px 9px;border:none;background:#15803d;color:#fff;border-radius:6px;cursor:pointer;font-size:11px;margin-right:3px">&#128202; Hist</button>';
      h+='<button onclick="meeArchivar(&quot;'+_escHTML(m.codigo).replace(/"/g,'&quot;')+'&quot;)" title="Archivar (eliminar)" style="padding:4px 7px;border:none;background:#dc2626;color:#fff;border-radius:4px;cursor:pointer;font-size:11px">&#128465; Borrar</button>';
      h+='</td>';
      h+='</tr>';
    });
    tb.innerHTML=h;
    if(window._meeAgrupado) renderMeeAgrupado();
  }catch(e){ console.error('cargarMeeStock:',e); }
}

// ─── Acciones MEE (paridad con MP) ──────────────────────────────
// Ajustar premium (modal): stock + ubicación (zona/estante/posición) + mínimo · Sebastián 9-jul
function _adjMsg(t,c){ var e=document.getElementById('mee-adj-msg'); if(e){e.textContent=t; e.style.color=c||'#334155';} }
async function meeAjustar(codigo){
  var dd=(window._MEE_DATA||{})[codigo]||{};
  var m=document.getElementById('mee-adj-modal'); if(!m){ alert('No se pudo abrir'); return; }
  var st=(dd.stock!=null?dd.stock:0);
  document.getElementById('mee-adj-cod').textContent=codigo;
  document.getElementById('mee-adj-desc').textContent=dd.desc||'';
  document.getElementById('mee-adj-stockact').textContent=st+' '+(dd.unidad||'und');
  document.getElementById('mee-adj-cant').value=st;
  document.getElementById('mee-adj-min').value=(dd.min||0);
  var _pv=document.getElementById('mee-adj-prov'); if(_pv) _pv.value=dd.prov||'';
  document.getElementById('mee-adj-motivo').value='';
  _adjMsg('');
  m.dataset.cod=codigo; m.style.display='flex';
  await _meeCargarUbic();
  _meeFillUbic('mee-adj-zona','zona',dd.zona||'');
  _meeFillUbic('mee-adj-estante','estante',dd.estante||'');
  _meeFillUbic('mee-adj-pos','posicion',dd.pos||'');
}
function meeAjustarClose(){ var m=document.getElementById('mee-adj-modal'); if(m) m.style.display='none'; }
function meeAjustarRotulo(){
  var m=document.getElementById('mee-adj-modal'); var cod=(m&&m.dataset.cod)||''; if(!cod) return;
  var cant=parseFloat(document.getElementById('mee-adj-cant').value)||0;
  window.open('/rotulo-recepcion-mee/'+encodeURIComponent(cod)+'/'+(cant>0?cant:1),'_blank');
}
function meeRotulo(codigo){
  var dd=(window._MEE_DATA||{})[codigo]||{}; var cant=parseFloat(dd.stock)||0;
  window.open('/rotulo-recepcion-mee/'+encodeURIComponent(codigo)+'/'+(cant>0?cant:1),'_blank');
}
// ─── Kit de partes por envase (Sebastián 9-jul) ───────────────────────────────
var _kitPartes=[];
function meeKit(codigo){
  var m=document.getElementById('mee-kit-modal'); if(!m){ alert('No se pudo abrir'); return; }
  var dd=(window._MEE_DATA||{})[codigo]||{};
  m.dataset.cod=codigo;
  document.getElementById('mee-kit-cod').textContent=codigo;
  document.getElementById('mee-kit-desc').textContent=dd.desc||'';
  _kitPartes=[]; _kitRender();
  _kitFillDropdown(codigo);
  m.style.display='flex';
  fetch('/api/mee/partes?codigo='+encodeURIComponent(codigo),{credentials:'same-origin'}).then(function(r){return r.json();}).then(function(d){
    _kitPartes=((d&&d.partes)||[]).map(function(p){return {codigo:p.codigo, cantidad:(p.cantidad_por_unidad||1), desc:(p.descripcion||'')};});
    _kitRender();
  }).catch(function(){ _kitRender(); });
}
function meeKitClose(){ var m=document.getElementById('mee-kit-modal'); if(m) m.style.display='none'; }
function _kitFillDropdown(self){
  var sel=document.getElementById('mee-kit-sel'); if(!sel) return;
  var data=window._MEE_DATA||{}; var su=(self||'').toUpperCase(); var byCat={};
  Object.keys(data).forEach(function(cod){ if(cod.toUpperCase()===su) return; var dd=data[cod]||{}; var cat=((dd.cat||'').trim())||'Otro'; (byCat[cat]=byCat[cat]||[]).push(cod); });
  var h='<option value="">-- elegí la parte por tipo --</option>';
  Object.keys(byCat).sort().forEach(function(cat){ h+='<optgroup label="'+_meeEscOpt(cat)+'">'; byCat[cat].sort().forEach(function(cod){ var dd=data[cod]||{}; h+='<option value="'+_meeEscOpt(cod)+'">'+_meeEscOpt(cod)+' — '+_meeEscOpt(dd.desc||'')+'</option>'; }); h+='</optgroup>'; });
  sel.innerHTML=h;
}
function _kitRender(){
  var box=document.getElementById('mee-kit-list'); if(!box) return;
  if(!_kitPartes.length){ box.innerHTML='<div style="color:#94a3b8;font-size:13px;padding:8px 0">&mdash; sin partes &middot; este envase va solo &mdash;</div>'; return; }
  box.innerHTML=_kitPartes.map(function(p,i){ return '<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #f1f5f9"><b style="font-family:monospace;font-size:12px;color:#1e293b">'+_meeEscOpt(p.codigo)+'</b> <span style="flex:1;font-size:12px;color:#475569">'+_meeEscOpt(p.desc||'')+'</span> <span style="font-size:12px;color:#64748b">&times;'+p.cantidad+'</span> <a onclick="meeKitDelParte('+i+')" style="color:#dc2626;cursor:pointer;font-weight:800;font-size:15px" title="Quitar">&times;</a></div>'; }).join('');
}
function meeKitAddParte(){
  var sel=document.getElementById('mee-kit-sel'); var cant=document.getElementById('mee-kit-cant');
  if(!sel||!sel.value) return;
  if(_kitPartes.some(function(p){return p.codigo===sel.value;})){ sel.value=''; return; }
  var c=parseFloat(cant?cant.value:1)||1; if(c<=0)c=1;
  var dd=(window._MEE_DATA||{})[sel.value]||{};
  _kitPartes.push({codigo:sel.value, cantidad:c, desc:(dd.desc||'')});
  sel.value=''; if(cant)cant.value='1'; _kitRender();
}
function meeKitDelParte(i){ _kitPartes.splice(i,1); _kitRender(); }
async function meeKitGuardar(){
  var m=document.getElementById('mee-kit-modal'); var cod=(m&&m.dataset.cod)||''; if(!cod) return;
  try{
    var r=await fetch('/api/mee/'+encodeURIComponent(cod)+'/partes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({partes:_kitPartes.map(function(p){return {codigo:p.codigo, cantidad:p.cantidad};})})});
    var d=await r.json();
    if(r.ok&&d.ok){ meeKitClose(); _toast('Kit guardado · '+d.n_partes+' parte(s)',1); }
    else { alert('Error: '+((d&&d.error)||r.status)); }
  }catch(e){ alert('Error de red'); }
}
// Catálogo de ubicaciones (dropdowns · Sebastián 9-jul) · zona/estante/posición desde el server + "Agregar"
async function _meeCargarUbic(){
  if(window._MEE_UBIC) return window._MEE_UBIC;
  try{
    var r=await fetch('/api/mee/ubicaciones',{credentials:'same-origin'}); var d=await r.json();
    if(r.ok&&d.ok){ window._MEE_UBIC={zona:d.zona||[],estante:d.estante||[],posicion:d.posicion||[]}; }
    else { window._MEE_UBIC={zona:[],estante:[],posicion:[]}; }
  }catch(e){ window._MEE_UBIC={zona:[],estante:[],posicion:[]}; }
  return window._MEE_UBIC;
}
function _meeFillUbic(selId, tipo, current){
  var sel=document.getElementById(selId); if(!sel) return;
  var lst=(((window._MEE_UBIC||{})[tipo])||[]).slice();
  if(current && lst.indexOf(current)<0) lst.unshift(current);
  var h='<option value="">&mdash; sin asignar &mdash;</option>';
  lst.forEach(function(v){ h+='<option value="'+_escHTML(v)+'"'+(v===current?' selected':'')+'>'+_escHTML(v)+'</option>'; });
  h+='<option value="__add__">&#10133; Agregar&hellip;</option>';
  sel.innerHTML=h;
}
async function meeUbicChange(sel, tipo){
  if(sel.value!=='__add__') return;
  var v=prompt('Nueva '+(tipo==='posicion'?'posición':tipo)+':'); v=(v||'').trim();
  if(!v){ sel.value=''; return; }
  try{
    var r=await fetch('/api/mee/ubicaciones/agregar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tipo:tipo,valor:v})});
    var d=await r.json();
    if(r.ok&&d.ok){ window._MEE_UBIC=window._MEE_UBIC||{}; window._MEE_UBIC[tipo]=d[tipo]||((window._MEE_UBIC[tipo]||[]).concat([v])); _meeFillUbic(sel.id, tipo, v); }
    else { alert('Error: '+(d.error||'')); sel.value=''; }
  }catch(e){ alert('Error de red'); sel.value=''; }
}
async function meeAjustarGuardar(){
  var m=document.getElementById('mee-adj-modal'); var codigo=m.dataset.cod||'';
  var dd=(window._MEE_DATA||{})[codigo]||{}; var st=(dd.stock!=null?parseFloat(dd.stock):0);
  var cant=parseFloat(document.getElementById('mee-adj-cant').value);
  var min=parseFloat(document.getElementById('mee-adj-min').value);
  var motivo=(document.getElementById('mee-adj-motivo').value||'').trim();
  var _pv=document.getElementById('mee-adj-prov');
  var body={ zona:document.getElementById('mee-adj-zona').value||'', estanteria:document.getElementById('mee-adj-estante').value||'', posicion:document.getElementById('mee-adj-pos').value||'', proveedor:(_pv?_pv.value:'')||'' };
  if(!isNaN(min)) body.stock_minimo=min;
  var cambiaStock=!isNaN(cant) && cant!==st;
  if(cambiaStock){
    if(cant<0){ _adjMsg('Cantidad inválida','#dc2626'); return; }
    if(!motivo){ _adjMsg('Poné el motivo del cambio de stock','#dc2626'); return; }
    body.cantidad_nueva=cant; body.motivo=motivo;
  }
  _adjMsg('Guardando…','#7c3aed');
  try{
    var r=await fetch('/api/mee/'+encodeURIComponent(codigo)+'/ajustar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(r.ok&&d.ok){ meeAjustarClose(); _toast('Guardado'+(cambiaStock?(' · stock '+d.stock_anterior+' → '+d.stock_nuevo):''),1); cargarMeeStock(); }
    else { _adjMsg('Error: '+(d.error||r.status),'#dc2626'); }
  }catch(e){ _adjMsg('Error de red','#dc2626'); }
}

async function meeProveedor(codigo){
  var prov = prompt('Proveedor para '+codigo+' (vacío para limpiar):', '');
  if(prov===null) return;
  try {
    var r = await fetch('/api/mee/'+encodeURIComponent(codigo)+'/proveedor', {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({proveedor: prov.trim()})
    });
    if(!r.ok){ alert('Error'); return; }
    _toast('Proveedor actualizado', 1);
    cargarMeeStock();
  } catch(e){ alert('Error: '+e.message); }
}

async function meeMin(codigo, actual){
  var n = prompt('Nuevo stock mínimo para '+codigo+' (actual: '+actual+'):', actual);
  if(n===null) return;
  var num = parseFloat(n); if(isNaN(num) || num<0){ alert('Inválido'); return; }
  try {
    var r = await fetch('/api/mee/'+encodeURIComponent(codigo)+'/stock-minimo', {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({stock_minimo: num})
    });
    if(!r.ok){ alert('Error'); return; }
    _toast('Mínimo actualizado', 1);
    cargarMeeStock();
  } catch(e){ alert('Error: '+e.message); }
}

async function meeHistorico(codigo){
  try {
    var r = await fetch('/api/mee/'+encodeURIComponent(codigo)+'/historico');
    var d = await r.json();
    var movs = d.movimientos || [];
    var html = '<div style="position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:99999;display:flex;align-items:center;justify-content:center;padding:20px" id="mee-hist-modal" onclick="if(event.target===this)this.remove()">'+
      '<div style="background:#fff;border-radius:14px;padding:20px;width:800px;max-width:100%;max-height:90vh;overflow-y:auto" onclick="event.stopPropagation()">'+
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">'+
          '<h3 style="margin:0">📊 Histórico · '+_escHTML(codigo)+'</h3>'+
          '<button onclick="document.getElementById(&quot;mee-hist-modal&quot;).remove()" style="background:transparent;border:1px solid #d6d3d1;border-radius:6px;width:32px;height:32px;cursor:pointer;font-size:16px">&#10005;</button>'+
        '</div>'+
        (movs.length ?
          '<table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr>'+
            '<th style="background:#fafaf9;padding:8px;text-align:left;font-size:11px;text-transform:uppercase">Fecha</th>'+
            '<th style="background:#fafaf9;padding:8px;text-align:left;font-size:11px;text-transform:uppercase">Tipo</th>'+
            '<th style="background:#fafaf9;padding:8px;text-align:right;font-size:11px;text-transform:uppercase">Cantidad</th>'+
            '<th style="background:#fafaf9;padding:8px;text-align:left;font-size:11px;text-transform:uppercase">Lote/Batch</th>'+
            '<th style="background:#fafaf9;padding:8px;text-align:left;font-size:11px;text-transform:uppercase">Responsable</th>'+
            '<th style="background:#fafaf9;padding:8px;text-align:left;font-size:11px;text-transform:uppercase">Observaciones</th>'+
          '</tr></thead><tbody>'+
          movs.map(function(m){
            var tCol = m.tipo==='Entrada'?'#16a34a':m.tipo==='Salida'?'#dc2626':'#7c3aed';
            return '<tr style="border-bottom:1px solid #f5f5f4'+(m.anulado?';opacity:0.5;text-decoration:line-through':'')+'">'+
              '<td style="padding:7px;font-size:12px">'+_escHTML((m.fecha||'').substring(0,16))+'</td>'+
              '<td style="padding:7px"><span style="background:'+tCol+'22;color:'+tCol+';padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700">'+_escHTML(m.tipo)+'</span></td>'+
              '<td style="padding:7px;text-align:right;font-weight:700">'+m.cantidad+' '+_escHTML(m.unidad||'und')+'</td>'+
              '<td style="padding:7px;font-size:11px;color:#666">'+_escHTML(m.lote_ref||m.batch_ref||'-')+'</td>'+
              '<td style="padding:7px;font-size:11px;color:#666">'+_escHTML(m.responsable||'-')+'</td>'+
              '<td style="padding:7px;font-size:11px;color:#666;max-width:300px;word-wrap:break-word">'+_escHTML(m.observaciones||'')+'</td>'+
            '</tr>';
          }).join('')+
          '</tbody></table>'
          : '<div style="text-align:center;color:#a8a29e;padding:40px">Sin movimientos registrados</div>')+
      '</div></div>';
    document.body.insertAdjacentHTML('beforeend', html);
  } catch(e){ alert('Error: '+e.message); }
}

async function meeArchivar(codigo){
  if(!confirm('¿Archivar (eliminar de la lista) "'+codigo+'"? Los movimientos históricos se conservan.')) return;
  try {
    var r = await fetch('/api/mee/'+encodeURIComponent(codigo), {method:'DELETE'});
    if(!r.ok){ alert('Error'); return; }
    _toast(codigo+' archivado', 1);
    cargarMeeStock();
  } catch(e){ alert('Error: '+e.message); }
}

async function meeImportarExcel(){
  if(!confirm('Importar inventario MEE desde el Excel cargado?\n\n68 items en 5 categorías (Envases, Goteros, Tapas, Etiquetas, Plegadizas).\n\nLos códigos existentes se actualizan, los nuevos se crean.')) return;
  try {
    // Cargar JSON desde el repo
    var rJson = await fetch('/static/scripts/mee_excel_import.json');
    if(!rJson.ok){
      // Fallback: pedir URL manual
      alert('No se encuentra scripts/mee_excel_import.json. Asegúrate de hacer deploy.');
      return;
    }
    var items = await rJson.json();
    var r = await fetch('/api/mee/import-bulk', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({items: items, modo: 'upsert'})
    });
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    alert('✅ Importación completa\n\nInsertados: '+d.insertados+'\nActualizados: '+d.actualizados+'\nTotal: '+d.total_recibidos);
    cargarMeeStock();
  } catch(e){ alert('Error: '+e.message); }
}

function meeAgrupadoToggle(){
  window._meeAgrupado = !window._meeAgrupado;
  var tabla = document.getElementById('mee-tabla-estandar');
  var wrap = document.getElementById('mee-agrupado-wrap');
  var btn = document.getElementById('mee-agrupado-btn');
  if(window._meeAgrupado){
    tabla.style.display = 'none';
    wrap.style.display = 'block';
    btn.innerHTML = '📋 Lista plana';
    renderMeeAgrupado();
  } else {
    tabla.style.display = '';
    wrap.style.display = 'none';
    btn.innerHTML = '📑 Agrupado';
  }
}

function renderMeeAgrupado(){
  var wrap = document.getElementById('mee-agrupado-wrap');
  var items = window._meeItems || [];
  // Agrupar por categoria
  var grupos = {};
  items.forEach(function(m){
    var cat = m.categoria || 'Sin categoría';
    if(!grupos[cat]) grupos[cat] = [];
    grupos[cat].push(m);
  });
  var cats = Object.keys(grupos).sort();
  var aC={critico:'#e74c3c',bajo:'#e67e22',advertencia:'#f39c12',ok:'#27ae60',sin_minimo:'#95a5a6'};
  wrap.innerHTML = cats.map(function(cat){
    var grupo = grupos[cat];
    var totalStock = grupo.reduce(function(a,m){return a+(m.stock_actual||0)},0);
    var nBajo = grupo.filter(function(m){return m.alerta==='critico'||m.alerta==='bajo'}).length;
    return '<details style="margin-bottom:10px;background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:14px 16px" open>'+
      '<summary style="cursor:pointer;font-weight:700;color:#1c1917;display:flex;align-items:center;gap:10px;list-style:none">'+
        '<span style="font-size:15px">📦 '+_escHTML(cat)+'</span>'+
        '<span style="font-size:12px;color:#78716c;font-weight:500">'+grupo.length+' items · '+totalStock.toLocaleString('es-CO')+' und total'+
          (nBajo>0?' · <span style="color:#dc2626;font-weight:700">'+nBajo+' bajo mínimo</span>':'')+'</span>'+
      '</summary>'+
      '<div style="margin-top:10px;display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:8px">'+
        grupo.map(function(m){
          var col = aC[m.alerta]||'#27ae60';
          return '<div style="background:#fafaf9;border:1px solid #e7e5e4;border-left:3px solid '+col+';border-radius:8px;padding:10px;cursor:pointer" onclick="meeHistorico(&quot;'+_escHTML(m.codigo).replace(/"/g,'&quot;')+'&quot;)">'+
            '<div style="font-weight:600;font-size:12px;color:#1c1917">'+_escHTML(m.descripcion)+'</div>'+
            '<div style="font-size:10px;color:#78716c;margin-top:2px;font-family:monospace">'+_escHTML(m.codigo)+'</div>'+
            '<div style="display:flex;justify-content:space-between;margin-top:6px;align-items:center">'+
              '<span style="font-weight:700;font-size:14px;color:#1c1917">'+(m.stock_actual||0).toLocaleString('es-CO')+' '+_escHTML(m.unidad||'und')+'</span>'+
              '<span style="font-size:10px;color:#999">min '+(m.stock_minimo||0)+'</span>'+
            '</div>'+
          '</div>';
        }).join('')+
      '</div>'+
    '</details>';
  }).join('');
}
function meeActualizarTipo(tipo){ var iS=tipo==='Salida'; var lg=document.getElementById('mee-lote-group'); var bg=document.getElementById('mee-batch-group'); if(lg) lg.style.display=iS?'none':'block'; if(bg) bg.style.display=iS?'block':'none'; }
function meeSubTab(name){
  ['recepcion','inventario'].forEach(function(t){
    var p=document.getElementById('meepane-'+t); if(p) p.style.display=(t===name?'block':'none');
    var b=document.getElementById('meest-'+t); if(b){ b.style.color=(t===name?'#6d28d9':'#64748b'); b.style.borderBottom=(t===name?'3px solid #6d28d9':'3px solid transparent'); }
  });
  if(name==='inventario' && typeof cargarMeeStock==='function'){ try{ cargarMeeStock(); }catch(e){} }
}
function _meeFoto(cod){ var box=document.getElementById('mee-foto-box'); var img=document.getElementById('mee-foto-img'); var vac=document.getElementById('mee-foto-vacio'); if(!box||!img) return; var u=(window._MEE_IMG||{})[cod]||''; if(u){ img.src=u; box.style.display='block'; if(vac) vac.style.display='none'; } else { box.style.display='none'; if(vac) vac.style.display='block'; } }
async function meeCargarPorCalificar(){
  var box=document.getElementById('mee-calificar-box'); var list=document.getElementById('mee-calificar-list'); var cnt=document.getElementById('mee-calif-count');
  if(!box||!list) return;
  try{
    var r=await fetch('/api/mee/por-calificar'); var d=await r.json(); var ps=d.pendientes||[];
    if(cnt) cnt.textContent=ps.length;
    if(!ps.length){ box.style.display='none'; list.innerHTML=''; return; }
    list.innerHTML=ps.map(function(p){ return '<div style="display:flex;gap:8px;align-items:center;justify-content:space-between;background:#fff;border:1px solid #bfdbfe;border-radius:6px;padding:8px 10px;margin-bottom:6px;flex-wrap:wrap"><span style="font-size:12px"><b>'+_escHTML(p.codigo)+'</b> — '+_escHTML(p.descripcion)+'</span><button data-cod="'+_escHTML(p.codigo)+'" data-desc="'+_escHTML(p.descripcion)+'" onclick="meeAbrirCalificar(this)" style="background:#1d4ed8;color:#fff;border:none;border-radius:5px;padding:5px 10px;font-size:11px;font-weight:700;cursor:pointer">Calificar</button></div>'; }).join('');
    box.style.display='block';
  }catch(e){}
}
function meeAbrirCalificar(btn){ var cod=btn.getAttribute('data-cod'); var desc=btn.getAttribute('data-desc'); var m=document.getElementById('mee-calif-modal'); if(!m) return; var cc=document.getElementById('mc-codigo'); if(cc)cc.value=cod; var nn=document.getElementById('mee-calif-nombre'); if(nn)nn.textContent=cod+' — '+(desc||''); ['mc-capacidad','mc-material','mc-medidas','mc-documentos'].forEach(function(idd){var e=document.getElementById(idd); if(e)e.checked=false;}); var nt=document.getElementById('mc-notas'); if(nt)nt.value=''; m.style.display='block'; }
function meeCalifClose(){ var m=document.getElementById('mee-calif-modal'); if(m) m.style.display='none'; }
async function meeCalificar(){
  var cod=(document.getElementById('mc-codigo')||{}).value||'';
  var det={capacidad:!!(document.getElementById('mc-capacidad')||{}).checked, material:!!(document.getElementById('mc-material')||{}).checked, medidas:!!(document.getElementById('mc-medidas')||{}).checked, documentos:!!(document.getElementById('mc-documentos')||{}).checked, notas:(document.getElementById('mc-notas')||{}).value||''};
  if(!det.capacidad||!det.material||!det.medidas||!det.documentos){ alert('Marcá los 4 items del checklist para calificar.'); return; }
  try{ var r=await fetch('/api/mee/calificar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({codigo:cod,detalle:det})}); var d=await r.json(); if(d.ok){ meeCalifClose(); meeCargarPorCalificar(); } else { alert('Error: '+(d.error||'')); } }catch(e){ alert('Error de conexión'); } }
async function meeCargarCuarentena(){
  var box=document.getElementById('mee-cuarentena-box'); var list=document.getElementById('mee-cuarentena-list'); var cnt=document.getElementById('mee-cuar-count');
  if(!box||!list) return;
  try{
    var r=await fetch('/api/mee/cuarentena-pendientes'); var d=await r.json(); var ps=d.pendientes||[];
    if(cnt) cnt.textContent=ps.length;
    if(!ps.length){ box.style.display='none'; list.innerHTML=''; return; }
    list.innerHTML=ps.map(function(p){ return '<div style="display:flex;gap:8px;align-items:center;justify-content:space-between;background:#fff;border:1px solid #fed7aa;border-radius:6px;padding:8px 10px;margin-bottom:6px;flex-wrap:wrap"><span style="font-size:12px"><b>'+_escHTML(p.codigo)+'</b> — '+_escHTML(p.descripcion)+' · '+p.cantidad+' '+_escHTML(p.unidad)+(p.zona?(' · zona '+_escHTML(p.zona)):'')+(p.lote?(' · lote '+_escHTML(p.lote)):'')+'</span><span style="display:flex;gap:6px"><button onclick="meeCuarLiberar('+p.id+')" style="background:#16a34a;color:#fff;border:none;border-radius:5px;padding:5px 10px;font-size:11px;font-weight:700;cursor:pointer">&#10003; Liberar</button><button onclick="meeCuarRechazar('+p.id+')" style="background:#dc2626;color:#fff;border:none;border-radius:5px;padding:5px 10px;font-size:11px;font-weight:700;cursor:pointer">Rechazar</button></span></div>'; }).join('');
    box.style.display='block';
  }catch(e){}
}
function meeCuarLiberar(id){ meeCuarentena(id,'liberar'); }
function meeCuarRechazar(id){ meeCuarentena(id,'rechazar'); }
async function meeCuarentena(id, accion){ if(accion==='rechazar' && !confirm('¿Rechazar esta recepción de envase?')) return; try{ var r=await fetch('/api/mee/cuarentena/'+id+'/'+accion,{method:'POST'}); var d=await r.json(); if(d.ok){ meeCargarCuarentena(); cargarMeeStock(); } else { alert('Error: '+(d.error||'')); } }catch(e){ alert('Error de conexión'); } }
async function meeCargarPartesRecep(cod){
  var box=document.getElementById('mee-partes-recep'); var list=document.getElementById('mee-partes-recep-list');
  if(!box||!list) return;
  if(!cod){ box.style.display='none'; list.innerHTML=''; return; }
  try{
    var r=await fetch('/api/mee/partes?codigo='+encodeURIComponent(cod)); var d=await r.json(); var ps=d.partes||[];
    if(!ps.length){ box.style.display='none'; list.innerHTML=''; return; }
    list.innerHTML=ps.map(function(p){ return '<div style="display:flex;gap:8px;align-items:center;margin-bottom:6px"><span style="flex:2;font-size:12px"><b>'+_escHTML(p.codigo)+'</b> — '+_escHTML(p.descripcion||'')+'</span><input type="number" min="0" step="1" id="mprc-'+_escHTML(p.codigo)+'" placeholder="0" style="flex:1;max-width:100px" title="cantidad recibida de esta parte"></div>'; }).join('');
    box.style.display='block';
  }catch(e){ box.style.display='none'; }
}
async function meeRegistrarPartes(){
  var inputs=document.querySelectorAll('[id^="mprc-"]'); var n=0;
  for(var i=0;i<inputs.length;i++){ var el=inputs[i]; var q=parseFloat(el.value)||0; if(q>0){ var cod=el.id.substring(5);
    try{ var rr=await fetch('/api/mee/movimiento',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tipo:'Entrada',codigo:cod,cantidad:q,unidad:'und',lote_ref:'',observaciones:'Parte recibida con el empaque'})}); var dd=await rr.json(); if(rr.ok && !dd.error) n++; }catch(e){} } }
  return n;
}
function _meeAutofill(cod){ var dd=(window._MEE_DATA||{})[cod]||{}; var de=document.getElementById('mee-descripcion'); if(de)de.value=dd.desc||''; var ce=document.getElementById('mee-categoria'); if(ce)ce.value=dd.cat||''; var pe=document.getElementById('mee-proveedor'); if(pe)pe.value=dd.prov||''; }
function meeCalcValor(){ var q=parseFloat((document.getElementById('mee-cantidad')||{}).value)||0; var p=parseFloat((document.getElementById('mee-precio')||{}).value)||0; var v=document.getElementById('mee-valor'); if(v){ var t=q*p; v.value=t>0?('$'+t.toLocaleString('es-CO')):''; } }
function _meeWizNorm(s){ return String(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toUpperCase().replace(/[^A-Z0-9]/g,''); }
var _meeWizPartes=[];
function _meeEscOpt(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function meeWizFillPartes(){ var sel=document.getElementById('mee-wiz-parte-sel'); if(!sel) return; var data=window._MEE_DATA||{}; var byCat={}; Object.keys(data).forEach(function(cod){ var dd=data[cod]||{}; var cat=((dd.cat||'').trim())||'Otro'; (byCat[cat]=byCat[cat]||[]).push(cod); }); var h='<option value="">-- elegí el componente por tipo --</option>'; Object.keys(byCat).sort().forEach(function(cat){ h+='<optgroup label="'+_meeEscOpt(cat)+'">'; byCat[cat].sort().forEach(function(cod){ var dd=data[cod]||{}; h+='<option value="'+_meeEscOpt(cod)+'">'+_meeEscOpt(cod)+' — '+_meeEscOpt(dd.desc||'')+'</option>'; }); h+='</optgroup>'; }); sel.innerHTML=h; }
function meeWizRenderPartes(){ var box=document.getElementById('mee-wiz-partes-list'); if(!box) return; box.innerHTML=_meeWizPartes.map(function(p,i){ return '<span style="display:inline-block;background:#ede9fe;color:#5b21b6;border-radius:8px;padding:2px 8px;margin:2px 4px 2px 0;font-size:12px;font-weight:600">'+p.codigo+' &times;'+p.cantidad+' <a onclick="meeWizDelParte('+i+')" style="color:#dc2626;cursor:pointer;font-weight:800;margin-left:3px">&times;</a></span>'; }).join('') || '<span style="font-size:11px;color:#cbd5e1">— sin partes —</span>'; }
function meeWizAddParte(){ var sel=document.getElementById('mee-wiz-parte-sel'); var cant=document.getElementById('mee-wiz-parte-cant'); if(!sel||!sel.value) return; var c=parseFloat(cant.value)||1; if(_meeWizPartes.some(function(p){return p.codigo===sel.value;})) return; _meeWizPartes.push({codigo:sel.value, cantidad:c}); sel.value=''; if(cant) cant.value='1'; meeWizRenderPartes(); }
function meeWizDelParte(i){ _meeWizPartes.splice(i,1); meeWizRenderPartes(); }
function meeWizOpen(){ var m=document.getElementById('mee-wiz-modal'); if(m) m.style.display='block'; ['mee-wiz-tipo','mee-wiz-material','mee-wiz-metodo','mee-wiz-car','mee-wiz-prod','mee-wiz-ml','mee-wiz-tono','mee-wiz-desc','mee-wiz-cliente'].forEach(function(idd){var el=document.getElementById(idd); if(el){el.value=''; if(el.dataset) delete el.dataset.touched;}}); _meeWizPartes=[]; meeWizFillPartes(); meeWizRenderPartes(); meeWizGen(); }
function meeWizClose(){ var m=document.getElementById('mee-wiz-modal'); if(m) m.style.display='none'; }
async function meeWizGen(){
  var tipo=(document.getElementById('mee-wiz-tipo')||{}).value||'';
  var ml=(document.getElementById('mee-wiz-ml')||{}).value||''; var tonoRaw=(document.getElementById('mee-wiz-tono')||{}).value||'';
  var catLbl={ENV:'Envase',IMP:'Impreso',GOT:'Gotero',TAP:'Tapa',ETQ:'Etiqueta',PLG:'Plegadiza'}[tipo]||'';
  var nm=[catLbl, ml?(ml+'ml'):'', tonoRaw].filter(function(x){return x;}).join(' ');
  var de=document.getElementById('mee-wiz-desc'); if(de && !de.dataset.touched) de.value=nm;
  var cd=document.getElementById('mee-wiz-code'); var msg=document.getElementById('mee-wiz-msg'); if(msg) msg.innerHTML='';
  if(!tipo){ if(cd) cd.textContent='—'; return; }
  if(cd) cd.textContent='…';
  try{
    var r=await fetch('/api/mee/siguiente-codigo?tipo='+encodeURIComponent(tipo),{credentials:'same-origin'});
    var d=await r.json();
    if(r.ok && d.ok){ if(cd) cd.textContent=d.codigo; }
    else { if(cd) cd.textContent='—'; if(msg) msg.innerHTML='<span style="color:#dc2626;">'+((d&&d.error)||'error')+'</span>'; }
  }catch(e){ if(cd) cd.textContent='—'; }
}
async function meeWizCrear(){
  var tipo=(document.getElementById('mee-wiz-tipo')||{}).value||'';
  if(!tipo){ alert('Elegí el tipo (Envase, Impreso, Gotero, Tapa, Etiqueta o Plegadiza).'); return; }
  var desc=(document.getElementById('mee-wiz-desc')||{}).value||'';
  if(!desc.trim()){ alert('Poné una descripción.'); return; }
  var ml=parseFloat((document.getElementById('mee-wiz-ml')||{}).value)||0;
  var cliente=(document.getElementById('mee-wiz-cliente')||{}).value||'';
  var s=document.getElementById('mee-codigo-sel');
  try{
    var r=await fetch('/api/mee/crear-auto',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tipo:tipo,descripcion:desc,volumen_ml:ml,cliente:cliente,partes:_meeWizPartes})});
    var res=await r.json();
    if(r.ok && res.ok){ await cargarMeeStock(); if(s){ s.value=res.codigo; meeSelChange(); } meeWizClose(); if(typeof meeCargarPorCalificar==='function') meeCargarPorCalificar(); }
    else { alert('Error: '+(res.error||'No se pudo crear')); }
  }catch(e){ alert('Error de conexión'); }
}
function meeSelChange(){ var sel=document.getElementById('mee-codigo-sel'); var prev=document.getElementById('mee-stock-preview'); var und=document.getElementById('mee-unidad'); if(!sel||!sel.value){if(prev)prev.style.display='none'; _meeFoto(''); _meeAutofill(''); meeCargarPartesRecep(''); return;} _meeFoto(sel.value); _meeAutofill(sel.value); meeCargarPartesRecep(sel.value); var opt=sel.options[sel.selectedIndex]; var st=opt.getAttribute('data-stock'); var u=opt.getAttribute('data-unidad')||'und'; var mn=opt.getAttribute('data-min'); if(prev){var r=mn>0?(st/mn*100).toFixed(0):null; var col=!r?'#666':(r<100?'#e74c3c':'#27ae60'); prev.style.display='block'; prev.innerHTML='&#128230; Stock: <strong style="color:'+col+';">'+st+' '+u+'</strong> | Minimo: <strong>'+mn+' '+u+'</strong>'+(r?' ('+r+'%)':'');} if(und) und.value=u; }
async function registrarMeeMovimiento(){ var tipo=(document.getElementById('mee-tipo')||{}).value; var codigo=(document.getElementById('mee-codigo-sel')||{}).value; var cantidad=parseFloat((document.getElementById('mee-cantidad')||{}).value); var unidad=(document.getElementById('mee-unidad')||{}).value||'und'; var lote=(document.getElementById('mee-lote')||{}).value||''; var batch=(document.getElementById('mee-batch')||{}).value||''; var obs=(document.getElementById('mee-obs')||{}).value||''; var prov=(document.getElementById('mee-proveedor')||{}).value||''; var zona=(document.getElementById('mee-zona')||{}).value||''; var precio=parseFloat((document.getElementById('mee-precio')||{}).value)||0; var fvenc=(document.getElementById('mee-fecha-venc')||{}).value||''; var oc=(document.getElementById('mee-oc')||{}).value||''; var factura=(document.getElementById('mee-factura')||{}).value||''; var msg=document.getElementById('mee-form-msg');
  if(!codigo){if(msg)msg.innerHTML='<div class="alert-error">Selecciona un material MEE</div>';return;}
  if(!cantidad||cantidad<=0){if(msg)msg.innerHTML='<div class="alert-error">Ingresa una cantidad valida</div>';return;}
  try{ var r=await fetch('/api/mee/movimiento',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tipo:tipo,codigo:codigo,cantidad:cantidad,unidad:unidad,lote_ref:lote,batch_ref:batch,observaciones:obs,proveedor:prov,zona:zona,precio_unitario:precio,fecha_vencimiento:fvenc,oc_numero:oc,factura_numero:factura,cliente:(document.getElementById('mee-cliente')||{}).value||''})}); var res=await r.json();
    if(res.ok){ var np=await meeRegistrarPartes(); var al=res.alerta?'<br><strong style="color:#e74c3c;">&#9888; '+res.alerta+'</strong>':''; if(msg)msg.innerHTML='<div class="alert-success">'+res.message+(np>0?(' · +'+np+' parte(s)'):'')+' - Stock: <strong>'+res.stock_nuevo+'</strong>'+al+'</div>'; var loteSave=lote; document.getElementById('mee-cantidad').value=''; document.getElementById('mee-lote').value=''; document.getElementById('mee-batch').value=''; document.getElementById('mee-obs').value=''; ['mee-zona','mee-precio','mee-valor','mee-fecha-venc','mee-oc','mee-factura'].forEach(function(idd){var el=document.getElementById(idd); if(el)el.value='';}); meeCargarPartesRecep(codigo); cargarMeeStock();cargarMeeAlertas();cargarMeeHistorial();meeCargarCuarentena(); if(tipo==='Entrada'){window.open('/rotulo-recepcion-mee/'+encodeURIComponent(codigo)+'/'+cantidad+'?lote='+encodeURIComponent(loteSave),'_blank');}
    } else { if(msg)msg.innerHTML='<div class="alert-error">'+(res.error||'Error al registrar')+'</div>'; }
  }catch(e){if(msg)msg.innerHTML='<div class="alert-error">Error de conexion</div>';}
}
async function cargarMeeHistorial(){ try{ var r=await fetch('/api/mee/movimientos?limit=30'); var d=await r.json(); var tb=document.getElementById('mee-hist-tbody'); if(!tb) return;
  if(!d.movimientos||!d.movimientos.length){tb.innerHTML='<tr><td colspan="9" style="text-align:center;color:#999;">Sin movimientos registrados</td></tr>';return;}
  var tC={Entrada:'#27ae60',Salida:'#e74c3c',Ajuste:'#9b59b6'}; var h='';
  d.movimientos.forEach(function(m){var c=tC[m.tipo]||'#555'; var ref=m.batch_ref||m.lote_ref||'';
    var btnRotulo=m.tipo==='Entrada'?'<button data-codigo="'+encodeURIComponent(m.mee_codigo)+'" data-cantidad="'+m.cantidad+'" data-lote="'+encodeURIComponent(ref||'')+'" onclick="abrirRotuloMEE(this)" style="background:#6d28d9;color:white;border:none;padding:4px 8px;font-size:0.75em;margin-right:4px;border-radius:3px;cursor:pointer;">&#128203; R&#243;tulo</button>':'';
    h+='<tr><td style="color:#bbb;font-size:0.8em;">#'+m.id+'</td><td style="font-family:monospace;font-size:0.82em;">'+m.mee_codigo+'</td><td style="font-size:0.85em;">'+m.descripcion+'</td><td><span style="color:'+c+';font-weight:700;font-size:0.88em;">'+m.tipo+'</span></td><td style="font-weight:700;">'+m.cantidad+' <span style="color:#999;font-size:0.8em;">'+m.unidad+'</span></td><td style="font-size:0.8em;color:#777;font-family:monospace;">'+(ref||'--')+'</td><td style="font-size:0.82em;">'+m.responsable+'</td><td style="font-size:0.8em;color:#888;">'+(m.fecha?m.fecha.substring(0,16):'')+'</td><td>'+btnRotulo+'<button onclick="meeAnular('+m.id+')" style="background:#c0392b;padding:4px 8px;font-size:0.75em;">Anular</button></td></tr>';
  }); tb.innerHTML=h;
  }catch(e){}}
function abrirRotuloMEE(btn){
  var c=btn.getAttribute('data-codigo')||'';
  var q=btn.getAttribute('data-cantidad')||'1';
  var l=btn.getAttribute('data-lote')||'';
  window.open('/rotulo-recepcion-mee/'+c+'/'+q+'?lote='+l,'_blank');
}
async function meeAnular(id){ var m=prompt('Motivo de anulacion (obligatorio):'); if(!m||!m.trim()){alert('Debes ingresar un motivo.');return;}
  try{var r=await fetch('/api/mee/anular/'+id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({motivo:m.trim()})}); var res=await r.json();
    if(res.ok){alert(res.message);cargarMeeHistorial();cargarMeeStock();cargarMeeAlertas();}else alert(res.error||'Error');
  }catch(e){alert('Error de conexion');}}
async function buscarTrazabilidadBatch(){ var b=(document.getElementById('mee-traz-batch')||{}).value||''; b=b.trim(); if(!b){alert('Ingresa un batch');return;}
  var res=document.getElementById('mee-traz-result'); if(res)res.innerHTML='<div style="color:#666;padding:10px;">Buscando...</div>';
  try{var r=await fetch('/api/mee/trazabilidad?batch='+encodeURIComponent(b)); var d=await r.json();
    if(!d.consumos||!d.consumos.length){if(res)res.innerHTML='<div style="color:#999;padding:10px 0;">Sin consumos para batch: <strong>'+b+'</strong></div>';return;}
    var h='<div style="background:white;border-radius:8px;padding:14px;margin-top:4px;"><h4 style="margin-bottom:10px;color:#155724;">Empaque consumido en batch: <strong>'+b+'</strong></h4><table class="table"><thead><tr><th>Codigo</th><th>Descripcion</th><th>Categoria</th><th>Cantidad</th><th>Responsable</th><th>Fecha</th></tr></thead><tbody>';
    d.consumos.forEach(function(c){h+='<tr><td style="font-family:monospace;font-size:0.82em;">'+c.mee_codigo+'</td><td>'+c.descripcion+'</td><td style="color:#777;font-size:0.8em;">'+c.categoria+'</td><td style="font-weight:700;">'+c.cantidad+' '+c.unidad+'</td><td>'+c.responsable+'</td><td style="font-size:0.8em;color:#888;">'+(c.fecha?c.fecha.substring(0,16):'')+'</td></tr>';});
    h+='</tbody></table></div>'; if(res)res.innerHTML=h;
  }catch(e){if(res)res.innerHTML='<div style="color:#e74c3c;">Error</div>';}}
async function buscarTrazabilidadMee(){ var cod=(document.getElementById('mee-traz-codigo')||{}).value||''; cod=cod.trim(); if(!cod){alert('Ingresa un codigo MEE');return;}
  var res=document.getElementById('mee-traz-result'); if(res)res.innerHTML='<div style="color:#666;padding:10px;">Buscando...</div>';
  try{var r=await fetch('/api/mee/trazabilidad?codigo='+encodeURIComponent(cod)); var d=await r.json();
    if(!d.historial||!d.historial.length){if(res)res.innerHTML='<div style="color:#999;padding:10px 0;">Sin historial para MEE: <strong>'+cod+'</strong></div>';return;}
    var tC={Entrada:'#27ae60',Salida:'#e74c3c',Ajuste:'#9b59b6'};
    var h='<div style="background:white;border-radius:8px;padding:14px;margin-top:4px;"><h4 style="margin-bottom:10px;color:#155724;">Historial de: <strong>'+cod+'</strong></h4><table class="table"><thead><tr><th>Tipo</th><th>Cantidad</th><th>Lote</th><th>Batch Prod.</th><th>Responsable</th><th>Fecha</th></tr></thead><tbody>';
    d.historial.forEach(function(m){var c=tC[m.tipo]||'#555'; h+='<tr><td><span style="color:'+c+';font-weight:700;">'+m.tipo+'</span></td><td style="font-weight:700;">'+m.cantidad+' '+m.unidad+'</td><td style="font-size:0.82em;color:#777;">'+(m.lote_ref||'--')+'</td><td style="font-family:monospace;font-size:0.82em;">'+(m.batch_ref||'--')+'</td><td>'+m.responsable+'</td><td style="font-size:0.8em;color:#888;">'+(m.fecha?m.fecha.substring(0,16):'')+'</td></tr>';});
    h+='</tbody></table></div>'; if(res)res.innerHTML=h;
  }catch(e){if(res)res.innerHTML='<div style="color:#e74c3c;">Error</div>';}}


function _toast(msg,ok){var t=document.createElement("div");t.style="position:fixed;bottom:24px;right:24px;background:"+(ok?"#27ae60":"#c0392b")+";color:#fff;padding:14px 24px;border-radius:8px;z-index:9999;font-size:15px;font-weight:600;box-shadow:0 4px 14px rgba(0,0,0,0.2);max-width:360px;transition:opacity 0.3s;";t.textContent=msg;document.body.appendChild(t);setTimeout(function(){t.style.opacity="0";setTimeout(function(){if(t.parentNode)t.parentNode.removeChild(t);},300);},4000);}
var _meeAcondItems=[];
function cargarMeeParaAcond(){
  fetch("/api/mee/stock").then(function(r){return r.json();}).then(function(d){
    _meeAcondItems=(d.items||[]).filter(function(m){return m.stock_actual>0;});
  }).catch(function(){});
}
function addMEERowAcond(){
  var cont=document.getElementById("ac-mee-rows");
  var msg=document.getElementById("ac-mee-msg"); if(msg) msg.style.display="none";
  var row=document.createElement("div");
  row.style.cssText="display:flex;gap:8px;align-items:center;";
  var selHtml='<select style="flex:2;padding:5px;border:1px solid #ccc;border-radius:4px;font-size:12px;">'+
    '<option value="">-- Seleccionar MEE --</option>';
  _meeAcondItems.forEach(function(m){
    selHtml+='<option value="'+m.codigo+'">'+m.codigo+' - '+m.descripcion+' (stock:'+m.stock_actual+')</option>';
  });
  selHtml+='</select>';
  row.innerHTML=selHtml+
    '<input type="number" min="1" placeholder="Cant" style="flex:1;padding:5px;border:1px solid #ccc;border-radius:4px;font-size:12px;">'+
    '<button onclick="this.parentElement.remove();_checkMEEMsg();" style="background:#dc3545;color:#fff;border:none;border-radius:4px;padding:4px 8px;cursor:pointer;font-size:12px;">&times;</button>';
  cont.appendChild(row);
}
function _checkMEEMsg(){
  var cont=document.getElementById("ac-mee-rows");
  var msg=document.getElementById("ac-mee-msg");
  if(msg) msg.style.display=(cont&&cont.children.length===0)?"block":"none";
}
var _envPresCount=0,_envMEE=[];
async function cargarEnvasadoTab(){
  var sel=document.getElementById('env-prod-sel');if(!sel) return;
  // Only reload if selector is empty or has just the placeholder
  var needsLoad=(sel.options.length<=1);
  if(needsLoad) sel.innerHTML='<option value="">Cargando producciones...</option>';
  try{
    var rp=await fetch('/api/produccion');var dp=await rp.json();
    var rm=await fetch('/api/mee');var dm=await rm.json();
    var prods=(dp.producciones||[]).filter(function(p){return p.estado==='Completado';});
    _envMEE=dm.items||[];
    // Only rebuild if we got real data
    if(prods.length>0){
      sel.innerHTML='<option value="">-- Selecciona produccion terminada --</option>';
      prods.forEach(function(p){
        var op=document.createElement('option');
        op.value=p.id;
        op.dataset.producto=p.producto||'';
        op.dataset.lote=p.lote||('PROD-'+String(p.id).padStart(5,'0'));
        op.dataset.batch=p.cantidad||0;
        op.text=(p.lote||'PROD-'+String(p.id).padStart(5,'0'))+' - '+(p.producto||'?')+' ('+p.cantidad+'kg) '+(p.fecha||'').slice(0,10);
        sel.appendChild(op);
      });
    }
  }catch(e){if(needsLoad) sel.innerHTML='<option value="">Error - recarga la pagina</option>';}
  await cargarHistEnvasado();
  if(!document.getElementById('env-pres-rows').children.length){
    _envPresCount=0;addEnvPres();
  }
}
function cargarDatosProduccion(){
  var sel=document.getElementById('env-prod-sel');if(!sel) return;
  var opt=sel.options[sel.selectedIndex];if(!opt||!opt.value) return;
  var p=document.getElementById('env-producto');var l=document.getElementById('env-lote');var b=document.getElementById('env-batch-total');
  if(p) p.value=opt.dataset.producto||'';
  if(l) l.value=opt.dataset.lote||'';
  if(b) b.value=(parseFloat(opt.dataset.batch||0)*1000).toFixed(0)+' g';
}
function addEnvPres(){
  if(_envPresCount>=2){alert('Maximo 2 presentaciones');return;}
  _envPresCount++;var n=_envPresCount;
  var cats=['Envase','Frasco','Gotero'];
  var optEnv=_envMEE.filter(function(m){return cats.indexOf(m.categoria)>=0;}).map(function(m){return '<option value="'+m.codigo+'">'+m.codigo+' - '+m.descripcion+' ('+m.stock_actual+')</option>';}).join('');
  var optTap=_envMEE.filter(function(m){return m.categoria==='Tapa';}).map(function(m){return '<option value="'+m.codigo+'">'+m.codigo+' - '+m.descripcion+' ('+m.stock_actual+')</option>';}).join('');
  var div=document.createElement('div');div.id='env-pres-'+n;div.style.cssText='background:#fff;border:1px solid #ddd;border-radius:6px;padding:12px;margin-bottom:8px;';
  div.innerHTML='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;"><strong style="font-size:13px;color:#1a4a7a">Presentacion '+n+'</strong>'+(n>1?'<button onclick="rmEnvPres('+n+')" style="background:#dc3545;color:#fff;border:none;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:11px">Quitar</button>':'')+'</div><div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;"><div><label style="font-size:11px">Presentacion</label><input id="ep'+n+'-pres" placeholder="Ej: 30ml" style="width:100%;padding:6px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div><div><label style="font-size:11px">Envase</label><select id="ep'+n+'-env" style="width:100%;padding:6px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:11px;"><option value="">--</option>'+optEnv+'</select></div><div><label style="font-size:11px">Tapa</label><select id="ep'+n+'-tap" style="width:100%;padding:6px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:11px;"><option value="">--</option>'+optTap+'</select></div><div><label style="font-size:11px">Unidades</label><input id="ep'+n+'-uds" type="number" min="1" placeholder="0" style="width:100%;padding:6px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div></div>';
  document.getElementById('env-pres-rows').appendChild(div);
  if(_envPresCount>=2){var btn=document.getElementById('env-add-pres-btn');if(btn)btn.style.display='none';}
}
function rmEnvPres(n){var el=document.getElementById('env-pres-'+n);if(el)el.remove();_envPresCount--;var btn=document.getElementById('env-add-pres-btn');if(btn)btn.style.display='';}
async function registrarEnvasado(){
  var prodSel=document.getElementById('env-prod-sel');
  if(!prodSel||!prodSel.value){alert('Selecciona un batch de produccion');return;}
  var prodId=parseInt(prodSel.value);
  var lote=(document.getElementById('env-lote')||{value:''}).value.trim();
  var producto=(document.getElementById('env-producto')||{value:''}).value.trim();
  var obs=(document.getElementById('env-obs')||{value:''}).value.trim();
  var presentaciones=[];
  for(var i=1;i<=2;i++){
    var presEl=document.getElementById('ep'+i+'-pres');if(!presEl) continue;
    var pres=presEl.value.trim();
    var envCod=(document.getElementById('ep'+i+'-env')||{value:''}).value;
    var tapCod=(document.getElementById('ep'+i+'-tap')||{value:''}).value;
    var uds=parseInt((document.getElementById('ep'+i+'-uds')||{value:0}).value||0);
    if(!pres||uds<=0) continue;
    presentaciones.push({presentacion:pres,envase_codigo:envCod,tapa_codigo:tapCod,unidades:uds});
  }
  if(!presentaciones.length){alert('Agrega al menos una presentacion con unidades');return;}
  var msg=document.getElementById('env-msg');
  if(msg) msg.innerHTML='<span style="color:#666;">Registrando...</span>';
  var allAlertas=[];
  for(var j=0;j<presentaciones.length;j++){
    var p=presentaciones[j];
    try{
      var r=await fetch('/api/envasado',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({produccion_id:prodId,lote:lote,producto:producto,presentacion:p.presentacion,unidades:p.unidades,envase_codigo:p.envase_codigo,tapa_codigo:p.tapa_codigo,operador:OPER_ACTUAL||'Operario',observaciones:obs})});
      var d=await r.json();
      if(!r.ok){if(msg)msg.innerHTML='<div style="color:#dc3545;padding:8px;">Error: '+(d.error||r.status)+'</div>';return;}
      if(d.alertas_mee) allAlertas=allAlertas.concat(d.alertas_mee);
    }catch(e){if(msg)msg.innerHTML='<div style="color:#dc3545;">Error: '+e.message+'</div>';return;}
  }
  var alertTxt=allAlertas.length?' | MEE bajo minimo: '+allAlertas.map(function(a){return a.nombre+' deficit '+a.deficit;}).join(', ')+'. Solicitud enviada a Compras.':'';
  if(msg) msg.innerHTML='<div style="color:#28a745;padding:8px;background:#d4edda;border-radius:4px;">Envasado registrado. MEE descontado.'+alertTxt+'</div>';
  await cargarHistEnvasado();
  if(typeof loadAlertasMEE==='function') setTimeout(loadAlertasMEE,500);
}
window._envHistOffset = 0;
window._envHistLimit = 50;
window._envHistDebounceT = null;
function _envHistDebounced(){
  if(window._envHistDebounceT) clearTimeout(window._envHistDebounceT);
  window._envHistDebounceT = setTimeout(function(){
    window._envHistOffset = 0;
    cargarEnvHistorial();
  }, 350);
}
async function cargarHistEnvasado(){ return cargarEnvHistorial(); }
async function cargarEnvHistorial(){
  var tb=document.getElementById('env-tbody');
  var ft=document.getElementById('env-hist-footer');
  if(!tb) return;
  var q = (document.getElementById('env-q')||{}).value || '';
  var desde = (document.getElementById('env-desde')||{}).value || '';
  var hasta = (document.getElementById('env-hasta')||{}).value || '';
  var limit = window._envHistLimit;
  var offset = window._envHistOffset || 0;
  var url = '/api/envasado?limit='+limit+'&offset='+offset
          +(q ? '&q='+encodeURIComponent(q) : '')
          +(desde ? '&desde='+encodeURIComponent(desde) : '')
          +(hasta ? '&hasta='+encodeURIComponent(hasta) : '');
  try{
    var r=await fetch(url, {credentials:'same-origin'});
    var d=await r.json();
    var rows=d.envasados||[];
    if(!rows.length){
      tb.innerHTML='<tr><td colspan="9" style="text-align:center;color:#999;padding:12px;">Sin registros que coincidan</td></tr>';
      if(ft) ft.innerHTML = 'Total: 0';
      return;
    }
    tb.innerHTML=rows.map(function(e){
      var fec = (e.fecha||'').substring(0,16).replace('T',' ');
      return '<tr style="border-bottom:1px solid #eee;">'+
        '<td style="padding:6px;font-family:monospace;font-size:12px;color:#6d28d9;font-weight:700">'+_escHTML(e.lote||'')+'</td>'+
        '<td style="padding:6px;">'+_escHTML(e.producto||'')+'</td>'+
        '<td style="padding:6px;">'+_escHTML(e.presentacion||'')+'</td>'+
        '<td style="padding:6px;text-align:center;font-weight:700">'+(e.unidades||0)+'</td>'+
        '<td style="padding:6px;font-size:11px;color:#666;">'+_escHTML(e.envase_codigo||'—')+'</td>'+
        '<td style="padding:6px;font-size:11px;color:#666;">'+_escHTML(e.tapa_codigo||'—')+'</td>'+
        '<td style="padding:6px;font-size:12px;">'+_escHTML(fec)+'</td>'+
        '<td style="padding:6px;font-size:12px;">'+_escHTML(e.operador||'')+'</td>'+
        '<td style="padding:6px;text-align:center"><button data-env-act="detalle" data-eid="'+e.id+'" style="background:#7c3aed;color:#fff;border:none;padding:3px 8px;border-radius:4px;font-size:10px;cursor:pointer" title="Ver MEE descontado + costo">📋</button></td>'+
      '</tr>';
    }).join('');
    if(ft){
      var total = d.total || 0;
      var d_n = (offset||0) + 1;
      var h_n = (offset||0) + rows.length;
      var pag = '';
      if(offset > 0) pag += '<button onclick="window._envHistOffset=Math.max(0,window._envHistOffset-'+limit+');cargarEnvHistorial()" style="padding:4px 10px;background:#475569;color:#fff;border:none;border-radius:4px;font-size:11px;cursor:pointer;margin-right:4px">← Anterior</button>';
      if(offset + limit < total) pag += '<button onclick="window._envHistOffset+='+limit+';cargarEnvHistorial()" style="padding:4px 10px;background:#1a4a7a;color:#fff;border:none;border-radius:4px;font-size:11px;cursor:pointer">Siguiente →</button>';
      ft.innerHTML = '<span>Mostrando '+d_n+'–'+h_n+' de '+total.toLocaleString()+'</span><span>'+pag+'</span>';
    }
  }catch(err){
    if(tb) tb.innerHTML='<tr><td colspan="9" style="color:#c00;text-align:center;padding:10px">Error: '+_escHTML(err.message)+'</td></tr>';
  }
}

if(typeof document !== 'undefined' && !window._ENV_HIST_DELEG){
  window._ENV_HIST_DELEG = true;
  document.addEventListener('click', function(ev){
    var b = ev.target && ev.target.closest && ev.target.closest('[data-env-act="detalle"]');
    if(!b) return;
    verDetalleEnvasado(b.getAttribute('data-eid'));
  });
}
async function verDetalleEnvasado(eid){
  try{
    var r = await fetch('/api/envasado/'+eid+'/detalle');
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    var existe = document.getElementById('modal-env-det'); if(existe) existe.remove();
    var div = document.createElement('div');
    div.id = 'modal-env-det';
    div.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px';
    var costoStr = d.costo_estimado_mee_cop ? '$'+Number(d.costo_estimado_mee_cop).toLocaleString('es-CO') : '—';
    var meeRows = (d.mee_descontados||[]).map(function(m){
      return '<tr><td style="font-family:monospace">'+_escHTML(m.codigo||'')+'</td><td>'+_escHTML(m.descripcion||'')+'</td><td style="text-align:right;font-weight:700">'+(m.unidades||0)+'</td></tr>';
    }).join('');
    div.innerHTML =
      '<div style="background:#fff;border-radius:14px;padding:24px;max-width:720px;width:100%;max-height:90vh;overflow-y:auto">'+
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><h3 style="margin:0;color:#1a4a7a">📦 Detalle envasado · '+_escHTML(d.lote||'')+'</h3>'+
      '<button id="env-det-close" style="background:none;border:none;font-size:1.4em;cursor:pointer">×</button></div>'+
      '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;background:#f8fafc;padding:12px;border-radius:8px;margin-bottom:14px;font-size:13px">'+
        '<div><b>Producto</b><br>'+_escHTML(d.producto||'')+'</div>'+
        '<div><b>Presentación</b><br>'+_escHTML(d.presentacion||'')+'</div>'+
        '<div><b>Unidades</b><br><span style="font-size:18px;font-weight:800;color:#1a4a7a">'+(d.unidades||0)+'</span></div>'+
        '<div><b>Lote</b><br><span style="font-family:monospace;color:#dc2626;font-weight:700">'+_escHTML(d.lote||'')+'</span></div>'+
        '<div><b>Envase</b><br>'+_escHTML(d.envase_codigo||'—')+'</div>'+
        '<div><b>Tapa</b><br>'+_escHTML(d.tapa_codigo||'—')+'</div>'+
        '<div><b>Costo MEE</b><br><span style="color:#6d28d9;font-weight:700">'+costoStr+'</span></div>'+
        '<div><b>Operador</b><br>'+_escHTML(d.operador||'')+'</div>'+
      '</div>'+
      '<h4 style="margin:14px 0 6px;color:#475569;font-size:13px">📉 MEE descontados</h4>'+
      '<table class="table" style="font-size:11px"><thead><tr><th>Código</th><th>Descripción</th><th style="text-align:right">Unidades</th></tr></thead><tbody>'+
        (meeRows || '<tr><td colspan="3" style="text-align:center;color:#94a3b8">Sin MEE registrados</td></tr>')+
      '</tbody></table>'+
      (d.observaciones ? '<div style="margin-top:12px;padding:8px;background:#fef3c7;border-left:3px solid #ca8a04;font-size:12px"><b>Observaciones:</b><br>'+_escHTML(d.observaciones)+'</div>' : '')+
      '</div>';
    document.body.appendChild(div);
    document.getElementById('env-det-close').onclick = function(){ var m = document.getElementById('modal-env-det'); if(m) m.remove(); };
    div.addEventListener('click', function(e){ if(e.target === div){ var m = document.getElementById('modal-env-det'); if(m) m.remove(); } });
  }catch(e){ alert('Error red: '+e.message); }
}
async function cargarEnvasadosPendientes(){
  var sel=document.getElementById('ac-envasado-sel');if(!sel) return;
  try{
    var r=await fetch('/api/envasado/pendientes-acond');var d=await r.json();var pend=d.pendientes||[];
    sel.innerHTML='<option value="">-- Selecciona batch envasado listo --</option>';
    pend.forEach(function(e){var op=document.createElement('option');op.value=e.id;op.dataset.lote=e.lote||'';op.dataset.producto=e.producto||'';op.dataset.pres=e.presentacion||'';op.dataset.uds=e.unidades||0;op.dataset.batch=e.batch_g||0;op.text=e.lote+' - '+e.producto+' '+e.presentacion+' ('+e.unidades+' uds) '+e.fecha;sel.appendChild(op);});
  }catch(e){}
}
function cargarDesdeEnvasado(){
  var sel=document.getElementById('ac-envasado-sel');if(!sel||!sel.value) return;
  var opt=sel.options[sel.selectedIndex];
  var f=function(id,v){var el=document.getElementById(id);if(el)el.value=v;};
  f('ac-envasado-id',opt.value);f('ac-lote',opt.dataset.lote||'');f('ac-prod',opt.dataset.producto||'');
  f('ac-pres',opt.dataset.pres||'');f('ac-uds',opt.dataset.uds||'');f('ac-batch',opt.dataset.batch||'');
}

function registrarAcond(){
  var lote=document.getElementById("ac-lote").value;
  var prod=document.getElementById("ac-prod").value;
  if(!lote||!prod){_toast("Lote y producto son obligatorios",0);return;}
  var meeRows=document.getElementById("ac-mee-rows").querySelectorAll("div");
  var mee_consumido=[];
  var meeOk=true;
  meeRows.forEach(function(row){
    var sel=row.querySelector("select");
    var qty=row.querySelector("input[type=number]");
    if(sel&&qty&&sel.value){
      var c=parseInt(qty.value)||0;
      if(c<=0){meeOk=false;return;}
      mee_consumido.push({codigo:sel.value,cantidad:c});
    }
  });
  if(!meeOk){_toast("Verifica cantidades MEE (deben ser > 0)",0);return;}
  var d={
    lote:lote,
    producto:prod,
    presentacion:document.getElementById("ac-pres").value,
    cantidad_batch_g:parseFloat(document.getElementById("ac-batch").value)||0,
    unidades_producidas:parseInt(document.getElementById("ac-uds").value)||0,
    fecha:document.getElementById("ac-fecha").value,
    observaciones:document.getElementById("ac-obs").value,
    sku:document.getElementById("ac-sku").value.trim(),
    precio_base:parseFloat(document.getElementById("ac-precio").value)||0,
    mee_consumido:mee_consumido
  };
  var msgEl=document.getElementById("ac-form-msg");
  fetch("/api/acondicionamiento",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)})
  .then(function(r){return r.json();})
  .then(function(j){
    if(j.ok||j.id){
      var info="✅ Batch registrado #"+j.id;
      if(mee_consumido.length) info+=" | MEE descontado: "+mee_consumido.length+" item(s)";
      _toast(info,1);
      ["ac-lote","ac-prod","ac-pres","ac-batch","ac-uds","ac-obs","ac-sku","ac-precio"].forEach(function(id){document.getElementById(id).value="";});
      document.getElementById("ac-mee-rows").innerHTML="";
      _checkMEEMsg();
      if(msgEl) msgEl.innerHTML="";
      loadAcond();
    } else {
      var err="Error: "+(j.error||"desconocido");
      _toast(err,0);
      if(msgEl) msgEl.innerHTML='<span style="color:red;">'+err+'</span>';
    }
  }).catch(function(e){
    _toast("Error de red: "+e,0);
    if(msgEl) msgEl.innerHTML='<span style="color:red;">Error de red: '+e+'</span>';
  });
}
async function crearLegajoEnvasado(btn){
  // Crea el legajo EBR de envasado y entra a construirlo. Si falta el MBR aprobado,
  // ofrece generarlo+aprobarlo (con la firma del usuario) y reintenta.
  var prod=btn.getAttribute('data-prod'), lote=btn.getAttribute('data-lote');
  if(!prod){return;}
  btn.disabled=true; var _t=btn.textContent; btn.textContent='Creando…';
  async function _crear(){
    var r=await fetch('/api/brd/legajo-rapido',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({producto:prod,lote:lote||prod,fase:'envasado'})});
    return {r:r,d:await r.json()};
  }
  try{
    var res=await _crear();
    if(res.r.status===409 && /MBR/.test(((res.d&&res.d.error)||''))){
      if(confirm('"'+prod+'" no tiene MBR de envasado aprobado.\n\n¿Generar y APROBAR su MBR ahora (con tu firma) para hacer la prueba?')){
        btn.textContent='Aprobando MBR…';
        var ra=await fetch('/api/brd/mbr/preparar-aprobado',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({producto_nombre:prod})});
        var da=await ra.json();
        if(!ra.ok||!da.ok){alert('No se pudo aprobar el MBR: '+((da&&da.error)||ra.status));btn.disabled=false;btn.textContent=_t;return;}
        btn.textContent='Creando…'; res=await _crear();
      } else { btn.disabled=false; btn.textContent=_t; return; }
    }
    if(!res.r.ok||!res.d.ok){alert('No se pudo crear el legajo: '+((res.d&&res.d.error)||res.r.status));btn.disabled=false;btn.textContent=_t;return;}
    location.href=res.d.link||('/planta/orden/'+res.d.id);
  }catch(e){alert('Error: '+(e.message||e));btn.disabled=false;btn.textContent=_t;}
}
function cargarOrdenesEnvasado(){
  // Órdenes de Envasado (con estado + legajo) · como MyBatch. Reusa el endpoint
  // unificado /api/brd/ordenes-unificadas?fase=envasado (trae estado y link al legajo).
  var tb=document.getElementById('ordenes-env-tbody');
  if(!tb)return;
  var E=function(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');};
  fetch('/api/brd/ordenes-unificadas?fase=envasado').then(function(r){return r.json();}).then(function(d){
    var ords=(d&&d.ordenes)||[];
    if(!ords.length){tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:#999;padding:10px">Sin órdenes de envasado aún · envasá un lote para crearlas</td></tr>';return;}
    tb.innerHTML=ords.map(function(o){
      var leg=o.link?('<a href="'+E(o.link)+'" style="color:#7c3aed;font-weight:700;text-decoration:none">Abrir legajo →</a>'):('<button data-prod="'+E(o.producto)+'" data-lote="'+E(o.lote_bulk||o.numero_op||'')+'" onclick="crearLegajoEnvasado(this)" style="background:#16a34a;color:#fff;border:none;border-radius:5px;padding:4px 10px;font-size:12px;cursor:pointer">Crear legajo &rarr;</button>');
      return '<tr style="border-bottom:1px solid #f1f5f9">'+
        '<td style="padding:8px;font-weight:600">'+E(o.numero_op)+'</td>'+
        '<td style="padding:8px">'+E(o.producto)+'</td>'+
        '<td style="padding:8px">'+E(o.lote_bulk||'—')+'</td>'+
        '<td style="padding:8px">'+E(o.estado||'—')+'</td>'+
        '<td style="padding:8px;color:#64748b">'+E(o.fecha||'—')+'</td>'+
        '<td style="padding:8px;text-align:center">'+leg+'</td></tr>';
    }).join('');
  }).catch(function(){tb.innerHTML='<tr><td colspan="6" style="color:#c00;text-align:center;padding:10px">Error cargando órdenes</td></tr>';});
}
async function crearLegajoAcondicionamiento(btn){
  // Crea el legajo EBR de acondicionamiento (OA) y entra a construirlo. Si falta el
  // MBR aprobado, ofrece generarlo+aprobarlo (con la firma del usuario) y reintenta.
  var prod=btn.getAttribute('data-prod'), lote=btn.getAttribute('data-lote');
  if(!prod){return;}
  btn.disabled=true; var _t=btn.textContent; btn.textContent='Creando…';
  async function _crear(){
    var r=await fetch('/api/brd/legajo-rapido',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({producto:prod,lote:lote||prod,fase:'acondicionamiento'})});
    return {r:r,d:await r.json()};
  }
  try{
    var res=await _crear();
    if(res.r.status===409 && /MBR/.test(((res.d&&res.d.error)||''))){
      if(confirm('"'+prod+'" no tiene MBR aprobado.\n\n¿Generar y APROBAR su MBR ahora (con tu firma) para hacer la prueba?')){
        btn.textContent='Aprobando MBR…';
        var ra=await fetch('/api/brd/mbr/preparar-aprobado',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({producto_nombre:prod})});
        var da=await ra.json();
        if(!ra.ok||!da.ok){alert('No se pudo aprobar el MBR: '+((da&&da.error)||ra.status));btn.disabled=false;btn.textContent=_t;return;}
        btn.textContent='Creando…'; res=await _crear();
      } else { btn.disabled=false; btn.textContent=_t; return; }
    }
    if(!res.r.ok||!res.d.ok){alert('No se pudo crear el legajo: '+((res.d&&res.d.error)||res.r.status));btn.disabled=false;btn.textContent=_t;return;}
    location.href=res.d.link||('/planta/orden/'+res.d.id);
  }catch(e){alert('Error: '+(e.message||e));btn.disabled=false;btn.textContent=_t;}
}
function cargarOrdenesAcondicionamiento(){
  // Órdenes de Acondicionamiento (con estado + legajo) · como MyBatch. Reusa el endpoint
  // unificado /api/brd/ordenes-unificadas?fase=acondicionamiento (estado + link al legajo).
  var tb=document.getElementById('ordenes-acond-tbody');
  if(!tb)return;
  var E=function(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');};
  fetch('/api/brd/ordenes-unificadas?fase=acondicionamiento').then(function(r){return r.json();}).then(function(d){
    var ords=(d&&d.ordenes)||[];
    if(!ords.length){tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:#999;padding:10px">Sin órdenes de acondicionamiento aún · acondicioná un lote para crearlas</td></tr>';return;}
    tb.innerHTML=ords.map(function(o){
      var leg=o.link?('<a href="'+E(o.link)+'" style="color:#7c3aed;font-weight:700;text-decoration:none">Abrir legajo →</a>'):('<button data-prod="'+E(o.producto)+'" data-lote="'+E(o.lote_bulk||o.numero_op||'')+'" onclick="crearLegajoAcondicionamiento(this)" style="background:#16a34a;color:#fff;border:none;border-radius:5px;padding:4px 10px;font-size:12px;cursor:pointer">Crear legajo &rarr;</button>');
      return '<tr style="border-bottom:1px solid #f1f5f9">'+
        '<td style="padding:8px;font-weight:600">'+E(o.numero_op)+'</td>'+
        '<td style="padding:8px">'+E(o.producto)+'</td>'+
        '<td style="padding:8px">'+E(o.lote_bulk||'—')+'</td>'+
        '<td style="padding:8px">'+E(o.estado||'—')+'</td>'+
        '<td style="padding:8px;color:#64748b">'+E(o.fecha||'—')+'</td>'+
        '<td style="padding:8px;text-align:center">'+leg+'</td></tr>';
    }).join('');
  }).catch(function(){tb.innerHTML='<tr><td colspan="6" style="color:#c00;text-align:center;padding:10px">Error cargando órdenes</td></tr>';});
}
// ENVASADO 26-jun (Sebastián) · loader LIMPIO de la pestaña Envasado: solo legajos de envasado
// HABILITADOS (ebr_ejecuciones fase='envasado' · se crean cuando Calidad LIBERA el granel · Fase 2).
// Espeja cargarEnCurso de Fabricación · abre el legajo en el MISMO runner role-aware (abrirEBR).
async function cargarEnvasadoRunner(){
  var wrap=document.getElementById('envasado-lista');
  if(!wrap) return;
  wrap.innerHTML='<div style="color:#999;padding:10px">Cargando&hellip;</div>';
  try{
    var d=await (await fetch('/api/brd/ordenes-unificadas?fase=envasado',{credentials:'same-origin'})).json();
    var items=((d&&d.items)?d.items:[]).filter(function(o){return o&&o.ebr_id;});
    if(!items.length){
      wrap.innerHTML='<div style="color:#64748b;padding:16px;text-align:center;font-size:13px">Sin órdenes de envasado todav&iacute;a.<br>Cuando Calidad <b>libera</b> el granel de un lote, su Orden de Envasado aparece ac&aacute; autom&aacute;ticamente.</div>';
      return;
    }
    var h='<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr style="background:#f5f3ff;color:#5b21b6"><th style="text-align:left;padding:8px">N&deg; orden</th><th style="text-align:left;padding:8px">Producto</th><th style="text-align:left;padding:8px">Lote</th><th style="text-align:left;padding:8px">Estado</th><th style="padding:8px">Legajo</th></tr></thead><tbody>';
    items.forEach(function(o){
      h+='<tr style="border-bottom:1px solid #eee"><td style="padding:8px">'+(o.numero_op||('EBR-'+o.ebr_id))+'</td><td style="padding:8px">'+(o.producto||'')+'</td><td style="padding:8px;font-family:monospace;font-size:11px">'+(o.lote_bulk||'')+'</td><td style="padding:8px">'+(o.estado||'')+'</td><td style="padding:8px;text-align:center"><button onclick="abrirEBR('+o.ebr_id+',&#39;envasado-runner&#39;)" style="background:#6d28d9;color:#fff;border:none;border-radius:5px;padding:5px 12px;font-size:11px;font-weight:700;cursor:pointer">&#128203; Pasos</button></td></tr>';
    });
    h+='</tbody></table></div>';
    wrap.innerHTML=h;
  }catch(e){ wrap.innerHTML='<div style="color:#dc2626;padding:10px">Error cargando &oacute;rdenes de envasado.</div>'; }
}
// ENVASADO Fase 3 (26-jun) · sección de presentaciones en el runner: unidades por presentación + cerrar/descontar.
async function cargarEnvasesPlan(ebrId){
  var wrap=document.getElementById('env-pres-'+ebrId);
  if(!wrap) return;
  try{
    var d=await (await fetch('/api/brd/ebr/'+ebrId+'/envases-plan',{credentials:'same-origin'})).json();
    if(!d.ok||!d.items||!d.items.length){ wrap.innerHTML='<div style="color:#94a3b8">Este producto no tiene presentaciones configuradas. Cargalas en <b>Planta &rsaquo; Presentaciones</b> (producto &rarr; 15/30/50ml &rarr; envase/tapa/caja).</div>'; return; }
    var desc=d.descontado;
    var h='<table class="table" style="font-size:12px"><thead><tr><th>Presentaci&oacute;n</th><th>Vol</th><th>Envase</th><th>Tapa</th><th>Caja</th><th>Unidades</th><th></th></tr></thead><tbody>';
    d.items.forEach(function(it){
      var pc=it.presentacion_codigo;
      var inp=desc?('<b>'+(it.unidades||0)+'</b>'):('<input id="eu-'+ebrId+'-'+pc+'" type="number" min="0" value="'+(it.unidades||0)+'" style="width:80px;padding:4px;border:1px solid #cbd5e1;border-radius:4px">');
      var btn=desc?'':('<button onclick="ebrRegistrarUnidades('+ebrId+',&#39;'+pc+'&#39;,'+(it.volumen_ml||0)+')" style="background:#16a34a;color:#fff;border:none;border-radius:4px;padding:4px 10px;font-size:11px;cursor:pointer">Guardar</button>');
      h+='<tr><td>'+(it.etiqueta||pc)+'</td><td>'+(it.volumen_ml||0)+' ml</td><td style="font-family:monospace;font-size:10px">'+(it.envase_codigo||'&mdash;')+'</td><td style="font-family:monospace;font-size:10px">'+(it.tapa_codigo||'&mdash;')+'</td><td style="font-family:monospace;font-size:10px">'+(it.caja_codigo||'&mdash;')+'</td><td>'+inp+'</td><td>'+btn+'</td></tr>';
    });
    h+='</tbody></table>';
    if(desc){ h+='<div style="margin-top:8px;color:#16a34a;font-weight:700">&#10003; Envases descontados (legajo cerrado).</div>'; }
    else { h+='<button onclick="ebrCerrarEnvasado('+ebrId+')" style="margin-top:10px;background:#6d28d9;color:#fff;border:none;border-radius:6px;padding:8px 18px;font-size:13px;font-weight:700;cursor:pointer">&#128274; Cerrar envasado y descontar envases</button> <span style="color:#94a3b8;font-size:11px">descuenta envase+tapa+caja &times; unidades de cada presentaci&oacute;n</span>'; }
    wrap.innerHTML=h;
  }catch(e){ wrap.innerHTML='<div style="color:#dc2626">Error cargando presentaciones.</div>'; }
}
async function ebrRegistrarUnidades(ebrId, pc, vol){
  var el=document.getElementById('eu-'+ebrId+'-'+pc);
  var u=el?parseFloat(el.value||'0'):0;
  var r=await fetch('/api/brd/ebr/'+ebrId+'/registrar-unidades',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({presentacion_codigo:pc,unidades:u,volumen_ml:vol})});
  var d=await r.json();
  if(!r.ok){ alert(d.error||'Error'); return; }
  cargarEnvasesPlan(ebrId);
}
async function ebrCerrarEnvasado(ebrId){
  if(!confirm('Cerrar el envasado y descontar los envases (envase+tapa+caja por unidad)? Baja el stock de MEE y marca el legajo completado.')) return;
  var r=await fetch('/api/brd/ebr/'+ebrId+'/cerrar-envasado',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({})});
  var d=await r.json();
  if(!r.ok){ alert(d.error||'No se pudo cerrar'); return; }
  alert('Envasado cerrado · '+(d.n_descuentos||0)+' descuentos de envase registrados.');
  if(typeof abrirEBR==='function') abrirEBR(ebrId);
}
function acondAddMat(ebrId){
  var wrap=document.getElementById('acond-mat-rows-'+ebrId); if(!wrap) return;
  var div=document.createElement('div'); div.className='acond-mat-row'; div.style.cssText='display:flex;gap:6px;margin-bottom:5px;align-items:center';
  div.innerHTML='<input class="acond-cod" placeholder="Código MEE" style="flex:2;padding:6px;border:1px solid #ccc;border-radius:4px;font-size:12px"><input class="acond-cant" type="number" min="0" step="1" placeholder="Cantidad" style="flex:1;padding:6px;border:1px solid #ccc;border-radius:4px;font-size:12px"><button onclick="this.parentNode.remove()" style="background:#fee2e2;color:#991b1b;border:none;border-radius:4px;padding:5px 9px;font-size:12px;cursor:pointer">&times;</button>';
  wrap.appendChild(div);
}
async function ebrCerrarAcond(ebrId){
  var rows=document.querySelectorAll('#acond-mat-rows-'+ebrId+' .acond-mat-row');
  var mats=[];
  rows.forEach(function(r){
    var cod=((r.querySelector('.acond-cod')||{}).value||'').trim(), cant=parseFloat((r.querySelector('.acond-cant')||{}).value||'0');
    if(cod&&cant>0) mats.push({codigo:cod, cantidad:cant});
  });
  if(!mats.length){ alert('Agregá al menos un material con cantidad.'); return; }
  if(!confirm('Cerrar el acondicionamiento y descontar '+mats.length+' material(es)? Baja el stock de MEE y marca el legajo completado.')) return;
  var r=await fetch('/api/brd/ebr/'+ebrId+'/cerrar-acondicionamiento',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({materiales:mats})});
  var d=await r.json();
  if(!r.ok){ alert(d.error||'No se pudo cerrar'); return; }
  alert('Acondicionamiento cerrado · '+(d.n_descuentos||0)+' material(es) descontado(s).');
  if(typeof abrirEBR==='function') abrirEBR(ebrId);
}
// 🔗 Lote completo (27-jun · #8 · INVIMA) · muestra OP+OF+OA de un lote físico juntos en un overlay.
async function verLoteFases(loteEnc){
  try{
    var d=await (await fetch('/api/brd/lote/'+loteEnc+'/fases',{credentials:'same-origin'})).json();
    var fa=d.fases||[];
    var LB={fabricacion:'📋 Fabricación (OP)',envasado:'📦 Envasado (OF)',acondicionamiento:'🎁 Acondicionamiento (OA)'};
    var rows=fa.map(function(f){
      var est=(typeof _ebrBadge==='function')?_ebrBadge(f.estado):_escHTML(f.estado||'');
      var fin=f.completado_at?String(f.completado_at).replace('T',' ').slice(0,16):'—';
      return '<tr><td style="font-weight:700">'+(LB[f.fase]||_escHTML(f.fase))+'</td><td>'+_escHTML(f.numero_op||'')+'</td><td>'+est+'</td><td style="font-size:11px">'+_escHTML(f.iniciado_por||'—')+'</td><td style="font-size:11px;color:#94a3b8">'+fin+'</td><td><button class="lf-open" data-ebr="'+f.ebr_id+'" style="background:#ede9fe;color:#6d28d9;border:none;border-radius:5px;padding:3px 9px;font-size:11px;cursor:pointer;font-weight:700">Abrir</button></td></tr>';
    }).join('');
    var ov=document.createElement('div'); ov.id='lote-fases-ov';
    ov.style.cssText='position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
    ov.innerHTML='<div style="background:#fff;border-radius:14px;max-width:680px;width:100%;padding:22px;box-shadow:0 20px 60px rgba(0,0,0,.3)"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px"><h3 style="margin:0;color:#5b21b6">🔗 Lote '+_escHTML(d.lote||'')+' · trazabilidad de fases</h3><button class="lf-close" style="background:#94a3b8;color:#fff;border:none;border-radius:6px;padding:5px 10px;cursor:pointer">✕</button></div>'+(fa.length?('<table class="table" style="font-size:12px"><thead><tr><th>Fase</th><th>Orden</th><th>Estado</th><th>Inició</th><th>Terminó</th><th></th></tr></thead><tbody>'+rows+'</tbody></table>'):'<div style="color:#94a3b8">Sin fases registradas para este lote.</div>')+'<div style="font-size:10px;color:#94a3b8;margin-top:8px">El mismo lote físico de punta a punta (Fabricación → Envasado → Acondicionamiento) · INVIMA.</div></div>';
    ov.addEventListener('click',function(e){
      if(e.target===ov || (e.target.classList && e.target.classList.contains('lf-close'))){ ov.remove(); return; }
      var b=e.target.closest && e.target.closest('.lf-open');
      if(b){ ov.remove(); if(typeof abrirEBR==='function') abrirEBR(parseInt(b.getAttribute('data-ebr'),10)); }
    });
    document.body.appendChild(ov);
  }catch(e){ alert('Error: '+e.message); }
}
function loadColaSinEnvasar(){
  if(typeof cargarOrdenesEnvasado==='function')cargarOrdenesEnvasado();
  var tb=document.getElementById('cola-env-tbody');
  if(!tb)return;
  tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:#999;padding:10px">Cargando...</td></tr>';
  fetch('/api/producciones/sin-envasar')
    .then(function(r){return r.json();})
    .then(function(d){
      var rows=d.cola||[];
      var countEl = document.getElementById('cola-env-count');
      if(countEl) countEl.textContent = rows.length + (rows.length === 1 ? ' lote' : ' lotes');
      if(!rows.length){tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:#27ae60;padding:10px">&#10003; Sin lotes pendientes de envasar</td></tr>';return;}
      _sinEnvasarMap={};
      rows.forEach(function(r){_sinEnvasarMap[r.id]=r;});
      tb.innerHTML=rows.map(function(r){
        return '<tr style="border-bottom:1px solid #c8e6c9">'+
          '<td style="padding:7px;font-weight:600">'+(r.lote||'S/L')+'</td>'+
          '<td style="padding:7px">'+r.producto+'</td>'+
          '<td style="padding:7px;text-align:center">'+(r.cantidad_kg||0)+' kg</td>'+
          '<td style="padding:7px">'+(r.fecha||'')+'</td>'+
          '<td style="padding:7px">'+(r.operador||'')+'</td>'+
          '<td style="padding:7px"><button onclick="abrirEnvasado('+r.id+')" '+
          'style="background:#1b5e20;color:#fff;border:none;border-radius:4px;padding:4px 10px;font-size:12px;cursor:pointer">'+
          '&#128230; Envasar</button></td>'+
          '</tr>';
      }).join('');
    })
    .catch(function(){tb.innerHTML='<tr><td colspan="6" style="color:#c00;text-align:center">Error cargando cola</td></tr>';});
}
var _envActObj = null;
var _sinEnvasarMap = {};
var _pendAcondMap  = {};
function _buildMeeOpts(selectedVal){
  // Sprint Envasado PRO · 20-may-2026 · destacar MEE con stock crítico
  // (bajo mínimo o agotado) y ordenar por stock disponible desc para que
  // el operario vea primero lo que sí hay.
  var envCats=['Envase','Frasco','Gotero','Tarro'];
  var eOpts='<option value="">-- Sin envase --</option>';
  var tOpts='<option value="">-- Sin tapa --</option>';
  var sorted = (_envSimpleMEE||[]).slice().sort(function(a,b){
    return (b.stock_actual||0) - (a.stock_actual||0);
  });
  sorted.forEach(function(m){
    var stock = Number(m.stock_actual||0);
    var min = Number(m.stock_minimo||0);
    var badge = '';
    if(stock === 0) badge = ' ⛔ AGOTADO';
    else if(min > 0 && stock < min) badge = ' ⚠ bajo mínimo';
    var opt='<option value="'+m.codigo+'"'+(m.codigo===selectedVal?' selected':'')+
      (stock === 0 ? ' disabled' : '')+'>'+
      m.codigo+' - '+m.descripcion+' ('+stock+')'+badge+'</option>';
    if(envCats.indexOf(m.categoria)>=0) eOpts+=opt;
    else if(m.categoria==='Tapa') tOpts+=opt;
  });
  return {env:eOpts, tap:tOpts};
}
function _presRowHtml(idx){
  var opts=_buildMeeOpts('');
  return '<div class="pres-row" id="pr-'+idx+'" style="background:#f0f4f8;border-radius:8px;padding:12px;margin-bottom:10px;position:relative">'
    +'<div style="display:grid;grid-template-columns:2fr 2fr 2fr 1fr;gap:10px;align-items:end">'
    +'<div><label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:3px">Presentacion *</label>'
    +'<input type="text" class="pr-pres" placeholder="Ej: Frasco 30ml" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:13px"></div>'
    +'<div><label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:3px">Envase (MEE)</label>'
    +'<select class="pr-env" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:13px">'+opts.env+'</select></div>'
    +'<div><label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:3px">Tapa (MEE)</label>'
    +'<select class="pr-tap" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:13px">'+opts.tap+'</select></div>'
    +'<div><label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:3px">Unidades *</label>'
    +'<input type="number" class="pr-uds" min="1" placeholder="66" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:13px"></div>'
    +'</div>'
    +(idx>0?'<button onclick="removePresRow('+idx+')" style="position:absolute;top:8px;right:8px;background:#dc3545;color:#fff;border:none;border-radius:4px;padding:2px 8px;font-size:12px;cursor:pointer">&#10005;</button>':'')
    +'</div>';
}
var _prIdx=0;
function abrirEnvasado(id){
  var lote_obj=_sinEnvasarMap[id]||{};
  _envActObj=lote_obj;
  _prIdx=0;
  document.getElementById('env-act-prod').textContent=lote_obj.producto||'';
  document.getElementById('env-act-prod-raw').value=lote_obj.producto||'';
  document.getElementById('env-act-lote').textContent=lote_obj.lote||'S/L';
  document.getElementById('env-act-batch').textContent=(lote_obj.cantidad_kg||0)+' kg';
  document.getElementById('env-act-prod-id').value=lote_obj.id||'';
  var rows=document.getElementById('env-pres-rows');
  rows.innerHTML=_presRowHtml(_prIdx);
  document.getElementById('env-act-msg').innerHTML='';
  document.getElementById('env-panel-activo').style.display='block';
  document.getElementById('env-panel-activo').scrollIntoView({behavior:'smooth',block:'start'});
  _cargarSugerenciasEnvasado();
}
function _cargarSugerenciasEnvasado(){
  // Semi-auto · pre-llena operario sugerido + áreas de envasado limpias (jefe confirma).
  var E=function(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');};
  var opSel=document.getElementById('env-act-operario');
  var arSel=document.getElementById('env-act-area');
  var hint=document.getElementById('env-area-hint');
  if(opSel)opSel.innerHTML='<option>Cargando…</option>';
  if(arSel)arSel.innerHTML='<option>Cargando…</option>';
  fetch('/api/planta/envasado/sugerencias').then(function(r){return r.json();}).then(function(d){
    var ops=d.operarios||[];
    if(opSel)opSel.innerHTML = ops.length ? ops.map(function(o){
      return '<option value="'+E(o.nombre)+'"'+(o.nombre===d.operario_sugerido?' selected':'')+'>'+E(o.nombre)+(o.rol?(' · '+E(o.rol)):'')+'</option>';
    }).join('') : '<option value="">(sin operarios)</option>';
    var ars=d.areas||[];
    if(arSel)arSel.innerHTML = (ars.length ? ars.map(function(a){
      var et=a.limpia?'✓ limpia':('⚠ '+(a.estado||''));
      return '<option value="'+E(a.codigo)+'"'+(a.codigo===d.area_sugerida?' selected':'')+'>'+E(a.nombre||a.codigo)+' · '+et+'</option>';
    }).join('') : '') + '<option value="">— sin asignar área —</option>';
    if(hint)hint.textContent = d.area_sugerida ? '(sugerida limpia)' : '(ninguna limpia)';
  }).catch(function(){
    if(opSel)opSel.innerHTML='<option value="">(error)</option>';
    if(arSel)arSel.innerHTML='<option value="">(error)</option>';
  });
}
function addPresRow(){
  _prIdx++;
  document.getElementById('env-pres-rows').insertAdjacentHTML('beforeend',_presRowHtml(_prIdx));
}
function removePresRow(idx){
  var el=document.getElementById('pr-'+idx);if(el)el.remove();
}
function cerrarEnvActivo(){
  _envActObj=null;
  document.getElementById('env-panel-activo').style.display='none';
  document.getElementById('env-pres-rows').innerHTML='';
}
async function registrarEnvasadoMulti(){
  if(!_envActObj){return;}
  var rows=document.querySelectorAll('#env-pres-rows .pres-row');
  if(!rows.length){_toast('Agrega al menos una presentacion',0);return;}
  var payload=[];
  var ok=true;
  rows.forEach(function(row){
    var pres=(row.querySelector('.pr-pres')||{value:''}).value.trim();
    var uds=parseInt((row.querySelector('.pr-uds')||{value:0}).value||0);
    var env=(row.querySelector('.pr-env')||{value:''}).value;
    var tap=(row.querySelector('.pr-tap')||{value:''}).value;
    if(!pres||uds<=0){ok=false;return;}
    payload.push({pres:pres,uds:uds,env:env,tap:tap});
  });
  if(!ok){_toast('Completa presentacion y unidades en todas las filas',0);return;}
  var msg=document.getElementById('env-act-msg');
  msg.innerHTML='<span style="color:#666">Registrando...</span>';
  var errores=[];
  // Semi-auto · operario + área asignados (gate de limpieza · override por confirmación).
  var _oper=(document.getElementById('env-act-operario')||{value:''}).value||(OPER_ACTUAL||'Operario');
  var _areaCod=(document.getElementById('env-act-area')||{value:''}).value||'';
  var _ovr=false;
  for(var i=0;i<payload.length;i++){
    var p=payload[i];
    var _try=0;
    while(_try<2){
      _try++;
      try{
        var r=await fetch('/api/envasado',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({
            produccion_id:_envActObj.id||null,
            lote:_envActObj.lote||'',
            producto:_envActObj.producto||'',
            presentacion:p.pres,
            unidades:p.uds,
            envase_codigo:p.env||'',
            tapa_codigo:p.tap||'',
            operador:_oper,
            area_codigo:_areaCod,
            override_area:_ovr,
            batch_g:(_envActObj.cantidad_kg||0)*1000
          })
        });
        var d=await r.json();
        if(r.status===409&&d.requiere_override&&!_ovr){
          if(confirm((d.warning||'Área no limpia')+'\n\n¿Envasar igual?')){_ovr=true;continue;}
          errores.push(p.pres+': área no limpia (cancelado)');break;
        }
        if(!r.ok&&!d.id){errores.push(p.pres+': '+(d.error||d.warning||'error'));break;}
        break;
      }catch(e){errores.push(p.pres+': error de red');break;}
    }
  }
  if(errores.length){
    msg.innerHTML='<span style="color:red">'+errores.join(' | ')+'</span>';
  }else{
    _toast('&#9989; Envasado registrado ('+payload.length+' presentacion'+(payload.length>1?'es':'')+')',1);
    cerrarEnvActivo();
    loadColaSinEnvasar();
    if(typeof cargarHistEnvasado==='function') cargarHistEnvasado();
  }
}
function loadColaAcond(){
  if(typeof cargarOrdenesAcondicionamiento==='function')cargarOrdenesAcondicionamiento();
  var tb=document.getElementById('cola-acond-tbody');
  if(!tb)return;
  tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:#999;padding:10px">Cargando...</td></tr>';
  fetch('/api/envasado/pendientes-acond')
    .then(function(r){return r.json();})
    .then(function(d){
      var rows=d.pendientes||[];
      if(!rows.length){tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:#27ae60;padding:10px">&#10003; Sin lotes pendientes de acondicionar</td></tr>';return;}
      _pendAcondMap={};
      rows.forEach(function(r){_pendAcondMap[r.id]=r;});
      tb.innerHTML=rows.map(function(r){
        return '<tr style="border-bottom:1px solid #bbdefb">'+
          '<td style="padding:7px;font-weight:600">'+(r.lote||'S/L')+'</td>'+
          '<td style="padding:7px">'+r.producto+'</td>'+
          '<td style="padding:7px;text-align:center">'+(r.unidades||0)+'</td>'+
          '<td style="padding:7px">'+(r.presentacion||'')+'</td>'+
          '<td style="padding:7px">'+(r.fecha||'')+'</td>'+
          '<td style="padding:7px"><button onclick="prefillAcond('+r.id+')" '+
          'style="background:#0d47a1;color:#fff;border:none;border-radius:4px;padding:4px 10px;font-size:12px;cursor:pointer">'+
          '&#128393; Acondicionar</button></td>'+
          '</tr>';
      }).join('');
    })
    .catch(function(){tb.innerHTML='<tr><td colspan="6" style="color:#c00;text-align:center">Error cargando cola</td></tr>';});
}
function prefillAcond(id){ abrirAcond(id); }
var _acActObj = null;
var _acPrIdx = 0;
function _acPresRowHtml(idx, pres, uds){
  pres = pres||''; uds = uds||'';
  return '<div class="ac-pres-row" id="acpr-'+idx+'" style="background:#f0f4f8;border-radius:8px;padding:12px;margin-bottom:10px;position:relative">'
    +'<div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:10px;align-items:end">'
    +'<div><label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:3px">Presentacion / SKU *</label>'
    +'<input type="text" class="acpr-pres" placeholder="Ej: LBHA-30ML" value="'+pres+'" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:13px"></div>'
    +'<div><label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:3px">Unidades *</label>'
    +'<input type="number" class="acpr-uds" min="1" placeholder="66" value="'+uds+'" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:13px"></div>'
    +'<div><label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:3px">Etiquetas</label>'
    +'<input type="number" class="acpr-et" min="0" placeholder="66" value="'+uds+'" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:13px"></div>'
    +'<div><label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:3px">Plegadizas</label>'
    +'<input type="number" class="acpr-pl" min="0" placeholder="66" value="'+uds+'" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:13px"></div>'
    +'</div>'
    +(idx>0?'<button onclick="removeAcPresRow('+idx+')" style="position:absolute;top:8px;right:8px;background:#dc3545;color:#fff;border:none;border-radius:4px;padding:2px 8px;font-size:12px;cursor:pointer">&#10005;</button>':'')
    +'</div>';
}
function abrirAcond(id){
  var env=_pendAcondMap[id]||{};
  _acActObj = env;
  _acPrIdx = 0;
  document.getElementById('ac-act-prod').textContent = env.producto||'';
  document.getElementById('ac-act-prod-raw').value = env.producto||'';
  document.getElementById('ac-act-lote').textContent = env.lote||'S/L';
  document.getElementById('ac-act-lote-raw').value = env.lote||'';
  document.getElementById('ac-act-uds-info').textContent = (env.unidades||0)+' uds disponibles';
  document.getElementById('ac-act-env-id').value = env.id||'';
  var fEl=document.getElementById('ac-act-fecha'); if(fEl) fEl.value=new Date().toISOString().slice(0,10);
  var dEl=document.getElementById('ac-act-destino'); if(dEl) dEl.value='';
  var obsEl=document.getElementById('ac-act-obs'); if(obsEl) obsEl.value='';
  var msgEl=document.getElementById('ac-act-msg'); if(msgEl) msgEl.innerHTML='';
  var rows=document.getElementById('ac-pres-rows');
  if(rows) rows.innerHTML=_acPresRowHtml(0, env.presentacion||'', env.unidades||'');
  var fm=document.getElementById('ac-form-manual'); if(fm) fm.style.display='none';
  document.getElementById('ac-panel-activo').style.display='block';
  document.getElementById('ac-panel-activo').scrollIntoView({behavior:'smooth',block:'start'});
}
function addAcPresRow(){
  _acPrIdx++;
  document.getElementById('ac-pres-rows').insertAdjacentHTML('beforeend',_acPresRowHtml(_acPrIdx,'',''));
}
function removeAcPresRow(idx){
  var el=document.getElementById('acpr-'+idx); if(el) el.remove();
}
function cerrarAcondActivo(){
  _acActObj=null;
  document.getElementById('ac-panel-activo').style.display='none';
  var rows=document.getElementById('ac-pres-rows'); if(rows) rows.innerHTML='';
  var fm=document.getElementById('ac-form-manual'); if(fm) fm.style.display='block';
}
async function registrarAcondDesdePanel(){
  if(!_acActObj){ _toast('No hay lote activo',0); return; }
  var lote=(document.getElementById('ac-act-lote-raw')||{value:''}).value.trim();
  var producto=(document.getElementById('ac-act-prod-raw')||{value:''}).value.trim();
  var fecha=(document.getElementById('ac-act-fecha')||{value:''}).value;
  var destino=(document.getElementById('ac-act-destino')||{value:''}).value.trim();
  var obs=(document.getElementById('ac-act-obs')||{value:''}).value.trim();
  if(!lote||!producto){ _toast('Datos de lote incompletos',0); return; }
  var presRows=document.querySelectorAll('#ac-pres-rows .ac-pres-row');
  if(!presRows.length){ _toast('Agrega al menos una presentacion',0); return; }
  var payload=[];
  var ok=true;
  presRows.forEach(function(row){
    var pres=(row.querySelector('.acpr-pres')||{value:''}).value.trim();
    var uds=parseInt((row.querySelector('.acpr-uds')||{value:0}).value||0);
    var et=parseInt((row.querySelector('.acpr-et')||{value:0}).value||0);
    var pl=parseInt((row.querySelector('.acpr-pl')||{value:0}).value||0);
    if(!pres||uds<=0){ok=false;return;}
    payload.push({pres:pres,uds:uds,et:et,pl:pl});
  });
  if(!ok){ _toast('Completa presentacion y unidades en todas las filas',0); return; }
  var msgEl=document.getElementById('ac-act-msg');
  if(msgEl) msgEl.innerHTML='<span style="color:#666">Registrando...</span>';
  var errores=[];
  for(var i=0;i<payload.length;i++){
    var p=payload[i];
    var obsCompleto='Etiquetas: '+p.et+' | Plegadizas: '+p.pl+(destino?' | Destino: '+destino:'')+(obs?' | '+obs:'');
    try{
      var r=await fetch('/api/acondicionamiento',{
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          lote:lote, producto:producto,
          presentacion:p.pres,
          cantidad_batch_g:0,
          unidades_producidas:p.uds,
          fecha:fecha,
          observaciones:obsCompleto,
          sku:p.pres, precio_base:0, mee_consumido:[]
        })
      });
      var d=await r.json();
      if(!r.ok&&!d.id){ errores.push(p.pres+': '+(d.error||r.status)); }
    }catch(e){ errores.push(p.pres+': error de red'); }
  }
  if(errores.length){
    if(msgEl) msgEl.innerHTML='<span style="color:red">'+errores.join(' | ')+'</span>';
  }else{
    _toast('✅ Acondicionamiento registrado ('+payload.length+' presentacion'+(payload.length>1?'es':'')+')',1);
    cerrarAcondActivo();
    loadColaAcond();
    loadAcondSimple();
  }
}

function loadAcond(){
  fetch("/api/acondicionamiento").then(function(r){return r.json();}).then(function(rows){
    var tb=document.getElementById("ac-tbody"); if(!tb)return;
    tb.innerHTML="";
    // SEC-FIX · 21-may-2026 · escape strings de DB (XSS stored)
    function _eAc(s){return String(s||'').replace(/[&<>"'/]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',"/":'&#47;'}[c];});}
    rows.forEach(function(r){
      var estadoColor=r.estado==="Completado"?"#28a745":r.estado==="Rechazado"?"#dc3545":"#fd7e14";
      var btn="";
        if(r.estado==="En proceso") btn=`<button onclick="updateAcond(${r.id},'Completado')" style="background:#28a745;color:#fff;border:none;border-radius:3px;padding:3px 7px;cursor:pointer;font-size:11px">Completar</button>`;
        tb.innerHTML+=`<tr><td style="padding:7px;border-bottom:1px solid #eee">${_eAc(r.lote)}</td><td style="padding:7px;border-bottom:1px solid #eee">${_eAc(r.producto)}</td><td style="padding:7px;border-bottom:1px solid #eee">${_eAc(r.presentacion)}</td><td style="padding:7px;border-bottom:1px solid #eee">${r.cantidad_batch_g||0}</td><td style="padding:7px;border-bottom:1px solid #eee">${r.unidades_producidas||0}</td><td style="padding:7px;border-bottom:1px solid #eee">${_eAc(r.fecha)}</td><td style="padding:7px;border-bottom:1px solid #eee">${_eAc(r.operador)}</td><td style="padding:7px;border-bottom:1px solid #eee"><span style="background:${estadoColor};color:#fff;padding:2px 7px;border-radius:10px;font-size:11px">${_eAc(r.estado)}</span></td><td style="padding:7px;border-bottom:1px solid #eee">${btn}</td></tr>`;
    });
  }).catch(function(){});
}
function updateAcond(id,estado){
  fetch("/api/acondicionamiento/"+id,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({estado:estado})})
  .then(function(){loadAcond();});
}
async function cargarAcondPendientesLib(){
  var sel=document.getElementById('lb-acond-sel');if(!sel) return;
  if(sel.options.length>1) return;
  try{
    var r=await fetch('/api/acondicionamiento/pendientes-lib');
    var d=await r.json();var pend=d.pendientes||[];
    sel.innerHTML='<option value="">-- Selecciona batch acondicionado --</option>';
    pend.forEach(function(a){
      var op=document.createElement('option');
      op.value=a.id;op.dataset.lote=a.lote||'';op.dataset.producto=a.producto||'';
      op.dataset.pres=a.presentacion||'';op.dataset.uds=a.unidades||0;op.dataset.fecha=a.fecha||'';
      op.text=(a.lote||'?')+' - '+(a.producto||'?')+' '+a.presentacion+' ('+a.unidades+' uds)';
      sel.appendChild(op);
    });
  }catch(e){}
}
function cargarDesdeAcond(){
  var sel=document.getElementById('lb-acond-sel');if(!sel||!sel.value) return;
  var opt=sel.options[sel.selectedIndex];
  var f=function(id,v){var el=document.getElementById(id);if(el)el.value=v;};
  f('lb-acond-id',opt.value);f('lb-lote',opt.dataset.lote||'');
  f('lb-prod',opt.dataset.producto||'');f('lb-pres',opt.dataset.pres||'');
  f('lb-uds',opt.dataset.uds||'');
  var fechaEl=document.getElementById('lb-fprod');
  if(fechaEl&&opt.dataset.fecha) fechaEl.value=(opt.dataset.fecha||'').slice(0,10);
}

function registrarLiberacion(){
  var d={lote:document.getElementById("lb-lote").value,producto:document.getElementById("lb-prod").value,presentacion:document.getElementById("lb-pres").value,unidades:parseInt(document.getElementById("lb-uds").value)||0,fecha_produccion:document.getElementById("lb-fprod").value,destino:document.getElementById("lb-dest").value,cliente:document.getElementById("lb-cli").value,observaciones:document.getElementById("lb-obs").value};
  if(!d.lote||!d.producto){_toast("Lote y producto son obligatorios",0);return;}
  fetch("/api/liberacion",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)})
  .then(function(r){return r.json();}).then(function(j){
    if(j.ok){_toast("✅ Lote enviado a CC #"+j.id,1);["lb-lote","lb-prod","lb-pres","lb-uds","lb-cli","lb-obs"].forEach(function(i){document.getElementById(i).value="";});loadLiberaciones("");}
    else _toast("Error: "+(j.error||"desconocido"),0);
  }).catch(function(e){_toast("Error: "+e,0);});
}
function loadLiberaciones(estado){
  var url="/api/liberacion"+(estado?"?estado="+encodeURIComponent(estado):"");
  // SEC-FIX · 22-may-2026 · escape strings DB (XSS stored prevention)
  function _eLib(s){return String(s||'').replace(/[&<>"'/]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',"/":'&#47;'}[c];});}
  fetch(url).then(function(r){return r.json();}).then(function(rows){
    var tb=document.getElementById("lb-tbody"); if(!tb)return;
    tb.innerHTML="";
    rows.forEach(function(r){
      var ec=r.estado==="Liberado"?"#28a745":r.estado==="Rechazado"?"#dc3545":"#fd7e14";
      var btns="";
      if(r.estado==="Pendiente CC"){
            btns=`<button onclick="aprobarLib(${r.id})" style="background:#28a745;color:#fff;border:none;border-radius:3px;padding:3px 7px;cursor:pointer;font-size:11px;margin-right:3px">Liberar</button>`;
            btns+=`<button onclick="rechazarLib(${r.id})" style="background:#dc3545;color:#fff;border:none;border-radius:3px;padding:3px 7px;cursor:pointer;font-size:11px">Rechazar</button>`;
      }
        tb.innerHTML+=`<tr><td style="padding:7px;border-bottom:1px solid #eee">${_eLib(r.lote)}</td><td style="padding:7px;border-bottom:1px solid #eee">${_eLib(r.producto)}</td><td style="padding:7px;border-bottom:1px solid #eee">${r.unidades||0}</td><td style="padding:7px;border-bottom:1px solid #eee">${_eLib(r.destino)}</td><td style="padding:7px;border-bottom:1px solid #eee">${_eLib(r.cliente||'--')}</td><td style="padding:7px;border-bottom:1px solid #eee">${_eLib(r.fecha_produccion||'--')}</td><td style="padding:7px;border-bottom:1px solid #eee">${_eLib(r.fecha_liberacion||'--')}</td><td style="padding:7px;border-bottom:1px solid #eee">${_eLib(r.aprobado_por||'--')}</td><td style="padding:7px;border-bottom:1px solid #eee"><span style="background:${ec};color:#fff;padding:2px 7px;border-radius:10px;font-size:11px">${_eLib(r.estado)}</span></td><td style="padding:7px;border-bottom:1px solid #eee">${btns}</td></tr>`;
    });
  }).catch(function(){});
}
var _clientesLib=[];
async function cargarClientesLib(){
  try{var r=await fetch('/api/clientes');var d=await r.json();_clientesLib=(d.clientes||[]).filter(function(c){return c.activo;});}
  catch(e){_clientesLib=[];}
}
function aprobarLib(id){
  var opts=_clientesLib.map(function(c){
    var o=document.createElement("option");
    o.value=c.nombre; o.textContent=c.nombre; return o.outerHTML;
  }).join("");
  var modal=document.createElement("div");
  modal.id="lib-modal-overlay";
  modal.style.cssText="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.55);z-index:9999;display:flex;align-items:center;justify-content:center;";
  modal.innerHTML=
    '<div style="background:#fff;border-radius:10px;padding:28px 32px;'
    +'min-width:340px;max-width:460px;box-shadow:0 8px 40px rgba(0,0,0,0.18);">'
    +'<h3 style="margin:0 0 18px;color:#1a2332;font-size:1.1em;">'
    +'&#128666; Confirmar Liberación</h3>'
    +'<label style="font-size:0.85em;color:#555;display:block;margin-bottom:5px;">'
    +'Cliente destino</label>'
    +'<select id="lib-cli-sel" style="width:100%;padding:8px;border:1px solid #ccc;'
    +'border-radius:6px;font-size:0.93em;margin-bottom:14px;">'
    +'<option value="">-- Seleccionar cliente --</option>'+opts+'</select>'
    +'<label style="font-size:0.85em;color:#555;display:block;margin-bottom:5px;">'
    +'Observaciones (opcional)</label>'
    +'<input id="lib-obs-inp" type="text" '
    +'style="width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;'
    +'font-size:0.93em;margin-bottom:20px;box-sizing:border-box;" '
    +'placeholder="Ej: Conforme CC, OK BPM...">'
    +'<div style="display:flex;gap:10px;justify-content:flex-end;">'
    +'<button id="lib-cancel-btn" style="padding:8px 18px;border:1px solid #ccc;'
    +'border-radius:6px;cursor:pointer;background:#f5f5f5;font-size:0.9em;">Cancelar</button>'
    +'<button id="lib-confirm-btn" style="padding:8px 18px;background:#28a745;'
    +'color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;'
    +'font-size:0.9em;">&#10003; Liberar</button>'
    +'</div></div>';
  document.body.appendChild(modal);
  document.getElementById("lib-cancel-btn").onclick=function(){modal.remove();};
  document.getElementById("lib-confirm-btn").onclick=function(){
    var cli=document.getElementById("lib-cli-sel").value;
    var obs=document.getElementById("lib-obs-inp").value;
    modal.remove();
    fetch("/api/liberacion/"+id,{method:"PATCH",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({estado:"Liberado",cliente:cli,observaciones:obs})})
    .then(function(r){return r.json();})
    .then(function(){_toast('✅ Liberado'+(cli?' → '+cli:''),1);loadLiberaciones('');});
  };
}
function rechazarLib(id){
  var obs=prompt("Motivo de rechazo:");
  if(!obs)return;
  fetch("/api/liberacion/"+id,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({estado:"Rechazado",observaciones:obs})})
  .then(function(){loadLiberaciones("");});
}

/* ============================================================
   ENVASADO SIMPLE
   ============================================================ */
var _envSimpleMEE = [];
async function cargarEnvasadoSimpleTab(){
  // Populate product selector from formulas
  var sel = document.getElementById('env-prod-sel');
  if(sel && sel.options.length <= 1){
    try{
      var r = await fetch('/api/programacion/productos');
      var d = await r.json();
      var prods = d.formulas || [];
      if(prods.length){
        sel.innerHTML = '<option value="">-- Selecciona producto --</option>';
        prods.forEach(function(p){
          var op = document.createElement('option');
          var nombre = p.nombre || p.producto_nombre || '';
          op.value = nombre; op.text = nombre;
          sel.appendChild(op);
        });
      }
    }catch(e){}
  }
  // Populate envase/tapa selectors from MEE stock
  var selEnv = document.getElementById('env-envase-sel');
  var selTap = document.getElementById('env-tapa-sel');
  if(selEnv && selEnv.options.length <= 1){
    try{
      var rm = await fetch('/api/mee/stock');
      var dm = await rm.json();
      _envSimpleMEE = dm.items || [];
      var envCats = ['Envase','Frasco','Gotero','Tarro'];
      var envOpts = '<option value="">-- Sin envase --</option>';
      var tapOpts = '<option value="">-- Sin tapa --</option>';
      _envSimpleMEE.forEach(function(m){
        var opt = '<option value="'+m.codigo+'">'+m.codigo+' - '+m.descripcion+' (stock: '+m.stock_actual+')</option>';
        if(envCats.indexOf(m.categoria) >= 0) envOpts += opt;
        else if(m.categoria === 'Tapa') tapOpts += opt;
      });
      if(selEnv) selEnv.innerHTML = envOpts;
      if(selTap) selTap.innerHTML = tapOpts;
    }catch(e){}
  }
  // Load history
  await cargarHistEnvasado();
}

async function registrarEnvasadoSimple(){
  var prodSel = document.getElementById('env-prod-sel');
  var lote = (document.getElementById('env-lote')||{value:''}).value.trim();
  var uds = parseInt((document.getElementById('env-uds')||{value:0}).value||0);
  var pres = (document.getElementById('env-pres')||{value:''}).value.trim();
  var envCod = (document.getElementById('env-envase-sel')||{value:''}).value;
  var tapCod = (document.getElementById('env-tapa-sel')||{value:''}).value;
  var obs = (document.getElementById('env-obs')||{value:''}).value.trim();
  var producto = prodSel ? prodSel.value : '';
  if(!producto){ _toast('Selecciona un producto', 0); return; }
  if(!lote){ _toast('Ingresa el numero de lote', 0); return; }
  if(uds <= 0){ _toast('Ingresa unidades envasadas', 0); return; }
  var msg = document.getElementById('env-msg');
  if(msg) msg.innerHTML = '<span style="color:#666">Registrando...</span>';
  try{
    var r = await fetch('/api/envasado', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        produccion_id: null,
        lote: lote,
        producto: producto,
        presentacion: pres || producto,
        unidades: uds,
        envase_codigo: envCod || '',
        tapa_codigo: tapCod || '',
        operador: OPER_ACTUAL || 'Operario',
        observaciones: obs
      })
    });
    var d = await r.json();
    if(!r.ok){ if(msg) msg.innerHTML='<div style="color:#dc3545;padding:8px;">Error: '+(d.error||r.status)+'</div>'; return; }
    _toast('✅ Envasado registrado', 1);
    ['env-lote','env-uds','env-pres','env-obs'].forEach(function(id){ var el=document.getElementById(id); if(el) el.value=''; });
    if(prodSel) prodSel.selectedIndex = 0;
    if(msg) msg.innerHTML = '';
    await cargarHistEnvasado();
    if(typeof loadAlertasMEE === 'function') setTimeout(loadAlertasMEE, 500);
  }catch(e){
    if(msg) msg.innerHTML='<div style="color:#dc3545;padding:8px;">Error de red: '+e.message+'</div>';
  }
}

/* ============================================================
   ACONDICIONAMIENTO SIMPLE
   ============================================================ */
async function cargarAcondSimpleTab(){
  // Populate product selector
  var sel = document.getElementById('ac-prod-sel');
  if(sel && sel.options.length <= 1){
    try{
      var r = await fetch('/api/programacion/productos');
      var d = await r.json();
      var prods = d.formulas || [];
      if(prods.length){
        sel.innerHTML = '<option value="">-- Selecciona producto --</option>';
        prods.forEach(function(p){
          var nombre = p.nombre || p.producto_nombre || '';
          var op = document.createElement('option');
          op.value = nombre; op.text = nombre;
          sel.appendChild(op);
        });
      }
    }catch(e){}
  }
  // Set today as default date
  var fechaEl = document.getElementById('ac-fecha');
  if(fechaEl && !fechaEl.value) fechaEl.value = new Date().toISOString().slice(0,10);
  // Load history
  loadAcondSimple();
}

async function registrarAcondSimple(){
  var prodSel = document.getElementById('ac-prod-sel');
  var lote = (document.getElementById('ac-lote')||{value:''}).value.trim();
  var uds = parseInt((document.getElementById('ac-uds')||{value:0}).value||0);
  var fecha = (document.getElementById('ac-fecha')||{value:''}).value;
  var etiquetas = parseInt((document.getElementById('ac-etiquetas')||{value:0}).value||0);
  var plegadizas = parseInt((document.getElementById('ac-plegadizas')||{value:0}).value||0);
  var destino = (document.getElementById('ac-destino')||{value:''}).value.trim();
  var sku = (document.getElementById('ac-sku')||{value:''}).value.trim();
  var obs = (document.getElementById('ac-obs')||{value:''}).value.trim();
  var producto = prodSel ? prodSel.value : '';
  if(!producto){ _toast('Selecciona un producto', 0); return; }
  if(!lote){ _toast('Ingresa el numero de lote PT', 0); return; }
  if(uds <= 0){ _toast('Ingresa unidades acondicionadas', 0); return; }
  var obsCompleto = 'Etiquetas: '+etiquetas+' | Plegadizas: '+plegadizas+(destino?' | Destino: '+destino:'')+(obs?' | '+obs:'');
  var msgEl = document.getElementById('ac-form-msg');
  if(msgEl) msgEl.innerHTML = '<span style="color:#666">Registrando...</span>';
  try{
    var r = await fetch('/api/acondicionamiento', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        lote: lote,
        producto: producto,
        presentacion: sku || producto,
        cantidad_batch_g: 0,
        unidades_producidas: uds,
        fecha: fecha,
        observaciones: obsCompleto,
        sku: sku,
        precio_base: 0,
        mee_consumido: []
      })
    });
    var d = await r.json();
    if(!r.ok){ if(msgEl) msgEl.innerHTML='<div style="color:#dc3545;padding:8px;">Error: '+(d.error||r.status)+'</div>'; return; }
    _toast('✅ Batch registrado', 1);
    ['ac-lote','ac-uds','ac-etiquetas','ac-plegadizas','ac-destino','ac-sku','ac-obs'].forEach(function(id){ var el=document.getElementById(id); if(el) el.value=''; });
    if(prodSel) prodSel.selectedIndex = 0;
    if(msgEl) msgEl.innerHTML = '';
    loadAcondSimple();
  }catch(e){
    if(msgEl) msgEl.innerHTML='<div style="color:#dc3545;padding:8px;">Error de red: '+e.message+'</div>';
  }
}

function loadAcondSimple(){ cargarAcondHistorial(); }

// Sprint Acondicionamiento PRO UI · 21-may-2026 · paginación + búsqueda + detalle
window._acHistOffset = 0;
window._acHistLimit = 50;
window._acHistDebounceT = null;
function _acHistDebounced(){
  if(window._acHistDebounceT) clearTimeout(window._acHistDebounceT);
  window._acHistDebounceT = setTimeout(function(){
    window._acHistOffset = 0;
    cargarAcondHistorial();
  }, 350);
}
async function cargarAcondHistorial(){
  var tb = document.getElementById('ac-tbody');
  var ft = document.getElementById('ac-hist-footer');
  if(!tb) return;
  var q = (document.getElementById('ac-q')||{}).value || '';
  var limit = window._acHistLimit;
  var offset = window._acHistOffset || 0;
  var url = '/api/acondicionamiento?limit='+limit+'&offset='+offset+(q ? '&q='+encodeURIComponent(q) : '');
  try{
    var r = await fetch(url, {credentials:'same-origin'});
    var d = await r.json();
    // Backward compat: si response es array (schema viejo), usar directo
    var rows = Array.isArray(d) ? d : (d.items || []);
    var total = Array.isArray(d) ? rows.length : (d.total || 0);
    if(!rows.length){
      tb.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#999;padding:12px;">Sin registros</td></tr>';
      if(ft) ft.innerHTML = 'Total: 0';
      return;
    }
    tb.innerHTML = rows.map(function(r){
      var fec = (r.fecha||'').substring(0,16);
      return '<tr style="border-bottom:1px solid #eee">'+
        '<td style="padding:7px;font-family:monospace;font-size:12px;color:#0d47a1;font-weight:700">'+_escHTML(r.lote||'')+'</td>'+
        '<td style="padding:7px">'+_escHTML(r.producto||'')+'</td>'+
        '<td style="padding:7px;text-align:center;font-weight:700">'+(r.unidades_producidas||0)+'</td>'+
        '<td style="padding:7px;text-align:center">'+_escHTML(r.presentacion||'—')+'</td>'+
        '<td style="padding:7px;text-align:center;font-family:monospace;font-size:11px">'+_escHTML(r.sku||'—')+'</td>'+
        '<td style="padding:7px;font-size:12px">'+_escHTML(fec)+'</td>'+
        '<td style="padding:7px;font-size:12px">'+_escHTML(r.operador||'—')+'</td>'+
        '<td style="padding:7px;text-align:center"><button data-acond-act="detalle" data-aid="'+r.id+'" style="background:#7c3aed;color:#fff;border:none;padding:3px 8px;border-radius:4px;font-size:10px;cursor:pointer">📋</button></td>'+
      '</tr>';
    }).join('');
    if(ft){
      var d_n = (offset||0) + 1;
      var h_n = (offset||0) + rows.length;
      var pag = '';
      if(offset > 0) pag += '<button onclick="window._acHistOffset=Math.max(0,window._acHistOffset-'+limit+');cargarAcondHistorial()" style="padding:4px 10px;background:#475569;color:#fff;border:none;border-radius:4px;font-size:11px;cursor:pointer;margin-right:4px">← Anterior</button>';
      if(offset + limit < total) pag += '<button onclick="window._acHistOffset+='+limit+';cargarAcondHistorial()" style="padding:4px 10px;background:#0d47a1;color:#fff;border:none;border-radius:4px;font-size:11px;cursor:pointer">Siguiente →</button>';
      ft.innerHTML = '<span>Mostrando '+d_n+'–'+h_n+' de '+total.toLocaleString()+'</span><span>'+pag+'</span>';
    }
  }catch(e){
    tb.innerHTML = '<tr><td colspan="8" style="color:#c00;text-align:center;padding:10px">Error: '+_escHTML(e.message)+'</td></tr>';
  }
}
if(typeof document !== 'undefined' && !window._ACOND_DELEG){
  window._ACOND_DELEG = true;
  document.addEventListener('click', function(ev){
    var b = ev.target && ev.target.closest && ev.target.closest('[data-acond-act="detalle"]');
    if(!b) return;
    verDetalleAcond(b.getAttribute('data-aid'));
  });
}
async function verDetalleAcond(aid){
  try{
    var r = await fetch('/api/acondicionamiento/'+aid+'/detalle');
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    var ex = document.getElementById('m-acond-det'); if(ex) ex.remove();
    var div = document.createElement('div');
    div.id = 'm-acond-det';
    div.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px';
    var meeRows = (d.mee_consumido_parsed||[]).map(function(m){
      return '<tr><td style="font-family:monospace">'+_escHTML(m.codigo||m.codigo_mee||'')+'</td><td>'+_escHTML(m.descripcion||m.nombre_mee||'')+'</td><td style="text-align:right;font-weight:700">'+(m.cantidad||0)+'</td></tr>';
    }).join('');
    div.innerHTML = '<div style="background:#fff;border-radius:12px;padding:20px;max-width:720px;width:100%;max-height:90vh;overflow-y:auto">'+
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><h3 style="margin:0;color:#0d47a1">🔧 Detalle Acondicionamiento · '+_escHTML(d.lote||'')+'</h3><button id="ac-det-close" style="background:none;border:none;font-size:1.4em;cursor:pointer">×</button></div>'+
      '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;background:#f8fafc;padding:12px;border-radius:8px;margin-bottom:14px;font-size:13px">'+
        '<div><b>Producto</b><br>'+_escHTML(d.producto||'')+'</div>'+
        '<div><b>Lote PT</b><br><span style="font-family:monospace;color:#dc2626;font-weight:700">'+_escHTML(d.lote||'')+'</span></div>'+
        '<div><b>SKU</b><br>'+_escHTML(d.sku||'—')+'</div>'+
        '<div><b>Unidades</b><br><span style="font-size:18px;font-weight:800;color:#0d47a1">'+(d.unidades_producidas||0)+'</span></div>'+
        '<div><b>Batch</b><br>'+(d.cantidad_batch_g||0)+' g</div>'+
        '<div><b>Presentación</b><br>'+_escHTML(d.presentacion||'—')+'</div>'+
        '<div><b>Fecha</b><br>'+_escHTML((d.fecha||'').substring(0,16))+'</div>'+
        '<div><b>Operador</b><br>'+_escHTML(d.operador||'—')+'</div>'+
      '</div>'+
      '<h4 style="margin:14px 0 6px;color:#475569;font-size:13px">📦 MEE consumido</h4>'+
      '<table class="table" style="font-size:11px"><thead><tr><th>Código</th><th>Descripción</th><th style="text-align:right">Unidades</th></tr></thead><tbody>'+
        (meeRows || '<tr><td colspan="3" style="text-align:center;color:#94a3b8">Sin MEE registrados</td></tr>')+
      '</tbody></table>'+
      (d.observaciones ? '<div style="margin-top:12px;padding:8px;background:#fef3c7;border-left:3px solid #ca8a04;font-size:12px"><b>Observaciones:</b><br>'+_escHTML(d.observaciones)+'</div>' : '')+
      '</div>';
    document.body.appendChild(div);
    document.getElementById('ac-det-close').onclick = function(){ div.remove(); };
    div.addEventListener('click', function(e){ if(e.target === div) div.remove(); });
  }catch(e){ alert('Error red: '+e.message); }
}

/* ============================================================
   PROGRAMACION — placeholder (Phase 2)
   ============================================================ */
async function sincronizarShopify(btnEl){
  if(btnEl){ btnEl.disabled=true; btnEl.textContent='Sincronizando...'; }
  try {
    var resp = await fetch('/api/programacion/sync-stock-shopify', {method:'POST', headers:{'Content-Type':'application/json'}});
    var txt = await resp.text();
    var d;
    try { d = JSON.parse(txt); } catch(pe){ alert('Error parse JSON: ' + txt.substring(0,300)); return; }
    if(d.ok){
      _toast(d.mensaje || (d.synced + ' SKUs sincronizados'), 1);
      cargarProgramacion(null);
    } else {
      alert('ERROR SYNC SHOPIFY: ' + (d.error || JSON.stringify(d)));
    }
  } catch(e){
    alert('Error de red: ' + e.message);
  } finally {
    if(btnEl){ btnEl.disabled=false; btnEl.textContent='Sincronizar Shopify'; }
  }
}

async function sincronizarVentas(btnEl){
  if(btnEl){ btnEl.disabled=true; btnEl.textContent='Sincronizando...'; }
  try {
    var resp = await fetch('/api/programacion/sync-ventas', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({days:60})});
    var txt = await resp.text();
    var d;
    try { d = JSON.parse(txt); } catch(pe){ alert('Error parse: ' + txt.substring(0,300)); return; }
    if(d.ok){
      _toast(d.mensaje || (d.synced + ' ordenes sync'), 1);
      cargarProgramacion(null);
    } else {
      alert('ERROR SYNC VENTAS: ' + (d.error || JSON.stringify(d)));
    }
  } catch(e){
    alert('Error de red: ' + e.message);
  } finally {
    if(btnEl){ btnEl.disabled=false; btnEl.textContent='Sync Ventas'; }
  }
}

async function cargarProgramacion(btnEl){
  if(btnEl){ btnEl.disabled = true; btnEl.textContent = 'Cargando...'; }
  var iaStatus = document.getElementById('prog-ia-status');
  if(iaStatus) iaStatus.textContent = 'Consultando Shopify + Stock + IA…';
  try{
    var r = await fetch('/api/programacion/resumen');
    var d = await r.json();
    if(d.error && !d.proyeccion){
      _toast(d.error, 0);
      if(iaStatus) iaStatus.textContent = d.error;
      return;
    }
    _renderProgramacion(d);
  }catch(e){
    _toast('Error al cargar programación: ' + e.message, 0);
    if(iaStatus) iaStatus.textContent = 'Error: ' + e.message;
  }finally{
    if(btnEl){ btnEl.disabled = false; btnEl.textContent = '🔄 Actualizar'; }
  }
}

async function generarOCProgramacion(btnEl){
  if(!confirm('Crear solicitud de compra automática para todos los MPs faltantes?')) return;
  if(btnEl){ btnEl.disabled = true; btnEl.textContent = 'Generando...'; }
  try{
    var r = await fetch('/api/programacion/generar-oc', {method:'POST', headers:{'Content-Type':'application/json'}});
    var d = await r.json();
    if(d.ok){
      _toast('✅ ' + d.mensaje, 1);
    } else {
      _toast('Error: ' + (d.error || 'desconocido'), 0);
    }
  }catch(e){
    _toast('Error de red: ' + e.message, 0);
  }finally{
    if(btnEl){ btnEl.disabled = false; btnEl.textContent = '🛒 Generar OC'; }
  }
}

document.addEventListener('click', async function(e){
  var btn = e.target.closest('.btn-stock-init');
  if(!btn) return;
  var producto = btn.getAttribute('data-prod');
  var sku = btn.getAttribute('data-sku') || producto;
  var uds = prompt('Unidades fisicas de ' + producto + ' en bodega Espagiria (listas para ANIMUS):');
  if(!uds || isNaN(parseInt(uds)) || parseInt(uds) <= 0) return;
  var lote = prompt('Lote (Enter para auto-generar):', '');
  var body = {producto: producto, sku: sku, unidades: parseInt(uds)};
  if(lote && lote.trim()) body.lote = lote.trim();
  try{
    var r = await fetch('/api/programacion/registrar-stock', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if(d.ok){ _toast('Stock registrado: ' + d.unidades + ' uds de ' + d.producto, 1); cargarProgramacion(null); }
    else { _toast('Error: ' + (d.error||'desconocido'), 0); }
  }catch(e){ _toast('Error de red', 0); }
});

function _renderProgramacion(d){
  var vel = document.getElementById('prog-vel-val');
  var cal = document.getElementById('prog-cal-val');
  var alerts = document.getElementById('prog-alert-val');
  var iaStatus = document.getElementById('prog-ia-status');
  var iaBox = document.getElementById('prog-ia-box');
  var iaText = document.getElementById('prog-ia-text');
  if(vel && d.velocidad_total !== undefined) vel.textContent = d.velocidad_total;
  if(cal && d.proxima_produccion) cal.textContent = d.proxima_produccion;
  if(alerts && d.n_alertas !== undefined) alerts.textContent = d.n_alertas;
  if(d.narrativa_ia && iaBox && iaText){
    iaBox.style.display = 'block';
    iaText.textContent = d.narrativa_ia;
    if(iaStatus) iaStatus.textContent = 'Actualizado';
  }
  // Warnings de integridad de datos (alias collisions, calendar fail, velocidad pobre, fórmulas incompletas)
  var warnBox = document.getElementById('prog-warnings');
  if(warnBox){
    var ws = (d.warnings_datos || []);
    if(!ws.length){
      warnBox.style.display = 'none';
      warnBox.innerHTML = '';
    } else {
      warnBox.style.display = 'block';
      warnBox.innerHTML = '<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:12px 16px;margin-bottom:14px;">'
        + '<div style="font-weight:700;color:#856404;margin-bottom:8px;font-size:13px;">⚠️ ' + ws.length + ' advertencia(s) de integridad de datos</div>'
        + ws.map(function(w, idx){
            var color = w.severidad === 'alta' ? '#c00' : (w.severidad === 'media' ? '#856404' : '#666');
            var prods = '';
            if(w.productos && w.productos.length){
              prods = '<div style="font-size:11px;color:#555;margin-top:6px"><b>Productos afectados:</b> '
                    + w.productos.slice(0,5).map(function(p){
                        return '<span style="background:#fef3c7;padding:2px 7px;border-radius:6px;color:#1c1917;font-weight:600;font-size:11px">'+_escHTML(p)+'</span>';
                      }).join(' ')
                    + (w.productos.length > 5 ? ' +'+(w.productos.length-5)+' más' : '')
                    + ' <a href="/tecnica" target="_blank" style="color:#7c3aed;text-decoration:underline;margin-left:6px;font-weight:600">→ Ir a /tecnica</a>'
                    + '</div>';
            }
            // Detalle de alias_collision: mostrar variantes con boton para fusionar
            var detalleHtml = '';
            if(w.tipo === 'alias_collision' && w.detalle && w.detalle.length){
              detalleHtml = '<div style="margin-top:8px;background:#fffbeb;border:1px solid #fde68a;border-radius:6px;padding:8px 10px">'
                + '<div style="font-size:11px;font-weight:700;color:#92400e;margin-bottom:5px">🔍 MPs que colisionan:</div>'
                + w.detalle.map(function(g){
                    var vlist = (g.variantes||[]).map(function(v){
                      return '<li style="margin:3px 0"><span style="font-family:monospace;font-size:11px;background:#fef3c7;padding:1px 6px;border-radius:4px;color:#1c1917">'+_escHTML(v.codigo)+'</span> <span style="font-size:11px">'+_escHTML(v.nombre)+'</span></li>';
                    }).join('');
                    return '<div style="margin-bottom:6px;padding-bottom:6px;border-bottom:1px dashed #fde68a">'
                      + '<div style="font-size:10px;color:#78716c;margin-bottom:3px">Normalizado: <code style="background:#fff;padding:1px 5px;border-radius:3px">'+_escHTML(g.normalizado)+'</code></div>'
                      + '<ul style="margin:0;padding-left:18px">'+vlist+'</ul>'
                      + '</div>';
                  }).join('')
                + '<div style="font-size:11px;color:#475569;margin-top:6px"><b>Cómo arreglar:</b> Decide cuál nombre es el canónico, edita el otro en <a href="/inventarios" target="_blank" style="color:#7c3aed;font-weight:600">Bodega MP → Limpiar proveedores</a> o ajusta los nombres en <code>maestro_mps</code> para que sean idénticos cuando son el mismo producto.</div>'
                + '</div>';
            }
            return '<div style="font-size:12px;color:'+color+';padding:8px 0;border-top:1px dashed #e0d8a8;">'
              + '<strong>['+w.tipo+']</strong> ' + w.mensaje
              + (w.accion ? '<div style="font-size:11px;color:#666;font-style:italic;margin-top:2px;">→ ' + w.accion + '</div>' : '')
              + prods
              + detalleHtml
              + '</div>';
          }).join('')
        + '</div>';
    }
  }
  // Render projection table
  var tbody = document.getElementById('prog-tbody');
  if(tbody && d.proyeccion && d.proyeccion.length){
    tbody.innerHTML = d.proyeccion.map(function(p){
      var semColor = p.semaforo === 'verde' ? '#28a745' : p.semaforo === 'amarillo' ? '#fd7e14' : '#dc3545';
      var semEmoji = p.semaforo === 'verde' ? '✅' : p.semaforo === 'amarillo' ? '⚠️' : '🚨';
      // MPs: ✅ all OK | ⚠️ data gap (not in movimientos) | ❌ confirmed deficit
      var mpIcon = p.mp_lista === null ? '?' :
                   (p.mp_lista === true ? '✅' :
                   (p.mp_lista === false ? '❌' :
                   (p.mp_data_gap ? '⚠️' : '?')));
      // If no confirmed deficit but has data gaps, show warning instead of X
      if (p.mp_lista !== false && p.mp_data_gap) mpIcon = '⚠️';
      var skuKey = p.sku || p.producto;
      var calIcon = p.cal_ok ? '✅' : (p.prox_produccion === 'No programado' ? '❌' : '⚠️');
      var diasStr = p.dias_cobertura !== null && p.dias_cobertura !== undefined ? p.dias_cobertura + 'd' : '---';
      // BUG-5 fix · 20-may-2026 Dashboard PRO audit · null<20 === true en JS:
      // SKUs con cobertura infinita (sin ventas) se pintaban en ROJO crítico
      // aunque el texto al lado fuera '---'. Guard explícito para null/undefined.
      var diasColor = (p.dias_cobertura == null) ? '#94a3b8'
                     : (p.dias_cobertura < 20 ? '#dc3545'
                     : (p.dias_cobertura < 40 ? '#fd7e14' : '#28a745'));
      var isPast = p.prox_prod_pasada === true;
      var progLabel, progBtnColor;
      if (p.prox_produccion === 'No programado') {
        progLabel = '📅 Programar'; progBtnColor = '#6c757d';
      } else if (isPast) {
        progLabel = '⚠️ ' + p.prox_produccion + ' — ¿completada?'; progBtnColor = '#e67e00';
      } else {
        progLabel = '📅 ' + p.prox_produccion; progBtnColor = '#198754';
      }
      // Faltantes por horizonte: 0 = OK (verde), >0 = se queda corto (rojo)
      var f15 = p.faltante_uds_15d || 0;
      var f30 = p.faltante_uds_30d || 0;
      var f60 = p.faltante_uds_60d || 0;
      var f15Cell = f15 > 0
        ? '<span style="color:#dc2626;font-weight:700">'+f15+' uds</span>'
        : '<span style="color:#16a34a">✓</span>';
      var f30Cell = f30 > 0
        ? '<span style="color:#dc2626;font-weight:700">'+f30+' uds</span>'
        : '<span style="color:#16a34a">✓</span>';
      var f60Cell = f60 > 0
        ? '<span style="color:#dc2626;font-weight:700">'+f60+' uds</span>'
        : '<span style="color:#16a34a">✓</span>';
      return '<tr style="border-bottom:1px solid #eee">' +
        '<td style="padding:9px;font-weight:600">'+p.producto+'</td>' +
        '<td style="padding:9px;text-align:center">'+p.stock_actual+'</td>' +
        '<td style="padding:9px;text-align:center">'+p.vel_mes+'</td>' +
        '<td style="padding:9px;text-align:center;font-weight:700;color:'+diasColor+'">'+diasStr+'</td>' +
        '<td style="padding:9px;text-align:center;background:#fffbeb">'+f15Cell+'</td>' +
        '<td style="padding:9px;text-align:center;background:#fff7ed">'+f30Cell+'</td>' +
        '<td style="padding:9px;text-align:center;background:#fef2f2">'+f60Cell+'</td>' +
        '<td style="padding:9px;text-align:center">' +
          '<button data-prod="' + p.producto + '" onclick="abrirModalProgramar(this.dataset.prod)" style="background:'+progBtnColor+';color:#fff;border:none;border-radius:6px;padding:3px 9px;font-size:11px;cursor:pointer;white-space:nowrap">'+progLabel+'</button>' +
        '</td>' +
        '<td style="padding:9px;text-align:center;font-size:16px">'+calIcon+'</td>' +
        '<td style="padding:9px;text-align:center;font-size:16px">'+mpIcon+'</td>' +
        '<td style="padding:9px;text-align:center"><span style="background:'+semColor+';color:#fff;padding:3px 10px;border-radius:10px;font-size:12px">'+semEmoji+' '+p.semaforo+'</span></td>' +
        '<td style="padding:9px;text-align:center"><button class="btn-stock-init btn btn-ghost btn-sm" style="font-size:11px;padding:2px 8px" data-prod="'+p.producto+'" data-sku="'+skuKey+'">+Stock</button></td>' +
        '</tr>';
    }).join('');
  }
  // Render alerts
  var alertsDiv = document.getElementById('prog-alertas');
  if(alertsDiv && d.alertas && d.alertas.length){
    alertsDiv.innerHTML = d.alertas.map(function(a){
      var color = a.nivel === 'critico' ? '#dc3545' : a.nivel === 'alto' ? '#fd7e14' : '#ffc107';
      return '<div style="background:#fff5f5;border-left:4px solid '+color+';border-radius:4px;padding:10px 14px;margin-bottom:8px">' +
        '<div style="font-weight:600;color:'+color+';font-size:13px">⚠ '+a.producto+'</div>' +
        '<div style="font-size:12px;color:#555;margin-top:3px">'+a.mensaje+'</div>' +
        '</div>';
    }).join('');
  } else if(alertsDiv){
    alertsDiv.innerHTML = '<div style="text-align:center;color:#28a745;padding:20px;font-size:14px">✅ Sin alertas criticas</div>';
  }
}

