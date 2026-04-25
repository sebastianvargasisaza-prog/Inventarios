import os
import json
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS
from auth import (
    _client_ip, _is_locked, _record_failure, _clear_attempts,
    _log_sec, register_hooks,
)

from database import init_db, seed_compromisos, seed_rrhh, run_seed_rrhh

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'hha-group-2026-secretkey-x9kq')
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)
register_hooks(app)


from templates_py.rrhh_html import RRHH_HTML

# ─── HUB HHA GROUP ────────────────────────────────────────────
from templates_py.compromisos_html import COMPROMISOS_HTML

from templates_py.home_html import HOME_HTML

from templates_py.hub_html import HUB_HTML

# ─── LOGIN COMPRAS ────────────────────────────────────────────
# ─── MÓDULO CLIENTES ──────────────────────────────────────────
from templates_py.clientes_html import CLIENTES_HTML

# ─── MÓDULO CALIDAD BPM ────────────────────────────────────────
from templates_py.calidad_html import CALIDAD_HTML

# ─── MÓDULO HQ GERENCIA ────────────────────────────────────────
from templates_py.gerencia_html import GERENCIA_HTML

# ─── MÓDULO FINANCIERO ────────────────────────────────────────
from templates_py.financiero_html import FINANCIERO_HTML

from templates_py.login_html import LOGIN_HTML

# ─── MÓDULO COMPRAS ───────────────────────────────────────────
from templates_py.compras_html import COMPRAS_HTML

from templates_py.recepcion_html import RECEPCION_HTML

from templates_py.salida_html import SALIDA_HTML

from templates_py.solicitudes_html import SOLICITUDES_HTML

from templates_py.dashboard_html import DASHBOARD_HTML

@app.route('/')
def index():
    return Response(HOME_HTML, mimetype='text/html')

@app.route('/inventarios')
def inventarios():
    return Response(DASHBOARD_HTML, mimetype='text/html')

# (rate limiter y hooks de seguridad → auth.py — registrados via register_hooks(app))

@app.route('/login', methods=['GET','POST'])
def login():
    error = ''
    if request.method == 'POST':
        ip = _client_ip()
        if _is_locked(ip):
            error = '<div class="err">Demasiados intentos. Espera 15 min.</div>'
            return Response(LOGIN_HTML.replace('{error}', error), mimetype='text/html')
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '').strip()
        expected = COMPRAS_USERS.get(username, '')
        # Soporte PBKDF2 (env var con hash) y plaintext legacy
        if expected and expected.startswith('pbkdf2:'):
            match = check_password_hash(expected, password)
        else:
            match = bool(expected) and hmac.compare_digest(expected, password)
        if match:
            _clear_attempts(ip)
            _log_sec("login_success", username, ip)
            session.clear()
            session.permanent = True
            session['compras_user'] = username
            session['login_time']   = time.time()
            nxt = request.args.get('next', '/compras')
            if not nxt.startswith('/') or nxt.startswith('//'):
                nxt = '/compras'
            return redirect(nxt)
        _record_failure(ip)
        _log_sec("login_failure", username, ip)
        error = '<div class="err">Usuario o contraseña incorrectos.</div>'
    return Response(LOGIN_HTML.replace('{error}', error), mimetype='text/html')

@app.route('/logout')
def logout():
    session.pop('compras_user', None)
    return redirect('/')

@app.route('/compras')
def compras():
    if 'compras_user' not in session:
        return redirect('/login')
    usuario = session.get('compras_user', '').capitalize()
    es_contadora = 'true' if session.get('compras_user','') in CONTADORA_USERS else 'false'
    html = COMPRAS_HTML.replace('{usuario}', usuario).replace('{es_contadora}', es_contadora)
    return Response(html, mimetype='text/html')


@app.route('/api/hub/resumen')
def hub_resumen():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
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
    conn.close()
    return jsonify({
        'ocs': {'por_autorizar': cnt_por_autorizar, 'por_pagar': cnt_por_pagar,
                'valor_autorizar': val_por_autorizar, 'valor_pagar': val_por_pagar},
        'stock_critico': stock_crit,
        'pagado_semana': pag_semana,
        'compromisos': {'pendientes': comp_pendientes, 'vencidos': comp_vencidos, 'criticos': comp_criticos},
        'clientes': clientes_activos
    })

@app.route('/api/hub/alertas')
def hub_alertas():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
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
    conn.close()
    return jsonify({'alertas': alertas[:15], 'resumen': resumen})

@app.route('/api/compromisos', methods=['GET','POST'])
def handle_compromisos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('descripcion'): conn.close(); return jsonify({'error':'Descripcion requerida'}),400
        c.execute("""INSERT INTO compromisos (descripcion,responsable,area,fecha_limite,estado,prioridad,origen,empresa,fecha_creacion)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (d['descripcion'],d.get('responsable',''),d.get('area',''),d.get('fecha_limite',''),
                   d.get('estado','Pendiente'),d.get('prioridad','Normal'),d.get('origen',''),
                   d.get('empresa','Espagiria'),datetime.now().strftime('%Y-%m-%d')))
        conn.commit(); conn.close()
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
    conn.close()
    return jsonify({'compromisos': rows})

@app.route('/api/compromisos/<int:cid>', methods=['PATCH'])
def update_compromiso(cid):
    d = request.json or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    sets=[]; params=[]
    for field in ['estado','notas','fecha_limite','responsable','prioridad']:
        if field in d: sets.append(f"{field}=?"); params.append(d[field])
    if d.get('estado') == 'Completado':
        sets.append("fecha_cierre=?"); params.append(datetime.now().strftime('%Y-%m-%d'))
    if not sets: conn.close(); return jsonify({'error':'Nada que actualizar'}),400
    params.append(cid)
    c.execute(f"UPDATE compromisos SET {', '.join(sets)} WHERE id=?", params)
    conn.commit(); conn.close()
    return jsonify({'ok':True})

@app.route('/compromisos')
def compromisos_page():
    if 'compras_user' not in session:
        return redirect('/login')
    return Response(COMPROMISOS_HTML, mimetype='text/html')

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Inventory system running'})

@app.route('/api/inventario')
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

@app.route('/api/formulas', methods=['GET', 'POST'])
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

@app.route('/api/formulas/<producto_nombre>', methods=['DELETE'])
def del_formula(producto_nombre):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM formula_items WHERE producto_nombre=?', (producto_nombre,))
    c.execute('DELETE FROM formula_headers WHERE producto_nombre=?', (producto_nombre,))
    conn.commit()
    conn.close()
    return jsonify({'message': f'Formula {producto_nombre} eliminada'})

@app.route('/api/movimientos', methods=['GET', 'POST'])
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

@app.route('/api/produccion', methods=['GET', 'POST'])
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
                       f'Produccion {lote_ref} — {cantidad_kg}kg'))
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


@app.route('/api/produccion/simular', methods=['POST'])
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


@app.route('/api/formula/costo', methods=['POST'])
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


@app.route('/api/trazabilidad/lote-pt/<lote_ref>')
def trazabilidad_lote_pt(lote_ref):
    """Traza hacia atrás: dado un lote PT (PROD-00001) devuelve MPs consumidas, proveedor, fecha vencimiento."""
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # Producción base
    c.execute("SELECT id, producto, cantidad, fecha, operador, observaciones FROM producciones WHERE lote=? OR id=?",
              (lote_ref, lote_ref.replace('PROD-','').lstrip('0') or 0))
    prod = c.fetchone()
    if not prod:
        conn.close()
        return jsonify({'error': f'Lote no encontrado: {lote_ref}', 'lote_ref': lote_ref}), 404
    prod_data = {'id': prod[0], 'producto': prod[1], 'cantidad_kg': prod[2],
                 'fecha': prod[3], 'operador': prod[4] or '', 'observaciones': prod[5] or ''}
    # MPs consumidas — buscar Salidas etiquetadas con este lote_ref O por fecha+producto (legacy)
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


@app.route('/api/trazabilidad/lote-mp/<path:lote_mp>')
def trazabilidad_lote_mp(lote_mp):
    """Traza hacia adelante: dado un lote de MP devuelve en qué producciones se usó y a qué clientes llegó."""
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
    # Salidas — producciones que consumieron este lote
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
    # Detallar producciones únicas
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


@app.route('/api/analisis-abc')
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
        pct = (cumulative / total) * 100         # % acumulado DESPUÉS
        # Clasificacion basada en donde EMPIEZA el item (estandar Pareto)
        # Un item es A si al agregarlo aun no hemos superado el 80% previo
        clasificacion = 'A' if prev_pct < 80 else ('B' if prev_pct < 95 else 'C')
        abc.append({'material': mat, 'cantidad': qty, 'valor': f'{pct:.1f}%',
                    'clasificacion': clasificacion})
    return jsonify({'items': abc})

@app.route('/api/alertas', methods=['GET', 'POST'])
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



@app.route('/api/alertas-reabastecimiento')
def alertas_reabastecimiento():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT m.material_id,
                        COALESCE(mp.nombre_comercial, m.material_nombre) as nombre,
                        COALESCE(mp.proveedor,'') as proveedor,
                        COALESCE(mp.stock_minimo,0) as stock_minimo,
                        SUM(CASE WHEN m.tipo='Entrada' THEN m.cantidad ELSE -m.cantidad END) as stock_actual
                 FROM movimientos m
                 LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
                 GROUP BY m.material_id
                 HAVING stock_actual < stock_minimo AND stock_minimo > 0
                 ORDER BY (stock_actual/stock_minimo) ASC""")
    rows = c.fetchall(); conn.close()
    alertas = []
    for r in rows:
        stock_actual = round(r[4] or 0, 1)
        stock_minimo = round(r[3], 1)
        alertas.append({'codigo_mp': r[0] or '', 'nombre': r[1] or '', 'proveedor': r[2] or '',
                        'stock_minimo': stock_minimo, 'stock_actual': max(stock_actual, 0),
                        'deficit': round(max(stock_minimo - stock_actual, 0), 1)})
    return jsonify({'alertas': alertas, 'total': len(alertas)})

@app.route('/api/stock')
def get_stock():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT material_id, material_nombre, SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE 0 END), SUM(CASE WHEN tipo='Salida' THEN cantidad ELSE 0 END), SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) FROM movimientos GROUP BY material_id, material_nombre ORDER BY material_nombre")
    rows = c.fetchall(); conn.close()
    return jsonify({'items': [{'material_id':r[0],'material_nombre':r[1],'entradas':round(r[2] or 0,2),'salidas':round(r[3] or 0,2),'stock_actual':round(r[4] or 0,2)} for r in rows]})

@app.route('/api/lotes')
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

@app.route('/api/maestro-mps', methods=['GET','POST'])
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

@app.route('/api/maestro-mps/<codigo>')
def get_mp(codigo):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT codigo_mp,nombre_inci,nombre_comercial,tipo,proveedor,stock_minimo FROM maestro_mps WHERE codigo_mp=?", (codigo,))
    r = c.fetchone(); conn.close()
    return jsonify({'codigo_mp':r[0],'nombre_inci':r[1],'nombre_comercial':r[2],'tipo':r[3],'proveedor':r[4],'stock_minimo':r[5]}) if r else (jsonify({'error':'not found'}),404)

@app.route('/api/recepcion', methods=['POST'])
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
    if cuarentena: msg += ' — En CUARENTENA (pendiente aprobacion QC)'
    if numero_oc: msg += f' | OC {numero_oc} actualizada'
    return jsonify({'message': msg,'lote':lote,'codigo':codigo,'nombre':nombre,'cantidad':d.get('cantidad',0),'cuarentena':cuarentena}), 201

@app.route('/api/lotes/cuarentena', methods=['GET'])
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

@app.route('/api/lotes/liberar', methods=['POST'])
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

@app.route('/api/trazabilidad/<lote>', methods=['GET'])
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

