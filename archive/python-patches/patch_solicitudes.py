# patch_solicitudes.py — fixes en solicitudes_html.py
# 1. Handle guardado en obs
# 2. Double-submit fix: id btn-enviar-pago + disable correcto
# 3. nuevaSolicitud() resetea tipo correctamente
# 4. Handle oculto para Servicios Profesionales
# 5. Re-enable en caso de error cubre ambos botones

TARGET = '/tmp/inv_p9/api/templates_py/solicitudes_html.py'

with open(TARGET, 'r') as f:
    h = f.read()

# ================================================================
# FIX 1: Dar id al botón de pago (para poder referenciarlo)
# ================================================================
OLD1 = '<button class="btn-primary" onclick="enviarSolicitud()">Enviar Solicitud de Pago</button>'
NEW1 = '<button class="btn-primary" id="btn-enviar-pago" onclick="enviarSolicitud()">Enviar Solicitud de Pago</button>'
assert OLD1 in h, "FIX1 anchor not found"
h = h.replace(OLD1, NEW1, 1)
print("FIX1 OK - id en boton pago")

# ================================================================
# FIX 2: Handle oculto para Servicios Profesionales — label + input
# wrapeados en div con id para show/hide
# ================================================================
OLD2 = (
    '        <div class="field"><label>Red social / Handle</label>\n'
    '          <input type="text" id="p-handle" placeholder="@usuario o N/A"></div>\n'
)
NEW2 = (
    '        <div class="field" id="p-handle-box"><label>Red social / Handle</label>\n'
    '          <input type="text" id="p-handle" placeholder="@usuario"></div>\n'
)
assert OLD2 in h, "FIX2 anchor not found"
h = h.replace(OLD2, NEW2, 1)
print("FIX2 OK - handle box con id")

# ================================================================
# FIX 3: onCatChange — mostrar handle solo para Influencer,
#         ocultar para Servicios Profesionales
# ================================================================
OLD3 = (
    'function onCatChange(){\n'
    '  var cat=document.getElementById(\'f-cat\').value;\n'
    '  var esPago=PAGO_CATS.indexOf(cat)>=0;\n'
    '  document.getElementById(\'items-section\').style.display=esPago?\'none\':\'block\';\n'
    '  document.getElementById(\'pago-section\').style.display=esPago?\'block\':\'none\';\n'
    '  if(esPago)setTipo(\'Pago\');else setTipo(\'Compra\');\n'
    '  if(!esPago){\n'
    '    var rows=document.getElementById(\'items-body\').children;\n'
    '    for(var i=0;i<rows.length;i++){\n'
    '      var rid=rows[i].id.replace(\'ir-\',\'\');\n'
    '      var sel=document.getElementById(\'i\'+rid+\'-uni\');\n'
    '      if(sel){var cur=sel.value;sel.outerHTML=buildUniSelect(\'i\'+rid+\'-uni\',cur);}\n'
    '    }\n'
    '  }\n'
    '}'
)
NEW3 = (
    'function onCatChange(){\n'
    '  var cat=document.getElementById(\'f-cat\').value;\n'
    '  var esPago=PAGO_CATS.indexOf(cat)>=0;\n'
    '  var esInfl=cat===\'Influencer/Marketing Digital\';\n'
    '  document.getElementById(\'items-section\').style.display=esPago?\'none\':\'block\';\n'
    '  document.getElementById(\'pago-section\').style.display=esPago?\'block\':\'none\';\n'
    '  var hbox=document.getElementById(\'p-handle-box\');\n'
    '  if(hbox) hbox.style.display=esInfl?\'block\':\'none\';\n'
    '  if(esPago)setTipo(\'Pago\');else setTipo(\'Compra\');\n'
    '  if(!esPago){\n'
    '    var rows=document.getElementById(\'items-body\').children;\n'
    '    for(var i=0;i<rows.length;i++){\n'
    '      var rid=rows[i].id.replace(\'ir-\',\'\');\n'
    '      var sel=document.getElementById(\'i\'+rid+\'-uni\');\n'
    '      if(sel){var cur=sel.value;sel.outerHTML=buildUniSelect(\'i\'+rid+\'-uni\',cur);}\n'
    '    }\n'
    '  }\n'
    '}'
)
assert OLD3 in h, "FIX3 anchor not found"
h = h.replace(OLD3, NEW3, 1)
print("FIX3 OK - handle visibility por categoria")

