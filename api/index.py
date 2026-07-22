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
            # FIX 27-may · scrubbear también request.data (POST body) · sino
            # un POST con {"password":"xxx"} se manda crudo a Sentry SaaS.
            if 'request' in event:
                if 'data' in event['request']:
                    event['request']['data'] = _scrub_pii(event['request']['data'])
                if 'cookies' in event['request']:
                    event['request']['cookies'] = '<redacted>'
                if 'headers' in event['request']:
                    hdrs = event['request']['headers']
                    if isinstance(hdrs, dict):
                        for k in list(hdrs.keys()):
                            if k.lower() in ('authorization','cookie','x-csrf-token','x-api-key'):
                                hdrs[k] = '<redacted>'
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
    # Sebastián 14-may-2026: "que no me lo pida cada momentico · de vez
    # en cuando". Sesiones duran 60 días sin re-login (antes 30).
    PERMANENT_SESSION_LIFETIME=timedelta(days=60),
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
from blueprints.artes import bp as artes_bp
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
from blueprints.identidad import bp as identidad_bp
from blueprints.firmas import bp as firmas_bp
from blueprints.brd import bp as brd_bp
from blueprints.operario import bp as operario_bp
from blueprints.plan import bp as plan_bp
from blueprints.portal import bp as portal_bp

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
app.register_blueprint(artes_bp)
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
app.register_blueprint(identidad_bp)
app.register_blueprint(firmas_bp)
app.register_blueprint(brd_bp)
app.register_blueprint(operario_bp)
app.register_blueprint(plan_bp)
app.register_blueprint(portal_bp)

# ─── DB init + migraciones de esquema (idempotente) ────────────────────────
init_db()   # crea tablas + ejecuta run_migrations() internamente (solo SQLite)
run_seed_rrhh()
import logging as _log
_log.getLogger(__name__).info(
    "schema_migrations: %d versiones registradas", len(MIGRATIONS)
)

