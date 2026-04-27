#!/usr/bin/env python3
"""
FASE 1 — Bugs + Visibilidad básica
Ejecutar: python3 patch_fase1.py
Requiere: /tmp/inv_fix/api/index.py existe (el repo clonado)
"""
import sys

SRC = '/tmp/inv_fix/api/index.py'

with open(SRC, 'r', encoding='utf-8') as f:
    src = f.read()

original_len = len(src)
changes = []

# ─────────────────────────────────────────────────────────────────────────────
# F1-1: Fix generar_oc_automatica — cantidad_solicitada → cantidad_g
# ─────────────────────────────────────────────────────────────────────────────
OLD_F1_1 = (
    'c.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_solicitada, unidad) VALUES (?,?,?,?,?)",\n'
    "                      (numero_oc, item['codigo_mp'], item['nombre_mp'], item['cantidad_pedir'], 'g'))"
)
NEW_F1_1 = (
    'c.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g) VALUES (?,?,?,?)",\n'
    "                      (numero_oc, item['codigo_mp'], item['nombre_mp'], item['cantidad_pedir']))"
)
assert src.count(OLD_F1_1) == 1, f"F1-1: expected 1, got {src.count(OLD_F1_1)}"
src = src.replace(OLD_F1_1, NEW_F1_1)
changes.append("F1-1: Fix cantidad_solicitada → cantidad_g en generar_oc_automatica")

# ─────────────────────────────────────────────────────────────────────────────
# F1-2a: Fix addItemOC() — agregar nombre_mp field y botón eliminar
# ─────────────────────────────────────────────────────────────────────────────
OLD_F1_2a = (
    "function addItemOC(){\n"
    "  var div=document.createElement('div');div.className='grid3 oc-item-row';div.style.marginBottom='8px';\n"
    "  div.innerHTML='<input type=\"text\" class=\"oc-cod\" placeholder=\"MP00001\">"
    "<input type=\"number\" class=\"oc-cant\" placeholder=\"0\" step=\"0.01\">"
    "<input type=\"number\" class=\"oc-precio\" placeholder=\"0\" step=\"0.01\">';\n"
    "  document.getElementById('oc-items-list').appendChild(div);\n"
    "}"
)
NEW_F1_2a = (
    "function addItemOC(){\n"
    "  var div=document.createElement('div');div.className='oc-item-row';\n"
    "  div.style.cssText='display:grid;grid-template-columns:14% 1fr 13% 13% 5%;gap:6px;margin-bottom:6px;align-items:center;';\n"
    "  div.innerHTML=\n"
    "    '<input type=\"text\" class=\"oc-cod\" placeholder=\"Cod. MP\" style=\"font-family:monospace;\">'+\n"
    "    '<input type=\"text\" class=\"oc-nom\" placeholder=\"Descripcion del item\">'+\n"
    "    '<input type=\"number\" class=\"oc-cant\" placeholder=\"Cant.\" step=\"0.01\" min=\"0\">'+\n"
    "    '<input type=\"number\" class=\"oc-precio\" placeholder=\"Precio/g\" step=\"100\" min=\"0\">'+\n"
    "    '<button class=\"btn-del\" onclick=\"this.parentElement.remove()\" style=\"padding:4px 6px;\">&#10005;</button>';\n"
    "  document.getElementById('oc-items-list').appendChild(div);\n"
    "}"
)
assert src.count(OLD_F1_2a) == 1, f"F1-2a: expected 1, got {src.count(OLD_F1_2a)}"
src = src.replace(OLD_F1_2a, NEW_F1_2a)
changes.append("F1-2a: Fix addItemOC() — 5 columnas con nombre_mp y botón eliminar")

