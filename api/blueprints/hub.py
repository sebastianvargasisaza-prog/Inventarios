# blueprints/hub.py — extraído de index.py (Fase C)
import os
import json
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS
from database import get_db
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

bp = Blueprint('hub', __name__)

@bp.route('/api/hub/resumen')
def hub_resumen():
    conn = get_db(); c = conn.cursor()
    # OCs
    c.execute("SELECT estado, COUNT(*), COALESCE(SUM(valor_total),0) FROM ordenes_compra GROUP BY estado")
    oc_data = {r[0]:{'count':r[1],'valor':r[2]} for r in c.fetchall()}
    hoy = datetime.now().strftime('%Y-%m-%d')
    semana_ini = (datetime.now() - __import__('datetime').timedelta(days=7)).strftime('%Y-%m-%d')
    # Pagado esta semana
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM ordenes_compra WHERE estado='Pagada' AND fecha_pago >= ?", (semana_ini,))
    pag_semana = c.fetchone()[0] or 0
    # Por pagar (Autorizada)
    val_por_pagar = oc_data.get('Autorizada',{}).get('valor',0)
    cnt_por_pagar = oc_data.get('Autorizada',{}).get('count',0)
    val_por_autorizar = oc_data.get('Revisada',{}).get('valor',0)
    cnt_por_autorizar = oc_data.get('Revisada',{}).get('count',0)
    # Stock crítico
    c.execute("""SELECT COUNT(*) FROM (
        SELECT m.material_id, COALESCE(SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad WHEN m.tipo='Salida' THEN -m.cantidad ELSE 0 END),0) as stock,
               mp.stock_minimo FROM movimientos m
        LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
        GROUP BY m.material_id HAVING stock < COALESCE(mp.stock_minimo,0) AND COALESCE(mp.stock_minimo,0)>0
    )""")
    stock_crit = c.fetchone()[0] or 0
    # Compromisos
    c.execute("SELECT estado, prioridad, COUNT(*) FROM compromisos GROUP BY estado, prioridad")
    comp_rows = c.fetchall()
    comp_vencidos = 0
    c.execute("SELECT COUNT(*) FROM compromisos WHERE estado NOT IN ('Completado','Cancelado') AND fecha_limite != '' AND fecha_limite < ?", (hoy,))
    comp_vencidos = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM compromisos WHERE estado NOT IN ('Completado','Cancelado')")
    comp_pendientes = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM compromisos WHERE prioridad='Critico' AND estado NOT IN ('Completado','Cancelado')")
    comp_criticos = c.fetchone()[0] or 0
    # Clientes activos
    c.execute("SELECT COUNT(*) FROM clientes WHERE activo=1")
    clientes_activos = c.fetchone()[0] or 0
    return jsonify({
        'ocs': {'por_autorizar': cnt_por_autorizar, 'por_pagar': cnt_por_pagar,
                'valor_autorizar': val_por_autorizar, 'valor_pagar': val_por_pagar},
        'stock_critico': stock_crit,
        'pagado_semana': pag_semana,
        'compromisos': {'pendientes': comp_pendientes, 'vencidos': comp_vencidos, 'criticos': comp_criticos},
        'clientes': clientes_activos
    })

@bp.route('/api/hub/alertas')
def hub_alertas():
    conn = get_db(); c = conn.cursor()
    hoy = datetime.now().strftime('%Y-%m-%d')
    alertas = []
    # OCs Revisadas sin autorizar (> 2 dias)
    hace2 = (datetime.now() - __import__('datetime').timedelta(days=2)).isoformat()
    c.execute("SELECT numero_oc, proveedor, valor_total, fecha FROM ordenes_compra WHERE estado='Revisada' ORDER BY fecha ASC LIMIT 10")
    for row in c.fetchall():
        num, prov, val, fecha = row
        dias = max(0, (datetime.now() - datetime.fromisoformat(fecha[:19])).days) if fecha else 0
        nivel = 'critico' if dias >= 3 else 'atencion'
        alertas.append({'nivel':nivel,'tipo':'oc_autorizar','titulo':'OC pendiente de autorizar',
            'detalle':f'{num} — {prov or "?"} ${val:,.0f} — {dias}d sin autorizar',
            'accion':'/compras','oc_num':num,'valor':val})
    # OCs Autorizadas con fecha vencida
    c.execute("SELECT numero_oc, proveedor, valor_total, fecha_entrega_est FROM ordenes_compra WHERE estado='Autorizada' AND fecha_entrega_est != '' AND fecha_entrega_est < ? ORDER BY fecha_entrega_est ASC", (hoy,))
    for row in c.fetchall():
        num, prov, val, fecha = row
        alertas.append({'nivel':'critico','tipo':'pago_vencido','titulo':'Pago vencido',
            'detalle':f'{num} — {prov or "?"} ${val:,.0f} — vencio {fecha}',
            'accion':'/compras','oc_num':num,'valor':val})
    # OCs Autorizadas proximas a vencer (3 dias)
    en3 = (datetime.now() + __import__('datetime').timedelta(days=3)).strftime('%Y-%m-%d')
    c.execute("SELECT numero_oc, proveedor, valor_total, fecha_entrega_est FROM ordenes_compra WHERE estado='Autorizada' AND fecha_entrega_est BETWEEN ? AND ? ORDER BY fecha_entrega_est ASC", (hoy, en3))
    for row in c.fetchall():
        num, prov, val, fecha = row
        alertas.append({'nivel':'atencion','tipo':'pago_proximo','titulo':'Pago proximo',
            'detalle':f'{num} — {prov or "?"} ${val:,.0f} — vence {fecha}',
            'accion':'/compras','oc_num':num,'valor':val})
    # Compromisos vencidos
    c.execute("SELECT descripcion, responsable, fecha_limite, prioridad FROM compromisos WHERE estado NOT IN ('Completado','Cancelado') AND fecha_limite != '' AND fecha_limite < ? ORDER BY prioridad DESC, fecha_limite ASC LIMIT 5", (hoy,))
    for row in c.fetchall():
        desc, resp, fecha, prior = row
        nivel = 'critico' if prior == 'Critico' else 'atencion'
        alertas.append({'nivel':nivel,'tipo':'compromiso_vencido','titulo':'Compromiso vencido',
            'detalle':f'{desc[:60]} — {resp} — vencio {fecha}',
            'accion':'/compromisos'})
    # Lotes proximos a vencer o ya vencidos
    hoy_dt = datetime.now()
    en60 = (hoy_dt + timedelta(days=60)).strftime('%Y-%m-%d')
    hoy_str = hoy_dt.strftime('%Y-%m-%d')
    try:
        c.execute("""SELECT material_nombre, lote, fecha_vencimiento, material_id
                     FROM movimientos
                     WHERE tipo='Entrada' AND fecha_vencimiento IS NOT NULL AND fecha_vencimiento != ''
                     AND fecha_vencimiento <= ?
                     GROUP BY material_id, lote
                     ORDER BY fecha_vencimiento ASC LIMIT 8""", (en60,))
        for row in c.fetchall():
            nombre, lote, fv, mid = row
            try:
                fv_clean = (fv or '')[:10]
                fv_dt = datetime.strptime(fv_clean, '%Y-%m-%d')
                dias = (fv_dt - hoy_dt).days
            except Exception:
                continue
            nivel = 'critico' if dias <= 15 else 'atencion'
            if dias < 0:
                msg = f'VENCIDO hace {abs(dias)} dias'
            elif dias == 0:
                msg = 'VENCE HOY'
            else:
                msg = f'Vence en {dias} dias ({fv_clean})'
            alertas.append({'nivel': nivel, 'tipo': 'lote_vencimiento',
                'titulo': 'Lote proximo a vencer',
                'detalle': f'{nombre} — Lote {lote or "sin lote"} — {msg}',
                'accion': '/inventarios'})
    except Exception:
        pass
    # Sort: critico first
    orden = {'critico':0,'atencion':1,'info':2}
    alertas.sort(key=lambda x: orden.get(x['nivel'],2))
    resumen = {'critico': sum(1 for a in alertas if a['nivel']=='critico'),
               'atencion': sum(1 for a in alertas if a['nivel']=='atencion'),
               'info': sum(1 for a in alertas if a['nivel']=='info')}
    return jsonify({'alertas': alertas[:15], 'resumen': resumen})

