"""
Rebuild aprobarLib with clean modal — no inline onclick, no quote conflicts.
Both cancel and confirm use programmatic .onclick handlers.
"""

with open('/tmp/inv_p7/api/templates_py/dashboard_html.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Find the entire aprobarLib function by brace counting
idx = c.find('var _clientesLib=[];')
assert idx != -1, "aprobarLib block not found"

# Find the end: the closing } of function aprobarLib
func_idx = c.find('function aprobarLib(id){', idx)
assert func_idx != -1, "function aprobarLib not found"
depth = 0
i = func_idx
for ch in c[func_idx:]:
    if ch == '{':
        depth += 1
    elif ch == '}':
        depth -= 1
        if depth == 0:
            break
    i += 1
func_end = i + 1

OLD_BLOCK = c[idx:func_end]
print(f"Found aprobarLib block: {len(OLD_BLOCK)} chars, lines {c[:idx].count(chr(10))+1} to {c[:func_end].count(chr(10))+1}")

# Clean replacement — NO inline onclick attributes, NO quote escaping issues
# All event handlers attached programmatically after DOM creation
NEW_BLOCK = (
    'var _clientesLib=[];\n'
    'async function cargarClientesLib(){\n'
    "  try{var r=await fetch('/api/clientes');var d=await r.json();"
    "_clientesLib=(d.clientes||[]).filter(function(c){return c.activo;});}\n"
    '  catch(e){_clientesLib=[];}\n'
    '}\n'
    'function aprobarLib(id){\n'
    '  var opts=_clientesLib.map(function(c){\n'
    '    var o=document.createElement("option");\n'
    '    o.value=c.nombre; o.textContent=c.nombre; return o.outerHTML;\n'
    '  }).join("");\n'
    '  var modal=document.createElement("div");\n'
    '  modal.id="lib-modal-overlay";\n'
    '  modal.style.cssText="position:fixed;top:0;left:0;width:100%;height:100%;'
    'background:rgba(0,0,0,0.55);z-index:9999;display:flex;align-items:center;justify-content:center;";\n'
    '  modal.innerHTML=\n'
    '    \'<div style="background:#fff;border-radius:10px;padding:28px 32px;\'\n'
    '    +\'min-width:340px;max-width:460px;box-shadow:0 8px 40px rgba(0,0,0,0.18);">\'\n'
    '    +\'<h3 style="margin:0 0 18px;color:#1a2332;font-size:1.1em;">\'\n'
    '    +\'&#128666; Confirmar Liberaci\u00f3n</h3>\'\n'
    '    +\'<label style="font-size:0.85em;color:#555;display:block;margin-bottom:5px;">\'\n'
    '    +\'Cliente destino</label>\'\n'
    '    +\'<select id="lib-cli-sel" style="width:100%;padding:8px;border:1px solid #ccc;\'\n'
    '    +\'border-radius:6px;font-size:0.93em;margin-bottom:14px;">\'\n'
    '    +\'<option value="">-- Seleccionar cliente --</option>\'+opts+\'</select>\'\n'
    '    +\'<label style="font-size:0.85em;color:#555;display:block;margin-bottom:5px;">\'\n'
    '    +\'Observaciones (opcional)</label>\'\n'
    '    +\'<input id="lib-obs-inp" type="text" \'\n'
    '    +\'style="width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;\'\n'
    '    +\'font-size:0.93em;margin-bottom:20px;box-sizing:border-box;" \'\n'
    '    +\'placeholder="Ej: Conforme CC, OK BPM...">\'\n'
    '    +\'<div style="display:flex;gap:10px;justify-content:flex-end;">\'\n'
    '    +\'<button id="lib-cancel-btn" style="padding:8px 18px;border:1px solid #ccc;\'\n'
    '    +\'border-radius:6px;cursor:pointer;background:#f5f5f5;font-size:0.9em;">Cancelar</button>\'\n'
    '    +\'<button id="lib-confirm-btn" style="padding:8px 18px;background:#28a745;\'\n'
    '    +\'color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;\'\n'
    '    +\'font-size:0.9em;">&#10003; Liberar</button>\'\n'
    '    +\'</div></div>\';\n'
    '  document.body.appendChild(modal);\n'
    '  document.getElementById("lib-cancel-btn").onclick=function(){modal.remove();};\n'
    '  document.getElementById("lib-confirm-btn").onclick=function(){\n'
    '    var cli=document.getElementById("lib-cli-sel").value;\n'
    '    var obs=document.getElementById("lib-obs-inp").value;\n'
    '    modal.remove();\n'
    '    fetch("/api/liberacion/"+id,{method:"PATCH",headers:{"Content-Type":"application/json"},\n'
    '      body:JSON.stringify({estado:"Liberado",cliente:cli,observaciones:obs})})\n'
    '    .then(function(r){return r.json();})\n'
    "    .then(function(){_toast('\u2705 Liberado'+(cli?' \u2192 '+cli:''),1);loadLiberaciones('');});\n"
    '  };\n'
    '}'
)

c = c[:idx] + NEW_BLOCK + c[func_end:]

# Verify no closest() in the new block
new_section = c[idx:idx+len(NEW_BLOCK)]
if "closest(" in new_section:
    raise ValueError("closest() still in block")
if "lib-cancel-btn" not in new_section:
    raise ValueError("lib-cancel-btn missing")
if "lib-confirm-btn" not in new_section:
    raise ValueError("lib-confirm-btn missing")
print("Verification OK")

with open('/tmp/inv_p7/api/templates_py/dashboard_html.py', 'w', encoding='utf-8') as f:
    f.write(c)
print(f"dashboard_html.py written — {len(c.splitlines())} lines")