# Sebastián 23-may-2026 PM · CRÍTICO · en modo PostgreSQL init_db() retorna
# early y NO aplica migraciones · solo las aplica /api/admin/migrations-run
# manualmente. Resultado: migraciones nuevas añadidas al código que no se
# aplican en producción jamás. Acá detectamos pendientes al boot y las
# aplicamos automáticamente.
# FIX 23-may-PM v2 · primer intento usó _cur.execute(...).fetchall() que
# falla en psycopg directo · ahora usa el wrapper _Cursor de pg_adapter
# (el mismo que usa toda la app) que SÍ permite chain execute().fetchall()
# + logging explícito en cada paso para diag.
try:
    from database import _usa_postgres
    if _usa_postgres():
        _logger_mig = _log.getLogger('inventario.auto-mig-pg')
        _logger_mig.warning("AUTO-MIG-PG · iniciando · backend=PG")
        from database import db_connect
        from pg_compat import (
            translate_ddl, es_insert_or, reescribir_insert_or_ignore,
            es_ddl_a_saltar,
        )
        _BENIGN = (
            'duplicate column name', 'already exists', 'no such table',
            'duplicate column', 'duplicate key',
        )
        _c = db_connect()
        _logger_mig.warning("AUTO-MIG-PG · db_connect() OK · type=%s",
                             type(_c).__name__)
        try:
            _cur = _c.cursor()
            _logger_mig.warning("AUTO-MIG-PG · cursor() OK · type=%s",
                                 type(_cur).__name__)
            # Asegurar schema_migrations existe
            try:
                _cur.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version     INTEGER PRIMARY KEY,
                        applied_at  TEXT    NOT NULL DEFAULT to_char(now() AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'),
                        description TEXT    NOT NULL DEFAULT ''
                    )
                """)
                _c.commit()
                _logger_mig.warning("AUTO-MIG-PG · schema_migrations OK")
            except Exception as _e:
                _logger_mig.error("AUTO-MIG-PG · schema_migrations CREATE falló: %s", _e)
            # Leer versiones aplicadas · separar execute y fetchall (psycopg)
            _applied = set()
            try:
                _cur.execute("SELECT version FROM schema_migrations")
                _rows = _cur.fetchall()
                _applied = {r[0] for r in _rows}
                _logger_mig.warning("AUTO-MIG-PG · ya aplicadas: %s",
                                     sorted(_applied)[-5:])
            except Exception as _e:
                _logger_mig.error("AUTO-MIG-PG · SELECT versiones falló: %s", _e)
            _aplicadas = []
            _fallidas = []
            for _v, _desc, _stmts in sorted(MIGRATIONS, key=lambda m: m[0]):
                if _v in _applied:
                    continue
                _logger_mig.warning("AUTO-MIG-PG · ejecutando v%d · %d stmts",
                                     _v, len(_stmts))
                _v_ok = True
                for _stmt in _stmts:
                    if es_ddl_a_saltar(_stmt):
                        continue
                    try:
                        _stmt_pg = translate_ddl(_stmt)
                        # FIX 27-jun · solo pre-reescribir IGNORE acá; REPLACE lo maneja el cursor del adapter
                        # (pg_adapter dispatch). Antes esto llamaba el rewriter de IGNORE también para REPLACE →
                        # le anexaba 'ON CONFLICT DO NOTHING' sin quitar 'OR REPLACE' y el adapter agregaba OTRO
                        # ON CONFLICT → doble → syntax error en PG (rompió mig 297). Espeja pg_adapter:297-301.
                        if es_insert_or(_stmt_pg) == 'ignore':
                            _stmt_pg = reescribir_insert_or_ignore(_stmt_pg)
                        _cur.execute(_stmt_pg)
                        _c.commit()
                    except Exception as _e:
                        _msg = str(_e).lower()
                        if any(p in _msg for p in _BENIGN):
                            try:
                                _c.rollback()
                            except Exception:
                                pass
                            continue
                        _v_ok = False
                        _fallidas.append({'version': _v, 'stmt': _stmt[:80],
                                          'error': str(_e)[:200]})
                        _logger_mig.error(
                            "AUTO-MIG-PG v%d STMT FALLÓ · %s · stmt: %s",
                            _v, _e, _stmt[:120])
                        try:
                            _c.rollback()
                        except Exception:
                            pass
                        break
                if _v_ok:
                    try:
                        # Usar ? que el wrapper traduce a %s
                        _cur.execute(
                            "INSERT INTO schema_migrations (version, description) "
                            "VALUES (?, ?)",
                            (_v, _desc))
                        _c.commit()
                        _aplicadas.append(_v)
                        _logger_mig.warning("AUTO-MIG-PG · v%d REGISTRADA", _v)
                    except Exception as _e:
                        _logger_mig.error(
                            "AUTO-MIG-PG · no se pudo registrar v%d: %s", _v, _e)
                        try:
                            _c.rollback()
                        except Exception:
                            pass
            _logger_mig.warning(
                "AUTO-MIG-PG · RESUMEN · aplicadas=%s · fallidas=%d",
                _aplicadas, len(_fallidas))
            if _fallidas:
                for _f in _fallidas[:5]:
                    _logger_mig.error("AUTO-MIG-PG FALLA · %s", _f)
            # Audit 3-jun · cargar triggers PG (inmutabilidad EBR/firmas/audit).
            # Las migraciones SALTAN los CREATE TRIGGER en PG (es_ddl_a_saltar) y
            # pg_triggers.sql solo lo aplicaba el script one-time de migración →
            # en prod los triggers de inmutabilidad podían faltar (legajo liberado
            # MUTABLE). Es idempotente (CREATE OR REPLACE). NUNCA aborta el boot.
            try:
                _trg_path = os.path.join(os.path.dirname(__file__), 'pg_triggers.sql')
                if os.path.exists(_trg_path):
                    try:
                        _c.rollback()  # asegurar transacción limpia
                    except Exception:
                        pass
                    with open(_trg_path, encoding='utf-8') as _ftrg:
                        _trg_sql = _ftrg.read()
                    _c.executescript(_trg_sql)
                    _c.commit()
                    _logger_mig.warning("AUTO-MIG-PG · pg_triggers.sql cargado OK")
            except Exception as _e:
                _logger_mig.error(
                    "AUTO-MIG-PG · pg_triggers.sql FALLÓ (no aborta boot): %s", _e)
                try:
                    _c.rollback()
                except Exception:
                    pass
        finally:
            try:
                _c.close()
            except Exception:
                pass
except Exception as _e:
    import traceback as _tb
    _log.getLogger(__name__).error(
        "auto-mig-pg CRASH (no aborta boot) · %s\n%s",
        _e, _tb.format_exc()[:1000])

# Arrancar loops de background daemon (no bloqueantes).
# Solo si NO estamos en modo testing (los tests no necesitan loops corriendo).
# NOTA: este bloque corre al IMPORTAR el módulo · app.config['TESTING'] todavía
# no está seteado por conftest en ese momento, así que también chequeamos la env
# var EOS_DISABLE_DAEMONS (conftest la setea ANTES del import). Sin esto los
# daemons arrancaban en pytest y bloqueaban la BD ('database is locked').
if not app.config.get("TESTING") and not os.environ.get("EOS_DISABLE_DAEMONS"):
    try:
        from blueprints.marketing import _start_marketing_metrics_loop
        _start_marketing_metrics_loop()
        _log.getLogger(__name__).info("marketing-metrics-loop arrancado")
    except Exception as _e:
        _log.getLogger(__name__).warning("metrics-loop NO arrancó: %s", _e)
    # Sebastián 26-may-2026 PM · cron semanal reporte ejecutivo (lunes 8am Bogotá)
    try:
        from blueprints.marketing import _start_reporte_ejecutivo_loop
        _start_reporte_ejecutivo_loop()
        _log.getLogger(__name__).info("reporte-ejecutivo-loop arrancado")
    except Exception as _e:
        _log.getLogger(__name__).warning("reporte-ejecutivo-loop NO arrancó: %s", _e)
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

    # PERF 6-jul (Sebastián · diag fable) · catch-up: si ventas_diarias está VACÍA al boot (el cron 3×/día aún
    # no corrió · su reloj es UTC), poblarla en background con LOCK → así el DEPLOY mismo la llena y los fast-
    # paths de Necesidades/Abastecimiento no caen al parseo de ~39k órdenes (la causa del blanco/lento). Solo
    # un worker la corre (lock); los demás ven filas>0 y saltan. Sleep para no competir con el arranque.
    try:
        def _catchup_ventas_diarias():
            import time as _tt
            _tt.sleep(25)
            try:
                with app.app_context():
                    from database import get_db as _gdb
                    from blueprints.auto_plan_jobs import (_adquirir_lock_cron, _liberar_lock_cron,
                                                           job_refrescar_ventas_diarias)
                    _c = _gdb()
                    try:
                        _n = _c.execute("SELECT COUNT(*) FROM ventas_diarias").fetchone()[0]
                    except Exception:
                        _n = -1
                    if _n == 0 and _adquirir_lock_cron(_c, 'ventas_diarias_manual', ttl_horas=1):
                        _log.getLogger(__name__).warning("catch-up ventas_diarias · tabla vacía · poblando…")
                        try:
                            job_refrescar_ventas_diarias(app)
                        finally:
                            try:
                                _liberar_lock_cron(_gdb(), 'ventas_diarias_manual')
                            except Exception:
                                pass
            except Exception as _e2:
                _log.getLogger(__name__).warning("catch-up ventas_diarias NO corrió: %s", _e2)
        import threading as _thr_vd
        _thr_vd.Thread(target=_catchup_ventas_diarias, daemon=True).start()
    except Exception as _e:
        _log.getLogger(__name__).warning("catch-up ventas_diarias thread NO arrancó: %s", _e)

    # Sebastián 25-may-2026 · audit zero-error · DAEMON SUPERVISOR.
    # Antes los 3 daemons (marketing-metrics, auto-plan-cron, multi-cron)
    # se arrancaban una sola vez al boot · si alguno crasheaba dentro del
    # loop, moría silencioso y nadie se enteraba · producción quedaba sin
    # crons hasta el siguiente deploy. Ahora un 4to thread supervisor
    # cada 5 min re-llama iniciar_*() · que internamente detecta thread
    # muerto via .is_alive() y re-arranca. Idempotente · si todos vivos,
    # no-op. Log warning cuando relanza.
    def _daemon_supervisor():
        import time as _ts
        sup_log = _log.getLogger('daemon-supervisor')
        sup_log.info('daemon supervisor arrancado · check cada 300s')
        while True:
            try:
                _ts.sleep(300)  # 5 min
                # 1. marketing-metrics-loop · idempotente interno
                try:
                    from blueprints.marketing import _start_marketing_metrics_loop
                    _start_marketing_metrics_loop()
                except Exception as _ex:
                    sup_log.warning('marketing relaunch fallo: %s', _ex)
                # 1b. reporte-ejecutivo-loop · idempotente interno
                try:
                    from blueprints.marketing import _start_reporte_ejecutivo_loop
                    _start_reporte_ejecutivo_loop()
                except Exception as _ex:
                    sup_log.warning('reporte-ejecutivo relaunch fallo: %s', _ex)
                # 2. auto-plan-cron · detección is_alive
                try:
                    from blueprints.auto_plan_jobs import iniciar_cron as _ic
                    _ic(app)
                except Exception as _ex:
                    sup_log.warning('auto-plan-cron relaunch fallo: %s', _ex)
                # 3. multi-cron · detección is_alive
                try:
                    from blueprints.auto_plan_jobs import iniciar_multi_cron as _imc
                    _imc(app)
                except Exception as _ex:
                    sup_log.warning('multi-cron relaunch fallo: %s', _ex)
            except Exception as _ex_loop:
                sup_log.exception('supervisor crash: %s · backoff 60s', _ex_loop)
                try:
                    _ts.sleep(60)
                except Exception:
                    pass
    try:
        import threading as _thr
        _sup_t = _thr.Thread(target=_daemon_supervisor, daemon=True,
                              name='daemon-supervisor')
        _sup_t.start()
        _log.getLogger(__name__).info('daemon-supervisor arrancado')
    except Exception as _e_sup:
        _log.getLogger(__name__).warning('daemon-supervisor NO arrancó: %s', _e_sup)

    # Sebastián 22-may-2026 · One-shot al deploy · normalizar fórmulas con
    # abreviaturas. Corre en background después del startup para no bloquear.
    # Idempotente · si no hay nada que normalizar, no hace nada.
    def _normalizar_formulas_one_shot():
        import time as _t
        _t.sleep(60)  # esperar 60s a que el deploy estabilice (migrations finish)
        try:
            with app.app_context():
                from blueprints.auto_plan_jobs import job_auto_normalizar_formulas
                ok, resultado, _ = job_auto_normalizar_formulas(app)
                _log.getLogger('inventario').info(
                    "[deploy-normalizar-formulas] ok=%s resultado=%s",
                    ok, resultado,
                )
        except Exception as _e:
            _log.getLogger('inventario').warning(
                "[deploy-normalizar-formulas] fallo: %s", _e,
            )

    try:
        import threading as _threading
        _threading.Thread(
            target=_normalizar_formulas_one_shot,
            daemon=True,
            name='deploy-normalizar-formulas',
        ).start()
    except Exception as _e:
        _log.getLogger(__name__).warning("normalizar-formulas one-shot NO arrancó: %s", _e)



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
    # En tests NO disparar backups async: el thread copia/escribe la BD y
    # causa 'database is locked' intermitente en los tests que abren conexiones
    # sqlite crudas (test_planta_*). Audit ronda2 29-may-2026.
    if app.config.get("TESTING") or os.environ.get("EOS_DISABLE_DAEMONS"):
        return
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
    autenticadas + cortex.js (loader + error overlay) en TODAS las HTML.

    Sebastian (29-abr-2026): "vista lateral persistente tipo WhatsApp Web
    — boton flotante en cualquier pagina". Se hace via after_request para
    no tener que editar cada template.

    27-may-2026 PM · agregado cortex.js (oculta loader, captura errors JS,
    evita "pantalla en blanco" en mobile) · se inyecta para anonimos también.
    """
    try:
        path = request.path or ''
        if path.startswith('/api/') or path.startswith('/static/'):
            return response
        ct = (response.headers.get('Content-Type') or '').lower()
        if not ct.startswith('text/html'):
            return response
        # Defensa 6-jun: nunca tocar un cuerpo ya comprimido/encoded (decodificarlo
        # como texto lo corrompería). Con el cambio de _gzip_response el HTML ya no
        # llega comprimido acá, pero este guard lo deja a prueba de balas.
        if response.headers.get('Content-Encoding') or response.direct_passthrough:
            return response
        body = response.get_data(as_text=True)
        if '</body>' not in body:
            return response
        # cortex.js para TODOS (incluso /login /logout) · sin async para que
        # cx-ready se aplique antes que el browser pinte loader 8s permanente
        snippet = '<script src="/static/cortex.js?v=eos3"></script>'
        # chat-widget + notif solo si autenticado y NO en /chat /login /logout
        # 29-jun · estas páginas van EMBEBIDAS en iframe dentro del dashboard → NO inyectar el chat+campana
        # (si no, aparecen duplicados/solapados DENTRO del calendario · el dashboard padre ya los tiene).
        _embebidas = ('/admin/plan-calendario', '/planta/kanban', '/admin/factibilidad-plan', '/admin/marcacion-envases')
        # 9-jul · páginas de RÓTULO / impresión: NO inyectar campana+chat (flotan encima del rótulo
        # y tapan el QR/datos al imprimir · Sebastián). Cubre /rotulos, /rotulo-recepcion, /rotulo-recepcion-mee, etc.
        _es_impresion = path.startswith('/rotulo') or '/rotulos' in path
        if (session.get('compras_user')
                and not (path.startswith('/chat')
                         or path.startswith('/login')
                         or path.startswith('/logout')
                         or path in _embebidas
                         or _es_impresion)):
            snippet += ('<script src="/api/chat/widget.js" async></script>'
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
def _perf_cache_headers(response):
    """OLA Performance · 20-may-2026 · Cache-Control para endpoints de
    lectura que se llaman cada 30-60s por auto-refresh. Evita re-fetch
    si el browser tiene una copia de hace 20s.

    Solo aplica a GET de endpoints listados · max-age corto (20-30s)
    porque son datos vivos · no static assets.
    """
    try:
        if request.method != 'GET':
            return response
        if response.status_code != 200:
            return response
        p = request.path or ''
        CACHE_20S = (
            '/api/dashboard/insights',
            '/api/dashboard-stats',
            '/api/planta/oee',
            '/api/planta/kanban-eta',
            '/api/planta/alertas-mee',
        )
        CACHE_30S = (
            '/api/inventario',
            '/api/alertas-reabastecimiento',
            '/api/planta/tablero-equipo',
        )
        if any(p.startswith(x) for x in CACHE_20S):
            response.headers['Cache-Control'] = 'private, max-age=20, must-revalidate'
        elif any(p.startswith(x) for x in CACHE_30S):
            response.headers['Cache-Control'] = 'private, max-age=30, must-revalidate'
        # /planta y /inventarios (HTML) cache corto · 60s
        elif p in ('/planta', '/inventarios'):
            response.headers['Cache-Control'] = 'private, max-age=60, must-revalidate'
    except Exception:
        pass
    return response


@app.after_request
def _gzip_response(response):
    """OLA Performance · 20-may-2026 · Sebastián.

    Comprime HTML/JSON > 1KB con gzip si el cliente lo soporta. Reduce
    el dashboard de planta (1.3MB HTML) a ~180KB (~7x más rápido en red).

    No comprime:
      - Respuestas binarias (imágenes, PDF, etc.)
      - Respuestas ya comprimidas (Content-Encoding ya set)
      - Streaming responses (direct_passthrough)
      - <1KB (overhead no vale)
    """
    try:
        accept_enc = request.headers.get('Accept-Encoding', '')
        if 'gzip' not in accept_enc.lower():
            return response
        # Solo JSON / texto / JS / CSS · NO HTML.
        ct = (response.content_type or '').lower()
        # 6-jun-2026 · NO gzipear text/html en la app. Cloudflare ya comprime el
        # HTML en el edge; hacerlo también acá causaba doble-manejo de compresión
        # (Content-Encoding:gzip + proxy) y, combinado con _inject_chat_widget que
        # corre DESPUÉS del gzip (orden inverso de Flask), podía romper/cortar el
        # <script> final en el navegador → página "Cargando…" eterna. Dejar el
        # HTML sin comprimir en origen y que Cloudflare lo gzipee es lo robusto.
        if 'text/html' in ct:
            return response
        if not any(t in ct for t in ('text/', 'application/json', 'application/javascript',
                                       'application/xml')):
            return response
        if response.direct_passthrough:
            return response
        if response.headers.get('Content-Encoding'):
            return response
        # Status no comprimibles
        if response.status_code < 200 or response.status_code >= 300:
            return response
        body = response.get_data()
        if len(body) < 1024:
            return response
        import gzip as _gzip
        compressed = _gzip.compress(body, compresslevel=6)
        response.set_data(compressed)
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = str(len(compressed))
        # Vary: para que proxies cacheen distinto según Accept-Encoding
        vary = response.headers.get('Vary', '')
        if 'Accept-Encoding' not in vary:
            response.headers['Vary'] = (vary + ', Accept-Encoding').strip(', ')
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
            "ts":         __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
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
        # 15-jun · una ruta /api/* NUNCA debe devolver HTML a un fetch (rompe el
        # JSON.parse del front con "Unexpected token '<'"). Devolvemos JSON con el
        # código real. Las páginas (no /api/) conservan la página HTML de Werkzeug.
        try:
            if request.path.startswith('/api/'):
                return jsonify({'error': getattr(e, 'description', str(e)) or 'Error',
                                'code': getattr(e, 'code', 500)}), (getattr(e, 'code', 500) or 500)
        except Exception:
            pass
        return e
    import traceback as _tb
    import json as _json
    rid = getattr(request, "id", "-")
    try:
        _logger.error(_json.dumps({
            "ts":         __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
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


@app.route('/diag/huerfanos-actuales')
def diag_huerfanos_actuales():
    """Lista huérfanos vendiendo 60d · sin auth · read-only.
    Más fácil para que Sebastián vea desde curl sin login.
    """
    import json as _json
    from datetime import datetime as _dt2, timedelta as _td2
    try:
        from database import get_db
        db = get_db()
        c = db.cursor()
        mapeados = set()
        for r in c.execute(
            "SELECT UPPER(TRIM(sku)) FROM sku_producto_map "
            "WHERE COALESCE(activo,1)=1"
        ).fetchall():
            mapeados.add(r[0])
        desde = (_dt2.utcnow() - _td2(days=60)).strftime('%Y-%m-%dT00:00:00')
        ventas = {}
        for r in c.execute(
            """SELECT sku_items FROM animus_shopify_orders
               WHERE creado_en >= ? AND sku_items IS NOT NULL
                 AND sku_items != ''
                 AND LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided')
                 AND LOWER(COALESCE(estado_pago,'')) NOT IN ('refunded','voided','partially_refunded')""",
            (desde,),
        ).fetchall():
            try:
                items = _json.loads(r[0]) if r[0] else []
            except Exception:
                continue
            if not isinstance(items, list):
                continue
            for it in items:
                sk = (it.get('sku') or '').upper().strip()
                if not sk:
                    continue
                qty = float(it.get('qty') or it.get('quantity') or it.get('cantidad') or 0)
                ventas[sk] = ventas.get(sk, 0) + qty
        huerfanos = sorted(
            [{'sku': k, 'uds_60d': v} for k, v in ventas.items() if k not in mapeados],
            key=lambda x: -x['uds_60d'])
        return jsonify({'ok': True, 'n_huerfanos': len(huerfanos),
                        'huerfanos': huerfanos})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:200]}), 500


@app.route('/diag/animus-calc/<path:producto>')
def diag_animus_calc(producto):
    """Sebastián 24-may · 'BHA refrescado pero sigue sin mapear en UI'
    aunque diag dice 740 uds. Endpoint que ejecuta directamente
    _calcular_animus_dtc para detectar dónde falla el match (case,
    whitespace, etc).
    """
    try:
        from database import get_db
        from blueprints.plan import _calcular_animus_dtc
        db = get_db()
        productos = _calcular_animus_dtc(db.cursor(), ventana=60,
                                           cob_critico=20, cob_alerta=25,
                                           cob_vigilar=45)
        match = (producto or '').strip().upper()
        encontrado = [p for p in (productos or [])
                       if (p.get('producto_nombre') or '').strip().upper() == match
                       or match in (p.get('producto_nombre') or '').upper()]
        return jsonify({
            'ok': True,
            'producto_buscado': producto,
            'n_productos_calculados': len(productos or []),
            'matches': [{
                'producto_nombre': p.get('producto_nombre'),
                'velocidad_uds_dia': p.get('velocidad_uds_dia'),
                'velocidad_kg_dia': p.get('velocidad_kg_dia'),
                'ventas_periodo_uds': p.get('ventas_periodo_uds'),
                'stock_uds_total': p.get('stock_uds_total'),
                'dias_cobertura': p.get('dias_cobertura'),
                'urgencia': p.get('urgencia'),
                'ml_unidad': p.get('ml_unidad'),
                'ml_inferido': p.get('ml_inferido'),
                'lote_bulk_kg': p.get('lote_bulk_kg'),
                'lote_bulk_kg_bd': p.get('lote_bulk_kg_bd'),
                'lote_calculado': p.get('lote_calculado'),
                'lote_size_faltante': p.get('lote_size_faltante'),
                'sin_mapeo_shopify': p.get('sin_mapeo_shopify'),
            } for p in encontrado],
        })
    except Exception as e:
        import traceback as _tb
        return jsonify({'ok': False, 'error': str(e)[:200],
                        'trace': _tb.format_exc()[:500]}), 500


@app.route('/diag/producto-ventas/<path:producto>')
def diag_producto_ventas(producto):
    """Sebastián 23-may-2026 PM · 'suero exfoliante bha no hace match
    adecuado · dice 300/mes pero no es verdad'. Endpoint público
    diagnóstico (sin auth · solo lectura · sin datos sensibles).

    Devuelve para el producto buscado (LIKE case-insensitive):
    - nombres canónicos encontrados en formula_headers
    - SKUs mapeados en sku_producto_map activos
    - ml configurados en producto_presentaciones
    - ventas últimos 60d por SKU mapeado (con filtro cancelled/refunded
      aplicado vs sin filtro · para detectar si se están perdiendo ventas)
    - SKUs HUÉRFANOS vendiendo con sustring del producto
      (ej. busca 'SAH', 'BHA' en sku_items de animus_shopify_orders
       que NO estén en sku_producto_map)
    """
    try:
        from database import get_db
        import json as _json
        db = get_db()
        c = db.cursor()
        prod_like = '%' + (producto or '').strip().upper() + '%'
        out = {'ok': True, 'producto_buscado': producto}

        # 1. formula_headers · nombres canónicos
        try:
            rows = c.execute(
                """SELECT producto_nombre, codigo_pt, lote_size_kg, activo
                   FROM formula_headers
                   WHERE UPPER(TRIM(producto_nombre)) LIKE ?
                   ORDER BY producto_nombre""",
                (prod_like,),
            ).fetchall()
            out['formula_headers'] = [{
                'producto_nombre': r[0], 'codigo_pt': r[1],
                'lote_size_kg': float(r[2] or 0), 'activo': int(r[3] or 0),
            } for r in rows]
        except Exception as e:
            out['fh_err'] = str(e)[:200]

        # 2. SKUs mapeados
        canonicos = [x['producto_nombre'] for x in out.get('formula_headers', [])]
        if canonicos:
            try:
                qs = ','.join(['?'] * len(canonicos))
                rows = c.execute(
                    f"""SELECT sku, producto_nombre, activo
                        FROM sku_producto_map
                        WHERE UPPER(TRIM(producto_nombre)) IN ({qs})
                        ORDER BY sku""",
                    tuple(x.upper().strip() for x in canonicos),
                ).fetchall()
                out['skus_mapeados'] = [{
                    'sku': r[0], 'producto_nombre': r[1],
                    'activo': int(r[2] or 0),
                } for r in rows]
            except Exception as e:
                out['skus_err'] = str(e)[:200]
        else:
            out['skus_mapeados'] = []

        # 3. ml por SKU en producto_presentaciones
        skus = [x['sku'].upper() for x in out.get('skus_mapeados', [])]
        if skus:
            try:
                qs = ','.join(['?'] * len(skus))
                rows = c.execute(
                    f"""SELECT sku_shopify, volumen_ml, peso_g, activo
                        FROM producto_presentaciones
                        WHERE UPPER(TRIM(sku_shopify)) IN ({qs})""",
                    tuple(skus),
                ).fetchall()
                out['producto_presentaciones'] = [{
                    'sku_shopify': r[0],
                    'volumen_ml': float(r[1] or 0),
                    'peso_g': float(r[2] or 0),
                    'activo': int(r[3] or 0),
                } for r in rows]
            except Exception as e:
                out['pp_err'] = str(e)[:200]

        # 4. Ventas últimos 60d · con vs sin filtro
        from datetime import datetime as _dt, timedelta as _td
        desde = (_dt.utcnow() - _td(days=60)).strftime('%Y-%m-%dT00:00:00')
        try:
            rows_all = c.execute(
                """SELECT sku_items, estado, estado_pago, COUNT(*) OVER ()
                   FROM animus_shopify_orders
                   WHERE creado_en >= ?
                     AND sku_items IS NOT NULL AND sku_items != ''""",
                (desde,),
            ).fetchall()
            ventas_sin_filtro = {}
            ventas_con_filtro = {}
            cancelled_count = 0
            refunded_count = 0
            for r in rows_all:
                items_json = r[0] or ''
                est = (r[1] or '').lower()
                est_pago = (r[2] or '').lower()
                try:
                    items = _json.loads(items_json) if isinstance(items_json, str) else items_json
                except Exception:
                    continue
                if not isinstance(items, list):
                    continue
                es_cancelled = est in ('cancelled', 'cancelado', 'voided')
                es_refunded = est_pago in ('refunded', 'voided', 'partially_refunded')
                if es_cancelled:
                    cancelled_count += 1
                if es_refunded:
                    refunded_count += 1
                for it in items:
                    sk = (it.get('sku') or '').upper().strip()
                    if not sk:
                        continue
                    qty = float(it.get('qty') or it.get('quantity') or it.get('cantidad') or 0)
                    if sk not in ventas_sin_filtro:
                        ventas_sin_filtro[sk] = 0
                    ventas_sin_filtro[sk] += qty
                    if not es_cancelled and not es_refunded:
                        if sk not in ventas_con_filtro:
                            ventas_con_filtro[sk] = 0
                        ventas_con_filtro[sk] += qty
            # Filtrar por SKUs del producto
            ventas_prod_sin = {k: v for k, v in ventas_sin_filtro.items() if k in skus}
            ventas_prod_con = {k: v for k, v in ventas_con_filtro.items() if k in skus}
            out['ventas_60d_mapeados'] = {
                'sin_filtro': ventas_prod_sin,
                'con_filtro_cancelled_refunded': ventas_prod_con,
                'total_uds_sin_filtro': sum(ventas_prod_sin.values()),
                'total_uds_con_filtro': sum(ventas_prod_con.values()),
                'cancelled_orders_60d': cancelled_count,
                'refunded_orders_60d': refunded_count,
            }
            # 5. SKUs HUÉRFANOS · vendieron en 60d pero NO están en map
            mapeados_set = set(skus)
            huerfanos = {k: v for k, v in ventas_sin_filtro.items()
                         if k not in mapeados_set}
            # FIX 23-may-PM v2 · heurística substring 4-letras del primer
            # word fallaba (ej. "EXFOLIANTE BHA" → buscaba "EXFO" pero
            # SKUs reales son "BHA33"). Ahora prueba: cada palabra del
            # nombre, primeras 3-4-5 letras Y substrings comunes.
            substrings = []
            for w in (producto or '').upper().split():
                w = w.strip()
                if len(w) >= 3:
                    substrings.append(w[:3])
                    substrings.append(w[:4])
                if len(w) >= 5:
                    substrings.append(w[:5])
                substrings.append(w)  # palabra completa
            huerfanos_relevantes = {}
            for k, v in huerfanos.items():
                if any(s in k for s in substrings if s):
                    huerfanos_relevantes[k] = v
            out['skus_huerfanos_relevantes'] = huerfanos_relevantes
            out['n_skus_huerfanos_total'] = len(huerfanos)
            # Top 50 huérfanos por ventas (para detección manual)
            top50 = sorted(huerfanos.items(), key=lambda x: -x[1])[:50]
            out['top_50_huerfanos_por_ventas'] = [
                {'sku': k, 'uds_60d': v} for k, v in top50
            ]
        except Exception as e:
            out['ventas_err'] = str(e)[:200]

        return jsonify(out)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:200]}), 500


