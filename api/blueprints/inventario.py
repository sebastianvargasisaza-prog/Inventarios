# blueprints/inventario.py ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ extraÃÂÃÂÃÂÃÂ­do de index.py (Fase C)
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

bp = Blueprint('inventario', __name__)


@bp.route('/api/inventario')
def get_inventario():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM movimientos')
    mov = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM producciones')
    prod = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM alertas')
    alrt = c.fetchone()[0]
    c.execute('SELECT COALESCE(SUM(CASE WHEN tipo="Entrada" THEN cantidad ELSE -cantidad END),0) FROM movimientos')
    stock = c.fetchone()[0]
    conn.close()
    return jsonify({'total_items': mov, 'movimientos': mov, 'producciones': prod,
                    'alertas': alrt, 'stock_total': round(stock, 2)})

@bp.route('/api/formulas', methods=['GET', 'POST'])
def handle_formulas():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        prod = data['producto_nombre']
        c.execute('INSERT OR REPLACE INTO formula_headers (producto_nombre, unidad_base_g, descripcion, fecha_creacion) VALUES (?,?,?,?)',
                  (prod, data.get('unidad_base_g', 1000), data.get('descripcion', ''), datetime.now().isoformat()))
        c.execute('DELETE FROM formula_items WHERE producto_nombre=?', (prod,))
        for item in data.get('items', []):
            c.execute('INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje) VALUES (?,?,?,?)',
                      (prod, item['material_id'], item['material_nombre'], item['porcentaje']))
        conn.commit()
        conn.close()
        return jsonify({'message': f'Formula de {prod} guardada exitosamente'}), 201
    c.execute('SELECT producto_nombre, unidad_base_g, descripcion, fecha_creacion FROM formula_headers ORDER BY producto_nombre')
    headers = c.fetchall()
    formulas = []
    for h in headers:
        c.execute('SELECT material_id, material_nombre, porcentaje FROM formula_items WHERE producto_nombre=?', (h[0],))
        items = [{'material_id': r[0], 'material_nombre': r[1], 'porcentaje': r[2]} for r in c.fetchall()]
        formulas.append({'producto_nombre': h[0], 'unidad_base_g': h[1], 'descripcion': h[2],
                         'fecha_creacion': h[3], 'items': items})
    conn.close()
    return jsonify({'formulas': formulas})

@bp.route('/api/formulas/<producto_nombre>', methods=['DELETE'])
def del_formula(producto_nombre):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM formula_items WHERE producto_nombre=?', (producto_nombre,))
    c.execute('DELETE FROM formula_headers WHERE producto_nombre=?', (producto_nombre,))
    conn.commit()
    conn.close()
    return jsonify({'message': f'Formula {producto_nombre} eliminada'})

@bp.route('/api/movimientos', methods=['GET', 'POST'])
def handle_movimientos():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        c.execute("""INSERT INTO movimientos
                     (material_id, material_nombre, cantidad, tipo, fecha, observaciones,
                      lote, fecha_vencimiento, estanteria, posicion, proveedor, estado_lote, operador)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (data['material_id'], data['material_nombre'], data['cantidad'],
                   data['tipo'], datetime.now().isoformat(), data.get('observaciones',''),
                   data.get('lote',''), data.get('fecha_vencimiento',''),
                   data.get('estanteria',''), data.get('posicion',''),
                   data.get('proveedor',''), data.get('estado_lote','VIGENTE'),
                   data.get('operador','')))
        conn.commit(); conn.close()
        return jsonify({'message': 'Movimiento registrado exitosamente'}), 201
    c.execute('SELECT material_id, material_nombre, cantidad, tipo, fecha, observaciones, operador, lote FROM movimientos ORDER BY fecha DESC LIMIT 500')
    movimientos = [{'material_id': r[0] or '', 'material_nombre': r[1], 'cantidad': r[2], 'tipo': r[3], 'fecha': r[4], 'observaciones': r[5], 'operador': r[6] or '', 'lote': r[7] or ''} for r in c.fetchall()]
    conn.close()
    return jsonify({'movimientos': movimientos})

@bp.route('/api/produccion', methods=['GET', 'POST'])
def handle_produccion():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        producto = data.get('producto', data.get('producto',''))
        presentacion = data.get('presentacion','')
        cantidad_kg = float(data.get('cantidad_kg', data.get('cantidad', 0)))
        cantidad_g = cantidad_kg * 1000
        fecha = datetime.now().isoformat()
        c.execute('INSERT INTO producciones (producto, cantidad, fecha, estado, observaciones, operador, presentacion) VALUES (?,?,?,?,?,?,?)',
                  (producto, cantidad_kg, fecha, 'Completado', data.get('observaciones', ''), data.get('operador', ''), presentacion))
        prod_id = c.lastrowid
        lote_ref = f'PROD-{prod_id:05d}'
        # Guardar lote_ref en producciones para trazabilidad
        try: c.execute("UPDATE producciones SET lote=? WHERE id=?", (lote_ref, prod_id))
        except: pass
        c.execute('SELECT material_id, material_nombre, porcentaje FROM formula_items WHERE producto_nombre=?', (producto,))
        formula_items = c.fetchall()
        descuentos = []
        for mat_id, mat_nombre, pct in formula_items:
            g_total = round((pct / 100) * cantidad_g, 2)
            if g_total <= 0: continue
            # FEFO: seleccionar lotes por fecha de vencimiento mas proxima con stock disponible
            c.execute("""SELECT lote, fecha_vencimiento,
                                SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock
                         FROM movimientos
                         WHERE material_id=? AND lote IS NOT NULL AND lote!='' AND lote!='S/L'
                           AND (estado_lote IS NULL OR estado_lote NOT IN ('CUARENTENA','CUARENTENA_EXTENDIDA','RECHAZADO'))
                         GROUP BY lote HAVING stock > 0
                         ORDER BY CASE WHEN fecha_vencimiento IS NULL OR fecha_vencimiento=''
                                  THEN '9999' ELSE fecha_vencimiento END ASC""", (mat_id,))
            lotes_fefo = c.fetchall()
            g_restante = g_total; lotes_usados = []
            for lrow in lotes_fefo:
                if g_restante <= 0: break
                lote_n, lote_v, lote_s = lrow
                g_lote = round(min(g_restante, lote_s), 2)
                c.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, observaciones, lote, operador) VALUES (?,?,?,?,?,?,?,?)",
                          (mat_id, mat_nombre, g_lote, 'Salida', fecha,
                           f'FEFO:{lote_ref}:{producto} x {cantidad_kg}kg', lote_n, data.get('operador','')))
                lotes_usados.append({'lote': lote_n, 'vence': str(lote_v)[:10] if lote_v else '', 'cantidad_g': g_lote})
                g_restante = round(g_restante - g_lote, 2)
            if g_restante > 0:
                c.execute("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, observaciones, operador) VALUES (?,?,?,?,?,?,?)",
                          (mat_id, mat_nombre, g_restante, 'Salida', fecha, f'Produccion: {producto} x {cantidad_kg}kg', data.get('operador','')))
                lotes_usados.append({'lote': 'sin_lote', 'vence': '', 'cantidad_g': g_restante})
            descuentos.append({'material': mat_nombre, 'material_id': mat_id,
                                'cantidad_g': g_total, 'lotes_fefo': lotes_usados})
        # Auto-crear entrada en stock_pt si viene sku + unidades
        sku_pt = data.get('sku_pt', '').strip()
        unidades_pt = int(data.get('unidades_pt', 0) or 0)
        precio_pt = float(data.get('precio_pt', 0) or 0)
        if sku_pt and unidades_pt > 0:
            c.execute("""INSERT INTO stock_pt
                         (sku, descripcion, lote_produccion, fecha_produccion,
                          unidades_inicial, unidades_disponible, precio_base, empresa, estado, observaciones)
                         VALUES (?,?,?,?,?,?,?,?,?,?)""",
                      (sku_pt, producto, lote_ref, fecha,
                       unidades_pt, unidades_pt, precio_pt,
                       'ANIMUS', 'Disponible',
                       f'Produccion {lote_ref} ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ {cantidad_kg}kg'))
        conn.commit()
        conn.close()
        msg = f'Produccion registrada: {producto} x {cantidad_kg}kg (FEFO)'
        if descuentos:
            msg += f'. {len(descuentos)} MPs descontadas por FEFO.'
        if sku_pt and unidades_pt > 0:
            msg += f'. {unidades_pt} uds de {sku_pt} en stock PT.'
        return jsonify({'message': msg, 'descuentos': descuentos, 'lote': lote_ref,
                        'stock_pt_creado': bool(sku_pt and unidades_pt > 0)}), 201
    c.execute('SELECT producto, cantidad, fecha, estado, operador, COALESCE(presentacion,"") FROM producciones ORDER BY fecha DESC LIMIT 50')
    prod = [{'producto': r[0], 'cantidad': r[1], 'fecha': r[2], 'estado': r[3], 'operador': r[4] or '', 'presentacion': r[5] or ''} for r in c.fetchall()]
    conn.close()
    return jsonify({'producciones': prod})


@bp.route('/api/produccion/simular', methods=['POST'])
def simular_produccion():
    """Pre-check de stock FEFO + estimado de costo sin commitear ningun movimiento."""
    data = request.json
    producto = data.get('producto', '')
    cantidad_kg = float(data.get('cantidad_kg', 1))
    cantidad_g = cantidad_kg * 1000
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT fi.material_id, fi.material_nombre, fi.porcentaje,
                        COALESCE(m.precio_referencia, 0)
                 FROM formula_items fi
                 LEFT JOIN maestro_mps m ON fi.material_id = m.codigo_mp
                 WHERE fi.producto_nombre=?""", (producto,))
    items = c.fetchall()
    if not items:
        conn.close()
        return jsonify({'error': f'Formula no encontrada: {producto}', 'factible': False}), 404
    resultado = []
    factible = True
    costo_total = 0.0
    sin_precio = 0
    for mat_id, mat_nombre, pct, precio_kg in items:
        g_req = round((pct / 100) * cantidad_g, 2)
        c.execute("""SELECT COALESCE(SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END),0)
                     FROM movimientos WHERE material_id=?
                     AND (estado_lote IS NULL OR estado_lote NOT IN ('CUARENTENA','CUARENTENA_EXTENDIDA','RECHAZADO'))""",
                  (mat_id,))
        g_disp = round(c.fetchone()[0] or 0, 2)
        suf = g_disp >= g_req
        if not suf:
            factible = False
        precio_g = (precio_kg or 0) / 1000.0
        costo_item = round(g_req * precio_g, 2)
        costo_total += costo_item
        if not precio_kg or precio_kg == 0:
            sin_precio += 1
        resultado.append({
            'material_id': mat_id, 'material_nombre': mat_nombre,
            'porcentaje': pct, 'g_requerido': g_req,
            'g_disponible': g_disp,
            'g_faltante': max(0, round(g_req - g_disp, 2)),
            'suficiente': suf,
            'precio_kg': round(precio_kg or 0, 2),
            'costo': costo_item
        })
    conn.close()
    faltantes = sum(1 for r in resultado if not r['suficiente'])
    n = len(resultado)
    return jsonify({
        'producto': producto, 'cantidad_kg': cantidad_kg,
        'factible': factible, 'faltantes': faltantes,
        'costo_total': round(costo_total, 2),
        'costo_por_kg': round(costo_total / cantidad_kg, 2) if cantidad_kg > 0 else 0,
        'ingredientes_sin_precio': sin_precio,
        'cobertura_precio_pct': round((n - sin_precio) / n * 100, 1) if n > 0 else 0,
        'ingredientes': sorted(resultado, key=lambda x: x['suficiente'])
    })