# ─────────────────────────────────────────────────────────────────────────────
# F1-2b: Fix crearOC() — leer nombre_mp, validar items
# ─────────────────────────────────────────────────────────────────────────────
OLD_F1_2b = (
    "async function crearOC(){\n"
    "  var items=[];\n"
    "  document.querySelectorAll('.oc-item-row').forEach(function(row){\n"
    "    var cod=row.querySelector('.oc-cod').value.trim();\n"
    "    var cant=parseFloat(row.querySelector('.oc-cant').value)||0;\n"
    "    var precio=parseFloat(row.querySelector('.oc-precio').value)||0;\n"
    "    if(cod&&cant>0) items.push({codigo_mp:cod,cantidad_g:cant,precio_unitario:precio});\n"
    "  });\n"
    "  var data={proveedor:document.getElementById('oc-prov').value,"
    "fecha_entrega_est:document.getElementById('oc-fecha-ent').value,"
    "observaciones:document.getElementById('oc-obs').value,items:items,creado_por:USUARIO};\n"
    "  try{\n"
    "    var r=await fetch('/api/ordenes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});\n"
    "    var res=await r.json();\n"
    "    if(r.ok){document.getElementById('oc-msg').innerHTML='<div class=\"msg-ok\">'+res.message+'</div>';loadOCs();}\n"
    "    else{document.getElementById('oc-msg').innerHTML='<div class=\"msg-err\">'+(res.error||'Error')+'</div>';}\n"
    "  }catch(e){document.getElementById('oc-msg').innerHTML='<div class=\"msg-err\">Error</div>';}\n"
    "}"
)
NEW_F1_2b = (
    "async function crearOC(){\n"
    "  if(!document.getElementById('oc-prov').value.trim()){alert('Ingresa el proveedor');return;}\n"
    "  var items=[];\n"
    "  document.querySelectorAll('.oc-item-row').forEach(function(row){\n"
    "    var cod=row.querySelector('.oc-cod').value.trim();\n"
    "    var nom=row.querySelector('.oc-nom')?row.querySelector('.oc-nom').value.trim():'';\n"
    "    var cant=parseFloat(row.querySelector('.oc-cant').value)||0;\n"
    "    var precio=parseFloat(row.querySelector('.oc-precio').value)||0;\n"
    "    if((cod||nom)&&cant>0) items.push({codigo_mp:cod,nombre_mp:nom,cantidad_g:cant,precio_unitario:precio});\n"
    "  });\n"
    "  if(!items.length){alert('Agrega al menos un item con cantidad');return;}\n"
    "  var data={proveedor:document.getElementById('oc-prov').value.trim(),"
    "fecha_entrega_est:document.getElementById('oc-fecha-ent').value,"
    "observaciones:document.getElementById('oc-obs').value,items:items,creado_por:USUARIO};\n"
    "  var btn=document.querySelector('#form-oc .btn');if(btn){btn.disabled=true;btn.textContent='Guardando...';}\n"
    "  try{\n"
    "    var r=await fetch('/api/ordenes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});\n"
    "    var res=await r.json();\n"
    "    if(r.ok){\n"
    "      var msg='<div class=\"msg-ok\">'+res.message+'</div>';\n"
    "      if(res.advertencia) msg+='<div style=\"background:#fef9c3;border-left:3px solid #f59e0b;padding:7px 10px;border-radius:4px;font-size:12px;margin-top:5px;\">'+res.advertencia+'</div>';\n"
    "      document.getElementById('oc-msg').innerHTML=msg;\n"
    "      document.getElementById('form-oc').style.display='none';loadOCs();loadDashboard();\n"
    "    } else {\n"
    "      document.getElementById('oc-msg').innerHTML='<div class=\"msg-err\">'+(res.error||'Error')+'</div>';\n"
    "    }\n"
    "  }catch(e){document.getElementById('oc-msg').innerHTML='<div class=\"msg-err\">Error de conexion</div>';}\n"
    "  finally{if(btn){btn.disabled=false;btn.textContent='Guardar OC';}}\n"
    "}"
)
assert src.count(OLD_F1_2b) == 1, f"F1-2b: expected 1, got {src.count(OLD_F1_2b)}"
src = src.replace(OLD_F1_2b, NEW_F1_2b)
changes.append("F1-2b: Fix crearOC() — lee nombre_mp, valida, muestra advertencia proveedor")