@app.route('/diag/abastecimiento-mp/<path:codigo>')
def diag_abastecimiento_mp(codigo):
    """Sebastián/Alejandro 22-jul · verificar que 'programado × fórmula' CUADRE con lo que pide
    abastecimiento, con dato real. Diag público read-only. Para una MP:
      - MOTOR (abastecimiento): consumo/deficit/neto_a_pedir/stock/cuarentena/pendiente por horizonte.
      - INDEPENDIENTE: productos que la usan (formula_items) × sus producciones programadas (kg) →
        gramos esperados = Σ kg × porcentaje/100 × 1000. Con desglose producto por producto.
      - CUADRA: compara el consumo del motor vs el independiente por horizonte.
    ?dias=90 (default) · uno o más separados por coma (ej ?dias=30,90,365)."""
    try:
        from database import get_db
        from blueprints.programacion import _consumo_horizontes_core
        from datetime import datetime as _dt, timedelta as _td
        db = get_db(); c = db.cursor()
        cod = (codigo or '').strip().upper()
        try:
            _dias = [int(x) for x in (request.args.get('dias', '90') or '90').split(',') if x.strip()][:4] or [90]
        except Exception:
            _dias = [90]
        out = {'ok': True, 'codigo_mp': cod, 'dias': _dias}
        # info MP
        info = c.execute("SELECT COALESCE(nombre_comercial,nombre_inci,codigo_mp), COALESCE(nombre_inci,''), COALESCE(proveedor,'') "
                         "FROM maestro_mps WHERE UPPER(TRIM(codigo_mp))=?", (cod,)).fetchone()
        out['existe_mp'] = bool(info)
        out['nombre'] = info[0] if info else None
        out['inci'] = info[1] if info else None
        # ── INDEPENDIENTE: productos que la usan × programado ──
        piso = (_dt.utcnow() - _td(hours=5)).date().isoformat()
        prods = c.execute("SELECT producto_nombre, COALESCE(porcentaje,0), COALESCE(cantidad_g_por_lote,0) "
                          "FROM formula_items WHERE UPPER(TRIM(material_id))=? ORDER BY producto_nombre", (cod,)).fetchall()
        indep = {str(d): 0.0 for d in _dias}
        desglose = []
        for pnom, pct, gpl in prods:
            # header activo?
            hz = c.execute("SELECT COALESCE(lote_size_kg,0), COALESCE(activo,1) FROM formula_headers "
                           "WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) ORDER BY COALESCE(activo,1) DESC LIMIT 1", (pnom,)).fetchone()
            lote_kg = float(hz[0]) if hz else 0.0
            activo = int(hz[1]) if hz else 1
            fila = {'producto': pnom, 'porcentaje': float(pct or 0), 'g_por_lote': float(gpl or 0),
                    'lote_size_kg': lote_kg, 'formula_activa': bool(activo), 'programado': {}}
            for d in _dias:
                cutoff = (_dt.utcnow() - _td(hours=5) + _td(days=d)).date().isoformat()
                pr = c.execute("SELECT COALESCE(SUM(COALESCE(cantidad_kg,0)),0), COUNT(*) FROM produccion_programada "
                               "WHERE UPPER(TRIM(producto))=UPPER(TRIM(?)) "
                               "AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado','esperando_recurso') "
                               "AND COALESCE(inventario_descontado_at,'')='' "
                               "AND fecha_programada>=? AND fecha_programada<=?", (pnom, piso, cutoff)).fetchone()
                kg = float(pr[0] or 0); nlotes = int(pr[1] or 0)
                # gramos esperados: %-first (kg × pct/100 × 1000). Si pct=0 y hay gpl, usar gpl × (kg/lote_size).
                if pct and pct > 0:
                    g = kg * (float(pct) / 100.0) * 1000.0
                elif gpl and gpl > 0 and lote_kg > 0:
                    g = float(gpl) * (kg / lote_kg)
                else:
                    g = 0.0
                fila['programado'][str(d)] = {'kg': round(kg, 2), 'lotes': nlotes, 'gramos_esperados': round(g, 1)}
                if activo:
                    indep[str(d)] += g
            desglose.append(fila)
        out['productos_que_usan'] = len(prods)
        out['desglose'] = desglose
        out['independiente_gramos'] = {str(d): round(indep[str(d)], 1) for d in _dias}
        # ── MOTOR: abastecimiento ──
        motor = {}
        try:
            data = _consumo_horizontes_core(db, list(_dias), True, True, 'comprometido', False, 'mp')
            _mp = None
            for it in (data.get('mps') or []):
                if str(it.get('codigo', '')).upper() == cod:
                    _mp = it; break
            if _mp is None:  # ¿es envase?
                for it in (data.get('mees') or []):
                    if str(it.get('codigo', '')).upper() == cod:
                        _mp = it; break
            if _mp:
                for d in _dias:
                    dk = str(d)
                    motor[dk] = {
                        'consumo': round(float((_mp.get('consumo') or {}).get(dk, 0) or 0), 1),
                        'deficit': round(float((_mp.get('deficit') or {}).get(dk, 0) or 0), 1),
                        'neto_a_pedir': round(float((_mp.get('neto_a_pedir') or {}).get(dk, 0) or 0), 1),
                    }
                motor['stock_g'] = _mp.get('stock_actual_g', _mp.get('stock_actual_u'))
                motor['cuarentena'] = _mp.get('cuarentena_g', _mp.get('cuarentena_u'))
                motor['pendiente'] = _mp.get('pendiente_compras_g', _mp.get('pendiente_compras_u'))
                motor['productos_motor'] = len(_mp.get('productos') or [])
            else:
                out['motor_nota'] = 'la MP no aparece en el motor (sin consumo en el horizonte, o no es MP/MEE controlada)'
        except Exception as _em:
            out['motor_err'] = str(_em)[:250]
        out['motor'] = motor
        # ── CUADRA ──
        cuadra = {}
        for d in _dias:
            dk = str(d)
            m = float((motor.get(dk) or {}).get('consumo', 0) or 0)
            i = float(indep.get(dk, 0) or 0)
            diff = round(m - i, 1)
            tol = max(1.0, i * 0.02)
            cuadra[dk] = {'motor_consumo': m, 'independiente': round(i, 1), 'diferencia': diff,
                          'cuadra': abs(diff) <= tol}
        out['cuadra'] = cuadra
        return jsonify(out)
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e)[:250], 'trace': traceback.format_exc()[-600:]}), 500


