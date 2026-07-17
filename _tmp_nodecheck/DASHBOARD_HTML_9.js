
// Estado del auto-refresh
window._ckAutoRefreshTimer = null;
window._ckAutoRefreshSec = 60;
window._ckLastDias = 60;

function ckSetAutoRefresh(seg){
  // Detener timer existente
  if(window._ckAutoRefreshTimer){
    clearInterval(window._ckAutoRefreshTimer);
    window._ckAutoRefreshTimer = null;
  }
  var s = parseInt(seg||0, 10);
  window._ckAutoRefreshSec = s;
  if(!s){ return; }
  window._ckAutoRefreshTimer = setInterval(function(){
    // Pausar si la pestaña no esta visible (no quema requests innecesarios)
    if(document.visibilityState !== 'visible') return;
    // Solo si seguimos en el tab del checklist
    var tab = document.getElementById('ptab-checklist');
    if(!tab || tab.style.display === 'none') return;
    cargarChecklistResumen(window._ckLastDias);
  }, s * 1000);
}

function ckFmtRelativo(isoUtc){
  if(!isoUtc) return '—';
  try {
    var t = new Date(isoUtc).getTime();
    if(isNaN(t)) return isoUtc;
    var seg = Math.max(0, Math.round((Date.now() - t) / 1000));
    if(seg < 60) return 'hace '+seg+'s';
    var min = Math.round(seg/60);
    if(min < 60) return 'hace '+min+' min';
    var h = Math.round(min/60);
    if(h < 24) return 'hace '+h+'h';
    return 'hace '+Math.round(h/24)+'d';
  } catch(e){ return '—'; }
}

async function cargarChecklistResumen(dias){
  // Cargar catalogo de productos en paralelo (no bloquea)
  if(typeof cargarCatalogoProductos==='function') cargarCatalogoProductos();
  if(dias){
    document.querySelectorAll('[id^=ck-h-]').forEach(b=>{
      var match = b.id.match(/ck-h-(\d+)/);
      if(match){
        var d = parseInt(match[1]);
        b.style.background = d===dias?'#15803d':'#fff';
        b.style.color      = d===dias?'#fff':'#15803d';
      }
    });
  }
  dias = dias || 60;
  window._ckLastDias = dias;
  document.getElementById('ck-loading').style.display='block';
  document.getElementById('ck-empty').style.display='none';
  document.getElementById('ck-producciones-list').innerHTML='';
  document.getElementById('ck-resumen-cards').innerHTML='';
  try {
    var r = await fetch('/api/programacion/checklist/resumen-calendario?dias='+dias);
    var d = await r.json();
    document.getElementById('ck-loading').style.display='none';
    // Indicador de ultima sincronizacion
    var sc = d.sync_calendario || {};
    var lastEl = document.getElementById('ck-last-sync');
    if(lastEl){
      var rel = ckFmtRelativo(sc.last_run_at);
      var nuevas = sc.producciones_nuevas || 0;
      lastEl.textContent = 'última sync calendario: ' + rel + (nuevas>0 ? ' · '+nuevas+' nueva(s) producción(es) importada(s)' : '');
      lastEl.style.color = sc.last_error ? '#dc2626' : '#15803d';
      if(sc.last_error){ lastEl.title = sc.last_error; }
    }
    var prods = d.producciones || [];
    if(!prods.length){
      document.getElementById('ck-empty').style.display='block';
      return;
    }
    // Cards de resumen
    var verde = prods.filter(p=>p.semaforo==='verde').length;
    var amar = prods.filter(p=>p.semaforo==='amarillo').length;
    var rojo = prods.filter(p=>p.semaforo==='rojo').length;
    var sinChecklist = prods.filter(p=>p.total_items===0).length;
    document.getElementById('ck-resumen-cards').innerHTML =
      cardKpi('Producciones', prods.length, '#1c1917', '') +
      cardKpi('🟢 Verde', verde, '#15803d', '>=90% listo') +
      cardKpi('🟡 Amarillo', amar, '#f59e0b', '50-89%') +
      cardKpi('🔴 Rojo', rojo, '#dc2626', '<50%') +
      cardKpi('Sin checklist', sinChecklist, '#78716c', 'click "Generar"');
    // Guardar lista para navegacion siguiente/anterior dentro del modal
    window._ckLista = prods.filter(function(p){ return (p.total_items||0) > 0; });
    // Sebastián 12-may-2026: AGRUPAR POR SEMANA (Lun-Dom).
    // Antes: lista plana ordenada por fecha · usuario no podía leer "qué hay
    // esta semana vs próxima". Ahora cada semana tiene header con rango +
    // conteo + suma de kg programados, y las producciones anidadas dentro.
    document.getElementById('ck-producciones-list').innerHTML = renderProduccionesPorSemana(prods);
  } catch(e){
    document.getElementById('ck-loading').style.display='none';
    document.getElementById('ck-empty').textContent='Error: '+e.message;
    document.getElementById('ck-empty').style.display='block';
  }
}

function cardKpi(label, val, color, sub){
  return '<div style="background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:14px;text-align:center">' +
    '<div style="font-size:10px;color:#78716c;text-transform:uppercase;letter-spacing:0.5px;font-weight:700">'+label+'</div>' +
    '<div style="font-size:1.6em;font-weight:800;color:'+color+';margin:4px 0">'+val+'</div>' +
    (sub?'<div style="font-size:10px;color:#a8a29e">'+sub+'</div>':'') +
    '</div>';
}

// Sebastián 12-may-2026: agrupar producciones por semana ISO (Lun-Dom).
// Resuelve queja "no está ordenado por semana realmente". Header sticky
// con rango Lun-Dom + total kg + count. Click colapsa/expande.
function _lunesDe(fechaStr){
  // fechaStr formato YYYY-MM-DD · devuelve Date del Lun de esa semana ISO
  var d = new Date(fechaStr + 'T00:00:00');
  var dia = d.getDay();  // 0=Dom, 1=Lun, ..., 6=Sab
  // Si es Dom (0), retroceder 6 días; si es Lun (1), 0 días; etc
  var offset = dia === 0 ? -6 : 1 - dia;
  d.setDate(d.getDate() + offset);
  return d;
}
function _fmtFechaCorta(d){
  var meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
  return d.getDate() + ' ' + meses[d.getMonth()];
}
function _semanaKey(fechaStr){
  var lun = _lunesDe(fechaStr);
  return lun.toISOString().slice(0,10);
}

function renderProduccionesPorSemana(prods){
  if(!prods || !prods.length) return '';
  // Agrupar
  var grupos = {};
  prods.forEach(function(p){
    var f = p.fecha_objetivo || p.fecha_programada || '';
    if(!f) return;
    var key = _semanaKey(f);
    if(!grupos[key]) grupos[key] = [];
    grupos[key].push(p);
  });
  // Ordenar semanas asc
  var keys = Object.keys(grupos).sort();
  var hoy = new Date(); hoy.setHours(0,0,0,0);
  var lunesHoy = _lunesDe(hoy.toISOString().slice(0,10));
  var lunesHoyKey = lunesHoy.toISOString().slice(0,10);
  var html = '';
  keys.forEach(function(key){
    var lun = new Date(key + 'T00:00:00');
    var dom = new Date(lun); dom.setDate(dom.getDate()+6);
    var rango = 'Semana ' + _fmtFechaCorta(lun) + ' - ' + _fmtFechaCorta(dom);
    if(key === lunesHoyKey) rango += ' · ESTA SEMANA';
    var items = grupos[key];
    // Total kg programados de la semana
    var totalKg = items.reduce(function(s,p){ return s + (parseFloat(p.cantidad_kg)||0); }, 0);
    var nProd = items.length;
    var bgHeader = key === lunesHoyKey ? '#dcfce7' : '#f1f5f9';
    var fgHeader = key === lunesHoyKey ? '#15803d' : '#0f172a';
    html += '<div style="margin-top:18px;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden">' +
      '<div style="background:'+bgHeader+';padding:10px 14px;font-weight:700;font-size:13px;color:'+fgHeader+';display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e5e7eb">' +
        '<span>📅 ' + rango + '</span>' +
        '<span style="font-size:11px;font-weight:600">' + nProd + ' producción(es) · ' + totalKg.toFixed(1) + ' kg</span>' +
      '</div>' +
      '<div>' + items.map(rowProduccion).join('') + '</div>' +
    '</div>';
  });
  return html;
}