@bp.route('/api/formula/costo', methods=['POST'])
def calcular_costo_formula():
    """Calcula costo estimado de un batch sin verificar stock."""
    data = request.json
    producto = data.get('producto', '')
    cantidad_kg = float(data.get('cantidad_kg', 1))
    cantidad_g = cantidad_kg * 1000
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT fi.material_id, fi.material_nombre, fi.porcentaje,
                        COALESCE(m.precio_referencia, 0)
                 FROM formula_items fi
                 LEFT JOIN maestro_mps m ON fi.material_id = m.codigo_mp
                 WHERE fi.producto_nombre=?""", (producto,))
    items = c.fetchall()
    conn.close()
    if not items:
        return jsonify({'error': f'Formula no encontrada: {producto}'}), 404
    resultado = []
    costo_total = 0.0
    sin_precio = 0
    for mat_id, mat_nombre, pct, precio_kg in items:
        g_req = round((pct / 100) * cantidad_g, 2)
        precio_g = (precio_kg or 0) / 1000.0
        costo_item = round(g_req * precio_g, 2)
        costo_total += costo_item
        if not precio_kg or precio_kg == 0:
            sin_precio += 1
        resultado.append({
            'material_id': mat_id, 'material_nombre': mat_nombre,
            'porcentaje': pct, 'g_requerido': g_req,
            'precio_kg': round(precio_kg or 0, 2),
            'precio_g': round(precio_g, 5),
            'costo': costo_item
        })
    n = len(resultado)
    return jsonify({
        'producto': producto, 'cantidad_kg': cantidad_kg,
        'costo_total': round(costo_total, 2),
        'costo_por_kg': round(costo_total / cantidad_kg, 2) if cantidad_kg > 0 else 0,
        'ingredientes_sin_precio': sin_precio,
        'cobertura_precio_pct': round((n - sin_precio) / n * 100, 1) if n > 0 else 0,
        'ingredientes': sorted(resultado, key=lambda x: x['costo'], reverse=True)
    })


@bp.route('/api/trazabilidad/lote-pt/<lote_ref>')
def trazabilidad_lote_pt(lote_ref):
    """Traza hacia atrÃÂÃÂÃÂÃÂ¡s: dado un lote PT (PROD-00001) devuelve MPs consumidas, proveedor, fecha vencimiento."""
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # ProducciÃÂÃÂÃÂÃÂ³n base
    c.execute("SELECT id, producto, cantidad, fecha, operador, observaciones FROM producciones WHERE lote=? OR id=?",
              (lote_ref, lote_ref.replace('PROD-','').lstrip('0') or 0))
    prod = c.fetchone()
    if not prod:
        conn.close()
        return jsonify({'error': f'Lote no encontrado: {lote_ref}', 'lote_ref': lote_ref}), 404
    prod_data = {'id': prod[0], 'producto': prod[1], 'cantidad_kg': prod[2],
                 'fecha': prod[3], 'operador': prod[4] or '', 'observaciones': prod[5] or ''}
    # MPs consumidas ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ buscar Salidas etiquetadas con este lote_ref O por fecha+producto (legacy)
    c.execute("""SELECT material_id, material_nombre, SUM(cantidad) as g_total,
                        GROUP_CONCAT(DISTINCT lote) as lotes_mp,
                        GROUP_CONCAT(DISTINCT proveedor) as proveedores
                 FROM movimientos
                 WHERE tipo='Salida'
                   AND (observaciones LIKE ? OR (fecha=? AND observaciones LIKE ?))
                 GROUP BY material_id, material_nombre
                 ORDER BY material_nombre""",
              (f'FEFO:{lote_ref}:%', prod[3], f'%{prod[1]}%'))
    mps = [{'material_id': r[0], 'material_nombre': r[1], 'g_consumido': round(r[2], 2),
             'lotes_mp': [l for l in (r[3] or '').split(',') if l and l != 'None'],
             'proveedores': list(set([p for p in (r[4] or '').split(',') if p and p != 'None']))}
           for r in c.fetchall()]
    # Para cada lote de MP consumido, obtener info del ingreso original
    detalle_lotes = []
    for mp in mps:
        for lote_mp in mp['lotes_mp']:
            c.execute("""SELECT fecha, proveedor, numero_oc, numero_factura, fecha_vencimiento, estado_lote
                         FROM movimientos WHERE lote=? AND tipo='Entrada' AND material_id=?
                         ORDER BY fecha DESC LIMIT 1""", (lote_mp, mp['material_id']))
            row = c.fetchone()
            if row:
                detalle_lotes.append({
                    'material_id': mp['material_id'], 'material_nombre': mp['material_nombre'],
                    'lote_mp': lote_mp, 'fecha_ingreso': row[0][:10] if row[0] else '',
                    'proveedor': row[1] or '', 'numero_oc': row[2] or '',
                    'numero_factura': row[3] or '', 'fecha_vencimiento': row[4] or '',
                    'estado_lote': row[5] or 'VIGENTE'
                })
    # Despachos que usaron este PT batch
    c.execute("""SELECT d.numero, cl.nombre, d.fecha,
                        di.sku, di.descripcion, di.cantidad
                 FROM despachos_items di
                 JOIN despachos d ON di.numero_despacho=d.numero
                 LEFT JOIN clientes cl ON d.cliente_id=cl.id
                 WHERE di.lote_pt=? OR di.lote_pt LIKE ?""", (lote_ref, f'%{lote_ref}%'))
    despachos = [{'numero': r[0], 'cliente': r[1] or '', 'fecha': r[2], 'sku': r[3],
                  'descripcion': r[4], 'cantidad': r[5]} for r in c.fetchall()]
    conn.close()
    return jsonify({
        'lote_ref': lote_ref, 'produccion': prod_data,
        'mps_consumidas': mps, 'detalle_lotes_mp': detalle_lotes,
        'despachos': despachos,
        'trazabilidad_completa': len(mps) > 0
    })


@bp.route('/api/trazabilidad/lote-mp/<path:lote_mp>')
def trazabilidad_lote_mp(lote_mp):
    """Traza hacia adelante: dado un lote de MP devuelve en quÃÂÃÂÃÂÃÂ© producciones se usÃÂÃÂÃÂÃÂ³ y a quÃÂÃÂÃÂÃÂ© clientes llegÃÂÃÂÃÂÃÂ³."""
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # Ingreso del lote
    c.execute("""SELECT material_id, material_nombre, cantidad, fecha, proveedor,
                        numero_oc, numero_factura, fecha_vencimiento, estado_lote
                 FROM movimientos WHERE lote=? AND tipo='Entrada' LIMIT 1""", (lote_mp,))
    ingreso = c.fetchone()
    if not ingreso:
        conn.close()
        return jsonify({'error': f'Lote MP no encontrado: {lote_mp}'}), 404
    mat_info = {
        'material_id': ingreso[0], 'material_nombre': ingreso[1],
        'cantidad_kg_ingresada': round((ingreso[2] or 0) / 1000, 3),
        'fecha_ingreso': ingreso[3][:10] if ingreso[3] else '', 'proveedor': ingreso[4] or '',
        'numero_oc': ingreso[5] or '', 'numero_factura': ingreso[6] or '',
        'fecha_vencimiento': ingreso[7] or '', 'estado_lote': ingreso[8] or 'VIGENTE'
    }
    # Salidas ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ producciones que consumieron este lote
    c.execute("""SELECT observaciones, cantidad, fecha FROM movimientos
                 WHERE lote=? AND tipo='Salida' ORDER BY fecha""", (lote_mp,))
    salidas = c.fetchall()
    producciones_ref = []
    for obs, cant, fec in salidas:
        # obs format: "FEFO:PROD-00001:Suero TRX x 10kg" or legacy "FEFO: Suero TRX x 10kg"
        lote_prod = ''
        if obs and obs.startswith('FEFO:PROD-'):
            parts = obs.split(':')
            lote_prod = parts[1] if len(parts) > 1 else ''
        producciones_ref.append({
            'lote_produccion': lote_prod, 'g_consumido': round(cant, 2),
            'fecha': fec[:10] if fec else '', 'observaciones': obs or ''
        })
    # Detallar producciones ÃÂÃÂÃÂÃÂºnicas
    lotes_prod_unicos = list(set(p['lote_produccion'] for p in producciones_ref if p['lote_produccion']))
    producciones_detalle = []
    for lp in lotes_prod_unicos:
        c.execute("SELECT producto, cantidad, fecha, operador FROM producciones WHERE lote=?", (lp,))
        pr = c.fetchone()
        if pr:
            # Despachos desde este lote PT
            c.execute("""SELECT d.numero, cl.nombre, d.fecha, di.cantidad
                         FROM despachos_items di
                         JOIN despachos d ON di.numero_despacho=d.numero
                         LEFT JOIN clientes cl ON d.cliente_id=cl.id
                         WHERE di.lote_pt=?""", (lp,))
            dsps = [{'numero': r[0], 'cliente': r[1] or '', 'fecha': r[2], 'cantidad': r[3]} for r in c.fetchall()]
            producciones_detalle.append({
                'lote_ref': lp, 'producto': pr[0], 'cantidad_kg': pr[1],
                'fecha': pr[2][:10] if pr[2] else '', 'operador': pr[3] or '',
                'despachos': dsps
            })
    conn.close()
    return jsonify({
        'lote_mp': lote_mp, 'material': mat_info,
        'salidas': producciones_ref,
        'producciones': producciones_detalle,
        'clientes_afectados': list(set(
            d['cliente'] for p in producciones_detalle for d in p['despachos']
        ))
    })


@bp.route('/api/analisis-abc')
def get_analisis_abc():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT material_nombre, SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock
                 FROM movimientos GROUP BY material_nombre ORDER BY stock DESC""")
    items = [(r[0], r[1]) for r in c.fetchall() if r[1] and r[1] > 0]
    conn.close()
    if not items:
        return jsonify({'items': []})
    total = sum(i[1] for i in items)
    cumulative = 0
    abc = []
    for mat, qty in items:
        prev_pct = (cumulative / total) * 100   # % acumulado ANTES de este item
        cumulative += qty
        pct = (cumulative / total) * 100         # % acumulado DESPUÃÂÃÂÃÂÃÂS
        # Clasificacion basada en donde EMPIEZA el item (estandar Pareto)
        # Un item es A si al agregarlo aun no hemos superado el 80% previo
        clasificacion = 'A' if prev_pct < 80 else ('B' if prev_pct < 95 else 'C')
        abc.append({'material': mat, 'cantidad': qty, 'valor': f'{pct:.1f}%',
                    'clasificacion': clasificacion})
    return jsonify({'items': abc})

@bp.route('/api/alertas', methods=['GET', 'POST'])
def handle_alertas():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        c.execute('INSERT INTO alertas (material_id, material_nombre, stock_actual, stock_minimo, fecha, estado) VALUES (?,?,?,?,?,?)',
                  (data['material_id'], data['material_nombre'], data['stock_actual'],
                   data['stock_minimo'], datetime.now().isoformat(), 'Activa'))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Alerta creada'}), 201
    c.execute('SELECT material_nombre, stock_actual, stock_minimo, estado, fecha FROM alertas ORDER BY fecha DESC')
    alertas = [{'material_nombre': r[0], 'stock_actual': r[1], 'stock_minimo': r[2], 'estado': r[3], 'fecha': r[4]} for r in c.fetchall()]
    conn.close()
    return jsonify({'alertas': alertas})



@bp.route('/api/alertas-reabastecimiento')
def alertas_reabastecimiento():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # MPs bajo minimo
    c.execute("""SELECT m.material_id,
                        COALESCE(mp.nombre_comercial, m.material_nombre) as nombre,
                        COALESCE(mp.proveedor,'') as proveedor,
                        COALESCE(mp.stock_minimo,0) as stock_minimo,
                        SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad ELSE -m.cantidad END) as stock_actual,
                        'MP' as tipo_material,
                        COALESCE(mp.tipo,'') as subtipo
                 FROM movimientos m
                 LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
                 GROUP BY m.material_id
                 HAVING stock_actual < stock_minimo AND stock_minimo > 0
                 ORDER BY (stock_actual/stock_minimo) ASC""")
    rows_mp = c.fetchall()
    # MEE bajo minimo
    c.execute("""SELECT codigo, descripcion, '' as proveedor, stock_minimo,
                        stock_actual, 'MEE' as tipo_material, categoria as subtipo
                 FROM maestro_mee
                 WHERE estado='Activo' AND stock_minimo > 0 AND stock_actual < stock_minimo
                 ORDER BY (stock_actual/stock_minimo) ASC""")
    rows_mee = c.fetchall()
    conn.close()
    alertas = []
    for r in list(rows_mp) + list(rows_mee):
        stock_actual = round(r[4] or 0, 1)
        stock_minimo = round(r[3], 1)
        alertas.append({'codigo_mp': r[0] or '', 'nombre': r[1] or '', 'proveedor': r[2] or '',
                        'stock_minimo': stock_minimo, 'stock_actual': max(stock_actual, 0),
                        'deficit': round(max(stock_minimo - stock_actual, 0), 1),
                        'tipo': r[5] or 'MP', 'subtipo': r[6] or ''})
    alertas.sort(key=lambda x: x['stock_actual']/x['stock_minimo'] if x['stock_minimo'] else 1)
    return jsonify({'alertas': alertas, 'total': len(alertas)})
@bp.route('/api/stock')
def get_stock():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT material_id, material_nombre, SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE 0 END), SUM(CASE WHEN tipo='Salida' THEN cantidad ELSE 0 END), SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) FROM movimientos GROUP BY material_id, material_nombre ORDER BY material_nombre")
    rows = c.fetchall(); conn.close()
    return jsonify({'items': [{'material_id':r[0],'material_nombre':r[1],'entradas':round(r[2] or 0,2),'salidas':round(r[3] or 0,2),'stock_actual':round(r[4] or 0,2)} for r in rows]})

