"""Fix cancel button in aprobarLib modal — removes closest('div') broken JS"""
import re

with open('/tmp/inv_p7/api/templates_py/dashboard_html.py', 'r', encoding='utf-8') as f:
    c = f.read()

# The file contains: onclick="this.closest(\'div\').parentElement.remove()"
# The \' in the file is a literal backslash + quote (Python template string escaping)
# In JavaScript this renders as: this.closest('div') which breaks the outer JS string

# Find the exact broken text
search = "this.closest(\\'div\\')"
idx = c.find(search, 198000)
if idx == -1:
    # Try without the extra backslash context
    search = "closest(\\'div\\')"
    idx = c.find(search, 198000)
print(f"Found '{search}' at idx={idx}")

# Get the full button string to replace
# Pattern: from onclick=" to >Cancelar</button>'
btn_start = c.rfind("+'<button", 0, idx)
btn_end = c.find("Cancelar</button>'", idx) + len("Cancelar</button>'")
old_btn = c[btn_start:btn_end]
print("Old btn:", repr(old_btn[:120]))

# New button uses getElementById - no inner quotes that conflict
new_btn = (
    "+'<button onclick=\"document.getElementById(\\'lib-modal-wrap\\').parentElement.remove()\" "
    "style=\"padding:8px 18px;border:1px solid #ccc;border-radius:6px;cursor:pointer;"
    "background:#f5f5f5;font-size:0.9em;\">Cancelar</button>'"
)
print("New btn:", repr(new_btn[:120]))

c = c[:btn_start] + new_btn + c[btn_end:]
print("Replace OK")

# Also add id to the modal wrapper div if not already there
if 'id="lib-modal-wrap"' not in c:
    lib_idx = c.find("var _clientesLib=[];")
    OLD_DIV = "'<div style=\"background:#fff;border-radius:10px"
    modal_div_idx = c.find(OLD_DIV, lib_idx)
    if modal_div_idx != -1:
        c = c[:modal_div_idx] + "'<div id=\"lib-modal-wrap\" style=\"background:#fff;border-radius:10px" + c[modal_div_idx + len(OLD_DIV):]
        print("Added id=lib-modal-wrap to modal div")

# Verify no broken closest in aprobarLib section
lib_idx = c.find("var _clientesLib=[];")
snippet = c[lib_idx:lib_idx+2500]
remaining = [m.start() for m in re.finditer(r"closest\(", snippet)]
print("Remaining closest() occurrences in aprobarLib:", len(remaining))

with open('/tmp/inv_p7/api/templates_py/dashboard_html.py', 'w', encoding='utf-8') as f:
    f.write(c)
print(f"dashboard_html.py written — {len(c.splitlines())} lines")
