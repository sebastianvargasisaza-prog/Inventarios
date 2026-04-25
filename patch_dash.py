"""Patch dashboard_html.py — switchTab + aprobarLib modal"""
SRC = '/tmp/inv_p7'

with open(f'{SRC}/api/templates_py/dashboard_html.py', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. switchTab
OLD1 = "if(n==='liberacion') loadLiberaciones('');"
NEW1 = "if(n==='liberacion'){loadLiberaciones('');cargarClientesLib();}"
if OLD1 not in c:
    print("WARN: switchTab anchor not found")
else:
    c = c.replace(OLD1, NEW1, 1)
    print("switchTab OK")

# 2. Find aprobarLib by dynamic search (avoids quote escaping issues)
idx = c.find('function aprobarLib(id){')
if idx == -1:
    idx = c.find('function aprobarLib(id) {')
assert idx != -1, "aprobarLib not found"
depth = 0
i = idx
for ch in c[idx:]:
    if ch == '{':
        depth += 1
    elif ch == '}':
        depth -= 1
        if depth == 0:
            break
    i += 1
OLD2 = c[idx:i+1]
print(f"Found aprobarLib ({len(OLD2)} chars)")

NEW2 = (
    'var _clientesLib=[];\n'
    'async function cargarClientesLib(){\n'
    "  try{var r=await fetch('/api/clientes');var d=await r.json();"
    "_clientesLib=(d.clientes||[]).filter(function(c){return c.activo;});}\n"
    '  catch(e){_clientesLib=[];}\n'
    '}\n'
    'function aprobarLib(id){\n'
    "  var opts=_clientesLib.map(function(c){"
    "return '<option value=\"'+c.nombre+'\">'+c.nombre+'</option>';}).join('');\n"
    "  var modal=document.createElement('div');\n"
    "  modal.style.cssText='position:fixed;top:0;left:0;width:100%;height:100%;"
    "background:rgba(0,0,0,0.55);z-index:9999;display:flex;align-items:center;justify-content:center;';\n"
    "  modal.innerHTML="
    "'<div style=\"background:#fff;border-radius:10px;padding:28px 32px;"
    "min-width:340px;max-width:460px;box-shadow:0 8px 40px rgba(0,0,0,0.18);\">'\n"
    "    +'<h3 style=\"margin:0 0 18px;color:#1a2332;font-size:1.1em;\">"
    "&#128666; Confirmar Liberaci\u00f3n</h3>'\n"
    "    +'<label style=\"font-size:0.85em;color:#555;display:block;margin-bottom:5px;\">"
    "Cliente destino</label>'\n"
    "    +'<select id=\"lib-cli-sel\" style=\"width:100%;padding:8px;border:1px solid #ccc;"
    "border-radius:6px;font-size:0.93em;margin-bottom:14px;\">'\n"
    "    +'<option value=\"\">-- Seleccionar cliente --</option>'+opts\n"
    "    +'</select>'\n"
    "    +'<label style=\"font-size:0.85em;color:#555;display:block;margin-bottom:5px;\">"
    "Observaciones (opcional)</label>'\n"
    "    +'<input id=\"lib-obs-inp\" type=\"text\" style=\"width:100%;padding:8px;"
    "border:1px solid #ccc;border-radius:6px;font-size:0.93em;margin-bottom:20px;"
    "box-sizing:border-box;\" placeholder=\"Ej: Conforme CC, OK BPM...\">'\n"
    "    +'<div style=\"display:flex;gap:10px;justify-content:flex-end;\">'\n"
    "    +'<button onclick=\"this.closest(\\'div\\').parentElement.remove()\" "
    "style=\"padding:8px 18px;border:1px solid #ccc;border-radius:6px;cursor:pointer;"
    "background:#f5f5f5;font-size:0.9em;\">Cancelar</button>'\n"
    "    +'<button id=\"lib-confirm-btn\" style=\"padding:8px 18px;background:#28a745;"
    "color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;"
    "font-size:0.9em;\">&#10003; Liberar</button>'\n"
    "    +'</div></div>';\n"
    '  document.body.appendChild(modal);\n'
    "  document.getElementById('lib-confirm-btn').onclick=function(){\n"
    "    var cli=document.getElementById('lib-cli-sel').value;\n"
    "    var obs=document.getElementById('lib-obs-inp').value;\n"
    '    modal.remove();\n'
    '    fetch("/api/liberacion/"+id,{method:"PATCH",'
    'headers:{"Content-Type":"application/json"},\n'
    '      body:JSON.stringify({estado:"Liberado",cliente:cli,observaciones:obs})})\n'
    '    .then(function(r){return r.json();})\n'
    "    .then(function(){_toast('\u2705 Liberado'+(cli?' \u2192 '+cli:''),1);"
    "loadLiberaciones('');});\n"
    '  };\n'
    '}'
)

c = c.replace(OLD2, NEW2, 1)
print("aprobarLib modal OK")

# Verify
assert 'cargarClientesLib' in c, "cargarClientesLib missing after patch"
assert 'lib-cli-sel' in c, "lib-cli-sel missing after patch"

with open(f'{SRC}/api/templates_py/dashboard_html.py', 'w', encoding='utf-8') as f:
    f.write(c)
print(f"dashboard_html.py done — {len(c.splitlines())} lines")