@bp.route('/api/compromisos', methods=['GET','POST'])
def handle_compromisos():
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('descripcion'): return jsonify({'error':'Descripcion requerida'}),400
        c.execute("""INSERT INTO compromisos (descripcion,responsable,area,fecha_limite,estado,prioridad,origen,empresa,fecha_creacion)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (d['descripcion'],d.get('responsable',''),d.get('area',''),d.get('fecha_limite',''),
                   d.get('estado','Pendiente'),d.get('prioridad','Normal'),d.get('origen',''),
                   d.get('empresa','Espagiria'),datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        return jsonify({'ok':True,'id':c.lastrowid}), 201
    estado_f = request.args.get('estado','')
    empresa_f = request.args.get('empresa','')
    sql = "SELECT id,descripcion,responsable,area,fecha_limite,estado,prioridad,origen,empresa,fecha_creacion,notas FROM compromisos"
    clauses=[]; params=[]
    if estado_f and estado_f != 'Todos': clauses.append("estado=?"); params.append(estado_f)
    if empresa_f: clauses.append("empresa=?"); params.append(empresa_f)
    if clauses: sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY CASE prioridad WHEN 'Critico' THEN 0 WHEN 'Alta' THEN 1 WHEN 'Normal' THEN 2 ELSE 3 END, fecha_limite ASC"
    c.execute(sql, params)
    cols = ['id','descripcion','responsable','area','fecha_limite','estado','prioridad','origen','empresa','fecha_creacion','notas']
    rows = [dict(zip(cols,r)) for r in c.fetchall()]
    return jsonify({'compromisos': rows})

@bp.route('/api/compromisos/<int:cid>', methods=['PATCH'])
def update_compromiso(cid):
    d = request.json or {}
    conn = get_db(); c = conn.cursor()
    sets=[]; params=[]
    for field in ['estado','notas','fecha_limite','responsable','prioridad']:
        if field in d: sets.append(f"{field}=?"); params.append(d[field])
    if d.get('estado') == 'Completado':
        sets.append("fecha_cierre=?"); params.append(datetime.now().strftime('%Y-%m-%d'))
    if not sets: return jsonify({'error':'Nada que actualizar'}),400
    params.append(cid)
    c.execute(f"UPDATE compromisos SET {', '.join(sets)} WHERE id=?", params)
    conn.commit()
    return jsonify({'ok':True})

@bp.route('/api/compromisos/migrar-a-tareas', methods=['POST'])
def migrar_compromisos_a_tareas():
    """Migra compromisos pendientes a tareas_internas (Comunicacion).

    Decision Sebastian: el modulo /compromisos esta deprecado, todo va a
    /comunicacion (tareas con RACI). Este endpoint copia los compromisos
    activos a tareas_internas con origen='compromisos_legacy', preservando
    el responsable original como rol 'R' en RACI.

    Idempotente: detecta tareas ya migradas via origen+origen_ref para
    no duplicar.

    Solo admin.
    """
    u = session.get('compras_user', '')
    if u not in ADMIN_USERS:
        return jsonify({'error': 'Solo admins'}), 403
    conn = get_db(); c = conn.cursor()

    # Solo migrar los activos (no los Completados / Cancelados)
    pendientes = c.execute("""
        SELECT id, descripcion, responsable, area, fecha_limite,
               estado, prioridad, origen, empresa, fecha_creacion
        FROM compromisos
        WHERE estado NOT IN ('Completado', 'Cancelado', 'Cerrado')
        ORDER BY id ASC
    """).fetchall()

    migrados = 0
    skipped = 0
    for r in pendientes:
        cid = r[0]
        # Idempotencia: si ya existe tarea con origen_ref=str(cid), skip
        ya = c.execute("""SELECT 1 FROM tareas_internas
                          WHERE origen='compromisos_legacy' AND origen_ref=?
                          LIMIT 1""", (str(cid),)).fetchone()
        if ya:
            skipped += 1
            continue
        # Mapeo prioridad legacy -> tareas
        prio = (r[6] or 'Media').strip()
        if prio in ('Critico', 'Critica'): prio = 'Alta'
        elif prio in ('Normal', 'Media'): prio = 'Media'
        elif prio not in ('Alta', 'Baja'): prio = 'Media'
        c.execute("""INSERT INTO tareas_internas
                     (titulo, descripcion, estado, prioridad, area, origen,
                      origen_ref, fecha_compromiso, fecha_creacion, creado_por)
                     VALUES (?,?,?,?,?,?,?,?,?,?)""",
                  ((r[1] or 'Compromiso')[:200],   # titulo (descripcion truncada)
                   r[1] or '',                     # descripcion completa
                   'Asignada',                     # estado
                   prio,                           # prioridad mapeada
                   r[3] or '',                     # area
                   'compromisos_legacy',           # origen
                   str(cid),                       # origen_ref
                   r[4] or None,                   # fecha_compromiso
                   r[9] or '',                     # fecha_creacion
                   u))
        new_tid = c.lastrowid
        # Si tenia responsable, asignar como R
        responsable = (r[2] or '').strip().lower()
        if responsable:
            try:
                c.execute("""INSERT OR IGNORE INTO tareas_raci
                             (tarea_id, usuario, rol, asignado_por)
                             VALUES (?,?,?,?)""",
                          (new_tid, responsable, 'R', u))
            except Exception:
                pass
        migrados += 1

    conn.commit()
    return jsonify({
        'ok': True,
        'migrados': migrados,
        'ya_migrados_skipped': skipped,
        'mensaje': f'{migrados} compromisos copiados a Tareas (Comunicación). '
                   f'{skipped} ya estaban migrados.',
    })


@bp.route('/compromisos')
def compromisos_page():
    """DEPRECATED — redirige a /comunicacion (tareas RACI son el reemplazo).

    Decision Sebastian 2026-04-28: el modulo /compromisos es legacy. La
    funcionalidad real esta en /comunicacion con RACI, chat, actas y
    quejas IA. Mantenemos esta ruta solo para no romper bookmarks
    pero redirige.
    """
    if 'compras_user' not in session:
        return redirect('/login?next=/comunicacion')
    return redirect('/comunicacion')

@bp.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Inventory system running'})


@bp.route('/manifest.json')
def pwa_manifest():
    """Sirve el manifest PWA desde la raiz (algunos browsers lo requieren).
    Tambien accesible en /static/manifest.json."""
    import os as _os
    base = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    path = _os.path.join(base, 'static', 'manifest.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return Response(f.read(), mimetype='application/manifest+json')
    except Exception:
        return jsonify({'error': 'manifest no encontrado'}), 404


@bp.route('/sw.js')
def pwa_service_worker():
    """Sirve service worker desde raiz (scope obliga raiz)."""
    import os as _os
    base = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    path = _os.path.join(base, 'static', 'sw.js')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            resp = Response(f.read(), mimetype='application/javascript')
            resp.headers['Service-Worker-Allowed'] = '/'
            resp.headers['Cache-Control'] = 'no-cache'
            return resp
    except Exception:
        return Response('', status=404)


@bp.route('/tesoreria')
def tesoreria_page():
    """Tesoreria — UI unificada de Finanzas + Contabilidad.
    Decision Sebastian 2026-04-28: 'que esa fusion la podamos llamar
    tesoreria, suena lindo'.
    Las URLs viejas /financiero y /contabilidad siguen funcionando.
    """
    if 'compras_user' not in session:
        return redirect('/login?next=/tesoreria')
    u = session.get('compras_user', '')
    # Acceso: ADMIN_USERS + CONTADORA_USERS (Mayra, Catalina)
    if u not in ADMIN_USERS and u not in CONTADORA_USERS:
        return jsonify({'error': 'Sin acceso a Tesoreria'}), 403
    from templates_py.tesoreria_html import HTML
    return Response(HTML, mimetype='text/html')


# ─── CENTRO DE NOTIFICACIONES UNIFICADO ────────────────────────────────────

@bp.route('/api/notificaciones/centro')
def centro_notificaciones():
    """Agrega alertas criticas de TODOS los modulos en una sola lista
    priorizada por severidad. Vista unica de "que urge hoy" para CEO/admins.

    Cruza:
      - Inventario: MPs en cero, lotes vencen <7d
      - Compras: OCs pendientes de pago, solicitudes sin atender
      - Marketing: influencers "toca pagar", quejas Alta/Critica sin resolver
      - Calidad: NCs estancadas >30d, calibraciones vencidas, lotes en cuarentena
      - Comunicacion: tareas vencidas asignadas a mi, mensajes sin leer
      - Compromisos comite: reincidentes >14d sin avance
      - Financiero: shopify pendiente sync >30 pedidos
    """
    u = session.get('compras_user', '')
    if not u:
        return jsonify({'error': 'No autenticado'}), 401

    conn = get_db(); c = conn.cursor()
    alertas = []

    # ── Inventario: MPs en stock cero ──
    try:
        for r in c.execute("""
            SELECT m.codigo_mp, m.nombre_inci as nombre,
                   COALESCE(SUM(CASE WHEN mov.tipo IN ('Entrada','Ajuste +') THEN mov.cantidad
                                     WHEN mov.tipo IN ('Salida','Ajuste -') THEN -mov.cantidad
                                     ELSE 0 END), 0) as stock
            FROM maestro_mps m
            LEFT JOIN movimientos mov ON mov.material_id = m.codigo_mp
            WHERE m.activo=1 AND m.stock_minimo > 0
            GROUP BY m.codigo_mp
            HAVING stock <= 0
            LIMIT 15
        """).fetchall():
            alertas.append({
                'severidad': 'alta',
                'modulo': 'inventario',
                'icono': '📦',
                'titulo': f'MP en cero: {r["nombre"]}',
                'detalle': f'Codigo {r["codigo_mp"]} sin stock',
                'link': '/inventarios',
                'accion': 'Crear solicitud de compra urgente',
            })
    except Exception:
        pass

    # ── Inventario: lotes vencen en <=7 dias ──
    try:
        hoy = datetime.now().date().isoformat()
        d7 = (datetime.now() + timedelta(days=7)).date().isoformat()
        for r in c.execute("""
            SELECT material_nombre, lote, fecha_vencimiento, cantidad
            FROM movimientos
            WHERE tipo='Entrada' AND fecha_vencimiento BETWEEN ? AND ?
            LIMIT 10
        """, (hoy, d7)).fetchall():
            alertas.append({
                'severidad': 'alta',
                'modulo': 'inventario',
                'icono': '📅',
                'titulo': f'Lote {r["lote"]} vence en <=7 días',
                'detalle': f'{r["material_nombre"]} ({r["cantidad"]} g) — {r["fecha_vencimiento"]}',
                'link': '/inventarios',
                'accion': 'Usar primero o transferir',
            })
    except Exception:
        pass

    # ── Compras: OCs autorizadas sin pagar >7 dias ──
    if u in ADMIN_USERS or u in CONTADORA_USERS:
        try:
            for r in c.execute("""
                SELECT numero_oc, proveedor, valor_total, fecha
                FROM ordenes_compra
                WHERE estado IN ('Autorizada','Aprobada')
                  AND fecha < date('now','-7 day')
                ORDER BY fecha ASC LIMIT 10
            """).fetchall():
                alertas.append({
                    'severidad': 'media',
                    'modulo': 'compras',
                    'icono': '💰',
                    'titulo': f'OC {r["numero_oc"]} sin pagar >7 días',
                    'detalle': f'{r["proveedor"] or "-"} — ${(r["valor_total"] or 0):,.0f}',
                    'link': '/compras',
                    'accion': 'Pagar o cancelar',
                })
        except Exception:
            pass

    # ── Calidad: NCs abiertas >30 días (estancadas) ──
    try:
        for r in c.execute("""
            SELECT id, descripcion, fecha, responsable
            FROM no_conformidades
            WHERE estado='Abierta' AND fecha < date('now','-30 day')
            ORDER BY fecha ASC LIMIT 10
        """).fetchall():
            alertas.append({
                'severidad': 'media',
                'modulo': 'calidad',
                'icono': '🔬',
                'titulo': f'NC abierta hace >30 días',
                'detalle': (r['descripcion'] or '')[:100],
                'link': '/calidad',
                'accion': f'Cerrar — resp: {r["responsable"]}',
            })
    except Exception:
        pass

    # ── Calidad: calibraciones vencidas ──
    try:
        n_calib = c.execute("""SELECT COUNT(*) FROM calibraciones
                               WHERE fecha_proxima < date('now') AND estado != 'OK'
                            """).fetchone()[0]
        if n_calib:
            alertas.append({
                'severidad': 'media',
                'modulo': 'calidad',
                'icono': '🔧',
                'titulo': f'{n_calib} calibracion(es) vencida(s)',
                'detalle': 'Equipos con calibracion fuera de fecha',
                'link': '/calidad',
                'accion': 'Programar recalibracion',
            })
    except Exception:
        pass

    # ── Marketing: influencers "toca pagar" (cumplio ciclo, sin solicitud) ──
    try:
        # Reusa la logica del modulo: ultimo pago + ciclo
        rows = c.execute("""
            SELECT mi.id, mi.nombre, mi.ciclo_pago,
                   MAX(p.fecha) as ultimo_pago_fecha
            FROM marketing_influencers mi
            LEFT JOIN pagos_influencers p ON p.influencer_id=mi.id AND p.estado='Pagada'
            WHERE mi.estado='Activo'
              AND mi.ciclo_pago IN ('Mensual','Bimensual','Trimestral')
            GROUP BY mi.id
            HAVING ultimo_pago_fecha IS NOT NULL
        """).fetchall()
        for r in rows:
            ciclo_dias = {'Mensual': 30, 'Bimensual': 60, 'Trimestral': 90}.get(r['ciclo_pago'], 30)
            try:
                fecha_ult = datetime.strptime((r['ultimo_pago_fecha'] or '')[:10], "%Y-%m-%d")
                dias_desde = (datetime.now() - fecha_ult).days
                if dias_desde >= ciclo_dias:
                    # Verificar que no tenga solicitud activa
                    pend = c.execute("""SELECT 1 FROM pagos_influencers
                                        WHERE influencer_id=? AND estado='Pendiente' LIMIT 1""",
                                     (r['id'],)).fetchone()
                    if not pend:
                        alertas.append({
                            'severidad': 'media',
                            'modulo': 'marketing',
                            'icono': '⏰',
                            'titulo': f'Toca pagar a {r["nombre"]}',
                            'detalle': f'Hace {dias_desde}d del último pago — ciclo {r["ciclo_pago"]}',
                            'link': '/marketing',
                            'accion': 'Crear solicitud pago',
                        })
            except Exception:
                pass
    except Exception:
        pass

    # ── Comunicacion: tareas vencidas asignadas al usuario ──
    try:
        for r in c.execute("""
            SELECT t.id, t.titulo, t.fecha_compromiso, t.area
            FROM tareas_internas t
            JOIN tareas_raci r ON r.tarea_id = t.id
            WHERE r.usuario=? AND r.rol IN ('R','A')
              AND t.estado NOT IN ('Hecha','Cancelada')
              AND t.fecha_compromiso IS NOT NULL
              AND t.fecha_compromiso < date('now')
            ORDER BY t.fecha_compromiso ASC LIMIT 10
        """, (u,)).fetchall():
            alertas.append({
                'severidad': 'alta',
                'modulo': 'comunicacion',
                'icono': '📋',
                'titulo': f'Tarea vencida: {r["titulo"][:60]}',
                'detalle': f'Comprometida {r["fecha_compromiso"]} — area: {r["area"]}',
                'link': '/comunicacion',
                'accion': 'Completar o renegociar',
            })
    except Exception:
        pass

    # ── Comunicacion: mensajes sin leer ──
    try:
        n_msg = c.execute("""SELECT COUNT(*) FROM mensajes_internos
                             WHERE a_usuario=? AND leido_at IS NULL""",
                          (u,)).fetchone()[0]
        if n_msg > 0:
            alertas.append({
                'severidad': 'info',
                'modulo': 'comunicacion',
                'icono': '💬',
                'titulo': f'{n_msg} mensaje(s) sin leer',
                'detalle': 'Tienes mensajes pendientes en chat interno',
                'link': '/comunicacion',
                'accion': 'Revisar bandeja',
            })
    except Exception:
        pass

    # ── Comunicacion: quejas Alta/Critica sin resolver (admins) ──
    if u in ADMIN_USERS:
        try:
            for r in c.execute("""
                SELECT id, de_usuario, severidad_ia, contexto, fecha
                FROM quejas_internas
                WHERE estado IN ('Pendiente','Analizada','Escalada')
                  AND severidad_ia IN ('Alta','Critica')
                ORDER BY
                  CASE severidad_ia WHEN 'Critica' THEN 1 ELSE 2 END,
                  fecha ASC
                LIMIT 5
            """).fetchall():
                alertas.append({
                    'severidad': 'alta' if r['severidad_ia'] == 'Critica' else 'media',
                    'modulo': 'comunicacion',
                    'icono': '🚨',
                    'titulo': f'Queja {r["severidad_ia"]}: {r["de_usuario"]}',
                    'detalle': (r['contexto'] or '')[:100],
                    'link': '/comunicacion',
                    'accion': 'Revisar y resolver',
                })
        except Exception:
            pass

    # ── Comunicacion: compromisos comite reincidentes >14d ──
    try:
        for r in c.execute("""
            SELECT t.id, t.titulo,
                   (SELECT GROUP_CONCAT(usuario,',') FROM tareas_raci
                    WHERE tarea_id=t.id AND rol='R') as resp,
                   (julianday('now') - julianday(t.fecha_creacion)) as dias
            FROM tareas_internas t
            WHERE t.estado NOT IN ('Hecha','Cancelada')
              AND t.origen='comite'
              AND t.fecha_creacion < date('now','-14 day')
            ORDER BY t.fecha_creacion ASC LIMIT 5
        """).fetchall():
            alertas.append({
                'severidad': 'media',
                'modulo': 'comunicacion',
                'icono': '♻️',
                'titulo': f'Reincidente comite: {r["titulo"][:60]}',
                'detalle': f'Sin avance hace {int(r["dias"])} días — resp: {r["resp"] or "-"}',
                'link': '/comunicacion',
                'accion': 'Escalar o reasignar',
            })
    except Exception:
        pass

    # ── Tecnica: SGDs (SOPs) que requieren revision en <30 dias ──
    try:
        for r in c.execute("""
            SELECT id, codigo, nombre, fecha_proxima_revision, responsable_revision,
                   julianday(fecha_proxima_revision) - julianday('now') as dias
            FROM documentos_sgd
            WHERE estado='Vigente'
              AND COALESCE(fecha_proxima_revision,'') != ''
              AND fecha_proxima_revision <= date('now','+30 day')
            ORDER BY fecha_proxima_revision ASC LIMIT 10
        """).fetchall():
            dias = int(r['dias']) if r['dias'] is not None else 0
            sev = 'alta' if dias <= 0 else ('media' if dias <= 14 else 'info')
            alertas.append({
                'severidad': sev,
                'modulo': 'tecnica',
                'icono': '📜',
                'titulo': f'SGD {"VENCIDO" if dias <= 0 else "vence pronto"}: {r["codigo"]}',
                'detalle': f'{r["nombre"]} — revisión en {dias} días — resp: {r["responsable_revision"] or "-"}',
                'link': '/tecnica',
                'accion': 'Revisar y marcar revisado',
            })
    except Exception:
        pass

    # ── Financiero: Shopify pendiente sync (>30 pedidos) ──
    if u in ADMIN_USERS or u in CONTADORA_USERS:
        try:
            n_pend = c.execute("""SELECT COUNT(*) FROM animus_shopify_orders
                                  WHERE (flujo_synced=0 OR flujo_synced IS NULL)
                                    AND LOWER(COALESCE(estado_pago,'')) IN
                                        ('paid','pagado','complete','captured','partially_paid')
                               """).fetchone()[0]
            if n_pend > 30:
                alertas.append({
                    'severidad': 'info',
                    'modulo': 'financiero',
                    'icono': '🛍️',
                    'titulo': f'{n_pend} pedidos Shopify sin sincronizar',
                    'detalle': 'Hay ingresos no reflejados en flujo_ingresos',
                    'link': '/financiero',
                    'accion': 'Click "Sincronizar ahora"',
                })
        except Exception:
            pass

    # Agrupar y ordenar por severidad
    sev_orden = {'alta': 1, 'media': 2, 'info': 3}
    alertas.sort(key=lambda a: (sev_orden.get(a['severidad'], 9), a['modulo']))

    return jsonify({
        'alertas': alertas,
        'total': len(alertas),
        'por_severidad': {
            'alta':  sum(1 for a in alertas if a['severidad'] == 'alta'),
            'media': sum(1 for a in alertas if a['severidad'] == 'media'),
            'info':  sum(1 for a in alertas if a['severidad'] == 'info'),
        },
    })


@bp.route('/hoy')
@bp.route('/centro')  # alias legacy — sigue funcionando para no romper bookmarks
def centro_operaciones_page():
    """Pagina /hoy — vista ejecutiva del DIA (tiempo real operativo).

    Renombrado de /centro a /hoy para hacer explicito el rol:
    - /hoy        = que pasa AHORA (caja hoy, ventas hoy, tareas vencidas)
    - /financiero = transaccional + P&L + Working Capital + Runway (Mayra)
    - /gerencia   = metas YTD estrategicas, alertas cronicas, churn, SGSST

    /centro sigue funcionando como alias para no romper accesos guardados.
    """
    if 'compras_user' not in session:
        return redirect('/login?next=/hoy')
    u = session.get('compras_user', '')
    if u not in ADMIN_USERS:
        return jsonify({'error': 'Solo admins'}), 403
    from templates_py.centro_operaciones_html import HTML
    return Response(HTML.replace('{usuario}', u), mimetype='text/html')


@bp.route('/api/centro/operaciones')
def centro_operaciones_data():
    """Dashboard ejecutivo unificado — TODO lo que el CEO necesita ver de un
    vistazo en lugar de entrar a 8 modulos. Combina:
      • Caja: ingresos/egresos del dia + saldo acumulado mes
      • Produccion: lotes en curso, MPs criticos, alertas calidad
      • Comercial: ventas Shopify hoy/mes, pedidos B2B activos, AR/AP aging
      • Pagos: OCs por pagar + facturas con saldo + nomina pendiente
      • Equipo: tareas vencidas todas las areas, mensajes admin, quejas IA
      • Marketing: campanas activas, influencers a pagar, ROI mes
    Solo admins (sebastian + alejandro).
    """
    u = session.get('compras_user', '')
    if not u:
        return jsonify({'error': 'No autenticado'}), 401
    if u not in ADMIN_USERS:
        return jsonify({'error': 'Solo admins'}), 403

    conn = get_db(); c = conn.cursor()
    out = {'generado_en': datetime.now().isoformat()}

    # ─── CAJA / FINANZAS ─────────────────────────────────────────────────
    try:
        hoy = datetime.now().strftime('%Y-%m-%d')
        mes = datetime.now().strftime('%Y-%m')
        ing_hoy = c.execute("SELECT COALESCE(SUM(monto),0) FROM flujo_ingresos WHERE fecha=?", (hoy,)).fetchone()[0]
        egr_hoy = c.execute("SELECT COALESCE(SUM(monto),0) FROM flujo_egresos WHERE fecha=?", (hoy,)).fetchone()[0]
        ing_mes = c.execute("SELECT COALESCE(SUM(monto),0) FROM flujo_ingresos WHERE periodo=?", (mes,)).fetchone()[0]
        egr_mes = c.execute("SELECT COALESCE(SUM(monto),0) FROM flujo_egresos WHERE periodo=?", (mes,)).fetchone()[0]
        out['caja'] = {
            'ingresos_hoy':  ing_hoy or 0,
            'egresos_hoy':   egr_hoy or 0,
            'neto_hoy':      (ing_hoy or 0) - (egr_hoy or 0),
            'ingresos_mes':  ing_mes or 0,
            'egresos_mes':   egr_mes or 0,
            'neto_mes':      (ing_mes or 0) - (egr_mes or 0),
        }
    except Exception:
        out['caja'] = {}

    # ─── PRODUCCION ──────────────────────────────────────────────────────
    try:
        prods_mes = c.execute("""
            SELECT COUNT(*) as lotes, COALESCE(SUM(cantidad),0) as kg
            FROM producciones
            WHERE strftime('%Y-%m',fecha)=strftime('%Y-%m','now')
              AND estado != 'Cancelada'
        """).fetchone()
        prods_proximos = c.execute("""
            SELECT COUNT(*) FROM produccion_programada
            WHERE estado='Programada' AND fecha_planeada >= date('now')
              AND fecha_planeada <= date('now','+30 day')
        """).fetchone()
        out['produccion'] = {
            'lotes_mes': prods_mes[0] if prods_mes else 0,
            'kg_mes': float(prods_mes[1]) if prods_mes else 0,
            'programados_30d': prods_proximos[0] if prods_proximos else 0,
        }
    except Exception:
        out['produccion'] = {}

    # ─── INVENTARIO ──────────────────────────────────────────────────────
    try:
        n_cero = c.execute("""
            SELECT COUNT(*) FROM (
                SELECT m.codigo_mp,
                       COALESCE(SUM(CASE WHEN mov.tipo IN ('Entrada','Ajuste +') THEN mov.cantidad
                                         WHEN mov.tipo IN ('Salida','Ajuste -') THEN -mov.cantidad
                                         ELSE 0 END),0) as stock
                FROM maestro_mps m
                LEFT JOIN movimientos mov ON mov.material_id=m.codigo_mp
                WHERE m.activo=1 AND m.stock_minimo>0
                GROUP BY m.codigo_mp HAVING stock<=0
            )
        """).fetchone()[0]
        n_bajo = c.execute("""
            SELECT COUNT(*) FROM (
                SELECT m.codigo_mp, m.stock_minimo,
                       COALESCE(SUM(CASE WHEN mov.tipo IN ('Entrada','Ajuste +') THEN mov.cantidad
                                         WHEN mov.tipo IN ('Salida','Ajuste -') THEN -mov.cantidad
                                         ELSE 0 END),0) as stock
                FROM maestro_mps m
                LEFT JOIN movimientos mov ON mov.material_id=m.codigo_mp
                WHERE m.activo=1 AND m.stock_minimo>0
                GROUP BY m.codigo_mp
                HAVING stock<m.stock_minimo AND stock>0
            )
        """).fetchone()[0]
        venc7 = c.execute("""SELECT COUNT(*) FROM movimientos
                             WHERE tipo='Entrada' AND fecha_vencimiento BETWEEN
                                   date('now') AND date('now','+7 day')""").fetchone()[0]
        out['inventario'] = {
            'mps_cero': n_cero, 'mps_bajo': n_bajo, 'lotes_vencen_7d': venc7,
        }
    except Exception:
        out['inventario'] = {}

    # ─── COMERCIAL: SHOPIFY + PEDIDOS B2B ────────────────────────────────
    try:
        sh_hoy = c.execute("""SELECT COUNT(*), COALESCE(SUM(total),0)
                              FROM animus_shopify_orders WHERE creado_en LIKE ?
                           """, (hoy + '%',)).fetchone()
        sh_mes = c.execute("""SELECT COUNT(*), COALESCE(SUM(total),0)
                              FROM animus_shopify_orders WHERE creado_en LIKE ?
                           """, (mes + '%',)).fetchone()
        n_pedidos_b2b = c.execute("""SELECT COUNT(*) FROM pedidos
                                     WHERE estado IN ('Pendiente','En produccion','Listo')
                                  """).fetchone()[0]
        out['comercial'] = {
            'shopify_hoy_count': sh_hoy[0] if sh_hoy else 0,
            'shopify_hoy_total': sh_hoy[1] if sh_hoy else 0,
            'shopify_mes_count': sh_mes[0] if sh_mes else 0,
            'shopify_mes_total': sh_mes[1] if sh_mes else 0,
            'pedidos_b2b_activos': n_pedidos_b2b,
        }
    except Exception:
        out['comercial'] = {}

    # ─── PAGOS: OCs + facturas + nomina ──────────────────────────────────
    try:
        oc_pendientes = c.execute("""
            SELECT COUNT(*), COALESCE(SUM(valor_total),0)
            FROM ordenes_compra
            WHERE estado IN ('Borrador','Pendiente','Revisada','Aprobada','Autorizada','Recibida','Parcial')
        """).fetchone()
        facturas_saldo = c.execute("""
            SELECT COUNT(*), COALESCE(SUM(total - COALESCE(
                (SELECT SUM(monto) FROM facturas_pagos WHERE numero_factura=facturas.numero_factura),0
            )),0) as saldo
            FROM facturas
            WHERE estado IN ('Emitida','Parcial')
        """).fetchone()
        out['pagos'] = {
            'ocs_pendientes_count': oc_pendientes[0] if oc_pendientes else 0,
            'ocs_pendientes_valor': oc_pendientes[1] if oc_pendientes else 0,
            'facturas_pendientes_count': facturas_saldo[0] if facturas_saldo else 0,
            'facturas_saldo_total':      facturas_saldo[1] if facturas_saldo else 0,
        }
    except Exception:
        out['pagos'] = {}

    # ─── EQUIPO ──────────────────────────────────────────────────────────
    try:
        tareas_venc_total = c.execute("""
            SELECT COUNT(*) FROM tareas_internas
            WHERE estado NOT IN ('Hecha','Cancelada')
              AND fecha_compromiso IS NOT NULL
              AND fecha_compromiso < date('now')
        """).fetchone()[0]
        msg_admin = c.execute("""SELECT COUNT(*) FROM mensajes_internos
                                 WHERE a_usuario=? AND leido_at IS NULL""",
                              (u,)).fetchone()[0]
        quejas_alta = c.execute("""SELECT COUNT(*) FROM quejas_internas
                                   WHERE estado IN ('Pendiente','Analizada','Escalada')
                                     AND severidad_ia IN ('Alta','Critica')""").fetchone()[0]
        ncs = c.execute("SELECT COUNT(*) FROM no_conformidades WHERE estado='Abierta'").fetchone()[0]
        out['equipo'] = {
            'tareas_vencidas_total': tareas_venc_total,
            'mensajes_sin_leer': msg_admin,
            'quejas_alta_critica': quejas_alta,
            'ncs_abiertas': ncs,
        }
    except Exception:
        out['equipo'] = {}

    # ─── MARKETING ───────────────────────────────────────────────────────
    try:
        camp_act = c.execute("""SELECT COUNT(*) FROM marketing_campanas
                                WHERE estado='Activa'""").fetchone()[0]
        # Influencers que tocan pagar (cumplio ciclo, sin solicitud)
        toca_pagar = 0
        try:
            rows = c.execute("""
                SELECT mi.id, mi.ciclo_pago, MAX(p.fecha) as ultimo
                FROM marketing_influencers mi
                LEFT JOIN pagos_influencers p ON p.influencer_id=mi.id AND p.estado='Pagada'
                WHERE mi.estado='Activo' AND mi.ciclo_pago IN ('Mensual','Bimensual','Trimestral')
                GROUP BY mi.id HAVING ultimo IS NOT NULL
            """).fetchall()
            for r in rows:
                ciclo = {'Mensual':30,'Bimensual':60,'Trimestral':90}.get(r['ciclo_pago'],30)
                try:
                    fult = datetime.strptime((r['ultimo'] or '')[:10], '%Y-%m-%d')
                    if (datetime.now() - fult).days >= ciclo:
                        pend = c.execute("""SELECT 1 FROM pagos_influencers
                                            WHERE influencer_id=? AND estado='Pendiente'
                                            LIMIT 1""", (r['id'],)).fetchone()
                        if not pend: toca_pagar += 1
                except Exception:
                    pass
        except Exception:
            pass
        out['marketing'] = {
            'campanas_activas': camp_act,
            'influencers_toca_pagar': toca_pagar,
        }
    except Exception:
        out['marketing'] = {}

    # ─── DIRECCION TECNICA ──────────────────────────────────────────────
    try:
        out['tecnica'] = {
            'formulas_vigentes': c.execute("SELECT COUNT(*) FROM formulas_maestras WHERE estado='Vigente'").fetchone()[0] or 0,
            'invima_vigentes':   c.execute("SELECT COUNT(*) FROM registros_invima WHERE estado='Vigente'").fetchone()[0] or 0,
            'sgd_vencen_30d':    c.execute("""SELECT COUNT(*) FROM documentos_sgd
                                             WHERE estado='Vigente'
                                               AND COALESCE(fecha_proxima_revision,'') != ''
                                               AND fecha_proxima_revision <= date('now','+30 day')""").fetchone()[0] or 0,
        }
    except Exception:
        out['tecnica'] = {}

    # ─── RRHH ────────────────────────────────────────────────────────────
    try:
        out['rrhh'] = {
            'empleados_activos': c.execute("SELECT COUNT(*) FROM empleados WHERE estado='Activo'").fetchone()[0] or 0,
            'ausencias_pendientes': c.execute("SELECT COUNT(*) FROM ausencias WHERE estado='Pendiente'").fetchone()[0] or 0,
        }
    except Exception:
        out['rrhh'] = {}

    # ─── ACTIVIDAD ULTIMA HORA ───────────────────────────────────────────
    try:
        actividad = []
        # Movimientos
        for r in c.execute("""SELECT 'movimiento' as tipo, fecha, material_nombre as titulo, tipo as detalle
                              FROM movimientos WHERE fecha >= datetime('now','-1 hour')
                              ORDER BY fecha DESC LIMIT 5""").fetchall():
            actividad.append(dict(r))
        # OCs nuevas
        for r in c.execute("""SELECT 'oc' as tipo, fecha, numero_oc as titulo, proveedor as detalle
                              FROM ordenes_compra WHERE fecha >= datetime('now','-1 hour')
                              ORDER BY fecha DESC LIMIT 5""").fetchall():
            actividad.append(dict(r))
        # Tareas creadas
        for r in c.execute("""SELECT 'tarea' as tipo, fecha_creacion as fecha, titulo, area as detalle
                              FROM tareas_internas WHERE fecha_creacion >= datetime('now','-1 hour')
                              ORDER BY fecha_creacion DESC LIMIT 5""").fetchall():
            actividad.append(dict(r))
        actividad.sort(key=lambda x: x.get('fecha','') or '', reverse=True)
        out['actividad_reciente'] = actividad[:15]
    except Exception:
        out['actividad_reciente'] = []

    return jsonify(out)


@bp.route('/api/ia/analizar-semana', methods=['POST'])
def ia_analizar_semana():
    """IA agente CEO: analiza el reporte semanal con Claude y devuelve
    insights, decisiones sugeridas y riesgos.

    Pre-requisito: env var ANTHROPIC_API_KEY configurada en Render.
    """
    u = session.get('compras_user', '')
    if u not in ADMIN_USERS:
        return jsonify({'error': 'Solo admins'}), 403

    # Reusar el reporte semanal como contexto
    import json as _json
    import urllib.request as _urlreq
    import os as _os

    api_key = _os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        # Intentar leer de animus_config
        try:
            conn_cfg = get_db()
            row = conn_cfg.execute("SELECT valor FROM animus_config WHERE clave='anthropic_api_key'").fetchone()
            if row:
                api_key = row[0]
        except Exception:
            pass

    if not api_key:
        return jsonify({'error': 'ANTHROPIC_API_KEY no configurada'}), 500

    # Datos: recolectar reporte semanal inline
    conn = get_db(); c = conn.cursor()
    datos = {}
    try:
        datos['caja_semana_neta'] = c.execute("""
            SELECT (SELECT COALESCE(SUM(monto),0) FROM flujo_ingresos WHERE fecha >= date('now','-7 day'))
                 - (SELECT COALESCE(SUM(monto),0) FROM flujo_egresos WHERE fecha >= date('now','-7 day'))
        """).fetchone()[0]
        datos['ocs_creadas'] = c.execute("SELECT COUNT(*) FROM ordenes_compra WHERE fecha >= date('now','-7 day')").fetchone()[0]
        datos['shopify_pedidos'] = c.execute("SELECT COUNT(*) FROM animus_shopify_orders WHERE creado_en >= datetime('now','-7 day')").fetchone()[0]
        datos['ncs_abiertas'] = c.execute("SELECT COUNT(*) FROM no_conformidades WHERE estado='Abierta'").fetchone()[0]
        datos['tareas_vencidas'] = c.execute("""SELECT COUNT(*) FROM tareas_internas
                                                WHERE estado NOT IN ('Hecha','Cancelada')
                                                  AND fecha_compromiso < date('now')""").fetchone()[0]
        datos['mps_cero'] = c.execute("""SELECT COUNT(*) FROM (
            SELECT m.codigo_mp, COALESCE(SUM(CASE WHEN mov.tipo IN ('Entrada','Ajuste +') THEN mov.cantidad
                                                  WHEN mov.tipo IN ('Salida','Ajuste -') THEN -mov.cantidad ELSE 0 END),0) as stock
            FROM maestro_mps m LEFT JOIN movimientos mov ON mov.material_id=m.codigo_mp
            WHERE m.activo=1 AND m.stock_minimo>0 GROUP BY m.codigo_mp HAVING stock<=0)""").fetchone()[0]
    except Exception as _e:
        datos['error_recoleccion'] = str(_e)

    prompt = (
        "Eres CFO+COO virtual de HHA Group (holding cosmetico colombiano: "
        "Espagiria manufactura + ANIMUS Lab marca DTC). Analiza la semana "
        "y devuelve en formato JSON con estas claves:\n"
        '{"diagnostico": "1 parrafo objetivo de como va la empresa esta semana",\n'
        ' "alertas_criticas": ["lista de 2-4 cosas que requieren accion inmediata"],\n'
        ' "decisiones_sugeridas": ["lista de 3-5 acciones especificas para el CEO esta semana"],\n'
        ' "metricas_destacadas": "1-2 lineas sobre KPIs clave",\n'
        ' "calificacion_semana": "Excelente|Buena|Regular|Mala|Critica"}\n\n'
        "Datos:\n" + _json.dumps(datos, ensure_ascii=False, indent=2)
    )

    payload = _json.dumps({
        'model': 'claude-haiku-4-5-20251001',
        'max_tokens': 600,
        'messages': [{'role': 'user', 'content': prompt}]
    }).encode('utf-8')

    try:
        req = _urlreq.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={'x-api-key': api_key,
                     'anthropic-version': '2023-06-01',
                     'content-type': 'application/json'},
            method='POST')
        with _urlreq.urlopen(req, timeout=30) as resp:
            data = _json.loads(resp.read().decode('utf-8'))
            text = data['content'][0]['text']
            # Extraer JSON de la respuesta
            import re as _re
            m = _re.search(r'\{[\s\S]+\}', text)
            if m:
                analisis = _json.loads(m.group(0))
                return jsonify({'ok': True, 'datos': datos, 'analisis': analisis})
            return jsonify({'ok': True, 'datos': datos, 'analisis_raw': text})
    except Exception as e:
        return jsonify({'error': f'IA no disponible: {e}', 'datos': datos}), 500


@bp.route('/api/reporte/semanal-ceo')
def reporte_semanal_ceo():
    """Reporte semanal para el CEO — JSON con todo lo que cierra la semana.

    Diseñado para enviar via email cada lunes 8am o consultar bajo demanda.
    Cubre: caja semana, ventas Shopify, OCs creadas, NCs, tareas completadas,
    influencers pagados, alertas pendientes.
    """
    u = session.get('compras_user', '')
    if u not in ADMIN_USERS:
        return jsonify({'error': 'Solo admins'}), 403

    conn = get_db(); c = conn.cursor()
    out = {
        'periodo': {
            'desde': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            'hasta': datetime.now().strftime('%Y-%m-%d'),
        },
    }

    try:
        ing = c.execute("""SELECT COALESCE(SUM(monto),0) FROM flujo_ingresos
                           WHERE fecha >= date('now','-7 day')""").fetchone()[0]
        egr = c.execute("""SELECT COALESCE(SUM(monto),0) FROM flujo_egresos
                           WHERE fecha >= date('now','-7 day')""").fetchone()[0]
        out['caja_semana'] = {'ingresos': ing, 'egresos': egr, 'neto': ing - egr}
    except Exception:
        out['caja_semana'] = {}

    try:
        sh = c.execute("""SELECT COUNT(*), COALESCE(SUM(total),0)
                          FROM animus_shopify_orders
                          WHERE creado_en >= datetime('now','-7 day')""").fetchone()
        out['shopify_semana'] = {'pedidos': sh[0] if sh else 0,
                                 'total': sh[1] if sh else 0}
    except Exception:
        out['shopify_semana'] = {}

    try:
        out['ocs_creadas'] = c.execute("""SELECT COUNT(*) FROM ordenes_compra
                                         WHERE fecha >= date('now','-7 day')""").fetchone()[0]
        out['ocs_pagadas'] = c.execute("""SELECT COUNT(*), COALESCE(SUM(valor_total),0)
                                          FROM ordenes_compra
                                          WHERE fecha_pago >= date('now','-7 day')""").fetchone()
        out['ocs_pagadas'] = {'count': out['ocs_pagadas'][0] if out['ocs_pagadas'] else 0,
                              'valor': out['ocs_pagadas'][1] if out['ocs_pagadas'] else 0}
    except Exception:
        out['ocs_creadas'] = 0
        out['ocs_pagadas'] = {}

    try:
        out['ncs_nuevas'] = c.execute("""SELECT COUNT(*) FROM no_conformidades
                                         WHERE fecha >= date('now','-7 day')""").fetchone()[0]
        out['ncs_cerradas'] = c.execute("""SELECT COUNT(*) FROM no_conformidades
                                           WHERE fecha_cierre >= date('now','-7 day')""").fetchone()[0]
    except Exception:
        out['ncs_nuevas'] = 0
        out['ncs_cerradas'] = 0

    try:
        out['producciones_semana'] = c.execute("""SELECT COUNT(*), COALESCE(SUM(cantidad),0)
                                                  FROM producciones
                                                  WHERE fecha >= date('now','-7 day')""").fetchone()
        out['producciones_semana'] = {'lotes': out['producciones_semana'][0],
                                      'kg': out['producciones_semana'][1]/1000.0}
    except Exception:
        out['producciones_semana'] = {}

    try:
        out['tareas_completadas'] = c.execute("""SELECT COUNT(*) FROM tareas_internas
                                                 WHERE fecha_completada >= date('now','-7 day')""").fetchone()[0]
        out['tareas_creadas'] = c.execute("""SELECT COUNT(*) FROM tareas_internas
                                             WHERE fecha_creacion >= date('now','-7 day')""").fetchone()[0]
        out['tareas_vencidas_pendientes'] = c.execute("""SELECT COUNT(*) FROM tareas_internas
                                                         WHERE estado NOT IN ('Hecha','Cancelada')
                                                           AND fecha_compromiso < date('now')""").fetchone()[0]
    except Exception:
        out['tareas_completadas'] = out['tareas_creadas'] = out['tareas_vencidas_pendientes'] = 0

    try:
        inf_pagados = c.execute("""SELECT COUNT(*), COALESCE(SUM(valor),0)
                                   FROM pagos_influencers
                                   WHERE fecha >= date('now','-7 day')
                                     AND estado='Pagada'""").fetchone()
        out['influencers_pagados'] = {'count': inf_pagados[0] if inf_pagados else 0,
                                      'total': inf_pagados[1] if inf_pagados else 0}
    except Exception:
        out['influencers_pagados'] = {}

    return jsonify(out)


@bp.route('/api/marketing/roi-campanas')
def roi_marketing_campanas():
    """ROI por campaña activa: spend vs revenue atribuible.

    Cruza marketing_campanas.presupuesto con ventas Shopify cuyas
    discount_codes corresponden a influencers de la campaña.
    """
    u = session.get('compras_user', '')
    if not u:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    try:
        rows = c.execute("""
            SELECT mc.id, mc.nombre, mc.estado,
                   COALESCE(mc.presupuesto, 0) as presupuesto,
                   mc.fecha_inicio, mc.fecha_fin,
                   (SELECT COUNT(DISTINCT influencer_id)
                    FROM marketing_campana_influencer
                    WHERE campana_id=mc.id) as n_influencers,
                   (SELECT COALESCE(SUM(valor),0)
                    FROM pagos_influencers pi
                    JOIN marketing_campana_influencer ci
                      ON ci.influencer_id=pi.influencer_id
                    WHERE ci.campana_id=mc.id AND pi.estado='Pagada') as spend_real,
                   (SELECT COALESCE(SUM(so.total),0)
                    FROM animus_shopify_orders so
                    JOIN marketing_influencers mi
                      ON mi.discount_code != ''
                         AND so.discount_codes LIKE '%'||mi.discount_code||'%'
                    JOIN marketing_campana_influencer ci ON ci.influencer_id=mi.id
                    WHERE ci.campana_id=mc.id) as revenue_atribuido
            FROM marketing_campanas mc
            ORDER BY mc.fecha_inicio DESC
            LIMIT 50
        """).fetchall()
        cols = [x[0] for x in c.description]
        campanas = []
        for r in rows:
            d = dict(zip(cols, r))
            spend = d.get('spend_real', 0) or d.get('presupuesto', 0)
            rev = d.get('revenue_atribuido', 0) or 0
            d['roi_pct'] = round(((rev - spend) / spend * 100), 1) if spend > 0 else None
            d['roas'] = round(rev / spend, 2) if spend > 0 else None
            campanas.append(d)
        return jsonify({'campanas': campanas})
    except Exception as e:
        return jsonify({'error': str(e), 'campanas': []})


@bp.route('/api/notificaciones/count')
def centro_count():
    """Contador rapido para mostrar badge en la campana sin recalcular todo.
    Solo cuenta alertas alta+media. Pull cada N min desde el frontend."""
    u = session.get('compras_user', '')
    if not u:
        return jsonify({'count': 0})
    # Reusa centro_notificaciones para no duplicar logica
    resp = centro_notificaciones()
    if isinstance(resp, tuple):
        return resp
    data = resp.get_json()
    high_med = data['por_severidad']['alta'] + data['por_severidad']['media']
    return jsonify({'count': high_med, 'total': data['total']})

