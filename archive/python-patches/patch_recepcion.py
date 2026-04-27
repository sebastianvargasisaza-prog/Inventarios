"""
patch_recepcion.py — Fix 5 bugs in the reception (ingreso) flow
Bugs fixed:
  B1 (CRITICAL/backend):  cantidad > 0 validation missing in registrar_recepcion
  B2 (MODERATE/backend):  except:pass silences OC update errors
  B3 (MODERATE/frontend): buscarMPIngreso fetches /api/maestro-mps on every keypress
  B4 (MINOR/frontend):    Registrar button has no loading/disabled state -> double-submit
  B5 (MINOR/frontend):    Form not cleared after successful registration
"""
import ast, sys, re

BACKEND = '/tmp/inv_p8/api/blueprints/inventario.py'
FRONTEND = '/tmp/inv_p8/api/templates_py/dashboard_html.py'

# ─── Backend patches ────────────────────────────────────────────────────────

with open(BACKEND, 'r', encoding='utf-8') as f:
    be = f.read()

original_be = be

# B1 — Add cantidad > 0 validation.
# Insert after the line that checks `if not codigo`
OLD_B1 = (
    "    if not codigo: return jsonify({'error': 'Codigo MP requerido'}), 400\n"
    "    conn = sqlite3.connect(DB_PATH)"
)
NEW_B1 = (
    "    if not codigo: return jsonify({'error': 'Codigo MP requerido'}), 400\n"
    "    cantidad_recibida = float(d.get('cantidad') or 0)\n"
    "    if cantidad_recibida <= 0:\n"
    "        return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400\n"
    "    conn = sqlite3.connect(DB_PATH)"
)
assert be.count(OLD_B1) == 1, f"B1: expected 1 match, got {be.count(OLD_B1)}"
be = be.replace(OLD_B1, NEW_B1)

# B1b — Use the validated variable instead of re-evaluating d.get('cantidad',0) in INSERT
OLD_B1b = (
    "              (codigo,nombre,float(d.get('cantidad',0)),'Entrada',datetime.now().isoformat(),"
)
NEW_B1b = (
    "              (codigo,nombre,cantidad_recibida,'Entrada',datetime.now().isoformat(),"
)
assert be.count(OLD_B1b) == 1, f"B1b: expected 1 match, got {be.count(OLD_B1b)}"
be = be.replace(OLD_B1b, NEW_B1b)

# B1c — Use the validated variable in OC update
OLD_B1c = (
    "            c.execute(\"UPDATE ordenes_compra_items SET cantidad_recibida_g=cantidad_recibida_g+?,lote_asignado=? WHERE numero_oc=? AND codigo_mp=?\",\n"
    "                      (float(d.get('cantidad',0)), lote, numero_oc, codigo))"
)
NEW_B1c = (
    "            c.execute(\"UPDATE ordenes_compra_items SET cantidad_recibida_g=cantidad_recibida_g+?,lote_asignado=? WHERE numero_oc=? AND codigo_mp=?\",\n"
    "                      (cantidad_recibida, lote, numero_oc, codigo))"
)
assert be.count(OLD_B1c) == 1, f"B1c: expected 1 match, got {be.count(OLD_B1c)}"
be = be.replace(OLD_B1c, NEW_B1c)

# B1d — Fix the response still using d.get('cantidad',0)
OLD_B1d = (
    "    return jsonify({'message': msg,'lote':lote,'codigo':codigo,'nombre':nombre,'cantidad':d.get('cantidad',0),'cuarentena':cuarentena}), 201"
)
NEW_B1d = (
    "    return jsonify({'message': msg,'lote':lote,'codigo':codigo,'nombre':nombre,'cantidad':cantidad_recibida,'cuarentena':cuarentena}), 201"
)
assert be.count(OLD_B1d) == 1, f"B1d: expected 1 match, got {be.count(OLD_B1d)}"
be = be.replace(OLD_B1d, NEW_B1d)