function rowProduccion(p){
  var color = p.semaforo==='verde' ? '#15803d' : p.semaforo==='amarillo' ? '#f59e0b' : '#dc2626';
  var diasTxt = p.dias_faltan>=0 ? p.dias_faltan+' días' : 'hace '+Math.abs(p.dias_faltan)+'d';
  var diasColor = p.dias_faltan<0 ? '#dc2626' : p.dias_faltan<=7 ? '#f59e0b' : '#15803d';
  var pct = p.porcentaje || 0;
  var noChecklist = (p.total_items||0)===0;
  // Pills de estado: cada estado con icono propio + tooltip explicativo + color distintivo.
  // Solo se muestran los estados con count>0 para no saturar.
  var pills = '';
  function pill(cnt, ico, label, bg, fg, tip){
    if(!cnt) return '';
    return '<span title="'+tip+'" style="display:inline-flex;align-items:center;gap:3px;background:'+bg+';color:'+fg+';font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;margin:1px 0 1px 4px">'+ico+' '+cnt+'</span>';
  }
  pills += pill(p.pendientes,   '🔴', 'pend', '#fee2e2', '#991b1b', 'Pendiente — falta elegir o solicitar');
  pills += pill(p.solicitados,  '⏳', 'sol',  '#fef3c7', '#92400e', 'Solicitado — en cola de Catalina (Compras)');
  pills += pill(p.en_transito,  '🚚', 'tra',  '#dbeafe', '#1e40af', 'En tránsito — OC creada, esperando llegada');
  pills += pill(p.recibidos,    '📦', 'rec',  '#dcfce7', '#166534', 'Recibido — ya está en bodega');
  pills += pill(p.no_aplica,    '—',  'na',   '#f5f5f4', '#78716c', 'No aplica para este producto');
  // Barra de progreso visual
  var barraHtml = noChecklist ? '' :
    '<div style="background:#e7e5e4;border-radius:6px;height:8px;overflow:hidden;margin-top:6px">' +
      '<div style="background:'+color+';height:100%;width:'+pct+'%;transition:width .3s"></div>' +
    '</div>';
  // Badge de origen: distingue producciones del calendario auto-sync vs manuales
  var origenBadge = (p.origen === 'calendar')
    ? '<span title="Sincronizada desde Google Calendar" style="background:#dbeafe;color:#1e40af;font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;margin-left:6px">📅 cal</span>'
    : '<span title="Entrada manual (no viene del calendario) — si esta duplicada, click ✖ para borrar" style="background:#fef3c7;color:#92400e;font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;margin-left:6px">✋ man</span>';
  // Boton borrar (X) inline al lado del nombre — solo admin, valida en backend.
  var btnBorrar = '<button onclick="event.stopPropagation();ckBorrarProduccion('+p.id+', '+JSON.stringify(p.producto_nombre).replace(/"/g,'&quot;')+', '+JSON.stringify(p.fecha_planeada).replace(/"/g,'&quot;')+')" title="Borrar esta producción (admin) — útil para limpiar duplicados/fantasmas" style="background:transparent;color:#dc2626;border:1px solid #fca5a5;border-radius:4px;width:20px;height:20px;font-size:10px;font-weight:700;cursor:pointer;padding:0;line-height:1;margin-left:6px;vertical-align:middle">✖</button>';
  // Sebastian (29-abr-2026): badge "✅ Completada" si ya descontó inventario.
  // Si NO ha descontado y el checklist está al 80%+, botón "✅ Completar y descontar".
  var yaCompletada = !!p.descontado_at;
  var badgeCompletada = yaCompletada
    ? '<span title="Inventario descontado el '+_escHTML(p.descontado_at)+'" style="background:#dcfce7;color:#15803d;font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;margin-left:6px">✅ completada</span>'
    : '';
  // Botón "Completar" si checklist >= 80% Y NO se ha descontado aún
  var btnCompletar = '';
  if(!yaCompletada && !noChecklist && pct >= 80){
    btnCompletar = '<button onclick="event.stopPropagation();ckCompletarProduccion('+p.id+', '+JSON.stringify(p.producto_nombre).replace(/"/g,'&quot;')+')" title="Marca completada y descuenta MPs + envases del inventario" style="background:#15803d;color:#fff;border:none;border-radius:6px;padding:6px 12px;font-size:11px;font-weight:700;cursor:pointer;margin-top:6px;display:block;width:100%">✅ Completar y descontar</button>';
  } else if(yaCompletada){
    btnCompletar = '<button onclick="event.stopPropagation();ckRevertirCompletado('+p.id+', '+JSON.stringify(p.producto_nombre).replace(/"/g,'&quot;')+')" title="Revertir el descuento (solo admin)" style="background:transparent;color:#7c3aed;border:1px solid #67e8f9;border-radius:6px;padding:4px 10px;font-size:10px;font-weight:600;cursor:pointer;margin-top:6px">↩ Revertir</button>';
  }
  return '<div style="background:#fff;border:1px solid #e7e5e4;border-left:4px solid '+color+';border-radius:8px;padding:14px;display:grid;grid-template-columns:1fr auto auto auto;gap:14px;align-items:center;cursor:pointer" onclick="abrirChecklistDetalle('+p.id+', '+JSON.stringify(p.producto_nombre).replace(/"/g,'&quot;')+')">' +
    '<div>' +
      '<div style="font-weight:700;font-size:14px">'+_escHTML(p.producto_nombre)+origenBadge+badgeCompletada+btnBorrar+'</div>' +
      '<div style="font-size:11px;color:#78716c;margin-top:2px">' + (p.kg||0).toLocaleString('es-CO')+' kg · ' + p.fecha_planeada + '</div>' +
      barraHtml +
    '</div>' +
    '<div style="text-align:center;min-width:80px"><div style="font-weight:800;color:'+diasColor+';font-size:1.1em">'+diasTxt+'</div><div style="font-size:10px;color:#78716c">para producir</div></div>' +
    '<div style="min-width:140px">' +
      (noChecklist
        ? '<button onclick="event.stopPropagation();ckGenerar('+p.id+')" style="background:#a16207;color:#fff;border:none;border-radius:6px;padding:6px 12px;font-size:11px;font-weight:700;cursor:pointer">+ Generar checklist</button>'
        : '<div style="background:#f5f5f4;border-radius:8px;padding:6px 10px;text-align:center"><div style="font-weight:700;color:'+color+'">'+pct+'%</div><div style="font-size:10px;color:#78716c">'+(p.completados||0)+' de '+(p.total_items||0)+' OK</div></div>') +
      btnCompletar +
    '</div>' +
    '<div style="font-size:11px;color:#78716c;text-align:right;min-width:140px">' +
      (noChecklist ? '' : '<div style="text-align:right;line-height:1.6">'+pills+'</div>') +
      (noChecklist?'':'<div style="margin-top:4px;color:#15803d">Click para detalle →</div>') +
    '</div>' +
  '</div>';
}

async function ckGenerar(produccionId){
  try {
    var r = await fetch('/api/programacion/checklist/generar/'+produccionId, {method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||'')); return; }
    _toast('Checklist generado: '+d.items_creados+' items', 1);
    cargarChecklistResumen();
  } catch(e){ alert('Error: '+e.message); }
}

async function ckBackfill(){
  if(!confirm('Generar checklists para TODAS las producciones programadas que no tienen?')) return;
  try {
    var r = await fetch('/api/programacion/checklist/backfill', {method:'POST'});
    var d = await r.json();
    if(!r.ok){
      // Error en la fase de SELECT (ej. tabla rota) — mostrar detalle
      console.error('backfill error:', d);
      alert('Error: '+(d.error||r.status)+'\n\nDetalle en consola (F12).');
      return;
    }
    if(d.fallas && d.fallas.length){
      // Procesado parcial — listar las fallas
      console.warn('backfill con fallas:', d.fallas);
      var lista = d.fallas.slice(0, 5).map(function(f){
        return '• '+(f.producto||'?')+' ('+(f.fecha||'')+')\n  → '+(f.error||'').substring(0,150);
      }).join('\n');
      alert(d.mensaje + '\n\nFallas (top 5 de '+d.fallas.length+'):\n'+lista +
            '\n\nDetalle completo en consola (F12).');
    } else {
      _toast(d.mensaje, 1);
    }
    cargarChecklistResumen();
  } catch(e){ alert('Error: '+e.message); }
}

// Borra y regenera el checklist de una produccion — util cuando se actualizo
// la formula (lote_size_kg / volumen_unitario_ml) y queremos recalcular las
// cantidades de envases automaticamente con la nueva info.
// Borra HARD una produccion programada (admin only — backend valida).
// Util para limpiar duplicados o fantasmas que aparecen en el horizonte.
// Sebastian (29-abr-2026): "que todo descuente que el inventario este perfecto".
// Flujo: 1) dry_run para preview. 2) confirm con detalle. 3) descuento real.
async function ckCompletarProduccion(produccionId, producto){
  if(!produccionId){ alert('ID inválido'); return; }
  try {
    // Paso 1: dry_run para mostrar preview de qué se va a descontar
    var rPrev = await fetch('/api/programacion/programar/'+produccionId+'/completar',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({dry_run:true})
    });
    var rawP = await rPrev.text();
    var prev = null; try { prev = JSON.parse(rawP); } catch(_){}
    if(!rPrev.ok){
      if(prev && prev.codigo === 'YA_DESCONTADO'){
        alert('Esta producción ya descontó inventario el '+prev.inventario_descontado_at+'.\n\nUsa "↩ Revertir" si necesitas re-hacer el descuento.');
        return;
      }
      alert('Error: '+(prev && prev.error || rawP.substring(0,200)));
      return;
    }
    var mps = prev.mps_a_descontar || [];
    var mees = prev.mees_a_descontar || [];
    if(!mps.length && !mees.length){
      if(!confirm('Esta producción NO tiene MPs en fórmula ni envases en checklist. ¿Marcar completada igual?')) return;
    } else {
      var msg = 'Confirmar completar "'+producto+'"?\n\n';
      msg += 'Se descontarán del inventario:\n';
      msg += '  • '+mps.length+' MPs ('+(prev.total_g_mps||0).toLocaleString('es-CO')+' g totales)\n';
      msg += '  • '+mees.length+' envases/etiquetas ('+(prev.total_unidades_mees||0)+' unidades)\n\n';
      if(mps.length){
        msg += 'MPs principales:\n';
        mps.slice(0,5).forEach(function(m){
          msg += '  - '+m.nombre+': '+Math.round(m.cantidad_g).toLocaleString('es-CO')+' g\n';
        });
        if(mps.length > 5) msg += '  ...y '+(mps.length-5)+' más\n';
      }
      msg += '\nEsto NO se puede deshacer fácilmente (admin tiene "↩ Revertir"). ¿Continuar?';
      if(!confirm(msg)) return;
    }
    // Paso 2: descuento real
    var r = await fetch('/api/programacion/programar/'+produccionId+'/completar',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({})
    });
    var raw = await r.text();
    var d = null; try { d = JSON.parse(raw); } catch(_){}
    if(!r.ok){
      alert('Error al descontar: '+(d && d.error || raw.substring(0,200)));
      return;
    }
    _toast('✅ '+(d.mensaje || 'Producción completada'), 1);
    cargarChecklistResumen(window._ckLastDias || 60);
  } catch(e){ alert('Error de red: '+e.message); }
}

