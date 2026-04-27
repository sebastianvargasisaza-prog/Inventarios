"""
patch_auth_roles.py
====================
Aplica control de acceso completo al sistema:
  - Todas las rutas HTML requieren login
  - Cada módulo restringe por rol
  - auth.py recibe helper sin_acceso_html()
  - config.py recibe nuevos sets de acceso

Ejecutar desde VM:
  python3 /sessions/magical-great-cray/mnt/Inventarios/patch_auth_roles.py
"""

import os
import sys

BASE = '/tmp/inv_p8/api'

def read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def patch(path, old, new, label):
    txt = read(path)
    if old not in txt:
        print(f'  [FAIL] {label} — cadena NO encontrada en {path}')
        print(f'         Buscando: {repr(old[:80])}')
        sys.exit(1)
    count = txt.count(old)
    if count > 1:
        print(f'  [WARN] {label} — cadena aparece {count} veces, reemplazando todas')
    txt = txt.replace(old, new)
    write(path, txt)
    print(f'  [OK] {label}')

# ──────────────────────────────────────────────────────────────────────────────
# PASO 1 — config.py: actualizar y agregar sets de acceso
# ──────────────────────────────────────────────────────────────────────────────
print('\n=== PASO 1: config.py ===')
cfg = os.path.join(BASE, 'config.py')

# RRHH_USERS: agregar admins
patch(cfg,
    'RRHH_USERS      = {"gloria", "daniela", "luz", "mayra"}',
    'RRHH_USERS      = {"gloria", "daniela", "luz", "mayra", "alejandro", "sebastian"}',
    'RRHH_USERS + admins')

# CALIDAD_USERS: agregar admins
patch(cfg,
    'CALIDAD_USERS   = {"laura", "miguel", "yuliel"}',
    'CALIDAD_USERS   = {"laura", "miguel", "yuliel", "alejandro", "sebastian"}',
    'CALIDAD_USERS + admins')

# COMPRAS_ACCESS: agregar daniela
patch(cfg,
    'COMPRAS_ACCESS  = {"luz", "catalina", "mayra", "alejandro", "sebastian"}',
    'COMPRAS_ACCESS  = {"luz", "catalina", "mayra", "daniela", "alejandro", "sebastian"}',
    'COMPRAS_ACCESS + daniela')

# FINANZAS_ACCESS: agregar bloque CLIENTES_ACCESS y TECNICA_USERS después
patch(cfg,
    'FINANZAS_ACCESS = {"mayra", "catalina", "sebastian", "alejandro"}',
    ('FINANZAS_ACCESS = {"mayra", "catalina", "sebastian", "alejandro"}\n'
     'CLIENTES_ACCESS = {"mayra", "luz", "catalina", "valentina", "daniela", "alejandro", "sebastian"}\n'
     'TECNICA_USERS   = {"hernando", "miguel", "alejandro", "sebastian"}'),
    'Agregar CLIENTES_ACCESS + TECNICA_USERS')

# ──────────────────────────────────────────────────────────────────────────────
# PASO 2 — auth.py: agregar helper sin_acceso_html()
# ──────────────────────────────────────────────────────────────────────────────
print('\n=== PASO 2: auth.py ===')
auth = os.path.join(BASE, 'auth.py')

patch(auth,
    'def register_hooks(app):',
    ('def sin_acceso_html(modulo):\n'
     '    """Pagina de acceso denegado consistente para todos los modulos."""\n'
     '    return (\n'
     '        \'<!DOCTYPE html><html><head><meta charset=UTF-8>\'\n'
     '        \'<title>Sin acceso</title>\'\n'
     '        \'<style>body{font-family:sans-serif;background:#0f172a;color:#fff;display:flex;\'\n'
     '        \'align-items:center;justify-content:center;height:100vh;margin:0;flex-direction:column;gap:16px;}\'\n'
     '        \'.card{background:#1e293b;border:1px solid #334155;border-radius:16px;padding:40px;\'\n'
     '        \'text-align:center;max-width:400px;}\'\n'
     '        \'h2{color:#f59e0b;margin:0 0 12px;}p{color:#94a3b8;margin:0 0 20px;}\'\n'
     '        \'a{display:inline-block;background:#667eea;color:#fff;text-decoration:none;\'\n'
     '        \'padding:10px 24px;border-radius:8px;font-weight:600;}</style></head>\'\n'
     '        f\'<body><div class="card"><h2>Acceso restringido</h2>\'\n'
     '        f\'<p>El modulo de {modulo} no esta disponible para tu usuario.</p>\'\n'
     '        \'<a href="/hub">Volver al escritorio</a></div></body></html>\'\n'
     '    )\n'
     '\n'
     '\n'
     'def register_hooks(app):'),
    'sin_acceso_html() helper')

