# blueprints/calidad.py — extraído de index.py (Fase C)
import os
import json
import logging
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, CALIDAD_USERS
from database import get_db
from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec, sin_acceso_html
from audit_helpers import audit_log, intentar_insert_con_retry

log = logging.getLogger('calidad')


def _require_calidad():
    """Audit zero-error 2-may-2026 · gating PII + decisiones regulatorias.

    Antes los POSTs de NCs, CAPA, CoA, agua, especificaciones, micro,
    estabilidades NO tenían RBAC: cualquier compras_user creaba/modificaba
    estos registros (operario podía inyectar lecturas falsas de agua,
    CoAs ficticios, etc.).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    u = session.get('compras_user', '')
    if u not in (set(CALIDAD_USERS) | set(ADMIN_USERS)):
        return jsonify({'error': 'Solo Calidad/Admin pueden mutar registros de Calidad'}), 403
    return None, None
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

bp = Blueprint('calidad', __name__)

@bp.route('/calidad')
def calidad_page():
    if 'compras_user' not in session:
        return redirect('/login?next=/calidad')
    u = session.get('compras_user', '')
    if u not in CALIDAD_USERS:
        return Response(sin_acceso_html('Calidad BPM'), mimetype='text/html')
    return Response(CALIDAD_HTML, mimetype='text/html')

@bp.route('/api/calidad/dashboard')
def calidad_dashboard():
    conn = get_db(); c = conn.cursor()
    # Lotes en cuarentena · Sebastian 5-may-2026 (audit zero-error):
    # UPPER() para matchear ambos 'Cuarentena' y 'CUARENTENA' que coexisten
    # en DB · antes este KPI mostraba menos lotes de los reales.
    c.execute("""SELECT COUNT(*) FROM movimientos
                 WHERE tipo='Entrada'
                   AND (UPPER(COALESCE(estado_lote,'')) IN ('CUARENTENA','CUARENTENA_EXTENDIDA')
                        OR (estado_lote IS NULL AND lote IS NOT NULL AND lote != ''))""")
    cuarentena = c.fetchone()[0]
    # Aprobados y rechazados últimos 30d · UPPER tambien
    c.execute("""SELECT COUNT(*) FROM movimientos
                 WHERE UPPER(COALESCE(estado_lote,''))='APROBADO'
                   AND fecha >= date('now','-30 days')""")
    aprobados = c.fetchone()[0]
    c.execute("""SELECT COUNT(*) FROM movimientos
                 WHERE UPPER(COALESCE(estado_lote,''))='RECHAZADO'
                   AND fecha >= date('now','-30 days')""")
    rechazados = c.fetchone()[0]
    # NC abiertas
    c.execute("SELECT COUNT(*) FROM no_conformidades WHERE estado='Abierta'")
    nc_abiertas = c.fetchone()[0]
    # Calibraciones vencidas
    hoy = datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT COUNT(*) FROM calibraciones_instrumentos WHERE fecha_proxima < ? OR estado='Vencida'", (hoy,))
    cals_vencidas = c.fetchone()[0]
    # PT liberados y rechazados ultimos 30d
    c.execute("""SELECT COUNT(*) FROM liberaciones
                 WHERE estado='Liberado'
                 AND fecha_liberacion >= date('now','-30 days')""")
    liberados_mes = c.fetchone()[0]
    c.execute("""SELECT COUNT(*) FROM liberaciones
                 WHERE estado='Rechazado'
                 AND fecha_liberacion >= date('now','-30 days')""")
    rechazados_pt = c.fetchone()[0]
    total_lib = liberados_mes + rechazados_pt
    tasa_liberacion = round((liberados_mes / total_lib * 100), 1) if total_lib > 0 else None
    # Actividad reciente: últimas NC + últimas acciones CC
    actividad = []
    c.execute("""SELECT 't#C' as tipo, descripcion, area, fecha, estado, impacto
                 FROM no_conformidades ORDER BY id DESC LIMIT 5""")
    for r in c.fetchall():
        color = 'rojo' if r[2] in ('Alto','Critico') else 'amari'
        actividad.append({'titulo': f'NC — {r[1][:55]}',
                          'subtitulo': f'{r[2]} · {r[4]}', 'fecha': r[3], 'color': color})
    c.execute("""SELECT material_nombre, lote, estado_lote, fecha
                 FROM movimientos WHERE tipo='Entrada'
                 AND estado_lote IN ('Aprobado','Rechazado')
                 ORDER BY id DESC LIMIT 5""")
    for r in c.fetchall():
        color = 'verde' if r[2] == 'Aprobado' else 'rojo'
        actividad.append({'titulo': f'Lote {r[1] or "s/n"} — {r[2]}',
                          'subtitulo': r[0][:50], 'fecha': r[3], 'color': color})
    c.execute("""SELECT l.producto, l.lote, l.estado, l.fecha_liberacion, l.aprobado_por, l.cliente
                 FROM liberaciones l
                 WHERE l.estado IN ('Liberado','Rechazado')
                 ORDER BY l.id DESC LIMIT 5""")
    for r in c.fetchall():
        color = 'verde' if r[2] == 'Liberado' else 'rojo'
        cliente_txt = f' -> {r[5]}' if r[5] else ''
        actividad.append({'titulo': f'PT {r[2]} -- {r[0][:40]}',
                          'subtitulo': f'Lote {r[1] or "s/n"} · {r[4] or ""}{cliente_txt}',
                          'fecha': r[3] or '', 'color': color})
    actividad.sort(key=lambda x: x.get('fecha','') or '', reverse=True)
    return jsonify({
        'cuarentena': cuarentena,
        'aprobados': aprobados,
        'rechazados': rechazados,
        'nc_abiertas': nc_abiertas,
        'cals_vencidas': cals_vencidas,
        'liberados_mes': liberados_mes,
        'rechazados_pt': rechazados_pt,
        'tasa_liberacion': tasa_liberacion,
        'actividad_reciente': actividad[:10]
    })

# ════════════════════════════════════════════════════════════════════════
# BANDEJA QC DEL DÍA · centro de mando de Calidad
# Sebastián 1-may-2026: "que le resuelva la vida al equipo de Calidad".
# Una sola pantalla con TODO lo pendiente: lotes a liberar, equipos a
# calibrar, NCs/OOS abiertas, cronograma muestreo, registro agua de hoy,
# auditorías próximas. Reemplaza Excel + WhatsApp + 124 docs sueltos.
# ════════════════════════════════════════════════════════════════════════

@bp.route('/api/calidad/bandeja', methods=['GET'])
def calidad_bandeja():
    """Retorna TODO lo pendiente del equipo Calidad en una sola response.

    Secciones:
      - lotes_cuarentena · MP/ME/MEM esperando liberación
      - ncs_abiertas · No Conformidades sin cerrar
      - oos_abiertas · Out of Specification activos
      - calibraciones · vencidas + próximas 7d
      - muestreo_micro_semana · cronograma COC-PRO-011
      - registro_agua_hoy · COC-PRO-008 (null si falta hoy)
      - cola_liberacion · PT esperando liberación QC
      - cola_revisar · cola_liberacion en estado listo_revisar
      - auditorias_proximas · 60 días
      - estabilidades_pendientes · próximas a fecha de análisis

    Auth: cualquier compras_user (lectura abierta).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    fecha_hoy = datetime.now().date().isoformat()
    log = logging.getLogger('calidad')

    out = {'fecha_hoy': fecha_hoy, 'secciones': {}, 'kpis': {}}

    # ── 1. Lotes en cuarentena (MP/ME/MEM) ─────────────────────────────
    # Audit zero-error 2-may-2026: KPIs reales · COUNT separado del LIMIT.
    # Antes 'total' era len(items) capeado a LIMIT 100 → KPI incorrecto si >100.
    try:
        # Sebastian 5-may-2026 (audit zero-error Recepciones): UPPER() para
        # matchear 'Cuarentena' y 'CUARENTENA' que coexisten en DB.
        kpi_row = c.execute("""
            SELECT COUNT(*),
                   COUNT(CASE WHEN (julianday('now') - julianday(m.fecha)) > 5 THEN 1 END)
            FROM movimientos m
            LEFT JOIN maestro_mps mp ON mp.codigo_mp = m.material_id
            WHERE m.tipo = 'Entrada'
              AND UPPER(COALESCE(m.estado_lote, '')) IN ('CUARENTENA','CUARENTENA_EXTENDIDA')
        """).fetchone()
        rows = c.execute("""
            SELECT m.material_id, m.material_nombre, m.lote, m.proveedor,
                   m.cantidad, m.fecha,
                   CAST((julianday('now') - julianday(m.fecha)) AS INTEGER) as dias_cuarentena,
                   COALESCE(mp.tipo_material, 'MP') as tipo
            FROM movimientos m
            LEFT JOIN maestro_mps mp ON mp.codigo_mp = m.material_id
            WHERE m.tipo = 'Entrada'
              AND UPPER(COALESCE(m.estado_lote, '')) IN ('CUARENTENA','CUARENTENA_EXTENDIDA')
            ORDER BY m.fecha ASC
            LIMIT 20
        """).fetchall()
        items = [{
            'material_id': r[0], 'material_nombre': r[1],
            'lote': r[2], 'proveedor': r[3], 'cantidad': r[4],
            'fecha_recepcion': r[5], 'dias_cuarentena': r[6],
            'tipo': r[7], 'critico': (r[6] or 0) > 5,
        } for r in rows]
        out['secciones']['lotes_cuarentena'] = {
            'total': kpi_row[0] or 0,
            'criticos': kpi_row[1] or 0,
            'items': items,
        }
    except Exception as e:
        log.warning('bandeja lotes_cuarentena fallo: %s', e)
        out['secciones']['lotes_cuarentena'] = {'total': 0, 'criticos': 0, 'items': []}

    # ── 2. NCs abiertas ────────────────────────────────────────────────
    try:
        kpi_row = c.execute("""
            SELECT COUNT(*),
                   COUNT(CASE WHEN impacto IN ('Critico','Alto') THEN 1 END)
            FROM no_conformidades WHERE estado = 'Abierta'
        """).fetchone()
        rows = c.execute("""
            SELECT id, fecha, tipo, descripcion, area, responsable, impacto,
                   CAST((julianday('now') - julianday(fecha)) AS INTEGER) as dias_abierta
            FROM no_conformidades
            WHERE estado = 'Abierta'
            ORDER BY CASE impacto
                WHEN 'Critico' THEN 0 WHEN 'Alto' THEN 1
                WHEN 'Medio' THEN 2 ELSE 3 END,
                fecha ASC
            LIMIT 15
        """).fetchall()
        items = [{
            'id': r[0], 'fecha': r[1], 'tipo': r[2],
            'descripcion': (r[3] or '')[:120],
            'area': r[4], 'responsable': r[5], 'impacto': r[6],
            'dias_abierta': r[7], 'urgente': (r[7] or 0) > 30,
        } for r in rows]
        out['secciones']['ncs_abiertas'] = {
            'total': kpi_row[0] or 0,
            'criticas': kpi_row[1] or 0,
            'items': items,
        }
    except Exception as e:
        log.warning('bandeja ncs_abiertas fallo: %s', e)
        out['secciones']['ncs_abiertas'] = {'total': 0, 'criticas': 0, 'items': []}

    # ── 3. OOS abiertas (Out of Specification) ─────────────────────────
    try:
        kpi_oos = c.execute("""
            SELECT COUNT(*) FROM calidad_oos
            WHERE COALESCE(estado, 'abierto') NOT IN ('cerrado', 'descartado')
        """).fetchone()
        rows = c.execute("""
            SELECT id, fecha_deteccion, producto, lote, parametro, valor_obtenido,
                   especificacion, severidad, estado,
                   CAST((julianday('now') - julianday(fecha_deteccion)) AS INTEGER) as dias_abierta
            FROM calidad_oos
            WHERE COALESCE(estado, 'abierto') NOT IN ('cerrado', 'descartado')
            ORDER BY fecha_deteccion ASC
            LIMIT 15
        """).fetchall()
        items = [{
            'id': r[0], 'fecha': r[1], 'producto': r[2], 'lote': r[3],
            'parametro': r[4], 'valor': r[5], 'spec': r[6],
            'severidad': r[7], 'estado': r[8], 'dias_abierta': r[9],
        } for r in rows]
        out['secciones']['oos_abiertas'] = {
            'total': kpi_oos[0] or 0,
            'items': items,
        }
    except Exception as e:
        log.warning('bandeja oos_abiertas fallo: %s', e)
        out['secciones']['oos_abiertas'] = {'total': 0, 'items': []}

    # ── 4. Calibraciones vencidas + próximas 7d ─────────────────────────
    try:
        rows_venc = c.execute("""
            SELECT id, instrumento, codigo, ubicacion, fecha_proxima, responsable, estado,
                   CAST((julianday('now') - julianday(fecha_proxima)) AS INTEGER) as dias_vencida
            FROM calibraciones_instrumentos
            WHERE date(fecha_proxima) < date('now')
            ORDER BY fecha_proxima ASC
            LIMIT 30
        """).fetchall()
        rows_prox = c.execute("""
            SELECT id, instrumento, codigo, ubicacion, fecha_proxima, responsable, estado,
                   CAST((julianday(fecha_proxima) - julianday('now')) AS INTEGER) as dias_restantes
            FROM calibraciones_instrumentos
            WHERE date(fecha_proxima) BETWEEN date('now') AND date('now', '+7 days')
            ORDER BY fecha_proxima ASC
            LIMIT 30
        """).fetchall()
        out['secciones']['calibraciones'] = {
            'vencidas': [{
                'id': r[0], 'instrumento': r[1], 'codigo': r[2],
                'ubicacion': r[3], 'fecha_proxima': r[4],
                'responsable': r[5], 'dias_vencida': r[7],
            } for r in rows_venc],
            'proximas_7d': [{
                'id': r[0], 'instrumento': r[1], 'codigo': r[2],
                'ubicacion': r[3], 'fecha_proxima': r[4],
                'responsable': r[5], 'dias_restantes': r[7],
            } for r in rows_prox],
            'total_vencidas': len(rows_venc),
            'total_proximas': len(rows_prox),
        }
    except Exception as e:
        log.warning('bandeja calibraciones fallo: %s', e)
        out['secciones']['calibraciones'] = {
            'vencidas': [], 'proximas_7d': [],
            'total_vencidas': 0, 'total_proximas': 0,
        }

    # ── 5. Cronograma muestreo microbiológico semana ────────────────────
    try:
        rows = c.execute("""
            SELECT fecha, area_codigo, area_nombre, tipo_muestra, frecuencia, estado, asignado_a
            FROM cronograma_muestreo_micro
            WHERE date(fecha) BETWEEN date('now') AND date('now', '+7 days')
              AND COALESCE(estado, 'pendiente') NOT IN ('completado', 'cancelado')
            ORDER BY fecha ASC, area_codigo
            LIMIT 50
        """).fetchall()
        items = [{
            'fecha': r[0], 'area_codigo': r[1], 'area_nombre': r[2],
            'tipo': r[3], 'frecuencia': r[4], 'estado': r[5],
            'asignado_a': r[6],
        } for r in rows]
        out['secciones']['muestreo_micro_semana'] = {
            'total': len(items), 'items': items,
        }
    except Exception as e:
        # Tabla puede no existir si no se ha implementado el cronograma
        log.info('bandeja muestreo_micro (tabla puede no existir): %s', e)
        out['secciones']['muestreo_micro_semana'] = {'total': 0, 'items': []}

    # ── 6. Registro sistema agua hoy (COC-PRO-008) ──────────────────────
    # Sebastián 1-may-2026: tabla real es calidad_sistema_agua. Antes apuntaba
    # a agua_registros (no existía) · resultaba en alerta perpetua falsa.
    try:
        row = c.execute("""
            SELECT id, fecha, hora, punto_muestreo, tipo_agua, ph,
                   conductividad_us_cm, toc_ppb, microorganismos_ufc_ml,
                   estado, observaciones, operador
            FROM calidad_sistema_agua
            WHERE date(fecha) = date('now')
            ORDER BY id DESC LIMIT 1
        """).fetchone()
        if row:
            out['secciones']['registro_agua_hoy'] = {
                'registrado': True,
                'id': row[0], 'fecha': row[1], 'hora': row[2],
                'punto_muestreo': row[3], 'tipo_agua': row[4],
                'ph': row[5], 'conductividad': row[6], 'toc': row[7],
                'micro': row[8], 'estado': row[9],
                'observaciones': row[10], 'registrado_por': row[11],
            }
        else:
            out['secciones']['registro_agua_hoy'] = {
                'registrado': False,
                'alerta': '⚠️ Falta registro del sistema de agua hoy',
            }
    except Exception as e:
        log.warning('bandeja calidad_sistema_agua read fallo: %s', e)
        out['secciones']['registro_agua_hoy'] = {
            'registrado': False, 'alerta': 'Error consultando registro de agua',
        }

    # ── 7. Cola liberación PT (esperando QC) ───────────────────────────
    try:
        rows = c.execute("""
            SELECT id, producto_nombre, lote, fecha_envasado, fecha_min_liberacion, estado,
                   CAST((julianday(fecha_min_liberacion) - julianday('now')) AS INTEGER) as dias_para
            FROM cola_liberacion
            WHERE COALESCE(estado, '') NOT IN ('liberado', 'rechazado')
            ORDER BY fecha_min_liberacion ASC
            LIMIT 30
        """).fetchall()
        listo_revisar = [r for r in rows if (r[6] or 0) <= 0]
        items_all = [{
            'id': r[0], 'producto': r[1], 'lote': r[2],
            'fecha_envasado': r[3], 'fecha_min_liberacion': r[4],
            'estado': r[5], 'dias_para': r[6],
            'listo_hoy': (r[6] or 0) <= 0,
        } for r in rows]
        out['secciones']['cola_liberacion'] = {
            'total': len(items_all),
            'listos_revisar_hoy': len(listo_revisar),
            'items': items_all[:20],
        }
    except Exception as e:
        log.info('bandeja cola_liberacion: %s', e)
        out['secciones']['cola_liberacion'] = {
            'total': 0, 'listos_revisar_hoy': 0, 'items': [],
        }

    # ── 8. Auditorías próximas 60d ─────────────────────────────────────
    try:
        rows = c.execute("""
            SELECT id, fecha, tipo, area, responsable, descripcion, estado
            FROM auditorias
            WHERE date(fecha) BETWEEN date('now') AND date('now', '+60 days')
              AND COALESCE(estado, 'programada') NOT IN ('completada', 'cancelada')
            ORDER BY fecha ASC
            LIMIT 20
        """).fetchall()
        items = [{
            'id': r[0], 'fecha': r[1], 'tipo': r[2],
            'area': r[3], 'responsable': r[4],
            'descripcion': (r[5] or '')[:80], 'estado': r[6],
        } for r in rows]
        out['secciones']['auditorias_proximas'] = {
            'total': len(items), 'items': items,
        }
    except Exception as e:
        log.info('bandeja auditorias: %s', e)
        out['secciones']['auditorias_proximas'] = {'total': 0, 'items': []}

    # ── 9. Estabilidades pendientes próximas 30d ───────────────────────
    try:
        rows = c.execute("""
            SELECT id, producto, lote, condicion, fecha_inicio, fecha_proxima_analisis, estado,
                   CAST((julianday(fecha_proxima_analisis) - julianday('now')) AS INTEGER) as dias
            FROM estabilidades
            WHERE date(fecha_proxima_analisis) BETWEEN date('now') AND date('now', '+30 days')
              AND COALESCE(estado, 'en_curso') = 'en_curso'
            ORDER BY fecha_proxima_analisis ASC
            LIMIT 20
        """).fetchall()
        items = [{
            'id': r[0], 'producto': r[1], 'lote': r[2],
            'condicion': r[3], 'fecha_inicio': r[4],
            'fecha_proxima': r[5], 'estado': r[6], 'dias': r[7],
        } for r in rows]
        out['secciones']['estabilidades_pendientes'] = {
            'total': len(items), 'items': items,
        }
    except Exception as e:
        log.info('bandeja estabilidades: %s', e)
        out['secciones']['estabilidades_pendientes'] = {'total': 0, 'items': []}

    # ── KPIs unificados ─────────────────────────────────────────────────
    out['kpis'] = {
        'lotes_cuarentena': out['secciones']['lotes_cuarentena']['total'],
        'lotes_cuarentena_criticos': out['secciones']['lotes_cuarentena']['criticos'],
        'ncs_abiertas': out['secciones']['ncs_abiertas']['total'],
        'oos_abiertas': out['secciones']['oos_abiertas']['total'],
        'calibraciones_vencidas': out['secciones']['calibraciones']['total_vencidas'],
        'calibraciones_proximas': out['secciones']['calibraciones']['total_proximas'],
        'muestreo_pendiente_semana': out['secciones']['muestreo_micro_semana']['total'],
        'cola_liberacion_listos': out['secciones']['cola_liberacion']['listos_revisar_hoy'],
        'auditorias_proximas': out['secciones']['auditorias_proximas']['total'],
        'estabilidades_pendientes': out['secciones']['estabilidades_pendientes']['total'],
        'agua_registrada_hoy': out['secciones']['registro_agua_hoy'].get('registrado', False),
    }
    # Total de "items que requieren acción del equipo Calidad"
    out['kpis']['total_pendientes'] = (
        out['kpis']['lotes_cuarentena']
        + out['kpis']['ncs_abiertas']
        + out['kpis']['oos_abiertas']
        + out['kpis']['calibraciones_vencidas']
        + out['kpis']['cola_liberacion_listos']
    )
    return jsonify(out)


