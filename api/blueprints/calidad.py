# blueprints/calidad.py — extraído de index.py (Fase C)
import os
import json
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, CALIDAD_USERS
from database import get_db
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
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        desc = (d.get('descripcion') or '').strip()
        if not desc:
            return jsonify({'error': 'descripcion requerida'}), 400
        c.execute("""INSERT INTO no_conformidades
                     (fecha,tipo,descripcion,area,responsable,lote,codigo_mp,
                      impacto,accion_correctiva,estado,creado_por)
                     VALUES (date('now'),?,?,?,?,?,?,?,?,'Abierta',?)""",
                  (d.get('tipo','Proceso'), desc,
                   d.get('area',''), d.get('responsable',''),
                   d.get('lote',''), d.get('codigo_mp',''),
                   d.get('impacto','Bajo'), d.get('accion_correctiva',''),
                   session.get('compras_user','')))
        conn.commit(); new_id = c.lastrowid
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
    conn = get_db(); c = conn.cursor()
    c.execute("""UPDATE no_conformidades
                 SET estado='Cerrada', fecha_cierre=date('now'), cerrado_por=?
                 WHERE id=?""",
              (session.get('compras_user',''), ncid))
    conn.commit()
    return jsonify({'ok': True})

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
    if 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('codigo_mp') or not d.get('parametro'):
            return jsonify({'error':'codigo_mp y parametro requeridos'}), 400
        try:
            c.execute("""INSERT INTO especificaciones_mp
                (codigo_mp, parametro, unidad, valor_min, valor_max, metodo_ensayo,
                 obligatorio, tipo, farmacopea_ref, creado_por)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (d['codigo_mp'], d['parametro'], d.get('unidad',''),
                 d.get('valor_min'), d.get('valor_max'), d.get('metodo_ensayo',''),
                 1 if d.get('obligatorio', True) else 0,
                 d.get('tipo','fisicoquimico'), d.get('farmacopea_ref',''),
                 session.get('compras_user','sistema')))
            conn.commit()
            return jsonify({'ok':True, 'id':c.lastrowid}), 201
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
    if 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        d = request.json or {}
        for k in ('lote','codigo_mp','parametro','valor_obtenido'):
            if not d.get(k):
                return jsonify({'error':f'{k} requerido'}), 400

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

        c.execute("""INSERT INTO coa_resultados
            (lote, codigo_mp, material_nombre, parametro, unidad,
             valor_obtenido, valor_min_spec, valor_max_spec, conforme,
             metodo_ensayo, analista, fecha_analisis, equipo_id,
             observaciones, decision)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d['lote'], d['codigo_mp'], d.get('material_nombre',''),
             d['parametro'], unidad, d['valor_obtenido'],
             valor_min_spec, valor_max_spec, conforme, metodo,
             d.get('analista', session.get('compras_user','')),
             d.get('fecha_analisis'),
             d.get('equipo_id'), d.get('observaciones',''), decision))
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
    if 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        for k in ('producto','lote_piloto','condicion','tiempo_dias','fecha_inicio'):
            if not d.get(k):
                return jsonify({'error':f'{k} requerido'}), 400
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
             d.get('analista', session.get('compras_user','')),
             d.get('estado','Programado')))
        conn.commit()
        return jsonify({'ok':True, 'id':c.lastrowid}), 201
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
    if 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        for k in ('nc_id','tipo','descripcion'):
            if not d.get(k):
                return jsonify({'error':f'{k} requerido'}), 400
        if d['tipo'] not in ('correctiva','preventiva','contencion'):
            return jsonify({'error':'tipo debe ser correctiva/preventiva/contencion'}), 400
        c.execute("""INSERT INTO capa_acciones
            (nc_id, tipo, descripcion, responsable, fecha_compromiso, estado)
            VALUES (?,?,?,?,?,?)""",
            (int(d['nc_id']), d['tipo'], d['descripcion'],
             d.get('responsable',''), d.get('fecha_compromiso'),
             d.get('estado','Pendiente')))
        conn.commit()
        return jsonify({'ok':True, 'id':c.lastrowid}), 201
    nc_id = request.args.get('nc_id','').strip()
    if nc_id:
        c.execute("SELECT * FROM capa_acciones WHERE nc_id=? ORDER BY id ASC", (nc_id,))
    else:
        c.execute("SELECT * FROM capa_acciones ORDER BY creado_en DESC LIMIT 200")
    cols = [x[0] for x in c.description]
    return jsonify([dict(zip(cols,r)) for r in c.fetchall()])


@bp.route('/api/calidad/capa/<int:cid>', methods=['PATCH'])
def capa_update(cid):
    if 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    d = request.json or {}
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
    conn.commit()
    return jsonify({'ok':True})


# ─── AUDITORIAS ─────────────────────────────────────────────────────────────

@bp.route('/api/calidad/auditorias', methods=['GET','POST'])
def auditorias_list():
    if 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('tipo') or not d.get('ente_auditado'):
            return jsonify({'error':'tipo y ente_auditado requeridos'}), 400
        c.execute("""INSERT INTO auditorias
            (tipo, ente_auditado, fecha_planeada, auditor, alcance, estado)
            VALUES (?,?,?,?,?,?)""",
            (d['tipo'], d['ente_auditado'], d.get('fecha_planeada'),
             d.get('auditor', session.get('compras_user','')),
             d.get('alcance',''), d.get('estado','Planeada')))
        conn.commit()
        return jsonify({'ok':True, 'id':c.lastrowid}), 201
    c.execute("SELECT * FROM auditorias ORDER BY fecha_planeada DESC LIMIT 100")
    cols = [x[0] for x in c.description]
    return jsonify([dict(zip(cols,r)) for r in c.fetchall()])