async function ckRevertirCompletado(produccionId, producto){
  if(!confirm('¿Revertir el descuento de "'+producto+'"?\n\nEsto regresará MPs y envases al inventario, y la producción volverá a estado "programado". Solo admin puede hacer esto.')) return;
  try {
    var r = await fetch('/api/programacion/programar/'+produccionId+'/revertir-completado',{
      method:'POST', headers:{'Content-Type':'application/json'}, body: '{}'
    });
    var raw = await r.text();
    var d = null; try { d = JSON.parse(raw); } catch(_){}
    if(!r.ok){
      if(r.status === 403){ alert('Solo admin puede revertir.'); return; }
      alert('Error: '+(d && d.error || raw.substring(0,200)));
      return;
    }
    _toast(d.mensaje || 'Revertido', 1);
    cargarChecklistResumen(window._ckLastDias || 60);
  } catch(e){ alert('Error: '+e.message); }
}

async function ckBorrarProduccion(produccionId, producto, fecha){
  // Guard: si el id no llegó (fila vieja o cache stale), abortar con mensaje claro
  if(!produccionId || produccionId === 'undefined' || produccionId === 'null'){
    alert('Esta tarjeta no tiene id válido. Recarga la página (Ctrl+F5) e intenta de nuevo.');
    return;
  }
  if(!confirm('¿Borrar la producción "'+producto+'" del '+fecha+'?\n\nEsto la elimina DEFINITIVAMENTE junto con su checklist. Solo úsalo para duplicados o fantasmas que NO existen en el calendario.')) return;
  try {
    var r = await fetch('/api/programacion/produccion-programada/'+produccionId+'/borrar', {method:'DELETE'});
    // Robusto: parse texto crudo y solo despues intentar JSON. Si la respuesta
    // es HTML (ej. login redirect, 404 de Flask, error 502 de Render), no
    // crasheamos con "Unexpected token '<'" — mostramos el error real.
    var raw = await r.text();
    var d = null;
    try { d = JSON.parse(raw); } catch(_){}
    if(!r.ok){
      if(d && d.error){ alert('Error '+r.status+': '+d.error); }
      else if(r.status === 401){ alert('Sesión expirada. Vuelve a entrar a /login y reintenta.'); }
      else if(r.status === 403){ alert('Sin permisos. Solo Sebastian/Alejandro pueden borrar producciones.'); }
      else if(r.status === 404){ alert('Producción no encontrada. Recarga (Ctrl+F5) — quizá ya fue borrada por otro usuario.'); }
      else { alert('Error '+r.status+'. Respuesta del servidor:\n\n'+raw.substring(0,300)); }
      return;
    }
    _toast((d && d.mensaje) || 'Borrada', 1);
    cargarChecklistResumen(window._ckLastDias || 60);
  } catch(e){ alert('Error de red: '+e.message); }
}

async function ckRegenerar(produccionId){
  if(!confirm('Borrar y regenerar el checklist de esta producción?\n\nEsto recalcula MPs y envases con la presentación actual del producto. Las correcciones manuales que hayas hecho se pierden.')) return;
  try {
    var r = await fetch('/api/programacion/checklist/generar/'+produccionId, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({forzar:true})
    });
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    _toast('Regenerado: '+(d.items_creados||0)+' items', 1);
    abrirChecklistDetalle(produccionId, window._ckCurrentProducto || '');
  } catch(e){ alert('Error: '+e.message); }
}

