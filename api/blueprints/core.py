# blueprints/core.py — extraído de index.py (Fase C)
import os
import json
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response, session, redirect, url_for, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, PLANTA_USERS, CALIDAD_USERS, COMPRAS_ACCESS, CLIENTES_ACCESS
from database import db_connect
from auth import (
    _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec,
    sin_acceso_html, _ensure_csrf_token,
)
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


def _resolve_password_hash(username):
    """Devuelve el hash de password para un usuario, con fallback lazy.

    Prioridad:
      1. Tabla users_passwords en DB (si el usuario cambió su password
         vía /api/cambiar-password, su hash vive aquí).
      2. config.COMPRAS_USERS (env var PASS_<USER> en Render).

    Retorna '' si no hay ninguno (usuario no existe o env var ausente).
    Diseñado para ser robusto: si la DB falla, fallback automático a env.
    """
    if not username:
        return ''
    try:
        conn = db_connect()
        conn.execute("PRAGMA busy_timeout=2000")
        # Sebastián 21-may-2026 mig 149: respetar activo flag · si user
        # está desactivado (activo=0), devolver '' como si no existiera
        # · bloquea login efectivamente. NULL activo = 1 (default
        # legacy users).
        try:
            row = conn.execute(
                "SELECT password_hash, COALESCE(activo,1) FROM users_passwords WHERE username=?",
                (username,)
            ).fetchone()
        except Exception:
            row = conn.execute(
                "SELECT password_hash FROM users_passwords WHERE username=?",
                (username,)
            ).fetchone()
            if row:
                row = (row[0], 1)
        conn.close()
        if row and row[0]:
            if len(row) > 1 and not row[1]:
                # Usuario desactivado · bloquear login (no devolver hash)
                return ''
            return row[0]
    except Exception:
        # Tabla no existe (pre-migración) o DB no responde —
        # cae al fallback de env vars.
        pass
    return COMPRAS_USERS.get(username, '')