# ─────────────────────────────────────────────────────────────────────────────
# F1-2c: Fix form OC header — reemplazar grid3 por grid5
# ─────────────────────────────────────────────────────────────────────────────
OLD_F1_2c = (
    '      <div id="oc-items-list">\n'
    '        <div class="grid3 oc-item-row" style="font-size:11px;color:#888;margin-bottom:4px;">'
    '<span>Codigo MP</span><span>Cantidad (g)</span><span>Precio unit.</span></div>\n'
    '        <div class="grid3 oc-item-row">\n'
    '          <input type="text" class="oc-cod" placeholder="MP-00001">'
    '<input type="number" class="oc-cant" placeholder="0" step="0.01">'
    '<input type="number" class="oc-precio" placeholder="0" step="0.01">\n'
    '        </div>\n'
    '      </div>'
)
NEW_F1_2c = (
    '      <div id="oc-items-list">\n'
    '        <div style="display:grid;grid-template-columns:14% 1fr 13% 13% 5%;gap:6px;margin-bottom:4px;font-size:11px;color:#888;font-weight:600;">'
    '<span>Codigo</span><span>Descripcion *</span><span>Cantidad</span><span>Precio/g</span><span></span></div>\n'
    '        <div class="oc-item-row" style="display:grid;grid-template-columns:14% 1fr 13% 13% 5%;gap:6px;margin-bottom:6px;align-items:center;">\n'
    '          <input type="text" class="oc-cod" placeholder="Cod. MP" style="font-family:monospace;">'
    '<input type="text" class="oc-nom" placeholder="Descripcion del item">'
    '<input type="number" class="oc-cant" placeholder="0" step="0.01" min="0">'
    '<input type="number" class="oc-precio" placeholder="0" step="100" min="0">'
    '<button class="btn-del" onclick="this.parentElement.remove()" style="padding:4px 6px;">&#10005;</button>\n'
    '        </div>\n'
    '      </div>'
)
assert src.count(OLD_F1_2c) == 1, f"F1-2c: expected 1, got {src.count(OLD_F1_2c)}"
src = src.replace(OLD_F1_2c, NEW_F1_2c)
changes.append("F1-2c: Form OC HTML — 5 columnas con descripcion y botón eliminar")

