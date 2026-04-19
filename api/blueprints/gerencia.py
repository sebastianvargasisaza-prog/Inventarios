# blueprints/gerencia.py — extraído de index.py (Fase C)
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

bp = Blueprint('gerencia', __name__)


@bp.route('/gerencia')
def gerencia_page():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return redirect(url_for('core.login'))
    return Response(HUB_HTML, mimetype='text/html')

@bp.route('/gerencia-financiero')
def gerencia_financiero_page():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return redirect(url_for('core.login'))
    return Response(GERENCIA_HTML, mimetype='text/html')

@bp.route('/api/gerencia/kpis')
def gerencia_kpis():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM maestro_mps m LEFT JOIN (SELECT material_id,SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as s FROM movimientos GROUP BY material_id) st ON m.codigo_mp=st.material_id WHERE m.activo=1 AND m.stock_minimo>0 AND COALESCE(st.s,0)<m.stock_minimo")
    mps_bajo_minimo = c.fetchone()[0] or 0
    try:
        c.execute("SELECT COUNT(*) FROM maestro_mee WHERE estado='Activo' AND stock_actual < stock_minimo AND stock_minimo > 0")
        mee_bajo_minimo = c.fetchone()[0] or 0
    except Exception:
        mee_bajo_minimo = 0
    c.execute("SELECT COUNT(*) FROM movimientos WHERE tipo='Entrada' AND fecha_vencimiento IS NOT NULL AND fecha_vencimiento!='' AND fecha_vencimiento<=date('now','+30 days') AND fecha_vencimiento>=date('now')")
    lotes_vence_30 = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM movimientos WHERE tipo='Entrada' AND fecha_vencimiento IS NOT NULL AND fecha_vencimiento!='' AND fecha_vencimiento<=date('now','+60 days') AND fecha_vencimiento>=date('now','+30 days')")
    lotes_vence_60 = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM producciones WHERE fecha>=date('now','start of month')")
    prod_mes = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM ordenes_compra WHERE estado IN ('Pendiente','Aprobada','Enviada')")
    ocs_pendientes = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(unidades_disponible),0) FROM stock_pt WHERE estado='Disponible'")
    uds_pt = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM pedidos WHERE estado IN ('Confirmado','En preparacion')")
    pedidos_activos = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(DISTINCT sku) FROM stock_pt WHERE unidades_disponible>0 AND estado='Disponible'")
    skus_stock = c.fetchone()[0] or 0
    c.execute("SELECT MAX(fecha) FROM pedidos WHERE cliente_id=(SELECT id FROM clientes WHERE codigo='CLI-002' LIMIT 1)")
    ult_fm = c.fetchone()[0]; dias_fm = None
    if ult_fm:
        from datetime import date as _d
        try: dt = datetime.fromisoformat(ult_fm[:10]); dias_fm = (_d.today() - dt.date()).days
        except: pass
    c.execute("SELECT periodo,saldo_caja,ingresos_animus,ingresos_maquila,notas,fecha FROM gerencia_inputs ORDER BY periodo DESC LIMIT 1")
    row = c.fetchone()
    cols_inp = ['periodo','saldo_caja','ingresos_animus','ingresos_maquila','notas','fecha']
    inputs_manuales = dict(zip(cols_inp, row)) if row else {}
    conn.close()
    semaforos = {
        'mps': 'rojo' if mps_bajo_minimo > 5 else ('amarillo' if mps_bajo_minimo > 0 else 'verde'),
        'mee': 'rojo' if mee_bajo_minimo > 3 else ('amarillo' if mee_bajo_minimo > 0 else 'verde'),
        'vencimientos': 'rojo' if lotes_vence_30 > 0 else ('amarillo' if lotes_vence_60 > 0 else 'verde'),
        'pt': 'rojo' if uds_pt < 100 else ('amarillo' if uds_pt < 500 else 'verde'),
        'pedidos': 'amarillo' if pedidos_activos > 0 else 'verde',
    }
    return jsonify({'espagiria': {'mps_bajo_minimo': mps_bajo_minimo, 'mee_bajo_minimo': mee_bajo_minimo,
                                   'lotes_vence_30': lotes_vence_30,
                                   'lotes_vence_60': lotes_vence_60, 'prod_mes': prod_mes, 'ocs_pendientes': ocs_pendientes},
                    'animus': {'uds_pt': uds_pt, 'pedidos_activos': pedidos_activos, 'skus_stock': skus_stock, 'dias_desde_fm': dias_fm},
                    'inputs_manuales': inputs_manuales, 'semaforos': semaforos})

