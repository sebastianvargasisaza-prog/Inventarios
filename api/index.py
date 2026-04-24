import os
import sys
import logging
import time as _time_module

# Garantizar que api/ esté en sys.path sin importar cómo Gunicorn arranca el app.
# Con 'gunicorn api.index:app' desde la raíz, Python importa api.index como
# namespace package y NO agrega api/ a sys.path automáticamente.
_api_dir = os.path.dirname(os.path.abspath(__file__))
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

import json
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS

# Garantizar directorio de DB antes de importar blueprints (evita crash en Render)
import pathlib as _pl
_db_dir = _pl.Path(DB_PATH).parent
if str(_db_dir) not in ('', '.', '/'):
    _db_dir.mkdir(parents=True, exist_ok=True)
del _pl, _db_dir
from auth import (
    _client_ip, _is_locked, _record_failure, _clear_attempts,
    _log_sec, register_hooks,
)

from database import init_db, seed_compromisos, seed_rrhh, run_seed_rrhh, get_db, run_migrations, MIGRATIONS

app = Flask(__name__)
_secret = os.environ.get('SECRET_KEY')
if not _secret:
    import warnings
    warnings.warn(
        "SECRET_KEY no configurado como variable de entorno. "
        "Las sesiones son predecibles. Configura SECRET_KEY en Render → Environment.",
        stacklevel=2
    )
    _secret = 'hha-group-2026-secretkey-x9kq'  # fallback solo para desarrollo local
app.secret_key = _secret
del _secret
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)
register_hooks(app)


# ── Logging estructurado para producción ─────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',   # JSON puro — Render/Datadog lo parsea directamente
)
_logger = logging.getLogger("inventario")
_APP_START = _time_module.time()


@app.teardown_appcontext
def close_db(exception=None):
    """Cierra la conexion SQLite al final de cada request (incluso si hay error).
    Esto garantiza que get_db() nunca deja conexiones abiertas, independientemente
    de si la funcion del blueprint llama conn.close() o no.
    """
    db = None
    try:
        from flask import g
        db = g.pop("db", None)
    except RuntimeError:
        pass
    if db is not None:
        try:
            db.close()
        except Exception:
            pass



@app.route('/api/email-status')
def email_status():
    """Diagnostico de configuracion SMTP — solo admins."""
    if session.get('compras_user') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    import sys as _sys
    _api_dir2 = os.path.dirname(os.path.abspath(__file__))
    _parent = os.path.dirname(_api_dir2)
    _sys.path.insert(0, _parent)
    try:
        from notificaciones import SistemaNotificaciones
        n = SistemaNotificaciones()
        remitente = n.email_remitente
        password_set = bool(n.contraseña)
        # Enmascarar: muestra primeros 4 chars + ***
        remitente_masked = (remitente[:4] + '***' + remitente[remitente.find('@'):]) if '@' in remitente else (remitente[:4] + '***' if remitente else '')
        # Fuente de cada var
        src_email = ('EMAIL_REMITENTE' if os.getenv('EMAIL_REMITENTE') else
                     'SMTP_EMAIL'      if os.getenv('SMTP_EMAIL')      else 'NO CONFIGURADO')
        src_pass  = ('EMAIL_PASSWORD'  if os.getenv('EMAIL_PASSWORD')  else
                     'SMTP_PASSWORD'   if os.getenv('SMTP_PASSWORD')   else 'NO CONFIGURADO')
        configurado = bool(remitente and password_set)
        return jsonify({
            'configurado': configurado,
            'remitente': remitente_masked or 'NO CONFIGURADO',
            'password_set': password_set,
            'smtp_server': n.smtp_server,
            'smtp_port': n.smtp_port,
            'fuente_email': src_email,
            'fuente_password': src_pass,
            'advertencia': None if configurado else
                'Email NO configurado. Define EMAIL_REMITENTE (o SMTP_EMAIL) y '
                'EMAIL_PASSWORD (o SMTP_PASSWORD) como variables de entorno en Render.'
        })
    except Exception as e:
        return jsonify({'configurado': False, 'error': str(e)}), 500


