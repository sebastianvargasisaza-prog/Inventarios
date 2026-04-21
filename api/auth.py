# auth.py — rate limiting, hooks y utilidades de seguridad
# Fase B refactor: extraído de index.py
import sqlite3
import time
from datetime import datetime

from flask import request, session, redirect

from config import DB_PATH

# ── Rate limiter ──────────────────────────────────────────────────────────────
_LOGIN_ATTEMPTS = {}
_MAX_ATTEMPTS   = 5
_LOCKOUT_SECS   = 900


def _client_ip():
    hdr = request.headers.get('X-Forwarded-For', request.remote_addr or '0.0.0.0')
    return hdr.split(',')[0].strip()


def _is_locked(ip):
    rec = _LOGIN_ATTEMPTS.get(ip)
    if not rec: return False
    if time.time() < rec['locked_until']: return True
    _LOGIN_ATTEMPTS.pop(ip, None)
    return False


def _record_failure(ip):
    rec = _LOGIN_ATTEMPTS.setdefault(ip, {'count': 0, 'locked_until': 0.0})
    rec['count'] += 1
    if rec['count'] >= _MAX_ATTEMPTS:
        rec['locked_until'] = time.time() + _LOCKOUT_SECS


def _clear_attempts(ip):
    _LOGIN_ATTEMPTS.pop(ip, None)


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
                return redirect('/login')

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