# ── CONTEO CICLICO BDG-PRO-002 ──────────────────────────────────
@app.route('/api/conteo/estanterias', methods=['GET'])
def conteo_estanterias():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT COALESCE(NULLIF(estanteria,''),'Sin estanteria') as est,
                        COUNT(DISTINCT material_id) as total_mps,
                        SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock_total
                 FROM movimientos GROUP BY est ORDER BY est""")
    rows = c.fetchall()
    conn.close()
    return jsonify([{'estanteria': r[0], 'total_mps': r[1], 'stock_total': round(r[2] or 0, 1)} for r in rows])

@app.route('/api/conteo/materiales', methods=['GET'])
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

@app.route('/api/conteo/iniciar', methods=['POST'])
def conteo_iniciar():
    if 'compras_user' not in session:
        return jsonify({'error': 'Autenticacion requerida'}), 401
    d = request.json or {}
    est = d.get('estanteria', '')
    responsable = d.get('responsable', session.get('compras_user',''))
    from datetime import date
    numero = 'CNT-' + date.today().strftime('%Y%m%d') + '-' + est.replace(' ','')[:6].upper()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    try:
        c.execute("INSERT INTO conteos_fisicos (numero,fecha_inicio,estado,responsable,estanteria,tipo_conteo) VALUES (?,datetime('now'),'Abierto',?,?,'Ciclico')",
                  (numero, responsable, est))
        conteo_id = c.lastrowid
        conn.commit(); conn.close()
        return jsonify({'conteo_id': conteo_id, 'numero': numero, 'message': 'Conteo iniciado'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 400

@app.route('/api/conteo/<int:conteo_id>/guardar', methods=['POST'])
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

@app.route('/api/conteo/<int:conteo_id>/cerrar', methods=['POST'])
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

@app.route('/api/conteo/<int:conteo_id>/ajustar', methods=['POST'])
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

@app.route('/api/conteo/historial', methods=['GET'])
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

@app.route('/api/conteo/<int:conteo_id>/items', methods=['GET'])
def conteo_get_items(conteo_id):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT * FROM conteo_items WHERE conteo_id=? ORDER BY codigo_mp", (conteo_id,))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return jsonify([dict(zip(cols, r)) for r in rows])

@app.route('/api/lotes/cc-review', methods=['POST'])
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

@app.route('/api/reset-movimientos', methods=['POST'])
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

@app.route('/rotulos/<producto_nombre>/<cantidad_str>')
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

@app.route('/rotulo-recepcion/<codigo>/<lote>/<cantidad_str>')
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
    h+=('<div class="ph"><b>Rotulo de Recepcion — Materia Prima</b><button class="pb" onclick="window.print()">Imprimir</button></div>'
        '<div class="r"><div class="rh">'
        '<span style="font-weight:bold;font-size:11pt;display:block;margin-bottom:2px;">ROTULO DE INGRESO DE MATERIA PRIMA</span>'
        '<span style="font-size:7.5pt;opacity:0.85;">Espagiria Laboratorios &nbsp;|&nbsp; COC-PRO-002-F07 &nbsp;|&nbsp; '+hoy+'</span>'
        '</div>'
        '<div class="lote"><div style="font-size:9pt;color:#888;margin-bottom:4px;">NUMERO DE LOTE — CODIGO DE BARRAS</div>'
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


@app.route('/rotulo-recepcion-mee/<codigo>/<cantidad_str>')
def rotulo_recepcion_mee(codigo, cantidad_str):
    try: cantidad = int(float(cantidad_str))
    except: return "<h2>Cantidad invalida</h2>", 400
    from datetime import date; import urllib.parse
    hoy = date.today().strftime('%d-%b-%Y').upper()
    codigo = urllib.parse.unquote(codigo)
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT descripcion, categoria, proveedor FROM mee WHERE codigo=?", (codigo,))
    mee = c.fetchone()
    c.execute("SELECT referencia, operador, fecha FROM movimientos_mee WHERE codigo_mee=? AND tipo='entrada' ORDER BY id DESC LIMIT 1", (codigo,))
    mov = c.fetchone(); conn.close()
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
    h += ('<div class="ph"><b>Rótulo de Recepción — Material E&E</b>'
          '<button class="pb" onclick="window.print()">Imprimir</button></div>'
          '<div class="r"><div class="rh">'
          '<span style="font-weight:bold;font-size:11pt;display:block;margin-bottom:2px;">ROTULO DE INGRESO DE MATERIAL E&E</span>'
          '<span style="font-size:7.5pt;opacity:0.85;">Espagiria Laboratorios &nbsp;|&nbsp; COC-PRO-002-F07 &nbsp;|&nbsp; ' + hoy + '</span>'
          '</div>'
          '<div class="lote">'
          '<div style="font-size:9pt;color:#666;margin-bottom:4px;">CODIGO MATERIAL — CODIGO DE BARRAS</div>'
          '<div class="lnum">' + codigo + '</div>'
          '<svg id="bc" style="margin-top:6px;"></svg>'
          '</div><table>'
          '<tr><td class="l">Código MEE:</td><td style="font-weight:700;">' + codigo + '</td></tr>'
          '<tr><td class="l">Descripción:</td><td style="font-weight:700;">' + desc + '</td></tr>'
          '<tr><td class="l">Categoría:</td><td>' + cat + '</td></tr>'
          '<tr><td class="l">Proveedor / Ref. compra:</td><td style="font-weight:700;">' + prov_display + '</td></tr>'
          '<tr><td class="l">Cantidad recibida:</td><td style="color:#27ae60;font-weight:700;">' + f"{cantidad:,}" + ' unidades</td></tr>'
          '<tr><td class="l">Fecha de recepción:</td><td style="font-weight:700;">' + hoy + '</td></tr>'
          '<tr><td class="l">Fecha de análisis / inspección:</td><td style="height:28px;background:#fffde7;"></td></tr>'
          '<tr><td class="l">Piezas inspeccionadas (AQL):</td><td style="height:28px;"></td></tr>'
          '<tr class="calidad"><td class="l calidad" style="color:#1b5e20;font-weight:800;">Estado de calidad:</td>'
          '<td style="height:28px;"><span style="margin-right:14px;">&#9744; Aprobado</span>'
          '<span style="margin-right:14px;">&#9744; En cuarentena</span>'
          '<span>&#9744; Rechazado</span></td></tr>'
          '<tr><td class="l">Número de recepción:</td><td>' + nr + '</td></tr>'
          '<tr><td class="l">Recibido por:</td><td style="height:30px;">' + oper + '</td></tr>'
          '<tr><td class="l">Aprobado por (Calidad):</td><td style="height:30px;"></td></tr>'
          '</table>'
          '<div style="background:#dde8f0;padding:4px 10px;font-size:7.5pt;color:#555;text-align:center;">'
          'COC-PRO-002-F07 &nbsp;|&nbsp; Material Envase & Empaque &nbsp;|&nbsp; ' + hoy + '</div>'
          '</div>'
          '<script>window.onload=function(){try{JsBarcode("#bc","' + bv + '",{format:"CODE128",width:1.5,height:45,displayValue:false,margin:0});}catch(e){}}</script>'
          '</body></html>')
    return h


@app.route('/api/dashboard-stats')
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


@app.route('/api/generar-oc-automatica', methods=['POST'])
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
@app.route('/api/ordenes-compra', methods=['GET','POST'])
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
        " COALESCE(o.valor_total, 0) as valor_total"
        " FROM ordenes_compra o LEFT JOIN ordenes_compra_items i ON o.numero_oc=i.numero_oc"
    )
    if cat_filter:
        c.execute(_sql + " WHERE o.categoria=? GROUP BY o.numero_oc ORDER BY o.fecha DESC LIMIT 300", (cat_filter,))
    else:
        c.execute(_sql + " GROUP BY o.numero_oc ORDER BY o.fecha DESC LIMIT 300")
    cols = ['numero_oc','fecha','estado','proveedor','fecha_entrega_est','observaciones',
            'creado_por','num_items','categoria','remision_code','autorizado_por','valor_total']
    rows = c.fetchall(); conn.close()
    return jsonify({'ordenes': [dict(zip(cols, r)) for r in rows]})

@app.route('/api/ordenes-compra/<numero_oc>', methods=['GET','PUT'])
def handle_oc_detalle(numero_oc):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
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
    items = c.fetchall(); conn.close()
    if not oc_row: return jsonify({'error': 'OC no encontrada'}), 404
    return jsonify({'oc': dict(zip(oc_cols, oc_row)), 'items': items})

@app.route('/api/proveedores-compras', methods=['GET','POST'])
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

@app.route('/api/proveedores-compras/<path:nombre>/ficha')
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


@app.route('/api/solicitudes-compra', methods=['GET','POST'])
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
        c.execute("""INSERT INTO solicitudes_compra
                     (numero,fecha,estado,solicitante,urgencia,observaciones,area,empresa,categoria,tipo)
                     VALUES (?,?,?,?,?,?,?,?,?,?)""",
                  (numero, datetime.now().isoformat(), 'Pendiente',
                   d.get('solicitante',''), d.get('urgencia','Normal'), d.get('observaciones',''),
                   area, emp, cat, tip))
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
    sql = "SELECT numero,fecha,estado,solicitante,urgencia,observaciones,empresa,categoria,tipo,area FROM solicitudes_compra WHERE 1=1"
    params = []
    if filtro_estado: sql += " AND estado=?"; params.append(filtro_estado)
    if filtro_empresa: sql += " AND empresa=?"; params.append(filtro_empresa)
    sql += " ORDER BY fecha DESC LIMIT 200"
    c.execute(sql, params)
    cols_sol = ['numero','fecha','estado','solicitante','urgencia','observaciones','empresa','categoria','tipo','area']
    rows_sol = [dict(zip(cols_sol, r)) for r in c.fetchall()]
    conn.close()
    return jsonify({'solicitudes': rows_sol})


@app.route('/api/solicitudes-compra/<numero>', methods=['GET'])
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

@app.route('/solicitudes')
def solicitudes_page():
    return Response(SOLICITUDES_HTML, mimetype='text/html')


@app.route('/api/solicitudes-compra/<numero>/estado', methods=['PATCH'])
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
        cur.execute("SELECT codigo_mp, nombre_mp, cantidad_g, unidad FROM solicitudes_compra_items WHERE numero=?", (numero.upper(),))
        items_sol = cur.fetchall()
        proveedor_oc = d.get('proveedor', 'Por definir')
        cur.execute("SELECT COUNT(*) FROM ordenes_compra")
        n_oc = cur.fetchone()[0] + 1
        oc_num = f"OC-{datetime.now().year}-{n_oc:04d}"
        cur.execute("""INSERT INTO ordenes_compra (numero_oc, fecha, estado, proveedor, observaciones, creado_por)
                     VALUES (?,?,?,?,?,?)""",
                  (oc_num, datetime.now().isoformat(), 'Borrador', proveedor_oc,
                   f'Generado desde {numero.upper()}', session.get('compras_user','')))
        for it in items_sol:
            cur.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g) VALUES (?,?,?,?)",
                      (oc_num, it[0], it[1], it[2]))
        cur.execute("UPDATE solicitudes_compra SET numero_oc=? WHERE numero=?", (oc_num, numero.upper()))
        oc_creada = oc_num
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'estado': nuevo, 'numero_oc': oc_creada})

@app.route('/api/ordenes-compra/<numero_oc>/recibir', methods=['POST'])
def recibir_oc(numero_oc):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT estado, proveedor, categoria FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    oc_row = cur.fetchone()
    if not oc_row:
        conn.close(); return jsonify({'error': 'OC no encontrada'}), 404
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
    # Build lookup dict for items_recepcion data keyed by codigo_mp
    rec_map = {ir.get('codigo_mp', ''): ir for ir in items_r}
    ingresos = 0
    es_parcial = False
    for item in items_oc:
        codigo, nombre, cantidad_pedida = item
        ir = rec_map.get(codigo, {})
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
                cur.execute("INSERT INTO movimientos_mee (codigo_mee, tipo, cantidad, referencia, observaciones, operador, fecha) VALUES (?,?,?,?,?,?,?)",
                           (codigo, 'entrada', cant_recibida, numero_oc, f'Recepcion OC {numero_oc}', operador, fecha))
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

@app.route('/api/ordenes-compra/<numero_oc>/revisar', methods=['PATCH'])
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
    params.append(numero_oc)
    cur.execute(f"UPDATE ordenes_compra SET {', '.join(sets)} WHERE numero_oc=?", params)
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'estado': 'Revisada'})

@app.route('/api/ordenes-compra/<numero_oc>/autorizar', methods=['PATCH'])
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

@app.route('/api/ordenes-compra/<numero_oc>/pagar', methods=['PATCH'])
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
    cat_map = {'MPs':'MPs','MP':'MPs','Envase':'MEE','Insumos':'MEE','MEE':'MEE','Servicios':'Servicios','Analisis':'Servicios','Ánalisis':'Servicios','Acondicionamiento':'Servicios','Admin':'Administrativo','Nomina':'Administrativo','ADM':'Administrativo','Infraestructura':'Infraestructura','INF':'Infraestructura','CC':'Cuentas de Cobro'}
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

@app.route('/api/compras/buscar-remision/<remision_code>')
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

@app.route('/api/mee', methods=['GET','POST'])
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

@app.route('/api/mee/<codigo>', methods=['GET','PUT'])
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

@app.route('/api/mee/<codigo>/ajuste', methods=['POST'])
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
    cur.execute("INSERT INTO movimientos_mee (codigo_mee,tipo,cantidad,referencia,observaciones,operador,fecha) VALUES (?,?,?,?,?,?,?)",
                (codigo,'ajuste',diff,'ajuste_manual',obs,oper,datetime.now().isoformat()))
    conn.commit(); conn.close()
    return jsonify({'ok':True,'nuevo_stock':nuevo})

@app.route('/api/movimientos-mee', methods=['GET','POST'])
def handle_movimientos_mee():
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    if request.method == 'POST':
        d = request.get_json()
        cod  = d.get('codigo_mee')
        tipo = d.get('tipo','entrada')
        cant = float(d.get('cantidad',0))
        ref  = d.get('referencia','')
        obs  = d.get('observaciones','')
        oper = d.get('operador','')
        if not cod or cant<=0: conn.close(); return jsonify({'error':'datos invalidos'}), 400
        cur.execute("SELECT stock_actual FROM maestro_mee WHERE codigo=?", (cod,))
        row=cur.fetchone()
        if not row: conn.close(); return jsonify({'error':'MEE no encontrado'}), 404
        delta = cant if tipo=='entrada' else -cant
        nuevo = row[0]+delta
        if nuevo<0: conn.close(); return jsonify({'error':f'Stock insuficiente (actual: {row[0]})'}), 400
        cur.execute("UPDATE maestro_mee SET stock_actual=? WHERE codigo=?", (nuevo,cod))
        cur.execute("INSERT INTO movimientos_mee (codigo_mee,tipo,cantidad,referencia,observaciones,operador,fecha) VALUES (?,?,?,?,?,?,?)",
                    (cod,tipo,cant,ref,obs,oper,datetime.now().isoformat()))
        conn.commit(); conn.close()
        return jsonify({'ok':True,'nuevo_stock':nuevo}), 201
    # GET con filtros
    codigo = request.args.get('codigo','')
    tipo   = request.args.get('tipo','')
    limit  = int(request.args.get('limit',50))
    sql = """SELECT m.id,m.codigo_mee,mm.descripcion,m.tipo,m.cantidad,m.referencia,m.observaciones,m.operador,m.fecha
             FROM movimientos_mee m LEFT JOIN maestro_mee mm ON m.codigo_mee=mm.codigo WHERE 1=1"""
    params=[]
    if codigo: sql+=" AND m.codigo_mee=?"; params.append(codigo)
    if tipo:   sql+=" AND m.tipo=?"; params.append(tipo)
    sql+=" ORDER BY m.fecha DESC LIMIT ?"; params.append(limit)
    cur.execute(sql, params)
    cols=['id','codigo_mee','descripcion','tipo','cantidad','referencia','observaciones','operador','fecha']
    rows=[dict(zip(cols,r)) for r in cur.fetchall()]
    conn.close()
    return jsonify({'movimientos':rows})

@app.route('/api/movimientos-mee/lote', methods=['POST'])
def movimientos_mee_lote():
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    d = request.get_json()
    movs = d.get('movimientos',[])
    oper = d.get('operador','')
    ref  = d.get('referencia','')
    errores=[]
    for m in movs:
        cod=m.get('codigo_mee'); cant=float(m.get('cantidad',0))
        if not cod or cant<=0: continue
        cur.execute("SELECT stock_actual FROM maestro_mee WHERE codigo=?", (cod,))
        row=cur.fetchone()
        if not row: errores.append(f'{cod} no encontrado'); continue
        nuevo=row[0]-cant
        if nuevo<0: nuevo=0
        cur.execute("UPDATE maestro_mee SET stock_actual=? WHERE codigo=?", (nuevo,cod))
        cur.execute("INSERT INTO movimientos_mee (codigo_mee,tipo,cantidad,referencia,observaciones,operador,fecha) VALUES (?,?,?,?,?,?,?)",
                    (cod,'salida',cant,ref,'Consumo produccion',oper,datetime.now().isoformat()))
    conn.commit(); conn.close()
    if errores: return jsonify({'ok':True,'advertencias':errores})
    return jsonify({'ok':True})

@app.route('/api/alertas-mee', methods=['GET'])
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
@app.route('/clientes')
def clientes_page():
    if 'compras_user' not in session:
        return redirect(url_for('login'))
    return Response(CLIENTES_HTML, mimetype='text/html')

@app.route('/api/clientes', methods=['GET','POST'])
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
                          condiciones_pago,descuento_pct,activo,fecha_creacion,observaciones)
                         VALUES (?,?,?,?,?,?,?,?,?,?,1,datetime('now'),?)""",
                      (codigo, d['nombre'], d.get('empresa','ANIMUS'), d.get('tipo','Distribuidor'),
                       d.get('contacto',''), d.get('email',''), d.get('telefono',''),
                       d.get('nit',''), d.get('condiciones_pago','30 dias'),
                       float(d.get('descuento_pct',0)), d.get('observaciones','')))
            conn.commit(); conn.close()
            return jsonify({'message': f"Cliente creado", 'codigo': codigo}), 201
        except Exception as e:
            conn.close(); return jsonify({'error': str(e)}), 400
    c.execute("SELECT id,codigo,nombre,empresa,tipo,contacto,email,telefono,condiciones_pago,descuento_pct,activo,fecha_creacion FROM clientes WHERE activo=1 ORDER BY nombre")
    cols = ['id','codigo','nombre','empresa','tipo','contacto','email','telefono','condiciones_pago','descuento_pct','activo','fecha_creacion']
    clientes = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close(); return jsonify({'clientes': clientes})