// Sincroniza eventos del Google Calendar (animuslb.com) → produccion_programada.
// Idempotente: usa (producto, fecha) como key. Auto-llamado al cargar el
// resumen, pero este boton da trigger manual + feedback visible.
// ─── Catálogo de productos con foto (sync masivo Shopify) ────────────
async function cargarCatalogoProductos(){
  try {
    var r = await fetch('/api/formulas/catalogo');
    var d = await r.json();
    if(!r.ok){ return; }
    var resumen = document.getElementById('cat-resumen');
    if(resumen){
      resumen.innerHTML = '<b style="color:#15803d">'+d.con_foto+'</b> con foto · '+
                          '<b style="color:#dc2626">'+d.sin_foto+'</b> sin foto · '+
                          d.total+' total';
    }
    var grid = document.getElementById('cat-grid');
    if(!grid) return;
    if(!d.productos || !d.productos.length){
      grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:#a8a29e;padding:20px;font-size:12px">No hay productos en formula_headers</div>';
      return;
    }
    grid.innerHTML = d.productos.map(function(p){
      var proxyUrl = '/api/imagen-producto/'+encodeURIComponent(p.nombre)+'?t='+Date.now();
      var fotoHtml;
      if(p.tiene_foto){
        fotoHtml = '<img src="'+proxyUrl+'" alt="'+_escHTML(p.nombre)+'" '+
                   'style="width:100%;height:120px;object-fit:cover;border-radius:6px;background:#f5f5f4" '+
                   'onerror="this.style.opacity=0.3">';
      } else {
        fotoHtml = '<div style="height:120px;background:#fef2f2;border:1px dashed #fca5a5;border-radius:6px;display:flex;align-items:center;justify-content:center;color:#dc2626;font-size:11px;font-weight:600">Sin foto</div>';
      }
      var skuLine = p.sku ? '<div style="font-size:10px;color:#6d28d9;font-weight:600">'+_escHTML(p.sku)+'</div>' : '';
      return '<div style="background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:8px;cursor:pointer" '+
             'onclick="catProductoClick(&quot;'+_escHTML(p.nombre).replace(/"/g,'&quot;')+'&quot;)" '+
             'title="Click para gestionar imagen">' +
        fotoHtml +
        '<div style="margin-top:6px;font-size:11px;font-weight:700;color:#1c1917;line-height:1.3;min-height:30px">'+_escHTML(p.nombre)+'</div>' +
        skuLine +
        '</div>';
    }).join('');
  } catch(e){
    console.error('catalogo:', e);
  }
}

async function syncShopifyAll(){
  var btn = document.getElementById('btn-sync-all');
  if(btn){ btn.disabled = true; btn.textContent = '⏳ Sincronizando...'; }
  try {
    var r = await fetch('/api/formulas/sync-shopify-blocking', {method:'POST'});
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    var msg = '✅ '+d.sincronizados+' sincronizados';
    if(d.no_encontrados) msg += ' · ⚠️ '+d.no_encontrados+' no encontrados en Shopify';
    if(d.errores) msg += ' · ❌ '+d.errores+' errores';
    alert(msg);
    cargarCatalogoProductos();
  } catch(e){
    alert('Error de red: '+e.message);
  } finally {
    if(btn){ btn.disabled = false; btn.innerHTML = '🔄 Sincronizar todos'; }
  }
}

async function catProductoClick(nombre){
  var url = prompt('URL de imagen para "'+nombre+'" (vacío = sync Shopify):', '');
  if(url===null) return;
  url = (url||'').trim();
  if(url){
    try {
      var r = await fetch('/api/formulas/'+encodeURIComponent(nombre)+'/imagen', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({imagen_url: url})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    } catch(e){ alert('Error: '+e.message); return; }
  } else {
    // Sync Shopify del producto puntual
    try {
      var r = await fetch('/api/formulas/'+encodeURIComponent(nombre)+'/imagen-shopify-sync', {method:'POST'});
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    } catch(e){ alert('Error: '+e.message); return; }
  }
  cargarCatalogoProductos();
}

async function ckSyncCalendario(){
  try {
    var r = await fetch('/api/programacion/checklist/sync-calendar?dias=90', {method:'POST'});
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||'')); return; }
    _toast(d.mensaje || 'Calendario sincronizado', 1);
    // Despues del sync, generar checklists faltantes automaticamente para
    // que las nuevas producciones aparezcan con sus items pre-poblados.
    if(d.producciones_creadas > 0){
      try { await fetch('/api/programacion/checklist/backfill', {method:'POST'}); } catch(e){}
    }
    cargarChecklistResumen();
  } catch(e){ alert('Error: '+e.message); }
}

