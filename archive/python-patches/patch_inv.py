"""Patch inventario.py — add calidad_registros INSERT on liberacion Liberado"""
SRC = '/tmp/inv_p7'

with open(f'{SRC}/api/blueprints/inventario.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Anchor: the UPDATE liberaciones SET estado='Liberado' line
LIBERADO_UPD = "UPDATE liberaciones SET estado='Liberado'"
assert LIBERADO_UPD in c, "Liberado UPDATE anchor not found"

# Anchor: elif estado == 'Rechazado' — insert BEFORE this line
ELIF_RECH = "    elif estado == 'Rechazado':"
assert ELIF_RECH in c, "elif Rechazado anchor not found"

# Find the elif that comes AFTER the Liberado UPDATE
lib_idx = c.find(LIBERADO_UPD)
elif_idx = c.find(ELIF_RECH, lib_idx)
assert elif_idx != -1, "elif Rechazado not found after Liberado block"

CAL_BLOCK = (
    "        # Registrar en calidad como BPM completado\n"
    "        try:\n"
    "            _lib_val = lib[1] if lib else 'PT'\n"
    "            _lib_lote = lib[0] if lib else ''\n"
    "            _cli_dest = d.get('cliente','') or 'sin cliente'\n"
    "            c.execute(\"\"\"INSERT INTO calidad_registros\n"
    "                         (fecha, tarea_id, usuario, estado, valor_registrado, observaciones)\n"
    "                         VALUES (date('now'), NULL, ?, 'Completado', ?, ?)\"\"\",\n"
    "                     (u,\n"
    "                      f\"{_lib_lote} | {str(_lib_val)[:40]}\",\n"
    "                      f\"BPM Liberacion PT -> {_cli_dest}\"))\n"
    "        except Exception:\n"
    "            pass\n"
)

# Confirm not already patched
if 'BPM Liberacion PT' in c:
    print("Already patched — skipping")
else:
    c = c[:elif_idx] + CAL_BLOCK + c[elif_idx:]
    print("calidad_registros INSERT added")

# Verify variable 'lib' and 'u' exist in scope before the elif
snippet = c[lib_idx-500:elif_idx+50]
has_lib = 'lib = c.fetchone()' in snippet or 'lib=c.fetchone()' in snippet
has_u = ' u ' in snippet or "session.get(" in snippet
print(f"Scope check — lib in scope: {has_lib}, u in scope: {has_u}")

with open(f'{SRC}/api/blueprints/inventario.py', 'w', encoding='utf-8') as f:
    f.write(c)
print(f"inventario.py done — {len(c.splitlines())} lines")
