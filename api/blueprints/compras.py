# blueprints/compras.py — extraído de index.py (Fase C)
import os
import json
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, USER_EMAILS
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

bp = Blueprint('compras', __name__)


def _notificar_solicitante_email(dest_email, asunto, body_html):
    """Envia email al solicitante de forma no-bloqueante.
    Nunca lanza excepcion — falla silenciosamente con log.
    """
    if not dest_email:
        return
    try:
        import sys, threading
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from notificaciones import SistemaNotificaciones
        notif = SistemaNotificaciones()
        threading.Thread(
            target=notif._enviar_email,
            args=(asunto, body_html, [dest_email]),
            daemon=True
        ).start()
    except Exception as _e:
        print(f'[notificar_solicitante] email error (non-critical): {_e}')


@bp.route('/api/dashboard-stats')
def dashboard_stats():
    from datetime import date
    hoy = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()

    # Vencimientos por mes (próximos 6 meses)
    venc_por_mes = {}
    c.execute("""SELECT fecha_vencimiento, COUNT(*) as n, SUM(cantidad) as total_g
                 FROM movimientos WHERE tipo='Entrada' AND fecha_vencimiento IS NOT NULL
                 AND fecha_vencimiento >= ? AND fecha_vencimiento <= date(?, '+180 days')
                 GROUP BY substr(fecha_vencimiento,1,7) ORDER BY fecha_vencimiento""", (hoy, hoy))
    for row in c.fetchall():
        if row[0]:
            mes = str(row[0])[:7]
            venc_por_mes[mes] = {'lotes': row[1], 'kg': round((row[2] or 0)/1000, 1)}

    # Alertas de reabastecimiento: MPs bajo mínimo
    c.execute("""SELECT COUNT(*) FROM maestro_mps m
                 LEFT JOIN (SELECT material_id, SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock
                            FROM movimientos GROUP BY material_id) s ON m.codigo_mp=s.material_id
                 WHERE m.activo=1 AND m.stock_minimo>0 AND COALESCE(s.stock,0)<m.stock_minimo""")
    mps_bajo_minimo = c.fetchone()[0] or 0

    # Lotes vencidos / críticos / próximos
    c.execute("""SELECT estado_lote, COUNT(*) FROM movimientos WHERE tipo='Entrada' AND estado_lote IN ('VENCIDO','CRITICO','PROXIMO')
                 GROUP BY estado_lote""")
    estados = {r[0]: r[1] for r in c.fetchall()}

    # Top 5 MPs por stock actual
    c.execute("""SELECT material_id, material_nombre,
                        SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock
                 FROM movimientos GROUP BY material_id, material_nombre
                 HAVING stock > 0 ORDER BY stock DESC LIMIT 5""")
    top_stock = [{'codigo': r[0], 'nombre': r[1], 'kg': round(r[2]/1000, 1)} for r in c.fetchall()]

    # Stock total en kg
    c.execute("SELECT SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) FROM movimientos")
    stock_total_g = c.fetchone()[0] or 0

    conn.close()
    return jsonify({
        'vencimientos_por_mes': venc_por_mes,
        'mps_bajo_minimo': mps_bajo_minimo,
        'estados_lotes': estados,
        'top_stock': top_stock,
        'stock_total_kg': round(stock_total_g/1000, 1)
    })


@bp.route('/api/generar-oc-automatica', methods=['POST'])
def generar_oc_automatica():
    """Genera OCs automaticas por proveedor para todas las MPs bajo minimo"""
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()

    # Obtener MPs bajo minimo
    c.execute("""SELECT m.codigo_mp, m.nombre_comercial, m.proveedor, m.stock_minimo,
                        COALESCE(s.stock_actual, 0) as stock_actual
                 FROM maestro_mps m
                 LEFT JOIN (SELECT material_id,
                            SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock_actual
                            FROM movimientos GROUP BY material_id) s ON m.codigo_mp=s.material_id
                 WHERE m.activo=1 AND m.stock_minimo>0 AND COALESCE(s.stock_actual,0)<m.stock_minimo
                 ORDER BY m.proveedor, m.nombre_comercial""")
    alertas = c.fetchall()

    if not alertas:
        conn.close()
        return jsonify({'message': 'No hay MPs bajo stock minimo', 'ordenes': []})

    # Agrupar por proveedor
    por_proveedor = {}
    for row in alertas:
        codigo, nombre, prov, smin, sact = row
        prov = prov or 'Sin proveedor'
        deficit = smin - sact
        cantidad_pedir = round(deficit * 1.1, 0)  # pedir el deficit + 10% extra
        if prov not in por_proveedor:
            por_proveedor[prov] = []
        por_proveedor[prov].append({
            'codigo_mp': codigo, 'nombre_mp': nombre,
            'stock_actual': round(sact, 0), 'stock_minimo': smin,
            'deficit': round(deficit, 0), 'cantidad_pedir': cantidad_pedir,
            'unidad': 'g'
        })

    # Crear OC por cada proveedor
    ordenes_creadas = []
    for prov, items in por_proveedor.items():
        c.execute("SELECT COUNT(*) FROM ordenes_compra"); num=(c.fetchone()[0] or 0)+1
        numero_oc = f"OC-{datetime.now().strftime('%Y')}-{num:04d}"
        c.execute("INSERT INTO ordenes_compra (numero_oc, fecha, estado, proveedor, observaciones) VALUES (?,?,?,?,?)",
                  (numero_oc, datetime.now().isoformat(), 'Pendiente', prov, 'Generada automaticamente por stock bajo minimo'))
        for item in items:
            c.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g) VALUES (?,?,?,?)",
                      (numero_oc, item['codigo_mp'], item['nombre_mp'], item['cantidad_pedir']))
        # Generar cuerpo del email
        sep = '-' * 50
        fecha_str = datetime.now().strftime('%d/%m/%Y')
        eb = 'ORDEN DE COMPRA: ' + numero_oc + '\n'
        eb += 'Fecha: ' + fecha_str + '\n'
        eb += 'Proveedor: ' + prov + '\n'
        eb += 'Generada por: Sistema de Inventarios Espagiria\n\n'
        eb += 'MATERIAS PRIMAS A COMPRAR:\n' + sep + '\n'
        for it in items:
            eb += str(it['codigo_mp']) + ' - ' + str(it['nombre_mp']) + '\n'
            eb += '  Stock actual: ' + str(int(it['stock_actual'])) + 'g | Minimo: ' + str(int(it['stock_minimo'])) + 'g\n'
            eb += '  CANTIDAD A PEDIR: ' + str(int(it['cantidad_pedir'])) + ' g = ' + str(round(it['cantidad_pedir']/1000, 2)) + ' kg\n'
            eb += sep + '\n'
        eb += '\nTotal: ' + str(len(items)) + ' items pendientes de compra.\n'
        eb += 'Por favor aprobar y contactar al proveedor.\n'
        eb += '\n--- Sistema de Inventarios Espagiria Laboratorios ---\n'
        email_body = eb
        ordenes_creadas.append({
            'numero_oc': numero_oc, 'proveedor': prov,
            'total_items': len(items), 'items': items,
            'email_subject': f'[OC] {numero_oc} - Espagiria Laboratorios',
            'email_body': email_body
        })

    conn.commit(); conn.close()
    return jsonify({
        'message': f'{len(ordenes_creadas)} OC(s) generadas automaticamente',
        'ordenes': ordenes_creadas
    }), 201