async function abrirChecklistDetalle(produccionId, producto){
  document.getElementById('ck-modal').style.display='flex';
  document.getElementById('ck-modal-titulo').textContent = '📋 ' + producto;
  document.getElementById('ck-modal-items').innerHTML = '<div style="text-align:center;padding:40px;color:#78716c">Cargando...</div>';
  try {
    var r = await fetch('/api/programacion/checklist/'+produccionId);
    var d = await r.json();
    if(!r.ok){ document.getElementById('ck-modal-items').innerHTML='Error: '+(d.error||''); return; }
    var prim = (d.items||[])[0]||{};
    window._ckCurrentMeta = prim;  // guardar contexto para el editor inline (fecha_planeada, cantidad_kg, volumen_unitario_ml)
    var ckKg = prim.cantidad_kg||0;
    var subEl = document.getElementById('ck-modal-sub');
    if(ckKg > 0){
      subEl.innerHTML = ckKg.toLocaleString('es-CO')+' kg programada para '+(prim.fecha_planeada||'-')+
        ' &middot; <a href="javascript:void(0)" onclick="ckRegenerar('+produccionId+')" style="color:#a16207;font-size:11px;font-weight:700;text-decoration:none">🔁 Regenerar checklist</a>';
    } else {
      subEl.innerHTML = '<span style="color:#a16207">⚠️ Sin tamaño de lote — completa <code>lote_size_kg</code> en la fórmula o pon kg en el título del calendario</span>'+
        ' &middot; <a href="javascript:void(0)" onclick="ckRegenerar('+produccionId+')" style="color:#a16207;font-size:11px;font-weight:700;text-decoration:none">🔁 Regenerar</a>';
    }

    // Imagen del producto + acciones (sync Shopify, pegar URL manual)
    var imgWrap = document.getElementById('ck-modal-imagen');
    if(!imgWrap){
      imgWrap = document.createElement('div');
      imgWrap.id = 'ck-modal-imagen';
      imgWrap.style.cssText = 'margin-bottom:14px;display:flex;gap:14px;align-items:flex-start;background:#fafaf9;border:1px solid #e7e5e4;border-radius:10px;padding:12px';
      var prog = document.getElementById('ck-modal-progress');
      prog.parentNode.insertBefore(imgWrap, prog);
    }
    var prodNombre = d.producto_nombre || producto;
    var meta = d.producto_meta || {};
    // Proxy server-side para evitar hotlink/CORS de Shopify CDN
    var proxyBase = '/api/imagen-producto/' + encodeURIComponent(prodNombre);
    var imgHtml;
    if(d.imagen_url){
      imgHtml = '<img src="'+proxyBase+'?t='+Date.now()+'" alt="'+_escHTML(prodNombre)+'" '+
                'style="width:200px;height:200px;object-fit:cover;border-radius:10px;border:1px solid #e7e5e4;background:#fff;flex-shrink:0" '+
                'onerror="this.style.display=\'none\';if(this.nextElementSibling)this.nextElementSibling.style.display=\'flex\'">' +
                '<div style="display:none;width:200px;height:200px;background:#f5f5f4;border-radius:10px;align-items:center;justify-content:center;color:#a8a29e;font-size:12px;text-align:center;padding:12px;flex-shrink:0">Imagen no disponible</div>';
    } else {
      imgHtml = '<div style="width:200px;height:200px;background:#f5f5f4;border-radius:10px;display:flex;align-items:center;justify-content:center;color:#a8a29e;font-size:12px;text-align:center;padding:12px;flex-shrink:0">Sin foto</div>';
    }
    // Galería de imagenes extra (frontal/posterior/lateral) — usa proxy
    var galeriaHtml = '';
    var imgsExtra = (meta.imagenes_extra || []).filter(function(x,i){ return i>0 && x && x.src; });
    if(imgsExtra.length){
      galeriaHtml = '<div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">' +
        imgsExtra.slice(0,6).map(function(im, i){
          var proxyUrl = proxyBase + '?idx=' + (i+1) + '&t=' + Date.now();
          var alt = im.alt || ('Vista '+(im.position||(i+2)));
          return '<img src="'+proxyUrl+'" alt="'+_escHTML(alt)+'" title="'+_escHTML(alt)+'" '+
                 'style="width:54px;height:54px;object-fit:cover;border-radius:6px;border:1px solid #e7e5e4;cursor:pointer" '+
                 'onerror="this.style.opacity=0.3">';
        }).join('') +
        '</div>';
    }
    // Línea de SKU + precio + peso si vino de Shopify
    var bits = [];
    if(meta.sku) bits.push('<b style="color:#6d28d9">SKU:</b> '+_escHTML(meta.sku));
    if(meta.precio>0) bits.push('$'+Math.round(meta.precio).toLocaleString('es-CO'));
    if(meta.peso_g>0) bits.push(Math.round(meta.peso_g)+' g');
    var metaLine = bits.length ? '<div style="font-size:11px;color:#475569;margin-top:6px">'+bits.join(' &middot; ')+'</div>' : '';
    // Descripcion preview
    var descHtml = '';
    if(meta.descripcion){
      var preview = meta.descripcion.substring(0,200) + (meta.descripcion.length>200?'…':'');
      descHtml = '<div style="font-size:11px;color:#78716c;margin-top:6px;font-style:italic;line-height:1.4">'+_escHTML(preview)+'</div>';
    }
    // Link a Shopify storefront
    var shopifyLink = '';
    if(meta.shopify_handle){
      shopifyLink = ' <a href="https://animuslb.com/products/'+_escHTML(meta.shopify_handle)+'" target="_blank" style="font-size:10px;color:#10b981;text-decoration:none;font-weight:600;margin-left:6px">↗ Ver en animuslb.com</a>';
    }

    imgWrap.innerHTML = imgHtml +
      '<div style="flex:1">' +
        '<div style="font-weight:700;font-size:15px;color:#1c1917">'+_escHTML(prodNombre)+shopifyLink+'</div>' +
        '<div style="font-size:11px;color:#78716c;margin-top:2px">'+(prim.cantidad_kg||0).toLocaleString('es-CO')+' kg &middot; '+(prim.fecha_planeada||'-')+'</div>' +
        metaLine +
        descHtml +
        galeriaHtml +
        '<div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">' +
          '<button onclick="ckImagenPegarURL(&quot;'+_escHTML(prodNombre).replace(/"/g,'&quot;')+'&quot;)" style="background:#3b82f6;color:#fff;border:none;border-radius:5px;padding:5px 10px;font-size:11px;font-weight:600;cursor:pointer">📎 Pegar URL</button>' +
          '<button onclick="ckImagenShopify(&quot;'+_escHTML(prodNombre).replace(/"/g,'&quot;')+'&quot;)" style="background:#10b981;color:#fff;border:none;border-radius:5px;padding:5px 10px;font-size:11px;font-weight:600;cursor:pointer" title="Forzar re-sync (el sync auto ya corre solo)">🔄 Re-sync</button>' +
          (d.imagen_url ? '<button onclick="ckImagenLimpiar(&quot;'+_escHTML(prodNombre).replace(/"/g,'&quot;')+'&quot;)" style="background:#fff;color:#dc2626;border:1px solid #dc2626;border-radius:5px;padding:5px 10px;font-size:11px;font-weight:600;cursor:pointer">🗑️ Quitar</button>' : '') +
        '</div>' +
      '</div>';
    var pct = d.porcentaje_listo||0;
    var color = pct>=90?'#15803d':pct>=50?'#f59e0b':'#dc2626';
    document.getElementById('ck-modal-progress').innerHTML =
      '<div style="background:#f5f5f4;border-radius:8px;padding:14px;display:grid;grid-template-columns:repeat(7,1fr);gap:10px;font-size:11px">' +
      '<div><div style="color:#15803d;font-weight:800;font-size:1.4em">'+pct+'%</div><div style="color:#78716c">Listo</div></div>' +
      '<div><div style="font-weight:800;font-size:1.2em">'+(d.totales_por_estado.verificado_ok||0)+'</div><div style="color:#15803d">✅ Verificado</div></div>' +
      '<div><div style="font-weight:800;font-size:1.2em">'+(d.totales_por_estado.recibido||0)+'</div><div style="color:#15803d">📦 Recibido</div></div>' +
      '<div><div style="font-weight:800;font-size:1.2em">'+(d.totales_por_estado.en_transito||0)+'</div><div style="color:#1e40af">🚚 Tránsito</div></div>' +
      '<div><div style="font-weight:800;font-size:1.2em">'+(d.totales_por_estado.solicitado||0)+'</div><div style="color:#a16207">⏳ Solicitado</div></div>' +
      '<div><div style="font-weight:800;font-size:1.2em;color:#dc2626">'+(d.totales_por_estado.pendiente||0)+'</div><div style="color:#dc2626">🔴 Pendiente</div></div>' +
      '<div><div style="font-weight:800;font-size:1.2em">'+(d.totales_por_estado.no_aplica||0)+'</div><div style="color:#78716c">— N/A</div></div>' +
      '</div>';
    var items = d.items || [];
    if(!items.length){ document.getElementById('ck-modal-items').innerHTML='<div style="text-align:center;padding:40px;color:#78716c">Sin items en este checklist</div>'; return; }
    var html = '<table style="width:100%;border-collapse:collapse;font-size:13px">' +
      '<thead><tr style="background:#fafaf9;color:#78716c;font-size:11px;text-transform:uppercase">' +
      '<th style="padding:8px 10px;text-align:left">Item</th>' +
      '<th style="padding:8px 10px;text-align:right">Requerido</th>' +
      '<th style="padding:8px 10px;text-align:left">Estado / Proveedor</th>' +
      '<th style="padding:8px 10px;text-align:right">Acciones</th>' +
      '</tr></thead><tbody>';
    items.forEach(function(it){
      var icon = {mp:'⚗️',envase_primario:'🧴',tapa:'🔘',etiqueta_frontal:'🏷️',etiqueta_posterior:'🏷️',etiqueta_lateral:'🏷️',caja_exterior:'📦',serigrafia:'🎨',tampografia:'🎨',instructivo:'📄'}[it.item_tipo]||'•';
      var stCfg = {pendiente:['🔴 Pendiente','#dc2626'],verificado_ok:['✅ Verificado','#15803d'],solicitado:['⏳ Solicitado','#a16207'],en_transito:['🚚 En tránsito','#1e40af'],recibido:['📦 Recibido','#15803d'],listo:['✓ Listo','#15803d'],no_aplica:['— N/A','#78716c']}[it.estado]||['?','#78716c'];
      var cantTxt = it.cantidad_unidades>0 ? (Math.round(it.cantidad_unidades).toLocaleString('es-CO')+' und') :
                    (it.cantidad_requerida ? (Math.round(it.cantidad_requerida).toLocaleString('es-CO')+' '+(it.unidad||'g')) : '—');
      var refLink = it.solicitud_produccion_id ? '<div style="font-size:10px;color:#a16207;margin-top:2px">📋 SP-'+it.solicitud_produccion_id+'</div>' :
                    (it.solicitud_numero ? '<div style="font-size:10px;color:#a16207;margin-top:2px">'+_escHTML(it.solicitud_numero)+'</div>' :
                    (it.oc_numero ? '<div style="font-size:10px;color:#1e40af;margin-top:2px">'+_escHTML(it.oc_numero)+'</div>' : ''));
      // Tipos editables (con dropdown MEE)
      var ESEDIT = ['envase_primario','envase_secundario','tapa','etiqueta_frontal','etiqueta_posterior','etiqueta_lateral','caja_exterior','instructivo','otro'];
      var esEditable = ESEDIT.indexOf(it.item_tipo) >= 0;
      var yaTieneMee = !!it.mee_codigo_asignado;
      var canSolicitar = (it.estado==='pendiente' && !it.solicitud_produccion_id);
      var canMarcar = ['pendiente','solicitado','en_transito'].indexOf(it.estado)>=0;
      var lblElegir = yaTieneMee ? '✏️ Cambiar' : '✏️ Elegir';
      var bgElegir = yaTieneMee ? '#64748b' : '#3b82f6';
      var acciones = '';
      if(esEditable) acciones += '<button onclick="ckAbrirEditor('+it.id+',&quot;'+it.item_tipo+'&quot;,'+(it.cantidad_unidades||0)+')" style="background:'+bgElegir+';color:#fff;border:none;border-radius:5px;padding:4px 10px;font-size:10px;font-weight:700;cursor:pointer;margin-right:4px">'+lblElegir+'</button>';
      if(canSolicitar) acciones += '<button onclick="ckSolicitarProduccion('+it.id+')" style="background:#a16207;color:#fff;border:none;border-radius:5px;padding:4px 10px;font-size:10px;font-weight:700;cursor:pointer;margin-right:4px" title="Enviar a Catalina (cola de compras)">📋 Solicitar</button>';
      if(canMarcar) acciones += '<button onclick="ckMarcar('+it.id+',&quot;recibido&quot;)" style="background:#15803d;color:#fff;border:none;border-radius:5px;padding:4px 10px;font-size:10px;font-weight:700;cursor:pointer;margin-right:4px">Recibido</button>';
      acciones += '<button onclick="ckMarcar('+it.id+',&quot;no_aplica&quot;)" style="background:#78716c;color:#fff;border:none;border-radius:5px;padding:4px 10px;font-size:10px;font-weight:700;cursor:pointer">N/A</button>';
      var obs = it.observaciones ? '<div style="font-size:10px;color:#78716c;margin-top:3px;font-family:monospace">'+_escHTML(it.observaciones)+'</div>' : '';
      var meeLine = yaTieneMee ? '<div style="font-size:10px;color:#6d28d9;margin-top:2px"><b>MEE:</b> '+_escHTML(it.mee_codigo_asignado)+'</div>' : '';
      var decoLine = it.decoracion_tipo ? '<div style="font-size:10px;color:#7c3aed;margin-top:2px"><b>Decoración:</b> '+_escHTML(it.decoracion_tipo)+'</div>' : '';
      // Hint cuando ya hay MEE elegido pero todavía no se envió a Catalina (caso "solo guardar")
      var hintNoEnviado = (yaTieneMee && it.estado==='pendiente' && !it.solicitud_produccion_id) ?
        '<div style="font-size:10px;color:#a16207;margin-top:2px;font-style:italic">⚠️ Elegido pero no enviado a Catalina — click 📋 Solicitar</div>' : '';
      html += '<tr id="ck-row-'+it.id+'" style="border-bottom:1px solid #f5f5f4">' +
        '<td style="padding:10px"><div style="font-weight:600">'+icon+' '+_escHTML(it.descripcion)+'</div>'+(it.codigo_mp?'<div style="font-size:10px;color:#78716c">cod: '+_escHTML(it.codigo_mp)+'</div>':'')+meeLine+decoLine+obs+hintNoEnviado+'</td>' +
        '<td style="padding:10px;text-align:right;font-family:monospace">'+cantTxt+'</td>' +
        '<td style="padding:10px"><span style="color:'+stCfg[1]+';font-weight:700">'+stCfg[0]+'</span>'+(it.proveedor?'<div style="font-size:10px;color:#78716c">'+_escHTML(it.proveedor)+'</div>':'')+refLink+'</td>' +
        '<td style="padding:10px;text-align:right;white-space:nowrap">'+acciones+'</td>' +
        '</tr>';
    });
    html += '</tbody></table>';
    document.getElementById('ck-modal-items').innerHTML = html;
    // Guardar produccionId actual para refrescar despues de cambiar imagen
    window._ckCurrentProduccionId = produccionId;
    window._ckCurrentProducto = producto;
    // Actualizar botones de navegacion ◀ N/M ▶ segun posicion en la lista
    if(typeof ckActualizarNavegacion === 'function') ckActualizarNavegacion();
  } catch(e){ document.getElementById('ck-modal-items').innerHTML='Error: '+e.message; }
}

// Pegar URL de imagen manualmente (Sebastian la copia desde animuslb.com)
async function ckImagenPegarURL(producto){
  var url = prompt('URL de imagen para "'+producto+'" (ej. https://animuslb.com/cdn/...):', '');
  if(url===null) return;
  url = (url||'').trim();
  if(!url){ alert('URL vacia.'); return; }
  try {
    var r = await fetch('/api/formulas/'+encodeURIComponent(producto)+'/imagen', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({imagen_url: url})
    });
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    if(window._ckCurrentProduccionId) abrirChecklistDetalle(window._ckCurrentProduccionId, window._ckCurrentProducto);
  } catch(e){ alert('Error: '+e.message); }
}

async function ckImagenShopify(producto){
  try {
    var r = await fetch('/api/formulas/'+encodeURIComponent(producto)+'/imagen-shopify-sync', {method:'POST'});
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    _toast('Imagen sincronizada de Shopify', 1);
    if(window._ckCurrentProduccionId) abrirChecklistDetalle(window._ckCurrentProduccionId, window._ckCurrentProducto);
  } catch(e){ alert('Error: '+e.message); }
}

async function ckImagenLimpiar(producto){
  if(!confirm('Quitar imagen del producto "'+producto+'"?')) return;
  try {
    await fetch('/api/formulas/'+encodeURIComponent(producto)+'/imagen', {method:'DELETE'});
    if(window._ckCurrentProduccionId) abrirChecklistDetalle(window._ckCurrentProduccionId, window._ckCurrentProducto);
  } catch(e){ alert('Error: '+e.message); }
}

// Navegacion siguiente/anterior dentro del modal del checklist sin tener
// que cerrar y volver a abrir. Sebastian (29-abr-2026): "falta como una
// flecha para seguir al siguiente producto sin necesidad de salirse".
function ckNavegarProducto(delta){
  var lista = window._ckLista || [];
  if(!lista.length) return;
  var idActual = window._ckCurrentProduccionId;
  var idx = lista.findIndex(function(p){ return p.id === idActual; });
  if(idx < 0) return;
  var nuevoIdx = idx + delta;
  if(nuevoIdx < 0 || nuevoIdx >= lista.length) return;
  var p = lista[nuevoIdx];
  // Cerrar editor inline si esta abierto
  document.querySelectorAll('tr.ck-edit-row').forEach(function(r){ r.remove(); });
  abrirChecklistDetalle(p.id, p.producto_nombre);
}

function ckActualizarNavegacion(){
  var lista = window._ckLista || [];
  var idActual = window._ckCurrentProduccionId;
  var idx = lista.findIndex(function(p){ return p.id === idActual; });
  var prev = document.getElementById('ck-nav-prev');
  var next = document.getElementById('ck-nav-next');
  var pos  = document.getElementById('ck-nav-pos');
  if(!prev || !next || !pos) return;
  if(idx < 0 || !lista.length){
    prev.disabled = next.disabled = true;
    prev.style.opacity = next.style.opacity = '0.3';
    pos.textContent = '';
    return;
  }
  pos.textContent = (idx+1) + ' / ' + lista.length;
  // Anterior
  if(idx === 0){ prev.disabled = true; prev.style.opacity = '0.3'; prev.style.cursor = 'not-allowed'; }
  else { prev.disabled = false; prev.style.opacity = '1'; prev.style.cursor = 'pointer'; }
  // Siguiente
  if(idx === lista.length - 1){ next.disabled = true; next.style.opacity = '0.3'; next.style.cursor = 'not-allowed'; }
  else { next.disabled = false; next.style.opacity = '1'; next.style.cursor = 'pointer'; }
}

// Atajos de teclado: ← → para navegar, Esc para cerrar
document.addEventListener('keydown', function(e){
  var modal = document.getElementById('ck-modal');
  if(!modal || modal.style.display === 'none') return;
  // No interferir si el usuario esta escribiendo en un input/textarea
  var tag = (e.target && e.target.tagName || '').toLowerCase();
  if(tag === 'input' || tag === 'textarea' || tag === 'select') return;
  if(e.key === 'ArrowRight'){ e.preventDefault(); ckNavegarProducto(1); }
  else if(e.key === 'ArrowLeft'){ e.preventDefault(); ckNavegarProducto(-1); }
  else if(e.key === 'Escape'){ modal.style.display = 'none'; }
});

async function ckSolicitar(itemId){
  if(!confirm('Generar solicitud de compra para este item?')) return;
  try {
    var r = await fetch('/api/programacion/checklist/items/'+itemId+'/solicitar', {method:'POST'});
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||'')); return; }
    _toast(d.mensaje||'Solicitud creada', 1);
    // Refrescar sin cerrar el modal
    cargarChecklistResumen();
    if(window._ckCurrentProduccionId) abrirChecklistDetalle(window._ckCurrentProduccionId, window._ckCurrentProducto);
  } catch(e){ alert('Error: '+e.message); }
}