# ─────────────────────────────────────────────────────────────────────────────
# F1-3a: Agregar función verOC() antes de cambiarEstadoOC()
# ─────────────────────────────────────────────────────────────────────────────
OLD_F1_3a = "async function cambiarEstadoOC(numero){"
NEW_F1_3a = (
    "async function verOC(numero){\n"
    "  openModal('modal-oc-det');\n"
    "  document.getElementById('modal-oc-det-content').innerHTML='<div style=\"padding:20px;text-align:center;color:#999;\">Cargando...</div>';\n"
    "  try{\n"
    "    var d=await fetch('/api/ordenes-compra/'+numero).then(function(r){return r.json();});\n"
    "    var oc=d.oc||{}; var items=d.items||[];\n"
    "    // oc tuple: id(0) numero_oc(1) fecha(2) estado(3) proveedor(4) valor_total(5) obs(6) creado_por(7) fecha_ent(8)\n"
    "    var h='<div style=\"display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;\">';\n"
    "    h+='<div><span style=\"font-family:monospace;font-size:18px;font-weight:800;\">'+numero+'</span></div>';\n"
    "    h+=badgeEstado(oc[3]||'')+'</div>';\n"
    "    h+='<div style=\"display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:13px;margin-bottom:14px;\">';\n"
    "    h+='<div><strong>Proveedor</strong><br>'+(oc[4]||'—')+'</div>';\n"
    "    h+='<div><strong>Fecha</strong><br>'+(oc[2]||'').substring(0,10)+'</div>';\n"
    "    h+='<div><strong>Entrega est.</strong><br>'+(oc[8]||'—')+'</div>';\n"
    "    h+='<div><strong>Creado por</strong><br>'+(oc[7]||'—')+'</div></div>';\n"
    "    if(oc[6]) h+='<div style=\"background:#fafafa;border-radius:8px;padding:9px 12px;font-size:12px;margin-bottom:14px;\">'+oc[6]+'</div>';\n"
    "    var total=0;\n"
    "    h+='<table style=\"width:100%;border-collapse:collapse;font-size:13px;\">';\n"
    "    h+='<thead><tr>';\n"
    "    h+='<th style=\"text-align:left;padding:6px 8px;background:#f5f5f5;font-size:11px;color:#888;\">Cod.</th>';\n"
    "    h+='<th style=\"text-align:left;padding:6px 8px;background:#f5f5f5;font-size:11px;color:#888;\">Descripcion</th>';\n"
    "    h+='<th style=\"text-align:right;padding:6px 8px;background:#f5f5f5;font-size:11px;color:#888;\">Cant.</th>';\n"
    "    h+='<th style=\"text-align:right;padding:6px 8px;background:#f5f5f5;font-size:11px;color:#888;\">P.Unit.</th>';\n"
    "    h+='<th style=\"text-align:right;padding:6px 8px;background:#f5f5f5;font-size:11px;color:#888;\">Subtotal</th>';\n"
    "    h+='</tr></thead><tbody>';\n"
    "    items.forEach(function(it){\n"
    "      var sub=(it[4]||0)*(it[5]||0); total+=sub;\n"
    "      h+='<tr>';\n"
    "      h+='<td style=\"padding:6px 8px;font-family:monospace;font-size:11px;color:#888;\">'+(it[2]||'—')+'</td>';\n"
    "      h+='<td style=\"padding:6px 8px;\">'+(it[3]||'—')+'</td>';\n"
    "      h+='<td style=\"padding:6px 8px;text-align:right;\">'+(it[4]||0).toLocaleString('es-CO')+' g</td>';\n"
    "      h+='<td style=\"padding:6px 8px;text-align:right;\">'+(it[5]?'$'+it[5].toLocaleString('es-CO'):'—')+'</td>';\n"
    "      h+='<td style=\"padding:6px 8px;text-align:right;font-weight:600;\">'+(sub?'$'+sub.toLocaleString('es-CO'):'—')+'</td>';\n"
    "      h+='</tr>';\n"
    "    });\n"
    "    if(!items.length) h+='<tr><td colspan=\"5\" style=\"padding:12px;text-align:center;color:#aaa;\">Sin items registrados</td></tr>';\n"
    "    h+='</tbody>';\n"
    "    if(total>0) h+='<tfoot><tr><td colspan=\"4\" style=\"padding:8px;text-align:right;font-weight:700;border-top:2px solid #eee;\">TOTAL ESTIMADO</td><td style=\"padding:8px;text-align:right;font-weight:900;font-size:16px;color:#2B7A78;border-top:2px solid #eee;\">$'+total.toLocaleString('es-CO')+'</td></tr></tfoot>';\n"
    "    h+='</table>';\n"
    "    h+='<div style=\"margin-top:16px;display:flex;gap:8px;justify-content:flex-end;\">';\n"
    "    h+='<button class=\"btn btn-ghost\" onclick=\"window.open(\\'/compras/oc/'+numero+'/print\\',\\'_blank\\')\">Imprimir / PDF</button>';\n"
    "    h+='<button class=\"btn btn-ghost\" onclick=\"cambiarEstadoOC(\\''+numero+'\\')\" >Cambiar estado</button>';\n"
    "    h+='</div>';\n"
    "    document.getElementById('modal-oc-det-content').innerHTML=h;\n"
    "  }catch(e){\n"
    "    document.getElementById('modal-oc-det-content').innerHTML='<div style=\"color:#dc2626;padding:16px;\">Error al cargar</div>';\n"
    "  }\n"
    "}\n"
    "async function cambiarEstadoOC(numero){"
)
assert src.count(OLD_F1_3a) == 1, f"F1-3a: expected 1, got {src.count(OLD_F1_3a)}"
src = src.replace(OLD_F1_3a, NEW_F1_3a)
changes.append("F1-3a: Agregar función verOC() con modal de detalle")

