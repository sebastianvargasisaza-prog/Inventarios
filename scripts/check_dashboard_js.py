"""Verifica con node --check que el JS de DASHBOARD_HTML es válido.

Uso: python scripts/check_dashboard_js.py
Sale con código 1 si hay error.
"""
import sys
import os
import re
import subprocess
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
from templates_py.dashboard_html import DASHBOARD_HTML

html = DASHBOARD_HTML
scripts = list(re.finditer(r'<script[^>]*>(.*?)</script>', html, re.DOTALL))

errores = []
for i, m in enumerate(scripts):
    body = m.group(1).strip()
    if len(body) < 200:
        continue
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
        f.write('(async function(){\n' + body + '\n})();\n')
        tmpname = f.name
    try:
        result = subprocess.run(
            ['node', '--check', tmpname],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            stderr = (result.stderr or '').strip()
            # Limpiar caracteres no-ASCII para Windows console
            stderr_safe = stderr.encode('ascii', 'replace').decode('ascii')
            errores.append((i + 1, stderr_safe[:500]))
    except Exception as e:
        errores.append((i + 1, str(e)))
    finally:
        try:
            os.unlink(tmpname)
        except Exception:
            pass

if errores:
    print(f'[FAIL] {len(errores)} script(s) con syntax errors:')
    for idx, err in errores:
        print(f'  Script #{idx}:')
        for line in err.split('\n')[:6]:
            print(f'    {line}')
    sys.exit(1)
else:
    print(f'[OK] {len(scripts)} scripts validados con node --check')
    sys.exit(0)
