import os
import sys
import logging
import time as _time_module

# ─── Sentry (alertas proactivas de errores 5xx) ────────────────────────────
# Solo se inicializa si la env var SENTRY_DSN está configurada en Render.
# Sin DSN, la app funciona normal pero los errores no llegan a Sentry —
# útil para dev local y tests donde no queremos generar ruido.
_sentry_dsn = os.environ.get("SENTRY_DSN", "").strip()
if _sentry_dsn and not os.environ.get("PYTEST_CURRENT_TEST"):
    # Filtros PII y ruido (definidos antes del init para usarlos como callback)
    _PII_KEYS = {'cliente_nombre','cliente_contacto','cliente_email','email',
                  'telefono','phone','nit','password','secret','token','api_key',
                  'firma_hash','referencia','radicado'}

    def _scrub_pii(obj, depth=0):
        """Reemplaza valores de claves PII por '<redacted>' en cualquier nivel."""
        if depth > 6 or obj is None:
            return obj
        if isinstance(obj, dict):
            return {k: ('<redacted>' if str(k).lower() in _PII_KEYS else _scrub_pii(v, depth+1))
                       for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return type(obj)(_scrub_pii(v, depth+1) for v in obj)
        return obj

    def _sentry_before_send(event, hint):
        # No enviar 4xx (auth fails, validation errors) — son user error, no bug.
        try:
            extra = (event.get('extra') or {})
            req = (event.get('request') or {})
            status = extra.get('status_code')
            if isinstance(status, int) and 400 <= status < 500:
                return None
            # Filtrar PII de extras, contexts y breadcrumbs
            if 'extra' in event: event['extra'] = _scrub_pii(event['extra'])
            if 'contexts' in event: event['contexts'] = _scrub_pii(event['contexts'])
            if 'breadcrumbs' in event:
                bs = event['breadcrumbs']
                if isinstance(bs, dict) and 'values' in bs:
                    bs['values'] = [_scrub_pii(b) for b in bs['values']]
            # Quitar query strings con credenciales del request URL
            url = (req.get('url') or '')
            if 'password=' in url or 'token=' in url:
                event['request']['url'] = url.split('?')[0] + '?<redacted>'
        except Exception:
            pass  # nunca romper el envío por nuestro propio filtro
        return event

    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        sentry_sdk.init(
            dsn=_sentry_dsn,
            integrations=[FlaskIntegration()],
            # Sample rate de transacciones para performance monitoring.
            # 0.1 = 10% — balance entre visibilidad y costo. Sentry tiene
            # plan gratis con 5k errores + 10k transactions/mes.
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            # Environment para distinguir prod vs staging si se agrega después.
            environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
            # No enviar PII automáticamente (passwords, headers de auth).
            send_default_pii=False,
            # Filtrar antes de enviar: PII (clientes) + ruido (4xx).
            before_send=_sentry_before_send,
            release=os.environ.get("RENDER_GIT_COMMIT", "unknown"),
        )
    except ImportError:
        # sentry-sdk no instalado — fallback silencioso (dev local sin deps)
        pass
del _sentry_dsn

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

from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, validate_config

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
_secret = os.environ.get('SECRET_KEY', '').strip()
if not _secret:
    # Sin fallback hardcoded: si falta SECRET_KEY, generamos una clave
    # ALEATORIA EFÍMERA (válida solo para este proceso). Consecuencia:
    # todas las sesiones se invalidan al redeploy y los users deben
    # re-login. Mejor que tener una clave pública conocida que permita
    # falsificar sesiones. validate_config() reporta CRITICAL para que
    # el admin pueda configurarla en Render.
    import secrets as _secrets_module
    _secret = _secrets_module.token_urlsafe(48)
    del _secrets_module
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

# Validación de configuración al startup. Emite warnings estructurados (JSON
# por línea) en logs de Render/Datadog si faltan secretos críticos. No
# crashea la app — el admin ve los warnings y puede priorizar el fix.
_CONFIG_ISSUES = validate_config()


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
from blueprints.aseguramiento import bp as aseguramiento_bp
from blueprints.tecnica import bp as tecnica_bp
from blueprints.marketing import bp as marketing_bp
from blueprints.animus import bp as animus_bp
from blueprints.espagiria import bp as espagiria_bp
from blueprints.comunicacion import bp as comunicacion_bp
from blueprints.contabilidad import bp as contabilidad_bp
from blueprints.programacion import bp as programacion_bp
from blueprints.admin import bp as admin_bp
from blueprints.chat import bp as chat_bp
from blueprints.bienestar import bp as bienestar_bp
from blueprints.mfa import bp as mfa_bp
from blueprints.notif import bp as notif_bp
from blueprints.compliance import bp as compliance_bp
from blueprints.comercial import bp as comercial_bp
from blueprints.auto_plan import bp as auto_plan_bp

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
app.register_blueprint(aseguramiento_bp)
app.register_blueprint(tecnica_bp)
app.register_blueprint(marketing_bp)
app.register_blueprint(animus_bp)
app.register_blueprint(espagiria_bp)
app.register_blueprint(comunicacion_bp)
app.register_blueprint(contabilidad_bp)
app.register_blueprint(programacion_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(bienestar_bp)
app.register_blueprint(mfa_bp)
app.register_blueprint(notif_bp)
app.register_blueprint(compliance_bp)
app.register_blueprint(comercial_bp)
app.register_blueprint(auto_plan_bp)

# ─── DB init + migraciones de esquema (idempotente) ────────────────────────
init_db()   # crea tablas + ejecuta run_migrations() internamente
run_seed_rrhh()
import logging as _log
_log.getLogger(__name__).info(
    "schema_migrations: %d versiones registradas", len(MIGRATIONS)
)

# Arrancar loops de background daemon (no bloqueantes).
# Solo si NO estamos en modo testing (los tests no necesitan loops corriendo).
if not app.config.get("TESTING"):
    try:
        from blueprints.marketing import _start_marketing_metrics_loop
        _start_marketing_metrics_loop()
        _log.getLogger(__name__).info("marketing-metrics-loop arrancado")
    except Exception as _e:
        _log.getLogger(__name__).warning("metrics-loop NO arrancó: %s", _e)
    # Sebastian (30-abr-2026): cron auto-plan diario 07:00 L-V.
    # Solo arranca si AUTO_PLAN_CRON_ENABLED=1 en env (Render).
    try:
        from blueprints.auto_plan_jobs import iniciar_cron as _iniciar_auto_plan
        _iniciar_auto_plan(app)
    except Exception as _e:
        _log.getLogger(__name__).warning("auto-plan-cron NO arrancó: %s", _e)
    # Sebastian (1-may-2026): multi-cron interno · sin Render Cron Jobs externos.
    # Loop cada 5 min ejecuta sync_shopify (6am), auto_d20 (8am), auto-sc mensual
    # día 1-5 (12:00), auto-sc-mee mensual día 1-5 (12:30), urgente lunes (12:00).
    try:
        from blueprints.auto_plan_jobs import iniciar_multi_cron as _iniciar_multi_cron
        _iniciar_multi_cron(app)
    except Exception as _e:
        _log.getLogger(__name__).warning("multi-cron NO arrancó: %s", _e)



@app.before_request
def _attach_request_context():
    """Adjunta request_id (12 hex) y timestamp de inicio.

    El request_id se reusa si llega en el header X-Request-Id (ej. desde un
    load balancer que ya lo asigno) — caso contrario se genera uno nuevo.
    Ambos: timing y correlacion para debugging multi-worker.
    """
    import uuid as _uuid
    request._start_time = _time_module.time()
    incoming = request.headers.get("X-Request-Id", "").strip()
    request.id = incoming if (incoming and len(incoming) <= 64) else _uuid.uuid4().hex[:12]


# Trigger oportunista de backup automático: chequea cada N requests si toca
# correr. El chequeo es liviano (1 query) y solo lanza el backup si han
# pasado >23h del último completado. Multi-worker safe via backup_log lock.
_backup_check_counter = [0]
_BACKUP_CHECK_EVERY_N_REQUESTS = 50


@app.before_request
def _maybe_trigger_backup():
    """Cada N requests, evalúa si toca correr backup automático."""
    _backup_check_counter[0] += 1
    if _backup_check_counter[0] % _BACKUP_CHECK_EVERY_N_REQUESTS != 0:
        return
    try:
        from backup import should_run_backup, trigger_backup_async
        from database import get_db
        if should_run_backup(get_db()):
            trigger_backup_async(triggered_by="auto")
    except Exception:
        # Backup falla en silencio — no debe afectar el request del usuario.
        pass


@app.after_request
def _inject_chat_widget(response):
    """Inyectar el widget flotante 💬 EOS Chat en TODAS las paginas HTML
    autenticadas — excepto /chat /login /logout (donde seria redundante).

    Sebastian (29-abr-2026): "vista lateral persistente tipo WhatsApp Web
    — boton flotante en cualquier pagina". Se hace via after_request para
    no tener que editar cada template.
    """
    try:
        if not session.get('compras_user'):
            return response  # Anonimos no ven el widget
        path = request.path or ''
        if path.startswith('/chat') or path.startswith('/login') or path.startswith('/logout'):
            return response
        if path.startswith('/api/') or path.startswith('/static/'):
            return response
        ct = (response.headers.get('Content-Type') or '').lower()
        if not ct.startswith('text/html'):
            return response
        # Solo inyectar si la respuesta tiene </body>
        body = response.get_data(as_text=True)
        if '</body>' not in body:
            return response
        snippet = ('<script src="/api/chat/widget.js" async></script>'
                   '<script src="/api/notif/widget.js" async></script>')
        # Usar rsplit (último </body>) para evitar inyectar dentro de strings JS
        # como w.document.write('<html><body>...</body></html>') que aparece
        # en compras_html.py / recepcion_html.py / salida_html.py.
        # Sebastian (29-abr-2026): el replace original con count=1 reemplazaba
        # el PRIMER </body> que estaba en string literal JS, rompiendo todo
        # el script de /compras.
        idx = body.rfind('</body>')
        body = body[:idx] + snippet + body[idx:]
        response.set_data(body)
        # Refrescar Content-Length
        response.headers['Content-Length'] = str(len(response.get_data()))
    except Exception:
        pass  # Inyeccion no critica — fallar silenciosamente
    return response


@app.after_request
def _no_cache_html(response):
    """Forzar no-cache en TODAS las páginas HTML del app.

    Sin este header, el navegador del usuario cachea HTML viejo y nunca
    recibe los nuevos templates después de un deploy — los botones quedan
    apuntando a JS viejo, los IDs no coinciden, y los handlers no responden.
    Causa raíz reportada: 'ningún botón sirve' después de fixes desplegados.

    Solo aplica a HTML — NO toca /api/* (JSON), assets estáticos, ni PDFs
    (esos pueden y deben cachearse por el ETag/Last-Modified default).
    """
    try:
        content_type = (response.headers.get("Content-Type") or "").lower()
        if content_type.startswith("text/html"):
            response.headers["Cache-Control"] = (
                "no-cache, no-store, must-revalidate, max-age=0"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
    except Exception:
        pass
    return response


@app.after_request
def _log_request(response):
    """Log estructurado de cada request — parseable por Render/Datadog/Grafana.

    Incluye request_id para correlacionar logs entre middleware, blueprints y
    error handlers. El header X-Request-Id se devuelve al cliente para que
    pueda referenciarlo al reportar bugs.
    """
    try:
        import json as _json
        rid = getattr(request, "id", "-")
        response.headers["X-Request-Id"] = rid
        duration_ms = round((_time_module.time() - getattr(request, "_start_time", _time_module.time())) * 1000, 1)
        _logger.info(_json.dumps({
            "ts":         __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "request_id": rid,
            "method":     request.method,
            "path":       request.path,
            "status":     response.status_code,
            "ms":         duration_ms,
            "user":       session.get("compras_user", "-"),
            "ip":         request.headers.get("X-Forwarded-For", request.remote_addr or "-").split(",")[0].strip(),
        }, ensure_ascii=False))
    except Exception:
        pass
    return response


@app.errorhandler(Exception)
def _unhandled_exception(e):
    """Captura cualquier excepcion no manejada, loguea stack trace estructurado
    y devuelve un JSON consistente al cliente con el request_id para soporte.

    Excepciones HTTP de Werkzeug (404, 401, etc.) se delegan a sus handlers
    nativos — solo aplica a errores 5xx y bugs no anticipados.
    """
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return e
    import traceback as _tb
    import json as _json
    rid = getattr(request, "id", "-")
    try:
        _logger.error(_json.dumps({
            "ts":         __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "level":      "ERROR",
            "request_id": rid,
            "method":     request.method,
            "path":       request.path,
            "user":       session.get("compras_user", "-"),
            "exception":  type(e).__name__,
            "message":    str(e)[:500],
            "trace":      _tb.format_exc()[-2000:],
        }, ensure_ascii=False))
    except Exception:
        pass
    # Audit zero-error 2-may-2026: NO incluir traceback en la respuesta JSON
    # ni siquiera para admins. Si la sesión admin está comprometida o se
    # comparte pantalla, el traceback expone paths internos, schema, secrets.
    # Los admins consultan logs de Render con request_id (incluido aquí).
    user = session.get("compras_user", "")
    is_admin = user in ADMIN_USERS if 'ADMIN_USERS' in globals() else False
    payload = {
        "error": "Error interno del servidor",
        "request_id": rid,
    }
    if is_admin:
        # Solo el TIPO de excepción + mensaje corto, sin traceback ni path/method
        # (path ya se ve en network tab, traceback va a logs).
        payload["tipo"] = type(e).__name__
        payload["mensaje"] = str(e)[:200]
    return jsonify(payload), 500


@app.route('/api/health')
@app.route('/healthz')          # alias estandar para uptime monitors (Pingdom, UptimeRobot, Better Stack)
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

@app.route('/admin/system-health')
def admin_system_health_page():
    """Dashboard ejecutivo de salud del sistema · solo Admin.

    Renderiza UI compacta consumiendo /api/admin/health-detailed.
    Una sola pantalla con todos los semáforos operacionales.
    """
    if 'compras_user' not in session:
        return redirect('/login?next=/admin/system-health')
    user = session.get('compras_user', '')
    if user not in ADMIN_USERS:
        return Response('<h1>403</h1><p>Solo administradores</p>', status=403, mimetype='text/html')
    from templates_py.system_health_html import SYSTEM_HEALTH_HTML
    return Response(SYSTEM_HEALTH_HTML, mimetype='text/html')


@app.route('/api/admin/health-detailed')
def health_detailed():
    """Diagnóstico exhaustivo del sistema · audit zero-error · solo Admin.

    Verifica:
    - DB · migraciones aplicadas · indexes presentes
    - Helpers (audit_helpers, http_helpers) importables
    - Cron jobs registrados
    - Tablas críticas con datos esperados
    - Audit log accesible y reciente
    - Sentry status
    - Backups status
    Retorna por sección con OK/WARNING/ERROR.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if user not in ADMIN_USERS:
        return jsonify({'error': 'Solo Admin'}), 403

    out = {'timestamp': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
           'commit': os.environ.get('RENDER_GIT_COMMIT', 'unknown')[:8],
           'sections': {}}
    overall_ok = True

    # ── DB · migraciones ──────────────────────────────────────────────────
    try:
        from database import get_db, MIGRATIONS
        db = get_db()
        applied = {r[0] for r in db.execute(
            "SELECT version FROM schema_migrations").fetchall()}
        defined = {m[0] for m in MIGRATIONS}
        missing = sorted(defined - applied)
        out['sections']['migrations'] = {
            'status': 'ok' if not missing else 'warning',
            'applied_count': len(applied),
            'missing': missing[:10],
        }
        if missing:
            overall_ok = False
    except Exception as e:
        out['sections']['migrations'] = {'status': 'error', 'detail': str(e)[:200]}
        overall_ok = False

    # ── Indexes críticos ──────────────────────────────────────────────────
    try:
        critical_idx = ['idx_audit_accion', 'idx_desv_estado', 'idx_chg_estado',
                         'idx_qc_estado', 'idx_rcl_estado', 'idx_pedidos_cliente',
                         'idx_desv_detectado', 'idx_chg_solicitante']
        present = {r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        ).fetchall()}
        missing_idx = [i for i in critical_idx if i not in present]
        out['sections']['indexes'] = {
            'status': 'ok' if not missing_idx else 'warning',
            'critical_present': len(critical_idx) - len(missing_idx),
            'critical_total': len(critical_idx),
            'missing': missing_idx,
        }
        if missing_idx:
            overall_ok = False
    except Exception as e:
        out['sections']['indexes'] = {'status': 'error', 'detail': str(e)[:200]}

    # ── Helpers globales ──────────────────────────────────────────────────
    helpers_ok = True
    helper_status = {}
    try:
        from audit_helpers import audit_log, intentar_insert_con_retry, siguiente_codigo_secuencial
        helper_status['audit_helpers'] = 'ok'
    except Exception as e:
        helper_status['audit_helpers'] = f'error: {str(e)[:100]}'
        helpers_ok = False
    try:
        from http_helpers import fetch_with_retry, validate_money
        helper_status['http_helpers'] = 'ok'
    except Exception as e:
        helper_status['http_helpers'] = f'error: {str(e)[:100]}'
        helpers_ok = False
    out['sections']['helpers'] = {
        'status': 'ok' if helpers_ok else 'error', **helper_status,
    }
    if not helpers_ok:
        overall_ok = False

    # ── Cron jobs ─────────────────────────────────────────────────────────
    try:
        from blueprints.auto_plan_jobs import JOBS_SCHEDULE
        out['sections']['crons'] = {
            'status': 'ok',
            'jobs_count': len(JOBS_SCHEDULE),
            'jobs': [j[0] for j in JOBS_SCHEDULE],
        }
    except Exception as e:
        out['sections']['crons'] = {'status': 'error', 'detail': str(e)[:200]}
        overall_ok = False

    # ── Audit log reciente ────────────────────────────────────────────────
    try:
        recent = db.execute(
            "SELECT COUNT(*) FROM audit_log WHERE fecha >= date('now','-7 days')"
        ).fetchone()[0]
        out['sections']['audit_log'] = {
            'status': 'ok' if recent > 0 else 'warning',
            'entries_last_7d': recent,
        }
        if recent == 0:
            out['sections']['audit_log']['hint'] = 'Sin entries en 7 días · regulatorio sospechoso'
    except Exception as e:
        out['sections']['audit_log'] = {'status': 'error', 'detail': str(e)[:200]}

    # ── ASG workflows · totales por tabla ────────────────────────────────
    try:
        asg_totals = {}
        for tabla in ('desviaciones', 'control_cambios', 'quejas_clientes', 'recalls'):
            try:
                count = db.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
                asg_totals[tabla] = count
            except Exception:
                asg_totals[tabla] = -1  # tabla no existe
        out['sections']['asg_workflows'] = {'status': 'ok', **asg_totals}
    except Exception as e:
        out['sections']['asg_workflows'] = {'status': 'error', 'detail': str(e)[:200]}

    # ── Backups ───────────────────────────────────────────────────────────
    try:
        from backup import list_backups, BACKUP_OFFSITE_URL
        backups = list_backups()
        last = backups[0] if backups else None
        out['sections']['backups'] = {
            'status': 'ok' if last else 'warning',
            'count': len(backups),
            'latest': last['filename'] if last else None,
            'latest_size_mb': last['size_mb'] if last else None,
            'offsite_configured': bool(BACKUP_OFFSITE_URL),
        }
        if not last:
            out['sections']['backups']['hint'] = 'Sin backups · ejecutar manualmente desde /admin'
    except Exception as e:
        out['sections']['backups'] = {'status': 'error', 'detail': str(e)[:200]}

    # ── Sentry ────────────────────────────────────────────────────────────
    sentry_dsn = os.environ.get('SENTRY_DSN', '').strip()
    out['sections']['sentry'] = {
        'status': 'ok' if sentry_dsn else 'warning',
        'configured': bool(sentry_dsn),
    }
    if not sentry_dsn:
        out['sections']['sentry']['hint'] = 'SENTRY_DSN no configurado · errores no se reportan'

    # ── INVIMA · registros vencidos o por vencer ──────────────────────────
    try:
        invima_row = db.execute("""
            SELECT
              SUM(CASE WHEN fecha_vencimiento != '' AND fecha_vencimiento < date('now') THEN 1 ELSE 0 END) as vencidos,
              SUM(CASE WHEN fecha_vencimiento != '' AND fecha_vencimiento BETWEEN date('now') AND date('now','+30 days') THEN 1 ELSE 0 END) as por_vencer_30d,
              SUM(CASE WHEN fecha_vencimiento != '' AND fecha_vencimiento BETWEEN date('now','+30 days') AND date('now','+90 days') THEN 1 ELSE 0 END) as por_vencer_90d
            FROM registros_invima WHERE estado='Vigente'
        """).fetchone()
        venc = (invima_row[0] or 0)
        v30 = (invima_row[1] or 0)
        v90 = (invima_row[2] or 0)
        st_invima = 'ok' if (venc == 0 and v30 == 0) else ('error' if venc > 0 else 'warning')
        out['sections']['invima'] = {
            'status': st_invima,
            'vencidos': venc, 'por_vencer_30d': v30, 'por_vencer_90d': v90,
        }
        if venc > 0:
            out['sections']['invima']['hint'] = f'{venc} registro(s) INVIMA vencido(s) · acción inmediata'
            overall_ok = False
    except Exception as e:
        out['sections']['invima'] = {'status': 'error', 'detail': str(e)[:200]}

    # ── Recalls activos ──────────────────────────────────────────────────
    try:
        rcl_row = db.execute("""
            SELECT
              COUNT(*) as total_abiertos,
              SUM(CASE WHEN clase_recall IS NULL OR clase_recall='' THEN 1 ELSE 0 END) as sin_clasificar,
              SUM(CASE WHEN notificacion_invima_at IS NULL THEN 1 ELSE 0 END) as sin_invima,
              SUM(CASE WHEN clase_recall='clase_I' AND estado != 'cerrado' THEN 1 ELSE 0 END) as clase_I_abiertos
            FROM recalls
            WHERE estado NOT IN ('cerrado', 'cancelado')
        """).fetchone()
        total_r = (rcl_row[0] or 0)
        sin_cl = (rcl_row[1] or 0)
        sin_inv = (rcl_row[2] or 0)
        c1 = (rcl_row[3] or 0)
        st_rcl = 'ok' if total_r == 0 else ('error' if c1 > 0 else 'warning')
        out['sections']['recalls'] = {
            'status': st_rcl,
            'total_abiertos': total_r, 'sin_clasificar': sin_cl,
            'sin_notificacion_invima': sin_inv, 'clase_I_abiertos': c1,
        }
        if c1 > 0:
            out['sections']['recalls']['hint'] = f'{c1} recall(s) Clase I abiertos · riesgo crítico'
            overall_ok = False
    except Exception as e:
        out['sections']['recalls'] = {'status': 'error', 'detail': str(e)[:200]}

    # ── Lotes en cuarentena por mucho tiempo ─────────────────────────────
    try:
        cuar_row = db.execute("""
            SELECT
              SUM(CASE WHEN julianday('now') - julianday(fecha) > 5 THEN 1 ELSE 0 END) as cuarentena_5d,
              SUM(CASE WHEN julianday('now') - julianday(fecha) > 10 THEN 1 ELSE 0 END) as cuarentena_10d
            FROM movimientos
            WHERE tipo='Entrada' AND estado_lote IN ('Cuarentena','CUARENTENA')
        """).fetchone()
        c5 = (cuar_row[0] or 0)
        c10 = (cuar_row[1] or 0)
        out['sections']['cuarentena'] = {
            'status': 'ok' if c5 == 0 else ('error' if c10 > 0 else 'warning'),
            'esperando_5d_o_mas': c5, 'esperando_10d_o_mas': c10,
        }
        if c10 > 0:
            out['sections']['cuarentena']['hint'] = f'{c10} lote(s) en cuarentena >10 días · liberar o rechazar'
    except Exception as e:
        out['sections']['cuarentena'] = {'status': 'error', 'detail': str(e)[:200]}

    # ── Cola de liberación PT ────────────────────────────────────────────
    try:
        lib_row = db.execute("""
            SELECT
              SUM(CASE WHEN estado='listo_revisar' THEN 1 ELSE 0 END) as listos,
              SUM(CASE WHEN estado='listo_revisar'
                       AND julianday('now') - julianday(COALESCE(fecha_min_liberacion, fecha_envasado)) > 5
                       THEN 1 ELSE 0 END) as atrasados_5d
            FROM cola_liberacion
        """).fetchone()
        listos = (lib_row[0] or 0)
        atras = (lib_row[1] or 0)
        out['sections']['liberacion_pt'] = {
            'status': 'ok' if atras == 0 else 'warning',
            'listos_para_liberar': listos, 'atrasados_5d_o_mas': atras,
        }
        if atras > 0:
            out['sections']['liberacion_pt']['hint'] = f'{atras} lote(s) PT esperan liberación >5 días'
    except Exception as e:
        out['sections']['liberacion_pt'] = {'status': 'error', 'detail': str(e)[:200]}

    # ── Hallazgos vencidos (INVIMA / crítico / mayor) ────────────────────
    try:
        hall_row = db.execute("""
            SELECT
              SUM(CASE WHEN estado != 'cerrado' AND fecha_limite < date('now') THEN 1 ELSE 0 END) as vencidos,
              SUM(CASE WHEN estado != 'cerrado' AND fecha_limite < date('now')
                       AND (origen='INVIMA' OR severidad IN ('critico','mayor')) THEN 1 ELSE 0 END) as criticos
            FROM hallazgos
            WHERE COALESCE(fecha_limite,'') != ''
        """).fetchone()
        venc_h = (hall_row[0] or 0)
        crit_h = (hall_row[1] or 0)
        out['sections']['hallazgos_vencidos'] = {
            'status': 'ok' if venc_h == 0 else ('error' if crit_h > 0 else 'warning'),
            'vencidos_total': venc_h, 'vencidos_criticos': crit_h,
        }
        if crit_h > 0:
            out['sections']['hallazgos_vencidos']['hint'] = f'{crit_h} hallazgo(s) crítico(s)/INVIMA vencido(s)'
            overall_ok = False
    except Exception as e:
        out['sections']['hallazgos_vencidos'] = {'status': 'error', 'detail': str(e)[:200]}

    # ── Caja vs commitments ──────────────────────────────────────────────
    try:
        ult = db.execute("""SELECT periodo, saldo_caja FROM gerencia_inputs
                            ORDER BY periodo DESC LIMIT 1""").fetchone()
        saldo = float(ult[1] or 0) if ult else 0.0
        # OCs autorizadas pero no pagadas (committed)
        committed = db.execute("""
            SELECT COALESCE(SUM(valor_total),0) FROM ordenes_compra
            WHERE estado IN ('Autorizada','Recibida','Parcial')
        """).fetchone()[0]
        committed = float(committed or 0)
        runway_ratio = (saldo / committed) if committed > 0 else None
        st_caja = 'ok'
        if committed > 0 and saldo < committed * 0.5:
            st_caja = 'error'
        elif committed > 0 and saldo < committed:
            st_caja = 'warning'
        out['sections']['caja'] = {
            'status': st_caja,
            'saldo_ultimo_input': saldo,
            'periodo_input': ult[0] if ult else None,
            'committed_ocs_autorizadas': committed,
            'cobertura_ratio': round(runway_ratio, 2) if runway_ratio else None,
        }
    except Exception as e:
        out['sections']['caja'] = {'status': 'error', 'detail': str(e)[:200]}

    # ── Salas de planta · estado actual ──────────────────────────────────
    try:
        sala_rows = db.execute("""SELECT estado, COUNT(*) FROM areas_planta
                                   GROUP BY estado""").fetchall()
        sala_dict = {r[0] or 'sin_estado': r[1] for r in sala_rows}
        out['sections']['salas'] = {'status': 'ok', **sala_dict}
    except Exception as e:
        out['sections']['salas'] = {'status': 'error', 'detail': str(e)[:200]}

    # ── MFA enrollment de admins ─────────────────────────────────────────
    try:
        mfa_rows = db.execute("""SELECT username FROM users_mfa
                                  WHERE enabled=1""").fetchall()
        enrolled = {r[0] for r in mfa_rows}
        admins_list = sorted(ADMIN_USERS)
        admins_with_mfa = [a for a in admins_list if a in enrolled]
        admins_without = [a for a in admins_list if a not in enrolled]
        out['sections']['mfa_admins'] = {
            'status': 'ok' if not admins_without else 'warning',
            'admins_total': len(admins_list),
            'admins_con_mfa': admins_with_mfa,
            'admins_sin_mfa': admins_without,
        }
        if admins_without:
            out['sections']['mfa_admins']['hint'] = (
                f"{len(admins_without)} admin(s) sin MFA · /api/mfa/setup"
            )
    except Exception as e:
        # users_mfa puede no existir si migración 58 no corrió
        out['sections']['mfa_admins'] = {'status': 'warning',
                                          'detail': f'tabla users_mfa no accesible: {str(e)[:100]}'}

    out['overall'] = 'ok' if overall_ok else 'warning'
    return jsonify(out)


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