# ─────────────────────────────────────────────────────────────────────────────
# F1-3b: Agregar modal-oc-det HTML justo antes del modal-sol
# ─────────────────────────────────────────────────────────────────────────────
OLD_F1_3b = "<!-- Modal Solicitud -->"
NEW_F1_3b = (
    '<!-- Modal OC Detalle -->\n'
    '<div id="modal-oc-det" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:2000;align-items:flex-start;justify-content:center;padding-top:60px;">\n'
    '  <div style="background:#fff;border-radius:14px;padding:28px 32px;max-width:700px;width:94%;max-height:80vh;overflow-y:auto;position:relative;box-shadow:0 20px 60px rgba(0,0,0,.2);">\n'
    '    <button onclick="closeModal(\'modal-oc-det\')" style="position:absolute;top:14px;right:16px;background:none;border:none;font-size:22px;cursor:pointer;color:#bbb;">&#x2715;</button>\n'
    '    <div id="modal-oc-det-content">Cargando...</div>\n'
    '  </div>\n'
    '</div>\n\n'
    '<!-- Modal Solicitud -->'
)
assert src.count(OLD_F1_3b) == 1, f"F1-3b: expected 1, got {src.count(OLD_F1_3b)}"
src = src.replace(OLD_F1_3b, NEW_F1_3b)
changes.append("F1-3b: Agregar modal-oc-det HTML")

# ─────────────────────────────────────────────────────────────────────────────
# F1-3c: Agregar botón "Ver" en loadOCs() + columna Valor
# ─────────────────────────────────────────────────────────────────────────────
OLD_F1_3c = (
    "      return '<tr><td style=\"font-family:monospace;font-weight:600;\">'+o.numero_oc+'</td>"
    "<td>'+o.proveedor+'</td><td>'+o.fecha.substring(0,10)+'</td>"
    "<td>'+(o.fecha_entrega_est||'—')+'</td><td>'+badgeEstado(o.estado)+'</td>"
    "<td style=\"text-align:center;\">'+(o.num_items||0)+'</td>"
    "<td><button class=\"btn btn-ghost btn-sm\" onclick=\"cambiarEstadoOC(&quot;'+o.numero_oc+'&quot;)\" >Estado</button>'+bR+'</td></tr>';"
)
NEW_F1_3c = (
    "      var valStr=o.valor_total>0?'$'+parseFloat(o.valor_total).toLocaleString('es-CO'):'—';\n"
    "      return '<tr><td style=\"font-family:monospace;font-weight:600;\">'+o.numero_oc+'</td>"
    "<td>'+o.proveedor+'</td><td>'+o.fecha.substring(0,10)+'</td>"
    "<td>'+(o.fecha_entrega_est||'—')+'</td><td>'+badgeEstado(o.estado)+'</td>"
    "<td style=\"text-align:center;\">'+(o.num_items||0)+'</td>"
    "<td style=\"text-align:right;font-size:12px;color:#2B7A78;font-weight:600;\">'+valStr+'</td>"
    "<td><button class=\"btn btn-ghost btn-sm\" onclick=\"verOC(&quot;'+o.numero_oc+'&quot;)\" >Ver</button> "
    "<button class=\"btn btn-ghost btn-sm\" onclick=\"cambiarEstadoOC(&quot;'+o.numero_oc+'&quot;)\" >Estado</button>'+bR+'</td></tr>';"
)
assert src.count(OLD_F1_3c) == 1, f"F1-3c: expected 1, got {src.count(OLD_F1_3c)}"
src = src.replace(OLD_F1_3c, NEW_F1_3c)
changes.append("F1-3c: loadOCs() — botón Ver y columna Valor")

# ─────────────────────────────────────────────────────────────────────────────
# F1-3d: Agregar columna Valor en header de tabla OCs
# ─────────────────────────────────────────────────────────────────────────────
OLD_F1_3d = (
    '    <table class="tbl"><thead><tr>'
    '<th>Numero OC</th><th>Proveedor</th><th>Fecha</th>'
    '<th>Entrega est.</th><th>Estado</th><th>Items</th><th>Acciones</th>'
    '</tr></thead>'
)
NEW_F1_3d = (
    '    <table class="tbl"><thead><tr>'
    '<th>Numero OC</th><th>Proveedor</th><th>Fecha</th>'
    '<th>Entrega est.</th><th>Estado</th><th>Items</th><th style="text-align:right;">Valor est.</th><th>Acciones</th>'
    '</tr></thead>'
)
assert src.count(OLD_F1_3d) == 1, f"F1-3d: expected 1, got {src.count(OLD_F1_3d)}"
src = src.replace(OLD_F1_3d, NEW_F1_3d)
changes.append("F1-3d: Tabla OCs — columna Valor est.")