@bp.route('/api/calidad/no-conformidades', methods=['GET', 'POST'])
def handle_no_conformidades():
    # GET es libre para cualquier user logueado · POST requiere Calidad/Admin
    if request.method == 'POST':
        err, code = _require_calidad()
        if err: return err, code
    elif 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        desc = (d.get('descripcion') or '').strip()
        if not desc:
            return jsonify({'error': 'descripcion requerida'}), 400
        user = session.get('compras_user', '')
        c.execute("""INSERT INTO no_conformidades
                     (fecha,tipo,descripcion,area,responsable,lote,codigo_mp,
                      impacto,accion_correctiva,estado,creado_por)
                     VALUES (date('now'),?,?,?,?,?,?,?,?,'Abierta',?)""",
                  (d.get('tipo','Proceso'), desc,
                   d.get('area',''), d.get('responsable',''),
                   d.get('lote',''), d.get('codigo_mp',''),
                   d.get('impacto','Bajo'), d.get('accion_correctiva',''),
                   user))
        new_id = c.lastrowid
        # Audit log INVIMA · creación de NC es evento regulado
        try:
            audit_log(c, usuario=user, accion='CREAR_NC', tabla='no_conformidades',
                      registro_id=new_id,
                      despues={'tipo': d.get('tipo','Proceso'),
                                'descripcion': desc[:300],
                                'lote': d.get('lote','')[:100],
                                'impacto': d.get('impacto','Bajo')})
        except Exception as e:
            log.warning('audit_log CREAR_NC fallo: %s', e)
        conn.commit()
        return jsonify({'id': new_id}), 201
    # GET
    c.execute("""SELECT id,fecha,tipo,descripcion,area,responsable,lote,codigo_mp,
                        impacto,accion_correctiva,estado,fecha_cierre,cerrado_por,creado_por
                 FROM no_conformidades ORDER BY id DESC LIMIT 200""")
    cols = ['id','fecha','tipo','descripcion','area','responsable','lote','codigo_mp',
            'impacto','accion_correctiva','estado','fecha_cierre','cerrado_por','creado_por']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify(rows)