@bp.route('/api/lotes')
def get_lotes():
    from datetime import date; hoy = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT m.material_id, m.material_nombre, m.lote,
                        SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad ELSE -m.cantidad END) as stock_neto,
                        MAX(m.fecha_vencimiento) as fecha_vencimiento,
                        MAX(m.estanteria) as estanteria, MAX(m.posicion) as posicion,
                        MAX(m.proveedor) as proveedor, MAX(m.estado_lote) as estado_lote,
                        COALESCE(MAX(mp.nombre_inci),'') as inci,
                        COALESCE(MAX(mp.tipo),'') as tipo,
                        COALESCE(MAX(mp.stock_minimo),0) as smin
                 FROM movimientos m LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
                 GROUP BY m.material_id, m.lote
                 HAVING stock_neto > -999999
                 ORDER BY m.material_nombre ASC, fecha_vencimiento ASC""")
    rows = c.fetchall(); conn.close()
    result = []
    for r in rows:
        mid,mnm,lote,cant,fvenc,est,pos,prov,estado,inci,tipo,smin = r
        dias,alerta = None,'ok'
        if fvenc and len(str(fvenc))>=10:
            try:
                from datetime import datetime as dt2
                dias=(dt2.strptime(str(fvenc)[:10],'%Y-%m-%d').date()-dt2.strptime(hoy,'%Y-%m-%d').date()).days
                alerta='vencido' if dias<0 else ('critico' if dias<=30 else ('proximo' if dias<=90 else 'ok'))
            except: pass
        result.append({'material_id':mid or '','nombre_inci':inci,'material_nombre':mnm or '',
                       'tipo':tipo,'proveedor':prov or '','stock_min_g':round(smin,1),
                       'lote':lote or '','cantidad_g':round(cant or 0,2),'cantidad_kg':round((cant or 0)/1000,3),
                       'estanteria':est or '','posicion':pos or '',
                       'fecha_vencimiento':str(fvenc)[:10] if fvenc else '',
                       'dias_para_vencer':dias,'estado_lote':estado or '','alerta':alerta})
    return jsonify({'lotes': result, 'total': len(result)})

@bp.route('/api/maestro-mps', methods=['GET','POST'])
def handle_maestro():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json
        c.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo,proveedor,stock_minimo) VALUES (?,?,?,?,?,?)",
                  (d['codigo_mp'],d.get('nombre_inci',''),d.get('nombre_comercial',''),d.get('tipo',''),d.get('proveedor',''),d.get('stock_minimo',0)))
        conn.commit(); conn.close()
        return jsonify({'message': 'MP guardada'}), 201
    c.execute("SELECT codigo_mp,nombre_inci,nombre_comercial,tipo,proveedor,stock_minimo,COALESCE(precio_referencia,0) FROM maestro_mps WHERE activo=1 ORDER BY nombre_comercial")
    rows = c.fetchall(); conn.close()
    return jsonify({'mps': [{'codigo_mp':r[0],'nombre_inci':r[1],'nombre_comercial':r[2],'tipo':r[3],'proveedor':r[4],'stock_minimo':r[5],'precio_referencia':r[6]} for r in rows]})

@bp.route('/api/maestro-mps/<codigo>')
def get_mp(codigo):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT codigo_mp,nombre_inci,nombre_comercial,tipo,proveedor,stock_minimo FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    r = c.fetchone(); conn.close()
    return jsonify({'codigo_mp':r[0],'nombre_inci':r[1],'nombre_comercial':r[2],'tipo':r[3],'proveedor':r[4],'stock_minimo':r[5]}) if r else (jsonify({'error':'not found'}),404)


@bp.route('/api/maestro-mps/<codigo>/stock-minimo', methods=['PUT'])
def update_stock_minimo(codigo):
    """Actualiza el stock minimo de una MP."""
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    d = request.json or {}
    nuevo_min = d.get('stock_minimo')
    if nuevo_min is None:
        return jsonify({'error': 'stock_minimo requerido'}), 400
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE maestro_mps SET stock_minimo=? WHERE codigo_mp=?", (float(nuevo_min), codigo))
    if c.rowcount == 0:
        conn.close(); return jsonify({'error': 'MP no encontrada'}), 404
    conn.commit(); conn.close()
    return jsonify({'message': f'Stock minimo de {codigo} actualizado a {nuevo_min}'})

@bp.route('/api/maestro-mps/<codigo>/mee-stock-minimo', methods=['PUT'])
def update_mee_stock_minimo(codigo):
    """Actualiza el stock minimo de un MEE."""
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    d = request.json or {}
    nuevo_min = d.get('stock_minimo')
    if nuevo_min is None:
        return jsonify({'error': 'stock_minimo requerido'}), 400
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE maestro_mee SET stock_minimo=? WHERE codigo=?", (float(nuevo_min), codigo))
    if c.rowcount == 0:
        conn.close(); return jsonify({'error': 'MEE no encontrado'}), 404
    conn.commit(); conn.close()
    return jsonify({'message': f'Stock minimo de {codigo} actualizado a {nuevo_min}'})

@bp.route('/api/consumo-manual', methods=['POST'])
def consumo_manual():
    """Registra consumo manual de una MP (ajuste por uso)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    d = request.json or {}
    codigo = (d.get('codigo_mp') or '').upper().strip()
    cantidad = float(d.get('cantidad') or 0)
    lote = d.get('lote', '')
    obs = d.get('observaciones', 'Consumo manual')
    operador = d.get('operador', session.get('compras_user', ''))
    if not codigo or cantidad <= 0:
        return jsonify({'error': 'Codigo y cantidad positiva requeridos'}), 400
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT nombre_comercial FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    mp = c.fetchone()
    nombre = mp[0] if mp else codigo
    c.execute("""INSERT INTO movimientos
                 (material_id,material_nombre,cantidad,tipo,fecha,observaciones,lote,operador)
                 VALUES (?,?,?,'Salida',datetime('now'),?,?,?)""",
              (codigo, nombre, cantidad, obs, lote, operador))
    conn.commit(); conn.close()
    return jsonify({'message': f'Consumo de {cantidad} registrado para {nombre}'}), 201

@bp.route('/api/maestro-mps/<codigo>/archivar', methods=['PUT'])
def archivar_mp(codigo):
    """Archiva una MP (la marca como inactiva sin borrarla)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE maestro_mps SET activo=0 WHERE codigo_mp=?", (codigo,))
    if c.rowcount == 0:
        conn.close(); return jsonify({'error': 'MP no encontrada'}), 404
    conn.commit(); conn.close()
    return jsonify({'message': f'MP {codigo} archivada exitosamente'})

@bp.route('/api/recepcion', methods=['POST'])
def registrar_recepcion():
    d = request.json; codigo = (d.get('codigo_mp') or '').upper().strip()
    if not codigo: return jsonify({'error': 'Codigo MP requerido'}), 400
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT nombre_inci,nombre_comercial,tipo,proveedor FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    mp = c.fetchone()
    nombre = d.get('nombre_comercial','') or (mp[1] if mp else codigo)
    proveedor = d.get('proveedor','') or (mp[3] if mp else '')
    precio_kg = float(d.get('precio_kg') or 0)
    numero_factura = (d.get('numero_factura') or '').strip()
    numero_oc = (d.get('numero_oc') or '').strip()
    cuarentena = bool(d.get('cuarentena', False))
    estado_lote = 'CUARENTENA' if cuarentena else 'VIGENTE'
    # Si la MP es nueva y viene con datos, crearla en el catalogo
    if not mp and (d.get('nombre_inci') or d.get('nombre_comercial')):
        c.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, tipo, proveedor, stock_minimo) VALUES (?,?,?,?,?,?)",
                  (codigo, d.get('nombre_inci',''), nombre, d.get('tipo',''), proveedor, d.get('stock_minimo',0)))
        conn.commit()
    # Actualizar precio_referencia en maestro_mps si viene precio
    if precio_kg > 0:
        try:
            c.execute("UPDATE maestro_mps SET precio_referencia=?, ultima_act_precio=datetime('now') WHERE codigo_mp=?", (precio_kg, codigo))
        except: pass
    lote = (d.get('lote') or '').strip()
    if not lote or lote.upper()=='AUTO':
        from datetime import date; lote = f"ESP{date.today().strftime('%y%m%d')}{codigo[-3:]}"
    c.execute("""INSERT INTO movimientos
                 (material_id,material_nombre,cantidad,tipo,fecha,observaciones,
                  lote,fecha_vencimiento,estanteria,posicion,proveedor,estado_lote,operador,
                  precio_kg,numero_factura,numero_oc)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (codigo,nombre,float(d.get('cantidad',0)),'Entrada',datetime.now().isoformat(),
               d.get('observaciones','Ingreso MP'),lote,d.get('fecha_vencimiento',''),
               d.get('estanteria',''),d.get('posicion',''),proveedor,estado_lote,
               d.get('operador',''),precio_kg,numero_factura,numero_oc))
    mov_id = c.lastrowid
    # Log precio historico
    if precio_kg > 0:
        try:
            c.execute("INSERT OR IGNORE INTO precios_mp_historico (codigo_mp,precio_kg,numero_factura,proveedor,fecha) VALUES (?,?,?,?,datetime('now'))",
                      (codigo, precio_kg, numero_factura, proveedor))
        except: pass
    # Cerrar OC si se referencia una
    if numero_oc:
        try:
            c.execute("UPDATE ordenes_compra_items SET cantidad_recibida_g=cantidad_recibida_g+?,lote_asignado=? WHERE numero_oc=? AND codigo_mp=?",
                      (float(d.get('cantidad',0)), lote, numero_oc, codigo))
            # verificar si todos los items de la OC estan recibidos
            c.execute("SELECT COUNT(*) FROM ordenes_compra_items WHERE numero_oc=? AND (cantidad_g - cantidad_recibida_g) > 1", (numero_oc,))
            pendientes = c.fetchone()[0]
            if pendientes == 0:
                c.execute("UPDATE ordenes_compra SET estado='RECIBIDA',fecha_recepcion=datetime('now'),recibido_por=? WHERE numero_oc=?",
                          (d.get('operador',''), numero_oc))
        except: pass
    conn.commit(); conn.close()
    msg = f'{nombre} ingresada. Lote: {lote}'
    if cuarentena: msg += ' ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ En CUARENTENA (pendiente aprobacion QC)'
    if numero_oc: msg += f' | OC {numero_oc} actualizada'
    return jsonify({'message': msg,'lote':lote,'codigo':codigo,'nombre':nombre,'cantidad':d.get('cantidad',0),'cuarentena':cuarentena}), 201

@bp.route('/api/lotes/cuarentena', methods=['GET'])
def lotes_cuarentena():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT m.id, m.material_id, m.material_nombre, m.lote, m.cantidad,
                      m.fecha, m.proveedor, m.numero_factura, m.numero_oc, m.observaciones,
                      mp.nombre_inci
               FROM movimientos m
               LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
               WHERE m.estado_lote='CUARENTENA' AND m.tipo='Entrada'
               ORDER BY m.fecha DESC""")
    rows = c.fetchall()
    conn.close()
    cols = ['id','codigo_mp','nombre','lote','cantidad','fecha','proveedor','numero_factura','numero_oc','observaciones','nombre_inci']
    return jsonify([dict(zip(cols,r)) for r in rows])

@bp.route('/api/lotes/liberar', methods=['POST'])
def liberar_lote():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'Solo administradores pueden liberar lotes'}), 401
    d = request.json or {}
    mov_id = d.get('id')
    accion = (d.get('accion') or 'APROBAR').upper()
    if accion not in ('APROBAR','RECHAZAR'):
        return jsonify({'error': 'Accion debe ser APROBAR o RECHAZAR'}), 400
    nuevo_estado = 'VIGENTE' if accion == 'APROBAR' else 'RECHAZADO'
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE movimientos SET estado_lote=? WHERE id=? AND estado_lote='CUARENTENA'", (nuevo_estado, mov_id))
    if c.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Lote no encontrado o ya procesado'}), 404
    c.execute("""INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                 VALUES (?,?,?,?,?,?,datetime('now'))""",
              (session.get('compras_user','?'), f'LOTE_{accion}', 'movimientos',
               str(mov_id), f'Lote liberado: {accion}', request.remote_addr))
    conn.commit(); conn.close()
    return jsonify({'message': f'Lote {accion.lower()}ado correctamente', 'estado': nuevo_estado})

@bp.route('/api/trazabilidad/<lote>', methods=['GET'])
def trazabilidad_lote(lote):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # Ingreso del lote
    c.execute("""SELECT m.material_id, m.material_nombre, m.cantidad, m.fecha,
                      m.proveedor, m.numero_factura, m.numero_oc, m.precio_kg
               FROM movimientos m WHERE m.lote=? AND m.tipo='Entrada' LIMIT 1""", (lote,))
    ingreso = c.fetchone()
    # Consumos en produccion
    # consumos: buscar en producciones que mencionen el lote en observaciones
    c.execute("""SELECT producto, fecha, operador, cantidad
               FROM producciones WHERE observaciones LIKE ? ORDER BY fecha""", (f'%{lote}%',))
    producciones = c.fetchall()
    conn.close()
    return jsonify({
        'lote': lote,
        'ingreso': {'codigo_mp': ingreso[0], 'nombre': ingreso[1], 'cantidad_g': ingreso[2],
                    'fecha': ingreso[3], 'proveedor': ingreso[4], 'factura': ingreso[5],
                    'orden_compra': ingreso[6], 'precio_kg': ingreso[7]} if ingreso else None,
        'producciones': [{'producto': p[0], 'fecha': p[1], 'operador': p[2],
                          'cantidad_g': p[3]} for p in producciones],
        'total_producciones': len(producciones)
    })

# ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂ CONTEO CICLICO BDG-PRO-002 ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂ
@bp.route('/api/conteo/estanterias', methods=['GET'])
def conteo_estanterias():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT COALESCE(NULLIF(estanteria,''),'Sin estanteria') as est,
                        COUNT(DISTINCT material_id) as total_mps,
                        SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock_total
                 FROM movimientos GROUP BY est ORDER BY est""")
    rows = c.fetchall()
    conn.close()
    return jsonify([{'estanteria': r[0], 'total_mps': r[1], 'stock_total': round(r[2] or 0, 1)} for r in rows])

@bp.route('/api/conteo/materiales', methods=['GET'])
def conteo_materiales_estanteria():
    est = request.args.get('estanteria', '')
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if est and est != 'Sin estanteria':
        c.execute("""SELECT m.material_id, m.material_nombre,
                            COALESCE(mp.nombre_inci,'') as inci,
                            COALESCE(mp.precio_referencia,0) as precio_ref,
                            SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad ELSE -m.cantidad END) as stock_sistema,
                            MAX(m.estanteria) as estanteria
                     FROM movimientos m
                     LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
                     WHERE m.estanteria=?
                     GROUP BY m.material_id HAVING stock_sistema > 0
                     ORDER BY m.material_nombre""", (est,))
    else:
        c.execute("""SELECT m.material_id, m.material_nombre,
                            COALESCE(mp.nombre_inci,'') as inci,
                            COALESCE(mp.precio_referencia,0) as precio_ref,
                            SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad ELSE -m.cantidad END) as stock_sistema,
                            '' as estanteria
                     FROM movimientos m
                     LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
                     WHERE (m.estanteria IS NULL OR m.estanteria='')
                     GROUP BY m.material_id HAVING stock_sistema > 0
                     ORDER BY m.material_nombre""")
    rows = c.fetchall()
    conn.close()
    cols = ['codigo_mp','nombre','inci','precio_ref','stock_sistema','estanteria']
    return jsonify([dict(zip(cols, r)) for r in rows])