# ── MÓDULO COMPRAS ──────────────────────────────────────────────────────────
@bp.route('/api/ordenes-compra', methods=['GET','POST'])
def handle_ordenes_compra():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json
        if not d.get('proveedor'): conn.close(); return jsonify({'error': 'Proveedor requerido'}), 400
        c.execute("SELECT COUNT(*) FROM ordenes_compra"); num = (c.fetchone()[0] or 0) + 1
        numero_oc = f"OC-{datetime.now().strftime('%Y')}-{num:04d}"
        categoria = d.get('categoria', 'MP')
        c.execute("INSERT INTO ordenes_compra (numero_oc,fecha,estado,proveedor,observaciones,creado_por,fecha_entrega_est,categoria) VALUES (?,?,?,?,?,?,?,?)",
                  (numero_oc, datetime.now().isoformat(), 'Borrador', d['proveedor'],
                   d.get('observaciones',''), d.get('creado_por',''), d.get('fecha_entrega_est',''), categoria))
        for it in (d.get('items') or []):
            subtotal = round((it.get('cantidad_g',0)) * (it.get('precio_unitario',0)), 2)
            c.execute("INSERT INTO ordenes_compra_items (numero_oc,codigo_mp,nombre_mp,cantidad_g,precio_unitario,subtotal) VALUES (?,?,?,?,?,?)",
                      (numero_oc, it.get('codigo_mp',''), it.get('nombre_mp',''),
                       it.get('cantidad_g',0), it.get('precio_unitario',0), subtotal))
        valor_total_calc = sum(
            round((it.get('cantidad_g',0))*(it.get('precio_unitario',0)),2)
            for it in (d.get('items') or [])
        )
        if valor_total_calc > 0:
            c.execute("UPDATE ordenes_compra SET valor_total=? WHERE numero_oc=?", (valor_total_calc, numero_oc))
        conn.commit(); conn.close()
        return jsonify({'message': f'OC {numero_oc} creada', 'numero_oc': numero_oc}), 201
    cat_filter = request.args.get('categoria', '')
    _sql = (
        "SELECT o.numero_oc, o.fecha, o.estado, o.proveedor, o.fecha_entrega_est,"
        " o.observaciones, o.creado_por, COUNT(i.id) as num_items,"
        " o.categoria, o.remision_code, o.autorizado_por,"
        " COALESCE(o.valor_total, 0) as valor_total,"
        " COALESCE(o.con_iva, 0) as con_iva, COALESCE(o.valor_sin_iva, 0) as valor_sin_iva"
        " FROM ordenes_compra o LEFT JOIN ordenes_compra_items i ON o.numero_oc=i.numero_oc"
    )
    if cat_filter:
        c.execute(_sql + " WHERE o.categoria=? GROUP BY o.numero_oc ORDER BY o.fecha DESC LIMIT 300", (cat_filter,))
    else:
        c.execute(_sql + " GROUP BY o.numero_oc ORDER BY o.fecha DESC LIMIT 300")
    cols = ['numero_oc','fecha','estado','proveedor','fecha_entrega_est','observaciones',
            'creado_por','num_items','categoria','remision_code','autorizado_por','valor_total',
            'con_iva','valor_sin_iva']
    rows = c.fetchall(); conn.close()
    return jsonify({'ordenes': [dict(zip(cols, r)) for r in rows]})