@bp.route('/api/calidad/no-conformidades/<int:ncid>/cerrar', methods=['POST'])
def cerrar_no_conformidad(ncid):
    """Cierra una NC. Sebastián 1-may-2026 audit INVIMA:
    - Requiere motivo_cierre (≥10 chars) explícito
    - Requiere accion_correctiva o evidencia
    - RBAC: solo CALIDAD_USERS o ADMIN_USERS
    - Audit log obligatorio (regulación INVIMA)
    """
    user = session.get('compras_user', '')
    # RBAC: solo calidad o admin pueden cerrar NC
    try:
        from config import CALIDAD_USERS, ADMIN_USERS
        autorizados = set(CALIDAD_USERS) | set(ADMIN_USERS)
    except ImportError:
        from config import ADMIN_USERS
        autorizados = set(ADMIN_USERS)
    if user not in autorizados:
        return jsonify({'error': 'Solo Calidad o Admin pueden cerrar NCs (regulación INVIMA)'}), 403

    d = request.get_json(silent=True) or {}
    motivo = (d.get('motivo_cierre') or '').strip()
    accion = (d.get('accion_correctiva') or '').strip()
    if len(motivo) < 10:
        return jsonify({'error': 'motivo_cierre requerido (mín 10 chars)'}), 400
    if len(accion) < 5:
        return jsonify({'error': 'accion_correctiva requerida (mín 5 chars)'}), 400
    conn = get_db(); c = conn.cursor()
    # Verificar NC existe y NO ya cerrada
    row = c.execute(
        "SELECT estado FROM no_conformidades WHERE id=?", (ncid,)
    ).fetchone()
    if not row:
        return jsonify({'error': 'NC no encontrada'}), 404
    if row[0] == 'Cerrada':
        return jsonify({'error': 'NC ya está cerrada'}), 409
    c.execute("""UPDATE no_conformidades
                 SET estado='Cerrada', fecha_cierre=date('now'), cerrado_por=?,
                     accion_correctiva=COALESCE(?, accion_correctiva)
                 WHERE id=?""",
              (user, accion, ncid))
    # Audit log INVIMA
    try:
        import json as _json
        c.execute("""
            INSERT INTO audit_log (usuario, accion, registro_id, antes, despues)
            VALUES (?, 'CERRAR_NC', ?, ?, ?)
        """, (user, str(ncid), _json.dumps({'estado_anterior': row[0]}),
              _json.dumps({'motivo': motivo[:300], 'accion': accion[:300]})))
    except Exception as _e:
        import logging
        logging.getLogger('calidad').warning('audit cerrar_NC fallo: %s', _e)
    conn.commit()
    return jsonify({'ok': True, 'cerrado_por': user, 'fecha_cierre': datetime.now().date().isoformat()})

@bp.route('/api/calidad/calibraciones')
def get_calibraciones():
    conn = get_db(); c = conn.cursor()
    hoy = datetime.now().strftime('%Y-%m-%d')
    # Auto-update estado based on fecha_proxima
    c.execute("""UPDATE calibraciones_instrumentos
                 SET estado='Vencida' WHERE fecha_proxima < ? AND estado='Vigente'""", (hoy,))
    conn.commit()
    c.execute("""SELECT id,instrumento,codigo,ubicacion,fecha_ultima,fecha_proxima,
                        responsable,empresa,estado,certificado,observaciones
                 FROM calibraciones_instrumentos
                 ORDER BY CASE estado WHEN 'Vencida' THEN 0 ELSE 1 END, fecha_proxima ASC""")
    cols = ['id','instrumento','codigo','ubicacion','fecha_ultima','fecha_proxima',
            'responsable','empresa','estado','certificado','observaciones']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify(rows)

# ── CRONOGRAMA DEL DÍA ─────────────────────────────────────────────────────

@bp.route('/api/calidad/cronograma')
def get_cronograma():
    fecha = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT id,nombre,categoria,hora_objetivo,hora_limite,responsable,
                        procedimiento,requiere_valor,unidad_valor,orden
                 FROM calidad_tareas WHERE activa=1 ORDER BY orden, id""")
    cols_t = ['id','nombre','categoria','hora_objetivo','hora_limite','responsable',
              'procedimiento','requiere_valor','unidad_valor','orden']
    tareas = [dict(zip(cols_t, r)) for r in c.fetchall()]
    c.execute("""SELECT tarea_id,usuario,estado,hora_inicio,hora_fin,
                        valor_registrado,observaciones
                 FROM calidad_registros WHERE fecha=?""", (fecha,))
    cols_r = ['tarea_id','usuario','estado','hora_inicio','hora_fin',
              'valor_registrado','observaciones']
    registros = {r[0]: dict(zip(cols_r, r)) for r in c.fetchall()}
    return jsonify({'tareas': tareas, 'registros': registros, 'fecha': fecha})

@bp.route('/api/calidad/cronograma/iniciar', methods=['POST'])
def iniciar_tarea_cron():
    d = request.get_json(silent=True) or {}
    tarea_id = d.get('tarea_id')
    fecha = d.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    hora_ahora = datetime.now().strftime('%H:%M')
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id FROM calidad_registros WHERE fecha=? AND tarea_id=?", (fecha, tarea_id))
    existing = c.fetchone()
    if existing:
        c.execute("UPDATE calidad_registros SET estado='En curso', hora_inicio=? WHERE id=?",
                  (hora_ahora, existing[0]))
    else:
        c.execute("""INSERT INTO calidad_registros
                     (fecha,tarea_id,usuario,estado,hora_inicio)
                     VALUES (?,?,?,?,?)""",
                  (fecha, tarea_id, session.get('compras_user',''), 'En curso', hora_ahora))
    conn.commit()
    return jsonify({'ok': True})

@bp.route('/api/calidad/cronograma/completar', methods=['POST'])
def completar_tarea_cron():
    d = request.get_json(silent=True) or {}
    tarea_id = d.get('tarea_id')
    fecha = d.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    hora_ahora = datetime.now().strftime('%H:%M')
    estado = d.get('estado', 'Completada')
    if estado not in ('Completada', 'No aplica', 'OOS'):
        estado = 'Completada'
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, hora_inicio FROM calidad_registros WHERE fecha=? AND tarea_id=?",
              (fecha, tarea_id))
    existing = c.fetchone()
    if existing:
        c.execute("""UPDATE calidad_registros
                     SET estado=?, hora_fin=?, valor_registrado=?, observaciones=?,
                         usuario=?
                     WHERE id=?""",
                  (estado, hora_ahora, d.get('valor',''), d.get('observaciones',''),
                   session.get('compras_user',''), existing[0]))
    else:
        c.execute("""INSERT INTO calidad_registros
                     (fecha,tarea_id,usuario,estado,hora_fin,valor_registrado,observaciones)
                     VALUES (?,?,?,?,?,?,?)""",
                  (fecha, tarea_id, session.get('compras_user',''),
                   estado, hora_ahora, d.get('valor',''), d.get('observaciones','')))
    if estado == 'OOS':
        c.execute("SELECT nombre FROM calidad_tareas WHERE id=?", (tarea_id,))
        row = c.fetchone()
        nombre_tarea = row[0] if row else 'Tarea de cronograma'
        c.execute("""INSERT INTO no_conformidades
                     (fecha,tipo,descripcion,area,responsable,impacto,
                      accion_correctiva,estado,creado_por)
                     VALUES (date('now'),'Proceso',?,
                     'Calidad','Jefe CC','Alto',
                     ?,'Abierta',?)""",
                  ('OOS detectado en cronograma: ' + nombre_tarea,
                   d.get('observaciones',''),
                   session.get('compras_user','')))
    conn.commit()
    return jsonify({'ok': True})

@bp.route('/api/calidad/cronograma/resumen')
def resumen_cronograma():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM calidad_tareas WHERE activa=1")
    total_tareas = c.fetchone()[0] or 1
    dias = []
    for i in range(6, -1, -1):
        fecha = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        c.execute("""SELECT
                       COUNT(*) as total_reg,
                       SUM(CASE WHEN estado IN ('Completada','No aplica') THEN 1 ELSE 0 END) as comp,
                       SUM(CASE WHEN estado='OOS' THEN 1 ELSE 0 END) as oos
                     FROM calidad_registros WHERE fecha=?""", (fecha,))
        row = c.fetchone()
        dias.append({
            'fecha': fecha,
            'completadas': (row[1] or 0) + (row[2] or 0),
            'oos': row[2] or 0,
            'total_tareas': total_tareas
        })
    return jsonify({'dias': dias, 'total_tareas': total_tareas})


# ═════════════════════════════════════════════════════════════════════════
#   CALIDAD AVANZADA: CoA · Especificaciones MP · Estabilidades · CAPA
# ═════════════════════════════════════════════════════════════════════════

# ─── ESPECIFICACIONES MP ────────────────────────────────────────────────────

@bp.route('/api/calidad/especificaciones', methods=['GET','POST'])
def especificaciones_list():
    if request.method == 'POST':
        # Audit zero-error 2-may-2026: alterar specs farmacopea es decisión técnica
        err, code = _require_calidad()
        if err: return err, code
    elif 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('codigo_mp') or not d.get('parametro'):
            return jsonify({'error':'codigo_mp y parametro requeridos'}), 400
        user = session.get('compras_user','sistema')
        try:
            c.execute("""INSERT INTO especificaciones_mp
                (codigo_mp, parametro, unidad, valor_min, valor_max, metodo_ensayo,
                 obligatorio, tipo, farmacopea_ref, creado_por)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (d['codigo_mp'], d['parametro'], d.get('unidad',''),
                 d.get('valor_min'), d.get('valor_max'), d.get('metodo_ensayo',''),
                 1 if d.get('obligatorio', True) else 0,
                 d.get('tipo','fisicoquimico'), d.get('farmacopea_ref',''),
                 user))
            spec_id = c.lastrowid
            # Audit log INVIMA · alterar specs es regulatorio
            try:
                audit_log(c, usuario=user, accion='CREAR_SPEC_MP',
                          tabla='especificaciones_mp', registro_id=spec_id,
                          despues={'codigo_mp': d['codigo_mp'][:60],
                                    'parametro': d['parametro'][:80],
                                    'min': d.get('valor_min'),
                                    'max': d.get('valor_max')})
            except Exception as e:
                log.warning('audit_log CREAR_SPEC_MP fallo: %s', e)
            conn.commit()
            return jsonify({'ok':True, 'id':spec_id}), 201
        except sqlite3.IntegrityError:
            return jsonify({'error':'Ya existe especificacion para ese MP+parametro'}), 409
    # GET — filtro por codigo_mp opcional
    codigo = request.args.get('codigo_mp','').strip()
    if codigo:
        c.execute("""SELECT * FROM especificaciones_mp WHERE codigo_mp=?
                     ORDER BY parametro""", (codigo,))
    else:
        c.execute("""SELECT * FROM especificaciones_mp
                     ORDER BY codigo_mp, parametro LIMIT 500""")
    cols = [x[0] for x in c.description]
    return jsonify([dict(zip(cols,r)) for r in c.fetchall()])


@bp.route('/api/calidad/especificaciones/<int:eid>', methods=['PATCH','DELETE'])
def especificacion_update(eid):
    if 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'DELETE':
        c.execute("DELETE FROM especificaciones_mp WHERE id=?", (eid,))
        conn.commit()
        return jsonify({'ok':True})
    d = request.json or {}
    fields = ['unidad','valor_min','valor_max','metodo_ensayo','obligatorio',
              'tipo','farmacopea_ref']
    sets = ', '.join(f+'=?' for f in fields if f in d)
    vals = [d[f] for f in fields if f in d]
    if not sets: return jsonify({'error':'Nada que actualizar'}), 400
    vals.append(eid)
    c.execute(f"UPDATE especificaciones_mp SET {sets} WHERE id=?", vals)
    conn.commit()
    return jsonify({'ok':True})