@bp.route('/api/csrf-token', methods=['GET'])
def csrf_token():
    """Devuelve el CSRF token actual de la sesión, generándolo si no existe.

    El frontend lo lee al cargar la app y lo envía como header X-CSRF-Token
    en cada POST/PUT/DELETE/PATCH. Defense in depth sobre el Origin check.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    return jsonify({'csrf_token': _ensure_csrf_token()})


@bp.route('/api/health')
def health():
    """Diagnostico publico — backend, version, tablas clave.

    Sebastián 12-may-2026: tras incidente 'database disk image is malformed',
    el endpoint retorna 503 si detecta malformed (SQLite) o si la BD no
    responde, para que Render y el monitoreo externo lo detecten.

    Migración Fase 5: el endpoint consulta el BACKEND ACTIVO (PostgreSQL o
    SQLite) vía db_connect() · antes leía siempre el archivo SQLite, lo que
    en modo PostgreSQL reportaba datos obsoletos.
    """
    import os as _os, subprocess as _sp
    from database import db_connect, _usa_postgres
    try:
        commit = _sp.check_output(['git', 'rev-parse', '--short', 'HEAD'],
            cwd=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
            stderr=_sp.DEVNULL).decode().strip()
    except Exception:
        commit = 'unknown'
    es_pg = _usa_postgres()
    tables = {}
    malformed = False
    error = None
    conn = None
    migrations_info = None
    try:
        conn = db_connect()
        if not es_pg:
            # PRAGMA quick_check solo aplica a SQLite.
            try:
                ic = conn.execute('PRAGMA quick_check').fetchone()
                if ic and ic[0] != 'ok':
                    malformed = True
            except sqlite3.DatabaseError:
                malformed = True
        for tbl in ['maestro_mps', 'solicitudes_compra', 'ordenes_compra',
                    'movimientos']:
            try:
                tables[tbl] = conn.execute(
                    'SELECT COUNT(*) FROM %s' % tbl).fetchone()[0]
            except Exception as e:
                tables[tbl] = 'err'
                if 'malformed' in str(e).lower() or 'corrupt' in str(e).lower():
                    malformed = True
        try:
            tables['planta_pendientes'] = conn.execute(
                "SELECT COUNT(*) FROM solicitudes_compra WHERE estado='Aprobada' "
                "AND area='Produccion' AND (numero_oc IS NULL OR numero_oc='')"
            ).fetchone()[0]
        except Exception:
            pass
        # Diagnóstico MEE · conteo público sin exponer detalles (Sebastián 27-may PM)
        # Para verificar desde curl si hay productos sin envase/volumen sin login.
        try:
            from datetime import date as _d, timedelta as _td
            _hoy = _d.today().isoformat()
            _hasta = (_d.today() + _td(days=60)).isoformat()
            _prods = conn.execute(
                """SELECT DISTINCT producto FROM produccion_programada
                   WHERE date(fecha_programada) BETWEEN ? AND ?
                     AND LOWER(COALESCE(estado,'')) NOT IN ('cancelado','completado')""",
                (_hoy, _hasta),
            ).fetchall()
            _mapeados = set()
            for _r in conn.execute(
                """SELECT DISTINCT UPPER(sku_codigo) FROM sku_mee_config
                   WHERE COALESCE(aplica,1)=1"""
            ).fetchall():
                _mapeados.add(_r[0])
            _con_vol = set()
            for _r in conn.execute(
                """SELECT UPPER(producto_nombre) FROM volumen_unitario_producto
                   WHERE COALESCE(activo,1)=1 AND COALESCE(volumen_ml,0) > 0"""
            ).fetchall():
                _con_vol.add(_r[0])
            _sin_map = 0; _sin_vol = 0
            for _r in _prods:
                _norm = (_r[0] or '').strip().upper()
                if _norm not in _mapeados: _sin_map += 1
                elif _norm not in _con_vol: _sin_vol += 1
            tables['mee_diag_sin_mapping'] = _sin_map
            tables['mee_diag_sin_volumen'] = _sin_vol
        except Exception:
            pass
        # Migraciones · versiones aplicadas vs pendientes (Sebastián 27-may PM)
        # Útil para verificar deploys sin admin login · sin exponer DDL/SQL.
        try:
            from database import MIGRATIONS as _MIGS
            _defined = sorted({m[0] for m in _MIGS})
            _applied = []
            try:
                _rows = conn.execute(
                    'SELECT version FROM schema_migrations ORDER BY version'
                ).fetchall()
                _applied = sorted({r[0] for r in _rows})
            except Exception:
                _applied = []
            _pendientes = [v for v in _defined if v not in set(_applied)]
            migrations_info = {
                'defined_total': len(_defined),
                'applied_total': len(_applied),
                'pending_total': len(_pendientes),
                'last_applied': _applied[-1] if _applied else None,
                'pending_versions': _pendientes[:10],
            }
        except Exception:
            migrations_info = None
    except Exception as e:
        error = str(e)
        if 'malformed' in str(e).lower() or 'corrupt' in str(e).lower():
            malformed = True
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    payload = {
        'status': 'error' if (malformed or error) else 'ok',
        'commit': commit,
        'db': {
            'backend': 'postgres' if es_pg else 'sqlite',
            'tables': tables,
        },
    }
    if migrations_info is not None:
        payload['migrations'] = migrations_info
    if error:
        payload['db']['error'] = error
    if malformed:
        try:
            from auth import _log_sec
            _log_sec('db_malformed_detected', None, None,
                     details='health endpoint detectó BD corrupta · restaurar via /api/admin/emergency-restore')
        except Exception:
            pass
        payload['alert'] = (
            'DB MALFORMED · restaurar via POST /api/admin/emergency-restore '
            '(con body {confirm:true})'
        )
        return jsonify(payload), 503
    if error:
        return jsonify(payload), 503
    return jsonify(payload), 200


@bp.route('/api/health/debug')
def health_debug():
    """Diagnostico publico extendido · errores REALES de cada query.

    Sebastian 4-may-2026: tablas mostraban 'err' generico en /api/health,
    sin saber por que. Este endpoint retorna el str() de la excepcion
    para diagnosticar issues post-deploy.

    Admin-only · expone esquema, conteos de tablas y movimientos recientes.
    """
    from config import ADMIN_USERS
    if session.get('compras_user', '') not in ADMIN_USERS:
        return jsonify({'error': 'Solo administradores'}), 403
    import sqlite3 as _sq, os as _os, traceback as _tb
    db_exists = _os.path.exists(DB_PATH)
    out = {'db_exists': db_exists, 'db_path': DB_PATH, 'tables': {}}
    if not db_exists:
        return jsonify(out)
    try:
        conn = db_connect(timeout=2)
        # PRAGMA info
        try:
            out['journal_mode'] = conn.execute('PRAGMA journal_mode').fetchone()[0]
        except Exception as e:
            out['journal_mode_err'] = str(e)[:200]
        try:
            out['integrity_check'] = conn.execute('PRAGMA integrity_check').fetchone()[0]
        except Exception as e:
            out['integrity_check_err'] = str(e)[:200]
        try:
            out['busy_timeout'] = conn.execute('PRAGMA busy_timeout').fetchone()[0]
        except Exception:
            pass
        # Migraciones aplicadas
        try:
            rows = conn.execute('SELECT id, descripcion FROM migraciones ORDER BY id DESC LIMIT 10').fetchall()
            out['migraciones_top10'] = [{'id': r[0], 'desc': (r[1] or '')[:80]} for r in rows]
        except Exception as e:
            out['migraciones_err'] = str(e)[:300]
        # Cada tabla con error real
        # Sebastian 8-may-2026: ampliada para detectar regresiones en producciones,
        # programacion, formulas, conteos · evidencia rapida de "datos perdidos"
        for tbl in ['maestro_mps','solicitudes_compra','ordenes_compra','movimientos',
                    'animus_inventario_baseline','animus_inventario_movimientos',
                    'sgd_documentos','documentos_sgd','users_passwords','rate_limit',
                    'security_events','empleados','notificaciones_empleados',
                    'producciones','produccion_programada','formula_headers',
                    'formula_items','conteos_fisicos','conteo_items',
                    'maestro_mee','movimientos_mee','clientes','despachos',
                    'audit_log']:
            try:
                n = conn.execute(f'SELECT COUNT(*) FROM {tbl}').fetchone()[0]
                out['tables'][tbl] = n
            except Exception as e:
                out['tables'][tbl] = f'ERR: {type(e).__name__}: {str(e)[:200]}'

        # Sebastian 8-may-2026 (alarma "se perdieron producciones"): seccion
        # FORENSE para diagnosticar en caliente sin necesitar admin auth.
        # Solo lectura · counts y top-N · sin PII.
        out['forensics'] = {}
        try:
            # Movimientos por tipo · si hubo producciones, debe haber muchas Salidas
            rows = conn.execute(
                "SELECT tipo, COUNT(*) FROM movimientos GROUP BY tipo"
            ).fetchall()
            out['forensics']['movimientos_por_tipo'] = {r[0]: r[1] for r in rows}
        except Exception as e:
            out['forensics']['movimientos_por_tipo_err'] = str(e)[:200]
        try:
            # Sebastián 9-may-2026: subtipo/categoria de cada MP en catalogo
            # → para responder "qué categorías aplican" sin pedir login.
            rows = conn.execute(
                "SELECT COALESCE(NULLIF(TRIM(tipo),''),'(vacío)'), COUNT(*) "
                "FROM maestro_mps WHERE activo=1 GROUP BY 1 ORDER BY 2 DESC"
            ).fetchall()
            out['forensics']['mp_subtipos'] = {r[0]: r[1] for r in rows}
        except Exception as e:
            out['forensics']['mp_subtipos_err'] = str(e)[:200]
        try:
            # Sebastián 9-may-2026 EMERGENCY: últimos movimientos (sin PII)
            # para diagnosticar "ingresé X y no sale en Bodega".
            rows = conn.execute("""
                SELECT id, material_id,
                       SUBSTR(COALESCE(material_nombre,''),1,40) as nombre,
                       cantidad, tipo,
                       SUBSTR(COALESCE(lote,''),1,30) as lote,
                       SUBSTR(COALESCE(proveedor,''),1,30) as prov,
                       SUBSTR(COALESCE(estado_lote,''),1,20) as estado,
                       SUBSTR(fecha,1,19) as fecha
                FROM movimientos
                ORDER BY id DESC
                LIMIT 8
            """).fetchall()
            out['forensics']['ultimos_movimientos'] = [
                {'id': r[0], 'material_id': r[1], 'nombre': r[2],
                 'cantidad': r[3], 'tipo': r[4], 'lote': r[5],
                 'proveedor': r[6], 'estado_lote': r[7], 'fecha': r[8]}
                for r in rows
            ]
        except Exception as e:
            out['forensics']['ultimos_movs_err'] = str(e)[:200]
        try:
            # Últimas MPs creadas en catálogo
            rows = conn.execute("""
                SELECT codigo_mp,
                       SUBSTR(COALESCE(nombre_comercial,''),1,40) as nc,
                       SUBSTR(COALESCE(tipo_material,'MP'),1,20) as tm,
                       activo
                FROM maestro_mps
                ORDER BY codigo_mp DESC
                LIMIT 8
            """).fetchall()
            out['forensics']['ultimas_mps'] = [
                {'codigo_mp': r[0], 'nombre': r[1],
                 'tipo_material': r[2], 'activo': r[3]}
                for r in rows
            ]
        except Exception as e:
            out['forensics']['ultimas_mps_err'] = str(e)[:200]
        try:
            # Sebastián 9-may-2026 EMERGENCY 2: replicar EXACTAMENTE la query
            # de /api/lotes para los materiales ingresados recientemente y ver
            # si aparecen / por qué no aparecen.
            # 1. Identificar materiales con movimientos en últimas 24h
            mids_recent = [r[0] for r in conn.execute("""
                SELECT DISTINCT material_id FROM movimientos
                WHERE fecha >= datetime('now','-1 day') AND material_id IS NOT NULL
                ORDER BY material_id LIMIT 20
            """).fetchall()]
            # 2. Para cada uno, replicar el query de /api/lotes (sin LIMIT)
            #    y ver qué lotes aparecen y cuáles no
            placeholders = ','.join(['?']*len(mids_recent)) if mids_recent else "''"
            rows = conn.execute(f"""
                SELECT m.material_id, COALESCE(m.lote,'') as lote,
                       SUM(CASE WHEN m.tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN m.cantidad WHEN m.tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -m.cantidad ELSE 0 END) as stock_neto,
                       UPPER(COALESCE(mp.tipo_material,'MP')) as tipo_mat_norm,
                       (mp.codigo_mp IS NOT NULL) as en_catalogo,
                       COUNT(*) as n_movs
                FROM movimientos m LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
                WHERE m.material_id IN ({placeholders})
                GROUP BY m.material_id, m.lote
                ORDER BY m.material_id, m.lote
            """, mids_recent).fetchall() if mids_recent else []
            out['forensics']['materiales_recientes_lotes'] = [
                {
                    'material_id': r[0], 'lote': r[1],
                    'stock_neto': r[2], 'tipo_mat': r[3],
                    'en_catalogo': bool(r[4]), 'n_movs': r[5],
                    'visible_bodega_mp': (r[3] == 'MP' and (r[2] or 0) > 0),
                }
                for r in rows
            ]
        except Exception as e:
            out['forensics']['recientes_lotes_err'] = str(e)[:200]
        try:
            # Producciones por estado
            rows = conn.execute(
                "SELECT COALESCE(estado,'(null)'), COUNT(*) "
                "FROM producciones GROUP BY estado"
            ).fetchall()
            out['forensics']['producciones_por_estado'] = {r[0]: r[1] for r in rows}
            # Primera y ultima
            row = conn.execute(
                "SELECT MIN(fecha), MAX(fecha) FROM producciones"
            ).fetchone()
            out['forensics']['producciones_rango_fechas'] = {
                'primera': row[0], 'ultima': row[1]
            }
        except Exception as e:
            out['forensics']['producciones_err'] = str(e)[:200]
        try:
            # Producciones programadas con inicio_real_at o descontadas
            row = conn.execute(
                "SELECT "
                "  COUNT(*) as total, "
                "  SUM(CASE WHEN inicio_real_at IS NOT NULL AND inicio_real_at != '' THEN 1 ELSE 0 END) as iniciadas, "
                "  SUM(CASE WHEN inventario_descontado_at IS NOT NULL AND inventario_descontado_at != '' THEN 1 ELSE 0 END) as descontadas "
                "FROM produccion_programada"
            ).fetchone()
            out['forensics']['produccion_programada'] = {
                'total': row[0], 'iniciadas': row[1], 'descontadas': row[2]
            }
        except Exception as e:
            out['forensics']['programada_err'] = str(e)[:200]
        try:
            # Salidas tipo FEFO/UNLIMITED en movimientos (descuentos por produccion)
            row = conn.execute(
                "SELECT COUNT(*) FROM movimientos "
                "WHERE tipo='Salida' AND (observaciones LIKE 'FEFO:%' OR observaciones LIKE 'UNLIMITED:%')"
            ).fetchone()
            out['forensics']['salidas_por_produccion'] = row[0]
        except Exception as e:
            out['forensics']['salidas_err'] = str(e)[:200]
        try:
            # Audit log: ultimos DELETE de tablas criticas
            rows = conn.execute(
                "SELECT accion, tabla, COUNT(*) "
                "FROM audit_log "
                "WHERE accion LIKE '%DELETE%' OR accion LIKE '%ELIMINAR%' "
                "      OR accion='DB_RESTORED' OR accion='RESTORE_BACKUP' "
                "GROUP BY accion, tabla "
                "ORDER BY COUNT(*) DESC LIMIT 20"
            ).fetchall()
            out['forensics']['deletes_recientes'] = [
                {'accion': r[0], 'tabla': r[1], 'count': r[2]} for r in rows
            ]
        except Exception as e:
            out['forensics']['audit_err'] = str(e)[:200]
        try:
            # Security events tipo db_restored o sospechosos
            rows = conn.execute(
                "SELECT category, COUNT(*) "
                "FROM security_events "
                "WHERE category IN ('db_restored','backup_manual_triggered','db_drop','admin_action') "
                "   OR category LIKE '%delete%' "
                "GROUP BY category"
            ).fetchall()
            out['forensics']['security_events_criticos'] = {r[0]: r[1] for r in rows}
        except Exception as e:
            out['forensics']['security_err'] = str(e)[:200]

        conn.close()
    except Exception as e:
        out['fatal'] = f'{type(e).__name__}: {str(e)[:300]}'
        out['trace'] = _tb.format_exc()[-1500:]
    return jsonify(out)

@bp.route('/')
def index():
    # Redirigir a login si no hay sesion activa; a /modulos si ya esta autenticado
    if 'compras_user' not in session:
        return redirect('/login')
    return redirect('/modulos')

@bp.route('/programacion-areas')
def programacion_areas_page():
    """Vista calendario por área · cronograma estilo Alejandro.

    Matriz 5 días Lun-Vie × 10 áreas con todas las fases proyectadas
    automáticamente desde la data del sistema (FAB/ENV/MICRO/LIB/ACOND/
    ENTR/LIMP). Solo lectura · si Alejandro quiere editar, va al módulo
    de la fase correspondiente.
    """
    if 'compras_user' not in session:
        return redirect('/login?next=/programacion-areas')
    from templates_py.programacion_areas_html import PROGRAMACION_AREAS_HTML
    return Response(PROGRAMACION_AREAS_HTML, mimetype='text/html; charset=utf-8')


@bp.route('/programacion-comparar')
def programacion_comparar_page():
    """Comparación del cronograma de Alejandro vs Calendar (real)."""
    if 'compras_user' not in session:
        return redirect('/login?next=/programacion-comparar')
    from templates_py.cronograma_comparar_html import CRONOGRAMA_COMPARAR_HTML
    return Response(CRONOGRAMA_COMPARAR_HTML, mimetype='text/html; charset=utf-8')


@bp.route('/asignar-areas')
def asignar_areas_page():
    """UI para asignar área a cada producción próxima.

    Sebastián 2-may-2026: Alejandro pide poder organizar las producciones
    por sala (FAB1, FYE2, etc). Esta pantalla lista las próximas N días,
    sugiere área en base a fórmula + tamaño de lote, permite cambiar con
    dropdown y confirmar todo en bloque.
    """
    if 'compras_user' not in session:
        return redirect('/login?next=/asignar-areas')
    from templates_py.asignar_areas_html import ASIGNAR_AREAS_HTML
    return Response(ASIGNAR_AREAS_HTML, mimetype='text/html; charset=utf-8')


@bp.route('/inventarios')
@bp.route('/planta')
def inventarios():
    if 'compras_user' not in session:
        return redirect('/login?next=/inventarios')
    usuario = session.get('compras_user', '').capitalize()
    from config import ADMIN_USERS
    es_admin = 'true' if session.get('compras_user','') in ADMIN_USERS else 'false'
    # Batch Record (EBR/MBR) oculto hasta validación Part 11 (Sebastián 18-jun): ocultar las
    # secciones inline de crear-MBR y correr-legajos. 22-jun: usa el helper user-aware de brd
    # (modo 'solo yo' por usuario). Reversible vía /api/admin/brd-visibilidad.
    _brd_vis = False
    try:
        from blueprints.brd import _brd_visible as _brdv
        _brd_vis = bool(_brdv())
    except Exception:
        _brd_vis = False
    brd_hide_css = '' if _brd_vis else '<style>#mbr-secciones,#ebr-seccion{display:none!important;}</style>'
    html = (DASHBOARD_HTML.replace('{usuario}', usuario)
            .replace('{es_admin}', es_admin)
            .replace('{brd_hide_css}', brd_hide_css))
    resp = Response(html, mimetype='text/html; charset=utf-8')
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp


@bp.route('/planta-app.js')
def planta_app_js():
    # PERF 26-jun (Increment 1) · sirve el 2º bloque JS grande del dashboard (~12k líneas, SIN
    # interpolaciones) como ARCHIVO EXTERNO cacheable. La HTML servida lo referencia con
    # <script src="/planta-app.js?v=HASH">. Es código de la app (sin datos sensibles · los datos
    # vienen de APIs con login) → público + cache immutable: la URL lleva ?v=HASH, así que al cambiar
    # el JS cambia la URL y el navegador baja la versión nueva. Si la extracción no corrió (fallback),
    # DASHBOARD_APP_JS está vacío y el dashboard sigue con el JS inline (esta ruta no se usa).
    from templates_py.dashboard_html import DASHBOARD_APP_JS
    if not DASHBOARD_APP_JS:
        return Response('/* planta-app.js no disponible (fallback inline activo) */',
                        mimetype='application/javascript; charset=utf-8'), 404
    resp = Response(DASHBOARD_APP_JS, mimetype='application/javascript; charset=utf-8')
    resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return resp


@bp.route('/planta-core.js')
def planta_core_js():
    # PERF 26-jun (Increment 2) · 1er bloque JS grande del dashboard como archivo externo cacheable.
    # Mismo criterio que /planta-app.js (público · sin datos · immutable + ?v=HASH). Las interpolaciones
    # {usuario}/{es_admin} NO están acá (van en un <script> inline previo) → el archivo es user-independiente.
    from templates_py.dashboard_html import DASHBOARD_CORE_JS
    if not DASHBOARD_CORE_JS:
        return Response('/* planta-core.js no disponible (fallback inline activo) */',
                        mimetype='application/javascript; charset=utf-8'), 404
    resp = Response(DASHBOARD_CORE_JS, mimetype='application/javascript; charset=utf-8')
    resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return resp

# (rate limiter y hooks de seguridad → auth.py — registrados via register_hooks(app))

@bp.route('/hub')
def hub():
    if 'compras_user' not in session:
        return redirect('/login?next=/modulos')
    from templates_py.hub_html import HUB_HTML
    return Response(HUB_HTML, mimetype='text/html')


# ─── Módulo Usuarios PRO · Sebastián 21-may-2026 ────────────────────────
# Reemplaza la dependencia de Render env vars (PASS_<USER>) por gestión
# desde UI. Admin (Sebastián/Alejandro) puede crear/desactivar/resetear
# password de cualquier usuario sin tocar Render.
# ────────────────────────────────────────────────────────────────────────

def _require_admin_session():
    """Helper: solo admin · case-insensitive · devuelve username o (None, error, code)."""
    u = session.get('compras_user', '')
    if not u:
        return None, jsonify({'error': 'No autenticado'}), 401
    if (u or '').strip().lower() not in {x.lower() for x in ADMIN_USERS}:
        return None, jsonify({'error': 'solo admin (Sebastián / Alejandro)'}), 403
    return u, None, None


def _ensure_users_meta_columns(conn):
    """Sebastián 21-may-2026: si la mig 149 no se aplicó en PostgreSQL
    (deploy en curso, o ALTER TABLE falló silenciosamente), crear las
    columnas requeridas al primer uso del endpoint admin. Idempotente.

    Usa `ADD COLUMN IF NOT EXISTS` que soportan tanto PG como SQLite≥3.35.
    Si igual falla, captura silenciosamente y deja que la query del
    endpoint use COALESCE o fallback.
    """
    cols_needed = [
        ('activo', 'INTEGER DEFAULT 1'),
        ('nombre_completo', 'TEXT'),
        ('cargo', 'TEXT'),
        ('email', 'TEXT'),
        ('roles_csv', "TEXT DEFAULT 'compras'"),
        ('creado_por', 'TEXT'),
        ('creado_at_utc', 'TEXT'),
        ('ultimo_login_at_utc', 'TEXT'),
        ('baja_motivo', 'TEXT'),
    ]
    for col, tipo in cols_needed:
        try:
            conn.execute(f"ALTER TABLE users_passwords ADD COLUMN IF NOT EXISTS {col} {tipo}")
        except Exception:
            # Fallback sin IF NOT EXISTS (SQLite viejo) · try/except por columna
            try:
                conn.execute(f"ALTER TABLE users_passwords ADD COLUMN {col} {tipo}")
            except Exception:
                pass  # ya existe o no se puede crear · seguir
    try:
        conn.commit()
    except Exception:
        pass


@bp.route('/api/admin/usuarios', methods=['GET'])
def admin_usuarios_list():
    """Lista TODOS los usuarios · BD + env vars · admin only."""
    u, err, code = _require_admin_session()
    if err:
        return err, code
    try:
        conn = db_connect()
        conn.execute("PRAGMA busy_timeout=2000")
        _ensure_users_meta_columns(conn)
        try:
            rows = conn.execute(
                """SELECT username, COALESCE(activo,1), COALESCE(nombre_completo,''),
                          COALESCE(cargo,''), COALESCE(email,''),
                          COALESCE(roles_csv,''), COALESCE(creado_por,''),
                          COALESCE(creado_at_utc,''), COALESCE(ultimo_login_at_utc,''),
                          COALESCE(changed_at,''), COALESCE(baja_motivo,'')
                   FROM users_passwords ORDER BY username""",
            ).fetchall()
        except Exception:
            # Mig 149 no aplicó · fallback minimal
            rows_min = conn.execute(
                "SELECT username, password_hash, COALESCE(changed_at,'') FROM users_passwords"
            ).fetchall()
            rows = [(r[0], 1, '', '', '', '', '', '', '', r[2], '') for r in rows_min]
        conn.close()
    except Exception as e:
        return jsonify({'error': f'BD inaccesible: {e}'}), 500
    db_users = {r[0]: r for r in rows}
    users_list = []
    for un, fila in db_users.items():
        users_list.append({
            'username': un,
            'activo': bool(fila[1]),
            'nombre_completo': fila[2],
            'cargo': fila[3],
            'email': fila[4],
            'roles': [r.strip() for r in (fila[5] or '').split(',') if r.strip()],
            'creado_por': fila[6],
            'creado_at_utc': fila[7],
            'ultimo_login_at_utc': fila[8],
            'password_changed_at': fila[9],
            'baja_motivo': fila[10],
            'fuente': 'bd',
        })
    # También listar users que SOLO viven en env vars (no migrados todavía)
    for env_user in (COMPRAS_USERS or {}).keys():
        if env_user not in db_users:
            users_list.append({
                'username': env_user,
                'activo': True,  # env vars no tienen flag
                'nombre_completo': '',
                'cargo': '',
                'email': '',
                'roles': [],
                'fuente': 'env_var',
            })
    users_list.sort(key=lambda x: (not x['activo'], x['username']))
    # Roles disponibles para dropdown
    roles_catalogo = [
        'admin', 'compras', 'planta', 'calidad', 'marketing',
        'contadora', 'comercial', 'gerencia', 'maquila',
        'aseguramiento', 'firmas',
    ]
    return jsonify({
        'usuarios': users_list,
        'total': len(users_list),
        'roles_catalogo': roles_catalogo,
    })


@bp.route('/api/admin/usuarios', methods=['POST'])
def admin_usuarios_crear():
    """Crear usuario nuevo · genera password temporal · admin only."""
    u, err, code = _require_admin_session()
    if err:
        return err, code
    body = request.get_json(silent=True) or {}
    username = (body.get('username') or '').strip().lower()
    nombre = (body.get('nombre_completo') or '').strip()
    cargo = (body.get('cargo') or '').strip()
    email = (body.get('email') or '').strip()
    roles = body.get('roles') or []
    password_temp = (body.get('password_temporal') or '').strip()
    # Validaciones
    import re as _re
    if not _re.match(r'^[a-z][a-z0-9_-]{2,30}$', username):
        return jsonify({'error': 'username: 3-31 chars · [a-z0-9_-] · iniciar con letra'}), 400
    if len(password_temp) < 8:
        return jsonify({'error': 'password_temporal mínimo 8 chars'}), 400
    if not nombre:
        return jsonify({'error': 'nombre_completo requerido'}), 400
    if not isinstance(roles, list):
        roles = []
    roles_csv = ','.join(r.strip().lower() for r in roles if r.strip())
    # Hash password
    from werkzeug.security import generate_password_hash
    pw_hash = generate_password_hash(password_temp, method='pbkdf2:sha256')
    from datetime import datetime as _dt
    now = _dt.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    try:
        conn = db_connect()
        conn.execute("PRAGMA busy_timeout=2000")
        _ensure_users_meta_columns(conn)
        # Verificar que no exista
        ex = conn.execute("SELECT 1 FROM users_passwords WHERE username=?", (username,)).fetchone()
        if ex:
            conn.close()
            return jsonify({'error': f'username "{username}" ya existe en BD'}), 409
        if username in (COMPRAS_USERS or {}):
            conn.close()
            return jsonify({'error': f'username "{username}" ya existe en env vars (PASS_{username.upper()})'}), 409
        conn.execute(
            """INSERT INTO users_passwords (username, password_hash, changed_at, changed_by,
                                             activo, nombre_completo, cargo, email,
                                             roles_csv, creado_por, creado_at_utc)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (username, pw_hash, now, u, 1, nombre, cargo, email, roles_csv, u, now),
        )
        # Audit
        try:
            conn.execute(
                "INSERT INTO audit_log (usuario, accion, tabla, registro_id, detalle, ip, fecha) "
                "VALUES (?,?,?,?,?,'',?)",
                (u, 'CREAR_USUARIO', 'users_passwords', username,
                 f'nombre={nombre} · cargo={cargo} · roles={roles_csv}', now),
            )
        except Exception:
            pass
        conn.commit()
        conn.close()
    except Exception as e:
        return jsonify({'error': f'Falla crear: {e}'}), 500
    return jsonify({
        'ok': True,
        'username': username,
        'password_temporal': password_temp,
        'mensaje': f'Usuario "{username}" creado · password temporal: {password_temp} · pedíle que la cambie en /cambiar-password al primer login.',
    }), 201