# ─────────────────────────────────────────────────────────────────────────────
# F1-3e: Agregar closeModal en keydown para modal-oc-det
# ─────────────────────────────────────────────────────────────────────────────
OLD_F1_3e = "document.addEventListener('keydown',function(e){if(e.key==='Escape'){closeModal('modal-sol');closeModal('modal-oc-estado');}});"
NEW_F1_3e = "document.addEventListener('keydown',function(e){if(e.key==='Escape'){closeModal('modal-sol');closeModal('modal-oc-estado');closeModal('modal-oc-det');}});"
assert src.count(OLD_F1_3e) == 1, f"F1-3e: expected 1, got {src.count(OLD_F1_3e)}"
src = src.replace(OLD_F1_3e, NEW_F1_3e)
changes.append("F1-3e: Esc cierra modal-oc-det también")

# ─────────────────────────────────────────────────────────────────────────────
# F1-4a: Backend — GET /api/solicitudes-compra con valor_total por solicitud
# ─────────────────────────────────────────────────────────────────────────────
OLD_F1_4a = (
    '    filtro_estado = request.args.get(\'estado\', \'\')\n'
    '    filtro_empresa = request.args.get(\'empresa\', \'\')\n'
    '    sql = "SELECT numero,fecha,estado,solicitante,urgencia,observaciones,empresa,categoria,tipo,area FROM solicitudes_compra WHERE 1=1"\n'
    '    params = []\n'
    '    if filtro_estado: sql += " AND estado=?"; params.append(filtro_estado)\n'
    '    if filtro_empresa: sql += " AND empresa=?"; params.append(filtro_empresa)\n'
    '    sql += " ORDER BY fecha DESC LIMIT 200"\n'
    '    c.execute(sql, params)\n'
    "    cols_sol = ['numero','fecha','estado','solicitante','urgencia','observaciones','empresa','categoria','tipo','area']"
)
NEW_F1_4a = (
    '    filtro_estado = request.args.get(\'estado\', \'\')\n'
    '    filtro_empresa = request.args.get(\'empresa\', \'\')\n'
    '    sql = """SELECT s.numero,s.fecha,s.estado,s.solicitante,s.urgencia,s.observaciones,\n'
    '                    s.empresa,s.categoria,s.tipo,s.area,\n'
    '                    COALESCE(SUM(si.valor_estimado),0) as valor_total\n'
    '             FROM solicitudes_compra s\n'
    '             LEFT JOIN solicitudes_compra_items si ON s.numero=si.numero\n'
    '             WHERE 1=1"""\n'
    '    params = []\n'
    '    if filtro_estado: sql += " AND s.estado=?"; params.append(filtro_estado)\n'
    '    if filtro_empresa: sql += " AND s.empresa=?"; params.append(filtro_empresa)\n'
    '    sql += " GROUP BY s.numero ORDER BY s.fecha DESC LIMIT 200"\n'
    '    c.execute(sql, params)\n'
    "    cols_sol = ['numero','fecha','estado','solicitante','urgencia','observaciones','empresa','categoria','tipo','area','valor_total']"
)
assert src.count(OLD_F1_4a) == 1, f"F1-4a: expected 1, got {src.count(OLD_F1_4a)}"
src = src.replace(OLD_F1_4a, NEW_F1_4a)
changes.append("F1-4a: GET /api/solicitudes-compra — incluye valor_total por solicitud")

