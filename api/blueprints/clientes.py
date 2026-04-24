# blueprints/clientes.py — extraído de index.py (Fase C)
import os
import json
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, CLIENTES_ACCESS
from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec, sin_acceso_html
from templates_py.clientes_html import CLIENTES_HTML

bp = Blueprint('clientes', __name__)


@bp.route('/clientes')
def clientes_page():
    if 'compras_user' not in session:
        return redirect('/login?next=/clientes')
    u = session.get('compras_user', '')
    if u not in CLIENTES_ACCESS:
        return Response(sin_acceso_html('Clientes'), mimetype='text/html')
    return Response(CLIENTES_HTML, mimetype='text/html')

@bp.route('/api/clientes', methods=['GET','POST'])
def handle_clientes():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('nombre'):
            conn.close(); return jsonify({'error': 'Nombre requerido'}), 400
        c.execute("SELECT COUNT(*) FROM clientes"); n = (c.fetchone()[0] or 0) + 1
        codigo = d.get('codigo') or f"CLI-{n:03d}"
        try:
            c.execute("""INSERT INTO clientes
                         (codigo,nombre,empresa,tipo,contacto,email,telefono,nit,
                          condiciones_pago,descuento_pct,activo,fecha_creacion,observaciones,ciudad,
                          categoria_profesional,canal_captacion,redes_sociales,notas_seguimiento)
                         VALUES (?,?,?,?,?,?,?,?,?,?,1,datetime('now'),?,?,?,?,?,?)""",
                      (codigo, d['nombre'], d.get('empresa','ANIMUS'), d.get('tipo','Distribuidor'),
                       d.get('contacto',''), d.get('email',''), d.get('telefono',''),
                       d.get('nit',''), d.get('condiciones_pago','Pago anticipado'),
                       float(d.get('descuento_pct',0)), d.get('observaciones',''), d.get('ciudad',''),
                       d.get('categoria_profesional',''), d.get('canal_captacion',''),
                       json.dumps(d.get('redes_sociales',{})), d.get('notas_seguimiento','')))
            conn.commit(); conn.close()
            return jsonify({'message': f"Cliente creado", 'codigo': codigo}), 201
        except Exception as e:
            conn.close(); return jsonify({'error': str(e)}), 400
    empresa_fil = request.args.get('empresa')
    q_filter = "AND cl.empresa=?" if empresa_fil else ""
    q_params = (empresa_fil,) if empresa_fil else ()
    c.execute(f"""SELECT cl.id, cl.codigo, cl.nombre, cl.empresa, cl.tipo, cl.contacto, cl.email,
                        cl.telefono, cl.condiciones_pago, cl.descuento_pct, cl.activo, cl.fecha_creacion,
                        COUNT(p.numero) as total_pedidos,
                        COALESCE(SUM(p.valor_total),0) as facturado_total,
                        MAX(p.fecha) as ultimo_pedido,
                        COALESCE(cl.nivel_aliado,'Ingreso') as nivel_aliado,
                        COALESCE(cl.semaforo,'verde') as semaforo,
                        COALESCE(cl.fecha_vinculacion,'') as fecha_vinculacion,
                        COALESCE(cl.ciudad,'') as ciudad,
                        COALESCE(cl.categoria_profesional,'') as categoria_profesional,
                        COALESCE(cl.canal_captacion,'') as canal_captacion,
                        COALESCE(cl.redes_sociales,'{}') as redes_sociales,
                        COALESCE(cl.notas_seguimiento,'') as notas_seguimiento
                 FROM clientes cl
                 LEFT JOIN pedidos p ON p.cliente_id = cl.id
                 WHERE cl.activo=1 {q_filter}
                 GROUP BY cl.id
                 ORDER BY cl.nombre""", q_params)
    cols = ['id','codigo','nombre','empresa','tipo','contacto','email','telefono',
            'condiciones_pago','descuento_pct','activo','fecha_creacion',
            'total_pedidos','facturado_total','ultimo_pedido',
            'nivel_aliado','semaforo','fecha_vinculacion','ciudad',
            'categoria_profesional','canal_captacion','redes_sociales','notas_seguimiento']
    clientes = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close(); return jsonify({'clientes': clientes})

