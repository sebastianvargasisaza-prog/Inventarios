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


def _is_locked(ip):
    """Verifica si la IP está bloqueada. Lee de SQLite — funciona con N workers."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA busy_timeout=2000")
        row = conn.execute(
            "SELECT locked_until FROM rate_limit WHERE ip=?", (ip,)
        ).fetchone()
        conn.close()
        if not row:
            return False
        if time.time() < row[0]:
            return True
        # Bloqueo expirado — limpiar
        _clear_attempts(ip)
        return False
    except Exception:
        return False   # En caso de error de DB, no bloquear


def _record_failure(ip):
    """Registra un intento fallido. Usa INSERT OR REPLACE para atomicidad."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA busy_timeout=2000")
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
        """, (ip, time.time(), _MAX_ATTEMPTS, _LOCKOUT_SECS))
        conn.commit()
        conn.close()
    except Exception:
        pass


def _clear_attempts(ip):
    """Borra el registro de intentos para la IP (login exitoso)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA busy_timeout=2000")
        conn.execute("DELETE FROM rate_limit WHERE ip=?", (ip,))
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
