
  // ── Programar Producción Modal ───────────────────────────────────────────
  // Cache global de areas + operarios (cargado al abrir modal, sirve tambien
  // para vista de listado y futura vista plano interactivo).
  var _PLANTA_AREAS = null;
  var _PLANTA_OPERARIOS = null;

  async function _mpCargarCatalogos(){
    try{
      var r1 = await fetch('/api/planta/areas');
      var d1 = await r1.json();
      _PLANTA_AREAS = d1.areas || [];
    }catch(e){ _PLANTA_AREAS = []; }
    try{
      var r2 = await fetch('/api/planta/operarios');
      var d2 = await r2.json();
      _PLANTA_OPERARIOS = d2.operarios || [];
    }catch(e){ _PLANTA_OPERARIOS = []; }
  }

  function _mpPoblarSelectores(){
    // Sala — etiqueta enriquecida con capacidades para que se vea cual sirve
    var sel = document.getElementById('mp-sala');
    sel.innerHTML = '<option value="">— sin asignar —</option>' +
      (_PLANTA_AREAS||[]).map(function(a){
        var caps = [];
        if(a.puede_producir) caps.push('prod');
        if(a.puede_envasar)  caps.push('env');
        if(a.marmita_ml)     caps.push('marmita ' + a.marmita_ml + 'ml');
        if(a.especial)       caps.push(a.especial);
        return '<option value="'+a.id+'">'+a.nombre+'  ('+caps.join(' · ')+')</option>';
      }).join('');

    // Operarios — armar 4 selects con defaults segun rol_predeterminado.
    // Mayerlin (fija_dispensacion=true) se preselecciona y bloquea el slot.
    var ops = _PLANTA_OPERARIOS || [];
    var faseToOpDefault = {disp:null, elab:null, env:null, acon:null};
    ops.forEach(function(o){
      if (o.es_jefe) return;
      if (o.fija_dispensacion)                faseToOpDefault.disp = o.id;
      else if (o.rol === 'envasado')          faseToOpDefault.env  = o.id;
      else if (o.rol === 'acondicionamiento') faseToOpDefault.acon = o.id;
      else if (o.rol === 'todero' && faseToOpDefault.elab===null) faseToOpDefault.elab = o.id;
    });
    function _opt(o){ return '<option value="'+o.id+'">'+o.nombre_completo+(o.fija_dispensacion?' 🔒':'')+'</option>'; }
    var optsHTML = '<option value="">—</option>' +
      ops.filter(function(o){ return !o.es_jefe; }).map(_opt).join('');
    ['mp-op-disp','mp-op-elab','mp-op-env','mp-op-acon'].forEach(function(id){
      document.getElementById(id).innerHTML = optsHTML;
    });
    // Aplicar defaults
    if(faseToOpDefault.disp) document.getElementById('mp-op-disp').value = faseToOpDefault.disp;
    if(faseToOpDefault.elab) document.getElementById('mp-op-elab').value = faseToOpDefault.elab;
    if(faseToOpDefault.env)  document.getElementById('mp-op-env').value  = faseToOpDefault.env;
    if(faseToOpDefault.acon) document.getElementById('mp-op-acon').value = faseToOpDefault.acon;
  }

  async function mpChequearConflictoSala(){
    var sala_id = document.getElementById('mp-sala').value;
    var fecha   = document.getElementById('mp-fecha').value;
    var warn    = document.getElementById('mp-sala-warn');
    warn.style.display = 'none'; warn.textContent = '';
    if(!sala_id || !fecha) return;
    try{
      var r = await fetch('/api/planta/areas?fecha='+encodeURIComponent(fecha));
      var d = await r.json();
      var sala = (d.areas||[]).find(function(a){ return String(a.id)===String(sala_id); });
      if(sala && sala.ocupada_por && sala.ocupada_por.length){
        var nombres = sala.ocupada_por.map(function(o){ return o.producto; }).join(', ');
        warn.textContent = '⚠️ Esa sala ya tiene producción ese día: ' + nombres + '. Igual puedes asignarla, decides tú.';
        warn.style.display = 'block';
      }
    }catch(e){}
  }

  async function abrirModalProgramar(producto) {
    document.getElementById('mp-producto').value = producto;
    var d = new Date(); d.setDate(d.getDate() + 3);
    document.getElementById('mp-fecha').value = d.toISOString().slice(0,10);
    document.getElementById('mp-lotes').value = 1;
    document.getElementById('mp-obs').value = '';
    cargarEventosProducto(producto);
    var m = document.getElementById('modal-programar');
    m.style.display = 'flex';
    // Cargar catalogos solo la primera vez
    if(_PLANTA_AREAS===null) await _mpCargarCatalogos();
    _mpPoblarSelectores();
    // Cargar semáforo de insumos
    cargarSemaforoInsumos();
    // Listener para re-chequear conflicto cuando cambia fecha
    var fInp = document.getElementById('mp-fecha');
    if(!fInp._planta_listener){
      fInp.addEventListener('change', mpChequearConflictoSala);
      fInp._planta_listener = true;
    }
  }

  async function cargarSemaforoInsumos(){
    var producto = document.getElementById('mp-producto').value;
    var lotes = parseInt(document.getElementById('mp-lotes').value) || 1;
    var box = document.getElementById('mp-semaforo');
    var content = document.getElementById('mp-semaforo-content');
    if(!producto){ box.style.display='none'; return; }
    box.style.display = 'block';
    content.innerHTML = '<div style="color:#94a3b8;text-align:center;padding:8px">⏳ Calculando...</div>';
    try{
      var r = await fetch('/api/planta/listo-producir/'+encodeURIComponent(producto)+'?lotes='+lotes);
      if(!r.ok){
        if(r.status === 404){
          content.innerHTML = '<div style="color:#94a3b8;text-align:center;padding:8px">📋 Sin fórmula registrada para este producto</div>';
        } else {
          content.innerHTML = '<div style="color:#dc2626">Error al consultar insumos</div>';
        }
        return;
      }
      var d = await r.json();
      var resumen = d.resumen || {};
      var headerColor = resumen.deficit > 0 ? '#dc2626' : resumen.justo > 0 ? '#d97706' : '#16a34a';
      var headerLabel = resumen.deficit > 0 ? '❌ Faltan insumos críticos' : resumen.justo > 0 ? '⚠ Stock justo' : '✅ Listo para producir';
      var html = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid #e2e8f0">' +
        '<b style="color:'+headerColor+';font-size:13px">'+headerLabel+'</b>' +
        '<span style="font-size:10px;color:#64748b">'+resumen.ok+' OK · '+resumen.justo+' justo · '+resumen.deficit+' déficit · '+resumen.total+' MPs</span>' +
        '</div>';
      // Mostrar primero deficit, luego justo, luego ok
      var orden = {'deficit':0, 'justo':1, 'ok':2};
      var sorted = (d.items||[]).slice().sort(function(a,b){ return (orden[a.status]||9) - (orden[b.status]||9); });
      // Solo mostrar los problemáticos por defecto
      var problematicos = sorted.filter(function(x){ return x.status !== 'ok'; });
      if(!problematicos.length){
        html += '<div style="color:#16a34a;font-size:12px;text-align:center;padding:6px">Todos los '+resumen.total+' MPs disponibles ✓</div>';
      } else {
        html += problematicos.slice(0,8).map(function(it){
          var icon = it.status==='deficit'?'❌':it.status==='justo'?'⚠':'✓';
          var color = it.status==='deficit'?'#dc2626':it.status==='justo'?'#d97706':'#16a34a';
          var fmt = function(g){ return Math.round(g).toLocaleString('es-CO')+' g'; };
          return '<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:11px">' +
            '<span>'+icon+' <b>'+_escHTML(it.nombre)+'</b></span>' +
            '<span style="color:'+color+';font-family:monospace">'+fmt(it.disponible_g)+' / '+fmt(it.requerido_g)+(it.faltante_g>0?' <b>(falta '+fmt(it.faltante_g)+')</b>':'')+'</span>' +
            '</div>';
        }).join('');
        if(problematicos.length > 8){
          html += '<div style="text-align:center;font-size:10px;color:#94a3b8;margin-top:4px">+ '+(problematicos.length-8)+' más</div>';
        }
      }
      content.innerHTML = html;
    }catch(e){
      content.innerHTML = '<div style="color:#dc2626">Error de red</div>';
    }
  }
  function cerrarModalProgramar() {
    document.getElementById('modal-programar').style.display = 'none';
  }
  function actualizarDashboard() {
    cargarProgramacion(null);
  }

  // -- Pestana Abastecimiento (sistema VIVO en cargarAbastecimiento ~L20xxx)
  // setAbastFoco resalta el horizonte foco y dispara la recarga.
  // Sebastián 24-may-2026 noche · selector 7 opciones · 15/30/60/90/120/180/365
  window.setAbastFoco = function(dias){
    window.ABAST_HORIZ = dias;
    // FIX 10-jun · el horizonte de FOCO es la decisión: "Cubrir" (cantidad a pedir)
    // se sincroniza con él → si decido 90 días, "Pedir" jala EXACTO el déficit a 90d.
    // (el usuario igual puede cambiar "Cubrir" a mano después.)
    try { if (window._ABA_STATE) window._ABA_STATE.cubrir_dias = dias; } catch(e){}
    document.querySelectorAll('.abast-htab').forEach(function(b){
      var active = parseInt(b.dataset.h) === dias;
      b.style.background = active ? '#7c3aed' : '#fff';
      b.style.color = active ? '#fff' : '#475569';
      b.style.borderColor = active ? '#7c3aed' : '#cbd5e1';
    });
    var hint = document.getElementById('abast-foco-hint');
    if (hint) {
      var lbl = (dias >= 365) ? '1 año' : (dias >= 30 ? Math.round(dias/30) + ' meses' : dias + ' días');
      hint.textContent = '· ' + lbl;
    }
    if (typeof cargarAbastecimiento === 'function') cargarAbastecimiento();
  };

  // Inyecta el déficit por horizonte DENTRO de cada botón de horizonte (compactado
  // 2-jun-2026 · elimina la caja duplicada "déficit por horizonte"). setAbastFoco
  // solo cambia colores, no innerHTML, así que el conteo persiste al resaltar.
  window._abastPintarHorizontes = function(d){
    try {
      (d.horizontes || []).forEach(function(h){
        var btn = document.querySelector('.abast-htab[data-h="' + h + '"]');
        if (!btn) return;
        var r2 = (d.resumen_por_horizonte || {})[String(h)] || {};
        var n = r2.n_total_con_deficit || 0;
        var base = (h >= 365) ? '365d' : (h + 'd');
        btn.innerHTML = base + ' <span style="opacity:.6;font-weight:800">·' + n + '</span>';
      });
    } catch(_) {}
  };

  // ── Sub-tabs internos de Programacion ────────────────────────────────────
  // Sprint Programación 20-may-2026 · Opción A · 4 grupos visuales.
  // Mapeo tab→grupo · cuando switchProgTab cambia de tab, también
  // actualizamos el grupo activo + el sub-tab seleccionado.
  var _PROG_TAB_TO_GROUP = {
    'necesidades': 'plan',
    'planv2': 'plan',  // legacy oculto · si llaman, queda en grupo plan
    // Sebastián 24-may-2026 noche: Abastecimiento movido al grupo
    // Calendario IA · lee el calendario, no es planeación independiente.
    'abastecimiento': 'calendario_grp',
    'calendario': 'calendario_grp',
    'factibilidad': 'calendario_grp',
    'serigrafia': 'calendario_grp',
    'mando': 'opera_grp',
    'kanban': 'opera_grp',
    'midia': 'opera_grp',
  };
  function switchProgGroup(group){
    try {
      // Activar/desactivar botones grupo
      var btns = document.querySelectorAll('[data-prog-grp]');
      btns.forEach(function(b){
        var isActive = b.getAttribute('data-prog-grp') === group;
        b.style.opacity = isActive ? '1' : '0.6';
      });
      // Mostrar sub-bar correcta
      ['plan','calendario_grp','opera_grp'].forEach(function(g){
        var sb = document.getElementById('prog-sub-'+g);
        if(sb) sb.style.display = (g===group) ? 'flex' : 'none';
      });
      // Default sub-tab por grupo
      var DEF = {plan:'necesidades', calendario_grp:'calendario', opera_grp:'mando'};
      if(DEF[group]) switchProgTab(DEF[group]);
    } catch(err) { console.warn('switchProgGroup:', err); }
  }
  function _highlightProgSubTab(tab){
    // Resalta el sub-tab activo dentro de su grupo (fill vs outline)
    var group = _PROG_TAB_TO_GROUP[tab];
    if(!group) return;
    var COLORS = {
      'necesidades': '#6d28d9', 'abastecimiento': '#7c3aed',
      'calendario': '#ca8a04', 'factibilidad': '#059669',
      'mando': '#1a4a7a', 'kanban': '#7c3aed', 'midia': '#1e40af',
    };
    var SUB_TAB_FROM = {
      'necesidades': "switchProgTab('necesidades')",
      'abastecimiento': "switchProgTab('abastecimiento')",
      'calendario': "switchProgTab('calendario')",
      'factibilidad': "switchProgTab('factibilidad')",
      'mando': "switchProgTab('mando')",
      'kanban': "switchProgTab('kanban')",
      'midia': "switchProgTab('midia')",
    };
    var sb = document.getElementById('prog-sub-'+group);
    if(!sb) return;
    sb.querySelectorAll('button[data-prog-sub]').forEach(function(b){
      var onc = b.getAttribute('onclick') || '';
      var matchTab = null;
      Object.keys(SUB_TAB_FROM).forEach(function(t){
        if(onc.indexOf(SUB_TAB_FROM[t]) !== -1) matchTab = t;
      });
      if(matchTab && matchTab === tab){
        b.style.background = COLORS[matchTab] || '#475569';
        b.style.color = '#fff';
      } else if(matchTab){
        b.style.background = '#fff';
        b.style.color = COLORS[matchTab] || '#475569';
      }
    });
  }
  async function cargarSerigrafiaCola(){
    var box=document.getElementById('serig-cola-body'); if(!box) return;
    box.innerHTML='Cargando&hellip;';
    try{
      var d=await (await fetch('/api/programacion/marcacion-ordenes',{cache:'no-store'})).json();
      var its=((d&&d.items)||[]).filter(function(o){return o.estado==='enviado';});
      if(!its.length){ box.innerHTML='<div style="padding:24px;color:#94a3b8;text-align:center">Sin envases solicitados por Compras todav&iacute;a.<br><span style="font-size:11px">Cuando Compras env&iacute;e envases a marcar, aparecen ac&aacute; para alistar.</span></div>'; return; }
      its.sort(function(a,b){ return (a.fecha_alistar||'9999')<(b.fecha_alistar||'9999')?-1:1; });
      var U={vencido:['&#128308;','#dc2626'],critica:['&#128308;','#dc2626'],urgente:['&#128992;','#ea580c'],alta:['&#128992;','#ea580c'],proximo:['&#128993;','#ca8a04'],media:['&#128993;','#ca8a04'],normal:['&#128994;','#16a34a'],ok:['&#128994;','#16a34a']};
      var h='<table style="width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden"><thead><tr style="background:#f1f5f9;font-size:11px;text-transform:uppercase"><th style="text-align:left;padding:7px 9px">Alistar antes de</th><th style="text-align:left;padding:7px 9px">Producci&oacute;n</th><th style="text-align:left;padding:7px 9px">Envase a alistar</th><th style="padding:7px 9px">Cantidad</th><th style="text-align:left;padding:7px 9px">M&eacute;todo</th><th style="text-align:left;padding:7px 9px">Proveedor</th></tr></thead><tbody>';
      its.forEach(function(o){
        var u=U[o.urgencia||'media']||U.media;
        var hr=(o.hora_alistar||'10:00');
        var dr=(o.dias_restantes!=null)?('<br><span style="font-size:10px;color:'+u[1]+'">'+(o.dias_restantes<0?('hace '+(-o.dias_restantes)+'d'):(o.dias_restantes===0?'HOY':('en '+o.dias_restantes+'d')))+' &middot; antes '+hr+'</span>'):('<br><span style="font-size:10px;color:'+u[1]+'">antes '+hr+'</span>');
        h+='<tr style="border-bottom:1px solid #f1f5f9;font-size:12px"><td style="padding:7px 9px;white-space:nowrap"><b style="color:'+u[1]+'">'+u[0]+' '+_escHTML(o.fecha_alistar||o.fecha_envio||'')+'</b>'+dr+'</td><td style="padding:7px 9px"><b>'+_escHTML(o.producto||'')+'</b></td><td style="padding:7px 9px">'+_escHTML(o.base||o.serigrafiado||'')+'</td><td style="padding:7px 9px;text-align:center;font-weight:700;color:#5b21b6">'+(Math.round(o.cantidad_enviada||0).toLocaleString('es-CO'))+'</td><td style="padding:7px 9px">'+_escHTML(o.metodo||'')+'</td><td style="padding:7px 9px">'+_escHTML(o.proveedor||'')+'</td></tr>';
      });
      h+='</tbody></table>';
      box.innerHTML=h;
    }catch(e){ box.innerHTML='<div style="color:#dc2626;padding:20px">Error: '+e+'</div>'; }
  }

  function switchProgTab(tab){
    try {
      // Auto-sincronizar grupo + sub-tab activo (Opción A 20-may-2026)
      var grp = _PROG_TAB_TO_GROUP[tab];
      if(grp){
        ['plan','calendario_grp','opera_grp'].forEach(function(g){
          var sb = document.getElementById('prog-sub-'+g);
          if(sb) sb.style.display = (g===grp) ? 'flex' : 'none';
        });
        document.querySelectorAll('[data-prog-grp]').forEach(function(b){
          b.style.opacity = (b.getAttribute('data-prog-grp')===grp) ? '1' : '0.6';
        });
        _highlightProgSubTab(tab);
      }
      // Mapeo tab → ID del div objetivo
      var TAB_TO_DIV = {
        'planv2': 'ptab-planv2',
        'midia':  'ptab-midia',
        'calendario': 'ptab-calendario',
        'kanban': 'ptab-kanban',
        'necesidades': 'ptab-necesidades',
        'abastecimiento': 'ptab-abastecimiento',
        'factibilidad': 'ptab-factibilidad',
        'serigrafia': 'ptab-serigrafia',
        // 'asignacion' eliminado · redirige a 'mando' (unificado en mapa)
        'asignacion': 'ptab-plano',
        'mando': 'ptab-plano',
        'autoplan': 'ptab-autoplan',
        'config': 'ptab-config',
        'maquila': 'ptab-maquila',
        // Compat con flujos viejos
        'presentaciones': 'ptab-presentaciones',
        'equipos': 'ptab-equipos',
        'preflight': 'ptab-preflight',
        'plansem': 'ptab-plansem',
        'conteo': 'ptab-conteo',
        'centro': 'ptab-centro',
        'plan': 'ptab-plan',
        'checklist': 'ptab-checklist',
        'tareas': 'ptab-tareas',
        'plano': 'ptab-plano',
      };
      // Lazy-load Abastecimiento al activar tab · Sebastián 23-may-2026
      // FIX 24-may noche · NO HACER return aquí · corta la función antes
      // de toggle de visibilidad de divs y el tab no se ve cambiado.
      if (tab === 'abastecimiento') {
        try {
          // Marcar foco visual del horizonte activo (default 90d).
          // setAbastFoco también dispara cargarAbastecimiento internamente.
          if (typeof setAbastFoco === 'function') {
            setAbastFoco(window.ABAST_HORIZ || 90);
          } else if (typeof cargarAbastecimiento === 'function') {
            var ac = document.getElementById('abast-contenido');
            if (ac && ac.textContent.indexOf('Click') >= 0) {
              cargarAbastecimiento();
            }
          }
        } catch(e) { console.warn('lazy load abast:', e); }
      }
      // Lazy-load iframe Mi Día solo al activar tab (evita carga al boot).
      // Sebastián 19-may-2026: si ya estaba cargado, refrescar el contenido
      // sin recargar el iframe entero (mantiene navegación · solo refetch data).
      if (tab === 'midia') {
        var fr = document.getElementById('midia-frame');
        if (fr) {
          if (!fr.src || fr.src === 'about:blank') {
            fr.src = '/operario';
          } else {
            try {
              if (fr.contentWindow && typeof fr.contentWindow.loadMiDia === 'function') {
                fr.contentWindow.loadMiDia();
              }
            } catch(e) { console.warn('refresh midia falló:', e); }
          }
        }
      }
      // Lazy-load iframe Calendario IA al activar tab · Sebastián 14-may-2026:
      // "deberia quedarse alli como sub pestaña".
      // Sebastián 19-may-2026: fix · el iframe NO se recargaba al volver a la
      // pestaña, quedaba con datos stale (causó la falsa alarma "desaparecio
      // del calendario la programacion de esta semana" cuando en realidad las
      // producciones existían en BD pero el iframe nunca refetcheó).
      if (tab === 'calendario') {
        var frCal = document.getElementById('calendario-iframe');
        if (frCal) {
          if (!frCal.src || frCal.src === 'about:blank' || !frCal.src.includes('plan-calendario')) {
            frCal.src = '/admin/plan-calendario';
          } else {
            try {
              if (frCal.contentWindow && typeof frCal.contentWindow.cargar === 'function') {
                frCal.contentWindow.cargar();
              }
            } catch(e) { console.warn('refresh calendario falló:', e); }
          }
        }
      }
      // Lazy-load iframe Kanban de Planta · pieza 2 · Sebastián 19-may-2026.
      // Mismo patrón anti-stale: si ya estaba cargado, llamar contentWindow.cargar()
      if (tab === 'kanban') {
        var frKb = document.getElementById('kanban-iframe');
        if (frKb) {
          if (!frKb.src || frKb.src === 'about:blank' || !frKb.src.includes('/planta/kanban')) {
            frKb.src = '/planta/kanban';
          } else {
            try {
              if (frKb.contentWindow && typeof frKb.contentWindow.cargar === 'function') {
                frKb.contentWindow.cargar();
              }
            } catch(e) { console.warn('refresh kanban falló:', e); }
          }
        }
      }
      // Lazy-load iframe Factibilidad del Plan al activar la pestaña.
      // Sebastián 19-may-2026: mismo patrón anti-stale que calendario.
      if (tab === 'factibilidad') {
        var frFact = document.getElementById('factibilidad-iframe');
        if (frFact) {
          if (!frFact.src || frFact.src === 'about:blank' || !frFact.src.includes('factibilidad-plan')) {
            frFact.src = '/admin/factibilidad-plan';
          } else {
            try {
              if (frFact.contentWindow && typeof frFact.contentWindow.cargar === 'function') {
                frFact.contentWindow.cargar();
              }
            } catch(e) { console.warn('refresh factibilidad falló:', e); }
          }
        }
      }
      // Lazy-load Necesidades al activar tab
      if (tab === 'necesidades') {
        if (typeof cargarNecesidades === 'function') cargarNecesidades();
      }
      // (Abastecimiento ya se carga arriba vía setAbastFoco · PERF 9-jul: se quitó el
      //  segundo cargarAbastecimiento() que disparaba el endpoint más pesado 2× · workflow speed-audit #3)
      // Lazy-load Plan en curso al activar tab
      if (tab === 'planv2') {
        if (typeof cargarPlanEnCurso === 'function') cargarPlanEnCurso();
      }
      // Ocultar TODOS los ptab-* dentro de #programacion
      var prog = document.getElementById('programacion');
      if(prog){
        var todos = prog.querySelectorAll('[id^="ptab-"]');
        todos.forEach(function(div){ div.style.display = 'none'; });
      }
      // Mostrar el div objetivo
      var targetId = TAB_TO_DIV[tab];
      if(targetId){
        var elT = document.getElementById(targetId);
        if(elT){
          elT.style.display = 'block';
        } else {
          console.warn('switchProgTab: div '+targetId+' no encontrado');
        }
      }
      // Hooks específicos por tab — cada uno se invoca solo si la función existe
      if(tab==='maquila' && typeof maquilaInit==='function') maquilaInit();
      if(tab==='checklist' && typeof cargarChecklistResumen==='function'){
        cargarChecklistResumen();
        var sel = document.getElementById('ck-autorefresh');
        if(sel && typeof ckSetAutoRefresh==='function') ckSetAutoRefresh(sel.value);
      } else if(typeof ckSetAutoRefresh==='function'){ ckSetAutoRefresh(0); }
      if(tab==='tareas' && typeof cargarTareasOperativas==='function') cargarTareasOperativas();
      if(tab==='plano' || tab==='mando'){
        if(typeof renderCentroMando==='function') renderCentroMando();
        if(typeof cmStartAutoRefresh==='function') cmStartAutoRefresh();
      } else if(typeof cmStopAutoRefresh==='function'){ cmStopAutoRefresh(); }
      if(tab==='presentaciones' && typeof cargarPresentaciones==='function') cargarPresentaciones();
      if(tab==='equipos' && typeof cargarEquipos==='function') cargarEquipos();
      if(tab==='preflight' && typeof cargarPreflightLista==='function') cargarPreflightLista();
      if(tab==='plansem' && typeof cargarPlanSemanal==='function') cargarPlanSemanal();
      if(tab==='autoplan' && typeof apInit==='function') apInit();
      if(tab==='conteo' && typeof cargarConteoCalendario==='function') cargarConteoCalendario();
      if(tab==='plan' && typeof cargarPlanificacion==='function' && !window._planLoaded){
        cargarPlanificacion(60);
      }
      if(tab==='plan' && typeof autoscRecargar==='function') autoscRecargar();
      if(tab==='plan' && typeof autoscMeeRecargar==='function') autoscMeeRecargar();
      if(tab==='plan' && typeof alertEtiquetasRecargar==='function') alertEtiquetasRecargar();
      if(tab==='plan' && typeof alertD20Recargar==='function') alertD20Recargar();
      // Estilos botones — los 6 oficiales
      function _bg(id, activeStyle, activeClass){
        var b = document.getElementById(id);
        if(!b) return;
        if(activeClass){ b.style.background = activeStyle; b.style.color='#fff'; b.style.boxShadow='0 3px 10px rgba(0,0,0,.2)'; }
        else { b.style.background='#e2e8f0'; b.style.color='#1a4a7a'; b.style.boxShadow=''; }
      }
      _bg('prog-tab-planv2',     'linear-gradient(135deg,#6d28d9,#7c3aed)', tab==='planv2');
      _bg('prog-tab-necesidades','linear-gradient(135deg,#6d28d9,#7c3aed)', tab==='necesidades');
      _bg('prog-tab-calendario', 'linear-gradient(135deg,#ca8a04,#f59e0b)', tab==='calendario');
      _bg('prog-tab-midia',      '#1e40af',                                  tab==='midia');
      _bg('prog-tab-abastecimiento', '#7c3aed',                              tab==='abastecimiento');
      _bg('prog-tab-mando',      '#1a4a7a',                                  tab==='mando');
      _bg('prog-tab-autoplan',   'linear-gradient(135deg,#7c3aed,#dc2626)',  tab==='autoplan');
      _bg('prog-tab-maquila',    'linear-gradient(135deg,#1a4a7a,#7c3aed)', tab==='maquila');
      _bg('prog-tab-config',     '#1f2937',                                  tab==='config');
      // === Hooks de inicialización ===
      if(tab==='planv2' && typeof planV2Init==='function') planV2Init();
      if(tab==='config' && typeof cfgInit==='function') cfgInit();
      // Sebastián 1-may-2026: tab Asignación ELIMINADO · paneles operativos
      // ahora viven dentro de Operación Live (mando) junto con el mapa
      if(tab==='mando'){
        if(typeof miDiaCargarOperarios === 'function') miDiaCargarOperarios();
        if(typeof preProduccionRecargar === 'function') preProduccionRecargar();
      }
      if(tab==='config'){
        if(typeof healthRecargar === 'function') healthRecargar();
        if(typeof reporteEjecutivoRecargar === 'function') reporteEjecutivoRecargar();
        if(typeof cronStatusRecargar === 'function') cronStatusRecargar();
      }
    } catch(err) {
      _toast('Error en switchProgTab: ' + err.message, 0);
    }
  }

  // ── Centro de Mando (Capa 3+ live tracking) ─────────────────────────────
  // Cache global del ultimo payload, sirve para el panel detalle al hacer click
  var _CM_LAST = null;
  var _CM_TIMER = null;

  function cmStartAutoRefresh(){
    if(_CM_TIMER) return;
    var chk = document.getElementById('cm-auto');
    if(!chk || !chk.checked) return;
    _CM_TIMER = setInterval(function(){
      if(document.getElementById('ptab-plano').style.display === 'none'){
        cmStopAutoRefresh(); return;
      }
      // BUG-19 fix · 19-may-2026 audit Planta PERFECTA: si la pestaña del
      // navegador está en background (visibilityState='hidden'), saltar el
      // refresh. Evita 11,520 fetches/día por usuario que dejó la pestaña
      // abierta en background sin necesitar datos frescos.
      if(typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
      var c = document.getElementById('cm-auto');
      if(c && c.checked) renderCentroMando(true /*silent*/);
    }, 30000);
  }
  function cmStopAutoRefresh(){
    if(_CM_TIMER){ clearInterval(_CM_TIMER); _CM_TIMER = null; }
  }
  // BUG-19 fix · escuchar visibilitychange para refrescar al volver a la
  // pestaña (datos pueden estar stale tras minutos en background).
  if(typeof document !== 'undefined' && !window._CM_VIS_LISTENER){
    window._CM_VIS_LISTENER = true;
    document.addEventListener('visibilitychange', function(){
      if(document.visibilityState !== 'visible') return;
      var ptab = document.getElementById('ptab-plano');
      if(ptab && ptab.style.display !== 'none' && typeof renderCentroMando === 'function'){
        renderCentroMando(true /*silent*/);
      }
    });
  }

  function _fmtMin(min){
    if(min == null) return '';
    if(min < 60) return min + ' min';
    var h = Math.floor(min/60), m = min%60;
    return h + 'h' + (m?(' '+m+'min'):'');
  }

  async function renderCentroMando(silent){
    var fechaInp = document.getElementById('plano-fecha');
    if(!fechaInp.value){ fechaInp.value = new Date().toISOString().slice(0,10); }
    try{
      var r = await fetch('/api/planta/centro-mando?fecha='+encodeURIComponent(fechaInp.value));
      var d = await r.json();
      _CM_LAST = d;
      // Pintar KPIs
      var kpiBox = document.getElementById('cm-kpis');
      var k = d.kpis || {};
      kpiBox.innerHTML = [
        _kpiCard('🟡 Producciones AHORA', k.producciones_activas_ahora||0, k.producciones_activas_ahora>0?'#ca8a04':'#94a3b8'),
        _kpiCard('✅ Terminadas hoy',     k.terminadas_hoy||0,             '#16a34a'),
        _kpiCard('⏱ Cycle time prom',     k.cycle_time_promedio_min!=null?_fmtMin(k.cycle_time_promedio_min):'—', '#6d28d9'),
        _kpiCard('🟢 Salas libres',       k.salas_libres||0,               '#16a34a'),
        _kpiCard('🔴 Salas sucias',       k.salas_sucias||0,               k.salas_sucias>0?'#b91c1c':'#94a3b8'),
        _kpiCard('🟡 Salas ocupadas',     k.salas_ocupadas||0,             '#ca8a04'),
      ].join('');
      // Mapa codigo → area
      var mapa = {};
      (d.areas||[]).forEach(function(a){ mapa[a.codigo] = a; });
      // Pintar cada rect
      var ESTADO_COLORS = {
        libre:      {fill:'#86efac', stroke:'#16a34a', txt:'#16a34a'},
        ocupada:    {fill:'#fde68a', stroke:'#ca8a04', txt:'#92400e'},
        sucia:      {fill:'#fca5a5', stroke:'#b91c1c', txt:'#991b1b'},
        limpiando:  {fill:'#93c5fd', stroke:'#1d4ed8', txt:'#1e3a8a'}
      };
      // CM-FIX #8 · 20-may-2026: incluir QC, DISP, PIP (estaban en SVG
      // con data-codigo pero nunca recibían estado dinámico).
      ['PROD1','PROD2','PROD3','PROD4','ENV1','ACOND','ALMP','ALMPT','QC','DISP','PIP'].forEach(function(cod){
        var g = document.querySelector('[data-codigo="'+cod+'"]');
        if(!g) return;
        var rect = g.querySelector('rect.r');
        var lbl  = g.querySelector('text.status');
        var a    = mapa[cod];
        if(!a) return;
        var estadoVisual = a.estado;
        // si tiene producciones en curso → ocupada
        var enCurso = (a.ocupada_por||[]).filter(function(o){ return o.en_curso; });
        if(enCurso.length) estadoVisual = 'ocupada';
        var col = ESTADO_COLORS[estadoVisual] || ESTADO_COLORS.libre;
        if(rect){
          rect.setAttribute('fill', col.fill);
          rect.setAttribute('stroke', col.stroke);
        }
        if(lbl){
          // Texto contextual según estado (Sebastián 1-may-2026:
          // 'fabricando GEL HIDRATANTE · sucia por fabricar tal · limpiada')
          var txt = '';
          if(enCurso.length){
            // OCUPADA: producto + operario + tiempo corrido
            var o = enCurso[0];
            var quien = o.operario_elaboracion || o.operario_envasado || o.operario_dispensacion || o.operario_acondicionamiento || '';
            txt = '🏭 ' + o.producto.substring(0,18);
            if(o.minutos_corridos != null) txt += ' · ⏱'+_fmtMin(o.minutos_corridos);
            if(quien) txt += ' · '+quien.split(' ')[0];
          } else if(estadoVisual === 'sucia'){
            // SUCIA: 'Sucia · era X'
            txt = '🔴 SUCIA';
            if(a.ultima_produccion && a.ultima_produccion.producto){
              txt += ' · era ' + a.ultima_produccion.producto.substring(0,15);
            }
          } else if(estadoVisual === 'limpiando'){
            txt = '🧹 LIMPIANDO';
          } else if(estadoVisual === 'libre'){
            txt = 'LIBRE';
          } else {
            txt = estadoVisual.toUpperCase();
          }
          lbl.textContent = txt;
          lbl.setAttribute('fill', col.txt);
        }
      });
      // Click handler
      document.querySelectorAll('[data-codigo]').forEach(function(g){
        var cod = g.getAttribute('data-codigo');
        if(!mapa[cod]) return;
        g.onclick = function(){ mostrarDetalleSala(mapa[cod]); };
      });
      // Eventos recientes (timeline lateral)
      cargarTimelineEventos(d.eventos_recientes || []);
      // PERF 9-jul (speed-audit #8): en el refresh silencioso de 30s NO re-fetcheamos datos
      // casi-estáticos (rotación 14d, tabla de operarios) · se cargan al abrir/refrescar explícito.
      // El plano, cards de HOY, equipo de HOY y andon (live) SÍ se refrescan siempre.
      if(!silent){ cargarRotacionOperarios(); cargarTablaOperarios(); }
      // cargarKpisActividades() ELIMINADO 1-may-2026 · panel turnos era legacy
      // ── Producciones HOY · cards encima del mapa (Sebastián 1-may-2026)
      renderProduccionesDiaCards(d.producciones_dia || [], k);
      renderProduccionesDiag(d.producciones_diag || {});
      if(typeof cmCargarEquipo === 'function') cmCargarEquipo();
      // OLA 2 · Andon panel
      if(typeof cmCargarAndon === 'function') cmCargarAndon();
      // OLA 3 · OEE por sala (7d · casi-estático → no en el refresh silencioso de 30s · speed-audit #8)
      if(!silent && typeof cmCargarOee === 'function') cmCargarOee();
      var lu = document.getElementById('cm-last-update');
      if(lu) lu.textContent = 'actualizado ' + new Date().toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
    }catch(e){
      if(!silent){ _toast('Error al cargar Centro de Mando: '+e.message, 0); }
    }
  }

  // ── Re-asignar HOY (Operación Live · pieza 5) — botón admin ──────────────
  async function cmReasignarHoy(){
    if(!confirm('🤖 ¿Re-correr auto-asignación para HOY?\n\nSolo afecta producciones SUGERIDAS (canónicas / calendar / manual). Lo FIJO (lo que arrastraste/editaste) no se toca.')) return;
    try{
      // BUG-17 fix · 19-may-2026: token CSRF desde endpoint, no cookie
      // (la cookie nunca tenía el token · vive en session Flask).
      let csrf = window._csrfTok || '';
      if(!csrf){
        try {
          const tr = await fetch('/api/csrf-token', {credentials:'same-origin'});
          if(tr.ok){ const td = await tr.json(); csrf = td.csrf_token || ''; window._csrfTok = csrf; }
        } catch(_e){}
      }
      const r = await fetch('/api/planta/auto-asignar-hoy', {
        method:'POST',
        headers:{'Content-Type':'application/json','X-CSRF-Token': csrf},
        credentials:'same-origin',
        body:'{}'
      });
      const d = await r.json();
      if(!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
      alert('✓ Auto-asignación HOY\n· ' + (d.asignadas||0) + ' de ' + (d.total||0) + ' producciones procesadas\n· ' + ((d.fallidas||[]).length) + ' fallaron');
      if(typeof cmCargarEquipo === 'function') cmCargarEquipo();
      if(typeof renderCentroMando === 'function') renderCentroMando();
    }catch(e){
      alert('Error: ' + (e.message || e));
    }
  }

  // ── Equipo HOY · tablero de operarios (paso 2 · Sebastián 19-may-2026) ──
  function _cmEstadoArea(est){
    var M = {
      libre:     {dot:'#16a34a', txt:'Limpia / libre'},
      ocupada:   {dot:'#ca8a04', txt:'Ocupada'},
      sucia:     {dot:'#b91c1c', txt:'Sucia'},
      limpiando: {dot:'#1d4ed8', txt:'Limpiando'}
    };
    return M[est] || M.libre;
  }
  // Paso 3 · click un operario → resalta su área en el plano SVG
  function cmResaltarArea(cod){
    var svg = document.getElementById('plano-svg');
    if(!svg || !cod) return;
    var g = svg.querySelector('[data-codigo="'+cod+'"]');
    var rect = g ? (g.querySelector('rect.r') || g.querySelector('rect')) : null;
    if(!rect) return;
    var NS = 'http://www.w3.org/2000/svg';
    var hi = document.getElementById('cm-area-highlight');
    if(!hi){
      hi = document.createElementNS(NS, 'rect');
      hi.setAttribute('id', 'cm-area-highlight');
      hi.setAttribute('fill', 'none');
      hi.setAttribute('stroke', '#f59e0b');
      hi.setAttribute('stroke-width', '6');
      hi.setAttribute('rx', '6');
      hi.setAttribute('pointer-events', 'none');
      var an = document.createElementNS(NS, 'animate');
      an.setAttribute('attributeName', 'stroke-opacity');
      an.setAttribute('values', '1;0.2;1');
      an.setAttribute('dur', '1.1s');
      an.setAttribute('repeatCount', 'indefinite');
      hi.appendChild(an);
      svg.appendChild(hi);
    }
    var x = parseFloat(rect.getAttribute('x')) || 0;
    var y = parseFloat(rect.getAttribute('y')) || 0;
    var w = parseFloat(rect.getAttribute('width')) || 0;
    var h = parseFloat(rect.getAttribute('height')) || 0;
    hi.setAttribute('x', x - 4);
    hi.setAttribute('y', y - 4);
    hi.setAttribute('width', w + 8);
    hi.setAttribute('height', h + 8);
    hi.style.display = '';
    if(svg.scrollIntoView) svg.scrollIntoView({behavior:'smooth', block:'center'});
  }
  // OLA 3 · OEE por sala
  async function cmCargarOee(){
    var cont = document.getElementById('cm-oee-cards');
    if(!cont) return;
    try{
      var r = await fetch('/api/planta/oee?dias=7');
      if(!r.ok) return;
      var d = await r.json();
      cont.innerHTML = (d.items||[]).map(function(s){
        var pct = s.oee_pct;
        var col = s.color==='verde'?'#16a34a':s.color==='amarillo'?'#ca8a04':s.color==='rojo'?'#dc2626':'#94a3b8';
        var pctTxt = pct==null ? '—' : pct.toFixed(0)+'%';
        var det = pct==null ? 'sin lotes' : ('D '+s.disp_pct+'% · R '+s.rend_pct+'% · C '+s.calidad_pct+'%');
        return '<div style="background:#fff;border:2px solid '+col+';border-radius:8px;padding:6px 10px;min-width:120px" title="OEE 7d · '+s.n_lotes+' lotes">'+
          '<div style="font-size:10px;color:#475569;text-transform:uppercase;font-weight:700">'+_escHTML(s.sala_codigo)+' · OEE</div>'+
          '<div style="font-size:1.4em;font-weight:800;color:'+col+'">'+pctTxt+'</div>'+
          '<div style="font-size:9px;color:#64748b">'+det+'</div>'+
        '</div>';
      }).join('');
    }catch(e){}
  }

  // OLA 2 · Andon · operario reporta problemas en vivo
  async function cmCargarAndon(){
    var panel = document.getElementById('cm-andon-panel');
    var sub = document.getElementById('cm-andon-sub');
    var cards = document.getElementById('cm-andon-cards');
    if(!panel || !cards) return;
    try{
      var r = await fetch('/api/planta/andon');
      if(!r.ok){ panel.style.display='none'; return; }
      var d = await r.json();
      var items = d.alertas || [];
      if(!items.length){ panel.style.display='none'; return; }
      panel.style.display = 'block';
      if(sub) sub.textContent = items.length + ' abierta(s)';
      var TIPO_EMOJI = {mp_faltante:'📦', equipo_caido:'⚠️', consulta_qc:'🔬', accidente:'🚨', otro:'❓'};
      cards.innerHTML = items.map(function(a){
        var fec = (a.ts_abierta||'').substring(5,16).replace('T',' ');
        var atendBadge = a.estado==='en_atencion'
          ? '<span style="background:#fef3c7;color:#92400e;padding:1px 6px;border-radius:8px;font-size:10px;font-weight:700;margin-left:4px">EN ATENCIÓN · '+_escHTML(a.atendida_por)+'</span>'
          : '';
        return '<div style="display:flex;justify-content:space-between;align-items:center;background:#fef2f2;border-left:3px solid #dc2626;padding:7px 10px;border-radius:5px">'+
          '<div style="flex:1">'+
            '<div style="font-size:12px;font-weight:600;color:#991b1b">'+
              (TIPO_EMOJI[a.tipo]||'❓')+' '+_escHTML(a.tipo)+' · '+_escHTML(a.operario)+atendBadge+
            '</div>'+
            '<div style="font-size:11px;color:#475569;margin-top:1px">'+_escHTML(a.descripcion)+'</div>'+
            '<div style="font-size:10px;color:#94a3b8;margin-top:1px">'+fec+(a.area_codigo?' · '+_escHTML(a.area_codigo):'')+'</div>'+
          '</div>'+
          '<div style="display:flex;gap:4px;margin-left:8px">'+
            (a.estado==='abierta' ? '<button data-andon-act="atender" data-id="'+a.id+'" style="padding:3px 8px;font-size:10px;background:#ca8a04;color:#fff;border:none;border-radius:4px;cursor:pointer">Atender</button>' : '')+
            '<button data-andon-act="resolver" data-id="'+a.id+'" style="padding:3px 8px;font-size:10px;background:#16a34a;color:#fff;border:none;border-radius:4px;cursor:pointer">✓ Resuelta</button>'+
          '</div>'+
        '</div>';
      }).join('');
    }catch(e){ panel.style.display='none'; }
  }
  if(typeof document !== 'undefined' && !window._CM_ANDON_DELEG){
    window._CM_ANDON_DELEG = true;
    document.addEventListener('click', async function(ev){
      var btn = ev.target && ev.target.closest && ev.target.closest('[data-andon-act]');
      if(!btn) return;
      var act = btn.getAttribute('data-andon-act');
      var id = btn.getAttribute('data-id');
      var body = {};
      if(act==='atender'){ body.estado = 'en_atencion'; }
      else if(act==='resolver'){
        var resol = prompt('Resolución (≥3 chars · qué se hizo):');
        if(!resol || resol.trim().length < 3){ alert('Resolución requerida'); return; }
        body.estado = 'resuelta'; body.resolucion = resol.trim();
      }
      try{
        var r = await fetch('/api/planta/andon/'+id+'/resolver', {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify(body),
        });
        var d = await r.json();
        if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
        cmCargarAndon();
      }catch(e){ alert('Error red: '+e.message); }
    });
  }

  // OLA 3 IA · Asistente "Pregúntale a la planta"
  function cmAbrirAsistente(){
    var m = document.getElementById('cm-asistente-modal');
    if(m){ m.style.display = 'flex'; document.getElementById('cm-asistente-input').focus(); }
  }
  function cmCerrarAsistente(){
    var m = document.getElementById('cm-asistente-modal');
    if(m) m.style.display = 'none';
  }
  async function cmAsistentePreguntar(){
    var inp = document.getElementById('cm-asistente-input');
    var hist = document.getElementById('cm-asistente-historial');
    var btn = document.getElementById('cm-asistente-send');
    var pregunta = (inp.value||'').trim();
    if(pregunta.length < 3) return;
    hist.innerHTML += '<div style="text-align:right;margin-bottom:6px"><span style="background:#7c3aed;color:#fff;padding:6px 10px;border-radius:10px;display:inline-block;max-width:80%">'+_escHTML(pregunta)+'</span></div>';
    hist.innerHTML += '<div id="cm-asist-pending" style="margin-bottom:6px"><span style="background:#f1f5f9;color:#475569;padding:6px 10px;border-radius:10px;display:inline-block;font-style:italic">pensando…</span></div>';
    hist.scrollTop = hist.scrollHeight;
    inp.value = ''; btn.disabled = true;
    try{
      var fecha = document.getElementById('plano-fecha') ? document.getElementById('plano-fecha').value : '';
      var r = await fetch('/api/asistente/operacion', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({pregunta: pregunta, fecha: fecha}),
      });
      var d = await r.json();
      var pending = document.getElementById('cm-asist-pending');
      if(pending) pending.remove();
      if(!r.ok){
        hist.innerHTML += '<div style="margin-bottom:6px"><span style="background:#fee2e2;color:#991b1b;padding:6px 10px;border-radius:10px;display:inline-block">⚠ '+_escHTML(d.error || ('HTTP '+r.status))+'</span></div>';
      } else {
        hist.innerHTML += '<div style="margin-bottom:6px"><span style="background:#f0fdfa;color:#134e4a;padding:6px 10px;border-radius:10px;display:inline-block;max-width:90%;white-space:pre-wrap">'+_escHTML(d.respuesta||'(sin respuesta)')+'</span></div>';
      }
      hist.scrollTop = hist.scrollHeight;
    }catch(e){
      var pending2 = document.getElementById('cm-asist-pending'); if(pending2) pending2.remove();
      hist.innerHTML += '<div style="margin-bottom:6px"><span style="background:#fee2e2;color:#991b1b;padding:6px 10px;border-radius:10px;display:inline-block">⚠ red: '+_escHTML(e.message)+'</span></div>';
    }
    btn.disabled = false;
  }

  async function cmCargarEquipo(){
    var cont = document.getElementById('cm-equipo-cards');
    var sub  = document.getElementById('cm-equipo-sub');
    if(!cont) return;
    try{
      var r = await fetch('/api/planta/tablero-equipo', {credentials:'same-origin'});
      var d = await r.json();
      if(!r.ok){
        if(sub) sub.textContent = '⚠️ ' + (d.error || ('HTTP ' + r.status));
        cont.innerHTML = '<div style="padding:14px;text-align:center;color:#b91c1c;font-size:12px">No se pudo cargar el equipo</div>';
        return;
      }
      var ops = d.operarios || [];
      var res = d.resumen || {};
      if(sub) sub.textContent = (res.con_tarea||0) + ' con tarea · ' + (res.sin_tarea||0) + ' disponibles';
      if(!ops.length){
        cont.innerHTML = '<div style="padding:14px;text-align:center;color:#94a3b8;font-size:12px">Sin operarios activos</div>';
        return;
      }
      cont.innerHTML = ops.map(function(o){
        var chip = o.es_jefe
          ? '<span style="font-size:9px;background:#fef3c7;color:#92400e;padding:1px 6px;border-radius:6px;font-weight:700">JEFE</span>'
          : (o.rol ? '<span style="font-size:9px;background:#e2e8f0;color:#475569;padding:1px 6px;border-radius:6px">'+_escHTML(o.rol)+'</span>' : '');
        var cuerpo;
        if(o.tareas && o.tareas.length){
          cuerpo = o.tareas.map(function(t){
            var ea = _cmEstadoArea(t.area_estado);
            var area = t.area_codigo
              ? '<span style="white-space:nowrap"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:'+ea.dot+';margin-right:3px;vertical-align:middle"></span>'+_escHTML(t.area_nombre||t.area_codigo)+' · '+ea.txt+'</span>'
              : '<span style="color:#94a3b8">sin área asignada</span>';
            var lp = t.area_requiere_limpieza ? ' <span title="requiere limpieza profunda">🧽</span>' : '';
            var dataArea = t.area_codigo ? ' data-area="'+_escHTML(t.area_codigo)+'"' : '';
            var verPlano = t.area_codigo ? ' <span style="font-size:9px;color:#1a4a7a;font-weight:700">📍 ver en plano</span>' : '';
            return '<div'+dataArea+' style="margin-top:6px;padding:6px 8px;background:#f8fafc;border-radius:6px;border-left:3px solid #1a4a7a">'
              + '<div style="font-size:11px;font-weight:700;color:#1a4a7a">'+_escHTML(t.etapa_label||'Tarea')+'</div>'
              + '<div style="font-size:12px;color:#0f172a;font-weight:600">'+_escHTML(t.producto||'(sin producto)')+'</div>'
              + '<div style="font-size:10px;color:#64748b;margin-top:2px">'+area+lp+verPlano+'</div>'
              + '</div>';
          }).join('');
        } else if(!(o.limpiezas && o.limpiezas.length)){
          cuerpo = '<div style="margin-top:6px;padding:8px;background:#f8fafc;border-radius:6px;font-size:11px;color:#94a3b8;text-align:center">Sin tarea asignada hoy</div>';
        } else {
          cuerpo = '';
        }
        var limp = '';
        if(o.limpiezas && o.limpiezas.length){
          limp = o.limpiezas.map(function(l){
            return '<div data-area="'+_escHTML(l.area_codigo)+'" style="margin-top:6px;padding:6px 8px;background:#ecfeff;border-radius:6px;border-left:3px solid #7c3aed">'
              + '<div style="font-size:11px;font-weight:700;color:#7c3aed">🧽 Limpiar '+_escHTML(l.area_nombre||l.area_codigo)+'</div>'
              + '<div style="font-size:10px;color:#64748b;margin-top:1px">'+_escHTML(l.limpieza_estado||'pendiente')+' · 📍 ver en plano</div>'
              + '</div>';
          }).join('');
        }
        var activo = (o.tareas && o.tareas.length) || (o.limpiezas && o.limpiezas.length);
        var borde = activo ? '#1a4a7a' : '#cbd5e1';
        return '<div style="background:#fff;border:1px solid #e2e8f0;border-top:3px solid '+borde+';border-radius:8px;padding:10px 12px">'
          + '<div style="display:flex;justify-content:space-between;align-items:center;gap:6px">'
          + '<a href="/mi-dia?as_operario_id='+o.id+'" target="_blank" style="font-size:13px;color:#0f172a;font-weight:700;text-decoration:none" title="Abrir Mi Día de '+_escHTML(o.nombre||'')+'">'+_escHTML(o.nombre||('op#'+o.id))+' <span style="font-size:9px;color:#1a4a7a;font-weight:500">↗</span></a>'
          + chip + '</div>'
          + cuerpo
          + limp
          + '</div>';
      }).join('');
      // Panel de limpieza de salas (paso 4)
      var limpPanel = document.getElementById('cm-limpieza-panel');
      var limpCards = document.getElementById('cm-limpieza-cards');
      var limpSub   = document.getElementById('cm-limpieza-sub');
      var salas = d.salas_limpieza || [];
      if(limpPanel && limpCards){
        if(!salas.length){
          limpPanel.style.display = 'none';
        } else {
          limpPanel.style.display = '';
          if(limpSub) limpSub.textContent = salas.length + ' sala(s) · ' + (res.salas_sin_limpiador||0) + ' sin responsable';
          limpCards.innerHTML = salas.map(function(s){
            var ea = _cmEstadoArea(s.area_estado);
            var quien = s.asignado_a
              ? '<span style="font-size:11px;color:#0f172a;font-weight:600">👤 '+_escHTML(s.asignado_a)+'</span>'
              : '<span style="font-size:11px;color:#b91c1c;font-weight:700">⚠️ sin asignar</span>';
            return '<div data-area="'+_escHTML(s.area_codigo)+'" style="background:#fff;border:1px solid #e2e8f0;border-top:3px solid '+ea.dot+';border-radius:8px;padding:10px 12px">'
              + '<div style="font-size:13px;font-weight:700;color:#0f172a">'+_escHTML(s.area_nombre||s.area_codigo)+'</div>'
              + '<div style="font-size:10px;color:'+ea.dot+';font-weight:700;margin:2px 0">'+_escHTML(ea.txt)+(s.requiere_profunda?' · limpieza profunda':'')+'</div>'
              + quien
              + '</div>';
          }).join('');
        }
      }
      document.querySelectorAll('#cm-equipo-cards [data-area], #cm-limpieza-cards [data-area]').forEach(function(el){
        el.style.cursor = 'pointer';
        el.title = 'Click para resaltar el área en el plano';
        el.onclick = function(){ cmResaltarArea(el.getAttribute('data-area')); };
      });
    }catch(e){
      if(sub) sub.textContent = '⚠️ ' + (e.message || e);
    }
  }

  // CALENDARIO SEMANAL (Sebastián 1-may-2026: 'estilo calendario donde dice
  // día y producción'). 5 columnas L-V con producciones apiladas en cada día.
  function renderProduccionesDiaCards(prods, kpis){
    var sub = document.getElementById('cm-dia-sub');
    var grid = document.getElementById('cm-dia-cards');
    if(!grid) return;
    var n_pendientes = prods.filter(function(p){ return p.estado === 'planeado' || p.estado === 'programado'; }).length;
    var n_iniciadas = prods.filter(function(p){ return p.estado === 'en_proceso' || p.estado === 'iniciado'; }).length;
    var n_terminadas = prods.filter(function(p){ return p.estado === 'completado'; }).length;
    if(sub) sub.textContent = prods.length + ' total · ' + n_pendientes + ' pendientes · ' + n_iniciadas + ' en proceso · ' + n_terminadas + ' terminadas';

    // Calcular semana (lunes-viernes) basada en fecha selector o hoy
    var hoyIso = new Date().toISOString().slice(0,10);
    var hoy = new Date(hoyIso+'T00:00:00');
    var fechaSel = (document.getElementById('plano-fecha')||{value:''}).value;
    var ref = fechaSel ? new Date(fechaSel+'T00:00:00') : hoy;
    // si es sábado/domingo → próximo lunes
    var dow = ref.getDay();
    var lunes = new Date(ref);
    if(dow === 0) lunes.setDate(ref.getDate() + 1);  // dom → lun
    else if(dow === 6) lunes.setDate(ref.getDate() + 2);  // sáb → lun
    else lunes.setDate(ref.getDate() - (dow - 1));  // L=0d, M=−1, etc

    var diasSemana = [];
    var nombresDia = ['LUN','MAR','MIÉ','JUE','VIE'];
    var tiposDia = ['PRODUCCIÓN','ACOND/CONTEO','PRODUCCIÓN','ACOND/CONTEO','PRODUCCIÓN'];
    for(var i=0; i<5; i++){
      var d = new Date(lunes); d.setDate(lunes.getDate()+i);
      var iso = d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
      diasSemana.push({iso: iso, nombre: nombresDia[i], tipo: tiposDia[i], es_hoy: iso === hoyIso});
    }

    // Agrupar producciones por fecha
    var porFecha = {};
    prods.forEach(function(p){
      var f = p.fecha || '';
      if(!porFecha[f]) porFecha[f] = [];
      porFecha[f].push(p);
    });

    // ── render mini-card de producción
    function _renderProdMini(p){
      var borderCol = '#cbd5e1';
      var bgCol = '#fff';
      var icon = '';
      if(p.estado === 'completado'){
        borderCol = '#16a34a'; bgCol = '#f0fdf4'; icon = '✅';
      } else if(p.estado === 'en_proceso' || p.estado === 'iniciado'){
        borderCol = '#1d4ed8'; bgCol = '#eff6ff'; icon = '🔵';
      } else if(p.desde_calendar){
        borderCol = '#7c3aed'; bgCol = '#faf5ff'; icon = '📅';
      } else {
        borderCol = '#6d28d9'; bgCol = '#f0fdfa'; icon = '⏳';
      }
      // Wave label si hay scheduling secuencial
      var waveBadge = '';
      if(p.wave && p.wave > 1){
        waveBadge = '<span style="background:#fbbf24;color:#78350f;padding:1px 4px;border-radius:3px;font-size:8px;font-weight:700;margin-left:3px">⏰ ONDA '+p.wave+'</span>';
      }
      var h = '<div style="background:'+bgCol+';border-left:3px solid '+borderCol+';border-radius:4px;padding:5px 7px;margin-bottom:5px;font-size:10px">';
      h += '<div style="font-weight:700;color:#0f172a" title="'+_escHTML(p.titulo_calendar||p.producto)+'">'+icon+' '+_escHTML((p.producto||'').substring(0,24))+waveBadge+'</div>';
      h += '<div style="color:#475569;font-size:9px;margin-top:1px">'+(p.kg||0)+'kg';
      if(p.area && p.area.codigo) h += ' · 🏭 '+_escHTML(p.area.codigo);
      // Slot horario sugerido
      if(p.slot_inicio_sugerido) h += ' · ⏱'+p.slot_inicio_sugerido+'-'+p.slot_fin_sugerido;
      h += '</div>';
      // Operarios compactos (1 línea)
      var ops = [];
      if(p.operarios.dispensacion) ops.push(p.operarios.dispensacion.split(' ')[0]);
      if(p.operarios.elaboracion && !ops.includes(p.operarios.elaboracion.split(' ')[0])) ops.push(p.operarios.elaboracion.split(' ')[0]);
      if(p.operarios.envasado && !ops.includes(p.operarios.envasado.split(' ')[0])) ops.push(p.operarios.envasado.split(' ')[0]);
      if(p.operarios.acondicionamiento && !ops.includes(p.operarios.acondicionamiento.split(' ')[0])) ops.push(p.operarios.acondicionamiento.split(' ')[0]);
      if(ops.length) h += '<div style="color:#64748b;font-size:9px;margin-top:1px">👤 '+_escHTML(ops.slice(0,3).join('·'))+'</div>';
      // Botón acción mini
      if(p.accion){
        var btnCol = (p.accion === 'iniciar' || p.accion === 'iniciar_calendar') ? '#10b981' :
                     (p.accion === 'terminar' ? '#1d4ed8' : '#7c3aed');
        if(p.accion === 'iniciar_calendar' && p.payload_iniciar){
          var payB64 = btoa(unescape(encodeURIComponent(JSON.stringify(p.payload_iniciar))));
          h += '<button class="cm-dia-btn" data-tipo="iniciar_calendar" data-payload="'+payB64+'" style="margin-top:3px;width:100%;padding:3px 6px;background:'+btnCol+';color:#fff;border:none;border-radius:3px;font-size:9px;font-weight:700;cursor:pointer">▶</button>';
        } else {
          var lbl = (p.accion === 'terminar') ? '✓ Terminar' : (p.accion === 'asignar_ia' ? '🤖 IA' : '▶');
          h += '<button class="cm-dia-btn" data-tipo="'+p.accion+'" data-id="'+(p.id||0)+'" style="margin-top:3px;width:100%;padding:3px 6px;background:'+btnCol+';color:#fff;border:none;border-radius:3px;font-size:9px;font-weight:700;cursor:pointer">'+lbl+'</button>';
        }
      }
      h += '</div>';
      return h;
    }

    // Render calendario semanal (5 columnas L-V)
    grid.style.display = 'grid';
    grid.style.gridTemplateColumns = 'repeat(5, 1fr)';
    grid.style.gap = '8px';
    grid.innerHTML = diasSemana.map(function(dia){
      var prodsDia = porFecha[dia.iso] || [];
      var bgHeader = dia.es_hoy ? '#f59e0b' : (dia.tipo === 'PRODUCCIÓN' ? '#6d28d9' : '#64748b');
      var bgBody = dia.es_hoy ? '#fef3c7' : '#fff';
      var html = '<div style="background:'+bgBody+';border:'+(dia.es_hoy?'2px solid #f59e0b':'1px solid #e2e8f0')+';border-radius:8px;overflow:hidden;min-height:200px">';
      // Header
      html += '<div style="background:'+bgHeader+';color:#fff;padding:6px 8px;text-align:center">';
      html += '<div style="font-weight:800;font-size:13px">'+dia.nombre+' '+dia.iso.substring(5)+'</div>';
      html += '<div style="font-size:9px;opacity:.9">'+dia.tipo+(prodsDia.length?' · '+prodsDia.length+' prods':'')+'</div>';
      if(dia.es_hoy) html += '<div style="font-size:9px;font-weight:700;background:rgba(255,255,255,.3);border-radius:3px;padding:1px 6px;display:inline-block;margin-top:2px">HOY</div>';
      html += '</div>';
      // Body
      html += '<div style="padding:6px">';
      if(prodsDia.length){
        html += prodsDia.map(_renderProdMini).join('');
      } else {
        var msg = dia.tipo === 'PRODUCCIÓN' ? 'Sin producciones · agrega evento al Calendar' : 'Día de acond/conteo';
        html += '<div style="color:#94a3b8;font-style:italic;font-size:9px;text-align:center;padding:14px 4px">'+msg+'</div>';
      }
      html += '</div></div>';
      return html;
    }).join('');
  }

  // ── Diagnóstico DB sin match Calendar (Sebastián 1-may-2026:
  // 'sigue mostrando lunes todas y martes mezcla' → auto-limpieza al GET)
  function renderProduccionesDiag(diag){
    var panel = document.getElementById('cm-dia-panel');
    if(!panel) return;
    var existing = document.getElementById('cm-diag-banner');
    if(existing) existing.remove();
    var capExisting = document.getElementById('cm-cap-banner');
    if(capExisting) capExisting.remove();
    var orphans = (diag.db_sin_calendar) || [];
    var autoClean = diag.auto_canceladas_esta_carga || 0;
    var capWarn = diag.capacidad_warnings || [];

    // Banner de sobre-capacidad (Sebastián 1-may-2026)
    if(capWarn.length){
      var capBanner = document.createElement('div');
      capBanner.id = 'cm-cap-banner';
      capBanner.style.cssText = 'background:#fef3c7;border:1px solid #fbbf24;border-radius:6px;padding:8px 10px;margin-bottom:10px;font-size:11px;color:#78350f';
      var lista = capWarn.map(function(w){
        var d = new Date(w.fecha+'T00:00:00');
        var nombresD = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'];
        return '<li><b>'+nombresD[d.getDay()]+' '+w.fecha.substring(5)+'</b>: '+w.num_producciones+' producciones · capacidad simultánea '+w.capacidad+' · '+w.extras_secuenciales+' deben ser secuenciales (onda '+w.ondas_secuenciales+')</li>';
      }).join('');
      capBanner.innerHTML = '<b>⏰ '+capWarn.length+' día(s) con sobre-capacidad</b> · 4 operarios pueden llevar máximo 4 producciones en paralelo · las extras serán ondas secuenciales:<br>'
        +'<ul style="margin:4px 0 0 18px;padding:0">'+lista+'</ul>'
        +'<div style="font-size:10px;margin-top:4px;opacity:.8">Las cards muestran ⏱hh:mm con horario sugerido · onda 2/3 = ⏰ amarillo</div>';
      var firstChild = panel.firstChild;
      panel.insertBefore(capBanner, firstChild ? firstChild.nextSibling : null);
    }

    // Mostrar banner orphans/auto-clean si hubo
    if(!autoClean && !orphans.length) return;
    var banner = document.createElement('div');
    banner.id = 'cm-diag-banner';
    if(autoClean){
      // ✅ Auto-clean sucedió en este GET · banner verde informativo
      banner.style.cssText = 'background:#dcfce7;border:1px solid #86efac;border-radius:6px;padding:8px 10px;margin-bottom:10px;font-size:11px;color:#166534';
      var detalle = (diag.auto_cancel_detalle||[]).map(_escHTML).join(' · ');
      banner.innerHTML = '<b>✅ '+autoClean+' filas DB huérfanas auto-canceladas</b> · Calendar es ahora la fuente única de verdad'
        +(detalle ? '<br><span style="font-size:10px;opacity:.8">Ej: '+detalle+(autoClean > 5 ? ' ...' : '')+'</span>' : '');
    } else {
      // Quedan orphans pendientes (probablemente >50 de límite)
      banner.style.cssText = 'background:#fef3c7;border:1px solid #fbbf24;border-radius:6px;padding:8px 10px;margin-bottom:10px;font-size:11px;color:#78350f';
      var lista = orphans.slice(0,8).map(function(o){
        return '<li>'+_escHTML(o.producto)+' · '+o.fecha+' · '+(o.kg||0)+'kg'+(o.area_codigo?(' · '+_escHTML(o.area_codigo)):'')+'</li>';
      }).join('');
      banner.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap">'
        +'<div><b>⚠️ '+orphans.length+' producciones DB SIN match en Google Calendar</b><br>'
        +'<span style="font-size:10px">Auto-limpieza próximo refresh · o click manual</span></div>'
        +'<button onclick="limpiarDbSinCalendar()" style="padding:5px 12px;background:#dc2626;color:#fff;border:none;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer">🗑 Cancelar '+orphans.length+' ahora</button>'
        +'</div>'
        +'<details style="margin-top:6px"><summary style="cursor:pointer;font-size:10px">Ver detalle</summary>'
        +'<ul style="margin:4px 0 0 18px;padding:0">'+lista
        +(orphans.length > 8 ? '<li>...y '+(orphans.length-8)+' más</li>' : '')
        +'</ul></details>';
    }
    // Insertar al inicio del panel (después del header)
    var firstChild = panel.firstChild;
    panel.insertBefore(banner, firstChild ? firstChild.nextSibling : null);
    // Auto-hide después de 8s si fue solo info de auto-clean
    if(autoClean){
      setTimeout(function(){ if(banner) banner.style.display='none'; }, 8000);
    }
  }

  async function limpiarDbSinCalendar(){
    if(!confirm('🗑 Cancelar producciones DB sin match Calendar?\n\n• Solo afecta filas no iniciadas\n• Cambia estado a "cancelado" (NO delete · revertible)\n• Calendar queda como fuente única de verdad\n\n¿Continuar?')) return;
    var msg = document.getElementById('cm-dia-msg');
    if(msg){
      msg.style.display='block';
      msg.style.background='#fef3c7'; msg.style.color='#78350f';
      msg.innerHTML='⏳ Cancelando filas DB huérfanas...';
    }
    try{
      var fecha = (document.getElementById('plano-fecha')||{value:''}).value || new Date().toISOString().slice(0,10);
      var r = await fetch('/api/planta/limpiar-db-sin-calendar', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({fecha: fecha}),
      });
      var d = await r.json();
      if(!r.ok || !d.ok) throw new Error(d.error || 'HTTP '+r.status);
      if(msg){
        msg.style.background='#dcfce7'; msg.style.color='#166534';
        msg.innerHTML='✅ '+d.mensaje;
        setTimeout(function(){ msg.style.display='none'; }, 4000);
      }
      renderCentroMando();
    }catch(e){
      if(msg){
        msg.style.background='#fef2f2'; msg.style.color='#991b1b';
        msg.innerHTML='❌ '+e.message;
      }
    }
  }

  // Event delegation para botones de cards (Sebastián 1-may-2026)
  document.addEventListener('click', function(ev){
    var btn = ev.target.closest && ev.target.closest('.cm-dia-btn');
    if(!btn) return;
    var tipo = btn.getAttribute('data-tipo');
    var msg = document.getElementById('cm-dia-msg');
    function showMsg(html, color, bg){
      if(!msg) return;
      msg.style.display='block';
      msg.style.color = color || '#0f172a';
      msg.style.background = bg || '#f1f5f9';
      msg.innerHTML = html;
    }
    function hideMsg(){
      setTimeout(function(){ if(msg) msg.style.display='none'; }, 3500);
    }
    // Calendar-first iniciar
    var payload = btn.getAttribute('data-payload');
    if(tipo === 'iniciar_calendar' && payload){
      try{
        var pl = JSON.parse(decodeURIComponent(escape(atob(payload))));
        if(!confirm('▶ Iniciar "'+pl.producto+'"?\n\n• IA asigna área óptima\n• IA rota operarios\n• Marca sala como ocupada')) return;
        showMsg('⏳ Iniciando...', '#78350f', '#fef3c7');
        fetch('/api/planta/accion-rapida', {
          method:'POST', credentials:'same-origin',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify(Object.assign({tipo:'iniciar_calendar'}, pl)),
        }).then(function(r){return r.json().then(function(d){return {ok:r.ok && d.ok!==false, d:d};});}).then(function(res){
          if(!res.ok) throw new Error(res.d.error || 'error');
          showMsg('✅ '+(res.d.mensaje||'Iniciada'), '#166534', '#dcfce7');
          hideMsg();
          renderCentroMando();
        }).catch(function(e){
          showMsg('❌ '+e.message, '#991b1b', '#fef2f2');
        });
      }catch(e){ showMsg('❌ payload error', '#991b1b', '#fef2f2'); }
      return;
    }
    var id = parseInt(btn.getAttribute('data-id') || '0', 10);
    if(!tipo || !id) return;
    var labels = {
      'iniciar': '▶ Iniciar producción',
      'terminar': '✓ Terminar (sala queda SUCIA hasta marcar limpia)',
      'asignar_ia': '🤖 IA asigna área + operarios',
    };
    if(!confirm((labels[tipo]||tipo)+'?')) return;
    showMsg('⏳ Ejecutando...', '#78350f', '#fef3c7');
    var tipoBack = tipo === 'iniciar' ? 'iniciar_produccion' : (tipo === 'terminar' ? 'terminar_produccion' : tipo);
    fetch('/api/planta/accion-rapida', {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({tipo: tipoBack, produccion_id: id}),
    }).then(function(r){return r.json().then(function(d){return {ok:r.ok && d.ok!==false, d:d};});}).then(function(res){
      if(!res.ok) throw new Error(res.d.error || 'error');
      showMsg('✅ '+(res.d.mensaje||'OK'), '#166534', '#dcfce7');
      hideMsg();
      renderCentroMando();
    }).catch(function(e){
      showMsg('❌ '+e.message, '#991b1b', '#fef2f2');
    });
  });

  function _kpiCard(label, val, color){
    return '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:10px 14px;border-left:4px solid '+color+'">'+
      '<div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">'+label+'</div>'+
      '<div style="font-size:22px;font-weight:800;color:'+color+';margin-top:2px">'+val+'</div>'+
      '</div>';
  }

  function cargarTimelineEventos(evs){
    var box = document.getElementById('plano-rotacion');
    // En realidad pintaremos timeline + rotacion juntos en cargarRotacionOperarios
    // (rotacion sigue debajo). Aqui guardamos el array y la rotacion lo merge.
    window._CM_EVENTS = evs;
  }

  function mostrarDetalleSala(a){
    var box = document.getElementById('plano-detalle');
    if(!a){ box.style.display='none'; return; }
    box.style.display = 'block';
    var caps = [];
    if(a.puede_producir) caps.push('Producción');
    if(a.puede_envasar)  caps.push('Envasado');
    if(a.marmita_ml)     caps.push('Marmita ' + a.marmita_ml + ' ml');
    if(a.especial)       caps.push('Especial: ' + a.especial);
    if(a.tipo === 'conteo_ciclico') caps.push('Conteos cíclicos');
    if(a.tipo === 'apoyo_asignable') caps.push('Apoyo asignable');
    var ocupHTML = '';
    if(a.ocupada_por && a.ocupada_por.length){
      ocupHTML = '<div style="margin-top:12px"><b>Producciones asignadas / en curso:</b>' +
        a.ocupada_por.map(function(o){
          var ops = [];
          // BUG-16 fix · 19-may-2026: escapar nombres operarios (vienen de DB)
          if(o.operario_dispensacion)      ops.push('Disp: '+_escHTML(o.operario_dispensacion));
          if(o.operario_elaboracion)       ops.push('Elab: '+_escHTML(o.operario_elaboracion));
          if(o.operario_envasado)          ops.push('Env: '+_escHTML(o.operario_envasado));
          if(o.operario_acondicionamiento) ops.push('Acon: '+_escHTML(o.operario_acondicionamiento));
          var liveBadge = '';
          if(o.en_curso){
            liveBadge = '<span style="background:#dc2626;color:#fff;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;letter-spacing:.5px;margin-left:6px;text-transform:uppercase">EN CURSO ⏱'+_fmtMin(o.minutos_corridos)+'</span>';
          } else if(o.fin_real_at){
            liveBadge = '<span style="background:#16a34a;color:#fff;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;margin-left:6px">terminada</span>';
          } else {
            liveBadge = '<span style="background:#94a3b8;color:#fff;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;margin-left:6px">pendiente iniciar</span>';
          }
          // Botones iniciar/terminar
          var btns = '';
          if(!o.inicio_real_at){
            btns = '<button onclick="cmIniciarProduccion('+o.produccion_id+')" style="background:#16a34a;color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer">▶ Iniciar producción</button>';
          } else if(!o.fin_real_at){
            btns = '<button onclick="cmTerminarProduccion('+o.produccion_id+')" style="background:#dc2626;color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer">⏹ Terminar producción</button>';
          }
          return '<div style="background:#f8fafc;border-radius:6px;padding:10px 14px;margin-top:8px;border-left:3px solid '+(o.en_curso?'#ca8a04':o.fin_real_at?'#16a34a':'#94a3b8')+'">' +
            // BUG-16 fix · 19-may-2026: escapar producto (viene de DB)
            '<div><b>'+_escHTML(o.producto)+'</b> · '+(parseInt(o.lotes,10)||0)+' lote(s) · '+(parseFloat(o.kg)||0)+' kg' + liveBadge + '</div>' +
            (ops.length?'<div style="font-size:11px;color:#64748b;margin-top:4px">'+ops.join(' · ')+'</div>':'') +
            (btns?'<div style="margin-top:8px">'+btns+'</div>':'') +
            '</div>';
        }).join('') + '</div>';
    } else {
      ocupHTML = '<div style="margin-top:10px;color:#16a34a;font-size:13px">✓ Sin producción asignada</div>';
    }
    box.innerHTML =
      '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px">'+
        // BUG-16 fix · 19-may-2026: escapar nombre/código del área
        '<h3 style="margin:0;color:#1a4a7a">🏭 '+_escHTML(a.nombre)+' <span style="font-size:12px;color:#64748b;font-weight:500">('+_escHTML(a.codigo)+')</span></h3>'+
        '<div style="display:flex;gap:6px;flex-wrap:wrap">'+
          ['libre','sucia','limpiando','ocupada'].map(function(est){
            var current = a.estado===est;
            return '<button onclick="cambiarEstadoSala('+a.id+',\''+est+'\')" style="padding:5px 10px;border:1px solid '+(current?'#1a4a7a':'#cbd5e1')+';background:'+(current?'#1a4a7a':'#fff')+';color:'+(current?'#fff':'#475569')+';border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;text-transform:uppercase">'+est+'</button>';
          }).join('') +
          '<button onclick="abrirRotulo('+a.id+')" style="padding:5px 12px;border:none;background:#7c3aed;color:#fff;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer">🏷️ Rótulo de limpieza</button>' +
        '</div>'+
      '</div>'+
      '<div style="font-size:13px;color:#475569;margin-top:8px">'+caps.join(' · ')+'</div>'+
      ocupHTML +
      // Sección turnos de operarios (con timer + iniciar/terminar)
      '<div id="cm-turnos-'+a.id+'" style="margin-top:14px;padding:12px;background:#fefce8;border:1px solid #fde68a;border-radius:8px">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">' +
          '<b style="color:#854d0e;font-size:13px">🧑‍🏭 Turnos de operarios en esta sala</b>' +
          '<button onclick="abrirIniciarTurno('+a.id+')" style="background:#16a34a;color:#fff;border:none;padding:5px 10px;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer">+ Iniciar turno</button>' +
        '</div>' +
        '<div id="cm-turnos-list-'+a.id+'" style="font-size:12px"><div style="color:#94a3b8;text-align:center;padding:10px">Cargando turnos...</div></div>' +
      '</div>';
    cargarTurnosSala(a.id);
  }

  async function cargarTurnosSala(area_id){
    var box = document.getElementById('cm-turnos-list-'+area_id);
    if(!box) return;
    try{
      var r = await fetch('/api/planta/areas/'+area_id+'/actividades');
      var d = await r.json();
      var acts = d.actividades || [];
      var activas = acts.filter(function(x){ return x.en_curso; });
      var cerradas = acts.filter(function(x){ return !x.en_curso; }).slice(0, 5);
      var html = '';
      if(activas.length){
        html += '<div style="margin-bottom:8px"><b style="font-size:11px;color:#854d0e;text-transform:uppercase;letter-spacing:.5px">⏱ En curso ahora</b></div>';
        html += activas.map(function(t){
          var icon = {produccion:'🏭',dispensacion:'⚖',envasado:'📦',acondicionamiento:'🎁',conteo_ciclico:'📊',limpieza:'🧹',mantenimiento:'🔧',otro:'📋'}[t.tipo]||'📋';
          return '<div style="background:#fff;border-left:3px solid #ca8a04;padding:8px 10px;margin-bottom:6px;border-radius:0 6px 6px 0;display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap">' +
            '<div style="flex:1;min-width:140px">' +
              // BUG-16 fix · 19-may-2026: escapar operario_nombre / tipo / descripcion (vienen de DB)
              '<div style="font-weight:600;color:#0f172a">'+icon+' <b>'+_escHTML(t.operario_nombre)+'</b> · <span style="color:#64748b">'+_escHTML(t.tipo)+'</span></div>' +
              (t.descripcion?'<div style="font-size:11px;color:#64748b;margin-top:2px">'+_escHTML(t.descripcion)+'</div>':'') +
              '<div style="font-size:11px;color:#ca8a04;font-weight:700;margin-top:3px">⏱ '+_fmtMin(t.minutos_corridos)+' transcurridos</div>' +
            '</div>' +
            '<button onclick="terminarTurno('+t.id+','+area_id+')" style="background:#dc2626;color:#fff;border:none;padding:5px 10px;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer">⏹ Terminar</button>' +
          '</div>';
        }).join('');
      } else {
        html += '<div style="color:#94a3b8;text-align:center;padding:6px;font-style:italic">Nadie trabajando ahora — click "+ Iniciar turno"</div>';
      }
      if(cerradas.length){
        html += '<div style="margin-top:10px;padding-top:8px;border-top:1px dashed #fde68a"><b style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px">Últimos turnos cerrados</b></div>';
        html += cerradas.map(function(t){
          var icon = {produccion:'🏭',dispensacion:'⚖',envasado:'📦',acondicionamiento:'🎁',conteo_ciclico:'📊',limpieza:'🧹',mantenimiento:'🔧',otro:'📋'}[t.tipo]||'📋';
          return '<div style="font-size:11px;color:#475569;padding:4px 8px;background:#f8fafc;border-radius:4px;margin-top:3px;display:flex;justify-content:space-between">' +
            // BUG-16 fix · 19-may-2026: escapar operario_nombre + tipo
            '<span>'+icon+' '+_escHTML(t.operario_nombre)+' · '+_escHTML(t.tipo)+'</span>' +
            '<span style="color:#64748b">⏱ '+_fmtMin(t.duracion_min)+'</span>' +
          '</div>';
        }).join('');
      }
      box.innerHTML = html;
    }catch(e){ box.innerHTML = '<div style="color:#dc2626;font-size:12px">Error al cargar turnos</div>'; }
  }

  async function abrirIniciarTurno(area_id){
    // Cargar operarios para selector
    if(!_PLANTA_OPERARIOS) await _mpCargarCatalogos();
    var ops = (_PLANTA_OPERARIOS||[]).filter(function(o){ return !o.es_jefe; });
    if(!ops.length){ _toast('Sin operarios activos', 0); return; }
    var opSel = ops.map(function(o){ return '<option value="'+o.id+'">'+o.nombre_completo+'</option>'; }).join('');
    var modal = document.getElementById('modal-turno');
    if(!modal){
      modal = document.createElement('div');
      modal.id = 'modal-turno';
      modal.style.cssText = 'display:flex;position:fixed;inset:0;background:rgba(15,23,42,.7);z-index:99999;align-items:center;justify-content:center;padding:20px';
      modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:20px 22px;max-width:420px;width:100%">' +
        '<h3 style="color:#1a4a7a;font-size:16px;margin-bottom:14px">⏱ Iniciar turno operario</h3>' +
        '<input type="hidden" id="tn-area">' +
        '<label style="font-size:12px;font-weight:600;color:#475569;display:block;margin-bottom:3px">Operario *</label>' +
        '<select id="tn-op" style="width:100%;padding:7px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;margin-bottom:10px">'+opSel+'</select>' +
        '<label style="font-size:12px;font-weight:600;color:#475569;display:block;margin-bottom:3px">Tipo de actividad *</label>' +
        '<select id="tn-tipo" style="width:100%;padding:7px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;margin-bottom:10px">' +
          '<option value="produccion">🏭 Producción</option>' +
          '<option value="dispensacion">⚖ Dispensación</option>' +
          '<option value="envasado">📦 Envasado</option>' +
          '<option value="acondicionamiento">🎁 Acondicionamiento</option>' +
          '<option value="conteo_ciclico">📊 Conteo cíclico</option>' +
          '<option value="limpieza">🧹 Limpieza</option>' +
          '<option value="mantenimiento">🔧 Mantenimiento</option>' +
          '<option value="otro">📋 Otro</option>' +
        '</select>' +
        '<label style="font-size:12px;font-weight:600;color:#475569;display:block;margin-bottom:3px">Descripción (opcional)</label>' +
        '<textarea id="tn-descr" rows="2" placeholder="Ej: lote LBHA-261001, turno A" style="width:100%;padding:7px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;font-family:inherit;margin-bottom:14px"></textarea>' +
        '<div style="display:flex;gap:8px;justify-content:flex-end">' +
          '<button id="tn-cancel" style="background:#e2e8f0;color:#475569;border:none;padding:8px 16px;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer">Cancelar</button>' +
          '<button id="tn-save" style="background:#16a34a;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-size:13px;font-weight:700;cursor:pointer">▶ Iniciar</button>' +
        '</div>' +
      '</div>';
      document.body.appendChild(modal);
      document.getElementById('tn-cancel').onclick = function(){
        document.getElementById('modal-turno').style.display='none';
      };
      document.getElementById('tn-save').onclick = iniciarTurno;
    } else {
      document.getElementById('tn-op').innerHTML = opSel;
      modal.style.display = 'flex';
    }
    document.getElementById('tn-area').value = area_id;
    document.getElementById('tn-descr').value = '';
  }

  async function iniciarTurno(){
    var area_id = document.getElementById('tn-area').value;
    var body = {
      operario_id: parseInt(document.getElementById('tn-op').value),
      tipo: document.getElementById('tn-tipo').value,
      descripcion: document.getElementById('tn-descr').value
    };
    try{
      var r = await fetch('/api/planta/areas/'+area_id+'/actividades', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body)
      });
      var d = await r.json();
      if(d.ok){
        if(d.cerrado_previo){ _toast('Turno previo de '+d.operario+' cerrado en otra sala', 1); }
        else { _toast('Turno iniciado: '+d.operario, 1); }
        document.getElementById('modal-turno').style.display = 'none';
        cargarTurnosSala(area_id);
        renderCentroMando();
      } else { _toast('Error: '+(d.error||'?'), 0); }
    }catch(e){ _toast('Error de red', 0); }
  }

  async function terminarTurno(act_id, area_id){
    var obs = prompt('Observaciones del turno (opcional):', '');
    if(obs === null) return; // canceló
    try{
      var r = await fetch('/api/planta/actividades/'+act_id+'/terminar', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({observaciones: obs || null})
      });
      var d = await r.json();
      if(d.ok){
        _toast('Turno cerrado · ' + (d.duracion_min!=null ? _fmtMin(d.duracion_min) : ''), 1);
        cargarTurnosSala(area_id);
        renderCentroMando();
      } else { _toast('Error: '+(d.error||'?'), 0); }
    }catch(e){ _toast('Error de red', 0); }
  }

  async function cmIniciarProduccion(id){
    if(!confirm('¿Iniciar la producción ahora?\n\n' +
                'Se DESCONTARÁ el inventario de MPs (FEFO) en este momento.\n' +
                'El contador de tiempo arranca.\n\n' +
                'Si falta stock para alguna MP, el sistema bloquea el inicio.')) return;
    try{
      var r = await fetch('/api/programacion/programar/'+id+'/iniciar', {method:'POST'});
      var d = await r.json();
      if(d.ok){
        var msg;
        if(d.ya_iniciada){
          msg = 'Ya estaba iniciada';
        } else if(d.sin_formula){
          msg = '⚠ Iniciada SIN descontar (formula vacia · revisa /tecnica)';
        } else {
          var n = (d.mps_descontadas||[]).length;
          msg = 'Producción iniciada · descontadas '+n+' MPs ('+
                ((d.total_g_descontado||0)/1000).toFixed(1)+' kg)';
        }
        _toast(msg, 1);
        renderCentroMando();
      }
      else if(r.status === 422 && d.codigo === 'SIN_STOCK'){
        var faltantes = (d.faltantes||[]).slice(0,5).map(function(f){
          return '  · '+f.nombre+': falta '+(f.falta_g||0).toLocaleString()+' g';
        }).join('\n');
        if((d.faltantes||[]).length > 5) faltantes += '\n  ... y '+(d.faltantes.length-5)+' MPs mas';
        alert('❌ NO se puede iniciar: stock insuficiente\n\n'+faltantes+
              '\n\nRevisa entradas en /planta o crea OC en /compras.');
      }
      else { _toast('Error: '+(d.error||'?'), 0); }
    }catch(e){ _toast('Error de red', 0); }
  }
  async function cmTerminarProduccion(id){
    if(!confirm('¿Terminar la producción? La sala quedará en estado SUCIA esperando limpieza.')) return;
    try{
      var r = await fetch('/api/programacion/programar/'+id+'/terminar', {method:'POST'});
      var d = await r.json();
      if(d.ok){
        var msg = d.ya_terminada ? 'Ya estaba terminada' : ('Producción terminada · cycle time: '+_fmtMin(d.cycle_time_min));
        _toast(msg, 1);
        renderCentroMando();
      }
      else { _toast('Error: '+(d.error||'?'), 0); }
    }catch(e){ _toast('Error de red', 0); }
  }

  async function cambiarEstadoSala(id, nuevo){
    try{
      var r = await fetch('/api/planta/areas/'+id+'/estado', {
        method:'PATCH', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({estado: nuevo})
      });
      var d = await r.json();
      if(d.ok){
        _toast('Sala actualizada: '+nuevo, 1);
        renderCentroMando();
      } else {
        _toast('Error: '+(d.error||'desconocido'), 0);
      }
    }catch(e){ _toast('Error de red', 0); }
  }

  // ── Gestion de operarios CRUD ────────────────────────────────────────
  async function cargarTablaOperarios(){
    var box = document.getElementById('crew-mgmt-tabla');
    if(!box) return;
    try{
      var r = await fetch('/api/planta/operarios?incluir_inactivos=1');
      var d = await r.json();
      var ops = d.operarios || [];
      if(!ops.length){
        box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Sin operarios. Click "+ Nuevo operario".</div>';
        return;
      }
      var html = '<table style="width:100%;border-collapse:collapse;font-size:13px">' +
        '<thead><tr style="text-align:left;color:#64748b;border-bottom:1px solid #e2e8f0;background:#f8fafc">' +
        '<th style="padding:8px">Nombre</th>' +
        '<th style="padding:8px">Rol predeterminado</th>' +
        '<th style="padding:8px;text-align:center">Flags</th>' +
        '<th style="padding:8px;text-align:center">Estado</th>' +
        '<th style="padding:8px;text-align:right">Acciones</th>' +
        '</tr></thead><tbody>';
      ops.forEach(function(o){
        var flags = [];
        if(o.fija_dispensacion) flags.push('🔒 fijo dispensación');
        if(o.es_jefe) flags.push('⭐ jefe');
        var estado = o.activo
          ? '<span style="background:#d1fae5;color:#065f46;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">ACTIVO</span>'
          : '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">INACTIVO</span>';
        var btnDelOrEnable = o.activo
          ? '<button onclick="desactivarOperario('+o.id+',&quot;'+o.nombre_completo.replace(/"/g,'&quot;')+'&quot;)" style="background:#fee2e2;color:#991b1b;border:none;padding:5px 9px;border-radius:5px;font-size:11px;font-weight:600;cursor:pointer">Desactivar</button>'
          : '<button onclick="reactivarOperario('+o.id+')" style="background:#d1fae5;color:#065f46;border:none;padding:5px 9px;border-radius:5px;font-size:11px;font-weight:600;cursor:pointer">Reactivar</button>';
        html += '<tr style="border-bottom:1px solid #f1f5f9">' +
          '<td style="padding:8px;font-weight:600">'+_escHTML(o.nombre_completo)+'</td>' +
          '<td style="padding:8px;color:#475569">'+_escHTML(o.rol||'todero')+'</td>' +
          '<td style="padding:8px;text-align:center;font-size:11px;color:#64748b">'+(flags.join(' · ')||'—')+'</td>' +
          '<td style="padding:8px;text-align:center">'+estado+'</td>' +
          '<td style="padding:8px;text-align:right">' +
            '<button onclick="abrirModalEditarOperario('+o.id+')" style="background:#dbeafe;color:#1e40af;border:none;padding:5px 9px;border-radius:5px;font-size:11px;font-weight:600;cursor:pointer;margin-right:4px">Editar</button>' +
            btnDelOrEnable +
          '</td>' +
        '</tr>';
      });
      html += '</tbody></table>';
      box.innerHTML = html;
    }catch(e){ box.innerHTML = '<div style="color:#dc2626">Error al cargar.</div>'; }
  }

  function abrirModalNuevoOperario(){
    document.getElementById('op-modal-title').textContent = 'Nuevo operario';
    document.getElementById('op-id').value = '';
    document.getElementById('op-nombre').value = '';
    document.getElementById('op-apellido').value = '';
    document.getElementById('op-rol').value = 'todero';
    document.getElementById('op-fija').checked = false;
    document.getElementById('op-jefe').checked = false;
    document.getElementById('modal-operario').style.display = 'flex';
  }

  async function abrirModalEditarOperario(id){
    try{
      var r = await fetch('/api/planta/operarios?incluir_inactivos=1');
      var d = await r.json();
      var op = (d.operarios||[]).find(function(o){ return o.id === id; });
      if(!op){ _toast('No encontrado', 0); return; }
      document.getElementById('op-modal-title').textContent = 'Editar: '+op.nombre_completo;
      document.getElementById('op-id').value = op.id;
      document.getElementById('op-nombre').value = op.nombre;
      document.getElementById('op-apellido').value = op.apellido;
      document.getElementById('op-rol').value = op.rol || 'todero';
      document.getElementById('op-fija').checked = !!op.fija_dispensacion;
      document.getElementById('op-jefe').checked = !!op.es_jefe;
      document.getElementById('modal-operario').style.display = 'flex';
    }catch(e){ _toast('Error de red', 0); }
  }

  function cerrarModalOperario(){
    document.getElementById('modal-operario').style.display = 'none';
  }

  async function guardarOperario(){
    var id = document.getElementById('op-id').value;
    var body = {
      nombre: document.getElementById('op-nombre').value.trim(),
      apellido: document.getElementById('op-apellido').value.trim(),
      rol_predeterminado: document.getElementById('op-rol').value,
      fija_en_dispensacion: document.getElementById('op-fija').checked,
      es_jefe_produccion: document.getElementById('op-jefe').checked
    };
    if(!body.nombre){ _toast('Nombre requerido', 0); return; }
    try{
      var url = id ? '/api/planta/operarios/'+id : '/api/planta/operarios';
      var method = id ? 'PATCH' : 'POST';
      var r = await fetch(url, {method:method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
      var d = await r.json();
      if(d.ok){
        _toast(id?'Operario actualizado':'Operario creado', 1);
        cerrarModalOperario();
        cargarTablaOperarios();
        // Limpiar cache para que el próximo "Programar" lo incluya
        _PLANTA_OPERARIOS = null;
      }else{ _toast('Error: '+(d.error||'?'), 0); }
    }catch(e){ _toast('Error de red', 0); }
  }

  async function desactivarOperario(id, nombre){
    if(!confirm('¿Desactivar a '+nombre+'? No aparecerá en selectores nuevos pero el historial se preserva.')) return;
    try{
      var r = await fetch('/api/planta/operarios/'+id, {method:'DELETE'});
      var d = await r.json();
      if(d.ok){ _toast('Desactivado', 1); cargarTablaOperarios(); _PLANTA_OPERARIOS=null; }
      else { _toast('Error', 0); }
    }catch(e){ _toast('Error de red', 0); }
  }

  async function reactivarOperario(id){
    try{
      var r = await fetch('/api/planta/operarios/'+id, {
        method:'PATCH', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({activo: true})
      });
      var d = await r.json();
      if(d.ok){ _toast('Reactivado', 1); cargarTablaOperarios(); _PLANTA_OPERARIOS=null; }
      else { _toast('Error', 0); }
    }catch(e){ _toast('Error de red', 0); }
  }

  // Toggle del checkbox auto-refresh
  document.addEventListener('DOMContentLoaded', function(){
    var chk = document.getElementById('cm-auto');
    if(chk){ chk.addEventListener('change', function(){
      if(this.checked) cmStartAutoRefresh();
      else cmStopAutoRefresh();
    });}
    // PERF 6-jul (diag fable): NO cargar Necesidades en CADA apertura de la app · es el endpoint más pesado
    // (parsea velocidad) y casi siempre la pestaña Programación no está visible al arrancar. Se carga LAZY
    // cuando se abre Programación (showTab('programacion') → switchProgTab('necesidades'), línea ~4424).
  });

  // KPIs de actividades (turnos, horas por operario, por tipo)
  async function cargarKpisActividades(){
    var box = document.getElementById('cm-act-kpis');
    if(!box) return;
    try{
      var r = await fetch('/api/planta/actividades/kpis');
      var d = await r.json();
      var op = d.por_operario || [];
      var tp = d.por_tipo || [];
      var html = '';
      // Card resumen turnos activos ahora
      html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px">' +
          '<b style="color:#1a4a7a;font-size:14px">⏱ Turnos operarios</b>' +
          '<span style="font-size:11px;color:#64748b">📅 ' + (d.desde||'') + ' → ' + (d.hasta||'') + ' · Activos ahora: <b style="color:'+(d.turnos_activos_ahora>0?'#ca8a04':'#94a3b8')+'">' + (d.turnos_activos_ahora||0) + '</b></span>' +
        '</div>';
      if(op.length){
        html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px"><div>';
        html += '<div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Por operario</div>';
        html += '<table style="width:100%;font-size:12px;border-collapse:collapse">';
        op.forEach(function(o){
          var hrs = o.horas;
          var bar = Math.min(100, Math.round(hrs * 5));  // visual rough scale
          html += '<tr style="border-bottom:1px solid #f1f5f9">' +
            '<td style="padding:4px 0;font-weight:600">'+_escHTML(o.operario)+'</td>' +
            '<td style="padding:4px 0;color:#64748b;text-align:right">'+o.turnos+' turno'+(o.turnos===1?'':'s')+'</td>' +
            '<td style="padding:4px 0;text-align:right;font-weight:700;color:#6d28d9">'+hrs+'h</td>' +
            '</tr>';
        });
        html += '</table></div><div>';
        html += '<div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Por tipo de actividad</div>';
        html += '<table style="width:100%;font-size:12px;border-collapse:collapse">';
        var iconos = {produccion:'🏭',dispensacion:'⚖',envasado:'📦',acondicionamiento:'🎁',conteo_ciclico:'📊',limpieza:'🧹',mantenimiento:'🔧',otro:'📋'};
        tp.forEach(function(t){
          html += '<tr style="border-bottom:1px solid #f1f5f9">' +
            '<td style="padding:4px 0">'+(iconos[t.tipo]||'📋')+' '+t.tipo+'</td>' +
            '<td style="padding:4px 0;color:#64748b;text-align:right">'+t.turnos+' turno'+(t.turnos===1?'':'s')+'</td>' +
            '<td style="padding:4px 0;text-align:right;font-weight:700;color:#6d28d9">'+t.horas+'h</td>' +
            '</tr>';
        });
        html += '</table></div></div>';
      } else {
        html += '<div style="text-align:center;color:#94a3b8;padding:20px;font-size:13px;font-style:italic">' +
          'Aún sin turnos cerrados en los últimos 30 días — inicia un turno desde cualquier sala para empezar a medir.' +
          '</div>';
      }
      html += '</div>';
      box.innerHTML = html;
    }catch(e){ box.innerHTML = ''; }
  }

  // Capa 4: rotación operarios — pinta panel debajo del plano
  async function cargarRotacionOperarios(){
    var box = document.getElementById('plano-rotacion');
    if(!box) return;
    try{
      var r = await fetch('/api/planta/operarios/historial');
      var d = await r.json();
      var ops = d.operarios || [];
      if(!ops.length){
        box.innerHTML = '';
        return;
      }
      var html = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:14px 16px">' +
        '<h3 style="margin:0 0 10px;color:#1a4a7a;font-size:15px">👥 Rotación de operarios <span style="font-size:11px;color:#64748b;font-weight:500">(últimos '+(d.ventana_dias||14)+' días)</span></h3>' +
        '<table style="width:100%;border-collapse:collapse;font-size:12px"><thead>' +
          '<tr style="text-align:left;color:#64748b;border-bottom:1px solid #e2e8f0">' +
            '<th style="padding:6px 4px">Operario</th>' +
            '<th style="padding:6px 4px;text-align:center">Disp</th>' +
            '<th style="padding:6px 4px;text-align:center">Elab</th>' +
            '<th style="padding:6px 4px;text-align:center">Env</th>' +
            '<th style="padding:6px 4px;text-align:center">Acon</th>' +
            '<th style="padding:6px 4px">Sugerencia</th>' +
          '</tr></thead><tbody>';
      ops.forEach(function(op){
        var f = op.fases || {};
        var rotar = op.sugerir_rotar
          ? '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:8px;font-weight:700">⚠ rotar — '+op.dias_en_fase+' días en '+op.fase_acumulada+'</span>'
          : '<span style="color:#16a34a">✓ ok</span>';
        function _cell(n){ return '<td style="padding:6px 4px;text-align:center;color:'+(n?'#0f172a':'#cbd5e1')+';font-weight:'+(n?'700':'400')+'">'+(n||0)+'</td>'; }
        html += '<tr style="border-bottom:1px solid #f1f5f9"><td style="padding:6px 4px;font-weight:600">'+op.nombre+' '+(op.apellido||'')+'</td>' +
          _cell(f.dispensacion) + _cell(f.elaboracion) + _cell(f.envasado) + _cell(f.acondicionamiento) +
          '<td style="padding:6px 4px">'+rotar+'</td></tr>';
      });
      html += '</tbody></table></div>';
      box.innerHTML = html;
    }catch(e){
      box.innerHTML = '';
    }
  }

  async function cargarTareasOperativas(){
    var lista = document.getElementById('tareas-op-lista');
    if(!lista) return;
    lista.innerHTML = '<div style="color:#94a3b8;text-align:center;padding:20px">Cargando...</div>';
    try {
      // Sebastian (29-abr-2026): /planta solo muestra tareas fisicas de planta
      // (excluye chat_asignacion como "Cargar influencers" que era para Jeferson).
      var r = await fetch('/api/tareas-operativas?contexto=planta');
      var d = await r.json();
      var tareas = d.tareas || [];
      var badge = document.getElementById('prog-tareas-badge');
      if(badge){
        var pend = tareas.filter(function(t){return t.estado==='pendiente'||t.estado==='en_progreso'}).length;
        if(pend){ badge.textContent = pend; badge.style.display='inline-block'; }
        else badge.style.display = 'none';
      }
      if(!tareas.length){
        lista.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:40px;font-size:13px">Sin tareas operativas pendientes 🎉</div>';
        return;
      }
      lista.innerHTML = tareas.map(function(t){
        var tipoColors = {sacar_envases_serigrafia:'#7c3aed',sacar_envases_tampografia:'#7c3aed',sacar_inventario:'#16a34a',envasado:'#7c3aed',etiquetado:'#d97706',general:'#64748b'};
        var col = tipoColors[t.tipo]||'#64748b';
        var estCol = t.estado==='pendiente'?'#dc2626':t.estado==='en_progreso'?'#d97706':t.estado==='completada'?'#15803d':'#94a3b8';
        var fechaObj = t.fecha_objetivo?'<span style="color:#dc2626;font-size:11px;font-weight:700">📅 '+_escHTML(t.fecha_objetivo)+'</span>':'';
        return '<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+col+';border-radius:10px;padding:14px 18px;margin-bottom:10px;display:grid;grid-template-columns:1fr auto;gap:14px;align-items:center">'+
          '<div>'+
            '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">'+
              '<span style="font-weight:700;color:#0f172a;font-size:14px">'+_escHTML(t.titulo)+'</span>'+
              '<span style="background:'+col+'22;color:'+col+';font-size:10px;font-weight:700;padding:2px 8px;border-radius:8px">'+_escHTML(t.tipo||'')+'</span>'+
              '<span style="background:'+estCol+'22;color:'+estCol+';font-size:10px;font-weight:700;padding:2px 8px;border-radius:8px;text-transform:uppercase">'+_escHTML(t.estado)+'</span>'+
            '</div>'+
            '<div style="font-size:13px;color:#475569;margin-top:6px">'+_escHTML(t.descripcion||'')+'</div>'+
            '<div style="font-size:11px;color:#64748b;margin-top:4px">'+
              (t.producto_relacionado?'📦 <b>'+_escHTML(t.producto_relacionado)+'</b> · ':'')+
              (t.cantidad>0?'🔢 '+Math.round(t.cantidad).toLocaleString('es-CO')+' und · ':'')+
              (t.asignado_a?'👥 '+_escHTML(t.asignado_a)+' · ':'')+
              fechaObj +
            '</div>'+
          '</div>'+
          '<div style="text-align:right">'+
            (t.estado==='pendiente'||t.estado==='en_progreso' ? '<button onclick="completarTareaOp('+t.id+')" style="background:#16a34a;color:#fff;border:none;border-radius:6px;padding:7px 14px;font-size:12px;font-weight:700;cursor:pointer">✓ Completar</button>' : '') +
          '</div>'+
        '</div>';
      }).join('');
    } catch(e){
      lista.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  async function completarTareaOp(tid){
    var obs = prompt('Observaciones del cierre (opcional):', '') || '';
    try {
      var r = await fetch('/api/tareas-operativas/'+tid+'/completar', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({observaciones: obs})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
      _toast('Tarea completada', 1);
      cargarTareasOperativas();
    } catch(e){ alert('Error: '+e.message); }
  }

  // ── Fase 0: Presentaciones por Producto ──────────────────────────────
  // Sebastian + Alejandro (30-abr-2026): suero 30/15/10mL, contornos 15/10mL,
  // maxlash 4.5mL, blush 6g. Sin esto, planear "produzcamos para 2 meses"
  // es ambiguo. UI lista + crea + aplica plantillas por categoría.
  var _presProductos = [];

  async function cargarPresentaciones(){
    var lista = document.getElementById('pres-lista');
    var kpis  = document.getElementById('pres-kpis');
    var banner= document.getElementById('pres-cobertura-banner');
    if(!lista) return;
    lista.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r1 = await fetch('/api/planta/presentaciones');
      var d1 = await r1.json();
      var r2 = await fetch('/api/planta/presentaciones/productos-disponibles');
      var d2 = await r2.json();
      _presProductos = d2.productos || [];

      // KPIs
      var totalPres = (d1.presentaciones||[]).length;
      var totalProd = _presProductos.length;
      var prodConPres = _presProductos.filter(function(p){return (p.n_presentaciones||0)>0}).length;
      var sinPres = totalProd - prodConPres;
      var pct = totalProd ? Math.round(prodConPres/totalProd*100) : 0;
      kpis.innerHTML = ''
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">Productos en BD</div><div style="font-size:24px;font-weight:800;color:#0f172a">'+totalProd+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">Con presentación</div><div style="font-size:24px;font-weight:800;color:#15803d">'+prodConPres+' <span style="font-size:13px;color:#64748b">('+pct+'%)</span></div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">Sin presentación</div><div style="font-size:24px;font-weight:800;color:'+(sinPres?'#dc2626':'#15803d')+'">'+sinPres+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">Total presentaciones</div><div style="font-size:24px;font-weight:800;color:#0f172a">'+totalPres+'</div></div>';

      if(sinPres > 0){
        banner.style.display = 'block';
        banner.innerHTML = '⚠ Hay <b>'+sinPres+' productos sin presentación</b> definida. Sin esto el sistema no puede sugerir tamaño de lote correcto. Usa "Aplicar plantilla" o "+ Nueva presentación" para completarlos.';
      } else {
        banner.style.display = 'none';
      }

      // Lista agrupada por producto
      if(!totalProd){
        lista.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px">No hay productos en formula_headers</div>';
        return;
      }
      var byProd = d1.por_producto || {};
      var html = '';
      _presProductos.forEach(function(prod){
        var pres = byProd[prod.producto_nombre] || [];
        var color = pres.length ? '#15803d' : '#dc2626';
        var status = pres.length ? '✓ '+pres.length+' presentación'+(pres.length>1?'es':'') : '⚠ sin presentación';
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+color+';border-radius:10px;padding:14px 16px">'
          +'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">'
          +'<div><b style="color:#0f172a">'+_escHTML(prod.producto_nombre)+'</b> <span style="color:#64748b;font-size:12px;margin-left:6px">lote '+(prod.lote_size_kg||0)+' kg</span></div>'
          +'<div style="font-size:12px;color:'+color+';font-weight:700">'+status+'</div>'
          +'</div>';
        if(pres.length){
          html += '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:10px">';
          pres.forEach(function(p){
            var vol = p.volumen_ml ? p.volumen_ml+' mL' : (p.peso_g ? p.peso_g+' g' : '');
            html += '<div style="background:#f0fdf4;border:1px solid #86efac;color:#166534;padding:6px 10px;border-radius:6px;font-size:12px;display:flex;align-items:center;gap:6px">'
              +'<b>'+_escHTML(p.etiqueta)+'</b>'
              +(vol?'<span style="color:#64748b">·</span><span>'+vol+'</span>':'')
              +(p.envase_codigo?'<span style="color:#64748b">·</span><span style="font-family:monospace;font-size:11px">'+_escHTML(p.envase_codigo)+'</span>':'')
              +' <button onclick="eliminarPresentacion('+p.id+')" title="Eliminar" style="background:transparent;border:none;color:#dc2626;cursor:pointer;font-weight:700;padding:0 2px">×</button>'
              +'</div>';
          });
          html += '</div>';
        } else {
          html += '<div style="margin-top:8px;display:flex;gap:6px"><button onclick="abrirAplicarPlantilla(\''+_escAttr(prod.producto_nombre)+'\')" style="background:#1a4a7a;color:#fff;border:none;padding:5px 12px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">🏭 Plantilla</button>'
            +'<button onclick="abrirNuevaPresentacion(\''+_escAttr(prod.producto_nombre)+'\')" style="background:#6d28d9;color:#fff;border:none;padding:5px 12px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">+ Manual</button></div>';
        }
        html += '</div>';
      });
      lista.innerHTML = html;
    } catch(e){
      lista.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  function _escAttr(s){ return (s==null?'':String(s)).replace(/'/g, "&#39;").replace(/"/g, '&quot;'); }

  function _llenarSelectProductos(selId, valorPreset){
    var sel = document.getElementById(selId);
    if(!sel) return;
    sel.innerHTML = '<option value="">— elegir producto —</option>'
      + _presProductos.map(function(p){
        var sel = (p.producto_nombre===valorPreset) ? ' selected' : '';
        return '<option value="'+_escAttr(p.producto_nombre)+'"'+sel+'>'+_escHTML(p.producto_nombre)+'</option>';
      }).join('');
  }

  function abrirNuevaPresentacion(productoPreset){
    _llenarSelectProductos('pres-producto', productoPreset||'');
    ['pres-categoria','pres-codigo','pres-etiqueta','pres-volumen','pres-peso','pres-envase','pres-tapa','pres-caja','pres-sku','pres-notas'].forEach(function(id){
      var el = document.getElementById(id); if(el) el.value = '';
    });
    var m = document.getElementById('modal-pres-nueva');
    m.style.display = 'flex';
  }
  function cerrarPresModal(){ document.getElementById('modal-pres-nueva').style.display='none'; }

  async function guardarPresentacion(){
    var body = {
      producto_nombre: (document.getElementById('pres-producto').value||'').trim(),
      categoria: (document.getElementById('pres-categoria').value||'').trim(),
      presentacion_codigo: (document.getElementById('pres-codigo').value||'').trim(),
      etiqueta: (document.getElementById('pres-etiqueta').value||'').trim(),
      volumen_ml: parseFloat(document.getElementById('pres-volumen').value)||null,
      peso_g: parseFloat(document.getElementById('pres-peso').value)||null,
      envase_codigo: (document.getElementById('pres-envase').value||'').trim(),
      tapa_codigo: (document.getElementById('pres-tapa').value||'').trim(),
      caja_codigo: (document.getElementById('pres-caja').value||'').trim(),
      sku_shopify: (document.getElementById('pres-sku').value||'').trim(),
      notas: (document.getElementById('pres-notas').value||'').trim(),
    };
    if(!body.producto_nombre){ alert('Producto requerido'); return; }
    if(!body.presentacion_codigo){ alert('Código de presentación requerido'); return; }
    if(!body.etiqueta){ alert('Etiqueta requerida'); return; }
    try {
      var r = await fetch('/api/planta/presentaciones', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body)
      });
      var d = await r.json().catch(function(){return {};});
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
      cerrarPresModal();
      _toast('Presentación creada', 1);
      cargarPresentaciones();
    } catch(e){ alert('Error de red: '+e.message); }
  }

  function abrirAplicarPlantilla(productoPreset){
    _llenarSelectProductos('plt-producto', productoPreset||'');
    document.getElementById('plt-categoria').value = '';
    document.getElementById('modal-pres-plantilla').style.display = 'flex';
  }
  function cerrarPlantillaModal(){ document.getElementById('modal-pres-plantilla').style.display='none'; }

  async function aplicarPlantilla(){
    var prod = (document.getElementById('plt-producto').value||'').trim();
    var cat  = (document.getElementById('plt-categoria').value||'').trim();
    if(!prod || !cat){ alert('Producto y categoría requeridos'); return; }
    try {
      var r = await fetch('/api/planta/presentaciones/bulk-categoria', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({producto_nombre: prod, categoria: cat})
      });
      var d = await r.json().catch(function(){return {};});
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
      cerrarPlantillaModal();
      _toast('Plantilla aplicada · '+(d.total||0)+' presentaciones creadas', 1);
      cargarPresentaciones();
    } catch(e){ alert('Error de red: '+e.message); }
  }

  async function eliminarPresentacion(pid){
    if(!confirm('¿Eliminar (desactivar) esta presentación?')) return;
    try {
      var r = await fetch('/api/planta/presentaciones/'+pid, {method:'DELETE'});
      var d = await r.json().catch(function(){return {};});
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
      cargarPresentaciones();
    } catch(e){ alert('Error de red: '+e.message); }
  }

  // ── Fase 1: Equipos del Excel + sugerir-área ─────────────────────────
  var _eqTodos = [];
  var _eqTipos = {};
  var _eqAreas = {};

  async function cargarEquipos(){
    var lista = document.getElementById('eq-lista');
    if(!lista) return;
    lista.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r = await fetch('/api/planta/equipos');
      var d = await r.json();
      _eqTodos = d.equipos || [];
      _eqTipos = d.por_tipo || {};
      // Por area
      var porArea = d.por_area || {};
      _eqAreas = porArea;

      // KPIs
      var kpis = document.getElementById('eq-kpis');
      var nTanques = _eqTodos.filter(function(e){return e.tipo==='tanque'||e.tipo==='marmita'||e.tipo==='olla'}).length;
      var nEnvas   = _eqTodos.filter(function(e){return e.tipo==='envasadora'||e.tipo==='tapadora'}).length;
      var nMedida  = _eqTodos.filter(function(e){return ['balanza','bascula','viscosimetro','phmetro','espectrofotometro','termometro','termohigrometro','pie_de_rey','picnometro','pesa_patron'].indexOf(e.tipo)>=0}).length;
      var nMezcla  = _eqTodos.filter(function(e){return ['agitador','homogenizador','mezclador','batidor','molino','plancha'].indexOf(e.tipo)>=0}).length;
      kpis.innerHTML = ''
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Total</div><div style="font-size:24px;font-weight:800;color:#0f172a">'+_eqTodos.length+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Tanques/marmitas</div><div style="font-size:24px;font-weight:800;color:#1a4a7a">'+nTanques+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Envasado</div><div style="font-size:24px;font-weight:800;color:#7c3aed">'+nEnvas+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Mezcla</div><div style="font-size:24px;font-weight:800;color:#7c3aed">'+nMezcla+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Medición/CC</div><div style="font-size:24px;font-weight:800;color:#16a34a">'+nMedida+'</div></div>';

      // Llenar selects de filtro
      var selT = document.getElementById('eq-filtro-tipo');
      var selA = document.getElementById('eq-filtro-area');
      var tiposSorted = Object.keys(_eqTipos).sort();
      selT.innerHTML = '<option value="">Todos los tipos ('+_eqTodos.length+')</option>'
        + tiposSorted.map(function(t){ return '<option value="'+t+'">'+t+' ('+_eqTipos[t]+')</option>'; }).join('');
      var areasSorted = Object.keys(porArea).sort();
      selA.innerHTML = '<option value="">Todas las áreas</option>'
        + areasSorted.map(function(a){ return '<option value="'+a+'">'+a+' ('+(porArea[a].length)+')</option>'; }).join('');

      filtrarEquipos();
    } catch(e){
      lista.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  function filtrarEquipos(){
    var lista = document.getElementById('eq-lista');
    var q = (document.getElementById('eq-search').value||'').toLowerCase();
    var ft = (document.getElementById('eq-filtro-tipo').value||'').toLowerCase();
    var fa = (document.getElementById('eq-filtro-area').value||'');
    var filtered = _eqTodos.filter(function(e){
      if(ft && (e.tipo||'').toLowerCase()!==ft) return false;
      if(fa && (e.area_codigo||'')!==fa) return false;
      if(q){
        var t = ((e.codigo||'')+' '+(e.nombre||'')+' '+(e.capacidad_raw||'')+' '+(e.area_codigo||'')+' '+(e.ubicacion_raw||'')).toLowerCase();
        if(t.indexOf(q)<0) return false;
      }
      return true;
    });
    if(!filtered.length){
      lista.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px">Sin resultados.</div>';
      return;
    }
    // Agrupar por area
    var grupos = {};
    filtered.forEach(function(e){
      var a = e.area_codigo || '—';
      grupos[a] = grupos[a] || [];
      grupos[a].push(e);
    });
    var html = '';
    Object.keys(grupos).sort().forEach(function(a){
      var eqs = grupos[a];
      html += '<div style="margin-bottom:14px"><h3 style="margin:0 0 8px;color:#1a4a7a;font-size:14px">'+a+' <span style="color:#64748b;font-size:11px;font-weight:500">('+eqs.length+' equipos)</span></h3>'
        +'<table style="width:100%;border-collapse:collapse;background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden"><thead><tr style="background:#f1f5f9"><th style="padding:8px 12px;text-align:left;font-size:11px;color:#475569;text-transform:uppercase">Código</th><th style="padding:8px 12px;text-align:left;font-size:11px;color:#475569;text-transform:uppercase">Nombre</th><th style="padding:8px 12px;text-align:left;font-size:11px;color:#475569;text-transform:uppercase">Tipo</th><th style="padding:8px 12px;text-align:right;font-size:11px;color:#475569;text-transform:uppercase">Capacidad</th></tr></thead><tbody>';
      eqs.forEach(function(e){
        var capStr = e.capacidad_raw || '—';
        if(e.capacidad_litros){ capStr = e.capacidad_litros+' L'; }
        else if(e.capacidad_kg){ capStr = e.capacidad_kg+' kg'; }
        html += '<tr style="border-top:1px solid #e2e8f0"><td style="padding:7px 12px;font-family:monospace;font-size:12px;color:#1e293b">'+_escHTML(e.codigo)+'</td><td style="padding:7px 12px;font-size:13px">'+_escHTML(e.nombre||'')+'</td><td style="padding:7px 12px;font-size:11px"><span style="background:#ede9fe;color:#5b21b6;padding:2px 7px;border-radius:8px;font-weight:600">'+_escHTML(e.tipo||'otro')+'</span></td><td style="padding:7px 12px;font-size:12px;text-align:right;color:#0f172a;font-weight:600">'+_escHTML(capStr)+'</td></tr>';
      });
      html += '</tbody></table></div>';
    });
    lista.innerHTML = html;
  }

  function abrirSugerirArea(){
    document.getElementById('sa-producto').value = '';
    document.getElementById('sa-lote').value = '';
    document.getElementById('sa-resultado').innerHTML = '';
    document.getElementById('modal-sugerir-area').style.display = 'flex';
  }
  function cerrarSugerirArea(){ document.getElementById('modal-sugerir-area').style.display='none'; }

  async function ejecutarSugerirArea(){
    var prod = (document.getElementById('sa-producto').value||'').trim() || 'Producto X';
    var lote = parseFloat(document.getElementById('sa-lote').value);
    if(!lote || lote<=0){ alert('Tamaño de lote requerido (kg)'); return; }
    var box = document.getElementById('sa-resultado');
    box.innerHTML = '<div style="color:#94a3b8;padding:14px;text-align:center">Calculando...</div>';
    try {
      var r = await fetch('/api/planta/sugerir-area', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({producto_nombre: prod, lote_kg: lote})
      });
      var d = await r.json();
      if(!r.ok){ box.innerHTML='<div style="color:#dc2626;padding:14px">'+(d.error||'Error')+'</div>'; return; }
      var sugerencias = d.sugerencias||[];
      var html = '<div style="background:#f8fafc;border:1px solid #e2e8f0;padding:10px 14px;border-radius:6px;margin-bottom:10px;font-size:12px;color:#475569">📊 '+_escHTML(d.mensaje)+'</div>';
      if(!sugerencias.length){
        box.innerHTML = html;
        return;
      }
      sugerencias.forEach(function(s, i){
        var medal = i===0 ? '🥇' : i===1 ? '🥈' : i===2 ? '🥉' : '·';
        var color = i===0 ? '#15803d' : '#64748b';
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+color+';border-radius:8px;padding:12px 14px;margin-bottom:8px">'
          +'<div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:6px">'
          +'<div><b style="color:#0f172a;font-size:14px">'+medal+' '+_escHTML(s.area_nombre)+'</b> <span style="font-family:monospace;color:#64748b;font-size:11px">('+_escHTML(s.area_codigo)+')</span></div>'
          +'<div style="font-size:13px;font-weight:700;color:'+color+'">Score '+s.score+'</div>'
          +'</div>'
          +'<div style="margin-top:6px;font-size:12px;color:#475569">🛢 '+_escHTML(s.tanque.tanque_nombre)+' <span style="color:#64748b">('+_escHTML(s.tanque.tanque_codigo)+')</span> · '+s.tanque.capacidad_litros+'L · uso '+s.utilizacion_pct+'%</div>'
          +(s.envasado_sugerido?'<div style="margin-top:4px;font-size:11px;color:#7c3aed">📦 Envasado sugerido: '+s.envasado_sugerido+'</div>':'')
          +'<div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:4px">'
          +(s.razones||[]).map(function(r){ return '<span style="background:#f1f5f9;color:#475569;font-size:11px;padding:2px 8px;border-radius:8px">'+_escHTML(r)+'</span>'; }).join('')
          +'</div></div>';
      });
      box.innerHTML = html;
    } catch(e){ box.innerHTML='<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>'; }
  }

  // ── Fase 2: Pre-flight (motor de gates) ──────────────────────────────
  // Sebastian (30-abr-2026): "programado un producto dice donde como, le dice
  // inteligentemente area sucia confirmar limpieza confirmar tal y tal cosa".
  async function cargarPreflightLista(){
    var lista = document.getElementById('pf-lista');
    var kpis  = document.getElementById('pf-kpis');
    if(!lista) return;
    lista.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando producciones próximas...</div>';
    try {
      // Reusar /api/programar para obtener producciones próximas
      var r = await fetch('/api/programacion/programar?dias=14');
      var d = await r.json();
      var eventos = d.eventos || d.items || [];
      // Filtrar las que tienen produccion_id (de produccion_programada local)
      var producciones = eventos.filter(function(e){return e.id && e.estado!=='completado' && e.estado!=='cancelado'});

      // Para cada produccion, llamar a /preflight (paralelo limit 5)
      var conGates = [];
      for(var i=0;i<producciones.length;i+=5){
        var batch = producciones.slice(i, i+5);
        var res = await Promise.all(batch.map(function(p){
          return fetch('/api/planta/preflight/'+p.id).then(function(r){return r.json()}).catch(function(){return null});
        }));
        res.forEach(function(pf, idx){
          if(pf && pf.gates) conGates.push(Object.assign({}, batch[idx], {preflight: pf}));
        });
      }

      // KPIs
      var nListos = conGates.filter(function(p){return p.preflight.listo && p.preflight.resumen.warn===0}).length;
      var nWarn   = conGates.filter(function(p){return p.preflight.listo && p.preflight.resumen.warn>0}).length;
      var nBlock  = conGates.filter(function(p){return !p.preflight.listo}).length;
      kpis.innerHTML = ''
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #6b7280;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Total programadas</div><div style="font-size:24px;font-weight:800;color:#0f172a">'+conGates.length+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #15803d;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Listas para iniciar</div><div style="font-size:24px;font-weight:800;color:#15803d">'+nListos+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #d97706;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Con advertencias</div><div style="font-size:24px;font-weight:800;color:#d97706">'+nWarn+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #dc2626;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Bloqueadas</div><div style="font-size:24px;font-weight:800;color:#dc2626">'+nBlock+'</div></div>';

      if(!conGates.length){
        lista.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px;background:#f8fafc;border-radius:10px">Sin producciones programadas próximas (14d).</div>';
        return;
      }

      var html = '';
      conGates.forEach(function(p){
        var pf = p.preflight;
        var color = pf.resumen.blocker>0 ? '#dc2626' : (pf.resumen.warn>0 ? '#d97706' : '#15803d');
        var badge = pf.resumen.blocker>0 ? '⛔ BLOQUEADA' : (pf.resumen.warn>0 ? '⚠ Con advertencias' : '✅ LISTA');
        html += '<div onclick="abrirPreflightModal('+p.id+')" style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+color+';border-radius:10px;padding:14px 18px;margin-bottom:10px;cursor:pointer;display:grid;grid-template-columns:1fr auto;gap:14px;align-items:center" onmouseover="this.style.background=\'#f8fafc\'" onmouseout="this.style.background=\'#fff\'">'
          +'<div>'
          +'<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><b style="color:#0f172a;font-size:14px">'+_escHTML(p.titulo||p.producto||'Producción '+p.id)+'</b>'
          +'<span style="background:'+color+'22;color:'+color+';font-size:11px;font-weight:700;padding:2px 8px;border-radius:8px">'+badge+'</span></div>'
          +'<div style="font-size:12px;color:#64748b;margin-top:4px">📅 '+_escHTML(p.fecha_inicio||p.fecha_programada||'')+(p.lotes?' · '+p.lotes+' lote(s)':'')+'</div>'
          +'<div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap">'
          +pf.gates.map(function(g){
            var col = g.status==='blocker'?'#dc2626':(g.status==='warn'?'#d97706':'#15803d');
            var ic  = g.status==='blocker'?'⛔':(g.status==='warn'?'⚠':'✓');
            return '<span style="background:'+col+'18;color:'+col+';padding:3px 8px;border-radius:6px;font-size:11px;font-weight:600">'+ic+' '+_escHTML(g.titulo)+'</span>';
          }).join('')
          +'</div></div>'
          +'<div style="text-align:right;color:'+color+';font-size:24px">→</div>'
          +'</div>';
      });
      lista.innerHTML = html;
    } catch(e){
      lista.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  async function abrirPreflightModal(prodId){
    var modal = document.getElementById('modal-preflight');
    var hdr = document.getElementById('pf-modal-header');
    var body = document.getElementById('pf-modal-gates');
    hdr.innerHTML = '<div style="color:#94a3b8">Cargando...</div>';
    body.innerHTML = '';
    modal.style.display = 'flex';
    try {
      var r = await fetch('/api/planta/preflight/'+prodId);
      var pf = await r.json();
      var color = pf.resumen.blocker>0?'#dc2626':(pf.resumen.warn>0?'#d97706':'#15803d');
      hdr.innerHTML = '<div style="margin-bottom:14px">'
        +'<h3 style="margin:0 0 4px;color:'+color+';font-size:16px">'+_escHTML(pf.veredicto)+'</h3>'
        +'<div style="font-size:13px;color:#475569"><b>'+_escHTML(pf.producto||'')+'</b> · '+(pf.lotes||1)+' lote(s) · 📅 '+_escHTML(pf.fecha_programada||'')+'</div>'
        +'<div style="font-size:11px;color:#64748b;margin-top:4px">Producción ID '+pf.produccion_id+' · estado: '+_escHTML(pf.estado||'')+'</div>'
        +'</div>';
      body.innerHTML = pf.gates.map(function(g){
        var col = g.status==='blocker'?'#dc2626':(g.status==='warn'?'#d97706':'#15803d');
        var bg  = g.status==='blocker'?'#fef2f2':(g.status==='warn'?'#fffbeb':'#f0fdf4');
        var ic  = g.status==='blocker'?'⛔':(g.status==='warn'?'⚠':'✅');
        var meta = '';
        if(g.meta && g.meta.deficit){
          meta = '<ul style="margin:6px 0 0;padding-left:18px;font-size:12px;color:#475569">'
            + g.meta.deficit.map(function(m){ return '<li>'+_escHTML(m.nombre)+': falta '+m.faltante_g+'g</li>'; }).join('')
            + '</ul>';
        } else if(g.meta && g.meta.items){
          meta = '<ul style="margin:6px 0 0;padding-left:18px;font-size:12px;color:#475569">'
            + g.meta.items.map(function(it){
                var s = it.stock!=null ? ' · stock '+it.stock : '';
                return '<li>'+_escHTML(it.presentacion)+(it.envase?' · '+_escHTML(it.envase):'')+s+'</li>';
              }).join('')
            + '</ul>';
        }
        var btn = '';
        if(g.accion === 'confirmar_limpieza'){
          btn = '<button onclick="confirmarLimpiezaPF('+prodId+')" style="margin-top:8px;background:'+col+';color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">🧹 Confirmar limpieza profunda</button>';
        } else if(g.accion === 'asignar_area'){
          btn = '<div style="margin-top:8px;font-size:11px;color:#64748b">→ Ve a Centro de Mando para asignar área</div>';
        } else if(g.accion === 'crear_tareas_compra'){
          btn = '<div style="margin-top:8px;font-size:11px;color:#64748b">→ Catalina puede ver el déficit en /compras</div>';
        }
        return '<div style="background:'+bg+';border:1px solid '+col+'33;border-left:4px solid '+col+';border-radius:8px;padding:12px 14px;margin-bottom:8px">'
          +'<div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:6px">'
          +'<div><b style="color:'+col+'">'+ic+' '+_escHTML(g.titulo)+'</b><div style="font-size:12px;color:#475569;margin-top:2px">'+_escHTML(g.mensaje||'')+'</div></div>'
          +'<span style="font-family:monospace;color:#94a3b8;font-size:10px">'+_escHTML(g.gate)+'</span>'
          +'</div>'
          + meta + btn
          +'</div>';
      }).join('');
    } catch(e){
      body.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }
  function cerrarPreflightModal(){ document.getElementById('modal-preflight').style.display='none'; }

  async function confirmarLimpiezaPF(prodId){
    var nota = prompt('Nota de la limpieza (opcional):', '');
    if(nota===null) return;
    try {
      var r = await fetch('/api/planta/preflight/'+prodId+'/confirmar-limpieza', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({nota: nota||''})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
      _toast('Limpieza profunda registrada', 1);
      // Refrescar el modal
      abrirPreflightModal(prodId);
    } catch(e){ alert('Error: '+e.message); }
  }

  // ── Fase 4: Plan Semanal con flujo guiado completo ───────────────────
  // Sebastian (30-abr-2026): "tenemos algo maravilloso allí en planta...
  // entonces lo selecciona le sale con la foto, y de una sale señalar
  // envases, solicitar etiquetas, armado de goteros si requiere, aceptar
  // producción se dispone para realizar, entonces automáticamente pasa a
  // que el sistema decida en que área se hace y genere todo".
  var _PS_DATA = null;

  async function cargarPlanSemanal(){
    var grid = document.getElementById('ps-grid');
    var kpis = document.getElementById('ps-kpis');
    var alertasBox = document.getElementById('ps-alertas');
    if(!grid) return;
    var dias = (document.getElementById('ps-dias')||{value:14}).value;
    grid.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px;grid-column:1/-1">Cargando plan semanal...</div>';
    try {
      var r = await fetch('/api/planta/plan-semanal?dias='+dias);
      var d = await r.json();
      _PS_DATA = d;
      // KPIs
      var k = d.kpis || {};
      kpis.innerHTML = ''
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Producciones</div><div style="font-size:26px;font-weight:800;color:#0f172a">'+(k.total||0)+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(k.alerta_roja_dias?'#dc2626':'#15803d')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Alerta días &lt;10</div><div style="font-size:26px;font-weight:800;color:'+(k.alerta_roja_dias?'#dc2626':'#15803d')+'">'+(k.alerta_roja_dias||0)+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(k.alerta_amarilla_dias?'#d97706':'#15803d')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Alerta días &lt;20</div><div style="font-size:26px;font-weight:800;color:'+(k.alerta_amarilla_dias?'#d97706':'#15803d')+'">'+(k.alerta_amarilla_dias||0)+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(k.sin_mp_suficiente?'#dc2626':'#15803d')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Sin MP suficiente</div><div style="font-size:26px;font-weight:800;color:'+(k.sin_mp_suficiente?'#dc2626':'#15803d')+'">'+(k.sin_mp_suficiente||0)+'</div></div>';

      // Banner de alertas críticas
      var critic = (d.items||[]).filter(function(it){return it.alerta_dias==='rojo' || !it.alcanza_mp});
      if(critic.length){
        alertasBox.style.display = 'block';
        alertasBox.innerHTML = '<b>⚠ '+critic.length+' producción(es) con alerta crítica:</b><br>'
          + critic.slice(0,5).map(function(c){
            var ico = !c.alcanza_mp ? '🔴 sin MP' : '⏰ '+c.dias_inventario+'d';
            return '· <b>'+_escHTML(c.producto)+'</b> ('+_escHTML(c.fecha_programada)+') '+ico;
          }).join('<br>');
      } else {
        alertasBox.style.display = 'none';
      }

      // Cards
      var items = d.items || [];
      if(!items.length){
        grid.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:40px;grid-column:1/-1;background:#f8fafc;border-radius:10px">Sin producciones programadas en el rango.</div>';
        return;
      }
      grid.innerHTML = items.map(function(it){
        var diasCol = it.alerta_dias==='rojo' ? '#dc2626' : (it.alerta_dias==='amarillo'?'#d97706':(it.alerta_dias==='verde'?'#15803d':'#94a3b8'));
        var diasTxt = it.dias_inventario===null ? '—' : it.dias_inventario+'d';
        var mpCol = it.alcanza_mp ? '#15803d' : '#dc2626';
        var mpTxt = it.alcanza_mp ? '✓ MP listas' : '✗ Faltan '+(it.mp_deficit||[]).length+' MP';
        var img = it.imagen_url
          ? '<img loading="lazy" decoding="async" src="'+_escAttr(it.imagen_url)+'" style="width:100%;height:120px;object-fit:cover;border-radius:8px 8px 0 0" alt="">'
          : '<div style="width:100%;height:120px;background:linear-gradient(135deg,#1a4a7a,#7c3aed);border-radius:8px 8px 0 0;display:flex;align-items:center;justify-content:center;color:#fff;font-size:36px">📦</div>';
        var pres = (it.presentaciones||[]).slice(0,2).map(function(p){
          return '<span style="background:#f0f9ff;color:#0369a1;padding:2px 8px;border-radius:8px;font-size:11px;font-weight:600">'+_escHTML(p.etiqueta)+'</span>';
        }).join(' ');
        return '<div onclick="abrirPlanSemModal('+it.produccion_id+')" style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;cursor:pointer;transition:transform .12s,box-shadow .12s" onmouseover="this.style.transform=\'translateY(-2px)\';this.style.boxShadow=\'0 8px 20px rgba(0,0,0,.1)\'" onmouseout="this.style.transform=\'\';this.style.boxShadow=\'\'">'
          + img
          +'<div style="padding:12px 14px">'
          +'<div style="font-weight:800;color:#0f172a;font-size:14px;margin-bottom:4px">'+_escHTML(it.producto)+'</div>'
          +'<div style="font-size:12px;color:#64748b;margin-bottom:8px">📅 '+_escHTML(it.fecha_programada)+' · '+(it.lotes||1)+' lote(s) · '+(it.lote_size_kg||0)+'kg</div>'
          +'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">'+pres+'</div>'
          +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px">'
          +'<div style="background:'+diasCol+'15;border:1px solid '+diasCol+'40;color:'+diasCol+';padding:6px 8px;border-radius:6px;text-align:center;font-size:11px;font-weight:700">⏰ '+diasTxt+'</div>'
          +'<div style="background:'+mpCol+'15;border:1px solid '+mpCol+'40;color:'+mpCol+';padding:6px 8px;border-radius:6px;text-align:center;font-size:11px;font-weight:700">'+mpTxt+'</div>'
          +'</div>'
          +(it.area_nombre?'<div style="font-size:11px;color:#64748b">🏭 '+_escHTML(it.area_nombre)+'</div>':'<div style="font-size:11px;color:#dc2626;font-weight:600">⚠ Sin área asignada</div>')
          +'</div></div>';
      }).join('');
    } catch(e){
      grid.innerHTML = '<div style="color:#dc2626;padding:14px;grid-column:1/-1">Error: '+e.message+'</div>';
    }
  }

  function abrirPlanSemModal(prodId){
    if(!_PS_DATA) return;
    var item = (_PS_DATA.items||[]).find(function(x){return x.produccion_id===prodId});
    if(!item) return;
    var modal = document.getElementById('modal-plansem');
    var box = document.getElementById('ps-modal-content');
    var diasCol = item.alerta_dias==='rojo' ? '#dc2626' : (item.alerta_dias==='amarillo'?'#d97706':(item.alerta_dias==='verde'?'#15803d':'#94a3b8'));
    var img = item.imagen_url
      ? '<img src="'+_escAttr(item.imagen_url)+'" style="width:100%;height:200px;object-fit:cover" alt="">'
      : '<div style="width:100%;height:200px;background:linear-gradient(135deg,#1a4a7a,#7c3aed);display:flex;align-items:center;justify-content:center;color:#fff;font-size:80px">📦</div>';

    var mpHtml = '';
    if(item.mp_status && item.mp_status.length){
      mpHtml = '<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:6px"><thead><tr style="background:#f1f5f9"><th style="padding:6px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">MP</th><th style="padding:6px 10px;text-align:right;font-size:10px;color:#475569">Req</th><th style="padding:6px 10px;text-align:right;font-size:10px;color:#475569">Stock</th><th style="padding:6px 10px;text-align:right;font-size:10px;color:#475569">Reservado</th><th style="padding:6px 10px;text-align:right;font-size:10px;color:#475569">Neto</th></tr></thead><tbody>';
      item.mp_status.forEach(function(m){
        var c = m.estado==='ok'?'#15803d':(m.estado==='justo'?'#d97706':'#dc2626');
        mpHtml += '<tr style="border-top:1px solid #e2e8f0"><td style="padding:5px 10px"><span style="color:'+c+';font-weight:700">'+(m.estado==='ok'?'✓':m.estado==='justo'?'⚠':'✗')+'</span> '+_escHTML(m.material_nombre)+'</td>'
          +'<td style="padding:5px 10px;text-align:right;font-family:monospace">'+m.requerido_g.toLocaleString()+'g</td>'
          +'<td style="padding:5px 10px;text-align:right;font-family:monospace;color:#64748b">'+m.stock_total_g.toLocaleString()+'g</td>'
          +'<td style="padding:5px 10px;text-align:right;font-family:monospace;color:#94a3b8">-'+m.reservado_previo_g.toLocaleString()+'g</td>'
          +'<td style="padding:5px 10px;text-align:right;font-family:monospace;font-weight:700;color:'+c+'">'+m.disponible_neto_g.toLocaleString()+'g</td></tr>';
      });
      mpHtml += '</tbody></table>';
    }

    var presOptions = '<option value="">— elegir presentación —</option>'
      + (item.presentaciones||[]).map(function(p){
        var vol = p.volumen_ml?p.volumen_ml+' mL':(p.peso_g?p.peso_g+' g':'');
        return '<option value="'+p.id+'">'+_escHTML(p.etiqueta)+(vol?' · '+vol:'')+'</option>';
      }).join('');

    box.innerHTML = img
      +'<div style="padding:18px 22px">'
      +'<div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:8px;margin-bottom:14px">'
      +'<div><h2 style="margin:0;color:#0f172a;font-size:20px">'+_escHTML(item.producto)+'</h2><div style="font-size:13px;color:#64748b;margin-top:2px">📅 '+_escHTML(item.fecha_programada)+' · '+(item.lotes||1)+' lote(s) de '+(item.lote_size_kg||0)+'kg</div></div>'
      +'<button onclick="cerrarPlanSemModal()" style="background:#fff;border:1px solid #cbd5e1;padding:6px 12px;border-radius:6px;cursor:pointer">Cerrar ✕</button>'
      +'</div>'
      // Estado actual
      +'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px">'
      +'<div style="background:'+diasCol+'15;border:1px solid '+diasCol+'40;border-radius:8px;padding:10px"><div style="font-size:10px;color:'+diasCol+';text-transform:uppercase;font-weight:700">Días inventario</div><div style="font-size:20px;font-weight:800;color:'+diasCol+';margin-top:2px">'+(item.dias_inventario===null?'—':item.dias_inventario+'d')+'</div></div>'
      +'<div style="background:'+(item.alcanza_mp?'#f0fdf4':'#fef2f2')+';border:1px solid '+(item.alcanza_mp?'#86efac':'#fecaca')+';border-radius:8px;padding:10px"><div style="font-size:10px;color:'+(item.alcanza_mp?'#15803d':'#dc2626')+';text-transform:uppercase;font-weight:700">MP</div><div style="font-size:14px;font-weight:800;color:'+(item.alcanza_mp?'#15803d':'#dc2626')+';margin-top:2px">'+(item.alcanza_mp?'✓ Alcanzan':'✗ Faltan '+(item.mp_deficit||[]).length)+'</div></div>'
      +'<div style="background:'+(item.area_nombre?'#f1f5f9':'#fef3c7')+';border:1px solid '+(item.area_nombre?'#cbd5e1':'#fbbf24')+';border-radius:8px;padding:10px"><div style="font-size:10px;color:'+(item.area_nombre?'#475569':'#92400e')+';text-transform:uppercase;font-weight:700">Área</div><div style="font-size:14px;font-weight:800;color:'+(item.area_nombre?'#0f172a':'#92400e')+';margin-top:2px">'+(item.area_nombre||'⚠ Sin asignar')+'</div></div>'
      +'</div>'
      // MP detalle
      +'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px;margin-bottom:14px">'
      +'<h4 style="margin:0 0 4px;color:#0f172a;font-size:13px">📊 Materias Primas (consumo agregado)</h4>'
      +'<p style="font-size:11px;color:#64748b;margin:0 0 4px">"Reservado" = MP comprometido por producciones programadas ANTES de esta. Neto = lo que realmente queda.</p>'
      + mpHtml
      +'</div>'
      // Presentación + Aceptar
      +'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:14px;margin-bottom:8px">'
      +'<h4 style="margin:0 0 10px;color:#166534;font-size:14px">✅ Aceptar y disparar producción</h4>'
      +'<p style="margin:0 0 10px;font-size:12px;color:#475569">Al aceptar, el sistema:<br>· asigna área (si no la tiene)<br>· crea tareas: señalar envases, solicitar etiquetas'+(item.presentaciones&&item.presentaciones.length?', armar goteros (si aplica)':'')+'<br>· programa envasado mañana<br>· notifica a Calidad para muestra micro</p>'
      +'<label style="font-size:11px;color:#64748b;font-weight:600">Presentación a producir</label>'
      +'<select id="ps-pres" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;margin-bottom:10px">'+presOptions+'</select>'
      +'<button onclick="aceptarProduccion('+item.produccion_id+')" style="width:100%;background:#15803d;color:#fff;border:none;padding:12px;border-radius:8px;font-size:14px;font-weight:800;cursor:pointer">✅ ACEPTAR PRODUCCIÓN</button>'
      +'</div>'
      +'<div id="ps-resultado"></div>'
      +'</div>';
    modal.style.display = 'flex';
  }
  function cerrarPlanSemModal(){ document.getElementById('modal-plansem').style.display='none'; }

  async function aceptarProduccion(prodId){
    var presSel = document.getElementById('ps-pres');
    var presId = presSel ? parseInt(presSel.value) : null;
    var resBox = document.getElementById('ps-resultado');
    resBox.innerHTML = '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px;text-align:center;color:#64748b;margin-top:10px">Disparando cascade...</div>';
    try {
      var r = await fetch('/api/planta/aceptar-produccion/'+prodId, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({presentacion_id: presId})
      });
      var d = await r.json();
      if(!r.ok){ resBox.innerHTML='<div style="color:#dc2626;padding:14px;background:#fef2f2;border-radius:8px;margin-top:10px">'+(d.error||'Error')+'</div>'; return; }
      resBox.innerHTML = '<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:14px;margin-top:10px">'
        +'<h4 style="margin:0 0 8px;color:#166534">✅ Producción aceptada</h4>'
        +'<ul style="margin:0;padding-left:18px;font-size:12px;color:#1e293b">'
        + (d.log||[]).map(function(l){ return '<li>'+_escHTML(l)+'</li>'; }).join('')
        + '</ul>'
        +'<div style="margin-top:8px;font-size:12px;color:#64748b">Envasado tentativo: <b>'+_escHTML(d.fecha_envasado_estimada)+'</b> · '+(d.tareas_creadas||[]).length+' tarea(s) creada(s)</div>'
        +'<div style="margin-top:10px"><a href="#" onclick="cerrarPlanSemModal();switchProgTab(\'preflight\');return false" style="color:#7c3aed;font-weight:700;text-decoration:none">→ Ver Pre-flight</a> · <a href="#" onclick="cerrarPlanSemModal();switchProgTab(\'tareas\');return false" style="color:#7c3aed;font-weight:700;text-decoration:none">→ Ver Tareas operativas</a></div>'
        +'</div>';
      // Refrescar plan después de unos segundos
      setTimeout(cargarPlanSemanal, 2000);
    } catch(e){ resBox.innerHTML='<div style="color:#dc2626;padding:14px;margin-top:10px">Error de red: '+e.message+'</div>'; }
  }

  // ════════════════════════════════════════════════════════════════════════
  // Conteo Cíclico ABC · Ma/Ju
  // ════════════════════════════════════════════════════════════════════════
  async function cargarConteoCalendario(){
    var lista = document.getElementById('cc-lista');
    var kpis  = document.getElementById('cc-kpis');
    if(!lista) return;
    lista.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r = await fetch('/api/conteo-ciclico/calendario?dias=30');
      var d = await r.json();
      var items = d.items || [];
      var pend = d.pendientes || 0;
      var contados = items.filter(function(x){return x.estado==='cerrado'}).length;
      var conDif = items.filter(function(x){return x.estado==='con_diferencia'}).length;
      kpis.innerHTML = ''
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #6d28d9;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Total programados</div><div style="font-size:26px;font-weight:800;color:#0f172a">'+items.length+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #d97706;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Pendientes</div><div style="font-size:26px;font-weight:800;color:#d97706">'+pend+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #15803d;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Contados OK</div><div style="font-size:26px;font-weight:800;color:#15803d">'+contados+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(conDif?'#dc2626':'#15803d')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Con diferencia</div><div style="font-size:26px;font-weight:800;color:'+(conDif?'#dc2626':'#15803d')+'">'+conDif+'</div></div>';

      if(!items.length){
        lista.innerHTML = '<div style="background:#fef3c7;border:1px solid #fbbf24;color:#92400e;padding:20px;border-radius:10px;text-align:center">⚠ Sin conteos programados. Ejecuta "🔥 Auto-Plan AHORA" en la pestaña 🤖 Auto-Plan para generar el calendario de conteos.</div>';
        return;
      }
      // Agrupar por fecha
      var porFecha = {};
      items.forEach(function(it){ porFecha[it.fecha] = porFecha[it.fecha] || []; porFecha[it.fecha].push(it); });
      var html = '';
      Object.keys(porFecha).sort().forEach(function(fecha){
        var dia = new Date(fecha+'T00:00:00').toLocaleDateString('es-CO', {weekday:'long', day:'numeric', month:'short'});
        html += '<div style="margin-bottom:14px"><h3 style="margin:0 0 8px;color:#6d28d9;font-size:14px;text-transform:capitalize">📅 '+_escHTML(dia)+'</h3>';
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden"><table style="width:100%;border-collapse:collapse;font-size:12px"><thead style="background:#f9fafb"><tr>'
          +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Material</th>'
          +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">ABC</th>'
          +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Asignado</th>'
          +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Estado</th>'
          +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Diferencia</th>'
          +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Acción</th>'
          +'</tr></thead><tbody>';
        porFecha[fecha].forEach(function(it){
          var abcCol = it.categoria_abc==='A' ? '#dc2626' : (it.categoria_abc==='B' ? '#d97706' : '#15803d');
          var estCol = it.estado==='cerrado' ? '#15803d' : (it.estado==='con_diferencia' ? '#dc2626' : '#94a3b8');
          var dif = it.diferencia_g!==null ? (it.diferencia_g>=0?'+':'')+it.diferencia_g.toFixed(0)+'g' : '—';
          html += '<tr style="border-top:1px solid #f1f5f9">'
            +'<td style="padding:7px 10px"><b>'+_escHTML(it.material_nombre||it.material_id)+'</b></td>'
            +'<td style="padding:7px 10px;text-align:center"><span style="background:'+abcCol+'22;color:'+abcCol+';padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700">'+_escHTML(it.categoria_abc||'C')+'</span></td>'
            +'<td style="padding:7px 10px;font-size:11px;color:#64748b">'+_escHTML(it.asignado_a||'—')+'</td>'
            +'<td style="padding:7px 10px;text-align:center"><span style="background:'+estCol+'22;color:'+estCol+';padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700;text-transform:uppercase">'+_escHTML(it.estado||'')+'</span></td>'
            +'<td style="padding:7px 10px;text-align:right;font-family:monospace;color:'+(it.estado==='con_diferencia'?'#dc2626':'#0f172a')+';font-weight:700">'+_escHTML(dif)+'</td>'
            +'<td style="padding:7px 10px;text-align:center">'
            +(it.estado==='programado' ? '<button onclick="ccAbrirRegistro('+it.id+',\''+_escHTML(String(it.material_nombre||it.material_id||'').replace(/\x27/g,"\\\x27"))+'\')" style="background:#6d28d9;color:#fff;border:none;padding:4px 12px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer">📝 Registrar</button>' : '<span style="color:#94a3b8;font-size:11px">'+_escHTML(it.terminado_por||'—')+'</span>')
            +'</td></tr>';
        });
        html += '</tbody></table></div></div>';
      });
      lista.innerHTML = html;
    } catch(e){
      lista.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  function ccAbrirRegistro(id, nombre){
    document.getElementById('cc-reg-id').value = id;
    document.getElementById('cc-reg-titulo').textContent = '📋 Conteo: '+nombre;
    document.getElementById('cc-reg-stock').value = '';
    document.getElementById('cc-reg-notas').value = '';
    document.getElementById('modal-cc-reg').style.display = 'flex';
    setTimeout(function(){document.getElementById('cc-reg-stock').focus();}, 50);
  }

  async function ccRegistrar(){
    var id = document.getElementById('cc-reg-id').value;
    var stock = parseFloat(document.getElementById('cc-reg-stock').value);
    if(isNaN(stock) || stock < 0){ alert('Stock real requerido (gramos)'); return; }
    try {
      var r = await fetch('/api/conteo-ciclico/'+id+'/registrar', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({stock_real_g: stock, notas: document.getElementById('cc-reg-notas').value})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
      document.getElementById('modal-cc-reg').style.display = 'none';
      var msg = 'Conteo registrado · diferencia '+d.diferencia_g.toFixed(0)+'g ('+d.pct_diferencia+'%)';
      _toast(msg, 1);
      cargarConteoCalendario();
    } catch(e){ alert('Error: '+e.message); }
  }

  // ════════════════════════════════════════════════════════════════════════
  // Auto-Plan Maestro · Sebastian: "la herramienta más avanzada del mundo"
  // Cron L-V 7am · genera producciones + compras + conteos + emails
  // ════════════════════════════════════════════════════════════════════════
  var _AP_SUBTAB = 'resumen';
  var _AP_PLAN = null;

  function apInit(){
    apSwitchSubtab(_AP_SUBTAB);
    apCronStateRefresh();
  }

  async function apCronStateRefresh(){
    try {
      var r = await fetch('/api/auto-plan/cron/state');
      var d = await r.json();
      var span = document.getElementById('ap-cron-status');
      var btn = document.getElementById('ap-cron-toggle-btn');
      if(d.habilitado){
        span.innerHTML = '✓ <b>ACTIVO</b>'+(d.ultima_ejecucion_at?' · última: '+_escHTML(d.ultima_ejecucion_at.substring(0,16)):'');
        btn.textContent = 'Desactivar';
        btn.style.background = '#fee2e2';
        btn.style.color = '#dc2626';
      } else {
        span.innerHTML = '⏸ inactivo';
        btn.textContent = 'Activar';
        btn.style.background = '#fff';
        btn.style.color = '#7c3aed';
      }
    } catch(e){}
  }
  async function apCronToggle(){
    try {
      var sr = await fetch('/api/auto-plan/cron/state');
      var st = await sr.json();
      var nuevo = !st.habilitado;
      var msg = nuevo
        ? '¿ACTIVAR cron diario? Cada L-V 7am el sistema generará plan + SOLs + emails automáticamente.'
        : '¿DESACTIVAR cron? El plan dejará de ejecutarse automáticamente (puedes seguir disparándolo manual con "🔥 Ejecutar AHORA").';
      if(!confirm(msg)) return;
      var r = await fetch('/api/auto-plan/cron/toggle', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({habilitar: nuevo})
      });
      var d = await r.json();
      if(!r.ok){ alert(d.error||'Error'); return; }
      _toast('Cron '+(nuevo?'activado ✓':'desactivado'), 1);
      apCronStateRefresh();
    } catch(e){ alert('Error: '+e.message); }
  }

  function apSwitchSubtab(t){
    _AP_SUBTAB = t;
    ['resumen','skus','mp','emails','aprendizaje','runs'].forEach(function(s){
      var div = document.getElementById('ap-sub-'+s);
      var btn = document.getElementById('ap-stab-'+s);
      if(div) div.style.display = (s===t) ? 'block' : 'none';
      if(btn){
        if(s==='aprendizaje'){
          btn.style.background = (s===t) ? '#dc2626' : 'linear-gradient(135deg,#fbbf24,#dc2626)';
          btn.style.color = '#fff';
        } else {
          btn.style.background = (s===t) ? '#7c3aed' : '#e2e8f0';
          btn.style.color      = (s===t) ? '#fff' : '#475569';
        }
      }
    });
    if(t==='skus') apCargarSkus();
    if(t==='mp') apCargarMp();
    if(t==='emails') apCargarEmails();
    if(t==='runs') apCargarRuns();
    if(t==='aprendizaje') apAnalizarHistorico();
  }

  // 🧠 Aprendizaje del histórico
  async function apAnalizarHistorico(){
    var box = document.getElementById('ap-aprendizaje-content');
    box.style.padding = '20px';
    box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px">🧠 Analizando histórico de 12 meses...</div>';
    try {
      var r = await fetch('/api/auto-plan/aprender-historico?meses_atras=12');
      var d = await r.json();
      var k = d.kpis || {};
      var html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:14px">'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Productos con histórico</div><div style="font-size:26px;font-weight:800;color:#0f172a">'+(k.productos_con_historico||0)+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #d97706;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Productos NUEVOS</div><div style="font-size:26px;font-weight:800;color:#d97706">'+(k.productos_nuevos_sin_historico||0)+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #dc2626;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Recomendaciones</div><div style="font-size:26px;font-weight:800;color:#dc2626">'+(k.recomendaciones_actualizar||0)+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #15803d;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Lotes analizados</div><div style="font-size:26px;font-weight:800;color:#15803d">'+(k.total_lotes_analizados||0)+'</div></div>'
        +'</div>';

      var aprend = d.aprendizaje || [];
      if(aprend.length){
        html += '<h3 style="color:#0f172a;margin:14px 0 8px">📊 Cadencias detectadas vs configuradas</h3>';
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">';
        html += '<thead style="background:#f9fafb"><tr>'
          +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producto</th>'
          +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Lotes hist.</th>'
          +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Última prod.</th>'
          +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Cadencia REAL</th>'
          +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Configurada</th>'
          +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Diferencia</th>'
          +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Acción</th>'
          +'</tr></thead><tbody>';
        aprend.forEach(function(a){
          var rowBg = a.recomendar_actualizar ? '#fef3c7' : '#fff';
          var difCol = !a.diferencia_dias ? '#94a3b8' : (Math.abs(a.diferencia_dias)>14?'#dc2626':(Math.abs(a.diferencia_dias)>7?'#d97706':'#15803d'));
          html += '<tr style="border-top:1px solid #f1f5f9;background:'+rowBg+'">'
            +'<td style="padding:7px 10px"><b>'+_escHTML(a.producto)+'</b></td>'
            +'<td style="padding:7px 10px;text-align:right;font-family:monospace">'+a.lotes_historicos+'</td>'
            +'<td style="padding:7px 10px;font-size:11px;color:#64748b">'+_escHTML(a.ultima_produccion||'—')+(a.dias_desde_ultima!=null?' (hace '+a.dias_desde_ultima+'d)':'')+'</td>'
            +'<td style="padding:7px 10px;text-align:right;font-family:monospace;font-weight:700">'+(a.cadencia_real_dias?a.cadencia_real_dias+'d':'—')+'</td>'
            +'<td style="padding:7px 10px;text-align:right;font-family:monospace;color:#64748b">'+(a.cadencia_configurada?a.cadencia_configurada+'d':'auto')+'</td>'
            +'<td style="padding:7px 10px;text-align:right;font-family:monospace;color:'+difCol+';font-weight:700">'+(a.diferencia_dias!=null?(a.diferencia_dias>0?'+':'')+a.diferencia_dias+'d':'—')+'</td>'
            +'<td style="padding:7px 10px;text-align:center">'+(a.recomendar_actualizar
              ? '<button onclick="apAplicarUna(\''+_escAttr(a.producto)+'\','+a.cadencia_real_dias+')" style="background:#15803d;color:#fff;border:none;padding:4px 10px;border-radius:5px;font-size:10px;font-weight:700;cursor:pointer">✓ Adoptar</button>'
              : '<span style="color:#94a3b8;font-size:11px">OK</span>')+'</td>'
            +'</tr>';
        });
        html += '</tbody></table></div>';
      }

      var nuevos = d.productos_nuevos || [];
      if(nuevos.length){
        html += '<h3 style="color:#0f172a;margin:18px 0 8px">🆕 Productos nuevos (sin histórico)</h3>';
        html += '<p style="color:#64748b;font-size:12px;margin:0 0 8px">Estos productos están en formula_headers pero NUNCA se han producido. El sistema los pondrá como "primer lote" en el plan.</p>';
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px;font-size:12px">';
        nuevos.forEach(function(p){
          html += '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f1f5f9">'
            +'<span><b>'+_escHTML(p.producto)+'</b> · lote '+(p.lote_kg||0)+'kg</span>'
            +'<span style="color:#d97706;font-size:11px">→ '+_escHTML(p.sugerencia||'producir pronto')+'</span>'
            +'</div>';
        });
        html += '</div>';
      }

      box.style.padding = '0';
      box.innerHTML = html;
    } catch(e){
      box.innerHTML = '<div style="color:#dc2626;padding:20px">Error: '+e.message+'</div>';
    }
  }

  async function apAplicarUna(producto, cadencia){
    if(!confirm('¿Adoptar cadencia REAL de '+cadencia+'d para "'+producto+'"?')) return;
    try {
      var r = await fetch('/api/auto-plan/aplicar-aprendizaje', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({productos:[{producto: producto, cadencia_real_dias: cadencia}]})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'')); return; }
      _toast('✓ Cadencia adoptada', 1);
      apAnalizarHistorico();
    } catch(e){ alert('Error: '+e.message); }
  }

  async function apAplicarAprendizaje(){
    if(!confirm('¿Aplicar TODAS las recomendaciones de cadencia detectadas del histórico?\n\nLas cadencias actualmente configuradas serán reemplazadas con las REALES.')) return;
    try {
      var r = await fetch('/api/auto-plan/aplicar-aprendizaje', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'')); return; }
      _toast('✓ '+d.total+' cadencias actualizadas', 1);
      apAnalizarHistorico();
    } catch(e){ alert('Error: '+e.message); }
  }

  async function apPreview(){
    var content = document.getElementById('ap-resumen-content');
    content.innerHTML = '<div style="text-align:center;padding:40px;color:#7c3aed">🤖 Generando plan...</div>';
    try {
      var r = await fetch('/api/auto-plan/preview?dias=60');
      var d = await r.json();
      _AP_PLAN = d;
      apRenderPlan(d, false);
    } catch(e){
      content.innerHTML = '<div style="color:#dc2626;padding:20px">Error: '+e.message+'</div>';
    }
  }

  async function apEjecutar(){
    if(!confirm('¿Ejecutar Auto-Plan AHORA?\n\nEl sistema CREARÁ producciones, SOLs de compra y conteos cíclicos según las cadencias y stock actual. Si hay emails configurados, los enviará.')) return;
    var content = document.getElementById('ap-resumen-content');
    content.innerHTML = '<div style="text-align:center;padding:40px;color:#dc2626">🔥 Ejecutando auto-plan + creando registros...</div>';
    try {
      var r = await fetch('/api/auto-plan/aplicar', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({dias: 60})
      });
      var d = await r.json();
      if(!r.ok){ content.innerHTML='<div style="color:#dc2626;padding:20px">'+(d.error||'Error')+'</div>'; return; }
      var banner = document.getElementById('ap-status-banner');
      banner.style.display='block';
      banner.style.background = '#f0fdf4';
      banner.style.border = '1px solid #86efac';
      banner.style.color = '#166534';
      banner.innerHTML = '<b>✅ Auto-Plan aplicado</b> · '
        +(d.resultado.producciones_creadas||[]).length+' producciones creadas · '
        +(d.resultado.compras_creadas||[]).length+' SOLs creadas · '
        +(d.resultado.conteos_creados||[]).length+' conteos programados';
      // Cargar el plan completo para mostrar
      apRenderPlan({
        producciones_propuestas: d.plan.producciones_propuestas,
        compras_propuestas: d.plan.compras_propuestas,
        conteos_propuestos: d.plan.conteos_propuestos,
        alertas: d.plan.alertas,
        log: d.plan.log,
      }, true);
    } catch(e){
      content.innerHTML='<div style="color:#dc2626;padding:20px">Error de red: '+e.message+'</div>';
    }
  }

  function apRenderPlan(d, aplicado){
    var content = document.getElementById('ap-resumen-content');
    content.style.padding = '0';
    content.style.textAlign = 'left';
    content.style.color = 'inherit';
    var prods = d.producciones_propuestas || [];
    var compras = d.compras_propuestas || [];
    var conteos = d.conteos_propuestos || [];
    var alertas = d.alertas || [];

    // KPIs
    var nCrit = alertas.filter(function(a){return a.severidad==='critica'}).length;
    var html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:18px">'
      +'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:10px;padding:14px"><div style="font-size:11px;color:#166534;text-transform:uppercase;font-weight:700">Producciones</div><div style="font-size:30px;font-weight:800;color:#15803d">'+prods.length+'</div></div>'
      +'<div style="background:#fef3c7;border:1px solid #fbbf24;border-radius:10px;padding:14px"><div style="font-size:11px;color:#92400e;text-transform:uppercase;font-weight:700">SOLs auto</div><div style="font-size:30px;font-weight:800;color:#92400e">'+compras.length+'</div></div>'
      +'<div style="background:'+(nCrit?'#fef2f2':'#f0fdf4')+';border:1px solid '+(nCrit?'#fecaca':'#86efac')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:'+(nCrit?'#7f1d1d':'#166534')+';text-transform:uppercase;font-weight:700">Alertas críticas</div><div style="font-size:30px;font-weight:800;color:'+(nCrit?'#dc2626':'#15803d')+'">'+nCrit+'</div></div>'
      +'<div style="background:#f3e8ff;border:1px solid #d8b4fe;border-radius:10px;padding:14px"><div style="font-size:11px;color:#6b21a8;text-transform:uppercase;font-weight:700">Conteos cíclicos</div><div style="font-size:30px;font-weight:800;color:#7c3aed">'+conteos.length+'</div></div>'
      +'</div>';

    // Alertas críticas
    if(alertas.length){
      html += '<h3 style="color:#0f172a;margin:0 0 8px;font-size:14px">⚠ Alertas</h3>';
      html += alertas.map(function(a){
        var c = a.severidad==='critica' ? '#dc2626' : '#d97706';
        return '<div style="background:'+c+'15;border-left:3px solid '+c+';padding:10px 14px;border-radius:6px;margin-bottom:6px;font-size:13px"><b style="color:'+c+'">'+_escHTML(a.titulo||'')+'</b></div>';
      }).join('');
    }

    // Producciones
    html += '<h3 style="color:#0f172a;margin:18px 0 8px;font-size:14px">📅 Producciones propuestas ('+prods.length+')</h3>';
    if(!prods.length){
      html += '<div style="background:#f8fafc;padding:20px;border-radius:8px;text-align:center;color:#94a3b8">Sin producciones nuevas — todo dentro de cobertura ✓</div>';
    } else {
      html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;margin-bottom:14px"><table style="width:100%;border-collapse:collapse;font-size:12px">'
        +'<thead style="background:#f9fafb"><tr><th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Fecha</th><th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producto</th><th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Lote</th><th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Razón</th></tr></thead><tbody>';
      prods.forEach(function(p){
        html += '<tr style="border-top:1px solid #f1f5f9"><td style="padding:7px 10px;font-family:monospace">'+_escHTML(p.fecha_programada)+'</td><td style="padding:7px 10px"><b>'+_escHTML(p.producto)+'</b><br><span style="color:#64748b;font-size:10px">cad '+(p.razon||'')+'</span></td><td style="padding:7px 10px;text-align:right;font-family:monospace;font-weight:700">'+(p.kg_con_merma||0).toFixed(0)+'kg</td><td style="padding:7px 10px;font-size:11px;color:#64748b">'+_escHTML(p.razon||'')+'</td></tr>';
      });
      html += '</tbody></table></div>';
    }

    // Compras
    html += '<h3 style="color:#0f172a;margin:18px 0 8px;font-size:14px">🛒 Compras automáticas ('+compras.length+')</h3>';
    if(!compras.length){
      html += '<div style="background:#f8fafc;padding:20px;border-radius:8px;text-align:center;color:#94a3b8">Sin compras nuevas — MP suficientes</div>';
    } else {
      html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;margin-bottom:14px"><table style="width:100%;border-collapse:collapse;font-size:12px">'
        +'<thead style="background:#f9fafb"><tr><th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Material</th><th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Cantidad</th><th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Origen</th><th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Urgencia</th></tr></thead><tbody>';
      compras.forEach(function(c){
        var urgCol = c.urgencia==='critica'?'#dc2626':(c.urgencia==='alta'?'#d97706':'#7c3aed');
        html += '<tr style="border-top:1px solid #f1f5f9"><td style="padding:7px 10px"><b>'+_escHTML(c.material_nombre)+'</b></td><td style="padding:7px 10px;text-align:right;font-family:monospace">'+(c.cantidad_a_pedir_g/1000).toFixed(2)+'kg</td><td style="padding:7px 10px;font-size:11px">'+_escHTML(c.origen)+' · '+c.lead_time_dias+'d</td><td style="padding:7px 10px;text-align:center"><span style="background:'+urgCol+';color:#fff;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700">'+c.urgencia.toUpperCase()+'</span></td></tr>';
      });
      html += '</tbody></table></div>';
    }

    // Conteos cíclicos
    if(conteos.length){
      html += '<h3 style="color:#0f172a;margin:18px 0 8px;font-size:14px">📋 Conteos cíclicos (Ma/Ju)</h3>';
      html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:12px;font-size:12px">'
        + conteos.slice(0,10).map(function(c){
          return '<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #f1f5f9"><span><b>'+_escHTML(c.fecha)+'</b> · '+_escHTML(c.material_nombre||'')+' <span style="background:#ede9fe;color:#5b21b6;padding:1px 6px;border-radius:6px;font-size:10px">'+_escHTML(c.categoria_abc||'C')+'</span></span><span style="color:#64748b;font-size:10px">'+_escHTML(c.asignado_a||'')+'</span></div>';
        }).join('')
        +'</div>';
    }

    // Log
    if(d.log){
      html += '<details style="margin-top:18px"><summary style="cursor:pointer;color:#64748b;font-size:12px;font-weight:600">📜 Log generación</summary>'
        +'<pre style="background:#0f172a;color:#cbd5e1;padding:14px;border-radius:8px;font-size:11px;overflow:auto;max-height:280px;margin-top:8px">'+ _escHTML(d.log.join('\n')) +'</pre></details>';
    }

    content.innerHTML = html;
  }

  async function apCargarSkus(){
    var box = document.getElementById('ap-skus-tabla');
    box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r = await fetch('/api/auto-plan/configs/sku');
      var d = await r.json();
      var rows = d.configs || [];
      box.innerHTML = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden"><table style="width:100%;border-collapse:collapse;font-size:12px">'
        +'<thead style="background:#f9fafb"><tr>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producto</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Categoría</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Cadencia (d)</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Cob. target</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Cob. min</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Merma %</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Lote kg</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Prio</th>'
        +'</tr></thead><tbody>'
        + rows.map(function(c){
          return '<tr style="border-top:1px solid #f1f5f9">'
            +'<td style="padding:6px 10px"><b>'+_escHTML(c.producto_nombre)+'</b></td>'
            +'<td style="padding:6px 10px;font-size:11px;color:#64748b">'+_escHTML(c.categoria||'')+'</td>'
            +'<td style="padding:6px 10px;text-align:right" contenteditable="true" data-id="'+c.id+'" data-col="cadencia_dias" onblur="apSkuUpdate(this)">'+(c.cadencia_dias===null?'auto':c.cadencia_dias)+'</td>'
            +'<td style="padding:6px 10px;text-align:right" contenteditable="true" data-id="'+c.id+'" data-col="cobertura_target_dias" onblur="apSkuUpdate(this)">'+c.cobertura_target_dias+'</td>'
            +'<td style="padding:6px 10px;text-align:right" contenteditable="true" data-id="'+c.id+'" data-col="cobertura_min_dias" onblur="apSkuUpdate(this)">'+c.cobertura_min_dias+'</td>'
            +'<td style="padding:6px 10px;text-align:right" contenteditable="true" data-id="'+c.id+'" data-col="merma_pct" onblur="apSkuUpdate(this)">'+c.merma_pct+'</td>'
            +'<td style="padding:6px 10px;text-align:right;color:#64748b">'+(c.lote_size_kg||'—')+'</td>'
            +'<td style="padding:6px 10px;text-align:right" contenteditable="true" data-id="'+c.id+'" data-col="prioridad" onblur="apSkuUpdate(this)">'+c.prioridad+'</td>'
            +'</tr>';
        }).join('')
        +'</tbody></table></div>'
        +'<p style="font-size:11px;color:#64748b;margin-top:8px">💡 Click en cualquier celda para editar. Tab/blur guarda. Cadencia="auto" deja que el sistema decida por umbral.</p>';
    } catch(e){
      box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  async function apSkuUpdate(el){
    var id = el.dataset.id;
    var col = el.dataset.col;
    var val = el.textContent.trim();
    if(col==='cadencia_dias' && (val==='auto' || val==='' || val==='null')) val = null;
    else val = parseFloat(val);
    if(val !== null && isNaN(val)) return;
    try {
      var body = {}; body[col] = val;
      var r = await fetch('/api/auto-plan/configs/sku/'+id, {
        method:'PUT', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body)
      });
      if(r.ok) el.style.background = '#dcfce7'; else el.style.background = '#fee2e2';
      setTimeout(function(){el.style.background='';}, 800);
    } catch(e){ el.style.background = '#fee2e2'; }
  }

  async function apCargarMp(){
    var box = document.getElementById('ap-mp-tabla');
    box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r = await fetch('/api/auto-plan/configs/mp');
      var d = await r.json();
      var rows = d.configs || [];
      if(!rows.length){
        box.innerHTML = '<div style="background:#fef3c7;border:1px solid #fbbf24;padding:14px;border-radius:8px;color:#92400e">⚠ No hay materiales con lead time configurado. El auto-plan usará defaults (lead 14d, buffer 30d, origen local). Para envases de China, configúralos aquí con lead 180d.</div>';
        return;
      }
      box.innerHTML = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden"><table style="width:100%;border-collapse:collapse;font-size:12px">'
        +'<thead style="background:#f9fafb"><tr>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">ID</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Material</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Origen</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Lead</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Buffer</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Cob min</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Cob ideal</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Proveedor</th>'
        +'</tr></thead><tbody>'
        + rows.map(function(c){
          var origenColor = c.origen==='china'?'#dc2626':(c.origen==='local'?'#15803d':'#7c3aed');
          return '<tr style="border-top:1px solid #f1f5f9">'
            +'<td style="padding:6px 10px;font-family:monospace;font-size:11px">'+_escHTML(c.material_id)+(c.es_envase?' 📦':'')+'</td>'
            +'<td style="padding:6px 10px"><b>'+_escHTML(c.material_nombre||'')+'</b></td>'
            +'<td style="padding:6px 10px"><span style="background:'+origenColor+'22;color:'+origenColor+';padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700">'+_escHTML(c.origen)+'</span></td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace">'+c.lead_time_dias+'d</td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace">'+c.buffer_dias+'d</td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace">'+c.cobertura_min_dias+'d</td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace">'+c.cobertura_ideal_dias+'d</td>'
            +'<td style="padding:6px 10px;font-size:11px;color:#64748b">'+_escHTML(c.proveedor_principal||'—')+'</td>'
            +'</tr>';
        }).join('')
        +'</tbody></table></div>';
    } catch(e){
      box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  function apMpNuevo(){
    ['mp-id','mp-nombre','mp-prov'].forEach(function(id){document.getElementById(id).value=''});
    document.getElementById('mp-origen').value='local';
    document.getElementById('mp-envase').value='0';
    document.getElementById('mp-lead').value='14';
    document.getElementById('mp-buffer').value='30';
    document.getElementById('mp-cobmin').value='30';
    document.getElementById('mp-cobideal').value='60';
    document.getElementById('modal-mp-cfg').style.display='flex';
  }

  async function apMpGuardar(){
    var body = {
      material_id: document.getElementById('mp-id').value.trim(),
      material_nombre: document.getElementById('mp-nombre').value.trim(),
      origen: document.getElementById('mp-origen').value,
      es_envase: parseInt(document.getElementById('mp-envase').value),
      lead_time_dias: parseInt(document.getElementById('mp-lead').value),
      buffer_dias: parseInt(document.getElementById('mp-buffer').value),
      cobertura_min_dias: parseInt(document.getElementById('mp-cobmin').value),
      cobertura_ideal_dias: parseInt(document.getElementById('mp-cobideal').value),
      proveedor_principal: document.getElementById('mp-prov').value.trim(),
    };
    if(!body.material_id){ alert('ID material requerido'); return; }
    try {
      var r = await fetch('/api/auto-plan/configs/mp', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
      document.getElementById('modal-mp-cfg').style.display='none';
      _toast('Material configurado', 1);
      apCargarMp();
    } catch(e){ alert('Error: '+e.message); }
  }

  async function apCargarEmails(){
    var box = document.getElementById('ap-emails-tabla');
    box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r = await fetch('/api/auto-plan/configs/emails');
      var d = await r.json();
      var rows = d.configs || [];
      box.innerHTML = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden"><table style="width:100%;border-collapse:collapse;font-size:12px">'
        +'<thead style="background:#f9fafb"><tr>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Rol</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Nombre</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Email</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Resumen</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Alertas</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Compras</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Calidad</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Agenda</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase"></th>'
        +'</tr></thead><tbody>'
        + rows.map(function(c){
          var ck = function(v,k){return '<input type="checkbox" '+(v?'checked':'')+' onchange="apEmailToggle(\''+c.rol+'\',\''+k+'\',this.checked)">';};
          return '<tr style="border-top:1px solid #f1f5f9">'
            +'<td style="padding:6px 10px;font-family:monospace;font-size:11px">'+_escHTML(c.rol)+'</td>'
            +'<td style="padding:6px 10px"><b>'+_escHTML(c.nombre||'')+'</b></td>'
            +'<td style="padding:6px 10px"><input type="email" value="'+_escAttr(c.email||'')+'" placeholder="email@dominio.com" data-rol="'+c.rol+'" onblur="apEmailUpdate(this)" style="width:100%;padding:5px 8px;border:1px solid #cbd5e1;border-radius:4px;font-size:12px;background:'+(c.email?'#f0fdf4':'#fef2f2')+'"></td>'
            +'<td style="padding:6px 10px;text-align:center">'+ck(c.recibe_resumen_diario,'recibe_resumen_diario')+'</td>'
            +'<td style="padding:6px 10px;text-align:center">'+ck(c.recibe_alertas_criticas,'recibe_alertas_criticas')+'</td>'
            +'<td style="padding:6px 10px;text-align:center">'+ck(c.recibe_compras_aprob,'recibe_compras_aprob')+'</td>'
            +'<td style="padding:6px 10px;text-align:center">'+ck(c.recibe_calidad,'recibe_calidad')+'</td>'
            +'<td style="padding:6px 10px;text-align:center">'+ck(c.recibe_agenda_personal,'recibe_agenda_personal')+'</td>'
            +'<td style="padding:6px 10px;text-align:center"><button onclick="apEmailTest(\''+_escAttr(c.email||'')+'\')" '+(c.email?'':'disabled')+' style="background:#7c3aed;color:#fff;border:none;padding:4px 10px;border-radius:4px;font-size:11px;font-weight:600;cursor:pointer;'+(c.email?'':'opacity:.4')+'">📧 Test</button></td>'
            +'</tr>';
        }).join('')
        +'</tbody></table></div>';
    } catch(e){
      box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  async function apEmailUpdate(input){
    try {
      var r = await fetch('/api/auto-plan/configs/emails', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({rol: input.dataset.rol, email: input.value.trim()})
      });
      if(r.ok){ input.style.background = input.value.trim() ? '#f0fdf4' : '#fef2f2'; }
    } catch(e){}
  }

  async function apEmailToggle(rol, key, val){
    var body = {rol: rol}; body[key] = val ? 1 : 0;
    try { await fetch('/api/auto-plan/configs/emails', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)}); } catch(e){}
  }

  async function apEmailTest(email){
    if(!email) return;
    if(!confirm('¿Enviar email de prueba a '+email+'?')) return;
    try {
      var r = await fetch('/api/auto-plan/configs/emails/test', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({email: email})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'no se pudo enviar')); return; }
      _toast('📧 Test enviado a '+email+' (puede tardar 30s)', 1);
    } catch(e){ alert('Error: '+e.message); }
  }

  async function apCargarRuns(){
    var box = document.getElementById('ap-runs-tabla');
    box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r = await fetch('/api/auto-plan/runs');
      var d = await r.json();
      var rows = d.runs || [];
      if(!rows.length){
        box.innerHTML = '<div style="background:#f8fafc;padding:20px;border-radius:8px;text-align:center;color:#94a3b8">El auto-plan aún no se ha ejecutado. Pulsa "🔥 Ejecutar AHORA" arriba para hacer la primera corrida.</div>';
        return;
      }
      box.innerHTML = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden"><table style="width:100%;border-collapse:collapse;font-size:12px">'
        +'<thead style="background:#f9fafb"><tr>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Fecha/hora</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Por</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Tipo</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Producciones</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Compras</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Alertas</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Emails</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Tiempo</th>'
        +'</tr></thead><tbody>'
        + rows.map(function(c){
          var tipoColor = c.tipo==='auto'?'#7c3aed':(c.tipo==='manual'?'#7c3aed':'#64748b');
          return '<tr style="border-top:1px solid #f1f5f9">'
            +'<td style="padding:6px 10px;font-family:monospace;font-size:11px">'+_escHTML((c.ejecutado_at||'').substring(0,19))+'</td>'
            +'<td style="padding:6px 10px;font-size:11px;color:#64748b">'+_escHTML(c.ejecutado_por)+'</td>'
            +'<td style="padding:6px 10px"><span style="background:'+tipoColor+'22;color:'+tipoColor+';padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700">'+_escHTML(c.tipo)+'</span></td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace">'+c.producciones_creadas+'</td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace">'+c.compras_creadas+'</td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace;color:'+(c.alertas_criticas>0?'#dc2626':'#64748b')+';font-weight:'+(c.alertas_criticas>0?'700':'400')+'">'+c.alertas_criticas+'</td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace">'+(c.emails_enviados||0)+'</td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace;font-size:11px;color:#64748b">'+(c.duracion_ms||0)+'ms</td>'
            +'</tr>';
        }).join('')
        +'</tbody></table></div>';
    } catch(e){
      box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  // ════════════════════════════════════════════════════════════════════════
  // PLAN V2 — Multi-horizonte (1sem / 1m / 2m / 3m / 6m / 1año)
  // ════════════════════════════════════════════════════════════════════════
  // Sebastian (30-abr-2026): "monte dos meses según lo que dice shopify"
  // → default 2 meses (con switcher para ver más / menos)
  var _PV2_HORIZONTE = '2';
  var _PV2_DATA = null;

  function planV2Init(){
    // Sebastian 7-may-2026: gutted. El módulo Plan se reduce a la vista
    // minimalista de producciones programadas. Toda la maquinaria legacy
    // (auto-plan auto-trigger, status line, centro acción, MP rolling,
    // paneles MEE, alertas, recomendaciones, calendar status, cobertura,
    // auditoría, detectarCambios) ya NO se carga automáticamente · si
    // alguien necesita esos panels los llama explícitamente desde botones
    // específicos. Resultado: 1 sola llamada al backend por tab activation.
    // Sebastián 12-may-2026 pivote: apaCargar (Shopify-driven) en lugar de
    // pv2CargarProdFaltantes (Calendar-driven). Ya no dependemos de Alejandro.
    apaCargar();
  }

  function planV2InjectMeePanels(){
    if(window._meePanelsMoved) return;
    var planv2 = document.getElementById('ptab-planv2');
    var anchor = document.getElementById('pv2-kpis');
    if(!planv2 || !anchor) return;

    // Sebastián 1-may-2026 (revisión): "Plan = necesidades del mes simple ·
    // Asignación Semanal = donde se hará todo · Centro de Mando = mapa".
    // PLAN: sólo necesidades (qué solicitar) + alertas
    // ASIGNACION: Esta Semana + Mi Día + Salas Vivo
    // CONFIG: Salud + Reporte + Crons + Items asignar + Config MEE
    var esenciales = ['plan-estado-solicitudes', 'plan-mee-alerts', 'plan-autosc', 'plan-autosc-mee'];
    var avanzados = ['mee-asignar-panel', 'mee-config-panel'];

    // Sebastián 1-may-2026: 'unificamos todo en el mapa, eliminamos pestaña'.
    // Mi Día + Pre-producción → tab Operación Live (Centro de Mando).
    // Esta Semana + Salas Vivo → ELIMINADOS (redundantes con cards de hoy
    // arriba del mapa · si quieres ver semana completa usa tab Plan).
    var mando = document.getElementById('ptab-plano');
    if(mando){
      var panelesMando = ['plan-mi-dia', 'plan-pre-produccion'];
      panelesMando.forEach(function(id){
        var el = document.getElementById(id);
        if(el) mando.appendChild(el);
      });
      // Esta Semana y Salas Vivo: ocultar (redundantes)
      ['plan-esta-semana', 'plan-salas-vivo'].forEach(function(id){
        var el = document.getElementById(id);
        if(el) el.style.display = 'none';
      });
    }

    // Mover paneles admin/config al tab Configuración
    var config = document.getElementById('ptab-config');
    if(config){
      var panelesConfig = ['plan-health', 'plan-reporte-ejecutivo', 'plan-cron-status'];
      panelesConfig.forEach(function(id){
        var el = document.getElementById(id);
        if(el) config.appendChild(el);
      });
    }

    // Crear contenedor de avanzados (oculto por default)
    var avBtn = document.createElement('div');
    avBtn.id = 'plan-avanzado-toggle';
    avBtn.style.cssText = 'margin:8px 0;text-align:center';
    avBtn.innerHTML = '<button onclick="planV2ToggleAvanzado()" id="btn-tog-avanzado" style="padding:6px 18px;background:#f1f5f9;color:#1f2937;border:1px solid #cbd5e1;border-radius:6px;font-size:11px;cursor:pointer;font-weight:600">⚙️ Mostrar avanzado (reportes · crons · config MEE)</button>';

    var avCont = document.createElement('div');
    avCont.id = 'plan-avanzado-cont';
    avCont.style.cssText = 'display:none';

    var current = anchor;
    esenciales.forEach(function(id){
      var el = document.getElementById(id);
      if(!el) return;
      if(current.nextSibling){
        planv2.insertBefore(el, current.nextSibling);
      } else {
        planv2.appendChild(el);
      }
      current = el;
    });
    // Toggle button + container
    if(current.nextSibling){
      planv2.insertBefore(avBtn, current.nextSibling);
      planv2.insertBefore(avCont, avBtn.nextSibling);
    } else {
      planv2.appendChild(avBtn);
      planv2.appendChild(avCont);
    }
    avanzados.forEach(function(id){
      var el = document.getElementById(id);
      if(el) avCont.appendChild(el);
    });

    window._meePanelsMoved = true;
    // Cargar datos esenciales (los avanzados se cargan al toggle)
    // Plan = estado solicitudes + auto-SC + alertas (simple)
    if(typeof estadoSolicitudesRecargar === 'function') estadoSolicitudesRecargar();
    if(typeof autoscRecargar === 'function') autoscRecargar();
    if(typeof autoscMeeRecargar === 'function') autoscMeeRecargar();
    if(typeof alertEtiquetasRecargar === 'function') alertEtiquetasRecargar();
    if(typeof alertD20Recargar === 'function') alertD20Recargar();
    // Counter del botón asignar (sin abrir panel)
    try{
      fetch('/api/planta/items-por-asignar', {credentials:'same-origin'})
        .then(function(r){return r.json();})
        .then(function(d){
          var btn = document.getElementById('btn-asignar-count');
          if(btn) btn.textContent = (d.total || 0);
        }).catch(function(){});
    }catch(e){}
  }
  function planV2ToggleAvanzado(){
    var cont = document.getElementById('plan-avanzado-cont');
    var btn = document.getElementById('btn-tog-avanzado');
    if(!cont || !btn) return;
    if(cont.style.display === 'none'){
      cont.style.display = 'block';
      btn.textContent = '⚙️ Ocultar avanzado';
      btn.style.background = '#1f2937';
      btn.style.color = '#fff';
      // Cargar datos avanzados al expandir
      if(typeof reporteEjecutivoRecargar === 'function') reporteEjecutivoRecargar();
      if(typeof preProduccionRecargar === 'function') preProduccionRecargar();
      if(typeof cronStatusRecargar === 'function') cronStatusRecargar();
    } else {
      cont.style.display = 'none';
      btn.textContent = '⚙️ Mostrar avanzado (reportes · crons · config MEE)';
      btn.style.background = '#f1f5f9';
      btn.style.color = '#1f2937';
    }
  }

  // ════════════════════════════════════════════════════════════════════
  // 📦 MP ROLLING FORECAST — consumo MP acumulado en el horizonte
  // ════════════════════════════════════════════════════════════════════
  // Horizonte seleccionable 15/30/60/90/180 días — Sebastián 30-abr-2026:
  // "Alejandro puede decidir qué trae de más. Pedidos en bloque o individual".
  var _MP_ROLLING_DIAS = 60;  // default

  function planV2MpRollingHorizonte(dias){
    _MP_ROLLING_DIAS = dias;
    planV2CargarMpRolling();
  }

  async function planV2CargarMpRolling(){
    var box = document.getElementById('pv2-mp-rolling');
    if(!box) return;
    var dias = _MP_ROLLING_DIAS;
    box.innerHTML = '<div style="background:#f1f5f9;padding:12px;border-radius:8px;font-size:12px;color:#64748b">⏳ Calculando consumo MP acumulado próximos '+dias+' días...</div>';
    try {
      var r = await fetch('/api/planta/mp-rolling-forecast?dias='+dias);
      var d = await r.json();
      if(d.error){ box.innerHTML=''; return; }
      var mats = d.materias || [];
      var k = d.kpis || {};
      if(!mats.length){
        box.innerHTML = '<div style="background:#ecfdf5;border:1px solid #6ee7b7;padding:12px;border-radius:8px;font-size:13px;color:#065f46">✅ Sin producciones planeadas en el horizonte — no hay consumo MP que proyectar</div>';
        return;
      }
      var stockouts = mats.filter(function(m){return m.fecha_stockout;});
      var criticas = stockouts.filter(function(m){return m.urgencia==='critica';});
      var altas = stockouts.filter(function(m){return m.urgencia==='alta';});
      var medias = stockouts.filter(function(m){return m.urgencia==='media';});
      var ok = mats.filter(function(m){return !m.fecha_stockout;});

      var bgHeader = stockouts.length ? 'linear-gradient(135deg,#7c3aed,#dc2626)' : 'linear-gradient(135deg,#7c3aed,#059669)';
      var html = '<div style="background:#fff;border:2px solid '+(stockouts.length?'#7c3aed':'#7c3aed')+';border-radius:10px;overflow:hidden">';
      html += '<div style="background:'+bgHeader+';color:#fff;padding:12px 16px">';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;margin-bottom:10px">';
      html += '<div><b style="font-size:15px">📦 Plan MP rolling · '+dias+' días</b><div style="font-size:11px;color:#fce7f3;margin-top:2px">Consumo MP acumulado de TODAS las producciones planeadas (sumando lunes + martes + ...)</div></div>';
      html += '<div style="display:flex;gap:5px;flex-wrap:wrap;font-size:10px">';
      if(criticas.length) html += '<span style="background:rgba(220,38,38,.5);padding:3px 8px;border-radius:5px;font-weight:800">🔴 '+criticas.length+' críticas</span>';
      if(altas.length) html += '<span style="background:rgba(249,115,22,.5);padding:3px 8px;border-radius:5px;font-weight:800">🟠 '+altas.length+' altas</span>';
      if(medias.length) html += '<span style="background:rgba(234,179,8,.5);padding:3px 8px;border-radius:5px;font-weight:800">🟡 '+medias.length+' medias</span>';
      if(ok.length) html += '<span style="background:rgba(34,197,94,.5);padding:3px 8px;border-radius:5px;font-weight:800">🟢 '+ok.length+' OK</span>';
      html += '</div></div>';
      // Selector de horizonte
      html += '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">';
      html += '<div style="display:flex;gap:4px;flex-wrap:wrap">';
      [15,30,60,90,180,365].forEach(function(d){
        var act = d === dias;
        html += '<button onclick="planV2MpRollingHorizonte('+d+')" style="padding:5px 12px;border:none;border-radius:5px;background:'+(act?'#fff':'rgba(255,255,255,.18)')+';color:'+(act?'#7c3aed':'#fff')+';font-weight:'+(act?'800':'600')+';cursor:pointer;font-size:11px">'+d+'d</button>';
      });
      html += '</div>';
      // Botón solicitar bloque
      if(stockouts.length){
        html += '<button onclick="planV2SolicitarBloque()" style="background:#fbbf24;color:#7c2d12;border:none;padding:6px 14px;border-radius:6px;font-size:11px;font-weight:800;cursor:pointer">📋 Solicitar a Compras (bloque)</button>';
      }
      html += '</div>';
      html += '</div>';  // /header
      html += '<div style="padding:10px 14px">';
      html += '<div style="font-size:11px;color:#64748b;margin-bottom:8px">📊 '+(k.total_producciones||0)+' producciones planeadas · '+(k.mps_afectadas||0)+' MPs distintas · ☑️ Marca las que quieras pedir en bloque</div>';

      // Tabla MP
      html += '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:11px">';
      html += '<thead style="background:#f1f5f9"><tr>';
      html += '<th style="padding:6px;width:30px"><input type="checkbox" id="mp-rolling-todos" onclick="planV2MpToggleTodos(this)" title="Marcar todos los stockouts"></th>';
      html += '<th style="padding:6px;text-align:left">Material</th>';
      html += '<th style="padding:6px;text-align:right">Stock hoy</th>';
      html += '<th style="padding:6px;text-align:right">Consumo</th>';
      html += '<th style="padding:6px;text-align:right">Saldo final</th>';
      html += '<th style="padding:6px;text-align:right">Lotes</th>';
      html += '<th style="padding:6px;text-align:left">Stockout</th>';
      html += '<th style="padding:6px;text-align:left">Comprar antes</th>';
      html += '<th style="padding:6px;text-align:right">Pedir</th>';
      html += '<th style="padding:6px;text-align:center">Solo</th>';
      html += '</tr></thead><tbody>';
      var urgCol = {critica:'#dc2626', alta:'#f97316', media:'#eab308', ok:'#10b981'};
      var maxFilas = stockouts.length + Math.min(8, ok.length);
      var idx = 0;
      var todas = stockouts.concat(ok);
      todas.forEach(function(m){
        if(idx >= maxFilas && !m.fecha_stockout) return;
        idx++;
        var col = urgCol[m.urgencia] || '#64748b';
        var safeId = (m.material_id||'').replace(/\x27/g,"\\\x27");
        var puedePedir = !!m.fecha_stockout;
        html += '<tr style="border-top:1px solid #e2e8f0">';
        if(puedePedir){
          html += '<td style="padding:5px 6px;text-align:center"><input type="checkbox" class="mp-rolling-check" data-id="'+_escHTML(m.material_id)+'"></td>';
        } else {
          html += '<td style="padding:5px 6px"></td>';
        }
        html += '<td style="padding:5px 6px;cursor:pointer" onclick="planV2VerMpDetalle(\''+safeId+'\')"><b>'+_escHTML(m.material_nombre)+'</b><div style="font-size:9px;color:#64748b">'+_escHTML(m.material_id)+'</div></td>';
        html += '<td style="padding:5px 6px;text-align:right;font-family:monospace">'+_fmtMiles(Math.round(m.stock_inicial_g))+' g</td>';
        html += '<td style="padding:5px 6px;text-align:right;font-family:monospace">'+_fmtMiles(Math.round(m.consumo_total_g))+' g</td>';
        var saldoCol = m.saldo_final_g < 0 ? '#dc2626' : '#10b981';
        html += '<td style="padding:5px 6px;text-align:right;font-family:monospace;color:'+saldoCol+';font-weight:700">'+_fmtMiles(Math.round(m.saldo_final_g))+' g</td>';
        html += '<td style="padding:5px 6px;text-align:right">'+m.num_lotes_que_la_usan+'</td>';
        if(m.fecha_stockout){
          html += '<td style="padding:5px 6px"><span style="background:'+col+'22;color:'+col+';padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700">'+_escHTML(m.fecha_stockout)+' (en '+m.dias_hasta_stockout+'d)</span></td>';
          html += '<td style="padding:5px 6px;font-size:10px;color:'+col+';font-weight:700">'+_escHTML(m.comprar_antes_de||'—')+'</td>';
          html += '<td style="padding:5px 6px;text-align:right;font-family:monospace;font-weight:700;color:'+col+'">'+_fmtMiles(Math.round(m.comprar_g_recomendado||0))+' g</td>';
          html += '<td style="padding:5px 6px;text-align:center"><button onclick="planV2SolicitarMP(\''+safeId+'\')" style="background:#7c3aed;color:#fff;border:none;padding:3px 8px;border-radius:4px;font-size:10px;font-weight:700;cursor:pointer">📋</button></td>';
        } else {
          html += '<td style="padding:5px 6px;color:#10b981">✓ alcanza</td>';
          html += '<td style="padding:5px 6px;color:#94a3b8">—</td>';
          html += '<td style="padding:5px 6px;text-align:right;color:#94a3b8">—</td>';
          html += '<td style="padding:5px 6px"></td>';
        }
        html += '</tr>';
      });
      html += '</tbody></table></div>';
      if(ok.length > 8){
        html += '<div style="margin-top:6px;font-size:10px;color:#64748b">+ '+(ok.length-8)+' MPs adicionales con stock suficiente (no listadas)</div>';
      }
      html += '<div style="margin-top:10px;font-size:10px;color:#64748b">💡 Click en nombre MP = ver detalle día por día · ☑️ marca y pulsa <b>"Solicitar bloque"</b> · 📋 = pedir individual</div>';
      html += '</div></div>';
      box.innerHTML = html;
      window._mpRollingData = mats;
    } catch(e){
      box.innerHTML = '<div style="background:#fef2f2;border:1px solid #fca5a5;padding:10px;border-radius:8px;font-size:12px;color:#991b1b">Error MP rolling: '+(e.message||'desconocido')+'</div>';
    }
  }

  function planV2MpToggleTodos(cb){
    document.querySelectorAll('.mp-rolling-check').forEach(function(c){c.checked = cb.checked;});
  }

  // ════════════════════════════════════════════════════════════════════
  // 📋 SOLICITAR A COMPRAS — individual o en bloque
  // ════════════════════════════════════════════════════════════════════
  async function planV2SolicitarMP(materialId){
    var mats = window._mpRollingData || [];
    var m = mats.find(function(x){return x.material_id === materialId;});
    if(!m){ alert('MP no encontrada'); return; }
    if(!m.fecha_stockout){ alert('Esta MP tiene stock suficiente, no requiere SC'); return; }
    var qty = prompt('📋 Solicitud de Compra individual\n\nMP: '+m.material_nombre+'\nID: '+m.material_id+'\nStockout: '+m.fecha_stockout+' (en '+m.dias_hasta_stockout+'d)\nLead time: '+(m.lead_time_dias||14)+'d\n\n¿Cuántos gramos pedir?', m.comprar_g_recomendado || 1000);
    if(qty === null) return;
    var cantidad = parseFloat(qty);
    if(isNaN(cantidad) || cantidad <= 0){ alert('Cantidad inválida'); return; }
    var justif = prompt('Justificación (opcional):', 'Stockout proyectado '+m.fecha_stockout+' por '+m.num_lotes_que_la_usan+' lotes en '+_MP_ROLLING_DIAS+'d') || '';
    await _planV2CrearSC([{material: m, cantidad_g: cantidad, justificacion: justif}], false);
  }

  async function planV2SolicitarBloque(){
    var checks = document.querySelectorAll('.mp-rolling-check:checked');
    var ids = Array.from(checks).map(function(c){return c.dataset.id;});
    if(!ids.length){ alert('Marca al menos una MP en stockout para incluir en el bloque'); return; }
    var mats = window._mpRollingData || [];
    var seleccion = mats.filter(function(m){return ids.indexOf(m.material_id) >= 0 && m.fecha_stockout;});
    if(!seleccion.length){ alert('Las MPs marcadas no requieren SC'); return; }
    var resumen = seleccion.map(function(m){return '  • '+m.material_nombre+': '+_fmtMiles(Math.round(m.comprar_g_recomendado||0))+' g (stockout '+m.fecha_stockout+')';}).join('\n');
    var ok = confirm('📋 Crear UNA solicitud de compra con '+seleccion.length+' MPs:\n\n'+resumen+'\n\n¿Confirmar?');
    if(!ok) return;
    var items = seleccion.map(function(m){
      return {
        material: m,
        cantidad_g: m.comprar_g_recomendado || 1000,
        justificacion: 'Stockout proyectado '+m.fecha_stockout+' (' + m.num_lotes_que_la_usan + ' lotes la usan)',
      };
    });
    await _planV2CrearSC(items, true);
  }

  async function _planV2CrearSC(items, esBloque){
    try {
      var body = {
        empresa: 'Espagiria',
        categoria: 'Materia Prima',
        tipo: 'Compra',
        area: 'Produccion',
        urgencia: 'Alta',
        observaciones: esBloque
          ? 'SC en bloque generada desde Plan MP rolling ('+_MP_ROLLING_DIAS+'d)'
          : 'SC individual generada desde Plan MP rolling ('+_MP_ROLLING_DIAS+'d)',
        items: items.map(function(it){
          return {
            codigo_mp: it.material.material_id,
            nombre_mp: it.material.material_nombre,
            cantidad_g: it.cantidad_g,
            unidad: 'g',
            justificacion: it.justificacion + (it.material.lead_time_dias ? ' · Lead time '+it.material.lead_time_dias+'d ('+(it.material.origen||'local')+')' : ''),
            valor_estimado: 0,
            proveedor_sugerido: it.material.proveedor_sugerido || '',
          };
        }),
      };
      var r = await fetch('/api/solicitudes-compra', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body),
      });
      var d = await r.json();
      if(d.error){ alert('Error: '+d.error); return; }
      alert('✅ Solicitud creada: '+d.numero+'\n\nCompras la verá en su bandeja.\nIr a /solicitudes para ver/aprobar.');
      // Refrescar panel
      planV2CargarMpRolling();
    } catch(e){
      alert('Error creando SC: '+(e.message||'desconocido'));
    }
  }

  function planV2VerMpDetalle(materialId){
    var mats = window._mpRollingData || [];
    var m = mats.find(function(x){return x.material_id === materialId;});
    if(!m){ alert('MP no encontrada'); return; }
    var modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
    modal.onclick = function(e){if(e.target===modal)modal.remove();};
    var html = '<div style="background:#fff;border-radius:12px;width:780px;max-width:96vw;max-height:92vh;overflow:auto;padding:24px">';
    html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px"><div>';
    html += '<h2 style="margin:0;color:#0f172a">📦 '+_escHTML(m.material_nombre)+'</h2>';
    html += '<p style="font-size:11px;color:#64748b;margin:4px 0 0">'+_escHTML(m.material_id)+'</p>';
    html += '</div><button onclick="this.closest(\'div[style*=fixed]\').remove()" style="background:#fff;border:1px solid #cbd5e1;padding:6px 12px;border-radius:6px;cursor:pointer">Cerrar ✕</button></div>';
    // KPIs
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-bottom:14px">';
    html += '<div style="background:#ecfdf5;padding:10px;border-radius:8px"><div style="font-size:10px;color:#065f46">Stock hoy</div><div style="font-size:20px;font-weight:800;color:#047857">'+_fmtMiles(Math.round(m.stock_inicial_g))+' g</div></div>';
    html += '<div style="background:#fff7ed;padding:10px;border-radius:8px"><div style="font-size:10px;color:#7c2d12">Consumo total</div><div style="font-size:20px;font-weight:800;color:#ea580c">'+_fmtMiles(Math.round(m.consumo_total_g))+' g</div></div>';
    var saldoCol = m.saldo_final_g < 0 ? '#dc2626' : '#10b981';
    html += '<div style="background:'+saldoCol+'12;padding:10px;border-radius:8px"><div style="font-size:10px;color:'+saldoCol+'">Saldo final</div><div style="font-size:20px;font-weight:800;color:'+saldoCol+'">'+_fmtMiles(Math.round(m.saldo_final_g))+' g</div></div>';
    html += '<div style="background:#f1f5f9;padding:10px;border-radius:8px"><div style="font-size:10px;color:#475569">Lotes la usan</div><div style="font-size:20px;font-weight:800;color:#1e293b">'+m.num_lotes_que_la_usan+'</div></div>';
    html += '</div>';
    if(m.fecha_stockout){
      html += '<div style="background:#fef2f2;border:2px solid #dc2626;border-radius:8px;padding:12px;margin-bottom:14px">';
      html += '<b style="color:#991b1b">🔴 Stock-out el '+_escHTML(m.fecha_stockout)+' (en '+m.dias_hasta_stockout+' días)</b>';
      html += '<div style="font-size:11px;color:#7f1d1d;margin-top:4px">📅 Comprar antes de: <b>'+_escHTML(m.comprar_antes_de||'—')+'</b></div>';
      html += '<div style="font-size:11px;color:#7f1d1d">📦 Cantidad recomendada: <b>'+_fmtMiles(Math.round(m.comprar_g_recomendado||0))+' g</b></div>';
      html += '<div style="font-size:11px;color:#7f1d1d">⏱️ Lead time: '+(m.lead_time_dias||14)+'d · Origen: '+(m.origen||'local')+'</div>';
      html += '</div>';
    }
    // Tabla cronológica
    html += '<h3 style="color:#0f172a;font-size:14px;margin:14px 0 8px">📅 Consumo día a día</h3>';
    html += '<table style="width:100%;border-collapse:collapse;font-size:11px"><thead style="background:#f1f5f9"><tr>';
    html += '<th style="padding:6px;text-align:left">Fecha</th><th style="padding:6px;text-align:left">Producto</th>';
    html += '<th style="padding:6px;text-align:right">Lote kg</th><th style="padding:6px;text-align:right">Consume g</th>';
    html += '<th style="padding:6px;text-align:right">Saldo</th></tr></thead><tbody>';
    (m.consumos||[]).forEach(function(cons){
      var sCol = cons.saldo_post_g < 0 ? '#dc2626' : '#10b981';
      html += '<tr style="border-top:1px solid #f1f5f9">';
      html += '<td style="padding:5px 6px;font-family:monospace">'+_escHTML(cons.fecha)+'</td>';
      html += '<td style="padding:5px 6px"><b>'+_escHTML(cons.producto)+'</b></td>';
      html += '<td style="padding:5px 6px;text-align:right">'+cons.kg_lote+' kg</td>';
      html += '<td style="padding:5px 6px;text-align:right;font-family:monospace">-'+_fmtMiles(Math.round(cons.g_consumido))+' g</td>';
      html += '<td style="padding:5px 6px;text-align:right;font-family:monospace;font-weight:700;color:'+sCol+'">'+_fmtMiles(Math.round(cons.saldo_post_g))+' g</td>';
      html += '</tr>';
    });
    html += '</tbody></table>';
    html += '</div>';
    modal.innerHTML = html;
    document.body.appendChild(modal);
  }

  // ════════════════════════════════════════════════════════════════════
  // 🛍️ FORECAST BLACK FRIDAY — pre-stock necesario por SKU
  // ════════════════════════════════════════════════════════════════════
  async function planV2VerForecastBF(){
    var modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
    modal.onclick = function(e){if(e.target===modal)modal.remove();};
    modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:40px;text-align:center"><div style="font-size:32px">🛍️</div><div style="margin-top:10px;color:#64748b">Calculando forecast Black Friday...</div></div>';
    document.body.appendChild(modal);
    try {
      var r = await fetch('/api/planta/forecast-black-friday');
      var d = await r.json();
      if(d.error){ modal.remove(); alert('Error: '+d.error); return; }
      var skus = d.skus || [];
      var k = d.kpis || {};
      var html = '<div style="background:#fff;border-radius:12px;width:1000px;max-width:96vw;max-height:92vh;overflow:auto;padding:24px">';
      html += '<div style="background:linear-gradient(135deg,#a855f7,#dc2626);color:#fff;border-radius:10px;padding:16px 20px;margin-bottom:18px">';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px">';
      html += '<div><h2 style="margin:0;font-size:22px">🛍️ Forecast Black Friday '+d.year+'</h2>';
      html += '<p style="font-size:12px;color:#fce7f3;margin:4px 0 0">BF: '+_escHTML(d.bf_fecha)+' · Cyber Monday: '+_escHTML(d.cyber_monday)+' · Ventana pico: '+_escHTML(d.ventana_pico_inicio)+' → '+_escHTML(d.ventana_pico_fin)+'</p>';
      html += '<p style="font-size:12px;color:#fce7f3;margin:4px 0 0">⚠️ Stock LISTO máximo el '+_escHTML(d.fecha_limite_stock)+' (pipeline 7d)</p></div>';
      html += '<button onclick="this.closest(\'div[style*=fixed]\').remove()" style="background:rgba(255,255,255,.25);border:1px solid rgba(255,255,255,.4);color:#fff;padding:8px 14px;border-radius:6px;cursor:pointer;font-weight:700">Cerrar ✕</button>';
      html += '</div></div>';

      // KPIs
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:18px">';
      html += '<div style="background:#fdf4ff;padding:12px;border-radius:8px;border:1px solid #d8b4fe"><div style="font-size:11px;color:#581c87">SKUs afectados</div><div style="font-size:26px;font-weight:800;color:#7c3aed">'+(k.total_skus_afectados||0)+'</div></div>';
      html += '<div style="background:#fef2f2;padding:12px;border-radius:8px;border:1px solid #fca5a5"><div style="font-size:11px;color:#991b1b">Lotes extra recomendados</div><div style="font-size:26px;font-weight:800;color:#dc2626">'+(k.total_lotes_extra||0)+'</div></div>';
      html += '<div style="background:#fff7ed;padding:12px;border-radius:8px;border:1px solid #fdba74"><div style="font-size:11px;color:#7c2d12">Total kg extra</div><div style="font-size:26px;font-weight:800;color:#ea580c">'+_fmtMiles(Math.round(k.total_kg_extra||0))+'</div></div>';
      html += '</div>';

      // Reglas
      html += '<div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:8px;padding:10px 14px;margin-bottom:18px;font-size:12px;color:#78350f">';
      html += '<b>📐 Reglas:</b><ul style="margin:6px 0 0 18px;padding:0">';
      (d.reglas||[]).forEach(function(r){ html += '<li>'+_escHTML(r)+'</li>'; });
      html += '</ul></div>';

      // Tabla
      html += '<table style="width:100%;border-collapse:collapse;font-size:12px"><thead style="background:#f1f5f9"><tr>';
      html += '<th style="padding:8px;text-align:left">Producto</th>';
      html += '<th style="padding:8px;text-align:right">Vel normal</th>';
      html += '<th style="padding:8px;text-align:right">Vel pico</th>';
      html += '<th style="padding:8px;text-align:right">Mult</th>';
      html += '<th style="padding:8px;text-align:right">Extra (u)</th>';
      html += '<th style="padding:8px;text-align:right">Extra (kg)</th>';
      html += '<th style="padding:8px;text-align:right">Lotes extra</th>';
      html += '<th style="padding:8px;text-align:left">Urg</th>';
      html += '</tr></thead><tbody>';
      var urgCol = {alta:'#dc2626', media:'#f97316', baja:'#10b981'};
      skus.forEach(function(s){
        var col = urgCol[s.urgencia] || '#64748b';
        html += '<tr style="border-top:1px solid #e2e8f0"><td style="padding:6px 8px"><b>'+_escHTML(s.producto)+'</b></td>';
        html += '<td style="padding:6px 8px;text-align:right;font-family:monospace">'+s.velocidad_normal_u_d+'</td>';
        html += '<td style="padding:6px 8px;text-align:right;font-family:monospace;color:'+col+';font-weight:700">'+s.velocidad_pico_u_d+'</td>';
        html += '<td style="padding:6px 8px;text-align:right;font-family:monospace">'+s.multiplicador+'×</td>';
        html += '<td style="padding:6px 8px;text-align:right">'+_fmtMiles(s.extra_unidades_pico)+'</td>';
        html += '<td style="padding:6px 8px;text-align:right;font-weight:700">'+s.extra_kg_pico+' kg</td>';
        html += '<td style="padding:6px 8px;text-align:right;font-weight:800;color:'+col+'">'+s.lotes_extra_recomendados+'</td>';
        html += '<td style="padding:6px 8px"><span style="background:'+col+'22;color:'+col+';padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700;text-transform:uppercase">'+s.urgencia+'</span></td>';
        html += '</tr>';
      });
      html += '</tbody></table>';
      html += '</div>';
      modal.innerHTML = html;
    } catch(e){
      modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:30px;color:#dc2626">Error: '+(e.message||'desconocido')+'<br><button onclick="this.closest(\'div[style*=fixed]\').remove()" style="margin-top:14px;padding:6px 14px">Cerrar</button></div>';
    }
  }

  // ════════════════════════════════════════════════════════════════════
  // 🔍 VERIFICAR LISTO PARA PRODUCIR — chequea MP/envases ANTES de producir
  // ════════════════════════════════════════════════════════════════════
  // Programación = aquí se verifica que TODO está listo antes de mandar a
  // Producción. El registro real (kg producidos + descuento FEFO MP) se
  // hace en el módulo Producción existente (/produccion).
  async function planV2VerificarListo(producto, kgSugerido){
    var modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
    modal.onclick = function(e){if(e.target===modal)modal.remove();};
    modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:40px;text-align:center"><div style="font-size:32px">🔍</div><div style="margin-top:10px;color:#64748b">Verificando MP para '+_escHTML(producto)+'...</div></div>';
    document.body.appendChild(modal);
    try {
      var r = await fetch('/api/planta/mp-para-lote?producto='+encodeURIComponent(producto)+'&kg='+kgSugerido);
      var d = await r.json();
      if(d.error){ modal.remove(); alert('Error: '+d.error); return; }
      var mps = d.mps || [];
      var k = d.kpis || {};
      var alcanza = d.alcanza;
      var faltantes = mps.filter(function(m){return m.estado==='faltante';});
      var ajustados = mps.filter(function(m){return m.estado==='ajustado';});
      var html = '<div style="background:#fff;border-radius:12px;width:780px;max-width:96vw;max-height:92vh;overflow:auto;padding:24px">';
      var bgHeader = alcanza ? 'linear-gradient(135deg,#10b981,#059669)' : 'linear-gradient(135deg,#dc2626,#ea580c)';
      html += '<div style="background:'+bgHeader+';color:#fff;border-radius:10px;padding:14px 18px;margin-bottom:16px">';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">';
      html += '<div><h2 style="margin:0;font-size:18px">🔍 '+_escHTML(producto)+' · '+kgSugerido+' kg</h2>';
      html += '<p style="font-size:12px;margin:4px 0 0;opacity:.95">'+_escHTML(d.mensaje||'')+'</p></div>';
      html += '<button onclick="this.closest(\'div[style*=fixed]\').remove()" style="background:rgba(255,255,255,.25);border:1px solid rgba(255,255,255,.4);color:#fff;padding:6px 12px;border-radius:6px;cursor:pointer;font-weight:700">Cerrar</button>';
      html += '</div></div>';

      // KPIs
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin-bottom:14px">';
      html += '<div style="background:#ecfdf5;padding:10px;border-radius:8px;border:1px solid #6ee7b7"><div style="font-size:10px;color:#065f46">✓ OK</div><div style="font-size:22px;font-weight:800;color:#047857">'+(k.ok||0)+'</div></div>';
      if(k.ajustado) html += '<div style="background:#fef3c7;padding:10px;border-radius:8px;border:1px solid #fcd34d"><div style="font-size:10px;color:#92400e">⚠ Ajustado</div><div style="font-size:22px;font-weight:800;color:#b45309">'+k.ajustado+'</div></div>';
      if(k.faltante) html += '<div style="background:#fef2f2;padding:10px;border-radius:8px;border:1px solid #fca5a5"><div style="font-size:10px;color:#991b1b">🔴 Faltante</div><div style="font-size:22px;font-weight:800;color:#dc2626">'+k.faltante+'</div></div>';
      html += '<div style="background:#f1f5f9;padding:10px;border-radius:8px"><div style="font-size:10px;color:#475569">Total MPs</div><div style="font-size:22px;font-weight:800;color:#1e293b">'+(k.total_mps||0)+'</div></div>';
      html += '</div>';

      // Acción
      if(alcanza){
        html += '<div style="background:#ecfdf5;border:2px solid #10b981;padding:14px;border-radius:8px;margin-bottom:14px;text-align:center">';
        html += '<div style="font-size:14px;color:#065f46;font-weight:700">✅ Listo para producir</div>';
        html += '<div style="font-size:11px;color:#047857;margin-top:4px">Cuando termines el lote, registra el resultado real en <b>Producción → Nueva</b> (descuento FEFO automático).</div>';
        html += '<a href="/inventarios/produccion" target="_blank" style="display:inline-block;margin-top:10px;background:#10b981;color:#fff;padding:8px 16px;border-radius:6px;text-decoration:none;font-weight:700;font-size:12px">→ Ir a Producción</a>';
        html += '</div>';
      } else {
        html += '<div style="background:#fef2f2;border:2px solid #dc2626;padding:14px;border-radius:8px;margin-bottom:14px">';
        html += '<div style="font-size:14px;color:#991b1b;font-weight:700">🔴 NO PRODUCIR — falta MP</div>';
        html += '<div style="font-size:11px;color:#7f1d1d;margin-top:6px">Compra/recibe las siguientes MPs antes de iniciar:</div>';
        html += '<ul style="margin:6px 0 0 18px;padding:0;font-size:11px;color:#7f1d1d">';
        faltantes.slice(0,8).forEach(function(m){
          html += '<li><b>'+_escHTML(m.material_nombre)+'</b>: faltan '+m.falta_g+' g (req '+m.requerido_g+' · stock '+m.stock_g+')</li>';
        });
        html += '</ul></div>';
      }

      // Alerta si hay MPs sin cruce (no_encontrado) — bug de ID
      var noCruzados = mps.filter(function(m){return m.fuente_stock === 'no_encontrado';});
      if(noCruzados.length){
        html += '<div style="background:#fef3c7;border:2px solid #d97706;border-radius:8px;padding:12px;margin-bottom:14px">';
        html += '<b style="color:#92400e">⚠️ '+noCruzados.length+' MPs sin cruce de ID</b>';
        html += '<div style="font-size:11px;color:#78350f;margin-top:4px">El sistema NO encontró estas MPs en bodega — probable diferencia entre el ID de la fórmula y el ID de movimientos. <b>Stock mostrado puede ser incorrecto.</b></div>';
        html += '<div style="font-size:11px;color:#78350f;margin-top:6px">Solución: ir a Admin → Bridge MP → mapear estos IDs:</div>';
        html += '<ul style="margin:4px 0 0 18px;padding:0;font-size:11px;color:#78350f">';
        noCruzados.slice(0,8).forEach(function(m){
          html += '<li><b>'+_escHTML(m.material_id)+'</b> ('+_escHTML(m.material_nombre)+') → bridge a su ID en bodega</li>';
        });
        html += '</ul></div>';
      }

      // Tabla MPs
      html += '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:11px">';
      html += '<thead style="background:#f1f5f9"><tr>';
      html += '<th style="padding:6px;text-align:left">Material</th>';
      html += '<th style="padding:6px;text-align:right">%</th>';
      html += '<th style="padding:6px;text-align:right">Requerido</th>';
      html += '<th style="padding:6px;text-align:right">Stock</th>';
      html += '<th style="padding:6px;text-align:right">Falta</th>';
      html += '<th style="padding:6px;text-align:left">Estado</th>';
      html += '<th style="padding:6px;text-align:left">Match</th>';
      html += '</tr></thead><tbody>';
      var estCol = {ok:'#10b981',ajustado:'#f59e0b',faltante:'#dc2626'};
      var fuenteIcono = {
        material_id: '✅ id',
        material_id_upper: '✅ id↑',
        nombre_exacto: '✅ nom',
        nombre_normalizado: '🟡 norm',
        no_encontrado: '🔴 SIN MATCH',
        fallback_query: '⚠ fallback',
      };
      mps.forEach(function(m){
        var c = estCol[m.estado] || '#64748b';
        var fuenteCol = m.fuente_stock === 'no_encontrado' ? '#dc2626' : (m.fuente_stock === 'nombre_normalizado' ? '#f59e0b' : '#10b981');
        html += '<tr style="border-top:1px solid #e2e8f0">';
        html += '<td style="padding:5px 6px"><b>'+_escHTML(m.material_nombre)+'</b><div style="font-size:9px;color:#64748b">'+_escHTML(m.material_id)+'</div></td>';
        html += '<td style="padding:5px 6px;text-align:right;font-family:monospace">'+m.porcentaje+'%</td>';
        html += '<td style="padding:5px 6px;text-align:right;font-family:monospace">'+m.requerido_g+' g</td>';
        html += '<td style="padding:5px 6px;text-align:right;font-family:monospace">'+m.stock_g+' g</td>';
        html += '<td style="padding:5px 6px;text-align:right;font-family:monospace;color:'+c+';font-weight:700">'+(m.falta_g>0?m.falta_g+' g':'—')+'</td>';
        html += '<td style="padding:5px 6px"><span style="background:'+c+'22;color:'+c+';padding:2px 6px;border-radius:4px;font-size:9px;font-weight:700;text-transform:uppercase">'+m.estado+'</span></td>';
        html += '<td style="padding:5px 6px;font-size:9px;color:'+fuenteCol+'">'+(fuenteIcono[m.fuente_stock]||m.fuente_stock||'—')+'</td>';
        html += '</tr>';
      });
      html += '</tbody></table></div>';
      html += '</div>';
      modal.innerHTML = html;
    } catch(e){
      modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:30px;color:#dc2626">Error: '+(e.message||'desconocido')+'<br><button onclick="this.closest(\'div[style*=fixed]\').remove()" style="margin-top:14px;padding:6px 14px">Cerrar</button></div>';
    }
  }

  // ════════════════════════════════════════════════════════════════════
  // STATUS LINE CONSOLIDADA — 1 línea con cobertura + calendar + margen
  // ════════════════════════════════════════════════════════════════════
  async function planV2CargarStatusLine(){
    var box = document.getElementById('pv2-status-line');
    if(!box) return;
    try {
      var [cobR, calR, audR] = await Promise.all([
        // BUG-1 fix · 20-may-2026 Dashboard PRO audit: URL real es
        // /api/planta/kpi-cobertura (sin -skus). Antes 404 silencioso.
        fetch('/api/planta/kpi-cobertura').then(function(r){return r.json();}).catch(function(){return null;}),
        fetch('/api/planta/calendar-debug').then(function(r){return r.json();}).catch(function(){return null;}),
        fetch('/api/planta/auditoria-calendar').then(function(r){return r.json();}).catch(function(){return null;}),
      ]);
      var partes = [];
      if(cobR && cobR.cobertura_pct !== undefined){
        partes.push('🎯 ' + cobR.cobertura_pct + '% cobertura SKUs');
      }
      if(calR && calR.events !== undefined){
        partes.push('📅 ' + (calR.events.length || 0) + ' eventos Calendar');
      }
      if(audR && audR.kpis && audR.kpis.cumple_margen_pct !== undefined){
        partes.push('✓ ' + audR.kpis.cumple_margen_pct + '% margen 20d');
      }
      if(partes.length){
        box.innerHTML = partes.join(' · ');
      } else {
        box.innerHTML = 'Producciones · MP · Envases — proyectado por horizonte';
      }
    } catch(e){
      box.innerHTML = 'Producciones · MP · Envases — proyectado por horizonte';
    }
  }

  // ════════════════════════════════════════════════════════════════════
  // CENTRO DE ACCIÓN UNIFICADO — Alertas + Recomendaciones en 1 panel
  // ════════════════════════════════════════════════════════════════════
  async function planV2CargarCentroAccion(){
    var box = document.getElementById('pv2-centro-accion');
    if(!box) return;
    box.innerHTML = '<div style="background:#f1f5f9;padding:14px;border-radius:8px;font-size:13px;color:#64748b">⏳ Cargando centro de acción...</div>';
    try {
      var [alR, recR] = await Promise.all([
        fetch('/api/planta/alertas-calendar').then(function(r){return r.json();}).catch(function(){return {alertas:[],kpis:{}};}),
        fetch('/api/planta/recomendaciones').then(function(r){return r.json();}).catch(function(){return {recomendaciones:[],kpis:{}};}),
      ]);
      var alertas = (alR && alR.alertas) || [];
      var alK = (alR && alR.kpis) || {};
      var recs = (recR && recR.recomendaciones) || [];
      var recK = (recR && recR.kpis) || {};

      // Combinar alertas + recomendaciones en una sola lista de "acciones"
      // Producto único, prioridad por estado más urgente
      var accionesMap = {};
      // Alertas
      alertas.forEach(function(a){
        accionesMap[a.producto] = {
          producto: a.producto,
          tipo: 'alerta',
          estado: a.estado,
          mensaje: a.mensaje,
          proxima_fecha: a.proxima_fecha,
          dias_hasta: a.dias_hasta_proximo,
          kg: a.kg_proximo,
          velocidad_real: a.velocidad_real,
          velocidad_planeada: a.velocidad_planeada,
          ratio: a.ratio,
          diff_dias: a.diff_dias,
          urgencia_orden: ({adelantar:1, adelantar_ligero:2, reducir_lote:3, atrasar_ligero:4, sin_ventas:5, ok:6}[a.estado] || 7),
        };
      });
      // Recomendaciones (sólo si SKU no tiene alerta y es accionable)
      recs.forEach(function(r){
        if(!accionesMap[r.producto] && (r.urgencia==='critica' || r.urgencia==='alta' || r.urgencia==='media')){
          accionesMap[r.producto] = {
            producto: r.producto,
            tipo: 'recomendacion',
            estado: r.urgencia,
            mensaje: r.razon || ('Días alcance: ' + r.dias_alcance + 'd'),
            proxima_fecha: r.fecha_proxima,
            dias_hasta: null,
            kg: r.lote_tipico_kg || r.lote_kg_default,
            velocidad_real: r.velocidad_dia,
            urgencia_orden: ({critica:1, alta:2, media:3}[r.urgencia] || 8),
          };
        }
      });
      var acciones = Object.values(accionesMap);
      acciones.sort(function(a,b){return a.urgencia_orden - b.urgencia_orden;});

      if(!acciones.length){
        box.innerHTML = '<div style="background:#ecfdf5;border:1px solid #6ee7b7;padding:14px;border-radius:8px;font-size:13px;color:#065f46">✅ Sin acciones pendientes — todos los SKUs alineados con su plan</div>';
        return;
      }

      var colDeEstado = function(s){
        return s==='adelantar'||s==='critica'?'#dc2626'
          : s==='adelantar_ligero'||s==='alta'?'#f97316'
          : s==='ok'?'#10b981'
          : s==='atrasar_ligero'||s==='media'?'#eab308'
          : s==='reducir_lote'?'#a855f7'
          : '#64748b';
      };
      var labelEstado = function(s){
        return ({adelantar:'🔴 ADELANTAR',adelantar_ligero:'🟠 ADELANTAR LIGERO',ok:'🟢 OK',
                 atrasar_ligero:'🟡 ATRASAR',reducir_lote:'⚠️ REDUCIR',sin_ventas:'∅ SIN VENTAS',
                 critica:'🔴 CRÍTICA',alta:'🟠 ALTA',media:'🟡 MEDIA'}[s] || s.toUpperCase());
      };

      var criticos = acciones.filter(function(a){return a.urgencia_orden <= 2;});
      var medios = acciones.filter(function(a){return a.urgencia_orden >= 3 && a.urgencia_orden <= 5;});
      var ok = acciones.filter(function(a){return a.urgencia_orden >= 6;});

      var html = '<div style="background:#fff;border:2px solid '+(criticos.length>0?'#dc2626':'#fb923c')+';border-radius:10px;overflow:hidden">';
      html += '<div style="background:linear-gradient(135deg,'+(criticos.length>0?'#dc2626,#ea580c':'#f97316,#fbbf24')+');color:#fff;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">';
      html += '<div><b style="font-size:15px">🎯 Centro de Acción</b><div style="font-size:11px;color:#fed7aa;margin-top:2px">Cruce Calendar + Velocidad real + Recomendaciones</div></div>';
      html += '<div style="display:flex;gap:6px;font-size:11px;flex-wrap:wrap">';
      if(criticos.length) html += '<span style="background:rgba(220,38,38,.4);padding:4px 10px;border-radius:6px;font-weight:800">🔴 '+criticos.length+' críticas</span>';
      if(medios.length) html += '<span style="background:rgba(234,179,8,.4);padding:4px 10px;border-radius:6px;font-weight:800">🟡 '+medios.length+' medias</span>';
      if(ok.length) html += '<span style="background:rgba(34,197,94,.4);padding:4px 10px;border-radius:6px;font-weight:800">🟢 '+ok.length+' OK</span>';
      html += '</div></div>';
      html += '<div style="padding:8px 12px;max-height:380px;overflow:auto">';

      function fila(a){
        var col = colDeEstado(a.estado);
        var bg = col + '12';
        var safeProducto = (a.producto||'').replace(/\x27/g,"\\\x27");
        var kgSugerido = a.kg || 30;
        return '<div style="background:'+bg+';border-left:4px solid '+col+';padding:10px 12px;margin-bottom:6px;border-radius:0 6px 6px 0">'
          +'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">'
          +'<div style="flex:1"><b style="color:#0f172a;font-size:13px">'+_escHTML(a.producto)+'</b>'
          +'<div style="font-size:11px;color:#475569;margin-top:3px">'+_escHTML(a.mensaje||'')+'</div>'
          +(a.proxima_fecha?'<div style="font-size:10px;color:#64748b;margin-top:3px">📅 Próximo: '+_escHTML(a.proxima_fecha)+(a.dias_hasta!=null?(' (en '+a.dias_hasta+'d)'):'')+(a.kg?(' · '+a.kg+' kg'):'')+'</div>':'')
          +(a.velocidad_real?'<div style="font-size:10px;color:#64748b">📊 Vel real: '+a.velocidad_real+' u/d'+(a.velocidad_planeada?(' · plan: '+a.velocidad_planeada+' u/d · ratio '+a.ratio+'×'):'')+'</div>':'')
          +'</div>'
          +'<div style="text-align:right;display:flex;flex-direction:column;gap:4px;align-items:flex-end">'
          +'<span style="background:'+col+';color:#fff;padding:4px 10px;border-radius:6px;font-size:10px;font-weight:800;white-space:nowrap">'+labelEstado(a.estado)+'</span>'
          +(a.diff_dias?('<div style="font-size:10px;color:'+col+';font-weight:700">'+(a.diff_dias>0?'-':'+')+Math.abs(a.diff_dias)+'d</div>'):'')
          +'<button onclick="planV2VerificarListo(\''+safeProducto+'\','+kgSugerido+')" style="background:#7c3aed;color:#fff;border:none;padding:4px 10px;border-radius:6px;font-size:10px;font-weight:700;cursor:pointer" title="Verificar MP, envases y capacidad antes de producir">🔍 Verificar listo</button>'
          +'</div></div></div>';
      }
      criticos.forEach(function(a){html+=fila(a);});
      medios.forEach(function(a){html+=fila(a);});
      if(ok.length){
        html += '<details style="margin-top:8px"><summary style="cursor:pointer;color:#475569;font-size:12px;padding:6px;font-weight:600">🟢 '+ok.length+' SKUs en plan correcto (clic para expandir)</summary>';
        ok.forEach(function(a){html+=fila(a);});
        html += '</details>';
      }
      html += '</div></div>';
      box.innerHTML = html;
    } catch(e){
      box.innerHTML = '<div style="background:#fef2f2;border:1px solid #fca5a5;padding:12px;border-radius:8px;font-size:12px;color:#991b1b">Error cargando centro de acción: '+(e.message||'desconocido')+'</div>';
    }
  }

  async function planV2CargarAlertas(){
    var box = document.getElementById('pv2-alertas-wrap');
    if(!box) return;
    box.innerHTML = '<div style="background:#f1f5f9;padding:12px;border-radius:8px;font-size:12px;color:#64748b">⏳ Cargando alertas Calendar vs ventas...</div>';
    try {
      var r = await fetch('/api/planta/alertas-calendar');
      var d = await r.json();
      if(d.error){ box.innerHTML=''; return; }
      var alertas = d.alertas||[];
      var k = d.kpis||{};
      if(!alertas.length){
        box.innerHTML = '<div style="background:#ecfdf5;border:1px solid #6ee7b7;padding:12px;border-radius:8px;font-size:13px;color:#065f46">✅ Sin alertas — todos los SKUs están alineados con su cadencia o sin lotes próximos en 60 días</div>';
        return;
      }
      var critical = alertas.filter(function(a){return a.estado==="adelantar"||a.estado==="reducir_lote";});
      var warn = alertas.filter(function(a){return a.estado==="adelantar_ligero"||a.estado==="atrasar_ligero"||a.estado==="sin_ventas";});
      var ok = alertas.filter(function(a){return a.estado==="ok";});
      var html = '<div style="background:#fff;border:2px solid #fb923c;border-radius:10px;overflow:hidden">';
      html += '<div style="background:linear-gradient(135deg,#dc2626,#ea580c);color:#fff;padding:12px 16px;display:flex;justify-content:space-between;align-items:center">';
      html += '<div><b style="font-size:15px">🚨 Alertas Calendar vs Ventas</b><div style="font-size:11px;color:#fed7aa;margin-top:2px">Cruce de cadencia planeada con velocidad real Shopify (30d)</div></div>';
      html += '<div style="display:flex;gap:8px;font-size:11px">';
      if(k.adelantar) html += '<span style="background:rgba(220,38,38,.4);padding:4px 10px;border-radius:6px;font-weight:800">🔴 '+k.adelantar+' adelantar</span>';
      if(k.adelantar_ligero) html += '<span style="background:rgba(249,115,22,.4);padding:4px 10px;border-radius:6px;font-weight:800">🟠 '+k.adelantar_ligero+' adelantar light</span>';
      if(k.ok) html += '<span style="background:rgba(34,197,94,.4);padding:4px 10px;border-radius:6px;font-weight:800">🟢 '+k.ok+' OK</span>';
      if(k.atrasar_ligero) html += '<span style="background:rgba(234,179,8,.4);padding:4px 10px;border-radius:6px;font-weight:800">🟡 '+k.atrasar_ligero+' atrasar</span>';
      if(k.reducir_lote) html += '<span style="background:rgba(168,85,247,.4);padding:4px 10px;border-radius:6px;font-weight:800">⚠ '+k.reducir_lote+' reducir lote</span>';
      if(k.sin_ventas) html += '<span style="background:rgba(100,116,139,.4);padding:4px 10px;border-radius:6px;font-weight:800">∅ '+k.sin_ventas+' sin ventas</span>';
      html += '</div></div>';
      html += '<div style="padding:8px 12px;max-height:340px;overflow:auto">';

      function colDeEstado(s){
        return s==='adelantar'?'#dc2626':s==='adelantar_ligero'?'#f97316':s==='ok'?'#10b981':s==='atrasar_ligero'?'#eab308':s==='reducir_lote'?'#a855f7':'#64748b';
      }

      function fila(a){
        var col = colDeEstado(a.estado);
        var bg  = col + '12';
        return '<div style="background:'+bg+';border-left:4px solid '+col+';padding:10px 12px;margin-bottom:6px;border-radius:0 6px 6px 0">'
          +'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">'
          +'<div style="flex:1"><b style="color:#0f172a;font-size:13px">'+_escHTML(a.producto)+'</b>'
          +'<div style="font-size:11px;color:#475569;margin-top:3px">'+_escHTML(a.mensaje)+'</div>'
          +'<div style="font-size:10px;color:#64748b;margin-top:3px">📅 Próximo lote: '+_escHTML(a.proxima_fecha)+' (en '+a.dias_hasta_proximo+'d) · '+a.kg_proximo+' kg · '+(a.unidades_lote||0)+' u</div>'
          +'<div style="font-size:10px;color:#64748b">📊 Velocidad real: '+(a.velocidad_real||0)+' u/d · planeada: '+(a.velocidad_planeada||0)+' u/d · ratio: '+(a.ratio||0)+'×</div>'
          +'</div>'
          +'<div style="text-align:right"><span style="background:'+col+';color:#fff;padding:4px 10px;border-radius:6px;font-size:10px;font-weight:800;text-transform:uppercase">'+a.estado.replace(/_/g," ")+'</span>'
          +(a.diff_dias?('<div style="font-size:10px;color:'+col+';margin-top:4px;font-weight:700">'+(a.diff_dias>0?'-':'+')+Math.abs(a.diff_dias)+'d</div>'):'')
          +'</div></div></div>';
      }

      // Críticos primero
      critical.forEach(function(a){ html += fila(a); });
      warn.forEach(function(a){ html += fila(a); });
      // OK colapsado
      if(ok.length){
        html += '<details style="margin-top:8px"><summary style="cursor:pointer;color:#475569;font-size:12px;padding:6px">🟢 '+ok.length+' SKUs en plan correcto (clic para expandir)</summary>';
        ok.forEach(function(a){ html += fila(a); });
        html += '</details>';
      }
      html += '</div></div>';
      box.innerHTML = html;
    } catch(e){
      box.innerHTML = '<div style="background:#fef2f2;border:1px solid #fca5a5;padding:10px;border-radius:8px;font-size:12px;color:#991b1b">Error cargando alertas: '+(e.message||'desconocido')+'</div>';
    }
  }

  async function planV2CargarAuditoria(){
    var box = document.getElementById('pv2-auditoria');
    if(!box) return;
    try {
      var r = await fetch('/api/planta/auditoria-calendar');
      var d = await r.json();
      var k = d.kpis || {};
      if((d.total||0) === 0){
        box.style.display = 'none';
        return;
      }
      box.style.display = 'block';
      var pct = k.cumple_margen_pct || 0;
      var col = pct >= 80 ? '#86efac' : (pct >= 60 ? '#fcd34d' : '#fca5a5');
      var icon = pct >= 80 ? '✓' : (pct >= 60 ? '⚠' : '🔴');
      box.innerHTML = '<b style="color:'+col+'">'+icon+' '+pct+'% cumple margen 20d</b> '
        + '· de '+d.total+' producciones en Calendar: '
        + (k.ok ? '<b style="color:#86efac">'+k.ok+' OK</b> · ' : '')
        + (k.temprana ? '<span style="color:#93c5fd">'+k.temprana+' tempranas</span> · ' : '')
        + (k.ajustada ? '<span style="color:#fcd34d">'+k.ajustada+' ajustadas</span> · ' : '')
        + (k.tarde ? '<span style="color:#fb923c">'+k.tarde+' tardes</span> · ' : '')
        + (k.stockout ? '<b style="color:#fca5a5">'+k.stockout+' stock-outs</b>' : '')
        + ' <a href="#" onclick="planV2VerAuditoria();return false" style="color:#fff;text-decoration:underline;margin-left:6px">ver detalle</a>';
    } catch(e){ /* silent */ }
  }

  async function planV2VerAuditoria(){
    try {
      var r = await fetch('/api/planta/auditoria-calendar');
      var d = await r.json();
      var auditorias = d.auditorias || [];
      var modal = document.createElement('div');
      modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
      modal.onclick = function(e){if(e.target===modal)modal.remove();};
      var byClase = {ok:'#15803d',temprana:'#7c3aed',ajustada:'#d97706',tarde:'#dc2626',stockout:'#7f1d1d'};
      var html = '<div style="background:#fff;border-radius:12px;width:900px;max-width:96vw;max-height:90vh;overflow:auto;padding:20px">'
        +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><h3 style="margin:0;color:#0f172a">📊 Auditoría Calendar · margen 20d</h3><button onclick="this.closest(\'div[style*=fixed]\').remove()" style="background:#fff;border:1px solid #cbd5e1;padding:6px 12px;border-radius:6px;cursor:pointer">Cerrar ✕</button></div>'
        +'<p style="color:#64748b;font-size:12px;margin:0 0 14px">Para cada producción del Calendar, calculamos cuánto cubría el lote anterior vs cuándo se hizo la siguiente. Si el margen real ≥ 20 días → se cumplió la regla.</p>';
      if(!auditorias.length){
        html += '<div style="text-align:center;padding:40px;color:#94a3b8">Sin pares consecutivos para auditar</div>';
      } else {
        html += '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">'
          +'<thead style="background:#f9fafb"><tr>'
          +'<th style="padding:8px;text-align:left">Producto</th>'
          +'<th style="padding:8px;text-align:left">Anterior</th>'
          +'<th style="padding:8px;text-align:left">Actual</th>'
          +'<th style="padding:8px;text-align:right">Gap</th>'
          +'<th style="padding:8px;text-align:right">Cubre</th>'
          +'<th style="padding:8px;text-align:right">Margen</th>'
          +'<th style="padding:8px;text-align:left">Estado</th>'
          +'</tr></thead><tbody>';
        auditorias.forEach(function(a){
          var col = byClase[a.clase] || '#64748b';
          html += '<tr style="border-top:1px solid #f1f5f9">'
            +'<td style="padding:6px 8px"><b>'+_escHTML(a.producto)+'</b></td>'
            +'<td style="padding:6px 8px;font-size:11px">'+_escHTML(a.fecha_anterior)+'<br><span style="color:#64748b">'+a.kg_anterior+'kg</span></td>'
            +'<td style="padding:6px 8px;font-size:11px">'+_escHTML(a.fecha_actual)+'</td>'
            +'<td style="padding:6px 8px;text-align:right;font-family:monospace">'+a.gap_dias+'d</td>'
            +'<td style="padding:6px 8px;text-align:right;font-family:monospace">'+a.duracion_estimada_lote+'d</td>'
            +'<td style="padding:6px 8px;text-align:right;font-family:monospace;font-weight:700;color:'+col+'">'+(a.margen_dias>0?'+':'')+a.margen_dias+'d</td>'
            +'<td style="padding:6px 8px"><span style="background:'+col+'22;color:'+col+';padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase">'+a.clase+'</span></td>'
            +'</tr>';
        });
        html += '</tbody></table></div>';
      }
      html += '</div>';
      modal.innerHTML = html;
      document.body.appendChild(modal);
    } catch(e){ alert('Error: '+e.message); }
  }

  // ════════════════════════════════════════════════════════════════════
  // 🔍 DIAGNÓSTICO SKU — lo que el sistema LEE crudo de Shopify
  // ════════════════════════════════════════════════════════════════════
  async function planV2DiagnosticoSKU(){
    // Paso 1: cargar lista de productos
    var modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
    modal.onclick = function(e){if(e.target===modal)modal.remove();};
    modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:30px;text-align:center"><div style="font-size:32px">⏳</div><div style="margin-top:10px;color:#64748b">Cargando productos...</div></div>';
    document.body.appendChild(modal);
    try {
      var r = await fetch('/api/planta/diagnostico-sku?listar=1');
      var d = await r.json();
      var prods = d.productos || [];
      var html = '<div style="background:#fff;border-radius:12px;width:600px;max-width:96vw;max-height:90vh;overflow:auto;padding:24px">';
      html += '<h3 style="margin:0 0 14px;color:#0f172a">🔍 Selecciona un producto a diagnosticar</h3>';
      html += '<p style="color:#64748b;font-size:12px;margin:0 0 14px">Vamos a ver crudo lo que el sistema lee de Shopify para ese producto: SKUs mapeados, stock, ventas, velocidad, días de alcance.</p>';
      html += '<input type="text" id="diagSkuFiltro" oninput="planV2DiagFiltrar()" placeholder="Filtrar..." style="width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;margin-bottom:10px">';
      html += '<div id="diagSkuLista" style="max-height:50vh;overflow:auto">';
      prods.forEach(function(p){
        var col = p.estado === 'activo' ? '#0f172a' : '#94a3b8';
        html += '<div class="diag-item" data-nombre="'+_escHTML((p.nombre||'').toLowerCase())+'" onclick="planV2DiagnosticoVer(\''+_escHTML((p.nombre||'').replace(/\x27/g,"\\\x27"))+'\')" style="padding:10px;border-bottom:1px solid #f1f5f9;cursor:pointer;display:flex;justify-content:space-between;color:'+col+'" onmouseover="this.style.background=\'#f8fafc\'" onmouseout="this.style.background=\'#fff\'">';
        html += '<span><b>'+_escHTML(p.nombre)+'</b></span><span style="color:#64748b;font-size:11px">P'+(p.prioridad||'-')+' · '+_escHTML(p.estado||'')+'</span>';
        html += '</div>';
      });
      html += '</div></div>';
      modal.innerHTML = html;
    } catch(e){
      modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:30px;color:#dc2626">Error: '+(e.message||'desconocido')+'<br><button onclick="this.closest(\'div[style*=fixed]\').remove()" style="margin-top:14px;padding:6px 14px">Cerrar</button></div>';
    }
  }

  function planV2DiagFiltrar(){
    var q = (document.getElementById('diagSkuFiltro').value||'').toLowerCase();
    var items = document.querySelectorAll('.diag-item');
    items.forEach(function(it){
      var n = it.getAttribute('data-nombre') || '';
      it.style.display = (!q || n.indexOf(q) >= 0) ? '' : 'none';
    });
  }

  async function planV2DiagnosticoVer(producto){
    // Cierra modal anterior
    document.querySelectorAll('div[style*="position:fixed"][style*="z-index:9999"]').forEach(function(m){m.remove();});
    var modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
    modal.onclick = function(e){if(e.target===modal)modal.remove();};
    modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:50px;text-align:center"><div style="font-size:42px">🔍</div><div style="margin-top:14px;color:#0f172a;font-size:16px;font-weight:700">Analizando "'+_escHTML(producto)+'"...</div></div>';
    document.body.appendChild(modal);
    try {
      var r = await fetch('/api/planta/diagnostico-sku?producto='+encodeURIComponent(producto));
      var d = await r.json();
      if(d.error){ modal.remove(); alert('Error: '+d.error); return; }

      var html = '<div style="background:#fff;border-radius:12px;width:1100px;max-width:96vw;max-height:92vh;overflow:auto;padding:24px">';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:14px">';
      html += '<div><h2 style="margin:0;color:#0f172a;font-size:22px">🔍 Diagnóstico: '+_escHTML(d.producto)+'</h2>';
      html += '<p style="color:#64748b;font-size:11px;margin:4px 0 0">Análisis: '+_escHTML(d.timestamp_actual||'')+'</p></div>';
      html += '<button onclick="this.closest(\'div[style*=fixed]\').remove()" style="background:#fff;border:1px solid #cbd5e1;padding:6px 14px;border-radius:6px;cursor:pointer">Cerrar ✕</button></div>';

      // Advertencias
      if((d.advertencias||[]).length){
        html += '<div style="background:#fef2f2;border:1px solid #fca5a5;padding:12px;border-radius:8px;margin-bottom:16px">';
        d.advertencias.forEach(function(a){
          html += '<div style="color:#991b1b;font-size:12px;margin-bottom:4px">'+_escHTML(a)+'</div>';
        });
        html += '</div>';
      }

      // 1. SKUs mapeados
      html += '<div style="background:#f8fafc;border-radius:8px;padding:14px;margin-bottom:14px">';
      html += '<h4 style="margin:0 0 10px;color:#0f172a">1️⃣ SKUs Shopify mapeados a este producto</h4>';
      var skus = d.skus_mapeados||[];
      if(!skus.length){
        html += '<div style="color:#dc2626;font-size:12px">⚠ NINGÚN SKU mapeado. Sin esto el sistema no puede leer Shopify.</div>';
      } else {
        html += '<div style="display:flex;gap:8px;flex-wrap:wrap">';
        skus.forEach(function(s){
          html += '<span style="background:'+(s.activo?'#dbeafe':'#f1f5f9')+';color:'+(s.activo?'#1e3a8a':'#64748b')+';padding:6px 12px;border-radius:6px;font-family:monospace;font-weight:700">'+_escHTML(s.sku)+(s.activo?'':' (inactivo)')+'</span>';
        });
        html += '</div>';
      }
      html += '</div>';

      // 2. Stock por SKU
      html += '<div style="background:#f8fafc;border-radius:8px;padding:14px;margin-bottom:14px">';
      html += '<h4 style="margin:0 0 10px;color:#0f172a">2️⃣ Stock actual por SKU (tabla stock_pt)</h4>';
      html += '<div style="font-size:24px;font-weight:800;color:#0f172a;margin-bottom:10px">'+_fmtMiles(d.stock_total_unidades||0)+' <span style="font-size:13px;font-weight:500;color:#64748b">unidades total</span></div>';
      var stockSku = d.stock_por_sku||[];
      stockSku.forEach(function(s){
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:10px;margin-bottom:8px">';
        html += '<div style="display:flex;justify-content:space-between;font-weight:700;color:#0f172a"><span>'+_escHTML(s.sku)+'</span><span>'+(s.total_unidades||0)+' u · '+(s.lotes_count||0)+' lote(s)</span></div>';
        if((s.lotes||[]).length){
          html += '<table style="width:100%;font-size:11px;margin-top:6px;border-collapse:collapse"><thead style="color:#64748b"><tr><th style="text-align:left;padding:3px">Lote</th><th style="text-align:left">Fecha</th><th style="text-align:right">Inicial</th><th style="text-align:right">Disponible</th><th>Estado</th></tr></thead><tbody>';
          s.lotes.forEach(function(l){
            var col = l.estado === 'AGOTADO' ? '#94a3b8' : '#0f172a';
            html += '<tr style="color:'+col+'"><td style="padding:3px">'+_escHTML(l.lote||'')+'</td><td>'+_escHTML(l.fecha||'')+'</td><td style="text-align:right">'+l.inicial+'</td><td style="text-align:right;font-weight:700">'+l.disponible+'</td><td>'+_escHTML(l.estado)+'</td></tr>';
          });
          html += '</tbody></table>';
        }
        html += '</div>';
      });
      html += '</div>';

      // 3. Ventas por periodo
      html += '<div style="background:#f8fafc;border-radius:8px;padding:14px;margin-bottom:14px">';
      html += '<h4 style="margin:0 0 10px;color:#0f172a">3️⃣ Ventas Shopify por periodo</h4>';
      var vp = d.ventas_por_periodo||{};
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px">';
      ['30d','60d','90d','365d'].forEach(function(p){
        var pp = vp[p]||{};
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:10px"><div style="font-size:11px;color:#64748b">Últimos '+p+'</div><div style="font-size:22px;font-weight:800;color:#0f172a">'+_fmtMiles(pp.total_unidades||0)+'</div><div style="font-size:11px;color:#64748b">'+(pp.velocidad_promedio||0)+' u/día prom.</div></div>';
      });
      html += '</div></div>';

      // 4. Velocidad final usada por motor
      var vf = d.velocidad_final||{};
      html += '<div style="background:#ecfdf5;border:2px solid #10b981;border-radius:8px;padding:14px;margin-bottom:14px">';
      html += '<h4 style="margin:0 0 10px;color:#065f46">4️⃣ Velocidad que USA el motor (con tendencia)</h4>';
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px">';
      html += '<div><div style="font-size:11px;color:#065f46">Base 30d</div><div style="font-size:18px;font-weight:800">'+(vf.velocidad_base||0)+' u/d</div></div>';
      html += '<div><div style="font-size:11px;color:#065f46">Factor tendencia</div><div style="font-size:18px;font-weight:800">×'+(vf.factor_tendencia||1)+'</div></div>';
      html += '<div><div style="font-size:11px;color:#065f46">Velocidad ajustada</div><div style="font-size:22px;font-weight:800;color:#047857">'+(vf.unidades_por_dia||0)+' u/d</div></div>';
      html += '<div><div style="font-size:11px;color:#065f46">Por semana</div><div style="font-size:18px;font-weight:800">'+(vf.unidades_por_semana||0)+' u</div></div>';
      html += '<div><div style="font-size:11px;color:#065f46">Por mes</div><div style="font-size:18px;font-weight:800">'+(vf.unidades_por_mes||0)+' u</div></div>';
      html += '</div></div>';

      // 5. Días de alcance + recomendación
      var alc = d.dias_alcance_hoy;
      var col = alc==null ? '#94a3b8' : (alc<20 ? '#dc2626' : (alc<40 ? '#f97316' : '#10b981'));
      html += '<div style="background:'+col+'15;border:2px solid '+col+';border-radius:8px;padding:14px;margin-bottom:14px">';
      html += '<h4 style="margin:0 0 10px;color:'+col+'">5️⃣ Días de alcance HOY</h4>';
      html += '<div style="font-size:42px;font-weight:800;color:'+col+'">'+(alc==null?'—':alc+' días')+'</div>';
      if(d.fecha_stockout_proyectada){
        html += '<div style="font-size:13px;color:#0f172a">Stockout proyectado: <b>'+_escHTML(d.fecha_stockout_proyectada)+'</b></div>';
      }
      if(d.fecha_lote_recomendada){
        html += '<div style="font-size:13px;color:#0f172a;margin-top:4px">Lote recomendado: <b>'+_escHTML(d.fecha_lote_recomendada)+'</b></div>';
      }
      html += '<div style="font-size:13px;color:'+col+';margin-top:6px;font-weight:700">'+_escHTML(d.urgencia||'')+'</div>';
      html += '</div>';

      // 6. Lote típico + factor g/u
      var l = d.lote||{};
      html += '<div style="background:#f8fafc;border-radius:8px;padding:14px;margin-bottom:14px">';
      html += '<h4 style="margin:0 0 10px;color:#0f172a">6️⃣ Lote y factor g/u</h4>';
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px">';
      html += '<div><div style="font-size:11px;color:#64748b">Factor g/u (motor)</div><div style="font-size:20px;font-weight:800">'+(d.factor_g_por_unidad||0)+' g</div></div>';
      html += '<div><div style="font-size:11px;color:#64748b">Lote default fórmula</div><div style="font-size:20px;font-weight:800">'+(l.lote_default_formula||0)+' kg</div></div>';
      html += '<div><div style="font-size:11px;color:#64748b">Lote típico (mediana)</div><div style="font-size:20px;font-weight:800">'+(l.lote_tipico_historico||0)+' kg</div></div>';
      html += '<div><div style="font-size:11px;color:#64748b">Unidades por lote</div><div style="font-size:20px;font-weight:800;color:#7c3aed">'+_fmtMiles(d.unidades_por_lote||0)+' u</div></div>';
      html += '<div><div style="font-size:11px;color:#64748b">Lote durará</div><div style="font-size:20px;font-weight:800">'+(d.dias_que_durara_lote==null?'—':d.dias_que_durara_lote+' d')+'</div></div>';
      html += '</div>';
      if((l.historico_kg_lista||[]).length){
        html += '<div style="margin-top:8px;font-size:11px;color:#64748b">Histórico Calendar (kg): '+l.historico_kg_lista.join(', ')+'</div>';
      }
      html += '</div>';

      // 7. Cálculo paso a paso
      html += '<div style="background:#1e293b;color:#e2e8f0;border-radius:8px;padding:14px;margin-bottom:14px;font-family:monospace;font-size:12px">';
      html += '<h4 style="margin:0 0 10px;color:#f8fafc;font-family:system-ui">7️⃣ Cálculo paso a paso</h4>';
      (d.ejemplo_calculo||[]).forEach(function(line){
        html += '<div style="margin-bottom:4px">'+_escHTML(line)+'</div>';
      });
      html += '</div>';

      // 8. Últimos pedidos con este producto
      var ult = d.ultimos_10_pedidos_con_este_producto||[];
      if(ult.length || ult.error){
        html += '<div style="background:#f8fafc;border-radius:8px;padding:14px">';
        html += '<h4 style="margin:0 0 10px;color:#0f172a">8️⃣ Últimos pedidos Shopify con este producto</h4>';
        if(ult.error){
          html += '<div style="color:#dc2626;font-size:12px">Error: '+_escHTML(ult.error)+'</div>';
        } else if(!ult.length){
          html += '<div style="color:#64748b;font-size:12px">Sin pedidos recientes encontrados.</div>';
        } else {
          html += '<table style="width:100%;font-size:12px;border-collapse:collapse"><thead style="background:#f1f5f9"><tr><th style="padding:6px;text-align:left">Fecha</th><th style="padding:6px;text-align:left">Pedido</th><th style="padding:6px;text-align:left">SKU</th><th style="padding:6px;text-align:right">Cantidad</th></tr></thead><tbody>';
          ult.forEach(function(u){
            html += '<tr style="border-top:1px solid #e2e8f0"><td style="padding:5px 6px">'+_escHTML(u.fecha||'')+'</td><td style="padding:5px 6px">'+_escHTML(u.pedido||'')+'</td><td style="padding:5px 6px;font-family:monospace">'+_escHTML(u.sku||'')+'</td><td style="padding:5px 6px;text-align:right;font-weight:700">'+(u.cantidad||0)+'</td></tr>';
          });
          html += '</tbody></table>';
        }
        html += '</div>';
      }

      html += '</div>';
      modal.innerHTML = html;
    } catch(e){
      modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:30px;color:#dc2626">Error: '+(e.message||'desconocido')+'<br><button onclick="this.closest(\'div[style*=fixed]\').remove()" style="margin-top:14px;padding:6px 14px">Cerrar</button></div>';
    }
  }

  // ════════════════════════════════════════════════════════════════════
  // 🛒 Plan SOLO Shopify — vista por día (próximo lunes → viernes)
  // ════════════════════════════════════════════════════════════════════
  async function planV2VerSemanaShopify(){
    // Pregunta cuántas semanas
    var semanasStr = prompt('¿Cuántas semanas planear?\n(1 = solo próxima semana, 2 = dos semanas, 4 = mes completo)', '1');
    if(semanasStr === null) return;
    var semanas = Math.max(1, Math.min(8, parseInt(semanasStr) || 1));
    var modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
    modal.onclick = function(e){if(e.target===modal)modal.remove();};
    modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:40px;text-align:center"><div style="font-size:32px">⏳</div><div style="margin-top:10px;color:#64748b">Calculando plan SOLO con Shopify...</div></div>';
    document.body.appendChild(modal);
    try {
      var r = await fetch('/api/planta/plan-semana-shopify?semanas='+semanas);
      var d = await r.json();
      if(d.error){ modal.remove(); alert('Error: '+d.error); return; }
      var k = d.kpis || {};
      var dias = d.dias || [];
      var sin = d.sin_slot || [];
      var urgCol = {critica:'#dc2626',alta:'#f97316',media:'#eab308',baja:'#3b82f6'};
      var urgEmoji = {critica:'🔴',alta:'🟠',media:'🟡',baja:'🔵'};
      var html = '<div style="background:#fff;border-radius:12px;width:1100px;max-width:96vw;max-height:90vh;overflow:auto;padding:24px">';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:18px">';
      html += '<div><h2 style="margin:0;color:#0f172a;font-size:22px">🛒 Plan de la semana — SOLO Shopify</h2>';
      html += '<p style="color:#64748b;font-size:12px;margin:6px 0 0">Sin tener en cuenta el Calendar. Stock = Shopify · Velocidad = ventas 30d · Margen = 20d</p>';
      html += '<p style="color:#0f172a;font-size:13px;margin:8px 0 0"><b>Semana del '+_escHTML(d.semana_inicio)+' al '+_escHTML(d.semana_fin)+'</b> · '+_escHTML(d.patron_distribucion)+' · '+(d.semanas||1)+' semana(s)</p></div>';
      html += '<button onclick="this.closest(\'div[style*=fixed]\').remove()" style="background:#fff;border:1px solid #cbd5e1;padding:6px 12px;border-radius:6px;cursor:pointer">Cerrar ✕</button></div>';
      // KPIs
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-bottom:18px">';
      html += '<div style="background:#f1f5f9;padding:10px;border-radius:8px"><div style="font-size:11px;color:#64748b">Asignadas</div><div style="font-size:22px;font-weight:800;color:#0f172a">'+(k.asignadas_semana||0)+'</div></div>';
      html += '<div style="background:#fee2e2;padding:10px;border-radius:8px"><div style="font-size:11px;color:#991b1b">🔴 Críticas</div><div style="font-size:22px;font-weight:800;color:#dc2626">'+(k.criticas||0)+'</div></div>';
      html += '<div style="background:#fed7aa;padding:10px;border-radius:8px"><div style="font-size:11px;color:#9a3412">🟠 Altas</div><div style="font-size:22px;font-weight:800;color:#f97316">'+(k.altas||0)+'</div></div>';
      html += '<div style="background:#fef3c7;padding:10px;border-radius:8px"><div style="font-size:11px;color:#854d0e">🟡 Medias</div><div style="font-size:22px;font-weight:800;color:#eab308">'+(k.medias||0)+'</div></div>';
      html += '<div style="background:#e0e7ff;padding:10px;border-radius:8px"><div style="font-size:11px;color:#3730a3">🔵 Bajas</div><div style="font-size:22px;font-weight:800;color:#3b82f6">'+(k.bajas||0)+'</div></div>';
      if(k.sin_cupo){
        html += '<div style="background:#fce7f3;padding:10px;border-radius:8px"><div style="font-size:11px;color:#9d174d">⚠ Sin cupo</div><div style="font-size:22px;font-weight:800;color:#be185d">'+k.sin_cupo+'</div></div>';
      }
      html += '</div>';
      // Reglas usadas
      html += '<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:10px 14px;margin-bottom:16px;font-size:12px;color:#78350f">';
      html += '<b>📐 Reglas aplicadas:</b><ul style="margin:6px 0 0 18px;padding:0">';
      (d.reglas||[]).forEach(function(r){ html += '<li>'+_escHTML(r)+'</li>'; });
      html += '</ul></div>';
      // Tabla por día
      if(!dias.length){
        html += '<div style="text-align:center;padding:40px;color:#94a3b8;background:#f8fafc;border-radius:8px">No hay días de producción en el rango</div>';
      } else {
        html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-bottom:16px">';
        dias.forEach(function(dia){
          var bgHeader = dia.producciones_count > 0 ? 'linear-gradient(135deg,#6d28d9,#7c3aed)' : '#94a3b8';
          html += '<div style="background:#fff;border:2px solid '+(dia.producciones_count>0?'#6d28d9':'#e2e8f0')+';border-radius:10px;overflow:hidden">';
          html += '<div style="background:'+bgHeader+';color:#fff;padding:10px 14px"><div style="font-size:11px;opacity:.85;text-transform:uppercase">'+_escHTML(dia.nombre_dia)+'</div><div style="font-size:16px;font-weight:800">'+_escHTML(dia.fecha)+'</div><div style="font-size:11px;margin-top:2px">'+dia.producciones_count+' producci'+(dia.producciones_count===1?'ón':'ones')+'</div></div>';
          if(dia.producciones_count === 0){
            html += '<div style="padding:18px;text-align:center;color:#94a3b8;font-size:12px;font-style:italic">— día libre —</div>';
          } else {
            html += '<div style="padding:8px">';
            dia.producciones.forEach(function(p){
              var col = urgCol[p.urgencia] || '#64748b';
              var emo = urgEmoji[p.urgencia] || '⚪';
              html += '<div style="border-left:4px solid '+col+';background:#f8fafc;padding:8px 10px;margin-bottom:6px;border-radius:0 6px 6px 0">';
              html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:6px">';
              html += '<div style="flex:1"><b style="color:#0f172a;font-size:13px">'+_escHTML(p.producto)+'</b>';
              html += '<div style="font-size:11px;color:#64748b;margin-top:2px">'+p.lote_kg+' kg → '+p.unidades_lote+' u · durará ~'+p.dias_que_durara_lote+'d</div></div>';
              html += '<span style="background:'+col+'22;color:'+col+';padding:2px 6px;border-radius:4px;font-size:10px;font-weight:800">'+emo+' '+p.urgencia.toUpperCase()+'</span>';
              html += '</div>';
              html += '<div style="font-size:10px;color:#475569;margin-top:4px">📦 Stock '+p.stock_actual+'u · 📈 '+p.velocidad_dia+' u/día · ⏰ alcance '+p.dias_alcance+'d</div>';
              html += '<div style="font-size:11px;color:#334155;margin-top:4px;font-style:italic">"'+_escHTML(p.razon)+'"</div>';
              html += '</div>';
            });
            html += '</div>';
          }
          html += '</div>';
        });
        html += '</div>';
      }
      // Sin cupo (overflow)
      if(sin.length){
        html += '<div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;padding:14px;margin-top:14px"><b style="color:#991b1b">⚠ Sin cupo en la(s) semana(s) — '+sin.length+' SKUs</b>';
        html += '<p style="font-size:12px;color:#7f1d1d;margin:6px 0">Estos productos tienen necesidad pero no caben con 1/día. Considera planear más semanas o desbloquear más slots.</p>';
        html += '<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:8px"><thead style="background:#fee2e2"><tr><th style="padding:6px;text-align:left">Producto</th><th style="padding:6px;text-align:right">Lote</th><th style="padding:6px;text-align:right">Días alcance</th><th style="padding:6px;text-align:left">Urgencia</th></tr></thead><tbody>';
        sin.forEach(function(s){
          var col = urgCol[s.urgencia] || '#64748b';
          html += '<tr style="border-top:1px solid #fee2e2"><td style="padding:5px 6px"><b>'+_escHTML(s.producto)+'</b></td><td style="padding:5px 6px;text-align:right">'+s.lote_kg+' kg</td><td style="padding:5px 6px;text-align:right">'+s.dias_alcance+'d</td><td style="padding:5px 6px"><span style="color:'+col+';font-weight:700">'+s.urgencia.toUpperCase()+'</span></td></tr>';
        });
        html += '</tbody></table></div>';
      }
      html += '</div>';
      modal.innerHTML = html;
    } catch(e){
      modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:30px;color:#dc2626">Error: '+(e.message||'desconocido')+'<br><button onclick="this.closest(\'div[style*=fixed]\').remove()" style="margin-top:14px;padding:6px 14px">Cerrar</button></div>';
    }
  }

  // ════════════════════════════════════════════════════════════════════
  // 📆 Plan LARGO — 6 meses / 1 año Shopify rolling forecast
  // ════════════════════════════════════════════════════════════════════
  // Cache para CSV download
  window._planLargoData = null;
  async function planV2VerLargoShopify(meses){
    var modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
    modal.onclick = function(e){if(e.target===modal)modal.remove();};
    modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:50px;text-align:center"><div style="font-size:42px">⏳</div><div style="margin-top:14px;color:#0f172a;font-size:16px;font-weight:700">Calculando plan de '+meses+' meses...</div><div style="margin-top:6px;color:#64748b;font-size:12px">Simulando rolling forecast día-a-día</div></div>';
    document.body.appendChild(modal);
    try {
      var r = await fetch('/api/planta/plan-largo-shopify?meses='+meses);
      var d = await r.json();
      if(d.error){ modal.remove(); alert('Error: '+d.error); return; }
      window._planLargoData = d;
      var k = d.kpis || {};
      var porMes = d.producciones_por_mes || {};
      var porSku = d.producciones_por_sku || {};
      var sinVentas = d.sin_ventas || [];
      var producciones = d.producciones || [];
      var titulo = meses === 12 ? '🗓️ Plan 1 año' : '📆 Plan '+meses+' meses';
      var bgGrad = meses === 12 ? 'linear-gradient(135deg,#06b6d4,#7c3aed)' : 'linear-gradient(135deg,#10b981,#059669)';

      var html = '<div style="background:#fff;border-radius:12px;width:1300px;max-width:96vw;max-height:92vh;overflow:auto;padding:24px">';
      // Header
      html += '<div style="background:'+bgGrad+';color:#fff;border-radius:10px;padding:16px 20px;margin-bottom:18px">';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px">';
      html += '<div><h2 style="margin:0;color:#fff;font-size:24px">'+titulo+' — SOLO Shopify</h2>';
      html += '<p style="color:#cffafe;font-size:12px;margin:4px 0 0">Rolling forecast día-a-día · '+_escHTML(d.fecha_inicio)+' → '+_escHTML(d.fecha_fin)+'</p></div>';
      html += '<div style="display:flex;gap:6px"><button onclick="planLargoCSV()" style="background:rgba(255,255,255,.25);border:1px solid rgba(255,255,255,.4);color:#fff;padding:8px 14px;border-radius:6px;cursor:pointer;font-weight:700;font-size:12px">📥 CSV</button>';
      html += '<button onclick="this.closest(\'div[style*=fixed]\').remove()" style="background:rgba(255,255,255,.25);border:1px solid rgba(255,255,255,.4);color:#fff;padding:8px 14px;border-radius:6px;cursor:pointer;font-weight:700;font-size:12px">Cerrar ✕</button></div>';
      html += '</div></div>';

      // KPIs
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:18px">';
      html += '<div style="background:#ecfdf5;padding:12px;border-radius:8px;border:1px solid #6ee7b7"><div style="font-size:11px;color:#065f46">Total lotes</div><div style="font-size:26px;font-weight:800;color:#047857">'+(k.total_lotes||0)+'</div></div>';
      html += '<div style="background:#eff6ff;padding:12px;border-radius:8px;border:1px solid #93c5fd"><div style="font-size:11px;color:#1e3a8a">Total kg</div><div style="font-size:26px;font-weight:800;color:#1d4ed8">'+_fmtMiles(k.total_kg||0)+'</div></div>';
      html += '<div style="background:#fdf4ff;padding:12px;border-radius:8px;border:1px solid #d8b4fe"><div style="font-size:11px;color:#581c87">SKUs planeados</div><div style="font-size:26px;font-weight:800;color:#7c3aed">'+(k.productos_planeados||0)+'</div></div>';
      html += '<div style="background:#fff7ed;padding:12px;border-radius:8px;border:1px solid #fdba74"><div style="font-size:11px;color:#7c2d12">Lotes/mes</div><div style="font-size:26px;font-weight:800;color:#ea580c">'+(k.promedio_lotes_por_mes||0)+'</div></div>';
      html += '<div style="background:#f1f5f9;padding:12px;border-radius:8px"><div style="font-size:11px;color:#475569">Días con producción</div><div style="font-size:26px;font-weight:800;color:#1e293b">'+(k.dias_con_produccion||0)+'</div></div>';
      if(k.alerta_capacidad){
        html += '<div style="background:#fee2e2;padding:12px;border-radius:8px;border:1px solid #fca5a5"><div style="font-size:11px;color:#991b1b">⚠ Forzados (cap.)</div><div style="font-size:26px;font-weight:800;color:#dc2626">'+(k.forzados_por_capacidad||0)+'</div></div>';
      }
      if(k.productos_sin_ventas){
        html += '<div style="background:#fef3c7;padding:12px;border-radius:8px;border:1px solid #fcd34d"><div style="font-size:11px;color:#92400e">Sin ventas</div><div style="font-size:26px;font-weight:800;color:#d97706">'+k.productos_sin_ventas+'</div></div>';
      }
      html += '</div>';

      // Reglas
      html += '<div style="background:#f0fdfa;border:1px solid #5eead4;border-radius:8px;padding:10px 14px;margin-bottom:18px;font-size:12px;color:#134e4a">';
      html += '<b>📐 Reglas aplicadas:</b><ul style="margin:6px 0 0 18px;padding:0">';
      (d.reglas||[]).forEach(function(r){ html += '<li>'+_escHTML(r)+'</li>'; });
      html += '</ul></div>';

      // Tabs internas
      html += '<div style="display:flex;gap:6px;margin-bottom:14px;border-bottom:2px solid #e2e8f0">';
      html += '<button class="plLargo-tab" data-tab="mes" onclick="planLargoTab(\'mes\')" style="padding:8px 16px;border:none;background:#7c3aed;color:#fff;font-weight:800;cursor:pointer;border-radius:6px 6px 0 0">📅 Por mes</button>';
      html += '<button class="plLargo-tab" data-tab="sku" onclick="planLargoTab(\'sku\')" style="padding:8px 16px;border:none;background:#f1f5f9;color:#475569;font-weight:700;cursor:pointer;border-radius:6px 6px 0 0">📦 Por SKU</button>';
      html += '<button class="plLargo-tab" data-tab="lista" onclick="planLargoTab(\'lista\')" style="padding:8px 16px;border:none;background:#f1f5f9;color:#475569;font-weight:700;cursor:pointer;border-radius:6px 6px 0 0">📋 Lista cronológica</button>';
      if(sinVentas.length){
        html += '<button class="plLargo-tab" data-tab="sin" onclick="planLargoTab(\'sin\')" style="padding:8px 16px;border:none;background:#f1f5f9;color:#475569;font-weight:700;cursor:pointer;border-radius:6px 6px 0 0">⚠ Sin ventas ('+sinVentas.length+')</button>';
      }
      html += '</div>';

      // Vista por mes (default)
      html += '<div id="plLargo-vista-mes">';
      var meses_keys = Object.keys(porMes).sort();
      if(!meses_keys.length){
        html += '<div style="text-align:center;padding:40px;color:#94a3b8;background:#f8fafc;border-radius:8px">No hay producciones planeadas</div>';
      } else {
        html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px">';
        meses_keys.forEach(function(mk){
          var lotes = porMes[mk] || [];
          var totalKg = lotes.reduce(function(s,l){return s+(l.lote_kg||0);},0);
          html += '<div style="background:#fff;border:2px solid #7c3aed;border-radius:10px;overflow:hidden">';
          html += '<div style="background:linear-gradient(135deg,#7c3aed,#7c3aed);color:#fff;padding:10px 14px"><div style="font-size:11px;opacity:.85;text-transform:uppercase">Mes</div><div style="font-size:18px;font-weight:800">'+_escHTML(mk)+'</div><div style="font-size:11px;margin-top:2px">'+lotes.length+' lotes · '+_fmtMiles(Math.round(totalKg))+' kg</div></div>';
          html += '<div style="padding:8px;max-height:300px;overflow:auto">';
          lotes.forEach(function(l){
            html += '<div style="background:#f8fafc;padding:6px 10px;margin-bottom:4px;border-radius:6px;border-left:3px solid #7c3aed;font-size:11px">';
            html += '<b style="color:#0f172a">'+_escHTML(l.producto)+'</b>';
            html += '<div style="color:#64748b">'+_escHTML(l.fecha)+' ('+_escHTML(l.dia_semana)+') · '+l.lote_kg+' kg</div>';
            html += '</div>';
          });
          html += '</div></div>';
        });
        html += '</div>';
      }
      html += '</div>';

      // Vista por SKU (oculta inicialmente)
      html += '<div id="plLargo-vista-sku" style="display:none">';
      var skus_sorted = Object.keys(porSku).sort(function(a,b){return porSku[b].total_lotes - porSku[a].total_lotes;});
      if(!skus_sorted.length){
        html += '<div style="text-align:center;padding:40px;color:#94a3b8">No hay SKUs planeados</div>';
      } else {
        html += '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">';
        html += '<thead style="background:#f1f5f9"><tr>';
        html += '<th style="padding:10px;text-align:left">Producto</th>';
        html += '<th style="padding:10px;text-align:right">Velocidad</th>';
        html += '<th style="padding:10px;text-align:right">Lotes</th>';
        html += '<th style="padding:10px;text-align:right">Total kg</th>';
        html += '<th style="padding:10px;text-align:left">Fechas programadas</th>';
        html += '</tr></thead><tbody>';
        skus_sorted.forEach(function(sku){
          var info = porSku[sku];
          html += '<tr style="border-top:1px solid #e2e8f0">';
          html += '<td style="padding:8px 10px"><b>'+_escHTML(sku)+'</b></td>';
          html += '<td style="padding:8px 10px;text-align:right;font-family:monospace">'+(info.velocidad_dia||0)+' u/d</td>';
          html += '<td style="padding:8px 10px;text-align:right;font-weight:700">'+info.total_lotes+'</td>';
          html += '<td style="padding:8px 10px;text-align:right;font-family:monospace">'+_fmtMiles(Math.round(info.total_kg))+' kg</td>';
          html += '<td style="padding:8px 10px;font-size:11px;color:#64748b">'+(info.fechas||[]).slice(0,8).join(' · ')+(info.fechas.length>8?' +'+(info.fechas.length-8)+' más':'')+'</td>';
          html += '</tr>';
        });
        html += '</tbody></table></div>';
      }
      html += '</div>';

      // Vista lista cronológica
      html += '<div id="plLargo-vista-lista" style="display:none">';
      if(!producciones.length){
        html += '<div style="text-align:center;padding:40px;color:#94a3b8">No hay producciones</div>';
      } else {
        html += '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">';
        html += '<thead style="background:#f1f5f9"><tr>';
        html += '<th style="padding:8px;text-align:left">Fecha</th>';
        html += '<th style="padding:8px;text-align:left">Día</th>';
        html += '<th style="padding:8px;text-align:left">Producto</th>';
        html += '<th style="padding:8px;text-align:right">Lote</th>';
        html += '<th style="padding:8px;text-align:right">Stock antes</th>';
        html += '<th style="padding:8px;text-align:right">Stock después</th>';
        html += '<th style="padding:8px;text-align:left">Motivo</th>';
        html += '</tr></thead><tbody>';
        producciones.forEach(function(p){
          var col = p.forzado_capacidad ? '#dc2626' : '#0f172a';
          html += '<tr style="border-top:1px solid #f1f5f9">';
          html += '<td style="padding:6px 8px;font-family:monospace;color:'+col+'">'+_escHTML(p.fecha)+'</td>';
          html += '<td style="padding:6px 8px;font-size:11px">'+_escHTML(p.dia_semana)+'</td>';
          html += '<td style="padding:6px 8px"><b>'+_escHTML(p.producto)+'</b>'+(p.forzado_capacidad?' <span style="background:#fee2e2;color:#dc2626;padding:1px 5px;border-radius:3px;font-size:9px">⚠ FORZADO</span>':'')+'</td>';
          html += '<td style="padding:6px 8px;text-align:right;font-family:monospace">'+p.lote_kg+' kg</td>';
          html += '<td style="padding:6px 8px;text-align:right;font-family:monospace;color:#64748b">'+p.stock_antes+'</td>';
          html += '<td style="padding:6px 8px;text-align:right;font-family:monospace;color:#15803d">'+p.stock_despues+'</td>';
          html += '<td style="padding:6px 8px;font-size:11px;color:#64748b">'+_escHTML(p.motivo)+'</td>';
          html += '</tr>';
        });
        html += '</tbody></table></div>';
      }
      html += '</div>';

      // Vista sin ventas
      if(sinVentas.length){
        html += '<div id="plLargo-vista-sin" style="display:none">';
        html += '<div style="background:#fef3c7;border:1px solid #fcd34d;padding:12px;border-radius:8px;margin-bottom:12px;color:#78350f;font-size:12px">Estos SKUs están activos pero sin ventas detectadas en Shopify (velocidad &lt; 0.01 u/día). El sistema NO los planeó. Considera marcarlos como descontinuados o revisar la conexión Shopify.</div>';
        html += '<table style="width:100%;border-collapse:collapse;font-size:12px"><thead style="background:#fef3c7"><tr><th style="padding:8px;text-align:left">Producto</th><th style="padding:8px;text-align:right">Stock</th><th style="padding:8px;text-align:left">Razón</th></tr></thead><tbody>';
        sinVentas.forEach(function(s){
          html += '<tr style="border-top:1px solid #fde68a"><td style="padding:6px 8px"><b>'+_escHTML(s.producto)+'</b></td><td style="padding:6px 8px;text-align:right">'+s.stock_inicial+'u</td><td style="padding:6px 8px;color:#78350f">'+_escHTML(s.razon)+'</td></tr>';
        });
        html += '</tbody></table></div>';
      }

      html += '</div>';
      modal.innerHTML = html;
    } catch(e){
      modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:30px;color:#dc2626">Error: '+(e.message||'desconocido')+'<br><button onclick="this.closest(\'div[style*=fixed]\').remove()" style="margin-top:14px;padding:6px 14px">Cerrar</button></div>';
    }
  }

  function planLargoTab(t){
    ['mes','sku','lista','sin'].forEach(function(name){
      var v = document.getElementById('plLargo-vista-'+name);
      if(v) v.style.display = (name===t)?'block':'none';
    });
    var btns = document.querySelectorAll('.plLargo-tab');
    btns.forEach(function(b){
      var a = b.getAttribute('data-tab');
      if(a===t){ b.style.background='#7c3aed'; b.style.color='#fff'; }
      else { b.style.background='#f1f5f9'; b.style.color='#475569'; }
    });
  }

  function planLargoCSV(){
    var d = window._planLargoData;
    if(!d || !d.producciones){ alert('No hay datos cargados'); return; }
    var rows = [['Fecha','Día','Producto','Lote_kg','Unidades','Stock_antes','Stock_después','Velocidad_día','Motivo','Forzado']];
    d.producciones.forEach(function(p){
      rows.push([p.fecha,p.dia_semana,p.producto,p.lote_kg,p.unidades_lote,p.stock_antes,p.stock_despues,p.velocidad_dia,(p.motivo||'').replace(/[\n\r,;]/g,' '),p.forzado_capacidad?'SI':'']);
    });
    var csv = rows.map(function(r){return r.map(function(c){var s=String(c==null?'':c);return /[,;"\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;}).join(',');}).join('\n');
    var blob = new Blob([csv], {type:'text/csv;charset=utf-8'});
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'plan_'+d.horizonte_meses+'meses_'+d.fecha_inicio+'.csv';
    a.click();
  }

  async function recDescontinuar(producto){
    var razon = prompt('¿Por qué descontinuar "'+producto+'"?\n(El sistema dejará de programar producción para este SKU)', 'Ya no se produce');
    if(razon === null) return;
    try {
      var r1 = await fetch('/api/auto-plan/configs/sku');
      var d1 = await r1.json();
      var cfg = (d1.configs||[]).find(function(x){return (x.producto_nombre||'').trim().toUpperCase() === producto.trim().toUpperCase();});
      if(!cfg){ alert('SKU no encontrado'); return; }
      var r = await fetch('/api/planta/sku/'+cfg.id+'/estado', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({estado:'descontinuado', razon: razon})
      });
      if(r.ok){ _toast('✓ '+producto+' descontinuado', 1); planV2CargarRecomendaciones(); }
    } catch(e){ alert('Error: '+e.message); }
  }

  async function recReactivar(producto){
    if(!confirm('¿Reactivar "'+producto+'"? El sistema volverá a programarlo.')) return;
    try {
      var r1 = await fetch('/api/auto-plan/configs/sku');
      var d1 = await r1.json();
      var cfg = (d1.configs||[]).find(function(x){return (x.producto_nombre||'').trim().toUpperCase() === producto.trim().toUpperCase();});
      if(!cfg){ alert('SKU no encontrado'); return; }
      var r = await fetch('/api/planta/sku/'+cfg.id+'/estado', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({estado:'activo'})
      });
      if(r.ok){ _toast('✓ '+producto+' reactivado', 1); planV2CargarRecomendaciones(); }
    } catch(e){ alert('Error: '+e.message); }
  }

  async function planV2CargarRecomendaciones(){
    var box = document.getElementById('pv2-recomendaciones-wrap');
    if(!box) return;
    box.innerHTML = '<div style="text-align:center;padding:20px;color:#94a3b8">🧠 Calculando recomendaciones inteligentes...</div>';
    try {
      var r = await fetch('/api/planta/recomendaciones');
      var d = await r.json();
      var recs = d.recomendaciones || [];
      var k = d.kpis || {};
      // Filtrar: SOLO mostrar accionables (críticas, altas, medias, bajas) y OK
      // Sin_ventas / baja_rotacion / inactivo van colapsados al final
      var accionables = recs.filter(function(x){return ['critica','alta','media','baja'].indexOf(x.urgencia) >= 0;});
      var inactivos = recs.filter(function(x){return ['sin_ventas','baja_rotacion','inactivo'].indexOf(x.urgencia) >= 0;});
      var resumen = '';
      if(k.criticas) resumen += '<span style="background:#dc2626;color:#fff;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:800;margin-right:6px">🚨 '+k.criticas+' CRÍTICAS</span>';
      if(k.altas) resumen += '<span style="background:#d97706;color:#fff;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:800;margin-right:6px">⚠ '+k.altas+' altas</span>';
      if(k.medias) resumen += '<span style="background:#7c3aed;color:#fff;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:700;margin-right:6px">'+k.medias+' medias</span>';
      if(k.bajas) resumen += '<span style="background:#7c3aed;color:#fff;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:600;margin-right:6px">'+k.bajas+' bajas</span>';
      if(k.innecesarias) resumen += '<span style="background:#15803d;color:#fff;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:600;margin-right:6px">✓ '+k.innecesarias+' OK</span>';
      var inact = (k.sin_ventas||0)+(k.baja_rotacion||0)+(k.inactivos||0);
      if(inact) resumen += '<span style="background:#475569;color:#fff;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:600">⊗ '+inact+' inactivos</span>';
      var distInfo = d.distribucion || {};
      var distrChip = distInfo.patron ? '<div style="font-size:10px;color:#94a3b8;margin-top:6px">📅 Distribución: <b>'+distInfo.patron+'</b> · '+(distInfo.razon||'')+'</div>' : '';
      var html = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden">'
        +'<div style="background:linear-gradient(135deg,#1e293b,#0f172a);color:#fff;padding:14px 18px">'
        +'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">'
        +'<div><h3 style="margin:0;color:#fff;font-size:16px">🧠 Recomendaciones Inteligentes</h3><div style="font-size:11px;color:#cbd5e1;margin-top:2px">Stock Shopify + Pipeline (Calendar 14d) + Velocidad ventas → fecha óptima</div></div>'
        +'<div>'+resumen+'</div>'
        +'</div>'
        + distrChip
        +'</div>';
      if(!accionables.length){
        html += '<div style="padding:30px;text-align:center;color:#15803d;font-size:14px">✅ Todos los SKUs cubiertos · ningún producto requiere acción inmediata</div>';
      } else {
        html += '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">'
          +'<thead style="background:#f9fafb;border-bottom:2px solid #e5e7eb"><tr>'
          +'<th style="padding:10px 12px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producto</th>'
          +'<th style="padding:10px 8px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Stock</th>'
          +'<th style="padding:10px 8px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Pipeline</th>'
          +'<th style="padding:10px 8px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Total</th>'
          +'<th style="padding:10px 8px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Días</th>'
          +'<th style="padding:10px 8px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Cadencia</th>'
          +'<th style="padding:10px 8px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Lote típ.</th>'
          +'<th style="padding:10px 12px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Recomendación</th>'
          +'</tr></thead><tbody>';
        accionables.forEach(function(r){
          var urgCol = {critica:'#dc2626',alta:'#d97706',media:'#7c3aed',baja:'#7c3aed'}[r.urgencia] || '#64748b';
          var fechaTxt = '—';
          if(r.fecha_proxima){
            try {
              var dia = new Date(r.fecha_proxima+'T00:00:00').toLocaleDateString('es-CO',{weekday:'short',day:'numeric',month:'short'});
              fechaTxt = dia;
            } catch(e){ fechaTxt = r.fecha_proxima; }
          }
          html += '<tr style="border-top:1px solid #f1f5f9;background:'+(r.urgencia==='critica'?'#fef2f2':r.urgencia==='alta'?'#fffbeb':'#fff')+'">'
            +'<td style="padding:8px 12px"><b style="color:#0f172a">'+_escHTML(r.producto)+'</b><br><span style="font-size:10px;color:#64748b">'+r.velocidad_dia+' u/día</span></td>'
            +'<td style="padding:8px;text-align:right;font-family:monospace">'+r.stock_shopify+'</td>'
            +'<td style="padding:8px;text-align:right;font-family:monospace;color:#7c3aed;font-weight:600">'+(r.pipeline_unidades>0?'+'+r.pipeline_unidades:'—')+'<br><span style="font-size:9px;color:#64748b">'+r.pipeline_kg+'kg</span></td>'
            +'<td style="padding:8px;text-align:right;font-family:monospace;font-weight:700">'+r.stock_total_unidades+'</td>'
            +'<td style="padding:8px;text-align:right;font-family:monospace;font-weight:800;color:'+urgCol+'">'+r.dias_alcance+'d</td>'
            +'<td style="padding:8px;text-align:right;font-size:11px;color:#64748b">'+(r.cadencia_historica_dias?r.cadencia_historica_dias+'d hist':r.cadencia_configurada?r.cadencia_configurada+'d cfg':'—')+'</td>'
            +'<td style="padding:8px;text-align:right;font-family:monospace;font-size:11px">'+r.lote_tipico_kg+'kg</td>'
            +'<td style="padding:8px 12px"><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><span style="background:'+urgCol+';color:#fff;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:800;text-transform:uppercase">'+r.urgencia+'</span><b style="color:#0f172a;font-size:12px;text-transform:capitalize">'+_escHTML(fechaTxt)+'</b></div><div style="font-size:11px;color:#475569;margin-top:4px">'+_escHTML(r.razon)+'</div><div style="margin-top:6px"><button onclick="recDescontinuar(\''+_escAttr(r.producto)+'\')" style="background:#fff;color:#dc2626;border:1px solid #dc2626;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;cursor:pointer">⊗ Descontinuar</button></div></td>'
            +'</tr>';
        });
        html += '</tbody></table></div>';
      }
      // Sección OK (colapsable)
      var oks = recs.filter(function(x){return x.urgencia==='innecesaria'});
      if(oks.length){
        html += '<details style="border-top:1px solid #e5e7eb;padding:8px 16px"><summary style="cursor:pointer;color:#15803d;font-size:12px;font-weight:600">✅ '+oks.length+' SKUs cubiertos (no requieren acción)</summary>'
          +'<div style="margin-top:8px;font-size:11px;color:#64748b;display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:6px">';
        oks.forEach(function(r){
          html += '<div style="background:#f0fdf4;padding:5px 8px;border-radius:4px;border-left:3px solid #15803d">'
            +'<b>'+_escHTML(r.producto)+'</b><br><span style="color:#166534">stock '+r.dias_alcance+'d · '+r.stock_total_unidades+'u total</span></div>';
        });
        html += '</div></details>';
      }
      // Sección INACTIVOS / SIN VENTAS / DESCONTINUADOS (colapsada)
      if(inactivos.length){
        html += '<details style="border-top:1px solid #e5e7eb;padding:8px 16px;background:#f8fafc"><summary style="cursor:pointer;color:#64748b;font-size:12px;font-weight:600">⊗ '+inactivos.length+' SKUs inactivos / sin ventas (no se programa producción)</summary>'
          +'<div style="margin-top:8px;font-size:11px;color:#64748b">';
        inactivos.forEach(function(r){
          var label = r.urgencia==='sin_ventas'?'sin ventas':(r.urgencia==='baja_rotacion'?'baja rotación':r.estado_sku||r.urgencia);
          html += '<div style="display:flex;justify-content:space-between;align-items:center;background:#fff;padding:6px 10px;border-radius:5px;border-left:3px solid #94a3b8;margin-bottom:4px">'
            +'<div><b>'+_escHTML(r.producto)+'</b><br><span style="color:#94a3b8;font-size:10px">'+_escHTML(label)+' · '+_escHTML(r.razon||'')+'</span></div>'
            +'<button onclick="recReactivar(\''+_escAttr(r.producto)+'\')" style="background:#fff;color:#15803d;border:1px solid #15803d;padding:3px 10px;border-radius:5px;font-size:11px;font-weight:600;cursor:pointer">↻ Reactivar</button>'
            +'</div>';
        });
        html += '</div></details>';
      }
      html += '</div>';
      box.innerHTML = html;
    } catch(e){
      box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  async function planV2CargarCalendarStatus(){
    var box = document.getElementById('pv2-calendar-status');
    if(!box) return;
    try {
      var r = await fetch('/api/planta/calendar-debug');
      var d = await r.json();
      if(d.total_eventos === 0){
        box.style.display = 'block';
        box.innerHTML = '⚠ <b>Calendar vacío</b> — verifica GCAL_ICAL_URL en Render. <a href="#" onclick="switchProgTab(\'config\');setTimeout(function(){cfgSubtab(\'calendar\')},150);return false" style="color:#fff;text-decoration:underline">Ir a Configuración</a>';
        return;
      }
      box.style.display = 'block';
      box.innerHTML = '📆 Calendar: <b>'+d.total_eventos+'</b> eventos · ✓ <b style="color:#86efac">'+d.matcheados+'</b> matcheados con productos · '
        +(d.sin_match_aceptable ? '? <b style="color:#fbbf24">'+d.sin_match_aceptable+'</b> sin match — '+'<a href="#" onclick="switchProgTab(\'config\');setTimeout(function(){cfgSubtab(\'calendar\')},150);return false" style="color:#fff;text-decoration:underline">configurar aliases</a>' : '<span style="color:#86efac">100% identificados</span>')
        +' · ⚖ <b>'+d.con_kg_detectados+'</b> con kg parseados';
    } catch(e){ /* silent */ }
  }

  async function planV2CargarCobertura(){
    var box = document.getElementById('pv2-cobertura');
    if(!box) return;
    var meses = parseFloat(_PV2_HORIZONTE);
    var dias = meses < 1 ? 14 : Math.round(meses * 30);
    try {
      var r = await fetch('/api/planta/kpi-cobertura?dias='+dias);
      var d = await r.json();
      var pct = d.cobertura_pct || 0;
      var icon = pct >= 90 ? '✅' : (pct >= 60 ? '⚠️' : '🔴');
      var col = pct >= 90 ? '#10b981' : (pct >= 60 ? '#fbbf24' : '#fca5a5');
      var horizonteLabel = meses < 1 ? 'semana' : (meses+(meses===1?' mes':' meses'));
      box.innerHTML = '<span style="color:'+col+';font-weight:800">'+icon+' '+pct+'% cobertura ('+horizonteLabel+')</span> · '
        +'<b>'+d.en_plan+' / '+d.total_skus+' SKUs</b> con producción en el horizonte (BD + Google Calendar) · '
        +(d.sin_plan && d.sin_plan.length ? '<span style="color:#fca5a5">'+d.sin_plan.length+' SIN plan: '+_escHTML(d.sin_plan.slice(0,3).join(', '))+(d.sin_plan.length>3?'…':'')+'</span>' : '<span style="color:#10b981">Todos los SKUs cubiertos</span>');
    } catch(e){ /* silent */ }
  }

  function abrirNuevoProducto(){
    ['np-nombre','np-lote','np-cadencia','np-fecha','np-lotes'].forEach(function(id){var e=document.getElementById(id); if(e) e.value=(id==='np-merma'?'5':(id==='np-lotes'?'1':''));});
    document.getElementById('np-merma').value = '5';
    document.getElementById('np-categoria').value = '';
    document.getElementById('np-prioritario').checked = false;
    document.getElementById('np-prio-detalle').style.display = 'none';
    document.getElementById('modal-nuevo-producto').style.display = 'flex';
    // Listener checkbox
    var chk = document.getElementById('np-prioritario');
    chk.onchange = function(){
      document.getElementById('np-prio-detalle').style.display = chk.checked ? 'block' : 'none';
    };
  }

  async function guardarNuevoProducto(){
    var body = {
      producto_nombre: (document.getElementById('np-nombre').value||'').trim().toUpperCase(),
      lote_size_kg: parseFloat(document.getElementById('np-lote').value),
      categoria: document.getElementById('np-categoria').value || null,
      cadencia_dias: parseInt(document.getElementById('np-cadencia').value) || null,
      merma_pct: parseFloat(document.getElementById('np-merma').value) || 5,
      prioritario: document.getElementById('np-prioritario').checked,
      fecha_primera_prod: document.getElementById('np-fecha').value || null,
      lotes_inicial: parseInt(document.getElementById('np-lotes').value) || 1,
    };
    if(!body.producto_nombre){ alert('Nombre requerido'); return; }
    if(!body.lote_size_kg || body.lote_size_kg <= 0){ alert('Tamaño lote requerido'); return; }
    try {
      var r = await fetch('/api/planta/producto-nuevo', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body)
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'')); return; }
      document.getElementById('modal-nuevo-producto').style.display='none';
      var msg = '✓ '+body.producto_nombre+' creado';
      if(d.produccion_creada_id) msg += ' (producción #'+d.produccion_creada_id+')';
      _toast(msg, 1);
      planV2Cargar();
      planV2CargarCobertura();
    } catch(e){ alert('Error: '+e.message); }
  }

  async function planV2DetectarCambios(){
    try {
      var r = await fetch('/api/planta/detectar-cambios-demanda');
      var d = await r.json();
      var cambios = d.cambios || [];
      var box = document.getElementById('pv2-comprar-ya');
      if(!cambios.length) return;
      // Renderizar banner de cambios encima del de "comprar ya"
      var existing = document.getElementById('pv2-cambios-demanda');
      if(existing) existing.remove();
      var banner = document.createElement('div');
      banner.id = 'pv2-cambios-demanda';
      banner.style.cssText = 'background:linear-gradient(135deg,#fef3c7,#fde68a);border:2px solid #d97706;border-radius:12px;padding:14px 18px;margin-bottom:14px';
      banner.innerHTML = '<h3 style="margin:0 0 8px;color:#92400e;font-size:14px">📈 '+cambios.length+' cambio(s) de demanda detectado(s)</h3>'
        + '<div style="font-size:12px;color:#78350f;margin-bottom:8px">El sistema detectó que las ventas cambiaron significativamente. Revisa si ajustar el plan:</div>'
        + cambios.map(function(c, i){
          var icono = c.tipo === 'aumento' ? '📈' : '📉';
          var color = c.tipo === 'aumento' ? '#dc2626' : '#7c3aed';
          return '<div style="background:#fff;border:1px solid #fbbf24;border-radius:8px;padding:10px 12px;margin-top:6px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">'
            + '<div style="font-size:12px"><b>'+icono+' '+_escHTML(c.producto)+'</b> · <span style="color:'+color+';font-weight:700">'+(c.cambio_pct>0?'+':'')+c.cambio_pct+'%</span> ('+c.velocidad_base.toFixed(1)+'→'+c.velocidad_reciente.toFixed(1)+' u/d)<br><span style="color:#64748b;font-size:11px">'+_escHTML(c.recomendacion||'Sin recomendación específica')+'</span></div>'
            + (c.fecha_sugerida && c.proxima_produccion_id
              ? '<button onclick="aceptarRecomendacion('+c.proxima_produccion_id+',\''+c.fecha_sugerida+'\')" style="background:#6d28d9;color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer;white-space:nowrap">✓ Aceptar</button>'
              : '<span style="color:#94a3b8;font-size:11px">Sin acción</span>')
            + '</div>';
        }).join('');
      box.parentNode.insertBefore(banner, box);
    } catch(e){ /* silent */ }
  }

  async function aceptarRecomendacion(prodId, nuevaFecha){
    if(!confirm('¿Mover esta producción a '+nuevaFecha+'?')) return;
    try {
      var r = await fetch('/api/planta/produccion/'+prodId+'/aceptar-recomendacion', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({nueva_fecha: nuevaFecha})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'')); return; }
      _toast('✓ Producción movida', 1);
      planV2Init();
    } catch(e){ alert('Error: '+e.message); }
  }

  function planV2Horizonte(meses){
    _PV2_HORIZONTE = meses;
    document.querySelectorAll('.phz-btn').forEach(function(b){
      var act = b.dataset.meses === meses;
      b.style.background = act ? '#fff' : 'rgba(255,255,255,.18)';
      b.style.color = act ? '#6d28d9' : '#fff';
    });
    // Sebastian 7-may-2026: solo refrescar la vista simple · planV2Cargar
    // y planV2CargarCobertura escriben en panels ocultos.
    // Sebastián 12-may-2026 pivote: apaCargar reemplaza pv2CargarProdFaltantes.
    apaCargar();
  }

  // ── Sebastian 5-may-2026 (Luis Enrique): vista simple primaria ─────────
  // Producciones programadas en horizonte + MP/MEE faltantes por producto
  // + boton "Solicitar TODO" que crea SOLs agrupadas por proveedor.
  var _PV2_FALTANTES_DATA = null;

  function _pv2HorizonteDias(){
    var meses = parseFloat(_PV2_HORIZONTE || '2');
    if(meses < 1) return 14;  // semana = 14d (segunda semana incluida)
    return Math.round(meses * 30);
  }

  // ────────────────────────────────────────────────────────────────────────
  // Sebastián 12-may-2026: panel Shopify-driven (APA = Animus Prioridad Agotamiento)
  // Reemplaza el viejo pv2 basado en Calendar. Ahora prioriza por días para
  // agotamiento (stock_pt / velocidad ventas Shopify).
  // ────────────────────────────────────────────────────────────────────────
  function _apaEscHTML(s){return String(s===null||s===undefined?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;');}
  function _apaFmtN(n,d){if(n===null||n===undefined)return '—';return Number(n).toLocaleString('es-CO',{maximumFractionDigits:d||0});}
  // Sebastian 12-may-2026: regla Alejandro · MPs SIEMPRE en gramos con separador miles · NUNCA convertir a kg
  function _apaFmtG(g){if(g===null||g===undefined)return '—';return Math.round(g).toLocaleString('es-CO')+' g';}
  function _apaUrgenciaColor(u){
    return {CRITICO:'#dc2626',ALTA:'#ea580c',MEDIA:'#d97706',BAJA:'#7c3aed',OK:'#15803d',SIN_USO:'#64748b'}[u]||'#64748b';
  }
  function _apaUrgenciaBg(u){
    return {CRITICO:'#fee2e2',ALTA:'#ffedd5',MEDIA:'#fef3c7',BAJA:'#cffafe',OK:'#dcfce7',SIN_USO:'#f1f5f9'}[u]||'#f1f5f9';
  }

  async function apaSyncShopify(){
    var resumen = document.getElementById('apa-resumen');
    if(resumen) resumen.textContent = '⏳ Sincronizando stock desde Shopify…';
    try{
      var r = await fetch('/api/programacion/sync-stock-shopify', {method:'POST'});
      var d = await r.json();
      if(!r.ok || d.ok === false){
        alert('Error sync Shopify: '+(d.error||r.status));
        if(resumen) resumen.textContent = '';
        return;
      }
      apaCargar();
    }catch(e){
      alert('Error red sync Shopify: '+e.message);
      if(resumen) resumen.textContent = '';
    }
  }

  async function apaCargar(){
    var ventana = document.getElementById('apa-ventana');
    var cobertura = document.getElementById('apa-cobertura');
    var v = ventana ? (ventana.value || 60) : 60;
    var c = cobertura ? (cobertura.value || 30) : 30;
    var out = document.getElementById('apa-resultado');
    var resumen = document.getElementById('apa-resumen');
    if(!out) return;
    out.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px">⏳ Calculando prioridad de agotamiento…</div>';
    try{
      var r = await fetch('/api/admin/animus-prioridad-agotamiento?ventana_ventas='+v+'&cobertura_objetivo='+c);
      var d = await r.json();
      if(!d.ok){
        out.innerHTML = '<div style="color:#dc2626;padding:18px;text-align:center">Error: '+_apaEscHTML(d.error||'?')+'</div>';
        return;
      }
      var res = d.resumen || {};
      var params = d.parametros || {};
      if(resumen){
        var partes = [];
        partes.push((res.n_skus||0)+' SKUs');
        if(res.n_critico) partes.push('🔴 '+res.n_critico+' crítico');
        if(res.n_alta) partes.push('🟠 '+res.n_alta+' alta');
        if(res.n_media) partes.push('🟡 '+res.n_media+' media');
        if(res.n_baja) partes.push('🔵 '+res.n_baja+' baja');
        if(res.n_ok) partes.push('✅ '+res.n_ok+' ok');
        if(res.n_sin_uso) partes.push('⚪ '+res.n_sin_uso+' sin uso');
        partes.push((res.kg_total_a_producir||0).toFixed(1)+' kg a producir');
        partes.push(res.n_mps_faltantes+' MPs faltantes');
        // Frescura del sync Shopify (Sebastián 12-may-2026)
        var syncTxt = '';
        var dAtras = params.stock_sync_dias_atras;
        if(dAtras === null || dAtras === undefined){
          syncTxt = '⚠️ Stock nunca sincronizado · clickea 🔄 Sync Shopify';
        } else if(dAtras === 0){
          syncTxt = '📡 Stock sincronizado hoy';
        } else if(dAtras === 1){
          syncTxt = '📡 Stock sincronizado ayer';
        } else if(dAtras <= 2){
          syncTxt = '📡 Stock sincronizado hace '+dAtras+' días';
        } else {
          syncTxt = '⚠️ Stock desactualizado · hace '+dAtras+' días';
        }
        resumen.innerHTML = partes.map(_apaEscHTML).join(' · ') + '<br><span style="color:'+(dAtras>2||dAtras===null?'#dc2626':'#6d28d9')+';font-weight:700">'+_apaEscHTML(syncTxt)+'</span>';
      }
      var skus = d.skus || [];
      var mps = d.mps_necesarias || [];
      var html = '';
      // Tabla SKUs
      html += '<h4 style="margin:6px 0 8px;color:#134e4a;font-size:13px">🛍️ SKUs por urgencia (los primeros se agotan primero)</h4>';
      html += '<table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:18px">';
      html += '<thead><tr style="border-bottom:2px solid #e2e8f0;background:#f8fafc">'+
              '<th style="text-align:left;padding:8px;color:#64748b;font-weight:700">SKU</th>'+
              '<th style="text-align:left;padding:8px;color:#64748b;font-weight:700">Producto base</th>'+
              '<th style="text-align:right;padding:8px;color:#64748b;font-weight:700">Stock</th>'+
              '<th style="text-align:right;padding:8px;color:#64748b;font-weight:700">Vendido</th>'+
              '<th style="text-align:right;padding:8px;color:#64748b;font-weight:700">uds/día</th>'+
              '<th style="text-align:right;padding:8px;color:#64748b;font-weight:700">Días</th>'+
              '<th style="text-align:left;padding:8px;color:#64748b;font-weight:700">Urgencia</th>'+
              '<th style="text-align:right;padding:8px;color:#64748b;font-weight:700">A producir</th>'+
              '</tr></thead><tbody>';
      if(!skus.length){
        html += '<tr><td colspan="8" style="text-align:center;color:#94a3b8;padding:18px">Sin SKUs · sincroniza stock Shopify primero</td></tr>';
      }
      skus.forEach(function(s){
        var bg = _apaUrgenciaBg(s.urgencia);
        var col = _apaUrgenciaColor(s.urgencia);
        html += '<tr style="border-bottom:1px solid #f1f5f9;background:'+(s.urgencia==='CRITICO'?'#fef2f2':'transparent')+'">'+
          '<td style="padding:8px;font-weight:700;color:#1e293b">'+_apaEscHTML(s.sku)+'</td>'+
          '<td style="padding:8px;color:#475569">'+_apaEscHTML(s.producto_base||'—')+'</td>'+
          '<td style="padding:8px;text-align:right;font-variant-numeric:tabular-nums">'+_apaFmtN(s.stock_actual_u)+(s.fuente_stock?' <span title="Fuente del stock (CC=conteo local, SHOPIFY=snapshot Shopify)" style="font-size:9px;color:#94a3b8;font-weight:600">'+_apaEscHTML(s.fuente_stock)+'</span>':'')+'</td>'+
          '<td style="padding:8px;text-align:right;font-variant-numeric:tabular-nums">'+_apaFmtN(s.ventas_periodo_u)+'</td>'+
          '<td style="padding:8px;text-align:right;font-variant-numeric:tabular-nums">'+_apaFmtN(s.velocidad_uds_dia,2)+'</td>'+
          '<td style="padding:8px;text-align:right;font-variant-numeric:tabular-nums;font-weight:'+(s.urgencia==='CRITICO'||s.urgencia==='ALTA'?'700':'400')+'">'+(s.dias_cobertura===null?'∞':_apaFmtN(s.dias_cobertura,1))+'</td>'+
          '<td style="padding:8px"><span style="background:'+bg+';color:'+col+';padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700">'+_apaEscHTML(s.urgencia)+'</span></td>'+
          '<td style="padding:8px;text-align:right;font-variant-numeric:tabular-nums;font-weight:'+(s.kg_a_producir_para_cobertura>0?'700':'400')+';color:'+(s.kg_a_producir_para_cobertura>0?'#dc2626':'#94a3b8')+'">'+(s.kg_a_producir_para_cobertura>0?_apaFmtN(s.kg_a_producir_para_cobertura,1)+' kg':'—')+'</td>'+
          '</tr>';
      });
      html += '</tbody></table>';

      // Sebastián 12-may-2026: 2 categorías de SKUs filtrados con acción clara
      function _apaPintarFiltro(titulo, accion, lista){
        var h = '<details style="margin:0 0 10px;font-size:11px;color:#92400e;background:#fffbeb;border:1px solid #fed7aa;border-radius:6px;padding:6px 10px">'+
                '<summary style="cursor:pointer;font-weight:700">⚠️ '+_apaEscHTML(titulo)+' ('+lista.length+') · clic para ver</summary>'+
                '<div style="margin-top:6px;color:#78350f"><b>Acción:</b> '+_apaEscHTML(accion)+'</div>'+
                '<table style="width:100%;font-size:11px;margin-top:6px;border-collapse:collapse">'+
                '<thead><tr style="color:#78350f"><th style="text-align:left;padding:4px">SKU</th><th style="text-align:right;padding:4px">Vendido</th></tr></thead><tbody>';
        lista.forEach(function(x){
          h += '<tr><td style="padding:4px;font-weight:600">'+_apaEscHTML(x.sku)+'</td><td style="padding:4px;text-align:right">'+_apaFmtN(x.ventas_periodo_u)+'</td></tr>';
        });
        return h + '</tbody></table></details>';
      }
      var huerf = d.skus_huerfano || [];
      var mvac = d.skus_mapeo_vacio || [];
      if(huerf.length){
        html += _apaPintarFiltro(
          huerf.length+' SKUs huérfanos vendiendo (no están en sku_producto_map)',
          'Si es producto real: agregar fila en sku_producto_map · si no, desactivar SKU en Shopify',
          huerf);
      }
      if(mvac.length){
        html += _apaPintarFiltro(
          mvac.length+' SKUs con mapeo vacío vendiendo (producto_nombre en blanco)',
          'Completar la columna producto_nombre en sku_producto_map para estos SKUs',
          mvac);
      }

      // Tabla MPs
      html += '<h4 style="margin:18px 0 8px;color:#134e4a;font-size:13px">📦 MPs necesarias (agregado de SKUs urgentes)</h4>';
      html += '<table style="width:100%;border-collapse:collapse;font-size:12px">';
      html += '<thead><tr style="border-bottom:2px solid #e2e8f0;background:#f8fafc">'+
              '<th style="text-align:left;padding:8px;color:#64748b;font-weight:700">Código</th>'+
              '<th style="text-align:left;padding:8px;color:#64748b;font-weight:700">Nombre</th>'+
              '<th style="text-align:left;padding:8px;color:#64748b;font-weight:700">Proveedor</th>'+
              '<th style="text-align:right;padding:8px;color:#64748b;font-weight:700">Stock actual</th>'+
              '<th style="text-align:right;padding:8px;color:#64748b;font-weight:700">Necesario</th>'+
              '<th style="text-align:right;padding:8px;color:#64748b;font-weight:700">Faltante</th>'+
              '</tr></thead><tbody>';
      if(!mps.length){
        html += '<tr><td colspan="6" style="text-align:center;color:#15803d;padding:18px">✓ Ninguna MP faltante 🎉</td></tr>';
      }
      mps.forEach(function(m){
        html += '<tr style="border-bottom:1px solid #f1f5f9;background:'+(m.faltante_g>0?'#fef2f2':'transparent')+'">'+
          '<td style="padding:8px;font-weight:700">'+_apaEscHTML(m.codigo_mp)+'</td>'+
          '<td style="padding:8px;color:#475569">'+_apaEscHTML(m.nombre)+'</td>'+
          '<td style="padding:8px;color:#475569">'+_apaEscHTML(m.proveedor||'—')+'</td>'+
          '<td style="padding:8px;text-align:right;font-variant-numeric:tabular-nums">'+_apaFmtG(m.stock_actual_g)+'</td>'+
          '<td style="padding:8px;text-align:right;font-variant-numeric:tabular-nums">'+_apaFmtG(m.necesario_g)+'</td>'+
          '<td style="padding:8px;text-align:right;font-variant-numeric:tabular-nums;font-weight:700;color:'+(m.faltante_g>0?'#dc2626':'#15803d')+'">'+_apaFmtG(m.faltante_g)+'</td>'+
          '</tr>';
      });
      html += '</tbody></table>';
      out.innerHTML = html;
    }catch(e){
      out.innerHTML = '<div style="color:#dc2626;padding:18px;text-align:center">Error red: '+_apaEscHTML(e.message)+'</div>';
    }
  }

  async function pv2CargarProdFaltantes(){
    // Sebastian 7-may-2026: vista CONSOLIDADA por PRODUCTO (no por día).
    // Cada producto aparece UNA card con todas sus fechas listadas adentro.
    // Si detectamos clones (mismo producto + mismos lotes + mismas kg
    // dentro de 7 días) marcamos badge ⚠️ y exponemos el botón "Limpiar
    // duplicados" arriba.
    //
    // Soluciona el problema visual de "lo mismo aparece en lunes y miércoles"
    // que era data duplicada en produccion_programada (sync mal hecho).
    var resumen = document.getElementById('pv2-vs-resumen');
    var out = document.getElementById('pv2-vs-resultado');
    var btn = document.getElementById('pv2-vs-btn-solicitar');
    var btnDup = document.getElementById('pv2-vs-btn-dup');
    if(!out) return;
    if(resumen) resumen.textContent = '⏳ Calculando...';
    if(btn) btn.style.display = 'none';
    if(btnDup) btnDup.style.display = 'none';
    out.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">⏳ Construyendo plan...</div>';
    var dias = _pv2HorizonteDias();
    // Sebastián 9-may-2026: por default ocultar atrasadas pendientes >7d
    // (basura vieja). Toggle "Mostrar atrasadas viejas" pasa 999.
    var atrasadasMaxDias = window._PV2_MOSTRAR_ATRASADAS_VIEJAS ? 999 : 7;
    try{
      var url = '/api/programacion/producciones-faltantes?dias='+dias+
                '&atrasadas_max_dias='+atrasadasMaxDias;
      var r = await fetch(url);
      var d = await r.json();
      if(!r.ok){
        out.innerHTML = '<div style="color:#dc2626;padding:18px;text-align:center">Error: '+_escHTML(d.error||r.status)+'</div>';
        return;
      }
      _PV2_FALTANTES_DATA = d;
      var res = d.resumen || {};
      var nDup = res.n_productos_con_duplicados || 0;
      var nReal = res.n_realizadas || 0;
      var nProc = res.n_en_proceso || 0;
      var nAtr = res.n_atrasadas || 0;
      var nPend = res.n_pendientes || 0;
      var nAtrOcultas = res.n_atrasadas_ocultas || 0;
      var pasadoDias = d.pasado_dias || 0;
      if(resumen){
        // Sebastián 8-may-2026: separar pendientes de realizadas en el header
        // para que se vea de un golpe qué falta y qué ya está hecho.
        var partes = [];
        partes.push((res.n_productos_unicos||0)+' productos');
        if(nPend) partes.push(nPend+' pendientes');
        if(nProc) partes.push('▶ '+nProc+' en curso');
        if(nAtr) partes.push('⚠️ '+nAtr+' atrasadas');
        if(nReal) partes.push('✓ '+nReal+' realizadas');
        partes.push(res.n_mps_faltantes+' MPs faltantes');
        partes.push(res.n_mees_faltantes+' MEEs faltantes');
        partes.push(res.n_proveedores_unicos+' proveedores');
        partes.push('ventana -'+pasadoDias+'d / +'+dias+'d');
        if(nDup) partes.push('⚠️ '+nDup+' con clones');
        // Sebastián 9-may-2026: badge con # de atrasadas viejas ocultas +
        // toggle para mostrarlas. La basura abandonada (atrasada-pendiente >7d)
        // queda fuera del panel principal pero accesible si el user la quiere
        // limpiar/cancelar/reprogramar.
        var resumenHtml = partes.map(_escHTML).join(' · ');
        if(nAtrOcultas > 0 && !window._PV2_MOSTRAR_ATRASADAS_VIEJAS){
          resumenHtml += ' · <a href="javascript:void(0)" '+
            'onclick="window._PV2_MOSTRAR_ATRASADAS_VIEJAS=true;pv2CargarProdFaltantes()" '+
            'style="color:#6b7280;background:#f3f4f6;border:1px solid #d1d5db;'+
            'border-radius:4px;padding:1px 7px;text-decoration:none;'+
            'font-size:11px;font-weight:600">📅 Mostrar '+nAtrOcultas+' atrasadas viejas</a>';
        } else if(window._PV2_MOSTRAR_ATRASADAS_VIEJAS){
          resumenHtml += ' · <a href="javascript:void(0)" '+
            'onclick="window._PV2_MOSTRAR_ATRASADAS_VIEJAS=false;pv2CargarProdFaltantes()" '+
            'style="color:#7c3aed;background:#ede9fe;border:1px solid #c4b5fd;'+
            'border-radius:4px;padding:1px 7px;text-decoration:none;'+
            'font-size:11px;font-weight:600">⏪ Ocultar atrasadas viejas</a>';
        }
        resumen.innerHTML = resumenHtml;
      }
      var hayFaltantes = (res.n_mps_faltantes||0)+(res.n_mees_faltantes||0) > 0;
      if(btn) btn.style.display = hayFaltantes ? 'inline-block' : 'none';
      if(btnDup) btnDup.style.display = nDup > 0 ? 'inline-block' : 'none';

      var grupos = d.producciones_agrupadas || [];
      if(!grupos.length){
        out.innerHTML = '<div style="text-align:center;color:#22c55e;padding:30px;font-size:14px">✓ Sin producciones programadas en este horizonte</div>';
        return;
      }

      // Index para acceso rápido en el modal: producto_norm → idx en grupos
      _PV2_FALTANTES_DATA._gruposIdx = {};
      grupos.forEach(function(g, i){
        var k = (g.producto||'').trim().toUpperCase();
        _PV2_FALTANTES_DATA._gruposIdx[k] = i;
      });

      // Sets de faltantes globales para color-coding
      var mpsFaltantesSet = {};
      (d.faltantes_mps||[]).forEach(function(m){ mpsFaltantesSet[m.codigo_mp]=m; });
      var meesFaltantesSet = {};
      (d.faltantes_mees||[]).forEach(function(m){ meesFaltantesSet[(m.codigo||'').toUpperCase()]=m; });

      var hoy = new Date();
      hoy.setHours(0,0,0,0);
      var hoyISO = hoy.toISOString().slice(0,10);
      function _fechaChip(f){
        // Acepta 'YYYY-MM-DD' · devuelve {label, color, bg}
        var iso = (f.fecha||'').slice(0,10);
        var d = new Date(iso+'T00:00:00');
        var dowName = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'][d.getDay()];
        var esHoy = iso === hoyISO;
        var esPasado = iso < hoyISO;
        var lbl = dowName+' '+d.getDate();
        if(esHoy) lbl += ' · HOY';
        else if(esPasado) lbl += ' · ya pasó';
        return {
          label: lbl,
          bg: esHoy ? '#7c3aed' : (esPasado ? '#cbd5e1' : '#6d28d9'),
          color: '#fff',
        };
      }

      // Tabla minimalista · una fila por producto único
      var html = '';
      if(nDup){
        html += '<div style="margin-bottom:10px;padding:10px 14px;'+
                'background:#fef3c7;border:1px solid #fcd34d;'+
                'border-radius:6px;display:flex;align-items:center;'+
                'justify-content:space-between;gap:10px;flex-wrap:wrap">';
        html += '<div style="font-size:12px;color:#78350f">'+
                '<b>⚠️ '+nDup+' producto'+(nDup!==1?'s':'')+
                ' con clones detectados</b> '+
                '<span style="opacity:0.85">(mismo producto + lotes/kg dentro de 7 días)</span>'+
                '</div>';
        html += '<button onclick="pv2LimpiarDuplicados()" '+
                'style="background:#b45309;color:#fff;border:none;'+
                'padding:6px 12px;border-radius:5px;font-size:11px;'+
                'font-weight:700;cursor:pointer">🗑️ Limpiar</button>';
        html += '</div>';
      }
      // Sebastian 8-may-2026 (zero-error): UNA FILA POR (producto × fecha).
      // Antes era una fila por producto con badge "+N" oculto y eso colapsaba
      // visualmente todas las fechas a la primera (ej. AZHC Lun 11 Y Lun 18
      // ambos aparecian solo como "Lun 11 +1"). Ahora cada fecha programada
      // es una fila propia, ordenadas por fecha ascendente. Kg y Lotes son
      // de ESA fecha, Estado sigue siendo agregado a nivel producto (porque
      // las MPs/MEEs faltantes se calculan sumando todas las fechas).
      var filas = [];
      grupos.forEach(function(g, idx){
        (g.fechas||[]).forEach(function(f, fi){
          filas.push({grupo: g, grupoIdx: idx, fecha: f, fechaIdx: fi});
        });
      });
      filas.sort(function(a, b){
        var fa = (a.fecha.fecha||'').slice(0,10);
        var fb = (b.fecha.fecha||'').slice(0,10);
        if(fa !== fb) return fa < fb ? -1 : 1;
        var pa = (a.grupo.producto||'').toUpperCase();
        var pb = (b.grupo.producto||'').toUpperCase();
        return pa < pb ? -1 : (pa > pb ? 1 : 0);
      });

      // Sebastián 12-may-2026: helper para agrupar por semana ISO (Lun-Dom).
      // Antes: lista lineal cruzando semanas sin separador. Ahora cada
      // semana tiene header con rango + count producciones + total kg.
      function _pv2LunesDe(iso){
        if(!iso) return null;
        var d = new Date(iso+'T00:00:00');
        if(isNaN(d.getTime())) return null;
        var dia = d.getDay();
        var offset = dia === 0 ? -6 : 1 - dia;
        d.setDate(d.getDate() + offset);
        return d;
      }
      function _pv2SemanaKey(iso){
        var l = _pv2LunesDe(iso);
        return l ? l.toISOString().slice(0,10) : 'zzz';
      }
      function _pv2FmtFechaCorta(d){
        var meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
        return d.getDate() + ' ' + meses[d.getMonth()];
      }
      var lunesHoyKey = _pv2SemanaKey(hoyISO);

      html += '<table style="width:100%;border-collapse:collapse;font-size:12px">';
      html += '<thead><tr style="border-bottom:2px solid #e2e8f0;'+
              'background:#f8fafc">'+
              '<th style="text-align:left;padding:8px 10px;font-weight:700;'+
              'color:#64748b">Producto</th>'+
              '<th style="text-align:left;padding:8px 10px;font-weight:700;'+
              'color:#64748b;width:120px">Fecha</th>'+
              '<th style="text-align:right;padding:8px 10px;font-weight:700;'+
              'color:#64748b;width:80px">Kg</th>'+
              '<th style="text-align:right;padding:8px 10px;font-weight:700;'+
              'color:#64748b;width:60px">Lotes</th>'+
              '<th style="text-align:left;padding:8px 10px;font-weight:700;'+
              'color:#64748b;width:160px">Estado</th>'+
              '<th style="width:40px"></th>'+
              '</tr></thead><tbody>';
      // Agrupar filas por semana antes de renderizar
      var filasPorSemana = {};
      filas.forEach(function(row){
        var iso = (row.fecha.fecha||'').slice(0,10);
        var key = _pv2SemanaKey(iso) || 'sin-fecha';
        if(!filasPorSemana[key]) filasPorSemana[key] = [];
        filasPorSemana[key].push(row);
      });
      var semanasOrdenadas = Object.keys(filasPorSemana).sort();
      semanasOrdenadas.forEach(function(semanaKey){
        var rowsSemana = filasPorSemana[semanaKey];
        // Header de semana con rango + count + total kg
        if(semanaKey !== 'sin-fecha'){
          var lun = new Date(semanaKey + 'T00:00:00');
          var dom = new Date(lun); dom.setDate(dom.getDate()+6);
          var rangoSem = 'Semana ' + _pv2FmtFechaCorta(lun) + ' – ' + _pv2FmtFechaCorta(dom);
          var esEstaSem = semanaKey === lunesHoyKey;
          var esPasada = semanaKey < lunesHoyKey;
          if(esEstaSem) rangoSem += ' · ESTA SEMANA';
          else if(esPasada) rangoSem += ' · pasada';
          var totalKgSem = rowsSemana.reduce(function(s, row){
            return s + (parseFloat(row.fecha.cantidad_kg)||0);
          }, 0);
          var bgSem = esEstaSem ? '#dcfce7' : (esPasada ? '#f3f4f6' : '#e0f2fe');
          var fgSem = esEstaSem ? '#15803d' : (esPasada ? '#6b7280' : '#7c3aed');
          html += '<tr style="background:'+bgSem+';border-top:2px solid #e2e8f0">'+
                  '<td colspan="6" style="padding:8px 12px;color:'+fgSem+
                  ';font-weight:700;font-size:11.5px;letter-spacing:0.3px">'+
                  '📅 '+_escHTML(rangoSem)+
                  ' <span style="font-weight:500;opacity:0.85;margin-left:8px">· '+
                  rowsSemana.length+' producción(es) · '+totalKgSem.toFixed(1)+' kg</span>'+
                  '</td></tr>';
        }
        rowsSemana.forEach(function(row){
        var g = row.grupo;
        var f = row.fecha;
        var faltMP = g.faltantes_mps_count || 0;
        var faltMEE = g.faltantes_mees_count || 0;
        var hayFalta = (faltMP + faltMEE) > 0;
        var dup = !!g.duplicado_sospechoso;
        var iso = (f.fecha||'').slice(0,10);
        var dt = iso ? new Date(iso+'T00:00:00') : null;
        var fechaLbl = '-';
        var fechaCol = '#64748b';
        if(dt && !isNaN(dt.getTime())){
          var dowName = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'][dt.getDay()];
          fechaLbl = dowName+' '+dt.getDate();
          var esHoy = iso === hoyISO;
          var esPasado = iso < hoyISO;
          if(esHoy){ fechaLbl += ' · HOY'; fechaCol = '#7c3aed'; }
          else if(esPasado){ fechaLbl += ' · ya pasó'; fechaCol = '#94a3b8'; }
          else { fechaCol = '#6d28d9'; }
        }
        // Sebastián 8-may-2026 · estado_display: realizada / en_proceso /
        // atrasada / pendiente. Cada uno con tag visual distinto. Las
        // realizadas y en_proceso NO muestran botón borrar (ya descontaron
        // inventario · borrarlas crearía drift).
        var sd = f.estado_display || 'pendiente';
        var rowBg = '';
        var rowOpacity = '1';
        var estadoTxt, estadoCol;
        if(sd === 'realizada'){
          estadoTxt = '✓ Realizada';
          estadoCol = '#15803d';
          rowBg = '#f0fdf4';
          rowOpacity = '0.85';
        } else if(sd === 'en_proceso'){
          estadoTxt = '▶ En proceso';
          estadoCol = '#b45309';
          rowBg = '#fffbeb';
        } else if(sd === 'atrasada'){
          estadoTxt = '⚠ Atrasada';
          if(hayFalta) estadoTxt += ' · falta '+faltMP+(faltMP===1?' MP':' MPs');
          estadoCol = '#b91c1c';
          rowBg = '#fef2f2';
        } else if(hayFalta){
          estadoTxt = 'Falta '+faltMP+(faltMP===1?' MP':' MPs');
          if(faltMEE) estadoTxt += ' · '+faltMEE+(faltMEE===1?' MEE':' MEEs');
          estadoCol = '#dc2626';
        } else {
          estadoTxt = '✓ Listo';
          estadoCol = '#16a34a';
        }
        var pidArrJSON = JSON.stringify([f.pid]).replace(/"/g,'&quot;');
        var rowLabel = (g.producto||'')+' · '+fechaLbl;
        var rowStyle = 'border-bottom:1px solid #f1f5f9;cursor:pointer;'+
                       'opacity:'+rowOpacity+';';
        if(rowBg) rowStyle += 'background:'+rowBg+';';
        html += '<tr onclick="pv2VerProductoAgrupado('+row.grupoIdx+')" '+
                'style="'+rowStyle+'" '+
                'onmouseover="this.style.background=\'#f1f5f9\'" '+
                'onmouseout="this.style.background=\''+(rowBg||'transparent')+'\'">';
        html += '<td style="padding:8px 10px;font-weight:600;color:#1e293b">'+
                _escHTML(g.producto||'');
        if(dup){
          html += ' <span style="background:#fef3c7;color:#92400e;'+
                  'padding:1px 6px;border-radius:3px;font-size:9px;'+
                  'font-weight:700;margin-left:4px" title="Clones detectados">CLONES</span>';
        }
        html += '</td>';
        html += '<td style="padding:8px 10px;color:'+fechaCol+';font-weight:600">'+
                _escHTML(fechaLbl)+'</td>';
        html += '<td style="padding:8px 10px;text-align:right;color:#475569">'+
                Number(f.cantidad_kg||0).toFixed(1)+'</td>';
        html += '<td style="padding:8px 10px;text-align:right;color:#475569">'+
                (f.lotes||1)+'</td>';
        html += '<td style="padding:8px 10px;color:'+estadoCol+';'+
                'font-weight:600">'+_escHTML(estadoTxt)+'</td>';
        // Sebastián 8-may-2026: solo permitir borrar pendientes/atrasadas.
        // Realizadas y en_proceso ya tocaron inventario · borrarlas crea drift.
        var puedeBorrar = (sd === 'pendiente' || sd === 'atrasada');
        if(f.pid && puedeBorrar){
          html += '<td style="padding:6px 8px;text-align:right">'+
                  '<button onclick="event.stopPropagation();pv2QuitarProducto('+
                  pidArrJSON+',\''+_escHTML(rowLabel)+'\')" '+
                  'title="Borrar SOLO esta producción del horizonte (otras fechas no se tocan)" '+
                  'style="background:transparent;border:1px solid #fecaca;color:#dc2626;'+
                  'border-radius:4px;padding:3px 8px;font-size:11px;cursor:pointer">🗑️</button>'+
                  '</td>';
        } else {
          html += '<td></td>';
        }
        html += '</tr>';
        });
      });
      html += '</tbody></table>';

      out.innerHTML = html;
    }catch(e){
      out.innerHTML = '<div style="color:#dc2626;padding:18px;text-align:center">Error red: '+_escHTML(e.message)+'</div>';
    }
  }

  // Sebastian 7-may-2026: limpiar duplicados de produccion_programada · 2 pasos
  async function pv2LimpiarDuplicados(){
    var dias = _pv2HorizonteDias();
    function _post(body){
      return fetch('/api/programacion/limpiar-duplicados-producciones', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
      });
    }
    try{
      var rDry = await _post({dry_run: true, horizonte_dias: dias});
      var dDry = await rDry.json();
      if(!rDry.ok){ alert('Error preview: '+(dDry.error||rDry.status)); return; }
      if((dDry.producciones_a_borrar||0) === 0){
        alert('✓ No hay duplicados que limpiar en este horizonte.');
        return;
      }
      var detalle = (dDry.plan||[]).slice(0,8).map(function(g){
        var fs = g.fechas.map(function(f){
          return f.fecha+(f.accion==='BORRAR'?' (BORRAR)':' (KEEP)');
        }).join(' · ');
        return '  · '+g.producto+': '+fs;
      }).join('\n');
      if((dDry.plan||[]).length > 8){
        detalle += '\n  ... y '+((dDry.plan||[]).length-8)+' grupos más';
      }
      var msg = 'LIMPIAR DUPLICADOS de produccion_programada\n\n'+
        'Va a borrar '+dDry.producciones_a_borrar+' producciones duplicadas\n'+
        '(en '+dDry.grupos_detectados+' grupos · horizonte '+dias+'d)\n\n'+
        'Conserva la fecha más temprana de cada grupo.\n'+
        'No toca producciones ya descontadas / canceladas / iniciadas.\n\n'+
        'Plan:\n'+detalle+'\n\n¿Confirmar?';
      if(!confirm(msg)) return;

      var r = await _post({dry_run: false, horizonte_dias: dias});
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
      alert('✓ '+d.mensaje);
      pv2CargarProdFaltantes();
    }catch(e){ alert('Error de red: '+e.message); }
  }

  // Sebastian 7-may-2026: forzar sync con Google Calendar (espejo total).
  // force_mirror=true · HARD DELETE de cualquier producción del horizonte
  // que NO esté en Calendar (manual + calendar), excepto las ya iniciadas
  // o descontadas. Garantiza que la app refleje EXACTAMENTE Calendar.
  async function pv2ReSyncCalendar(){
    var resumen = document.getElementById('pv2-vs-resumen');
    var msg = 'Re-sync ESPEJO con Google Calendar\n\n'+
              'Va a:\n'+
              ' · Insertar las producciones nuevas que aparezcan en Calendar\n'+
              ' · BORRAR las del horizonte que ya NO están en Calendar\n'+
              '   (sin importar si las creó alguien manualmente)\n\n'+
              'NO toca producciones ya iniciadas o que descontaron inventario.\n\n'+
              '¿Continuar?';
    if(!confirm(msg)) return;
    if(resumen) resumen.textContent = '⏳ Re-sync con Calendar (espejo)...';
    try{
      var r = await fetch('/api/programacion/checklist/sync-calendar?dias=120&force_mirror=true',
                          {method:'POST'});
      var d = await r.json();
      if(!r.ok){
        alert('Error sync: '+(d.error||r.status));
        if(resumen) resumen.textContent = '';
        return;
      }
      // Recargar la vista para ver el resultado
      pv2CargarProdFaltantes();
    }catch(e){
      alert('Error de red al sync: '+e.message);
      if(resumen) resumen.textContent = '';
    }
  }

  // Sebastian 7-may-2026: borrar producciones de un producto · solo admin.
  // Hard delete · útil para limpiar fantasmas que sobrevivieron al sync
  // (entries manuales viejas con fecha distinta a Calendar).
  // Si NADA se borra, llamamos al debug endpoint y mostramos por qué.
  async function pv2QuitarProducto(pids, productoNombre){
    if(!pids || !pids.length){ return; }
    var n = pids.length;
    var msg = 'BORRAR '+n+' producción'+(n!==1?'es':'')+' de "'+productoNombre+'"?\n\n'+
              'Esto las borra DEFINITIVAMENTE de la DB.\n'+
              'Si la producción está en Calendar, volverá a aparecer al re-sync.\n\n'+
              '¿Confirmar?';
    if(!confirm(msg)) return;
    var fails = 0; var ok = 0;
    for(var i=0; i<pids.length; i++){
      try{
        var r = await fetch('/api/programacion/produccion-programada/'+pids[i]+'/borrar',
                            {method:'DELETE'});
        if(r.ok) ok++; else fails++;
      }catch(e){ fails++; }
    }
    if(ok > 0 && fails === 0){
      // todo OK · refresh
      pv2CargarProdFaltantes();
      return;
    }
    // Algo falló · pedir debug para entender por qué
    try{
      var rDbg = await fetch('/api/programacion/debug-producto/'+
                              encodeURIComponent(productoNombre));
      var dbg = await rDbg.json();
      if(rDbg.ok && (dbg.entries_db||[]).length){
        var protegidas = dbg.entries_db.filter(function(e){ return e.protegida_del_sync; });
        if(protegidas.length){
          var detalle = protegidas.map(function(e){
            return '  · id='+e.id+' fecha='+e.fecha_programada+
                   ' razón: '+(e.razones_guard||[]).join(', ');
          }).join('\n');
          alert('Borradas '+ok+'/'+n+'\n\n'+
                protegidas.length+' protegida(s) por guard de seguridad:\n'+
                detalle+'\n\n'+
                'Estas tienen inicio_real_at o inventario_descontado_at set ' +
                '(ya iniciaron / descontaron). Si querés forzar borrado, '+
                'pedile a Alejandro que reverta el "iniciar producción" en '+
                'Operación Live · o contacta a soporte para hard delete admin.');
          pv2CargarProdFaltantes();
          return;
        }
      }
      alert('Borradas '+ok+'/'+n+' · '+fails+' fallaron · '+
            '¿permisos de admin? (debug endpoint disponible: '+
            '/api/programacion/debug-producto/'+encodeURIComponent(productoNombre)+')');
    }catch(_e){
      alert('Borradas '+ok+'/'+n+' · '+fails+' fallaron');
    }
    pv2CargarProdFaltantes();
  }

  // Click en card del producto agrupado · abre modal con MPs/MEEs faltantes
  // y lista de fechas. Reusa el modal existente con vista consolidada.
  function pv2VerProductoAgrupado(idx){
    if(!_PV2_FALTANTES_DATA || !_PV2_FALTANTES_DATA.producciones_agrupadas) return;
    var g = _PV2_FALTANTES_DATA.producciones_agrupadas[idx];
    if(!g) return;
    var d = _PV2_FALTANTES_DATA;
    var mpsFalt = {}; (d.faltantes_mps||[]).forEach(function(m){ mpsFalt[m.codigo_mp]=m; });
    var meesFalt = {}; (d.faltantes_mees||[]).forEach(function(m){ meesFalt[(m.codigo||'').toUpperCase()]=m; });

    document.getElementById('mpd-titulo').textContent = g.producto || 'Producto';
    var fechasLbl = (g.fechas||[]).map(function(f){
      return (f.fecha||'').slice(0,10)+' ('+(f.lotes||1)+'L·'+(f.cantidad_kg||0)+'kg)';
    }).join(' · ');
    var sub = (g.fechas||[]).length+' fecha'+((g.fechas||[]).length!==1?'s':'')+
              ' · '+(g.total_lotes||0)+' lotes · '+
              Number(g.total_kg||0).toFixed(1)+' kg total';
    if(g.duplicado_sospechoso){
      sub += ' · ⚠️ DUPLICADOS DETECTADOS';
    }
    var subEl = document.getElementById('mpd-subtitulo');
    if(subEl){
      subEl.textContent = sub;
      subEl.title = fechasLbl;
    }

    // MPs · usa los necesarios agregados del grupo
    var bodyMP = document.getElementById('mpd-mps');
    if(bodyMP){
      var mps = (g.mps_necesarias||[]).map(function(m){
        var f = mpsFalt[m.codigo_mp];
        var col = f ? '#dc2626' : '#16a34a';
        var bg = f ? '#fef2f2' : '#f0fdf4';
        var statusTxt = f
          ? ('FALTA '+Number(f.faltante_g||0).toLocaleString('es-CO')+' g')
          : 'OK';
        return '<div style="background:'+bg+';border-left:3px solid '+col+
               ';padding:8px 12px;margin-bottom:4px;border-radius:0 4px 4px 0">'+
               '<div style="font-weight:700;font-size:12px;color:#1e293b">'+
                _escHTML(m.nombre||m.codigo_mp)+'</div>'+
               '<div style="font-size:11px;color:'+col+'">'+
               'Necesita '+Number(m.necesario_g||0).toLocaleString('es-CO')+' g · '+
               statusTxt+'</div>'+
               '</div>';
      }).join('');
      bodyMP.innerHTML = mps || '<div style="color:#94a3b8;font-size:11px;padding:6px">Sin MPs necesarias</div>';
    }

    // MEEs
    var bodyMEE = document.getElementById('mpd-mees');
    if(bodyMEE){
      var mees = (g.mees_necesarios||[]).map(function(m){
        var f = meesFalt[(m.codigo||'').toUpperCase()];
        var col = f ? '#dc2626' : '#16a34a';
        var bg = f ? '#fef2f2' : '#f0fdf4';
        var statusTxt = f
          ? ('FALTA '+Number(f.faltante_u||0).toLocaleString('es-CO')+' u')
          : 'OK';
        return '<div style="background:'+bg+';border-left:3px solid '+col+
               ';padding:8px 12px;margin-bottom:4px;border-radius:0 4px 4px 0">'+
               '<div style="font-weight:700;font-size:12px;color:#1e293b">'+
                _escHTML(m.descripcion||m.codigo)+'</div>'+
               '<div style="font-size:11px;color:'+col+'">'+
               'Necesita '+Number(m.necesario_unidades||0).toLocaleString('es-CO')+' u · '+
               statusTxt+'</div>'+
               '</div>';
      }).join('');
      bodyMEE.innerHTML = mees || '<div style="color:#94a3b8;font-size:11px;padding:6px">Sin MEEs necesarios</div>';
    }

    document.getElementById('modal-prod-detalle').style.display = 'flex';
  }

  // Sebastian 5-may-2026: click producción en calendario · abre modal
  function pv2VerProd(idx){
    if(!_PV2_FALTANTES_DATA || !_PV2_FALTANTES_DATA.producciones) return;
    var p = _PV2_FALTANTES_DATA.producciones[idx];
    if(!p) return;
    var d = _PV2_FALTANTES_DATA;
    var mpsFalt = {}; (d.faltantes_mps||[]).forEach(function(m){ mpsFalt[m.codigo_mp]=m; });
    var meesFalt = {}; (d.faltantes_mees||[]).forEach(function(m){ meesFalt[(m.codigo||'').toUpperCase()]=m; });

    document.getElementById('mpd-titulo').textContent = p.producto || 'Producción';
    var sub = (p.fecha||'')+' · '+(p.lotes||1)+' lote'+(p.lotes>1?'s':'')+
              ' · '+(p.cantidad_kg||0)+'kg';
    if(p.area_nombre) sub += ' · '+p.area_nombre;
    if(p.estado && p.estado !== 'pendiente') sub += ' · '+p.estado;
    document.getElementById('mpd-subtitulo').textContent = sub;

    var body = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">';
    // MPs
    body += '<div><div style="font-weight:700;color:#475569;font-size:11px;text-transform:uppercase;margin-bottom:8px">Materias primas</div>';
    if((p.mps_necesarias||[]).length){
      body += '<table style="width:100%;font-size:12px;border-collapse:collapse"><tbody>';
      p.mps_necesarias.forEach(function(m){
        var f = mpsFalt[m.codigo_mp];
        var cl = f ? '#dc2626' : '#16a34a';
        body += '<tr style="border-bottom:1px solid #f1f5f9">';
        body += '<td style="padding:5px 6px"><b>'+_escHTML(m.nombre||m.codigo_mp)+'</b></td>';
        body += '<td style="padding:5px 6px;text-align:right;color:#64748b">'+(m.necesario_g||0).toLocaleString()+' g</td>';
        body += '<td style="padding:5px 6px;text-align:right;color:'+cl+';font-weight:700">'+
                (f ? ('falta '+(f.faltante_g||0).toLocaleString()+' g') : '✓')+'</td>';
        body += '</tr>';
      });
      body += '</tbody></table>';
    } else {
      body += '<div style="color:#94a3b8;font-size:12px">Sin fórmula registrada · revisar /tecnica</div>';
    }
    body += '</div>';
    // MEEs
    body += '<div><div style="font-weight:700;color:#475569;font-size:11px;text-transform:uppercase;margin-bottom:8px">Envases &amp; empaque</div>';
    if((p.mees_necesarios||[]).length){
      body += '<table style="width:100%;font-size:12px;border-collapse:collapse"><tbody>';
      p.mees_necesarios.forEach(function(m){
        var fk = (m.codigo||'').toUpperCase();
        var f = meesFalt[fk];
        var cl = f ? '#dc2626' : '#16a34a';
        body += '<tr style="border-bottom:1px solid #f1f5f9">';
        body += '<td style="padding:5px 6px"><b>'+_escHTML(m.descripcion||m.codigo)+'</b><br><span style="color:#94a3b8;font-size:10px">'+_escHTML(m.tipo||'')+'</span></td>';
        body += '<td style="padding:5px 6px;text-align:right;color:#64748b">'+(m.necesario_unidades||0).toLocaleString()+' u</td>';
        body += '<td style="padding:5px 6px;text-align:right;color:'+cl+';font-weight:700">'+
                (f ? ('falta '+(f.faltante_u||0).toLocaleString()+' u') : '✓')+'</td>';
        body += '</tr>';
      });
      body += '</tbody></table>';
    } else {
      body += '<div style="color:#94a3b8;font-size:12px">Sin envases configurados · revisar /admin → sku_mee_config</div>';
    }
    body += '</div>';
    body += '</div>';

    document.getElementById('mpd-body').innerHTML = body;
    document.getElementById('modal-prod-detalle').style.display = 'flex';
  }

  function cerrarProdDetalle(){
    document.getElementById('modal-prod-detalle').style.display = 'none';
  }

  async function pv2SolicitarFaltantesBulk(){
    if(!_PV2_FALTANTES_DATA) return;
    var dias = _PV2_FALTANTES_DATA.horizonte_dias || _pv2HorizonteDias();
    var nMps = (_PV2_FALTANTES_DATA.faltantes_mps||[]).length;
    var nMees = (_PV2_FALTANTES_DATA.faltantes_mees||[]).length;
    var provs = _PV2_FALTANTES_DATA.resumen.n_proveedores_unicos || 0;
    if(!confirm('Crear solicitudes de compra agrupadas por proveedor para todo lo faltante?\n\n'+
                '  • '+nMps+' MPs faltantes\n'+
                '  • '+nMees+' MEEs faltantes\n'+
                '  • '+provs+' proveedores distintos (cada uno = 1 solicitud)\n'+
                '  • Horizonte: '+dias+' días\n\n'+
                'Las solicitudes llegarán a Compras como Pendientes y Catalina las procesará.\n\n'+
                'Continuar?')) return;
    var btn = document.getElementById('pv2-vs-btn-solicitar');
    if(btn){ btn.disabled = true; btn.textContent = 'Generando...'; }
    try{
      var r = await fetch('/api/programacion/solicitar-faltantes-bulk', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({dias: dias, urgencia: 'Alta'})
      });
      var d = await r.json();
      if(btn){ btn.disabled = false; btn.innerHTML = '🛒 Solicitar TODO faltante'; }
      if(!r.ok){
        alert('Error: '+(d.error||r.status));
        return;
      }
      var msg = '✓ '+d.mensaje+'\n\n';
      (d.solicitudes_creadas||[]).slice(0,8).forEach(function(s){
        msg += '  • '+s.numero+' · '+s.proveedor+' · '+s.items_count+' items\n';
      });
      if((d.solicitudes_creadas||[]).length > 8) msg += '  ... y '+((d.solicitudes_creadas||[]).length-8)+' más\n';
      msg += '\nVer todas en /compras → tab Solicitudes';
      alert(msg);
      pv2CargarProdFaltantes();  // refresh
    }catch(e){
      if(btn){ btn.disabled = false; btn.innerHTML = '🛒 Solicitar TODO faltante'; }
      alert('Error red: '+e.message);
    }
  }

  async function planV2Cargar(){
    var vista = document.getElementById('pv2-vista');
    var kpis = document.getElementById('pv2-kpis');
    if(!vista) return;
    // Sebastian 5-may-2026: cargar vista simple de Luis Enrique en paralelo.
    // No bloquea el flujo · si falla, el resto del Plan sigue funcionando.
    try{ pv2CargarProdFaltantes(); }catch(e){/* no critico */}
    vista.innerHTML = '<div style="text-align:center;padding:40px;color:#94a3b8">Cargando plan...</div>';
    var meses = parseFloat(_PV2_HORIZONTE);
    try {
      // Para horizonte ≤ 2 meses: pintar grid calendario visual ARRIBA + cards abajo
      var calendarHtml = '';
      if(meses <= 2){
        try {
          var diasGrid = meses < 1 ? 14 : Math.round(meses * 30);
          var calR = await fetch('/api/planta/calendar-eventos-plan?dias='+diasGrid);
          var calD = await calR.json();
          calendarHtml = planV2RenderCalendarGrid(calD.events || [], diasGrid);
        } catch(e){ /* sin calendar grid si falla */ }
      }
      if(meses < 1){
        var r = await fetch('/api/planta/plan-semanal-v2?dias=14');
        var d = await r.json();
        _PV2_DATA = d;
        planV2RenderSemanaV2(d);
        if(calendarHtml) vista.innerHTML = calendarHtml + vista.innerHTML;
      } else {
        var r = await fetch('/api/planta/forecast?meses='+Math.round(meses));
        var d = await r.json();
        _PV2_DATA = d;
        planV2RenderForecast(d, Math.round(meses));
        if(calendarHtml) vista.innerHTML = calendarHtml + vista.innerHTML;
      }
    } catch(e){
      vista.innerHTML = '<div style="color:#dc2626;padding:20px">Error: '+e.message+'</div>';
    }
  }

  // ════════════════════════════════════════════════════════════════════
  // VISTA CALENDARIO GRID — pinta los eventos del Calendar como grid mensual
  // ════════════════════════════════════════════════════════════════════
  function planV2RenderCalendarGrid(events, diasHorizonte){
    // Sebastián 1-may-2026: si no hay eventos, NO devolver caja — el empty
    // state del Timeline ya lo cubre con mensaje + botón Diagnosticar.
    if(!events || !events.length){
      return '';
    }
    // Agrupar eventos por fecha
    var porFecha = {};
    events.forEach(function(e){
      if(!porFecha[e.fecha]) porFecha[e.fecha] = [];
      porFecha[e.fecha].push(e);
    });
    // Determinar rango: hoy + N días
    var hoy = new Date();
    hoy.setHours(0,0,0,0);
    var fin = new Date(hoy.getTime() + diasHorizonte*86400000);
    // Ajustar inicio al lunes anterior, fin al domingo siguiente
    var inicio = new Date(hoy);
    var dowInicio = (inicio.getDay() + 6) % 7;  // 0=Mon
    inicio.setDate(inicio.getDate() - dowInicio);
    var dowFin = (fin.getDay() + 6) % 7;
    fin.setDate(fin.getDate() + (6 - dowFin));

    var nombreMeses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
    var nombreDias = ['L','M','M','J','V','S','D'];

    var html = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px;margin-bottom:14px">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">';
    html += '<b style="color:#0f172a;font-size:14px">📅 Calendario de Producción</b>';
    html += '<span style="font-size:11px;color:#64748b">'+events.length+' eventos · '+inicio.toLocaleDateString('es-CO',{day:'numeric',month:'short'})+' → '+fin.toLocaleDateString('es-CO',{day:'numeric',month:'short'})+'</span>';
    html += '</div>';

    // Headers de días
    html += '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin-bottom:6px">';
    nombreDias.forEach(function(d,i){
      var col = i>=5 ? '#94a3b8' : '#475569';
      html += '<div style="text-align:center;font-size:10px;color:'+col+';font-weight:700;text-transform:uppercase;padding:4px">'+d+'</div>';
    });
    html += '</div>';

    // Grid de días
    html += '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px">';
    var cur = new Date(inicio);
    var hoyISO = new Date().toISOString().slice(0,10);
    while(cur <= fin){
      var iso = cur.toISOString().slice(0,10);
      var dow = (cur.getDay() + 6) % 7;
      var esWeekend = dow >= 5;
      var esHoy = iso === hoyISO;
      var dentroRango = cur >= hoy && cur <= new Date(hoy.getTime() + diasHorizonte*86400000);
      var evs = porFecha[iso] || [];
      var bg = esHoy ? '#fef3c7' : esWeekend ? '#f8fafc' : (dentroRango?'#fff':'#f1f5f9');
      var border = esHoy ? '2px solid #f59e0b' : '1px solid #e2e8f0';
      html += '<div style="background:'+bg+';border:'+border+';border-radius:6px;min-height:80px;padding:5px;font-size:10px;'+(dentroRango?'':'opacity:.5')+'">';
      html += '<div style="font-weight:700;color:'+(esHoy?'#92400e':esWeekend?'#94a3b8':'#0f172a')+';margin-bottom:3px">'+cur.getDate()+(cur.getDate()===1?' '+nombreMeses[cur.getMonth()]:'')+'</div>';
      evs.slice(0,3).forEach(function(e){
        var titulo = (e.titulo||'').replace(/[🌿💋🧴🧬🍊🚿💄🆕💡🔬✨🧪☕🌿💫📦👁️💧🛍️🏖️]/g,'').trim();
        html += '<div title="'+_escHTML(e.titulo||'')+'" style="background:rgba(99,102,241,.15);color:#3730a3;padding:2px 4px;border-radius:3px;margin-bottom:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:9px">'+_escHTML((e.titulo||'').slice(0,18))+'</div>';
      });
      if(evs.length > 3) html += '<div style="font-size:9px;color:#64748b">+'+(evs.length-3)+' más</div>';
      html += '</div>';
      cur.setDate(cur.getDate() + 1);
    }
    html += '</div>';
    html += '<div style="margin-top:8px;font-size:10px;color:#64748b;text-align:center">⬛ hoy · ⬜ fin de semana · 💜 evento Calendar</div>';
    html += '</div>';
    return html;
  }

  function planV2RenderSemanaV2(d){
    var kpis = document.getElementById('pv2-kpis');
    var k = d.kpis || {};
    var status = d.auto_plan_status || {};
    kpis.innerHTML = ''
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Próximas 14d</div><div style="font-size:26px;font-weight:800;color:#0f172a">'+(k.total||0)+'</div></div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #15803d;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Confirmadas</div><div style="font-size:26px;font-weight:800;color:#15803d">'+(k.desde_bd||0)+'</div></div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">🔮 Proyectadas</div><div style="font-size:26px;font-weight:800;color:#7c3aed">'+(k.proyectadas||0)+'</div></div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(status.horas_desde_run<24?'#15803d':'#d97706')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Auto-Plan</div><div style="font-size:14px;font-weight:700;color:'+(status.horas_desde_run<24?'#15803d':'#d97706')+';margin-top:4px">'+(status.horas_desde_run!=null ? 'hace '+status.horas_desde_run+'h' : 'nunca corrió')+'</div></div>';

    document.getElementById('pv2-comprar-ya').style.display = 'none';

    var vista = document.getElementById('pv2-vista');
    var items = d.items || [];

    // Banner si todas son proyectadas
    var banner = '';
    if(k.desde_bd === 0 && k.proyectadas > 0){
      banner = '<div style="background:#f3e8ff;border:1px solid #d8b4fe;border-radius:10px;padding:14px 18px;margin-bottom:14px;color:#6b21a8;font-size:13px">'
        +'<b>🔮 Plan proyectado automáticamente</b> · Se calculó desde Shopify + cadencias. '
        +'Ejecuta <b>🔥 Auto-Plan AHORA</b> para confirmar y crear los registros, o haz click en cada producción para confirmarla individual.'
        +'</div>';
    } else if(k.desde_bd > 0 && k.proyectadas === 0 && status.horas_desde_run > 24){
      banner = '<div style="background:#fef3c7;border:1px solid #fbbf24;border-radius:10px;padding:14px 18px;margin-bottom:14px;color:#92400e;font-size:13px">'
        +'⚠ El Auto-Plan no se ha ejecutado en '+status.horas_desde_run+'h. <b>Ejecuta AHORA</b> para refrescar con datos actuales de Shopify.'
        +'</div>';
    }

    if(!items.length){
      vista.innerHTML = banner + '<div style="background:#fef3c7;padding:30px;border-radius:10px;text-align:center;color:#92400e;font-size:14px">⚠ Sin producciones próximas. Ejecuta <b>Auto-Plan</b> para que el sistema calcule el plan desde Shopify.</div>';
      return;
    }

    vista.innerHTML = banner + '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px">'
      + items.map(function(it){
        var esProy = it.origen === 'proyeccion';
        var borderCol = esProy ? '#7c3aed' : '#e2e8f0';
        var img = it.imagen_url
          ? '<img loading="lazy" decoding="async" src="'+_escAttr(it.imagen_url)+'" style="width:100%;height:110px;object-fit:cover" alt="">'
          : '<div style="width:100%;height:110px;background:linear-gradient(135deg,'+(esProy?'#7c3aed,#dc2626':'#6d28d9,#7c3aed')+');display:flex;align-items:center;justify-content:center;color:#fff;font-size:32px">📦</div>';
        var fechaTxt = '';
        try { fechaTxt = new Date(it.fecha_programada+'T00:00:00').toLocaleDateString('es-CO',{weekday:'short',day:'numeric',month:'short'}); } catch(e){ fechaTxt = it.fecha_programada; }
        var idAttr = it.produccion_id || 0;
        return '<div data-prod-id="'+idAttr+'" data-producto="'+_escAttr(it.producto)+'" data-fecha="'+_escAttr(it.fecha_programada)+'" data-kg="'+(it.kg||0)+'" style="background:#fff;border:2px solid '+borderCol+';border-radius:10px;overflow:hidden;transition:transform .12s">'
          + '<div onclick="' + (esProy ? 'confirmarProyeccion(this.parentNode)' : 'abrirPlanSemModal('+idAttr+')') + '" style="cursor:pointer">' + img + '</div>'
          +'<div style="padding:10px 12px;position:relative">'
          + (esProy ? '<div style="position:absolute;top:-12px;right:8px;background:#7c3aed;color:#fff;padding:3px 8px;border-radius:6px;font-size:10px;font-weight:800;letter-spacing:.5px">🔮 PROYECTADA</div>' : '')
          +'<b style="color:#0f172a;font-size:13px">'+_escHTML(it.producto)+'</b>'
          +'<div style="font-size:11px;color:#64748b;margin-top:2px;text-transform:capitalize">📅 '+_escHTML(fechaTxt)+' · '+(it.kg||0).toFixed(0)+'kg</div>'
          + (esProy
              ? '<div style="font-size:11px;color:#7c3aed;margin-top:6px;font-weight:600">👆 Click para confirmar</div>'
              : (it.area_nombre ? '<div style="font-size:11px;color:#64748b;margin-top:4px">🏭 '+_escHTML(it.area_nombre)+'</div>' : '<div style="font-size:11px;color:#dc2626;margin-top:4px">⚠ Sin área asignada</div>'))
          + (!esProy && idAttr ? '<div style="display:flex;gap:4px;margin-top:8px;border-top:1px solid #e5e7eb;padding-top:8px">'
              +'<button onclick="event.stopPropagation();editarLoteModal('+idAttr+',\''+_escAttr(it.producto)+'\','+(it.kg||0)+')" style="flex:1;background:#fff;color:#7c3aed;border:1px solid #7c3aed;padding:5px 8px;border-radius:5px;font-size:10px;font-weight:700;cursor:pointer">✏️ Editar lote</button>'
              +'<button onclick="event.stopPropagation();eliminarYReplanificar('+idAttr+',\''+_escAttr(it.producto)+'\')" style="flex:1;background:#fff;color:#dc2626;border:1px solid #dc2626;padding:5px 8px;border-radius:5px;font-size:10px;font-weight:700;cursor:pointer">🗑 Eliminar</button>'
              +'</div>' : '')
          +'</div></div>';
      }).join('')
      +'</div>';
  }

  async function confirmarProyeccion(card){
    var producto = card.dataset.producto;
    var fecha = card.dataset.fecha;
    var kg = parseFloat(card.dataset.kg) || 0;
    if(!confirm('¿Confirmar producción de "'+producto+'" para '+fecha+'?\n\nSe creará en el calendario y aparecerá en Pre-flight.')) return;
    try {
      var r = await fetch('/api/planta/confirmar-proyeccion', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({producto: producto, fecha_programada: fecha, kg: kg})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'no se pudo confirmar')); return; }
      _toast(d.ya_existia ? 'Ya estaba creada' : '✓ Producción confirmada', 1);
      planV2Cargar();
    } catch(e){ alert('Error: '+e.message); }
  }

  async function eliminarYReplanificar(prodId, producto){
    var motivo = prompt('¿Por qué eliminas esta producción de "'+producto+'"?\n\n(El sistema propondrá automáticamente otra fecha en su lugar según cadencia)', 'Ya producida');
    if(motivo === null) return;
    try {
      var r = await fetch('/api/planta/produccion/'+prodId+'/eliminar-y-replanificar', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({motivo: motivo})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'')); return; }
      _toast('✓ Eliminada · nueva sugerida para '+d.nueva_fecha, 1);
      planV2Cargar();
    } catch(e){ alert('Error: '+e.message); }
  }

  function planV2Descargar(){
    var meses = parseFloat(_PV2_HORIZONTE);
    if(meses < 1) meses = 1;
    window.open('/api/planta/plan/exportar?meses='+Math.round(meses)+'&formato=xlsx', '_blank');
  }

  // ════════════════════════════════════════════════════════════════════════
  // MAQUILA · pedidos de clientes que se suman al plan
  // ════════════════════════════════════════════════════════════════════════
  var _MQ_CLIENTES = [];
  var _MQ_PRODUCTOS = [];

  async function maquilaInit(){
    cargarClientesMaquila();
    cargarPedidosMaquila();
  }

  async function cargarClientesMaquila(){
    try {
      var r = await fetch('/api/maquila/clientes');
      var d = await r.json();
      _MQ_CLIENTES = d.clientes || [];
    } catch(e){}
  }

  async function cargarPedidosMaquila(){
    var box = document.getElementById('mq-pedidos');
    var kpis = document.getElementById('mq-kpis');
    if(!box) return;
    box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r = await fetch('/api/maquila/pedidos?estado=todos');
      var d = await r.json();
      var items = d.pedidos || [];
      var pend = items.filter(function(x){return x.estado==='recibido'}).length;
      var plan = items.filter(function(x){return x.estado==='planificado'}).length;
      var enProd = items.filter(function(x){return x.estado==='en_produccion'}).length;
      var entreg = items.filter(function(x){return x.estado==='entregado'}).length;
      kpis.innerHTML = ''
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #d97706;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Recibidos</div><div style="font-size:26px;font-weight:800;color:#d97706">'+pend+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Planificados</div><div style="font-size:26px;font-weight:800;color:#7c3aed">'+plan+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">En producción</div><div style="font-size:26px;font-weight:800;color:#7c3aed">'+enProd+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #15803d;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Entregados</div><div style="font-size:26px;font-weight:800;color:#15803d">'+entreg+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #1a4a7a;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Clientes</div><div style="font-size:26px;font-weight:800;color:#1a4a7a">'+_MQ_CLIENTES.length+'</div></div>';

      if(!items.length){
        box.innerHTML = '<div style="background:#f8fafc;padding:30px;border-radius:10px;text-align:center;color:#94a3b8">Sin pedidos de maquila. Crea uno con "+ Nuevo pedido".</div>';
        return;
      }
      var html = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">';
      html += '<thead style="background:#f9fafb"><tr>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">N°</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Cliente</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producto</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Unidades</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Kg</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Entrega</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Estado</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producción</th>'
        +'<th style="padding:8px 10px"></th>'
        +'</tr></thead><tbody>';
      items.forEach(function(p){
        var estCol = {recibido:'#d97706',planificado:'#7c3aed',en_produccion:'#7c3aed',listo_entrega:'#1a4a7a',entregado:'#15803d',cancelado:'#94a3b8'}[p.estado] || '#475569';
        html += '<tr style="border-top:1px solid #f1f5f9">'
          +'<td style="padding:7px 10px;font-family:monospace;font-size:11px"><b>'+_escHTML(p.numero)+'</b></td>'
          +'<td style="padding:7px 10px"><b>'+_escHTML(p.cliente_nombre||'')+'</b></td>'
          +'<td style="padding:7px 10px">'+_escHTML(p.producto_nombre||'')+'</td>'
          +'<td style="padding:7px 10px;text-align:right;font-family:monospace;font-weight:700">'+(p.unidades||0).toLocaleString('es-CO')+'</td>'
          +'<td style="padding:7px 10px;text-align:right;font-family:monospace;color:#64748b">'+(p.kg_estimados ? p.kg_estimados.toFixed(1) : '—')+'</td>'
          +'<td style="padding:7px 10px;font-size:11px;color:#64748b">'+_escHTML(p.fecha_entrega_objetivo||'—')+'</td>'
          +'<td style="padding:7px 10px;text-align:center"><span style="background:'+estCol+'22;color:'+estCol+';padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase">'+_escHTML(p.estado)+'</span></td>'
          +'<td style="padding:7px 10px;font-size:11px;color:#64748b">'+(p.produccion_id ? '#'+p.produccion_id+(p.produccion_fecha?' · '+_escHTML(p.produccion_fecha):'') : '—')+'</td>'
          +'<td style="padding:7px 10px;text-align:right">'+(p.estado==='recibido' || p.estado==='planificado' ? '<button onclick="cancelarPedidoMaquila('+p.id+')" style="background:#fff;color:#dc2626;border:1px solid #dc2626;padding:3px 8px;border-radius:5px;font-size:10px;font-weight:700;cursor:pointer">✕</button>' : '')+'</td>'
          +'</tr>';
      });
      html += '</tbody></table></div>';
      // Mensaje educativo
      html += '<div style="background:#f0f9ff;border:1px solid #7dd3fc;border-radius:10px;padding:12px 16px;margin-top:14px;font-size:12px;color:#0369a1">💡 <b>Cómo funciona:</b> Los pedidos en estado "recibido" se SUMAN automáticamente al lote de Animus la próxima vez que el Auto-Plan corra. Si Kelly Guerra pide 500 unid de Suero AH y Animus va a producir 90kg → el lote total será 90kg + lo necesario para esas 500 unid.</div>';
      box.innerHTML = html;
    } catch(e){
      box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  function abrirNuevoPedido(){
    if(!_MQ_CLIENTES.length){ alert('Primero crea un cliente con "+ Cliente"'); return; }
    var sel = document.getElementById('mq-cliente');
    sel.innerHTML = '<option value="">— elegir cliente —</option>'
      + _MQ_CLIENTES.map(function(c){return '<option value="'+c.id+'">'+_escHTML(c.nombre)+(c.comparte_formula_con?' (fórmula '+_escHTML(c.comparte_formula_con)+')':'')+'</option>';}).join('');
    var sp = document.getElementById('mq-producto');
    sp.innerHTML = '<option value="">— elegir producto —</option>'
      + (_presProductos||[]).map(function(p){return '<option value="'+_escAttr(p.producto_nombre)+'">'+_escHTML(p.producto_nombre)+'</option>';}).join('');
    if(!(_presProductos||[]).length){
      // Cargar productos si no están cargados
      fetch('/api/planta/presentaciones/productos-disponibles').then(function(r){return r.json();}).then(function(d){
        _presProductos = d.productos || [];
        sp.innerHTML = '<option value="">— elegir producto —</option>'
          + _presProductos.map(function(p){return '<option value="'+_escAttr(p.producto_nombre)+'">'+_escHTML(p.producto_nombre)+'</option>';}).join('');
      });
    }
    ['mq-unidades','mq-kg','mq-fecha','mq-obs'].forEach(function(id){var e=document.getElementById(id); if(e) e.value='';});
    document.getElementById('modal-mq-pedido').style.display = 'flex';
  }

  async function guardarPedidoMaquila(){
    var body = {
      cliente_id: parseInt(document.getElementById('mq-cliente').value),
      producto_nombre: document.getElementById('mq-producto').value,
      unidades: parseInt(document.getElementById('mq-unidades').value),
      kg_estimados: parseFloat(document.getElementById('mq-kg').value)||null,
      fecha_entrega_objetivo: document.getElementById('mq-fecha').value,
      observaciones: document.getElementById('mq-obs').value,
    };
    if(!body.cliente_id || !body.producto_nombre || !body.unidades){
      alert('Cliente, producto y unidades son requeridos'); return;
    }
    try {
      var r = await fetch('/api/maquila/pedidos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'')); return; }
      document.getElementById('modal-mq-pedido').style.display='none';
      _toast('✓ Pedido '+d.numero+' creado', 1);
      cargarPedidosMaquila();
    } catch(e){ alert('Error: '+e.message); }
  }

  function abrirNuevoCliente(){
    ['mc-nombre','mc-email','mc-tel','mc-comparte'].forEach(function(id){var e=document.getElementById(id); if(e) e.value='';});
    document.getElementById('modal-mq-cliente').style.display = 'flex';
  }

  async function guardarClienteMaquila(){
    var body = {
      nombre: document.getElementById('mc-nombre').value.trim(),
      email: document.getElementById('mc-email').value.trim(),
      telefono: document.getElementById('mc-tel').value.trim(),
      comparte_formula_con: document.getElementById('mc-comparte').value.trim(),
    };
    if(!body.nombre){ alert('Nombre requerido'); return; }
    try {
      var r = await fetch('/api/maquila/clientes', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'')); return; }
      document.getElementById('modal-mq-cliente').style.display='none';
      _toast('✓ Cliente creado', 1);
      cargarClientesMaquila();
    } catch(e){ alert('Error: '+e.message); }
  }

  async function cancelarPedidoMaquila(id){
    if(!confirm('¿Cancelar este pedido de maquila?')) return;
    try {
      var r = await fetch('/api/maquila/pedidos/'+id, {method:'DELETE'});
      if(r.ok){ _toast('Pedido cancelado', 1); cargarPedidosMaquila(); }
    } catch(e){ alert('Error: '+e.message); }
  }

  function editarLoteModal(prodId, producto, kgActual){
    var nueva = prompt('Editar tamaño del lote para "'+producto+'"\n\nKg actuales: '+kgActual+'\n\nNuevo tamaño (kg):', kgActual);
    if(nueva === null) return;
    nueva = parseFloat(nueva);
    if(isNaN(nueva) || nueva <= 0){ alert('Cantidad inválida'); return; }
    fetch('/api/planta/produccion/'+prodId+'/editar-lote', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({cantidad_kg: nueva})
    }).then(function(r){return r.json();}).then(function(d){
      if(!d.ok){ alert('Error: '+(d.error||'')); return; }
      var msg = '✓ Lote actualizado a '+nueva+'kg';
      if(d.envase_recalculado){
        msg += '\nEnvases ahora: '+d.envase_recalculado.unidades_requeridas+' unidades';
      }
      if(d.mp_recalculada && d.mp_recalculada.length){
        var top3 = d.mp_recalculada.slice(0,3).map(function(m){return m.material_nombre+': '+m.gramos_requeridos+'g'}).join('\n');
        msg += '\n\nMP recalculada:\n'+top3;
      }
      alert(msg);
      planV2Cargar();
    });
  }

  function planV2RenderSemana(d){
    var kpis = document.getElementById('pv2-kpis');
    var k = d.kpis || {};
    kpis.innerHTML = ''
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Producciones 14d</div><div style="font-size:26px;font-weight:800;color:#0f172a">'+(k.total||0)+'</div></div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(k.alerta_roja_dias?'#dc2626':'#15803d')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Alerta días &lt;10</div><div style="font-size:26px;font-weight:800;color:'+(k.alerta_roja_dias?'#dc2626':'#15803d')+'">'+(k.alerta_roja_dias||0)+'</div></div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(k.sin_mp_suficiente?'#dc2626':'#15803d')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Sin MP</div><div style="font-size:26px;font-weight:800;color:'+(k.sin_mp_suficiente?'#dc2626':'#15803d')+'">'+(k.sin_mp_suficiente||0)+'</div></div>';

    document.getElementById('pv2-comprar-ya').style.display = 'none';

    var vista = document.getElementById('pv2-vista');
    var items = d.items || [];
    if(!items.length){
      vista.innerHTML = '<div style="background:#f0fdf4;padding:30px;border-radius:10px;text-align:center;color:#166534;font-size:14px">✓ Sin producciones próximas — todo dentro de cobertura</div>';
      return;
    }
    vista.innerHTML = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px">'
      + items.map(function(it){
        var diasCol = it.alerta_dias==='rojo'?'#dc2626':(it.alerta_dias==='amarillo'?'#d97706':(it.alerta_dias==='verde'?'#15803d':'#94a3b8'));
        var diasTxt = it.dias_inventario===null?'—':it.dias_inventario+'d';
        var mpCol = it.alcanza_mp?'#15803d':'#dc2626';
        var img = it.imagen_url
          ? '<img loading="lazy" decoding="async" src="'+_escAttr(it.imagen_url)+'" style="width:100%;height:110px;object-fit:cover" alt="">'
          : '<div style="width:100%;height:110px;background:linear-gradient(135deg,#6d28d9,#7c3aed);display:flex;align-items:center;justify-content:center;color:#fff;font-size:32px">📦</div>';
        return '<div onclick="abrirPlanSemModal('+it.produccion_id+')" style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;cursor:pointer;transition:transform .12s">'
          + img
          +'<div style="padding:10px 12px"><b style="color:#0f172a;font-size:13px">'+_escHTML(it.producto)+'</b>'
          +'<div style="font-size:11px;color:#64748b;margin-top:2px">📅 '+_escHTML(it.fecha_programada)+' · '+(it.lotes||1)+' lote(s)</div>'
          +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-top:8px">'
          +'<div style="background:'+diasCol+'15;color:'+diasCol+';padding:5px;border-radius:5px;text-align:center;font-size:10px;font-weight:700">⏰ '+diasTxt+'</div>'
          +'<div style="background:'+mpCol+'15;color:'+mpCol+';padding:5px;border-radius:5px;text-align:center;font-size:10px;font-weight:700">'+(it.alcanza_mp?'✓ MP':'✗ MP')+'</div>'
          +'</div></div></div>';
      }).join('')
      +'</div>';
  }

  function planV2RenderForecast(d, meses){
    var k = d.kpis || {};
    var kpis = document.getElementById('pv2-kpis');
    var desglose = k.desglose || {};
    var dMotor = desglose.motor_mrp || {lotes:0,kg:0,skus:0};
    var dBd = desglose.bd_interna || {lotes:0,kg:0,skus:0};
    var dCal = desglose.google_calendar || {lotes:0,kg:0,skus:0};
    kpis.innerHTML = ''
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:10px;padding:14px">'
        +'<div style="font-size:11px;color:#64748b;text-transform:uppercase">Total lotes planeados</div>'
        +'<div style="font-size:26px;font-weight:800;color:#0f172a">'+(k.total_lotes_proyectados||0)+'</div>'
        +'<div style="font-size:10px;color:#64748b;margin-top:4px">📆 '+dCal.lotes+' Calendar · 🤖 '+dMotor.lotes+' Motor · ✓ '+dBd.lotes+' BD</div>'
      +'</div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #15803d;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Total kg</div><div style="font-size:26px;font-weight:800;color:#15803d">'+(k.total_kg_proyectados||0).toLocaleString('es-CO')+'</div><div style="font-size:10px;color:#64748b;margin-top:4px">📆 '+dCal.kg+'kg · 🤖 '+dMotor.kg+'kg</div></div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">SKUs distintos</div><div style="font-size:26px;font-weight:800;color:#7c3aed">'+(k.productos_distintos||0)+'</div><div style="font-size:10px;color:#64748b;margin-top:4px">con producción en horizonte</div></div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(k.compras_urgentes_count?'#dc2626':'#15803d')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">🛒 Comprar YA</div><div style="font-size:26px;font-weight:800;color:'+(k.compras_urgentes_count?'#dc2626':'#15803d')+'">'+(k.compras_urgentes_count||0)+'</div></div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(k.meses_con_alerta_capacidad?'#d97706':'#15803d')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Meses cuello botella</div><div style="font-size:26px;font-weight:800;color:'+(k.meses_con_alerta_capacidad?'#d97706':'#15803d')+'">'+(k.meses_con_alerta_capacidad||0)+'</div></div>';

    // Sección comprar YA (urgentes)
    var compYa = d.compras_urgentes || [];
    var box = document.getElementById('pv2-comprar-ya');
    if(compYa.length){
      box.style.display = 'block';
      box.innerHTML = '<div style="background:#fef2f2;border:2px solid #dc2626;border-radius:12px;padding:16px">'
        +'<h3 style="margin:0 0 10px;color:#991b1b">🚨 Comprar AHORA · '+compYa.length+' material(es) por lead time</h3>'
        +'<div style="font-size:12px;color:#7f1d1d;margin-bottom:10px">Estos envases NO llegarán a tiempo si no se piden hoy. Lead time China = 180 días.</div>'
        +'<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#fee2e2"><th style="padding:8px;text-align:left">Envase</th><th style="padding:8px;text-align:right">Cantidad</th><th style="padding:8px;text-align:left">Origen</th><th style="padding:8px;text-align:right">Lead</th><th style="padding:8px;text-align:right">Necesario para</th></tr></thead><tbody>'
        + compYa.map(function(c){
          return '<tr style="border-top:1px solid #fecaca">'
            +'<td style="padding:6px 8px"><b>'+_escHTML(c.etiqueta)+'</b><br><code style="font-size:10px;color:#991b1b">'+_escHTML(c.envase_codigo)+'</code></td>'
            +'<td style="padding:6px 8px;text-align:right;font-family:monospace;font-weight:800">'+c.unidades_requeridas.toLocaleString('es-CO')+'</td>'
            +'<td style="padding:6px 8px"><span style="background:#dc2626;color:#fff;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700">'+_escHTML(c.origen)+'</span></td>'
            +'<td style="padding:6px 8px;text-align:right;font-family:monospace">'+c.lead_time_dias+'d</td>'
            +'<td style="padding:6px 8px;text-align:right">'+_escHTML(c.mes_objetivo)+'</td>'
            +'</tr>';
        }).join('')
        +'</tbody></table></div>';
    } else {
      box.style.display = 'none';
    }

    var vista = document.getElementById('pv2-vista');
    if(meses === 1){
      planV2RenderCalendarioMes(d, vista);
    } else if(meses <= 3){
      planV2RenderTimeline(d, vista, meses);
    } else {
      planV2RenderHeatmap(d, vista, meses);
    }
  }

  async function planV2RenderCalendarioMes(d, vista){
    // Agrupar producciones del MOTOR por fecha
    var prods = d.producciones_proyectadas || [];
    var porFecha = {};
    prods.forEach(function(p){
      porFecha[p.fecha] = porFecha[p.fecha] || [];
      porFecha[p.fecha].push({producto: p.producto, origen: 'motor', kg: p.kg_con_merma});
    });

    // Sumar eventos REALES del Google Calendar
    try {
      var rcal = await fetch('/api/planta/calendar-eventos-plan?dias=35');
      var dcal = await rcal.json();
      (dcal.eventos || []).forEach(function(ev){
        porFecha[ev.fecha] = porFecha[ev.fecha] || [];
        porFecha[ev.fecha].push({
          producto: ev.producto_match || ev.titulo,
          titulo_real: ev.titulo,
          origen: 'calendar',
          kg: ev.kg,
          score: ev.score,
        });
      });
    } catch(e){ /* silent */ }

    var hoy = new Date(d.fecha_inicio);
    var html = '<h3 style="margin:0 0 8px;color:#0f172a;font-size:15px">📅 Calendario próximos 30 días</h3>';
    html += '<div style="display:flex;gap:14px;font-size:11px;color:#64748b;margin-bottom:8px;flex-wrap:wrap">'
      +'<span><span style="display:inline-block;width:10px;height:10px;background:#7c3aed;border-radius:2px;vertical-align:middle"></span> Google Calendar (real)</span>'
      +'<span><span style="display:inline-block;width:10px;height:10px;background:#7c3aed;border-radius:2px;vertical-align:middle"></span> Motor MRP (proyectado)</span>'
      +'<span><span style="display:inline-block;width:10px;height:10px;background:#15803d;border-radius:2px;vertical-align:middle"></span> Confirmado en BD</span>'
      +'</div>';
    html += '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px;font-size:11px">';
    ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'].forEach(function(dn){
      html += '<div style="font-weight:800;color:#475569;text-align:center;padding:6px;background:#f1f5f9;border-radius:4px">'+dn+'</div>';
    });
    var pad = (hoy.getDay() + 6) % 7;
    for(var i=0;i<pad;i++) html += '<div></div>';
    for(var d_=0; d_<30; d_++){
      var fecha = new Date(hoy); fecha.setDate(fecha.getDate()+d_);
      var fStr = fecha.toISOString().substring(0,10);
      var weekday = (fecha.getDay()+6)%7;
      var esLMV = [0,2,4].indexOf(weekday) >= 0;
      var prodsDia = porFecha[fStr] || [];
      var bg = esLMV ? '#fff' : '#f9fafb';
      var border = prodsDia.length ? '#6d28d9' : '#e5e7eb';
      html += '<div style="background:'+bg+';border:1px solid '+border+';border-radius:6px;padding:6px;min-height:70px;font-size:10px">'
        +'<div style="color:#94a3b8;font-weight:700;font-size:10px">'+fecha.getDate()+'</div>'
        + prodsDia.slice(0,4).map(function(p){
          var col = p.origen==='calendar' ? '#7c3aed' : '#7c3aed';
          var bgCol = p.origen==='calendar' ? '#cffafe' : '#ede9fe';
          var txtCol = p.origen==='calendar' ? '#155e75' : '#5b21b6';
          var label = p.titulo_real || p.producto;
          var kgTxt = p.kg ? ' '+Math.round(p.kg)+'kg' : '';
          return '<div style="background:'+bgCol+';color:'+txtCol+';padding:2px 4px;border-radius:3px;margin-top:2px;font-size:9px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border-left:2px solid '+col+'" title="'+_escAttr((p.titulo_real||p.producto)+kgTxt+' · '+p.origen)+'">'+_escHTML(label.substring(0,16))+kgTxt+'</div>';
        }).join('')
        + (prodsDia.length>4?'<div style="font-size:9px;color:#64748b;margin-top:2px">+'+(prodsDia.length-4)+' más</div>':'')
        +'</div>';
    }
    html += '</div>';
    vista.innerHTML = html;
  }

  function planV2RenderTimeline(d, vista, meses){
    // Agrupar producciones por SKU
    var prods = d.producciones_proyectadas || [];
    var resumen = d.resumen_mensual || {};
    var porSku = {};
    prods.forEach(function(p){ porSku[p.producto] = porSku[p.producto] || []; porSku[p.producto].push(p); });

    // Sebastián 1-may-2026: empty state limpio cuando no hay producciones
    // proyectadas. Antes renderizaba headers vacíos (Timeline + Resumen
    // mensual con solo títulos de columna) que se veía feo.
    if(!prods.length && !Object.keys(resumen).length){
      vista.innerHTML = '<div style="background:#f8fafc;border:1px dashed #cbd5e1;border-radius:10px;padding:32px 18px;text-align:center;color:#64748b">'
        +'<div style="font-size:32px;margin-bottom:8px">📊</div>'
        +'<div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:6px">Sin producciones proyectadas en '+meses+' meses</div>'
        +'<div style="font-size:12px;color:#64748b;margin-bottom:12px">El motor MRP no encontró eventos del Calendar ni necesidades por velocidad de venta.</div>'
        +'<button onclick="diagnosticarCalendar()" style="padding:7px 14px;background:#7c3aed;color:#fff;border:none;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer">🔧 Diagnosticar Calendar</button>'
        +'</div>';
      return;
    }

    var hoy = new Date(d.fecha_inicio);
    var fin = new Date(d.fecha_fin);

    var html = '<h3 style="margin:0 0 10px;color:#0f172a;font-size:15px">📊 Timeline · '+meses+' meses</h3>';
    html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px;overflow-x:auto">';
    // Eje X: meses
    html += '<div style="display:grid;grid-template-columns:200px 1fr;gap:10px;border-bottom:1px solid #e5e7eb;padding-bottom:6px;margin-bottom:8px;font-size:11px;font-weight:700;color:#64748b">';
    html += '<div>SKU</div>';
    html += '<div style="display:grid;grid-template-columns:repeat('+meses+',1fr)">';
    for(var m=0;m<meses;m++){
      var d2 = new Date(hoy); d2.setMonth(d2.getMonth()+m);
      html += '<div style="text-align:center">'+d2.toLocaleString('es-CO',{month:'short',year:'2-digit'}).toUpperCase()+'</div>';
    }
    html += '</div></div>';
    // Filas SKU (solo si hay datos)
    if(Object.keys(porSku).length){
      Object.keys(porSku).sort().forEach(function(sku){
        html += '<div style="display:grid;grid-template-columns:200px 1fr;gap:10px;align-items:center;padding:5px 0;border-top:1px solid #f1f5f9;font-size:11px">';
        html += '<div style="font-weight:600;color:#0f172a;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="'+_escAttr(sku)+'">'+_escHTML(sku)+'</div>';
        html += '<div style="position:relative;height:20px;background:#f8fafc;border-radius:3px">';
        porSku[sku].forEach(function(p){
          var pf = new Date(p.fecha);
          var offset = (pf - hoy) / (fin - hoy) * 100;
          if(offset < 0 || offset > 100) return;
          html += '<div title="'+_escAttr(p.fecha+' · '+p.kg_con_merma+'kg')+'" style="position:absolute;left:'+offset+'%;top:2px;width:8px;height:16px;background:#6d28d9;border-radius:2px"></div>';
        });
        html += '</div></div>';
      });
    } else {
      html += '<div style="text-align:center;padding:18px;color:#94a3b8;font-size:11px;font-style:italic">Sin producciones en horizonte</div>';
    }
    html += '</div>';

    // Tabla resumen mensual (solo si hay datos)
    if(Object.keys(resumen).length){
      html += '<h3 style="margin:18px 0 10px;color:#0f172a;font-size:15px">📈 Resumen mensual</h3>';
      html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">';
      html += '<thead style="background:#f9fafb"><tr><th style="padding:8px 12px;text-align:left">Mes</th><th style="padding:8px;text-align:right">Lotes</th><th style="padding:8px;text-align:right">Kg total</th><th style="padding:8px;text-align:right">SKUs</th></tr></thead><tbody>';
      Object.keys(resumen).sort().forEach(function(m){
        var r = resumen[m];
        html += '<tr style="border-top:1px solid #f1f5f9"><td style="padding:7px 12px;font-weight:700">'+_escHTML(m)+'</td><td style="padding:7px;text-align:right;font-family:monospace">'+r.lotes+'</td><td style="padding:7px;text-align:right;font-family:monospace">'+r.kg_total+'</td><td style="padding:7px;text-align:right;font-family:monospace">'+r.productos_distintos+'</td></tr>';
      });
      html += '</tbody></table></div>';
    }

    vista.innerHTML = html;
  }

  function planV2RenderHeatmap(d, vista, meses){
    // Heatmap SKU × mes (intensidad = kg)
    var prods = d.producciones_proyectadas || [];
    var skus = [...new Set(prods.map(function(p){return p.producto}))].sort();
    var meses_keys = Object.keys(d.resumen_mensual || {}).sort();

    // Sebastián 1-may-2026: empty state limpio
    if(!prods.length && !meses_keys.length){
      vista.innerHTML = '<div style="background:#f8fafc;border:1px dashed #cbd5e1;border-radius:10px;padding:32px 18px;text-align:center;color:#64748b">'
        +'<div style="font-size:32px;margin-bottom:8px">🌡</div>'
        +'<div style="font-size:14px;font-weight:700;color:#0f172a;margin-bottom:6px">Sin datos para heatmap '+meses+' meses</div>'
        +'<div style="font-size:12px">El motor MRP no proyectó producciones en este horizonte.</div>'
        +'</div>';
      return;
    }

    // Calcular max kg por celda para normalizar color
    var celda = {};
    prods.forEach(function(p){
      var k = p.producto+'|'+p.mes;
      celda[k] = (celda[k]||0) + p.kg_con_merma;
    });
    var maxVal = Math.max(...Object.values(celda), 1);

    var html = '<h3 style="margin:0 0 10px;color:#0f172a;font-size:15px">🌡 Mapa de calor · '+meses+' meses</h3>';
    html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px;overflow-x:auto">';
    html += '<div style="display:grid;grid-template-columns:240px repeat('+meses_keys.length+',minmax(50px,1fr));gap:2px;font-size:10px">';
    html += '<div></div>';
    meses_keys.forEach(function(m){
      html += '<div style="text-align:center;padding:6px 4px;background:#f1f5f9;border-radius:3px;font-weight:700;color:#475569">'+_escHTML(m.substring(5))+'</div>';
    });
    skus.forEach(function(sku){
      html += '<div style="padding:6px 8px;font-size:11px;font-weight:600;color:#0f172a;background:#f8fafc;border-radius:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="'+_escAttr(sku)+'">'+_escHTML(sku.substring(0,30))+'</div>';
      meses_keys.forEach(function(m){
        var v = celda[sku+'|'+m] || 0;
        var pct = Math.min(100, (v/maxVal)*100);
        var bg = v > 0 ? 'rgba(15,118,110,'+(0.15+pct/130)+')' : '#fafafa';
        html += '<div style="padding:6px 4px;background:'+bg+';border-radius:3px;text-align:center;font-size:10px;color:'+(v>maxVal*0.5?'#fff':'#0f172a')+';font-weight:700" title="'+_escAttr(sku+' · '+m+': '+v.toFixed(0)+'kg')+'">'+(v>0?v.toFixed(0):'')+'</div>';
      });
    });
    html += '</div></div>';

    // Necesidades agregadas año
    if(meses >= 6){
      html += '<h3 style="margin:18px 0 10px;color:#0f172a;font-size:15px">🛒 Necesidades agregadas '+meses+' meses</h3>';
      // Sumar MP total
      var mpTotal = {};
      Object.values(d.mp_consumo_mensual || {}).forEach(function(mes){
        Object.keys(mes).forEach(function(matId){
          mpTotal[matId] = mpTotal[matId] || {nombre: mes[matId].nombre, gramos: 0};
          mpTotal[matId].gramos += mes[matId].gramos;
        });
      });
      var mpArr = Object.entries(mpTotal).map(function(e){return Object.assign({material_id:e[0]}, e[1]);}).sort(function(a,b){return b.gramos-a.gramos;}).slice(0,15);
      html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;margin-bottom:14px">';
      html += '<div style="padding:10px 14px;background:#f9fafb;font-weight:700;font-size:12px;color:#475569">Top 15 materias primas</div>';
      html += '<table style="width:100%;border-collapse:collapse;font-size:12px"><thead style="background:#f9fafb"><tr><th style="padding:6px 10px;text-align:left">Material</th><th style="padding:6px 10px;text-align:right">Total gramos</th><th style="padding:6px 10px;text-align:right">Total kg</th></tr></thead><tbody>';
      mpArr.forEach(function(m){
        html += '<tr style="border-top:1px solid #f1f5f9"><td style="padding:6px 10px"><b>'+_escHTML(m.nombre||m.material_id)+'</b></td><td style="padding:6px 10px;text-align:right;font-family:monospace">'+Math.round(m.gramos).toLocaleString('es-CO')+'</td><td style="padding:6px 10px;text-align:right;font-family:monospace;font-weight:700">'+(m.gramos/1000).toFixed(2)+'</td></tr>';
      });
      html += '</tbody></table></div>';

      // Envases agregados
      var envTotal = {};
      Object.values(d.envases_consumo_mensual || {}).forEach(function(mes){
        Object.keys(mes).forEach(function(cod){
          envTotal[cod] = envTotal[cod] || {etiqueta: mes[cod].etiqueta, unidades: 0};
          envTotal[cod].unidades += mes[cod].unidades;
        });
      });
      var envArr = Object.entries(envTotal).map(function(e){return Object.assign({codigo:e[0]}, e[1]);}).sort(function(a,b){return b.unidades-a.unidades;});
      if(envArr.length){
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden">';
        html += '<div style="padding:10px 14px;background:#f9fafb;font-weight:700;font-size:12px;color:#475569">Envases requeridos</div>';
        html += '<table style="width:100%;border-collapse:collapse;font-size:12px"><thead style="background:#f9fafb"><tr><th style="padding:6px 10px;text-align:left">Envase</th><th style="padding:6px 10px;text-align:right">Unidades</th></tr></thead><tbody>';
        envArr.forEach(function(e){
          html += '<tr style="border-top:1px solid #f1f5f9"><td style="padding:6px 10px"><b>'+_escHTML(e.etiqueta)+'</b> <code style="font-size:10px;color:#64748b">'+_escHTML(e.codigo)+'</code></td><td style="padding:6px 10px;text-align:right;font-family:monospace;font-weight:700">'+e.unidades.toLocaleString('es-CO')+'</td></tr>';
        });
        html += '</tbody></table></div>';
      }
    }
    vista.innerHTML = html;
  }

  // ════════════════════════════════════════════════════════════════════════
  // ASIGNACIÓN SEMANAL · qué hace cada área cada día
  // ════════════════════════════════════════════════════════════════════════
  // Sebastián 1-may-2026: grid 'Asignación Semanal por Área' eliminado.
  // Era redundante con 'Esta Semana en planta' (Calendar-first) y aparecía
  // vacío en semanas pasadas. Funciones asigInit/asigSemana/asigCargar removidas.

  // ════════════════════════════════════════════════════════════════════════
  // CONFIGURACIÓN · sub-tabs (Presentaciones, Equipos, Cadencias, etc.)
  // ════════════════════════════════════════════════════════════════════════
  var _CFG_SUB = 'pres';
  function cfgInit(){ cfgSubtab(_CFG_SUB); }
  function cfgSubtab(s){
    _CFG_SUB = s;
    ['pres','equipos','cadencias','mp','emails','riesgo','calendar','estac','reparto'].forEach(function(x){
      var btn = document.getElementById('cfg-stab-'+x);
      if(btn){
        if(x==='calendar'){
          btn.style.background = (s===x)?'#dc2626':'linear-gradient(135deg,#fbbf24,#dc2626)';
          btn.style.color = '#fff';
        } else if(x==='estac'){
          btn.style.background = (s===x)?'#4c1d95':'linear-gradient(135deg,#6d28d9,#0891b2)';
          btn.style.color = '#fff';
        } else if(x==='reparto'){
          btn.style.background = (s===x)?'#065f46':'linear-gradient(135deg,#0891b2,#16a34a)';
          btn.style.color = '#fff';
        } else {
          btn.style.background = (s===x)?'#1f2937':'#e5e7eb';
          btn.style.color = (s===x)?'#fff':'#475569';
        }
      }
    });
    var c = document.getElementById('cfg-content');
    // Cargamos los divs antiguos como contenido — reusamos sus cargadores
    if(s==='pres'){
      c.innerHTML = '<div id="ptab-presentaciones-host"></div>';
      // Mover el contenido de ptab-presentaciones aquí (clonando)
      var src = document.getElementById('ptab-presentaciones');
      if(src) c.innerHTML = src.outerHTML.replace('display:none','display:block').replace('id="ptab-presentaciones"','id="ptab-presentaciones-rendered"');
      if(typeof cargarPresentaciones==='function') setTimeout(cargarPresentaciones, 50);
    } else if(s==='equipos'){
      var src = document.getElementById('ptab-equipos');
      if(src) c.innerHTML = src.outerHTML.replace('display:none','display:block').replace('id="ptab-equipos"','id="ptab-equipos-rendered"');
      if(typeof cargarEquipos==='function') setTimeout(cargarEquipos, 50);
    } else if(s==='cadencias'){
      c.innerHTML = '<p style="color:#64748b;font-size:13px">Cadencia, cobertura y merma por SKU. Edita inline.</p><div id="ap-skus-tabla"></div>';
      if(typeof apCargarSkus==='function') setTimeout(apCargarSkus, 50);
    } else if(s==='mp'){
      c.innerHTML = '<div style="display:flex;justify-content:flex-end;margin-bottom:10px"><button onclick="apMpNuevo()" style="background:#6d28d9;color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">+ Nuevo material</button></div><div id="ap-mp-tabla"></div>';
      if(typeof apCargarMp==='function') setTimeout(apCargarMp, 50);
    } else if(s==='emails'){
      c.innerHTML = '<div id="ap-emails-tabla"></div>';
      if(typeof apCargarEmails==='function') setTimeout(apCargarEmails, 50);
    } else if(s==='riesgo'){
      c.innerHTML = '<p style="color:#64748b;font-size:13px">Productos con perfil de riesgo (pigmento, ácido, sensibilidad). Usado por el motor de gates pre-flight para detectar arrastre crítico.</p><div id="cfg-riesgo-tabla"><div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div></div>';
      cfgCargarRiesgo();
    } else if(s==='calendar'){
      c.innerHTML = '<div style="background:linear-gradient(135deg,#fef3c7,#fbbf24);color:#78350f;padding:14px 18px;border-radius:10px;margin-bottom:14px">'
        +'<h3 style="margin:0 0 4px;color:#78350f;font-size:15px">📆 Lectura del Google Calendar</h3>'
        +'<p style="margin:0;font-size:12px;color:#7c2d12">El motor MRP lee tu calendario y matchea cada evento con un producto. Revisa que estén bien matcheados — si hay errores, configura aliases en la sección de cadencias.</p>'
        +'</div>'
        +'<div style="display:flex;gap:8px;margin-bottom:12px"><button onclick="cfgCargarCalendar()" style="background:#dc2626;color:#fff;border:none;padding:8px 14px;border-radius:6px;font-weight:700;cursor:pointer">🔄 Re-leer Calendar</button><button onclick="cfgCargarAliases()" style="background:#fff;border:1px solid #cbd5e1;padding:8px 14px;border-radius:6px;font-weight:600;cursor:pointer">⚙ Editar aliases</button></div>'
        +'<div id="cfg-cal-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:14px"></div>'
        +'<div id="cfg-cal-tabla"><div style="text-align:center;color:#94a3b8;padding:20px">Pulsa "Re-leer Calendar"</div></div>';
      cfgCargarCalendar();
    } else if(s==='estac'){
      c.innerHTML = '<div id="estac-panel"><div style="text-align:center;color:#94a3b8;padding:20px">Cargando…</div></div>';
      if(typeof cargarEstacionalidad==='function') setTimeout(cargarEstacionalidad, 50);
    } else if(s==='reparto'){
      c.innerHTML = '<div id="reparto-panel"><div style="text-align:center;color:#94a3b8;padding:20px">Cargando…</div></div>';
      if(typeof cargarReparto==='function') setTimeout(cargarReparto, 50);
    }
  }

  async function cargarReparto(){
    var el = document.getElementById('reparto-panel'); if(!el) return;
    el.innerHTML = '<div style="color:#94a3b8;padding:20px">Cargando…</div>';
    var h = '';
    // === Sección 0 · Productos SIN envase asignado ===
    try{
      var cov = await (await fetch('/api/abastecimiento/envases-cobertura')).json();
      var envs = ((await (await fetch('/api/programacion/envases-lista')).json()).envases)||[];
      var envOpts = envs.map(function(e){ return '<option value="'+escapeHtmlNec(e.codigo)+'">'+escapeHtmlNec(e.codigo)+' · '+escapeHtmlNec(e.descripcion)+'</option>'; }).join('');
      var faltan = cov.sin_envase||[];
      h += '<div style="font-weight:800;color:'+(faltan.length?'#b91c1c':'#065f46')+';font-size:16px;margin-bottom:4px">'+(faltan.length?'⚠️ '+faltan.length+' producto(s) SIN envase':'✅ Todos los productos activos tienen envase')+'</div>';
      if(faltan.length){
        h += '<div style="font-size:12px;color:#475569;margin-bottom:8px">Estos se producen pero su envase NO se planea/compra (demanda 0). Asignales el frasco (tamaño + envase):</div>';
        faltan.forEach(function(pn,i){
          h += '<div style="display:flex;gap:8px;align-items:center;margin:3px 0;font-size:12px;flex-wrap:wrap"><span style="min-width:240px;color:#334155;font-weight:600">'+escapeHtmlNec(pn)+'</span>'
            +'<label style="color:#64748b">ml <input type="number" id="nv-'+i+'" style="width:56px;padding:4px;border:1px solid #f59e0b;border-radius:6px"></label>'
            +'<select id="ne-'+i+'" style="padding:4px;border:1px solid #e6e1f2;border-radius:6px;font-size:11px;max-width:280px">'+envOpts+'</select>'
            +'<button data-prod="'+escapeHtmlNec(pn)+'" data-idx="'+i+'" onclick="asignarEnvase(this)" style="background:#16a34a;color:#fff;border:none;padding:4px 12px;border-radius:7px;font-weight:700;cursor:pointer;font-size:12px">Asignar</button>'
            +'<button data-prod="'+escapeHtmlNec(pn)+'" onclick="noAplicaEnvase(this)" title="No requiere envase (maquila / otro cliente) · lo saca de la lista" style="background:#f1f5f9;color:#64748b;border:1px solid #e2e8f0;padding:4px 10px;border-radius:7px;cursor:pointer;font-size:11px">no aplica</button></div>';
        });
      }
      var noap = cov.no_aplica||[];
      if(noap.length){ h += '<div style="font-size:11px;color:#94a3b8;margin-top:6px">Marcados "no requiere envase" (otro cliente): '+noap.map(escapeHtmlNec).join(', ')+' · <a href="#" onclick="reincluirNoAplica();return false" style="color:#0891b2">reincluir todos</a></div>'; }
      h += '<div style="border-top:2px solid #ece9f5;margin:16px 0 12px"></div>';
    }catch(e){}
    // === Sección 1 · Envase por tamaño (todos los 10ml en el mismo frasco) ===
    try{
      var t = await (await fetch('/api/programacion/envases-por-tamano')).json();
      h += '<div style="font-weight:800;color:#065f46;font-size:16px;margin-bottom:4px">🧴 Envase por tamaño</div>';
      h += '<div style="font-size:12px;color:#475569;margin-bottom:10px;line-height:1.5">Los productos del MISMO tamaño suelen ir en el MISMO frasco (ej. niacinamida, TRX, hialurónico de 10ml → todos en el frasco de vidrio de 10ml). Si están disparejos, unificá acá.</div>';
      (t.tamanos||[]).forEach(function(tv){
        var dis = tv.disparejo;
        h += '<div style="border:1.5px solid '+(dis?'#fcd34d':'#d1fae5')+';border-radius:11px;padding:10px 12px;margin-bottom:8px;background:'+(dis?'#fffbeb':'#f0fdf4')+'">';
        h += '<div style="font-weight:800;color:#334155;font-size:13px;margin-bottom:4px">'+tv.volumen_ml+' ml · '+tv.n_productos+' producto(s) '+(dis?'<span style="color:#d97706;font-size:11px;font-weight:700">⚠️ usan frascos distintos</span>':'<span style="color:#16a34a;font-size:11px;font-weight:700">✅ todos en el mismo</span>')+'</div>';
        var opts = (tv.envases_disponibles||[]).map(function(e){ return '<option value="'+escapeHtmlNec(e.codigo)+'">'+escapeHtmlNec(e.codigo)+' · '+escapeHtmlNec(e.descripcion)+'</option>'; }).join('');
        if(opts){
          h += '<div style="margin:6px 0;font-size:12px;color:#475569">Poner a TODOS los de '+tv.volumen_ml+'ml: <select id="uni-'+tv.volumen_ml+'" style="padding:5px;border:1px solid #e6e1f2;border-radius:7px;font-size:12px;max-width:340px">'+opts+'</select> <button data-vol="'+tv.volumen_ml+'" onclick="unificarEnvase(this)" style="background:#0891b2;color:#fff;border:none;padding:6px 12px;border-radius:8px;font-weight:700;cursor:pointer;font-size:12px">Aplicar a los '+tv.n_productos+'</button></div>';
        }
        (tv.items||[]).forEach(function(it){
          var iopts = (tv.envases_disponibles||[]).map(function(e){ return '<option value="'+escapeHtmlNec(e.codigo)+'"'+(e.codigo===it.envase?' selected':'')+'>'+escapeHtmlNec(e.codigo)+'</option>'; }).join('');
          var selHtml = iopts ? ('<select data-prod="'+escapeHtmlNec(it.producto)+'" data-cod="'+escapeHtmlNec(it.presentacion)+'" onchange="cambiarEnvasePres(this)" style="min-width:200px;padding:3px;border:1px solid #e6e1f2;border-radius:6px;font-size:11px">'+iopts+'</select>') : ('<span style="color:#334155;font-weight:600;min-width:180px">'+escapeHtmlNec(it.envase||'—')+'</span>');
          h += '<div style="display:flex;gap:8px;align-items:center;margin:2px 0;font-size:11.5px"><span style="min-width:250px;color:#475569">'+escapeHtmlNec(it.producto)+'</span>'+selHtml+'<button data-prod="'+escapeHtmlNec(it.producto)+'" data-cod="'+escapeHtmlNec(it.presentacion)+'" onclick="quitarPres(this)" title="Quitar esta presentación (duplicada/sobrante · reversible)" style="background:#fee2e2;color:#b91c1c;border:none;padding:2px 9px;border-radius:6px;cursor:pointer;font-size:11px">🗑</button></div>';
        });
        h += '</div>';
      });
      h += '<div style="border-top:2px solid #ece9f5;margin:16px 0 12px"></div>';
    }catch(e){}
    // === Sección 2 · Reparto por ventas ===
    try{
      var d = await (await fetch('/api/programacion/split-audit')).json();
      if(!d.ok){ el.innerHTML = h + '<div style="color:#dc2626;padding:20px">Error</div>'; return; }
      var badge = {falta_volumen:['⚠️ falta tamaño','#d97706'], sin_sku:['⚠️ sin SKU','#dc2626'], sin_ventas:['⚠️ sin ventas','#dc2626'], ok_shopify:['✅ ventas Shopify','#16a34a'], ok_manual:['✅ manual','#16a34a']};
      h += '<div style="font-weight:800;color:#4c1d95;font-size:16px;margin-bottom:4px">📊 Reparto por ventas (entre tamaños)</div>';
      h += '<div style="font-size:12px;color:#475569;margin-bottom:12px;line-height:1.5">Cada producto con 2+ tamaños reparte el lote por <b>VENTAS</b>. Cargá el <b>tamaño (ml)</b> de cada SKU → el reparto sale de las ventas reales de Shopify. O escribí las <b>ventas/mes</b> a mano por tamaño. Los ⚠️ son los que faltan.</div>';
      (d.productos||[]).forEach(function(p){
        var b = badge[p.estado]||['',''];
        h += '<div style="border:1px solid #ece9f5;border-radius:12px;padding:12px 14px;margin-bottom:10px;background:#fff">';
        h += '<div style="font-weight:800;color:#4c1d95;margin-bottom:8px;font-size:14px">'+escapeHtmlNec(p.producto)+' <span style="font-size:11px;font-weight:700;color:'+b[1]+';margin-left:6px">'+b[0]+'</span></div>';
        h += '<div style="font-size:11px;color:#64748b;margin:2px 0">SKUs · cargá el tamaño en ml:</div>';
        (p.skus||[]).forEach(function(sk){
          h += '<div style="display:flex;gap:10px;align-items:center;margin:4px 0;font-size:12px"><span style="min-width:200px;color:#334155">'+escapeHtmlNec(sk.sku)+'</span><label style="color:#64748b">ml <input type="number" value="'+(sk.volumen_ml||'')+'" data-sku="'+escapeHtmlNec(sk.sku)+'" onchange="setSkuVol(this.dataset.sku,this.value)" style="width:64px;padding:5px;border:1.5px solid '+(sk.volumen_ml?'#e6e1f2':'#f59e0b')+';border-radius:7px"></label><span style="color:#94a3b8">vende '+(Number(sk.ventas_90d)||0)+' /90d</span></div>';
        });
        if(!(p.skus||[]).length) h += '<div style="font-size:11px;color:#dc2626;margin:4px 0">Sin SKUs mapeados a este producto (revisá el mapeo SKU→producto)</div>';
        h += '<div style="font-size:11px;color:#64748b;margin:8px 0 2px">…o ventas/mes a mano por tamaño (gana sobre lo de arriba):</div>';
        (p.presentaciones||[]).forEach(function(pr){
          h += '<div style="display:flex;gap:10px;align-items:center;margin:4px 0;font-size:12px"><span style="min-width:200px;color:#334155">'+(pr.volumen_ml||'?')+'ml · '+escapeHtmlNec(pr.envase||'')+'</span><label style="color:#64748b">vende/mes <input type="number" value="'+(pr.ventas_mes_referencia||'')+'" data-prod="'+escapeHtmlNec(p.producto)+'" data-cod="'+escapeHtmlNec(pr.codigo)+'" onchange="setPresVentas(this.dataset.prod,this.dataset.cod,this.value)" style="width:74px;padding:5px;border:1.5px solid #e6e1f2;border-radius:7px"></label></div>';
        });
        h += '</div>';
      });
      if(!(d.productos||[]).length) h += '<div style="color:#94a3b8;padding:20px">No hay productos con 2+ presentaciones.</div>';
      el.innerHTML = h;
    }catch(e){ el.innerHTML = '<div style="color:#dc2626;padding:20px">Error: '+e+'</div>'; }
  }
  async function cambiarEnvasePres(sel){ try{ await fetch('/api/programacion/pres-set-envase?producto='+encodeURIComponent(sel.dataset.prod)+'&presentacion_codigo='+encodeURIComponent(sel.dataset.cod)+'&envase='+encodeURIComponent(sel.value)); }catch(e){} cargarReparto(); }
  async function noAplicaEnvase(btn){ try{ await fetch('/api/programacion/pres-no-aplica?producto='+encodeURIComponent(btn.dataset.prod)); }catch(e){} cargarReparto(); }
  async function reincluirNoAplica(){
    try{ var cov = await (await fetch('/api/abastecimiento/envases-cobertura')).json(); var na = cov.no_aplica||[];
      for(var i=0;i<na.length;i++){ await fetch('/api/programacion/pres-no-aplica?producto='+encodeURIComponent(na[i])+'&quitar=1'); } }catch(e){}
    cargarReparto();
  }
  async function asignarEnvase(btn){
    var pn=btn.dataset.prod, i=btn.dataset.idx;
    var vol=document.getElementById('nv-'+i), env=document.getElementById('ne-'+i);
    if(!vol||!vol.value||!env||!env.value){ alert('Poné el tamaño (ml) y elegí el envase'); return; }
    btn.disabled=true; btn.textContent='…';
    try{ await fetch('/api/programacion/pres-crear?producto='+encodeURIComponent(pn)+'&volumen_ml='+encodeURIComponent(vol.value)+'&envase='+encodeURIComponent(env.value)); }catch(e){}
    cargarReparto();
  }
  async function setSkuVol(sku,v){ try{ await fetch('/api/programacion/sku-volumen?sku='+encodeURIComponent(sku)+'&volumen_ml='+encodeURIComponent(v)); }catch(e){} cargarReparto(); }
  async function setPresVentas(prod,cod,v){ try{ await fetch('/api/programacion/pres-ventas?producto='+encodeURIComponent(prod)+'&presentacion_codigo='+encodeURIComponent(cod)+'&ventas_mes='+encodeURIComponent(v)); }catch(e){} cargarReparto(); }
  async function quitarPres(btn){ if(!confirm('¿Quitar esta presentación del producto? (reversible)')) return; try{ await fetch('/api/programacion/pres-quitar?producto='+encodeURIComponent(btn.dataset.prod)+'&presentacion_codigo='+encodeURIComponent(btn.dataset.cod)); }catch(e){} cargarReparto(); }
  async function unificarEnvase(btn){
    var vol = btn.dataset.vol; var sel = document.getElementById('uni-'+vol); if(!sel||!sel.value) return;
    if(!confirm('¿Poner el envase '+sel.value+' a TODOS los productos de '+vol+'ml?')) return;
    btn.disabled=true; btn.textContent='Aplicando…';
    try{
      var t = await (await fetch('/api/programacion/envases-por-tamano')).json();
      var tv = (t.tamanos||[]).find(function(x){ return String(x.volumen_ml)===String(vol); });
      if(tv){ for(var i=0;i<tv.items.length;i++){ var it=tv.items[i]; await fetch('/api/programacion/pres-set-envase?producto='+encodeURIComponent(it.producto)+'&presentacion_codigo='+encodeURIComponent(it.presentacion)+'&envase='+encodeURIComponent(sel.value)); } }
    }catch(e){}
    cargarReparto();
  }

  async function cargarEstacionalidad(){
    var el = document.getElementById('estac-panel'); if(!el) return;
    el.innerHTML = '<div style="color:#94a3b8;padding:20px">Cargando…</div>';
    try{
      var r = await fetch('/api/programacion/estacionalidad-config');
      var d = await r.json();
      if(!d.ok){ el.innerHTML = '<div style="color:#dc2626;padding:20px">Error: '+(d.error||r.status)+'</div>'; return; }
      var h = '';
      h += '<div style="background:linear-gradient(135deg,#6d28d9,#0891b2);color:#fff;padding:16px 20px;border-radius:12px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">';
      h += '<div><div style="font-size:18px;font-weight:800">📈 Estacionalidad de demanda</div><div style="font-size:12px;opacity:.9">El plan produce y compra MÁS antes de los meses fuertes (ej. noviembre · Black Friday)</div></div>';
      h += '<button onclick="estacToggle('+(d.activa?'0':'1')+')" style="background:'+(d.activa?'#16a34a':'#fff')+';color:'+(d.activa?'#fff':'#6d28d9')+';border:none;padding:11px 20px;border-radius:11px;font-weight:800;cursor:pointer;font-size:13px">'+(d.activa?'✅ Activado · apagar':'⚪ Apagado · ACTIVAR')+'</button>';
      h += '</div>';
      h += '<div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:12px">';
      h += '<button onclick="estacRefrescar()" style="background:#0891b2;color:#fff;border:none;padding:9px 15px;border-radius:10px;font-weight:700;cursor:pointer;font-size:12px">🔄 Recalcular del histórico</button>';
      h += '<label style="font-size:12px;color:#475569;font-weight:600">Tope <input id="estac-tope" type="number" step="0.1" min="1.1" max="4" value="'+(d.tope||2)+'" onchange="estacTope(this.value)" style="width:64px;padding:7px;border:1px solid #e6e1f2;border-radius:9px"></label>';
      h += '<span style="font-size:11px;color:#94a3b8">Ningún mes dispara más de este factor</span>';
      h += '</div>';
      h += '<table style="width:100%;border-collapse:collapse;font-size:13px;background:#fff;border:1px solid #ece9f5;border-radius:12px;overflow:hidden"><thead><tr style="background:linear-gradient(180deg,#faf9ff,#f3f1fb);color:#6d28d9"><th style="padding:9px;text-align:left">Mes</th><th style="padding:9px;text-align:right" title="Del histórico Shopify">Auto</th><th style="padding:9px;text-align:right" title="Lo que fija Alejandro a mano · vacío = usa el auto">Override</th><th style="padding:9px;text-align:right">Efectivo</th><th style="padding:9px;text-align:right" title="Lo que el plan aplica (mes ÷ mes actual, capado)">Factor plan</th></tr></thead><tbody>';
      (d.meses||[]).forEach(function(m){
        var fac = (d.factores_aplicados||{})[m.mes];
        var alto = (m.efectivo!=null && Number(m.efectivo)>=1.3);
        h += '<tr style="border-top:1px solid #f1f5f9'+(alto?';background:#fef9f3':'')+'">';
        h += '<td style="padding:8px 9px;font-weight:600">'+m.mes+(alto?' 🔥':'')+'</td>';
        h += '<td style="padding:8px 9px;text-align:right;color:#64748b">'+(m.mult_auto!=null?m.mult_auto:'—')+'</td>';
        h += '<td style="padding:8px 9px;text-align:right"><input type="number" step="0.05" placeholder="auto" value="'+(m.mult_override!=null?m.mult_override:'')+'" data-mes="'+m.mes_num+'" onchange="estacOverride(this.dataset.mes,this.value)" style="width:66px;padding:5px;border:1px solid #e6e1f2;border-radius:7px;text-align:right"></td>';
        h += '<td style="padding:8px 9px;text-align:right;font-weight:700">'+(m.efectivo!=null?m.efectivo:'—')+'</td>';
        h += '<td style="padding:8px 9px;text-align:right;font-weight:700;color:'+(fac>1.05?'#d97706':(fac<0.95?'#0891b2':'#334155'))+'">'+(fac!=null?fac+'×':'—')+'</td>';
        h += '</tr>';
      });
      h += '</tbody></table>';
      h += '<div style="font-size:11px;color:#94a3b8;margin-top:10px">'+(d.activa?'✅ Activado: el plan ya usa estos factores. Regenerá el plan para ver los lotes adelantarse antes de los meses fuertes.':'⚪ Apagado: no afecta el plan. Prendelo cuando quieras · se apaga igual de fácil.')+' · Override vacío = usa el Auto · 🔥 = mes fuerte.</div>';
      el.innerHTML = h;
    }catch(e){ el.innerHTML = '<div style="color:#dc2626;padding:20px">Error: '+e+'</div>'; }
  }
  async function estacToggle(v){ try{ await fetch('/api/programacion/estacionalidad-config?accion=toggle&activa='+v); }catch(e){} cargarEstacionalidad(); }
  async function estacRefrescar(){ var el=document.getElementById('estac-panel'); if(el) el.innerHTML='<div style="color:#94a3b8;padding:20px">Recalculando del histórico…</div>'; try{ await fetch('/api/programacion/estacionalidad-config?accion=refrescar'); }catch(e){} cargarEstacionalidad(); }
  async function estacTope(v){ try{ await fetch('/api/programacion/estacionalidad-config?accion=tope&tope='+encodeURIComponent(v)); }catch(e){} cargarEstacionalidad(); }
  async function estacOverride(mes,v){ try{ await fetch('/api/programacion/estacionalidad-config?accion=override&mes='+mes+'&multiplicador='+encodeURIComponent(v)); }catch(e){} cargarEstacionalidad(); }

  async function cfgCargarCalendar(){
    var box = document.getElementById('cfg-cal-tabla');
    var kpis = document.getElementById('cfg-cal-kpis');
    if(!box) return;
    box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Leyendo calendar...</div>';
    try {
      var r = await fetch('/api/planta/calendar-debug');
      var d = await r.json();
      if(!r.ok){ box.innerHTML = '<div style="color:#dc2626">Error: '+(d.error||'')+'</div>'; return; }
      kpis.innerHTML = ''
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:10px;padding:12px"><div style="font-size:10px;color:#64748b;text-transform:uppercase">Eventos</div><div style="font-size:24px;font-weight:800;color:#0f172a">'+d.total_eventos+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #15803d;border-radius:10px;padding:12px"><div style="font-size:10px;color:#64748b;text-transform:uppercase">✓ Matcheados</div><div style="font-size:24px;font-weight:800;color:#15803d">'+d.matcheados+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(d.en_conflicto?'#dc2626':'#15803d')+';border-radius:10px;padding:12px"><div style="font-size:10px;color:#64748b;text-transform:uppercase">⚠ Conflicto</div><div style="font-size:24px;font-weight:800;color:'+(d.en_conflicto?'#dc2626':'#15803d')+'">'+d.en_conflicto+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(d.sin_match_aceptable?'#d97706':'#15803d')+';border-radius:10px;padding:12px"><div style="font-size:10px;color:#64748b;text-transform:uppercase">? Sin match</div><div style="font-size:24px;font-weight:800;color:'+(d.sin_match_aceptable?'#d97706':'#15803d')+'">'+d.sin_match_aceptable+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:10px;padding:12px"><div style="font-size:10px;color:#64748b;text-transform:uppercase">⚖ Con kg</div><div style="font-size:24px;font-weight:800;color:#7c3aed">'+d.con_kg_detectados+'</div></div>';
      var eventos = d.eventos || [];
      if(!eventos.length){
        box.innerHTML = '<div style="background:#fef3c7;border:1px solid #fbbf24;color:#92400e;padding:20px;border-radius:10px;text-align:center"><b>Sin eventos en calendar</b><br><span style="font-size:12px">Verifica que GCAL_ICAL_URL esté configurado en Render.</span></div>';
        return;
      }
      var html = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">'
        +'<thead style="background:#f9fafb"><tr>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Evento</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Fecha</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Kg</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producto matcheado</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Score</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Estado</th>'
        +'</tr></thead><tbody>';
      eventos.forEach(function(e){
        var col = {matcheado:'#15803d',conflicto:'#dc2626',sin_match:'#d97706',no_relacionado:'#94a3b8'}[e.estado] || '#475569';
        var ico = {matcheado:'✓',conflicto:'⚠',sin_match:'?',no_relacionado:'·'}[e.estado] || '';
        html += '<tr style="border-top:1px solid #f1f5f9">'
          +'<td style="padding:7px 10px"><b>'+_escHTML(e.titulo)+'</b></td>'
          +'<td style="padding:7px 10px;font-family:monospace;font-size:11px">'+_escHTML(e.fecha)+'</td>'
          +'<td style="padding:7px 10px;text-align:right;font-family:monospace;font-weight:700">'+(e.kg_detectados!=null?e.kg_detectados+'kg':'<span style="color:#94a3b8">—</span>')+'</td>'
          +'<td style="padding:7px 10px;font-size:11px">'+(e.producto_match?'<b>'+_escHTML(e.producto_match)+'</b>':'<span style="color:#94a3b8">—</span>')+'</td>'
          +'<td style="padding:7px 10px;text-align:right;font-family:monospace;color:'+col+';font-weight:700">'+e.score_match+'</td>'
          +'<td style="padding:7px 10px;text-align:center"><span style="background:'+col+'22;color:'+col+';padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700">'+ico+' '+e.estado+'</span></td>'
          +'</tr>';
        if(e.candidatos_top3 && e.candidatos_top3.length > 1 && e.estado==='conflicto'){
          html += '<tr><td colspan="6" style="padding:4px 30px;background:#fef2f2;font-size:10px;color:#7f1d1d">Candidatos: '+e.candidatos_top3.map(function(cc){return cc.producto+' ('+cc.score+')'}).join(' · ')+'</td></tr>';
        }
      });
      html += '</tbody></table></div>';
      box.innerHTML = html;
    } catch(err){ box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+err.message+'</div>'; }
  }

  async function cfgCargarAliases(){
    var box = document.getElementById('cfg-cal-tabla');
    box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r = await fetch('/api/auto-plan/configs/sku');
      var d = await r.json();
      var rows = d.configs || [];
      var html = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow-x:auto">'
        +'<div style="padding:12px 14px;background:#f9fafb;font-size:12px;color:#475569"><b>Aliases del Calendar por producto</b><br><span style="font-size:11px;color:#64748b">Separa con coma. Ejemplo: <code style="background:#fff;padding:1px 5px;border-radius:3px">AH 1.5%, AH, Hidratante AH</code></span></div>'
        +'<table style="width:100%;border-collapse:collapse;font-size:12px">'
        +'<thead style="background:#f9fafb"><tr>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producto</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Aliases (CSV)</th>'
        +'</tr></thead><tbody>';
      rows.forEach(function(c){
        html += '<tr style="border-top:1px solid #f1f5f9">'
          +'<td style="padding:7px 10px"><b>'+_escHTML(c.producto_nombre)+'</b></td>'
          +'<td style="padding:5px 10px"><input type="text" value="'+_escAttr(c.alias_calendar||'')+'" placeholder="alias1, alias2, ..." onblur="apAliasGuardar('+c.id+', this)" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:5px;font-size:12px"></td>'
          +'</tr>';
      });
      html += '</tbody></table></div>';
      box.innerHTML = html;
    } catch(e){ box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>'; }
  }

  async function apAliasGuardar(id, input){
    try {
      var r = await fetch('/api/auto-plan/configs/sku/'+id, {
        method:'PUT', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({alias_calendar: input.value.trim() || null})
      });
      if(r.ok){ input.style.background='#f0fdf4'; setTimeout(function(){input.style.background='';}, 800); }
    } catch(e){}
  }

  async function cfgCargarRiesgo(){
    var box = document.getElementById('cfg-riesgo-tabla');
    if(!box) return;
    try {
      var r = await fetch('/api/auto-plan/configs/perfil-riesgo');
      var d = await r.json();
      var rows = d.perfiles || [];
      box.innerHTML = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden"><table style="width:100%;border-collapse:collapse;font-size:12px"><thead style="background:#f9fafb"><tr>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producto</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Pigmento</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Color</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Ácido</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Riesgo arrastre</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Notas</th>'
        +'</tr></thead><tbody>'
        + rows.map(function(p){
          var pigCol = p.tiene_pigmento ? '#dc2626' : '#94a3b8';
          var rieCol = p.riesgo_arrastre_pct >= 50 ? '#dc2626' : (p.riesgo_arrastre_pct >= 25 ? '#d97706' : '#15803d');
          return '<tr style="border-top:1px solid #f1f5f9">'
            +'<td style="padding:7px 10px"><b>'+_escHTML(p.producto_nombre)+'</b></td>'
            +'<td style="padding:7px 10px;text-align:center"><span style="background:'+pigCol+'22;color:'+pigCol+';padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700">'+(p.tiene_pigmento?'SÍ':'no')+'</span></td>'
            +'<td style="padding:7px 10px;font-size:11px;color:#64748b">'+_escHTML(p.color_descripcion||'—')+'</td>'
            +'<td style="padding:7px 10px;text-align:center">'+(p.es_acido?'🧪':'—')+'</td>'
            +'<td style="padding:7px 10px;text-align:right;color:'+rieCol+';font-weight:700">'+p.riesgo_arrastre_pct+'%</td>'
            +'<td style="padding:7px 10px;font-size:11px;color:#64748b">'+_escHTML((p.notas||'').substring(0,60))+'</td>'
            +'</tr>';
        }).join('')
        +'</tbody></table></div>';
    } catch(e){
      box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  // Safe modal backdrop close — placed after all functions are defined
  (function(){
    var _m = document.getElementById('modal-programar');
    if(_m) _m.addEventListener('click', function(e){ if(e.target===this) cerrarModalProgramar(); });
  })();

  var _planLoaded = false;
  var _planData   = null;
  var _planDias   = 60;

  function _setPlanHorizonBtn(d){
    [15,30,60,90,180,365].forEach(function(n){
      var b=document.getElementById('plan-btn-'+n);
      if(b){ b.style.background=d===n?'#1a4a7a':'#fff'; b.style.color=d===n?'#fff':'#1a4a7a'; }
    });
  }

  // ── Auto-SC IA (Sebastián 30-abr-2026): panel automático en tab Plan
  function _autoscFmtFecha(iso){
    if(!iso) return '—';
    try{
      var d = new Date(iso);
      if(isNaN(d.getTime())) return iso;
      return d.toLocaleDateString('es-CO', {day:'2-digit', month:'short'}) + ' ' + d.toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit'});
    }catch(e){ return iso; }
  }
  function _autoscDiasSince(iso){
    if(!iso) return null;
    try{
      var d = new Date(iso); var now = new Date();
      return Math.floor((now-d) / 86400000);
    }catch(e){ return null; }
  }
  async function autoscRecargar(){
    var sub = document.getElementById('autosc-subtitle');
    if(sub) sub.textContent = 'Cargando estado…';
    try{
      var r = await fetch('/api/planta/auto-sc-status', {credentials:'same-origin'});
      if(!r.ok) throw new Error('HTTP '+r.status);
      var s = await r.json();
      var ventana = s.ventana_mensual_activa
        ? '🟢 Ventana mensual activa (día '+s.dia_mes+'/5) · próxima ejecución cron mensual'
        : '⚪ Día '+s.dia_mes+' del mes · próxima ventana mensual: '+s.proxima_ventana_mensual;
      var hoyEsLunes = (new Date(s.hoy)).getUTCDay() === 1;
      if(hoyEsLunes) ventana += ' · 🟡 Hoy es lunes (cron urgente)';
      if(sub) sub.textContent = ventana;

      document.getElementById('autosc-mes-actual').textContent = (s.scs_mes_actual||0) + ' SCs';
      var elM = document.getElementById('autosc-last-mensual');
      var elMs = document.getElementById('autosc-last-mensual-sub');
      if(s.last_mensual){
        var d = _autoscDiasSince(s.last_mensual.ejecutado_at);
        elM.textContent = (s.last_mensual.scs_creadas||0)+' SCs';
        elMs.textContent = _autoscFmtFecha(s.last_mensual.ejecutado_at) + (d!=null ? ' · hace '+d+'d' : '');
      } else { elM.textContent='—'; elMs.textContent='Sin ejecuciones aún'; }
      var elU = document.getElementById('autosc-last-urgente');
      var elUs = document.getElementById('autosc-last-urgente-sub');
      if(s.last_urgente){
        var d2 = _autoscDiasSince(s.last_urgente.ejecutado_at);
        elU.textContent = (s.last_urgente.scs_creadas||0)+' SCs';
        elUs.textContent = _autoscFmtFecha(s.last_urgente.ejecutado_at) + (d2!=null ? ' · hace '+d2+'d' : '');
      } else { elU.textContent='—'; elUs.textContent='Sin ejecuciones aún'; }

      var elP = document.getElementById('autosc-prox');
      var elPs = document.getElementById('autosc-prox-sub');
      if(s.ventana_mensual_activa){
        elP.textContent = 'AHORA';
        elPs.textContent = 'Día '+s.dia_mes+' (1-5) · ejecutar cuando quieras';
      } else if(hoyEsLunes){
        elP.textContent = 'HOY';
        elPs.textContent = 'Lunes · cron urgente activo';
      } else {
        var proxLunes = new Date(s.proximo_lunes);
        elP.textContent = proxLunes.toLocaleDateString('es-CO',{day:'2-digit',month:'short'});
        elPs.textContent = 'Lunes · luego día 1-5 ('+s.proxima_ventana_mensual+')';
      }

      var wrap = document.getElementById('autosc-recientes-wrap');
      var list = document.getElementById('autosc-recientes-list');
      if(s.recientes && s.recientes.length){
        wrap.style.display = 'block';
        list.innerHTML = s.recientes.slice(0,12).map(function(sc){
          var prov = (sc.proveedor||'').split(',')[0] || 'sin proveedor';
          var icono = sc.estado === 'Pendiente' ? '🟡' : (sc.estado === 'Aprobada' ? '✅' : (sc.estado === 'Rechazada' ? '❌' : '⚪'));
          return '<a class="autosc-pill" href="/solicitudes#'+encodeURIComponent(sc.numero)+'" title="'+(sc.observaciones||'').replace(/"/g,'&quot;')+'">'+icono+' '+sc.numero+' · '+prov+' · '+(sc.items_count||0)+' MPs</a>';
        }).join('');
      } else { wrap.style.display = 'none'; }
    }catch(e){
      if(sub) sub.textContent = 'No se pudo cargar el estado · '+(e.message||e);
    }
  }
  async function autoscPreview(modo){
    var msg = document.getElementById('autosc-msg');
    msg.style.display='block';
    msg.innerHTML = '⏳ Calculando preview ('+modo+')…';
    try{
      var r = await fetch('/api/planta/auto-sc-preview?modo='+encodeURIComponent(modo), {credentials:'same-origin'});
      if(!r.ok) throw new Error('HTTP '+r.status);
      var p = await r.json();
      var k = p.kpis || {};
      var sps = p.scs_por_proveedor || {};
      var huerf = p.items_huerfanos || [];
      var nProv = Object.keys(sps).length;
      var html = '<b>📊 Preview '+modo+'</b> · '+nProv+' SCs por crear · '+(k.total_items||0)+' MPs · '+Math.round((k.total_g||0)/1000)+' kg<br>';
      if(nProv){
        html += '<div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:6px">';
        Object.entries(sps).slice(0,8).forEach(function(kv){
          html += '<span style="background:rgba(0,0,0,.18);padding:3px 8px;border-radius:10px">'+kv[0]+': '+kv[1].length+' MPs</span>';
        });
        html += '</div>';
      }
      if(huerf.length){
        html += '<div style="margin-top:6px;color:#fde68a">⚠️ '+huerf.length+' MPs sin proveedor sugerido (no se incluirán)</div>';
      }
      msg.innerHTML = html;
    }catch(e){
      msg.innerHTML = '❌ Error en preview: '+(e.message||e);
    }
  }
  async function autoscGenerar(modo, forzar){
    var nombreModo = modo === 'urgente' ? 'URGENTE (lunes, 14d)' : 'MENSUAL (60-90d)';
    var prompt = forzar
      ? '⚠️ FORZAR nuevo pedido aunque YA hay SCs creadas este mes?\n\n(Catalina podría recibir SCs duplicadas)\n\n¿Continuar?'
      : 'Vas a crear las SCs reales en estado Pendiente '+nombreModo+'.\n\nCatalina y Alejandro las verán en /solicitudes para revisar/editar/aprobar.\n\n¿Continuar?';
    if(!confirm(prompt)) return;
    var msg = document.getElementById('autosc-msg');
    msg.style.display='block';
    msg.innerHTML = '⏳ Generando SCs ('+modo+')…';
    try{
      var body = {modo: modo, enviar_email: true};
      if(forzar) body.forzar = true;
      var r = await fetch('/api/planta/auto-sc-generar', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body),
      });
      var data = await r.json();
      // Anti-duplicado · 409
      if(r.status === 409 && data.duplicado){
        if(confirm(data.mensaje + '\n\n¿Forzar igual?')){
          return autoscGenerar(modo, true);
        }
        msg.innerHTML = '⚠️ ' + data.mensaje;
        return;
      }
      if(!r.ok || !data.ok) throw new Error(data.error || ('HTTP '+r.status));
      msg.innerHTML = '✅ '+data.mensaje + ' · <a href="/solicitudes" style="color:#fff;text-decoration:underline">ver en Compras</a>';
      autoscRecargar();
    }catch(e){
      msg.innerHTML = '❌ Error generando SCs: '+(e.message||e);
    }
  }

  // ── Auto-SC MEE (Sebastián 1-may-2026): China 9m + Local 90d, MOQ-aware
  async function autoscMeeRecargar(){
    var sub = document.getElementById('autosc-mee-subtitle');
    if(sub) sub.textContent = 'Cargando estado…';
    try{
      var r = await fetch('/api/planta/auto-sc-mee-status', {credentials:'same-origin'});
      if(!r.ok) throw new Error('HTTP '+r.status);
      var s = await r.json();
      document.getElementById('autosc-mee-mes-actual').textContent = (s.scs_mes_actual||0)+' SCs';
      var configsEl = document.getElementById('autosc-mee-configs');
      var configsSub = document.getElementById('autosc-mee-configs-sub');
      if(configsEl){ configsEl.textContent = s.mee_configurados||0; }
      if(configsSub){ configsSub.textContent = (s.mee_con_proveedor||0)+' con proveedor'; }
      var skusEl = document.getElementById('autosc-mee-skus');
      if(skusEl){ skusEl.textContent = s.skus_con_mee||0; }
      var lastEl = document.getElementById('autosc-mee-last');
      var lastSub = document.getElementById('autosc-mee-last-sub');
      if(s.last_mensual && lastEl){
        lastEl.textContent = (s.last_mensual.scs_creadas||0)+' SCs';
        if(lastSub) lastSub.textContent = _autoscFmtFecha(s.last_mensual.ejecutado_at);
      } else if(lastEl){
        lastEl.textContent = '—';
        if(lastSub) lastSub.textContent = 'Sin ejecuciones aún';
      }
      var warn = document.getElementById('autosc-mee-config-warn');
      if(warn) warn.style.display = s.configuracion_lista ? 'none' : 'block';
      if(sub){
        if(!s.configuracion_lista){
          sub.textContent = 'Pendiente configurar proveedores MEE y mapping SKU→componentes';
        } else {
          sub.textContent = (s.mee_con_proveedor||0)+' MEE listos · '+(s.skus_con_mee||0)+' SKUs mapeados';
        }
      }
    }catch(e){
      if(sub) sub.textContent = 'No se pudo cargar el estado · '+(e.message||e);
    }
  }
  async function autoscMeePreview(modo){
    var origen = (document.getElementById('autosc-mee-origen')||{value:''}).value || '';
    var msg = document.getElementById('autosc-mee-msg');
    msg.style.display='block';
    msg.innerHTML = '⏳ Calculando preview MEE ('+modo+(origen?' / '+origen:'')+')…';
    try{
      var url = '/api/planta/auto-sc-mee-preview?modo='+encodeURIComponent(modo);
      if(origen) url += '&origen='+encodeURIComponent(origen);
      var r = await fetch(url, {credentials:'same-origin'});
      if(!r.ok) throw new Error('HTTP '+r.status);
      var p = await r.json();
      if(p.razon_vacio){
        msg.innerHTML = '⚠️ '+p.razon_vacio;
        return;
      }
      var k = p.kpis || {};
      var sps = p.scs_por_proveedor || {};
      var huerf = p.items_huerfanos || [];
      var nProv = Object.keys(sps).length;
      var html = '<b>📊 Preview MEE '+modo+'</b> · '+nProv+' SCs · '+(k.total_items||0)+' MEE · '+Math.round(k.total_unidades||0).toLocaleString()+' ud';
      if(k.total_valor_estimado) html += ' · $'+Math.round(k.total_valor_estimado).toLocaleString();
      html += '<br>SKUs evaluados: '+(k.skus_evaluados||0)+' · MEE evaluados: '+(k.mee_evaluados||0);
      if(nProv){
        html += '<div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:6px">';
        Object.entries(sps).slice(0,8).forEach(function(kv){
          var totalUd = kv[1].reduce(function(a,b){return a+b.cantidad_unidades;},0);
          html += '<span style="background:rgba(0,0,0,.18);padding:3px 8px;border-radius:10px">'+kv[0]+': '+kv[1].length+' MEE / '+Math.round(totalUd).toLocaleString()+' ud</span>';
        });
        html += '</div>';
      }
      if(huerf.length){
        html += '<div style="margin-top:6px;color:#fde68a">⚠️ '+huerf.length+' MEE sin proveedor (no incluidos)</div>';
      }
      msg.innerHTML = html;
    }catch(e){
      msg.innerHTML = '❌ Error preview MEE: '+(e.message||e);
    }
  }
  // ══════════════════════════════════════════════════════════════
  // ESTADO SOLICITUDES · ⭐ Plan automático Lunes 7am (Sebastián 1-may-2026)
  // ══════════════════════════════════════════════════════════════
  async function estadoSolicitudesRecargar(){
    var sub = document.getElementById('estado-sol-subtitle');
    var grid = document.getElementById('estado-sol-grid');
    var det = document.getElementById('estado-sol-detalle');
    if(sub) sub.textContent = 'Cargando...';
    try{
      // Cargar resumen de SCs activas + workflow lunes
      var [r1, r2] = await Promise.all([
        fetch('/api/planta/estado-solicitudes', {credentials:'same-origin'}),
        fetch('/api/planta/scs-pedidas-resumen?dias=45', {credentials:'same-origin'}),
      ]);
      var d = await r1.json();
      var pedidas = await r2.json();
      if(!r1.ok) throw new Error(d.error || 'HTTP '+r1.status);
      var sol = d.solicitado_ultimo_mes || {};
      var pend = d.pendiente_solicitar || {};
      var ult = d.ultimo_workflow_lunes;
      var ejecutado = d.workflow_lunes_ejecutado_esta_semana;
      var pkpis = (pedidas && pedidas.kpis) || {};
      var pmes = (pedidas && pedidas.mes_actual) || {};

      if(sub){
        if(ejecutado && ult){
          sub.textContent = '✅ Workflow lunes 7am ejecutado · ' + ult.bloqueadas + ' producciones bloqueadas · semana ' + ult.fecha_lunes;
        } else if(ult){
          sub.textContent = '⚠️ Última ejecución: ' + (ult.fecha_lunes||'—') + ' · esta semana NO se ha ejecutado';
        } else {
          sub.textContent = '⏳ Workflow lunes 7am NO se ha ejecutado nunca · click "Ejecutar lunes 7am ahora"';
        }
      }

      function tile(label, val, color, sub){
        return '<div style="background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.18);border-radius:8px;padding:10px 12px">'
          +'<div style="font-size:9px;text-transform:uppercase;letter-spacing:.4px;opacity:.75">'+label+'</div>'
          +'<div style="font-size:22px;font-weight:800;color:'+(color||'#fff')+';margin-top:2px">'+val+'</div>'
          +(sub?'<div style="font-size:10px;opacity:.7;margin-top:2px">'+sub+'</div>':'')
          +'</div>';
      }
      // Tiles con estado real de SCs (Sebastián 1-may-2026: claridad anti-doble pedido)
      grid.innerHTML = ''
        + tile('🟡 Pendiente aprobación', pkpis.pendiente || 0, '#fbbf24', 'esperando Catalina')
        + tile('🟢 Aprobadas', pkpis.aprobada || 0, '#10b981', 'OC en proceso')
        + tile('🚚 En tránsito', pkpis.en_transito || 0, '#3b82f6', 'mercancía viajando')
        + tile('✅ Recibidas', pkpis.recibida || 0, '#10b981', 'en bodega')
        + tile('Pendiente solicitar', (pend.mp_30d||0)+(pend.mee_30d||0), (pend.mp_30d+pend.mee_30d)>0 ? '#fbbf24' : '#a3e635', 'cron día 1-5');

      // Detalle anti-duplicado · qué se puede pedir y qué no
      var html = '';
      if(pmes.mp_ya_pedido || pmes.mee_ya_pedido){
        html += '<div style="background:#dbeafe;color:#1e40af;padding:6px 10px;border-radius:6px;margin-bottom:6px;font-size:11px">'
          + '<b>⚠️ Anti-duplicado activo</b> · este mes ya hay '
          + (pmes.mp_ya_pedido ? (pmes.mp_creadas+' SCs MP') : '')
          + (pmes.mp_ya_pedido && pmes.mee_ya_pedido ? ' + ' : '')
          + (pmes.mee_ya_pedido ? (pmes.mee_creadas+' SCs MEE') : '')
          + ' creadas. Si das "Generar mensual" otra vez, te pediré confirmación para FORZAR.'
          + '</div>';
      }
      if(ult){
        html += '<b>Última ejecución lunes 7am ('+ult.fecha_lunes+'):</b><br>'
          + '✅ '+(ult.bloqueadas||0)+' producciones bloqueadas · '
          + '🔄 '+(ult.sincronizadas||0)+' sincronizadas Calendar · '
          + '🤖 '+(ult.asignadas||0)+' asignadas IA · '
          + '🧹 '+(ult.limpiezas_creadas||0)+' limpiezas';
      } else {
        html += 'El cron interno corre lunes 7:00 AM automáticamente.';
      }
      // Listar SCs activas (top 5)
      if(pedidas && pedidas.scs && pedidas.scs.length){
        html += '<div style="margin-top:10px"><b>SCs activas (' + pedidas.scs.length + '):</b><br>'
          + pedidas.scs.slice(0,8).map(function(sc){
            return '<div style="margin-top:3px;padding:3px 6px;background:rgba(255,255,255,.08);border-left:3px solid '+sc.color+';border-radius:3px;font-size:10px">'
              + sc.icon + ' <b>' + sc.numero + '</b> · ' + sc.estado_label
              + ' · ' + sc.categoria
              + (sc.fecha ? ' · ' + sc.fecha : '')
              + '</div>';
          }).join('') + '</div>';
      }
      if(det) det.innerHTML = html;
    }catch(e){
      if(sub) sub.textContent = 'Error: '+(e.message||e);
    }
  }
  async function ejecutarLunes7am(){
    if(!confirm('Ejecutar workflow LUNES 7AM completo AHORA?\n\n1. Sync Shopify\n2. Sync Calendar (force)\n3. Auto-asignar IA toda la semana\n4. Bloquear producciones (no más cambios)\n5. Email Alejandro\n\n¿Continuar?')) return;
    var sub = document.getElementById('estado-sol-subtitle');
    if(sub) sub.textContent = '⏳ Ejecutando workflow completo...';
    try{
      var r = await fetch('/api/planta/ejecutar-lunes-7am', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'}, body:'{}'
      });
      var d = await r.json();
      if(!r.ok || !d.ok) throw new Error(d.error || 'HTTP '+r.status);
      var res = d.resultado || {};
      var msg = '⭐ ' + d.mensaje + '\n\n';
      msg += '✅ ' + (res.bloqueadas||0) + ' producciones bloqueadas\n';
      msg += '🔄 ' + (res.sincronizadas||0) + ' sincronizadas del Calendar\n';
      msg += '🤖 ' + (res.asignadas||0) + ' asignadas por IA\n';
      msg += '🧹 ' + (res.limpiezas_creadas||0) + ' limpiezas auto\n';
      msg += '📧 ' + (res.email_enviado ? 'Email enviado' : 'Email skipped') + '\n\n';
      if(res.pasos) msg += res.pasos.join('\n');
      alert(msg);
      estadoSolicitudesRecargar();
      if(typeof semanaRecargar === 'function') semanaRecargar();
    }catch(e){
      alert('❌ Error: '+(e.message||e));
    }
  }

  // ══════════════════════════════════════════════════════════════
  // ESTA SEMANA · vista principal jefe de produccion (Sebastián 1-may-2026)
  // IA asigna todo · operario solo da click para avanzar
  // ══════════════════════════════════════════════════════════════
  async function semanaRecargar(){
    var sub = document.getElementById('semana-subtitle');
    var kpis = document.getElementById('semana-kpis');
    var grid = document.getElementById('semana-grid');
    var salas = document.getElementById('semana-salas');
    if(sub) sub.textContent = '⏳ Cargando...';
    try{
      var r = await fetch('/api/planta/semana-produccion', {credentials:'same-origin'});
      var d = await r.json();
      if(!r.ok) throw new Error(d.error || 'HTTP '+r.status);
      var k = d.kpis || {};
      var cdiag = d.calendar_diag || {};
      var subText = '📅 Calendar-first · ' + (k.total_producciones_semana||0) + ' producciones · ' + (k.total_kg_semana||0) + ' kg total · ' + (k.total_limpiezas||0) + ' limpiezas';
      if(cdiag.con_match) subText += ' · ✅ ' + cdiag.con_match + ' SKUs reconocidos';
      if(k.sin_asignar_ia) subText += ' · ⚠️ ' + k.sin_asignar_ia + ' sin asignar';
      if(sub) sub.textContent = subText;
      // Banner debug si hay eventos sin match
      var msgEl = document.getElementById('semana-msg');
      if(msgEl){
        var lines = [];
        if(cdiag.sin_match_sample && cdiag.sin_match_sample.length){
          lines.push('ℹ️ Eventos en Calendar sin match preciso a SKU (se muestran con título crudo): ' +
            cdiag.sin_match_sample.slice(0,3).map(function(s){return '<code>'+esc(s[0])+'</code>';}).join(', '));
        }
        if(cdiag.total === 0){
          lines.push('⚠️ <b>No hay eventos del Calendar</b> · revisa GCAL_ICAL_URL en Render env vars');
        } else if(cdiag.en_semana === 0){
          lines.push('ℹ️ Calendar tiene '+cdiag.total+' eventos pero ninguno cae en esta semana');
        }
        if(lines.length){
          msgEl.style.display='block';
          msgEl.style.background='rgba(251,191,36,.2)';
          msgEl.innerHTML = lines.join('<hr style="margin:6px 0;border:0;border-top:1px solid rgba(255,255,255,.3)">');
        } else {
          msgEl.style.display='none';
        }
      }

      // KPIs pills
      function pill(label, val, color){
        return '<span style="background:'+(color||'rgba(255,255,255,.18)')+';padding:5px 12px;border-radius:14px;font-size:11px"><b>'+val+'</b> '+label+'</span>';
      }
      kpis.innerHTML = pill('producciones', k.total_producciones_semana||0)
        + pill('kg', (k.total_kg_semana||0).toLocaleString())
        + pill('limpiezas', k.total_limpiezas||0)
        + (k.sin_asignar_ia ? pill('sin asignar IA', k.sin_asignar_ia, 'rgba(220,38,38,.7)') : '');

      // 5 cards L-V
      var dias = d.dias || [];
      grid.innerHTML = dias.map(function(dia){
        var bgCard = dia.es_hoy ? '#fef3c7' : (dia.tipo_dia==='PRODUCCIÓN' ? 'rgba(255,255,255,.97)' : 'rgba(255,255,255,.85)');
        var border = dia.es_hoy ? '3px solid #f59e0b' : '1px solid rgba(255,255,255,.3)';
        var html = '<div style="background:'+bgCard+';border:'+border+';border-radius:8px;padding:8px;color:#0f172a;min-height:200px;font-size:11px">';
        html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;border-bottom:1px solid #e2e8f0;padding-bottom:4px">';
        html += '<b style="font-size:13px">'+dia.nombre_dia+' '+dia.fecha.substring(5)+'</b>';
        if(dia.es_hoy) html += '<span style="background:#f59e0b;color:#fff;padding:1px 6px;border-radius:6px;font-size:9px;font-weight:700">HOY</span>';
        html += '</div>';
        html += '<div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px">'+dia.tipo_dia+'</div>';

        // Producciones
        if(dia.producciones && dia.producciones.length){
          dia.producciones.forEach(function(p){
            var stColor = {
              'completado':'#10b981',
              'en_proceso':'#1d4ed8',
              'iniciado':'#1d4ed8',
              'programado':'#64748b',
            }[p.estado] || '#64748b';
            // Card · color borde varía segun estado/origen
            var bordeCol = stColor;
            if(p.estado === 'planeado' && p.desde_calendar) bordeCol = '#7c3aed'; // morado para planeado-calendar
            html += '<div style="background:rgba(255,255,255,.6);border-left:3px solid '+bordeCol+';padding:5px 7px;margin-bottom:4px;border-radius:4px;font-size:10px">';
            var icon = '';
            if(p.bloqueado) icon = '🔒 ';
            else if(p.estado === 'planeado') icon = '📅 ';
            else if(!p.tiene_match && p.desde_calendar) icon = '❓ ';
            html += '<div style="font-weight:700;color:#0f172a" title="'+esc(p.titulo_calendar||p.producto)+'">'+icon+esc(p.producto.substring(0,22))+'</div>';
            html += '<div style="color:#475569">'+p.kg+'kg · '+p.lotes+' lt';
            if(p.area && p.area.codigo) html += ' · 🏭 '+p.area.codigo;
            if(p.envasado) html += ' → '+p.envasado;
            html += '</div>';
            // Operarios mini
            var ops = [];
            if(p.operarios.dispensacion) ops.push('disp:'+p.operarios.dispensacion.split(' ')[0]);
            if(p.operarios.elaboracion) ops.push('elab:'+p.operarios.elaboracion.split(' ')[0]);
            if(p.operarios.envasado) ops.push('env:'+p.operarios.envasado.split(' ')[0]);
            if(ops.length) html += '<div style="color:#64748b;font-size:9px;margin-top:2px">👤 '+ops.join(' · ')+'</div>';
            // Acción inline (data-attrs para evitar problemas de quoting)
            if(p.accion){
              var btnCol = (p.accion === 'iniciar' || p.accion === 'iniciar_calendar') ? '#10b981'
                          : (p.accion === 'terminar' ? '#1d4ed8' : '#7c3aed');
              if(p.accion === 'iniciar_calendar' && p.payload_iniciar){
                // Calendar-first: payload completo en data-payload (JSON encoded)
                var payB64 = btoa(unescape(encodeURIComponent(JSON.stringify(p.payload_iniciar))));
                html += '<button class="semana-accion-btn" data-tipo="iniciar_calendar" data-payload="'+payB64+'" style="margin-top:3px;width:100%;padding:3px 8px;background:'+btnCol+';color:#fff;border:none;border-radius:3px;font-size:10px;font-weight:700;cursor:pointer">'+esc(p.accion_label)+'</button>';
              } else {
                html += '<button class="semana-accion-btn" data-tipo="'+p.accion+'" data-id="'+(p.id||0)+'" style="margin-top:3px;width:100%;padding:3px 8px;background:'+btnCol+';color:#fff;border:none;border-radius:3px;font-size:10px;font-weight:700;cursor:pointer">'+esc(p.accion_label)+'</button>';
              }
            } else if(p.estado === 'completado'){
              html += '<div style="margin-top:3px;color:#10b981;font-size:9px;font-weight:700">✅ Completada</div>';
            }
            html += '</div>';
          });
        } else if(dia.tipo_dia === 'PRODUCCIÓN'){
          html += '<div style="color:#94a3b8;font-style:italic;font-size:10px">Sin producciones programadas</div>';
        }
        // Limpiezas
        if(dia.limpiezas && dia.limpiezas.length){
          dia.limpiezas.forEach(function(l){
            html += '<div style="background:#fef3c7;border-left:3px solid #f59e0b;padding:4px 6px;margin-bottom:3px;border-radius:3px;font-size:9px;color:#78350f">';
            html += '<b>🧹 Limpieza '+esc(l.area)+'</b>';
            if(l.asignado_a) html += '<br>👤 '+esc(l.asignado_a.split(' ')[0]);
            if(l.accion){
              html += '<button class="semana-accion-btn" data-tipo="marcar_limpia" data-id="'+l.id+'" style="margin-top:2px;width:100%;padding:2px 6px;background:#10b981;color:#fff;border:none;border-radius:3px;font-size:9px;cursor:pointer">✓ Limpiada</button>';
            }
            html += '</div>';
          });
        }
        if(!dia.producciones.length && !dia.limpiezas.length && dia.tipo_dia !== 'PRODUCCIÓN'){
          html += '<div style="color:#94a3b8;font-style:italic;font-size:10px">Día de acondicionamiento/conteo</div>';
        }
        html += '</div>';
        return html;
      }).join('');

      // Salas estado mini
      salas.innerHTML = '<span style="font-size:10px;opacity:.85;margin-right:4px;align-self:center">Salas:</span>' +
        (d.salas||[]).map(function(s){
          var col = {'libre':'#10b981','ocupada':'#dc2626','sucia':'#f59e0b','limpiando':'#3b82f6'}[s.estado] || '#94a3b8';
          var ico = {'libre':'🟢','ocupada':'🔴','sucia':'🟡','limpiando':'🔵'}[s.estado] || '⚪';
          return '<span title="'+esc(s.nombre)+' · '+s.estado+'" style="background:rgba(255,255,255,.15);padding:3px 8px;border-radius:10px;font-size:10px;border-left:3px solid '+col+';cursor:default">'+ico+' '+s.codigo+'</span>';
        }).join('');

    }catch(e){
      if(sub) sub.textContent = '❌ Error: '+(e.message||e);
    }
  }
  // Event delegation · evita quoting issues con onclick inline
  document.addEventListener('click', function(ev){
    var btn = ev.target.closest && ev.target.closest('.semana-accion-btn');
    if(!btn) return;
    var tipo = btn.getAttribute('data-tipo');
    // Calendar-first: si trae payload, decodificar y usar
    var payload = btn.getAttribute('data-payload');
    if(tipo === 'iniciar_calendar' && payload){
      try{
        var pl = JSON.parse(decodeURIComponent(escape(atob(payload))));
        accionRapidaCalendar(tipo, pl);
        return;
      }catch(e){
        console.error('payload decode failed', e);
        return;
      }
    }
    var id = parseInt(btn.getAttribute('data-id') || '0', 10);
    if(tipo && id) accionRapida(tipo, id);
  });

  async function accionRapidaCalendar(tipo, payload){
    // Calendar-first iniciar: crea fila DB + auto-asigna IA + marca en_proceso
    if(!confirm('▶ Iniciar producción "'+(payload.producto||'')+'"?\n\n• Crea registro en DB ahora\n• IA asigna área óptima\n• IA rota operarios\n• Marca como en proceso')) return;
    var msg = document.getElementById('semana-msg');
    msg.style.display='block';
    msg.innerHTML = '⏳ Creando registro y asignando IA...';
    try{
      var body = Object.assign({tipo: 'iniciar_calendar'}, payload);
      var r = await fetch('/api/planta/accion-rapida', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body),
      });
      var d = await r.json();
      if(!r.ok || (d.ok === false && d.error)) throw new Error(d.error || 'HTTP '+r.status);
      msg.innerHTML = '✅ '+ (d.mensaje || 'OK');
      setTimeout(function(){ msg.style.display='none'; }, 3000);
      semanaRecargar();
      if(typeof salasVivoRecargar === 'function') salasVivoRecargar();
    }catch(e){
      msg.innerHTML = '❌ Error: '+(e.message||e);
    }
  }

  async function accionRapida(tipo, id){
    var labels = {
      'iniciar': '▶ Iniciar producción',
      'iniciar_produccion': '▶ Iniciar producción',
      'terminar': '✓ Terminar producción (mp/mee se descontarán)',
      'terminar_produccion': '✓ Terminar producción',
      'marcar_limpia': '✓ Marcar área como LIMPIA',
      'asignar_ia': '🤖 Que IA asigne área + operarios',
    };
    if(!confirm(labels[tipo]+'?')) return;
    var msg = document.getElementById('semana-msg');
    msg.style.display='block';
    msg.innerHTML = '⏳ Ejecutando...';
    try{
      // Mapear tipo a tipo del backend
      var tipoBack = tipo;
      if(tipo === 'iniciar') tipoBack = 'iniciar_produccion';
      if(tipo === 'terminar') tipoBack = 'terminar_produccion';
      var body = {tipo: tipoBack};
      if(tipoBack === 'marcar_limpia') body.limpieza_id = id;
      else body.produccion_id = id;
      var r = await fetch('/api/planta/accion-rapida', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body),
      });
      var d = await r.json();
      if(!r.ok || (d.ok === false && d.error)) throw new Error(d.error || 'HTTP '+r.status);
      msg.innerHTML = '✅ '+ (d.mensaje || 'OK');
      setTimeout(function(){ msg.style.display='none'; }, 3000);
      semanaRecargar();
      if(typeof salasVivoRecargar === 'function') salasVivoRecargar();
    }catch(e){
      msg.innerHTML = '❌ Error: '+(e.message||e);
    }
  }

  // ── Salud del sistema + Self-heal (Sebastián 1-may-2026)
  async function healthRecargar(){
    var sum_ = document.getElementById('health-summary');
    var grid = document.getElementById('health-grid');
    if(sum_) sum_.textContent = 'Cargando…';
    try{
      var r = await fetch('/api/planta/health-check', {credentials:'same-origin'});
      var d = await r.json();
      if(!r.ok) throw new Error(d.error || 'HTTP '+r.status);
      var k = d.kpis || {};
      var emoji = d.overall_status === 'ok' ? '✅' : (d.overall_status === 'warn' ? '⚠️' : '🚨');
      if(sum_) sum_.textContent = emoji+' '+(k.ok||0)+' OK · '+(k.warn||0)+' avisos · '+(k.error||0)+' errores';
      var items = d.items || [];
      grid.innerHTML = items.map(function(it){
        var col, ico;
        switch(it.status){
          case 'ok':    col='#10b981'; ico='✓'; break;
          case 'warn':  col='#fbbf24'; ico='⚠'; break;
          case 'error': col='#ef4444'; ico='✗'; break;
          default:      col='#94a3b8'; ico='?';
        }
        var html = '<div style="background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.15);border-left:3px solid '+col+';border-radius:5px;padding:6px 10px;font-size:11px">';
        html += '<div style="display:flex;justify-content:space-between;align-items:center"><b>'+ico+' '+esc(it.nombre)+'</b><span style="color:'+col+';font-weight:700">'+esc(it.valor||'')+'</span></div>';
        if(it.sugerencia) html += '<div style="font-size:10px;opacity:.7;margin-top:2px">→ '+esc(it.sugerencia)+'</div>';
        html += '</div>';
        return html;
      }).join('');
    }catch(e){
      if(sum_) sum_.textContent = 'Error: '+(e.message||e);
    }
  }
  async function selfHealEjecutar(){
    if(!confirm('Self-heal IA: habilitar cron · auto-asignar producciones pendientes · crear limpiezas faltantes · limpiar logs viejos.\n\n¿Continuar?')) return;
    var sum_ = document.getElementById('health-summary');
    if(sum_) sum_.textContent = '⏳ Ejecutando self-heal…';
    try{
      var r = await fetch('/api/planta/self-heal', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:'{}'});
      var d = await r.json();
      if(!r.ok || !d.ok) throw new Error(d.error || 'HTTP '+r.status);
      var msg = '✅ '+d.mensaje;
      if(d.acciones && d.acciones.length){
        msg += '\n\nAcciones:\n' + d.acciones.map(function(a){return '  • '+a;}).join('\n');
      }
      alert(msg);
      healthRecargar();
      if(typeof salasVivoRecargar === 'function') salasVivoRecargar();
    }catch(e){
      alert('❌ Error: '+(e.message||e));
    }
  }

  // ── Estado Salas en Vivo · IA auto-asigna áreas + operarios + limpieza
  async function salasVivoRecargar(){
    var sub = document.getElementById('salas-subtitle');
    var grid = document.getElementById('salas-grid');
    if(sub) sub.textContent = 'Cargando…';
    try{
      var r = await fetch('/api/planta/estado-salas-vivo', {credentials:'same-origin'});
      var d = await r.json();
      if(!r.ok) throw new Error(d.error || 'HTTP '+r.status);
      if(sub) sub.textContent = (d.libres||0)+' libres · '+(d.ocupadas||0)+' ocupadas · '+(d.sucias||0)+' sucias · '+(d.limpiando||0)+' limpiando';
      var salas = d.salas || [];
      grid.innerHTML = salas.map(function(s){
        var bg, border, ico, statusTxt;
        switch(s.estado){
          case 'ocupada': bg='#fef2f2'; border='#dc2626'; ico='🔴'; statusTxt='OCUPADA'; break;
          case 'sucia':   bg='#fef3c7'; border='#f59e0b'; ico='🟡'; statusTxt='SUCIA'; break;
          case 'limpiando': bg='#dbeafe'; border='#2563eb'; ico='🔵'; statusTxt='LIMPIANDO'; break;
          default:        bg='#f0fdf4'; border='#15803d'; ico='🟢'; statusTxt='LIBRE'; break;
        }
        var html = '<div style="background:'+bg+';border:2px solid '+border+';border-radius:8px;padding:10px;font-size:11px">';
        html += '<div style="display:flex;justify-content:space-between;align-items:center"><b style="color:#0f172a;font-size:13px">'+ico+' '+s.codigo+' · '+s.nombre.substring(0,18)+'</b><span style="background:'+border+';color:#fff;padding:2px 8px;border-radius:10px;font-size:9px;font-weight:700">'+statusTxt+'</span></div>';
        if(s.tanque_principal){
          html += '<div style="font-size:10px;color:#64748b;margin-top:4px">🛢 '+s.tanque_principal.codigo+' · '+s.tanque_principal.litros+'L</div>';
        }
        if(s.produccion){
          var p = s.produccion;
          html += '<div style="background:rgba(255,255,255,.5);border-radius:5px;padding:6px;margin-top:6px;font-size:10px">';
          html += '<b>'+p.producto.substring(0,28)+'</b> · '+p.kg+'kg<br>';
          html += '📅 '+p.fecha+' · '+p.lotes+' lote · '+(p.estado||'programado')+'<br>';
          if(p.op_dispensacion) html += '👤 disp: '+p.op_dispensacion+'<br>';
          if(p.op_elaboracion)  html += '👤 elab: '+p.op_elaboracion+'<br>';
          if(p.op_envasado)     html += '👤 env: '+p.op_envasado;
          html += '</div>';
        } else {
          html += '<div style="color:#94a3b8;font-style:italic;font-size:10px;margin-top:6px">Sin producción asignada</div>';
        }
        if(s.limpieza_pendiente){
          var l = s.limpieza_pendiente;
          html += '<div style="background:#fff;border:1px solid #f59e0b;border-radius:5px;padding:5px;margin-top:5px;font-size:10px;color:#92400e">';
          html += '🧹 Limpieza '+l.fecha.substring(0,10)+'<br>';
          html += '👤 '+(l.asignado_a||'sin asignar')+' · '+l.estado;
          html += '</div>';
        }
        if(s.requiere_limpieza_profunda && !s.ultima_limpieza_profunda){
          html += '<div style="font-size:9px;color:#92400e;margin-top:4px">⚠ Sin registro de limpieza profunda</div>';
        }
        html += '<button onclick="abrirRotulo('+s.id+')" style="margin-top:8px;width:100%;padding:6px;background:#7c3aed;color:#fff;border:none;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer">&#127991;&#65039; Rótulo de limpieza</button>';
        html += '</div>';
        return html;
      }).join('');
    }catch(e){
      if(sub) sub.textContent = 'Error: '+(e.message||e);
    }
  }
  // ── Rótulo de Limpieza virtual · PRD-PRO-002-F02 · Sebastián 6-jun-2026
  // Operario registra limpieza (sucia→en limpieza) · Calidad verifica con
  // e-firma (en limpieza→Limpio, vía despeje canónico). Fluye con producción.
  var _ROT = null;
  async function abrirRotulo(areaId){
    var m=document.getElementById('rotmodal');
    var body=document.getElementById('rot-body');
    if(m) m.style.display='flex';
    if(body) body.innerHTML='Cargando…';
    try{
      var r=await fetch('/api/planta/rotulo-limpieza/'+areaId,{credentials:'same-origin'});
      var d=await r.json();
      if(!r.ok) throw new Error(d.error||'HTTP '+r.status);
      d.area_id=areaId; _ROT=d; renderRotulo();
    }catch(e){ if(body) body.innerHTML='<div style="color:#dc2626">Error: '+escapeHtml(e.message||e)+'</div>'; }
  }
  function cerrarRotulo(){ var m=document.getElementById('rotmodal'); if(m) m.style.display='none'; _ROT=null; }
  function renderRotulo(){
    var d=_ROT; if(!d) return;
    var rot=d.rotulo, ciclo=d.ciclo||null;
    var cols={'Limpio':'#15803d','En uso':'#dc2626','Sucio':'#f59e0b','En limpieza':'#2563eb'};
    var col=cols[rot.estado]||'#64748b';
    var h='';
    h+='<div style="text-align:center;margin-bottom:14px"><span style="display:inline-block;padding:6px 18px;border-radius:20px;background:'+col+';color:#fff;font-weight:800;font-size:15px">'+escapeHtml(rot.estado)+'</span></div>';
    h+='<div style="font-size:13px;line-height:1.7">';
    h+='<div><b>Área:</b> '+escapeHtml(rot.area_nombre)+' · '+escapeHtml(rot.area_codigo)+'</div>';
    h+='<div><b>Producto a elaborar:</b> '+escapeHtml(rot.producto_elaborar||'—')+(rot.lote_elaborar?' · Lote '+escapeHtml(rot.lote_elaborar):'')+'</div>';
    h+='<div><b>Producto anterior:</b> '+escapeHtml(rot.producto_anterior||'—')+(rot.lote_anterior?' · Lote '+escapeHtml(rot.lote_anterior):'')+'</div>';
    if(ciclo){
      if(ciclo.realizado_por) h+='<div><b>Limpieza realizada por:</b> '+escapeHtml(ciclo.realizado_por)+' · '+escapeHtml(ciclo.realizado_at||'')+'</div>';
      if(ciclo.verificado_por) h+='<div><b>Verificado por (Calidad):</b> '+escapeHtml(ciclo.verificado_por)+' · '+escapeHtml(ciclo.verificado_at||'')+'</div>';
      if(ciclo.sanitizante && !d.puede_realizar) h+='<div><b>Sanitizante:</b> '+escapeHtml(ciclo.sanitizante)+'</div>';
    }
    h+='</div>';
    if(d.puede_realizar){
      h+='<div style="margin-top:14px;border-top:1px solid #e2e8f0;padding-top:12px">';
      h+='<div style="font-weight:700;font-size:12px;margin-bottom:6px">Registrar limpieza (operario)</div>';
      h+='<label style="font-size:12px">Sanitizante / detergente<br><select id="rot-sanit" style="width:100%;padding:6px;border:1px solid #cbd5e1;border-radius:5px;margin-bottom:8px">';
      (d.sanitizantes_sugeridos||['Alcohol 70%']).forEach(function(s){ h+='<option>'+escapeHtml(s)+'</option>'; });
      h+='</select></label>';
      if(rot.equipos && rot.equipos.length){
        h+='<div style="font-size:12px;font-weight:700;margin:4px 0">Equipos limpiados:</div><div style="max-height:130px;overflow:auto;border:1px solid #e2e8f0;border-radius:5px;padding:6px">';
        rot.equipos.forEach(function(eq){ h+='<label style="display:block;font-size:12px;margin:2px 0"><input type="checkbox" class="rot-eq" value="'+escapeHtml(eq.codigo)+'"> '+escapeHtml(eq.codigo)+' · '+escapeHtml(eq.nombre)+'</label>'; });
        h+='</div>';
      }
      h+='<button onclick="rotuloRealizar()" style="margin-top:10px;width:100%;padding:8px;background:#2563eb;color:#fff;border:none;border-radius:6px;font-weight:700;cursor:pointer">&#10003; Registrar limpieza</button>';
      h+='</div>';
    }
    if(d.puede_verificar){
      h+='<div style="margin-top:12px"><button onclick="rotuloVerificar()" style="width:100%;padding:8px;background:#15803d;color:#fff;border:none;border-radius:6px;font-weight:700;cursor:pointer">&#9989; Verificar y liberar (firma Calidad)</button></div>';
    }
    h+='<div style="margin-top:12px;text-align:center"><a href="/planta/rotulo-limpieza/'+d.area_id+'/pdf" target="_blank" style="color:#7c3aed;font-size:12px;font-weight:700;text-decoration:none">&#128424;&#65039; Imprimir rótulo F02</a></div>';
    var body=document.getElementById('rot-body'); if(body) body.innerHTML=h;
  }
  async function rotuloRealizar(){
    var d=_ROT; if(!d) return;
    var sanitEl=document.getElementById('rot-sanit');
    var sanit=sanitEl?sanitEl.value:'Alcohol 70%';
    var equipos=[];
    document.querySelectorAll('.rot-eq:checked').forEach(function(c){ equipos.push(c.value); });
    try{
      var r=await fetch('/api/planta/rotulo-limpieza/'+d.area_id+'/realizar',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({sanitizante:sanit,equipos:equipos})});
      var dd=await r.json();
      if(!r.ok||!dd.ok) throw new Error(dd.error||'HTTP '+r.status);
      abrirRotulo(d.area_id);
      if(typeof salasVivoRecargar==='function') salasVivoRecargar();
    }catch(e){ alert('❌ '+(e.message||e)); }
  }
  async function rotuloVerificar(){
    var d=_ROT; if(!d) return;
    var rid=d.ciclo?d.ciclo.id:null;
    if(!rid){ alert('No hay limpieza realizada para verificar'); return; }
    var pwd=prompt('FIRMA ELECTRÓNICA (21 CFR Part 11)\n\nContraseña para verificar la limpieza del área:');
    if(!pwd) return;
    var totp=prompt('Si tenés MFA activo, ingresá el código de 6 dígitos.\nSi no usás MFA, dejá vacío y presioná OK.')||'';
    try{
      var rc=await fetch('/api/sign/challenge',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pwd,totp_token:totp})});
      var dc=await rc.json(); if(!rc.ok) throw new Error(dc.error||'Credenciales inválidas');
      var rs=await fetch('/api/sign',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({record_table:'rotulos_limpieza',record_id:String(rid),meaning:'revisa',challenge_token:dc.token})});
      var ds=await rs.json(); if(!rs.ok) throw new Error(ds.error||'Error al firmar');
      var rv=await fetch('/api/planta/rotulo-limpieza/'+d.area_id+'/verificar',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({signature_id:ds.signature_id})});
      var dv=await rv.json(); if(!rv.ok||!dv.ok) throw new Error(dv.error||'HTTP '+rv.status);
      alert('✅ '+dv.mensaje); cerrarRotulo();
      if(typeof salasVivoRecargar==='function') salasVivoRecargar();
    }catch(e){ alert('❌ '+(e.message||e)); }
  }

  // Sub-pestaña "Rótulos de limpieza" (en Fabricación · bar-prodHub): lista
  // todas las salas con su estado y abre el rótulo de cada una.
  async function cargarRotulosLimp(){
    var box=document.getElementById('rotuloslimp-grid');
    if(!box) return;
    box.innerHTML='Cargando…';
    try{
      var r=await fetch('/api/planta/rotulos-limpieza',{credentials:'same-origin'});
      var d=await r.json();
      if(!r.ok) throw new Error(d.error||'HTTP '+r.status);
      var salas=d.areas||[];
      if(!salas.length){ box.innerHTML='<div style="color:#64748b">No hay áreas configuradas.</div>'; return; }
      var cols={'libre':['#15803d','🟢 LIMPIO'],'ocupada':['#dc2626','🔴 EN USO'],'sucia':['#f59e0b','🟡 SUCIO'],'limpiando':['#2563eb','🔵 EN LIMPIEZA']};
      box.innerHTML=salas.map(function(s){
        var c=cols[s.estado]||['#64748b',(s.estado||'').toUpperCase()];
        var h='<div style="border:2px solid '+c[0]+';border-radius:10px;padding:12px;background:#fff">';
        h+='<div style="display:flex;justify-content:space-between;align-items:center;gap:6px"><b style="font-size:13px">'+escapeHtml(s.nombre||s.codigo)+'</b><span style="background:'+c[0]+';color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;white-space:nowrap">'+c[1]+'</span></div>';
        if(s.producto) h+='<div style="font-size:11px;color:#64748b;margin-top:6px">🏭 '+escapeHtml(s.producto.substring(0,32))+'</div>';
        h+='<button onclick="planoImprimirRotulo('+s.id+')" style="margin-top:10px;width:100%;padding:9px;background:#0f766e;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">🖨️ Imprimir rótulo</button>';
        h+='<button onclick="abrirRotulo('+s.id+')" style="margin-top:6px;width:100%;padding:7px;background:#fff;color:#7c3aed;border:1px solid #7c3aed;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer">✍️ Registrar / verificar limpieza</button>';
        h+='</div>';
        return h;
      }).join('');
    }catch(e){ box.innerHTML='<div style="color:#dc2626">Error: '+escapeHtml(e.message||e)+'</div>'; }
  }

  async function autoAsignarPendientes(){
    if(!confirm('Auto-asignar área + operarios para producciones próximos 7 días sin asignar.\n\nLa IA elige tanque óptimo (más chico que aguante el lote) y rota operarios.\n\n¿Continuar?')) return;
    var sub = document.getElementById('salas-subtitle');
    if(sub) sub.textContent = '⏳ Auto-asignando…';
    try{
      var r = await fetch('/api/planta/auto-asignar-pendientes', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({dias: 7}),
      });
      var d = await r.json();
      if(!r.ok || !d.ok) throw new Error(d.error || 'HTTP '+r.status);
      alert('✅ '+d.mensaje + (d.procesadas.length ? '\n\n'+d.procesadas.slice(0,8).map(function(p){return '#'+p.id+' · '+p.cambios.join(' | ');}).join('\n') : ''));
      salasVivoRecargar();
    }catch(e){
      alert('❌ Error: '+(e.message||e));
    }
  }

  // ── Mi Día por Operario (Sebastián 1-may-2026)
  var _MI_DIA_OPERARIOS = [];
  async function miDiaCargarOperarios(){
    var sel = document.getElementById('midia-operario');
    var sub = document.getElementById('midia-subtitle');
    if(!sel) return;
    try{
      // list_only=1 fuerza que el endpoint devuelva la lista (no auto-resuelve usuario)
      var r = await fetch('/api/planta/mi-dia?list_only=1', {credentials:'same-origin'});
      var d = await r.json();
      if(!r.ok){
        if(sub) sub.textContent = '❌ Error cargando operarios: '+(d.error||'HTTP '+r.status);
        return;
      }
      var ops = d.operarios_disponibles || [];
      if(!ops.length){
        if(sub) sub.textContent = '⚠️ No hay operarios activos en operarios_planta · revisar config';
        sel.innerHTML = '<option value="">⚠️ Sin operarios activos</option>';
        return;
      }
      _MI_DIA_OPERARIOS = ops;
      sel.innerHTML = '<option value="">— elegir operario ('+ops.length+') —</option>' +
        ops.map(function(o){
          var label = _escHTML(o.nombre || o.codigo || ('op#'+o.id));
          if(o.es_jefe) label += ' [👨‍🏭 jefe]';
          else if(o.rol) label += ' ['+_escHTML(o.rol)+']';
          return '<option value="'+o.id+'">'+label+'</option>';
        }).join('');
      if(sub) sub.textContent = ops.length+' operarios disponibles · selecciona uno para ver sus tareas próximos 7 días';
    }catch(e){
      if(sub) sub.textContent = '❌ Error: '+(e.message||e);
    }
  }
  async function miDiaRecargar(){
    var opId = (document.getElementById('midia-operario')||{value:''}).value;
    var dias = (document.getElementById('midia-dias')||{value:'7'}).value;
    var sub = document.getElementById('midia-subtitle');
    var grid = document.getElementById('midia-grid');
    var resumen = document.getElementById('midia-resumen');
    if(!opId){
      // Si dropdown está vacío, recargar operarios
      if(!_MI_DIA_OPERARIOS.length) {
        await miDiaCargarOperarios();
      } else {
        if(sub) sub.textContent = 'Selecciona un operario para ver sus tareas';
      }
      if(grid) grid.innerHTML = '';
      if(resumen) resumen.innerHTML = '';
      return;
    }
    if(sub) sub.textContent = 'Cargando…';
    try{
      var r = await fetch('/api/planta/mi-dia?operario_id='+opId+'&dias='+dias, {credentials:'same-origin'});
      var d = await r.json();
      if(!r.ok) throw new Error(d.error || 'HTTP '+r.status);
      var op = d.operario || {};
      var rs = d.resumen || {};
      if(sub) sub.textContent = (op.nombre||'')+' · '+(rs.total_tareas||0)+' tareas en '+dias+'d · '+(rs.kg_total_semana||0)+'kg total';
      // Resumen
      if(resumen){
        resumen.innerHTML = '<div style="display:flex;gap:6px;flex-wrap:wrap;font-size:11px">'
          +'<span style="background:#dbeafe;color:#1e40af;padding:3px 10px;border-radius:12px"><b>'+(rs.total_tareas||0)+'</b> tareas</span>'
          +'<span style="background:#dcfce7;color:#15803d;padding:3px 10px;border-radius:12px"><b>'+(rs.kg_total_semana||0)+'kg</b> a producir</span>'
          +'<span style="background:#fef3c7;color:#92400e;padding:3px 10px;border-radius:12px"><b>'+(rs.dias_con_actividad||0)+'</b> días activos</span>'
          +'<span style="background:#f3f4f6;color:#475569;padding:3px 10px;border-radius:12px">Rol: '+(op.rol_predeterminado||'—')+'</span>'
          +'</div>';
      }
      // Cards por día
      var dias_arr = d.dias || [];
      grid.innerHTML = dias_arr.map(function(dia){
        var hoy = (dia.fecha === d.fecha_hoy);
        var bg = hoy ? '#fef3c7' : (dia.es_laboral ? '#fff' : '#f3f4f6');
        var border = hoy ? '#f59e0b' : (dia.tipo_dia === 'PRODUCCIÓN' ? '#1d4ed8' : (dia.tipo_dia === 'ACONDICIONAR/CONTEO' ? '#7c3aed' : '#94a3b8'));
        var icon = dia.tipo_dia === 'PRODUCCIÓN' ? '🔬' : (dia.tipo_dia === 'ACONDICIONAR/CONTEO' ? '📦' : '🏠');
        var html = '<div style="background:'+bg+';border:2px solid '+border+';border-radius:8px;padding:10px;font-size:11px;min-height:140px">';
        html += '<div style="font-weight:700;color:#0f172a;font-size:12px;display:flex;justify-content:space-between">'+icon+' '+dia.nombre_dia+' '+dia.fecha.substring(5);
        if(hoy) html += '<span style="background:#f59e0b;color:#fff;padding:1px 6px;border-radius:6px;font-size:9px">HOY</span>';
        html += '</div>';
        html += '<div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px">'+dia.tipo_dia+'</div>';
        if(dia.alerta_limpieza){
          html += '<div style="background:#fee2e2;border:1px solid #fca5a5;color:#991b1b;padding:4px 6px;border-radius:5px;font-size:10px;margin-bottom:5px">'+dia.alerta_limpieza+'</div>';
        }
        if(dia.producciones && dia.producciones.length){
          dia.producciones.forEach(function(p){
            var pigCol = p.pigmento ? '#dc2626' : '#1e40af';
            html += '<div style="background:#dbeafe;color:'+pigCol+';padding:4px 6px;border-radius:4px;margin-bottom:3px;font-size:10px"><b>'+p.producto.substring(0,22)+'</b> ('+p.rol+')<br>'+p.kg+'kg · '+(p.area||'')+(p.pigmento?' · 🎨 PIGMENTO':'')+'</div>';
          });
        }
        if(dia.limpiezas && dia.limpiezas.length){
          dia.limpiezas.forEach(function(l){
            html += '<div style="background:#fef3c7;color:#92400e;padding:4px 6px;border-radius:4px;margin-bottom:3px;font-size:10px">🧹 Limpieza '+l.area+(l.razon?' · '+l.razon.substring(0,20):'')+'</div>';
          });
        }
        if(dia.conteos && dia.conteos.length){
          dia.conteos.forEach(function(co){
            html += '<div style="background:#f3e8ff;color:#6b21a8;padding:4px 6px;border-radius:4px;margin-bottom:3px;font-size:10px">📦 '+(co.material||'').substring(0,20)+(co.abc?' ['+co.abc+']':'')+'</div>';
          });
        }
        if(!dia.producciones.length && !dia.limpiezas.length && !dia.conteos.length){
          html += '<div style="color:#94a3b8;font-style:italic;font-size:10px;margin-top:8px">Sin tareas asignadas</div>';
        }
        html += '</div>';
        return html;
      }).join('');
    }catch(e){
      if(sub) sub.textContent = 'Error: '+(e.message||e);
    }
  }

  // ── Cron status interno
  async function cronStatusRecargar(){
    var box = document.getElementById('cron-status-list');
    if(!box) return;
    box.innerHTML = '<div style="font-size:10px;opacity:.6">Cargando…</div>';
    try{
      var r = await fetch('/api/planta/cron-jobs-status', {credentials:'same-origin'});
      var d = await r.json();
      if(!r.ok) throw new Error(d.error || 'HTTP '+r.status);
      box.innerHTML = (d.jobs || []).map(function(j){
        var statusCol = j.ultima_ejecucion_at ? (j.ultima_ok ? '#10b981' : '#ef4444') : '#64748b';
        var statusTxt = j.ultima_ejecucion_at ? (j.ultima_ok ? 'OK' : 'FAIL') : 'pendiente';
        var ult = j.ultima_ejecucion_at ? j.ultima_ejecucion_at.substring(5,16) : 'nunca';
        return '<div style="background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.15);border-radius:6px;padding:6px 10px">'
          +'<div style="display:flex;justify-content:space-between;align-items:center;font-size:11px">'
          +'<b>'+j.job_name+'</b>'
          +'<span style="background:'+statusCol+';color:#fff;padding:1px 6px;border-radius:8px;font-size:9px">'+statusTxt+'</span>'
          +'</div>'
          +'<div style="font-size:9px;opacity:.65;margin-top:2px">📅 '+j.schedule+'</div>'
          +'<div style="font-size:9px;opacity:.7;margin-top:1px">⏱ Última: '+ult+'</div>'
          +(j.ultima_error ? '<div style="font-size:9px;color:#fca5a5;margin-top:1px">⚠ '+j.ultima_error.substring(0,40)+'</div>' : '')
          +'</div>';
      }).join('');
    }catch(e){
      box.innerHTML = '<div style="font-size:10px;color:#fca5a5">Error: '+(e.message||e)+'</div>';
    }
  }

  // ── Reporte Ejecutivo Auto-SC IA (Sebastián 1-may-2026)
  async function reporteEjecutivoRecargar(){
    var grid = document.getElementById('reporte-grid');
    var detalle = document.getElementById('reporte-detalle');
    if(!grid) return;
    grid.innerHTML = '<div style="color:#94a3b8;font-size:11px">Cargando…</div>';
    try{
      var r = await fetch('/api/planta/reporte-ejecutivo', {credentials:'same-origin'});
      var d = await r.json();
      if(!r.ok) throw new Error(d.error || 'HTTP '+r.status);
      function tile(label, val, sub, color){
        return '<div style="background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);border-radius:8px;padding:10px 12px">'
          +'<div style="font-size:9px;text-transform:uppercase;letter-spacing:.4px;opacity:.75">'+label+'</div>'
          +'<div style="font-size:20px;font-weight:800;color:'+(color||'#fff')+';margin-top:2px">'+val+'</div>'
          +(sub?'<div style="font-size:10px;opacity:.7;margin-top:2px">'+sub+'</div>':'')
        +'</div>';
      }
      var s = d.scs || {};
      var a = d.aprendizaje || {};
      var m = d.mee_config || {};
      var v = d.ventanas || {};
      grid.innerHTML = ''
        + tile('SCs IA · 30d', s.ia_30d || 0, (s.pct_automatizacion_30d||0)+'% del total', '#22d3ee')
        + tile('SCs IA · 90d', s.ia_90d || 0, 'cumulado trimestre', '#22d3ee')
        + tile('Cobertura SKUs', (a.pct_cobertura_skus||0)+'%', (a.skus_mapeados||0)+' de '+(a.skus_activos||0)+' SKUs', '#a3e635')
        + tile('Mappings aprendidos', a.mappings_aprendidos||0, 'de '+(a.mappings_totales||0)+' totales', '#a3e635')
        + tile('MEE configurados', (m.con_proveedor||0)+'/'+(m.aplica||0), (m.pct_completos||0)+'% con precio', '#fbbf24')
        + tile('Items POR-ASIGNAR', d.items_por_asignar||0, 'pendientes Catalina', d.items_por_asignar > 0 ? '#fbbf24' : '#a3e635');
      var html = '<b>📅 Próximas ventanas:</b> '
        +'mensual '+v.proxima_ventana_mensual+' · lunes '+v.proximo_lunes
        +' · D-20 desde '+v.ventana_d20_min+' hasta '+v.ventana_d20_max;
      if(d.top_proveedores && d.top_proveedores.length){
        html += '<br><br><b>🏭 Top SCs por proveedor (90d):</b><br>'
          + d.top_proveedores.slice(0,5).map(function(p){
            return '  • '+(p.observacion||'').substring(0,50)+' · '+p.scs+' SCs · $'+(p.valor_total||0).toLocaleString();
          }).join('<br>');
      }
      if(detalle) detalle.innerHTML = html;
    }catch(e){
      grid.innerHTML = '<div style="color:#fca5a5;font-size:11px">Error: '+(e.message||e)+'</div>';
    }
  }

  // ── Re-asigna IA a producciones con conflictos/duplicados (Sebastián 1-may-2026)
  async function reasignarConflictos(){
    if(!confirm('🔧 Resolver conflictos de operarios?\n\n• Detecta producciones con duplicados (mismo op en 2+ roles)\n• NULL todos los operarios de esas filas\n• IA reasigna 4 operarios DISTINTOS por producción\n\nAfecta próximos 14 días. ¿Continuar?')) return;
    var msg = document.getElementById('prep-msg');
    if(msg){
      msg.style.display='block';
      msg.style.background='#fef3c7';
      msg.style.color='#78350f';
      msg.innerHTML='⏳ Reasignando IA...';
    }
    try{
      var r = await fetch('/api/planta/reasignar-operarios-conflictos', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'}, body:'{}'
      });
      var d = await r.json();
      if(!r.ok || !d.ok) throw new Error(d.error || 'HTTP '+r.status);
      if(msg){
        msg.style.background='#dcfce7';
        msg.style.color='#166534';
        msg.innerHTML='✅ '+d.mensaje + (d.errores && d.errores.length ? '<br>⚠️ '+d.errores.length+' errores: '+d.errores.slice(0,3).map(_escHTML).join('; ') : '');
      }
      setTimeout(function(){ if(msg) msg.style.display='none'; }, 6000);
      preProduccionRecargar();
      if(typeof semanaRecargar === 'function') semanaRecargar();
    }catch(e){
      if(msg){
        msg.style.background='#fef2f2';
        msg.style.color='#991b1b';
        msg.innerHTML='❌ Error: '+(e.message||e);
      }
    }
  }

  // ── Pre-producción · Acomodo del equipo
  async function preProduccionRecargar(){
    var sub = document.getElementById('prep-subtitle');
    var kpisEl = document.getElementById('prep-kpis');
    var prodsEl = document.getElementById('prep-producciones');
    var conflEl = document.getElementById('prep-conflictos');
    var cargaEl = document.getElementById('prep-carga-operarios');
    if(sub) sub.textContent = 'Cargando…';
    var dias = (document.getElementById('prep-dias')||{value:'7'}).value;
    try{
      var r = await fetch('/api/planta/pre-produccion-equipo?dias='+dias, {credentials:'same-origin'});
      var d = await r.json();
      if(!r.ok) throw new Error(d.error || 'HTTP '+r.status);
      var k = d.kpis || {};
      if(sub) sub.textContent = (k.total||0)+' producciones próximos '+dias+' días · '+(k.listas||0)+' listas · '+(k.con_pendientes||0)+' con pendientes';
      // KPIs tiles
      function tile(label, val, color){
        return '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:7px;padding:8px 10px">'
          +'<div style="font-size:9px;color:#64748b;text-transform:uppercase">'+label+'</div>'
          +'<div style="font-size:18px;font-weight:800;color:'+(color||'#0f172a')+'">'+val+'</div>'
        +'</div>';
      }
      kpisEl.innerHTML = ''
        + tile('Total', k.total||0)
        + tile('Listas', k.listas||0, '#15803d')
        + tile('Con pendientes', k.con_pendientes||0, k.con_pendientes ? '#dc2626' : '#15803d')
        + tile('Sin operario', k.sin_operarios_asignados||0, k.sin_operarios_asignados ? '#dc2626' : '#15803d')
        + tile('Conflictos', k.conflictos_operario||0, k.conflictos_operario ? '#dc2626' : '#15803d')
        + tile('Duplicados intra', k.duplicados_intra_produccion||0, k.duplicados_intra_produccion ? '#fbbf24' : '#15803d');

      // Conflictos REALES (operario en 2+ producciones DISTINTAS mismo día)
      var conflictos = d.conflictos || [];
      // Duplicados INTRA-producción (mismo op en varios roles de la misma prod) → bug
      var dupes = d.duplicados_intra_produccion || [];
      conflEl.innerHTML = '';
      if(conflictos.length){
        conflEl.innerHTML += '<div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:6px;padding:8px 10px;font-size:11px;margin-bottom:6px">'
          +'<b style="color:#991b1b">⚠️ '+conflictos.length+' conflicto(s) cross-producción</b> · mismo operario en 2+ producciones distintas el mismo día:'
          +'<ul style="margin:4px 0 0 18px;padding:0;color:#7f1d1d">'
          + conflictos.map(function(c){
            var prods_set = {};
            (c.producciones||[]).forEach(function(p){ prods_set[p.producto]=1; });
            return '<li>'+_escHTML(c.operario_nombre)+' · '+c.fecha+' · '+(c.producciones_distintas||0)+' producciones: '
              + Object.keys(prods_set).map(_escHTML).join(', ')+'</li>';
          }).join('')
          +'</ul></div>';
      }
      if(dupes.length){
        conflEl.innerHTML += '<div style="background:#fef3c7;border:1px solid #fbbf24;border-radius:6px;padding:8px 10px;font-size:11px">'
          +'<b style="color:#78350f">🔧 '+dupes.length+' producción(es) con operario duplicado en varios roles</b> · click "🔧 Resolver conflictos" arriba para reasignar:'
          +'<ul style="margin:4px 0 0 18px;padding:0;color:#78350f">'
          + dupes.slice(0,8).map(function(d){
            return '<li>'+_escHTML(d.producto.substring(0,40))+' · '+d.fecha+' · op#'+d.operario_id+' en '+(d.roles||[]).map(function(r){return r.replace('op_','');}).join('+')+'</li>';
          }).join('')
          + (dupes.length > 8 ? '<li>...y '+(dupes.length-8)+' más</li>' : '')
          +'</ul></div>';
      }

      // Producciones cards
      var prods = d.producciones || [];
      if(!prods.length){
        prodsEl.innerHTML = '<div style="text-align:center;padding:20px;color:#94a3b8;font-size:11px;font-style:italic">Sin producciones programadas en próximos '+dias+' días</div>';
      } else {
        prodsEl.innerHTML = prods.map(function(p){
          var border = p.listo_para_producir ? '#15803d' : (p.dias_hasta <= 2 ? '#dc2626' : '#fbbf24');
          var bg = p.listo_para_producir ? '#f0fdf4' : (p.dias_hasta <= 2 ? '#fef2f2' : '#fefce8');
          var statusIcon = p.listo_para_producir ? '✅' : '⏳';
          var statusTxt = p.listo_para_producir ? 'LISTA' : 'pendiente';
          return '<div style="background:'+bg+';border-left:4px solid '+border+';padding:10px 12px;border-radius:6px;font-size:11px">'
            +'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px">'
            +'<div><b style="color:#0f172a">'+statusIcon+' '+_escHTML(p.producto.substring(0,40))+'</b>'
            +' · D-'+p.dias_hasta+' · '+p.fecha.substring(0,10)+' · '+p.cantidad_kg+'kg ('+p.lotes+' lote)'
            +(p.area ? ' · 🏭 '+p.area : '')
            +'</div>'
            +'<span style="background:'+border+';color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700">'+statusTxt+'</span>'
            +'</div>'
            +'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:6px;margin-top:6px;font-size:10px">'
            +'<div>👤 <b>Elaboración:</b> '+(p.op_elaboracion || '<span style="color:#dc2626">SIN ASIGNAR</span>')+'</div>'
            +'<div>📦 <b>Envasado:</b> '+(p.op_envasado || '<span style="color:#dc2626">SIN ASIGNAR</span>')+'</div>'
            +'<div>🏷️ <b>Acondicionar:</b> '+(p.op_acondicionamiento || '<span style="color:#94a3b8">—</span>')+'</div>'
            +'<div>🧪 <b>MPs:</b> '+(p.mp_ok||0)+' OK · '+(p.mp_pendientes||0)+' pend</div>'
            +'<div>📦 <b>MEEs:</b> '+(p.mee_ok||0)+' OK · '+(p.mee_pendientes||0)+' pend</div>'
            +'</div>'
            +'</div>';
        }).join('');
      }

      // Carga por operario
      var carga = d.carga_operarios || [];
      if(carga.length){
        var rolIconMap = {elaboracion:'👤', envasado:'📦', acondicionamiento:'🏷️', dispensacion:'⚖️'};
        var rolLabelMap = {elaboracion:'Elab', envasado:'Env', acondicionamiento:'Acond', dispensacion:'Disp'};
        cargaEl.innerHTML = '<h4 style="margin:0 0 6px;color:#0f172a;font-size:12px">📊 Carga semanal por operario</h4>'
          +'<div style="display:flex;flex-wrap:wrap;gap:6px">'
          + carga.map(function(c){
            var color = c.producciones >= 5 ? '#dc2626' : (c.producciones >= 3 ? '#fbbf24' : '#15803d');
            var roles = (c.roles||[]).map(function(r){
              return (rolIconMap[r]||'')+' '+(rolLabelMap[r]||r);
            }).join(' · ');
            var kg = (c.kg_total||0).toLocaleString('es-CO');
            return '<div style="background:'+color+';color:#fff;padding:6px 12px;border-radius:14px;font-size:11px;font-weight:600;line-height:1.4">'
              +'<div>'+_escHTML(c.nombre)+' · '+c.producciones+' producciones · '+kg+' kg</div>'
              +(roles ? '<div style="font-weight:500;opacity:.92;font-size:10px;margin-top:2px">'+roles+'</div>' : '')
              +'</div>';
          }).join('')
          +'</div>';
      } else {
        cargaEl.innerHTML = '';
      }
    }catch(e){
      if(sub) sub.textContent = 'Error: '+(e.message||e);
    }
  }

  // ── Diagnosticar Calendar (Sebastián 1-may-2026, modal + nuevo shape)
  async function diagnosticarCalendar(){
    // Crear modal flotante con resultado bonito
    var prev = document.getElementById('diag-cal-modal');
    if(prev) prev.remove();
    var modal = document.createElement('div');
    modal.id = 'diag-cal-modal';
    modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.7);z-index:10000;display:flex;align-items:center;justify-content:center;padding:20px';
    modal.innerHTML = '<div style="background:#fff;border-radius:12px;max-width:700px;width:100%;max-height:90vh;overflow-y:auto;padding:20px;box-shadow:0 10px 40px rgba(0,0,0,.3)">'
      +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">'
      +'<h3 style="margin:0;color:#0f172a">🔧 Diagnóstico Google Calendar</h3>'
      +'<button onclick="document.getElementById(\'diag-cal-modal\').remove()" style="background:#f1f5f9;border:none;width:32px;height:32px;border-radius:50%;cursor:pointer;font-size:18px">×</button>'
      +'</div>'
      +'<div id="diag-cal-body" style="font-size:12px;color:#334155">⏳ Diagnosticando…</div>'
      +'</div>';
    document.body.appendChild(modal);
    var body = document.getElementById('diag-cal-body');

    try{
      var r = await fetch('/api/planta/diagnostico-calendar', {credentials:'same-origin'});
      var d = await r.json();
      if(!r.ok) throw new Error(d.error || 'HTTP '+r.status);

      var env = d.env_vars || {};
      var fetch_ = d.fetch || {};
      var ut = d.url_test || null;
      var html = '';

      // Sección 1: Variables de entorno
      html += '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px;margin-bottom:10px">';
      html += '<b style="color:#0f172a">🔑 Variables de entorno (Render)</b>';
      html += '<table style="width:100%;font-size:11px;margin-top:6px"><tr><td><b>GCAL_ICAL_URL</b></td><td style="text-align:right">'+(env.GCAL_ICAL_URL_configurado ? '<span style="color:#15803d">✓ configurada</span>' : '<span style="color:#dc2626">✗ NO configurada</span>')+'</td></tr>';
      if(env.GCAL_ICAL_URL_preview && env.GCAL_ICAL_URL_configurado){
        html += '<tr><td colspan="2"><code style="font-size:10px;color:#64748b;word-break:break-all">'+esc(env.GCAL_ICAL_URL_preview)+'</code></td></tr>';
      }
      html += '<tr><td><b>GOOGLE_API_KEY</b></td><td style="text-align:right">'+(env.GOOGLE_API_KEY_configurado ? '<span style="color:#15803d">✓ configurada</span>' : '<span style="color:#94a3b8">— no configurada (opcional)</span>')+'</td></tr>';
      html += '<tr><td><b>CALENDAR_ID</b></td><td style="text-align:right"><code style="font-size:10px">'+esc(env.CALENDAR_ID || '(no definido)')+'</code></td></tr></table>';
      html += '</div>';

      // Sección 2: Fetch en vivo
      var srcCol = fetch_.source === 'ical' ? '#15803d' : (fetch_.source === 'gcal_api' ? '#15803d' : (fetch_.source === 'fail' ? '#dc2626' : '#f59e0b'));
      html += '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px;margin-bottom:10px">';
      html += '<b style="color:#0f172a">📡 Fetch en vivo</b>';
      html += '<table style="width:100%;font-size:11px;margin-top:6px"><tr><td><b>Source</b></td><td style="text-align:right;color:'+srcCol+';font-weight:700">'+esc(fetch_.source || '?')+'</td></tr>';
      html += '<tr><td><b>Eventos en próximos 60d</b></td><td style="text-align:right;font-size:14px;font-weight:800;color:'+(fetch_.total_eventos_60d > 0 ? '#15803d' : '#dc2626')+'">'+(fetch_.total_eventos_60d || 0)+'</td></tr>';
      html += '<tr><td><b>Duración fetch</b></td><td style="text-align:right">'+(fetch_.duracion_ms || 0)+' ms</td></tr>';
      if(fetch_.error){
        html += '<tr><td colspan="2" style="color:#dc2626;font-size:10px">⚠ '+esc(fetch_.error)+'</td></tr>';
      }
      html += '</table></div>';

      // Sección 3: Test directo URL (si aplica)
      if(ut){
        html += '<div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:8px;padding:12px;margin-bottom:10px">';
        html += '<b style="color:#92400e">🧪 Test directo de URL</b>';
        html += '<table style="width:100%;font-size:11px;margin-top:6px">';
        if(ut.error){
          html += '<tr><td colspan="2" style="color:#dc2626">⚠ '+esc(ut.error)+'</td></tr>';
        } else {
          html += '<tr><td><b>Status HTTP</b></td><td style="text-align:right">'+(ut.status||0)+'</td></tr>';
          html += '<tr><td><b>Content-Type</b></td><td style="text-align:right;font-size:10px"><code>'+esc(ut.content_type||'')+'</code></td></tr>';
          html += '<tr><td><b>Tamaño feed</b></td><td style="text-align:right">'+((ut.size_bytes||0)/1024).toFixed(1)+' KB</td></tr>';
          html += '<tr><td><b>iCal válido</b></td><td style="text-align:right">'+(ut.es_ical_valido ? '<span style="color:#15803d">✓ sí</span>' : '<span style="color:#dc2626">✗ no</span>')+'</td></tr>';
          html += '<tr><td><b>Eventos VEVENT</b></td><td style="text-align:right;font-weight:700">'+(ut.cantidad_VEVENT || 0)+'</td></tr>';
        }
        html += '</table></div>';
      }

      // Sección 4: Sample eventos
      if(d.eventos_sample && d.eventos_sample.length){
        html += '<div style="background:#dbeafe;border:1px solid #93c5fd;border-radius:8px;padding:12px;margin-bottom:10px">';
        html += '<b style="color:#1e40af">📅 Próximos eventos (sample 10)</b>';
        html += '<ul style="margin:6px 0 0 18px;padding:0;font-size:11px">';
        d.eventos_sample.forEach(function(e){
          html += '<li><b>'+esc(e.fecha||'')+'</b> · '+esc(e.titulo||'(sin título)')+'</li>';
        });
        html += '</ul></div>';
      }

      // Sección 5: Test matching producto-evento
      if(d.matching_test && d.matching_test.length){
        html += '<div style="background:#f3e8ff;border:1px solid #d8b4fe;border-radius:8px;padding:12px;margin-bottom:10px">';
        html += '<b style="color:#6b21a8">🎯 Test matching producto ↔ evento</b>';
        html += '<div style="font-size:11px;margin-top:6px">';
        d.matching_test.forEach(function(t){
          html += '<div style="margin-bottom:6px"><b>'+esc(t.producto)+'</b>';
          if(t.alias && t.alias !== '(ninguno)') html += ' <span style="color:#64748b">(alias: '+esc(t.alias)+')</span>';
          html += ':<br>';
          if(t.top_matches && t.top_matches.length){
            t.top_matches.forEach(function(m){
              var col = m.score >= 60 ? '#15803d' : '#f59e0b';
              html += '&nbsp;&nbsp;→ <span style="color:'+col+'">score '+m.score+'</span> · '+esc(m.evento)+' ('+esc(m.fecha)+')<br>';
            });
          } else {
            html += '&nbsp;&nbsp;<span style="color:#dc2626">— sin match en eventos disponibles</span><br>';
          }
          html += '</div>';
        });
        html += '</div></div>';
      }

      // Sección 6: Sugerencias
      if(d.sugerencias && d.sugerencias.length){
        html += '<div style="background:#ecfdf5;border:2px solid #6ee7b7;border-radius:8px;padding:12px">';
        html += '<b style="color:#065f46">💡 Recomendación</b>';
        html += '<ul style="margin:6px 0 0 18px;padding:0;font-size:11px">';
        d.sugerencias.forEach(function(s){
          html += '<li style="margin-bottom:4px">'+esc(s)+'</li>';
        });
        html += '</ul></div>';
      }

      body.innerHTML = html;
    }catch(e){
      body.innerHTML = '<div style="color:#dc2626">❌ Error: '+esc(e.message||String(e))+'</div>';
    }
  }

  // ── Normalizar MEE: backfill proveedor + auto-mapping fuzzy
  async function meeNormalizar(){
    var msg = document.getElementById('autosc-mee-msg');
    msg.style.display='block';
    msg.innerHTML = '⏳ Calculando propuestas de normalización…';
    try{
      // Paso 1: dry_run para mostrar propuestas
      var r = await fetch('/api/planta/normalizar-mee', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({dry_run: true, umbral_score: 40}),
      });
      var d = await r.json();
      if(!r.ok) throw new Error(d.error || 'HTTP '+r.status);
      var bf = d.backfill_proveedor || {};
      var am = d.auto_mapping || {};
      var nBf = (bf.cambios||[]).length;
      var nMap = (am.sugerencias||[]).length;
      if(nBf === 0 && nMap === 0){
        msg.innerHTML = '✅ Nada que normalizar · todos los MEE ya tienen proveedor y los SKUs ya están mapeados.';
        return;
      }
      // Mostrar resumen + sample
      var samplesMap = (am.sugerencias||[]).slice(0,8).map(function(s){
        return '<li>'+s.sku_codigo.substring(0,30)+' → <code>'+s.mee_codigo+'</code> ('+s.componente_tipo+', score '+s.score+')</li>';
      }).join('');
      var html = '<b>📋 Propuestas de normalización</b><br>';
      html += '<div style="margin-top:6px">📦 Backfill proveedor: <b>'+nBf+'</b> MEE</div>';
      html += '<div>🪄 Auto-mapping fuzzy SKU→etiqueta/serigrafía: <b>'+nMap+'</b> mappings</div>';
      if(samplesMap) html += '<ul style="margin:6px 0 0 18px;font-size:10px">'+samplesMap + (nMap>8?'<li>+ '+(nMap-8)+' más</li>':'')+'</ul>';
      html += '<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">';
      html += '<button onclick="meeNormalizarAplicar()" style="padding:5px 12px;background:#10b981;color:#fff;border:none;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer">✅ Aplicar todos</button>';
      html += '<button onclick="document.getElementById(\'autosc-mee-msg\').style.display=\'none\'" style="padding:5px 12px;background:#64748b;color:#fff;border:none;border-radius:5px;font-size:11px;cursor:pointer">Cancelar</button>';
      html += '</div>';
      msg.innerHTML = html;
    }catch(e){
      msg.innerHTML = '❌ Error normalizando: '+(e.message||e);
    }
  }
  async function meeNormalizarAplicar(){
    var msg = document.getElementById('autosc-mee-msg');
    msg.innerHTML = '⏳ Aplicando normalización…';
    try{
      var r = await fetch('/api/planta/normalizar-mee', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({dry_run: false, umbral_score: 40}),
      });
      var d = await r.json();
      if(!r.ok) throw new Error(d.error || 'HTTP '+r.status);
      var bf = d.backfill_proveedor || {};
      var am = d.auto_mapping || {};
      msg.innerHTML = '✅ ' + d.mensaje + '<br><div style="font-size:10px;margin-top:4px;opacity:.85">Refresca el panel para ver los datos actualizados.</div>';
      autoscMeeRecargar();
    }catch(e){
      msg.innerHTML = '❌ Error aplicando: '+(e.message||e);
    }
  }

  // ── Items POR-ASIGNAR (Catalina) — Sebastián 1-may-2026
  var _MEE_ASIGNAR_DATA = {items: [], maestro_mee: [], proveedores: []};
  function meeAsignarToggle(){
    var p = document.getElementById('mee-asignar-panel');
    if(!p) return;
    if(p.style.display === 'none'){
      p.style.display = 'block';
      meeAsignarRecargar();
    } else {
      p.style.display = 'none';
    }
  }
  async function meeAsignarRecargar(){
    var status = document.getElementById('mee-asignar-status');
    if(status) status.textContent = 'Cargando…';
    try{
      var r = await fetch('/api/planta/items-por-asignar', {credentials:'same-origin'});
      var d = await r.json();
      if(!r.ok) throw new Error(d.error || 'HTTP '+r.status);
      _MEE_ASIGNAR_DATA = d;
      var btnCount = document.getElementById('btn-asignar-count');
      if(btnCount) btnCount.textContent = d.total || 0;
      var countSpan = document.getElementById('mee-asignar-count');
      if(countSpan) countSpan.textContent = (d.total || 0) + ' items pendientes';
      meeAsignarRender();
    }catch(e){
      if(status) status.textContent = 'Error: '+(e.message||e);
    }
  }
  function meeAsignarRender(){
    var tb = document.getElementById('mee-asignar-tbody');
    var empty = document.getElementById('mee-asignar-empty');
    if(!tb) return;
    var items = _MEE_ASIGNAR_DATA.items || [];
    if(!items.length){
      tb.innerHTML = '';
      if(empty) empty.style.display = 'block';
      return;
    }
    if(empty) empty.style.display = 'none';
    var mees = _MEE_ASIGNAR_DATA.maestro_mee || [];
    var provs = _MEE_ASIGNAR_DATA.proveedores || [];
    // Inferir tipo del nombre para filtrar dropdown
    function tipoComponente(nombre){
      var n = (nombre || '').toLowerCase();
      if(n.indexOf('envase') >= 0) return 'envase';
      if(n.indexOf('tapa') >= 0) return 'tapa';
      if(n.indexOf('etiqueta') >= 0) return 'etiqueta';
      if(n.indexOf('serigraf') >= 0) return 'serigrafia';
      if(n.indexOf('tampograf') >= 0) return 'tampografia';
      if(n.indexOf('caja') >= 0) return 'caja';
      return 'otro';
    }
    function categoriaCompatible(tipo){
      // map tipo componente → categoría maestro_mee
      if(tipo === 'envase') return ['Envase','Frasco'];
      if(tipo === 'tapa') return ['Tapa','Gotero'];
      if(tipo === 'etiqueta') return ['Etiqueta'];
      if(tipo === 'serigrafia') return ['Serigrafia'];
      if(tipo === 'tampografia') return ['Serigrafia','Tampografia'];
      if(tipo === 'caja') return ['Plegable','Contorno'];
      return [];
    }
    tb.innerHTML = items.map(function(it){
      var tipo = tipoComponente(it.nombre_mp);
      var cats = categoriaCompatible(tipo);
      var meesFiltrados = cats.length ? mees.filter(function(m){return cats.indexOf(m.categoria) >= 0;}) : mees;
      var optsMee = '<option value="">— seleccionar código MEE —</option>' +
        meesFiltrados.map(function(m){
          return '<option value="'+m.codigo+'">'+m.codigo+' · '+(m.descripcion||'').substring(0,40)+' (stock '+m.stock+')</option>';
        }).join('');
      var optsProv = '<option value="">— proveedor —</option>' +
        provs.map(function(p){return '<option value="'+esc(p)+'">'+esc(p)+'</option>';}).join('');
      return '<tr data-id="'+it.id+'" style="border-bottom:1px solid #e2e8f0">' +
        '<td style="padding:5px;font-family:monospace;font-size:10px">'+it.numero+'</td>' +
        '<td style="padding:5px"><div style="font-size:10px;color:#5b21b6;font-weight:700">'+esc(it.nombre_mp).substring(0,60)+'</div><div style="font-size:9px;color:#94a3b8">tipo: '+tipo+'</div></td>' +
        '<td style="padding:5px;text-align:right;font-family:monospace">'+(Math.round(it.cantidad_g||0)).toLocaleString()+' '+(it.unidad||'und')+'</td>' +
        '<td style="padding:3px"><select id="mee-cod-'+it.id+'" style="width:100%;padding:3px;border:1px solid #cbd5e1;border-radius:3px;font-size:10px">'+optsMee+'</select></td>' +
        '<td style="padding:3px"><input id="mee-prov-'+it.id+'" list="dl-prov-'+it.id+'" placeholder="proveedor..." style="width:120px;padding:3px;border:1px solid #cbd5e1;border-radius:3px;font-size:10px"><datalist id="dl-prov-'+it.id+'">'+optsProv+'</datalist></td>' +
        '<td style="padding:3px;text-align:center"><button onclick="meeAsignarItem('+it.id+',\''+tipo+'\')" style="padding:4px 10px;background:#10b981;color:#fff;border:none;border-radius:5px;font-size:10px;font-weight:700;cursor:pointer">Asignar</button></td>' +
      '</tr>';
    }).join('');
  }
  function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
  async function meeAsignarItem(itemId, tipo){
    var meeSel = document.getElementById('mee-cod-'+itemId);
    var provInput = document.getElementById('mee-prov-'+itemId);
    var meeCod = (meeSel||{value:''}).value;
    var prov = (provInput||{value:''}).value.trim();
    if(!meeCod){
      alert('Debes seleccionar un código MEE'); return;
    }
    var status = document.getElementById('mee-asignar-status');
    if(status) status.textContent = '⏳ Asignando '+meeCod+'…';
    try{
      var r = await fetch('/api/planta/sc-mee-asignar', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          sc_item_id: itemId,
          mee_codigo: meeCod,
          proveedor: prov,
          componente_tipo: tipo,
        }),
      });
      var d = await r.json();
      if(!r.ok || !d.ok) throw new Error(d.error || 'HTTP '+r.status);
      if(status) status.textContent = '✅ '+d.mensaje;
      // remover fila visualmente
      var tr = document.querySelector('tr[data-id="'+itemId+'"]');
      if(tr) tr.style.opacity = '0.4';
      setTimeout(meeAsignarRecargar, 600);
    }catch(e){
      if(status) status.textContent = '❌ Error: '+(e.message||e);
    }
  }

  // ── Config MEE (proveedor + MOQ + origen + flags)
  var _meeConfigData = [];
  function meeConfigToggle(){
    var panel = document.getElementById('mee-config-panel');
    if(!panel) return;
    if(panel.style.display === 'none'){
      panel.style.display = 'block';
      meeConfigRecargar();
    } else {
      panel.style.display = 'none';
    }
  }
  async function meeConfigRecargar(){
    var status = document.getElementById('mee-config-status');
    if(status) status.textContent = 'Cargando…';
    try{
      var r = await fetch('/api/planta/mee-config', {credentials:'same-origin'});
      var d = await r.json();
      _meeConfigData = d.mees || [];
      if(status) status.textContent = _meeConfigData.length + ' MEEs · click en cualquier celda para editar';
      meeConfigRender();
    }catch(e){
      if(status) status.textContent = 'Error: '+(e.message||e);
    }
  }
  function meeConfigRender(){
    var tb = document.getElementById('mee-config-tbody');
    if(!tb) return;
    var filtro = ((document.getElementById('mee-config-filter')||{value:''}).value||'').toLowerCase();
    var cat = (document.getElementById('mee-config-categoria')||{value:''}).value || '';
    var rows = _meeConfigData.filter(function(m){
      if(cat && m.categoria !== cat) return false;
      if(!filtro) return true;
      var s = (m.codigo+' '+m.descripcion+' '+(m.proveedor_principal||'')+' '+(m.notas||'')).toLowerCase();
      return s.indexOf(filtro) >= 0;
    });
    if(!rows.length){
      tb.innerHTML = '<tr><td colspan="11" style="text-align:center;padding:20px;color:#94a3b8">Sin coincidencias</td></tr>';
      return;
    }
    tb.innerHTML = rows.map(function(m){
      var faltaProv = !(m.proveedor_principal||'').trim();
      var hl = faltaProv ? 'background:#fef3c7' : '';
      return '<tr data-codigo="'+m.codigo+'" style="border-bottom:1px solid #e2e8f0;'+hl+'">' +
        '<td style="padding:4px 6px;font-family:monospace;font-size:10px">'+m.codigo+'</td>' +
        '<td style="padding:4px 6px;font-size:10px">'+(m.descripcion||'').substring(0,32)+'</td>' +
        '<td style="padding:4px 6px"><span style="background:#f1f5f9;padding:1px 6px;border-radius:8px;font-size:9px">'+(m.categoria||'')+'</span></td>' +
        '<td style="padding:2px"><input type="text" value="'+(m.proveedor_principal||'').replace(/"/g,"&quot;")+'" placeholder="proveedor..." onchange="meeConfigSave(this,\''+m.codigo+'\',\'proveedor_principal\')" style="width:130px;padding:3px;border:1px solid #cbd5e1;border-radius:3px;font-size:10px"></td>' +
        '<td style="padding:2px"><select onchange="meeConfigSave(this,\''+m.codigo+'\',\'origen\')" style="padding:3px;border:1px solid #cbd5e1;border-radius:3px;font-size:10px">' +
          ['China','Local','Mixto'].map(function(o){return '<option value="'+o+'"'+(m.origen===o?' selected':'')+'>'+o+'</option>';}).join('') +
        '</select></td>' +
        '<td style="padding:2px"><input type="number" value="'+(m.lead_time_dias||30)+'" onchange="meeConfigSave(this,\''+m.codigo+'\',\'lead_time_dias\')" style="width:50px;padding:3px;border:1px solid #cbd5e1;border-radius:3px;font-size:10px;text-align:right"></td>' +
        '<td style="padding:2px"><input type="number" value="'+(m.moq_unidades||0)+'" onchange="meeConfigSave(this,\''+m.codigo+'\',\'moq_unidades\')" style="width:60px;padding:3px;border:1px solid #cbd5e1;border-radius:3px;font-size:10px;text-align:right"></td>' +
        '<td style="padding:2px"><input type="number" step="0.01" value="'+(m.precio_unit||0)+'" onchange="meeConfigSave(this,\''+m.codigo+'\',\'precio_unit\')" style="width:60px;padding:3px;border:1px solid #cbd5e1;border-radius:3px;font-size:10px;text-align:right"></td>' +
        '<td style="padding:2px;text-align:center"><input type="checkbox"'+(m.aplica?' checked':'')+' onchange="meeConfigSave(this,\''+m.codigo+'\',\'aplica\')"></td>' +
        '<td style="padding:2px;text-align:center"><input type="checkbox"'+(m.disparo_d20?' checked':'')+' onchange="meeConfigSave(this,\''+m.codigo+'\',\'disparo_d20\')" title="Cron D-20 (serigrafía/tampografía)"></td>' +
        '<td style="padding:2px;text-align:center"><input type="checkbox"'+(m.disparo_post_envasado?' checked':'')+' onchange="meeConfigSave(this,\''+m.codigo+'\',\'disparo_post_envasado\')" title="Etiqueta — se pide post-envasado"></td>' +
      '</tr>';
    }).join('');
  }
  async function meeConfigSave(el, codigo, field){
    var val = el.type === 'checkbox' ? el.checked : el.value;
    var status = document.getElementById('mee-config-status');
    el.style.background = '#fef9c3';
    try{
      var body = {}; body[field] = val;
      var r = await fetch('/api/planta/mee-config/'+encodeURIComponent(codigo), {
        method:'PUT', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body),
      });
      var d = await r.json();
      if(!r.ok || !d.ok) throw new Error(d.error || 'HTTP '+r.status);
      el.style.background = '#dcfce7';
      setTimeout(function(){ el.style.background = ''; }, 800);
      // Update cached data
      var item = _meeConfigData.find(function(m){return m.codigo === codigo;});
      if(item) item[field] = val;
      if(status) status.textContent = '✓ '+codigo+' · '+field+' guardado';
    }catch(e){
      el.style.background = '#fee2e2';
      if(status) status.textContent = '❌ '+e.message;
    }
  }

  // ── Alerta etiquetas post-envasado
  async function alertEtiquetasRecargar(){
    var sub = document.getElementById('alert-etiq-subtitle');
    var list = document.getElementById('alert-etiq-list');
    if(sub) sub.textContent = 'Cargando…';
    try{
      var r = await fetch('/api/planta/alerta-etiquetas-pendientes?dias=14', {credentials:'same-origin'});
      if(!r.ok) throw new Error('HTTP '+r.status);
      var d = await r.json();
      var k = d.kpis || {};
      if(sub) sub.textContent = (k.pendientes_etiqueta||0)+' / '+(k.total_envasados||0)+' envasados últimos 14d sin SC etiqueta · '+(k.unidades_pendientes||0).toLocaleString()+' ud';
      var pendientes = (d.pendientes||[]);
      if(!pendientes.length){
        list.innerHTML = '<div style="text-align:center;color:#92400e;font-size:11px;padding:8px;font-style:italic">Sin envasados pendientes ✓</div>';
        return;
      }
      list.innerHTML = pendientes.slice(0,15).map(function(e){
        var etqs = (e.etiquetas_sku||[]).map(function(et){
          return et.codigo+' (stock '+(et.stock||0)+')';
        }).join(', ') || '<span style="color:#dc2626">⚠️ Sin etiquetas configuradas para SKU</span>';
        var btn = (e.etiquetas_sku && e.etiquetas_sku.length)
          ? '<button onclick="alertEtiquetaCrearSC('+e.id+')" style="padding:3px 8px;background:#92400e;color:#fff;border:none;border-radius:4px;font-size:10px;cursor:pointer;font-weight:700">📥 Crear SC</button>'
          : '<span style="font-size:10px;color:#dc2626">configura sku_mee_config</span>';
        return '<div style="background:#fff;border:1px solid #fcd34d;border-radius:6px;padding:6px 10px;font-size:11px">' +
               '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:4px">' +
               '<b style="color:#92400e">'+e.lote+'</b> · '+(e.producto||'').substring(0,30)+' · '+e.unidades+' ud · '+(e.fecha||'').substring(0,10) +
               btn + '</div>' +
               '<div style="font-size:10px;color:#78350f;margin-top:2px">'+etqs+'</div>' +
               '</div>';
      }).join('');
    }catch(err){
      if(sub) sub.textContent = 'Error cargando: '+(err.message||err);
    }
  }
  async function alertEtiquetaCrearSC(envId){
    if(!confirm('¿Crear SC de etiquetas para este envasado? Estado: Pendiente. Catalina la verá en /solicitudes.')) return;
    try{
      var r = await fetch('/api/planta/sc-etiqueta-rapida', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({envasado_id: envId}),
      });
      var d = await r.json();
      if(!r.ok || !d.ok) throw new Error(d.error || ('HTTP '+r.status));
      alert('✅ '+d.mensaje + (d.scs_creadas.length ? '\n\nNúmeros: '+d.scs_creadas.map(function(s){return s.numero;}).join(', ') : ''));
      alertEtiquetasRecargar();
    }catch(e){
      alert('❌ Error: '+(e.message||e));
    }
  }

  // ── Alerta serigrafía/tampografía D-20
  async function alertD20Recargar(){
    var sub = document.getElementById('alert-d20-subtitle');
    var list = document.getElementById('alert-d20-list');
    if(sub) sub.textContent = 'Cargando…';
    try{
      var r = await fetch('/api/planta/alerta-d20-pendientes', {credentials:'same-origin'});
      if(!r.ok) throw new Error('HTTP '+r.status);
      var d = await r.json();
      var k = d.kpis || {};
      if(sub) sub.textContent = (k.total||0)+' producciones en ventana D-15..D-25 · '+(k.criticas||0)+' críticas · '+(k.sin_decoraciones||0)+' sin decoración configurada';
      var prods = (d.producciones||[]);
      if(!prods.length){
        list.innerHTML = '<div style="text-align:center;color:#7f1d1d;font-size:11px;padding:8px;font-style:italic">Sin producciones en ventana D-20 ✓</div>';
        return;
      }
      list.innerHTML = prods.slice(0,15).map(function(p){
        var decos = (p.decoraciones||[]).map(function(d){
          return d.tipo+': '+d.codigo+' (stock '+(d.stock||0)+', lead '+(d.lead_time||20)+'d)';
        }).join(', ');
        var btn = (p.decoraciones && p.decoraciones.length)
          ? '<button onclick="alertD20CrearSC(\''+p.producto.replace(/\\/g,"\\\\").replace(/\x27/g,"\\\x27")+'\',\''+p.fecha+'\','+p.unidades_estimadas+')" style="padding:3px 8px;background:#991b1b;color:#fff;border:none;border-radius:4px;font-size:10px;cursor:pointer;font-weight:700">🎨 Crear SC</button>'
          : '<span style="font-size:10px;color:#7f1d1d">sin decoración configurada</span>';
        var color = p.critico ? '#dc2626' : '#92400e';
        return '<div style="background:#fff;border:1px solid #fca5a5;border-radius:6px;padding:6px 10px;font-size:11px">' +
               '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:4px">' +
               '<span><b style="color:'+color+'">D-'+p.dias_hasta+'</b> · '+(p.producto||'').substring(0,30)+' · '+p.kg+'kg ('+p.unidades_estimadas+' ud)</span>' +
               btn + '</div>' +
               (decos ? '<div style="font-size:10px;color:#7f1d1d;margin-top:2px">'+decos+'</div>' : '') +
               '</div>';
      }).join('');
    }catch(err){
      if(sub) sub.textContent = 'Error cargando: '+(err.message||err);
    }
  }
  async function alertD20CrearSC(producto, fecha, unidades){
    if(!confirm('¿Crear SC de serigrafía/tampografía para '+producto+'? Lead típico 20d.')) return;
    try{
      var r = await fetch('/api/planta/sc-d20-rapida', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({producto: producto, fecha_produccion: fecha, unidades_estimadas: unidades}),
      });
      var d = await r.json();
      if(!r.ok || !d.ok) throw new Error(d.error || ('HTTP '+r.status));
      alert('✅ '+d.mensaje + (d.scs_creadas.length ? '\n\nNúmeros: '+d.scs_creadas.map(function(s){return s.numero;}).join(', ') : ''));
      alertD20Recargar();
    }catch(e){
      alert('❌ Error: '+(e.message||e));
    }
  }

  async function autoscMeeGenerar(modo, generico, forzar){
    generico = !!generico;
    var origen = (document.getElementById('autosc-mee-origen')||{value:''}).value || '';
    var nombreModo = generico ? '🎯 GENÉRICA · Catalina asigna' : (modo === 'urgente' ? 'URGENTE (30d)' : 'MENSUAL (China 9m + Local 90d)');
    var aviso = forzar
      ? '⚠️ FORZAR nuevo pedido aunque YA hay SCs MEE este mes?\n\n(Catalina podría recibir SCs duplicadas)\n\n¿Continuar?'
      : (generico
        ? 'Vas a crear UNA SC genérica con items "POR-ASIGNAR" para todos los SKUs SIN mapping.\n\nCatalina debe abrir cada item en /solicitudes y asignar:\n  • código MEE específico\n  • proveedor\n\nAl asignar, el sistema aprende y guarda el mapping para futuras SCs.\n\n¿Continuar?'
        : 'Vas a crear las SCs MEE reales '+nombreModo+(origen?' / origen '+origen:'')+'.\n\nCatalina y Alejandro revisarán en /solicitudes.\n\n¿Continuar?');
    if(!confirm(aviso)) return;
    var msg = document.getElementById('autosc-mee-msg');
    msg.style.display='block';
    msg.innerHTML = '⏳ Generando SCs MEE '+(generico ? 'genéricas' : '('+modo+')')+'…';
    try{
      var body = {modo: modo, enviar_email: true, generico: generico};
      if(origen) body.origen = origen;
      if(forzar) body.forzar = true;
      var r = await fetch('/api/planta/auto-sc-mee-generar', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body),
      });
      var data = await r.json();
      // Anti-duplicado · 409
      if(r.status === 409 && data.duplicado){
        if(confirm(data.mensaje + '\n\n¿Forzar igual?')){
          return autoscMeeGenerar(modo, generico, true);
        }
        msg.innerHTML = '⚠️ ' + data.mensaje;
        return;
      }
      if(!r.ok || !data.ok) throw new Error(data.error || ('HTTP '+r.status));
      if(data.razon_vacio){
        msg.innerHTML = '⚠️ '+data.razon_vacio;
        return;
      }
      var extra = '';
      if(data.kpis && data.kpis.items_genericos_pendientes){
        extra = '<br>🎯 <b>'+data.kpis.items_genericos_pendientes+' items genéricos</b> pendientes de asignar por Catalina ('+data.kpis.skus_genericos+' SKUs)';
      }
      msg.innerHTML = '✅ '+data.mensaje + extra + ' · <a href="/solicitudes" style="color:#fff;text-decoration:underline;font-weight:700">ver en Compras →</a>';
      autoscMeeRecargar();
    }catch(e){
      msg.innerHTML = '❌ Error generando SCs MEE: '+(e.message||e);
    }
  }

  async function cargarPlanificacion(dias){
    _planDias=dias;
    _planLoaded=false;  // Sebastián 1-may-2026: reset flag para que switchTab recargue
    _setPlanHorizonBtn(dias);
    document.getElementById('plan-empty').style.display='none';
    document.getElementById('plan-loading').style.display='block';
    document.getElementById('plan-error').style.display='none';
    document.getElementById('plan-cards').innerHTML='';
    document.getElementById('plan-deficit-box').style.display='none';
    document.getElementById('plan-ok-box').style.display='none';
    document.getElementById('plan-bulk-box').style.display='none';
    document.getElementById('plan-prods-box').style.display='none';
    var staffBox=document.getElementById('plan-staff-box'); if(staffBox) staffBox.style.display='none';
    var prodsDetailBox=document.getElementById('plan-prods-detail-box'); if(prodsDetailBox) prodsDetailBox.style.display='none';
    try{
      var r=await fetch('/api/programacion/planificacion?dias='+dias);
      var d=await r.json();
      document.getElementById('plan-loading').style.display='none';
      if(d.cal_error){
        document.getElementById('plan-error').style.display='block';
        document.getElementById('plan-error').innerHTML='&#9888; Calendario: '+d.cal_error;
      }
      _planData=d;
      _planLoaded=true;
      _renderPlanificacion(d);
    }catch(e){
      document.getElementById('plan-loading').style.display='none';
      var errDiv = document.getElementById('plan-error');
      errDiv.style.display='block';
      errDiv.style.background='#f8d7da';
      errDiv.style.border='2px solid #dc3545';
      errDiv.style.padding='16px';
      errDiv.style.fontSize='14px';
      errDiv.innerHTML='<strong>⚠ Error al cargar planificacion:</strong><br>' + e.message + '<br><small>' + (e.stack||'') + '</small>';
      _toast('Error planificacion: ' + e.message, 0);
    }
  }

  function _fmtG(g){
    // Normalizado: SIEMPRE en gramos con separador de miles (acordado con Alejandro).
    if(g === null || g === undefined) return '—';
    var n = Math.round(Number(g) || 0);
    return n.toLocaleString('es-CO') + ' g';
  }

  function _renderPlanificacion(d){
    var meses=d.meses||2;
    var dias =d.dias ||_planDias;
    var horizonteLabel = d.horizonte_label || (dias+' días');

    // Cards resumen
    var cards=[
      {val:d.total_prods,    label:'Producciones<br>en calendario', icon:'&#128197;', color:'#1a4a7a'},
      {val:d.mps_deficit?d.mps_deficit.length:0, label:'MPs en<br>déficit', icon:'&#128997;', color:d.mps_deficit&&d.mps_deficit.length?'#dc3545':'#28a745'},
      {val:d.mps_ok_count||0, label:'MPs con stock<br>suficiente', icon:'&#10003;', color:'#28a745'},
      {val:d.bulk_opps?d.bulk_opps.length:0, label:'Oportunidades<br>de bulk', icon:'&#128200;', color:'#0d47a1'},
    ];
    document.getElementById('plan-cards').innerHTML=cards.map(function(c){
      return '<div style="background:#fff;border-radius:10px;padding:16px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.08);border-top:3px solid '+c.color+'">'
        +'<div style="font-size:22px;margin-bottom:4px">'+c.icon+'</div>'
        +'<div style="font-size:26px;font-weight:800;color:'+c.color+'">'+c.val+'</div>'
        +'<div style="font-size:11px;color:#666;margin-top:4px;line-height:1.4">'+c.label+'</div>'
        +'</div>';
    }).join('');

    // Producciones en horizonte
    if(d.producciones&&d.producciones.length){
      document.getElementById('plan-prods-box').style.display='block';
      var byMes={};
      d.producciones.forEach(function(p){ byMes[p.mes]=byMes[p.mes]||[]; byMes[p.mes].push(p); });
      var html='';
      Object.keys(byMes).sort().forEach(function(mes){
        html+='<div style="margin-bottom:8px;width:100%"><span style="font-size:11px;font-weight:700;color:#1a4a7a;text-transform:uppercase;letter-spacing:1px">'+mes+'</span><div style="display:flex;flex-wrap:wrap;gap:5px;margin-top:4px">';
        byMes[mes].forEach(function(p){
          html+='<span style="background:#e8f0fe;color:#1a4a7a;border-radius:5px;padding:3px 10px;font-size:12px;font-weight:600">'+p.producto+' ('+p.kg+' kg)</span>';
        });
        html+='</div></div>';
      });
      document.getElementById('plan-prods-list').innerHTML=html||'Sin producciones identificadas en el calendario';
    }

    // Vista por producción: cada producción con su MP status
    if(d.producciones && d.producciones.length){
      document.getElementById('plan-prods-detail-box').style.display='block';
      var detailHtml=d.producciones.map(function(p, idx){
        var statusBadge = p.puede_producir
          ? '<span style="background:#d4edda;color:#155724;border-radius:12px;padding:3px 10px;font-size:11px;font-weight:700">&#10003; Puede producir</span>'
          : '<span style="background:#f8d7da;color:#721c24;border-radius:12px;padding:3px 10px;font-size:11px;font-weight:700">&#9888; Faltan '+p.n_mps_falta+' MP(s)</span>';
        var fechaStr = p.fecha || '';
        var producerHeader = '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;cursor:pointer" onclick="_toggleProdDetail('+idx+')">'
          +'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
          +'<span id="plan-prod-arrow-'+idx+'" style="color:#1a4a7a;font-size:12px">&#9654;</span>'
          +'<strong style="font-size:13px;color:#1a4a7a">'+p.producto+'</strong>'
          +'<span style="font-size:11px;color:#666">'+fechaStr+' &middot; '+p.kg+' kg</span>'
          +'</div>'+statusBadge+'</div>';
        var alcanzanList = (p.mps_status||[]).filter(function(m){return m.alcanza;});
        var faltanList   = (p.mps_status||[]).filter(function(m){return !m.alcanza;});
        var faltanHtml=faltanList.map(function(m){
          var stockTxt = m.ilimitado ? '∞ (producido en sitio)' : _fmtG(m.stock_g);
          return '<tr style="background:#fff5f5;border-bottom:1px solid #fadcdc">'
            +'<td style="padding:6px 8px;font-size:11px"><span style="color:#dc3545">&#9888;</span> '+m.nombre+'<span style="color:#aaa;font-size:10px;margin-left:4px;font-family:monospace">'+m.material_id+'</span></td>'
            +'<td style="padding:6px 8px;font-size:11px;text-align:right">'+_fmtG(m.necesario_g)+'</td>'
            +'<td style="padding:6px 8px;font-size:11px;text-align:right;color:#dc3545">'+stockTxt+'</td>'
            +'<td style="padding:6px 8px;font-size:11px;text-align:right;font-weight:700;color:#dc3545">'+_fmtG(m.deficit_g)+'</td>'
            +'</tr>';
        }).join('');
        var alcanzanHtml=alcanzanList.map(function(m){
          var stockTxt = m.ilimitado ? '∞' : _fmtG(m.stock_g);
          return '<tr style="border-bottom:1px solid #eee">'
            +'<td style="padding:5px 8px;font-size:11px"><span style="color:#28a745">&#10003;</span> '+m.nombre+'<span style="color:#aaa;font-size:10px;margin-left:4px;font-family:monospace">'+m.material_id+'</span></td>'
            +'<td style="padding:5px 8px;font-size:11px;text-align:right">'+_fmtG(m.necesario_g)+'</td>'
            +'<td style="padding:5px 8px;font-size:11px;text-align:right;color:#28a745">'+stockTxt+'</td>'
            +'<td style="padding:5px 8px;font-size:11px;text-align:right;color:#aaa">—</td>'
            +'</tr>';
        }).join('');
        var detailBody=''
          +'<div id="plan-prod-detail-'+idx+'" style="display:none;margin-top:10px;background:#fafbfc;border-radius:6px;padding:10px;border:1px solid #e8eaed">'
          + (faltanHtml ? '<div style="font-size:11px;font-weight:700;color:#dc3545;margin-bottom:4px">&#128997; Faltantes ('+faltanList.length+')</div>'
              +'<table style="width:100%;border-collapse:collapse;margin-bottom:10px"><thead><tr style="background:#fceaea;color:#721c24"><th style="padding:5px 8px;text-align:left;font-size:11px">MP</th><th style="padding:5px 8px;text-align:right;font-size:11px">Necesario</th><th style="padding:5px 8px;text-align:right;font-size:11px">Stock</th><th style="padding:5px 8px;text-align:right;font-size:11px">Falta</th></tr></thead><tbody>'+faltanHtml+'</tbody></table>'
              : '')
          + (alcanzanHtml ? '<div style="font-size:11px;font-weight:700;color:#155724;margin-bottom:4px">&#10003; MPs suficientes ('+alcanzanList.length+')</div>'
              +'<table style="width:100%;border-collapse:collapse"><thead><tr style="background:#e8f5e9;color:#155724"><th style="padding:5px 8px;text-align:left;font-size:11px">MP</th><th style="padding:5px 8px;text-align:right;font-size:11px">Necesario</th><th style="padding:5px 8px;text-align:right;font-size:11px">Stock</th><th style="padding:5px 8px;text-align:right;font-size:11px">—</th></tr></thead><tbody>'+alcanzanHtml+'</tbody></table>'
              : '')
          +'</div>';
        var bgColor = p.puede_producir ? '#fff' : '#fff8f8';
        var brColor = p.puede_producir ? '#28a745' : '#dc3545';
        return '<div style="background:'+bgColor+';border:1px solid #e0e0e0;border-left:4px solid '+brColor+';border-radius:6px;padding:10px 14px;margin-bottom:8px">'
          +producerHeader+detailBody+'</div>';
      }).join('');
      document.getElementById('plan-prods-detail-list').innerHTML=detailHtml;
    }

    // Staff general de MPs (todos los MPs con su estado)
    _renderStaffGeneral();

    // Tabla de déficit
    if(d.mps_deficit&&d.mps_deficit.length){
      document.getElementById('plan-deficit-box').style.display='block';
      var rows=d.mps_deficit.map(function(mp){
        var pct=mp.cobertura_pct;
        var pctColor=pct<30?'#dc3545':pct<70?'#fd7e14':'#28a745';
        var origenIcon=mp.origen==='china'?'&#127464;&#127475;':mp.origen==='colombia'?'&#127464;&#127476;':'&#127758;';
        return '<tr style="border-bottom:1px solid #eee">'
          +'<td style="padding:8px"><div style="font-weight:600;font-size:12px">'+mp.nombre+'</div>'
          +'<div style="font-size:10px;color:#888;font-family:monospace">'+mp.material_id+'</div></td>'
          +'<td style="padding:8px;font-size:12px;cursor:pointer;border-radius:4px" data-mid="'+mp.material_id+'" onclick="_editProv(this)" title="Clic para editar proveedor">'+origenIcon+' '+(mp.proveedor||'<em style="color:#bbb;font-size:11px">Sin asignar</em>')+'<span style="color:#ccc;font-size:10px;margin-left:3px">&#9998;</span></td>'
          +'<td style="padding:8px;text-align:right;font-size:12px">'+_fmtG(mp.total_g)+'</td>'
          +'<td style="padding:8px;text-align:right;font-size:12px;color:'+(mp.stock_g<mp.total_g?'#dc3545':'#28a745')+'">'+_fmtG(mp.stock_g)+'</td>'
          +'<td style="padding:8px;text-align:right;font-weight:700;color:#dc3545;font-size:12px">'+_fmtG(mp.deficit_g)+'</td>'
          +'<td style="padding:8px;text-align:center"><div style="display:inline-block;background:#f0f0f0;border-radius:10px;overflow:hidden;width:80px;height:12px;margin-bottom:2px"><div style="background:'+pctColor+';width:'+pct+'%;height:100%"></div></div><div style="font-size:11px;color:'+pctColor+';font-weight:700">'+pct+'%</div></td>'
          +'<td style="padding:8px;text-align:center"><span style="background:#e8f0fe;color:#1a4a7a;border-radius:10px;padding:2px 8px;font-size:11px;font-weight:700">'+mp.n_meses+'m</span></td>'
          +'<td style="padding:8px;font-size:11px;color:#555;max-width:160px">'+mp.productos.join(', ')+'</td>'
          +'</tr>';
      }).join('');
      document.getElementById('plan-deficit-tbody').innerHTML=rows;
    }

    // MPs OK
    if(d.mps_ok_count>0){
      document.getElementById('plan-ok-box').style.display='block';
      // Construir lista desde mps del backend que no están en deficit
      // (solo mostramos count ya que la lista puede ser grande)
      document.getElementById('plan-ok-list').innerHTML='<span style="font-size:13px;color:#155724">'+d.mps_ok_count+' materias primas tienen stock suficiente para cubrir todas las producciones del período.</span>';
    }

    // Bulk opportunities
    if(d.bulk_opps&&d.bulk_opps.length){
      document.getElementById('plan-bulk-box').style.display='block';
      var bulkHtml=d.bulk_opps.map(function(mp){
        var origenBadge=mp.origen==='china'
          ?'<span style="background:#fff3e0;color:#e65100;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700">&#127464;&#127475; Importación</span>'
          :'<span style="background:#e8f5e9;color:#1b5e20;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700">&#127464;&#127476; Local</span>';
        return '<div style="background:#fff;border:1px solid #c5d8fa;border-radius:8px;padding:14px;margin-bottom:10px;border-left:4px solid #0d47a1">'
          +'<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">'
          +'<div><div style="font-weight:700;font-size:13px;color:#0d47a1">'+mp.nombre+'</div>'
          +'<div style="font-size:11px;color:#888;margin-top:2px">Proveedor: '+(mp.proveedor||'Sin asignar')+' &nbsp;|&nbsp; Usada en: '+mp.productos.join(', ')+'</div></div>'
          +origenBadge+'</div>'
          +'<div style="margin-top:8px;font-size:12px;color:#1a4a7a;background:#e8f0fe;border-radius:5px;padding:8px">&#128161; '+mp.bulk_msg+'</div>'
          +'<div style="margin-top:6px;display:flex;gap:12px;font-size:11px;color:#555">'
          +'<span>Total necesario: <strong>'+_fmtG(mp.total_g)+'</strong></span>'
          +'<span>Stock actual: <strong>'+_fmtG(mp.stock_g)+'</strong></span>'
          +'<span>Déficit: <strong style="color:#dc3545">'+_fmtG(mp.deficit_g)+'</strong></span>'
          +'<span>Meses de uso: <strong>'+mp.n_meses+'</strong></span>'
          +'</div></div>';
      }).join('');
      document.getElementById('plan-bulk-list').innerHTML=bulkHtml;
    }

    if(!d.total_prods){
      document.getElementById('plan-empty').style.display='block';
      document.getElementById('plan-empty').innerHTML='<div style="font-size:40px;margin-bottom:12px">&#128197;</div>'
        +'<div style="font-size:14px;font-weight:600;margin-bottom:6px">Sin producciones en el calendario para este período</div>'
        +'<div style="font-size:13px;color:#aaa">Verifica que los eventos de Google Calendar tengan el código SKU en el título (ej: NPHA – Fabricacion 14 kg)</div>';
    }
  }

  function exportarPlanificacion(){
    if(!_planData||!_planData.mps_deficit) return;
    var rows=[['Material','Codigo','Proveedor','Necesario_g','Stock_g','Deficit_g','Cobertura_pct','Meses_uso','Productos']];
    _planData.mps_deficit.forEach(function(mp){
      rows.push([mp.nombre,mp.material_id,mp.proveedor,mp.total_g,mp.stock_g,mp.deficit_g,mp.cobertura_pct,mp.n_meses,mp.productos.join('|')]);
    });
    var csv=rows.map(function(r){return r.map(function(c){return '"'+String(c||'').replace(/"/g,'""')+'"';}).join(',');}).join('\n');
    var blob=new Blob([csv],{type:'text/csv'});
    var a=document.createElement('a'); a.href=URL.createObjectURL(blob);
    a.download='planificacion_mps_'+_planDias+'d_'+new Date().toISOString().slice(0,10)+'.csv';
    a.click();
  }

  async function descargarChecklistVerificacion(){
    var btn=document.getElementById('btn-checklist-verif');
    if(btn){ btn.disabled=true; btn.textContent='Generando...'; }
    try{
      var resp=await fetch('/api/programacion/planificacion/checklist-verificacion?horizontes=15,30');
      if(!resp.ok){
        var err=await resp.json().catch(function(){return {error:'error '+resp.status};});
        _toast('Error: '+(err.error||'desconocido'),0);
        if(btn){ btn.disabled=false; btn.innerHTML='&#128203; Excel para verificar (15d + 1m)'; }
        return;
      }
      var blob=await resp.blob();
      var url=URL.createObjectURL(blob);
      var a=document.createElement('a');
      a.href=url;
      a.download='verificar_bodega_15-30d_'+new Date().toISOString().slice(0,10)+'.xlsx';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      _toast('Excel descargado — listo para mandar a la asistente',1);
    }catch(e){
      _toast('Error: '+e.message,0);
    }finally{
      if(btn){ btn.disabled=false; btn.innerHTML='&#128203; Excel para verificar (15d + 1m)'; }
    }
  }

  function _toggleProdDetail(idx){
    var box=document.getElementById('plan-prod-detail-'+idx);
    var arr=document.getElementById('plan-prod-arrow-'+idx);
    if(!box) return;
    var open = box.style.display==='block';
    box.style.display = open ? 'none' : 'block';
    if(arr) arr.innerHTML = open ? '&#9654;' : '&#9660;';
  }

  function _renderStaffGeneral(){
    if(!_planData) return;
    var deficit = (_planData.mps_deficit||[]).map(function(mp){return Object.assign({}, mp, {_estado:'deficit'});});
    var ok      = (_planData.mps_ok     ||[]).map(function(mp){return Object.assign({}, mp, {_estado:'ok'});});
    var todos   = deficit.concat(ok);
    if(!todos.length){
      document.getElementById('plan-staff-box').style.display='none';
      return;
    }
    document.getElementById('plan-staff-box').style.display='block';
    var fEl=document.getElementById('plan-staff-filter');
    var sEl=document.getElementById('plan-staff-state');
    var filtro=(fEl&&fEl.value||'').trim().toLowerCase();
    var estadoF=(sEl&&sEl.value||'todos');
    var visibles = todos.filter(function(mp){
      if(estadoF==='deficit' && mp._estado!=='deficit') return false;
      if(estadoF==='ok'      && mp._estado!=='ok')      return false;
      if(filtro){
        var t=(mp.nombre+' '+mp.material_id+' '+(mp.proveedor||'')).toLowerCase();
        if(t.indexOf(filtro)===-1) return false;
      }
      return true;
    });
    // Ordenar: déficit primero, luego por nombre
    visibles.sort(function(a,b){
      if(a._estado!==b._estado) return a._estado==='deficit' ? -1 : 1;
      return (a.nombre||'').localeCompare(b.nombre||'');
    });
    if(!visibles.length){
      document.getElementById('plan-staff-tbody').innerHTML='';
      document.getElementById('plan-staff-empty').style.display='block';
      return;
    }
    document.getElementById('plan-staff-empty').style.display='none';
    var rows=visibles.map(function(mp){
      var pct=mp.cobertura_pct||0;
      var pctColor=pct<30?'#dc3545':pct<70?'#fd7e14':'#28a745';
      var estadoBadge = mp._estado==='deficit'
        ? '<span style="background:#f8d7da;color:#721c24;border-radius:10px;padding:2px 8px;font-size:10px;font-weight:700">DÉFICIT</span>'
        : '<span style="background:#d4edda;color:#155724;border-radius:10px;padding:2px 8px;font-size:10px;font-weight:700">OK</span>';
      var rowBg = mp._estado==='deficit' ? '#fff8f8' : '#fff';
      return '<tr style="background:'+rowBg+';border-bottom:1px solid #eee">'
        +'<td style="padding:7px 8px;text-align:center">'+estadoBadge+'</td>'
        +'<td style="padding:7px 8px"><div style="font-weight:600;font-size:12px">'+mp.nombre+'</div><div style="font-size:10px;color:#888;font-family:monospace">'+mp.material_id+'</div></td>'
        +'<td style="padding:7px 8px;font-size:11px;color:#555">'+(mp.proveedor||'<em style="color:#bbb">Sin asignar</em>')+'</td>'
        +'<td style="padding:7px 8px;text-align:right;font-size:12px">'+_fmtG(mp.total_g)+'</td>'
        +'<td style="padding:7px 8px;text-align:right;font-size:12px;color:'+(mp.stock_g<mp.total_g?'#dc3545':'#28a745')+'">'+_fmtG(mp.stock_g)+'</td>'
        +'<td style="padding:7px 8px;text-align:right;font-size:12px;font-weight:'+(mp.deficit_g>0?'700':'400')+';color:'+(mp.deficit_g>0?'#dc3545':'#aaa')+'">'+(mp.deficit_g>0?_fmtG(mp.deficit_g):'—')+'</td>'
        +'<td style="padding:7px 8px;text-align:center"><div style="display:inline-block;background:#f0f0f0;border-radius:10px;overflow:hidden;width:60px;height:8px"><div style="background:'+pctColor+';width:'+pct+'%;height:100%"></div></div><div style="font-size:10px;color:'+pctColor+';font-weight:700">'+pct+'%</div></td>'
        +'<td style="padding:7px 8px;font-size:10px;color:#666;max-width:140px">'+(mp.productos||[]).slice(0,3).join(', ')+((mp.productos||[]).length>3?' +'+((mp.productos||[]).length-3):'')+'</td>'
        +'</tr>';
    }).join('');
    document.getElementById('plan-staff-tbody').innerHTML=rows;
  }

  async function solicitarBloque(){
    if(!_planData||!_planData.mps_deficit||!_planData.mps_deficit.length){
      _toast('No hay MPs en déficit para el período actual',0); return;
    }
    var nDef=_planData.mps_deficit.length;
    var label=_planData.horizonte_label||(_planDias+' días');
    if(!confirm('¿Crear solicitudes de compra agrupadas por proveedor para '+nDef+' MPs en déficit ('+label+')?\n\nSe creará 1 solicitud por proveedor con todos sus MPs faltantes. Esto queda registrado en audit log.')) return;
    var btn=document.getElementById('btn-solicitar-bloque');
    if(btn){ btn.disabled=true; btn.textContent='Creando...'; }
    try{
      var resp=await fetch('/api/programacion/planificacion/solicitar-bulk',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({dias:_planDias, urgencia:'Normal'})
      });
      var data=await resp.json();
      if(btn){ btn.disabled=false; btn.innerHTML='&#128229; Solicitar en bloque'; }
      if(!resp.ok || data.error){
        _toast('Error: '+(data.error||'desconocido'),0);
        return;
      }
      var n=data.count_solicitudes||0;
      var nE=data.count_errores||0;
      var msg = n+' solicitud(es) creadas';
      if(data.solicitudes_creadas && data.solicitudes_creadas.length){
        var nums=data.solicitudes_creadas.map(function(s){return s.numero;}).join(', ');
        msg += ' ('+nums+')';
      }
      if(nE) msg += ' · '+nE+' errores';
      _toast(msg, n>0?1:0);
    }catch(e){
      if(btn){ btn.disabled=false; btn.innerHTML='&#128229; Solicitar en bloque'; }
      _toast('Error: '+e.message, 0);
    }
  }

  async function solicitarNecesidades(){
    if(!_planData||!_planData.mps_deficit||!_planData.mps_deficit.length){
      _toast('No hay MPs en déficit para el período actual',0); return;
    }
    var deficit = _planData.mps_deficit;
    // Agrupar por proveedor
    var grupos = {};
    deficit.forEach(function(mp){
      var prov = (mp.proveedor||'').trim() || 'Sin asignar';
      if(!grupos[prov]) grupos[prov] = [];
      grupos[prov].push(mp);
    });
    var proveedores = Object.keys(grupos);
    var btn = document.getElementById('btn-solicitar');
    if(btn){ btn.disabled=true; btn.textContent='Creando...'; }
    var creadas = [];
    var errores = [];
    var hoy = new Date(); hoy.setDate(hoy.getDate()+7);
    var fechaReq = hoy.toISOString().slice(0,10);
    for(var i=0;i<proveedores.length;i++){
      var prov = proveedores[i];
      var mps  = grupos[prov];
      var items = mps.map(function(mp){
        var deficit_g = Math.ceil(mp.deficit_g);
        return {
          codigo_mp: mp.material_id||'',
          nombre_mp: mp.nombre||'',
          cantidad_g: deficit_g,
          unidad: 'g',
          justificacion: 'Planificación '+_planDias+'d — Para producir: '+mp.productos.slice(0,3).join(', ')+(mp.productos.length>3?' +'+(mp.productos.length-3)+' más':''),
          valor_estimado: 0
        };
      });
      // Resumen de MPs principales para que el card de solicitudes muestre
      // exactamente qué se está pidiendo, no solo el conteo.
      var mpsResumen = mps.slice(0, 5).map(function(mp){
        return mp.nombre + ' (' + Math.ceil(mp.deficit_g).toLocaleString('es-CO') + ' g)';
      }).join(', ');
      if(mps.length > 5) mpsResumen += ' +' + (mps.length-5) + ' más';
      var payload = {
        solicitante: 'sebastian',
        urgencia: 'Normal',
        observaciones: 'Planificación Estratégica '+_planDias+'d · Proveedor: '+prov+' · '+mps.length+' MPs · '+mpsResumen,
        area: 'Produccion',
        empresa: 'Espagiria',
        categoria: 'Materia Prima',
        tipo: 'Compra',
        fecha_requerida: fechaReq,
        items: items
      };
      try{
        var resp = await fetch('/api/solicitudes-compra',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify(payload)
        });
        var data = await resp.json();
        if(resp.ok && data.numero){
          creadas.push(data.numero);
        } else {
          errores.push(prov+': '+(data.error||'error desconocido'));
        }
      } catch(e){
        errores.push(prov+': '+e.message);
      }
    }
    if(btn){ btn.disabled=false; btn.innerHTML='&#128722; Solicitar necesidades'; }
    if(creadas.length){
      var msg = creadas.length===1
        ? 'Solicitud '+creadas[0]+' creada en Compras ('+deficit.length+' MPs)'
        : creadas.length+' solicitudes creadas: '+creadas.join(', ');
      _toast(msg, 1);
    }
    if(errores.length){
      _toast('Errores: '+errores.join(' | '), 0);
    }
  }

  function _editProv(td){
    var mid  = td.dataset.mid;
    var cur  = td.innerText.replace('✎','').trim();
    if(cur === 'Sin asignar') cur = '';
    var input = document.createElement('input');
    input.value = cur;
    input.style.cssText = 'width:120px;padding:3px 6px;border:2px solid #1a4a7a;border-radius:4px;font-size:12px;outline:none';
    input.onclick = function(e){ e.stopPropagation(); };
    td.innerHTML = '';
    td.appendChild(input);
    input.focus();
    function save(){
      var prov = input.value.trim();
      if(!prov){ td.innerHTML = '&#127758; <em style="color:#bbb;font-size:11px">Sin asignar</em><span style="color:#ccc;font-size:10px;margin-left:3px">&#9998;</span>'; return; }
      td.innerHTML = '<span style="color:#999;font-size:11px">Guardando...</span>';
      fetch('/api/maestro-mps/'+mid+'/proveedor',{
        method:'PUT', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({proveedor:prov})
      }).then(function(r){return r.json();}).then(function(d){
        if(d.ok||d.message){
          td.innerHTML = '&#127758; '+prov+'<span style="color:#28a745;font-size:10px;margin-left:4px">&#10003;</span><span style="color:#ccc;font-size:10px;margin-left:3px">&#9998;</span>';
          td.dataset.mid = mid;
          td.onclick = function(){ _editProv(td); };
          // Update bulk opps panel too
          if(_planData&&_planData.bulk_opps){
            _planData.bulk_opps.forEach(function(mp){ if(mp.material_id===mid) mp.proveedor=prov; });
          }
          _toast('Proveedor actualizado: '+prov, 1);
        } else {
          td.innerHTML = '&#127758; '+prov+'<span style="color:#dc3545;font-size:10px;margin-left:4px">&#10007;</span><span style="color:#ccc;font-size:10px;margin-left:3px">&#9998;</span>';
          _toast('Error al guardar: '+(d.error||''), 0);
        }
        td.dataset.mid = mid;
        td.onclick = function(){ _editProv(td); };
      }).catch(function(e){
        td.innerHTML = '&#127758; '+prov+'<span style="color:#dc3545;font-size:10px;margin-left:4px">&#10007;</span>';
        _toast('Error: '+e.message, 0);
      });
    }
    input.addEventListener('blur', save);
    input.addEventListener('keydown', function(e){
      if(e.key==='Enter'){ e.preventDefault(); input.blur(); }
      if(e.key==='Escape'){ td.innerHTML = '&#127758; '+(cur||'<em style="color:#bbb;font-size:11px">Sin asignar</em>')+'<span style="color:#ccc;font-size:10px;margin-left:3px">&#9998;</span>'; td.dataset.mid=mid; td.onclick=function(){_editProv(td);}; }
    });
  }

  async function guardarProgramacion() {
    var producto = document.getElementById('mp-producto').value;
    var fecha    = document.getElementById('mp-fecha').value;
    var lotes    = parseInt(document.getElementById('mp-lotes').value) || 1;
    var obs      = document.getElementById('mp-obs').value;
    if(!fecha){ alert('Selecciona una fecha'); return; }
    try{
      var r = await fetch('/api/programacion/programar', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({producto:producto, fecha:fecha, lotes:lotes, observaciones:obs})
      });
      var d = await r.json();
      if(!d.ok){ alert('Error: '+(d.error||'desconocido')); return; }
      // Si hay sala u operario seleccionado, persistir asignacion
      var asign = {};
      var sala = document.getElementById('mp-sala').value;
      var disp = document.getElementById('mp-op-disp').value;
      var elab = document.getElementById('mp-op-elab').value;
      var env  = document.getElementById('mp-op-env').value;
      var acon = document.getElementById('mp-op-acon').value;
      if(sala) asign.area_id                       = parseInt(sala);
      if(disp) asign.operario_dispensacion_id      = parseInt(disp);
      if(elab) asign.operario_elaboracion_id       = parseInt(elab);
      if(env)  asign.operario_envasado_id          = parseInt(env);
      if(acon) asign.operario_acondicionamiento_id = parseInt(acon);
      if(Object.keys(asign).length){
        var rA = await fetch('/api/programacion/programar/'+d.id+'/asignar', {
          method:'PATCH', headers:{'Content-Type':'application/json'},
          body: JSON.stringify(asign)
        });
        var dA = await rA.json();
        if(dA.warnings && dA.warnings.length){
          // No bloqueante — solo informativo
          console.warn('Conflicto asignacion:', dA.warnings);
        }
      }
      cerrarModalProgramar();
      actualizarDashboard();
    }catch(e){ alert('Error de red: '+e); }
  }

  function cargarEventosProducto(producto) {
    fetch('/api/programacion/programar').then(function(r){ return r.json(); }).then(function(eventos){
      var futuros = eventos.filter(function(e){
        return e.producto === producto && e.estado !== 'cancelado' && e.estado !== 'completado';
      });
      var lista = document.getElementById('mp-eventos-lista');
      var items = document.getElementById('mp-eventos-items');
      if(futuros.length === 0){ lista.style.display='none'; return; }
      lista.style.display = 'block';
      items.innerHTML = futuros.map(function(ev){
        var estadoColor = ev.estado === 'pendiente' ? '#0d6efd' : '#fd7e14';
        // Badges sala + operarios asignados (post-INVIMA)
        var asignadoBits = [];
        if(ev.area_nombre) asignadoBits.push('🏭 '+ev.area_nombre);
        if(ev.operario_dispensacion)      asignadoBits.push('Disp: '+ev.operario_dispensacion);
        if(ev.operario_elaboracion)       asignadoBits.push('Elab: '+ev.operario_elaboracion);
        if(ev.operario_envasado)          asignadoBits.push('Env: '+ev.operario_envasado);
        if(ev.operario_acondicionamiento) asignadoBits.push('Acon: '+ev.operario_acondicionamiento);
        var asignadoHTML = asignadoBits.length
          ? '<div style="font-size:11px;color:#475569;margin-top:4px;line-height:1.5">'+asignadoBits.map(function(b){
              return '<span style="background:#eef2ff;color:#3730a3;padding:1px 6px;border-radius:4px;margin-right:4px;display:inline-block;margin-bottom:2px">'+b+'</span>';
            }).join('')+'</div>'
          : '<div style="font-size:10px;color:#94a3b8;font-style:italic;margin-top:4px">Sin sala/operarios asignados</div>';
        return '<div style="padding:8px 0;border-bottom:1px solid #f5f5f5;font-size:12px">' +
          '<div style="display:flex;align-items:center;gap:8px">' +
            '<span style="flex:1;font-weight:600">'+ev.fecha+'</span>' +
            '<span style="color:#555">'+ev.lotes+' lote'+(ev.lotes>1?'s':'')+'</span>' +
            '<span style="background:'+estadoColor+';color:#fff;padding:2px 7px;border-radius:8px">'+ev.estado+'</span>' +
            '<button onclick="cancelarEvento('+ev.id+',\''+producto+'\')" style="background:#dc3545;color:#fff;border:none;border-radius:4px;padding:2px 7px;font-size:11px;cursor:pointer">✕</button>' +
          '</div>' +
          asignadoHTML +
          '</div>';
      }).join('');
    });
  }

  function cancelarEvento(id, producto) {
    if(!confirm('¿Cancelar esta producción programada?')) return;
    fetch('/api/programacion/programar/'+id, {method:'DELETE'})
      .then(function(r){ return r.json(); }).then(function(d){
        if(d.ok){ cargarEventosProducto(producto); actualizarDashboard(); }
      });
  }

  // ── MP Bridge UI ─────────────────────────────────────────────────────────
  function toggleBridgePanel(){
    var body = document.getElementById('bridge-panel-body');
    if(!body) return;
    body.style.display = body.style.display === 'none' ? 'block' : 'none';
  }

  async function cargarUnmatched(btn){
    var list = document.getElementById('unmatched-list');
    var cnt  = document.getElementById('unmatched-count');
    if(btn){ btn.disabled=true; btn.textContent='Cargando...'; }
    try {
      var r = await fetch('/api/programacion/mp-bridge/unmatched');
      var d = await r.json();
      if(cnt) cnt.textContent = '(' + d.total_unmatched + ' sin enlazar)';
      if(!d.unmatched || d.unmatched.length === 0){
        list.innerHTML = '<div style="color:#6d28d9;font-size:12px;padding:8px">✅ Todos los MPs de fórmulas tienen enlace o ya coinciden automáticamente.</div>';
      } else {
        list.innerHTML = d.unmatched.map(function(u){
          var cands = (u.candidates||[]).slice(0,5);
          var candHtml = cands.length === 0
            ? '<span style="color:#aaa;font-size:11px">Sin candidatos automáticos</span>'
            : cands.map(function(c){
                var safeF = encodeURIComponent(JSON.stringify({
                  formula_material_id: u.formula_material_id,
                  formula_material_nombre: u.formula_material_nombre,
                  bodega_material_id: c.material_id,
                  bodega_material_nombre: c.material_nombre
                }));
                return '<button onclick="linkBridge(this,' + "'" + safeF + "')" + '" style="background:#f0f4ff;border:1px solid #c5cef9;border-radius:4px;padding:3px 8px;font-size:11px;cursor:pointer;margin:2px">' +
                  c.material_id + ' — ' + (c.material_nombre||'').substring(0,30) +
                  ' (' + c.shared_keywords.join(',') + ')' +
                  '</button>';
              }).join('');
          return '<div style="border:1px solid #e8d5c0;border-radius:6px;padding:10px;margin-bottom:8px;background:#fffaf5">' +
            '<div style="font-size:12px;font-weight:600;color:#5c3317;margin-bottom:6px">' +
              u.formula_material_id + ' — ' + u.formula_material_nombre +
            '</div>' +
            '<div style="font-size:11px;color:#666;margin-bottom:6px">Candidatos: ' + candHtml + '</div>' +
            '<div style="display:flex;gap:6px;flex-wrap:wrap">' +
              '<input id="fid-' + u.formula_material_id + '" placeholder="ID Bodega (ej: MP00293)" ' +
                'style="border:1px solid #ccc;border-radius:4px;padding:3px 7px;font-size:11px;width:160px">' +
              '<input id="fn-' + u.formula_material_id + '" placeholder="Nombre bodega (opcional)" ' +
                'style="border:1px solid #ccc;border-radius:4px;padding:3px 7px;font-size:11px;width:200px">' +
              '<button onclick="linkBridgeManual(this,' + "'" + u.formula_material_id + "','" + u.formula_material_nombre.replace(/'/g,"") + "')" + '" ' +
                'style="background:#5c3317;color:#fff;border:none;border-radius:4px;padding:3px 10px;font-size:11px;cursor:pointer">Enlazar</button>' +
            '</div>' +
          '</div>';
        }).join('');
      }
    } catch(e) {
      if(list) list.innerHTML = '<div style="color:#c00;font-size:12px">Error: ' + e.message + '</div>';
    }
    if(btn){ btn.disabled=false; btn.textContent='↺ Cargar'; }
  }

  async function linkBridge(btn, safePayload){
    var payload;
    try { payload = JSON.parse(decodeURIComponent(safePayload)); } catch(e){ alert('Error decodificando payload'); return; }
    btn.disabled=true; btn.style.background='#c5cef9';
    var r = await fetch('/api/programacion/mp-bridge', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    var d = await r.json();
    if(d.ok){
      _toast('Enlazado: ' + payload.formula_material_id + ' → ' + payload.bodega_material_id, 1);
      cargarUnmatched(null);
      cargarBridgeMappings();
    } else {
      _toast('Error: ' + (d.error||'desconocido'), 0);
      btn.disabled=false;
    }
  }

  async function linkBridgeManual(btn, fid, fname){
    var bidEl = document.getElementById('fid-' + fid);
    var bnameEl = document.getElementById('fn-' + fid);
    var bid = bidEl ? bidEl.value.trim() : '';
    var bname = bnameEl ? bnameEl.value.trim() : '';
    if(!bid){ alert('Ingresa el ID de Bodega (ej: MP00293)'); return; }
    btn.disabled=true;
    var r = await fetch('/api/programacion/mp-bridge', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        formula_material_id: fid,
        formula_material_nombre: fname,
        bodega_material_id: bid,
        bodega_material_nombre: bname
      })
    });
    var d = await r.json();
    if(d.ok){
      _toast('Enlazado: ' + fid + ' → ' + bid, 1);
      cargarUnmatched(null);
      cargarBridgeMappings();
    } else {
      _toast('Error: ' + (d.error||'desconocido'), 0);
    }
    btn.disabled=false;
  }

  async function cargarBridgeMappings(){
    var el = document.getElementById('bridge-mappings-list');
    if(!el) return;
    var r = await fetch('/api/programacion/mp-bridge');
    var rows = await r.json();
    var active = rows.filter(function(x){ return x.activo; });
    if(active.length === 0){
      el.innerHTML = '<div style="color:#aaa;font-style:italic;font-size:12px">— sin mapeos activos —</div>';
      return;
    }
    el.innerHTML = '<table style="width:100%;border-collapse:collapse;font-size:12px">' +
      '<thead><tr style="background:#f5f5f5">' +
        '<th style="text-align:left;padding:5px 8px;border-bottom:1px solid #ddd">Formula ID</th>' +
        '<th style="text-align:left;padding:5px 8px;border-bottom:1px solid #ddd">Formula Nombre</th>' +
        '<th style="text-align:left;padding:5px 8px;border-bottom:1px solid #ddd">Bodega ID</th>' +
        '<th style="text-align:left;padding:5px 8px;border-bottom:1px solid #ddd">Bodega Nombre</th>' +
        '<th style="padding:5px 8px;border-bottom:1px solid #ddd"></th>' +
      '</tr></thead>' +
      '<tbody>' +
      active.map(function(m){
        return '<tr style="border-bottom:1px solid #f0f0f0">' +
          '<td style="padding:5px 8px;font-family:monospace;color:#5c3317">' + m.formula_material_id + '</td>' +
          '<td style="padding:5px 8px">' + (m.formula_material_nombre||'—') + '</td>' +
          '<td style="padding:5px 8px;font-family:monospace;color:#6d28d9">' + m.bodega_material_id + '</td>' +
          '<td style="padding:5px 8px">' + (m.bodega_material_nombre||'—') + '</td>' +
          '<td style="padding:5px 8px">' +
            '<button onclick="eliminarBridge(' + m.id + ')" ' +
              'style="background:#dc3545;color:#fff;border:none;border-radius:3px;padding:2px 7px;font-size:10px;cursor:pointer">✕</button>' +
          '</td>' +
        '</tr>';
      }).join('') +
      '</tbody></table>';
  }

  async function eliminarBridge(id){
    if(!confirm('¿Eliminar este enlace?')) return;
    var r = await fetch('/api/programacion/mp-bridge/' + id, {method:'DELETE'});
    var d = await r.json();
    if(d.ok){ _toast('Enlace eliminado', 1); cargarBridgeMappings(); cargarUnmatched(null); }
  }

  // ═══════════════════════════════════════════════════════════════════
  // Tab "Necesidades" · Sebastián 13-may-2026 · Sprint 2A Plan v3
  // ═══════════════════════════════════════════════════════════════════
  const URG_COLORS = {
    'CRITICO':         {bg:'#fee2e2', border:'#dc2626', text:'#991b1b', emoji:'🔴'},
    'URGENTE':         {bg:'#fff7ed', border:'#ea580c', text:'#9a3412', emoji:'🟠'},
    'VIGILAR':         {bg:'#fefce8', border:'#ca8a04', text:'#854d0e', emoji:'🟡'},
    'POR_ENTRAR':      {bg:'#ecfeff', border:'#0891b2', text:'#155e75', emoji:'🔵'},
    'OK':              {bg:'#f0fdf4', border:'#16a34a', text:'#15803d', emoji:'🟢'},
    'SIN_VENTAS':      {bg:'#f1f5f9', border:'#94a3b8', text:'#475569', emoji:'⚪'},
    // FIX 23-may-2026 · auditoría · backend emite estos sub-estados pero UI los caía a OK
    'SIN_MAPEO':       {bg:'#fef3c7', border:'#d97706', text:'#92400e', emoji:'❓'},
    'SIN_HISTORIAL':   {bg:'#e0f2fe', border:'#0284c7', text:'#075985', emoji:'🆕'},
    'SIN_VENTAS_REAL': {bg:'#f3f4f6', border:'#6b7280', text:'#374151', emoji:'⏸️'},
  };

  function escapeHtmlNec(s) {
    if (s === null || s === undefined) return '';
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  // Servicios (OS) · UI de Planta retirada 14-jun-2026 (decisión Sebastián · reduce
  // ruido visual). El feature SIGUE vivo: tablas, datos y endpoints
  // (/api/compras/ordenes-servicio, /planta/ordenes-servicio) intactos · Catalina
  // crea/gestiona OS desde Compras. Solo se quitó el tile + la tab embebida en Planta.

  // Sebastián 31-may-2026 · salud del sync Shopify + filtro B2B (verificación config)
  async function verificarSyncSalud(){
    var m=document.getElementById('modal-sync-salud'); if(m) m.remove();
    m=document.createElement('div'); m.id='modal-sync-salud';
    m.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:99999;display:flex;align-items:flex-start;justify-content:center;padding:20px;overflow:auto';
    m.innerHTML='<div style="background:#fff;border-radius:12px;max-width:760px;width:100%;box-shadow:0 12px 40px rgba(0,0,0,.3);padding:24px"><div style="text-align:center;padding:40px;color:#94a3b8">Consultando salud del sync…</div></div>';
    document.body.appendChild(m);
    m.addEventListener('click',function(e){ if(e.target===m) m.remove(); });
    try{
      var r=await fetch('/api/programacion/sync-salud',{cache:'no-store'});
      if(r.status===401){ location.href='/login'; return; }
      var d=await r.json();
      var esc=escapeHtmlNec;
      function row(k,v,col){ return '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f1f5f9"><span style="color:#64748b">'+k+'</span><span style="font-weight:700;color:'+(col||'#1e293b')+'">'+v+'</span></div>'; }
      var cfg=d.config||{}, b=d.b2b||{}, html='';
      html+='<div style="display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #e2e8f0;padding-bottom:12px;margin-bottom:14px">';
      html+='<div><h2 style="margin:0;font-size:18px;color:#0891b2">🔌 Salud del sync Shopify + filtro B2B</h2></div>';
      html+='<button onclick="document.getElementById(&quot;modal-sync-salud&quot;).remove()" style="background:#e2e8f0;color:#475569;border:none;width:36px;height:36px;border-radius:50%;font-size:20px;cursor:pointer">×</button></div>';
      html+='<div style="font-weight:700;color:#0f172a;margin-bottom:4px">Conexión &amp; sync</div>';
      html+=row('Dominio configurado', cfg.dominio_set?'✓ sí':'✗ NO', cfg.dominio_set?'#15803d':'#b91c1c');
      html+=row('Token configurado', cfg.token_set?'✓ sí':'✗ NO', cfg.token_set?'#15803d':'#b91c1c');
      html+=row('Órdenes totales', (d.ordenes_total!=null?d.ordenes_total:'—'));
      html+=row('Órdenes últimos 30d', (d.ordenes_30d!=null?d.ordenes_30d:'—'));
      html+=row('Última sincronización', d.ultima_sync?esc(d.ultima_sync):'—');
      html+='<div style="font-weight:700;color:#0f172a;margin:16px 0 4px">Filtro B2B (SHOPIFY_B2B_TAGS)</div>';
      if(b.error){ html+='<div style="color:#b91c1c">Error: '+esc(b.error)+'</div>'; }
      else{
        if(!b.configurado){
          html+='<div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:10px;font-size:12px;color:#9a3412;margin-bottom:8px">⚠ <b>SHOPIFY_B2B_TAGS está vacío</b> en Render. Si vendés B2B/mayorista por la tienda Shopify, esas ventas se cuentan como DTC e inflan la velocidad. Si el B2B entra solo por pedidos manuales (no por Shopify), está bien dejarlo vacío.</div>';
        } else {
          html+=row('Tags configurados', esc(b.tags_configurados.join(', ')), '#15803d');
          html+=row('Órdenes 30d clasificadas B2B', (b.ordenes_30d_clasificadas_b2b!=null?b.ordenes_30d_clasificadas_b2b:'—'));
        }
        if(b.columnas_tags_existen===false){ html+='<div style="color:#b45309;font-size:12px;margin:6px 0">⚠ Las columnas de tags no existen (mig 166 sin aplicar) · no se puede clasificar B2B.</div>'; }
        html+=row('Órdenes 30d con algún tag', (b.ordenes_30d_con_tag!=null?b.ordenes_30d_con_tag:'—'));
        if(b.tags_vistos_top && b.tags_vistos_top.length){
          html+='<div style="font-size:12px;color:#64748b;margin:10px 0 4px">Tags que traen las órdenes (últimos 30d) — usá estos para configurar la var:</div><div style="display:flex;flex-wrap:wrap;gap:6px">';
          b.tags_vistos_top.forEach(function(t){ html+='<span style="background:#eef2ff;color:#3730a3;border-radius:6px;padding:3px 8px;font-size:11px;font-weight:600">'+esc(t[0])+' <span style="color:#6366f1">×'+t[1]+'</span></span>'; });
          html+='</div>';
        } else { html+='<div style="font-size:12px;color:#94a3b8;margin-top:8px">No se vieron tags en las órdenes de los últimos 30 días.</div>'; }
      }
      // ── Salud del STOCK (lo que jala de Shopify) ──
      var st=d.stock||{};
      html+='<div style="font-weight:700;color:#0f172a;margin:16px 0 4px">📦 Stock desde Shopify</div>';
      if(st.error){ html+='<div style="color:#b91c1c">Error: '+esc(st.error)+'</div>'; }
      else{
        html+=row('Último sync de stock', st.ultimo_sync_stock?esc(st.ultimo_sync_stock):'—', st.ultimo_sync_stock?'#1e293b':'#b91c1c');
        html+=row('SKUs con stock disponible', (st.skus_disponibles!=null?st.skus_disponibles:'—'), (st.skus_disponibles>0?'#15803d':'#b91c1c'));
        html+=row('SKUs agotados', (st.skus_agotados!=null?st.skus_agotados:'—'));
        html+=row('Unidades disponibles (total)', (st.uds_disponibles_total!=null?st.uds_disponibles_total:'—'));
        html+=row('Fuente del último sync', st.uso_available?'✓ Available (correcto)':'⚠ On hand (fallback)', st.uso_available?'#15803d':'#b45309');
        if(st.alerta){ html+='<div style="background:#fff1f2;border:1px solid #fecaca;border-radius:8px;padding:10px;font-size:12px;color:#991b1b;margin-top:8px">'+esc(st.alerta)+'</div>'; }
      }
      // ── Scopes del token (chequeo decisivo) ──
      var sc=d.shopify_scopes||{};
      html+='<div style="font-weight:700;color:#0f172a;margin:16px 0 4px">🔑 Permisos del token Shopify</div>';
      if(sc.error){ html+='<div style="color:#b91c1c;font-size:12px">'+esc(sc.error)+'</div>'; }
      else{
        html+=row('read_products', sc.read_products?'✓ sí':'✗ NO', sc.read_products?'#15803d':'#b91c1c');
        html+=row('read_inventory', sc.read_inventory?'✓ sí':'✗ NO', sc.read_inventory?'#15803d':'#b91c1c');
        if(sc.alerta){ html+='<div style="background:#fff1f2;border:1px solid #fecaca;border-radius:8px;padding:10px;font-size:12px;color:#991b1b;margin-top:8px">'+esc(sc.alerta)+'</div>'; }
      }
      // Botón para refrescar el stock desde Shopify AHORA
      html+='<div style="margin-top:16px;display:flex;gap:8px;align-items:center">';
      html+='<button id="btn-sync-stock-now" style="background:#0891b2;color:#fff;border:none;padding:9px 16px;border-radius:7px;font-size:13px;font-weight:700;cursor:pointer">🔄 Sincronizar stock desde Shopify ahora</button>';
      html+='<span id="sync-stock-now-msg" style="font-size:12px;color:#64748b"></span></div>';
      m.querySelector('div').innerHTML=html;
      var bsn=document.getElementById('btn-sync-stock-now');
      if(bsn){ bsn.addEventListener('click', async function(){
        var msg=document.getElementById('sync-stock-now-msg');
        bsn.disabled=true; bsn.textContent='Sincronizando…'; if(msg) msg.textContent='';
        try{
          var rr=await fetch('/api/programacion/sync-stock-shopify',{method:'POST',headers:{'Content-Type':'application/json'}});
          var dd=await rr.json();
          if(dd.ok){ if(msg){ msg.style.color='#15803d'; msg.textContent='✓ '+(dd.mensaje||'')+' · '+(dd.skipped_zero||0)+' agotados de '+(dd.total_variantes||0); } setTimeout(verificarSyncSalud,900); }
          else { if(msg){ msg.style.color='#b91c1c'; msg.textContent='✕ '+(dd.error||'falló'); } bsn.disabled=false; bsn.textContent='🔄 Reintentar'; }
        }catch(err){ if(msg){ msg.style.color='#b91c1c'; msg.textContent='✕ '+(err.message||err); } bsn.disabled=false; bsn.textContent='🔄 Reintentar'; }
      }); }
    }catch(e){ m.querySelector('div').innerHTML='<div style="color:#dc2626;padding:30px">Error: '+escapeHtmlNec(e.message||e)+'</div>'; }
  }

  // Sebastián 1-jun-2026 · Reconciliación EN VIVO Shopify ↔ motor de Necesidades.
  // Trae cada variante de Shopify y la compara SKU x SKU: On hand, Available,
  // mapeo, stock resuelto, ventas 60d, diagnóstico. "cómo jala de Shopify todo y cada uno".
  window._RECON_FILAS = []; window._RECON_SOLO_PROB = false;
  function _renderReconTabla(){
    var d = window._RECON_DATA || {}; var esc = escapeHtmlNec;
    var filas = (d.filas||[]).filter(function(f){ return window._RECON_SOLO_PROB ? f.problema : true; });
    var h = '';
    h += '<div style="display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #e2e8f0;padding-bottom:12px;margin-bottom:12px">';
    h += '<div><h2 style="margin:0;font-size:18px;color:#be185d">🔍 Reconciliación Shopify ↔ Necesidades</h2>';
    h += '<div style="font-size:11px;color:#64748b;margin-top:3px">'+(d.total_variantes||0)+' variantes · '+(d.mapeados||0)+' mapeadas · '+(d.sin_mapeo||0)+' sin mapear · <b style="color:'+((d.con_problema||0)>0?'#b91c1c':'#15803d')+'">'+(d.con_problema||0)+' con problema</b> · fuente: '+(d.used_available?'Available ✓':'On hand (fallback) ⚠')+'</div></div>';
    h += '<button onclick="document.getElementById(&quot;modal-recon&quot;).remove()" style="background:#e2e8f0;color:#475569;border:none;width:36px;height:36px;border-radius:50%;font-size:20px;cursor:pointer">×</button></div>';
    h += '<label style="font-size:12px;color:#475569;display:inline-flex;align-items:center;gap:6px;margin-bottom:10px;cursor:pointer"><input type="checkbox" '+(window._RECON_SOLO_PROB?'checked':'')+' onchange="window._RECON_SOLO_PROB=this.checked;_renderReconTabla()"> Mostrar solo problemas ('+((d.filas||[]).filter(function(f){return f.problema;}).length)+')</label>';
    h += '<div style="overflow-x:auto;max-height:60vh;border:1px solid #e2e8f0;border-radius:8px"><table style="width:100%;border-collapse:collapse;font-size:11px">';
    h += '<thead style="position:sticky;top:0"><tr style="background:#f8fafc;color:#475569"><th style="text-align:left;padding:6px 8px">SKU</th><th style="text-align:left;padding:6px 8px">Producto</th><th style="padding:6px 8px">Map</th><th style="padding:6px 8px">On hand</th><th style="padding:6px 8px">Available</th><th style="padding:6px 8px">Motor</th><th style="padding:6px 8px">Vende 60d</th><th style="text-align:left;padding:6px 8px">Diagnóstico</th></tr></thead><tbody>';
    filas.forEach(function(f){
      var bg = f.problema ? '#fff1f2' : '#fff';
      var mapCell = f.mapeado ? '✓' : (f.en_presentaciones ? '~' : '<span style="color:#b91c1c;font-weight:700">✗</span>');
      var avCell = (f.available==null) ? '<span style="color:#94a3b8">—</span>' : f.available;
      var motorCol = f.resuelto_motor>0 ? '#15803d' : '#b91c1c';
      var diagCol = f.problema ? '#b91c1c' : '#64748b';
      h += '<tr style="border-top:1px solid #f1f5f9;background:'+bg+'">'
        + '<td style="padding:5px 8px;font-family:ui-monospace;font-weight:700">'+esc(f.sku||'(vacío)')+'</td>'
        + '<td style="padding:5px 8px">'+esc(f.producto||'—')+'</td>'
        + '<td style="padding:5px 8px;text-align:center">'+mapCell+'</td>'
        + '<td style="padding:5px 8px;text-align:center">'+f.on_hand+'</td>'
        + '<td style="padding:5px 8px;text-align:center">'+avCell+'</td>'
        + '<td style="padding:5px 8px;text-align:center;font-weight:700;color:'+motorCol+'">'+f.resuelto_motor+'</td>'
        + '<td style="padding:5px 8px;text-align:center">'+(f.vende_60d||0)+'</td>'
        + '<td style="padding:5px 8px;color:'+diagCol+'">'+esc(f.diagnostico||'')+'</td>'
        + '</tr>';
    });
    if(!filas.length) h += '<tr><td colspan="8" style="padding:20px;text-align:center;color:#94a3b8">Sin filas</td></tr>';
    h += '</tbody></table></div>';
    h += '<div style="font-size:10px;color:#94a3b8;margin-top:8px">Map: ✓ en sku_producto_map · ~ solo en presentaciones · ✗ sin mapeo (su stock NO entra a Necesidades). "Motor" = unidades que ve el cálculo de cobertura.</div>';
    var mm = document.getElementById('modal-recon'); if(mm) mm.querySelector('div').innerHTML = h;
  }
  async function reconciliarShopify(){
    var m=document.getElementById('modal-recon'); if(m) m.remove();
    m=document.createElement('div'); m.id='modal-recon';
    m.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:99999;display:flex;align-items:flex-start;justify-content:center;padding:20px;overflow:auto';
    m.innerHTML='<div style="background:#fff;border-radius:12px;max-width:1000px;width:100%;box-shadow:0 12px 40px rgba(0,0,0,.3);padding:24px"><div style="text-align:center;padding:40px;color:#94a3b8">Trayendo cada variante de Shopify en vivo… (puede tardar unos segundos)</div></div>';
    document.body.appendChild(m);
    m.addEventListener('click',function(e){ if(e.target===m) m.remove(); });
    try{
      var r=await fetch('/api/programacion/reconciliar-shopify',{cache:'no-store'});
      if(r.status===401){ location.href='/login'; return; }
      var d=await r.json();
      if(!d.ok){ m.querySelector('div').innerHTML='<div style="color:#dc2626;padding:30px">Error: '+escapeHtmlNec(d.error||'')+'</div>'; return; }
      window._RECON_DATA=d; window._RECON_SOLO_PROB=((d.con_problema||0)>0);
      _renderReconTabla();
    }catch(e){ m.querySelector('div').innerHTML='<div style="color:#dc2626;padding:30px">Error: '+escapeHtmlNec(e.message||e)+'</div>'; }
  }

  // Sebastián 31-may-2026 · Planta ve las asignaciones de preparación de envases
  // (OS de serigrafía/tampografía en curso) · read-only · qué viene y para cuándo.
  async function verPreparacionEnvases(){
    var m = document.getElementById('modal-prep-envases');
    if(m) m.remove();
    m = document.createElement('div');
    m.id = 'modal-prep-envases';
    m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9999;display:flex;align-items:flex-start;justify-content:center;padding:20px;overflow:auto';
    m.innerHTML = '<div style="background:#fff;border-radius:12px;max-width:1000px;width:100%;box-shadow:0 12px 40px rgba(0,0,0,.3);padding:24px"><div style="text-align:center;padding:40px;color:#94a3b8">Cargando preparación de envases…</div></div>';
    document.body.appendChild(m);
    m.addEventListener('click', function(e){ if(e.target === m) m.remove(); });
    try {
      var r = await fetch('/api/compras/ordenes-servicio', {cache:'no-store'});
      if(r.status === 401){ window.location.href = '/login'; return; }
      var d = await r.json();
      var act = (d.ordenes || []).filter(function(o){ return ['Entregada','Confirmada','Cancelada'].indexOf(o.estado) < 0; });
      act.sort(function(a,b){ return (a.fecha_requerida_entrega||'9999') < (b.fecha_requerida_entrega||'9999') ? -1 : 1; });
      var esc = escapeHtmlNec, hoy = new Date().toISOString().slice(0,10), html = '';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #e2e8f0;padding-bottom:12px;margin-bottom:14px">';
      html += '<div><h2 style="margin:0;font-size:18px;color:#5b21b6">📦 Preparación de envases · en curso</h2><div style="font-size:11px;color:#64748b;margin-top:3px">' + act.length + ' en preparación · serigrafía / tampografía · qué viene y para cuándo (read-only)</div></div>';
      html += '<button onclick="document.getElementById(&quot;modal-prep-envases&quot;).remove()" style="background:#e2e8f0;color:#475569;border:none;width:36px;height:36px;border-radius:50%;font-size:20px;cursor:pointer">×</button></div>';
      html += '<div style="overflow-x:auto;border:1px solid #e2e8f0;border-radius:8px"><table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#f8fafc;color:#475569">';
      ['OS','Envase','Producto','Uds','Tipo','Proveedor','Lista para','Estado'].forEach(function(h,i){ html += '<th style="text-align:' + (i===3?'right':'left') + ';padding:7px 8px;font-weight:700;white-space:nowrap">' + h + '</th>'; });
      html += '</tr></thead><tbody>';
      act.forEach(function(o){
        var fr = (o.fecha_requerida_entrega||'').slice(0,10);
        var atras = fr && fr < hoy;
        var estCol = {'Borrador':'#64748b','Enviada':'#0891b2','Recogida':'#7c3aed','En proceso':'#b45309'}[o.estado] || '#475569';
        html += '<tr style="border-top:1px solid #f1f5f9' + (atras?';background:#fff1f2':'') + '">';
        html += '<td style="padding:6px 8px;font-family:ui-monospace;font-weight:700">' + esc(o.numero_os||'') + '</td>';
        html += '<td style="padding:6px 8px;font-size:11px">' + esc(o.envase_codigo_mee || o.envase_descripcion || '') + '</td>';
        html += '<td style="padding:6px 8px">' + esc(o.producto_final||'') + '</td>';
        html += '<td style="padding:6px 8px;text-align:right">' + (o.cantidad_unidades||0) + '</td>';
        html += '<td style="padding:6px 8px">' + esc(o.tipo_servicio||'') + '</td>';
        html += '<td style="padding:6px 8px">' + esc(o.proveedor||'') + '</td>';
        html += '<td style="padding:6px 8px;white-space:nowrap' + (atras?';color:#b91c1c;font-weight:700':'') + '">' + (fr||'—') + (atras?' ⚠':'') + '</td>';
        html += '<td style="padding:6px 8px"><span style="color:' + estCol + ';font-weight:700">' + esc(o.estado||'') + '</span></td>';
        html += '</tr>';
      });
      if(!act.length) html += '<tr><td colspan="8" style="padding:20px;text-align:center;color:#94a3b8">No hay envases en preparación.</td></tr>';
      html += '</tbody></table></div>';
      m.querySelector('div').innerHTML = html;
    } catch(e){
      m.querySelector('div').innerHTML = '<div style="color:#dc2626;padding:30px">Error: ' + escapeHtmlNec(e.message) + '</div>';
    }
  }

  // Sebastián 30-may-2026 · sync manual de ventas Shopify (el cron 6am a veces
  // se atrasa · esto fuerza el pull ahora). También sirve de diagnóstico: si
  // falla, el alert muestra por qué (token/HTTP) → explica datos desactualizados.
  async function syncVentasNec(btn){
    var prev = btn ? btn.textContent : '';
    if(btn){ btn.disabled = true; btn.textContent = 'Sincronizando…'; }
    try {
      // Ventana chica (cubre el atraso reciente) · 90 días por HTTP supera el
      // límite de 30s del worker → 502. El cron 6am hace los 90 días completos
      // en background (sin ese límite). Sebastián 30-may-2026.
      var r = await fetch('/api/programacion/sync-ventas', {
        method: 'POST',
        headers: {'Content-Type':'application/json','X-CSRF-Token':(typeof csrfTokenNec==='function'?csrfTokenNec():'')},
        body: JSON.stringify({days: 7}),
      });
      if(r.status === 401){ window.location.href = '/login'; return; }
      var txt = await r.text();
      var d = null;
      try { d = JSON.parse(txt); } catch(pe){ d = null; }
      if(d && d.ok){
        alert('✅ ' + (d.mensaje || (d.synced + ' órdenes sincronizadas')) +
              '\n\nRecargá Necesidades y reabrí el lote en el calendario para ver la velocidad actualizada.');
        if(typeof cargarNecesidades === 'function'){ try { cargarNecesidades(); } catch(e){} }
      } else if(d) {
        alert('❌ El sync de Shopify FALLÓ:\n\n' +
              String(d.error || JSON.stringify(d)).substring(0, 400) +
              '\n\nPasame este mensaje.');
      } else {
        // Respuesta no-JSON (página HTML) = timeout/502 del servidor
        alert('⏱ El servidor tardó demasiado (HTTP ' + r.status + ') y cortó la sincronización.\n\n' +
              'Probá de nuevo en un momento. El cron de las 6am hace la sincronización completa de 90 días en segundo plano.');
      }
    } catch(e) {
      alert('Error de red: ' + e.message);
    } finally {
      if(btn){ btn.disabled = false; btn.textContent = prev || '🔄 Sincronizar ventas'; }
    }
  }

  // Sebastián 30-may-2026 · Verificar Shopify · reconciliación ventas por SKU.
  // ¿Llega Shopify? ¿cada SKU/sub-SKU se atribuye? ¿cuánta demanda se pierde?
  window._SHOPIFY_DIAG = null;
  async function verificarShopify(){
    var m = document.getElementById('modal-shopify-diag');
    if(m) m.remove();
    m = document.createElement('div');
    m.id = 'modal-shopify-diag';
    m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9999;display:flex;align-items:flex-start;justify-content:center;padding:20px;overflow:auto';
    m.innerHTML = '<div style="background:#fff;border-radius:12px;max-width:1150px;width:100%;box-shadow:0 12px 40px rgba(0,0,0,.3);padding:24px"><div style="text-align:center;padding:40px;color:#94a3b8">Reconciliando ventas de Shopify…</div></div>';
    document.body.appendChild(m);
    m.addEventListener('click', function(e){ if(e.target === m) m.remove(); });
    try {
      var r = await fetch('/api/plan/diagnostico-shopify', {cache:'no-store'});
      if(r.status === 401){ window.location.href = '/login'; return; }
      var d = await r.json();
      if(!r.ok || !d.ok){
        m.querySelector('div').innerHTML = '<div style="color:#dc2626;padding:30px">Error: ' + escapeHtmlNec((d && d.error) || r.status) + '</div>';
        return;
      }
      window._SHOPIFY_DIAG = d;
      // Lista de productos para el dropdown de mapeo (huérfanos)
      var prodOptions = '<option value="">— elegí producto —</option>';
      try {
        var rp = await fetch('/api/programacion/productos', {cache:'no-store'});
        var dp = await rp.json();
        (dp.formulas || []).forEach(function(p){
          prodOptions += '<option>' + escapeHtmlNec(p.nombre || '') + '</option>';
        });
      } catch(e) { /* sin lista · el dropdown queda solo con el placeholder */ }
      var esc = escapeHtmlNec;
      var s = d.sync || {}, rec = d.reconciliacion || {};
      var cob = rec.pct_cobertura_real || 0;
      var cobColor = cob >= 95 ? '#15803d' : (cob >= 80 ? '#b45309' : '#b91c1c');
      var cfg = s.shopify_configurado;
      var cfgTxt = cfg === true ? '✅ conectado' + (s.shopify_shop ? ' (' + esc(s.shopify_shop) + ')' : '')
                  : (cfg === false ? '❌ NO configurado' : '— desconocido');
      var html = '';
      // Header
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #e2e8f0;padding-bottom:12px;margin-bottom:14px">';
      html += '<div><h2 style="margin:0;font-size:18px;color:#0f766e">🔍 Verificar Shopify · reconciliación de ventas por SKU</h2>';
      html += '<div style="font-size:11px;color:#64748b;margin-top:3px">Ventana 90 días · filtra cancelled/refunded · DTC-only</div></div>';
      html += '<button onclick="document.getElementById(&quot;modal-shopify-diag&quot;).remove()" style="background:#e2e8f0;color:#475569;border:none;width:36px;height:36px;border-radius:50%;font-size:20px;cursor:pointer">×</button>';
      html += '</div>';
      // Salud de ingesta
      html += '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;font-size:12px">';
      function kpi(lbl, val, col){ return '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:8px 14px;min-width:120px;text-align:center"><div style="font-size:18px;font-weight:800;color:' + (col||'#1e293b') + '">' + val + '</div><div style="font-size:10px;color:#64748b;text-transform:uppercase">' + lbl + '</div></div>'; }
      html += kpi('Shopify', cfgTxt, cfg === false ? '#b91c1c' : '#0f766e');
      html += kpi('Órdenes totales', (s.ordenes_total||0).toLocaleString('es-CO'));
      html += kpi('Últimos 30d', s.ordenes_30d||0);
      html += kpi('Últimos 60d', s.ordenes_60d||0);
      html += kpi('Últimos 90d', s.ordenes_90d||0);
      html += kpi('Última orden', s.fecha_max ? esc(String(s.fecha_max).slice(0,10)) : '—');
      html += kpi('Último sync', s.ultimo_synced_at ? esc(String(s.ultimo_synced_at).slice(0,16).replace('T',' ')) : '—');
      html += '</div>';
      // Reconciliación
      html += '<div style="background:linear-gradient(90deg,#f0fdfa,#ecfeff);border:1px solid #99f6e4;border-radius:10px;padding:14px;margin-bottom:14px">';
      html += '<div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap">';
      html += '<div style="text-align:center"><div style="font-size:34px;font-weight:900;color:' + cobColor + '">' + cob + '%</div><div style="font-size:11px;color:#475569;max-width:130px">demanda que SÍ entra al plan</div></div>';
      html += '<div style="flex:1;min-width:260px;display:flex;gap:8px;flex-wrap:wrap">';
      html += kpi('Mapeadas 90d', (rec.uds_mapeadas_90d||0).toLocaleString('es-CO'), '#15803d');
      html += kpi('Huérfanas 90d', (rec.uds_huerfanas_90d||0).toLocaleString('es-CO'), (rec.uds_huerfanas_90d>0?'#b45309':'#15803d'));
      html += kpi('SKU vacío 90d', (rec.uds_sku_vacio_90d||0).toLocaleString('es-CO'), (rec.uds_sku_vacio_90d>0?'#b91c1c':'#15803d'));
      html += kpi('Regalo 90d', (rec.uds_regalo_90d||0).toLocaleString('es-CO'), '#64748b');
      html += '</div></div>';
      // Alertas de fuga
      var alertas = '';
      if((rec.uds_sku_vacio_90d||0) > 0){
        var muestra = (d.sku_vacio && d.sku_vacio.ordenes_muestra) || [];
        alertas += '<div style="background:#fef2f2;border-left:4px solid #dc2626;border-radius:6px;padding:8px 12px;margin-top:10px;color:#991b1b;font-size:12px"><b>⚠ ' + (rec.uds_sku_vacio_90d) + ' uds vendidas sin SKU en Shopify (' + (rec.pct_perdido_sku_vacio||0) + '%)</b> · esa demanda se PIERDE. Asigná SKU a esas variantes en Shopify. Órdenes ej.: ' + muestra.slice(0,12).map(esc).join(', ') + '</div>';
      }
      if((rec.uds_huerfanas_90d||0) > 0){
        alertas += '<div style="background:#fffbeb;border-left:4px solid #f59e0b;border-radius:6px;padding:8px 12px;margin-top:8px;color:#92400e;font-size:12px"><b>⚠ ' + (rec.n_skus_huerfanos) + ' SKU sin mapear = ' + (rec.uds_huerfanas_90d) + ' uds (' + (rec.pct_perdido_huerfano||0) + '%)</b> · vendiste pero no cuentan al plan. Mapealos en sku_producto_map (tabla de abajo, filas naranja).</div>';
      }
      if(!alertas){
        alertas = '<div style="background:#f0fdf4;border-left:4px solid #16a34a;border-radius:6px;padding:8px 12px;margin-top:10px;color:#15803d;font-size:12px"><b>✓ Sin fugas</b> · toda la venta no-regalo está mapeada a un producto.</div>';
      }
      html += alertas;
      html += '</div>';
      // Tabla por SKU
      var det = d.por_sku || [];
      html += '<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">';
      html += '<h3 style="margin:0;font-size:14px;color:#0f766e">Ventas por SKU / sub-SKU (' + det.length + ')</h3>';
      html += '<input type="text" placeholder="🔍 filtrar SKU / producto / tono…" oninput="_filtShopify(this.value)" style="flex:1;max-width:340px;padding:6px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:12px">';
      html += '</div>';
      html += '<div style="overflow-x:auto;border:1px solid #e2e8f0;border-radius:8px">';
      html += '<table style="width:100%;border-collapse:collapse;font-size:12px">';
      html += '<thead><tr class="necx-thead" style="background:#f8fafc;color:#475569">';
      ['SKU','Producto','Estado','Tono','ml','30d','60d','90d'].forEach(function(h, i){
        var al = i >= 5 ? 'right' : (i===2||i===4?'center':'left');
        html += '<th style="text-align:' + al + ';padding:7px 8px;font-weight:700;white-space:nowrap">' + h + '</th>';
      });
      html += '</tr></thead><tbody id="shopify-diag-tbody">';
      det.forEach(function(it, idx){
        var badge, bg = '#fff';
        if(it.estado === 'MAPEADO'){ badge = '<span style="background:#dcfce7;color:#15803d;padding:1px 7px;border-radius:4px;font-weight:700">MAPEADO</span>'; }
        else if(it.estado === 'MAPEADO_SIN_FORMULA'){ badge = '<span title="Mapeado a un nombre que NO cruza a ninguna fórmula · la venta se pierde" style="background:#ede9fe;color:#6d28d9;padding:1px 7px;border-radius:4px;font-weight:700">SIN FÓRMULA</span>'; bg = '#faf5ff'; }
        else if(it.estado === 'REGALO'){ badge = '<span style="background:#f1f5f9;color:#64748b;padding:1px 7px;border-radius:4px;font-weight:700">REGALO</span>'; }
        else { badge = '<span style="background:#fee2e2;color:#b91c1c;padding:1px 7px;border-radius:4px;font-weight:700">HUÉRFANO</span>'; bg = '#fff7ed'; }
        var _mlEd = (it.estado === 'MAPEADO' || it.estado === 'MAPEADO_SIN_FORMULA');
        var mlTxt = _mlEd
          ? '<input id="mlx-' + idx + '" type="number" min="0" step="1" value="' + (it.ml || '') + '" placeholder="ml" style="width:50px;padding:2px 4px;border:1px solid ' + (it.ml_faltante ? '#f59e0b' : '#cbd5e1') + ';border-radius:4px;font-size:11px;text-align:right"><button onclick="setMlSku(' + idx + ')" title="Guardar el ml (volumen) de este SKU" style="margin-left:3px;background:#0f766e;color:#fff;border:none;border-radius:4px;padding:2px 6px;font-size:11px;cursor:pointer">&#10003;</button>'
          : (it.ml_faltante ? '<span style="color:#b45309;font-weight:700">&#9888; falta</span>' : (it.ml ? it.ml : '&mdash;'));
        var sattr = ((it.sku||'') + ' ' + (it.producto||'') + ' ' + (it.tono||'')).toLowerCase();
        html += '<tr data-s="' + esc(sattr) + '" style="border-top:1px solid #f1f5f9;background:' + bg + '">';
        html += '<td style="padding:6px 8px;font-family:ui-monospace;font-weight:700">' + esc(it.sku||'') + '</td>';
        if(it.estado === 'HUERFANO'){
          html += '<td style="padding:6px 8px;white-space:nowrap">' +
            '<select id="hp-' + idx + '" style="max-width:190px;font-size:11px;padding:3px;border:1px solid #f59e0b;border-radius:4px">' + prodOptions + '</select>' +
            '<label style="font-size:10px;margin-left:5px;color:#64748b"><input type="checkbox" id="hr-' + idx + '" style="vertical-align:middle"> regalo</label>' +
            '<button onclick="mapearHuerfano(' + idx + ')" style="margin-left:5px;background:#0f766e;color:#fff;border:none;padding:3px 9px;border-radius:4px;font-size:11px;font-weight:700;cursor:pointer">Mapear</button>' +
            '</td>';
        } else {
          html += '<td style="padding:6px 8px">' + (it.producto ? esc(it.producto) : '<span style="color:#94a3b8">—</span>') + '</td>';
        }
        html += '<td style="padding:6px 8px;text-align:center">' + badge + '</td>';
        html += '<td style="padding:6px 8px">' + (it.tono ? esc(it.tono) : '') + '</td>';
        html += '<td style="padding:6px 8px;text-align:center">' + mlTxt + '</td>';
        html += '<td style="padding:6px 8px;text-align:right">' + (it.uds_30d||0) + '</td>';
        html += '<td style="padding:6px 8px;text-align:right">' + (it.uds_60d||0) + '</td>';
        html += '<td style="padding:6px 8px;text-align:right;font-weight:700">' + (it.uds_90d||0) + '</td>';
        html += '</tr>';
      });
      if(!det.length){ html += '<tr><td colspan="8" style="padding:20px;text-align:center;color:#94a3b8">Sin ventas en la ventana de 90 días</td></tr>'; }
      html += '</tbody></table></div>';
      html += '<div style="font-size:11px;color:#94a3b8;margin-top:8px">' + esc(d.nota||'') + '</div>';
      m.querySelector('div').innerHTML = html;
    } catch(e) {
      m.querySelector('div').innerHTML = '<div style="color:#dc2626;padding:30px">Error de red: ' + escapeHtmlNec(e.message) + '</div>';
    }
  }
  function _filtShopify(q){
    q = (q || '').toLowerCase().trim();
    var rows = document.querySelectorAll('#shopify-diag-tbody tr');
    for(var i=0;i<rows.length;i++){
      var s = rows[i].getAttribute('data-s') || '';
      rows[i].style.display = (!q || s.indexOf(q) >= 0) ? '' : 'none';
    }
  }
  // Fija el ml (volumen) de un SKU MAPEADO desde el diagnóstico · reusa /api/plan/set-volumen (multi-tamaño).
  async function setMlSku(idx){
    var det = (window._SHOPIFY_DIAG || {}).por_sku || [];
    var it = det[idx]; if(!it) return;
    var inp = document.getElementById('mlx-' + idx);
    var v = parseFloat((inp || {}).value || '0');
    if(!(v > 0)){ alert('Poné un ml válido (> 0).'); return; }
    var t = ''; try{ t = (await (await fetch('/api/csrf-token', {credentials:'same-origin'})).json()).csrf_token || ''; }catch(e){}
    try{
      var r = await fetch('/api/plan/set-volumen', {method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRF-Token':t}, body: JSON.stringify({sku: it.sku, volumen_ml: v})});
      var d = await r.json();
      if(!r.ok){ alert('Error: ' + (d.error || r.status)); return; }
      it.ml = v; it.ml_faltante = false;
      if(inp){ inp.style.borderColor = '#16a34a'; }
      if(typeof _toast === 'function') _toast('✓ ' + it.sku + ' = ' + v + ' ml', 1);
    }catch(e){ alert('Error de red: ' + e.message); }
  }
  // Mapea un SKU huérfano a un producto (o lo marca regalo) desde el modal.
  async function mapearHuerfano(idx){
    var det = (window._SHOPIFY_DIAG || {}).por_sku || [];
    var it = det[idx];
    if(!it){ return; }
    var sel = document.getElementById('hp-' + idx);
    var chk = document.getElementById('hr-' + idx);
    var prod = sel ? sel.value : '';
    var esRegalo = !!(chk && chk.checked);
    if(!prod){ alert('Elegí un producto para ' + it.sku + (esRegalo ? ' (un regalo igual necesita su producto base)' : '')); return; }
    var btn = sel ? sel.parentNode.querySelector('button') : null;
    if(btn){ btn.disabled = true; btn.textContent = '…'; }
    try {
      var r = await fetch('/api/admin/sku-producto-map/bulk', {
        method: 'POST',
        headers: {'Content-Type':'application/json','X-CSRF-Token':(typeof csrfTokenNec==='function'?csrfTokenNec():'')},
        body: JSON.stringify({items: [{sku: it.sku, producto_nombre: prod, es_regalo: esRegalo}]}),
      });
      var d = await r.json();
      if(r.status === 401){ window.location.href = '/login'; return; }
      if(!r.ok || !d.ok || (d.n_mapeados || 0) < 1){
        var msg = (d && d.errores && d.errores[0] && d.errores[0].error) || (d && d.error) || ('HTTP ' + r.status);
        alert('No se pudo mapear ' + it.sku + ': ' + msg);
        if(btn){ btn.disabled = false; btn.textContent = 'Mapear'; }
        return;
      }
      // Éxito · refrescar reconciliación + el plan de necesidades por detrás
      verificarShopify();
      if(typeof cargarNecesidades === 'function'){ try { cargarNecesidades(); } catch(e){} }
    } catch(e) {
      alert('Error de red: ' + e.message);
      if(btn){ btn.disabled = false; btn.textContent = 'Mapear'; }
    }
  }

  // Sebastián 5-jul · forzar el sync de stock de Shopify de un clic (antes había que ir al modal de salud).
  // Trae Ánimus Lab (góndola) + Espagiria (por entrar) y recarga Necesidades con los números al día.
  async function syncStockAhora(btn){
    var _t = btn ? btn.textContent : '';
    if(btn){ btn.disabled = true; btn.textContent = '🔄 Sincronizando…'; }
    try{
      var r = await fetch('/api/programacion/sync-stock-shopify', {method:'POST', headers:{'Content-Type':'application/json'}});
      var d = await r.json().catch(function(){ return {}; });
      if(r.ok && d.ok){
        if(btn){ btn.textContent = '✓ Stock al día'; }
        setTimeout(function(){ if(btn){ btn.disabled=false; btn.textContent=_t; } cargarNecesidades(); }, 700);
      } else {
        alert('No se pudo sincronizar: ' + (d.error || ('HTTP ' + r.status)));
        if(btn){ btn.disabled=false; btn.textContent=_t; }
      }
    }catch(e){
      alert('Error de red: ' + e);
      if(btn){ btn.disabled=false; btn.textContent=_t; }
    }
  }

  function _updateSoloManualBtn() {
    var b = document.getElementById('btn-solo-manual'); if (!b) return;
    var on = !!window.__SOLO_MANUAL;
    b.textContent = on ? '🎛️ Modo manual: ON' : '🎛️ Modo manual: OFF';
    b.style.background = on ? '#16a34a' : '#475569';
  }
  async function toggleSoloManual() {
    var next = !window.__SOLO_MANUAL;
    if (!confirm(next
      ? 'Activar MODO CANÓNICO MANUAL:\n\nLa programación vivirá SOLO de las cadenas que creás a mano (punto de origen + cadencia). Se ocultan las sugerencias y los crons NO crean producciones automáticas.\n\n¿Continuar?'
      : 'Desactivar el modo manual y volver a las sugerencias/automáticos. ¿Continuar?')) return;
    try {
      var t = (await (await fetch('/api/csrf-token', {credentials:'same-origin'})).json()).csrf_token;
      var r = await fetch('/api/plan/solo-manual', {method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRF-Token':t}, body: JSON.stringify({activo: next})});
      var d = await r.json();
      if (!r.ok) { alert('No se pudo: ' + ((d && d.error) || r.status)); return; }
      window.__SOLO_MANUAL = !!d.activo;
      _updateSoloManualBtn();
      if (window.cargarNecesidades) { try { await cargarNecesidades(); } catch(e){} }
    } catch(e) { alert('Error: ' + e); }
  }
  async function cargarNecesidades() {
    const cobC = document.getElementById('nec-cob-critico').value || 20;
    const cobA = document.getElementById('nec-cob-alerta').value || 25;
    const qs = `?cobertura_dias_minimo=${cobC}&cobertura_dias_alerta=${cobA}&cobertura_dias_vigilar=45`;
    const div = document.getElementById('nec-contenido');
    div.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:40px">Cargando…</div>';
    // Sebastián 2-jul · precargar frascos (FR-*) para el select de envase por pedido B2B
    if (!window._NEC_ENVASES) {
      try {
        const _er = await fetch('/api/programacion/mees-disponibles');
        const _ed = await _er.json();
        window._NEC_ENVASES = ((_ed && _ed.items) || []).filter(function(m){ return /^FR-/.test((m.codigo||'')); });
      } catch(e){ window._NEC_ENVASES = []; }
    }
    // Sebastián 10-jul · modelo canónico manual: si está ON, ocultamos las SUGERENCIAS
    // (acción sugerida/adelantar/próxima) · la programación vive solo de las cadenas manuales.
    if (window.__SOLO_MANUAL === undefined) {
      try { window.__SOLO_MANUAL = !!(await (await fetch('/api/plan/solo-manual', {credentials:'same-origin'})).json()).activo; }
      catch(e){ window.__SOLO_MANUAL = false; }
    }
    _updateSoloManualBtn();
    try {
      const r = await fetch('/api/plan/necesidades' + qs);
      if (r.status === 401) { window.location.href = '/login'; return; }
      const d = await r.json();
      // FIX 23-may-2026 · cachear SKUs huérfanos para mapeo inline desde drill
      window._NEC_SKUS_HUERFANOS = (d.resumen && d.resumen.skus_huerfanos_vendiendo) || [];
      renderResumenNec(d.resumen);
      renderClientesNec(d.clientes);
      renderSyncBanner(d.sync_ventas, d.sync_stock);
      cargarPedidosB2BPendientes();
    } catch(e) {
      div.innerHTML = '<div style="text-align:center;color:#dc2626;padding:40px">Error: ' + escapeHtmlNec(e.message) + '</div>';
    }
  }

  // Sebastián 30-may-2026 · banner de ATRASO del sync de ventas. Si pasa >36h
  // sin sincronizar Shopify, el plan corre con ventas viejas (caso 25-may: 5
  // días stale → velocidad baja). Hace visible el fallo que antes era silencioso.
  function renderSyncBanner(sv, ss){
    var host = document.getElementById('nec-contenido');
    if(!host) return;
    ['nec-sync-banner','nec-sync-banner-stock'].forEach(function(id){var o=document.getElementById(id); if(o) o.remove();});
    function fmtCuanto(h){ return (h==null)?'tiempo desconocido':(h>=48?(h/24).toFixed(1)+' días':Math.round(h)+' horas'); }
    // Banner de VENTAS (>36h stale) · el plan usaría ventas viejas.
    if(sv){
      var h = sv.horas_desde;
      if(h == null || h > 36){
        var cuanto = fmtCuanto(h);
        var ultimo = sv.ultimo ? String(sv.ultimo).slice(0,16).replace('T',' ') : '—';
        var msg = '⚠ Ventas Shopify sin sincronizar hace <b>' + cuanto + '</b> (último: ' +
                  escapeHtmlNec(ultimo) + '). El plan puede estar usando ventas viejas · ' +
                  'la velocidad y la cobertura saldrán bajas.';
        var html = '<div id="nec-sync-banner" style="background:#fef2f2;border:1px solid #fecaca;' +
          'border-left:4px solid #dc2626;border-radius:8px;padding:10px 14px;margin-bottom:12px;' +
          'color:#991b1b;font-size:13px;display:flex;align-items:center;gap:10px;flex-wrap:wrap">' +
          '<span style="flex:1;min-width:220px">' + msg + '</span>' +
          '<button onclick="syncVentasNec(this)" style="background:#dc2626;color:#fff;border:none;' +
          'padding:6px 14px;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer">🔄 Sincronizar ahora</button>' +
          '</div>';
        host.insertAdjacentHTML('afterbegin', html);
      }
    }
    // Banner de STOCK (>12h stale) · se inserta al final para quedar ARRIBA (afterbegin) · el
    // stock decide días-de-góndola y urgencia; antes solo se vigilaba la frescura de ventas (M9).
    if(ss){
      var hs = ss.horas_desde;
      if(hs == null || hs > 12){
        var ults = ss.ultimo ? String(ss.ultimo).slice(0,16).replace('T',' ') : '—';
        var msgs = '⚠ Stock Shopify sin sincronizar hace <b>' + fmtCuanto(hs) + '</b> (último: ' +
                   escapeHtmlNec(ults) + '). Los días de góndola y la urgencia pueden estar ' +
                   'desactualizados.';
        var htmls = '<div id="nec-sync-banner-stock" style="background:#fffbeb;border:1px solid #fde68a;' +
          'border-left:4px solid #d97706;border-radius:8px;padding:10px 14px;margin-bottom:12px;' +
          'color:#92400e;font-size:13px;display:flex;align-items:center;gap:10px;flex-wrap:wrap">' +
          '<span style="flex:1;min-width:220px">' + msgs + '</span>' +
          '<button onclick="location.reload()" style="background:#d97706;color:#fff;border:none;' +
          'padding:6px 14px;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer">🔄 Recargar</button>' +
          '</div>';
        host.insertAdjacentHTML('afterbegin', htmls);
      }
    }
  }

  // 🤝 Bandeja "Pedidos B2B por confirmar" en Necesidades (Sebastián 27-jun): los pedidos del portal
  // aterrizan acá · el equipo revisa (ajusta cantidad/fecha) y con 1 click los confirma → al plan (Fijo).
  async function cargarPedidosB2BPendientes(){
    var host = document.getElementById('nec-contenido');
    if(!host) return;
    var old = document.getElementById('nec-b2b-pend'); if(old) old.remove();
    try{
      var d = await (await fetch('/api/pedidos-b2b?estado=pendiente', {cache:'no-store'})).json();
      var items = (d.items || []).filter(function(p){ return p.estado === 'pendiente'; });
      if(!items.length) return;
      var rows = items.map(function(p){
        var kg = ((p.cantidad_uds||0) * (p.ml_unidad||30) / 1000).toFixed(1);
        return '<div data-pid="'+p.id+'" style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:#fff;border:1px solid #ddd6fe;border-radius:8px;padding:8px 12px;margin-top:8px">'
          + '<div style="flex:1;min-width:200px"><b style="color:#5b21b6">'+escapeHtmlNec(p.cliente_nombre||p.cliente_id||'cliente')+'</b> · '+escapeHtmlNec(p.producto_nombre||'')+(p.notas?('<div style="font-size:10px;color:#94a3b8">'+escapeHtmlNec(p.notas)+'</div>'):'')+'</div>'
          + '<label style="font-size:11px;color:#64748b">Cant <input id="b2bc-'+p.id+'" type="number" min="1" value="'+(p.cantidad_uds||0)+'" style="width:72px;padding:3px 5px;border:1px solid #cbd5e1;border-radius:4px;text-align:right"> uds</label>'
          + '<span style="font-size:11px;color:#94a3b8">×'+(p.ml_unidad||30)+'ml ≈ '+kg+'kg</span>'
          + '<label style="font-size:11px;color:#64748b">Fecha <input id="b2bf-'+p.id+'" type="date" value="'+((p.fecha_estimada||'').slice(0,10))+'" style="padding:3px 5px;border:1px solid #cbd5e1;border-radius:4px"></label>'
          + '<button onclick="confirmarPedidoB2B('+p.id+',this)" style="background:#16a34a;color:#fff;border:none;border-radius:6px;padding:6px 14px;font-size:12px;font-weight:700;cursor:pointer">&#10003; Confirmar &rarr; al plan</button>'
          + '<div id="b2bmatch-'+p.id+'" style="flex-basis:100%;font-size:11px;color:#94a3b8;margin-top:2px">🔗 buscando lote de Ánimus…</div>'
          + '</div>';
      }).join('');
      var html = '<div id="nec-b2b-pend" style="background:linear-gradient(90deg,#f5f3ff,#faf5ff);border:1px solid #c4b5fd;border-left:4px solid #7c3aed;border-radius:10px;padding:12px 14px;margin-bottom:12px">'
        + '<div style="font-weight:800;color:#5b21b6;font-size:14px">🤝 '+items.length+' pedido'+(items.length===1?'':'s')+' B2B por confirmar</div>'
        + '<div style="font-size:11px;color:#64748b;margin-bottom:2px">Revisá cantidad y fecha · confirmá → entra al plan como producción Fija del cliente.</div>'
        + rows + '</div>';
      host.insertAdjacentHTML('afterbegin', html);
      items.forEach(function(p){ _matchPreviewB2B(p.id); });
    }catch(e){ /* silencioso · nunca romper Necesidades por la bandeja */ }
  }

  // Preview del match: a qué lote de Ánimus se sumará el pedido (la fecha de Ánimus manda) · Sebastián 27-jun.
  async function _matchPreviewB2B(pid){
    var box = document.getElementById('b2bmatch-' + pid);
    if(!box) return;
    try{
      var d = await (await fetch('/api/pedidos-b2b/' + pid + '/match-preview', {cache:'no-store'})).json();
      if(d && d.match){
        box.innerHTML = '🔗 Se suma al lote de Ánimus del <b>' + escapeHtmlNec(d.fecha) + '</b> (hoy ' + (d.kg_actual||0) + 'kg) · la fecha de Ánimus manda';
        box.style.color = '#15803d';
      } else {
        box.innerHTML = '🆕 No hay lote cercano · se creará un lote dedicado para este cliente';
        box.style.color = '#b45309';
      }
    }catch(e){ box.innerHTML = ''; }
  }

  async function confirmarPedidoB2B(pid, btn){
    if(btn){ btn.disabled = true; btn.textContent = '…'; }
    var cant = parseInt((document.getElementById('b2bc-'+pid)||{}).value || '0');
    var fecha = (document.getElementById('b2bf-'+pid)||{}).value || '';
    var body = {};
    if(cant > 0) body.cantidad_uds = cant;
    if(fecha) body.fecha_estimada = fecha;
    var t=''; try{ t=(await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json()).csrf_token||''; }catch(e){}
    try{
      var r = await fetch('/api/pedidos-b2b/'+pid+'/confirmar', {method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRF-Token':t}, body: JSON.stringify(body)});
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||r.status)); if(btn){ btn.disabled=false; btn.innerHTML='&#10003; Confirmar &rarr; al plan'; } return; }
      var row = document.querySelector('#nec-b2b-pend [data-pid="'+pid+'"]'); if(row) row.remove();
      var box = document.getElementById('nec-b2b-pend');
      if(box && !box.querySelector('[data-pid]')) box.remove();
      if(typeof _toast === 'function') _toast('✓ Pedido confirmado · '+(d.kg_b2b||'')+'kg al plan', 1);
      cargarNecesidades();
    }catch(e){ alert('Error de red: '+e.message); if(btn){ btn.disabled=false; btn.innerHTML='&#10003; Confirmar &rarr; al plan'; } }
  }

  // ═══════════════════════════════════════════════════════════════════
  // Tab "Abastecimiento" · Sebastián 23-may-2026 · Centro de solicitudes
  // Convertido de read-only a accionable · botón Solicitar, filtros,
  // lead time visible, badges SOL/OC en curso, cubrir N días
  // ═══════════════════════════════════════════════════════════════════
  const _ABA_URG_COLORS = {
    'CRITICO':     {bg:'#fee2e2', text:'#991b1b', emoji:'🔴'},
    'URGENTE':     {bg:'#fff7ed', text:'#9a3412', emoji:'🟠'},
    'VIGILAR':     {bg:'#fefce8', text:'#854d0e', emoji:'🟡'},
    'PLANIFICAR':  {bg:'#eff6ff', text:'#1e40af', emoji:'🔵'},
    'OK':          {bg:'#f0fdf4', text:'#15803d', emoji:'🟢'},
  };

  // Estado local del tab Abastecimiento
  window._ABA_STATE = {
    items: [],           // último response de /api/abastecimiento/consumo-horizontes
    horizontes: [],
    seleccionados: {},   // codigo → {cantidad_override?: number, marcado: bool}
    filtros: {           // filtros UI
      busqueda: '',
      urgencia: 'TODAS',
      proveedor: 'TODOS',
      tipo: 'TODOS',
    },
    cubrir_dias: 30,     // horizonte sugerido como cantidad a pedir
    tipoActivo: 'mp',    // Sebastián 25-may-2026 PM · sub-pestaña activa
  };

  // Sebastián 25-may-2026 PM · cambia entre sub-pestañas MP/MEE.
  // Filtra los items renderizados sin reconsultar el backend.
  window.setAbastTipo = function(tipo) {
    if (tipo !== 'mp' && tipo !== 'mee') return;
    window._ABA_STATE.tipoActivo = tipo;
    // Toggle visual de los tabs
    const tabMp = document.getElementById('abast-stab-mp');
    const tabMee = document.getElementById('abast-stab-mee');
    if (tabMp && tabMee) {
      const activo = 'padding:10px 22px;border:none;background:linear-gradient(135deg,#7c3aed,#5b21b6);color:#fff;font-size:13px;font-weight:800;cursor:pointer;border-radius:8px 8px 0 0;letter-spacing:.3px;box-shadow:0 -2px 6px rgba(124,58,237,.2);position:relative;top:2px';
      const inactivo = 'padding:10px 22px;border:none;background:#fff;color:#64748b;font-size:13px;font-weight:700;cursor:pointer;border:1px solid #e2e8f0;border-bottom:none;border-radius:8px 8px 0 0;margin-left:4px';
      if (tipo === 'mp') {
        tabMp.style.cssText = activo;
        tabMee.style.cssText = inactivo;
      } else {
        tabMp.style.cssText = inactivo;
        tabMee.style.cssText = activo;
      }
    }
    // Reset filtros para no arrastrar selección del otro tipo
    window._ABA_STATE.seleccionados = {};
    renderTablaAbast();
  };

  function _fmtAba(n) {
    if (!n || n < 0.01) return '—';
    if (n >= 1000) return Math.round(n).toLocaleString('es-CO');
    return Math.round(n*10)/10;
  }

  function _cantidadSugerida(it, cubrirDias) {
    // Cantidad a pedir = déficit EXACTO del horizonte elegido (consumo_H − stock −
    // en cola). FIX 10-jun (Sebastián): "jalar exacto para N días · ni de más ni de
    // menos". Antes, si el horizonte elegido estaba cubierto, jalaba de un horizonte
    // POSTERIOR (se pasaba). Ahora si está cubierto → 0 (no sobre-pedir).
    if (!it.deficit) return 0;
    const dh = it.deficit[String(cubrirDias)];
    return (dh && dh > 0.01) ? Math.round(dh) : 0;
  }

  function _aplicarFiltros(items) {
    const f = window._ABA_STATE.filtros;
    const q = (f.busqueda || '').toLowerCase().trim();
    return items.filter(it => {
      if (f.urgencia !== 'TODAS' && it.urgencia !== f.urgencia) return false;
      if (f.proveedor !== 'TODOS' && (it.proveedor_sugerido || '(sin proveedor)') !== f.proveedor) return false;
      if (f.tipo !== 'TODOS' && it.tipo !== f.tipo) return false;
      if (q && !(it.codigo.toLowerCase().includes(q) ||
                 (it.nombre || '').toLowerCase().includes(q) ||
                 (it.proveedor_sugerido || '').toLowerCase().includes(q))) return false;
      return true;
    });
  }

  async function cargarAbastecimiento() {
    const div = document.getElementById('abast-contenido');
    const resumenDiv = document.getElementById('abast-resumen');
    const tipos = [];
    if (document.getElementById('abast-mp').checked) tipos.push('mp');
    if (document.getElementById('abast-mee').checked) tipos.push('mee');
    if (!tipos.length) {
      div.innerHTML = '<div style="text-align:center;color:#dc2626;padding:20px">Selecciona al menos MP o MEE</div>';
      return;
    }
    const modoSel = document.getElementById('abast-modo');
    const modo = (modoSel && modoSel.value) || 'comprometido';
    div.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:40px">Calculando consumo por horizonte (' + modo + ')…</div>';
    resumenDiv.innerHTML = '';
    try {
      const r = await fetch('/api/abastecimiento/consumo-horizontes?tipo=' + tipos.join(',') + '&modo=' + encodeURIComponent(modo));
      if (r.status === 401) { window.location.href = '/login'; return; }
      if (!r.ok) {
        div.innerHTML = '<div style="text-align:center;color:#dc2626;padding:20px">Error: HTTP ' + r.status + '</div>';
        return;
      }
      const d = await r.json();
      // Guardar estado para acciones (filtros, selección)
      window._ABA_STATE.items = [].concat(d.mps || [], d.mees || []);
      window._ABA_STATE.horizontes = d.horizontes || [];
      window._ABA_STATE.seleccionados = {};

      // FIX UX 24-may-2026 noche · 2 filas separadas:
      // FILA A: cuántos LOTES hay en el calendario (con desglose)
      // FILA B: cuántas MP/MEE tienen DÉFICIT por horizonte (lo que pinta la tabla)
      // Antes ambas se mezclaban en una sola línea confusa.
      const modoLabel = d.modo === 'run_rate' ? '<span style="background:#ede9fe;color:#5b21b6;padding:2px 6px;border-radius:4px;font-weight:700">Run-rate</span>' : '<span style="background:#dcfce7;color:#15803d;padding:2px 6px;border-radius:4px;font-weight:700">Comprometido</span>';
      const nTotal = d.n_producciones_total || 0;
      const nFij = d.n_producciones_fijas || 0;
      const nSug = d.n_producciones_sugeridas || 0;
      const nB2B = d.n_pedidos_b2b_pendientes || 0;
      const lotesSem = d.lotes_por_semana_90d || 0;
      const cobDias = d.cobertura_dias || 0;
      const ultimoLote = d.ultimo_lote_fecha || '—';

      // Compactado 2-jun-2026 · UNA línea fina de contexto (no 2 cajas) · el
      // "déficit por horizonte" se fusiona DENTRO de los botones de horizonte.
      let html = '<div style="font-size:12px;color:#64748b;display:flex;gap:12px;flex-wrap:wrap;align-items:center">';
      html += '<span><strong style="color:#1e293b;font-size:14px">' + nTotal + '</strong> lotes</span>';
      html += '<span title="Fijas + Sugeridas + B2B pendientes"><span style="color:#6d28d9;font-weight:700">' + nFij + '</span> Fij · <span style="color:#7c3aed;font-weight:700">' + nSug + '</span> Sug · <span style="color:#ea580c;font-weight:700">' + nB2B + '</span> B2B</span>';
      html += '<span>📈 <strong>' + lotesSem + '</strong>/sem</span>';
      html += '<span>cobertura <strong>' + cobDias + 'd</strong></span>';
      if (d.productos_sin_lote_size && d.productos_sin_lote_size.length) {
        html += '<span style="background:#fef3c7;color:#92400e;padding:1px 8px;border-radius:6px;font-weight:700" title="Productos sin lote_size_kg · completar en /admin/formulas">⚠ ' + d.productos_sin_lote_size.length + ' sin lote_size</span>';
      }
      html += '<span style="margin-left:auto">' + modoLabel + '</span>';
      html += '</div>';
      resumenDiv.innerHTML = html;

      // Inyectar el déficit por horizonte DENTRO de cada botón de horizonte
      // (elimina la caja duplicada · "90d ·51").
      _abastPintarHorizontes(d);

      renderTablaAbast();
    } catch(e) {
      div.innerHTML = '<div style="text-align:center;color:#dc2626;padding:20px">Error red: ' + escapeHtmlNec(e.message) + '</div>';
    }
  }

  // Sebastián 24-may-2026 noche · trail por MP · "tomar producto por
  // producto enlazar fórmula e ir sumando". Modal full-screen con desglose.
  function _abastCodesList(){
    var seen={}, out=[];
    document.querySelectorAll('a[data-cod]').forEach(function(a){
      var oc = a.getAttribute('onclick')||'';
      if(oc.indexOf('abastTrailMp')<0) return;
      var cod = a.dataset.cod;
      if(cod && !seen[cod] && a.offsetParent!==null){ seen[cod]=1; out.push(cod); }
    });
    return out;
  }
  window._trailNav = {prev:null, next:null, idx:-1, n:0};
  window._trailNavBtns = function(){
    var nv = window._trailNav||{prev:null,next:null,idx:-1,n:0};
    var b = function(cod,arrow,title){ var on=!!cod; return '<button '+(on?'':'disabled')+' onclick="abastTrailMp(&quot;'+(cod||'')+'&quot;)" title="'+title+'" style="background:'+(on?'#ede9fe':'#f8fafc')+';color:'+(on?'#6d28d9':'#cbd5e1')+';border:none;width:34px;height:34px;border-radius:50%;font-size:15px;font-weight:800;cursor:'+(on?'pointer':'default')+';transition:all .15s">'+arrow+'</button>'; };
    return '<div style="display:flex;gap:6px;align-items:center">'
      + b(nv.prev,'◀','Anterior (tecla ←)')
      + (nv.idx>=0?'<span style="font-size:10px;color:#94a3b8;min-width:34px;text-align:center">'+(nv.idx+1)+' / '+nv.n+'</span>':'')
      + b(nv.next,'▶','Siguiente (tecla →)')
      + '<button onclick="document.getElementById(&quot;modal-trail-mp&quot;).remove()" title="Cerrar (Esc)" style="background:#e2e8f0;color:#475569;border:none;width:34px;height:34px;border-radius:50%;font-size:20px;cursor:pointer;margin-left:4px">×</button>'
      + '</div>';
  };
  window.abastTrailMp = async function(codigo) {
    if(window._trailKeyh){ document.removeEventListener('keydown', window._trailKeyh); window._trailKeyh=null; }
    let m = document.getElementById('modal-trail-mp');
    if (m) m.remove();
    var _codes = _abastCodesList();
    var _idx = _codes.indexOf(codigo);
    window._trailNav = {prev:(_idx>0?_codes[_idx-1]:null), next:(_idx>=0&&_idx<_codes.length-1?_codes[_idx+1]:null), idx:_idx, n:_codes.length};
    m = document.createElement('div');
    m.id = 'modal-trail-mp';
    m.style.cssText = 'position:fixed;inset:0;background:rgba(15,23,42,0.6);backdrop-filter:blur(2px);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
    m.innerHTML = '<div style="background:#fff;border-radius:16px;max-width:1100px;width:100%;max-height:92vh;overflow:auto;box-shadow:0 24px 60px rgba(15,23,42,0.4);padding:24px"><div style="text-align:center;padding:40px;color:#94a3b8">Cargando trail de ' + codigo + '…</div></div>';
    document.body.appendChild(m);
    m.addEventListener('click', function(e){ if (e.target === m){ m.remove(); if(window._trailKeyh){document.removeEventListener('keydown',window._trailKeyh);window._trailKeyh=null;} } });
    window._trailKeyh = function(e){ var nv=window._trailNav||{}; if(e.key==='ArrowLeft'&&nv.prev){abastTrailMp(nv.prev);} else if(e.key==='ArrowRight'&&nv.next){abastTrailMp(nv.next);} else if(e.key==='Escape'){var mm=document.getElementById('modal-trail-mp'); if(mm)mm.remove(); document.removeEventListener('keydown',window._trailKeyh); window._trailKeyh=null;} };
    document.addEventListener('keydown', window._trailKeyh);
    try {
      const r = await fetch('/api/abastecimiento/trail-mp/' + encodeURIComponent(codigo));
      const d = await r.json();
      if (!r.ok || d.error) {
        m.querySelector('div').innerHTML = '<div style="color:#dc2626;padding:30px">Error: ' + (d.error || r.status) + '</div>';
        return;
      }
      if (d.es_mee) {
        // Trail de ENVASE (MEE) · productos que lo usan + lotes × unidades (kg×1000÷ml)
        let h = '<div style="display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #ece9f5;padding-bottom:14px;margin-bottom:14px">';
        h += '<div><h2 style="margin:0;font-size:18px;color:#1e293b">📦 ' + escapeHtmlNec(d.codigo_mp) + ' · ' + escapeHtmlNec(d.nombre_comercial||'') + '</h2>';
        h += '<div style="font-size:11px;color:#64748b;margin-top:3px">Envase · ' + (d.volumen_ml||0) + ' ml · lo usan ' + (d.productos_que_usan||[]).length + ' producto(s)</div></div>';
        h += _trailNavBtns() + '</div>';
        const th = d.total_unidades_por_horizonte||{};
        h += '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">';
        ['15','30','60','90','120','180','365'].forEach(k => { h += '<div style="background:#f4f2fb;border:1px solid #ece9f5;border-radius:10px;padding:8px 12px;text-align:center"><div style="font-size:16px;font-weight:800;color:#6d28d9">' + (Number(th[k])||0).toLocaleString("es-CO") + '</div><div style="font-size:9px;color:#94a3b8">' + k + 'd · uds</div></div>'; });
        h += '</div>';
        h += '<div style="font-size:12px;color:#475569;font-weight:700;margin-bottom:6px">Lotes que lo consumen · unidades = kg × <b>share</b> × 1000 ÷ ml</div>';
        h += '<div style="overflow:auto;border:1px solid #ece9f5;border-radius:12px"><table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:linear-gradient(180deg,#faf9ff,#f3f1fb);color:#6d28d9"><th style="text-align:left;padding:8px">Producto</th><th style="padding:8px">Fecha</th><th style="text-align:right;padding:8px">kg lote</th><th style="text-align:right;padding:8px" title="Porción del lote que va a ESTA presentación, por ventas">Share</th><th style="text-align:right;padding:8px">Unidades</th><th style="text-align:left;padding:8px">Origen</th></tr></thead><tbody>';
        (d.producciones||[]).forEach(p => { const shBad = (Number(p.share_pct)>=45 && Number(p.share_pct)<=55); h += '<tr style="border-top:1px solid #f1f5f9"><td style="padding:7px 8px">' + escapeHtmlNec(p.producto) + '</td><td style="padding:7px 8px;text-align:center">' + p.fecha + '</td><td style="padding:7px 8px;text-align:right">' + p.cantidad_kg + '</td><td style="padding:7px 8px;text-align:right;font-weight:700;color:' + (shBad?'#d97706':'#334155') + '">' + (Number(p.share_pct)||0) + '%' + (shBad?' ⚠️':'') + '</td><td style="padding:7px 8px;text-align:right;font-weight:700">' + (Number(p.unidades)||0).toLocaleString("es-CO") + '</td><td style="padding:7px 8px;color:#94a3b8;font-size:10px">' + escapeHtmlNec(p.origen||'') + '</td></tr>'; });
        if (!(d.producciones||[]).length) h += '<tr><td colspan="6" style="padding:20px;text-align:center;color:#94a3b8">Ningún lote futuro usa este envase (revisá el mapeo producto→envase en Presentaciones)</td></tr>';
        h += '</tbody></table></div>';
        if (d.nota) h += '<div style="font-size:10.5px;color:#94a3b8;margin-top:8px">' + escapeHtmlNec(d.nota) + '</div>';
        m.querySelector('div').innerHTML = h;
        return;
      }
      const stock = d.stock_actual_g || 0;
      const pend = d.pendiente_compras_g || 0;
      const consumo = d.total_consumo_365d_g || 0;
      const deficit = d.deficit_365d_g || 0;
      let html = '<div style="display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #e2e8f0;padding-bottom:14px;margin-bottom:14px">';
      html += '<div><h2 style="margin:0;font-size:18px;color:#1e293b">' + (d.codigo_mp) + ' · ' + escapeHtmlNec(d.nombre_inci || d.nombre_comercial || '') + '</h2>';
      if (d.nombre_comercial && d.nombre_comercial !== d.nombre_inci) html += '<div style="font-size:11px;color:#64748b;margin-top:3px">Comercial: ' + escapeHtmlNec(d.nombre_comercial) + '</div>';
      if (d.proveedor) html += '<div style="font-size:11px;color:#64748b">Proveedor: ' + escapeHtmlNec(d.proveedor) + '</div>';
      html += '</div>';
      html += _trailNavBtns();
      html += '</div>';
      // KPIs
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:18px">';
      html += '<div style="background:#f1f5f9;border-radius:8px;padding:12px;text-align:center"><div style="font-size:22px;font-weight:800;color:#1e293b">' + _fmtAba(stock) + ' g</div><div style="font-size:10px;color:#64748b;text-transform:uppercase">Stock actual</div></div>';
      html += '<div style="background:' + (pend>0?'#dbeafe':'#f1f5f9') + ';border-radius:8px;padding:12px;text-align:center"><div style="font-size:22px;font-weight:800;color:' + (pend>0?'#1e40af':'#475569') + '">' + _fmtAba(pend) + ' g</div><div style="font-size:10px;color:#64748b;text-transform:uppercase">En cola compras</div></div>';
      html += '<div style="background:#fefce8;border-radius:8px;padding:12px;text-align:center"><div style="font-size:22px;font-weight:800;color:#854d0e">' + _fmtAba(consumo) + ' g</div><div style="font-size:10px;color:#64748b;text-transform:uppercase">Consumo proyectado 365d</div></div>';
      html += '<div style="background:' + (deficit>0?'#fee2e2':'#f0fdf4') + ';border-radius:8px;padding:12px;text-align:center"><div style="font-size:22px;font-weight:800;color:' + (deficit>0?'#991b1b':'#15803d') + '">' + _fmtAba(deficit) + ' g</div><div style="font-size:10px;color:#64748b;text-transform:uppercase">Déficit 365d</div></div>';
      html += '</div>';

      // Productos que la usan
      const prods = d.productos || [];
      if (!prods.length) {
        html += '<div style="background:#fef3c7;border-left:4px solid #f59e0b;padding:14px;border-radius:8px;color:#92400e;font-size:13px"><b>⚠ Ningún producto en BD declara usar esta materia prima.</b><br>Revisá la fórmula maestra en formula_items.</div>';
      } else {
        html += '<h3 style="margin:8px 0 10px;color:#1e293b;font-size:14px">📋 Productos que la usan (' + prods.length + ') · ordenados por consumo proyectado</h3>';
        html += '<table style="width:100%;border-collapse:collapse;font-size:12px">';
        html += '<thead style="background:#f1f5f9"><tr>';
        html += '<th style="text-align:left;padding:8px;font-weight:700">Producto</th>';
        html += '<th style="text-align:right;padding:8px;font-weight:700" title="% de la MP en la fórmula">%</th>';
        html += '<th style="text-align:right;padding:8px;font-weight:700" title="Gramos de la MP por lote estándar del producto">g/lote</th>';
        html += '<th style="text-align:right;padding:8px;font-weight:700">Lote estándar (kg)</th>';
        html += '<th style="text-align:right;padding:8px;font-weight:700">Lotes futuros</th>';
        html += '<th style="text-align:right;padding:8px;font-weight:700;background:#fefce8">Consumo 365d (g)</th>';
        html += '</tr></thead><tbody>';
        prods.forEach(p => {
          const sin_lotes = p.n_lotes_futuros === 0;
          const bg = sin_lotes ? '#fafafa' : '#fff';
          const colorWarn = sin_lotes ? '#94a3b8' : '#1e293b';
          html += '<tr style="border-top:1px solid #e2e8f0;background:' + bg + '">';
          html += '<td style="padding:8px;color:' + colorWarn + ';font-weight:600">' + escapeHtmlNec(p.producto_nombre);
          if (sin_lotes) html += ' <span style="background:#fef3c7;color:#92400e;padding:1px 6px;border-radius:4px;font-size:10px;font-weight:700" title="Producto en BD pero sin lotes programados en próximos 365d">SIN LOTES</span>';
          html += '</td>';
          html += '<td style="padding:8px;text-align:right;font-family:ui-monospace">' + (p.porcentaje||0).toFixed(2) + '%</td>';
          html += '<td style="padding:8px;text-align:right;font-family:ui-monospace">' + _fmtAba(p.cantidad_g_por_lote) + '</td>';
          html += '<td style="padding:8px;text-align:right;font-family:ui-monospace">' + (p.lote_size_kg||0).toFixed(1) + '</td>';
          html += '<td style="padding:8px;text-align:right;font-family:ui-monospace;font-weight:700;color:' + (sin_lotes?'#dc2626':'#1e293b') + '">' + p.n_lotes_futuros + '</td>';
          html += '<td style="padding:8px;text-align:right;font-family:ui-monospace;background:#fefce8;font-weight:700">' + _fmtAba(p.gramos_total_365d) + '</td>';
          html += '</tr>';
          // Detalle expandible de lotes si los hay
          if (p.lotes_detalle && p.lotes_detalle.length) {
            html += '<tr><td colspan="6" style="padding:0;background:#fafafa">';
            html += '<details style="padding:8px 14px"><summary style="cursor:pointer;font-size:11px;color:#7c3aed">Ver ' + p.n_lotes_futuros + ' lote(s)…</summary>';
            html += '<table style="width:100%;font-size:11px;margin-top:6px"><thead><tr style="color:#64748b"><th style="text-align:left;padding:4px">Fecha</th><th style="text-align:left;padding:4px">Origen</th><th style="text-align:right;padding:4px">kg producción</th><th style="text-align:right;padding:4px">g consumidos</th></tr></thead><tbody>';
            p.lotes_detalle.forEach(l => {
              html += '<tr><td style="padding:3px 4px;font-family:ui-monospace">' + l.fecha + '</td>';
              html += '<td style="padding:3px 4px;font-size:10px">' + escapeHtmlNec(l.origen||'') + '</td>';
              html += '<td style="padding:3px 4px;text-align:right;font-family:ui-monospace">' + l.cantidad_kg.toFixed(1) + ' kg</td>';
              html += '<td style="padding:3px 4px;text-align:right;font-family:ui-monospace;color:#854d0e">' + _fmtAba(l.gramos) + '</td></tr>';
            });
            if (p.mas_lotes > 0) html += '<tr><td colspan="4" style="text-align:center;padding:6px;color:#94a3b8">… y ' + p.mas_lotes + ' lote(s) más</td></tr>';
            html += '</tbody></table></details></td></tr>';
          }
        });
        html += '</tbody></table>';

        // Diagnóstico
        const productos_sin_lotes = prods.filter(p => p.n_lotes_futuros === 0);
        if (productos_sin_lotes.length) {
          html += '<div style="background:#fef3c7;border-left:4px solid #f59e0b;border-radius:8px;padding:12px;margin-top:14px;font-size:12px;color:#92400e">';
          html += '<b>⚠ ' + productos_sin_lotes.length + ' producto(s) usa esta MP pero NO tiene lotes programados</b><br>';
          html += 'Esto explica por qué el consumo proyectado es bajo. Si esos productos van a producirse, programalos manualmente o ejecutá <a href="/admin/llenar-calendario" target="_blank" style="color:#7c3aed;font-weight:700">llenar calendario</a> con velocidad de ventas habilitada.';
          html += '</div>';
        }
      }
      m.querySelector('div').innerHTML = html;
    } catch(e) {
      m.querySelector('div').innerHTML = '<div style="color:#dc2626;padding:30px">Error red: ' + e.message + '</div>';
    }
  };

  function renderTablaAbast() {
    const div = document.getElementById('abast-contenido');
    const st = window._ABA_STATE;
    // Sebastián 25-may-2026 PM · filtrar por sub-pestaña activa (mp/mee)
    const tipoAct = st.tipoActivo || 'mp';
    const allItemsRaw = st.items || [];
    const allItems = allItemsRaw.filter(i => (i.tipo || '').toLowerCase() === tipoAct);
    // Contadores para info en el header
    const nMp = allItemsRaw.filter(i => (i.tipo||'').toLowerCase() === 'mp').length;
    const nMee = allItemsRaw.filter(i => (i.tipo||'').toLowerCase() === 'mee').length;
    const infoEl = document.getElementById('abast-tipo-info');
    if (infoEl) {
      infoEl.innerHTML = '🧪 <strong>' + nMp + '</strong> MP &middot; 📦 <strong>' + nMee + '</strong> MEE con déficit';
    }
    if (!allItems.length) {
      const otroTipoLbl = tipoAct === 'mp' ? 'MEE' : 'MP';
      const otroN = tipoAct === 'mp' ? nMee : nMp;
      let msg = '✓ Sin déficits de ' + (tipoAct === 'mp' ? 'Materia Prima' : 'Material de Envase') + ' · stock + pendiente cubre las producciones';
      if (otroN > 0) msg += '<br><span style="font-size:11px;margin-top:8px;display:inline-block">💡 Hay <strong>' + otroN + '</strong> ' + otroTipoLbl + ' con déficit · clickeá la otra pestaña arriba</span>';
      div.innerHTML = '<div style="text-align:center;color:#15803d;padding:30px;background:#f0fdf4;border-radius:8px;border:1px solid #bbf7d0">' + msg + '</div>';
      return;
    }

    // Filtros disponibles (solo del tipo activo)
    const proveedores = Array.from(new Set(allItems.map(i => i.proveedor_sugerido || '(sin proveedor)'))).sort();
    const urgencias = Array.from(new Set(allItems.map(i => i.urgencia))).sort();
    const items = _aplicarFiltros(allItems);

    // Barra de filtros + acciones
    // Barra de filtros PREMIUM (Sebastián 5-jul) · una sola línea limpia · sin el dropdown "MP+MEE" (ya está
    // el tab MP/MEE arriba · redundante). El filtro tipo queda en 'TODOS' (no oculta nada del tab activo).
    st.filtros.tipo = 'TODOS';
    const _abaSel = 'padding:8px 13px;border:1px solid #e6e1f2;border-radius:10px;font-size:12px;background:#fff;color:#334155;font-weight:600;cursor:pointer;outline:none;box-shadow:0 1px 2px rgba(16,15,45,.04)';
    let html = '<div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;background:linear-gradient(180deg,#fbfaff,#f4f2fb);padding:12px 14px;border:1px solid #ece9f5;border-radius:14px;margin-bottom:12px;box-shadow:0 1px 3px rgba(16,15,45,.05),0 14px 30px -20px rgba(16,15,45,.16);font-size:12px">';
    html += '<input type="text" id="abast-buscar" placeholder="🔍 Buscar código, nombre o proveedor…" value="' + escapeHtmlNec(st.filtros.busqueda) + '" oninput="_abastFiltroBusq(this.value)" style="flex:1;min-width:220px;padding:9px 15px;border:1px solid #e6e1f2;border-radius:11px;font-size:12.5px;background:#fff;outline:none;box-shadow:0 1px 2px rgba(16,15,45,.04)">';
    html += '<select data-campo="urgencia" onchange="_abastFiltro(this.dataset.campo,this.value)" style="' + _abaSel + '"><option value="TODAS">Urgencia · todas</option>';
    urgencias.forEach(u => {
      const sel = st.filtros.urgencia === u ? ' selected' : '';
      const cfg = _ABA_URG_COLORS[u] || {emoji:''};
      html += '<option value="' + u + '"' + sel + '>' + cfg.emoji + ' ' + u + '</option>';
    });
    html += '</select>';
    html += '<select data-campo="proveedor" onchange="_abastFiltro(this.dataset.campo,this.value)" style="' + _abaSel + ';max-width:230px"><option value="TODOS">Proveedor · todos</option>';
    proveedores.forEach(p => {
      const sel = st.filtros.proveedor === p ? ' selected' : '';
      html += '<option value="' + escapeHtmlNec(p) + '"' + sel + '>' + escapeHtmlNec(p) + '</option>';
    });
    html += '</select>';
    html += '<label style="display:flex;align-items:center;gap:6px;color:#64748b;font-weight:600">Cubrir <select id="abast-cubrir" onchange="_abastCubrir(this.value)" style="' + _abaSel + '">';
    (st.horizontes || []).forEach(h => {
      const sel = st.cubrir_dias === h ? ' selected' : '';
      html += '<option value="' + h + '"' + sel + '>' + h + 'd</option>';
    });
    html += '</select></label>';
    const _abaBtn = 'padding:9px 14px;border:0;border-radius:10px;font-size:12px;font-weight:700;cursor:pointer;box-shadow:0 3px 10px -3px rgba(16,15,45,.3);color:#fff';
    html += '<button onclick="_abastSelectVisibles(true)" style="padding:8px 12px;background:#fff;color:#64748b;border:1px solid #e6e1f2;border-radius:10px;font-size:11.5px;font-weight:600;cursor:pointer">☑ Todos</button>';
    html += '<button onclick="_abastSelectVisibles(false)" style="padding:8px 12px;background:#fff;color:#64748b;border:1px solid #e6e1f2;border-radius:10px;font-size:11.5px;font-weight:600;cursor:pointer">☐ Ninguno</button>';
    html += '<button onclick="_abastSelectBarco()" style="' + _abaBtn + ';background:linear-gradient(180deg,#0ea5e9,#0369a1)" title="Selecciona todas las MP que CONSUMEN 3 kg o más en 90 días y pone la cantidad a pedir = AÑO ENTERO (365d). Para importar por barco de una.">&#128674; &gt;3kg a 90d · pedir año</button>';
    html += '<span id="abast-sel-count" style="color:#7c3aed;font-weight:800"></span>';
    html += '<button onclick="_abastAbrirSolicitar()" style="' + _abaBtn + ';background:linear-gradient(180deg,#22c55e,#16a34a)">📩 Solicitar seleccionados</button>';
    html += '<button onclick="_abastExportExcel()" style="' + _abaBtn + ';background:linear-gradient(180deg,#3b82f6,#1e40af)" title="Déficit por horizonte (para jefe producción) · respeta filtros · 2 sheets: detalle + agrupado por proveedor">📊 Excel déficit</button>';
    html += '<button onclick="_abastExportConsumoBruto()" style="' + _abaBtn + ';background:linear-gradient(180deg,#10b981,#047857)" title="Consumo TOTAL en gramos/unidades sin restar inventario (para Alejandro · visión gerencial)">📦 Excel consumo</button>';
    html += '</div>';

    if (!items.length) {
      html += '<div style="text-align:center;color:#94a3b8;padding:30px">Sin items que coincidan con los filtros</div>';
      div.innerHTML = html;
      _abastActualizarContadorSel();
      return;
    }

    // Tabla
    html += '<div style="overflow-x:auto;background:white;border-radius:14px;border:1px solid #ece9f5;box-shadow:0 1px 3px rgba(16,15,45,.05),0 18px 40px -28px rgba(16,15,45,.2)">';
    html += '<table style="width:100%;border-collapse:collapse;font-size:12px;min-width:1100px">';
    html += '<thead><tr style="background:linear-gradient(180deg,#faf9ff,#f3f1fb);color:#6d28d9;border-bottom:1px solid #ece9f5">';
    html += '<th style="text-align:center;padding:8px;font-weight:700;width:32px"><input type="checkbox" onchange="_abastSelectVisibles(this.checked)"></th>';
    html += '<th style="text-align:left;padding:8px;font-weight:700">Código</th>';
    html += '<th style="text-align:left;padding:8px;font-weight:700">Nombre</th>';
    html += '<th style="text-align:center;padding:8px;font-weight:700">Tipo</th>';
    html += '<th style="text-align:left;padding:8px;font-weight:700">Proveedor</th>';
    html += '<th style="text-align:right;padding:8px;font-weight:700" title="Lead time del proveedor">LT</th>';
    html += '<th style="text-align:right;padding:8px;font-weight:700">Stock</th>';
    html += '<th style="text-align:right;padding:8px;font-weight:700">En cola</th>';
    html += '<th style="text-align:right;padding:8px;font-weight:700" title="Ya lleg&oacute; - esperando liberaci&oacute;n de Calidad">&#128300; Cuarentena</th>';
    (st.horizontes || []).forEach(h => {
      html += '<th style="text-align:right;padding:8px;font-weight:700;background:#f1f5f9">' + h + 'd</th>';
    });
    html += '<th style="text-align:center;padding:8px;font-weight:700">Urg</th>';
    html += '<th style="text-align:right;padding:8px;font-weight:700;background:#ecfdf5">Pedir</th>';
    html += '</tr></thead><tbody>';
    items.forEach((it, idx) => {
      const urg = _ABA_URG_COLORS[it.urgencia] || _ABA_URG_COLORS.OK;
      const rowBg = it.urgencia === 'CRITICO' ? '#fef2f2' : (it.urgencia === 'URGENTE' ? '#fff7ed' : 'white');
      const selData = st.seleccionados[it.codigo] || {};
      const checked = selData.marcado ? ' checked' : '';
      const cantidad = (selData.cantidad_override != null) ? selData.cantidad_override : _cantidadSugerida(it, st.cubrir_dias);
      html += '<tr data-cod="' + escapeHtmlNec(it.codigo) + '" style="border-top:1px solid #e2e8f0;background:' + rowBg + '">';
      html += '<td style="padding:6px 8px;text-align:center"><input type="checkbox" data-cod="' + escapeHtmlNec(it.codigo) + '"' + checked + ' onchange="_abastTogglePick(this)"></td>';
      // Código + badges SOL/OC
      let badgesHtml = '';
      const enCurso = it.solicitudes_en_curso || [];
      if (enCurso.length) {
        const sol = enCurso.filter(s => s.tipo === 'SOL').length;
        const oc = enCurso.filter(s => s.tipo === 'OC').length;
        const tip = enCurso.map(s => s.tipo + ' ' + s.numero + ' (' + s.estado + ')').join(' · ');
        badgesHtml = ' <span style="background:#dbeafe;color:#1e40af;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700" title="' + escapeHtmlNec(tip) + '">' + (sol?sol+' SOL ':'') + (oc?oc+' OC':'') + '</span>';
      }
      // FIX UX 24-may-2026 noche · click en código abre el trail · "tomar
      // producto por producto, enlazar formula e ir sumando · ver dónde
      // viene cada gramo del consumo".
      const codTrail = escapeHtmlNec(it.codigo);
      html += '<td style="padding:6px 8px;font-family:ui-monospace;font-weight:700">' +
        '<a href="#" onclick="abastTrailMp(this.dataset.cod);return false" data-cod="' + codTrail + '" style="color:#7c3aed;text-decoration:underline;cursor:pointer" title="Ver desglose · qué productos la usan y cuántos lotes futuros">' +
        codTrail + '</a>' + badgesHtml + '</td>';
      html += '<td style="padding:6px 8px"><a href="#" onclick="abastTrailMp(this.dataset.cod);return false" data-cod="' + codTrail + '" style="color:#1e293b;text-decoration:none;cursor:pointer;font-weight:600" title="Ver desglose">' + escapeHtmlNec(it.nombre_inci || it.nombre) + '</a>' + ((it.nombre_inci && it.nombre && it.nombre_inci !== it.nombre) ? '<div style="font-size:10px;color:#94a3b8">' + escapeHtmlNec(it.nombre) + '</div>' : '') + '</td>';
      html += '<td style="padding:6px 8px;text-align:center;font-size:10px;font-weight:700;color:' + (it.tipo==='MP'?'#7c3aed':'#7c3aed') + '">' + it.tipo + '</td>';
      html += '<td style="padding:6px 8px;color:#64748b">' + escapeHtmlNec(it.proveedor_sugerido || '—') + '</td>';
      // Lead time · si quiebre <= lead_time → advertencia roja (no llegará a tiempo)
      const lt = it.lead_time_dias || 14;
      const ltCol = (it.horizonte_quiebre_dias && it.horizonte_quiebre_dias <= lt) ? '#dc2626' : '#64748b';
      const ltTip = (it.horizonte_quiebre_dias && it.horizonte_quiebre_dias <= lt) ? 'Quiebre en ' + it.horizonte_quiebre_dias + 'd · LT ' + lt + 'd · ¡no llega a tiempo!' : 'Lead time del proveedor';
      html += '<td style="padding:6px 8px;text-align:right;color:' + ltCol + ';font-weight:' + (ltCol==='#dc2626'?'700':'400') + '" title="' + ltTip + '">' + lt + 'd</td>';
      const stockKey = it.tipo === 'MP' ? 'stock_actual_g' : 'stock_actual_u';
      const colaKey = it.tipo === 'MP' ? 'pendiente_compras_g' : 'pendiente_compras_u';
      const cuarKey = it.tipo === 'MP' ? 'cuarentena_g' : 'cuarentena_u';
      const unit = it.tipo === 'MP' ? 'g' : 'u';
      html += '<td style="padding:6px 8px;text-align:right;font-family:ui-monospace">' + _fmtAba(it[stockKey]) + (it[stockKey]?' '+unit:'') + '</td>';
      html += '<td style="padding:6px 8px;text-align:right;font-family:ui-monospace;color:' + (it[colaKey]>0?'#15803d':'#94a3b8') + '">' + _fmtAba(it[colaKey]) + (it[colaKey]?' '+unit:'') + '</td>';
      html += '<td style="padding:6px 8px;text-align:right;font-family:ui-monospace;color:' + (it[cuarKey]>0?'#b45309':'#cbd5e1') + (it[cuarKey]>0?';font-weight:700':'') + '" title="' + (it[cuarKey]>0?'Ya lleg&oacute; - esperando liberaci&oacute;n de Calidad (cuarentena)':'') + '">' + (it[cuarKey]>0?('&#128300; '+_fmtAba(it[cuarKey])+' '+unit):'&mdash;') + '</td>';
      (st.horizontes || []).forEach(h => {
        const def = it.deficit[String(h)] || 0;
        const cons = it.consumo[String(h)] || 0;
        const cellBg = def > 0.01 ? (h<=15?'#fee2e2':h<=30?'#fff7ed':h<=90?'#fefce8':'#eff6ff') : '';
        const cellTc = def > 0.01 ? '#991b1b' : '#94a3b8';
        html += '<td style="padding:6px 8px;text-align:right;font-family:ui-monospace;background:' + cellBg + ';color:' + cellTc + ';font-weight:' + (def>0.01?'700':'400') + '" title="Consumo ' + h + 'd: ' + _fmtAba(cons) + ' ' + unit + '">' + _fmtAba(def) + '</td>';
      });
      html += '<td style="padding:6px 8px;text-align:center;font-size:16px" title="' + urg.text + '">' + urg.emoji + '</td>';
      // Pedir: input editable · sugerencia automática
      html += '<td style="padding:4px;background:#ecfdf5"><input type="number" min="0" data-cod="' + escapeHtmlNec(it.codigo) + '" value="' + (cantidad || 0) + '" onchange="_abastCantidad(this)" style="width:80px;padding:4px 6px;border:1px solid #86efac;border-radius:4px;font-family:ui-monospace;font-size:12px;text-align:right"></td>';
      html += '</tr>';
    });
    html += '</tbody></table></div>';
    html += '<div style="font-size:11px;color:#64748b;margin-top:10px">💡 <strong>Cómo usar:</strong> ① Marca check de las filas que quieres solicitar (la columna "Pedir" sugiere cantidad para cubrir los días seleccionados) ② Ajusta cantidad si querés ③ Click "📩 Solicitar seleccionados" → crea SOLs agrupadas por proveedor. Si el LT del proveedor es mayor al horizonte de quiebre, aparece en rojo: pedí YA.</div>';
    div.innerHTML = html;
    _abastActualizarContadorSel();
  }

  function _abastFiltroBusq(v) {
    window._ABA_STATE.filtros.busqueda = v;
    renderTablaAbast();
  }
  function _abastFiltro(campo, valor) {
    window._ABA_STATE.filtros[campo] = valor;
    renderTablaAbast();
  }
  function _abastCubrir(v) {
    window._ABA_STATE.cubrir_dias = parseInt(v, 10);
    renderTablaAbast();
  }
  function _abastTogglePick(checkbox) {
    const cod = checkbox.dataset.cod;
    const st = window._ABA_STATE;
    if (!st.seleccionados[cod]) st.seleccionados[cod] = {marcado: false};
    st.seleccionados[cod].marcado = checkbox.checked;
    _abastActualizarContadorSel();
  }
  function _abastCantidad(input) {
    const cod = input.dataset.cod;
    const st = window._ABA_STATE;
    if (!st.seleccionados[cod]) st.seleccionados[cod] = {marcado: false};
    st.seleccionados[cod].cantidad_override = parseFloat(input.value) || 0;
  }
  function _abastSelectVisibles(check) {
    const st = window._ABA_STATE;
    const visibles = _aplicarFiltros(st.items);
    visibles.forEach(it => {
      if (!st.seleccionados[it.codigo]) st.seleccionados[it.codigo] = {};
      st.seleccionados[it.codigo].marcado = check;
    });
    renderTablaAbast();
  }
  // 🚢 Pedido por BARCO · Sebastián 24-jun: seleccionar las MP que CONSUMEN >=3 kg en 90 días
  // y poner la cantidad a pedir = consumo de 1 AÑO + % de aumento por ventas − stock − en cola.
  function _abastSelectBarco() {
    const st = window._ABA_STATE;
    const resp = prompt(
      'Pedido por BARCO\n\n' +
      'Selecciona las MP que CONSUMEN 3 kg o más en 90 días y calcula cuánto pedir para el AÑO ENTERO (365 días) + un % de aumento por crecimiento de ventas.\n\n' +
      '¿Qué % de aumento por ventas querés aplicar? (0 = sin aumento)', '20');
    if (resp === null) return; // canceló
    const growth = Math.max(0, parseFloat(resp) || 0) / 100;
    const UMBRAL_G = 3000; // 3 kg en 90 días
    st.cubrir_dias = 365;
    const selEl = document.getElementById('abast-cubrir');
    if (selEl) selEl.value = '365';
    const visibles = _aplicarFiltros(st.items);
    let n = 0, totalG = 0;
    visibles.forEach(it => {
      if (it.tipo !== 'MP') return; // el corte de 3 kg es para materia prima (gramos)
      const c90 = (it.consumo && Number(it.consumo['90'])) || 0;
      if (c90 < UMBRAL_G) return;
      const c365 = (it.consumo && Number(it.consumo['365'])) || 0;
      const stock = Number(it.stock_actual_g) || 0;
      const enCola = Number(it.pendiente_compras_g) || 0;
      const cuar = Number(it.cuarentena_g) || 0;   // FIX 5-jul · acreditar cuarentena (igual que el déficit normal)
      const pedir = Math.max(0, Math.round(c365 * (1 + growth) - stock - enCola - cuar));
      if (!st.seleccionados[it.codigo]) st.seleccionados[it.codigo] = {};
      st.seleccionados[it.codigo].marcado = true;
      st.seleccionados[it.codigo].cantidad_override = pedir;
      n++; totalG += pedir;
    });
    renderTablaAbast();
    alert('Barco: ' + n + ' MP seleccionadas (consumo >=3 kg en 90 dias).\n\n' +
          'Cantidad a pedir = consumo de 1 ano' + (growth > 0 ? ' +' + Math.round(growth*100) + '% por ventas' : '') +
          ' - stock - en cola.\nTotal a pedir: ' + Math.round(totalG).toLocaleString() + ' g (' + (totalG/1000).toFixed(1) + ' kg).\n\n' +
          'Revisa la columna "Pedir" y dale "Solicitar seleccionados".');
  }
  function _abastActualizarContadorSel() {
    const st = window._ABA_STATE;
    const n = Object.values(st.seleccionados).filter(s => s.marcado).length;
    const el = document.getElementById('abast-sel-count');
    if (el) el.textContent = n > 0 ? ('· ' + n + ' seleccionado(s)') : '';
  }
  function _abastBuildExportParams() {
    const st = window._ABA_STATE;
    const tipos = [];
    if (document.getElementById('abast-mp').checked) tipos.push('mp');
    if (document.getElementById('abast-mee').checked) tipos.push('mee');
    const modoSel = document.getElementById('abast-modo');
    const modo = (modoSel && modoSel.value) || 'comprometido';
    const params = new URLSearchParams();
    params.set('modo', modo);
    if (tipos.length) params.set('tipo', tipos.join(','));
    if (st.filtros.busqueda) params.set('busqueda', st.filtros.busqueda);
    if (st.filtros.urgencia !== 'TODAS') params.set('urgencia', st.filtros.urgencia);
    if (st.filtros.proveedor !== 'TODOS') params.set('proveedor', st.filtros.proveedor);
    if (st.filtros.tipo !== 'TODOS') params.set('tipo_filtro', st.filtros.tipo);
    return params.toString();
  }

  function _abastExportExcel() {
    window.open('/api/abastecimiento/export-excel?' + _abastBuildExportParams(), '_blank');
  }

  function _abastExportConsumoBruto() {
    window.open('/api/abastecimiento/consumo-bruto-excel?' + _abastBuildExportParams(), '_blank');
  }

  async function _abastAbrirSolicitar() {
    const st = window._ABA_STATE;
    const items = [];
    st.items.forEach(it => {
      const sel = st.seleccionados[it.codigo];
      if (!sel || !sel.marcado) return;
      const cant = (sel.cantidad_override != null) ? sel.cantidad_override : _cantidadSugerida(it, st.cubrir_dias);
      if (cant <= 0) return;
      items.push({
        tipo: it.tipo.toLowerCase(),
        codigo: it.codigo,
        cantidad: cant,
        proveedor_sugerido: it.proveedor_sugerido,
      });
    });
    if (!items.length) { alert('Selecciona al menos 1 item con cantidad > 0'); return; }
    if (!confirm('Crear SOL(s) agrupadas por proveedor con ' + items.length + ' item(s)?\n\nCubrir días: ' + st.cubrir_dias + 'd · urgencia: Normal')) return;
    // FIX 1-jun-2026 audit Abastecimiento (P1) · guard anti-doble-orden · evita que
    // un doble-click cree las SOLs dos veces (×2 compra). Re-entrada bloqueada.
    if (window._abastSolicitando) { return; }
    window._abastSolicitando = true;
    try {
      const r = await fetch('/api/abastecimiento/solicitar-items', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          items: items,
          agrupar_por_proveedor: true,
          urgencia: 'Normal',
          cubrir_dias: st.cubrir_dias,
        }),
      });
      const d = await r.json();
      if (r.status === 401) { window.location.href='/login'; return; }
      if (!r.ok || d.error) { alert('Error: ' + (d.error || ('HTTP '+r.status))); return; }
      alert('✓ ' + d.mensaje + '\n\n' + (d.creadas || []).map(c => c.numero + ' · ' + c.proveedor + ' (' + c.total_items + ' items)').join('\n'));
      cargarAbastecimiento();  // refresh
    } catch(e) {
      alert('Error red: ' + e.message);
    } finally {
      window._abastSolicitando = false;
    }
  }

  // FIX 23-may-2026 · Sebastián · botón Auto-sugerir producciones
  // · cron diario 5 AM también lo hace · este botón es disparador manual
  async function autoSugerirProducciones() {
    if (!confirm('¿Crear producciones Sugeridas en el calendario para los productos que se van a quebrar?\n\n' +
                  'Usa velocidad real de ventas + cobertura · genera lotes con origen=Sugerida (eos_canonico) · ' +
                  'puedes arrastrarlas para Fijarlas · respeta lo Fijo (NO toca)')) return;
    try {
      const r = await fetch('/api/plan/auto-programar-sugeridas', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({dias_horizonte: 90, cob_critico: 20, cob_alerta: 25}),
      });
      if (r.status === 401) { window.location.href='/login'; return; }
      const d = await r.json();
      if (!r.ok || d.error) {
        alert('Error: ' + (d.error || ('HTTP '+r.status)));
        return;
      }
      const detalle = (d.creados || []).map(c =>
        '  · ' + c.producto + ' · ' + c.fecha + ' · ' + c.cantidad_kg + 'kg (' + c.urgencia + ')'
      ).join('\n');
      // Cuando no se crea nada, mostrar razones de salto para diagnóstico
      const razones = (d.saltados || []).slice(0, 10).map(s =>
        '  · ' + (s.producto || '?') + (s.fecha ? ' [' + s.fecha + ']' : '') + ' → ' + (s.razon || '')
      ).join('\n');
      const mas = (d.saltados || []).length > 10 ? '\n  ... y ' + ((d.saltados || []).length - 10) + ' más' : '';
      const cuerpo = d.n_creados > 0
        ? '✓ ' + d.n_creados + ' Sugerida(s) creada(s):\n\n' + detalle +
          (d.n_saltados ? '\n\nSaltados: ' + d.n_saltados : '')
        : '⚠ No se creó ninguna Sugerida\n\nSaltados: ' + d.n_saltados +
          (razones ? '\n\nRazones:\n' + razones + mas : '');
      alert(cuerpo);
      cargarNecesidades();
    } catch(e) {
      alert('Error red: ' + e.message);
    }
  }

  // FIX 23-may-2026 PM Sebastián · "no me deja [consola], no hay otra
  // forma que tú lo hagas". Botones de mantenimiento desde la UI ·
  // limpiar Sugeridas viejas + listar/arreglar productos con
  // lote_size_kg absurdo · todo desde el navegador sin tocar consola.
  // FIX UX 24-may-2026 PM · Modal Herramientas con sidebar · antes 6
  // secciones apiladas creaban wall-of-options · ahora sidebar izq con
  // 6 tabs + pane derecho con 1 sección visible.
  window.mostrarTabHerr = function(idx) {
    document.querySelectorAll('.herr-tab').forEach(t => t.style.display = 'none');
    document.querySelectorAll('.herr-tab-btn').forEach(b => {
      b.style.background = 'transparent';
      b.style.color = '#475569';
      b.style.fontWeight = '600';
    });
    const tab = document.getElementById('herr-tab-' + idx);
    if (tab) tab.style.display = 'block';
    const btn = document.getElementById('herr-tab-btn-' + idx);
    if (btn) {
      btn.style.background = '#6d28d9';
      btn.style.color = '#fff';
      btn.style.fontWeight = '800';
    }
  };
  window.abrirHerramientasLimpieza = function() {
    let m = document.getElementById('modal-herramientas');
    if (m) m.remove();
    m = document.createElement('div');
    m.id = 'modal-herramientas';
    m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
    const TABS = [
      {n:1, label:'Limpiar Sugeridas', emoji:'🗑'},
      {n:2, label:'Lote_size absurdo', emoji:'⚖'},
      {n:3, label:'Huérfanos vendiendo', emoji:'🔍'},
      {n:4, label:'Re-mapear SKU', emoji:'↻'},
      {n:5, label:'Desactivar producto', emoji:'✕'},
      {n:6, label:'ml a todos SKUs', emoji:'✏️'},
      {n:7, label:'Envases B2B (whitelist)', emoji:'🤝'},
      {n:8, label:'Variantes fórmula', emoji:'🧪'},
      {n:9, label:'Llenar calendario 365d', emoji:'📅'},
    ];
    const sidebarHtml = TABS.map(t =>
      '<button id="herr-tab-btn-' + t.n + '" class="herr-tab-btn" onclick="mostrarTabHerr(' + t.n + ')" style="display:block;width:100%;text-align:left;background:transparent;color:#475569;border:none;border-left:3px solid transparent;padding:11px 14px;font-size:12px;font-weight:600;cursor:pointer;border-radius:0">' +
        '<span style="font-size:14px;margin-right:8px">' + t.emoji + '</span>' + t.n + '. ' + t.label +
      '</button>'
    ).join('');

    m.innerHTML = '<div style="background:#fff;border-radius:12px;max-width:980px;width:100%;max-height:90vh;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.25);display:flex;flex-direction:column">' +
      '<div style="padding:16px 22px;border-bottom:1px solid #e5e7eb;display:flex;align-items:center;justify-content:space-between;flex-shrink:0">' +
        '<h3 style="margin:0;font-size:16px;color:#1e293b">⚙ Herramientas de mantenimiento</h3>' +
        '<button onclick="document.getElementById(\'modal-herramientas\').remove()" style="background:#e5e7eb;color:#475569;border:none;width:32px;height:32px;border-radius:50%;font-size:18px;cursor:pointer">×</button>' +
      '</div>' +
      '<div style="display:flex;flex:1;overflow:hidden">' +
        // SIDEBAR izq
        '<div style="width:230px;background:#f1f5f9;border-right:1px solid #e2e8f0;padding:10px 0;overflow-y:auto;flex-shrink:0">' +
          sidebarHtml +
        '</div>' +
        // PANE der
        '<div style="flex:1;padding:18px 22px;overflow-y:auto">' +
        '<div style="background:#fef3c7;border-left:4px solid #f59e0b;border-radius:6px;padding:10px 14px;margin-bottom:14px;font-size:11px;color:#92400e">⚠ Estas acciones son reversibles (soft-cancel) pero modifican producción · ejecuta solo si entendés lo que hacés.</div>' +
        // Tab 1 · Limpiar Sugeridas
        '<div id="herr-tab-1" class="herr-tab" style="display:block">' +
          '<div style="font-weight:700;color:#1e293b;font-size:14px;margin-bottom:4px">🗑 Limpiar Sugeridas viejas del calendario</div>' +
          '<div style="font-size:12px;color:#64748b;margin-bottom:12px">Cancela producciones origen=Sugerida con fecha posterior al corte · NO toca Fijo (lo que vos pusiste manualmente).</div>' +
          '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px">' +
            '<label style="font-size:11px;color:#475569">Conservar hasta:</label>' +
            '<input id="herr-desde" type="date" value="2026-06-07" style="padding:5px 8px;border:1px solid #cbd5e1;border-radius:5px;font-size:12px">' +
          '</div>' +
          '<div style="display:flex;gap:8px;flex-wrap:wrap">' +
            '<button onclick="herrDryRun()" style="background:#7c3aed;color:#fff;border:none;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">🔍 Ver qué se cancelaría</button>' +
            '<button onclick="herrAplicar()" style="background:#dc2626;color:#fff;border:none;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">🗑 Aplicar limpieza</button>' +
          '</div>' +
          '<div id="herr-resultado-limpieza" style="margin-top:12px;font-size:11px;color:#64748b"></div>' +
        '</div>' +
        // Tab 2 · Productos con lote absurdo
        '<div id="herr-tab-2" class="herr-tab" style="display:none">' +
          '<div style="font-weight:700;color:#1e293b;font-size:14px;margin-bottom:4px">⚖ Productos con lote_size_kg absurdo (&lt;1 kg)</div>' +
          '<div style="font-size:12px;color:#64748b;margin-bottom:12px">Caso AZ HIBRID CLEAR: BD tenía 0.1 kg → planificador sugería 23 lotes diarios · arreglar aquí.</div>' +
          '<button onclick="herrListarSospechosos()" style="background:#6d28d9;color:#fff;border:none;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">📋 Listar sospechosos</button>' +
          '<div id="herr-resultado-sospechosos" style="margin-top:12px"></div>' +
        '</div>' +
        // Tab 3 · SKUs huérfanos
        '<div id="herr-tab-3" class="herr-tab" style="display:none">' +
          '<div style="font-weight:700;color:#1e293b;font-size:14px;margin-bottom:4px">🔍 SKUs vendiendo sin mapeo (huérfanos)</div>' +
          '<div style="font-size:12px;color:#64748b;margin-bottom:12px">Caso BHA: LBHA + CRB3BHA vendían sin map · reportaba 300/mes cuando real es 1280/mes (4×). Mapealos a su producto.</div>' +
          '<button onclick="herrListarHuerfanos()" style="background:#7c3aed;color:#fff;border:none;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">🔍 Listar huérfanos top</button>' +
          '<div id="herr-resultado-huerfanos" style="margin-top:12px"></div>' +
        '</div>' +
        // Tab 4 · Re-mapear SKU
        '<div id="herr-tab-4" class="herr-tab" style="display:none">' +
          '<div style="font-weight:700;color:#1e293b;font-size:14px;margin-bottom:4px">↻ Re-mapear SKU a otro producto</div>' +
          '<div style="font-size:12px;color:#64748b;margin-bottom:12px">Para corregir mapeos mal hechos · ej. SERUM-BT-001 estaba en LIP SERUM (PIB CHINO) cuando es BOOSTER TENSOR.</div>' +
          '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px">' +
            '<input id="herr-rm-sku" type="text" placeholder="SKU exacto (ej. SERUM-BT-001)" style="flex:1;min-width:180px;padding:6px 10px;border:1px solid #cbd5e1;border-radius:5px;font-size:12px;text-transform:uppercase">' +
            '<input id="herr-rm-prod" type="text" placeholder="Producto destino (formula_headers)" list="herr-rm-prod-list" style="flex:2;min-width:220px;padding:6px 10px;border:1px solid #cbd5e1;border-radius:5px;font-size:12px">' +
            '<datalist id="herr-rm-prod-list"></datalist>' +
            '<button onclick="herrRemapearSku()" style="background:#7c3aed;color:#fff;border:none;padding:6px 14px;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer">↻ Re-mapear</button>' +
          '</div>' +
          '<div id="herr-resultado-remap" style="font-size:11px;color:#64748b"></div>' +
        '</div>' +
        // Tab 5 · Desactivar producto
        '<div id="herr-tab-5" class="herr-tab" style="display:none">' +
          '<div style="font-weight:700;color:#1e293b;font-size:14px;margin-bottom:4px">✕ Desactivar producto (ya no se vende)</div>' +
          '<div style="font-size:12px;color:#64748b;margin-bottom:12px">Marca activo=0 · sale de Necesidades + Calendar · NO se borra (preserva histórico).</div>' +
          '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px">' +
            '<input id="herr-dz-prod" type="text" placeholder="Producto a desactivar (autocomplete)" list="herr-rm-prod-list" style="flex:1;min-width:260px;padding:6px 10px;border:1px solid #cbd5e1;border-radius:5px;font-size:12px">' +
            '<button onclick="herrDesactivarProd()" style="background:#dc2626;color:#fff;border:none;padding:6px 14px;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer">✕ Desactivar</button>' +
            '<button onclick="herrActivarProd()" style="background:#6d28d9;color:#fff;border:none;padding:6px 14px;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer">↻ Reactivar</button>' +
          '</div>' +
          '<div id="herr-resultado-dz" style="font-size:11px;color:#64748b"></div>' +
        '</div>' +
        // Tab 6 · ml a todos
        '<div id="herr-tab-6" class="herr-tab" style="display:none">' +
          '<div style="font-weight:700;color:#1e293b;font-size:14px;margin-bottom:4px">✏️ Fijar ml/gramos del envase a TODOS los SKUs</div>' +
          '<div style="font-size:12px;color:#64748b;margin-bottom:12px">Ej. BLUSH BALM = 6g por unidad · aplica a todos los SKUs del producto (BB101, BB201, BB301, BB401, BBM). Útil cuando ml está inferido por nombre y todos los tonos tienen el mismo formato.</div>' +
          '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px">' +
            '<input id="herr-mlt-prod" type="text" placeholder="Producto (autocomplete)" list="herr-rm-prod-list" style="flex:1;min-width:240px;padding:6px 10px;border:1px solid #cbd5e1;border-radius:5px;font-size:12px">' +
            '<input id="herr-mlt-ml" type="number" min="1" max="5000" step="0.1" placeholder="ml o g" style="width:90px;padding:6px 8px;border:1px solid #cbd5e1;border-radius:5px;font-size:12px">' +
            '<button onclick="herrFijarMlTodos()" style="background:#f59e0b;color:#fff;border:none;padding:6px 14px;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer">✏️ Aplicar a todos</button>' +
          '</div>' +
          '<div id="herr-resultado-mlt" style="font-size:11px;color:#64748b"></div>' +
        '</div>' +
        // Tab 7 · Envases B2B (whitelist por cliente)
        '<div id="herr-tab-7" class="herr-tab" style="display:none">' +
          '<div style="font-weight:700;color:#1e293b;font-size:14px;margin-bottom:4px">🤝 Envases permitidos por cliente B2B</div>' +
          '<div style="font-size:12px;color:#64748b;margin-bottom:12px">Define qué envases puede pedir cada cliente B2B desde el portal. Default permisivo: sin whitelist → ve todos los envases activos. Con whitelist → solo los que selecciones.</div>' +
          '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px">' +
            '<input id="herr-cli-id" type="text" placeholder="cliente_id (ej. FERN)" style="flex:1;min-width:180px;padding:6px 10px;border:1px solid #cbd5e1;border-radius:5px;font-size:12px;text-transform:uppercase">' +
            '<button onclick="herrCliEnvasesLoad()" style="background:#7c3aed;color:#fff;border:none;padding:6px 14px;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer">🔍 Cargar</button>' +
          '</div>' +
          '<div id="herr-cli-envases-out" style="margin-top:10px"></div>' +
        '</div>' +
        // Tab 9 · Diag calendario + llenar Sugeridas a 365d
        '<div id="herr-tab-9" class="herr-tab" style="display:none">' +
          '<div style="font-weight:700;color:#1e293b;font-size:14px;margin-bottom:4px">📅 Cobertura del calendario + llenar a 365d</div>' +
          '<div style="font-size:12px;color:#64748b;margin-bottom:12px">Verificá hasta qué fecha llega el calendario actual. Si está corto, dispará el cron auto-sugerir manualmente para llenarlo a 1 año (el cron diario corre 5 AM).</div>' +
          '<div style="display:flex;gap:8px;margin-bottom:12px">' +
            '<button onclick="herrDiagCalendario()" style="background:#7c3aed;color:#fff;border:none;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">🔍 Diagnosticar cobertura</button>' +
            '<button onclick="herrLlenarCalendario()" style="background:#7c3aed;color:#fff;border:none;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">🚀 Llenar a 365d ahora</button>' +
          '</div>' +
          '<div id="herr-cal-out" style="margin-top:10px"></div>' +
        '</div>' +
        // Tab 8 · Variantes de fórmula (agrupar canónico)
        '<div id="herr-tab-8" class="herr-tab" style="display:none">' +
          '<div style="font-weight:700;color:#1e293b;font-size:14px;margin-bottom:4px">🧪 Variantes de fórmula (producto canónico)</div>' +
          '<div style="font-size:12px;color:#64748b;margin-bottom:12px">Agrupa N fórmulas bajo un nombre canónico. Ej: LIP SERUM (canónico) = LIP SERUM PIB CHINO + LIP SERUM PIB LOCAL. El sistema escoge automáticamente la variante con más stock MP cuando se programa.</div>' +
          '<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:6px;padding:8px 10px;margin-bottom:12px;font-size:11px;color:#92400e">⚠ Requiere que las variantes ya existan en formula_headers como filas separadas. Solo agrupa por canónico, no crea fórmulas nuevas.</div>' +
          '<div style="margin-bottom:10px"><label style="font-size:11px;color:#475569;display:block;margin-bottom:3px">Nombre canónico</label>' +
            '<input id="herr-var-canonico" type="text" placeholder="LIP SERUM" style="width:100%;padding:6px 10px;border:1px solid #cbd5e1;border-radius:5px;font-size:12px">' +
          '</div>' +
          '<div id="herr-var-rows" style="margin-bottom:10px"></div>' +
          '<button onclick="herrVarAddRow()" style="background:#f1f5f9;color:#475569;border:1px dashed #cbd5e1;padding:6px 14px;border-radius:5px;font-size:11px;cursor:pointer;margin-right:8px">+ Agregar variante</button>' +
          '<button onclick="herrVarGuardar()" style="background:#7c3aed;color:#fff;border:none;padding:7px 16px;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer">💾 Guardar agrupación</button>' +
          '<div style="margin-top:14px"><label style="font-size:11px;color:#475569;display:block;margin-bottom:3px">🔍 Ver selección óptima actual</label>' +
            '<div style="display:flex;gap:8px;align-items:center">' +
              '<input id="herr-var-test-canonico" type="text" placeholder="canónico a evaluar" style="flex:1;padding:6px 10px;border:1px solid #cbd5e1;border-radius:5px;font-size:12px">' +
              '<input id="herr-var-test-kg" type="number" value="10" min="0.1" step="0.1" style="width:80px;padding:6px 8px;border:1px solid #cbd5e1;border-radius:5px;font-size:12px">' +
              '<button onclick="herrVarEvaluar()" style="background:#6d28d9;color:#fff;border:none;padding:6px 12px;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer">🧮 Evaluar</button>' +
            '</div>' +
          '</div>' +
          '<div id="herr-var-out" style="margin-top:10px;font-size:11px"></div>' +
        '</div>' +
        '</div>' +
      '</div>' +
      '</div>';
    document.body.appendChild(m);
    mostrarTabHerr(1);
    // Pre-cargar lista de productos para el datalist (re-map)
    (async function() {
      try {
        const r = await fetch('/api/admin/skus-huerfanos-top?limit=1');
        const d = await r.json();
        const dl = document.getElementById('herr-rm-prod-list');
        if (dl && d.productos_disponibles) {
          dl.innerHTML = d.productos_disponibles.map(p => '<option value="' + p.replace(/"/g,'&quot;') + '">').join('');
        }
      } catch(e) {}
    })();
  };
  // FIX 23-may-PM Sebastián · "SERUM-BT-001 ya lo tienes pero no lo
  // estabamos asociando" · re-mapear SKU existente vía bulk endpoint
  // (UPSERT) sin tener que pasar por consola del navegador.
  window.herrRemapearSku = async function() {
    const sku = (document.getElementById('herr-rm-sku').value || '').trim().toUpperCase();
    const prod = (document.getElementById('herr-rm-prod').value || '').trim();
    const out = document.getElementById('herr-resultado-remap');
    if (!sku || !prod) { out.innerHTML = '<span style="color:#dc2626">SKU y producto requeridos</span>'; return; }
    if (!confirm('¿Re-mapear SKU ' + sku + ' → ' + prod + '?\n\n(Si ya estaba mapeado, sobrescribe.)')) return;
    out.innerHTML = 'Aplicando…';
    try {
      const r = await fetch('/api/admin/sku-producto-map/bulk', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({items:[{sku, producto_nombre: prod}]}),
      });
      const d = await r.json();
      if (!r.ok || d.error) { out.innerHTML = '<span style="color:#dc2626">Error: ' + (d.error || r.status) + '</span>'; return; }
      if (d.n_errores > 0) {
        out.innerHTML = '<span style="color:#dc2626">Error: ' + JSON.stringify(d.errores[0]) + '</span>';
        return;
      }
      out.innerHTML = '<span style="color:#6d28d9;font-weight:700">✓ SKU ' + sku + ' → ' + prod + ' (' + d.creados[0].sku + ')</span>';
      document.getElementById('herr-rm-sku').value = '';
      document.getElementById('herr-rm-prod').value = '';
    } catch(e) { out.innerHTML = '<span style="color:#dc2626">Error red: ' + e.message + '</span>'; }
  };
  // Sección 6 · Fijar ml a todos los SKUs del producto
  window.herrFijarMlTodos = async function() {
    const prod = (document.getElementById('herr-mlt-prod').value || '').trim();
    const ml = parseFloat(document.getElementById('herr-mlt-ml').value);
    const out = document.getElementById('herr-resultado-mlt');
    if (!prod || !ml || ml <= 0 || ml > 5000) {
      out.innerHTML = '<span style="color:#dc2626">Producto y ml (1-5000) requeridos</span>';
      return;
    }
    if (!confirm('¿Aplicar ' + ml + ' ml/g a TODOS los SKUs activos de "' + prod + '"?')) return;
    try {
      const r = await fetch('/api/admin/ml-fix-todos-skus', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({producto_nombre: prod, volumen_ml: ml}),
      });
      const d = await r.json();
      if (!r.ok || d.error) { out.innerHTML = '<span style="color:#dc2626">Error: ' + (d.error || r.status) + '</span>'; return; }
      out.innerHTML = '<span style="color:#6d28d9;font-weight:700">✓ ' + d.n_skus + ' SKU(s) actualizados a ' + d.volumen_ml + 'ml/g para ' + d.producto_nombre + '</span>';
      document.getElementById('herr-mlt-prod').value = '';
      document.getElementById('herr-mlt-ml').value = '';
    } catch(e) { out.innerHTML = '<span style="color:#dc2626">Error red: ' + e.message + '</span>'; }
  };
  // Tab 9 · Diagnóstico cobertura + llenar Sugeridas a 365d
  window.herrDiagCalendario = async function() {
    const out = document.getElementById('herr-cal-out');
    out.innerHTML = 'Calculando…';
    try {
      const r = await fetch('/api/admin/diag-cobertura-calendario');
      const d = await r.json();
      if (!r.ok || d.error) { out.innerHTML = '<span style="color:#dc2626">Error: ' + (d.error || r.status) + '</span>'; return; }
      const bg = d.cobertura_dias_real >= 360 ? '#f0fdf4' : '#fef3c7';
      const bordr = d.cobertura_dias_real >= 360 ? '#16a34a' : '#f59e0b';
      let html = '<div style="background:' + bg + ';border-left:4px solid ' + bordr + ';padding:10px 14px;border-radius:6px;margin-bottom:12px">' +
        '<div style="font-size:13px;color:#1e293b"><strong>' + d.total_lotes_futuros + ' lotes</strong> programados desde hoy hasta <strong>' + (d.fecha_ultimo_lote || '—') + '</strong> · ' + d.kg_total_proyectado + ' kg totales</div>' +
        '<div style="font-size:11px;color:#475569;margin-top:4px">Cobertura real: <strong>' + d.cobertura_dias_real + 'd</strong> de 365d · boquete: <strong>' + d.boquete_dias + 'd</strong></div>' +
        '<div style="font-size:11px;color:#475569;margin-top:6px;font-style:italic">' + (d.recomendacion || '') + '</div>' +
        '</div>';
      const orig = d.por_origen || {};
      const meses = d.por_mes || {};
      html += '<div style="display:flex;gap:14px;flex-wrap:wrap">';
      html += '<div style="flex:1;min-width:220px"><div style="font-weight:700;font-size:12px;color:#475569;margin-bottom:4px">Por origen</div>';
      html += '<table style="width:100%;border-collapse:collapse;font-size:11px"><tbody>';
      Object.keys(orig).sort().forEach(k => {
        html += '<tr><td style="padding:3px 6px">' + k + '</td><td style="padding:3px 6px;text-align:right;font-weight:700">' + orig[k] + '</td></tr>';
      });
      html += '</tbody></table></div>';
      html += '<div style="flex:1;min-width:220px"><div style="font-weight:700;font-size:12px;color:#475569;margin-bottom:4px">Por mes (futuro)</div>';
      html += '<table style="width:100%;border-collapse:collapse;font-size:11px"><tbody>';
      Object.keys(meses).sort().forEach(k => {
        html += '<tr><td style="padding:3px 6px">' + k + '</td><td style="padding:3px 6px;text-align:right;font-weight:700">' + meses[k] + '</td></tr>';
      });
      html += '</tbody></table></div>';
      html += '</div>';
      out.innerHTML = html;
    } catch(e) { out.innerHTML = '<span style="color:#dc2626">Error red: ' + e.message + '</span>'; }
  };
  window.herrLlenarCalendario = async function() {
    if (!confirm('¿Disparar el cron de auto-sugeridas con horizonte 365 días?\n\nVa a llenar el calendario para todos los productos con velocidad de venta. Lotes Sugeridos quedan editables (no son Fijos).')) return;
    const out = document.getElementById('herr-cal-out');
    out.innerHTML = 'Llenando calendario · esto puede tardar 5-15 segundos…';
    try {
      const r = await fetch('/api/plan/auto-programar-sugeridas', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({dias_horizonte: 365}),
      });
      const d = await r.json();
      if (!r.ok || d.error) { out.innerHTML = '<span style="color:#dc2626">Error: ' + (d.error || r.status) + '</span>'; return; }
      out.innerHTML = '<div style="background:#f0fdf4;border-left:4px solid #16a34a;padding:10px 14px;border-radius:6px;font-size:12px;color:#15803d"><strong>✓ ' + (d.n_creados || 0) + ' Sugeridas creadas</strong> · ' + (d.n_saltados || 0) + ' saltadas (ya había lote ±7d). Recargá Abastecimiento para ver el efecto.</div>';
      setTimeout(herrDiagCalendario, 800);
    } catch(e) { out.innerHTML = '<span style="color:#dc2626">Error red: ' + e.message + '</span>'; }
  };
  // Tab 7 · Envases B2B (whitelist por cliente) · 24-may-2026 noche
  window._herrCliEnvasesState = {actuales: [], catalogo: []};
  window.herrCliEnvasesLoad = async function() {
    const cid = (document.getElementById('herr-cli-id').value || '').trim().toUpperCase();
    const out = document.getElementById('herr-cli-envases-out');
    if (!cid) { out.innerHTML = '<span style="color:#dc2626">cliente_id requerido</span>'; return; }
    out.innerHTML = 'Cargando…';
    try {
      const [r1, r2] = await Promise.all([
        fetch('/api/admin/b2b/cliente/' + encodeURIComponent(cid) + '/envases'),
        fetch('/api/b2b/envases-disponibles'),
      ]);
      const d1 = await r1.json();
      const d2 = await r2.json();
      if (!r1.ok || d1.error) { out.innerHTML = '<span style="color:#dc2626">Error: ' + (d1.error || r1.status) + '</span>'; return; }
      window._herrCliEnvasesState.cid = cid;
      window._herrCliEnvasesState.actuales = d1.items || [];
      window._herrCliEnvasesState.catalogo = d2.items || [];
      const actSet = new Set((d1.items || []).filter(x => x.activo).map(x => x.envase_codigo));
      let html = '<div style="background:' + (d1.modo === 'whitelist' ? '#fdf4ff' : '#f0fdf4') + ';border-left:3px solid ' + (d1.modo === 'whitelist' ? '#7e22ce' : '#16a34a') + ';padding:8px 10px;border-radius:5px;margin-bottom:12px;font-size:11px"><strong>Modo: ' + d1.modo + '</strong> · ' + (d1.modo === 'whitelist' ? d1.total + ' envases permitidos' : 'permisivo · cliente ve todos los activos') + '</div>';
      html += '<table style="width:100%;border-collapse:collapse;font-size:11px"><thead style="background:#f1f5f9"><tr><th style="text-align:left;padding:6px">✓</th><th style="text-align:left;padding:6px">Código</th><th style="text-align:left;padding:6px">Descripción</th><th style="text-align:left;padding:6px">Notas</th></tr></thead><tbody>';
      (d2.items || []).forEach(it => {
        const checked = actSet.has(it.codigo) ? ' checked' : '';
        html += '<tr style="border-top:1px solid #e2e8f0">' +
          '<td style="padding:6px"><input type="checkbox" data-cod="' + it.codigo + '"' + checked + ' class="herr-env-chk"></td>' +
          '<td style="padding:6px;font-family:ui-monospace;font-weight:600">' + it.codigo + '</td>' +
          '<td style="padding:6px">' + (it.descripcion || '') + '</td>' +
          '<td style="padding:6px"><input type="text" data-cod-notas="' + it.codigo + '" placeholder="notas (opcional)" style="width:140px;padding:3px 6px;border:1px solid #cbd5e1;border-radius:4px;font-size:11px"></td>' +
        '</tr>';
      });
      html += '</tbody></table>';
      html += '<div style="margin-top:12px;display:flex;gap:8px"><button onclick="herrCliEnvasesGuardar()" style="background:#7c3aed;color:#fff;border:none;padding:8px 16px;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer">💾 Guardar whitelist</button><span style="font-size:10px;color:#64748b;align-self:center">Vacío = modo permisivo (cliente ve todos)</span></div>';
      out.innerHTML = html;
    } catch(e) { out.innerHTML = '<span style="color:#dc2626">Error red: ' + e.message + '</span>'; }
  };
  window.herrCliEnvasesGuardar = async function() {
    const cid = window._herrCliEnvasesState.cid;
    if (!cid) return;
    const items = [];
    document.querySelectorAll('.herr-env-chk:checked').forEach(chk => {
      const cod = chk.dataset.cod;
      const notasInp = document.querySelector('[data-cod-notas="' + cod + '"]');
      items.push({envase_codigo: cod, notas: notasInp ? notasInp.value : ''});
    });
    if (!confirm('¿Guardar whitelist de ' + items.length + ' envase(s) para ' + cid + '?\n\n' + (items.length === 0 ? 'Sin items = modo PERMISIVO (cliente ve todos)' : 'Cliente solo podrá pedir los marcados.'))) return;
    try {
      const r = await fetch('/api/admin/b2b/cliente/' + encodeURIComponent(cid) + '/envases', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({items, reemplazar: true}),
      });
      const d = await r.json();
      if (!r.ok || d.error) { alert('Error: ' + (d.error || r.status)); return; }
      alert('✓ Whitelist actualizada · ' + d.total_activos + ' envases activos');
      herrCliEnvasesLoad();
    } catch(e) { alert('Error red: ' + e.message); }
  };
  // Tab 8 · Variantes fórmula (canónico)
  window._herrVarRows = 0;
  window.herrVarAddRow = function() {
    window._herrVarRows++;
    const n = window._herrVarRows;
    const cont = document.getElementById('herr-var-rows');
    const div = document.createElement('div');
    div.style.cssText = 'display:flex;gap:6px;margin-bottom:6px;align-items:center';
    div.innerHTML = '<input id="herr-var-prod-' + n + '" type="text" placeholder="producto_nombre (existente en formula_headers)" list="herr-rm-prod-list" style="flex:2;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;font-size:11px">' +
      '<input id="herr-var-label-' + n + '" type="text" placeholder="label (PIB CHINO)" style="flex:1;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;font-size:11px">' +
      '<input id="herr-var-prio-' + n + '" type="number" placeholder="0" value="0" min="0" max="100" style="width:60px;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;font-size:11px" title="0=auto-seleccionar · >0=preferir manual">' +
      '<button onclick="this.parentElement.remove()" style="background:#fee2e2;color:#991b1b;border:none;padding:4px 8px;border-radius:4px;cursor:pointer">✕</button>';
    cont.appendChild(div);
  };
  window.herrVarGuardar = async function() {
    const canonico = (document.getElementById('herr-var-canonico').value || '').trim();
    if (!canonico) { alert('Nombre canónico requerido'); return; }
    const variantes = [];
    for (let i = 1; i <= window._herrVarRows; i++) {
      const prod = document.getElementById('herr-var-prod-' + i);
      if (!prod) continue;
      const v = prod.value.trim();
      if (!v) continue;
      variantes.push({
        producto_nombre: v,
        variante_label: document.getElementById('herr-var-label-' + i).value.trim(),
        prioridad: parseInt(document.getElementById('herr-var-prio-' + i).value) || 0,
      });
    }
    if (!variantes.length) { alert('Agregá al menos 1 variante'); return; }
    if (!confirm('¿Agrupar ' + variantes.length + ' variante(s) bajo canónico "' + canonico + '"?')) return;
    try {
      const r = await fetch('/api/admin/formulas/agrupar-canonico', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({producto_canonico: canonico, variantes}),
      });
      const d = await r.json();
      if (!r.ok || d.error) { alert('Error: ' + (d.error || r.status)); return; }
      const out = document.getElementById('herr-var-out');
      let msg = '<span style="color:#6d28d9;font-weight:700">✓ ' + d.n_actualizadas + ' actualizadas</span>';
      if ((d.errores || []).length) {
        msg += '<div style="margin-top:6px;color:#dc2626">Errores: ' + d.errores.map(e => e.producto + ': ' + e.error).join(' · ') + '</div>';
      }
      out.innerHTML = msg;
    } catch(e) { alert('Error red: ' + e.message); }
  };
  window.herrVarEvaluar = async function() {
    const canonico = (document.getElementById('herr-var-test-canonico').value || '').trim();
    const kg = parseFloat(document.getElementById('herr-var-test-kg').value) || 10;
    const out = document.getElementById('herr-var-out');
    if (!canonico) { out.innerHTML = '<span style="color:#dc2626">canónico requerido</span>'; return; }
    out.innerHTML = 'Evaluando…';
    try {
      const r = await fetch('/api/admin/formulas/variantes/' + encodeURIComponent(canonico) + '?kg=' + kg);
      const d = await r.json();
      if (!r.ok) { out.innerHTML = '<span style="color:#dc2626">Error: ' + (d.error || r.status) + '</span>'; return; }
      if (!d.seleccion) { out.innerHTML = '<span style="color:#64748b">Sin variantes registradas para "' + canonico + '"</span>'; return; }
      const s = d.seleccion;
      let html = '<div style="background:#f0fdf4;border-left:3px solid #16a34a;padding:8px 10px;border-radius:5px">' +
        '<div style="font-weight:700;color:#15803d">✓ Ganadora: ' + s.producto_nombre + (s.variante_label ? ' (' + s.variante_label + ')' : '') + '</div>' +
        '<div style="font-size:11px;color:#475569;margin-top:3px">Decisión: ' + s.decision + ' · variantes evaluadas: ' + s.n_variantes_evaluadas + (s.faltante_total_g > 0 ? ' · faltante: ' + s.faltante_total_g + 'g' : ' · sin faltantes') + '</div>' +
        '</div>';
      if (s.evaluadas && s.evaluadas.length > 1) {
        html += '<table style="width:100%;margin-top:8px;border-collapse:collapse;font-size:11px"><thead style="background:#f1f5f9"><tr><th style="text-align:left;padding:5px">Variante</th><th style="text-align:right;padding:5px">Faltante (g)</th><th style="text-align:right;padding:5px">Items</th></tr></thead><tbody>';
        s.evaluadas.forEach((e, i) => {
          const bg = i === 0 ? '#dcfce7' : '#fff';
          html += '<tr style="border-top:1px solid #e2e8f0;background:' + bg + '"><td style="padding:5px">' + e.producto_nombre + (e.variante_label ? ' (' + e.variante_label + ')' : '') + '</td><td style="text-align:right;padding:5px">' + e.faltante_total_g + '</td><td style="text-align:right;padding:5px">' + e.n_items + '</td></tr>';
        });
        html += '</tbody></table>';
      }
      out.innerHTML = html;
    } catch(e) { out.innerHTML = '<span style="color:#dc2626">Error red: ' + e.message + '</span>'; }
  };
  // Sección 5 · Desactivar/Reactivar producto
  window.herrDesactivarProd = async function() {
    const prod = (document.getElementById('herr-dz-prod').value || '').trim();
    const out = document.getElementById('herr-resultado-dz');
    if (!prod) { out.innerHTML = '<span style="color:#dc2626">Producto requerido</span>'; return; }
    if (!confirm('¿Desactivar "' + prod + '"?\n\nSale de Necesidades + Calendar · NO se borra · puede reactivarse.')) return;
    try {
      const r = await fetch('/api/admin/formula-desactivar', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({producto_nombre: prod}),
      });
      const d = await r.json();
      if (!r.ok || d.error) { out.innerHTML = '<span style="color:#dc2626">Error: ' + (d.error || r.status) + '</span>'; return; }
      out.innerHTML = '<span style="color:#6d28d9;font-weight:700">✓ ' + d.producto_nombre + ' desactivado</span>';
      document.getElementById('herr-dz-prod').value = '';
    } catch(e) { out.innerHTML = '<span style="color:#dc2626">Error red: ' + e.message + '</span>'; }
  };
  window.herrActivarProd = async function() {
    const prod = (document.getElementById('herr-dz-prod').value || '').trim();
    const out = document.getElementById('herr-resultado-dz');
    if (!prod) { out.innerHTML = '<span style="color:#dc2626">Producto requerido</span>'; return; }
    try {
      const r = await fetch('/api/admin/formula-activar', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({producto_nombre: prod}),
      });
      const d = await r.json();
      if (!r.ok || d.error) { out.innerHTML = '<span style="color:#dc2626">Error: ' + (d.error || r.status) + '</span>'; return; }
      out.innerHTML = '<span style="color:#6d28d9;font-weight:700">✓ ' + d.producto_nombre + ' reactivado</span>';
      document.getElementById('herr-dz-prod').value = '';
    } catch(e) { out.innerHTML = '<span style="color:#dc2626">Error red: ' + e.message + '</span>'; }
  };
  window.herrDryRun = async function() {
    const desde = document.getElementById('herr-desde').value;
    if (!desde) { alert('Elegí fecha de corte'); return; }
    const out = document.getElementById('herr-resultado-limpieza');
    out.innerHTML = 'Calculando…';
    try {
      const r = await fetch('/api/plan/limpiar-sugeridas-futuras', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({desde: desde, dry_run: true}),
      });
      const d = await r.json();
      if (!r.ok || d.error) { out.innerHTML = '<span style="color:#dc2626">Error: '+(d.error||r.status)+'</span>'; return; }
      let html = '<div style="background:#fff;border:1px solid #e5e7eb;border-radius:6px;padding:8px;margin-top:4px;max-height:240px;overflow:auto">';
      html += '<div style="font-weight:700;color:#6d28d9;margin-bottom:6px">🔍 Cancelaría ' + d.n_dry + ' Sugerida(s) · Fijo intacto</div>';
      if (d.items && d.items.length) {
        html += '<table style="width:100%;border-collapse:collapse;font-size:11px"><thead><tr style="background:#f1f5f9"><th style="padding:4px;text-align:left">Producto</th><th style="padding:4px">Fecha</th><th style="padding:4px;text-align:right">Kg</th><th style="padding:4px">Origen</th></tr></thead><tbody>';
        d.items.slice(0, 50).forEach(it => {
          html += '<tr style="border-bottom:1px solid #f1f5f9"><td style="padding:4px">' + it.producto + '</td><td style="padding:4px;font-family:ui-monospace">' + it.fecha + '</td><td style="padding:4px;text-align:right">' + it.kg + '</td><td style="padding:4px;font-size:10px;color:#64748b">' + it.origen + '</td></tr>';
        });
        html += '</tbody></table>';
        if (d.items.length > 50) html += '<div style="font-size:10px;color:#64748b;margin-top:4px">... y ' + (d.items.length - 50) + ' más</div>';
      } else {
        html += '<div style="color:#64748b">(ninguna)</div>';
      }
      html += '</div>';
      out.innerHTML = html;
    } catch(e) { out.innerHTML = '<span style="color:#dc2626">Error: '+e.message+'</span>'; }
  };
  window.herrAplicar = async function() {
    const desde = document.getElementById('herr-desde').value;
    if (!desde) { alert('Elegí fecha de corte'); return; }
    if (!confirm('¿Cancelar TODAS las Sugeridas con fecha > ' + desde + '?\n\nEsto NO toca Fijo (eos_plan/b2b). Es soft-cancel (reversible vía audit_log).')) return;
    const out = document.getElementById('herr-resultado-limpieza');
    out.innerHTML = 'Aplicando…';
    try {
      const r = await fetch('/api/plan/limpiar-sugeridas-futuras', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({desde: desde, dry_run: false}),
      });
      const d = await r.json();
      if (!r.ok || d.error) { out.innerHTML = '<span style="color:#dc2626">Error: '+(d.error||r.status)+'</span>'; return; }
      out.innerHTML = '<span style="color:#6d28d9;font-weight:700">✓ ' + d.n_borradas + ' Sugerida(s) canceladas</span>';
      setTimeout(() => { location.reload(); }, 1500);
    } catch(e) { out.innerHTML = '<span style="color:#dc2626">Error: '+e.message+'</span>'; }
  };
  window.herrListarSospechosos = async function() {
    const out = document.getElementById('herr-resultado-sospechosos');
    out.innerHTML = 'Buscando…';
    try {
      const r = await fetch('/api/admin/lote-size-sospechoso');
      const d = await r.json();
      if (!r.ok || d.error) { out.innerHTML = '<span style="color:#dc2626">Error: '+(d.error||r.status)+'</span>'; return; }
      if (!d.items || !d.items.length) { out.innerHTML = '<span style="color:#6d28d9">✓ No hay productos con lote_size_kg absurdo</span>'; return; }
      let html = '<div style="font-size:11px;color:#64748b;margin-bottom:6px">' + d.n + ' producto(s) a arreglar · poné el valor real y pulsá Guardar:</div>';
      html += '<table style="width:100%;border-collapse:collapse;font-size:11px"><thead><tr style="background:#f1f5f9"><th style="padding:4px;text-align:left">Producto</th><th style="padding:4px;text-align:right">Actual</th><th style="padding:4px;text-align:right">Sugerido</th><th style="padding:4px;text-align:right">Nuevo kg</th><th style="padding:4px"></th></tr></thead><tbody>';
      d.items.forEach((it, idx) => {
        const prodEsc = (it.producto_nombre || '').replace(/"/g, '&quot;').replace(/'/g, "&#39;");
        const sug = it.sugerido_kg != null ? it.sugerido_kg : '';
        html += '<tr style="border-bottom:1px solid #f1f5f9"><td style="padding:4px">' + it.producto_nombre + '</td>' +
          '<td style="padding:4px;text-align:right;color:#dc2626">' + it.lote_size_kg_actual + '</td>' +
          '<td style="padding:4px;text-align:right;color:#64748b">' + sug + '</td>' +
          '<td style="padding:4px;text-align:right"><input id="herr-fix-' + idx + '" type="number" min="0.5" max="1000" step="0.1" value="' + (sug || 1) + '" style="width:60px;padding:3px 5px;border:1px solid #cbd5e1;border-radius:4px;font-size:11px;text-align:right"></td>' +
          '<td style="padding:4px"><button onclick="herrFixProd(&quot;' + prodEsc + '&quot;,' + idx + ')" style="background:#6d28d9;color:#fff;border:none;padding:4px 8px;border-radius:4px;font-size:10px;font-weight:700;cursor:pointer">Guardar</button></td></tr>';
      });
      html += '</tbody></table>';
      out.innerHTML = html;
    } catch(e) { out.innerHTML = '<span style="color:#dc2626">Error: '+e.message+'</span>'; }
  };
  // FIX 23-may-2026 PM Sebastián · "Suero Exfoliante BHA no hace match · 300/mes
  // no es verdad" · diag reveló SKUs huérfanos vendiendo sin map. UI para
  // mapearlos en bulk · una llamada actualiza N.
  window.herrListarHuerfanos = async function() {
    const out = document.getElementById('herr-resultado-huerfanos');
    out.innerHTML = 'Buscando…';
    try {
      const r = await fetch('/api/admin/skus-huerfanos-top?limit=50');
      const d = await r.json();
      if (!r.ok || d.error) { out.innerHTML = '<span style="color:#dc2626">Error: '+(d.error||r.status)+'</span>'; return; }
      const huerfanos = d.huerfanos_top || [];
      const productos = d.productos_disponibles || [];
      if (!huerfanos.length) { out.innerHTML = '<span style="color:#6d28d9">✓ No hay huérfanos vendiendo</span>'; return; }
      window._herr_productos = productos;
      let html = '<div style="font-size:11px;color:#64748b;margin-bottom:6px">' + huerfanos.length + ' SKU(s) huérfanos · ' + d.n_huerfanos_total + ' total en BD · elegí producto y pulsá Mapear · al final ✅ Mapear todos</div>';
      html += '<div style="max-height:380px;overflow:auto;border:1px solid #e5e7eb;border-radius:6px">';
      html += '<table style="width:100%;border-collapse:collapse;font-size:11px"><thead style="position:sticky;top:0;background:#f1f5f9"><tr><th style="padding:5px;text-align:left">SKU</th><th style="padding:5px;text-align:right">uds 60d</th><th style="padding:5px;text-align:left">Mapear a producto</th><th style="padding:5px"></th></tr></thead><tbody>';
      huerfanos.forEach((h, idx) => {
        const skuEsc = (h.sku || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        html += '<tr style="border-bottom:1px solid #f1f5f9"><td style="padding:5px;font-family:ui-monospace;font-weight:700">' + h.sku + '</td>' +
          '<td style="padding:5px;text-align:right;color:#7c3aed;font-weight:700">' + h.uds_60d + '</td>' +
          '<td style="padding:5px"><select id="herr-h-prod-' + idx + '" style="width:100%;padding:3px 4px;border:1px solid #cbd5e1;border-radius:4px;font-size:11px"><option value="">— elegir —</option>';
        // Sugerencia: producto cuyo nombre contenga el SKU como substring
        const skuU = (h.sku || '').toUpperCase();
        const sugerencia = productos.find(p => skuU.length >= 3 && p.toUpperCase().split(' ').some(w => w.length >= 3 && skuU.indexOf(w.substring(0,3)) >= 0));
        productos.forEach(p => {
          const sel = (p === sugerencia) ? ' selected' : '';
          html += '<option value="' + p.replace(/"/g, '&quot;') + '"' + sel + '>' + p + '</option>';
        });
        html += '</select></td>' +
          '<td style="padding:5px"><button onclick="herrMapearUno(&quot;' + skuEsc + '&quot;,' + idx + ')" style="background:#6d28d9;color:#fff;border:none;padding:3px 8px;border-radius:4px;font-size:10px;font-weight:700;cursor:pointer">Map</button></td></tr>';
      });
      html += '</tbody></table></div>';
      html += '<div style="margin-top:8px"><button onclick="herrMapearTodos()" style="background:#7c3aed;color:#fff;border:none;padding:6px 14px;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer">✅ Mapear todos los seleccionados (bulk)</button></div>';
      out.innerHTML = html;
    } catch(e) { out.innerHTML = '<span style="color:#dc2626">Error: '+e.message+'</span>'; }
  };
  window.herrMapearUno = async function(sku, idx) {
    const sel = document.getElementById('herr-h-prod-' + idx);
    if (!sel || !sel.value) { alert('Elegí un producto del dropdown'); return; }
    if (!confirm('¿Mapear SKU ' + sku + ' → ' + sel.value + '?')) return;
    try {
      const r = await fetch('/api/admin/sku-producto-map/bulk', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({items:[{sku, producto_nombre: sel.value}]}),
      });
      const d = await r.json();
      if (!r.ok || d.error) { alert('Error: ' + (d.error||r.status)); return; }
      sel.disabled = true;
      sel.style.background = '#dcfce7';
      if (sel.nextElementSibling) sel.nextElementSibling.innerHTML = '<span style="color:#6d28d9;font-weight:700;font-size:14px">✓</span>';
    } catch(e) { alert('Error red: ' + e.message); }
  };
  window.herrMapearTodos = async function() {
    const huerfanos = window._herr_productos ? [...document.querySelectorAll('[id^="herr-h-prod-"]')] : [];
    const items = [];
    huerfanos.forEach((sel, i) => {
      if (sel.value && !sel.disabled) {
        const tr = sel.closest('tr');
        const sku = tr ? tr.querySelector('td').textContent.trim() : '';
        if (sku) items.push({sku, producto_nombre: sel.value});
      }
    });
    if (!items.length) { alert('No hay productos seleccionados sin mapear'); return; }
    if (!confirm('¿Mapear ' + items.length + ' SKU(s) a sus productos?')) return;
    try {
      const r = await fetch('/api/admin/sku-producto-map/bulk', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({items}),
      });
      const d = await r.json();
      if (!r.ok || d.error) { alert('Error: ' + (d.error||r.status)); return; }
      alert('✓ ' + d.n_mapeados + ' mapeados, ' + d.n_errores + ' errores · recargá Necesidades para ver velocidad real');
      herrListarHuerfanos();
    } catch(e) { alert('Error red: ' + e.message); }
  };
  window.herrFixProd = async function(prodNombre, idx) {
    const inp = document.getElementById('herr-fix-' + idx);
    if (!inp) return;
    const kg = parseFloat(inp.value);
    if (!kg || kg < 0.5 || kg > 1000) { alert('Valor inválido (0.5 - 1000 kg)'); return; }
    if (!confirm('¿Actualizar ' + prodNombre + ' · lote_size_kg = ' + kg + '?')) return;
    try {
      const r = await fetch('/api/admin/lote-size-fix', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({producto_nombre: prodNombre, lote_size_kg: kg}),
      });
      const d = await r.json();
      if (!r.ok || d.error) { alert('Error: ' + (d.error || r.status)); return; }
      // Marcar visualmente como hecho
      inp.disabled = true;
      inp.style.background = '#dcfce7';
      inp.nextElementSibling && (inp.nextElementSibling.innerHTML = '<span style="color:#6d28d9;font-weight:700">✓</span>');
    } catch(e) { alert('Error: ' + e.message); }
  };

  // FIX 23-may-2026 Sebastián · "moldear necesidades · botón Programar
  // debe permitir seleccionar horizonte calculando perfecto el consumo y
  // para cuánto alcanzará · si ya está programado debe decir programado
  // está bien o lo movemos".
  // Modal HTML real (no alert) con selector horizonte + tabla por lote +
  // detección de conflicto ±7d con opción mantener / reubicar.
  window._previewState = {producto: null, data: null, horizonte: 90};
  // FIX 24-may PM Sebastián · auto-sugerencia Nivel 1 · 1-click
  // mapeo de SKU huérfano sugerido. Llama endpoint bulk con 1 item.
  window.aceptarSugerenciaMapeo = async function(sku, prodNombre, ev) {
    if (ev && ev.stopPropagation) ev.stopPropagation();
    if (!confirm('¿Mapear SKU ' + sku + ' → ' + prodNombre + '?')) return;
    try {
      const r = await fetch('/api/admin/sku-producto-map/bulk', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({items:[{sku, producto_nombre: prodNombre}]}),
      });
      const d = await r.json();
      if (!r.ok || d.error) { alert('Error: ' + (d.error || r.status)); return; }
      if ((d.n_errores || 0) > 0) { alert('Error: ' + JSON.stringify(d.errores[0])); return; }
      alert('✓ ' + sku + ' → ' + prodNombre + ' mapeado · refrescando...');
      if (typeof cargarNecesidades === 'function') cargarNecesidades();
    } catch(e) { alert('Error red: ' + e.message); }
  };
  // FIX 23-may-2026 PM Sebastián · "triactive no tiene tamaño envase
  // y no me deja modificarlo" · prompt rápido + POST /admin/ml-fix
  window.fixVolumenMl = async function(prodNombre, mlActual) {
    const ml = prompt('Volumen real en ml del envase principal de ' + prodNombre + ':\n\nActualmente inferido por nombre = ' + mlActual + 'ml.\nEjemplos: 30 (suero), 50 (gel), 150 (limpiador), 100 (mascarilla).', String(mlActual));
    if (!ml || isNaN(parseFloat(ml))) return;
    const mlNum = parseFloat(ml);
    if (mlNum <= 0 || mlNum > 5000) { alert('Inválido (1-5000 ml)'); return; }
    try {
      const r = await fetch('/api/admin/ml-fix', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({producto_nombre: prodNombre, volumen_ml: mlNum}),
      });
      const d = await r.json();
      if (!r.ok || d.error) { alert('Error: ' + (d.error || r.status)); return; }
      alert('✓ Envase fijado en ' + d.volumen_ml_nuevo + 'ml para ' + d.producto_nombre +
            '\nSKU: ' + d.sku_shopify + ' · ' + d.accion);
      if (typeof cargarNecesidades === 'function') cargarNecesidades();
    } catch(e) { alert('Error red: ' + e.message); }
  };
  window.previewSugeridasProducto = async function(prodNombre) {
    window._previewState = {producto: prodNombre, data: null, horizonte: 90};
    abrirModalProgramar();
    await recargarPreviewProgramar();
  };
  function abrirModalProgramar() {
    let modal = document.getElementById('modal-programar');
    if (modal) modal.remove();
    modal = document.createElement('div');
    modal.id = 'modal-programar';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
    modal.innerHTML = '<div style="background:#fff;border-radius:12px;max-width:760px;width:100%;max-height:90vh;overflow:auto;box-shadow:0 12px 40px rgba(0,0,0,0.25)">' +
      '<div style="padding:18px 22px;border-bottom:1px solid #e5e7eb;display:flex;align-items:center;justify-content:space-between">' +
        '<div><h3 style="margin:0;font-size:16px;color:#1e293b">🤖 Programar producción</h3><div id="mp-prod" style="font-size:13px;color:#64748b;margin-top:2px"></div></div>' +
        '<button onclick="document.getElementById(\'modal-programar\').remove()" style="background:#e5e7eb;color:#475569;border:none;width:32px;height:32px;border-radius:50%;font-size:18px;cursor:pointer">×</button>' +
      '</div>' +
      '<div style="padding:18px 22px">' +
        '<div id="mp-loading" style="text-align:center;color:#64748b;padding:30px">Calculando…</div>' +
        '<div id="mp-content" style="display:none">' +
          '<div style="background:#f1f5f9;border-radius:8px;padding:12px;margin-bottom:14px;display:grid;grid-template-columns:repeat(4,1fr);gap:8px;font-size:12px">' +
            '<div><div style="color:#64748b;font-size:10px;text-transform:uppercase">Velocidad</div><div id="mp-vel" style="font-weight:700;color:#1e40af"></div></div>' +
            '<div><div style="color:#64748b;font-size:10px;text-transform:uppercase" title="Editá para hacer lotes más grandes (duran más, fabricás menos seguido)">Lote estándar ✏️</div><div style="display:flex;align-items:center;gap:4px;margin-top:2px"><input id="mp-lote-input" type="number" min="1" max="2000" step="0.5" style="width:70px;padding:3px 5px;border:1px solid #7c3aed;border-radius:4px;font-size:13px;font-weight:700;color:#1e40af" onchange="cambiarLoteKg(parseFloat(this.value))"><span style="font-size:11px;color:#64748b">kg</span></div><div id="mp-lote-status" style="font-size:9px;color:#64748b;margin-top:2px"></div></div>' +
            '<div><div style="color:#64748b;font-size:10px;text-transform:uppercase">Dura</div><div id="mp-dur" style="font-weight:700;color:#1e40af"></div></div>' +
            '<div><div style="color:#64748b;font-size:10px;text-transform:uppercase">Re-orden cada</div><div id="mp-paso" style="font-weight:700;color:#1e40af"></div></div>' +
          '</div>' +
          '<div style="margin-bottom:6px;display:flex;align-items:center;gap:10px;flex-wrap:wrap">' +
            '<label style="font-weight:700;color:#1e293b;font-size:13px" title="Hasta dónde mostrar lotes en la tabla · NO es la frecuencia · re-orden cada N días lo decide automático según duración del lote y buffer (mostrado en RE-ORDEN CADA arriba)">Hasta cuándo proyectar:</label>' +
            '<button onclick="cambiarHorizonte(30)" class="mp-h-btn" data-h="30" style="padding:5px 10px;border:1px solid #cbd5e1;background:#fff;border-radius:5px;cursor:pointer;font-size:12px">30d</button>' +
            '<button onclick="cambiarHorizonte(60)" class="mp-h-btn" data-h="60" style="padding:5px 10px;border:1px solid #cbd5e1;background:#fff;border-radius:5px;cursor:pointer;font-size:12px">60d</button>' +
            '<button onclick="cambiarHorizonte(90)" class="mp-h-btn" data-h="90" style="padding:5px 10px;border:1px solid #cbd5e1;background:#fff;border-radius:5px;cursor:pointer;font-size:12px">90d</button>' +
            '<button onclick="cambiarHorizonte(180)" class="mp-h-btn" data-h="180" style="padding:5px 10px;border:1px solid #cbd5e1;background:#fff;border-radius:5px;cursor:pointer;font-size:12px">180d</button>' +
            '<button onclick="cambiarHorizonte(365)" class="mp-h-btn" data-h="365" style="padding:5px 10px;border:1px solid #cbd5e1;background:#fff;border-radius:5px;cursor:pointer;font-size:12px">1 año</button>' +
            '<input id="mp-h-custom" type="number" min="7" max="365" placeholder="custom" style="width:80px;padding:5px 8px;border:1px solid #cbd5e1;border-radius:5px;font-size:12px" onchange="cambiarHorizonte(parseInt(this.value))">' +
          '</div>' +
          '<div style="font-size:11px;color:#64748b;margin-bottom:12px;padding:6px 10px;background:#f1f5f9;border-radius:5px">💡 El horizonte solo limita hasta cuándo proyectar lotes en la tabla. La frecuencia real (cada cuántos días se programa un nuevo lote) la decide el sistema según <strong>DURA del lote − buffer 25d</strong> · ej. lote 60d → re-orden cada 35d.</div>' +
          '<div id="mp-cobertura" style="background:#dcfce7;border-left:4px solid #16a34a;border-radius:6px;padding:10px 12px;margin-bottom:12px;font-size:13px;color:#166534"></div>' +
          '<div id="mp-desglose-tonos" style="display:none;background:#fdf4ff;border-left:4px solid #a855f7;border-radius:6px;padding:10px 12px;margin-bottom:12px;font-size:13px;color:#581c87"></div>' +
          '<div id="mp-blocker" style="display:none;background:#fee2e2;border-left:4px solid #dc2626;border-radius:6px;padding:12px;margin-bottom:12px;font-size:13px;color:#991b1b;font-weight:700"></div>' +
          '<div id="mp-tabla"></div>' +
          '<div style="margin-top:14px;display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap">' +
            '<button onclick="document.getElementById(\'modal-programar\').remove()" style="padding:8px 14px;border:1px solid #cbd5e1;background:#fff;color:#475569;border-radius:6px;cursor:pointer;font-size:13px">Cancelar</button>' +
            '<button id="mp-btn-uno" onclick="generarSoloProximoLote()" style="padding:8px 16px;background:#6d28d9;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:700" title="Crea solo 1 lote (la próxima fecha sugerida) · vos arrastrás más si querés">📅 Solo el próximo (1 lote)</button>' +
            '<button id="mp-btn-generar" onclick="generarProgramacionesProducto()" style="padding:8px 16px;background:#7c3aed;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:700" title="Genera la cadena completa de lotes en el horizonte">🤖 Generar en cadena</button>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '</div>';
    document.body.appendChild(modal);
  }
  // FIX 23-may-2026 PM Sebastián · "si yo quisiera aumentar la cantidad
  // de lote para que me dure más días y fabricar menos seguido · debería
  // poder cambiar que calcule automático". Input editable Lote Estándar
  // recalcula dur, paso y tabla en frontend · al programar manda override
  // al endpoint para que el INSERT use el kg custom.
  window.cambiarLoteKg = function(kg) {
    if (!kg || kg < 1 || kg > 2000) {
      alert('Lote inválido (1-2000 kg)');
      return;
    }
    window._previewState.lote_kg_override = kg;
    recargarPreviewProgramar();
  };
  window.cambiarHorizonte = function(d) {
    if (!d || d < 7) return;
    window._previewState.horizonte = d;
    document.querySelectorAll('.mp-h-btn').forEach(b => {
      const matches = parseInt(b.dataset.h) === d;
      b.style.background = matches ? '#7c3aed' : '#fff';
      b.style.color = matches ? '#fff' : '#1e293b';
    });
    recargarPreviewProgramar();
  };
  async function recargarPreviewProgramar() {
    const st = window._previewState;
    if (!st.producto) return;
    document.getElementById('mp-prod').textContent = st.producto;
    document.getElementById('mp-loading').style.display = 'block';
    document.getElementById('mp-content').style.display = 'none';
    try {
      let url = '/api/plan/sugerir-preview?producto=' + encodeURIComponent(st.producto) + '&dias_horizonte=' + st.horizonte;
      if (st.lote_kg_override != null) url += '&lote_kg_override=' + st.lote_kg_override;
      const r = await fetch(url);
      const d = await r.json();
      st.data = d;
      document.getElementById('mp-loading').style.display = 'none';
      document.getElementById('mp-content').style.display = 'block';
      // Si no hay lote_kg_override aún, usar el del backend; si hay, preservar el del usuario
      const loteActual = (st.lote_kg_override != null) ? st.lote_kg_override : (d.lote_bulk_kg || 0);
      st.lote_kg_actual = loteActual;
      document.getElementById('mp-vel').textContent = (d.velocidad_kg_dia || 0).toFixed(2) + ' kg/d';
      const inpLote = document.getElementById('mp-lote-input');
      if (inpLote) inpLote.value = loteActual;
      const stLoteEl = document.getElementById('mp-lote-status');
      if (stLoteEl) stLoteEl.textContent = (st.lote_kg_override != null) ? '✎ editado' : (d.lote_calculado ? 'calculado' : 'de BD');
      document.getElementById('mp-dur').textContent = (d.dur_lote_dias || 0) + ' d';
      document.getElementById('mp-paso').textContent = (d.paso_dias || 0) + ' d';
      // Marca botón horizonte activo
      document.querySelectorAll('.mp-h-btn').forEach(b => {
        const matches = parseInt(b.dataset.h) === st.horizonte;
        b.style.background = matches ? '#7c3aed' : '#fff';
        b.style.color = matches ? '#fff' : '#1e293b';
      });
      const blocker = document.getElementById('mp-blocker');
      if (d.blocker) {
        blocker.style.display = 'block';
        blocker.textContent = '⚠ ' + d.blocker;
        document.getElementById('mp-tabla').innerHTML = '';
        document.getElementById('mp-cobertura').style.display = 'none';
        document.getElementById('mp-btn-generar').disabled = true;
        document.getElementById('mp-btn-generar').style.opacity = '0.4';
        return;
      }
      blocker.style.display = 'none';
      document.getElementById('mp-cobertura').style.display = 'block';
      const fechas = d.fechas || [];
      const nuevas = fechas.filter(f => !f.ya_programado);
      const ya = fechas.filter(f => f.ya_programado);
      const kgTotal = fechas.reduce((s,f) => s + (f.kg || 0), 0);
      const diasCob = (d.velocidad_kg_dia > 0) ? Math.round(kgTotal / d.velocidad_kg_dia) : 0;
      let avisoLote = '';
      if (d.lote_calculado) {
        avisoLote = '<div style="background:#fef3c7;color:#92400e;border-left:3px solid #f59e0b;padding:6px 10px;border-radius:5px;font-size:11px;font-weight:600;margin-top:8px">⚠ lote_size_kg en BD = ' + d.lote_bulk_kg_bd + ' kg (absurdo) · usando ' + d.lote_bulk_kg + ' kg calculado (~' + (d.dur_lote_dias || 60) + 'd cobertura) · corregí el lote_size_kg en el maestro de fórmulas</div>';
      }
      if (d.ml_inferido) {
        avisoLote += '<div style="background:#fef3c7;color:#92400e;border-left:3px solid #f59e0b;padding:6px 10px;border-radius:5px;font-size:11px;font-weight:600;margin-top:6px">⚠ ml inferido por nombre · agregá envase en producto_presentaciones para precisión</div>';
      }
      document.getElementById('mp-cobertura').innerHTML =
        '📅 <strong>' + fechas.length + '</strong> lote(s) en el horizonte · ' +
        '<strong>' + nuevas.length + '</strong> nuevo(s) por crear · ' +
        '<strong>' + ya.length + '</strong> ya programado(s)<br>' +
        '🎯 Total <strong>' + kgTotal.toFixed(1) + ' kg</strong> · te alcanzará para <strong>~' + diasCob + ' días</strong> (~' + (diasCob/30).toFixed(1) + ' meses)' +
        avisoLote;
      // 🎨 Desglose por tono · Sebastián 24-may PM
      // Si el producto tiene 2+ SKUs (lip serum tonos, blush balm colores)
      // mostrar cómo dividir el bulk del próximo lote según mix ventas.
      const proxLote = nuevas[0] || ya[0];
      if (proxLote && (d.lote_bulk_kg || 0) > 0) {
        cargarDesgloseTonos(st.producto, d.lote_bulk_kg);
      } else {
        const dt = document.getElementById('mp-desglose-tonos');
        if (dt) dt.style.display = 'none';
      }
      // Tabla
      let html = '<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#f1f5f9;color:#475569"><th style="padding:8px;text-align:left">#</th><th style="padding:8px;text-align:left">Fecha</th><th style="padding:8px;text-align:right">Kg</th><th style="padding:8px;text-align:right">En</th><th style="padding:8px;text-align:left">Estado</th></tr></thead><tbody>';
      fechas.forEach((f, i) => {
        const bg = f.ya_programado ? '#fef3c7' : '#fff';
        const badge = f.ya_programado
          ? '<span style="background:#f59e0b;color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700">YA PROGRAMADO</span>'
          : '<span style="background:#7c3aed;color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700">NUEVA</span>';
        html += '<tr style="background:' + bg + ';border-bottom:1px solid #e5e7eb"><td style="padding:8px">' + (i+1) + '</td><td style="padding:8px;font-weight:700">' + f.fecha + '</td><td style="padding:8px;text-align:right">' + f.kg + '</td><td style="padding:8px;text-align:right;color:#64748b">' + f.dias_hasta + 'd</td><td style="padding:8px">' + badge + '</td></tr>';
      });
      if (!fechas.length) {
        html += '<tr><td colspan="5" style="padding:18px;text-align:center;color:#64748b">No hay sugerencias en este horizonte</td></tr>';
      }
      html += '</tbody></table>';
      document.getElementById('mp-tabla').innerHTML = html;
      const btn = document.getElementById('mp-btn-generar');
      if (nuevas.length === 0) {
        btn.disabled = true;
        btn.style.opacity = '0.5';
        btn.textContent = ya.length ? '✓ Está bien · cerrar' : 'Nada por programar';
        btn.onclick = () => document.getElementById('modal-programar').remove();
      } else {
        btn.disabled = false;
        btn.style.opacity = '1';
        btn.textContent = 'Generar ' + nuevas.length + ' lote(s) en Calendario';
        btn.onclick = generarProgramacionesProducto;
      }
    } catch(e) {
      document.getElementById('mp-loading').textContent = 'Error: ' + e.message;
    }
  }
  // FIX 24-may PM Sebastián · "lip serum tonos · se suma cantidad
  // total, se hace base y se divide para cada tono según venta" ·
  // muestra desglose para que sepas cuánto pigmentar de cada tono.
  window.cargarDesgloseTonos = async function(producto, kgTotal) {
    const dt = document.getElementById('mp-desglose-tonos');
    if (!dt) return;
    try {
      const r = await fetch('/api/plan/desglose-tonos?producto=' + encodeURIComponent(producto) + '&cantidad_kg=' + kgTotal + '&ventana_dias=60');
      const d = await r.json();
      if (!r.ok || !d.ok) { dt.style.display = 'none'; return; }
      if ((d.n_tonos || 0) < 2) { dt.style.display = 'none'; return; }  // Solo si multi-SKU
      let html = '<div style="font-weight:700;margin-bottom:6px">🎨 Desglose por tono · próximo lote de ' + kgTotal + ' kg</div>';
      html += '<div style="font-size:11px;color:#7c3aed;margin-bottom:6px">Mix calculado de ventas últimos ' + d.ventana_dias + ' días · ' + d.total_uds_ventana + ' uds totales</div>';
      html += '<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#f3e8ff;color:#581c87"><th style="padding:5px;text-align:left">SKU</th><th style="padding:5px;text-align:right">Vendió 60d</th><th style="padding:5px;text-align:right">%</th><th style="padding:5px;text-align:right">Kg lote</th></tr></thead><tbody>';
      d.items.forEach(it => {
        html += '<tr style="border-bottom:1px solid #f3e8ff"><td style="padding:5px;font-family:ui-monospace;font-weight:700">' + it.sku + '</td>' +
          '<td style="padding:5px;text-align:right">' + it.uds_ventana + '</td>' +
          '<td style="padding:5px;text-align:right;font-weight:700">' + it.porcentaje.toFixed(1) + '%</td>' +
          '<td style="padding:5px;text-align:right;font-weight:800;color:#7c3aed">' + it.kg_sugerido.toFixed(2) + ' kg</td></tr>';
      });
      html += '</tbody></table>';
      html += '<div style="font-size:10px;color:#7c3aed;margin-top:4px">💡 Producís 1 base bulk de ' + kgTotal + ' kg · al pigmentar dividís entre tonos según este mix · si las ventas cambian la próxima vez verás otro %.</div>';
      dt.innerHTML = html;
      dt.style.display = 'block';
    } catch(e) {
      dt.style.display = 'none';
    }
  };
  window.generarProgramacionesProducto = async function() {
    const st = window._previewState;
    if (!st.producto || !st.data) return;
    const btn = document.getElementById('mp-btn-generar');
    btn.disabled = true; btn.textContent = 'Generando…';
    try {
      const body = {producto: st.producto, dias_horizonte: st.horizonte};
      if (st.lote_kg_override != null) body.lote_kg_override = st.lote_kg_override;
      const r = await fetch('/api/plan/auto-programar-sugeridas', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (!r.ok || d.error) { alert('Error: ' + (d.error || r.status)); btn.disabled = false; return; }
      const mios = (d.creados || []).filter(c => (c.producto || '').toUpperCase() === st.producto.toUpperCase());
      alert('✓ ' + mios.length + ' lote(s) creado(s) en Calendario para ' + st.producto + '\n\n' +
            mios.map(c => '  · ' + c.fecha + ' · ' + c.cantidad_kg + 'kg').join('\n'));
      document.getElementById('modal-programar').remove();
      cargarNecesidades();
    } catch(e) {
      alert('Error red: ' + e.message);
      btn.disabled = false;
    }
  };
  // FIX 23-may-2026 PM Sebastián · "una opción es que me dejes a mí
  // manual hacerlo · veo que sigue colocando mal y planeando mal".
  // Crea SOLO 1 lote (la próxima fecha sugerida) · ideal para control
  // manual · el usuario decide cuándo agregar más.
  window.generarSoloProximoLote = async function() {
    const st = window._previewState;
    if (!st.producto || !st.data) return;
    const proxima = (st.data.fechas || []).find(f => !f.ya_programado);
    if (!proxima) {
      alert('No hay próxima fecha por crear · todas las posiciones del horizonte ya están programadas');
      return;
    }
    if (!confirm('¿Crear UN solo lote?\n\n' + st.producto + '\nFecha: ' + proxima.fecha + '\nKg: ' + proxima.kg + '\n\nPodés agregar más después desde el calendario o repitiendo este flujo.')) return;
    const btn = document.getElementById('mp-btn-uno');
    btn.disabled = true; btn.textContent = 'Creando…';
    try {
      // Usa horizonte mínimo (paso+1) para que el helper solo cree el primero
      const minHorizonte = Math.max((st.data.paso_dias || 30) + 1, (proxima.dias_hasta || 1) + 1);
      const body = {producto: st.producto, dias_horizonte: minHorizonte};
      if (st.lote_kg_override != null) body.lote_kg_override = st.lote_kg_override;
      const r = await fetch('/api/plan/auto-programar-sugeridas', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (!r.ok || d.error) { alert('Error: ' + (d.error || r.status)); btn.disabled = false; return; }
      const mios = (d.creados || []).filter(c => (c.producto || '').toUpperCase() === st.producto.toUpperCase());
      alert('✓ ' + mios.length + ' lote(s) creado(s) en Calendario\n' +
            mios.map(c => '  · ' + c.fecha + ' · ' + c.cantidad_kg + 'kg').join('\n'));
      document.getElementById('modal-programar').remove();
      cargarNecesidades();
    } catch(e) {
      alert('Error red: ' + e.message);
      btn.disabled = false;
    }
  };

  // FIX 23-may-2026 · Sebastián pidió mapear SKU inline desde el alert
  // SIN MAPEO SHOPIFY · antes mensaje sin acción · ahora input + huérfanos
  // sugeridos + POST /api/admin/sku-producto-map
  window._mapearSkuInline = async function(prodNombre, inputId, statusId) {
    const inp = document.getElementById(inputId);
    const status = document.getElementById(statusId);
    if (!inp || !status) return;
    const sku = (inp.value || '').trim().toUpperCase();
    if (!sku) {
      status.innerHTML = '<span style="color:#dc2626">Ingresá un SKU</span>';
      return;
    }
    status.innerHTML = '<span style="color:#6b7280">Mapeando…</span>';
    try {
      const r = await fetch('/api/admin/sku-producto-map', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({sku: sku, producto_nombre: prodNombre, activo: true}),
      });
      const d = await r.json();
      if (r.status === 401) {
        status.innerHTML = '<span style="color:#dc2626">Sesión expirada · re-loguea</span>';
        return;
      }
      if (r.status === 403) {
        status.innerHTML = '<span style="color:#dc2626">Solo admin puede mapear SKUs</span>';
        return;
      }
      if (!r.ok || d.error) {
        status.innerHTML = '<span style="color:#dc2626">Error: ' + escapeHtmlNec(d.error || ('HTTP '+r.status)) + '</span>';
        return;
      }
      status.innerHTML = '<span style="color:#16a34a;font-weight:700">✓ Mapeado · refrescando necesidades…</span>';
      setTimeout(function() { cargarNecesidades(); }, 600);
    } catch(e) {
      status.innerHTML = '<span style="color:#dc2626">Error red: ' + escapeHtmlNec(e.message) + '</span>';
    }
  };

  function renderProximasNec(items) {
    const div = document.getElementById('nec-proximas');
    if (!items.length) { div.innerHTML = ''; return; }
    // Sebastián 25-may-2026 PM · arranca cerrado · "que para toda la app
    // salgan colapsados y ya uno escoja si los abre".
    let html = '<details style="background:white;border-radius:12px;border:1px solid #e2e8f0;overflow:hidden">';
    html += '<summary style="cursor:pointer;padding:12px 16px;background:linear-gradient(90deg,#eff6ff,#dbeafe);font-weight:700;color:#1e40af;font-size:14px">';
    html += '📅 Próximas producciones agendadas · ' + items.length;
    html += '</summary>';
    html += '<div style="padding:10px 16px;overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px;min-width:560px">';
    html += '<thead><tr style="background:#f8fafc;color:#475569">';
    html += '<th style="text-align:center;padding:6px 6px;font-weight:700">Fecha</th>';
    html += '<th style="text-align:left;padding:6px 6px;font-weight:700">Producto</th>';
    html += '<th style="text-align:center;padding:6px 6px;font-weight:700">kg</th>';
    html += '<th style="text-align:center;padding:6px 6px;font-weight:700">Sala</th>';
    html += '<th style="text-align:center;padding:6px 6px;font-weight:700">Origen</th>';
    html += '<th style="text-align:center;padding:6px 6px;font-weight:700">Estado</th>';
    html += '<th style="padding:6px 6px"></th>';
    html += '</tr></thead><tbody>';
    items.forEach(it => {
      const orig = it.origen === 'eos_plan' ? '🆕 EOS' :
                   it.origen === 'eos_retroactivo' ? '📜 EOS-back' :
                   it.origen === 'calendar' ? '📆 Calendar' : it.origen;
      html += '<tr style="border-bottom:1px solid #f1f5f9">';
      html += '<td style="padding:6px 6px;text-align:center;font-weight:700">' + escapeHtmlNec(it.fecha_programada) + '</td>';
      html += '<td style="padding:6px 6px">' + escapeHtmlNec(it.producto) + '</td>';
      html += '<td style="padding:6px 6px;text-align:center">' + it.cantidad_kg + '</td>';
      html += '<td style="padding:6px 6px;text-align:center">' + (it.area_codigo || '—') + '</td>';
      html += '<td style="padding:6px 6px;text-align:center;font-size:11px">' + escapeHtmlNec(orig) + '</td>';
      html += '<td style="padding:6px 6px;text-align:center"><span style="background:#e0e7ff;color:#3730a3;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700">' + escapeHtmlNec(it.estado) + '</span></td>';
      html += '<td style="padding:6px 6px;text-align:right">';
      if (it.estado === 'pendiente' || it.estado === 'programado') {
        html += '<button onclick="cancelarProxima(' + it.id + ')" style="background:transparent;border:1px solid #cbd5e1;color:#64748b;padding:3px 8px;border-radius:4px;font-size:10px;cursor:pointer">Cancelar</button>';
      }
      html += '</td></tr>';
    });
    html += '</tbody></table></div></details>';
    div.innerHTML = html;
  }

  // Eliminar un lote agendado · con opción de FORZAR (admin · revierte el descuento) si ya inició/descontó.
  async function _eliminarProxFuerza(id){
    let r = await fetch('/api/plan/proximas/' + id, {method:'DELETE', headers:{'X-CSRF-Token': csrfTokenNec()}});
    if(r.ok) return true;
    let d={}; try{ d = await r.json(); }catch(e){}
    if(d && d.codigo === 'YA_EN_EJECUCION'){
      if(confirm('Esta producción ya inició o descontó inventario.\n\n¿Forzar la eliminación? Revierte el descuento (re-agrega la MP/MEE al inventario) y elimina el lote. Solo admin.')){
        r = await fetch('/api/plan/proximas/' + id, {method:'DELETE', headers:{'Content-Type':'application/json','X-CSRF-Token': csrfTokenNec()}, body: JSON.stringify({force:true})});
        if(r.ok) return true;
        let d2={}; try{ d2 = await r.json(); }catch(e){}
        alert('Error: ' + (d2.error || r.status)); return false;
      }
      return false;
    }
    alert('Error: ' + (d.error || r.status)); return false;
  }
  async function cancelarProxima(id) {
    if (!confirm('¿Cancelar este lote agendado?')) return;
    try { if(await _eliminarProxFuerza(id)) cargarNecesidades(); }
    catch(e) { alert('Error: ' + e.message); }
  }

  // ── Plan en curso · bitácora de lotes agendados ─────────────────
  const PEC_ESTADO_COLORS = {
    'pendiente':           {bg:'#fef3c7', text:'#854d0e', emoji:'⏳'},
    'programado':          {bg:'#dbeafe', text:'#1e40af', emoji:'📅'},
    'en_curso':            {bg:'#fed7aa', text:'#9a3412', emoji:'⚙️'},
    'esperando_recurso':   {bg:'#fde68a', text:'#78350f', emoji:'⏸'},
    'completado':          {bg:'#dcfce7', text:'#166534', emoji:'✓'},
    'cancelado':           {bg:'#fee2e2', text:'#991b1b', emoji:'✕'},
  };

  async function cargarPlanEnCurso() {
    const div = document.getElementById('pec-contenido');
    if (!div) return;
    div.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:40px">Cargando…</div>';
    const estados = Array.from(document.querySelectorAll('.pec-est:checked')).map(c => c.value);
    if (!estados.length) {
      div.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:40px">Marcá al menos un estado.</div>';
      return;
    }
    const qs = new URLSearchParams();
    qs.set('estados', estados.join(','));
    const desde = document.getElementById('pec-desde').value;
    const hasta = document.getElementById('pec-hasta').value;
    if (desde) qs.set('desde', desde);
    if (hasta) qs.set('hasta', hasta);

    try {
      const r = await fetch('/api/plan/proximas?' + qs.toString());
      if (r.status === 401) { window.location.href = '/login'; return; }
      const d = await r.json();
      renderPlanEnCurso(d.items || []);
    } catch(e) {
      div.innerHTML = '<div style="text-align:center;color:#dc2626;padding:40px">Error: ' + escapeHtmlNec(e.message) + '</div>';
    }
  }

  function renderPlanEnCurso(items) {
    const div = document.getElementById('pec-contenido');
    if (!items.length) {
      div.innerHTML = '<div style="text-align:center;padding:60px 20px;color:#64748b">'
        + '<div style="font-size:48px;opacity:0.4;margin-bottom:12px">📅</div>'
        + '<div style="font-size:14px;font-weight:600;margin-bottom:6px">Sin lotes con estos filtros</div>'
        + '<div style="font-size:12px;color:#94a3b8">Andá a Necesidades → ⚡ Solicitar para agendar uno</div>'
        + '</div>';
      return;
    }
    let html = '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px;min-width:720px">';
    html += '<thead><tr style="background:#f8fafc;color:#475569">';
    html += '<th style="text-align:center;padding:10px 6px;font-weight:700">Fecha</th>';
    html += '<th style="text-align:left;padding:10px 6px;font-weight:700">Producto</th>';
    html += '<th style="text-align:center;padding:10px 6px;font-weight:700">kg</th>';
    html += '<th style="text-align:center;padding:10px 6px;font-weight:700">Sala</th>';
    html += '<th style="text-align:center;padding:10px 6px;font-weight:700">Origen</th>';
    html += '<th style="text-align:center;padding:10px 6px;font-weight:700">Estado</th>';
    html += '<th style="text-align:left;padding:10px 6px;font-weight:700">Notas</th>';
    html += '<th style="padding:10px 6px;width:120px"></th>';
    html += '</tr></thead><tbody>';
    items.forEach(it => {
      const cfg = PEC_ESTADO_COLORS[it.estado] || {bg:'#e2e8f0', text:'#475569', emoji:''};
      const orig = it.origen === 'eos_plan' ? '🆕 EOS' :
                   it.origen === 'eos_canonico' ? '🔁 Canónico' :
                   it.origen === 'eos_retroactivo' ? '📜 Histórico' :
                   it.origen === 'calendar' ? '📆 Calendar' :
                   it.origen === 'manual' ? '✋ Manual' : escapeHtmlNec(it.origen || '—');
      html += '<tr style="border-bottom:1px solid #f1f5f9">';
      html += '<td style="padding:9px 6px;text-align:center;font-weight:700">' + escapeHtmlNec(it.fecha_programada) + '</td>';
      html += '<td style="padding:9px 6px">' + escapeHtmlNec(it.producto) + '</td>';
      html += '<td style="padding:9px 6px;text-align:center">' + (it.kg_real != null ? it.kg_real + ' <span style="color:#94a3b8">/' + it.cantidad_kg + '</span>' : it.cantidad_kg) + '</td>';
      html += '<td style="padding:9px 6px;text-align:center">' + (it.area_codigo || '—') + '</td>';
      html += '<td style="padding:9px 6px;text-align:center;font-size:11px">' + orig + '</td>';
      html += '<td style="padding:9px 6px;text-align:center"><span style="background:' + cfg.bg + ';color:' + cfg.text + ';padding:3px 9px;border-radius:6px;font-size:11px;font-weight:700">' + cfg.emoji + ' ' + escapeHtmlNec(it.estado) + '</span></td>';
      html += '<td style="padding:9px 6px;color:#64748b;font-size:11px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + escapeHtmlNec(it.observaciones || '') + '">' + escapeHtmlNec((it.observaciones || '').slice(0, 40)) + '</td>';
      html += '<td style="padding:9px 6px;text-align:right;white-space:nowrap">';
      if (it.estado === 'pendiente' || it.estado === 'programado') {
        html += '<button onclick="moverPEC(' + it.id + ',&#39;' + escapeHtmlNec(it.producto) + '&#39;,&#39;' + escapeHtmlNec(it.fecha_programada) + '&#39;)" style="background:transparent;border:1px solid #6d28d9;color:#6d28d9;padding:4px 8px;border-radius:4px;font-size:11px;cursor:pointer;margin-right:4px" title="Cambiar fecha">📅 Mover</button>';
        html += '<button onclick="pausarPEC(' + it.id + ',&#39;' + escapeHtmlNec(it.producto) + '&#39;)" style="background:transparent;border:1px solid #ca8a04;color:#ca8a04;padding:4px 8px;border-radius:4px;font-size:11px;cursor:pointer;margin-right:4px" title="Pausar · esperando MP u otro recurso">⏸ Pausar</button>';
        html += '<button onclick="cancelarPEC(' + it.id + ')" style="background:transparent;border:1px solid #cbd5e1;color:#64748b;padding:4px 10px;border-radius:4px;font-size:11px;cursor:pointer">Cancelar</button>';
      } else if (it.estado === 'esperando_recurso') {
        html += '<button onclick="reactivarPEC(' + it.id + ',&#39;' + escapeHtmlNec(it.producto) + '&#39;,&#39;' + escapeHtmlNec(it.fecha_programada) + '&#39;)" style="background:#16a34a;color:white;border:none;padding:4px 10px;border-radius:4px;font-size:11px;cursor:pointer;margin-right:4px" title="Reactivar · ya llegó el recurso">▶ Reactivar</button>';
        html += '<button onclick="cancelarPEC(' + it.id + ')" style="background:transparent;border:1px solid #cbd5e1;color:#64748b;padding:4px 10px;border-radius:4px;font-size:11px;cursor:pointer">Cancelar</button>';
      }
      html += '</td></tr>';
    });
    html += '</tbody></table></div>';
    // Resumen
    const conteo = {};
    items.forEach(it => { conteo[it.estado] = (conteo[it.estado]||0) + 1; });
    let chips = '<div style="padding:10px 14px;border-top:1px solid #e2e8f0;background:#f8fafc;display:flex;gap:8px;flex-wrap:wrap">';
    Object.entries(conteo).forEach(([est, n]) => {
      const cfg = PEC_ESTADO_COLORS[est] || {bg:'#e2e8f0', text:'#475569', emoji:''};
      chips += '<span style="background:' + cfg.bg + ';color:' + cfg.text + ';padding:3px 9px;border-radius:6px;font-size:11px;font-weight:700">' + cfg.emoji + ' ' + est + ': ' + n + '</span>';
    });
    chips += '</div>';
    div.innerHTML = html + chips;
  }

  async function cancelarPEC(id) {
    if (!confirm('¿Cancelar este lote agendado?')) return;
    try { if(await _eliminarProxFuerza(id)) cargarPlanEnCurso(); }
    catch(e) { alert('Error: ' + e.message); }
  }

  async function moverPEC(id, producto, fechaActual) {
    const fNueva = prompt('📅 Mover producción\n\n' + producto + '\nFecha actual: ' + fechaActual +
                          '\n\nNueva fecha (YYYY-MM-DD):', fechaActual);
    if (!fNueva || fNueva === fechaActual) return;
    if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(fNueva.trim())) {
      alert('Formato inválido · usa YYYY-MM-DD');
      return;
    }
    const razon = prompt('Razón (opcional · ej: falta_mp, operario_ausente):', 'falta_mp') || '';
    try {
      let r = await fetch('/api/plan/proximas/' + id + '/reprogramar', {
        method: 'POST',
        headers: {'Content-Type':'application/json', 'X-CSRF-Token': csrfTokenNec()},
        body: JSON.stringify({nueva_fecha: fNueva.trim(), razon: razon.trim()}),
      });
      let d = await r.json();
      // 422 = validación de día (festivo, lote grande, etc) · ofrecer forzar
      if (r.status === 422) {
        if (confirm('⚠ ' + (d.error || 'Validación falló') + '\n\n¿Forzar reprogramación de todos modos?')) {
          r = await fetch('/api/plan/proximas/' + id + '/reprogramar', {
            method: 'POST',
            headers: {'Content-Type':'application/json', 'X-CSRF-Token': csrfTokenNec()},
            body: JSON.stringify({nueva_fecha: fNueva.trim(), razon: razon.trim(), skip_validacion_dia: true}),
          });
          d = await r.json();
        } else {
          return;
        }
      }
      if (!r.ok) { alert('Error: ' + (d.error || r.status)); return; }
      if (d.noop) { alert('Misma fecha · sin cambios'); return; }
      alert('✓ Reprogramado: ' + d.fecha_antes + ' → ' + d.fecha_nueva);
      cargarPlanEnCurso();
    } catch(e) { alert('Error: ' + e.message); }
  }

  async function pausarPEC(id, producto) {
    const motivo = prompt('⏸ Pausar producción\n\n' + producto +
                            '\n\nMotivo (falta_mp, operario_ausente, equipo_mantenimiento, espera_QC, etc):',
                            'falta_mp');
    if (!motivo || !motivo.trim()) return;
    try {
      const r = await fetch('/api/plan/proximas/' + id + '/pausar', {
        method: 'POST',
        headers: {'Content-Type':'application/json', 'X-CSRF-Token': csrfTokenNec()},
        body: JSON.stringify({motivo_pausa: motivo.trim()}),
      });
      const d = await r.json();
      if (!r.ok) { alert('Error: ' + (d.error || r.status)); return; }
      alert('⏸ Pausado · esperando: ' + d.motivo_pausa);
      cargarPlanEnCurso();
      // Recargar Necesidades también para reflejar pausa
      if (typeof cargarNecesidades === 'function') cargarNecesidades();
    } catch(e) { alert('Error: ' + e.message); }
  }

  async function reactivarPEC(id, producto, fechaActual) {
    const nueva = prompt('▶ Reactivar producción\n\n' + producto +
                           '\nFecha pausada: ' + fechaActual +
                           '\n\nNueva fecha (YYYY-MM-DD · deja vacío para conservar):',
                           fechaActual);
    if (nueva === null) return;
    const fechaParam = (nueva && nueva.trim()) ? nueva.trim() : '';
    try {
      let r = await fetch('/api/plan/proximas/' + id + '/reactivar', {
        method: 'POST',
        headers: {'Content-Type':'application/json', 'X-CSRF-Token': csrfTokenNec()},
        body: JSON.stringify(fechaParam ? {nueva_fecha: fechaParam} : {}),
      });
      let d = await r.json();
      if (r.status === 422) {
        if (confirm('⚠ ' + (d.error || 'Validación falló') + '\n\n¿Forzar?')) {
          r = await fetch('/api/plan/proximas/' + id + '/reactivar', {
            method: 'POST',
            headers: {'Content-Type':'application/json', 'X-CSRF-Token': csrfTokenNec()},
            body: JSON.stringify({nueva_fecha: fechaParam, skip_validacion_dia: true}),
          });
          d = await r.json();
        } else { return; }
      }
      if (!r.ok) { alert('Error: ' + (d.error || r.status)); return; }
      alert('▶ Reactivado · fecha: ' + d.fecha_programada);
      cargarPlanEnCurso();
      if (typeof cargarNecesidades === 'function') cargarNecesidades();
    } catch(e) { alert('Error: ' + e.message); }
  }

  function renderResumenNec(res) {
    if (!res) return;
    const items = [
      ['🔴 Crítico', res.n_critico, '#dc2626'],
      ['🟠 Urgente', res.n_urgente, '#ea580c'],
      ['🟡 Vigilar', res.n_vigilar, '#ca8a04'],
      ['🔵 Por entrar', res.n_por_entrar, '#0891b2'],
      ['🟢 OK', res.n_ok, '#16a34a'],
      ['⚪ Sin ventas', res.n_sin_ventas, '#64748b'],
      ['📦 Pedidos B2B', res.n_pedidos_b2b_pendientes, '#1e40af'],
    ];
    document.getElementById('nec-resumen').innerHTML = items.map(it =>
      '<div style="background:var(--cx-card,#fff);border:1px solid var(--cx-hairline,#ece9f5);border-top:3px solid '+it[2]+';border-radius:14px;padding:14px 18px;flex:1;min-width:120px;text-align:center;box-shadow:0 1px 3px rgba(16,15,45,.06),0 12px 26px -14px rgba(16,15,45,.14)">'
      + '<div style="font-size:11px;color:var(--cx-text-mute,#64748b);font-weight:700;letter-spacing:.02em">'+it[0]+'</div>'
      + '<div style="font-size:26px;font-weight:800;color:'+it[2]+';line-height:1.1;margin-top:3px">'+it[1]+'</div>'
      + '</div>'
    ).join('');
  }

  // Cache global productos · key = índice numérico estable (codigo_pt
  // puede colisionar: varios "CONT..." o "SUER..." con fallback de 4 letras).
  window._NEC_PRODUCTOS_CACHE = [];

  // Sebastián 4-jul · pasada de diseño premium de Necesidades (tabla + desglose wow). CSS inyectado
  // 1 sola vez con clases propias (prefijo necx- · M61 no reusar clases del framework).
  function _ensureNecxStyle(){
    if(document.getElementById('necx-style')) return;
    var s = document.createElement('style'); s.id = 'necx-style';
    s.textContent = '.necx-thead th{text-transform:uppercase;letter-spacing:.04em;font-size:11px;color:#64748b;font-weight:700}'
      + '.necx-prow{transition:box-shadow .14s ease}'
      + '.necx-prow:hover{box-shadow:inset 0 0 0 9999px rgba(99,102,241,.035)}'
      + '.necx-exp{margin-top:2px}'
      + '.necx-sum{list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:6px;font-size:10px;font-weight:700;color:#64748b;background:#f1f5f9;border:1px solid #e2e8f0;border-radius:999px;padding:3px 11px;transition:all .18s ease;user-select:none}'
      + '.necx-sum::-webkit-details-marker{display:none}'
      + '.necx-sum::marker{content:""}'
      + '.necx-sum:hover{background:#e2e8f0;color:#334155}'
      + '.necx-swstrip{display:inline-flex;gap:3px;margin-left:5px}'
      + '.necx-swdot{width:10px;height:10px;border-radius:50%;box-shadow:0 0 0 1.5px #fff,0 0 0 2.5px rgba(0,0,0,.08)}'
      + '.necx-chev{display:inline-block;transition:transform .2s ease;font-size:9px}'
      + '.necx-exp[open] .necx-chev{transform:rotate(90deg)}'
      + '.necx-expbody{margin-top:10px;animation:necxIn .25s ease}'
      + '@keyframes necxIn{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}'
      + '.necx-ttbl{width:100%;border-collapse:separate;border-spacing:0;font-size:11px;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(157,23,109,.08)}'
      + '.necx-ttbl thead th{text-align:center;padding:7px 8px;font-weight:700;color:#9d174d;background:#fdf2f8;font-size:10px;text-transform:uppercase;letter-spacing:.03em}'
      + '.necx-ttbl thead th:first-child{text-align:left}'
      + '.necx-trow td{padding:7px 8px;text-align:center;border-top:1px solid #fbe4ef;transition:background .12s}'
      + '.necx-trow:hover td{background:#fdf6fa}'
      + '.necx-ttbl td:first-child{text-align:left;font-weight:700;color:#9d174d}'
      + '.necx-swatch{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:7px;vertical-align:-1px;box-shadow:0 0 0 1px rgba(0,0,0,.1)}'
      + '.necx-mono{font-family:ui-monospace,monospace;color:#64748b}'
      + '.necx-mix{font-weight:800;color:#be185d}'
      + '.necx-uds{font-weight:800;color:#9d174d}'
      + '.necx-note{font-size:10px;color:#94a3b8;margin-top:7px;padding-left:2px}'
      + '.b2bx{border:none;border-radius:7px;padding:5px 12px;font-size:10.5px;font-weight:700;cursor:pointer;transition:all .15s ease;display:inline-flex;align-items:center;gap:4px;margin-left:5px;box-shadow:0 1px 2px rgba(0,0,0,.1);letter-spacing:.01em}'
      + '.b2bx:hover{transform:translateY(-1px);box-shadow:0 4px 10px rgba(0,0,0,.16)}'
      + '.b2bx:active{transform:translateY(0);box-shadow:0 1px 2px rgba(0,0,0,.1)}'
      + '.b2bx-assign{background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff}'
      + '.b2bx-confirm{background:linear-gradient(135deg,#8b5cf6,#6d28d9);color:#fff}'
      + '.b2bx-ghost{background:#fff;border:1px solid #e2e8f0;color:#94a3b8;box-shadow:none;font-weight:600}'
      + '.b2bx-ghost:hover{background:#fef2f2;border-color:#fca5a5;color:#dc2626;transform:none;box-shadow:none}';
    document.head.appendChild(s);
  }
  // color estable por tono (hash del nombre → HSL) para el swatch del desglose.
  function _tonoColor(lbl){
    var s = String(lbl || ''), h = 0, i;
    for(i = 0; i < s.length; i++){ h = (h * 31 + s.charCodeAt(i)) % 360; }
    return 'hsl(' + h + ',60%,58%)';
  }
  // Sebastián 4-jul · traer la foto del producto desde Shopify al vuelo (el rebuild de fórmula del 1-jul
  // borró imagen_url) · matchea por SKU mapeado. Click en el placeholder 📦 del modal.
  async function _traerFotoShopify(el){
    var prod = el.getAttribute('data-prod'); if(!prod) return;
    var _orig = el.innerHTML, _w = el.style.width || '80px', _h = el.style.height || '80px';
    el.style.opacity = '.6'; el.innerHTML = '<span style="font-size:12px">⏳</span>';
    try{
      var t = (await (await fetch('/api/csrf-token', {credentials:'same-origin'})).json()).csrf_token;
      var r = await fetch('/api/formulas/' + encodeURIComponent(prod) + '/imagen-shopify-sync', {method:'POST', credentials:'same-origin', headers:{'X-CSRF-Token':t}});
      var d = await r.json().catch(function(){ return {}; });
      var _img = d && (d.imagen_url || d.imagen);
      if(r.ok && _img){
        el.outerHTML = '<img src="' + _img + '" alt="" style="width:' + _w + ';height:' + _h + ';object-fit:cover;border-radius:8px">';
      } else if(r.ok){
        el.style.opacity = '1'; el.innerHTML = _orig; alert('Sincronizó, pero Shopify no tiene foto para "' + prod + '".');
      } else {
        el.style.opacity = '1'; el.innerHTML = _orig; alert('No se pudo traer la foto: ' + ((d && d.error) || r.status));
      }
    }catch(e){ el.style.opacity = '1'; el.innerHTML = _orig; alert('Error: ' + e); }
  }

  function renderClientesNec(clientes) {
    _ensureNecxStyle();
    const div = document.getElementById('nec-contenido');
    if (!clientes || !clientes.length) { div.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:40px">Sin datos.</div>'; return; }
    window._NEC_PRODUCTOS_CACHE = [];  // reset cache en cada render
    let html = '';
    clientes.forEach(cli => {
      if (cli.tipo === 'shopify_auto') html += renderAnimusSection(cli);
      else if (cli.tipo === 'b2b_manual') html += renderB2BSection(cli);
    });
    div.innerHTML = html;
  }

  function renderAnimusSection(cli) {
    const prods = cli.productos || [];
    // Cachear con índice estable · base = tamaño actual del cache
    const baseIdx = window._NEC_PRODUCTOS_CACHE.length;
    prods.forEach(p => { window._NEC_PRODUCTOS_CACHE.push(p); });
    // Chips resumen por urgencia
    const conteos = {CRITICO:0, URGENTE:0, VIGILAR:0, POR_ENTRAR:0, OK:0, SIN_VENTAS:0, SIN_MAPEO:0, SIN_HISTORIAL:0, SIN_VENTAS_REAL:0};
    prods.forEach(p => { if (conteos[p.urgencia] !== undefined) conteos[p.urgencia]++; });
    let chips = '';
    ['CRITICO','URGENTE','VIGILAR','POR_ENTRAR','OK','SIN_VENTAS','SIN_MAPEO','SIN_HISTORIAL','SIN_VENTAS_REAL'].forEach(u => {
      if (conteos[u] > 0) {
        const cfg = URG_COLORS[u];
        chips += '<span style="background:'+cfg.bg+';color:'+cfg.text+';padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;margin-left:4px">' + cfg.emoji + ' ' + conteos[u] + '</span>';
      }
    });

    // Sebastián 25-may-2026 PM · arranca cerrado · "que para toda la app
    // salgan colapsados y ya uno escoja si los abre".
    let html = '<details style="background:white;border-radius:14px;margin-bottom:14px;border:1px solid #e2e8f0;overflow:hidden">';
    html += '<summary style="cursor:pointer;padding:14px 18px;background:linear-gradient(90deg,#f0fdfa,#ecfeff);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">';
    html += '<div><span style="color:#6d28d9;font-size:16px;font-weight:800">🛍️ ' + escapeHtmlNec(cli.cliente_nombre) + '</span>';
    html += ' <span style="font-size:11px;font-weight:500;color:#94a3b8">· Shopify auto · ' + prods.length + ' SKUs</span></div>';
    html += '<div>' + chips + '</div></summary>';
    html += '<div style="padding:14px 18px;overflow-x:auto">';

    if (!prods.length) {
      html += '<div style="text-align:center;color:#94a3b8;padding:20px">Sin productos con codigo_pt · ejecutá mig 118 seed.</div>';
    } else {
      // Tabla mínima · Sebastián 13-may-2026 "hablemos directo": producto,
      // vende día/mes, alcanza, estado, botón solicitar. Todo lo demás
      // (presentación, horizonte, sugerencias) vive en el modal único
      // que abre el botón.
      // Vista mínima · Sebastián 14-may-2026: "siento que necesidades
      // quedo cargado de mil cosas que necesitamos poner es en este
      // calendario EOS ia, y dejamos mejor las necesidades solitas que
      // diga nada mas y programar te parece?"
      // Solo: producto + urgencia · demanda · cobertura · stock · botón
      // Todo lo complejo (plan / MPs / IA / horizonte) vive en /admin/plan-calendario
      html += '<table style="width:100%;border-collapse:collapse;font-size:13px">';
      html += '<thead><tr class="necx-thead" style="background:#f8fafc;color:#475569">';
      html += '<th style="text-align:left;padding:10px 8px;font-weight:700">Producto</th>';
      html += '<th style="text-align:center;padding:10px 8px;font-weight:700">Vende/día</th>';
      html += '<th style="text-align:center;padding:10px 8px;font-weight:700">Vende/mes</th>';
      html += '<th style="text-align:center;padding:10px 8px;font-weight:700">Stock</th>';
      html += '<th style="text-align:center;padding:10px 8px;font-weight:700">Alcanza</th>';
      html += '<th style="text-align:left;padding:10px 8px;font-weight:700">Plan 2 años · acción</th>';
      html += '<th style="text-align:right;padding:10px 8px;font-weight:700">Programar</th>';
      html += '</tr></thead><tbody>';
      prods.forEach((p, j) => {
        const idx = baseIdx + j;
        const cfg = URG_COLORS[p.urgencia] || URG_COLORS.OK;
        // FIX 1-jun-2026 · "centro real de necesidades en tiempo real": la columna
        // Alcanza ahora muestra los días REALES de góndola (stock físico/velocidad),
        // NO la cobertura-con-pipeline (que daba "95.9d" con góndola 0 y parecía
        // estático). El color sale de los días reales. dias_cobertura (incluye lotes
        // programados/en producción) se muestra como anotación "+prod → Xd".
        const _dg = (p.dias_gondola != null) ? p.dias_gondola : null;
        const dias = _dg != null ? _dg + 'd' : (p.dias_cobertura != null ? p.dias_cobertura + 'd' : '—');
        // El color del número = el MISMO del semáforo (urgencia del backend), para que
        // número y emoji nunca se contradigan (M5). Fallback por días si no hay urgencia.
        const _urgCol = {CRITICO:'#dc2626', URGENTE:'#ea580c', VIGILAR:'#d97706', POR_ENTRAR:'#0891b2', OK:'#16a34a'};
        const diasColorReal = (_dg == null) ? cfg.text
                            : (_urgCol[p.urgencia] || (_dg < 20 ? '#dc2626' : (_dg < 45 ? '#d97706' : '#16a34a')));
        // FIX 1-jun-2026 · en vez del confuso "+prod → Xd" (cobertura con el lote
        // grande / venta chica daba 355d), mostrar el PRÓXIMO LOTE: cuántas uds
        // entran para Animus DTC y cuándo. Más claro y accionable.
        let _prodInfo = '';
        const _pl = p.proximo_lote;
        if (_pl && _pl.fecha) {
          if (_pl.atrasado) {
            // M14 · lote programado con fecha ya pasada que no se ejecutó → ATRASADO,
            // no reposición que viene. Se pinta en rojo para que no dé falsa tranquilidad.
            _prodInfo = '<div style="font-size:9px;color:#dc2626;font-weight:700" title="Hay un lote programado para una fecha YA PASADA que no se ha ejecutado. Está atrasado/atascado, no es reposición en camino. Revisá por qué no se produjo.">⚠ lote atrasado ' + _pl.fecha.slice(5,10) + ' · sin ejecutar</div>';
          } else {
            const _mlu = p.ml_unidad || 30;
            const _kgIn = (_pl.kg_dtc != null ? _pl.kg_dtc : _pl.kg) || 0;
            const _udsIn = (_mlu > 0) ? Math.round(_kgIn * 1000 / _mlu) : 0;
            if (_udsIn > 0) {
              if (p.lote_tarde) {
                // El stock se agota ANTES de que llegue este lote → adelantar
                _prodInfo = '<div style="font-size:9px;color:#dc2626;font-weight:700" title="El stock físico se agota el ' + (p.agota_fecha||'') + ' pero el lote llega el ' + _pl.fecha.slice(0,10) + ' → ' + (p.dias_descubierto||0) + ' día(s) sin stock. Adelantá la producción.">⏩ lote TARDE ' + _pl.fecha.slice(5,10) + ' · ' + (p.dias_descubierto||0) + 'd sin stock</div>';
              } else {
                _prodInfo = '<div style="font-size:9px;color:#2563eb" title="próximo lote programado · unidades que entran para Animus DTC">📦 +' + _udsIn.toLocaleString('es-CO') + ' uds · ' + _pl.fecha.slice(5,10) + '</div>';
              }
            }
          }
        }
        // Estado de programación · explícito para CADA producto. El positivo
        // (📅 fecha) ya lo pinta chipPlan junto al nombre; acá resaltamos el caso
        // ACCIONABLE: cobertura física baja Y sin lote programado → "⚠ Sin programar".
        const _tienePlan = (p.planificacion || []).length > 0;
        let estadoProgHtml = '';
        if (!_tienePlan && p.velocidad_uds_dia > 0 && _dg != null && _dg < 40) {
          estadoProgHtml = '<div style="font-size:9px;color:#dc2626;font-weight:700;margin-top:2px" title="Cobertura física baja y sin lote programado · requiere acción">⚠ Sin programar</div>';
        }
        const codDisp = escapeHtmlNec(p.codigo_pt || '');
        const ventaMes = Math.round(p.velocidad_uds_dia * 30);
        const mlReal = p.ml_unidad || 30;
        // Alerts mínimos · solo si crítico
        let alertSinSku = p.sin_mapeo_shopify ? ' <span title="Sin mapeo Shopify" style="color:#dc2626;font-size:11px">🛒</span>' : '';
        // Indicador "ya programado" minimal (cuántos lotes activos)
        let chipPlan = '';
        if ((p.planificacion || []).length) {
          const _atr = !!(p.proximo_lote && p.proximo_lote.atrasado);
          const proxFecha = (p.proximo_lote && p.proximo_lote.fecha) ? p.proximo_lote.fecha.slice(5, 10) : '';
          const _cBg = _atr ? '#fee2e2' : '#dbeafe', _cFg = _atr ? '#991b1b' : '#1e40af';
          const _cTit = _atr ? 'Lote programado para fecha pasada SIN ejecutar (atrasado) · click Programar para gestionar'
                             : (p.planificacion.length + ' lote(s) agendado(s) · click Programar para gestionar');
          chipPlan = ' <span title="' + _cTit + '" style="background:'+_cBg+';color:'+_cFg+';padding:1px 6px;border-radius:4px;font-size:10px;font-weight:700">📅 ' + (_atr?'⚠ ':'') + proxFecha + '</span>';
        }
        // FEATURE B2B 24-may-2026 · chip B2B si algún lote tiene aportes B2B.
        // Muestra "+Xkg B2B" + tooltip con clientes (Fernando, etc.).
        let chipB2B = '';
        const lotesConB2B = (p.planificacion || []).filter(l => l.tiene_b2b);
        if (lotesConB2B.length) {
          const kgB2B = lotesConB2B.reduce((s, l) => s + (l.kg_b2b || 0), 0);
          const clientes = new Set();
          lotesConB2B.forEach(l => (l.aportes_b2b || []).forEach(a => clientes.add(a.cliente || '?')));
          const ttip = lotesConB2B.length + ' lote(s) con B2B · ' + [...clientes].join(', ');
          chipB2B = ' <span title="' + ttip + '" style="background:#fdf4ff;color:#7e22ce;padding:1px 6px;border-radius:4px;font-size:10px;font-weight:700">🤝 +' + kgB2B.toFixed(1) + 'kg</span>';
        }

        // FIX UX 24-may PM · jerarquía visual · fila completa con tinte
        // de fondo + borde izquierdo grueso si crítico/urgente. OK/sin-ventas
        // se atenúan para que los rojos canten.
        const _esGrave = (p.urgencia === 'CRITICO' || p.urgencia === 'URGENTE');
        const _esPorEntrar = (p.urgencia === 'POR_ENTRAR');
        const _esOk = (p.urgencia === 'OK');
        // OK ya NO se atenúa (se veía gris/apagado · Sebastián 5-jul) → tinte verde suave + borde + opacidad
        // plena, se ve "sano". Solo se atenúan los SIN_VENTAS (realmente ignorables). Los rojos cantan por su fondo.
        const _esIgnorable = (p.urgencia === 'SIN_VENTAS' || p.urgencia === 'SIN_VENTAS_REAL');
        const _rowBg = _esGrave ? cfg.bg : (_esPorEntrar ? '#ecfeff' : (_esOk ? '#f3fdf7' : '#fff'));
        const _rowBorderL = _esGrave ? ('4px solid ' + cfg.border) : (_esPorEntrar ? '4px solid #0891b2' : (_esOk ? '4px solid #4ade80' : '4px solid transparent'));
        const _rowOpacity = _esIgnorable ? '0.6' : '1';
        // Sebastián 25-may-2026 PM · chip 🎨 si producto tiene ≥2 tonos
        // (caso LIP SERUM 5 tonos · cada tono envase distinto).
        let chipTonos = '';
        const _tonos = p.tonos || [];
        if (_tonos.length >= 2) {
          chipTonos = ' <span title="' + _tonos.length + ' tonos · click fila para desglose" style="background:#fdf2f8;color:#be185d;padding:1px 6px;border-radius:4px;font-size:10px;font-weight:700;cursor:pointer">🎨 ' + _tonos.length + ' tonos</span>';
        }
        // ===== Sebastián 4-jul · ESTADO DE CADENA (plan 2 años) + ALERTA inteligente por producto =====
        var _hoyN = new Date().toISOString().slice(0,10);
        var _cad = (p.planificacion || []).filter(function(l){ var f = ('' + (l.fecha || '')).slice(0,10); return l.origen === 'eos_plan' && f > _hoyN && (l.estado||'') !== 'cancelado' && (l.estado||'') !== 'completado'; });
        var _nCad = _cad.length;
        var _fc = _cad.map(function(l){ return ('' + l.fecha).slice(0,10); }).sort();
        var _spanC = _fc.length >= 2 ? Math.round((new Date(_fc[_fc.length-1] + 'T12:00:00') - new Date(_fc[0] + 'T12:00:00')) / 86400000) : 0;
        var _cadEst = (_nCad === 0) ? 'sin' : ((_nCad < 4 || _spanC < 480) ? 'inc' : 'ok');
        var _cadBadge = _cadEst === 'ok' ? '<span title="Cadena de 2 años completa" style="background:#dcfce7;color:#15803d;padding:2px 7px;border-radius:5px;font-size:10px;font-weight:800">✅ ' + _nCad + ' lotes</span>'
                      : _cadEst === 'inc' ? '<span title="Cadena incompleta · reprogramá" style="background:#fef3c7;color:#b45309;padding:2px 7px;border-radius:5px;font-size:10px;font-weight:800">🟠 ' + _nCad + ' lote' + (_nCad === 1 ? '' : 's') + '</span>'
                      : '<span title="Sin cadena de 2 años · programala" style="background:#fee2e2;color:#b91c1c;padding:2px 7px;border-radius:5px;font-size:10px;font-weight:800">🔴 sin plan</span>';
        var _tend = p.tendencia || 0, _tp = Math.round(_tend * 100);   // tendencia 0..0.5 · positiva = ascenso
        var _al, _alc;
        if(!(p.velocidad_uds_dia > 0.001)){ _al = '🛒 sin ventas mapeadas · revisá el SKU'; _alc = '#94a3b8'; }
        else if(_cadEst === 'sin'){ _al = '🔴 programá la cadena de 2 años'; _alc = '#dc2626'; }
        else if(_cadEst === 'inc'){ _al = '🟠 cadena incompleta · reprogramá'; _alc = '#d97706'; }
        else if(_tend >= 0.08){ _al = '📈 ventas +' + _tp + '% · considerá adelantar'; _alc = '#7c3aed'; }
        else if(p.lote_tarde || p.accion_sugerida === 'adelantar'){ _al = '⏩ adelantá la próxima'; _alc = '#dc2626'; }
        else if(p.accion_sugerida === 'atrasar'){ _al = '📉 vas holgado · podés atrasar'; _alc = '#0891b2'; }
        else if(_tend >= 0.04){ _al = '📈 ventas +' + _tp + '% en ascenso'; _alc = '#7c3aed'; }
        else { _al = '✅ al día'; _alc = '#16a34a'; }
        var _proxTxt = p.proxima_sugerida_fecha ? ('próxima ' + ('' + p.proxima_sugerida_fecha).slice(5,10)) : '';
        // Sebastián 10-jul · modelo canónico manual: badge/estado NEUTRO, sin sugerencias
        // (adelantar/atrasar/tendencia/incompleta) · solo muestra si hay o no cadena manual.
        if (window.__SOLO_MANUAL) {
          _cadBadge = _nCad > 0
            ? '<span title="Lotes programados (cadena manual)" style="background:#dcfce7;color:#15803d;padding:2px 7px;border-radius:5px;font-size:10px;font-weight:800">📅 ' + _nCad + ' lote' + (_nCad === 1 ? '' : 's') + '</span>'
            : '<span title="Sin cadena · programala con el botón Programar" style="background:#f1f5f9;color:#64748b;padding:2px 7px;border-radius:5px;font-size:10px;font-weight:800">⚪ sin programar</span>';
          _al = _nCad > 0 ? ('📅 ' + _nCad + ' lote' + (_nCad === 1 ? '' : 's') + ' programado' + (_nCad === 1 ? '' : 's')) : '⚪ sin programar';
          _alc = _nCad > 0 ? '#16a34a' : '#94a3b8';
          _proxTxt = '';
        }
        html += '<tr class="necx-prow" style="border-top:1px solid #e2e8f0;background:' + _rowBg + ';border-left:' + _rowBorderL + ';opacity:' + _rowOpacity + '">';
        // Producto + urgencia
        html += '<td style="padding:10px 8px">';
        html += '<div style="display:flex;align-items:center;gap:6px"><span style="background:' + cfg.bg + ';color:' + cfg.text + ';padding:2px 8px;border-radius:6px;font-size:11px;font-weight:800">' + cfg.emoji + '</span>';
        html += '<span style="font-weight:700;color:#1e293b">' + escapeHtmlNec(p.producto_nombre) + '</span>';
        // chipPlan (📅 fecha) removido del nombre · la fecha/estado del lote ya va
        // en la columna Alcanza (uds + atrasado/tarde), evita duplicar la fecha.
        html += alertSinSku + chipB2B + chipTonos;
        html += '</div>';
        html += '<div style="font-family:ui-monospace,monospace;font-size:10px;color:#94a3b8;margin-top:2px">' + codDisp + ' · ' + (Math.round(mlReal * 10) / 10) + 'ml</div>';
        html += '</td>';
        // Vende día / mes / stock / cobertura
        html += '<td style="padding:10px 8px;text-align:center">' + p.velocidad_uds_dia.toFixed(1) + '</td>';
        html += '<td style="padding:10px 8px;text-align:center">' + ventaMes + '</td>';
        html += '<td style="padding:10px 8px;text-align:center">' + p.stock_uds_total
              + ((p.por_entrar_uds||0) > 0 ? '<div style="font-size:9px;color:#0891b2;font-weight:700" title="Producido en Espagiria, aún no trasladado a Ánimus · ya cuenta para la próxima">🔵 +' + p.por_entrar_uds + ' por entrar</div>' : '')
              + '</td>';
        // Alcanza · LIMPIO (Sebastián 4-jul): cobertura (color) + próxima sugerida · sin el ruido
        // "lote atrasado sin ejecutar" (eso ahora va como alerta accionable en la columna Plan·acción).
        html += '<td style="padding:10px 8px;text-align:center">'
              + '<div style="font-weight:700;color:' + diasColorReal + '">' + dias + '</div>'
              + (_proxTxt ? ('<div style="font-size:9px;color:#64748b">' + _proxTxt + '</div>') : '')
              + '</td>';
        // Plan 2 años · alerta inteligente (estado de cadena + sugerencia accionable)
        html += '<td style="padding:10px 8px;text-align:left">'
              + '<div>' + _cadBadge + '</div>'
              + '<div style="font-size:10px;color:' + _alc + ';font-weight:700;margin-top:3px">' + _al + '</div>'
              + '</td>';
        // Programar
        html += '<td style="padding:10px 8px;text-align:right"><button onclick="abrirPlanProduccion(' + idx + ')" style="background:#6d28d9;color:#fff;border:none;padding:7px 16px;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer">📅 Programar</button></td>';
        html += '</tr>';
        // Sub-fila colapsable con desglose por tono (solo si hay ≥2 tonos)
        if (_tonos.length >= 2) {
          html += '<tr><td colspan="7" style="padding:0 14px 9px">';
          html += '<details class="necx-exp"><summary class="necx-sum"><span class="necx-chev">▸</span>Desglose por referencia · ' + _tonos.length + ' tonos/tamaños</summary>';
          html += '<div class="necx-expbody">';
          html += '<table class="necx-ttbl"><thead><tr><th>Tono</th><th>SKU</th><th>ml</th><th>Vende</th><th>Stock</th><th>% mix</th><th>Uds/lote</th><th>Cobertura</th></tr></thead><tbody>';
          _tonos.forEach(t => {
            var _cob = (t.dias_cobertura_tono != null) ? t.dias_cobertura_tono : null;
            var _esCuello = !!t.cuello;   // el tono que fija el cuello de botella (solo entre los de mix ≥5%)
            var _bajo = !!t.mix_bajo;     // tono marginal (<5% del mix) · no manda la alarma del producto
            var _cobColor = _esCuello ? '#dc2626' : (_bajo ? '#94a3b8' : (_cob != null && _cob < 25 ? '#d97706' : '#16a34a'));
            var _cobCell = (_cob == null) ? '<span style="color:#cbd5e1">—</span>'
              : ('<span style="font-weight:800;color:' + _cobColor + '">' + _cob + 'd' + (_esCuello ? ' ⚠️' : '') + '</span>');
            html += '<tr class="necx-trow"' + (_bajo ? ' style="opacity:.55"' : '') + '>'
              + '<td><span class="necx-swatch" style="background:' + _tonoColor(t.tono_label) + '"></span>' + escapeHtmlNec(t.tono_label) + '</td>'
              + '<td class="necx-mono">' + escapeHtmlNec(t.sku) + '</td>'
              + '<td>' + t.ml_unidad + '</td>'
              + '<td>' + t.ventas_ventana_uds + '</td>'
              + '<td>' + (t.stock_uds != null ? t.stock_uds : '—') + '</td>'
              + '<td class="necx-mix">' + t.porcentaje_mix + '%</td>'
              + '<td class="necx-uds">' + t.uds_estim_lote + '</td>'
              + '<td>' + _cobCell + '</td>'
              + '</tr>';
          });
          html += '</tbody></table>';
          html += '<div class="necx-note">Mix con ventas de la ventana actual · uds asumen lote bulk completo (' + (p.lote_bulk_kg||0) + 'kg) · Cobertura = stock del tono ÷ su velocidad · <span style="color:#dc2626;font-weight:700">⚠️ = el tono DOMINANTE</span> (el de mayor mix · marca la pauta del producto) · un tono/tamaño secundario en 0 NO tira el producto a crítico (se envasa junto al dominante · igual verás su cobertura acá)</div>';
          html += '</div></details></td></tr>';
        }
      });
      html += '</tbody></table>';
    }
    html += '</div></details>';
    return html;
  }

  // Renderiza lotes programados/pausados inline en Necesidades · Sebastián
  // 13-may-2026: "todo junto en necesidades asi esta integrado". Reemplaza
  // a Plan en curso · misma data, misma acciones, contexto del producto.
  // Rediseño 15-jun · lista vertical tipo timeline (antes chips apretados) ·
  // cada lote = una fila clara: fecha grande · estado · kg · origen · B2B · acciones.
  const _MESES_ABR = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
  function renderLotesInline(lotes, producto) {
    if (!lotes || !lotes.length) return '';
    const ORIGEN_LABEL = {
      'eos_plan': '🆕 manual', 'eos_canonico': '🔁 auto', 'eos_retroactivo': '📜 histórico',
      'calendar': '📆 calendar', 'manual': '✋ manual', 'auto_plan': '🤖 auto', 'sugerido': '🔁 auto',
    };
    const prodEsc = escapeHtmlNec(producto);
    const arr = lotes.slice().sort((a, b) => String(a.fecha || '').localeCompare(String(b.fecha || '')));
    let html = '<div style="display:flex;flex-direction:column;gap:8px">';
    arr.forEach(lt => {
      const cfg = PEC_ESTADO_COLORS[lt.estado] || {bg:'#e2e8f0', text:'#475569', emoji:''};
      const orig = ORIGEN_LABEL[lt.origen] || lt.origen || '';
      const f = String(lt.fecha || '');
      const dd = f.slice(8, 10), mm = parseInt(f.slice(5, 7), 10), yy = f.slice(0, 4);
      const mesAbr = (mm >= 1 && mm <= 12) ? _MESES_ABR[mm - 1] : '';
      let acc = '';
      if (lt.estado === 'pendiente' || lt.estado === 'programado') {
        // Sebastián 10-jul · usar ESTE lote como origen y recalcular TODO el horizonte (con la cadencia de arriba)
        acc += '<button onclick="recalcularHorizonteDesdeLote(' + lt.id + ',&#39;' + prodEsc + '&#39;)" title="Usar este lote como origen y recalcular todo el horizonte con la cadencia de arriba (cada X meses · kg · años)" style="background:#7c3aed;color:#fff;border:none;padding:0 9px;height:28px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer">📌 recalcular</button>';
        acc += '<button onclick="moverPEC(' + lt.id + ',&#39;' + prodEsc + '&#39;,&#39;' + f + '&#39;)" title="Mover fecha" style="background:#fff;border:1px solid #c4b5fd;color:#6d28d9;width:28px;height:28px;border-radius:6px;font-size:13px;cursor:pointer">📅</button>';
        acc += '<button onclick="pausarPEC(' + lt.id + ',&#39;' + prodEsc + '&#39;)" title="Pausar" style="background:#fff;border:1px solid #fde68a;color:#ca8a04;width:28px;height:28px;border-radius:6px;font-size:13px;cursor:pointer">⏸</button>';
        acc += '<button onclick="cancelarPEC(' + lt.id + ')" title="Cancelar" style="background:#fff;border:1px solid #e2e8f0;color:#94a3b8;width:28px;height:28px;border-radius:6px;font-size:13px;cursor:pointer">✕</button>';
      } else if (lt.estado === 'esperando_recurso') {
        acc += '<button onclick="reactivarPEC(' + lt.id + ',&#39;' + prodEsc + '&#39;,&#39;' + f + '&#39;)" title="Reactivar" style="background:#16a34a;color:#fff;border:none;padding:0 10px;height:28px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">▶ Reactivar</button>';
        acc += '<button onclick="cancelarPEC(' + lt.id + ')" title="Cancelar" style="background:#fff;border:1px solid #e2e8f0;color:#94a3b8;width:28px;height:28px;border-radius:6px;font-size:13px;cursor:pointer">✕</button>';
      }
      html += '<div style="display:flex;align-items:center;gap:12px;background:#fff;border:1px solid #e2e8f0;border-left:4px solid ' + cfg.text + ';border-radius:8px;padding:8px 12px">';
      // bloque fecha
      html += '<div style="text-align:center;min-width:44px;line-height:1.1"><div style="font-size:17px;font-weight:800;color:#1e293b">' + dd + '</div><div style="font-size:10px;color:#94a3b8;text-transform:uppercase">' + mesAbr + ' ' + yy.slice(2) + '</div></div>';
      // info central
      html += '<div style="flex:1;min-width:0">';
      html += '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">';
      html += '<span style="background:' + cfg.bg + ';color:' + cfg.text + ';padding:2px 9px;border-radius:10px;font-size:10px;font-weight:700">' + cfg.emoji + ' ' + lt.estado + '</span>';
      html += '<span style="font-size:13px;font-weight:700;color:#334155">' + lt.kg + ' kg</span>';
      if (orig) html += '<span style="font-size:10px;color:#94a3b8">' + orig + '</span>';
      html += '</div>';
      if (lt.tiene_b2b && lt.kg_b2b > 0) {
        const tt = (lt.aportes_b2b || []).map(a => a.cliente + ': ' + a.kg + 'kg (' + a.n_pedidos + ' pedido' + (a.n_pedidos === 1 ? '' : 's') + ')').join(' · ');
        html += '<div title="' + tt + '" style="font-size:10px;color:#7e22ce;margin-top:3px;font-weight:700">🤝 ' + lt.kg_dtc + ' DTC + ' + lt.kg_b2b + ' B2B</div>';
      }
      if (lt.distribucion_resumen) html += '<div style="font-size:10px;color:#64748b;margin-top:3px">' + escapeHtmlNec(lt.distribucion_resumen) + '</div>';
      if (lt.motivo_pausa) html += '<div style="font-size:10px;color:#92400e;margin-top:3px">⏸ ' + escapeHtmlNec(lt.motivo_pausa) + '</div>';
      html += '</div>';
      // acciones
      html += '<div style="display:flex;gap:5px;flex-shrink:0">' + acc + '</div>';
      html += '</div>';
    });
    html += '</div>';
    return html;
  }

  function renderDrillPanel(p, idx) {
    const cfg = URG_COLORS[p.urgencia] || URG_COLORS.OK;
    const imgHtml = p.imagen_url
      ? '<img loading="lazy" decoding="async" src="' + escapeHtmlNec(p.imagen_url) + '" alt="" style="width:100px;height:100px;object-fit:cover;border-radius:10px;background:#f1f5f9" onerror="this.style.display=&#39;none&#39;">'
      : '<div onclick="_traerFotoShopify(this)" data-prod="' + escapeHtmlNec(p.producto_nombre) + '" title="Click para traer la foto de Shopify" style="width:100px;height:100px;background:linear-gradient(135deg,#e2e8f0,#cbd5e1);border-radius:10px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:30px;color:#64748b;cursor:pointer">📦<span style="font-size:9px;color:#475569;font-weight:700;margin-top:2px">traer foto</span></div>';
    let html = '<div style="display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap">';
    html += imgHtml;
    html += '<div style="flex:1;min-width:260px">';
    html += '<div style="font-weight:800;color:' + cfg.text + ';font-size:14px;margin-bottom:8px">' + cfg.emoji + ' ' + escapeHtmlNec(p.codigo_pt) + ' · ' + escapeHtmlNec(p.producto_nombre) + '</div>';
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-bottom:10px">';
    html += '<div style="background:white;border:1px solid #e2e8f0;border-radius:6px;padding:8px"><div style="font-size:10px;color:#64748b">Stock</div><div style="font-weight:700;color:#1e293b">' + p.stock_uds_total + ' uds · ' + p.stock_kg_total + 'kg</div></div>';
    html += '<div style="background:white;border:1px solid #e2e8f0;border-radius:6px;padding:8px"><div style="font-size:10px;color:#64748b">Velocidad</div><div style="font-weight:700;color:#1e293b">' + p.velocidad_uds_dia.toFixed(1) + ' uds/día (' + p.ventas_periodo_uds + ' en ventana)</div></div>';
    html += '<div style="background:white;border:1px solid #e2e8f0;border-radius:6px;padding:8px"><div style="font-size:10px;color:#64748b">Cobertura</div><div style="font-weight:700;color:' + cfg.text + '">' + (p.dias_cobertura != null ? p.dias_cobertura + ' días' : '—') + '</div></div>';
    html += '<div style="background:white;border:1px solid #e2e8f0;border-radius:6px;padding:8px"><div style="font-size:10px;color:#64748b">Lote bulk</div><div style="font-weight:700;color:#1e293b">' + p.lote_bulk_kg + ' kg</div></div>';
    html += '</div>';
    if (p.n_lotes_recomendados > 0) {
      let s = '💡 Sistema sugiere: <strong>' + p.n_lotes_recomendados + ' lote × ' + p.lote_bulk_kg + 'kg = ' + p.kg_a_producir + 'kg</strong>';
      if (p.regalos_extra_uds > 0) s += ' (+ ' + p.regalos_extra_uds + ' uds 10ml regalo)';
      html += '<div style="font-size:12px;color:#475569;margin-bottom:6px">' + s + '</div>';
    }
    if (p.pipeline_kg > 0) {
      html += '<div style="font-size:11px;color:#15803d;margin-bottom:6px">🔄 Pipeline 7d: ' + p.pipeline_kg + 'kg pendiente de Shopify Available</div>';
    }
    if ((p.lotes_pendientes_n || 0) > 0) {
      html += '<div style="font-size:11px;color:#1e40af;margin-bottom:6px">📅 Ya agendado en EOS: ' + p.lotes_pendientes_n + ' lote · ' + p.lotes_pendientes_kg + 'kg · fechas: ' + (p.lotes_pendientes_proximas_fechas || []).join(', ') + '</div>';
    }
    // Horizonte · última producción + próxima sugerida (Sebastián 13-may-2026)
    if (p.ultima_produccion_fecha) {
      let lineas = '<div style="background:#fef9c3;border-left:4px solid #ca8a04;border-radius:6px;padding:8px 10px;margin-top:8px;margin-bottom:8px">';
      lineas += '<div style="font-size:11px;color:#854d0e;font-weight:700;margin-bottom:3px">📜 Horizonte</div>';
      lineas += '<div style="font-size:11px;color:#475569">Última producción: <strong>' + p.ultima_produccion_fecha + '</strong> · ' + p.ultima_produccion_kg + 'kg';
      if (p.dias_desde_ultima != null) lineas += ' · hace ' + p.dias_desde_ultima + 'd';
      lineas += '</div>';
      if (p.duracion_lote_dias) {
        lineas += '<div style="font-size:11px;color:#475569">Lote alcanza para ~<strong>' + p.duracion_lote_dias + ' días</strong></div>';
      }
      if (p.proxima_sugerida_fecha) {
        const en = p.proxima_sugerida_dias;
        const colorSug = en <= 0 ? '#dc2626' : (en <= 7 ? '#ea580c' : '#6d28d9');
        lineas += '<div style="font-size:11px;color:' + colorSug + ';font-weight:700">Próxima sugerida: ' + p.proxima_sugerida_fecha;
        if (en != null) lineas += ' (' + (en > 0 ? 'en ' + en + 'd' : 'YA · ' + (-en) + 'd atrasado') + ')';
        lineas += '</div>';
      }
      lineas += '</div>';
      html += lineas;
    } else {
      html += '<div style="font-size:11px;color:#94a3b8;margin-top:6px;margin-bottom:6px">📜 Sin producciones registradas · usá "✓ Ya producido" para back-fill el histórico</div>';
    }
    // FIX 23-may-2026 Sebastián · "la cantidad debe ir con el horizonte" ·
    // reemplaza botones Cubrir 30/60/90 estáticos por un único botón que
    // abre el planificador moderno con selector de horizonte.
    const prodEscList = (p.producto_nombre || '').replace(/'/g, "&#39;").replace(/"/g, '&quot;');
    html += '<div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;border-top:1px solid #e2e8f0;padding-top:10px">';
    html += '<button onclick="previewSugeridasProducto(&quot;' + prodEscList + '&quot;)" style="background:#7c3aed;color:#fff;border:none;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">🤖 Programar</button>';
    html += '<button onclick="abrirGenerarProduccion(' + idx + ')" style="background:#475569;color:#fff;border:none;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">⚙ Manual</button>';
    html += '<button onclick="abrirYaProducido(' + idx + ')" style="background:#1e40af;color:#fff;border:none;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">✓ Ya producido (back-fill)</button>';
    html += '</div>';
    html += '</div></div>';
    return html;
  }

  // ── Modal unificado "Solicitar producción" ──────────────────────
  // Alias semántico · Sebastián 14-may-2026: "donde dice plan de produccion
  // deberia quedar con todas las funciones, cambiar fecha, cambiar cantidad,
  // todo lo que tiene solicitar pero bien ordenado, también allí que quede
  // el horizonte, programar automatico cada 30,60, 90 dias".
  // El modal ya tenía todo · solo cambiamos punto de entrada y nombre.
  function abrirPlanProduccion(idx) { return abrirSolicitar(idx); }

  // Placeholder "Solicitar" · reservado para futura función · Sebastián
  // 14-may-2026: "solicitar lo usare para algo mas ahora"
  function solicitarPlaceholder(prodNombre) {
    alert('⚡ Solicitar · función en definición\n\n' +
          'Sebastián reservó este botón para un nuevo flujo. ' +
          'Por ahora abrí el plan completo desde la columna "📅 Plan de producción".\n\n' +
          'Producto: ' + prodNombre);
  }

  // 🎯 Caja de acción sugerida unificada · una sola acción clara (adelantar/atrasar/
  // programar/ok) en vez de alerta roja + caja programar sueltas. Regla 20d.
  function _accionSugeridaHtml(p, idx) {
    const a = p.accion_sugerida;
    const fobj = (p.accion_fecha_objetivo || '').slice(0, 10);
    const flim = (p.fecha_limite_produccion || '').slice(0, 10);
    const fprox = (p.proximo_lote && p.proximo_lote.fecha) ? p.proximo_lote.fecha.slice(5, 10) : '?';
    if (!a || a === 'ok') {
      if (a === 'ok') {
        return '<div style="background:#dcfce7;border-left:4px solid #16a34a;border-radius:8px;padding:10px 12px;margin-bottom:12px;font-size:12px;color:#166534">✅ <strong>Cubierto</strong> · el lote del ' + fprox + ' llega a tiempo (regla: producir 20 días antes de agotarse). Sin acción.</div>';
      }
      return '';
    }
    let bg, bd, fg, titulo, detalle, btn;
    if (a === 'adelantar') {
      bg = '#fef2f2'; bd = '#dc2626'; fg = '#991b1b';
      titulo = 'Adelantar producción';
      detalle = 'El lote del <strong>' + fprox + '</strong> llega tarde: debes producir 20 días antes de agotarte (límite ' + (flim || '—') + ')' + ((p.dias_descubierto || 0) > 0 ? ' · te agotás ' + p.dias_descubierto + 'd antes de que llegue' : '') + '. Lo muevo a lo antes posible: <strong>' + (fobj || '—') + '</strong> y recalculo el resto del horizonte.';
      btn = '⏩ Adelantar y recalcular';
    } else if (a === 'atrasar') {
      bg = '#eff6ff'; bd = '#2563eb'; fg = '#1e40af';
      titulo = 'Atrasar producción';
      detalle = 'El lote del <strong>' + fprox + '</strong> está muy adelantado. Lo muevo al <strong>' + (fobj || '—') + '</strong> (20 días antes de agotarte) y recalculo el horizonte.';
      btn = '⏪ Atrasar y recalcular';
    } else { // programar
      bg = '#f5f3ff'; bd = '#7c3aed'; fg = '#5b21b6';
      titulo = 'Programar producción';
      detalle = 'No hay lote programado y lo necesitas (' + (p.urgencia || '') + '). Lo programo para <strong>' + (fobj || '—') + '</strong> (20 días antes de agotarte) y recalculo el horizonte con la venta actual.';
      btn = '🤖 Programar y recalcular';
    }
    // Sebastián 4-jul · si el producto YA tiene cadena, aclarar que esta sugerencia es solo por el stock
    // en 0 de HOY (el proximo_lote que mira es el base pasado) · NO significa que la cadena esté mal.
    var _ceA = _cadenaExistente(p);
    var _notaCadena = _ceA ? '<div style="font-size:10px;color:#166534;background:#dcfce7;border:1px solid #86efac;border-radius:5px;padding:5px 8px;margin-bottom:8px">✅ Tu cadena ya está programada (' + _ceA.n + ' lotes de ' + _ceA.kg.toFixed(1) + ' kg cada ' + _ceA.meses + ' mes' + (_ceA.meses === 1 ? '' : 'es') + '). Esto es solo por el stock en 0 de <b>HOY</b> · si querés adelantar la 1ª por el quiebre, dale; si no, no afecta la cadena.</div>' : '';
    return '<div style="background:' + bg + ';border-left:4px solid ' + bd + ';border-radius:8px;padding:12px;margin-bottom:12px">'
      + '<div style="font-weight:800;color:' + fg + ';margin-bottom:4px">🎯 Acción sugerida · ' + titulo + '</div>'
      + _notaCadena
      + '<div style="font-size:12px;color:#475569;margin-bottom:8px">' + detalle + '</div>'
      + '<button onclick="aplicarAccionSugerida(' + idx + ',this)" style="background:' + bd + ';color:#fff;border:none;padding:8px 16px;border-radius:6px;font-size:13px;font-weight:700;cursor:pointer">' + btn + '</button>'
      + '<div id="accion-sug-st-' + idx + '" style="font-size:11px;margin-top:8px"></div>'
      + '</div>';
  }

  // 🎨 Desglose por referencia/tono (multi-SKU · 27-jun) · reusa /api/plan/desglose-tonos · muestra cómo se
  // reparte la demanda entre los SKU del producto (tonos/tamaños) según el mix de ventas reciente.
  async function verDesgloseTonos(producto){
    function _e(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
    try{
      var d = await (await fetch('/api/plan/desglose-tonos?producto=' + encodeURIComponent(producto), {cache:'no-store'})).json();
      var items = d.items || [];
      var rows = items.map(function(it){
        return '<tr style="border-top:1px solid #f1f5f9"><td style="padding:5px 8px;font-family:ui-monospace;font-weight:700">'+_e(it.sku||'')+'</td><td style="padding:5px 8px">'+_e(it.tono_label||it.tono||'')+'</td><td style="padding:5px 8px;text-align:right">'+(it.ml_unidad||'—')+'</td><td style="padding:5px 8px;text-align:right;font-weight:700">'+(it.uds_ventana||0)+'</td><td style="padding:5px 8px;text-align:right;color:#6d28d9;font-weight:700">'+(it.porcentaje!=null?it.porcentaje+'%':'—')+'</td></tr>';
      }).join('');
      var ov = document.createElement('div'); ov.id='desglose-tonos-ov';
      ov.style.cssText='position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:10000;display:flex;align-items:center;justify-content:center;padding:20px';
      ov.innerHTML = '<div style="background:#fff;border-radius:14px;max-width:640px;width:100%;padding:22px;box-shadow:0 20px 60px rgba(0,0,0,.3)"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><h3 style="margin:0;color:#5b21b6">🎨 '+_e(d.producto||producto)+' · referencias / tonos</h3><button class="dt-close" style="background:#94a3b8;color:#fff;border:none;border-radius:6px;padding:5px 10px;cursor:pointer">✕</button></div>'+(items.length?('<div style="font-size:11px;color:#64748b;margin-bottom:8px">Mismo bulk · se reparte entre las referencias según el mix de ventas (últimos 60d).</div><table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#f8fafc;color:#475569"><th style="padding:5px 8px;text-align:left">SKU</th><th style="padding:5px 8px;text-align:left">Tono</th><th style="padding:5px 8px;text-align:right">ml</th><th style="padding:5px 8px;text-align:right">uds 60d</th><th style="padding:5px 8px;text-align:right">% mix</th></tr></thead><tbody>'+rows+'</tbody></table>'):'<div style="color:#94a3b8;padding:20px;text-align:center">'+_e(d.mensaje||'Sin referencias mapeadas a este producto.')+'</div>')+'</div>';
      ov.addEventListener('click', function(e){ if(e.target===ov || (e.target.classList && e.target.classList.contains('dt-close'))) ov.remove(); });
      document.body.appendChild(ov);
    }catch(e){ alert('Error: '+e.message); }
  }

  // Índices de productos que requieren acción (crítico/urgente) en orden de la lista ·
  // para navegar con "Siguiente crítico" sin salir del modal.
  function _navCriticos() {
    const arr = window._NEC_PRODUCTOS_CACHE || [];
    const out = [];
    for (let i = 0; i < arr.length; i++) {
      const u = (arr[i] || {}).urgencia;
      if (u === 'CRITICO' || u === 'URGENTE') out.push(i);
    }
    return out;
  }

  async function aplicarAccionSugerida(idx, btn) {
    const p = window._NEC_PRODUCTOS_CACHE[idx];
    if (!p) return;
    const st = document.getElementById('accion-sug-st-' + idx);
    const a = p.accion_sugerida, fobj = p.accion_fecha_objetivo;
    const _cod = p.codigo_pt, _nom = p.producto_nombre;
    if (btn) { btn.disabled = true; }
    if (st) st.innerHTML = '⏳ Aplicando…';
    const _post = (url, body) => fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body), credentials:'same-origin'});
    try {
      // 1) adelantar/atrasar el lote existente (best-effort · el replan de abajo igual ajusta)
      if ((a === 'adelantar' || a === 'atrasar') && p.accion_lote_id && fobj) {
        let r = await _post('/api/plan/proximas/' + p.accion_lote_id + '/reprogramar', {nueva_fecha: fobj, razon: a + '_auto'});
        if (!r.ok) { await _post('/api/plan/proximas/' + p.accion_lote_id + '/reprogramar', {nueva_fecha: fobj, razon: a + '_auto', skip_validacion_dia: true}); }
      }
      // 2) recalcular REEMPLAZANDO: cancela los lotes futuros pendientes del producto
      // (no iniciados/terminados, no B2B) y crea la cadena limpia · NO duplica.
      const r2 = await _post('/api/plan/auto-programar-sugeridas', {producto: _nom, dias_horizonte: 365, reemplazar: true});
      const d2 = await r2.json().catch(() => ({}));
      if (!r2.ok) { if (st) st.innerHTML = '<span style="color:#dc2626">Error: ' + (d2.error || r2.status) + '</span>'; if (btn) btn.disabled = false; return; }
      // 3) refrescar SIN cerrar el modal: recargar datos y re-renderizar el mismo producto
      if (window.cargarNecesidades) { try { await cargarNecesidades(); } catch (e) {} }
      const arr = window._NEC_PRODUCTOS_CACHE || [];
      let ni = arr.findIndex(x => (x.codigo_pt && x.codigo_pt === _cod) || x.producto_nombre === _nom);
      if (ni < 0) ni = idx;
      abrirSolicitar(ni);
      const st2 = document.getElementById('accion-sug-st-' + ni);
      if (st2) st2.innerHTML = '<span style="color:#16a34a">✓ Hecho · ' + (d2.n_reemplazados || 0) + ' lote(s) viejos reemplazados · horizonte recalculado limpio.</span>';
    } catch (e) {
      if (st) st.innerHTML = '<span style="color:#dc2626">Error red: ' + e.message + '</span>';
      if (btn) btn.disabled = false;
    }
  }

  function abrirSolicitar(idx) {
    const p = window._NEC_PRODUCTOS_CACHE[idx];
    if (!p) { alert('Producto no encontrado'); return; }
    document.getElementById('sol-titulo').textContent =
      '📅 ' + (p.codigo_pt || '') + ' · ' + p.producto_nombre;
    const cfg = URG_COLORS[p.urgencia] || URG_COLORS.OK;
    const ventaMes = Math.round(p.velocidad_uds_dia * 30);

    const imgHtml = p.imagen_url
      ? '<img loading="lazy" decoding="async" src="' + escapeHtmlNec(p.imagen_url) + '" alt="" style="width:80px;height:80px;object-fit:cover;border-radius:8px" onerror="this.style.display=&#39;none&#39;">'
      : '<div onclick="_traerFotoShopify(this)" data-prod="' + escapeHtmlNec(p.producto_nombre) + '" title="Click para traer la foto de Shopify" style="width:80px;height:80px;background:linear-gradient(135deg,#e2e8f0,#cbd5e1);border-radius:8px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:26px;cursor:pointer">📦<span style="font-size:8px;color:#475569;font-weight:700;margin-top:1px">traer foto</span></div>';

    // Presentación + 10ml info · usa ml_unidad real (Sebastián 13-may-2026:
    // "los sueros son de 30, los limpiadores de 150, geles e hidratantes de 50")
    const mlReal = p.ml_unidad || 30;
    // Sebastián 4-jul · mostrar el tamaño DOMINANTE (el que más vende), NO el promedio ponderado
    // (ml_unidad mezcla 30ml+10ml → salía 29.09 · el promedio es correcto para el CÁLCULO pero engaña
    // en el display: no existe una botella de 29.1ml, son de 30). El cálculo de kg NO se toca.
    var _mlShow = Math.round(mlReal * 10) / 10;
    try {
      var _tt = (p.tonos || []).filter(function(t){ return t.ml_unidad; });
      if (_tt.length >= 2) {
        var _dom = _tt.slice().sort(function(a,b){ return (b.ventas_ventana_uds || 0) - (a.ventas_ventana_uds || 0); })[0];
        if (_dom && _dom.ml_unidad) _mlShow = Math.round(_dom.ml_unidad * 10) / 10;
      }
    } catch(e){}
    let presentacion = '<strong>' + _mlShow + ' ml</strong> (presentación DTC)';
    if (p.tiene_10ml) {
      const tipo10 = p.tipo_10ml === 'regalo' ? 'regalo automático' : 'venta';
      presentacion += '<br><span style="background:#fdf4ff;color:#7e22ce;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">10ml · ' + p.uds_10ml_por_lote + ' uds/lote · ' + tipo10 + '</span>';
    }
    // FIX #2 · 23-may-2026 Sebastián · flags de calidad del dato
    // FIX UX 24-may PM · auditoría agente · 3-4 banners apilados era
    // spam visual. Ahora los acumulo y si son 2+ los colapso en <details>
    // (solo el más crítico expandido por default).
    const _avisos = [];
    if (p.huerfanos_sugeridos && p.huerfanos_sugeridos.length > 0) {
      const prodEscSug = (p.producto_nombre || '').replace(/'/g, "&#39;").replace(/"/g, '&quot;');
      let html_h = '<div style="background:#dbeafe;color:#1e40af;border-left:3px solid #2563eb;padding:6px 10px;border-radius:5px;font-size:11px;font-weight:600">';
      html_h += '💡 SKU(s) vendiendo sin mapeo:';
      p.huerfanos_sugeridos.forEach(h => {
        html_h += '<div style="display:flex;align-items:center;justify-content:space-between;margin-top:4px;background:#fff;padding:4px 8px;border-radius:4px"><span><strong>' + h.sku + '</strong> · ' + h.uds_60d + ' uds/60d</span><button onclick="aceptarSugerenciaMapeo(&quot;' + h.sku + '&quot;,&quot;' + prodEscSug + '&quot;,event)" style="background:#2563eb;color:#fff;border:none;padding:3px 10px;border-radius:4px;font-size:10px;font-weight:700;cursor:pointer">✓ Mapear</button></div>';
      });
      html_h += '</div>';
      _avisos.push({prio: 1, label: '💡 SKUs sin mapeo', html: html_h});
    }
    if (p.lote_size_faltante) {
      const valBd = p.lote_bulk_kg_bd != null ? p.lote_bulk_kg_bd : 0;
      const tieneCalc = p.lote_calculado;
      const html_l = '<div style="background:#fee2e2;color:#991b1b;border-left:3px solid #dc2626;padding:6px 10px;border-radius:5px;font-size:11px;font-weight:600">⚠ lote_size_kg en BD = ' + valBd + ' kg ' +
        (tieneCalc ? '(usando ' + p.lote_bulk_kg + ' kg calculado · ~60d cobertura)' : '') +
        ' · corregí el lote_size_kg en el maestro de fórmulas</div>';
      _avisos.push({prio: 2, label: '⚠ lote_size mal', html: html_l});
    }
    if (p.ml_inferido) {
      const prodEscMl = (p.producto_nombre || '').replace(/'/g, "&#39;").replace(/"/g, '&quot;');
      const html_m = '<div style="background:#fef3c7;color:#92400e;border-left:3px solid #f59e0b;padding:6px 10px;border-radius:5px;font-size:11px;font-weight:600;display:flex;justify-content:space-between;align-items:center;gap:8px"><span>⚠ ml inferido = ' + (Math.round((p.ml_unidad || 0) * 10) / 10) + 'ml · definí el real</span><button onclick="fixVolumenMl(&quot;' + prodEscMl + '&quot;,' + (p.ml_unidad || 30) + ')" style="background:#f59e0b;color:#fff;border:none;padding:3px 10px;border-radius:5px;font-size:10px;font-weight:700;cursor:pointer;white-space:nowrap">✏️ Fijar ml</button></div>';
      _avisos.push({prio: 3, label: '⚠ ml inferido', html: html_m});
    }
    let avisos = '';
    if (_avisos.length === 1) {
      avisos = '<div style="margin-top:6px">' + _avisos[0].html + '</div>';
    } else if (_avisos.length >= 2) {
      _avisos.sort((a,b) => a.prio - b.prio);
      avisos = '<details style="margin-top:6px"><summary style="cursor:pointer;font-size:11px;color:#64748b;padding:4px 8px;background:#f1f5f9;border-radius:4px;font-weight:600">⚠ ' + _avisos.length + ' avisos de calidad de datos · ' + _avisos.map(a => a.label).join(' · ') + '</summary>';
      _avisos.forEach((a, i) => {
        avisos += '<div style="margin-top:6px">' + a.html + '</div>';
      });
      avisos += '</details>';
    }

    // Navegación entre productos CRÍTICOS sin salir del modal (Sebastián 15-jun).
    let html = '';
    const _nav = _navCriticos();
    const _pos = _nav.indexOf(idx);
    if (_nav.length > 1) {
      const _prev = (_pos > 0) ? _nav[_pos - 1] : null;
      const _next = (_pos >= 0 && _pos < _nav.length - 1) ? _nav[_pos + 1] : (_pos === -1 ? _nav[0] : null);
      html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;gap:8px">';
      html += (_prev != null)
        ? '<button onclick="abrirSolicitar(' + _prev + ')" style="background:#f1f5f9;color:#475569;border:1px solid #cbd5e1;padding:6px 12px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">◀ Anterior</button>'
        : '<span></span>';
      html += '<span style="font-size:12px;color:#64748b;font-weight:700">' + (_pos >= 0 ? '🔴 Crítico ' + (_pos + 1) + ' de ' + _nav.length : 'Revisión de críticos') + '</span>';
      html += (_next != null)
        ? '<button onclick="abrirSolicitar(' + _next + ')" style="background:#6d28d9;color:#fff;border:none;padding:6px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">Siguiente crítico ▶</button>'
        : '<span></span>';
      html += '</div>';
    }
    html += '<div style="display:flex;gap:14px;margin-bottom:16px;align-items:center">';
    html += imgHtml;
    html += '<div style="flex:1">' + presentacion + avisos + '</div>';
    html += '</div>';

    // ═══════ SECCIÓN 1 · DIAGNÓSTICO (read-only) ═══════
    // Sebastián 14-may-2026: "bien ordenado" · separo en 3 secciones claras:
    // 1) Diagnóstico (qué pasa hoy) · 2) Programar (acción rápida) · 3) Mover/Pausar (acciones sobre lo agendado)

    html += '<div style="font-size:11px;color:#6d28d9;font-weight:800;text-transform:uppercase;letter-spacing:.5px;margin:14px 0 6px;padding-bottom:4px;border-bottom:2px solid #6d28d9">① Diagnóstico</div>';

    // ── Demanda actual ──
    html += '<div style="background:#f8fafc;border-radius:8px;padding:12px;margin-bottom:8px;border-left:4px solid ' + cfg.border + '">';
    html += '<div style="font-size:11px;color:#475569;font-weight:700;margin-bottom:6px">📊 Demanda y stock</div>';
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px">';
    html += '<div>Vende/día: <strong>' + p.velocidad_uds_dia.toFixed(1) + ' uds</strong></div>';
    html += '<div>Vende/mes: <strong>' + ventaMes + ' uds</strong></div>';
    html += '<div>Stock góndola: <strong>' + p.stock_uds_total + ' uds</strong></div>';
    html += ((p.por_entrar_uds || 0) > 0 ? '<div>🔵 Por entrar (Espagiria): <strong style="color:#0891b2">' + p.por_entrar_uds + ' uds</strong> <span style="font-size:10px;color:#94a3b8">producido en el lab · aún no en góndola · ya cuenta para la próxima, no para la urgencia</span></div>' : '');
    // M5/M6 · "Alcanza" = días de GÓNDOLA físicos (lo que decide la urgencia), NO la
    // cobertura-con-pipeline. Así el número y el color (CRÍTICO/etc.) coinciden.
    html += '<div>Alcanza góndola: <strong style="color:' + cfg.text + '">' + (p.dias_gondola != null ? p.dias_gondola + ' días' : '—') + '</strong> ' + cfg.emoji + ' ' + p.urgencia + '</div>';
    html += '</div>';
    // Sebastián 3-jul · QUITADA la línea "Con producción en camino: alcanza ~Xd" · era la MISMA
    // referencia (~120d) que la caja "Última producción · horizonte" de abajo (Alcanza para ~120 días).
    // Una sola referencia del alcance.
    html += '</div>';
    // 🎨 Desglose por referencia/tono (multi-SKU · 27-jun) · siempre disponible (abre el mix de ventas por SKU).
    html += '<button onclick="verDesgloseTonos(' + JSON.stringify((p.producto_nombre||p.producto||'')).replace(/"/g,'&quot;') + ')" style="background:#fff;border:1px solid #c4b5fd;color:#6d28d9;border-radius:6px;padding:5px 12px;font-size:11px;font-weight:700;cursor:pointer;margin-bottom:10px">🎨 Ver referencias / tonos</button>';
    // Sebastián 10-jul · ELIMINADA la "Acción sugerida · Adelantar producción" (Alejandro no quiere
    // sugerencias · la programación vive solo de la cadencia manual de abajo). La función _accionSugeridaHtml
    // queda en el código por si se reusa, pero NO se renderiza en la ficha.

    // ── Última producción REAL (solo referencia del origen · Sebastián 10-jul) ──
    // Sin "próxima sugerida" ni cobertura (eso era sugerencia). El punto de origen editable vive
    // en el bloque "Programar producción" de abajo (que se pre-llena con esta fecha real).
    if (p.ultima_produccion_fecha) {
      html += '<div style="background:#fef9c3;border-left:4px solid #ca8a04;border-radius:8px;padding:10px 12px;margin-bottom:12px">';
      html += '<div style="font-size:12px;color:#475569">📜 Última producción real: <strong>' + p.ultima_produccion_fecha + '</strong> · ' + p.ultima_produccion_kg + ' kg (hace ' + p.dias_desde_ultima + 'd)</div>';
      html += '</div>';
    }

    // ── Diagnostic SKUs Shopify · ¿se cuentan las ventas? ──
    if (p.sin_mapeo_shopify) {
      // FIX 23-may-2026 · Sebastián · mapeo inline desde el alert · antes
      // solo decía "agregar en otro lado" · ahora input + datalist con
      // SKUs huérfanos vendiendo · POST directo a /api/admin/sku-producto-map
      const huerfanos = window._NEC_SKUS_HUERFANOS || [];
      const inpId = 'nec-map-sku-' + idx;
      const stId  = 'nec-map-st-' + idx;
      const dlId  = 'nec-map-dl-' + idx;
      html += '<div style="background:#fee2e2;border-left:4px solid #dc2626;border-radius:8px;padding:10px;margin-bottom:12px">';
      html += '<div style="font-size:11px;color:#991b1b;font-weight:700;margin-bottom:4px">🛒✕ SIN MAPEO SHOPIFY</div>';
      html += '<div style="font-size:11px;color:#475569;margin-bottom:6px">Este producto no tiene SKUs registrados en <code>sku_producto_map</code> · sus ventas Shopify NO se imputan · por eso aparece como "sin ventas" aunque sí venda.</div>';
      // Form de mapeo inline
      html += '<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-top:6px">';
      html += '<input id="' + inpId + '" list="' + dlId + '" type="text" placeholder="SKU Shopify (ej: SAH-30)" style="flex:1;min-width:160px;padding:6px 8px;border:1px solid #fca5a5;border-radius:6px;font-size:12px;font-family:ui-monospace;text-transform:uppercase">';
      if (huerfanos.length) {
        html += '<datalist id="' + dlId + '">';
        huerfanos.forEach(s => { html += '<option value="' + escapeHtmlNec(s) + '">'; });
        html += '</datalist>';
      }
      // FIX 23-may-2026 · usar data-* + this.dataset para evitar issue de
      // quoting en Python triple-quote (mi patrón 5 / data-act recomendado)
      html += '<button class="nec-map-btn" data-prod="' + escapeHtmlNec(p.producto_nombre) + '" data-inp="' + inpId + '" data-st="' + stId + '" onclick="_mapearSkuInline(this.dataset.prod, this.dataset.inp, this.dataset.st)" style="padding:6px 12px;background:#dc2626;color:white;border:0;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">Mapear ahora</button>';
      html += '</div>';
      if (huerfanos.length) {
        html += '<div style="font-size:10px;color:#7f1d1d;margin-top:4px">💡 ' + huerfanos.length + ' SKU(s) huérfano(s) vendiendo · escribí o elegí del dropdown</div>';
      } else {
        html += '<div style="font-size:10px;color:#7f1d1d;margin-top:4px">Sin huérfanos detectados · escribí el SKU Shopify manualmente</div>';
      }
      html += '<div id="' + stId + '" style="font-size:11px;margin-top:6px"></div>';
      html += '</div>';
    } else {
      html += '<div style="background:#f0fdfa;border-left:4px solid #a78bfa;border-radius:8px;padding:6px 10px;margin-bottom:12px;font-size:11px;color:#475569">';
      html += '🛒 ' + p.n_skus_mapeados + ' SKU(s) Shopify mapeados: <code style="font-family:ui-monospace">' + (p.skus_mapeados || []).join(', ') + '</code>';
      html += '</div>';
    }

    // ── Match materias primas · ¿puede fabricarse? ──
    // Sebastián 13-may-2026: bloque CRÍTICO antes de programar
    if (p.mps_status === 'OK') {
      html += '<div style="background:#dcfce7;border-left:4px solid #16a34a;border-radius:8px;padding:10px;margin-bottom:12px;font-size:12px;color:#166534">';
      html += '🧪 <strong>Materias primas OK</strong> · ' + p.mps_total_items + ' items con stock suficiente para 1 lote · listo para producir';
      html += '</div>';
    } else if (p.mps_status === 'FALTAN_MPS') {
      html += '<div style="background:#fee2e2;border-left:4px solid #dc2626;border-radius:8px;padding:10px;margin-bottom:12px">';
      html += '<div style="font-size:11px;color:#991b1b;font-weight:700;margin-bottom:6px">🧪⚠ FALTAN MATERIAS PRIMAS · ' + p.mps_n_faltantes + ' de ' + p.mps_total_items + ' items insuficientes</div>';
      html += '<table style="width:100%;border-collapse:collapse;font-size:11px;margin-top:6px"><thead><tr style="background:rgba(255,255,255,.5)"><th style="text-align:left;padding:4px">Código</th><th style="text-align:left;padding:4px">MP</th><th style="text-align:center;padding:4px">Necesario</th><th style="text-align:center;padding:4px">Stock</th><th style="text-align:center;padding:4px">Falta</th></tr></thead><tbody>';
      p.mps_faltantes.forEach(f => {
        html += '<tr style="border-top:1px solid rgba(220,38,38,.2)"><td style="padding:3px 4px;font-family:ui-monospace;font-weight:700">' + escapeHtmlNec(f.material_id) + '</td><td style="padding:3px 4px">' + escapeHtmlNec(f.material_nombre) + '</td><td style="padding:3px 4px;text-align:center">' + f.necesario_g + 'g</td><td style="padding:3px 4px;text-align:center">' + f.disponible_g + 'g</td><td style="padding:3px 4px;text-align:center;color:#dc2626;font-weight:700">' + f.faltante_g + 'g</td></tr>';
      });
      html += '</tbody></table>';
      html += '<div style="font-size:11px;color:#7f1d1d;margin-top:6px">⚠ Comprar/recibir estas MPs antes de iniciar producción</div>';
      html += '</div>';
    } else if (p.mps_status === 'SIN_FORMULA') {
      html += '<div style="background:#f1f5f9;border-left:4px solid #94a3b8;border-radius:8px;padding:10px;margin-bottom:12px;font-size:12px;color:#64748b">';
      html += '🧪? Sin fórmula registrada · no se puede calcular MPs necesarias';
      html += '</div>';
    }
    // Sebastián 10-jul · DESPLEGABLE con TODAS las materias primas de la fórmula (confirmar mapeo/stock).
    if ((p.mps_todas || []).length > 0) {
      html += '<details style="margin-bottom:12px"><summary style="cursor:pointer;font-size:11px;color:#6d28d9;font-weight:700;padding:6px 10px;background:#f5f3ff;border-radius:6px;border-left:3px solid #7c3aed">🧪 Ver todas las materias primas (' + p.mps_todas.length + ') · confirmar mapeo</summary>';
      html += '<div style="padding:8px 0 0"><table style="width:100%;border-collapse:collapse;font-size:11px"><thead><tr style="background:#f1f5f9"><th style="text-align:left;padding:4px">Código</th><th style="text-align:left;padding:4px">MP</th><th style="text-align:center;padding:4px">Necesario</th><th style="text-align:center;padding:4px">Stock</th><th style="text-align:center;padding:4px">Estado</th></tr></thead><tbody>';
      p.mps_todas.forEach(function(m){
        var falta = (m.necesario_g - m.disponible_g) > 0.01 && !m.es_agua && m.tiene_mov;
        var est = m.es_agua ? '<span style="color:#0891b2">💧 infinita</span>'
                : (!m.tiene_mov ? '<span title="Sin movimientos en kardex · código nuevo o sin recibir" style="color:#b45309">🆕 sin mov</span>'
                : (falta ? '<span style="color:#dc2626;font-weight:700">⚠ falta</span>' : '<span style="color:#16a34a">✓ OK</span>'));
        html += '<tr style="border-top:1px solid #e2e8f0"><td style="padding:3px 4px;font-family:ui-monospace;font-weight:700">' + escapeHtmlNec(m.material_id) + '</td><td style="padding:3px 4px">' + escapeHtmlNec(m.material_nombre) + '</td><td style="padding:3px 4px;text-align:center">' + (Math.round(m.necesario_g*10)/10) + 'g</td><td style="padding:3px 4px;text-align:center">' + (Math.round(m.disponible_g*10)/10) + 'g</td><td style="padding:3px 4px;text-align:center">' + est + '</td></tr>';
      });
      html += '</tbody></table><div style="font-size:10px;color:#94a3b8;margin-top:4px">🆕 sin mov = código sin movimientos en el kardex (nuevo o sin recibir) · revisá que esté bien mapeado.</div></div></details>';
    }

    // ═══════ PROGRAMAR PRODUCCIÓN · CANÓNICO MANUAL (Sebastián 10-jul) ═══════
    // Modelo nuevo (Alejandro no quiere sugerencias): la programación vive SOLO desde el punto de
    // ORIGEN (la última producción, editable a mano) + la CADENCIA que ponemos nosotros. Sin cobertura,
    // sin "adelantar", sin próxima sugerida. Punto de partida → cada X meses → Y kg/lote → 1 o 2 años.
    {
      var _ceM = _cadenaExistente(p);   // si ya hay cadena, mostrarla (solo informativo)
      // Punto de origen: la última producción real (editable) · si no hay, hoy.
      var _hoyCo = new Date(Date.now() - 5 * 3600 * 1000).toISOString().slice(0, 10);
      var _partFecha = (p.ultima_produccion_fecha || _hoyCo).slice(0, 10);
      var _partKg = (p.ultima_produccion_kg != null && p.ultima_produccion_kg > 0) ? p.ultima_produccion_kg : (p.lote_bulk_kg || 30);
      var _mesesM = _ceM ? _ceM.meses : 2;
      var _velDiaM = p.velocidad_kg_dia || 0;
      var _kgM = _ceM ? _ceM.kg.toFixed(1) : (_velDiaM > 0 ? (Math.round(_velDiaM * 30.44 * _mesesM * 10) / 10) : _partKg);
      html += '<div style="background:linear-gradient(135deg,#f5f3ff,#faf5ff);border:1px solid #ddd6fe;border-radius:10px;padding:14px;margin:14px 0">';
      html += '<div style="font-size:13px;font-weight:800;color:#5b21b6;margin-bottom:8px">📅 Programar producción · canónico manual</div>';
      if (_ceM) {
        html += '<div style="background:#dcfce7;border:1px solid #86efac;border-radius:6px;padding:7px 10px;margin-bottom:10px;font-size:11px;color:#166534;line-height:1.5">✅ <b>Ya tenés cadena:</b> ' + _ceM.n + ' lotes de <b>' + _ceM.kg.toFixed(1) + ' kg</b> cada <b>' + _ceM.meses + ' mes' + (_ceM.meses === 1 ? '' : 'es') + '</b>. Reprogramá abajo para cambiarla.</div>';
      }
      // Fecha canónica / de origen (editable a mano · para normalizar el punto de partida)
      html += '<div style="font-size:11px;color:#6d28d9;font-weight:800;margin-bottom:4px">📍 Fecha canónica / fecha de origen <span style="font-weight:600;color:#94a3b8">(punto de partida · editá para normalizar)</span></div>';
      html += '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px">';
      html += '<label style="font-size:11px;color:#475569">Fecha <input id="cm-part-fecha" type="date" value="' + _partFecha + '" style="padding:4px 6px;border:1px solid #c4b5fd;border-radius:5px;font-size:12px"></label>';
      html += '<label style="font-size:11px;color:#475569">Kg producidos <input id="cm-part-kg" type="number" min="0.1" step="0.1" value="' + _partKg + '" style="width:66px;padding:4px 6px;border:1px solid #c4b5fd;border-radius:5px;font-size:12px;text-align:center"></label>';
      html += '</div>';
      // Cadencia + kg por lote + horizonte
      html += '<div style="font-size:11px;color:#6d28d9;font-weight:800;margin-bottom:4px">🔁 Cadencia</div>';
      html += '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px">';
      html += '<span style="font-size:12px;color:#5b21b6;font-weight:700">Cada <input id="cm-meses" type="number" min="1" max="12" value="' + _mesesM + '" oninput="_cmPreview(' + idx + ')" style="width:44px;padding:3px 4px;border:1px solid #c4b5fd;border-radius:4px;text-align:center;font-weight:700"> meses</span>';
      html += '<span style="font-size:12px;color:#5b21b6;font-weight:700">· <input id="cm-kg" type="number" min="0.1" step="0.1" value="' + _kgM + '" oninput="_cmPreview(' + idx + ')" title="kg de cada lote de la cadena (editable)" style="width:62px;padding:3px 4px;border:1px solid #7c3aed;border-radius:4px;text-align:center;font-weight:800;color:#5b21b6"> kg/lote</span>';
      html += '<span style="font-size:12px;color:#5b21b6;font-weight:700">· Horizonte <select id="cm-anios" onchange="_cmPreview(' + idx + ')" style="padding:3px 4px;border:1px solid #c4b5fd;border-radius:4px;font-weight:700"><option value="1">1 año</option><option value="2">2 años</option><option value="3">3 años</option></select></span>';
      html += '</div>';
      html += '<div id="cm-preview-' + idx + '" style="font-size:11px;color:#5b21b6;background:#fff;border:1px solid #ede9fe;border-radius:6px;padding:8px 10px;line-height:1.5;margin-bottom:8px"></div>';
      html += '<button onclick="programarCadenaManual(' + idx + ')" style="background:linear-gradient(90deg,#7c3aed,#5b21b6);color:#fff;border:none;border-radius:6px;padding:9px 16px;font-size:13px;font-weight:800;cursor:pointer;box-shadow:0 2px 8px -2px rgba(124,58,237,.5)">📅 Crear cadena en el calendario</button>';
      html += '<div style="font-size:10px;color:#94a3b8;margin-top:6px">Crea un lote cada X meses desde la partida, por el horizonte elegido, en día hábil (sin festivos). Reemplaza las futuras de este producto · conserva pedidos B2B y lo ya producido.</div>';
      html += '</div>';
    }

    // Sebastián 10-jul · ELIMINADO el planificador (🤖 Abrir planificador · sugerencias) — Alejandro no
    // lo quiere. El lote puntual se rediseñó: agregar un lote ahora recalcula TODO el horizonte desde él
    // (ver la sección "Lotes ya agendados" · cada lote tiene "recalcular horizonte desde acá").
    const prodNombreEsc = (p.producto_nombre || '').replace(/'/g, "&#39;").replace(/"/g, '&quot;');

    // ═══════ SECCIÓN 3 · LOTES AGENDADOS · ACCIONES ═══════
    if ((p.planificacion || []).length > 0) {
      html += '<div style="font-size:11px;color:#6d28d9;font-weight:800;text-transform:uppercase;letter-spacing:.5px;margin:18px 0 6px;padding-bottom:4px;border-bottom:2px solid #6d28d9">③ Lotes ya agendados · ' + p.planificacion.length + '</div>';
      html += '<div style="background:#f8fafc;border-radius:8px;padding:10px">';
      html += renderLotesInline(p.planificacion, p.producto_nombre);
      html += '</div>';
    }

    // ═══════ SECCIÓN 4 · OTRAS ACCIONES ═══════
    html += '<div style="display:flex;gap:8px;flex-wrap:wrap;padding-top:12px;margin-top:12px;border-top:1px solid #e2e8f0">';
    html += '<button onclick="cerrarSolicitar();setTimeout(function(){abrirYaProducido(' + idx + ')},100)" style="background:#1e40af;color:#fff;border:none;padding:9px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">✓ Back-fill · ya se produjo</button>';
    html += '</div>';

    document.getElementById('sol-body').innerHTML = html;
    document.getElementById('solicitarModal').style.display = 'flex';
    setTimeout(function(){ try{ _cmPreview(idx); }catch(e){} }, 40);  // preview de la cadena canónica manual (Sebastián 10-jul)
  }

  // Sebastián 3-jul · cadencia desde Necesidades (motor completo · "aquí debería ser todo").
  // Calcula la porción Animus, el intervalo por cobertura (kg÷venta) y cuándo cae la 1ª (stock−buffer).
  // OJO M65: DASHBOARD_HTML es un string REGULAR → alert/confirm usan salto escapado con doble backslash.
  // Ancla = la producción REAL más RECIENTE que ya pasó (<= hoy) del producto · sea EJECUTADA (lo
  // que ya se hizo · última producción) o AGENDADA. Así toma la del 30-jun, no un atrasado más viejo
  // (Sebastián 3-jul). Desde ese punto se monta la cadena.
  function _anclaProd(p){
    var hoy = new Date().toISOString().slice(0,10);
    // Sebastián 4-jul (workflow ultracode · BUG cadena de 1 lote) · un lote PENDIENTE pasado (el 1er slot
    // de una cadena previa que NUNCA se produjo) NO es un ancla · solo anclan producciones REALES
    // (ejecutadas: inicio/fin/inventario_descontado) o lotes FUTUROS. Antes marcaba todos ejec:false y el
    // pending pasado con id ganaba → rutéo a desde-lote/<id> con ancla falsa → cadena colapsada a 1 lote.
    var cands = (p.planificacion || []).filter(function(l){
      if((l.estado || '') === 'cancelado' || !l.fecha) return false;
      var f = ('' + l.fecha).slice(0, 10);
      if(f < hoy && !l.ejecutado) return false;   // pending pasado (no ejecutado) → NO puede ser ancla
      return true;
    }).map(function(l){ return {id: l.id, fecha: ('' + l.fecha).slice(0, 10), kg: (l.kg || 0), ejec: !!l.ejecutado}; });
    if(p.ultima_produccion_fecha){ cands.push({id: null, fecha: ('' + p.ultima_produccion_fecha).slice(0, 10), kg: (p.ultima_produccion_kg || 0), ejec: true}); }
    if(!cands.length) return null;
    var pasadas = cands.filter(function(c){ return c.fecha <= hoy; });
    if(pasadas.length){
      // más reciente <= hoy · desempate DETERMINÍSTICO: ante misma fecha, preferir la ejecutada (real).
      pasadas.sort(function(a,b){ if(a.fecha !== b.fecha) return a.fecha > b.fecha ? -1 : 1; return (b.ejec ? 1 : 0) - (a.ejec ? 1 : 0); });
      return pasadas[0];
    }
    cands.sort(function(a,b){ return a.fecha < b.fecha ? -1 : 1; });  // ninguna pasó → la más temprana futura
    return cands[0];
  }
  // Sebastián 3-jul · al cambiar los meses, recalcula el kg del lote (campo editable) · así ves los
  // kilos y podés ajustarlos para programar la cantidad exacta ("full").
  // Sebastián 4-jul · ¿este producto YA tiene una cadena programada? (≥2 lotes eos_plan futuros). Devuelve
  // sus parámetros (meses = separación entre lotes, kg Animus, otro) para PRE-LLENAR el recuadro y que
  // refleje lo que ya está, en vez del default 2 meses. Así no confunde al re-abrir.
  function _cadenaExistente(p){
    var hoy = new Date().toISOString().slice(0,10);
    var cad = (p.planificacion || []).filter(function(l){
      return l.origen === 'eos_plan' && ('' + (l.fecha || '')).slice(0,10) > hoy
        && (l.estado || '') !== 'cancelado' && (l.estado || '') !== 'completado';
    }).sort(function(a,b){ return ('' + a.fecha).localeCompare('' + b.fecha); });
    if(cad.length < 2) return null;
    var d1 = new Date(('' + cad[0].fecha).slice(0,10) + 'T12:00:00');
    var d2 = new Date(('' + cad[1].fecha).slice(0,10) + 'T12:00:00');
    var meses = Math.max(1, Math.round(Math.round((d2 - d1) / 86400000) / 30.44));
    var kgTot = cad[0].kg || 0, otro = cad[0].kg_otro_cliente || 0;
    return {n: cad.length, meses: meses, kg: Math.max(0, Math.round((kgTot - otro) * 10) / 10), otro: Math.round(otro * 10) / 10};
  }
  // Sebastián 4-jul · el usuario escribió los kg a mano → FIJARLOS (marcar el candado) para que al
  // cambiar los meses NO se recalculen. Así hace de más y produce cada X meses igual. Aplica a todos.
  function _cadpKgManual(idx){
    var f = document.getElementById('cadp-kg-fijo'); if(f) f.checked = true;
    _updateCadenaProdPreview(idx);
  }
  function _cadpMesesToKg(idx){
    var p = window._NEC_PRODUCTOS_CACHE[idx]; if(!p) return;
    var vel = p.velocidad_kg_dia || 0;
    var meses = parseFloat((document.getElementById('cadp-meses')||{}).value) || 2;
    var kgEl = document.getElementById('cadp-kg');
    var fijo = document.getElementById('cadp-kg-fijo');
    // si el kg está FIJADO (candado) NO recalcular al cambiar meses · la cadencia sale de los meses igual.
    if(kgEl && vel > 0.0001 && !(fijo && fijo.checked)){ kgEl.value = (Math.round(vel * meses * 30.44 * 10) / 10).toFixed(1); }
    _updateCadenaProdPreview(idx);
  }
  function _cadenaProdCalc(idx){
    var p = window._NEC_PRODUCTOS_CACHE[idx]; if(!p) return null;
    var vel = p.velocidad_kg_dia || 0;   // kg/día Animus
    if(!(vel > 0.0001)) return null;
    var meses = parseFloat((document.getElementById('cadp-meses')||{}).value) || 2;   // CADENCIA · cada X meses
    var otro = parseFloat((document.getElementById('cadp-otro')||{}).value) || 0;
    if(otro < 0) otro = 0;
    // el KG del lote es EDITABLE (cadp-kg) · si el user lo puso, manda; si no, = demanda de X meses.
    var _kgEl = document.getElementById('cadp-kg');
    var _kgOverride = _kgEl ? (parseFloat(_kgEl.value) || 0) : 0;
    var kgAnimus = _kgOverride > 0 ? _kgOverride : Math.round(vel * meses * 30.44 * 10) / 10;
    if(!(kgAnimus > 0)) return null;
    // Sebastián 3-jul PUNTO 1: la CADENCIA sale de los MESES, NO del kg · subir el kg = hacés de más,
    // NO amplía el tiempo entre producciones (respeta "cada 3 meses").
    var intervalDias = Math.max(Math.round(meses * 30.44), 15);
    var mesesCubre = Math.round((kgAnimus / (vel * 30.44)) * 10) / 10;  // cuánto cubre el kg (surplus si > meses)
    var nLotes = Math.max(1, Math.round(730 / intervalDias));
    var cadaTxt = '~' + meses + ' meses';
    var diasGond = (p.dias_gondola != null) ? p.dias_gondola : 0;
    var ancla = _anclaProd(p);
    var firstOffset;
    // Sebastián 3-jul PUNTO 2: la 1ª de la cadena arranca en la "Próxima sugerida" del recuadro
    // amarillo (proxima_sugerida_fecha) · lo que YA calcula el sistema, no "100 días después".
    var _prox = p.proxima_sugerida_fecha;
    if(ancla && _prox){
      try{
        var _d1 = new Date(('' + ancla.fecha).slice(0,10) + 'T12:00:00');
        var _d2 = new Date(('' + _prox).slice(0,10) + 'T12:00:00');
        firstOffset = Math.max(Math.round((_d2 - _d1) / 86400000), 1);
      }catch(e){ firstOffset = null; }
    }
    if(firstOffset == null){
      if(ancla){
        var anclaAnimusKg = Math.max(0, (ancla.kg || 0) - otro);
        firstOffset = Math.max(Math.round(anclaAnimusKg / vel) - 20, 1);
      } else {
        firstOffset = Math.max(diasGond - 20, 0);
      }
    }
    return {meses:meses, mesesCubre:mesesCubre, otro:otro, kgAnimus:kgAnimus, intervalDias:intervalDias, firstOffset:firstOffset, nLotes:nLotes, cadaTxt:cadaTxt, vel:vel, diasGond:diasGond, ancla:ancla, prox:_prox};
  }
  function _updateCadenaProdPreview(idx){
    var el = document.getElementById('cadp-preview'); if(!el) return;
    var cc = _cadenaProdCalc(idx);
    if(!cc){ el.innerHTML = '<span style="color:#94a3b8">Sin velocidad de venta · no se puede calcular la cadencia.</span>'; return; }
    // Sebastián 3-jul · NO repetir "Producción base · kg" (la caja "Última producción" de arriba ya
    // la muestra) · solo referenciar la fecha base concisa aquí.
    var _surplus = cc.mesesCubre > (cc.meses + 0.3);
    var _fijo = !!(document.getElementById('cadp-kg-fijo') || {}).checked;
    el.innerHTML = '📦 Cada lote de la cadena <b>' + cc.kgAnimus.toFixed(1) + ' kg</b>'
      + (_fijo ? ' <span style="background:#ede9fe;color:#6d28d9;padding:0 5px;border-radius:4px;font-weight:800">🔒 fijo</span>' : '')
      + ' (cubre ~' + cc.mesesCubre + ' meses de venta'
      + (_surplus ? ' · hacés de más' : '') + ') · vende <b>' + (cc.vel*30).toFixed(1) + ' kg/mes</b>'
      + (cc.otro > 0 ? (' · ' + cc.otro.toFixed(1) + ' kg otro cliente en la base') : '') + '<br>'
      + '⏳ Un lote cada <b>' + cc.cadaTxt + '</b> (' + (_fijo ? 'kg fijos · igual producís cada ' + cc.meses + ' meses' : 'respeta el ritmo · no cambia si subís los kg') + ') · ~<b>' + cc.nLotes + '</b> lotes · total <b>' + (cc.kgAnimus * cc.nLotes).toFixed(0) + ' kg</b> en 2 años<br>'
      + '🗓️ La 1ª de la cadena el <b>' + (cc.prox || (cc.ancla ? '~' + cc.firstOffset + 'd desde la base' : 'según stock')) + '</b>' + (cc.prox ? ' (la próxima sugerida)' : '') + '.';
  }
  // ── Programación canónica MANUAL (Sebastián 10-jul) · desde el punto de origen + la cadencia ──
  function _cmCalc(idx){
    var p = window._NEC_PRODUCTOS_CACHE[idx]; if(!p) return null;
    var partida = ((document.getElementById('cm-part-fecha')||{}).value || '').slice(0,10);
    var kg = parseFloat((document.getElementById('cm-kg')||{}).value) || 0;
    var meses = parseFloat((document.getElementById('cm-meses')||{}).value) || 0;
    var anios = parseInt((document.getElementById('cm-anios')||{}).value) || 1;
    if(anios < 1 || anios > 3) anios = 1;
    if(!partida || !(kg > 0) || !(meses > 0)) return null;
    var intervalDias = Math.max(Math.round(meses * 30.44), 15);
    var horizonte = anios * 365;
    // 1ª de la cadena = partida + una cadencia (el backend la clampa a hoy si la partida es vieja)
    var nLotes = Math.max(1, Math.floor((horizonte - intervalDias) / intervalDias) + 1);
    return {partida:partida, kg:kg, meses:meses, anios:anios, intervalDias:intervalDias, nLotes:nLotes, horizonte:horizonte};
  }
  function _cmPreview(idx){
    var el = document.getElementById('cm-preview-' + idx); if(!el) return;
    var cc = _cmCalc(idx);
    if(!cc){ el.innerHTML = '<span style="color:#94a3b8">Completá la partida, cada cuántos meses y los kg/lote.</span>'; return; }
    var _first = '';
    try{ var _d = new Date(cc.partida + 'T12:00:00'); _d.setDate(_d.getDate() + cc.intervalDias); _first = _d.toISOString().slice(0,10); }catch(e){}
    el.innerHTML = '📦 Un lote de <b>' + cc.kg.toFixed(1) + ' kg</b> cada <b>' + cc.meses + ' mes' + (cc.meses===1?'':'es') + '</b> (~' + cc.intervalDias + ' días)<br>'
      + '🗓️ Desde <b>' + cc.partida + '</b> · 1ª aprox <b>' + (_first||'—') + '</b> (si cae en el pasado, arranca hoy) · ~<b>' + cc.nLotes + '</b> lotes en <b>' + cc.anios + ' año' + (cc.anios===1?'':'s') + '</b> · total <b>' + (cc.kg*cc.nLotes).toFixed(0) + ' kg</b>';
  }
  async function programarCadenaManual(idx){
    var p = window._NEC_PRODUCTOS_CACHE[idx]; if(!p){ alert('Producto no encontrado'); return; }
    var cc = _cmCalc(idx);
    if(!cc){ alert('Completá la producción de partida (fecha), cada cuántos meses y los kg por lote.'); return; }
    var msg = 'Crear la cadena de "' + (p.producto_nombre || '') + '":\n\n'
      + '• Punto de origen: ' + cc.partida + '\n'
      + '• Un lote de ' + cc.kg.toFixed(1) + ' kg cada ' + cc.meses + ' mes(es)\n'
      + '• ~' + cc.nLotes + ' lotes en ' + cc.anios + ' año(s) · total ' + (cc.kg*cc.nLotes).toFixed(0) + ' kg\n\n'
      + 'Reemplaza las producciones futuras de este producto (conserva pedidos B2B y lo ya producido).';
    if(!confirm(msg)) return;
    if(window._cadenaBusy){ return; }
    window._cadenaBusy = true;
    try{
      var t = (await (await fetch('/api/csrf-token', {credentials:'same-origin'})).json()).csrf_token;
      var bodyObj = {producto: p.producto_nombre, ancla_fecha: cc.partida, kg_por_lote: cc.kg,
                     interval_dias: cc.intervalDias, dias_hasta_primera: cc.intervalDias, anios: cc.anios};
      var r = await fetch('/api/plan/programar-cadencia-producto', {method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRF-Token':t}, body: JSON.stringify(bodyObj)});
      var d = await r.json();
      if(r.status === 409 && d && (('' + (d.error || '')).indexOf('ya se está programando') >= 0)){
        await new Promise(function(res){ setTimeout(res, 1500); });
        r = await fetch('/api/plan/programar-cadencia-producto', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-CSRF-Token':t}, body: JSON.stringify(bodyObj)});
        d = await r.json();
      }
      if(!r.ok){ window._cadenaBusy = false; alert('No se pudo: ' + ((d && d.error) || r.status)); return; }
      window._cadenaBusy = false;
      var _cr = d.creados || 0, _esp = d.esperados || _cr;
      _toastCadena('✓ ' + (p.producto_nombre || '') + ' · ' + _cr + '/' + _esp + ' lotes');
      if(d.aviso){ alert('⚠ ' + (p.producto_nombre || '') + '\n\n' + d.aviso); }
      try{ if(window._NEC_PRODUCTOS_CACHE[idx]) window._NEC_PRODUCTOS_CACHE[idx]._cadena_programada = true; }catch(e){}
      if(window.cargarNecesidades){ try{ await cargarNecesidades(); }catch(e){} }
    }catch(e){ window._cadenaBusy = false; alert('Error: ' + e); }
  }
  // Sebastián 10-jul · usar un lote AGENDADO como origen y recalcular TODO el horizonte con la
  // cadencia del bloque de arriba (cada X meses · kg · años). "Unido a este lote modifica el horizonte."
  async function recalcularHorizonteDesdeLote(loteId, producto){
    var meses = parseFloat((document.getElementById('cm-meses')||{}).value) || 0;
    var kg = parseFloat((document.getElementById('cm-kg')||{}).value) || 0;
    var anios = parseInt((document.getElementById('cm-anios')||{}).value) || 1;
    if(anios < 1 || anios > 3) anios = 1;
    if(!(meses > 0) || !(kg > 0)){ alert('Definí arriba la cadencia (cada cuántos meses) y los kg/lote antes de recalcular.'); return; }
    var interval = Math.max(Math.round(meses * 30.44), 15);
    if(!confirm('Usar este lote como ORIGEN y recalcular todo el horizonte:\n\n• Un lote de ' + kg.toFixed(1) + ' kg cada ' + meses + ' mes(es) por ' + anios + ' año(s).\n\nReemplaza las futuras de este producto (conserva pedidos B2B y lo ya producido). ¿Continuar?')) return;
    if(window._cadenaBusy){ return; }
    window._cadenaBusy = true;
    try{
      var t = (await (await fetch('/api/csrf-token', {credentials:'same-origin'})).json()).csrf_token;
      var r = await fetch('/api/plan/programar-cadencia-desde-lote/' + loteId, {method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRF-Token':t},
        body: JSON.stringify({interval_dias: interval, first_offset_dias: interval, kg_por_lote: kg, anios: anios})});
      var d = await r.json();
      window._cadenaBusy = false;
      if(!r.ok){ alert('No se pudo: ' + ((d && d.error) || r.status)); return; }
      _toastCadena('✓ ' + (producto || '') + ' · horizonte recalculado · ' + (d.creados || 0) + ' lotes');
      if(d.aviso){ alert('⚠ ' + (producto || '') + '\n\n' + d.aviso); }
      if(window.cargarNecesidades){ try{ await cargarNecesidades(); }catch(e){} }
    }catch(e){ window._cadenaBusy = false; alert('Error: ' + e); }
  }
  async function programarCadenaProducto(idx){
    var p = window._NEC_PRODUCTOS_CACHE[idx]; if(!p){ alert('Producto no encontrado'); return; }
    var cc = _cadenaProdCalc(idx);
    if(!cc){ alert('Este producto no tiene velocidad de venta · no se puede calcular la cadencia.'); return; }
    var msg = 'Programar la cadena de "' + (p.producto_nombre || '') + '":\n\n';
    if(cc.ancla){ msg += '• Base: producción del ' + cc.ancla.fecha + ' (' + (cc.ancla.kg||0).toFixed(1) + ' kg) · se conserva y se cuenta desde ahí\n'; }
    msg += '• Cada lote ' + cc.kgAnimus.toFixed(1) + ' kg (cubre ~' + cc.mesesCubre + ' meses de venta)\n• Cada ' + cc.cadaTxt + ' · ~' + cc.nLotes + ' producciones · total ' + (cc.kgAnimus * cc.nLotes).toFixed(0) + ' kg en 2 años\n• La 1ª de la cadena el ' + (cc.prox || (cc.firstOffset + ' días después de la base')) + '\n\nBORRA todas las producciones futuras de ese producto (Fijo, auto, proyección) y deja solo esta cadena. Conserva pedidos B2B y lo ya producido.';
    if(!confirm(msg)) return;
    // Sebastián 3-jul · guard anti doble-click (idempotencia) · un 2º POST cancelaría y recrearía la
    // cadena recién hecha (o en concurrencia duplicaría). No programar dos veces el mismo producto.
    if(window._cadenaBusy){ return; }
    window._cadenaBusy = true;
    try{
      var t = (await (await fetch('/api/csrf-token', {credentials:'same-origin'})).json()).csrf_token;
      var url, bodyObj;
      if(cc.ancla && cc.ancla.id){
        url = '/api/plan/programar-cadencia-desde-lote/' + cc.ancla.id;   // base = lote programado (tiene id)
        bodyObj = {interval_dias: cc.intervalDias, first_offset_dias: cc.firstOffset, kg_por_lote: cc.kgAnimus, kg_otro_cliente: cc.otro, anios: 2};
      } else {
        url = '/api/plan/programar-cadencia-producto';                    // base = producción ejecutada (sin id) o desde stock
        bodyObj = {producto: p.producto_nombre, kg_por_lote: cc.kgAnimus, interval_dias: cc.intervalDias, dias_hasta_primera: cc.firstOffset, kg_otro_cliente: cc.otro, anios: 2};
        if(cc.ancla && cc.ancla.fecha){ bodyObj.ancla_fecha = cc.ancla.fecha; }  // ancla a la producción real que ya se hizo
      }
      var r = await fetch(url, {method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRF-Token':t}, body: JSON.stringify(bodyObj)});
      var d = await r.json();
      // Sebastián 4-jul (workflow ultracode) · si el lock está ocupado (409 · request previo del mismo
      // producto), reintentar 1 vez tras 1.5s antes de rendirse (evita el "No se pudo" al programar rápido).
      if(r.status === 409 && d && (('' + (d.error || '')).indexOf('ya se está programando') >= 0)){
        await new Promise(function(res){ setTimeout(res, 1500); });
        r = await fetch(url, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-CSRF-Token':t}, body: JSON.stringify(bodyObj)});
        d = await r.json();
      }
      if(!r.ok){ window._cadenaBusy = false; alert('No se pudo: ' + ((d && d.error) || r.status)); return; }
      window._cadenaBusy = false;
      // Sebastián 4-jul · FEEDBACK CLARO: mostrar creados vs esperados · si la cadena quedó INCOMPLETA,
      // alertar (no avanzar en silencio) para que el usuario SEPA que ese producto necesita atención.
      var _cr = d.creados || 0, _esp = d.esperados || _cr;
      if(d.aviso || (_esp >= 3 && _cr < 3)){
        alert('⚠ ' + (p.producto_nombre || '') + '\n\nSe crearon ' + _cr + ' de ~' + _esp + ' lotes.' + (d.aviso ? ('\n' + d.aviso) : '') + '\n\nEste producto tiene producciones agendadas que chocan con la cadena. Revisalo con "Verificar plan".');
      }
      // NO cerrar ni recargar todo · avanzar al SIGUIENTE producto (fila). Toast + abrirSolicitar(next).
      try{ if(window._NEC_PRODUCTOS_CACHE[idx]) window._NEC_PRODUCTOS_CACHE[idx]._cadena_programada = true; }catch(e){}
      _toastCadena('✓ ' + (p.producto_nombre || '') + ' · ' + _cr + '/' + _esp + ' lotes');
      var _nav = (typeof _navCriticos === 'function') ? _navCriticos() : [];
      var _pos = _nav.indexOf(idx);
      var _next = null;
      for(var _k = 0; _k < _nav.length; _k++){ if(_nav[_k] === idx){ if(_k + 1 < _nav.length) _next = _nav[_k + 1]; break; } }
      if(_next != null){
        abrirSolicitar(_next);   // avanza al siguiente · mantiene el modal, sin recargar Necesidades
      } else {
        _toastCadena('✓ Era el último · recargá Necesidades para ver el calendario');
        if(window.cargarNecesidades){ try{ await cargarNecesidades(); }catch(e){} }
      }
    }catch(e){ window._cadenaBusy = false; alert('Error: ' + e); }
  }
  // Toast no-bloqueante para la cadena (Sebastián 3-jul) · no interrumpe el flujo producto-a-producto.
  function _toastCadena(msg){
    try{
      var t = document.getElementById('cadena-toast');
      if(!t){ t = document.createElement('div'); t.id = 'cadena-toast'; t.style.cssText = 'position:fixed;top:16px;left:50%;transform:translateX(-50%);z-index:2147483647;background:#16a34a;color:#fff;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:700;box-shadow:0 8px 24px rgba(0,0,0,.25)'; document.body.appendChild(t); }
      t.textContent = msg; t.style.display = 'block';
      clearTimeout(window._cadenaToastT);
      window._cadenaToastT = setTimeout(function(){ if(t) t.style.display = 'none'; }, 2200);
    }catch(e){}
  }

  // Programar único desde el modal Plan de producción · Sebastián 14-may-2026
  async function programarUnicoDesdePlan() {
    const idx = parseInt(document.getElementById('ppd-idx').value);
    const p = window._NEC_PRODUCTOS_CACHE[idx];
    if (!p) { alert('Producto no encontrado'); return; }
    const fecha = (document.getElementById('ppd-fecha').value || '').trim();
    const kg = parseFloat(document.getElementById('ppd-kg').value);
    if (!fecha || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(fecha)) { alert('Fecha inválida (YYYY-MM-DD)'); return; }
    if (!kg || kg <= 0) { alert('Cantidad kg inválida'); return; }
    if (!confirm('¿Programar ' + p.producto_nombre + ' · ' + kg + 'kg para ' + fecha + '?')) return;
    try {
      const r = await fetch('/api/plan/programar-produccion', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrfTokenNec()},
        body: JSON.stringify({
          producto_nombre: p.producto_nombre,
          cantidad_kg: kg,
          fecha_programada: fecha,
          notas: 'Lote único desde modal Plan',
        }),
      });
      const d = await r.json();
      if (!r.ok) { alert('Error: ' + (d.error || r.status)); return; }
      cerrarSolicitar();
      cargarNecesidades();
    } catch(e) { alert('Error: ' + e.message); }
  }
  function cerrarSolicitar() { document.getElementById('solicitarModal').style.display = 'none'; }

  // Programar canónico · genera N lotes recurrentes con horizonte
  async function programarCanonico(idx) {
    const p = window._NEC_PRODUCTOS_CACHE[idx];
    if (!p) { alert('Producto no encontrado'); return; }
    const freq = parseInt(document.getElementById('can-freq').value);
    const kg = parseFloat(document.getElementById('can-kg').value);
    const horizonte = parseInt(document.getElementById('can-horizonte').value);
    if (!freq || !kg || kg <= 0 || !horizonte) { alert('Completá frecuencia, kg y horizonte'); return; }
    const nLotes = Math.floor(horizonte / freq);
    if (!confirm('¿Generar ' + nLotes + ' lotes de ' + p.producto_nombre + ' · ' + kg + 'kg c/u · cada ' + freq + ' días durante ' + horizonte + ' días? · Respeta lun-vie · prefiere lun/mié/vie · max 2/día.')) return;
    try {
      const r = await fetch('/api/plan/programar-canonico', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrfTokenNec()},
        body: JSON.stringify({
          producto_nombre: p.producto_nombre,
          cantidad_kg: kg,
          frecuencia_dias: freq,
          horizonte_dias: horizonte,
        }),
      });
      const d = await r.json();
      if (!r.ok) { alert('Error: ' + (d.error || r.status)); return; }
      cerrarSolicitar();
      alert('✓ ' + d.total + ' lotes generados · cada ' + d.frecuencia_dias + 'd · horizonte ' + d.horizonte_dias + 'd · Ve a Plan en curso para verlos.');
      cargarNecesidades();
    } catch(e) { alert('Error: ' + e.message); }
  }

  // Agenda directo · 1 click desde el escenario sugerido
  async function agendarRapido(idx, kg, fecha, etiqueta) {
    const p = window._NEC_PRODUCTOS_CACHE[idx];
    if (!p) { alert('Producto no encontrado'); return; }
    if (!confirm('¿Agendar producción de ' + p.producto_nombre + ' · ' + kg + 'kg para ' + fecha + '? · ' + etiqueta)) return;
    try {
      const r = await fetch('/api/plan/programar-produccion', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrfTokenNec()},
        body: JSON.stringify({
          producto_nombre: p.producto_nombre,
          cantidad_kg: kg,
          fecha_programada: fecha,
          notas: etiqueta,
        }),
      });
      const d = await r.json();
      if (!r.ok) { alert('Error: ' + (d.error || r.status)); return; }
      cerrarSolicitar();
      cargarNecesidades();
    } catch(e) { alert('Error: ' + e.message); }
  }

  function toggleDrill(idx) {
    const tr = document.getElementById('drill-' + idx);
    if (!tr) return;
    tr.style.display = (tr.style.display === 'none' || !tr.style.display) ? 'table-row' : 'none';
  }

  function abrirGenerarProduccion(idx) {
    const p = window._NEC_PRODUCTOS_CACHE[idx];
    if (!p) { alert('Producto no encontrado en cache (idx=' + idx + ')'); return; }
    document.getElementById('gp-codigo').value = p.codigo_pt || '';
    document.getElementById('gp-producto').value = p.producto_nombre;
    document.getElementById('gp-titulo').textContent = '⚡ Generar producción · ' + p.codigo_pt;
    document.getElementById('gp-kg').value = p.kg_a_producir > 0 ? p.kg_a_producir : p.lote_bulk_kg;
    const f = new Date(); f.setDate(f.getDate() + 7);
    document.getElementById('gp-fecha').value = f.toISOString().slice(0, 10);
    document.getElementById('gp-notas').value = '';
    document.getElementById('gpModal').style.display = 'flex';
  }
  function cerrarGenerarProduccion() { document.getElementById('gpModal').style.display = 'none'; }

  async function confirmarGenerarProduccion() {
    const producto = document.getElementById('gp-producto').value;
    const kg = parseFloat(document.getElementById('gp-kg').value);
    const fecha = document.getElementById('gp-fecha').value;
    const notas = document.getElementById('gp-notas').value.trim();
    if (!producto || !kg || kg <= 0 || !fecha) { alert('Completá producto, kg y fecha'); return; }
    try {
      const r = await fetch('/api/plan/programar-produccion', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrfTokenNec()},
        body: JSON.stringify({producto_nombre: producto, cantidad_kg: kg, fecha_programada: fecha, notas: notas}),
      });
      const d = await r.json();
      if (!r.ok) { alert('Error: ' + (d.error || r.status)); return; }
      cerrarGenerarProduccion();
      alert('✓ Producción agendada · #' + d.id + ' · ' + d.producto + ' · ' + d.cantidad_kg + 'kg · ' + d.fecha);
      cargarNecesidades();
    } catch(e) { alert('Error: ' + e.message); }
  }

  // Modal "Ya producido" · registra lote retroactivo (sin tocar inventario)
  function abrirYaProducido(idx) {
    const p = window._NEC_PRODUCTOS_CACHE[idx];
    if (!p) { alert('Producto no encontrado en cache'); return; }
    document.getElementById('yp-producto').value = p.producto_nombre;
    document.getElementById('yp-titulo').textContent = '✓ Ya producido · ' + (p.codigo_pt || p.producto_nombre.substring(0, 20));
    document.getElementById('yp-kg').value = p.lote_bulk_kg || '';
    document.getElementById('yp-fecha').value = new Date().toISOString().slice(0, 10);
    document.getElementById('yp-lote').value = '';
    document.getElementById('yp-notas').value = '';
    document.getElementById('ypModal').style.display = 'flex';
  }
  function cerrarYaProducido() { document.getElementById('ypModal').style.display = 'none'; }

  async function confirmarYaProducido() {
    const producto = document.getElementById('yp-producto').value;
    const kg = parseFloat(document.getElementById('yp-kg').value);
    const fecha = document.getElementById('yp-fecha').value;
    const lote = document.getElementById('yp-lote').value.trim();
    const notas = document.getElementById('yp-notas').value.trim();
    if (!producto || !kg || kg <= 0 || !fecha) { alert('Completá producto, kg y fecha'); return; }
    try {
      const r = await fetch('/api/plan/registrar-produccion-completada', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrfTokenNec()},
        body: JSON.stringify({
          producto_nombre: producto, cantidad_kg_real: kg,
          fecha_producida: fecha, lote: lote, notas: notas,
        }),
      });
      const d = await r.json();
      if (!r.ok) { alert('Error: ' + (d.error || r.status)); return; }
      cerrarYaProducido();

      // Follow-up · sugerir próxima producción · Sebastián 13-may-2026:
      // "ya fue producido, y diga alcanzará para tantos días, producir
      // en tal fecha, ¿aceptar?"
      try {
        const rn = await fetch('/api/plan/necesidades?cobertura_dias_minimo=20&cobertura_dias_alerta=25&cobertura_dias_vigilar=45');
        const dn = await rn.json();
        const animus = (dn.clientes || []).find(c => c.cliente_id === 'ANIMUS_DTC');
        const prodUpdate = animus && animus.productos.find(pp => pp.producto_nombre === producto);
        if (prodUpdate && prodUpdate.duracion_lote_dias && prodUpdate.proxima_sugerida_fecha) {
          const msg = '✓ Lote registrado: ' + d.lote + ' · ' + d.kg_real + 'kg · '
                    + 'Este lote alcanza para ~' + prodUpdate.duracion_lote_dias + ' días · '
                    + 'Próxima sugerida: ' + prodUpdate.proxima_sugerida_fecha
                    + (prodUpdate.proxima_sugerida_dias != null ? ' (en ' + prodUpdate.proxima_sugerida_dias + 'd)' : '')
                    + ' · ¿Agendar siguiente lote para esa fecha?';
          if (confirm(msg)) {
            // Agendar próximo automáticamente
            await fetch('/api/plan/programar-produccion', {
              method: 'POST',
              headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrfTokenNec()},
              body: JSON.stringify({
                producto_nombre: producto,
                cantidad_kg: kg,  // misma kg que el ya producido
                fecha_programada: prodUpdate.proxima_sugerida_fecha,
                notas: 'Auto-sugerido tras back-fill ' + d.lote,
              }),
            });
          }
        } else {
          alert('✓ Lote registrado · #' + d.id + ' · ' + d.lote + ' · ' + d.kg_real + 'kg');
        }
      } catch(e) {
        alert('✓ Lote registrado · #' + d.id + ' · ' + d.lote + ' · ' + d.kg_real + 'kg');
      }
      cargarNecesidades();
    } catch(e) { alert('Error: ' + e.message); }
  }

  // Sebastián 2-jul · select de ENVASE (frasco) por pedido B2B · guarda vía PATCH.
  function _pedEnvaseSelect(id, cur){
    cur = (cur || '').toUpperCase();
    var list = window._NEC_ENVASES || [];
    var h = '<select class="ped-fld" data-id="'+id+'" data-field="envase_codigo" onchange="savePedidoField(this)" title="Envase de este pedido · al confirmar/programar cae al calendario con este envase" style="border:1px solid #cbd5e1;border-radius:4px;font-size:10px;padding:2px 4px;max-width:160px;cursor:pointer">';
    h += '<option value="">&#8212; envase &#8212;</option>';
    var found = false;
    for(var i=0;i<list.length;i++){
      var e = list[i]; var sel = (e.codigo === cur) ? ' selected' : '';
      if(e.codigo === cur) found = true;
      h += '<option value="'+(e.codigo||'').replace(/"/g,'&quot;')+'"'+sel+'>'+((e.codigo||'')+(e.descripcion?(' · '+e.descripcion):'')).slice(0,42)+'</option>';
    }
    if(cur && !found){ h += '<option value="'+cur.replace(/"/g,'&quot;')+'" selected>'+cur+'</option>'; }
    h += '</select>';
    return h;
  }
  async function savePedidoField(el){
    if(!el) return;
    var id = el.getAttribute('data-id'), field = el.getAttribute('data-field'), val = el.value;
    if(!id || !field) return;
    var body = {}; body[field] = val;
    try{
      var t = (await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json()).csrf_token;
      var r = await fetch('/api/pedidos-b2b/' + id, {method:'PATCH',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify(body)});
      if(!r.ok){ var d = await r.json().catch(function(){return {};}); alert('No se pudo guardar: ' + (d.error || r.status)); return; }
      el.style.borderColor = '#16a34a';
      setTimeout(function(){ el.style.borderColor = '#cbd5e1'; }, 1200);
    }catch(e){ alert('Error: ' + e); }
  }
  function renderB2BSection(cli) {
    const cliEsc = (cli.cliente_id || '').replace(/'/g, '&#39;').replace(/"/g, '&quot;');
    const cliNomEsc = (cli.cliente_nombre || '').replace(/'/g, '&#39;').replace(/"/g, '&quot;');
    // Sebastián 25-may-2026 PM · "que todos los clientes se vean como
    // animus" · mismo wrapper <details> cerrado por default + summary
    // glassy con chips de conteo por estado del pedido (pendiente,
    // confirmado, cancelado). Botón + Producto stopPropagation para no
    // togglear el details al click.
    const conteos = {pendiente:0, confirmado:0, en_produccion:0, despachado:0, cancelado:0};
    (cli.pedidos || []).forEach(p => {
      const e = (p.estado || 'pendiente').toLowerCase();
      if (conteos[e] !== undefined) conteos[e]++;
    });
    const CHIP_CFG = {
      pendiente:    {bg:'#e0e7ff', text:'#3730a3', emoji:'⏳'},
      confirmado:   {bg:'#dcfce7', text:'#15803d', emoji:'✓'},
      en_produccion:{bg:'#fef3c7', text:'#854d0e', emoji:'⚙'},
      despachado:   {bg:'#d1fae5', text:'#065f46', emoji:'📦'},
      cancelado:    {bg:'#fee2e2', text:'#991b1b', emoji:'✕'},
    };
    let chips = '';
    Object.keys(CHIP_CFG).forEach(k => {
      if (conteos[k] > 0) {
        const cfg = CHIP_CFG[k];
        chips += '<span style="background:'+cfg.bg+';color:'+cfg.text+';padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;margin-left:4px">' + cfg.emoji + ' ' + conteos[k] + '</span>';
      }
    });

    // Sebastián 25-may-2026 PM · chip max_urgencia en el header del cliente
    // así planta ve de un vistazo qué cliente apura.
    const URG_HEADER = {
      alta:  {bg:'#fee2e2', text:'#991b1b', emoji:'🔴', lbl:'Alta'},
      media: {bg:'#fef3c7', text:'#854d0e', emoji:'🟡', lbl:'Media'},
      baja:  {bg:'#d1fae5', text:'#065f46', emoji:'🟢', lbl:'Baja'},
    };
    const maxUrg = cli.max_urgencia || 'media';
    const urgCfg = URG_HEADER[maxUrg] || URG_HEADER.media;
    let chipUrgHeader = '<span title="urgencia máxima entre sus pedidos" style="background:'+urgCfg.bg+';color:'+urgCfg.text+';padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;margin-left:4px">' + urgCfg.emoji + ' ' + urgCfg.lbl + '</span>';

    let html = '<details style="background:white;border-radius:14px;margin-bottom:14px;border:1px solid #e2e8f0;overflow:hidden">';
    html += '<summary style="cursor:pointer;padding:14px 18px;background:linear-gradient(90deg,#eef2ff,#e0e7ff);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">';
    html += '<div><span style="color:#3730a3;font-size:16px;font-weight:800">📦 ' + escapeHtmlNec(cli.cliente_nombre) + '</span>';
    // Sebastián 2-jul · tipo REAL del cliente (Espagiria = Maquila 360, no B2B genérico)
    var _tipoLbl = ({maquila:'Maquila 360', b2b:'B2B', influencer:'Influencer'})[cli.tipo_cliente || 'b2b'] || (cli.tipo_cliente ? cli.tipo_cliente.toUpperCase() : 'B2B');
    html += ' <span style="font-size:11px;font-weight:500;color:#94a3b8">· ' + _tipoLbl + ' · ' + (cli.pedidos||[]).length + ' pedidos · ' + cli.kg_total.toFixed(1) + ' kg</span></div>';
    html += '<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">' + chipUrgHeader + chips;
    html += '<button onclick="event.preventDefault();event.stopPropagation();revisarB2BCliente(\''+cliEsc+'\',\''+cliNomEsc+'\')" style="background:#0f766e;color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer;margin-left:8px" title="Revisar cobertura y duplicados de este cliente (read-only)">🔍 Revisar</button>';
    html += '<button onclick="event.preventDefault();event.stopPropagation();abrirFormB2BCliente(\''+cliEsc+'\',\''+cliNomEsc+'\')" style="background:#7c3aed;color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer;margin-left:8px">+ Producto</button>';
    html += '</div></summary>';
    html += '<div style="padding:14px 18px;overflow-x:auto">';
    html += '<table style="width:100%;border-collapse:collapse;font-size:12px">';
    html += '<thead><tr style="background:#f1f5f9"><th style="padding:6px 10px">Urg.</th><th style="text-align:left;padding:6px 10px">Producto</th><th style="padding:6px 10px">Uds</th><th style="padding:6px 10px">kg</th><th style="padding:6px 10px">Fecha</th><th style="padding:6px 10px">Estado</th><th style="padding:6px 10px">Lote</th><th style="padding:6px 10px">Envase</th><th style="padding:6px 10px"></th></tr></thead><tbody>';
    // Sebastián 2-jul · cliente sin pedidos (Luz aún no le cargó) · guía para empezar
    if (!(cli.pedidos && cli.pedidos.length)) {
      html += '<tr><td colspan="9" style="padding:14px;text-align:center;color:#94a3b8">Sin pedidos aún &middot; toc&aacute; <b>+ Producto</b> para cargarle un pedido y que entre a producci&oacute;n</td></tr>';
    }
    (cli.pedidos || []).forEach(p => {
      const lote = p.lote_consolidado || null;
      let loteHtml = '<span style="color:#94a3b8;font-size:10px">sin asignar</span>';
      if (lote) {
        const modoLbl = lote.modo === 'sumado_a_lote_canonico' ? '✓ Animus' : '🔵 Dedicado';
        loteHtml = '<span style="font-size:10px;color:#1e40af" title="Lote #'+lote.lote_id+' · '+(lote.fecha_lote||'')+'">'+modoLbl+'<br><span style="color:#64748b">'+(lote.fecha_lote||'')+'</span></span>';
      }
      // Botón Asignar a Animus · solo si NO está ya sumado a canónico
      let btnAsignar = '';
      if (!lote || lote.modo !== 'sumado_a_lote_canonico') {
        btnAsignar = '<button onclick="asignarB2BaAnimus('+p.id+')" class="b2bx b2bx-assign" title="Busca el lote de Animus DTC del mismo producto (±30 días) y suma este pedido B2B a ese lote · así se produce todo junto en vez de un lote aparte">🔗 Asignar a Animus</button>';
      }
      // CONFIRMACIÓN 26-jun · el pedido del portal queda 'pendiente' (no entra solo al plan) · el equipo lo CONFIRMA acá
      let btnConfirmar = '';
      if ((p.estado || '') === 'pendiente') {
        btnConfirmar = '<button onclick="confirmarB2B('+p.id+')" class="b2bx b2bx-confirm" title="Revisar y confirmar el pedido · recién al confirmarlo entra al plan de producción (antes queda pendiente, sin producirse)">✅ Confirmar</button>';
      }
      // Sebastián 2-jul · "despachar no va acá (eso se hace en Producto Terminado)" → quitado.
      const estadoBg = p.estado === 'confirmado' ? '#dcfce7' : (p.estado === 'cancelado' ? '#fee2e2' : '#e0e7ff');
      const estadoColor = p.estado === 'confirmado' ? '#15803d' : (p.estado === 'cancelado' ? '#991b1b' : '#3730a3');
      const urgP = (p.urgencia || 'media').toLowerCase();
      const rowHi = urgP === 'alta' ? 'background:#fef2f2;' : '';
      // URGENCIA editable (Sebastián 2-jul) · alta = el cliente necesita adelantar producción.
      var urgOpts = ['alta','media','baja'].map(function(u){ return '<option value="'+u+'"'+(u===urgP?' selected':'')+'>'+({alta:'🔴 Alta',media:'🟡 Media',baja:'🟢 Baja'}[u])+'</option>'; }).join('');
      var urgSel = '<select class="ped-fld" data-id="'+p.id+'" data-field="urgencia" onchange="savePedidoField(this)" style="border:1px solid #cbd5e1;border-radius:4px;font-size:10px;padding:2px 4px;font-weight:700;cursor:pointer">'+urgOpts+'</select>';
      var urgAlert = (urgP === 'alta') ? '<div style="font-size:9px;color:#b91c1c;font-weight:800;margin-top:2px" title="El cliente lo necesita urgente · considerá adelantar la producción">⚡ adelantar</div>' : '';
      // ENVASE seleccionable + guardar (Sebastián 2-jul) · cae al calendario con el envase unido.
      var envSel = _pedEnvaseSelect(p.id, p.envase || '');
      html += '<tr style="border-bottom:1px solid #e2e8f0;' + rowHi + '">'
        + '<td style="padding:6px 10px;text-align:center">' + urgSel + urgAlert + '</td>'
        + '<td style="padding:6px 10px"><strong>' + escapeHtmlNec(p.producto_nombre) + '</strong></td>'
        + '<td style="padding:6px 10px;text-align:center">' + p.cantidad_uds + ' × ' + p.ml_unidad + 'ml</td>'
        + '<td style="padding:6px 10px;text-align:center;font-weight:700">' + p.kg_equivalente + '</td>'
        + '<td style="padding:6px 10px;text-align:center">' + (p.fecha_estimada || '—') + '</td>'
        + '<td style="padding:6px 10px;text-align:center"><span style="background:'+estadoBg+';color:'+estadoColor+';padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700">' + p.estado + '</span></td>'
        + '<td style="padding:6px 10px;text-align:center">' + loteHtml + '</td>'
        + '<td style="padding:6px 10px;text-align:center">' + envSel + '</td>'
        + '<td style="padding:6px 10px;text-align:right">' + btnConfirmar + btnAsignar + '<button onclick="cancelarB2B(' + p.id + ')" class="b2bx b2bx-ghost" title="Cancelar este pedido B2B · no se produce (se puede volver a cargar con + Producto)">Cancelar</button></td>'
        + '</tr>';
    });
    html += '</tbody></table></div></details>';
    return html;
  }

  // Sebastián 30-may-2026 · Revisar B2B (read-only) · cobertura + duplicados.
  // Caso Kelly: ver qué pedidos están en calendario, cuáles duplicadas, estados.
  window.revisarB2BCliente = async function(cliId, cliNom){
    window._B2B_DIAG_CLI = {id: cliId, nom: cliNom};
    window._B2B_DIAG_PEDIDOS = {};
    var m = document.getElementById('modal-b2b-diag');
    if(m) m.remove();
    m = document.createElement('div');
    m.id = 'modal-b2b-diag';
    m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9999;display:flex;align-items:flex-start;justify-content:center;padding:20px;overflow:auto';
    m.innerHTML = '<div style="background:#fff;border-radius:12px;max-width:1050px;width:100%;box-shadow:0 12px 40px rgba(0,0,0,.3);padding:24px"><div style="text-align:center;padding:40px;color:#94a3b8">Revisando pedidos de ' + escapeHtmlNec(cliNom||cliId) + '…</div></div>';
    document.body.appendChild(m);
    m.addEventListener('click', function(e){ if(e.target === m) m.remove(); });
    try {
      var r = await fetch('/api/pedidos-b2b/diagnostico-cliente?cliente=' + encodeURIComponent(cliId || cliNom), {cache:'no-store'});
      if(r.status === 401){ window.location.href = '/login'; return; }
      var d = await r.json();
      if(!r.ok || !d.ok){
        m.querySelector('div').innerHTML = '<div style="color:#dc2626;padding:30px">Error: ' + escapeHtmlNec((d && d.error) || r.status) + '</div>';
        return;
      }
      var esc = escapeHtmlNec, html = '';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #e2e8f0;padding-bottom:12px;margin-bottom:14px">';
      html += '<div><h2 style="margin:0;font-size:18px;color:#0f766e">🔍 Revisar B2B · ' + esc(d.cliente_nombre || cliNom || '') + '</h2>';
      html += '<div style="font-size:11px;color:#64748b;margin-top:3px">' + d.n_pedidos + ' pedidos · ' + d.n_vinculados + ' en calendario · ' + d.n_sin_lote + ' sin lote · ' + (d.n_duplicados ? ('<b style="color:#b91c1c">' + d.n_duplicados + ' duplicados</b>') : '0 duplicados') + ' · read-only</div></div>';
      html += '<button onclick="document.getElementById(&quot;modal-b2b-diag&quot;).remove()" style="background:#e2e8f0;color:#475569;border:none;width:36px;height:36px;border-radius:50%;font-size:20px;cursor:pointer">×</button>';
      html += '</div>';
      html += '<div style="overflow-x:auto;border:1px solid #e2e8f0;border-radius:8px"><table style="width:100%;border-collapse:collapse;font-size:12px">';
      html += '<thead><tr class="necx-thead" style="background:#f8fafc;color:#475569">';
      ['Producto','Uds','kg','Fecha','Estado','En calendario','Cobertura','Acción'].forEach(function(h,i){
        var al = (i===1||i===2) ? 'right' : 'left';
        html += '<th style="text-align:' + al + ';padding:7px 8px;font-weight:700;white-space:nowrap">' + h + '</th>';
      });
      html += '</tr></thead><tbody>';
      (d.pedidos || []).forEach(function(p){
        window._B2B_DIAG_PEDIDOS[p.id] = {producto: p.producto, kg: p.kg};
        var bg = p.duplicado ? '#fff1f2' : (p.sin_lote ? '#fff7ed' : '#fff');
        var cobBadge, cobCol;
        if(p.duplicado){ cobBadge = '⚠ DUPLICADO'; cobCol = '#b91c1c'; }
        else if(p.vinculado){ cobBadge = '✓ vinculado'; cobCol = '#15803d'; }
        else if(p.hay_lote_calendario > 0){ cobBadge = 'lote sin vincular'; cobCol = '#b45309'; }
        else { cobBadge = '✗ sin lote'; cobCol = '#b91c1c'; }
        var lotesTxt = (p.lotes_vinculados || []).map(function(l){ return '#' + l.lote_id + ' (' + l.fecha + ', ' + l.kg_aporte + 'kg)'; }).join(', ') || '—';
        html += '<tr style="border-top:1px solid #f1f5f9;background:' + bg + '">';
        html += '<td style="padding:6px 8px">' + esc(p.producto||'') + '</td>';
        html += '<td style="padding:6px 8px;text-align:right">' + p.uds + '</td>';
        html += '<td style="padding:6px 8px;text-align:right">' + p.kg + '</td>';
        html += '<td style="padding:6px 8px;white-space:nowrap">' + (p.fecha_estimada||'—') + '</td>';
        html += '<td style="padding:6px 8px">' + esc(p.estado||'') + '</td>';
        html += '<td style="padding:6px 8px;font-size:11px;color:#64748b">' + esc(lotesTxt) + (p.apariciones_texto>1 ? ' <span style="color:#b91c1c;font-weight:700">·texto x' + p.apariciones_texto + '</span>' : '') + '</td>';
        html += '<td style="padding:6px 8px"><span style="color:' + cobCol + ';font-weight:700">' + cobBadge + '</span><div style="font-size:10px;color:#94a3b8">' + esc(p.recomendacion||'') + '</div></td>';
        if((p.estado||'').toLowerCase() === 'cancelado'){
          html += '<td style="padding:6px 8px;text-align:center;color:#94a3b8;font-size:11px">—</td>';
        } else {
          html += '<td style="padding:6px 8px;text-align:center"><button onclick="cancelarPedidoB2B(' + p.id + ')" style="background:#dc2626;color:#fff;border:none;padding:4px 10px;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer" title="Cancelar este pedido · le resta el kg al lote del calendario">🗑 Cancelar</button></td>';
        }
        html += '</tr>';
      });
      if(!(d.pedidos||[]).length){ html += '<tr><td colspan="8" style="padding:20px;text-align:center;color:#94a3b8">Sin pedidos para este cliente</td></tr>'; }
      html += '</tbody></table></div>';
      html += '<div style="font-size:11px;color:#94a3b8;margin-top:8px">' + esc(d.nota||'') + '</div>';
      m.querySelector('div').innerHTML = html;
    } catch(e){
      m.querySelector('div').innerHTML = '<div style="color:#dc2626;padding:30px">Error de red: ' + escapeHtmlNec(e.message) + '</div>';
    }
  };

  // Sebastián 30-may-2026 · cancelar un pedido B2B desde el modal Revisar.
  // Caso Kelly: borrar el pedido de prueba duplicado. El backend resta el kg
  // al lote (reversion) · idempotente. Refresca modal + necesidades.
  window.cancelarPedidoB2B = async function(pid){
    var info = (window._B2B_DIAG_PEDIDOS || {})[pid] || {};
    var desc = info.producto ? (info.producto + ' · ' + info.kg + 'kg') : ('pedido #' + pid);
    if(!confirm('¿Cancelar ' + desc + ' (pedido #' + pid + ')?\n\nSe le restará el kg al lote en el calendario. Útil para borrar duplicados/pruebas.')) return;
    try {
      var r = await fetch('/api/pedidos-b2b/' + pid, {method:'DELETE', headers:{'X-CSRF-Token':(typeof csrfTokenNec==='function'?csrfTokenNec():'')}});
      if(r.status === 401){ window.location.href = '/login'; return; }
      var d = await r.json();
      if(!r.ok || !d.ok){
        alert('No se pudo cancelar: ' + String((d && d.error) || ('HTTP ' + r.status)).substring(0, 300));
        return;
      }
      var cli = window._B2B_DIAG_CLI || {};
      if(cli.id || cli.nom){ revisarB2BCliente(cli.id, cli.nom); }  // refresca el modal
      if(typeof cargarNecesidades === 'function'){ try { cargarNecesidades(); } catch(e){} }
    } catch(e){ alert('Error de red: ' + e.message); }
  };

  // Pre-llena cliente_id y abre el form B2B
  window.abrirFormB2BCliente = function(cli_id, cli_nom) {
    document.getElementById('b2b-cliente-id').value = cli_id;
    document.getElementById('b2b-cliente-nombre').value = cli_nom;
    abrirFormB2B();
  };

  // CONFIRMACIÓN 26-jun (Sebastián) · Catalina confirma un pedido PENDIENTE del portal → recién acá entra al plan.
  window.confirmarB2B = async function(pid) {
    if (!confirm('Confirmar este pedido? Va a entrar al plan de producción.\n\n(Si querés ajustar cantidad/fecha, editá el pedido antes.)')) return;
    try {
      const r = await fetch('/api/pedidos-b2b/' + pid + '/confirmar', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrfTokenNec()},
        body: '{}',
      });
      const d = await r.json();
      if (!r.ok) { alert(d.error || 'No se pudo confirmar'); return; }
      alert('\u2713 Pedido confirmado \u00b7 entr\u00f3 al plan (' + (d.kg_b2b || 0) + ' kg).');
      cargarNecesidades();
    } catch (e) { alert('Error confirmando el pedido'); }
  };

  // DESPACHO 26-jun (mejora 2/4) · marca el pedido despachado con guía/transportadora · el cliente lo ve.
  window.despacharB2B = async function(pid) {
    var transp = prompt('Transportadora (opcional):', '');
    if (transp === null) return;
    var guia = prompt('N\u00b0 de gu\u00eda / tracking (opcional):', '') || '';
    try {
      const r = await fetch('/api/pedidos-b2b/' + pid + '/despachar', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrfTokenNec()},
        body: JSON.stringify({transportadora: transp, guia: guia}),
      });
      const d = await r.json();
      if (!r.ok) { alert(d.error || 'No se pudo despachar'); return; }
      alert('\u2713 Pedido marcado DESPACHADO \u00b7 el cliente lo ve en su portal.');
      cargarNecesidades();
    } catch (e) { alert('Error al despachar'); }
  };

  // Asigna un pedido B2B a un lote Animus DTC existente
  window.asignarB2BaAnimus = async function(pid) {
    if (!confirm('¿Buscar un lote Animus DTC del mismo producto ±30d y sumar este pedido?\n\nSi hay match, se cancela el lote dedicado y se evita producción duplicada.')) return;
    try {
      const r = await fetch('/api/pedidos-b2b/' + pid + '/asignar-a-animus', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrfTokenNec()},
      });
      const d = await r.json();
      if (r.ok) {
        alert('✓ ' + d.mensaje + '\n\nTotal del lote ahora: ' + d.kg_total_lote.toFixed(1) + ' kg');
        cargarNecesidades();
        return;
      }
      // No matcheó · si hay candidatos fuera de ventana, ofrecer forzar
      if (d.candidatos_fuera_ventana && d.candidatos_fuera_ventana.length > 0) {
        let lista = 'No hay lote en ventana ±30d, pero existen estos del mismo producto:\n\n';
        d.candidatos_fuera_ventana.forEach((c, i) => {
          lista += (i+1) + '. Lote #' + c.id + ' · ' + c.producto + ' · ' +
                   c.fecha + ' · ' + c.kg + 'kg · ' + c.estado + '\n';
        });
        lista += '\n¿Querés FORZAR asignación a uno? Escribí el número (1-' +
                 d.candidatos_fuera_ventana.length + ') o cancelá:';
        const sel = prompt(lista);
        const idx = parseInt(sel, 10) - 1;
        if (idx >= 0 && idx < d.candidatos_fuera_ventana.length) {
          const loteSel = d.candidatos_fuera_ventana[idx];
          const r2 = await fetch('/api/pedidos-b2b/' + pid + '/asignar-a-lote/' + loteSel.id, {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrfTokenNec()},
          });
          const d2 = await r2.json();
          if (r2.ok) {
            alert('✓ ' + d2.mensaje + '\n\nTotal lote: ' + d2.kg_total_lote.toFixed(1) + ' kg');
            cargarNecesidades();
          } else {
            alert('Error forzando: ' + (d2.error || r2.status));
          }
        }
        return;
      }
      // Sin candidatos · ofrecer diagnóstico
      if (confirm('No hay lote del mismo producto. Ver diagnóstico (qué lotes existen y por qué se descartaron)?')) {
        const rd = await fetch('/api/pedidos-b2b/' + pid + '/diagnostico-match');
        const dd = await rd.json();
        let txt = 'DIAGNÓSTICO MATCH B2B↔ANIMUS\n';
        txt += '────────────────────────\n';
        txt += 'Pedido #' + dd.pedido_id + ' · ' + (dd.cliente || '') + '\n';
        txt += 'Producto: ' + dd.producto_pedido + '\n';
        txt += 'Canónico: ' + dd.producto_canonico + '\n';
        txt += 'Fecha target: ' + dd.fecha_target + ' (±' + dd.ventana_dias + 'd)\n';
        txt += 'Lotes existentes: ' + dd.total_lotes_existentes_mismo_producto + '\n';
        txt += '────────────────────────\n';
        if (dd.candidatos && dd.candidatos.length) {
          dd.candidatos.forEach(c => {
            txt += '#' + c.id + ' · ' + (c.fecha||'') + ' · ' + c.kg + 'kg · ' +
                   c.estado + ' · origen=' + c.origen + '\n';
            if (!c.match_directo && c.razones_descarte.length) {
              txt += '    ⚠ ' + c.razones_descarte.join(' · ') + '\n';
            }
          });
        } else {
          txt += 'Sin lotes existentes · necesitás programar uno nuevo.';
        }
        alert(txt);
      }
    } catch(e) { alert('Error red: ' + e.message); }
  };

  // Sebastián 2-jul · Clientes B2B como POPUP (iframe) sin salir de Necesidades.
  // Cierre por addEventListener (evita comillas escapadas en onclick · lección M65).
  function abrirClientesB2B() {
    var ov = document.getElementById('cliB2bOverlay');
    if (ov) { ov.style.display = 'flex'; var f = ov.querySelector('iframe'); if (f) f.src = f.src; return; }
    ov = document.createElement('div');
    ov.id = 'cliB2bOverlay';
    ov.style.cssText = 'position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:2147483647;display:flex;align-items:center;justify-content:center;padding:20px';
    ov.innerHTML =
      '<div style="background:#fff;border-radius:12px;width:min(1150px,97vw);height:min(90vh,940px);display:flex;flex-direction:column;overflow:hidden;box-shadow:0 12px 44px rgba(0,0,0,.35)">'
      + '<div style="display:flex;justify-content:space-between;align-items:center;padding:9px 16px;background:#0d9488;color:#fff;flex:0 0 auto">'
      + '<span style="font-weight:800;font-size:14px">&#128101; Clientes B2B</span>'
      + '<button id="cliB2bClose" style="background:rgba(255,255,255,.25);color:#fff;border:none;border-radius:6px;padding:5px 13px;cursor:pointer;font-weight:700">&#10005; Cerrar</button>'
      + '</div>'
      + '<iframe src="/admin/clientes-b2b" style="flex:1 1 auto;border:none;width:100%"></iframe>'
      + '</div>';
    ov.addEventListener('click', function (e) { if (e.target === ov) ov.remove(); });
    document.body.appendChild(ov);
    var _cb = document.getElementById('cliB2bClose');
    if (_cb) _cb.addEventListener('click', function () { ov.remove(); });
  }

  async function abrirFormB2B() {
    // Cargar productos activos al select si está vacío
    const sel = document.getElementById('b2b-producto');
    if (sel.options.length <= 1) {
      try {
        const r = await fetch('/api/formulas');
        const d = await r.json();
        const items = d.items || d.formulas || d;
        if (Array.isArray(items)) {
          items.forEach(p => {
            const nombre = p.producto_nombre || p.producto || p.nombre;
            const activo = p.activo === undefined ? true : p.activo;
            if (nombre && activo) {
              const opt = document.createElement('option');
              opt.value = nombre;
              opt.textContent = nombre;
              sel.appendChild(opt);
            }
          });
        }
      } catch(e) { console.warn('No se pudo cargar productos:', e); }
    }
    document.getElementById('b2bModal').style.display = 'flex';
  }
  function cerrarFormB2B() { document.getElementById('b2bModal').style.display = 'none'; }

  async function crearB2B() {
    const cliente_id = document.getElementById('b2b-cliente-id').value.trim();
    const cliente_nombre = document.getElementById('b2b-cliente-nombre').value.trim();
    const producto = document.getElementById('b2b-producto').value;
    const cantidad = parseInt(document.getElementById('b2b-cantidad').value);
    const ml = parseFloat(document.getElementById('b2b-ml').value || '30');
    const fecha = document.getElementById('b2b-fecha').value;
    const notas = document.getElementById('b2b-notas').value.trim();
    if (!cliente_id || !cliente_nombre || !producto || !cantidad || cantidad <= 0) {
      alert('Completá cliente, producto y cantidad'); return;
    }
    try {
      const r = await fetch('/api/pedidos-b2b', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrfTokenNec()},
        body: JSON.stringify({
          cliente_id, cliente_nombre,
          producto_nombre: producto,
          cantidad_uds: cantidad,
          ml_unidad: ml,
          fecha_estimada: fecha,
          notas,
        }),
      });
      const d = await r.json();
      if (!r.ok) { alert('Error: ' + (d.error || r.status)); return; }
      cerrarFormB2B();
      // Limpiar campos
      ['b2b-cliente-id','b2b-cliente-nombre','b2b-cantidad','b2b-fecha','b2b-notas'].forEach(id => document.getElementById(id).value='');
      document.getElementById('b2b-producto').value = '';
      // Sebastián 19-may-2026: mostrar warning de MP faltante (non-blocking).
      // El pedido YA quedó creado · el aviso es para que decidan generar SOL
      // o ajustar cantidad antes de producir.
      let msg = '✓ Pedido creado · ' + (d.kg_b2b || 0) + 'kg';
      if (d.mp_check && d.mp_check.mps_faltantes && d.mp_check.mps_faltantes.length > 0) {
        msg += '\n\n⚠️ ATENCIÓN · faltan ' + d.mp_check.mps_faltantes.length + ' MP(s):';
        d.mp_check.mps_faltantes.slice(0, 6).forEach(m => {
          msg += '\n  · ' + (m.material_nombre || m.material_id) +
                 ' · falta ' + (m.faltante_g || 0).toLocaleString() + ' g';
        });
        if (d.mp_check.mps_faltantes.length > 6) {
          msg += '\n  · …y ' + (d.mp_check.mps_faltantes.length - 6) + ' más';
        }
        msg += '\n\nGenerá solicitudes de compra desde "Abastecimiento" o ajustá cantidad.';
      } else if (d.mp_check && d.mp_check.sin_formula) {
        msg += '\n\n⚠️ El producto no tiene fórmula cargada · no se pudo chequear MP.';
      }
      alert(msg);
      cargarNecesidades();
    } catch(e) { alert('Error: ' + e.message); }
  }

  async function cancelarB2B(id) {
    if (!confirm('¿Cancelar este pedido?')) return;
    try {
      const r = await fetch('/api/pedidos-b2b/' + id, {method: 'DELETE', headers: {'X-CSRF-Token': csrfTokenNec()}});
      if (!r.ok) { const d = await r.json(); alert('Error: ' + (d.error || r.status)); return; }
      cargarNecesidades();
    } catch(e) { alert('Error: ' + e.message); }
  }

  // BUG-6 fix · 20-may-2026 Dashboard PRO audit: el token CSRF vive en
  // session Flask, NO en cookie · document.cookie nunca lo encuentra,
  // helper devolvía ''. Ahora usa window._csrfTok cargado al boot del
  // dashboard (mismo patrón que cmReasignarHoy y operario_html).
  function csrfTokenNec() {
    return window._csrfTok || '';
  }
  