@bp.route('/api/clientes/<int:cid>', methods=['GET','PUT'])
def handle_cliente_detalle(cid):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'PUT':
        d = request.json or {}
        campos = ['nombre','empresa','tipo','contacto','email','telefono','nit','condiciones_pago','descuento_pct','observaciones','activo']
        sets = []; vals = []
        for campo in campos:
            if campo in d: sets.append(f"{campo}=?"); vals.append(d[campo])
        if sets:
            vals.append(cid)
            c.execute(f"UPDATE clientes SET {','.join(sets)} WHERE id=?", vals)
            conn.commit()
        conn.close(); return jsonify({'message': 'Cliente actualizado'})
    c.execute("SELECT id,codigo,nombre,empresa,tipo,contacto,email,telefono,nit,condiciones_pago,descuento_pct,activo,fecha_creacion,observaciones FROM clientes WHERE id=?", (cid,))
    row = c.fetchone(); conn.close()
    if not row: return jsonify({'error': 'No encontrado'}), 404
    cols = ['id','codigo','nombre','empresa','tipo','contacto','email','telefono','nit','condiciones_pago','descuento_pct','activo','fecha_creacion','observaciones']
    return jsonify({'cliente': dict(zip(cols, row))})

@bp.route('/api/clientes/<int:cid>/historial')
def handle_cliente_historial(cid):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT numero,fecha,estado,valor_total,fecha_despacho FROM pedidos WHERE cliente_id=? ORDER BY fecha DESC LIMIT 50", (cid,))
    cols = ['numero','fecha','estado','valor_total','fecha_despacho']
    pedidos = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close(); return jsonify({'pedidos': pedidos})

@bp.route('/api/clientes/<int:cid>/stats')
def handle_cliente_stats(cid):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT COUNT(*), COALESCE(SUM(valor_total),0), MAX(fecha) FROM pedidos WHERE cliente_id=?", (cid,))
    row = c.fetchone(); conn.close()
    return jsonify({'total_pedidos': row[0], 'valor_total': row[1], 'ultimo_pedido': row[2]})