@bp.route('/api/conteo/iniciar', methods=['POST'])
def conteo_iniciar():
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    d = request.json or {}
    est = d.get('estanteria', '')
    responsable = d.get('responsable', session.get('compras_user',''))
    from datetime import date
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # Verificar si ya existe un conteo ABIERTO para esta estanteria
    c.execute("SELECT id, numero FROM conteos_fisicos WHERE estanteria=? AND estado='Abierto' ORDER BY id DESC LIMIT 1", (est,))
    existing = c.fetchone()
    if existing:
        conn.close()
        return jsonify({'conteo_id': existing[0], 'numero': existing[1],
                        'message': 'Conteo retomado', 'resuming': True})
    numero = 'CNT-' + date.today().strftime('%Y%m%d') + '-' + est.replace(' ','')[:6].upper()
    # Si el numero ya existe (mismo dia), agregar sufijo incremental
    c.execute("SELECT COUNT(*) FROM conteos_fisicos WHERE numero LIKE ?", (numero + '%',))
    suffix = c.fetchone()[0]
    if suffix > 0:
        numero = numero + f'-{suffix+1}'
    try:
        c.execute("INSERT INTO conteos_fisicos (numero,fecha_inicio,estado,responsable,estanteria,tipo_conteo) VALUES (?,datetime('now'),'Abierto',?,?,'Ciclico')",
                  (numero, responsable, est))
        conteo_id = c.lastrowid
        conn.commit(); conn.close()
        return jsonify({'conteo_id': conteo_id, 'numero': numero, 'message': 'Conteo iniciado'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 400


@bp.route('/api/conteo/programacion', methods=['GET'])
def conteo_programacion():
    """Retorna la programacion ciclica automatica: estanteria asignada por semana ISO."""
    from datetime import date, timedelta
    import math
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT COALESCE(NULLIF(estanteria,''),'Sin estanteria') as est
                 FROM movimientos
                 GROUP BY est
                 HAVING SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) > 0
                 ORDER BY est""")
    estanterias = [r[0] for r in c.fetchall()]
    if not estanterias:
        conn.close()
        return jsonify({'semanas': [], 'total_estanterias': 0})
    n = len(estanterias)
    hoy = date.today()
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    semanas = []
    for delta in range(-1, 5):
        lunes = lunes_actual + timedelta(weeks=delta)
        semana_iso = lunes.isocalendar()[1]
        anio = lunes.isocalendar()[0]
        idx = (semana_iso - 1) % n
        est = estanterias[idx]
        fecha_fin = lunes + timedelta(days=6)
        c.execute("""SELECT id, numero, estado FROM conteos_fisicos
                     WHERE estanteria=? AND fecha_inicio BETWEEN ? AND ?
                     ORDER BY id DESC LIMIT 1""",
                  (est, lunes.isoformat(), fecha_fin.isoformat() + ' 23:59:59'))
        conteo = c.fetchone()
        semanas.append({
            'semana': semana_iso, 'anio': anio, 'lunes': lunes.isoformat(),
            'estanteria': est, 'es_actual': delta == 0,
            'conteo_id': conteo[0] if conteo else None,
            'conteo_numero': conteo[1] if conteo else None,
            'conteo_estado': conteo[2] if conteo else 'Pendiente',
        })
    conn.close()
    return jsonify({'semanas': semanas, 'total_estanterias': n, 'estanterias': estanterias})

@bp.route('/api/conteo/<int:conteo_id>/guardar', methods=['POST'])
def conteo_guardar(conteo_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    d = request.json or {}
    items = d.get('items', [])
    UMBRAL_ESCALA = 0.05  # 5% -> escala a gerencia (BDG-PRO-002 num 8)
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT estado FROM conteos_fisicos WHERE id=?", (conteo_id,))
    row = c.fetchone()
    if not row or row[0] != 'Abierto':
        conn.close(); return jsonify({'error': 'Conteo no encontrado o ya cerrado'}), 400

    items_con_diff = 0
    for item in items:
        codigo = item.get('codigo_mp','')
        stock_sis = float(item.get('stock_sistema', 0))
        stock_fis = item.get('stock_fisico')
        if stock_fis is None or stock_fis == '': continue
        stock_fis = float(stock_fis)
        diff = stock_fis - stock_sis
        precio_ref = float(item.get('precio_ref', 0))
        valor_diff = abs(diff / 1000) * precio_ref  # diff en g, precio en /kg
        pct_diff = abs(diff / stock_sis) if stock_sis > 0 else 0
        requiere_gerencia = 1 if pct_diff > UMBRAL_ESCALA else 0
        causa = item.get('causa_diferencia', '')
        if abs(diff) > 0: items_con_diff += 1
        c.execute("""INSERT OR REPLACE INTO conteo_items
                     (conteo_id,codigo_mp,nombre_mp,stock_sistema,stock_fisico,diferencia,
                      estanteria,causa_diferencia,valor_diferencia,requiere_gerencia,observaciones)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (conteo_id, codigo, item.get('nombre',''), stock_sis, stock_fis, diff,
                   item.get('estanteria',''), causa, round(valor_diff,0), requiere_gerencia,
                   item.get('observaciones','')))
    c.execute("UPDATE conteos_fisicos SET items_diferencia=?,total_items=? WHERE id=?",
              (items_con_diff, len(items), conteo_id))
    conn.commit(); conn.close()
    return jsonify({'message': 'Conteo guardado', 'items_con_diferencia': items_con_diff})

@bp.route('/api/conteo/<int:conteo_id>/cerrar', methods=['POST'])
def conteo_cerrar(conteo_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM conteo_items WHERE conteo_id=? AND requiere_gerencia=1 AND aprobado_gerencia=0", (conteo_id,))
    pendientes_gerencia = c.fetchone()[0]
    c.execute("UPDATE conteos_fisicos SET estado='Cerrado',fecha_cierre=datetime('now') WHERE id=?", (conteo_id,))
    conn.commit(); conn.close()
    msg = 'Conteo cerrado.'
    if pendientes_gerencia:
        msg += f' ATENCION: {pendientes_gerencia} item(s) con diferencia >5% pendientes de aprobacion Gerencia General antes de ajustar (BDG-PRO-002 num 8).'
    return jsonify({'message': msg, 'pendientes_gerencia': pendientes_gerencia})

@bp.route('/api/conteo/<int:conteo_id>/ajustar', methods=['POST'])
def conteo_ajustar(conteo_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    user = session.get('compras_user','')
    d = request.json or {}
    item_id = d.get('item_id')
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT ci.*, cf.estado FROM conteo_items ci JOIN conteos_fisicos cf ON ci.conteo_id=cf.id WHERE ci.id=?", (item_id,))
    item = c.fetchone()
    if not item:
        conn.close(); return jsonify({'error': 'Item no encontrado'}), 404
    cols = [desc[0] for desc in c.description]
    it = dict(zip(cols, item))
    if it['requiere_gerencia'] and not it['aprobado_gerencia']:
        if user not in ADMIN_USERS:
            conn.close()
            return jsonify({'error': 'Diferencia >5% requiere aprobacion Gerencia General (BDG-PRO-002)'}), 403
        c.execute("UPDATE conteo_items SET aprobado_gerencia=1,aprobado_gerencia_por=? WHERE id=?", (user, item_id))
    diff = float(it['diferencia'])
    if diff == 0:
        conn.close(); return jsonify({'message': 'Sin diferencia, no se requiere ajuste'})
    tipo_mov = 'Entrada' if diff > 0 else 'Salida'
    obs = f'Ajuste inventario ciclico #{conteo_id} - {it.get("causa_diferencia","Sin causa")} - Aprobado: {user}'
    c.execute("""INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,observaciones,lote,estanteria,estado_lote,operador)
                 VALUES (?,?,?,?,datetime('now'),?,?,?,'VIGENTE',?)""",
              (it['codigo_mp'], it['nombre_mp'], abs(diff), tipo_mov, obs,
               'AJUSTE-'+str(conteo_id), it.get('estanteria',''), user))
    c.execute("UPDATE conteo_items SET ajuste_aplicado=1 WHERE id=?", (item_id,))
    c.execute("INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha) VALUES (?,?,?,?,?,?,datetime('now'))",
              (user, 'AJUSTE_INVENTARIO', 'conteo_items', str(item_id),
               f'MP:{it["codigo_mp"]} Diff:{diff}g Causa:{it.get("causa_diferencia","")}',
               request.remote_addr))
    conn.commit(); conn.close()
    return jsonify({'message': f'Ajuste aplicado: {tipo_mov} de {abs(diff):.0f}g para {it["nombre_mp"]}'})

@bp.route('/api/conteo/historial', methods=['GET'])
def conteo_historial():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT cf.id, cf.numero, cf.estanteria, cf.fecha_inicio, cf.fecha_cierre,
                        cf.estado, cf.responsable, cf.total_items, cf.items_diferencia,
                        COUNT(CASE WHEN ci.requiere_gerencia=1 THEN 1 END) as items_gerencia
                 FROM conteos_fisicos cf
                 LEFT JOIN conteo_items ci ON cf.id=ci.conteo_id
                 GROUP BY cf.id ORDER BY cf.fecha_inicio DESC LIMIT 50""")
    rows = c.fetchall()
    conn.close()
    cols = ['id','numero','estanteria','fecha_inicio','fecha_cierre','estado','responsable','total_items','items_diferencia','items_gerencia']
    return jsonify([dict(zip(cols, r)) for r in rows])

@bp.route('/api/conteo/<int:conteo_id>/items', methods=['GET'])
def conteo_get_items(conteo_id):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT * FROM conteo_items WHERE conteo_id=? ORDER BY codigo_mp", (conteo_id,))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return jsonify([dict(zip(cols, r)) for r in rows])

@bp.route('/api/lotes/cc-review', methods=['POST'])
def cc_review():
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    user = session.get('compras_user', '')
    allowed = set(ADMIN_USERS) | {'hernando'}
    if user not in allowed:
        return jsonify({'error': 'Solo CC o administradores'}), 401
    d = request.json or {}
    mov_id = d.get('mov_id')
    if not mov_id:
        return jsonify({'error': 'mov_id requerido'}), 400
    solubilidad = d.get('solubilidad', '')
    resultado_aql = d.get('resultado_aql', '')
    if solubilidad == 'RECHAZO' or resultado_aql == 'NO_CONFORME':
        estado_final = 'RECHAZADO'
    elif resultado_aql == 'CUARENTENA_EXTENDIDA':
        estado_final = 'CUARENTENA_EXTENDIDA'
    else:
        estado_final = 'APROBADO'
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT id, material_id, lote, estado_lote FROM movimientos WHERE id=?", (mov_id,))
    mov = c.fetchone()
    if not mov:
        conn.close(); return jsonify({'error': 'Lote no encontrado'}), 404
    if mov[3] not in ('CUARENTENA', 'CUARENTENA_EXTENDIDA'):
        conn.close(); return jsonify({'error': 'Lote no esta en cuarentena'}), 400
    c.execute(
        "INSERT INTO cc_reviews (mov_id,lote,codigo_mp,coa_ok,lote_coincide,coa_vigente,ficha_ok,"
        "solubilidad,resultado_aql,observaciones_aql,muestra_retencion,observaciones,firmante,estado_final,fecha,ip) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?)",
        (mov_id, d.get('lote',''), d.get('codigo_mp',''),
         1 if d.get('coa_ok') else 0, 1 if d.get('lote_coincide') else 0,
         1 if d.get('coa_vigente') else 0, 1 if d.get('ficha_ok') else 0,
         solubilidad, resultado_aql, d.get('observaciones_aql',''),
         1 if d.get('muestra_retencion') else 0, d.get('observaciones',''),
         d.get('firmante', user), estado_final, request.remote_addr))
    c.execute("UPDATE movimientos SET estado_lote=? WHERE id=?", (estado_final, mov_id))
    c.execute(
        "INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha) VALUES (?,?,?,?,?,?,datetime('now'))",
        (user, 'CC_REVIEW_'+estado_final, 'movimientos', str(mov_id),
         'Lote '+d.get('lote','')+' AQL:'+resultado_aql+' Solub:'+solubilidad+' Firma:'+d.get('firmante',user),
         request.remote_addr))
    if estado_final == 'RECHAZADO':
        try:
            c.execute(
                "INSERT INTO solicitudes_compra (material_codigo,material_nombre,cantidad,unidad,justificacion,estado,empresa,area,solicitante,fecha) "
                "VALUES (?,?,0,'kg',?,'PENDIENTE','Espagiria','Calidad',?,datetime('now'))",
                (d.get('codigo_mp',''), d.get('lote',''),
                 'LOTE RECHAZADO QC - Devolucion proveedor. Lote: '+d.get('lote',''), user))
        except: pass
    conn.commit(); conn.close()
    msgs = {'APROBADO': 'Lote APROBADO. Disponible para produccion.',
            'RECHAZADO': 'Lote RECHAZADO. Notificacion creada en Compras.',
            'CUARENTENA_EXTENDIDA': 'CUARENTENA EXTENDIDA. Maximo 5 dias para definicion.'}
    return jsonify({'message': msgs.get(estado_final,''), 'estado': estado_final})

@bp.route('/api/movimientos/<int:mov_id>/anular', methods=['POST'])
def anular_movimiento(mov_id):
    """Anula un movimiento generando un contra-movimiento. Requiere autenticacion."""
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    user = session.get('compras_user', '')
    d = request.json or {}
    motivo = d.get('motivo', '').strip()
    if not motivo:
        return jsonify({'error': 'Motivo de anulacion requerido'}), 400
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT m.*, mp.nombre FROM movimientos m
                 LEFT JOIN maestro_mps mp ON m.material_id = mp.codigo_mp
                 WHERE m.id=?""", (mov_id,))
    row = c.fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'Movimiento no encontrado'}), 404
    cols = [d[0] for d in c.description]
    mov = dict(zip(cols, row))
    if mov.get('observaciones','').startswith('[ANULADO]'):
        conn.close(); return jsonify({'error': 'Movimiento ya anulado'}), 400
    if user not in ADMIN_USERS and mov.get('responsable','') != user:
        conn.close(); return jsonify({'error': 'Solo puedes anular tus propios movimientos o ser administrador'}), 403
    tipo_inv = 'Salida' if mov['tipo'] == 'Entrada' else 'Entrada'
    obs_contra = f'[ANULACION] del movimiento #{mov_id} ÃÂ¢ÃÂÃÂ {motivo} ÃÂ¢ÃÂÃÂ por {user}'
    c.execute("""INSERT INTO movimientos
                 (material_id, tipo, cantidad, unidad, lote_ref, responsable, observaciones, fecha)
                 VALUES (?,?,?,?,?,?,?,datetime('now'))""",
              (mov['material_id'], tipo_inv, mov['cantidad'], mov.get('unidad','g'),
               mov.get('lote_ref',''), user, obs_contra))
    c.execute("UPDATE movimientos SET observaciones=? WHERE id=?",
              ('[ANULADO] ' + (mov.get('observaciones') or ''), mov_id))
    c.execute("""INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                 VALUES (?,?,?,?,?,?,datetime('now'))""",
              (user, 'ANULAR_MOVIMIENTO', 'movimientos', str(mov_id),
               f'Anulado mov #{mov_id} ({mov["tipo"]} {mov["cantidad"]}g de {mov["material_id"]}) ÃÂ¢ÃÂÃÂ {motivo}',
               request.remote_addr))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'message': f'Movimiento #{mov_id} anulado. Contra-movimiento generado.',
                    'tipo_contramovimiento': tipo_inv})


