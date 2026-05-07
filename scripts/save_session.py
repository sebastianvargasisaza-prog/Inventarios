#!/usr/bin/env python3
"""SAVE SESSION · Sebastián 7-may-2026

Para usar al CERRAR una sesión IA (epilogue).

Genera un SESSION_LOG/YYYY-MM-DD-N.md con:
  · Commits creados en esta sesión
  · Archivos modificados
  · Archivos creados
  · Stats de la suite (si ya corrió)

Uso:
  python scripts/save_session.py "Resumen breve del trabajo"
  python scripts/save_session.py --auto    · usa último mensaje commit como resumen
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SESSION_LOG = REPO_ROOT / 'SESSION_LOG'


def _git(*args):
    r = subprocess.run(['git'] + list(args), cwd=REPO_ROOT,
                       capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return (r.stdout or '').strip()


def _commits_today():
    """Commits del día (UTC)."""
    today = datetime.utcnow().strftime('%Y-%m-%d')
    log = _git('log', f'--since={today}', '--pretty=format:%h|%s|%an')
    return [line.split('|', 2) for line in log.splitlines() if line.strip()]


def _files_changed_today():
    today = datetime.utcnow().strftime('%Y-%m-%d')
    log = _git('log', f'--since={today}', '--pretty=format:', '--name-status')
    files = set()
    for line in log.splitlines():
        if not line.strip():
            continue
        parts = line.split('\t', 1)
        if len(parts) == 2:
            status, path = parts
            files.add((status, path))
    return sorted(files)


def main():
    args = sys.argv[1:]
    auto = '--auto' in args
    args = [a for a in args if a != '--auto']
    summary = ' '.join(args).strip()

    if auto and not summary:
        commits = _commits_today()
        summary = commits[0][1] if commits else 'Sesión sin commits'
    if not summary:
        print('Uso: python scripts/save_session.py "resumen breve"')
        print('  o: python scripts/save_session.py --auto')
        return 1

    SESSION_LOG.mkdir(exist_ok=True)
    today = datetime.utcnow().strftime('%Y-%m-%d')

    # Encontrar siguiente sufijo si ya hay log de hoy
    existing = sorted(SESSION_LOG.glob(f'{today}*.md'))
    suffix_n = len(existing) + 1
    if suffix_n == 1:
        filename = f'{today}.md'
    else:
        filename = f'{today}-{suffix_n}.md'
    target = SESSION_LOG / filename

    if target.exists():
        # Append en vez de overwrite
        mode = 'a'
        prefix = '\n\n---\n\n'
    else:
        mode = 'w'
        prefix = ''

    commits = _commits_today()
    files = _files_changed_today()

    lines = [
        prefix + f'# Sesión {today} · {summary}',
        '',
        f'Generado: {datetime.utcnow().isoformat()}Z',
        '',
        '## Commits creados',
        '',
    ]
    if commits:
        for h, msg, author in commits:
            lines.append(f'- `{h}` {msg.strip()} _({author.strip()})_')
    else:
        lines.append('_Sin commits hoy._')

    lines += ['', '## Archivos cambiados', '']
    if files:
        for status, path in files:
            sym = {'A': '➕', 'M': '✏️', 'D': '➖', 'R100': '➡️'}.get(status, status)
            lines.append(f'- {sym} `{path}`')
    else:
        lines.append('_Sin cambios hoy._')

    lines += [
        '',
        '## Próximos pasos',
        '',
        '_(Editar este archivo manualmente si querés agregar pendientes,',
        ' decisiones, bugs, etc.)_',
        '',
    ]

    with open(target, mode, encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f'[OK] SESSION_LOG escrito: {target.relative_to(REPO_ROOT)}')
    print(f'     Commits: {len(commits)} · Archivos: {len(files)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