# B2 — Replace silent except:pass in OC update with observable error handling
OLD_B2 = (
    "    # Cerrar OC si se referencia una\n"
    "    if numero_oc:\n"
    "        try:\n"
    "            c.execute(\"UPDATE ordenes_compra_items SET cantidad_recibida_g=cantidad_recibida_g+?,lote_asignado=? WHERE numero_oc=? AND codigo_mp=?\",\n"
    "                      (cantidad_recibida, lote, numero_oc, codigo))\n"
    "            # verificar si todos los items de la OC estan recibidos\n"
    "            c.execute(\"SELECT COUNT(*) FROM ordenes_compra_items WHERE numero_oc=? AND (cantidad_g - cantidad_recibida_g) > 1\", (numero_oc,))\n"
    "            pendientes = c.fetchone()[0]\n"
    "            if pendientes == 0:\n"
    "                c.execute(\"UPDATE ordenes_compra SET estado='RECIBIDA',fecha_recepcion=datetime('now'),recibido_por=? WHERE numero_oc=?\",\n"
    "                          (d.get('operador',''), numero_oc))\n"
    "        except: pass"
)
NEW_B2 = (
    "    # Cerrar OC si se referencia una\n"
    "    oc_warning = None\n"
    "    if numero_oc:\n"
    "        try:\n"
    "            c.execute(\"UPDATE ordenes_compra_items SET cantidad_recibida_g=cantidad_recibida_g+?,lote_asignado=? WHERE numero_oc=? AND codigo_mp=?\",\n"
    "                      (cantidad_recibida, lote, numero_oc, codigo))\n"
    "            # verificar si todos los items de la OC estan recibidos\n"
    "            c.execute(\"SELECT COUNT(*) FROM ordenes_compra_items WHERE numero_oc=? AND (cantidad_g - cantidad_recibida_g) > 1\", (numero_oc,))\n"
    "            pendientes = c.fetchone()[0]\n"
    "            if pendientes == 0:\n"
    "                c.execute(\"UPDATE ordenes_compra SET estado='RECIBIDA',fecha_recepcion=datetime('now'),recibido_por=? WHERE numero_oc=?\",\n"
    "                          (d.get('operador',''), numero_oc))\n"
    "        except Exception as oc_err:\n"
    "            # Log but don't fail the reception — OC can be reconciled manually\n"
    "            print(f'[WARN] OC update failed for {numero_oc}: {oc_err}', flush=True)\n"
    "            oc_warning = f'OC {numero_oc} no pudo actualizarse automaticamente — verificar manualmente'"
)
assert be.count(OLD_B2) == 1, f"B2: expected 1 match, got {be.count(OLD_B2)}"
be = be.replace(OLD_B2, NEW_B2)

# B2b — Expose oc_warning in response message
OLD_B2b = (
    "    if numero_oc: msg += f' | OC {numero_oc} actualizada'\n"
    "    return jsonify({'message': msg,'lote':lote,'codigo':codigo,'nombre':nombre,'cantidad':cantidad_recibida,'cuarentena':cuarentena}), 201"
)
NEW_B2b = (
    "    if numero_oc and not oc_warning: msg += f' | OC {numero_oc} actualizada'\n"
    "    if oc_warning: msg += f' | ⚠ {oc_warning}'\n"
    "    return jsonify({'message': msg,'lote':lote,'codigo':codigo,'nombre':nombre,'cantidad':cantidad_recibida,'cuarentena':cuarentena,'oc_warning':oc_warning}), 201"
)
assert be.count(OLD_B2b) == 1, f"B2b: expected 1 match, got {be.count(OLD_B2b)}"
be = be.replace(OLD_B2b, NEW_B2b)

# Verify Python syntax
try:
    ast.parse(be)
    print('Backend: Python syntax OK')
except SyntaxError as e:
    print(f'Backend SyntaxError line {e.lineno}: {e.msg}')
    sys.exit(1)

# Confirm changes
print(f'Backend: B1 cantidad validation added: {"cantidad_recibida <= 0" in be}')
_b1b_check = "cantidad_recibida,'Entrada'" in be
print(f'Backend: B1b INSERT uses validated var: {_b1b_check}')
print(f'Backend: B2 OC error observable: {"oc_err" in be}')

with open(BACKEND, 'w', encoding='utf-8') as f:
    f.write(be)
print('Backend written.\n')

# ─── Frontend patches ────────────────────────────────────────────────────────

with open(FRONTEND, 'r', encoding='utf-8') as f:
    fe = f.read()

original_fe = fe

# B3 — Fix buscarMPIngreso to use _cat cache instead of fetching on every keypress
OLD_B3 = '''async function buscarMPIngreso(val){
  val=(val||'').trim();
  var st=document.getElementById('ing-status'),panel=document.getElementById('ing-nueva-mp-inline'),dd=document.getElementById('mp-dropdown');
  if(val.length<2){
    if(st)st.textContent='';
    ['ing-inci','ing-nombre','ing-tipo'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='';});
    if(panel)panel.style.display='none';
    if(dd)dd.style.display='none';
    return;
  }
  try{
    var r2=await fetch('/api/maestro-mps'),d2=await r2.json(),mps=d2.mps||[];
    var busq=val.toLowerCase();
    var matches=mps.filter(function(m){
      return (m.codigo_mp||'').toLowerCase().includes(busq)||(m.nombre_comercial||'').toLowerCase().includes(busq)||(m.nombre_inci||'').toLowerCase().includes(busq);
    }).slice(0,12);
    window._mpMatches=matches;
    if(dd){
      if(!matches.length){dd.style.display='none';}
      else{
        dd.style.display='block';
        dd.innerHTML=matches.map(function(m,i){return '<div class="mp-item" style="padding:9px 14px;cursor:pointer;border-bottom:1px solid #eee;font-size:0.9em;" onmousedown="seleccionarMP(_mpMatches['+i+'])">'+'<span style="font-family:monospace;color:#667eea;font-size:0.85em;">'+m.codigo_mp+'</span> &mdash; <strong>'+m.nombre_comercial+'</strong>'+(m.proveedor?' <span style="color:#888;font-size:0.82em;">('+m.proveedor+')</span>':'')+'</div>';}).join('');
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
  }catch(e){if(st){st.textContent='Error buscando';st.style.color='#c0392b';}}
}'''