@app.route('/api/clientes/<int:cid>', methods=['GET','PUT'])
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

@app.route('/api/clientes/<int:cid>/historial')
def handle_cliente_historial(cid):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT numero,fecha,estado,valor_total,fecha_despacho FROM pedidos WHERE cliente_id=? ORDER BY fecha DESC LIMIT 50", (cid,))
    cols = ['numero','fecha','estado','valor_total','fecha_despacho']
    pedidos = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close(); return jsonify({'pedidos': pedidos})

@app.route('/api/clientes/<int:cid>/stats')
def handle_cliente_stats(cid):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT COUNT(*), COALESCE(SUM(valor_total),0), MAX(fecha) FROM pedidos WHERE cliente_id=?", (cid,))
    row = c.fetchone(); conn.close()
    return jsonify({'total_pedidos': row[0], 'valor_total': row[1], 'ultimo_pedido': row[2]})

@app.route('/api/clientes/alertas-recompra')
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


@app.route('/api/clientes/<int:cid>/ficha360')
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


@app.route('/api/pedidos', methods=['GET','POST'])
def handle_pedidos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('cliente_id'):
            conn.close(); return jsonify({'error': 'cliente_id requerido'}), 400
        c.execute("SELECT COUNT(*) FROM pedidos"); n = (c.fetchone()[0] or 0) + 1
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
    q = "SELECT p.numero,c.nombre,p.fecha,p.estado,p.valor_total,p.empresa,p.fecha_entrega_est FROM pedidos p LEFT JOIN clientes c ON p.cliente_id=c.id"
    params = []
    if estado: q += " WHERE p.estado=?"; params.append(estado)
    q += " ORDER BY p.fecha DESC LIMIT 100"
    c.execute(q, params)
    cols = ['numero','cliente','fecha','estado','valor_total','empresa','fecha_entrega_est']
    rows = c.fetchall(); conn.close()
    return jsonify({'pedidos': [dict(zip(cols, r)) for r in rows]})

@app.route('/api/pedidos/<numero>', methods=['GET','PATCH'])
def handle_pedido_detalle(numero):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'PATCH':
        d = request.json or {}
        if d.get('estado'):
            c.execute("UPDATE pedidos SET estado=? WHERE numero=?", (d['estado'], numero))
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

@app.route('/api/stock-pt', methods=['GET','POST'])
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
    c.execute("SELECT sku,descripcion,SUM(unidades_disponible) as disponible,SUM(unidades_inicial) as inicial,MAX(fecha_produccion) as ultima_prod,empresa,precio_base FROM stock_pt WHERE estado='Disponible' GROUP BY sku,empresa ORDER BY sku")
    cols = ['sku','descripcion','disponible','inicial','ultima_prod','empresa','precio_base']
    rows = c.fetchall()
    conn.close()
    return jsonify({'stock_pt': [dict(zip(cols, r)) for r in rows]})

@app.route('/api/despachos', methods=['GET','POST'])
def handle_despachos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        c.execute("SELECT COUNT(*) FROM despachos"); n = (c.fetchone()[0] or 0) + 1
        numero = f"DSP-{datetime.now().strftime('%Y')}-{n:04d}"
        c.execute("INSERT INTO despachos (numero,numero_pedido,cliente_id,fecha,operador,observaciones,estado) VALUES (?,?,?,datetime('now'),?,?,?)",
                  (numero, d.get('numero_pedido',''), d.get('cliente_id'), session.get('compras_user','sistema'), d.get('observaciones',''), 'Completado'))
        for it in (d.get('items') or []):
            c.execute("INSERT INTO despachos_items (numero_despacho,sku,descripcion,lote_pt,cantidad,precio_unitario) VALUES (?,?,?,?,?,?)",
                      (numero, it.get('sku',''), it.get('descripcion',''), it.get('lote_pt',''), int(it.get('cantidad',0)), float(it.get('precio_unitario',0))))
            c.execute("UPDATE stock_pt SET unidades_disponible=MAX(0,unidades_disponible-?) WHERE sku=? AND unidades_disponible>0 ORDER BY fecha_produccion ASC LIMIT 1",
                      (int(it.get('cantidad',0)), it.get('sku','')))
        if d.get('numero_pedido'):
            c.execute("UPDATE pedidos SET estado='Despachado',fecha_despacho=datetime('now') WHERE numero=?", (d['numero_pedido'],))
        conn.commit(); conn.close()
        return jsonify({'message': f'Despacho {numero} registrado', 'numero': numero}), 201
    c.execute("SELECT d.numero,cl.nombre as cliente,d.fecha,d.numero_pedido,d.estado,d.operador FROM despachos d LEFT JOIN clientes cl ON d.cliente_id=cl.id ORDER BY d.fecha DESC LIMIT 100")
    cols = ['numero','cliente','fecha','numero_pedido','estado','operador']
    rows = c.fetchall(); conn.close()
    return jsonify({'despachos': [dict(zip(cols, r)) for r in rows]})

