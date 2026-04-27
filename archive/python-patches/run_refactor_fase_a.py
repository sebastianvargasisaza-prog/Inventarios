"""
Fase A Refactor — Extraer HTML templates a módulos separados.
Detecta correctamente cierres tanto en línea propia como inline (</html>\""").
Ejecutar desde la raíz del repo: python run_refactor_fase_a.py
"""

import os, re, shutil, subprocess, sys
from datetime import datetime

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api')
INDEX_PY = os.path.join(BASE_DIR, 'index.py')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates_py')

if not os.path.isfile(INDEX_PY):
    sys.exit(f"No se encontró {INDEX_PY}")

# Backup
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
bak = INDEX_PY + f'.bak_{ts}'
shutil.copy2(INDEX_PY, bak)
print(f"[OK] Backup: {bak}")

with open(INDEX_PY, 'r', encoding='utf-8') as f:
    source = f.read()

lines = source.splitlines(keepends=True)
print(f"[OK] index.py: {len(lines)} líneas")

# ── Localizar templates usando AST-like token scan ────────────────────────────
# Patrón: VAR = """...""" o VAR = r"""..."""
# Soporta cierre en línea propia O al final de una línea (</html>""")

TEMPLATES = [
    'RRHH_HTML',
    'COMPROMISOS_HTML',
    'HOME_HTML',
    'HUB_HTML',
    'CLIENTES_HTML',
    'GERENCIA_HTML',
    'FINANCIERO_HTML',
    'LOGIN_HTML',
    'COMPRAS_HTML',
    'SOLICITUDES_HTML',
    'DASHBOARD_HTML',
]

def find_triple_string_end(lines, start_0idx):
    """
    Dado el índice 0-based de la línea de apertura (VAR = r\"\"\" o VAR = \"\"\"),
    encuentra el índice 0-based de la línea de cierre (inclusive).
    La cadena puede cerrar:
      - En una línea propia: sólo \"\"\" (con posibles espacios)
      - Al final de contenido: cualquier cosa + \"\"\"
    No confunde con la apertura (que tiene = antes).
    """
    open_line = lines[start_0idx]
    # Detectar si hay contenido en la primera línea después de """
    # ej: VAR = """contenido...  (cierra en otra línea)
    # ej: VAR = """              (cierra en otra línea)
    m = re.search(r'r?"""', open_line)
    if not m:
        raise ValueError(f"No se encontró apertura en línea {start_0idx+1}")
    after_open = open_line[m.end():]
    # ¿Cierra en la misma línea de apertura?
    if '"""' in after_open:
        return start_0idx  # string de una sola línea
    # Buscar cierre en las siguientes líneas
    i = start_0idx + 1
    while i < len(lines):
        if '"""' in lines[i]:
            return i
        i += 1
    raise ValueError(f"No se encontró cierre para template desde línea {start_0idx+1}")

# Construir mapa de rangos
ranges = {}  # var_name → (start_0, end_0)
for var in TEMPLATES:
    # Buscar la línea de asignación
    pat = re.compile(r'^' + re.escape(var) + r'\s*=\s*r?"""', re.MULTILINE)
    m = pat.search(source)
    if not m:
        print(f"  [WARN] No se encontró {var} en index.py — omitido")
        continue
    # Convertir offset a número de línea 0-based
    line_start = source[:m.start()].count('\n')
    line_end = find_triple_string_end(lines, line_start)
    ranges[var] = (line_start, line_end)
    print(f"  {var}: líneas {line_start+1}–{line_end+1} ({line_end-line_start+1} líneas)")

# ── Crear directorio templates_py ────────────────────────────────────────────
os.makedirs(TEMPLATES_DIR, exist_ok=True)
init_path = os.path.join(TEMPLATES_DIR, '__init__.py')
if not os.path.exists(init_path):
    with open(init_path, 'w') as f:
        f.write('# HTML template modules\n')

# ── Escribir cada módulo de template ─────────────────────────────────────────
sk = set()
ia = {}  # 0-idx → import statement

for var, (s0, e0) in ranges.items():
    fname = var.lower() + '.py'
    fpath = os.path.join(TEMPLATES_DIR, fname)
    template_lines = lines[s0:e0+1]
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(f'# Auto-extraído de index.py — Fase A refactor\n')
        f.writelines(template_lines)
    print(f"  [OK] {fname} ({len(template_lines)} líneas)")
    for i in range(s0, e0+1):
        sk.add(i)
    ia[s0] = f'from templates_py.{var.lower()} import {var}\n'

# ── Reconstruir index.py ─────────────────────────────────────────────────────
new_lines = []
for i, line in enumerate(lines):
    if i in ia:
        new_lines.append(ia[i])
    elif i not in sk:
        new_lines.append(line)

with open(INDEX_PY, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"\n[DONE] index.py reescrito: {len(lines)} → {len(new_lines)} líneas")
print(f"[DONE] Reducción: {len(lines)-len(new_lines)} líneas ({round((len(lines)-len(new_lines))/len(lines)*100)}%)")

# ── Verificar sintaxis ────────────────────────────────────────────────────────
result = subprocess.run(
    [sys.executable, '-m', 'py_compile', INDEX_PY],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("[OK] Sintaxis Python válida ✓")
    print("\nPróximo paso: git add -A && git commit -m 'Fase A: Extraer HTML templates a módulos' && git push")
else:
    print(f"[ERROR] Sintaxis inválida:\n{result.stderr}")
    print("Restaurando backup...")
    shutil.copy2(bak, INDEX_PY)
    print(f"[OK] Restaurado desde {bak}")