# ─── Blueprints ───────────────────────────────────────────────────────────
from blueprints.core import bp as core_bp
from blueprints.hub import bp as hub_bp
from blueprints.inventario import bp as inventario_bp
from blueprints.compras import bp as compras_bp
from blueprints.clientes import bp as clientes_bp
from blueprints.gerencia import bp as gerencia_bp
from blueprints.financiero import bp as financiero_bp
from blueprints.maquila import bp as maquila_bp
from blueprints.despachos import bp as despachos_bp
from blueprints.rrhh import bp as rrhh_bp
from blueprints.calidad import bp as calidad_bp
from blueprints.tecnica import bp as tecnica_bp
from blueprints.marketing import bp as marketing_bp
from blueprints.animus import bp as animus_bp

app.register_blueprint(core_bp)
app.register_blueprint(hub_bp)
app.register_blueprint(inventario_bp)
app.register_blueprint(compras_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(gerencia_bp)
app.register_blueprint(financiero_bp)
app.register_blueprint(maquila_bp)
app.register_blueprint(despachos_bp)
app.register_blueprint(rrhh_bp)
app.register_blueprint(calidad_bp)
app.register_blueprint(tecnica_bp)
app.register_blueprint(marketing_bp)
app.register_blueprint(animus_bp)

# ─── DB init + migraciones de esquema (idempotente) ────────────────────────
init_db()   # crea tablas + ejecuta run_migrations() internamente
run_seed_rrhh()
import logging as _log
_log.getLogger(__name__).info(
    "schema_migrations: %d versiones registradas", len(MIGRATIONS)
)



@app.after_request
def log_request(response):
    """Log estructurado de cada request — parseable por Render/Datadog/Grafana."""
    try:
        import json as _json
        duration_ms = round((_time_module.time() - getattr(request, '_start_time', _time_module.time())) * 1000, 1)
        _logger.info(_json.dumps({
            "ts":       __import__('datetime').datetime.utcnow().isoformat() + "Z",
            "method":   request.method,
            "path":     request.path,
            "status":   response.status_code,
            "ms":       duration_ms,
            "user":     session.get("compras_user", "-"),
            "ip":       request.headers.get("X-Forwarded-For", request.remote_addr or "-").split(",")[0].strip(),
        }, ensure_ascii=False))
    except Exception:
        pass
    return response

@app.before_request
def mark_start_time():
    request._start_time = _time_module.time()


@app.route('/api/health')
def health_check():
    """Health check completo — usado por Render, load balancers y monitoreo externo.
    No requiere autenticacion — es publico por diseno.
    Retorna 200 si todo OK, 503 si la DB no responde.
    """
    import os as _os
    try:
        from database import get_db
        db = get_db()
        tables = db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        db_size_mb = round(_os.path.getsize(DB_PATH) / 1024 / 1024, 2) if _os.path.exists(DB_PATH) else 0
        wal_mode = db.execute("PRAGMA journal_mode").fetchone()[0]
        uptime_s  = round(_time_module.time() - _APP_START)
        uptime_h  = f"{uptime_s//3600}h {(uptime_s%3600)//60}m"
        return jsonify({
            "status":   "ok",
            "uptime":   uptime_h,
            "db": {
                "tables":    tables,
                "size_mb":   db_size_mb,
                "wal_mode":  wal_mode == "wal",
            },
            "version":  "2.0.0",
            "workers":  int(_os.environ.get("WEB_CONCURRENCY", 1)),
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 503

@app.errorhandler(404)
def not_found(e):
    h = '<html><body style="background:#0d1117;color:#fff;font-family:sans-serif;text-align:center;padding-top:10vh"><h1>404</h1><p>Pagina no encontrada.</p><a href="/compras" style="color:#7ACFCC;">Volver</a></body></html>'
    return Response(h, status=404, mimetype='text/html')

@app.errorhandler(500)
def server_error(e):
    h = '<html><body style="background:#0d1117;color:#fff;font-family:sans-serif;text-align:center;padding-top:10vh"><h1>500</h1><p>Error interno del servidor.</p><a href="/compras" style="color:#7ACFCC;">Volver</a></body></html>'
    return Response(h, status=500, mimetype='text/html')

if __name__ == '__main__':

    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
