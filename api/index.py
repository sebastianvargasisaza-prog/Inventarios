import os
import json
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS
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
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)
register_hooks(app)


from templates_py.rrhh_html import RRHH_HTML

# ─── HUB HHA GROUP ────────────────────────────────────────────
from templates_py.compromisos_html import COMPROMISOS_HTML

from templates_py.home_html import HOME_HTML

from templates_py.hub_html import HUB_HTML

# ─── LOGIN COMPRAS ────────────────────────────────────────────
# ─── MÓDULO CLIENTES ──────────────────────────────────────────
from templates_py.clientes_html import CLIENTES_HTML

# ─── MÓDULO CALIDAD BPM ────────────────────────────────────────
from templates_py.calidad_html import CALIDAD_HTML

# ─── MÓDULO HQ GERENCIA ────────────────────────────────────────
from templates_py.gerencia_html import GERENCIA_HTML

# ─── MÓDULO FINANCIERO ────────────────────────────────────────
from templates_py.financiero_html import FINANCIERO_HTML

from templates_py.login_html import LOGIN_HTML

# ─── MÓDULO COMPRAS ───────────────────────────────────────────
from templates_py.compras_html import COMPRAS_HTML

from templates_py.recepcion_html import RECEPCION_HTML

from templates_py.salida_html import SALIDA_HTML

from templates_py.solicitudes_html import SOLICITUDES_HTML

from templates_py.dashboard_html import DASHBOARD_HTML


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
