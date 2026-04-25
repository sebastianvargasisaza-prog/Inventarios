"""
extract_templates.py — Fase C pre: extrae templates inline a templates_py/
Elimina CALIDAD_HTML duplicado (dead code) y extrae CALIDAD, RECEPCION, SALIDA
a api/templates_py/, reemplazando cada bloque con un import limpio.

Ejecutar desde la raíz del repo: python extract_templates.py
"""
import os, re, shutil, subprocess, sys
from datetime import datetime

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api')
INDEX_PY = os.path.join(BASE_DIR, 'index.py')
TPL_DIR  = os.path.join(BASE_DIR, 'templates_py')

if not os.path.isfile(INDEX_PY):
    sys.exit(f"No se encontró {INDEX_PY}")
if not os.path.isdir(TPL_DIR):
    sys.exit(f"No se encontró directorio {TPL_DIR}")

with open(INDEX_PY, 'r', encoding='utf-8') as f:
    source = f.read()
lines = source.splitlines(keepends=True)
n = len(lines)
print(f"[OK] index.py: {n} líneas")


def find_pattern_line(pattern, nth=1):
    """Retorna índice 0-based de la línea que coincide (nth-ésima ocurrencia)."""
    count = 0
    for i, ln in enumerate(lines):
        if re.match(pattern, ln):
            count += 1
            if count == nth:
                return i
    sys.exit(f"[ERROR] Patrón no encontrado (nth={nth}): {pattern!r}")


def find_block_end(start_idx, end_patterns):
    """Escanea hacia adelante desde start_idx+1 hasta hallar línea que coincide."""
    for i in range(start_idx + 1, n):
        stripped = lines[i].rstrip('\r\n')
        for pat in end_patterns:
            if re.fullmatch(pat, stripped):
                return i
    sys.exit(f"[ERROR] No se encontró cierre del bloque iniciado en línea {start_idx+1}")


# ── Identificar bloques ──────────────────────────────────────────────────────

# BLOQUE A — dead CALIDAD_HTML (primera definición, sobreescrita)
dead_comment   = find_pattern_line(r'# ─── MÓDULO CALIDAD BPM', nth=1)
dead_def_start = find_pattern_line(r'CALIDAD_HTML\s*=\s*r"""', nth=1)
dead_def_end   = find_block_end(dead_def_start, [r'</html>"""', r'"""'])
print(f"  [A] CALIDAD_HTML dead: líneas {dead_comment+1}–{dead_def_end+1}")

# BLOQUE B — real CALIDAD_HTML (segunda definición)
real_comment    = find_pattern_line(r'# ─── MÓDULO CALIDAD BPM', nth=2)
real_def_start  = find_pattern_line(r'CALIDAD_HTML\s*=\s*r"""', nth=2)
real_def_end    = find_block_end(real_def_start, [r'</html>"""', r'"""'])
print(f"  [B] CALIDAD_HTML real: líneas {real_comment+1}–{real_def_end+1}")

# BLOQUE C — RECEPCION_HTML
rec_start = find_pattern_line(r'RECEPCION_HTML\s*=\s*r"""')
rec_end   = find_block_end(rec_start, [r'"""'])
print(f"  [C] RECEPCION_HTML: líneas {rec_start+1}–{rec_end+1}")

# BLOQUE D — SALIDA_HTML
sal_start = find_pattern_line(r'SALIDA_HTML\s*=\s*r"""')
sal_end   = find_block_end(sal_start, [r'"""'])
print(f"  [D] SALIDA_HTML: líneas {sal_start+1}–{sal_end+1}")


# ── Extraer y escribir archivos templates_py/ ────────────────────────────────

def write_template_file(filename, varname, start, end):
    """Escribe el bloque start..end como módulo Python en templates_py/."""
    path = os.path.join(TPL_DIR, filename)
    if os.path.exists(path):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        shutil.copy2(path, path + f'.bak_{ts}')
        print(f"  [OK] Backup previo: {filename}")
    content = ''.join(lines[start:end + 1])
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"# {filename} — extraído de index.py (Fase C prep)\n")
        f.write(content)
        f.write('\n')
    # Validar sintaxis
    res = subprocess.run([sys.executable, '-m', 'py_compile', path],
                        capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[ERROR] {filename} sintaxis inválida:\n{res.stderr}")
        os.remove(path)
        sys.exit(1)
    print(f"  [OK] {filename} escrito ({end - start + 1} líneas) — sintaxis válida ✓")

write_template_file('calidad_html.py', 'CALIDAD_HTML', real_def_start, real_def_end)
write_template_file('recepcion_html.py', 'RECEPCION_HTML', rec_start, rec_end)
write_template_file('salida_html.py', 'SALIDA_HTML', sal_start, sal_end)


# ── Construir nuevo index.py ─────────────────────────────────────────────────

# Conjunto de índices a omitir
skip = set()

# A — dead block completo (comment + definición + trailing blank si existe)
skip.update(range(dead_comment, dead_def_end + 1))
# Incluir línea en blanco posterior si existe
if dead_def_end + 1 < n and lines[dead_def_end + 1].strip() == '':
    skip.add(dead_def_end + 1)

# B — real CALIDAD_HTML: comment + definición
skip.update(range(real_comment, real_def_end + 1))

# C — RECEPCION_HTML
skip.update(range(rec_start, rec_end + 1))

# D — SALIDA_HTML
skip.update(range(sal_start, sal_end + 1))

# Líneas de reemplazo (solo en la primera línea omitida del bloque)
replacements = {
    real_comment: '# ─── MÓDULO CALIDAD BPM ────────────────────────────────────────\n'
                  'from templates_py.calidad_html import CALIDAD_HTML\n',
    rec_start:    'from templates_py.recepcion_html import RECEPCION_HTML\n',
    sal_start:    'from templates_py.salida_html import SALIDA_HTML\n',
}

new_lines = []
for i, line in enumerate(lines):
    if i in skip:
        if i in replacements:
            new_lines.append(replacements[i])
        # else: línea eliminada
    else:
        new_lines.append(line)

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
    print("\nPróximos pasos:")
    print("  git add api/templates_py/ api/index.py")
    print("  git commit -m 'Fase C pre: extraer CALIDAD/RECEPCION/SALIDA HTML a templates_py'")
    print("  git push origin main")
else:
    print(f"[ERROR] index.py sintaxis inválida:\n{res.stderr}")
    shutil.copy2(bak, INDEX_PY)
    for fname in ['calidad_html.py', 'recepcion_html.py', 'salida_html.py']:
        p = os.path.join(TPL_DIR, fname)
        if os.path.exists(p):
            os.remove(p)
    print("[OK] Todo restaurado desde backups")
    sys.exit(1)