# ─── CoA RESULTADOS ─────────────────────────────────────────────────────────

@bp.route('/api/calidad/coa', methods=['GET','POST'])
def coa_list():
    """Registra resultados de analisis CoA por lote.
    Auto-valida contra especificaciones_mp si existen y marca conforme=0
    si esta fuera de spec.
    """
    # Audit zero-error 2-may-2026: POST de CoA es evidencia regulatoria INVIMA
    if request.method == 'POST':
        err, code = _require_calidad()
        if err: return err, code
    elif 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        d = request.json or {}
        for k in ('lote','codigo_mp','parametro','valor_obtenido'):
            if not d.get(k):
                return jsonify({'error':f'{k} requerido'}), 400

        # Audit zero-error: bloquear CoA si equipo tiene calibración vencida.
        # Antes un instrumento descalibrado podía registrar análisis "válidos".
        equipo_id = d.get('equipo_id')
        if equipo_id:
            try:
                eq = c.execute("""
                    SELECT codigo, fecha_proxima FROM equipos_eventos
                    WHERE equipo_codigo=(SELECT codigo FROM equipos_eventos WHERE id=? LIMIT 1)
                       OR id=?
                    ORDER BY fecha DESC LIMIT 1
                """, (equipo_id, equipo_id)).fetchone()
                if eq and eq[1]:
                    from datetime import date as _date
                    try:
                        venc = _date.fromisoformat(str(eq[1])[:10])
                        if venc < _date.today():
                            return jsonify({
                                'error': f"Equipo {eq[0]} con calibración vencida ({eq[1]}). No se puede registrar CoA.",
                                'codigo': 'EQUIPO_VENCIDO',
                                'equipo': eq[0],
                                'fecha_vencimiento': eq[1],
                            }), 409
                    except (ValueError, TypeError):
                        pass  # fecha mal formada · no bloquear
            except Exception as e:
                log.warning('check equipo vencido fallo: %s', e)

        # Buscar especificacion para auto-validacion
        spec = c.execute("""SELECT valor_min, valor_max, unidad, metodo_ensayo
                            FROM especificaciones_mp
                            WHERE codigo_mp=? AND parametro=?""",
                         (d['codigo_mp'], d['parametro'])).fetchone()
        valor_min_spec = spec[0] if spec else d.get('valor_min_spec')
        valor_max_spec = spec[1] if spec else d.get('valor_max_spec')
        unidad = (spec[2] if spec else d.get('unidad','')) or d.get('unidad','')
        metodo = (spec[3] if spec else d.get('metodo_ensayo','')) or d.get('metodo_ensayo','')

        # Auto-validar conformidad: si valor_obtenido es numerico y hay specs
        conforme = 1
        try:
            val_num = float(str(d['valor_obtenido']).replace(',','.').strip())
            if valor_min_spec is not None and val_num < float(valor_min_spec):
                conforme = 0
            if valor_max_spec is not None and val_num > float(valor_max_spec):
                conforme = 0
        except (ValueError, TypeError):
            # Valor no-numerico (ej: "Conforme", "Cumple") — no auto-validar
            if d.get('conforme') is not None:
                conforme = 1 if d.get('conforme') else 0

        decision = 'Aprobado' if conforme else 'Rechazado'
        if d.get('decision'):
            decision = d['decision']

        user = session.get('compras_user','sistema')
        c.execute("""INSERT INTO coa_resultados
            (lote, codigo_mp, material_nombre, parametro, unidad,
             valor_obtenido, valor_min_spec, valor_max_spec, conforme,
             metodo_ensayo, analista, fecha_analisis, equipo_id,
             observaciones, decision)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d['lote'], d['codigo_mp'], d.get('material_nombre',''),
             d['parametro'], unidad, d['valor_obtenido'],
             valor_min_spec, valor_max_spec, conforme, metodo,
             d.get('analista', user),
             d.get('fecha_analisis'),
             d.get('equipo_id'), d.get('observaciones',''), decision))
        coa_id = c.lastrowid
        # Audit log INVIMA · CoA es evidencia primaria de calidad de MP
        try:
            audit_log(c, usuario=user, accion='CREAR_COA',
                      tabla='coa_resultados', registro_id=coa_id,
                      despues={'lote': d['lote'], 'codigo_mp': d['codigo_mp'],
                                'parametro': d['parametro'][:80],
                                'valor': str(d['valor_obtenido'])[:100],
                                'conforme': bool(conforme),
                                'decision': decision})
        except Exception as e:
            log.warning('audit_log CREAR_COA fallo: %s', e)
        conn.commit()

        # Si NO conforme y no hay NC abierta para este lote+parametro, crear auto
        if not conforme:
            try:
                c.execute("""INSERT INTO no_conformidades
                             (fecha,tipo,descripcion,area,responsable,lote,
                              codigo_mp,impacto,accion_correctiva,estado,creado_por)
                             VALUES (date('now'),'Insumo',?,?,?,?,?,?,?,'Abierta',?)""",
                          (f'CoA fuera de spec: {d["parametro"]}={d["valor_obtenido"]} '
                           f'(spec {valor_min_spec}-{valor_max_spec})',
                           'Calidad', 'Jefe CC', d['lote'], d['codigo_mp'],
                           'Alto', 'Cuarentena lote, evaluar disposicion',
                           session.get('compras_user','sistema')))
                conn.commit()
            except Exception:
                pass

        return jsonify({'ok':True, 'id':c.lastrowid, 'conforme':conforme,
                        'decision':decision}), 201

    # GET — filtros
    lote = request.args.get('lote','').strip()
    codigo_mp = request.args.get('codigo_mp','').strip()
    where, params = [], []
    if lote: where.append('lote=?'); params.append(lote)
    if codigo_mp: where.append('codigo_mp=?'); params.append(codigo_mp)
    sql = "SELECT * FROM coa_resultados"
    if where: sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY fecha_analisis DESC, id DESC LIMIT 500'
    c.execute(sql, params)
    cols = [x[0] for x in c.description]
    return jsonify([dict(zip(cols,r)) for r in c.fetchall()])


@bp.route('/api/calidad/coa/lote/<path:lote>')
def coa_por_lote(lote):
    """Devuelve CoA completo de un lote agrupado por parametro con verdict global."""
    if 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    rows = c.execute("""SELECT parametro, unidad, valor_obtenido, valor_min_spec,
                               valor_max_spec, conforme, metodo_ensayo, analista,
                               fecha_analisis, decision
                        FROM coa_resultados
                        WHERE lote=? ORDER BY fecha_analisis DESC""",
                     (lote,)).fetchall()
    cols = [x[0] for x in c.description]
    parametros = [dict(zip(cols,r)) for r in rows]
    n_total = len(parametros)
    n_conformes = sum(1 for p in parametros if p['conforme'])
    verdict = 'Aprobado' if n_total > 0 and n_conformes == n_total else \
              ('Rechazado' if n_total > 0 else 'Sin analizar')
    return jsonify({
        'lote': lote,
        'parametros': parametros,
        'n_parametros': n_total,
        'n_conformes': n_conformes,
        'verdict': verdict,
    })


# ─── ESTABILIDADES ──────────────────────────────────────────────────────────

@bp.route('/api/calidad/estabilidades', methods=['GET','POST'])
def estabilidades_list():
    # POST requiere RBAC Calidad/Admin · GET libre
    if request.method == 'POST':
        err, code = _require_calidad()
        if err: return err, code
    elif 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        for k in ('producto','lote_piloto','condicion','tiempo_dias','fecha_inicio'):
            if not d.get(k):
                return jsonify({'error':f'{k} requerido'}), 400
        user = session.get('compras_user','sistema')
        c.execute("""INSERT INTO estabilidades
            (producto, lote_piloto, condicion, tiempo_dias, tiempo_etiqueta,
             fecha_inicio, fecha_evaluacion, parametros_json, conforme,
             observaciones, analista, estado)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d['producto'], d['lote_piloto'], d['condicion'],
             int(d['tiempo_dias']), d.get('tiempo_etiqueta',''),
             d['fecha_inicio'], d.get('fecha_evaluacion'),
             d.get('parametros_json','{}'), 1 if d.get('conforme', True) else 0,
             d.get('observaciones',''),
             d.get('analista', user),
             d.get('estado','Programado')))
        est_id = c.lastrowid
        try:
            audit_log(c, usuario=user, accion='CREAR_ESTABILIDAD',
                      tabla='estabilidades', registro_id=est_id,
                      despues={'producto': d['producto'][:80],
                                'lote_piloto': d['lote_piloto'][:80],
                                'condicion': d['condicion'][:80],
                                'tiempo_dias': int(d['tiempo_dias'])})
        except Exception as e:
            log.warning('audit_log CREAR_ESTABILIDAD fallo: %s', e)
        conn.commit()
        return jsonify({'ok':True, 'id':est_id}), 201
    producto = request.args.get('producto','').strip()
    lote = request.args.get('lote','').strip()
    where, params = [], []
    if producto: where.append('producto=?'); params.append(producto)
    if lote: where.append('lote_piloto=?'); params.append(lote)
    sql = 'SELECT * FROM estabilidades'
    if where: sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY fecha_inicio DESC, tiempo_dias ASC LIMIT 300'
    c.execute(sql, params)
    cols = [x[0] for x in c.description]
    return jsonify([dict(zip(cols,r)) for r in c.fetchall()])


# ─── CAPA acciones (workflow real para no_conformidades) ────────────────────

@bp.route('/api/calidad/capa', methods=['GET','POST'])
def capa_list():
    # POST requiere RBAC Calidad/Admin · GET es libre
    if request.method == 'POST':
        err, code = _require_calidad()
        if err: return err, code
    elif 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        for k in ('nc_id','tipo','descripcion'):
            if not d.get(k):
                return jsonify({'error':f'{k} requerido'}), 400
        if d['tipo'] not in ('correctiva','preventiva','contencion'):
            return jsonify({'error':'tipo debe ser correctiva/preventiva/contencion'}), 400
        user = session.get('compras_user','sistema')
        c.execute("""INSERT INTO capa_acciones
            (nc_id, tipo, descripcion, responsable, fecha_compromiso, estado)
            VALUES (?,?,?,?,?,?)""",
            (int(d['nc_id']), d['tipo'], d['descripcion'],
             d.get('responsable',''), d.get('fecha_compromiso'),
             d.get('estado','Pendiente')))
        capa_id = c.lastrowid
        try:
            audit_log(c, usuario=user, accion='CREAR_CAPA',
                      tabla='capa_acciones', registro_id=capa_id,
                      despues={'nc_id': d['nc_id'], 'tipo': d['tipo'],
                                'descripcion': d['descripcion'][:200]})
        except Exception as e:
            log.warning('audit_log CREAR_CAPA fallo: %s', e)
        conn.commit()
        return jsonify({'ok':True, 'id':capa_id}), 201
    nc_id = request.args.get('nc_id','').strip()
    if nc_id:
        c.execute("SELECT * FROM capa_acciones WHERE nc_id=? ORDER BY id ASC", (nc_id,))
    else:
        c.execute("SELECT * FROM capa_acciones ORDER BY creado_en DESC LIMIT 200")
    cols = [x[0] for x in c.description]
    return jsonify([dict(zip(cols,r)) for r in c.fetchall()])