@bp.route('/api/clientes/alertas-recompra')
def clientes_alertas_recompra():
    """Clientes con >N dias sin pedido — churn detection."""
    umbral = int(request.args.get('dias', 75))
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT cl.id, cl.nombre, cl.tipo, cl.email, cl.telefono,
                        MAX(p.fecha) as ultimo_pedido,
                        COUNT(p.numero) as total_pedidos,
                        COALESCE(SUM(p.valor_total),0) as valor_total
                 FROM clientes cl
                 LEFT JOIN pedidos p ON p.cliente_id = cl.id
                 WHERE cl.activo=1
                 GROUP BY cl.id, cl.nombre
                 HAVING ultimo_pedido IS NOT NULL
                 ORDER BY ultimo_pedido ASC""")
    hoy = datetime.now()
    resultado = []
    for r in c.fetchall():
        cid, nombre, tipo, email, tel, ult, tot_ped, val = r
        try:
            dias = (hoy - datetime.fromisoformat(ult[:19])).days
        except Exception:
            dias = 0
        if dias >= umbral:
            resultado.append({
                'id': cid, 'nombre': nombre, 'tipo': tipo,
                'email': email, 'telefono': tel,
                'ultimo_pedido': (ult or '')[:10], 'dias_sin_pedido': dias,
                'total_pedidos': tot_ped, 'valor_total': val,
                'nivel': 'critico' if dias >= 120 else 'atencion'
            })
    conn.close()
    return jsonify({'alertas': resultado, 'umbral_dias': umbral})


@bp.route('/api/clientes/<int:cid>/ficha360')
def cliente_ficha_360(cid):
    """Cliente 360: datos + stats + historial pedidos recientes + items."""
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT id, codigo, nombre, empresa, tipo, contacto, email,
                        telefono, nit, condiciones_pago, descuento_pct, observaciones, fecha_creacion
                 FROM clientes WHERE id=? AND activo=1""", (cid,))
    row = c.fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'Cliente no encontrado'}), 404
    cols_cli = ['id','codigo','nombre','empresa','tipo','contacto','email',
                'telefono','nit','condiciones_pago','descuento_pct','observaciones','fecha_creacion']
    cliente = dict(zip(cols_cli, row))
    # Stats
    c.execute("SELECT COUNT(*), COALESCE(SUM(valor_total),0), MAX(fecha), MIN(fecha) FROM pedidos WHERE cliente_id=?", (cid,))
    s = c.fetchone()
    total_ped, valor_total, ultimo_ped, primer_ped = s[0] or 0, s[1] or 0, s[2], s[3]
    hoy = datetime.now()
    dias_sin_pedido = None
    if ultimo_ped:
        try: dias_sin_pedido = (hoy - datetime.fromisoformat(ultimo_ped[:19])).days
        except Exception: pass
    # Ticket promedio
    ticket_prom = round(valor_total / total_ped, 0) if total_ped > 0 else 0
    # Pedidos recientes (last 10)
    c.execute("""SELECT numero, fecha, estado, valor_total, fecha_entrega_est, fecha_despacho
                 FROM pedidos WHERE cliente_id=? ORDER BY fecha DESC LIMIT 10""", (cid,))
    ped_cols = ['numero','fecha','estado','valor_total','fecha_entrega_est','fecha_despacho']
    pedidos_recientes = [dict(zip(ped_cols, r)) for r in c.fetchall()]
    # Top SKUs comprados
    c.execute("""SELECT pi.sku, pi.descripcion, SUM(pi.cantidad) as tot_uds, COUNT(DISTINCT p.numero) as en_pedidos
                 FROM pedidos_items pi JOIN pedidos p ON pi.numero_pedido=p.numero
                 WHERE p.cliente_id=?
                 GROUP BY pi.sku, pi.descripcion
                 ORDER BY tot_uds DESC LIMIT 10""", (cid,))
    top_skus = [{'sku':r[0],'descripcion':r[1],'unidades':r[2],'pedidos':r[3]} for r in c.fetchall()]
    conn.close()
    return jsonify({
        'cliente': cliente,
        'stats': {
            'total_pedidos': total_ped, 'valor_total': valor_total,
            'ticket_promedio': ticket_prom, 'ultimo_pedido': (ultimo_ped or '')[:10],
            'primer_pedido': (primer_ped or '')[:10], 'dias_sin_pedido': dias_sin_pedido
        },
        'pedidos_recientes': pedidos_recientes,
        'top_skus': top_skus
    })




