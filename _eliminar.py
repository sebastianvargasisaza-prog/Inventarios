p = 'api/templates_py/dashboard_html.py'
a = open(p, encoding='utf-8').read()

def rep(old, new, label):
    assert a.count(old) == 1, (label, a.count(old))
    return a.replace(old, new, 1)

# 1) botón: corregir (✏️) → eliminar (🗑 · revierte MP) · título exacto
a = rep(
    'corregirCantidadFab(' + chr(39) + '+o.produccion_id+' + chr(39) + ')" title="Corregir la cantidad (revierte y re-descuenta la MP)" style="background:#ede9fe;color:#6d28d9;border:1px solid #c4b5fd;border-radius:5px;padding:4px 8px;font-size:10px;font-weight:700;cursor:pointer;margin-right:5px">&#9999;&#65039;',
    'eliminarFabVivo(' + chr(39) + '+o.produccion_id+' + chr(39) + ')" title="Eliminar esta produccion y revertir la MP - para borrar las mal registradas" style="background:#fee2e2;color:#dc2626;border:1px solid #fca5a5;border-radius:5px;padding:4px 8px;font-size:10px;font-weight:700;cursor:pointer;margin-right:5px">&#128465;',
    'btn')

# 2) función: corregirCantidadFab → eliminarFabVivo (force-delete · strings de UNA línea, sin newline)
old_fn = (
    "      window.corregirCantidadFab=async function(pid){\n"
    "        var v=prompt('Nueva cantidad en KG (ej: 80 = 80.000 g) - revierte el descuento viejo y descuenta la nueva cantidad de MP:');\n"
    "        if(v===null)return; var kg=parseFloat(v);\n"
    "        if(!(kg>0)){ alert('Cantidad invalida'); return; }\n"
    "        var t=await _csrfFab();\n"
    "        var r=await fetch('/api/programacion/programar/'+pid+'/corregir-cantidad',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify({cantidad_kg:kg})});\n"
    "        var j=await r.json();\n"
    "        if(!r.ok){ alert('Error: '+(j.error||r.status)); return; }\n"
    "        alert('Cantidad corregida a '+kg+' kg - MP ajustada.');\n"
    "        if(window.cargarEnCurso) window.cargarEnCurso();\n"
    "      };"
)
new_fn = (
    "      window.eliminarFabVivo=async function(pid){\n"
    "        if(!confirm('Eliminar esta produccion y REVERTIR el descuento de MP? Para borrar las mal registradas y volver a empezar limpio.'))return;\n"
    "        var t=await _csrfFab();\n"
    "        var r=await fetch('/api/plan/proximas/'+pid,{method:'DELETE',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify({force:true})});\n"
    "        var j=await r.json();\n"
    "        if(!r.ok){ alert('Error: '+(j.error||r.status)); return; }\n"
    "        alert('Eliminada - MP revertida al inventario.');\n"
    "        if(window.cargarEnCurso) window.cargarEnCurso();\n"
    "      };"
)
a = rep(old_fn, new_fn, 'fn')

open(p, 'w', encoding='utf-8').write(a)
print('botón 🗑 + eliminarFabVivo (limpio) · OK')
