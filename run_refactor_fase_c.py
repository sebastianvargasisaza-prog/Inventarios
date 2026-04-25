"""
run_refactor_fase_c.py — Fase C: Crear Flask Blueprints desde index.py
Crea api/blueprints/{domain}.py para cada dominio funcional y actualiza index.py
de forma que quede sólo con imports, registro de blueprints y error handlers.

Ejecutar desde la raíz del repo: python run_refactor_fase_c.py
"""
import os
import re
import shutil
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api')
INDEX_PY = os.path.join(BASE_DIR, 'index.py')
BP_DIR   = os.path.join(BASE_DIR, 'blueprints')

if not os.path.isfile(INDEX_PY):
    sys.exit(f"No se encontró {INDEX_PY}")

with open(INDEX_PY, 'r', encoding='utf-8') as f:
    source = f.read()
lines = source.splitlines(keepends=True)
n = len(lines)
print(f"[OK] index.py: {n} líneas")

# ── Definición de blueprints ──────────────────────────────────────────────────
# Rangos 1-indexed (como muestra grep), inclusive en ambos extremos.
# inventario tiene dos bloques no-contiguos; van al mismo archivo.

BLUEPRINTS = OrderedDict([
    ('core',       [(64, 120)]),
    ('hub',        [(121, 298)]),
    ('inventario', [(299, 1365), (3024, 3240)]),
    ('compras',    [(1366, 2061)]),
    ('clientes',   [(2062, 2305)]),
    ('gerencia',   [(2306, 2634)]),
    ('financiero', [(2635, 3023)]),
    ('maquila',    [(3241, 3638)]),
    ('despachos',  [(3639, 3749)]),
    ('rrhh',       [(3750, 3965)]),
    ('calidad',    [(3966, 4089)]),
])

# Header estándar para todos los blueprints.
# Incluye TODOS los templates — Python cachea módulos, no hay costo extra.
BP_HEADER = """\
import os
import json
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS
from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec
from templates_py.rrhh_html import RRHH_HTML
from templates_py.compromisos_html import COMPROMISOS_HTML
from templates_py.home_html import HOME_HTML
from templates_py.hub_html import HUB_HTML
from templates_py.clientes_html import CLIENTES_HTML
from templates_py.calidad_html import CALIDAD_HTML
from templates_py.gerencia_html import GERENCIA_HTML
from templates_py.financiero_html import FINANCIERO_HTML
from templates_py.login_html import LOGIN_HTML
from templates_py.compras_html import COMPRAS_HTML
from templates_py.recepcion_html import RECEPCION_HTML
from templates_py.salida_html import SALIDA_HTML
from templates_py.solicitudes_html import SOLICITUDES_HTML
from templates_py.dashboard_html import DASHBOARD_HTML

"""

# ── Crear directorio blueprints ──────────────────────────────────────────────

os.makedirs(BP_DIR, exist_ok=True)
init_path = os.path.join(BP_DIR, '__init__.py')
if not os.path.exists(init_path):
    with open(init_path, 'w', encoding='utf-8') as f:
        f.write('# blueprints package\n')
    print("[OK] blueprints/__init__.py creado")

# ── Colección de todas las líneas a omitir en index.py (0-indexed) ──────────

skip_set = set()
for name, ranges in BLUEPRINTS.items():
    for start1, end1 in ranges:
        # grep es 1-indexed → Python es 0-indexed
        skip_set.update(range(start1 - 1, end1))

# ── Generar archivos de blueprint ────────────────────────────────────────────

created_files = []