@bp.route('/api/calidad/capa/<int:cid>', methods=['PATCH'])
def capa_update(cid):
    err, code = _require_calidad()
    if err: return err, code
    d = request.json or {}
    user = session.get('compras_user','sistema')
    conn = get_db(); c = conn.cursor()
    fields = ['descripcion','responsable','fecha_compromiso','fecha_ejecucion',
              'evidencia_url','efectiva','verificada_por','fecha_verificacion','estado']
    sets = ', '.join(f+'=?' for f in fields if f in d)
    vals = [d[f] for f in fields if f in d]
    if not sets: return jsonify({'error':'Nada que actualizar'}), 400
    # Si pasa a Verificada, registrar fecha
    if d.get('estado') == 'Verificada' and 'fecha_verificacion' not in d:
        sets += ', fecha_verificacion=date(\'now\')'
    vals.append(cid)
    c.execute(f"UPDATE capa_acciones SET {sets} WHERE id=?", vals)
    try:
        audit_log(c, usuario=user, accion='ACTUALIZAR_CAPA',
                  tabla='capa_acciones', registro_id=cid,
                  despues={k: d[k] for k in fields if k in d})
    except Exception as e:
        log.warning('audit_log ACTUALIZAR_CAPA fallo: %s', e)
    conn.commit()
    return jsonify({'ok':True})


# ─── AUDITORIAS ─────────────────────────────────────────────────────────────

@bp.route('/api/calidad/auditorias', methods=['GET','POST'])
def auditorias_list():
    # POST requiere RBAC Calidad/Admin · GET libre
    if request.method == 'POST':
        err, code = _require_calidad()
        if err: return err, code
    elif 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('tipo') or not d.get('ente_auditado'):
            return jsonify({'error':'tipo y ente_auditado requeridos'}), 400
        user = session.get('compras_user','sistema')
        c.execute("""INSERT INTO auditorias
            (tipo, ente_auditado, fecha_planeada, auditor, alcance, estado)
            VALUES (?,?,?,?,?,?)""",
            (d['tipo'], d['ente_auditado'], d.get('fecha_planeada'),
             d.get('auditor', user),
             d.get('alcance',''), d.get('estado','Planeada')))
        aud_id = c.lastrowid
        try:
            audit_log(c, usuario=user, accion='CREAR_AUDITORIA',
                      tabla='auditorias', registro_id=aud_id,
                      despues={'tipo': d['tipo'], 'ente': d['ente_auditado'][:200],
                                'fecha': d.get('fecha_planeada')})
        except Exception as e:
            log.warning('audit_log CREAR_AUDITORIA fallo: %s', e)
        conn.commit()
        return jsonify({'ok':True, 'id':aud_id}), 201
    c.execute("SELECT * FROM auditorias ORDER BY fecha_planeada DESC LIMIT 100")
    cols = [x[0] for x in c.description]
    return jsonify([dict(zip(cols,r)) for r in c.fetchall()])


# ═══════════════════════════════════════════════════════════════════════════
# CALIDAD AMPLIADA — Micro Specs + Resultados (heatmap) + Agua + OOS
# Sebastian (30-abr-2026)
# ═══════════════════════════════════════════════════════════════════════════

def _calc_estado_micro(valor, valor_texto, spec):
    """Calcula estado de un resultado micro vs spec.
    spec = dict con limite_industria, meta_lab, tipo_limite.
    Returns: 'ok' / 'fuera_meta' / 'fuera_industria' / 'observacion'."""
    if not spec:
        return 'observacion'
    tipo = spec.get('tipo_limite', 'maximo')
    li = spec.get('limite_industria')
    ml = spec.get('meta_lab')
    if tipo == 'ausencia':
        # Si reportan numero > 0 o texto que no diga "ausencia/negativo/<10/<1/0"
        v_str = (valor_texto or '').strip().lower()
        if valor is not None and valor > 0:
            return 'fuera_industria'
        if v_str and not any(k in v_str for k in ['ausencia','ausente','negativo','<10','<1','<100','no detect','0 ufc','sin crecimiento']):
            return 'observacion'
        return 'ok'
    if valor is None:
        return 'observacion'
    if tipo == 'maximo':
        if li is not None and valor > li:
            return 'fuera_industria'
        if ml is not None and valor > ml:
            return 'fuera_meta'
        return 'ok'
    if tipo == 'minimo':
        if li is not None and valor < li:
            return 'fuera_industria'
        if ml is not None and valor < ml:
            return 'fuera_meta'
        return 'ok'
    return 'observacion'


@bp.route('/api/calidad/micro/specs', methods=['GET', 'POST'])
def calidad_micro_specs():
    """GET: lista todas las specs (incluye los defaults globales aplicables a
    cualquier producto si no tiene override).
    POST: crea/actualiza spec para un producto+microorganismo."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        prod = (d.get('producto_nombre') or '').strip()
        micro = (d.get('microorganismo') or '').strip()
        if not prod or not micro:
            return jsonify({'error': 'producto_nombre y microorganismo requeridos'}), 400
        c.execute("""INSERT INTO calidad_micro_specs
            (producto_nombre, microorganismo, unidad, limite_industria,
             meta_lab, tipo_limite, metodo_referencia, activa)
            VALUES (?,?,?,?,?,?,?,1)
            ON CONFLICT(producto_nombre, microorganismo) DO UPDATE SET
              unidad=excluded.unidad,
              limite_industria=excluded.limite_industria,
              meta_lab=excluded.meta_lab,
              tipo_limite=excluded.tipo_limite,
              metodo_referencia=excluded.metodo_referencia""",
            (prod, micro, d.get('unidad') or 'UFC/g',
             d.get('limite_industria'), d.get('meta_lab'),
             d.get('tipo_limite') or 'maximo',
             d.get('metodo_referencia')))
        conn.commit()
        return jsonify({'ok': True})

    producto = (request.args.get('producto') or '').strip()
    rows = c.execute("""SELECT id, producto_nombre, microorganismo, unidad,
                              limite_industria, meta_lab, tipo_limite,
                              metodo_referencia, activa
                       FROM calidad_micro_specs
                       WHERE activa=1
                         AND (? = '' OR producto_nombre = ?)
                       ORDER BY producto_nombre, microorganismo""",
                    (producto, producto)).fetchall()
    cols = ['id','producto_nombre','microorganismo','unidad','limite_industria',
            'meta_lab','tipo_limite','metodo_referencia','activa']
    specs = [dict(zip(cols, r)) for r in rows]
    # Defaults globales
    rows_d = c.execute("""SELECT microorganismo, unidad, limite_industria,
                                 meta_lab, tipo_limite, descripcion
                         FROM calidad_micro_specs_default
                         ORDER BY id""").fetchall()
    cols_d = ['microorganismo','unidad','limite_industria','meta_lab','tipo_limite','descripcion']
    defaults = [dict(zip(cols_d, r)) for r in rows_d]
    return jsonify({'specs': specs, 'defaults': defaults})


@bp.route('/api/calidad/micro/resultados', methods=['GET', 'POST'])
def calidad_micro_resultados():
    """GET: lista resultados con filtros (producto, lote, estado, desde, hasta).
    POST: registra un resultado nuevo. Calcula estado vs spec."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        producto = (d.get('producto_nombre') or '').strip()
        lote = (d.get('lote') or '').strip()
        micro = (d.get('microorganismo') or '').strip()
        if not producto or not lote or not micro:
            return jsonify({'error': 'producto_nombre, lote y microorganismo requeridos'}), 400
        valor = d.get('valor')
        try:
            valor = float(valor) if valor not in (None, '') else None
        except (TypeError, ValueError):
            valor = None
        valor_texto = (d.get('valor_texto') or '').strip() or None

        # Buscar spec: primero por producto, luego default
        spec = c.execute("""SELECT unidad, limite_industria, meta_lab, tipo_limite
                            FROM calidad_micro_specs
                            WHERE producto_nombre=? AND microorganismo=? AND activa=1""",
                         (producto, micro)).fetchone()
        if not spec:
            spec_d = c.execute("""SELECT unidad, limite_industria, meta_lab, tipo_limite
                                  FROM calidad_micro_specs_default
                                  WHERE microorganismo=?""", (micro,)).fetchone()
            spec = spec_d
        spec_dict = None
        if spec:
            spec_dict = {'unidad': spec[0], 'limite_industria': spec[1],
                         'meta_lab': spec[2], 'tipo_limite': spec[3]}
        estado = _calc_estado_micro(valor, valor_texto, spec_dict)
        unidad = (d.get('unidad') or (spec_dict['unidad'] if spec_dict else 'UFC/g'))

        from datetime import date as _date
        fecha_analisis = (d.get('fecha_analisis') or '').strip() or _date.today().isoformat()
        c.execute("""INSERT INTO calidad_micro_resultados
            (lote, producto_nombre, fecha_muestreo, fecha_analisis,
             microorganismo, valor, valor_texto, unidad, estado, laboratorio,
             analista, metodo, observaciones, creado_por)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (lote, producto,
             (d.get('fecha_muestreo') or '').strip() or None,
             fecha_analisis,
             micro, valor, valor_texto, unidad, estado,
             (d.get('laboratorio') or 'Interno').strip(),
             (d.get('analista') or '').strip() or user,
             (d.get('metodo') or '').strip() or None,
             (d.get('observaciones') or '').strip() or None,
             user))
        new_id = c.lastrowid

        # Si fuera_industria → crear OOS automáticamente · race-safe
        # Audit zero-error 2-may-2026: el código OOS-NNN se generaba con
        # SELECT MAX + INSERT sin retry · bajo concurrencia 2 micros simultáneos
        # podían generar mismo código → IntegrityError 500 al usuario.
        oos_codigo = None
        if estado == 'fuera_industria':
            def _insert_oos():
                last = c.execute(
                    "SELECT codigo FROM calidad_oos WHERE codigo LIKE 'OOS-%' ORDER BY id DESC LIMIT 1"
                ).fetchone()
                n = 1
                if last:
                    try: n = int(last[0].split('-')[-1]) + 1
                    except: n = 1
                cod = f'OOS-{n:03d}'
                c.execute("""INSERT INTO calidad_oos
                    (codigo, origen, lote, producto, parametro, valor_obtenido,
                     valor_obtenido_texto, valor_esperado_texto, limite_violado,
                     accion_inmediata, creado_por)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (cod, 'micro', lote, producto, micro, valor, valor_texto,
                     f'≤ {spec_dict["limite_industria"]} {unidad}' if spec_dict else 'según spec',
                     'limite_industria',
                     f'Lote {lote} pasa a CUARENTENA. No liberar hasta cierre OOS.',
                     user))
                return cod, c.lastrowid
            try:
                oos_codigo, oos_id = intentar_insert_con_retry(_insert_oos)
                c.execute("UPDATE calidad_micro_resultados SET oos_id=? WHERE id=?", (oos_id, new_id))
                # Audit log INVIMA · OOS es decisión regulatoria crítica
                try:
                    audit_log(c, usuario=user, accion='CREAR_OOS',
                              tabla='calidad_oos', registro_id=oos_codigo,
                              despues={'lote': lote, 'producto': producto,
                                        'parametro': micro, 'valor': valor})
                except Exception as _e:
                    log.warning('audit_log CREAR_OOS fallo: %s', _e)
            except Exception as _e:
                log.exception('crear OOS fallo: %s', _e)
                # NO silenciar · OOS es regulatorio. Pero tampoco abortar el
                # registro de micro · loguear y seguir (oos_codigo queda None).
                oos_codigo = None
            # Notif in-app a calidad + admin (solo si OOS se creó OK)
            if oos_codigo:
                try:
                    from blueprints.notif import push_notif_multi
                    push_notif_multi(
                        ['controlcalidad.espagiria','aseguramiento.espagiria','sebastian','alejandro'],
                        'capa', f'⚠ OOS {oos_codigo}: {micro} en {producto}',
                        body=f'Lote {lote} · valor {valor or valor_texto} {unidad}',
                        link='/calidad', remitente=user, importante=True
                    )
                except Exception:
                    pass
        elif estado == 'fuera_meta':
            # Notif menos urgente — solo a calidad
            try:
                from blueprints.notif import push_notif
                push_notif('controlcalidad.espagiria', 'capa',
                           f'Resultado fuera de meta lab: {micro} en {producto}',
                           body=f'Lote {lote} · valor {valor or valor_texto} {unidad}',
                           link='/calidad', remitente=user)
            except Exception: pass
        conn.commit()
        return jsonify({'ok': True, 'id': new_id, 'estado': estado, 'oos_codigo': oos_codigo}), 201

    # GET
    producto = (request.args.get('producto') or '').strip()
    lote = (request.args.get('lote') or '').strip()
    estado = (request.args.get('estado') or '').strip()
    desde = (request.args.get('desde') or '').strip()
    hasta = (request.args.get('hasta') or '').strip()
    where = []; params = []
    if producto: where.append('producto_nombre=?'); params.append(producto)
    if lote: where.append('lote=?'); params.append(lote)
    if estado: where.append('estado=?'); params.append(estado)
    if desde: where.append('fecha_analisis >= ?'); params.append(desde)
    if hasta: where.append('fecha_analisis <= ?'); params.append(hasta)
    sql = """SELECT id, lote, producto_nombre, fecha_muestreo, fecha_analisis,
                    microorganismo, valor, valor_texto, unidad, estado,
                    laboratorio, analista, metodo, observaciones, oos_id
             FROM calidad_micro_resultados"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY fecha_analisis DESC, id DESC LIMIT 500"
    rows = c.execute(sql, params).fetchall()
    cols = ['id','lote','producto_nombre','fecha_muestreo','fecha_analisis',
            'microorganismo','valor','valor_texto','unidad','estado',
            'laboratorio','analista','metodo','observaciones','oos_id']
    return jsonify({'resultados': [dict(zip(cols, r)) for r in rows]})


@bp.route('/api/calidad/micro/heatmap', methods=['GET'])
def calidad_micro_heatmap():
    """Mapa de calor: matriz producto × microorganismo con:
       - peor_estado (worst case en últimos N meses)
       - n_resultados
       - n_fuera_industria
       - n_fuera_meta
       - ultimo_valor / fecha
    Window: últimos 12 meses por default.
    Sebastian: 'tener un mapa de calor o de resultados consolidados con alerta'.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    meses = int(request.args.get('meses', 12))
    conn = get_db(); c = conn.cursor()

    # Lista de microorganismos relevantes (defaults + custom usados)
    micros = [r[0] for r in c.execute(
        "SELECT microorganismo FROM calidad_micro_specs_default ORDER BY id"
    ).fetchall()]
    extras = [r[0] for r in c.execute(
        "SELECT DISTINCT microorganismo FROM calidad_micro_resultados "
        "WHERE microorganismo NOT IN (SELECT microorganismo FROM calidad_micro_specs_default)"
    ).fetchall()]
    micros += extras

    # Lista de productos con resultados en la ventana
    prods = [r[0] for r in c.execute(
        "SELECT DISTINCT producto_nombre FROM calidad_micro_resultados "
        "WHERE fecha_analisis >= date('now','-' || ? || ' months') "
        "ORDER BY producto_nombre", (meses,)
    ).fetchall()]

    # Construir matriz
    matriz = []
    for prod in prods:
        row = {'producto': prod, 'cells': []}
        for m in micros:
            cell = c.execute("""SELECT
                  COUNT(*) as n,
                  SUM(CASE WHEN estado='fuera_industria' THEN 1 ELSE 0 END) as n_fi,
                  SUM(CASE WHEN estado='fuera_meta' THEN 1 ELSE 0 END) as n_fm,
                  MAX(fecha_analisis) as ultima_fecha
                FROM calidad_micro_resultados
                WHERE producto_nombre=? AND microorganismo=?
                  AND fecha_analisis >= date('now','-' || ? || ' months')
            """, (prod, m, meses)).fetchone()
            n, n_fi, n_fm, ultima = cell
            if not n:
                row['cells'].append({'micro': m, 'n': 0, 'estado': 'sin_dato'})
                continue
            ult_val = c.execute("""SELECT valor, valor_texto, estado, unidad
                FROM calidad_micro_resultados
                WHERE producto_nombre=? AND microorganismo=? AND fecha_analisis=?
                ORDER BY id DESC LIMIT 1""", (prod, m, ultima)).fetchone()
            estado_peor = 'fuera_industria' if n_fi > 0 else ('fuera_meta' if n_fm > 0 else 'ok')
            row['cells'].append({
                'micro': m, 'n': n,
                'n_fuera_industria': n_fi or 0,
                'n_fuera_meta': n_fm or 0,
                'estado': estado_peor,
                'ultima_fecha': ultima,
                'ultimo_valor': ult_val[0] if ult_val else None,
                'ultimo_texto': ult_val[1] if ult_val else None,
                'unidad': ult_val[3] if ult_val else 'UFC/g',
            })
        matriz.append(row)

    # KPIs globales
    total_res = c.execute(
        "SELECT COUNT(*) FROM calidad_micro_resultados WHERE fecha_analisis >= date('now','-' || ? || ' months')", (meses,)
    ).fetchone()[0] or 0
    total_fi = c.execute(
        "SELECT COUNT(*) FROM calidad_micro_resultados WHERE estado='fuera_industria' AND fecha_analisis >= date('now','-' || ? || ' months')", (meses,)
    ).fetchone()[0] or 0
    total_fm = c.execute(
        "SELECT COUNT(*) FROM calidad_micro_resultados WHERE estado='fuera_meta' AND fecha_analisis >= date('now','-' || ? || ' months')", (meses,)
    ).fetchone()[0] or 0

    return jsonify({
        'meses_ventana': meses,
        'microorganismos': micros,
        'productos': prods,
        'matriz': matriz,
        'kpis': {
            'total_resultados': total_res,
            'total_fuera_industria': total_fi,
            'total_fuera_meta': total_fm,
            'tasa_ok': round((total_res - total_fi - total_fm) * 100 / total_res, 1) if total_res else None,
        },
    })