// Editor inline (panel expandible bajo la fila — NO modal sobre modal):
// dropdown MEE + cantidad + decoracion + fecha objetivo + observaciones.
// Al guardar, dispara también solicitud a Catalina (un solo paso).
async function ckAbrirEditor(itemId, itemTipo, cantUnd){
  // Cerrar cualquier editor abierto previamente
  document.querySelectorAll('tr.ck-edit-row').forEach(function(r){ r.remove(); });

  var row = document.getElementById('ck-row-'+itemId);
  if(!row){ alert('No se encontró la fila del item.'); return; }

  // Loader inicial mientras llegan opciones MEE
  var loaderHtml = '<tr id="ck-edit-'+itemId+'" class="ck-edit-row"><td colspan="4" style="padding:0">' +
    '<div style="background:#eff6ff;border-left:4px solid #3b82f6;padding:14px 18px;color:#1e40af;font-size:12px">⏳ Cargando opciones MEE...</div>' +
    '</td></tr>';
  row.insertAdjacentHTML('afterend', loaderHtml);

  // Cargar opciones MEE para este tipo
  var r = await fetch('/api/checklist/mee-options?tipo='+encodeURIComponent(itemTipo));
  var d = await r.json();
  var options = d.options || [];
  window._ckEdOptions = options;
  window._ckEdSelected = null;
  window._ckEdItemId = itemId;
  window._ckEdItemTipo = itemTipo;

  var prim = window._ckCurrentMeta || {};
  var fechaDefault = prim.fecha_planeada || '';
  var soporteDeco = (itemTipo==='envase_primario' || itemTipo==='envase_secundario');

  var deco = soporteDeco ?
    '<label style="font-size:10px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.5px">Decoración</label>' +
    '<select id="ck-ed-deco" style="width:100%;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;margin:4px 0;font-size:12px">' +
      '<option value="">— Sin decoración —</option>' +
      '<option value="etiqueta_adhesiva">Etiqueta adhesiva</option>' +
      '<option value="serigrafia">Serigrafía</option>' +
      '<option value="tampografia">Tampografía</option>' +
    '</select>' : '';

  var editor = '<tr id="ck-edit-'+itemId+'" class="ck-edit-row"><td colspan="4" style="padding:0">' +
    '<div style="background:#eff6ff;border-left:4px solid #3b82f6;padding:14px 18px">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">' +
        '<div style="font-weight:700;color:#1e40af;font-size:13px">✏️ Elegir material · '+itemTipo.replace(/_/g,' ')+'</div>' +
        '<button onclick="ckCerrarEditor('+itemId+')" style="background:transparent;border:1px solid #cbd5e1;border-radius:6px;width:28px;height:28px;cursor:pointer;font-size:14px;color:#475569;font-weight:700">×</button>' +
      '</div>' +
      '<div style="display:grid;grid-template-columns:2fr 1fr 1fr;gap:14px;align-items:start">' +
        // Col 1: buscador + lista MEE
        '<div>' +
          '<label style="font-size:10px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.5px">Material (bodega MEE)</label>' +
          '<input type="text" id="ck-ed-search" placeholder="Buscar..." oninput="ckEditorFiltrar()" style="width:100%;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;margin:4px 0 6px;font-size:12px">' +
          '<div id="ck-ed-list" style="max-height:160px;overflow-y:auto;border:1px solid #e2e8f0;border-radius:6px;background:#fff"></div>' +
        '</div>' +
        // Col 2: cantidad + decoración
        '<div>' +
          '<label style="font-size:10px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.5px">Cantidad (und)</label>' +
          '<input type="number" id="ck-ed-cant" value="'+(cantUnd||0)+'" min="0" step="1" style="width:100%;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;margin:4px 0 10px;font-size:12px">' +
          deco +
        '</div>' +
        // Col 3: fecha objetivo + observaciones
        '<div>' +
          '<label style="font-size:10px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.5px">Fecha objetivo</label>' +
          '<input type="date" id="ck-ed-fecha" value="'+_escHTML(fechaDefault)+'" style="width:100%;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;margin:4px 0 10px;font-size:12px">' +
          '<label style="font-size:10px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.5px">Observaciones</label>' +
          '<textarea id="ck-ed-obs" rows="2" placeholder="Para Catalina (opcional)..." style="width:100%;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;margin:4px 0;font-size:12px;font-family:inherit;resize:vertical"></textarea>' +
        '</div>' +
      '</div>' +
      '<div style="display:flex;justify-content:flex-end;align-items:center;gap:10px;margin-top:12px;padding-top:10px;border-top:1px solid #c7d2fe">' +
        '<a href="javascript:void(0)" onclick="ckGuardarEditor('+itemId+',false)" style="font-size:11px;color:#475569;text-decoration:underline;cursor:pointer">solo guardar</a>' +
        '<button onclick="ckCerrarEditor('+itemId+')" style="background:#fff;border:1px solid #cbd5e1;color:#475569;border-radius:6px;padding:7px 14px;font-size:12px;font-weight:600;cursor:pointer">Cancelar</button>' +
        '<button onclick="ckGuardarEditor('+itemId+',true)" style="background:#16a34a;color:#fff;border:none;border-radius:6px;padding:7px 16px;font-size:12px;font-weight:700;cursor:pointer">💾 Guardar y enviar a Catalina</button>' +
      '</div>' +
    '</div></td></tr>';

  // Reemplazar loader con editor real
  var loader = document.getElementById('ck-edit-'+itemId);
  if(loader) loader.outerHTML = editor;
  ckEditorFiltrar();
}

