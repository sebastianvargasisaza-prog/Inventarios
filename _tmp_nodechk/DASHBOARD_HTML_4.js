
    (function(){
      // Plano esquemático dibujado · coords en % del contenedor · cod=null → sala de contexto (gris).
      // Plano REAL de la planta (diseño de Sebastián · coords del SVG · cod = área con estado en vivo).
      var ROOMS=[
        {id:'lavado_ut',lab:'Lavado de utensilios',x:38,y:42,w:167,h:108,fs:8},
        {id:'ducha1',lab:'Ducha',x:38,y:150,w:167,h:47,fs:8},
        {id:'alm_mp',lab:'Almacenamiento materia prima',x:38,y:205,w:180,h:95,fs:7,cod:'ALMP'},
        {id:'utens_aseo',lab:'Utensilios de aseo',x:218,y:205,w:27,h:150,fs:5.6,rot:-90},
        {id:'prod3',lab:'Producción 3 líquido semisólido',x:38,y:300,w:262,h:140,fs:8,cod:'FAB3'},
        {id:'lav_excl3',lab:'Lavado exclusa 3',x:300,y:355,w:100,h:85,fs:7,cod:'LAV'},
        {id:'excl1',lab:'Exclusa 1',x:205,y:42,w:115,h:48,fs:7.5,cod:'ESC1'},
        {id:'epp',lab:'EPP',x:205,y:90,w:22,h:115,fs:5,rot:-90},
        {id:'zona_disp',lab:'Zona de dispensación',x:227,y:90,w:93,h:115,fs:7,cod:'DISP'},
        {id:'ing_mp',lab:'Ingreso materia prima',x:320,y:42,w:110,h:48,fs:6.2},
        {id:'escalera',lab:'Escalera',x:430,y:42,w:110,h:48,fs:7.5},
        {id:'ing_cub',lab:'Ingreso cubierta',x:540,y:42,w:180,h:48,fs:7.5},
        {id:'prod1',lab:'Producción 1 líquido semisólido',x:320,y:90,w:110,h:115,fs:7,cod:'FAB1'},
        {id:'env1',lab:'Envasado 1',x:430,y:90,w:110,h:115,fs:7.5,cod:'ENV1'},
        {id:'prod_proc',lab:'Producto en proceso',x:540,y:90,w:110,h:95,fs:7},
        {id:'acond',lab:'Acondicionamiento de producto terminado',x:650,y:90,w:70,h:140,fs:6,cod:'ACOND'},
        {id:'pasillo',lab:'Pasillo gris',x:245,y:205,w:335,h:33,fs:7.5},
        {id:'excl2',lab:'Exclusa 2',x:580,y:205,w:70,h:45,fs:6.5},
        {id:'prod2',lab:'Producción 2 líquido semisólido',x:320,y:238,w:135,h:82,fs:7,cod:'FAB2'},
        {id:'env2',lab:'Envasado 2',x:455,y:238,w:95,h:82,fs:7,cod:'ENV2'},
        {id:'cc',lab:'Control de calidad',x:550,y:238,w:100,h:82,fs:7,cod:'CC'},
        {id:'rechazado',lab:'Rechazado',x:650,y:230,w:70,h:50,fs:6.5},
        {id:'devol',lab:'Devoluciones',x:650,y:280,w:70,h:50,fs:6.2},
        {id:'muestras',lab:'Muestras de retención',x:650,y:330,w:70,h:85,fs:6},
        {id:'alm_pt',lab:'Almacenamiento producto terminado',x:550,y:320,w:100,h:120,fs:6.4,cod:'ALMPT'},
        {id:'comedor',lab:'Comedor',x:340,y:450,w:130,h:80,fs:8},
        {id:'ing_esc',lab:'Ingreso escaleras',x:340,y:530,w:130,h:55,fs:7},
        {id:'cocineta',lab:'Cocineta',x:470,y:450,w:80,h:135,fs:7},
        {id:'ac',lab:'AC',x:35,y:445,w:95,h:85,fs:8},
        {id:'lockers',lab:'Lockers',x:175,y:440,w:185,h:85,fs:8},
        {id:'ingreso',lab:'Ingreso',x:95,y:525,w:280,h:23,fs:7},
        {id:'aseo',lab:'Aseo',x:35,y:525,w:60,h:23,fs:6},
        {id:'bano1',lab:'Baño',x:35,y:548,w:75,h:37,fs:7},
        {id:'bano2',lab:'Baño',x:110,y:548,w:90,h:37,fs:7},
        {id:'ducha2',lab:'Ducha',x:200,y:548,w:35,h:37,fs:5,rot:-90},
        {id:'utb',lab:'UTB',x:375,y:525,w:65,h:60,fs:7.5},
        {id:'recep',lab:'Recepción mat. envase y empaque',x:550,y:440,w:150,h:30,fs:5.6,cod:'RECEP'},
        {id:'mat_env1',lab:'Material de envase',x:550,y:470,w:150,h:115,fs:8}
      ];
      var POLYS=[
        {lab:'Área administrativa',pts:'320,310 550,310 550,450 400,450 400,355 320,355',cx:435,cy:333,fs:8},
        {lab:'Material de envase',pts:'720,90 760,55 792,575 700,562',cx:745,cy:330,fs:6.5}
      ];
      var COL={libre:'#16a34a',ocupada:'#d97706',sucia:'#dc2626',limpiando:'#0ea5e9'};
      var LBL={libre:'LIBRE',ocupada:'OCUPADA',sucia:'SUCIA',limpiando:'LIMPIANDO'};
      // Estilo PRO · blueprint claro (paredes #3a3a3a finas) + tinte de estado en las áreas de trabajo.
      var STY={
        libre:{fill:'#16a34a',op:0.14,stroke:'#16a34a'},
        ocupada:{fill:'#f59e0b',op:0.42,stroke:'#d97706'},
        sucia:{fill:'#ef4444',op:0.38,stroke:'#dc2626'},
        limpiando:{fill:'#0ea5e9',op:0.34,stroke:'#0284c7'}
      };
      var WALL='#3a3a3a';
      var DOORS=[
        {hx:205,hy:150,r:34,a0:90,a1:180},{hx:227,hy:150,r:30,a0:0,a1:90},{hx:320,hy:150,r:34,a0:90,a1:180},
        {hx:430,hy:150,r:30,a0:90,a1:180},{hx:540,hy:215,r:42,a0:180,a1:270},{hx:300,hy:438,r:34,a0:270,a1:360},
        {hx:398,hy:400,r:30,a0:180,a1:270},{hx:130,hy:528,r:30,a0:270,a1:360},{hx:95,hy:548,r:26,a0:0,a1:90},
        {hx:200,hy:472,r:30,a0:90,a1:180},{hx:470,hy:452,r:34,a0:0,a1:90},{hx:650,hy:255,r:28,a0:180,a1:270},
        {hx:540,hy:96,r:28,a0:90,a1:180},{hx:360,hy:548,r:28,a0:0,a1:90}
      ];
      var STALLS=[{x:238,y:550,w:42,h:33},{x:284,y:550,w:42,h:33},{x:330,y:550,w:42,h:33}];
      var EXTRAS=[{lab:'Equipo de agua',x:160,y:67,fs:5.2},{lab:'N',x:58,y:596,fs:7}];
      function _bays(){var A=[720,92],B=[702,558],C=[760,60],D=[790,572],N=15,o=[];for(var i=0;i<=N;i++){var t=i/N;o.push([A[0]+(B[0]-A[0])*t,A[1]+(B[1]-A[1])*t,C[0]+(D[0]-C[0])*t,C[1]+(D[1]-C[1])*t]);}return o;}
      function _doorPath(d){var R=Math.PI/180;var p0x=d.hx+d.r*Math.cos(d.a0*R),p0y=d.hy+d.r*Math.sin(d.a0*R);var p1x=d.hx+d.r*Math.cos(d.a1*R),p1y=d.hy+d.r*Math.sin(d.a1*R);var sw=d.a1>d.a0?1:0;return 'M '+d.hx+' '+d.hy+' L '+p0x.toFixed(1)+' '+p0y.toFixed(1)+' A '+d.r+' '+d.r+' 0 0 '+sw+' '+p1x.toFixed(1)+' '+p1y.toFixed(1);}
      var TWIN={FAB1:'PROD1',FAB2:'PROD2',FAB3:'PROD3',FAB_FLOAT:'PROD4'};
      function _pickArea(byCod,cod){
        var a=byCod[cod]; var t=TWIN[cod]?byCod[TWIN[cod]]:null;
        if(t&&t.produccion&&!(a&&a.produccion)) return t;
        if(t&&t.estado&&t.estado!=='libre'&&(!a||a.estado==='libre')) return t;
        return a||t||null;
      }
      function _esc2(x){return String(x==null?'':x).replace(/&/g,'&amp;').replace(/</g,'&lt;');}
      function _elapsed(m){m=parseInt(m,10);if(isNaN(m)||m<0)return '';var h=Math.floor(m/60),mm=m%60;return (h?h+'h ':'')+mm+'m';}
      function _wrap(lab,lw,fs){var words=String(lab).toUpperCase().split(' ');var max=Math.max(5,Math.floor(lw/(fs*0.56)));var lines=[],cur='';words.forEach(function(wd){var tt=cur?cur+' '+wd:wd;if(tt.length<=max||!cur){cur=tt;}else{lines.push(cur);cur=wd;}});if(cur)lines.push(cur);return lines.slice(0,3);}
      function _label(lab,cx,cy,fs,lw,rot,color,weight){
        var lines=_wrap(lab,lw,fs);var lh=fs*1.08;var y0=cy-(lines.length-1)*lh/2+fs*0.34;
        var t='<text text-anchor="middle" fill="'+color+'" font-size="'+fs+'" font-weight="'+(weight||500)+'" font-family="system-ui,sans-serif" letter-spacing="0.4"'+(rot?(' transform="rotate('+rot+' '+cx+' '+cy+')"'):'')+'>';
        lines.forEach(function(ln,i){t+='<tspan x="'+cx+'" y="'+(y0+i*lh)+'">'+_esc2(ln)+'</tspan>';});
        return t+'</text>';
      }
      window.planoFullscreen=function(){var el=document.getElementById('plano-mapa');if(!el)return;if(document.fullscreenElement){document.exitFullscreen();}else if(el.requestFullscreen){el.requestFullscreen();}};
      window.planoCerrarSala=function(){var m=document.getElementById('plano-sala-modal');if(m)m.style.display='none';};
      window.planoImprimirRotulo=function(aid){ if(aid) window.open('/planta/rotulo-limpieza/'+aid+'/pdf','_blank'); };
      window.planoFinalizar=function(pid){planoCerrarSala();if(window.finalizarFabVivo){var pr=window.finalizarFabVivo(pid);if(pr&&pr.then){pr.then(function(){setTimeout(window.cargarPlanoGrid,500);});}else{setTimeout(window.cargarPlanoGrid,900);}}};
      window.planoIrLimpieza=function(){planoCerrarSala();var b=document.querySelector('.sub-btn[onclick*="rotuloslimp"]');if(b)b.click();};
      window.planoIniciarAqui=function(aid){planoCerrarSala();var b=document.querySelector('.sub-btn[onclick*="produccion"]');if(b)b.click();setTimeout(function(){var s=document.getElementById('prod-area');if(s)s.value=aid;},600);};
      window.planoAbrirSala=function(cod){
        var a=(window._PLANO_LIVE||{})[cod]; if(!a) return;
        var e=a.estado||'libre', p=a.produccion;
        var m=document.getElementById('plano-sala-modal'), b=document.getElementById('plano-sala-body'); if(!m||!b) return;
        var CP={libre:'#16a34a',ocupada:'#d97706',sucia:'#dc2626',limpiando:'#0ea5e9'}, LP={libre:'LIBRE',ocupada:'OCUPADA',sucia:'SUCIA · a limpiar',limpiando:'EN LIMPIEZA'};
        var cc=CP[e]||'#64748b';
        var h='<div style="font-weight:800;font-size:17px;color:#0f172a">'+_esc2(a.nombre||cod)+'</div>';
        h+='<div style="display:inline-block;margin:8px 0;padding:3px 12px;border-radius:8px;font-weight:800;font-size:12px;background:'+cc+'22;color:'+cc+'">'+(LP[e]||e)+'</div>';
        if(p){ h+='<div style="font-size:14px;line-height:1.7;color:#334155">&#129514; <b>'+_esc2(p.producto||'')+'</b>'+(p.kg?(' · '+p.kg+' kg'):'')+(p.operario?('<br>&#128100; '+_esc2(p.operario)):'')+(p.mins!=null?('<br>&#9201; '+_elapsed(p.mins)+' corriendo'):'')+'</div>'; }
        h+='<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:16px">';
        if(p){ if(p.vivo){ h+='<button onclick="planoFinalizarVivo('+(a.id||0)+')" style="flex:1 1 100%;padding:10px;background:#16a34a;color:#fff;border:none;border-radius:8px;font-weight:700;cursor:pointer">&#127937; Finalizar '+_esc2(p.fase||'envasado')+'</button>'; } else { h+='<button onclick="planoFinalizar('+p.id+')" style="flex:1 1 100%;padding:10px;background:#16a34a;color:#fff;border:none;border-radius:8px;font-weight:700;cursor:pointer">&#127937; Finalizar producción</button>'; } }
        if(e==='sucia'||e==='limpiando'){ h+='<button onclick="planoCerrarSala();abrirRotulo('+(a.id||0)+')" style="flex:1 1 100%;padding:10px;background:#7c3aed;color:#fff;border:none;border-radius:8px;font-weight:700;cursor:pointer">'+(e==='limpiando'?'&#10003; Verificar limpieza (Calidad)':'&#129529; Registrar limpieza')+'</button>'; }
        if(e==='libre'){ h+='<button onclick="planoIniciarAqui('+(a.id||0)+')" style="flex:1 1 100%;padding:10px;background:#2563eb;color:#fff;border:none;border-radius:8px;font-weight:700;cursor:pointer">&#9654; Iniciar fabricación aquí</button>'; }
        h+='<button onclick="planoImprimirRotulo('+(a.id||0)+')" style="flex:1 1 100%;padding:9px;background:#0f766e;color:#fff;border:none;border-radius:8px;font-weight:700;cursor:pointer">&#128424;&#65039; Imprimir rótulo (F02)</button>';
        h+='<button onclick="planoCerrarSala()" style="flex:1;padding:9px;background:#fff;color:#475569;border:1px solid #cbd5e1;border-radius:8px;font-weight:700;cursor:pointer">Cerrar</button>';
        h+='</div>';
        b.innerHTML=h; m.style.display='flex';
      };
      async function _planoCsrf(){try{return (await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json()).csrf_token;}catch(e){return '';}}
      function _planoPost(url,body,t){return fetch(url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify(body)});}
      window.planoFinalizarVivo=async function(aid){planoCerrarSala();var t=await _planoCsrf();try{await _planoPost('/api/planta/area/liberar-vivo',{area_id:aid},t);}catch(e){}setTimeout(window.cargarPlanoGrid,400);};
      window.simularFlujoPlanta=async function(){
        if(!confirm('SIMULACRO: voy a INICIAR una fabricación de demostración en un área libre — la vas a ver 🟠 ocupada en el plano — y en ~7s la FINALIZO (queda 🔴 sucia y el bulk va solo a Envasado). ¿Arranco?')) return;
        var t=await _planoCsrf();
        var areas=((await (await fetch('/api/planta/areas',{credentials:'same-origin'})).json()).areas)||[];
        var seen={}, libre=null;
        areas.filter(function(a){return a.puede_producir && String(a.estado||'libre').toLowerCase()==='libre';}).forEach(function(a){var k=(a.nombre||'').toLowerCase();if(!seen[k]){seen[k]=1;if(!libre)libre=a;}});
        if(!libre){ alert('No hay un área de fabricación LIBRE para el simulacro. Liberá una (o dale 🧹 Limpiar).'); return; }
        var r=await _planoPost('/api/planta/fabricacion/crear-iniciar',{producto:'🧪 SIMULACRO Demo',area_id:libre.id,cantidad_kg:10,presentacion:'30ml'},t);
        var d=await r.json();
        if(d&&d.error){ alert('No se pudo iniciar el simulacro: '+d.error); return; }
        await cargarPlanoGrid();
        alert('▶ Simulacro INICIADO en "'+libre.nombre+'". Mirá el plano: esa sala está 🟠 ocupada con producto + operario + ⏱️ tiempo. Dale OK y en ~7s la finalizo.');
        setTimeout(async function(){
          var pl=((await (await fetch('/api/planta/plano-fabricacion?todas=1',{credentials:'same-origin'})).json()).areas)||[];
          var ar=pl.filter(function(a){return a.produccion && String(a.produccion.producto||'').indexOf('SIMULACRO')>=0 && a.produccion.id;})[0];
          if(!ar){ await cargarPlanoGrid(); return; }
          var t2=await _planoCsrf();
          var rf=await _planoPost('/api/programacion/programar/'+ar.produccion.id+'/terminar',{kg_real:9.6},t2);
          var df=await rf.json();
          await cargarPlanoGrid();
          alert('🏁 Simulacro FINALIZADO. La sala quedó 🔴 sucia y el bulk «🧪 SIMULACRO Demo» (lote '+(df.bulk_lote||'auto')+' · 30ml) ya está en la cola de ENVASADO. Andá a Producción → Envasado para verlo. Después dale 🧹 Limpiar simulacro.');
        }, 7000);
      };
      window.limpiarSimulacro=async function(){
        if(!confirm('¿Borrar los datos del SIMULACRO (producción demo + bulk en envasado) y liberar las áreas?')) return;
        var t=await _planoCsrf();
        var d=await (await _planoPost('/api/planta/simulacro/limpiar',{},t)).json();
        await cargarPlanoGrid();
        var _est=d.estados_antes?(' · estados que había: '+Object.keys(d.estados_antes).map(function(k){return k+'='+d.estados_antes[k];}).join(', ')):'';
        alert('🧹 Prueba limpiada · '+(d.pp_borradas||0)+' fabricación + '+(d.bulk_borradas||0)+' bulk + '+(d.rotulos_borrados||0)+' rótulos borrados · '+((d.areas_liberadas||0)+(d.areas_reset||0))+' áreas vueltas a LIMPIO · '+(d.colgadas_cerradas||0)+' colgadas cerradas.'+_est);
      };
      window.abrirIniciarVivo=async function(fase){
        var m=document.getElementById('vivo-modal'); if(!m) return;
        fase=fase||'envasado';
        document.getElementById('vivo-fase').value=fase;
        document.getElementById('vivo-producto').value='';
        document.getElementById('vivo-titulo').textContent='▶ Iniciar '+(fase==='acondicionamiento'?'acondicionamiento':'envasado')+' en vivo';
        try{
          var d=await (await fetch('/api/planta/areas',{credentials:'same-origin'})).json();
          var areas=(d.areas||d.items||[]);
          var filt=areas.filter(function(a){ return fase==='acondicionamiento' ? ((a.codigo||'').toUpperCase()==='ACOND') : a.puede_envasar; });
          var s=document.getElementById('vivo-area'); s.innerHTML='<option value="">-- elegí área --</option>'+filt.map(function(a){return '<option value="'+a.id+'">'+_esc2(a.nombre)+(String(a.estado||'').toLowerCase()==='ocupada'?' (ocupada)':'')+'</option>';}).join('');
        }catch(e){}
        try{
          var o=await (await fetch('/api/planta/operarios',{credentials:'same-origin'})).json();
          var sel=document.getElementById('vivo-operario');
          sel.innerHTML='<option value="">-- opcional --</option>'+(o.operarios||o.items||[]).map(function(x){return '<option value="'+x.id+'">'+_esc2(((x.nombre||'')+' '+(x.apellido||'')).trim())+'</option>';}).join('');
        }catch(e){}
        m.style.display='flex';
      };
      window.cerrarVivo=function(){var m=document.getElementById('vivo-modal');if(m)m.style.display='none';};
      window.guardarVivo=async function(){
        var producto=(document.getElementById('vivo-producto').value||'').trim();
        var area=document.getElementById('vivo-area').value;
        var op=document.getElementById('vivo-operario').value;
        var fase=document.getElementById('vivo-fase').value;
        if(!producto||!area){ alert('Producto y área son obligatorios'); return; }
        var t=await _planoCsrf();
        try{
          var r=await _planoPost('/api/planta/area/ocupar-vivo',{area_id:parseInt(area,10),producto:producto,operario_id:op?parseInt(op,10):0,fase:fase},t);
          var d=await r.json();
          if(d.error){ alert('Error: '+d.error); return; }
          cerrarVivo();
          alert('✓ '+(fase==='acondicionamiento'?'Acondicionamiento':'Envasado')+' iniciado en '+(d.area||'')+' · míralo en el Plano');
          if(window.cargarPlanoGrid) window.cargarPlanoGrid();
        }catch(e){ alert('Error de conexión'); }
      };
      window.cargarPlanoGrid=async function(){
        var mapa=document.getElementById('plano-mapa'); var g=document.getElementById('plano-grid');
        if(!mapa) return;
        var data; try{ data=await (await fetch('/api/planta/plano-fabricacion?todas=1',{credentials:'same-origin'})).json(); }catch(e){ mapa.innerHTML='<div style="padding:20px;color:#b91c1c">Error cargando el plano</div>'; return; }
        var byCod={}; (data.areas||[]).forEach(function(a){ byCod[(a.codigo||'').toUpperCase()]=a; });
        window._PLANO_LIVE={};
        var sv='<svg viewBox="0 0 838 609" style="width:100%;height:auto;display:block;background:#fbfbf9">';
        sv+='<polygon points="36,40 722,40 722,87 760,53 793,576 700,562 700,587 33,587 33,40" fill="none" stroke="#2a2a2a" stroke-width="2.6" stroke-linejoin="round"/>';
        POLYS.forEach(function(pp){ sv+='<polygon points="'+pp.pts+'" fill="none" stroke="'+WALL+'" stroke-width="0.9"/>'; });
        var cards=''; var cnt={libre:0,ocupada:0,sucia:0,limpiando:0}; var totKg=0; var nLate=0; var LATE=480;
        ROOMS.forEach(function(r){
          var live=r.cod?_pickArea(byCod,r.cod):null;
          var e=live?(live.estado||'libre'):null;
          var st=e?STY[e]:null;
          var lw=r.rot?r.h:r.w, hasP=live&&live.produccion;
          if(e){cnt[e]=(cnt[e]||0)+1;}
          if(st){ var pulse=(e==='ocupada'||e==='sucia'); sv+='<rect x="'+r.x+'" y="'+r.y+'" width="'+r.w+'" height="'+r.h+'" fill="'+st.fill+'" fill-opacity="'+st.op+'">'+(pulse?('<animate attributeName="fill-opacity" values="'+st.op+';'+(st.op*0.5).toFixed(2)+';'+st.op+'" dur="2.4s" repeatCount="indefinite"/>'):'')+'</rect>'; }
          if(r.cod){ window._PLANO_LIVE[r.cod]=live?{id:live.id,nombre:live.nombre||r.lab,estado:e,produccion:live.produccion}:{id:0,nombre:r.lab,estado:'libre',produccion:null}; }
          sv+='<rect x="'+r.x+'" y="'+r.y+'" width="'+r.w+'" height="'+r.h+'" fill="none" stroke="'+(st?st.stroke:WALL)+'" stroke-width="'+(st?1.4:0.8)+'"'+(r.cod?(' style="cursor:pointer" onclick="planoAbrirSala(&#39;'+r.cod+'&#39;)"'):'')+'><title>'+_esc2(r.lab)+(e?(' · '+(LBL[e]||e)):'')+(r.cod?' · clic para acciones':'')+'</title></rect>';
          var cx=r.x+r.w/2, cy=r.y+r.h/2;
          sv+=_label(r.lab,cx,(hasP?cy-r.h*0.24:cy),r.fs,lw,r.rot||0,'#454545',(st?600:400));
          if(hasP){var p=live.produccion;if(p.kg)totKg+=parseFloat(p.kg)||0;var lt=(p.mins!=null&&p.mins>LATE);if(lt)nLate++;var t2=r.fs*0.92;sv+='<text text-anchor="middle" font-family="system-ui,sans-serif" fill="#1f2937" font-size="'+t2+'" font-weight="700"><tspan x="'+cx+'" y="'+(cy+r.h*0.04)+'">'+_esc2(String(p.producto||'').slice(0,18))+'</tspan>'+(p.operario?('<tspan x="'+cx+'" y="'+(cy+r.h*0.04+t2*1.15)+'">&#128100; '+_esc2(String(p.operario).slice(0,16))+'</tspan>'):'')+(p.mins!=null?('<tspan x="'+cx+'" y="'+(cy+r.h*0.04+t2*2.3)+'" fill="'+(lt?'#dc2626':'#b45309')+'" font-weight="800">'+(lt?'&#9888;&#65039; ':'&#9201; ')+_elapsed(p.mins)+'</tspan>'):'')+'</text>';}
          if(r.cod){
            var cc=e?COL[e]:'#94a3b8';
            cards+='<div style="background:#fff;border:1px solid #e5e7eb;border-top:5px solid '+cc+';border-radius:12px;padding:12px">';
            cards+='<div style="font-weight:800;font-size:14px;color:#111">'+_esc2(r.lab)+'</div>';
            cards+='<div style="display:inline-block;margin:5px 0;padding:2px 9px;border-radius:6px;font-size:11px;font-weight:700;background:'+cc+'22;color:'+cc+'">'+(LBL[e]||e||'—')+'</div>';
            if(hasP){var q=live.produccion;cards+='<div style="font-size:13px;line-height:1.5;color:#333">&#129514; <b>'+_esc2(q.producto||'')+'</b>'+(q.kg?('<br>'+q.kg+' kg'):'')+(q.operario?('<br>&#128100; '+_esc2(q.operario)):'')+(q.mins!=null?('<br>&#9201; '+_elapsed(q.mins)+' corriendo'):'')+'</div>';}
            else{cards+='<div style="color:#9ca3af;font-size:13px">disponible</div>';}
            cards+='</div>';
          }
        });
        STALLS.forEach(function(s2){ sv+='<rect x="'+s2.x+'" y="'+s2.y+'" width="'+s2.w+'" height="'+s2.h+'" fill="none" stroke="'+WALL+'" stroke-width="0.7"/>'; });
        DOORS.forEach(function(d){ sv+='<path d="'+_doorPath(d)+'" fill="none" stroke="'+WALL+'" stroke-width="0.7" opacity="0.65"/>'; });
        _bays().forEach(function(b){ sv+='<line x1="'+b[0].toFixed(1)+'" y1="'+b[1].toFixed(1)+'" x2="'+b[2].toFixed(1)+'" y2="'+b[3].toFixed(1)+'" stroke="'+WALL+'" stroke-width="0.6" opacity="0.5"/>'; });
        EXTRAS.forEach(function(x){ sv+=_label(x.lab,x.x,x.y,x.fs,80,0,'#8c8c8c',400); });
        POLYS.forEach(function(pp){ var prot=(String(pp.lab).indexOf('Material')===0)?-82:0; sv+=_label(pp.lab,pp.cx,pp.cy,pp.fs,140,prot,'#454545',400); });
        sv+='</svg>';
        mapa.innerHTML=sv;
        if(g) g.innerHTML=cards;
        var rs=document.getElementById('plano-resumen');
        if(rs){ rs.innerHTML='<span style="background:#16a34a22;color:#15803d;padding:2px 8px;border-radius:8px;font-weight:700">'+cnt.libre+' libres</span><span style="background:#d9770622;color:#b45309;padding:2px 8px;border-radius:8px;font-weight:700">'+cnt.ocupada+' ocupadas</span><span style="background:#dc262622;color:#b91c1c;padding:2px 8px;border-radius:8px;font-weight:700">'+cnt.sucia+' sucias</span>'+(cnt.limpiando?('<span style="background:#0ea5e922;color:#0369a1;padding:2px 8px;border-radius:8px;font-weight:700">'+cnt.limpiando+' limpiando</span>'):'')+(totKg>0?('<span style="background:#7c3aed22;color:#6d28d9;padding:2px 8px;border-radius:8px;font-weight:700">'+Math.round(totKg)+' kg en producción</span>'):'')+(nLate?('<span style="background:#dc2626;color:#fff;padding:2px 8px;border-radius:8px;font-weight:700">&#9888;&#65039; '+nLate+' pasada(s) de tiempo</span>'):''); }
        var up=document.getElementById('plano-update');
        if(up){ var n=new Date(); up.textContent='actualizado '+('0'+n.getHours()).slice(-2)+':'+('0'+n.getMinutes()).slice(-2); }
      };
      setInterval(function(){var t=document.getElementById('plano');if(t&&t.classList.contains('active'))cargarPlanoGrid();},20000);
    })();
    