@bp.route('/api/calidad/agua/registros', methods=['GET', 'POST'])
def calidad_agua_registros():
    """COC-PRO-008 Sistema de Agua. GET lista registros con filtro fecha+punto.
    POST registra una lectura nueva. Calcula estado vs umbrales BPM:
       pH purificada: 5.0-7.5
       conductividad ≤ 1.3 µS/cm a 25°C (USP <645>)
       TOC ≤ 500 ppb (USP <643>)
       microorganismos ≤ 100 UFC/100mL (USP)
    """
    if request.method == 'POST':
        # POST requiere Calidad/Admin · evidencia INVIMA
        err, code = _require_calidad()
        if err: return err, code
    elif 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        punto = (d.get('punto_muestreo') or '').strip()
        if not punto:
            return jsonify({'error': 'punto_muestreo requerido'}), 400

        # Audit zero-error 2-may-2026: validación de plausibilidad física
        # antes de aceptar valores. Antes pH=15 se aceptaba como 'fuera_spec'
        # · ahora rechazamos físicamente imposible.
        ph = d.get('ph')
        cond = d.get('conductividad_us_cm')
        toc = d.get('toc_ppb')
        micro = d.get('microorganismos_ufc_ml')
        try: ph = float(ph) if ph not in (None,'') else None
        except: ph = None
        try: cond = float(cond) if cond not in (None,'') else None
        except: cond = None
        try: toc = float(toc) if toc not in (None,'') else None
        except: toc = None
        try: micro = float(micro) if micro not in (None,'') else None
        except: micro = None
        # Rangos físicos plausibles (valores fuera = error de tipeo)
        if ph is not None and not (0 <= ph <= 14):
            return jsonify({'error': f'pH={ph} fuera de rango físico (0-14)'}), 400
        if cond is not None and not (0 <= cond <= 50):
            return jsonify({'error': f'conductividad={cond} fuera de rango (0-50 µS/cm)'}), 400
        if toc is not None and toc < 0:
            return jsonify({'error': 'TOC no puede ser negativo'}), 400
        if micro is not None and micro < 0:
            return jsonify({'error': 'microorganismos no puede ser negativo'}), 400

        # Calcular estado (USP — agua purificada)
        estado = 'ok'
        warnings = []
        if ph is not None:
            if ph < 5.0 or ph > 7.5: estado = 'fuera_spec'; warnings.append(f'pH={ph} fuera 5.0-7.5')
            elif ph < 5.5 or ph > 7.0: estado = 'alerta' if estado=='ok' else estado
        if cond is not None:
            if cond > 1.3: estado = 'fuera_spec'; warnings.append(f'cond={cond}µS > 1.3')
            elif cond > 1.1: estado = 'alerta' if estado=='ok' else estado
        if toc is not None:
            if toc > 500: estado = 'fuera_spec'; warnings.append(f'TOC={toc}ppb > 500')
            elif toc > 400: estado = 'alerta' if estado=='ok' else estado
        if micro is not None:
            if micro > 100: estado = 'fuera_spec'; warnings.append(f'micro={micro}UFC/ml > 100')
            elif micro > 50: estado = 'alerta' if estado=='ok' else estado

        from datetime import date as _date
        fecha_reg = (d.get('fecha') or '').strip() or _date.today().isoformat()
        obs_extra = d.get('observaciones') or ''
        if warnings:
            obs_final = '; '.join(warnings) + (' | ' + obs_extra if obs_extra else '')
        else:
            obs_final = obs_extra.strip() or None
        c.execute("""INSERT INTO calidad_sistema_agua
            (fecha, hora, punto_muestreo, tipo_agua, ph, conductividad_us_cm,
             toc_ppb, microorganismos_ufc_ml, cloro_residual_ppm, temperatura_c,
             estado, observaciones, operador)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (fecha_reg,
             (d.get('hora') or '').strip() or None,
             punto, d.get('tipo_agua') or 'purificada',
             ph, cond, toc, micro,
             d.get('cloro_residual_ppm'), d.get('temperatura_c'),
             estado, obs_final, user))
        new_id = c.lastrowid
        # Audit log INVIMA · cada lectura de agua es evidencia regulatoria
        try:
            audit_log(c, usuario=user, accion='REGISTRAR_AGUA',
                      tabla='calidad_sistema_agua', registro_id=new_id,
                      despues={'fecha': fecha_reg, 'punto': punto, 'estado': estado,
                                'ph': ph, 'conductividad': cond, 'toc': toc, 'micro': micro})
        except Exception as _e:
            log.warning('audit_log REGISTRAR_AGUA fallo: %s', _e)
        # Si fuera_spec → notif urgente
        if estado == 'fuera_spec':
            try:
                from blueprints.notif import push_notif_multi
                push_notif_multi(
                    ['controlcalidad.espagiria','aseguramiento.espagiria','sebastian'],
                    'capa', f'⚠ Sistema de agua FUERA DE SPEC: {punto}',
                    body='; '.join(warnings),
                    link='/calidad', remitente=user, importante=True
                )
            except Exception: pass
        conn.commit()
        return jsonify({'ok': True, 'id': new_id, 'estado': estado, 'warnings': warnings}), 201

    # GET
    desde = (request.args.get('desde') or '').strip()
    hasta = (request.args.get('hasta') or '').strip()
    punto = (request.args.get('punto') or '').strip()
    where = []; params = []
    if desde: where.append('fecha >= ?'); params.append(desde)
    if hasta: where.append('fecha <= ?'); params.append(hasta)
    if punto: where.append('punto_muestreo=?'); params.append(punto)
    sql = "SELECT * FROM calidad_sistema_agua"
    if where: sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY fecha DESC, hora DESC, id DESC LIMIT 500"
    rows = c.execute(sql, params).fetchall()
    cols = [d[0] for d in c.description]
    out = [dict(zip(cols, r)) for r in rows]
    return jsonify({'registros': out})


@bp.route('/api/calidad/agua/estado-hoy', methods=['GET'])
def calidad_agua_estado_hoy():
    """Estado del registro del sistema de agua HOY.

    Retorna: { registrado: bool, ultimo_registro: {...}, hora_actual,
               necesita_alerta: bool (si pasaron 12pm sin registro) }
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    row = c.execute("""
        SELECT id, fecha, hora, punto_muestreo, tipo_agua, ph,
               conductividad_us_cm, toc_ppb, microorganismos_ufc_ml,
               cloro_residual_ppm, temperatura_c, estado, observaciones, operador
        FROM calidad_sistema_agua
        WHERE date(fecha) = date('now')
        ORDER BY id DESC LIMIT 1
    """).fetchone()
    ahora = datetime.now()
    out = {
        'fecha_hoy': ahora.date().isoformat(),
        'hora_actual': ahora.strftime('%H:%M'),
        'registrado': bool(row),
        'necesita_alerta': False,
        'ultimo_registro': None,
    }
    if row:
        cols = ['id','fecha','hora','punto_muestreo','tipo_agua','ph',
                'conductividad_us_cm','toc_ppb','microorganismos_ufc_ml',
                'cloro_residual_ppm','temperatura_c','estado',
                'observaciones','operador']
        out['ultimo_registro'] = dict(zip(cols, row))
    else:
        # Si pasó del mediodía y no hay registro → alerta
        out['necesita_alerta'] = ahora.hour >= 12
    return jsonify(out)


@bp.route('/api/calidad/agua/tendencia', methods=['GET'])
def calidad_agua_tendencia():
    """Tendencia del sistema de agua últimos N días (default 30).

    Retorna arrays para gráfico + drift detection (3+ lecturas crecientes
    consecutivas en conductividad), conteo fuera_spec, kpis.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        dias = int(request.args.get('dias', 30))
    except (ValueError, TypeError):
        dias = 30
    if not (1 <= dias <= 365):
        return jsonify({'error': 'dias fuera de rango (1-365)'}), 400
    conn = get_db(); c = conn.cursor()
    # Una lectura por fecha (la más reciente del día)
    rows = c.execute("""
        SELECT fecha, MAX(hora) as hora_max,
               AVG(ph) as ph_avg,
               AVG(conductividad_us_cm) as cond_avg,
               AVG(toc_ppb) as toc_avg,
               AVG(microorganismos_ufc_ml) as micro_avg,
               SUM(CASE WHEN estado='fuera_spec' THEN 1 ELSE 0 END) as n_fuera,
               SUM(CASE WHEN estado='alerta' THEN 1 ELSE 0 END) as n_alerta,
               COUNT(*) as n_total
        FROM calidad_sistema_agua
        WHERE date(fecha) >= date('now', '-' || ? || ' days')
        GROUP BY fecha
        ORDER BY fecha ASC
    """, (dias,)).fetchall()
    serie = [{
        'fecha': r[0], 'hora_max': r[1],
        'ph': round(r[2], 2) if r[2] is not None else None,
        'conductividad': round(r[3], 3) if r[3] is not None else None,
        'toc': round(r[4], 1) if r[4] is not None else None,
        'micro': round(r[5], 1) if r[5] is not None else None,
        'n_fuera_spec': r[6] or 0,
        'n_alerta': r[7] or 0,
        'n_total': r[8] or 0,
    } for r in rows]

    # Drift detection: 3+ lecturas consecutivas crecientes en conductividad
    drift_alerta = False
    drift_dias = 0
    if len(serie) >= 3:
        cond_vals = [(s['fecha'], s['conductividad']) for s in serie if s['conductividad'] is not None]
        if len(cond_vals) >= 3:
            # Ventana móvil de 3
            for i in range(len(cond_vals) - 2):
                a, b, c_v = cond_vals[i][1], cond_vals[i+1][1], cond_vals[i+2][1]
                if a < b < c_v:
                    drift_dias = 3
                    if i + 3 < len(cond_vals) and cond_vals[i+3][1] > c_v:
                        drift_dias = 4
                    drift_alerta = True
            # Si la racha continúa hasta hoy, también marca
            ult3 = cond_vals[-3:]
            if len(ult3) == 3 and ult3[0][1] < ult3[1][1] < ult3[2][1]:
                drift_alerta = True

    total_dias_con_registro = sum(1 for s in serie if s['n_total'] > 0)
    total_fuera_spec = sum(s['n_fuera_spec'] for s in serie)
    total_alerta = sum(s['n_alerta'] for s in serie)
    total_lecturas = sum(s['n_total'] for s in serie)

    return jsonify({
        'dias_ventana': dias,
        'serie': serie,
        'drift_alerta': drift_alerta,
        'drift_dias_consecutivos': drift_dias,
        'kpis': {
            'dias_con_registro': total_dias_con_registro,
            'dias_sin_registro': dias - total_dias_con_registro,
            'cobertura_pct': round(total_dias_con_registro * 100 / dias, 1) if dias else 0,
            'lecturas_totales': total_lecturas,
            'lecturas_fuera_spec': total_fuera_spec,
            'lecturas_alerta': total_alerta,
            'tasa_ok_pct': round((total_lecturas - total_fuera_spec - total_alerta) * 100 / total_lecturas, 1) if total_lecturas else None,
        },
    })


@bp.route('/api/calidad/agua/exportar-csv', methods=['GET'])
def calidad_agua_exportar_csv():
    """Exporta registros del sistema de agua en CSV (para INVIMA)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    desde = (request.args.get('desde') or '').strip()
    hasta = (request.args.get('hasta') or '').strip()
    conn = get_db(); c = conn.cursor()
    where = []; params = []
    if desde: where.append('fecha >= ?'); params.append(desde)
    if hasta: where.append('fecha <= ?'); params.append(hasta)
    sql = ("SELECT fecha, hora, punto_muestreo, tipo_agua, ph, "
           "conductividad_us_cm, toc_ppb, microorganismos_ufc_ml, "
           "cloro_residual_ppm, temperatura_c, estado, observaciones, operador "
           "FROM calidad_sistema_agua")
    if where: sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY fecha DESC, hora DESC LIMIT 10000"
    rows = c.execute(sql, params).fetchall()
    import csv
    from io import StringIO
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(['Fecha','Hora','Punto','Tipo','pH','Conductividad uS/cm',
                 'TOC ppb','Micro UFC/mL','Cloro ppm','Temp C',
                 'Estado','Observaciones','Operador'])
    for r in rows:
        w.writerow([str(x) if x is not None else '' for x in r])
    csv_text = buf.getvalue()
    fn = f'sistema_agua_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
    return Response(
        csv_text,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename={fn}'},
    )


@bp.route('/api/calidad/oos', methods=['GET'])
def calidad_oos_list():
    """Lista de OOS (Out Of Spec). Filtros: estado, desde, hasta, lote."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    estado = (request.args.get('estado') or '').strip()
    conn = get_db(); c = conn.cursor()
    sql = "SELECT * FROM calidad_oos"
    params = []
    if estado: sql += " WHERE estado=?"; params.append(estado)
    sql += " ORDER BY estado='cerrado' ASC, fecha_deteccion DESC LIMIT 200"
    rows = c.execute(sql, params).fetchall()
    cols = [d[0] for d in c.description]
    return jsonify({'oos': [dict(zip(cols, r)) for r in rows]})


@bp.route('/api/calidad/oos/<int:oos_id>', methods=['PATCH'])
def calidad_oos_update(oos_id):
    """Actualiza OOS — flujo investigación → aprobación → cierre."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    d = request.get_json(silent=True) or {}
    conn = get_db(); c = conn.cursor()
    sets = []; params = []
    for col in ('accion_inmediata','causa_raiz','disposicion','aprobado_por',
                'fecha_objetivo_cierre','capa_id'):
        if col in d:
            sets.append(f'{col}=?'); params.append(d[col])
    if 'estado' in d:
        nuevo = d['estado']
        if nuevo not in ('abierto','en_investigacion','en_aprobacion','cerrado','rechazado'):
            return jsonify({'error': 'estado invalido'}), 400
        sets.append('estado=?'); params.append(nuevo)
        if nuevo == 'cerrado':
            sets.append('fecha_cierre=?'); params.append(datetime.now().date().isoformat())
            sets.append('aprobado_por=?'); params.append(user)
            sets.append('fecha_aprobacion=?'); params.append(datetime.now().isoformat())
    if not sets:
        return jsonify({'error': 'nada que actualizar'}), 400
    params.append(oos_id)
    c.execute(f"UPDATE calidad_oos SET {', '.join(sets)} WHERE id=?", params)
    conn.commit()
    return jsonify({'ok': True})


# ════════════════════════════════════════════════════════════════════════
# EQUIPOS Y CALIBRACIONES · COC-PRO-006 + COC-PRO-012 + PRD-PRO-004
# Sebastián 1-may-2026: integra los 104 equipos del seed con tracking de
# vigencia, hoja de vida y cronograma 2026 importado del xlsx oficial.
# ════════════════════════════════════════════════════════════════════════

@bp.route('/api/calidad/equipos/dashboard', methods=['GET'])
def calidad_equipos_dashboard():
    """KPIs + lista de equipos vencidos/próximos. Pantalla principal del módulo."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()

    # Total equipos activos
    total_activos = c.execute(
        "SELECT COUNT(DISTINCT codigo) FROM equipos_planta WHERE COALESCE(activo,1)=1"
    ).fetchone()[0] or 0

    # Por equipo, calcular última fecha_proxima del último evento de calibración o verificación
    # Si no hay evento, queda como "sin tracking"
    rows = c.execute("""
        SELECT ep.codigo, ep.nombre, ep.area_codigo, ep.ubicacion_raw, ep.tipo,
               (SELECT MAX(fecha_proxima) FROM equipos_eventos
                WHERE equipo_codigo = ep.codigo
                  AND tipo_evento IN ('calibracion','verificacion_semestral')
                  AND fecha_proxima IS NOT NULL) as fecha_proxima_cal,
               (SELECT MAX(fecha) FROM equipos_eventos
                WHERE equipo_codigo = ep.codigo
                  AND tipo_evento = 'calibracion') as ultima_cal
        FROM equipos_planta ep
        WHERE COALESCE(ep.activo,1) = 1
        GROUP BY ep.codigo
        ORDER BY ep.codigo
    """).fetchall()

    vencidos = []
    proximos_30d = []
    sin_tracking = []
    vigentes = 0
    for cod, nom, area, ubic, tipo, prox, ult in rows:
        if not prox:
            sin_tracking.append({
                'codigo': cod, 'nombre': nom, 'area': area,
                'ubicacion': ubic, 'tipo': tipo,
                'ultima_calibracion': ult,
            })
            continue
        # Calcular días
        try:
            from datetime import date as _date
            f_prox = _date.fromisoformat(prox)
            dias = (f_prox - _date.today()).days
        except Exception:
            sin_tracking.append({'codigo': cod, 'nombre': nom, 'tipo': tipo})
            continue
        item = {
            'codigo': cod, 'nombre': nom, 'area': area,
            'ubicacion': ubic, 'tipo': tipo,
            'fecha_proxima': prox, 'ultima_calibracion': ult,
            'dias_para_vencer': dias,
        }
        if dias < 0:
            item['dias_vencido'] = abs(dias)
            vencidos.append(item)
        elif dias <= 30:
            proximos_30d.append(item)
        else:
            vigentes += 1
    vencidos.sort(key=lambda x: x['dias_vencido'], reverse=True)
    proximos_30d.sort(key=lambda x: x['dias_para_vencer'])

    return jsonify({
        'kpis': {
            'total_activos': total_activos,
            'vigentes': vigentes,
            'proximos_30d': len(proximos_30d),
            'vencidos': len(vencidos),
            'sin_tracking': len(sin_tracking),
        },
        'vencidos': vencidos[:50],
        'proximos_30d': proximos_30d[:50],
        'sin_tracking': sin_tracking[:50],
    })


@bp.route('/api/calidad/equipos/cronograma', methods=['GET'])
def calidad_equipos_cronograma():
    """Cronograma del mes (default mes actual). Querystring: ?mes=N&anio=YYYY."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    from datetime import date as _date
    hoy = _date.today()
    try:
        mes = int(request.args.get('mes', hoy.month))
        anio = int(request.args.get('anio', hoy.year))
    except (ValueError, TypeError):
        return jsonify({'error': 'mes y anio deben ser enteros'}), 400
    if not (1 <= mes <= 12):
        return jsonify({'error': 'mes fuera de rango'}), 400
    conn = get_db(); c = conn.cursor()
    rows = c.execute("""
        SELECT cron.id, cron.equipo_codigo, ep.nombre, ep.area_codigo,
               cron.tipo_actividad, cron.estado, cron.fecha_completado,
               cron.completado_por, cron.observaciones
        FROM equipos_cronograma cron
        LEFT JOIN equipos_planta ep ON ep.codigo = cron.equipo_codigo
        WHERE cron.anio = ? AND cron.mes = ?
        ORDER BY cron.tipo_actividad, cron.equipo_codigo
        LIMIT 500
    """, (anio, mes)).fetchall()
    items = [{
        'id': r[0], 'equipo_codigo': r[1], 'equipo_nombre': r[2] or '',
        'area': r[3] or '', 'tipo_actividad': r[4],
        'estado': r[5], 'fecha_completado': r[6],
        'completado_por': r[7], 'observaciones': r[8],
    } for r in rows]
    completados = sum(1 for i in items if i['estado'] == 'completado')
    return jsonify({
        'anio': anio, 'mes': mes,
        'items': items,
        'kpis': {
            'total': len(items),
            'completados': completados,
            'pendientes': len(items) - completados,
            'cumplimiento_pct': round(completados * 100 / len(items), 1) if items else None,
        },
    })


@bp.route('/api/calidad/equipos/<path:codigo>/hoja-vida', methods=['GET'])
def calidad_equipos_hoja_vida(codigo):
    """Histórico completo del equipo: datos + todos los eventos."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    eq = c.execute("""
        SELECT codigo, nombre, area_codigo, ubicacion_raw, tipo,
               capacidad_raw, capacidad_litros, capacidad_kg,
               estado_operacional, activo, notas, creado_en
        FROM equipos_planta
        WHERE codigo = ?
        LIMIT 1
    """, (codigo,)).fetchone()
    if not eq:
        return jsonify({'error': f'equipo {codigo} no encontrado'}), 404
    eventos = c.execute("""
        SELECT id, tipo_evento, fecha, fecha_proxima, estado, responsable,
               empresa_externa, certificado_url, resultado, observaciones, creado_por
        FROM equipos_eventos
        WHERE equipo_codigo = ?
        ORDER BY fecha DESC, id DESC
        LIMIT 200
    """, (codigo,)).fetchall()
    cronograma = c.execute("""
        SELECT anio, mes, tipo_actividad, estado, fecha_completado
        FROM equipos_cronograma
        WHERE equipo_codigo = ?
        ORDER BY anio DESC, mes DESC
        LIMIT 50
    """, (codigo,)).fetchall()
    return jsonify({
        'equipo': {
            'codigo': eq[0], 'nombre': eq[1], 'area': eq[2],
            'ubicacion': eq[3], 'tipo': eq[4],
            'capacidad_raw': eq[5], 'capacidad_litros': eq[6], 'capacidad_kg': eq[7],
            'estado_operacional': eq[8], 'activo': bool(eq[9]),
            'notas': eq[10], 'creado_en': eq[11],
        },
        'eventos': [{
            'id': r[0], 'tipo_evento': r[1], 'fecha': r[2],
            'fecha_proxima': r[3], 'estado': r[4], 'responsable': r[5],
            'empresa_externa': r[6], 'certificado_url': r[7],
            'resultado': r[8], 'observaciones': r[9], 'creado_por': r[10],
        } for r in eventos],
        'cronograma': [{
            'anio': r[0], 'mes': r[1], 'tipo_actividad': r[2],
            'estado': r[3], 'fecha_completado': r[4],
        } for r in cronograma],
    })


@bp.route('/api/calidad/equipos/<path:codigo>/registrar-evento', methods=['POST'])
def calidad_equipos_registrar_evento(codigo):
    """Registra un evento (calibración, verificación, mantenimiento, etc.) en hoja de vida.

    Body: {
      tipo_evento: str (req · uno de los CHECK constraint),
      fecha_proxima: str opt (cuándo vence)
      estado: str opt (default 'completado'),
      responsable, empresa_externa, certificado_url, resultado, observaciones
    }

    RBAC: solo CALIDAD_USERS o ADMIN_USERS pueden registrar.
    """
    user = session.get('compras_user', '')
    try:
        from config import CALIDAD_USERS, ADMIN_USERS
        autorizados = set(CALIDAD_USERS) | set(ADMIN_USERS)
    except ImportError:
        from config import ADMIN_USERS
        autorizados = set(ADMIN_USERS)
    if user not in autorizados:
        return jsonify({'error': 'Solo Calidad o Admin pueden registrar eventos de equipos'}), 403

    conn = get_db(); c = conn.cursor()
    eq = c.execute("SELECT 1 FROM equipos_planta WHERE codigo=?", (codigo,)).fetchone()
    if not eq:
        return jsonify({'error': f'equipo {codigo} no encontrado'}), 404

    d = request.get_json(silent=True) or {}
    tipo = (d.get('tipo_evento') or '').strip()
    valid_tipos = ('calibracion','verificacion_diaria','verificacion_semestral',
                    'mantenimiento_preventivo','mantenimiento_correctivo',
                    'baja','reparacion','validacion','reactivacion')
    if tipo not in valid_tipos:
        return jsonify({'error': f'tipo_evento inválido. Uno de: {", ".join(valid_tipos)}'}), 400

    fecha = (d.get('fecha') or datetime.now().date().isoformat()).strip()
    fecha_proxima = (d.get('fecha_proxima') or '').strip() or None
    estado = (d.get('estado') or 'completado').strip()
    if estado not in ('completado','programado','en_curso','cancelado'):
        return jsonify({'error': 'estado inválido'}), 400

    try:
        c.execute("""
            INSERT INTO equipos_eventos
              (equipo_codigo, tipo_evento, fecha, fecha_proxima, estado,
               responsable, empresa_externa, certificado_url, resultado,
               observaciones, creado_por)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (codigo, tipo, fecha, fecha_proxima, estado,
              d.get('responsable'), d.get('empresa_externa'),
              d.get('certificado_url'), d.get('resultado'),
              d.get('observaciones'), user))
        evento_id = c.lastrowid
        # Si es completado y reactiva, actualizar estado_operacional
        if tipo in ('reactivacion','calibracion','verificacion_semestral') and estado == 'completado':
            c.execute("UPDATE equipos_planta SET estado_operacional='operativo' "
                      "WHERE codigo=? AND estado_operacional!='baja'", (codigo,))
        elif tipo == 'baja':
            c.execute("UPDATE equipos_planta SET estado_operacional='baja' "
                      "WHERE codigo=?", (codigo,))
        elif tipo in ('mantenimiento_correctivo','reparacion'):
            c.execute("UPDATE equipos_planta SET estado_operacional='mantenimiento' "
                      "WHERE codigo=? AND estado_operacional!='baja'", (codigo,))
        # Audit log
        try:
            import json as _json
            c.execute("""
                INSERT INTO audit_log (usuario, accion, registro_id, despues)
                VALUES (?, 'EQUIPOS_REGISTRAR_EVENTO', ?, ?)
            """, (user, codigo, _json.dumps({
                'tipo': tipo, 'fecha': fecha, 'fecha_proxima': fecha_proxima,
                'estado': estado, 'evento_id': evento_id,
            })))
        except Exception as _e:
            logging.getLogger('calidad').debug('audit equipos registrar fallo: %s', _e)
        conn.commit()
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return jsonify({'error': str(e)[:200]}), 500
    return jsonify({'ok': True, 'evento_id': evento_id})


