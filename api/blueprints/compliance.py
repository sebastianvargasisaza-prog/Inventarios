"""Blueprint Compliance — Cronogramas BPM + CAPA + Hallazgos.

Sebastian (30-abr-2026): basado en correos reales — cronogramas BPM
atrasados (fumigación 20%, ducha 25%), DESV-007 cerrada por email,
"tuberías aguas + áreas rechazo" pendientes INVIMA. Modulo digital con
alertas y conexion al sistema notif in-app.
"""
from flask import Blueprint, jsonify, request, session, Response, redirect
import logging
from datetime import date, datetime, timedelta
from database import get_db
from config import ADMIN_USERS
from audit_helpers import audit_log, intentar_insert_con_retry

logger = logging.getLogger(__name__)
log = logger  # alias
bp = Blueprint('compliance', __name__)

# Roles que pueden cerrar hallazgos / aprobar CAPA
RESPONSABLES_BPM = {'sebastian','alejandro','aseguramiento.espagiria',
                     'controlcalidad.espagiria','direccion','luza.torresg',
                     'produccion.espagiria','direcciontecnica'}


def _is_responsable(user):
    u = (user or '').lower()
    return u in RESPONSABLES_BPM or u in {x.lower() for x in ADMIN_USERS}


# ─── Pagina /compliance ───────────────────────────────────────────────────
@bp.route('/compliance')
def compliance_page():
    if 'compras_user' not in session:
        return redirect('/login?next=/compliance')
    from templates_py.compliance_html import HTML
    user = session.get('compras_user', '')
    es_resp = 'true' if _is_responsable(user) else 'false'
    html = HTML.replace('{usuario}', user.capitalize()).replace('{es_responsable}', es_resp)
    return Response(html, mimetype='text/html; charset=utf-8')


