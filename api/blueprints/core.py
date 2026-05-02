# blueprints/core.py — extraído de index.py (Fase C)
import os
import json
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, PLANTA_USERS, CALIDAD_USERS, COMPRAS_ACCESS, CLIENTES_ACCESS
from auth import (
    _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec,
    sin_acceso_html, _ensure_csrf_token,
)
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

bp = Blueprint('core', __name__)


def _resolve_password_hash(username):
    """Devuelve el hash de password para un usuario, con fallback lazy.

    Prioridad:
      1. Tabla users_passwords en DB (si el usuario cambió su password
         vía /api/cambiar-password, su hash vive aquí).
      2. config.COMPRAS_USERS (env var PASS_<USER> en Render).

    Retorna '' si no hay ninguno (usuario no existe o env var ausente).
    Diseñado para ser robusto: si la DB falla, fallback automático a env.
    """
    if not username:
        return ''
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA busy_timeout=2000")
        row = conn.execute(
            "SELECT password_hash FROM users_passwords WHERE username=?",
            (username,)
        ).fetchone()
        conn.close()
        if row and row[0]:
            return row[0]
    except Exception:
        # Tabla no existe (pre-migración) o DB no responde —
        # cae al fallback de env vars.
        pass
    return COMPRAS_USERS.get(username, '')