@bp.route('/api/ordenes-compra/<numero_oc>', methods=['GET','PUT','DELETE'])
def handle_oc_detalle(numero_oc):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'DELETE':
        c.execute("SELECT estado FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
        _row = c.fetchone()
        if not _row:
            conn.close(); return jsonify({'error': 'OC no encontrada'}), 404
        if _row[0] not in ('Borrador', 'Rechazada'):
            conn.close()
            return jsonify({'error': f'No se puede eliminar una OC en estado {_row[0]}. Solo Borrador o Rechazada.'}), 400
        c.execute('DELETE FROM ordenes_compra_items WHERE numero_oc=?', (numero_oc,))
        c.execute('DELETE FROM ordenes_compra WHERE numero_oc=?', (numero_oc,))
        conn.commit(); conn.close()
        return jsonify({'ok': True, 'message': f'OC {numero_oc} eliminada'})

    if request.method == 'PUT':
        d = request.json
        nuevo_estado = d.get('estado','')
        usuario_actual = session.get('compras_user','')
        if usuario_actual in CONTADORA_USERS and nuevo_estado in ('Aprobada','Pagada'):
            conn.close(); return jsonify({'error':'Sin permiso para esta accion'}), 403
        if d.get('estado'): c.execute("UPDATE ordenes_compra SET estado=? WHERE numero_oc=?", (d['estado'], numero_oc))
        conn.commit(); conn.close(); return jsonify({'message': f'OC {numero_oc} actualizada'})
    c.execute("SELECT * FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    oc_row = c.fetchone()
    oc_cols = [d[0] for d in c.description] if c.description else []
    c.execute("SELECT * FROM ordenes_compra_items WHERE numero_oc=?", (numero_oc,))
    items = c.fetchall()
    if not oc_row: conn.close(); return jsonify({'error': 'OC no encontrada'}), 404
    oc_dict = dict(zip(oc_cols, oc_row))
    prov_data = None
    prov_name = oc_dict.get('proveedor', '')
    if prov_name:
        c.execute(
            "SELECT banco, tipo_cuenta, num_cuenta, nit, email, telefono, contacto"
            " FROM proveedores WHERE nombre=? AND activo=1 LIMIT 1",
            (prov_name,)
        )
        prow = c.fetchone()
        if prow:
            prov_data = dict(zip(
                ['banco', 'tipo_cuenta', 'num_cuenta', 'nit', 'email', 'telefono', 'contacto'],
                prow
            ))
    conn.close()
    return jsonify({'oc': oc_dict, 'items': items, 'prov_data': prov_data})

@bp.route('/api/ordenes-compra/<numero_oc>/editar', methods=['PATCH'])
def editar_oc(numero_oc):
    """Edita una OC en estado Borrador: reemplaza items y actualiza campos."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute('SELECT estado FROM ordenes_compra WHERE numero_oc=?', (numero_oc,))
    row = c.fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'OC no encontrada'}), 404
    if row[0] != 'Borrador':
        conn.close()
        return jsonify({'error': f'Solo se pueden editar OCs en Borrador (estado actual: {row[0]})'}), 400
    d = request.json or {}
    if not d.get('proveedor'):
        conn.close(); return jsonify({'error': 'Proveedor requerido'}), 400
    con_iva = 1 if d.get('con_iva') else 0
    valor_sin_iva = float(d.get('valor_sin_iva', 0))
    c.execute("""
        UPDATE ordenes_compra SET
            proveedor=?, categoria=?, observaciones=?,
            fecha_entrega_est=?, con_iva=?, valor_sin_iva=?
        WHERE numero_oc=?""",
        (d['proveedor'], d.get('categoria', 'MP'), d.get('observaciones', ''),
         d.get('fecha_entrega_est', ''), con_iva, valor_sin_iva, numero_oc))
    # Reemplazar items completo
    c.execute('DELETE FROM ordenes_compra_items WHERE numero_oc=?', (numero_oc,))
    valor_total = 0.0
    for it in (d.get('items') or []):
        subtotal = round(float(it.get('cantidad_g', 0)) * float(it.get('precio_unitario', 0)), 2)
        c.execute('INSERT INTO ordenes_compra_items (numero_oc,codigo_mp,nombre_mp,cantidad_g,precio_unitario,subtotal) VALUES (?,?,?,?,?,?)',
                  (numero_oc, it.get('codigo_mp', ''), it.get('nombre_mp', ''),
                   float(it.get('cantidad_g', 0)), float(it.get('precio_unitario', 0)), subtotal))
        valor_total += subtotal
    if con_iva:
        valor_total = round(valor_total * 1.19, 2)
    c.execute('UPDATE ordenes_compra SET valor_total=? WHERE numero_oc=?', (valor_total, numero_oc))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'message': f'OC {numero_oc} actualizada', 'valor_total': valor_total})

@bp.route('/api/proveedores-compras', methods=['GET','POST'])
def handle_proveedores_compras():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json
        if not d.get('nombre'): conn.close(); return jsonify({'error': 'Nombre requerido'}), 400
        try:
            c.execute("""INSERT INTO proveedores
                (nombre,contacto,email,telefono,categoria,condiciones_pago,
                 nit,direccion,num_cuenta,tipo_cuenta,banco,concepto_compra,fecha_creacion)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (d['nombre'],d.get('contacto',''),d.get('email',''),d.get('telefono',''),
                 d.get('categoria',''),d.get('condiciones_pago','30 dias'),
                 d.get('nit',''),d.get('direccion',''),d.get('num_cuenta',''),
                 d.get('tipo_cuenta',''),d.get('banco',''),d.get('concepto_compra',d.get('concepto','')),
                 datetime.now().isoformat()))
            conn.commit(); conn.close()
            return jsonify({'message': f"Proveedor '{d['nombre']}' creado"}), 201
        except Exception as e: conn.close(); return jsonify({'error': str(e)}), 400
    c.execute("""SELECT nombre,contacto,email,telefono,categoria,condiciones_pago,
                       nit,direccion,num_cuenta,tipo_cuenta,banco,concepto_compra
                FROM proveedores WHERE activo=1 ORDER BY nombre""")
    cols = ['nombre','contacto','email','telefono','categoria','condiciones_pago',
            'nit','direccion','num_cuenta','tipo_cuenta','banco','concepto_compra']
    provs = [dict(zip(cols, r)) for r in c.fetchall()]; conn.close()
    return jsonify({'proveedores': provs})

@bp.route('/api/proveedores-compras/<path:nombre>/ficha')
def proveedor_ficha_360(nombre):
    """Proveedor 360: datos completos + historial OCs + scoring."""
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT id, nombre, contacto, email, telefono, categoria,
                        nit, direccion, num_cuenta, tipo_cuenta, banco, concepto_compra,
                        id_interno, estado_lpa, ultima_evaluacion, vencimiento_docs,
                        acuerdo_calidad, condiciones_pago
                 FROM proveedores WHERE nombre=? AND activo=1""", (nombre,))
    row = c.fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'Proveedor no encontrado'}), 404
    cols = ['id','nombre','contacto','email','telefono','categoria',
            'nit','direccion','num_cuenta','tipo_cuenta','banco','concepto_compra',
            'id_interno','estado_lpa','ultima_evaluacion','vencimiento_docs',
            'acuerdo_calidad','condiciones_pago']
    prov = dict(zip(cols, row))
    # OC stats
    c.execute("""SELECT COUNT(*), COALESCE(SUM(valor_total),0), MIN(fecha), MAX(fecha)
                 FROM ordenes_compra WHERE proveedor=?""", (nombre,))
    r = c.fetchone()
    oc_total, valor_total, primera_oc, ultima_oc = (r[0] or 0), (r[1] or 0), r[2], r[3]
    c.execute("SELECT COUNT(*) FROM ordenes_compra WHERE proveedor=? AND estado IN ('Recibida','Pagada','Parcial')", (nombre,))
    oc_recibidas = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM ordenes_compra WHERE proveedor=? AND tiene_discrepancias=1 AND estado IN ('Recibida','Pagada','Parcial')", (nombre,))
    oc_disc = c.fetchone()[0] or 0
    # Scoring: cumplimiento 70% + calidad (sin discrepancias) 30%
    cumplimiento = round((oc_recibidas / oc_total * 100) if oc_total > 0 else 0, 1)
    tasa_disc = round((oc_disc / oc_recibidas * 100) if oc_recibidas > 0 else 0, 1)
    score = min(100.0, round(cumplimiento * 0.7 + (100 - tasa_disc) * 0.3, 1))
    # Recent OCs
    c.execute("""SELECT numero_oc, fecha, estado, valor_total, categoria,
                        tiene_discrepancias, fecha_recepcion
                 FROM ordenes_compra WHERE proveedor=?
                 ORDER BY fecha DESC LIMIT 8""", (nombre,))
    oc_cols = ['numero_oc','fecha','estado','valor_total','categoria','tiene_discrepancias','fecha_recepcion']
    ocs_recientes = [dict(zip(oc_cols, r)) for r in c.fetchall()]
    # Materials bought from this supplier
    c.execute("""SELECT oci.codigo_mp, oci.nombre_mp, COUNT(*) as veces, SUM(oci.cantidad_g) as total_g
                 FROM ordenes_compra oc
                 JOIN ordenes_compra_items oci ON oc.numero_oc=oci.numero_oc
                 WHERE oc.proveedor=?
                 GROUP BY oci.codigo_mp, oci.nombre_mp
                 ORDER BY total_g DESC LIMIT 15""", (nombre,))
    mps = [{'codigo': r[0], 'nombre': r[1], 'veces': r[2], 'total_g': round(r[3] or 0, 1)}
           for r in c.fetchall()]
    conn.close()
    return jsonify({
        'proveedor': prov,
        'stats': {
            'oc_total': oc_total, 'oc_recibidas': oc_recibidas, 'oc_discrepancias': oc_disc,
            'valor_total': valor_total, 'primera_oc': primera_oc, 'ultima_oc': ultima_oc,
            'cumplimiento': cumplimiento, 'tasa_discrepancias': tasa_disc, 'score': score
        },
        'ocs_recientes': ocs_recientes,
        'materiales': mps
    })


@bp.route('/api/solicitudes-compra', methods=['GET','POST'])
def handle_solicitudes_compra():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json
        c.execute("SELECT COUNT(*) FROM solicitudes_compra"); num = (c.fetchone()[0] or 0) + 1
        numero = f"SOL-{datetime.now().strftime('%Y')}-{num:04d}"
        emp = d.get('empresa','Espagiria')
        cat = d.get('categoria','Materia Prima')
        tip = d.get('tipo','Compra')
        area = d.get('area','Produccion')
        email_sol = d.get('email_solicitante', '').strip().lower()
        fecha_req = d.get('fecha_requerida', '').strip()
        c.execute("""INSERT INTO solicitudes_compra
                     (numero,fecha,estado,solicitante,urgencia,observaciones,area,empresa,categoria,tipo,email_solicitante,fecha_requerida)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (numero, datetime.now().isoformat(), 'Pendiente',
                   d.get('solicitante',''), d.get('urgencia','Normal'), d.get('observaciones',''),
                   area, emp, cat, tip, email_sol, fecha_req))
        for it in (d.get('items') or []):
            c.execute("""INSERT INTO solicitudes_compra_items
                         (numero,codigo_mp,nombre_mp,cantidad_g,unidad,justificacion,valor_estimado)
                         VALUES (?,?,?,?,?,?,?)""",
                      (numero, it.get('codigo_mp',''), it.get('nombre_mp',''),
                       it.get('cantidad_g',0), it.get('unidad','g'),
                       it.get('justificacion',''), it.get('valor_estimado',0)))
        conn.commit(); conn.close()
        return jsonify({'message': f'Solicitud {numero} creada', 'numero': numero}), 201
    # GET: listar todas las solicitudes
    filtro_estado = request.args.get('estado', '')
    filtro_empresa = request.args.get('empresa', '')
    sql = "SELECT numero,fecha,estado,solicitante,urgencia,observaciones,empresa,categoria,tipo,area,email_solicitante,fecha_requerida FROM solicitudes_compra WHERE 1=1"
    params = []
    if filtro_estado: sql += " AND estado=?"; params.append(filtro_estado)
    if filtro_empresa: sql += " AND empresa=?"; params.append(filtro_empresa)
    filtro_categoria = request.args.get('categoria', '')
    if filtro_categoria:
        sql += " AND categoria=?"; params.append(filtro_categoria)
    else:
        # Sin filtro explicito = vista de Catalina: excluir categorias de pago/gerencia
        sql += " AND categoria NOT IN ('Influencer/Marketing Digital','Cuenta de Cobro')"
    sql += " ORDER BY fecha DESC LIMIT 200"
    c.execute(sql, params)
    cols_sol = ['numero','fecha','estado','solicitante','urgencia','observaciones','empresa','categoria','tipo','area','email_solicitante','fecha_requerida']
    rows_sol = [dict(zip(cols_sol, r)) for r in c.fetchall()]
    # Enrich with numero_oc and total valor
    for row in rows_sol:
        c2 = conn.cursor()
        c2.execute("SELECT numero_oc, aprobado_por FROM solicitudes_compra WHERE numero=?", (row['numero'],))
        extra = c2.fetchone()
        row['numero_oc'] = extra[0] if extra else None
        c2.execute("SELECT COALESCE(SUM(valor_estimado),0) FROM solicitudes_compra_items WHERE numero=?", (row['numero'],))
        row['valor'] = c2.fetchone()[0] or 0
    conn.close()
    return jsonify({'solicitudes': rows_sol})


