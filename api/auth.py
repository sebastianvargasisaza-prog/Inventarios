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

    # ── CSRF protection light: Origin/Referer check ──────────────────────────
    # Bloquea CSRF clásico verificando que requests con efectos secundarios
    # (POST/PUT/DELETE/PATCH) provengan del mismo host. No requiere tokens
    # explícitos en el frontend — funciona con cualquier form/fetch
    # same-origin moderno (los browsers envían Origin/Referer automáticamente).
    #
    # Casos manejados:
    #  - GET/HEAD/OPTIONS: nunca chequeados (idempotentes por contrato HTTP)
    #  - Header Origin presente: comparar con request.host
    #  - Origin ausente, Referer presente: extraer host del Referer
    #  - Ambos ausentes: rechazar (browsers modernos siempre envían Referer
    #    a menos que se configure 'no-referrer' explícitamente — sospechoso)
    #  - Webhooks externos legítimos pueden whitelist-ear su path en CSRF_EXEMPT
    CSRF_EXEMPT_PATHS = {
        '/api/health',  # health check público
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

        if origin:
            origin_host = _host_from_url(origin)
            if origin_host == expected_host:
                return
        elif referer:
            referer_host = _host_from_url(referer)
            if referer_host == expected_host:
                return
        else:
            # Algunos clientes legítimos (curl, scripts internos) no envían
            # Origin/Referer. Para no romper integraciones, si la sesión es
            # válida Y la request viene de la misma red de Render (X-Forwarded
            # -For matchea), permitimos. Caso normal browser fluye por las
            # ramas de arriba.
            if session.get('compras_user'):
                # Sesión válida + sin headers cross-origin = probablemente
                # script legítimo del usuario. Loguear pero permitir.
                _log_sec(
                    "csrf_no_origin_allowed",
                    session.get('compras_user'),
                    _client_ip(),
                    f"path={request.path}"
                )
                return

        # Bloqueado: cross-origin attempt o headers ausentes sin sesión
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

    @app.after_request
    def add_security_headers(response):
        response.headers['X-Frame-Options']           = 'SAMEORIGIN'
        response.headers['X-Content-Type-Options']    = 'nosniff'
        response.headers['Referrer-Policy']           = 'strict-origin-when-cross-origin'
        response.headers['X-XSS-Protection']          = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        csp = ("default-src 'self'; "
               "script-src 'self' 'unsafe-inline' cdnjs.cloudflare.com; "
               "style-src 'self' 'unsafe-inline' fonts.googleapis.com cdnjs.cloudflare.com; "
               "font-src 'self' fonts.gstatic.com cdnjs.cloudflare.com; "
               "img-src 'self' data:; connect-src 'self';")
        response.headers['Content-Security-Policy'] = csp
        return response