function ckCerrarEditor(itemId){
  var r = document.getElementById('ck-edit-'+itemId);
  if(r) r.remove();
  window._ckEdSelected = null;
}

function ckEditorFiltrar(){
  var q = (document.getElementById('ck-ed-search').value||'').toLowerCase().trim();
  var opts = window._ckEdOptions || [];
  var filtered = q ? opts.filter(function(o){
    return (o.descripcion||'').toLowerCase().indexOf(q)>=0 ||
           (o.codigo||'').toLowerCase().indexOf(q)>=0;
  }) : opts;
  var list = document.getElementById('ck-ed-list');
  if(!filtered.length){ list.innerHTML = '<div style="padding:14px;color:#a8a29e;text-align:center;font-size:12px">Sin coincidencias</div>'; return; }
  // Render con data-codigo + listeners delegados (sin mouseover/mouseout inline que pisa la selección)
  list.innerHTML = filtered.slice(0, 60).map(function(o){
    var stockColor = o.stock>0 ? '#16a34a' : '#dc2626';
    var sel = (window._ckEdSelected === o.codigo);
    var bg = sel ? '#dbeafe' : '#fff';
    var bd = sel ? '2px solid #3b82f6' : '1px solid #f5f5f4';
    return '<div class="ck-mee-row" data-codigo="'+_escHTML(o.codigo)+'" '+
           'style="padding:8px 12px;cursor:pointer;border-bottom:'+bd+';background:'+bg+'">' +
      '<div style="font-size:13px;font-weight:600;color:#1c1917">'+(sel?'✓ ':'')+_escHTML(o.descripcion)+'</div>' +
      '<div style="font-size:10px;color:#78716c;margin-top:2px"><span style="font-family:monospace">'+_escHTML(o.codigo)+'</span> · stock: <span style="color:'+stockColor+';font-weight:600">'+Math.round(o.stock)+' '+_escHTML(o.unidad||'und')+'</span>'+(o.proveedor?' · '+_escHTML(o.proveedor):'')+'</div>' +
      '</div>';
  }).join('');
  // Adjuntar handlers via JS (no inline) — más robusto contra escapes
  list.querySelectorAll('.ck-mee-row').forEach(function(row){
    row.addEventListener('click', function(){
      ckEdSeleccionar(row.dataset.codigo);
    });
    row.addEventListener('mouseenter', function(){
      if(row.dataset.codigo !== window._ckEdSelected){ row.style.background = '#fafaf9'; }
    });
    row.addEventListener('mouseleave', function(){
      if(row.dataset.codigo !== window._ckEdSelected){ row.style.background = '#fff'; }
    });
  });
}