@bp.route('/api/reset-movimientos', methods=['POST'])
def reset_mov():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado. Solo administradores.'}), 401
    d = request.json or {}
    if d.get('confirmacion','').upper() != 'BORRAR':
        return jsonify({'error': 'Debes enviar confirmacion="BORRAR"'}), 400
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("DELETE FROM movimientos")
    c.execute("""INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                 VALUES (?,?,?,?,?,?,datetime('now'))""",
              (session.get('compras_user','?'), 'RESET_MOVIMIENTOS', 'movimientos',
               'ALL', 'Borrado total de movimientos autorizado', request.remote_addr))
    conn.commit(); conn.close()
    return jsonify({'message': 'Movimientos borrados. Accion registrada en audit_log.'})

@bp.route('/rotulos/<producto_nombre>/<cantidad_str>')
def generar_rotulos(producto_nombre, cantidad_str):
    try: cantidad_kg = float(cantidad_str)
    except: return "<h2>Cantidad invalida</h2>", 400
    from datetime import date; import urllib.parse
    hoy = date.today().strftime('%d-%b-%Y').upper()
    prod = urllib.parse.unquote(producto_nombre); op_num = "OP-"+date.today().strftime('%Y%m%d'); cant_g = cantidad_kg*1000
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT material_id,material_nombre,porcentaje FROM formula_items WHERE producto_nombre=?", (prod,))
    items = c.fetchall()
    lotes = {}; incis = {}
    for r in items:
        mid = r[0]
        c.execute("SELECT nombre_inci FROM maestro_mps WHERE codigo_mp=?", (mid,)); ir=c.fetchone(); incis[mid]=ir[0] if ir and ir[0] else ''
        c.execute("SELECT lote,estanteria,posicion,fecha_vencimiento FROM movimientos WHERE material_id=? AND tipo='Entrada' AND lote IS NOT NULL AND lote!='' AND lote!='S/L' ORDER BY CASE WHEN fecha_vencimiento IS NULL OR fecha_vencimiento='' THEN '9999' ELSE fecha_vencimiento END ASC LIMIT 1", (mid,))
        row=c.fetchone(); lotes[mid]={'lote':row[0] if row else 'S/L','est':row[1] if row else '','pos':row[2] if row else '','vence':str(row[3])[:10] if row and row[3] else ''}
    conn.close()
    if not items: return '<h2>Formula no encontrada: '+prod+'</h2>', 404
    rhtml=''; barcodes=''
    for i,r in enumerate(items):
        mid,mnm,pct=r; peso=round((pct/100)*cant_g,2); info=lotes.get(mid,{}); lote_mp=info.get('lote','S/L')
        ubicacion=('Est. '+str(info.get('est',''))+str(info.get('pos',''))).strip(); vence=info.get('vence',''); inci=incis.get(mid,'')
        bv=mid+'|'+lote_mp; barcodes+=f'try{{JsBarcode("#bc{i}","{bv}",{{format:"CODE128",width:1.2,height:35,displayValue:false,margin:0}})}}catch(e){{}};'
        rhtml+='<div class="r"><div class="rh"><span class="rt">ROTULO MATERIA PRIMA DISPENSADA</span><span class="rc">PRD-PRO-001-F08 | v1<br>04-Mar-2025 / 03-Mar-2028</span></div>'
        rhtml+='<table><tr><td class="l">OP:</td><td class="v">'+op_num+'</td><td class="l">Fecha:</td><td class="v">'+hoy+'</td></tr>'
        rhtml+='<tr><td class="l">Producto:</td><td class="v big" colspan="3"><b>'+prod+'</b> &mdash; '+str(cantidad_kg)+' kg</td></tr>'
        rhtml+='<tr><td class="l">Nombre MP:</td><td class="v bold" colspan="3"><b>'+mnm+'</b> <span style="color:#888;font-size:0.8em;">('+mid+')</span></td></tr>'
        if inci: rhtml+='<tr><td class="l">Nombre INCI:</td><td class="v" colspan="3" style="font-size:0.82em;color:#444;">'+inci+'</td></tr>'
        rhtml+='<tr><td class="l">Lote MP:</td><td class="v bold">'+lote_mp+'</td><td class="l">Ubicacion:</td><td class="v">'+ubicacion+'</td></tr>'
        rhtml+='<tr><td class="l">Vencimiento:</td><td class="v" style="color:#c0392b;">'+vence+'</td><td class="l">% formula:</td><td class="v">'+str(pct)+'%</td></tr>'
        rhtml+='<tr><td class="l">Peso teorico:</td><td class="v peso">'+f"{peso:,.2f} g"+'</td><td class="l">Lote Prod.:</td><td class="blank"></td></tr>'
        rhtml+='<tr><td class="l">Tara:</td><td class="blank"></td><td class="l">Peso Neto:</td><td class="blank"></td></tr>'
        rhtml+='<tr><td class="l">Pesado por:</td><td class="blank firma"></td><td class="l">Verificado:</td><td class="blank firma"></td></tr>'
        rhtml+='</table>'
        rhtml+='<div style="text-align:center;padding:4px;"><svg id="bc'+str(i)+'"></svg></div>'
        rhtml+='<div class="rf">'+mid+'|'+lote_mp+' | #'+str(i+1)+' de '+str(len(items))+'</div></div>'
    css=('<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script><title>Rotulos</title>'
         '<script src="https://cdnjs.cloudflare.com/ajax/libs/jsbarcode/3.11.5/JsBarcode.all.min.js"></script>'
         '<style>*{margin:0;padding:0;box-sizing:border-box;}body{font-family:Arial,sans-serif;font-size:9pt;background:#eee;}'
         '.ph{background:#1a252f;color:white;padding:10px 16px;display:flex;justify-content:space-between;align-items:center;}'
         '.pbtn{background:#27ae60;color:white;border:none;padding:7px 18px;border-radius:4px;cursor:pointer;font-weight:bold;}'
         '.wrap{display:flex;flex-wrap:wrap;gap:5px;padding:8px;}'
         '.r{background:white;border:2px solid #1a252f;border-radius:3px;width:370px;page-break-inside:avoid;}'
         '.rh{background:#1a252f;color:white;padding:5px 8px;display:flex;justify-content:space-between;align-items:center;}'
         '.rt{font-weight:bold;font-size:8pt;}.rc{font-size:6.5pt;text-align:right;line-height:1.4;}'
         'table{width:100%;border-collapse:collapse;}td{border:1px solid #bbb;padding:3px 5px;vertical-align:middle;}'
         '.l{background:#ecf0f1;font-weight:bold;font-size:7.5pt;color:#1a252f;white-space:nowrap;width:27%;}'
         '.v{font-size:8.5pt;width:23%;}.bold{font-size:9pt;}.big{font-size:9pt;}'
         '.peso{background:#fff3cd;color:#c0392b;font-size:12pt;font-weight:bold;}'
         '.blank{height:20px;width:23%;}.firma{height:26px;}.rf{background:#ecf0f1;padding:2px 6px;font-size:6.5pt;color:#888;text-align:right;}'
         '@media print{body{background:white;}.ph{display:none;}.wrap{padding:0;gap:3px;}.r{width:48%;}@page{size:letter landscape;margin:7mm;}}'
         '</style></head><body>')
    return (css+'<div class="ph"><div><h2>Rotulos &mdash; '+prod+' &mdash; '+str(cantidad_kg)+' kg</h2>'
            '<div style="font-size:8pt;opacity:0.8;">'+op_num+' | '+str(len(items))+' MPs | '+hoy+'</div></div>'
            '<button class="pbtn" onclick="window.print()">Imprimir todos</button></div>'
            '<div class="wrap">'+rhtml+'</div>'
            '<script>window.onload=function(){'+barcodes+'};</script>'
            '</body></html>')

@bp.route('/rotulo-recepcion/<codigo>/<lote>/<cantidad_str>')
def rotulo_recepcion(codigo, lote, cantidad_str):
    try: cantidad = float(cantidad_str)
    except: return "<h2>Cantidad invalida</h2>", 400
    from datetime import date; import urllib.parse
    hoy = date.today().strftime('%d-%b-%Y').upper(); lote=urllib.parse.unquote(lote)
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT nombre_inci,nombre_comercial,tipo,proveedor FROM maestro_mps WHERE codigo_mp=?", (codigo,)); mp=c.fetchone()
    c.execute("SELECT fecha_vencimiento,estanteria,posicion FROM movimientos WHERE material_id=? AND lote=? ORDER BY fecha DESC LIMIT 1", (codigo,lote)); mov=c.fetchone(); conn.close()
    ni=mp[0] if mp else ''; nc=mp[1] if mp else codigo; tp=mp[2] if mp else ''; pv=mp[3] if mp else ''
    fv=str(mov[0])[:10] if mov and mov[0] else ''; ub=((mov[1] or '')+(mov[2] or '')) if mov else ''
    nr="REC-"+date.today().strftime('%Y%m%d')+"-"+codigo[-3:]; bv=codigo+'|'+lote
    h=('<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script><title>Rotulo Recepcion</title>'
       '<script src="https://cdnjs.cloudflare.com/ajax/libs/jsbarcode/3.11.5/JsBarcode.all.min.js"></script>'
       '<style>*{margin:0;padding:0;box-sizing:border-box;}body{font-family:Arial,sans-serif;font-size:10pt;background:#eee;padding:20px;}'
       '.ph{background:#1a252f;color:white;padding:10px 16px;display:flex;justify-content:space-between;margin-bottom:10px;}'
       '.pb{background:#27ae60;color:white;border:none;padding:7px 18px;border-radius:4px;cursor:pointer;font-weight:bold;}'
       '.r{background:white;border:3px solid #1a252f;border-radius:5px;max-width:520px;margin:auto;}'
       '.rh{background:#1a252f;color:white;padding:8px 12px;text-align:center;}'
       '.lote{background:#fff3cd;border:2px solid #f39c12;padding:10px;text-align:center;margin:10px;}'
       '.lnum{font-size:20pt;font-weight:bold;color:#c0392b;letter-spacing:2px;}'
       'table{width:100%;border-collapse:collapse;}td{border:1px solid #ccc;padding:6px 8px;}'
       '.l{background:#ecf0f1;font-weight:bold;font-size:8.5pt;width:35%;}'
       '@media print{.ph{display:none;}body{background:white;padding:0;}}'
       '</style></head><body>')
    h+=('<div class="ph"><b>Rotulo de Recepcion ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ Materia Prima</b><button class="pb" onclick="window.print()">Imprimir</button></div>'
        '<div class="r"><div class="rh">'
        '<span style="font-weight:bold;font-size:11pt;display:block;margin-bottom:2px;">ROTULO DE INGRESO DE MATERIA PRIMA</span>'
        '<span style="font-size:7.5pt;opacity:0.85;">Espagiria Laboratorios &nbsp;|&nbsp; COC-PRO-002-F07 &nbsp;|&nbsp; '+hoy+'</span>'
        '</div>'
        '<div class="lote"><div style="font-size:9pt;color:#888;margin-bottom:4px;">NUMERO DE LOTE ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ CODIGO DE BARRAS</div>'
        '<div class="lnum">'+lote+'</div>'
        '<svg id="bc" style="margin-top:6px;"></svg>'
        '<div style="font-size:7pt;color:#888;margin-top:2px;">'+bv+'</div>'
        '</div><table>'
        '<tr><td class="l">Codigo MP:</td><td style="font-weight:700;">'+codigo+'</td></tr>'
        '<tr><td class="l">Nombre INCI:</td><td style="font-size:0.9em;color:#1a5276;">'+ni+'</td></tr>'
        '<tr><td class="l">Nombre Comercial:</td><td style="font-weight:700;">'+nc+'</td></tr>'
        '<tr><td class="l">Tipo / Funcion:</td><td>'+tp+'</td></tr>'
        '<tr><td class="l">Proveedor:</td><td style="font-weight:700;">'+pv+'</td></tr>'
        '<tr><td class="l">Cantidad recibida:</td><td style="color:#27ae60;font-weight:700;">'+f"{cantidad:,.0f} g"+'</td></tr>'
        '<tr><td class="l">Fecha de recepcion:</td><td style="font-weight:700;">'+hoy+'</td></tr>'
        '<tr><td class="l">Fecha de vencimiento:</td><td style="color:#c0392b;font-weight:700;">'+fv+'</td></tr>'
        '<tr><td class="l">Fecha de analisis:</td><td style="height:28px;background:#fffde7;"></td></tr>'
        '<tr style="background:#e8f5e9;"><td class="l" style="color:#1b5e20;font-weight:800;">Estado de calidad:</td>'
        '<td style="height:28px;"><span style="margin-right:18px;">&#9744; Aprobado</span><span style="margin-right:18px;">&#9744; En cuarentena</span><span>&#9744; Rechazado</span></td></tr>'
        '<tr><td class="l">Ubicacion:</td><td>Est. '+ub+'</td></tr>'
        '<tr><td class="l">N de Recepcion:</td><td>'+nr+'</td></tr>'
        '<tr><td class="l">Recibido por:</td><td style="height:30px;"></td></tr>'
        '<tr><td class="l">Analizado / Aprobado por:</td><td style="height:30px;"></td></tr>'
        '</table>'
        '<div style="background:#ecf0f1;padding:4px 10px;font-size:7.5pt;color:#888;text-align:center;">'
        'COC-PRO-002-F07 &nbsp;|&nbsp; Ingreso registrado al sistema &nbsp;|&nbsp; '+hoy
        +'</div>'
        '</div>'
        '<script>window.onload=function(){try{JsBarcode("#bc","'+bv+'",{format:"CODE128",width:1.5,height:45,displayValue:false,margin:0});}catch(e){}}</script>'
        '</body></html>')
    return h


