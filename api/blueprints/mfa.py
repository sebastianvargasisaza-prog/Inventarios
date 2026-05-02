"""MFA TOTP — Multi-Factor Authentication via Time-based One-Time Password.

Sebastian (30-abr-2026): "que más hace crítica a una app que la haga
inestable y que no la quieran" — auditoría de seguridad. MFA es P0
para admins (control total con phishing exitoso = compromiso del holding).

Diseño:
- TOTP RFC 6238 con pyotp (Google Authenticator, Authy, 1Password compatible)
- Opt-in inicialmente. UI en /perfil/seguridad.
- Backup code (un solo código de emergencia) si se pierde el authenticator.
- Login flow de 2 pasos: si MFA enabled, después de password se pide TOTP.
- Disable: requiere password actual + token TOTP vigente.
- Si admin pierde MFA + backup code: otro admin puede deshabilitarlo
  via /api/mfa/admin-disable (defensa de bus factor).

Tabla: users_mfa(username, secret, enabled, backup_code_hash, ...).
Migration 57 en database.py.
"""
import sqlite3
import time
import secrets
import hmac
from flask import Blueprint, request, jsonify, session, redirect, Response
from werkzeug.security import generate_password_hash, check_password_hash

from config import DB_PATH, ADMIN_USERS
from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec

bp = Blueprint('mfa', __name__)


# ── Helpers internos ─────────────────────────────────────────────────────────