# ================================================================
# FIX 4: enviarSolicitud() — handle guardado + double-submit fix
#         Reemplazar el bloque de construccion del obsStr y el btn
# ================================================================
OLD4 = (
    '    var handle=document.getElementById(\'p-handle\').value.trim();\n'
    '    var banco=document.getElementById(\'p-banco\').value;\n'
    '    var tipoCta=document.getElementById(\'p-tipo-cta\').value;\n'
    '    var numcta=document.getElementById(\'p-numcta\').value.trim();\n'
    '    var cedula=document.getElementById(\'p-cedula\').value.trim();\n'
    '    var valor=parseFloat(document.getElementById(\'p-valor\').value)||0;\n'
    '    var desc=document.getElementById(\'p-desc\').value.trim();\n'
    '    var obsExtra=document.getElementById(\'p-obs\').value.trim();\n'
    '    if(!nombre){alert(\'Ingresa el nombre del beneficiario\');return;}\n'
    '    if(!banco){alert(\'Selecciona el banco\');return;}\n'
    '    if(!numcta){alert(\'Ingresa el numero de cuenta o celular\');return;}\n'
    '    if(!valor){alert(\'Ingresa el valor a pagar\');return;}\n'
    '    if(!desc){alert(\'Ingresa una descripcion del servicio\');return;}\n'
    '    var obsStr=\'BENEFICIARIO: \'+nombre+\' | BANCO: \'+banco+\' \'+tipoCta+\' | CUENTA/CEL: \'+numcta+(cedula?\' | CED/NIT: \'+cedula:\'\')+\' | VALOR: $\'+valor+\' | SERVICIO: \'+desc+(obsExtra?\' | \'+obsExtra:\'\');\n'
)
# This exact string may have slightly different quoting — let me check what's in the file
NEW4 = (
    '    var handle=document.getElementById(\'p-handle\').value.trim();\n'
    '    var banco=document.getElementById(\'p-banco\').value;\n'
    '    var tipoCta=document.getElementById(\'p-tipo-cta\').value;\n'
    '    var numcta=document.getElementById(\'p-numcta\').value.trim();\n'
    '    var cedula=document.getElementById(\'p-cedula\').value.trim();\n'
    '    var valor=parseFloat(document.getElementById(\'p-valor\').value)||0;\n'
    '    var desc=document.getElementById(\'p-desc\').value.trim();\n'
    '    var obsExtra=document.getElementById(\'p-obs\').value.trim();\n'
    '    if(!nombre){alert(\'Ingresa el nombre del beneficiario\');return;}\n'
    '    if(!banco){alert(\'Selecciona el banco\');return;}\n'
    '    if(!numcta){alert(\'Ingresa el numero de cuenta o celular\');return;}\n'
    '    if(!valor){alert(\'Ingresa el valor a pagar\');return;}\n'
    '    if(!desc){alert(\'Ingresa una descripcion del servicio\');return;}\n'
    '    var obsStr=\'BENEFICIARIO: \'+nombre+(handle?\' | HANDLE: \'+handle:\'\')+\' | BANCO: \'+banco+\' \'+tipoCta+\' | CUENTA/CEL: \'+numcta+(cedula?\' | CED/NIT: \'+cedula:\'\')+\' | VALOR: $\'+valor+\' | SERVICIO: \'+desc+(obsExtra?\' | \'+obsExtra:\'\');\n'
)

