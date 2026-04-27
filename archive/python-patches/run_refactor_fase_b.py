"""
Fase B Refactor — Extraer init_db / seeds a database.py y limpiar index.py.
Ejecutar desde la raíz del repo: python run_refactor_fase_b.py

Qué hace:
  1. Crea api/database.py con init_db(), seed_compromisos(), seed_rrhh()
     + helper run_seed_rrhh() con conexión propia.
  2. Reescribe api/index.py:
       - Sustituye bloque COMPRAS_USERS/DB_PATH  por import desde config
       - Sustituye bloque def init_db() / seeds   por import desde database
       - Limpia conn2 = __import__(...) → run_seed_rrhh()
       - Sustituye bloque rate-limiter/auth-hooks  por import desde auth
       - Añade register_hooks(app) tras app.config.update(...)
  3. Valida sintaxis con py_compile y restaura backup si falla.
"""

import os, re, shutil, subprocess, sys
from datetime import datetime

BASE_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api')
INDEX_PY   = os.path.join(BASE_DIR, 'index.py')
DB_PY      = os.path.join(BASE_DIR, 'database.py')

if not os.path.isfile(INDEX_PY):
    sys.exit(f"No se encontró {INDEX_PY}")

# ── Backup ────────────────────────────────────────────────────────────────────
ts  = datetime.now().strftime('%Y%m%d_%H%M%S')
bak = INDEX_PY + f'.bak_{ts}'
shutil.copy2(INDEX_PY, bak)
print(f"[OK] Backup: {bak}")

with open(INDEX_PY, 'r', encoding='utf-8') as f:
    source = f.read()
lines = source.splitlines(keepends=True)
print(f"[OK] index.py: {len(lines)} líneas")


# ── Helper: devuelve el número de línea 0-based del primer match ─────────────
def find_line(pattern, required=True):
    m = re.compile(pattern, re.MULTILINE).search(source)
    if not m:
        if required:
            sys.exit(f"[ERROR] No se encontró patrón: {pattern!r}")
        return None
    return source[:m.start()].count('\n')


# ─────────────────────────────────────────────────────────────────────────────
# 1.  IDENTIFICAR RANGOS
# ─────────────────────────────────────────────────────────────────────────────

# CONFIG: desde COMPRAS_USERS hasta DB_PATH (inclusive)
cfg_start = find_line(r'^COMPRAS_USERS\s*=\s*\{')
cfg_end   = find_line(r'^DB_PATH\s*=')
print(f"  Config   : líneas {cfg_start+1}–{cfg_end+1}")

# DATABASE: desde def init_db(): hasta la línea justo antes de init_db()
db_start     = find_line(r'^def init_db\(\):')
initdb_call  = find_line(r'^init_db\(\)\s*$')
db_end       = initdb_call - 1
while db_end > db_start and lines[db_end].strip() == '':
    db_end -= 1
print(f"  Database : líneas {db_start+1}–{db_end+1} ({db_end-db_start+1} líneas)")

# CONN2 CALL: la línea sucia que hace seed_rrhh con __import__
conn2_line = find_line(r'^conn2\s*=\s*__import__')
print(f"  conn2    : línea {conn2_line+1}")

# AUTH: desde el comentario rate-limiter hasta justo antes de @app.route('/login')
auth_start  = find_line(r'^# .*Security.*rate limiter')
login_route = find_line(r"^@app\.route\('/login'")
auth_end    = login_route - 1
while auth_end > auth_start and lines[auth_end].strip() == '':
    auth_end -= 1
print(f"  Auth     : líneas {auth_start+1}–{auth_end+1}")

# INSERTION POINT para register_hooks(app): justo después del bloque app.config.update(...)
# Buscamos la línea con PERMANENT_SESSION_LIFETIME (última línea del bloque .update)
perm_line   = find_line(r'PERMANENT_SESSION_LIFETIME')
# Avanzar hasta el ')' que cierra app.config.update
app_cfg_end = perm_line
while app_cfg_end < len(lines) and lines[app_cfg_end].rstrip() not in (')', )','):
    if lines[app_cfg_end].strip() == ')':
        break
    app_cfg_end += 1