@bp.route('/api/solicitudes-compra/<numero>', methods=['GET'])
def get_solicitud_estado(numero):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT numero,fecha,estado,solicitante,urgencia,observaciones,numero_oc FROM solicitudes_compra WHERE numero=?", (numero.upper(),))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'No encontrada'}), 404
    cols = ['numero','fecha','estado','solicitante','urgencia','observaciones','numero_oc']
    sol = dict(zip(cols, row))
    for col in ['area','empresa','categoria','tipo','aprobado_por','fecha_aprobacion']:
        try:
            c.execute(f"SELECT {col} FROM solicitudes_compra WHERE numero=?", (numero.upper(),))
            r2 = c.fetchone()
            if r2: sol[col] = r2[0]
        except: pass
    c.execute("SELECT codigo_mp,nombre_mp,cantidad_g,unidad,valor_estimado FROM solicitudes_compra_items WHERE numero=?", (numero.upper(),))
    items = [dict(zip(['codigo_mp','nombre_mp','cantidad_g','unidad','valor_estimado'], r)) for r in c.fetchall()]
    conn.close()
    return jsonify({'solicitud': sol, 'items': items})

@bp.route('/solicitudes')
def solicitudes_page():
    if 'compras_user' not in session:
        return redirect('/login?next=/solicitudes')
    return Response(SOLICITUDES_HTML, mimetype='text/html')


