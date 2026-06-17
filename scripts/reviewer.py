#!/usr/bin/env python3
"""REVIEWER - Sebastian 7-may-2026

Pre-commit reviewer · revisa diff staged y aplica heuristicas:

  1. Si modificas un blueprint sin actualizar su CONTRACT_*.md - warning
  2. Si modificas MEMORY.md sin agregar entrada en SESSION_LOG - warning
  3. Si agregas endpoint nuevo (@bp.route) sin agregar test - warning
  4. Si tocas logica critica (movimientos, conteo_items, sync) sin
     actualizar golden paths - ERROR (block)
  5. Si commit no tiene mensaje descriptivo (<10 chars) - warning

Uso:
  python scripts/reviewer.py           - revisa staged
  python scripts/reviewer.py --strict  - warnings se vuelven errors

Instalacion:
  bash scripts/install_hooks.sh
"""
import re
import subprocess
import sys
from pathlib import Path

# Sebastian 8-may-2026: forzar stdout/stderr a UTF-8 para que
# print() no falle en Windows console (cp1252) cuando warnings
# o diff content tienen chars no-ASCII tipo flecha o middot.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, ValueError):
    pass  # Python <3.7 o stream sin reconfigure

REPO_ROOT = Path(__file__).resolve().parent.parent
STRICT = '--strict' in sys.argv

# Mapeo blueprint -> CONTRACT.md esperado
BLUEPRINT_CONTRACTS = {
    'api/blueprints/inventario.py':   'api/blueprints/CONTRACT_inventario.md',
    'api/blueprints/programacion.py': 'api/blueprints/CONTRACT_programacion.md',
    'api/blueprints/compras.py':      'api/blueprints/CONTRACT_compras.md',
}

# Funciones críticas · si tocás estas, debe haber update en golden_paths
CRITICAL_PATTERNS = [
    # función + archivo donde vive
    (r'def conteo_ajustar', 'api/blueprints/inventario.py'),
    (r'def conteo_cerrar', 'api/blueprints/inventario.py'),
    (r'def _sync_calendar_a_produccion_programada', 'api/blueprints/programacion.py'),
    (r'def update_sol_items', 'api/blueprints/compras.py'),
    (r'def limpiar_duplicados_producciones', 'api/blueprints/programacion.py'),
]


