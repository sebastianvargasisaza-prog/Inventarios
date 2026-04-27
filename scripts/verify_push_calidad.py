"""Verify calidad_html.py fix and push to GitHub"""
import ast, subprocess, os

path = '/tmp/inv_p8/api/templates_py/calidad_html.py'

# 1. Python syntax check
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

try:
    ast.parse(src)
    print('Python syntax OK')
except SyntaxError as e:
    print(f'Python SyntaxError line {e.lineno}: {e.msg}')
    exit(1)

# 2. Extract HTML and check JS around the fixed lines
ns = {}
exec(src, ns)
html = ns.get('CALIDAD_HTML', '')
lines = html.split('\n')
print(f'HTML lines: {len(lines)}')
# Show lines 270-280 of rendered HTML
for i in range(269, min(280, len(lines))):
    print(f'L{i+1}: {lines[i][:200]}')

# 3. Confirm no \!= remains
bad = '\\' + '!='
remaining = html.count(bad)
print(f'\nRemaining \\!= in HTML: {remaining}')

# 4. Confirm != is present correctly
correct = html.count('!=')
print(f'Correct != occurrences: {correct}')

# 5. Git commit and push
os.chdir('/tmp/inv_p8')
result = subprocess.run(
    ['git', 'config', 'user.email', 'sebastianvargasisaza@gmail.com'],
    capture_output=True, text=True
)
result = subprocess.run(
    ['git', 'config', 'user.name', 'Sebastian'],
    capture_output=True, text=True
)
result = subprocess.run(
    ['git', 'add', 'api/templates_py/calidad_html.py'],
    capture_output=True, text=True
)
result = subprocess.run(
    ['git', 'commit', '-m', 'fix(calidad): corregir \\!= -> != en JS loadDash (heredoc corruption)'],
    capture_output=True, text=True
)
print('\nCommit:', result.stdout.strip() or result.stderr.strip())

result = subprocess.run(
    ['git', 'push', 'origin', 'main'],
    capture_output=True, text=True
)
print('Push:', result.stdout.strip() or result.stderr.strip())
print('Push rc:', result.returncode)