# ──────────────────────────────────────────────────────────────────────────────
# PASO 3 — core.py: proteger /, /hub, /inventarios
# ──────────────────────────────────────────────────────────────────────────────
print('\n=== PASO 3: core.py ===')
core = os.path.join(BASE, 'blueprints/core.py')

# Actualizar import desde config (agregar CLIENTES_ACCESS)
patch(core,
    'from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, PLANTA_USERS, CALIDAD_USERS, COMPRAS_ACCESS',
    'from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, PLANTA_USERS, CALIDAD_USERS, COMPRAS_ACCESS, CLIENTES_ACCESS',
    'core.py import CLIENTES_ACCESS')

# Actualizar import desde auth (agregar sin_acceso_html)
patch(core,
    'from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec',
    'from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec, sin_acceso_html',
    'core.py import sin_acceso_html')

# / → redirigir a login si no hay sesión, a /hub si sí
patch(core,
    ('@bp.route(\'/\')\n'
     'def index():\n'
     '    return Response(HOME_HTML, mimetype=\'text/html\')'),
    ('@bp.route(\'/\')\n'
     'def index():\n'
     '    # Redirigir a login si no hay sesion activa; a /hub si ya esta autenticado\n'
     '    if \'compras_user\' not in session:\n'
     '        return redirect(\'/login\')\n'
     '    return redirect(\'/hub\')'),
    'Proteger / con redirect a login')

# /hub → require session
patch(core,
    ('@bp.route(\'/hub\')\n'
     'def hub():\n'
     '    from templates_py.hub_html import HUB_HTML\n'
     '    return Response(HUB_HTML, mimetype=\'text/html\')'),
    ('@bp.route(\'/hub\')\n'
     'def hub():\n'
     '    if \'compras_user\' not in session:\n'
     '        return redirect(\'/login?next=/hub\')\n'
     '    from templates_py.hub_html import HUB_HTML\n'
     '    return Response(HUB_HTML, mimetype=\'text/html\')'),
    'Proteger /hub con session check')

# /inventarios, /planta → require session
patch(core,
    ('@bp.route(\'/inventarios\')\n'
     '@bp.route(\'/planta\')\n'
     'def inventarios():\n'
     '    usuario = session.get(\'compras_user\', \'\').capitalize()'),
    ('@bp.route(\'/inventarios\')\n'
     '@bp.route(\'/planta\')\n'
     'def inventarios():\n'
     '    if \'compras_user\' not in session:\n'
     '        return redirect(\'/login?next=/inventarios\')\n'
     '    usuario = session.get(\'compras_user\', \'\').capitalize()'),
    'Proteger /inventarios con session check')

# /compras: actualizar redirect a /login?next=/compras (consistencia)
patch(core,
    ('    if \'compras_user\' not in session:\n'
     '        return redirect(\'/login\')\n'
     '    username = session.get(\'compras_user\', \'\')\n'
     '    # Solo usuarios con acceso a compras\n'
     '    if username not in COMPRAS_ACCESS:'),
    ('    if \'compras_user\' not in session:\n'
     '        return redirect(\'/login?next=/compras\')\n'
     '    username = session.get(\'compras_user\', \'\')\n'
     '    # Solo usuarios con acceso a compras\n'
     '    if username not in COMPRAS_ACCESS:'),
    '/compras redirect preserva ?next=')

# ──────────────────────────────────────────────────────────────────────────────
# PASO 4 — hub.py: proteger /compromisos
# ──────────────────────────────────────────────────────────────────────────────
print('\n=== PASO 4: hub.py ===')
hub = os.path.join(BASE, 'blueprints/hub.py')

patch(hub,
    ('@bp.route(\'/compromisos\')\n'
     'def compromisos_page():\n'
     '    return Response(COMPROMISOS_HTML, mimetype=\'text/html\')'),
    ('@bp.route(\'/compromisos\')\n'
     'def compromisos_page():\n'
     '    if \'compras_user\' not in session:\n'
     '        return redirect(\'/login?next=/compromisos\')\n'
     '    return Response(COMPROMISOS_HTML, mimetype=\'text/html\')'),
    'Proteger /compromisos')

# hub.py necesita session y redirect importados
patch(hub,
    'from flask import Blueprint, jsonify, request, Response, session, redirect',
    'from flask import Blueprint, jsonify, request, Response, session, redirect',
    'hub.py flask imports ya correctos (no-op)')