@bp.route('/api/admin/usuarios/<username>', methods=['PATCH'])
def admin_usuarios_editar(username):
    """Editar metadata o activo flag · admin only · NO toca password (usar reset)."""
    u, err, code = _require_admin_session()
    if err:
        return err, code
    username = (username or '').strip().lower()
    body = request.get_json(silent=True) or {}
    cambios = {}
    for campo in ('nombre_completo', 'cargo', 'email', 'baja_motivo'):
        if campo in body:
            cambios[campo] = (body.get(campo) or '').strip()
    if 'activo' in body:
        cambios['activo'] = 1 if body['activo'] else 0
    if 'roles' in body:
        rs = body['roles'] or []
        if not isinstance(rs, list):
            rs = []
        cambios['roles_csv'] = ','.join(r.strip().lower() for r in rs if r.strip())
    if not cambios:
        return jsonify({'error': 'sin cambios'}), 400
    try:
        conn = db_connect()
        conn.execute("PRAGMA busy_timeout=2000")
        _ensure_users_meta_columns(conn)
        # Verificar existe
        ex = conn.execute("SELECT 1 FROM users_passwords WHERE username=?", (username,)).fetchone()
        if not ex:
            # Auto-crear stub en BD si solo vive en env var (para poder editarlo)
            if username in (COMPRAS_USERS or {}):
                from datetime import datetime as _dt
                now = _dt.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                conn.execute(
                    "INSERT INTO users_passwords (username, password_hash, changed_at, changed_by, activo, creado_at_utc) VALUES (?,?,?,?,1,?)",
                    (username, COMPRAS_USERS[username], now, '_migrado_de_env', now),
                )
            else:
                conn.close()
                return jsonify({'error': f'usuario "{username}" no existe'}), 404
        sets = ', '.join(f'{k}=?' for k in cambios.keys())
        params = list(cambios.values()) + [username]
        conn.execute(f"UPDATE users_passwords SET {sets} WHERE username=?", params)
        # Audit
        try:
            from datetime import datetime as _dt
            now = _dt.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                "INSERT INTO audit_log (usuario, accion, tabla, registro_id, detalle, ip, fecha) VALUES (?,?,?,?,?,'',?)",
                (u, 'EDITAR_USUARIO', 'users_passwords', username, str(cambios)[:300], now),
            )
        except Exception:
            pass
        conn.commit()
        conn.close()
    except Exception as e:
        return jsonify({'error': f'Falla edit: {e}'}), 500
    return jsonify({'ok': True, 'username': username, 'cambios': cambios})