# ─── MÓDULO GERENCIA — Rutas ──────────────────────────────────
@app.route('/gerencia')
def gerencia_page():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return redirect(url_for('login'))
    return Response(HUB_HTML, mimetype='text/html')

@app.route('/gerencia-financiero')
def gerencia_financiero_page():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return redirect(url_for('login'))
    return Response(GERENCIA_HTML, mimetype='text/html')

@app.route('/api/gerencia/kpis')
def gerencia_kpis():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM maestro_mps m LEFT JOIN (SELECT material_id,SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as s FROM movimientos GROUP BY material_id) st ON m.codigo_mp=st.material_id WHERE m.activo=1 AND m.stock_minimo>0 AND COALESCE(st.s,0)<m.stock_minimo")
    mps_bajo_minimo = c.fetchone()[0] or 0
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
        'vencimientos': 'rojo' if lotes_vence_30 > 0 else ('amarillo' if lotes_vence_60 > 0 else 'verde'),
        'pt': 'rojo' if uds_pt < 100 else ('amarillo' if uds_pt < 500 else 'verde'),
        'pedidos': 'amarillo' if pedidos_activos > 0 else 'verde',
    }
    return jsonify({'espagiria': {'mps_bajo_minimo': mps_bajo_minimo, 'lotes_vence_30': lotes_vence_30,
                                   'lotes_vence_60': lotes_vence_60, 'prod_mes': prod_mes, 'ocs_pendientes': ocs_pendientes},
                    'animus': {'uds_pt': uds_pt, 'pedidos_activos': pedidos_activos, 'skus_stock': skus_stock, 'dias_desde_fm': dias_fm},
                    'inputs_manuales': inputs_manuales, 'semaforos': semaforos})

@app.route('/api/gerencia/flujo-operacional')
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

@app.route('/api/admin/security-log')
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

@app.route('/api/admin/generate-hash', methods=['POST'])
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

@app.route('/api/gerencia/dashboard-extra')
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
@app.route('/api/admin/cleanup-test-data', methods=['POST'])
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

@app.route('/api/gerencia/input-manual', methods=['POST'])
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
@app.route('/financiero')
def financiero_page():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return redirect(url_for('login'))
    return Response(FINANCIERO_HTML, mimetype='text/html')

@app.route('/api/financiero/ingresos', methods=['GET','POST'])
def handle_fin_ingresos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('concepto') or not d.get('monto'):
            conn.close(); return jsonify({'error': 'Concepto y monto requeridos'}), 400
        periodo = (d.get('fecha') or datetime.now().isoformat())[:7]
        c.execute("""INSERT INTO flujo_ingresos (fecha,empresa,concepto,categoria,monto,periodo,fuente,referencia,creado_por)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (d.get('fecha', datetime.now().isoformat()[:10]), d.get('empresa','HHA'),
                   d['concepto'], d.get('categoria','Ventas'), float(d['monto']),
                   periodo, 'manual', d.get('referencia',''), session.get('compras_user','sistema')))
        conn.commit(); conn.close()
        return jsonify({'message': f"Ingreso de ${float(d['monto']):,.0f} registrado"}), 201
    mes = request.args.get('mes')
    q = "SELECT id,fecha,empresa,concepto,categoria,monto,periodo,referencia FROM flujo_ingresos"
    params = []
    if mes: q += " WHERE periodo=?"; params.append(mes)
    q += " ORDER BY fecha DESC LIMIT 200"
    c.execute(q, params)
    cols = ['id','fecha','empresa','concepto','categoria','monto','periodo','referencia']
    conn.close()
    return jsonify({'ingresos': [dict(zip(cols, r)) for r in c.fetchall()]})

@app.route('/api/financiero/egresos', methods=['GET','POST'])
def handle_fin_egresos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('concepto') or not d.get('monto'):
            conn.close(); return jsonify({'error': 'Concepto y monto requeridos'}), 400
        periodo = (d.get('fecha') or datetime.now().isoformat())[:7]
        c.execute("""INSERT INTO flujo_egresos (fecha,empresa,concepto,categoria,monto,periodo,fuente,referencia,creado_por)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (d.get('fecha', datetime.now().isoformat()[:10]), d.get('empresa','HHA'),
                   d['concepto'], d.get('categoria','MPs'), float(d['monto']),
                   periodo, 'manual', d.get('referencia',''), session.get('compras_user','sistema')))
        conn.commit(); conn.close()
        return jsonify({'message': f"Egreso de ${float(d['monto']):,.0f} registrado"}), 201
    mes = request.args.get('mes')
    q = "SELECT id,fecha,empresa,concepto,categoria,monto,periodo,referencia FROM flujo_egresos"
    params = []
    if mes: q += " WHERE periodo=?"; params.append(mes)
    q += " ORDER BY fecha DESC LIMIT 200"
    c.execute(q, params)
    cols = ['id','fecha','empresa','concepto','categoria','monto','periodo','referencia']
    conn.close()
    return jsonify({'egresos': [dict(zip(cols, r)) for r in c.fetchall()]})

@app.route('/api/financiero/kpis')
def financiero_kpis():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    periodo_actual = datetime.now().strftime('%Y-%m')
    # KPIs mes actual
    c.execute("SELECT COALESCE(SUM(monto),0), COUNT(*) FROM flujo_ingresos WHERE periodo=?", (periodo_actual,))
    ing_mes, ing_count = c.fetchone()
    c.execute("SELECT COALESCE(SUM(monto),0), COUNT(*) FROM flujo_egresos WHERE periodo=?", (periodo_actual,))
    egr_mes, egr_count = c.fetchone()
    # Saldo caja desde gerencia_inputs
    c.execute("SELECT saldo_caja FROM gerencia_inputs ORDER BY periodo DESC LIMIT 1")
    row = c.fetchone(); saldo_caja = row[0] if row else 0
    # Desglose por categoría mes actual
    c.execute("SELECT categoria, SUM(monto) as total FROM flujo_ingresos WHERE periodo=? GROUP BY categoria ORDER BY total DESC", (periodo_actual,))
    desglose_ing = [{'categoria': r[0], 'total': r[1]} for r in c.fetchall()]
    c.execute("SELECT categoria, SUM(monto) as total FROM flujo_egresos WHERE periodo=? GROUP BY categoria ORDER BY total DESC", (periodo_actual,))
    desglose_egr = [{'categoria': r[0], 'total': r[1]} for r in c.fetchall()]
    # Histórico 6 meses
    historico = []
    for i in range(5, -1, -1):
        from datetime import date as _d
        import calendar
        hoy = _d.today()
        mes = hoy.month - i
        anio = hoy.year
        while mes <= 0: mes += 12; anio -= 1
        p = f"{anio}-{mes:02d}"
        c.execute("SELECT COALESCE(SUM(monto),0) FROM flujo_ingresos WHERE periodo=?", (p,))
        ing = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(monto),0) FROM flujo_egresos WHERE periodo=?", (p,))
        egr = c.fetchone()[0]
        historico.append({'periodo': p, 'ingresos': ing, 'egresos': egr})
    conn.close()
    return jsonify({'ing_mes': ing_mes, 'ing_count': ing_count, 'egr_mes': egr_mes, 'egr_count': egr_count,
                    'saldo_caja': saldo_caja, 'desglose_ing': desglose_ing, 'desglose_egr': desglose_egr,
                    'historico': historico, 'periodo': periodo_actual})

@app.route('/api/financiero/flujo-mensual')
def financiero_flujo_mensual():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT periodo, SUM(monto) FROM flujo_ingresos GROUP BY periodo ORDER BY periodo")
    ings = {r[0]: r[1] for r in c.fetchall()}
    c.execute("SELECT periodo, SUM(monto) FROM flujo_egresos GROUP BY periodo ORDER BY periodo")
    egrs = {r[0]: r[1] for r in c.fetchall()}
    periodos = sorted(set(list(ings.keys()) + list(egrs.keys())))
    meses = [{'periodo': p, 'ingresos': ings.get(p, 0), 'egresos': egrs.get(p, 0)} for p in periodos]
    conn.close()
    return jsonify({'meses': meses})

@app.route('/api/financiero/config', methods=['GET','POST'])
def financiero_config():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        for clave, valor in d.items():
            c.execute("INSERT INTO flujo_config (clave,valor,descripcion) VALUES (?,?,?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor", (clave, str(valor), ''))
        conn.commit(); conn.close()
        return jsonify({'message': f'{len(d)} parámetros actualizados'})
    c.execute("SELECT clave, valor FROM flujo_config ORDER BY clave")
    config = {r[0]: r[1] for r in c.fetchall()}
    conn.close()
    return jsonify({'config': config})

@app.route('/api/financiero/importar-ocs', methods=['POST'])
def financiero_importar_ocs():
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # Traer OCs recibidas que no estén ya importadas
    c.execute("""SELECT oc.numero_oc, oc.fecha, oc.proveedor,
                        COALESCE(SUM(i.cantidad_g * i.precio_unitario), oc.valor_total, 0) as total
                 FROM ordenes_compra oc
                 LEFT JOIN ordenes_compra_items i ON oc.numero_oc=i.numero_oc
                 WHERE oc.estado='Recibida'
                 AND oc.numero_oc NOT IN (SELECT referencia FROM flujo_egresos WHERE referencia LIKE 'OC-%')
                 GROUP BY oc.numero_oc""")
    ocs = c.fetchall()
    importadas = 0
    for numero_oc, fecha, proveedor, total in ocs:
        if total and total > 0:
            periodo = (fecha or datetime.now().isoformat())[:7]
            c.execute("""INSERT INTO flujo_egresos (fecha,empresa,concepto,categoria,monto,periodo,fuente,referencia,creado_por)
                         VALUES (?,?,?,?,?,?,?,?,?)""",
                      (fecha[:10] if fecha else datetime.now().isoformat()[:10],
                       'ESPAGIRIA', f'OC {numero_oc} — {proveedor or ""}',
                       'MPs', float(total), periodo, 'automatico', numero_oc, 'sistema'))
            importadas += 1
    conn.commit(); conn.close()
    return jsonify({'message': f'{importadas} OC(s) importadas como egresos'})


@app.route('/api/financiero/precios-mayorista', methods=['GET'])
def get_precios_mayorista():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT sku, descripcion, precio_base, precio_mayorista, unidad FROM sku_precios ORDER BY sku")
    rows = c.fetchall(); conn.close()
    return jsonify([{'sku':r[0],'descripcion':r[1],'precio_base':r[2],'precio_mayorista':r[3],'unidad':r[4]} for r in rows])

@app.route('/api/financiero/precios-mayorista/<sku>', methods=['POST'])
def update_precio_mayorista(sku):
    if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
        return jsonify({'error': 'Solo admins pueden editar precios'}), 401
    d = request.get_json()
    precio = float(d.get('precio_mayorista', 0) or 0)
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE sku_precios SET precio_mayorista=? WHERE sku=?", (precio, sku))
    conn.commit(); conn.close()
    return jsonify({'message': f'Precio actualizado para {sku}'})