@bp.route('/api/calidad/equipos/cronograma/<int:cron_id>/completar', methods=['POST'])
def calidad_equipos_cronograma_completar(cron_id):
    """Marca un item del cronograma como completado y crea evento asociado.

    Body opcional: {observaciones, responsable}
    """
    user = session.get('compras_user', '')
    try:
        from config import CALIDAD_USERS, ADMIN_USERS
        autorizados = set(CALIDAD_USERS) | set(ADMIN_USERS)
    except ImportError:
        from config import ADMIN_USERS
        autorizados = set(ADMIN_USERS)
    if user not in autorizados:
        return jsonify({'error': 'Solo Calidad o Admin'}), 403

    conn = get_db(); c = conn.cursor()
    row = c.execute("""
        SELECT equipo_codigo, anio, mes, tipo_actividad, estado
        FROM equipos_cronograma WHERE id=?
    """, (cron_id,)).fetchone()
    if not row:
        return jsonify({'error': 'cronograma no encontrado'}), 404
    if row[4] == 'completado':
        return jsonify({'error': 'ya está completado'}), 409

    d = request.get_json(silent=True) or {}
    obs = (d.get('observaciones') or '').strip()
    resp = (d.get('responsable') or user).strip()
    fecha_hoy = datetime.now().date().isoformat()

    try:
        # Mapear tipo_actividad → tipo_evento
        tipo_map = {
            'preventivo': 'mantenimiento_preventivo',
            'correctivo': 'mantenimiento_correctivo',
            'verificacion': 'verificacion_semestral',
            'calibracion': 'calibracion',
        }
        tipo_evento = tipo_map.get(row[3], 'mantenimiento_preventivo')
        c.execute("""
            INSERT INTO equipos_eventos
              (equipo_codigo, tipo_evento, fecha, estado, responsable,
               observaciones, creado_por)
            VALUES (?, ?, ?, 'completado', ?, ?, ?)
        """, (row[0], tipo_evento, fecha_hoy, resp, obs or None, user))
        evento_id = c.lastrowid
        c.execute("""
            UPDATE equipos_cronograma
            SET estado='completado', fecha_completado=?, completado_por=?,
                evento_id=?, observaciones=?
            WHERE id=?
        """, (fecha_hoy, user, evento_id, obs or None, cron_id))
        conn.commit()
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return jsonify({'error': str(e)[:200]}), 500
    return jsonify({'ok': True, 'evento_id': evento_id})