# ──────────────────────────────────────────────────────────────────────────────
# PASO 5 — calidad.py: proteger /calidad + check CALIDAD_USERS
# ──────────────────────────────────────────────────────────────────────────────
print('\n=== PASO 5: calidad.py ===')
cal = os.path.join(BASE, 'blueprints/calidad.py')

# Actualizar import desde config
patch(cal,
    'from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS',
    'from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, CALIDAD_USERS',
    'calidad.py import CALIDAD_USERS')

# Actualizar import desde auth
patch(cal,
    'from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec',
    'from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec, sin_acceso_html',
    'calidad.py import sin_acceso_html')

# Agregar imports de Flask si redirect no está
cal_txt = read(cal)
if 'redirect' not in cal_txt.split('from flask import')[1].split('\n')[0]:
    patch(cal,
        'from flask import Blueprint, jsonify, request, Response, session',
        'from flask import Blueprint, jsonify, request, Response, session, redirect',
        'calidad.py agregar redirect a flask imports')

# Proteger /calidad con session + rol
patch(cal,
    ('@bp.route(\'/calidad\')\n'
     'def calidad_page():\n'
     '    return Response(CALIDAD_HTML, mimetype=\'text/html\')'),
    ('@bp.route(\'/calidad\')\n'
     'def calidad_page():\n'
     '    if \'compras_user\' not in session:\n'
     '        return redirect(\'/login?next=/calidad\')\n'
     '    u = session.get(\'compras_user\', \'\')\n'
     '    if u not in CALIDAD_USERS:\n'
     '        return Response(sin_acceso_html(\'Calidad BPM\'), mimetype=\'text/html\')\n'
     '    return Response(CALIDAD_HTML, mimetype=\'text/html\')'),
    'Proteger /calidad con session + rol')

# ──────────────────────────────────────────────────────────────────────────────
# PASO 6 — despachos.py: proteger /recepcion
# ──────────────────────────────────────────────────────────────────────────────
print('\n=== PASO 6: despachos.py ===')
des = os.path.join(BASE, 'blueprints/despachos.py')

# Agregar redirect a flask imports si no existe
des_txt = read(des)
flask_import_line = des_txt.split('from flask import')[1].split('\n')[0]
if 'redirect' not in flask_import_line:
    patch(des,
        'from flask import Blueprint, jsonify, request, Response, session',
        'from flask import Blueprint, jsonify, request, Response, session, redirect',
        'despachos.py agregar redirect')

patch(des,
    ('@bp.route(\'/recepcion\')\n'
     'def recepcion_panel():\n'
     '    return Response(RECEPCION_HTML, mimetype=\'text/html\')'),
    ('@bp.route(\'/recepcion\')\n'
     'def recepcion_panel():\n'
     '    if \'compras_user\' not in session:\n'
     '        return redirect(\'/login?next=/recepcion\')\n'
     '    return Response(RECEPCION_HTML, mimetype=\'text/html\')'),
    'Proteger /recepcion')

# ──────────────────────────────────────────────────────────────────────────────
# PASO 7 — maquila.py: proteger /hub-salida
# ──────────────────────────────────────────────────────────────────────────────
print('\n=== PASO 7: maquila.py ===')
maq = os.path.join(BASE, 'blueprints/maquila.py')

maq_txt = read(maq)
flask_import_line = maq_txt.split('from flask import')[1].split('\n')[0]
if 'redirect' not in flask_import_line:
    patch(maq,
        'from flask import Blueprint, jsonify, request, Response, session',
        'from flask import Blueprint, jsonify, request, Response, session, redirect',
        'maquila.py agregar redirect')

patch(maq,
    ('@bp.route(\'/hub-salida\')\n'
     'def hub_salida_page():\n'
     '    return Response(SALIDA_HTML, mimetype=\'text/html\')'),
    ('@bp.route(\'/hub-salida\')\n'
     'def hub_salida_page():\n'
     '    if \'compras_user\' not in session:\n'
     '        return redirect(\'/login?next=/hub-salida\')\n'
     '    return Response(SALIDA_HTML, mimetype=\'text/html\')'),
    'Proteger /hub-salida')

# ──────────────────────────────────────────────────────────────────────────────
# PASO 8 — tecnica.py: fix _check_access() para verificar sesión + TECNICA_USERS
# ──────────────────────────────────────────────────────────────────────────────
print('\n=== PASO 8: tecnica.py ===')
tec = os.path.join(BASE, 'blueprints/tecnica.py')