@app.route('/api/financiero/ar-aging')
def financiero_ar_aging():
    from datetime import date
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    today = date.today()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT numero_pedido, cliente, fecha, valor_total
                 FROM pedidos
                 WHERE estado NOT IN ('Cancelado','Facturado','Entregado')
                 AND valor_total > 0""")
    rows = c.fetchall(); conn.close()
    buckets = {
        'corriente': {'total': 0, 'count': 0},
        'dias_30':   {'total': 0, 'count': 0},
        'dias_60':   {'total': 0, 'count': 0},
        'dias_90':   {'total': 0, 'count': 0},
    }
    pedidos = []
    ar_total = 0
    for r in rows:
        num, cliente, fecha_str, valor = r
        try:
            fd = date.fromisoformat(fecha_str[:10])
        except Exception:
            fd = today
        dias = (today - fd).days
        ar_total += (valor or 0)
        if dias <= 30:
            b = 'corriente'
        elif dias <= 60:
            b = 'dias_30'
        elif dias <= 90:
            b = 'dias_60'
        else:
            b = 'dias_90'
        buckets[b]['total'] += (valor or 0)
        buckets[b]['count'] += 1
        pedidos.append({'numero_pedido': num, 'cliente': cliente, 'fecha': fecha_str[:10] if fecha_str else '', 'dias': dias, 'valor_total': valor or 0})
    pedidos.sort(key=lambda x: x['dias'], reverse=True)
    return jsonify({'ar_total': ar_total, 'count': len(pedidos), 'buckets': buckets, 'pedidos': pedidos})

@app.route('/api/financiero/ap-aging')
def financiero_ap_aging():
    from datetime import date
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    today = date.today()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT numero_oc, proveedor, fecha, valor_total
                 FROM ordenes_compra
                 WHERE estado IN ('Autorizada','Recibida','Parcial')
                 AND (pagado_por IS NULL OR pagado_por = '')""")
    rows = c.fetchall(); conn.close()
    buckets = {
        'corriente': {'total': 0, 'count': 0},
        'dias_30':   {'total': 0, 'count': 0},
        'dias_60':   {'total': 0, 'count': 0},
        'dias_90':   {'total': 0, 'count': 0},
    }
    ocs = []
    ap_total = 0
    for r in rows:
        num, prov, fecha_str, valor = r
        try:
            fd = date.fromisoformat(fecha_str[:10])
        except Exception:
            fd = today
        dias = (today - fd).days
        ap_total += (valor or 0)
        if dias <= 30:
            b = 'corriente'
        elif dias <= 60:
            b = 'dias_30'
        elif dias <= 90:
            b = 'dias_60'
        else:
            b = 'dias_90'
        buckets[b]['total'] += (valor or 0)
        buckets[b]['count'] += 1
        ocs.append({'numero_oc': num, 'proveedor': prov, 'fecha': fecha_str[:10] if fecha_str else '', 'dias': dias, 'valor_total': valor or 0})
    ocs.sort(key=lambda x: x['dias'], reverse=True)
    return jsonify({'ap_total': ap_total, 'count': len(ocs), 'buckets': buckets, 'ocs': ocs})

@app.route('/api/financiero/working-capital')
def financiero_working_capital():
    from datetime import date, timedelta
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    today = date.today()
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # AR
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM pedidos WHERE estado NOT IN ('Cancelado','Facturado','Entregado') AND valor_total > 0")
    ar_total = c.fetchone()[0] or 0
    # AP
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM ordenes_compra WHERE estado IN ('Autorizada','Recibida','Parcial') AND (pagado_por IS NULL OR pagado_por='')")
    ap_total = c.fetchone()[0] or 0
    # Cash from gerencia_inputs
    try:
        c.execute("SELECT valor FROM gerencia_inputs WHERE clave='saldo_caja' ORDER BY fecha DESC LIMIT 1")
        row = c.fetchone()
        cash = float(row[0]) if row else 0.0
    except Exception:
        cash = 0.0
    # Inventory value: lotes activos valorados a precio promedio por MP
    try:
        c.execute("""SELECT l.codigo_mp, l.cantidad_g,
                            COALESCE((SELECT AVG(oci.precio_unitario)
                                      FROM ordenes_compra_items oci
                                      WHERE oci.codigo_mp=l.codigo_mp AND oci.precio_unitario>0),0)
                     FROM lotes l WHERE l.estado='activo' AND l.cantidad_g>0""")
        inv_rows = c.fetchall()
        inventory_value = sum((r[1] or 0) * (r[2] or 0) for r in inv_rows)
    except Exception:
        inventory_value = 0.0
    # 90-day flows for DSO/DIO/DPO
    cutoff90 = (today - timedelta(days=90)).isoformat()
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM pedidos WHERE fecha >= ? AND estado NOT IN ('Cancelado')", (cutoff90,))
    ventas_90 = c.fetchone()[0] or 1
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM ordenes_compra WHERE fecha >= ? AND estado NOT IN ('Pendiente','Cancelada')", (cutoff90,))
    compras_90 = c.fetchone()[0] or 1
    c.execute("SELECT COALESCE(SUM(fi.cantidad * fi.precio_unitario),0) FROM flujo_egresos fi WHERE fi.fecha >= ? AND fi.categoria IN ('MP','Materia Prima','Insumo')", (cutoff90,))
    cogs_90 = c.fetchone()[0] or 1
    # Burn rate: promedio mensual de OCs pagadas (últimos 3 meses)
    cutoff3m = (today - timedelta(days=90)).isoformat()
    c.execute("SELECT COALESCE(SUM(valor_total),0) FROM ordenes_compra "
              "WHERE fecha >= ? AND estado NOT IN ('Pendiente','Cancelada','Borrador')",
              (cutoff3m,))
    egr3m = c.fetchone()[0] or 0
    burn_rate = max(egr3m / 3.0, 1.0)
    conn.close()
    dso = (ar_total / (ventas_90 / 90.0)) if ventas_90 > 0 else 0
    dpo = (ap_total / (compras_90 / 90.0)) if compras_90 > 0 else 0
    dio = (inventory_value / (cogs_90 / 90.0)) if cogs_90 > 0 else 0
    ccc = dio + dso - dpo
    working_capital = cash + inventory_value + ar_total - ap_total
    runway_meses = (cash / burn_rate) if burn_rate > 0 else 0
    return jsonify({
        'ar_total': ar_total, 'ap_total': ap_total, 'cash': cash,
        'inventory_value': inventory_value, 'working_capital': working_capital,
        'dso': dso, 'dpo': dpo, 'dio': dio, 'ccc': ccc,
        'burn_rate': burn_rate, 'runway_meses': runway_meses
    })

@app.route('/api/financiero/pnl')
def financiero_pnl():
    """P&L real: ingresos desde pedidos + maquila, egresos desde ordenes_compra."""
    from datetime import date, timedelta
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    today   = date.today()
    mes_str = today.strftime('%Y-%m')
    year_str= today.strftime('%Y')
    periodo = today.strftime('%b %Y')
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()

    def ing_animus(periodo_like):
        c.execute("SELECT COALESCE(SUM(valor_total),0) FROM pedidos "
                  "WHERE fecha LIKE ? AND estado NOT IN ('Cancelado')"
                  " AND (empresa='ANIMUS' OR empresa IS NULL OR empresa='')",
                  (periodo_like+'%',))
        return c.fetchone()[0] or 0

    def ing_maquila(periodo_like):
        try:
            c.execute("SELECT COALESCE(SUM(precio_lote),0) FROM maquila_ordenes "
                      "WHERE fecha_orden LIKE ? AND estado NOT IN ('Cotizacion','Cancelada')",
                      (periodo_like+'%',))
            return c.fetchone()[0] or 0
        except Exception:
            return 0

    def egr_total(periodo_like):
        c.execute("SELECT COALESCE(SUM(valor_total),0) FROM ordenes_compra "
                  "WHERE fecha LIKE ? AND estado NOT IN ('Pendiente','Cancelada','Borrador')",
                  (periodo_like+'%',))
        return c.fetchone()[0] or 0

    # Mes actual
    animus_ing  = ing_animus(mes_str)
    maqui_ing   = ing_maquila(mes_str)
    total_ing   = animus_ing + maqui_ing
    total_egr   = egr_total(mes_str)
    margen      = total_ing - total_egr
    margen_pct  = round((margen / total_ing * 100), 1) if total_ing > 0 else 0
    # YTD
    ytd_ing = ing_animus(year_str) + ing_maquila(year_str)
    ytd_egr = egr_total(year_str)
    empresas = {
        'ANIMUS':    {'ingresos': animus_ing, 'egresos': 0, 'margen': animus_ing,
                      'margen_pct': 100, 'ingresos_ytd': ing_animus(year_str),
                      'egresos_ytd': 0, 'ebitda': animus_ing},
        'ESPAGIRIA': {'ingresos': maqui_ing, 'egresos': 0, 'margen': maqui_ing,
                      'margen_pct': 100, 'ingresos_ytd': ing_maquila(year_str),
                      'egresos_ytd': 0, 'ebitda': maqui_ing},
        'TOTAL':     {'ingresos': total_ing, 'egresos': total_egr, 'margen': margen,
                      'margen_pct': margen_pct, 'ingresos_ytd': ytd_ing,
                      'egresos_ytd': ytd_egr, 'ebitda': margen},
    }
    # Histórico 6 meses
    historico = []
    for i in range(5, -1, -1):
        ref   = today.replace(day=1) - timedelta(days=i * 28)
        p     = ref.strftime('%Y-%m')
        label = ref.strftime('%b %y')
        h_ing = ing_animus(p) + ing_maquila(p)
        h_egr = egr_total(p)
        historico.append({'periodo': label, 'ingresos': h_ing,
                          'egresos': h_egr, 'margen': h_ing - h_egr})
    conn.close()
    return jsonify({'empresas': empresas, 'historico': historico, 'periodo': periodo})

# ===============================================================
# INVENTARIO v2 - NUEVOS ENDPOINTS
# ===============================================================

@app.route('/api/ordenes-compra/pendientes-recepcion')
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

@app.route('/api/trazabilidad/lote/<path:lote>')
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

@app.route('/api/mp/<codigo>/historial-precios')
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

@app.route('/api/mp/<codigo>/consumo-historico')
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

@app.route('/api/conteos', methods=['GET','POST'])
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

@app.route('/api/conteos/<int:cid>', methods=['GET','PATCH'])
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


@app.route('/api/lotes/cuarentena/<int:mov_id>/liberar', methods=['POST'])
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

@app.route('/api/maestro-mp/<codigo>/precio', methods=['POST'])
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


@app.route('/api/admin/backfill-precios-mp', methods=['POST'])
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
    # Fuente 2: precios_mp_historico (precio más reciente por MP)
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


# ═══════════════════════════════════════════════
#  MAQUILA 360 — API
# ═══════════════════════════════════════════════
@app.route('/api/maquila/prospectos', methods=['GET','POST'])
def api_maquila_prospectos():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        empresa = (d.get('empresa') or '').strip()
        if not empresa:
            conn.close(); return jsonify({'error':'Empresa requerida'}), 400
        c.execute('''INSERT INTO maquila_prospectos
                     (empresa,contacto,email,whatsapp,categoria_producto,etapa,
                      observaciones,valor_estimado_lote,creado_por)
                     VALUES (?,?,?,?,?,?,?,?,?)''',
                  (empresa, d.get('contacto',''), d.get('email',''),
                   d.get('telefono',''), d.get('producto_tipo',''),
                   d.get('etapa','Contacto'), d.get('notas',''),
                   float(d.get('valor_estimado',0)),
                   session.get('compras_user') or d.get('operador','sistema')))
        conn.commit(); pid = c.lastrowid; conn.close()
        return jsonify({'id': pid}), 201
    c.execute('''SELECT id, empresa, contacto, email,
                        COALESCE(whatsapp,'') as telefono,
                        COALESCE(categoria_producto,'') as producto_tipo,
                        etapa,
                        COALESCE(observaciones,'') as notas,
                        COALESCE(valor_estimado_lote,0) as valor_estimado,
                        fecha_creacion as fecha_contacto
                 FROM maquila_prospectos ORDER BY id DESC''')
    cols=['id','empresa','contacto','email','telefono','producto_tipo',
          'etapa','notas','valor_estimado','fecha_contacto']
    rows=[dict(zip(cols,r)) for r in c.fetchall()]
    conn.close(); return jsonify(rows)

@app.route('/api/maquila/prospectos/<int:pid>', methods=['PATCH'])
def api_maquila_prospecto_patch(pid):
    d = request.json or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if 'etapa' in d:
        c.execute('UPDATE maquila_prospectos SET etapa=? WHERE id=?', (d['etapa'], pid))
    if 'valor_estimado' in d:
        c.execute('UPDATE maquila_prospectos SET valor_estimado_lote=? WHERE id=?',
                  (float(d['valor_estimado']), pid))
    if 'notas' in d:
        c.execute('UPDATE maquila_prospectos SET observaciones=? WHERE id=?', (d['notas'], pid))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/maquila/ordenes', methods=['GET','POST'])