@bp.route('/api/solicitudes-compra/<numero>/estado', methods=['PATCH'])
def actualizar_estado_solicitud(numero):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.get_json() or {}
    nuevo = d.get('estado', 'Aprobada')
    numero_oc_param = d.get('numero_oc', '')
    obs = d.get('observaciones', '')
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("""UPDATE solicitudes_compra SET estado=?, aprobado_por=?, fecha_aprobacion=?
                 WHERE numero=?""",
              (nuevo, session.get('compras_user',''), datetime.now().isoformat(), numero.upper()))
    if numero_oc_param:
        cur.execute("UPDATE solicitudes_compra SET numero_oc=? WHERE numero=?", (numero_oc_param, numero.upper()))
    if nuevo == 'Rechazada' and obs:
        cur.execute("UPDATE solicitudes_compra SET observaciones=? WHERE numero=?", (obs, numero.upper()))
    conn.commit()
    oc_creada = ''
    if d.get('crear_oc'):
        cur.execute("SELECT codigo_mp, nombre_mp, cantidad_g, unidad, categoria FROM solicitudes_compra_items WHERE numero=?", (numero.upper(),))
        items_sol = cur.fetchall()
        # Obtener categoria de la solicitud para la OC
        cur.execute("SELECT categoria FROM solicitudes_compra WHERE numero=?", (numero.upper(),))
        sol_row = cur.fetchone()
        categoria_oc = d.get('categoria') or (sol_row[0] if sol_row and sol_row[0] else 'MP')
        # Normalizar categorias largas de solicitudes a claves cortas de OC
        _SOLIC_TO_OC_CAT = {
            'Materia Prima': 'MP', 'Materias Primas': 'MP', 'MPs': 'MP',
            'Material de Empaque': 'MEE', 'Envase': 'MEE', 'Insumos': 'MEE',
            'Empaque': 'MEE',
            'EPP': 'ADM', 'Aseo/Limpieza': 'ADM', 'Papeleria/Oficina': 'ADM',
            'Dotacion': 'ADM', 'Otro': 'ADM', 'Administrativo': 'ADM',
            'Nomina': 'ADM', 'Admin': 'ADM',
            'Mantenimiento': 'INF', 'Repuestos': 'INF',
            'Reactivos/Laboratorio': 'INF', 'Infraestructura': 'INF',
            'Servicios Profesionales': 'SVC', 'Software/Tecnologia': 'SVC',
            'Servicios': 'SVC', 'Analisis': 'SVC', 'Acondicionamiento': 'SVC',
            'Servicio': 'SVC',
        }
        categoria_oc = _SOLIC_TO_OC_CAT.get(categoria_oc, categoria_oc)
        proveedor_oc = d.get('proveedor', 'Por definir')
        valor_oc = float(d.get('valor_total') or 0)
        fent_oc = d.get('fecha_entrega_est', '')
        obs_oc = d.get('observaciones_oc') or f'Generado desde {numero.upper()}'
        cur.execute("SELECT COUNT(*) FROM ordenes_compra")
        n_oc = cur.fetchone()[0] + 1
        oc_num = f"OC-{datetime.now().year}-{n_oc:04d}"
        # Influencer y Cuenta de Cobro saltan directo a Autorizada
        # (gerencia ya aprobo la solicitud en su tab — no necesita doble autorizacion)
        _FAST_TRACK = ('Influencer/Marketing Digital', 'Cuenta de Cobro')
        estado_oc = 'Autorizada' if categoria_oc in _FAST_TRACK else 'Revisada'
        cur.execute(
            "INSERT INTO ordenes_compra "
            "(numero_oc, fecha, estado, proveedor, observaciones, creado_por, valor_total, fecha_entrega_est, categoria) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (oc_num, datetime.now().isoformat(), estado_oc, proveedor_oc,
             obs_oc, session.get('compras_user',''),
             valor_oc if valor_oc > 0 else None, fent_oc or None, categoria_oc))
        for it in items_sol:
            cur.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g) VALUES (?,?,?,?)",
                      (oc_num, it[0], it[1], it[2]))
        cur.execute("UPDATE solicitudes_compra SET numero_oc=? WHERE numero=?", (oc_num, numero.upper()))
        oc_creada = oc_num
    # Fetch email for notification BEFORE closing connection
    cur.execute("SELECT email_solicitante FROM solicitudes_compra WHERE numero=?", (numero.upper(),))
    _em_row = cur.fetchone()
    _notif_dest = (_em_row[0] if _em_row else '').strip()
    conn.commit(); conn.close()
    # Notificacion al solicitante (no-blocking, best-effort)
    if _notif_dest:
        if nuevo == 'Rechazada':
            _asunto_n = f'Solicitud rechazada \u2014 {numero.upper()}'
            _body_n = (
                '<html><body style="font-family:Arial,sans-serif;max-width:600px;">'
                '<div style="background:#fee2e2;padding:20px;border-radius:8px;border-left:4px solid #dc2626;">'
                '<h2 style="color:#991b1b;">Solicitud rechazada</h2>'
                f'<p>Tu solicitud <strong>{numero.upper()}</strong> fue rechazada.</p>'
                + (f'<p><strong>Motivo:</strong> {obs}</p>' if obs else '')
                + '<p>Puedes corregirla y reenviarla desde el sistema.</p>'
                '<p style="color:#6b7280;font-size:12px;">Compras HHA \u2014 Espagiria</p>'
                '</div></body></html>'
            )
            _notificar_solicitante_email(_notif_dest, _asunto_n, _body_n)
        elif oc_creada:
            _asunto_n = f'Solicitud aprobada \u2014 {numero.upper()}'
            _body_n = (
                '<html><body style="font-family:Arial,sans-serif;max-width:600px;">'
                '<div style="background:#dcfce7;padding:20px;border-radius:8px;border-left:4px solid #16a34a;">'
                '<h2 style="color:#15803d;">Solicitud aprobada</h2>'
                f'<p>Tu solicitud <strong>{numero.upper()}</strong> fue aprobada.</p>'
                f'<p>Orden de compra generada: <strong>{oc_creada}</strong></p>'
                '<p>El equipo de compras esta gestionando tu pedido.</p>'
                '<p style="color:#6b7280;font-size:12px;">Compras HHA \u2014 Espagiria</p>'
                '</div></body></html>'
            )
            _notificar_solicitante_email(_notif_dest, _asunto_n, _body_n)
    return jsonify({'ok': True, 'estado': nuevo, 'numero_oc': oc_creada})