@bp.route('/api/admin/usuarios/<username>/reset-password', methods=['POST'])
def admin_usuarios_reset_password(username):
    """Resetea password con una temporal · admin only."""
    u, err, code = _require_admin_session()
    if err:
        return err, code
    username = (username or '').strip().lower()
    body = request.get_json(silent=True) or {}
    nueva = (body.get('password_temporal') or '').strip()
    if len(nueva) < 8:
        return jsonify({'error': 'password_temporal mínimo 8 chars'}), 400
    from werkzeug.security import generate_password_hash
    pw_hash = generate_password_hash(nueva, method='pbkdf2:sha256')
    from datetime import datetime as _dt
    now = _dt.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    try:
        conn = db_connect()
        conn.execute("PRAGMA busy_timeout=2000")
        _ensure_users_meta_columns(conn)
        ex = conn.execute("SELECT 1 FROM users_passwords WHERE username=?", (username,)).fetchone()
        if ex:
            conn.execute(
                "UPDATE users_passwords SET password_hash=?, changed_at=?, changed_by=? WHERE username=?",
                (pw_hash, now, u, username),
            )
        elif username in (COMPRAS_USERS or {}):
            conn.execute(
                "INSERT INTO users_passwords (username, password_hash, changed_at, changed_by, activo, creado_at_utc, creado_por) VALUES (?,?,?,?,1,?,?)",
                (username, pw_hash, now, u, now, '_reset_por_admin'),
            )
        else:
            conn.close()
            return jsonify({'error': f'usuario "{username}" no existe'}), 404
        try:
            conn.execute(
                "INSERT INTO audit_log (usuario, accion, tabla, registro_id, detalle, ip, fecha) VALUES (?,?,?,?,?,'',?)",
                (u, 'RESET_PASSWORD_USUARIO', 'users_passwords', username, 'admin reset', now),
            )
        except Exception:
            pass
        conn.commit()
        conn.close()
    except Exception as e:
        return jsonify({'error': f'Falla reset: {e}'}), 500
    return jsonify({
        'ok': True, 'username': username,
        'password_temporal': nueva,
        'mensaje': f'Password reseteada · entregar al usuario: "{nueva}" · que la cambie en /cambiar-password',
    })


