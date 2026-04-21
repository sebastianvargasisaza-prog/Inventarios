# blueprints/calidad.py — extraído de index.py (Fase C)
import os
import json
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS
from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec
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
    return Response(CALIDAD_HTML, mimetype='text/html')


@bp.route('/api/calidad/dashboard')
def calidad_dashboard():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # Lotes en cuarentena
    c.execute("""SELECT COUNT(*) FROM movimientos
                 WHERE tipo='Entrada' AND (estado_lote='Cuarentena'
                 OR (estado_lote IS NULL AND lote IS NOT NULL AND lote != ''))""")
    cuarentena = c.fetchone()[0]
    # Aprobados y rechazados últimos 30d
    c.execute("""SELECT COUNT(*) FROM movimientos
                 WHERE estado_lote='Aprobado'
                 AND fecha >= date('now','-30 days')""")
    aprobados = c.fetchone()[0]
    c.execute("""SELECT COUNT(*) FROM movimientos
                 WHERE estado_lote='Rechazado'
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
    conn.close()
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


@bp.route('/api/calidad/no-conformidades', methods=['GET', 'POST'])
def handle_no_conformidades():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        desc = (d.get('descripcion') or '').strip()
        if not desc:
            conn.close(); return jsonify({'error': 'descripcion requerida'}), 400
        c.execute("""INSERT INTO no_conformidades
                     (fecha,tipo,descripcion,area,responsable,lote,codigo_mp,
                      impacto,accion_correctiva,estado,creado_por)
                     VALUES (date('now'),?,?,?,?,?,?,?,?,'Abierta',?)""",
                  (d.get('tipo','Proceso'), desc,
                   d.get('area',''), d.get('responsable',''),
                   d.get('lote',''), d.get('codigo_mp',''),
                   d.get('impacto','Baj`'), d.get('accion_correctiva',''),
                   session.get('compras_user','')))
        conn.commit(); new_id = c.lastrowid; conn.close()
        return jsonify({'id': new_id}), 201
    # GET
    c.execute("""SELECT id,fecha,tipo,descripcion,area,responsable,lote,codigo_mp,
                        impacto,accion_correctiva,estado,fecha_cierre,cerrado_por,creado_por
                 FROM no_conformidades ORDER BY id DESC LIMIT 200""")
    cols = ['id','fecha','tipo','descripcion','area','responsable','lote','codigo_mp',
            'impacto','accion_correctiva','estado','fecha_cierre','cerrado_por','creado_por']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close(); return jsonify(rows)


@bp.route('/api/calidad/no-conformidades/<int:ncid>/cerrar', methods=['POST'])
def cerrar_no_conformidad(ncid):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""UPDATE no_conformidades
                 SET estado='Cerrada', fecha_cierre=date('now'), cerrado_por=?
                 WHERE id=?""",
              (session.get('compras_user',''), ncid))
    conn.commit(); conn.close()
    return jsonify({'ok': True})


@bp.route('/api/calidad/calibraciones')
def get_calibraciones():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
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
    conn.close(); return jsonify(rows)


# ── CRONOGRAMA DEL DÍA ─────────────────────────────────────────────────────

@bp.route('/api/calidad/cronograma')
def get_cronograma():
    fecha = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
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
    conn.close()
    return jsonify({'tareas': tareas, 'registros': registros, 'fecha': fecha})


@bp.route('/api/calidad/cronograma/iniciar', methods=['POST'])
def iniciar_tarea_cron():
    d = request.get_json(silent=True) or {}
    tarea_id = d.get('tarea_id')
    fecha = d.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    hora_ahora = datetime.now().strftime('%H:%M')
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
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
    conn.commit(); conn.close()
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
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
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
                     VALUES (date('now'),'Proceso',?z,
                     'Calidad','Jefe CC','Alto',
                     ?,'Abierta',?)""",
                  ('OOS detectado en cronograma: ' + nombre_tarea,
                   d.get('observaciones',''),
                   session.get('compras_user','')))
    conn.commit(); conn.close()
    return jsonify({'ok': True})


@bp.route('/api/calidad/cronograma/resumen')
def resumen_cronograma():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
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
    conn.close()
    return jsonify({'dias': dias, 'total_tareas': total_tareas})