def api_maquila_ordenes():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        empresa = (d.get('empresa') or '').strip()
        producto = (d.get('producto') or '').strip()
        if not empresa or not producto:
            conn.close(); return jsonify({'error':'Empresa y producto requeridos'}), 400
        c.execute('''INSERT INTO maquila_ordenes
                     (cliente_nombre,producto,lote_kg,fecha_orden,
                      fecha_entrega_est,estado,precio_lote,observaciones,creado_por)
                     VALUES (?,?,?,?,?,?,?,?,?)''',
                  (empresa, producto, float(d.get('batch_size_kg',0)),
                   d.get('fecha_inicio',''), d.get('fecha_entrega',''),
                   d.get('estado','Cotizacion'), float(d.get('valor_total',0)),
                   d.get('observaciones',''),
                   session.get('compras_user') or d.get('operador','sistema')))
        conn.commit(); oid=c.lastrowid; conn.close()
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
    conn.close(); return jsonify(rows)

@app.route('/api/maquila/ordenes/<int:oid>', methods=['PATCH'])
def api_maquila_orden_patch(oid):
    d = request.json or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if 'estado' in d:
        c.execute('UPDATE maquila_ordenes SET estado=? WHERE id=?', (d['estado'], oid))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/maquila/cotizar', methods=['POST'])
def api_maquila_cotizar():
    d = request.json or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute('''INSERT INTO maquila_cotizaciones
                 (empresa,producto_tipo,batch_size_kg,costo_mp,costo_proceso,margen_pct,valor_total,usuario)
                 VALUES (?,?,?,?,?,?,?,?)''',
              (d.get('empresa',''), d.get('producto_tipo',''),
               float(d.get('batch_size_kg',0)), float(d.get('costo_mp',0)),
               float(d.get('costo_proceso',0)), float(d.get('margen_pct',0)),
               float(d.get('valor_total',0)),
               session.get('compras_user') or d.get('operador','sistema')))
    conn.commit(); cid=c.lastrowid; conn.close()
    return jsonify({'id': cid}), 201

@app.route('/api/maquila/kpis', methods=['GET'])
def api_maquila_kpis():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM maquila_prospectos WHERE etapa NOT IN ('Activo','Perdido') AND estado='Activo'")
    prosp = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM maquila_ordenes WHERE estado IN ('Cotizacion','Orden','En proceso','Produccion')")
    ords = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(valor_estimado_lote),0) FROM maquila_prospectos WHERE estado='Activo'")
    valor = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM maquila_prospectos WHERE etapa IN ('Negociacion','Cierre') AND estado='Activo'")
    cierre = c.fetchone()[0]
    conn.close()
    return jsonify({'prospectos_activos':prosp,'ordenes_activas':ords,
                    'valor_pipeline':valor,'en_cierre':cierre})


# ═══════════════════════════════════════════════════════
#  ÁNIMUS — Auto Producción + Recall Engine COC-PRO-016
# ═══════════════════════════════════════════════════════
@app.route('/api/animus/alertas-stock', methods=['GET'])
def animus_alertas_stock():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
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
    conn.close()
    return jsonify({'alertas': alertas, 'total': len(alertas)})

@app.route('/api/animus/solicitar-produccion', methods=['POST'])
def animus_solicitar_produccion():
    d = request.json or {}
    sku = d.get('sku','').strip()
    if not sku:
        return jsonify({'error': 'SKU requerido'}), 400
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    # Get current stock info
    c.execute("SELECT descripcion, SUM(unidades_disponible), stock_minimo_ud FROM stock_pt WHERE sku=? AND empresa='ANIMUS' AND estado='Disponible' GROUP BY sku", (sku,))
    row = c.fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'SKU no encontrado en stock ANIMUS'}), 404
    desc, disponible, minimo = row[0], row[1] or 0, row[2] or 0
    # Check if there's already a pending solicitud
    c.execute("SELECT id FROM solicitudes_produccion WHERE sku=? AND estado='Pendiente'", (sku,))
    existente = c.fetchone()
    if existente:
        conn.close(); return jsonify({'warning': 'Ya existe una solicitud pendiente para este SKU', 'id': existente[0]}), 200
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
    conn.commit(); conn.close()
    return jsonify({'id': sid, 'sku': sku, 'unidades': unidades, 'prioridad': prioridad}), 201

@app.route('/api/animus/solicitudes-produccion', methods=['GET'])
def animus_solicitudes_produccion():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT id,sku,descripcion,unidades_solicitadas,motivo,
                        estado,prioridad,fecha_solicitud,fecha_requerida,
                        solicitado_por,observaciones
                 FROM solicitudes_produccion ORDER BY
                 CASE prioridad WHEN 'Urgente' THEN 1 WHEN 'Alta' THEN 2 ELSE 3 END,
                 fecha_solicitud DESC""")
    cols=['id','sku','descripcion','unidades','motivo','estado','prioridad',
          'fecha_solicitud','fecha_requerida','solicitado_por','observaciones']
    rows=[dict(zip(cols,r)) for r in c.fetchall()]
    conn.close(); return jsonify(rows)

@app.route('/api/animus/solicitudes-produccion/<int:sid>', methods=['PATCH'])
def animus_update_solicitud(sid):
    d = request.json or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if 'estado' in d:
        c.execute("UPDATE solicitudes_produccion SET estado=? WHERE id=?", (d['estado'], sid))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/stock-pt/<sku>/reorden', methods=['POST'])
def actualizar_reorden_pt(sku):
    d = request.json or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE stock_pt SET stock_minimo_ud=?, dias_reposicion=? WHERE sku=?",
              (int(d.get('stock_minimo_ud', 0)),
               int(d.get('dias_reposicion', 15)), sku))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

# ── Recall Engine COC-PRO-016 ──────────────────────────────────────────
@app.route('/api/recall/simular/<path:lote_pt>', methods=['GET'])
def recall_simular(lote_pt):
    import urllib.parse; lote_pt = urllib.parse.unquote(lote_pt)
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
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
    conn.close()
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

@app.route('/api/recall/ejecutar', methods=['POST'])
def recall_ejecutar():
    if 'compras_user' not in session or session.get('compras_user') not in ADMIN_USERS:
        return jsonify({'error': 'Solo administradores pueden ejecutar un recall'}), 401
    d = request.json or {}
    lote_pt = d.get('lote_pt','').strip()
    motivo  = d.get('motivo','').strip()
    if not lote_pt or not motivo:
        return jsonify({'error': 'lote_pt y motivo son requeridos'}), 400
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
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
    conn.commit(); conn.close()
    return jsonify({
        'recall_id': rid,
        'lote_pt': lote_pt,
        'unidades_despachadas': total_uds,
        'despachos': n_desp,
        'lotes_bloqueados_bodega': bloqueadas,
        'estado': 'Ejecutado'
    }), 201




# ─── Panel de Recepcion — rutas standalone ────────────────────────────────────


@app.route('/hub-salida')
def hub_salida_page():
    if 'compras_user' not in session:
        return redirect(url_for('login'))
    return Response(SALIDA_HTML, mimetype='text/html')

@app.route('/api/hub-salida/pedidos-pendientes')
def hub_pedidos_pendientes():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT p.numero, p.cliente_id, cl.nombre as cliente, p.fecha, p.estado, p.valor_total
                 FROM pedidos p
                 LEFT JOIN clientes cl ON p.cliente_id = cl.id
                 WHERE p.estado IN ('Confirmado','En preparacion','En Produccion','Aprobado','Listo')
                 ORDER BY p.fecha DESC""")
    cols = ['numero','cliente_id','cliente','fecha','estado','valor_total']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return jsonify({'pedidos': rows})

@app.route('/api/hub-salida/pedido/<numero>')
def hub_pedido_detalle(numero):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT p.numero, p.cliente_id, cl.nombre as cliente, p.fecha, p.estado, p.valor_total
                 FROM pedidos p LEFT JOIN clientes cl ON p.cliente_id=cl.id
                 WHERE p.numero=?""", (numero,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Pedido no encontrado'}), 404
    ped = dict(zip(['numero','cliente_id','cliente','fecha','estado','valor_total'], row))
    c.execute("""SELECT sku, descripcion, cantidad, precio_unitario
                 FROM pedidos_items WHERE numero_pedido=?""", (numero,))
    ped['items'] = [dict(zip(['sku','descripcion','cantidad','precio_unitario'], r)) for r in c.fetchall()]
    conn.close()
    return jsonify(ped)

@app.route('/api/hub-salida/stock/<sku>')
def hub_stock_sku(sku):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT lote_pt, unidades_disponible, fecha_produccion
                 FROM stock_pt WHERE sku=? AND estado='Disponible' AND unidades_disponible>0
                 ORDER BY fecha_produccion ASC""", (sku,))
    lotes = [{'lote': r[0], 'disponible': r[1], 'fecha': r[2]} for r in c.fetchall()]
    total = sum(l['disponible'] for l in lotes)
    conn.close()
    return jsonify({'sku': sku, 'total': total, 'lotes': lotes})

@app.route('/api/hub-salida/despachar', methods=['POST'])
def hub_despachar():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    d = request.get_json() or {}
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM despachos"); n = (c.fetchone()[0] or 0) + 1
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
    conn.commit(); conn.close()
    return jsonify({'message': f'Despacho {numero} registrado', 'numero': numero}), 201


@app.route('/recepcion')
def recepcion_panel():
    return Response(RECEPCION_HTML, mimetype='text/html')


@app.route('/api/recepcion/detalle/<numero_oc>')
def recepcion_detalle_oc(numero_oc):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute(
        'SELECT numero_oc, proveedor, estado, categoria, fecha, '
        'COALESCE(valor_total,0), creado_por, observaciones '
        'FROM ordenes_compra WHERE numero_oc=?', (numero_oc,))
    oc = c.fetchone()
    if oc is None:
        conn.close(); return jsonify({'error': 'OC no encontrada'}), 404
    c.execute(
        'SELECT codigo_mp, nombre_mp, COALESCE(cantidad_g,0), '
        'COALESCE(precio_unitario,0), COALESCE(cantidad_recibida_g,0), '
        'COALESCE(lote_asignado,"") '
        'FROM ordenes_compra_items WHERE numero_oc=?', (numero_oc,))
    items = c.fetchall()
    conn.close()
    return jsonify({
        'numero_oc': oc[0], 'proveedor': oc[1], 'estado': oc[2],
        'categoria': oc[3], 'fecha': oc[4], 'valor_total': oc[5],
        'creado_por': oc[6], 'observaciones': oc[7],
        'items': [
            {'codigo_mp': i[0], 'nombre_mp': i[1], 'cantidad_g': i[2],
             'precio_unitario': i[3], 'cantidad_recibida_g': i[4], 'lote_asignado': i[5]}
            for i in items
        ]
    })


@app.route('/api/recepcion/seguimiento')
def recepcion_seguimiento():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute(
        'SELECT numero_oc, fecha, estado, proveedor, categoria, '
        'COALESCE(valor_total,0), COALESCE(fecha_recepcion,""), '
        'COALESCE(observaciones_recepcion,""), COALESCE(tiene_discrepancias,0), '
        'COALESCE(fecha_pago,""), COALESCE(fecha_autorizacion,"") '
        "FROM ordenes_compra WHERE estado IN ('Autorizada','Recibida','Pagada','Parcial') "
        'ORDER BY fecha DESC LIMIT 200')
    rows = c.fetchall()
    conn.close()
    return jsonify([
        {'numero_oc': r[0], 'fecha': r[1], 'estado': r[2], 'proveedor': r[3],
         'categoria': r[4], 'valor_total': r[5], 'fecha_recepcion': r[6],
         'observaciones': r[7], 'tiene_discrepancias': r[8],
         'fecha_pago': r[9], 'fecha_autorizacion': r[10]}
        for r in rows
    ])