@bp.route('/api/aliados/analytics')
def aliados_analytics():
    """Ventas mensuales por aliado, frecuencia de compra y top SKUs."""
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    try:
        hace6m = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

        # ── Ventas netas por aliado por mes (últimos 6 meses) ────────────────
        c.execute("""
            SELECT cl.id, cl.nombre,
                   strftime('%Y-%m', p.fecha) as mes,
                   COALESCE(SUM(p.valor_total),0) as ventas,
                   COUNT(p.numero) as pedidos
            FROM clientes cl
            JOIN pedidos p ON p.cliente_id=cl.id
            WHERE cl.activo=1 AND cl.empresa='ANIMUS'
              AND p.estado NOT IN ('Cancelado','Borrador')
              AND p.fecha >= ?
            GROUP BY cl.id, mes
            ORDER BY cl.nombre, mes
        """, (hace6m,))
        ventas_mes = [dict(zip(['id','nombre','mes','ventas','pedidos'], r)) for r in c.fetchall()]

        # ── Frecuencia de compra por aliado ──────────────────────────────────
        c.execute("""
            SELECT cl.id, cl.nombre, GROUP_CONCAT(p.fecha ORDER BY p.fecha ASC) as fechas
            FROM clientes cl
            JOIN pedidos p ON p.cliente_id=cl.id
            WHERE cl.activo=1 AND cl.empresa='ANIMUS'
              AND p.estado NOT IN ('Cancelado','Borrador')
            GROUP BY cl.id
        """)
        frecuencia = []
        for row in c.fetchall():
            cid_, nombre_, fechas_str = row
            fechas = [f[:10] for f in (fechas_str or '').split(',') if f]
            if len(fechas) >= 2:
                gaps = []
                for i in range(1, len(fechas)):
                    try:
                        d1 = datetime.strptime(fechas[i-1], '%Y-%m-%d')
                        d2 = datetime.strptime(fechas[i], '%Y-%m-%d')
                        gaps.append((d2-d1).days)
                    except Exception:
                        pass
                avg_dias = round(sum(gaps)/len(gaps), 0) if gaps else None
            else:
                avg_dias = None
            frecuencia.append({
                'id': cid_, 'nombre': nombre_,
                'total_pedidos': len(fechas),
                'frecuencia_dias': avg_dias,
                'primer_pedido': fechas[0] if fechas else None,
                'ultimo_pedido': fechas[-1] if fechas else None
            })

        # ── Top SKUs por aliado ───────────────────────────────────────────────
        c.execute("""
            SELECT p.cliente_id, cl.nombre,
                   pi.sku, pi.descripcion,
                   SUM(pi.cantidad) as uds,
                   SUM(pi.subtotal) as revenue
            FROM pedidos_items pi
            JOIN pedidos p ON pi.numero_pedido=p.numero
            JOIN clientes cl ON p.cliente_id=cl.id
            WHERE cl.activo=1 AND cl.empresa='ANIMUS'
              AND p.estado NOT IN ('Cancelado','Borrador')
            GROUP BY p.cliente_id, pi.sku
            ORDER BY p.cliente_id, revenue DESC
        """)
        top_skus_raw = c.fetchall()
        top_skus = {}
        for row in top_skus_raw:
            cid_ = row[0]
            if cid_ not in top_skus:
                top_skus[cid_] = []
            if len(top_skus[cid_]) < 5:
                top_skus[cid_].append({
                    'sku': row[2], 'descripcion': row[3],
                    'uds': row[4], 'revenue': round(row[5] or 0, 0)
                })

        # ── Resumen por aliado (para tabla principal) ─────────────────────────
        c.execute("""
            SELECT cl.id, cl.nombre, cl.codigo, cl.nivel_aliado, cl.semaforo,
                   cl.categoria_profesional, cl.canal_captacion,
                   cl.redes_sociales, cl.ciudad, cl.notas_seguimiento,
                   COALESCE(SUM(p.valor_total),0) as total_facturado,
                   COALESCE(SUM(CASE WHEN p.fecha >= ? THEN p.valor_total ELSE 0 END),0) as mes_actual,
                   MAX(p.fecha) as ultimo_pedido,
                   COUNT(p.numero) as total_pedidos
            FROM clientes cl
            LEFT JOIN pedidos p ON p.cliente_id=cl.id
              AND p.estado NOT IN ('Cancelado','Borrador')
            WHERE cl.activo=1 AND cl.empresa='ANIMUS'
            GROUP BY cl.id
            ORDER BY total_facturado DESC
        """, ((datetime.now().replace(day=1)).strftime("%Y-%m-%d"),))
        cols_res = ['id','nombre','codigo','nivel_aliado','semaforo',
                    'categoria_profesional','canal_captacion','redes_sociales',
                    'ciudad','notas_seguimiento','total_facturado','mes_actual',
                    'ultimo_pedido','total_pedidos']
        resumen = []
        for row in c.fetchall():
            r = dict(zip(cols_res, row))
            r['top_skus'] = top_skus.get(r['id'], [])
            freq = next((f for f in frecuencia if f['id'] == r['id']), None)
            r['frecuencia_dias'] = freq['frecuencia_dias'] if freq else None
            try:
                r['redes_sociales'] = json.loads(r['redes_sociales'] or '{}')
            except Exception:
                r['redes_sociales'] = {}
            resumen.append(r)

        conn.close()
        return jsonify({
            'resumen': resumen,
            'ventas_mes': ventas_mes,
            'frecuencia': frecuencia
        })
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/pedidos', methods=['GET','POST'])
def handle_pedidos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('cliente_id'):
            conn.close(); return jsonify({'error': 'cliente_id requerido'}), 400
        c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(numero,10) AS INTEGER)),0) FROM pedidos WHERE numero LIKE ?", (f"PED-{datetime.now().strftime('%Y')}-%",)); n = (c.fetchone()[0] or 0) + 1
        numero = f"PED-{datetime.now().strftime('%Y')}-{n:04d}"
        valor_total = sum(float(it.get('subtotal', float(it.get('cantidad',0))*float(it.get('precio_unitario',0)))) for it in (d.get('items') or []))
        c.execute("""INSERT INTO pedidos (numero,cliente_id,fecha,fecha_entrega_est,estado,empresa,valor_total,observaciones,creado_por)
                     VALUES (?,?,datetime('now'),?,?,?,?,?,?)""",
                  (numero, d['cliente_id'], d.get('fecha_entrega_est',''), d.get('estado','Confirmado'),
                   d.get('empresa','ANIMUS'), valor_total, d.get('observaciones',''), session.get('compras_user','sistema')))
        for it in (d.get('items') or []):
            subtotal = float(it.get('subtotal', float(it.get('cantidad',0))*float(it.get('precio_unitario',0))))
            c.execute("INSERT INTO pedidos_items (numero_pedido,sku,descripcion,cantidad,precio_unitario,subtotal) VALUES (?,?,?,?,?,?)",
                      (numero, it.get('sku',''), it.get('descripcion',''), int(it.get('cantidad',0)), float(it.get('precio_unitario',0)), subtotal))
        conn.commit(); conn.close()
        return jsonify({'message': f'Pedido {numero} creado', 'numero': numero}), 201
    estado = request.args.get('estado')
    q = "SELECT p.numero,c.nombre,p.fecha,p.estado,p.valor_total,p.empresa,p.fecha_entrega_est,c.codigo as cliente_codigo,COALESCE(p.monto_pagado,0) as monto_pagado,COALESCE(p.estado_pago,'Pendiente') as estado_pago,c.id as cliente_id FROM pedidos p LEFT JOIN clientes c ON p.cliente_id=c.id"
    params = []
    if estado: q += " WHERE p.estado=?"; params.append(estado)
    q += " ORDER BY p.fecha DESC LIMIT 100"
    c.execute(q, params)
    cols = ['numero','cliente','fecha','estado','valor_total','empresa','fecha_entrega_est','cliente_codigo','monto_pagado','estado_pago','cliente_id']
    rows = c.fetchall(); conn.close()
    return jsonify({'pedidos': [dict(zip(cols, r)) for r in rows]})