@bp.route('/api/ordenes-compra/<numero_oc>/recibir', methods=['POST'])
def recibir_oc(numero_oc):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT estado, proveedor, categoria FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    oc_row = cur.fetchone()
    if not oc_row:
        conn.close(); return jsonify({'error': 'OC no encontrada'}), 404
    if oc_row[0] not in ('Autorizada', 'Parcial'):
        conn.close(); return jsonify({'error': f'OC en estado {oc_row[0]} no permite recepcion'}), 409
    prov_nombre = oc_row[1] or ''
    categoria = oc_row[2] or 'MP'
    cur.execute("SELECT codigo_mp, nombre_mp, cantidad_g FROM ordenes_compra_items WHERE numero_oc=?", (numero_oc,))
    items_oc = cur.fetchall()
    fecha = datetime.now().isoformat()
    operador = session.get('compras_user', '')
    data2 = request.get_json(silent=True) or {}
    obs_r = data2.get('observaciones_recepcion', '')
    disc_r = 1 if data2.get('tiene_discrepancias') else 0
    items_r = data2.get('items_recepcion', [])
    receptor_nombre = data2.get('receptor_nombre', '') or operador
    # Build lookup por indice posicional (codigo_mp puede estar vacio en solicitudes)
    rec_map_idx = {idx: ir for idx, ir in enumerate(items_r)}
    # Fallback: lookup por codigo_mp para compatibilidad con clientes que lo envien
    rec_map_cod = {ir.get('codigo_mp', ''): ir for ir in items_r if ir.get('codigo_mp', '')}
    ingresos = 0
    es_parcial = False
    for _idx, item in enumerate(items_oc):
        codigo, nombre, cantidad_pedida = item
        ir = rec_map_idx.get(_idx) or rec_map_cod.get(codigo, {})
        cant_recibida = float(ir.get('cantidad_recibida', 0) or cantidad_pedida)
        lote_num = ir.get('lote', '').strip()
        fv = ir.get('fecha_vencimiento', '').strip()
        estado_item = ir.get('estado', 'OK')
        notas_item = ir.get('notas', '')
        # Detectar recepcion parcial
        if cant_recibida < cantidad_pedida * 0.999:
            es_parcial = True
        # Solo registrar movimiento si hay algo recibido
        if cant_recibida > 0:
            if categoria == 'MEE':
                cur.execute("UPDATE maestro_mee SET stock_actual = stock_actual + ? WHERE codigo=?", (cant_recibida, codigo))
                cur.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, lote_ref, observaciones, responsable, fecha) VALUES (?,?,?,?,?,?,?)",
                           (codigo, 'Entrada', cant_recibida, numero_oc, f'Recepcion OC {numero_oc}', operador, fecha))
            else:
                cur.execute(
                    "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, "
                    "observaciones, proveedor, operador, lote, fecha_vencimiento, estado_lote, numero_oc) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (codigo, nombre, cant_recibida, 'Entrada', fecha,
                     f'Recepcion OC {numero_oc}' + (f' | {notas_item}' if notas_item else ''),
                     prov_nombre, operador, lote_num or None, fv or None, 'Cuarentena', numero_oc))
            ingresos += 1
        # Actualizar item OC
        try:
            cur.execute(
                "UPDATE ordenes_compra_items SET cantidad_recibida_g=?, estado_recepcion=?, notas_recepcion=?, lote_asignado=?"
                " WHERE numero_oc=? AND codigo_mp=?",
                (cant_recibida, estado_item, notas_item, lote_num, numero_oc, codigo))
        except Exception:
            pass
    # Estado final de la OC
    nuevo_estado = 'Parcial' if es_parcial else 'Recibida'
    try:
        cur.execute(
            "UPDATE ordenes_compra SET estado=?, fecha_recepcion=?,"
            " observaciones_recepcion=?, tiene_discrepancias=?, recibido_por=? WHERE numero_oc=?",
            (nuevo_estado, fecha, obs_r, disc_r, receptor_nombre, numero_oc))
    except Exception:
        cur.execute("UPDATE ordenes_compra SET estado=?, fecha_recepcion=? WHERE numero_oc=?", (nuevo_estado, fecha, numero_oc))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'numero_oc': numero_oc, 'ingresos': ingresos, 'estado': nuevo_estado, 'parcial': es_parcial})

# ============================================================
# Compras — Flujo de autorizacion y pago
# ============================================================

@bp.route('/api/ordenes-compra/<numero_oc>/revisar', methods=['PATCH'])
def revisar_oc(numero_oc):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.get_json() or {}
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    sets = ["estado='Revisada'"]; params = []
    if d.get('proveedor'):
        sets.append('proveedor=?'); params.append(str(d['proveedor']))
    if d.get('valor_total') not in (None, '', 0):
        sets.append('valor_total=?'); params.append(float(d['valor_total'] or 0))
    if d.get('observaciones'):
        sets.append('observaciones=?'); params.append(str(d['observaciones']))
    # IVA
    sets.append('con_iva=?'); params.append(1 if d.get('con_iva') else 0)
    sets.append('valor_sin_iva=?'); params.append(float(d.get('valor_sin_iva') or 0))
    params.append(numero_oc)
    cur.execute(f"UPDATE ordenes_compra SET {', '.join(sets)} WHERE numero_oc=?", params)
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'estado': 'Revisada'})

@bp.route('/api/ordenes-compra/<numero_oc>/autorizar', methods=['PATCH'])
def autorizar_oc(numero_oc):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    usuario_actual = session.get('compras_user', '')
    if usuario_actual in CONTADORA_USERS:
        return jsonify({'error': 'Sin permiso para autorizar OCs'}), 403
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT estado FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    row = cur.fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'OC no encontrada'}), 404
    fecha_hoy = datetime.now().strftime('%Y%m%d')
    cur.execute("SELECT remision_code FROM ordenes_compra WHERE remision_code LIKE ? ORDER BY remision_code DESC LIMIT 1",
                (f'REM-ESP-{fecha_hoy}-%',))
    last = cur.fetchone()
    n = int(last[0].split('-')[-1]) + 1 if last and last[0] else 1
    remision_code = f'REM-ESP-{fecha_hoy}-{n:03d}'
    fecha_aut = datetime.now().isoformat()
    cur.execute("UPDATE ordenes_compra SET estado='Autorizada', remision_code=?, autorizado_por=?, fecha_autorizacion=? WHERE numero_oc=?",
                (remision_code, usuario_actual, fecha_aut, numero_oc))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'estado': 'Autorizada', 'remision_code': remision_code})