@app.route('/diag/envasado-estado')
def diag_envasado_estado():
    """Sebastián 21-jul · "sigue sin salirme nada en Envasado". Diag público read-only (sin datos
    sensibles · solo metadata de legajos) para ver por qué la lista de Envasado sale vacía:
    - conteo de ebr_ejecuciones por (fase, estado)
    - legajos de ENVASADO existentes (id, lote, estado)
    - fabricaciones LIBERADAS y si cada una tiene su legajo de envasado
    - corre la MISMA query de ordenes-unificadas(fase=envasado) y reporta filas / error real."""
    try:
        from database import get_db
        db = get_db(); c = db.cursor()
        out = {'ok': True}
        # 1. conteo por fase+estado
        try:
            rows = c.execute("SELECT COALESCE(fase,'fabricacion'), COALESCE(estado,''), COUNT(*) "
                             "FROM ebr_ejecuciones GROUP BY COALESCE(fase,'fabricacion'), COALESCE(estado,'')").fetchall()
            out['conteo_fase_estado'] = [{'fase': r[0], 'estado': r[1], 'n': r[2]} for r in rows]
        except Exception as e:
            out['conteo_err'] = str(e)[:200]
        # 2. legajos de envasado existentes
        try:
            rows = c.execute("SELECT id, COALESCE(lote_codigo,lote,''), COALESCE(estado,''), COALESCE(numero_op,''), "
                             "COALESCE(iniciado_at_utc,'') FROM ebr_ejecuciones "
                             "WHERE COALESCE(fase,'fabricacion')='envasado' ORDER BY id DESC LIMIT 30").fetchall()
            out['envasado_legajos'] = [{'id': r[0], 'lote': r[1], 'estado': r[2], 'op': r[3], 'iniciado': r[4]} for r in rows]
        except Exception as e:
            out['envasado_err'] = str(e)[:200]
        # 3. fabricaciones LIBERADAS y si tienen envasado
        try:
            rows = c.execute("SELECT id, COALESCE(lote_codigo,lote,''), COALESCE(estado,''), COALESCE(mbr_template_id,0) "
                             "FROM ebr_ejecuciones WHERE COALESCE(fase,'fabricacion')='fabricacion' "
                             "AND LOWER(COALESCE(estado,''))='liberado' ORDER BY id DESC LIMIT 30").fetchall()
            fabs = []
            for r in rows:
                lote = r[1]
                tiene_env = c.execute("SELECT COUNT(*) FROM ebr_ejecuciones WHERE COALESCE(fase,'fabricacion')='envasado' "
                                      "AND COALESCE(lote_codigo,lote)=?", (lote,)).fetchone()[0]
                # producto del MBR (para ver si _erow[1] estaría vacío → el hook no dispara)
                prod = c.execute("SELECT COALESCE(producto_nombre,''), COALESCE(estado,'') FROM mbr_templates WHERE id=?", (r[3],)).fetchone()
                fabs.append({'id': r[0], 'lote': lote, 'estado': r[2], 'mbr_id': r[3],
                             'mbr_producto': (prod[0] if prod else '(MBR no existe)'),
                             'mbr_estado': (prod[1] if prod else ''),
                             'tiene_legajo_envasado': tiene_env})
            out['fabricaciones_liberadas'] = fabs
        except Exception as e:
            out['fab_err'] = str(e)[:200]
        # 4. correr la MISMA query de ordenes-unificadas(envasado) y reportar filas / error
        try:
            rows = c.execute(
                "SELECT e.id, e.numero_op, e.produccion_id, COALESCE(e.lote_codigo, e.lote) AS lote, e.estado, "
                "e.cantidad_objetivo_g, e.cantidad_real_g, COALESCE(e.ml_envasable, NULL) AS ml_envasable, "
                "e.iniciado_at_utc, e.liberado_at_utc, COALESCE(e.fase,'fabricacion') AS fase, "
                "COALESCE(m.producto_nombre,'') AS producto FROM ebr_ejecuciones e "
                "LEFT JOIN mbr_templates m ON m.id = e.mbr_template_id "
                "WHERE COALESCE(e.fase,'fabricacion') = 'envasado' AND COALESCE(e.estado,'') != 'cancelado' "
                "ORDER BY e.iniciado_at_utc DESC").fetchall()
            out['ordenes_unificadas_envasado_query'] = {'ok': True, 'filas': len(rows),
                'lotes': [str(r[3]) for r in rows[:20]]}
        except Exception as e:
            out['ordenes_unificadas_envasado_query'] = {'ok': False, 'error': str(e)[:300]}
        return jsonify(out)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:200]}), 500


