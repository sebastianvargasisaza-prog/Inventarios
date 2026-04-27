"""
Crea api/database.py extrayendo las funciones DB de index.py.
Ejecutar desde la raíz del repo: python create_database_py.py

Úsalo cuando run_refactor_fase_b.py ya no sirve (config y auth
fueron extraídos manualmente en Fase B.1).
"""
import os, re, shutil, subprocess, sys
from datetime import datetime

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api')
INDEX_PY = os.path.join(BASE_DIR, 'index.py')
DB_PY    = os.path.join(BASE_DIR, 'database.py')

if not os.path.isfile(INDEX_PY):
    sys.exit(f"No se encontró {INDEX_PY}")

with open(INDEX_PY, 'r', encoding='utf-8') as f:
    source = f.read()
lines = source.splitlines(keepends=True)
print(f"[OK] index.py: {len(lines)} líneas")

def find_line(pattern, required=True):
    m = re.compile(pattern, re.MULTILINE).search(source)
    if not m:
        if required:
            sys.exit(f"[ERROR] No se encontró patrón: {pattern!r}")
        return None
    return source[:m.start()].count('\n')

# Rango: desde def init_db(): hasta def run_seed_rrhh(): (exclusive)
db_start    = find_line(r'^def init_db\(\):')
run_seed_line = find_line(r'^def run_seed_rrhh\(\):', required=False)

if run_seed_line is None:
    # run_seed_rrhh no está aún — extraer hasta init_db() call
    initdb_call = find_line(r'^init_db\(\)\s*$')
    db_end = initdb_call - 1
else:
    db_end = run_seed_line - 1

# Trim trailing blank lines
while db_end > db_start and lines[db_end].strip() == '':
    db_end -= 1

print(f"  DB block: líneas {db_start+1}–{db_end+1} ({db_end-db_start+1} líneas)")

db_header = (
    "# database.py — inicialización de BD y seeds\n"
    "# Fase B refactor: extraído de index.py\n"
    "import os\n"
    "import sqlite3\n"
    "import random\n"
    "from datetime import datetime\n"
    "\n"
    "from config import DB_PATH\n"
    "\n"
    "\n"
)

db_footer = (
    "\n\n"
    "def run_seed_rrhh():\n"
    '    """Ejecuta seed_rrhh con su propia conexión (llamada al arranque)."""\n'
    "    conn = sqlite3.connect(DB_PATH)\n"
    "    c = conn.cursor()\n"
    "    seed_rrhh(c)\n"
    "    conn.commit()\n"
    "    conn.close()\n"
)

db_lines = lines[db_start:db_end+1]

# Backup if exists
if os.path.exists(DB_PY):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    shutil.copy2(DB_PY, DB_PY + f'.bak_{ts}')
    print(f"[OK] Backup previo guardado")

with open(DB_PY, 'w', encoding='utf-8') as f:
    f.write(db_header)
    f.writelines(db_lines)
    f.write(db_footer)

print(f"[OK] database.py creado ({len(db_lines)} líneas extraídas)")

# Validar sintaxis
res = subprocess.run([sys.executable, '-m', 'py_compile', DB_PY],
                     capture_output=True, text=True)
if res.returncode != 0:
    print(f"[ERROR] database.py sintaxis inválida:\n{res.stderr}")
    os.remove(DB_PY)
    sys.exit(1)
print("[OK] database.py sintaxis válida ✓")

# Ahora actualizar index.py:
# 1. Quitar las definiciones locales (init_db, seed_compromisos, seed_rrhh, run_seed_rrhh)
# 2. Añadir: from database import init_db, seed_compromisos, seed_rrhh, run_seed_rrhh

# Leer index.py actualizado
with open(INDEX_PY, 'r', encoding='utf-8') as f:
    src2 = f.read()
lines2 = src2.splitlines(keepends=True)

# Bloque a eliminar: desde def init_db(): hasta el final de run_seed_rrhh()
# (inclusive), más la llamada init_db() y run_seed_rrhh()

def find_line2(pattern, src, required=True):
    m = re.compile(pattern, re.MULTILINE).search(src)
    if not m:
        if required: sys.exit(f"[ERROR] No encontrado en index.py: {pattern!r}")
        return None
    return src[:m.start()].count('\n')

db_s2 = find_line2(r'^def init_db\(\):', src2)
# Find end of run_seed_rrhh (last function — look for next @app.route or end of file)
# Safer: find the line "from templates_py" which comes right after
next_block = find_line2(r'^from templates_py\.', src2)
db_e2 = next_block - 1
while db_e2 > db_s2 and lines2[db_e2].strip() == '':
    db_e2 -= 1

print(f"  Bloque a eliminar de index.py: líneas {db_s2+1}–{db_e2+1}")

# Líneas init_db() y run_seed_rrhh() calls
calls = set()
for pat in [r'^init_db\(\)\s*$', r'^run_seed_rrhh\(\)\s*$']:
    ln = find_line2(pat, src2, required=False)
    if ln is not None: calls.add(ln)

# Insertion point: before app = Flask(
app_line = find_line2(r'^app\s*=\s*Flask\(', src2)

skip2 = set(range(db_s2, db_e2+1)) | calls
imports_db = "from database import init_db, seed_compromisos, seed_rrhh, run_seed_rrhh\n"

new_lines2 = []
for i, line in enumerate(lines2):
    if i == app_line:
        new_lines2.append(imports_db)
    if i not in skip2:
        new_lines2.append(line)

ts2 = datetime.now().strftime('%Y%m%d_%H%M%S')
bak2 = INDEX_PY + f'.bak_{ts2}'
shutil.copy2(INDEX_PY, bak2)
print(f"[OK] Backup index.py: {bak2}")

with open(INDEX_PY, 'w', encoding='utf-8') as f:
    f.writelines(new_lines2)

reduction = len(lines2) - len(new_lines2)
print(f"[DONE] index.py: {len(lines2)} → {len(new_lines2)} líneas (−{reduction})")

res2 = subprocess.run([sys.executable, '-m', 'py_compile', INDEX_PY],
                      capture_output=True, text=True)
if res2.returncode == 0:
    print("[OK] index.py sintaxis válida ✓")
    print("\nPróximos pasos:")
    print("  git add api/database.py api/index.py api/config.py api/auth.py")
    print("  git commit -m 'Fase B: extraer config, database, auth a módulos base'")
    print("  git push origin main")
else:
    print(f"[ERROR] index.py sintaxis inválida:\n{res2.stderr}")
    shutil.copy2(bak2, INDEX_PY)
    os.remove(DB_PY)
    print("[OK] Ambos archivos restaurados desde backup")
    sys.exit(1)
