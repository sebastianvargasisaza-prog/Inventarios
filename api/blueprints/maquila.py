# blueprints/maquila.py — extraído de index.py (Fase C)
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
from audit_helpers import audit_log
from http_helpers import validate_money
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

bp = Blueprint('maquila', __name__)

# Audit zero-error 2-may-2026: 16 de 17 endpoints estaban sin auth.
# Solo /api/recall/ejecutar tenía chequeo. El resto permitía a CUALQUIER
# request (incluso sin sesión) crear/modificar prospectos, órdenes, recalls
# simulados, y disparar solicitudes a Animus. Audit zero-error encontró.
_MAQUILA_ALLOWED = lambda: set(COMPRAS_USERS) | set(ADMIN_USERS)


@bp.before_request
def _maquila_gate():
    """Gate global · solo aplica a endpoints API.

    /hub-salida (HTML) tiene su propio gate. /api/* requieren login.
    /api/recall/ejecutar requiere ADMIN además (manejado en el endpoint).
    """
    p = request.path
    if not p.startswith('/api/'):
        return None  # endpoints HTML manejan auth localmente
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    u = session.get('compras_user', '')
    if u not in _MAQUILA_ALLOWED():
        return jsonify({'error': 'Acceso restringido'}), 403
    return None


@bp.route('/api/maquila/prospectos', methods=['GET','POST'])
def api_maquila_prospectos():
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        empresa = (d.get('empresa') or '').strip()
        if not empresa:
            return jsonify({'error':'Empresa requerida'}), 400
        # Validar valor_estimado · audit zero-error
        valor_est, err = validate_money(d.get('valor_estimado', 0), allow_zero=True,
                                          field_name='valor_estimado')
        if err:
            return jsonify(err), 400
        c.execute('''INSERT INTO maquila_prospectos
                     (empresa,contacto,email,whatsapp,categoria_producto,etapa,
                      observaciones,valor_estimado_lote,nivel_servicio,
                      kam_asignado,es_incubacion,contacto_referido,creado_por)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (empresa, d.get('contacto',''), d.get('email',''),
                   d.get('telefono',''), d.get('producto_tipo',''),
                   d.get('etapa','Contacto'), d.get('notas',''),
                   valor_est,
                   d.get('nivel_servicio',''),
                   d.get('kam_asignado','Luz'),
                   1 if d.get('es_incubacion') else 0,
                   d.get('contacto_referido',''),
                   session.get('compras_user') or d.get('operador','sistema')))
        pid = c.lastrowid
        try:
            audit_log(c, usuario=session.get('compras_user', 'sistema'),
                      accion='CREAR_PROSPECTO_MAQUILA',
                      tabla='maquila_prospectos', registro_id=pid,
                      despues={'empresa': empresa[:120],
                                'etapa': d.get('etapa','Contacto'),
                                'valor_estimado': valor_est,
                                'kam': d.get('kam_asignado','Luz')},
                      detalle=f"Creó prospecto maquila · {empresa}")
        except Exception:
            pass
        conn.commit()
        return jsonify({'id': pid}), 201
    c.execute('''SELECT id, empresa, contacto, email,
                        COALESCE(whatsapp,'') as telefono,
                        COALESCE(categoria_producto,'') as producto_tipo,
                        etapa,
                        COALESCE(observaciones,'') as notas,
                        COALESCE(valor_estimado_lote,0) as valor_estimado,
                        fecha_creacion as fecha_contacto,
                        COALESCE(nivel_servicio,'') as nivel_servicio,
                        COALESCE(kam_asignado,'Luz') as kam_asignado,
                        COALESCE(es_incubacion,0) as es_incubacion,
                        COALESCE(contacto_referido,'') as contacto_referido
                 FROM maquila_prospectos ORDER BY id DESC''')
    cols=['id','empresa','contacto','email','telefono','producto_tipo',
          'etapa','notas','valor_estimado','fecha_contacto',
          'nivel_servicio','kam_asignado','es_incubacion','contacto_referido']
    rows=[dict(zip(cols,r)) for r in c.fetchall()]
    return jsonify(rows)

@bp.route('/api/maquila/prospectos/<int:pid>', methods=['PATCH'])
def api_maquila_prospecto_patch(pid):
    d = request.json or {}
    conn = get_db(); c = conn.cursor()
    if 'etapa' in d:
        c.execute('UPDATE maquila_prospectos SET etapa=? WHERE id=?', (d['etapa'], pid))
    if 'valor_estimado' in d:
        c.execute('UPDATE maquila_prospectos SET valor_estimado_lote=? WHERE id=?',
                  (float(d['valor_estimado']), pid))
    if 'notas' in d:
        c.execute('UPDATE maquila_prospectos SET observaciones=? WHERE id=?', (d['notas'], pid))
    if 'nivel_servicio' in d:
        c.execute('UPDATE maquila_prospectos SET nivel_servicio=? WHERE id=?', (d['nivel_servicio'], pid))
    if 'kam_asignado' in d:
        c.execute('UPDATE maquila_prospectos SET kam_asignado=? WHERE id=?', (d['kam_asignado'], pid))
    if 'es_incubacion' in d:
        c.execute('UPDATE maquila_prospectos SET es_incubacion=? WHERE id=?', (1 if d['es_incubacion'] else 0, pid))
    conn.commit()
    return jsonify({'ok': True})

@bp.route('/api/maquila/ordenes', methods=['GET','POST'])
def api_maquila_ordenes():
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        empresa = (d.get('empresa') or '').strip()
        producto = (d.get('producto') or '').strip()
        if not empresa or not producto:
            return jsonify({'error':'Empresa y producto requeridos'}), 400
        # Validar batch_size + valor_total
        batch_kg, err = validate_money(d.get('batch_size_kg', 0), allow_zero=True,
                                         max_value=10_000, field_name='batch_size_kg')
        if err:
            return jsonify(err), 400
        valor_total, err = validate_money(d.get('valor_total', 0), allow_zero=True,
                                            field_name='valor_total')
        if err:
            return jsonify(err), 400
        c.execute('''INSERT INTO maquila_ordenes
                     (cliente_nombre,producto,lote_kg,fecha_orden,
                      fecha_entrega_est,estado,precio_lote,observaciones,creado_por)
                     VALUES (?,?,?,?,?,?,?,?,?)''',
                  (empresa, producto, batch_kg,
                   d.get('fecha_inicio',''), d.get('fecha_entrega',''),
                   d.get('estado','Cotizacion'), valor_total,
                   d.get('observaciones',''),
                   session.get('compras_user') or d.get('operador','sistema')))
        oid = c.lastrowid
        try:
            audit_log(c, usuario=session.get('compras_user', 'sistema'),
                      accion='CREAR_ORDEN_MAQUILA',
                      tabla='maquila_ordenes', registro_id=oid,
                      despues={'cliente': empresa[:120], 'producto': producto[:120],
                                'batch_kg': batch_kg, 'valor_total': valor_total,
                                'estado': d.get('estado','Cotizacion')},
                      detalle=f"Orden maquila · {empresa} · {producto} · "
                              f"{batch_kg:.0f}kg · ${valor_total/1_000_000:.1f}M")
        except Exception:
            pass
        conn.commit()
        return jsonify({'id': oid}), 201
    c.execute('''SELECT id,
                        COALESCE(cliente_nombre,'') as empresa,
                        producto,
                        COALESCE(lote_kg,0) as batch_size_kg,
                        COALESCE(fecha_orden,'') as fecha_inicio,
                        COALESCE(fecha_entrega_est,'') as fecha_entrega,
                        estado,
                        COALESCE(precio_lote,0) as valor_total,
                        COALESCE(observaciones,'') as observaciones,
                        fecha_creacion
                 FROM maquila_ordenes ORDER BY fecha_creacion DESC''')
    cols=['id','empresa','producto','batch_size_kg','fecha_inicio','fecha_entrega',
          'estado','valor_total','observaciones','fecha_creacion']
    rows=[dict(zip(cols,r)) for r in c.fetchall()]
    return jsonify(rows)

@bp.route('/api/maquila/ordenes/<int:oid>', methods=['PATCH'])
def api_maquila_orden_patch(oid):
    d = request.json or {}
    conn = get_db(); c = conn.cursor()
    if 'estado' in d:
        c.execute('UPDATE maquila_ordenes SET estado=? WHERE id=?', (d['estado'], oid))
    conn.commit()
    return jsonify({'ok': True})

@bp.route('/api/maquila/ordenes/<int:oid>/facturar', methods=['POST'])
def api_maquila_facturar(oid):
    """Genera una factura de servicio de maquila usando el mismo motor de
    contabilidad. Cierra el Gap 7: maquila ahora alimenta facturas y por
    consiguiente flujo_ingresos cuando se cobre.

    Body opcional:
      iva_pct (default 19), descuento (default 0), notas, fecha_vencimiento
    """
    from datetime import date
    d = request.json or {}
    conn = get_db(); c = conn.cursor()

    orden = c.execute("SELECT * FROM maquila_ordenes WHERE id=?", (oid,)).fetchone()
    if not orden:
        return jsonify({'error': 'Orden de maquila no encontrada'}), 404
    orden = dict(orden)

    # Verificar que no este ya facturada
    existe = c.execute(
        "SELECT numero FROM facturas WHERE numero_pedido=? AND tipo='FM'",
        (f"MAQ-{oid}",)
    ).fetchone()
    if existe:
        return jsonify({
            'ok': True, 'ya_facturada': True,
            'numero_factura': existe[0],
            'mensaje': f'Ya existe factura {existe[0]} para esta orden'
        }), 200

    # Numeracion fiscal (importar funcion de contabilidad)
    from blueprints.contabilidad import _next_numero
    empresa_emisora = (orden.get('empresa') or 'Espagiria').strip() or 'Espagiria'
    # Para servicios de maquila usamos prefijo 'FM' (Factura Maquila) para
    # diferenciar de facturas de venta de productos terminados ('FV')
    numero = _next_numero(conn, empresa_emisora, tipo='FM')

    # Datos base de la factura (schema real: precio_lote es el valor a facturar)
    cliente_nombre = orden.get('cliente_nombre') or orden.get('proveedor') or 'Sin cliente'
    cliente_nit = orden.get('cliente_nit') or ''
    valor_servicio = float(orden.get('precio_lote')
                            or orden.get('valor_total') or 0)
    iva_pct = float(d.get('iva_pct', 19))
    descuento = float(d.get('descuento', 0))
    base_iva = valor_servicio - descuento
    iva_valor = round(base_iva * iva_pct / 100, 2)
    total = base_iva + iva_valor
    hoy = date.today().isoformat()
    fecha_venc = d.get('fecha_vencimiento', '')
    notas = d.get('notas') or f'Servicio de maquila — orden #{oid}'

    c.execute("""
        INSERT INTO facturas
        (numero, tipo, numero_pedido, cliente_nombre, cliente_nit,
         empresa, fecha_emision, fecha_vencimiento, subtotal, descuento,
         iva_pct, iva_valor, total, estado, notas, creado_por)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (numero, 'FM', f'MAQ-{oid}', cliente_nombre, cliente_nit,
          empresa_emisora, hoy, fecha_venc, valor_servicio, descuento,
          iva_pct, iva_valor, total, 'Emitida', notas,
          session.get('compras_user', 'sistema')))

    # Item unico: servicio de maquila (schema real: producto/lote_kg)
    try:
        producto_desc = (orden.get('producto') or orden.get('producto_tipo')
                         or 'producto cosmetico')
        kg = orden.get('lote_kg') or orden.get('batch_size_kg') or 0
        c.execute("""
            INSERT INTO facturas_items
            (numero_factura, sku, descripcion, cantidad, precio_unitario, subtotal)
            VALUES (?,?,?,?,?,?)
        """, (numero, f'MAQ-{oid}',
              f"Maquila: {producto_desc} ({kg} kg)",
              1, valor_servicio, valor_servicio))
    except sqlite3.OperationalError:
        pass  # tabla items puede no existir en instancias muy viejas

    # Actualizar orden con referencia a la factura
    c.execute("""UPDATE maquila_ordenes
                 SET estado=COALESCE(estado,'En proceso')
                 WHERE id=?""", (oid,))

    conn.commit()

    return jsonify({
        'ok': True,
        'numero_factura': numero,
        'total': total,
        'mensaje': f'Factura {numero} generada por ${total:,.0f} COP'
    }), 201


@bp.route('/api/maquila/cotizar', methods=['POST'])
def api_maquila_cotizar():
    d = request.json or {}
    conn = get_db(); c = conn.cursor()
    c.execute('''INSERT INTO maquila_cotizaciones
                 (empresa,producto_tipo,batch_size_kg,costo_mp,costo_proceso,margen_pct,valor_total,usuario)
                 VALUES (?,?,?,?,?,?,?,?)''',
              (d.get('empresa',''), d.get('producto_tipo',''),
               float(d.get('batch_size_kg',0)), float(d.get('costo_mp',0)),
               float(d.get('costo_proceso',0)), float(d.get('margen_pct',0)),
               float(d.get('valor_total',0)),
               session.get('compras_user') or d.get('operador','sistema')))
    conn.commit(); cid=c.lastrowid
    return jsonify({'id': cid}), 201

@bp.route('/api/maquila/kpis', methods=['GET'])
def api_maquila_kpis():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM maquila_prospectos WHERE etapa NOT IN ('Activo','Perdido') AND estado='Activo'")
    prosp = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM maquila_ordenes WHERE estado IN ('Cotizacion','Orden','En proceso','Produccion')")
    ords = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(valor_estimado_lote),0) FROM maquila_prospectos WHERE estado='Activo'")
    valor = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM maquila_prospectos WHERE etapa IN ('Negociacion','Cierre') AND estado='Activo'")
    cierre = c.fetchone()[0]
    return jsonify({'prospectos_activos':prosp,'ordenes_activas':ords,
                    'valor_pipeline':valor,'en_cierre':cierre})

# ═══════════════════════════════════════════════════════
#  ÁNIMUS — Auto Producción + Recall Engine COC-PRO-016
# ═══════════════════════════════════════════════════════
@bp.route('/api/animus/alertas-stock', methods=['GET'])
def animus_alertas_stock():
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT sku, descripcion, empresa,
                        SUM(unidades_disponible) as disponible,
                        stock_minimo_ud, dias_reposicion, precio_base
                 FROM stock_pt
                 WHERE empresa='ANIMUS' AND estado='Disponible'
                 GROUP BY sku
                 HAVING disponible < stock_minimo_ud AND stock_minimo_ud > 0
                 ORDER BY (disponible*1.0/NULLIF(stock_minimo_ud,0)) ASC""")
    cols=['sku','descripcion','empresa','disponible','stock_minimo_ud','dias_reposicion','precio_base']
    alertas=[dict(zip(cols,r)) for r in c.fetchall()]
    # Check pending solicitudes
    for a in alertas:
        c.execute("""SELECT COUNT(*) FROM solicitudes_produccion
                     WHERE sku=? AND estado='Pendiente'""", (a['sku'],))
        a['solicitud_pendiente'] = c.fetchone()[0] > 0
        a['deficit'] = max(0, a['stock_minimo_ud'] - a['disponible'])
        a['cobertura_dias'] = round(a['disponible'] / max(a['stock_minimo_ud']/30, 1), 0)
    return jsonify({'alertas': alertas, 'total': len(alertas)})

@bp.route('/api/animus/solicitar-produccion', methods=['POST'])
def animus_solicitar_produccion():
    d = request.json or {}
    sku = d.get('sku','').strip()
    if not sku:
        return jsonify({'error': 'SKU requerido'}), 400
    conn = get_db(); c = conn.cursor()
    # Get current stock info
    c.execute("SELECT descripcion, SUM(unidades_disponible), stock_minimo_ud FROM stock_pt WHERE sku=? AND empresa='ANIMUS' AND estado='Disponible' GROUP BY sku", (sku,))
    row = c.fetchone()
    if not row:
        return jsonify({'error': 'SKU no encontrado en stock ANIMUS'}), 404
    desc, disponible, minimo = row[0], row[1] or 0, row[2] or 0
    # Check if there's already a pending solicitud
    c.execute("SELECT id FROM solicitudes_produccion WHERE sku=? AND estado='Pendiente'", (sku,))
    existente = c.fetchone()
    if existente:
        return jsonify({'warning': 'Ya existe una solicitud pendiente para este SKU', 'id': existente[0]}), 200
    unidades = int(d.get('unidades', max(minimo - disponible, minimo)))
    prioridad = 'Alta' if disponible == 0 else ('Normal' if disponible > minimo * 0.5 else 'Alta')
    c.execute("""INSERT INTO solicitudes_produccion
                 (sku, descripcion, unidades_solicitadas, motivo, estado,
                  prioridad, fecha_requerida, solicitado_por, observaciones)
                 VALUES (?,?,?,?,?,?,?,?,?)""",
              (sku, desc, unidades,
               f'Stock bajo: {disponible} uds disponibles (mínimo {minimo})',
               'Pendiente', prioridad,
               d.get('fecha_requerida',''),
               session.get('compras_user') or d.get('operador','sistema'),
               d.get('observaciones','')))
    sid = c.lastrowid
    # Audit log
    c.execute("""INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                 VALUES (?,?,?,?,?,?,datetime('now'))""",
              (session.get('compras_user','sistema'), 'SOLICITUD_PRODUCCION',
               'solicitudes_produccion', str(sid),
               f'{sku} — {unidades} uds — Stock: {disponible}/{minimo}',
               request.remote_addr))
    conn.commit()
    return jsonify({'id': sid, 'sku': sku, 'unidades': unidades, 'prioridad': prioridad}), 201

@bp.route('/api/animus/solicitudes-produccion', methods=['GET'])
def animus_solicitudes_produccion():
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT id,sku,descripcion,unidades_solicitadas,motivo,
                        estado,prioridad,fecha_solicitud,fecha_requerida,
                        solicitado_por,observaciones
                 FROM solicitudes_produccion ORDER BY
                 CASE prioridad WHEN 'Urgente' THEN 1 WHEN 'Alta' THEN 2 ELSE 3 END,
                 fecha_solicitud DESC""")
    cols=['id','sku','descripcion','unidades','motivo','estado','prioridad',
          'fecha_solicitud','fecha_requerida','solicitado_por','observaciones']
    rows=[dict(zip(cols,r)) for r in c.fetchall()]
    return jsonify(rows)

@bp.route('/api/animus/solicitudes-produccion/<int:sid>', methods=['PATCH'])
def animus_update_solicitud(sid):
    d = request.json or {}
    conn = get_db(); c = conn.cursor()
    if 'estado' in d:
        c.execute("UPDATE solicitudes_produccion SET estado=? WHERE id=?", (d['estado'], sid))
    conn.commit()
    return jsonify({'ok': True})

@bp.route('/api/stock-pt/<sku>/reorden', methods=['POST'])
def actualizar_reorden_pt(sku):
    d = request.json or {}
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE stock_pt SET stock_minimo_ud=?, dias_reposicion=? WHERE sku=?",
              (int(d.get('stock_minimo_ud', 0)),
               int(d.get('dias_reposicion', 15)), sku))
    conn.commit()
    return jsonify({'ok': True})

# ── Recall Engine COC-PRO-016 ──────────────────────────────────────────
@bp.route('/api/recall/simular/<path:lote_pt>', methods=['GET'])
def recall_simular(lote_pt):
    import urllib.parse; lote_pt = urllib.parse.unquote(lote_pt)
    conn = get_db(); c = conn.cursor()
    # Find all dispatch items with this lote_pt
    c.execute("""SELECT di.numero_despacho, di.sku, di.descripcion,
                        di.cantidad, di.lote_pt,
                        d.fecha, d.estado,
                        cl.nombre as cliente, cl.email, cl.telefono
                 FROM despachos_items di
                 LEFT JOIN despachos d ON di.numero_despacho=d.numero
                 LEFT JOIN clientes cl ON d.cliente_id=cl.id
                 WHERE di.lote_pt=?
                 ORDER BY d.fecha DESC""", (lote_pt,))
    cols=['despacho','sku','descripcion','cantidad','lote_pt','fecha','estado_desp',
          'cliente','email','telefono']
    items=[dict(zip(cols,r)) for r in c.fetchall()]
    # Aggregates
    total_uds = sum(i['cantidad'] for i in items)
    clientes_afectados = list({i['cliente'] for i in items if i['cliente']})
    despachos_afectados = list({i['despacho'] for i in items})
    # Also check stock_pt (units still in warehouse)
    c.execute("SELECT SUM(unidades_disponible) FROM stock_pt WHERE lote_produccion=? AND estado='Disponible'", (lote_pt,))
    en_bodega = c.fetchone()[0] or 0
    return jsonify({
        'lote_pt': lote_pt,
        'impacto': {
            'unidades_despachadas': total_uds,
            'unidades_en_bodega': en_bodega,
            'total_afectadas': total_uds + en_bodega,
            'despachos': len(despachos_afectados),
            'clientes': len(clientes_afectados)
        },
        'despachos_detalle': items,
        'clientes_afectados': clientes_afectados,
        'alerta': 'ALTO' if (total_uds + en_bodega) > 500 else ('MEDIO' if (total_uds + en_bodega) > 100 else 'BAJO')
    })

@bp.route('/api/recall/ejecutar', methods=['POST'])
def recall_ejecutar():
    if 'compras_user' not in session or session.get('compras_user') not in ADMIN_USERS:
        return jsonify({'error': 'Solo administradores pueden ejecutar un recall'}), 401
    d = request.json or {}
    lote_pt = d.get('lote_pt','').strip()
    motivo  = d.get('motivo','').strip()
    if not lote_pt or not motivo:
        return jsonify({'error': 'lote_pt y motivo son requeridos'}), 400
    conn = get_db(); c = conn.cursor()
    # Count impact
    c.execute("SELECT COUNT(*), SUM(di.cantidad) FROM despachos_items di WHERE di.lote_pt=?", (lote_pt,))
    n_desp, total_uds = c.fetchone(); total_uds = total_uds or 0
    # Block remaining stock in bodega
    c.execute("UPDATE stock_pt SET estado='Recall' WHERE lote_produccion=?", (lote_pt,))
    bloqueadas = c.rowcount
    # Log to recall_log
    c.execute("""INSERT INTO recall_log
                 (lote_pt,sku,motivo,total_despachos,total_unidades,ejecutado_por,estado)
                 VALUES (?,?,?,?,?,?,?)""",
              (lote_pt, d.get('sku',''), motivo,
               n_desp or 0, total_uds,
               session['compras_user'], 'Ejecutado'))
    rid = c.lastrowid
    # Audit log — immutable
    c.execute("""INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                 VALUES (?,?,?,?,?,?,datetime('now'))""",
              (session['compras_user'], 'RECALL_EJECUTADO', 'stock_pt',
               str(rid),
               f'Lote {lote_pt} — Motivo: {motivo} — {total_uds} uds en {n_desp} despachos — {bloqueadas} lotes bloqueados en bodega',
               request.remote_addr))
    conn.commit()
    return jsonify({
        'recall_id': rid,
        'lote_pt': lote_pt,
        'unidades_despachadas': total_uds,
        'despachos': n_desp,
        'lotes_bloqueados_bodega': bloqueadas,
        'estado': 'Ejecutado'
    }), 201

# ─── Panel de Recepcion — rutas standalone ────────────────────────────────────

@bp.route('/hub-salida')
def hub_salida_page():
    if 'compras_user' not in session:
        return redirect('/login?next=/hub-salida')
    return Response(SALIDA_HTML, mimetype='text/html')

@bp.route('/api/hub-salida/pedidos-pendientes')
def hub_pedidos_pendientes():
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT p.numero, p.cliente_id, cl.nombre as cliente, p.fecha, p.estado, p.valor_total
                 FROM pedidos p
                 LEFT JOIN clientes cl ON p.cliente_id = cl.id
                 WHERE p.estado IN ('Confirmado','En preparacion','En Produccion','Aprobado','Listo')
                 ORDER BY p.fecha DESC""")
    cols = ['numero','cliente_id','cliente','fecha','estado','valor_total']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify({'pedidos': rows})

@bp.route('/api/hub-salida/pedido/<numero>')
def hub_pedido_detalle(numero):
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT p.numero, p.cliente_id, cl.nombre as cliente, p.fecha, p.estado, p.valor_total
                 FROM pedidos p LEFT JOIN clientes cl ON p.cliente_id=cl.id
                 WHERE p.numero=?""", (numero,))
    row = c.fetchone()
    if not row:
        return jsonify({'error': 'Pedido no encontrado'}), 404
    ped = dict(zip(['numero','cliente_id','cliente','fecha','estado','valor_total'], row))
    c.execute("""SELECT sku, descripcion, cantidad, precio_unitario
                 FROM pedidos_items WHERE numero_pedido=?""", (numero,))
    ped['items'] = [dict(zip(['sku','descripcion','cantidad','precio_unitario'], r)) for r in c.fetchall()]
    return jsonify(ped)

@bp.route('/api/hub-salida/stock/<sku>')
def hub_stock_sku(sku):
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT lote_pt, unidades_disponible, fecha_produccion
                 FROM stock_pt WHERE sku=? AND estado='Disponible' AND unidades_disponible>0
                 ORDER BY fecha_produccion ASC""", (sku,))
    lotes = [{'lote': r[0], 'disponible': r[1], 'fecha': r[2]} for r in c.fetchall()]
    total = sum(l['disponible'] for l in lotes)
    return jsonify({'sku': sku, 'total': total, 'lotes': lotes})

@bp.route('/api/hub-salida/despachar', methods=['POST'])
def hub_despachar():
    d = request.get_json() or {}
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(numero,10) AS INTEGER)),0) FROM despachos WHERE numero LIKE ?",
              (f"DSP-{datetime.now().strftime('%Y')}-%",))
    n = (c.fetchone()[0] or 0) + 1
    numero = f"DSP-{datetime.now().strftime('%Y')}-{n:04d}"
    c.execute("""INSERT INTO despachos (numero,numero_pedido,cliente_id,fecha,operador,observaciones,estado)
                 VALUES (?,?,?,datetime('now'),?,?,?)""",
              (numero, d.get('numero_pedido',''), d.get('cliente_id'),
               session.get('compras_user','sistema'), d.get('observaciones',''), 'Completado'))
    for it in (d.get('items') or []):
        if int(it.get('cantidad',0)) <= 0:
            continue
        c.execute("""INSERT INTO despachos_items (numero_despacho,sku,descripcion,lote_pt,cantidad,precio_unitario)
                     VALUES (?,?,?,?,?,?)""",
                  (numero, it.get('sku',''), it.get('descripcion',''), it.get('lote_pt',''),
                   int(it.get('cantidad',0)), float(it.get('precio_unitario',0))))
        lote = it.get('lote_pt','')
        if lote:
            c.execute("""UPDATE stock_pt SET unidades_disponible=MAX(0,unidades_disponible-?)
                         WHERE sku=? AND lote_pt=?""",
                      (int(it.get('cantidad',0)), it.get('sku',''), lote))
        else:
            c.execute("""UPDATE stock_pt SET unidades_disponible=MAX(0,unidades_disponible-?)
                         WHERE sku=? AND unidades_disponible>0
                         ORDER BY fecha_produccion ASC LIMIT 1""",
                      (int(it.get('cantidad',0)), it.get('sku','')))
    num_ped = d.get('numero_pedido','')
    if num_ped:
        c.execute("UPDATE pedidos SET estado='Despachado',fecha_despacho=datetime('now') WHERE numero=?", (num_ped,))
    conn.commit()
    return jsonify({'message': f'Despacho {numero} registrado', 'numero': numero}), 201