@bp.route('/api/calidad/equipos/importar-cronograma', methods=['POST'])
def calidad_equipos_importar_cronograma():
    """Importa items del cronograma anual desde JSON. RBAC admin.

    Body: {
      anio: int (default 2026),
      items: [{equipo_codigo, mes, tipo_actividad}, ...]
    }
    Idempotente · UNIQUE(equipo_codigo, anio, mes, tipo_actividad).
    """
    user = session.get('compras_user', '')
    from config import ADMIN_USERS
    if user not in ADMIN_USERS:
        return jsonify({'error': 'Solo Admin'}), 403
    d = request.get_json(silent=True) or {}
    try:
        anio = int(d.get('anio', 2026))
    except (ValueError, TypeError):
        return jsonify({'error': 'anio inválido'}), 400
    items = d.get('items') or []
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'items debe ser lista no vacía'}), 400

    conn = get_db(); c = conn.cursor()
    insertados = 0
    saltados = 0
    errores = []
    for it in items[:5000]:  # límite anti-bomb
        try:
            eq = (it.get('equipo_codigo') or '').strip()
            mes = int(it.get('mes', 0))
            tipo = (it.get('tipo_actividad') or '').strip()
            if not eq or not (1 <= mes <= 12):
                errores.append(f'invalid: {it}')
                continue
            if tipo not in ('preventivo','correctivo','verificacion','calibracion'):
                errores.append(f'tipo invalido: {it}')
                continue
            r = c.execute("""
                INSERT OR IGNORE INTO equipos_cronograma
                  (equipo_codigo, anio, mes, tipo_actividad)
                VALUES (?, ?, ?, ?)
            """, (eq, anio, mes, tipo))
            if r.rowcount > 0:
                insertados += 1
            else:
                saltados += 1
        except Exception as e:
            errores.append(f'{it}: {e}')
    conn.commit()
    return jsonify({
        'ok': True, 'anio': anio,
        'insertados': insertados,
        'saltados_ya_existian': saltados,
        'errores': errores[:20],
    })