NEW_B3 = '''function buscarMPIngreso(val){
  val=(val||'').trim();
  var st=document.getElementById('ing-status'),panel=document.getElementById('ing-nueva-mp-inline'),dd=document.getElementById('mp-dropdown');
  if(val.length<2){
    if(st)st.textContent='';
    ['ing-inci','ing-nombre','ing-tipo'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='';});
    if(panel)panel.style.display='none';
    if(dd)dd.style.display='none';
    return;
  }
  // Use cached catalog (_cat loaded by initIngreso) — avoids HTTP request on every keypress
  var mps=Object.values(_cat);
  var busq=val.toLowerCase();
  var matches=mps.filter(function(m){
    return (m.codigo_mp||'').toLowerCase().includes(busq)||(m.nombre_comercial||'').toLowerCase().includes(busq)||(m.nombre_inci||'').toLowerCase().includes(busq);
  }).slice(0,12);
  window._mpMatches=matches;
  if(dd){
    if(!matches.length){dd.style.display='none';}
    else{
      dd.style.display='block';
      dd.innerHTML=matches.map(function(m,i){return '<div class="mp-item" style="padding:9px 14px;cursor:pointer;border-bottom:1px solid #eee;font-size:0.9em;" onmousedown="seleccionarMP(_mpMatches['+i+'])">'+'<span style="font-family:monospace;color:#667eea;font-size:0.85em;">'+m.codigo_mp+'</span> &mdash; <strong>'+m.nombre_comercial+'</strong>'+(m.proveedor?' <span style="color:#888;font-size:0.82em;">('+m.proveedor+')</span>':'')+'</div>';}).join('');
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
}'''

assert fe.count(OLD_B3) == 1, f"B3: expected 1 match, got {fe.count(OLD_B3)}"
fe = fe.replace(OLD_B3, NEW_B3)

# B4 + B5 — Disable button during POST, re-enable on error; clear form on success
OLD_B45 = '''async function registrarIngreso(){
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
  try{
    var r=await fetch('/api/recepcion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    if(r.ok){
      _ultimoIng=res;
      document.getElementById('ing-msg').innerHTML='<div class="alert-success">'+res.message+(enCuarentena?' — CUARENTENA activa':'')+'</div>';
      await cargarHistIngreso();
      await cargarOCsPendientes();
    } else {document.getElementById('ing-msg').innerHTML='<div class="alert-error">'+(res.error||'Error')+'</div>';}
  }catch(e){document.getElementById('ing-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}'''

NEW_B45 = '''async function registrarIngreso(){
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
  // B4: disable button to prevent double-submission
  var btn=document.querySelector('button[onclick="registrarIngreso()"]');
  if(btn){btn.disabled=true;btn.textContent='Registrando...';}
  try{
    var r=await fetch('/api/recepcion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    if(r.ok){
      _ultimoIng=res;
      var ocWarn=res.oc_warning?'<br><span style="color:#e65100;font-size:0.9em;">⚠ '+res.oc_warning+'</span>':'';
      document.getElementById('ing-msg').innerHTML='<div class="alert-success">'+res.message+(enCuarentena?' — CUARENTENA activa':'')+ocWarn+'</div>';
      // B5: clear form after successful registration to prevent accidental re-submission
      limpiarIngreso();
      await cargarHistIngreso();
      await cargarOCsPendientes();
    } else {
      document.getElementById('ing-msg').innerHTML='<div class="alert-error">'+(res.error||'Error al registrar')+'</div>';
      if(btn){btn.disabled=false;btn.textContent='\\u2713 Registrar Entrada';}
    }
  }catch(e){
    document.getElementById('ing-msg').innerHTML='<div class="alert-error">Error de red: '+e.message+'</div>';
    if(btn){btn.disabled=false;btn.textContent='\\u2713 Registrar Entrada';}
  }
}'''

assert fe.count(OLD_B45) == 1, f"B45: expected 1 match, got {fe.count(OLD_B45)}"
fe = fe.replace(OLD_B45, NEW_B45)

# Verify
print(f'Frontend: B3 cache used: {"Object.values(_cat)" in fe}')
print(f'Frontend: B4 button disabled: {"btn.disabled=true" in fe}')
print(f'Frontend: B5 limpiarIngreso on success: {"limpiarIngreso();" in fe}')

with open(FRONTEND, 'w', encoding='utf-8') as f:
    f.write(fe)
print('Frontend written.\n')
print('All 5 bugs patched. Ready to verify and push.')