import os
import sys

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

from database import init_db, seed_compromisos, seed_rrhh, run_seed_rrhh

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'hha-group-2026-secretkey-x9kq')
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)
register_hooks(app)

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

# ─── DB init (idempotente) ──────────────────────────────────────────────────
init_db()
run_seed_rrhh()


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