@app.route('/diag/sku-buscar')
def diag_sku_buscar():
    """Sebastián 23-may-PM · "BOOSTER ya sale en Shopy como booster tensor
    pero no me lo sugieres" · busca TODOS los SKUs (mapeados + huérfanos)
    que contengan la query · case-insensitive · sin tope por volumen.

    Query: ?q=BOOSTER o ?q=BT etc.
    """
    import json as _json
    from datetime import datetime as _dt2, timedelta as _td2
    q = (request.args.get('q') or '').strip().upper()
    if not q or len(q) < 2:
        return jsonify({'error': 'q requerido (min 2 chars)'}), 400
    try:
        from database import get_db
        db = get_db()
        c = db.cursor()
        # SKUs mapeados que matchean
        mapeados = []
        for r in c.execute(
            """SELECT sku, producto_nombre, COALESCE(activo,1)
                 FROM sku_producto_map
                WHERE UPPER(TRIM(sku)) LIKE ?
                ORDER BY sku""",
            ('%' + q + '%',),
        ).fetchall():
            mapeados.append({
                'sku': r[0], 'producto_nombre': r[1],
                'activo': int(r[2] or 0),
            })
        # SKUs vendidos 60d que matchean (huérfanos + mapeados)
        desde = (_dt2.utcnow() - _td2(days=60)).strftime('%Y-%m-%dT00:00:00')
        sku_to_qty = {}
        for r in c.execute(
            """SELECT sku_items FROM animus_shopify_orders
                WHERE creado_en >= ? AND sku_items IS NOT NULL
                  AND sku_items != ''
                  AND LOWER(COALESCE(estado,'')) NOT IN ('cancelled','cancelado','voided')""",
            (desde,),
        ).fetchall():
            try:
                items = _json.loads(r[0]) if r[0] else []
            except Exception:
                continue
            if not isinstance(items, list):
                continue
            for it in items:
                sk = (it.get('sku') or '').upper().strip()
                if not sk or q not in sk:
                    continue
                qty = float(it.get('qty') or it.get('quantity') or it.get('cantidad') or 0)
                sku_to_qty[sk] = sku_to_qty.get(sk, 0) + qty
        # Marcar mapeado o huerfano
        mapeados_set = {m['sku'].upper() for m in mapeados}
        vendiendo = []
        for sku, qty in sorted(sku_to_qty.items(), key=lambda x: -x[1]):
            vendiendo.append({
                'sku': sku, 'uds_60d': qty,
                'huerfano': sku not in mapeados_set,
                'producto_mapeado': next(
                    (m['producto_nombre'] for m in mapeados
                     if m['sku'].upper() == sku), None),
            })
        return jsonify({
            'ok': True, 'q': q,
            'skus_en_mapeo': mapeados,
            'skus_vendiendo_60d': vendiendo,
            'n_mapeados': len(mapeados),
            'n_vendiendo': len(vendiendo),
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:200]}), 500