def _get_mfa_record(username):
    """Lee el registro MFA del usuario. Devuelve dict o None si no existe."""
    if not username:
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=2000")
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT username, secret, enabled, backup_code_hash, "
            "created_at, enabled_at, last_used_at, disabled_at "
            "FROM users_mfa WHERE username=?", (username,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _is_mfa_enabled(username):
    """True si el usuario tiene MFA activado y verificado."""
    rec = _get_mfa_record(username)
    return bool(rec and rec.get('enabled'))


def _verify_totp(secret, token):
    """Verifica un token TOTP de 6 dígitos contra el secret. Retorna bool.

    Acepta tokens del paso anterior y siguiente (window=1) para tolerar
    deriva de reloj de hasta ±30 segundos. Es el comportamiento estándar
    de pyotp y Google Authenticator.
    """
    try:
        import pyotp
    except ImportError:
        # pyotp no instalado — fallback seguro: rechaza todos los tokens.
        # Producción debe tener pyotp; este fallback solo para tests donde
        # la dependency pueda faltar.
        return False
    if not secret or not token:
        return False
    token = str(token).strip().replace(' ', '')
    if not token.isdigit() or len(token) != 6:
        return False
    try:
        return pyotp.TOTP(secret).verify(token, valid_window=1)
    except Exception:
        return False


def _gen_secret():
    """Genera un secret base32 de 160 bits (recomendado RFC 4226)."""
    import pyotp
    return pyotp.random_base32()


def _gen_backup_code():
    """Genera un código de respaldo de 12 caracteres alfanuméricos.

    Formato: XXXX-XXXX-XXXX (legible, fácil de transcribir). Se muestra
    UNA SOLA VEZ al usuario tras enrollment. El hash se guarda en DB.
    """
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sin caracteres ambiguos (0/O, 1/I/l)
    chars = [secrets.choice(alphabet) for _ in range(12)]
    return f"{''.join(chars[0:4])}-{''.join(chars[4:8])}-{''.join(chars[8:12])}"


def _provisioning_uri(username, secret):
    """Devuelve URI otpauth:// para escanear con la app authenticator.

    issuer = 'EOS HHA Group' aparece como nombre de la cuenta en el authenticator.
    """
    import pyotp
    return pyotp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name='EOS HHA Group'
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@bp.route('/api/mfa/status', methods=['GET'])
def mfa_status():
    """Devuelve el estado MFA del usuario en sesión."""
    username = session.get('compras_user', '')
    if not username:
        return jsonify({'error': 'No autorizado'}), 401
    rec = _get_mfa_record(username)
    return jsonify({
        'username': username,
        'mfa_enabled': bool(rec and rec.get('enabled')),
        'has_secret_pending': bool(rec and not rec.get('enabled')),
        'enabled_at': rec.get('enabled_at') if rec else None,
        'last_used_at': rec.get('last_used_at') if rec else None,
    })


@bp.route('/api/mfa/setup', methods=['POST'])
def mfa_setup():
    """Inicia el enrollment MFA. Genera secret nuevo (no activa todavía).

    Si ya hay MFA activo, devuelve 409 — primero hay que disable.
    Devuelve secret + provisioning_uri para mostrar QR/copiar al authenticator.
    """
    username = session.get('compras_user', '')
    if not username:
        return jsonify({'error': 'No autorizado'}), 401

    rec = _get_mfa_record(username)
    if rec and rec.get('enabled'):
        return jsonify({'error': 'MFA ya está activo. Desactívalo antes de re-enrollar.'}), 409

    try:
        secret = _gen_secret()
    except ImportError:
        return jsonify({'error': 'pyotp no instalado en el servidor.'}), 503

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=2000")
    try:
        conn.execute("""
            INSERT INTO users_mfa (username, secret, enabled, created_at)
            VALUES (?, ?, 0, datetime('now', 'utc'))
            ON CONFLICT(username) DO UPDATE SET
                secret      = excluded.secret,
                enabled     = 0,
                created_at  = datetime('now', 'utc'),
                enabled_at  = NULL
        """, (username, secret))
        conn.commit()
    finally:
        conn.close()

    _log_sec("mfa_setup_started", username, _client_ip())
    return jsonify({
        'secret': secret,                         # ← mostrar al usuario UNA vez
        'provisioning_uri': _provisioning_uri(username, secret),
        'issuer': 'EOS HHA Group',
        'account': username,
        'message': 'Escanea el QR o copia el secret en tu app authenticator. Luego ingresa el primer token de 6 dígitos.',
    })


@bp.route('/api/mfa/verify-setup', methods=['POST'])
def mfa_verify_setup():
    """Verifica el primer token TOTP y activa MFA. Genera backup code.

    Body: {token: '123456'}
    Devuelve: {ok: True, backup_code: 'XXXX-XXXX-XXXX'} ← MOSTRAR UNA VEZ
    """
    username = session.get('compras_user', '')
    if not username:
        return jsonify({'error': 'No autorizado'}), 401

    body = request.get_json(silent=True) or {}
    token = (body.get('token') or '').strip()

    rec = _get_mfa_record(username)
    if not rec:
        return jsonify({'error': 'No hay setup MFA pendiente. Inicia con /api/mfa/setup.'}), 400
    if rec.get('enabled'):
        return jsonify({'error': 'MFA ya está activo.'}), 409

    if not _verify_totp(rec['secret'], token):
        ip = _client_ip()
        _record_failure(ip, username)
        _log_sec("mfa_setup_verify_failed", username, ip)
        return jsonify({'error': 'Token incorrecto. Verifica que tu app authenticator esté sincronizada.'}), 400

    backup_code = _gen_backup_code()
    backup_hash = generate_password_hash(backup_code, method='pbkdf2:sha256:600000')

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=2000")
    try:
        conn.execute("""
            UPDATE users_mfa
               SET enabled          = 1,
                   enabled_at       = datetime('now', 'utc'),
                   last_used_at     = datetime('now', 'utc'),
                   backup_code_hash = ?,
                   disabled_at      = NULL
             WHERE username = ?
        """, (backup_hash, username))
        conn.commit()
    finally:
        conn.close()

    _log_sec("mfa_enabled", username, _client_ip())
    return jsonify({
        'ok': True,
        'backup_code': backup_code,   # ← MOSTRAR UNA SOLA VEZ
        'message': 'MFA activado. Guarda el código de respaldo en lugar seguro — es la única forma de entrar si pierdes tu authenticator.',
    })


@bp.route('/api/mfa/disable', methods=['POST'])
def mfa_disable():
    """Desactiva MFA. Requiere password actual + token TOTP vigente.

    Body: {password: '...', token: '123456'}
    """
    username = session.get('compras_user', '')
    if not username:
        return jsonify({'error': 'No autorizado'}), 401

    body = request.get_json(silent=True) or {}
    password = (body.get('password') or '').strip()
    token = (body.get('token') or '').strip()

    if not password or not token:
        return jsonify({'error': 'Faltan password o token.'}), 400

    # Re-verificar password (defensa contra session hijacking)
    from blueprints.core import _resolve_password_hash
    expected = _resolve_password_hash(username)
    if not expected:
        return jsonify({'error': 'Cuenta sin contraseña configurada.'}), 503
    if expected.startswith('pbkdf2:') or expected.startswith('scrypt:'):
        ok = check_password_hash(expected, password)
    else:
        ok = bool(expected) and hmac.compare_digest(expected, password)
    if not ok:
        ip = _client_ip()
        _record_failure(ip, username)
        _log_sec("mfa_disable_failed_pwd", username, ip)
        return jsonify({'error': 'Password incorrecta.'}), 403

    rec = _get_mfa_record(username)
    if not rec or not rec.get('enabled'):
        return jsonify({'error': 'MFA no está activo.'}), 400

    if not _verify_totp(rec['secret'], token):
        ip = _client_ip()
        _record_failure(ip, username)
        _log_sec("mfa_disable_failed_token", username, ip)
        return jsonify({'error': 'Token TOTP incorrecto.'}), 400

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=2000")
    try:
        conn.execute("""
            UPDATE users_mfa
               SET enabled          = 0,
                   disabled_at      = datetime('now', 'utc'),
                   secret           = '',
                   backup_code_hash = NULL
             WHERE username = ?
        """, (username,))
        conn.commit()
    finally:
        conn.close()

    _log_sec("mfa_disabled", username, _client_ip())
    return jsonify({'ok': True, 'message': 'MFA desactivado correctamente.'})


@bp.route('/api/mfa/admin-disable', methods=['POST'])
def mfa_admin_disable():
    """Permite a un admin desactivar MFA de OTRO usuario (defensa bus factor).

    Caso de uso: usuario perdió authenticator + backup code. Sin esto, queda
    bloqueado fuera del sistema. Requiere ser admin (sebastian / alejandro).

    Body: {target_username: '...'}

    Audit log: TODO admin-disable se registra. Si alguien abusa, se ve.
    """
    actor = session.get('compras_user', '')
    if not actor or actor not in ADMIN_USERS:
        return jsonify({'error': 'Solo admins.'}), 403

    body = request.get_json(silent=True) or {}
    target = (body.get('target_username') or '').strip().lower()
    if not target:
        return jsonify({'error': 'Falta target_username.'}), 400
    if target == actor:
        return jsonify({'error': 'Usa /api/mfa/disable para desactivar tu propio MFA.'}), 400

    rec = _get_mfa_record(target)
    if not rec or not rec.get('enabled'):
        return jsonify({'error': f'MFA de {target} no está activo.'}), 400

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=2000")
    try:
        conn.execute("""
            UPDATE users_mfa
               SET enabled          = 0,
                   disabled_at      = datetime('now', 'utc'),
                   secret           = '',
                   backup_code_hash = NULL
             WHERE username = ?
        """, (target,))
        # Audit log · acción admin sensible
        try:
            from audit_helpers import audit_log as _al
            cur_audit = conn.cursor()
            _al(cur_audit, usuario=actor, accion='MFA_ADMIN_DISABLE',
                tabla='users_mfa', registro_id=target,
                despues={'target': target, 'enabled': 0, 'disabled_by': actor},
                detalle=f"Admin {actor} desactivó MFA de {target} (recovery flow)")
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()

    _log_sec("mfa_admin_disabled", actor, _client_ip(),
             f"target={target}")
    return jsonify({
        'ok': True,
        'message': f'MFA de {target} desactivado por admin {actor}. Evento registrado en audit log.',
    })


# ── Login flow integration ───────────────────────────────────────────────────
# Estos endpoints son usados por el flow de login en core.py cuando un
# usuario con MFA enabled intenta entrar. core.py guarda 'mfa_pending_user'
# en sesión y redirige a /login/mfa.

@bp.route('/login/mfa', methods=['GET'])
def login_mfa_page():
    """Página de paso 2 del login: pide token TOTP."""
    pending = session.get('mfa_pending_user', '')
    if not pending:
        return redirect('/login')
    html = """<!doctype html>
<html lang="es-CO">
<head>
<meta charset="utf-8">
<title>Verificación 2FA · EOS</title>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; background: #0d1117; color: #fff; margin: 0; padding: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
  .box { max-width: 420px; width: 92%; background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 32px; }
  h1 { margin: 0 0 8px; font-size: 22px; }
  p { color: #8b949e; font-size: 14px; line-height: 1.5; margin: 0 0 24px; }
  input[type=text] { width: 100%; padding: 14px; font-size: 22px; text-align: center; letter-spacing: 8px; background: #0d1117; border: 1px solid #30363d; border-radius: 8px; color: #fff; box-sizing: border-box; }
  input[type=text]:focus { border-color: #6d28d9; outline: none; }
  button { width: 100%; padding: 12px; margin-top: 16px; background: #6d28d9; color: #fff; border: 0; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; }
  button:hover { background: #5b21b6; }
  .alt { display: block; margin-top: 16px; text-align: center; font-size: 13px; color: #8b949e; }
  .alt a { color: #7ACFCC; text-decoration: none; }
  .err { background: #2d1b1d; border: 1px solid #6e2a30; color: #f85149; padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-bottom: 16px; }
</style>
</head>
<body>
  <div class="box">
    <h1>Verificación de 2 factores</h1>
    <p>Ingresa el código de 6 dígitos de tu app authenticator (Google Authenticator, Authy, 1Password). Si perdiste tu app, usa el código de respaldo.</p>
    {error}
    <form method="POST" action="/login/mfa">
      <input type="hidden" name="csrf_token" value="{csrf}"/>
      <input type="text" name="token" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" autofocus autocomplete="one-time-code" placeholder="000000"/>
      <button type="submit">Verificar</button>
      <span class="alt">¿Perdiste tu authenticator? <a href="/login/mfa-backup">Usar código de respaldo</a></span>
      <span class="alt"><a href="/logout">Cancelar</a></span>
    </form>
  </div>
</body>
</html>"""
    error_html = ''
    err = session.pop('mfa_error', '')
    if err:
        error_html = f'<div class="err">{err}</div>'
    from auth import _ensure_csrf_token
    csrf = _ensure_csrf_token()
    return Response(
        html.replace('{error}', error_html).replace('{csrf}', csrf),
        mimetype='text/html'
    )


@bp.route('/login/mfa', methods=['POST'])
def login_mfa_verify():
    """Verifica el token TOTP del paso 2 de login y completa la sesión."""
    pending = session.get('mfa_pending_user', '')
    if not pending:
        return redirect('/login')

    token = (request.form.get('token') or '').strip()
    rec = _get_mfa_record(pending)
    ip = _client_ip()

    if _is_locked(ip, pending):
        session['mfa_error'] = 'Demasiados intentos. Espera 15 min.'
        return redirect('/login/mfa')

    if not rec or not rec.get('enabled') or not _verify_totp(rec['secret'], token):
        _record_failure(ip, pending)
        _log_sec("mfa_login_token_failed", pending, ip)
        session['mfa_error'] = 'Token incorrecto. Inténtalo de nuevo.'
        return redirect('/login/mfa')

    # Token válido — completar la sesión
    session.pop('mfa_pending_user', None)
    session.pop('mfa_error', None)
    session.permanent = True
    session['compras_user'] = pending
    session['login_time'] = time.time()

    # Update last_used_at
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=2000")
    try:
        conn.execute("UPDATE users_mfa SET last_used_at=datetime('now','utc') WHERE username=?", (pending,))
        conn.commit()
    finally:
        conn.close()

    _clear_attempts(ip, pending)
    _log_sec("mfa_login_success", pending, ip)

    from auth import _ensure_csrf_token
    _ensure_csrf_token()
    return redirect('/modulos')


@bp.route('/login/mfa-backup', methods=['GET', 'POST'])
def login_mfa_backup():
    """Login de emergencia con backup code. Tras uso exitoso, MFA queda
    DESACTIVADO (el backup code es de un solo uso) y el usuario debe
    re-enrollar. Es la mejor práctica RFC 6238.
    """
    pending = session.get('mfa_pending_user', '')
    if not pending:
        return redirect('/login')

    if request.method == 'POST':
        code = (request.form.get('backup_code') or '').strip().upper()
        rec = _get_mfa_record(pending)
        ip = _client_ip()

        if _is_locked(ip, pending):
            session['mfa_error'] = 'Demasiados intentos. Espera 15 min.'
            return redirect('/login/mfa-backup')

        if not rec or not rec.get('backup_code_hash') or not check_password_hash(rec['backup_code_hash'], code):
            _record_failure(ip, pending)
            _log_sec("mfa_backup_failed", pending, ip)
            session['mfa_error'] = 'Código de respaldo incorrecto.'
            return redirect('/login/mfa-backup')

        # Backup code válido — desactivar MFA (de un solo uso) y completar login
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA busy_timeout=2000")
        try:
            conn.execute("""
                UPDATE users_mfa
                   SET enabled          = 0,
                       disabled_at      = datetime('now', 'utc'),
                       secret           = '',
                       backup_code_hash = NULL
                 WHERE username = ?
            """, (pending,))
            conn.commit()
        finally:
            conn.close()

        session.pop('mfa_pending_user', None)
        session.pop('mfa_error', None)
        session.permanent = True
        session['compras_user'] = pending
        session['login_time'] = time.time()
        session['must_reenroll_mfa'] = True   # bandera para mostrar nag en /perfil

        _clear_attempts(ip, pending)
        _log_sec("mfa_backup_used", pending, ip)

        from auth import _ensure_csrf_token
        _ensure_csrf_token()
        return redirect('/modulos')

    # GET — mostrar form
    error_html = ''
    err = session.pop('mfa_error', '')
    if err:
        error_html = f'<div class="err">{err}</div>'
    from auth import _ensure_csrf_token
    csrf = _ensure_csrf_token()
    html = """<!doctype html>
<html lang="es-CO">
<head>
<meta charset="utf-8">
<title>Código de respaldo · EOS</title>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; background: #0d1117; color: #fff; margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
  .box { max-width: 460px; width: 92%; background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 32px; }
  h1 { margin: 0 0 8px; font-size: 22px; }
  p { color: #8b949e; font-size: 14px; line-height: 1.5; margin: 0 0 24px; }
  .warn { background: #2d2517; border: 1px solid #6e5a2a; color: #f0c674; padding: 12px; border-radius: 8px; font-size: 13px; margin-bottom: 16px; }
  input[type=text] { width: 100%; padding: 12px; font-size: 16px; font-family: monospace; letter-spacing: 2px; text-transform: uppercase; background: #0d1117; border: 1px solid #30363d; border-radius: 8px; color: #fff; box-sizing: border-box; }
  button { width: 100%; padding: 12px; margin-top: 16px; background: #6d28d9; color: #fff; border: 0; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; }
  button:hover { background: #5b21b6; }
  .alt { display: block; margin-top: 16px; text-align: center; font-size: 13px; }
  .alt a { color: #7ACFCC; text-decoration: none; }
  .err { background: #2d1b1d; border: 1px solid #6e2a30; color: #f85149; padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-bottom: 16px; }
</style>
</head>
<body>
  <div class="box">
    <h1>Código de respaldo</h1>
    <div class="warn">Después de usar el código de respaldo, MFA se desactivará automáticamente. Tendrás que re-enrollar tu authenticator después de entrar.</div>
    <p>Ingresa tu código de respaldo de 12 caracteres (formato XXXX-XXXX-XXXX).</p>
    {error}
    <form method="POST" action="/login/mfa-backup">
      <input type="hidden" name="csrf_token" value="{csrf}"/>
      <input type="text" name="backup_code" placeholder="XXXX-XXXX-XXXX" autofocus autocomplete="off"/>
      <button type="submit">Entrar y desactivar MFA</button>
      <span class="alt"><a href="/login/mfa">← Volver a token normal</a></span>
      <span class="alt"><a href="/logout">Cancelar</a></span>
    </form>
  </div>
</body>
</html>"""
    return Response(
        html.replace('{error}', error_html).replace('{csrf}', csrf),
        mimetype='text/html'
    )
