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
from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec, sin_acceso_html
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


@bp.route('/')
def index():
    # Redirigir a login si no hay sesion activa; a /hub si ya esta autenticado
    if 'compras_user' not in session:
        return redirect('/login')
    return redirect('/hub')

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
        return redirect('/login?next=/hub')
    from templates_py.hub_html import HUB_HTML
    return Response(HUB_HTML, mimetype='text/html')

@bp.route('/modulos')
def modulos():
    if 'compras_user' not in session:
        return redirect('/login?next=/modulos')
    from templates_py.modulos_html import MODULOS_HTML
    usuario = session.get('compras_user', '')
    return Response(MODULOS_HTML.replace('{usuario}', usuario), mimetype='text/html')

@bp.route('/login', methods=['GET','POST'])
def login():
    error = ''
    next_url = request.args.get('next', '/hub')
    if not next_url.startswith('/') or next_url.startswith('//'):
        next_url = '/hub'
    if request.method == 'POST':
        ip = _client_ip()
        if _is_locked(ip):
            error = '<div class="err">Demasiados intentos. Espera 15 min.</div>'
            return Response(LOGIN_HTML.replace('{error}', error).replace('{next_url}', next_url), mimetype='text/html')
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '').strip()
        expected = COMPRAS_USERS.get(username, '')
        # Soporte PBKDF2 (env var con hash) y plaintext legacy
        if expected and expected.startswith('pbkdf2:'):
            match = check_password_hash(expected, password)
        else:
            match = bool(expected) and hmac.compare_digest(expected, password)
        if match:
            _clear_attempts(ip)
            _log_sec("login_success", username, ip)
            session.clear()
            session.permanent = True
            session['compras_user'] = username
            session['login_time']   = time.time()
            nxt = request.args.get('next', '')
            if not nxt or not nxt.startswith('/') or nxt.startswith('//'):
                nxt = '/hub'
            return redirect(nxt)
        _record_failure(ip)
        _log_sec("login_failure", username, ip)
        error = '<div class="err">Usuario o contraseña incorrectos.</div>'
    return Response(LOGIN_HTML.replace('{error}', error).replace('{next_url}', next_url), mimetype='text/html')

@bp.route('/logout')
def logout():
    session.pop('compras_user', None)
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