# ─── CRONOGRAMAS BPM ──────────────────────────────────────────────────────
@bp.route('/api/compliance/cronogramas', methods=['GET'])
def cronogramas_listar():
    """Lista cronogramas con % cumplimiento del año en curso."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db()
    year = request.args.get('year', date.today().year)
    rows = conn.execute("""
        SELECT c.id, c.codigo, c.nombre, c.frecuencia, c.responsable,
               c.ejecuciones_year_objetivo,
               (SELECT COUNT(*) FROM cronograma_ejecuciones e
                WHERE e.cronograma_id=c.id AND e.estado='ejecutado'
                  AND strftime('%Y', e.fecha_real)=?) as ejecutadas,
               (SELECT COUNT(*) FROM cronograma_ejecuciones e
                WHERE e.cronograma_id=c.id AND e.estado='vencido'
                  AND strftime('%Y', e.fecha_planeada)=?) as vencidas,
               (SELECT COUNT(*) FROM cronograma_ejecuciones e
                WHERE e.cronograma_id=c.id AND e.estado='pendiente'
                  AND e.fecha_planeada >= date('now')) as proximas
        FROM cronogramas_bpm c
        WHERE c.activo=1
        ORDER BY c.codigo
    """, (str(year), str(year))).fetchall()
    out = []
    for r in rows:
        objetivo = r[5] or 12
        ejec = r[6] or 0
        venc = r[7] or 0
        prox = r[8] or 0
        pct = round((ejec / objetivo) * 100) if objetivo else 0
        out.append({
            'id': r[0], 'codigo': r[1], 'nombre': r[2], 'frecuencia': r[3],
            'responsable': r[4], 'objetivo': objetivo,
            'ejecutadas': ejec, 'vencidas': venc, 'proximas': prox,
            'pct_cumplimiento': pct,
            'riesgo': pct < 50,
        })
    return jsonify({'cronogramas': out, 'year': year})


@bp.route('/api/compliance/cronogramas/<int:cron_id>/ejecuciones', methods=['GET', 'POST'])
def cronograma_ejecuciones(cron_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        # Solo responsables BPM pueden agendar ejecuciones de cronograma
        if not _is_responsable(user):
            return jsonify({'error': 'Solo responsables BPM pueden agendar'}), 403
        d = request.get_json(force=True, silent=True) or {}
        fecha_planeada = (d.get('fecha_planeada') or '').strip()
        if not fecha_planeada:
            return jsonify({'error': 'fecha_planeada requerida'}), 400
        c.execute("""INSERT INTO cronograma_ejecuciones
            (cronograma_id, fecha_planeada, estado, observaciones)
            VALUES (?, ?, 'pendiente', ?)""",
            (cron_id, fecha_planeada, (d.get('observaciones') or '').strip() or None))
        ej_id = c.lastrowid
        try:
            audit_log(c, usuario=user, accion='AGENDAR_CRONOGRAMA',
                      tabla='cronograma_ejecuciones', registro_id=ej_id,
                      despues={'cronograma_id': cron_id,
                                'fecha_planeada': fecha_planeada,
                                'observaciones': (d.get('observaciones') or '')[:200]},
                      detalle=f"Agendó ejecución cronograma #{cron_id} para {fecha_planeada}")
        except Exception as e:
            log.warning('audit_log AGENDAR_CRONOGRAMA fallo: %s', e)
        conn.commit()
        return jsonify({'ok': True, 'id': ej_id}), 201

    rows = c.execute("""SELECT id, fecha_planeada, fecha_real, ejecutado_por,
                              evidencia_url, observaciones, estado, creado_en
                       FROM cronograma_ejecuciones
                       WHERE cronograma_id=?
                       ORDER BY fecha_planeada DESC LIMIT 50""", (cron_id,)).fetchall()
    cols = ['id','fecha_planeada','fecha_real','ejecutado_por',
            'evidencia_url','observaciones','estado','creado_en']
    return jsonify({'ejecuciones': [dict(zip(cols, r)) for r in rows]})


@bp.route('/api/compliance/ejecuciones/<int:ej_id>/cumplir', methods=['POST'])
def cronograma_marcar_cumplido(ej_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    # Audit zero-error 2-may-2026: solo responsables BPM pueden marcar cumplido
    # (antes cualquier compras_user marcaba un cronograma BPM como cumplido)
    if not _is_responsable(user):
        return jsonify({'error': 'Solo responsables BPM pueden marcar cumplido'}), 403
    d = request.get_json(force=True, silent=True) or {}
    conn = get_db(); c = conn.cursor()
    cur = c.execute("""UPDATE cronograma_ejecuciones
        SET estado='ejecutado', fecha_real=date('now'), ejecutado_por=?,
            evidencia_url=COALESCE(?, evidencia_url),
            observaciones=COALESCE(?, observaciones)
        WHERE id=?""", (user,
                        (d.get('evidencia_url') or '').strip() or None,
                        (d.get('observaciones') or '').strip() or None,
                        ej_id))
    # Audit log INVIMA · cumplimiento de cronograma BPM
    try:
        audit_log(c, usuario=user, accion='CRONOGRAMA_CUMPLIR',
                  tabla='cronograma_ejecuciones', registro_id=ej_id,
                  despues={'evidencia_url': (d.get('evidencia_url') or '')[:300],
                            'observaciones': (d.get('observaciones') or '')[:300]})
    except Exception as e:
        log.warning('audit_log CRONOGRAMA_CUMPLIR fallo: %s', e)
    conn.commit()
    return jsonify({'ok': True, 'actualizado': cur.rowcount > 0})


# ─── CAPA / Desviaciones ──────────────────────────────────────────────────
@bp.route('/api/compliance/capa', methods=['GET', 'POST'])
def capa_handler():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        # Audit zero-error 2-may-2026: solo responsables BPM crean capa_desviaciones
        if not _is_responsable(user):
            return jsonify({'error': 'Solo responsables BPM pueden crear desviaciones'}), 403
        d = request.get_json(force=True, silent=True) or {}
        titulo = (d.get('titulo') or '').strip()
        if not titulo:
            return jsonify({'error': 'titulo requerido'}), 400
        # fecha_objetivo default = +5 dias
        fecha_objetivo = (d.get('fecha_objetivo') or '').strip()
        if not fecha_objetivo:
            fecha_objetivo = (date.today() + timedelta(days=5)).isoformat()
        responsable = (d.get('responsable') or '').strip() or 'aseguramiento.espagiria'
        # Race-safe DESV-NNN · audit zero-error · evita IntegrityError 500 al user
        def _insert_capa():
            last = c.execute(
                "SELECT codigo FROM capa_desviaciones WHERE codigo LIKE 'DESV-%' "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
            n = 1
            if last:
                try: n = int(last[0].split('-')[-1]) + 1
                except: n = 1
            cod = f'DESV-{n:03d}'
            c.execute("""INSERT INTO capa_desviaciones
                (codigo, tipo, titulo, descripcion, producto_relacionado, lote,
                 severidad, fecha_objetivo, responsable, accion_inmediata,
                 creado_por)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (cod, (d.get('tipo') or 'desviacion'),
                 titulo, (d.get('descripcion') or '').strip() or None,
                 (d.get('producto_relacionado') or '').strip() or None,
                 (d.get('lote') or '').strip() or None,
                 (d.get('severidad') or 'media'),
                 fecha_objetivo, responsable,
                 (d.get('accion_inmediata') or '').strip() or None,
                 user))
            return cod, c.lastrowid
        try:
            codigo, new_id = intentar_insert_con_retry(_insert_capa)
        except Exception as e:
            log.exception('crear capa_desviacion fallo: %s', e)
            return jsonify({'error': 'No se pudo crear la desviación'}), 500
        # Audit log INVIMA · creación de desviación regulatoria
        try:
            audit_log(c, usuario=user, accion='CREAR_CAPA_DESV',
                      tabla='capa_desviaciones', registro_id=codigo,
                      despues={'titulo': titulo[:200],
                                'severidad': d.get('severidad','media'),
                                'lote': (d.get('lote') or '')[:100]})
        except Exception as e:
            log.warning('audit_log CREAR_CAPA_DESV fallo: %s', e)
        conn.commit()
        # Push notif al responsable
        try:
            from blueprints.notif import push_notif
            push_notif(responsable, 'capa', f'{codigo}: {titulo}',
                       body=f'Severidad {d.get("severidad","media")} · objetivo {fecha_objetivo}',
                       link='/compliance', remitente=user, importante=True)
        except Exception: pass
        return jsonify({'ok': True, 'id': new_id, 'codigo': codigo}), 201

    # GET
    estado = request.args.get('estado', '').strip()
    where = []; params = []
    if estado:
        where.append('estado=?'); params.append(estado)
    sql = """SELECT id, codigo, tipo, titulo, descripcion, producto_relacionado,
                    lote, severidad, fecha_apertura, fecha_objetivo, fecha_cierre,
                    responsable, accion_inmediata, causa_raiz, accion_correctiva,
                    accion_preventiva, evidencia_url, estado, creado_por, creado_en
             FROM capa_desviaciones"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY estado='cerrada' ASC, fecha_apertura DESC LIMIT 100"
    rows = c.execute(sql, params).fetchall()
    cols = ['id','codigo','tipo','titulo','descripcion','producto_relacionado',
            'lote','severidad','fecha_apertura','fecha_objetivo','fecha_cierre',
            'responsable','accion_inmediata','causa_raiz','accion_correctiva',
            'accion_preventiva','evidencia_url','estado','creado_por','creado_en']
    out = []
    for r in rows:
        item = dict(zip(cols, r))
        # dias desde apertura
        try:
            ap = date.fromisoformat(item['fecha_apertura'])
            item['dias_abierta'] = (date.today() - ap).days
        except Exception:
            item['dias_abierta'] = None
        out.append(item)
    return jsonify({'capa': out})


@bp.route('/api/compliance/capa/<int:cid>', methods=['PATCH'])
def capa_actualizar(cid):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if not _is_responsable(user):
        return jsonify({'error': 'Solo responsable puede actualizar'}), 403
    d = request.get_json(force=True, silent=True) or {}
    conn = get_db(); c = conn.cursor()
    # Capturar estado anterior para audit log (transiciones regulatorias)
    antes_row = c.execute(
        "SELECT codigo, estado, severidad, responsable FROM capa_desviaciones WHERE id=?",
        (cid,)).fetchone()
    if not antes_row:
        return jsonify({'error': 'CAPA no encontrada'}), 404
    antes = dict(antes_row)
    # Si va a cerrar, exigir causa_raiz registrada (INVIMA art. 11)
    nuevo_estado = d.get('estado')
    if nuevo_estado == 'cerrada':
        existing_causa = c.execute(
            "SELECT causa_raiz FROM capa_desviaciones WHERE id=?", (cid,)).fetchone()
        causa_actual = (existing_causa[0] if existing_causa else '') or ''
        causa_nueva = (d.get('causa_raiz') or '').strip()
        if not causa_actual.strip() and len(causa_nueva) < 10:
            return jsonify({'error': 'causa_raiz (≥10 chars) requerida para cerrar CAPA'}), 400
    sets = []; params = []
    for col in ('descripcion','causa_raiz','accion_correctiva','accion_preventiva',
                'evidencia_url','accion_inmediata','responsable','severidad',
                'producto_relacionado','lote','fecha_objetivo'):
        if col in d:
            sets.append(f'{col}=?'); params.append((d[col] or None) if isinstance(d[col], str) else d[col])
    if 'estado' in d:
        nuevo = d['estado']
        if nuevo not in ('abierta','en_investigacion','en_implementacion','cerrada','cancelada'):
            return jsonify({'error': 'estado invalido'}), 400
        sets.append('estado=?'); params.append(nuevo)
        if nuevo == 'cerrada':
            sets.append('fecha_cierre=?'); params.append(date.today().isoformat())
    if not sets:
        return jsonify({'error': 'nada que actualizar'}), 400
    params.append(cid)
    cur = c.execute(f"UPDATE capa_desviaciones SET {', '.join(sets)} WHERE id=?", params)
    # Audit log INVIMA · separa CERRAR_CAPA_DESV de modificaciones regulares
    accion = 'CERRAR_CAPA_DESV' if nuevo_estado == 'cerrada' else 'ACTUALIZAR_CAPA_DESV'
    try:
        audit_log(c, usuario=user, accion=accion, tabla='capa_desviaciones',
                  registro_id=cid, antes=antes,
                  despues={k: d.get(k) for k in d
                            if k in ('estado','severidad','responsable','causa_raiz',
                                     'accion_correctiva','accion_preventiva')},
                  detalle=f"{accion} {antes.get('codigo','—')} (id={cid})")
    except Exception as e:
        log.warning('audit_log %s fallo: %s', accion, e)
    conn.commit()
    return jsonify({'ok': True, 'actualizado': cur.rowcount > 0})


# ─── HALLAZGOS ─────────────────────────────────────────────────────────────
@bp.route('/api/compliance/hallazgos', methods=['GET', 'POST'])
def hallazgos_handler():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        # Audit zero-error 2-may-2026: solo responsables BPM crean hallazgos
        if not _is_responsable(user):
            return jsonify({'error': 'Solo responsables BPM pueden crear hallazgos'}), 403
        d = request.get_json(force=True, silent=True) or {}
        titulo = (d.get('titulo') or '').strip()
        origen = (d.get('origen') or 'BPM_interna').strip()
        if not titulo:
            return jsonify({'error': 'titulo requerido'}), 400
        if origen not in ('INVIMA','BPM_interna','autoinspeccion','auditoria_externa','queja_cliente','otro'):
            origen = 'otro'
        responsable = (d.get('responsable') or '').strip() or 'aseguramiento.espagiria'
        # Race-safe HLZ-XXX-NNN
        def _insert_hallazgo():
            last = c.execute(
                "SELECT codigo FROM hallazgos WHERE codigo LIKE ? ORDER BY id DESC LIMIT 1",
                (f'HLZ-{origen[:3].upper()}-%',)
            ).fetchone()
            n = 1
            if last:
                try: n = int(last[0].split('-')[-1]) + 1
                except: n = 1
            cod = f'HLZ-{origen[:3].upper()}-{n:03d}'
            c.execute("""INSERT INTO hallazgos
                (codigo, origen, titulo, descripcion, area, severidad,
                 fecha_limite, responsable, accion_propuesta, creado_por)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (cod, origen, titulo,
                 (d.get('descripcion') or '').strip() or None,
                 (d.get('area') or '').strip() or None,
                 (d.get('severidad') or 'media'),
                 (d.get('fecha_limite') or '').strip() or None,
                 responsable,
                 (d.get('accion_propuesta') or '').strip() or None,
                 user))
            return cod, c.lastrowid
        try:
            codigo, new_id = intentar_insert_con_retry(_insert_hallazgo)
        except Exception as e:
            log.exception('crear hallazgo fallo: %s', e)
            return jsonify({'error': 'No se pudo crear el hallazgo'}), 500
        # Audit log INVIMA · hallazgos son input regulatorio (ej. INVIMA, auditoría)
        try:
            audit_log(c, usuario=user, accion='CREAR_HALLAZGO',
                      tabla='hallazgos', registro_id=codigo,
                      despues={'origen': origen, 'titulo': titulo[:200],
                                'severidad': d.get('severidad','media')})
        except Exception as e:
            log.warning('audit_log CREAR_HALLAZGO fallo: %s', e)
        conn.commit()
        try:
            from blueprints.notif import push_notif
            push_notif(responsable, 'hallazgo', f'{codigo}: {titulo}',
                       body=f'Origen {origen} · severidad {d.get("severidad","media")}',
                       link='/compliance', remitente=user,
                       importante=(d.get('severidad') in ('critico','mayor')))
        except Exception: pass
        return jsonify({'ok': True, 'id': new_id, 'codigo': codigo}), 201

    estado = request.args.get('estado', '').strip()
    origen = request.args.get('origen', '').strip()
    where = []; params = []
    if estado: where.append('estado=?'); params.append(estado)
    if origen: where.append('origen=?'); params.append(origen)
    sql = """SELECT id, codigo, origen, titulo, descripcion, area, severidad,
                    fecha_deteccion, fecha_limite, fecha_cierre, responsable,
                    accion_propuesta, evidencia_cierre_url, capa_relacionada_id,
                    estado, creado_por, creado_en
             FROM hallazgos"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY estado='cerrado' ASC, severidad='critico' DESC, fecha_limite ASC NULLS LAST LIMIT 100"
    rows = c.execute(sql, params).fetchall()
    cols = ['id','codigo','origen','titulo','descripcion','area','severidad',
            'fecha_deteccion','fecha_limite','fecha_cierre','responsable',
            'accion_propuesta','evidencia_cierre_url','capa_relacionada_id',
            'estado','creado_por','creado_en']
    out = []
    for r in rows:
        item = dict(zip(cols, r))
        # dias hasta limite
        if item['fecha_limite']:
            try:
                fl = date.fromisoformat(item['fecha_limite'])
                item['dias_a_limite'] = (fl - date.today()).days
                item['vencido'] = item['dias_a_limite'] < 0 and item['estado'] != 'cerrado'
            except Exception:
                item['dias_a_limite'] = None
                item['vencido'] = False
        else:
            item['dias_a_limite'] = None
            item['vencido'] = False
        out.append(item)
    return jsonify({'hallazgos': out})


@bp.route('/api/compliance/hallazgos/<int:hid>', methods=['PATCH'])
def hallazgo_actualizar(hid):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if not _is_responsable(user):
        return jsonify({'error': 'Solo responsable puede actualizar'}), 403
    d = request.get_json(force=True, silent=True) or {}
    conn = get_db(); c = conn.cursor()
    antes_row = c.execute(
        "SELECT codigo, estado, severidad, origen, responsable FROM hallazgos WHERE id=?",
        (hid,)).fetchone()
    if not antes_row:
        return jsonify({'error': 'Hallazgo no encontrado'}), 404
    antes = dict(antes_row)
    nuevo_estado = d.get('estado')
    # Si va a cerrar un hallazgo INVIMA o crítico, exigir evidencia
    if nuevo_estado == 'cerrado':
        existing = c.execute(
            "SELECT origen, severidad, evidencia_cierre_url FROM hallazgos WHERE id=?",
            (hid,)).fetchone()
        if existing:
            origen_h, sev_h, evidencia_h = existing[0], existing[1], (existing[2] or '')
            evidencia_nueva = (d.get('evidencia_cierre_url') or '').strip()
            evidencia_final = evidencia_nueva or evidencia_h
            if (origen_h == 'INVIMA' or sev_h in ('critico','mayor')) and not evidencia_final:
                return jsonify({'error': 'evidencia_cierre_url requerida para cerrar hallazgo INVIMA/crítico'}), 400
    sets = []; params = []
    for col in ('descripcion','area','severidad','fecha_limite','responsable',
                'accion_propuesta','evidencia_cierre_url','capa_relacionada_id'):
        if col in d:
            sets.append(f'{col}=?'); params.append(d[col])
    if 'estado' in d:
        nuevo = d['estado']
        if nuevo not in ('abierto','en_proceso','cerrado','rechazado'):
            return jsonify({'error': 'estado invalido'}), 400
        sets.append('estado=?'); params.append(nuevo)
        if nuevo == 'cerrado':
            sets.append('fecha_cierre=?'); params.append(date.today().isoformat())
    if not sets:
        return jsonify({'error': 'nada que actualizar'}), 400
    params.append(hid)
    cur = c.execute(f"UPDATE hallazgos SET {', '.join(sets)} WHERE id=?", params)
    accion = 'CERRAR_HALLAZGO' if nuevo_estado == 'cerrado' else 'ACTUALIZAR_HALLAZGO'
    try:
        audit_log(c, usuario=user, accion=accion, tabla='hallazgos',
                  registro_id=hid, antes=antes,
                  despues={k: d.get(k) for k in d
                            if k in ('estado','severidad','responsable',
                                     'accion_propuesta','evidencia_cierre_url',
                                     'capa_relacionada_id')},
                  detalle=f"{accion} {antes.get('codigo','—')} (id={hid})")
    except Exception as e:
        log.warning('audit_log %s fallo: %s', accion, e)
    conn.commit()
    return jsonify({'ok': True, 'actualizado': cur.rowcount > 0})


# ─── KPIs agregados para dashboard ─────────────────────────────────────────
@bp.route('/api/compliance/kpis', methods=['GET'])
def compliance_kpis():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db()
    year = str(date.today().year)
    # Cumplimiento promedio cronogramas
    crons = conn.execute("""
        SELECT c.id, c.ejecuciones_year_objetivo,
               (SELECT COUNT(*) FROM cronograma_ejecuciones e
                WHERE e.cronograma_id=c.id AND e.estado='ejecutado'
                  AND strftime('%Y', e.fecha_real)=?)
        FROM cronogramas_bpm c WHERE c.activo=1
    """, (year,)).fetchall()
    pcts = []
    for r in crons:
        obj = r[1] or 12; ejec = r[2] or 0
        if obj: pcts.append(min(100, round(ejec*100/obj)))
    cumpl_prom = round(sum(pcts)/len(pcts)) if pcts else 0
    # CAPA abiertas / vencidas
    capa_total = conn.execute("SELECT COUNT(*) FROM capa_desviaciones WHERE estado!='cerrada' AND estado!='cancelada'").fetchone()[0]
    capa_5d = conn.execute(
        "SELECT COUNT(*) FROM capa_desviaciones WHERE estado!='cerrada' AND estado!='cancelada' "
        "AND julianday('now') - julianday(fecha_apertura) > 5"
    ).fetchone()[0]
    # Hallazgos abiertos / vencidos
    hall_total = conn.execute("SELECT COUNT(*) FROM hallazgos WHERE estado!='cerrado' AND estado!='rechazado'").fetchone()[0]
    hall_venc = conn.execute(
        "SELECT COUNT(*) FROM hallazgos WHERE estado!='cerrado' AND estado!='rechazado' "
        "AND fecha_limite < date('now')"
    ).fetchone()[0]
    hall_invima = conn.execute(
        "SELECT COUNT(*) FROM hallazgos WHERE origen='INVIMA' AND estado!='cerrado'"
    ).fetchone()[0]
    return jsonify({
        'cronogramas_cumplimiento_promedio': cumpl_prom,
        'cronogramas_total': len(crons),
        'capa_abiertas': capa_total,
        'capa_vencidas_5d': capa_5d,
        'hallazgos_abiertos': hall_total,
        'hallazgos_vencidos': hall_venc,
        'hallazgos_invima_abiertos': hall_invima,
    })