@bp.route('/api/gerencia/flujo-operacional')
def gerencia_flujo_operacional():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    from datetime import date
    today = date.today()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # OCs en tránsito (Autorizada, sin recepción)
    c.execute("""SELECT oc.numero_oc, oc.proveedor, oc.fecha, oc.valor_total
                 FROM ordenes_compra oc
                 WHERE oc.estado = 'Autorizada'
                 AND (oc.fecha_recepcion IS NULL OR oc.fecha_recepcion = '')
                 ORDER BY oc.fecha ASC LIMIT 20""")
    oc_cols = ['numero_oc','proveedor','fecha','valor_total']
    ocs_transito = []
    for r in c.fetchall():
        row = dict(zip(oc_cols, r))
        try:
            fd = date.fromisoformat(str(r[2])[:10])
            row['dias_transito'] = (today - fd).days
        except Exception:
            row['dias_transito'] = 0
        ocs_transito.append(row)
    # Recepciones con discrepancias
    c.execute("""SELECT numero_oc, proveedor, fecha_recepcion
                 FROM ordenes_compra
                 WHERE tiene_discrepancias = 1
                 ORDER BY fecha_recepcion DESC LIMIT 10""")
    recepciones_disc = [{'numero_oc': r[0], 'proveedor': r[1], 'fecha': r[2]} for r in c.fetchall()]
    # Pedidos listos para despachar
    c.execute("""SELECT p.numero, cl.nombre as cliente, p.fecha, p.valor_total, p.estado
                 FROM pedidos p LEFT JOIN clientes cl ON p.cliente_id=cl.id
                 WHERE p.estado IN ('Confirmado','En preparacion','En Produccion','Aprobado','Listo')
                 ORDER BY p.fecha ASC LIMIT 20""")
    ped_cols = ['numero','cliente','fecha','valor_total','estado']
    pedidos_listos = [dict(zip(ped_cols, r)) for r in c.fetchall()]
    # Despachos recientes (last 10)
    c.execute("""SELECT d.numero, cl.nombre as cliente, d.fecha, d.numero_pedido, d.estado
                 FROM despachos d LEFT JOIN clientes cl ON d.cliente_id=cl.id
                 ORDER BY d.fecha DESC LIMIT 10""")
    dsp_cols = ['numero','cliente','fecha','numero_pedido','estado']
    despachos_recientes = [dict(zip(dsp_cols, r)) for r in c.fetchall()]
    conn.close()
    return jsonify({
        'ocs_transito': ocs_transito,
        'recepciones_disc': recepciones_disc,
        'pedidos_listos': pedidos_listos,
        'despachos_recientes': despachos_recientes
    })

@bp.route('/api/admin/security-log')
def admin_security_log():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'Solo admins'}), 401
    limit  = min(int(request.args.get('limit', 200)), 500)
    event  = request.args.get('event', '')
    conn   = sqlite3.connect(DB_PATH); c = conn.cursor()
    if event:
        c.execute('SELECT * FROM security_events WHERE event=? ORDER BY id DESC LIMIT ?', (event, limit))
    else:
        c.execute('SELECT * FROM security_events ORDER BY id DESC LIMIT ?', (limit,))
    cols = ['id','ts','event','username','ip','user_agent','details']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    # Summary counts
    c.execute('SELECT event, COUNT(*) FROM security_events GROUP BY event')
    summary = {r[0]: r[1] for r in c.fetchall()}
    conn.close()
    return jsonify({'events': rows, 'summary': summary})

@bp.route('/api/admin/generate-hash', methods=['POST'])
def admin_generate_hash():
    """Utility: generate a PBKDF2 hash for a plaintext password.
    Use this to pre-hash passwords before storing them in env vars.
    POST {password: 'xxx'} -> {hash: 'pbkdf2:...'}
    """
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'Solo admins'}), 401
    d = request.get_json() or {}
    pw = d.get('password', '')
    if not pw:
        return jsonify({'error': 'Falta password'}), 400
    from werkzeug.security import generate_password_hash
    h = generate_password_hash(pw, method='pbkdf2:sha256', salt_length=16)
    return jsonify({'hash': h, 'note': 'Guarda este hash en la env var correspondiente'})