# ─────────────────────────────────────────────────────────────────────────────
# F1-4b: Frontend — tabla solicitudes muestra categoría y valor
# ─────────────────────────────────────────────────────────────────────────────
# Header: agregar columna Cat./Valor
OLD_F1_4b_hdr = (
    '    <table class="tbl"><thead><tr>'
    '<th>Numero</th><th>Solicitante</th><th>Fecha</th>'
    '<th>Urgencia</th><th>Estado</th><th>Acciones</th>'
    '</tr></thead>'
)
NEW_F1_4b_hdr = (
    '    <table class="tbl"><thead><tr>'
    '<th>Numero</th><th>Solicitante / Area</th><th>Fecha</th>'
    '<th>Cat. / Valor</th><th>Urgencia</th><th>Estado</th><th>Empresa</th><th>Acciones</th>'
    '</tr></thead>'
)
assert src.count(OLD_F1_4b_hdr) == 1, f"F1-4b hdr: expected 1, got {src.count(OLD_F1_4b_hdr)}"
src = src.replace(OLD_F1_4b_hdr, NEW_F1_4b_hdr)
changes.append("F1-4b: Header tabla solicitudes — columnas mejoradas")

# Row: mostrar categoría y valor
OLD_F1_4b_row = (
    "      var eBadge=s.empresa&&s.empresa.indexOf('ANIMUS')>=0?"
    "'<span style=\"display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;background:#f3e8ff;color:#7A4A8B;font-weight:600;margin-right:4px;\">AN</span>'"
    ":'<span style=\"display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;background:#e8f4f0;color:#2B7A78;font-weight:600;margin-right:4px;\">ESP</span>';\n"
    "      var acc='<button class=\"btn btn-ghost btn-sm\" onclick=\"verSolicitud(&quot;'+s.numero+'&quot;)\" >Ver</button>';\n"
    "      if(s.estado==='Pendiente') acc+=' <button class=\"btn btn-sm\" style=\"font-size:11px;\" onclick=\"verSolicitud(&quot;'+s.numero+'&quot;,true)\">Gestionar</button>';\n"
    "      return '<tr><td style=\"font-family:monospace;font-weight:600;\">'+s.numero+'</td>"
    "<td>'+s.solicitante+'</td><td>'+s.fecha.substring(0,10)+'</td>"
    "<td>'+badgeEstado(s.urgencia)+'</td><td>'+badgeEstado(s.estado)+'</td>"
    "<td>'+eBadge+acc+'</td></tr>';"
)
NEW_F1_4b_row = (
    "      var eBadge=s.empresa&&s.empresa.indexOf('ANIMUS')>=0?\n"
    "        '<span style=\"display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;background:#f3e8ff;color:#7A4A8B;font-weight:600;\">AN</span>':\n"
    "        '<span style=\"display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;background:#e8f4f0;color:#2B7A78;font-weight:600;\">ESP</span>';\n"
    "      var catStr=s.categoria?'<span style=\"font-size:11px;color:#555;\">'+s.categoria+'</span>':'';\n"
    "      var valStr=s.valor_total>0?'<br><span style=\"font-size:11px;font-weight:700;color:#2B7A78;\">$'+parseFloat(s.valor_total).toLocaleString('es-CO')+'</span>':'';\n"
    "      var acc='<button class=\"btn btn-ghost btn-sm\" onclick=\"verSolicitud(&quot;'+s.numero+'&quot;)\" >Ver</button>';\n"
    "      if(s.estado==='Pendiente') acc+=' <button class=\"btn btn-sm\" style=\"font-size:11px;\" onclick=\"verSolicitud(&quot;'+s.numero+'&quot;,true)\">Gestionar</button>';\n"
    "      return '<tr>'\n"
    "        +'<td style=\"font-family:monospace;font-weight:600;\">'+s.numero+'</td>'\n"
    "        +'<td>'+s.solicitante+'<br><span style=\"font-size:11px;color:#aaa;\">'+(s.area||'')+'</span></td>'\n"
    "        +'<td>'+s.fecha.substring(0,10)+'</td>'\n"
    "        +'<td>'+catStr+valStr+'</td>'\n"
    "        +'<td>'+badgeEstado(s.urgencia)+'</td>'\n"
    "        +'<td>'+badgeEstado(s.estado)+'</td>'\n"
    "        +'<td>'+eBadge+'</td>'\n"
    "        +'<td>'+acc+'</td></tr>';"
)
assert src.count(OLD_F1_4b_row) == 1, f"F1-4b row: expected 1, got {src.count(OLD_F1_4b_row)}"
src = src.replace(OLD_F1_4b_row, NEW_F1_4b_row)
changes.append("F1-4b: Filas tabla solicitudes — categoría, valor, área separados")