_USERS_ADMIN_HTML = '''<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Usuarios · EOS</title>
<style>
*{box-sizing:border-box;font-family:'Segoe UI',Roboto,sans-serif}
body{margin:0;background:#f1f5f9;color:#0f172a;padding:20px}
.container{max-width:1200px;margin:0 auto;background:#fff;border-radius:12px;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,.05)}
h1{margin:0 0 6px;color:#0f766e}
.subtitle{color:#64748b;font-size:13px;margin-bottom:18px}
.toolbar{display:flex;gap:8px;align-items:center;margin-bottom:16px;flex-wrap:wrap}
button.primary{background:#0f766e;color:#fff;padding:9px 18px;border:none;border-radius:6px;font-weight:700;cursor:pointer}
button.primary:hover{background:#115e59}
button.secondary{background:#475569;color:#fff;padding:8px 14px;border:none;border-radius:5px;font-size:12px;cursor:pointer}
button.danger{background:#dc2626;color:#fff;padding:5px 10px;border:none;border-radius:4px;font-size:11px;cursor:pointer}
button.warn{background:#ca8a04;color:#fff;padding:5px 10px;border:none;border-radius:4px;font-size:11px;cursor:pointer}
input.search{flex:1;max-width:300px;padding:8px 12px;border:1px solid #cbd5e1;border-radius:5px}
table{width:100%;border-collapse:collapse;font-size:13px}
thead{background:#0f172a;color:#fff}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #e2e8f0}
tr:hover{background:#f8fafc}
.badge{display:inline-block;padding:2px 8px;border-radius:8px;font-size:11px;font-weight:600}
.b-active{background:#dcfce7;color:#166534}
.b-inactive{background:#fee2e2;color:#991b1b}
.b-env{background:#fef3c7;color:#78350f}
.b-bd{background:#dbeafe;color:#1e40af}
.role{background:#f1f5f9;color:#475569;padding:1px 6px;border-radius:8px;font-size:10px;margin-right:3px}
#msg{padding:10px 14px;border-radius:6px;margin-bottom:14px;display:none}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;padding:20px;z-index:99}
.modal-content{background:#fff;border-radius:10px;padding:24px;max-width:500px;width:100%;max-height:90vh;overflow-y:auto}
.modal h2{margin:0 0 14px;color:#0f766e}
.field{margin-bottom:12px}
.field label{display:block;font-weight:600;font-size:12px;color:#475569;margin-bottom:4px}
.field input,.field select{width:100%;padding:8px 10px;border:1px solid #cbd5e1;border-radius:5px;font-size:13px}
.actions{display:flex;gap:8px;justify-content:flex-end;margin-top:18px}
.role-chk{display:inline-block;margin-right:8px;font-size:12px;color:#475569;cursor:pointer}
.role-chk input{margin-right:3px}
</style></head>
<body>
<div class="container">
<h1>👥 Gestión de Usuarios</h1>
<p class="subtitle">Crear / editar / desactivar / resetear password sin tocar Render env vars. Solo admin (Sebastián / Alejandro).</p>
<div id="msg"></div>
<div class="toolbar">
  <input id="q" class="search" placeholder="🔍 Buscar usuario o nombre..." oninput="renderUsers()">
  <select id="filtro-estado" onchange="renderUsers()" style="padding:8px;border:1px solid #cbd5e1;border-radius:5px">
    <option value="todos">Todos</option>
    <option value="activos">Activos</option>
    <option value="inactivos">Inactivos</option>
  </select>
  <button class="primary" onclick="openCrearModal()">➕ Nuevo usuario</button>
  <button class="secondary" onclick="loadUsers()">🔄 Refrescar</button>
  <a href="/modulos" style="margin-left:auto;color:#64748b;font-size:12px;text-decoration:none">← Volver</a>
</div>
<div style="overflow-x:auto">
<table>
<thead><tr>
  <th>Usuario</th><th>Estado</th><th>Nombre</th><th>Cargo</th><th>Roles</th>
  <th>Último login</th><th>Fuente</th><th>Acciones</th>
</tr></thead>
<tbody id="users-tbody"><tr><td colspan="8" style="text-align:center;padding:20px;color:#94a3b8">Cargando…</td></tr></tbody>
</table>
</div>
</div>
<script>
var _allUsers = [];
var _rolesCatalogo = [];
function _esc(s){return String(s||'').replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c];});}
function _msg(txt, ok){
  var m = document.getElementById('msg');
  m.textContent = txt;
  m.style.display = 'block';
  m.style.background = ok ? '#dcfce7' : '#fee2e2';
  m.style.color = ok ? '#166534' : '#991b1b';
  setTimeout(function(){ m.style.display = 'none'; }, 5000);
}
async function loadUsers(){
  try{
    var r = await fetch('/api/admin/usuarios', {credentials:'same-origin'});
    var d = await r.json();
    if(!r.ok){ _msg('Error: ' + (d.error||r.status), false); return; }
    _allUsers = d.usuarios || [];
    _rolesCatalogo = d.roles_catalogo || [];
    renderUsers();
  }catch(e){ _msg('Red: '+e.message, false); }
}
function renderUsers(){
  var q = (document.getElementById('q').value||'').toLowerCase();
  var filtro = document.getElementById('filtro-estado').value;
  var tb = document.getElementById('users-tbody');
  var list = _allUsers.filter(function(u){
    if(filtro==='activos' && !u.activo) return false;
    if(filtro==='inactivos' && u.activo) return false;
    if(q && !((u.username||'').toLowerCase().includes(q) || (u.nombre_completo||'').toLowerCase().includes(q))) return false;
    return true;
  });
  if(!list.length){ tb.innerHTML='<tr><td colspan="8" style="text-align:center;padding:16px;color:#94a3b8">Sin usuarios que coincidan</td></tr>'; return; }
  tb.innerHTML = list.map(function(u){
    var roles = (u.roles||[]).map(function(r){return '<span class="role">'+_esc(r)+'</span>';}).join('');
    var fuenteBadge = u.fuente==='bd' ? '<span class="badge b-bd">BD</span>' : '<span class="badge b-env">env</span>';
    var estado = u.activo ? '<span class="badge b-active">✓ activo</span>' : '<span class="badge b-inactive">⛔ inactivo</span>';
    var ult = (u.ultimo_login_at_utc||'').substring(0,16) || '<span style="color:#cbd5e1">—</span>';
    var btnDes = u.activo
      ? '<button class="danger" data-act="desactivar" data-u="'+_esc(u.username)+'" title="Bloquear acceso">⛔ Desactivar</button>'
      : '<button class="warn" data-act="activar" data-u="'+_esc(u.username)+'" title="Reactivar">✓ Activar</button>';
    return '<tr>'+
      '<td><b style="font-family:monospace">'+_esc(u.username)+'</b></td>'+
      '<td>'+estado+'</td>'+
      '<td>'+_esc(u.nombre_completo||'')+'</td>'+
      '<td>'+_esc(u.cargo||'')+'</td>'+
      '<td>'+(roles||'<span style="color:#cbd5e1">—</span>')+'</td>'+
      '<td style="font-size:11px;color:#64748b">'+ult+'</td>'+
      '<td>'+fuenteBadge+'</td>'+
      '<td style="white-space:nowrap">'+
        '<button class="warn" data-act="editar" data-u="'+_esc(u.username)+'" title="Editar nombre/cargo/roles">✏ Editar</button> '+
        '<button class="warn" data-act="reset" data-u="'+_esc(u.username)+'" title="Resetear password">🔑 Reset</button> '+
        btnDes+
      '</td></tr>';
  }).join('');
}
document.addEventListener('click', function(ev){
  var b = ev.target.closest('[data-act]');
  if(!b) return;
  var act = b.getAttribute('data-act');
  var un = b.getAttribute('data-u');
  if(act==='desactivar') return doSetActivo(un, false);
  if(act==='activar') return doSetActivo(un, true);
  if(act==='reset') return doResetPwd(un);
  if(act==='editar') return openEditarModal(un);
});
async function doSetActivo(un, activo){
  var motivo = '';
  if(!activo){
    motivo = prompt('Motivo de baja (opcional · queda en audit):') || '';
    if(motivo===null) return;
  }
  if(!confirm((activo?'Reactivar':'Desactivar')+' usuario "'+un+'"?')) return;
  try{
    var r = await fetch('/api/admin/usuarios/'+encodeURIComponent(un), {
      method:'PATCH', credentials:'same-origin',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({activo: activo, baja_motivo: motivo}),
    });
    var d = await r.json();
    if(!r.ok){ _msg('Error: '+(d.error||r.status), false); return; }
    _msg('✓ '+un+(activo?' reactivado':' desactivado · ya no podrá hacer login'), true);
    loadUsers();
  }catch(e){ _msg('Red: '+e.message, false); }
}
async function doResetPwd(un){
  var nueva = prompt('Password temporal para "'+un+'" (≥8 chars · entregársela en persona):');
  if(!nueva) return;
  nueva = nueva.trim();
  if(nueva.length < 8){ _msg('Password mínimo 8 chars', false); return; }
  try{
    var r = await fetch('/api/admin/usuarios/'+encodeURIComponent(un)+'/reset-password', {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({password_temporal: nueva}),
    });
    var d = await r.json();
    if(!r.ok){ _msg('Error: '+(d.error||r.status), false); return; }
    alert('✓ Password reseteada · entregale al usuario:\\n\\n'+nueva+'\\n\\nQue la cambie en /cambiar-password al loguearse.');
    loadUsers();
  }catch(e){ _msg('Red: '+e.message, false); }
}
function openCrearModal(){
  var m = document.createElement('div');
  m.className = 'modal';
  m.id = 'modal-crear';
  var rolesHtml = _rolesCatalogo.map(function(r){
    return '<label class="role-chk"><input type="checkbox" value="'+_esc(r)+'" name="roles-crear"> '+_esc(r)+'</label>';
  }).join('');
  m.innerHTML = '<div class="modal-content">'+
    '<h2>➕ Nuevo usuario</h2>'+
    '<div class="field"><label>Username (lowercase, sin espacios) *</label><input id="c-username" placeholder="ej: laura"></div>'+
    '<div class="field"><label>Password temporal (≥8 chars) *</label><input id="c-password" type="text" value="EOS-Temp-'+(new Date().getFullYear())+'-X" placeholder="EOS-Temp-2026-X"></div>'+
    '<div class="field"><label>Nombre completo *</label><input id="c-nombre" placeholder="Laura Martínez"></div>'+
    '<div class="field"><label>Cargo</label><input id="c-cargo" placeholder="Jefe de Producción"></div>'+
    '<div class="field"><label>Email</label><input id="c-email" type="email" placeholder="laura@espagiria.co"></div>'+
    '<div class="field"><label>Roles</label><div>'+rolesHtml+'</div></div>'+
    '<div class="actions">'+
      '<button class="secondary" onclick="document.getElementById(\\'modal-crear\\').remove()">Cancelar</button>'+
      '<button class="primary" onclick="doCrear()">Crear</button>'+
    '</div>'+
    '</div>';
  document.body.appendChild(m);
}
async function doCrear(){
  var username = (document.getElementById('c-username').value||'').trim().toLowerCase();
  var password = (document.getElementById('c-password').value||'').trim();
  var nombre = (document.getElementById('c-nombre').value||'').trim();
  var cargo = (document.getElementById('c-cargo').value||'').trim();
  var email = (document.getElementById('c-email').value||'').trim();
  var roles = [];
  document.querySelectorAll('input[name=roles-crear]:checked').forEach(function(el){ roles.push(el.value); });
  if(!username || !password || !nombre){ alert('username, password y nombre obligatorios'); return; }
  try{
    var r = await fetch('/api/admin/usuarios', {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({username:username, password_temporal:password, nombre_completo:nombre, cargo:cargo, email:email, roles:roles}),
    });
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    alert('✓ Usuario creado:\\n\\nUsuario: '+d.username+'\\nPassword temporal: '+d.password_temporal+'\\n\\nEntregársela al usuario · debe cambiarla en /cambiar-password.');
    document.getElementById('modal-crear').remove();
    loadUsers();
  }catch(e){ alert('Red: '+e.message); }
}
function openEditarModal(un){
  var u = _allUsers.find(function(x){return x.username===un;});
  if(!u){ alert('No encontrado'); return; }
  var m = document.createElement('div');
  m.className = 'modal'; m.id = 'modal-edit';
  var userRoles = u.roles || [];
  var rolesHtml = _rolesCatalogo.map(function(r){
    var chk = userRoles.indexOf(r) >= 0 ? ' checked' : '';
    return '<label class="role-chk"><input type="checkbox" value="'+_esc(r)+'" name="roles-edit"'+chk+'> '+_esc(r)+'</label>';
  }).join('');
  m.innerHTML = '<div class="modal-content">'+
    '<h2>✏ Editar usuario · '+_esc(un)+'</h2>'+
    '<div class="field"><label>Nombre completo</label><input id="e-nombre" value="'+_esc(u.nombre_completo||'')+'"></div>'+
    '<div class="field"><label>Cargo</label><input id="e-cargo" value="'+_esc(u.cargo||'')+'"></div>'+
    '<div class="field"><label>Email</label><input id="e-email" type="email" value="'+_esc(u.email||'')+'"></div>'+
    '<div class="field"><label>Roles</label><div>'+rolesHtml+'</div></div>'+
    '<div class="actions">'+
      '<button class="secondary" onclick="document.getElementById(\\'modal-edit\\').remove()">Cancelar</button>'+
      '<button class="primary" onclick="doEditar(\\''+_esc(un)+'\\')">Guardar</button>'+
    '</div></div>';
  document.body.appendChild(m);
}
async function doEditar(un){
  var nombre = (document.getElementById('e-nombre').value||'').trim();
  var cargo = (document.getElementById('e-cargo').value||'').trim();
  var email = (document.getElementById('e-email').value||'').trim();
  var roles = [];
  document.querySelectorAll('input[name=roles-edit]:checked').forEach(function(el){ roles.push(el.value); });
  try{
    var r = await fetch('/api/admin/usuarios/'+encodeURIComponent(un), {
      method:'PATCH', credentials:'same-origin',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({nombre_completo:nombre, cargo:cargo, email:email, roles:roles}),
    });
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    _msg('✓ Usuario "'+un+'" actualizado', true);
    document.getElementById('modal-edit').remove();
    loadUsers();
  }catch(e){ alert('Red: '+e.message); }
}
loadUsers();
</script>
</body></html>'''


@bp.route('/admin/usuarios')
def admin_usuarios_page():
    """Página HTML admin · /admin/usuarios · Sebastián 21-may-2026."""
    if 'compras_user' not in session:
        return redirect('/login?next=/admin/usuarios')
    u = session.get('compras_user', '')
    if (u or '').strip().lower() not in {x.lower() for x in ADMIN_USERS}:
        return Response(
            '<h1>403 · Solo admin</h1><p>Solo Sebastián / Alejandro pueden gestionar usuarios.</p><p><a href="/modulos">← Volver</a></p>',
            mimetype='text/html', status=403,
        )
    return Response(_USERS_ADMIN_HTML, mimetype='text/html')