# Actualizar import desde config para agregar TECNICA_USERS
patch(tec,
    'from config import DB_PATH, ADMIN_USERS',
    'from config import DB_PATH, ADMIN_USERS, TECNICA_USERS',
    'tecnica.py import TECNICA_USERS')

# Agregar sin_acceso_html a auth imports
patch(tec,
    'from flask import Blueprint, jsonify, request, Response, session, redirect',
    'from flask import Blueprint, jsonify, request, Response, session, redirect\n'
    'from auth import sin_acceso_html',
    'tecnica.py import sin_acceso_html')

# Fix _check_access(): reemplazar return True por verificación real
patch(tec,
    ('def _check_access():\n'
     '    return True  # auth eliminada — solo compras/gerencia requieren login'),
    ('def _check_access():\n'
     '    """Verifica sesion activa y pertenencia a TECNICA_USERS o ADMIN_USERS."""\n'
     '    u = session.get(\'compras_user\', \'\')\n'
     '    return bool(u) and (u in TECNICA_USERS or u in ADMIN_USERS)'),
    'tecnica.py fix _check_access()')

# La ruta /tecnica ya llama _check_access() y hace redirect — solo verificar el redirect to login
tec_txt = read(tec)
if "redirect('/login" not in tec_txt:
    patch(tec,
        '        return redirect(\'/login?next=/tecnica\')',
        '        return redirect(\'/login?next=/tecnica\')',
        'tecnica.py redirect ya existe')

# Asegurar que la ruta /tecnica también retorna sin_acceso_html cuando hay sesión pero sin rol
# Leer el estado actual de la ruta
if "sin_acceso_html" not in read(tec):
    patch(tec,
        ('    if not _check_access():\n'
         '        return redirect(\'/login?next=/tecnica\')\n'
         '    return Response(TECNICA_HTML, mimetype=\'text/html\')'),
        ('    if \'compras_user\' not in session:\n'
         '        return redirect(\'/login?next=/tecnica\')\n'
         '    if not _check_access():\n'
         '        return Response(sin_acceso_html(\'Tecnica\'), mimetype=\'text/html\')\n'
         '    return Response(TECNICA_HTML, mimetype=\'text/html\')'),
        'tecnica.py separar check sesion vs check rol')

# ──────────────────────────────────────────────────────────────────────────────
# PASO 9 — clientes.py: agregar check de CLIENTES_ACCESS (ya tiene session check)
# ──────────────────────────────────────────────────────────────────────────────
print('\n=== PASO 9: clientes.py ===')
cli = os.path.join(BASE, 'blueprints/clientes.py')

# Actualizar import desde config
patch(cli,
    'from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS',
    'from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, CLIENTES_ACCESS',
    'clientes.py import CLIENTES_ACCESS')

# Actualizar import desde auth
patch(cli,
    'from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec',
    'from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec, sin_acceso_html',
    'clientes.py import sin_acceso_html')

# Agregar check de rol después del check de sesión
patch(cli,
    ('def clientes_page():\n'
     '    if \'compras_user\' not in session:\n'
     '        return redirect(url_for(\'core.login\'))\n'
     '    return Response(CLIENTES_HTML, mimetype=\'text/html\')'),
    ('def clientes_page():\n'
     '    if \'compras_user\' not in session:\n'
     '        return redirect(\'/login?next=/clientes\')\n'
     '    u = session.get(\'compras_user\', \'\')\n'
     '    if u not in CLIENTES_ACCESS:\n'
     '        return Response(sin_acceso_html(\'Clientes\'), mimetype=\'text/html\')\n'
     '    return Response(CLIENTES_HTML, mimetype=\'text/html\')'),
    'clientes.py agregar check CLIENTES_ACCESS')

# ──────────────────────────────────────────────────────────────────────────────
# PASO 10 — rrhh.py: proteger /rrhh + check RRHH_USERS
# ──────────────────────────────────────────────────────────────────────────────
print('\n=== PASO 10: rrhh.py ===')
rrhh = os.path.join(BASE, 'blueprints/rrhh.py')

# Actualizar import desde auth
patch(rrhh,
    'from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec',
    'from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec, sin_acceso_html',
    'rrhh.py import sin_acceso_html')

# Agregar ADMIN_USERS al import de config
patch(rrhh,
    'from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, RRHH_USERS',
    'from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, RRHH_USERS',
    'rrhh.py config imports ya correctos (no-op)')

# Agregar redirect a flask imports
rrhh_txt = read(rrhh)
flask_line = rrhh_txt.split('from flask import')[1].split('\n')[0]
if 'redirect' not in flask_line:
    patch(rrhh,
        rrhh_txt.split('\n')[rrhh_txt.split('\n').index(
            next(l for l in rrhh_txt.split('\n') if l.startswith('from flask import')))],
        None,  # skip
        'rrhh.py verificar flask imports')