@bp.route('/api/gerencia/dashboard-extra')
def gerencia_dashboard_extra():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    from datetime import date, timedelta
    today    = date.today()
    mes_str  = today.strftime('%Y-%m')
    year_str = today.strftime('%Y')
    cutoff7  = (today - timedelta(days=7)).isoformat()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()

    # Ingresos del mes desde transacciones reales
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM pedidos "
              "WHERE fecha LIKE ? AND estado NOT IN ('Cancelado')"
              " AND (empresa='ANIMUS' OR empresa IS NULL OR empresa='')",
              (mes_str+'%',))
    ing_animus = c.fetchone()[0] or 0
    try:
        c.execute("SELECT COALESCE(SUM(precio_lote),0) FROM maquila_ordenes "
                  "WHERE fecha_orden LIKE ? AND estado NOT IN ('Cotizacion','Cancelada')",
                  (mes_str+'%',))
        ing_maquila = c.fetchone()[0] or 0
    except Exception:
        ing_maquila = 0
    ingresos_mes = {'animus': ing_animus, 'maquila': ing_maquila, 'total': ing_animus + ing_maquila}

    # AR — cuentas por cobrar
    c.execute("SELECT COALESCE(SUM(valor_total),0), COUNT(*) FROM pedidos "
              "WHERE estado NOT IN ('Cancelado','Despachado') AND valor_total > 0")
    ar_row = c.fetchone()
    ar_total, ar_count = (ar_row[0] or 0), (ar_row[1] or 0)
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM pedidos "
              "WHERE estado NOT IN ('Cancelado','Despachado') "
              "AND valor_total > 0 AND fecha <= ?",
              ((today - timedelta(days=30)).isoformat(),))
    ar_v30 = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM pedidos "
              "WHERE estado NOT IN ('Cancelado','Despachado') "
              "AND valor_total > 0 AND fecha <= ?",
              ((today - timedelta(days=60)).isoformat(),))
    ar_v60 = c.fetchone()[0] or 0
    ar = {'total': ar_total, 'count': ar_count, 'vencido_30': ar_v30, 'vencido_60': ar_v60}

    # AP — cuentas por pagar
    c.execute("SELECT COALESCE(SUM(valor_total),0), COUNT(*) FROM ordenes_compra "
              "WHERE estado IN ('Autorizada','Recibida','Parcial') "
              "AND (pagado_por IS NULL OR pagado_por='')")
    ap_row = c.fetchone()
    ap_total, ap_count = (ap_row[0] or 0), (ap_row[1] or 0)
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM ordenes_compra "
              "WHERE estado IN ('Autorizada','Recibida','Parcial') "
              "AND (pagado_por IS NULL OR pagado_por='') AND fecha <= ?",
              ((today - timedelta(days=30)).isoformat(),))
    ap_v30 = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM ordenes_compra "
              "WHERE estado IN ('Autorizada','Recibida','Parcial') "
              "AND (pagado_por IS NULL OR pagado_por='') AND fecha <= ?",
              ((today - timedelta(days=60)).isoformat(),))
    ap_v60 = c.fetchone()[0] or 0
    ap = {'total': ap_total, 'count': ap_count, 'vencido_30': ap_v30, 'vencido_60': ap_v60}

    # Maquila pipeline activo
    try:
        c.execute("SELECT numero, cliente_nombre, producto, precio_lote, estado "
                  "FROM maquila_ordenes "
                  "WHERE estado NOT IN ('Cotizacion','Cancelada','Entregada') "
                  "ORDER BY fecha_orden DESC LIMIT 10")
        maquila_pipeline = [{'numero': r[0], 'cliente_nombre': r[1],
                              'producto': r[2], 'precio_lote': r[3],
                              'estado': r[4]} for r in c.fetchall()]
    except Exception:
        maquila_pipeline = []

    # Stock critico — MPs con stock < stock_minimo
    c.execute("""
        SELECT m.codigo_mp,
               COALESCE(m.nombre_comercial, m.nombre_inci,'') as nombre,
               m.stock_minimo,
               COALESCE(SUM(CASE WHEN mv.tipo='Entrada' THEN mv.cantidad
                                 WHEN mv.tipo='Salida'  THEN -mv.cantidad
                                 ELSE 0 END), 0) as stock_actual
        FROM maestro_mps m
        LEFT JOIN movimientos mv ON m.codigo_mp = mv.material_id
        WHERE m.activo=1 AND m.stock_minimo > 0
        GROUP BY m.codigo_mp
        HAVING stock_actual < m.stock_minimo
        ORDER BY (stock_actual / m.stock_minimo) ASC
        LIMIT 15
    """)
    stock_critico = [{'codigo_mp': r[0], 'nombre': r[1],
                       'stock_minimo': r[2], 'stock_actual': max(r[3], 0)}
                     for r in c.fetchall()]

    # SGSST — proximos vencimientos (60 dias)
    cutoff_sgsst = (today + timedelta(days=60)).isoformat()
    try:
        c.execute("""
            SELECT descripcion, proximo_vencimiento, responsable, estado
            FROM sgsst_items
            WHERE proximo_vencimiento IS NOT NULL
              AND proximo_vencimiento != ''
              AND proximo_vencimiento <= ?
              AND estado != 'Cumplido'
            ORDER BY proximo_vencimiento ASC LIMIT 8
        """, (cutoff_sgsst,))
        sgsst_rows = c.fetchall()
        sgsst_proximos = []
        for r in sgsst_rows:
            try:
                venc = date.fromisoformat(str(r[1])[:10])
                dias = (venc - today).days
            except Exception:
                dias = 999
            sgsst_proximos.append({'descripcion': r[0], 'proximo_vencimiento': r[1],
                                   'responsable': r[2], 'estado': r[3], 'dias_restantes': dias})
    except Exception:
        sgsst_proximos = []

    # Security summary — last 7 days
    try:
        c.execute("SELECT COUNT(*) FROM security_events WHERE event='login_success' AND ts >= ?",
                  (cutoff7+'T00:00:00Z',))
        succ7 = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM security_events WHERE event='login_failure' AND ts >= ?",
                  (cutoff7+'T00:00:00Z',))
        fail7 = c.fetchone()[0] or 0
        c.execute("SELECT ts FROM security_events ORDER BY id DESC LIMIT 1")
        last_ev = c.fetchone()
        last_event_ts = last_ev[0] if last_ev else None
        security = {'success_7d': succ7, 'fail_7d': fail7, 'last_event': last_event_ts}
    except Exception:
        security = {'success_7d': 0, 'fail_7d': 0, 'last_event': None}

    conn.close()
    return jsonify({
        'ingresos_mes': ingresos_mes,
        'ar': ar, 'ap': ap,
        'maquila_pipeline': maquila_pipeline,
        'stock_critico': stock_critico,
        'sgsst_proximos': sgsst_proximos,
        'security': security,
    })