_INFLUENCERS_ADMIN_HTML = '''<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Influencers · EOS</title>
<style>
*{box-sizing:border-box;font-family:'Segoe UI',Roboto,sans-serif}
body{margin:0;background:#f1f5f9;color:#0f172a;padding:20px}
.container{max-width:1200px;margin:0 auto;background:#fff;border-radius:12px;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,.05)}
h1{margin:0 0 6px;color:#0f766e}
.subtitle{color:#64748b;font-size:13px;margin-bottom:18px}
.tabs{display:flex;gap:8px;margin-bottom:16px;border-bottom:2px solid #e2e8f0}
.tb{padding:9px 18px;background:transparent;border:none;cursor:pointer;font-weight:700;font-size:13px;color:#64748b}
.tb.on{color:#0f766e;border-bottom:3px solid #0f766e}
table{width:100%;border-collapse:collapse;font-size:13px}
thead{background:#0f172a;color:#fff}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #e2e8f0}
tr:hover{background:#f8fafc}
.badge{display:inline-block;padding:2px 8px;border-radius:8px;font-size:11px;font-weight:700}
.b-pend{background:#fef3c7;color:#78350f}
.b-pag{background:#dcfce7;color:#166534}
.b-rech{background:#fee2e2;color:#991b1b}
.toolbar{display:flex;gap:8px;align-items:center;margin-bottom:14px}
button.primary{background:#0f766e;color:#fff;padding:9px 16px;border:none;border-radius:6px;font-weight:700;cursor:pointer}
button.secondary{background:#475569;color:#fff;padding:7px 14px;border:none;border-radius:5px;font-size:12px;cursor:pointer}
button.success{background:#16a34a;color:#fff;padding:5px 12px;border:none;border-radius:5px;font-size:11px;cursor:pointer}
input.search{flex:1;max-width:300px;padding:8px 12px;border:1px solid #cbd5e1;border-radius:5px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:14px}
.stat{background:#f1f5f9;padding:10px 14px;border-radius:6px;font-size:12px}
.stat b{font-size:1.6em;color:#0f766e;display:block}
</style></head>
<body>
<div class="container">
<h1>💸 Influencers · pagos</h1>
<p class="subtitle">Vista privada de Sebastián · Catalina NO tiene acceso a este flujo · pagos Marketing</p>
<div class="stats" id="stats"></div>
<div class="tabs">
  <button class="tb on" data-tb="pendientes">⏳ Pendientes</button>
  <button class="tb" data-tb="pagados">✓ Histórico pagados</button>
  <button class="tb" data-tb="rechazados">⛔ Rechazados</button>
</div>
<div class="toolbar">
  <input id="q" class="search" placeholder="🔍 Buscar influencer o número SOL..." oninput="render()">
  <button class="secondary" onclick="load()">🔄 Refrescar</button>
  <a href="/modulos" style="margin-left:auto;color:#64748b;font-size:12px;text-decoration:none">← Volver</a>
</div>
<div style="overflow-x:auto">
<table>
<thead><tr>
  <th>#SOL</th><th>Influencer</th><th>Concepto</th><th>Monto</th><th>Fecha sol</th>
  <th>Fecha pago</th><th>Estado</th><th>Acción</th>
</tr></thead>
<tbody id="tbody"><tr><td colspan="8" style="text-align:center;padding:18px;color:#94a3b8">Cargando…</td></tr></tbody>
</table>
</div>
</div>
<script>
var _all = [];
var _curTab = 'pendientes';
function _esc(s){return String(s||'').replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c];});}
function _fmt(n){ try{return Number(n||0).toLocaleString('es-CO');}catch(e){return n;} }
document.querySelectorAll('.tb').forEach(function(b){
  b.addEventListener('click',function(){
    _curTab=b.getAttribute('data-tb');
    document.querySelectorAll('.tb').forEach(function(x){x.classList.remove('on');});
    b.classList.add('on');
    render();
  });
});
async function load(){
  try{
    var r=await fetch('/api/solicitudes-compra?fuente=influencers&limit=500',{credentials:'same-origin'});
    var d=await r.json();
    _all=d.solicitudes||d||[];
    renderStats(); render();
  }catch(e){
    document.getElementById('tbody').innerHTML='<tr><td colspan="8" style="color:#dc2626;text-align:center;padding:18px">Error: '+_esc(e.message)+'</td></tr>';
  }
}
function renderStats(){
  var pend=_all.filter(function(s){return s.estado==='Pendiente';}).length;
  var apr=_all.filter(function(s){return s.estado==='Aprobada';}).length;
  var pag=_all.filter(function(s){return s.estado==='Pagada' || s.estado==='Reconciliada';}).length;
  var rech=_all.filter(function(s){return s.estado==='Rechazada' || s.estado==='Cancelada';}).length;
  var totalMonto=_all.filter(function(s){return s.estado==='Pendiente';}).reduce(function(a,s){return a+Number(s.valor||0);},0);
  document.getElementById('stats').innerHTML=
    '<div class="stat">Pendientes<b>'+pend+'</b></div>'+
    '<div class="stat">Por pagar (monto)<b>$'+_fmt(totalMonto)+'</b></div>'+
    '<div class="stat">Aprobados<b>'+apr+'</b></div>'+
    '<div class="stat">Pagados (histórico)<b>'+pag+'</b></div>'+
    '<div class="stat">Rechazados<b>'+rech+'</b></div>';
}
function render(){
  var q=(document.getElementById('q').value||'').toLowerCase();
  var filt;
  if(_curTab==='pendientes') filt=_all.filter(function(s){return s.estado==='Pendiente' || s.estado==='Aprobada';});
  else if(_curTab==='pagados') filt=_all.filter(function(s){return s.estado==='Pagada' || s.estado==='Reconciliada';});
  else filt=_all.filter(function(s){return s.estado==='Rechazada' || s.estado==='Cancelada';});
  if(q) filt=filt.filter(function(s){
    return ((s.solicitante||'').toLowerCase().includes(q) ||
            (s.numero||'').toLowerCase().includes(q) ||
            (s.observaciones||'').toLowerCase().includes(q));
  });
  var tb=document.getElementById('tbody');
  if(!filt.length){
    tb.innerHTML='<tr><td colspan="8" style="text-align:center;padding:18px;color:#94a3b8">Sin registros</td></tr>';
    return;
  }
  tb.innerHTML=filt.map(function(s){
    var clBadge=s.estado==='Pendiente'?'b-pend':(s.estado==='Pagada' || s.estado==='Reconciliada'?'b-pag':'b-rech');
    var accion='';
    if(s.estado==='Pendiente' || s.estado==='Aprobada'){
      accion='<button class="success" data-num="'+_esc(s.numero)+'" data-act="pagar">💸 Marcar pagado</button>';
    }
    return '<tr>'+
      '<td style="font-family:monospace;font-weight:700">'+_esc(s.numero)+'</td>'+
      '<td>'+_esc(s.solicitante||'—')+'</td>'+
      '<td style="font-size:11px;color:#475569">'+_esc((s.observaciones||'').substring(0,60))+'</td>'+
      '<td style="text-align:right;font-weight:700">$'+_fmt(s.valor)+'</td>'+
      '<td style="font-size:11px">'+_esc((s.fecha||'').substring(0,10))+'</td>'+
      '<td style="font-size:11px">'+_esc((s.fecha_pago||'').substring(0,10) || '—')+'</td>'+
      '<td><span class="badge '+clBadge+'">'+_esc(s.estado)+'</span></td>'+
      '<td>'+accion+'</td>'+
    '</tr>';
  }).join('');
}
document.addEventListener('click',async function(ev){
  var b=ev.target.closest('[data-act="pagar"]');
  if(!b) return;
  var num=b.getAttribute('data-num');
  var ref=prompt('Referencia / comprobante del pago a '+num+':');
  if(!ref) return;
  try{
    var token=document.cookie.match(/csrf_token=([^;]*)/);
    token=token?decodeURIComponent(token[1]):'';
    var r=await fetch('/api/solicitudes-compra/'+encodeURIComponent(num)+'/estado',{
      method:'PATCH',
      headers:{'Content-Type':'application/json','X-CSRF-Token':token},
      credentials:'same-origin',
      body:JSON.stringify({estado:'Pagada',observaciones_extra:'Pago directo Sebastián · ref: '+ref}),
    });
    var d=await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    alert('✓ Pago registrado · '+num);
    load();
  }catch(e){ alert('Error red: '+e.message); }
});
load();
</script>
</body></html>'''


@bp.route('/admin/influencers')
def admin_influencers_page():
    """Sebastián 21-may-2026 · página privada para gestionar influencers.

    Catalina NO tiene acceso (no aparece en su /compras). Vive aquí porque
    es flujo Marketing → directamente Sebastián.
    """
    if 'compras_user' not in session:
        return redirect('/login?next=/admin/influencers')
    u = session.get('compras_user', '')
    if (u or '').strip().lower() not in {x.lower() for x in ADMIN_USERS}:
        return Response(
            '<h1>403 · Solo admin</h1><p>Solo Sebastián paga influencers.</p><p><a href="/modulos">← Volver</a></p>',
            mimetype='text/html', status=403,
        )
    return Response(_INFLUENCERS_ADMIN_HTML, mimetype='text/html')


@bp.route('/cambiar-password')
def cambiar_password_page():
    """Página standalone para que cualquier user logueado cambie su password.

    Sebastián 7-may-2026: el modal del /hub solo lo ven users que pasan por
    el hub. Mayerlin/Catalina entran directo a /planta o /compras y no lo
    veían. Esta página standalone es accesible desde cualquier sesión activa.
    """
    if 'compras_user' not in session:
        return redirect('/login?next=/cambiar-password')
    username = session.get('compras_user', '')
    return Response(
        _PWD_PAGE_HTML.replace('{{USERNAME}}', username),
        mimetype='text/html',
    )


_PWD_PAGE_HTML = """<!DOCTYPE html>
<html lang="es"><head>
<meta charset="utf-8">
<title>Cambiar contraseña · EOS</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
       background: linear-gradient(135deg, #0f172a, #1e293b);
       min-height: 100vh; display: flex; align-items: center;
       justify-content: center; padding: 20px; color: #e2e8f0; }
.card { background: #1e293b; border: 1px solid #334155; border-radius: 14px;
        padding: 32px; width: 100%; max-width: 440px;
        box-shadow: 0 20px 50px rgba(0,0,0,.4); }
h1 { font-size: 22px; color: #f1f5f9; margin-bottom: 6px; }
.user { font-size: 13px; color: #94a3b8; margin-bottom: 24px; }
.user b { color: #a78bfa; }
.req { font-size: 11px; color: #94a3b8; background: #0f172a;
       border: 1px solid #1e293b; padding: 10px 12px; border-radius: 8px;
       margin-bottom: 18px; line-height: 1.6; }
label { font-size: 11px; color: #94a3b8; font-weight: 600;
        text-transform: uppercase; letter-spacing: .05em;
        display: block; margin-bottom: 4px; }
input[type=password] { background: #0f172a; border: 1px solid #334155;
       color: #e2e8f0; padding: 10px 14px; border-radius: 8px;
       font-size: 14px; width: 100%; font-family: inherit; }
input:focus { outline: none; border-color: #7c3aed; }
.row { margin-bottom: 14px; }
.actions { display: flex; gap: 10px; margin-top: 20px; }
.btn { flex: 1; padding: 11px 18px; border-radius: 8px; cursor: pointer;
       font-size: 14px; font-weight: 700; border: none; }
.btn.primary { background: linear-gradient(135deg, #7c3aed, #4c1d95);
               color: #fff; }
.btn.primary:hover { background: linear-gradient(135deg, #6d28d9, #3b1480); }
.btn.primary:disabled { opacity: .5; cursor: not-allowed; }
.btn.secondary { background: transparent; border: 1px solid #334155;
                 color: #94a3b8; }
.msg { font-size: 13px; min-height: 20px; padding: 8px 0;
       text-align: center; }
.back { text-align: center; margin-top: 20px; }
.back a { color: #94a3b8; font-size: 12px; text-decoration: none; }
.back a:hover { color: #e2e8f0; }
</style>
</head><body>
<div class="card">
  <h1>🔐 Cambiar contraseña</h1>
  <div class="user">Usuario: <b>{{USERNAME}}</b></div>
  <div class="req">
    Tu nueva contraseña debe tener:
    <ul style="margin-left:18px;margin-top:4px;">
      <li>Mínimo 8 caracteres</li>
      <li>Al menos una letra y un número</li>
      <li>Diferente a tu nombre de usuario</li>
    </ul>
  </div>
  <form id="form" onsubmit="return submitForm(event)">
    <div class="row">
      <label>Contraseña actual</label>
      <input type="password" id="actual" required autocomplete="current-password" autofocus>
    </div>
    <div class="row">
      <label>Nueva contraseña</label>
      <input type="password" id="nueva" required minlength="8" autocomplete="new-password">
    </div>
    <div class="row">
      <label>Confirmar nueva contraseña</label>
      <input type="password" id="confirmar" required minlength="8" autocomplete="new-password">
    </div>
    <div class="msg" id="msg"></div>
    <div class="actions">
      <button type="button" class="btn secondary" onclick="window.history.back()">Cancelar</button>
      <button type="submit" class="btn primary" id="btn">Guardar</button>
    </div>
  </form>
  <div class="back"><a href="/modulos">← Volver al panel</a></div>
</div>

<script>
async function submitForm(ev) {
  ev.preventDefault();
  const actual = document.getElementById('actual').value;
  const nueva = document.getElementById('nueva').value;
  const confirmar = document.getElementById('confirmar').value;
  const msg = document.getElementById('msg');
  const btn = document.getElementById('btn');

  msg.style.color = '#fbbf24';
  msg.textContent = 'Validando...';

  if (nueva !== confirmar) {
    msg.style.color = '#f87171';
    msg.textContent = 'La confirmación no coincide.';
    return false;
  }
  if (nueva.length < 8) {
    msg.style.color = '#f87171';
    msg.textContent = 'Mínimo 8 caracteres.';
    return false;
  }
  if (!/[a-zA-Z]/.test(nueva) || !/[0-9]/.test(nueva)) {
    msg.style.color = '#f87171';
    msg.textContent = 'Debe incluir al menos una letra y un número.';
    return false;
  }

  btn.disabled = true;
  try {
    const r = await fetch('/api/cambiar-password', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        password_actual: actual,
        password_nueva: nueva,
        password_confirmar: confirmar
      })
    });
    const data = await r.json();
    if (r.ok && (data.ok || data.message)) {
      msg.style.color = '#34d399';
      msg.textContent = '✅ Contraseña actualizada · redirigiendo a login...';
      setTimeout(() => { window.location.href = '/logout'; }, 1800);
    } else {
      msg.style.color = '#f87171';
      msg.textContent = data.error || 'Error desconocido';
      btn.disabled = false;
    }
  } catch (e) {
    msg.style.color = '#f87171';
    msg.textContent = 'Error de red: ' + e.message;
    btn.disabled = false;
  }
  return false;
}
</script>
</body></html>
"""