@bp.route('/rotulo-recepcion-mee/<codigo>/<cantidad_str>')
def rotulo_recepcion_mee(codigo, cantidad_str):
    try: cantidad = int(float(cantidad_str))
    except: return "<h2>Cantidad invalida</h2>", 400
    from datetime import date; import urllib.parse
    hoy = date.today().strftime('%d-%b-%Y').upper()
    codigo = urllib.parse.unquote(codigo)
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT descripcion, categoria, proveedor FROM maestro_mee WHERE codigo=?", (codigo,))
        mee = c.fetchone()
        c.execute("SELECT lote_ref, responsable, fecha FROM movimientos_mee WHERE mee_codigo=? AND tipo='Entrada' AND anulado=0 ORDER BY id DESC LIMIT 1", (codigo,))
        mov = c.fetchone(); conn.close()
    except Exception as e:
        return "<h2>Error DB: " + str(e) + "</h2>", 500
    desc = mee[0] if mee else codigo; cat = mee[1] if mee else ''; prov = mee[2] if mee else ''
    ref  = mov[0] if mov else ''; oper = mov[1] if mov else ''
    nr   = "REC-MEE-" + date.today().strftime('%Y%m%d') + "-" + codigo[-4:]
    bv   = codigo; prov_display = ref or prov
    h = ('<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
         '<script src="https://cdnjs.cloudflare.com/ajax/libs/jsbarcode/3.11.5/JsBarcode.all.min.js"></script>'
         '<style>*{margin:0;padding:0;box-sizing:border-box;}body{font-family:Arial,sans-serif;font-size:10pt;background:#eee;padding:20px;}'
         '.ph{background:#1a3a5c;color:white;padding:10px 16px;display:flex;justify-content:space-between;margin-bottom:10px;}'
         '.pb{background:#2980b9;color:white;border:none;padding:7px 18px;border-radius:4px;cursor:pointer;font-weight:bold;}'
         '.r{background:white;border:3px solid #1a3a5c;border-radius:5px;max-width:520px;margin:auto;}'
         '.rh{background:#1a3a5c;color:white;padding:8px 12px;text-align:center;}'
         '.lote{background:#e8f4fd;border:2px solid #2980b9;padding:10px;text-align:center;margin:10px;}'
         '.lnum{font-size:16pt;font-weight:bold;color:#1a3a5c;letter-spacing:2px;}'
         'table{width:100%;border-collapse:collapse;}td{border:1px solid #ccc;padding:6px 8px;}'
         '.l{background:#ecf0f1;font-weight:bold;font-size:8.5pt;width:38%;}'
         '.calidad{background:#e8f5e9;}'
         '@media print{.ph{display:none;}body{background:white;padding:0;}}'
         '</style></head><body>')
    h += ('<div class="ph"><b>RÃÂÃÂÃÂÃÂ³tulo de RecepciÃÂÃÂÃÂÃÂ³n ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ Material E&E</b>'
          '<button class="pb" onclick="window.print()">Imprimir</button></div>'
          '<div class="r"><div class="rh">'
          '<span style="font-weight:bold;font-size:11pt;display:block;margin-bottom:2px;">ROTULO DE INGRESO DE MATERIAL E&E</span>'
          '<span style="font-size:7.5pt;opacity:0.85;">Espagiria Laboratorios &nbsp;|&nbsp; COC-PRO-002-F07 &nbsp;|&nbsp; ' + hoy + '</span>'
          '</div>'
          '<div class="lote">'
          '<div style="font-size:9pt;color:#666;margin-bottom:4px;">CODIGO MATERIAL ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ CODIGO DE BARRAS</div>'
          '<div class="lnum">' + codigo + '</div>'
          '<svg id="bc" style="margin-top:6px;"></svg>'
          '</div><table>'
          '<tr><td class="l">CÃÂÃÂÃÂÃÂ³digo MEE:</td><td style="font-weight:700;">' + codigo + '</td></tr>'
          '<tr><td class="l">DescripciÃÂÃÂÃÂÃÂ³n:</td><td style="font-weight:700;">' + desc + '</td></tr>'
          '<tr><td class="l">CategorÃÂÃÂÃÂÃÂ­a:</td><td>' + cat + '</td></tr>'
          '<tr><td class="l">Proveedor / Ref. compra:</td><td style="font-weight:700;">' + prov_display + '</td></tr>'
          '<tr><td class="l">Cantidad recibida:</td><td style="color:#27ae60;font-weight:700;">' + f"{cantidad:,}" + ' unidades</td></tr>'
          '<tr><td class="l">Fecha de recepciÃÂÃÂÃÂÃÂ³n:</td><td style="font-weight:700;">' + hoy + '</td></tr>'
          '<tr><td class="l">Fecha de anÃÂÃÂÃÂÃÂ¡lisis / inspecciÃÂÃÂÃÂÃÂ³n:</td><td style="height:28px;background:#fffde7;"></td></tr>'
          '<tr><td class="l">Piezas inspeccionadas (AQL):</td><td style="height:28px;"></td></tr>'
          '<tr class="calidad"><td class="l calidad" style="color:#1b5e20;font-weight:800;">Estado de calidad:</td>'
          '<td style="height:28px;"><span style="margin-right:14px;">&#9744; Aprobado</span>'
          '<span style="margin-right:14px;">&#9744; En cuarentena</span>'
          '<span>&#9744; Rechazado</span></td></tr>'
          '<tr><td class="l">NÃÂÃÂÃÂÃÂºmero de recepciÃÂÃÂÃÂÃÂ³n:</td><td>' + nr + '</td></tr>'
          '<tr><td class="l">Recibido por:</td><td style="height:30px;">' + oper + '</td></tr>'
          '<tr><td class="l">Aprobado por (Calidad):</td><td style="height:30px;"></td></tr>'
          '</table>'
          '<div style="background:#dde8f0;padding:4px 10px;font-size:7.5pt;color:#555;text-align:center;">'
          'COC-PRO-002-F07 &nbsp;|&nbsp; Material Envase & Empaque &nbsp;|&nbsp; ' + hoy + '</div>'
          '</div>'
          '<script>window.onload=function(){try{JsBarcode("#bc","' + bv + '",{format:"CODE128",width:1.5,height:45,displayValue:false,margin:0});}catch(e){}}</script>'
          '</body></html>')
    return h



@bp.route('/api/ordenes-compra/pendientes-recepcion')
def ocs_pendientes_recepcion():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT oc.numero_oc, oc.proveedor, oc.fecha, oc.valor_total,
                        oci.codigo_mp, oci.nombre_mp, oci.cantidad_g, oci.precio_unitario
                 FROM ordenes_compra oc
                 JOIN ordenes_compra_items oci ON oc.numero_oc = oci.numero_oc
                 WHERE oc.estado IN ('Aprobada','Enviada','Parcial')
                 ORDER BY oc.fecha DESC""")
    rows = c.fetchall(); conn.close()
    ocs = {}
    for r in rows:
        num = r[0]
        if num not in ocs:
            ocs[num] = {'numero_oc': num, 'proveedor': r[1], 'fecha': r[2],
                        'valor_total': r[3], 'items': []}
        ocs[num]['items'].append({'codigo_mp': r[4], 'nombre_mp': r[5],
                                   'cantidad_g': r[6], 'precio_unitario': r[7]})
    return jsonify(list(ocs.values()))

@bp.route('/api/trazabilidad/lote/<path:lote>')
def trazabilidad_lote_path(lote):
    import urllib.parse; lote = urllib.parse.unquote(lote)
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT id, material_id, material_nombre, cantidad, tipo, fecha,
                        observaciones, proveedor, precio_kg, numero_factura, numero_oc
                 FROM movimientos WHERE lote=? ORDER BY fecha""", (lote,))
    cols = [d[0] for d in c.description]
    movs = [dict(zip(cols, r)) for r in c.fetchall()]
    c.execute("""SELECT id, producto, cantidad, fecha, observaciones, operador
                 FROM producciones WHERE observaciones LIKE ? ORDER BY fecha""", (f'%{lote}%',))
    cols2 = [d[0] for d in c.description]
    prods = [dict(zip(cols2, r)) for r in c.fetchall()]
    c.execute("""SELECT d.numero, cl.nombre, d.fecha, d.estado
                 FROM despachos d LEFT JOIN clientes cl ON d.cliente_id=cl.id
                 WHERE d.observaciones LIKE ?""", (f'%{lote}%',))
    cols3 = [d[0] for d in c.description]
    desps = [dict(zip(cols3, r)) for r in c.fetchall()]
    conn.close()
    return jsonify({'lote': lote, 'movimientos': movs, 'producciones': prods, 'despachos': desps})

