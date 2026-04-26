# auth.py — rate limiting, hooks y utilidades de seguridad
# Fase B refactor: extraído de index.py
import sqlite3
import time
from datetime import datetime

from flask import request, session, redirect, jsonify

from config import DB_PATH

# ── Rate limiter persistente (SQLite — multi-worker safe) ────────────────────
_MAX_ATTEMPTS = 5
_LOCKOUT_SECS = 900   # 15 minutos


def _client_ip():
    hdr = request.headers.get('X-Forwarded-For', request.remote_addr or '0.0.0.0')
    return hdr.split(',')[0].strip()


def _constant_time_eq(a, b):
    """Comparación de strings en tiempo constante (anti timing-attack)."""
    import hmac as _hmac
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    try:
        return _hmac.compare_digest(a, b)
    except Exception:
        return False


def _ensure_csrf_token():
    """Genera y guarda un CSRF token en la sesión si no existe.

    Retorna el token actual. Idempotente — múltiples llamadas devuelven el mismo
    token mientras la sesión exista. Token nuevo solo se genera tras logout.
    """
    import secrets as _secrets
    token = session.get('csrf_token')
    if not token:
        token = _secrets.token_urlsafe(32)
        session['csrf_token'] = token
    return token


def _rate_key(ip, username=None):
    """Compone la clave para rate limiting.

    Si username está disponible (login attempt con username conocido), la clave
    es 'ip|username' — esto evita que una botnet con N IPs distintas pueda
    fuerza bruta sobre un usuario específico, y simétricamente que un atacante
    con 1 IP pueda enumerar usuarios.

    Sin username, fallback a sólo IP — compatible con código existente.
    """
    if username:
        return f"{ip}|{username.strip().lower()[:32]}"
    return ip


def _is_locked(ip, username=None):
    """Verifica si IP (o IP+username) está bloqueada.

    Devuelve True si CUALQUIERA de las dos claves está bloqueada — esto cierra
    la brecha donde un atacante alterna usernames para evadir el lock por IP.
    """
    keys_to_check = [_rate_key(ip)]
    if username:
        keys_to_check.append(_rate_key(ip, username))
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA busy_timeout=2000")
        placeholders = ",".join("?" * len(keys_to_check))
        rows = conn.execute(
            f"SELECT ip, locked_until FROM rate_limit WHERE ip IN ({placeholders})",
            keys_to_check
        ).fetchall()
        conn.close()
        now = time.time()
        # ¿Alguna key está bloqueada activamente?
        for _, locked_until in rows:
            if now < locked_until:
                return True
        # Limpieza oportunista: SOLO entries con locked_until ya expirado
        # (mayor a 0 significa que sí estuvo bloqueada en el pasado).
        # NO borrar entries con locked_until=0 porque esas son contadores
        # de fallos NO bloqueantes — borrarlas reseteaba el contador en
        # cada login fallido y rompía el rate limit.
        expired_keys = [
            ip for ip, locked_until in rows
            if 0 < locked_until <= now
        ]
        for key in expired_keys:
            _clear_attempts(key)
        return False
    except Exception:
        return False   # En caso de error de DB, no bloquear


def _record_failure(ip, username=None):
    """Registra un intento fallido. Incrementa contador para IP y para IP+user.

    Doble registro: por IP (defensa contra escaneo) y por IP+user (defensa
    contra brute-force dirigido). Cualquiera que llegue al máximo activa lock.
    """
    keys_to_record = [_rate_key(ip)]
    if username:
        keys_to_record.append(_rate_key(ip, username))
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA busy_timeout=2000")
        for key in keys_to_record:
            conn.execute("""
                INSERT INTO rate_limit(ip, attempts, locked_until, last_attempt)
                VALUES(?, 1, 0, ?)
                ON CONFLICT(ip) DO UPDATE SET
                    attempts     = attempts + 1,
                    last_attempt = excluded.last_attempt,
                    locked_until = CASE
                        WHEN attempts + 1 >= ? THEN ? + excluded.last_attempt
                        ELSE locked_until
                    END
            """, (key, time.time(), _MAX_ATTEMPTS, _LOCKOUT_SECS))
        conn.commit()
        conn.close()
    except Exception:
        pass