@bp.route('/modulos')
def modulos():
    if 'compras_user' not in session:
        return redirect('/login?next=/modulos')
    from templates_py.modulos_html import MODULOS_HTML
    from blueprints.marketing import MARKETING_USERS
    from config import ADMIN_USERS as _ADMS
    usuario = session.get('compras_user', '')
    es_admin = 'true' if usuario in _ADMS else 'false'
    html = (MODULOS_HTML
            .replace('{usuario}', usuario)
            .replace('{usuario_es_admin}', es_admin))
    # Ocultar tarjeta ANIMUS Lab para usuarios sin acceso a Marketing
    if usuario not in MARKETING_USERS:
        import re
        html = re.sub(
            r'<a class="mod-card" href="/marketing"[^>]*>.*?</a>',
            '', html, flags=re.DOTALL
        )
    return Response(html, mimetype='text/html')

@bp.route('/login', methods=['GET','POST'])
def login():
    error = ''
    next_url = request.args.get('next', '/modulos')
    # SEC-FIX · 21-may-2026 · XSS reflejado en next_url (CVSS 7.5)
    # Antes: solo bloqueaba // · aceptaba /x"><script>alert()</script>
    # Ahora: whitelist regex estricta (solo paths internos seguros)
    import re as _re_secfix
    if not _re_secfix.match(r'^/[a-zA-Z0-9/_\-?=&%.]{0,200}$', next_url) or next_url.startswith('//'):
        next_url = '/modulos'
    if request.method == 'POST':
        ip = _client_ip()
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '').strip()
        # Lock por IP O por (IP, username) — bloquea brute-force que rota
        # usernames y brute-force dirigido a un solo usuario.
        if _is_locked(ip, username):
            error = '<div class="err">Demasiados intentos. Espera 15 min.</div>'
            return Response(LOGIN_HTML.replace('{error}', error).replace('{next_url}', next_url), mimetype='text/html')
        # Fallback lazy: hash de DB tiene prioridad (si el user lo cambió);
        # si no hay entry en DB, usar env var (PASS_<USER>). Esto permite
        # self-service de password sin migrar todos los users de una vez.
        expected = _resolve_password_hash(username)
        # SEC-FIX · 21-may-2026 · login plaintext fallback (CRÍTICA · CVSS 7+)
        # Antes: si env var quedaba plaintext, hmac.compare_digest aceptaba ·
        # config.py warning CRITICAL pero NO bloqueaba arranque · brecha total.
        # Ahora: SOLO hashes pbkdf2/scrypt aceptados · plaintext rechazado.
        if expected and (expected.startswith('pbkdf2:') or expected.startswith('scrypt:')):
            match = check_password_hash(expected, password)
        else:
            # Plaintext legacy bloqueado · forzar reset via /admin/usuarios
            __import__('logging').getLogger('inventario.security').error(
                'login.plaintext_blocked user=%s · env var no hasheada · reset password',
                username,
            )
            match = False
        if match:
            # ── MFA gate (paso 2) ──────────────────────────────────────────────
            # Si el usuario tiene MFA enabled, NO completamos login todavía.
            # Guardamos username en 'mfa_pending_user' y redirigimos a /login/mfa
            # donde se pide el token TOTP. Solo después de verificar TOTP se
            # establece session['compras_user'] = username (en blueprints/mfa.py).
            #
            # Sebastián 14-may-2026: "que no me lo pida cada momentico".
            # Cookie 'mfa_trusted' permite saltar el paso TOTP si fue
            # verificado en los últimos 60 días desde este navegador.
            try:
                from blueprints.mfa import _is_mfa_enabled
                # Sebastián 19-may-2026: usuarios en MFA_EXEMPT_USERS (env var)
                # saltan TODO el flujo MFA · ni redirect ni bloqueo posterior.
                # Ver auth.py:55 para configuración.
                try:
                    from auth import MFA_EXEMPT_USERS as _MFA_EXEMPT
                except Exception:
                    _MFA_EXEMPT = set()
                if (username or '').lower() in _MFA_EXEMPT:
                    _is_mfa_enabled_eff = lambda _u: False  # noqa: E731
                else:
                    _is_mfa_enabled_eff = _is_mfa_enabled
                if _is_mfa_enabled_eff(username):
                    # Validar cookie mfa_trusted (firmada con SECRET_KEY)
                    # SEC-FIX · 22-may-2026 · session_version invalida cookies
                    # cuando user cambia password. Cookie incluye sv (session
                    # version actual al momento de firmar) · compara con DB.
                    trusted_cookie = request.cookies.get('mfa_trusted', '')
                    skip_mfa = False
                    if trusted_cookie:
                        import hashlib, hmac as _hmac
                        secret = current_app.secret_key or ''
                        parts = trusted_cookie.split('|')
                        # Soportar formato legacy (3 partes) + nuevo (4 con sv)
                        if len(parts) in (3, 4):
                            try:
                                if len(parts) == 4:
                                    user_c, ts_c, sv_c, sig_c = parts
                                    msg = f"{user_c}|{ts_c}|{sv_c}"
                                else:
                                    user_c, ts_c, sig_c = parts
                                    sv_c = '0'
                                    msg = f"{user_c}|{ts_c}"
                                ts_int = int(ts_c)
                                expected = _hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()[:32]
                                if (_hmac.compare_digest(expected, sig_c)
                                        and user_c == username
                                        and (time.time() - ts_int) < 60 * 24 * 3600):
                                    # SEC-FIX 22-may · validar session_version actual vs cookie
                                    sv_db = '0'
                                    try:
                                        _c2 = db_connect()
                                        _row = _c2.execute(
                                            "SELECT COALESCE(session_version, 1) FROM users_passwords WHERE username=?",
                                            (username,),
                                        ).fetchone()
                                        _c2.close()
                                        sv_db = str(_row[0]) if _row else '1'
                                    except Exception:
                                        sv_db = '1'
                                    if sv_c == sv_db:
                                        skip_mfa = True
                                    else:
                                        _log_sec("mfa_trusted_revoked_sv_mismatch",
                                                 username, ip,
                                                 f"cookie_sv={sv_c} db_sv={sv_db}")
                            except (ValueError, TypeError):
                                pass
                    if skip_mfa:
                        # Bypass MFA · cookie trusted válida
                        _clear_attempts(ip, username)
                        _log_sec("login_success_mfa_trusted", username, ip)
                        session.clear()
                        session.permanent = True
                        session['compras_user'] = username
                        session['login_time'] = time.time()
                        _ensure_csrf_token()
                        nxt = request.args.get('next', '')
                        if nxt and nxt.startswith('/') and not nxt.startswith('//'):
                            resp = redirect(nxt)
                        else:
                            # Sebastián 19-may-2026 · Kanban pieza 5: redirect
                            # por rol también en path MFA-trusted. Operario
                            # planta no admin → /operario (Mi Día). Antes
                            # iba a /modulos como cualquier otro · "que todos
                            # sepan qué hacer cuando llegan" requiere aterrizar
                            # directo en su pantalla.
                            from config import (ADMIN_USERS as _AU_T,
                                                 PLANTA_USERS as _PU_T)
                            if username in _PU_T and username not in _AU_T:
                                resp = redirect('/operario')
                            else:
                                resp = redirect('/modulos')
                        # Sebastián 15-may-2026: "la verificación dos pasos
                        # me cansa · estaría bien cada mes". Cookie ROLLING:
                        # se renueva con timestamp nuevo en cada login válido,
                        # así 60 días cuentan desde el ÚLTIMO acceso, no desde
                        # el TOTP original. Un usuario que entra seguido casi
                        # nunca vuelve a ver el código.
                        try:
                            import hashlib as _hl, hmac as _hm
                            _secret = current_app.secret_key or ''
                            _tt = f"{username}|{int(time.time())}"
                            _sig = _hm.new(_secret.encode(), _tt.encode(),
                                           _hl.sha256).hexdigest()[:32]
                            resp.set_cookie(
                                'mfa_trusted', f"{_tt}|{_sig}",
                                max_age=60 * 24 * 3600,
                                httponly=True, secure=True, samesite='Lax',
                            )
                        except Exception:
                            pass  # renovar cookie es best-effort
                        return resp
                    session.clear()
                    session['mfa_pending_user'] = username
                    session['mfa_pending_next'] = next_url
                    _log_sec("login_password_ok_mfa_pending", username, ip)
                    return redirect('/login/mfa')
            except ImportError:
                pass  # blueprint mfa no cargado (test environment) — seguir sin MFA
            _clear_attempts(ip, username)
            _log_sec("login_success", username, ip)
            session.clear()
            session.permanent = True
            session['compras_user'] = username
            session['login_time']   = time.time()
            # Generar CSRF token nuevo en cada login (rotación = mejor seguridad)
            _ensure_csrf_token()
            nxt = request.args.get('next', '')
            # Todos los usuarios van al hub; si había un ?next= válido se respeta
            if not nxt or not nxt.startswith('/') or nxt.startswith('//'):
                nxt = '/modulos'
            # Safety: non-admins must not land on admin-only pages
            from config import ADMIN_USERS as _AU, PLANTA_USERS as _PU
            ADMIN_ONLY = {'/gerencia'}
            if any(nxt == p or nxt.startswith(p + '/') for p in ADMIN_ONLY) and username not in _AU:
                nxt = '/modulos'
            # Operarios de planta (no admin · no explicit ?next=) → directo a Mi Día.
            # Saltean /modulos porque su día-a-día es solo producciones asignadas.
            # Admin/gerencia/contadora siguen yendo a /modulos.
            if (nxt == '/modulos' and username in _PU and username not in _AU
                and not request.args.get('next')):
                nxt = '/operario'
            return redirect(nxt)
        _record_failure(ip, username)
        _log_sec("login_failure", username, ip)
        error = '<div class="err">Usuario o contraseña incorrectos.</div>'
    return Response(LOGIN_HTML.replace('{error}', error).replace('{next_url}', next_url), mimetype='text/html')