@app.route('/diag/productos-sin-sku')
def diag_productos_sin_sku():
    """Sebastián 23-may-PM · "BOOSTER TENSOR sin SKUs mapeados" ·
    audita TODOS los productos activos para detectar cuántos tienen
    0 SKUs en sku_producto_map · indicador de cuántos están reportando
    velocidad 0 falsa.
    """
    try:
        from database import get_db
        db = get_db()
        c = db.cursor()
        rows = c.execute(
            """SELECT fh.producto_nombre,
                      COALESCE(fh.lote_size_kg, 0),
                      COALESCE(fh.activo, 1),
                      (SELECT COUNT(*) FROM sku_producto_map sm
                        WHERE UPPER(TRIM(sm.producto_nombre)) =
                              UPPER(TRIM(fh.producto_nombre))
                          AND COALESCE(sm.activo,1)=1) AS n_skus,
                      (SELECT COUNT(*) FROM producto_presentaciones pp
                        WHERE UPPER(TRIM(pp.producto_nombre)) =
                              UPPER(TRIM(fh.producto_nombre))
                          AND COALESCE(pp.activo,1)=1) AS n_present
                 FROM formula_headers fh
                WHERE COALESCE(fh.activo,1) = 1
             ORDER BY n_skus ASC, fh.producto_nombre"""
        ).fetchall()
        sin_sku = []
        con_sku = 0
        for r in rows:
            if int(r[3] or 0) == 0:
                sin_sku.append({
                    'producto_nombre': r[0],
                    'lote_size_kg': float(r[1] or 0),
                    'n_skus_mapeados': 0,
                    'n_presentaciones': int(r[4] or 0),
                })
            else:
                con_sku += 1
        return jsonify({
            'ok': True,
            'n_productos_total': len(rows),
            'n_sin_sku': len(sin_sku),
            'n_con_sku': con_sku,
            'productos_sin_sku': sin_sku,
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:200]}), 500