for name, ranges in BLUEPRINTS.items():
    # Colectar líneas de todos los rangos
    bp_lines = []
    for i, (start1, end1) in enumerate(ranges):
        block = lines[start1 - 1 : end1]   # 0-indexed slice
        bp_lines.extend(block)
        # Separador entre rangos no-contiguos
        if i < len(ranges) - 1:
            if bp_lines and not bp_lines[-1].endswith('\n'):
                bp_lines.append('\n')
            bp_lines.append('\n')

    # Transformaciones
    content = ''.join(bp_lines)
    content = content.replace('@app.route(', '@bp.route(')
    if name != 'core':
        content = content.replace("url_for('login')", "url_for('core.login')")

    # Contenido completo del archivo
    bp_decl = f"bp = Blueprint('{name}', __name__)\n\n\n"
    full_content = (
        f"# blueprints/{name}.py — extraído de index.py (Fase C)\n"
        + BP_HEADER
        + bp_decl
        + content
    )

    bp_path = os.path.join(BP_DIR, f'{name}.py')
    with open(bp_path, 'w', encoding='utf-8') as f:
        f.write(full_content)
    created_files.append(bp_path)

    # Validar sintaxis
    res = subprocess.run([sys.executable, '-m', 'py_compile', bp_path],
                         capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[ERROR] blueprints/{name}.py sintaxis inválida:\n{res.stderr}")
        # Limpiar archivos creados
        for p in created_files:
            if os.path.exists(p):
                os.remove(p)
        sys.exit(1)

    total = sum(e - s + 1 for s, e in ranges)
    print(f"  [OK] blueprints/{name}.py — {total} líneas — sintaxis válida ✓")

# ── Bloque de registro de blueprints para el nuevo index.py ─────────────────

bp_imports_str = '\n'.join(
    f'from blueprints.{name} import bp as {name}_bp'
    for name in BLUEPRINTS
)
bp_registers_str = '\n'.join(
    f'app.register_blueprint({name}_bp)'
    for name in BLUEPRINTS
)

BLUEPRINT_BLOCK = (
    '\n\n'
    '# ─── Blueprints ───────────────────────────────────────────────────────────\n'
    + bp_imports_str
    + '\n\n'
    + bp_registers_str
    + '\n\n'
    '# ─── DB init (idempotente) ──────────────────────────────────────────────────\n'
    'init_db()\n'
    'run_seed_rrhh()\n'
)

# ── Construir nuevo index.py ─────────────────────────────────────────────────

# Punto de inserción: línea con DASHBOARD_HTML import (0-indexed)
insertion_idx = None
for i, ln in enumerate(lines):
    if 'from templates_py.dashboard_html import DASHBOARD_HTML' in ln:
        insertion_idx = i
        break

if insertion_idx is None:
    sys.exit("[ERROR] No se encontró la línea de DASHBOARD_HTML import")

print(f"  Blueprint block se inserta tras línea 0-indexed {insertion_idx}")

new_lines = []
for i, line in enumerate(lines):
    if i in skip_set:
        continue          # eliminar líneas de rutas extraídas
    new_lines.append(line)
    if i == insertion_idx:
        new_lines.append(BLUEPRINT_BLOCK)

# ── Backup y escribir ────────────────────────────────────────────────────────

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
bak = INDEX_PY + f'.bak_{ts}'
shutil.copy2(INDEX_PY, bak)
print(f"[OK] Backup index.py: {bak}")

with open(INDEX_PY, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

reduction = len(lines) - len(new_lines)
print(f"[DONE] index.py: {len(lines)} → {len(new_lines)} líneas (−{reduction})")

# ── Validar sintaxis ─────────────────────────────────────────────────────────

res = subprocess.run([sys.executable, '-m', 'py_compile', INDEX_PY],
                     capture_output=True, text=True)
if res.returncode == 0:
    print("[OK] index.py sintaxis válida ✓")
    print('\n✅ Fase C completada. Próximos pasos:')
    print('  git add api/blueprints/ api/index.py')
    print("  git commit -m 'Fase C: Flask Blueprints por dominio funcional'")
    print('  git push origin main')
else:
    print(f"[ERROR] index.py sintaxis inválida:\n{res.stderr}")
    shutil.copy2(bak, INDEX_PY)
    print("[OK] index.py restaurado desde backup")
    for p in created_files:
        if os.path.exists(p):
            os.remove(p)
    sys.exit(1)
