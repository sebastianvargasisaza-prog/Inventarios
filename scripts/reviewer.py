#!/usr/bin/env python3
"""REVIEWER · Sebastián 7-may-2026

Pre-commit reviewer · revisa diff staged y aplica heurísticas:

  1. Si modificás un blueprint sin actualizar su CONTRACT_*.md → warning
  2. Si modificás MEMORY.md sin agregar entrada en SESSION_LOG → warning
  3. Si agregás endpoint nuevo (@bp.route) sin agregar test → warning
  4. Si tocás logica crítica (movimientos, conteo_items, sync) sin
     actualizar golden paths → ERROR (block)
  5. Si commit no tiene mensaje descriptivo (<10 chars) → warning

Uso:
  python scripts/reviewer.py           · revisa staged
  python scripts/reviewer.py --strict  · warnings → errors

Instalación:
  bash scripts/install_hooks.sh
"""
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STRICT = '--strict' in sys.argv

# Mapeo blueprint → CONTRACT.md esperado
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

    # Check 1: blueprint modificado → CONTRACT.md también?
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
                    f'tablas → actualizá el CONTRACT.'
                )

    # Check 2: MEMORY.md cambió → SESSION_LOG?
    if 'MEMORY.md' in files:
        has_session = any(f.startswith('SESSION_LOG/') and f.endswith('.md')
                          for f in files)
        if not has_session:
            warnings.append(
                'Modificaste MEMORY.md sin agregar entrada en SESSION_LOG/. '
                'Cambios en reglas estáticas requieren justificación auditable.'
            )

    # Check 3: nuevo endpoint @bp.route → ¿hay test asociado?
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

    # Check 4: tocó función crítica → golden_paths debe estar staged también
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

    # Check 5: commit message significativo (heurística: hooks no acceden al
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