@bp.route('/api/pedidos/<numero>', methods=['GET','PATCH','DELETE'])
def handle_pedido_detalle(numero):
    if request.method == 'DELETE':
        if session.get('compras_user') not in ADMIN_USERS:
            return jsonify({'error':'Solo admins'}), 403
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute('DELETE FROM pedidos WHERE numero=?', (numero,))
        if c.rowcount == 0:
            conn.close(); return jsonify({'error':'No encontrado'}), 404
        conn.commit(); conn.close()
        return jsonify({'ok':True, 'eliminado':numero})
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'PATCH':
        d = request.json or {}
        sets = []; vals = []
        if d.get('estado'): sets.append('estado=?'); vals.append(d['estado'])
        if 'monto_pagado' in d: sets.append('monto_pagado=?'); vals.append(float(d['monto_pagado']))
        if d.get('estado_pago'): sets.append('estado_pago=?'); vals.append(d['estado_pago'])
        if d.get('numero_factura'): sets.append('numero_factura=?'); vals.append(d['numero_factura'])
        if sets:
            vals.append(numero)
            c.execute(f"UPDATE pedidos SET {','.join(sets)} WHERE numero=?", vals)
            conn.commit()
        conn.close(); return jsonify({'message': f'Pedido {numero} actualizado'})
    c.execute("SELECT p.*,cl.nombre as cliente_nombre FROM pedidos p LEFT JOIN clientes cl ON p.cliente_id=cl.id WHERE p.numero=?", (numero,))
    row = c.fetchone()
    if not row: conn.close(); return jsonify({'error': 'No encontrado'}), 404
    cols = [d[0] for d in c.description]
    pedido = dict(zip(cols, row))
    c.execute("SELECT sku,descripcion,cantidad,precio_unitario,subtotal,lote_pt FROM pedidos_items WHERE numero_pedido=?", (numero,))
    items = [dict(zip(['sku','descripcion','cantidad','precio_unitario','subtotal','lote_pt'], r)) for r in c.fetchall()]
    conn.close(); return jsonify({'pedido': pedido, 'items': items})

