#!/usr/bin/env python3
# coding: utf-8
"""
smoke_check.py - Inventarios/Espagiria
Ejecutar antes de cada git commit: python3 scripts/smoke_check.py

1. Python compile check
2. JS syntax check via node --check
3. Dangerous pattern scan
"""

import re
import subprocess
import sys
import tempfile
import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = REPO_ROOT / "api" / "templates_py"
BLUEPRINTS_DIR = REPO_ROOT / "api" / "blueprints"

ERRORS = []
WARNINGS = []
PRE_EXISTING = []

def err(msg):  ERRORS.append(msg);       print("  X " + msg)
def warn(msg): WARNINGS.append(msg);     print("  ! " + msg)
def pre(msg):  PRE_EXISTING.append(msg); print("  ~ " + msg + "  [pre-existing]")
def ok(msg):   print("  OK " + msg)


# ─── 1. Python compile check ──────────────────────────────────────
print("\n[1/3] Python compile check...")

for py_file in sorted(list(TEMPLATES_DIR.glob("*.py")) + list(BLUEPRINTS_DIR.glob("*.py"))):
    if py_file.name.startswith("_"):
        continue
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(py_file)],
        capture_output=True, text=True
    )
    label = py_file.name if py_file.parent == TEMPLATES_DIR else "blueprints/" + py_file.name
    if result.returncode != 0:
        err(label + ": " + result.stderr.strip())
    else:
        ok(label)


# ─── 2. JS syntax check (node --check) — import-based ───────────
# IMPORTANT: we import the module and evaluate the Python string, then run
# node --check on the EVALUATED output. Raw-text extraction misses bugs like
# actual newlines in JS strings (\n in non-raw strings) because the file
# bytes look fine but Python eval turns \n → real newline → JS SyntaxError.
print("\n[2/3] JS syntax check (node --check via Python import)...")

import importlib, pkgutil
sys.path.insert(0, str(REPO_ROOT))
import api.templates_py as _tpkg

SUBSTITUTIONS = {
    '{usuario}': 'smoketest',
    '{es_contadora}': 'false',
    '{PIN_PLACEHOLDER}': '0000',
}

node_ok = subprocess.run(["node", "--version"], capture_output=True).returncode == 0
if not node_ok:
    warn("node not found - skipping JS syntax check")
else:
    for _importer, modname, _ispkg in sorted(pkgutil.iter_modules(_tpkg.__path__)):
        full_mod = f'api.templates_py.{modname}'
        # Force fresh import so edits are picked up on re-run
        if full_mod in sys.modules:
            del sys.modules[full_mod]
        try:
            mod = importlib.import_module(full_mod)
        except Exception as exc:
            err(f"{modname}.py: import failed — {exc}")
            continue

        html_var = next((a for a in dir(mod) if a.endswith('_HTML')), None)
        if not html_var:
            continue  # not a template module

        html = getattr(mod, html_var)
        for k, v in SUBSTITUTIONS.items():
            html = html.replace(k, v)

        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        js_code = '\n'.join(scripts)
        if not js_code.strip():
            ok(f"{modname}.py: no <script> block")
            continue

        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False,
                                         encoding='utf-8') as tmp:
            tmp.write(js_code)
            tmp_path = tmp.name

        try:
            result = subprocess.run(['node', '--check', tmp_path],
                                    capture_output=True, text=True)
            if result.returncode != 0:
                stderr = result.stderr.strip()
                line_m = re.search(r':(\d+)\n(.+)', stderr)
                offending = ''
                if line_m:
                    lineno = int(line_m.group(1))
                    lines = js_code.split('\n')
                    if 0 < lineno <= len(lines):
                        offending = lines[lineno - 1].strip()
                first_line = stderr.split('\n')[0][:120]
                err(f"{modname}.py: JS syntax error — {first_line}")
                if offending:
                    print('     Line: ' + offending[:140])
            else:
                ok(f"{modname}.py: JS OK")
        finally:
            os.unlink(tmp_path)

# ─── 3. Dangerous pattern scan ────────────────────────────────────
print("\n[3/3] Dangerous pattern scan...")