@bp.route('/api/mp/<codigo>/historial-precios')
def historial_precios_mp(codigo):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT fecha, proveedor, precio_kg, valor_total, numero_factura, numero_oc
                 FROM movimientos WHERE material_id=? AND tipo='Entrada' AND precio_kg>0
                 ORDER BY fecha DESC LIMIT 24""", (codigo,))
    hist = [{'fecha':r[0],'proveedor':r[1],'precio_kg':r[2],'valor_total':r[3],'factura':r[4],'oc':r[5]} for r in c.fetchall()]
    c.execute("SELECT precio_referencia, proveedor FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    mp = c.fetchone(); conn.close()
    return jsonify({'codigo': codigo, 'precio_referencia': mp[0] if mp else 0,
                    'proveedor_habitual': mp[1] if mp else '', 'historial': hist})

@bp.route('/api/mp/<codigo>/consumo-historico')
def consumo_historico_mp(codigo):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT substr(fecha,1,7) as mes,
                        SUM(CASE WHEN tipo='Salida' THEN cantidad ELSE 0 END) as consumo_g,
                        COUNT(CASE WHEN tipo='Salida' THEN 1 END) as n_salidas
                 FROM movimientos WHERE material_id=?
                 GROUP BY substr(fecha,1,7) ORDER BY mes DESC LIMIT 12""", (codigo,))
    meses = [{'mes':r[0],'consumo_g':r[1],'n_salidas':r[2]} for r in c.fetchall()]
    consumos = [m['consumo_g'] for m in meses if m['consumo_g'] and m['consumo_g'] > 0]
    promedio = sum(consumos)/len(consumos) if consumos else 0
    c.execute("SELECT lead_time_dias, stock_minimo FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    mp = c.fetchone(); conn.close()
    lead = (mp[0] if mp and mp[0] else 7)
    stock_min = (mp[1] if mp and mp[1] else 0)
    punto_reorden = (promedio/30) * lead + stock_min
    return jsonify({'codigo': codigo, 'meses': meses,
                    'promedio_mes_g': round(promedio, 0),
                    'consumo_diario_g': round(promedio/30, 1),
                    'lead_time_dias': lead,
                    'punto_reorden_g': round(punto_reorden, 0)})

@bp.route('/api/conteos', methods=['GET','POST'])
def conteos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        num = 'CNT-' + datetime.now().strftime('%Y%m%d-%H%M')
        c.execute("""INSERT INTO conteos_fisicos (numero,fecha_inicio,estado,responsable,observaciones)
                     VALUES (?,?,'Abierto',?,?)""",
                  (num, datetime.now().isoformat(), d.get('responsable',''), d.get('observaciones','')))
        cid = c.lastrowid
        c.execute("""SELECT mp.codigo_mp, mp.nombre_comercial,
                            COALESCE(SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad
                                         WHEN m.tipo='Salida' THEN -m.cantidad ELSE 0 END),0)
                     FROM maestro_mps mp
                     LEFT JOIN movimientos m ON mp.codigo_mp=m.material_id
                     WHERE mp.activo=1 GROUP BY mp.codigo_mp""")
        mps = c.fetchall()
        for mp in mps:
            c.execute("INSERT INTO conteo_items (conteo_id,codigo_mp,nombre_mp,stock_sistema) VALUES (?,?,?,?)",
                      (cid, mp[0], mp[1], max(0, mp[2])))
        c.execute("UPDATE conteos_fisicos SET total_items=? WHERE id=?", (len(mps), cid))
        conn.commit(); conn.close()
        return jsonify({'numero': num, 'id': cid, 'total_items': len(mps)}), 201
    c.execute("SELECT id,numero,fecha_inicio,estado,responsable,total_items,items_diferencia FROM conteos_fisicos ORDER BY fecha_inicio DESC LIMIT 20")
    rows = [{'id':r[0],'numero':r[1],'fecha':r[2],'estado':r[3],'responsable':r[4],'total':r[5],'diffs':r[6]} for r in c.fetchall()]
    conn.close(); return jsonify(rows)

@bp.route('/api/conteos/<int:cid>', methods=['GET','PATCH'])
def conteo_detalle(cid):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'PATCH':
        d = request.json or {}; accion = d.get('accion')
        if accion == 'registrar_fisico':
            sf = float(d.get('stock_fisico', 0))
            c.execute("""UPDATE conteo_items SET stock_fisico=?,diferencia=?-stock_sistema,observaciones=?
                         WHERE conteo_id=? AND codigo_mp=?""",
                      (sf, sf, d.get('observaciones',''), cid, d.get('codigo_mp')))
            c.execute("""UPDATE conteos_fisicos SET
                         items_diferencia=(SELECT COUNT(*) FROM conteo_items
                                          WHERE conteo_id=? AND stock_fisico IS NOT NULL AND ABS(diferencia)>0.1)
                         WHERE id=?""", (cid, cid))
        elif accion == 'cerrar':
            c.execute("UPDATE conteos_fisicos SET estado='Cerrado',fecha_cierre=?,aprobado_por=? WHERE id=?",
                      (datetime.now().isoformat(), d.get('aprobado_por',''), cid))
        elif accion == 'aplicar_ajustes':
            c.execute("SELECT codigo_mp,nombre_mp,diferencia FROM conteo_items WHERE conteo_id=? AND ABS(diferencia)>0.1 AND ajuste_aplicado=0", (cid,))
            for cod, nom, dif in c.fetchall():
                tipo = 'Entrada' if dif > 0 else 'Salida'
                c.execute("""INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,fecha,observaciones,estado_lote,operador)
                             VALUES (?,?,?,?,?,?,'VIGENTE',?)""",
                          (cod, nom, abs(dif), tipo, datetime.now().isoformat(), f'Ajuste conteo {cid}', d.get('responsable','')))
                c.execute("UPDATE conteo_items SET ajuste_aplicado=1 WHERE conteo_id=? AND codigo_mp=?", (cid, cod))
        conn.commit()
        c.execute("SELECT id,numero,estado,total_items,items_diferencia FROM conteos_fisicos WHERE id=?", (cid,))
        r = c.fetchone(); conn.close()
        return jsonify({'id':r[0],'numero':r[1],'estado':r[2],'total':r[3],'diffs':r[4]})
    c.execute("SELECT * FROM conteos_fisicos WHERE id=?", (cid,)); h = c.fetchone()
    if not h: conn.close(); return jsonify({'error':'No encontrado'}), 404
    c.execute("SELECT codigo_mp,nombre_mp,stock_sistema,stock_fisico,diferencia,ajuste_aplicado,observaciones FROM conteo_items WHERE conteo_id=? ORDER BY nombre_mp", (cid,))
    items = [{'codigo':r[0],'nombre':r[1],'sistema':r[2],'fisico':r[3],'diff':r[4],'ajustado':r[5],'obs':r[6]} for r in c.fetchall()]
    conn.close()
    return jsonify({'header':{'id':h[0],'numero':h[1],'estado':h[4],'responsable':h[5],'total':h[7],'diffs':h[8]},'items':items})


@bp.route('/api/lotes/cuarentena/<int:mov_id>/liberar', methods=['POST'])
def liberar_cuarentena(mov_id):
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error':'Solo admins pueden liberar cuarentena'}), 401
    d = request.json or {}; decision = d.get('decision','Aprobado')
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    nuevo_estado = 'VIGENTE' if decision == 'Aprobado' else 'RECHAZADO'
    c.execute("UPDATE movimientos SET estado_lote=? WHERE id=?", (nuevo_estado, mov_id))
    c.execute("""INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                 VALUES (?,?,?,?,?,?,datetime('now'))""",
              (session['compras_user'], f'{decision.upper()}_CUARENTENA', 'movimientos',
               str(mov_id), d.get('observaciones',''), request.remote_addr))
    conn.commit(); conn.close()
    return jsonify({'ok':True, 'decision':decision, 'estado':nuevo_estado})

@bp.route('/api/maestro-mp/<codigo>/precio', methods=['POST'])
def actualizar_precio_mp(codigo):
    d = request.json or {}; precio = float(d.get('precio_kg', 0))
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE maestro_mps SET precio_referencia=?,ultima_act_precio=? WHERE codigo_mp=?",
              (precio, datetime.now().isoformat()[:10], codigo))
    c.execute("""INSERT INTO precios_mp_historico (codigo_mp,proveedor,precio_kg,fecha,origen,observaciones)
                 VALUES (?,?,?,?,?,?)""",
              (codigo, d.get('proveedor',''), precio, datetime.now().isoformat()[:10],
               d.get('origen','manual'), d.get('observaciones','')))
    conn.commit(); conn.close()
    return jsonify({'ok':True, 'precio_kg':precio})


@bp.route('/api/admin/backfill-precios-mp', methods=['POST'])
def backfill_precios_mp():
    """Pobla precio_referencia en maestro_mps desde movimientos.precio_kg y precios_mp_historico.
    Solo actualiza MPs que tienen precio_referencia=0 o nulo."""
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    actualizados = 0
    # Fuente 1: promedio ponderado de movimientos de entrada con precio registrado
    c.execute("""SELECT material_id, AVG(precio_kg) as avg_precio
                 FROM movimientos
                 WHERE tipo='Entrada' AND precio_kg IS NOT NULL AND precio_kg > 0
                 GROUP BY material_id""")
    from_movs = c.fetchall()
    for mat_id, avg_p in from_movs:
        c.execute("""UPDATE maestro_mps SET precio_referencia=?, ultima_act_precio=datetime('now')
                     WHERE codigo_mp=? AND (precio_referencia IS NULL OR precio_referencia=0)""",
                  (round(avg_p, 2), mat_id))
        actualizados += c.rowcount
    # Fuente 2: precios_mp_historico (precio mÃÂÃÂÃÂÃÂ¡s reciente por MP)
    c.execute("""SELECT codigo_mp, precio_kg FROM precios_mp_historico
                 WHERE (codigo_mp, fecha) IN (
                     SELECT codigo_mp, MAX(fecha) FROM precios_mp_historico
                     WHERE precio_kg > 0 GROUP BY codigo_mp
                 )""")
    from_hist = c.fetchall()
    hist_count = 0
    for codigo, precio in from_hist:
        c.execute("""UPDATE maestro_mps SET precio_referencia=?, ultima_act_precio=datetime('now')
                     WHERE codigo_mp=? AND (precio_referencia IS NULL OR precio_referencia=0)""",
                  (round(precio, 2), codigo))
        hist_count += c.rowcount
    actualizados += hist_count
    # Stats
    c.execute("SELECT COUNT(*) FROM maestro_mps WHERE precio_referencia > 0")
    con_precio = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM maestro_mps WHERE activo=1")
    total_activos = c.fetchone()[0]
    conn.commit(); conn.close()
    return jsonify({
        'ok': True,
        'actualizados': actualizados,
        'con_precio_ahora': con_precio,
        'total_activos': total_activos,
        'cobertura_pct': round(con_precio / total_activos * 100, 1) if total_activos > 0 else 0
    })


# ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂ
#  MAQUILA 360 ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ API
# ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂ


# ===========================================================================
# MODULO MEE - Material de Empaque y Envase  (Tasks #70 #71 #72)
# ===========================================================================