def _git(*args):
    """Run git command, return stdout. UTF-8 decode con replace para no
    crashear con archivos legacy en CP1252."""
    r = subprocess.run(['git'] + list(args), cwd=REPO_ROOT,
                       capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.stdout or ''


def _staged_files():
    out = _git('diff', '--cached', '--name-only', '--diff-filter=ACMR')
    return [l.strip() for l in out.splitlines() if l.strip()]


def _staged_diff_content(filepath):
    """Get added lines from staged diff of a file. Tolerant a archivos
    binarios o con encoding mixto."""
    try:
        out = _git('diff', '--cached', '-U0', '--', filepath) or ''
    except Exception:
        return ''
    added = []
    for line in out.splitlines():
        if line.startswith('+') and not line.startswith('+++'):
            added.append(line[1:])
    return '\n'.join(added)


def main():
    files = _staged_files()
    if not files:
        print('REVIEWER · no hay archivos staged · skip')
        return 0

    warnings = []
    errors = []

    # Check 1: blueprint modificado -> CONTRACT.md también?
    for bp_path, contract_path in BLUEPRINT_CONTRACTS.items():
        if bp_path in files and contract_path not in files:
            # Si solo es un fix trivial (1-2 líneas) no exigimos contract
            diff = _git('diff', '--cached', '--shortstat', '--', bp_path)
            # ej: "1 file changed, 5 insertions(+), 2 deletions(-)"
            m = re.search(r'(\d+) insertion', diff)
            ins = int(m.group(1)) if m else 0
            if ins >= 10:
                warnings.append(
                    f'Modificaste {bp_path} ({ins} líneas) pero NO actualizaste '
                    f'{contract_path}. Si cambiaste invariantes / endpoints / '
                    f'tablas -> actualizá el CONTRACT.'
                )

    # Check 2: MEMORY.md cambió -> SESSION_LOG?
    if 'MEMORY.md' in files:
        has_session = any(f.startswith('SESSION_LOG/') and f.endswith('.md')
                          for f in files)
        if not has_session:
            warnings.append(
                'Modificaste MEMORY.md sin agregar entrada en SESSION_LOG/. '
                'Cambios en reglas estáticas requieren justificación auditable.'
            )

    # Check 3: nuevo endpoint @bp.route -> ¿hay test asociado?
    new_routes = []
    for f in files:
        if not f.endswith('.py'):
            continue
        diff = _staged_diff_content(f)
        for m in re.finditer(r"@bp\.route\(['\"]([^'\"]+)['\"]", diff):
            new_routes.append((f, m.group(1)))
    if new_routes:
        # ¿al menos un test_*.py también está staged?
        has_tests = any(f.startswith('tests/test_') and f.endswith('.py')
                        for f in files)
        if not has_tests:
            warnings.append(
                f'{len(new_routes)} endpoint(s) nuevo(s) ' +
                f'({", ".join(r for _, r in new_routes[:3])}) ' +
                'sin test asociado. Agregá un test antes de mergear.'
            )

    # Check 4: tocó función crítica -> golden_paths debe estar staged también
    critical_touched = []
    for f in files:
        if not f.endswith('.py'):
            continue
        diff = _staged_diff_content(f)
        for pattern, expected_file in CRITICAL_PATTERNS:
            if expected_file == f and re.search(pattern, diff):
                critical_touched.append((f, pattern))
    if critical_touched:
        golden_in_staged = 'tests/test_golden_paths.py' in files
        if not golden_in_staged:
            errors.append(
                f'Tocaste función CRÍTICA: ' +
                ', '.join(p for _, p in critical_touched[:3]) +
                '. Estas funciones tienen golden paths que las protegen. '
                'Confirma que test_golden_paths.py SIGUE PASANDO localmente '
                'antes de commit. Si pasa, este check no aplica.'
            )

    # Check 5: validar JS embebido en templates_py/*.py
    # Sebastián 13-may-2026: cazó el bug fatal de comillas simples dentro
    # de onerror inline · rompía silenciosamente todo el <script> · sub-tabs
    # dejaron de abrir. Cero error a futuro: importamos el módulo, agarramos
    # el HTML RENDERED (no el .py raw) y validamos cada <script> con
    # `node --check`. Sin node · skip silencioso.
    templates_touched = [f for f in files
                          if f.startswith('api/templates_py/') and f.endswith('.py')]
    if templates_touched:
        try:
            node_check = subprocess.run(['node', '--version'],
                                         capture_output=True, timeout=5)
            node_ok = node_check.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            node_ok = False
        if node_ok:
            import tempfile, os as _os
            # sys.path: agregar api/ para que `import templates_py.xxx` funcione
            api_path = str(REPO_ROOT / 'api')
            if api_path not in sys.path:
                sys.path.insert(0, api_path)
            import importlib
            for tpl_path in templates_touched:
                # Convertir 'api/templates_py/foo_html.py' → 'templates_py.foo_html'
                module_name = (tpl_path
                                .replace('api/', '', 1)
                                .replace('/', '.')
                                .replace('.py', ''))
                try:
                    if module_name in sys.modules:
                        importlib.reload(sys.modules[module_name])
                        mod = sys.modules[module_name]
                    else:
                        mod = importlib.import_module(module_name)
                except Exception as e:
                    warnings.append(f'No pude importar {module_name}: {e}')
                    continue
                # Recolectar todos los strings >1000 chars (los HTML)
                html_strings = []
                for attr_name in dir(mod):
                    if attr_name.startswith('_'):
                        continue
                    val = getattr(mod, attr_name, None)
                    if isinstance(val, str) and len(val) > 1000:
                        html_strings.append((attr_name, val))
                    elif callable(val):
                        # Functions like render_xxx() pueden devolver el HTML
                        try:
                            import inspect
                            if not inspect.isfunction(val):
                                continue
                            sig = inspect.signature(val)
                            if any(p.default is p.empty and p.kind != p.VAR_KEYWORD
                                   for p in sig.parameters.values()
                                   if p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)):
                                continue  # requiere args · skip
                            rendered = val()
                            if isinstance(rendered, str) and len(rendered) > 1000:
                                html_strings.append((attr_name + '()', rendered))
                        except Exception:
                            pass
                if not html_strings:
                    continue
                for attr_name, html in html_strings:
                    scripts = re.findall(r'<script[^>]*>(.*?)</script>',
                                          html, re.DOTALL)
                    for i, sc in enumerate(scripts):
                        if len(sc) < 50:
                            continue
                        with tempfile.NamedTemporaryFile(
                                mode='w', suffix='.js', delete=False,
                                encoding='utf-8') as tf:
                            tf.write(sc)
                            tf_path = tf.name
                        try:
                            r = subprocess.run(
                                ['node', '--check', tf_path],
                                capture_output=True, text=True, timeout=15,
                                encoding='utf-8', errors='replace',
                            )
                            if r.returncode != 0:
                                err_lines = (r.stderr or '').strip().split('\n')[:3]
                                errors.append(
                                    f'JS SYNTAX ERROR en {tpl_path} ({attr_name} '
                                    f'script #{i+1}): ' + ' · '.join(err_lines)[:400]
                                )
                        except Exception as e:
                            warnings.append(
                                f'No pude validar JS de {tpl_path}: {e}'
                            )
                        finally:
                            try: _os.unlink(tf_path)
                            except Exception: pass

    # ──────────────────────────────────────────────────────────────────
    # Check 6: PROTOCOLO ZERO-ERROR (22-may-2026) · Sebastián
    # Detecta antipatrones de los 76 bugs de auditoría 21-may.
    # Memoria viva: project_bugs_patrones_recurrentes_21may.md
    # ──────────────────────────────────────────────────────────────────
    ZERO_ERROR_PATTERNS = [
        # (regex, error/warning, descripción)
        (r'CASE WHEN tipo="', 'ERROR', 'SQL doble comilla "" inválido en PG · usar single quotes'),
        (r"date\('now',\s*'-?\d", 'WARN',
         "date('now',...) multi-arg falla en PG · usar timedelta Python + ?"),
        (r"f['\"]SELECT .*WHERE.*=.*\\{", 'WARN',
         'f-string SQL · usar params ? (anti-SQLi + PG compat)'),
        (r'session\.get\([\'\"]compras_user[\'\"]\)\s*\)\s*not in', 'WARN',
         'Comparación user vacío sin guard previo · validar `if not user: return 401`'),
        (r"COALESCE\((\w+),''\)\s*=\s*\"\"", 'WARN',
         'COALESCE(col,"") es identificador vacío en PG · usar \'\''),
        (r"hmac\.compare_digest\(expected,\s*password\)", 'ERROR',
         'Plaintext password fallback prohibido · solo pbkdf2/scrypt'),
        (r"innerHTML\s*=\s*[^;]*\$\{[^}]*\.(?:nombre|descripcion|lote|observaciones)\b", 'WARN',
         'Template literal sin esc() · XSS stored · escapar strings de DB'),
        (r"INSERT INTO movimientos.*lote.*=.*''", 'WARN',
         'lote vacío en INSERT movimientos · usar lote real o sintético con advertencia'),
        (r"check_password_hash\([^,]+,\s*[^)]+\)\s*$", 'WARN',
         'check_password_hash sin validar formato hash · verificar pbkdf2:/scrypt: prefix'),
        (r"_require_compras_session\(\)\s*$", 'WARN',
         'Endpoint con _require_compras_session · si toca PII upgrade a _require_compras_write'),
        # 17-jun · M45/M46 · drift PG recurrente: CAST(SUBSTR(...)) sobre texto
        # revienta en PostgreSQL si el sufijo no es 100% numérico (nº de OC con
        # sufijo, códigos MP con letras). SQLite lo tolera con 0 → bug invisible
        # en local. Extraer el correlativo en Python (audit_helpers.siguiente_numero_oc).
        (r"CAST\(\s*SUBSTR\(", 'WARN',
         'CAST(SUBSTR(...)) sobre texto revienta en PG si el sufijo no es numérico · '
         'extraer el correlativo en Python (ver audit_helpers.siguiente_numero_oc)'),
        # 17-jun · M46 · `.get(col,'')` devuelve None cuando la columna TEXT es NULL
        # (la clave existe con valor None → el default NO aplica) → `.startswith`/etc
        # revienta con 500 (bug anular_movimiento). Usar `(x.get(col) or '')`.
        (r"\.get\([^,)]+,\s*['\"]['\"]\)\.(startswith|strip|upper|lower|split|replace|endswith|rstrip|lstrip)",
         'WARN',
         ".get(col,'') da None si la columna es NULL · usar (x.get(col) or '') antes de un método de string"),
    ]
    for f in files:
        if not f.endswith('.py') and not f.endswith('.html'):
            continue
        diff = _staged_diff_content(f)
        if not diff:
            continue
        for added_line in [l[1:] for l in diff.split('\n') if l.startswith('+') and not l.startswith('+++')]:
            for regex, severity, desc in ZERO_ERROR_PATTERNS:
                if re.search(regex, added_line):
                    msg = f'ZERO-ERROR · {f} · {desc} · ej: {added_line.strip()[:80]}'
                    if severity == 'ERROR':
                        errors.append(msg)
                    else:
                        warnings.append(msg)
                    break

    # Check 7: commit message significativo (heurística: hooks no acceden al
    # mensaje en pre-commit, solo en commit-msg. Skip por ahora.)

    # Reportar (ASCII-safe para Windows cmd)
    print('')
    print('[REVIEWER] pre-commit checks')
    print(f'  archivos staged: {len(files)}')
    print('')
    if not warnings and not errors:
        print('[OK] Todo bien')
        return 0
    if warnings:
        print(f'[WARN] {len(warnings)} warning(s):')
        for w in warnings:
            print(f'   - {w}')
        print('')
    if errors:
        print(f'[ERROR] {len(errors)} error(s):')
        for e in errors:
            print(f'   - {e}')
        print('')
        return 1
    if STRICT and warnings:
        print('STRICT mode: warnings tratados como errors. Block commit.')
        return 1
    print('Commit permitido (warnings no bloquean en modo normal).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