@bp.route('/api/admin/cleanup-test-data', methods=['POST'])
def admin_cleanup_test_data():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'Solo admins'}), 401
    d = request.get_json() or {}
    if not d.get('confirm'):
        return jsonify({'error': 'Enviar confirm:true para confirmar'}), 400
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    deleted = {}
    # Test OCs from audit
    test_oc_nums = ['OC-2026-0002','OC-2026-0003']
    for num in test_oc_nums:
        c.execute("DELETE FROM ordenes_compra_items WHERE numero_oc=?", (num,))
        c.execute("DELETE FROM ordenes_compra WHERE numero_oc=? AND proveedor LIKE '%test%' OR numero_oc=?", (num, num))
    deleted['ocs'] = len(test_oc_nums)
    # Test solicitudes
    c.execute("DELETE FROM solicitudes WHERE numero='SOL-2026-0001' OR proveedor LIKE '%test%' OR proveedor LIKE '%prueba%'")
    deleted['solicitudes'] = c.rowcount
    # Test pedidos
    c.execute("DELETE FROM pedidos_items WHERE numero_pedido='PED-2026-0001'")
    c.execute("DELETE FROM pedidos WHERE numero='PED-2026-0001'")
    deleted['pedidos'] = c.rowcount
    # Test lotes
    c.execute("DELETE FROM lotes WHERE codigo_lote LIKE '%AUDIT%' OR codigo_lote LIKE '%TEST%' OR codigo_lote LIKE '%-test-%'")
    deleted['lotes'] = c.rowcount
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'deleted': deleted, 'message': 'Test data cleaned up'})

@bp.route('/api/gerencia/input-manual', methods=['POST'])
def gerencia_input_manual():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.json or {}
    periodo = d.get('periodo', datetime.now().strftime('%Y-%m'))
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""INSERT INTO gerencia_inputs (periodo,saldo_caja,ingresos_animus,ingresos_maquila,notas,fecha)
                    VALUES (?,?,?,?,?,datetime('now'))
                    ON CONFLICT(periodo) DO UPDATE SET saldo_caja=excluded.saldo_caja,
                    ingresos_animus=excluded.ingresos_animus, ingresos_maquila=excluded.ingresos_maquila,
                    notas=excluded.notas, fecha=excluded.fecha""",
                 (periodo, float(d.get('saldo_caja',0)), float(d.get('ingresos_animus',0)),
                  float(d.get('ingresos_maquila',0)), d.get('notas','')))
    conn.commit(); conn.close()
    return jsonify({'message': f'Inputs de {periodo} guardados'})


# ─── MÓDULO FINANCIERO — Rutas ────────────────────────────────
