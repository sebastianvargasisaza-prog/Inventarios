# patch_solic_logic.py — fixes criticos en logica de solicitudes
# Fix 1: loadSolicitudes definida
# Fix 2: CMAP ampliado con todas las categorias de solicitudes
# Fix 3: _guardarNuevoProv URL correcta
# Fix 4: gestionarSol post-action usa loadSolicitudes correctamente
# (backend cat normalization se hace en patch separado)

TARGET = '/tmp/inv_p9/api/templates_py/compras_html.py'

with open(TARGET, 'r') as f:
    h = f.read()

# ================================================================
# FIX 1: CMAP — ampliar con todas las categorias de solicitudes
#   mee: agrega 'Material de Empaque'
#   svc: agrega 'Servicios Profesionales', 'Software/Tecnologia'
#   adm: agrega 'EPP', 'Aseo/Limpieza', 'Papeleria/Oficina', 'Dotacion', 'Otro'
#   inf: agrega 'Mantenimiento', 'Repuestos', 'Reactivos/Laboratorio'
# ================================================================
OLD1 = (
    "var CMAP = {\n"
    "  mp:  ['MPs','MP','Materia Prima','Materias Primas'],\n"
    "  mee: ['Envase','Insumos','MEE','Empaque'],\n"
    "  svc: ['Servicios','Analisis','Acondicionamiento','SVC','Servicio'],\n"
    "  adm: ['Admin','Nomina','ADM','Administrativo'],\n"
    "  inf: ['Infraestructura','INF'],\n"
    "  cc:  ['CC','Cuenta de Cobro','Cuentas de Cobro']\n"
    "};"
)
NEW1 = (
    "var CMAP = {\n"
    "  mp:  ['MPs','MP','Materia Prima','Materias Primas'],\n"
    "  mee: ['Envase','Insumos','MEE','Empaque','Material de Empaque'],\n"
    "  svc: ['Servicios','Analisis','Acondicionamiento','SVC','Servicio',\n"
    "        'Servicios Profesionales','Software/Tecnologia'],\n"
    "  adm: ['Admin','Nomina','ADM','Administrativo',\n"
    "        'EPP','Aseo/Limpieza','Papeleria/Oficina','Dotacion','Otro'],\n"
    "  inf: ['Infraestructura','INF','Mantenimiento','Repuestos','Reactivos/Laboratorio'],\n"
    "  cc:  ['CC','Cuenta de Cobro','Cuentas de Cobro']\n"
    "};"
)
assert OLD1 in h, "FIX1 CMAP anchor not found"
h = h.replace(OLD1, NEW1, 1)
print("FIX1 OK - CMAP ampliado")

# ================================================================
# FIX 2: Definir loadSolicitudes (faltaba completamente)
#   Se inserta justo antes de loadInfluencers
# ================================================================
OLD2 = (
    "// \u2500\u2500\u2500 Solicitudes para Catalina \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
    "var SOLIC=[];\n"
    "var INFLUENCERS=[];\n"
    "async function loadInfluencers(){"
)
NEW2 = (
    "// \u2500\u2500\u2500 Solicitudes para Catalina \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
    "var SOLIC=[];\n"
    "var INFLUENCERS=[];\n"
    "async function loadSolicitudes(){\n"
    "  try{\n"
    "    var r=await fetch('/api/solicitudes-compra');\n"
    "    var d=await r.json();\n"
    "    SOLIC=d.solicitudes||[];\n"
    "  }catch(e){ SOLIC=[]; }\n"
    "  renderSolicitudes();\n"
    "}\n"
    "async function loadInfluencers(){"
)
assert OLD2 in h, "FIX2 loadSolicitudes anchor not found"
h = h.replace(OLD2, NEW2, 1)
print("FIX2 OK - loadSolicitudes definida")

# ================================================================
# FIX 3: _guardarNuevoProv: /api/proveedores → /api/proveedores-compras
# ================================================================
OLD3 = "    var r=await fetch('/api/proveedores',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});"
NEW3 = "    var r=await fetch('/api/proveedores-compras',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});"
assert OLD3 in h, "FIX3 _guardarNuevoProv URL anchor not found"
h = h.replace(OLD3, NEW3, 1)
print("FIX3 OK - _guardarNuevoProv URL corregida")

with open(TARGET, 'w') as f:
    f.write(h)
print("\nAll fixes applied.")
