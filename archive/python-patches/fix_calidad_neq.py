"""Fix \!= -> != in calidad_html.py JS (heredoc bash corruption)"""
import re

path = '/tmp/inv_p8/api/templates_py/calidad_html.py'
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# Find the kv-lib-mes context
idx = src.find('kv-lib-mes')
if idx != -1:
    chunk = src[idx:idx+150]
    print('Raw repr:', repr(chunk))
else:
    print('kv-lib-mes NOT FOUND')

# Check what characters surround !=
# Search for the literal backslash-exclamation pattern
bad = '\\'+ '!='   # literal \!=
good = '!='

count_bad = src.count(bad)
print(f'Occurrences of literal \\!= : {count_bad}')

if count_bad > 0:
    fixed = src.replace(bad, good)
    # Verify fix
    still_bad = fixed.count(bad)
    print(f'After fix: {still_bad} remaining')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(fixed)
    print('calidad_html.py written with fix')
else:
    print('No \\!= found — checking for other issues')
    # Look at what's actually around the != operators
    for m in re.finditer(r'.{0,3}!=.{0,3}', src[max(0,idx-50):idx+150] if idx != -1 else src[:500]):
        print('  match:', repr(m.group()))