# Check actual content
if OLD4 not in h:
    # Find the actual string in the file for this section
    idx = h.find("var obsStr='BENEFICIARIO: '")
    if idx > 0:
        print("obsStr line (actual):", repr(h[idx:idx+200]))
    else:
        print("FIX4: obsStr not found — searching for handle line...")
        idx2 = h.find("p-handle")
        print("p-handle context:", repr(h[max(0,idx2-50):idx2+100]))
    print("FIX4 SKIPPED - will search manually")
else:
    h = h.replace(OLD4, NEW4, 1)
    print("FIX4 OK - handle en obsStr")

# ================================================================
# FIX 5: btn disable — usar ids especificos para cada seccion
# ================================================================
OLD5 = (
    '  var btn=document.querySelector(\'#btn-enviar,#pago-section .btn-primary\');\n'
    '  if(btn){btn.disabled=true;btn.textContent=\'Enviando...\';}\n'
)
NEW5 = (
    '  var btn=esPago ? document.getElementById(\'btn-enviar-pago\') : document.getElementById(\'btn-enviar\');\n'
    '  if(btn){btn.disabled=true;btn.textContent=\'Enviando...\';}\n'
)
assert OLD5 in h, "FIX5 anchor not found"
h = h.replace(OLD5, NEW5, 1)
print("FIX5 OK - btn disable por seccion")

# ================================================================
# FIX 6: re-enable en caso de error — cubrir ambos botones
# ================================================================
OLD6 = "if(d.numero){\n      document.getElementById('confirm-num').textContent=d.numero;\n      document.getElementById('form-card').style.display='none';\n      document.getElementById('confirm-card').style.display='block';\n      window.scrollTo(0,0);\n    }else{alert('Error: '+(d.error||'Intenta de nuevo'));if(btn){btn.disabled=false;btn.textContent='Enviar Solicitud';}}\n  }catch(e){alert('Error de conexion.');if(btn){btn.disabled=false;btn.textContent='Enviar Solicitud';}}"
NEW6 = "if(d.numero){\n      document.getElementById('confirm-num').textContent=d.numero;\n      document.getElementById('form-card').style.display='none';\n      document.getElementById('confirm-card').style.display='block';\n      window.scrollTo(0,0);\n    }else{\n      alert('Error: '+(d.error||'Intenta de nuevo'));\n      if(btn){btn.disabled=false;btn.textContent=esPago?'Enviar Solicitud de Pago':'Enviar Solicitud';}\n    }\n  }catch(e){\n    alert('Error de conexion.');\n    if(btn){btn.disabled=false;btn.textContent=esPago?'Enviar Solicitud de Pago':'Enviar Solicitud';}\n  }"

if OLD6 not in h:
    print("FIX6 SKIPPED - anchor not found (will patch manually)")
else:
    h = h.replace(OLD6, NEW6, 1)
    print("FIX6 OK - re-enable error texto correcto")

# ================================================================
# FIX 7: nuevaSolicitud() — resetear tipo variable + visual
# ================================================================
OLD7 = "  itemCount=1;urg='Normal';setUrg('Normal',document.getElementById('ub-n'));\n  var eb=document.getElementById('btn-enviar');if(eb){eb.disabled=false;eb.textContent='Enviar Solicitud';}"
NEW7 = "  itemCount=1;urg='Normal';tipo='Compra';setUrg('Normal',document.getElementById('ub-n'));setTipo('Compra');\n  var eb=document.getElementById('btn-enviar');if(eb){eb.disabled=false;eb.textContent='Enviar Solicitud';}\n  var ep=document.getElementById('btn-enviar-pago');if(ep){ep.disabled=false;ep.textContent='Enviar Solicitud de Pago';}\n  var hbox=document.getElementById('p-handle-box');if(hbox)hbox.style.display='none';"
assert OLD7 in h, "FIX7 anchor not found"
h = h.replace(OLD7, NEW7, 1)
print("FIX7 OK - nuevaSolicitud reset tipo + btn-pago")

with open(TARGET, 'w') as f:
    f.write(h)
print("\nAll fixes written.")