@app.route('/api/recepcion/lotes-cuarentena')
def recepcion_lotes_cuarentena():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT id, material_id, material_nombre, cantidad, lote,
                        fecha_vencimiento, proveedor, fecha, numero_oc
                 FROM movimientos
                 WHERE tipo='Entrada' AND (estado_lote='Cuarentena' OR (estado_lote IS NULL AND lote IS NOT NULL AND lote != ''))
                 ORDER BY fecha DESC LIMIT 100""")
    rows = c.fetchall()
    conn.close()
    cols = ['id','material_id','material_nombre','cantidad','lote','fecha_vencimiento','proveedor','fecha','numero_oc']
    return jsonify([dict(zip(cols, r)) for r in rows])


@app.route('/api/recepcion/aprobar-lote', methods=['POST'])
def recepcion_aprobar_lote():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.get_json() or {}
    mov_id = d.get('mov_id')
    nuevo_estado = d.get('estado', 'Aprobado')  # Aprobado o Rechazado
    if not mov_id:
        return jsonify({'error': 'mov_id requerido'}), 400
    usuario = session.get('compras_user', '')
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE movimientos SET estado_lote=?, operador=? WHERE id=?",
              (nuevo_estado, usuario, mov_id))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'estado': nuevo_estado})


@app.route('/api/recepcion/trazabilidad/<path:lote>')
def recepcion_trazabilidad_lote(lote):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""SELECT m.id, m.material_id, m.material_nombre, m.cantidad,
                        m.lote, m.fecha_vencimiento, m.proveedor, m.fecha,
                        m.estado_lote, m.numero_oc, m.operador
                 FROM movimientos m
                 WHERE m.lote=? ORDER BY m.fecha DESC""", (lote,))
    rows = c.fetchall()
    cols = ['id','material_id','material_nombre','cantidad','lote','fecha_vencimiento',
            'proveedor','fecha','estado_lote','numero_oc','operador']
    movs = [dict(zip(cols, r)) for r in rows]
    oc_info = None
    if movs and movs[0].get('numero_oc'):
        c.execute("SELECT numero_oc, fecha, proveedor, estado, valor_total, recibido_por FROM ordenes_compra WHERE numero_oc=?",
                  (movs[0]['numero_oc'],))
        oc_row = c.fetchone()
        if oc_row:
            oc_info = dict(zip(['numero_oc','fecha','proveedor','estado','valor_total','recibido_por'], oc_row))
    conn.close()
    return jsonify({'lote': lote, 'movimientos': movs, 'oc': oc_info})


# ─── Recursos Humanos ────────────────────────────────────────────────────────

@app.route("/rrhh")
def rrhh_panel():
    if "compras_user" not in session:
        return redirect("/login?next=/rrhh")
    usuario = session.get("compras_user","").capitalize()
    return Response(RRHH_HTML.replace("{usuario}", usuario), mimetype="text/html")


@app.route("/api/rrhh/dashboard")
def rrhh_dashboard():
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM empleados WHERE estado='Activo'")
    headcount = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(salario_base),0) FROM empleados WHERE estado='Activo'")
    nomina_bruta = c.fetchone()[0]
    mes_actual = datetime.now().strftime("%Y-%m")
    c.execute("SELECT COALESCE(SUM(dias),0) FROM ausencias WHERE estado='Aprobada' AND fecha_inicio LIKE ?", (mes_actual+"%",))
    dias_ausentes = c.fetchone()[0]
    ausentismo_pct = round(dias_ausentes/(headcount*22)*100,1) if headcount>0 else 0
    c.execute("SELECT COUNT(*) FROM capacitaciones_empleados WHERE completado=0")
    caps_pendientes = c.fetchone()[0]
    c.execute("SELECT empresa, COUNT(*) FROM empleados WHERE estado='Activo' GROUP BY empresa ORDER BY 2 DESC")
    por_empresa = [{"empresa":r[0],"count":r[1]} for r in c.fetchall()]
    c.execute("SELECT area, COUNT(*) FROM empleados WHERE estado='Activo' GROUP BY area ORDER BY 2 DESC")
    por_area = [{"area":r[0],"count":r[1]} for r in c.fetchall()]
    alertas = []
    from datetime import date as ddate
    c.execute("SELECT id, nombre||' '||apellido, fecha_ingreso FROM empleados WHERE estado='Activo'")
    for emp in c.fetchall():
        if emp[2]:
            try:
                fi = ddate.fromisoformat(emp[2])
                if (ddate.today()-fi).days > 365:
                    c.execute("SELECT COALESCE(SUM(dias),0) FROM ausencias WHERE tipo='Vacaciones' AND estado='Aprobada' AND empleado_id=?", (emp[0],))
                    vac = c.fetchone()[0]
                    if vac < 15:
                        alertas.append({"tipo":"warn","msg":emp[1]+" tiene "+str(15-vac)+" dias de vacaciones pendientes"})
            except: pass
    c.execute("SELECT nombre||' '||apellido, fecha_fin_contrato FROM empleados WHERE tipo_contrato='Fijo' AND fecha_fin_contrato!='' AND estado='Activo'")
    for r in c.fetchall():
        if r[1]:
            try:
                fv = ddate.fromisoformat(r[1])
                d_days = (fv-ddate.today()).days
                if 0 < d_days <= 45:
                    alertas.append({"tipo":"danger","msg":"Contrato de "+r[0]+" vence en "+str(d_days)+" dias"})
            except: pass
    conn.close()
    return jsonify({"headcount":headcount,"nomina_bruta":nomina_bruta,"ausentismo_pct":ausentismo_pct,"caps_pendientes":caps_pendientes,"por_empresa":por_empresa,"por_area":por_area,"alertas":alertas})


@app.route("/api/rrhh/empleados", methods=["GET","POST"])
def rrhh_empleados():
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == "POST":
        d = request.get_json(silent=True) or {}
        c.execute("SELECT COUNT(*) FROM empleados"); n = c.fetchone()[0]+1
        codigo = "EMP"+str(n).zfill(4)
        c.execute("INSERT INTO empleados (codigo,nombre,apellido,cedula,cargo,area,empresa,tipo_contrato,fecha_ingreso,estado,salario_base,eps,afp,arl,caja_compensacion,email,telefono,nivel_riesgo,observaciones) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (codigo,d.get("nombre",""),d.get("apellido",""),d.get("cedula",""),d.get("cargo",""),d.get("area",""),d.get("empresa","Espagiria"),d.get("tipo_contrato","Indefinido"),d.get("fecha_ingreso",""),"Activo",float(d.get("salario_base",0)),d.get("eps",""),d.get("afp",""),d.get("arl",""),d.get("caja",""),d.get("email",""),d.get("telefono",""),int(d.get("nivel_riesgo",1)),d.get("observaciones","")))
        conn.commit(); new_id=c.lastrowid; conn.close()
        return jsonify({"ok":True,"id":new_id,"codigo":codigo}),201
    c.execute("SELECT id,codigo,nombre,apellido,cargo,area,empresa,tipo_contrato,fecha_ingreso,estado,salario_base,email,telefono,eps,afp,nivel_riesgo FROM empleados ORDER BY empresa,nombre")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"codigo":r[1],"nombre":r[2],"apellido":r[3],"cargo":r[4],"area":r[5],"empresa":r[6],"tipo_contrato":r[7],"fecha_ingreso":r[8],"estado":r[9],"salario_base":r[10],"email":r[11],"telefono":r[12],"eps":r[13],"afp":r[14],"nivel_riesgo":r[15]} for r in rows])


@app.route("/api/rrhh/empleados/<int:eid>", methods=["GET","PUT"])
def rrhh_empleado_det(eid):
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == "PUT":
        d = request.get_json(silent=True) or {}
        c.execute("UPDATE empleados SET nombre=?,apellido=?,cargo=?,area=?,empresa=?,tipo_contrato=?,salario_base=?,eps=?,afp=?,arl=?,caja_compensacion=?,email=?,telefono=?,nivel_riesgo=?,observaciones=?,estado=? WHERE id=?",
                 (d.get("nombre",""),d.get("apellido",""),d.get("cargo",""),d.get("area",""),d.get("empresa",""),d.get("tipo_contrato",""),float(d.get("salario_base",0)),d.get("eps",""),d.get("afp",""),d.get("arl",""),d.get("caja",""),d.get("email",""),d.get("telefono",""),int(d.get("nivel_riesgo",1)),d.get("observaciones",""),d.get("estado","Activo"),eid))
        conn.commit(); conn.close(); return jsonify({"ok":True})
    c.execute("SELECT * FROM empleados WHERE id=?", (eid,))
    r=c.fetchone()
    if not r: conn.close(); return jsonify({"error":"not found"}),404
    cols=[d[0] for d in c.description]; conn.close()
    return jsonify(dict(zip(cols,r)))


@app.route("/api/rrhh/nomina/<periodo>")
def rrhh_nomina(periodo):
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    SMMLV=1423500; AUX=202000
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    c.execute("SELECT id,nombre,apellido,cargo,salario_base,empresa,area,nivel_riesgo FROM empleados WHERE estado='Activo' ORDER BY empresa,nombre")
    emps=c.fetchall()
    c.execute("SELECT empleado_id,dias_trabajados,horas_extras,valor_horas_extras,bonificaciones,otros_descuentos FROM nomina_registros WHERE periodo=?", (periodo,))
    ex={r[0]:r for r in c.fetchall()}; conn.close()
    result=[]
    arl_rates={1:0.00522,2:0.01044,3:0.02436,4:0.04350,5:0.06960}
    for e in emps:
        eid,nom,ape,cargo,sal,emp,area,riesgo=e
        xr=ex.get(eid)
        dias=xr[1] if xr else 30; he=xr[2] if xr else 0; vhe=xr[3] if xr else 0
        bonos=xr[4] if xr else 0; otros=xr[5] if xr else 0
        aux=AUX if sal<=2*SMMLV else 0
        desc_salud=round(sal*0.04); desc_pension=round(sal*0.04)
        neto=sal+aux+vhe+bonos-desc_salud-desc_pension-otros
        ap_s=round(sal*0.085); ap_p=round(sal*0.12)
        ap_arl=round(sal*arl_rates.get(riesgo,0.00522))
        ap_sena=round(sal*0.02); ap_icbf=round(sal*0.03); ap_caja=round(sal*0.04)
        ap_tot=ap_s+ap_p+ap_arl+ap_sena+ap_icbf+ap_caja
        result.append({"id":eid,"nombre":nom+" "+ape,"cargo":cargo,"empresa":emp,"area":area,"salario_base":sal,"dias_trabajados":dias,"aux_transporte":aux,"horas_extras":he,"valor_horas_extras":vhe,"bonificaciones":bonos,"desc_salud":desc_salud,"desc_pension":desc_pension,"otros_descuentos":otros,"neto":neto,"aportes_empleador":{"salud":ap_s,"pension":ap_p,"arl":ap_arl,"sena":ap_sena,"icbf":ap_icbf,"caja":ap_caja,"total":ap_tot}})
    return jsonify(result)