@bp.route('/api/ordenes-compra/<numero_oc>/pagar', methods=['PATCH'])
def pagar_oc(numero_oc):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    usuario_actual = session.get('compras_user', '')
    if usuario_actual in CONTADORA_USERS:
        return jsonify({'error': 'Sin permiso para registrar pagos'}), 403
    d = request.get_json() or {}
    monto = float(d.get('monto', 0) or 0)
    medio = d.get('medio', 'Transferencia')
    obs = d.get('observaciones', '')
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT estado, categoria, proveedor, valor_total FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    row = cur.fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'OC no encontrada'}), 404
    categoria = row[1] or 'MP'
    proveedor = row[2] or ''
    if not monto: monto = float(row[3] or 0)
    cat_map = {'MPs':'MPs','MP':'MPs','Envase':'MEE','Insumos':'MEE','MEE':'MEE','SVC':'Servicios','Servicios':'Servicios','Analisis':'Servicios','Ánalisis':'Servicios','Acondicionamiento':'Servicios','Admin':'Administrativo','Nomina':'Administrativo','ADM':'Administrativo','Infraestructura':'Infraestructura','INF':'Infraestructura','CC':'Cuentas de Cobro'}
    cat_egreso = cat_map.get(categoria, 'Compras')
    fecha_pago = datetime.now().isoformat()
    cur.execute("UPDATE ordenes_compra SET estado='Pagada', pagado_por=?, fecha_pago=? WHERE numero_oc=?",
                (usuario_actual, fecha_pago, numero_oc))
    try:
        cur.execute("INSERT INTO flujo_egresos (fecha, empresa, concepto, categoria, monto, periodo, fuente, referencia, creado_por, observaciones) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (fecha_pago, 'Espagiria', f'Pago OC {numero_oc} - {proveedor}',
                    cat_egreso, monto, datetime.now().strftime('%Y-%m'),
                    'compras', numero_oc, usuario_actual, f'{medio}. {obs}'))
    except Exception:
        pass
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'estado': 'Pagada', 'monto': monto})

@bp.route('/api/compras/oc/<numero_oc>/rechazar', methods=['POST'])
def rechazar_oc(numero_oc):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    usuario_actual = session.get('compras_user', '')
    d = request.get_json() or {}
    motivo = d.get('motivo', 'Sin motivo especificado')[:300]
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT estado, categoria FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    row = cur.fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'OC no encontrada'}), 404
    # Mark OC as Rechazada
    cur.execute("UPDATE ordenes_compra SET estado='Rechazada', observaciones=COALESCE(observaciones,'')||' | RECHAZADA: '||? WHERE numero_oc=?",
                (motivo, numero_oc))
    # Revert linked solicitud to Pendiente so requester can resubmit
    cur.execute("SELECT numero FROM solicitudes_compra WHERE numero_oc=?", (numero_oc,))
    sol = cur.fetchone()
    if sol:
        cur.execute("UPDATE solicitudes_compra SET estado='Pendiente', observaciones=COALESCE(observaciones,'')||' | RECHAZADA por '||?||': '||? WHERE numero=?",
                    (usuario_actual, motivo, sol[0]))
    # Fetch solicitante nombre + email directo BEFORE closing connection
    _sol_nombre = ''
    _sol_email_directo = ''
    if sol:
        cur.execute('SELECT solicitante, email_solicitante FROM solicitudes_compra WHERE numero=?', (sol[0],))
        _sr = cur.fetchone()
        _sol_nombre = (_sr[0] if _sr else '').lower().strip()
        _sol_email_directo = (_sr[1] if _sr and len(_sr) > 1 else '').strip()
    conn.commit(); conn.close()
    # Email destino: primero el email directo de la solicitud, luego el mapa USER_EMAILS
    _dest_email = _sol_email_directo or USER_EMAILS.get(_sol_nombre, '')
    if sol and _dest_email:
        _asunto_r = f'OC rechazada \u2014 {numero_oc}'
        _body_r = (
            '<html><body style="font-family:Arial,sans-serif;max-width:600px;">'
            '<div style="background:#fee2e2;padding:20px;border-radius:8px;border-left:4px solid #dc2626;">'
            '<h2 style="color:#991b1b;">Orden de compra rechazada</h2>'
            f'<p>La OC <strong>{numero_oc}</strong> asociada a tu solicitud fue rechazada.</p>'
            f'<p><strong>Motivo:</strong> {motivo}</p>'
            '<p>Tu solicitud volvio a estado <em>Pendiente</em>. '
            'Puedes corregirla y reenviarla desde el sistema.</p>'
            '<p style="color:#6b7280;font-size:12px;">Compras HHA \u2014 Espagiria</p>'
            '</div></body></html>'
        )
        _notificar_solicitante_email(_dest_email, _asunto_r, _body_r)
    return jsonify({'ok': True, 'estado': 'Rechazada', 'motivo': motivo})

@bp.route('/api/compras/buscar-remision/<remision_code>')
def buscar_remision(remision_code):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT * FROM ordenes_compra WHERE remision_code=?", (remision_code,))
    oc_row = cur.fetchone()
    oc_cols = [d[0] for d in cur.description] if cur.description else []
    if not oc_row:
        conn.close(); return jsonify({'error': 'No encontrado'}), 404
    oc = dict(zip(oc_cols, oc_row))
    cur.execute("SELECT * FROM ordenes_compra_items WHERE numero_oc=?", (oc['numero_oc'],))
    items = cur.fetchall()
    conn.close()
    return jsonify({'oc': oc, 'items': items})



# ════════════════════════════════════════════
# MEE — Materiales de Envase & Empaque
# ════════════════════════════════════════════