def _clear_attempts(ip_or_key, username=None):
    """Borra el registro de intentos para una IP/key (login exitoso).

    Si se pasa username, también limpia la entrada IP+user.
    """
    keys_to_clear = [_rate_key(ip_or_key)]
    if username:
        keys_to_clear.append(_rate_key(ip_or_key, username))
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA busy_timeout=2000")
        placeholders = ",".join("?" * len(keys_to_clear))
        conn.execute(
            f"DELETE FROM rate_limit WHERE ip IN ({placeholders})",
            keys_to_clear
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _log_sec(event, username=None, ip=None, details=None):
    try:
        ua = request.headers.get("User-Agent", "")[:200]
        ts = datetime.utcnow().isoformat() + "Z"
        conn2 = sqlite3.connect(DB_PATH)
        conn2.execute(
            "INSERT INTO security_events(ts,event,username,ip,user_agent,details)"
            " VALUES(?,?,?,?,?,?)",
            (ts, event, username, ip, ua, details or "")
        )
        conn2.commit(); conn2.close()
    except Exception:
        pass


def sin_acceso_html(modulo):
    """Pagina de acceso denegado consistente para todos los modulos."""
    return (
        '<!DOCTYPE html><html><head><meta charset=UTF-8>'
        '<title>Sin acceso</title>'
        '<style>body{font-family:sans-serif;background:#0f172a;color:#fff;display:flex;'
        'align-items:center;justify-content:center;height:100vh;margin:0;flex-direction:column;gap:16px;}'
        '.card{background:#1e293b;border:1px solid #334155;border-radius:16px;padding:40px;'
        'text-align:center;max-width:400px;}'
        'h2{color:#f59e0b;margin:0 0 12px;}p{color:#94a3b8;margin:0 0 20px;}'
        'a{display:inline-block;background:#667eea;color:#fff;text-decoration:none;'
        'padding:10px 24px;border-radius:8px;font-weight:600;}</style></head>'
        f'<body><div class="card"><h2>Acceso restringido</h2>'
        f'<p>El modulo de {modulo} no esta disponible para tu usuario.</p>'
        '<a href="/hub">Volver al escritorio</a></div></body></html>'
    )


def register_hooks(app):
    """Registra before_request y after_request en la app Flask."""

    @app.before_request
    def check_session_timeout():
        if session.get('compras_user'):
            if time.time() - session.get('login_time', 0) > 8 * 3600:
                session.clear()
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Sesion expirada'}), 401
                return redirect('/login')

    @app.before_request
    def require_auth_for_api():
        """Bloquea TODAS las rutas /api/ si no hay sesion activa.
        Excepcion: /api/login (publico).
        Esto cierra la brecha donde ~45 endpoints aceptaban mutaciones sin auth.
        """
        if not request.path.startswith('/api/'):
            return  # Rutas HTML se manejan individualmente
        PUBLIC_API = {'/api/login', '/api/logout', '/api/health'}
        if request.path in PUBLIC_API:
            return
        if not session.get('compras_user'):
            return jsonify({'error': 'No autorizado. Inicia sesion primero.'}), 401

    # ── CSRF protection light: Origin/Referer check + token ──────────────────
    # Defense in depth con 2 capas independientes:
    #  1. Origin/Referer check (universal, sin requerir frontend cooperante)
    #  2. CSRF token explícito (si el frontend lo envía, también se valida)
    #
    # Cualquiera de las 2 capas que falle = 403. Funciona aún si el frontend
    # solo implementa una; mejor seguridad si implementa ambas.
    CSRF_EXEMPT_PATHS = {
        '/api/health',         # health check público
        '/api/csrf-token',     # endpoint que entrega el token
    }
    UNSAFE_METHODS = {'POST', 'PUT', 'DELETE', 'PATCH'}

    @app.before_request
    def csrf_origin_check():
        if request.method not in UNSAFE_METHODS:
            return
        if request.path in CSRF_EXEMPT_PATHS:
            return

        expected_host = request.host  # incluye puerto si no es default
        origin = request.headers.get('Origin', '').strip()
        referer = request.headers.get('Referer', '').strip()

        def _host_from_url(url):
            try:
                from urllib.parse import urlparse
                return urlparse(url).netloc
            except Exception:
                return ''

        # ── Capa 1: Origin/Referer check ─────────────────────────────────
        origin_ok = False
        if origin:
            origin_host = _host_from_url(origin)
            if origin_host == expected_host:
                origin_ok = True
        elif referer:
            referer_host = _host_from_url(referer)
            if referer_host == expected_host:
                origin_ok = True
        else:
            # Algunos clientes legítimos (curl, scripts internos) no envían
            # Origin/Referer. Si la sesión es válida, permitimos pero logueamos.
            if session.get('compras_user'):
                _log_sec(
                    "csrf_no_origin_allowed",
                    session.get('compras_user'),
                    _client_ip(),
                    f"path={request.path}"
                )
                origin_ok = True

        if not origin_ok:
            _log_sec(
                "csrf_blocked",
                session.get('compras_user', '-'),
                _client_ip(),
                f"path={request.path} origin={origin[:80]} referer={referer[:80]}"
            )
            return jsonify({
                "error": "Origen de la petición no válido",
                "hint": "Esta acción solo puede ejecutarse desde la app web."
            }), 403

        # ── Capa 2: CSRF token explícito (defense in depth) ──────────────
        # Si el cliente envía X-CSRF-Token, DEBE matchear con session['csrf_token'].
        # Si NO lo envía, se permite (los frontends viejos siguen funcionando).
        # El frontend nuevo puede activar este check enviando el header.
        provided_token = request.headers.get('X-CSRF-Token', '').strip()
        if provided_token:
            session_token = session.get('csrf_token', '')
            if not session_token or not _constant_time_eq(provided_token, session_token):
                _log_sec(
                    "csrf_token_mismatch",
                    session.get('compras_user', '-'),
                    _client_ip(),
                    f"path={request.path}"
                )
                return jsonify({
                    "error": "CSRF token inválido o expirado",
                    "hint": "Recarga la página para obtener un token nuevo."
                }), 403

    @app.after_request
    def add_security_headers(response):
        response.headers['X-Frame-Options']           = 'SAMEORIGIN'
        response.headers['X-Content-Type-Options']    = 'nosniff'
        response.headers['Referrer-Policy']           = 'strict-origin-when-cross-origin'
        response.headers['X-XSS-Protection']          = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        # CSP defense-in-depth. 'unsafe-inline' sigue presente porque los
        # templates_py tienen JS/CSS embebido — migrarlos a Jinja2 +
        # nonces es trabajo de ~1 semana documentado en SECURITY.md.
        # Mientras tanto, se cierran 3 vectores que NO requieren refactor:
        #   - frame-ancestors 'none': bloquea clickjacking aunque
        #     X-Frame-Options se ignore en navegadores nuevos.
        #   - form-action 'self': forms solo pueden submitear al mismo host
        #     (anti exfiltración via <form action="https://evil.com">).
        #   - base-uri 'self': anti rebase URL injection.
        #   - object-src 'none': no plugins/applets.
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' fonts.googleapis.com cdnjs.cloudflare.com; "
            "font-src 'self' fonts.gstatic.com cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'; "
            "object-src 'none';"
        )
        response.headers['Content-Security-Policy'] = csp
        # Cross-Origin policies para defense in depth contra Spectre y leaks
        response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
        return response
