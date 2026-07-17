
    (function(){
      async function _csrfFab(){try{return (await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json()).csrf_token;}catch(e){return '';}}
      window.cargarOperariosFab=async function(){
        var sel=document.getElementById('prod-operario'); if(!sel) return;
        try{
          var d=await (await fetch('/api/planta/operarios',{credentials:'same-origin'})).json();
          var o='<option value="">-- opcional --</option>';
          (d.operarios||d.items||[]).filter(function(x){return !x.fija_en_dispensacion;}).forEach(function(x){o+='<option value="'+x.id+'">'+((x.nombre||'')+' '+(x.apellido||'')).trim()+'</option>';});
          sel.innerHTML=o;
        }catch(e){}
      };
      window.iniciarFabVivo=async function(){
        var prod=((document.getElementById('prod-sel')||{}).value||(document.getElementById('prod-manual')||{}).value||'').trim();
        var kg=parseFloat((document.getElementById('prod-kg')||{}).value);
        var area=(document.getElementById('prod-area')||{}).value;
        var op=(document.getElementById('prod-operario')||{}).value;
        var m=document.getElementById('prod-msg');
        if(!prod){m.innerHTML='<div style="background:#fee2e2;color:#991b1b;padding:8px 12px;border-radius:6px">Elegí un producto.</div>';return;}
        if(!kg||kg<=0){m.innerHTML='<div style="background:#fee2e2;color:#991b1b;padding:8px 12px;border-radius:6px">Ingresá la cantidad en kg.</div>';return;}
        if(!area){m.innerHTML='<div style="background:#fee2e2;color:#991b1b;padding:8px 12px;border-radius:6px">Elegí un área de fabricación.</div>';return;}
        var body={producto:prod,area_id:parseInt(area),cantidad_kg:kg}; if(op) body.operario_id=parseInt(op);
        var _pres=((document.getElementById('prod-presentacion')||{}).value||'').trim(); if(_pres) body.presentacion=_pres;
        var t=await _csrfFab();
        var r=await fetch('/api/planta/fabricacion/crear-iniciar',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify(body)});
        var j=await r.json();
        if(!r.ok){m.innerHTML='<div style="background:#fee2e2;color:#991b1b;padding:8px 12px;border-radius:6px">'+(j.mensaje||j.error||('Error '+r.status))+'</div>';return;}
        m.innerHTML='<div style="background:#dcfce7;color:#166534;padding:8px 12px;border-radius:6px;font-weight:700">&#9654; Fabricación iniciada · MP descontada · área ocupada</div>';
        window.cargarEnProcesoFab();
      };
      // 25-jun · "En fabricación ahora" y "Fabricaciones terminadas" se ABSORBIERON en la tabla única
      // "Órdenes de Producción" (las en-curso salen arriba con su botón Finalizar). Estos quedan como
      // wrappers que refrescan esa tabla, para que todos los llamadores existentes sigan funcionando.
      // PERF 9-jul (speed-audit #4): cargarEnCurso y cargarHistProd fetchean el MISMO endpoint pesado
      // y cargarEnProcesoFab llama a ambas → doble request. Promesa compartida (M59): dedup mientras
      // está en vuelo, se limpia al resolver → un refresh posterior trae datos frescos.
      window._ordUnifFabFetch=function(){
        if(window._ordUnifFabPromise) return window._ordUnifFabPromise;
        var p=fetch('/api/brd/ordenes-unificadas?fase=fabricacion',{credentials:'same-origin'})
          .then(function(r){return r.json();})
          .finally(function(){ setTimeout(function(){ window._ordUnifFabPromise=null; },50); });
        window._ordUnifFabPromise=p; return p;
      };
      window.cargarEnCurso=async function(){
        var tb=document.getElementById('encurso-body'); if(!tb) return;
        try{
          var d=await window._ordUnifFabFetch();
          var enc=((d&&d.ordenes)||[]).filter(function(o){return o.produccion_id;});
          if(!enc.length){ tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:18px">Nada en fabricaci\u00f3n ahora \u00b7 abr\u00ed una orden arriba \u25b2</td></tr>'; return; }
          tb.innerHTML=enc.map(function(o){
            var leg=o.ebr_id
              ? '<button onclick="abrirEBR('+o.ebr_id+',&#39;encurso-runner&#39;)" style="background:#6d28d9;color:#fff;border:none;border-radius:5px;padding:4px 9px;font-size:10px;font-weight:700;cursor:pointer;margin-right:6px" title="Trabajar el batch record: despeje, pesaje, pasos, IPC, cierre">&#128203; Pasos</button>'
              : (o.link?'<a href="'+o.link+'" style="color:#7c3aed;font-weight:700;text-decoration:none;font-size:11px;margin-right:6px">Legajo \u2192</a>':'');
            return '<tr>'+
              '<td style="font-family:monospace;font-weight:700;color:#1e40af">'+_escHTML(o.numero_op||'')+'</td>'+
              '<td style="font-weight:600">'+_escHTML(o.producto||'\u2014')+'</td>'+
              '<td>'+_escHTML(o.operador||'\u2014')+'</td>'+
              '<td style="text-align:right">'+(o.teorica_g!=null?(Number(o.teorica_g).toLocaleString('es-CO')+' g'):'\u2014')+'</td>'+
              '<td style="text-align:center"><span class="cx-chip cx-chip-warn">En proceso</span></td>'+
              '<td style="text-align:center">'+leg+'<button onclick="eliminarFabVivo('+o.produccion_id+')" title="Eliminar esta produccion y revertir la MP - para borrar las mal registradas" style="background:#fee2e2;color:#dc2626;border:1px solid #fca5a5;border-radius:5px;padding:4px 8px;font-size:10px;font-weight:700;cursor:pointer;margin-right:5px">&#128465;</button><button onclick="finalizarFabVivo('+o.produccion_id+')" style="background:#d97706;color:#fff;border:none;border-radius:5px;padding:4px 9px;font-size:10px;font-weight:700;cursor:pointer">\u25a0 Finalizar</button></td>'+
            '</tr>';
          }).join('');
        }catch(e){ tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:#c00;padding:16px">Error: '+_escHTML(e.message||e)+'</td></tr>'; }
        if(window.cargarMiTrabajo){ try{ window.cargarMiTrabajo(); }catch(e){} }
      };
      // Bandeja "Mi trabajo" por ROL (Nivel 2): cada quien ve su cola de tareas en los legajos en curso.
      window.cargarMiTrabajo=async function(){
        var box=document.getElementById('mi-trabajo-panel'); if(!box) return;
        try{
          var d=await (await fetch('/api/brd/mi-trabajo',{credentials:'same-origin'})).json();
          if(!d||!d.rol||(!d.rol.realiza&&!d.rol.verifica)){ box.innerHTML=''; return; }
          var rc=({operario:'#16a34a',jefe_produccion:'#2563eb',calidad:'#0891b2',director_tecnico:'#7c3aed',aseguramiento:'#b45309',admin:'#6d28d9'})[d.rol.tipo]||'#6d28d9';
          var its=d.items||[];
          var h='<div style="background:'+rc+'0d;border:1px solid '+rc+'40;border-radius:12px;padding:12px 14px">';
          h+='<div style="font-size:13px;font-weight:800;color:'+rc+';margin-bottom:'+(its.length?'8px':'0')+'">&#128188; Mi trabajo &middot; '+_escHTML(d.rol.rol||'')+(its.length?(' &middot; '+d.total_legajos+' legajo(s)'):'')+'</div>';
          if(!its.length){ h+='<div style="font-size:12px;color:#16a34a;font-weight:600">&#10003; No ten\u00e9s tareas pendientes en los legajos en curso</div>'; }
          else{ its.forEach(function(it){
            var tt=(it.tareas||[]).map(function(t){return t.txt;}).join(' &middot; ');
            h+='<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;padding:7px 0;border-top:1px solid '+rc+'22;flex-wrap:wrap">';
            h+='<div><b style="color:#1e293b">'+_escHTML(it.numero_op||('Lote '+it.lote))+'</b> <span style="color:#64748b;font-size:12px">'+_escHTML(it.producto||'')+'</span><div style="font-size:11px;color:'+rc+';font-weight:600">'+tt+'</div></div>';
            h+='<button onclick="abrirEBR('+it.ebr_id+',&#39;encurso-runner&#39;)" style="background:'+rc+';color:#fff;border:none;border-radius:6px;padding:5px 12px;font-size:11px;font-weight:700;cursor:pointer">Abrir &#8594;</button>';
            h+='</div>';
          }); }
          h+='</div>';
          box.innerHTML=h;
        }catch(e){ box.innerHTML=''; }
      };
      window.cargarEnProcesoFab=async function(){
        if(window.cargarEnCurso){ try{ window.cargarEnCurso(); }catch(e){} }
        if(window.cargarHistProd){ try{ window.cargarHistProd(); }catch(e){} }
      };
      window.cargarFabTerminadas=async function(){ /* absorbida en Órdenes / Históricos */ };
      window.limpiarDemos=async function(btn){
        if(!confirm('Borrar TODOS los demos? (producciones demo + sus legajos · no toca producciones reales · dejan de salir en el calendario)'))return;
        if(btn){ btn.disabled=true; btn.textContent='Limpiando...'; }
        try{
          var t=await _csrfFab();
          var r=await fetch('/api/brd/limpiar-demos',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:'{}'});
          var j=await r.json();
          if(!r.ok){ alert('Error: '+(j.error||r.status)); return; }
          alert('✓ Demos borrados: '+(j.producciones_borradas||0)+' producciones · '+(j.legajos_descartados||0)+' legajos. Ya no salen en el calendario.');
          if(window.cargarEnCurso) window.cargarEnCurso();
        }catch(e){ alert('Error: '+(e.message||e)); }
        finally{ if(btn){ btn.disabled=false; btn.innerHTML='&#129529; Limpiar demos'; } }
      };
      window.crearDemoLegajo=async function(btn){
        if(btn){ btn.disabled=true; btn.textContent='Creando\u2026'; }
        try{
          var t=await _csrfFab();
          var r=await fetch('/api/brd/demo-legajo',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:'{}'});
          var j=await r.json();
          if(!r.ok){ alert('Error: '+(j.error||r.status)); return; }
          alert('\ud83e\uddea Demo creado: '+j.producto+' \u00b7 toc\u00e1 \ud83d\udccb Pasos en su orden para ver el batch record (sin descontar MP). Borralo con \ud83e\uddf9 Limpiar en el Plano.');
          if(window.cargarEnCurso) window.cargarEnCurso();
        }catch(e){ alert('Error: '+(e.message||e)); }
        finally{ if(btn){ btn.disabled=false; btn.innerHTML='\ud83e\uddea Demo legajo'; } }
      };
      window.eliminarFabVivo=async function(pid){
        if(!confirm('Eliminar esta produccion y REVERTIR el descuento de MP? Para borrar las mal registradas y volver a empezar limpio.'))return;
        var t=await _csrfFab();
        var r=await fetch('/api/plan/proximas/'+pid,{method:'DELETE',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify({force:true})});
        var j=await r.json();
        if(!r.ok){ alert('Error: '+(j.error||r.status)); return; }
        alert('Eliminada - MP revertida al inventario.');
        if(window.cargarEnCurso) window.cargarEnCurso();
      };
      window.finalizarFabVivo=async function(pid){
        if(!confirm('¿Finalizar esta fabricación? El área queda sucia hasta que la limpien.')) return;
        var t=await _csrfFab();
        var r=await fetch('/api/programacion/programar/'+pid+'/terminar',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:'{}'});
        if(r.ok){document.getElementById('prod-msg').innerHTML='<div style="background:#dcfce7;color:#166534;padding:8px 12px;border-radius:6px">&#9632; Fabricación finalizada · área marcada sucia</div>';window.cargarEnProcesoFab();window.cargarFabTerminadas();}
      };
      try{cargarOperariosFab();cargarEnProcesoFab();cargarFabTerminadas();setInterval(function(){ if(document.hidden) return; var _el=document.getElementById('encurso-body'); if(_el && _el.offsetParent===null) return; cargarEnProcesoFab();cargarFabTerminadas(); },20000);}catch(e){}
    })();
    