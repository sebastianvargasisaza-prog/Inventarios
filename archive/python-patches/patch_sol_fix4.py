# patch_sol_fix4.py — FIX4: handle guardado en obsStr
TARGET = '/tmp/inv_p9/api/templates_py/solicitudes_html.py'

with open(TARGET, 'r') as f:
    h = f.read()

OLD = "    var obsStr='BENEFICIARIO: '+nombre+' | BANCO: '+banco+' '+tipoCta+' | CUENTA/CEL: '+numcta+(cedula?' | CED/NIT: '+cedula:'')+' | VALOR: $'+valor+' | SERVICIO: '+desc+(obsExtra?' | '+obsExtra:'');\n"
NEW = "    var obsStr='BENEFICIARIO: '+nombre+(handle?' | HANDLE: '+handle:'')+' | BANCO: '+banco+' '+tipoCta+' | CUENTA/CEL: '+numcta+(cedula?' | CED/NIT: '+cedula:'')+' | VALOR: $'+valor+' | SERVICIO: '+desc+(obsExtra?' | '+obsExtra:'');\n"

assert OLD in h, "FIX4 anchor not found — check exact string"
h = h.replace(OLD, NEW, 1)

with open(TARGET, 'w') as f:
    f.write(h)
print("FIX4 OK - handle guardado en obsStr")