# (regex, severity, short_description, fix)
# Patterns are designed to minimize false positives:
# - COUNT(*) only matches sequence-generator usage (SELECT COUNT(*) used directly as n+1)
# - insertBefore only flags non-querySelector usage (querySelector refs are valid)
PATTERNS = [
    (
        # Match: COUNT(*) stored directly as the base for a sequence number
        # i.e.:  c.execute("SELECT COUNT(*) FROM <table>"); n = c.fetchone()[0]...
        # Excludes: COUNT(*) with WHERE clause filtering by field (analytics usage)
        r'SELECT COUNT\(\*\) FROM (solicitudes_compra|ordenes_compra|pedidos|despachos)"'
        r'[^)]*\)\s*\n[^n]*n\s*=\s*\(?\s*c\.fetchone',
        "ERROR",
        "COUNT(*) para generar numero de secuencia -- deletion-unsafe (UNIQUE constraint explota)",
        "Usar: COALESCE(MAX(CAST(SUBSTR(col, offset) AS INTEGER)), 0) + 1"
    ),
    (
        # insertBefore NOT preceded by querySelector (querySelector usages are valid)
        r'\.insertBefore\(\s*\w+\s*,\s*document\.getElementById\(',
        "ERROR",
        "insertBefore(el, document.getElementById(...)) -- reference may not be direct child",
        "Poner placeholder estatico en HTML; JS solo show/hide. Evita 'not a child of this node'"
    ),
    (
        # async function body that has 'var data = {' outside try block
        # Simple heuristic: var data = { on a line, followed within 5 lines by fetch(, but NO try{ before fetch
        r'var\s+data\s*=\s*\{[^}]{10,300}\};\s*\n(?:(?!try\s*\{).){0,200}await fetch\(',
        "WARN",
        "var data={} posiblemente fuera del try/catch -- TypeError silencioso si falla antes del fetch",
        "Mover construccion de 'data' DENTRO del bloque try{}"
    ),
    (
        # r.json() call not wrapped in try/catch
        # Flags: await r.json() without a catch nearby
        r'await\s+\w+\.json\(\)(?![\s\S]{0,30}catch)',
        "WARN",
        "r.json() sin try/catch proximo -- explota si server devuelve HTML (500 error page)",
        "Envolver: try{ res=await r.json() }catch(_){ res=null }"
    ),
]

all_files = sorted(
    [p for p in TEMPLATES_DIR.glob("*_html.py")] +
    [p for p in BLUEPRINTS_DIR.glob("*.py") if not p.name.startswith("_")]
)

for py_file in all_files:
    with open(py_file, encoding="utf-8", errors="replace") as f:
        content = f.read()

    for pattern_str, severity, description, suggestion in PATTERNS:
        try:
            matches = list(re.finditer(pattern_str, content, re.DOTALL))
        except re.error as ex:
            warn("Pattern scan regex error [" + pattern_str[:40] + "]: " + str(ex))
            continue

        if not matches:
            continue

        locations = []
        for match in matches[:3]:
            lineno = content[:match.start()].count("\n") + 1
            locations.append("~L" + str(lineno))

        rel = str(py_file.relative_to(REPO_ROOT / "api"))
        msg = rel + " [" + ", ".join(locations) + "]: " + description + "\n    Fix: " + suggestion
        if severity == "ERROR":
            err(msg)
        else:
            warn(msg)


# ─── Result ───────────────────────────────────────────────────────
print("\n" + "=" * 60)
if PRE_EXISTING:
    print("  ~ " + str(len(PRE_EXISTING)) + " pre-existing issue(s) noted (not blocking -- fix when touching that module)")

if ERRORS:
    print("\nFAILED -- " + str(len(ERRORS)) + " error(s), " + str(len(WARNINGS)) + " warning(s)")
    print("\nFix before committing:")
    for e in ERRORS:
        print("  * " + e.split("\n")[0])
    sys.exit(1)
elif WARNINGS:
    print("\nPASSED with " + str(len(WARNINGS)) + " warning(s) -- review before merging to main")
    sys.exit(0)
else:
    print("\nPASSED -- all clear")
    sys.exit(0)