@bp.route('/api/stock-pt', methods=['GET','POST'])
def handle_stock_pt():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('sku'):
            conn.close(); return jsonify({'error': 'SKU requerido'}), 400
        unidades = int(d.get('unidades_inicial', d.get('unidades_disponible', 0)))
        c.execute("""INSERT INTO stock_pt (sku,descripcion,lote_produccion,fecha_produccion,unidades_inicial,unidades_disponible,precio_base,empresa,estado,observaciones)
                     VALUES (?,?,?,datetime('now'),?,?,?,?,?,?)""",
                  (d['sku'], d.get('descripcion',''), d.get('lote_produccion',''), unidades, unidades,
                   float(d.get('precio_base',0)), d.get('empresa','ANIMUS'), 'Disponible', d.get('observaciones','')))
        conn.commit(); conn.close()
        return jsonify({'message': f"Stock PT registrado: {d['sku']} — {unidades} uds"}), 201
    c.execute("SELECT sku,descripcion,SUM(unidades_disponible) as disponible,SUM(unidades_inicial) as inicial,MAX(fecha_produccion) as ultima_prod,empresa,precio_base,COUNT(*) as lotes FROM stock_pt WHERE estado='Disponible' GROUP BY sku,empresa ORDER BY sku")
    cols = ['sku','descripcion','disponible','inicial','ultima_prod','empresa','precio_base','lotes']
    rows = c.fetchall()
    conn.close()
    return jsonify({'stock_pt': [dict(zip(cols, r)) for r in rows]})

@bp.route('/api/despachos', methods=['GET','POST'])
def handle_despachos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(numero,10) AS INTEGER)),0) FROM despachos WHERE numero LIKE ?", (f"DSP-{datetime.now().strftime('%Y')}-%",)); n = (c.fetchone()[0] or 0) + 1
        numero = f"DSP-{datetime.now().strftime('%Y')}-{n:04d}"
        c.execute("INSERT INTO despachos (numero,numero_pedido,cliente_id,fecha,operador,observaciones,estado) VALUES (?,?,?,datetime('now'),?,?,?)",
                  (numero, d.get('numero_pedido',''), d.get('cliente_id'), session.get('compras_user','sistema'), d.get('observaciones',''), 'Completado'))
        for it in (d.get('items') or []):
            c.execute("INSERT INTO despachos_items (numero_despacho,sku,descripcion,lote_pt,cantidad,precio_unitario) VALUES (?,?,?,?,?,?)",
                      (numero, it.get('sku',''), it.get('descripcion',''), it.get('lote_pt',''), int(it.get('cantidad',0)), float(it.get('precio_unitario',0))))
            c.execute("""UPDATE stock_pt SET unidades_disponible=MAX(0,unidades_disponible-?)
                         WHERE id=(
                           SELECT id FROM stock_pt
                           WHERE sku=? AND unidades_disponible>0
                           ORDER BY fecha_produccion ASC LIMIT 1
                         )""",
                      (int(it.get('cantidad',0)), it.get('sku','')))
        if d.get('numero_pedido'):
            c.execute("UPDATE pedidos SET estado='Despachado',fecha_despacho=datetime('now') WHERE numero=?", (d['numero_pedido'],))
        conn.commit(); conn.close()
        return jsonify({'message': f'Despacho {numero} registrado', 'numero': numero}), 201
    c.execute("SELECT d.numero,cl.nombre as cliente,d.fecha,d.numero_pedido,d.estado,d.operador FROM despachos d LEFT JOIN clientes cl ON d.cliente_id=cl.id ORDER BY d.fecha DESC LIMIT 100")
    cols = ['numero','cliente','fecha','numero_pedido','estado','operador']
    rows = c.fetchall(); conn.close()
    return jsonify({'despachos': [dict(zip(cols, r)) for r in rows]})