@app.route('/diag/azh-mig-status')
def diag_azh_mig_status():
    """Sebastián 23-may-2026 PM · diagnóstico público (sin auth) para saber
    si auto-mig-pg al boot se aplicó · devuelve schema_migrations recientes
    + estado de AZ HIBRID CLEAR en formula_headers + producto_canonico_config.
    NO expone datos sensibles · solo es ID + lote.
    """
    try:
        from database import get_db
        db = get_db()
        c = db.cursor()
        out = {'ok': True}
        try:
            rows = c.execute(
                "SELECT version, description FROM schema_migrations "
                "ORDER BY version DESC LIMIT 10"
            ).fetchall()
            out['migraciones_recientes'] = [
                {'v': r[0], 'desc': str(r[1] or '')[:80]} for r in rows]
        except Exception as e:
            out['migraciones_recientes_error'] = str(e)[:200]
        try:
            row = c.execute(
                "SELECT lote_size_kg, unidad_base_g, activo "
                "FROM formula_headers "
                "WHERE UPPER(TRIM(producto_nombre)) = 'AZ HIBRID CLEAR'"
            ).fetchone()
            out['azh_formula_headers'] = {
                'lote_size_kg': float(row[0] or 0) if row else None,
                'unidad_base_g': float(row[1] or 0) if row else None,
                'activo': int(row[2] or 0) if row else None,
            }
        except Exception as e:
            out['azh_formula_headers_error'] = str(e)[:200]
        try:
            row = c.execute(
                "SELECT kg_por_lote FROM producto_canonico_config "
                "WHERE UPPER(TRIM(producto_nombre)) = 'AZ HIBRID CLEAR'"
            ).fetchone()
            out['azh_canonico_config_kg'] = (
                float(row[0] or 0) if row else None)
        except Exception as e:
            out['azh_canonico_config_error'] = str(e)[:200]
        try:
            # Cuántas Sugeridas activas hay con fecha futura
            row = c.execute(
                "SELECT COUNT(*) FROM produccion_programada "
                "WHERE substr(fecha_programada,1,10) >= '2026-05-23' "
                "AND COALESCE(origen,'') IN ('eos_canonico','auto_plan','sugerido','manual','calendar') "
                "AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado') "
                "AND fin_real_at IS NULL"
            ).fetchone()
            out['sugeridas_futuras_activas'] = int(row[0] or 0) if row else 0
        except Exception as e:
            out['sugeridas_futuras_error'] = str(e)[:200]
        return jsonify(out)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:200]}), 500


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

    out = {'timestamp': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
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

    # ── Drift de inventario · MP negativos + MEE drift persistido vs calc ──
    try:
        from inventario_helpers import drift_summary
        ds = drift_summary(db)
        total_drift = ds.get('total_items_con_drift', 0)
        mp_neg = ds.get('mp_negativos', 0)
        mee_drift = ds.get('mee_drift', 0)
        if total_drift == 0:
            st_drift = 'ok'
        elif mp_neg > 0 or mee_drift > 10:
            st_drift = 'error'
        else:
            st_drift = 'warning'
        out['sections']['inventario_drift'] = {
            'status': st_drift,
            'mp_stocks_negativos': mp_neg,
            'mee_con_drift': mee_drift,
            'total_items_afectados': total_drift,
        }
        if mp_neg > 0 or mee_drift > 0:
            top_msg = []
            for it in ds.get('mp_top', [])[:3]:
                top_msg.append(f"MP {it['codigo_mp']}: {it['stock_g']:.0f}g")
            for it in ds.get('mee_top', [])[:3]:
                top_msg.append(f"MEE {it['codigo']}: drift {it['drift']:+.0f}")
            out['sections']['inventario_drift']['top'] = top_msg[:5]
            out['sections']['inventario_drift']['hint'] = (
                f"{total_drift} item(s) con drift · revisar /admin/audit-inventario"
            )
            if st_drift == 'error':
                overall_ok = False
    except Exception as e:
        out['sections']['inventario_drift'] = {'status': 'error', 'detail': str(e)[:200]}

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


@app.route('/mi-bandeja')
def mi_bandeja_page():
    """Bandeja CEO · centro de comando con todo lo pendiente cross-módulo.

    Solo Admin. Consume /api/bandeja-ceo cada 60s.
    """
    if 'compras_user' not in session:
        return redirect('/login?next=/mi-bandeja')
    user = session.get('compras_user', '')
    if user not in ADMIN_USERS:
        return Response('<h1>403</h1><p>Solo administradores</p>',
                          status=403, mimetype='text/html')
    from templates_py.bandeja_ceo_html import BANDEJA_CEO_HTML
    return Response(BANDEJA_CEO_HTML, mimetype='text/html')


@app.route('/api/bandeja-ceo')
def bandeja_ceo():
    """Agregador de pendientes cross-módulo para el CEO.

    Categorías priorizadas por urgencia:
    - critical: requieren acción HOY (regulatorias o financieras críticas)
    - high: revisar en la semana
    - medium: revisar cuando se pueda

    Cada item lleva: titulo, descripcion, link, edad_dias, severidad,
    accion_sugerida.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if user not in ADMIN_USERS:
        return jsonify({'error': 'Solo Admin'}), 403

    from database import get_db
    db = get_db()
    items = []

    def _add(severidad, modulo, titulo, descripcion, link, edad_dias=None, registro_id=None):
        items.append({
            'severidad': severidad, 'modulo': modulo,
            'titulo': titulo, 'descripcion': descripcion,
            'link': link, 'edad_dias': edad_dias,
            'registro_id': registro_id,
        })

    # ── CRITICAL · Recalls Clase I sin notificar INVIMA ──
    try:
        rows = db.execute("""
            SELECT codigo, producto,
                   julianday('now') - julianday(clasificado_at) as dias
            FROM recalls
            WHERE clase_recall='clase_I'
              AND notificacion_invima_at IS NULL
              AND estado NOT IN ('cerrado','cancelado')
              AND clasificado_at IS NOT NULL
            ORDER BY clasificado_at LIMIT 10
        """).fetchall()
        for r in rows:
            _add('critical', 'recalls',
                  f"Recall Clase I {r[0]} sin notificar INVIMA",
                  f"Producto: {r[1] or '—'} · {r[2]:.0f}d desde clasificación (regulatorio <24h)",
                  '/aseguramiento#tab-recalls',
                  edad_dias=int(r[2] or 0), registro_id=r[0])
    except Exception:
        pass

    # ── CRITICAL · Hallazgos INVIMA / críticos / mayores vencidos ──
    try:
        rows = db.execute("""
            SELECT codigo, titulo, origen, severidad,
                   julianday('now') - julianday(fecha_limite) as dias_vencido
            FROM hallazgos
            WHERE estado NOT IN ('cerrado','rechazado')
              AND COALESCE(fecha_limite,'') != ''
              AND fecha_limite < date('now')
              AND (origen='INVIMA' OR severidad IN ('critico','mayor'))
            ORDER BY fecha_limite LIMIT 10
        """).fetchall()
        for r in rows:
            _add('critical', 'compliance',
                  f"Hallazgo {r[0]} ({r[2]} · {r[3]}) vencido",
                  f"{(r[1] or '')[:80]} · {r[4]:.0f}d vencido",
                  '/compliance',
                  edad_dias=int(r[4] or 0), registro_id=r[0])
    except Exception:
        pass

    # ── CRITICAL · Recalls sin clasificar >12h ──
    try:
        rows = db.execute("""
            SELECT codigo, producto,
                   (julianday('now') - julianday(creado_en)) * 24 as horas
            FROM recalls
            WHERE estado='iniciado'
              AND datetime(creado_en) <= datetime('now','-12 hours')
            ORDER BY creado_en LIMIT 10
        """).fetchall()
        for r in rows:
            _add('critical', 'recalls',
                  f"Recall {r[0]} sin clasificar",
                  f"Producto: {r[1] or '—'} · {r[2]:.0f}h sin clasificar",
                  '/aseguramiento#tab-recalls',
                  edad_dias=round(float(r[2] or 0)/24, 1), registro_id=r[0])
    except Exception:
        pass

    # ── HIGH · Lotes esperando liberación >5d ──
    try:
        rows = db.execute("""
            SELECT id, lote, producto_nombre,
                   julianday('now') - julianday(COALESCE(fecha_min_liberacion, fecha_envasado)) as dias
            FROM cola_liberacion
            WHERE estado='listo_revisar'
              AND julianday('now') - julianday(COALESCE(fecha_min_liberacion, fecha_envasado)) > 5
            ORDER BY fecha_min_liberacion LIMIT 10
        """).fetchall()
        for r in rows:
            _add('high', 'planta',
                  f"Lote PT {r[1]} esperando liberación {r[3]:.0f}d",
                  f"{r[2]} · cola_liberacion id={r[0]}",
                  '/aseguramiento',
                  edad_dias=int(r[3] or 0), registro_id=r[0])
    except Exception:
        pass

    # ── HIGH · OCs autorizadas pendientes de pago >7d ──
    try:
        rows = db.execute("""
            SELECT numero_oc, proveedor, valor_total,
                   julianday('now') - julianday(fecha_autorizacion) as dias
            FROM ordenes_compra
            WHERE estado='Autorizada'
              AND fecha_autorizacion IS NOT NULL
              AND julianday('now') - julianday(fecha_autorizacion) > 7
            ORDER BY fecha_autorizacion LIMIT 15
        """).fetchall()
        for r in rows:
            _add('high', 'compras',
                  f"OC {r[0]} autorizada hace {r[3]:.0f}d sin pagar",
                  f"{(r[1] or '')[:60]} · ${(r[2] or 0)/1_000_000:.1f}M",
                  '/compras',
                  edad_dias=int(r[3] or 0), registro_id=r[0])
    except Exception:
        pass

    # ── HIGH · Solicitudes influencer pendientes de aprobación ──
    try:
        rows = db.execute("""
            SELECT numero, solicitante, valor,
                   julianday('now') - julianday(fecha) as dias
            FROM solicitudes_compra
            WHERE estado='Pendiente'
              AND categoria IN ('Influencer/Marketing Digital','Cuenta de Cobro')
              AND julianday('now') - julianday(fecha) > 1
            ORDER BY fecha LIMIT 15
        """).fetchall()
        for r in rows:
            _add('high', 'compras',
                  f"SOL influencer {r[0]} pendiente {r[3]:.0f}d",
                  f"{(r[1] or '')[:50]} · ${(r[2] or 0)/1_000_000:.1f}M",
                  '/compras',
                  edad_dias=int(r[3] or 0), registro_id=r[0])
    except Exception:
        pass

    # ── HIGH · Quejas críticas sin responder >48h ──
    try:
        rows = db.execute("""
            SELECT codigo, severidad,
                   julianday('now') - julianday(fecha_recepcion) as dias
            FROM quejas_clientes
            WHERE estado IN ('recibida','en_investigacion')
              AND severidad IN ('critica','alta')
              AND julianday('now') - julianday(fecha_recepcion) > 2
            ORDER BY fecha_recepcion LIMIT 10
        """).fetchall()
        for r in rows:
            _add('high', 'aseguramiento',
                  f"Queja {r[0]} ({r[1]}) sin responder {r[2]:.0f}d",
                  f"Severidad {r[1]} · revisar urgente",
                  '/aseguramiento#tab-quejas',
                  edad_dias=int(r[2] or 0), registro_id=r[0])
    except Exception:
        pass

    # ── HIGH · Cambios pendientes de aprobación ──
    try:
        rows = db.execute("""
            SELECT codigo, titulo,
                   julianday('now') - julianday(fecha_solicitud) as dias
            FROM control_cambios
            WHERE estado='evaluacion'
              AND julianday('now') - julianday(fecha_solicitud) > 3
            ORDER BY fecha_solicitud LIMIT 10
        """).fetchall()
        for r in rows:
            _add('high', 'aseguramiento',
                  f"Cambio {r[0]} en evaluación {r[2]:.0f}d",
                  f"{(r[1] or '')[:60]}",
                  '/aseguramiento#tab-cambios',
                  edad_dias=int(r[2] or 0), registro_id=r[0])
    except Exception:
        pass

    # ── MEDIUM · Lotes en cuarentena >5d ──
    try:
        rows = db.execute("""
            SELECT id, lote, material_nombre,
                   julianday('now') - julianday(fecha) as dias
            FROM movimientos
            WHERE tipo='Entrada'
              AND estado_lote IN ('Cuarentena','CUARENTENA')
              AND julianday('now') - julianday(fecha) > 5
            ORDER BY fecha LIMIT 10
        """).fetchall()
        for r in rows:
            _add('medium', 'planta',
                  f"Lote MP {r[1]} en cuarentena {r[3]:.0f}d",
                  f"{(r[2] or '')[:60]}",
                  '/recepcion',
                  edad_dias=int(r[3] or 0), registro_id=r[0])
    except Exception:
        pass

    # ── HIGH · Drift de inventario (MP negativos o MEE drift persistido) ──
    try:
        from inventario_helpers import drift_summary
        ds = drift_summary(db)
        total = ds.get('total_items_con_drift', 0)
        if total > 0:
            mp_neg = ds.get('mp_negativos', 0)
            mee_drift = ds.get('mee_drift', 0)
            sev = 'critical' if mp_neg > 0 else 'high'
            partes = []
            if mp_neg: partes.append(f"{mp_neg} MP con stock NEGATIVO")
            if mee_drift: partes.append(f"{mee_drift} MEE con drift")
            _add(sev, 'planta',
                  f"Inventario · {total} item(s) con sesgo (cero sesgo violado)",
                  ' · '.join(partes),
                  '/admin/audit-inventario',
                  edad_dias=None, registro_id=None)
    except Exception:
        pass

    # ── MEDIUM · Registros INVIMA por vencer en 30d ──
    try:
        rows = db.execute("""
            SELECT producto, num_registro, fecha_vencimiento,
                   julianday(fecha_vencimiento) - julianday('now') as dias_restantes
            FROM registros_invima
            WHERE estado='Vigente'
              AND fecha_vencimiento != ''
              AND fecha_vencimiento BETWEEN date('now') AND date('now','+30 days')
            ORDER BY fecha_vencimiento LIMIT 10
        """).fetchall()
        for r in rows:
            _add('medium', 'tecnica',
                  f"Registro INVIMA {r[1]} vence en {r[3]:.0f}d",
                  f"{(r[0] or '')[:60]} · vence {r[2]}",
                  '/tecnica',
                  edad_dias=int(r[3] or 0), registro_id=r[1])
    except Exception:
        pass

    # ── Resumen agregado ──
    counts = {'critical': 0, 'high': 0, 'medium': 0}
    for it in items:
        counts[it['severidad']] = counts.get(it['severidad'], 0) + 1

    return jsonify({
        'timestamp': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'usuario': user,
        'total': len(items),
        'counts': counts,
        'items': items,
    })


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