def _init_mee_movimientos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS movimientos_mee (
        id          INTEGER  PRIMARY KEY AUTOINCREMENT,
        mee_codigo  TEXT     NOT NULL,
        tipo        TEXT     NOT NULL CHECK(tipo IN ('Entrada','Salida','Ajuste')),
        cantidad    REAL     NOT NULL,
        unidad      TEXT     DEFAULT 'und',
        lote_ref    TEXT     DEFAULT '',
        batch_ref   TEXT     DEFAULT '',
        responsable TEXT     DEFAULT '',
        observaciones TEXT   DEFAULT '',
        fecha       DATETIME DEFAULT (datetime('now')),
        anulado     INTEGER  DEFAULT 0
    )""")
    conn.commit(); conn.close()

_init_mee_movimientos()


@bp.route('/api/mee', methods=['POST'])
def mee_crear():
    if 'compras_user' not in session:return jsonify({'error':'Autenticacion requerida'}),401
    d=request.json or {};cod=d.get('codigo','').strip().upper();desc=d.get('descripcion','').strip()
    if not cod or not desc:return jsonify({'error':'codigo y descripcion requeridos'}),400
    cat=d.get('categoria','Otro');prov=d.get('proveedor','');und=d.get('unidad','und')
    sa=float(d.get('stock_actual',0));sm=float(d.get('stock_minimo',0))
    conn=sqlite3.connect(DB_PATH);c=conn.cursor()
    try:c.execute("INSERT INTO maestro_mee(codigo,descripcion,categoria,unidad,proveedor,stock_actual,stock_minimo,estado)VALUES(?,?,?,?,?,?,?,'Activo')",(cod,desc,cat,und,prov,sa,sm));conn.commit()
    except Exception as e:conn.close();return jsonify({'error':str(e)}),400
    conn.close();return jsonify({'ok':True,'codigo':cod,'message':f'Material {cod} creado'})


@bp.route('/api/mee/stock', methods=['GET'])
def mee_stock_list():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    cat_f = request.args.get('categoria', '')
    sql = """
        SELECT m.codigo, m.descripcion, m.categoria, m.unidad,
               m.stock_actual, m.stock_minimo, m.estado, m.proveedor,
               COALESCE(mv.ultima_entrada,'') as ultima_entrada,
               COALESCE(mv.ultima_salida,'')  as ultima_salida,
               COALESCE(mv.total_entradas,0)  as total_entradas,
               COALESCE(mv.total_salidas,0)   as total_salidas
        FROM maestro_mee m
        LEFT JOIN (
            SELECT mee_codigo,
                   MAX(CASE WHEN tipo='Entrada' AND anulado=0 THEN fecha END) as ultima_entrada,
                   MAX(CASE WHEN tipo='Salida'  AND anulado=0 THEN fecha END) as ultima_salida,
                   SUM(CASE WHEN tipo='Entrada' AND anulado=0 THEN cantidad ELSE 0 END) as total_entradas,
                   SUM(CASE WHEN tipo='Salida'  AND anulado=0 THEN cantidad ELSE 0 END) as total_salidas
            FROM movimientos_mee GROUP BY mee_codigo
        ) mv ON m.codigo = mv.mee_codigo
        WHERE m.estado='Activo'
    """
    params = []
    if cat_f:
        sql += " AND m.categoria=?"; params.append(cat_f)
    sql += " ORDER BY m.categoria, m.descripcion"
    c.execute(sql, params)
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    from datetime import date
    hoy = date.today()
    for r in rows:
        s, mn = r['stock_actual'] or 0, r['stock_minimo'] or 0
        if mn > 0:
            ratio = s / mn
            if ratio <= 0:    r['alerta'] = 'critico'
            elif ratio < 1:   r['alerta'] = 'bajo'
            elif ratio < 1.5: r['alerta'] = 'advertencia'
            else:             r['alerta'] = 'ok'
        else:
            r['alerta'] = 'sin_minimo'
        ref = r['ultima_entrada'] or r['ultima_salida']
        if ref:
            try:
                days = (hoy - date.fromisoformat(ref[:10])).days
                r['dias_sin_mov'] = days; r['obsoleto'] = days > 90
            except Exception:
                r['dias_sin_mov'] = None; r['obsoleto'] = False
        else:
            r['dias_sin_mov'] = None; r['obsoleto'] = s > 0
    c.execute("SELECT DISTINCT categoria FROM maestro_mee WHERE estado='Activo' ORDER BY categoria")
    categorias = [row[0] for row in c.fetchall()]
    c.execute("SELECT COUNT(*) FROM maestro_mee WHERE estado='Activo'"); total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM maestro_mee WHERE estado='Activo' AND stock_minimo>0 AND stock_actual<stock_minimo"); bajo = c.fetchone()[0]
    conn.close()
    return jsonify({'items': rows, 'categorias': categorias, 'total': total, 'bajo_minimo': bajo})


@bp.route('/api/mee/movimiento', methods=['POST'])
def mee_registrar_movimiento():
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    d = request.json or {}
    codigo = d.get('codigo','').strip(); tipo = d.get('tipo','').strip()
    cantidad = float(d.get('cantidad', 0)); unidad = d.get('unidad','und').strip()
    lote_ref = d.get('lote_ref','').strip(); batch_ref = d.get('batch_ref','').strip()
    responsable = d.get('responsable', session.get('compras_user','')).strip()
    obs = d.get('observaciones','').strip()
    if not codigo or tipo not in ('Entrada','Salida','Ajuste') or cantidad <= 0:
        return jsonify({'error': 'codigo, tipo y cantidad>0 requeridos'}), 400
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT codigo, descripcion, stock_actual, unidad FROM maestro_mee WHERE codigo=?", (codigo,))
    mee = c.fetchone()
    if not mee:
        conn.close(); return jsonify({'error': 'Codigo MEE no encontrado'}), 404
    c.execute("""INSERT INTO movimientos_mee
                 (mee_codigo, tipo, cantidad, unidad, lote_ref, batch_ref, responsable, observaciones)
                 VALUES (?,?,?,?,?,?,?,?)""",
              (codigo, tipo, cantidad, unidad, lote_ref, batch_ref, responsable, obs))
    mov_id = c.lastrowid
    if tipo == 'Entrada':
        c.execute("UPDATE maestro_mee SET stock_actual=stock_actual+? WHERE codigo=?", (cantidad, codigo))
    elif tipo == 'Salida':
        c.execute("UPDATE maestro_mee SET stock_actual=MAX(0,stock_actual-?) WHERE codigo=?", (cantidad, codigo))
    else:
        c.execute("UPDATE maestro_mee SET stock_actual=? WHERE codigo=?", (cantidad, codigo))
    c.execute("SELECT stock_actual, stock_minimo FROM maestro_mee WHERE codigo=?", (codigo,))
    s_new, s_min = c.fetchone()
    conn.commit(); conn.close()
    alerta = None
    if s_min and s_min > 0 and s_new < s_min:
        alerta = 'Stock bajo minimo: ' + str(int(s_new)) + ' ' + unidad + ' (minimo: ' + str(int(s_min)) + ')'
    return jsonify({'ok': True, 'movimiento_id': mov_id, 'stock_nuevo': s_new, 'alerta': alerta,
                    'message': tipo + ' de ' + str(int(cantidad)) + ' ' + unidad + ' registrada para ' + mee[1]})


@bp.route('/api/mee/movimientos', methods=['GET'])
def mee_historial_movimientos():
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    codigo = request.args.get('codigo',''); tipo = request.args.get('tipo','')
    limit = min(int(request.args.get('limit', 50)), 200)
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    sql = """SELECT mv.id, mv.mee_codigo, COALESCE(m.descripcion,'') as descripcion,
                    mv.tipo, mv.cantidad, mv.unidad, mv.lote_ref, mv.batch_ref,
                    mv.responsable, mv.observaciones, mv.fecha, mv.anulado
             FROM movimientos_mee mv LEFT JOIN maestro_mee m ON mv.mee_codigo=m.codigo
             WHERE mv.anulado=0"""
    params = []
    if codigo: sql += " AND mv.mee_codigo=?"; params.append(codigo)
    if tipo:   sql += " AND mv.tipo=?"; params.append(tipo)
    sql += " ORDER BY mv.fecha DESC LIMIT " + str(limit)
    c.execute(sql, params)
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return jsonify({'movimientos': rows, 'total': len(rows)})


@bp.route('/api/mee/alertas', methods=['GET'])
def mee_alertas_list():
    from datetime import date, timedelta
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    hace90 = (date.today() - timedelta(days=90)).isoformat()
    c.execute("""SELECT m.codigo, m.descripcion, m.categoria, m.stock_actual, m.stock_minimo, m.unidad
                 FROM maestro_mee m WHERE m.estado='Activo' AND m.stock_minimo>0 AND m.stock_actual<m.stock_minimo
                 ORDER BY (m.stock_actual/m.stock_minimo) ASC""")
    bajo_minimo = [{'codigo':r[0],'descripcion':r[1],'categoria':r[2],'stock_actual':r[3],
                    'stock_minimo':r[4],'unidad':r[5],'ratio':round(r[3]/r[4],2) if r[4] else 0} for r in c.fetchall()]
    c.execute("""SELECT m.codigo, m.descripcion, m.categoria, m.stock_actual, m.unidad, MAX(mv.fecha) as ultimo_mov
                 FROM maestro_mee m LEFT JOIN movimientos_mee mv ON m.codigo=mv.mee_codigo AND mv.anulado=0
                 WHERE m.estado='Activo' AND m.stock_actual>0 GROUP BY m.codigo
                 HAVING ultimo_mov IS NULL OR ultimo_mov < ? ORDER BY ultimo_mov ASC LIMIT 15""", (hace90,))
    obsolescencia = [{'codigo':r[0],'descripcion':r[1],'categoria':r[2],'stock_actual':r[3],
                      'unidad':r[4],'ultimo_mov':r[5] or 'Nunca'} for r in c.fetchall()]
    c.execute("SELECT COUNT(*) FROM maestro_mee WHERE estado='Activo'"); total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM maestro_mee WHERE estado='Activo' AND stock_minimo>0 AND stock_actual<stock_minimo"); n_bajo = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM movimientos_mee WHERE anulado=0 AND fecha>=date('now','-7 days')"); mov_sem = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM movimientos_mee WHERE tipo='Entrada' AND anulado=0 AND fecha>=date('now','-30 days')"); ent_mes = c.fetchone()[0]
    conn.close()
    return jsonify({'bajo_minimo': bajo_minimo, 'obsolescencia': obsolescencia,
                    'resumen': {'total_mee': total, 'bajo_minimo': n_bajo,
                                'movimientos_semana': mov_sem, 'entradas_mes': ent_mes}})


@bp.route('/api/mee/trazabilidad', methods=['GET'])
def mee_trazabilidad():
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    batch = request.args.get('batch','').strip(); codigo = request.args.get('codigo','').strip()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if batch:
        c.execute("""SELECT mv.id, mv.mee_codigo, COALESCE(m.descripcion,'') as descripcion,
                            m.categoria, mv.cantidad, mv.unidad, mv.responsable, mv.fecha, mv.observaciones
                     FROM movimientos_mee mv LEFT JOIN maestro_mee m ON mv.mee_codigo=m.codigo
                     WHERE mv.batch_ref LIKE ? AND mv.tipo='Salida' AND mv.anulado=0
                     ORDER BY mv.fecha""", ('%' + batch + '%',))
        cols = [d[0] for d in c.description]
        consumos = [dict(zip(cols, r)) for r in c.fetchall()]
        conn.close()
        return jsonify({'tipo':'batch','referencia':batch,'consumos':consumos,'total':len(consumos)})
    elif codigo:
        c.execute("""SELECT mv.id, mv.tipo, mv.batch_ref, mv.lote_ref, mv.cantidad, mv.unidad,
                            mv.responsable, mv.fecha, mv.observaciones
                     FROM movimientos_mee mv WHERE mv.mee_codigo=? AND mv.anulado=0
                     ORDER BY mv.fecha DESC LIMIT 100""", (codigo,))
        cols = [d[0] for d in c.description]
        historial = [dict(zip(cols, r)) for r in c.fetchall()]
        conn.close()
        return jsonify({'tipo':'mee','referencia':codigo,'historial':historial,'total':len(historial)})
    conn.close()
    return jsonify({'error': 'Proporcione parametro batch o codigo'}), 400


@bp.route('/api/mee/anular/<int:mov_id>', methods=['POST'])
def mee_anular_movimiento(mov_id):
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    user = session.get('compras_user','')
    payload = request.json or {}
    motivo = payload.get('motivo','').strip()
    if not motivo:
        return jsonify({'error': 'Motivo obligatorio'}), 400
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT * FROM movimientos_mee WHERE id=?", (mov_id,))
    row = c.fetchone()
    if not row: conn.close(); return jsonify({'error': 'No encontrado'}), 404
    cols_mv = [d[0] for d in c.description]; mv = dict(zip(cols_mv, row))
    if mv['anulado']: conn.close(); return jsonify({'error': 'Ya anulado'}), 400
    if mv['tipo'] == 'Entrada':
        c.execute("UPDATE maestro_mee SET stock_actual=MAX(0,stock_actual-?) WHERE codigo=?", (mv['cantidad'],mv['mee_codigo']))
    elif mv['tipo'] == 'Salida':
        c.execute("UPDATE maestro_mee SET stock_actual=stock_actual+? WHERE codigo=?", (mv['cantidad'],mv['mee_codigo']))
    c.execute("UPDATE movimientos_mee SET anulado=1, observaciones=observaciones||? WHERE id=?",
              (' [ANULADO por ' + user + ': ' + motivo + ']', mov_id))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'message': 'Movimiento #' + str(mov_id) + ' anulado y stock revertido'})



# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
#  ACONDICIONAMIENTO + LIBERACIÃN â Fase 4
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def _init_acondicionamiento():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS acondicionamiento (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        produccion_id       INTEGER DEFAULT 0,
        lote                TEXT NOT NULL DEFAULT '',
        producto            TEXT NOT NULL DEFAULT '',
        cantidad_batch_g    REAL DEFAULT 0,
        unidades_producidas INTEGER DEFAULT 0,
        presentacion        TEXT DEFAULT '',
        mee_consumido       TEXT DEFAULT '[]',
        fecha               TEXT DEFAULT (date('now')),
        operador            TEXT DEFAULT '',
        observaciones       TEXT DEFAULT '',
        estado              TEXT DEFAULT 'En proceso',
        creado_en           DATETIME DEFAULT (datetime('now'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS liberaciones (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        acondicionamiento_id    INTEGER DEFAULT 0,
        lote                    TEXT NOT NULL DEFAULT '',
        producto                TEXT NOT NULL DEFAULT '',
        unidades                INTEGER DEFAULT 0,
        presentacion            TEXT DEFAULT '',
        fecha_produccion        TEXT DEFAULT '',
        fecha_liberacion        TEXT DEFAULT '',
        aprobado_por            TEXT DEFAULT '',
        cliente                 TEXT DEFAULT '',
        destino                 TEXT DEFAULT 'ANIMUS',
        observaciones           TEXT DEFAULT '',
        estado                  TEXT DEFAULT 'Pendiente CC',
        creado_en               DATETIME DEFAULT (datetime('now'))
    )""")
    conn.commit(); conn.close()

_init_acondicionamiento()


@bp.route('/api/acondicionamiento', methods=['GET', 'POST'])
def acondicionamiento_list():
    if 'compras_user' not in session: return jsonify({'error': 'Autenticacion requerida'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        u = session.get('compras_user', '')
        c.execute("""INSERT INTO acondicionamiento
            (produccion_id, lote, producto, cantidad_batch_g, unidades_producidas, presentacion, mee_consumido, fecha, operador, observaciones)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (int(d.get('produccion_id', 0)), d.get('lote', ''), d.get('producto', ''),
             float(d.get('cantidad_batch_g', 0)), int(d.get('unidades_producidas', 0)),
             d.get('presentacion', ''), json.dumps(d.get('mee_consumido', [])),
             d.get('fecha', datetime.now().strftime('%Y-%m-%d')), u, d.get('observaciones', '')))
        conn.commit(); new_id = c.lastrowid; conn.close()
        return jsonify({'ok': True, 'id': new_id}), 201
    c.execute("""SELECT id, produccion_id, lote, producto, cantidad_batch_g, unidades_producidas,
                        presentacion, fecha, operador, estado, observaciones
                 FROM acondicionamiento ORDER BY creado_en DESC LIMIT 100""")
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)


@bp.route('/api/acondicionamiento/<int:aid>', methods=['PATCH'])
def acondicionamiento_update(aid):
    if 'compras_user' not in session: return jsonify({'error': 'Autenticacion requerida'}), 401
    d = request.get_json(silent=True) or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if 'estado' in d: c.execute("UPDATE acondicionamiento SET estado=? WHERE id=?", (d['estado'], aid))
    if 'unidades_producidas' in d: c.execute("UPDATE acondicionamiento SET unidades_producidas=? WHERE id=?", (int(d['unidades_producidas']), aid))
    if 'mee_consumido' in d: c.execute("UPDATE acondicionamiento SET mee_consumido=? WHERE id=?", (json.dumps(d['mee_consumido']), aid))
    if 'observaciones' in d: c.execute("UPDATE acondicionamiento SET observaciones=? WHERE id=?", (d['observaciones'], aid))
    conn.commit(); conn.close()
    return jsonify({'ok': True})


@bp.route('/api/liberacion', methods=['GET', 'POST'])
def liberacion_list():
    if 'compras_user' not in session: return jsonify({'error': 'Autenticacion requerida'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        c.execute("""INSERT INTO liberaciones
            (acondicionamiento_id, lote, producto, unidades, presentacion, fecha_produccion, cliente, destino, observaciones)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (int(d.get('acondicionamiento_id', 0)), d.get('lote', ''), d.get('producto', ''),
             int(d.get('unidades', 0)), d.get('presentacion', ''), d.get('fecha_produccion', ''),
             d.get('cliente', ''), d.get('destino', 'ANIMUS'), d.get('observaciones', '')))
        conn.commit(); new_id = c.lastrowid; conn.close()
        return jsonify({'ok': True, 'id': new_id}), 201
    estado = request.args.get('estado', '')
    if estado: c.execute("SELECT * FROM liberaciones WHERE estado=? ORDER BY creado_en DESC LIMIT 100", (estado,))
    else: c.execute("SELECT * FROM liberaciones ORDER BY creado_en DESC LIMIT 100")
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)


@bp.route('/api/liberacion/<int:lid>', methods=['PATCH'])
def liberacion_update(lid):
    if 'compras_user' not in session: return jsonify({'error': 'Autenticacion requerida'}), 401
    u = session.get('compras_user', '')
    d = request.get_json(silent=True) or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    estado = d.get('estado', '')
    if estado == 'Liberado':
        c.execute("UPDATE liberaciones SET estado='Liberado', fecha_liberacion=?, aprobado_por=?, cliente=? WHERE id=?",
                  (datetime.now().strftime('%Y-%m-%d'), u, d.get('cliente', ''), lid))
    elif estado == 'Rechazado':
        c.execute("UPDATE liberaciones SET estado='Rechazado', aprobado_por=?, observaciones=? WHERE id=?",
                  (u, d.get('observaciones', ''), lid))
    else:
        c.execute("UPDATE liberaciones SET observaciones=? WHERE id=?", (d.get('observaciones', ''), lid))
    conn.commit(); conn.close()
    return jsonify({'ok': True})