@bp.route('/api/aliados/<int:cid>', methods=['PATCH'])
def patch_aliado(cid):
    """Actualiza semaforo y/o nivel_aliado de un aliado ANIMUS."""
    d = request.json or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    campos = []; vals = []
    if 'semaforo' in d and d['semaforo'] in ('verde','amarillo','rojo'):
        campos.append('semaforo=?'); vals.append(d['semaforo'])
    if 'nivel_aliado' in d and d['nivel_aliado'] in ('Ingreso','Estratégico','Mayorista'):
        campos.append('nivel_aliado=?'); vals.append(d['nivel_aliado'])
    if 'fecha_vinculacion' in d:
        campos.append('fecha_vinculacion=?'); vals.append(d['fecha_vinculacion'])
    if 'ciudad' in d:
        campos.append('ciudad=?'); vals.append(d['ciudad'])
    if 'categoria_profesional' in d:
        campos.append('categoria_profesional=?'); vals.append(d['categoria_profesional'])
    if 'canal_captacion' in d:
        campos.append('canal_captacion=?'); vals.append(d['canal_captacion'])
    if 'redes_sociales' in d:
        campos.append('redes_sociales=?')
        vals.append(json.dumps(d['redes_sociales']) if isinstance(d['redes_sociales'], dict) else d['redes_sociales'])
    if 'notas_seguimiento' in d:
        campos.append('notas_seguimiento=?'); vals.append(d['notas_seguimiento'])
    if campos:
        vals.append(cid)
        c.execute(f"UPDATE clientes SET {','.join(campos)} WHERE id=?", vals)
        conn.commit()
    conn.close(); return jsonify({'ok': True})


@bp.route('/api/clientes/cartera')
def get_cartera():
    """Resumen de cartera por aliado: facturado, pagado, saldo."""
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""
        SELECT cl.id, cl.nombre, cl.codigo, cl.semaforo,
               COUNT(p.numero) as total_pedidos,
               COALESCE(SUM(p.valor_total),0) as facturado,
               COALESCE(SUM(COALESCE(p.monto_pagado,0)),0) as pagado,
               COALESCE(SUM(p.valor_total),0) - COALESCE(SUM(COALESCE(p.monto_pagado,0)),0) as saldo,
               MAX(p.fecha) as ultimo_pedido
        FROM clientes cl
        LEFT JOIN pedidos p ON p.cliente_id=cl.id AND p.estado NOT IN ('Cancelado','Borrador')
        WHERE cl.activo=1 AND cl.empresa='ANIMUS'
        GROUP BY cl.id
        ORDER BY saldo DESC
    """)
    cols = ['id','nombre','codigo','semaforo','total_pedidos','facturado','pagado','saldo','ultimo_pedido']
    rows = [dict(zip(cols,r)) for r in c.fetchall()]
    conn.close()
    total_cartera = sum(r['saldo'] for r in rows if r['saldo'] > 0)
    return jsonify({'aliados': rows, 'total_cartera': total_cartera})


@bp.route('/api/aliados/<int:cid>', methods=['DELETE'])
def delete_aliado(cid):
    """Soft-delete: marca activo=0. No borra datos historicos."""
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE clientes SET activo=0 WHERE id=? AND empresa='ANIMUS'", (cid,))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'message': 'Aliado desactivado'})

# ─── MÓDULO GERENCIA — Rutas ──────────────────────────────────
