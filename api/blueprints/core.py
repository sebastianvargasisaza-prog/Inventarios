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
        row = conn.execute(
            "SELECT password_hash FROM users_passwords WHERE username=?",
            (username,)
        ).fetchone()
        conn.close()
        if row and row[0]:
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
    """Diagnostico publico — version, DB, tablas clave.

    Sebastián 12-may-2026: tras incidente 'database disk image is malformed',
    el endpoint ahora retorna 503 si detecta malformed (en lugar de 200 con
    tables.err). Esto permite a Render auto-detect el problema y alerta a
    cualquier monitoreo externo (Pingdom, UptimeRobot, etc).
    """
    import sqlite3 as _sq, os as _os, subprocess as _sp
    try:
        commit = _sp.check_output(['git','rev-parse','--short','HEAD'],
            cwd=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
            stderr=_sp.DEVNULL).decode().strip()
    except Exception:
        commit = 'unknown'
    db_exists = _os.path.exists(DB_PATH)
    db_size = round(_os.path.getsize(DB_PATH)/1024, 1) if db_exists else 0
    tables = {}
    malformed = False
    try:
        conn = _sq.connect(DB_PATH, timeout=3.0)
        # Integrity check rápido (no quick) · más confiable que solo intentar query
        try:
            ic = conn.execute('PRAGMA quick_check').fetchone()
            if ic and ic[0] != 'ok':
                malformed = True
        except _sq.DatabaseError:
            malformed = True
        for tbl in ['maestro_mps','solicitudes_compra','ordenes_compra','movimientos']:
            try:
                tables[tbl] = conn.execute(f'SELECT COUNT(*) FROM {tbl}').fetchone()[0]
            except _sq.DatabaseError as e:
                tables[tbl] = 'err'
                if 'malformed' in str(e).lower() or 'corrupt' in str(e).lower():
                    malformed = True
        try:
            tables['planta_pendientes'] = conn.execute(
                "SELECT COUNT(*) FROM solicitudes_compra WHERE estado='Aprobada' AND area='Produccion' AND (numero_oc IS NULL OR numero_oc='')").fetchone()[0]
        except: pass
    except _sq.DatabaseError as e:
        tables['error'] = str(e)
        if 'malformed' in str(e).lower() or 'corrupt' in str(e).lower():
            malformed = True
    except Exception as e:
        tables['error'] = str(e)
    payload = {
        'status': 'error' if malformed else 'ok',
        'commit': commit,
        'db_exists': db_exists,
        'db_size_kb': db_size,
        'tables': tables,
    }
    if malformed:
        # Log SEC HIGH para alerta externa
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
        return jsonify(payload), 503  # Service Unavailable
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
        conn = _sq.connect(DB_PATH, timeout=2)
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
                       SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad ELSE -m.cantidad END) as stock_neto,
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
    html = DASHBOARD_HTML.replace('{usuario}', usuario).replace('{es_admin}', es_admin)
    resp = Response(html, mimetype='text/html; charset=utf-8')
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

# (rate limiter y hooks de seguridad → auth.py — registrados via register_hooks(app))

@bp.route('/hub')
def hub():
    if 'compras_user' not in session:
        return redirect('/login?next=/modulos')
    from templates_py.hub_html import HUB_HTML
    return Response(HUB_HTML, mimetype='text/html')


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
    if not next_url.startswith('/') or next_url.startswith('//'):
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
        # Soporte PBKDF2 (env var con hash) y plaintext legacy
        if expected and (expected.startswith('pbkdf2:') or expected.startswith('scrypt:')):
            match = check_password_hash(expected, password)
        else:
            match = bool(expected) and hmac.compare_digest(expected, password)
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
                if _is_mfa_enabled(username):
                    # Validar cookie mfa_trusted (firmada con SECRET_KEY)
                    trusted_cookie = request.cookies.get('mfa_trusted', '')
                    skip_mfa = False
                    if trusted_cookie:
                        import hashlib, hmac as _hmac
                        # La cookie mfa_trusted se firma con la MISMA llave que
                        # las sesiones Flask (app.secret_key). Nunca un literal
                        # 'devsecret': sería público y permitiría forjar la
                        # cookie y saltar MFA. Si SECRET_KEY no está en env,
                        # app.secret_key es aleatoria por proceso (segura).
                        secret = current_app.secret_key or ''
                        parts = trusted_cookie.split('|')
                        if len(parts) == 3:
                            user_c, ts_c, sig_c = parts
                            try:
                                ts_int = int(ts_c)
                                # Verificar firma
                                msg = f"{user_c}|{ts_c}"
                                expected = _hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()[:32]
                                if (_hmac.compare_digest(expected, sig_c)
                                        and user_c == username
                                        and (time.time() - ts_int) < 60 * 24 * 3600):
                                    skip_mfa = True
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
    html = COMPRAS_HTML.replace('{usuario}', usuario).replace('{es_contadora}', es_contadora)
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
        conn.commit()
        conn.close()
    except Exception as e:
        _log_sec("password_change_db_error", username, ip, str(e)[:200])
        return jsonify({'error': 'Error guardando contraseña. Intenta de nuevo.'}), 500

    _clear_attempts(ip, username)
    _log_sec("password_changed", username, ip)
    return jsonify({'ok': True, 'message': 'Contraseña actualizada correctamente.'})

