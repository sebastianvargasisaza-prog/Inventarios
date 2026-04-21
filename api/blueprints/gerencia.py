# blueprints/gerencia.py — extraído de index.py (Fase C)
import os
import re
import io
import zipfile
import xml.etree.ElementTree as ET
import json
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, FINANZAS_ACCESS
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
    u = session.get('compras_user', '')
    if not u or u not in FINANZAS_ACCESS:
        return redirect(url_for('core.login'))
    return Response(GERENCIA_HTML, mimetype='text/html')

@bp.route('/api/gerencia/kpis')
def gerencia_kpis():
    if 'compras_user' not in session or session.get('compras_user','') not in FINANZAS_ACCESS:
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
    try:
        c.execute("SELECT COUNT(*) FROM solicitudes_compra WHERE estado='Pendiente'")
        sol_pendientes = c.fetchone()[0] or 0
    except: sol_pendientes = 0
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
        'solicitudes': 'amarillo' if sol_pendientes > 0 else 'verde',
    }
    return jsonify({'espagiria': {'mps_bajo_minimo': mps_bajo_minimo, 'mee_bajo_minimo': mee_bajo_minimo,
                                   'lotes_vence_30': lotes_vence_30,
                                   'lotes_vence_60': lotes_vence_60, 'prod_mes': prod_mes, 'ocs_pendientes': ocs_pendientes, 'sol_pendientes': sol_pendientes},
                    'animus': {'uds_pt': uds_pt, 'pedidos_activos': pedidos_activos, 'skus_stock': skus_stock, 'dias_desde_fm': dias_fm},
                    'inputs_manuales': inputs_manuales, 'semaforos': semaforos})

@bp.route('/api/gerencia/flujo-operacional')
def gerencia_flujo_operacional():
    if 'compras_user' not in session or session.get('compras_user','') not in FINANZAS_ACCESS:
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
    if 'compras_user' not in session or session.get('compras_user','') not in FINANZAS_ACCESS:
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


# ─── ADMIN — Carga MEE desde xlsx (stdlib, sin dependencias extra) ────────────

def _parse_xlsx_bytes(raw):
    """Parse xlsx bytes usando stdlib (zipfile + xml.etree). Retorna (headers, data_rows)."""
    NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    def tag(n): return f'{{{NS}}}{n}'

    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        shared = []
        if 'xl/sharedStrings.xml' in names:
            root = ET.parse(z.open('xl/sharedStrings.xml')).getroot()
            for si in root.iter(tag('si')):
                text = ''.join(t.text or '' for t in si.iter(tag('t')))
                shared.append(text)

        sheet_path = None
        for name in sorted(names):
            if re.match(r'xl/worksheets/sheet\d+\.xml', name):
                sheet_path = name
                break
        if not sheet_path:
            return [], []

        root = ET.parse(z.open(sheet_path)).getroot()

        def col_idx(ref):
            letters = re.match(r'([A-Z]+)', ref).group(1)
            n = 0
            for ch in letters:
                n = n * 26 + (ord(ch) - 64)
            return n - 1

        rows_raw = {}
        for row_el in root.iter(tag('row')):
            r = int(row_el.get('r', 0)) - 1
            cols = {}
            for c_el in row_el.iter(tag('c')):
                ref = c_el.get('r', 'A1')
                ci = col_idx(ref)
                t = c_el.get('t', '')
                v_el = c_el.find(tag('v'))
                if t == 's' and v_el is not None:
                    idx = int(v_el.text)
                    cols[ci] = shared[idx] if idx < len(shared) else ''
                elif t == 'inlineStr':
                    te = c_el.find(f'.//{tag("t")}')
                    cols[ci] = te.text if te is not None else ''
                elif v_el is not None:
                    cols[ci] = v_el.text or ''
                else:
                    cols[ci] = ''
            rows_raw[r] = cols

        if not rows_raw:
            return [], []

        max_col = max(max(d.keys(), default=0) for d in rows_raw.values())
        max_row = max(rows_raw.keys())

        def get_row(i):
            d = rows_raw.get(i, {})
            return [d.get(c, '') for c in range(max_col + 1)]

        h_idx = 0; best = 0
        for i in range(min(10, max_row + 1)):
            filled = sum(1 for v in get_row(i) if str(v).strip())
            if filled > best:
                best = filled; h_idx = i

        headers = [str(v).strip() for v in get_row(h_idx)]
        data_rows = [get_row(i) for i in range(h_idx + 1, max_row + 1)]
        return headers, data_rows