# ─────────────────────────────────────────────────────────────────────────────
# F1-5: Backend — calcular valor_total al crear OC
# ─────────────────────────────────────────────────────────────────────────────
OLD_F1_5 = (
    "        for it in (d.get('items') or []):\n"
    "            subtotal = round((it.get('cantidad_g',0)) * (it.get('precio_unitario',0)), 2)\n"
    "            c.execute(\"INSERT INTO ordenes_compra_items (numero_oc,codigo_mp,nombre_mp,cantidad_g,precio_unitario,subtotal) VALUES (?,?,?,?,?,?)\",\n"
    "                      (numero_oc, it.get('codigo_mp',''), it.get('nombre_mp',''),\n"
    "                       it.get('cantidad_g',0), it.get('precio_unitario',0), subtotal))\n"
    "        conn.commit(); conn.close()\n"
    "        return jsonify({'message': f'OC {numero_oc} creada', 'numero_oc': numero_oc}), 201"
)
NEW_F1_5 = (
    "        valor_total = 0\n"
    "        for it in (d.get('items') or []):\n"
    "            subtotal = round((it.get('cantidad_g',0)) * (it.get('precio_unitario',0)), 2)\n"
    "            valor_total += subtotal\n"
    "            c.execute(\"INSERT INTO ordenes_compra_items (numero_oc,codigo_mp,nombre_mp,cantidad_g,precio_unitario,subtotal) VALUES (?,?,?,?,?,?)\",\n"
    "                      (numero_oc, it.get('codigo_mp',''), it.get('nombre_mp',''),\n"
    "                       it.get('cantidad_g',0), it.get('precio_unitario',0), subtotal))\n"
    "        if valor_total > 0:\n"
    "            c.execute(\"UPDATE ordenes_compra SET valor_total=? WHERE numero_oc=?\", (round(valor_total,2), numero_oc))\n"
    "        # Advertencia si proveedor no está calificado\n"
    "        prov_nombre_oc = d['proveedor']\n"
    "        c.execute(\"SELECT estado_calificacion FROM proveedores WHERE nombre=?\", (prov_nombre_oc,))\n"
    "        prov_row = c.fetchone()\n"
    "        advertencia = ''\n"
    "        if prov_row and prov_row[0] == 'Suspendido':\n"
    "            conn.close(); return jsonify({'error': f'Proveedor {prov_nombre_oc} esta SUSPENDIDO. No se puede crear OC.'}), 400\n"
    "        if not prov_row or (prov_row[0] if prov_row else '') == 'En evaluacion':\n"
    "            advertencia = f'{prov_nombre_oc} esta en evaluacion o no registrado como proveedor calificado.'\n"
    "        conn.commit(); conn.close()\n"
    "        return jsonify({'message': f'OC {numero_oc} creada', 'numero_oc': numero_oc, 'advertencia': advertencia}), 201"
)
assert src.count(OLD_F1_5) == 1, f"F1-5: expected 1, got {src.count(OLD_F1_5)}"
src = src.replace(OLD_F1_5, NEW_F1_5)
changes.append("F1-5: Backend POST OC — calcula valor_total y verifica calificación proveedor")

# ─────────────────────────────────────────────────────────────────────────────
# Escribir resultado
# ─────────────────────────────────────────────────────────────────────────────
with open(SRC, 'w', encoding='utf-8') as f:
    f.write(src)

print(f"\n{'='*60}")
print(f"FASE 1 — {len(changes)} cambios aplicados")
print(f"Lineas: {original_len} → {len(src)} chars")
print(f"{'='*60}")
for i, c in enumerate(changes, 1):
    print(f"  {i:2d}. {c}")
print(f"\nArchivo: {SRC}")
print("Siguiente: node --check, luego git commit + push")