function ckEdSeleccionar(codigo){
  window._ckEdSelected = codigo;
  // Re-render para que el highlight (✓ + bg azul + border) sobreviva
  ckEditorFiltrar();
  // Auto-fill cantidad si no hay
  var input = document.getElementById('ck-ed-cant');
  if(input && (!input.value || parseFloat(input.value)===0)){
    var prim = (window._ckCurrentMeta||{});
    if(prim.volumen_unitario_ml > 0 && prim.cantidad_kg > 0){
      input.value = Math.ceil((prim.cantidad_kg * 1000) / prim.volumen_unitario_ml);
    }
  }
  // Mostrar el codigo seleccionado en un badge sobre el input de busqueda
  var search = document.getElementById('ck-ed-search');
  if(search){
    search.placeholder = '✓ Seleccionado: ' + codigo + ' (busca otro para cambiar)';
  }
}

// Guarda la elección + (opcional) dispara solicitud a Catalina en una sola acción.
// enviarACompras=true → asignar-mee + solicitar-produccion en cadena.
// enviarACompras=false → solo asignar-mee (preparar sin enviar todavía).
async function ckGuardarEditor(itemId, enviarACompras){
  var codigo = window._ckEdSelected;
  if(!codigo){ alert('Selecciona un material primero.'); return; }
  var cant = parseFloat(document.getElementById('ck-ed-cant').value||0);
  if(!(cant > 0)){ alert('Ingresa una cantidad mayor a 0.'); return; }
  var decoEl = document.getElementById('ck-ed-deco');
  var deco = decoEl ? (decoEl.value||'') : '';
  var fechaEl = document.getElementById('ck-ed-fecha');
  var fecha = fechaEl ? (fechaEl.value||'') : '';
  var obsEl = document.getElementById('ck-ed-obs');
  var obs = obsEl ? (obsEl.value||'').trim() : '';
  try {
    // Paso 1: guardar selección de material (asignar-mee)
    var r1 = await fetch('/api/programacion/checklist/items/'+itemId+'/asignar-mee', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({mee_codigo: codigo, cantidad_unidades: cant, decoracion_tipo: deco})
    });
    var d1 = await r1.json();
    if(!r1.ok){ alert('Error al guardar: '+(d1.error||r1.status)); return; }

    // Paso 2 (opcional): enviar a la cola de Catalina
    if(enviarACompras){
      var r2 = await fetch('/api/programacion/checklist/items/'+itemId+'/solicitar-produccion', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({fecha_objetivo: fecha, observaciones: obs})
      });
      var d2 = await r2.json();
      if(!r2.ok){
        alert('Guardado, pero falló envío a Catalina: '+(d2.error||r2.status));
      } else {
        var msg = d2.ya_existia
          ? 'Ya estaba en cola de Catalina (SP-'+d2.solicitud_id+')'
          : '✓ Enviada a Catalina · SP-'+d2.solicitud_id+' · ver en /compras';
        _toast(msg, 1);
      }
    } else {
      _toast('✓ Selección guardada (no enviada todavía)', 1);
    }

    ckCerrarEditor(itemId);
    if(window._ckCurrentProduccionId) abrirChecklistDetalle(window._ckCurrentProduccionId, window._ckCurrentProducto);
  } catch(e){ alert('Error: '+e.message); }
}

async function ckSolicitarProduccion(itemId){
  if(!confirm('Enviar solicitud a Catalina?')) return;
  try {
    var r = await fetch('/api/programacion/checklist/items/'+itemId+'/solicitar-produccion', {
      method:'POST', headers:{'Content-Type':'application/json'}, body: '{}'
    });
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    _toast(d.mensaje||'Solicitud enviada', 1);
    if(window._ckCurrentProduccionId) abrirChecklistDetalle(window._ckCurrentProduccionId, window._ckCurrentProducto);
  } catch(e){ alert('Error: '+e.message); }
}

async function ckMarcar(itemId, estado){
  try {
    var r = await fetch('/api/programacion/checklist/items/'+itemId, {
      method:'PATCH',headers:{'Content-Type':'application/json'},
      body: JSON.stringify({estado: estado, fecha_recibido: estado==='recibido'? new Date().toISOString().slice(0,10) : null})
    });
    if(!r.ok){ alert('Error'); return; }
    _toast('Item actualizado', 1);
    // Refrescar TODO sin cerrar el modal: el listado de fondo + el detalle abierto
    cargarChecklistResumen();
    if(window._ckCurrentProduccionId) abrirChecklistDetalle(window._ckCurrentProduccionId, window._ckCurrentProducto);
  } catch(e){ alert('Error: '+e.message); }
}
