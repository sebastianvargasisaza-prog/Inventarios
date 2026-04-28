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

@bp.route('/compromisos')
def compromisos_page():
    if 'compras_user' not in session:
        return redirect('/login?next=/compromisos')
    return Response(COMPROMISOS_HTML, mimetype='text/html')

@bp.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Inventory system running'})


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