# Usar replace directo en la linea de flask import
rrhh_txt2 = read(rrhh)
old_flask = [l for l in rrhh_txt2.split('\n') if l.startswith('from flask import')][0]
if 'redirect' not in old_flask:
    patch(rrhh, old_flask, old_flask.rstrip() + ', redirect', 'rrhh.py agregar redirect')

# Proteger /rrhh con session + RRHH_USERS check
patch(rrhh,
    ('@bp.route("/rrhh")\n'
     'def rrhh_panel():\n'
     '    u = session.get("compras_user", "")\n'
     '    usuario = u.capitalize()\n'
     '    return Response(RRHH_HTML.replace("{usuario}", usuario), mimetype="text/html")'),
    ('@bp.route("/rrhh")\n'
     'def rrhh_panel():\n'
     '    if "compras_user" not in session:\n'
     '        return redirect("/login?next=/rrhh")\n'
     '    u = session.get("compras_user", "")\n'
     '    if u not in RRHH_USERS:\n'
     '        return Response(sin_acceso_html("Recursos Humanos"), mimetype="text/html")\n'
     '    usuario = u.capitalize()\n'
     '    return Response(RRHH_HTML.replace("{usuario}", usuario), mimetype="text/html")'),
    'Proteger /rrhh con session + rol')

# ──────────────────────────────────────────────────────────────────────────────
# VERIFICACIÓN FINAL
# ──────────────────────────────────────────────────────────────────────────────
print('\n=== VERIFICACIÓN FINAL ===')

checks = [
    (os.path.join(BASE, 'config.py'), 'CLIENTES_ACCESS', 'config.py tiene CLIENTES_ACCESS'),
    (os.path.join(BASE, 'config.py'), 'TECNICA_USERS', 'config.py tiene TECNICA_USERS'),
    (os.path.join(BASE, 'config.py'), '"daniela"', 'config.py COMPRAS_ACCESS tiene daniela'),
    (os.path.join(BASE, 'auth.py'), 'sin_acceso_html', 'auth.py tiene sin_acceso_html'),
    (os.path.join(BASE, 'blueprints/core.py'), "redirect('/login')\n    return redirect('/hub')", 'core.py / redirige a login'),
    (os.path.join(BASE, 'blueprints/core.py'), "redirect('/login?next=/hub')", 'core.py /hub protegido'),
    (os.path.join(BASE, 'blueprints/core.py'), "redirect('/login?next=/inventarios')", 'core.py /inventarios protegido'),
    (os.path.join(BASE, 'blueprints/hub.py'), "redirect('/login?next=/compromisos')", 'hub.py /compromisos protegido'),
    (os.path.join(BASE, 'blueprints/calidad.py'), 'CALIDAD_USERS', 'calidad.py usa CALIDAD_USERS'),
    (os.path.join(BASE, 'blueprints/despachos.py'), "redirect('/login?next=/recepcion')", 'despachos.py /recepcion protegido'),
    (os.path.join(BASE, 'blueprints/maquila.py'), "redirect('/login?next=/hub-salida')", 'maquila.py /hub-salida protegido'),
    (os.path.join(BASE, 'blueprints/tecnica.py'), 'TECNICA_USERS', 'tecnica.py usa TECNICA_USERS'),
    (os.path.join(BASE, 'blueprints/tecnica.py'), "return True  # auth eliminada", ''),  # debe NO existir
    (os.path.join(BASE, 'blueprints/clientes.py'), 'CLIENTES_ACCESS', 'clientes.py usa CLIENTES_ACCESS'),
    (os.path.join(BASE, 'blueprints/rrhh.py'), "redirect(\"/login?next=/rrhh\")", 'rrhh.py /rrhh protegido'),
]

errors = 0
for path, needle, label in checks:
    if not label:  # check negativo
        if needle in read(path):
            print(f'  [FAIL] tecnica.py todavia tiene "return True" hardcodeado')
            errors += 1
        continue
    if needle not in read(path):
        print(f'  [FAIL] {label}')
        errors += 1
    else:
        print(f'  [OK] {label}')

if errors == 0:
    print('\n✅ PATCH COMPLETO — 10 archivos actualizados, 0 errores')
    print('Siguiente paso: git add, commit, push desde /tmp/inv_p8')
else:
    print(f'\n❌ {errors} verificaciones fallaron — revisar antes de push')
    sys.exit(1)