@bp.route('/api/mee', methods=['GET','POST'])
def handle_mee():
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    if request.method == 'POST':
        d = request.get_json()
        if not d.get('codigo') or not d.get('descripcion'):
            conn.close(); return jsonify({'error':'codigo y descripcion requeridos'}), 400
        try:
            cur.execute("""INSERT INTO maestro_mee (codigo,descripcion,categoria,proveedor,fabricante,estado,stock_actual,stock_minimo,unidad,fecha_creacion)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (d['codigo'].upper().strip(), d['descripcion'].strip(),
                 d.get('categoria','Otro'), d.get('proveedor',''), d.get('fabricante',''),
                 'Activo', float(d.get('stock_actual',2000)), float(d.get('stock_minimo',1000)),
                 'und', datetime.now().isoformat()))
            conn.commit(); conn.close()
            return jsonify({'message':f"MEE '{d['codigo']}' creado"}), 201
        except Exception as e:
            conn.close(); return jsonify({'error':str(e)}), 400
    # GET
    cat = request.args.get('cat','')
    q   = request.args.get('q','')
    lim = int(request.args.get('limit',500))
    sql = "SELECT codigo,descripcion,categoria,proveedor,stock_actual,stock_minimo,estado FROM maestro_mee WHERE estado='Activo'"
    params = []
    if cat: sql += " AND categoria=?"; params.append(cat)
    if q:   sql += " AND (codigo LIKE ? OR descripcion LIKE ?)"; params += [f'%{q}%',f'%{q}%']
    sql += " ORDER BY categoria,codigo LIMIT ?"
    params.append(lim)
    cur.execute(sql, params)
    cols=['codigo','descripcion','categoria','proveedor','stock_actual','stock_minimo','estado']
    items=[dict(zip(cols,r)) for r in cur.fetchall()]
    conn.close()
    return jsonify({'items':items})

@bp.route('/api/mee/<codigo>', methods=['GET','PUT'])
def handle_mee_item(codigo):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    if request.method == 'PUT':
        d = request.get_json()
        fields=[]; vals=[]
        for f in ['descripcion','categoria','proveedor','stock_minimo','estado']:
            if f in d: fields.append(f'{f}=?'); vals.append(d[f])
        if not fields: conn.close(); return jsonify({'error':'nada que actualizar'}), 400
        vals.append(codigo)
        cur.execute(f"UPDATE maestro_mee SET {','.join(fields)} WHERE codigo=?", vals)
        conn.commit(); conn.close()
        return jsonify({'message':'actualizado'})
    cur.execute("SELECT * FROM maestro_mee WHERE codigo=?", (codigo,))
    row=cur.fetchone(); conn.close()
    if not row: return jsonify({'error':'no encontrado'}), 404
    cols=[d[0] for d in cur.description]
    return jsonify(dict(zip(cols,row)))

@bp.route('/api/mee/<codigo>/ajuste', methods=['POST'])
def ajuste_mee(codigo):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    d = request.get_json()
    nuevo = float(d.get('nuevo_stock',0))
    obs = d.get('observaciones','Ajuste manual')
    oper = d.get('operador','Sistema')
    cur.execute("SELECT stock_actual FROM maestro_mee WHERE codigo=?", (codigo,))
    row=cur.fetchone()
    if not row: conn.close(); return jsonify({'error':'MEE no encontrado'}), 404
    anterior=row[0]
    diff=nuevo-anterior
    cur.execute("UPDATE maestro_mee SET stock_actual=? WHERE codigo=?", (nuevo,codigo))
    cur.execute("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,lote_ref,observaciones,responsable,fecha) VALUES (?,?,?,?,?,?,?)",
                (codigo,'Ajuste',diff,'ajuste_manual',obs,oper,datetime.now().isoformat()))
    conn.commit(); conn.close()
    return jsonify({'ok':True,'nuevo_stock':nuevo})

@bp.route('/api/movimientos-mee', methods=['GET','POST'])
def handle_movimientos_mee():
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    if request.method == 'POST':
        d = request.get_json()
        cod  = d.get('codigo_mee') or d.get('mee_codigo', '')
        tipo_raw = d.get('tipo','Entrada'); tipo = tipo_raw[0].upper()+tipo_raw[1:].lower() if tipo_raw else 'Entrada'
        cant = float(d.get('cantidad',0))
        ref  = d.get('referencia','')
        obs  = d.get('observaciones','')
        oper = d.get('operador','')
        if not cod or cant<=0: conn.close(); return jsonify({'error':'datos invalidos'}), 400
        cur.execute("SELECT stock_actual FROM maestro_mee WHERE codigo=?", (cod,))
        row=cur.fetchone()
        if not row: conn.close(); return jsonify({'error':'MEE no encontrado'}), 404
        delta = cant if tipo in ('Entrada','entrada') else -cant
        nuevo = row[0]+delta
        if nuevo<0: conn.close(); return jsonify({'error':f'Stock insuficiente (actual: {row[0]})'}), 400
        cur.execute("UPDATE maestro_mee SET stock_actual=? WHERE codigo=?", (nuevo,cod))
        cur.execute("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,lote_ref,observaciones,responsable,fecha) VALUES (?,?,?,?,?,?,?)",
                    (cod,tipo,cant,ref,obs,oper,datetime.now().isoformat()))
        conn.commit(); conn.close()
        return jsonify({'ok':True,'nuevo_stock':nuevo}), 201
    # GET con filtros
    codigo = request.args.get('codigo','')
    tipo   = request.args.get('tipo','')
    limit  = int(request.args.get('limit',50))
    sql = """SELECT m.id,m.mee_codigo,mm.descripcion,m.tipo,m.cantidad,m.lote_ref,m.observaciones,m.responsable,m.fecha
             FROM movimientos_mee m LEFT JOIN maestro_mee mm ON m.mee_codigo=mm.codigo WHERE 1=1"""
    params=[]
    if codigo: sql+=" AND m.mee_codigo=?"; params.append(codigo)
    if tipo:   sql+=" AND m.tipo=?"; params.append(tipo)
    sql+=" ORDER BY m.fecha DESC LIMIT ?"; params.append(limit)
    cur.execute(sql, params)
    cols=['id','mee_codigo','descripcion','tipo','cantidad','lote_ref','observaciones','responsable','fecha']
    rows=[dict(zip(cols,r)) for r in cur.fetchall()]
    conn.close()
    return jsonify({'movimientos':rows})

@bp.route('/api/movimientos-mee/lote', methods=['POST'])
def movimientos_mee_lote():
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    d = request.get_json()
    movs = d.get('movimientos',[])
    oper = d.get('operador','')
    ref  = d.get('referencia','')
    errores=[]
    for m in movs:
        cod=m.get('codigo_mee') or m.get('mee_codigo'); cant=float(m.get('cantidad',0))
        if not cod or cant<=0: continue
        cur.execute("SELECT stock_actual FROM maestro_mee WHERE codigo=?", (cod,))
        row=cur.fetchone()
        if not row: errores.append(f'{cod} no encontrado'); continue
        nuevo=row[0]-cant
        if nuevo<0: nuevo=0
        cur.execute("UPDATE maestro_mee SET stock_actual=? WHERE codigo=?", (nuevo,cod))
        cur.execute("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,lote_ref,observaciones,responsable,fecha) VALUES (?,?,?,?,?,?,?)",
                    (cod,'Salida',cant,ref,'Consumo produccion',oper,datetime.now().isoformat()))
    conn.commit(); conn.close()
    if errores: return jsonify({'ok':True,'advertencias':errores})
    return jsonify({'ok':True})

@bp.route('/api/alertas-mee', methods=['GET'])
def alertas_mee():
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("""SELECT codigo,descripcion,categoria,proveedor,stock_actual,stock_minimo
                   FROM maestro_mee WHERE estado='Activo' AND stock_actual < stock_minimo
                   ORDER BY (stock_actual - stock_minimo) ASC""")
    cols=['codigo','descripcion','categoria','proveedor','stock_actual','stock_minimo']
    alertas=[dict(zip(cols,r)) for r in cur.fetchall()]
    conn.close()
    return jsonify({'alertas':alertas,'total':len(alertas)})

# ─── MÓDULO CLIENTES — Rutas ──────────────────────────────────