@bp.route('/api/admin/seed-mee-xlsx', methods=['POST'])
def seed_mee_xlsx():
    if 'compras_user' not in session or session.get('compras_user', '') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    if 'xlsx' not in request.files:
        return jsonify({'error': 'Campo "xlsx" requerido (multipart/form-data)'}), 400

    raw = request.files['xlsx'].read()
    try:
        headers, data_rows = _parse_xlsx_bytes(raw)
    except Exception as e:
        return jsonify({'error': f'Error parsing xlsx: {e}'}), 500

    if not headers:
        return jsonify({'error': 'No se encontraron datos en el xlsx'}), 400

    def norm(col):
        import unicodedata as _ud
        s = _ud.normalize('NFD', str(col).lower())
        return re.sub(r'[^a-z0-9]', '', ''.join(c for c in s if _ud.category(c) != 'Mn'))
    normas = {norm(h): i for i, h in enumerate(headers)}

    patrones = {
        'codigo':       ['codigomee', 'codigo', 'cod', 'ref', 'referencia', 'id', 'item'],
        'descripcion':  ['descripcion', 'nombre', 'material', 'desc', 'articulo', 'producto'],
        'categoria':    ['categoria', 'tipo', 'tipomaterial', 'clase', 'grupo'],
        'proveedor':    ['proveedor', 'supplier', 'vendedor'],
        'fabricante':   ['fabricante', 'marca', 'manufacturer'],
        'estado':       ['estado', 'status', 'activo'],
        'stock_actual': ['stockactual', 'cantidadactual', 'stock', 'existencias', 'cantidad',
                         'conteo', 'cantidadconteo', 'saldo', 'stockfisico', 'cant'],
        'stock_minimo': ['stockminimo', 'stockmin', 'minimo', 'min', 'reorden'],
        'unidad':       ['unidad', 'und', 'um', 'unidades', 'udm'],
    }
    mapa = {}
    for campo, lista in patrones.items():
        for p in lista:
            if p in normas:
                mapa[campo] = normas[p]; break

    if 'codigo' not in mapa or 'descripcion' not in mapa:
        return jsonify({'error': 'No se detectaron columnas codigo/descripcion',
                        'headers': headers}), 400

    def get_val(row, campo, default=''):
        idx = mapa.get(campo)
        return row[idx] if idx is not None and idx < len(row) else default

    def infer_cat(desc, cod):
        t = (str(desc) + ' ' + str(cod)).lower()
        if re.search(r'caja|corrugado|carton|box', t): return 'Caja'
        if re.search(r'frasco|botella|envase|flask|bottle', t): return 'Frasco'
        if re.search(r'tapa|cap|tapon', t): return 'Tapa'
        if re.search(r'bomba|pump|dispensador', t): return 'Bomba'
        if re.search(r'etiqueta|label|sticker', t): return 'Etiqueta'
        if re.search(r'bolsa|bag|sachet|pouch', t): return 'Bolsa'
        if re.search(r'tubo|tube', t): return 'Tubo'
        if re.search(r'insert|inserto|prospecto', t): return 'Inserto'
        return 'Otro'

    FECHA = '2026-04-19'
    inserted = skipped = dups = 0
    codigos_vistos = set()
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        for row in data_rows:
            cod  = str(get_val(row, 'codigo', '')).strip()
            desc = str(get_val(row, 'descripcion', '')).strip()
            if not cod or cod.upper() == 'NAN' or not desc:
                skipped += 1; continue
            if re.search(r'total|resumen|codigo|subtotal', cod, re.I):
                skipped += 1; continue
            if cod in codigos_vistos:
                dups += 1; continue
            codigos_vistos.add(cod)

            cat_raw = str(get_val(row, 'categoria', '')).strip()
            cat = cat_raw if cat_raw and cat_raw != 'nan' else infer_cat(desc, cod)
            prov = str(get_val(row, 'proveedor', '')).strip().replace('nan', '')
            fab  = str(get_val(row, 'fabricante', '')).strip().replace('nan', '')
            und  = str(get_val(row, 'unidad', 'und')).strip()
            if not und or und == 'nan': und = 'und'

            est_raw = str(get_val(row, 'estado', 'Activo')).lower().strip()
            estado = 'Inactivo' if re.search(r'inact|baja|obsoleto|descont', est_raw) else 'Activo'

            try: stock  = float(get_val(row, 'stock_actual', 0) or 0)
            except: stock = 0.0
            try: minimo = float(get_val(row, 'stock_minimo', 0) or 0)
            except: minimo = 0.0

            cur.execute("""INSERT OR REPLACE INTO maestro_mee
                (codigo, descripcion, categoria, proveedor, fabricante,
                 estado, stock_actual, stock_minimo, unidad, fecha_creacion)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (cod, desc, cat, prov, fab, estado, stock, minimo, und, FECHA))
            inserted += 1
        conn.commit()
    except Exception as e:
        conn.rollback(); conn.close()
        return jsonify({'error': str(e)}), 500

    c2 = conn.cursor()
    c2.execute("SELECT COUNT(*) FROM maestro_mee"); total = c2.fetchone()[0]
    c2.execute("SELECT COUNT(*) FROM maestro_mee WHERE stock_actual < stock_minimo AND stock_minimo > 0")
    bajo = c2.fetchone()[0]
    c2.execute("SELECT categoria, COUNT(*) c, SUM(stock_actual) s FROM maestro_mee GROUP BY categoria ORDER BY c DESC")
    cats = [{'cat': r[0], 'count': r[1], 'stock': r[2]} for r in c2.fetchall()]
    conn.close()

    return jsonify({
        'ok': True, 'inserted': inserted, 'skipped': skipped, 'dups': dups,
        'total_mee': total, 'bajo_minimo': bajo,
        'mapa_columnas': {k: headers[v] for k, v in mapa.items()},
        'por_categoria': cats
    })


@bp.route('/api/admin/mee-set-stock', methods=['POST'])
def mee_set_stock():
    """Actualiza stock_actual y stock_minimo de todos los MEE (uso unico admin)."""
    if 'compras_user' not in session or session.get('compras_user', '') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    data = request.get_json(silent=True) or {}
    stock_actual = float(data.get('stock_actual', 2000))
    stock_minimo = float(data.get('stock_minimo', 1000))
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE maestro_mee SET stock_actual=?, stock_minimo=?", (stock_actual, stock_minimo))
    updated = c.rowcount
    conn.commit()
    c.execute("SELECT COUNT(*) FROM maestro_mee WHERE stock_actual < stock_minimo AND stock_minimo > 0")
    bajo = c.fetchone()[0]
    conn.close()
    return jsonify({'ok': True, 'updated': updated, 'stock_actual': stock_actual,
                    'stock_minimo': stock_minimo, 'bajo_minimo': bajo})


# ─── MÓDULO FINANCIERO — Rutas ────────────────────────────────