print(f"  app.config.update ends: línea {app_cfg_end+1}")


# ─────────────────────────────────────────────────────────────────────────────
# 2.  CREAR database.py
# ─────────────────────────────────────────────────────────────────────────────
db_lines = lines[db_start:db_end+1]

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

with open(DB_PY, 'w', encoding='utf-8') as f:
    f.write(db_header)
    f.writelines(db_lines)
    f.write(db_footer)

total_db = len(db_lines) + db_header.count('\n') + db_footer.count('\n')
print(f"[OK] database.py creado ({total_db} líneas aprox)")

# Validar sintaxis database.py
res = subprocess.run([sys.executable, '-m', 'py_compile', DB_PY],
                     capture_output=True, text=True)
if res.returncode != 0:
    print(f"[ERROR] database.py sintaxis inválida:\n{res.stderr}")
    os.remove(DB_PY)
    sys.exit(1)
print("[OK] database.py sintaxis Python válida ✓")


# ─────────────────────────────────────────────────────────────────────────────
# 3.  REESCRIBIR index.py
# ─────────────────────────────────────────────────────────────────────────────

# Líneas a omitir completamente
skip = set()

# ① Bloque config (COMPRAS_USERS … DB_PATH)
for i in range(cfg_start, cfg_end + 1):
    skip.add(i)

# ② Bloque database (def init_db(): … último seed)
for i in range(db_start, db_end + 1):
    skip.add(i)

# ③ Línea conn2 = __import__(...)
skip.add(conn2_line)

# ④ Bloque auth (rate limiter … add_security_headers)
for i in range(auth_start, auth_end + 1):
    skip.add(i)

# Inserciones: mapa línea → texto a insertar ANTES de esa línea (o en su lugar si la línea está en skip)
inserts = {}

# Después de la última stdlib import (werkzeug), antes de `app = Flask(`
app_flask_line = find_line(r'^app\s*=\s*Flask\(')
inserts[app_flask_line] = (
    "from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS\n"
    "from database import init_db, seed_compromisos, seed_rrhh, run_seed_rrhh\n"
    "from auth import (\n"
    "    _client_ip, _is_locked, _record_failure, _clear_attempts,\n"
    "    _log_sec, register_hooks,\n"
    ")\n"
    "\n"
)

# Después de app.config.update(...) → agregar register_hooks(app)
inserts[app_cfg_end + 1] = "register_hooks(app)\n\n"

# Reemplazar conn2 = ... con run_seed_rrhh()
inserts[conn2_line] = "run_seed_rrhh()\n"

# Construir nueva lista de líneas
new_lines = []
i = 0
while i < len(lines):
    pre = inserts.get(i)
    if pre and i not in skip:
        new_lines.append(pre)
    elif pre and i in skip:
        new_lines.append(pre)
        i += 1
        continue
    if i not in skip:
        new_lines.append(lines[i])
    i += 1

with open(INDEX_PY, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

reduction = len(lines) - len(new_lines)
print(f"\n[DONE] index.py reescrito: {len(lines)} → {len(new_lines)} líneas")
print(f"[DONE] Reducción: {reduction} líneas ({round(reduction/len(lines)*100)}%)")


# ─────────────────────────────────────────────────────────────────────────────
# 4.  VALIDAR SINTAXIS
# ─────────────────────────────────────────────────────────────────────────────
res = subprocess.run([sys.executable, '-m', 'py_compile', INDEX_PY],
                     capture_output=True, text=True)
if res.returncode == 0:
    print("[OK] Sintaxis Python válida ✓")
    print("\nPróximo paso:")
    print("  git add -A")
    print("  git commit -m 'Fase B: extraer config, database, auth a módulos separados'")
    print("  git push origin main")
else:
    print(f"[ERROR] Sintaxis inválida:\n{res.stderr}")
    print("Restaurando backup...")
    shutil.copy2(bak, INDEX_PY)
    if os.path.exists(DB_PY):
        os.remove(DB_PY)
    print(f"[OK] Restaurado desde {bak}")
    sys.exit(1)