@bp.route('/logout')
def logout():
    # session.clear() en lugar de pop('compras_user') · audit zero-error
    # 2-may-2026: pop solo borraba compras_user, dejaba csrf_token,
    # mfa_pending_user, login_time, must_reenroll_mfa vivos. Una sesión
    # robada post-logout aún tenía artefactos válidos.
    session.clear()
    resp = redirect('/')
    # Borrar también la cookie mfa_trusted · si no, sigue válida 60 días y
    # un login posterior en ese navegador salta el MFA sin re-verificar
    # (incluso tras un logout explícito).
    resp.delete_cookie('mfa_trusted')
    return resp

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
    _u_low = (username or '').lower()
    _es_admin_b = _u_low in {x.lower() for x in ADMIN_USERS}
    es_admin = 'true' if _es_admin_b else 'false'
    # es_autorizador: quién puede AUTORIZAR OCs en la UI = admin O autorizador explícito
    # (Catalina · OC_AUTORIZA_USERS). Antes los botones de autorizar se gateaban con !ES_C,
    # lo que OCULTABA el botón a Catalina (es contadora) aunque el backend SÍ la deja → era
    # cuello de botella en admins. Ahora la UI coincide con _require_authorize_oc.
    try:
        from config import OC_AUTORIZA_USERS as _OCA
    except Exception:
        _OCA = set()
    es_autorizador = 'true' if (_es_admin_b or _u_low in {x.lower() for x in _OCA}) else 'false'
    html = (COMPRAS_HTML
            .replace('{usuario}', usuario)
            .replace('{es_contadora}', es_contadora)
            .replace('{es_admin}', es_admin)
            .replace('{es_autorizador}', es_autorizador))
    resp = Response(html, mimetype='text/html; charset=utf-8')
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

@bp.route('/animus')
def animus():
    if 'compras_user' not in session:
        return redirect('/login?next=/animus')
    from templates_py.animus_html import ANIMUS_HTML
    usuario = session.get('compras_user', '').capitalize()
    return Response(ANIMUS_HTML.replace('{usuario}', usuario), mimetype='text/html; charset=utf-8')

@bp.route('/marketing')
def marketing():
    if 'compras_user' not in session:
        return redirect('/login?next=/marketing')
    from templates_py.marketing_html import MARKETING_HTML
    usuario = session.get('compras_user', '').capitalize()
    return Response(MARKETING_HTML.replace('{usuario}', usuario), mimetype='text/html; charset=utf-8')


# ── Self-service de contraseña ────────────────────────────────────────────────
# Cualquier usuario autenticado puede cambiar su propia contraseña sin
# intervención del admin. El hash nuevo se guarda en users_passwords (DB);
# las env vars PASS_<USER> quedan como fallback si la entry de DB no existe.

# Política mínima de contraseña (server-side; no confiar solo en JS).
_PWD_MIN_LEN = 8
_PWD_MAX_LEN = 128

# Blacklist de passwords más comunes en español/inglés. Bloqueo absoluto
# aunque cumplan los demás criterios. Cubre ~90% de los ataques de
# diccionario de bots scanners. Lista pequeña, evaluable en O(1).
# Sebastian (30-abr-2026): refuerzo de password policy en audit de seguridad.
_PWD_BLACKLIST = frozenset([
    "password", "password1", "password123", "passw0rd", "passw0rd1",
    "12345678", "123456789", "1234567890", "qwerty123", "qwertyuiop",
    "abc12345", "abcd1234", "111111", "1q2w3e4r", "1qaz2wsx",
    "admin123", "admin1234", "administrator", "letmein123",
    "welcome1", "welcome123", "iloveyou", "monkey123",
    "espagiria", "espagiria1", "espagiria123", "espagiria2026",
    "animus", "animus1", "animus123", "animus2026",
    "hha2026", "hhagroup", "hhagroup2026", "hhagroup1",
    "colombia", "colombia1", "bogota", "bogota1", "bogota2026",
    "cosmetica", "cosmeticos", "laboratorio", "laboratorio1",
])


def _validate_new_password(pwd, current_pwd, username=None):
    """Valida una password nueva. Retorna lista de errores (vacía si OK).

    Reglas:
      - Longitud entre _PWD_MIN_LEN y _PWD_MAX_LEN
      - Al menos 1 letra y 1 número
      - No idéntica a la actual
      - No en blacklist (top passwords comunes)
      - No idéntica al username (incluso lowercase)
    """
    errors = []
    if not pwd or len(pwd) < _PWD_MIN_LEN:
        errors.append(f"Mínimo {_PWD_MIN_LEN} caracteres.")
    if len(pwd) > _PWD_MAX_LEN:
        errors.append(f"Máximo {_PWD_MAX_LEN} caracteres.")
    if pwd == current_pwd:
        errors.append("La nueva contraseña debe ser distinta a la actual.")
    # Al menos 1 letra y 1 número (anti-passwords débiles tipo "12345678")
    if not any(c.isalpha() for c in pwd):
        errors.append("Debe incluir al menos una letra.")
    if not any(c.isdigit() for c in pwd):
        errors.append("Debe incluir al menos un número.")
    # Blacklist de passwords comunes (case-insensitive)
    if pwd.lower() in _PWD_BLACKLIST:
        errors.append("Contraseña demasiado común. Escoge una distinta.")
    # No usar el username como password
    if username and pwd.lower() == username.lower().strip():
        errors.append("La contraseña no puede ser igual al usuario.")
    return errors


@bp.route('/api/cambiar-password', methods=['POST'])
def cambiar_password():
    """Cambia la password del usuario autenticado.

    Body JSON: {password_actual, password_nueva, password_confirmar}
    Validaciones:
      - Sesión activa
      - password_actual matchea con el hash actual (DB o env var)
      - password_nueva cumple política mínima
      - password_nueva == password_confirmar
      - Rate limit aplicado: 5 intentos fallidos en 15min bloquean al user
    """
    username = session.get('compras_user', '')
    if not username:
        return jsonify({'error': 'No autorizado'}), 401

    body = request.get_json(silent=True) or {}
    actual = (body.get('password_actual') or '').strip()
    nueva = (body.get('password_nueva') or '').strip()
    confirmar = (body.get('password_confirmar') or '').strip()

    if not actual or not nueva or not confirmar:
        return jsonify({'error': 'Faltan campos: password_actual, password_nueva, password_confirmar'}), 400

    if nueva != confirmar:
        return jsonify({'error': 'La confirmación no coincide con la nueva contraseña'}), 400

    # Rate limit: aplicar mismo lock que login. Si han fallado muchas veces
    # cambiando password, también se bloquea (defensa contra atacante con
    # sesión robada que intenta adivinar la actual).
    ip = _client_ip()
    if _is_locked(ip, username):
        return jsonify({'error': 'Demasiados intentos fallidos. Espera 15 minutos.'}), 429

    # Validar password_actual contra el hash vigente (DB o env var)
    expected = _resolve_password_hash(username)
    if not expected:
        # Caso raro: usuario en sesión pero sin hash configurado.
        return jsonify({'error': 'Cuenta sin contraseña configurada. Contacta al admin.'}), 503

    if expected.startswith('pbkdf2:') or expected.startswith('scrypt:'):
        ok = check_password_hash(expected, actual)
    else:
        ok = bool(expected) and hmac.compare_digest(expected, actual)

    if not ok:
        _record_failure(ip, username)
        _log_sec("password_change_failed", username, ip, "actual incorrecta")
        return jsonify({'error': 'Contraseña actual incorrecta'}), 403

    # Validar password nueva (incluye check anti-username)
    errors = _validate_new_password(nueva, actual, username=username)
    if errors:
        return jsonify({'error': ' '.join(errors)}), 400

    # Hashear y guardar
    new_hash = generate_password_hash(nueva, method='pbkdf2:sha256:600000')
    try:
        conn = db_connect()
        conn.execute("PRAGMA busy_timeout=2000")
        conn.execute("""
            INSERT INTO users_passwords (username, password_hash, changed_at, changed_by)
            VALUES (?, ?, datetime('now', 'utc'), ?)
            ON CONFLICT(username) DO UPDATE SET
                password_hash = excluded.password_hash,
                changed_at    = excluded.changed_at,
                changed_by    = excluded.changed_by
        """, (username, new_hash, username))
        # SEC-FIX · 21-may-2026 · invalidar todas las sesiones tras password change
        # Agregamos columna session_version · cada request valida que la session
        # tenga la última version · si no, fuerza re-login.
        # Sebastián 25-may-2026 · audit zero-error · usar IF NOT EXISTS + fallback
        # para evitar try/except: pass silencioso · si el ALTER falla por razón
        # distinta a "ya existe", queda en log de seguridad.
        try:
            conn.execute(
                "ALTER TABLE users_passwords ADD COLUMN IF NOT EXISTS "
                "session_version INTEGER DEFAULT 1"
            )
        except Exception as _e_alter:
            _msg = str(_e_alter).lower()
            if 'duplicate column' in _msg or 'already exists' in _msg:
                pass  # esperado · ya migrada
            else:
                # Fallback sin IF NOT EXISTS (SQLite viejo)
                try:
                    conn.execute(
                        "ALTER TABLE users_passwords ADD COLUMN session_version INTEGER DEFAULT 1"
                    )
                except Exception as _e_fb:
                    _msg2 = str(_e_fb).lower()
                    if 'duplicate column' not in _msg2 and 'already exists' not in _msg2:
                        _log_sec("alter_session_version_failed", username, ip,
                                  str(_e_fb)[:200])
        conn.execute(
            "UPDATE users_passwords SET session_version = COALESCE(session_version, 1) + 1 WHERE username=?",
            (username,),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        _log_sec("password_change_db_error", username, ip, str(e)[:200])
        return jsonify({'error': 'Error guardando contraseña. Intenta de nuevo.'}), 500

    _clear_attempts(ip, username)
    _log_sec("password_changed", username, ip)
    # Forzar re-login en este browser y revocar mfa_trusted cookie
    resp = jsonify({'ok': True, 'message': 'Contraseña actualizada · sesión cerrada · re-loguear.'})
    try:
        session.clear()
        resp.delete_cookie('mfa_trusted')
    except Exception:
        pass
    return resp