@app.route("/api/rrhh/nomina/guardar", methods=["POST"])
def rrhh_nomina_guardar():
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    d=request.get_json(silent=True) or {}
    periodo=d.get("periodo",""); registros=d.get("registros",[])
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    for r in registros:
        c.execute("INSERT OR REPLACE INTO nomina_registros (periodo,empleado_id,salario_base,dias_trabajados,horas_extras,valor_horas_extras,subsidio_transporte,bonificaciones,descuento_salud,descuento_pension,otros_descuentos,salario_neto,estado) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (periodo,r["id"],r["salario_base"],r.get("dias_trabajados",30),r.get("horas_extras",0),r.get("valor_horas_extras",0),r.get("aux_transporte",0),r.get("bonificaciones",0),r["desc_salud"],r["desc_pension"],r.get("otros_descuentos",0),r["neto"],"Generada"))
    conn.commit(); conn.close()
    return jsonify({"ok":True,"periodo":periodo,"registros":len(registros)})


@app.route("/api/rrhh/ausencias", methods=["GET","POST"])
def rrhh_ausencias():
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    if request.method=="POST":
        d=request.get_json(silent=True) or {}
        c.execute("INSERT INTO ausencias (empleado_id,tipo,fecha_inicio,fecha_fin,dias,estado,observaciones) VALUES (?,?,?,?,?,'Pendiente',?)",
                 (int(d.get("empleado_id",0)),d.get("tipo","Vacaciones"),d.get("fecha_inicio",""),d.get("fecha_fin",""),int(d.get("dias",0)),d.get("observaciones","")))
        conn.commit(); conn.close(); return jsonify({"ok":True}),201
    c.execute("SELECT a.id,e.nombre||' '||e.apellido,a.tipo,a.fecha_inicio,a.fecha_fin,a.dias,a.estado,a.observaciones,a.aprobado_por FROM ausencias a JOIN empleados e ON a.empleado_id=e.id ORDER BY a.creado_en DESC LIMIT 200")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"empleado":r[1],"tipo":r[2],"fecha_inicio":r[3],"fecha_fin":r[4],"dias":r[5],"estado":r[6],"observaciones":r[7],"aprobado_por":r[8]} for r in rows])


@app.route("/api/rrhh/ausencias/<int:aid>", methods=["PATCH"])
def rrhh_ausencia_upd(aid):
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    d=request.get_json(silent=True) or {}
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    c.execute("UPDATE ausencias SET estado=?,aprobado_por=? WHERE id=?", (d.get("estado",""),session.get("compras_user",""),aid))
    conn.commit(); conn.close(); return jsonify({"ok":True})


@app.route("/api/rrhh/capacitaciones", methods=["GET","POST"])
def rrhh_caps():
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    if request.method=="POST":
        d=request.get_json(silent=True) or {}
        c.execute("INSERT INTO capacitaciones (nombre,tipo,fecha,duracion_horas,instructor,empresa,obligatoria) VALUES (?,?,?,?,?,?,?)",
                 (d.get("nombre",""),d.get("tipo","BPM"),d.get("fecha",""),float(d.get("duracion_horas",1)),d.get("instructor",""),d.get("empresa","Espagiria"),1 if d.get("obligatoria") else 0))
        cap_id=c.lastrowid
        c.execute("SELECT id FROM empleados WHERE estado='Activo'")
        for emp in c.fetchall():
            try: c.execute("INSERT OR IGNORE INTO capacitaciones_empleados (capacitacion_id,empleado_id,completado) VALUES (?,?,0)", (cap_id,emp[0]))
            except: pass
        conn.commit(); conn.close(); return jsonify({"ok":True,"id":cap_id}),201
    c.execute("SELECT c.id,c.nombre,c.tipo,c.fecha,c.duracion_horas,c.instructor,c.obligatoria,COUNT(ce.id),COALESCE(SUM(ce.completado),0) FROM capacitaciones c LEFT JOIN capacitaciones_empleados ce ON c.id=ce.capacitacion_id GROUP BY c.id ORDER BY c.fecha DESC")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"nombre":r[1],"tipo":r[2],"fecha":r[3],"horas":r[4],"instructor":r[5],"obligatoria":r[6],"total":r[7],"completados":r[8]} for r in rows])


@app.route("/api/rrhh/evaluaciones", methods=["GET","POST"])
def rrhh_evals():
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    if request.method=="POST":
        d=request.get_json(silent=True) or {}
        scores=[float(d.get(k,0)) for k in ["calidad","asistencia","actitud","conocimiento","productividad"]]
        total=round(sum(scores)/5,1)
        c.execute("INSERT INTO evaluaciones (empleado_id,periodo,evaluador,puntaje_total,puntaje_calidad,puntaje_asistencia,puntaje_actitud,puntaje_conocimiento,puntaje_productividad,comentarios,estado) VALUES (?,?,?,?,?,?,?,?,?,?,'Publicada')",
                 (int(d.get("empleado_id",0)),d.get("periodo",""),session.get("compras_user",""),total,scores[0],scores[1],scores[2],scores[3],scores[4],d.get("comentarios","")))
        conn.commit(); conn.close(); return jsonify({"ok":True}),201
    periodo=request.args.get("periodo","")
    q="SELECT ev.id,e.nombre||' '||e.apellido,e.cargo,ev.periodo,ev.evaluador,ev.puntaje_total,ev.puntaje_calidad,ev.puntaje_asistencia,ev.puntaje_actitud,ev.puntaje_conocimiento,ev.puntaje_productividad,ev.comentarios FROM evaluaciones ev JOIN empleados e ON ev.empleado_id=e.id"
    if periodo: c.execute(q+" WHERE ev.periodo=? ORDER BY ev.puntaje_total DESC",(periodo,))
    else: c.execute(q+" ORDER BY ev.periodo DESC,ev.puntaje_total DESC LIMIT 50")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"empleado":r[1],"cargo":r[2],"periodo":r[3],"evaluador":r[4],"total":r[5],"calidad":r[6],"asistencia":r[7],"actitud":r[8],"conocimiento":r[9],"productividad":r[10],"comentarios":r[11]} for r in rows])


@app.route("/api/rrhh/sgsst", methods=["GET","POST"])
def rrhh_sgsst():
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    if request.method=="POST":
        d=request.get_json(silent=True) or {}
        c.execute("INSERT INTO sgsst_items (categoria,descripcion,frecuencia,responsable,proximo_vencimiento,estado) VALUES (?,?,?,?,?,'Pendiente')",
                 (d.get("categoria",""),d.get("descripcion",""),d.get("frecuencia","Anual"),d.get("responsable",""),d.get("proximo_vencimiento","")))
        conn.commit(); conn.close(); return jsonify({"ok":True}),201
    c.execute("SELECT id,categoria,descripcion,frecuencia,ultimo_cumplimiento,proximo_vencimiento,responsable,estado FROM sgsst_items ORDER BY categoria,descripcion")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"categoria":r[1],"descripcion":r[2],"frecuencia":r[3],"ultimo":r[4],"proximo":r[5],"responsable":r[6],"estado":r[7]} for r in rows])


@app.route("/api/rrhh/sgsst/<int:sid>", methods=["PATCH"])
def rrhh_sgsst_upd(sid):
    if "compras_user" not in session: return jsonify({"error":"No autorizado"}),401
    d=request.get_json(silent=True) or {}
    from datetime import date as ddate, timedelta
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    c.execute("SELECT frecuencia FROM sgsst_items WHERE id=?", (sid,))
    row=c.fetchone(); hoy=ddate.today().isoformat()
    freq_days={"Mensual":30,"Trimestral":90,"Semestral":180,"Anual":365}
    prox=d.get("proximo_vencimiento","") or (ddate.today()+timedelta(days=freq_days.get(row[0] if row else "Anual",365))).isoformat()
    c.execute("UPDATE sgsst_items SET estado='Cumplido',ultimo_cumplimiento=?,proximo_vencimiento=? WHERE id=?", (hoy,prox,sid))
    conn.commit(); conn.close(); return jsonify({"ok":True})

# ═══════════════════════════════════════════════════════
#  CALIDAD BPM — Página + API
# ═══════════════════════════════════════════════════════
@app.route('/calidad')
def calidad_page():
    if 'compras_user' not in session:
        return redirect('/login?next=/calidad')
    return Response(CALIDAD_HTML, mimetype='text/html')


@app.route('/api/calidad/dashboard')
def calidad_dashboard():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
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
    # Actividad reciente: últimas NC + últimas acciones CC
    actividad = []
    c.execute("""SELECT 'NC' as tipo, descripcion, area, fecha, estado, impacto
                 FROM no_conformidades ORDER BY id DESC LIMIT 5""")
    for r in c.fetchall():
        color = 'rojo' if r[5] in ('Alto','Critico') else 'amari'
        actividad.append({'titulo': f'NC #{r[0]}: {r[1][:60]}' if False else f'NC — {r[1][:55]}',
                          'subtitulo': f'{r[2]} · {r[4]}', 'fecha': r[3], 'color': color})
    c.execute("""SELECT material_nombre, lote, estado_lote, fecha
                 FROM movimientos WHERE tipo='Entrada'
                 AND estado_lote IN ('Aprobado','Rechazado')
                 ORDER BY id DESC LIMIT 5""")
    for r in c.fetchall():
        color = 'verde' if r[2] == 'Aprobado' else 'rojo'
        actividad.append({'titulo': f'Lote {r[1] or "s/n"} — {r[2]}',
                          'subtitulo': r[0][:50], 'fecha': r[3], 'color': color})
    actividad.sort(key=lambda x: x.get('fecha','') or '', reverse=True)
    conn.close()
    return jsonify({
        'cuarentena': cuarentena,
        'aprobados': aprobados,
        'rechazados': rechazados,
        'nc_abiertas': nc_abiertas,
        'cals_vencidas': cals_vencidas,
        'actividad_reciente': actividad[:8]
    })


@app.route('/api/calidad/no-conformidades', methods=['GET', 'POST'])
def handle_no_conformidades():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        desc = (d.get('descripcion') or '').strip()
        if not desc:
            conn.close(); return jsonify({'error': 'descripcion requerida'}), 400
        c.execute("""INSERT INTO no_conformidades
                     (fecha,tipo,descripcion,area,responsable,lote,codigo_mp,
                      impacto,accion_correctiva,estado,creado_por)
                     VALUES (date('now'),?,?,?,?,?,?,?,?,'Abierta',?)""",
                  (d.get('tipo','Proceso'), desc,
                   d.get('area',''), d.get('responsable',''),
                   d.get('lote',''), d.get('codigo_mp',''),
                   d.get('impacto','Bajo'), d.get('accion_correctiva',''),
                   session.get('compras_user','')))
        conn.commit(); new_id = c.lastrowid; conn.close()
        return jsonify({'id': new_id}), 201
    # GET
    c.execute("""SELECT id,fecha,tipo,descripcion,area,responsable,lote,codigo_mp,
                        impacto,accion_correctiva,estado,fecha_cierre,cerrado_por,creado_por
                 FROM no_conformidades ORDER BY id DESC LIMIT 200""")
    cols = ['id','fecha','tipo','descripcion','area','responsable','lote','codigo_mp',
            'impacto','accion_correctiva','estado','fecha_cierre','cerrado_por','creado_por']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close(); return jsonify(rows)


@app.route('/api/calidad/no-conformidades/<int:ncid>/cerrar', methods=['POST'])
def cerrar_no_conformidad(ncid):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""UPDATE no_conformidades
                 SET estado='Cerrada', fecha_cierre=date('now'), cerrado_por=?
                 WHERE id=?""",
              (session.get('compras_user',''), ncid))
    conn.commit(); conn.close()
    return jsonify({'ok': True})


@app.route('/api/calidad/calibraciones')
def get_calibraciones():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
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
    conn.close(); return jsonify(rows)


@app.errorhandler(404)
def not_found(e):
    h = '<html><body style="background:#0d1117;color:#fff;font-family:sans-serif;text-align:center;padding-top:10vh"><h1>404</h1><p>Pagina no encontrada.</p><a href="/compras" style="color:#7ACFCC;">Volver</a></body></html>'
    return Response(h, status=404, mimetype='text/html')

@app.errorhandler(500)
def server_error(e):
    h = '<html><body style="background:#0d1117;color:#fff;font-family:sans-serif;text-align:center;padding-top:10vh"><h1>500</h1><p>Error interno del servidor.</p><a href="/compras" style="color:#7ACFCC;">Volver</a></body></html>'
    return Response(h, status=500, mimetype='text/html')

if __name__ == '__main__':

    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