@bp.route('/api/csrf-token', methods=['GET'])
def csrf_token():
    """Devuelve el CSRF token actual de la sesión, generándolo si no existe.

    El frontend lo lee al cargar la app y lo envía como header X-CSRF-Token
    en cada POST/PUT/DELETE/PATCH. Defense in depth sobre el Origin check.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    return jsonify({'csrf_token': _ensure_csrf_token()})


@bp.route('/api/health')
def health():
    """Diagnostico publico — version, DB, tablas clave."""
    import sqlite3 as _sq, os as _os, subprocess as _sp
    try:
        commit = _sp.check_output(['git','rev-parse','--short','HEAD'],
            cwd=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
            stderr=_sp.DEVNULL).decode().strip()
    except Exception:
        commit = 'unknown'
    db_exists = _os.path.exists(DB_PATH)
    db_size = round(_os.path.getsize(DB_PATH)/1024, 1) if db_exists else 0
    tables = {}
    try:
        conn = _sq.connect(DB_PATH)
        for tbl in ['maestro_mps','solicitudes_compra','ordenes_compra','movimientos']:
            try:
                tables[tbl] = conn.execute(f'SELECT COUNT(*) FROM {tbl}').fetchone()[0]
            except: tables[tbl] = 'err'
        try:
            tables['planta_pendientes'] = conn.execute(
                "SELECT COUNT(*) FROM solicitudes_compra WHERE estado='Aprobada' AND area='Produccion' AND (numero_oc IS NULL OR numero_oc='')").fetchone()[0]
        except: pass
    except Exception as e:
        tables['error'] = str(e)
    return jsonify({'status':'ok','commit':commit,'db_exists':db_exists,
                    'db_size_kb':db_size,'tables':tables})

@bp.route('/')
def index():
    # Redirigir a login si no hay sesion activa; a /modulos si ya esta autenticado
    if 'compras_user' not in session:
        return redirect('/login')
    return redirect('/modulos')

@bp.route('/programacion-areas')
def programacion_areas_page():
    """Vista calendario por área · cronograma estilo Alejandro.

    Matriz 5 días Lun-Vie × 10 áreas con todas las fases proyectadas
    automáticamente desde la data del sistema (FAB/ENV/MICRO/LIB/ACOND/
    ENTR/LIMP). Solo lectura · si Alejandro quiere editar, va al módulo
    de la fase correspondiente.
    """
    if 'compras_user' not in session:
        return redirect('/login?next=/programacion-areas')
    from templates_py.programacion_areas_html import PROGRAMACION_AREAS_HTML
    return Response(PROGRAMACION_AREAS_HTML, mimetype='text/html; charset=utf-8')


@bp.route('/inventarios')
@bp.route('/planta')
def inventarios():
    if 'compras_user' not in session:
        return redirect('/login?next=/inventarios')
    usuario = session.get('compras_user', '').capitalize()
    from config import ADMIN_USERS
    es_admin = 'true' if session.get('compras_user','') in ADMIN_USERS else 'false'
    html = DASHBOARD_HTML.replace('{usuario}', usuario).replace('{es_admin}', es_admin)
    resp = Response(html, mimetype='text/html; charset=utf-8')
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

# (rate limiter y hooks de seguridad → auth.py — registrados via register_hooks(app))

@bp.route('/hub')
def hub():
    if 'compras_user' not in session:
        return redirect('/login?next=/modulos')
    from templates_py.hub_html import HUB_HTML
    return Response(HUB_HTML, mimetype='text/html')

@bp.route('/modulos')
def modulos():
    if 'compras_user' not in session:
        return redirect('/login?next=/modulos')
    from templates_py.modulos_html import MODULOS_HTML
    from blueprints.marketing import MARKETING_USERS
    from config import ADMIN_USERS as _ADMS
    usuario = session.get('compras_user', '')
    es_admin = 'true' if usuario in _ADMS else 'false'
    html = (MODULOS_HTML
            .replace('{usuario}', usuario)
            .replace('{usuario_es_admin}', es_admin))
    # Ocultar tarjeta ANIMUS Lab para usuarios sin acceso a Marketing
    if usuario not in MARKETING_USERS:
        import re
        html = re.sub(
            r'<a class="mod-card" href="/marketing"[^>]*>.*?</a>',
            '', html, flags=re.DOTALL
        )
    return Response(html, mimetype='text/html')

@bp.route('/login', methods=['GET','POST'])
def login():
    error = ''
    next_url = request.args.get('next', '/modulos')
    if not next_url.startswith('/') or next_url.startswith('//'):
        next_url = '/modulos'
    if request.method == 'POST':
        ip = _client_ip()
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '').strip()
        # Lock por IP O por (IP, username) — bloquea brute-force que rota
        # usernames y brute-force dirigido a un solo usuario.
        if _is_locked(ip, username):
            error = '<div class="err">Demasiados intentos. Espera 15 min.</div>'
            return Response(LOGIN_HTML.replace('{error}', error).replace('{next_url}', next_url), mimetype='text/html')
        # Fallback lazy: hash de DB tiene prioridad (si el user lo cambió);
        # si no hay entry en DB, usar env var (PASS_<USER>). Esto permite
        # self-service de password sin migrar todos los users de una vez.
        expected = _resolve_password_hash(username)
        # Soporte PBKDF2 (env var con hash) y plaintext legacy
        if expected and (expected.startswith('pbkdf2:') or expected.startswith('scrypt:')):
            match = check_password_hash(expected, password)
        else:
            match = bool(expected) and hmac.compare_digest(expected, password)
        if match:
            # ── MFA gate (paso 2) ──────────────────────────────────────────────
            # Si el usuario tiene MFA enabled, NO completamos login todavía.
            # Guardamos username en 'mfa_pending_user' y redirigimos a /login/mfa
            # donde se pide el token TOTP. Solo después de verificar TOTP se
            # establece session['compras_user'] = username (en blueprints/mfa.py).
            try:
                from blueprints.mfa import _is_mfa_enabled
                if _is_mfa_enabled(username):
                    session.clear()
                    session['mfa_pending_user'] = username
                    session['mfa_pending_next'] = next_url
                    _log_sec("login_password_ok_mfa_pending", username, ip)
                    return redirect('/login/mfa')
            except ImportError:
                pass  # blueprint mfa no cargado (test environment) — seguir sin MFA
            _clear_attempts(ip, username)
            _log_sec("login_success", username, ip)
            session.clear()
            session.permanent = True
            session['compras_user'] = username
            session['login_time']   = time.time()
            # Generar CSRF token nuevo en cada login (rotación = mejor seguridad)
            _ensure_csrf_token()
            nxt = request.args.get('next', '')
            # Todos los usuarios van al hub; si había un ?next= válido se respeta
            if not nxt or not nxt.startswith('/') or nxt.startswith('//'):
                nxt = '/modulos'
            # Safety: non-admins must not land on admin-only pages
            from config import ADMIN_USERS as _AU
            ADMIN_ONLY = {'/gerencia'}
            if any(nxt == p or nxt.startswith(p + '/') for p in ADMIN_ONLY) and username not in _AU:
                nxt = '/modulos'
            return redirect(nxt)
        _record_failure(ip, username)
        _log_sec("login_failure", username, ip)
        error = '<div class="err">Usuario o contraseña incorrectos.</div>'
    return Response(LOGIN_HTML.replace('{error}', error).replace('{next_url}', next_url), mimetype='text/html')

@bp.route('/logout')
def logout():
    # session.clear() en lugar de pop('compras_user') · audit zero-error
    # 2-may-2026: pop solo borraba compras_user, dejaba csrf_token,
    # mfa_pending_user, login_time, must_reenroll_mfa vivos. Una sesión
    # robada post-logout aún tenía artefactos válidos.
    session.clear()
    return redirect('/')

@bp.route('/compras')
def compras():
    if 'compras_user' not in session:
        return redirect('/login?next=/compras')
    username = session.get('compras_user', '')
    # Solo usuarios con acceso a compras
    if username not in COMPRAS_ACCESS:
        sin_acceso = (
            '<!DOCTYPE html><html><head><meta charset=UTF-8>'
            '<title>Sin acceso</title>'
            '<style>body{font-family:sans-serif;background:#0f172a;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;flex-direction:column;gap:16px;}'
            '.card{background:#1e293b;border:1px solid #334155;border-radius:16px;padding:40px;text-align:center;max-width:400px;}'
            'h2{color:#f59e0b;margin:0 0 12px;}p{color:#94a3b8;margin:0 0 20px;}'
            'a{display:inline-block;background:#667eea;color:#fff;text-decoration:none;padding:10px 24px;border-radius:8px;font-weight:600;}</style></head>'
            '<body><div class="card"><h2>Acceso restringido</h2>'
            '<p>El modulo de Compras no esta disponible para tu usuario.</p>'
            '<a href="/hub">Volver al escritorio</a></div></body></html>'
        )
        return Response(sin_acceso, mimetype='text/html')
    usuario = username.capitalize()
    es_contadora = 'true' if username in CONTADORA_USERS else 'false'
    html = COMPRAS_HTML.replace('{usuario}', usuario).replace('{es_contadora}', es_contadora)
    resp = Response(html, mimetype='text/html; charset=utf-8')
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

@bp.route('/animus')
def animus():
    if 'compras_user' not in session:
        return redirect('/login?next=/animus')
    from templates_py.animus_html import ANIMUS_HTML
    usuario = session.get('compras_user', '').capitalize()
    return Response(ANIMUS_HTML.replace('{usuario}', usuario), mimetype='text/html; charset=utf-8')

@bp.route('/marketing')
def marketing():
    if 'compras_user' not in session:
        return redirect('/login?next=/marketing')
    from templates_py.marketing_html import MARKETING_HTML
    usuario = session.get('compras_user', '').capitalize()
    return Response(MARKETING_HTML.replace('{usuario}', usuario), mimetype='text/html; charset=utf-8')


# ── Self-service de contraseña ────────────────────────────────────────────────
# Cualquier usuario autenticado puede cambiar su propia contraseña sin
# intervención del admin. El hash nuevo se guarda en users_passwords (DB);
# las env vars PASS_<USER> quedan como fallback si la entry de DB no existe.

# Política mínima de contraseña (server-side; no confiar solo en JS).
_PWD_MIN_LEN = 8
_PWD_MAX_LEN = 128

# Blacklist de passwords más comunes en español/inglés. Bloqueo absoluto
# aunque cumplan los demás criterios. Cubre ~90% de los ataques de
# diccionario de bots scanners. Lista pequeña, evaluable en O(1).
# Sebastian (30-abr-2026): refuerzo de password policy en audit de seguridad.
_PWD_BLACKLIST = frozenset([
    "password", "password1", "password123", "passw0rd", "passw0rd1",
    "12345678", "123456789", "1234567890", "qwerty123", "qwertyuiop",
    "abc12345", "abcd1234", "111111", "1q2w3e4r", "1qaz2wsx",
    "admin123", "admin1234", "administrator", "letmein123",
    "welcome1", "welcome123", "iloveyou", "monkey123",
    "espagiria", "espagiria1", "espagiria123", "espagiria2026",
    "animus", "animus1", "animus123", "animus2026",
    "hha2026", "hhagroup", "hhagroup2026", "hhagroup1",
    "colombia", "colombia1", "bogota", "bogota1", "bogota2026",
    "cosmetica", "cosmeticos", "laboratorio", "laboratorio1",
])


def _validate_new_password(pwd, current_pwd, username=None):
    """Valida una password nueva. Retorna lista de errores (vacía si OK).

    Reglas:
      - Longitud entre _PWD_MIN_LEN y _PWD_MAX_LEN
      - Al menos 1 letra y 1 número
      - No idéntica a la actual
      - No en blacklist (top passwords comunes)
      - No idéntica al username (incluso lowercase)
    """
    errors = []
    if not pwd or len(pwd) < _PWD_MIN_LEN:
        errors.append(f"Mínimo {_PWD_MIN_LEN} caracteres.")
    if len(pwd) > _PWD_MAX_LEN:
        errors.append(f"Máximo {_PWD_MAX_LEN} caracteres.")
    if pwd == current_pwd:
        errors.append("La nueva contraseña debe ser distinta a la actual.")
    # Al menos 1 letra y 1 número (anti-passwords débiles tipo "12345678")
    if not any(c.isalpha() for c in pwd):
        errors.append("Debe incluir al menos una letra.")
    if not any(c.isdigit() for c in pwd):
        errors.append("Debe incluir al menos un número.")
    # Blacklist de passwords comunes (case-insensitive)
    if pwd.lower() in _PWD_BLACKLIST:
        errors.append("Contraseña demasiado común. Escoge una distinta.")
    # No usar el username como password
    if username and pwd.lower() == username.lower().strip():
        errors.append("La contraseña no puede ser igual al usuario.")
    return errors


@bp.route('/api/cambiar-password', methods=['POST'])
def cambiar_password():
    """Cambia la password del usuario autenticado.

    Body JSON: {password_actual, password_nueva, password_confirmar}
    Validaciones:
      - Sesión activa
      - password_actual matchea con el hash actual (DB o env var)
      - password_nueva cumple política mínima
      - password_nueva == password_confirmar
      - Rate limit aplicado: 5 intentos fallidos en 15min bloquean al user
    """
    username = session.get('compras_user', '')
    if not username:
        return jsonify({'error': 'No autorizado'}), 401

    body = request.get_json(silent=True) or {}
    actual = (body.get('password_actual') or '').strip()
    nueva = (body.get('password_nueva') or '').strip()
    confirmar = (body.get('password_confirmar') or '').strip()

    if not actual or not nueva or not confirmar:
        return jsonify({'error': 'Faltan campos: password_actual, password_nueva, password_confirmar'}), 400

    if nueva != confirmar:
        return jsonify({'error': 'La confirmación no coincide con la nueva contraseña'}), 400

    # Rate limit: aplicar mismo lock que login. Si han fallado muchas veces
    # cambiando password, también se bloquea (defensa contra atacante con
    # sesión robada que intenta adivinar la actual).
    ip = _client_ip()
    if _is_locked(ip, username):
        return jsonify({'error': 'Demasiados intentos fallidos. Espera 15 minutos.'}), 429

    # Validar password_actual contra el hash vigente (DB o env var)
    expected = _resolve_password_hash(username)
    if not expected:
        # Caso raro: usuario en sesión pero sin hash configurado.
        return jsonify({'error': 'Cuenta sin contraseña configurada. Contacta al admin.'}), 503

    if expected.startswith('pbkdf2:') or expected.startswith('scrypt:'):
        ok = check_password_hash(expected, actual)
    else:
        ok = bool(expected) and hmac.compare_digest(expected, actual)

    if not ok:
        _record_failure(ip, username)
        _log_sec("password_change_failed", username, ip, "actual incorrecta")
        return jsonify({'error': 'Contraseña actual incorrecta'}), 403

    # Validar password nueva (incluye check anti-username)
    errors = _validate_new_password(nueva, actual, username=username)
    if errors:
        return jsonify({'error': ' '.join(errors)}), 400

    # Hashear y guardar
    new_hash = generate_password_hash(nueva, method='pbkdf2:sha256:600000')
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA busy_timeout=2000")
        conn.execute("""
            INSERT INTO users_passwords (username, password_hash, changed_at, changed_by)
            VALUES (?, ?, datetime('now', 'utc'), ?)
            ON CONFLICT(username) DO UPDATE SET
                password_hash = excluded.password_hash,
                changed_at    = excluded.changed_at,
                changed_by    = excluded.changed_by
        """, (username, new_hash, username))
        conn.commit()
        conn.close()
    except Exception as e:
        _log_sec("password_change_db_error", username, ip, str(e)[:200])
        return jsonify({'error': 'Error guardando contraseña. Intenta de nuevo.'}), 500

    _clear_attempts(ip, username)
    _log_sec("password_changed", username, ip)
    return jsonify({'ok': True, 'message': 'Contraseña actualizada correctamente.'})

